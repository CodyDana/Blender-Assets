// Copyright Epic Games, Inc. All Rights Reserved.

#include "NinjaAirJumpComponent.h"

#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimSequenceBase.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"
#include "Net/UnrealNetwork.h"
#include "NinjaVisual.h"

UNinjaAirJumpComponent::UNinjaAirJumpComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	// After the movement component (PrePhysics), so this frame's jump has already been counted.
	PrimaryComponentTick.TickGroup = TG_PostPhysics;
	SetIsReplicatedByDefault(true);
}

void UNinjaAirJumpComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
	Super::GetLifetimeReplicatedProps(OutLifetimeProps);
	// The owner predicted its own flip and the server played its own; only simulated proxies need the announcement.
	DOREPLIFETIME_CONDITION(UNinjaAirJumpComponent, AirJumpCounter, COND_SimulatedOnly);
	DOREPLIFETIME_CONDITION(UNinjaAirJumpComponent, bAirJumpWasBack, COND_SimulatedOnly);
}

ACharacter* UNinjaAirJumpComponent::GetCharacter() const
{
	return Cast<ACharacter>(GetOwner());
}

void UNinjaAirJumpComponent::BeginPlay()
{
	Super::BeginPlay();
	if (ACharacter* Character = GetCharacter())
	{
		Character->JumpMaxCount = FMath::Max(MaxJumps, 1);
		Character->MovementModeChangedDelegate.AddDynamic(this, &UNinjaAirJumpComponent::OnOwnerMovementModeChanged);
	}
}

void UNinjaAirJumpComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	ACharacter* Character = GetCharacter();
	if (!Character || Character->GetLocalRole() == ROLE_SimulatedProxy)
	{
		return;
	}
	// ACharacter::CheckJumpInput counts every jump (walking off a ledge counts the missed ground jump first), so an air jump shows
	// as the count reaching 2 or more while falling. Sampled once per tick: a correction replaying moves inside a frame does not
	// start a second flip.
	const int32 Count = Character->JumpCurrentCount;
	const UCharacterMovementComponent* Movement = Character->GetCharacterMovement();
	if (Count >= 2 && Count > LastJumpCount && Movement && Movement->IsFalling())
	{
		const bool bBack = WantsBackFlip();
		if (Character->HasAuthority())
		{
			// Set before the counter, so the flag is already right when the counter's OnRep fires on a proxy.
			bAirJumpWasBack = bBack;
			++AirJumpCounter;
		}
		PlayFlip(bBack);
	}
	LastJumpCount = Count;
}

bool UNinjaAirJumpComponent::WantsBackFlip() const
{
	const ACharacter* Character = GetCharacter();
	const AController* Controller = Character ? Character->GetController() : nullptr;
	if (!BackFlipAnimation || !Controller)
	{
		return false;
	}
	FVector Input = Character->GetLastMovementInputVector();
	Input.Z = 0.0f;
	if (Input.IsNearlyZero())
	{
		return false;
	}
	// Measured against the CAMERA's forward, not the ninja's: "S" has to mean the same thing whichever way the body is facing,
	// and with orient-to-movement the body is usually facing its travel rather than the camera. Backwards is a negative dot.
	const FRotator YawOnly(0.0f, Controller->GetControlRotation().Yaw, 0.0f);
	const FVector CameraForward = FRotationMatrix(YawOnly).GetUnitAxis(EAxis::X);
	return FVector::DotProduct(Input.GetSafeNormal(), CameraForward) <= -BackFlipInputThreshold;
}

void UNinjaAirJumpComponent::OnRep_AirJumpCounter()
{
	// The initial bunch replays the last counter value, which is state, not an event.
	if (HasBegunPlay())
	{
		PlayFlip(bAirJumpWasBack);
	}
}

bool UNinjaAirJumpComponent::PlayFlip(bool bBack)
{
	UAnimSequenceBase* Clip = (bBack && BackFlipAnimation) ? BackFlipAnimation.Get() : FlipAnimation.Get();
	if (!Clip)
	{
		return false;
	}
	const bool bUsingBack = (Clip == BackFlipAnimation);
	const float Length = Clip->GetPlayLength();
	const float Start = FMath::Clamp(bUsingBack ? BackFlipStartTime : FlipStartTime, 0.0f, Length);
	const float End = FMath::Clamp(bUsingBack ? BackFlipEndTime : FlipEndTime, Start, Length);
	UAnimMontage* Montage = NinjaVisual::PlaySlotMontage(NinjaVisual::FindVisualMesh(GetOwner()), Clip, NinjaVisual::FullBodySlot,
		FlipBlendIn, FlipBlendOut, FlipPlayRate, Start);
	if (!Montage)
	{
		return false;
	}
	// The auto blend-out starts when the montage's remaining PLAY time drops below this, so the clip-time tail End..Length is
	// divided by the play rate: the blend-out then starts at clip time End whatever FlipPlayRate is.
	Montage->BlendOutTriggerTime = (Length - End) / FMath::Max(FlipPlayRate, UE_KINDA_SMALL_NUMBER);
	FlipMontage = Montage;
	return true;
}

void UNinjaAirJumpComponent::CutFlip(float BlendOutTime)
{
	UAnimMontage* Flip = FlipMontage.Get();
	FlipMontage.Reset();
	const USkeletalMeshComponent* Visual = NinjaVisual::FindVisualMesh(GetOwner());
	UAnimInstance* AnimInstance = Visual ? Visual->GetAnimInstance() : nullptr;
	if (Flip && AnimInstance && AnimInstance->Montage_IsPlaying(Flip))
	{
		AnimInstance->Montage_Stop(BlendOutTime, Flip);
	}
}

void UNinjaAirJumpComponent::OnOwnerMovementModeChanged(ACharacter* Character, EMovementMode PrevMovementMode, uint8 PreviousCustomMode)
{
	// Every role lands through a mode change (only the owner and the server call Landed). The air jump starts while already
	// falling, so it never triggers this.
	const UCharacterMovementComponent* Movement = Character ? Character->GetCharacterMovement() : nullptr;
	if (PrevMovementMode == MOVE_Falling && Movement && !Movement->IsFalling())
	{
		CutFlip(FlipLandBlendOut);
	}
}
