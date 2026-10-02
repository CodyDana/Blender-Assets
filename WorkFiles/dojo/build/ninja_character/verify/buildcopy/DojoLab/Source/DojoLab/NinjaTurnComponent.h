// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "NinjaTurnComponent.generated.h"

class ACharacter;
class UCharacterMovementComponent;

/**
 * Gives the ninja's free-movement turn a duration (Cody, 2026-09-20: "there is no animation transition smoothly between running
 * forward (w) and running at an angle (w-d), its just snapping straight to the direction").
 *
 * Cause: GASP leaves `RotationRate.Yaw` at **-1**, and `UCharacterMovementComponent::GetAxisDeltaRotation` treats any negative
 * rate as 360 degrees per frame — an instant snap. GASP gets away with it because its own animation graph smooths the turn on the
 * mesh; our ninja run is a montage on the visible mesh, so nothing smooths it and the body teleports to the new heading.
 *
 * So this writes a finite yaw rate every frame, but ONLY while GASP is in orient-to-movement (free) mode. While strafing or
 * Tab-locked the rotation is GASP's business and is left exactly as it sets it.
 *
 * Tick order matters and is the same trick UNinjaStanceComponent uses: GASP's `AC_PreCMCTick` rewrites the rotation settings every
 * frame, and the movement component reads them immediately afterwards, so this must tick AFTER that component and BEFORE the
 * movement component. Writing the rate from a TG_PostPhysics tick would be a frame too late and overwritten before it was ever read.
 *
 * `ninja.turn.debug 1` logs the rate being written and the capsule yaw, which is how to tell a snap from a slow turn.
 */
UCLASS(ClassGroup=(Ninja), meta=(BlueprintSpawnableComponent))
class DEMOGAME_1_API UNinjaTurnComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UNinjaTurnComponent();

	virtual void BeginPlay() override;
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	/** Off restores GASP's instant snap. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Turn")
	bool bEnabled = true;

	/** Degrees per second at or below TurnRateSpeedLow. 540 turns the 45 degrees of a W -> W+D change in about 0.08 s. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Turn", meta=(ClampMin="1.0"))
	float TurnRate = 540.0f;

	/**
	 * Degrees per second at or above TurnRateSpeedHigh. Lower than TurnRate on purpose: a sprinting body that swings round as
	 * fast as a walking one reads as weightless, and the lag is what makes it look like leaning into the turn.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Turn", meta=(ClampMin="1.0"))
	float SprintTurnRate = 380.0f;

	/** Ground speed at which TurnRate applies. The ninja's run is 575 cm/s and its sprint 1000. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Turn", meta=(ClampMin="0.0"))
	float TurnRateSpeedLow = 450.0f;

	/** Ground speed at which SprintTurnRate applies; between the two the rate is interpolated. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Turn", meta=(ClampMin="0.0"))
	float TurnRateSpeedHigh = 700.0f;

	/**
	 * How hard the ninja gets up to speed (Cody, 2026-09-20: "make the transitions from idle to full sprinting faster" and "same
	 * with the transition from jogging to sprinting"). GASP writes its own MaxAcceleration every tick from UpdateMovement_PreCMC,
	 * so like the turn rate this has to be written after it and before the movement component reads it.
	 *
	 * Shipped behaviour measured at roughly 1450 cm/s^2: idle to 90% of sprint took 0.69 s and jog to sprint 1.01 s.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Turn")
	bool bDriveAcceleration = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Turn", meta=(ClampMin="1.0"))
	float MaxAcceleration = 3000.0f;

	/**
	 * Slowing down, which is two different settings (Cody, 2026-09-20: "apply the same transition speed when i stop sprinting
	 * and go back to jogging... jog -> idle and sprint -> idle").
	 *
	 * GroundFriction is what pulls the speed down to the gait cap while a move key is STILL HELD, so it owns sprint -> jog.
	 * BrakingDeceleration is what stops the ninja when no key is held, so it owns anything -> idle. Measured at GASP's shipped
	 * 8 / 500: sprint -> jog 0.81 s, sprint -> idle 0.52 s, jog -> idle 0.16 s.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Turn", meta=(ClampMin="0.0"))
	float GroundFriction = 20.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Turn", meta=(ClampMin="1.0"))
	float BrakingDeceleration = 6000.0f;

	/** The rate being written this frame, for the debug log and for anything that wants to lean by it. */
	UFUNCTION(BlueprintPure, Category="Ninja|Turn")
	float GetCurrentTurnRate() const { return CurrentTurnRate; }

private:
	ACharacter* GetCharacter() const;
	UCharacterMovementComponent* GetMovement() const;

	float CurrentTurnRate = 0.0f;
	/** GASP's own value, restored when this component stops driving the rate. */
	float SavedYawRate = -1.0f;
	bool bDriving = false;
	TWeakObjectPtr<AController> PrerequisiteController;
};
