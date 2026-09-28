import bpy
for o in bpy.data.objects:
    extra = ""
    if o.type == 'MESH':
        extra = "v=%d mats=%s mods=%s parent=%s" % (len(o.data.vertices), [m.name for m in o.data.materials if m], [m.type for m in o.modifiers], o.parent.name if o.parent else None)
    print("OBJ", o.name, o.type, extra)
for o in bpy.data.objects:
    if o.type == 'ARMATURE':
        print("ARM", o.name, o.data.pose_position, [ (b.name, tuple(round(x,1) for x in b.rotation_euler)) for b in o.pose.bones if 'arm' in b.name and b.rotation_mode!='QUATERNION'][:4], [(b.name, tuple(round(x,3) for x in b.rotation_quaternion)) for b in o.pose.bones if b.name in ('upperarm_l','lowerarm_l')])
