"""AR-01 magazine-fit hooks for gunlib.drivers.magfit_check (form stage) and gunlib.drivers.mag_fit (stage 6): the rock
path (R51), the lug / tab / catch-window selections and the receiver-sheet seams are the rifle's own data, moved
verbatim from rifle_magfit_check.py and rifle_mag_fit.py (gunlib 0.2.0).
"""
from __future__ import annotations

import json
import math

import numpy as np

from gunlib import game as GM
from gunlib import gateutil as GU
import rifle_magfit as MF
from rifle_common import SPEC

MAG_PARTS = ("magazine", "magazine_floor_plate")
CATCH_BOX = {"X": (355.0, 370.0), "Y": (-5.2, 5.2), "Z": (-70.0, -35.0)}
CATCH_PIVOT = np.array([362.0, -50.0])
CATCH_BOX_M = CATCH_BOX
#: inside the LOD0 receiver's well (between its walls, above its bottom sheet, between the opening's ends): magazine
#: surface here is hidden at EVERY LOD when seated or on the reload path, so its depth inside a coarse rifle LOD's solid
#: blockout changes nothing on screen (the coarse-LOD depth rule counts only points outside this box)
WELL_BOX_M = {"X": (368.8, 432.0), "Y": (-20.75, 20.75), "Z": (-30.85, 11.0)}
SWITCH_M = {1: 2.705, 2: 6.762, 3: 20.287}            # rifle LOD switch-in distances (gates/game.json LOD-pop)


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


def slerp_y(Ra, Rb, u):
    """Rotations that differ about Y only (the rock): interpolate the angle."""
    a = math.atan2(Ra[0, 2], Ra[0, 0])
    b = math.atan2(Rb[0, 2], Rb[0, 0])
    th = a + (b - a) * u
    return np.array([[math.cos(th), 0, math.sin(th)], [0, 1, 0], [-math.sin(th), 0, math.cos(th)]])


def _section(V, T, axis, c):
    """Segments of triangles cut by the plane coord[axis] = c (list of point pairs)."""
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


def _log(*a):
    print("[AR01-fit]", *a, flush=True)


# ================================================================================ form stage (magfit_check)
def form_header(S):
    import bpy
    return {"stage": "2 form: magazine fit (R51 loop-back)", "blend": bpy.data.filepath,
            "path": {"pivot_M": MF.PIVOT.tolist(), "rock_deg": MF.ROCK_DEG, "insert_mm": round(MF.INSERT_D, 4),
                     "approach_mm": MF.APPROACH}, "design": MF.report()}


def form_gates(S):
    """The AR-01's form-stage F-gates (verbatim from rifle_magfit_check.py, on the shared scene S)."""
    from mathutils import Vector
    MV, MT, RV, RT, RL = S.MV, S.MT, S.RV, S.RT, S.RL
    rn, rtree, cV, cT, ctree, hits = S.rn, S.rtree, S.cV, S.cT, S.ctree, S.hits
    gates = []
    # ---------------------------------------------------------------- F1 seated
    n, nc, no, other = hits(MV)
    gates.append(GU.gate("F1 (M1) seated: intersecting triangle pairs, magazine vs the rifle (LOD0)",
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
        rs, ms = GU.section_segs(RV, RT, 2, zp), GU.section_segs(MV, MT, 2, zp)
        rp = rs.reshape(-1, 3)
        mp = ms.reshape(-1, 3)
        if not len(rp) or not len(mp):
            continue
        x0, x1 = mp[:, 0].min(), mp[:, 0].max()
        xc = 0.5 * (x0 + x1)
        rb = GU.band_pts(rs, 1, 0.0, 8.0)
        rb = rb[(rb[:, 0] > x0 - 15) & (rb[:, 0] < x1 + 15)] if len(rb) else rb
        mb = GU.band_pts(ms, 1, 0.0, 8.0)
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
    rs = GU.section_segs(RV, RT[RL == rec_i], 2, zv)
    ms = GU.section_segs(MV, MT, 2, zv)
    edge = {}
    for name, lo, hi in (("front, outside the lug channel", MF.TAB_HW + MF.C_LUG + 0.3, 12.5),
                         ("front, lug channel", 0.0, MF.TAB_HW)):
        sel_r = GU.band_pts(rs, 1, lo, hi)
        sel_r = sel_r[sel_r[:, 0] > 400] if len(sel_r) else sel_r
        sel_m = GU.band_pts(ms, 1, lo, hi)
        if len(sel_r) and len(sel_m):
            edge[name] = round(float(sel_r[:, 0].min() - sel_m[:, 0].max()), 4)
    edge["front_at_Z_M"] = round(zv, 2)
    # rear: the sheet behind the opening is the ledge (its outer face at ledge_z(368.8)), above the guard's tang
    from rifle_parts import ledge_z
    zr = ledge_z(368.8) + 0.12
    sel_r = GU.band_pts(GU.section_segs(RV, RT[RL == rec_i], 2, zr), 1, 0.0, 12.0)
    sel_r = sel_r[(sel_r[:, 0] < 400) & (sel_r[:, 0] > 360)] if len(sel_r) else sel_r
    sel_m = GU.band_pts(GU.section_segs(MV, MT, 2, zr), 1, 0.0, 12.0)
    if len(sel_r) and len(sel_m):
        edge["rear (receiver sheet behind the opening)"] = round(float(sel_m[:, 0].min() - sel_r[:, 0].max()), 4)
    edge["rear_at_Z_M"] = round(zr, 2)
    # rear seam down the trigger guard's front tab (side view: the tab's front face against the rear spine)
    gi = rn.index("trigger_guard") if "trigger_guard" in rn else -1
    tab = {}
    for zt in (-29.6, -30.5, -31.5, -32.5, -33.5, -34.5):
        r_ = GU.band_pts(GU.section_segs(RV, RT[RL == gi], 2, zt), 1, 0.0, 8.0) if gi >= 0 else np.zeros((0, 3))
        m_ = GU.band_pts(GU.section_segs(MV, MT, 2, zt), 1, 0.0, 8.0)
        r_ = r_[(r_[:, 0] > 360) & (r_[:, 0] < 372)] if len(r_) else r_
        m_ = m_[m_[:, 0] < 400] if len(m_) else m_
        if len(r_) and len(m_):
            tab[str(zt)] = round(float(m_[:, 0].min() - r_[:, 0].max()), 3)
    edge["rear down the guard tab (Z: gap)"] = tab
    ok2 = 0.1 <= top_gap <= 0.5 and max(v["gap_mm"] for v in seams.values()) <= 0.6
    gates.append(GU.gate("F2 (M2) top stop; seam at the well's lower edge (M2 sections)",
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
        lat[side] = round(GU.nearest(Ss[sel & zwin], rtree, 10.0), 4)
    P0 = MF.PIVOT
    lugsel = (Ss[:, 0] - P0[0] > -8.0) & (Ss[:, 2] - P0[1] > -14.0) & (np.abs(Ss[:, 1]) < 7.0)
    d_lug = GU.nearest(Ss[lugsel], rtree, 20.0)
    tabsel = (Ss[:, 0] > MF.TAB_X0 + 1.0) & (Ss[:, 2] > MF.TAB_Z[0] - 0.05) & (np.abs(Ss[:, 1]) < MF.TAB_HW)
    d_tab = GU.nearest(Ss[tabsel], rtree, 20.0)
    rl = (Ss[:, 0] > 366.0) & (Ss[:, 0] < 374.0) & (Ss[:, 2] > -40.5) & (Ss[:, 2] < -34.5) & (np.abs(Ss[:, 1]) < 6)
    d_rear = GU.nearest(Ss[rl], ctree, 10.0) if ctree else None
    m3 = {"lateral_mm": lat, "front_lug_to_nearest_rifle_mm (M3 selection)": round(d_lug, 4),
          "hook_tab_to_its_pocket_mm": round(d_tab, 4), "rear_lug_to_catch_mm": None if d_rear is None else round(d_rear, 4)}
    ok3 = all(0.2 - 1e-3 <= v <= 0.6 for v in lat.values()) and 0.1 <= d_lug <= 0.4 and d_rear is not None and \
        0.0 <= d_rear <= 0.3
    gates.append(GU.gate("F3 (M3) lateral per side; front lug in its recess; rear lug to the catch", m3,
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
            dep = GU.depth_inside(GM.dense_samples(Q, MT, 0.4), ctree, cb_lo, cb_hi)
            catch_hits.append({"phase": kind, "rock_deg": deg, "insert_mm": round(s, 3), "pairs": nc, "depth_mm": round(dep, 3)})
        if no:
            other_hits.append({"phase": kind, "rock_deg": deg, "insert_mm": round(s, 3), "pairs": no, "parts": other})
    ok_catch = all(h["phase"] == "rock" and h["rock_deg"] <= 6.0 and h["depth_mm"] <= 3.0 for h in catch_hits)
    ok4 = not [h for h in other_hits if h["phase"] != "approach"] and ok_catch
    gates.append(GU.gate("F4 (M4/M5) reload path: insert 0.5 mm, rock 0.25 deg (+ the approach from under the receiver)",
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
    gates.append(GU.gate("F4b (info) the reload clip's vertical drop into MagInsertStart (last 40 mm, 0.5 mm steps)",
                      {"steps": 81, "intersecting_steps": len(vd), "first": vd[:4]}, "reported (0 expected)", True))
    # ---------------------------------------------------------------- F5 catch release with the magazine seated
    rel = []
    mtree = GU.tree(MV, MT)
    if ctree:
        for a in np.arange(0.0, 10.0001, 0.25):
            Vc = rot_catch(cV, a)
            rel.append((round(float(a), 2), len(GU.tree(Vc, cT).overlap(mtree))))
    ok5 = all(n == 0 for _, n in rel)
    gates.append(GU.gate("F5 catch release sweep 0-10 deg with the magazine seated", {"steps": len(rel),
                      "intersecting_steps": sum(1 for _, n in rel if n)}, "0", ok5))
    # ---------------------------------------------------------------- F8 vertical insert (info)
    vert = []
    for d in np.arange(30.0, -1e-9, -0.5):
        Q = MV + np.array([0.0, 0.0, -d])
        vert.append((round(float(d), 2), hits(Q)[0]))
    hit = [v for v in vert if v[1]]
    gates.append(GU.gate("F8 (M8, info) straight vertical insert without the rock", {"colliding_steps": len(hit),
                      "first": hit[:3]}, "reported (expected to collide)", True))
    return gates


# ================================================================================ stage 6 (mag_fit, shipped bytes)
def stage6_gates(F, out):
    """M6, M1-M5, M8 and the build-report gates of the AR-01 (verbatim from rifle_mag_fit.py on the shared scene)."""
    from mathutils import Vector
    rifle, mag, rs, ms, sk = F.gun, F.mag, F.gs, F.ms, F.sk
    GRIP = F.grip
    gates = []

    def place(k, R, t):
        return F.place(k, R, t)
    # frame check: the imported rifle (mag faces excluded) spans the SK rest AABB (same parts) in frame B
    V0, T0, Tm0 = rifle[0]
    used = np.unique(T0)
    lo, hi = V0[used].min(0), V0[used].max(0)
    rlo, rhi = (np.array(x) for x in F.RIG["bounds_extension"]["rest_aabb_mm"])
    frame_err = float(max(np.abs(lo - rlo).max(), np.abs(hi - rhi).max()))
    out["import_frame_check_mm"] = round(frame_err, 5)
    _log("frame check", frame_err)
    # ------------------------------------------------------------ sockets
    rs = {s["socket"]: s for s in json.loads((F.EXP / "SM_AR01.sockets.json").read_text())["sockets"]}
    ms = {s["socket"]: s for s in json.loads((F.EXP / "SM_AR01_Mag.sockets.json").read_text())["sockets"]}
    sk = {s["name"]: s for s in json.loads((F.EXP / "SK_AR01.skeletal.json").read_text())["sockets"]}
    RM, tM = F.sock_frame(rs["Mag"])
    RR, tR = F.sock_frame(rs["MagRockStart"])
    RI, tI = F.sock_frame(rs["MagInsertStart"])
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
    fitset = {k: np.array(v["blender_mm"]) for k, v in F.RIG.get("fit_set_sockets", {}).items()}
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
    gates.append(GU.gate("M6 reload-path sockets from the exported sidecars vs the fit", m6, "<= 0.001 mm, <= 0.001 deg", ok6,
                      "the rock is a pure rotation about the hook (RockStart at Mag's location); InsertStart lies on the "
                      "tilted mag's -Z; the skeletal and static sidecars agree; the magazine's Mag is its origin"))


    # ------------------------------------------------------------ M1 seated
    rtrees = {k: F.tree(rifle[k][0], rifle[k][1]) for k in rifle}
    m1 = {}
    ok1 = True
    rbox = {k: (rifle[k][0][np.unique(rifle[k][1])].min(0), rifle[k][0][np.unique(rifle[k][1])].max(0)) for k in rifle}
    for a, b in F.pairs:
        Q, T = place(b, RM, tM)
        n = len(rtrees[a].overlap(F.tree(Q, T)))
        row = {"intersecting_triangle_pairs": n}
        if n and max(a, b) >= 2:
            Sq = F.samples(Q, T, 0.5)
            raw = F.depth_inside(Sq, rtrees[a], *rbox[a])
            dep = F.depth_inside(F.visible_only(Sq), rtrees[a], *rbox[a])
            k = max(a, b)
            row.update(depth_mm_outside_well=round(dep, 3), depth_px=round(dep * F.px_per_mm(k), 3), at_m=F.switch_m[k],
                       raw_depth_mm_incl_hidden_well_part=round(raw, 3), raw_px=round(raw * F.px_per_mm(k), 3))
            ok1 &= dep * F.px_per_mm(k) < 1.0
        elif n:
            ok1 = False
        m1[f"rifle LOD{a} / mag LOD{b}"] = row
    gates.append(GU.gate("M1 seated: intersecting triangles, co-visible LOD pairs", m1,
                      "0 (LOD0-1 pairs 0; LOD2-3 pairs: depth under 1 px at the switch distance, counted outside the "
                      "LOD0 well where the magazine is never visible)", ok1,
                      "rifle LOD3 is the blockout silhouette level: its receiver is a solid with no well, so the seated "
                      "magazine's top (hidden inside the well at every LOD) lies inside it; raw depths are recorded"))
    # ------------------------------------------------------------ M2 top stop + seam
    QM, TM = place(0, RM, tM)
    S = F.samples(QM, TM, 0.25)
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
        rs, ms = _section(VR, TR_, 2, zp), _section(QM, TM, 2, zp)
        rp = [p for s_ in rs for p in s_]
        mp = [p for s_ in ms for p in s_]
        if not rp or not mp:
            continue
        rp, mp = np.array(rp), np.array(mp)
        x0, x1 = mp[:, 0].min(), mp[:, 0].max()
        xc = 0.5 * (x0 + x1)
        rb = GU.band_pts(rs, 1, 0.0, 8.0)
        rb = rb[(rb[:, 0] > x0 - 15) & (rb[:, 0] < x1 + 15)] if len(rb) else rb
        mb = GU.band_pts(ms, 1, 0.0, 8.0)
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
    gates.append(GU.gate("M2 seat: top-stop gap; visible seam at the well's lower edge",
                      {"top_stop_gap_mm": round(top_gap, 4), "top_stop_from": None if best[1] is None else
                       np.round(best[1] + GRIP, 2).tolist(), "seam": seams, "receiver_sheet_bottom_Z_M": round(zp + GRIP[2], 3)},
                      "top stop 0.1-0.5 mm; seam <= 0.6 mm (side: front / rear; front view: left / right)", ok2,
                      "fails: see the values (R51 design: front top stop = the hook tab under the trunnion, seam = the "
                      "spine's sweep at the sheet + 0.06, the lug channel at |Y| <= 4.2 is the real pattern's lug slot)"
                      if not ok2 else "R51: the front top stop is the hook tab under the front trunnion; the "
                      "visible-edge numbers per band are in gates/form_magfit.json"))
    # ------------------------------------------------------------ M3 clearances
    Ss = F.samples(QM, TM, 0.2)
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
    Sm = F.samples(Vm0, Tm0_, 0.2)
    lugsel = (Sm[:, 0] > -8.0) & (Sm[:, 2] > -14.0) & (np.abs(Sm[:, 1]) < 7.0)
    lug_pts = Sm[lugsel] @ RM.T + tM
    d_lug, ia = nearest(lug_pts, rtrees[0], cap=20.0)
    # rear lug to the catch face: rifle triangles inside the catch's box
    cm = (Mc[:, 0] >= CATCH_BOX_M["X"][0]) & (Mc[:, 0] <= CATCH_BOX_M["X"][1]) & \
         (Mc[:, 1] >= CATCH_BOX_M["Y"][0]) & (Mc[:, 1] <= CATCH_BOX_M["Y"][1]) & \
         (Mc[:, 2] >= CATCH_BOX_M["Z"][0]) & (Mc[:, 2] <= CATCH_BOX_M["Z"][1])
    ctree = F.tree(VR, TR_[cm])
    # the rear lug's window = the form gate's (F3, rifle_magfit_check.py): the R51 lug's rear face sits at X ~367.3
    rl = (SsM[:, 0] > 366.0) & (SsM[:, 0] < 374.0) & (SsM[:, 2] > -40.5) & (SsM[:, 2] < -34.5) & (np.abs(SsM[:, 1]) < 6)
    d_rear, _ = nearest(Ss[rl], ctree)
    m3 = {"lateral_mm": lat, "front_lug_to_nearest_rifle_mm": round(float(d_lug), 4),
          "rear_lug_to_catch_face_mm": round(float(d_rear), 4)}
    ok3 = all(0.2 - 1e-4 <= v <= 0.6 for v in lat.values()) and 0.1 <= d_lug <= 0.4 and 0.0 <= d_rear <= 0.3
    gates.append(GU.gate("M3 clearances: lateral per side; front lug in its recess; rear lug to the catch face", m3,
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
    ctrees = {k: F.tree(rifle[k][0], rifle[k][1][((rifle[k][0][rifle[k][1]].mean(1) + GRIP) >= np.array(
        [CATCH_BOX_M["X"][0], CATCH_BOX_M["Y"][0], CATCH_BOX_M["Z"][0]])).all(1) & (
        (rifle[k][0][rifle[k][1]].mean(1) + GRIP) <= np.array([CATCH_BOX_M["X"][1], CATCH_BOX_M["Y"][1],
                                                              CATCH_BOX_M["Z"][1]])).all(1)]) for k in rifle}
    path = {}
    worst_other = 0
    dep_cache = {}
    catch_hits = []
    catch_lod23 = []
    for a, b in F.pairs:
        rec = []
        for si, (kind, val, R, t) in enumerate(steps):
            Q, T = place(b, R, t)
            mt = F.tree(Q, T)
            n = len(rtrees[a].overlap(mt))
            nc = len(ctrees[a].overlap(mt)) if n else 0
            rec.append((kind, round(val, 3), n, nc))
            if n - nc > 0:
                if max(a, b) >= 2:
                    if si % 6 == 0 or si == len(steps) - 1:
                        dep = F.depth_inside(F.visible_only(F.samples(Q, T, 1.0)), rtrees[a], *rbox[a])
                        dep_cache.setdefault((a, b), []).append(dep * F.px_per_mm(max(a, b)))
                else:
                    worst_other = max(worst_other, n - nc)
            if nc:
                cb = (np.array([CATCH_BOX_M["X"][0], CATCH_BOX_M["Y"][0], CATCH_BOX_M["Z"][0]]) - GRIP,
                      np.array([CATCH_BOX_M["X"][1], CATCH_BOX_M["Y"][1], CATCH_BOX_M["Z"][1]]) - GRIP)
                cd = F.depth_inside(F.samples(Q, T, 0.5), ctrees[a], *cb)
                hit = {"pair": [a, b], "step": [kind, round(val, 3)], "triangle_pairs": nc, "depth_mm": round(cd, 3)}
                if max(a, b) >= 2:
                    # LOD2-3 pairs: every contact (the catch's included) is judged in pixels at the switch distance
                    hit["depth_px"] = round(cd * F.px_per_mm(max(a, b)), 4)
                    dep_cache.setdefault((a, b), []).append(cd * F.px_per_mm(max(a, b)))
                    catch_lod23.append(hit)
                else:
                    catch_hits.append(hit)
        path[f"rifle LOD{a} / mag LOD{b}"] = {"steps": len(rec), "intersecting_steps": sum(1 for r in rec if r[2]),
                                               "with_catch_only": sum(1 for r in rec if r[2] and r[2] == r[3])}
    deep = {f"rifle LOD{a} / mag LOD{b}": round(max(v), 3) for (a, b), v in dep_cache.items()}
    allowance_ok = all(v < 1.0 for v in deep.values()) and all(h["step"][0] == "rock" and abs(h["step"][1]) <= 6.0 and h["depth_mm"] <= 3.0
                                                            for h in catch_hits)
    ok4 = worst_other == 0 and allowance_ok
    gates.append(GU.gate("M4 rock path (insert 0.5 mm, rock 0.25 deg; co-visible pairs)",
                      {"steps": len(steps), "insert_steps": len(s_vals), "rock_steps": n_rot, "rock_deg": round(theta, 4),
                       "pairs": path, "catch_contacts": catch_hits[:20],
                       "catch_contacts_lod2_3 (px rule)": {"count": len(catch_lod23),
                                                           "worst": max(catch_lod23, key=lambda h: h["depth_px"])
                                                           if catch_lod23 else None},
                       "lod2_3_depth_px (every 6th step + seated)": deep},
                      "0 intersections (LOD0-1 pairs; LOD2-3 pairs: depth < 1 px at the switch distance), except the "
                      "rear lug on the catch nose (<= 3.0 mm, last <= 6 deg)", ok4,
                      "0 contacts at every step: the catch allowance is not used" if ok4 and not catch_hits else None))
    gates.append(GU.gate("M5 removal path (the M4 poses in reverse order)", {"pairs": path},
                      "same as M4", ok4, "the same pose set traversed backwards: identical intersection record"))
    # ------------------------------------------------------------ M8 straight vertical insert (info)
    vert = []
    for d in np.arange(40.0, -1e-9, -0.5):
        Q, T = place(0, RM, tM + np.array([0.0, 0.0, -d]))
        vert.append((round(float(d), 2), len(rtrees[0].overlap(F.tree(Q, T)))))
    hit = [v for v in vert if v[1]]
    gates.append(GU.gate("M8 (info) straight vertical insert without the rock", {"steps": len(vert),
                      "colliding_steps": len(hit), "first": hit[:3]},
                      "reported (expected to collide: proves the rock is needed)", True,
                      "does NOT collide: a straight push seats the magazine as well" if not hit else
                      "collides: the hook tab meets the trunnion's ledge and the rear lug the catch's nose"))
    # ------------------------------------------------------------ the build's gates (qa_check, C1, S1, LODs)
    m = F.MAGREP
    lods = [m["lods"][f"SM_AR01_Mag_LOD{k}"]["triangles"] for k in range(4)]
    gates.append(GU.gate("mag qa_check (LOD0-3, before export)", {"passed": m["qa_check"]["passed"],
                      "triangles": m["qa_check"]["triangles"], "texel_target": m["qa_check"]["texel_target_px_cm"],
                      "checks": m["qa_check"]["checks"]},
                      "pass; budget 7,000; UV1; UCX keyed to the node; texel = measured aggregate +-25 %",
                      m["qa_check"]["passed"]))
    gates.append(GU.gate("mag LODs: strictly descending, plan 3.3 targets", lods,
                      "LOD0 <= 7,000 (target ~4,500); LOD1 ~1,750; LOD2 ~580; LOD3 200-300",
                      lods[0] <= 7000 and lods[0] > lods[1] > lods[2] > lods[3] and 200 <= lods[3] <= 300,
                      "LOD0 6,868 is the detail-pass magazine (over the ~4,500 target, under the 7,000 ceiling); LOD1-3 "
                      "collapse-decimated from LOD0 (UV0 interpolated: the LOD0 maps stay valid; fold-overs relaxed, "
                      "overlaps separated: %s)" % json.dumps(m.get("uv0_overlap_fix"))))
    gates.append(GU.gate("C1 mag hull containment", m["C1"], "0 and 0; 2 hulls (spec collision_static_twin.mag), <= 32 "
                      "vertices", m["C1"]["pass"],
                      "2 hulls, not 1: one hull would fill the curve's ~30 mm sagitta (plan 7.1, spec, gun study 5.6)"))
    gates.append(GU.gate("S1 mag sockets (exported sidecar vs build)", {"count": len(m["S1"]["sockets"]),
                      "worst_mm": m["S1"]["worst_mm"], "worst_deg": m["S1"]["worst_deg"],
                      "names_match_spec": m["S1"]["names_match_spec"]},
                      "5 = spec names; <= 0.001 mm, <= 0.001 deg", m["S1"]["pass"]))
    gates.append(GU.gate("mag LOD screen sizes derived from the rifle's", m["lod_screen_sizes"],
                      "size_mag = size_rifle x r_mag / r_rifle", True))
    gates.append(GU.gate("B10 mag names", m["B10_names"], "no hit", m["B10_names"]["pass"]))
    tw = m.get("twin_mag_equal", {"pass": False, "lods": "missing (rifle_mag.twin_mag_check did not run)"})
    gates.append(GU.gate("Twin magazine = SM_AR01_Mag at every LOD (stage-7 fix round)", tw["lods"],
                      "per LOD: equal triangles; vertex sets within 0.001 mm both ways", tw["pass"],
                      "the static twin's merged magazine at LOD n is the shipped SM_AR01_Mag_LOD n (rifle_maglod: one "
                      "recipe for both)"))
    # geometry for the drawings
    sel = (Mc[:, 0] > 330) & (Mc[:, 0] < 500) & (Mc[:, 2] < 25) & (Mc[:, 2] > -80)
    F.geom = dict(RV=VR + GRIP, RT=TR_[sel], MV=Vm0, MT=Tm0_,
                        RM=RM, tM=tM + GRIP, RR=RR, tR=tR + GRIP, RI=RI, tI=tI + GRIP, theta=theta, d_ins=d_ins)
    return gates

