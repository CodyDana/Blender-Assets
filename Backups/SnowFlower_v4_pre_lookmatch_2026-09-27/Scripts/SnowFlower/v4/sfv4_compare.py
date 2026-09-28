"""Snow Flower v4: reference sheet vs shipped-asset renders, same pixel scale.

    blender -b --factory-startup --python sfv4_compare.py -- --renders <dir> --out <dir> [--prefix ref]

For each of front / side / back: [sheet crop | our render on white | silhouette overlay (red sheet
only, blue ours only, grey both)] and per-row silhouette widths measured the SAME way on both
(sheet: lum < 0.93 or sat > 0.06; ours: alpha > 0.5), written to compare_metrics.json.
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
import sfv4_png as P  # noqa: E402
import sfv4_spec as S  # noqa: E402

ROOT = HERE.parents[2]
REF = ROOT / "References" / "SnowFlower" / "SnowFlower_user_reference.png"
AXIS = {"front": 287.5, "side": 489.0, "back": 681.0}
W = 300


def load(path):
    im = bpy.data.images.load(str(path))
    w, h = im.size
    a = np.array(im.pixels[:], np.float32).reshape(h, w, im.channels)[::-1].copy()
    bpy.data.images.remove(im)
    if a.shape[2] == 3:
        a = np.concatenate([a, np.ones((h, w, 1), np.float32)], 2)
    return a


def fg_sheet(a):
    rgb = a[..., :3]
    lum = rgb @ np.array([.2126, .7152, .0722])
    sat = rgb.max(2) - rgb.min(2)
    return (lum < 0.93) | (sat > 0.06)


def widths(mask, rows, axis=W // 2, gap=3):
    """Per row: the extent of the run that contains (or is nearest to) the axis, bridging gaps of
    <= ``gap`` px, so the tassel and the title text beside the sword are not counted."""
    out = []
    for r in rows:
        idx = np.nonzero(mask[r])[0]
        if len(idx) == 0:
            out.append(None)
            continue
        c = idx[np.argmin(np.abs(idx - axis))]
        if abs(c - axis) > 40:
            out.append(None)
            continue
        lo = hi = c
        s = set(idx.tolist())
        while any((lo - k) in s for k in range(1, gap + 2)):
            lo = max(lo - k for k in range(1, gap + 2) if (lo - k) in s)
        while any((hi + k) in s for k in range(1, gap + 2)):
            hi = max(hi + k for k in range(1, gap + 2) if (hi + k) in s)
        out.append([int(lo), int(hi)])
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--renders", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--prefix", default="ref")
    a = ap.parse_args(argv)
    rd, out = Path(a.renders), Path(a.out)
    rd = rd if rd.is_absolute() else (ROOT / rd).resolve()
    out = out if out.is_absolute() else (ROOT / out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    ref = load(REF)
    H = ref.shape[0]
    metrics = {"mm_per_px": S.MM_PER_PX, "views": {}}
    panels = []
    for view in ("front", "side", "back"):
        ours = load(rd / f"{a.prefix}_{view}.png")
        ours = ours[:H]
        x0 = int(round(AXIS[view] - W / 2))
        refc = ref[:, x0:x0 + W]
        refm = fg_sheet(refc)
        # the sheet's text labels under the views and the side title are not part of the sword
        refm[1225:] = False
        alpha = ours[..., 3]
        om = alpha > 0.5
        on_white = ours[..., :3] * alpha[..., None] + (1 - alpha[..., None])
        ov = np.ones((H, W, 3), np.float32)
        ov[refm & ~om] = (0.90, 0.15, 0.15)
        ov[om & ~refm] = (0.10, 0.60, 0.95)
        ov[refm & om] = (0.30, 0.30, 0.30)
        sep = np.full((H, 6, 3), 0.8, np.float32)
        panels += [refc[..., :3], sep, on_white, sep, ov, sep, sep]
        rows = list(range(0, 1225))
        wr = widths(refm, rows)
        wo = widths(om, rows)
        inter = (refm & om).sum()
        union = (refm | om).sum()
        # row-wise width error on the sword's landmark bands (mm)
        bands = {"pommel": (10, 46), "grip": (47, 262), "collar_guard": (262, 340), "blade_upper": (340, 700),
                 "blade_lower": (700, 1000), "tip": (1000, 1216)}
        berr = {}
        for bname, (r0, r1) in bands.items():
            e = []
            for r in range(r0, r1):
                if wr[r] and wo[r]:
                    e.append(((wo[r][1] - wo[r][0]) - (wr[r][1] - wr[r][0])) * S.MM_PER_PX)
            berr[bname] = {"mean_width_diff_mm": float(np.mean(e)) if e else None,
                           "mean_abs_width_diff_mm": float(np.mean(np.abs(e))) if e else None, "rows": len(e)}
        metrics["views"][view] = {"iou": float(inter / max(union, 1)), "sheet_px": int(refm.sum()), "ours_px": int(om.sum()),
                                  "bands": berr,
                                  "rows_sampled": {str(r): {"sheet": wr[r], "ours": wo[r]} for r in range(0, 1225, 25)}}
    strip = np.concatenate(panels[:-1], 1)
    P.write_png(out / f"compare_{a.prefix}_views.png", strip)
    json.dump(metrics, open(out / f"compare_{a.prefix}_metrics.json", "w"), indent=1)
    print("SF4_COMPARE", json.dumps({v: {"iou": round(m["iou"], 3), **{b: (round(x["mean_width_diff_mm"], 1) if x["mean_width_diff_mm"] is not None else None)
                                                               for b, x in m["bands"].items()}} for v, m in metrics["views"].items()}))


if __name__ == "__main__":
    main()
