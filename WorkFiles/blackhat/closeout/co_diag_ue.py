"""Diagnostic only: import each diag FBX into a fresh path, bracketed by markers."""
import unreal, glob, os
D = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/blackhat/closeout/diag_tangent"
DEST = "/Game/PropsCheck/BlackHat_CO_diag_0926g"
for f in sorted(glob.glob(D + "/*.fbx")):
    n = os.path.splitext(os.path.basename(f))[0]
    ui = unreal.FbxImportUI()
    ui.set_editor_property("automated_import_should_detect_type", False)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
    ui.set_editor_property("import_materials", False); ui.set_editor_property("import_textures", False)
    sm = ui.get_editor_property("static_mesh_import_data")
    sm.set_editor_property("auto_generate_collision", False)
    sm.set_editor_property("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    sm.set_editor_property("normal_generation_method", unreal.FBXNormalGenerationMethod.MIKK_T_SPACE)
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", f); t.set_editor_property("destination_path", DEST)
    t.set_editor_property("automated", True); t.set_editor_property("save", False)
    t.set_editor_property("factory", unreal.FbxFactory()); t.set_editor_property("options", ui)
    unreal.log("DIAG_BEGIN " + n)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    unreal.log("DIAG_END " + n)
