// DojoLab (2026-10-02, ninja character port): per-pawn camera switch. See the header.

#include "DojoNinjaCameraSubsystem.h"

#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "HAL/IConsoleManager.h"
#include "NinjaJutsuComponent.h"

DEFINE_LOG_CATEGORY_STATIC(LogDojoNinja, Log, All);

namespace DojoNinjaCamera
{
	static int32 GSwitch = 1;
	static FAutoConsoleVariableRef CVarSwitch(TEXT("dojo.ninja.camera_switch"), GSwitch,
		TEXT("1 (default): set DDCVar.NewGameplayCameraSystem.Enable per spawned pawn (0 for a ninja, the original value ")
		TEXT("for GASP's SandboxCharacter pawns). 0: leave the cvar alone."));

	static const TCHAR* CameraCVarName = TEXT("DDCVar.NewGameplayCameraSystem.Enable");
	static bool bHaveOriginal = false;
	static bool bOriginal = true;

	static void SetCamera(bool bGameplayCameraSystem, const AActor* ForActor)
	{
		IConsoleVariable* CVar = IConsoleManager::Get().FindConsoleVariable(CameraCVarName);
		if (!CVar)
		{
			UE_LOG(LogDojoNinja, Warning, TEXT("camera switch: %s is not registered"), CameraCVarName);
			return;
		}
		if (!bHaveOriginal)
		{
			bOriginal = CVar->GetBool();
			bHaveOriginal = true;
		}
		const bool bWas = CVar->GetBool();
		if (bWas != bGameplayCameraSystem)
		{
			CVar->Set(bGameplayCameraSystem ? 1 : 0, ECVF_SetByCode);
		}
		UE_LOG(LogDojoNinja, Log, TEXT("camera switch: %s %d -> %d for %s"), CameraCVarName, bWas ? 1 : 0,
			CVar->GetBool() ? 1 : 0, *GetNameSafe(ForActor ? ForActor->GetClass() : nullptr));
	}
}

bool UDojoNinjaCameraSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

void UDojoNinjaCameraSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	if (UWorld* World = GetWorld())
	{
		SpawnHandle = World->AddOnActorSpawnedHandler(
			FOnActorSpawned::FDelegate::CreateUObject(this, &UDojoNinjaCameraSubsystem::HandleActorSpawned));
	}
}

void UDojoNinjaCameraSubsystem::Deinitialize()
{
	if (UWorld* World = GetWorld())
	{
		World->RemoveOnActorSpawnedHandler(SpawnHandle);
	}
	SpawnHandle.Reset();
	Super::Deinitialize();
}

void UDojoNinjaCameraSubsystem::HandleActorSpawned(AActor* Actor)
{
	if (DojoNinjaCamera::GSwitch == 0)
	{
		return;
	}
	const APawn* Pawn = Cast<APawn>(Actor);
	if (!Pawn)
	{
		return;
	}
	if (Pawn->FindComponentByClass<UNinjaJutsuComponent>())
	{
		DojoNinjaCamera::SetCamera(false, Pawn);
	}
	else if (Pawn->GetClass()->GetPathName().StartsWith(TEXT("/Game/Blueprints/SandboxCharacter_")))
	{
		if (DojoNinjaCamera::bHaveOriginal)
		{
			DojoNinjaCamera::SetCamera(DojoNinjaCamera::bOriginal, Pawn);
		}
	}
}
