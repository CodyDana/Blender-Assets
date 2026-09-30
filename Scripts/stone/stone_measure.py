"""Stone measurer (STONE_BUILDING_STUDY.md 6.1, 6.2, 6.8): reference and render measurements, numpy + PIL only.

Track-neutral: any stone kit imports it or runs it as a CLI (system Python `py -3` or Blender's Python; no bpy).

What it measures
  image values   both value methods of study 3.11 on an image (or a box of it):
                   method A: luma = Rec.709 weights on sRGB; p5 / p25 / p50 / p75 / p95; dark = luma < 0.20;
                             R/B of the mean colour; local std = mean std of luma in 16 px blocks
                   method C: linear Y; p10 / p50 / p90 and p90/p50; dark-joint fraction = Y < 0.45 x median;
                             stone hue / saturation (HSV of the mean linear->sRGB colour of the brightest half)
                   moss share = pixels with hue 50-80 deg and saturation >= 0.28 (study 3.8: hue, never "G > R")
  shape stats    from a trace (stone_trace/1 JSON, source px -> m by its scale) or from a layout JSON (our own 2D
                 stone outlines in metres, `stone_layout/1`): per zone width / height / area (p10, median, p90), area
                 CV, aspect h/w, upright share (h > w), tall share (h > 1.2 w), long share (w > 1.6 h), mean area
                 per third of the height, and (layouts only) crown / corner-radius CV
  gates          SG3 / SG4 (shape, scale-free ratios when the trace scale is uncertain), SG8 (dark-joint fraction),
                 SG9 (shape variety CV), SG10 (p90/p50, local std), SG11 (hue / sat / R/B), SG12 (moss hue) with the
                 study's tolerances and the tolerance floor of 6.2 (a gate is never tighter than the trace's pixel error)

CLI
  py -3 Scripts/stone/stone_measure.py image <png> [--box x0 y0 x1 y1] [--out json]
  py -3 Scripts/stone/stone_measure.py shapes <trace_or_layout.json> [--out json]
  py -3 Scripts/stone/stone_measure.py gates --spec <spec.json> [--out json]
      spec: {"reference": {"image": png, "box": [...], "trace": json}, "ours": {"image": png, "box": [...],
             "layout": json}, "zones": ["body"], "gates": ["SG3", ...]}
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

SCHEMA_LAYOUT = "stone_layout/1"


# ------------------------------------------------------------------------------------------------ io + colour
def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_rgb(path, box=None):
    im = Image.open(path).convert("RGB")
    if box:
        im = im.crop(tuple(int(round(v)) for v in box))
    return np.asarray(im, dtype=np.float64) / 255.0


def srgb_to_linear(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def rgb_to_hsv(rgb):
    """rgb (..., 3) in 0..1 -> hue deg, sat, val."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx = np.max(rgb, axis=-1)
    mn = np.min(rgb, axis=-1)
    d = mx - mn
    h = np.zeros_like(mx)
    nz = d > 1e-9
    rm = nz & (mx == r)
    gm = nz & (mx == g) & ~rm
    bm = nz & ~rm & ~gm
    h[rm] = ((g - b)[rm] / d[rm]) % 6.0
    h[gm] = (b - r)[gm] / d[gm] + 2.0
    h[bm] = (r - g)[bm] / d[bm] + 4.0
    h = h * 60.0
    s = np.where(mx > 1e-9, d / np.maximum(mx, 1e-9), 0.0)
    return h, s, mx


def pct(a, qs):
    a = np.asarray(a, dtype=np.float64).ravel()
    if a.size == 0:
        return [None for _ in qs]
    return [round(float(np.percentile(a, q)), 4) for q in qs]


# ------------------------------------------------------------------------------------------------ image values
def image_values(rgb, mask=None):
    """Both value methods of study 3.11 on an sRGB float image (H, W, 3). mask: optional bool (H, W) of pixels to use
    (e.g. stone-only regions); None = all."""
    H, W, _ = rgb.shape
    m = np.ones((H, W), bool) if mask is None else mask.astype(bool)
    px = rgb[m]
    # method A
    luma = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
    la = luma[m]
    mean = px.mean(axis=0)
    blocks = []
    for y in range(0, H - 15, 16):
        for x in range(0, W - 15, 16):
            if m[y:y + 16, x:x + 16].mean() > 0.8:
                blocks.append(float(luma[y:y + 16, x:x + 16].std()))
    A = {"luma_p5_p25_p50_p75_p95": pct(la, (5, 25, 50, 75, 95)),
         "dark_lt_0.20": round(float((la < 0.20).mean()), 4),
         "R_over_B": round(float(mean[0] / max(mean[2], 1e-6)), 3),
         "local_std_16px": round(float(np.mean(blocks)) if blocks else float("nan"), 4)}
    # method C
    lin = srgb_to_linear(rgb)
    Y = 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]
    ya = Y[m]
    p10, p50, p90 = [float(np.percentile(ya, q)) for q in (10, 50, 90)]
    bright = m & (Y >= p50)
    stone_lin = lin[bright].mean(axis=0)
    stone_srgb = linear_to_srgb(stone_lin)
    h, s, v = rgb_to_hsv(stone_srgb[None, :])
    C = {"Y_p10_p50_p90": [round(p10, 4), round(p50, 4), round(p90, 4)],
         "p90_over_p50": round(p90 / max(p50, 1e-6), 3),
         "dark_joint_fraction": round(float((ya < 0.45 * p50).mean()), 4),
         "stone_hue_deg": round(float(h[0]), 1), "stone_sat": round(float(s[0]), 3),
         "stone_srgb_mean": [round(float(c), 4) for c in stone_srgb]}
    hh, ss, vv = rgb_to_hsv(rgb)
    moss = m & (hh >= 50) & (hh <= 80) & (ss >= 0.28) & (vv > 0.08)
    return {"pixels": int(m.sum()), "size_px": [W, H], "method_A": A, "method_C": C,
            "moss_share": round(float(moss.sum() / max(m.sum(), 1)), 4)}


def measure_image(path, box=None, mask=None):
    rgb = load_rgb(path, box)
    out = image_values(rgb, mask)
    out["image"] = str(path)
    out["box"] = list(box) if box else None
    out["sha256"] = sha256(path)
    return out


# ------------------------------------------------------------------------------------------------ polygons
def poly_area(p):
    p = np.asarray(p, dtype=np.float64)
    x, y = p[:, 0], p[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def hull(pts):
    P = sorted(set((float(a), float(b)) for a, b in pts))
    if len(P) < 3:
        return P

    def cr(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in P:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(P):
        while len(hi) >= 2 and cr(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    return lo[:-1] + hi[:-1]


def shape_of(poly, y_down=False):
    """Width (horizontal extent), height (vertical extent), area, the min-area box (length, breadth, angle of the long
    side from horizontal, deg) and the convexity of one outline. y_down: image coordinates (y grows downward)."""
    p = np.asarray(poly, dtype=np.float64)
    if y_down:
        p = p * np.array([1.0, -1.0])
    area = abs(poly_area(p))
    w = float(p[:, 0].max() - p[:, 0].min())
    h = float(p[:, 1].max() - p[:, 1].min())
    hp = np.asarray(hull(p))
    best = None
    for i in range(len(hp)):
        e = hp[(i + 1) % len(hp)] - hp[i]
        L = math.hypot(*e)
        if L < 1e-12:
            continue
        u = e / L
        v = np.array([-u[1], u[0]])
        a_, b_ = hp @ u, hp @ v
        ext = (a_.max() - a_.min(), b_.max() - b_.min())
        if best is None or ext[0] * ext[1] < best[0] * best[1]:
            ang = math.degrees(math.atan2(u[1], u[0]))
            best = (ext[0], ext[1], ang)
    L_, B_, ang = best if best else (w, h, 0.0)
    if B_ > L_:
        L_, B_, ang = B_, L_, ang + 90.0
    ang = ((ang + 90.0) % 180.0) - 90.0
    ha = abs(poly_area(hp)) if len(hp) >= 3 else area
    return {"w": w, "h": h, "area": area, "len": float(L_), "breadth": float(B_), "long_axis_deg": round(ang, 1),
            "convexity": area / max(ha, 1e-12)}


def dist(vals):
    v = np.asarray(vals, dtype=np.float64)
    if v.size == 0:
        return None
    return {"p10": round(float(np.percentile(v, 10)), 4), "median": round(float(np.median(v)), 4),
            "p90": round(float(np.percentile(v, 90)), 4), "n": int(v.size)}


def cv(vals):
    v = np.asarray(vals, dtype=np.float64)
    if v.size < 2 or abs(v.mean()) < 1e-12:
        return None
    return round(float(v.std() / v.mean()), 3)


def shape_stats(stones, y_down=False, scale=1.0, zone_top=None, zone_bot=None):
    """stones: list of outlines (already filtered). scale: units -> m. Heights 'per third' split the zone's vertical
    range (zone_top .. zone_bot in the outlines' own units) into thirds, top first."""
    S = [shape_of(p, y_down) for p in stones]
    if not S:
        return None
    w = [s["w"] * scale for s in S]
    h = [s["h"] * scale for s in S]
    a = [s["area"] * scale * scale for s in S]
    asp = [s["h"] / max(s["w"], 1e-9) for s in S]
    out = {"n": len(S), "width_m": dist(w), "height_m": dist(h), "area_m2": dist(a), "area_cv": cv(a),
           "aspect_hw": dist(asp), "upright_share": round(float(np.mean([x > 1.0 for x in asp])), 3),
           "tall_share_hw_gt_1.2": round(float(np.mean([x > 1.2 for x in asp])), 3),
           "long_share_w_gt_1.6h": round(float(np.mean([x < 1 / 1.6 for x in asp])), 3),
           "convexity": dist([s["convexity"] for s in S]),
           "width_cv": cv(w), "height_cv": cv(h)}
    ys = [float(np.mean(np.asarray(p)[:, 1])) for p in stones]
    if zone_top is None:
        zone_top, zone_bot = min(ys), max(ys)
    lo, hi = min(zone_top, zone_bot), max(zone_top, zone_bot)
    thirds = []
    for k in range(3):
        a0, a1 = lo + (hi - lo) * k / 3, lo + (hi - lo) * (k + 1) / 3
        sel = [ai for ai, yi in zip(a, ys) if a0 <= yi <= a1 + 1e-9]
        thirds.append(round(float(np.mean(sel)), 4) if sel else None)
    # top first: in image coords (y down) the smallest y is the top; in metres (z up) the largest
    out["mean_area_per_third_top_first"] = thirds if y_down else list(reversed(thirds))
    return out


def trace_shapes(trace):
    """Shape statistics per zone from a stone_trace/1 JSON (dict or path). Stones with conf 'guess' or cut_by_crop
    are excluded (study 6.8). Returns sizes in m (by the trace scale) and the scale-free ratios."""
    if not isinstance(trace, dict):
        trace = json.loads(Path(trace).read_text(encoding="utf-8"))
    ppm = float(trace["scale"]["px_per_m"])
    unc = float(trace["scale"].get("uncertainty", 0.0))
    out = {"source": trace["source"]["path"], "scale_px_per_m": ppm, "scale_uncertainty": unc, "zones": {}}
    zones = sorted({s["zone"] for s in trace["stones"]})
    for z in zones:
        sel = [s["poly"] for s in trace["stones"] if s["zone"] == z and s.get("conf") != "guess"
               and not s.get("cut_by_crop")]
        st = shape_stats(sel, y_down=True, scale=1.0 / ppm)
        if st:
            px = [shape_of(p, True) for p in sel]
            st["stone_px_median"] = round(float(np.median([min(q["w"], q["h"]) for q in px])), 1)
            st["tolerance_floor"] = round(float(trace["resolution"].get("trace_error_px", 1)) /
                                          max(st["stone_px_median"], 1e-6), 3)
        out["zones"][z] = st
    if "cap" in out["zones"] and "body" in out["zones"] and out["zones"]["cap"] and out["zones"]["body"]:
        out["cap_h_over_body_h"] = round(out["zones"]["cap"]["height_m"]["median"] /
                                         out["zones"]["body"]["height_m"]["median"], 3)
        out["cap_w_over_body_w"] = round(out["zones"]["cap"]["width_m"]["median"] /
                                         out["zones"]["body"]["width_m"]["median"], 3)
    return out


def layout_shapes(layout):
    """Shape statistics per zone from a stone_layout/1 JSON: {"schema", "piece", "zones": {name: {"stones": [{"poly":
    [[a, z], ...], "crown": m, "corner_r": [m, ...]}], "z_top": m, "z_bot": m}}} (metres, z up)."""
    if not isinstance(layout, dict):
        layout = json.loads(Path(layout).read_text(encoding="utf-8"))
    out = {"piece": layout.get("piece"), "zones": {}}
    for z, zd in layout["zones"].items():
        sel = [s["poly"] for s in zd["stones"]]
        st = shape_stats(sel, y_down=False, scale=1.0, zone_top=zd.get("z_top"), zone_bot=zd.get("z_bot"))
        if st:
            cr = [s["crown"] for s in zd["stones"] if s.get("crown") is not None]
            rr = [x for s in zd["stones"] for x in (s.get("corner_r") or [])]
            st["crown_m"] = dist(cr)
            st["crown_cv"] = cv(cr)
            st["corner_r_m"] = dist(rr)
            st["corner_r_cv"] = cv(rr)
        out["zones"][z] = st
    zs = out["zones"]
    if zs.get("cap") and zs.get("body"):
        out["cap_h_over_body_h"] = round(zs["cap"]["height_m"]["median"] / zs["body"]["height_m"]["median"], 3)
        out["cap_w_over_body_w"] = round(zs["cap"]["width_m"]["median"] / zs["body"]["width_m"]["median"], 3)
    return out


def joint_stats(stones, y_down=False, tol=0.035, scale=1.0, bed_tol=0.12):
    """SG5 / SG6 (study 6.2) on outlines (a trace in px with y_down + scale, or a layout in m).
    SG5 coursing: for every stone and its nearest right-hand neighbour (vertical overlap > half the smaller height, the
    gap under 0.35 x the median width) the bed is 'continuous' when the two bottoms differ by less than bed_tol x the
    median height; bed_continuity = the share of such pairs; runs_ge4_per_m = straight bed runs of >= 4 stones per m of
    width. SG6 interlock: a 4-way joint is a head joint that continues straight through a bed joint (two head joints,
    one above the other, less than 1.5 x tol apart in x, whose ends meet within tol + 0.3 x the median height)."""
    P = []
    for p in stones:
        q = [(x * scale, (-y if y_down else y) * scale) for x, y in p]
        xs = [a for a, _ in q]
        zs = [b for _, b in q]
        P.append((min(xs), max(xs), min(zs), max(zs)))
    if len(P) < 3:
        return None
    wmed = float(np.median([b[1] - b[0] for b in P]))
    hmed = float(np.median([b[3] - b[2] for b in P]))
    right = {}
    for i, a in enumerate(P):
        best = None
        for j, b in enumerate(P):
            if i == j or b[0] < a[0] + 0.3 * (a[1] - a[0]):
                continue
            ov = min(a[3], b[3]) - max(a[2], b[2])
            if ov < 0.5 * min(a[3] - a[2], b[3] - b[2]):
                continue
            gap = b[0] - a[1]
            if gap > 0.35 * wmed:
                continue
            if best is None or b[0] < P[best][0]:
                best = j
        if best is not None:
            right[i] = best
    cont = {i: abs(P[i][2] - P[j][2]) < bed_tol * hmed for i, j in right.items()}
    share = float(np.mean(list(cont.values()))) if cont else None
    runs = []
    starts = set(right) - set(right.values())
    for s in starts | {i for i in right if not any(right.get(k) == i and cont.get(k) for k in right)}:
        n, i = 1, s
        seen = {s}
        while i in right and cont.get(i) and right[i] not in seen:
            i = right[i]
            seen.add(i)
            n += 1
        runs.append(n)
    width = max(b[1] for b in P) - min(b[0] for b in P)
    height = max(b[3] for b in P) - min(b[2] for b in P)
    heads = [((P[i][1] + P[j][0]) / 2, max(P[i][2], P[j][2]), min(P[i][3], P[j][3])) for i, j in right.items()]
    four = 0
    for a in heads:
        for b in heads:
            if a is b or b[2] > a[1] + 1e-9:
                continue
            if abs(a[0] - b[0]) < 1.5 * tol and abs(a[1] - b[2]) < tol + 0.3 * hmed:
                four += 1
    return {"pairs": len(right), "bed_continuity": None if share is None else round(share, 3),
            "runs_ge4": int(sum(1 for r in runs if r >= 4)),
            "runs_ge4_per_m": round(sum(1 for r in runs if r >= 4) / max(width, 1e-6), 3),
            "longest_run": int(max(runs) if runs else 0),
            "four_way": four, "four_way_per_m2": round(four / max(width * height, 1e-6), 3)}


# ------------------------------------------------------------------------------------------------ gates
def _within(ours, ref, tol):
    if ours is None or ref is None:
        return None
    return abs(ours - ref) <= tol * abs(ref)


def gates(ref_img=None, our_img=None, ref_shapes=None, our_shapes=None, zone="body", use_scale=False, which=None):
    """Study 6.2 gates from the measurements above. Sizes (SG3) compare in metres only when use_scale is True (the
    trace's px/m is trusted); otherwise the scale-free ratios gate (aspect, upright share, area CV, cap/body)."""
    G = {}
    want = set(which or ["SG3", "SG4", "SG7", "SG8", "SG9", "SG10", "SG11", "SG12"])
    if ref_shapes and our_shapes and ref_shapes["zones"].get(zone) and our_shapes["zones"].get(zone):
        r, o = ref_shapes["zones"][zone], our_shapes["zones"][zone]
        floor = r.get("tolerance_floor") or 0.0
        tm = max(0.10, floor)
        tp = max(0.20, floor * 1.5)
        if "SG3" in want:
            if use_scale:
                ok = all(_within(o[k]["median"], r[k]["median"], tm) and _within(o[k]["p10"], r[k]["p10"], tp)
                         and _within(o[k]["p90"], r[k]["p90"], tp) for k in ("width_m", "height_m"))
                G["SG3_size"] = {"pass": bool(ok), "ours_w": o["width_m"], "ref_w": r["width_m"], "ours_h": o["height_m"],
                                 "ref_h": r["height_m"], "tol_median": tm, "tol_p": tp}
            ac_ok = _within(o["area_cv"], r["area_cv"], 0.20)
            G["SG3_area_cv"] = {"pass": bool(ac_ok), "ours": o["area_cv"], "ref": r["area_cv"], "tol": 0.20}
            if ref_shapes.get("cap_h_over_body_h") and our_shapes.get("cap_h_over_body_h"):
                ok = _within(our_shapes["cap_h_over_body_h"], ref_shapes["cap_h_over_body_h"], tp)
                G["SG3_cap_over_body_h"] = {"pass": bool(ok), "ours": our_shapes["cap_h_over_body_h"],
                                            "ref": ref_shapes["cap_h_over_body_h"], "tol": tp}
        if "SG4" in want:
            ok = abs(o["upright_share"] - r["upright_share"]) <= 0.10
            ok2 = _within(o["aspect_hw"]["median"], r["aspect_hw"]["median"], tm)
            G["SG4_upright_share"] = {"pass": bool(ok), "ours": o["upright_share"], "ref": r["upright_share"],
                                      "tol_abs": 0.10}
            G["SG4_aspect_median"] = {"pass": bool(ok2), "ours": o["aspect_hw"], "ref": r["aspect_hw"], "tol": tm}
        if "SG7" in want:
            t = o["mean_area_per_third_top_first"]
            rt = r["mean_area_per_third_top_first"]
            ref_falls = rt[0] is not None and rt[-1] is not None and rt[-1] >= rt[0]
            ours_falls = t[0] is not None and t[-1] is not None and t[-1] >= t[0]
            G["SG7_grading"] = {"pass": bool(ours_falls or not ref_falls), "ours_top_first": t, "ref_top_first": rt,
                                "note": "mean area should grow toward the foot where the reference's does"}
        if "SG9" in want and o.get("crown_cv") is not None:
            G["SG9_variety"] = {"pass": bool(o["crown_cv"] >= 0.3 and (o.get("corner_r_cv") or 0) >= 0.3),
                                "crown_cv": o["crown_cv"], "corner_r_cv": o.get("corner_r_cv"), "target": ">= 0.3"}
    if ref_img and our_img:
        rc, oc = ref_img["method_C"], our_img["method_C"]
        ra, oa = ref_img["method_A"], our_img["method_A"]
        if "SG8" in want:
            G["SG8_dark_joint_fraction"] = {"pass": bool(_within(oc["dark_joint_fraction"], rc["dark_joint_fraction"], 0.30)),
                                            "ours": oc["dark_joint_fraction"], "ref": rc["dark_joint_fraction"], "tol": 0.30}
        if "SG10" in want:
            G["SG10_p90_over_p50"] = {"pass": bool(_within(oc["p90_over_p50"], rc["p90_over_p50"], 0.15)),
                                      "ours": oc["p90_over_p50"], "ref": rc["p90_over_p50"], "tol": 0.15}
            G["SG10_local_std"] = {"pass": bool(_within(oa["local_std_16px"], ra["local_std_16px"], 0.25)),
                                   "ours": oa["local_std_16px"], "ref": ra["local_std_16px"], "tol": 0.25,
                                   "note": "16 px blocks: only comparable at a matched stone size in px"}
        if "SG11" in want:
            dh = abs(((oc["stone_hue_deg"] - rc["stone_hue_deg"] + 180) % 360) - 180)
            G["SG11_colour"] = {"pass": bool(dh <= 4 and abs(oc["stone_sat"] - rc["stone_sat"]) <= 0.05
                                             and abs(oa["R_over_B"] - ra["R_over_B"]) <= 0.10),
                                "hue": [oc["stone_hue_deg"], rc["stone_hue_deg"], "+-4"],
                                "sat": [oc["stone_sat"], rc["stone_sat"], "+-0.05"],
                                "R_over_B": [oa["R_over_B"], ra["R_over_B"], "+-0.10"]}
        if "SG12" in want:
            G["SG12_moss_share"] = {"pass": bool(_within(our_img["moss_share"], ref_img["moss_share"], 0.30)
                                                  if ref_img["moss_share"] > 0.005 else our_img["moss_share"] < 0.02),
                                    "ours": our_img["moss_share"], "ref": ref_img["moss_share"], "tol": 0.30}
    return G


# ------------------------------------------------------------------------------------------------ CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    a = sp.add_parser("image")
    a.add_argument("png")
    a.add_argument("--box", nargs=4, type=float)
    a.add_argument("--out")
    b = sp.add_parser("shapes")
    b.add_argument("json")
    b.add_argument("--out")
    c = sp.add_parser("gates")
    c.add_argument("--spec", required=True)
    c.add_argument("--out")
    ns = ap.parse_args(argv)
    if ns.cmd == "image":
        res = measure_image(ns.png, ns.box)
    elif ns.cmd == "shapes":
        d = json.loads(Path(ns.json).read_text(encoding="utf-8"))
        res = trace_shapes(d) if d.get("schema", "").startswith("stone_trace") else layout_shapes(d)
    else:
        spec = json.loads(Path(ns.spec).read_text(encoding="utf-8"))
        R, O = spec.get("reference", {}), spec.get("ours", {})
        ri = measure_image(R["image"], R.get("box")) if R.get("image") else None
        oi = measure_image(O["image"], O.get("box")) if O.get("image") else None
        rs = trace_shapes(R["trace"]) if R.get("trace") else None
        os_ = layout_shapes(O["layout"]) if O.get("layout") else None
        res = {"reference_image": ri, "ours_image": oi, "reference_shapes": rs, "ours_shapes": os_, "gates": {}}
        for z in spec.get("zones", ["body"]):
            res["gates"][z] = gates(ri, oi, rs, os_, zone=z, use_scale=spec.get("use_scale", False),
                                    which=spec.get("gates"))
    txt = json.dumps(res, indent=1)
    if getattr(ns, "out", None):
        Path(ns.out).write_text(txt, encoding="utf-8")
    print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
