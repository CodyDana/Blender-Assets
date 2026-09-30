"""Round 3 reference | ours pairs for the upper roof form (system Python + Pillow):
  cmp_r3_upper_front.png   hall sheet front elevation, upper roof + band | ours (ortho, same framing by the silhouette
                           scale: the upper roof's eave corners span the same width)
  cmp_r3_top.png           hall sheet top view | ours (ortho top)
  cmp_r3_ref2_hall.png     dojo1_reference2, the hall at high zoom | ours (context_ref2_elevated, sunset), the hall
                           projected from world points with the render camera
  cmp_r3_f1_vs_r3.png      ours before (f1) | after (r3), front elevation upper roof
Run: py Scripts/dojo/hall/compose_r3.py [tag=r3]
"""
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
TAG = sys.argv[1] if len(sys.argv) > 1 else "r3"
D = ROOT / "WorkFiles" / "dojo" / "build" / "hall" / "renders" / TAG
F1 = ROOT / "WorkFiles" / "dojo" / "build" / "hall" / "renders" / "f1"
REF = ROOT / "References" / "Dojo"


def label(im, text):
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 9 * len(text) + 12, 22), fill=(0, 0, 0))
    d.text((6, 5), text, fill=(255, 255, 255))
    return im


def pair(a, b, out, h=520, la="reference", lb="ours"):
    a = a.convert("RGB")
    b = b.convert("RGB")
    a = a.resize((round(a.width * h / a.height), h), Image.LANCZOS)
    b = b.resize((round(b.width * h / b.height), h), Image.LANCZOS)
    c = Image.new("RGB", (a.width + b.width + 20, h), (255, 255, 255))
    c.paste(label(a, la), (0, 0))
    c.paste(label(b, lb), (a.width + 20, 0))
    c.save(out)
    print("wrote", out)


def flat(im, bg=(150, 150, 150)):
    im = im.convert("RGBA")
    c = Image.new("RGBA", im.size, bg + (255,))
    c.alpha_composite(im)
    return c


def ortho_crop(name, x0, x1, z0, z1, centre=(22.0, 20.0, 4.8), width_m=26.0):
    im = Image.open(D / f"{name}.png")
    ppm = im.width / width_m
    L = round(im.width / 2 + (x0 - centre[0]) * ppm)
    R = round(im.width / 2 + (x1 - centre[0]) * ppm)
    T = round(im.height / 2 - (z1 - centre[2]) * ppm)
    B = round(im.height / 2 - (z0 - centre[2]) * ppm)
    return flat(im).crop((L, T, R, B))


def project(cam_loc, look, lens, w, h, p):
    """Blender-style perspective (sensor 36 mm horizontal) of a world point to pixels."""
    f = [look[i] - cam_loc[i] for i in range(3)]
    fl = math.sqrt(sum(v * v for v in f))
    f = [v / fl for v in f]
    upw = (0.0, 0.0, 1.0)
    r = [f[1] * upw[2] - f[2] * upw[1], f[2] * upw[0] - f[0] * upw[2], f[0] * upw[1] - f[1] * upw[0]]
    rl = math.sqrt(sum(v * v for v in r))
    r = [v / rl for v in r]
    u = [r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0]]
    d = [p[i] - cam_loc[i] for i in range(3)]
    zc = sum(d[i] * f[i] for i in range(3))
    xc = sum(d[i] * r[i] for i in range(3))
    yc = sum(d[i] * u[i] for i in range(3))
    s = lens / 36.0 * w
    return (w / 2 + s * xc / zc, h / 2 - s * yc / zc)


ref_front = Image.open(REF / "dojo_hall_front_ref.png").convert("RGB")
# the sheet's upper roof (eave corners at about x 95 / 905) + the band down to the lower roof's top
if (D / "hall_front.png").exists():
    ours = ortho_crop("hall_front", 11.3, 32.7, 3.95, 9.35)
    pair(ref_front.crop((88, 50, 912, 246)), ours, D / "cmp_r3_upper_front.png", h=420)
    if (F1 / "hall_front.png").exists():
        D_, F1_ = D, F1
        a = Image.open(F1 / "hall_front.png")
        ppm = a.width / 26.0
        box = (round(a.width / 2 + (11.3 - 22) * ppm), round(a.height / 2 - (9.35 - 4.8) * ppm),
               round(a.width / 2 + (32.7 - 22) * ppm), round(a.height / 2 - (3.95 - 4.8) * ppm))
        pair(flat(a).crop(box), ours, D / "cmp_r3_f1_vs_r3.png", h=420, la="f1 (round 2 in Unreal)", lb="r3")
if (D / "hall_top.png").exists():
    t = Image.open(D / "hall_top.png")
    ppm = t.width / 26.0      # ortho top, centre (22, 27.8)
    box = (round(t.width / 2 + (10.2 - 22) * ppm), round(t.height / 2 - (35.2 - 27.8) * ppm),
           round(t.width / 2 + (33.8 - 22) * ppm), round(t.height / 2 - (20.6 - 27.8) * ppm))
    pair(ref_front.crop((20, 520, 720, 1000)), flat(t).crop(box), D / "cmp_r3_top.png", h=520)
ref2 = Image.open(REF / "dojo1_reference2.png").convert("RGB")
if (D / "context_ref2_elevated.png").exists():
    c = Image.open(D / "context_ref2_elevated.png")
    cam, look, lens = (22.0, -7.5, 9.2), (22.0, 23.5, 1.2), 30.0
    pts = [project(cam, look, lens, c.width, c.height, (x, y, z)) for x in (9.8, 34.2) for y in (21.0, 35.0)
           for z in (0.0, 9.6)]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    box = (round(min(xs)), round(min(ys)), round(max(xs)), round(max(ys)))
    pair(ref2.crop((395, 120, 1055, 470)), c.convert("RGB").crop(box), D / "cmp_r3_ref2_hall.png", h=520)
    pair(ref2.crop((420, 125, 1030, 300)), c.convert("RGB").crop((box[0], box[1], box[2],
                                                                   round(box[1] + (box[3] - box[1]) * 0.55))),
         D / "cmp_r3_ref2_roof.png", h=420)
if (D / "context_ref2_studio.png").exists():
    c = Image.open(D / "context_ref2_studio.png")
    cam, look, lens = (22.0, -7.5, 9.2), (22.0, 23.5, 1.2), 30.0
    pts = [project(cam, look, lens, c.width, c.height, (x, y, z)) for x in (9.8, 34.2) for y in (21.0, 35.0)
           for z in (0.0, 9.6)]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    box = (round(min(xs)), round(min(ys)), round(max(xs)), round(max(ys)))
    pair(ref2.crop((395, 120, 1055, 470)), flat(c).crop(box), D / "cmp_r3_ref2_hall_studio.png", h=520,
         lb="ours, neutral studio light")
