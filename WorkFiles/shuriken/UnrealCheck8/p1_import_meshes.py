"""UnrealCheck8 process 1: import the three shipped FBX into /Game/ShurikenCheck8/Verify, apply each sidecar
with Scripts/pipeline/ue_import_sockets.py (unchanged), save. Legacy FBX importer, ASSET_GUIDELINES 6.5 options.
Records the SHA-256 of every FBX and sidecar before AND after the import. In-process reads are informational
only; the gates run in p3_readback.py in a fresh process. Writes p1_import.json.
"""
import json
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealCheck8")
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "Scripts"))

import unreal  # noqa: E402
import uc8_common as C  # noqa: E402
from pipeline.ue_import_sockets import apply_sidecar  # noqa: E402


def fbx_options():
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
    sm.set_editor_property("generate_lightmap_u_vs", True)
    sm.set_editor_property("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    sm.set_editor_property("normal_generation_method", unreal.FBXNormalGenerationMethod.MIKK_T_SPACE)
    sm.set_editor_property("convert_scene", True)
    sm.set_editor_property("convert_scene_unit", True)
    sm.set_editor_property("force_front_x_axis", False)
    sm.set_editor_property("import_uniform_scale", 1.0)
    return ui


def main():
    report = {"engine": unreal.SystemLibrary.get_engine_version(), "dest": C.DEST, "forms": {}}
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    for form in C.FORMS:
        rec = {"fbx": str(C.fbx(form)), "sidecar": str(C.sidecar(form)),
               "fbx_sha256_before": C.sha256(C.fbx(form)), "sidecar_sha256_before": C.sha256(C.sidecar(form)),
               "fbx_md5": C.md5(C.fbx(form)),
               "asset_existed_before_import": bool(unreal.EditorAssetLibrary.does_asset_exist(C.asset(form)))}
        try:
            task = unreal.AssetImportTask()
            task.set_editor_property("filename", str(C.fbx(form)))
            task.set_editor_property("destination_path", C.DEST)
            task.set_editor_property("destination_name", C.FORMS[form]["mesh"])
            task.set_editor_property("automated", True)
            task.set_editor_property("replace_existing", True)
            task.set_editor_property("replace_existing_settings", True)
            task.set_editor_property("save", True)
            task.set_editor_property("factory", unreal.FbxFactory())
            task.set_editor_property("options", fbx_options())
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            paths = [str(p) for p in task.get_editor_property("imported_object_paths")]
            rec["imported_object_paths"] = paths
            objs = [unreal.load_asset(p) for p in paths]
            rec["imported_classes"] = [o.get_class().get_name() if o else None for o in objs]
            meshes = [m for m in objs if isinstance(m, unreal.StaticMesh)]
            rec["imported_static_meshes"] = len(meshes)
            if meshes:
                mesh = meshes[0]
                rec["after_import_in_process"] = C.inspect_mesh(mesh)
                asset_path = mesh.get_path_name().split(".")[0]
                rec["sidecar_result"] = apply_sidecar(str(C.sidecar(form)), asset_path)
                rec["after_sidecar_in_process"] = C.inspect_mesh(mesh)
                rec["saved_again"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(mesh))
        except Exception:  # noqa: BLE001
            rec["error"] = traceback.format_exc()
        rec["fbx_sha256_after"] = C.sha256(C.fbx(form))
        rec["sidecar_sha256_after"] = C.sha256(C.sidecar(form))
        report["forms"][form] = rec
    C.write(C.HERE / "p1_import.json", report)
    unreal.log("UC8_P1_DONE")


main()
