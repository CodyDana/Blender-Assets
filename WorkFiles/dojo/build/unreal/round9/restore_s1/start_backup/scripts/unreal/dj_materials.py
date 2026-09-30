"""DojoLab step (pythonscript commandlet, -nullrhi): the grey-box materials, built here and only here.

Master /Game/DojoKit/Greybox/Materials/M_DGB_FlatMaster (default lit: "Base Colour" vector, "Roughness" scalar), rebuilt
from scratch every run. One MaterialInstanceConstant per layout.json material, named exactly like the Blender slot
(M_DGB_Sand ...), colour = the layout's sRGB hex converted to linear. Every grey-box mesh then gets, per slot, the instance
named like the slot. The shared pack masters and the GASP materials are not touched.
Result: WorkFiles/dojo/build/unreal/materials.json
"""
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unreal  # noqa: E402
import dj_common as C  # noqa: E402

EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
MASTER = f"{C.MAT_DEST}/M_DGB_FlatMaster"


def get_or_create(path, cls, factory):
    if EAL.does_asset_exist(path):
        a = unreal.load_asset(path)
        if not isinstance(a, cls):
            raise TypeError(f"{path} exists as {type(a).__name__}, not {cls.__name__}: refusing to touch it")
        return a
    folder, name = path.rsplit("/", 1)
    a = AT.create_asset(name, folder, cls, factory)
    if a is None:
        raise RuntimeError(f"could not create {path}")
    return a


def build_master():
    m = get_or_create(MASTER, unreal.Material, unreal.MaterialFactoryNew())
    MEL.delete_all_material_expressions(m)
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    col = MEL.create_material_expression(m, unreal.MaterialExpressionVectorParameter, -400, 0)
    col.set_editor_property("parameter_name", "Base Colour")
    col.set_editor_property("default_value", unreal.LinearColor(0.5, 0.5, 0.5, 1.0))
    rough = MEL.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -400, 200)
    rough.set_editor_property("parameter_name", "Roughness")
    rough.set_editor_property("default_value", 0.85)
    MEL.connect_material_property(col, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m, False)
    return m


def main():
    t0 = time.time()
    rep = {"engine": unreal.SystemLibrary.get_engine_version(), "instances": {}, "assigned": {}, "errors": []}
    try:
        layout = C.load_layout()
        master = build_master()
        rep["master"] = MASTER
        for name, p in layout["materials"].items():
            mi = get_or_create(f"{C.MAT_DEST}/{name}", unreal.MaterialInstanceConstant,
                               unreal.MaterialInstanceConstantFactoryNew())
            MEL.set_material_instance_parent(mi, master)
            r, g, b = C.hexcol(p["srgb"])
            MEL.set_material_instance_vector_parameter_value(mi, "Base Colour", unreal.LinearColor(r, g, b, 1.0))
            MEL.set_material_instance_scalar_parameter_value(mi, "Roughness", float(p["roughness"]))
            MEL.update_material_instance(mi)
            EAL.save_loaded_asset(mi, False)
            rep["instances"][name] = {"linear": [round(r, 4), round(g, 4), round(b, 4)], "roughness": p["roughness"]}
        for piece in layout["pieces"]:
            mesh = unreal.load_asset(f"{C.MESH_DEST}/{piece}")
            if mesh is None:
                rep["errors"].append(f"missing mesh {piece}")
                continue
            slots = mesh.get_editor_property("static_materials")
            got = {}
            for i, s in enumerate(slots):
                sn = str(s.get_editor_property("material_slot_name"))
                mi = unreal.load_asset(f"{C.MAT_DEST}/{sn}")
                if mi is None:
                    rep["errors"].append(f"{piece}: no instance for slot {sn}")
                    continue
                mesh.set_material(i, mi)
                got[sn] = mi.get_name()
            EAL.save_loaded_asset(mesh, False)
            rep["assigned"][piece] = got
    except Exception:  # noqa: BLE001
        rep["errors"].append(traceback.format_exc()[-2000:])
    rep["passed"] = not rep["errors"] and len(rep["assigned"]) == len(C.load_layout()["pieces"])
    rep["sec"] = round(time.time() - t0, 1)
    C.write_json(C.OUT / "materials.json", rep)
    unreal.log(f"DJ_STEP_DONE materials passed={rep['passed']} instances={len(rep['instances'])}")


main()
