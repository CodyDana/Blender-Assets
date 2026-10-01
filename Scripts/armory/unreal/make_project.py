"""Create (or refresh) the ArmoryLab Unreal 5.8 project files. Plain Python, no Unreal. Idempotent: a file is only
rewritten when its content differs, and nothing outside the ArmoryLab folder is written.

- ArmoryLab.uproject: EngineAssociation 5.8, PythonScriptPlugin + EditorScriptingUtilities, and (2026-10-01) one C++ game
  module "ArmoryLab": the V first-person toggle (UArmoryViewToggleComponent). Its sources live in
  Scripts/armory/unreal/cpp/Source and are copied into ArmoryLab/Source here (the repo copy is the source of truth);
  run_armory_unreal.sh "build" compiles them with UnrealBuildTool, "firstperson" wires the component into the character.
- Config/DefaultEngine.ini: the RENDER settings of DemoGame_1 (read-only source, parsed, never written), plus the legacy FBX
  importer flag and the armory map as the game/editor default map.
- Config/DefaultGame.ini: project name.

Run: python make_project.py   -> prints a JSON summary and writes WorkFiles/armory/build/unreal/make_project.json
"""
import configparser
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ak_common as C  # noqa: E402

SOURCE_INI = Path(r"C:\Users\Cody\Documents\Unreal Projects\DemoGame_1\Config\DefaultEngine.ini")
# the render sections copied from DemoGame_1 (read-only source); everything else there is game-specific
RENDER_SECTIONS = ("/Script/Engine.RendererSettings", "/Script/WindowsTargetPlatform.WindowsTargetSettings",
                   "/Script/HardwareTargeting.HardwareTargetingSettings")
# WindowsTargetSettings carries audio keys in DemoGame_1: only the RHI / shader-format keys are render settings
WINDOWS_KEYS = ("DefaultGraphicsRHI", "-D3D12TargetedShaderFormats", "+D3D12TargetedShaderFormats",
                "-D3D11TargetedShaderFormats", "+D3D11TargetedShaderFormats")


def read_sections(path):
    """Unreal ini (duplicate keys with +/- prefixes allowed) -> {section: [(key, value), ...]} in file order."""
    out, cur = {}, None
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith(";"):
            continue
        if line.startswith("[") and line.endswith("]"):
            cur = line[1:-1]
            out.setdefault(cur, [])
            continue
        if cur is not None and "=" in line:
            k, v = line.split("=", 1)
            out[cur].append((k.strip(), v.strip()))
    return out


def engine_ini():
    src = read_sections(SOURCE_INI)
    lines = ["; ArmoryLab (lean armory build). Render settings copied from DemoGame_1/Config/DefaultEngine.ini by",
             "; Scripts/armory/unreal/make_project.py (DemoGame_1 is read-only; re-run the script to refresh).", ""]
    copied = {}
    for sec in RENDER_SECTIONS:
        items = src.get(sec, [])
        if sec.endswith("WindowsTargetSettings"):
            items = [(k, v) for k, v in items if k in WINDOWS_KEYS]
        copied[sec] = items
        lines.append(f"[{sec}]")
        lines += [f"{k}={v}" for k, v in items]
        lines.append("")
    m = C.LEVEL + "." + C.LEVEL.rsplit("/", 1)[1]
    lines += ["[/Script/EngineSettings.GameMapsSettings]", f"GameDefaultMap={m}", f"EditorStartupMap={m}",
              f"GlobalDefaultGameMode={GAME_MODE}", "",
              "[ConsoleVariables]",
              "; legacy FBX importer (UCX hulls keyed to the node name; measured on UE 5.8.2, see the export-pipeline notes)",
              "Interchange.FeatureFlags.Import.FBX=0", ""]
    return "\n".join(lines), copied


# Walk-in with Manny (user, 2026-09-27): the engine's own Third Person template content, copied from the engine install
# (never from DemoGame_1): its character / game mode / controller Blueprints and the shared Characters, Input and
# LevelPrototyping packs, mounted where the template mounts them.
ENGINE_TEMPLATES = Path(r"C:\Program Files\Epic Games\UE_5.8\Templates")
TEMPLATE_COPIES = [
    (ENGINE_TEMPLATES / "TP_ThirdPersonBP" / "Content" / "ThirdPerson" / "Blueprints", "ThirdPerson/Blueprints"),
    (ENGINE_TEMPLATES / "TemplateResources" / "High" / "Characters" / "Content", "Characters"),
    (ENGINE_TEMPLATES / "TemplateResources" / "High" / "Input" / "Content", "Input"),
    (ENGINE_TEMPLATES / "TemplateResources" / "High" / "LevelPrototyping" / "Content", "LevelPrototyping"),
]
# Items on display (user, 2026-09-27: "just have one tray displaying all of them neatly"): the pack's own IMPORTED assets
# (sockets recreated from the sidecars, pack materials), copied at file level from the pack validation project. The pack
# is the source of truth, so changed files are overwritten; nothing in ArmoryLab edits /Game/NinjaPack.
PACK_CONTENT = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealShuriken\Content\NinjaPack")


def sync_tree(src, dst, report):
    n_new = n_same = 0
    for f in src.rglob("*"):
        if not f.is_file():
            continue
        t = dst / f.relative_to(src)
        if t.exists() and t.stat().st_size == f.stat().st_size and t.read_bytes() == f.read_bytes():
            n_same += 1
            continue
        t.parent.mkdir(parents=True, exist_ok=True)
        t.write_bytes(f.read_bytes())
        n_new += 1
    report[str(dst)] = {"copied_or_updated": n_new, "unchanged": n_same}


TEMPLATE_INPUT_INI = ENGINE_TEMPLATES / "TP_ThirdPersonBP" / "Config" / "DefaultInput.ini"
GAME_MODE = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonGameMode.BP_ThirdPersonGameMode_C"


def copy_tree(src, dst, report):
    """Copy files that are MISSING only: never overwrites (ak_manny.py edits our copy of BP_ThirdPersonCharacter to use
    Manny, and a refresh must not revert it) and never deletes."""
    n_new = n_same = 0
    for f in src.rglob("*"):
        if not f.is_file():
            continue
        t = dst / f.relative_to(src)
        if t.exists():
            n_same += 1
            continue
        t.parent.mkdir(parents=True, exist_ok=True)
        t.write_bytes(f.read_bytes())
        n_new += 1
    report[str(dst)] = {"copied": n_new, "kept_existing": n_same}


UPROJECT = {
    "FileVersion": 3,
    "EngineAssociation": "5.8",
    "Category": "",
    "Description": "Armory gallery lab: the room and empty display cases (lean build).",
    "Modules": [
        {"Name": "ArmoryLab", "Type": "Runtime", "LoadingPhase": "Default"},   # the V first-person toggle
    ],
    "Plugins": [
        {"Name": "PythonScriptPlugin", "Enabled": True},
        {"Name": "EditorScriptingUtilities", "Enabled": True},
        {"Name": "GameplayStateTree", "Enabled": True},   # as the Third Person template's .uproject
    ],
}

GAME_INI = "\n".join(["[/Script/EngineSettings.GeneralProjectSettings]", "ProjectName=ArmoryLab",
                      "Description=Armory gallery lab (lean build)", ""])


CPP_SOURCE = Path(__file__).resolve().parent / "cpp" / "Source"


def sync_cpp(report):
    """Copy the game module's sources (Scripts/armory/unreal/cpp/Source) into ArmoryLab/Source. Only files that differ
    are rewritten (so UnrealBuildTool's up-to-date check holds); nothing else in Source is touched."""
    for f in sorted(CPP_SOURCE.rglob("*")):
        if f.is_file():
            put(C.PROJECT_DIR / "Source" / f.relative_to(CPP_SOURCE), f.read_text(encoding="utf-8"), report)


def put(path, text, report):
    path.parent.mkdir(parents=True, exist_ok=True)
    old = path.read_text(encoding="utf-8") if path.exists() else None
    if old == text:
        report[str(path)] = "unchanged"
        return
    path.write_text(text, encoding="utf-8")
    report[str(path)] = "created" if old is None else "updated"


def main():
    assert "ArmoryLab" in str(C.PROJECT_DIR) and "DemoGame" not in str(C.PROJECT_DIR)
    rep = {"project": str(C.UPROJECT), "files": {}}
    put(C.UPROJECT, json.dumps(UPROJECT, indent="\t") + "\n", rep["files"])
    text, copied = engine_ini()
    put(C.PROJECT_DIR / "Config" / "DefaultEngine.ini", text, rep["files"])
    put(C.PROJECT_DIR / "Config" / "DefaultGame.ini", GAME_INI, rep["files"])
    sync_cpp(rep["files"])
    (C.PROJECT_DIR / "Content").mkdir(parents=True, exist_ok=True)
    rep["template_content"] = {}
    for src, rel in TEMPLATE_COPIES:
        if src.exists():
            copy_tree(src, C.PROJECT_DIR / "Content" / rel, rep["template_content"])
        else:
            rep["template_content"][rel] = "missing in the engine install"
    put(C.PROJECT_DIR / "Config" / "DefaultInput.ini", TEMPLATE_INPUT_INI.read_text(encoding="utf-8-sig"), rep["files"])
    rep["pack_content"] = {}
    if PACK_CONTENT.exists():
        sync_tree(PACK_CONTENT, C.PROJECT_DIR / "Content" / "NinjaPack", rep["pack_content"])
    else:
        rep["pack_content"]["NinjaPack"] = "pack project content missing"
    rep["copied_from_demogame"] = copied
    need = {"r.AllowStaticLighting": "False", "r.Shadow.Virtual.Enable": "1", "r.GenerateMeshDistanceFields": "True",
            "r.DynamicGlobalIlluminationMethod": "1", "r.ReflectionMethod": "1", "r.RayTracing": "True",
            "r.Substrate": "True"}
    have = dict(copied["/Script/Engine.RendererSettings"])
    rep["render_settings_check"] = {k: have.get(k) == v for k, v in need.items()}
    rep["dx12_sm6"] = any(k == "+D3D12TargetedShaderFormats" and v == "PCD3D_SM6"
                          for k, v in copied["/Script/WindowsTargetPlatform.WindowsTargetSettings"])
    rep["passed"] = all(rep["render_settings_check"].values()) and rep["dx12_sm6"]
    C.write_json(C.OUT / "make_project.json", rep)
    print(json.dumps({k: rep[k] for k in ("files", "template_content", "render_settings_check", "dx12_sm6", "passed")},
                     indent=1))


main()
