import sys, bpy, addon_utils
sys.path.insert(0, r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\fan\build_dev\exp")
sys.argv = sys.argv[:sys.argv.index("--") + 1]
import fbx_scale_probe as P
out = r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\fan\build_dev\exp\fbxscale"
import os; os.makedirs(out, exist_ok=True)
combos = {
  "none_unit": dict(apply_scale_options="FBX_SCALE_NONE", apply_unit_scale=True, global_scale=1.0),
  "units_unit": dict(apply_scale_options="FBX_SCALE_UNITS", apply_unit_scale=True, global_scale=1.0),
  "all_unit": dict(apply_scale_options="FBX_SCALE_ALL", apply_unit_scale=True, global_scale=1.0),
  "all_nounit_100": dict(apply_scale_options="FBX_SCALE_ALL", apply_unit_scale=False, global_scale=100.0),
  "custom_nounit_100": dict(apply_scale_options="FBX_SCALE_CUSTOM", apply_unit_scale=False, global_scale=100.0),
  "none_unit_bake": dict(apply_scale_options="FBX_SCALE_NONE", apply_unit_scale=True, global_scale=1.0, bake_space_transform=True),
}
arm = bpy.data.objects["root"]; me = bpy.data.objects["SK_Fan"]
for k, c in combos.items():
    bpy.ops.object.select_all(action="DESELECT"); arm.select_set(True); me.select_set(True)
    bpy.context.view_layer.objects.active = arm
    f = os.path.join(out, k + ".fbx")
    bpy.ops.export_scene.fbx(filepath=f, use_selection=True, object_types={"ARMATURE", "MESH"}, add_leaf_bones=False,
                             armature_nodetype="NULL", bake_anim=False, axis_forward="-Y", axis_up="Z", **c)
    print("RES", k, P.dump(f))
