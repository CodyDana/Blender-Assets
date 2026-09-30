"""Lay the KIT 1 review renders out as model sheets like the reference sheets (References/Dojo/dojo_wall_ref.png and
dojo_gatehouse_ref.png, 1448 x 1086, plain light grey), with plain grey 1.8 m silhouettes beside the front and side
elevations. The ortho views' scale comes from views.json (render_kit1.py), so the silhouettes are exactly 1.8 m.

Run (system Python with Pillow): py Scripts/dojo/compose_kit1.py <tag>
Out: WorkFiles/dojo/build/renders/kit1/<tag>/sheet_wall.png, sheet_gate.png, sheet_wall_variants.png
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
TAG = sys.argv[1] if len(sys.argv) > 1 else "r1"
D = (ROOT / "WorkFiles" / "dojo" / "build" / "renders" / "kit1" / TAG).resolve()
V = json.loads((D / "views.json").read_text(encoding="utf-8"))
BG = (160, 160, 160, 255)          # the reference sheets' background (#A0A0A0, measured)
SIL = (108, 108, 108, 255)

# a standing figure, 1.80 m, front view (x, z) in metres (right half; mirrored)
_R = [(0.0, 1.80), (0.045, 1.795), (0.080, 1.77), (0.100, 1.72), (0.104, 1.67), (0.095, 1.62), (0.070, 1.585),
      (0.058, 1.555), (0.130, 1.525), (0.200, 1.49), (0.232, 1.44), (0.245, 1.30), (0.255, 1.12), (0.258, 0.95),
      (0.250, 0.84), (0.225, 0.80), (0.205, 0.83), (0.200, 0.96), (0.185, 1.20), (0.180, 1.02), (0.170, 0.90),
      (0.165, 0.60), (0.150, 0.30), (0.145, 0.08), (0.165, 0.02), (0.160, 0.0), (0.035, 0.0), (0.040, 0.08),
      (0.050, 0.45), (0.030, 0.82), (0.0, 0.86)]
FRONT = _R + [(-x, z) for (x, z) in reversed(_R[:-1])]
# side (profile) view, facing +x
SIDE = [(0.02, 1.80), (0.075, 1.78), (0.105, 1.73), (0.115, 1.68), (0.125, 1.655), (0.110, 1.64), (0.108, 1.60),
        (0.080, 1.575), (0.055, 1.56), (0.085, 1.50), (0.110, 1.40), (0.115, 1.25), (0.095, 1.05), (0.085, 0.95),
        (0.095, 0.60), (0.085, 0.10), (0.200, 0.03), (0.200, 0.0), (0.030, 0.0), (0.020, 0.08), (-0.040, 0.10),
        (-0.050, 0.45), (-0.065, 0.95), (-0.090, 1.05), (-0.100, 1.25), (-0.105, 1.40), (-0.080, 1.52), (-0.060, 1.56),
        (-0.075, 1.63), (-0.080, 1.70), (-0.060, 1.76)]


def load(name):
    return Image.open(D / f"{name}.png").convert("RGBA")


def model_bbox(im, thr=200):
    """Bounding box of the opaque model (ignores faint shadow-catcher pixels)."""
    a = im.getchannel("A").point(lambda v: 255 if v >= thr else 0)
    return a.getbbox()


def draw_figure(canvas, poly, x_px, ground_y, ppm):
    d = ImageDraw.Draw(canvas)
    d.polygon([(x_px + x * ppm, ground_y - z * ppm) for (x, z) in poly], fill=SIL)


def paste_ortho(canvas, name, ppm_target, left_px, ground_y, crop_m=None):
    """Scale an ortho render so 1 m = ppm_target px, paste it with its ground line at ground_y and the world point
    at the view's left crop edge at left_px. crop_m = (x0, x1) in view metres from the view centre (optional)."""
    v = V[name]
    im = load(name)
    f = ppm_target / v["ppm"]
    im = im.resize((max(1, round(im.width * f)), max(1, round(im.height * f))), Image.LANCZOS)
    bb = model_bbox(im)
    zc = v["centre"][2]
    g_row = im.height / 2 + zc * ppm_target            # the row of z = 0 in the scaled render (horizontal views)
    if bb is None:
        return None
    im = im.crop(bb)
    canvas.alpha_composite(im, (int(left_px), int(round(ground_y - (g_row - bb[1])))))
    return (left_px, left_px + im.width)


def paste_fit(canvas, name, box, anchor="center", margin=0.10):
    im = load(name)
    bb = model_bbox(im)
    mx, my = int((bb[2] - bb[0]) * margin), int((bb[3] - bb[1]) * margin)
    bb = (max(0, bb[0] - mx), max(0, bb[1] - my), min(im.width, bb[2] + mx), min(im.height, bb[3] + my))
    im = im.crop(bb)
    x0, y0, x1, y1 = box
    f = min((x1 - x0) / im.width, (y1 - y0) / im.height)
    im = im.resize((max(1, round(im.width * f)), max(1, round(im.height * f))), Image.LANCZOS)
    x = x0 + ((x1 - x0) - im.width) // 2
    y = y0 + ((y1 - y0) - im.height) // 2 if anchor == "center" else y1 - im.height
    canvas.alpha_composite(im, (int(x), int(y)))


def paste_top(canvas, name, ppm_target, left_px, top_px):
    """Paste a plan view at 1 m = ppm_target px; returns a world (x, y) -> canvas px function."""
    v = V[name]
    im = load(name)
    f = ppm_target / v["ppm"]
    im = im.resize((max(1, round(im.width * f)), max(1, round(im.height * f))), Image.LANCZOS)
    bb = model_bbox(im, 60)
    im = im.crop(bb)
    canvas.alpha_composite(im, (int(left_px), int(top_px)))
    cx, cy = v["centre"][0], v["centre"][1]
    W, H = round(v["w"] * f), round(v["h"] * f)

    def to_px(x, y):
        return (left_px - bb[0] + W / 2 + (x - cx) * ppm_target, top_px - bb[1] + H / 2 - (y - cy) * ppm_target)
    return to_px


def wall_sheet():
    c = Image.new("RGBA", (1448, 1086), BG)
    ppm = 118.0
    gy = 330
    draw_figure(c, FRONT, 60, gy, ppm)
    paste_ortho(c, "wall_front", ppm, 120, gy)
    draw_figure(c, SIDE, 745, gy, ppm)
    paste_ortho(c, "wall_side", ppm, 790, gy)
    paste_fit(c, "corner_elev", (1030, 30, 1440, gy + 6), anchor="bottom")
    paste_top(c, "wall_top", ppm, 110, 372)
    paste_top(c, "corner_top", ppm * 0.78, 760, 360)
    # f1: the section cut takes the middle-right slot; the bottom-right slot holds the sheet's freestanding
    # timber-framed pier (SM_DK_Wall_FramePier), as on the reference
    paste_fit(c, "wall_section", (1030, 345, 1440, 650))
    paste_fit(c, "wall_34", (0, 600, 560, 1080))
    paste_fit(c, "corner_34_out", (560, 640, 1010, 1080))
    paste_fit(c, "frame_pier", (1060, 650, 1440, 1080), anchor="bottom")
    c.convert("RGB").save(D / "sheet_wall.png")
    print("saved", D / "sheet_wall.png")


def variants_sheet():
    im = load("wall_variants")
    c = Image.new("RGBA", (im.width + 160, im.height + 40), BG)
    v = V["wall_variants"]
    ppm = v["ppm"]
    gy = 20 + im.height / 2 + v["centre"][2] * ppm
    c.alpha_composite(im, (140, 20))
    draw_figure(c, FRONT, 70, gy, ppm)
    c.convert("RGB").save(D / "sheet_wall_variants.png")
    print("saved", D / "sheet_wall_variants.png")


def gate_sheet():
    c = Image.new("RGBA", (1448, 1086), BG)
    ppm = 66.0
    gy = 470
    draw_figure(c, FRONT, 40, gy, ppm)
    paste_ortho(c, "gate_front", ppm, 75, gy)
    draw_figure(c, SIDE, 1085, gy, ppm)
    paste_ortho(c, "gate_side", ppm, 1100, gy)
    # f2: the reference's bottom-left view is an oblique top view (roof on, doors open under it): ours is the same,
    # an orthographic view from above the street at 55 deg
    paste_fit(c, "gate_top_oblique", (10, 530, 860, 1080), margin=0.04)
    paste_fit(c, "gate_34", (860, 520, 1448, 1080))
    c.convert("RGB").save(D / "sheet_gate.png")
    print("saved", D / "sheet_gate.png")


REF = ROOT / "References" / "Dojo"
# r2: per-piece pairs for Scripts/armory/side_by_side.py: the reference sheet's view (crop box in its 1448 x 1086 px)
# against our matching render, flattened onto the sheets' grey
PAIRS = [
    ("wall_front", "dojo_wall_ref.png", (100, 90, 625, 350), "wall_front"),
    ("wall_end", "dojo_wall_ref.png", (635, 90, 765, 350), "wall_side"),
    ("wall_top", "dojo_wall_ref.png", (90, 405, 730, 565), "wall_top"),
    ("wall_corner", "dojo_wall_ref.png", (850, 90, 1260, 365), "corner_elev"),
    ("wall_corner_top", "dojo_wall_ref.png", (840, 390, 1315, 690), "corner_top"),
    ("wall_34", "dojo_wall_ref.png", (35, 605, 665, 1035), "wall_34"),
    ("wall_corner_34", "dojo_wall_ref.png", (685, 680, 1095, 1035), "corner_34_out"),
    ("wall_end_34", "dojo_wall_ref.png", (1275, 90, 1425, 350), "wall_end_34"),
    ("wall_footing", "dojo_wall_ref.png", (110, 262, 615, 342), "close_footing"),
    ("wall_frame_pier", "dojo_wall_ref.png", (1155, 620, 1435, 1040), "frame_pier"),
    ("gate_front", "dojo_gatehouse_ref.png", (15, 40, 1040, 525), "gate_front"),
    ("gate_side", "dojo_gatehouse_ref.png", (1055, 20, 1445, 525), "gate_side"),
    ("gate_top", "dojo_gatehouse_ref.png", (20, 595, 855, 1005), "gate_top_oblique"),
    ("gate_34", "dojo_gatehouse_ref.png", (860, 570, 1445, 1065), "gate_34"),
    ("gate_doors", "dojo_gatehouse_ref.png", (360, 215, 740, 500), "gate_doors_close"),
    ("gate_ridge_end", "dojo_gatehouse_ref.png", (200, 45, 430, 235), "close_gate_ridge_end"),
    ("gate_junction", "dojo_gatehouse_ref.png", (170, 200, 420, 520), "close_gate_junction"),
]


def pair_sources():
    out = D / "sbs_src"
    out.mkdir(exist_ok=True)
    made = []
    for key, ref, box, ours in PAIRS:
        if not (D / f"{ours}.png").exists():
            continue
        Image.open(REF / ref).convert("RGB").crop(box).save(out / f"ref_{key}.png")
        im = load(ours)
        bb = model_bbox(im, 30) or (0, 0, im.width, im.height)
        m = int(0.04 * max(bb[2] - bb[0], bb[3] - bb[1]))
        bb = (max(0, bb[0] - m), max(0, bb[1] - m), min(im.width, bb[2] + m), min(im.height, bb[3] + m))
        flat = Image.new("RGBA", im.size, BG)
        flat.alpha_composite(im)
        flat.convert("RGB").crop(bb).save(out / f"ours_{key}.png")
        made.append(key)
    (out / "pairs.txt").write_text(chr(10).join(made), encoding="utf-8")
    print("pair sources", made)


if (D / "wall_front.png").exists():
    wall_sheet()
if (D / "wall_variants.png").exists():
    variants_sheet()
if (D / "gate_front.png").exists():
    gate_sheet()
pair_sources()
