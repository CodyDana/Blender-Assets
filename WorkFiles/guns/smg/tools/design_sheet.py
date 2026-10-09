"""Draw WorkFiles/guns/smg/SMG_DESIGN_SHEET.png from smg_spec.json (+ the traced reference beside it).

    py -3 -B WorkFiles/guns/smg/tools/design_sheet.py

Panels (frame M: X from the butt-pad rear toward the muzzle, Z up from the measurer's datum, 4 px per mm):
  A  SPEC, LEFT SIDE, stock extended (drawn muzzle-right; the LEFT panel is muzzle-left): every part from its spec
     outline or parametric numbers, key dimensions, height ladder, sockets, bore / sight / grip axes.
  B  TRACED REFERENCE: the LEFT panel warped into frame M, its trace (blue) and the RIGHT panel's trace mirrored into
     its own frame (red), no fitting.
  C  SPEC, TOP (image up = gun left): extended stock (filled) and the folded stock (dashed) about the right-rear axle.
  D  TRACED TOP silhouette over the TOP panel (the stock zone is oblique on the sheet).
  E  SPEC, STOCK FOLDED, seen from the right (mirrored into frame M): the folded stock over the receiver, the port, the
     catch and the folded length.
  F  MAGAZINE SM_SMG01_Mag (6 px/mm, its own frame): side with the ladder, floor plate, catch notch, sockets, the
     straight reload path; front section (thickness).
QA numbers (IoU of the spec drawing vs the traced silhouettes) are printed in the legend block.
Needs numpy + Pillow. ROOT comes from this file's location.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve()
SMG = HERE.parents[1]
ROOT = HERE.parents[4]
SPEC = json.loads((SMG / "smg_spec.json").read_text(encoding="utf-8"))
MEAS = json.loads((SMG / "smg_measured.json").read_text(encoding="utf-8"))
LEFT = json.loads((SMG / "trace" / "LEFT_outline.json").read_text(encoding="utf-8"))
RIGHT = json.loads((SMG / "trace" / "RIGHT_outline.json").read_text(encoding="utf-8"))
TOPT = json.loads((SMG / "trace" / "TOP_outline.json").read_text(encoding="utf-8"))
SHEET = ROOT / "References" / "Guns" / "SMG" / "smg_sheetA.webp"
OUT = SMG / "SMG_DESIGN_SHEET.png"

P = {p["id"]: p for p in SPEC["parts"]}
KD = SPEC["key_dimensions"]
FOLD = SPEC["fold"]
S = 4.0
W, H = 3700, 8000
OX = 330

POLY = (150, 156, 166)
POLY2 = (128, 134, 144)
STEEL = (196, 200, 208)
DARK = (92, 96, 104)
MAGC = (172, 162, 150)
RUB = (110, 110, 116)
INK = (20, 20, 24)
DIM = (24, 70, 170)
RED = (200, 30, 30)
GREY = (150, 150, 150)
GREEN = (40, 140, 60)
ORANGE = (210, 120, 0)
VIOLET = (160, 60, 160)


def font(sz, bold=False):
    for f in (("arialbd.ttf" if bold else "arial.ttf"), "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(f, sz)
        except OSError:
            pass
    return ImageFont.load_default()


F_T, F_H, F_M, F_S, F_XS = font(52, True), font(32, True), font(25), font(21), font(17)
img = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(img)


class Panel:
    def __init__(self, oy, scale=S, ox=OX, flip_x=False):
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


def dashed_poly(q, fill, width=2):
    for i in range(len(q)):
        dashed(q[i], q[(i + 1) % len(q)], fill=fill, width=width, dash=9, gap=6)


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


def fillpoly(pn, pts, fill, outline=INK, width=2, draw=None):
    q = pn.poly(pts)
    if len(q) >= 3:
        (draw or d).polygon(q, fill=fill)
        if draw is None:
            d.line(q + [q[0]], fill=outline, width=width, joint="curve")


def rect(x0, x1, z0, z1):
    return [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]


def circle(cx, cz, r, n=48):
    return [(cx + r * math.cos(t), cz + r * math.sin(t)) for t in np.linspace(0, 2 * math.pi, n, endpoint=False)]


def stadium(x0, x1, zc, h, n=12):
    r = h / 2
    pts = [(x1 - r + r * math.cos(t), zc + r * math.sin(t)) for t in np.linspace(-math.pi / 2, math.pi / 2, n)]
    pts += [(x0 + r + r * math.cos(t), zc + r * math.sin(t)) for t in np.linspace(math.pi / 2, 3 * math.pi / 2, n)]
    return pts


# ------------------------------------------------------------------------------------------------ spec geometry
MF = SPEC["frames"]["mag"]
MO = np.array(MF["Mag_in_M"], float)
UZ = np.array(MF["z_axis_in_M"], float)
UX = np.array(MF["x_axis_in_M"], float)
MD = P["magazine_body"]["dims"]


def mag_xz(xl, zl):
    p = MO + xl * UX + zl * UZ
    return (p[0], p[2])


def mag_outline(z_top=None):
    fa, zt, zf = MD["foreaft"] / 2, (MD["top_along_axis"] if z_top is None else z_top), MD["floor_along_axis"]
    return [mag_xz(-fa, zt), mag_xz(fa, zt), mag_xz(fa, zf + 7.5), mag_xz(fa + 1.0, zf + 6.0), mag_xz(fa + 1.0, zf),
            mag_xz(-fa - 0.6, zf), mag_xz(-fa - 0.6, zf + 6.0), mag_xz(-fa, zf + 7.5)]


def mag_visible_outline():
    """the magazine up to just inside the well (drawn under the magwell, which covers the overlap)."""
    return mag_outline(z_top=12.0)


LIP = P["magwell"]["dims"]


def below_lip_poly():
    (xf, zf_), (xr, zr_) = LIP["lip_lower_edge_front_XZ"], LIP["lip_lower_edge_rear_XZ"]
    s_ = (zf_ - zr_) / (xf - xr)
    zat = lambda x: zr_ + s_ * (x - xr)
    return [(380.0, zat(380.0)), (620.0, zat(620.0)), (620.0, -300.0), (380.0, -300.0)]


STEEL_SLOT = "M_SMG01_Metal"


def part_fill(p):
    if p["slot"].startswith(STEEL_SLOT):
        return STEEL
    if p["finish"] == "rubber_pad":
        return RUB
    return POLY


SIDE_ORDER = ["stock_frame", "butt_pad", "stock_hinge", "end_block", "upper_receiver", "lower_receiver", "magwell",
              "trigger_guard", "pistol_grip", "top_rail", "lower_rail", "sight_rear", "sight_front", "barrel",
              "muzzle_device", "trigger", "mag_release"]


def profiles(pid):
    sp = P[pid].get("side_profile_M")
    if not sp:
        return []
    return sp if isinstance(sp[0][0], list) else [sp]


def side_shapes(include_stock=True):
    sh = [(mag_visible_outline(), MAGC)]
    for k in SIDE_ORDER:
        if not include_stock and k in ("stock_frame", "butt_pad", "stock_hinge"):
            continue
        for pr in profiles(k):
            # the drawn lever's outline is the slot / guard-leg area (polymer); the built paddle is painted over it
            sh.append((pr, POLY if k == "mag_release" else part_fill(P[k])))
    return sh


def holes_M(view=LEFT):
    return [r["mm"] for r in view["silhouette"] if r["kind"] == "hole"]


def mask_from(shapes, shape_wh, pn, holes=()):
    m = Image.new("L", shape_wh, 0)
    dm = ImageDraw.Draw(m)
    for pts, _ in shapes:
        dm.polygon(pn.poly(pts), fill=255)
    for h in holes:
        dm.polygon(pn.poly(h), fill=0)
    return np.asarray(m) > 127


def trace_mask(rings_, shape_wh, pn, xmin=None):
    m = Image.new("L", shape_wh, 0)
    dm = ImageDraw.Draw(m)
    for r in rings_:
        if r["kind"] == "outer":
            dm.polygon(pn.poly(r["mm"]), fill=255)
    for r in rings_:
        if r["kind"] == "hole":
            dm.polygon(pn.poly(r["mm"]), fill=0)
    a = np.asarray(m) > 127
    if xmin is not None:
        a = a.copy()
        a[:, : int(pn.c(xmin, 0)[0])] = False
    return a


def iou(a, b):
    return float((a & b).sum() / max((a | b).sum(), 1))


# ================================================================== title
text((60, 36), "Compact SMG SM-01 (SMG01): design sheet (from smg_spec.json)", F_T)
text((60, 104), f"Overall {KD['overall_length']:.0f} mm   |   height {KD['height_with_mag']} with mag, "
     f"{KD['height_without_mag']} without   |   folded {FOLD['folded_length']}   |   bore Z_M {KD['bore_Z_M']}   |   "
     f"Grip origin M ({KD['grip']['origin_M'][0]}, {KD['grip']['origin_M'][2]})   |   frame M: X from the butt rear, "
     "Z up, mm   |   4 px = 1 mm", F_M)

# ================================================================== A: spec side
A = Panel(oy=740)
text((60, 190), "A  SPEC, LEFT SIDE, stock extended (frame M, muzzle right): parts, key dimensions, sockets", F_H)
for pts, fill in side_shapes():
    fillpoly(A, pts, fill)
for h in holes_M():
    q = A.poly(h)
    d.polygon(q, fill="white")
    d.line(q + [q[0]], fill=INK, width=1)
up = P["upper_receiver"]
uf = {f["name"]: f for f in up["features"]}
# vents (left), long vent, charging slot hidden under the arm
fv = uf["forward_long_vent_left"]
fillpoly(A, stadium(fv["X"][0], fv["X"][1], (fv["Z"][0] + fv["Z"][1]) / 2, fv["Z"][1] - fv["Z"][0]), DARK, width=1)
lv = uf["lower_vents_left"]
for x0, x1 in lv["X"]:
    fillpoly(A, stadium(x0, x1, lv["Z_centre"], lv["height"]), DARK, width=1)
cs = uf["charging_slot"]
fillpoly(A, rect(cs["X"][0], P["charging_handle"]["dims"]["arm_rear_block"]["X"][0], cs["Z"][0], cs["Z"][1]), DARK, width=1)
dashed_poly(A.poly(rect(cs["X"][0], cs["X"][1], cs["Z"][0], cs["Z"][1])), (60, 60, 60), 1)
ch = P["charging_handle"]["dims"]
fillpoly(A, rect(*ch["arm_rear_block"]["X"], *ch["arm_rear_block"]["Z"]), STEEL)
fillpoly(A, rect(*ch["arm_rod"]["X"], *ch["arm_rod"]["Z"]), STEEL)
fillpoly(A, circle(ch["knob_centre_XZ"][0], ch["knob_centre_XZ"][1], ch["knob_dia"] / 2), STEEL)
# pins, selector, eyelet
for pn_ in P["pins_fasteners"]["dims"]["list"]:
    if "left" in pn_["side"] or pn_["side"] == "both":
        x, z = pn_["XZ"]
        fillpoly(A, circle(x, z, pn_["dia"] / 2, 24), STEEL, width=1)
# lower-receiver face features (check fix C7): oblong recess, seam boss
for f_ in P["lower_receiver"]["features"]:
    if f_["name"] == "oblong_recess":
        fillpoly(A, stadium(f_["X"][0], f_["X"][1], (f_["Z"][0] + f_["Z"][1]) / 2, f_["Z"][1] - f_["Z"][0]), DARK, width=1)
    if f_["name"] == "seam_boss":
        fillpoly(A, circle(f_["XZ"][0], f_["XZ"][1], f_["dia"] / 2, 32), (120, 122, 128), width=1)
for pn_ in P["pins_fasteners"]["dims"]["list"]:
    if pn_["name"] == "seam boss pin":
        fillpoly(A, circle(pn_["XZ"][0], pn_["XZ"][1], pn_["dia"] / 2, 24), STEEL, width=1)
# magazine release paddle (built), its drawn lever (dashed), pivot, nose and the magwell rear wall's outer face
mr = P["mag_release"]["dims"]
dashed_poly(A.poly(rect(mr["drawn_lever"]["X"][0], mr["drawn_lever"]["X"][1], mr["drawn_lever"]["Z"][0],
                        mr["drawn_lever"]["Z"][1])), (40, 160, 200), 1)
fillpoly(A, rect(mr["rear_face_X"], mr["front_face_X"], mr["bottom_Z"], mr["top_Z"]), STEEL, width=1)
pvx, pvz = mr["pivot_XZ"]
nx_, nz_ = mr["nose_tip_XZ_seated"]
dashed_poly(A.poly([(pvx - 1.0, pvz), (pvx + 1.0, pvz), (nx_, nz_ + 1.0), (nx_, nz_ - 1.0)]), (90, 90, 90), 1)
fillpoly(A, circle(pvx, pvz, mr["pivot_boss_dia"] / 2, 16), STEEL, width=1)
fillpoly(A, circle(pvx, pvz, mr["pin_dia"] / 2, 12), INK, width=1)
mwr = P["magwell"]["dims"]["rear_wall"]
k_w, c_w = [float(v) for v in mwr["outer_face_line_XZ"].split("(")[0].replace("X =", "").replace("Z +", "").split()]
dashed(A.c(k_w * -20 + c_w, -20), A.c(k_w * -83 + c_w, -83), fill=(90, 90, 90), width=1)
text(A.c(mr["front_face_X"] + 1.0, mr["bottom_Z"] - 2.0), "paddle (built; drawn lever dashed)", F_XS, DIM, "lt")
# trigger pivot
tpx, tpz = P["trigger"]["dims"]["pivot_XZ"]
fillpoly(A, circle(tpx, tpz, 1.2, 12), INK, width=1)
sd = P["selector"]["dims"]
px_, pz_ = sd["pivot_XZ"]
tx_, tz_ = sd["blade_tip_XZ_left"]
ang = math.atan2(tz_ - pz_, tx_ - px_)
nrm = (-math.sin(ang), math.cos(ang))
blade = [(px_ + nrm[0] * 6, pz_ + nrm[1] * 6), (tx_ + nrm[0] * 3, tz_ + nrm[1] * 3), (tx_ - nrm[0] * 3, tz_ - nrm[1] * 3),
         (px_ - nrm[0] * 6, pz_ - nrm[1] * 6)]
fillpoly(A, circle(px_, pz_, sd["hub_dia"] / 2), STEEL)
fillpoly(A, blade, STEEL)
# rail slot ticks (cut slots), sight pivots, aperture and post
rd = P["top_rail"]["dims"]
for x in rd["cut_slot_centres_X"]:
    fillpoly(A, rect(x - 2.62, x + 2.62, rd["top_Z"] - 3.0, rd["top_Z"]), (235, 235, 240), width=1)
for x in P["lower_rail"]["dims"]["slot_centres_X"]:
    z = P["lower_rail"]["dims"]["bottom_Z"]
    fillpoly(A, rect(x - 2.62, x + 2.62, z, z + 3.0), (235, 235, 240), width=1)
ap = P["sight_rear"]["dims"]["aperture_centre_XZ"]
fillpoly(A, circle(ap[0], ap[1], 5.0, 24), STEEL, width=1)
fillpoly(A, circle(ap[0], ap[1], 1.0, 12), INK, width=1)
pt = P["sight_front"]["dims"]["post_tip_XZ"]
fillpoly(A, rect(pt[0] - 0.93, pt[0] + 0.93, P["top_rail"]["dims"]["top_Z"] + 8, pt[1]), DARK, width=1)
# sight pivots and the folded leaves (dashed, check fix C6)
for sk, sgn in (("sight_rear", 1.0), ("sight_front", -1.0)):
    sdm = P[sk]["dims"]
    qx, qz = sdm["pivot_XZ"]
    hx = sdm.get("leaf_head_X", sdm.get("head_X"))
    top_z = sdm.get("top_Z", sdm.get("ear_top_Z"))
    leaf = rect(hx[0], hx[1], qz, top_z)
    if sgn > 0:          # +90 about Y: (dx, dz) -> (dz, -dx)
        fold_ = [(qx + (z - qz), qz - (x - qx)) for x, z in leaf]
    else:                # -90 about Y: (dx, dz) -> (-dz, dx)
        fold_ = [(qx - (z - qz), qz + (x - qx)) for x, z in leaf]
    dashed_poly(A.poly(fold_), (200, 60, 60), 1)
    fillpoly(A, circle(qx, qz, 1.5, 12), INK, width=1)
text(A.c(P["sight_rear"]["dims"]["pivot_XZ"][0] + 4, P["sight_rear"]["dims"]["folded_max_Z"] + 2.0),
     f"rear folded <= Z {SPEC['parts'][[q['id'] for q in SPEC['parts']].index('sight_rear')]['dims']['folded_max_Z']}",
     F_XS, (200, 60, 60), "lb")
# stock holes, magazine ladder (visible part), floor plate line
for h in P["stock_frame"]["dims"]["through_holes"]:
    x, z = h["XZ"]
    fillpoly(A, circle(x, z, h["dia"] / 2, 24), "white", width=1)
lad = MD["ladder"]


def z_to_along(zM):
    return (zM - MO[2]) / UZ[2]


for side in (-1, 1):
    xa = side * (lad["rib_between"] / 2)
    xb = side * (lad["rib_between"] / 2 + lad["channel_width"])
    za, zb = z_to_along(lad["channel_top_Z"]), z_to_along(lad["channel_bottom_Z"])
    fillpoly(A, [mag_xz(xa, za), mag_xz(xb, za), mag_xz(xb, zb), mag_xz(xa, zb)], (140, 132, 122), width=1)
    for zt in lad["tie_Z"]:
        zz = z_to_along(zt)
        fillpoly(A, [mag_xz(xa, zz + 1.2), mag_xz(xb, zz + 1.2), mag_xz(xb, zz - 1.2), mag_xz(xa, zz - 1.2)], MAGC, width=1)
# hidden: barrel inside the receiver, bolt at rest and back, mag top inside the well, port (right side) dashed
bar = P["barrel"]["dims"]
bz = KD["bore_Z_M"]
for z in (bz + bar["hidden_od"] / 2, bz - bar["hidden_od"] / 2):
    dashed(A.c(bar["breech_X"], z), A.c(621.9, z), fill=(80, 80, 80), width=1)
dashed(A.c(bar["breech_X"], bz + 8.85), A.c(bar["breech_X"], bz - 8.85), fill=(80, 80, 80), width=1)
bo = P["bolt"]["box_M"]
dashed_poly(A.poly(rect(bo["X"][0], bo["X"][1], bo["Z"][0], bo["Z"][1])), (110, 110, 110), 1)
dashed_poly(A.poly(rect(bo["X"][0] - 75, bo["X"][1] - 75, bo["Z"][0], bo["Z"][1])), (190, 150, 150), 1)
dashed_poly(A.poly(mag_outline()), (90, 90, 90), 1)
pe = P["ejection_port_and_catch"]["dims"]
dashed_poly(A.poly(rect(pe["port_X"][0], pe["port_X"][1], pe["port_Z"][0], pe["port_Z"][1])), RED, 2)
text(A.c(pe["port_X"][0], pe["port_Z"][1] + 3.5), "port (right side)", F_XS, RED, "lb")
# axes
dashed(A.c(-15, bz), A.c(705, bz), fill=GREEN, width=1, dash=18, gap=8)
text(A.c(-17, bz + 1.5), "bore", F_XS, GREEN, "rd")
sl = ap[1]
dashed(A.c(ap[0] - 30, sl), A.c(pt[0] + 20, sl), fill=ORANGE, width=1)
gr = KD["grip"]
k = math.tan(math.radians(gr["axis_rake_deg"]))
jx, jz = gr["junction_M"]
dashed(A.c(jx + k * (-20 - jz), -20), A.c(jx + k * (-175 - jz), -175), fill=VIOLET, width=1)
text(A.c(jx + k * (-178 - jz) - 4, -178), f"grip axis {gr['axis_rake_deg']}° from vertical", F_XS, VIOLET, "rt")
gx, gz = gr["origin_M"][0], gr["origin_M"][2]
# dimension rows
hdim(A, 0, 690, 112, "overall 690.0", 0.0, 0.0, F_M)
hdim(A, ap[0], pt[0], 98, f"sight radius {KD['sight_radius']}", ap[1], pt[1])
hdim(A, 292.8, 621.9, 84, f"receiver {KD['receiver_length']}", 40, 40)
hdim(A, 0, FOLD["axis_M"][0], 84, f"stock to hinge axis {KD['stock']['length_hinge_to_butt']}", 26, 14)
hdim(A, rd["toothed_zone_X"][0], rd["toothed_zone_X"][1], 66, f"toothed zone: {rd['teeth_built']} teeth, 10.01 pitch",
     rd["top_Z"], rd["top_Z"], F_XS)
hdim(A, bar["breech_X"], bar["crown_X"], -56, f"barrel {bar['length']:.0f} (breech {bar['breech_X']:.0f} to crown "
     f"{bar['crown_X']:.0f}, hidden)", None, None, F_XS)
hdim(A, 644.1, 690, -24, "device 46.0", -11, -11, F_XS)
tg = P["trigger_guard"]["box_M"]
hdim(A, tg["X"][0], tg["X"][1], -132, f"guard {P['trigger_guard']['dims']['length']}", tg["Z"][0], tg["Z"][0], F_XS)
vdim(A, -22, PAD_Z0 := P["butt_pad"]["box_M"]["Z"][0], P["butt_pad"]["box_M"]["Z"][1],
     f"pad {P['butt_pad']['dims']['height']}", xref=0, left=True)
hdim(A, 409.4, 409.4 - 90.5, -70, "", None, None)
text(A.c(364, -66), f"reach {gr['trigger_reach']}", F_XS, DIM, "md")
mvo = P["magazine_body"]["box_M"]
hdim(A, mvo["X"][0], mvo["X"][1], -268, f"magazine X {mvo['X'][0]}-{mvo['X'][1]}, rake {MD['rake_deg']}°, fore-aft "
     f"{MD['foreaft']}", -254, -254, F_XS)
# height ladder at the right
LX = 712
d.line([A.c(LX, 90), A.c(LX, -258)], fill=DIM, width=2)
ladr = [(84.3, "+84.3 sight tops"), (ap[1], f"+{ap[1]} sight line (aperture / post tip)"), (rd["top_Z"], f"+{rd['top_Z']} rail top"),
        (rd["underside_Z"], f"+{rd['underside_Z']} receiver top"), (bz, f"+{bz} bore"),
        (-18.5, "-18.5 upper/lower seam"), (-41.1, "-41.1 lower rail bottom"), (tg["Z"][0], f"{tg['Z'][0]} guard bottom"),
        (gz, f"{gz} Grip origin"), (-167.8, "-167.8 grip bottom"), (-253.9, "-253.9 magazine floor")]
last = None
for z, s_ in sorted(ladr, key=lambda t: -t[0]):
    y = A.c(LX, z)[1]
    ty = y if last is None or y - last > 22 else last + 22
    d.line([A.c(LX - 3, z), A.c(LX + 3, z)], fill=DIM, width=2)
    text((A.c(LX + 6, z)[0], ty), s_, F_XS, DIM, "lm")
    last = ty
# sockets
lab = {"Grip": (-6, -3, "rt"), "SupportHand": (5, -3, "lt"), "Trigger": (-3, 8, "rb"), "Muzzle": (2, 6, "lb"),
       "MuzzleSeat": (0, -16, "mt"), "Sight": (-4, 6, "rb"), "SightFront": (4, 6, "lb"), "Mag": (6, 1, "lm"),
       "MagInsertStart": (6, -2, "lt"), "ShellEject": (0, 8, "mb"), "ChargingHandle": (4, 12, "lb"),
       "Selector": (-6, -2, "rt"), "MagRelease": (2, -12, "lt"), "Rail_Top": (0, 10, "mb"), "Rail_Bottom": (0, -9, "mt"),
       "Stock": (4, 4, "lb"), "Shoulder": (5, 2, "lb"), "SlingFront": (4, 4, "lb"), "SlingRear": (5, -3, "lt"),
       "CenterOfMass": (-4, 4, "rb")}
for s_ in SPEC["sockets"]["gun"]:
    if s_["socket"] == "Holster":
        continue
    x, _, z = s_["M_mm"]
    p = A.c(x, z)
    d.line([(p[0] - 9, p[1]), (p[0] + 9, p[1])], fill=RED, width=3)
    d.line([(p[0], p[1] - 9), (p[0], p[1] + 9)], fill=RED, width=3)
    dx, dz, an = lab.get(s_["socket"], (4, 4, "lb"))
    nm = s_["socket"] + (" = Holster (prov.)" if s_["socket"] == "CenterOfMass" else "")
    text(A.c(x + dx, z + dz), nm, F_XS, RED, an)
# mag insert path
mi = next(s for s in SPEC["sockets"]["gun"] if s["socket"] == "MagInsertStart")["M_mm"]
dashed(A.c(MO[0], MO[2]), A.c(mi[0], mi[2]), fill=RED, width=1)

# ================================================================== B: traced reference
BY0 = 1900
text((60, BY0 - 50), "B  TRACED REFERENCE: LEFT panel warped into frame M (muzzle right), its trace (blue); RIGHT "
     "panel mirrored, own frame, no fitting (red)", F_H)
B = Panel(oy=BY0 + 420)
sheet = Image.open(SHEET).convert("RGB")


def warp_into(view, pn, box):
    x0, y0, x1, y1 = view["panel_box_sheet_px"]
    crop = sheet.crop((x0, y0, x1 + 1, y1 + 1))
    if view.get("mirrored"):
        crop = crop.transpose(Image.FLIP_LEFT_RIGHT)
    s_px = view["px_per_mm"]
    u = np.array(view["bore_dir_px"], float)
    u /= np.hypot(*u)
    n = np.array(view["up_dir_px"], float)
    n /= np.hypot(*n)
    p0 = np.array(view["origin_px"], float)
    bx0, by0, bx1, by1 = box
    a_ = s_px * u[0] / pn.s
    b_ = -s_px * n[0] / pn.s
    c_ = p0[0] + s_px * (u[0] * (bx0 - pn.ox) / pn.s + n[0] * (pn.oy - by0) / pn.s)
    d_ = s_px * u[1] / pn.s
    e_ = -s_px * n[1] / pn.s
    f_ = p0[1] + s_px * (u[1] * (bx0 - pn.ox) / pn.s + n[1] * (pn.oy - by0) / pn.s)
    w = crop.transform((bx1 - bx0, by1 - by0), Image.AFFINE, (a_, b_, c_, d_, e_, f_), resample=Image.BICUBIC,
                       fillcolor=(255, 255, 255))
    w = Image.blend(w, Image.new("RGB", w.size, "white"), 0.40)
    img.paste(w, (bx0, by0))


warp_into(LEFT, B, (0, BY0, W, BY0 + 1460))
for r in LEFT["silhouette"]:
    q = B.poly(r["mm"])
    d.line(q + [q[0]], fill=(30, 80, 220), width=2)
for k_, rr in LEFT["parts"].items():
    for r in rr:
        if r["kind"] == "outer" and abs(r["area_px"]) > 40:
            q = B.poly(r["mm"])
            d.line(q + [q[0]], fill=(110, 150, 240), width=1)
for r in RIGHT["silhouette"]:
    q = B.poly(r["mm"])
    d.line(q + [q[0]], fill=RED, width=1)
dashed(B.c(-15, bz), B.c(705, bz), fill=GREEN, width=1, dash=18, gap=8)
ag = MEAS["agreement"]["left_vs_right"]
text((OX, BY0 + 1475), f"LEFT vs mirrored RIGHT, frame-aligned: silhouette IoU {ag['iou_silhouette_frame_aligned']}, "
     f"without mag {ag['iou_gun_without_mag_frame_aligned']}, magazine {ag['iou_magazine_frame_aligned']}; boundary "
     f"median {ag['boundary_distance_mm']['median']} mm, p90 {ag['boundary_distance_mm']['p90']} mm. Bore (green) "
     f"at Z_M {bz}: the centre of the device's outer edges (R2).", F_S, INK)

# ================================================================== C: spec top
CY0 = 3480
text((60, CY0 - 40), "C  SPEC, TOP (image up = gun left): stock extended (filled), stock folded about the right-rear "
     "axle (dashed)", F_H)
C = Panel(oy=CY0 + 270)
yl, yr = P["upper_receiver"]["dims"]["width_Y_left_right"]
fl, fr = P["upper_receiver"]["dims"]["width_fore_end_X560_584"]
top = []
pad_w = P["butt_pad"]["dims"]["width"]
fw = P["stock_frame"]["dims"]["width_Y"]
stock_ext = [rect(31.0, 244.6, -fw / 2, fw / 2), rect(0.0, 31.0, -pad_w / 2, pad_w / 2)]
top.append((stock_ext[0], POLY2))
top.append((stock_ext[1], RUB))
hk = P["stock_hinge"]["dims"]
top.append((rect(244.6, 272.4, -fw / 2 - 2, fw / 2 + 2), POLY2))
top.append((circle(hk["axis_X"], hk["axis_Y"], hk["knuckle_od"] / 2, 32), STEEL))
eb = P["end_block"]["box_M"]
top.append((rect(272.7, 292.8, eb["Y"][0], eb["Y"][1]), POLY))
top.append((rect(292.8, 533.6, yr, yl), POLY))
top.append((rect(533.6, 621.9, fr, fl), POLY))
top.append((rect(292.8, 618.1, -17.5, 17.5), STEEL))
top.append((rect(306.0, 618.1, -10.6, 10.6), (214, 218, 224)))
for x in rd["cut_slot_centres_X"]:
    top.append((rect(x - 2.62, x + 2.62, -10.6, 10.6), (170, 174, 182)))
srb = P["sight_rear"]["dims"]
top.append((rect(srb["base_X"][0], srb["base_X"][1], -14.0, 14.0), STEEL))
top.append((rect(312.1, 355.3, 14.0, yl + 6.5), STEEL))
sfb = P["sight_front"]["dims"]
top.append((rect(sfb["base_X"][0], sfb["base_X"][1], -14.0, 14.0), STEEL))
ck = sfb["clamp_knob_right"]
top.append((rect(ck["X"][0], ck["X"][1], ck["Y_extreme"], -14.0), STEEL))
top.append((rect(ch["arm_rear_block"]["X"][0], ch["arm_rod"]["X"][1], yl, yl + 3.3), STEEL))
top.append((rect(ch["knob_centre_XZ"][0] - 3, ch["knob_centre_XZ"][0] + 3, yl, ch["knob_centre_Y"]), STEEL))
top.append((circle(ch["knob_centre_XZ"][0], ch["knob_centre_Y"], ch["knob_dia"] / 2, 32), STEEL))
top.append((rect(621.9, 644.1, -11.3, 11.3), STEEL))
od = P["muzzle_device"]["dims"]["od"]
top.append((rect(644.1, 690.0, -od / 2, od / 2), STEEL))
for pts, fill in top:
    fillpoly(C, pts, fill, width=2)
# folded stock (dashed): rotate +180 deg about the axle
ax, ay = FOLD["axis_M"]


def fold_pts(pts):
    return [(2 * ax - x, 2 * ay - y) for x, y in pts]


tf = P["end_block"]["dims"]["top_frame"]
fillpoly(C, rect(tf["X"][0], tf["X"][1], tf["Y"][0], tf["Y"][1]), STEEL, width=1)
fillpoly(C, rect(tf["window_X"][0], tf["window_X"][1], tf["window_Y"][0], tf["window_Y"][1]), DARK, width=1)
lg = P["stock_frame"]["dims"]["retention_lug"]
lug_ext = rect(lg["body_X_ext"][0], lg["body_X_ext"][1], lg["tip_Y_ext"], lg["root_Y_ext"])
fillpoly(C, lug_ext, POLY2, width=1)
text(C.c(lg["body_X_ext"][1] + 3, lg["tip_Y_ext"] - 2), f"retention lug ({lg['proud_of_pad_side_ext']} beyond the "
     "pad side, Q17)", F_XS, DIM, "lt")
ll = P["end_block"]["dims"]["latch_lug"]
fillpoly(C, rect(ll["X"][0], ll["X"][1], ll["Y"][0], ll["Y"][1]), POLY, width=1)
for pts in stock_ext + [lug_ext]:
    dashed_poly(C.poly(fold_pts(pts)), (200, 60, 60), 2)
dashed(C.c(-15, 0), C.c(705, 0), fill=GREEN, width=1, dash=18, gap=8)
cat = P["ejection_port_and_catch"]["dims"]
fillpoly(C, rect(cat["catch_X"][0], cat["catch_X"][1], yr - 3.0, yr), (230, 120, 120), width=1)
text(C.c(cat["catch_X"][0], yr - 4.5), "port catch", F_XS, RED, "rt")
vdim(C, 420, yl, yr, f"receiver {round(yl - yr, 1)}", left=False, f=F_XS)
vdim(C, 572, fl, fr, f"fore-end {round(fl - fr, 1)}", left=False, f=F_XS)
vdim(C, 15, pad_w / 2, -pad_w / 2, f"pad {pad_w}", left=False, f=F_XS)
vdim(C, 120, fw / 2, -fw / 2, f"frame {fw}", left=False, f=F_XS)
vdim(C, 675, od / 2, -od / 2, f"device {od}", left=False, f=F_XS)
text(C.c(ch["knob_centre_XZ"][0], ch["knob_centre_Y"] + 12), f"knob tip Y +{P['charging_handle']['dims']['knob_tip_Y']}",
     F_XS, DIM, "md")
text(C.c(ax, ay - 8), f"axle ({ax}, {ay}), knuckles {hk['knuckle_proud_of_right_wall_TOP']} proud (Q6)", F_XS, DIM, "mt")
fx = FOLD["folded_pad_X"]
text(C.c(fx[1] + 4, FOLD["folded_mid_plane_Y"] - 22), f"folded: mid-plane Y {FOLD['folded_mid_plane_Y']}, pad X "
     f"{fx[0]}-{fx[1]}", F_XS, (200, 60, 60), "la")
hdim(C, FOLD["folded_rearmost_X"], 690.0, -122, f"folded length {FOLD['folded_length']} (real 450, R20)",
     FOLD["folded_min_Y"], -11, F_XS)

# ================================================================== D: traced top
DY0 = 4330
text((60, DY0 - 40), "D  TRACED TOP silhouette (blue) over the TOP panel; X < 245 (the stock) is drawn obliquely on "
     "the sheet (R18)", F_H)
Dp = Panel(oy=DY0 + 210)
warp_into(TOPT, Dp, (0, DY0, W, DY0 + 420))
for r in TOPT["silhouette"]:
    q = Dp.poly(r["mm"])
    d.line(q + [q[0]], fill=(30, 80, 220), width=2)
d.line([Dp.c(245, 60), Dp.c(245, -60)], fill=ORANGE, width=2)
dashed(Dp.c(-15, 0), Dp.c(705, 0), fill=GREEN, width=1, dash=18, gap=8)

# ================================================================== E: folded side
EY0 = 4880
text((60, EY0 - 40), "E  SPEC, STOCK FOLDED, seen from the right (mirrored into frame M): stock over the receiver, "
     "port and catch", F_H)
E = Panel(oy=EY0 + 430)
for pts, fill in side_shapes(include_stock=False)[1:]:
    fillpoly(E, pts, fill, width=1)
for h in holes_M():
    if min(p[0] for p in h) > 300:
        q = E.poly(h)
        d.polygon(q, fill="white")
fillpoly(E, rect(pe["port_X"][0], pe["port_X"][1], pe["port_Z"][0], pe["port_Z"][1]), DARK, width=1)
fillpoly(E, rect(pe["catch_X"][0], pe["catch_X"][1], pe["catch_Z"][0], pe["catch_Z"][1]), (230, 120, 120), width=1)
for k in ("stock_frame", "butt_pad", "stock_hinge"):
    for pr in profiles(k):
        fp = [(2 * ax - x, z) for x, z in pr]
        q = E.poly(fp)
        d.polygon(q, fill=(225, 190, 190))
        d.line(q + [q[0]], fill=(170, 40, 40), width=2)
for h in holes_M():
    if max(p[0] for p in h) < 245:
        q = E.poly([(2 * ax - x, z) for x, z in h])
        d.polygon(q, fill="white")
        d.line(q + [q[0]], fill=(170, 40, 40), width=1)
hdim(E, FOLD["folded_rearmost_X"], 690.0, 100, f"folded length {FOLD['folded_length']}", 40, 0, F_S)
text(E.c(300, -120), "The folded top strut crosses the port (Z 2.5-26.1) in this view; the stock is 14-40 mm outboard "
     "of the wall (open question Q5); magazine not drawn.", F_S, INK, "la")
lgf = P["stock_frame"]["dims"]["retention_lug"]
fx_l = [2 * ax - x for x in lgf["body_X_ext"]]
fillpoly(E, rect(min(fx_l), max(fx_l), lgf["Z"][0], lgf["Z"][1]), (200, 120, 120), width=1)
text(E.c(300, -135), f"Retention (check fix C3): the stock's lug (dark red) snaps under the port catch's rear lip, "
     f"engagement {lgf['engagement_X_under_lip']} mm (gate F3); extended, the left button's latch bolt (gate F6).",
     F_S, INK, "la")

# ================================================================== F: magazine
FY0 = 6230
MS = 6.0
text((60, FY0 - 40), f"F  MAGAZINE SM_SMG01_Mag ({MS:.0f} px = 1 mm, its own frame: origin = Mag, +Z up the insertion "
     "axis): side, ladder, floor plate, catch notch, sockets; front section", F_H)
Fp = Panel(oy=FY0 + 100 + 80 * MS, scale=MS, ox=380)
fa = MD["foreaft"] / 2
zt, zf = MD["top_along_axis"], MD["floor_along_axis"]
body = [(-fa, zt - 4), (-fa + 4, zt), (fa - 2, zt + 3), (fa, zt + 1), (fa, zf + 7.5), (-fa, zf + 7.5)]
fillpoly(Fp, body, MAGC)
fillpoly(Fp, [(-fa - 0.6, zf), (fa + 1.0, zf), (fa + 1.0, zf + 7.5), (-fa - 0.6, zf + 7.5)], (150, 140, 128))
for side in (-1, 1):
    xa = side * lad["rib_between"] / 2
    xb = side * (lad["rib_between"] / 2 + lad["channel_width"])
    za, zb = z_to_along(lad["channel_top_Z"]), z_to_along(lad["channel_bottom_Z"])
    fillpoly(Fp, [(xa, za), (xb, za), (xb, zb), (xa, zb)], (140, 132, 122), width=1)
    for ztie in lad["tie_Z"]:
        zz = z_to_along(ztie)
        fillpoly(Fp, [(xa, zz + 1.2), (xb, zz + 1.2), (xb, zz - 1.2), (xa, zz - 1.2)], MAGC, width=1)
fillpoly(Fp, rect(fa - 0.8, fa + 0.8, zf + 8, zt - 2), (190, 180, 168), width=1)
cn = MD["catch_notch"]
zn = z_to_along(cn["Z_seated"])
fillpoly(Fp, rect(-fa, -fa + cn["depth"], zn - cn["size"][0] / 2, zn + cn["size"][0] / 2), DARK, width=1)
text(Fp.c(-fa - 3, zn), "catch notch", F_XS, INK, "rm")
dashed(Fp.c(-fa - 18, 0), Fp.c(fa + 18, 0), fill=(90, 90, 90), width=2)
text(Fp.c(fa + 19, 0), " well lip (seated)", F_XS, (90, 90, 90), "lm")
for s_ in SPEC["sockets"]["mag"]:
    if s_["socket"] == "CenterOfMass":
        continue
    x, _, z = s_["mag_mm"]
    p = Fp.c(x, z)
    d.line([(p[0] - 10, p[1]), (p[0] + 10, p[1])], fill=RED, width=3)
    d.line([(p[0], p[1] - 10), (p[0], p[1] + 10)], fill=RED, width=3)
    text((p[0] + 12, p[1] + 4), s_["socket"] + {"Mag": " (origin)", "HandReload": " (left face)"}.get(s_["socket"], ""),
         F_S, RED, "la")
ins = SPEC["sockets"]["gun"]
isd = [s for s in ins if s["socket"] == "MagInsertStart"][0]
L_ins = float(np.linalg.norm(np.array(isd["M_mm"]) - MO))
d.line([Fp.c(fa + 10, 0), Fp.c(fa + 10, -L_ins)], fill=RED, width=2)
arrow(Fp.c(fa + 10, 0), (0, -1), fill=RED)
text(Fp.c(fa + 12, -L_ins / 2), f"insert path {L_ins:.1f} (MagInsertStart -> Mag, straight)", F_S, RED, "la")
vdim(Fp, -fa - 30, zf, zt, f"length {MD['length_along_axis']}", left=True)
hdim(Fp, -fa, fa, zf - 10, f"fore-aft {MD['foreaft']}", zf, zf)
text(Fp.c(-fa, zt + 8), f"feed lips top (seated Z_M -14.0), {MD['top_along_axis']} above the lip", F_XS, INK, "la")
text(Fp.c(fa + 4, z_to_along(lad["tie_Z"][1])), f"ladder: 2 x {lad['channel_width']} channels, rib {lad['rib_between']}, "
     f"{lad['depth']} deep; ties at Z_M {lad['tie_Z']}", F_XS, INK, "la")
# front section
sx0 = 1350
Fs = Panel(oy=Fp.oy, scale=MS, ox=sx0)
T = MD["thickness"]
fillpoly(Fs, rect(-T / 2, T / 2, zf + 7.5, zt), MAGC)
fillpoly(Fs, rect(-T / 2 - 1.0, T / 2 + 1.0, zf, zf + 7.5), (150, 140, 128))
fillpoly(Fs, rect(-3.0, 3.0, zf + 8, zt - 2), (190, 180, 168), width=1)
fillpoly(Fs, [(-T / 2, zt), (-6.0, zt + 2.5), (6.0, zt + 2.5), (T / 2, zt)], (150, 140, 128), width=1)
hdim(Fs, -T / 2, T / 2, zf - 10, f"thickness {T} (R14)", zf, zf)
text(Fs.c(0, zt + 8), "front (spine rib 6 x 0.8)", F_XS, INK, "mb")

# ================================================================== legend + QA
mA = mask_from(side_shapes(), (W, H), A, holes_M())
mT = trace_mask(LEFT["silhouette"], (W, H), A)
iou_side = iou(mA, mT)
mMagS = mask_from([(mag_visible_outline(), None)], (W, H), A) & mask_from([(below_lip_poly(), None)], (W, H), A)
mMagT = trace_mask(LEFT["magazine"], (W, H), A)
iou_mag = iou(mMagS, mMagT)
mC = mask_from(top, (W, H), C)
mTop = trace_mask(TOPT["silhouette"], (W, H), C, xmin=245)
mC[:, : int(C.c(245, 0)[0])] = False
iou_top = iou(mC, mTop)
QX, QY = 2000, FY0 + 60
lines = [
    ("QA (spec drawing vs traced silhouettes, 4 px/mm)", F_H),
    (f"side LEFT: IoU {iou_side:.3f} (panel A vs the LEFT trace; the part outlines ARE the trace)", F_M),
    (f"magazine (from spec numbers): IoU {iou_mag:.3f} vs the traced magazine", F_M),
    (f"top, X >= 245: IoU {iou_top:.3f} (panel C boxes vs the TOP trace)", F_M),
    ("", F_S),
    ("Key decisions (SMG_STUDY.md; smg_spec.json resolutions R1-R25)", F_H),
    ("- labels true (LEFT = left); 690 mm at the measured px/mm; the ruler reads 86.8 cm", F_S),
    (f"- bore at Z_M {bz}: device OD {od} (side and top agree; the 20.8 read was a slot sliver)", F_S),
    (f"- Grip 46 mm down the {gr['axis_rake_deg']}° grip axis; mag rake {MD['rake_deg']}°, 46.7 x {T}", F_S),
    (f"- breech X {bar['breech_X']:.0f}, barrel {bar['length']:.0f} (Q2); bolt + handle travel 75; knob {ch['knob_dia']} (re-read)", F_S),
    (f"- top rail: {rd['teeth_built']} teeth / {len(rd['cut_slot_centres_X'])} cut slots at 10.01, flats as drawn", F_S),
    (f"- fold: axle ({ax}, {ay}), +180° to the right, folded {FOLD['folded_length']} (Q6, R19-R20)", F_S),
    ("- right long slot = a vent (not a mirror); boss at the port = stock catch", F_S),
    ("- drum on the rear sight's LEFT; front clamp knob on the right", F_S),
    ("", F_S),
    ("Check fixes C1-C16 (SMG_STUDY.md section 12)", F_H),
    (f"- paddle behind the 4.0 magwell wall: pivot {P['mag_release']['dims']['pivot_XZ']}, "
     f"{P['mag_release']['dims']['declared_deviation']['front_face_vs_drawn']} mm vs the drawn lever (declared)", F_S),
    (f"- mag rake {MD['rake_deg']}° (straight-body fit); trigger pull +{P['trigger']['dims']['pull_rot_Y_deg']:.0f}° "
     f"about the drawn axle {P['trigger']['dims']['pivot_XZ']}", F_S),
    (f"- sight line Z {ap[1]} on the drawn aperture; rear leaf pinned at its front-lower corner "
     f"{P['sight_rear']['dims']['pivot_XZ']}", F_S),
    (f"- handle lock about the slide's roll pin {P['charging_handle']['dims']['lock_axis']['YZ']} (Y, Z); "
     f"lower rail {P['lower_rail']['dims']['slots']} slots; folded min Y {FOLD['folded_min_Y']}", F_S),
    ("", F_S),
    ("Legend", F_H),
    ("polymer / steel / rubber / magazine fills; red cross = socket; blue = dimension; dashed = hidden", F_S),
    ("green dash = bore; orange dash = sight line; violet dash = grip axis; red dashed = right-side or folded", F_S),
]
y = QY
for s_, f in lines:
    text((QX, y), s_, f)
    y += 44 if f in (F_H, F_M) else 32
for i, (c, lbl) in enumerate(((POLY, "polymer"), (STEEL, "steel"), (RUB, "rubber"), (MAGC, "magazine"))):
    d.rectangle([QX + i * 250, y + 6, QX + i * 250 + 40, y + 40], fill=c, outline=INK)
    text((QX + i * 250 + 50, y + 8), lbl, F_S)
text((60, H - 40), f"Generated by WorkFiles/guns/smg/tools/design_sheet.py from smg_spec.json ({SPEC['meta']['date']}). "
     f"Reference: {SPEC['meta']['reference']}.", F_XS, GREY)

img.save(OUT, optimize=True)
print(f"wrote {OUT.relative_to(ROOT)}  side IoU {iou_side:.4f}  mag IoU {iou_mag:.4f}  top IoU {iou_top:.4f}")
