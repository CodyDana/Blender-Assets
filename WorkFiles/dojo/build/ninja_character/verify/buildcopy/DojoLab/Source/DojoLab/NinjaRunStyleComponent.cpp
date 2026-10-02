// Copyright Epic Games, Inc. All Rights Reserved.

#include "NinjaRunStyleComponent.h"

#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimSequenceBase.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "HAL/IConsoleManager.h"
#include "NinjaCombatComponent.h"
#include "NinjaJutsuComponent.h"
#include "NinjaStanceComponent.h"
#include "NinjaVisual.h"

DEFINE_LOG_CATEGORY_STATIC(LogNinjaRunStyle, Log, All);

static TAutoConsoleVariable<int32> CVarNinjaRunStyle(
	TEXT("ninja.run.style"), 1, TEXT("0 puts the ninja back on GASP's own run, for an A/B without a rebuild."), ECVF_Default);

static TAutoConsoleVariable<int32> CVarNinjaRunDebug(
	TEXT("ninja.run.debug"), 0, TEXT("Log when the ninja run override takes and gives back the body."), ECVF_Default);

UNinjaRunStyleComponent::UNinjaRunStyleComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	// After the movement component, so GetVelocity is this frame's.
	PrimaryComponentTick.TickGroup = TG_PostPhysics;
}

ACharacter* UNinjaRunStyleComponent::GetCharacter() const
{
	return Cast<ACharacter>(GetOwner());
}

bool UNinjaRunStyleComponent::ShouldRun(float& OutSpeed) const
{
	OutSpeed = 0.0f;
	if (!bEnabled || (!RunAnimation && !SprintAnimation && !WalkAnimation) || CVarNinjaRunStyle.GetValueOnGameThread() == 0)
	{
		return false;
	}
	const ACharacter* Character = GetCharacter();
	const UCharacterMovementComponent* Movement = Character ? Character->GetCharacterMovement() : nullptr;
	if (!Movement || !Movement->IsMovingOnGround() || Character->bIsCrouched)
	{
		return false;
	}
	// Anything else that owns the visible full-body slot wins: a lying body, an attack, a guard, a finisher.
	if (const UNinjaStanceComponent* Stance = Character->FindComponentByClass<UNinjaStanceComponent>(); Stance && Stance->IsProne())
	{
		return false;
	}
	if (const UNinjaCombatComponent* Combat = Character->FindComponentByClass<UNinjaCombatComponent>();
		Combat && (Combat->IsBusy() || Combat->IsBlocking()))
	{
		return false;
	}
	if (const UNinjaJutsuComponent* Jutsu = Character->FindComponentByClass<UNinjaJutsuComponent>();
		Jutsu && (Jutsu->IsCastingJutsu() || Jutsu->IsFinishing()))
	{
		return false;
	}
	// GASP plays its traversals (vault, mantle) on its own hidden mesh's full-body slot; let those play out.
	const UAnimInstance* BodyAnim = Character->GetMesh() ? Character->GetMesh()->GetAnimInstance() : nullptr;
	if (BodyAnim && BodyAnim->IsSlotActive(NinjaVisual::FullBodySlot))
	{
		return false;
	}

	FVector Velocity = Character->GetVelocity();
	Velocity.Z = 0.0f;
	OutSpeed = Velocity.Size();
	// The lowest tier that actually has a clip: with no jog clip (the default) nothing happens below the sprint threshold.
	const float LowestTier = WalkAnimation ? WalkMinSpeed : (RunAnimation ? MinSpeed : SprintMinSpeed);
	// Hysteresis, so a speed hovering on the threshold can't flicker the override on and off every frame.
	const float Threshold = bRunning ? FMath::Max(LowestTier - SpeedHysteresis, 0.0f) : LowestTier;
	if (OutSpeed < Threshold || OutSpeed < KINDA_SMALL_NUMBER)
	{
		return false;
	}
	// The pack has no strafe or backpedal run, so only take the body when moving roughly the way the ninja faces.
	const FVector Direction = Velocity / OutSpeed;
	const float Cosine = FVector::DotProduct(Direction, Character->GetActorForwardVector());
	return Cosine >= FMath::Cos(FMath::DegreesToRadians(FMath::Clamp(MaxForwardAngle, 0.0f, 180.0f)));
}

UAnimSequenceBase* UNinjaRunStyleComponent::ChooseClip(float Speed, float& OutClipSpeed) const
{
	if (SprintAnimation && Speed >= SprintMinSpeed)
	{
		OutClipSpeed = SprintClipSpeed;
		return SprintAnimation;
	}
	if (RunAnimation && Speed >= MinSpeed)
	{
		OutClipSpeed = RunClipSpeed;
		return RunAnimation;
	}
	// Below the jog: the walk, when there is one. (ShouldRun only lets speeds under MinSpeed through when there is.)
	if (WalkAnimation && Speed < MinSpeed)
	{
		OutClipSpeed = WalkClipSpeed;
		return WalkAnimation;
	}
	if (RunAnimation)
	{
		OutClipSpeed = RunClipSpeed;
		return RunAnimation;
	}
	// No jog clip: the sprint clip is the only one there is, and ShouldRun already held it back below SprintMinSpeed.
	OutClipSpeed = SprintClipSpeed;
	return SprintAnimation;
}

void UNinjaRunStyleComponent::StartOrUpdateRun(float Speed)
{
	USkeletalMeshComponent* Visual = NinjaVisual::FindVisualMesh(GetOwner());
	UAnimInstance* Anim = Visual ? Visual->GetAnimInstance() : nullptr;
	if (!Anim)
	{
		return;
	}
	float ClipSpeed = RunClipSpeed;
	UAnimSequenceBase* Clip = ChooseClip(Speed, ClipSpeed);
	if (!Clip)
	{
		return;
	}
	const float WantedRate = Speed / FMath::Max(ClipSpeed, 1.0f);
	const bool bWalk = Clip == WalkAnimation;
	const float Rate = FMath::Clamp(WantedRate, bWalk ? WalkMinPlayRate : MinPlayRate, bWalk ? WalkMaxPlayRate : MaxPlayRate);
	// What the rate could not deliver, the stride warping makes up by lengthening or shortening the step. Where the rate is not
	// clamped this is 1 and the warping node is a no-op, leaving Foot Placement to do the work.
	StrideScale = FMath::Clamp(WantedRate / FMath::Max(Rate, KINDA_SMALL_NUMBER), MinStrideScale, MaxStrideScale);

	// Restart when our montage is gone (an attack took the slot) or when the speed crossed into the other tier's clip.
	const bool bStillPlaying = bRunning && RunMontage.IsValid() && Anim->Montage_IsPlaying(RunMontage.Get())
		&& ActiveClip.Get() == Clip;
	if (!bStillPlaying)
	{
		UAnimMontage* Montage = NinjaVisual::PlaySlotMontage(Visual, Clip, NinjaVisual::FullBodySlot,
			BlendIn, BlendOut, Rate, 0.0f, /*bLoop*/ true);
		if (!Montage)
		{
			return;
		}
		RunMontage = Montage;
		ActiveClip = Clip;
		bRunning = true;
		if (CVarNinjaRunDebug.GetValueOnGameThread() != 0)
		{
			UE_LOG(LogNinjaRunStyle, Log, TEXT("%s: ninja run ON %s (%.0f cm/s, rate %.2f)"),
				*GetNameSafe(GetOwner()), *GetNameSafe(Clip), Speed, Rate);
		}
		return;
	}
	Anim->Montage_SetPlayRate(RunMontage.Get(), Rate);
}

void UNinjaRunStyleComponent::StopRun()
{
	if (!bRunning)
	{
		return;
	}
	bRunning = false;
	USkeletalMeshComponent* Visual = NinjaVisual::FindVisualMesh(GetOwner());
	UAnimInstance* Anim = Visual ? Visual->GetAnimInstance() : nullptr;
	// By pointer, not StopSlotMontages: an attack that just took the slot must not be cut short by our own stop.
	if (Anim && RunMontage.IsValid() && Anim->Montage_IsPlaying(RunMontage.Get()))
	{
		Anim->Montage_Stop(BlendOut, RunMontage.Get());
	}
	RunMontage.Reset();
	ActiveClip.Reset();
	if (CVarNinjaRunDebug.GetValueOnGameThread() != 0)
	{
		UE_LOG(LogNinjaRunStyle, Log, TEXT("%s: ninja run OFF"), *GetNameSafe(GetOwner()));
	}
}

void UNinjaRunStyleComponent::LogSlide(float DeltaTime, float Speed)
{
#if !UE_BUILD_SHIPPING
	const ACharacter* Character = GetCharacter();
	const USkeletalMeshComponent* Visual = NinjaVisual::FindVisualMesh(GetOwner());
	if (!Character || !Visual || DeltaTime <= 0.0f || !Character->IsLocallyControlled())
	{
		return;
	}
	// Pick the foot that is actually DOWN and report its horizontal world speed plus its height off the floor. Taking the slower
	// of the two feet (what the crouch run does) does not work for a run: a run has flight phases where neither foot is planted,
	// so the minimum stays large even when every contact is clean. The caller filters to the frames where height is small.
	const FVector Left = Visual->GetSocketLocation(TEXT("ball_l"));
	const FVector Right = Visual->GetSocketLocation(TEXT("ball_r"));
	const bool bLeftDown = Left.Z <= Right.Z;
	const FVector Down = bLeftDown ? Left : Right;
	const FVector LastDown = bLeftDown ? DebugLastLeftFoot : DebugLastRightFoot;
	float Planted = -1.0f;
	if (bDebugHasFeet)
	{
		Planted = static_cast<float>(FVector::Dist2D(Down, LastDown) / DeltaTime);
	}
	// Height of that foot above the capsule's base, so "on the floor" is comparable across frames.
	float FootHeight = 0.0f;
	if (const UCapsuleComponent* Capsule = Character->GetCapsuleComponent())
	{
		FootHeight = static_cast<float>(Down.Z - (Character->GetActorLocation().Z - Capsule->GetScaledCapsuleHalfHeight()));
	}
	DebugLastLeftFoot = Left;
	DebugLastRightFoot = Right;
	bDebugHasFeet = true;

	// How far the body is from pointing where it is actually travelling. The clip's stride runs along the body's forward axis,
	// so any angle here means the feet are pushing one way while the capsule goes another - which reads as sliding.
	FVector Velocity = Character->GetVelocity();
	Velocity.Z = 0.0f;
	float YawError = 0.0f;
	if (Velocity.SizeSquared() > 1.0f)
	{
		YawError = FMath::FindDeltaAngleDegrees(Character->GetActorRotation().Yaw, Velocity.Rotation().Yaw);
	}
	const float Rate = RunMontage.IsValid() && Visual->GetAnimInstance()
		? Visual->GetAnimInstance()->Montage_GetPlayRate(RunMontage.Get()) : 0.0f;
	UE_LOG(LogNinjaRunStyle, Log, TEXT("slide speed=%.0f rate=%.2f planted=%.0f height=%.0f yawErr=%.0f clip=%s"),
		Speed, Rate, Planted, FootHeight, YawError, *GetNameSafe(ActiveClip.Get()));
#endif
}

void UNinjaRunStyleComponent::UpdateFootLock(float DeltaTime, float Speed)
{
	if (!bDriveFootLock)
	{
		return;
	}
	USkeletalMeshComponent* Visual = NinjaVisual::FindVisualMesh(GetOwner());
	UAnimInstance* Anim = Visual ? Visual->GetAnimInstance() : nullptr;
	if (!Anim)
	{
		return;
	}
	// Faded, not switched: snapping the foot IK on pops the feet.
	const float Target = bRunning ? 1.0f : 0.0f;
	const float Step = DeltaTime / FMath::Max(FootLockBlendTime, 0.01f);
	LocoWeight = FMath::FInterpConstantTo(LocoWeight, Target, 1.0f, Step);
	if (!bRunning)
	{
		StrideScale = 1.0f;
	}
	NinjaVisual::SetAnimFloat(Anim, TEXT("NinjaLocoWeight"), LocoWeight);
	NinjaVisual::SetAnimFloat(Anim, TEXT("NinjaStrideScale"), StrideScale);
}

void UNinjaRunStyleComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	float Speed = 0.0f;
	if (ShouldRun(Speed))
	{
		StartOrUpdateRun(Speed);
	}
	else
	{
		StopRun();
	}
	UpdateFootLock(DeltaTime, Speed);
	if (CVarNinjaRunDebug.GetValueOnGameThread() >= 2)
	{
		LogSlide(DeltaTime, Speed);
	}
	else
	{
		bDebugHasFeet = false;
	}
}
