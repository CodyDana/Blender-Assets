import bpy
arm = bpy.data.objects["root"]
act = bpy.data.actions["A_Fan_Openness"]
arm.animation_data.action = act
try:
    arm.animation_data.action_slot = act.slots[0]
except Exception as e: print("slot", e)
print("range", tuple(act.frame_range))
for f in (0, 30, 59, 60):
    bpy.context.scene.frame_set(f)
    print(f, [(pb.name, tuple(round(v, 4) for v in pb.rotation_quaternion)) for pb in arm.pose.bones if pb.name in ("stick_13", "leaf_24", "leaf_25")])
    b = arm.pose.bones["leaf_25"]
    print("   leaf_25 bone axis rest", tuple(round(v,4) for v in arm.data.bones["leaf_25"].matrix_local.col[1][:3]), "parent", b.parent.name)
