// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Camera/CameraModifier.h"
#include "NinjaLockOnCameraModifier.generated.h"

/**
 * Keeps the focused target (UNinjaLockOnComponent::GetLockTarget, Tab) in front of the camera: swings the control rotation's yaw
 * toward the target, seen from the camera, and lets only a fraction of the mouse's yaw through as a nudge that the focus pulls
 * back. Pitch stays the player's. Does nothing while there is no target.
 *
 * It works on the CONTROL rotation (APlayerController::UpdateRotation -> PlayerCameraManager::ProcessViewRotation), which GASP's
 * camera rig and its movement input follow. The lock-on component adds it to the local player's camera manager only: the
 * server's copy of a remote client's controller also runs UpdateRotation before each of its moves, and a modifier there would
 * bend the control rotation the client sent.
 */
UCLASS()
class DEMOGAME_1_API UNinjaLockOnCameraModifier : public UCameraModifier
{
	GENERATED_BODY()

public:
	virtual bool ProcessViewRotation(AActor* ViewTarget, float DeltaTime, FRotator& OutViewRotation, FRotator& OutDeltaRot) override;
};
