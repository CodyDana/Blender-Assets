"""Diagnostic: SM_AR01 / SM_AR01_Mag imported (not saved) with the pass-A settings at several minimum lightmap
resolutions; Unreal's FBX export of each for the UV1 overlap count."""
import sys
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import unreal
import ar_common as C
import importlib.util
spec = importlib.util.spec_from_file_location("arA", str(C.HERE / "arA_import.py"))
unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")


def ui():
    u = unreal.FbxImportUI()
    u.set_editor_property("automated_import_should_detect_type", False)
    u.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
    u.set_editor_property("import_materials", False)
    u.set_editor_property("import_textures", False)
    sm = u.get_editor_property("static_mesh_import_data")
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
    return u


s = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem) or unreal.new_object(unreal.StaticMeshEditorSubsystem)
for name in ("SM_AR01", "SM_AR01_Mag"):
    for r in (1, 2):   # 1 = generate from the authored UV1, 2 = no generation: the authored UV1 as is
        t = unreal.AssetImportTask()
        t.set_editor_property("filename", str(C.EXP / f"{name}.fbx"))
        t.set_editor_property("destination_path", "/Game/GunCheck/AR01_lmtest")
        t.set_editor_property("destination_name", f"{name}_{r}")
        t.set_editor_property("automated", True)
        t.set_editor_property("save", False)
        t.set_editor_property("replace_existing", True)
        t.set_editor_property("options", ui())
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
        m = unreal.load_asset(f"/Game/GunCheck/AR01_lmtest/{name}_{r}")
        for i in range(m.get_num_lods()):
            b = s.get_lod_build_settings(m, i)
            b.set_editor_property("generate_lightmap_u_vs", r == 1)
            b.set_editor_property("src_lightmap_index", 1)
            b.set_editor_property("dst_lightmap_index", 1)
            b.set_editor_property("min_lightmap_resolution", 64)
            b.set_editor_property("use_full_precision_u_vs", False)
            s.set_lod_build_settings(m, i, b)
        m.set_editor_property("light_map_resolution", 64)
        m.set_editor_property("light_map_coordinate_index", 1)
        o = unreal.FbxExportOption()
        o.set_editor_property("collision", False)
        o.set_editor_property("level_of_detail", True)
        e = unreal.AssetExportTask()
        e.set_editor_property("object", m)
        e.set_editor_property("filename", str(C.HERE / "lmtest" / f"ue_{name}_{r}.fbx"))
        e.set_editor_property("automated", True)
        e.set_editor_property("prompt", False)
        e.set_editor_property("exporter", unreal.StaticMeshExporterFBX())
        e.set_editor_property("options", o)
        unreal.Exporter.run_asset_export_task(e)
unreal.log("AR_LM_DONE")
