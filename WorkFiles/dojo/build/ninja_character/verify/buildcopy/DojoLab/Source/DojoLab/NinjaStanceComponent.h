// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "InputCoreTypes.h"
#include "NinjaStanceComponent.generated.h"

class AController;
class ACharacter;
class UActorComponent;
class UAnimMontage;
class UAnimSequenceBase;
class UCharacterMovementComponent;
class UEnhancedInputLocalPlayerSubsystem;
class UInputAction;
class UInputComponent;
class UInputMappingContext;

/** Where the prone cycle is on this machine (each machine plays its own copy of the clips). */
UENUM(BlueprintType)
enum class ENinjaProneState : uint8
{
	None,
	/** Getting down: ProneEnterAnimation. */
	Entering,
	/** Lying: ProneIdleAnimation, looping. */
	Prone,
	/** Getting up: ProneExitAnimation. */
	Exiting,
};

/**
 * Crouch, crouch run and prone on the GASP ninja (Cody, 2026-09-19: "Allow us to crouch and still move quickly (C, then holding
 * Shift). Make C an action instead of a toggle to crouch. Make Z to prone (lay flat on the floor, head propped up slightly, arms in
 * front)").
 *
 * Crouch: CrouchAction (C) is HELD: crouched while it is down, standing when released. It replaces GASP's own IA_Crouch toggle,
 * because IMC_NinjaGasp maps C above IMC_Sandbox and the action consumes the key. It goes through ACharacter::Crouch / UnCrouch
 * like GASP's handler did, so the movement component predicts and replicates it. Held while airborne, the crouch starts on
 * landing; GASP uncrouches when walking off a ledge, and the crouch comes back on landing while C is still down.
 *
 * Crouch run: crouched, with GASP's sprint wanted (Left Shift sets WantsToSprint in its CharacterInputState, which GASP also sends
 * to the server) and moving within CrouchRunMaxAngle of the facing (GASP's own sprint rule while strafing), MaxWalkSpeedCrouched is
 * GASP's crouch speed for that direction times CrouchRunSpeedMultiplier. GASP only has crouch WALK clips, and its motion matching
 * speeds a clip up at most MaxDynamicPlayRate (1.25). The hidden animating mesh's GlobalAnimRateScale therefore makes up the rest,
 * derived from the actual ground speed on every machine (so remote copies match without replication). This component ticks
 * between GASP's pre-movement tick (AC_PreCMCTick, which rewrites the CMC's speeds and rotation mode every frame) and the movement
 * component.
 *
 * Prone: ProneAction (Z) toggles it; Space (ProneExitKeys) or C also gets up. Prone crouches the capsule, locks movement
 * (ProneMoveSpeed, 0 by default) and rotation, blocks jutsu, and plays ProneEnterAnimation, then ProneIdleAnimation looping, then
 * ProneExitAnimation on the visible mesh's DefaultSlot. The owner predicts it and tells the server (ServerSetProne), which
 * validates it (on the ground, not mid-traversal or mid-jutsu, room for the body: HasRoomToLieDown), replicates it to the other
 * machines (bProneReplicated) and refuses with ClientRejectProne. Falling ends it at once (the owner decides and tells the server:
 * ServerAbortProne). Z and Space are ignored while getting up. Shadow clones copy their leader's prone state.
 *
 * Known online limit: the crouch-run and prone speed caps are written each tick, not carried in the saved moves, so a Shift or Z
 * edge can cost one small server correction (GASP's own gait changes have the same one-frame lag); the exact fix is a movement
 * component subclass with custom move flags.
 */
UCLASS(ClassGroup=(Ninja), meta=(BlueprintSpawnableComponent))
class DEMOGAME_1_API UNinjaStanceComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UNinjaStanceComponent();

	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
	virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;

	/** True from the moment the ninja starts getting down until it has finished getting up. */
	UFUNCTION(BlueprintPure, Category="Ninja|Stance")
	bool IsProne() const { return ProneState != ENinjaProneState::None; }

	/** True while lying or getting down (not while getting up): what a toggle, or a clone, compares against. */
	UFUNCTION(BlueprintPure, Category="Ninja|Stance")
	bool WantsProne() const { return bProneWanted; }

	UFUNCTION(BlueprintPure, Category="Ninja|Stance")
	ENinjaProneState GetProneState() const { return ProneState; }

	/** Crouched and moving at the crouch-run speed this frame (owner and server). */
	UFUNCTION(BlueprintPure, Category="Ninja|Stance")
	bool IsCrouchRunning() const { return bCrouchRunning; }

	/**
	 * Lies down (true) or gets up (false). On the owning client it is predicted and sent to the server; on the server it is
	 * applied and replicated. Ignored when it cannot happen (lying down needs the ground, no traversal, no jutsu in progress).
	 */
	UFUNCTION(BlueprintCallable, Category="Ninja|Stance")
	void SetProne(bool bProne);

	/** Held to crouch (C). Mapped in InputMappingContext; it must consume the key so GASP's IA_Crouch toggle never sees it. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Stance|Input")
	TObjectPtr<UInputAction> CrouchAction;

	/** Toggles prone (Z). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Stance|Input")
	TObjectPtr<UInputAction> ProneAction;

	/** Added for the local player if missing (IMC_NinjaGasp, shared with the jutsu and lock-on components). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Stance|Input")
	TObjectPtr<UInputMappingContext> InputMappingContext;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Stance|Input")
	int32 InputMappingPriority = 1;

	/**
	 * While prone these keys get up instead of doing their usual job (Space would jump or start a GASP traversal): a runtime mapping
	 * context maps them to ProneAction above every other context.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Stance|Input")
	TArray<FKey> ProneExitKeys = { EKeys::SpaceBar, EKeys::Gamepad_FaceButton_Bottom };

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Stance|Input")
	int32 ProneExitPriority = 100;

	/** Crouch-run speed = GASP's crouch speed for the direction (225 forward, 200 sideways, 180 back) times this. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Stance|Crouch Run", meta=(ClampMin="1.0"))
	float CrouchRunSpeedMultiplier = 2.0f;

	/** While strafing, the crouch run needs the movement within this many degrees of the facing (GASP's own sprint rule is 50). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Stance|Crouch Run", meta=(ClampMin="0.0", ClampMax="180.0"))
	float CrouchRunMaxAngle = 50.0f;

	/**
	 * The play rate GASP's motion matching already applies at most (Get_DynamicPlayRate: MaxDynamicPlayRate, 1.25 unless a clip's
	 * curve says otherwise). The animation rate scale covers only the speed beyond crouch speed x this.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Stance|Crouch Run", meta=(ClampMin="1.0"))
	float CrouchAnimAssumedMaxPlayRate = 1.25f;

	/** Upper bound of the hidden mesh's animation rate scale while crouch running. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Stance|Crouch Run", meta=(ClampMin="1.0"))
	float CrouchAnimMaxRateScale = 2.5f;

	/** How fast the animation rate scale follows the speed (per second). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Stance|Crouch Run", meta=(ClampMin="0.0"))
	float CrouchAnimRateInterpSpeed = 8.0f;

	/** Getting down: played once, then ProneIdleAnimation. Its last frame should be the idle's first. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Stance|Prone")
	TObjectPtr<UAnimSequenceBase> ProneEnterAnimation;

	/** Lying: looped while prone. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Stance|Prone")
	TObjectPtr<UAnimSequenceBase> ProneIdleAnimation;

	/** Getting up: played once from the idle pose, ending crouched; then the slot blends back to GASP's pose. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Stance|Prone")
	TObjectPtr<UAnimSequenceBase> ProneExitAnimation;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Stance|Prone", meta=(ClampMin="0.0"))
	float ProneEnterBlendIn = 0.2f;

	/** Blend from the enter clip's end into the idle loop (they should already match). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Stance|Prone", meta=(ClampMin="0.0"))
	float ProneIdleBlendIn = 0.05f;

	/** Blend from wherever the body is (lying, or still getting down) into the exit clip. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Stance|Prone", meta=(ClampMin="0.0"))
	float ProneExitBlendIn = 0.15f;

	/** Blend from the exit clip's last (crouched) pose back to GASP's crouch or standing pose. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Stance|Prone", meta=(ClampMin="0.0"))
	float ProneExitBlendOut = 0.25f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Stance|Prone", meta=(ClampMin="0.01"))
	float ProneEnterPlayRate = 1.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Stance|Prone", meta=(ClampMin="0.01"))
	float ProneExitPlayRate = 1.0f;

	/** Lying down needs room for the body (CanLieDown): how far the lying body reaches ahead of the capsule centre (head, arms). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Stance|Prone|Room", meta=(ClampMin="0.0"))
	float ProneBodyFrontReach = 70.0f;

	/** ... and behind it (legs, feet). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Stance|Prone|Room", meta=(ClampMin="0.0"))
	float ProneBodyBackReach = 120.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Stance|Prone|Room", meta=(ClampMin="1.0"))
	float ProneBodyHalfWidth = 28.0f;

	/** Half height of the tested box, whose bottom sits ProneBodyClearance above the floor (so the ground itself does not count). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Stance|Prone|Room", meta=(ClampMin="1.0"))
	float ProneBodyHalfHeight = 15.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Stance|Prone|Room", meta=(ClampMin="0.0"))
	float ProneBodyClearance = 15.0f;

	/** Both ends of the body need ground within this far below the floor (no lying over a ledge). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Stance|Prone|Room", meta=(ClampMin="0.0"))
	float ProneMaxGroundDrop = 40.0f;

	/** Ground speed while lying (0: no crawl animation yet, so the body stays put; turning is locked too). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Stance|Prone", meta=(ClampMin="0.0"))
	float ProneMoveSpeed = 0.0f;

private:
	ACharacter* GetCharacter() const;
	bool IsLocallyControlledPlayer() const;
	/** Binds the actions and adds InputMappingContext once per input component (it is recreated on each possession). */
	void UpdateInputBinding();
	void OnCrouchPressed();
	void OnCrouchReleased();
	void OnProneInput();

	/** Owner/server: keeps the held crouch, sets the crouch-run / prone speed and the prone rotation lock after GASP's pre-movement tick. */
	void UpdateMovementOverrides(float DeltaTime);
	/** Every machine: the hidden mesh's animation rate while crouch running. */
	void UpdateCrouchAnimRate(float DeltaTime);
	/** Every machine: advances the prone clips (enter -> idle, exit -> done) and ends prone on leaving the ground. */
	void UpdateProne();

	bool CanLieDown() const;
	/** A flat box along the facing is free of blocking geometry and there is ground under both ends of the body. */
	bool HasRoomToLieDown() const;
	/** Seconds a clip takes as a dynamic montage (its own RateScale times PlayRate). */
	static float ClipDuration(const UAnimSequenceBase* Clip, float PlayRate);
	/** Starts getting down / getting up on this machine (clips, capsule, exit keys); bInstant lies down with no enter clip. */
	void ApplyProne(bool bProne, bool bInstant = false);
	/** Ends prone immediately with no exit clip (fell off something, or the component is going away). */
	void AbortProne();
	/** Prone is over on this machine: releases the clip over BlendOutTime, the exit keys, and the crouch unless C is held. */
	void FinishExit(float BlendOutTime);
	void SetExitKeysActive(bool bActive);

	UFUNCTION(Server, Reliable)
	void ServerSetProne(bool bProne);

	/** The owner fell out of prone: the server ends it too (the owner is the one that sees every fall of its own pawn). */
	UFUNCTION(Server, Reliable)
	void ServerAbortProne();

	/** The server refused a predicted prone change: go back to what it has. */
	UFUNCTION(Client, Reliable)
	void ClientRejectProne(bool bServerProne);

	UFUNCTION()
	void OnRep_ProneReplicated();

	/** The server's prone state, for simulated proxies (the owner predicts its own). */
	UPROPERTY(ReplicatedUsing=OnRep_ProneReplicated)
	bool bProneReplicated = false;

	ENinjaProneState ProneState = ENinjaProneState::None;
	bool bProneWanted = false;
	double ProneClipEndTime = 0.0;
	TWeakObjectPtr<UAnimMontage> ProneMontage;

	bool bCrouchHeld = false;
	bool bCrouchRunning = false;
	/** GASP's crouch speed this frame, before this component's override (every machine computes it). */
	float GaspCrouchSpeed = 0.0f;
	/** What this component last wrote to MaxWalkSpeedCrouched, to tell GASP's fresh value from its own stale one. */
	float LastWrittenCrouchSpeed = -1.0f;
	float CrouchAnimRate = 1.0f;
	/** The movement component's MinAnalogWalkSpeed at BeginPlay (lowered to ProneMoveSpeed while prone). */
	float SavedMinAnalogWalkSpeed = 0.0f;
	/** ninja.stance.debug: the visible feet last frame. */
	FVector DebugLastLeftFoot = FVector::ZeroVector;
	FVector DebugLastRightFoot = FVector::ZeroVector;
	bool bDebugHasFeet = false;

	TWeakObjectPtr<UInputComponent> BoundInputComponent;
	/** The controller this component currently ticks after. */
	TWeakObjectPtr<AController> PrerequisiteController;
	UPROPERTY(Transient)
	TObjectPtr<UInputMappingContext> ProneExitContext;
	TWeakObjectPtr<UEnhancedInputLocalPlayerSubsystem> ProneExitSubsystem;
};
