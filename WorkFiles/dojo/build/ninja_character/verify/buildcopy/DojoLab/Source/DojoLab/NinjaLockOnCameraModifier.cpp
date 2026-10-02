// Copyright Epic Games, Inc. All Rights Reserved.

#include "NinjaLockOnCameraModifier.h"

#include "Camera/PlayerCameraManager.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "NinjaLockOnComponent.h"

bool UNinjaLockOnCameraModifier::ProcessViewRotation(AActor* ViewTarget, float DeltaTime, FRotator& OutViewRotation, FRotator& OutDeltaRot)
{
	// The focused pawn is the controller's, not necessarily the view target (GASP's Gameplay Camera system may view through its
	// own actor).
	const APlayerController* PC = CameraOwner ? CameraOwner->GetOwningPlayerController() : nullptr;
	const APawn* Pawn = PC ? PC->GetPawn() : nullptr;
	const UNinjaLockOnComponent* LockOn = Pawn ? Pawn->FindComponentByClass<UNinjaLockOnComponent>() : nullptr;
	const AActor* Target = LockOn ? LockOn->GetLockTarget() : nullptr;
	if (!Target)
	{
		return false;
	}

	// Aimed from where the camera is (last frame's, it converges within a few frames), not from the character: with a shoulder
	// camera a yaw taken from the character would put the target just beside its head; from the camera the target is centred.
	const FVector ToTarget = Target->GetActorLocation() - CameraOwner->GetCameraLocation();
	if (ToTarget.SizeSquared2D() < FMath::Square(50.0f))
	{
		return false;
	}
	const float DesiredYaw = static_cast<float>(ToTarget.Rotation().Yaw);

	// The mouse still nudges a little; the pull below takes it back. This runs on the control rotation, which GASP's camera rig
	// and its movement input both follow.
	OutDeltaRot.Yaw *= LockOn->LockCameraYawNudgeScale;
	const float Delta = FMath::FindDeltaAngleDegrees(static_cast<float>(OutViewRotation.Yaw), DesiredYaw);
	const float Pull = FMath::Clamp(DeltaTime * LockOn->LockCameraInterpSpeed, 0.0f, 1.0f);
	OutViewRotation.Yaw += Delta * Pull;
	return false;
}
