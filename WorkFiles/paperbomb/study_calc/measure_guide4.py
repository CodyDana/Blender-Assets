# -*- coding: utf-8 -*-
"""Fourth pass: clean glyph boxes with a neutral-black mask (dark antialiased red
pixels were leaking into the black mask in passes 1-3), plus ink coverage and the
seal boxes measured as frame + panel.

blender -b --factory-startup --python measure_guide4.py -- <out.json>
"""
from __future__ import annotations

import json
import os
import sys

import bpy
import numpy as np

REF = r"C:/Users/Cody/Desktop/Blender_Projects/References/PaperBomb"
IMAGES = [("v1", os.path.join(REF, "paperbomb_guide.png")),
          ("v2", os.path.join(REF, "paperbomb_guide_v2_real_glyphs.png"))]


def load(path):
    img = bpy.data.images.load(path)
    img.colorspace_settings.name = "Non-Color"
    w, h = img.size
    buf = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(buf)
    a = buf.reshape(h, w, 4)[::-1].astype(np.float64)
    bpy.data.images.remove(img)
    return a, w, h


def analyse(path):
    a, W, H = load(path)
    rgb = a[:, :, :3]
    R, G, B = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    luma = 0.2126 * R + 0.7152 * G + 0.0722 * B
    sat = rgb.max(axis=2) - rgb.min(axis=2)
    card = (sat > 0.06) | (luma < 0.70)
    cx = np.nonzero(card.sum(axis=0) > 0.05 * H)[0]
    ry = np.nonzero(card.sum(axis=1) > 0.05 * W)[0]
    cx0, cx1, cy0, cy1 = int(cx.min()), int(cx.max()), int(ry.min()), int(ry.max())
    CW, CH = cx1 - cx0 + 1, cy1 - cy0 + 1
    RED = ((R - G > 0.25) & (R > 0.22))[cy0:cy1 + 1, cx0:cx1 + 1]
    # neutral black only: dark AND low saturation
    BK = ((luma < 0.35) & (sat < 0.18))[cy0:cy1 + 1, cx0:cx1 + 1]
    AR = card.shape

    def gbox(mask, fx0, fx1, fy0, fy1):
        x0, x1 = int(fx0 * CW), int(fx1 * CW)
        y0, y1 = int(fy0 * CH), int(fy1 * CH)
        sub = mask[y0:y1, x0:x1]
        ys_, xs_ = np.nonzero(sub)
        if len(xs_) < 20:
            return None
        w = xs_.max() + 1 - xs_.min()
        h = ys_.max() + 1 - ys_.min()
        return {"x0": round((x0 + xs_.min()) / CW, 4), "x1": round((x0 + xs_.max() + 1) / CW, 4),
                "y0": round((y0 + ys_.min()) / CH, 4), "y1": round((y0 + ys_.max() + 1) / CH, 4),
                "cx": round((x0 + (xs_.min() + xs_.max() + 1) / 2) / CW, 4),
                "cy": round((y0 + (ys_.min() + ys_.max() + 1) / 2) / CH, 4),
                "w_over_W": round(w / CW, 4), "h_over_H": round(h / CH, 4),
                "h_over_W": round(h / CW, 4),
                "ink_density": round(float(sub.sum()) / (w * h), 3),
                "clipped": [bool(xs_.min() <= 1), bool(xs_.max() >= sub.shape[1] - 2),
                            bool(ys_.min() <= 1), bool(ys_.max() >= sub.shape[0] - 2)]}

    G_ = {
        "centre_big": gbox(BK, 0.06, 0.94, 0.30, 0.71),
        "flame_emblem": gbox(BK, 0.30, 0.70, 0.05, 0.34),
        "ul_c1": gbox(BK, 0.02, 0.35, 0.035, 0.135),
        "ul_c2": gbox(BK, 0.02, 0.35, 0.135, 0.235),
        "ul_c3": gbox(BK, 0.02, 0.35, 0.235, 0.345),
        "ur_c1": gbox(BK, 0.64, 0.96, 0.035, 0.135),
        "ur_c2": gbox(BK, 0.64, 0.96, 0.135, 0.235),
        "ur_c3": gbox(BK, 0.64, 0.96, 0.235, 0.345),
        "lr_c1": gbox(BK, 0.64, 0.96, 0.55, 0.665),
        "lr_c2": gbox(BK, 0.64, 0.96, 0.665, 0.825),
        "lc_c1": gbox(BK, 0.33, 0.70, 0.69, 0.815),
        "lc_c2": gbox(BK, 0.33, 0.70, 0.815, 0.935),
        "seal_big_outer": gbox(RED, 0.03, 0.45, 0.72, 0.95),
        "seal_small_outer": gbox(RED, 0.74, 0.93, 0.74, 0.94),
        "bottom_diamond": gbox(RED, 0.44, 0.56, 0.955, 1.0),
        "mid_diamond_left": gbox(RED, 0.03, 0.09, 0.33, 0.42),
        "mid_diamond_right": gbox(RED, 0.91, 0.97, 0.33, 0.42),
    }
    # seal box interiors: red panel inside the big box, empty inside the small one
    sb = G_["seal_big_outer"]
    if sb:
        x0, x1 = int(sb["x0"] * CW), int(sb["x1"] * CW)
        y0, y1 = int(sb["y0"] * CH), int(sb["y1"] * CH)
        row = RED[(y0 + y1) // 2, x0:x1]
        col = RED[y0:y1, (x0 + x1) // 2]

        def runs(v, off, denom):
            o, r = [], None
            for i, q in enumerate(v):
                if q:
                    r = [i, i] if r is None else [r[0], i]
                else:
                    if r is not None:
                        o.append(r)
                    r = None
            if r is not None:
                o.append(r)
            return [[round((off + q[0]) / denom, 4), round((off + q[1] + 1) / denom, 4),
                     round((q[1] + 1 - q[0]) / denom, 4)] for q in o]
        G_["seal_big_h_runs"] = runs(row, x0, CW)
        G_["seal_big_v_runs"] = runs(col, y0, CH)
    ss = G_["seal_small_outer"]
    if ss:
        x0, x1 = int(ss["x0"] * CW), int(ss["x1"] * CW)
        y0, y1 = int(ss["y0"] * CH), int(ss["y1"] * CH)
        row = RED[(y0 + y1) // 2, x0:x1]
        col = RED[y0:y1, (x0 + x1) // 2]

        def runs2(v, off, denom):
            o, r = [], None
            for i, q in enumerate(v):
                if q:
                    r = [i, i] if r is None else [r[0], i]
                else:
                    if r is not None:
                        o.append(r)
                    r = None
            if r is not None:
                o.append(r)
            return [[round((off + q[0]) / denom, 4), round((off + q[1] + 1) / denom, 4),
                     round((q[1] + 1 - q[0]) / denom, 4)] for q in o]
        G_["seal_small_h_runs"] = runs2(row, x0, CW)
        G_["seal_small_v_runs"] = runs2(col, y0, CH)

    cov = {
        "red_frac_of_card": round(float(RED.sum()) / (CW * CH), 4),
        "black_frac_of_card": round(float(BK.sum()) / (CW * CH), 4),
        "ink_frac_of_card": round(float((RED | BK).sum()) / (CW * CH), 4),
    }
    return {"file": os.path.basename(path), "card_px": [CW, CH],
            "aspect_w_over_h": round(CW / CH, 4), "glyphs": G_, "coverage": cov}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    o = argv[0] if argv else os.path.join(os.path.dirname(__file__), "guide_measure4.json")
    res = {t: analyse(p) for t, p in IMAGES}
    with open(o, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    for t in res:
        v = res[t]
        print("==", t, v["card_px"], v["aspect_w_over_h"], v["coverage"])
        for n, b in v["glyphs"].items():
            if isinstance(b, dict):
                print("  %-18s x %.3f-%.3f y %.3f-%.3f c(%.3f,%.3f) w/W %.3f h/W %.3f dens %.2f clip %s"
                      % (n, b["x0"], b["x1"], b["y0"], b["y1"], b["cx"], b["cy"],
                         b["w_over_W"], b["h_over_W"], b["ink_density"], b["clipped"]))
            else:
                print("  %-18s %s" % (n, b))
    print("WROTE", o)


main()
