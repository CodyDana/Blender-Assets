"""Lays out the kit 9 review renders (render_training.py raw views) as model sheets like the reference
(References/Dojo/dojo_training_props_ref.png): plain light-grey background, a grey 1.8 m silhouette, then the front and
side elevations, the top view and a 3/4 perspective, all orthographic views at the same px/m and on one ground line.
Also: close-up contact sheets, the reference crop of each prop (for side_by_side.py) and the measured stats.

Run (system Python with Pillow): py Scripts/dojo/props/training/make_training_sheets.py <renders dir>
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[4]
REF = ROOT / "References" / "Dojo" / "dojo_training_props_ref.png"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "WorkFiles/dojo/build/props/training/renders/r0"
RAW = OUT / "raw"
BG = (181, 182, 182)          # the reference sheet's background (measured)
SIL = (123, 122, 121)         # the reference silhouette grey (measured)
GAP = 50

# reference crops (sheet pixels): each prop's front + side views with the silhouette that stands beside them
REF_CROPS = {
    "SM_DKP_Train_Makiwara": (40, 50, 432, 392),
    "SM_DKP_Train_StrikingPost": (478, 50, 870, 392),
    "SM_DKP_Train_WoodenDummy": (888, 50, 1415, 400),
    "SM_DKP_Train_LongArmDummy": (40, 440, 650, 770),
    "SM_DKP_Train_WeaponRack": (685, 470, 1415, 770),
    "SM_DKP_Train_Bench": (40, 790, 910, 1030),
    "SM_DKP_Train_Stool": (975, 790, 1385, 1030),
}


def over_bg(path, bg=BG):
    """Composite an RGBA render (straight alpha, shadow-catcher shadows in alpha) over the flat background."""
    im = np.asarray(Image.open(path).convert("RGBA")).astype(np.float32) / 255.0
    rgb, a = im[..., :3], im[..., 3:4]
    # the shadow catcher leaves a faint veil of world occlusion over the whole floor: keep contact shadows only
    solid = (rgb.max(-1, keepdims=True) > 0.02).astype(np.float32)
    a = np.where(solid > 0, a, np.clip((a - 0.12) / 0.88, 0, 1))
    out = rgb * a + (np.array(bg, np.float32) / 255.0) * (1 - a)
    return Image.fromarray(np.clip(out * 255 + 0.5, 0, 255).astype(np.uint8)), im[..., 3]


def silhouette_img():
    im = np.asarray(Image.open(RAW / "silhouette_front.png").convert("RGBA")).astype(np.float32) / 255.0
    a = (im[..., 3] > 0.5).astype(np.float32)[..., None]
    ys, xs = np.where(a[..., 0] > 0)
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    out = np.array(SIL, np.float32) * a + np.array(BG, np.float32) * (1 - a)
    return Image.fromarray(out.astype(np.uint8))


def trim_ground(img, alpha, keep_bottom=True):
    """Crop to the object's columns (alpha of the render, shadows included only faintly) keeping the full height."""
    cols = np.where(alpha.max(0) > 0.35)[0]
    rows = np.where(alpha.max(1) > 0.35)[0]
    x0, x1 = max(cols.min() - 10, 0), min(cols.max() + 10, img.width)
    y0 = max(rows.min() - 10, 0)
    return img.crop((x0, y0, x1, img.height))


def model_sheet(name):
    sil = silhouette_img()
    front, fa = over_bg(RAW / f"{name}_front.png")
    side, sa = over_bg(RAW / f"{name}_side.png")
    top, ta = over_bg(RAW / f"{name}_top.png")
    p34, pa = over_bg(RAW / f"{name}_34.png")
    p34 = trim_ground(p34, pa)
    rows = np.where(pa.max(1) > 0.35)[0]
    p34 = p34.crop((0, 0, p34.width, min(p34.height, rows.max() - (pa.shape[0] - p34.height) + 30)))
    front, side = trim_ground(front, fa), trim_ground(side, sa)
    # the ortho renders put the ground 0.06 m * PPM above the bottom edge; the silhouette's feet go on that line
    ppm = 400
    ground_off = int(round(0.06 * ppm))
    row_h = max(sil.height + ground_off, front.height, side.height, top.height) + 2 * GAP
    ground_y = row_h - GAP
    h34 = int(min(row_h * 0.86, max(front.height * 1.25, 380)))
    p34 = p34.resize((int(p34.width * h34 / p34.height), h34), Image.LANCZOS)
    col = None
    if (RAW / f"{name}_collision.png").exists():   # f1: UCX overlay panel, same framing as the 3/4 view
        col, ca = over_bg(RAW / f"{name}_collision.png")
        col = trim_ground(col, ca)
        rows_c = np.where(ca.max(1) > 0.35)[0]
        col = col.crop((0, 0, col.width, min(col.height, rows_c.max() - (ca.shape[0] - col.height) + 30)))
        col = col.resize((int(col.width * h34 / col.height), h34), Image.LANCZOS)
    W = GAP + sil.width + GAP // 2 + front.width + GAP + side.width + 2 * GAP + top.width + 2 * GAP + p34.width + GAP
    if col is not None:
        W += GAP + col.width
    sheet = Image.new("RGB", (W, row_h), BG)
    x = GAP
    sheet.paste(sil, (x, ground_y - ground_off - sil.height))
    x += sil.width + GAP // 2
    for im in (front, side):
        sheet.paste(im, (x, ground_y - im.height))
        x += im.width + GAP
    x += GAP
    sheet.paste(top, (x, (row_h - top.height) // 2))
    x += top.width + 2 * GAP
    sheet.paste(p34, (x, (row_h - p34.height) // 2))
    if col is not None:
        x += p34.width + GAP
        sheet.paste(col, (x, (row_h - col.height) // 2))
    sheet.save(OUT / f"{name}_sheet.png")
    # the like-for-like strip for the side-by-side: silhouette, front, side (as the reference shows them)
    sw = GAP + sil.width + GAP // 2 + front.width + GAP + side.width + GAP
    strip = Image.new("RGB", (sw, row_h), BG)
    x = GAP
    strip.paste(sil, (x, ground_y - ground_off - sil.height))
    x += sil.width + GAP // 2
    for im in (front, side):
        strip.paste(im, (x, ground_y - im.height))
        x += im.width + GAP
    strip.save(OUT / f"{name}_strip.png")
    ref = Image.open(REF).convert("RGB").crop(REF_CROPS[name])
    # upscaled to our strip height so side_by_side.py (which fits both to the smaller height) keeps our resolution
    ref = ref.resize((int(ref.width * row_h / ref.height), row_h), Image.LANCZOS)
    ref.save(RAW / f"ref_{name}.png")
    return {"sheet": str(OUT / f"{name}_sheet.png"), "size": [W, row_h]}


def closeups():
    shots = sorted(RAW.glob("close_*.png"))
    by_prop = {}
    for s in shots:
        prop = "_".join(s.stem.split("_")[1:5])
        by_prop.setdefault(prop, []).append(s)
    made = []
    for prop, files in by_prop.items():
        ims = [over_bg(f)[0] for f in files]
        w = 700
        ims = [im.resize((w, int(im.height * w / im.width)), Image.LANCZOS) for im in ims]
        cols = min(3, len(ims))
        rows = (len(ims) + cols - 1) // cols
        h = max(im.height for im in ims)
        sheet = Image.new("RGB", (cols * w + (cols + 1) * 16, rows * h + (rows + 1) * 16), BG)
        for i, im in enumerate(ims):
            sheet.paste(im, (16 + (i % cols) * (w + 16), 16 + (i // cols) * (h + 16)))
        path = OUT / f"closeups_{prop}.png"
        sheet.save(path)
        made.append(str(path))
    return made


def main():
    names = sorted({p.stem.rsplit("_", 1)[0] for p in RAW.glob("SM_DKP_Train_*_front.png")})
    rep = {"sheets": {n: model_sheet(n) for n in names}, "closeups": closeups()}
    if (RAW / "lineup_sunset.png").exists():
        Image.open(RAW / "lineup_sunset.png").convert("RGB").save(OUT / "lineup_sunset.png")
    if (RAW / "context_sunset.png").exists():
        Image.open(RAW / "context_sunset.png").convert("RGB").save(OUT / "context_sunset.png")
    (OUT / "sheets_report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
