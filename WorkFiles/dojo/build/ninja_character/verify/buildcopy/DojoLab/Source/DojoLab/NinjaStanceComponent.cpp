// Copyright Epic Games, Inc. All Rights Reserved.

#include "NinjaStanceComponent.h"

#include "Animation/AnimInstance.h"
#include "CollisionQueryParams.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimSequenceBase.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "InputAction.h"
#include "InputMappingContext.h"
#include "Net/UnrealNetwork.h"
#include "NinjaJutsuComponent.h"
#include "NinjaVisual.h"

DEFINE_LOG_CATEGORY_STATIC(LogNinjaStance, Log, All);

namespace NinjaStanceConst
{
	/** GASP's component whose tick runs UpdateRotation_PreCMC / UpdateMovement_PreCMC, just before the movement component. */
	const FName GaspPreMovementTickComponent(TEXT("AC_PreCMCTick"));
	/** GASP's CMC character keeps its inputs in this Blueprint struct; its bool fields carry GUID suffixes. */
	const FName GaspInputStateProperty(TEXT("CharacterInputState"));
	const TCHAR* GaspWantsToSprintPrefix = TEXT("WantsToSprint");
}

#if !UE_BUILD_SHIPPING
static TAutoConsoleVariable<int32> CVarNinjaStanceDebug(TEXT("ninja.stance.debug"), 0,
	TEXT("1: log the local ninja's crouch run every frame (speed, GASP crouch speed, animation rate, the planted foot's slide)."));
#endif

UNinjaStanceComponent::UNinjaStanceComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	// Between GASP's pre-movement tick and the movement component (both prerequisites are added in BeginPlay).
	PrimaryComponentTick.TickGroup = TG_PrePhysics;
	SetIsReplicatedByDefault(true);
}

void UNinjaStanceComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
	Super::GetLifetimeReplicatedProps(OutLifetimeProps);
	// The owner predicts its own prone; the server's answer to it comes through ClientRejectProne.
	DOREPLIFETIME_CONDITION(UNinjaStanceComponent, bProneReplicated, COND_SkipOwner);
}

ACharacter* UNinjaStanceComponent::GetCharacter() const
{
	return Cast<ACharacter>(GetOwner());
}

bool UNinjaStanceComponent::IsLocallyControlledPlayer() const
{
	const ACharacter* Character = GetCharacter();
	const APlayerController* PC = Character ? Cast<APlayerController>(Character->GetController()) : nullptr;
	return PC && PC->IsLocalController();
}

void UNinjaStanceComponent::BeginPlay()
{
	Super::BeginPlay();
	ACharacter* Character = GetCharacter();
	UCharacterMovementComponent* Movement = Character ? Character->GetCharacterMovement() : nullptr;
	if (!Movement)
	{
		return;
	}
	// GASP rewrites MaxWalkSpeedCrouched and the rotation mode in its pre-movement tick every frame: override after it, before the
	// movement component uses them.
	UActorComponent* GaspPreMovement = nullptr;
	for (UActorComponent* Component : Character->GetComponents())
	{
		if (Component && Component->GetFName() == NinjaStanceConst::GaspPreMovementTickComponent)
		{
			GaspPreMovement = Component;
			break;
		}
	}
	if (GaspPreMovement)
	{
		AddTickPrerequisiteComponent(GaspPreMovement);
	}
	else
	{
		UE_LOG(LogNinjaStance, Warning, TEXT("%s: no %s component; the crouch run may be overwritten by the owner's own speed code."),
			*GetNameSafe(Character), *NinjaStanceConst::GaspPreMovementTickComponent.ToString());
	}
	Movement->AddTickPrerequisiteComponent(this);
	SavedMinAnalogWalkSpeed = Movement->MinAnalogWalkSpeed;
	// A simulated proxy that joins while its owner lies down.
	if (bProneReplicated && Character->GetLocalRole() == ROLE_SimulatedProxy)
	{
		ApplyProne(true, /*bInstant*/ true);
	}
}

void UNinjaStanceComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	SetExitKeysActive(false);
	if (ACharacter* Character = GetCharacter())
	{
		if (USkeletalMeshComponent* Body = Character->GetMesh())
		{
			Body->GlobalAnimRateScale = 1.0f;
		}
	}
	Super::EndPlay(EndPlayReason);
}

void UNinjaStanceComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	// After the controller, so this frame's input (the pending movement vector the crouch run reads) is already in.
	if (ACharacter* Character = GetCharacter())
	{
		AController* Controller = Character->GetController();
		if (Controller != PrerequisiteController.Get())
		{
			if (AController* Old = PrerequisiteController.Get())
			{
				RemoveTickPrerequisiteActor(Old);
			}
			if (Controller)
			{
				AddTickPrerequisiteActor(Controller);
			}
			PrerequisiteController = Controller;
		}
	}
	UpdateInputBinding();
	UpdateProne();
	UpdateMovementOverrides(DeltaTime);
	UpdateCrouchAnimRate(DeltaTime);
}

// ---------------------------------------------------------------- Input

void UNinjaStanceComponent::UpdateInputBinding()
{
	const ACharacter* Character = GetCharacter();
	UInputComponent* Input = Character ? Character->InputComponent.Get() : nullptr;
	APlayerController* PC = Character ? Cast<APlayerController>(Character->GetController()) : nullptr;
	if (!Input || !PC || !PC->IsLocalController())
	{
		BoundInputComponent.Reset();
		bCrouchHeld = false;
		return;
	}
	if (BoundInputComponent.Get() == Input)
	{
		return;
	}
	BoundInputComponent = Input;
	if (UEnhancedInputComponent* Enhanced = Cast<UEnhancedInputComponent>(Input))
	{
		if (CrouchAction)
		{
			// With no triggers on the action, Started is the press and Completed the release.
			Enhanced->BindAction(CrouchAction, ETriggerEvent::Started, this, &UNinjaStanceComponent::OnCrouchPressed);
			Enhanced->BindAction(CrouchAction, ETriggerEvent::Completed, this, &UNinjaStanceComponent::OnCrouchReleased);
		}
		if (ProneAction)
		{
			Enhanced->BindAction(ProneAction, ETriggerEvent::Started, this, &UNinjaStanceComponent::OnProneInput);
		}
	}
	if (InputMappingContext)
	{
		if (UEnhancedInputLocalPlayerSubsystem* Subsystem = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(PC->GetLocalPlayer()))
		{
			if (!Subsystem->HasMappingContext(InputMappingContext))
			{
				Subsystem->AddMappingContext(InputMappingContext, InputMappingPriority);
			}
		}
	}
}

void UNinjaStanceComponent::OnCrouchPressed()
{
	bCrouchHeld = true;
	ACharacter* Character = GetCharacter();
	if (!Character)
	{
		return;
	}
	if (IsProne())
	{
		// C while lying gets up into a crouch (held): FinishExit keeps the crouch while C is down.
		if (bProneWanted)
		{
			SetProne(false);
		}
		return;
	}
	// In the air it waits for the landing (UpdateMovementOverrides), as GASP's own handler refused a mid-air crouch.
	const UCharacterMovementComponent* Movement = Character->GetCharacterMovement();
	if (Movement && Movement->IsMovingOnGround())
	{
		Character->Crouch();
	}
}

void UNinjaStanceComponent::OnCrouchReleased()
{
	bCrouchHeld = false;
	ACharacter* Character = GetCharacter();
	if (Character && !IsProne())
	{
		Character->UnCrouch();
	}
}

void UNinjaStanceComponent::OnProneInput()
{
	// Ignored while getting up (Space stays mapped here until the ninja is up, so it cannot jump or vault out of the clip).
	if (ProneState != ENinjaProneState::Exiting)
	{
		SetProne(!bProneWanted);
	}
}

void UNinjaStanceComponent::SetExitKeysActive(bool bActive)
{
	if (!bActive)
	{
		if (UEnhancedInputLocalPlayerSubsystem* Subsystem = ProneExitSubsystem.Get(); Subsystem && ProneExitContext)
		{
			// The default options ignore keys still held until released, so a held Space does not jump the moment the ninja is up.
			Subsystem->RemoveMappingContext(ProneExitContext);
		}
		ProneExitSubsystem.Reset();
		return;
	}
	const ACharacter* Character = GetCharacter();
	const APlayerController* PC = Character ? Cast<APlayerController>(Character->GetController()) : nullptr;
	UEnhancedInputLocalPlayerSubsystem* Subsystem = PC && PC->IsLocalController() && PC->GetLocalPlayer()
		? ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(PC->GetLocalPlayer()) : nullptr;
	if (!Subsystem || !ProneAction || ProneExitKeys.IsEmpty() || ProneExitSubsystem.Get() == Subsystem)
	{
		return;
	}
	if (!ProneExitContext)
	{
		// ProneAction consumes its keys (bConsumeInput), so the lower-priority jump / traversal mapping never sees them.
		ProneExitContext = NewObject<UInputMappingContext>(this, TEXT("IMC_NinjaProneExit"), RF_Transient);
		for (const FKey& Key : ProneExitKeys)
		{
			ProneExitContext->MapKey(ProneAction, Key);
		}
	}
	Subsystem->AddMappingContext(ProneExitContext, ProneExitPriority);
	ProneExitSubsystem = Subsystem;
}

// ---------------------------------------------------------------- Crouch and crouch run

void UNinjaStanceComponent::UpdateMovementOverrides(float DeltaTime)
{
	ACharacter* Character = GetCharacter();
	UCharacterMovementComponent* Movement = Character ? Character->GetCharacterMovement() : nullptr;
	if (!Movement)
	{
		return;
	}
	// GASP's fresh crouch speed for this frame; if its pre-movement tick did not run, the field still holds this component's own
	// last write, and the previous GASP value stands.
	if (!FMath::IsNearlyEqual(Movement->MaxWalkSpeedCrouched, LastWrittenCrouchSpeed))
	{
		GaspCrouchSpeed = Movement->MaxWalkSpeedCrouched;
	}
	const ENetRole Role = Character->GetLocalRole();
	if (Role != ROLE_Authority && Role != ROLE_AutonomousProxy)
	{
		bCrouchRunning = false;
		return;
	}

	// The held crouch: down again after a landing, or after GASP's walk-off-ledge uncrouch.
	if (bCrouchHeld && !IsProne() && IsLocallyControlledPlayer() && Movement->IsMovingOnGround() && !Movement->bWantsToCrouch)
	{
		Character->Crouch();
	}

	bool bRun = false;
	if (Character->bIsCrouched && !IsProne() && Movement->IsMovingOnGround())
	{
		bool bWantsSprint = false;
		if (const FStructProperty* State = FindFProperty<FStructProperty>(Character->GetClass(), NinjaStanceConst::GaspInputStateProperty))
		{
			const void* StateValue = State->ContainerPtrToValuePtr<void>(Character);
			for (TFieldIterator<FBoolProperty> It(State->Struct); It; ++It)
			{
				if (It->GetName().StartsWith(NinjaStanceConst::GaspWantsToSprintPrefix))
				{
					bWantsSprint = It->GetPropertyValue_InContainer(StateValue);
					break;
				}
			}
		}
		if (bWantsSprint)
		{
			// GASP's CanSprint: this frame's input where it is known, the replicated acceleration on the server.
			FVector Direction = Character->IsLocallyControlled() ? Character->GetPendingMovementInputVector() : Movement->GetCurrentAcceleration();
			Direction.Z = 0.0;
			if (!Direction.IsNearlyZero())
			{
				const float Delta = static_cast<float>(FMath::Abs(FRotator::NormalizeAxis(Direction.Rotation().Yaw - Character->GetActorRotation().Yaw)));
				bRun = Movement->bOrientRotationToMovement || Delta < CrouchRunMaxAngle;
			}
		}
	}
	bCrouchRunning = bRun;

	float CrouchSpeed = GaspCrouchSpeed * (bRun ? CrouchRunSpeedMultiplier : 1.0f);
	if (IsProne())
	{
		CrouchSpeed = ProneMoveSpeed;
		// Also the standing speed, for the frame before the crouch takes effect.
		Movement->MaxWalkSpeed = ProneMoveSpeed;
		// No turning while lying (and while getting down or up): GASP would turn the capsule to the camera or the input.
		Movement->bUseControllerDesiredRotation = false;
		Movement->bOrientRotationToMovement = false;
	}
	Movement->MaxWalkSpeedCrouched = CrouchSpeed;
	LastWrittenCrouchSpeed = CrouchSpeed;
	// The input speed never drops below MinAnalogWalkSpeed (GASP: 150), whatever the caps: held W would crawl the lying body along.
	Movement->MinAnalogWalkSpeed = IsProne() ? FMath::Min(SavedMinAnalogWalkSpeed, ProneMoveSpeed) : SavedMinAnalogWalkSpeed;
}

void UNinjaStanceComponent::UpdateCrouchAnimRate(float DeltaTime)
{
	ACharacter* Character = GetCharacter();
	const UCharacterMovementComponent* Movement = Character ? Character->GetCharacterMovement() : nullptr;
	USkeletalMeshComponent* Body = Character ? Character->GetMesh() : nullptr;
	if (!Movement || !Body)
	{
		return;
	}
	// From the actual speed, so every machine (simulated proxies too) gets the same rate without replicating the crouch run. Only
	// eased inside the crouch band: leaving it (standing up, falling, prone, or a GASP traversal montage on the hidden mesh) snaps
	// back to 1 at once, so no leftover speed-up reaches the next animation or a traversal's root motion.
	const float Speed = static_cast<float>(Character->GetVelocity().Size2D());
	const UAnimInstance* BodyAnim = Body->GetAnimInstance();
	const bool bCrouchBand = Character->bIsCrouched && !IsProne() && Movement->IsMovingOnGround() && GaspCrouchSpeed > 1.0f
		&& !(BodyAnim && BodyAnim->IsSlotActive(NinjaVisual::FullBodySlot));
	if (bCrouchBand)
	{
		const float Target = FMath::Clamp(Speed / (GaspCrouchSpeed * CrouchAnimAssumedMaxPlayRate), 1.0f, CrouchAnimMaxRateScale);
		CrouchAnimRate = FMath::FInterpTo(CrouchAnimRate, Target, DeltaTime, CrouchAnimRateInterpSpeed);
		if (Target == 1.0f && FMath::IsNearlyEqual(CrouchAnimRate, 1.0f, 0.005f))
		{
			CrouchAnimRate = 1.0f;
		}
	}
	else
	{
		CrouchAnimRate = 1.0f;
	}
	if (Body->GlobalAnimRateScale != CrouchAnimRate)
	{
		Body->GlobalAnimRateScale = CrouchAnimRate;
	}

#if !UE_BUILD_SHIPPING
	if (CVarNinjaStanceDebug.GetValueOnGameThread() > 0 && Character->IsLocallyControlled() && DeltaTime > 0.0f)
	{
		// The planted foot is the slower of the two in world space; a clean contact is near 0 cm/s.
		const USkeletalMeshComponent* Visual = NinjaVisual::FindVisualMesh(Character);
		if (Visual)
		{
			const FVector Left = Visual->GetSocketLocation(TEXT("ball_l"));
			const FVector Right = Visual->GetSocketLocation(TEXT("ball_r"));
			float Planted = -1.0f;
			if (bDebugHasFeet)
			{
				Planted = static_cast<float>(FMath::Min(FVector::Dist2D(Left, DebugLastLeftFoot), FVector::Dist2D(Right, DebugLastRightFoot)) / DeltaTime);
			}
			DebugLastLeftFoot = Left;
			DebugLastRightFoot = Right;
			bDebugHasFeet = true;
			UE_LOG(LogNinjaStance, Log, TEXT("dbg crouched=%d run=%d speed=%.0f gaspCrouch=%.0f rate=%.2f planted=%.0f prone=%d"),
				Character->bIsCrouched ? 1 : 0, bCrouchRunning ? 1 : 0, Speed, GaspCrouchSpeed, CrouchAnimRate, Planted,
				static_cast<int32>(ProneState));
		}
	}
#endif
}

// ---------------------------------------------------------------- Prone

bool UNinjaStanceComponent::HasRoomToLieDown() const
{
	const ACharacter* Character = GetCharacter();
	const UWorld* World = GetWorld();
	const UCapsuleComponent* Capsule = Character ? Character->GetCapsuleComponent() : nullptr;
	if (!Capsule || !World)
	{
		return false;
	}
	const FVector Forward = FRotator(0.0f, static_cast<float>(Character->GetActorRotation().Yaw), 0.0f).Vector();
	const FVector Floor = Character->GetActorLocation() - FVector(0.0, 0.0, Capsule->GetScaledCapsuleHalfHeight());
	FCollisionQueryParams Params(SCENE_QUERY_STAT(NinjaProneRoom), false, Character);
	// The visible body is a child actor; clones and anything else attached do not count either.
	TArray<AActor*> Attached;
	Character->GetAttachedActors(Attached, true, true);
	Params.AddIgnoredActors(Attached);
	// The lying body: a flat box along the facing, lifted off the floor so the ground itself does not count.
	const float HalfLength = 0.5f * (ProneBodyFrontReach + ProneBodyBackReach);
	const FVector BoxCentre = Floor + Forward * (0.5f * (ProneBodyFrontReach - ProneBodyBackReach))
		+ FVector(0.0, 0.0, ProneBodyClearance + ProneBodyHalfHeight);
	const FQuat BoxRotation = FRotator(0.0f, static_cast<float>(Character->GetActorRotation().Yaw), 0.0f).Quaternion();
	if (World->OverlapBlockingTestByChannel(BoxCentre, BoxRotation, ECC_Pawn,
		FCollisionShape::MakeBox(FVector(HalfLength, ProneBodyHalfWidth, ProneBodyHalfHeight)), Params))
	{
		return false;
	}
	// Ground under both ends (not lying over a ledge).
	for (const float Reach : { ProneBodyFrontReach, -ProneBodyBackReach })
	{
		const FVector End = Floor + Forward * Reach;
		FHitResult Hit;
		if (!World->LineTraceSingleByChannel(Hit, End + FVector(0.0, 0.0, 50.0), End - FVector(0.0, 0.0, ProneMaxGroundDrop), ECC_Visibility, Params))
		{
			return false;
		}
	}
	return true;
}

bool UNinjaStanceComponent::CanLieDown() const
{
	const ACharacter* Character = GetCharacter();
	const UCharacterMovementComponent* Movement = Character ? Character->GetCharacterMovement() : nullptr;
	if (!Movement || !Movement->IsMovingOnGround())
	{
		return false;
	}
	// GASP plays its traversals (vault, mantle) as montages on its own animating mesh's DefaultSlot.
	const USkeletalMeshComponent* Body = Character->GetMesh();
	const UAnimInstance* BodyAnim = Body ? Body->GetAnimInstance() : nullptr;
	if (BodyAnim && BodyAnim->IsSlotActive(NinjaVisual::FullBodySlot))
	{
		return false;
	}
	const UNinjaJutsuComponent* Jutsu = Character->FindComponentByClass<UNinjaJutsuComponent>();
	if (Jutsu && (Jutsu->IsCastingJutsu() || Jutsu->IsFinishing()))
	{
		return false;
	}
	return HasRoomToLieDown();
}

void UNinjaStanceComponent::SetProne(bool bProne)
{
	ACharacter* Character = GetCharacter();
	if (!Character || bProne == bProneWanted || (bProne && !CanLieDown()))
	{
		return;
	}
	if (Character->HasAuthority())
	{
		bProneReplicated = bProne;
		ApplyProne(bProne);
	}
	else if (Character->IsLocallyControlled())
	{
		ApplyProne(bProne);
		ServerSetProne(bProne);
	}
}

void UNinjaStanceComponent::ServerSetProne_Implementation(bool bProne)
{
	if (bProne == bProneReplicated)
	{
		return;
	}
	if (bProne && !CanLieDown())
	{
		ClientRejectProne(bProneReplicated);
		return;
	}
	bProneReplicated = bProne;
	ApplyProne(bProne);
}

void UNinjaStanceComponent::ServerAbortProne_Implementation()
{
	// The owner fell out of it (it sees every fall first). Nothing to gain by cheating: Z already ends prone.
	bProneReplicated = false;
	AbortProne();
}

void UNinjaStanceComponent::ClientRejectProne_Implementation(bool bServerProne)
{
	if (bServerProne == bProneWanted)
	{
		return;
	}
	if (bServerProne)
	{
		ApplyProne(true);
	}
	else
	{
		AbortProne();
	}
}

void UNinjaStanceComponent::OnRep_ProneReplicated()
{
	// Before BeginPlay the visible mesh may not exist yet; BeginPlay applies the initial state.
	if (!HasBegunPlay())
	{
		return;
	}
	const ACharacter* Character = GetCharacter();
	const UCharacterMovementComponent* Movement = Character ? Character->GetCharacterMovement() : nullptr;
	if (!bProneReplicated && Movement && !Movement->IsMovingOnGround())
	{
		// Ended by a fall: no getting-up clip in mid-air.
		AbortProne();
		return;
	}
	ApplyProne(bProneReplicated);
}

float UNinjaStanceComponent::ClipDuration(const UAnimSequenceBase* Clip, float PlayRate)
{
	// The dynamic montage plays the clip at its own RateScale times the montage play rate.
	return Clip ? Clip->GetPlayLength() / FMath::Max(FMath::Abs(PlayRate * Clip->RateScale), 0.01f) : 0.0f;
}

void UNinjaStanceComponent::ApplyProne(bool bProne, bool bInstant)
{
	ACharacter* Character = GetCharacter();
	UWorld* World = GetWorld();
	if (!Character || !World)
	{
		return;
	}
	const UNinjaJutsuComponent* Jutsu = Character->FindComponentByClass<UNinjaJutsuComponent>();
	// Crouch is the owning machine's to change (its saved moves carry it to the server); a clone's follows its leader's.
	const bool bOwnsCrouch = Character->IsLocallyControlled() && !(Jutsu && Jutsu->IsShadowClone());
	USkeletalMeshComponent* Visual = NinjaVisual::FindVisualMesh(Character);
	bProneWanted = bProne;
	if (bProne)
	{
		if (ProneState == ENinjaProneState::Entering || ProneState == ENinjaProneState::Prone)
		{
			return;
		}
		if (bOwnsCrouch)
		{
			Character->Crouch();
		}
		if (IsLocallyControlledPlayer())
		{
			SetExitKeysActive(true);
		}
		if (bInstant)
		{
			// Already lying when this machine first sees it (a join, or the pawn becoming relevant again): straight to the idle.
			ProneState = ENinjaProneState::Entering;
			ProneClipEndTime = World->GetTimeSeconds();
			UpdateProne();
			return;
		}
		ProneState = ENinjaProneState::Entering;
		// Held on its last frame until the idle takes over (an auto blend-out would dip toward GASP's pose first).
		UAnimMontage* Montage = ProneEnterAnimation
			? NinjaVisual::PlaySlotMontage(Visual, ProneEnterAnimation, NinjaVisual::FullBodySlot, ProneEnterBlendIn, 0.0f, ProneEnterPlayRate,
				0.0f, /*bLoop*/ false, /*bAutoBlendOut*/ false)
			: nullptr;
		ProneMontage = Montage;
		ProneClipEndTime = World->GetTimeSeconds() + (Montage ? ClipDuration(ProneEnterAnimation, ProneEnterPlayRate) : 0.0f);
		return;
	}
	if (ProneState == ENinjaProneState::None || ProneState == ENinjaProneState::Exiting)
	{
		return;
	}
	ProneState = ENinjaProneState::Exiting;
	// Held on its last (crouched) frame; FinishExit blends it out together with the uncrouch.
	UAnimMontage* Montage = ProneExitAnimation
		? NinjaVisual::PlaySlotMontage(Visual, ProneExitAnimation, NinjaVisual::FullBodySlot, ProneExitBlendIn, ProneExitBlendOut, ProneExitPlayRate,
			0.0f, /*bLoop*/ false, /*bAutoBlendOut*/ false)
		: nullptr;
	ProneMontage = Montage;
	ProneClipEndTime = World->GetTimeSeconds() + (Montage ? ClipDuration(ProneExitAnimation, ProneExitPlayRate) : 0.0f);
}

void UNinjaStanceComponent::UpdateProne()
{
	if (ProneState == ENinjaProneState::None)
	{
		return;
	}
	ACharacter* Character = GetCharacter();
	const UCharacterMovementComponent* Movement = Character ? Character->GetCharacterMovement() : nullptr;
	const UWorld* World = GetWorld();
	if (!Movement || !World)
	{
		return;
	}
	// Knocked or walked off an edge. The machine that moves the pawn decides: the owner sees every fall first (one the server
	// causes reaches it as a correction carrying the falling mode) and tells the server, so the two cannot disagree. The server
	// decides for its own pawns and AI clones; simulated proxies follow the replicated state.
	if (!Movement->IsMovingOnGround() && Character->GetLocalRole() != ROLE_SimulatedProxy)
	{
		if (Character->HasAuthority())
		{
			if (Character->IsPlayerControlled() && !Character->IsLocallyControlled())
			{
				return;
			}
			bProneReplicated = false;
		}
		else
		{
			ServerAbortProne();
		}
		AbortProne();
		return;
	}
	if (World->GetTimeSeconds() < ProneClipEndTime)
	{
		return;
	}
	if (ProneState == ENinjaProneState::Entering)
	{
		ProneState = ENinjaProneState::Prone;
		// Its blend-out time only matters if something else stops it; getting up replaces it with the exit clip's blend-in.
		ProneMontage = ProneIdleAnimation
			? NinjaVisual::PlaySlotMontage(NinjaVisual::FindVisualMesh(Character), ProneIdleAnimation, NinjaVisual::FullBodySlot, ProneIdleBlendIn,
				ProneExitBlendIn, 1.0f, 0.0f, /*bLoop*/ true)
			: nullptr;
	}
	else if (ProneState == ENinjaProneState::Exiting)
	{
		FinishExit(ProneExitBlendOut);
	}
}

void UNinjaStanceComponent::FinishExit(float BlendOutTime)
{
	ProneState = ENinjaProneState::None;
	bProneWanted = false;
	SetExitKeysActive(false);
	ACharacter* Character = GetCharacter();
	const USkeletalMeshComponent* Visual = NinjaVisual::FindVisualMesh(Character);
	UAnimInstance* VisualAnim = Visual ? Visual->GetAnimInstance() : nullptr;
	if (UAnimMontage* Montage = ProneMontage.Get(); Montage && VisualAnim)
	{
		VisualAnim->Montage_Stop(BlendOutTime, Montage);
	}
	ProneMontage.Reset();
	const UNinjaJutsuComponent* Jutsu = Character ? Character->FindComponentByClass<UNinjaJutsuComponent>() : nullptr;
	if (Character && Character->IsLocallyControlled() && !(Jutsu && Jutsu->IsShadowClone()) && !bCrouchHeld)
	{
		Character->UnCrouch();
	}
}

void UNinjaStanceComponent::AbortProne()
{
	if (ProneState == ENinjaProneState::None)
	{
		bProneWanted = false;
		return;
	}
	FinishExit(FMath::Min(ProneExitBlendOut, 0.1f));
}
