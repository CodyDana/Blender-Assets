"""ArmoryLab step "firstperson" (pythonscript commandlet, -nullrhi): V toggles first person (user, 2026-10-01: "have the
option to go to first person on the 'v' key").

Needs the ArmoryLab C++ module built (run_armory_unreal.sh "build"; sources in Scripts/armory/unreal/cpp). Idempotent:
 1 /Game/ArmoryLab/Input/IA_ToggleView   InputAction (bool), created once
 2 /Game/ArmoryLab/Input/IMC_ArmoryView  InputMappingContext with exactly one mapping, V -> IA_ToggleView (the template's
                                        IMC_Default / IMC_MouseLook are untouched; the component adds this one on top)
 3 our copy of BP_ThirdPersonCharacter gets ONE ArmoryViewToggleComponent ("ViewToggle") with the action and context
   assigned; compiled and saved. The template's CameraBoom / FollowCamera stay exactly as they are.
Gate: re-read from disk: the assets exist, V is the context's only key for the action, the Blueprint holds exactly one
toggle component with both assigned, the Blueprint compiles. The runtime proof is the "fptest" step (ak_fptest.ps1).
Result: WorkFiles/armory/build/unreal/firstperson.json
"""
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unreal  # noqa: E402
import ak_common as C  # noqa: E402

EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
CH = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
INPUT_DIR = "/Game/ArmoryLab/Input"
IA = f"{INPUT_DIR}/IA_ToggleView"
IMC = f"{INPUT_DIR}/IMC_ArmoryView"
KEY = "V"
COMP_NAME = "ViewToggle"
REP = {"engine": unreal.SystemLibrary.get_engine_version(), "notes": []}


def make_key(name):
    k = unreal.Key()
    try:
        k.set_editor_property("key_name", name)
    except Exception:  # noqa: BLE001
        k.import_text(name)
    return k


def key_name(k):
    try:
        return str(k.get_editor_property("key_name"))
    except Exception:  # noqa: BLE001
        return str(k.export_text())


def ensure_asset(path, cls, factory):
    if EAL.does_asset_exist(path):
        a = unreal.load_asset(path)
        if isinstance(a, cls):
            return a, False
        raise RuntimeError(f"{path} exists but is a {type(a).__name__}, not {cls.__name__}")
    d, n = path.rsplit("/", 1)
    a = AT.create_asset(n, d, cls, factory)
    if a is None:
        raise RuntimeError(f"could not create {path}")
    return a, True


def mappings_of(imc):
    out = []
    for m in imc.get_editor_property("default_key_mappings").get_editor_property("mappings"):
        act = m.get_editor_property("action")
        out.append((act.get_path_name().split(".")[0] if act else None, key_name(m.get_editor_property("key"))))
    return out


def input_assets():
    ia, ia_new = ensure_asset(IA, unreal.InputAction, unreal.InputAction_Factory())
    if ia_new or str(ia.get_editor_property("value_type")) != str(unreal.InputActionValueType.BOOLEAN):
        ia.set_editor_property("value_type", unreal.InputActionValueType.BOOLEAN)
    imc, imc_new = ensure_asset(IMC, unreal.InputMappingContext, unreal.InputMappingContext_Factory())
    if mappings_of(imc) != [(IA, KEY)]:
        imc.unmap_all()
        imc.map_key(ia, make_key(KEY))
    REP["input"] = {"ia_created": ia_new, "imc_created": imc_new,
                    "ia_saved": bool(EAL.save_loaded_asset(ia, False)),
                    "imc_saved": bool(EAL.save_loaded_asset(imc, False))}
    return ia, imc


def toggle_handles(sds, bp):
    out = []
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        obj = unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(unreal.SubobjectDataBlueprintFunctionLibrary.get_data(h))
        if isinstance(obj, unreal.ArmoryViewToggleComponent):
            out.append((h, obj))
    return out


def wire_character(ia, imc):
    bp = unreal.load_asset(CH)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    found = toggle_handles(sds, bp)
    added = False
    if not found:
        root = sds.k2_gather_subobject_data_for_blueprint(bp)[0]
        params = unreal.AddNewSubobjectParams(parent_handle=root, new_class=unreal.ArmoryViewToggleComponent,
                                              blueprint_context=bp)
        handle, fail = sds.add_new_subobject(params)
        if not unreal.SubobjectDataBlueprintFunctionLibrary.is_handle_valid(handle):
            raise RuntimeError(f"add_new_subobject failed: {fail}")
        try:
            sds.rename_subobject(handle, unreal.Text(COMP_NAME))
        except Exception as exc:  # noqa: BLE001
            REP["notes"].append(f"rename: {str(exc)[:160]}")
        added = True
        found = toggle_handles(sds, bp)
    for _h, comp in found:
        comp.set_editor_property("toggle_view_action", ia)
        comp.set_editor_property("toggle_view_context", imc)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    saved = bool(EAL.save_asset(CH, only_if_is_dirty=False))
    REP["character"] = {"component_added": added, "n_toggle_components": len(found), "saved": saved}


def gate():
    """Re-read from disk (fresh loads) what the step wrote."""
    g = {}
    ia = unreal.load_asset(IA)
    imc = unreal.load_asset(IMC)
    g["ia"] = isinstance(ia, unreal.InputAction)
    g["imc_mappings"] = mappings_of(imc) if isinstance(imc, unreal.InputMappingContext) else None
    g["v_mapped"] = g["imc_mappings"] == [(IA, KEY)]
    bp = unreal.load_asset(CH)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    comps = toggle_handles(sds, bp)
    g["n_toggle_components"] = len(comps)
    if comps:
        c = comps[0][1]
        a, m = c.get_editor_property("toggle_view_action"), c.get_editor_property("toggle_view_context")
        g["assigned_action"] = a.get_path_name().split(".")[0] if a else None
        g["assigned_context"] = m.get_path_name().split(".")[0] if m else None
        g["component_class"] = c.get_class().get_path_name()
    # the template cameras are still there (third person is the default view)
    names = []
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        o = unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(unreal.SubobjectDataBlueprintFunctionLibrary.get_data(h))
        if isinstance(o, (unreal.CameraComponent, unreal.SpringArmComponent)):
            names.append(o.get_name())
    g["template_cameras"] = sorted(names)
    g["passed"] = bool(g["ia"] and g["v_mapped"] and g["n_toggle_components"] == 1 and g.get("assigned_action") == IA
                       and g.get("assigned_context") == IMC and len(names) >= 2)
    return g


def main():
    t0 = time.time()
    try:
        if not hasattr(unreal, "ArmoryViewToggleComponent"):
            raise RuntimeError("the ArmoryLab C++ module is not loaded: run run_armory_unreal.sh project build first")
        ia, imc = input_assets()
        wire_character(ia, imc)
        REP["gate"] = gate()
        REP["passed"] = REP["gate"]["passed"] and REP["character"]["saved"]
    except Exception:  # noqa: BLE001
        REP["error"] = traceback.format_exc()[-3000:]
        REP["passed"] = False
    REP["sec"] = round(time.time() - t0, 1)
    C.write_json(C.OUT / "firstperson.json", REP)
    unreal.log(f"AK_STEP_DONE firstperson passed={REP['passed']}")


main()
