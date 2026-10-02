// Copyright Epic Games, Inc. All Rights Reserved.

#include "NinjaTurnComponent.h"

#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"
#include "HAL/IConsoleManager.h"

DEFINE_LOG_CATEGORY_STATIC(LogNinjaTurn, Log, All);

namespace NinjaTurnConst
{
	/** GASP's component whose tick runs UpdateRotation_PreCMC, just before the movement component reads the settings. */
	const FName GaspPreMovementTickComponent(TEXT("AC_PreCMCTick"));
}

static TAutoConsoleVariable<int32> CVarNinjaTurnDebug(
	TEXT("ninja.turn.debug"), 0, TEXT("Log the yaw rate this component writes and the capsule yaw each frame."), ECVF_Default);

/** Same reason as the turn rate: how hard the ninja gets up to speed is judged by playing, so it is tunable live. */
static TAutoConsoleVariable<float> CVarNinjaAccel(
	TEXT("ninja.accel"), 0.0f,
	TEXT("Override the ninja's ground acceleration in cm/s^2. 0 uses the component's value; -1 hands it back to GASP."),
	ECVF_Default);

/** Slowing down, the two halves of it: friction while a key is held, braking when none is. 0 = use the component's value. */
static TAutoConsoleVariable<float> CVarNinjaFriction(
	TEXT("ninja.friction"), 0.0f,
	TEXT("Override the ninja's ground friction, which owns sprint -> jog. 0 uses the component's value."), ECVF_Default);

static TAutoConsoleVariable<float> CVarNinjaBraking(
	TEXT("ninja.braking"), 0.0f,
	TEXT("Override the ninja's braking deceleration in cm/s^2, which owns anything -> idle. 0 uses the component's value."),
	ECVF_Default);

/** Feel is judged by playing, not by reading numbers, so the rate can be dialled in live without a rebuild. */
static TAutoConsoleVariable<float> CVarNinjaTurnRate(
	TEXT("ninja.turn.rate"), 0.0f,
	TEXT("Override the ninja's free-movement turn rate in deg/s. 0 uses the component's own values; -1 restores GASP's instant snap."),
	ECVF_Default);

UNinjaTurnComponent::UNinjaTurnComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	// Must land between GASP's AC_PreCMCTick (which rewrites the rotation settings) and the movement component that reads them.
	PrimaryComponentTick.TickGroup = TG_PrePhysics;
}

ACharacter* UNinjaTurnComponent::GetCharacter() const
{
	return Cast<ACharacter>(GetOwner());
}

UCharacterMovementComponent* UNinjaTurnComponent::GetMovement() const
{
	const ACharacter* Character = GetCharacter();
	return Character ? Character->GetCharacterMovement() : nullptr;
}

void UNinjaTurnComponent::BeginPlay()
{
	Super::BeginPlay();
	ACharacter* Character = GetCharacter();
	UCharacterMovementComponent* Movement = GetMovement();
	if (!Character || !Movement)
	{
		return;
	}
	SavedYawRate = Movement->RotationRate.Yaw;

	UActorComponent* GaspPreMovement = nullptr;
	for (UActorComponent* Component : Character->GetComponents())
	{
		if (Component && Component->GetFName() == NinjaTurnConst::GaspPreMovementTickComponent)
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
		UE_LOG(LogNinjaTurn, Warning, TEXT("%s: no %s component; GASP may overwrite the turn rate before the move is simulated."),
			*GetNameSafe(Character), *NinjaTurnConst::GaspPreMovementTickComponent.ToString());
	}
	Movement->AddTickPrerequisiteComponent(this);
}

void UNinjaTurnComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	ACharacter* Character = GetCharacter();
	UCharacterMovementComponent* Movement = GetMovement();
	if (!Character || !Movement)
	{
		return;
	}
	// After the controller, so this frame's input has already produced the acceleration the character will turn towards.
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

	// Acceleration is written every frame for the same reason the yaw rate is: GASP's AC_PreCMCTick puts its own value back just
	// before this runs. Unlike the turn rate this applies in every rotation mode - getting up to speed should feel the same
	// whether or not you are locked on.
	const float AccelOverride = CVarNinjaAccel.GetValueOnGameThread();
	if (bDriveAcceleration && AccelOverride >= 0.0f)
	{
		Movement->MaxAcceleration = FMath::IsNearlyZero(AccelOverride) ? MaxAcceleration : AccelOverride;

		// Friction pulls the speed down to the gait cap while a key is still held (sprint -> jog); braking stops the ninja when
		// nothing is held (anything -> idle). GASP rewrites both every tick, so both are written here too.
		const float FrictionOverride = CVarNinjaFriction.GetValueOnGameThread();
		Movement->GroundFriction = FMath::IsNearlyZero(FrictionOverride) ? GroundFriction : FrictionOverride;
		const float BrakingOverride = CVarNinjaBraking.GetValueOnGameThread();
		Movement->BrakingDecelerationWalking = FMath::IsNearlyZero(BrakingOverride) ? BrakingDeceleration : BrakingOverride;
	}

	// Only free movement. Strafing and Tab-locked rotation are GASP's, and it wants its own instant yaw there.
	const bool bFreeTurning = bEnabled && Movement->bOrientRotationToMovement && !Movement->bUseControllerDesiredRotation;
	if (!bFreeTurning)
	{
		if (bDriving)
		{
			Movement->RotationRate.Yaw = SavedYawRate;
			bDriving = false;
			CurrentTurnRate = 0.0f;
		}
		return;
	}

	FVector Velocity = Character->GetVelocity();
	Velocity.Z = 0.0f;
	const float Speed = Velocity.Size();
	const float Alpha = (TurnRateSpeedHigh > TurnRateSpeedLow)
		? FMath::Clamp((Speed - TurnRateSpeedLow) / (TurnRateSpeedHigh - TurnRateSpeedLow), 0.0f, 1.0f)
		: 0.0f;
	CurrentTurnRate = FMath::Lerp(TurnRate, SprintTurnRate, Alpha);
	// `ninja.turn.rate` wins while it is non-zero, so the feel can be dialled in during PIE.
	if (const float Override = CVarNinjaTurnRate.GetValueOnGameThread(); !FMath::IsNearlyZero(Override))
	{
		CurrentTurnRate = Override;
	}

	if (!bDriving)
	{
		SavedYawRate = Movement->RotationRate.Yaw;
		bDriving = true;
	}
	// Written every frame: GASP's AC_PreCMCTick puts its own value back just before this runs.
	Movement->RotationRate.Yaw = CurrentTurnRate;

	if (CVarNinjaTurnDebug.GetValueOnGameThread() != 0)
	{
		UE_LOG(LogNinjaTurn, Log, TEXT("%s: turn rate %.0f deg/s at %.0f cm/s, capsule yaw %.0f"),
			*GetNameSafe(Character), CurrentTurnRate, Speed, Character->GetActorRotation().Yaw);
	}
}
