// ArmoryLab (Blender_Projects/Scripts/armory/unreal/cpp, copied into the project by make_project.py).

using UnrealBuildTool;
using System.Collections.Generic;

public class ArmoryLabTarget : TargetRules
{
	public ArmoryLabTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.V7;
		IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_8;
		ExtraModuleNames.Add("ArmoryLab");
	}
}
