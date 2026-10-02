// DojoLab game module (2026-10-02): the DemoGame_1 ninja character port.
// The Ninja*.h/.cpp files are byte-identical copies of DemoGame_1/Source/DemoGame_1 (see
// Blender_Projects/WorkFiles/dojo/build/ninja_character/PORT_PROVENANCE.md). They declare their classes with
// DEMOGAME_1_API; the definition below maps that macro onto this module's export macro so no copied file is edited.
// The copied assets name the classes /Script/DemoGame_1.<Class>; Config/DefaultEngine.ini [CoreRedirects] maps that
// package onto /Script/DojoLab.

using UnrealBuildTool;

public class DojoLab : ModuleRules
{
	public DojoLab(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", "InputCore", "EnhancedInput", "Niagara" });

		// AIModule: shadow clones are driven by an AAIController (UNinjaJutsuComponent::SpawnShadowClone).
		PrivateDependencyModuleNames.Add("AIModule");

		// The copied sources export with DEMOGAME_1_API (DemoGame_1's module macro).
		PublicDefinitions.Add("DEMOGAME_1_API=DOJOLAB_API");

		// DemoGame_1's editor-only dependencies (Landscape, BlueprintGraph, UnrealEd, Clothing*, SkeletalMeshEditor,
		// ChaosCloth) served its editor tools (NinjaLandscapeTool / NinjaBlueprintTool / NinjaClothTool), which are not
		// part of the port.
	}
}
