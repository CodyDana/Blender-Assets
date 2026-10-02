"""Mist / spray side-by-side against the sheet's cut-out panel, plus shape measurements (plain Python 3).

    py -3 -B Scripts/dojo/fx/compose_mist.py

Ours is lit here the way the Unreal material will light it: the six-way maps combined with a warm low sun from behind
upper-left (the sheet's backlight) and a cool dim fill, on black like the cut-outs. Measured per cut-out and per
sprite (opacity from luminance on black for the sheet, the real alpha for ours): bbox aspect (w/h at alpha > 0.1),
fill (area / bbox), feather (share of the visible area with 0.05 < alpha < 0.5: the edge softness) and the
core opacity (p95 of alpha).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fx_common as fx  # noqa: E402

PANEL = (737, 722, 1432, 1066)
CUTOUTS = {  # sheet cut-outs (original pixel boxes) -> our sprite (flipbook, frame)
    "puff": ((744, 742, 987, 887), ("MistPuff", 26)),
    "wisp": ((972, 752, 1227, 872), ("MistWisp", 22)),
    "plume": ((1217, 737, 1397, 882), ("MistWisp", 40)),
    "bank": ((737, 907, 987, 1032), ("Haze", None)),
    "spray_crown": ((957, 872, 1202, 1057), ("SprayBurst", 22)),
    "spray_column": ((1217, 862, 1412, 1057), ("SprayBurst", 34)),
}
SUN = np.array([1.0, 0.70, 0.46])
FILL = np.array([0.20, 0.22, 0.30])


def load(name):
    return np.asarray(Image.open(fx.TEX / name).convert("RGBA")).astype(np.float32) / 255.0


def cell(img, frame, grid=8):
    c = img.shape[0] // grid
    r, k = divmod(frame, grid)
    return img[r * c:(r + 1) * c, k * c:(k + 1) * c]


SKY = np.array([0.45, 0.50, 0.62])
# direction TO the sun in sprite space (x right, y up, z away from the viewer): upper left, slightly behind (the cut-outs are lit from the top left)
LS = np.array([-0.55, 0.60, 0.25]) / np.linalg.norm([-0.55, 0.60, 0.25])


def lit(P, N, ambient=0.8):
    """The catalog's M_DKF_SixWaySprite formula: key = sum max(+-Ls, 0) * six-way; + sky * (P.g/2 + 0.3 N.b + 0.2)."""
    key = (max(LS[0], 0) * P[..., 0] + max(-LS[0], 0) * N[..., 0] + max(LS[1], 0) * P[..., 1] +
           max(-LS[1], 0) * N[..., 1] + max(LS[2], 0) * P[..., 2] + max(-LS[2], 0) * N[..., 2])
    amb = 0.5 * P[..., 1] + 0.3 * N[..., 2] + 0.2
    rgb = key[..., None] * SUN * 1.1 + amb[..., None] * SKY * ambient
    a = P[..., 3:4]
    return np.clip(rgb, 0, 1) * a, a[..., 0]


def shape_stats(alpha):
    vis = alpha > 0.05
    if not vis.any():
        return {}
    m = alpha > 0.1
    ys, xs = np.nonzero(m)
    w, h = xs.max() - xs.min() + 1, ys.max() - ys.min() + 1
    return {"aspect_w_over_h": round(float(w / h), 3), "fill": round(float(m.sum() / (w * h)), 3),
            "feather": round(float(((alpha > 0.05) & (alpha < 0.5)).sum() / vis.sum()), 3),
            "core_p95": round(float(np.percentile(alpha[vis], 95)), 3)}


def ref_alpha(crop):
    lum = crop.mean(axis=-1)
    bg = np.percentile(lum, 5)
    core = np.percentile(lum, 99.5)
    return np.clip((lum - bg) / max(core - bg, 1e-3), 0, 1)


def main():
    ref = np.asarray(Image.open(fx.MIST_REF).convert("RGB")).astype(np.float32) / 255.0
    books = {}
    for n in ("MistPuff", "MistWisp", "SprayBurst"):
        books[n] = (load(f"T_DKF_{n}_SixWayP.png"), load(f"T_DKF_{n}_SixWayN.png"))
    haze = load("T_DKF_Haze_M.png")
    x0, y0, x1, y1 = PANEL
    W, H = (x1 - x0), (y1 - y0)
    ours = np.zeros((H, W, 3), np.float32)
    stats = {}
    for key, (box, (book, frame)) in CUTOUTS.items():
        bx0, by0, bx1, by1 = box
        bw, bh = bx1 - bx0, by1 - by0
        if book == "Haze":
            m = haze
            a = m[..., 0]
            key_l = 0.6 * m[..., 2] + 0.4 * m[..., 1]
            rgb = key_l[..., None] * SUN * 1.1 * a[..., None] + 0.08 * FILL * a[..., None]
        else:
            P, N = books[book]
            rgb, a = lit(cell(P, frame), cell(N, frame), 1.4 if book == "SprayBurst" else 0.35)
        # fit the sprite's alpha bbox into the cut-out box (keep aspect), like placing a Niagara sprite
        m = a > 0.03
        ys, xs = np.nonzero(m)
        crop_rgb = rgb[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        crop_a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        s = min(bw / crop_a.shape[1], bh / crop_a.shape[0])
        nw, nh = max(1, int(crop_a.shape[1] * s)), max(1, int(crop_a.shape[0] * s))
        im = Image.fromarray((np.clip(crop_rgb, 0, 1) * 255).astype(np.uint8)).resize((nw, nh), Image.LANCZOS)
        ia = Image.fromarray((crop_a * 255).astype(np.uint8)).resize((nw, nh), Image.LANCZOS)
        ox = bx0 - x0 + (bw - nw) // 2
        oy = by0 - y0 + (bh - nh) // 2
        region = ours[oy:oy + nh, ox:ox + nw]
        rr = np.asarray(im).astype(np.float32)[:region.shape[0], :region.shape[1]] / 255
        region[:] = np.maximum(region, rr)  # additive-ish on black
        stats[key] = {"ours": shape_stats(a), "sheet": shape_stats(ref_alpha(ref[by0:by1, bx0:bx1])),
                      "our_source": f"{book} frame {frame}" if frame is not None else book}
    sheet = (ref[y0:y1, x0:x1] * 255).astype(np.uint8)
    out = Image.new("RGB", (W * 2 + 20, H + 30), (40, 40, 40))
    out.paste(Image.fromarray(sheet), (0, 30))
    out.paste(Image.fromarray((ours * 255).astype(np.uint8)), (W + 20, 30))
    d = ImageDraw.Draw(out)
    d.text((6, 8), "SHEET cut-outs (dojo_mist_ref)", fill=(230, 230, 230))
    d.text((W + 26, 8), "OURS: MistPuff f26 | MistWisp f22 | MistWisp f40 / Haze | SprayBurst f22 | f34, six-way lit at sunset",
           fill=(230, 230, 230))
    dst = fx.WORK / "renders/flipbooks"
    dst.mkdir(parents=True, exist_ok=True)
    big = out.resize((out.width * 2, out.height * 2), Image.LANCZOS)
    big.save(dst / "SBS_mist_cutouts_ref_vs_ours.png")
    # the full flipbooks (neutral top-lit and sunset-lit) for the sheet
    for n, (P, N) in books.items():
        rgb, a = lit(P, N, 1.4 if n == "SprayBurst" else 0.35)
        Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)).resize((1024, 1024), Image.LANCZOS).save(
            dst / f"{n}_8x8_sunset_lit.png")
    fx.write_json(fx.WORK / "json/mist_measure.json", stats)
    for k, v in stats.items():
        print(k, v)


if __name__ == "__main__":
    main()
