"""Diagnostic (fresh commandlet, -nullrhi): import each tanexp/*.fbx (single-mesh LODs, shipped vs tangent-safe) with
pass A's static settings; NOTHING is saved. The log carries Unreal's tangent warnings per mesh name."""
import sys
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import unreal  # noqa: E402
import ar_common as C  # noqa: E402
import importlib.util
spec = importlib.util.spec_from_file_location("arA", str(C.HERE / "arA_import.py"))
unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")


def static_ui():
    ui = unreal.FbxImportUI()
    ui.set_editor_property("automated_import_should_detect_type", False)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    sm = ui.get_editor_property("static_mesh_import_data")
    sm.set_editor_property("import_mesh_lods", True)
    sm.set_editor_property("auto_generate_collision", False)
    sm.set_editor_property("combine_meshes", False)
    sm.set_editor_property("generate_lightmap_u_vs", True)
    sm.set_editor_property("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    sm.set_editor_property("normal_generation_method", unreal.FBXNormalGenerationMethod.MIKK_T_SPACE)
    sm.set_editor_property("convert_scene", True)
    sm.set_editor_property("convert_scene_unit", True)
    sm.set_editor_property("force_front_x_axis", False)
    return ui


for f in sorted((C.HERE / "tanexp").glob("*.fbx")):
    unreal.log(f"AR_TAN_BEGIN {f.stem}")
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", str(f))
    t.set_editor_property("destination_path", "/Game/GunCheck/AR01_tantest")
    t.set_editor_property("destination_name", f.stem)
    t.set_editor_property("automated", True)
    t.set_editor_property("save", False)
    t.set_editor_property("replace_existing", True)
    t.set_editor_property("options", static_ui())
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    m = unreal.load_asset(f"/Game/GunCheck/AR01_tantest/{f.stem}")
    if m is not None and True:
        o = unreal.FbxExportOption()
        o.set_editor_property("ascii", True)
        o.set_editor_property("level_of_detail", False)
        o.set_editor_property("collision", False)
        e = unreal.AssetExportTask()
        e.set_editor_property("object", m)
        e.set_editor_property("filename", str(C.HERE / "tanexp_ue" / f"ue_{f.stem}.fbx"))
        e.set_editor_property("automated", True)
        e.set_editor_property("prompt", False)
        e.set_editor_property("exporter", unreal.StaticMeshExporterFBX())
        e.set_editor_property("options", o)
        unreal.Exporter.run_asset_export_task(e)
    if m is not None:
        unreal.log(f"AR_TAN_TRIS {f.stem} {m.get_num_triangles(0)}")
    unreal.log(f"AR_TAN_END {f.stem}")
unreal.log("AR_TAN_DONE")
