import sys
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts"); sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
import bpy, numpy as np
import verify_fan as V
from props_lib import fan_look as LK
EXP = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/build_dev/dev1/Exports/Fan/"
LK.reset_scene()
objs = V.import_fbx(EXP + "SK_Fan.fbx")
arm = next(o for o in objs if o.type == "ARMATURE")
acts = {}
for nm, fps in (("A_Fan_OpenPose", 60), ("A_Fan_Openness", 60)):
    bpy.context.scene.render.fps = fps
    o3 = V.import_fbx(EXP + nm + ".fbx")
    a3 = next(o for o in o3 if o.type == "ARMATURE")
    act = a3.animation_data.action
    act.name = nm
    acts[nm] = act
    print(nm, "frame_range", tuple(act.frame_range), "slots", [s.identifier for s in act.slots] if hasattr(act, "slots") else None)
    try:
        fcs = list(act.fcurves)
    except Exception:
        fcs = [fc for l in act.layers for st in l.strips for cb in st.channelbags for fc in cb.fcurves]
    paths = sorted(set(fc.data_path for fc in fcs))
    print("  fcurves", len(fcs), paths[:6])
    kp = [ (fc.data_path, [round(k.co[0],2) for k in fc.keyframe_points][:4], fc.keyframe_points[-1].co[0]) for fc in fcs[:3]]
    print("  keys", kp)
    for o in o3: bpy.data.objects.remove(o, do_unlink=True)
if arm.animation_data is None: arm.animation_data_create()
for nm, f in (("A_Fan_OpenPose", 0), ("A_Fan_Openness", 60)):
    arm.animation_data.action = acts[nm]
    try:
        arm.animation_data.action_slot = acts[nm].slots[0]
    except Exception as e:
        print("slot err", e)
    bpy.context.scene.frame_set(f)
    print(nm, f, [(pb.name, tuple(round(v, 4) for v in pb.rotation_quaternion), tuple(round(v, 5) for v in pb.location)) for pb in arm.pose.bones if pb.name in ("stick_12", "leaf_24", "leaf_25", "stick_00")])
