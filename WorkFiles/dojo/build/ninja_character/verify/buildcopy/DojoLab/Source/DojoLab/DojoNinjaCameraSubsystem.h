// DojoLab (2026-10-02, ninja character port): per-pawn camera switch. New file, not from DemoGame_1.
//
// GASP's SandboxCharacter_CMC and its copy BP_NinjaGasp pick their camera in SetupCamera (on EventPossessed) from the
// project-wide cvar DDCVar.NewGameplayCameraSystem.Enable: 1 = GASP's Gameplay Camera rig (over the shoulder),
// 0 = the Blueprint's own SpringArm + Camera. DemoGame_1 sets 0 in its DefaultEngine.ini; DojoLab keeps GASP's 1 for
// the reference pawn, so instead this world subsystem sets the cvar for each pawn the game SPAWNS, before it is
// possessed: 0 for a ninja (a pawn with UNinjaJutsuComponent: BP_NinjaGasp, its shadow clones), and the value the cvar
// had before the first change for GASP's own pawns (/Game/Blueprints/SandboxCharacter_*). Other pawns are left alone.
// dojo.ninja.camera_switch 0 turns the switch off (the cvar is then only what the ini / console say).

#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "DojoNinjaCameraSubsystem.generated.h"

UCLASS()
class DOJOLAB_API UDojoNinjaCameraSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

protected:
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;

private:
	void HandleActorSpawned(AActor* Actor);

	FDelegateHandle SpawnHandle;
};
