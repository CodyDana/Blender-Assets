"""Offline: the ENGINE's bone transforms (ivB*.json) against Blender (Assets/Fan.blend, read only, never saved).
All geometry in UE component space, cm."""
import bpy, json, math, sys
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

D = sys.argv[sys.argv.index("--") + 1]
ref = json.load(open(D + "/bl_ref.json"))
B = json.load(open(D + "/ueout/ivB.json"))
RAW = json.load(open(D + "/ueout/ivB_raw.json"))
RUN = json.load(open(D + "/ueout/ivB_runtime.json"))
SC = json.load(open(r"C:/Users/Cody/Desktop/Blender_Projects/Exports/Fan/SK_Fan.skeletal.json"))
out = {}


def qrot(q, v):
    x, y, z, w = q
    u = np.array([x, y, z])
    v = np.asarray(v, float)
    return v + 2.0 * np.cross(u, np.cross(u, v) + w * v)


def qinv(q):
    return [-q[0], -q[1], -q[2], q[3]]


def apply(T, p):          # T = [tx,ty,tz,qx,qy,qz,qw,(sx,sy,sz)]
    s = np.array(T[7:10]) if len(T) >= 10 else np.ones(3)
    return np.array(T[:3]) + qrot(T[3:7], np.asarray(p) * s)


def unapply(T, p):
    s = np.array(T[7:10]) if len(T) >= 10 else np.ones(3)
    return qrot(qinv(T[3:7]), np.asarray(p) - np.array(T[:3])) / s


REF = B["skeleton"]["ref_comp"]
# ------------------------------------------------------------ hierarchy + reference pose
bl = ref["bones"]
ue_par = B["skeleton"]["parents"]
names_ue = [n for n in B["skeleton"]["order"] if n != "root"]
hier = {"ue_bones": len(B["skeleton"]["order"]), "blender_bones": len(bl), "skeleton_asset_bones": B["skeleton"]["skeleton_asset_bones"],
        "missing_in_ue": sorted(set(bl) - set(names_ue)), "extra_in_ue": sorted(set(names_ue) - set(bl)),
        "parent_mismatch": [n for n in bl if (ue_par.get(n) or None) != (bl[n]["parent"] or "root")],
        "order_equal": names_ue == ref["bone_order"]}
hier["max_head_err_mm"] = max(float(np.linalg.norm(np.array(REF[n][:3]) - np.array(bl[n]["head_ue"]))) for n in bl) * 10
hier["max_ref_scale_dev"] = max(abs(s - 1) for n in REF for s in REF[n][7:10])
# the rotation axis of every stick = the rivet axis: rotating about component Z only
hier["ref_is_open_pose"] = None
out["hierarchy"] = hier
# ------------------------------------------------------------ per-bone vertex sets from the blend (UE cm)
arm = bpy.data.objects["root"]


def mesh_bones(name):
    o = bpy.data.objects[name]
    me = o.data
    M = arm.matrix_world.inverted() @ o.matrix_world
    gn = [g.name for g in o.vertex_groups]
    per = {}
    for v in me.vertices:
        ws = [(g.weight, gn[g.group]) for g in v.groups if g.weight > 0]
        b = max(ws)[1]
        p = M @ v.co
        per.setdefault(b, []).append([p.x * 100, -p.y * 100, p.z * 100])
    return {b: np.array(v) for b, v in per.items()}


LODV = {L: mesh_bones(n) for L, n in enumerate(["SK_Fan", "SK_Fan_LOD1", "SK_Fan_LOD2"])}


def pose_pts(P, b, pts):
    """engine pose P (component transforms per bone) applied to bind-space points of bone b"""
    R = REF[b]
    loc = np.array([unapply(R, p) for p in pts])
    return np.array([apply(P[b], p) for p in loc])


def fast_pose(P, b, pts):
    R = REF[b]
    # compose Pose * Ref^-1 as rotation + translation (unit scales verified)
    qr, qp = R[3:7], P[b][3:7]
    local = qrot(qinv(qr), (pts - np.array(R[:3])).T.T) if False else None
    Rr = quat_mat(qr); Rp = quat_mat(qp)
    return (pts - np.array(R[:3])) @ Rr @ Rp.T + np.array(P[b][:3])


def quat_mat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


# sanity: quat_mat agrees with qrot
_q = REF["leaf_10"][3:7]
assert np.allclose(quat_mat(_q) @ np.array([1.0, 2.0, 3.0]), qrot(_q, [1.0, 2.0, 3.0]), atol=1e-9)
PAIRS = {L: ref["lods"][n]["crack_pairs"] for L, n in enumerate(["SK_Fan", "SK_Fan_LOD1", "SK_Fan_LOD2"])}
PROBES = ref["probes"]
front_face = max(LODV[0]["stick_00"][:, 2])      # front guard's front face (component z, cm)
rear_face = min(LODV[0]["stick_25"][:, 2])
out["stack"] = {"front_guard_face_cm": front_face, "rear_guard_face_cm": rear_face}
g0 = LODV[0]["stick_00"]
g25 = LODV[0]["stick_25"]


def opening_deg(P):
    def ang(b):
        tip = fast_pose(P, b, np.array([PROBES[b][0]]))[0]
        return math.degrees(math.atan2(tip[1], tip[0]))
    a0 = ang("stick_00"); a1 = ang("stick_25")
    base = math.degrees(math.atan2(PROBES["stick_25"][0][1], PROBES["stick_25"][0][0])) - math.degrees(math.atan2(PROBES["stick_00"][0][1], PROBES["stick_00"][0][0]))
    return abs((a1 - a0 + 180) % 360 - 180)


# the probe angle of the guards differs from the bone-axis angle by a constant: calibrate on the open ref pose
REFP = {b: REF[b] for b in REF}
open_ref_probe = opening_deg(REFP)


def eval_pose(P, anim=None, frame=None, lods=(0, 1, 2)):
    r = {}
    # crack
    cr = 0.0
    for L in lods:
        for a, b, pa, pb in PAIRS[L]:
            xa = fast_pose(P, a, np.array([pa]))[0]
            xb = fast_pose(P, b, np.array([pb]))[0]
            cr = max(cr, float(np.linalg.norm(xa - xb)))
    r["crack_mm"] = cr * 10
    # leaf z extremes vs guard faces (all LODs' leaf vertices)
    zmax, zmin = -1e9, 1e9
    inside_front = 0
    for L in lods:
        for b, v in LODV[L].items():
            if not b.startswith("leaf_"):
                continue
            X = fast_pose(P, b, v)
            zmax = max(zmax, X[:, 2].max()); zmin = min(zmin, X[:, 2].min())
    r["leaf_zmax_minus_front_face_mm"] = (zmax - front_face) * 10
    r["leaf_zmin_minus_rear_face_mm"] = (zmin - rear_face) * 10
    r["opening_probe_deg"] = opening_deg(P)
    if anim is not None and frame is not None and str(frame) in ref["anims"][anim]["frames"]:
        fr = ref["anims"][anim]["frames"][str(frame)]
        dev = 0.0
        for b, pts in PROBES.items():
            X = fast_pose(P, b, np.array(pts))
            dev = max(dev, float(np.abs(X - np.array(fr["probes"][b])).max()))
        r["vs_blender_probe_max_mm"] = dev * 10
        r["blender_opening_deg"] = fr["opening_deg"]
    return r


def run_set(poses, anim):
    rows = {}
    for t, P in poses.items():
        tt = float(t)
        f = tt * 60.0
        frame = int(round(f)) if abs(f - round(f)) < 1e-3 else None
        rows[t] = eval_pose(P, anim, frame)
    return rows


res = {}
for anim, poses in RAW.items():
    res["raw:" + anim] = run_set(poses, anim)
for nm, poses in RUN.items():
    base = nm.replace("_Default", "")
    res["runtime:" + nm] = run_set(poses, base)


def summ(rows):
    k = list(rows.values())
    s = {"samples": len(k), "crack_max_mm": max(r["crack_mm"] for r in k),
         "leaf_above_front_face_max_mm": max(r["leaf_zmax_minus_front_face_mm"] for r in k),
         "leaf_below_rear_face_min_mm": min(r["leaf_zmin_minus_rear_face_mm"] for r in k)}
    dv = [r["vs_blender_probe_max_mm"] for r in k if "vs_blender_probe_max_mm" in r]
    if dv:
        s["vs_blender_max_mm"] = max(dv)
        s["vs_blender_samples"] = len(dv)
    return s


out["summary"] = {k: summ(v) for k, v in res.items()}
# opening per frame: engine vs blender (probe-based, identical definition on both sides)
op = {}
for anim in RAW:
    rows = res["raw:" + anim]
    fr = ref["anims"][anim]["frames"]
    worst = 0.0
    for t, r in rows.items():
        f = float(t) * 60
        if abs(f - round(f)) < 1e-3 and str(int(round(f))) in fr:
            # blender opening from ITS OWN bone axes; engine probe-opening differs by the probe offset at the open ref pose
            worst = max(worst, abs((r["opening_probe_deg"] - open_ref_probe + 163.2) - fr[str(int(round(f)))]["opening_deg"]))
    op[anim] = {"max_err_deg": worst, "first": [rows[k]["opening_probe_deg"] - open_ref_probe + 163.2 for k in sorted(rows, key=float)[:3]],
                "last": [rows[k]["opening_probe_deg"] - open_ref_probe + 163.2 for k in sorted(rows, key=float)[-3:]]}
out["opening"] = op
out["open_ref_probe_deg"] = open_ref_probe
# loop / ends: OpenClose first and last pose
oc = RAW["A_Fan_OpenClose"]
ks = sorted(oc, key=float)
d_end = max(float(np.linalg.norm(fast_pose(oc[ks[0]], b, np.array(PROBES[b])) - fast_pose(oc[ks[-1]], b, np.array(PROBES[b])), axis=1).max()) for b in PROBES)
out["openclose_first_vs_last_mm"] = d_end * 10
out["openclose_times"] = [ks[0], ks[-1]]
# hold section: opening during 0.5-0.8 s
out["openclose_hold"] = {t: round(res["raw:A_Fan_OpenClose"][t]["opening_probe_deg"] - open_ref_probe + 163.2, 4) for t in ks if 0.45 <= float(t) <= 0.85 and abs(float(t) * 60 - round(float(t) * 60)) < 1e-3}
# Openness linearity
on = res["raw:A_Fan_Openness"]
lin = [abs((on[t]["opening_probe_deg"] - open_ref_probe + 163.2) - (1.57 + (163.2 - 1.57) * float(t))) for t in on]
out["openness_linear_max_dev_deg"] = max(lin)
# runtime vs raw at the same times (compression error)
comp = {}
for nm in RUN:
    base = nm.replace("_Default", "")
    worst = 0.0
    for t, P in RUN[nm].items():
        if t not in RAW[base]:
            continue
        Q = RAW[base][t]
        for b, pts in PROBES.items():
            worst = max(worst, float(np.abs(fast_pose(P, b, np.array(pts)) - fast_pose(Q, b, np.array(pts))).max()))
    comp[nm] = worst * 10
out["runtime_vs_raw_max_mm"] = comp
# ------------------------------------------------------------ bounds: component bounds vs blender posed AABB
pb = B["posed_bounds"]["0"]
o = np.array(pb["origin"]); e = np.array(pb["extent"])
lo, hi = o - e, o + e
worst = -1e9; wf = None
for f, bb in ref["anims"]["A_Fan_Openness"]["aabb"].items():
    mn = np.array(bb["min"]); mx = np.array(bb["max"])
    # y flipped in bl_ref aabb construction: take true min/max per axis
    amin = np.minimum(mn, mx); amax = np.maximum(mn, mx)
    over = max(float((lo - amin).max()), float((amax - hi).max()))
    if over > worst:
        worst, wf = over, f
out["bounds"] = {"component_min": lo.tolist(), "component_max": hi.tolist(), "worst_overhang_cm": worst, "at_frame": wf,
                 "asset_bounds": B["asset_bounds"]["bounds"], "all_frames_same": len({json.dumps(v["extent"]) for v in B["posed_bounds"].values()}) == 1}
# posed AABB from the ENGINE poses too (LOD0 all vertices), Openness raw
eng = []
for t, P in RAW["A_Fan_Openness"].items():
    pts = np.vstack([fast_pose(P, b, v) for b, v in LODV[0].items()])
    eng.append((float(t), pts.min(0), pts.max(0)))
ov = max(max(float((lo - a).max()), float((b_ - hi).max())) for _, a, b_ in eng)
out["bounds"]["engine_pose_worst_overhang_cm"] = ov
out["bounds"]["engine_pose_z_range_cm"] = [min(a[2] for _, a, _b in eng), max(b_[2] for _, _a, b_ in eng)]
# ------------------------------------------------------------ sockets vs sidecar
socks = {}
for s in SC["sockets"]:
    u = B["sockets"].get(s["name"])
    if not u:
        socks[s["name"]] = "missing"
        continue
    uc = s["unreal_component"]
    q1 = np.array(u["component"][3:7]); q2 = np.array(uc["quaternion_xyzw"])
    socks[s["name"]] = {"bone": u["bone"], "bone_ok": u["bone"] == s["bone"],
                        "loc_err_mm": float(np.linalg.norm(np.array(u["component"][:3]) - np.array(uc["location_cm"]))) * 10,
                        "rot_err_deg": math.degrees(2 * math.acos(min(1.0, abs(float(q1 @ q2))))),
                        "relative_scale": u["relative"][7:10]}
out["sockets"] = socks
json.dump({"out": out, "rows": res}, open(D + "/an_compare.json", "w"), indent=1)
print("ANALYSIS_DONE")
print(json.dumps(out, indent=1)[:9000])
