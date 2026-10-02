// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "NinjaFreeLookComponent.generated.h"

class ACharacter;
class AController;
class UInputAction;
class UInputComponent;

/**
 * PUBG-style free look (Cody, 2026-09-20: "if im going forward with w, then i hold alt and move my mouse, i should be able to
 * look around my character while the chracter is still moving forward"). Hold Left Alt and the camera swings around the ninja
 * while the run carries on in the direction it was already going; let go and the camera comes back where it was.
 *
 * How, without touching the camera at all: movement input is camera-relative, so while free look is held this component takes
 * the pending movement input off the pawn and puts it back rotated by however far the camera has turned since the key went down.
 * W therefore keeps pushing along the ORIGINAL heading no matter where the camera now points. The body follows the movement
 * because GASP is in orient-to-movement (see the strafe default), so the ninja keeps facing its run while the camera orbits.
 *
 * On release the control rotation is put back to what it was when the key went down, which is the snap PUBG does; set
 * ReturnTime above 0 to ease it back instead. Free look does not change where the ninja goes, only what you can see.
 *
 * Tick order is the same trick UNinjaStanceComponent and UNinjaTurnComponent use: after the controller (so this frame's input is
 * already in the pending vector) and BEFORE the movement component consumes it.
 */
UCLASS(ClassGroup=(Ninja), meta=(BlueprintSpawnableComponent))
class DEMOGAME_1_API UNinjaFreeLookComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UNinjaFreeLookComponent();

	virtual void BeginPlay() override;
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|FreeLook")
	bool bEnabled = true;

	/** Held, not toggled: BP_NinjaGasp uses IA_FreeLook on Left Alt (no triggers, so Started is the press and Completed the release). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|FreeLook")
	TObjectPtr<UInputAction> FreeLookAction;

	/**
	 * Seconds to bring the camera back to where it was when the key went down. 0 snaps, which is what PUBG does. The ninja's
	 * heading is never changed by this - only the camera moves.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|FreeLook", meta=(ClampMin="0.0"))
	float ReturnTime = 0.0f;

	/** How far round the ninja the camera may swing. 180 lets you look straight back over your shoulder. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|FreeLook", meta=(ClampMin="0.0", ClampMax="180.0"))
	float MaxYaw = 180.0f;

	UFUNCTION(BlueprintPure, Category="Ninja|FreeLook")
	bool IsFreeLooking() const { return bFreeLooking; }

private:
	ACharacter* GetCharacter() const;
	void UpdateInputBinding();

	UFUNCTION()
	void OnFreeLookPressed();
	UFUNCTION()
	void OnFreeLookReleased();

	bool bFreeLooking = false;
	/** The control rotation when the key went down: what movement stays relative to, and where the camera returns. */
	FRotator AnchorRotation = FRotator::ZeroRotator;
	/** Set while easing the camera back after release (ReturnTime > 0). */
	bool bReturning = false;
	float ReturnElapsed = 0.0f;
	FRotator ReturnFrom = FRotator::ZeroRotator;

	TWeakObjectPtr<UInputComponent> BoundInputComponent;
	TWeakObjectPtr<AController> PrerequisiteController;
};
