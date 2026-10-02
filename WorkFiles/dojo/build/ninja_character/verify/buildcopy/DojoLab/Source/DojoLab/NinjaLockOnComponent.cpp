// Copyright Epic Games, Inc. All Rights Reserved.

#include "NinjaLockOnComponent.h"

#include "Camera/PlayerCameraManager.h"
#include "Components/CapsuleComponent.h"
#include "Engine/Canvas.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "GameFramework/Character.h"
#include "GameFramework/HUD.h"
#include "GameFramework/PlayerController.h"
#include "InputMappingContext.h"
#include "Net/UnrealNetwork.h"
#include "NinjaJutsuComponent.h"
#include "NinjaLockOnCameraModifier.h"

DEFINE_LOG_CATEGORY_STATIC(LogNinjaLockOn, Log, All);

namespace NinjaLockOnConst
{
	/** GASP's CMC character keeps its gait/rotation inputs in this Blueprint struct; its bool fields carry GUID suffixes. */
	const FName GaspInputStateProperty(TEXT("CharacterInputState"));
	const TCHAR* GaspWantsToStrafePrefix = TEXT("WantsToStrafe");
	const TCHAR* GaspWantsToAimPrefix = TEXT("WantsToAim");
	/** GASP's own path for sending the input state to the server (its IA_Strafe handler calls it). */
	const FName GaspInputStateServerEvent(TEXT("UpdateInputState_Server"));
}

UNinjaLockOnComponent::UNinjaLockOnComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	SetIsReplicatedByDefault(true);
}

void UNinjaLockOnComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
	Super::GetLifetimeReplicatedProps(OutLifetimeProps);
	DOREPLIFETIME(UNinjaLockOnComponent, TeamId);
}

void UNinjaLockOnComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	// The marker is a static HUD delegate: it must not outlive this component.
	SetMarkerDrawn(false);
	Super::EndPlay(EndPlayReason);
}

void UNinjaLockOnComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	UpdateInputBinding();
	if (!LockTarget.IsValid())
	{
		if (MarkerDelegate.IsValid())
		{
			// The target was destroyed.
			ClearLockOn();
		}
		return;
	}
	// Too far, gone, hidden or no longer hostile: let go (no line-of-sight check here, a tree in between must not break the focus).
	if (!IsValidTarget(LockTarget.Get(), LockOnBreakRange))
	{
		ClearLockOn();
	}
}

void UNinjaLockOnComponent::UpdateInputBinding()
{
	const APawn* Pawn = Cast<APawn>(GetOwner());
	UInputComponent* Input = Pawn ? Pawn->InputComponent.Get() : nullptr;
	APlayerController* PC = Pawn ? Cast<APlayerController>(Pawn->GetController()) : nullptr;
	if (!Input || !PC || !PC->IsLocalController())
	{
		BoundInputComponent.Reset();
		return;
	}
	if (BoundInputComponent.Get() == Input)
	{
		return;
	}
	BoundInputComponent = Input;
	// Tab through Enhanced Input (a mapping), not a raw key binding: an unmapped Tab is reported unhandled to Slate, which then
	// uses it for focus navigation and can move keyboard focus off the viewport.
	if (UEnhancedInputComponent* Enhanced = Cast<UEnhancedInputComponent>(Input); Enhanced && LockOnAction)
	{
		Enhanced->BindAction(LockOnAction, ETriggerEvent::Started, this, &UNinjaLockOnComponent::OnLockOnInput);
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

void UNinjaLockOnComponent::OnLockOnInput()
{
	ToggleLockOn();
}

AActor* UNinjaLockOnComponent::GetLockTarget() const
{
	const UNinjaJutsuComponent* Jutsu = GetOwner() ? GetOwner()->FindComponentByClass<UNinjaJutsuComponent>() : nullptr;
	if (Jutsu && Jutsu->IsShadowClone())
	{
		const ACharacter* Leader = Jutsu->GetCloneLeader();
		const UNinjaLockOnComponent* LeaderLock = Leader ? Leader->FindComponentByClass<UNinjaLockOnComponent>() : nullptr;
		return LeaderLock ? LeaderLock->LockTarget.Get() : nullptr;
	}
	return LockTarget.Get();
}

bool UNinjaLockOnComponent::IsHostileTo(const AActor* Other) const
{
	// Compare the sides' leaders: a shadow clone fights for its leader.
	const AActor* MySide = UNinjaJutsuComponent::GetSideLeader(GetOwner());
	const AActor* OtherSide = UNinjaJutsuComponent::GetSideLeader(Other);
	const UNinjaLockOnComponent* Mine = MySide ? MySide->FindComponentByClass<UNinjaLockOnComponent>() : nullptr;
	const UNinjaLockOnComponent* Theirs = OtherSide ? OtherSide->FindComponentByClass<UNinjaLockOnComponent>() : nullptr;
	return Mine && Theirs && MySide != OtherSide && Mine->TeamId != Theirs->TeamId;
}

bool UNinjaLockOnComponent::IsValidTarget(const AActor* Candidate, float MaxRange) const
{
	const AActor* Owner = GetOwner();
	const UNinjaLockOnComponent* Other = Candidate ? Candidate->FindComponentByClass<UNinjaLockOnComponent>() : nullptr;
	const UNinjaJutsuComponent* OtherJutsu = Candidate ? Candidate->FindComponentByClass<UNinjaJutsuComponent>() : nullptr;
	// Hostile fighters only, never a shadow clone (a decoy is never a lock-on target).
	return Owner && Other && Other->bTargetable && Candidate != Owner && IsValid(Candidate) && !Candidate->IsActorBeingDestroyed()
		&& !Candidate->IsHidden() && !(OtherJutsu && OtherJutsu->IsShadowClone()) && IsHostileTo(Candidate)
		&& FVector::DistSquared(Candidate->GetActorLocation(), Owner->GetActorLocation()) <= FMath::Square(MaxRange);
}

AActor* UNinjaLockOnComponent::FindLockOnTarget() const
{
	const APawn* Pawn = Cast<APawn>(GetOwner());
	UWorld* World = GetWorld();
	if (!Pawn || !World)
	{
		return nullptr;
	}
	FVector ViewLocation = Pawn->GetPawnViewLocation();
	FRotator ViewRotation = Pawn->GetActorRotation();
	if (const APlayerController* PC = Pawn->GetController<APlayerController>())
	{
		PC->GetPlayerViewPoint(ViewLocation, ViewRotation);
	}
	const FVector ViewForward = ViewRotation.Vector().GetSafeNormal2D();

	AActor* Best = nullptr;
	float BestScore = TNumericLimits<float>::Max();
	bool bBestPreferred = false;
	for (TActorIterator<APawn> It(World); It; ++It)
	{
		APawn* Other = *It;
		if (!IsValidTarget(Other, LockOnRange))
		{
			continue;
		}
		const FVector ToOther = Other->GetActorLocation() - Pawn->GetActorLocation();
		const float Angle = FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(FVector::DotProduct(ViewForward, ToOther.GetSafeNormal2D()), -1.0f, 1.0f)));
		// Seen from the camera (pawns ignore the Visibility channel, so another fighter never hides a target).
		FCollisionQueryParams Params(SCENE_QUERY_STAT(NinjaLockOnSight), false, Pawn);
		Params.AddIgnoredActor(Other);
		FHitResult Blocker;
		if (World->LineTraceSingleByChannel(Blocker, ViewLocation, Other->GetActorLocation() + FVector(0.0f, 0.0f, 40.0f), ECC_Visibility, Params))
		{
			continue;
		}
		const bool bPreferred = Angle <= LockOnPreferredAngle;
		const float Score = Angle + static_cast<float>(ToOther.Size()) / 100.0f;
		if ((bPreferred && !bBestPreferred) || (bPreferred == bBestPreferred && Score < BestScore))
		{
			Best = Other;
			BestScore = Score;
			bBestPreferred = bPreferred;
		}
	}
	return Best;
}

void UNinjaLockOnComponent::ToggleLockOn()
{
	APawn* Pawn = Cast<APawn>(GetOwner());
	const UNinjaJutsuComponent* Jutsu = Pawn ? Pawn->FindComponentByClass<UNinjaJutsuComponent>() : nullptr;
	if (!Pawn || !Pawn->IsLocallyControlled() || (Jutsu && Jutsu->IsShadowClone()))
	{
		return;
	}
	if (LockTarget.IsValid())
	{
		ClearLockOn();
		return;
	}
	AActor* Target = FindLockOnTarget();
	if (!Target)
	{
		UE_LOG(LogNinjaLockOn, Log, TEXT("focus %s: no target within %.0f cm"), *GetNameSafe(Pawn), LockOnRange);
		return;
	}
	LockTarget = Target;
	if (APlayerController* PC = Pawn->GetController<APlayerController>(); PC && PC->PlayerCameraManager)
	{
		// Installed once on this (local) camera manager and left there: it does nothing without a target.
		if (!PC->PlayerCameraManager->FindCameraModifierByClass(UNinjaLockOnCameraModifier::StaticClass()))
		{
			PC->PlayerCameraManager->AddNewCameraModifier(UNinjaLockOnCameraModifier::StaticClass());
		}
	}
	SetMarkerDrawn(true);
	ApplyLockStance(true);
	UE_LOG(LogNinjaLockOn, Log, TEXT("focus %s -> %s (%.0f cm)"), *GetNameSafe(Pawn), *GetNameSafe(Target),
		FVector::Dist(Pawn->GetActorLocation(), Target->GetActorLocation()));
}

void UNinjaLockOnComponent::ClearLockOn()
{
	if (LockTarget.IsValid())
	{
		UE_LOG(LogNinjaLockOn, Log, TEXT("focus %s released %s"), *GetNameSafe(GetOwner()), *GetNameSafe(LockTarget.Get()));
	}
	LockTarget.Reset();
	SetMarkerDrawn(false);
	ApplyLockStance(false);
}

void UNinjaLockOnComponent::ApplyLockStance(bool bLocked)
{
	if (bLocked == bLockStanceApplied)
	{
		return;
	}
	AActor* Owner = GetOwner();
	FStructProperty* StateProperty = Owner ? FindFProperty<FStructProperty>(Owner->GetClass(), NinjaLockOnConst::GaspInputStateProperty) : nullptr;
	if (!StateProperty)
	{
		return;
	}
	void* State = StateProperty->ContainerPtrToValuePtr<void>(Owner);
	FBoolProperty* Strafe = nullptr;
	FBoolProperty* Aim = nullptr;
	for (TFieldIterator<FBoolProperty> It(StateProperty->Struct); It; ++It)
	{
		if (It->GetName().StartsWith(NinjaLockOnConst::GaspWantsToStrafePrefix))
		{
			Strafe = *It;
		}
		else if (It->GetName().StartsWith(NinjaLockOnConst::GaspWantsToAimPrefix))
		{
			Aim = *It;
		}
	}
	if (!Strafe || !Aim)
	{
		UE_LOG(LogNinjaLockOn, Warning, TEXT("%s: no WantsToStrafe / WantsToAim field in %s; the character will not face the target."),
			*GetNameSafe(Owner), *StateProperty->Struct->GetName());
	}
	// Locking saves the player's own strafe and aim (GASP starts in strafe; MMB / RMB toggle them) and releasing puts them back.
	if (bLocked)
	{
		bSavedStrafe = Strafe && Strafe->GetPropertyValue_InContainer(State);
		bSavedAim = Aim && Aim->GetPropertyValue_InContainer(State);
	}
	if (Strafe && bStrafeWhileLocked)
	{
		Strafe->SetPropertyValue_InContainer(State, bLocked || bSavedStrafe);
	}
	if (Aim && bAimWhileLocked)
	{
		Aim->SetPropertyValue_InContainer(State, bLocked || bSavedAim);
	}
	bLockStanceApplied = bLocked;
	// The server needs the same flags (it picks the rotation mode for the movement it simulates); sent the way GASP's own IA_Strafe
	// and IA_Aim handlers send them.
	UFunction* ServerEvent = Owner->FindFunction(NinjaLockOnConst::GaspInputStateServerEvent);
	if (!ServerEvent || ServerEvent->NumParms != 1)
	{
		return;
	}
	FStructProperty* Param = CastField<FStructProperty>(ServerEvent->PropertyLink);
	if (!Param || Param->Struct != StateProperty->Struct)
	{
		return;
	}
	uint8* Params = static_cast<uint8*>(FMemory_Alloca(ServerEvent->ParmsSize));
	FMemory::Memzero(Params, ServerEvent->ParmsSize);
	Param->InitializeValue_InContainer(Params);
	Param->CopyCompleteValue(Param->ContainerPtrToValuePtr<void>(Params), State);
	Owner->ProcessEvent(ServerEvent, Params);
	Param->DestroyValue_InContainer(Params);
}

void UNinjaLockOnComponent::SetMarkerDrawn(bool bDrawn)
{
	if (bDrawn && !MarkerDelegate.IsValid())
	{
		MarkerDelegate = AHUD::OnHUDPostRender.AddUObject(this, &UNinjaLockOnComponent::DrawLockMarker);
	}
	else if (!bDrawn && MarkerDelegate.IsValid())
	{
		AHUD::OnHUDPostRender.Remove(MarkerDelegate);
		MarkerDelegate.Reset();
	}
}

void UNinjaLockOnComponent::DrawLockMarker(AHUD* HUD, UCanvas* Canvas)
{
	const APawn* Pawn = Cast<APawn>(GetOwner());
	const AActor* Target = LockTarget.Get();
	// Every HUD broadcasts this delegate: draw only on this player's own screen.
	if (!Canvas || !HUD || !Pawn || !Target || HUD->GetOwningPlayerController() != Pawn->GetController())
	{
		return;
	}
	float HalfHeight = 90.0f;
	if (const ACharacter* TargetCharacter = Cast<ACharacter>(Target); TargetCharacter && TargetCharacter->GetCapsuleComponent())
	{
		HalfHeight = TargetCharacter->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	}
	const FVector Screen = Canvas->Project(Target->GetActorLocation() + FVector(0.0f, 0.0f, HalfHeight + 28.0f));
	if (Screen.Z <= 0.0f)
	{
		return;
	}
	// A diamond above the head, breathing slightly so it reads as live, over a dark rim for contrast on bright skies.
	const float Time = GetWorld() ? static_cast<float>(GetWorld()->GetTimeSeconds()) : 0.0f;
	const float Pulse = 1.0f + 0.12f * FMath::Sin(Time * 6.0f);
	const FVector2D Center(Screen.X, Screen.Y);
	const FVector2D Radius(LockMarkerSize * 0.75f * Pulse, LockMarkerSize * 1.1f * Pulse);
	Canvas->K2_DrawPolygon(nullptr, Center, Radius + FVector2D(2.5f, 3.0f), 4, FLinearColor(0.0f, 0.0f, 0.0f, 0.6f));
	Canvas->K2_DrawPolygon(nullptr, Center, Radius, 4, LockMarkerColor);
}
