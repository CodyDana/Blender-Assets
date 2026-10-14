"""SR01 gate H1 FULL (the SMG's smg_h1_full.py ported to the sniper): MH_PlayerDefault's hands on the SHIPPED bytes.

    blender -b References/Characters/MH_PlayerDefault/MH_PlayerDefault_FitBody.blend --factory-startup \
        --python Scripts/guns/sniper/sr_h1_full.py

Gun: Exports/Guns/SR01/SK_SR01.fbx (LOD0, skinned; parts = the vertices of each bone), the clip extremes taken from the
shipped clip FBX files (each clip's own armature drives the SK mesh, as sr_rig_render.py), SM_SR01_Mag.fbx LOD0 on the
'magazine' bone, SM_Att_Scope_LongRange.fbx LOD0 on Rail_Top + 2 slots (the sidecar's mount). Nothing is saved to the
fit body; nothing in Exports/ is written.

Method (the SMG's, frame B = the Grip origin, mm):
1. right hand on Grip: the hand frame from the rest skeleton (knuckle line = down the grip, palm normal = gun +Y), the
   grip seated in the opened hand (metacarpals and thenar / heel 0.3 mm off), the highest seat whose index base and open
   fingers clear every part, the web-in-the-hollow seat tried too (spec web point); middle / ring / pinky curl to 0.5 mm,
   thumb out of the grip then curled; the trigger finger searched for the pad nearest the Trigger face, clear of the
   frame;
2. left hand on SupportHand (pose A, standing / sitting, bipod folded) and on SupportHandBipod (pose B, prone, bipod
   deployed): palm up under the gun (knuckle line along the bore, fingers wrapping the gun's right side), the socket
   over the palm centre, pushed to 0.3 mm contact, fingers and thumb curled to 0.5 mm (the same curl);
3. gates: palm penetration <= 1 mm (each hand), index pad 0..3 mm from the trigger face, 0 hand-gun triangle pairs /
   penetrations at rest and at every clip extreme (bolt unlocked, bolt back, trigger pulled, SAFE, paddle pressed,
   magazine out, riser up / down, bipod deployed), both arms' two-bone IK < 0.5 mm with the elbow inside 0..150 deg
   with the scope's EyePoint on the right eye (bore level, facing the body's front), grip girth <= 167 mm at the palm
   and trigger reach <= 80 mm (the W1 early bands);
4. reported: length of pull, eye relief (EyePoint to the eyepiece, and what the upright body gives with the butt in the
   shoulder pocket), cheek-riser height needed (the face's lowest point over the riser), each support socket vs the
   seated palm centre (a proposal when they differ), hand_offset (the Grip frame in hand_r).
Writes WorkFiles/guns/sniper/gates/h1_full.json and Renders/Guns/SR01/h1_*.png.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from sr_common import ROOT, WORK, GATES, RENDERS, D, GRIP  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Quaternion, Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

EXP = ROOT / "Exports" / "Guns" / "SR01"
SKJ = json.loads((EXP / "SK_SR01.skeletal.json").read_text())
SCJ = json.loads((EXP / "SM_Att_Scope_LongRange.sockets.json").read_text())
LOCK = json.loads((ROOT / "References" / "Characters" / "MH_PlayerDefault" / "base_lock.json").read_text())
SOCK = {s["name"]: np.array(s["location_mm"], float) for s in SKJ["sockets"]}
MOUNT_B = np.array(D["scope_attachment"]["mount_M"], float) - GRIP
SC_SOCK = {s["socket"]: np.array(s["location_cm"], float) * np.array([10.0, -10.0, 10.0]) for s in SCJ["sockets"]}
EYEPOINT_B = MOUNT_B + SC_SOCK["EyePoint"]
SIGHT_B = MOUNT_B + SC_SOCK["Sight"]
RHO = math.radians(float(SKJ["gun"]["grip_axis_deg"]))
CONTACT = 0.3
CURL_STOP = 0.5
RENDERS.mkdir(parents=True, exist_ok=True)
OUTJ = GATES / "h1_full.json"


def log(*a):
    print("[SRH1]", *a, flush=True)


arm = bpy.data.objects["root"]                     # the fit body's armature (taken before any FBX import)
body = bpy.data.objects["FIT_MH_PlayerDefault_Body"]
headm = bpy.data.objects["FIT_MH_PlayerDefault_Head"]
headparts = bpy.data.objects["FIT_MH_PlayerDefault_HeadParts"]
Mw = np.array(arm.matrix_world)
for pb in arm.pose.bones:
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = Quaternion()
bpy.context.view_layer.update()


def bone_head(n):
    return (Mw @ np.r_[np.array(arm.data.bones[n].head_local), 1.0])[:3] * 1000.0


def pose_tail(n):
    return (Mw @ np.r_[np.array(arm.pose.bones[n].tail), 1.0])[:3] * 1000.0


def bvh(V, T):
    return BVHTree.FromPolygons([tuple(v) for v in V], [tuple(int(i) for i in t) for t in T], all_triangles=True)


# ================================================================================================ the shipped gun
def import_fbx(p):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(p), use_custom_normals=True, automatic_bone_orientation=False)
    return [o for o in bpy.data.objects if o not in before]


IMPORTED = []
sk = import_fbx(EXP / "SK_SR01.fbx")
IMPORTED += sk
skarm = next(o for o in sk if o.type == "ARMATURE")
skmesh = next(o for o in sk if o.type == "MESH" and any(m.type == "ARMATURE" for m in o.modifiers))
for o in sk:
    if o.type == "MESH" and o is not skmesh:
        o.hide_render = True
trig_head = np.array(skarm.matrix_world @ skarm.data.bones["trigger"].head_local) * 1000.0
frame_err = float(np.linalg.norm(trig_head - np.array(SKJ["bones_rest"]["trigger"]["head_mm"])))
log("imported SK frame check (trigger bone head vs sidecar, mm)", round(frame_err, 4))
assert frame_err < 0.5, "the imported SK_SR01 is not in frame B (metres)"
CLIPS = {}
for c in ("A_SR01_BoltCycle", "A_SR01_Fire", "A_SR01_Selector", "A_SR01_Reload", "A_SR01_CheekRiser",
          "A_SR01_BipodDeploy"):
    objs = import_fbx(EXP / f"{c}.fbx")
    IMPORTED += objs
    a2 = next(o for o in objs if o.type == "ARMATURE")
    CLIPS[c] = a2
    for o in objs:
        if o is not a2:
            o.hide_render = True


def first_lod(path, stem):
    objs = import_fbx(path)
    IMPORTED.extend(objs)
    keep = next(o for o in objs if o.type == "MESH" and o.name.startswith(f"{stem}_LOD0"))
    m = keep.data
    m.calc_loop_triangles()
    V = np.array([v.co for v in m.vertices]) * 1000.0
    T = np.array([t.vertices[:] for t in m.loop_triangles])
    return V, T


MAG_V, MAG_T = first_lod(EXP / "SM_SR01_Mag.fbx", "SM_SR01_Mag")
SCO_V, SCO_T = first_lod(EXP / "SM_Att_Scope_LongRange.fbx", "SM_Att_Scope_LongRange")
SCO_V = SCO_V + MOUNT_B
skm = skmesh.data
skm.calc_loop_triangles()
SK_T = np.array([t.vertices[:] for t in skm.loop_triangles])
vg_name = {g.index: g.name for g in skmesh.vertex_groups}
dom = []
for v in skm.vertices:
    gs = [(g.weight, vg_name[g.group]) for g in v.groups if g.weight > 0]
    dom.append(max(gs)[1] if gs else "body")
dom = np.array(dom)
PART_TRIS = {}
for b in sorted(set(dom)):
    sel = dom[SK_T[:, 0]] == b
    if sel.any():
        PART_TRIS[b] = SK_T[sel]
log("SK parts", {b: len(t) for b, t in PART_TRIS.items()})


def reset_skarm():
    for pb in skarm.pose.bones:
        pb.matrix_basis = Matrix()
    bpy.context.view_layer.update()


def gun_config(clip=None, frame=0, mag=True):
    """Every part's vertices in frame B (mm) with the SK posed at a clip frame (absolute pose matrices copied)."""
    reset_skarm()
    if clip:
        a2 = CLIPS[clip]
        off = int(round(a2.animation_data.action.frame_range[0]))
        bpy.context.scene.frame_set(frame + off)
        bpy.context.view_layer.update()
        for b in skarm.data.bones:
            skarm.pose.bones[b.name].matrix = a2.pose.bones[b.name].matrix.copy()
            bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = skmesh.evaluated_get(dg)
    me = ev.to_mesh()
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    ev.to_mesh_clear()
    co = co.reshape(-1, 3)
    M = np.array(skmesh.matrix_world)
    V = (np.c_[co, np.ones(len(co))] @ M.T)[:, :3] * 1000.0
    parts = {}
    for b, T in PART_TRIS.items():
        used = np.unique(T)
        rm = -np.ones(len(V), int)
        rm[used] = np.arange(len(used))
        parts[b] = (V[used], rm[T])
    if mag:
        Mm = np.array(skarm.matrix_world @ skarm.pose.bones["magazine"].matrix)
        loc, rot, _s = Matrix(Mm.tolist()).decompose()
        Rm = np.array(rot.to_matrix())
        parts["magazine_SM"] = (MAG_V @ Rm.T + np.array(loc) * 1000.0, MAG_T)
    parts["scope_SM"] = (SCO_V, SCO_T)
    pose_vals = {"bolt_head_dx_mm": round(float((np.array(skarm.matrix_world @ skarm.pose.bones["bolt"].head)
                                                 * 1000.0)[0] - SKJ["bones_rest"]["bolt"]["head_mm"][0]), 2)}
    return parts, pose_vals


class Gun:
    def __init__(self, parts, label=""):
        self.P = parts
        self.label = label
        self.tr = {n: bvh(V, T) for n, (V, T) in parts.items()}
        self.box = {n: (V.min(0), V.max(0)) for n, (V, T) in parts.items()}


DIRS = [Vector((0.577, 0.577, 0.577)), Vector((-0.4, 0.8, 0.45)), Vector((0.3, -0.5, 0.81))]


def signed_gap(P, gun, names=None, cap=40.0):
    """Per point (frame B, mm): distance to the nearest gun surface, negative inside a part (ray parity, 3 rays)."""
    out = np.full(len(P), cap)
    owner = np.array([""] * len(P), object)
    for n in (names or list(gun.P)):
        t = gun.tr[n]
        lo, hi = gun.box[n][0] - cap, gun.box[n][1] + cap
        idx = np.nonzero(np.all((P >= lo) & (P <= hi), axis=1))[0]
        for i in idx:
            p = Vector(P[i])
            h = t.find_nearest(p, cap)
            if h[0] is None:
                continue
            d = h[3]
            if d >= out[i]:
                continue
            if d > 3.0:
                if (P[i] - np.array(h[0])) @ np.array(h[1]) >= 0:
                    out[i], owner[i] = d, n
                    continue
            inside = 0
            for dv in DIRS:
                k, q = 0, p.copy()
                for _ in range(64):
                    hh = t.ray_cast(q + dv * 1e-4, dv, 3000.0)
                    if hh[0] is None:
                        break
                    k += 1
                    q = hh[0]
                inside += k % 2
            sd = -d if inside >= 2 else d
            if sd < out[i]:
                out[i], owner[i] = sd, n
    return out, owner


# ================================================================================================ hands (LBS)
gi = {g.index: g.name for g in body.vertex_groups}
me_body = body.data
VREST = np.array([v.co for v in me_body.vertices]) * 1000.0


class Hand:
    def __init__(self, side):
        s = "_" + side
        self.s = s
        root = "hand" + s
        hb = {root} | {b.name for b in arm.data.bones[root].children_recursive}
        HV = []
        for v in me_body.vertices:
            gs = [(gi[g.group], g.weight) for g in v.groups if g.weight > 0 and g.group in gi]
            if gs and max(gs, key=lambda t_: t_[1])[0] in hb:
                HV.append(v.index)
        self.HV = np.array(HV)
        hvs = set(HV)
        names = sorted({gi[g.group] for i in HV for g in me_body.vertices[i].groups if g.group in gi and g.weight > 0})
        self.bidx = {b: k for k, b in enumerate(names)}
        Wm = np.zeros((len(HV), len(names)))
        for r, i in enumerate(HV):
            for g in me_body.vertices[i].groups:
                if g.group in gi and g.weight > 0 and gi[g.group] in self.bidx:
                    Wm[r, self.bidx[gi[g.group]]] += g.weight
        self.Wm = Wm / np.maximum(Wm.sum(1, keepdims=True), 1e-9)
        self.VH = VREST[self.HV]
        self.main = np.array([names[k] for k in self.Wm.argmax(1)])
        tris = []
        for p in me_body.polygons:
            vs = list(p.vertices)
            if all(v in hvs for v in vs):
                tris += [vs[:3]] + ([[vs[0], vs[2], vs[3]]] if len(vs) == 4 else [])
        remap = {int(v): k for k, v in enumerate(self.HV)}
        self.HT = np.array([[remap[a] for a in t] for t in tris])
        self.rest_inv = {b: np.linalg.inv(np.array(arm.data.bones[b].matrix_local)) for b in names}
        self.F = {f: [f"{f}_0{k}{s}" for k in (1, 2, 3)] for f in ("index", "middle", "ring", "pinky", "thumb")}
        # frame
        self.Wr = bone_head(root)
        Ki, Km, Kp = bone_head("index_01" + s), bone_head("middle_01" + s), bone_head("pinky_01" + s)
        self.web = 0.5 * (Ki + bone_head("thumb_02" + s))
        self.palm_c = 0.5 * (self.Wr + 0.5 * (Ki + Kp))
        k_ax = (Kp - Ki) / np.linalg.norm(Kp - Ki)
        f_ax = Km - self.Wr
        f_ax = f_ax - k_ax * (f_ax @ k_ax)
        self.k_ax, self.f_ax = k_ax, f_ax / np.linalg.norm(f_ax)
        pal = np.mean([bone_head(f"{f}_01_palm{s}") for f in ("index", "middle", "ring", "pinky")], axis=0)
        kn = np.mean([bone_head(f"{f}_01{s}") for f in ("index", "middle", "ring", "pinky")], axis=0)
        n_try = np.cross(self.f_ax, k_ax)
        self.n_palm = n_try if (pal - kn) @ n_try > 0 else -n_try
        self.SIGN = {}
        for fn, chain in self.F.items():
            b = chain[1] if fn != "thumb" else chain[2]
            t0 = pose_tail(chain[2])
            self.set_rot(b, 20.0)
            bpy.context.view_layer.update()
            t1 = pose_tail(chain[2])
            self.set_rot(b, 0.0)
            self.SIGN[fn] = 1.0 if (t1 - t0) @ self.n_palm > 0 else -1.0
        bpy.context.view_layer.update()
        self.OPEN = {}
        self.open_hand()
        mb = self.main
        self.palm_mask = np.array([b == root or (("metacarpal" in b) and not b.startswith("index")) for b in mb])
        self.side_mask = np.array([b == root or "metacarpal" in b for b in mb])
        # (SR01) the seat masks carry no thumb skin: the rest thumb lies across the grip's left side and would block
        # every push (run 1: the thenar 9.5 mm inside the grip at both ends of the heel push); thumb_clear frees it
        thw = self.moved_mask(["thumb"], wmin=0.2)
        L = float(np.linalg.norm(0.5 * (Ki + Kp) - self.Wr))
        along = (self.VH - self.Wr) @ self.f_ax
        self.heel_mask = (mb == root) & ~thw & (along < 0.4 * L)
        self.web_mask = (np.isin(mb, [root, "index_metacarpal" + s]) & ~thw
                         & (np.linalg.norm(self.VH - self.web, axis=1) < 18.0))
        self.idx_base_mask = np.array([b.startswith("index_01") or b.startswith("index_metacarpal") for b in mb])
        self.fingers_mask = np.array([b.startswith(("middle_0", "ring_0", "pinky_0", "index_0")) for b in mb])
        self.pad_mask = np.array([b.startswith("index_03") for b in mb])
        log(f"hand{s}: masks side {int(self.side_mask.sum())} heel {int(self.heel_mask.sum())} "
            f"web {int(self.web_mask.sum())} palm {int(self.palm_mask.sum())}")
        log(f"hand{s}: verts {len(self.HV)} tris {len(self.HT)} palm normal {np.round(self.n_palm, 3)} "
            f"knuckle axis {np.round(k_ax, 3)} signs {self.SIGN}")

    def set_rot(self, b, deg):
        arm.pose.bones[b].rotation_quaternion = Quaternion((0.0, 0.0, 1.0), math.radians(deg))

    def open_hand(self):
        for fn in ("index", "middle", "ring", "pinky"):
            for b, a in zip(self.F[fn], (-25.0, -15.0, -5.0)):
                self.OPEN[b] = self.SIGN[fn] * a
                self.set_rot(b, self.OPEN[b])
        for b in self.F["thumb"]:
            arm.pose.bones[b].rotation_quaternion = Quaternion()
        bpy.context.view_layer.update()

    def skin(self):
        bpy.context.view_layer.update()
        out = np.zeros_like(self.VH)
        iMw = np.linalg.inv(Mw)
        for b, k in self.bidx.items():
            w = self.Wm[:, k]
            sel = w > 0
            if not sel.any():
                continue
            S = Mw @ np.array(arm.pose.bones[b].matrix) @ self.rest_inv[b] @ iMw
            P = np.c_[self.VH[sel] * 0.001, np.ones(sel.sum())] @ S.T
            out[sel] += w[sel, None] * P[:, :3] * 1000.0
        return out

    def moved_mask(self, stems, wmin=0.05):
        cols = [k for b_, k in self.bidx.items() if any(b_.startswith(s_) for s_ in stems)]
        return self.Wm[:, cols].sum(1) >= wmin if cols else np.zeros(len(self.HV), bool)

    def finger_pose(self):
        out = {}
        for chain in self.F.values():
            for b in chain:
                q = arm.pose.bones[b].rotation_quaternion
                out[b] = [round(float(x), 6) for x in q]
        return out


def to_B(Pw, R, t):
    return (Pw - t) @ R


def place(R, t):
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = t
    return T


class Fit:
    """One hand on one gun configuration at one placement (R, t: frame B -> the hand's rest world, mm)."""

    def __init__(self, hand, gun, R):
        self.h, self.g, self.R = hand, gun, R

    def gap(self, t, mask, names=None, cap=40.0):
        g, _o = signed_gap(to_B(self.h.skin()[mask], self.R, t), self.g, names, cap)
        return float(g.min())

    def worst(self, t, mask, names=None):
        """(gap, part, hand bone) of the mask's most-penetrating / nearest vertex (diagnostics)."""
        g, o = signed_gap(to_B(self.h.skin()[mask], self.R, t), self.g, names)
        k = int(np.argmin(g))
        return round(float(g[k]), 2), str(o[k]), str(self.h.main[mask][k])

    def push(self, t, direction, mask, names=None, target=CONTACT, lo=-40.0, hi=40.0):
        a, b = lo, hi
        ga, gb = self.gap(t + a * direction, mask, names), self.gap(t + b * direction, mask, names)
        if not (ga >= target >= gb):
            return t + (a if abs(ga - target) < abs(gb - target) else b) * direction, (round(ga, 3), round(gb, 3))
        for _ in range(24):
            m = 0.5 * (a + b)
            if self.gap(t + m * direction, mask, names) > target:
                a = m
            else:
                b = m
        return t + 0.5 * (a + b) * direction, None

    def chain_gap(self, t, chain, cap=25.0):
        mask = self.h.moved_mask([x.replace(self.h.s, "") for x in chain])
        g, own = signed_gap(to_B(self.h.skin()[mask], self.R, t), self.g, cap=cap)
        return float(g.min()), str(own[np.argmin(g)])

    def curl(self, t, finger, max_deg=100.0, joints=None):
        h = self.h
        chain = h.F[finger] if joints is None else joints
        sg = h.SIGN[finger]
        angles = {}
        for j, b in enumerate(chain):
            distal = chain[j:]
            a0 = h.OPEN.get(b, 0.0)
            h.set_rot(b, a0)
            g, _ = self.chain_gap(t, distal)
            ext = 0.0
            while g <= CURL_STOP and ext < 60.0:
                ext += 2.0
                h.set_rot(b, a0 - sg * ext)
                g, _ = self.chain_gap(t, distal)
            a0 = a0 - sg * ext
            ang, step = 0.0, 2.0
            while ang < max_deg:
                h.set_rot(b, a0 + sg * (ang + step))
                g, _ = self.chain_gap(t, distal)
                if g <= CURL_STOP:
                    if step <= 0.25:
                        break
                    step /= 4.0
                    continue
                ang += step
            h.set_rot(b, a0 + sg * ang)
            angles[b] = round(a0 + sg * ang, 2)
        return angles

    def thumb_clear(self, t, target_B=None):
        """thumb_01 turned out of the gun (10 deg grid about local X / Z to +-70) so the whole thumb is CURL_STOP off;
        with target_B (SR01) the clear pose whose tip is nearest that gun-surface point (the thumb wraps the grip's left
        side), otherwise the smallest rotation (the SMG's rule)."""
        pb = arm.pose.bones["thumb_01" + self.h.s]
        tipm = np.array([b_.startswith("thumb_03") for b_ in self.h.main])
        best = None
        for ax in range(-70, 71, 10):
            for az in range(-70, 71, 10):
                pb.rotation_quaternion = (Quaternion((1.0, 0.0, 0.0), math.radians(ax)) @
                                          Quaternion((0.0, 0.0, 1.0), math.radians(az)))
                g, _ = self.chain_gap(t, self.h.F["thumb"])
                if g >= CURL_STOP:
                    if target_B is None:
                        key = (abs(ax) + abs(az), g)
                    else:
                        tip = to_B(self.h.skin()[tipm], self.R, t).mean(0)
                        key = (float(np.linalg.norm(tip - target_B)), g)
                    if best is None or key < best[0]:
                        best = (key, ax, az, g)
        if best is None:
            pb.rotation_quaternion = Quaternion()
            return {pb.name: "no clear pose in the grid"}
        _, ax, az, g = best
        pb.rotation_quaternion = (Quaternion((1.0, 0.0, 0.0), math.radians(ax)) @
                                  Quaternion((0.0, 0.0, 1.0), math.radians(az)))
        return {pb.name: {"about_local_X_deg": ax, "about_local_Z_deg": az, "gap_mm": round(g, 3)}}


def tri_overlaps(hand, PHb, gun):
    th = bvh(PHb, hand.HT)
    out = {}
    for n, t in gun.tr.items():
        k = len(th.overlap(t))
        if k:
            out[n] = k
    return out


def check(hand, PHw, R, t, gun):
    PHb = to_B(PHw, R, t)
    ov = tri_overlaps(hand, PHb, gun)
    g, o = signed_gap(PHb, gun, cap=5.0)
    pen = {}
    for n in set(o[g < -0.01]):
        sel_ = (o == n) & (g < 0)
        k_ = np.nonzero(sel_)[0][np.argmin(g[sel_])]
        pen[n] = {"depth_mm": round(float(-g[k_]), 3), "hand_bone": str(hand.main[k_]), "vertices": int(sel_.sum())}
    return {"config": gun.label, "triangle_pairs": ov, "penetration_mm": pen, "min_gap_mm": round(float(g.min()), 3)}


# ================================================================================================ configurations
CONFIGS = [("rest", None, 0, True), ("bolt unlocked (turned)", "A_SR01_BoltCycle", 6, True),
           ("bolt back", "A_SR01_BoltCycle", 14, True), ("trigger pulled", "A_SR01_Fire", 2, True),
           ("safety SAFE", "A_SR01_Selector", 10, True), ("paddle pressed", "A_SR01_Reload", 3, True),
           ("magazine out", None, 0, False), ("cheek riser up", "A_SR01_CheekRiser", 8, True),
           ("cheek riser down", "A_SR01_CheekRiser", 18, True), ("bipod deployed", "A_SR01_BipodDeploy", 36, True)]
GUNS = {}
POSEVALS = {}
for label, clip, fr, mag in CONFIGS:
    parts, pv = gun_config(clip, fr, mag)
    GUNS[label] = Gun(parts, label)
    POSEVALS[label] = pv
log("configs", POSEVALS)
G0 = GUNS["rest"]
GD = GUNS["bipod deployed"]
out = {"body": LOCK["blend"], "body_sha256_locked": LOCK.get("blend_sha256"),
       "body_sha256_now": hashlib.sha256((ROOT / LOCK["blend"]).read_bytes()).hexdigest(),
       "gun_bytes": {n: hashlib.sha256((EXP / n).read_bytes()).hexdigest()
                     for n in ("SK_SR01.fbx", "SM_SR01_Mag.fbx", "SM_Att_Scope_LongRange.fbx",
                               "SK_SR01.skeletal.json", "SM_Att_Scope_LongRange.sockets.json")},
       "imported_frame_check_mm": round(frame_err, 4), "config_pose_values": POSEVALS}
out["body_sha256_matches_lock"] = out["body_sha256_now"] == out["body_sha256_locked"]

# ================================================================================================ 1. right hand on Grip
HR = Hand("r")
Yw = HR.n_palm / np.linalg.norm(HR.n_palm)
Dw = HR.k_ax - Yw * (HR.k_ax @ Yw)
Dw /= np.linalg.norm(Dw)
best = None
for sgn in (1.0, -1.0):
    Pw = sgn * np.cross(Yw, Dw)
    Xw = -math.sin(RHO) * Dw + math.cos(RHO) * Pw
    Zw = -math.cos(RHO) * Dw - math.sin(RHO) * Pw
    if np.cross(Xw, Yw) @ Zw > 0:
        best = (Xw, Zw)
Xw, Zw = best
RR = np.c_[Xw, Yw, Zw]
FR = Fit(HR, G0, RR)
GRIP_PARTS = ["body"]


trig_B = SOCK["Trigger"]
CORE = ~HR.fingers_mask & ~HR.moved_mask(["thumb"], wmin=0.2)
wp = D["frames"]["grip"]["web_point_M"]
hollow_B = np.array([wp[0], 0.0, wp[1]]) - GRIP


def pad_dist(tt):
    return float(np.linalg.norm(to_B(HR.skin()[HR.pad_mask], RR, tt) - trig_B, axis=1).min())


def seat_web(ax_off, bx):
    """(SR01) the web landmark (index_01 / thumb_02 heads' midpoint) on the spec web point (the back strap's hollow),
    moved ax_off along the grip and bx back into the web (the gun's -X), then the gun pushed along -Y until the palm's
    metacarpal skin is 0.3 mm off the grip. The SMG's contact rules (thenar / web 0.3 mm off the back strap) cannot be
    met here: MH_PlayerDefault's rest thumb lies across the grip's left side and its web stays in the palm plane beside
    the back strap (runs 1-4 of this script: thenar 9.5 mm inside at every push, the web never within 2.8 mm of the
    back strap over a 60 mm sweep); thumb_clear then turns the thumb out."""
    t0 = HR.web - RR @ hollow_B + Dw * ax_off + bx * (-Xw)
    tt, note = FR.push(t0 + Yw * 30.0, -Yw, HR.side_mask, GRIP_PARTS, lo=-30.0, hi=60.0)
    return tt, {"side_gap": round(FR.gap(tt, HR.side_mask, GRIP_PARTS), 3),
                "web_gap": round(FR.gap(tt, HR.web_mask, GRIP_PARTS), 3), "note": note}


log("placing the grip in the right palm (web on the hollow, palm side contact)")
rec_push = []
cands = []
for ax_off in (0.0, -6.0, 6.0, -12.0, 12.0):
    for bx in (0.0, 4.0, 8.0):
        tt, last = seat_web(ax_off, bx)
        cg, ig, fg = FR.gap(tt, CORE), FR.gap(tt, HR.idx_base_mask), FR.gap(tt, HR.fingers_mask)
        r_ = {"axial_offset_mm": ax_off, "back_offset_mm": bx, "last": last, "core_palm_gap": round(cg, 3),
              "index_base_gap": round(ig, 3), "open_fingers_gap": round(fg, 3),
              "open_pad_to_trigger_mm": round(pad_dist(tt), 2), "worst_core": FR.worst(tt, CORE)}
        r_["converged"] = abs(last["side_gap"] - CONTACT) < 0.15
        r_["clear"] = r_["converged"] and cg >= -1.0 and ig >= CONTACT - 0.05 and fg >= 0.0
        rec_push.append(r_)
        cands.append((r_, tt))
        log("seat", r_)
# the SMG's stated rule: the palm centre (wrist / knuckle midpoint) on the Grip origin; fore-aft (gun X) and axial
# offsets tried in 4 mm steps, the gun then pushed along -Y to the palm contact; the clear seat nearest the rule is used
palm_cands = []
for ax_off in (0.0, -4.0, 4.0, -8.0, 8.0):
    for bx in (0.0, -4.0, 4.0, -8.0, 8.0):
        t0 = HR.palm_c + Dw * ax_off + bx * (-Xw)
        tt, note = FR.push(t0 + Yw * 30.0, -Yw, HR.side_mask, GRIP_PARTS, lo=-30.0, hi=60.0)
        sg_ = FR.gap(tt, HR.side_mask, GRIP_PARTS)
        cg, ig, fg = FR.gap(tt, CORE), FR.gap(tt, HR.idx_base_mask), FR.gap(tt, HR.fingers_mask)
        r_ = {"rule": "palm centre on Grip", "axial_offset_mm": ax_off, "back_offset_mm": bx,
              "last": {"side_gap": round(sg_, 3), "web_gap": round(FR.gap(tt, HR.web_mask, GRIP_PARTS), 3), "note": note},
              "core_palm_gap": round(cg, 3), "index_base_gap": round(ig, 3), "open_fingers_gap": round(fg, 3),
              "open_pad_to_trigger_mm": round(pad_dist(tt), 2), "worst_core": FR.worst(tt, CORE)}
        r_["clear"] = abs(sg_ - CONTACT) < 0.15 and cg >= -1.0 and ig >= CONTACT - 0.05 and fg >= 0.0
        rec_push.append(r_)
        palm_cands.append((r_, tt))
        log("seat", r_)
pclear = [c for c in palm_cands if c[0]["clear"]]
if pclear:
    r_, t_r = min(pclear, key=lambda c: (abs(c[0]["axial_offset_mm"]) + abs(c[0]["back_offset_mm"]),
                                          c[0]["open_pad_to_trigger_mm"]))
    seat_used = (f"palm centre on Grip, axial offset {r_['axial_offset_mm']} mm, back {r_['back_offset_mm']} mm "
                 f"(the clear seat nearest the SMG's rule)")
else:
    clear = [c for c in cands if c[0]["clear"]]
    if clear:
        r_, t_r = min(clear, key=lambda c: (round(c[0]["last"]["web_gap"], 1), c[0]["open_pad_to_trigger_mm"]))
        seat_used = (f"web on the hollow, axial offset {r_['axial_offset_mm']} mm, back {r_['back_offset_mm']} mm "
                     f"(clear, the web snuggest in the hollow)")
    else:
        r_, t_r = max(cands, key=lambda c: min(c[0]["core_palm_gap"] + 1.0, c[0]["index_base_gap"], c[0]["open_fingers_gap"]))
        seat_used = f"no seat fully clear: best axial offset {r_['axial_offset_mm']} mm"
_h = G0.tr["body"].ray_cast(Vector((hollow_B[0] - 12.0, 80.0, hollow_B[2] - 28.0)), Vector((0.0, -1.0, 0.0)), 200.0)
THUMB_T = np.array(_h[0]) if _h[0] is not None else hollow_B + np.array([-12.0, 16.0, -28.0])
log("thumb target (grip left face)", THUMB_T.round(1))
# (SR01) the thumb must be able to wrap the grip's left side: in a seat whose web lies beside the back strap the only
# clear thumb poses point forward along the gun's right side (run 11's renders). The leading clear seats (the one
# chosen above first, then the web-on-hollow seats snuggest first, then the other palm-centre seats nearest the rule)
# are tried with the open hand: the first whose clear thumb tip reaches the left face (B Y > +8 mm) is used.
TIPM = np.array([b_.startswith("thumb_03") for b_ in HR.main])


def thumb_wraps(tt_):
    HR.open_hand()
    res_ = FR.thumb_clear(tt_, THUMB_T)
    tip_ = to_B(HR.skin()[TIPM], RR, tt_).mean(0)
    HR.open_hand()
    return float(tip_[1]), res_


def rot_axis(ax_, deg):
    ax_ = ax_ / np.linalg.norm(ax_)
    K = np.array([[0.0, -ax_[2], ax_[1]], [ax_[2], 0.0, -ax_[0]], [-ax_[1], ax_[0], 0.0]])
    a_ = math.radians(deg)
    return np.eye(3) + math.sin(a_) * K + (1.0 - math.cos(a_)) * K @ K


# the hand turned about the grip axis by phi (the back strap into the web, the palm facing forward-left as in a real
# pistol-grip hold); each phi with the palm centre on the Grip origin and 0 / 6 / 12 mm back, pushed toward the palm
thumb_trials = []
chosen = None
FR0 = FR
for phi in (0.0, 15.0, -15.0, 30.0, -30.0, 45.0, -45.0):
    Rp = rot_axis(Dw, phi) @ RR
    Fp = Fit(HR, G0, Rp)
    for bx in (0.0, 6.0, 12.0):
        HR.open_hand()
        t0 = HR.palm_c + bx * (-Rp[:, 0])
        FR = Fp
        tt_, note_ = Fp.push(t0 + Yw * 30.0, -Yw, HR.side_mask, GRIP_PARTS, lo=-40.0, hi=60.0)
        sg_ = Fp.gap(tt_, HR.side_mask, GRIP_PARTS)
        cg, ig, fg = Fp.gap(tt_, CORE), Fp.gap(tt_, HR.idx_base_mask), Fp.gap(tt_, HR.fingers_mask)
        clear_ = abs(sg_ - CONTACT) < 0.15 and cg >= -1.0 and ig >= CONTACT - 0.05 and fg >= 0.0
        rec_ = {"phi_deg": phi, "back_offset_mm": bx, "side_gap": round(sg_, 3), "core_palm_gap": round(cg, 3),
                "index_base_gap": round(ig, 3), "open_fingers_gap": round(fg, 3), "clear": clear_, "note": note_}
        if clear_:
            ty_, res_ = thumb_wraps(tt_)
            rec_.update({"thumb_tip_Y_B_mm": round(ty_, 1), "thumb": res_,
                         "open_pad_to_trigger_mm": round(float(np.linalg.norm(
                             to_B(HR.skin()[HR.pad_mask], Rp, tt_) - trig_B, axis=1).min()), 2)})
        thumb_trials.append(rec_)
        log("phi trial", rec_)
        if clear_ and rec_["thumb_tip_Y_B_mm"] > 8.0:
            chosen = (phi, bx, Rp, tt_)
            break
    if chosen:
        break
FR = FR0
if chosen:
    phi, bx, RR, t_r = chosen
    Xw, Yw_g, Zw = RR[:, 0], RR[:, 1], RR[:, 2]
    FR = Fit(HR, G0, RR)
    seat_used = (f"palm centre on Grip, hand turned {phi} deg about the grip axis, {bx} mm back (the least turn whose "
                 f"clear thumb wraps the grip's left side)")
else:
    seat_used += " (no hand turn up to 45 deg lets the thumb wrap the grip's left side)"
log("seat used", seat_used)
TgR = place(RR, t_r)
STAGE = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
DBG = WORK / "scratch" / "h1"


def hold_render(tag, R, t, gun, centre_B):
    """Debug: the gun at the hold placement around the resting hand (scratch only)."""
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.render.resolution_x, sc.render.resolution_y = 900, 750
    objs = []
    T = place(R, t)
    T[:3, 3] *= 0.001
    for n, (V, Tt) in gun.P.items():
        m = bpy.data.meshes.new("dbg_" + n)
        m.from_pydata((V * 0.001).tolist(), [], Tt.tolist())
        o = bpy.data.objects.new("dbg_" + n, m)
        sc.collection.objects.link(o)
        o.matrix_world = Matrix(T.tolist())
        objs.append(o)
    for o in IMPORTED:
        o.hide_render = True
    cam = bpy.data.objects.new("dbgcam", bpy.data.cameras.new("dbgcam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 0.26
    c = (R @ centre_B + t) * 0.001
    for k, off, up in (("gunright", -R[:, 1], R[:, 2]), ("gunleft", R[:, 1], R[:, 2]), ("under", -R[:, 2], R[:, 0])):
        cam.location = Vector((c + off * 0.6).tolist())
        zc = off / np.linalg.norm(off)                     # camera +Z points back at the viewer
        yc = up - zc * (up @ zc)
        yc /= np.linalg.norm(yc)
        cam.rotation_euler = Matrix(np.c_[np.cross(yc, zc), yc, zc].tolist()).to_euler()
        sc.render.filepath = str(DBG / f"dbg_{tag}_{k}.png")
        bpy.ops.render.render(write_still=True)
    for o in objs + [cam]:
        bpy.data.objects.remove(o, do_unlink=True)


if "seat" in STAGE:
    hold_render("seat", RR, t_r, G0, np.array([20.0, 0.0, 0.0]))
    log("STAGE seat done")
    sys.exit(0)
POSE_R = {}
for fn in ("middle", "ring", "pinky"):
    POSE_R.update(FR.curl(t_r, fn))
    log("curl", fn, FR.chain_gap(t_r, HR.F[fn]))
POSE_R.update(FR.thumb_clear(t_r, THUMB_T))
POSE_R.update(FR.curl(t_r, "thumb", joints=["thumb_02_r", "thumb_03_r"], max_deg=40.0))


def index_to_trigger(t):
    chain = HR.F["index"]
    mask = HR.moved_mask([x.replace("_r", "") for x in chain])
    pad = HR.pad_mask
    others = [n for n in G0.P if n != "trigger"]
    sg = HR.SIGN["index"]

    def pose(q1, a, q2):
        arm.pose.bones[chain[0]].rotation_quaternion = (
            Quaternion((1.0, 0.0, 0.0), math.radians(a)) @
            Quaternion((0.0, 0.0, 1.0), math.radians(HR.OPEN[chain[0]] + sg * q1)))
        HR.set_rot(chain[1], HR.OPEN[chain[1]] + sg * q2)
        HR.set_rot(chain[2], HR.OPEN[chain[2]] + sg * 0.7 * q2)

    def score(q1, a, q2):
        pose(q1, a, q2)
        PHb = to_B(HR.skin(), RR, t)
        g, _ = signed_gap(PHb[mask], G0, others, cap=8.0)
        if g.min() < 0.0:
            return None
        gt, _ = signed_gap(PHb[pad], G0, ["trigger"], cap=30.0)
        if gt.min() < CURL_STOP:
            return None
        k_ = int(np.argmin(gt))
        if (PHb[pad][k_] - trig_B)[0] < -2.0:
            return None
        return (float(gt.min()) + 0.01 * float(np.linalg.norm(PHb[pad] - trig_B, axis=1).min()), float(g.min()),
                float(gt.min()))
    bst = None
    for q1 in range(-30, 71, 10):
        for a in range(-40, 21, 10):
            for q2 in range(0, 101, 10):
                r = score(q1, a, q2)
                if r is not None and (bst is None or r[0] < bst[0][0]):
                    bst = (r, q1, a, q2)
    if bst is None:
        return {"index": "no clear pose"}, None
    _, q1b, ab, q2b = bst
    for q1 in np.arange(q1b - 7.5, q1b + 7.6, 2.5):
        for a in np.arange(ab - 7.5, ab + 7.6, 2.5):
            for q2 in np.arange(max(0.0, q2b - 7.5), q2b + 7.6, 2.5):
                r = score(q1, a, q2)
                if r is not None and r[0] < bst[0][0]:
                    bst = (r, q1, a, q2)
    (_dp, g, gt), q1, a, q2 = bst
    pose(q1, a, q2)
    return ({"index_01_r": {"curl_deg": round(float(HR.OPEN[chain[0]] + sg * q1), 2),
                            "abduction_deg_about_local_X": float(a)},
             "index_02_r": round(float(HR.OPEN[chain[1]] + sg * q2), 2),
             "index_03_r": round(float(HR.OPEN[chain[2]] + sg * 0.7 * q2), 2)},
            {"pad_to_trigger_surface_mm": round(gt, 3), "gap_to_frame_mm": round(g, 3)})


log("trigger finger search")
ip, IDX = index_to_trigger(t_r)
POSE_R.update(ip)
log("index", ip, IDX)
PHR = HR.skin()
POSE_R_Q = HR.finger_pose()
gp, _ = signed_gap(to_B(PHR[HR.palm_mask], RR, t_r), G0, GRIP_PARTS)
out["right_palm"] = {"min_signed_gap_mm": round(float(gp.min()), 3), "penetration_mm": round(max(0.0, -float(gp.min())), 3),
                     "threshold": "<= 1 mm", "pass": -float(gp.min()) <= 1.0}
PB = to_B(PHR[HR.pad_mask], RR, t_r)
gi_, oi_ = signed_gap(PB, G0)
gtr, _ = signed_gap(PB, G0, ["trigger"])
out["index"] = {"pad_to_trigger_face_mm": round(float(gtr.min()), 3),
                "pad_to_trigger_socket_point_mm": round(float(np.linalg.norm(PB - trig_B, axis=1).min()), 2),
                "nearest_part": str(oi_[np.argmin(gi_)]), "nearest_gap_mm": round(float(gi_.min()), 3), "search": IDX,
                "threshold": "the index pad within 3 mm of the trigger face at the rest curl, the finger clear of the frame",
                "pass": 0.0 <= float(gtr.min()) <= 3.0}
out["right_seat"] = {"used": seat_used, "pushes": rec_push, "thumb_trials": thumb_trials}
out["right_clip_extremes"] = [check(HR, PHR, RR, t_r, GUNS[c[0]]) for c in CONFIGS]
for c in out["right_clip_extremes"]:
    log("R extreme", c)
if "right" in STAGE:
    hold_render("right", RR, t_r, G0, np.array([20.0, 0.0, 0.0]))
    (DBG / "right_stage.json").write_text(json.dumps(out, indent=1, default=str))
    log("STAGE right done")
    sys.exit(0)

# ================================================================================================ 2. left hand, palm up
HL = Hand("l")
Zl = HL.n_palm / np.linalg.norm(HL.n_palm)
Xl = -HL.k_ax + Zl * (HL.k_ax @ Zl)
Xl /= np.linalg.norm(Xl)
Yl = np.cross(Zl, Xl)
if HL.f_ax @ Yl > 0:                              # the fingers wrap the gun's right side (-Y), the thumb its left
    Xl, Yl = -Xl, -Yl
RL = np.c_[Xl, Yl, Zl]
log("left frame: fingers . gun Y", round(float(HL.f_ax @ Yl), 3), "det", round(float(np.linalg.det(RL)), 3))


def support_fit(sock, gun, tag):
    HL.open_hand()
    F = Fit(HL, gun, RL)
    t = HL.palm_c + Zl * 40.0 - RL @ sock
    t, note = F.push(t, -Zl, HL.palm_mask, lo=-150.0, hi=60.0)
    pose = {}
    for fn in ("index", "middle", "ring", "pinky"):
        pose.update(F.curl(t, fn))
    pose.update(F.thumb_clear(t))
    pose.update(F.curl(t, "thumb", joints=["thumb_02_l", "thumb_03_l"], max_deg=60.0))
    PH = HL.skin()
    gp_, _ = signed_gap(to_B(PH[HL.palm_mask], RL, t), gun)
    palm_B = to_B(HL.palm_c[None], RL, t)[0]
    # the gun surface point under the seated palm centre (straight down the palm normal = gun -Z ... up from the palm)
    hit = gun.tr
    surf = None
    for n in gun.P:
        h = gun.tr[n].ray_cast(Vector(palm_B.tolist()), Vector((0.0, 0.0, 1.0)), 400.0)
        if h[0] is not None and (surf is None or h[3] < surf[1]):
            surf = (np.array(h[0]), h[3], n)
    del hit
    rec = {"socket": tag, "socket_B_mm": sock.round(2).tolist(), "push_note": note,
           "palm_min_signed_gap_mm": round(float(gp_.min()), 3),
           "palm_penetration_mm": round(max(0.0, -float(gp_.min())), 3), "palm_pass": -float(gp_.min()) <= 1.0,
           "palm_centre_B_mm": palm_B.round(2).tolist(),
           "surface_over_palm_centre_B_mm": None if surf is None else surf[0].round(2).tolist(),
           "surface_part": None if surf is None else surf[2],
           "socket_to_surface_point_mm": None if surf is None else round(float(np.linalg.norm(surf[0] - sock)), 2),
           "pose_deg": pose}
    log("support", tag, {k: v for k, v in rec.items() if k != "pose_deg"})
    return t, PH, rec, HL.finger_pose()


t_la, PHLA, recA, POSE_LA_Q = support_fit(SOCK["SupportHand"], G0, "SupportHand")
recA["clip_extremes"] = [check(HL, PHLA, RL, t_la, GUNS[c[0]]) for c in CONFIGS if c[0] != "bipod deployed"]
t_lb, PHLB, recB, POSE_LB_Q = support_fit(SOCK["SupportHandBipod"], GD, "SupportHandBipod")
recB["clip_extremes"] = [check(HL, PHLB, RL, t_lb, GUNS[c[0]]) for c in CONFIGS if c[0] in
                         ("bipod deployed", "bolt back", "bolt unlocked (turned)", "trigger pulled", "cheek riser up",
                          "cheek riser down", "magazine out")]
out["left_A_SupportHand"] = recA
out["left_B_SupportHandBipod"] = recB


def inter(lst):
    return sorted(c["config"] for c in lst if c["triangle_pairs"] or c["penetration_mm"])


out["intersections"] = {"right": inter(out["right_clip_extremes"]), "left_A": inter(recA["clip_extremes"]),
                        "left_B": inter(recB["clip_extremes"])}
out["intersections"]["pass"] = not any(out["intersections"][k] for k in ("right", "left_A", "left_B"))

# ================================================================================================ 3. eye, cheek weld, IK
hp = headparts.data
Vhp = np.array([v.co for v in hp.vertices]) * 1000.0
Vhp = (np.c_[Vhp * 0.001, np.ones(len(Vhp))] @ np.array(headparts.matrix_world).T)[:, :3] * 1000.0
par = list(range(len(Vhp)))


def find(a):
    while par[a] != a:
        par[a] = par[par[a]]
        a = par[a]
    return a


for e in hp.edges:
    a, b = find(e.vertices[0]), find(e.vertices[1])
    if a != b:
        par[a] = b
isl = {}
for i in range(len(Vhp)):
    isl.setdefault(find(i), []).append(i)
eye_isl = None
for k, ids in isl.items():
    P = Vhp[ids]
    ext = np.ptp(P, 0)
    c = P.mean(0)
    if c[0] < -10.0 and np.all((ext > 17.0) & (ext < 32.0)):
        if eye_isl is None or P[:, 1].min() < eye_isl[1][:, 1].min():
            eye_isl = (k, P)
if eye_isl is not None:
    P = eye_isl[1]
    eye_c = 0.5 * (P.min(0) + P.max(0))
    eye = np.array([eye_c[0], P[:, 1].min(), eye_c[2]])          # the cornea front on the eye's axis
    eye_src = f"right eyeball island of FIT_MH_PlayerDefault_HeadParts ({len(P)} verts): centre {eye_c.round(1).tolist()}"
else:
    eye = bone_head("head") + np.array([-32.0, -95.0, 85.0])
    eye_src = "fallback: the SMG's head-joint offset"
log("eye", eye.round(1), eye_src)
Rg = np.array([[0.0, 1.0, 0.0], [-1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])   # gun X -> world -Y (front), Y -> +X, Z up
t_ads = eye - Rg @ EYEPOINT_B
Tads = place(Rg, t_ads)


def two_bone(S, L1, L2, T):
    d = float(np.linalg.norm(T - S))
    reach = L1 + L2
    resid = max(0.0, d - reach)
    dd = min(d, reach - 1e-6)
    cos_e = (L1 * L1 + L2 * L2 - dd * dd) / (2 * L1 * L2)
    inner = math.degrees(math.acos(max(-1.0, min(1.0, cos_e))))
    return {"distance_mm": round(d, 1), "reach_mm": round(reach, 1), "residual_mm": round(resid, 3),
            "elbow_flexion_deg": round(180.0 - inner, 1), "pass": resid < 0.5 and 0.0 <= 180.0 - inner <= 150.0}


def arm_ik(side, Tg_hold):
    s = "_" + side
    S = bone_head("upperarm" + s)
    E = bone_head("lowerarm" + s)
    W = bone_head("hand" + s)
    tgt = (Tads @ np.linalg.inv(Tg_hold) @ np.r_[W, 1.0])[:3]
    return two_bone(S, float(np.linalg.norm(E - S)), float(np.linalg.norm(W - E)), tgt), tgt


TgLA, TgLB = place(RL, t_la), place(RL, t_lb)
ikR, wR = arm_ik("r", TgR)
ikLA, wLA = arm_ik("l", TgLA)
ikLB, wLB = arm_ik("l", TgLB)
out["ik_right"] = dict(ikR, what="right arm to the held grip, the scope's EyePoint on the right eye")
out["ik_left_A"] = dict(ikLA, what="left arm to the seated SupportHand hold")
out["ik_left_B"] = dict(ikLB, what="left arm to the seated SupportHandBipod hold (upper body as standing: proxy for prone)")


def left_reach(Tg_hold, dx=0.0, yaw=0.0):
    """residual of the left arm with the hold slid dx along the gun's X and the shoulders yawed (deg, left forward)
    about the vertical through spine_05 (a bladed stance; the head and the gun stay)"""
    S, E, W = bone_head("upperarm_l"), bone_head("lowerarm_l"), bone_head("hand_l")
    tgt = (Tads @ np.linalg.inv(Tg_hold) @ np.r_[W, 1.0])[:3] + Rg @ np.array([dx, 0.0, 0.0])
    c = bone_head("spine_05")
    a_ = math.radians(yaw)
    Rz = np.array([[math.cos(a_), -math.sin(a_), 0.0], [math.sin(a_), math.cos(a_), 0.0], [0.0, 0.0, 1.0]])
    S2 = Rz @ (S - c) + c
    return two_bone(S2, float(np.linalg.norm(E - S)), float(np.linalg.norm(W - E)), tgt)


lo_, hi_ = -400.0, 0.0
for _ in range(30):
    m_ = 0.5 * (lo_ + hi_)
    if left_reach(TgLA, dx=m_)["residual_mm"] > 0.0:
        hi_ = m_
    else:
        lo_ = m_
yaw_need = None
for yw in range(0, 61, 1):
    for sg_ in (1.0, -1.0):
        if left_reach(TgLA, yaw=sg_ * yw)["residual_mm"] <= 0.0:
            yaw_need = sg_ * yw
            break
    if yaw_need is not None:
        break
out["left_A_reach"] = {"SupportHand_X_B_now_mm": float(SOCK["SupportHand"][0]),
                       "farthest_reachable_SupportHand_X_B_square_stance_mm": round(float(SOCK["SupportHand"][0] + lo_), 1),
                       "shortfall_mm": round(float(-lo_), 1),
                       "shoulder_yaw_that_reaches_deg": yaw_need,
                       "at_that_yaw": None if yaw_need is None else left_reach(TgLA, yaw=yaw_need),
                       "note": "square stance = the fit body's rest torso facing the target with the bore under the right "
                               "eye (the SMG's assumption); real standing / kneeling holds blade the torso, which brings "
                               "the left shoulder forward"}
log("left A reach", out["left_A_reach"])

# ---- the static measurements on the shipped bytes
Vb, Tb = G0.P["body"]
Vt, _ = G0.P["trigger"]
face_z = 21.13                                         # the W1 early H1's blade height (Z -75 in M)
tsel = np.abs(Vt[:, 2] - face_z) < 1.0
trig_face_x = float(Vt[tsel, 0].min()) if tsel.any() else float(trig_B[0])
butt_x = float(Vb[:, 0].min())
lop = trig_face_x - butt_x
reach = math.hypot(trig_face_x - hollow_B[0], face_z - hollow_B[2])


def section_perimeter(V, T, p0, n, rmax):
    """Length of the plane section of a triangle soup within rmax of p0 (numpy)."""
    dd = (V - p0) @ n
    tot = 0.0
    for tri in T:
        s = dd[tri]
        if (s > 0).all() or (s < 0).all():
            continue
        pts = []
        for i, j in ((0, 1), (1, 2), (2, 0)):
            a, b = s[i], s[j]
            if (a > 0) != (b > 0):
                u = a / (a - b)
                pts.append(V[tri[i]] + u * (V[tri[j]] - V[tri[i]]))
        if len(pts) == 2 and np.linalg.norm(0.5 * (pts[0] + pts[1]) - p0) < rmax:
            tot += float(np.linalg.norm(pts[1] - pts[0]))
    return tot


n_up = np.array([math.sin(RHO), 0.0, math.cos(RHO)])
near = np.all(np.abs(Vb - hollow_B) < 160.0, axis=1)
tsub = Tb[near[Tb].all(1)]
girth = {}
for dep in (25.0, 46.0, 70.0):
    girth[f"at_{int(dep)}mm"] = round(section_perimeter(Vb, tsub, hollow_B - n_up * dep, n_up, 45.0), 1)
scope_rear_x = float(SCO_V[:, 0].min())
riser = G0.P.get("cheek_riser")
# cheek: the face (FIT head mesh) over the riser's footprint with the eye on EyePoint
Vh = np.array([v.co for v in headm.data.vertices])
Vh = (np.c_[Vh, np.ones(len(Vh))] @ np.array(headm.matrix_world).T)[:, :3] * 1000.0
VhB = (Vh - t_ads) @ Rg
cheek = {}
htri = []
for p_ in headm.data.polygons:
    vs = list(p_.vertices)
    htri += [vs[:3]] + ([[vs[0], vs[2], vs[3]]] if len(vs) == 4 else [])
htree = bvh(VhB, np.array(htri))


HDIRS = [Vector((0.0, 1.0, 0.0)), Vector((0.0, -1.0, 0.0)), Vector((-1.0, 0.0, 0.0))]


def face_gap(tr_, st):
    """the comb-top point st's gap to the face (frame B): inside (parity on three horizontal rays, which leave the head
    sideways or backward, never through its open neck) = -(distance to the nearest skin); outside = the upward ray's
    distance to the skin it enters (None when it meets no skin)"""
    odd = 0
    for dv in HDIRS:
        k, q = 0, st.copy()
        for _ in range(64):
            hh = tr_.ray_cast(q + dv * 1e-4, dv, 1000.0)
            if hh[0] is None:
                break
            k += 1
            q = hh[0]
        odd += k % 2
    if odd >= 2:
        n_ = tr_.find_nearest(st, 400.0)
        return -(n_[3] if n_[0] is not None else 0.0)
    h_ = tr_.ray_cast(st, Vector((0.0, 0.0, 1.0)), 400.0)
    return None if h_[0] is None else h_[3]

if riser is not None:
    Vr = riser[0]
    top = float(Vr[:, 2].max())
    topv = Vr[Vr[:, 2] > top - 3.0]
    x0, x1 = float(topv[:, 0].min()), float(topv[:, 0].max())
    yh = float(np.abs(topv[:, 1]).max())
    best_c = None
    prof = {}
    for xx in np.arange(x0 + 2.0, x1 - 1.9, 4.0):
        for yy in np.arange(-yh + 2.0, yh - 1.9, 4.0):
            g_ = face_gap(htree, Vector((float(xx), float(yy), top)))
            if g_ is None:
                continue
            kx = round(float(EYEPOINT_B[0] - xx), 0)
            prof[kx] = min(prof.get(kx, 1e9), g_)
            if best_c is None or g_ < best_c[0]:
                best_c = (g_, np.array([xx, yy, top + max(g_, 0.0)]))
    rr = SKJ["gun"]["cheek_riser_mm"]
    cheek = {"riser_top_Z_B_mm": round(top, 2), "riser_top_X_B_mm": [round(x0, 1), round(x1, 1)],
             "riser_top_half_width_mm": round(yh, 1), "eye_over_riser_top_mm": round(float(EYEPOINT_B[2] - top), 2),
             "rule": "rays straight up from a 4 mm grid on the riser's top face to the FIT head mesh, the eye on "
                     "EyePoint, bore level, the head upright and neutral; the smallest gap = the raise that brings the "
                     "comb to the face (negative = the face would sit inside the rest riser)"}
    cheek["gap_by_distance_behind_the_eye_mm"] = [[k_, round(v_, 1)] for k_, v_ in sorted(prof.items())]
    if best_c is not None:
        need = float(best_c[0])
        cheek.update({"face_gap_over_riser_mm": round(need, 2), "face_contact_point_B_mm": best_c[1].round(1).tolist(),
                      "riser_raise_needed_mm": round(need, 2), "riser_travel_mm": rr,
                      "within_travel": rr[0] <= need <= rr[1]})
    else:
        cheek["note"] = "no face over the riser's top face in this pose"
# shoulder pocket: the chest skin between the clavicle head and the shoulder joint, straight behind (world +Y)
Vbd = VREST
btri = []
for p_ in me_body.polygons:
    vs = list(p_.vertices)
    btri += [vs[:3]] + ([[vs[0], vs[2], vs[3]]] if len(vs) == 4 else [])
btree = bvh(Vbd, np.array(btri))
sh_w = Rg @ SOCK["Shoulder"] + t_ads
pk0 = np.array([0.5 * (bone_head("clavicle_r")[0] + bone_head("upperarm_r")[0]), -400.0, bone_head("upperarm_r")[2] - 10.0])
h = btree.ray_cast(Vector(pk0.tolist()), Vector((0.0, 1.0, 0.0)), 1500.0)
pocket = {"butt_pad_centre_world_mm": sh_w.round(1).tolist()}
if h[0] is not None:
    P_ = np.array(h[0])
    dvec = P_ - sh_w
    pocket.update({"pocket_skin_world_mm": P_.round(1).tolist(),
                   "pocket_rule": "the front skin straight ahead of the point midway between the clavicle head and the "
                                  "right shoulder joint, 10 mm below the joint",
                   "butt_to_pocket_mm": {"down": round(float(-dvec[2]), 1), "toward_right": round(float(-dvec[0]), 1),
                                         "back": round(float(dvec[1]), 1)},
                   "eye_relief_if_the_butt_slides_back_to_the_pocket_mm": round(float(SIGHT_B[0] - EYEPOINT_B[0])
                                                                                - float(dvec[1]), 1),
                   "how": "with the eye on EyePoint and the head upright the butt pad sits 'down' mm above and "
                          "'toward_right' mm left of the pocket: the shooter closes it by dropping the head onto the "
                          "comb, canting the head and raising the shoulder (the real cheek weld); fore-aft, a butt "
                          "'back' mm in front of the pocket means the eye ends that much nearer the eyepiece"})
else:
    pocket["note"] = "no chest skin found ahead of the pocket point"
# ---- cheek-weld head pose (SR01): the head (and its eye) rotated about the neck base by a cant (right ear down,
# about the forward axis) and a pitch (nod forward), the torso fixed, the gun kept level and straight at the moved eye;
# the face's gap over the riser top by upward rays. The pose used: the least tilt whose face clears the riser at its
# lowest setting and touches it inside the travel (raise = the gap at the rest setting)
NECK = bone_head("neck_01")
HT_ = np.array(htri)

rr = SKJ["gun"]["cheek_riser_mm"]


def head_rot(cant, pitch):
    c_, p_ = math.radians(cant), math.radians(pitch)
    Ry = np.array([[math.cos(c_), 0.0, math.sin(c_)], [0.0, 1.0, 0.0], [-math.sin(c_), 0.0, math.cos(c_)]])
    Rx = np.array([[1.0, 0.0, 0.0], [0.0, math.cos(p_), math.sin(p_)], [0.0, -math.sin(p_), math.cos(p_)]])
    return Rx @ Ry


def riser_gap(cant, pitch):
    Rh = head_rot(cant, pitch)
    eye2 = Rh @ (eye - NECK) + NECK
    t2_ = eye2 - Rg @ EYEPOINT_B
    VB = ((Rh @ (Vh - NECK).T).T + NECK - t2_) @ Rg
    tr_ = bvh(VB, HT_)
    best_ = None
    for xx in np.arange(x0 + 2.0, x1 - 1.9, 6.0):
        for yy in np.arange(-yh + 2.0, yh - 1.9, 6.0):
            g_ = face_gap(tr_, Vector((float(xx), float(yy), top)))
            if g_ is None:
                continue
            if best_ is None or g_ < best_[0]:
                best_ = (g_, [round(float(xx), 1), round(float(yy), 1)])
    return best_, eye2, t2_


weld = None
grid = []
if riser is not None:
    for cant in np.arange(0.0, 40.1, 2.5):
        for pitch in np.arange(0.0, 40.1, 2.5):
            b_, e2, t2_ = riser_gap(cant, pitch)
            if b_ is None:
                continue
            grid.append([float(cant), float(pitch), round(float(b_[0]), 2)])
            if rr[0] <= b_[0] <= rr[1] and (weld is None or cant + pitch < weld["cant_deg"] + weld["pitch_deg"]):
                weld = {"cant_deg": float(cant), "pitch_deg": float(pitch), "riser_raise_needed_mm": round(float(b_[0]), 2),
                        "contact_XY_B_mm": b_[1], "eye_world_mm": e2.round(1).tolist(), "_t": t2_}
if weld is not None:
    t_w = weld.pop("_t")
    sh_w2 = Rg @ SOCK["Shoulder"] + t_w
    if h[0] is not None:
        d2 = np.array(h[0]) - sh_w2
        weld["butt_to_pocket_mm"] = {"down": round(float(-d2[2]), 1), "toward_right": round(float(-d2[0]), 1),
                                     "back": round(float(d2[1]), 1)}
        weld["eye_relief_if_the_butt_slides_back_to_the_pocket_mm"] = round(float(SIGHT_B[0] - EYEPOINT_B[0])
                                                                            - float(d2[1]), 1)
    Tads_w = place(Rg, t_w)
    weld["ik_right"] = two_bone(bone_head("upperarm_r"), float(np.linalg.norm(bone_head("lowerarm_r") - bone_head("upperarm_r"))),
                                float(np.linalg.norm(bone_head("hand_r") - bone_head("lowerarm_r"))),
                                (Tads_w @ np.linalg.inv(TgR) @ np.r_[bone_head("hand_r"), 1.0])[:3])
    for tg_, nm_ in ((TgLA, "ik_left_A"), (TgLB, "ik_left_B")):
        weld[nm_] = two_bone(bone_head("upperarm_l"), float(np.linalg.norm(bone_head("lowerarm_l") - bone_head("upperarm_l"))),
                             float(np.linalg.norm(bone_head("hand_l") - bone_head("lowerarm_l"))),
                             (Tads_w @ np.linalg.inv(tg_) @ np.r_[bone_head("hand_l"), 1.0])[:3])
if weld is None and grid:
    bst_ = max(grid, key=lambda r: r[2])
    cheek["cheek_weld_head_pose"] = {"found": False, "least_penetrating_pose_cant_pitch_gap": bst_,
                                     "note": "no cant / pitch up to 40 deg puts the face on the riser inside its travel; "
                                             "the least-penetrating pose's gap is the riser change it would need"}
else:
    cheek["cheek_weld_head_pose"] = weld
cheek["cheek_weld_rule"] = ("head rotated about neck_01's head (cant = right ear down about the forward axis, then pitch = "
                            "nod forward), torso fixed, the gun level and straight with EyePoint on the moved eye; the pose "
                            "with the least cant + pitch whose face-to-riser gap lies inside the riser travel (the raise "
                            "that brings the comb to the cheek)")
cheek["cheek_weld_grid_cant_pitch_gap"] = grid
log("cheek weld", {k: v for k, v in (weld or {}).items()})
out["measurements"] = {
    "length_of_pull_mm": round(lop, 1), "length_of_pull_rule": "trigger blade face (Z B 21.13) to the butt pad rear "
    "(min X of the body bone's vertices)", "trigger_face_X_B_mm": round(trig_face_x, 2), "butt_rear_X_B_mm": round(butt_x, 2),
    "real_length_of_pull_mm": [330, 370],
    "trigger_reach_mm": round(reach, 1), "trigger_reach_rule": "spec web point (hollow) -> trigger blade face",
    "trigger_reach_gate_mm": 80.0, "trigger_reach_pass": reach <= 80.0,
    "grip_girth_mm": girth, "grip_girth_rule": "section perpendicular to the grip axis, 25 / 46 / 70 mm down from the web "
    "point (the W1 early method), on the shipped body-bone bytes", "grip_girth_gate_mm": 167.0,
    "grip_girth_pass": girth["at_46mm"] <= 167.0 and girth["at_46mm"] > 0,
    "eye_relief_design_mm": round(float(SIGHT_B[0] - EYEPOINT_B[0]), 2),
    "eye_to_eyepiece_rear_mm": round(scope_rear_x - float(EYEPOINT_B[0]), 2),
    "EyePoint_B_mm": EYEPOINT_B.round(2).tolist(), "Sight_B_mm": SIGHT_B.round(2).tolist(),
    "eye_world_mm": eye.round(1).tolist(), "eye_source": eye_src,
    "cheek_riser": cheek, "shoulder_pocket": pocket}
Mh = Mw @ np.array(arm.data.bones["hand_r"].matrix_local)
Mh[:3, 3] *= 1000.0
G_in_hand = np.linalg.inv(Mh) @ TgR
q = Matrix(G_in_hand[:3, :3].tolist()).to_quaternion()
out["hand_offset"] = {"frame": "hand_r bone (MH_PlayerDefault metahuman_base_skel, Blender armature axes)",
                      "Grip_location_mm": np.round(G_in_hand[:3, 3], 3).tolist(),
                      "Grip_rotation_quaternion_wxyz": [round(float(v), 6) for v in q],
                      "grip_pose_deg": POSE_R, "grip_pose_quaternions": POSE_R_Q}
right_palm_B = to_B(HR.palm_c[None], RR, t_r)[0]
out["right_palm_centre_B_mm"] = right_palm_B.round(2).tolist()
summary = {"right_palm_penetration_mm": out["right_palm"]["penetration_mm"],
           "index_pad_to_trigger_face_mm": out["index"]["pad_to_trigger_face_mm"],
           "left_A_palm_penetration_mm": recA["palm_penetration_mm"],
           "left_B_palm_penetration_mm": recB["palm_penetration_mm"],
           "intersections": {k: v for k, v in out["intersections"].items() if k != "pass"},
           "ik_right": [ikR["residual_mm"], ikR["elbow_flexion_deg"]],
           "ik_left_A": [ikLA["residual_mm"], ikLA["elbow_flexion_deg"]],
           "ik_left_B": [ikLB["residual_mm"], ikLB["elbow_flexion_deg"]],
           "grip_girth_46_mm": girth["at_46mm"], "trigger_reach_mm": round(reach, 1),
           "length_of_pull_mm": round(lop, 1), "riser_raise_needed_mm_upright_head": cheek.get("riser_raise_needed_mm"),
           "cheek_weld": None if weld is None else {k: weld[k] for k in ("cant_deg", "pitch_deg", "riser_raise_needed_mm",
                                                                          "butt_to_pocket_mm") if k in weld},
           "butt_to_shoulder_pocket_mm": pocket.get("butt_to_pocket_mm"),
           "left_A_shortfall_mm": out["left_A_reach"]["shortfall_mm"],
           "left_A_shoulder_yaw_that_reaches_deg": out["left_A_reach"]["shoulder_yaw_that_reaches_deg"]}
out["socket_proposals"] = {
    "SupportHand": {"now_B_mm": SOCK["SupportHand"].tolist(),
                    "palm_contact_surface_B_mm": recA["surface_over_palm_centre_B_mm"],
                    "farthest_reachable_X_B_square_stance_mm": out["left_A_reach"][
                        "farthest_reachable_SupportHand_X_B_square_stance_mm"],
                    "why": "the socket is socket_to_surface_point_mm inside the forend above the palm's contact face; in "
                           "the square stance the left arm reaches only to the X given"},
    "SupportHandBipod": {"now_B_mm": SOCK["SupportHandBipod"].tolist(),
                         "palm_contact_surface_B_mm": recB["surface_over_palm_centre_B_mm"],
                         "why": "the socket is socket_to_surface_point_mm inside the butt above its underside"},
    "Grip": "keep (frame origin; the hand seats with the palm centre on it, 0 offsets)",
    "Shoulder": "keep (the butt-pad rear centre; the pocket gap is a posture matter, see measurements.shoulder_pocket)"}
out["summary"] = summary
out["threshold"] = ("palm penetration <= 1 mm (each hand); index pad 0..3 mm from the trigger face at the rest curl, the "
                    "finger clear of the frame; 0 hand-gun triangle pairs / penetrations at rest and every clip extreme "
                    "(both hands, both poses); the three two-bone IKs < 0.5 mm with the elbow inside 0..150 deg; grip "
                    "girth at 46 mm <= 167 mm; trigger reach <= 80 mm (W1 early bands). Reported, not gated: length of "
                    "pull, eye relief, riser raise, shoulder pocket")
out["gate_rows"] = {"right_palm": out["right_palm"]["pass"], "index": out["index"]["pass"],
                    "left_A_palm": recA["palm_pass"], "left_B_palm": recB["palm_pass"],
                    "intersections": out["intersections"]["pass"], "ik_right": ikR["pass"], "ik_left_A": ikLA["pass"],
                    "ik_left_B": ikLB["pass"], "girth": out["measurements"]["grip_girth_pass"],
                    "reach": out["measurements"]["trigger_reach_pass"]}
out["pass"] = all(out["gate_rows"].values())
out["note"] = "measured on the locked fit body in Blender on the shipped Exports/Guns/SR01 bytes; no export touched"
OUTJ.write_text(json.dumps(out, indent=1, default=str))
log("SUMMARY", json.dumps(summary), "PASS" if out["pass"] else "FAIL", out["gate_rows"])


# ================================================================================================ pictures
def pose_arm(side, target_w_m, pole):
    s = "_" + side
    MwM = arm.matrix_world
    iMw = MwM.inverted()
    bu, bl, bh = (arm.data.bones[n + s] for n in ("upperarm", "lowerarm", "hand"))
    S = MwM @ bu.head_local
    Eh = MwM @ bl.head_local
    Wh = MwM @ bh.head_local
    L1, L2 = (Eh - S).length, (Wh - Eh).length
    W = target_w_m.to_translation()
    dv = W - S
    d = min(dv.length, L1 + L2 - 1e-5)
    u = dv.normalized()
    a = (L1 * L1 - L2 * L2 + d * d) / (2 * d)
    hh = math.sqrt(max(L1 * L1 - a * a, 0.0))
    p = Vector(pole) - u * Vector(pole).dot(u)
    p.normalize()
    E = S + u * a + p * hh
    R1 = (Eh - S).rotation_difference(E - S).to_matrix().to_4x4()
    Mu = MwM @ bu.matrix_local
    Mu_new = Matrix.Translation(S) @ R1 @ Matrix.Translation(-S) @ Mu
    arm.pose.bones[bu.name].matrix = iMw @ Mu_new
    bpy.context.view_layer.update()
    El = MwM @ arm.pose.bones[bl.name].head
    Ml_cur = MwM @ arm.pose.bones[bl.name].matrix
    dcur = (R1.to_3x3() @ (Wh - Eh))
    R2 = dcur.rotation_difference(W - El).to_matrix().to_4x4()
    Ml_new = Matrix.Translation(El) @ R2 @ Matrix.Translation(-El) @ Ml_cur
    arm.pose.bones[bl.name].matrix = iMw @ Ml_new
    bpy.context.view_layer.update()
    Wc = MwM @ arm.pose.bones[bh.name].head
    tm = target_w_m.copy()
    tm.translation = Wc
    arm.pose.bones[bh.name].matrix = iMw @ tm
    bpy.context.view_layer.update()
    return (Wc - W).length * 1000.0


def m4(A):
    return Matrix(A.tolist())


def mm_to_m(T):
    T = T.copy()
    T[:3, 3] *= 0.001
    return T


try:
    for o in IMPORTED:
        bpy.data.objects.remove(o, do_unlink=True)
    for o in bpy.data.objects:
        if o.type == "MESH" and o.name.endswith("HairProxy"):
            o.hide_render = True
    if not any(m.type == "ARMATURE" for m in body.modifiers):
        md = body.modifiers.new("Armature", "ARMATURE")
        md.object = arm
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "OBJECT"
    sc.display.shading.show_cavity = True
    sc.render.resolution_x, sc.render.resolution_y = 1400, 1000
    for o in bpy.data.objects:
        if o.type == "MESH":
            o.color = (0.78, 0.62, 0.52, 1.0)
    col = bpy.data.collections.new("H1_View")
    sc.collection.children.link(col)
    cam = bpy.data.objects.new("h1cam", bpy.data.cameras.new("h1cam"))
    col.objects.link(cam)
    sc.camera = cam
    cam.data.clip_start = 0.01
    # the renders show the cheek-weld posture when one was found (head canted / pitched about neck_01, the gun at the
    # moved eye); otherwise the upright gated pose
    if weld is not None:
        t_r_ = t_w
        Rh_ = head_rot(weld["cant_deg"], weld["pitch_deg"])
        eye_r = Rh_ @ (eye - NECK) + NECK
        Mrot = Matrix(np.r_[np.c_[Rh_, NECK * 0.001 - Rh_ @ NECK * 0.001], [[0.0, 0.0, 0.0, 1.0]]].tolist())
        if any(m.type == "ARMATURE" for m in headm.modifiers) or headm.parent_type == "BONE":
            head_mode = "bone"
        else:
            head_mode = "objects"
    else:
        t_r_, eye_r, head_mode, Mrot = t_ads, eye, None, None
    Tads_m = m4(mm_to_m(place(Rg, t_r_)))
    head_objs = [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("FIT_") and o is not body]
    base_mw = {o.name: o.matrix_world.copy() for o in head_objs}
    Mh_rest = {sd: arm.matrix_world @ arm.data.bones["hand_" + sd].matrix_local for sd in ("r", "l")}

    def gun_objs(gun, tag):
        objs = []
        for n, (V, T) in gun.P.items():
            m = bpy.data.meshes.new(f"h1_{tag}_{n}")
            m.from_pydata((V * 0.001).tolist(), [], T.tolist())
            o = bpy.data.objects.new(f"h1_{tag}_{n}", m)
            col.objects.link(o)
            o.matrix_world = Tads_m
            o.color = (0.12, 0.12, 0.12, 1.0) if n == "scope_SM" else (0.33, 0.36, 0.24, 1.0)
            objs.append(o)
        return objs

    def apply_fingers(Q):
        for b, qv in Q.items():
            arm.pose.bones[b].rotation_quaternion = Quaternion(qv)

    def shoot(name, eye_, tgt, ortho=None, lens=35.0, hide_head=False):
        cam.location = Vector(eye_)
        cam.rotation_euler = (Vector(tgt) - Vector(eye_)).to_track_quat("-Z", "Y").to_euler()
        if ortho:
            cam.data.type = "ORTHO"
            cam.data.ortho_scale = ortho
        else:
            cam.data.type = "PERSP"
            cam.data.lens = lens
        for o in (headm, headparts):
            o.hide_render = hide_head
        for o in bpy.data.objects:
            if o.name.endswith("HairCards"):
                o.hide_render = hide_head
        sc.render.filepath = str(RENDERS / f"{name}.png")
        bpy.ops.render.render(write_still=True)
        return str(RENDERS / f"{name}.png")

    def wpt(pB):
        return ((Rg @ pB + t_r_) * 0.001).tolist()

    def pose_head():
        if Mrot is None:
            return
        nb = arm.pose.bones["neck_01"]
        MwM = arm.matrix_world
        nb.matrix = MwM.inverted() @ Mrot @ MwM @ nb.matrix
        bpy.context.view_layer.update()
        if head_mode == "objects":
            for o in head_objs:
                o.matrix_world = Mrot @ base_mw[o.name]

    shots = []
    resid = {}
    for tag, gun, TgL, QL, sock in (("A", G0, TgLA, POSE_LA_Q, "SupportHand"),
                                    ("B", GD, TgLB, POSE_LB_Q, "SupportHandBipod")):
        for pb in arm.pose.bones:
            pb.matrix_basis = Matrix()
            pb.rotation_mode = "QUATERNION"
        bpy.context.view_layer.update()
        objs = gun_objs(gun, tag)
        pose_head()
        tr = Tads_m @ m4(mm_to_m(np.linalg.inv(TgR))) @ Mh_rest["r"]
        tl = Tads_m @ m4(mm_to_m(np.linalg.inv(TgL))) @ Mh_rest["l"]
        resid[f"{tag}_right_wrist_mm"] = round(pose_arm("r", tr, (-0.7, 0.3, -1.0)), 1)
        resid[f"{tag}_left_wrist_mm"] = round(pose_arm("l", tl, (0.6, 0.0, -1.0) if tag == "A" else (0.9, 0.3, -0.6)), 1)
        apply_fingers(POSE_R_Q)
        apply_fingers(QL)
        bpy.context.view_layer.update()
        mid = wpt(np.array([120.0, 0.0, 30.0]))
        shots.append(shoot(f"h1_{tag}_side", [mid[0] - 3.0, mid[1], mid[2] + 0.05], mid, ortho=1.45))
        e = (eye_r * 0.001)
        shots.append(shoot(f"h1_{tag}_fp", [e[0], e[1] + 0.06, e[2] + 0.07], wpt(np.array([180.0, 0.0, 40.0])),
                           lens=16.0, hide_head=True))
        g_ = wpt(np.array([20.0, 0.0, 10.0]))
        shots.append(shoot(f"h1_{tag}_grip_right", [g_[0] - 0.45, g_[1] - 0.15, g_[2] - 0.05], g_, ortho=0.32))
        s_ = wpt(SOCK[sock])
        shots.append(shoot(f"h1_{tag}_support_left", [s_[0] - 0.4, s_[1] - 0.12, s_[2] - 0.25], s_, ortho=0.34,
                           hide_head=tag == "B"))
        for o in objs:
            bpy.data.objects.remove(o, do_unlink=True)
    out["renders"] = shots
    out["render_arm_residuals_mm"] = resid
    out["render_head"] = {"mode": head_mode, "cheek_weld": None if weld is None else [weld["cant_deg"], weld["pitch_deg"]]}
    out["render_note"] = ("cheek-weld posture (measurements.cheek_riser.cheek_weld_head_pose) when found; arms posed analytically (two-bone, elbow pole down / out) to the hold transforms, fingers at "
                          "the measured poses; pose B keeps the standing upper body (a proxy for prone: the gun-to-head "
                          "and hand-to-gun relation is the gated part, the torso / legs are not posed prone)")
    OUTJ.write_text(json.dumps(out, indent=1, default=str))
    log("pictures written", resid)
except Exception as e:  # noqa: BLE001
    import traceback
    traceback.print_exc()
    log("pictures failed", e)
log("SRH1_DONE")
