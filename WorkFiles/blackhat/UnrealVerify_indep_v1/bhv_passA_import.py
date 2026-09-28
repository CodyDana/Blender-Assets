"""PASS A (process 1) - import the shipped FBX into a FRESH content path and apply the sidecar.

Legacy FBX importer (Interchange FBX off), Import Mesh LODs ON, no auto collision, one
convex hull per UCX, Generate Lightmap UVs ON, normals imported.  save=False on the import
task; Scripts/pipeline/ue_import_sockets.apply_sidecar (unchanged, imported read-only) does
the only save.  Nothing read here is a gate: the gates are read in pass B, a second fresh
process, off the saved package.
"""
import json
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\blackhat\UnrealVerify_indep_v1")
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "Scripts"))

import unreal                                                    # noqa: E402
import bhv_common as C                                           # noqa: E402
from pipeline.ue_import_sockets import apply_sidecar             # noqa: E402

OUT = HERE / "passA.json"


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
    sm.set_editor_property("generate_lightmap_u_vs", True)
    sm.set_editor_property("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    sm.set_editor_property("normal_generation_method", unreal.FBXNormalGenerationMethod.MIKK_T_SPACE)
    sm.set_editor_property("convert_scene", True)
    sm.set_editor_property("convert_scene_unit", True)
    sm.set_editor_property("force_front_x_axis", False)
    sm.set_editor_property("import_uniform_scale", 1.0)
    return ui


def main():
    rep = {"engine": unreal.SystemLibrary.get_engine_version(), "dest": C.DEST, "asset": C.ASSET,
           "hashes_before": C.all_hashes()}
    try:
        rep["dest_existed_before"] = bool(unreal.EditorAssetLibrary.does_directory_exist(C.DEST))
        rep["asset_existed_before"] = bool(unreal.EditorAssetLibrary.does_asset_exist(C.ASSET))
        unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", str(C.FBX))
        task.set_editor_property("destination_path", C.DEST)
        task.set_editor_property("destination_name", C.MESH_NAME)
        task.set_editor_property("automated", True)
        task.set_editor_property("replace_existing", True)
        task.set_editor_property("replace_existing_settings", True)
        task.set_editor_property("save", False)
        task.set_editor_property("factory", unreal.FbxFactory())
        task.set_editor_property("options", mesh_options())
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        paths = [str(p) for p in task.get_editor_property("imported_object_paths")]
        rep["imported_object_paths"] = paths
        meshes = [m for m in (unreal.load_asset(p) for p in paths) if isinstance(m, unreal.StaticMesh)]
        rep["imported_static_mesh_count"] = len(meshes)
        if meshes:
            mesh = meshes[0]
            rep["before_sidecar_in_process"] = C.inspect_mesh(mesh)
            asset_path = mesh.get_path_name().split(".")[0]
            rep["sidecar_result"] = C.safe(lambda: apply_sidecar(str(C.SIDECAR), asset_path))
            rep["after_sidecar_in_process_NOT_A_GATE"] = C.inspect_mesh(mesh)
    except Exception:                                            # noqa: BLE001
        rep["error"] = traceback.format_exc()
    rep["hashes_after"] = C.all_hashes()
    OUT.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
    unreal.log("BHV_PASSA_DONE " + str(OUT))


main()
