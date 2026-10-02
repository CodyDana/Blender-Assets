using UnrealBuildTool;

public class DojoLandscapeTools : ModuleRules
{
	public DojoLandscapeTools(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine" });
		PrivateDependencyModuleNames.AddRange(new string[] { "Landscape", "UnrealEd", "RenderCore" });
	}
}
