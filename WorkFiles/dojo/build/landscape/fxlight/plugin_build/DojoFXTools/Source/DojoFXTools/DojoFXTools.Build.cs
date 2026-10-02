using UnrealBuildTool;

public class DojoFXTools : ModuleRules
{
	public DojoFXTools(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine" });
		PrivateDependencyModuleNames.AddRange(new string[] { "Niagara", "UnrealEd" });
	}
}
