"""Snow Flower sheath: reference vs the render of the shipped asset, on the SAME pixel grid (measurement only - the
build never reads the reference).

    blender -b --factory-startup --python shv4_compare.py -- --renders <dir> --out <dir>

Writes:
    SnowFlower_Sheath_RefView_vs_Reference.png   [reference | ours on white | silhouette overlay]
                                                  (red = reference only, blue = ours only, grey = both)
    SnowFlower_Sheath_Detail_<fitting>_vs_Reference.png   reference crop (4x, nearest) | our 4x orthographic render
    sheath_compare_metrics.json    per-zone width differences, IoU, length, straightness, tone percentiles
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "shv4_lib"))   # look-match: frozen sfv4_* helpers
import sfv4_png as PNG  # noqa: E402
import shv4_spec as S  # noqa: E402

REF = S.ROOT / "References" / "SnowFlower" / "SnowFlower_sheath_reference.png"
ZONES = {"collar": (31, 40), "throat": (41, 167), "body_upper": (169, 283), "band": (284, 321),
         "body": (322, 1249), "chape": (1250, 1496)}


def load(path):
    im = bpy.data.images.load(str(path))
    w, h = im.size
    a = np.array(im.pixels[:], np.float32).reshape(h, w, im.channels)[::-1].copy()
    bpy.data.images.remove(im)
    if a.shape[2] == 3:
        a = np.concatenate([a, np.ones((h, w, 1), np.float32)], 2)
    return a


def to_display(rgb_linear):
    x = np.clip(rgb_linear, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def lum(rgb):
    return rgb @ np.array([0.2126, 0.7152, 0.0722])


def widths(mask):
    out = np.full((mask.shape[0], 2), -1, int)
    for r in range(mask.shape[0]):
        idx = np.nonzero(mask[r])[0]
        if len(idx):
            out[r] = [idx.min(), idx.max()]
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--renders", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    rd, out = Path(a.renders), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    ref = load(REF)                      # 8-bit PNGs load as their stored (display, sRGB-encoded) values
    ref_disp = ref[..., :3]
    ours = load(rd / "ref_front.png")
    ours_disp = ours[..., :3]
    alpha = ours[..., 3]
    # composite ours on white (display space)
    ours_on_white = ours_disp * alpha[..., None] + (1 - alpha[..., None])
    Lr = lum(ref_disp)
    sat = ref_disp.max(2) - ref_disp.min(2)
    m_ref = (Lr < 0.92) | (sat > 0.06)
    m_our = alpha > 0.5
    wr, wo = widths(m_ref), widths(m_our)
    rows_r = np.nonzero(wr[:, 0] >= 0)[0]
    rows_o = np.nonzero(wo[:, 0] >= 0)[0]
    met = {"reference_rows": [int(rows_r.min()), int(rows_r.max())], "ours_rows": [int(rows_o.min()), int(rows_o.max())],
           "length_px": {"reference": int(rows_r.max() - rows_r.min() + 1), "ours": int(rows_o.max() - rows_o.min() + 1)},
           "iou": float((m_ref & m_our).sum() / max((m_ref | m_our).sum(), 1)), "zones": {}}
    for zname, (r0, r1) in ZONES.items():
        d, dl, dr, cr, co = [], [], [], [], []
        for r in range(r0, r1 + 1):
            if wr[r, 0] < 0 or wo[r, 0] < 0:
                continue
            d.append((wo[r, 1] - wo[r, 0]) - (wr[r, 1] - wr[r, 0]))
            cr.append(0.5 * (wr[r, 0] + wr[r, 1]))
            co.append(0.5 * (wo[r, 0] + wo[r, 1]))
        d = np.array(d, float)
        if len(d):
            met["zones"][zname] = {"rows": [r0, r1], "mean_width_diff_px": round(float(d.mean()), 2),
                                   "mean_abs_width_diff_px": round(float(np.abs(d).mean()), 2),
                                   "max_abs_width_diff_px": round(float(np.abs(d).max()), 1),
                                   "mean_width_diff_mm": round(float(d.mean()) * S.K, 2),
                                   "centre_offset_px": round(float(np.mean(co) - np.mean(cr)), 2)}
    # straightness: centre line drift over rows 470-1200
    rr = np.arange(470, 1201)
    c_o = np.array([0.5 * (wo[r, 0] + wo[r, 1]) for r in rr])
    c_r = np.array([0.5 * (wr[r, 0] + wr[r, 1]) for r in rr])
    met["centre_drift_px"] = {"reference": round(float(np.polyfit(rr, c_r, 1)[0] * (rr[-1] - rr[0])), 2),
                              "ours": round(float(np.polyfit(rr, c_o, 1)[0] * (rr[-1] - rr[0])), 2)}
    # tones: lacquer = pixels 4 px inside the silhouette, rows 800-1000 (stem + pods only), not metal (L <= 0.33)
    def region(mask, w, r0, r1, inset=4):
        sel = np.zeros_like(mask)
        for r in range(r0, r1):
            if w[r, 0] >= 0:
                sel[r, w[r, 0] + inset: w[r, 1] - inset] = True
        return sel & mask
    tones = {}
    for name, img_disp, mask, w in (("reference", ref_disp, m_ref, wr), ("ours", ours_on_white, m_our, wo)):
        L = lum(img_disp)
        body = region(mask, w, 800, 1000)
        lac = body & (L <= 0.33)
        thr = region(mask, w, 41, 160, 2)
        chp = region(mask, w, 1300, 1480, 2)
        mt = (thr | chp) & (L > 0.30)
        tones[name] = {"lacquer_p5_p50_p95": [round(float(np.percentile(L[lac], q)), 3) for q in (5, 50, 95)],
                       "lacquer_mean_rgb": [round(float(v), 3) for v in img_disp[lac].mean(axis=0)],
                       "metal_p50": round(float(np.percentile(L[mt], 50)), 3),
                       "metal_fraction_fittings": round(float(mt.sum() / max((thr | chp).sum(), 1)), 3)}
    met["tones_display"] = tones
    # ---- side-by-side
    H, W = ref_disp.shape[:2]
    ov = np.ones((H, W, 3))
    ov[m_ref & ~m_our] = (0.9, 0.2, 0.2)
    ov[m_our & ~m_ref] = (0.2, 0.35, 0.95)
    ov[m_our & m_ref] = (0.55, 0.55, 0.55)
    gap = np.ones((H, 12, 3))
    sheet = np.concatenate([ref_disp, gap, ours_on_white, gap, ov], 1)
    PNG.write_png(out / "SnowFlower_Sheath_RefView_vs_Reference.png", sheet)
    # ---- detail crops: reference 4x nearest | ours 4x render
    for name, r0, r1, x0, x1 in (("throat", 20, 200, 420, 590), ("band", 270, 335, 430, 580),
                                 ("chape", 1240, 1500, 440, 570), ("vine", 440, 780, 440, 575)):
        p = rd / f"detail_{name}.png"
        if not p.is_file():
            continue
        crop = PNG.upscale(ref_disp[r0:r1, x0:x1], 4)
        d = load(p)
        dd = d[..., :3] * d[..., 3:4] + (1 - d[..., 3:4])
        h = min(crop.shape[0], dd.shape[0])
        w2 = min(crop.shape[1], dd.shape[1])
        PNG.write_png(out / f"SnowFlower_Sheath_Detail_{name.capitalize()}_vs_Reference.png",
                      np.concatenate([crop[:h, :w2], np.ones((h, 16, 3)), dd[:h, :w2]], 1))
    (out / "sheath_compare_metrics.json").write_text(json.dumps(met, indent=1), encoding="utf-8")
    print("SH4_COMPARE", json.dumps(met), flush=True)


if __name__ == "__main__":
    main()
