"""Pilot 2 measurement (study 6.1 / 6.2, the SAME code on the sheet and on ours, ours resampled to the sheet's px).
numpy + PIL (system Python):

    py -3 -B Scripts/dojo/rocks/rocks_measure2.py surface        the surface gate (test patch vs the sheet panels)
    py -3 -B Scripts/dojo/rocks/rocks_measure2.py all [--sbs]    silhouettes (IoU per view incl. the oblique / 3/4
                                                                 views), values per region, moss share, close-ups,
                                                                 riverbank, side-by-sides

Contrast measures that do not depend on exposure are reported beside the raw ones (study 3.11 method C rule: ratios
across different lighting): local std / p50 and the dark share below the sheet's own dark threshold relative to its
median (0.25 / 0.5726 = 0.437 x p50 for the grain panel).
Writes WorkFiles/dojo/build/rocks/pilot2/measure.json (+ surface.json) and pilot2/sbs/*.png (pilot 1's file names).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Scripts" / "stone"))
sys.path.insert(0, str(ROOT / "Scripts" / "dojo" / "rocks"))
import rock_ref as rr          # noqa: E402
import stone_measure as sm     # noqa: E402
import rocks_ref as ref        # noqa: E402

BUILD = ROOT / "WorkFiles" / "dojo" / "build" / "rocks"
P2 = BUILD / "pilot2"
SBS = P2 / "sbs"
REFC = BUILD / "pilot" / "refcrops"
BG = (186, 186, 186)
ROCKS = ["RiverRound", "RiverLong", "CliffChunk"]


def lum(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def local_std(L, mask=None, b=16):
    H, W = L.shape
    out = []
    for y in range(0, H - b + 1, b):
        for x in range(0, W - b + 1, b):
            if mask is None or mask[y:y + b, x:x + b].mean() > 0.8:
                out.append(float(L[y:y + b, x:x + b].std()))
    return float(np.mean(out)) if out else float("nan")


def contrast(rgb, mask=None, dark_rel=0.437):
    """rgb float 0-1 (sRGB)."""
    L = lum(rgb)
    la = L if mask is None else L[mask]
    p50 = float(np.median(la))
    ls = local_std(L, mask)
    v = sm.image_values(rgb, mask)
    return {"luma_p5_p25_p50_p75_p95": [round(float(x), 4) for x in np.percentile(la, (5, 25, 50, 75, 95))],
            "local_std_16px": round(ls, 4), "local_std_over_p50": round(ls / max(p50, 1e-6), 4),
            "dark_lt_0.25": round(float((la < 0.25).mean()), 4),
            "dark_rel": round(float((la < dark_rel * p50).mean()), 4),
            "R_over_B": v["method_A"]["R_over_B"], "hue": v["method_C"]["stone_hue_deg"],
            "sat": v["method_C"]["stone_sat"], "p90_over_p50": v["method_C"]["p90_over_p50"],
            "moss_share": v["moss_share"]}


def load_rgb(path, box=None):
    im = Image.open(path).convert("RGB")
    if box:
        im = im.crop(box)
    return im


def to_size(im, size):
    return np.asarray(im.resize(size, Image.LANCZOS), np.float64) / 255.0


def label(im, text):
    d = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype("arial.ttf", 22)
    except OSError:
        f = ImageFont.load_default()
    d.rectangle((0, 0, 12 + 12 * len(text), 32), fill=(30, 30, 30))
    d.text((6, 4), text, fill=(240, 240, 240), font=f)
    return im


def sbs(left, right, path, h=520, labels=("sheet", "ours")):
    L = left.resize((max(1, int(left.width * h / left.height)), h), Image.LANCZOS)
    R = right.resize((max(1, int(right.width * h / right.height)), h), Image.LANCZOS)
    out = Image.new("RGB", (L.width + R.width + 12, h), (20, 20, 20))
    out.paste(label(L, labels[0]), (0, 0))
    out.paste(label(R, labels[1]), (L.width + 12, 0))
    path.parent.mkdir(parents=True, exist_ok=True)
    out.save(path)
    return str(path.relative_to(ROOT))


SHEET = ROOT / "References" / "Dojo" / "dojo_rocks_ref.png"
PANELS = {"grain": (12, 850, 174, 1075), "fracture": (188, 850, 342, 1075), "moss": (355, 850, 517, 1075),
          "wetline": (531, 850, 696, 1075), "lichen": (710, 850, 862, 1075), "riverbank": (877, 844, 1444, 1082)}


def surface():
    out = {}
    sheet = Image.open(SHEET).convert("RGB")
    for shot, panel in (("grain", "grain"), ("lichen", "lichen"), ("wet", "wetline"), ("mid", "fracture")):
        p = P2 / "surface" / f"patch_{shot}.png"
        if not p.exists():
            continue
        b = PANELS[panel]
        size = (b[2] - b[0], b[3] - b[1])
        ref_rgb = np.asarray(sheet.crop(b), np.float64) / 255.0
        ours_im = load_rgb(p)
        # crop ours to the panel's aspect (centre) before resampling to the panel's px
        W, H = ours_im.size
        asp = size[0] / size[1]
        if W / H > asp:
            w = int(H * asp)
            ours_im = ours_im.crop(((W - w) // 2, 0, (W - w) // 2 + w, H))
        else:
            h = int(W / asp)
            ours_im = ours_im.crop((0, (H - h) // 2, W, (H - h) // 2 + h))
        ours = to_size(ours_im, size)
        out[shot] = {"sheet_panel": contrast(ref_rgb), "ours_at_sheet_px": contrast(ours), "panel_px": size}
        sbs(sheet.crop(b), ours_im, P2 / "surface" / f"sbs_patch_{shot}.png")
    (P2 / "surface" / "surface.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for k, v in out.items():
        print(k)
        for s in ("sheet_panel", "ours_at_sheet_px"):
            x = v[s]
            print(f"  {s:17s} luma {x['luma_p5_p25_p50_p75_p95']} lstd {x['local_std_16px']} "
                  f"lstd/p50 {x['local_std_over_p50']} dark<.25 {x['dark_lt_0.25']} dark_rel {x['dark_rel']} "
                  f"R/B {x['R_over_B']} hue {x['hue']} sat {x['sat']}")
    return out


def main():
    argv = sys.argv[1:]
    mode = argv[0] if argv else "all"
    if mode == "surface":
        surface()
        return
    import rocks_measure2_all as ma
    ma.run("--sbs" in argv)


if __name__ == "__main__":
    main()
