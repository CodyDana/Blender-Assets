"""Snow Flower sheath look-match: part-by-part BEFORE / AFTER against the reference, on the reference's own grid.

    blender -b --factory-startup --python shv4_lookmatch_compare.py -- --before <dir> --after <dir> --out <dir>

<before>/<after> hold ref_front.png (the front orthographic render of the SHIPPED asset on the reference grid) and
detail_<part>.png (4x crops framed like the reference crops), both produced by shv4_render.py from the exported FBX and
the exported PNGs.  Writes, per part, compare_<part>.png = [reference crop 4x | before | after] and one
lookmatch_metrics.json with measured numbers for both (silhouette IoU and zone widths, lacquer tone percentiles and
contrast, metal brightness and contrast, pearl brightness, and a structural score per part: the correlation of the
band-passed luminance with the reference's, 1.0 = identical structure).
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
sys.path.insert(0, str(HERE / "shv4_lib"))
import sfv4_png as PNG  # noqa: E402
import shv4_spec as S  # noqa: E402

REF = S.ROOT / "References" / "SnowFlower" / "SnowFlower_sheath_reference.png"
PARTS = {"throat": (20, 200, 420, 590), "band": (270, 335, 430, 580), "chape": (1240, 1500, 440, 570),
         "vine": (440, 780, 440, 575)}
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


def lum(rgb):
    return rgb @ np.array([0.2126, 0.7152, 0.0722])


def on_white(a):
    return a[..., :3] * a[..., 3:4] + (1 - a[..., 3:4])


def blur(x, r):
    if r <= 0:
        return x
    k = np.exp(-0.5 * (np.arange(-3 * r, 3 * r + 1) / r) ** 2)
    k /= k.sum()
    y = np.apply_along_axis(lambda v: np.convolve(v, k, mode="same"), 0, x)
    return np.apply_along_axis(lambda v: np.convolve(v, k, mode="same"), 1, y)


def structure_score(a, b):
    """Correlation of band-passed luminance (2-8 px structures) of two same-size greyscale crops."""
    fa = blur(a, 1.0) - blur(a, 4.0)
    fb = blur(b, 1.0) - blur(b, 4.0)
    fa, fb = fa - fa.mean(), fb - fb.mean()
    return float((fa * fb).sum() / max(np.sqrt((fa * fa).sum() * (fb * fb).sum()), 1e-9))


def widths(mask):
    out = np.full((mask.shape[0], 2), -1, int)
    for r in range(mask.shape[0]):
        idx = np.nonzero(mask[r])[0]
        if len(idx):
            out[r] = [idx.min(), idx.max()]
    return out


def measure(ref_disp, ours_rgba):
    ours = on_white(ours_rgba)
    alpha = ours_rgba[..., 3]
    Lr, Lo = lum(ref_disp), lum(ours)
    sat = ref_disp.max(2) - ref_disp.min(2)
    m_ref = (Lr < 0.92) | (sat > 0.06)
    m_our = alpha > 0.5
    wr, wo = widths(m_ref), widths(m_our)
    out = {"iou": round(float((m_ref & m_our).sum() / max((m_ref | m_our).sum(), 1)), 4), "zones": {}}
    for zname, (r0, r1) in ZONES.items():
        d = [(wo[r, 1] - wo[r, 0]) - (wr[r, 1] - wr[r, 0]) for r in range(r0, r1 + 1) if wr[r, 0] >= 0 and wo[r, 0] >= 0]
        if d:
            out["zones"][zname] = {"mean_width_diff_px": round(float(np.mean(d)), 2),
                                   "mean_abs_width_diff_px": round(float(np.mean(np.abs(d))), 2)}

    def region(mask, w, r0, r1, inset=4):
        sel = np.zeros_like(mask)
        for r in range(r0, r1):
            if w[r, 0] >= 0:
                sel[r, w[r, 0] + inset: w[r, 1] - inset] = True
        return sel & mask
    tones = {}
    for name, img, mask, w in (("reference", ref_disp, m_ref, wr), ("ours", ours, m_our, wo)):
        L = lum(img)
        body = region(mask, w, 780, 1000)
        lac = body & (L <= 0.33)
        fit = (region(mask, w, 41, 160, 2) | region(mask, w, 1300, 1480, 2))
        metal = fit & (L > 0.30)
        vine = region(mask, w, 450, 760, 6)
        pearl = vine & (L > 0.62)
        tones[name] = {"lacquer_p5_p50_p95": [round(float(np.percentile(L[lac], q)), 3) for q in (5, 50, 95)],
                       "lacquer_std": round(float(L[lac].std()), 4),
                       "lacquer_mean_rgb": [round(float(v), 3) for v in img[lac].mean(axis=0)],
                       "lacquer_blue_minus_red": round(float(img[lac][:, 2].mean() - img[lac][:, 0].mean()), 4),
                       "metal_p50_p90": [round(float(np.percentile(L[metal], q)), 3) for q in (50, 90)],
                       "metal_std": round(float(L[metal].std()), 4),
                       "fittings_metal_fraction": round(float(metal.sum() / max(fit.sum(), 1)), 3),
                       "vine_bright_fraction": round(float(pearl.sum() / max(vine.sum(), 1)), 4)}
    out["tones_display"] = tones
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", required=True)
    ap.add_argument("--after", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    bd, ad, out = Path(a.before), Path(a.after), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    ref = load(REF)[..., :3]
    met = {"reference": str(REF), "before": {}, "after": {}, "parts": {}}
    fb = load(bd / "ref_front.png")
    fa = load(ad / "ref_front.png")
    met["before"] = measure(ref, fb)
    met["after"] = measure(ref, fa)
    gap = np.ones((ref.shape[0], 12, 3))
    PNG.write_png(out / "compare_full.png", np.concatenate([ref, gap, on_white(fb), gap, on_white(fa)], 1))
    for part, (r0, r1, x0, x1) in PARTS.items():
        crop = PNG.upscale(ref[r0:r1, x0:x1], 4)
        rowset = [crop]
        rec = {}
        for tag, d in (("before", bd), ("after", ad)):
            p = d / f"detail_{part}.png"
            if not p.is_file():
                continue
            img = on_white(load(p))
            h, w = min(crop.shape[0], img.shape[0]), min(crop.shape[1], img.shape[1])
            rowset.append(img[:h, :w])
            # structure at the reference scale: our 4x render box-averaged down to the reference grid
            small = img[:h - h % 4, :w - w % 4].reshape(h // 4, 4, w // 4, 4, 3).mean(axis=(1, 3))
            refc = ref[r0:r0 + small.shape[0], x0:x0 + small.shape[1]]
            rec[tag] = {"structure_score": round(structure_score(lum(refc), lum(small)), 4),
                        "mean_abs_lum_diff": round(float(np.abs(blur(lum(refc), 1.5) - blur(lum(small), 1.5)).mean()), 4)}
        h = min(x.shape[0] for x in rowset)
        tiles = []
        for x in rowset:
            tiles += [x[:h], np.ones((h, 14, 3))]
        PNG.write_png(out / f"compare_{part}.png", np.concatenate(tiles[:-1], 1))
        met["parts"][part] = rec
    (out / "lookmatch_metrics.json").write_text(json.dumps(met, indent=1), encoding="utf-8")
    print("SH4_LOOKMATCH", json.dumps(met["parts"]), flush=True)


if __name__ == "__main__":
    main()
