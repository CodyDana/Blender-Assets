"""UnrealCheck9 step 1 (own process): import the shipped SM_Shuriken_SixPoint.fbx into a FRESH content path,
apply its sidecar with Scripts/pipeline/ue_import_sockets.py (unchanged), save.

Legacy FBX importer, ASSET_GUIDELINES 6.5 options. Records the SHA-256 / MD5 of the exact FBX and sidecar bytes
before and after the import. In-process reads are informational only; s3_readback.py is the gate.
Writes s1_import.json.
"""
import json
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealCheck9_SixPoint")
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "Scripts"))

import unreal  # noqa: E402
import u9_common as C  # noqa: E402
from pipeline.ue_import_sockets import apply_sidecar  # noqa: E402


def fbx_options():
    ui = unreal.FbxImportUI()
    ui.set_editor_property("automated_import_should_detect_type", False)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
    ui.set_editor_property("import_as_skeletal", False)
    ui.set_editor_property("import_mesh", True)
    ui.set_editor_property("import_materials", False)      # Do Not Create Material
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("import_animations", False)
    sm = ui.get_editor_property("static_mesh_import_data")
    sm.set_editor_property("import_mesh_lods", True)        # Import Mesh LODs ON
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
    rep = {"engine": unreal.SystemLibrary.get_engine_version(), "asset": C.ASSET,
           "fbx": str(C.FBX), "sidecar": str(C.SIDECAR),
           "fbx_sha256_before": C.sha256(C.FBX), "fbx_md5_before": C.md5(C.FBX),
           "sidecar_sha256_before": C.sha256(C.SIDECAR),
           "dest_existed_before": bool(unreal.EditorAssetLibrary.does_directory_exist(C.DEST)),
           "asset_existed_before": bool(unreal.EditorAssetLibrary.does_asset_exist(C.ASSET))}
    try:
        rep["cvar_interchange_fbx"] = unreal.SystemLibrary.get_console_variable_int_value(
            "Interchange.FeatureFlags.Import.FBX")
    except Exception as exc:  # noqa: BLE001
        rep["cvar_interchange_fbx"] = f"{type(exc).__name__}: {exc}"[:160]
    try:
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", str(C.FBX))
        task.set_editor_property("destination_path", C.DEST)
        task.set_editor_property("destination_name", C.MESH)
        task.set_editor_property("automated", True)
        task.set_editor_property("replace_existing", True)
        task.set_editor_property("save", True)
        task.set_editor_property("factory", unreal.FbxFactory())
        task.set_editor_property("options", fbx_options())
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        rep["imported_object_paths"] = [str(p) for p in task.get_editor_property("imported_object_paths")]
        meshes = [m for m in (unreal.load_asset(p) for p in rep["imported_object_paths"])
                  if isinstance(m, unreal.StaticMesh)]
        rep["imported_static_meshes"] = len(meshes)
        if meshes:
            mesh = meshes[0]
            asset_path = mesh.get_path_name().split(".")[0]
            rep["asset_path"] = asset_path
            rep["in_process_after_import"] = {
                "num_lods": mesh.get_num_lods(),
                "lod_triangles": [mesh.get_num_triangles(i) for i in range(mesh.get_num_lods())],
                "convex_hulls": len(mesh.get_editor_property("body_setup").get_editor_property("agg_geom")
                                    .get_editor_property("convex_elems")),
            }
            rep["sidecar_result"] = apply_sidecar(str(C.SIDECAR), asset_path)
            rep["saved_again"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(mesh))
    except Exception:  # noqa: BLE001
        rep["error"] = traceback.format_exc()
    rep["fbx_sha256_after"] = C.sha256(C.FBX)
    rep["sidecar_sha256_after"] = C.sha256(C.SIDECAR)
    rep["bytes_unchanged_by_import"] = (rep["fbx_sha256_after"] == rep["fbx_sha256_before"]
                                        and rep["sidecar_sha256_after"] == rep["sidecar_sha256_before"])
    C.write(C.HERE / "s1_import.json", rep)
    unreal.log("U9_S1_DONE")


main()
