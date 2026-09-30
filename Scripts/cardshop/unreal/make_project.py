"""Create (or refresh) the CardShopKit Unreal 5.8 validation project (spec D8). Plain Python, no Unreal. Idempotent: a file
is rewritten only when its content differs, and nothing outside the CardShopKit project folder is written.

- CardShopKit.uproject: EngineAssociation 5.8, Blueprint-only, PythonScriptPlugin + EditorScriptingUtilities.
- Config/DefaultEngine.ini: Substrate OFF (the house validation setting, spec 4.5), the legacy FBX importer (house rule:
  UCX hulls are keyed to the node name, measured on UE 5.8.2), Lumen with hardware ray tracing (DX12 SM6), and the showcase room
  (L_CSK_Shop) as the editor start-up map.
- Config/DefaultGame.ini: the project name.

Run: py -3 Scripts/cardshop/unreal/make_project.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import csk_common as C  # noqa: E402

UPROJECT = {
    "FileVersion": 3,
    "EngineAssociation": "5.8",
    "Category": "",
    "Description": "Card Shop Kit validation project (G1 standards spike and later the full kit).",
    "Plugins": [
        {"Name": "PythonScriptPlugin", "Enabled": True},
        {"Name": "EditorScriptingUtilities", "Enabled": True},
    ],
}

MAP = C.SHOP_LEVEL + "." + C.SHOP_LEVEL.rsplit("/", 1)[1]      # the showcase room opens at start-up
ENGINE_INI = "\n".join([
    "; CardShopKit validation project, written by Scripts/cardshop/unreal/make_project.py",
    "[/Script/Engine.RendererSettings]",
    "r.Substrate=False",
    "r.AllowStaticLighting=False",
    "; Lumen GI + reflections, virtual shadow maps (the ArmoryLab set)",
    "r.GenerateMeshDistanceFields=True",
    "r.DynamicGlobalIlluminationMethod=1",
    "r.ReflectionMethod=1",
    "r.Shadow.Virtual.Enable=1",
    "r.DefaultFeature.AutoExposure.ExtendDefaultLuminanceRange=True",
    "; hardware ray tracing for Lumen (as ArmoryLab): software Lumen had no mesh cards in the short offscreen captures",
    "r.SkinCache.CompileShaders=True",
    "r.RayTracing=True",
    "r.RayTracing.RayTracingProxies.ProjectEnabled=True",
    "",
    "[/Script/WindowsTargetPlatform.WindowsTargetSettings]",
    "DefaultGraphicsRHI=DefaultGraphicsRHI_DX12",
    "-D3D12TargetedShaderFormats=PCD3D_SM5",
    "+D3D12TargetedShaderFormats=PCD3D_SM6",
    "",
    "[/Script/EngineSettings.GameMapsSettings]",
    f"EditorStartupMap={MAP}",
    f"GameDefaultMap={MAP}",
    "",
    "[ConsoleVariables]",
    "; legacy FBX importer (UCX hulls keyed to the node name; measured on UE 5.8.2)",
    "Interchange.FeatureFlags.Import.FBX=0",
    "",
])
GAME_INI = "\n".join(["[/Script/EngineSettings.GeneralProjectSettings]", "ProjectName=CardShopKit",
                      "Description=Card Shop Kit validation", ""])


def put(path, text, report):
    path.parent.mkdir(parents=True, exist_ok=True)
    old = path.read_text(encoding="utf-8") if path.exists() else None
    if old == text:
        report[str(path)] = "unchanged"
        return
    path.write_text(text, encoding="utf-8")
    report[str(path)] = "created" if old is None else "updated"


def main():
    assert C.PROJECT_DIR.name == "CardShopKit"
    rep = {"project": str(C.UPROJECT), "files": {}}
    put(C.UPROJECT, json.dumps(UPROJECT, indent="\t") + "\n", rep["files"])
    put(C.PROJECT_DIR / "Config" / "DefaultEngine.ini", ENGINE_INI, rep["files"])
    put(C.PROJECT_DIR / "Config" / "DefaultGame.ini", GAME_INI, rep["files"])
    (C.PROJECT_DIR / "Content").mkdir(parents=True, exist_ok=True)
    rep["passed"] = C.UPROJECT.exists()
    C.write_json(C.OUT / "make_project.json", rep)
    print(json.dumps(rep, indent=1))
    print(f"CSK_STEP_DONE project passed={rep['passed']}")


main()
