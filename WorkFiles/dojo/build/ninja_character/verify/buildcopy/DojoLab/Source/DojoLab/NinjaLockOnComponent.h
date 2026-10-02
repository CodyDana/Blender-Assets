// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "NinjaLockOnComponent.generated.h"

class AHUD;
class UCanvas;
class UInputAction;
class UInputComponent;
class UInputMappingContext;

/**
 * Tab targeting and teams (Cody, 2026-09-19: keep the Tab targeting and the training dummy when GASP replaced our movement).
 *
 * Every fighter that can be targeted carries one, with its TeamId (the player 0, BP_TrainingDummy 1). On the local player, Tab
 * (LockOnAction) toggles the focus on the best hostile in range: in front of the camera first, then the smallest angle, with the
 * distance as a tie-break; seen from the camera; never a shadow clone. While focused, UNinjaLockOnCameraModifier pulls the view
 * (the control rotation, which GASP's camera and movement follow) toward the target, a diamond marker is drawn over it, and GASP's
 * strafe and aim are on (bStrafeWhileLocked, bAimWhileLocked) so the character faces the target while circling it and turns in
 * place to it when standing. The focus lets go past LockOnBreakRange or when the target is gone. The target, camera and marker
 * are the local player's own; only the strafe / aim flags reach the server, through GASP's input-state event.
 */
UCLASS(ClassGroup=(Ninja), meta=(BlueprintSpawnableComponent))
class DEMOGAME_1_API UNinjaLockOnComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UNinjaLockOnComponent();

	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
	virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;

	UFUNCTION(BlueprintCallable, Category="Ninja|LockOn")
	void ToggleLockOn();

	UFUNCTION(BlueprintCallable, Category="Ninja|LockOn")
	void ClearLockOn();

	/** The focused target, or null. A shadow clone reports its leader's. */
	UFUNCTION(BlueprintPure, Category="Ninja|LockOn")
	AActor* GetLockTarget() const;

	/** True when Other fights on another side (different TeamId; shadow clones are on their leader's side). */
	UFUNCTION(BlueprintPure, Category="Ninja|LockOn")
	bool IsHostileTo(const AActor* Other) const;

	/** Side this fighter is on. The player is 0; BP_TrainingDummy is 1. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Replicated, Category="Ninja|LockOn")
	uint8 TeamId = 0;

	/** False: never chosen as a target (a fighter can still target others). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|LockOn")
	bool bTargetable = true;

	/** Tab; mapped in the jutsu component's InputMappingContext (IMC_NinjaGasp). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|LockOn|Input")
	TObjectPtr<UInputAction> LockOnAction;

	/** Added for the local player if not already there (the jutsu component usually adds the same context). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|LockOn|Input")
	TObjectPtr<UInputMappingContext> InputMappingContext;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|LockOn|Input")
	int32 InputMappingPriority = 1;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|LockOn", meta=(ClampMin="0.0"))
	float LockOnRange = 2000.0f;

	/** The focus lets go past this distance. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|LockOn", meta=(ClampMin="0.0"))
	float LockOnBreakRange = 2800.0f;

	/** Targets further than this from the camera's forward (degrees) are only picked when nothing is closer to it. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|LockOn", meta=(ClampMin="0.0", ClampMax="180.0"))
	float LockOnPreferredAngle = 70.0f;

	/** How fast the view turns to the target (per second, as a fraction of the remaining angle). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|LockOn", meta=(ClampMin="0.0"))
	float LockCameraInterpSpeed = 6.0f;

	/** Fraction of the mouse's yaw that still reaches the camera while focused: a nudge the focus pulls back (0 = hard lock). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|LockOn", meta=(ClampMin="0.0", ClampMax="1.0"))
	float LockCameraYawNudgeScale = 0.3f;

	/** Turn on GASP's strafe rotation mode while focused (the character faces the target instead of its movement). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|LockOn")
	bool bStrafeWhileLocked = true;

	/**
	 * Turn on GASP's aim while focused. GASP's animation Blueprint turns the character in place only while aiming (ShouldTurnInPlace
	 * reads InputState.WantsToAim), so without it a standing ninja keeps its old facing and only its aim offset follows, up to 115
	 * degrees. It also switches GASP's camera to its closer over-the-shoulder aim framing.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|LockOn")
	bool bAimWhileLocked = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|LockOn|Marker")
	FLinearColor LockMarkerColor = FLinearColor(1.0f, 0.25f, 0.15f, 0.9f);

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|LockOn|Marker", meta=(ClampMin="1.0"))
	float LockMarkerSize = 12.0f;

private:
	void UpdateInputBinding();
	void OnLockOnInput();
	AActor* FindLockOnTarget() const;
	bool IsValidTarget(const AActor* Candidate, float MaxRange) const;
	void SetMarkerDrawn(bool bDrawn);
	void DrawLockMarker(AHUD* HUD, UCanvas* Canvas);
	/**
	 * Sets GASP's "Wants To Strafe" / "Wants To Aim" in the owner's CharacterInputState while focused (bStrafeWhileLocked /
	 * bAimWhileLocked), restores the player's own values on release, and sends the state to the server the way GASP's input does.
	 */
	void ApplyLockStance(bool bLocked);

	TWeakObjectPtr<AActor> LockTarget;
	TWeakObjectPtr<UInputComponent> BoundInputComponent;
	FDelegateHandle MarkerDelegate;
	bool bLockStanceApplied = false;
	bool bSavedStrafe = false;
	bool bSavedAim = false;
};
