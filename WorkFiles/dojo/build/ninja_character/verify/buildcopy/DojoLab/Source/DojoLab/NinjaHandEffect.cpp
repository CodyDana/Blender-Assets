// Copyright Epic Games, Inc. All Rights Reserved.

#include "NinjaHandEffect.h"

#include "Components/AudioComponent.h"
#include "Components/PointLightComponent.h"
#include "Engine/World.h"
#include "NiagaraComponent.h"

ANinjaHandEffect::ANinjaHandEffect()
{
	PrimaryActorTick.bCanEverTick = true;

	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	RootComponent = Root;

	Effect = CreateDefaultSubobject<UNiagaraComponent>(TEXT("Effect"));
	Effect->SetupAttachment(Root);

	Glow = CreateDefaultSubobject<UPointLightComponent>(TEXT("Glow"));
	Glow->SetupAttachment(Root);
	Glow->SetLightColor(FLinearColor(0.45f, 0.7f, 1.0f));
	Glow->SetIntensity(0.0f);
	Glow->SetAttenuationRadius(450.0f);
	Glow->SetCastShadows(false);

	Sound = CreateDefaultSubobject<UAudioComponent>(TEXT("Sound"));
	Sound->SetupAttachment(Root);
	Sound->bAutoActivate = true;
}

void ANinjaHandEffect::BeginPlay()
{
	Super::BeginPlay();
	SpawnTime = GetWorld()->GetTimeSeconds();
}

void ANinjaHandEffect::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	const double Time = GetWorld()->GetTimeSeconds();
	if (Time >= NextFlickerTime)
	{
		FlickerScale = 1.0f - FMath::FRand() * FlickerAmount;
		NextFlickerTime = Time + (FlickerRate > 0.0f ? 1.0 / FlickerRate : 1.0e9);
	}

	float Fade = FadeInTime > 0.0f ? FMath::Clamp(static_cast<float>(Time - SpawnTime) / FadeInTime, 0.0f, 1.0f) : 1.0f;
	if (StopTime >= 0.0)
	{
		const float Out = FadeOutTime > 0.0f ? FMath::Clamp(static_cast<float>(Time - StopTime) / FadeOutTime, 0.0f, 1.0f) : 1.0f;
		Fade *= 1.0f - Out;
		if (Time - StopTime >= FMath::Max(FadeOutTime, LingerTime))
		{
			Destroy();
			return;
		}
	}
	Glow->SetIntensity(GlowIntensity * FlickerScale * Fade);
}

void ANinjaHandEffect::StopEffect()
{
	if (StopTime >= 0.0)
	{
		return;
	}
	StopTime = GetWorld()->GetTimeSeconds();
	Effect->Deactivate();
	if (Sound->IsPlaying())
	{
		Sound->FadeOut(FadeOutTime, 0.0f);
	}
	// Leave the dying arcs where the hand stopped instead of dragging them along as the ninja stands up.
	DetachFromActor(FDetachmentTransformRules::KeepWorldTransform);
}
