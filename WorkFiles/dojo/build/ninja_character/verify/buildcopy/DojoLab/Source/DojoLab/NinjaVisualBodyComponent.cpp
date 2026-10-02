// Copyright Epic Games, Inc. All Rights Reserved.

#include "NinjaVisualBodyComponent.h"

#include "Animation/AnimInstance.h"
#include "Components/ChildActorComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/Actor.h"
#include "HAL/IConsoleManager.h"

DEFINE_LOG_CATEGORY_STATIC(LogNinjaVisualBody, Log, All);

/** The A/B switch: judged by looking, so it flips live on every ninja without a rebuild. */
static TAutoConsoleVariable<int32> CVarNinjaVisualMetaHuman(
	TEXT("ninja.visual.metahuman"), -1,
	TEXT("Visible ninja body: -1 = the Blueprint's bUseMetaHuman (default on), 0 = BP_NinjaVisual's Manny, 1 = the MetaHuman."),
	ECVF_Default);

UNinjaVisualBodyComponent::UNinjaVisualBodyComponent()
{
	// Ticks only to notice the console variable changing (and a child actor that did not exist yet at BeginPlay).
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.TickGroup = TG_PrePhysics;
}

bool UNinjaVisualBodyComponent::WantsMetaHuman() const
{
	const int32 Override = CVarNinjaVisualMetaHuman.GetValueOnGameThread();
	return Override < 0 ? bUseMetaHuman : Override > 0;
}

USkeletalMeshComponent* UNinjaVisualBodyComponent::GetHostMesh() const
{
	const AActor* Owner = GetOwner();
	if (!Owner)
	{
		return nullptr;
	}
	TInlineComponentArray<USkeletalMeshComponent*> Meshes(Owner);
	for (USkeletalMeshComponent* Mesh : Meshes)
	{
		if (Mesh && Mesh->GetFName() == HostMeshName)
		{
			return Mesh;
		}
	}
	// Same fallback as NinjaVisual::FindVisualMesh: the first skeletal mesh on the visual actor.
	return Owner->FindComponentByClass<USkeletalMeshComponent>();
}

AActor* UNinjaVisualBodyComponent::GetMetaHumanActor() const
{
	const AActor* Owner = GetOwner();
	if (!Owner)
	{
		return nullptr;
	}
	TInlineComponentArray<UChildActorComponent*> ChildActors(Owner);
	for (const UChildActorComponent* ChildActor : ChildActors)
	{
		if (ChildActor && ChildActor->ComponentHasTag(MetaHumanComponentTag))
		{
			return ChildActor->GetChildActor();
		}
	}
	return nullptr;
}

USkeletalMeshComponent* UNinjaVisualBodyComponent::GetMetaHumanBody() const
{
	const AActor* MetaHuman = GetMetaHumanActor();
	if (!MetaHuman)
	{
		return nullptr;
	}
	TInlineComponentArray<USkeletalMeshComponent*> Meshes(MetaHuman);
	for (USkeletalMeshComponent* Mesh : Meshes)
	{
		if (Mesh && Mesh->GetFName() == BodyComponentName)
		{
			return Mesh;
		}
	}
	return nullptr;
}

void UNinjaVisualBodyComponent::GetMetaHumanGarments(TArray<USkeletalMeshComponent*>& OutGarments) const
{
	OutGarments.Reset();
	const AActor* Owner = GetOwner();
	if (!Owner || MetaHumanGarmentTag.IsNone())
	{
		return;
	}
	TInlineComponentArray<USkeletalMeshComponent*> Meshes(Owner);
	for (USkeletalMeshComponent* Mesh : Meshes)
	{
		if (Mesh && Mesh->ComponentHasTag(MetaHumanGarmentTag))
		{
			OutGarments.Add(Mesh);
		}
	}
}

void UNinjaVisualBodyComponent::ApplyGarments(USkeletalMeshComponent* Body)
{
	TArray<USkeletalMeshComponent*> Garments;
	GetMetaHumanGarments(Garments);
	const bool bWear = bMetaHumanActive && Body;
	for (USkeletalMeshComponent* Garment : Garments)
	{
		if (bWear)
		{
			// The Blueprint parks the garment under Manny (the MetaHuman's Body only exists inside the child actor at runtime).
			if (Garment->GetAttachParent() != Body)
			{
				Garment->AttachToComponent(Body, FAttachmentTransformRules::SnapToTargetIncludingScale);
			}
			if (bGarmentsUseLeaderPose)
			{
				if (Garment->LeaderPoseComponent.Get() != Body)
				{
					Garment->SetLeaderPoseComponent(Body, /*bForceUpdate*/ true);
				}
			}
			// Evaluate (and simulate the cloth) after the body has its pose for this frame, or the cloth reads last frame's bones.
			Garment->AddTickPrerequisiteComponent(Body);
			Garment->SetComponentTickEnabled(true);
			Garment->SetVisibility(true, /*bPropagateToChildren*/ false);
			Garment->SetHiddenInGame(bSuppressed, /*bPropagateToChildren*/ false);
			// It has just jumped from where the Blueprint parked it (and from the reference pose): start the cloth from here.
			Garment->ForceClothNextUpdateTeleportAndReset();
		}
		else
		{
			Garment->SetVisibility(false, /*bPropagateToChildren*/ false);
			Garment->SetComponentTickEnabled(false);
		}
	}
}

void UNinjaVisualBodyComponent::BeginPlay()
{
	Super::BeginPlay();
	bApplied = ApplyMode(WantsMetaHuman());
}

void UNinjaVisualBodyComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	const bool bWant = WantsMetaHuman();
	const bool bStaleActor = bMetaHumanActive && AppliedMetaHuman.Get() != GetMetaHumanActor();
	if (!bApplied || bWant != bMetaHumanActive || bStaleActor)
	{
		bApplied = ApplyMode(bWant);
	}
}

void UNinjaVisualBodyComponent::ApplyMetaHumanActorVisibility(AActor* MetaHuman) const
{
	if (MetaHuman)
	{
		MetaHuman->SetActorHiddenInGame(!bMetaHumanActive || bSuppressed);
	}
}

bool UNinjaVisualBodyComponent::ApplyMode(bool bMetaHuman)
{
	USkeletalMeshComponent* Host = GetHostMesh();
	AActor* MetaHuman = GetMetaHumanActor();
	USkeletalMeshComponent* Body = GetMetaHumanBody();
	if (!Host)
	{
		return false;
	}
	if (bMetaHuman && (!MetaHuman || !Body || !BodyAnimClass))
	{
		// Nothing to show yet (or not set up): keep Manny visible and try again next tick.
		bMetaHumanActive = false;
		Host->SetVisibility(true, /*bPropagateToChildren*/ false);
		ApplyMetaHumanActorVisibility(MetaHuman);
		ApplyGarments(nullptr);
		return false;
	}

	bMetaHumanActive = bMetaHuman;
	// bVisible, not bHiddenInGame: the shadow clone's reveal toggles bHiddenInGame (SetVisualSuppressed) and must not show Manny.
	// Not propagated: the hidden Cloak and the MetaHuman child actor are Manny's children and keep their own visibility.
	Host->SetVisibility(!bMetaHuman, /*bPropagateToChildren*/ false);
	// The host must keep animating and refreshing its bones while invisible (ABP_NinjaVisual already ships with this), and at full
	// detail: a hidden mesh gets no screen-size LOD, and the retarget reads its fingers.
	Host->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
	Host->SetForcedLOD(bMetaHuman ? 1 : 0);

	if (MetaHuman)
	{
		if (bMetaHuman)
		{
			for (const TWeakObjectPtr<UActorComponent>& Component : DisabledTicks)
			{
				if (UActorComponent* Resolved = Component.Get())
				{
					Resolved->SetComponentTickEnabled(true);
				}
			}
			DisabledTicks.Reset();
			if (Body->GetAnimClass() != BodyAnimClass.Get())
			{
				Body->SetAnimInstanceClass(BodyAnimClass);
			}
			// The retarget reads the host's pose: evaluate after it (the attach chain passes through two non-ticking components).
			Body->AddTickPrerequisiteComponent(Host);
			// Pure decoration: the capsule and the hidden GASP mesh carry the collision; the grooms ship with PhysicsActor.
			TInlineComponentArray<UPrimitiveComponent*> Primitives(MetaHuman);
			for (UPrimitiveComponent* Primitive : Primitives)
			{
				Primitive->SetCollisionEnabled(ECollisionEnabled::NoCollision);
				Primitive->SetGenerateOverlapEvents(false);
			}
			AppliedMetaHuman = MetaHuman;
		}
		else
		{
			// Manny mode: the MetaHuman costs nothing (hidden, and its components stop ticking) so on/off timings compare cleanly.
			TInlineComponentArray<UActorComponent*> Components(MetaHuman);
			for (UActorComponent* Component : Components)
			{
				if (Component && Component->IsComponentTickEnabled())
				{
					Component->SetComponentTickEnabled(false);
					DisabledTicks.Add(Component);
				}
			}
		}
		ApplyMetaHumanActorVisibility(MetaHuman);
	}
	ApplyGarments(bMetaHuman ? Body : nullptr);
	UE_LOG(LogNinjaVisualBody, Log, TEXT("%s: visible body = %s"), *GetNameSafe(GetOwner()), bMetaHuman ? TEXT("MetaHuman") : TEXT("Manny"));
	return true;
}

void UNinjaVisualBodyComponent::SetVisualSuppressed(bool bInSuppressed)
{
	bSuppressed = bInSuppressed;
	if (USkeletalMeshComponent* Host = GetHostMesh())
	{
		Host->SetHiddenInGame(bSuppressed, /*bPropagateToChildren*/ false);
	}
	ApplyMetaHumanActorVisibility(GetMetaHumanActor());
	if (bMetaHumanActive)
	{
		// The garments belong to this actor but hang on the MetaHuman's Body, so hiding the MetaHuman actor does not hide them.
		TArray<USkeletalMeshComponent*> Garments;
		GetMetaHumanGarments(Garments);
		for (USkeletalMeshComponent* Garment : Garments)
		{
			Garment->SetHiddenInGame(bSuppressed, /*bPropagateToChildren*/ false);
		}
	}
}
