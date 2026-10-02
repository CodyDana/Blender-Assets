// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "NinjaVisualBodyComponent.generated.h"

class AActor;
class UActorComponent;
class UAnimInstance;
class UChildActorComponent;
class USkeletalMeshComponent;

/**
 * Chooses what the ninja's VISIBLE body is (2026-09-26, Cody: "let's test with the male"): BP_NinjaVisual's own Manny, or a
 * MetaHuman. Lives on BP_NinjaVisual.
 *
 * Manny stays the animation HOST either way: it keeps running ABP_NinjaVisual (the GASP retarget + our DefaultSlot / UpperBody
 * montages), and every gameplay system keeps finding it through NinjaVisual::FindVisualMesh. In MetaHuman mode Manny is made
 * invisible (bVisible off; it still ticks its pose and refreshes its bones, and is forced to LOD 0 so the retarget always reads
 * the full skeleton) and the MetaHuman child actor (the ChildActorComponent tagged MetaHumanComponentTag, attached to Manny) is
 * shown, its body running BodyAnimClass (ABP_MH_NinjaBody: Retarget Pose From Mesh, which finds Manny by walking up the attach
 * chain). The MetaHuman's face and grooms follow its body the way the MetaHuman Blueprint sets them up.
 *
 * `ninja.visual.metahuman -1|0|1` overrides bUseMetaHuman live on every ninja (-1 = follow the Blueprint, 0 = Manny, 1 = MetaHuman).
 *
 * Garments fitted to the MetaHuman (2026-09-26: the BlackCloak re-fit, BP_NinjaVisual's `CloakMH`) are skeletal mesh components of
 * the visual actor tagged MetaHumanGarmentTag. They cannot be parented to the MetaHuman's Body in the Blueprint (it lives inside the
 * child actor), so in MetaHuman mode this attaches them to the Body at runtime, makes them follow it (Leader Pose, or their own anim
 * Blueprint) and shows them; in Manny mode they are hidden and stop ticking (no cloth simulation), like the rest of the MetaHuman.
 */
UCLASS(ClassGroup = (Ninja), meta = (BlueprintSpawnableComponent))
class DEMOGAME_1_API UNinjaVisualBodyComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UNinjaVisualBodyComponent();

	/** Show the MetaHuman instead of Manny (the console variable ninja.visual.metahuman can override this live). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Ninja|Visual Body")
	bool bUseMetaHuman = true;

	/** The owner's skeletal mesh component that runs the animation (BP_NinjaVisual's Manny). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Ninja|Visual Body")
	FName HostMeshName = TEXT("Manny");

	/** Tag on the ChildActorComponent that spawns the MetaHuman Blueprint. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Ninja|Visual Body")
	FName MetaHumanComponentTag = TEXT("NinjaMetaHuman");

	/** Name of the MetaHuman Blueprint's body skeletal mesh component. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Ninja|Visual Body")
	FName BodyComponentName = TEXT("Body");

	/** Anim Blueprint put on the MetaHuman's body: retargets the host's pose every frame (ABP_MH_NinjaBody). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Ninja|Visual Body")
	TSubclassOf<UAnimInstance> BodyAnimClass;

	/** Tag on the visual actor's skeletal mesh components that are garments fitted to the MetaHuman body (BP_NinjaVisual's CloakMH). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Ninja|Visual Body")
	FName MetaHumanGarmentTag = TEXT("NinjaMHGarment");

	/**
	 * True: a garment follows the MetaHuman body as a Leader Pose follower (no anim evaluation of its own; Chaos Cloth still simulates,
	 * reading the leader's bones - Docs/Outfit_Pipeline.md trap 8). False: it keeps its own anim class, e.g. a Copy Pose From Mesh
	 * "use attached parent" graph, which then copies the Body it has been attached to.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Ninja|Visual Body")
	bool bGarmentsUseLeaderPose = true;

	/** The visual actor's garments fitted to the MetaHuman (components tagged MetaHumanGarmentTag). */
	UFUNCTION(BlueprintCallable, Category = "Ninja|Visual Body")
	void GetMetaHumanGarments(TArray<USkeletalMeshComponent*>& OutGarments) const;

	/** True while the MetaHuman is the visible body. */
	UFUNCTION(BlueprintPure, Category = "Ninja|Visual Body")
	bool IsMetaHumanActive() const { return bMetaHumanActive; }

	/**
	 * Hides whichever body is showing without changing the mode (the shadow clone's reveal delay: NinjaVisual::SetVisualHidden).
	 * Uses bHiddenInGame on Manny, which the mode never touches (the mode uses bVisible), so the two cannot undo each other.
	 */
	UFUNCTION(BlueprintCallable, Category = "Ninja|Visual Body")
	void SetVisualSuppressed(bool bInSuppressed);

	/** The MetaHuman's body mesh, or null when there is none. */
	UFUNCTION(BlueprintPure, Category = "Ninja|Visual Body")
	USkeletalMeshComponent* GetMetaHumanBody() const;

	/** The owner's animation host (Manny). */
	UFUNCTION(BlueprintPure, Category = "Ninja|Visual Body")
	USkeletalMeshComponent* GetHostMesh() const;

protected:
	virtual void BeginPlay() override;
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

private:
	bool WantsMetaHuman() const;
	AActor* GetMetaHumanActor() const;
	/** Applies the mode; returns false (nothing changed) when MetaHuman mode is wanted but the child actor does not exist yet. */
	bool ApplyMode(bool bMetaHuman);
	void ApplyMetaHumanActorVisibility(AActor* MetaHuman) const;
	/** Puts the MetaHuman garments on Body (MetaHuman mode) or hides and parks them (Manny mode, or Body null). */
	void ApplyGarments(USkeletalMeshComponent* Body);

	bool bApplied = false;
	bool bMetaHumanActive = false;
	bool bSuppressed = false;
	/** The child actor the body anim class was put on (a re-created child actor needs it again). */
	TWeakObjectPtr<AActor> AppliedMetaHuman;
	/** Components of the MetaHuman whose tick this component switched off in Manny mode, to switch back on. */
	TArray<TWeakObjectPtr<UActorComponent>> DisabledTicks;
};
