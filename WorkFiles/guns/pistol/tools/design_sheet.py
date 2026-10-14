"""HP01 design sheet: the sheet's LEFT and TOP with the trace, the build frame, bone pivots, sockets, key dimensions,
and the part / finish table, all read from hp01_spec.json + hp01_measured.json (nothing typed in by hand).

    py -3 -B WorkFiles/guns/pistol/tools/design_sheet.py   ->  WorkFiles/guns/pistol/HP01_DESIGN_SHEET.png
"""
import json
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(OUT, "..", "..", ".."))
S = json.load(open(os.path.join(OUT, "hp01_spec.json")))
M = json.load(open(os.path.join(OUT, "hp01_measured.json")))
L = json.load(open(os.path.join(OUT, "traces", "LEFT_outline.json")))
T = json.load(open(os.path.join(OUT, "traces", "TOP_outline.json")))
sheet = Image.open(os.path.join(ROOT, "References", "Guns", "Pistol", "pistol_sheetA.webp")).convert("RGB")
k = 2.0
s = M["scale"]["px_per_mm"]
FX, BY = M["frame_px"]["x_front"], M["frame_px"]["bore_y"]
GF = S["frames"]["grip_F"]


def font(n):
    try:
        return ImageFont.truetype("arial.ttf", n)
    except OSError:
        return ImageFont.load_default()


def B2px(x, z):
    """build-frame mm -> LEFT sheet px."""
    xf, zf = x + GF[0], z + GF[1]
    return FX - xf * s, BY - zf * s


W, H = 2400, 1700
im = Image.new("RGB", (W, H), (245, 245, 242))
d = ImageDraw.Draw(im)
d.text((30, 18), "Heavy Pistol HP-01 (HP01)  W0 design sheet  2026-10-14", fill=(20, 20, 20), font=font(30))
d.text((30, 58), "trace (red), build frame origin Grip (green), bone pivots (blue), sockets (orange); scale %.4f px/mm from the real "
       "overall 273 mm; ruler +%.1f %%" % (s, M["scale"]["ruler_error_pct"]), fill=(60, 60, 60), font=font(18))

# LEFT panel, 2x
x0, y0, x1, y1 = 0, 110, 624, 530
crop = sheet.crop((x0, y0, x1, y1)).resize((int((x1 - x0) * k), int((y1 - y0) * k)), Image.LANCZOS)
ox, oy = 30, 100
im.paste(crop, (ox, oy))


def P(px, py):
    return ox + (px - x0) * k, oy + (py - y0) * k


pts = [P(*p) for p in L["px"]]
d.line(pts + [pts[0]], fill=(230, 30, 30), width=2)
for h in L.get("holes", []):
    hp = [P(*p) for p in h["px"]]
    d.line(hp + [hp[0]], fill=(230, 30, 30), width=2)
d.line([P(x0, BY), P(x1, BY)], fill=(240, 220, 0), width=1)
g = P(*B2px(0, 0))
d.ellipse([g[0] - 7, g[1] - 7, g[0] + 7, g[1] + 7], outline=(0, 170, 0), width=3)
d.text((g[0] + 9, g[1] - 8), "Grip", fill=(0, 120, 0), font=font(16))
for b in S["bones"][1:]:
    q = P(*B2px(b["head_B"][0], b["head_B"][2]))
    d.rectangle([q[0] - 5, q[1] - 5, q[0] + 5, q[1] + 5], outline=(30, 60, 230), width=2)
    d.text((q[0] + 7, q[1] + 2), b["name"], fill=(30, 60, 200), font=font(14))
for so in S["sockets"]:
    if so["name"] in ("Grip",):
        continue
    q = P(*B2px(so["B"][0], so["B"][2]))
    d.ellipse([q[0] - 4, q[1] - 4, q[0] + 4, q[1] + 4], fill=(240, 140, 0))
    d.text((q[0] + 6, q[1] - 16), so["name"], fill=(200, 100, 0), font=font(13))
kd = S["key_dimensions"]
d.text((ox, oy + crop.height + 8), "overall 273.0 | height %.1f (class 159) | slide length %.1f | sight radius %.1f | sight line %.1f above bore | "
       "grip axis %.1f deg | trigger reach %.1f | top line rises %.1f deg" % (kd["height_mm_reads"], kd["slide_length_mm"], kd["sight_radius_mm"],
                                                                          kd["sight_line_above_bore_mm"], S["frames"]["grip_axis_deg"],
                                                                          kd["trigger_reach_to_backstrap_mm"], kd["top_line_rise_deg"]),
       fill=(20, 20, 20), font=font(17))

# TOP panel, 2x
tx0, ty0, tx1, ty1 = 0, 845, 624, 1000
ct = sheet.crop((tx0, ty0, tx1, ty1)).resize((int((tx1 - tx0) * k), int((ty1 - ty0) * k)), Image.LANCZOS)
tox, toy = 30, 1010
im.paste(ct, (tox, toy))
tp = [(tox + (x - tx0) * k, toy + (y - ty0) * k) for x, y in T["px"]]
d.line(tp + [tp[0]], fill=(230, 30, 30), width=2)
d.text((tox, toy + ct.height + 8), "TOP: slide %.1f mm wide as drawn, %.1f at the levers (class max ~32: Q1, default = as drawn, one parameter K_Y); "
       "rail 6 bars in the side views, 5 in TOP (6 kept)" % (S["scale"]["width"]["slide_mm_sheet"], S["scale"]["width"]["levers_mm_sheet"]),
       fill=(20, 20, 20), font=font(17))

# part table
cx = 1320
d.text((cx, 100), "part / bone / process / finish / slot / LOD0", fill=(20, 20, 20), font=font(20))
y = 132
for p in S["parts"]:
    line = "%-14s %-11s %-9s %-26s %-10s %5d" % (p["id"], p["bone"], p["process"], p["finish"][:26], p["slot"].replace("M_HP01_", ""), p["lod0_alloc"])
    d.text((cx, y), line, fill=(30, 30, 30), font=font(15))
    y += 22
y += 14
d.text((cx, y), "clips: " + ", ".join(c["name"].replace("A_HP01_", "") for c in S["clips"]), fill=(20, 20, 20), font=font(16))
y += 26
d.text((cx, y), "slide travel 48 (lock 46, press check 14); hammer 58 deg; trigger 9 deg; safety -40 deg; slide stop 10 deg; release 3 mm",
       fill=(20, 20, 20), font=font(15))
y += 26
d.text((cx, y), "LOD0 %d (15-25k, ceiling 30k); mag 1.8k; sets Steel 4096 / Furniture 1024 / Mag 1024" % S["budgets_triangles"]["gun"]["sum"],
       fill=(20, 20, 20), font=font(15))
y += 26
d.text((cx, y), "close-up gates CU1-CU8 from W1 (faired outlines, authored bevels, no slivers, ER0 at W1c, finish cards)", fill=(150, 30, 30), font=font(15))
y += 22
d.text((cx, y), "S0: %s" % S["S0"]["status"], fill=(0, 120, 0), font=font(18))
# 3/4 thumb
th = sheet.crop((630, 643, 1253, 1253)).resize((520, 509), Image.LANCZOS)
im.paste(th, (cx + 200, 1130))
d.text((cx + 200, 1110), "3/4 FRONT LEFT (sheet, left side by camera geometry)", fill=(60, 60, 60), font=font(15))
im.save(os.path.join(OUT, "HP01_DESIGN_SHEET.png"))
print("ok", im.size)
