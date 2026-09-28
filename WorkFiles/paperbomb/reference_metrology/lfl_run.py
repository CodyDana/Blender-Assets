# -*- coding: utf-8 -*-
"""Run the like-for-like instrument over V1, V2 and our shipped sheet.

METROLOGY ONLY - see lfl.py.  Writes lfl_report.json beside this file.
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lfl  # noqa: E402

GRID = lfl.GRID
CARD_W_MM, CARD_H_MM = lfl.CARD_W_MM, lfl.CARD_H_MM


def mm(px):
    return px / GRID


def px(mm_):
    return int(round(mm_ * GRID))


# ---------------------------------------------------------------------------
# distance transform (chamfer 3-4, then scaled) - no scipy in this environment
# ---------------------------------------------------------------------------

def chamfer(mask):
    """Approximate Euclidean distance in PIXELS from every cell to the nearest True."""
    big = 1e9
    d = np.where(mask, 0.0, big)
    a, b = 1.0, 1.4142135
    H, W = d.shape
    for y in range(H):
        row = d[y]
        if y:
            up = d[y - 1]
            row = np.minimum(row, up + a)
            row = np.minimum(row, np.concatenate(([big], up[:-1])) + b)
            row = np.minimum(row, np.concatenate((up[1:], [big])) + b)
        for x in range(1, W):
            if row[x] > row[x - 1] + a:
                row[x] = row[x - 1] + a
        d[y] = row
    for y in range(H - 1, -1, -1):
        row = d[y]
        if y < H - 1:
            dn = d[y + 1]
            row = np.minimum(row, dn + a)
            row = np.minimum(row, np.concatenate(([big], dn[:-1])) + b)
            row = np.minimum(row, np.concatenate((dn[1:], [big])) + b)
        for x in range(W - 2, -1, -1):
            if row[x] > row[x + 1] + a:
                row[x] = row[x + 1] + a
        d[y] = row
    return d


# ---------------------------------------------------------------------------
# 1.  the border rules
# ---------------------------------------------------------------------------

def fit_frame(red):
    """The rule rectangle, fitted on each side's own red like art_metrics does."""
    H, W = red.shape
    ys, xs = np.nonzero(red)
    # coarse: the outermost long red runs
    colocc = red.sum(axis=0) / float(H)
    rowocc = red.sum(axis=1) / float(W)
    cx = np.flatnonzero(colocc > 0.35)
    ry = np.flatnonzero(rowocc > 0.35)
    if cx.size < 2 or ry.size < 2:
        return None
    return (mm(cx[0]), mm(ry[0]), mm(cx[-1]), mm(ry[-1]))


def border(rgb, cl, frame):
    x0, y0, x1, y1 = frame
    red = cl["red"]
    chroma = rgb[..., 0] - rgb[..., 2]
    paper_sel = lfl.box(cl["ink"].astype(np.float64), 6) <= 0.0
    pap = chroma[paper_sel] if paper_sel.any() else chroma.ravel()
    p_med = float(np.median(pap))
    p_hi = float(np.percentile(pap, 99.9))
    out = {"paper_chroma_median": round(p_med, 4),
           "paper_chroma_p99.9": round(p_hi, 4), "sides": {}}
    half = px(1.6)
    for name, axis, at, lo, hi in (("left", "v", x0, y0 + 2.0, y1 - 2.0),
                                   ("right", "v", x1, y0 + 2.0, y1 - 2.0),
                                   ("top", "h", y0, x0 + 2.0, x1 - 2.0),
                                   ("bottom", "h", y1, x0 + 2.0, x1 - 2.0)):
        c = px(at)
        s0, s1 = px(lo), px(hi)
        if axis == "v":
            band_red = red[s0:s1, max(c - half, 0):c + half + 1]
            band_chr = chroma[s0:s1, max(c - half, 0):c + half + 1]
        else:
            band_red = red[max(c - half, 0):c + half + 1, s0:s1].T
            band_chr = chroma[max(c - half, 0):c + half + 1, s0:s1].T
        hits = band_red.any(axis=1)
        mx = band_chr.max(axis=1)
        n = len(hits)
        step = 1.0 / GRID
        gaps = [(b - a) * step for a, b in lfl.runs(~hits)]
        real = [g for g in gaps if g > 0.25]
        ink_runs = [(b - a) * step for a, b in lfl.runs(hits)]
        row = {
            "occupancy": round(float(hits.mean()), 4),
            "breaks": len(real),
            "longest_break_mm": round(max(real), 2) if real else 0.0,
            "longest_run_frac": round(max(ink_runs) / (n * step), 3) if ink_runs else 0.0,
        }
        for tag, thr in (("t02", p_med + 0.02), ("t05", p_med + 0.05),
                         ("t10", p_med + 0.10), ("p999", p_hi)):
            row["frac_zero_ink_" + tag] = round(float((mx < thr).mean()), 4)
            z = [(b - a) * step for a, b in lfl.runs(mx < thr)]
            row["longest_bare_mm_" + tag] = round(max(z), 2) if z else 0.0
        out["sides"][name] = row
    return out


# ---------------------------------------------------------------------------
# 2.  paper grain, by BAND POWER
# ---------------------------------------------------------------------------

def grain(rgb, cl):
    lum = cl["lum"]
    ink = lfl.box(cl["ink"].astype(np.float64), max(2, px(1.5))) > 1e-6
    sel = ~ink
    sel[:px(26.0), :] = False
    sel[-px(26.0):, :] = False
    sel[:, :px(16.0)] = False
    sel[:, -px(16.0):] = False
    if sel.sum() < 5000:
        return {}
    r025, r100, r300, r1000 = 1, max(2, px(1.0) // 2), max(3, px(3.0) // 2), max(4, px(10.0) // 2)
    L0 = lum
    L1 = lfl.box(lum, r025)
    L2 = lfl.box(lum, r100)
    L3 = lfl.box(lum, r300)
    L4 = lfl.box(lum, r1000)
    bands = {"sub_0.35mm": L0 - L1, "b0.35_1.0mm": L1 - L2,
             "b1.0_3.0mm": L2 - L3, "b3.0_10mm": L3 - L4}
    mean = float(np.mean(lum[sel]))
    # THE SCALE-FREE FIGURE: each band's rms as a fraction of the paper's own mean.
    # A FRACTION of a total is not comparable between two sheets whose totals are
    # dominated by different things - V1's 3-10 mm band carries its whole soft global
    # shading, which is a photograph's lighting and not the sheet's fibre.  So the bands
    # are reported ABSOLUTE first, and the fraction is taken over the SUB-3 mm texture
    # only, which is what "paper grain" means.
    out = {"paper_mean_luma": round(mean, 4)}
    detail = L0 - L2
    out["amplitude_p95_p05_over_mean"] = round(
        float(np.percentile(detail[sel], 95) - np.percentile(detail[sel], 5)) / max(mean, 1e-9), 5)
    fine_tot = 0.0
    for k, v in bands.items():
        vv = float(np.var(v[sel]))
        out["rms_" + k] = round(math.sqrt(max(vv, 0.0)) / max(mean, 1e-9), 5)
        if not k.startswith("b3.0"):
            fine_tot += vv
    for k, v in bands.items():
        if k.startswith("b3.0"):
            continue
        out["frac_sub3mm_" + k] = round(float(np.var(v[sel])) / max(fine_tot, 1e-12), 4)
    out["ratio_coarse_over_fine"] = round(
        float(np.var(bands["b3.0_10mm"][sel])) / max(fine_tot, 1e-12), 3)
    # ACF first zero on the sub-3 mm texture, masked to paper
    field = L0 - L3
    f = np.where(sel, field - float(np.mean(field[sel])), 0.0)
    w = sel.astype(np.float64)
    for axis, key in ((1, "acf_first_zero_x_mm"), (0, "acf_first_zero_y_mm")):
        n = min(int(round(4.0 * GRID)), f.shape[axis] - 2)
        ac = np.empty(n)
        for k in range(n):
            if axis == 1:
                num = float((f[:, :f.shape[1] - k] * f[:, k:]).sum())
                den = float((w[:, :f.shape[1] - k] * w[:, k:]).sum())
            else:
                num = float((f[:f.shape[0] - k] * f[k:]).sum())
                den = float((w[:f.shape[0] - k] * w[k:]).sum())
            ac[k] = num / max(den, 1.0)
        ac = ac / max(ac[0], 1e-12)
        z = np.flatnonzero(ac <= 0.0)
        out[key] = round(float(z[0]) / GRID if z.size else n / GRID, 4)
    out["acf_cell_mm"] = round(2.0 * min(out["acf_first_zero_x_mm"],
                                         out["acf_first_zero_y_mm"]), 4)
    out["paper_pixels"] = int(sel.sum())
    return out


# ---------------------------------------------------------------------------
# 3.  corners - what colour is the outboard ink?
# ---------------------------------------------------------------------------

def corners(cl, frame):
    x0, y0, x1, y1 = frame
    out = {}
    span = 11.0
    for name, cx, cy, sy in (("top_left", x0, y0, -1), ("top_right", x1, y0, -1),
                             ("bottom_left", x0, y1, +1), ("bottom_right", x1, y1, +1)):
        xa, xb = px(cx - span * 0.5), px(cx + span * 0.5)
        if sy < 0:
            ya, yb = px(cy - 8.0), px(cy - 0.45)
        else:
            ya, yb = px(cy + 0.45), px(cy + 8.0)
        xa, xb = max(xa, 0), min(xb, cl["red"].shape[1])
        ya, yb = max(ya, 0), min(yb, cl["red"].shape[0])
        r = cl["red"][ya:yb, xa:xb]
        b = cl["black"][ya:yb, xa:xb]
        k = 1.0 / (GRID * GRID)
        row = {"red_mm2": round(float(r.sum()) * k, 2),
               "black_mm2": round(float(b.sum()) * k, 2)}
        for key, m in (("red", r), ("black", b)):
            if m.any():
                ys, _ = np.nonzero(m)
                d = (mm(ys.min() + ya) if sy < 0 else mm(ys.max() + ya))
                row[key + "_reach_mm"] = round(abs(cy - d), 2)
            else:
                row[key + "_reach_mm"] = 0.0
        out[name] = row
    out["any_black"] = any(v["black_mm2"] > 0.15 for v in out.values() if isinstance(v, dict))
    return out


# ---------------------------------------------------------------------------
# 4.  the flame emblem
# ---------------------------------------------------------------------------

def flame(cl, centre=(34.83, 30.59), size=(26.0, 26.0)):
    black = cl["black"]
    cx, cy = centre
    w, h = size
    sub = black[px(cy - h * 0.5):px(cy + h * 0.5), px(cx - w * 0.5):px(cx + w * 0.5)]
    if not sub.any():
        return {}
    ys, xs = np.nonzero(sub)
    iy0, iy1, ix0, ix1 = int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max())
    m = sub[iy0:iy1 + 1, ix0:ix1 + 1]
    k = 1.0 / (GRID * GRID)
    lab, n = lfl.label_cc(m)
    areas = np.bincount(lab.ravel())[1:] * k if n else np.array([])
    order = np.argsort(-areas) if areas.size else []
    hp = iy1 - iy0
    fr = [0.05, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95]
    prof, segs = [], []
    for f in fr:
        yy = int(round(f * hp))
        idx = np.flatnonzero(m[yy])
        if idx.size == 0:
            prof.append(0.0); segs.append(0); continue
        prof.append(round(mm(idx.max() - idx.min() + 1), 2))
        segs.append(int(1 + int((np.diff(idx) > 1).sum())))
    lab2, n2 = lfl.label_cc(~m)
    bord = set(np.unique(np.concatenate([lab2[0], lab2[-1], lab2[:, 0], lab2[:, -1]])))
    holes = sorted((float((lab2 == i).sum()) * k for i in range(1, n2 + 1) if i not in bord),
                   reverse=True)
    elong = 0.0
    if n:
        big = int(np.argmax(np.bincount(lab.ravel())[1:])) + 1
        cys, cxs = np.nonzero(lab == big)
        pxs = cxs.astype(float) - cxs.mean()
        pys = cys.astype(float) - cys.mean()
        cv = np.array([[float((pxs * pxs).mean()), float((pxs * pys).mean())],
                       [float((pxs * pys).mean()), float((pys * pys).mean())]])
        ev = np.linalg.eigvalsh(cv)
        elong = math.sqrt(max(float(ev[1]), 1e-9) / max(float(ev[0]), 1e-9))
    strokes = sorted([float(a) for a in areas if a >= 8.0], reverse=True)
    return {
        "box_mm": [round(mm(ix1 - ix0 + 1), 2), round(mm(iy1 - iy0 + 1), 2)],
        "ink_mm2": round(float(m.sum()) * k, 1),
        "components": int(n),
        "strokes_ge_8mm2": len(strokes),
        "stroke_areas_mm2": [round(v, 1) for v in strokes[:6]],
        "specks": int(n) - len(strokes),
        "largest_elongation": round(elong, 2),
        "mass_ratio": round(strokes[0] / strokes[-1], 2) if len(strokes) >= 2 else 0.0,
        "width_by_height_mm": prof,
        "segments_by_height": segs,
        "base_width_mm": prof[-1], "top_width_mm": prof[0],
        "largest_counter_mm2": round(holes[0], 2) if holes else 0.0,
        "counters_mm2": [round(v, 2) for v in holes[:5]],
        "counters_over_0.3mm2": int(sum(1 for v in holes if v > 0.3)),
    }


# ---------------------------------------------------------------------------
# 5.  the four reds' laid-on value
# ---------------------------------------------------------------------------

def reds(cl, frame):
    x0, y0, x1, y1 = frame
    red = cl["red"]
    v = cl["v"]
    H, W = red.shape
    yy = np.arange(H)[:, None] / GRID
    xx = np.arange(W)[None, :] / GRID
    near = (np.minimum(np.abs(xx - x0), np.abs(xx - x1)) < 1.4) | \
           (np.minimum(np.abs(yy - y0), np.abs(yy - y1)) < 1.4)
    inside = (xx > x0 - 2.0) & (xx < x1 + 2.0) & (yy > y0 - 2.0) & (yy < y1 + 2.0)
    masks = {
        "border": red & near & inside,
        "ring": red & (yy > 44.0) & (yy < 112.0) & (xx > 5.0) & (xx < 66.0) & ~near,
        "big_seal": red & (yy > 116.0) & (yy < 145.0) & (xx > 5.0) & (xx < 25.0) & ~near,
        "small_seal": red & (yy > 122.0) & (yy < 143.0) & (xx > 53.0) & (xx < 65.0) & ~near,
    }
    out = {}
    for k, m in masks.items():
        if m.sum() < 30:
            out[k] = {"n": int(m.sum())}
            continue
        core = m & (lfl.box(m.astype(np.float64), 1) > 0.98)
        vals = v[m]
        out[k] = {"n": int(m.sum()),
                  "value_median": round(float(np.median(vals)), 4),
                  "value_p90": round(float(np.percentile(vals, 90)), 4),
                  "core_n": int(core.sum()),
                  "core_value_median": (round(float(np.median(v[core])), 4)
                                        if core.sum() > 10 else None),
                  "sat_median": round(float(np.median(cl["s"][m])), 4),
                  "hue_median": round(float(np.median(cl["h"][m])), 3)}
    vals = [out[k].get("core_value_median") or out[k].get("value_median")
            for k in masks if out[k].get("n", 0) > 30]
    if vals:
        out["core_value_spread"] = round(max(vals) - min(vals), 4)
    return out


# ---------------------------------------------------------------------------
# 6.  ink edge softness
# ---------------------------------------------------------------------------

def halo(cl):
    black = cl["black"]
    lum = cl["lum"]
    paper = float(cl["paper_lum"])
    d = chamfer(black)
    core = float(np.median(lum[lfl.box(black.astype(np.float64), 2) > 0.98])) \
        if (lfl.box(black.astype(np.float64), 2) > 0.98).any() else float(np.min(lum))
    prof = []
    for k in range(0, 13):
        sel = (d >= k) & (d < k + 1) & ~black
        prof.append(round(float(np.median(lum[sel])), 4) if sel.sum() > 50 else None)
    # 10-90 rise: from the edge outward, how far to recover 90 % of paper
    reach = None
    rise = None
    span = paper - core
    for k, val in enumerate(prof):
        if val is None:
            continue
        if rise is None and val >= core + 0.90 * span:
            rise = round(mm(k), 4)
        if reach is None and val >= paper - 0.03 * span:
            reach = round(mm(k), 4)
    return {"paper_luma": round(paper, 4), "core_luma": round(core, 4),
            "shell_luma_by_px": prof,
            "rise_to_90pct_mm": rise, "recover_97pct_mm": reach}


# ---------------------------------------------------------------------------
# 7.  hero glyph clearance, leaf isolation
# ---------------------------------------------------------------------------

def hero_clearance(cl):
    black = cl["black"]
    H, W = black.shape
    lab, n = lfl.label_cc(black)
    if not n:
        return {}
    cnt = np.bincount(lab.ravel())
    cnt[0] = 0
    big = int(np.argmax(cnt))
    hero = lab == big
    ys, xs = np.nonzero(hero)
    hero_box = [round(mm(xs.min()), 2), round(mm(ys.min()), 2),
                round(mm(xs.max()), 2), round(mm(ys.max()), 2)]
    # anything else whose centroid is in the lower-right column's slot
    others = np.zeros_like(black)
    picked = []
    for i in range(1, n + 1):
        if i == big or cnt[i] < 40:
            continue
        cys, cxs = np.nonzero(lab == i)
        cx, cy = mm(cxs.mean()), mm(cys.mean())
        if cx > 48.0 and 92.0 < cy < 132.0:
            others |= (lab == i)
            picked.append({"at": [round(cx, 2), round(cy, 2)],
                           "mm2": round(float(cnt[i]) / (GRID * GRID), 1),
                           "box_mm": [round(mm(cxs.min()), 2), round(mm(cys.min()), 2),
                                      round(mm(cxs.max()), 2), round(mm(cys.max()), 2)]})
    if not others.any():
        return {"hero_box_mm": hero_box, "note": "no lower-right column component"}
    d = chamfer(hero)
    gap = float(d[others].min()) / GRID
    return {"hero_box_mm": hero_box, "hero_mm2": round(float(cnt[big]) / (GRID * GRID), 1),
            "column_components": picked,
            "clearance_mm": round(gap, 2)}


def leaves(cl):
    red = cl["red"]
    lab, n = lfl.label_cc(red)
    found = []
    for i in range(1, n + 1):
        m = lab == i
        cys, cxs = np.nonzero(m)
        cx, cy = mm(cxs.mean()), mm(cys.mean())
        if 28.0 < cx < 43.0 and 126.0 < cy < 136.0:
            a = float(m.sum()) / (GRID * GRID)
            found.append({"at": [round(cx, 2), round(cy, 2)], "mm2": round(a, 2),
                          "w_mm": round(mm(cxs.max() - cxs.min() + 1), 2),
                          "h_mm": round(mm(cys.max() - cys.min() + 1), 2)})
    found.sort(key=lambda d: -d["mm2"])
    # do the leaves touch the black column?
    blk = cl["black"]
    sel = red & (lfl.box(blk.astype(np.float64), 1) > 1e-6)
    return {"red_components_in_leaf_band": found[:6],
            "red_touching_black_mm2_cardwide": round(float(sel.sum()) / (GRID * GRID), 1)}


# ---------------------------------------------------------------------------

def measure(which):
    rgb, _ = lfl.load_sheet(which)
    cl = lfl.classify(rgb)
    fr = fit_frame(cl["red"])
    out = {"sheet": which, "frame_mm": [round(v, 3) for v in fr] if fr else None,
           "paper_v": round(cl["paper_v"], 4), "paper_lum": round(cl["paper_lum"], 4),
           "red_area_fraction": round(float(cl["red"].mean()), 4),
           "black_area_fraction": round(float(cl["black"].mean()), 4)}
    if fr:
        out["border"] = border(rgb, cl, fr)
        out["corners"] = corners(cl, fr)
        out["reds"] = reds(cl, fr)
    out["grain"] = grain(rgb, cl)
    out["flame"] = flame(cl)
    out["halo"] = halo(cl)
    out["hero"] = hero_clearance(cl)
    out["leaves"] = leaves(cl)
    return out


def main():
    which = sys.argv[1:] or ["V1", "ours"]
    rep = {}
    for w in which:
        rep[w] = measure(w)
        print("== %s ==" % w)
        print(json.dumps(rep[w], indent=1, ensure_ascii=False))
    path = os.path.join(HERE, "lfl_report.json")
    old = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                old = json.load(fh)
        except Exception:
            old = {}
    old.update(rep)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(old, fh, indent=1, ensure_ascii=False)
    print("[lfl] wrote " + path)


if __name__ == "__main__":
    main()
