// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "NinjaFireball.generated.h"

class UNiagaraComponent;
class UNiagaraSystem;
class UPointLightComponent;
class UProjectileMovementComponent;
class USoundBase;
class USphereComponent;

/**
 * Fireball released by a Fireball jutsu. It flies straight, swells from StartSize to full size just after launch,
 * and bursts on the first wall or character it hits (never its caster or the caster's clones) or when its lifetime ends.
 *
 * Assign the flame effect on the FlameEffect component and the burst in ImpactEffect in a Blueprint subclass.
 * The growth drives the collision radius, the glow and the flame system's FlameScaleParameter user variable.
 */
UCLASS()
class DEMOGAME_1_API ANinjaFireball : public AActor
{
	GENERATED_BODY()

public:
	ANinjaFireball();

	virtual void Tick(float DeltaSeconds) override;

	/** Bursts the fireball where it is and removes it. */
	UFUNCTION(BlueprintCallable, Category="Fireball")
	void Burst();

protected:
	virtual void BeginPlay() override;

	/** Fires just before the burst effect spawns (for damage, camera shake, and so on). */
	UFUNCTION(BlueprintImplementableEvent, Category="Fireball")
	void OnBurst(AActor* HitActor);

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Fireball")
	TObjectPtr<USphereComponent> Collision;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Fireball")
	TObjectPtr<UNiagaraComponent> FlameEffect;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Fireball")
	TObjectPtr<UPointLightComponent> Glow;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Fireball")
	TObjectPtr<UProjectileMovementComponent> Movement;

	/** Seconds before the fireball bursts on its own. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Fireball", meta=(ClampMin="0.1"))
	float Lifetime = 2.0f;

	/** Collision radius at full size, in cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Fireball", meta=(ClampMin="1.0"))
	float Radius = 50.0f;

	/** Fraction of full size at launch; it grows to full size over GrowTime. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Fireball", meta=(ClampMin="0.01", ClampMax="1.0"))
	float StartSize = 0.2f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Fireball", meta=(ClampMin="0.0"))
	float GrowTime = 0.4f;

	/** Float user variable on the flame system that sets its size (NS_Fire: "Flame Scale"). None leaves the effect as authored. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Fireball")
	FName FlameScaleParameter = TEXT("Flame Scale");

	/** Value of FlameScaleParameter at full size. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Fireball", meta=(ClampMin="0.0"))
	float FlameScale = 1.0f;

	/** Glow intensity at full size. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Fireball", meta=(ClampMin="0.0"))
	float GlowIntensity = 20000.0f;

	/** Played attached to the fireball as it launches. */
	UPROPERTY(EditAnywhere, Category="Fireball|Audio")
	TObjectPtr<USoundBase> LaunchSound;

	UPROPERTY(EditAnywhere, Category="Fireball|Audio", meta=(ClampMin="0.0"))
	float LaunchVolume = 1.0f;

	UPROPERTY(EditAnywhere, Category="Fireball|Burst")
	TObjectPtr<UNiagaraSystem> ImpactEffect;

	UPROPERTY(EditAnywhere, Category="Fireball|Burst")
	FVector ImpactEffectScale = FVector(1.0f);

	UPROPERTY(EditAnywhere, Category="Fireball|Audio")
	TObjectPtr<USoundBase> ImpactSound;

private:
	UFUNCTION()
	void OnCollisionOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp, int32 OtherBodyIndex,
		bool bFromSweep, const FHitResult& SweepResult);

	UFUNCTION()
	void OnProjectileStop(const FHitResult& ImpactResult);

	/** True for the caster and anything on the caster's side (its clones, or a clone's leader and siblings). */
	bool IsFriendly(const AActor* Actor) const;

	void BurstOn(AActor* HitActor);
	/** Applies Size (fraction of full size) to the collision, glow and flame. */
	void ApplySize(float Size);

	double SpawnTime = 0.0;
	float CurrentSize = 1.0f;
	bool bBurst = false;
};
