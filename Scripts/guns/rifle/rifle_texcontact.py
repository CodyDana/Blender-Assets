"""AR-01 contact sheets of the renders from the baked maps (plain Python, PIL):

    py -3 -B Scripts/guns/rifle/rifle_texcontact.py

review/tex/contact_realism.png   the four realism views + the two ADS holds (spec Sight line / post level with the
                                 notch top), labelled
review/tex/contact_closeups.png  receiver right, front sight, grip checkering, stock, magazine, butt plate, receiver
                                 top, muzzle
review/tex/contact_lods.png      each LOD switch: LOD k and LOD k+1 rendered at the switch distance, cropped
review/tex/sheet_vs_ours_side.png  the sheet's LEFT-labelled panel over our L5 side render (same px <-> mm frame)
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
W = ROOT / "WorkFiles" / "guns" / "rifle"
T = W / "review" / "tex"


def tile(paths, labels, cols, tw, th, out):
    ims = []
    for p, lb in zip(paths, labels):
        if not Path(p).exists():
            continue
        im = Image.open(p).convert("RGB")
        im.thumbnail((tw, th), Image.LANCZOS)
        c = Image.new("RGB", (tw, th), (40, 40, 40))
        c.paste(im, ((tw - im.width) // 2, (th - im.height) // 2))
        ImageDraw.Draw(c).text((8, 6), lb, fill=(255, 255, 255))
        ims.append(c)
    rows = (len(ims) + cols - 1) // cols
    S = Image.new("RGB", (cols * tw, rows * th), (30, 30, 30))
    for i, im in enumerate(ims):
        S.paste(im, ((i % cols) * tw, (i // cols) * th))
    S.save(out)


def crop_fg(im, bg=126, pad=20):
    a = np.asarray(im.convert("RGB"), int)
    m = np.any(np.abs(a - bg) > 6, axis=2)
    ys, xs = np.nonzero(m)
    if not len(ys):
        return im
    return im.crop((max(xs.min() - pad, 0), max(ys.min() - pad, 0), xs.max() + pad, ys.max() + pad))


def main():
    names = ["hero_34", "tp_3m", "fp_35cm", "ads_55deg"]
    labels = ["hero 3/4, 1.5 m", "third person, 3 m", "first person, eye 35 cm", "ADS, 55 deg, 0.25 m behind Sight"]
    tile([T / f"{n}.png" for n in names], labels, 2, 960, 540, T / "contact_realism.png")
    cu = ["cu_receiver_right", "cu_front_sight", "cu_grip_checker", "cu_stock_r34", "cu_mag_left", "cu_buttplate",
          "cu_receiver_top", "cu_muzzle_34"]
    tile([T / f"{n}.png" for n in cu], [n[3:].replace("_", " ") for n in cu], 4, 640, 480, T / "contact_closeups.png")
    crops, labs = [], []
    for k in (1, 2, 3):
        for lv in (k - 1, k):
            p = T / f"lod_switch{k}_lod{lv}.png"
            if p.exists():
                c = crop_fg(Image.open(p))
                c = c.resize((c.width * 4, c.height * 4), Image.NEAREST)
                cp = T / f"_lodcrop_{k}_{lv}.png"
                c.save(cp)
                crops.append(cp)
                labs.append(f"switch {k}: LOD{lv} (4x nearest)")
    tile(crops, labs, 2, 900, 360, T / "contact_lods.png")
    for p in crops:
        p.unlink()
    side = T / "tex_side.png"
    if side.exists():
        j = json.loads((W / "trace" / "LEFT_outline.json").read_text())
        x0, y0, x1, y1 = j["panel_box_sheet_px"]
        a = Image.open(side).convert("RGB")
        s = Image.open(ROOT / "References" / "Guns" / "Rifle" / "rifle_sheetAB.webp").convert("RGB").crop(
            (x0, y0, x1 + 1, y1 + 1)).resize(a.size, Image.LANCZOS)
        c = Image.new("RGB", (a.width, a.height * 2))
        c.paste(s, (0, 0))
        c.paste(a, (0, a.height))
        c.thumbnail((2000, 2000))
        c.save(T / "sheet_vs_ours_side.png")
    print("[texcontact] wrote", T)


if __name__ == "__main__":
    main()
