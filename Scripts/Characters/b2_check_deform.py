"""b2_check_deform.py - PRIVATE / DO NOT SHIP. Independent deformation judge for step C1 (2B private bare rig).

  blender -b WorkFiles/Characters/2B_private/2B_private_rig.blend -P Scripts/Characters/b2_check_deform.py -- <mode> [pose ...]
  mode = numbers | render | both

Opens the rig blend read-only (NEVER saves it). Poses are built in world space on the A-pose rest.
Writes only to WorkFiles/Characters/2B_private/checks_c1/.
"""
import bpy, os, sys, json, math
import numpy as np
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

ROOT = r"C:/Users/Cody/Desktop/Blender_Projects"
OUT = ROOT + "/WorkFiles/Characters/2B_private/checks_c1"
ARM = None
LEFT = Vector((1, 0, 0)); FWD = Vector((0, -1, 0)); UP = Vector((0, 0, 1))


def log(*a):
    print("[chk]", *a, flush=True)


def argv():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def pb(n):
    return ARM.pose.bones[n]


def head(n):
    return ARM.matrix_world @ pb(n).head


def upd():
    bpy.context.view_layer.update()


def rot_world(n, R):
    p = pb(n)
    h = p.head.copy()
    p.matrix = Matrix.Translation(h) @ R.to_4x4() @ Matrix.Translation(-h) @ p.matrix
    upd()


def rot_axis(n, axis, deg):
    rot_world(n, Matrix.Rotation(math.radians(deg), 3, Vector(axis).normalized()))


def aim(n, child, direction):
    d0 = (head(child) - head(n)).normalized()
    rot_world(n, d0.rotation_difference(Vector(direction).normalized()).to_matrix())


def twist(n, child, deg):
    """Roll bone n about its own current long axis (toward child)."""
    rot_axis(n, (head(child) - head(n)).normalized(), deg)


def hand_axes(s):
    w = head(f"hand_{s}")
    mc = sum((head(f"{f}_01_{s}") for f in ("index", "middle", "ring", "pinky")), Vector()) / 4
    w1 = (mc - w).normalized()
    w2 = (head(f"index_01_{s}") - head(f"pinky_01_{s}")); w2 = (w2 - w1 * w2.dot(w1)).normalized()
    dorsal = (w2.cross(w1) if s == "l" else w1.cross(w2)).normalized()
    return w1, w2, dorsal


def curl(s, amounts, thumb=(30, 30, 30)):
    w1, w2, dorsal = hand_axes(s)
    for f in ("index", "middle", "ring", "pinky"):
        for k, deg in zip((1, 2, 3), amounts):
            n = f"{f}_0{k}_{s}"
            child = f"{f}_0{k + 1}_{s}" if k < 3 else None
            ax = w2.copy()
            tip = head(child) if child else head(n) + (head(n) - head(f"{f}_0{k - 1}_{s}"))
            v = tip - head(n)
            moved = Matrix.Rotation(math.radians(deg), 3, ax) @ v
            if (moved - v).dot(-dorsal) < 0:
                ax = -ax
            rot_axis(n, ax, deg)
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


def spread(s, degs=(-12, 0, 9, 18)):
    """Spread fingers in the palm plane (about the dorsal axis), index/middle/ring/pinky."""
    w1, w2, dorsal = hand_axes(s)
    for f, d in zip(("index", "middle", "ring", "pinky"), degs):
        n = f"{f}_01_{s}"
        v = head(f"{f}_02_{s}") - head(n)
        ax = dorsal.copy()
        moved = Matrix.Rotation(math.radians(abs(d)), 3, ax) @ v
        # positive d = toward pinky side (-w2)
        want = -w2 if d > 0 else w2
        if (moved - v).dot(want) < 0:
            ax = -ax
        if d:
            rot_axis(n, ax, abs(d))
    # thumb out
    v = head("thumb_02_" + s) - head("thumb_01_" + s)
    ax = dorsal.copy()
    moved = Matrix.Rotation(math.radians(20), 3, ax) @ v
    if (moved - v).dot(w2) < 0:
        ax = -ax
    rot_axis("thumb_01_" + s, ax, 20)


def floor_feet():
    upd()
    rest = min(ARM.data.bones[n].head_local.z for n in ("ball_l", "ball_r", "foot_l", "foot_r"))
    cur = min(head(n).z for n in ("ball_l", "ball_r", "foot_l", "foot_r"))
    p = pb("pelvis")
    p.matrix = Matrix.Translation((0, 0, rest - cur)) @ p.matrix
    upd()


def restore_world(n):
    upd()
    p = pb(n)
    p.matrix = Matrix.Translation(p.head) @ ARM.data.bones[n].matrix_local.to_3x3().to_4x4()
    upd()


def pose_reset():
    for p in ARM.pose.bones:
        p.matrix_basis = Matrix.Identity(4)
    upd()


# ---- poses (character faces -Y, her left = +X; about +X: negative swings a hanging limb forward, positive bends knee)
def p_sprint():
    rot_axis("pelvis", UP, 8)
    rot_axis("spine_01", LEFT, 14); rot_axis("spine_03", UP, -10); rot_axis("spine_05", UP, -6)
    rot_axis("thigh_l", LEFT, -75); rot_axis("calf_l", LEFT, 95); rot_axis("foot_l", LEFT, 10)
    rot_axis("thigh_r", LEFT, 35); rot_axis("calf_r", LEFT, 115); rot_axis("foot_r", LEFT, -35)
    # right arm forward (opposite left leg), left arm back, elbows ~95
    aim("upperarm_r", "lowerarm_r", Vector((-0.15, -0.75, -0.55)))
    aim("lowerarm_r", "hand_r", Vector((0.2, -0.45, 0.85)))
    aim("upperarm_l", "lowerarm_l", Vector((0.2, 0.8, -0.6)))
    aim("lowerarm_l", "hand_l", Vector((0.05, -0.35, -0.55)))
    curl("l", (55, 70, 40)); curl("r", (55, 70, 40))
    rot_axis("neck_01", LEFT, -8); rot_axis("head", LEFT, -6)
    floor_feet()


def p_jump_tuck():
    for s, sg in (("l", 1), ("r", -1)):
        rot_axis(f"thigh_{s}", LEFT, -112)
        rot_axis(f"thigh_{s}", UP, 10 * sg)
        rot_axis(f"calf_{s}", LEFT, 135)
        rot_axis(f"foot_{s}", LEFT, -30)
    rot_axis("spine_01", LEFT, 12); rot_axis("spine_02", LEFT, 10); rot_axis("spine_03", LEFT, 10)
    rot_axis("neck_01", LEFT, -10)
    for s, sg in (("l", 1), ("r", -1)):
        aim(f"upperarm_{s}", f"lowerarm_{s}", Vector((0.3 * sg, -0.7, -0.35)))
        aim(f"lowerarm_{s}", f"hand_{s}", Vector((-0.2 * sg, -0.6, -0.8)))
    curl("l", (50, 60, 35)); curl("r", (50, 60, 35))


def p_crouch_walk():
    rot_axis("thigh_l", LEFT, -95); rot_axis("thigh_l", UP, 8); rot_axis("calf_l", LEFT, 115); restore_world("foot_l")
    rot_axis("thigh_r", LEFT, -35); rot_axis("thigh_r", UP, -6); rot_axis("calf_r", LEFT, 120)
    restore_world("foot_r"); rot_axis("foot_r", LEFT, -35)
    rot_axis("spine_01", LEFT, 18); rot_axis("spine_02", LEFT, 10); rot_axis("spine_03", LEFT, 8)
    rot_axis("neck_01", LEFT, -18); rot_axis("head", LEFT, -10)
    for s, sg in (("l", 1), ("r", -1)):
        aim(f"upperarm_{s}", f"lowerarm_{s}", Vector((0.2 * sg, -0.35, -1)))
        aim(f"lowerarm_{s}", f"hand_{s}", Vector((0.0, -1, -0.2)))
    curl("l", (30, 40, 25)); curl("r", (30, 40, 25))
    floor_feet()


def p_sitting():
    for s, sg in (("l", 1), ("r", -1)):
        rot_axis(f"thigh_{s}", LEFT, -88)
        rot_axis(f"thigh_{s}", UP, 6 * sg)
        rot_axis(f"calf_{s}", LEFT, 92)
        restore_world(f"foot_{s}")
    rot_axis("spine_01", LEFT, -4); rot_axis("spine_04", LEFT, 6)
    for s, sg in (("l", 1), ("r", -1)):
        aim(f"upperarm_{s}", f"lowerarm_{s}", Vector((0.1 * sg, -0.25, -1)))
        aim(f"lowerarm_{s}", f"hand_{s}", Vector((0.05 * sg, -1, -0.15)))
    floor_feet()


def p_arms_crossed():
    aim("upperarm_l", "lowerarm_l", Vector((0.25, -0.55, -1)))
    aim("lowerarm_l", "hand_l", Vector((-1, -0.35, 0.18)))
    aim("upperarm_r", "lowerarm_r", Vector((-0.25, -0.75, -1)))
    aim("lowerarm_r", "hand_r", Vector((1, -0.5, 0.28)))


def p_reach_bend():
    for n in ("spine_01", "spine_02", "spine_03", "spine_04", "spine_05"):
        rot_axis(n, FWD, -6)
    rot_axis("clavicle_r", FWD, -22)
    aim("upperarm_r", "lowerarm_r", Vector((-0.35, 0.05, 1)))
    aim("lowerarm_r", "hand_r", Vector((-0.4, 0.05, 1)))
    aim("upperarm_l", "lowerarm_l", Vector((0.12, 0.0, -1)))
    aim("lowerarm_l", "hand_l", Vector((0.08, -0.05, -1)))
    rot_axis("head", FWD, 8)


def p_hands():
    # left: fist with forearm pronated 70 deg (candy-wrap test at the wrist); right: open spread palm + wrist bend
    for s, sg in (("l", 1), ("r", -1)):
        aim(f"upperarm_{s}", f"lowerarm_{s}", Vector((0.35 * sg, -0.3, -1)))
        aim(f"lowerarm_{s}", f"hand_{s}", Vector((0.25 * sg, -1, 0.15)))
    twist("hand_l", "middle_01_l", 70)
    curl("l", (88, 100, 65), (20, 35, 40))
    spread("r")
    w1, w2, dorsal = hand_axes("r")
    rot_axis("hand_r", w2, 30)   # wrist extension / flexion test
    twist("hand_r", "middle_01_r", -60)


def p_look_over_shoulder():
    for n, d in (("spine_02", 6), ("spine_03", 8), ("spine_04", 8), ("spine_05", 8)):
        rot_axis(n, UP, d)
    rot_axis("neck_01", UP, 20); rot_axis("neck_02", UP, 20); rot_axis("head", UP, 25)
    rot_axis("head", LEFT, -8)
    # thigh twist (candy-wrap at hip/thigh) and a slight knee bend
    twist("thigh_r", "calf_r", 35); rot_axis("calf_r", LEFT, 20); restore_world("foot_r")
    twist("lowerarm_l", "hand_l", -60)
    floor_feet()


def p_head_mild():
    # typical locomotion/look-at head motion: head only 15 deg yaw + 12 deg nod down, relative to the neck
    rot_axis("head", UP, 15); rot_axis("head", LEFT, 12)


def p_head_up():
    rot_axis("head", LEFT, -15); rot_axis("neck_02", LEFT, -5)


def p_walk():
    rot_axis("thigh_l", LEFT, -25); rot_axis("thigh_r", LEFT, 20); rot_axis("calf_r", LEFT, 28)
    rot_axis("foot_l", LEFT, 12); rot_axis("foot_r", LEFT, -12)
    rot_axis("upperarm_l", LEFT, 18); rot_axis("upperarm_r", LEFT, -18)
    rot_axis("lowerarm_r", LEFT, -22); rot_axis("lowerarm_l", LEFT, -10)
    rot_axis("spine_03", UP, -4); rot_axis("pelvis", UP, 4)
    floor_feet()


POSES = [("apose", lambda: None), ("apose_top", lambda: None), ("crouch_walk_top", p_crouch_walk), ("jump_tuck_top", p_jump_tuck), ("walk_top", p_walk), ("head_mild", p_head_mild), ("head_up", p_head_up), ("sprint", p_sprint), ("jump_tuck", p_jump_tuck), ("crouch_walk", p_crouch_walk),
         ("sitting", p_sitting), ("arms_crossed", p_arms_crossed), ("reach_bend", p_reach_bend), ("hands", p_hands),
         ("look_shoulder", p_look_over_shoulder)]

# closeups: (name, bone or (bone, bone2), direction, dist)
V = lambda x, y, z: Vector((x, y, z))
CLOSE = {
    "apose_top": [("top_front", "spine_05", V(0, -1, 0.2), 0.6), ("top_edge_r", "clavicle_r", V(-0.3, -1, 0.35), 0.4)],
    "crouch_walk_top": [("top_edge_r", "clavicle_r", V(-0.3, -1, 0.35), 0.4), ("top_edge_r_side", "clavicle_r", V(-1, -0.5, 0.3), 0.45)],
    "jump_tuck_top": [("top_edge_r", "clavicle_r", V(-0.3, -1, 0.35), 0.4), ("top_edge_l", "clavicle_l", V(0.3, -1, 0.35), 0.4)],
    "walk_top": [("top_edge_r", "clavicle_r", V(-0.3, -1, 0.35), 0.4), ("top_front", "spine_05", V(0, -1, 0.2), 0.6)],
    "head_mild": [("face", "head", V(0.1, -1, 0.05), 0.42), ("face_tq", "head", V(0.8, -0.8, 0.05), 0.42), ("face_rtq", "head", V(-0.8, -0.8, 0.0), 0.42)],
    "head_up": [("face", "head", V(0.1, -1, -0.1), 0.42), ("face_side", "head", V(1, -0.3, 0), 0.45)],
    "apose": [("feet_front", ("ball_l", "ball_r"), V(0, -1, 0.35), 0.75), ("feet_back", ("foot_l", "foot_r"), V(0, 1, 0.3), 0.8),
              ("feet_side_l", "foot_l", V(1, 0, 0.1), 0.55), ("feet_side_r", "foot_r", V(-1, 0, 0.1), 0.55),
              ("soles", ("foot_l", "foot_r"), V(0, 0.4, -1), 0.8),
              ("head_front", "head", V(0, -1, 0), 0.5), ("head_side", "head", V(1, 0, 0), 0.5),
              ("armpit_l", "upperarm_l", V(0.5, -1, -0.2), 0.5), ("back", "spine_03", V(0, 1, 0), 1.9)],
    "sprint": [("knee_l", "calf_l", V(1, -0.3, 0), 0.6), ("knee_r", "calf_r", V(-1, 0.3, 0), 0.6),
               ("hip_crotch", "pelvis", V(0.8, -1, 0.1), 0.8), ("elbow_r", "lowerarm_r", V(-1, -0.2, 0), 0.5),
               ("back_glute", "pelvis", V(0.4, 1, 0), 0.8)],
    "jump_tuck": [("hip_side", "pelvis", V(1, 0, 0), 0.9), ("knees_front", ("calf_l", "calf_r"), V(0, -1, 0.2), 0.8),
                  ("crotch_low", "pelvis", V(0, -1, -0.6), 0.7), ("back", "spine_02", V(0.3, 1, 0), 0.9)],
    "crouch_walk": [("knee_l", "calf_l", V(1, -0.2, 0.1), 0.6), ("knee_r_back", "calf_r", V(-0.6, 1, 0.2), 0.6),
                    ("hip_front", "pelvis", V(0, -1, 0.2), 0.8), ("glute", "pelvis", V(0.6, 1, 0), 0.8)],
    "sitting": [("lap", "pelvis", V(0, -1, 0.8), 0.9), ("hip_side", "pelvis", V(1, 0, 0), 0.9),
                ("knee_back", "calf_l", V(1, 0.6, -0.3), 0.6), ("glute_back", "pelvis", V(0, 1, -0.2), 0.8)],
    "arms_crossed": [("chest", "spine_05", V(0, -1, 0), 0.8), ("elbows", "spine_04", V(0.8, -1, 0), 0.9),
                     ("shoulder_l", "upperarm_l", V(1, 0.3, 0.3), 0.5)],
    "reach_bend": [("armpit_r", "upperarm_r", V(-1, -0.3, -0.2), 0.55), ("armpit_r_back", "upperarm_r", V(-0.7, 1, 0), 0.6),
                   ("waist_l", "spine_02", V(1, -0.4, 0), 0.8), ("top_front", "spine_05", V(0, -1, 0), 0.7)],
    "hands": [("fist_l", "hand_l", V(0.5, -1, 0.4), 0.3), ("fist_l_b", "hand_l", V(0.3, 0.6, 1), 0.3),
              ("wrist_l", ("lowerarm_l", "hand_l"), V(1, -0.2, 0.3), 0.45),
              ("open_r", "hand_r", V(-0.4, -1, 0.5), 0.35), ("open_r_b", "hand_r", V(-0.2, 0.3, 1), 0.35),
              ("wrist_r", ("lowerarm_r", "hand_r"), V(-1, -0.2, 0.3), 0.45)],
    "look_shoulder": [("head_neck", "neck_02", V(0.5, -1, 0.1), 0.5), ("face", "head", V(0.9, -0.5, 0.05), 0.45),
                      ("neck_back", "neck_01", V(-0.5, 1, 0.2), 0.5), ("thigh_r", "thigh_r", V(-0.6, -1, -0.2), 0.8),
                      ("forearm_l", "lowerarm_l", V(1, -0.5, 0.2), 0.5)],
}
FULL = {"apose_top": [], "crouch_walk_top": [], "jump_tuck_top": [], "walk_top": [], "head_mild": [], "head_up": [], "apose": ["front", "side", "back"], "sprint": ["front", "side", "tq"], "jump_tuck": ["front", "side"],
        "crouch_walk": ["front", "side", "tq"], "sitting": ["front", "side"], "arms_crossed": ["front", "tq"],
        "reach_bend": ["front", "back"], "hands": ["front"], "look_shoulder": ["front", "tq", "back"]}


def view_dir(view):
    ang = {"front": 0, "tq": 35, "side": 90, "back": 180, "rside": -90}[view]
    a = math.radians(ang)
    return Vector((math.sin(a), -math.cos(a), 0.0))


def look_at(cam, target, direction, dist):
    d = Vector(direction).normalized()
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    cam.location = Vector(target) + d * dist


def frame_camera(cam, center, direction, pts, margin=1.08):
    sc = bpy.context.scene
    d = Vector(direction).normalized()
    rot = (-d).to_track_quat('-Z', 'Y')
    cam.rotation_euler = rot.to_euler()
    R = rot.to_matrix()
    right = R @ Vector((1, 0, 0)); up = R @ Vector((0, 1, 0))
    cd = cam.data
    aspect = sc.render.resolution_x / sc.render.resolution_y
    fov_w = 2 * math.atan(cd.sensor_width / 2 / cd.lens)
    if aspect < 1:
        tan_v = math.tan(fov_w / 2); tan_h = tan_v * aspect
    else:
        tan_h = math.tan(fov_w / 2); tan_v = tan_h / aspect
    need = 0
    for p in pts:
        q = p - center
        x = q.dot(right); y = q.dot(up); z = q.dot(d)
        need = max(need, z + abs(x) * margin / tan_h, z + abs(y) * margin / tan_v)
    cam.location = center + d * need


def enable_gpu():
    prefs = bpy.context.preferences.addons['cycles'].preferences
    for t in ('OPTIX', 'CUDA'):
        try:
            prefs.compute_device_type = t
            prefs.get_devices()
            ok = False
            for d in prefs.devices:
                d.use = d.type != 'CPU'
                ok = ok or d.use
            if ok:
                bpy.context.scene.cycles.device = 'GPU'
                return t
        except Exception as e:  # noqa
            log("gpu", t, e)
    return 'CPU'


def render_to(path):
    sc = bpy.context.scene
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    log("rendered", os.path.basename(path))


# ---------------- numbers ----------------
def mesh_co(o, deformed=True):
    if deformed:
        dg = bpy.context.evaluated_depsgraph_get()
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
    else:
        me = o.data
    n = len(me.vertices)
    co = np.empty(n * 3, np.float32); me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    mw = np.array(o.matrix_world, np.float64)
    co = co @ mw[:3, :3].T + mw[:3, 3]
    if deformed:
        vn = np.empty(n * 3, np.float32); me.vertices.foreach_get("normal", vn)
        ev.to_mesh_clear()
        return co, vn.reshape(-1, 3)
    return co, None


def dom_bone(o):
    names = [g.name for g in o.vertex_groups]
    out = []
    for v in o.data.vertices:
        best = None; bw = -1
        for g in v.groups:
            if g.weight > bw:
                bw = g.weight; best = names[g.group]
        out.append(best)
    return out


def head_weight(o):
    gi = o.vertex_groups["head"].index if "head" in o.vertex_groups else -1
    w = np.zeros(len(o.data.vertices))
    for v in o.data.vertices:
        for g in v.groups:
            if g.group == gi:
                w[v.index] = g.weight
    return w


def poly_arrays(me):
    tris = []
    for p in me.polygons:
        vs = list(p.vertices)
        for k in range(1, len(vs) - 1):
            tris.append((vs[0], vs[k], vs[k + 1], p.index))
    return np.array(tris, np.int64)


def tri_area_normal(co, T):
    a = co[T[:, 0]]; b = co[T[:, 1]]; c = co[T[:, 2]]
    cr = np.cross(b - a, c - a)
    ar = np.linalg.norm(cr, axis=1) * 0.5
    return ar, cr / np.maximum(ar[:, None] * 2, 1e-12)


def main():
    global ARM
    a = argv()
    mode = a[0] if a else "both"
    only = set(a[1:])
    os.makedirs(OUT, exist_ok=True)
    ARM = bpy.data.objects["root"]
    sc = bpy.context.scene
    body = bpy.data.objects["SK_2B_Body"]; hp = bpy.data.objects["SK_2B_HeadParts"]; gar = bpy.data.objects["SK_2B_Garments"]
    meshes = [body, hp, gar]
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.name.startswith("RIG_") and o.name != "RIG_Floor":
            o.hide_render = True
    bpy.context.view_layer.objects.active = ARM
    bpy.ops.object.mode_set(mode='POSE')
    pose_reset()

    results = {}
    if mode in ("numbers", "both"):
        rest_b, _ = mesh_co(body, False)
        T = poly_arrays(body.data)
        ar0, n0 = tri_area_normal(rest_b, T)
        dom = dom_bone(body)
        dom_t = [dom[t[0]] for t in T]
        rest_hp, _ = mesh_co(hp, False)
        rest_g, _ = mesh_co(gar, False)
        g_mat = np.array([gar.data.polygons[0].material_index] * len(gar.data.vertices))
        for p in gar.data.polygons:
            for v in p.vertices:
                g_mat[v] = p.material_index
        gmat_names = [m.name for m in gar.data.materials]
        # eye centres from Sclera material of the head parts
        sid = [i for i, m in enumerate(hp.data.materials) if "Sclera" in m.name][0]
        sv = set()
        for p in hp.data.polygons:
            if p.material_index == sid:
                sv.update(p.vertices)
        sv = np.array(sorted(sv))
        eyeL = rest_hp[sv][rest_hp[sv][:, 0] > 0].mean(0); eyeR = rest_hp[sv][rest_hp[sv][:, 0] < 0].mean(0)
        lid_idx = np.where((np.linalg.norm(rest_b - eyeL, axis=1) < 0.02) | (np.linalg.norm(rest_b - eyeR, axis=1) < 0.02))[0]
        hw_body = head_weight(body); hw_hp = head_weight(hp)
        results["_static"] = {
            "eye_centres": [eyeL.round(4).tolist(), eyeR.round(4).tolist()],
            "eyelid_region_verts": int(len(lid_idx)),
            "eyelid_region_head_weight_min": float(hw_body[lid_idx].min()) if len(lid_idx) else None,
            "headparts_head_weight_min": float(hw_hp.min()), "headparts_head_weight_mean": float(hw_hp.mean()),
        }
        # body verts under garments at rest: nearest garment point, signed (garment normal)
        bvh_g0 = BVHTree.FromPolygons([tuple(v) for v in rest_g.tolist()], [tuple(p.vertices) for p in gar.data.polygons])
        under = []
        for i, c in enumerate(rest_b):
            loc, nrm, idx, d = bvh_g0.find_nearest(Vector(c), 0.012)
            if loc is not None and (Vector(c) - loc).dot(nrm) < 0:
                under.append(i)
        under = np.array(under)
        results["_static"]["body_verts_under_garment"] = int(len(under))
        # bandeau upper edge: left vs right height (front and back), 1 cm bins of |x|
        import bmesh
        tmi = [k for k, n in enumerate(gmat_names) if "Top" in n]
        if tmi:
            gbm = bmesh.new(); gbm.from_mesh(gar.data); gbm.verts.ensure_lookup_table()
            tv = {v for f in gbm.faces if f.material_index == tmi[0] for v in f.verts}
            tz = np.array([rest_g[v.index][2] for v in tv])
            ed = np.array([rest_g[v.index] for v in tv if v.is_boundary and rest_g[v.index][2] > np.median(tz)])
            ycen = float((min(rest_g[v.index][1] for v in tv) + max(rest_g[v.index][1] for v in tv)) / 2) if len(tv) else 0.0
            gbm.free()
            diffs = {}
            for part, m in (("front", ed[:, 1] < ycen), ("back", ed[:, 1] >= ycen)):
                e = ed[m]
                for b in np.arange(0.0, 0.14, 0.01):
                    L = e[(e[:, 0] >= b) & (e[:, 0] < b + 0.01)]; Rr = e[(-e[:, 0] >= b) & (-e[:, 0] < b + 0.01)]
                    if len(L) and len(Rr):
                        diffs[f"{part}_{int(round(b * 100))}cm"] = round(float(L[:, 2].max() - Rr[:, 2].max()) * 1000, 1)
            results["_static"]["top_upper_edge_L_minus_R_mm"] = diffs
            results["_static"]["top_upper_edge_max_abs_diff_mm"] = max((abs(x) for x in diffs.values()), default=None)

        # A-pose feet analysis
        left = rest_b[:, 0] > 0.03; right = rest_b[:, 0] < -0.03
        feetinfo = {}
        for s, m in (("l", left), ("r", right)):
            fv = rest_b[m & (rest_b[:, 2] < 0.12)]
            sole = fv[fv[:, 2] < fv[:, 2].min() + 0.006]
            feetinfo[s] = {"min_z": round(float(fv[:, 2].min()), 4), "len_y": round(float(fv[:, 1].max() - fv[:, 1].min()), 4),
                           "width_x": round(float(fv[:, 0].max() - fv[:, 0].min()), 4),
                           "sole_contact_y_range": [round(float(sole[:, 1].min()), 3), round(float(sole[:, 1].max()), 3)],
                           "heel_z": round(float(fv[fv[:, 1] > fv[:, 1].max() - 0.02][:, 2].min()), 4),
                           "toe_z": round(float(fv[fv[:, 1] < fv[:, 1].min() + 0.02][:, 2].min()), 4),
                           "n": int(len(fv))}
        # mirror similarity of feet
        fl = rest_b[left & (rest_b[:, 2] < 0.12)]; fr = rest_b[right & (rest_b[:, 2] < 0.12)]
        kd = KDTree(len(fr))
        for i, c in enumerate(fr):
            kd.insert(Vector(c), i)
        kd.balance()
        ds = np.array([kd.find(Vector((-c[0], c[1], c[2])))[2] for c in fl])
        feetinfo["mirror_dist_mm"] = {"mean": round(float(ds.mean() * 1000), 2), "p95": round(float(np.percentile(ds, 95) * 1000), 2),
                                      "max": round(float(ds.max() * 1000), 2)}
        # whole-body mirror asymmetry
        kdb = KDTree(len(rest_b))
        for i, c in enumerate(rest_b):
            kdb.insert(Vector(c), i)
        kdb.balance()
        samp = rest_b[::7]
        dsb = np.array([kdb.find(Vector((-c[0], c[1], c[2])))[2] for c in samp])
        results["_static"]["feet"] = feetinfo
        results["_static"]["body_mirror_asym_mm"] = {"mean": round(float(dsb.mean() * 1000), 2), "p99": round(float(np.percentile(dsb, 99) * 1000), 2),
                                                     "max": round(float(dsb.max() * 1000), 2)}
        # proportions vs MH (joint positions)
        J = {b.name: (ARM.matrix_world @ b.head_local) for b in ARM.data.bones}
        L = lambda x, y: round((J[x] - J[y]).length * 100, 1)
        tip = lambda f, s: ARM.matrix_world @ ARM.data.bones[f"{f}_03_{s}"].tail_local
        results["_static"]["lengths_cm"] = {
            "upperarm_l": L("upperarm_l", "lowerarm_l"), "lowerarm_l": L("lowerarm_l", "hand_l"),
            "upperarm_r": L("upperarm_r", "lowerarm_r"), "lowerarm_r": L("lowerarm_r", "hand_r"),
            "hand_to_middle_tip_l": round((tip("middle", "l") - J["hand_l"]).length * 100, 1),
            "thigh_l": L("thigh_l", "calf_l"), "calf_l": L("calf_l", "foot_l"), "thigh_r": L("thigh_r", "calf_r"), "calf_r": L("calf_r", "foot_r"),
            "shoulder_width_upperarm": L("upperarm_l", "upperarm_r"), "hip_width": L("thigh_l", "thigh_r"),
            "pelvis_z": round(J["pelvis"].z * 100, 1), "head_z": round(J["head"].z * 100, 1),
            "arm_angle_below_horizontal_l": round(math.degrees(math.atan2(-(J["lowerarm_l"] - J["upperarm_l"]).z,
                                                  math.hypot((J["lowerarm_l"] - J["upperarm_l"]).x, (J["lowerarm_l"] - J["upperarm_l"]).y))), 1),
            "arm_angle_below_horizontal_r": round(math.degrees(math.atan2(-(J["lowerarm_r"] - J["upperarm_r"]).z,
                                                  math.hypot((J["lowerarm_r"] - J["upperarm_r"]).x, (J["lowerarm_r"] - J["upperarm_r"]).y))), 1),
        }
        # mesh landmark: where is the elbow crease / wrist crease along the left arm? width profile along the arm axis
        ua = J["upperarm_l"]; ha = J["hand_l"]
        axis = (ha - ua); alen = axis.length; axis.normalize()
        armv = rest_b[(rest_b[:, 0] > 0.12)]
        rel = armv - np.array(ua)
        t = rel @ np.array(axis)
        perp = np.linalg.norm(rel - np.outer(t, np.array(axis)), axis=1)
        prof = []
        for k in np.arange(-0.02, alen + 0.12, 0.02):
            m = (t >= k) & (t < k + 0.02) & (perp < 0.07)
            prof.append([round(float(k * 100), 0), round(float(np.percentile(perp[m], 90) * 100), 2) if m.sum() > 5 else None, int(m.sum())])
        results["_static"]["left_arm_radius_profile_cm(t,r90,n)"] = prof
        results["_static"]["elbow_t_cm"] = round((J["lowerarm_l"] - ua).length * 100, 1)

        for name, fn in POSES:
            if only and name not in only:
                continue
            pose_reset(); fn(); upd()
            db, dn = mesh_co(body, True)
            ar1, n1 = tri_area_normal(db, T)
            ratio = ar1 / np.maximum(ar0, 1e-12)
            # fold: face normal vs mean vertex normal of its 3 verts
            vn = dn[T[:, 0]] + dn[T[:, 1]] + dn[T[:, 2]]
            fold = (np.einsum("ij,ij->i", n1, vn) < 0) & (ar0 > 1e-8)
            coll = ratio < 0.3; stre = ratio > 2.5
            def by_bone(mask):
                d = {}
                for i in np.where(mask)[0]:
                    d[dom_t[i]] = d.get(dom_t[i], 0) + 1
                return dict(sorted(d.items(), key=lambda kv: -kv[1])[:8])
            # edge stretch
            r = {"tri_collapse_lt0.3": int(coll.sum()), "collapse_by_bone": by_bone(coll),
                 "tri_stretch_gt2.5": int(stre.sum()), "stretch_by_bone": by_bone(stre),
                 "tri_folded": int(fold.sum()), "fold_by_bone": by_bone(fold),
                 "min_area_ratio": round(float(ratio[ar0 > 1e-8].min()), 3), "max_area_ratio": round(float(ratio.max()), 2)}
            # garment penetration: body verts that were inside garment at rest and are now outside by >0.5mm
            dg_, _ = mesh_co(gar, True)
            bvh_g = BVHTree.FromPolygons([tuple(v) for v in dg_.tolist()], [tuple(p.vertices) for p in gar.data.polygons])
            poke = []
            for i in under:
                c = Vector(db[i])
                loc, nrm, idx, d = bvh_g.find_nearest(c, 0.02)
                if loc is not None:
                    sd = (c - loc).dot(nrm)
                    if sd > 0.0005:
                        poke.append((i, sd, gar.data.polygons[idx].material_index))
            pk = {}
            for i, sd, mi in poke:
                key = gmat_names[mi] + ":" + str(dom[i])
                cur = pk.get(key, [0, 0.0]); cur[0] += 1; cur[1] = max(cur[1], sd * 1000); pk[key] = cur
            r["skin_through_garment_verts"] = len(poke)
            r["skin_through_by_region(count,max_mm)"] = {k: [v[0], round(v[1], 1)] for k, v in sorted(pk.items(), key=lambda kv: -kv[1][0])[:10]}
            # garment verts behind the skin (other direction)
            bvh_b = BVHTree.FromPolygons([tuple(v) for v in db.tolist()], [tuple(p.vertices) for p in body.data.polygons])
            behind = 0; bmax = 0; bb = {}
            for gi, c in enumerate(dg_):
                loc, nrm, idx, d = bvh_b.find_nearest(Vector(c), 0.01)
                if loc is not None:
                    sd = (Vector(c) - loc).dot(nrm)
                    if sd < -0.0005:
                        behind += 1; bmax = max(bmax, -sd)
                        k = gmat_names[g_mat[gi]]
                        bb[k] = bb.get(k, 0) + 1
            r["garment_verts_behind_skin"] = behind; r["garment_behind_max_mm"] = round(bmax * 1000, 1); r["garment_behind_by_mat"] = bb
            # head parts rigid follow
            Mh = ARM.matrix_world @ pb("head").matrix @ ARM.data.bones["head"].matrix_local.inverted() @ ARM.matrix_world.inverted()
            Mh = np.array(Mh)
            dh, _ = mesh_co(hp, True)
            exp = rest_hp @ Mh[:3, :3].T + Mh[:3, 3]
            dev = np.linalg.norm(dh - exp, axis=1)
            r["headparts_max_dev_from_head_mm"] = round(float(dev.max() * 1000), 2)
            expb = rest_b[lid_idx] @ Mh[:3, :3].T + Mh[:3, 3]
            devb = np.linalg.norm(db[lid_idx] - expb, axis=1)
            r["eyelid_region_max_dev_from_head_mm"] = round(float(devb.max() * 1000), 2) if len(lid_idx) else None
            # feet: lowest points
            r["foot_min_z_l"] = round(float(db[left][:, 2].min()), 4); r["foot_min_z_r"] = round(float(db[right][:, 2].min()), 4)
            results[name] = r
            log(name, json.dumps(r)[:600])
        with open(OUT + "/deform_numbers.json", "w") as fh:
            json.dump(results, fh, indent=1)

    if mode in ("render", "both"):
        enable_gpu()
        sc.render.engine = 'CYCLES'
        sc.cycles.samples = 40
        sc.cycles.use_denoising = True
        cam = sc.camera
        for name, fn in POSES:
            if only and name not in only:
                continue
            pose_reset(); fn(); upd()
            sc.render.resolution_x, sc.render.resolution_y = 800, 1100
            cam.data.lens = 70
            dg = bpy.context.evaluated_depsgraph_get()
            mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
            for o in meshes:
                ev = o.evaluated_get(dg); me = ev.to_mesh()
                for v in me.vertices:
                    c = o.matrix_world @ v.co
                    for k in range(3):
                        mn[k] = min(mn[k], c[k]); mx[k] = max(mx[k], c[k])
                ev.to_mesh_clear()
            pts = [Vector((x, y, z)) for x in (mn.x, mx.x) for y in (mn.y, mx.y) for z in (mn.z, mx.z)]
            for view in FULL.get(name, ["front", "side"]):
                frame_camera(cam, (mn + mx) / 2, view_dir(view), pts, 1.06)
                render_to(f"{OUT}/{name}_{view}.png")
            sc.render.resolution_x, sc.render.resolution_y = 900, 900
            cam.data.lens = 50
            for cn, bone, d, dist in CLOSE.get(name, []):
                if isinstance(bone, tuple):
                    c = (head(bone[0]) + head(bone[1])) / 2
                else:
                    c = head(bone)
                if cn.startswith("knee") and isinstance(bone, str):
                    pass
                look_at(cam, c, d, dist)
                render_to(f"{OUT}/{name}__{cn}.png")
        pose_reset()
    bpy.ops.object.mode_set(mode='OBJECT')
    log("DONE")


main()
