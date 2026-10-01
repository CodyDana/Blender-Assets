"""Annotate the plan render with the case footprints (from layout.json), their emblem fronts (arrow), labels, types
and the floor gaps along each side row. Usage: py -3 plan_annotate.py <plan.png> <layout.json> <out.png>"""
import json
import math
import sys

from PIL import Image, ImageDraw, ImageFont

src, lay, out = sys.argv[1:4]
X0, Y1, PPM = -0.5, 20.5, 80
im = Image.open(src).convert("RGB")
d = ImageDraw.Draw(im)
try:
    f = ImageFont.truetype("arial.ttf", 18)
    fs = ImageFont.truetype("arial.ttf", 15)
except OSError:
    f = fs = ImageFont.load_default()


def px(x, y):
    return ((x - X0) * PPM, (Y1 - y) * PPM)


cases = json.load(open(lay))["cases"]
NAMES = {"5": "kunai", "4": "cloak", "G1": "scrolls", "G4": "medium", "G3": "tall", "8": "shuriken tray",
         "7": "boots", "6": "hat", "G5": "tall", "G2": "tall", "1": "", "2": "", "3": "", "10": "hero"}
rows = {"W": [], "E": []}
for c in cases:
    W, D = c["width_depth_plinth_glass_m"][:2]
    x, y = c["loc"]
    r = math.radians(c["rot_z"])
    ca, sa = math.cos(r), math.sin(r)
    corners = [(x + ca * u - sa * v, y + sa * u + ca * v) for u, v in ((-W / 2, -D / 2), (W / 2, -D / 2),
                                                                         (W / 2, D / 2), (-W / 2, D / 2))]
    side = c["label"] not in ("1", "2", "3", "10")
    col = (40, 255, 90) if side else (255, 200, 60)
    d.polygon([px(*p) for p in corners], outline=col, width=3)
    # the emblem front: local -Y
    fx, fy = x + sa * (D / 2), y - ca * (D / 2)
    tx, ty = x + sa * (D / 2 + 0.35), y - ca * (D / 2 + 0.35)
    d.line([px(fx, fy), px(tx, ty)], fill=(255, 60, 60), width=4)
    d.ellipse([px(tx, ty)[0] - 5, px(tx, ty)[1] - 5, px(tx, ty)[0] + 5, px(tx, ty)[1] + 5], fill=(255, 60, 60))
    lx, ly = px(x, y)
    d.text((lx - 40, ly - 22), f"{c['label']} {c['type']}", fill=(255, 255, 255), font=f, stroke_width=2,
           stroke_fill=(0, 0, 0))
    d.text((lx - 40, ly), f"{NAMES.get(c['label'], '')}", fill=(230, 230, 230), font=fs, stroke_width=2,
           stroke_fill=(0, 0, 0))
    if side:
        ys = [p[1] for p in corners]
        rows["W" if x < 6 else "E"].append((min(ys), max(ys), x, W, D))
for k, rw in rows.items():
    rw.sort()
    for a, b in zip(rw, rw[1:]):
        g = b[0] - a[1]
        xm = a[2] + (-0.75 if k == "W" else 0.75)
        d.line([px(xm, a[1]), px(xm, b[0])], fill=(120, 200, 255), width=2)
        d.text((px(xm, (a[1] + b[0]) / 2)[0] - (70 if k == "W" else -6), px(xm, (a[1] + b[0]) / 2)[1] - 9),
               f"{g:.2f} m", fill=(120, 200, 255), font=fs, stroke_width=2, stroke_fill=(0, 0, 0))
d.text((10, 8), "r20 cases: plan (cut at +2.90, north = the rear dais up). Green = side cases (1.10 x 0.90 m), "
       "red tick = the emblem front, blue = floor gaps", fill=(255, 255, 255), font=fs, stroke_width=2,
       stroke_fill=(0, 0, 0))
im.save(out)
print("wrote", out, im.size)
