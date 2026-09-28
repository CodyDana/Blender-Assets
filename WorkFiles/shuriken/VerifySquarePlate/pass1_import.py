"""Verifier pass 1 (process 1): import the shipped FBX into the verifier's OWN content path, apply the sidecar, save.

Legacy FBX importer with the ASSET_GUIDELINES 6.5 options. The sidecar goes through the unmodified
Scripts/pipeline/ue_import_sockets.apply_sidecar. SHA-256 of the FBX and sidecar is taken immediately
before and after the import, so the evidence is tied to exact bytes. Nothing read back here is a gate.
"""
import json
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\VerifySquarePlate")
sys.path.insert(0, str(HERE))

import unreal  # noqa: E402
import vsp_unreal as U  # noqa: E402
from pipeline.ue_import_sockets import apply_sidecar  # noqa: E402

V, C, S = U.V, U.C, U.S
OUT = HERE / f"{V.FORM}_vpass1.json"


def options():
    ui = unreal.FbxImportUI()
    ui.set_editor_property("automated_import_should_detect_type", False)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
    ui.set_editor_property("import_as_skeletal", False)
    ui.set_editor_property("import_mesh", True)
    ui.set_editor_property("import_materials", False)       # Do Not Create Material
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("import_animations", False)
    sm = ui.get_editor_property("static_mesh_import_data")
    sm.set_editor_property("import_mesh_lods", True)          # Import Mesh LODs ON
    sm.set_editor_property("auto_generate_collision", False)  # UCX present
    sm.set_editor_property("one_convex_hull_per_ucx", True)
    sm.set_editor_property("combine_meshes", False)
    sm.set_editor_property("generate_lightmap_u_vs", True)    # not Nanite
    sm.set_editor_property("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    sm.set_editor_property("normal_generation_method", unreal.FBXNormalGenerationMethod.MIKK_T_SPACE)
    sm.set_editor_property("convert_scene", True)
    sm.set_editor_property("convert_scene_unit", True)
    sm.set_editor_property("force_front_x_axis", False)
    sm.set_editor_property("import_uniform_scale", 1.0)
    return ui


def main():
    report = {"engine": unreal.SystemLibrary.get_engine_version(), "form": V.FORM, "fbx": str(S["fbx"]),
              "sidecar": str(S["sidecar"]), "dest": S["asset"],
              "sha256_before_import": {"fbx": V.sha256(S["fbx"]), "sidecar": V.sha256(S["sidecar"])},
              "asset_existed_before_import": bool(unreal.EditorAssetLibrary.does_asset_exist(S["asset"])),
              "build_agent_asset_untouched_path": f"{V.BUILD_AGENT_DEST}/{S['mesh']}"}
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    try:
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", str(S["fbx"]))
        task.set_editor_property("destination_path", V.DEST)
        task.set_editor_property("destination_name", S["mesh"])
        task.set_editor_property("automated", True)
        task.set_editor_property("replace_existing", True)
        task.set_editor_property("replace_existing_settings", True)
        task.set_editor_property("save", True)
        task.set_editor_property("factory", unreal.FbxFactory())
        task.set_editor_property("options", options())
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        paths = [str(p) for p in task.get_editor_property("imported_object_paths")]
        report["imported_object_paths"] = paths
        meshes = [m for m in (unreal.load_asset(p) for p in paths) if isinstance(m, unreal.StaticMesh)]
        report["imported_static_meshes"] = len(meshes)
        if meshes:
            asset_path = meshes[0].get_path_name().split(".")[0]
            report["sidecar_result"] = apply_sidecar(str(S["sidecar"]), asset_path)
            report["saved"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(meshes[0]))
            report["in_process_not_authoritative"] = {"lod_triangles": [meshes[0].get_num_triangles(i)
                                                                        for i in range(meshes[0].get_num_lods())]}
    except Exception:
        report["error"] = traceback.format_exc()
    report["sha256_after_import"] = {"fbx": V.sha256(S["fbx"]), "sidecar": V.sha256(S["sidecar"])}
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    unreal.log("VPASS1_DONE " + str(OUT))


main()
