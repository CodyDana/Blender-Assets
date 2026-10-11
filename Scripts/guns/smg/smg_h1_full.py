"""SMG01 gate H1 FULL (SMG_BUILD_PLAN 14.2, W3; GUN_BUILDING_STUDY 7.2 H1): the SMG in MH_PlayerDefault's right hand.

    blender -b References/Characters/MH_PlayerDefault/MH_PlayerDefault_FitBody.blend --factory-startup \
        --python Scripts/guns/smg/smg_h1_full.py

Method (Blender only; the locked fit body and its metahuman_base_skel; nothing of the body is saved):
1. the hand frame from the rest skeleton: the knuckle line (index_01 -> pinky_01 heads) = the grip axis (down), the
   palm normal = the side the curled fingers move to (each finger's flexion axis is its bones' shared local Z) = the
   gun's +Y (the right palm presses toward the gun's left); along the axis the palm centre (wrist / knuckle midpoint)
   sits on the Grip origin (the early H1's 46 mm rule);
2. the SMG's LOD0 parts (Assets/Guns/SMG01.blend, frame B) seated in the opened hand: pushed toward the palm until the
   metacarpals' skin is 0.3 mm off the grip and back into the thenar / wrist until 0.3 mm off the back strap; the seat
   is the highest along the grip (from 24 mm above the palm-centre rule down) whose index knuckle clears the 62 mm
   wide trigger housing (the MCP under its bottom edge) and whose open fingers clear every part; the early H1's
   web-in-the-hollow seat is tried too and kept if it brings the pad nearer;
3. the class grip pose: middle, ring and pinky flex joint by joint (01 -> 02 -> 03 about each bone's local Z, the
   anatomical sign) until every vertex the joint drags is 0.5 mm off the gun; the thumb's metacarpal turns clear of
   the grip (grid about its local X / Z), its 02 / 03 flex to contact; the trigger finger's knuckle flexion and
   abduction and its middle joint are searched for the pad closest to the trigger's FRONT face with the finger clear
   of the frame (the rest curl); skin by linear blend skinning of the body's hand vertices;
4. gates: palm-to-grip penetration <= 1 mm; the index pad within +-3 mm of the trigger face (the Trigger socket) at
   the rest curl; 0 hand-gun intersections (triangle pairs between the hand skin and every part) at rest and at the
   clip extremes (bolt and charging handle back, trigger pulled, selector SAFE / AUTO, paddle pressed, magazine out,
   stock folded, sights folded); the left hand's two-bone IK to SupportHand with the gun at the cheek weld (Sight line
   through the right eye at 90 mm, bore level, facing the body's front) converges (< 0.5 mm) with the elbows inside
   0..150 deg, the right arm's IK to the held grip likewise;
5. records hand_offset: the Grip frame in the hand_r bone's frame (mm, quaternion), the class grip pose (finger
   rotations, deg) for gun_standard.json, and the cheek-weld assumptions.
Writes WorkFiles/guns/smg/scratch/h1_full.json and review/h1/h1_hold_*.png.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from smg_common import ROOT, BLEND, SCRATCH, REVIEW, SPEC, PARTS_COLL, GRIP, D  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Quaternion, Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

import smg_clips as CL  # noqa: E402

OUTD = REVIEW / "h1"
OUTD.mkdir(parents=True, exist_ok=True)
LOCK = json.loads((ROOT / "References" / "Characters" / "MH_PlayerDefault" / "base_lock.json").read_text())
CONTACT = 0.3          # mm: the palm / web skin's gap to the grip after the push
CURL_STOP = 0.5        # mm: a finger segment stops this close to the gun
EYE_OFFSET = np.array([-32.0, -95.0, 85.0])    # right eye from the 'head' joint (mm, world: -X right, -Y front)
EYE_RELIEF = 90.0      # mm behind the aperture (the cheek weld, B4b)


def log(*a):
    print("[H1F]", *a, flush=True)


arm = bpy.data.objects["root"]
body = bpy.data.objects["FIT_MH_PlayerDefault_Body"]
Mw = np.array(arm.matrix_world)


def bone_head(n):
    return (Mw @ np.r_[np.array(arm.data.bones[n].head_local), 1.0])[:3] * 1000.0


def bone_tail(n):
    return (Mw @ np.r_[np.array(arm.data.bones[n].tail_local), 1.0])[:3] * 1000.0


# ------------------------------------------------------------------------------------------------ hand skin (LBS)
hand_bones = {"hand_r"} | {b.name for b in arm.data.bones["hand_r"].children_recursive}
gi = {g.index: g.name for g in body.vertex_groups}
me = body.data
Vrest = np.array([v.co for v in me.vertices]) * 1000.0
HV = []
W = {}
for v in me.vertices:
    gs = [(gi[g.group], g.weight) for g in v.groups if g.weight > 0 and g.group in gi]
    if gs and max(gs, key=lambda t: t[1])[0] in hand_bones:
        HV.append(v.index)
HV = np.array(HV)
HVset = set(HV.tolist())
bone_names = sorted({gi[g.group] for i in HV for g in me.vertices[i].groups if g.group in gi and g.weight > 0})
bidx = {b: k for k, b in enumerate(bone_names)}
Wm = np.zeros((len(HV), len(bone_names)))
for r, i in enumerate(HV):
    for g in me.vertices[i].groups:
        if g.group in gi and g.weight > 0 and gi[g.group] in bidx:
            Wm[r, bidx[gi[g.group]]] += g.weight
Wm /= np.maximum(Wm.sum(1, keepdims=True), 1e-9)
VH = Vrest[HV]
main_bone = np.array([bone_names[k] for k in Wm.argmax(1)])
HT = np.array([p.vertices[:] for p in me.polygons if len(p.vertices) == 3 and all(v in HVset for v in p.vertices)]
              + [list(p.vertices)[:3] for p in me.polygons if len(p.vertices) == 4 and all(v in HVset for v in p.vertices)]
              + [[p.vertices[0], p.vertices[2], p.vertices[3]] for p in me.polygons
                 if len(p.vertices) == 4 and all(v in HVset for v in p.vertices)])
remap = {int(v): k for k, v in enumerate(HV)}
HT = np.array([[remap[int(a)] for a in t] for t in HT])
rest_inv = {b: np.linalg.inv(np.array(arm.data.bones[b].matrix_local)) for b in bone_names}


def skin():
    bpy.context.view_layer.update()
    out = np.zeros_like(VH)
    for b, k in bidx.items():
        w = Wm[:, k]
        sel = w > 0
        if not sel.any():
            continue
        S = Mw @ np.array(arm.pose.bones[b].matrix) @ rest_inv[b] @ np.linalg.inv(Mw)
        P = np.c_[VH[sel] * 0.001, np.ones(sel.sum())] @ S.T
        out[sel] += w[sel, None] * P[:, :3] * 1000.0
    return out


# ------------------------------------------------------------------------------------------------ the gun (LOD0 parts)
with bpy.data.libraries.load(str(BLEND), link=False) as (src, dst):
    names = [n for n in src.objects]
    dst.objects = names
GUN = {}
for o in dst.objects:
    if o is None or o.type != "MESH" or o.name.endswith(("_LOD1", "_LOD2", "_LOD3")) or o.name.startswith(("SM_", "SK_", "UCX_")):
        continue
    try:
        rec = json.loads(o.get("gun_part", "{}"))
    except Exception:  # noqa: BLE001
        rec = {}
    if not rec.get("slot"):
        continue
    m = o.data
    m.calc_loop_triangles()
    V = np.array([v.co for v in m.vertices]) * 1000.0
    T = np.array([t.vertices[:] for t in m.loop_triangles])
    GUN[o.name] = {"V": V, "T": T, "bone": rec.get("bone", "body")}
log("gun parts", len(GUN), "hand verts", len(HV), "hand tris", len(HT))
SOCK = {r["socket"]: r for r in SPEC.gun_sockets()}
BONES = {b["bone"]: SPEC.M_to_B(b["head_M"]) for b in D["bones"]["table"]}


def posed_gun(vals, mag=True):
    """Part vertices in frame B (mm) at clip values (smg_clips.basis_from about each bone head)."""
    bas = CL.basis_from(vals)
    out = {}
    for n, g in GUN.items():
        if not mag and g["bone"] == "magazine":
            continue
        V = g["V"]
        b = g["bone"]
        if b in bas:
            H = BONES[b]
            M = bas[b]
            V = (V - H) @ M[:3, :3].T + M[:3, 3] + H
        out[n] = (V, g["T"])
    return out


def to_world(G, Tg):
    return {n: (V @ Tg[:3, :3].T + Tg[:3, 3], T) for n, (V, T) in G.items()}


def trees(Gw):
    return {n: BVHTree.FromPolygons([tuple(v) for v in V], [tuple(int(i) for i in t) for t in T], all_triangles=True)
            for n, (V, T) in Gw.items()}


def signed_gap(P, Gw, Tr, names=None, cap=40.0):
    """Per point: distance to the nearest gun surface (mm), negative inside a part (ray parity, 3 rays)."""
    out = np.full(len(P), cap)
    owner = np.array([""] * len(P), object)
    dirs = [Vector((0.577, 0.577, 0.577)), Vector((-0.4, 0.8, 0.45)), Vector((0.3, -0.5, 0.81))]
    for n in (names or list(Gw)):
        t = Tr[n]
        V = Gw[n][0]
        lo, hi = V.min(0) - cap, V.max(0) + cap
        idx = np.nonzero(np.all((P >= lo) & (P <= hi), axis=1))[0]
        for i in idx:
            p = Vector(P[i])
            h = t.find_nearest(p, cap)
            if h[0] is None:
                continue
            d = h[3]
            if d >= out[i]:
                continue
            if d > 3.0:                          # far from the surface: outside unless deep inside a part (rare)
                nrm = np.array(h[1])
                if (P[i] - np.array(h[0])) @ nrm >= 0:
                    out[i], owner[i] = d, n
                    continue
            inside = 0
            for dv in dirs:
                k, q = 0, p.copy()
                for _ in range(64):
                    hh = t.ray_cast(q + dv * 1e-4, dv, 2000.0)
                    if hh[0] is None:
                        break
                    k += 1
                    q = hh[0]
                inside += k % 2
            sd = -d if inside >= 2 else d
            if sd < out[i]:
                out[i], owner[i] = sd, n
    return out, owner


def tri_overlaps(PH, Gw, Tr):
    th = BVHTree.FromPolygons([tuple(v) for v in PH], [tuple(int(i) for i in t) for t in HT], all_triangles=True)
    return {n: len(th.overlap(t)) for n, t in Tr.items() if len(th.overlap(t))}


# ------------------------------------------------------------------------------------------------ 1. hand frame
for pb in arm.pose.bones:
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = Quaternion()
bpy.context.view_layer.update()
Wr = bone_head("hand_r")
Ki, Km, Kp = bone_head("index_01_r"), bone_head("middle_01_r"), bone_head("pinky_01_r")
web = 0.5 * (Ki + bone_head("thumb_02_r"))
palm_c = 0.5 * (Wr + 0.5 * (Ki + Kp))
k_ax = (Kp - Ki) / np.linalg.norm(Kp - Ki)
f_ax = Km - Wr
f_ax = f_ax - k_ax * (f_ax @ k_ax)
f_ax /= np.linalg.norm(f_ax)
FINGERS = {"index": ["index_01_r", "index_02_r", "index_03_r"], "middle": ["middle_01_r", "middle_02_r", "middle_03_r"],
           "ring": ["ring_01_r", "ring_02_r", "ring_03_r"], "pinky": ["pinky_01_r", "pinky_02_r", "pinky_03_r"],
           "thumb": ["thumb_01_r", "thumb_02_r", "thumb_03_r"]}


def set_rot(b, deg):
    pb = arm.pose.bones[b]
    pb.rotation_quaternion = Quaternion((0.0, 0.0, 1.0), math.radians(deg))


# the palm side: where a finger tip goes when its 01 joint flexes; each finger's flexion sign makes the tip go there
tip0 = bone_tail("middle_03_r")
set_rot("middle_01_r", 30.0)
bpy.context.view_layer.update()
tipM = (Mw @ np.r_[np.array(arm.pose.bones["middle_03_r"].tail), 1.0])[:3] * 1000.0
set_rot("middle_01_r", 0.0)
d = tipM - tip0
# the palm side, anatomically: the '<finger>_01_palm_r' helper joints sit on the palm side of the knuckles
pal = np.mean([bone_head(f"{f}_01_palm_r") for f in ("index", "middle", "ring", "pinky")], axis=0)
kn = np.mean([bone_head(f"{f}_01_r") for f in ("index", "middle", "ring", "pinky")], axis=0)
n_try = np.cross(f_ax, k_ax)
n_palm = n_try if (pal - kn) @ n_try > 0 else -n_try
log("palm helper offset", np.round(pal - kn, 2), "tip move at +30 deg", np.round(d, 2))
SIGN = {}
for fn, chain in FINGERS.items():
    b = chain[1] if fn != "thumb" else chain[2]
    t0 = (Mw @ np.r_[np.array(arm.pose.bones[chain[2]].tail), 1.0])[:3] * 1000.0
    set_rot(b, 20.0)
    bpy.context.view_layer.update()
    t1 = (Mw @ np.r_[np.array(arm.pose.bones[chain[2]].tail), 1.0])[:3] * 1000.0
    set_rot(b, 0.0)
    ref = n_palm if fn != "thumb" else n_palm
    SIGN[fn] = 1.0 if (t1 - t0) @ ref > 0 else -1.0
bpy.context.view_layer.update()
log("hand frame: knuckle axis", np.round(k_ax, 3), "palm normal", np.round(n_palm, 3), "flex signs", SIGN)

# gun axes in the world: Y = palm normal, down-the-grip = the knuckle axis (orthogonalised)
rho = math.radians(float(D["sidecar_gun_block"]["grip_axis_deg"]))
Yw = n_palm / np.linalg.norm(n_palm)
Dw = k_ax - Yw * (k_ax @ Yw)
Dw /= np.linalg.norm(Dw)
best = None
for sgn in (1.0, -1.0):
    Pw = sgn * np.cross(Yw, Dw)
    Xw = -math.sin(rho) * Dw + math.cos(rho) * Pw
    Zw = -math.cos(rho) * Dw - math.sin(rho) * Pw
    if np.cross(Xw, Yw) @ Zw > 0:
        best = (Xw, Zw)
Xw, Zw = best
R = np.c_[Xw, Yw, Zw]                        # gun B axes -> world
a_g = np.array([-math.sin(rho), 0.0, -math.cos(rho)])


def place(t):
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = t
    return T


# the hand opened first (the rest pose's relaxed curl would put the fingers inside any grip): fingers 01 / 02 / 03
# extended 25 / 15 / 5 deg; the thumb at rest
OPEN = {}
for fn in ("index", "middle", "ring", "pinky"):
    for b, a in zip(FINGERS[fn], (-25.0, -15.0, -5.0)):
        OPEN[b] = SIGN[fn] * a
        set_rot(b, OPEN[b])
bpy.context.view_layer.update()
# along the axis: the palm centre on the Grip origin; start 30 mm out from the palm along +Y
t = palm_c + Yw * 30.0
G0 = posed_gun({})
grip_parts = [n for n in ("lower_receiver", "grip_cover") if n in G0]
palm_mask = np.array([b == "hand_r" or (("metacarpal" in b) and not b.startswith("index")) for b in main_bone])
web_mask = np.isin(main_bone, ["thumb_01_r", "index_metacarpal_r", "thumb_01_side_inn_r", "index_metacarpal_slide_r"])
idx_base_mask = np.array([b.startswith("index_01") or b.startswith("index_metacarpal") for b in main_bone])


def gap_of(t, mask):
    Gw = to_world({n: G0[n] for n in grip_parts}, place(t))
    Tr = trees(Gw)
    PH = skin()
    g, _o = signed_gap(PH[mask], Gw, Tr)
    return float(g.min())


def gap_of_all(t, mask):
    Gw = to_world(G0, place(t))
    Tr = trees(Gw)
    g, _o = signed_gap(skin()[mask], Gw, Tr)
    return float(g.min())


def push(t, direction, mask, target=CONTACT, lo=-40.0, hi=40.0, allparts=False):
    """t + s * direction with the mask's minimum gap = target (bisection on s; gap decreases as s grows)."""
    a, b = lo, hi
    gf = gap_of_all if allparts else gap_of
    ga = gf(t + a * direction, mask)
    gb = gf(t + b * direction, mask)
    if not (ga >= target >= gb):
        return t + (a if abs(ga - target) < abs(gb - target) else b) * direction, (round(ga, 3), round(gb, 3))
    for _ in range(24):
        m = 0.5 * (a + b)
        gm = gf(t + m * direction, mask)
        if gm > target:
            a = m
        else:
            b = m
    return t + 0.5 * (a + b) * direction, None


log("placing the grip in the palm")
side_mask = np.array([b == "hand_r" or "metacarpal" in b for b in main_bone])
heel_mask = np.array([b.startswith("thumb_01") or b.startswith("wrist") for b in main_bone])


def seat(s_ax):
    """The grip seated in the palm at axial offset s_ax (gun moved along the grip's down axis; negative = the hand lower
    on the grip): pushed toward the palm side (the outer metacarpals 0.3 mm off) and back into the palm heel / thenar
    (0.3 mm off), alternately until both hold."""
    t = palm_c + Dw * s_ax + Yw * 30.0
    rec = []
    for it in range(10):
        t, e1 = push(t, -Yw, side_mask)
        t, e2 = push(t, -Xw, heel_mask, lo=-30.0, hi=30.0)
        sg_, hg = gap_of(t, side_mask), gap_of(t, heel_mask)
        rec.append({"iter": it, "side_gap": round(sg_, 3), "heel_gap": round(hg, 3), "notes": [e1, e2]})
        if abs(sg_ - CONTACT) < 0.1 and abs(hg - CONTACT) < 0.1:
            break
    return t, rec


# the index knuckle must sit below the trigger housing (62 mm wide over a 32 mm grip: the MCP under its bottom edge,
# the finger reaching forward under it to the trigger): the highest seat (closest to the palm-centre rule) whose index
# base (MCP, proximal phalanx root) and open fingers clear every part: the sweep starts 24 mm above the palm-centre
# rule (the hand as high as the web allows) and steps down
rec_push = []
t = None
for s_ax in [24.0, 21.0, 18.0, 15.0, 12.0, 9.0, 6.0, 3.0, 0.0, -3.0, -6.0, -9.0, -12.0, -15.0, -18.0]:
    tt, rec = seat(s_ax)
    ig = gap_of_all(tt, idx_base_mask)
    fg = gap_of_all(tt, np.array([b.startswith(("middle_0", "ring_0", "pinky_0", "index_0")) for b in main_bone]))
    rec_push.append({"axial_offset_mm": s_ax, "seat": rec[-1], "iters": len(rec), "index_base_gap": round(ig, 3),
                     "open_fingers_gap": round(fg, 3)})
    log("seat", rec_push[-1])
    if ig >= CONTACT - 0.05 and fg >= 0.0 and abs(rec[-1]["side_gap"] - CONTACT) < 0.15:
        t = tt
        break
# a second seat, the early H1's definition: the web (index / thumb fork) in the back strap's hollow under the tang
# (scratch/h1_result.json web point), then the palm side and the web pushed to 0.3 mm contact; kept when it clears
# like the first and puts the index pad nearer the trigger face
h1e = json.loads((SCRATCH / "h1_result.json").read_text())
hollow_B = np.array(h1e["reach"]["web_point_M"], float) - GRIP
trig_Bp = np.array(SOCK["Trigger"]["blender_mm"], float)


def pad_dist(tt):
    PH = skin()
    pad = np.array([mb.startswith("index_03") for mb in main_bone])
    return float(np.linalg.norm(PH[pad] - (R @ trig_Bp + tt), axis=1).min())


t2 = web - R @ hollow_B - Yw * 0.0
rec2 = []
for it in range(10):
    t2, e1 = push(t2, -Yw, side_mask)
    t2, e2 = push(t2, -Xw, web_mask, lo=-30.0, hi=30.0)
    sg_, wg = gap_of(t2, side_mask), gap_of(t2, web_mask)
    rec2.append({"iter": it, "side_gap": round(sg_, 3), "web_gap": round(wg, 3)})
    if abs(sg_ - CONTACT) < 0.1 and abs(wg - CONTACT) < 0.1:
        break
ig2 = gap_of_all(t2, idx_base_mask)
fg2 = gap_of_all(t2, np.array([b.startswith(("middle_0", "ring_0", "pinky_0", "index_0")) for b in main_bone]))
seat2 = {"seat": "web in the hollow", "last": rec2[-1], "index_base_gap": round(ig2, 3), "open_fingers_gap": round(fg2, 3),
         "open_pad_to_trigger_mm": round(pad_dist(t2), 2)}
log("seat2", seat2)
rec_push.append(seat2)
if t is not None:
    log("seat1 open pad to trigger", round(pad_dist(t), 2))
if ig2 >= CONTACT - 0.05 and fg2 >= 0.0 and (t is None or pad_dist(t2) < pad_dist(t)):
    t = t2
    log("using the web-in-the-hollow seat")
if t is None:
    best = max(rec_push, key=lambda r: min(r["index_base_gap"], r["open_fingers_gap"]))
    t, _ = seat(best.get("axial_offset_mm", 0.0))
    log("no seat clears the index base: using", best)
Tg = place(t)

# ------------------------------------------------------------------------------------------------ 3. grip pose
Gw0 = to_world(G0, Tg)
Tr0 = trees(Gw0)
POSE = {}


def moved_mask(stems, wmin=0.05):
    """Hand vertices any of whose skin weight (>= wmin) sits on a bone of these chains (helpers included): every vertex
    a joint drags along, not only those it owns."""
    cols = [k for b_, k in bidx.items() if any(b_.startswith(s_) for s_ in stems)]
    return Wm[:, cols].sum(1) >= wmin if cols else np.zeros(len(HV), bool)


def chain_gap(chain_from, gun_w, gun_t):
    stem = [x.replace("_r", "") for x in chain_from]
    mask = moved_mask(stem)
    g, own = signed_gap(skin()[mask], gun_w, gun_t, cap=25.0)
    return float(g.min()), str(own[np.argmin(g)])


def curl(finger, gun_w, gun_t, max_deg=100.0, joints=None):
    """Each joint (proximal first) flexes (the anatomical sign: toward the palm) from the open pose until the distal
    skin is CURL_STOP off the gun (1 deg steps refined to 0.25); a joint whose distal skin already touches the gun
    first extends (up to 60 deg) until it is clear."""
    chain = FINGERS[finger] if joints is None else joints
    sg = SIGN[finger]
    angles = {}
    for j, b in enumerate(chain):
        distal = chain[j:]
        a0 = OPEN.get(b, 0.0)
        set_rot(b, a0)
        g, _ = chain_gap(distal, gun_w, gun_t)
        ext = 0.0
        while g <= CURL_STOP and ext < 60.0:
            ext += 2.0
            set_rot(b, a0 - sg * ext)
            g, _ = chain_gap(distal, gun_w, gun_t)
        a0 = a0 - sg * ext
        ang, step = 0.0, 2.0
        while ang < max_deg:
            set_rot(b, a0 + sg * (ang + step))
            g, _ = chain_gap(distal, gun_w, gun_t)
            if g <= CURL_STOP:
                if step <= 0.25:
                    break
                step /= 4.0
                continue
            ang += step
        set_rot(b, a0 + sg * ang)
        angles[b] = round(a0 + sg * ang, 2)
    return angles


def thumb_clear(gun_w, gun_t):
    """The thumb's metacarpal (thumb_01) turned out of the grip: the smallest rotation about its local X / Z axes (10
    deg grid to +-70) that leaves the whole thumb >= CURL_STOP off the gun, preferring the one closest to the grip."""
    pb = arm.pose.bones["thumb_01_r"]
    best = None
    for ax in range(-70, 71, 10):
        for az in range(-70, 71, 10):
            pb.rotation_quaternion = (Quaternion((1.0, 0.0, 0.0), math.radians(ax)) @
                                      Quaternion((0.0, 0.0, 1.0), math.radians(az)))
            g, _ = chain_gap(FINGERS["thumb"], gun_w, gun_t)
            if g >= CURL_STOP:
                key = (abs(ax) + abs(az), g)
                if best is None or key < best[0]:
                    best = (key, ax, az, g)
    if best is None:
        pb.rotation_quaternion = Quaternion()
        return {"thumb_01_r": "no clear pose in the grid"}
    _, ax, az, g = best
    pb.rotation_quaternion = (Quaternion((1.0, 0.0, 0.0), math.radians(ax)) @
                              Quaternion((0.0, 0.0, 1.0), math.radians(az)))
    return {"thumb_01_r": {"about_local_X_deg": ax, "about_local_Z_deg": az, "gap_mm": round(g, 3)}}


for fn in ("middle", "ring", "pinky"):
    POSE.update(curl(fn, Gw0, Tr0))
    log("curl", fn, {k: v for k, v in POSE.items() if k.startswith(fn)}, chain_gap(FINGERS[fn], Gw0, Tr0))
POSE.update(thumb_clear(Gw0, Tr0))
POSE.update(curl("thumb", Gw0, Tr0, joints=["thumb_02_r", "thumb_03_r"], max_deg=40.0))


def index_to_trigger(gun_w, gun_t):
    """The trigger finger: the knuckle's flexion q1 and abduction a (about its local Z / X), the middle joint's
    flexion q2 and the end joint at 0.7 q2, searched (coarse 10 deg grid, then 2.5 deg around the best) for the pad
    (index_03 skin) closest to the trigger face (the Trigger socket) with every vertex the finger drags clear of the
    frame (gap >= 0), the pad in front of the trigger face and CURL_STOP off it (the finger's contact): the pad as close
    to the trigger face as the frame lets it."""
    trig_B = np.array(SOCK["Trigger"]["blender_mm"], float)
    trig_w = Tg[:3, :3] @ trig_B + Tg[:3, 3]
    chain = FINGERS["index"]
    mask = moved_mask([x.replace("_r", "") for x in chain])
    pad = np.array([mb.startswith("index_03") for mb in main_bone])
    others = [n for n in gun_w if n != "trigger"]
    Go, To = {n: gun_w[n] for n in others}, {n: gun_t[n] for n in others}
    sg = SIGN["index"]

    def pose(q1, a, q2):
        arm.pose.bones[chain[0]].rotation_quaternion = (Quaternion((1.0, 0.0, 0.0), math.radians(a)) @
                                                        Quaternion((0.0, 0.0, 1.0), math.radians(OPEN[chain[0]] + sg * q1)))
        set_rot(chain[1], OPEN[chain[1]] + sg * q2)
        set_rot(chain[2], OPEN[chain[2]] + sg * 0.7 * q2)

    def score(q1, a, q2):
        pose(q1, a, q2)
        PH = skin()
        g, _ = signed_gap(PH[mask], Go, To, cap=8.0)
        if g.min() < 0.0:
            return None
        gt, _ = signed_gap(PH[pad], {"trigger": gun_w["trigger"]}, {"trigger": gun_t["trigger"]}, cap=30.0)
        if gt.min() < CURL_STOP:
            return None
        k_ = int(np.argmin(gt))
        if (PH[pad][k_] - trig_w) @ Xw < -2.0:          # the pad on the trigger's FRONT face (it pulls it back)
            return None
        # the pad's distance to the trigger's surface (the face it rests on), the socket point as a tie-break
        return (float(gt.min()) + 0.01 * float(np.linalg.norm(PH[pad] - trig_w, axis=1).min()), float(g.min()),
                float(gt.min()))
    best = None
    for q1 in range(-30, 71, 10):
        for a in range(-40, 21, 10):
            for q2 in range(0, 101, 10):
                r = score(q1, a, q2)
                if r is not None and (best is None or r[0] < best[0][0]):
                    best = (r, q1, a, q2)
    if best is None:
        return {"index": "no clear pose"}, None
    _, q1b, ab, q2b = best
    for q1 in np.arange(q1b - 7.5, q1b + 7.6, 2.5):
        for a in np.arange(ab - 7.5, ab + 7.6, 2.5):
            for q2 in np.arange(max(0.0, q2b - 7.5), q2b + 7.6, 2.5):
                r = score(q1, a, q2)
                if r is not None and r[0] < best[0][0]:
                    best = (r, q1, a, q2)
    (dpad, g, gt), q1, a, q2 = best
    pose(q1, a, q2)
    return ({"index_01_r": {"curl_deg": round(float(OPEN[chain[0]] + sg * q1), 2), "abduction_deg_about_local_X": float(a)},
             "index_02_r": round(float(OPEN[chain[1]] + sg * q2), 2),
             "index_03_r": round(float(OPEN[chain[2]] + sg * 0.7 * q2), 2)},
            {"pad_to_trigger_surface_mm": round(gt, 3), "gap_to_frame_mm": round(g, 3)})


ip, IDX = index_to_trigger(Gw0, Tr0)
POSE.update(ip)
log("index", ip, IDX)
log("curl thumb", {k: v for k, v in POSE.items() if k.startswith("thumb")}, chain_gap(FINGERS["thumb"], Gw0, Tr0))
PH0 = skin()

# ------------------------------------------------------------------------------------------------ 4. gates
out = {"body": LOCK["blend"], "body_sha256_locked": LOCK.get("blend_sha256"),
       "body_sha256_now": hashlib.sha256((ROOT / LOCK["blend"]).read_bytes()).hexdigest()}
out["body_sha256_matches_lock"] = out["body_sha256_now"] == out["body_sha256_locked"]
gp, own = signed_gap(PH0[palm_mask], {n: Gw0[n] for n in grip_parts}, {n: Tr0[n] for n in grip_parts})
out["palm"] = {"min_signed_gap_mm": round(float(gp.min()), 3), "penetration_mm": round(max(0.0, -float(gp.min())), 3),
               "threshold": "<= 1 mm", "pass": -float(gp.min()) <= 1.0}
# index pad to the trigger face
trig_B = np.array(SOCK["Trigger"]["blender_mm"], float)
trig_w = Tg[:3, :3] @ trig_B + Tg[:3, 3]
idx_mask = np.array([mb.startswith("index_03") for mb in main_bone])
dpad = np.linalg.norm(PH0[idx_mask] - trig_w, axis=1)
gi_, oi_ = signed_gap(PH0[idx_mask], Gw0, Tr0)
gtr, _ = signed_gap(PH0[idx_mask], {"trigger": Gw0["trigger"]}, {"trigger": Tr0["trigger"]}, cap=40.0)
out["index"] = {"pad_to_trigger_face_mm": round(float(gtr.min()), 3),
                "pad_to_trigger_socket_point_mm": round(float(dpad.min()), 2), "nearest_part": str(oi_[np.argmin(gi_)]),
                "nearest_gap_mm": round(float(gi_.min()), 3), "search": IDX,
                "threshold": "the index pad within 3 mm of the trigger face at the rest curl (study 7.2), the finger "
                             "clear of the frame",
                "pass": 0.0 <= float(gtr.min()) <= 3.0}


def check(vals, mag=True, label=""):
    Gw = to_world(posed_gun(vals, mag), Tg)
    Tr = trees(Gw)
    ov = tri_overlaps(PH0, Gw, Tr)
    g, o = signed_gap(PH0, Gw, Tr, cap=5.0)
    pen = {}
    for n in set(o[g < -0.01]):
        sel_ = (o == n) & (g < 0)
        k_ = np.nonzero(sel_)[0][np.argmin(g[sel_])]
        pen[n] = {"depth_mm": round(float(-g[k_]), 3), "hand_bone": str(main_bone[k_]),
                  "vertices": int(sel_.sum())}
    return {"config": label, "triangle_pairs": ov, "penetration_mm": pen, "min_gap_mm": round(float(g.min()), 3)}


configs = [({}, True, "rest"), ({"bolt": 67.9}, True, "bolt back"),
           ({"handle": 67.9, "bolt": 67.9}, True, "charging handle back"), ({"trigger": 13.0}, True, "trigger pulled"),
           ({"selector": -63.4}, True, "selector SAFE"), ({"selector": 45.0}, True, "selector AUTO"),
           ({"release": -11.0}, True, "paddle pressed"), ({}, False, "magazine out"), ({"stock": 180.0}, True,
                                                                                      "stock folded"),
           ({"rear": 90.0, "front": -90.0}, True, "sights folded")]
out["clip_extremes"] = [check(v, m, l) for v, m, l in configs]
# the palm's own contact (0.3 mm by construction) is the only allowed touch: everything else 0
inter = {c["config"]: c for c in out["clip_extremes"] if c["triangle_pairs"] or c["penetration_mm"]}
out["intersections"] = {"configs_with_any": sorted(inter), "pass": not inter}
for c in out["clip_extremes"]:
    log("extreme", c)


# ------------------------------------------------------------------------------------------------ cheek weld + IK
def two_bone(S, L1, L2, T):
    d = float(np.linalg.norm(T - S))
    reach = L1 + L2
    resid = max(0.0, d - reach)
    dd = min(d, reach - 1e-6)
    cos_e = (L1 * L1 + L2 * L2 - dd * dd) / (2 * L1 * L2)
    elbow_inner = math.degrees(math.acos(max(-1.0, min(1.0, cos_e))))
    return {"distance_mm": round(d, 1), "reach_mm": round(reach, 1), "residual_mm": round(resid, 3),
            "elbow_flexion_deg": round(180.0 - elbow_inner, 1),
            "pass": resid < 0.5 and 0.0 <= 180.0 - elbow_inner <= 150.0}


eye = bone_head("head") + EYE_OFFSET
Rg = np.array([[0.0, 1.0, 0.0], [-1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])   # gun X -> world -Y (front), Y -> +X, Z up
sight_B = np.array(SOCK["Sight"]["blender_mm"], float)
t_ads = eye - Rg @ (sight_B + np.array([-EYE_RELIEF, 0.0, 0.0]))
Tads = np.eye(4)
Tads[:3, :3] = Rg
Tads[:3, 3] = t_ads
hand_in_gun = np.linalg.inv(Tg)                     # world(hold) -> gun B
wr_target = Tads @ (hand_in_gun @ np.r_[Wr, 1.0])
S_r = bone_head("upperarm_r")
L1r = float(np.linalg.norm(bone_head("lowerarm_r") - S_r))
L2r = float(np.linalg.norm(Wr - bone_head("lowerarm_r")))
sh_B = np.array(SOCK["SupportHand"]["blender_mm"], float)
sh_w = Tads[:3, :3] @ sh_B + Tads[:3, 3]
S_l = bone_head("upperarm_l")
L1l = float(np.linalg.norm(bone_head("lowerarm_l") - S_l))
L2l = float(np.linalg.norm(bone_head("hand_l") - bone_head("lowerarm_l")))
palm_off = 0.5 * (bone_head("index_01_l") + bone_head("pinky_01_l")) * 0.5 + 0.5 * bone_head("hand_l") - bone_head("hand_l")
wl_target = sh_w - Rg @ np.array([0.0, 0.0, 0.0]) - palm_off * 0.0
shoulder_B = np.array(SOCK["Shoulder"]["blender_mm"], float)
shoulder_w = Tads[:3, :3] @ shoulder_B + Tads[:3, 3]
out["cheek_weld"] = {"eye_world_mm": np.round(eye, 1).tolist(), "eye_offset_from_head_joint_mm": EYE_OFFSET.tolist(),
                     "eye_relief_mm": EYE_RELIEF,
                     "assumption": "right eye 32 mm right, 95 mm forward, 85 mm above the 'head' joint (MetaHuman "
                                   "proportions; the body skeleton has no eye joint); bore level, facing the body's front",
                     "buttpad_centre_to_right_shoulder_joint_mm": round(float(np.linalg.norm(shoulder_w - S_r)), 1)}
out["ik_right"] = dict(two_bone(S_r, L1r, L2r, wr_target[:3]), what="right arm to the held grip (hand frame as in the hold)")
out["ik_left"] = dict(two_bone(S_l, L1l, L2l, sh_w), what="left arm: wrist to SupportHand (the palm on the magwell front)")
# ------------------------------------------------------------------------------------------------ hand_offset
Mh = Mw @ np.array(arm.data.bones["hand_r"].matrix_local)
Mh[:3, 3] *= 1000.0
G_in_hand = np.linalg.inv(Mh) @ Tg
q = Matrix(G_in_hand[:3, :3].tolist()).to_quaternion()
out["hand_offset"] = {"frame": "hand_r bone (MH_PlayerDefault metahuman_base_skel, Blender armature axes)",
                      "Grip_location_mm": np.round(G_in_hand[:3, 3], 3).tolist(),
                      "Grip_rotation_quaternion_wxyz": [round(float(v), 6) for v in q],
                      "grip_pose_deg_about_local_Z": POSE,
                      "note": "U11 reproduces it in engine (Grip on a socket of hand_r at this offset)"}
out["placement_pushes"] = rec_push
summary = {"palm_penetration_mm": out["palm"]["penetration_mm"], "index_pad_to_trigger_face_mm":
           out["index"]["pad_to_trigger_face_mm"], "index_nearest_part": out["index"]["nearest_part"],
           "intersections_at_extremes": out["intersections"]["configs_with_any"],
           "ik_left_residual_mm": out["ik_left"]["residual_mm"], "ik_left_elbow_deg": out["ik_left"]["elbow_flexion_deg"],
           "ik_right_residual_mm": out["ik_right"]["residual_mm"],
           "ik_right_elbow_deg": out["ik_right"]["elbow_flexion_deg"]}
out["summary"] = summary
out["threshold"] = ("palm penetration <= 1 mm; index pad <= 3 mm from the trigger face at the rest curl (the finger "
                    "clear of the frame); 0 hand-gun intersections at rest and at every clip extreme; both arms' two-bone IK "
                    "< 0.5 mm with the elbow inside 0..150 deg")
out["pass"] = bool(out["palm"]["pass"] and out["index"]["pass"] and out["intersections"]["pass"]
                   and out["ik_left"]["pass"] and out["ik_right"]["pass"])
out["note"] = "measured on the locked fit body in Blender (study 7.2 H1); U11 confirms in engine at W5"
(SCRATCH / "h1_full.json").write_text(json.dumps(out, indent=1, default=str))
log("SUMMARY", json.dumps(summary), "PASS" if out["pass"] else "FAIL")

# ------------------------------------------------------------------------------------------------ pictures
try:
    import bmesh
    col = bpy.data.collections.new("H1_View")
    bpy.context.scene.collection.children.link(col)
    for n, (V, T) in Gw0.items():
        m = bpy.data.meshes.new("h1_" + n)
        m.from_pydata((V * 0.001).tolist(), [], T.tolist())
        o = bpy.data.objects.new("h1_" + n, m)
        col.objects.link(o)
    for o in bpy.data.objects:
        if o.type == "MESH" and o.name.startswith("FIT_") and o != body:
            o.hide_render = True
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.render.resolution_x, sc.render.resolution_y = 1100, 900
    cam = bpy.data.objects.new("h1cam", bpy.data.cameras.new("h1cam"))
    col.objects.link(cam)
    sc.camera = cam
    c = (Tg[:3, 3]) * 0.001
    for tag, off in (("right", -Yw * 0.45 + Zw * 0.05), ("left", Yw * 0.45 + Zw * 0.05),
                     ("front", Xw * 0.45 + Zw * 0.1)):
        cam.location = Vector((c + off).tolist())
        dvec = Vector((c - (c + off)).tolist())
        cam.rotation_euler = dvec.to_track_quat("-Z", "Y").to_euler()
        cam.data.lens = 50
        sc.render.filepath = str(OUTD / f"h1_hold_{tag}.png")
        bpy.ops.render.render(write_still=True)
    log("pictures written")
except Exception as e:  # noqa: BLE001
    log("pictures failed", e)
log("H1F_DONE")
