// Copyright Epic Games, Inc. All Rights Reserved.

#include "NinjaJutsuComponent.h"

#include "AIController.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimSequenceBase.h"
#include "Components/AudioComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "InputAction.h"
#include "InputMappingContext.h"
#include "Kismet/GameplayStatics.h"
#include "NiagaraFunctionLibrary.h"
#include "NinjaFireball.h"
#include "NinjaHandEffect.h"
#include "NinjaJutsu.h"
#include "NinjaLockOnComponent.h"
#include "NinjaStanceComponent.h"
#include "NinjaVisual.h"
#include "Sound/SoundBase.h"

DEFINE_LOG_CATEGORY_STATIC(LogNinjaJutsu, Log, All);

namespace NinjaJutsuConst
{
	/** Held poses outlive their hold plus the next blend by this much, so a seal never ends before its successor has blended in. */
	constexpr float SealMontagePadding = 0.1f;
	constexpr float SealBlendOutTime = 0.1f;
	const FName HeadBone(TEXT("head"));
	/** GASP's CMC character keeps its gait inputs (Wants To Sprint / Walk / Strafe) in this Blueprint struct; clones copy it. */
	const FName GaspInputStateProperty(TEXT("CharacterInputState"));
}

UNinjaJutsuComponent::UNinjaJutsuComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	// After the character's movement this frame, so a clone copies the input its leader has just consumed.
	PrimaryComponentTick.TickGroup = TG_PostPhysics;
}

ACharacter* UNinjaJutsuComponent::GetCharacter() const
{
	return Cast<ACharacter>(GetOwner());
}

double UNinjaJutsuComponent::Now() const
{
	const UWorld* World = GetWorld();
	return World ? World->GetTimeSeconds() : 0.0;
}

USkeletalMeshComponent* UNinjaJutsuComponent::GetVisualMesh() const
{
	return NinjaVisual::FindVisualMesh(GetOwner());
}

ACharacter* UNinjaJutsuComponent::GetCloneLeader() const
{
	return CloneLeader.Get();
}

const AActor* UNinjaJutsuComponent::GetSideLeader(const AActor* Actor)
{
	const UNinjaJutsuComponent* Jutsu = Actor ? Actor->FindComponentByClass<UNinjaJutsuComponent>() : nullptr;
	if (Jutsu && Jutsu->bIsShadowClone && Jutsu->CloneLeader.IsValid())
	{
		return Jutsu->CloneLeader.Get();
	}
	return Actor;
}

void UNinjaJutsuComponent::BeginPlay()
{
	Super::BeginPlay();
	if (const ACharacter* Character = GetCharacter())
	{
		SavedJumpMaxCount = Character->JumpMaxCount;
	}
}

void UNinjaJutsuComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	// A held effect is attached to this character's mesh; don't leave it orphaned in the world.
	if (AActor* Effect = FinisherEffect.Get())
	{
		FinisherEffect.Reset();
		Effect->Destroy();
	}
	SetFinisherLock(false);
	if (!bIsShadowClone)
	{
		for (const TWeakObjectPtr<ACharacter>& Clone : TArray<TWeakObjectPtr<ACharacter>>(Clones))
		{
			ACharacter* CloneCharacter = Clone.Get();
			if (!IsValid(CloneCharacter))
			{
				continue;
			}
			UNinjaJutsuComponent* CloneJutsu = CloneCharacter->FindComponentByClass<UNinjaJutsuComponent>();
			if (EndPlayReason == EEndPlayReason::Destroyed && CloneJutsu)
			{
				CloneJutsu->DispelClone();
			}
			else
			{
				CloneCharacter->Destroy();
			}
		}
		Clones.Reset();
	}
	Super::EndPlay(EndPlayReason);
}

void UNinjaJutsuComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	UpdateInputBinding();
	if (bIsShadowClone)
	{
		UpdateClone();
		if (!IsValid(this) || !GetOwner() || GetOwner()->IsActorBeingDestroyed())
		{
			return;
		}
	}
	UpdateJutsu(DeltaTime);
}

// ---------------------------------------------------------------- Input

void UNinjaJutsuComponent::UpdateInputBinding()
{
	const APawn* Pawn = Cast<APawn>(GetOwner());
	UInputComponent* Input = Pawn ? Pawn->InputComponent.Get() : nullptr;
	APlayerController* PC = Pawn ? Cast<APlayerController>(Pawn->GetController()) : nullptr;
	if (bIsShadowClone || !Input || !PC || !PC->IsLocalController())
	{
		BoundInputComponent.Reset();
		return;
	}
	if (BoundInputComponent.Get() == Input)
	{
		return;
	}
	BoundInputComponent = Input;
	if (UEnhancedInputComponent* Enhanced = Cast<UEnhancedInputComponent>(Input))
	{
		for (int32 Index = 0; Index < Jutsus.Num(); ++Index)
		{
			if (Jutsus[Index] && Jutsus[Index]->InputAction)
			{
				Enhanced->BindAction(Jutsus[Index]->InputAction, ETriggerEvent::Started, this, &UNinjaJutsuComponent::OnJutsuInput, Index);
			}
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

void UNinjaJutsuComponent::OnJutsuInput(int32 JutsuIndex)
{
	UNinjaJutsu* Jutsu = Jutsus.IsValidIndex(JutsuIndex) ? Jutsus[JutsuIndex].Get() : nullptr;
	const bool bWasCasting = bIsCastingJutsu;
	StartJutsu(Jutsu);
	// Mirror only a press that started a cast here: an ignored press must not restart an idle clone.
	if (!bWasCasting && bIsCastingJutsu && CastingJutsu == Jutsu)
	{
		ForEachClone([Jutsu](UNinjaJutsuComponent& Clone)
		{
			Clone.CancelFinisher();
			Clone.CancelJutsu();
			Clone.StartJutsu(Jutsu);
		});
	}
}

void UNinjaJutsuComponent::StartJutsuByIndex(int32 Index)
{
	if (Jutsus.IsValidIndex(Index))
	{
		StartJutsu(Jutsus[Index]);
	}
}

// ---------------------------------------------------------------- Seal chain

bool UNinjaJutsuComponent::CanStartJutsu() const
{
	const ACharacter* Character = GetCharacter();
	const UCharacterMovementComponent* Movement = Character ? Character->GetCharacterMovement() : nullptr;
	if (!Movement || !Movement->IsMovingOnGround())
	{
		return false;
	}
	// Not while lying down, getting down or getting up (the seal layer would bend a prone body's spine upright).
	if (const UNinjaStanceComponent* Stance = Character->FindComponentByClass<UNinjaStanceComponent>(); Stance && Stance->IsProne())
	{
		return false;
	}
	// GASP plays its traversal (vault, mantle) as montages on its own animating mesh's DefaultSlot; don't sign through one.
	const UAnimInstance* BodyAnim = Character->GetMesh() ? Character->GetMesh()->GetAnimInstance() : nullptr;
	return !BodyAnim || !BodyAnim->IsSlotActive(NinjaVisual::FullBodySlot);
}

void UNinjaJutsuComponent::StartJutsu(UNinjaJutsu* Jutsu)
{
	const int32 FirstSeal = FindNextSeal(Jutsu, 0);
	if (bIsCastingJutsu || FinishingJutsu || FirstSeal == INDEX_NONE || !CanStartJutsu())
	{
		return;
	}
	USkeletalMeshComponent* Visual = GetVisualMesh();
	if (!Visual || !Visual->GetAnimInstance())
	{
		return;
	}
	bIsCastingJutsu = true;
	CastingJutsu = Jutsu;
	// The voice line starts with the hand signs (Cody, 2026-09-19); a previous line still talking is cut first.
	StopJutsuVoice(0.1f);
	if (Jutsu->StartVoice && !bIsShadowClone)
	{
		JutsuVoice = UGameplayStatics::SpawnSoundAttached(Jutsu->StartVoice, Visual, NAME_None,
			FVector::ZeroVector, EAttachLocation::KeepRelativeOffset, true, Jutsu->StartVoiceVolume);
		UE_LOG(LogNinjaJutsu, Log, TEXT("%s: voice %s for %s (%s)"), *GetNameSafe(GetOwner()), *GetNameSafe(Jutsu->StartVoice),
			*GetNameSafe(Jutsu), JutsuVoice.IsValid() ? TEXT("playing") : TEXT("not spawned"));
	}
	// The opening pose (e.g. biting the thumb) holds with SealIndex at INDEX_NONE, so UpdateJutsu moves on to seal 0.
	if (Jutsu->OpeningAnimation && PlayHeldPose(Jutsu->OpeningAnimation, Jutsu->OpeningHoldTime))
	{
		SealIndex = INDEX_NONE;
		NextSealTime = Now() + Jutsu->OpeningHoldTime;
		return;
	}
	PlaySeal(FirstSeal);
}

void UNinjaJutsuComponent::CancelJutsu()
{
	if (!bIsCastingJutsu)
	{
		return;
	}
	// The arm layer fades out in UpdateJutsu; the seal montage is stopped once it is fully hidden.
	UNinjaJutsu* CancelledJutsu = CastingJutsu;
	const int32 CancelledSealIndex = SealIndex;
	bIsCastingJutsu = false;
	CastingJutsu = nullptr;
	SealIndex = INDEX_NONE;
	// A jutsu that never happens does not finish its name.
	StopJutsuVoice(0.15f);
	OnJutsuCancelled.Broadcast(CancelledJutsu, CancelledSealIndex);
}

void UNinjaJutsuComponent::StopJutsuVoice(float FadeOutTime)
{
	if (UAudioComponent* Voice = JutsuVoice.Get(); Voice && Voice->IsPlaying())
	{
		Voice->FadeOut(FadeOutTime, 0.0f);
	}
	JutsuVoice.Reset();
}

int32 UNinjaJutsuComponent::FindNextSeal(const UNinjaJutsu* Jutsu, int32 FromIndex) const
{
	if (!Jutsu)
	{
		return INDEX_NONE;
	}
	for (int32 Index = FMath::Max(FromIndex, 0); Index < Jutsu->Seals.Num(); ++Index)
	{
		const UAnimSequenceBase* Seal = Jutsu->Seals[Index];
		if (Seal && Seal->GetPlayLength() > UE_KINDA_SMALL_NUMBER)
		{
			return Index;
		}
	}
	return INDEX_NONE;
}

void UNinjaJutsuComponent::PlaySeal(int32 Index)
{
	SealIndex = Index;
	const bool bLastSeal = FindNextSeal(CastingJutsu, Index + 1) == INDEX_NONE;
	const float HoldTime = bLastSeal ? FinalSealHoldTime : SealHoldTime;
	NextSealTime = Now() + HoldTime;

	UAnimSequenceBase* Seal = CastingJutsu->Seals[Index];
	if (!PlayHeldPose(Seal, HoldTime))
	{
		UE_LOG(LogNinjaJutsu, Warning, TEXT("%s: could not play jutsu seal %d (%s)."), *GetNameSafe(GetOwner()), Index, *GetNameSafe(Seal));
		CancelJutsu();
		return;
	}
	PlayJutsuSound(SealSound, SealSoundVolume, SealSoundPitchVariation);
	OnJutsuSeal.Broadcast(CastingJutsu, Index);
}

UAnimMontage* UNinjaJutsuComponent::PlayHeldPose(UAnimSequenceBase* Pose, float HoldTime)
{
	if (!Pose || Pose->GetPlayLength() <= UE_KINDA_SMALL_NUMBER)
	{
		return nullptr;
	}
	// With the arms down the pose comes in through the layer weight; otherwise cross-fade from the held pose.
	const float BlendIn = SealLayerWeight <= 0.0f ? 0.0f : SealBlendTime;
	// Stretch each pose so it outlives its hold plus the blend into whatever comes next.
	const float Lifetime = HoldTime + FMath::Max(SealBlendTime, SealLayerBlendTime) + NinjaJutsuConst::SealMontagePadding;
	return NinjaVisual::PlaySlotMontage(GetVisualMesh(), Pose, NinjaVisual::UpperBodySlot, BlendIn, NinjaJutsuConst::SealBlendOutTime,
		Pose->GetPlayLength() / Lifetime);
}

void UNinjaJutsuComponent::UpdateJutsu(float DeltaSeconds)
{
	const ACharacter* Character = GetCharacter();
	const UCharacterMovementComponent* Movement = Character ? Character->GetCharacterMovement() : nullptr;
	if (bIsCastingJutsu && (!Movement || !Movement->IsMovingOnGround()))
	{
		CancelJutsu();
	}
	if (bIsCastingJutsu && Now() >= NextSealTime)
	{
		const int32 NextSeal = FindNextSeal(CastingJutsu, SealIndex + 1);
		if (NextSeal != INDEX_NONE)
		{
			PlaySeal(NextSeal);
		}
		else
		{
			FinishSeals();
		}
	}
	UpdateFinisher();

	const float TargetWeight = bIsCastingJutsu ? 1.0f : 0.0f;
	const float PreviousWeight = SealLayerWeight;
	SealLayerWeight = FMath::FInterpConstantTo(SealLayerWeight, TargetWeight, DeltaSeconds, 1.0f / FMath::Max(SealLayerBlendTime, 0.01f));
	if (PreviousWeight <= 0.0f && SealLayerWeight <= 0.0f)
	{
		return;
	}
	USkeletalMeshComponent* Visual = GetVisualMesh();
	UAnimInstance* AnimInstance = Visual ? Visual->GetAnimInstance() : nullptr;
	NinjaVisual::SetAnimFloat(AnimInstance, NinjaVisual::SealWeightVariable, SealLayerWeight);
	// The layer is hidden now: clear the slot (its source is the retargeted body, so an empty slot is harmless, but a stale
	// seal must not linger for the next cast).
	if (!bIsCastingJutsu && PreviousWeight > 0.0f && SealLayerWeight <= 0.0f && AnimInstance)
	{
		AnimInstance->StopSlotAnimation(0.0f, NinjaVisual::UpperBodySlot);
	}
}

void UNinjaJutsuComponent::FinishSeals()
{
	UNinjaJutsu* Jutsu = CastingJutsu;
	bIsCastingJutsu = false;
	CastingJutsu = nullptr;
	SealIndex = INDEX_NONE;
	if (!Jutsu)
	{
		return;
	}

	// Finish the clones' copies first, on this frame: a clone ticks after its leader and would see the leader no longer casting
	// and cancel before releasing; and a ShadowClone release below may dispel the oldest clone, which must not vanish mid-chain.
	if (!bIsShadowClone)
	{
		ForEachClone([Jutsu](UNinjaJutsuComponent& Clone)
		{
			if (Clone.bIsCastingJutsu && Clone.CastingJutsu == Jutsu && Clone.CanStartJutsu())
			{
				Clone.FinishSeals();
			}
		});
	}

	if (Jutsu->FinisherAnimation)
	{
		const float PlayRate = FMath::Max(Jutsu->FinisherPlayRate, 0.05f);
		// Full body on DefaultSlot; the arm layer fades out underneath it over SealLayerBlendTime.
		if (const UAnimMontage* Montage = NinjaVisual::PlaySlotMontage(GetVisualMesh(), Jutsu->FinisherAnimation, NinjaVisual::FullBodySlot,
			Jutsu->FinisherBlendInTime, Jutsu->FinisherBlendOutTime, PlayRate))
		{
			SetFinisherLock(true);
			FinishingJutsu = Jutsu;
			bFinisherReleased = false;
			// The montage segment already includes the clip's RateScale; FinisherReleaseTime is authored in clip seconds.
			const float ClipRate = FMath::IsNearlyZero(Jutsu->FinisherAnimation->RateScale) ? 1.0f : FMath::Abs(Jutsu->FinisherAnimation->RateScale);
			const float Length = Montage->GetPlayLength() / PlayRate;
			const float ReleaseOffset = FMath::Min(Jutsu->FinisherReleaseTime / (PlayRate * ClipRate), Length);
			const double Time = Now();
			FinisherReleaseAt = Time + ReleaseOffset;
			// Actions unlock as the finisher starts blending out, but never before the release.
			FinisherEndAt = Time + FMath::Max(Length - Jutsu->FinisherBlendOutTime, ReleaseOffset);
			UpdateFinisher();
			return;
		}
		UE_LOG(LogNinjaJutsu, Warning, TEXT("%s: could not play the finisher %s; releasing without it."), *GetNameSafe(GetOwner()), *GetNameSafe(Jutsu->FinisherAnimation));
	}
	CompleteJutsu(Jutsu);
}

void UNinjaJutsuComponent::UpdateFinisher()
{
	if (!FinishingJutsu)
	{
		return;
	}
	// Off the ground ends it: a fall, or a GASP traversal (MOVE_Flying) the finisher's key block missed.
	const ACharacter* Character = GetCharacter();
	if (!Character || !Character->GetCharacterMovement() || !Character->GetCharacterMovement()->IsMovingOnGround())
	{
		CancelFinisher();
		return;
	}
	const double Time = Now();
	if (!bFinisherReleased && (Time >= FinisherReleaseAt || Time >= FinisherEndAt))
	{
		UNinjaJutsu* Jutsu = FinishingJutsu;
		bFinisherReleased = true;
		// Release the clones' copies first (they share this release time), for the same reasons FinishSeals finishes them first.
		if (!bIsShadowClone)
		{
			ForEachClone([Jutsu](UNinjaJutsuComponent& Clone)
			{
				if (Clone.FinishingJutsu == Jutsu && !Clone.bFinisherReleased)
				{
					Clone.bFinisherReleased = true;
					Clone.CompleteJutsu(Jutsu);
				}
			});
		}
		CompleteJutsu(Jutsu);
	}
	if (FinishingJutsu && Time >= FinisherEndAt)
	{
		FinishingJutsu = nullptr;
		SetFinisherLock(false);
		StopFinisherEffect();
	}
}

void UNinjaJutsuComponent::CancelFinisher()
{
	if (!FinishingJutsu)
	{
		return;
	}
	UNinjaJutsu* CancelledJutsu = FinishingJutsu;
	const bool bWasReleased = bFinisherReleased;
	FinishingJutsu = nullptr;
	SetFinisherLock(false);
	StopFinisherEffect();
	NinjaVisual::StopSlotMontages(GetVisualMesh(), NinjaVisual::FullBodySlot, CancelledJutsu->FinisherBlendOutTime);
	if (!bWasReleased)
	{
		StopJutsuVoice(0.15f);
		// A clone never releases a jutsu its leader failed to release.
		if (!bIsShadowClone)
		{
			ForEachClone([CancelledJutsu](UNinjaJutsuComponent& Clone)
			{
				if (Clone.FinishingJutsu == CancelledJutsu && !Clone.bFinisherReleased)
				{
					Clone.CancelFinisher();
				}
			});
		}
		OnJutsuCancelled.Broadcast(CancelledJutsu, INDEX_NONE);
	}
}

void UNinjaJutsuComponent::SetFinisherLock(bool bLock)
{
	ACharacter* Character = GetCharacter();
	if (!Character || bLock == bFinisherLock)
	{
		return;
	}
	bFinisherLock = bLock;
	if (bLock)
	{
		// Planted: a character signing on the run stops dead instead of sliding with its hand on the floor, and cannot jump away
		// (GASP's own speed code rewrites MaxWalkSpeed every tick, so the lock goes through the controller's move input; the jump
		// keys are swallowed before GASP's jump / traversal handler sees them; JumpMaxCount 0 is a local backstop).
		SavedJumpMaxCount = Character->JumpMaxCount;
		Character->JumpMaxCount = 0;
		if (UCharacterMovementComponent* Movement = Character->GetCharacterMovement())
		{
			Movement->StopMovementImmediately();
		}
		if (AController* Controller = Character->GetController())
		{
			Controller->SetIgnoreMoveInput(true);
			LockedController = Controller;
			SetFinisherKeysBlocked(Controller, true);
		}
		return;
	}
	Character->JumpMaxCount = SavedJumpMaxCount;
	// SetIgnoreMoveInput counts: undo exactly the controller that was locked, even if the character was re-possessed since.
	if (AController* Controller = LockedController.Get())
	{
		Controller->SetIgnoreMoveInput(false);
	}
	LockedController.Reset();
	SetFinisherKeysBlocked(nullptr, false);
}

void UNinjaJutsuComponent::SetFinisherKeysBlocked(AController* Controller, bool bBlocked)
{
	if (!bBlocked)
	{
		if (UEnhancedInputLocalPlayerSubsystem* Subsystem = FinisherBlockSubsystem.Get(); Subsystem && FinisherBlockContext)
		{
			// The default options ignore keys still held until they are released, so a Space held through the finisher does not
			// jump the moment it ends.
			Subsystem->RemoveMappingContext(FinisherBlockContext);
		}
		FinisherBlockSubsystem.Reset();
		return;
	}
	const APlayerController* PC = Cast<APlayerController>(Controller);
	UEnhancedInputLocalPlayerSubsystem* Subsystem = PC && PC->IsLocalController() && PC->GetLocalPlayer()
		? ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(PC->GetLocalPlayer()) : nullptr;
	if (!Subsystem || FinisherBlockedKeys.IsEmpty())
	{
		return;
	}
	if (!FinisherBlockContext)
	{
		// A mapping only consumes its key for lower-priority contexts when its action has bConsumeInput (the default); nothing
		// binds this action, so the press simply ends here.
		FinisherBlockAction = NewObject<UInputAction>(this, TEXT("IA_NinjaFinisherBlock"), RF_Transient);
		FinisherBlockAction->bConsumeInput = true;
		FinisherBlockContext = NewObject<UInputMappingContext>(this, TEXT("IMC_NinjaFinisherBlock"), RF_Transient);
		for (const FKey& Key : FinisherBlockedKeys)
		{
			FinisherBlockContext->MapKey(FinisherBlockAction, Key);
		}
	}
	Subsystem->AddMappingContext(FinisherBlockContext, FinisherBlockPriority);
	FinisherBlockSubsystem = Subsystem;
}

void UNinjaJutsuComponent::CompleteJutsu(UNinjaJutsu* Jutsu)
{
	if (!Jutsu)
	{
		return;
	}
	if (Jutsu->bPlayCompleteSound)
	{
		PlayJutsuSound(Jutsu->CompleteSound ? Jutsu->CompleteSound.Get() : JutsuCompleteSound.Get(), JutsuCompleteVolume, 0.0f);
	}
	switch (Jutsu->Release)
	{
	case ENinjaJutsuRelease::ShadowClone:
		if (!bIsShadowClone)
		{
			SpawnShadowClone();
		}
		break;
	case ENinjaJutsuRelease::Fireball:
		ReleaseFireball(*Jutsu);
		break;
	default:
		break;
	}

	// Held effects (the Chidori lightning) only exist while a finisher plays; they stop when it ends or is cancelled.
	if (FinishingJutsu == Jutsu && Jutsu->FinisherEffectClass)
	{
		SpawnFinisherEffect(*Jutsu);
	}

	const USkeletalMeshComponent* Visual = GetVisualMesh();
	if (!Jutsu->FinisherHandBone.IsNone() && Visual && Visual->DoesSocketExist(Jutsu->FinisherHandBone))
	{
		const FVector Ground = FindGroundUnderHand(Jutsu->FinisherHandBone);
		const FRotator Facing(0.0f, GetOwner()->GetActorRotation().Yaw, 0.0f);
		if (UWorld* World = GetWorld(); World && Jutsu->HandPlantedEffectClass)
		{
			FActorSpawnParameters Params;
			Params.Owner = GetOwner();
			Params.Instigator = Cast<APawn>(GetOwner());
			Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			World->SpawnActor<AActor>(Jutsu->HandPlantedEffectClass, Ground, Facing, Params);
		}
		OnJutsuHandPlanted.Broadcast(Jutsu, Ground, Facing);
	}
	OnJutsuCompleted.Broadcast(Jutsu);
}

void UNinjaJutsuComponent::SpawnFinisherEffect(const UNinjaJutsu& Jutsu)
{
	UWorld* World = GetWorld();
	USkeletalMeshComponent* Visual = GetVisualMesh();
	if (!World || !Visual || !Jutsu.FinisherEffectClass)
	{
		return;
	}
	StopFinisherEffect();
	FActorSpawnParameters Params;
	Params.Owner = GetOwner();
	Params.Instigator = Cast<APawn>(GetOwner());
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	AActor* Effect = World->SpawnActor<AActor>(Jutsu.FinisherEffectClass, GetOwner()->GetActorTransform(), Params);
	if (!Effect)
	{
		return;
	}
	const FName Bone = Visual->DoesSocketExist(Jutsu.FinisherEffectBone) ? Jutsu.FinisherEffectBone : NAME_None;
	Effect->AttachToComponent(Visual, FAttachmentTransformRules::SnapToTargetNotIncludingScale, Bone);
	Effect->SetActorRelativeLocation(Jutsu.FinisherEffectOffset);
	FinisherEffect = Effect;
}

void UNinjaJutsuComponent::StopFinisherEffect()
{
	AActor* Effect = FinisherEffect.Get();
	FinisherEffect.Reset();
	if (!IsValid(Effect))
	{
		return;
	}
	if (ANinjaHandEffect* HandEffect = Cast<ANinjaHandEffect>(Effect))
	{
		HandEffect->StopEffect();
	}
	else
	{
		Effect->Destroy();
	}
}

FVector UNinjaJutsuComponent::FindGroundUnderHand(FName HandBone) const
{
	const ACharacter* Character = GetCharacter();
	const USkeletalMeshComponent* Visual = GetVisualMesh();
	const UWorld* World = GetWorld();
	if (!Character || !Visual || !World)
	{
		return GetOwner() ? GetOwner()->GetActorLocation() : FVector::ZeroVector;
	}
	const FVector Hand = Visual->GetSocketLocation(HandBone);
	const FVector Center = Character->GetActorLocation();
	const float FeetZ = Center.Z - Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	FCollisionQueryParams Params(SCENE_QUERY_STAT(NinjaHandPlanted), false, Character);

	// Start the down trace from a point known to be free: level with the capsule centre above the hand, pulled back out of any
	// wall between the body and the hand.
	FVector Above(Hand.X, Hand.Y, Center.Z);
	FHitResult Hit;
	if (World->LineTraceSingleByChannel(Hit, Center, Above, ECC_Visibility, Params))
	{
		Above = Hit.Location - (Above - Center).GetSafeNormal2D() * 5.0f;
	}
	const float Reach = Character->GetCharacterMovement()->MaxStepHeight + 60.0f;
	if (World->LineTraceSingleByChannel(Hit, Above, FVector(Above.X, Above.Y, FeetZ - Reach), ECC_Visibility, Params) && !Hit.bStartPenetrating)
	{
		return Hit.ImpactPoint;
	}
	const FFindFloorResult& Floor = Character->GetCharacterMovement()->CurrentFloor;
	return FVector(Above.X, Above.Y, Floor.bBlockingHit ? Floor.HitResult.ImpactPoint.Z : FeetZ);
}

void UNinjaJutsuComponent::ReleaseFireball(const UNinjaJutsu& Jutsu)
{
	UWorld* World = GetWorld();
	ACharacter* Character = GetCharacter();
	if (!World || !Character || !Jutsu.FireballClass)
	{
		return;
	}
	// Breathe the fire where the player is looking; a clone aims with its leader's camera.
	const ACharacter* Aimer = bIsShadowClone && CloneLeader.IsValid() ? CloneLeader.Get() : Character;
	const float AimYaw = Aimer->GetController() ? Aimer->GetController()->GetControlRotation().Yaw : Character->GetActorRotation().Yaw;
	const FRotator Facing(0.0f, AimYaw, 0.0f);
	Character->SetActorRotation(Facing);

	const USkeletalMeshComponent* Visual = GetVisualMesh();
	const FVector Head = Visual && Visual->DoesSocketExist(NinjaJutsuConst::HeadBone) ? Visual->GetSocketLocation(NinjaJutsuConst::HeadBone)
		: Character->GetPawnViewLocation();
	const FVector SpawnLocation = Head + Facing.RotateVector(Jutsu.FireballSpawnOffset);
	FActorSpawnParameters Params;
	Params.Owner = Character;
	Params.Instigator = Character;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	// No null check: a fireball fired point-blank into an enemy bursts during BeginPlay, and SpawnActor then returns null.
	World->SpawnActor<ANinjaFireball>(Jutsu.FireballClass, SpawnLocation, Facing, Params);
}

void UNinjaJutsuComponent::PlayJutsuSound(USoundBase* Sound, float Volume, float PitchVariation) const
{
	// Clones sign silently so their seals don't double up with the leader's.
	USkeletalMeshComponent* Visual = GetVisualMesh();
	if (Sound && Visual && !bIsShadowClone)
	{
		const float Pitch = 1.0f + FMath::FRandRange(-PitchVariation, PitchVariation);
		UGameplayStatics::SpawnSoundAttached(Sound, Visual, NAME_None, FVector::ZeroVector, EAttachLocation::KeepRelativeOffset, true, Volume, Pitch);
	}
}

// ---------------------------------------------------------------- Shadow clones

void UNinjaJutsuComponent::ForEachClone(TFunctionRef<void(UNinjaJutsuComponent&)> Fn)
{
	PruneClones();
	for (const TWeakObjectPtr<ACharacter>& Clone : TArray<TWeakObjectPtr<ACharacter>>(Clones))
	{
		if (ACharacter* CloneCharacter = Clone.Get())
		{
			if (UNinjaJutsuComponent* CloneJutsu = CloneCharacter->FindComponentByClass<UNinjaJutsuComponent>())
			{
				Fn(*CloneJutsu);
			}
		}
	}
}

void UNinjaJutsuComponent::SpawnShadowClone()
{
	UWorld* World = GetWorld();
	ACharacter* Character = GetCharacter();
	if (!World || !Character || bIsShadowClone || MaxClones <= 0)
	{
		return;
	}
	PruneClones();
	while (Clones.Num() >= MaxClones)
	{
		ACharacter* Oldest = Clones[0].Get();
		Clones.RemoveAt(0);
		if (UNinjaJutsuComponent* OldestJutsu = Oldest ? Oldest->FindComponentByClass<UNinjaJutsuComponent>() : nullptr)
		{
			OldestJutsu->DispelClone();
		}
	}

	const FRotator Facing(0.0f, Character->GetActorRotation().Yaw, 0.0f);
	FVector Location = Character->GetActorLocation() + Facing.RotateVector(CloneSpawnOffset);
	if (!World->FindTeleportSpot(Character, Location, Facing))
	{
		Location = Character->GetActorLocation() + Facing.RotateVector(CloneSpawnOffset);
	}
	const FTransform SpawnTransform(Facing, Location);
	ACharacter* Clone = World->SpawnActorDeferred<ACharacter>(Character->GetClass(), SpawnTransform, Character, nullptr,
		ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn);
	if (!Clone)
	{
		UE_LOG(LogNinjaJutsu, Warning, TEXT("%s: failed to spawn a shadow clone."), *GetNameSafe(Character));
		return;
	}
	Clone->AutoPossessPlayer = EAutoReceiveInput::Disabled;
	Clone->AutoPossessAI = EAutoPossessAI::Spawned;
	Clone->AIControllerClass = AAIController::StaticClass();
	// Clones read their leader's state each tick; ticking after it makes that read see this frame's input and casts.
	Clone->AddTickPrerequisiteActor(Character);
	Clone->FinishSpawning(SpawnTransform);
	if (!IsValid(Clone))
	{
		return;
	}
	if (!Clone->GetController())
	{
		Clone->SpawnDefaultController();
	}
	if (!Clone->GetController())
	{
		// SpawnDefaultController does nothing on a network client, where the jutsu (and so this clone) is local: possess it here,
		// or it never runs its movement. The controller is ours to destroy in DispelClone.
		FActorSpawnParameters ControllerParams;
		ControllerParams.Instigator = Clone;
		ControllerParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		ControllerParams.OverrideLevel = Clone->GetLevel();
		ControllerParams.ObjectFlags |= RF_Transient;
		if (AAIController* LocalAI = World->SpawnActor<AAIController>(AAIController::StaticClass(), Clone->GetActorLocation(),
			Clone->GetActorRotation(), ControllerParams))
		{
			LocalAI->Possess(Clone);
		}
	}
	if (AAIController* CloneAI = Cast<AAIController>(Clone->GetController()))
	{
		// Keep the control rotation UpdateClone copies from the leader (GASP's strafe and aim face it); by default an AI controller
		// resets it to the pawn's own yaw every tick, before the movement component reads it.
		CloneAI->bSetControlRotationFromPawnOrientation = false;
		CloneAI->SetControlRotation(Character->GetControlRotation());
	}
	// Blueprint-added components exist only after FinishSpawning, so the clone is marked here.
	UNinjaJutsuComponent* CloneJutsu = Clone->FindComponentByClass<UNinjaJutsuComponent>();
	if (!CloneJutsu)
	{
		Clone->Destroy();
		return;
	}
	CloneJutsu->bIsShadowClone = true;
	CloneJutsu->CloneLeader = Character;
	// A clone made while the leader is in the air does not copy that jump.
	CloneJutsu->LastLeaderJumpCount = Character->JumpCurrentCount;
	CloneJutsu->CloneRevealTime = Now() + CloneRevealDelay;
	CloneJutsu->CloneExpireTime = CloneLifetime > 0.0f ? Now() + CloneLifetime : 0.0;
	if (UActorComponent* CloneJutsuTick = CloneJutsu)
	{
		CloneJutsuTick->AddTickPrerequisiteComponent(this);
	}
	// Start at the leader's speed so a clone made on the run keeps up; hidden until the smoke has covered the spot.
	Clone->GetCharacterMovement()->Velocity = Character->GetCharacterMovement()->Velocity;
	if (USkeletalMeshComponent* CloneVisual = CloneJutsu->GetVisualMesh())
	{
		NinjaVisual::SetVisualHidden(CloneVisual, true);
	}
	Clones.Add(Clone);
	// Attached so the burst stays centred on the clone even if it moves before it is revealed.
	SpawnCloneSmoke(Clone, /*bAttach*/ true);
	OnCloneSpawned.Broadcast(Clone);
}

void UNinjaJutsuComponent::DispelClones()
{
	for (const TWeakObjectPtr<ACharacter>& Clone : TArray<TWeakObjectPtr<ACharacter>>(Clones))
	{
		if (UNinjaJutsuComponent* CloneJutsu = Clone.IsValid() ? Clone->FindComponentByClass<UNinjaJutsuComponent>() : nullptr)
		{
			CloneJutsu->DispelClone();
		}
	}
	Clones.Reset();
}

void UNinjaJutsuComponent::DispelClone()
{
	ACharacter* Character = GetCharacter();
	if (!bIsShadowClone || !Character || Character->IsActorBeingDestroyed())
	{
		return;
	}
	// A chain or unreleased finisher in progress still ends with OnJutsuCancelled.
	CancelJutsu();
	CancelFinisher();
	SpawnCloneSmoke(Character, /*bAttach*/ false);
	if (CloneDispelSound)
	{
		UGameplayStatics::PlaySoundAtLocation(this, CloneDispelSound, Character->GetActorLocation());
	}
	if (ACharacter* Leader = CloneLeader.Get())
	{
		if (UNinjaJutsuComponent* LeaderJutsu = Leader->FindComponentByClass<UNinjaJutsuComponent>())
		{
			LeaderJutsu->Clones.RemoveAll([Character](const TWeakObjectPtr<ACharacter>& Entry) { return Entry.Get() == Character; });
		}
	}
	if (AController* CloneController = Character->GetController())
	{
		CloneController->UnPossess();
		CloneController->Destroy();
	}
	Character->Destroy();
}

void UNinjaJutsuComponent::UpdateClone()
{
	ACharacter* Character = GetCharacter();
	ACharacter* Leader = CloneLeader.Get();
	const double Time = Now();
	if (!Character || !Leader || (CloneExpireTime > 0.0 && Time >= CloneExpireTime))
	{
		DispelClone();
		return;
	}

	// Copy the leader's input this frame: its consumed movement input (world space), its control rotation (GASP's strafe mode
	// faces it), its gait flags (GASP keeps Wants To Sprint / Walk / Strafe / Aim in CharacterInputState), its jumps and crouch.
	Character->AddMovementInput(Leader->GetLastMovementInputVector());
	if (AController* CloneController = Character->GetController())
	{
		CloneController->SetControlRotation(Leader->GetControlRotation());
		// While the leader is focused, each clone faces the target from where it stands, not along the leader's line: an AI
		// controller turns its control rotation to its focus every tick, before the movement reads it, replacing this copy.
		if (AAIController* CloneAI = Cast<AAIController>(CloneController))
		{
			const UNinjaLockOnComponent* LeaderLockOn = Leader->FindComponentByClass<UNinjaLockOnComponent>();
			AActor* Target = LeaderLockOn ? LeaderLockOn->GetLockTarget() : nullptr;
			if (Target != CloneAI->GetFocusActor())
			{
				if (Target)
				{
					CloneAI->SetFocus(Target);
				}
				else
				{
					CloneAI->ClearFocus(EAIFocusPriority::Gameplay);
				}
			}
		}
	}
	if (FStructProperty* State = FindFProperty<FStructProperty>(Character->GetClass(), NinjaJutsuConst::GaspInputStateProperty))
	{
		if (FStructProperty* LeaderState = FindFProperty<FStructProperty>(Leader->GetClass(), NinjaJutsuConst::GaspInputStateProperty);
			LeaderState && LeaderState->Struct == State->Struct)
		{
			State->CopyCompleteValue(State->ContainerPtrToValuePtr<void>(Character), LeaderState->ContainerPtrToValuePtr<void>(Leader));
		}
	}
	// The leader's bPressedJump is set and cleared inside its own movement tick (ClearJumpInput; JumpMaxHoldTime is 0), so it is
	// always false by now. Its JumpCurrentCount rises only on a jump its movement accepted and drops to 0 on landing, so copy each
	// rise (the clone's air-jump component then plays the flip for the second). Stored every tick to follow the landing reset.
	if (Leader->JumpCurrentCount > LastLeaderJumpCount)
	{
		Character->Jump();
	}
	LastLeaderJumpCount = Leader->JumpCurrentCount;
	if (Leader->bIsCrouched && !Character->bIsCrouched)
	{
		Character->Crouch();
	}
	else if (!Leader->bIsCrouched && Character->bIsCrouched)
	{
		Character->UnCrouch();
	}
	// Prone as a state (lying down or getting up), like the crouch; a clone that cannot lie down yet (mid-air) tries again next tick.
	if (const UNinjaStanceComponent* LeaderStance = Leader->FindComponentByClass<UNinjaStanceComponent>())
	{
		UNinjaStanceComponent* Stance = Character->FindComponentByClass<UNinjaStanceComponent>();
		if (Stance && Stance->WantsProne() != LeaderStance->WantsProne())
		{
			Stance->SetProne(LeaderStance->WantsProne());
		}
	}

	// A clone never keeps signing on its own (its leader's chain was cancelled while the clone's was not).
	if (bIsCastingJutsu)
	{
		const UNinjaJutsuComponent* LeaderJutsu = Leader->FindComponentByClass<UNinjaJutsuComponent>();
		if (!LeaderJutsu || !LeaderJutsu->bIsCastingJutsu || LeaderJutsu->CastingJutsu != CastingJutsu)
		{
			CancelJutsu();
		}
	}
	if (CloneRevealTime > 0.0 && Time >= CloneRevealTime)
	{
		if (USkeletalMeshComponent* Visual = GetVisualMesh())
		{
			NinjaVisual::SetVisualHidden(Visual, false);
		}
		CloneRevealTime = 0.0;
	}
}

void UNinjaJutsuComponent::SpawnCloneSmoke(ACharacter* Target, bool bAttach) const
{
	if (!CloneSmokeEffect || !Target)
	{
		return;
	}
	if (bAttach)
	{
		UNiagaraFunctionLibrary::SpawnSystemAttached(CloneSmokeEffect, Target->GetCapsuleComponent(), NAME_None, CloneSmokeOffset, FRotator::ZeroRotator,
			CloneSmokeScale, EAttachLocation::KeepRelativeOffset, /*bAutoDestroy*/ true, ENCPoolMethod::None);
	}
	else
	{
		UNiagaraFunctionLibrary::SpawnSystemAtLocation(this, CloneSmokeEffect, Target->GetActorLocation() + CloneSmokeOffset, FRotator::ZeroRotator, CloneSmokeScale);
	}
}

void UNinjaJutsuComponent::PruneClones()
{
	Clones.RemoveAll([](const TWeakObjectPtr<ACharacter>& Clone) { return !IsValid(Clone.Get()) || Clone->IsActorBeingDestroyed(); });
}
