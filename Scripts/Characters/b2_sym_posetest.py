"""b2_sym_posetest.py - PRIVATE / DO NOT SHIP. Symmetry step: copy of b2_rig_posetest.py (step C1 deformation test poses,
never saved as actions), unchanged logic; the default output folder is sym_renders/poses (always pass an absolute one).

  blender -b WorkFiles/Characters/2B_private/2B_private_rig_sym.blend -P Scripts/Characters/b2_sym_posetest.py -- <abs out_dir> [pose ...]

Poses are built in world space on top of the A-pose rest (aim a bone at a world direction, or rotate it about a world
axis through its head), parents first. Renders front + side at 800x1100 (Cycles GPU) of every pose into the given folder.
The blend is never saved.
"""
import bpy, os, sys, json, math
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from b2_rig_common import *  # noqa

ARM = None


def pb(n):
    return ARM.pose.bones[n]


def head(n):
    return ARM.matrix_world @ pb(n).head


def upd():
    bpy.context.view_layer.update()


def rot_world(n, R):
    """Rotate pose bone n by world rotation R (3x3) about its current head."""
    p = pb(n)
    h = p.head.copy()
    M = Matrix.Translation(h) @ R.to_4x4() @ Matrix.Translation(-h)
    p.matrix = M @ p.matrix
    upd()


def rot_axis(n, axis, deg):
    rot_world(n, Matrix.Rotation(math.radians(deg), 3, Vector(axis).normalized()))


def aim(n, child, direction, amount=1.0):
    d0 = (head(child) - head(n)).normalized()
    q = d0.rotation_difference(Vector(direction).normalized())
    if amount != 1.0:
        q = Quaternion_slerp(q, amount)
    rot_world(n, q.to_matrix())


def Quaternion_slerp(q, t):
    from mathutils import Quaternion
    return Quaternion().slerp(q, t)


def hand_axes(s):
    w = head(f"hand_{s}")
    mc = sum((head(f"{f}_01_{s}") for f in ("index", "middle", "ring", "pinky")), Vector()) / 4
    w1 = (mc - w).normalized()
    w2 = (head(f"index_01_{s}") - head(f"pinky_01_{s}")); w2 = (w2 - w1 * w2.dot(w1)).normalized()
    dorsal = (w2.cross(w1) if s == "l" else w1.cross(w2)).normalized()
    return w1, w2, dorsal


def curl(s, amounts, thumb=(30, 30, 30)):
    """Curl the fingers towards the palm: amounts = (mcp, pip, dip) degrees."""
    w1, w2, dorsal = hand_axes(s)
    for f in ("index", "middle", "ring", "pinky"):
        for k, deg in zip((1, 2, 3), amounts):
            n = f"{f}_0{k}_{s}"
            child = f"{f}_0{k + 1}_{s}" if k < 3 else None
            # hinge axis: across the hand; sign chosen so the finger moves to the palm side
            ax = w2.copy()
            tip = head(child) if child else head(n) + (head(n) - head(f"{f}_0{k - 1}_{s}"))
            v = tip - head(n)
            moved = Matrix.Rotation(math.radians(deg), 3, ax) @ v
            if (moved - v).dot(-dorsal) < 0:
                ax = -ax
            rot_axis(n, ax, deg)
    # thumb: fold across the palm
    for k, deg in zip((1, 2, 3), thumb):
        n = f"thumb_0{k}_{s}"
        child = f"thumb_0{k + 1}_{s}" if k < 3 else None
        tip = head(child) if child else head(n) + (head(n) - head(f"thumb_0{k - 1}_{s}"))
        v = tip - head(n)
        ax = v.cross(-dorsal).normalized()
        mc = sum((head(f"{f}_01_{s}") for f in ("index", "middle", "ring", "pinky")), Vector()) / 4
        pc = (head(f"hand_{s}") + mc) / 2 - dorsal * 0.015
        moved = head(n) + Matrix.Rotation(math.radians(deg), 3, ax) @ v
        if (moved - pc).length > (tip - pc).length:
            ax = -ax
        rot_axis(n, ax, deg)


def floor_feet():
    """Translate the pelvis so the lowest foot/ball joint is at its rest height."""
    upd()
    rest = min(ARM.data.bones[n].head_local.z for n in ("ball_l", "ball_r", "foot_l", "foot_r"))
    cur = min(head(n).z for n in ("ball_l", "ball_r", "foot_l", "foot_r"))
    p = pb("pelvis")
    M = Matrix.Translation((0, 0, rest - cur))
    p.matrix = M @ p.matrix
    upd()


def pose_reset():
    for p in ARM.pose.bones:
        p.matrix_basis = Matrix.Identity(4)
    upd()


LEFT = Vector((1, 0, 0)); FWD = Vector((0, -1, 0)); UP = Vector((0, 0, 1))


def restore_world(n):
    """Give bone n back its rest world orientation (keeps its current head): feet flat on the floor."""
    upd()
    p = pb(n)
    rest = ARM.data.bones[n].matrix_local
    p.matrix = Matrix.Translation(p.head) @ rest.to_3x3().to_4x4()
    upd()


# sign conventions (world axes, character faces -Y): about +X, negative = swing a hanging limb FORWARD,
# positive = knee bend / spine flexion forward / toes up
def pose_walk():
    rot_axis("thigh_l", LEFT, -25); rot_axis("thigh_r", LEFT, 20); rot_axis("calf_r", LEFT, 28)
    rot_axis("foot_l", LEFT, 12); rot_axis("foot_r", LEFT, -12)
    rot_axis("upperarm_l", LEFT, 18); rot_axis("upperarm_r", LEFT, -18)
    rot_axis("lowerarm_r", LEFT, -22); rot_axis("lowerarm_l", LEFT, -10)
    rot_axis("spine_03", UP, -4); rot_axis("pelvis", UP, 4)
    floor_feet()


def pose_run():
    rot_axis("spine_01", LEFT, 8)
    rot_axis("thigh_l", LEFT, -55); rot_axis("calf_l", LEFT, 70)
    rot_axis("thigh_r", LEFT, 30); rot_axis("calf_r", LEFT, 85); rot_axis("foot_r", LEFT, -20)
    for s, sg in (("l", 1), ("r", -1)):
        aim(f"upperarm_{s}", f"lowerarm_{s}", Vector((0.25 * (1 if s == "l" else -1), 0.55 * sg, -0.8)))
        rot_axis(f"lowerarm_{s}", LEFT, -80)
    curl("l", (40, 50, 30)); curl("r", (40, 50, 30))
    floor_feet()


def pose_squat():
    for s in ("l", "r"):
        rot_axis(f"thigh_{s}", LEFT, -100)
        rot_axis(f"thigh_{s}", UP, 18 if s == "l" else -18)
        rot_axis(f"calf_{s}", LEFT, 125)
        restore_world(f"foot_{s}")
    rot_axis("spine_01", LEFT, 12); rot_axis("spine_03", LEFT, 12); rot_axis("spine_05", LEFT, 8)
    for s in ("l", "r"):
        aim(f"upperarm_{s}", f"lowerarm_{s}", Vector((0.15 * (1 if s == "l" else -1), -1, -0.2)))
        aim(f"lowerarm_{s}", f"hand_{s}", Vector((0.0, -1, 0.0)))
    floor_feet()


def pose_arms_up():
    for s, sg in (("l", 1), ("r", -1)):
        rot_axis(f"clavicle_{s}", FWD, 18 * sg)
        aim(f"upperarm_{s}", f"lowerarm_{s}", Vector((0.12 * sg, 0.05, 1)))
        aim(f"lowerarm_{s}", f"hand_{s}", Vector((0.05 * sg, 0.05, 1)))


def pose_arms_forward():
    for s, sg in (("l", 1), ("r", -1)):
        aim(f"upperarm_{s}", f"lowerarm_{s}", Vector((0.12 * sg, -1, 0)))
        aim(f"lowerarm_{s}", f"hand_{s}", Vector((0.05 * sg, -1, 0)))


def pose_tpose():
    for s, sg in (("l", 1), ("r", -1)):
        aim(f"upperarm_{s}", f"lowerarm_{s}", Vector((sg, 0, 0)))
        aim(f"lowerarm_{s}", f"hand_{s}", Vector((sg, 0, 0)))
        aim(f"hand_{s}", f"middle_01_{s}", Vector((sg, 0, 0)))


def pose_twist():
    for n, d in (("spine_01", 7), ("spine_02", 9), ("spine_03", 10), ("spine_04", 10), ("spine_05", 9)):
        rot_axis(n, UP, d)


def pose_head_turn():
    rot_axis("neck_01", UP, 15); rot_axis("neck_02", UP, 18); rot_axis("head", UP, 27)


def pose_fist():
    for s, sg in (("l", 1), ("r", -1)):
        aim(f"lowerarm_{s}", f"hand_{s}", Vector((0.35 * sg, -1, 0.1)))
    curl("l", (85, 100, 60), (20, 35, 40)); curl("r", (85, 100, 60), (20, 35, 40))


POSES = [("apose", lambda: None), ("walk", pose_walk), ("run", pose_run), ("squat", pose_squat), ("arms_up", pose_arms_up),
         ("arms_forward", pose_arms_forward), ("tpose", pose_tpose), ("twist45", pose_twist),
         ("head_turn60", pose_head_turn), ("fist", pose_fist)]


def main():
    global ARM
    a = argv()
    out = a[0] if a else OUT + "/sym_renders/poses"
    assert os.path.isabs(out), out
    only = set(a[1:])
    os.makedirs(out, exist_ok=True)
    ARM = bpy.data.objects["root"]
    sc = bpy.context.scene
    enable_gpu()
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 48
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = 800, 1100
    cam = sc.camera
    meshes = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith("SK_")]
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.name.startswith("RIG_") and o.name != "RIG_Floor":
            o.hide_render = True
    bpy.context.view_layer.objects.active = ARM
    bpy.ops.object.mode_set(mode='POSE')
    done = []
    for name, fn in POSES:
        if only and name not in only:
            continue
        pose_reset()
        fn()
        upd()
        mn, mx = world_bbox(meshes)
        pts = [Vector((x, y, z)) for x in (mn.x, mx.x) for y in (mn.y, mx.y) for z in (mn.z, mx.z)]
        for view in ("front", "side"):
            if name == "fist" and view == "side":
                view_ = "tq"
            else:
                view_ = view
            frame_camera(cam, (mn + mx) / 2, view_dir(view_), pts, 1.08)
            path = f"{out}/{name}_{view}.png"
            render_to(path)
            done.append(path)
        if name == "fist":
            for s in ("l", "r"):
                c = head(f"hand_{s}").lerp(head(f"middle_02_{s}"), 0.6)
                w1, w2, dorsal = hand_axes(s)
                d = (-w2 * 0.6 + Vector((0, 0, 0.35)) + dorsal * 0.5).normalized()
                look_at(cam, c, d, 0.36)
                path = f"{out}/fist_close_{s}.png"; render_to(path); done.append(path)
    pose_reset()
    bpy.ops.object.mode_set(mode='OBJECT')
    save_json(out + "/_poses.json", {"renders": done})


main()
