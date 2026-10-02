// Copyright Epic Games, Inc. All Rights Reserved.

#include "NinjaFireball.h"

#include "Components/PointLightComponent.h"
#include "Components/SphereComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/ProjectileMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "NiagaraComponent.h"
#include "NiagaraFunctionLibrary.h"
#include "NinjaJutsuComponent.h"

ANinjaFireball::ANinjaFireball()
{
	PrimaryActorTick.bCanEverTick = true;

	Collision = CreateDefaultSubobject<USphereComponent>(TEXT("Collision"));
	Collision->InitSphereRadius(Radius);
	Collision->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
	Collision->SetCollisionObjectType(ECC_WorldDynamic);
	Collision->SetCollisionResponseToAllChannels(ECR_Ignore);
	// Ignore-all baseline so the camera and visibility traces never hit a fireball; then block the solid object types.
	Collision->SetCollisionResponseToChannel(ECC_WorldStatic, ECR_Block);
	Collision->SetCollisionResponseToChannel(ECC_WorldDynamic, ECR_Block);
	Collision->SetCollisionResponseToChannel(ECC_PhysicsBody, ECR_Block);
	Collision->SetCollisionResponseToChannel(ECC_Destructible, ECR_Block);
	Collision->SetCollisionResponseToChannel(ECC_Vehicle, ECR_Block);
	// Characters are overlaps rather than blocks so the caster's side can be skipped without stopping the projectile.
	Collision->SetCollisionResponseToChannel(ECC_Pawn, ECR_Overlap);
	Collision->SetGenerateOverlapEvents(true);
	Collision->CanCharacterStepUpOn = ECB_No;
	RootComponent = Collision;

	FlameEffect = CreateDefaultSubobject<UNiagaraComponent>(TEXT("FlameEffect"));
	FlameEffect->SetupAttachment(Collision);

	Glow = CreateDefaultSubobject<UPointLightComponent>(TEXT("Glow"));
	Glow->SetupAttachment(Collision);
	Glow->SetLightColor(FLinearColor(1.0f, 0.45f, 0.12f));
	Glow->SetIntensity(GlowIntensity);
	Glow->SetAttenuationRadius(600.0f);
	Glow->SetCastShadows(false);

	Movement = CreateDefaultSubobject<UProjectileMovementComponent>(TEXT("Movement"));
	Movement->UpdatedComponent = Collision;
	Movement->InitialSpeed = 1000.0f;
	Movement->MaxSpeed = 1000.0f;
	Movement->ProjectileGravityScale = 0.0f;
	Movement->bRotationFollowsVelocity = true;
	Movement->bShouldBounce = false;
}

void ANinjaFireball::BeginPlay()
{
	Super::BeginPlay();

	SpawnTime = GetWorld()->GetTimeSeconds();

	if (APawn* Caster = GetInstigator())
	{
		Collision->IgnoreActorWhenMoving(Caster, true);
	}
	// Same-side fireballs (a leader's and its clones', or one still in flight) fly through each other both ways:
	// a blocking hit between them would stop both projectiles mid-air.
	for (TActorIterator<ANinjaFireball> It(GetWorld()); It; ++It)
	{
		ANinjaFireball* Other = *It;
		if (Other != this && !Other->bBurst && IsFriendly(Other->GetInstigator()))
		{
			Collision->IgnoreActorWhenMoving(Other, true);
			Other->Collision->IgnoreActorWhenMoving(this, true);
		}
	}

	Collision->OnComponentBeginOverlap.AddDynamic(this, &ANinjaFireball::OnCollisionOverlap);
	Movement->OnProjectileStop.AddDynamic(this, &ANinjaFireball::OnProjectileStop);
	ApplySize(GrowTime > 0.0f ? StartSize : 1.0f);
	if (bBurst)
	{
		return;
	}

	// Overlaps that began when the component registered (before the handler was bound) never fire the event:
	// an enemy already inside the sphere at spawn must still burst it.
	TArray<AActor*> Touching;
	Collision->GetOverlappingActors(Touching, APawn::StaticClass());
	for (AActor* Actor : Touching)
	{
		if (!IsFriendly(Actor))
		{
			BurstOn(Actor);
			return;
		}
	}

	if (LaunchSound)
	{
		UGameplayStatics::SpawnSoundAttached(LaunchSound, Collision, NAME_None, FVector::ZeroVector, EAttachLocation::KeepRelativeOffset, true, LaunchVolume);
	}
}

void ANinjaFireball::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	const double Age = GetWorld()->GetTimeSeconds() - SpawnTime;
	if (Age >= Lifetime)
	{
		Burst();
		return;
	}

	if (CurrentSize < 1.0f)
	{
		const float Alpha = GrowTime > 0.0f ? FMath::Clamp(static_cast<float>(Age) / GrowTime, 0.0f, 1.0f) : 1.0f;
		ApplySize(FMath::InterpEaseOut(StartSize, 1.0f, Alpha, 2.0f));
	}
}

void ANinjaFireball::ApplySize(float Size)
{
	CurrentSize = Size;
	Collision->SetSphereRadius(Radius * Size);
	Glow->SetIntensity(GlowIntensity * Size);
	if (!FlameScaleParameter.IsNone())
	{
		FlameEffect->SetVariableFloat(FlameScaleParameter, FlameScale * Size);
	}
}

void ANinjaFireball::Burst()
{
	BurstOn(nullptr);
}

void ANinjaFireball::OnCollisionOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp, int32 OtherBodyIndex,
	bool bFromSweep, const FHitResult& SweepResult)
{
	// Walls come through OnProjectileStop; overlaps only count for characters (not trigger volumes or other queries).
	if (Cast<APawn>(OtherActor) && !IsFriendly(OtherActor))
	{
		BurstOn(OtherActor);
	}
}

void ANinjaFireball::OnProjectileStop(const FHitResult& ImpactResult)
{
	BurstOn(ImpactResult.GetActor());
}

bool ANinjaFireball::IsFriendly(const AActor* Actor) const
{
	const AActor* Caster = GetInstigator();
	if (!Caster || !Actor)
	{
		return Actor == Caster;
	}
	// Compare the sides' leaders: a shadow clone and its leader (and sibling clones) are on the same side.
	return UNinjaJutsuComponent::GetSideLeader(Caster) == UNinjaJutsuComponent::GetSideLeader(Actor);
}

void ANinjaFireball::BurstOn(AActor* HitActor)
{
	if (bBurst)
	{
		return;
	}
	bBurst = true;

	OnBurst(HitActor);

	const FVector Location = GetActorLocation();
	if (ImpactEffect)
	{
		UNiagaraFunctionLibrary::SpawnSystemAtLocation(this, ImpactEffect, Location, GetActorRotation(), ImpactEffectScale * CurrentSize);
	}
	if (ImpactSound)
	{
		UGameplayStatics::PlaySoundAtLocation(this, ImpactSound, Location);
	}
	Destroy();
}
