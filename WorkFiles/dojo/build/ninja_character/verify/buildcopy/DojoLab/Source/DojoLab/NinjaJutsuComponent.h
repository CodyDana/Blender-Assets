// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "InputCoreTypes.h"
#include "NinjaJutsuComponent.generated.h"

class AController;
class ACharacter;
class UAnimMontage;
class UAnimSequenceBase;
class UAudioComponent;
class UEnhancedInputLocalPlayerSubsystem;
class UInputAction;
class UInputComponent;
class UInputMappingContext;
class UNiagaraSystem;
class UNinjaJutsu;
class USkeletalMeshComponent;
class USoundBase;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FNinjaJutsuSealSignature, UNinjaJutsu*, Jutsu, int32, SealIndex);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FNinjaJutsuSignature, UNinjaJutsu*, Jutsu);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_ThreeParams(FNinjaJutsuHandPlantedSignature, UNinjaJutsu*, Jutsu, FVector, GroundLocation, FRotator, Facing);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FNinjaCloneSignature, ACharacter*, Clone);

/**
 * Hand-seal jutsu for any character (2026-09-19: the ninja became Epic's Game Animation Sample character, BP_NinjaGasp, and only
 * the hand seals and their results were kept; this is that system, moved out of the old ANinjaCharacter).
 *
 * Each UNinjaJutsu in Jutsus is cast by its InputAction (bound on the owner's input component while a local player controls it,
 * through InputMappingContext) or by StartJutsu. The chain: an optional held opening pose, then each seal held on the visible
 * mesh's UpperBody slot (the seal layer, NinjaSealWeight), then an optional full-body finisher on DefaultSlot during which movement
 * and jumping are locked, then the release (Shadow Clone / Fireball / a planted-hand effect / a held finisher effect), sounds and
 * the Blueprint events. Leaving the ground cancels the chain and an unreleased finisher.
 *
 * Shadow clones are copies of the owner's class with an AI controller; each copies its leader's movement input, gait, jumps and
 * crouch every tick, and the leader's casts, and faces the leader's lock-on target. Local only, as the seals always were (no
 * replication yet: online, the other player does not see the seals, and a clone cast on the listen host reaches the client as
 * a plain character).
 */
UCLASS(ClassGroup=(Ninja), meta=(BlueprintSpawnableComponent))
class DEMOGAME_1_API UNinjaJutsuComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UNinjaJutsuComponent();

	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	/** Plays the jutsu's seals in order, then releases it. Ignored in the air, mid-traversal or while already casting. */
	UFUNCTION(BlueprintCallable, Category="Ninja|Jutsu")
	void StartJutsu(UNinjaJutsu* Jutsu);

	/** Casts entry Index of Jutsus. */
	UFUNCTION(BlueprintCallable, Category="Ninja|Jutsu")
	void StartJutsuByIndex(int32 Index);

	/** Stops a seal chain early. */
	UFUNCTION(BlueprintCallable, Category="Ninja|Jutsu")
	void CancelJutsu();

	UFUNCTION(BlueprintPure, Category="Ninja|Jutsu")
	bool IsCastingJutsu() const { return bIsCastingJutsu; }

	/** True while a jutsu's full-body finisher plays (movement and jumping locked). */
	UFUNCTION(BlueprintPure, Category="Ninja|Jutsu")
	bool IsFinishing() const { return FinishingJutsu != nullptr; }

	UFUNCTION(BlueprintPure, Category="Ninja|Jutsu")
	UNinjaJutsu* GetCastingJutsu() const { return CastingJutsu; }

	UFUNCTION(BlueprintPure, Category="Ninja|Jutsu")
	UNinjaJutsu* GetFinishingJutsu() const { return FinishingJutsu; }

	/** True on a shadow clone spawned by another character's jutsu. */
	UFUNCTION(BlueprintPure, Category="Ninja|Clone")
	bool IsShadowClone() const { return bIsShadowClone; }

	/** On a clone: the character it copies. */
	UFUNCTION(BlueprintPure, Category="Ninja|Clone")
	ACharacter* GetCloneLeader() const;

	/** Spawns a clone beside the owner in a puff of smoke (the oldest is dispelled past MaxClones). */
	UFUNCTION(BlueprintCallable, Category="Ninja|Clone")
	void SpawnShadowClone();

	/** Removes every clone of the owner with a puff of smoke. */
	UFUNCTION(BlueprintCallable, Category="Ninja|Clone")
	void DispelClones();

	/** On a clone: vanish in a puff of smoke. */
	UFUNCTION(BlueprintCallable, Category="Ninja|Clone")
	void DispelClone();

	/** The mesh the seals and finishers play on (see NinjaVisual::FindVisualMesh). */
	UFUNCTION(BlueprintPure, Category="Ninja|Jutsu")
	USkeletalMeshComponent* GetVisualMesh() const;

	/** The actor whose side Actor fights on: a shadow clone's leader, else Actor itself (fireballs never burn their own side). */
	static const AActor* GetSideLeader(const AActor* Actor);

	/** Fires as each seal of the chain starts. */
	UPROPERTY(BlueprintAssignable, Category="Ninja|Jutsu")
	FNinjaJutsuSealSignature OnJutsuSeal;

	/** Fires after the release (clone, fireball, planted effect). */
	UPROPERTY(BlueprintAssignable, Category="Ninja|Jutsu")
	FNinjaJutsuSignature OnJutsuCompleted;

	/** Fires when a chain or an unreleased finisher is interrupted; SealIndex is INDEX_NONE during an opening pose or finisher. */
	UPROPERTY(BlueprintAssignable, Category="Ninja|Jutsu")
	FNinjaJutsuSealSignature OnJutsuCancelled;

	/** Fires at the release of a jutsu whose finisher plants a hand (FinisherHandBone), before OnJutsuCompleted. */
	UPROPERTY(BlueprintAssignable, Category="Ninja|Jutsu")
	FNinjaJutsuHandPlantedSignature OnJutsuHandPlanted;

	/** Fires on the leader after a clone has been spawned. */
	UPROPERTY(BlueprintAssignable, Category="Ninja|Clone")
	FNinjaCloneSignature OnCloneSpawned;

	/** The jutsu this character knows; each entry's InputAction casts it. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Jutsu")
	TArray<TObjectPtr<UNinjaJutsu>> Jutsus;

	/** Added for the local player (holds the jutsu keys; the Tab lock-on shares it). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Jutsu|Input")
	TObjectPtr<UInputMappingContext> InputMappingContext;

	/** Above GASP's IMC_Sandbox (0) so the jutsu buttons win where they share a gamepad button with its demo actions. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Jutsu|Input")
	int32 InputMappingPriority = 1;

	/**
	 * Keys swallowed while a finisher plays (GASP's jump and traversal, IA_Jump in IMC_Sandbox). A runtime mapping context maps
	 * them to a do-nothing action above every other context, so the press never reaches GASP's jump handler, never becomes a
	 * saved move and never starts a vault or mantle; that also holds for an online client, where lowering JumpMaxCount on its
	 * own copy would not stop the server's.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Jutsu|Input")
	TArray<FKey> FinisherBlockedKeys = { EKeys::SpaceBar, EKeys::Gamepad_FaceButton_Bottom };

	/** Priority of the finisher's key-swallowing context: above IMC_Sandbox (0) and InputMappingContext. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Jutsu|Input")
	int32 FinisherBlockPriority = 100;

	/** Seconds each seal is held before blending to the next. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Jutsu", meta=(ClampMin="0.05"))
	float SealHoldTime = 0.15f;

	/** Blend time between consecutive seals. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Jutsu", meta=(ClampMin="0.0"))
	float SealBlendTime = 0.05f;

	/** How long the last seal is held before the chain completes. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Jutsu", meta=(ClampMin="0.05"))
	float FinalSealHoldTime = 0.3f;

	/** Time to raise the arms into the first seal and to lower them after the chain. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Jutsu", meta=(ClampMin="0.01"))
	float SealLayerBlendTime = 0.15f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Jutsu|Audio")
	TObjectPtr<USoundBase> SealSound;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Jutsu|Audio", meta=(ClampMin="0.0"))
	float SealSoundVolume = 1.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Jutsu|Audio", meta=(ClampMin="0.0", ClampMax="0.5"))
	float SealSoundPitchVariation = 0.0f;

	/** Played on completion for jutsu without their own CompleteSound. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Jutsu|Audio")
	TObjectPtr<USoundBase> JutsuCompleteSound;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Jutsu|Audio", meta=(ClampMin="0.0"))
	float JutsuCompleteVolume = 1.0f;

	/** Clones alive at once; the oldest is dispelled when a new one would exceed this. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Clone", meta=(ClampMin="1"))
	int32 MaxClones = 1;

	/** Spawn offset from the owner, in the owner's facing space (cm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Clone")
	FVector CloneSpawnOffset = FVector(0.0f, 140.0f, 0.0f);

	/** Seconds after the smoke bursts before the clone becomes visible inside it. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Clone", meta=(ClampMin="0.0"))
	float CloneRevealDelay = 0.12f;

	/** Seconds a clone lasts before dispelling itself; 0 keeps it until replaced or dispelled. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Clone", meta=(ClampMin="0.0"))
	float CloneLifetime = 5.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Clone")
	TObjectPtr<UNiagaraSystem> CloneSmokeEffect;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Clone")
	FVector CloneSmokeScale = FVector(1.0f);

	/** Smoke position relative to the capsule centre (cm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Clone")
	FVector CloneSmokeOffset = FVector(0.0f, 0.0f, -45.0f);

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Clone")
	TObjectPtr<USoundBase> CloneDispelSound;

private:
	ACharacter* GetCharacter() const;
	double Now() const;
	/** Binds the jutsu actions and adds InputMappingContext once per input component (it is recreated on each possession). */
	void UpdateInputBinding();
	void OnJutsuInput(int32 JutsuIndex);
	int32 FindNextSeal(const UNinjaJutsu* Jutsu, int32 FromIndex) const;
	void PlaySeal(int32 Index);
	/** A held upper-body pose (seal or opening), stretched to last HoldTime plus the next blend. */
	UAnimMontage* PlayHeldPose(UAnimSequenceBase* Pose, float HoldTime);
	void UpdateJutsu(float DeltaSeconds);
	/** The last seal's hold ended: finish the clones' copies, then play the finisher or release right away. */
	void FinishSeals();
	void CompleteJutsu(UNinjaJutsu* Jutsu);
	void UpdateFinisher();
	void CancelFinisher();
	/** Movement and jumping locked while a finisher plays (the palm stays planted). */
	void SetFinisherLock(bool bLock);
	/** Adds or removes the FinisherBlockedKeys context on the local player that is signing (created on first use). */
	void SetFinisherKeysBlocked(AController* Controller, bool bBlocked);
	void SpawnFinisherEffect(const UNinjaJutsu& Jutsu);
	void StopFinisherEffect();
	void ReleaseFireball(const UNinjaJutsu& Jutsu);
	FVector FindGroundUnderHand(FName HandBone) const;
	void PlayJutsuSound(USoundBase* Sound, float Volume, float PitchVariation) const;
	/** Fades out the jutsu's StartVoice if it is still talking. */
	void StopJutsuVoice(float FadeOutTime);
	/** True when the character may start signing: on the ground, not mid-traversal (a GASP montage on its own mesh). */
	bool CanStartJutsu() const;
	/** On a clone: copy the leader's input, dispel when it expires or loses its leader, reveal after the smoke. */
	void UpdateClone();
	void SpawnCloneSmoke(ACharacter* Target, bool bAttach) const;
	void PruneClones();

	/** Runs Fn on every live clone's jutsu component (the leader drives its clones' casts). */
	void ForEachClone(TFunctionRef<void(UNinjaJutsuComponent&)> Fn);

	TWeakObjectPtr<UInputComponent> BoundInputComponent;

	bool bIsCastingJutsu = false;
	UPROPERTY(Transient)
	TObjectPtr<UNinjaJutsu> CastingJutsu;
	UPROPERTY(Transient)
	TObjectPtr<UNinjaJutsu> FinishingJutsu;
	int32 SealIndex = INDEX_NONE;
	double NextSealTime = 0.0;
	double FinisherReleaseAt = 0.0;
	double FinisherEndAt = 0.0;
	bool bFinisherReleased = false;
	TWeakObjectPtr<AActor> FinisherEffect;
	/** The casting jutsu's StartVoice (auto-destroys when it finishes). */
	TWeakObjectPtr<UAudioComponent> JutsuVoice;
	float SealLayerWeight = 0.0f;

	bool bFinisherLock = false;
	int32 SavedJumpMaxCount = 1;
	TWeakObjectPtr<AController> LockedController;
	UPROPERTY(Transient)
	TObjectPtr<UInputMappingContext> FinisherBlockContext;
	UPROPERTY(Transient)
	TObjectPtr<UInputAction> FinisherBlockAction;
	TWeakObjectPtr<UEnhancedInputLocalPlayerSubsystem> FinisherBlockSubsystem;

	bool bIsShadowClone = false;
	TWeakObjectPtr<ACharacter> CloneLeader;
	/** The leader's JumpCurrentCount last tick: a rise is a jump its movement accepted, which the clone copies. */
	int32 LastLeaderJumpCount = 0;
	TArray<TWeakObjectPtr<ACharacter>> Clones;
	double CloneRevealTime = 0.0;
	double CloneExpireTime = 0.0;
};
