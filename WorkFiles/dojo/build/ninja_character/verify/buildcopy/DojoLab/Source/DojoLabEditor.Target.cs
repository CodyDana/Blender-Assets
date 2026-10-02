// DojoLab editor target (2026-10-02, ninja character port). Same settings as DemoGame_1Editor.Target.cs.

using UnrealBuildTool;
using System.Collections.Generic;

public class DojoLabEditorTarget : TargetRules
{
	public DojoLabEditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.V7;
		IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_8;
		ExtraModuleNames.Add("DojoLab");
	}
}
