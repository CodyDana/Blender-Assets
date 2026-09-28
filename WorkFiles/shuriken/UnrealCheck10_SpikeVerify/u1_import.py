"""UnrealCheck10 process 1: import the shipped SM_Shuriken_Spike.fbx into a FRESH content path, apply its sidecar with
Scripts/pipeline/ue_import_sockets.py (unchanged), save. Legacy FBX importer with the ASSET_GUIDELINES 6.5 options
(Import Mesh LODs ON, One Convex Hull per UCX, Auto Generate Collision OFF, Generate Lightmap UVs ON, Import Normals
+ MikkTSpace, Convert Scene + Unit ON, Force Front X OFF, uniform scale 1).
Refuses to run if the destination already holds anything. Records the SHA-256 of the FBX and sidecar before and
after. In-process reads are informational only; the gates run in u3_readback.py (a fresh process).
Writes u1_import.json.
"""
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealCheck10_SpikeVerify")
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "Scripts"))

import unreal  # noqa: E402
import uc10_common as C  # noqa: E402
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
    rep = {"engine": unreal.SystemLibrary.get_engine_version(), "dest": C.DEST, "fbx": str(C.FBX),
           "sidecar": str(C.SIDECAR), "fbx_sha256_before": C.sha256(C.FBX), "fbx_md5": C.md5(C.FBX),
           "sidecar_sha256_before": C.sha256(C.SIDECAR)}
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    rep["dest_existed_before"] = bool(unreal.EditorAssetLibrary.does_directory_exist(C.DEST))
    rep["dest_assets_before"] = [str(a) for a in unreal.EditorAssetLibrary.list_assets(C.DEST, recursive=True)] \
        if rep["dest_existed_before"] else []
    if rep["dest_assets_before"]:
        rep["error"] = "destination not fresh; refusing to import"
        C.write(C.HERE / "u1_import.json", rep)
        unreal.log("UC10_U1_REFUSED")
        return
    try:
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", str(C.FBX))
        task.set_editor_property("destination_path", C.DEST)
        task.set_editor_property("destination_name", C.MESH)
        task.set_editor_property("automated", True)
        task.set_editor_property("replace_existing", True)
        task.set_editor_property("replace_existing_settings", True)
        task.set_editor_property("save", True)
        task.set_editor_property("factory", unreal.FbxFactory())
        task.set_editor_property("options", fbx_options())
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        paths = [str(p) for p in task.get_editor_property("imported_object_paths")]
        rep["imported_object_paths"] = paths
        objs = [unreal.load_asset(p) for p in paths]
        rep["imported_classes"] = [o.get_class().get_name() if o else None for o in objs]
        meshes = [m for m in objs if isinstance(m, unreal.StaticMesh)]
        rep["imported_static_meshes"] = len(meshes)
        if meshes:
            mesh = meshes[0]
            rep["after_import_in_process_info_only"] = C.inspect_mesh(mesh)
            asset_path = mesh.get_path_name().split(".")[0]
            rep["sidecar_result"] = apply_sidecar(str(C.SIDECAR), asset_path)
            rep["saved_again"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(mesh))
    except Exception:  # noqa: BLE001
        rep["error"] = traceback.format_exc()
    rep["fbx_sha256_after"] = C.sha256(C.FBX)
    rep["sidecar_sha256_after"] = C.sha256(C.SIDECAR)
    rep["dest_assets_after"] = [str(a) for a in unreal.EditorAssetLibrary.list_assets(C.DEST, recursive=True)]
    C.write(C.HERE / "u1_import.json", rep)
    unreal.log("UC10_U1_DONE")


main()
