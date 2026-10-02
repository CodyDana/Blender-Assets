// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "NinjaHandEffect.generated.h"

class UAudioComponent;
class UNiagaraComponent;
class UPointLightComponent;

/**
 * An effect held in a ninja's hand during a jutsu finisher (e.g. the Chidori lightning). The character attaches it to a bone
 * when the jutsu releases and calls StopEffect when the finisher ends or is cancelled; it then fades and destroys itself.
 *
 * Assign the Niagara system, light and looping sound in a Blueprint subclass.
 */
UCLASS()
class DEMOGAME_1_API ANinjaHandEffect : public AActor
{
	GENERATED_BODY()

public:
	ANinjaHandEffect();

	virtual void Tick(float DeltaSeconds) override;

	/** Stops emitting, fades the light and sound over FadeOutTime, then destroys the actor. Safe to call more than once. */
	UFUNCTION(BlueprintCallable, Category="Hand Effect")
	void StopEffect();

protected:
	virtual void BeginPlay() override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Hand Effect")
	TObjectPtr<USceneComponent> Root;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Hand Effect")
	TObjectPtr<UNiagaraComponent> Effect;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Hand Effect")
	TObjectPtr<UPointLightComponent> Glow;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Hand Effect")
	TObjectPtr<UAudioComponent> Sound;

	/** Glow intensity; it flickers randomly between (1 - FlickerAmount) and 1 times this, FlickerRate times a second. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Hand Effect", meta=(ClampMin="0.0"))
	float GlowIntensity = 30000.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Hand Effect", meta=(ClampMin="0.0", ClampMax="1.0"))
	float FlickerAmount = 0.6f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Hand Effect", meta=(ClampMin="0.0"))
	float FlickerRate = 24.0f;

	/** Seconds for the glow to reach full intensity after spawning. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Hand Effect", meta=(ClampMin="0.0"))
	float FadeInTime = 0.12f;

	/** Seconds the glow and sound take to fade after StopEffect; the particles already alive finish on their own. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Hand Effect", meta=(ClampMin="0.0"))
	float FadeOutTime = 0.25f;

	/** Lifetime after StopEffect before the actor is destroyed (lets the last arcs die out). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Hand Effect", meta=(ClampMin="0.0"))
	float LingerTime = 0.6f;

private:
	double SpawnTime = 0.0;
	double StopTime = -1.0;
	double NextFlickerTime = 0.0;
	float FlickerScale = 1.0f;
};
