"""Draw WorkFiles/guns/sniper/SR01_DESIGN_SHEET.png: the SR01 decisions from sr01_spec.json (Pillow only).

    py -3 -B WorkFiles/guns/sniper/tools/design_sheet.py

Panels: (1) right side, bipod FOLDED (the sheet pose) over the traced GR silhouette, with bones, sockets, stations,
the bolt-open knob and the scope attachment; (2) right side, bipod DEPLOYED (ext 0 solid, ext 76 dashed, cant 15 deg
from the front in the inset) and the fold sweep arc; (3) front view (Y-Z) of the deployed bipod; (4) TOP outline with
the traced TOP silhouette and the knob / feet / riser widths; (5) mechanism close-ups: bolt cycle, mag release,
riser travel. QA: the spec's part boxes and the traced silhouette are drawn together so drift shows.
The SMG01 design_sheet.py was the template (layout idea only).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve()
SR = HERE.parents[1]
SPEC = json.loads((SR / "sr01_spec.json").read_text(encoding="utf-8"))
GR = json.loads((SR / "trace" / "GR_outline.json").read_text(encoding="utf-8"))
TOPT = json.loads((SR / "trace" / "TOP_outline.json").read_text(encoding="utf-8"))
OUT = SR / "SR01_DESIGN_SHEET.png"

try:
    FT = ImageFont.truetype("arial.ttf", 22)
    FS = ImageFont.truetype("arial.ttf", 15)
    FXS = ImageFont.truetype("arial.ttf", 12)
except OSError:
    FT = FS = FXS = ImageFont.load_default()

S = 1.35                       # px per mm
W, H = 1600, 2450
im = Image.new("RGB", (W, H), (250, 250, 247))
d = ImageDraw.Draw(im)
P = {p["id"]: p for p in SPEC["parts"]}
BN = {b["bone"]: b for b in SPEC["bones"]["table"]}
BP = SPEC["bipod"]
BC = SPEC["bolt_cycle"]


class View:
    def __init__(self, ox, oy, s=S):
        self.ox, self.oy, self.s = ox, oy, s

    def __call__(self, x, z):
        return (self.ox + x * self.s, self.oy - z * self.s)


def poly(v, pts, **kw):
    d.polygon([v(*p) for p in pts], **kw)


def line(v, pts, fill=(0, 0, 0), width=1, dash=None):
    Q = [v(*p) for p in pts]
    if not dash:
        d.line(Q, fill=fill, width=width)
        return
    for a, b in zip(Q[:-1], Q[1:]):
        L = math.dist(a, b)
        n = max(1, int(L / dash))
        for i in range(0, n, 2):
            t0, t1 = i / n, min(1, (i + 1) / n)
            d.line([(a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0), (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1)], fill=fill, width=width)


def rect(v, X, Z, **kw):
    a, b = v(X[0], Z[1]), v(X[1], Z[0])
    d.rectangle([min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])], **kw)


def circle(v, x, z, rad, **kw):
    c = v(x, z)
    rr = rad * v.s
    d.ellipse([c[0] - rr, c[1] - rr, c[0] + rr, c[1] + rr], **kw)


def label(v, x, z, t, fill=(0, 0, 0), f=FXS, dx=4, dy=-14):
    c = v(x, z)
    d.text((c[0] + dx, c[1] + dy), t, fill=fill, font=f)


def silhouette(v, fill=(214, 216, 205), outline=(120, 120, 110), keys=("silhouette",)):
    rings = [r_ for k in keys for r_ in GR[k]["mm"]]
    for r_ in rings:
        area = 0.5 * sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(r_, r_[1:] + r_[:1]))
        poly(v, r_, fill=fill if area > 0 else (250, 250, 247), outline=outline)


def leg(v, theta, ext, col=(30, 30, 30), dash=None, w=2):
    hx, hz = BP["hub_axis"]["X"], BP["hub_axis"]["Z"]
    th = math.radians(theta)
    dvec = (math.cos(th), -math.sin(th))
    nvec = (math.sin(th), math.cos(th))
    L_out = P["bipod_leg_l"]["box_M"]["X"][1] - hx
    foot = P["bipod_ext_l"]["dims"]["foot"]
    f0, f1 = foot["X"][0] - hx + ext, foot["X"][1] - hx + ext
    rr = foot["dia"] / 2

    def pt(s, o):
        return (hx + s * dvec[0] + o * nvec[0], hz + s * dvec[1] + o * nvec[1])
    for o in (-9.7, 9.7):
        line(v, [pt(18, o), pt(L_out, o)], fill=col, width=w, dash=dash)
    for o in (-6.35, 6.35):
        line(v, [pt(L_out, o), pt(f0, o)], fill=col, width=1, dash=dash)
    line(v, [pt(f0, -rr), pt(f1, -rr), pt(f1, rr), pt(f0, rr), pt(f0, -rr)], fill=col, width=w, dash=dash)
    line(v, [pt(L_out - 18.8, -14), pt(L_out, -14), pt(L_out, 14), pt(L_out - 18.8, 14), pt(L_out - 18.8, -14)], fill=col, width=1, dash=dash)


def bipod_body(v, col=(40, 40, 40)):
    mt = P["bipod_mount"]["dims"]
    rect(v, mt["clamp"]["X"], mt["clamp"]["Z"], outline=col, width=2)
    circle(v, BP["hub_axis"]["X"], BP["hub_axis"]["Z"], 18.45, outline=col, width=2)
    tk = mt["tension_knob"]
    rect(v, tk["X"], [tk["Zc"] - tk["r"], tk["Zc"] + tk["r"]], outline=col, width=1)


def bones(v, deployed=False):
    for b in SPEC["bones"]["table"]:
        x, y, z = b["head_M"]
        if b["bone"].endswith("_ext") and deployed:
            th = math.radians(90)
            hx, hz = BP["hub_axis"]["X"], BP["hub_axis"]["Z"]
            s = x - hx
            x, z = hx + s * math.cos(th), hz - s * math.sin(th)
        if b["bone"].endswith("_r") or b["bone"].endswith("_r_ext"):
            continue
        circle(v, x, z, 2.6, fill=(200, 30, 30))
        label(v, x, z, b["bone"], fill=(170, 20, 20), dy=2)


def sockets(v, names):
    for s in SPEC["sockets"]["gun"]:
        if s["socket"] in names:
            x, y, z = s["M_mm"]
            c = v(x, z)
            d.line([c[0] - 5, c[1], c[0] + 5, c[1]], fill=(0, 110, 200), width=2)
            d.line([c[0], c[1] - 5, c[0], c[1] + 5], fill=(0, 110, 200), width=2)
            label(v, x, z, s["socket"], fill=(0, 90, 170), dy=4)


def scope(v):
    sa = SPEC["scope_attachment"]
    sc = P["scope_body"]["dims"]
    ax = sa["sight_M"][2]
    X0, X1 = P["scope_body"]["box_M"]["X"]
    pts = [(X0, ax + sc["eyepiece"] / 2), (X0 + 85, ax + sc["eyepiece"] / 2), (X0 + 100, ax + sc["tube"] / 2),
           (600, ax + sc["tube"] / 2), (640, ax + sc["bell"] / 2), (X1, ax + sc["bell"] / 2)]
    full = pts + [(x, 2 * ax - z) for x, z in reversed(pts)]
    poly(v, full, outline=(60, 60, 60))
    for rx in sa["ring_X"]:
        rect(v, [rx - 11, rx + 11], [SPEC["rails"]["top"]["top_Z"], ax + 21], outline=(60, 60, 60))
    circle(v, sa["eye_point_M"][0], ax, 3, outline=(0, 140, 60), width=2)
    label(v, sa["eye_point_M"][0], ax, f"EyePoint (eye relief {sa['eye_relief']:.0f})", fill=(0, 120, 50), dx=-120, dy=-18)
    label(v, sa["mount_M"][0], sa["mount_M"][2], "Mount = Rail_Top + 2 slots", fill=(0, 90, 170), dy=8)


def title(y, t):
    d.text((20, y), t, fill=(0, 0, 0), font=FT)


# ------------------------------------------------------------------------------------------- header
d.text((20, 12), "Sniper Rifle SR-01 (SR01): design sheet, W0 decisions (sr01_spec.json; frame M: X from the butt-pad rear, Z up from the bore; mm)",
       fill=(0, 0, 0), font=FS)
d.text((20, 32), f"Scale {SPEC['scale']['overall_length']:.0f} mm overall (R2), barrel {SPEC['scale']['real']['barrel_mm']:.0f} (22 in), "
       f"{SPEC['scale']['real']['mass_kg_without_scope_and_mag']} kg w/o scope+mag.  Sheet LEFT = gun RIGHT (R1).  Bipod on the sheet: FOLDED in every view (R5).  S0 {SPEC['S0']['status']}.",
       fill=(60, 60, 60), font=FS)

# ------------------------------------------------------------------------------------------- 1 folded
y1 = 60
title(y1, "1  Right side, bipod FOLDED (sheet pose: authority GR/GL), bolt closed; grey = traced GR silhouette, lines = spec")
v1 = View(60, y1 + 200)
silhouette(v1)
scope(v1)
for pid in ("chassis", "butt", "butt_pad", "cheek_riser", "receiver", "rail", "barrel", "muzzle_device", "magazine", "grip", "trigger", "mag_release", "safety"):
    b = P[pid]["box_M"]
    rect(v1, b["X"], b["Z"], outline=(150, 150, 150))
bipod_body(v1)
leg(v1, 0, 0)
circle(v1, *BC["knob_rest"][::2], P["bolt_handle"]["dims"]["knob_dia"] / 2, outline=(0, 0, 0), width=2)
circle(v1, BC["knob_open"][0], BC["knob_open"][2], P["bolt_handle"]["dims"]["knob_dia"] / 2, outline=(200, 120, 0), width=2)
circle(v1, BC["knob_back"][0], BC["knob_back"][2], P["bolt_handle"]["dims"]["knob_dia"] / 2, outline=(200, 120, 0), width=1)
label(v1, BC["knob_back"][0], BC["knob_back"][2] + 14, f"knob open (-60 deg) and back (88): {BC['knob_min_to_scope']} mm to the scope", fill=(170, 100, 0), dx=-60, dy=-20)
bones(v1)
sockets(v1, ["Grip", "Muzzle", "MuzzleSeat", "ShellEject", "Mag", "MagInsertStart", "Rail_Top", "Shoulder", "SupportHand", "Trigger", "MagRelease", "BipodFoot_L"])
for k, x in (("crown", SPEC["stations_X"]["crown"]), ("bolt face", SPEC["stations_X"]["bolt_face"]), ("forend front", SPEC["stations_X"]["forend_front"])):
    line(v1, [(x, -150), (x, -170)], fill=(90, 90, 90))
    label(v1, x, -170, f"{k} {x}", fill=(90, 90, 90), dy=2)
line(v1, [(0, 0), (1100, 0)], fill=(200, 0, 200), dash=8)
label(v1, 1020, 0, "bore Z 0", fill=(160, 0, 160))

# ------------------------------------------------------------------------------------------- 2 deployed
y2 = 500
title(y2, "2  Right side, bipod DEPLOYED (real pattern): legs +90 deg about the hub (Y axis), ext 0 solid / 38 clip / 76 dashed; fold arc")
v2 = View(60, y2 + 175)
silhouette(v2, fill=(232, 233, 226), keys=("gun_body", "magazine", "scope"))
# cover the drawn folded bipod (it moves)
bipod_body(v2)
leg(v2, 90, 0)
leg(v2, 90, 38, col=(0, 120, 200), dash=None, w=1)
leg(v2, 90, 76, col=(80, 80, 80), dash=6)
leg(v2, 0, 0, col=(170, 170, 170), dash=5, w=1)
hx, hz = BP["hub_axis"]["X"], BP["hub_axis"]["Z"]
Lf = BP["leg_length_hub_to_foot_end"]
arc = [(hx + Lf * math.cos(math.radians(t)), hz - Lf * math.sin(math.radians(t))) for t in np.linspace(0, 90, 30)]
line(v2, arc, fill=(200, 0, 0), dash=5)
label(v2, arc[12][0], arc[12][1], "foot path, detents 0 / +90 (spring ball)", fill=(180, 0, 0))
for k, z in BP["ground_Z_deployed"].items():
    line(v2, [(hx - 70, z), (hx + 70, z)], fill=(0, 140, 60) if k in ("ext_0", "ext_76") else (150, 200, 150))
label(v2, hx + 75, BP["ground_Z_deployed"]["ext_0"], f"ground ext 0: bore {BP['bore_height_deployed']['ext_0']:.0f} mm up", fill=(0, 120, 50), dy=-8)
label(v2, hx + 75, BP["ground_Z_deployed"]["ext_76"], f"ext 76: {BP['bore_height_deployed']['ext_76']:.0f} (notches 19 mm)", fill=(0, 120, 50), dy=-8)
bones(v2, deployed=True)
sw = BP["sweep"]["min_by_obstacle"]
d.text((60, y2 + 655), f"Sweep 0..90 deg, ext 0 and 76, 0.5 deg steps: min to mount {sw['mount']} (designed hinge gap 0.2), forend {sw['forend']}, barrel {sw['barrel']}, "
       f"tension knob {sw['tension_knob']}, magazine {sw['magazine']} mm.  Cant +-15 deg: folded worst {BP['cant_worst']['folded']}, deployed {BP['cant_worst']['deployed']} mm.",
       fill=(0, 0, 0), font=FS)

# ------------------------------------------------------------------------------------------- 3 front view
y3 = 1185
title(y3, "3  Front view (from the muzzle, gun right = screen left): deployed legs at Y +-19.5, cant 0 and 15 deg")
v3 = View(330, y3 + 75, 1.1)


def front_leg(v, yc, cant, ext, col, dash=None):
    a = math.radians(cant)
    cz = BP["cant"]["axis_Z"]
    top = BP["hub_axis"]["Z"]
    bot = BP["ground_Z_deployed"]["ext_0"] - ext
    pts = []
    for (yy, zz) in ((yc - 9.7, top), (yc + 9.7, top), (yc + 9.7, bot + 29), (yc + 18.5, bot + 29), (yc + 18.5, bot), (yc - 18.5, bot), (yc - 18.5, bot + 29), (yc - 9.7, bot + 29), (yc - 9.7, top)):
        z0 = zz - cz
        Y = yy * math.cos(a) - z0 * math.sin(a)
        Z = cz + yy * math.sin(a) + z0 * math.cos(a)
        pts.append((-Y, Z))                      # screen x = -Y (gun right on the left as seen from the front)
    line(v, pts, fill=col, width=2, dash=dash)


# barrel, forend and device outlines (front)
circle(v3, 0, 0, P["muzzle_device"]["dims"]["od"] / 2, outline=(60, 60, 60), width=2)
rect(v3, [-SPEC["parts"][0]["dims"]["forend_width"] / 2, SPEC["parts"][0]["dims"]["forend_width"] / 2], [SPEC["parts"][0]["dims"]["forend_bottom_Z"], SPEC["parts"][0]["dims"]["forend_top_Z"]], outline=(120, 120, 120))
for yc in (19.5, -19.5):
    front_leg(v3, yc, 0, 0, (30, 30, 30))
    front_leg(v3, yc, 15, 0, (200, 80, 0), dash=5)
label(v3, 40, -150, "solid: cant 0;  dashed: cant +15 (about X at Z %.1f)" % BP["cant"]["axis_Z"], fill=(160, 70, 0))
label(v3, -150, BP["ground_Z_deployed"]["ext_0"], "feet 37 dia, 2.0 apart", fill=(0, 0, 0), dy=4)
tk = P["bipod_mount"]["dims"]["tension_knob"]
circle(v3, 0, tk["Zc"], tk["r"], outline=(0, 0, 0))
label(v3, 10, tk["Zc"], f"tension knob (legs clear it by {BP['clearances']['leg_to_tension_knob_Y']} in Y)", dy=-6)

# ------------------------------------------------------------------------------------------- 4 TOP
y4 = 1590
title(y4, "4  TOP (gun left = up): traced TOP silhouette (grey) and spec widths; knob Y from TOP, X from GR (R9); feet width declared (R21)")
v4 = View(60, y4 + 140)
for r_ in TOPT["silhouette"]["mm"]:
    poly(v4, r_, fill=(220, 222, 212), outline=(120, 120, 110))
for pid in ("butt_pad", "cheek_riser", "chassis", "barrel", "muzzle_device", "bipod_ext_l", "bipod_ext_r", "rail"):
    b = P[pid]["box_M"]
    rect(v4, b["X"], b["Y"], outline=(200, 0, 0))
kn = BC["knob_rest"]
circle(v4, kn[0], kn[1], 12.4, outline=(200, 120, 0), width=2)
label(v4, kn[0], kn[1] - 14, f"knob Y {kn[1]} (GR X {kn[0]})", fill=(170, 100, 0), dy=2)

# ------------------------------------------------------------------------------------------- 5 mechanisms
y5 = 1850
title(y5, "5  Mechanisms (x3): bolt (rotate -60 about X, then -X 88), mag release paddle, riser travel")
v5 = View(80, y5 + 330, 3.0)
# bolt cycle seen from the rear (Y-Z): knob arc
cx, cz = 160, 130
d.ellipse([cx - 3, y5 + cz - 3, cx + 3, y5 + cz + 3], fill=(0, 0, 0))
R = math.hypot(kn[1], kn[2])
a0 = math.degrees(math.atan2(kn[2], -kn[1]))
for t in np.linspace(0, 60, 20):
    a = math.radians(a0 + t)
    px, pz = cx - (-R * math.cos(a)) * 1.2, y5 + cz - R * math.sin(a) * 1.2
    d.ellipse([px - 2, pz - 2, px + 2, pz + 2], fill=(200, 120, 0))
d.ellipse([cx - 17 * 1.2, y5 + cz - (57.6 + 17) * 1.2, cx + 17 * 1.2, y5 + cz - (57.6 - 17) * 1.2], outline=(60, 60, 60), width=2)
d.ellipse([cx - 22.6 * 1.2, y5 + cz - (57.6 + 22.6) * 1.2, cx + 22.6 * 1.2, y5 + cz - (57.6 - 22.6) * 1.2], outline=(150, 150, 150))
d.text((40, y5 + 230), "rear view: knob arc rest -> open (26 deg below to 34 deg above horizontal);", fill=(0, 0, 0), font=FXS)
d.text((40, y5 + 246), f"scope tube/eyepiece circles; min {BC['knob_min_to_scope']} mm over rotate + slide", fill=(0, 0, 0), font=FXS)
# paddle (side, x3)
mr = P["mag_release"]["dims"]
v6 = View(520 - 395 * 3.0, y5 + 40 + (-40) * -3.0, 3.0)
rect(v6, [P["magazine"]["box_M"]["X"][0], P["magazine"]["box_M"]["X"][0] + 30], [P["magazine"]["box_M"]["Z"][0], -40], outline=(60, 60, 60), width=2)
px, pz = mr["pivot_XZ"]
pts_rest = [(mr["front_face_X"], pz - mr["pad_below_pivot"]), (mr["front_face_X"], pz + mr["hook_above_pivot"]), (mr["front_face_X"] - 5, pz + mr["hook_above_pivot"]), (mr["front_face_X"] - 5, pz - mr["pad_below_pivot"])]


def roty(p, deg):
    a = math.radians(deg)
    x, z = p[0] - px, p[1] - pz
    return (px + x * math.cos(a) + z * math.sin(a), pz - x * math.sin(a) + z * math.cos(a))


poly(v6, pts_rest, outline=(0, 0, 0))
poly(v6, [roty(p, mr["release_rot_Y_deg"]) for p in pts_rest], outline=(200, 120, 0))
circle(v6, px, pz, 1.5, fill=(200, 30, 30))
label(v6, px, pz, f"pivot; press {mr['release_rot_Y_deg']} deg", fill=(170, 20, 20), dx=-150)
label(v6, mr["front_face_X"], pz + mr["hook_above_pivot"], f"hook travel {mr['hook_travel']} > engage {mr['hook_engagement']}", dx=8)
label(v6, mr["front_face_X"], pz - mr["pad_below_pivot"], f"pad travel {mr['pad_travel']}, gap left {mr['gap_to_mag_pressed']}; shift {mr['declared_shift_rearward']} (declared)", dx=8, dy=0)
# riser
cr = P["cheek_riser"]["dims"]
v7 = View(1100 - 60 * 2.0, y5 + 200, 2.0)
for dz, col in ((0, (0, 0, 0)), (cr["travel_Z"][1], (0, 120, 200)), (cr["travel_Z"][0], (200, 120, 0))):
    rect(v7, P["cheek_riser"]["box_M"]["X"], [cr["plate_Z"][0] + dz, cr["plate_Z"][1] + dz], outline=col, width=2)
line(v7, [(60, P["butt"]["dims"]["top_Z"]), (190, P["butt"]["dims"]["top_Z"])], fill=(90, 90, 90), width=2)
label(v7, 60, P["butt"]["dims"]["top_Z"], f"riser travel {cr['travel_Z']} mm; low-stop gap {cr['low_stop_gap']}", dy=6)

d.text((20, H - 40), "Generated by tools/design_sheet.py from sr01_spec.json. Not a render: decisions only. The scope is the attachment SM_Att_Scope_LongRange.", fill=(90, 90, 90), font=FS)
im.save(OUT)
print("wrote", OUT)
