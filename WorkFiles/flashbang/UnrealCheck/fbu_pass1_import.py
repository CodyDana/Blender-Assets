"""Pass 1 (its own process): import the four shipped FBX (legacy importer, Import Mesh LODs ON, one hull per UCX,
lightmap UVs generated into index 1, normals imported) and apply each sidecar with Scripts/pipeline/ue_import_sockets.py
UNCHANGED (it does the save)."""
import json
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\flashbang\UnrealCheck")
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "Scripts"))
import unreal  # noqa: E402
import fbu_common as C  # noqa: E402
from pipeline.ue_import_sockets import apply_sidecar  # noqa: E402


def options():
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
    sm.set_editor_property("generate_lightmap_u_vs", False)   # the FBX ships its own UV1 (lightmap)
    sm.set_editor_property("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    sm.set_editor_property("normal_generation_method", unreal.FBXNormalGenerationMethod.MIKK_T_SPACE)
    sm.set_editor_property("convert_scene", True)
    sm.set_editor_property("convert_scene_unit", True)
    sm.set_editor_property("force_front_x_axis", False)
    sm.set_editor_property("import_uniform_scale", 1.0)
    return ui


rep = {"engine": unreal.SystemLibrary.get_engine_version(), "dest": C.DEST, "meshes": {}}
unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
for key, name in C.MESHES.items():
    r = {}
    try:
        fbx = C.EXP / f"{name}.fbx"
        side = C.EXP / f"{name}.sockets.json"
        r["fbx_sha256"], r["sidecar_sha256"] = C.sha256(fbx), C.sha256(side)
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", str(fbx))
        task.set_editor_property("destination_path", C.DEST)
        task.set_editor_property("destination_name", name)
        task.set_editor_property("automated", True)
        task.set_editor_property("replace_existing", True)
        task.set_editor_property("save", False)
        task.set_editor_property("factory", unreal.FbxFactory())
        task.set_editor_property("options", options())
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        paths = [str(p) for p in task.get_editor_property("imported_object_paths")]
        r["imported"] = paths
        meshes = [m for m in (unreal.load_asset(p) for p in paths) if isinstance(m, unreal.StaticMesh)]
        if meshes:
            ap = meshes[0].get_path_name().split(".")[0]
            m0 = meshes[0]
            r["light_map_coordinate_index_after_import"] = int(m0.get_editor_property("light_map_coordinate_index"))
            if r["light_map_coordinate_index_after_import"] != 1:
                m0.set_editor_property("light_map_coordinate_index", 1)
                r["light_map_coordinate_index_set"] = 1
            r["sidecar"] = C.safe(lambda: apply_sidecar(str(side), ap))
            r["final_save"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(m0))
    except Exception:  # noqa: BLE001
        r["error"] = traceback.format_exc()
    rep["meshes"][key] = r
(C.HERE / "pass1.json").write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
unreal.log("FBU_PASS1_DONE")
