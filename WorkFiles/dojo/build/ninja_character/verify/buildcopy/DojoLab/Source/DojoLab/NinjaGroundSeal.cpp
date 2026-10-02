// Copyright Epic Games, Inc. All Rights Reserved.

#include "NinjaGroundSeal.h"

#include "Components/DecalComponent.h"
#include "Engine/World.h"
#include "Materials/MaterialInstanceDynamic.h"

ANinjaGroundSeal::ANinjaGroundSeal()
{
	PrimaryActorTick.bCanEverTick = true;

	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	RootComponent = Root;

	Decal = CreateDefaultSubobject<UDecalComponent>(TEXT("Decal"));
	Decal->SetupAttachment(Root);
	// Decals project along their X axis: pitch it to point down. 8 x 8 m seal, only 20 cm deep so it does not streak up
	// nearby walls or props.
	Decal->SetRelativeRotation(FRotator(-90.0f, 0.0f, 0.0f));
	Decal->DecalSize = FVector(20.0f, 400.0f, 400.0f);
}

void ANinjaGroundSeal::BeginPlay()
{
	Super::BeginPlay();

	StartTime = GetWorld()->GetTimeSeconds();
	if (SealMaterial)
	{
		MaterialInstance = UMaterialInstanceDynamic::Create(SealMaterial, this);
		MaterialInstance->SetScalarParameterValue(RevealParameter, 0.0f);
		MaterialInstance->SetScalarParameterValue(FadeParameter, 1.0f);
		Decal->SetDecalMaterial(MaterialInstance);
	}
}

void ANinjaGroundSeal::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	const float Age = static_cast<float>(GetWorld()->GetTimeSeconds() - StartTime);
	const float RevealAlpha = FMath::Clamp((Age - RevealDelay) / RevealDuration, 0.0f, 1.0f);
	// Ease-out cubic, like the Blender reveal: the front bursts out of the palm and slows as it reaches the rim.
	const float Reveal = RevealEnd * (1.0f - FMath::Pow(1.0f - RevealAlpha, 3.0f));

	const float FadeStart = RevealDelay + RevealDuration + HoldTime;
	const float Fade = 1.0f - FMath::Clamp((Age - FadeStart) / FadeOutTime, 0.0f, 1.0f);

	if (MaterialInstance)
	{
		MaterialInstance->SetScalarParameterValue(RevealParameter, Reveal);
		MaterialInstance->SetScalarParameterValue(FadeParameter, Fade);
	}
	if (Age >= FadeStart + FadeOutTime)
	{
		Destroy();
	}
}
