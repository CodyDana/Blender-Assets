"""End-on section diagrams: the TRUE cross-sections of each option's LOD0 mesh (measure_mesh.py bisects) at three
stations, drawn to scale and dimensioned.  One panel per option (the option filled, the current section dashed, the
photo's reconciled face angle as a thin guide from the edge) plus one overlay panel (current / A / B / C together).

python make_sections.py   (Python 3.12 with PIL; reads options/<id>/mesh_measure.json, writes options/sections/*.png)
"""
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
OUT = HERE / "sections"
OUT.mkdir(exist_ok=True)
IDS = ["current", "A", "B", "C"]
STATIONS = [("26.7", 0.20), ("56.7", 0.45), ("91.4", 0.75)]
PHOTO = {"26.7": (0.237, (0.195, 0.31)), "56.7": (0.185, (0.14, 0.213)), "91.4": (0.217, (0.17, 0.31))}
COL = {"current": (150, 150, 150), "A": (70, 150, 230), "B": (230, 120, 40), "C": (60, 175, 90)}
FILL = {"current": (205, 205, 205), "A": (190, 215, 245), "B": (250, 210, 180), "C": (190, 230, 200)}
BG, INK, GUIDE = (250, 250, 247), (30, 30, 30), (200, 40, 120)
W, PANEL_H = 640, 580
S = 11.0                                  # px per mm


def font(size, bold=False):
    for name in (("arialbd.ttf" if bold else "arial.ttf"), "segoeui.ttf"):
        try:
            return ImageFont.truetype("C:/Windows/Fonts/" + name, size)
        except OSError:
            continue
    return ImageFont.load_default()


F_T, F_L, F_S = font(22, True), font(16, True), font(14)
sys.path.insert(0, str(HERE / "calc"))
from section_post import post as _post  # noqa: E402
data = {i: json.loads((HERE / i / "mesh_measure.json").read_text()) for i in IDS if (HERE / i / "mesh_measure.json").exists()}
for _d in data.values():                    # exact face slope / angle from the outline's own vertices
    for _s in _d["stations"].values():
        _p = _post(_s)
        _s["face_slope_mesh"], _s["face_angle_deg"] = _p["face_slope"], _p["face_angle_deg"]


def dashed(draw, pts, col, w=2, dash=6):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        L = math.hypot(x1 - x0, y1 - y0)
        n = max(1, int(L / dash))
        for k in range(0, n, 2):
            a, b = k / n, min(1.0, (k + 1) / n)
            draw.line([(x0 + (x1 - x0) * a, y0 + (y1 - y0) * a), (x0 + (x1 - x0) * b, y0 + (y1 - y0) * b)], fill=col,
                      width=w)


def to_px(cx, cy, y, z):
    return cx + y * S, cy - z * S


def panel(option, overlay=False):
    img = Image.new("RGB", (W, PANEL_H), BG)
    d = ImageDraw.Draw(img)
    title = "all four overlaid (true mesh sections)" if overlay else f"{option}: true section, LOD0 mesh"
    d.text((12, 8), title, font=F_L, fill=INK)
    d.text((12, 30), "to scale (11 px/mm); dashed = current; magenta = photo face angle from the edge" if not overlay
           else "grey current, blue A, orange B, green C; magenta = photo face angle", font=F_S, fill=(90, 90, 90))
    top = 64
    band = (PANEL_H - top) / 3
    for k, (st, frac) in enumerate(STATIONS):
        y0 = top + band * k
        cy = y0 + 22 + 4.8 * S
        cx = W / 2
        h_all = data["current"]["stations"][st]["half_width_mm"]
        ph, (lo, hi) = PHOTO[st]
        order = IDS if overlay else ([option] if option == "current" else [option, "current"])
        for oid in order:
            if oid not in data:
                continue
            poly = [to_px(cx, cy, y, z) for y, z in data[oid]["stations"][st]["outline_yz_mm"]]
            if overlay:
                d.polygon(poly, outline=COL[oid], width=2)
            elif oid == option:
                d.polygon(poly, fill=FILL[oid], outline=COL[oid], width=2)
            else:
                dashed(d, poly, (60, 60, 60), 1)
        # photo guide on top: a sharp diamond face at the reconciled slope, from each edge to the axis (top half)
        for sgn in (1, -1):
            d.line([to_px(cx, cy, sgn * h_all, 0.0), to_px(cx, cy, 0.0, ph * h_all)], fill=GUIDE, width=2)
        ref = data[option if not overlay else "current"]["stations"][st]
        d.text((12, y0 + 2), f"x {float(st):.1f} mm ({frac:.2f} of the visible blade)   width {2 * ref['half_width_mm']:.1f} mm",
               font=F_S, fill=INK)
        ty = y0 + 22 + 9.6 * S + 4
        if overlay:
            txt = "   ".join(f"{oid} {data[oid]['stations'][st]['ridge_thickness_mm']:.1f}mm/{data[oid]['stations'][st]['face_angle_deg']:.1f}°"
                            for oid in IDS if oid in data)
            d.text((12, ty), txt + f"   photo {math.degrees(math.atan(ph)):.1f}°", font=F_S, fill=INK)
        else:
            s_ = data[option]["stations"][st]
            cur = data["current"]["stations"][st]
            txt = (f"ridge {s_['ridge_thickness_mm']:.2f} mm   face {s_['face_angle_deg']:.1f}° (slope {s_['face_slope_mesh']:.3f})"
                   f"   photo {math.degrees(math.atan(ph)):.1f}° ({ph:.3f})")
            d.text((12, ty), txt, font=F_S, fill=INK)
            g = _post(s_).get("grind_band_mm")
            d.text((12, ty + 18), f"grind band in section {g:.2f} mm" + (
                "" if option == "current" else f"   (current: ridge {cur['ridge_thickness_mm']:.2f} mm, "
                                               f"{cur['face_angle_deg']:.1f}°)"), font=F_S, fill=(80, 80, 80))
    return img


for oid in IDS:
    if oid in data:
        panel(oid).save(OUT / f"section_{oid}.png")
panel("current", overlay=True).save(OUT / "section_overlay.png")
print("sections written", sorted(p.name for p in OUT.glob("*.png")))
