// DojoLab game target (2026-10-02, ninja character port). Same settings as DemoGame_1.Target.cs.

using UnrealBuildTool;
using System.Collections.Generic;

public class DojoLabTarget : TargetRules
{
	public DojoLabTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.V7;
		IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_8;
		ExtraModuleNames.Add("DojoLab");
	}
}
