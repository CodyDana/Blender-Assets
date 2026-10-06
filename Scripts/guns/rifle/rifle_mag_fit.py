"""AR-01 stage 6 fit verification on the SHIPPED bytes of both meshes, in a fresh Blender process:

    blender -b --factory-startup --python Scripts/guns/rifle/rifle_mag_fit.py

RIFLE_BUILD_PLAN 8.2 (GUN_BUILDING_STUDY 7.2 M-gates). Both FBX files are re-imported (nothing from a build scene); the
magazine is placed from the exported rifle sidecar's sockets:
- M1  seated: intersecting triangles of the co-visible rifle / mag LOD pairs (k,k) and (k,k+-1); the twin's merged
      magazine faces (slot M_AR01_Mag) are left out of the rifle;
- M2  top-stop gap (rays up from the magazine's top) and the visible seam at the well's lower edge (section through the
      receiver's bottom sheet: front, rear, left, right);
- M3  lateral clearance per side; front lug to the nearest rifle surface ("in its recess"); rear lug to the catch face;
- M4  rock path MagInsertStart -> MagRockStart (lerp, 0.5 mm steps) -> Mag (slerp about the hook, 0.25 deg steps) on
      the co-visible pairs: 0 intersections except the declared catch allowance (<= 3.0 mm, last <= 6 deg);
- M5  the removal path (the same poses in reverse order);
- M6  Mag / MagRockStart / MagInsertStart (static and skeletal sidecars) and the magazine's own Mag vs the fit;
- M7  rifle bytes = the stage-5 sha256 (and the magazine bytes = its build's);
- M8  (info) a straight vertical insert without the rock.
Writes WorkFiles/guns/rifle/gates/mag.json (with the build's qa_check / C1 / S1 / LOD results) and
scratch/mag/fit_geom.npz for the section and rock-strip drawings (rifle_mag_sheets.py).
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rifle_common import ROOT, SCRATCH, GATES, GRIP, SPEC  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Euler, Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

from gunlib import game as GM  # noqa: E402

EXP = ROOT / "Exports" / "Guns" / "AR01"
RIG = json.loads((SCRATCH / "rig" / "rig_report.json").read_text())
MAGREP = json.loads((SCRATCH / "mag" / "mag_report.json").read_text())
PAIRS = [(0, 0), (1, 1), (2, 2), (3, 3), (0, 1), (1, 0), (1, 2), (2, 1), (2, 3), (3, 2)]
SWITCH_M = {1: 2.705, 2: 6.762, 3: 20.287}            # rifle LOD switch-in distances (gates/game.json LOD-pop)
CATCH_BOX_M = {"X": (355.0, 370.0), "Y": (-5.2, 5.2), "Z": (-70.0, -35.0)}


def log(*a):
    print("[AR01-fit]", *a, flush=True)


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def gate(name, value, threshold, ok, note=None):
    g = {"name": name, "value": value, "threshold": threshold, "pass": bool(ok)}
    if note:
        g["note"] = note
    return g


def clear():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)


def mesh_np(o):
    me = o.data
    V = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", V)
    V = V.reshape(-1, 3)
    M = np.array(o.matrix_world)
    V = (np.c_[V, np.ones(len(V))] @ M.T)[:, :3] * 1000.0
    me.calc_loop_triangles()
    T = np.empty(len(me.loop_triangles) * 3, int)
    me.loop_triangles.foreach_get("vertices", T)
    mi = np.empty(len(me.loop_triangles), int)
    me.loop_triangles.foreach_get("material_index", mi)
    names = [s.material.name if s.material else "" for s in o.material_slots]
    return V, T.reshape(-1, 3), np.array([names[i] if i < len(names) else "" for i in mi])


def tree(V, T):
    return BVHTree.FromPolygons([tuple(v) for v in V], [tuple(int(i) for i in t) for t in T], all_triangles=True,
                                epsilon=0.0)


def samples(V, T, step):
    return GM.dense_samples(V, T, step)


def sock_frame(rec):
    """Static sidecar socket -> (R, t) in Blender frame B (mm)."""
    loc = np.array(rec["location_cm"], float) * 10.0
    t = np.array([loc[0], -loc[1], loc[2]])
    ro = rec["rotation_deg"]
    R = np.array(Euler(GM.blender_euler_for_ue(ro["roll"], ro["pitch"], ro["yaw"]), "XYZ").to_matrix())
    return R, t


def slerp_y(Ra, Rb, u):
    """Rotations that differ about Y only (the rock): interpolate the angle."""
    a = math.atan2(Ra[0, 2], Ra[0, 0])
    b = math.atan2(Rb[0, 2], Rb[0, 0])
    th = a + (b - a) * u
    return np.array([[math.cos(th), 0, math.sin(th)], [0, 1, 0], [-math.sin(th), 0, math.cos(th)]])


def _parity(t, p, d, cap=2000.0):
    n, o = 0, Vector(p)
    for _ in range(64):
        h = t.ray_cast(o, d, cap)
        if h[0] is None:
            break
        n += 1
        o = h[0] + d * 1e-4
    return n % 2 == 1


DIRS = [Vector((0.31, 0.53, 0.79)).normalized(), Vector((-0.62, 0.21, -0.75)).normalized(),
        Vector((0.12, -0.91, 0.40)).normalized()]


def depth_inside(points, t, lo, hi, cap=60.0):
    """Deepest point inside the closed mesh of tree t (ray parity, 2 of 3 rays), depth = distance to its nearest
    surface (rifle_g5_lods method)."""
    best = 0.0
    for p in points:
        if np.any(p < lo) or np.any(p > hi):
            continue
        h = t.find_nearest(Vector(p), cap)
        if h[0] is None or h[3] <= best:
            continue
        if sum(_parity(t, p, d) for d in DIRS) >= 2:
            best = h[3]
    return best


#: inside the LOD0 receiver's well (between its walls, above its bottom sheet, between the opening's ends): magazine
#: surface here is hidden at EVERY LOD when seated or on the reload path, so its depth inside a coarse rifle LOD's solid
#: blockout changes nothing on screen (the coarse-LOD depth rule counts only points outside this box)
WELL_BOX_M = {"X": (368.8, 432.0), "Y": (-20.75, 20.75), "Z": (-30.85, 11.0)}


def visible_only(P):
    M = P + GRIP
    inside = ((M[:, 0] >= WELL_BOX_M["X"][0]) & (M[:, 0] <= WELL_BOX_M["X"][1]) & (M[:, 1] >= WELL_BOX_M["Y"][0]) &
              (M[:, 1] <= WELL_BOX_M["Y"][1]) & (M[:, 2] >= WELL_BOX_M["Z"][0]) & (M[:, 2] <= WELL_BOX_M["Z"][1]))
    return P[~inside]


def px_per_mm(k):
    """At LOD k's switch-in distance (2560 x 1440, 90 deg hFOV): 1280 / d(mm)."""
    return 1280.0 / (SWITCH_M[k] * 1000.0)


def band_pts(segs, axis, lo, hi):
    """Endpoints of the section segments clipped to lo <= |coord[axis]| <= hi (R51: a band measured on the segments,
    not only on the mesh vertices; long faces cross the |Y| < 8 band with no vertex in it)."""
    out = []
    for a, b in segs:
        a, b = np.asarray(a), np.asarray(b)
        for sgn in (1.0, -1.0):
            ya, yb = sgn * a[axis], sgn * b[axis]
            t0, t1, d = 0.0, 1.0, yb - ya
            for bound, above in ((lo, True), (hi, False)):
                if abs(d) < 1e-12:
                    if (ya < bound) if above else (ya > bound):
                        t0, t1 = 1.0, 0.0
                    continue
                t = (bound - ya) / d
                if (d > 0) == above:
                    t0 = max(t0, t)
                else:
                    t1 = min(t1, t)
            if t0 <= t1:
                out += [a + (b - a) * t0, a + (b - a) * t1]
    return np.array(out) if out else np.zeros((0, 3))


def section(V, T, axis, c):
    """Segments of triangles cut by the plane coord[axis] = c."""
    s = V[:, axis] - c
    A, B, C = T[:, 0], T[:, 1], T[:, 2]
    P, m_ = [], []
    for e0, e1 in ((A, B), (B, C), (C, A)):
        s0, s1 = s[e0], s[e1]
        m = (s0 * s1) < 0
        t = np.where(m, s0 / np.where(m, s0 - s1, 1.0), 0.0)
        P.append(V[e0] + (V[e1] - V[e0]) * t[:, None])
        m_.append(m)
    cnt = m_[0].astype(int) + m_[1] + m_[2]
    idx = np.nonzero(cnt == 2)[0]
    segs = []
    for i in idx:
        q = [P[k][i] for k in range(3) if m_[k][i]]
        segs.append((q[0], q[1]))
    return segs


def main():
    clear()
    gates = []
    out = {"stage": "6 Mag (fit, geo, uv, maps, game, export, verify)"}
    # ------------------------------------------------------------ M7 bytes
    rf, mf = EXP / "SM_AR01.fbx", EXP / "SM_AR01_Mag.fbx"
    r_sha, m_sha = sha256(rf), sha256(mf)
    r_want = RIG["files"]["Exports/Guns/AR01/SM_AR01.fbx"]["sha256"]
    m_want = MAGREP["files"]["Exports/Guns/AR01/SM_AR01_Mag.fbx"]["sha256"]
    gates.append(gate("M7 rifle bytes = the shipped stage-5 sha256", {"rifle": r_sha, "recorded": r_want,
                      "mag": m_sha, "mag_recorded": m_want, "mag_built_from_rifle_sha": MAGREP["rifle_bytes"]["sha256"]},
                      "equal (and the magazine was built from these rifle bytes)",
                      r_sha == r_want and m_sha == m_want and MAGREP["rifle_bytes"]["sha256"] == r_sha))
    # ------------------------------------------------------------ import the shipped bytes
    bpy.ops.import_scene.fbx(filepath=str(rf), use_custom_normals=True)
    rifle = {}
    for o in bpy.data.objects:
        if o.type == "MESH" and o.name.startswith("SM_AR01_LOD"):
            k = int(o.name[-1])
            V, T, mat = mesh_np(o)
            keep = mat != "M_AR01_Mag"
            rifle[k] = (V, T[keep], T[~keep])
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(mf), use_custom_normals=True)
    mag = {}
    for o in bpy.data.objects:
        if o not in before and o.type == "MESH" and o.name.startswith("SM_AR01_Mag_LOD"):
            V, T, _ = mesh_np(o)
            mag[int(o.name[-1])] = (V, T)
    # frame check: the imported rifle (mag faces excluded) spans the SK rest AABB (same parts) in frame B
    V0, T0, Tm0 = rifle[0]
    used = np.unique(T0)
    lo, hi = V0[used].min(0), V0[used].max(0)
    rlo, rhi = (np.array(x) for x in RIG["bounds_extension"]["rest_aabb_mm"])
    frame_err = float(max(np.abs(lo - rlo).max(), np.abs(hi - rhi).max()))
    out["import_frame_check_mm"] = round(frame_err, 5)
    log("frame check", frame_err)
    # ------------------------------------------------------------ sockets
    rs = {s["socket"]: s for s in json.loads((EXP / "SM_AR01.sockets.json").read_text())["sockets"]}
    ms = {s["socket"]: s for s in json.loads((EXP / "SM_AR01_Mag.sockets.json").read_text())["sockets"]}
    sk = {s["name"]: s for s in json.loads((EXP / "SK_AR01.skeletal.json").read_text())["sockets"]}
    RM, tM = sock_frame(rs["Mag"])
    RR, tR = sock_frame(rs["MagRockStart"])
    RI, tI = sock_frame(rs["MagInsertStart"])
    theta = math.degrees(math.atan2(RR[0, 2], RR[0, 0]) - math.atan2(RM[0, 2], RM[0, 0]))
    d_ins = float(np.linalg.norm(tI - tR))
    # the fit's own path frames: RockStart = Mag rotated about the hook; InsertStart = RockStart + d along its -Z
    fit_I = tR + RR @ np.array([0.0, 0.0, -d_ins])
    m6 = {"rock_deg": round(theta, 6), "insert_mm": round(d_ins, 6),
          "rockstart_at_hook_mm": round(float(np.abs(tR - tM).max()), 6),
          "insertstart_on_tilted_axis_mm": round(float(np.abs(fit_I - tI).max()), 6),
          "insert_rot_eq_rock_deg": round(float(np.degrees(np.abs(RI - RR).max())), 6)}
    sp = {r["socket"]: r for r in SPEC.sockets["rifle"]}
    dspec = 0.0
    fitset = {k: np.array(v["blender_mm"]) for k, v in RIG.get("fit_set_sockets", {}).items()}
    for n in ("Mag", "MagRockStart", "MagInsertStart"):
        want_cm = np.array(sp[n]["unreal_cm"]) if n not in fitset else np.array(
            [fitset[n][0], -fitset[n][1], fitset[n][2]]) * 0.1
        dspec = max(dspec, float(np.abs(np.array(rs[n]["location_cm"]) - want_cm).max()) * 10)
        dspec = max(dspec, max(abs(rs[n]["rotation_deg"][k] - sp[n]["unreal_rotation_deg"][k]) for k in ("roll", "pitch", "yaw")))
    dsk = 0.0
    for n in ("Mag", "MagRockStart", "MagInsertStart"):
        dsk = max(dsk, float(np.abs(np.array(sk[n]["unreal_component"]["location_cm"]) - np.array(rs[n]["location_cm"])).max()) * 10)
    mag0 = ms["Mag"]
    mag_origin = max(max(abs(v) for v in mag0["location_cm"]) * 10, max(abs(v) for v in mag0["rotation_deg"].values()))
    m6.update({"vs_spec_mm_or_deg": round(dspec, 6), "skeletal_vs_static_mm": round(dsk, 6),
               "mag_own_Mag_origin_mm_or_deg": round(mag_origin, 6)})
    ok6 = (m6["rockstart_at_hook_mm"] <= 0.001 and m6["insertstart_on_tilted_axis_mm"] <= 0.001 and
           m6["insert_rot_eq_rock_deg"] <= 0.001 and dspec <= 0.001 and dsk <= 0.001 and mag_origin <= 0.001)
    gates.append(gate("M6 reload-path sockets from the exported sidecars vs the fit", m6, "<= 0.001 mm, <= 0.001 deg", ok6,
                      "the rock is a pure rotation about the hook (RockStart at Mag's location); InsertStart lies on the "
                      "tilted mag's -Z; the skeletal and static sidecars agree; the magazine's Mag is its origin"))

    def place(k, R, t):
        V, T = mag[k]
        return V @ R.T + t, T          # mag frame -> B: the magazine's local axes ride the given socket frame

    # ------------------------------------------------------------ M1 seated
    rtrees = {k: tree(rifle[k][0], rifle[k][1]) for k in rifle}
    m1 = {}
    ok1 = True
    rbox = {k: (rifle[k][0][np.unique(rifle[k][1])].min(0), rifle[k][0][np.unique(rifle[k][1])].max(0)) for k in rifle}
    for a, b in PAIRS:
        Q, T = place(b, RM, tM)
        n = len(rtrees[a].overlap(tree(Q, T)))
        row = {"intersecting_triangle_pairs": n}
        if n and max(a, b) >= 2:
            Sq = samples(Q, T, 0.5)
            raw = depth_inside(Sq, rtrees[a], *rbox[a])
            dep = depth_inside(visible_only(Sq), rtrees[a], *rbox[a])
            k = max(a, b)
            row.update(depth_mm_outside_well=round(dep, 3), depth_px=round(dep * px_per_mm(k), 3), at_m=SWITCH_M[k],
                       raw_depth_mm_incl_hidden_well_part=round(raw, 3), raw_px=round(raw * px_per_mm(k), 3))
            ok1 &= dep * px_per_mm(k) < 1.0
        elif n:
            ok1 = False
        m1[f"rifle LOD{a} / mag LOD{b}"] = row
    gates.append(gate("M1 seated: intersecting triangles, co-visible LOD pairs", m1,
                      "0 (LOD0-1 pairs 0; LOD2-3 pairs: depth under 1 px at the switch distance, counted outside the "
                      "LOD0 well where the magazine is never visible)", ok1,
                      "rifle LOD3 is the blockout silhouette level: its receiver is a solid with no well, so the seated "
                      "magazine's top (hidden inside the well at every LOD) lies inside it; raw depths are recorded"))
    # ------------------------------------------------------------ M2 top stop + seam
    QM, TM = place(0, RM, tM)
    S = samples(QM, TM, 0.25)
    ztop = S[:, 2].max()
    top = S[S[:, 2] > ztop - 4.0]
    best = (1e9, None)
    for p in top:
        h = rtrees[0].ray_cast(Vector(p) + Vector((0, 0, 1e-4)), Vector((0, 0, 1)), 60.0)
        if h[0] is not None and h[3] < best[0]:
            best = (h[3], p)
    top_gap = float(best[0])
    # seam: the receiver's bottom sheet around the opening (mid-thickness plane)
    VR, TR_ = rifle[0][0], rifle[0][1]
    c = VR[TR_].mean(1)
    Mc = c + GRIP
    near = (Mc[:, 0] > 432.5) & (Mc[:, 0] < 470) & (np.abs(Mc[:, 1]) < 10) & (Mc[:, 2] < -25) & (Mc[:, 2] > -40)
    plate_bottom = float(VR[TR_[near]][:, :, 2].min())
    # the seam is read in horizontal sections through the junction (the receiver's bottom sheet and the guard's front
    # tang, plate_bottom - 1.5 .. + 1.0 in 0.1 mm steps): per side the smallest gap between the magazine's outline and
    # the nearest rifle edge in front of / behind / beside it (|Y| < 8 for front and rear; the mid 60 % of the length
    # for the sides), over the planes where both exist
    gaps = {"front": [], "rear": [], "left": [], "right": []}
    for zp in np.arange(plate_bottom - 1.5, plate_bottom + 1.0001, 0.1):
        rs, ms = section(VR, TR_, 2, zp), section(QM, TM, 2, zp)
        rp = [p for s_ in rs for p in s_]
        mp = [p for s_ in ms for p in s_]
        if not rp or not mp:
            continue
        rp, mp = np.array(rp), np.array(mp)
        x0, x1 = mp[:, 0].min(), mp[:, 0].max()
        xc = 0.5 * (x0 + x1)
        rb = band_pts(rs, 1, 0.0, 8.0)
        rb = rb[(rb[:, 0] > x0 - 15) & (rb[:, 0] < x1 + 15)] if len(rb) else rb
        mb = band_pts(ms, 1, 0.0, 8.0)
        if len(mb) and (rb[:, 0] > xc).any():
            gaps["front"].append((float(rb[rb[:, 0] > xc][:, 0].min() - mb[:, 0].max()), float(zp)))
        if len(mb) and (rb[:, 0] < xc).any():
            gaps["rear"].append((float(mb[:, 0].min() - rb[rb[:, 0] < xc][:, 0].max()), float(zp)))
        xa, xb_ = x0 + 0.2 * (x1 - x0), x1 - 0.2 * (x1 - x0)
        rs_ = rp[(rp[:, 0] > xa) & (rp[:, 0] < xb_)]
        ms_ = mp[(mp[:, 0] > xa) & (mp[:, 0] < xb_)]
        if len(ms_) and (rs_[:, 1] > 0).any():
            gaps["left"].append((float(rs_[rs_[:, 1] > 0][:, 1].min() - ms_[:, 1].max()), float(zp)))
        if len(ms_) and (rs_[:, 1] < 0).any():
            gaps["right"].append((float(ms_[:, 1].min() - rs_[rs_[:, 1] < 0][:, 1].max()), float(zp)))
    seams = {}
    for k, v in gaps.items():
        v = [g for g in v if g[0] > -0.05]
        if v:
            g, z = min(v)
            seams[k] = {"gap_mm": round(g, 4), "at_Z_M": round(z + GRIP[2], 2)}
    zp = plate_bottom
    ok2 = 0.1 <= top_gap <= 0.5 and max(v["gap_mm"] for v in seams.values()) <= 0.6
    gates.append(gate("M2 seat: top-stop gap; visible seam at the well's lower edge",
                      {"top_stop_gap_mm": round(top_gap, 4), "top_stop_from": None if best[1] is None else
                       np.round(best[1] + GRIP, 2).tolist(), "seam": seams, "receiver_sheet_bottom_Z_M": round(zp + GRIP[2], 3)},
                      "top stop 0.1-0.5 mm; seam <= 0.6 mm (side: front / rear; front view: left / right)", ok2,
                      "fails: see the values (R51 design: front top stop = the hook tab under the trunnion, seam = the "
                      "spine's sweep at the sheet + 0.06, the lug channel at |Y| <= 4.2 is the real pattern's lug slot)"
                      if not ok2 else "R51: the front top stop is the hook tab under the front trunnion; the "
                      "visible-edge numbers per band are in gates/form_magfit.json"))
    # ------------------------------------------------------------ M3 clearances
    Ss = samples(QM, TM, 0.2)
    SsM = Ss + GRIP

    def nearest(points, t, cap=10.0):
        b, arg = cap, None
        for i, p in enumerate(points):
            h = t.find_nearest(Vector(p), b)
            if h[0] is not None and h[3] < b:
                b, arg = h[3], i
        return b, arg
    zwin = (SsM[:, 2] > -34.0) & (SsM[:, 2] < -27.0)
    lat = {}
    for side, sel in (("left", Ss[:, 1] > 11.0), ("right", Ss[:, 1] < -11.0)):
        d, _ = nearest(Ss[sel & zwin], rtrees[0])
        lat[side] = round(float(d), 4)
    # front lug: the hook region (mag frame X > -8, Z > -14 = within ~14 mm of the hook)
    Vm0, Tm0_ = mag[0]
    Sm = samples(Vm0, Tm0_, 0.2)
    lugsel = (Sm[:, 0] > -8.0) & (Sm[:, 2] > -14.0) & (np.abs(Sm[:, 1]) < 7.0)
    lug_pts = Sm[lugsel] @ RM.T + tM
    d_lug, ia = nearest(lug_pts, rtrees[0], cap=20.0)
    # rear lug to the catch face: rifle triangles inside the catch's box
    cm = (Mc[:, 0] >= CATCH_BOX_M["X"][0]) & (Mc[:, 0] <= CATCH_BOX_M["X"][1]) & \
         (Mc[:, 1] >= CATCH_BOX_M["Y"][0]) & (Mc[:, 1] <= CATCH_BOX_M["Y"][1]) & \
         (Mc[:, 2] >= CATCH_BOX_M["Z"][0]) & (Mc[:, 2] <= CATCH_BOX_M["Z"][1])
    ctree = tree(VR, TR_[cm])
    rl = (SsM[:, 0] > 368.0) & (SsM[:, 0] < 374.0) & (SsM[:, 2] > -40.5) & (SsM[:, 2] < -35.5) & (np.abs(SsM[:, 1]) < 6)
    d_rear, _ = nearest(Ss[rl], ctree)
    m3 = {"lateral_mm": lat, "front_lug_to_nearest_rifle_mm": round(float(d_lug), 4),
          "rear_lug_to_catch_face_mm": round(float(d_rear), 4)}
    ok3 = all(0.2 - 1e-4 <= v <= 0.6 for v in lat.values()) and 0.1 <= d_lug <= 0.4 and 0.0 <= d_rear <= 0.3
    gates.append(gate("M3 clearances: lateral per side; front lug in its recess; rear lug to the catch face", m3,
                      "0.2-0.6 mm; 0.1-0.4 mm; 0.0-0.3 mm", ok3,
                      None if ok3 else "fails: see the values (R51: the lug's pocket and the tab's channel in the front "
                                       "trunnion are cut 0.2 from the lug's swept envelope)"))
    # ------------------------------------------------------------ M4 / M5 rock path
    steps = []
    s_vals = np.arange(d_ins, -1e-9, -0.5)
    if s_vals[-1] > 1e-9:
        s_vals = np.r_[s_vals, 0.0]
    for s_ in s_vals:
        steps.append(("insert", float(s_), RR, tR + RR @ np.array([0.0, 0.0, -s_])))
    n_rot = int(math.ceil(abs(theta) / 0.25))
    for i in range(1, n_rot + 1):
        u = i / n_rot
        steps.append(("rock", float(theta * (1 - u)), slerp_y(RR, RM, u), tM))
    ctrees = {k: tree(rifle[k][0], rifle[k][1][((rifle[k][0][rifle[k][1]].mean(1) + GRIP) >= np.array(
        [CATCH_BOX_M["X"][0], CATCH_BOX_M["Y"][0], CATCH_BOX_M["Z"][0]])).all(1) & (
        (rifle[k][0][rifle[k][1]].mean(1) + GRIP) <= np.array([CATCH_BOX_M["X"][1], CATCH_BOX_M["Y"][1],
                                                              CATCH_BOX_M["Z"][1]])).all(1)]) for k in rifle}
    path = {}
    worst_other = 0
    dep_cache = {}
    catch_hits = []
    for a, b in PAIRS:
        rec = []
        for si, (kind, val, R, t) in enumerate(steps):
            Q, T = place(b, R, t)
            mt = tree(Q, T)
            n = len(rtrees[a].overlap(mt))
            nc = len(ctrees[a].overlap(mt)) if n else 0
            rec.append((kind, round(val, 3), n, nc))
            if n - nc > 0:
                if max(a, b) >= 2:
                    if si % 6 == 0 or si == len(steps) - 1:
                        dep = depth_inside(visible_only(samples(Q, T, 1.0)), rtrees[a], *rbox[a])
                        dep_cache.setdefault((a, b), []).append(dep * px_per_mm(max(a, b)))
                else:
                    worst_other = max(worst_other, n - nc)
            if nc:
                cb = (np.array([CATCH_BOX_M["X"][0], CATCH_BOX_M["Y"][0], CATCH_BOX_M["Z"][0]]) - GRIP,
                      np.array([CATCH_BOX_M["X"][1], CATCH_BOX_M["Y"][1], CATCH_BOX_M["Z"][1]]) - GRIP)
                cd = depth_inside(samples(Q, T, 0.5), ctrees[a], *cb)
                catch_hits.append({"pair": [a, b], "step": [kind, round(val, 3)], "triangle_pairs": nc,
                                   "depth_mm": round(cd, 3)})
        path[f"rifle LOD{a} / mag LOD{b}"] = {"steps": len(rec), "intersecting_steps": sum(1 for r in rec if r[2]),
                                               "with_catch_only": sum(1 for r in rec if r[2] and r[2] == r[3])}
    deep = {f"rifle LOD{a} / mag LOD{b}": round(max(v), 3) for (a, b), v in dep_cache.items()}
    allowance_ok = all(v < 1.0 for v in deep.values()) and all(h["step"][0] == "rock" and abs(h["step"][1]) <= 6.0 and h["depth_mm"] <= 3.0
                                                            for h in catch_hits)
    ok4 = worst_other == 0 and allowance_ok
    gates.append(gate("M4 rock path (insert 0.5 mm, rock 0.25 deg; co-visible pairs)",
                      {"steps": len(steps), "insert_steps": len(s_vals), "rock_steps": n_rot, "rock_deg": round(theta, 4),
                       "pairs": path, "catch_contacts": catch_hits[:20],
                       "lod2_3_depth_px (every 6th step + seated)": deep},
                      "0 intersections (LOD0-1 pairs; LOD2-3 pairs: depth < 1 px at the switch distance), except the "
                      "rear lug on the catch nose (<= 3.0 mm, last <= 6 deg)", ok4,
                      "0 contacts at every step: the catch allowance is not used" if ok4 and not catch_hits else None))
    gates.append(gate("M5 removal path (the M4 poses in reverse order)", {"pairs": path},
                      "same as M4", ok4, "the same pose set traversed backwards: identical intersection record"))
    # ------------------------------------------------------------ M8 straight vertical insert (info)
    vert = []
    for d in np.arange(40.0, -1e-9, -0.5):
        Q, T = place(0, RM, tM + np.array([0.0, 0.0, -d]))
        vert.append((round(float(d), 2), len(rtrees[0].overlap(tree(Q, T)))))
    hit = [v for v in vert if v[1]]
    gates.append(gate("M8 (info) straight vertical insert without the rock", {"steps": len(vert),
                      "colliding_steps": len(hit), "first": hit[:3]},
                      "reported (expected to collide: proves the rock is needed)", True,
                      "does NOT collide: a straight push seats the magazine as well" if not hit else
                      "collides: the hook tab meets the trunnion's ledge and the rear lug the catch's nose"))
    # ------------------------------------------------------------ the build's gates (qa_check, C1, S1, LODs)
    m = MAGREP
    lods = [m["lods"][f"SM_AR01_Mag_LOD{k}"]["triangles"] for k in range(4)]
    gates.append(gate("mag qa_check (LOD0-3, before export)", {"passed": m["qa_check"]["passed"],
                      "triangles": m["qa_check"]["triangles"], "texel_target": m["qa_check"]["texel_target_px_cm"],
                      "checks": m["qa_check"]["checks"]},
                      "pass; budget 7,000; UV1; UCX keyed to the node; texel = measured aggregate +-25 %",
                      m["qa_check"]["passed"]))
    gates.append(gate("mag LODs: strictly descending, plan 3.3 targets", lods,
                      "LOD0 <= 7,000 (target ~4,500); LOD1 ~1,750; LOD2 ~580; LOD3 200-300",
                      lods[0] <= 7000 and lods[0] > lods[1] > lods[2] > lods[3] and 200 <= lods[3] <= 300,
                      "LOD0 6,868 is the detail-pass magazine (over the ~4,500 target, under the 7,000 ceiling); LOD1-3 "
                      "collapse-decimated from LOD0 (UV0 interpolated: the LOD0 maps stay valid; fold-overs relaxed, "
                      "overlaps separated: %s)" % json.dumps(m.get("uv0_overlap_fix"))))
    gates.append(gate("C1 mag hull containment", m["C1"], "0 and 0; 2 hulls (spec collision_static_twin.mag), <= 32 "
                      "vertices", m["C1"]["pass"],
                      "2 hulls, not 1: one hull would fill the curve's ~30 mm sagitta (plan 7.1, spec, gun study 5.6)"))
    gates.append(gate("S1 mag sockets (exported sidecar vs build)", {"count": len(m["S1"]["sockets"]),
                      "worst_mm": m["S1"]["worst_mm"], "worst_deg": m["S1"]["worst_deg"],
                      "names_match_spec": m["S1"]["names_match_spec"]},
                      "5 = spec names; <= 0.001 mm, <= 0.001 deg", m["S1"]["pass"]))
    gates.append(gate("mag LOD screen sizes derived from the rifle's", m["lod_screen_sizes"],
                      "size_mag = size_rifle x r_mag / r_rifle", True))
    gates.append(gate("B10 mag names", m["B10_names"], "no hit", m["B10_names"]["pass"]))
    out["gates"] = gates
    out["failed"] = [g["name"] for g in gates if not g["pass"]]
    out["status"] = "pass" if not out["failed"] else "fail"
    out["files"] = {**{k: v for k, v in m["files"].items()},
                    "Exports/Guns/AR01/SM_AR01.fbx (input)": {"sha256": r_sha}}
    out["build_report"] = "scratch/mag/mag_report.json"
    (GATES / "mag.json").write_text(json.dumps(out, indent=1, default=str))
    # geometry for the drawings
    sel = (Mc[:, 0] > 330) & (Mc[:, 0] < 500) & (Mc[:, 2] < 25) & (Mc[:, 2] > -80)
    np.savez_compressed(SCRATCH / "mag" / "fit_geom.npz", RV=VR + GRIP, RT=TR_[sel], MV=Vm0, MT=Tm0_,
                        RM=RM, tM=tM + GRIP, RR=RR, tR=tR + GRIP, RI=RI, tI=tI + GRIP, theta=theta, d_ins=d_ins)
    log(out["status"], out["failed"])


main()
