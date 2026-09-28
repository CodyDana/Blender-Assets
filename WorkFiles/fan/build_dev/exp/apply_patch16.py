p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/verify_fan.py"
s = open(p, encoding="utf-8").read()
def rep(old, new):
    global s
    assert old in s, old[:80]
    s = s.replace(old, new, 1)
rep('''        act.name = aname
        LK._linear(act)
        for o in o3:
            bpy.data.objects.remove(o, do_unlink=True)
        if arm.animation_data is None:
            arm.animation_data_create()
        arm.animation_data.action = act
        try:
            slot = act.slots[0] if hasattr(act, "slots") and len(act.slots) else None
            if slot is not None:
                arm.animation_data.action_slot = slot
        except Exception:
            pass
        f0, f1 = int(round(act.frame_range[0])), int(round(act.frame_range[1]))''', '''        act.name = aname
        LK._linear(act)
        # Unreal plays an FBX animation as each joint's local transform per key (its own reference pose plays
        # no part); an animation-only FBX carries no bind pose, so Blender's importer gives its armature a rest
        # pose of its own.  So: play the IMPORTED armature and copy each bone's armature-space pose onto the
        # SK_Fan armature (the skin under test), frame by frame
        for o in o3:
            if o is not a3:
                bpy.data.objects.remove(o, do_unlink=True)
        a3.hide_render = True
        players[aname] = a3
        f0, f1 = int(round(act.frame_range[0])), int(round(act.frame_range[1]))''')
rep('''        for k, (f, sub) in enumerate(times[::step]):
            bpy.context.scene.frame_set(f, subframe=sub)
            Q = world_positions(mesh)''', '''        for k, (f, sub) in enumerate(times[::step]):
            bpy.context.scene.frame_set(f, subframe=sub)
            copy_pose(a3, arm, rest)
            Q = world_positions(mesh)''')
rep('''    results = {}
    for aname in ("A_Fan_Openness", "A_Fan_OpenClose", "A_Fan_OpenPose"):''', '''    results = {}
    players = {}
    rest = LK.rest_matrices(arm)
    for aname in ("A_Fan_Openness", "A_Fan_OpenClose", "A_Fan_OpenPose"):''')
rep('''def world_positions(obj):''', '''def copy_pose(src_arm, dst_arm, dst_rest):
    """dst bones take src bones' armature-space pose matrices (both armatures at the identity)."""
    T = {}
    for pb in src_arm.pose.bones:
        M = np.array(pb.matrix)
        R = dst_rest[pb.name]
        Tm = M @ np.linalg.inv(R)
        Tm[:3, 3] /= LK.MM
        T[pb.name] = Tm
    LK.pose(dst_arm, T, dst_rest)


def world_positions(obj):''')
# fold sheet: play A_Fan_Openness through its player
rep('''    arm.animation_data.action = bpy.data.actions.get("A_Fan_Openness")
    fps = next(x["fps"] for x in sidecar["animations"] if x["file"] == "A_Fan_Openness.fbx")
    n_frames = next(x["frames"] for x in sidecar["animations"] if x["file"] == "A_Fan_Openness.fbx")[1]

    def pose_at(opening_deg):
        s = spec.s_for_opening(max(opening_deg, spec.front_hinge_deg))
        fr = s * n_frames
        f = int(math.floor(fr))
        bpy.context.scene.frame_set(f, subframe=fr - f)''', '''    player = players["A_Fan_Openness"]
    pact = player.animation_data.action
    pf0, pf1 = pact.frame_range
    bpy.context.scene.render.fps = next(x["fps"] for x in sidecar["animations"] if x["file"] == "A_Fan_Openness.fbx")

    def pose_at(opening_deg):
        s = spec.s_for_opening(max(opening_deg, spec.front_hinge_deg))
        fr = pf0 + s * (pf1 - pf0)
        f = int(math.floor(fr))
        bpy.context.scene.frame_set(f, subframe=fr - f)
        copy_pose(player, arm, rest)''')
open(p, "w", encoding="utf-8").write(s)
print("ok")
