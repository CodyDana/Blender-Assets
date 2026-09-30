"""Lay the corridor review renders out like References/Dojo/dojo_corridor_ref.png and cut the matching reference | ours
panel pairs for Scripts/armory/side_by_side.py.

  sheet_corridor.png   the sheet's layout (1448 x 1086, its grey): the closed side (top, 75 px/m, ground row 352), the
                       open side (middle, 75 px/m, ground row 705) with exact 1.8 m silhouettes, the end view, the top
                       view, the 3/4 view
  pair_<panel>_ref.png / pair_<panel>_ours.png   matching crops (closed, open, end, top, 34) for side_by_side.py
Run (system Python with Pillow): py Scripts/dojo/corridors/compose_corridors.py <tag>
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
TAG = sys.argv[1] if len(sys.argv) > 1 else "r0"
D = (ROOT / "WorkFiles" / "dojo" / "build" / "corridors" / "renders" / TAG).resolve()
REF = ROOT / "References" / "Dojo" / "dojo_corridor_ref.png"
V = json.loads((D / "views.json").read_text(encoding="utf-8"))
SIL = (108, 108, 108, 255)
PPM = 75.0
# the hall compose's 1.8 m front silhouette (Scripts/dojo/hall/compose_hall.py), metres
_R = [(0.0, 1.80), (0.045, 1.795), (0.080, 1.77), (0.100, 1.72), (0.104, 1.67), (0.095, 1.62), (0.070, 1.585),
      (0.058, 1.555), (0.130, 1.525), (0.200, 1.49), (0.232, 1.44), (0.245, 1.30), (0.255, 1.12), (0.258, 0.95),
      (0.250, 0.84), (0.225, 0.80), (0.205, 0.83), (0.200, 0.96), (0.185, 1.20), (0.180, 1.02), (0.170, 0.90),
      (0.165, 0.60), (0.150, 0.30), (0.145, 0.08), (0.165, 0.02), (0.160, 0.0), (0.035, 0.0), (0.040, 0.08),
      (0.050, 0.45), (0.030, 0.82), (0.0, 0.86)]
FRONT = _R + [(-x, z) for (x, z) in reversed(_R[:-1])]
# the reference sheet's panels (px boxes in dojo_corridor_ref.png)
PANELS = {"closed": (0, 0, 1115, 370), "open": (40, 385, 1040, 718), "end": (1160, 388, 1402, 713),
          "top": (20, 740, 885, 1086), "34": (900, 740, 1426, 1086)}


def draw_figure(canvas, x_px, ground_y, ppm):
    d = ImageDraw.Draw(canvas)
    d.polygon([(x_px + x * ppm, ground_y - z * ppm) for (x, z) in FRONT], fill=SIL)


def load(name):
    return Image.open(D / f"{name}.png").convert("RGBA")


def paste_elev(canvas, name, ppm, left_px, ground_y):
    v = V[name]
    im = load(name)
    f = ppm / v["ppm"]
    if abs(f - 1.0) > 1e-6:
        im = im.resize((round(im.width * f), round(im.height * f)), Image.LANCZOS)
    g_row = im.height / 2 + v["centre"][2] * ppm
    canvas.alpha_composite(im, (int(left_px), int(round(ground_y - g_row))))


def paste_fit(canvas, name, box, crop_alpha=True, margin=0.03):
    im = load(name)
    if crop_alpha and im.getchannel("A").getextrema()[0] < 255:
        bb = im.getchannel("A").point(lambda a: 255 if a >= 30 else 0).getbbox()
        mx, my = int((bb[2] - bb[0]) * margin), int((bb[3] - bb[1]) * margin)
        im = im.crop((max(0, bb[0] - mx), max(0, bb[1] - my), min(im.width, bb[2] + mx), min(im.height, bb[3] + my)))
    x0, y0, x1, y1 = box
    f = min((x1 - x0) / im.width, (y1 - y0) / im.height)
    im = im.resize((max(1, round(im.width * f)), max(1, round(im.height * f))), Image.LANCZOS)
    canvas.alpha_composite(im, (int(x0 + ((x1 - x0) - im.width) // 2), int(y0 + ((y1 - y0) - im.height) // 2)))
    return f


def paste_cover(canvas, name, box):
    im = load(name)
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    f = max(bw / im.width, bh / im.height)
    im = im.resize((max(1, round(im.width * f)), max(1, round(im.height * f))), Image.LANCZOS)
    cx, cy = (im.width - bw) // 2, (im.height - bh) // 2
    canvas.alpha_composite(im.crop((cx, cy, cx + bw, cy + bh)), (x0, y0))


def main():
    ref = Image.open(REF).convert("RGBA")
    bg = ref.getpixel((1300, 60))            # the sheet grey (its top-left corner is the outbuilding plaster)
    c = Image.new("RGBA", ref.size, bg)
    # top: the closed side, the ground at the sheet's row 352, 100 px/m (the sheet's figure is 180 px = 1.8 m)
    band = Image.new("RGBA", ref.size, (0, 0, 0, 0))
    # 75 px/m (the sheet's own scale is about 100 px/m, but the spec corridor is taller: eave +3.0, ridge end +4.2)
    paste_elev(band, "corr_closed", PPM, 0, 352)
    c.alpha_composite(band.crop((0, 0, ref.width, 372)), (0, 0))
    draw_figure(c, 100, 352, PPM)
    band = Image.new("RGBA", ref.size, (0, 0, 0, 0))
    paste_elev(band, "corr_open", PPM, 0, 705)
    c.alpha_composite(band.crop((0, 384, 1120, 720)), (0, 384))
    draw_figure(c, 100, 705, PPM)
    f_end = paste_fit(c, "corr_end", (1150, 385, 1405, 715))
    # the end view's own silhouette at its scale, beside it (inside the panel's left margin)
    paste_fit(c, "corr_top", (20, 740, 885, 1086), crop_alpha=False)
    paste_cover(c, "corr_34", (900, 740, 1448, 1086))
    out = D / "sheet_corridor.png"
    c.convert("RGB").save(out)
    print("saved", out, "end view scale", round(f_end, 3))
    for k, box in PANELS.items():
        ref.crop(box).convert("RGB").save(D / f"pair_{k}_ref.png")
        c.crop(box).convert("RGB").save(D / f"pair_{k}_ours.png")
    print("pairs", list(PANELS))


if __name__ == "__main__":
    main()
