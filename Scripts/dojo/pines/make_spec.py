"""Hand trace (pixels) + reference masks -> pines_spec.json (metres), one entry per variant. System Python (PIL).

Study 4.3: one spec that everything reads (build, measure, wind, judge prep). Per variant:
  * v2 SCALE: the sheet's 1.8 m figure sets the scale of every panel (task, pines v2: heights from the figure,
    not the old 2.5/4.5/7/4 m spec). Origin: the sheet's GROUND row under the trunk (pines A-C: the mound's foot;
    pine D: the rock's ground contact), so the heights are ground-to-apex like the sheet (A 2.2-2.5, B 3.4-3.6,
    C 4.3-4.5, D 3.6-3.9 m). The traced trunk base (the mound top, about 0.2 m up) continues down to z = 0.
  * x, z from the front-like panel; depth y from the side panel (trunk y(z); pads matched to side pads with a reuse
    penalty (P53); limbs blend from the trunk's y to their pad's y);
  * v2 GIRTH: the trunk diameter at 1/4 of the tree height is the sheet's, measured per panel with a pixel ruler
    (measure_ref_v2.py crops, perpendicular to the trunk axis; P49: not from a closed wood mask); the profile has a
    strong taper; the side-panel girth sets an elliptical section (e = side / front, clamped 0.7-1.0).
    RENDER_GIRTH calibrates spec radius -> rendered width (relief, lobes, collars); compose measures it back;
  * targets for the gates come from the same masks (study 6.2).
Run: py -3 -B Scripts/dojo/pines/make_spec.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "Scripts" / "vegetation"))

import measure_tree as mt  # noqa: E402
import pines_trace as pt  # noqa: E402
import ref_panels as rp  # noqa: E402

OUT = HERE / "pines_spec.json"
# v2 girth (metres): trunk width at 1/4 of the tree height, perpendicular to the trunk axis, read with a 5x pixel
# ruler on the sheet (WorkFiles/dojo/build/pines/v2work/ruler_*.png), px / (figure px / 1.8 m):
#   P1F 24 px / 85.6 = 0.28   P1Q 22 / 85.6 = 0.26   P1S 20 / 85.6 = 0.23
#   P2F 27 / 85.6 = 0.32      P2Q 28 / 85.6 = 0.33   P2S 22 / 85.6 = 0.26
#   P3F 55 / 80.6 = 0.68      P3Q 43 / 80.6 = 0.53   P3S 32 / 80.6 = 0.40
#   P4F 21 / 80.6 = 0.26      P4Q 30 / 80.6 = 0.37   P4S 29 / 80.6 = 0.36
GIRTH_Q = {"P1F": 0.28, "P1Q": 0.26, "P1S": 0.23, "P2F": 0.32, "P2Q": 0.33, "P2S": 0.26,
           "P3F": 0.68, "P3Q": 0.53, "P3S": 0.40, "P4F": 0.26, "P4Q": 0.37, "P4S": 0.36}
# rendered width / (2 x spec radius) at 1/4 height, measured on the v2 renders (plates, lobes, flare): the spec radius
# is the target over this factor
RENDER_GIRTH = 1.08
# per pine: rosette pad parameters (rosettepad.RosettePadParams) and limb zig-zag (direction change every 15-30 cm)
# v2 s1 (relaunch): sites now cover the dome SURFACE (top + flanks) at a 3D spacing of 12 cm, fans upright;
# the count follows the surface area (15-45, big C pads up to 90: recorded deviation from 15-25).
# v2 r1 look: 15-25 rosettes on the sheet's 0.8-1.2 m pads left them sparse sprigs (front row fill 0.35 against
# 0.55); the sheet's tree panels show rosettes 6-9 cm apart, packed into near-solid domes (about 10-12 across a
# 1 m pad). The rosette SIZE stays the owner's 8-15 cm; the COUNT follows the sheet (recorded deviation from 15-25).
# v2f: 8 cm (C 9 cm) spacing (v2: 9 / 10 cm): the sheet's pad close-ups show brushes 6-7 cm apart that overlap into one dome
ROSETTE = {1: dict(spacing=0.08, ros_h=0.075, seg=0.15, amp=0.22, knuckle=0.32, n_min=15, n_max=130, n_max_big=170,
                   max_thick_ratio=0.40, clump_sp=0.19, clump_r=0.085, clump_in_sp=0.05),
           2: dict(spacing=0.08, ros_h=0.075, seg=0.16, amp=0.22, knuckle=0.32, n_min=15, n_max=130, n_max_big=170,
                   max_thick_ratio=0.40, clump_sp=0.19, clump_r=0.085, clump_in_sp=0.05),
           3: dict(spacing=0.09, ros_h=0.09, ros_scale=1.06, seg=0.20, amp=0.22, knuckle=0.30, n_min=15, n_max=220, n_max_big=300,
                   max_thick_ratio=0.40, clump_sp=0.23, clump_r=0.095, clump_in_sp=0.056),
           4: dict(spacing=0.08, ros_h=0.075, seg=0.15, amp=0.22, knuckle=0.32, n_min=15, n_max=130, n_max_big=170,
                   max_thick_ratio=0.40, clump_sp=0.19, clump_r=0.085, clump_in_sp=0.05)}
ZIG = {1: dict(seg=0.15, amp=0.5, knuckle=0.18), 2: dict(seg=0.20, amp=0.5, knuckle=0.18),
       3: dict(seg=0.28, amp=0.45, knuckle=0.16), 4: dict(seg=0.17, amp=0.5, knuckle=0.18)}
# PineC2's 3/4 view pairs with P3F (broad, leaning); a small depth shear y += k x widens it (front view unchanged).
DEPTH_SHEAR = {"PineC2": 0.25}
# C: "massive and twisted with a knuckle and broken stub" (P3F: a broken stub on the trunk's left flank just under
# the reaching limb, about 0.3 m long, pointing left-down; knuckle swellings where the upper limbs leave)
STUBS = {"PineC1": [dict(t=0.27, az=195.0, elev=-18.0, length=0.34, r_share=0.30)],
         "PineC2": [dict(t=0.33, az=160.0, elev=-10.0, length=0.26, r_share=0.26)]}
TRUNK_KNUCKLES = {"PineC1": dict(t=[0.38, 0.52, 0.70], amp=0.14), "PineC2": dict(t=[0.42, 0.55], amp=0.12),
                  # v2f (judge delta 8, P1F/P2F: gnarled knobs on the S-trunks where the limbs leave)
                  "PineA1": dict(t=[0.30, 0.48, 0.63], amp=0.10), "PineA2": dict(t=[0.32, 0.50], amp=0.10),
                  "PineB1": dict(t=[0.28, 0.45, 0.60], amp=0.09), "PineB2": dict(t=[0.30, 0.52], amp=0.09),
                  "PineD1": dict(t=[0.35, 0.55], amp=0.10), "PineD2": dict(t=[0.38, 0.56], amp=0.10)}
# v2 s14: limb girth read by hand where the pixel march fails (the reaching limb of C is almost as thick as the
# trunk where it leaves it: P3F about 36-44 px across near x 330-350 at 80.6 px/m, 0.25 m by the middle, 0.1 m at the
# far pads; the march took the twig band under the pads and gave 0.18 m). pad index -> (base radius, tip radius)
LIMB_R = {"P3F": {7: (0.21, 0.045), 9: (0.10, 0.035)}, "P3Q": {}}
SEEDS = {"PineA1": 101, "PineA2": 202, "PineB1": 303, "PineB2": 404, "PineC1": 505, "PineC2": 606,
         "PineD1": 707, "PineD2": 808}


def load_panel_masks(sheet, bg, name):
    p = rp.PANELS[name]
    a = sheet.copy()
    for (x0, y0, x1, y1) in p.get("exclude", []):
        a[y0:y1, x0:x1] = bg
    x0, y0, x1, y1 = p["box"]
    m = mt.masks(a[y0:y1, x0:x1], None, bg=bg)
    return m, (x0, y0)


def perp_width(mask, off, pts, i, max_px=90):
    """Width (px) of the mask across the polyline at point i (full-image px)."""
    x0, y0 = off
    P = np.asarray([(p[0], p[1]) for p in pts], dtype=float)
    a = P[max(i - 1, 0)]
    b = P[min(i + 1, len(P) - 1)]
    t = b - a
    t /= max(np.linalg.norm(t), 1e-9)
    n = np.array([-t[1], t[0]])
    h, w = mask.shape
    tot = 0.0
    for sgn in (1, -1):
        d, miss = 0.0, 0
        while d < max_px:
            q = P[i] + sgn * n * d
            xi, yi = int(round(q[0] - x0)), int(round(q[1] - y0))
            if not (0 <= xi < w and 0 <= yi < h) or not mask[yi, xi]:
                miss += 1
                if miss > 2:
                    break
            else:
                miss = 0
            d += 0.5
        tot += max(0.0, d - 1.5)
    return tot


def running_median(x, k=5):
    x = np.asarray(x, float)
    out = x.copy()
    for i in range(len(x)):
        out[i] = np.median(x[max(0, i - k // 2): i + k // 2 + 1])
    return out


def smoothstep(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def panel_frame(name, masks, off, pine):
    """v2: scale from the group's 1.8 m figure; origin at the ground row (x: trunk base, pine D: rock centre)."""
    p = rp.PANELS[name]
    fg = (masks["foliage"] | masks["wood"]) & ~masks["figure"]
    x0, y0 = off
    ys = np.nonzero(fg.any(1))[0]
    apex_y = y0 + int(ys.min())
    s = rp.FIGURE_M / float(p["figure"][1] - p["figure"][0])
    ground = p["ground"]
    if pine == 4:
        rock = np.asarray(pt.TRACE[name]["rock"], float)
        cx = 0.5 * (rock[:, 0].min() + rock[:, 0].max())
        return {"s": s, "ox": cx, "oy": ground, "apex_y": apex_y, "H": (ground - apex_y) * s}
    bx, by = p["base"]
    return {"s": s, "ox": bx, "oy": ground, "apex_y": apex_y, "H": (ground - apex_y) * s}


def to_m(fr, x, y):
    return (x - fr["ox"]) * fr["s"], (fr["oy"] - y) * fr["s"]


def trunk_profile(P, r_q, flare=1.30, tip_share=0.16):
    """v2 strong taper: r(t) over the trunk's arclength fraction t, r(1/4) = r_q, a smooth root swell toward the
    base (the tube builder adds the nebari flare and buttresses on top) and a thin top where it enters the apex."""
    s = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    t = s / max(s[-1], 1e-9)
    f = (1.0 - 0.78 * t) ** 1.35
    f = f / (1.0 - 0.78 * 0.25) ** 1.35
    f = f * (1.0 + (flare - 1.0) * np.exp(-t / 0.07))
    f = np.maximum(f, tip_share)
    return r_q * f


MOUND_OVERRIDE_PX = {"P3F": (258, 530)}   # P3F's mound runs under P3S's panel: read off a 2x crop by hand


def mound_extent(sheet, bg, name):
    """Widest row of the mound band (between the trunk base and the ground row), px (x0, x1)."""
    if name in MOUND_OVERRIDE_PX:
        return MOUND_OVERRIDE_PX[name]
    p = rp.PANELS[name]
    x0, y0, x1, y1 = p["box"]
    a = sheet.copy()
    for (ex0, ey0, ex1, ey1) in p.get("exclude", []):
        a[ey0:ey1, ex0:ex1] = bg
    m = mt.masks(a[y0:y1, x0:x1], None, bg=bg)
    fg = m["fg"] & ~m["figure"]
    best = (0, 0)
    for y in range(p["base"][1] + 2 - y0, p["ground"] - y0):
        xs = np.nonzero(fg[y])[0]
        if len(xs) and xs.max() - xs.min() > best[1] - best[0]:
            best = (int(xs.min()) + x0, int(xs.max()) + x0)
    return best


def build_variant(vname, sheet, bg):
    fname, sname = pt.VARIANTS[vname]
    pine = rp.PANELS[fname]["pine"]
    mF, offF = load_panel_masks(sheet, bg, fname)
    mS, offS = load_panel_masks(sheet, bg, sname)
    fF = panel_frame(fname, mF, offF, pine)
    fS = panel_frame(sname, mS, offS, pine)
    H = round(float(fF["H"]), 3)
    TF, TS = pt.TRACE[fname], pt.TRACE[sname]
    # ---- trunk: x,z front; y(z) from the side trace
    side_tr = np.array([to_m(fS, x, y) for x, y in TS["trunk"]])     # (y, z)
    order = np.argsort(side_tr[:, 1])
    ys_of_z = lambda z: float(np.interp(z, side_tr[order, 1], side_tr[order, 0]))
    trunk_xz = np.array([to_m(fF, x, y) for x, y in TF["trunk"]])
    trunk = np.array([[x, ys_of_z(z), z] for x, z in trunk_xz])
    if pine != 4:
        trunk[:, 1] -= trunk[0, 1]            # the base sits on the origin
        trunk[:, 0] -= trunk[0, 0]
        # the traced base is the mound top: continue the trunk straight down to the ground (z = 0)
        z0 = float(trunk[0, 2])
        if z0 > 0.03:
            k = max(1, int(np.ceil(z0 / 0.08)))
            low = np.array([[trunk[0, 0], trunk[0, 1], z0 * (1 - i / k)] for i in range(k, 0, -1)])
            trunk = np.vstack([low, trunk])
    # ---- v2 girth from the sheet (ruler, per panel), taper, ellipse from the side panel
    wq = GIRTH_Q[fname]
    r_q = 0.5 * wq / RENDER_GIRTH
    # s15: C's leader ended as a 10-18 cm post above its upper pads; the sheet's leader thins into the apex pad
    trunk_min_r = trunk_profile(trunk, r_q, flare=1.18 if pine != 3 else 1.22, tip_share=0.16 if pine != 3 else 0.09)
    base_r = float(trunk_min_r[0])
    ellipse = float(np.clip(GIRTH_Q[sname] / wq, 0.70, 1.0))
    # ---- pads
    side_pads = [(to_m(fS, cx, cy), rx * fS["s"], rt * fS["s"], rb * fS["s"], cx)
                 for cx, cy, rx, rt, rb in TS["pads"]]
    pads = []
    used = [0] * len(side_pads)
    for i, (cx, cy, rx, rt, rb) in enumerate(TF["pads"]):
        (x, z) = to_m(fF, cx, cy)
        rx_m, rt_m, rb_m = rx * fF["s"], rt * fF["s"], rb * fF["s"]
        lo, hi = z - rb_m, z + rt_m
        best, score, bk = None, -1e9, 0
        for k_, ((sy, sz), srx, srt, srb, _) in enumerate(side_pads):
            ov = min(hi, sz + srt) - max(lo, sz - srb)
            # f1: spread the front pads over DISTINCT side pads (r0 stacked several front pads on one side pad,
            # so the side views showed 1-3 merged masses where the sheet has 5-7)
            sc = ov / max(1e-6, min(hi - lo, srt + srb)) - 0.05 * abs(sz - z) - 0.45 * used[k_]
            # v2 s7: the apex is the apex in both views (s6: the enlarged apex took a wide middle side pad)
            if (i == 0) != (k_ == 0):
                sc -= 5.0
            if sc > score:
                best, score, bk = (sy, srx), sc, k_
        used[bk] += 1
        sy, srx = best
        if pine != 4:
            sy -= float(to_m(fS, *TS["trunk"][0])[0])
        # v2 r7 close-up: pads 0.35 x rx deep read as strips of rosettes along the limb; niwaki pads are round-ish
        # in plan (the sheet's side panels show pads nearly as wide as the front ones)
        ry = float(np.clip(srx, 0.60 * rx_m, 1.3 * rx_m))
        pads.append({"centre": [round(x - (trunk_xz[0, 0] if pine != 4 else 0.0), 4), round(sy, 4), round(z, 4)],
                     "rx": round(rx_m, 4), "ry": round(ry, 4), "rz_top": round(rt_m, 4),
                     "rz_bot": round(max(rb_m, 0.03), 4), "yaw": 0.0, "seed": SEEDS[vname] * 100 + i,
                     "holes": 1 if rx_m > 0.35 else 0, "trace": [cx, cy, rx, rt, rb]})
        if i == 0:
            # v2 s6 (owner item 2): the top tiers merge into a ROUNDED crown; the apex pad may be deeper than the
            # flat 2.5-4x pads below it (the sheet's crowns are about 2x wider than tall)
            pads[-1]["max_thick_ratio"] = 0.58
    # ---- traced pad outlines: every foliage pixel of the front panel goes to its nearest pad (distance scaled by
    # the pad's traced box); per column, the top and bottom of that pad's pixels become its profile (study 4.4)
    fol = mF["foliage"].copy()
    if pine != 4:
        fol[int(rp.PANELS[fname]["base"][1] - offF[1]):, :] = False
    ys, xs = np.nonzero(fol)
    X = xs + offF[0]
    Y = ys + offF[1]
    best_d = np.full(len(X), np.inf)
    owner = np.full(len(X), -1)
    for i, (cx, cy, rx, rt, rb) in enumerate(TF["pads"]):
        dy = np.where(Y < cy, (Y - cy) / max(rt, 1), (Y - cy) / max(rb, 1))
        d = ((X - cx) / max(rx, 1)) ** 2 + dy ** 2
        better = d < best_d
        best_d = np.where(better, d, best_d)
        owner = np.where(better, i, owner)
    owner[best_d > 4.0] = -1
    for i, (cx, cy, rx, rt, rb) in enumerate(TF["pads"]):
        m = owner == i
        if m.sum() < 30:
            continue
        cols = np.unique(X[m])
        top = np.array([Y[m][X[m] == c].min() for c in cols], float)
        bot = np.array([Y[m][X[m] == c].max() for c in cols], float)
        top = running_median(top, 7)
        bot = running_median(bot, 7)
        x0c, x1c = float(cols.min()), float(cols.max())
        xm = 0.5 * (x0c + x1c)
        (xm_m, zc_m) = to_m(fF, xm, cy)
        if pine != 4:
            xm_m -= trunk_xz[0, 0]
        prof_x = (cols - xm) * fF["s"]
        prof_t = np.clip((cy - top) * fF["s"], 0.0, None)
        prof_b = np.clip((bot - cy) * fF["s"], 0.0, None)
        # close the ends so the outline returns to the base plane
        prof_x = np.concatenate([[prof_x[0] - 0.02], prof_x, [prof_x[-1] + 0.02]])
        prof_t = np.concatenate([[0.0], prof_t, [0.0]])
        prof_b = np.concatenate([[0.0], prof_b, [0.0]])
        pads[i]["profile"] = {"centre": [round(xm_m, 4), pads[i]["centre"][1], pads[i]["centre"][2]],
                              "hx": round(0.5 * (x1c - x0c) * fF["s"] + 0.02, 4),
                              "x": np.round(prof_x, 4).tolist(), "top": np.round(prof_t, 4).tolist(),
                              "bot": np.round(prof_b, 4).tolist()}
    # ---- limbs
    limbs = []
    feed_idx = {}
    tr3 = trunk
    for li, (pad_i, pts) in enumerate(TF["limbs"]):
        feed_idx[pad_i] = li
    for li, (pad_i, pts) in enumerate(TF["limbs"]):
        parent, parent_t = "trunk", None
        raw = list(pts)
        if raw[0][0] == "L":
            _, ppad, parent_t = raw[0]
            parent = feed_idx[ppad]
            raw = raw[1:]
        # the traced line often runs on to the drooping far tip of the pad; stop it just past the pad centre so
        # the limb does not poke out of the pad as a bare stick (the twig network fills the pad from there)
        pcx, pcy, prx = TF["pads"][pad_i][0], TF["pads"][pad_i][1], TF["pads"][pad_i][2]
        dists = [np.hypot(x - pcx, y - pcy) for x, y in raw]
        k = int(np.argmin(dists))
        if len(raw) > 2 and k < len(raw) - 1:
            raw = raw[: k + 1]
        xz = np.array([to_m(fF, x, y) for x, y in raw])
        if pine != 4:
            xz[:, 0] -= trunk_xz[0, 0]
        pc = np.array(pads[pad_i]["centre"])
        if parent == "trunk":
            j = int(np.argmin((tr3[:, 0] - xz[0, 0]) ** 2 + (tr3[:, 2] - xz[0, 1]) ** 2))
            y0 = tr3[j, 1]
        else:
            y0 = None  # resolved after the parent limb (below)
        limbs.append({"pad": pad_i, "parent": parent, "parent_t": parent_t, "xz": xz, "y0": y0, "pc": pc,
                      "raw_px": raw})
    for L in limbs:
        if L["y0"] is None:
            P = limbs[L["parent"]]["pts3"] if "pts3" in limbs[L["parent"]] else None
            if P is None:
                # resolve parent first
                par = limbs[L["parent"]]
                par["pts3"] = _limb3(par)
                P = par["pts3"]
            s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
            q = np.array([np.interp(L["parent_t"] * s[-1], s, P[:, k]) for k in range(3)])
            L["y0"] = q[1]
            L["xz"] = np.vstack([[q[0], q[2]], L["xz"]])
        if "pts3" not in L:
            L["pts3"] = _limb3(L)
    limbs_out = []
    limbs_r = {}
    for L in limbs:
        raw = L["raw_px"]
        # girth across the limb, away from the trunk junction and the pad (short marches: a long one runs into
        # the twig network under the pads); capped at 0.55 x the trunk radius where it attaches (study 3.2)
        idx = range(1, len(raw) - 1) if len(raw) > 2 else range(len(raw) if len(raw) > 1 else 0)
        ws = [perp_width(mF["wood"], offF, raw, i, 14) for i in idx]
        ws = [w for w in ws if w > 0]
        rb = 0.5 * float(np.percentile(ws, 20)) * fF["s"] if ws else 0.04
        P = L["pts3"]
        jt = int(np.argmin(((tr3 - P[0]) ** 2).sum(1)))
        # v2 r2 look: limbs read too thick against the sheet's (about 5-6 cm on A): cap 0.40 x the trunk radius
        # (C's reaching limb is nearly as thick as the trunk on the sheet: 0.65 there)
        cap = (0.65 if pine == 3 else 0.40) * float(trunk_min_r[jt]) if L["parent"] == "trunk"             else 0.8 * limbs_r.get(L["parent"], rb)
        rb = float(np.clip(rb, 0.02, max(cap, 0.02)))
        t = np.linspace(0, 1, len(P))
        prof = np.clip(rb * (1 - 0.6 * t), 0.012, None)
        ov = LIMB_R.get(fname, {}).get(L["pad"])
        if ov:
            rb = float(min(ov[0], 0.8 * float(trunk_min_r[jt])))
            prof = rb + (ov[1] - rb) * t ** 0.8
        limbs_r[len(limbs_out)] = rb
        limbs_out.append({"pad": L["pad"], "parent": L["parent"], "parent_t": L["parent_t"],
                          "pts": np.round(P, 4).tolist(), "min_r": np.round(prof, 4).tolist(),
                          "r_base_measured": round(rb, 4)})
    bx_ = rp.PANELS[fname]["base"][0] - offF[0]
    by_ = rp.PANELS[fname]["base"][1] - offF[1]
    fol_, wood_ = mF["foliage"].copy(), mF["wood"].copy()
    fol_[by_:, :] = False
    wood_[by_:, :] = False
    crown_w = mt.metrics(fol_, wood_, (bx_, by_), 1.0 / fF["s"])["crown_w_m"]
    shear = DEPTH_SHEAR.get(vname, 0.0)
    if shear:
        trunk[:, 1] += shear * trunk[:, 0]
        for L_ in limbs_out:
            P_ = np.asarray(L_["pts"])
            P_[:, 1] += shear * P_[:, 0]
            L_["pts"] = np.round(P_, 4).tolist()
        for pd_ in pads:
            pd_["centre"][1] = round(pd_["centre"][1] + shear * pd_["centre"][0], 4)
            if "profile" in pd_:
                pd_["profile"]["centre"][1] = round(pd_["profile"]["centre"][1] + shear * pd_["profile"]["centre"][0], 4)
    spec = {"id": f"SM_DKN_{vname}", "variant": vname, "pine": pine, "species": "pinus_thunbergii",
            "style": "niwaki", "front": "-Y",
            "ref": {"sheet": rp.SHEET, "front_panel": fname, "side_panel": sname,
                    "m_per_px_front": round(fF["s"], 5), "m_per_px_side": round(fS["s"], 5)},
            "seed": SEEDS[vname], "height_m": H, "pipe_n": 2.6, "tip_r": 0.0042, "min_twig_r": 0.003,
            "sink_below_m": 0.2, "trunk_exact": True, "pad_method": "rosette", "rosette_pad": ROSETTE[pine],
            "zig": ZIG[pine],
            "girth": {"panel_w_q_m": wq, "side_w_q_m": GIRTH_Q[sname], "ellipse_y": round(ellipse, 3),
                      "render_factor": RENDER_GIRTH, "crown_w_m": crown_w,
                      "trunk_over_crown_sheet": round(wq / max(crown_w, 1e-6), 4),
                      "trunk_over_figure_sheet": round(wq / rp.FIGURE_M, 4)},
            "depth_shear": shear, "plate_spacing": 0.03 if pine == 3 else 0.022,
            "trunk": {"pts": np.round(trunk, 4).tolist(), "min_r": np.round(trunk_min_r, 4).tolist(),
                      "base_r_measured": round(base_r, 4), "ellipse_y": round(ellipse, 3),
                      "sheet_base_z": round(float(trunk_xz[0, 1]) if pine != 4 else 0.0, 4)},
            "limbs": limbs_out, "pads": pads, "apex_pad": 0,
            "stubs": STUBS.get(vname, []), "trunk_knuckles": TRUNK_KNUCKLES.get(vname)}
    if pine != 4:
        # v2 r3 look: the nebari spread read as a volcano; the sheet's roots stay within about 1.6 base radii
        # v2 s11: the sheet's roots leave the trunk ON the mound top and dive into the moss down its flank (s10: the
        # nebari sat under the 0.2 m mound, so the trunk went into the moss like a post)
        sbz = float(trunk_xz[0, 1])
        # (s15: C's 0.5 m base made 1 m roots a skirt; the reach is capped at 0.45 m and the roots are thinner there)
        spec["nebari"] = {"count": 7, "reach": round(min(2.1 * base_r, 0.45), 3),
                          "start_z": round(0.8 * sbz + 0.30 * base_r, 3), "depth": 0.06,
                          "r_share": 0.42 if pine != 3 else 0.30}
        # v2 base mound (SM_DKN_BaseMound_<family>): the sheet's mossy mound, measured on the front and side panels
        # (widest row of the band between the trunk base and the ground; the owner's 1.2-1.5x crown width is not
        # what the sheet shows: 0.65-0.9x, see BUILD_NOTES)
        fx0, fx1 = mound_extent(sheet, bg, fname)
        sx0, sx1 = mound_extent(sheet, bg, sname)
        pF, pS = rp.PANELS[fname], rp.PANELS[sname]
        spec["mound"] = {"rx": round(0.5 * (fx1 - fx0) * fF["s"], 3), "ry": round(0.5 * (sx1 - sx0) * fS["s"], 3),
                         "cx": round((0.5 * (fx0 + fx1) - pF["base"][0]) * fF["s"], 3),
                         "cy": round((0.5 * (sx0 + sx1) - pS["base"][0]) * fS["s"], 3),
                         "h": round((pF["ground"] - pF["base"][1]) * fF["s"], 3),
                         "px_front": [fx0, fx1], "px_side": [sx0, sx1]}
    else:
        rockF = np.array([to_m(fF, x, y) for x, y in TF["rock"]])
        rockS = np.array([to_m(fS, x, y) for x, y in TS["rock"]])
        # f1: the side panel draws the rock lower than the front panel (1.29 vs 1.88 m at spec scale); the front is
        # the height authority, so the side outline's heights are scaled to the front's rock top (the visual hull
        # took the lower of the two and the rock came out squat)
        kz = float(rockF[:, 1].max() / max(rockS[:, 1].max(), 1e-6))
        rockS[:, 1] *= kz
        base = to_m(fF, *TF["trunk"][0])
        spec["rock"] = {"front_xz": np.round(rockF, 4).tolist(), "side_yz": np.round(rockS, 4).tolist(),
                        "base_xz": [round(base[0], 4), round(base[1], 4)], "sink_m": 0.15}
        spec["root_guides_xz"] = [np.round(np.array([to_m(fF, x, y) for x, y in g]), 4).tolist()
                                  for g in TF["roots"]]
        spec["sink_below_m"] = 0.35
    # ---- measured targets from the reference masks (study 6.2)
    bx = rp.PANELS[fname]["base"][0] - offF[0]
    by = rp.PANELS[fname]["base"][1] - offF[1]
    fol, wood = mF["foliage"].copy(), mF["wood"].copy()
    fol[by:, :] = False
    wood[by:, :] = False
    met = mt.metrics(fol, wood, (bx, by), 1.0 / fF["s"])
    spec["targets"] = {k: met[k] for k in ("height_m", "crown_w_m", "crown_x0_m", "crown_x1_m", "crown_base_m",
                                           "lean_m", "foliage_centroid_dx_m", "tiers", "row_fill",
                                           "pad_size_cv", "lr_mass_ratio")}
    spec["targets"]["height_m"] = H
    spec["targets"]["pads_hand"] = len(TF["pads"])
    spec["targets"]["iou_min"] = 0.80
    return spec


# ---- rock stage (2026-09-30, STONE_BUILDING_STUDY.md 8.3): the owner's D rock at ~0.65 x the v2 rock's size
# relative to the tree, the tree set lower onto it, D1 leaning left with a heavier lower S-bend
ROCK_SCALE = 0.65
# the tree's base on the new rock (x, y), read with rock_v3's lobe plans: D1 on the crown lobe, D2 on the front-left
# lobe's top, against the tall block's left face (the v2 x0.65 point sat on that block's rounded edge)
# v2f: D2's tree stands on the top centre of the one fused rock (P4Q: the trunk base at the rock's middle), not
# on the front-left lobe beside a standing slab
D_BASE_XY = {"PineD1": (0.008, 0.06), "PineD2": (0.0, 0.02)}
# rock surface under the trunk base (measured on the v3 dense rock, lab l5 / build log); the build re-seats the
# trunk on the real surface and reports the difference
# v2f: measured on the v2f lab rocks (v2fwork/rock/r2 lab.json, top under the base at 0.8 r)
D_ROCK_TOP = {"PineD1": 1.045, "PineD2": 1.10}
# v2f (judge delta 2, checked on P4F / P4Q): the trunk where it meets the rock is about 1/5-1/6 of the rock's width
# (P4F: ~50 px of ~300 px; the sheet's slender S-trunk on top of the boulder, the roots making the root plate).
# v2's profile (sheet girth at 1/4 height, which falls ON the rock for pine D, x the root swell) gave 0.41 / 0.54 m
# at the base: half the 0.65 x rock's width. Base radius at the rock top (m), tapering to 0.55 x over ~1 m.
D_TRUNK_R0 = {"PineD1": 0.13, "PineD2": 0.15}
# build 1 look: a -0.22 m lean left the trunk rising to the RIGHT of its base (the v2 line); the owner wants it
# leaning LEFT over the rock: -0.45 m over the lower 1 m, the S bend at +-0.10 m
# v2f: final-1 sheet showed D1 rising nearly straight off the rock (P4F: the trunk leans hard left over the rock
# before the S swings back): lean -0.45 -> -0.62 m
D1_BEND = dict(lean=-0.62, lean_h=1.0, s1=-0.10, s1_h=0.6, s2=0.10, s2_h=(0.6, 1.2), heavy=1.08, heavy_h=(0.6, 0.9))


def _d1_dx(h):
    b = D1_BEND
    h = np.asarray(h, float)
    t = np.clip(h / b["lean_h"], 0, 1)
    dx = b["lean"] * t * t * (3 - 2 * t)
    dx = dx + np.where(h < b["s1_h"], b["s1"] * np.sin(np.pi * np.clip(h, 0, None) / b["s1_h"]), 0.0)
    h0, h1 = b["s2_h"]
    dx = dx + np.where((h >= h0) & (h < h1), b["s2"] * np.sin(np.pi * (h - h0) / (h1 - h0)), 0.0)
    return dx


def d_rock_v3(vname, spec):
    """Rescale the traced rock outlines (they stay the rock's 2D authority, at 0.65 x), move the tree onto the new
    rock top (xy to D_BASE_XY, z to D_ROCK_TOP + 1 cm: the root plate spreads over the top), and give D1 the owner's
    left lean and heavier lower S-bend. Trunk, limbs, pads (and their traced profiles) move together."""
    rk = spec["rock"]
    for key in ("front_xz", "side_yz"):
        rk["sheet_" + key] = rk[key]
        rk[key] = np.round(np.asarray(rk[key], float) * ROCK_SCALE, 4).tolist()
    rk["scale"] = ROCK_SCALE
    rk["method"] = "v3: stone study SDF lobes (Scripts/dojo/pines/rock_v3.py)"
    spec["root_guides_xz"] = [np.round(np.asarray(g, float) * ROCK_SCALE, 4).tolist() for g in spec["root_guides_xz"]]
    tp = np.asarray(spec["trunk"]["pts"], float)
    base = tp[0].copy()
    tx, ty = D_BASE_XY[vname]
    shift = np.array([tx - base[0], ty - base[1], D_ROCK_TOP[vname] + 0.01 - base[2]])

    def move(P):
        P = np.asarray(P, float).copy()
        if vname == "PineD1":
            P[..., 0] += _d1_dx(P[..., 2] - base[2])
        return P + shift
    if vname == "PineD1":
        h = tp[:, 2] - base[2]
        h0, h1 = D1_BEND["heavy_h"]
        k = 1.0 + (D1_BEND["heavy"] - 1.0) * np.clip((h1 - h) / (h1 - h0), 0, 1)
        spec["trunk"]["min_r"] = np.round(np.asarray(spec["trunk"]["min_r"]) * k, 4).tolist()
        spec["trunk"]["base_r_measured"] = spec["trunk"]["min_r"][0]
        spec["d1_bend"] = D1_BEND
    rb = D_TRUNK_R0[vname]
    h_ = tp[:, 2] - base[2]
    cap = rb * (0.55 + 0.45 * np.exp(-np.clip(h_, 0, None) / 0.35))
    spec["trunk"]["min_r"] = np.round(np.minimum(np.asarray(spec["trunk"]["min_r"]), cap), 4).tolist()
    spec["trunk"]["base_r_measured"] = spec["trunk"]["min_r"][0]
    spec["trunk"]["d_trunk_r0"] = rb
    spec["trunk"]["pts"] = np.round(move(tp), 4).tolist()
    for L in spec["limbs"]:
        L["pts"] = np.round(move(L["pts"]), 4).tolist()
    for pd in spec["pads"]:
        pd["centre"] = np.round(move(pd["centre"]), 4).tolist()
        if "profile" in pd:
            pd["profile"]["centre"] = np.round(move(pd["profile"]["centre"]), 4).tolist()
    rk["base_xz"] = [round(tx, 4), round(float(spec["trunk"]["pts"][0][2]), 4)]
    rk["tree_shift_m"] = np.round(shift, 4).tolist()
    # the trunk continues only 12 cm into the rock top (t3: the v2 0.35 m sink poked out of the smaller rock's back)
    spec["sink_below_m"] = 0.12
    top = max(float(np.max(np.asarray(pd["centre"])[2] + pd["rz_top"])) for pd in spec["pads"])
    old_h = spec["height_m"]
    spec["height_sheet_m"] = old_h
    spec["height_m"] = round(old_h + shift[2], 3)
    spec["targets"]["height_sheet_m"] = old_h
    spec["targets"]["height_m"] = spec["height_m"]
    return spec


def _limb3(L):
    xz = L["xz"]
    s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(xz, axis=0), axis=1))])
    t = s / max(s[-1], 1e-9)
    y = L["y0"] + (L["pc"][1] - L["y0"]) * smoothstep(t * 1.15)
    return np.stack([xz[:, 0], y, xz[:, 1]], axis=1)


def main():
    sheet = mt.load_rgb(str(ROOT / rp.SHEET))
    bg = mt.background_colour(sheet[20:60, 300:700])
    specs = {v: build_variant(v, sheet, bg) for v in pt.VARIANTS}
    for v in specs:
        if "rock" in specs[v]:
            d_rock_v3(v, specs[v])
    OUT.write_text(json.dumps(specs, indent=1), encoding="utf-8")
    for v, s in specs.items():
        print(v, "H", s["height_m"], "trunk base r", s["trunk"]["base_r_measured"], "pads", len(s["pads"]),
              "limbs", len(s["limbs"]), "crown_w", s["targets"]["crown_w_m"], "row_fill", s["targets"]["row_fill"])


if __name__ == "__main__":
    main()
