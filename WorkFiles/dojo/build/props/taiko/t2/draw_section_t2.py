"""t2: draw section_t2.json (the drum seated in the felt-lined saddle, exported meshes) to seat_section.png, and
print the measured vertical stack at the bottom of the seat (y = 0) per plane. System Python + Pillow."""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
S = json.loads((HERE / "section_t2.json").read_text(encoding="utf-8"))
COL = {"barrel": (150, 60, 30), "felt": (200, 30, 50), "wood": (110, 90, 70)}
try:
    FONT = ImageFont.truetype("arial.ttf", 18)
    FONTS = ImageFont.truetype("arial.ttf", 15)
except OSError:
    FONT = FONTS = ImageFont.load_default()


def z_at(segs, y0=0.0):
    out = []
    for (a, b) in segs:
        if (a[0] - y0) * (b[0] - y0) <= 0 and a[0] != b[0]:
            t = (y0 - a[0]) / (b[0] - a[0])
            out.append(a[1] + (b[1] - a[1]) * t)
    return out


keys = list(S)
W, H = 1800, 300 * len(keys) + 60
im = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(im)
d.text((10, 10), "t2: the drum seated in its saddle - sections of the EXPORTED drum + stand FBX (LOD0) at the planes "
       "below; brown = barrel, red = felt, grey-brown = wood seat", fill="black", font=FONT)
stack = {}
for r, k in enumerate(keys):
    y0 = 50 + r * 300
    segs = S[k]
    # left panel: the whole saddle (y -0.45..0.45, z 0.62..0.86), 1000 px over 0.9 m; drawn on its own image (clipped)
    L = Image.new("RGB", (1000, 270), "white")
    dl = ImageDraw.Draw(L)
    sx = 1000 / 0.9
    def P(p):
        return ((p[0] + 0.45) * sx, 270 - (p[1] - 0.62) * sx)
    for part in ("wood", "felt", "barrel"):
        for a, b in segs[part]:
            dl.line([P(a), P(b)], fill=COL[part], width=2)
    im.paste(L, (10, y0 + 10))
    d.rectangle([10, y0 + 10, 1010, y0 + 280], outline=(200, 200, 200))
    d.text((14, y0 + 12), f"plane x = {k[1:]} m", fill="black", font=FONT)
    # right panel: zoom at the seat bottom (y -0.03..0.03 m), 12 px per mm, 0 mm = the barrel bottom
    zb = min(z_at(segs["barrel"]) or [0.65])
    Z = Image.new("RGB", (720, 250), "white")
    dz = ImageDraw.Draw(Z)
    zs = 12000
    def Q(p):
        return ((p[0] + 0.03) * zs, 60 + (zb - p[1]) * zs)
    for mm in range(-4, 16):
        yy = 60 + mm / 1000 * zs
        dz.line([(0, yy), (720, yy)], fill=(232, 232, 232))
        if mm % 2 == 0:
            dz.text((672, yy - 8), f"{-mm} mm", fill=(140, 140, 140), font=FONTS)
    for part in ("wood", "felt", "barrel"):
        for a, b in segs[part]:
            if abs(a[0]) < 0.2 and abs(b[0]) < 0.2:
                dz.line([Q(a), Q(b)], fill=COL[part], width=3)
    im.paste(Z, (1060, y0 + 10))
    d.rectangle([1060, y0 + 10, 1780, y0 + 260], outline=(200, 200, 200))
    zf = sorted(z_at(segs["felt"]))
    zw = sorted(z_at(segs["wood"]))
    wood_top = max([z for z in zw if z < zb + 0.001] or [float("nan")])
    st = {"barrel_bottom_z": round(zb, 5),
          "felt_top_z": round(max(zf), 5) if zf else None, "felt_bottom_z": round(min(zf), 5) if zf else None,
          "wood_seat_z": round(wood_top, 5)}
    st["barrel_to_felt_mm"] = round((zb - st["felt_top_z"]) * 1000, 3) if zf else None
    st["felt_bottom_into_wood_mm"] = round((wood_top - st["felt_bottom_z"]) * 1000, 3) if zf else None
    st["barrel_to_wood_mm"] = round((zb - wood_top) * 1000, 3)
    stack[k] = st
    txt = (f"zoom at y = 0 (12 px/mm): barrel to felt {st['barrel_to_felt_mm']} mm (negative = pressed in), felt "
           f"{st['felt_bottom_into_wood_mm']} mm into the wood" if zf else
           f"zoom at y = 0 (12 px/mm): no felt at this plane; barrel to wood {st['barrel_to_wood_mm']} mm")
    d.text((1064, y0 + 264), txt, fill="black", font=FONTS)
im.save(HERE / "seat_section.png")
(HERE / "seat_section_stack.json").write_text(json.dumps(stack, indent=1), encoding="utf-8")
print(json.dumps(stack, indent=1))
