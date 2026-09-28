"""hy_sheets.py -- PRIVATE / DO NOT SHIP. Side-by-side sheets: the user's Hiyuki screenshots next to our
MH_Hiyuki_Private renders at matching framing (our render is scaled + cropped so the two iris centres land on the
reference's iris centres). Iris centres = 2-means clusters of the strongly-red pixels inside an eye box (both have red irises).
    py -3 Scripts/MetaHuman/hy_sheets.py [captures_dir]
Writes WorkFiles/MetaHuman/hiyuki_private/sheets/*.png
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(r"C:/Users/Cody/Desktop/Blender_Projects")
REFS = ROOT / "References/Characters/Hiyuki_private"
OUT = ROOT / "WorkFiles/MetaHuman/hiyuki_private"
CAP = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT / "verify_captures"
SHEETS = OUT / "sheets"
H = 640


def red_eyes(im: Image.Image, box=None, gr=1.8):
    """two largest strongly-red blobs -> (left_xy, right_xy) in image pixels, sorted by x"""
    a = np.asarray(im.convert("RGB")).astype(float)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    m = (r > 120) & (r > gr * g) & (r > 1.5 * b)
    if box:
        mm = np.zeros_like(m)
        x0, y0, x1, y1 = box
        mm[y0:y1, x0:x1] = m[y0:y1, x0:x1]
        m = mm
    if box is None and m.any():              # keep the densest red band (the irises), drop lips/blush strays
        rows = np.convolve(m.sum(1).astype(float), np.ones(15), "same")
        peak = int(rows.argmax())
        band = np.zeros_like(m)
        half = max(12, int(0.035 * m.shape[0]))
        band[max(0, peak - half):peak + half] = True
        m = m & band
    ys, xs = np.nonzero(m)
    if len(xs) < 20:
        return None
    pts = np.stack([xs, ys], 1).astype(float)
    c = np.array([pts[pts[:, 0].argmin()], pts[pts[:, 0].argmax()]])
    for _ in range(30):                      # 2-means on the red pixels
        k = np.argmin(((pts[:, None, :] - c[None]) ** 2).sum(-1), 1)
        c = np.array([pts[k == j].mean(0) if (k == j).any() else c[j] for j in (0, 1)])
    pts = sorted([tuple(c[0]), tuple(c[1])])
    return pts


def fit_to(ours: Image.Image, oe, re, size):
    """similarity transform putting our eye points oe onto the reference eye points re; output = ref size"""
    (ox0, oy0), (ox1, oy1) = oe
    (rx0, ry0), (rx1, ry1) = re
    so = np.hypot(ox1 - ox0, oy1 - oy0)
    sr = np.hypot(rx1 - rx0, ry1 - ry0)
    s = sr / so
    big = ours.resize((round(ours.width * s), round(ours.height * s)), Image.LANCZOS)
    omx, omy = (ox0 + ox1) / 2 * s, (oy0 + oy1) / 2 * s
    rmx, rmy = (rx0 + rx1) / 2, (ry0 + ry1) / 2
    canvas = Image.new("RGB", size, (46, 46, 46))
    canvas.paste(big, (round(rmx - omx), round(rmy - omy)))
    return canvas


def label(im, text):
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, im.width, 22], fill=(0, 0, 0))
    d.text((6, 5), text, fill=(255, 255, 255))
    return im


def pair(ref_name, ours_name, title, ref_eyes=None, ref_box=None):
    ref = Image.open(REFS / ref_name).convert("RGB")
    ours = Image.open(CAP / ours_name).convert("RGB")
    re = ref_eyes or red_eyes(ref, ref_box)
    oe = red_eyes(ours, gr=3.0)   # stricter: the pink lips must not count
    if re is None or oe is None:
        raise RuntimeError(f"eye detection failed: {ref_name} {re} / {ours_name} {oe}")
    fitted = fit_to(ours, oe, re, ref.size)
    s = H / ref.height
    a = label(ref.resize((round(ref.width * s), H)), f"HER: {ref_name}")
    b = label(fitted.resize((round(ref.width * s), H)), f"OURS: {ours_name} (eyes aligned)")
    sheet = Image.new("RGB", (a.width + b.width + 8, H + 30), (20, 20, 20))
    sheet.paste(a, (0, 30))
    sheet.paste(b, (a.width + 8, 30))
    ImageDraw.Draw(sheet).text((6, 8), f"PRIVATE / DO NOT SHIP  -  {title}", fill=(255, 200, 80))
    return sheet, {"ref_eyes": re, "our_eyes": oe}


def main():
    SHEETS.mkdir(parents=True, exist_ok=True)
    info = {}
    jobs = [("front_full", "reference1.jpg", "hy_Bust_Front.png", "front (ref1 full head)", [(202.0, 227.5), (262.5, 229.5)], None),
            ("front_close", "reference2.jpg", "hy_Face_Close.png", "front close-up (ref2)", None, (40, 220, 300, 290)),
            ("tq_a", "reference3.jpg", "hy_Face_TQ_L_High.png", "three-quarter (ref3)", None, (80, 150, 420, 280)),
            ("tq_b", "reference4.jpg", "hy_Face_TQ_L_High.png", "three-quarter (ref4)", None, (80, 180, 440, 330))]
    for key, rn, on, title, re, box in jobs:
        try:
            sh, inf = pair(rn, on, title, re, box)
            sh.save(SHEETS / f"{key}.png")
            info[key] = inf
            print(key, inf)
        except Exception as exc:  # noqa: BLE001
            print(key, "FAILED", exc)
    # side view: no side reference exists -> ours only, next to her full-head front for context
    side = [p for p in ("hy_Face_Profile_L.png", "hy_Face_Profile_R.png") if (CAP / p).is_file()]
    if side:
        ims = [label(Image.open(REFS / "reference1.jpg").convert("RGB").resize((480, H)), "HER: reference1 (no side view exists)")]
        for p in side:
            im = Image.open(CAP / p).convert("RGB")
            ims.append(label(im.resize((round(im.width * H / im.height), H)), f"OURS: {p}"))
        w = sum(i.width for i in ims) + 8 * (len(ims) - 1)
        sh = Image.new("RGB", (w, H + 30), (20, 20, 20))
        x = 0
        for i in ims:
            sh.paste(i, (x, 30))
            x += i.width + 8
        ImageDraw.Draw(sh).text((6, 8), "PRIVATE / DO NOT SHIP  -  side (no reference side view)", fill=(255, 200, 80))
        sh.save(SHEETS / "side.png")


if __name__ == "__main__":
    main()
