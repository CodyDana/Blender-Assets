"""Draw WorkFiles/guns/rifle/RIFLE_DESIGN_SHEET.png from rifle_spec.json (+ the traced reference outlines beside it).

    py -3 -B WorkFiles/guns/rifle/tools/design_sheet.py

Panels (all in the spec's M frame: X from the butt heel toward the muzzle, Z up from the bore, 4 px per mm):
  A  SPEC, right side: every part drawn from the spec (its side_profile_M polylines, or its parametric numbers for
     the barrel, gas tube, rod, magazine arcs, selector, port, handle, rivets), key dimensions, height ladder, sockets.
  B  TRACED REFERENCE: the LEFT-labelled panel (= true right side) warped into the M frame, its traced silhouette
     (blue) and the RIGHT-labelled panel's traced silhouette mirrored into its own frame (red), no fitting.
  C  SPEC, top view (image up = gun left): widths from the spec.   D  TRACED TOP silhouette over the TOP panel.
  E  Magazine detail (8 px/mm): arcs, centre, radii, ribs, floor plate, origin and the reload rock start; section.
The QA numbers (IoU of the spec drawing against the traced silhouettes) are printed in the title block.
Needs numpy + Pillow. ROOT comes from this file's location.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve()
RIFLE = HERE.parents[1]
ROOT = HERE.parents[4]
SPEC = json.loads((RIFLE / "rifle_spec.json").read_text(encoding="utf-8"))
MEAS = json.loads((RIFLE / "rifle_measured.json").read_text())
LEFT = json.loads((RIFLE / "trace" / "LEFT_outline.json").read_text())
RIGHT = json.loads((RIFLE / "trace" / "RIGHT_outline.json").read_text())
TOPT = json.loads((RIFLE / "trace" / "TOP_outline.json").read_text())
SHEET = ROOT / "References" / "Guns" / "Rifle" / "rifle_sheetAB.webp"
OUT = RIFLE / "RIFLE_DESIGN_SHEET.png"

P = {p["id"]: p for p in SPEC["parts"]}
S = 4.0                      # px per mm (side + top panels)
W, H = 4400, 4900
OX = 300                     # canvas x of X = 0

WOOD = (214, 176, 146)
STEEL = (182, 186, 194)
DARK = (150, 154, 162)
MAGC = (166, 170, 178)
INK = (20, 20, 24)
DIM = (24, 70, 170)
RED = (200, 30, 30)
GREY = (150, 150, 150)
LIGHT = (225, 225, 225)


def font(sz, bold=False):
    for f in (("arialbd.ttf" if bold else "arial.ttf"), "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(f, sz)
        except OSError:
            pass
    return ImageFont.load_default()


F_T, F_H, F_M, F_S, F_XS = font(54, True), font(34, True), font(26), font(22), font(18)

img = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(img)


class Panel:
    def __init__(self, oy, scale=S, ox=OX):
        self.oy, self.s, self.ox = oy, scale, ox

    def c(self, X, Z):
        return (self.ox + X * self.s, self.oy - Z * self.s)

    def poly(self, pts):
        return [self.c(x, z) for x, z in pts]


def text(xy, s, f=F_S, fill=INK, anchor="la"):
    d.text(xy, s, font=f, fill=fill, anchor=anchor)


def dashed(p0, p1, fill=GREY, width=2, dash=10, gap=7):
    p0, p1 = np.array(p0, float), np.array(p1, float)
    L = np.hypot(*(p1 - p0))
    if L == 0:
        return
    u = (p1 - p0) / L
    t = 0.0
    while t < L:
        a, b = p0 + u * t, p0 + u * min(t + dash, L)
        d.line([tuple(a), tuple(b)], fill=fill, width=width)
        t += dash + gap


def arrow(p, direction, fill=DIM, size=12):
    p = np.array(p, float)
    u = np.array(direction, float) / np.hypot(*direction)
    n = np.array([-u[1], u[0]])
    d.polygon([tuple(p), tuple(p - u * size + n * size * 0.4), tuple(p - u * size - n * size * 0.4)], fill=fill)


def hdim(pn, x0, x1, z, label, zref0=None, zref1=None, f=F_S):
    a, b = pn.c(x0, z), pn.c(x1, z)
    for x, zr in ((x0, zref0), (x1, zref1)):
        if zr is not None:
            d.line([pn.c(x, zr), pn.c(x, z + (1.5 if z > zr else -1.5))], fill=(140, 160, 210), width=1)
    d.line([a, b], fill=DIM, width=2)
    arrow(a, (-1, 0))
    arrow(b, (1, 0))
    text(((a[0] + b[0]) / 2, a[1] - 6), label, f, DIM, "md")


def vdim(pn, x, z0, z1, label, xref=None, left=True, f=F_S):
    a, b = pn.c(x, z0), pn.c(x, z1)
    if xref is not None:
        for z in (z0, z1):
            d.line([pn.c(xref, z), pn.c(x, z)], fill=(140, 160, 210), width=1)
    d.line([a, b], fill=DIM, width=2)
    arrow(a, (0, 1) if z0 < z1 else (0, -1))
    arrow(b, (0, -1) if z0 < z1 else (0, 1))
    text(((a[0] - 10) if left else (a[0] + 10), (a[1] + b[1]) / 2), label, f, DIM, "rm" if left else "lm")


def fillpoly(pn, pts, fill, outline=INK, width=2):
    q = pn.poly(pts)
    if len(q) >= 3:
        d.polygon(q, fill=fill)
        d.line(q + [q[0]], fill=outline, width=width, joint="curve")


def rect(x0, x1, z0, z1):
    return [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]


def arc(cx, cz, r, a0, a1, n=80):
    return [(cx + r * math.cos(math.radians(a)), cz + r * math.sin(math.radians(a))) for a in np.linspace(a0, a1, n)]


def ang_at_z(cx, cz, r, z):
    return math.degrees(math.atan2(z - cz, -math.sqrt(max(r * r - (z - cz) ** 2, 0.0))))


# ------------------------------------------------------------------------------------------------ spec geometry
def side_shapes():
    """List of (polygon in M (X, Z), fill) for the spec side view, in draw order."""
    sh = []
    bar = P["barrel"]["dims"]
    r = bar["dia"] / 2
    sh.append((rect(640.0, bar["crown_X"], -r, r), DARK))
    gt = P["gas_tube"]["dims"]
    sh.append((rect(536.0, 690.0, gt["axis_Z"] - gt["dia"] / 2, gt["axis_Z"] + gt["dia"] / 2), DARK))
    rod = P["cleaning_rod"]
    sh.append((rect(rod["box_M"]["X"][0], rod["box_M"]["X"][1], rod["box_M"]["Z"][0], rod["box_M"]["Z"][1]), DARK))
    order = ["stock", "butt_plate", "sling_swivel_rear", "receiver", "dust_cover", "rear_sight_block",
             "gas_tube_rear_cap", "upper_handguard", "lower_handguard", "handguard_front_band", "gas_block",
             "front_sight_block", "muzzle_brake", "pistol_grip", "trigger_guard", "trigger", "mag_catch"]
    for k in order:
        p = P[k if k != "stock" else "buttstock"]
        fill = WOOD if p["slot"] == "M_AR01_Furniture" else STEEL
        sh.append((p["side_profile_M"], fill))
    sh.append((mag_outline(), MAGC))
    return sh


def mag_outline(z_top=None):
    md = P["magazine_body"]["dims"]
    cx, cz = md["arc_centre_M"]
    zt = md["visible_top_Z"] if z_top is None else z_top
    a_out0 = ang_at_z(cx, cz, md["R_rear_convex"], zt)
    a_in0 = ang_at_z(cx, cz, md["R_front_concave"], zt)
    a = md["angles_deg_about_centre"]
    outer = arc(cx, cz, md["R_rear_convex"], a_out0, a["floor_rear"])
    inner = arc(cx, cz, md["R_front_concave"], a["floor_front"], a_in0)
    return outer + inner


def spec_side_mask(shape, pn):
    m = Image.new("L", shape, 0)
    dm = ImageDraw.Draw(m)
    for pts, _ in side_shapes():
        dm.polygon(pn.poly(pts), fill=255)
    for pts in (P["selector"]["features"][0]["XZ"],):
        dm.polygon(pn.poly(pts), fill=255)
    # see-through holes the spec keeps (FSB window, guard opening) come from the traced holes
    for r in LEFT["silhouette"]:
        if r["kind"] == "hole":
            dm.polygon(pn.poly(r["mm"]), fill=0)
    return np.asarray(m) > 127


def trace_mask(rings_, shape, pn):
    m = Image.new("L", shape, 0)
    dm = ImageDraw.Draw(m)
    for r in rings_:
        if r["kind"] == "outer":
            dm.polygon(pn.poly(r["mm"]), fill=255)
    for r in rings_:
        if r["kind"] == "hole":
            dm.polygon(pn.poly(r["mm"]), fill=0)
    return np.asarray(m) > 127


def iou(a, b):
    return float((a & b).sum() / max((a | b).sum(), 1))


def top_shapes():
    """(polygon in (X, Y) with +Y = gun left = image up, fill) for the spec top view."""
    sh = []
    st = P["buttstock"]["dims"]["width_by_X_TOP"]
    xs = sorted(float(k) for k in st)
    wx = [st[str(int(x))] for x in xs]
    x_w = [10.0] + xs + [231.4]
    w_w = [wx[0]] + wx + [wx[-1]]
    stock = [(x, w / 2) for x, w in zip(x_w, w_w)] + [(x, -w / 2) for x, w in zip(x_w[::-1], w_w[::-1])]
    sh.append((stock, WOOD))
    bp = P["butt_plate"]
    hw = bp["dims"]["width"] / 2
    sh.append((rect(0.0, 14.5, -hw, hw), STEEL))
    rc = P["receiver"]["box_M"]
    sh.append((rect(225.2, 240.9, rc["Y"][0], rc["Y"][1]), STEEL))
    dc = P["dust_cover"]["box_M"]
    sh.append((rect(dc["X"][0], dc["X"][1], dc["Y"][0], dc["Y"][1]), STEEL))
    rs = P["rear_sight_block"]["box_M"]
    sh.append((rect(rs["X"][0], rs["X"][1], rs["Y"][0], rs["Y"][1]), STEEL))
    ch = P["bolt_carrier"]["dims"]["charging_handle"]
    sh.append((rect(ch["X"][0], ch["X"][1], ch["tip_Y"], rc["Y"][0]), STEEL))
    sel = P["selector"]["box_M"]
    sh.append((rect(sel["X"][0], sel["X"][1], sel["Y"][0], sel["Y"][1]), STEEL))
    lh = P["lower_handguard"]["box_M"]
    sh.append((rect(lh["X"][0], lh["X"][1], lh["Y"][0], lh["Y"][1]), WOOD))
    uh = P["upper_handguard"]["box_M"]
    sh.append((rect(uh["X"][0], uh["X"][1], uh["Y"][0], uh["Y"][1]), (200, 160, 128)))
    fb = P["handguard_front_band"]["box_M"]
    sh.append((rect(fb["X"][0], fb["X"][1], fb["Y"][0], fb["Y"][1]), STEEL))
    gt = P["gas_tube"]["dims"]
    sh.append((rect(fb["X"][1], 690.0, -gt["dia"] / 2, gt["dia"] / 2), DARK))
    bar = P["barrel"]["dims"]
    sh.append((rect(640.0, bar["crown_X"], -bar["dia"] / 2, bar["dia"] / 2), DARK))
    gb = P["gas_block"]["box_M"]
    sh.append((rect(gb["X"][0], gb["X"][1], gb["Y"][0], gb["Y"][1]), STEEL))
    fs = P["front_sight_block"]
    sh.append((rect(fs["box_M"]["X"][0], 818.0, fs["box_M"]["Y"][0], fs["box_M"]["Y"][1]), STEEL))
    ears = P["front_sight_ears_post"]["box_M"]
    sh.append((rect(818.0, 840.0, ears["Y"][0], ears["Y"][1]), STEEL))
    sh.append((rect(840.0, 848.8, -8.7, 8.7), STEEL))
    br = P["muzzle_brake"]
    hw = br["dims"]["dia"] / 2
    sh.append((rect(848.8, 880.0, -hw, hw), STEEL))
    return sh


# ------------------------------------------------------------------------------------------------ panels
A = Panel(oy=722)            # Z = 0 (bore) at canvas y 722
B = Panel(oy=1848)
C = Panel(oy=2960)           # Y = 0
Dp = Panel(oy=3470)

# ---- title block
text((60, 40), "Assault Rifle AR-01: design sheet (from rifle_spec.json)", F_T)
km = SPEC["key_dimensions"]
text((60, 112), f"Overall {km['overall_length']:.0f} mm   |   barrel {km['barrel_length']:.0f} (exposed from the receiver "
     f"{km['barrel_exposed_from_receiver_face']})   |   height {km['overall_height_with_mag']} with mag, "
     f"{km['overall_height_without_mag']} without   |   frame M: X from the butt heel, Z from the bore, mm   |   "
     f"Grip origin M ({km['grip']['origin_M'][0]}, {km['grip']['origin_M'][2]})   |   4 px = 1 mm", F_M)

# ================================================================= A: spec side
text((60, 190), "A  SPEC, RIGHT SIDE (as the LEFT-labelled panel): parts drawn from the spec, key dimensions, sockets", F_H)
for pts, fill in side_shapes():
    fillpoly(A, pts, fill)
# see-through openings the spec keeps (FSB ear window, guard opening, gap under the leaf, gas tube / rod gaps)
for r in LEFT["silhouette"]:
    if r["kind"] == "hole":
        q = A.poly(r["mm"])
        d.polygon(q, fill="white")
        d.line(q + [q[0]], fill=INK, width=1)
# features drawn from the spec numbers
rcf ={f["name"]: f for f in P["receiver"]["features"]}
port = rcf["ejection_port"]
d.rectangle([A.c(port["X"][0], port["Z"][1]), A.c(port["X"][1], port["Z"][0])], outline=INK, width=2, fill=(110, 112, 118))
ch = P["bolt_carrier"]["dims"]
d.rectangle([A.c(ch["carrier_visible_X"][0], 14.0), A.c(ch["carrier_visible_X"][1], 6.0)], fill=STEEL, outline=INK, width=1)
c2 = ch["charging_handle"]
d.rectangle([A.c(c2["X"][0], c2["Z"][1]), A.c(c2["X"][1], c2["Z"][0])], fill=STEEL, outline=INK, width=2)
fillpoly(A, P["selector"]["features"][0]["XZ"], STEEL)
fillpoly(A, P["selector"]["features"][1]["XZ"], DARK)
dm = rcf["side_dimple"]
cx_, cz_ = dm["centre_XZ"]
d.ellipse([A.c(cx_ - dm["size"][0] / 2, cz_ + dm["size"][1] / 2), A.c(cx_ + dm["size"][0] / 2, cz_ - dm["size"][1] / 2)],
          outline=INK, width=2)
for x, z in rcf["rivets_right"]["XZ"]:
    d.ellipse([A.c(x - 2.25, z + 2.25), A.c(x + 2.25, z - 2.25)], fill=DARK, outline=INK, width=1)
# handguard side slots (upper guard lower edge) + the lower guard's dips (check C1)
slots = P["upper_handguard"]["features"][0]
dips = P["lower_handguard"]["features"][0]
for x0_, x1_ in slots["X"]:
    fillpoly(A, [(x0_, slots["Z"][0]), (x0_, slots["Z"][1]), (x1_, slots["Z"][1]), (x1_, slots["Z"][0]),
                 (x1_, dips["front_wall_bottom_Z"]), (x1_ - 3.0, slots["Z"][0] - dips["depth"]),
                 (x0_ + 2.0, slots["Z"][0] - dips["depth"])], (60, 50, 44), width=1)
# front sight ear boss + hole (check C10)
th_ = P["front_sight_ears_post"]["dims"]["top_hole"]
hx, hz = th_["XZ"]
# detail pass: a flush disc with a thin raised ring rim (boss_dia, no hole); form stage: boss ring + hole
for dia, fc in ((th_.get("boss_dia", th_.get("boss_ring_dia", 6.0)), STEEL), (th_.get("hole_dia", 0.0), (60, 60, 64)),
                (th_.get("boss_dia", 0.0) - 2 * th_.get("rim_width", 0.0), STEEL)):
    if dia > 0:
        d.ellipse([A.c(hx - dia / 2, hz + dia / 2), A.c(hx + dia / 2, hz - dia / 2)], fill=fc, outline=INK, width=1)
# receiver / trigger-guard top flange ledge seam behind the well (check C9)
led = P["receiver"]["dims"]["ledge_seam_XZ"]
d.line([A.c(*led[0]), A.c(*led[1]), A.c(*led[2])], fill=INK, width=2)
text(A.c(40, -118), "black line under the receiver, X 255-360:", F_XS, INK, "la")
text(A.c(40, -124), "ledge seam over the guard's top flange (to Z -34.8)", F_XS, INK, "la")
# hidden: barrel inside the receiver (chamber face -> crown), mag top inside the well
bar = P["barrel"]["dims"]
for z in (bar["dia"] / 2, -bar["dia"] / 2):
    dashed(A.c(bar["chamber_face_X"], z), A.c(485.3, z), fill=(90, 90, 90), width=1)
dashed(A.c(bar["chamber_face_X"], 7.5), A.c(bar["chamber_face_X"], -7.5), fill=(90, 90, 90), width=1)
mag_hidden = mag_outline(z_top=P["magazine_body"]["dims"]["lips_top_Z"])
q = A.poly(mag_hidden)
for i in range(len(q) - 1):
    if A.oy - q[i][1] > -30.9 * S:
        dashed(q[i], q[i + 1], fill=(90, 90, 90), width=1)
# bore axis
dashed(A.c(-10, 0), A.c(890, 0), fill=(60, 140, 60), width=1, dash=18, gap=8)
text(A.c(-12, 1.5), "bore", F_XS, (60, 140, 60), "rd")
# sight line
sl = km["sight_line"]
dashed(A.c(sl["notch_M"][0] - 40, sl["notch_M"][2]), A.c(sl["post_tip_M"][0] + 20, sl["post_tip_M"][2]), fill=(200, 120, 0), width=1)
# grip axis
pg = P["pistol_grip"]["dims"]
k = math.tan(math.radians(pg["axis_rake_deg_from_vertical"]))
jx, jz = pg["junction_M"]
gx2, gz2 = jx + k * (-140 - jz) * 1.0, -140.0
dashed(A.c(jx + k * (-20 - jz), -20), A.c(gx2 - k * 0, gz2), fill=(160, 60, 160), width=1)
text(A.c(gx2 - 4, gz2 - 2), f"grip axis {pg['axis_rake_deg_from_vertical']:.1f}° from vertical", F_XS, (160, 60, 160), "rt")

# dimension rows above
TOPZ = 49.4
hdim(A, 0, 880, 112, "overall 880.0", 0.0, 0.0, F_M)
hdim(A, bar["chamber_face_X"], bar["crown_X"], 96, "barrel 415.0 (chamber face 433.8 to crown 848.8)", 0, 0)
hdim(A, 0, 231.4, 80, "stock 231.4", 10, 10)
hdim(A, sl["notch_M"][0], sl["post_tip_M"][0], 80, f"sight radius {sl['radius']}", 48, 49.4)
hdim(A, 225.2, 485.3, 64, "receiver 260.1", 10.4, 10.6)
hdim(A, 534.0, 640.9, 64, "upper handguard 106.9", 42.7, 42.7)
hdim(A, 848.8, 880.0, 64, "brake 31.2", 9.8, 9.8)
hdim(A, 485.3, 848.8, -38, "barrel exposed 363.5", -9, -9, F_XS)
hdim(A, 484.0, 640.9, -50, "lower handguard 156.9", -33, -23, F_XS)
hdim(A, 681.0, 737.0, -26, "gas block 56.0", -17, -17, F_XS)
fsx = P["front_sight_block"]["box_M"]["X"]
hdim(A, fsx[0], fsx[1], -26, f"FSB {fsx[1] - fsx[0]:.1f}", -15.8, -15.8, F_XS)
# butt height + bottom dims
vdim(A, -22, -0.1, -109.9, "butt 109.8", xref=0, left=True)
tgb = P["trigger_guard"]["box_M"]
hdim(A, tgb["X"][0], tgb["X"][1], -86, f"trigger guard {tgb['X'][1] - tgb['X'][0]:.1f}", tgb["Z"][0], tgb["Z"][0], F_XS)
md = P["magazine_body"]["dims"]
hdim(A, 369.7, 494.0, -196, "magazine X 369.7-494.0", -183, -137, F_XS)
# height ladder at the right
LX = 905
d.line([A.c(LX, 55), A.c(LX, -190)], fill=DIM, width=2)
lad = [(49.4, "+49.4 front sight ear top"), (48.0, "+48.0 rear leaf top"), (45.5, "+45.5 notch bottom (sight line)"),
       (km["dust_cover_crown_Z"], f"+{km['dust_cover_crown_Z']} dust cover crown"), (24.2, "+24.2 gas tube axis"),
       (10.6, "+10.6 receiver wall top"), (0.0, "0 bore axis"), (-28.8, "-28.8 receiver bottom"),
       (-34.8, "-34.8 guard top flange bottom"), (tgb["Z"][0], f"{tgb['Z'][0]} trigger guard bottom"),
       (-132.7, "-132.7 grip bottom"), (-183.4, "-183.4 magazine bottom")]
last = None
for z, s_ in lad:
    y = A.c(LX, z)[1]
    ty = y if last is None or y - last > 24 else last + 24
    d.line([A.c(LX - 3, z), A.c(LX + 3, z)], fill=DIM, width=2)
    text((A.c(LX + 6, z)[0], ty), s_, F_XS, DIM, "lm")
    last = ty
# angles
text(A.c(882, -14), f"cut {SPEC['key_dimensions']['muzzle_brake']['cut_deg']}°", F_XS, DIM, "la")
text(A.c(120, 24), f"comb {P['buttstock']['dims']['comb_slope_deg']}°", F_XS, DIM, "ma")
text(A.c(150, -80), f"bottom line {P['buttstock']['dims']['bottom_slope_deg']}°", F_XS, DIM, "ma")
# sockets
lab_off = {"Grip": (-6, -4, "rt"), "SupportHand": (0, -6, "mt"), "Trigger": (5, -3, "lt"), "Muzzle": (2, 4, "lb"),
           "MuzzleSeat": (0, -12, "mt"), "Sight": (-4, 4, "rb"), "Mag": (8, 1, "lm"), "MagRockStart": (5, -2, "lt"),
           "MagInsertStart": (8, -3, "lt"), "ShellEject": (0, 9, "mb"), "ChargingHandle": (0, 8, "mb"),
           "Selector": (-6, 3, "rb"), "MagRelease": (5, 0, "lm"), "Shoulder": (5, 2, "lb"), "SlingRear": (5, -2, "lt"),
           "CenterOfMass": (-4, 3, "rb"), "Holster": (-5, 9, "rb")}
for s_ in SPEC["sockets"]["rifle"]:
    if s_["socket"] in ("MagRockStart", "Holster"):
        continue
    x, _, z = s_["M_mm"]
    p = A.c(x, z)
    d.line([(p[0] - 9, p[1]), (p[0] + 9, p[1])], fill=RED, width=3)
    d.line([(p[0], p[1] - 9), (p[0], p[1] + 9)], fill=RED, width=3)
    dx, dz, an = lab_off.get(s_["socket"], (4, 4, "lb"))
    name = s_["socket"] + (" (+MagRockStart 18°)" if s_["socket"] == "Mag" else "")
    name = name + (" = Holster" if s_["socket"] == "CenterOfMass" else "")
    text(A.c(x + dx, z + dz), name, F_XS, RED, an)

# ================================================================= B: traced reference
text((60, 1550), "B  TRACED REFERENCE: LEFT-labelled panel (= true right side) in the M frame, its trace (blue); "
     "RIGHT-labelled panel mirrored, own frame, no fitting (red)", F_H)
sheet = Image.open(SHEET).convert("RGB")
x0, y0, x1, y1 = LEFT["panel_box_sheet_px"]
crop = sheet.crop((x0, y0, x1 + 1, y1 + 1))
s_px = LEFT["px_per_mm"]
u = np.array(LEFT["bore_dir_px"], float)
u /= np.hypot(*u)
n = np.array([u[1], -u[0]])
p0 = np.array(LEFT["origin_px"], float)
# output canvas (cx, cy) -> X = (cx - ox)/S, Z = (oy - cy)/S -> input px = p0 + s (X u + Z n)
bx0, by0, bx1, by1 = 0, 1600, W, 2616
ow, oh = bx1 - bx0, by1 - by0
a_ = s_px * u[0] / S
b_ = -s_px * n[0] / S
c_ = p0[0] + s_px * (u[0] * (bx0 - B.ox) / S + n[0] * (B.oy - by0) / S)
d_ = s_px * u[1] / S
e_ = -s_px * n[1] / S
f_ = p0[1] + s_px * (u[1] * (bx0 - B.ox) / S + n[1] * (B.oy - by0) / S)
warp = crop.transform((ow, oh), Image.AFFINE, (a_, b_, c_, d_, e_, f_), resample=Image.BICUBIC, fillcolor=(255, 255, 255))
warp = Image.blend(warp, Image.new("RGB", warp.size, "white"), 0.45)
img.paste(warp, (bx0, by0))
for r in LEFT["silhouette"]:
    q = B.poly(r["mm"])
    d.line(q + [q[0]], fill=(30, 80, 220), width=2)
for k_, rr in LEFT["parts"].items():
    for r in rr:
        if r["kind"] == "outer" and abs(r["area_px"]) > 40 and k_ not in ("magazine",):
            q = B.poly(r["mm"])
            d.line(q + [q[0]], fill=(90, 140, 240), width=1)
for r in RIGHT["silhouette"]:
    q = B.poly(r["mm"])
    d.line(q + [q[0]], fill=RED, width=1)
ag = MEAS["agreement"]["left_vs_right"]
text((OX, 2632), f"LEFT vs mirrored RIGHT, frame-aligned: silhouette IoU {ag['iou_silhouette_frame_aligned']}, rifle "
     f"without mag {ag['iou_rifle_without_mag_frame_aligned']}, magazine {ag['iou_magazine_frame_aligned']}; boundary "
     f"distance median {ag['boundary_distance_mm']['median']} mm, p90 {ag['boundary_distance_mm']['p90']} mm. The RIGHT-"
     "labelled panel draws the middle 12-16 mm further forward; LEFT wins (TOP sides with it).", F_S, INK)

# ================================================================= C: spec top
text((60, 2700), "C  SPEC, TOP (image up = gun left; the charging handle and selector stand out on the right = down)", F_H)
for pts, fill in top_shapes():
    fillpoly(C, pts, fill, width=2)
dashed(C.c(-10, 0), C.c(890, 0), fill=(60, 140, 60), width=1, dash=18, gap=8)
td = [(25, P["buttstock"]["dims"]["width_by_X_TOP"]["25"], "stock 38.3"), (205, 31.9, "wrist 31.9"),
      (330, P["dust_cover"]["dims"]["outer_width"], "cover 43.5"), (560, P["lower_handguard"]["dims"]["width"], "handguard 42.4"),
      (700, 21.5, "gas block 21.5"), (812, 37.3, "FSB base 37.3"), (870, 20.2, "brake 20.2")]
for x, w_, lbl in td:
    vdim(C, x, w_ / 2, -w_ / 2, lbl, left=False, f=F_XS)
text(C.c(451, -40), "handle tip Y -35.2", F_XS, DIM, "mt")
text(C.c(0, 30), "butt 36.9", F_XS, DIM, "lb")

# ================================================================= D: traced top
text((60, 3220), "D  TRACED TOP silhouette (blue) over the TOP panel (its side bumps at X 236-295 and 353-462 are not real)", F_H)
tx0, ty0, tx1, ty1 = TOPT["panel_box_sheet_px"]
tcrop = sheet.crop((tx0, ty0, tx1 + 1, ty1 + 1))
ts = TOPT["px_per_mm"]
tu = np.array(TOPT["bore_dir_px"], float)
tu /= np.hypot(*tu)
tn = np.array([tu[1], -tu[0]])
tp0 = np.array(TOPT["origin_px"], float)
dx0, dy0, dx1, dy1 = 0, 3270, W, 3670
a_ = ts * tu[0] / S
b_ = -ts * tn[0] / S
c_ = tp0[0] + ts * (tu[0] * (dx0 - Dp.ox) / S + tn[0] * (Dp.oy - dy0) / S)
d_ = ts * tu[1] / S
e_ = -ts * tn[1] / S
f_ = tp0[1] + ts * (tu[1] * (dx0 - Dp.ox) / S + tn[1] * (Dp.oy - dy0) / S)
twarp = tcrop.transform((dx1 - dx0, dy1 - dy0), Image.AFFINE, (a_, b_, c_, d_, e_, f_), resample=Image.BICUBIC,
                        fillcolor=(255, 255, 255))
twarp = Image.blend(twarp, Image.new("RGB", twarp.size, "white"), 0.45)
img.paste(twarp, (dx0, dy0))
for r in TOPT["silhouette"]:
    q = Dp.poly(r["mm"])
    d.line(q + [q[0]], fill=(30, 80, 220), width=2)

# ================================================================= E: magazine
MS = 5.5
text((60, 3720), "E  MAGAZINE SM_AR01_Mag (5.5 px = 1 mm): concentric arcs, ribs, floor plate, origin = front-lug hook, "
     "reload rock start 18°", F_H)
cx, cz = md["arc_centre_M"]
E = Panel(oy=3780 - 6 * MS, scale=MS, ox=120 - 350 * MS)
hook = SPEC["sockets"]["mag"][0]["M_mm_seated"]
outline_full = mag_outline(z_top=md["lips_top_Z"])
# ghost at MagRockStart: rotate about the hook by +18 deg (base swings forward)
th = math.radians(18.0)


def rot_hook(p):
    x, z = p[0] - hook[0], p[1] - hook[2]
    return (hook[0] + x * math.cos(th) - z * math.sin(th), hook[2] + x * math.sin(th) + z * math.cos(th))


ghost = [rot_hook(p) for p in outline_full]
qg = E.poly(ghost)
for i in range(len(qg)):
    dashed(qg[i], qg[(i + 1) % len(qg)], fill=(120, 120, 200), width=2, dash=8, gap=6)
fillpoly(E, outline_full, MAGC)
# receiver bottom line and visible top
dashed(E.c(355, -28.8), E.c(500, -28.8), fill=(90, 90, 90), width=2)
text(E.c(500, -28.8), " receiver bottom -28.8", F_XS, (90, 90, 90), "lm")
# ribs: centre lines at fractions of the width from the rear edge
rb = P["magazine_ribs"]["dims"]
a = md["angles_deg_about_centre"]
wid = md["width_front_to_rear"]
for f in rb["rib_centres_fraction_from_rear_edge"] + [rb["front_rib_fraction"]]:
    rr = md["R_rear_convex"] - f * wid
    a0 = ang_at_z(cx, cz, rr, rb["top_tips_Z_seated"])
    a1 = a["floor_rear"] - 15.0 / rr * 180 / math.pi - 2.0
    q = E.poly(arc(cx, cz, rr, a0, a1, 60))
    d.line(q, fill=(235, 235, 240), width=int(2.5 * MS * (0.6 if f == rb["front_rib_fraction"] else 1.0)))
    d.line(q, fill=INK, width=1)
# top reinforcing plates (seated Z -38..-12, width fraction 0.08-0.80 from the rear edge; c4)
tp = P["magazine_top_plates"]["dims"]
fr0, fr1 = tp["width_fraction_from_rear_edge"]
r_a, r_b = md["R_rear_convex"] - fr0 * wid, md["R_rear_convex"] - fr1 * wid
za, zb = tp["Z_seated"]
plate = arc(cx, cz, r_a, ang_at_z(cx, cz, r_a, zb), ang_at_z(cx, cz, r_a, za), 12) + \
    arc(cx, cz, r_b, ang_at_z(cx, cz, r_b, za), ang_at_z(cx, cz, r_b, zb), 12)
fillpoly(E, plate, (190, 194, 202), width=2)
text(E.c(398, -22), "top plate (seated Z -38..-12)", F_XS, INK, "la")
# radii to the centre (shortened), labels
for rr, lbl, aa in ((md["R_rear_convex"], f"R {md['R_rear_convex']} (rear, convex)", -150.0),
                    (md["R_front_concave"], f"R {md['R_front_concave']} (front, concave)", -140.0)):
    p_on = (cx + rr * math.cos(math.radians(aa)), cz + rr * math.sin(math.radians(aa)))
    p_in = (cx + (rr - 45) * math.cos(math.radians(aa)), cz + (rr - 45) * math.sin(math.radians(aa)))
    d.line([E.c(*p_in), E.c(*p_on)], fill=DIM, width=2)
    arrow(E.c(*p_on), (E.c(*p_on)[0] - E.c(*p_in)[0], E.c(*p_on)[1] - E.c(*p_in)[1]))
# floor plate + width dims
fr, ff = P["magazine_floor_plate"]["dims"]["rear_corner_M"], P["magazine_floor_plate"]["dims"]["front_corner_M"]
text(E.c((fr[0] + ff[0]) / 2 + 12, (fr[1] + ff[1]) / 2 - 6), f"floor plate {P['magazine_floor_plate']['dims']['corner_to_corner']}"
     f" corner to corner", F_S, DIM, "lt")
text(E.c(372, -40), f"width {wid} (radial)", F_S, DIM, "la")
text(E.c(372, -52), f"R rear (convex) {md['R_rear_convex']}, R front (concave) {md['R_front_concave']}", F_S, DIM, "la")
text(E.c(372, -58), f"arc centre M ({md['arc_centre_M'][0]}, {md['arc_centre_M'][1]}); radius leaders run toward it", F_S, DIM, "la")
text(E.c(372, -46), f"sweep {md['sweep_deg']}°, centre-arc length {md['length_along_centre_arc']}", F_S, DIM, "la")
# origin + sockets
for s_ in SPEC["sockets"]["mag"]:
    if s_["socket"] == "CenterOfMass":
        continue
    x, _, z = s_["M_mm_seated"]
    p = E.c(x, z)
    d.line([(p[0] - 10, p[1]), (p[0] + 10, p[1])], fill=RED, width=3)
    d.line([(p[0], p[1] - 10), (p[0], p[1] + 10)], fill=RED, width=3)
    text((p[0] + 12, p[1] + 4), s_["socket"] + {"Mag": " (origin, rock pivot)", "HandReload": " + CenterOfMass (left face)"}.get(s_["socket"], ""), F_S, RED, "la")
text(E.c(*rot_hook((470, -175))), "MagRockStart (18°)", F_S, (120, 120, 200), "la")
# section (front view) to the right
sx, sy = 1400, 3820
T = md["thickness_Y"]
h_sec = (md["lips_top_Z"] - (-183.4)) * MS * 0.5
d.rectangle([sx, sy, sx + T * MS, sy + h_sec], fill=MAGC, outline=INK, width=2)
for yy in np.linspace(sy + 60, sy + h_sec - 60, 2):
    pass
d.line([sx + T * MS / 2 - 6, sy + 30, sx + T * MS / 2 - 6, sy + h_sec - 30], fill=INK, width=1)
d.line([sx + T * MS / 2 + 6, sy + 30, sx + T * MS / 2 + 6, sy + h_sec - 30], fill=INK, width=1)
d.line([sx, sy + h_sec + 30, sx + T * MS, sy + h_sec + 30], fill=DIM, width=2)
arrow((sx, sy + h_sec + 30), (-1, 0))
arrow((sx + T * MS, sy + h_sec + 30), (1, 0))
text((sx + T * MS / 2, sy + h_sec + 36), f"thickness {T:.0f}", F_S, DIM, "ma")
text((sx - 10, sy - 14), "front spine (c5), height at 0.5x", F_XS, INK, "lb")
text((sx, sy + h_sec + 80), "not measurable on the sheet (c5 reads ~18-20):", F_XS, INK, "la")
text((sx, sy + h_sec + 104), "real-pattern norm 28-30, 28 chosen (R5)", F_XS, INK, "la")

# ================================================================= legend + QA (bottom right)
QX, QY = 1950, 3790
sh_ = (W, H)
mA = spec_side_mask((W, H), A)
mT = trace_mask(LEFT["silhouette"], (W, H), A)
iou_side = iou(mA, mT)
mC = Image.new("L", (W, H), 0)
dmc = ImageDraw.Draw(mC)
for pts, _ in top_shapes():
    dmc.polygon(C.poly(pts), fill=255)
mC = np.asarray(mC) > 127
mTop = trace_mask(TOPT["silhouette"], (W, H), C)
iou_top = iou(mC, mTop)
lines = [
    ("QA (spec drawing vs traced silhouettes, rasterised at 4 px/mm)", F_H, INK),
    (f"side: IoU {iou_side:.3f} (spec panel A vs the LEFT-labelled trace)", F_M, INK),
    (f"top:  IoU {iou_top:.3f} (spec boxes in panel C vs the TOP trace; TOP's fake side bumps and", F_M, INK),
    ("       its drop shadow are outside the spec)", F_M, INK),
    ("", F_S, INK),
    ("Key decisions (RIFLE_STUDY.md, rifle_spec.json resolutions R1-R29)", F_H, INK),
    ("- LEFT-labelled panel = TRUE RIGHT side (handed features); RIGHT-labelled = true left + a copied selector", F_S, INK),
    ("- scale set by us: 880.0 overall, barrel 415.0; the sheet ruler is mislabelled", F_S, INK),
    (f"- dust cover crown +{km['dust_cover_crown_Z']} (not 46.9: a sliver ring); upper handguard 106.9 (not 153.8)", F_S, INK),
    ("- barrel 15.0, rod 4.0, magazine thickness 28.0 (real-pattern norm; not measurable on the sheet)", F_S, INK),
    (f"- check fixes: leaf overhangs the cover (notch X {km['sight_line']['notch_M'][0]}, radius {km['sight_line']['radius']}); "
     f"FSB from X {fsx[0]}; guard bottom {tgb['Z'][0]}", F_S, INK),
    ("- handguard side slots X 543-571 / 595-623; guard top flange; ear boss; cross-slot butt screws", F_S, INK),
    ("- frames: M here; Blender B = M - Grip (pure translation); Unreal cm = (Bx, -By, Bz)/10", F_S, INK),
    ("- sockets: GUN_BUILDING_STUDY 5.3 names; 17 rifle + 5 magazine", F_S, INK),
    ("", F_S, INK),
    ("Legend", F_H, INK),
    ("wood / steel / magazine fills; red crosshair = socket; blue = dimension; dashed grey = hidden", F_S, INK),
    ("green dash = bore axis; orange dash = sight line; violet dash = grip axis", F_S, INK),
]
y = QY
for s_, f, c in lines:
    text((QX, y), s_, f, c)
    y += 46 if f in (F_H, F_M) else 34
for i, (c, lbl) in enumerate(((WOOD, "wood"), (STEEL, "steel"), (MAGC, "magazine"))):
    d.rectangle([QX + i * 260, y + 6, QX + i * 260 + 40, y + 40], fill=c, outline=INK)
    text((QX + i * 260 + 50, y + 8), lbl, F_S)
text((60, H - 40), f"Generated by WorkFiles/guns/rifle/tools/design_sheet.py from rifle_spec.json "
     f"({SPEC['meta']['date']}). Reference: {SPEC['meta']['reference']}.", F_XS, GREY)

img.save(OUT, optimize=True)
print(f"wrote {OUT.relative_to(ROOT)}  side IoU {iou_side:.4f}  top IoU {iou_top:.4f}")
