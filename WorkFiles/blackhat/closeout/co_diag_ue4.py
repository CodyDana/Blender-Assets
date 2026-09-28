"""Diagnostic only: pass1's exact FbxImportUI on the diag FBXs, bracketed by markers."""
import unreal, glob, os
D = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/blackhat/closeout/diag_tangent"
DEST = os.environ.get("CO_DIAG_DEST", "/Game/PropsCheck/BlackHat_CO_diag_0926i")
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
for f in sorted(glob.glob(D + "/*.fbx")):
    n = os.path.splitext(os.path.basename(f))[0]
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", f); t.set_editor_property("destination_path", DEST + "/" + n)
    t.set_editor_property("destination_name", "SM_BlackHat")
    t.set_editor_property("automated", True); t.set_editor_property("replace_existing", True)
    t.set_editor_property("replace_existing_settings", True); t.set_editor_property("save", False)
    t.set_editor_property("factory", unreal.FbxFactory()); t.set_editor_property("options", mesh_options())
    unreal.log("DIAG_BEGIN " + n)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    unreal.log("DIAG_END " + n)
