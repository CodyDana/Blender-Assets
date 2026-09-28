import sys, json
sys.path.insert(0, r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\fan\UnrealCheck")
import unreal
from fan_ue_common import component_space_ref
AT = unreal.AssetToolsHelpers.get_asset_tools()
DEST = "/Game/FanCheck/Probe3b"
ui = unreal.FbxImportUI()
ui.set_editor_property("automated_import_should_detect_type", False)
ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH)
ui.set_editor_property("import_as_skeletal", True)
ui.set_editor_property("import_mesh", True)
ui.set_editor_property("create_physics_asset", False)
ui.set_editor_property("import_materials", False)
ui.set_editor_property("import_textures", False)
ui.set_editor_property("import_animations", False)
d = ui.get_editor_property("skeletal_mesh_import_data")
d.set_editor_property("convert_scene", True); d.set_editor_property("convert_scene_unit", True); d.set_editor_property("force_front_x_axis", False)
task = unreal.AssetImportTask()
task.set_editor_property("filename", r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/build_dev/dev1/Exports/Fan/SK_Fan.fbx")
task.set_editor_property("destination_path", DEST); task.set_editor_property("destination_name", "SK_Fan")
task.set_editor_property("automated", True); task.set_editor_property("save", False); task.set_editor_property("replace_existing", True)
task.set_editor_property("options", ui)
AT.import_asset_tasks([task])
mesh = unreal.load_asset(DEST + "/SK_Fan")
world, parent, local = component_space_ref(mesh)
out = {}
for n in ["root", "pivot", "stick_00", "stick_12", "leaf_00", "leaf_25"]:
    if n in local:
        l, w = local[n], world[n]
        out[n] = {"local_t": [l.translation.x, l.translation.y, l.translation.z], "local_s": [l.scale3d.x, l.scale3d.y, l.scale3d.z],
                  "local_r": [l.rotation.x, l.rotation.y, l.rotation.z, l.rotation.w],
                  "cs_t": [w.translation.x, w.translation.y, w.translation.z], "cs_s": [w.scale3d.x, w.scale3d.y, w.scale3d.z], "parent": parent[n]}
b = mesh.get_bounds()
out["bounds"] = {"origin": [b.origin.x, b.origin.y, b.origin.z], "extent": [b.box_extent.x, b.box_extent.y, b.box_extent.z]}
out["bone_count"] = len(local)
open(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/UnrealCheck/probe3.json", "w").write(json.dumps(out, indent=1))
unreal.log("PROBE_DONE")
