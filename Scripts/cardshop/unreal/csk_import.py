"""CardShopKit G1 step: import (pythonscript commandlet, -nullrhi).

Meshes: every Exports/CardShopKit/G1/<mesh>.fbx -> /Game/CardShopKit/G1/Meshes with the house legacy-FBX settings (the
armory's proven FbxImportUI: Import Mesh LODs ON, no auto collision, one convex hull per UCX, imported normals, no
materials or textures, no generated lightmap UVs because the FBX carries UV1, Nanite off). A changed source is
deleted and imported fresh (a re-import keeps stale slot names, armory look2). Then the pipeline sidecar is applied
with ``pipeline.ue_import_sockets.apply_sidecar``: sockets recreated (the FBX ones arrive at scale 100) and the LOD
screen sizes set.
Textures: every G1 texture -> /Game/CardShopKit/G1/Textures, BaseColor sRGB, TC_Default.

Results: WorkFiles/cardshop/g1/unreal/import.json. The authoritative check is csk_verify.py in a fresh process.
"""
import json
import sys
import time
import traceback
from pathlib import Path

import unreal  # noqa: E402  (first: Scripts/unreal/ must never shadow the engine module)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))           # Scripts/ (for pipeline.ue_import_sockets)
import csk_common as C  # noqa: E402
from pipeline.ue_import_sockets import apply_sidecar  # noqa: E402

EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()


def mesh_options():
    ui = unreal.FbxImportUI()
    ui.set_editor_property("automated_import_should_detect_type", False)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
    ui.set_editor_property("import_as_skeletal", False)
    ui.set_editor_property("import_mesh", True)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("import_animations", False)
    sm = ui.get_editor_property("static_mesh_import_data")
    sm.set_editor_property("import_mesh_lods", True)
    sm.set_editor_property("auto_generate_collision", False)
    sm.set_editor_property("one_convex_hull_per_ucx", True)
    sm.set_editor_property("combine_meshes", False)
    sm.set_editor_property("generate_lightmap_u_vs", False)
    sm.set_editor_property("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    sm.set_editor_property("normal_generation_method", unreal.FBXNormalGenerationMethod.MIKK_T_SPACE)
    sm.set_editor_property("convert_scene", True)
    sm.set_editor_property("convert_scene_unit", True)
    sm.set_editor_property("force_front_x_axis", False)
    sm.set_editor_property("import_uniform_scale", 1.0)
    try:
        sm.set_editor_property("build_nanite", False)
    except Exception:  # noqa: BLE001
        pass
    return ui


def run_task(filename, dest, name, factory=None, options=None):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(filename))
    task.set_editor_property("destination_path", dest)
    task.set_editor_property("destination_name", name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("replace_existing_settings", True)
    task.set_editor_property("save", False)
    if factory is not None:
        task.set_editor_property("factory", factory)
    if options is not None:
        task.set_editor_property("options", options)
    AT.import_asset_tasks([task])
    return [str(p) for p in task.get_editor_property("imported_object_paths")]


def main():
    t0 = time.time()
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    rep = {"engine": unreal.SystemLibrary.get_engine_version(), "meshes": {}, "textures": {}}
    for name in C.MESHES:
        fbx = C.G1 / f"{name}.fbx"
        path = f"{C.MESH_DEST}/{name}"
        e = {"fbx": str(fbx)}
        try:
            if not fbx.exists():
                raise FileNotFoundError(f"{fbx} is missing: run the Blender build step first")
            if EAL.does_asset_exist(path):
                e["deleted_before_import"] = bool(EAL.delete_asset(path))
            e["imported"] = run_task(fbx, C.MESH_DEST, name, unreal.FbxFactory(), mesh_options())
            mesh = unreal.load_asset(path)
            if not isinstance(mesh, unreal.StaticMesh):
                raise RuntimeError(f"{path} is not a StaticMesh after import")
            e["saved"] = bool(EAL.save_loaded_asset(mesh, False))
            side = C.sidecar(name)
            if side is not None:
                r = apply_sidecar(str(side), path, name_from="socket", save=True)
                e["sidecar"] = {"sockets": r["sockets"], "lod_screen_sizes": r["lod_screen_sizes"], "saved": r["saved"]}
        except Exception:  # noqa: BLE001
            e["error"] = traceback.format_exc()[-1500:]
        rep["meshes"][name] = e
    for name in C.TEXTURES:
        png = C.TEX / f"{name}.png"
        path = f"{C.TEX_DEST}/{name}"
        e = {"png": str(png)}
        try:
            if not png.exists():
                raise FileNotFoundError(f"{png} is missing: run the art step first")
            run_task(png, C.TEX_DEST, name)
            tex = unreal.load_asset(path)
            tex.set_editor_property("srgb", True)
            tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_DEFAULT)
            e["saved"] = bool(EAL.save_loaded_asset(tex, False))
            e["size"] = [int(tex.blueprint_get_size_x()), int(tex.blueprint_get_size_y())]
        except Exception:  # noqa: BLE001
            e["error"] = traceback.format_exc()[-1500:]
        rep["textures"][name] = e
    rep["errors"] = [k for sec in ("meshes", "textures") for k, v in rep[sec].items() if v.get("error")]
    rep["passed"] = not rep["errors"]
    rep["sec"] = round(time.time() - t0, 1)
    C.write_json(C.OUT / "import.json", rep)
    unreal.log(f"CSK_STEP_DONE import passed={rep['passed']} meshes={len(rep['meshes'])} textures={len(rep['textures'])}")


main()
