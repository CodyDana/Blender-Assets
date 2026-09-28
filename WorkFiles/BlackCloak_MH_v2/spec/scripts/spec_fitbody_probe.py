import bpy
for o in bpy.data.objects:
    print("OBJ", o.name, o.type, o.data.name if o.data else None, len(o.data.vertices) if o.type=="MESH" else "", [m.type for m in o.modifiers], o.parent.name if o.parent else None, tuple(round(v,3) for v in o.dimensions))
for c in bpy.data.collections: print("COL", c.name, [o.name for o in c.objects])
print("SCENEPROPS", {k: bpy.context.scene[k] for k in bpy.context.scene.keys()})
arm = bpy.data.objects.get("root")
if arm:
    for n in ("pelvis","spine_01","spine_03","spine_05","neck_01","neck_02","head","clavicle_r","upperarm_r","lowerarm_r","hand_r","clavicle_l","upperarm_l","FACIAL_C_Nose","FACIAL_L_Eye","FACIAL_R_Eye","FACIAL_C_Jaw","foot_r","ball_r"):
        b = arm.data.bones.get(n)
        if b: print("BONE", n, tuple(round(v,4) for v in (arm.matrix_world @ b.head_local)), tuple(round(v,4) for v in (arm.matrix_world @ b.tail_local)))
    print("NBONES", len(arm.data.bones), [b.name for b in arm.data.bones if "Eye" in b.name or "eye" in b.name][:20])
