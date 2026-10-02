// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "NinjaGroundSeal.generated.h"

class UDecalComponent;
class UMaterialInstanceDynamic;
class UMaterialInterface;

/**
 * A seal pattern projected onto the floor that burns outward from its centre, holds, then fades away (the Summoning
 * Technique's seal). Spawn it at the planted hand with its X axis along the caster's facing.
 *
 * The decal material reads two scalar parameters: RevealParameter (the radius of the revealed area in the texture's UV
 * space, 0 at the centre) and FadeParameter (overall opacity, 1 while shown).
 */
UCLASS()
class DEMOGAME_1_API ANinjaGroundSeal : public AActor
{
	GENERATED_BODY()

public:
	ANinjaGroundSeal();

	virtual void Tick(float DeltaSeconds) override;

protected:
	virtual void BeginPlay() override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Seal")
	TObjectPtr<USceneComponent> Root;

	/** Projects straight down; its DecalSize Y/Z are the half-extents of the seal on the floor (cm). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Seal")
	TObjectPtr<UDecalComponent> Decal;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Seal")
	TObjectPtr<UMaterialInterface> SealMaterial;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Seal")
	FName RevealParameter = TEXT("Front");

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Seal")
	FName FadeParameter = TEXT("Fade");

	/** Pause after the palm lands before the pattern starts spreading. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Seal", meta=(ClampMin="0.0"))
	float RevealDelay = 0.2f;

	/** Time for the reveal to reach RevealEnd, easing out (fast start, slow finish). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Seal", meta=(ClampMin="0.05"))
	float RevealDuration = 2.25f;

	/** Reveal radius at the end, in UV units (0.5 is the texture edge; the soft band needs a little extra). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Seal", meta=(ClampMin="0.0"))
	float RevealEnd = 0.6f;

	/** Seconds the finished seal stays on the floor before fading. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Seal", meta=(ClampMin="0.0"))
	float HoldTime = 2.5f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Seal", meta=(ClampMin="0.01"))
	float FadeOutTime = 0.8f;

private:
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> MaterialInstance;
	double StartTime = 0.0;
};
