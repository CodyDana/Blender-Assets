"""Lay the hall review renders out like the reference sheets and make the reference | ours comparisons.

  sheet_hall.png        like References/Dojo/dojo_hall_front_ref.png: front and side elevations with exact 1.8 m
                        silhouettes (scale from views.json), top view, the 2 m bay close-up, the 3/4 view
  sheet_roof.png        like the panels a-f of dojo_roof_details_ref.png (silhouette beside the ridge view)
  sheet_closeups.png    the key close-ups
  cmp_*.png             reference crop | ours pairs (same height) for every panel / view; the main sheet pairs are also
                        made with Scripts/armory/side_by_side.py (see BUILD_NOTES)
  numbers_<tag>.json    plaster / timber / tile medians (sRGB) in matched regions of the sheet and the reference

Run (system Python with Pillow): py Scripts/dojo/hall/compose_hall.py <tag>
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
TAG = sys.argv[1] if len(sys.argv) > 1 else "r0"
D = (ROOT / "WorkFiles" / "dojo" / "build" / "hall" / "renders" / TAG).resolve()
REF = ROOT / "References" / "Dojo"
V = json.loads((D / "views.json").read_text(encoding="utf-8")) if (D / "views.json").exists() else {}
SIL = (108, 108, 108, 255)

_R = [(0.0, 1.80), (0.045, 1.795), (0.080, 1.77), (0.100, 1.72), (0.104, 1.67), (0.095, 1.62), (0.070, 1.585),
      (0.058, 1.555), (0.130, 1.525), (0.200, 1.49), (0.232, 1.44), (0.245, 1.30), (0.255, 1.12), (0.258, 0.95),
      (0.250, 0.84), (0.225, 0.80), (0.205, 0.83), (0.200, 0.96), (0.185, 1.20), (0.180, 1.02), (0.170, 0.90),
      (0.165, 0.60), (0.150, 0.30), (0.145, 0.08), (0.165, 0.02), (0.160, 0.0), (0.035, 0.0), (0.040, 0.08),
      (0.050, 0.45), (0.030, 0.82), (0.0, 0.86)]
FRONT = _R + [(-x, z) for (x, z) in reversed(_R[:-1])]


def ref_bg(name):
    im = Image.open(REF / name).convert("RGB")
    return im.getpixel((4, 4)) + (255,)


def load(name):
    return Image.open(D / f"{name}.png").convert("RGBA")


def exists(name):
    return (D / f"{name}.png").exists()


def model_bbox(im, thr=200):
    return im.getchannel("A").point(lambda v: 255 if v >= thr else 0).getbbox()


def draw_figure(canvas, x_px, ground_y, ppm):
    d = ImageDraw.Draw(canvas)
    d.polygon([(x_px + x * ppm, ground_y - z * ppm) for (x, z) in FRONT], fill=SIL)


def paste_ortho(canvas, name, ppm_target, left_px, ground_y):
    v = V[name]
    im = load(name)
    f = ppm_target / v["ppm"]
    im = im.resize((max(1, round(im.width * f)), max(1, round(im.height * f))), Image.LANCZOS)
    bb = model_bbox(im)
    g_row = im.height / 2 + v["centre"][2] * ppm_target
    im = im.crop(bb)
    canvas.alpha_composite(im, (int(left_px), int(round(ground_y - (g_row - bb[1])))))
    return im.width


def paste_fit(canvas, name, box, margin=0.04, crop_alpha=True):
    im = load(name)
    if crop_alpha and im.getchannel("A").getextrema()[0] < 255:
        bb = model_bbox(im, 30)
        mx, my = int((bb[2] - bb[0]) * margin), int((bb[3] - bb[1]) * margin)
        im = im.crop((max(0, bb[0] - mx), max(0, bb[1] - my), min(im.width, bb[2] + mx), min(im.height, bb[3] + my)))
    x0, y0, x1, y1 = box
    f = min((x1 - x0) / im.width, (y1 - y0) / im.height)
    im = im.resize((max(1, round(im.width * f)), max(1, round(im.height * f))), Image.LANCZOS)
    canvas.alpha_composite(im, (int(x0 + ((x1 - x0) - im.width) // 2), int(y0 + ((y1 - y0) - im.height) // 2)))


def paste_cover(canvas, name, box):
    """Fill the box (crop the render's centre to the box aspect)."""
    im = load(name)
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    f = max(bw / im.width, bh / im.height)
    im = im.resize((max(1, round(im.width * f)), max(1, round(im.height * f))), Image.LANCZOS)
    cx, cy = (im.width - bw) // 2, (im.height - bh) // 2
    canvas.alpha_composite(im.crop((cx, cy, cx + bw, cy + bh)), (x0, y0))


def hall_sheet():
    bg = ref_bg("dojo_hall_front_ref.png")
    c = Image.new("RGBA", (1448, 1086), bg)
    ppm = 33.0
    gy = 474
    draw_figure(c, 40, gy, ppm)
    paste_ortho(c, "hall_front", ppm, 70, gy)
    draw_figure(c, 962, gy, ppm)
    paste_ortho(c, "hall_side", ppm, 980, gy)
    paste_fit(c, "hall_top", (20, 520, 720, 1030), margin=0.01)
    paste_cover(c, "hall_bay", (745, 527, 1003, 1027))
    paste_fit(c, "hall_34", (1005, 640, 1440, 960), margin=0.01)
    c.convert("RGB").save(D / "sheet_hall.png")
    print("saved", D / "sheet_hall.png")


ROOF_PANELS = [   # our render, reference box (dojo_roof_details_ref.png)
    ("roof_a1_tilefield", (20, 445, 328, 655)), ("roof_a2_eavecorner", (345, 445, 702, 655)),
    ("roof_b1_ridge", (729, 465, 1127, 652)), ("roof_b2_ridgeend", (1249, 465, 1432, 652)),
    ("roof_c1_hip", (20, 670, 350, 855)), ("roof_c2_hipcorner", (362, 670, 702, 855)),
    ("roof_d1_gable", (724, 670, 1117, 855)), ("roof_d2_gable34", (1122, 670, 1432, 855)),
    ("roof_e1_verge", (20, 870, 407, 1077)), ("roof_e2_verge34", (417, 870, 702, 1077)),
    ("roof_f1_gutter", (724, 870, 1084, 1072)), ("roof_f2_gutter34", (1117, 870, 1432, 1072))]


def roof_sheet():
    bg = ref_bg("dojo_roof_details_ref.png")
    c = Image.new("RGBA", (1448, 650), (205, 205, 205, 255))
    for name, (x0, y0, x1, y1) in ROOF_PANELS:
        if exists(name):
            paste_cover(c, name, (x0, y0 - 435, x1, y1 - 435))
    # the 1.8 m silhouette beside the ridge view (the reference's scale bar slot), scaled from panel b1's camera
    draw_figure(c, 1188, 212, 95.0)
    d = ImageDraw.Draw(c)
    d.line([(1152, 43), (1152, 212)], fill=(90, 90, 90, 255), width=2)
    _ = bg
    c.convert("RGB").save(D / "sheet_roof.png")
    print("saved", D / "sheet_roof.png")


def pair(ref_img, ours, out, h=700):
    a = ref_img.convert("RGB")
    b = ours.convert("RGB")
    a = a.resize((round(a.width * h / a.height), h), Image.LANCZOS)
    b = b.resize((round(b.width * h / b.height), h), Image.LANCZOS)
    c = Image.new("RGB", (a.width + b.width + 24, h), (255, 255, 255))
    c.paste(a, (0, 0))
    c.paste(b, (a.width + 24, 0))
    c.save(out)
    return out


def comparisons():
    rh = Image.open(REF / "dojo_hall_front_ref.png")
    rr = Image.open(REF / "dojo_roof_details_ref.png")
    out = []
    if (D / "sheet_hall.png").exists():
        sh = Image.open(D / "sheet_hall.png")
        boxes = {"front": (20, 40, 960, 485), "side": (985, 40, 1440, 485), "top": (20, 520, 720, 1030),
                 "bay": (745, 527, 1003, 1027), "34": (1000, 640, 1440, 960)}
        for k, b in boxes.items():
            out.append(pair(rh.crop(b), sh.crop(b), D / f"cmp_hall_{k}.png", h=600 if k != "front" else 500))
    for name, box in ROOF_PANELS:
        if exists(name):
            out.append(pair(rr.crop(box), load(name), D / f"cmp_{name}.png", h=420))
    if exists("context_establishing_ref2"):
        out.append(pair(Image.open(REF / "dojo1_reference2.png"), load("context_establishing_ref2"),
                        D / "cmp_establishing.png", h=700))
    if exists("context_ref2_elevated"):
        out.append(pair(Image.open(REF / "dojo1_reference2.png"), load("context_ref2_elevated"),
                        D / "cmp_ref2_elevated.png", h=700))
    if exists("context_from_courtyard"):
        out.append(pair(Image.open(REF / "dojo1_reference2.png"), load("context_from_courtyard"),
                        D / "cmp_courtyard.png", h=700))
    # one overview grid of all roof panel pairs
    ims = [Image.open(D / f"cmp_{n}.png") for n, _ in ROOF_PANELS if (D / f"cmp_{n}.png").exists()]
    if ims:
        w = max(i.width for i in ims)
        g = Image.new("RGB", (w * 2 + 20, (420 + 20) * ((len(ims) + 1) // 2)), (255, 255, 255))
        for k, im in enumerate(ims):
            g.paste(im, ((k % 2) * (w + 20), (k // 2) * 440))
        g.save(D / "cmp_roof_all.png")
    print("comparisons", len(out))


def closeup_sheet():
    names = ["close_eave_landing_route4", "close_ac_zone_route5", "close_downpipe_corner", "close_stair_band",
             "close_gable_verge", "close_veranda_side", "close_recess_frieze", "close_chidori_side",
             "close_ridge_diagonal", "close_upper_soffit", "close_door_head", "close_deck_wall", "close_recess_corner"]
    names = [n for n in names if exists(n)]
    if not names:
        return
    c = Image.new("RGBA", (1800, 400 * ((len(names) + 2) // 3)), (40, 40, 40, 255))
    for k, n in enumerate(names):
        paste_cover(c, n, ((k % 3) * 600, (k // 3) * 400, (k % 3) * 600 + 596, (k // 3) * 400 + 396))
    c.convert("RGB").save(D / "sheet_closeups.png")


def medians():
    """sRGB medians of matched regions (whole-view medians of the plaster / tile-ish pixels are not meaningful across
    two different renders; these boxes are hand-matched on the elevations: a plaster panel, a lower board panel, the
    lower roof tiles)."""
    import statistics
    res = {}
    if not (D / "sheet_hall.png").exists():
        return
    ours = Image.open(D / "sheet_hall.png").convert("RGB")
    ref = Image.open(REF / "dojo_hall_front_ref.png").convert("RGB")

    def med(im, box):
        px = list(im.crop(box).getdata())
        return [round(statistics.median(p[i] for p in px)) for i in range(3)]
    res["ref"] = {"plaster": med(ref, (250, 330, 275, 360)), "boards": med(ref, (250, 386, 275, 405)),
                  "tiles_lower": med(ref, (300, 250, 500, 280)), "tiles_upper": med(ref, (350, 110, 700, 150))}
    js = D / "sample_boxes.json"
    if js.exists():
        boxes = json.loads(js.read_text())
        res["ours"] = {k: med(ours, tuple(v)) for k, v in boxes.items()}
    (D / f"numbers_{TAG}.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res))


if exists("hall_front"):
    hall_sheet()
if any(exists(n) for n, _ in ROOF_PANELS):
    roof_sheet()
closeup_sheet()
comparisons()
medians()
