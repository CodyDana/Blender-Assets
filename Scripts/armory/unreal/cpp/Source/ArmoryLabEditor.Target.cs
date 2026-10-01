// ArmoryLab (Blender_Projects/Scripts/armory/unreal/cpp, copied into the project by make_project.py).

using UnrealBuildTool;
using System.Collections.Generic;

public class ArmoryLabEditorTarget : TargetRules
{
	public ArmoryLabEditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.V7;
		IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_8;
		ExtraModuleNames.Add("ArmoryLab");
	}
}
