// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "NinjaAirJumpComponent.generated.h"

class ACharacter;
class UAnimMontage;
class UAnimSequenceBase;

/**
 * Our double jump on Epic's Game Animation Sample character (Cody, 2026-09-19: "incorporate our double jump"). Sets the owner's
 * JumpMaxCount so GASP's own jump input (which tries a traversal first, then calls ACharacter::Jump) allows a second jump in the
 * air, and plays the airborne slice of FlipAnimation (a front flip) on the visible mesh's DefaultSlot when it happens.
 *
 * The jump itself is the character movement component's own (predicted). The flip is cosmetic: the owning client and the server
 * see JumpCurrentCount reach 2, the server bumps AirJumpCounter, and simulated proxies play it from the OnRep. A landing (any role:
 * simulated proxies never call Landed, so this watches the movement mode) cuts a flip still running.
 * The old third jump (a twisting layout flip) is parked in git: tag pre-gasp-baseline, see Docs/Parked_TripleJump.md.
 */
UCLASS(ClassGroup=(Ninja), meta=(BlueprintSpawnableComponent))
class DEMOGAME_1_API UNinjaAirJumpComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UNinjaAirJumpComponent();

	virtual void BeginPlay() override;
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
	virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;

	/** Jumps before landing, the ground jump included (2 = one air jump). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|AirJump", meta=(ClampMin="1"))
	int32 MaxJumps = 2;

	/**
	 * Full-body front flip for the air jump. BP_NinjaGasp: A_Loco_Evade_Fwd_Start (Kallari's evade flip), of which only the airborne
	 * slice FlipStartTime..FlipEndTime plays: its take-off and landing crouches would look wrong in mid-air. Empty = no flip.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|AirJump")
	TObjectPtr<UAnimSequenceBase> FlipAnimation;

	/** Clip time the flip starts at (A_Loco_Evade_Fwd_Start leaves the ground at ~0.07 s). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|AirJump", meta=(ClampMin="0.0"))
	float FlipStartTime = 0.07f;

	/** Clip time the flip starts blending out at (upright again by ~0.5 s; its landing crouch follows). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|AirJump", meta=(ClampMin="0.0"))
	float FlipEndTime = 0.5f;

	/**
	 * Back flip for the air jump, used instead of FlipAnimation while the player holds BACK at the moment of the second jump
	 * (Cody, 2026-09-20: "i meant space + s to backflip"). BP_NinjaGasp: A_Loco_Evade_Bwd_Start, Kallari's backward evade
	 * retargeted by Tools/Claude/Combat/retarget_backflip.py - the twin of the forward evade the front flip already uses.
	 * Empty = always front.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|AirJump")
	TObjectPtr<UAnimSequenceBase> BackFlipAnimation;

	/** Airborne slice of the back flip, the same idea as FlipStartTime / FlipEndTime: it leaves the ground at ~0.06 s, is
	 *  inverted at ~0.21 and has its feet back under it by ~0.55, after which its landing crouch would look wrong in mid-air. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|AirJump", meta=(ClampMin="0.0"))
	float BackFlipStartTime = 0.06f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|AirJump", meta=(ClampMin="0.0"))
	float BackFlipEndTime = 0.55f;

	/**
	 * How much of the move input has to point BACK, measured against the CAMERA's forward (so it means "S" whichever way the
	 * ninja happens to be facing), for the jump to go backwards. 1 would need S exactly and alone; 0.5 allows S+A or S+D.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|AirJump", meta=(ClampMin="0.0", ClampMax="1.0"))
	float BackFlipInputThreshold = 0.5f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|AirJump", meta=(ClampMin="0.1"))
	float FlipPlayRate = 1.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|AirJump", meta=(ClampMin="0.0"))
	float FlipBlendIn = 0.05f;

	/** Blend from the flip back to the fall pose. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|AirJump", meta=(ClampMin="0.0"))
	float FlipBlendOut = 0.15f;

	/** Faster blend when landing while still flipping. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|AirJump", meta=(ClampMin="0.0"))
	float FlipLandBlendOut = 0.1f;

private:
	ACharacter* GetCharacter() const;
	/** True when the move input points right of the camera hard enough to mean "D held". */
	bool WantsBackFlip() const;
	bool PlayFlip(bool bBack);
	void CutFlip(float BlendOutTime);

	UFUNCTION()
	void OnOwnerMovementModeChanged(ACharacter* Character, EMovementMode PrevMovementMode, uint8 PreviousCustomMode);

	UFUNCTION()
	void OnRep_AirJumpCounter();

	/** Bumped by the server on each air jump; simulated proxies play the flip in the OnRep. */
	UPROPERTY(ReplicatedUsing=OnRep_AirJumpCounter)
	uint8 AirJumpCounter = 0;

	/** Which flip that counter meant. Set before the counter is bumped so it is already correct when the OnRep reads it. */
	UPROPERTY(Replicated)
	bool bAirJumpWasBack = false;

	int32 LastJumpCount = 0;
	TWeakObjectPtr<UAnimMontage> FlipMontage;
};
