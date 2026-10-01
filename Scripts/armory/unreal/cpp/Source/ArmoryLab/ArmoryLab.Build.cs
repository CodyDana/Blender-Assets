// ArmoryLab game module (Blender_Projects/Scripts/armory/unreal/cpp, copied into the project by make_project.py).

using UnrealBuildTool;

public class ArmoryLab : ModuleRules
{
	public ArmoryLab(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", "InputCore", "EnhancedInput" });
		PrivateDependencyModuleNames.Add("ApplicationCore");   // IPlatformInputDeviceMapper (the self-test's key presses)
	}
}
