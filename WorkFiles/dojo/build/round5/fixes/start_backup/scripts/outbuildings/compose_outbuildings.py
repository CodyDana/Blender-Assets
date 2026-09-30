"""Lay the storehouse / residence review renders out like References/Dojo/dojo_outbuildings_ref.png and make the
reference | ours inputs for Scripts/armory/side_by_side.py.

  sheet_outbuildings.png   top row: storehouse front + gable | residence front + gable (ortho, one scale, exact 1.8 m
                           silhouettes from views.json); bottom row: top views and 3/4 views; the reference's grey
  sbs_in/ref_*.png, ours_*.png   matching crops (the reference's views, our views) for side_by_side.py
  sheet_closeups.png       the key close-ups in a grid
  numbers.json             plaster / granite / timber / tile medians (sRGB) in matched regions (ours: masks from the
                           piece views; reference: fixed boxes on the sheet's elevations)

Run (system Python with Pillow): py -3 Scripts/dojo/outbuildings/compose_outbuildings.py <tag>
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
TAG = sys.argv[1] if len(sys.argv) > 1 else "r0"
D = (ROOT / "WorkFiles" / "dojo" / "build" / "outbuildings" / "renders" / TAG).resolve()
REFP = ROOT / "References" / "Dojo" / "dojo_outbuildings_ref.png"
V = json.loads((D / "views.json").read_text(encoding="utf-8"))
SIL = (70, 70, 72, 255)
# the hall compose's 1.8 m figure (Scripts/dojo/hall/compose_hall.py), half outline, metres
_R = [(0.0, 1.80), (0.045, 1.795), (0.080, 1.77), (0.100, 1.72), (0.104, 1.67), (0.095, 1.62), (0.070, 1.585),
      (0.058, 1.555), (0.130, 1.525), (0.200, 1.49), (0.232, 1.44), (0.245, 1.30), (0.255, 1.12), (0.258, 0.95),
      (0.250, 0.84), (0.225, 0.80), (0.205, 0.83), (0.200, 0.96), (0.185, 1.20), (0.180, 1.02), (0.170, 0.90),
      (0.165, 0.60), (0.150, 0.30), (0.145, 0.08), (0.165, 0.02), (0.160, 0.0), (0.035, 0.0), (0.040, 0.08),
      (0.050, 0.45), (0.030, 0.82), (0.0, 0.86)]
FRONT = _R + [(-x, z) for (x, z) in reversed(_R[:-1])]


def load(name):
    return Image.open(D / f"{name}.png").convert("RGBA")


def bbox(im, thr=200):
    return im.getchannel("A").point(lambda v: 255 if v >= thr else 0).getbbox()


def figure(canvas, x_px, ground_y, ppm):
    ImageDraw.Draw(canvas).polygon([(x_px + x * ppm, ground_y - z * ppm) for (x, z) in FRONT], fill=SIL)


def paste_ortho(canvas, name, ppm, left, ground_y):
    v = V[name]
    im = load(name)
    f = ppm / v["ppm"]
    im = im.resize((max(1, round(im.width * f)), max(1, round(im.height * f))), Image.LANCZOS)
    b = bbox(im)
    g_row = im.height / 2 + v["centre"][2] * ppm      # ground (z 0) row in the resized render
    im = im.crop(b)
    canvas.alpha_composite(im, (int(left), int(round(ground_y - (g_row - b[1])))))
    return im.width


def paste_fit(canvas, name, box, margin=0.03):
    im = load(name)
    if im.getchannel("A").getextrema()[0] < 255:
        b = bbox(im, 200)             # the object, not the shadow catcher's soft square
        mx, my = int((b[2] - b[0]) * margin), int((b[3] - b[1]) * margin)
        im = im.crop((max(0, b[0] - mx), max(0, b[1] - my), min(im.width, b[2] + mx), min(im.height, b[3] + my)))
    x0, y0, x1, y1 = box
    f = min((x1 - x0) / im.width, (y1 - y0) / im.height)
    im = im.resize((max(1, round(im.width * f)), max(1, round(im.height * f))), Image.LANCZOS)
    canvas.alpha_composite(im, (int(x0 + ((x1 - x0) - im.width) // 2), int(y0 + ((y1 - y0) - im.height) // 2)))


ref = Image.open(REFP).convert("RGB")
bg = ref.getpixel((6, 6)) + (255,)
W, H = 2896, 2172                  # 2 x the reference sheet
sheet = Image.new("RGBA", (W, H), bg)
ppm = 68.0                          # px per m for the elevations (4 elevations across the 2896 px sheet)
ground = 820
x = 60
for bld in ("store", "res"):
    figure(sheet, x + 25, ground, ppm)
    x += 70
    wf = paste_ortho(sheet, f"{bld}_front", ppm, x, ground)
    x += wf + 40
    ws = paste_ortho(sheet, f"{bld}_side", ppm, x, ground)
    x += ws + (110 if bld == "store" else 0)
    if bld == "store":
        ImageDraw.Draw(sheet).line([(x - 55, 60), (x - 55, H - 60)], fill=(120, 120, 124, 255), width=3)
for i, bld in enumerate(("store", "res")):
    x0 = 60 + i * (W // 2)
    paste_fit(sheet, f"{bld}_top", (x0, 1000, x0 + 620, 2120))
    paste_fit(sheet, f"{bld}_34", (x0 + 640, 1080, x0 + W // 2 - 80, 2060))
sheet.convert("RGB").save(D / "sheet_outbuildings.png")
print("saved", D / "sheet_outbuildings.png")

# reference | ours inputs (same crops as refcrops/ of the build folder)
sb = D / "sbs_in"
sb.mkdir(exist_ok=True)
crops = {"store_front": (0, 80, 400, 430), "store_side": (400, 100, 700, 430), "res_front": (740, 80, 1140, 430),
         "res_side": (1140, 100, 1440, 430), "store_top": (0, 470, 340, 930), "store_34": (330, 540, 720, 900),
         "res_top": (750, 470, 1070, 930), "res_34": (1050, 540, 1448, 900)}
for k, b in crops.items():
    ref.crop(b).save(sb / f"ref_{k}.png")
    im = load(k)
    flat = Image.new("RGBA", im.size, bg)
    flat.alpha_composite(im)
    bb = bbox(im, 30)
    m = 40
    flat.crop((max(0, bb[0] - m), max(0, bb[1] - m), min(im.width, bb[2] + m), min(im.height, bb[3] + m))) \
        .convert("RGB").save(sb / f"ours_{k}.png")
ref.save(sb / "ref_sheet.png")
Image.open(D / "sheet_outbuildings.png").save(sb / "ours_sheet.png")

# close-ups grid
names = sorted(p.stem for p in D.glob("close_*.png"))
if names:
    cw, chh, cols = 900, 600, 3
    rows = (len(names) + cols - 1) // cols
    grid = Image.new("RGBA", (cols * cw + (cols + 1) * 20, rows * chh + (rows + 1) * 20), bg)
    for i, n in enumerate(names):
        r, c = divmod(i, cols)
        paste_fit(grid, n, (20 + c * (cw + 20), 20 + r * (chh + 20), 20 + c * (cw + 20) + cw, 20 + r * (chh + 20) + chh),
                  margin=0.0)
    grid.convert("RGB").save(D / "sheet_closeups.png")
    print("saved", D / "sheet_closeups.png")


# medians (sRGB) in matched regions: reference boxes on its elevations (1x coordinates), ours = same relative boxes on
# the ortho renders, located by their metric position
def median(im, box):
    px = list(im.crop(box).convert("RGB").getdata())
    if not px:
        return None
    return [sorted(c[i] for c in px)[len(px) // 2] for i in range(3)]


num = {"reference": {"store_plaster": median(ref, (70, 170, 120, 250)), "store_granite": median(ref, (65, 370, 150, 410)),
                     "res_plaster": median(ref, (1195, 150, 1370, 230)), "res_boards": median(ref, (1195, 365, 1370, 400)),
                     "tiles": median(ref, (60, 520, 150, 700))}}


def ours_box(name, x0m, x1m, z0m, z1m):
    v = V[name]
    im = load(name)
    ppm_ = v["ppm"]
    cx = im.width / 2
    gz = im.height / 2 + v["centre"][2] * ppm_
    return median(im, (int(cx + x0m * ppm_), int(gz - z1m * ppm_), int(cx + x1m * ppm_), int(gz - z0m * ppm_)))


num["ours"] = {"store_plaster": ours_box("store_side", -2.5, 2.5, 1.3, 2.9),
               "store_granite": ours_box("store_side", -2.5, 2.5, 0.1, 0.9),
               "res_plaster": ours_box("res_side", -2.5, 2.5, 1.3, 2.9),
               "res_boards": ours_box("res_side", -2.5, 2.5, 0.4, 0.85),
               "tiles": median(load("store_top"), (200, 150, 900, 450))}
(D / "numbers.json").write_text(json.dumps(num, indent=1), encoding="utf-8")
print(json.dumps(num))
