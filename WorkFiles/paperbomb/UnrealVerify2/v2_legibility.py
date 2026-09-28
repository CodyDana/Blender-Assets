#!/usr/bin/env python
"""Is the tag still legible when Unreal switches to LOD1 - and does the darker ink help?

THE GEOMETRY OF THE QUESTION
----------------------------
Unreal's LOD screen size is the projected DIAMETER of the mesh's bounding sphere as a
fraction of the screen (ComputeBoundsScreenSize returns 2 * ScreenMultiple * R / Dist,
and a value of 1.0 means the sphere spans the whole screen).  So at the LOD1 threshold
the sphere covers

    screen_size * screen_height  pixels

and the card, being a known number of millimetres across, follows from that.  The engine
reports the bounding sphere itself (passB/passC: 8.240522 cm), so no assumption is made
about the camera beyond the screen height.

WHAT IS MEASURED
----------------
Both base-colour maps - the shipped reference-matched one and the floored one from
WorkFiles/paperbomb/ink_floor_compare/floored - are cropped to the card, reduced in
LINEAR light to exactly the on-screen size, and then measured in three places: the hero
glyph, the narrowest side column, and the border rule.  Reducing in linear light is what
Unreal's mip generator does for an sRGB texture, so the comparison is the one the GPU
will actually make.

Nothing here reads or writes any reference guide.
"""
import json
import math
from pathlib import Path

import bpy
import numpy as np

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "paperbomb" / "UnrealVerify2"
OUT = HERE / "legibility.json"

MAPS = {
    "reference_matched_shipped": PROJ / "Exports" / "PaperBomb" / "Textures" / "T_PaperBomb_BC.png",
    "floored": PROJ / "WorkFiles" / "paperbomb" / "ink_floor_compare" / "floored" / "T_PaperBomb_BC.png",
}

PPMM = 12.923
PAD_PX = 16
CARD_W_MM, CARD_H_MM = 70.0, 156.0

# from passB / passC, read out of the engine
ENGINE_SPHERE_RADIUS_CM = 8.240522
BUILD_ASSUMED_RADIUS_CM = 8.551849          # the box-corner radius the sidecar was derived from
LOD_SCREEN_SIZES = [1.0, 0.171, 0.0599]
SCREEN_HEIGHTS = [1080, 1440, 2160]


def load_linear(path):
    """Stored sRGB PNG -> linear float RGB, with Blender kept out of the colour decision."""
    img = bpy.data.images.load(str(path))
    img.colorspace_settings.name = "Non-Color"
    w, h = img.size
    buf = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(buf)
    a = buf.reshape(h, w, 4)[:, :, :3].astype(np.float64)
    a = np.flipud(a)                                    # row 0 = top
    bpy.data.images.remove(img)
    s = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    return a, s                                         # stored, linear


def luma(lin):
    return 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]


def crop_card(stored, linear):
    """Front island: the card's own 70 x 156 mm, starting PAD_PX in."""
    w = int(round(CARD_W_MM * PPMM))
    h = int(round(CARD_H_MM * PPMM))
    x0, y0 = PAD_PX, PAD_PX
    return stored[y0:y0 + h, x0:x0 + w], linear[y0:y0 + h, x0:x0 + w], (x0, y0, w, h)


def segment(stored, linear):
    """Red first, then black - the spec's own binarisation convention."""
    L = luma(linear)
    r, g, b = stored[..., 0], stored[..., 1], stored[..., 2]
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    sat = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
    red = (sat > 0.35) & (r > g + 0.10) & (r > b + 0.10)
    paper = float(np.percentile(L[~red], 75))
    floor = float(np.percentile(L[~red], 0.5))
    thr = 0.5 * (paper + floor)
    black = (L < thr) & (~red)
    return {"red": red, "black": black, "L": L,
            "paper_linear_p75": paper, "ink_linear_p005": floor, "threshold": thr}


def area_resize(a, nw, nh):
    """Exact area average to an arbitrary size, done channel-wise in linear light."""
    h, w = a.shape[:2]
    ys = (np.arange(nh + 1) * h / nh)
    xs = (np.arange(nw + 1) * w / nw)
    # accumulate with a summed-area table for exactness at fractional edges
    if a.ndim == 2:
        a = a[:, :, None]
        squeeze = True
    else:
        squeeze = False
    sat = np.zeros((h + 1, w + 1, a.shape[2]), np.float64)
    sat[1:, 1:] = np.cumsum(np.cumsum(a, axis=0), axis=1)

    def interp(yy, xx):
        y0 = np.clip(np.floor(yy).astype(int), 0, h)
        x0 = np.clip(np.floor(xx).astype(int), 0, w)
        fy = np.clip(yy - y0, 0, 1)[:, None, None]
        fx = np.clip(xx - x0, 0, 1)[None, :, None]
        s00 = sat[np.ix_(y0, x0)]
        s01 = sat[np.ix_(y0, np.clip(x0 + 1, 0, w))]
        s10 = sat[np.ix_(np.clip(y0 + 1, 0, h), x0)]
        s11 = sat[np.ix_(np.clip(y0 + 1, 0, h), np.clip(x0 + 1, 0, w))]
        return (s00 * (1 - fy) * (1 - fx) + s01 * (1 - fy) * fx +
                s10 * fy * (1 - fx) + s11 * fy * fx)

    S = interp(ys, xs)
    tot = S[1:, 1:] - S[:-1, 1:] - S[1:, :-1] + S[:-1, :-1]
    area = ((ys[1:] - ys[:-1])[:, None] * (xs[1:] - xs[:-1])[None, :])[:, :, None]
    out = tot / np.maximum(area, 1e-12)
    return out[:, :, 0] if squeeze else out


def region_stats(lin_small, mask_small, label):
    """Michelson + RMS contrast of a region after the reduction to screen size."""
    L = luma(lin_small)
    if mask_small.sum() < 4:
        return {"label": label, "error": "region empty at this size"}
    inside = L[mask_small]
    around = L[~mask_small]
    lo, hi = float(inside.min()), float(np.percentile(around, 75)) if around.size else float(L.max())
    mich = (hi - lo) / max(hi + lo, 1e-9)
    return {
        "label": label,
        "pixels": int(mask_small.sum()),
        "darkest_linear": round(lo, 6),
        "local_paper_linear_p75": round(hi, 6),
        "michelson_contrast": round(float(mich), 5),
        "ratio_paper_over_darkest": round(hi / max(lo, 1e-9), 2),
        "mean_linear_in_region": round(float(inside.mean()), 6),
        "rms_contrast_in_region": round(float(inside.std() / max(inside.mean(), 1e-9)), 5),
    }


def main():
    rep = {"px_per_mm_atlas": PPMM, "card_mm": [CARD_W_MM, CARD_H_MM],
           "engine_sphere_radius_cm": ENGINE_SPHERE_RADIUS_CM,
           "build_assumed_radius_cm": BUILD_ASSUMED_RADIUS_CM,
           "lod_screen_sizes": LOD_SCREEN_SIZES}

    # ---- the on-screen size at each LOD threshold ------------------------------------
    geom = {}
    for H in SCREEN_HEIGHTS:
        per = {}
        for tag, R in (("engine_radius", ENGINE_SPHERE_RADIUS_CM),
                       ("build_assumed_radius", BUILD_ASSUMED_RADIUS_CM)):
            rows = {}
            for i, ss in enumerate(LOD_SCREEN_SIZES):
                sphere_px = ss * H
                px_per_mm = sphere_px / (2.0 * R * 10.0)
                rows[f"LOD{i}_threshold"] = {
                    "sphere_diameter_px": round(sphere_px, 2),
                    "screen_px_per_mm": round(px_per_mm, 5),
                    "card_px": [round(CARD_W_MM * px_per_mm, 2), round(CARD_H_MM * px_per_mm, 2)],
                }
            per[tag] = rows
        geom[f"{H}p"] = per
    rep["on_screen_geometry"] = geom

    px_per_mm_lod1 = (LOD_SCREEN_SIZES[1] * 1080.0) / (2.0 * ENGINE_SPHERE_RADIUS_CM * 10.0)
    rep["lod1_switch_px_per_mm_at_1080p"] = round(px_per_mm_lod1, 5)

    # ---- measure the elements on the shipped map, at full atlas resolution ------------
    results = {}
    for name, path in MAPS.items():
        if not path.is_file():
            results[name] = {"error": f"missing {path}"}
            continue
        stored_full, linear_full = load_linear(path)
        stored, linear, box = crop_card(stored_full, linear_full)
        seg = segment(stored, linear)
        h, w = seg["black"].shape
        ys, xs = np.mgrid[0:h, 0:w]
        xmm = (xs + 0.5) / PPMM
        ymm = (ys + 0.5) / PPMM

        # hero glyph: black ink strictly inside the enso ring
        cx, cy, ax, ay = 35.128, 76.835, 26.81, 29.18
        rr = np.sqrt(((xmm - cx) / ax) ** 2 + ((ymm - cy) / ay) ** 2)
        hero = seg["black"] & (rr < 0.80)
        # narrowest side column: the upper-left block 火遁術
        colL = seg["black"] & (xmm > 5.0) & (xmm < 21.0) & (ymm > 8.0) & (ymm < 74.0)
        # the border rule, left side
        rule = seg["black"] & (xmm > 2.6) & (xmm < 5.6) & (ymm > 20.0) & (ymm < 136.0)

        def bbox(m):
            if m.sum() == 0:
                return None
            yy, xx = np.nonzero(m)
            return {"x_mm": [round(float(xx.min() + 0.5) / PPMM, 3), round(float(xx.max() + 0.5) / PPMM, 3)],
                    "y_mm": [round(float(yy.min() + 0.5) / PPMM, 3), round(float(yy.max() + 0.5) / PPMM, 3)],
                    "w_mm": round(float(xx.max() - xx.min() + 1) / PPMM, 3),
                    "h_mm": round(float(yy.max() - yy.min() + 1) / PPMM, 3),
                    "ink_mm2": round(float(m.sum()) / (PPMM * PPMM), 3)}

        rec = {
            "source": str(path),
            "card_crop_px": box,
            "paper_linear_p75": round(seg["paper_linear_p75"], 6),
            "ink_linear_p005": round(seg["ink_linear_p005"], 6),
            "paper_over_ink_ratio_full_res": round(
                seg["paper_linear_p75"] / max(seg["ink_linear_p005"], 1e-9), 2),
            "black_fraction": round(float(seg["black"].mean()), 5),
            "red_fraction": round(float(seg["red"].mean()), 5),
            "hero_bbox": bbox(hero),
            "column_upper_left_bbox": bbox(colL),
            "rule_left_bbox": bbox(rule),
        }

        # ---- reduce to the LOD1 on-screen size and re-measure -------------------------
        nw = max(1, int(round(CARD_W_MM * px_per_mm_lod1)))
        nh = max(1, int(round(CARD_H_MM * px_per_mm_lod1)))
        small = area_resize(linear, nw, nh)
        rec["lod1_card_px"] = [nw, nh]

        def shrink_mask(m):
            f = area_resize(m.astype(np.float64), nw, nh)
            return f > 0.35

        for label, m in (("hero_glyph", hero), ("column_upper_left", colL), ("rule_left", rule)):
            rec[f"lod1_{label}"] = region_stats(small, shrink_mask(m), label)
            bb = bbox(m)
            if bb:
                rec[f"lod1_{label}"]["on_screen_px"] = [round(bb["w_mm"] * px_per_mm_lod1, 2),
                                                        round(bb["h_mm"] * px_per_mm_lod1, 2)]

        # whole-card contrast at LOD1 size
        Ls = luma(small)
        rec["lod1_whole_card"] = {
            "paper_linear_p75": round(float(np.percentile(Ls, 75)), 6),
            "darkest_linear": round(float(Ls.min()), 6),
            "p01_linear": round(float(np.percentile(Ls, 1)), 6),
            "contrast_p75_over_min": round(float(np.percentile(Ls, 75)) / max(float(Ls.min()), 1e-9), 2),
            "contrast_p75_over_p01": round(float(np.percentile(Ls, 75)) / max(float(np.percentile(Ls, 1)), 1e-9), 2),
            "rms_contrast": round(float(Ls.std() / max(Ls.mean(), 1e-9)), 5),
        }
        # and at LOD0 / LOD2 sizes, for the trend
        for i in (0, 2):
            pmm = (LOD_SCREEN_SIZES[i] * 1080.0) / (2.0 * ENGINE_SPHERE_RADIUS_CM * 10.0)
            w2 = max(1, int(round(CARD_W_MM * pmm)))
            h2 = max(1, int(round(CARD_H_MM * pmm)))
            s2 = luma(area_resize(linear, w2, h2))
            rec[f"lod{i}_whole_card"] = {
                "card_px": [w2, h2],
                "paper_linear_p75": round(float(np.percentile(s2, 75)), 6),
                "darkest_linear": round(float(s2.min()), 6),
                "contrast_p75_over_min": round(float(np.percentile(s2, 75)) / max(float(s2.min()), 1e-9), 2),
                "rms_contrast": round(float(s2.std() / max(s2.mean(), 1e-9)), 5),
            }
        results[name] = rec
    rep["maps"] = results

    a = results.get("reference_matched_shipped", {})
    b = results.get("floored", {})
    if "lod1_whole_card" in a and "lod1_whole_card" in b:
        rep["verdict_darker_ink_at_lod1"] = {
            "reference_contrast_at_lod1": a["lod1_whole_card"]["contrast_p75_over_min"],
            "floored_contrast_at_lod1": b["lod1_whole_card"]["contrast_p75_over_min"],
            "reference_rms": a["lod1_whole_card"]["rms_contrast"],
            "floored_rms": b["lod1_whole_card"]["rms_contrast"],
            "hero_michelson_reference": a.get("lod1_hero_glyph", {}).get("michelson_contrast"),
            "hero_michelson_floored": b.get("lod1_hero_glyph", {}).get("michelson_contrast"),
            "column_michelson_reference": a.get("lod1_column_upper_left", {}).get("michelson_contrast"),
            "column_michelson_floored": b.get("lod1_column_upper_left", {}).get("michelson_contrast"),
        }

    OUT.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print("[legibility] ->", OUT)
    print(json.dumps({k: rep[k] for k in ("lod1_switch_px_per_mm_at_1080p",
                                          "verdict_darker_ink_at_lod1")}, indent=1))
    for n, r in results.items():
        if "error" in r:
            print(" ", n, r["error"]); continue
        print(f"  {n}: card@LOD1 {r['lod1_card_px']}  hero {r['lod1_hero_glyph'].get('on_screen_px')} "
              f"mich {r['lod1_hero_glyph'].get('michelson_contrast')}  "
              f"col {r['lod1_column_upper_left'].get('on_screen_px')} "
              f"mich {r['lod1_column_upper_left'].get('michelson_contrast')}")
        print("     bbox hero", r["hero_bbox"], "col", r["column_upper_left_bbox"])


main()
