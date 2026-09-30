"""DojoLab step (pythonscript commandlet, -nullrhi): import the grey-box meshes into /Game/DojoKit/Greybox/Meshes.

Every Exports/DojoKit/SM_DGB_*.fbx with the legacy FBX importer (Interchange.FeatureFlags.Import.FBX 0) and the armory's
proven FbxImportUI: no auto collision, one convex hull per UCX, imported normals, no materials / textures, lightmap UV
generation off (AllowStaticLighting False), Nanite off (the whole grey-box is about 1.5k triangles).
Idempotent: a mesh whose FBX sha256 matches import_manifest.json is skipped unless DJ_FORCE_IMPORT=1; a changed source is
deleted and imported fresh (a reimport keeps stale slot names). Our own meshes that the kit no longer exports are deleted.
Result: WorkFiles/dojo/build/unreal/import.json (dj_verify.py is the authoritative check).
"""
import hashlib
import os
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unreal  # noqa: E402
import dj_common as C  # noqa: E402
import json  # noqa: E402

EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
MANIFEST = C.OUT / "import_manifest.json"
FORCE = os.environ.get("DJ_FORCE_IMPORT", "0") == "1"


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


def main():
    t0 = time.time()
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    man = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    rep = {"engine": unreal.SystemLibrary.get_engine_version(), "force": FORCE, "meshes": {}}
    for fbx in sorted(C.EXPORTS.glob(C.MESH_PREFIX + "*.fbx")):
        name, path = fbx.stem, f"{C.MESH_DEST}/{fbx.stem}"
        h = hashlib.sha256(fbx.read_bytes()).hexdigest()
        e = {"sha256": h}
        try:
            if not FORCE and man.get(path) == h and EAL.does_asset_exist(path):
                e["skipped"] = "unchanged source, asset exists"
            else:
                if EAL.does_asset_exist(path):
                    e["deleted_before_import"] = bool(EAL.delete_asset(path))
                task = unreal.AssetImportTask()
                for k, v in (("filename", str(fbx)), ("destination_path", C.MESH_DEST), ("destination_name", name),
                             ("automated", True), ("replace_existing", True), ("replace_existing_settings", True),
                             ("save", False), ("factory", unreal.FbxFactory()), ("options", mesh_options())):
                    task.set_editor_property(k, v)
                AT.import_asset_tasks([task])
                e["imported"] = [str(p) for p in task.get_editor_property("imported_object_paths")]
            mesh = unreal.load_asset(path)
            if not isinstance(mesh, unreal.StaticMesh):
                raise RuntimeError(f"{path} is not a StaticMesh after import")
            agg = mesh.get_editor_property("body_setup").get_editor_property("agg_geom")
            e["convex"] = len(agg.get_editor_property("convex_elems"))
            e["slots"] = [str(s.get_editor_property("material_slot_name")) for s in mesh.get_editor_property("static_materials")]
            if "imported" in e:
                e["saved"] = bool(EAL.save_loaded_asset(mesh, False))
                if e["saved"]:
                    man[path] = h
        except Exception:  # noqa: BLE001
            e["error"] = traceback.format_exc()[-1500:]
        rep["meshes"][name] = e
    C.write_json(MANIFEST, man)
    stems = {f.stem for f in C.EXPORTS.glob(C.MESH_PREFIX + "*.fbx")}
    rep["stale_deleted"] = []
    if EAL.does_directory_exist(C.MESH_DEST):
        for p in sorted(EAL.list_assets(C.MESH_DEST, recursive=False, include_folder=False)):
            base = p.split(".")[0]
            if base.rsplit("/", 1)[-1] not in stems and EAL.delete_asset(base):
                rep["stale_deleted"].append(base)
    rep["n_meshes"] = len(rep["meshes"])
    rep["errors"] = [k for k, v in rep["meshes"].items() if v.get("error")]
    rep["passed"] = rep["n_meshes"] == C.n_meshes() and not rep["errors"]
    rep["sec"] = round(time.time() - t0, 1)
    C.write_json(C.OUT / "import.json", rep)
    unreal.log(f"DJ_STEP_DONE import passed={rep['passed']} meshes={rep['n_meshes']}")


main()
