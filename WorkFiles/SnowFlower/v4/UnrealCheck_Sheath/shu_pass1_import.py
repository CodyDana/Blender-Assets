"""Pass 1: import the shipped sheath FBX (and the shipped v4 sword FBX beside it, for the Holster gate) into
the check content path and apply each sidecar.

Legacy FBX importer, Import Mesh LODs ON, no auto collision, one convex hull per UCX,
Generate Lightmap UVs ON, normals imported.  The sidecar goes through
Scripts/pipeline/ue_import_sockets.py UNCHANGED, which performs the only save (the
kunai's triple-save race).  Textures are imported by the props importer in their own
processes.  In-process reads are recorded but are NOT the gate: pass 2 is.
"""
import json
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\SnowFlower\v4\UnrealCheck_Sheath")
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[3] / "Scripts"))

import unreal                                                   # noqa: E402
import shu_common as C                                          # noqa: E402
from pipeline.ue_import_sockets import apply_sidecar            # noqa: E402

OUT = C.HERE / "pass1.json"


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


def import_one(fbx, name, sidecar, report, key):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(fbx))
    task.set_editor_property("destination_path", C.DEST)
    task.set_editor_property("destination_name", name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("replace_existing_settings", True)
    task.set_editor_property("save", False)
    task.set_editor_property("factory", unreal.FbxFactory())
    task.set_editor_property("options", mesh_options())
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    paths = [str(p) for p in task.get_editor_property("imported_object_paths")]
    report[key + "_imported_object_paths"] = paths
    meshes = [m for m in (unreal.load_asset(p) for p in paths) if isinstance(m, unreal.StaticMesh)]
    report[key + "_imported_static_meshes"] = len(meshes)
    if not meshes:
        return None
    mesh0 = meshes[0]
    asset_path = mesh0.get_path_name().split(".")[0]
    # the FBX ships its own UV1: generate Unreal's lightmap into channel 1 and point the lightmap at it
    sub = C.subsystem()
    for i in range(mesh0.get_num_lods()):
        bs = sub.get_lod_build_settings(mesh0, i)
        bs.set_editor_property("generate_lightmap_u_vs", True)
        bs.set_editor_property("src_lightmap_index", 0)
        bs.set_editor_property("dst_lightmap_index", 1)
        sub.set_lod_build_settings(mesh0, i, bs)
    mesh0.set_editor_property("light_map_coordinate_index", 1)
    report[key + "_sidecar_result"] = C.safe(lambda: apply_sidecar(str(sidecar), asset_path))
    return mesh0


def main():
    report = {"engine": unreal.SystemLibrary.get_engine_version(), "asset": C.MESH, "dest": C.ASSET,
              "fbx": str(C.FBX), "sidecar": str(C.SIDECAR),
              "fbx_sha256": C.sha256(C.FBX), "sidecar_sha256": C.sha256(C.SIDECAR),
              "report_fbx_sha256": C.REPORT["export"]["sha256"]["fbx"],
              "sword_fbx_sha256": C.sha256(C.SWORD_FBX),
              "asset_existed_before_import": bool(unreal.EditorAssetLibrary.does_asset_exist(C.ASSET))}
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    try:
        mesh = import_one(C.FBX, C.MESH, C.SIDECAR, report, "sheath")
        import_one(C.SWORD_FBX, C.SWORD_MESH, C.SWORD_SIDECAR, report, "sword")
        if mesh is not None:
            info = C.inspect(mesh)
            report["after_sidecar"] = info
            report["in_process_gates_not_authoritative"] = C.gates(info)[0]
            report["saved"] = bool((report.get("sheath_sidecar_result") or {}).get("saved"))
            report["sword_saved"] = bool((report.get("sword_sidecar_result") or {}).get("saved"))
    except Exception:
        report["error"] = traceback.format_exc()
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    unreal.log("SHU_PASS1_DONE " + str(OUT))


main()
