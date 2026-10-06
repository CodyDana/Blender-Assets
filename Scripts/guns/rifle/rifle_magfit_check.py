"""AR-01 magazine fit at the FORM stage (R51 loop-back): the stage-6 M-gates' geometry checks run on the built LOD0
parts (frame M), so a well / trunnion / lug change is proven before the UV, rig and export stages:

    blender -b <AR01.blend | scratch/AR01_form_partial.blend> --factory-startup --python Scripts/guns/rifle/rifle_magfit_check.py -- [--out json]

The magazine (magazine + magazine_floor_plate) moves along the reload path from the spec sockets (rifle_magfit:
MagInsertStart -> MagRockStart along the tilted -Z, then the rock about the Mag socket), against every other part:
- F1 seated: intersecting triangle pairs (M1 at LOD0);
- F2 top stop (rays up from the magazine's top 4 mm, M2) and the seam at the well's lower edge (horizontal sections
  through the bottom sheet as the M2 gate cuts them: front / rear for |Y| < 8, sides over the mid 60 %), plus the
  seam at the sheet's OUTER face across the width outside the lug channel and the channel itself (reported);
- F3 lateral per side, the front lug to its nearest rifle surface (the M3 selection about the Mag origin), the rear
  lug to the catch;
- F4 the path: insert 0.5 mm steps, rock 0.25 deg steps (M4), and the approach from under the receiver (14 mm more
  along the insert line, info): 0 intersections except the rear lug on the catch (<= 3.0 mm, last <= 6 deg);
- F5 the catch's release sweep (0-10 deg, 0.25 deg) with the magazine seated: 0 intersections, the magazine is never
  lifted; F8 (info) a straight vertical insert collides.
Writes WorkFiles/guns/rifle/gates/form_magfit.json (default).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rifle_common import GRIP, GATES  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

from gunlib import game as GM  # noqa: E402
import rifle_magfit as MF  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = Path(argv[argv.index("--out") + 1]) if "--out" in argv else GATES / "form_magfit.json"
COLL = argv[argv.index("--collection") + 1] if "--collection" in argv else "AR01_Parts"
MAG_PARTS = ("magazine", "magazine_floor_plate")
CATCH_BOX = {"X": (355.0, 370.0), "Y": (-5.2, 5.2), "Z": (-70.0, -35.0)}
CATCH_PIVOT = np.array([362.0, -50.0])


def log(*a):
    print("[AR01-magfit]", *a, flush=True)


def mesh_np(o):
    me = o.data
    V = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", V)
    V = V.reshape(-1, 3)
    M = np.array(o.matrix_world)
    V = (np.c_[V, np.ones(len(V))] @ M.T)[:, :3] * 1000.0 + GRIP          # frame M, mm
    me.calc_loop_triangles()
    T = np.empty(len(me.loop_triangles) * 3, int)
    me.loop_triangles.foreach_get("vertices", T)
    return V, T.reshape(-1, 3)


def tree(V, T):
    return BVHTree.FromPolygons([tuple(v) for v in V], [tuple(int(i) for i in t) for t in T], all_triangles=True,
                                epsilon=0.0)


def pose3(V, phi, s=0.0):
    """3D points of the magazine (frame M) at rock phi / insert s (rotation about Y through the pivot)."""
    Q = MF.pose_xz(V[:, [0, 2]], phi, s)
    return np.c_[Q[:, 0], V[:, 1], Q[:, 1]]


def rot_catch(V, deg):
    """Catch rotated about its pin, + = top rearward (the bone's range 0-10)."""
    a = math.radians(deg)
    d = V[:, [0, 2]] - CATCH_PIVOT
    c, s = math.cos(a), math.sin(a)
    x = CATCH_PIVOT[0] + d[:, 0] * c - d[:, 1] * s
    z = CATCH_PIVOT[1] + d[:, 0] * s + d[:, 1] * c
    return np.c_[x, V[:, 1], z]


def section(V, T, axis, c):
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
    out = []
    for i in np.nonzero(cnt == 2)[0]:
        q = [P[k][i] for k in range(3) if m_[k][i]]
        out += q
    return np.array(out) if out else np.zeros((0, 3))


def section_segs(V, T, axis, c):
    """Segments (n x 2 x 3) where the plane coord[axis] = c cuts the triangles."""
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
    out = []
    for i in np.nonzero(cnt == 2)[0]:
        q = [P[k][i] for k in range(3) if m_[k][i]]
        out.append(q)
    return np.array(out) if out else np.zeros((0, 2, 3))


def band_pts(segs, axis, lo, hi):
    """Endpoints of the segments clipped to lo <= |coord[axis]| <= hi (a plane section measured on its segments, not
    only on the mesh's vertices: long faces cross a band with no vertex in it)."""
    out = []
    for a, b in segs:
        for sgn in (1.0, -1.0):
            ya, yb = sgn * a[axis], sgn * b[axis]
            t0, t1 = 0.0, 1.0
            d = yb - ya
            for bound, keep_above in ((lo, True), (hi, False)):
                if abs(d) < 1e-12:
                    ok = (ya >= bound) if keep_above else (ya <= bound)
                    if not ok:
                        t0, t1 = 1.0, 0.0
                    continue
                t = (bound - ya) / d
                if keep_above:
                    if d > 0:
                        t0 = max(t0, t)
                    else:
                        t1 = min(t1, t)
                else:
                    if d > 0:
                        t1 = min(t1, t)
                    else:
                        t0 = max(t0, t)
            if t0 <= t1:
                out += [a + (b - a) * t0, a + (b - a) * t1]
    return np.array(out) if out else np.zeros((0, 3))


def nearest(points, t, cap=20.0):
    b = cap
    for p in points:
        h = t.find_nearest(Vector(p), b)
        if h[0] is not None and h[3] < b:
            b = h[3]
    return float(b)


def depth_inside(points, t, lo, hi, cap=30.0):
    dirs = [Vector((0.31, 0.53, 0.79)).normalized(), Vector((-0.62, 0.21, -0.75)).normalized(),
            Vector((0.12, -0.91, 0.40)).normalized()]

    def parity(p, d):
        n, o = 0, Vector(p)
        for _ in range(64):
            h = t.ray_cast(o, d, 2000.0)
            if h[0] is None:
                break
            n += 1
            o = h[0] + d * 1e-4
        return n % 2 == 1
    best = 0.0
    for p in points:
        if np.any(p < lo) or np.any(p > hi):
            continue
        h = t.find_nearest(Vector(p), cap)
        if h[0] is None or h[3] <= best:
            continue
        if sum(parity(p, d) for d in dirs) >= 2:
            best = h[3]
    return best


def gate(name, value, threshold, ok, note=None):
    g = {"name": name, "value": value, "threshold": threshold, "pass": bool(ok)}
    if note:
        g["note"] = note
    return g


def main():
    objs = [o for o in bpy.data.collections[COLL].objects if o.type == "MESH"]
    parts = {o.name: mesh_np(o) for o in objs}
    mV = [parts[n] for n in MAG_PARTS if n in parts]
    off = 0
    Vs, Ts = [], []
    for V, T in mV:
        Vs.append(V)
        Ts.append(T + off)
        off += len(V)
    MV, MT = np.vstack(Vs), np.vstack(Ts)
    rn = [n for n in parts if n not in MAG_PARTS]
    RV, RT, RL = [], [], []
    off = 0
    for i, n in enumerate(rn):
        V, T = parts[n]
        RV.append(V)
        RT.append(T + off)
        RL += [i] * len(T)
        off += len(V)
    RV, RT, RL = np.vstack(RV), np.vstack(RT), np.array(RL)
    rtree = tree(RV, RT)
    ci = rn.index("mag_catch") if "mag_catch" in rn else -1
    cV, cT = parts.get("mag_catch", (np.zeros((0, 3)), np.zeros((0, 3), int)))
    ctree = tree(cV, cT) if len(cT) else None
    gates, out = [], {"stage": "2 form: magazine fit (R51 loop-back)", "blend": bpy.data.filepath,
                      "path": {"pivot_M": MF.PIVOT.tolist(), "rock_deg": MF.ROCK_DEG, "insert_mm": round(MF.INSERT_D, 4),
                               "approach_mm": MF.APPROACH}, "design": MF.report()}

    def hits(V):
        """(n rifle tri pairs, n with the catch, n with other parts, other part names)."""
        pairs = rtree.overlap(tree(V, MT))
        if not pairs:
            return 0, 0, 0, []
        labs = RL[[p[0] for p in pairs]]
        nc = int((labs == ci).sum())
        other = sorted({rn[k] for k in labs if k != ci})
        return len(pairs), nc, len(pairs) - nc, other
    # ---------------------------------------------------------------- F1 seated
    n, nc, no, other = hits(MV)
    gates.append(gate("F1 (M1) seated: intersecting triangle pairs, magazine vs the rifle (LOD0)",
                      {"pairs": n, "parts": other + (["mag_catch"] if nc else [])}, "0", n == 0))
    # ---------------------------------------------------------------- F2 top stop + seams
    S = GM.dense_samples(MV, MT, 0.25)
    ztop = S[:, 2].max()
    top = S[S[:, 2] > ztop - 4.0]
    best = (1e9, None)
    for p in top:
        h = rtree.ray_cast(Vector(p) + Vector((0, 0, 1e-4)), Vector((0, 0, 1)), 60.0)
        if h[0] is not None and h[3] < best[0]:
            best = (h[3], p)
    top_gap = float(best[0])
    rec_i = rn.index("receiver")
    zp_in, zp_out = MF.SHEET_IN_Z, MF.SHEET_OUT_Z
    gaps = {"front": [], "rear": [], "left": [], "right": []}
    for zp in np.arange(zp_out - 0.95, zp_in + 0.5001, 0.1):
        rs, ms = section_segs(RV, RT, 2, zp), section_segs(MV, MT, 2, zp)
        rp = rs.reshape(-1, 3)
        mp = ms.reshape(-1, 3)
        if not len(rp) or not len(mp):
            continue
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
            seams[k] = {"gap_mm": round(g, 4), "at_Z_M": round(z, 2)}
    # the visible lower edge itself: a section just above the sheet's outer face, per Y band (receiver only)
    zv = zp_out + 0.12
    rs = section_segs(RV, RT[RL == rec_i], 2, zv)
    ms = section_segs(MV, MT, 2, zv)
    edge = {}
    for name, lo, hi in (("front, outside the lug channel", MF.TAB_HW + MF.C_LUG + 0.3, 12.5),
                         ("front, lug channel", 0.0, MF.TAB_HW)):
        sel_r = band_pts(rs, 1, lo, hi)
        sel_r = sel_r[sel_r[:, 0] > 400] if len(sel_r) else sel_r
        sel_m = band_pts(ms, 1, lo, hi)
        if len(sel_r) and len(sel_m):
            edge[name] = round(float(sel_r[:, 0].min() - sel_m[:, 0].max()), 4)
    edge["front_at_Z_M"] = round(zv, 2)
    # rear: the sheet behind the opening is the ledge (its outer face at ledge_z(368.8)), above the guard's tang
    from rifle_parts import ledge_z
    zr = ledge_z(368.8) + 0.12
    sel_r = band_pts(section_segs(RV, RT[RL == rec_i], 2, zr), 1, 0.0, 12.0)
    sel_r = sel_r[(sel_r[:, 0] < 400) & (sel_r[:, 0] > 360)] if len(sel_r) else sel_r
    sel_m = band_pts(section_segs(MV, MT, 2, zr), 1, 0.0, 12.0)
    if len(sel_r) and len(sel_m):
        edge["rear (receiver sheet behind the opening)"] = round(float(sel_m[:, 0].min() - sel_r[:, 0].max()), 4)
    edge["rear_at_Z_M"] = round(zr, 2)
    # rear seam down the trigger guard's front tab (side view: the tab's front face against the rear spine)
    gi = rn.index("trigger_guard") if "trigger_guard" in rn else -1
    tab = {}
    for zt in (-29.6, -30.5, -31.5, -32.5, -33.5, -34.5):
        r_ = band_pts(section_segs(RV, RT[RL == gi], 2, zt), 1, 0.0, 8.0) if gi >= 0 else np.zeros((0, 3))
        m_ = band_pts(section_segs(MV, MT, 2, zt), 1, 0.0, 8.0)
        r_ = r_[(r_[:, 0] > 360) & (r_[:, 0] < 372)] if len(r_) else r_
        m_ = m_[m_[:, 0] < 400] if len(m_) else m_
        if len(r_) and len(m_):
            tab[str(zt)] = round(float(m_[:, 0].min() - r_[:, 0].max()), 3)
    edge["rear down the guard tab (Z: gap)"] = tab
    ok2 = 0.1 <= top_gap <= 0.5 and max(v["gap_mm"] for v in seams.values()) <= 0.6
    gates.append(gate("F2 (M2) top stop; seam at the well's lower edge (M2 sections)",
                      {"top_stop_gap_mm": round(top_gap, 4), "top_stop_from_M": None if best[1] is None else
                       np.round(best[1], 2).tolist(), "seam": seams, "visible_edge_at_outer_face": edge},
                      "top stop 0.1-0.5 mm; seam <= 0.6 mm (clearance table visible seam 0.2-0.8)", ok2,
                      "the lug channel (the real pattern's slot for the front lug at the front of the well, TAB_HW "
                      "wide) is reported separately: the hook tab rises through it from under the receiver"))
    # ---------------------------------------------------------------- F3 clearances
    Ss = GM.dense_samples(MV, MT, 0.2)
    zwin = (Ss[:, 2] > -34.0) & (Ss[:, 2] < -27.0)
    lat = {}
    for side, sel in (("left", Ss[:, 1] > 11.0), ("right", Ss[:, 1] < -11.0)):
        lat[side] = round(nearest(Ss[sel & zwin], rtree, 10.0), 4)
    P0 = MF.PIVOT
    lugsel = (Ss[:, 0] - P0[0] > -8.0) & (Ss[:, 2] - P0[1] > -14.0) & (np.abs(Ss[:, 1]) < 7.0)
    d_lug = nearest(Ss[lugsel], rtree, 20.0)
    tabsel = (Ss[:, 0] > MF.TAB_X0 + 1.0) & (Ss[:, 2] > MF.TAB_Z[0] - 0.05) & (np.abs(Ss[:, 1]) < MF.TAB_HW)
    d_tab = nearest(Ss[tabsel], rtree, 20.0)
    rl = (Ss[:, 0] > 366.0) & (Ss[:, 0] < 374.0) & (Ss[:, 2] > -40.5) & (Ss[:, 2] < -34.5) & (np.abs(Ss[:, 1]) < 6)
    d_rear = nearest(Ss[rl], ctree, 10.0) if ctree else None
    m3 = {"lateral_mm": lat, "front_lug_to_nearest_rifle_mm (M3 selection)": round(d_lug, 4),
          "hook_tab_to_its_pocket_mm": round(d_tab, 4), "rear_lug_to_catch_mm": None if d_rear is None else round(d_rear, 4)}
    ok3 = all(0.2 - 1e-3 <= v <= 0.6 for v in lat.values()) and 0.1 <= d_lug <= 0.4 and d_rear is not None and \
        0.0 <= d_rear <= 0.3
    gates.append(gate("F3 (M3) lateral per side; front lug in its recess; rear lug to the catch", m3,
                      "0.2-0.6; 0.1-0.4; 0.0-0.3 mm", ok3))
    # ---------------------------------------------------------------- F4 path
    poses = MF.path(n_insert=int(round(MF.INSERT_D / 0.5)) + 1, n_rock=int(math.ceil(MF.ROCK_DEG / 0.25)) + 1,
                    approach=MF.APPROACH)
    cb_lo = np.array([CATCH_BOX["X"][0], CATCH_BOX["Y"][0], CATCH_BOX["Z"][0]])
    cb_hi = np.array([CATCH_BOX["X"][1], CATCH_BOX["Y"][1], CATCH_BOX["Z"][1]])
    rec4 = {"approach": [], "insert": [], "rock": []}
    catch_hits, other_hits = [], []
    for phi, s in poses:
        kind = "approach" if s > MF.INSERT_D + 1e-6 else ("insert" if abs(phi - MF.ROCK) < 1e-9 and s > 1e-9 else "rock")
        Q = pose3(MV, phi, s)
        n, nc, no, other = hits(Q)
        rec4[kind].append(n)
        deg = round(math.degrees(phi), 3)
        if nc and ctree:
            dep = depth_inside(GM.dense_samples(Q, MT, 0.4), ctree, cb_lo, cb_hi)
            catch_hits.append({"phase": kind, "rock_deg": deg, "insert_mm": round(s, 3), "pairs": nc, "depth_mm": round(dep, 3)})
        if no:
            other_hits.append({"phase": kind, "rock_deg": deg, "insert_mm": round(s, 3), "pairs": no, "parts": other})
    ok_catch = all(h["phase"] == "rock" and h["rock_deg"] <= 6.0 and h["depth_mm"] <= 3.0 for h in catch_hits)
    ok4 = not [h for h in other_hits if h["phase"] != "approach"] and ok_catch
    gates.append(gate("F4 (M4/M5) reload path: insert 0.5 mm, rock 0.25 deg (+ the approach from under the receiver)",
                      {"steps": {k: len(v) for k, v in rec4.items()},
                       "intersecting_steps": {k: sum(1 for x in v if x) for k, v in rec4.items()},
                       "catch_contacts": catch_hits, "other_contacts": other_hits[:12]},
                      "0 intersections on insert + rock except the rear lug on the catch nose (<= 3.0 mm, last <= 6 "
                      "deg); approach reported (0 expected)", ok4 and not other_hits))
    # ---------------------------------------------------------------- F4b the reload clip's drop (info)
    # rifle_clips.py brings the magazine to MagInsertStart along the weapon's -Z (DROP_MM 160): the last 40 mm of it
    vd = []
    for d in np.arange(40.0, -1e-9, -0.5):
        Q = pose3(MV, MF.ROCK, MF.INSERT_D) + np.array([0.0, 0.0, -d])
        n, nc, no, other = hits(Q)
        if n:
            vd.append({"drop_mm": round(float(d), 2), "pairs": n, "parts": other + (["mag_catch"] if nc else [])})
    gates.append(gate("F4b (info) the reload clip's vertical drop into MagInsertStart (last 40 mm, 0.5 mm steps)",
                      {"steps": 81, "intersecting_steps": len(vd), "first": vd[:4]}, "reported (0 expected)", True))
    # ---------------------------------------------------------------- F5 catch release with the magazine seated
    rel = []
    mtree = tree(MV, MT)
    if ctree:
        for a in np.arange(0.0, 10.0001, 0.25):
            Vc = rot_catch(cV, a)
            rel.append((round(float(a), 2), len(tree(Vc, cT).overlap(mtree))))
    ok5 = all(n == 0 for _, n in rel)
    gates.append(gate("F5 catch release sweep 0-10 deg with the magazine seated", {"steps": len(rel),
                      "intersecting_steps": sum(1 for _, n in rel if n)}, "0", ok5))
    # ---------------------------------------------------------------- F8 vertical insert (info)
    vert = []
    for d in np.arange(30.0, -1e-9, -0.5):
        Q = MV + np.array([0.0, 0.0, -d])
        vert.append((round(float(d), 2), hits(Q)[0]))
    hit = [v for v in vert if v[1]]
    gates.append(gate("F8 (M8, info) straight vertical insert without the rock", {"colliding_steps": len(hit),
                      "first": hit[:3]}, "reported (expected to collide)", True))
    out["gates"] = gates
    out["failed"] = [g["name"] for g in gates if not g["pass"]]
    out["status"] = "pass" if not out["failed"] else "fail"
    OUT.write_text(json.dumps(out, indent=1, default=str))
    for g in gates:
        log("PASS" if g["pass"] else "FAIL", g["name"], json.dumps(g["value"], default=str)[:400])
    log("MAGFIT", out["status"], out["failed"])


main()
