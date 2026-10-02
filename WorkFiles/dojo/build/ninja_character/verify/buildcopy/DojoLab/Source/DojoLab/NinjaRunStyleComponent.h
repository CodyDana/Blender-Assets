// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "NinjaRunStyleComponent.generated.h"

class ACharacter;
class UAnimMontage;
class UAnimSequenceBase;

/**
 * Makes the ninja RUN like the Bare Ninja AnimSet instead of like GASP (Cody, 2026-09-20: "replace the run animation with the
 * ninja pack's run animation (run_02)"). The pack's forward runs are the arms-trailing, deep-lean ninja run; both `move_run` and
 * `move_run_front` are that same style.
 *
 * Why an override and not a real swap: GASP's run is not one clip. It is ~300 clips (loops, starts, stops, pivots, turns, spins,
 * per-foot variants) inside motion-matching databases, authored on SK_UEFN_Mannequin - a different skeleton from the pack's UE5
 * Manny. There is nothing to "replace", and the pack's single 0.53 s loop could not feed motion matching anyway.
 *
 * So this is cosmetic only. GASP still owns movement, speed, turning, the camera and every other gait; this just plays the ninja
 * run as a LOOPING montage on the visible mesh's full-body slot while the character is actually running forward on the ground,
 * with the play rate matched to real speed so the feet don't skate. Walking, strafing, backpedalling, crouching, jumping and
 * traversals all fall back to GASP untouched. The trade is that the pack has no start / stop / pivot clips, so entering and
 * leaving the run is a blend rather than a planted transition.
 *
 * Purely velocity-driven, so every machine reaches the same answer on its own and nothing is replicated.
 * `ninja.run.style 0` turns it off live for an A/B; `ninja.run.debug 1` logs when it starts and stops.
 */
UCLASS(ClassGroup=(Ninja), meta=(BlueprintSpawnableComponent))
class DEMOGAME_1_API UNinjaRunStyleComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UNinjaRunStyleComponent();

	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|RunStyle")
	bool bEnabled = true;

	/**
	 * RUN tier: plain W, which really moves at 500 cm/s. BP_NinjaGasp: `/Game/Ninja/Animation/Loco/A_NinjaRun_InPlace`, from the
	 * pack's move_run (Cody, 2026-09-20: "if i hit only w, it should run with the move_run"). At 500 against the clip's 540.7 the
	 * play rate lands on 0.92, so it matches the ground almost exactly. Empty leaves this tier on GASP.
	 *
	 * Any clip here MUST be in place. The raw pack clips travel ~290 cm on `root` per cycle, which as a montage would slide the
	 * body off the capsule and snap back every loop; make_ninja_run.py strips that.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|RunStyle")
	TObjectPtr<UAnimSequenceBase> RunAnimation;

	/** Ground speed RunAnimation was animated at (cm/s), so PlayRate = speed / this. move_run measures 540.7. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|RunStyle", meta=(ClampMin="1.0"))
	float RunClipSpeed = 540.7f;

	/**
	 * SPRINT tier, used from SprintMinSpeed up. BP_NinjaGasp: `/Game/Ninja/Animation/Loco/A_NinjaSprint_InPlace`, built from the
	 * pack's move_run_front (Cody: "for our sprint use the other ninja run"). Empty falls back to RunAnimation.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|RunStyle")
	TObjectPtr<UAnimSequenceBase> SprintAnimation;

	/** Ground speed SprintAnimation was animated at (cm/s). move_run_front measures 567.0. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|RunStyle", meta=(ClampMin="1.0"))
	float SprintClipSpeed = 567.0f;

	/** At or above this the sprint clip is used instead of the run clip. Sits between the run's 500 and the sprint's 700. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|RunStyle", meta=(ClampMin="0.0"))
	float SprintMinSpeed = 600.0f;

	/**
	 * Below this neither tier takes the body and GASP keeps it. Measured (Tools/Claude/Combat/gait_speeds.ps1, 2026-09-20):
	 * plain W **500**, Shift+W **700**, Ctrl-toggled walk **200**, Shift+A strafe **350** cm/s. 300 therefore lets plain W in and
	 * keeps the walk out.
	 *
	 * Measure with W FIRST: GASP's Left Ctrl walk is a TOGGLE, not a hold, so taking the walk reading first leaves the character
	 * walking and every later reading comes back 200. That mistake is what first made plain W look like a 200 cm/s jog.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|RunStyle", meta=(ClampMin="0.0"))
	float MinSpeed = 300.0f;

	/**
	 * WALK tier, below MinSpeed (Cody, 2026-09-26: the female MetaHuman's runway walk, copied from an animation reel). Empty (the
	 * ninja's default) leaves walking on GASP. `/Game/Ninja/Animation/Walk/A_Catwalk_InPlace` is in place, authored on Manny, and
	 * steps at 56.9 cm/s - a slow runway pace, so the character's walk speed should be near that for the feet to match.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|RunStyle")
	TObjectPtr<UAnimSequenceBase> WalkAnimation;

	/** Ground speed WalkAnimation was animated at (cm/s). make_catwalk.py prints it ("in-place walk speed"). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|RunStyle", meta=(ClampMin="1.0"))
	float WalkClipSpeed = 56.9f;

	/** The walk tier starts at this speed (standing still stays on GASP's idle). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|RunStyle", meta=(ClampMin="0.0"))
	float WalkMinSpeed = 15.0f;

	/** The walk's own play-rate range: a runway walk played much faster than it was animated stops reading as one. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|RunStyle", meta=(ClampMin="0.1"))
	float WalkMinPlayRate = 0.5f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|RunStyle", meta=(ClampMin="0.1"))
	float WalkMaxPlayRate = 2.0f;

	/** Hysteresis: once running, the override holds until speed drops this much below MinSpeed, so it can't flicker at the edge. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|RunStyle", meta=(ClampMin="0.0"))
	float SpeedHysteresis = 60.0f;

	/**
	 * Only when moving roughly the way the ninja faces. The pack has no strafe or backpedal run, so sideways and backwards
	 * movement stays on GASP's motion matching rather than showing a forward run crabbing sideways.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|RunStyle", meta=(ClampMin="0.0", ClampMax="180.0"))
	float MaxForwardAngle = 50.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|RunStyle", meta=(ClampMin="0.0"))
	float BlendIn = 0.25f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|RunStyle", meta=(ClampMin="0.0"))
	float BlendOut = 0.25f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|RunStyle", meta=(ClampMin="0.1"))
	float MinPlayRate = 0.7f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|RunStyle", meta=(ClampMin="0.1"))
	float MaxPlayRate = 1.6f;

	/**
	 * Drives `NinjaLocoWeight` in ABP_NinjaVisual, which gates the Stride Warping and Foot Placement nodes at the end of the
	 * graph (`Tools/Claude/Combat/abp_foot_lock.ps1`). 1 only while this component owns the body, so attacks, finishers, seals
	 * and GASP's own animation keep their feet untouched. Faded rather than switched, or the foot IK pops on and off.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|RunStyle")
	bool bDriveFootLock = true;

	/** Seconds for NinjaLocoWeight to reach its target. Matches the montage blends so the IK arrives with the pose. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|RunStyle", meta=(ClampMin="0.01"))
	float FootLockBlendTime = 0.25f;

	/** Safety rails on the stride scale pushed to the warping node; 1 means the play rate already matches the ground. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|RunStyle", meta=(ClampMin="0.1"))
	float MinStrideScale = 0.6f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|RunStyle", meta=(ClampMin="0.1"))
	float MaxStrideScale = 1.8f;

	UFUNCTION(BlueprintPure, Category="Ninja|RunStyle")
	bool IsRunStyleActive() const { return bRunning; }

private:
	ACharacter* GetCharacter() const;
	/** Everything that must be true for the ninja run to own the body this frame. */
	bool ShouldRun(float& OutSpeed) const;
	/** The tier for this speed, and the clip speed to match the play rate against. Null when neither tier has a clip. */
	UAnimSequenceBase* ChooseClip(float Speed, float& OutClipSpeed) const;
	void StartOrUpdateRun(float Speed);
	/** Stops OUR montage by pointer: StopSlotMontages would also kill an attack or a finisher sharing the slot. */
	void StopRun();

	/** `ninja.run.debug 2`: per-frame planted-foot slide and body-vs-travel angle, for diagnosing foot sliding. */
	void LogSlide(float DeltaTime, float Speed);
	/** Pushes NinjaLocoWeight / NinjaStrideScale to ABP_NinjaVisual, which gate and drive the foot-lock nodes. */
	void UpdateFootLock(float DeltaTime, float Speed);

	float LocoWeight = 0.0f;
	float StrideScale = 1.0f;

	bool bRunning = false;
	TWeakObjectPtr<UAnimMontage> RunMontage;
	/** Which clip the playing montage was built from, so crossing the sprint threshold restarts it on the other one. */
	TWeakObjectPtr<UAnimSequenceBase> ActiveClip;

	FVector DebugLastLeftFoot = FVector::ZeroVector;
	FVector DebugLastRightFoot = FVector::ZeroVector;
	bool bDebugHasFeet = false;
};
