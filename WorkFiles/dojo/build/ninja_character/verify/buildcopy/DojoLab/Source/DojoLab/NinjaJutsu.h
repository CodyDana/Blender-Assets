// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "NinjaJutsu.generated.h"

class ANinjaFireball;
class UAnimSequenceBase;
class UInputAction;
class USoundBase;

/** What happens when a jutsu's last seal completes. */
UENUM(BlueprintType)
enum class ENinjaJutsuRelease : uint8
{
	/** Only the completion sound and the OnJutsuCompleted event. */
	None,
	/** Spawn a shadow clone beside the caster (Shadow Clone Technique). */
	ShadowClone,
	/** Launch FireballClass from the caster's mouth (Great Fireball Technique). */
	Fireball,
};

/**
 * One entry in a ninja's jutsu list: its hand seals, the input that casts it and what it releases.
 * Create one data asset per jutsu and add it to a UNinjaJutsuComponent's Jutsus (BP_NinjaGasp's NinjaJutsu component).
 */
UCLASS(BlueprintType)
class DEMOGAME_1_API UNinjaJutsu : public UPrimaryDataAsset
{
	GENERATED_BODY()

public:
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Jutsu")
	FText DisplayName;

	/**
	 * Optional held upper-body pose before the first seal (e.g. biting the thumb for Summoning). It plays on the seal layer
	 * without the seal sound or OnJutsuSeal, and is cancelled like a seal.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Jutsu")
	TObjectPtr<UAnimSequenceBase> OpeningAnimation;

	/** Seconds the opening pose is held before the first seal. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Jutsu", meta=(ClampMin="0.05"))
	float OpeningHoldTime = 0.35f;

	/** Hand-seal poses played in order. Each is a held pose (e.g. A_Seal_Snake). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Jutsu")
	TArray<TObjectPtr<UAnimSequenceBase>> Seals;

	/** Pressing this action casts the jutsu. Leave empty for jutsu started only from code or Blueprint. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Jutsu")
	TObjectPtr<UInputAction> InputAction;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Jutsu")
	ENinjaJutsuRelease Release = ENinjaJutsuRelease::None;

	/**
	 * Optional voice line that starts with the hand signs (the opening pose, or the first seal): e.g. "Kage Bunshin no Jutsu", or
	 * "Katon... Goukakyuu no Jutsu" for the Great Fireball. It is cut short (quick fade) if the signing is cancelled before the
	 * jutsu releases, and runs on through the release otherwise. The leader only; clones sign silently.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Jutsu|Voice")
	TObjectPtr<USoundBase> StartVoice;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Jutsu|Voice", meta=(ClampMin="0.0"))
	float StartVoiceVolume = 1.0f;

	/** Played when the jutsu releases. Falls back to the character's JutsuCompleteSound when empty. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Jutsu")
	TObjectPtr<USoundBase> CompleteSound;

	/** Off for jutsu that release silently (no CompleteSound and no fallback). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Jutsu")
	bool bPlayCompleteSound = true;

	/**
	 * Optional full-body move played after the last seal (e.g. the Summoning palm slam). Movement, jumps (and GASP's
	 * traversals) and other jutsu are locked while it plays. The jutsu releases FinisherReleaseTime seconds into it.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Jutsu|Finisher")
	TObjectPtr<UAnimSequenceBase> FinisherAnimation;

	/** Seconds into FinisherAnimation (at play rate 1) when the jutsu releases: sound, release, OnJutsuCompleted. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Jutsu|Finisher", meta=(ClampMin="0.0"))
	float FinisherReleaseTime = 0.0f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Jutsu|Finisher", meta=(ClampMin="0.05"))
	float FinisherPlayRate = 1.0f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Jutsu|Finisher", meta=(ClampMin="0.0"))
	float FinisherBlendInTime = 0.1f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Jutsu|Finisher", meta=(ClampMin="0.0"))
	float FinisherBlendOutTime = 0.35f;

	/**
	 * Bone of the hand that touches the ground in the finisher (e.g. hand_r). When set, OnJutsuHandPlanted fires at the
	 * release with the floor point under that hand, for effects such as a summoning seal pattern.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Jutsu|Finisher")
	FName FinisherHandBone;

	/**
	 * Optional actor spawned where the hand plants (e.g. the summoning seal, ANinjaGroundSeal), facing the caster's direction.
	 * Needs FinisherHandBone. It manages its own lifetime.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Jutsu|Finisher", meta=(EditCondition="FinisherHandBone != NAME_None"))
	TSubclassOf<AActor> HandPlantedEffectClass;

	/**
	 * Optional effect actor held during the finisher (e.g. the Chidori lightning). It is spawned at the release, attached to
	 * FinisherEffectBone, and told to stop (ANinjaHandEffect::StopEffect, or destroyed for other actors) when the finisher
	 * ends or is cancelled.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Jutsu|Finisher")
	TSubclassOf<AActor> FinisherEffectClass;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Jutsu|Finisher")
	FName FinisherEffectBone = TEXT("hand_r");

	/** Offset from FinisherEffectBone in the bone's space, in cm. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Jutsu|Finisher")
	FVector FinisherEffectOffset = FVector::ZeroVector;

	/** Projectile launched by the Fireball release. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Jutsu|Fireball", meta=(EditCondition="Release == ENinjaJutsuRelease::Fireball"))
	TSubclassOf<ANinjaFireball> FireballClass;

	/** Where the fireball appears, relative to the head bone in the caster's facing space (X forward, Y right, Z up), in cm. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Jutsu|Fireball", meta=(EditCondition="Release == ENinjaJutsuRelease::Fireball"))
	FVector FireballSpawnOffset = FVector(35.0f, 0.0f, -5.0f);
};
