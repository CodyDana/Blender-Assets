"""Quick look during a build round: reference panel | ours for chosen variants and views (system Python).

    py -3 -B Scripts/dojo/pines/quick_look.py --renders DIR --variants PineA1 [--views front,side,3q] [--out FILE]

Uses compose_pines' pairing and grey compositing; one strip per variant, reference panels on the left of each pair.
Also prints the silhouette IoU per view and the trunk width at 1/4 height measured on our sil render (the girth
check, same method as the sheet: rows around 1/4 of the tree height, the wood run through the trunk centreline).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "Scripts" / "vegetation"))
import compose_pines as cp  # noqa: E402
import measure_tree as mt  # noqa: E402
import ref_panels as rp  # noqa: E402


def our_trunk_width(rdir, v, view, meta):
    """Trunk width (m) at 1/4 of the tree height on our sil render: wood pixels in a run through the trunk."""
    img = np.asarray(Image.open(rdir / f"{v}_{view}_sil.png").convert("RGBA")).astype(np.float32)
    a = img[..., 3] > 128
    wood = a & (np.abs(img[..., 0] - 130) < 25) & (np.abs(img[..., 1] - 80) < 25)
    m = meta[f"{v}_{view}"]
    bx, by = m["base_px"]
    pxm = m["px_per_m"]
    ys = np.nonzero(a.any(1))[0]
    top = ys.min()
    ground = by
    y = int(round(ground - 0.25 * (ground - top)))
    ws = []
    # follow the trunk up from the base: at each row take the wood run nearest the previous centre
    cx = bx
    for yy in range(int(ground) - 2, y - 4, -1):
        row = wood[yy]
        xs = np.nonzero(row)[0]
        if not len(xs):
            continue
        d = np.diff(np.r_[0, row.astype(int), 0])
        st, en = np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]
        k = int(np.argmin(np.abs((st + en) / 2 - cx)))
        cx = 0.5 * (st[k] + en[k])
        if abs(yy - y) <= 3:
            ws.append(en[k] - st[k])
    return float(np.median(ws)) / pxm if ws else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--renders", required=True)
    ap.add_argument("--variants", default="PineA1")
    ap.add_argument("--views", default="front,side,3q")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    rdir = Path(a.renders)
    if not rdir.is_absolute():
        rdir = ROOT / rdir
    meta = json.loads((rdir / "render_meta.json").read_text())
    sheet = mt.load_rgb(str(ROOT / rp.SHEET))
    bg = mt.background_colour(sheet[20:60, 300:700])
    ref_img = Image.open(ROOT / rp.SHEET).convert("RGB")
    rows = []
    for v in a.variants.split(","):
        pine = cp.SPEC[v]["pine"]
        tiles = []
        for view in a.views.split(","):
            key = f"{v}_{view}"
            if key not in meta:
                continue
            rn = cp.ref_panel_name(v, view)
            img, alpha = cp.on_grey(rdir / f"{key}_final.png", meta[key]["base_px"][1])
            x0, y0, x1, y1 = cp.content_box(alpha)
            y1 = max(y1, int(meta[key]["base_px"][1]) + 8)
            ours = img.crop((x0, y0, x1, y1))
            ref = ref_img.crop(rp.PANELS[rn]["box"])
            H = 520
            r2 = ref.resize((int(ref.size[0] * H / ref.size[1]), H), Image.LANCZOS)
            o2 = ours.resize((max(1, int(ours.size[0] * H / ours.size[1])), H), Image.LANCZOS)
            t = Image.new("RGB", (r2.size[0] + o2.size[0] + 10, H), (255, 255, 255))
            t.paste(r2, (0, 0))
            t.paste(o2, (r2.size[0] + 10, 0))
            tiles.append(t)
            # numbers
            rm, rbase, _ = cp.ref_masks(sheet, bg, rn)
            om, obase, opxm = cp.our_masks(rdir, v, view, meta, pine)
            ref_pxm = (rp.PANELS[rn]["figure"][1] - rp.PANELS[rn]["figure"][0]) / rp.FIGURE_M
            iou, mr, mo = cp.metrics_pair(rm, rbase, ref_pxm, om, obase, opxm, pine)
            tw = our_trunk_width(rdir, v, view, meta) if pine != 4 else None
            print(f"{key} vs {rn}: IoU {iou['iou']:.3f} werr {iou['width_err']:.3f} row_fill ref {mr.get('row_fill')} "
                  f"ours {mo.get('row_fill')} crown ref {mr.get('crown_w_m')} ours {mo.get('crown_w_m')} "
                  f"height ref {mr.get('height_m')} ours {mo.get('height_m')} pads ref {mr.get('pads_auto')} ours "
                  f"{mo.get('pads_auto')} trunk@1/4 ours {tw}")
        W = sum(t.size[0] for t in tiles) + 20 * len(tiles)
        row = Image.new("RGB", (W, 520), (255, 255, 255))
        x = 0
        for t in tiles:
            row.paste(t, (x, 0))
            x += t.size[0] + 20
        rows.append(row)
    W = max(r.size[0] for r in rows)
    out = Image.new("RGB", (W, 540 * len(rows)), (255, 255, 255))
    for i, r in enumerate(rows):
        out.paste(r, (0, 540 * i))
    op = Path(a.out) if a.out else rdir / "quick_look.png"
    out.save(op)
    print("wrote", op)


if __name__ == "__main__":
    main()
