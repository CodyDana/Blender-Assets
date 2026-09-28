"""Snow Flower sheath (SM_SnowFlower_Sheath) - every design number in one place.

SOURCE OF THE NUMBERS
    References/SnowFlower/SHEATH_REFERENCE_SPEC.md and its machine twin WorkFiles/SnowFlower/v4/sheath_spec.json
    (measured off the reference by the metrology job).  The build NEVER reads the reference pixels: every number
    below is either copied from the spec (MEASURED), derived from it (INFERRED) or a design choice (DESIGNED, the
    reference cannot show it or the v4 blade forces it).  Plate outlines are DESIGNED polygons placed on the spec's
    measured tip positions and tier widths; ``throat_width_check`` compares their union with the spec tiers.

SHEATH MODEL FRAME (millimetres, the shipped mesh)
    origin  = centre of the mid band (the belt mount, reference row 304) on the sheath axis
    +Z      = toward the chape point (the same direction as the sword's +Z toward its tip)
    +X      = the sword's SPINE side; seen in the reference front view (mouth up) +X is on the viewer's LEFT
    -Y      = the front face (the face the reference shows, with the vine and blossoms)
    Reference pixel (row, x_px) -> z = (row - 304) * K,  x = (505.5 - x_px) * K.
    K = 0.687 mm per reference px (spec section 0, DESIGNED from the fit): mouth z -187.55, point z +818.90.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
SPEC_JSON = ROOT / "WorkFiles" / "SnowFlower" / "v4" / "sheath_spec.json"

K = 0.687
ROW_MOUTH = 31.0
ROW_BAND = 304.0
ROW_POINT = 1496.0
X_AXIS_PX = 505.5


def zr(row):
    return (np.asarray(row, float) - ROW_BAND) * K


def xp(x_px):
    return (X_AXIS_PX - np.asarray(x_px, float)) * K


def row_of(z):
    return np.asarray(z, float) / K + ROW_BAND


Z_MOUTH = float(zr(ROW_MOUTH))       # -187.551
Z_POINT = float(zr(ROW_POINT))       # +818.898
LENGTH = Z_POINT - Z_MOUTH           # 1006.4

# --------------------------------------------------------------------------- body (lacquer core)
#: body width profile [row, px] (spec section 2, MEASURED); rows < 169 are under the throat (the core keeps 97 px)
BODY_PX = [(31, 97.0), (169, 97.0), (250, 97.0), (286, 97.0), (322, 96.0), (340, 96.0), (400, 95.0), (500, 92.0),
           (600, 90.0), (700, 88.0), (800, 85.0), (900, 83.0), (1000, 79.0), (1100, 77.0), (1200, 74.0),
           (1250, 72.0), (1292, 71.5), (1400, 71.5)]
#: depth (thickness, Y): DESIGNED 22 mm under the throat -> 17 mm at the chape collar (spec section 2)
DEPTH_ROWS = [(31, 22.0), (169, 22.0), (1292, 17.0), (1400, 16.4)]
#: section ratios (spec section 2: front face 0.51 of the width, chamfers 0.21 each in projection, sides 0.035)
SEC_FRONT = 0.51     # front face half-width / half-width
SEC_CHAMF = 0.93     # chamfer/side corner x / half-width
SEC_CHAMF_Y = 0.40   # chamfer/side corner |y| / half-depth
SEC_SIDE_Y = 0.13    # side face top |y| / half-depth


def body_w(row):
    """Reference body width (mm) - the visible lacquer silhouette."""
    r, w = zip(*BODY_PX)
    return np.interp(np.asarray(row, float), r, w) * K


#: DESIGNED (fit): under the throat the hidden lacquer core is widened by this much per side (full to row 60, fading
#: to 0 at row 140) so the mouth can pass the 53.5 mm v4 blade; the collar follows it (the sleeve keeps its width).
THROAT_EXTRA = 2.0          # final pass 1.5 -> 2.0 (the mouth now also passes the guard's pendant leaves)


def core_w(row):
    """Width (mm) of the lacquer core: the reference body, widened under the throat (hidden)."""
    row = np.asarray(row, float)
    e = THROAT_EXTRA * np.clip((140.0 - row) / (140.0 - 60.0), 0.0, 1.0)
    return body_w(row) + 2 * e


#: FINAL PASS (guard seat, 2026-09-26): the sword now sinks until the guard's LEAF BODY sits GUARD_GAP above the collar
#: (before, only the pendant-leaf tips touched and ~20 mm of bare blade showed under the leaf body).  The front/back
#: pendant leaves (x +-12.2, y up to +-15.3 mm, 19 mm long) therefore enter the mouth like a habaki, and the core + throat
#: under the collar are deepened by this much per side (full to row 62 = 21 mm below the mouth, fading to 0 by row 100;
#: hidden inside the throat fitting, DESIGNED - the reference shows no side view).
THROAT_DEPTH_EXTRA = 9.0          # pendant |y| 15.3 + clearance 0.6 + the 16-gon corner (1/cos 11.25) + wall 1.2
THROAT_DEPTH_ROWS = (62.0, 100.0)


def body_d(row):
    r, d = zip(*DEPTH_ROWS)
    row = np.asarray(row, float)
    a, b = THROAT_DEPTH_ROWS
    e = THROAT_DEPTH_EXTRA * np.clip((b - row) / (b - a), 0.0, 1.0)
    return np.interp(row, r, d) + 2 * e


def core_section(W, D, level=0):
    """Closed ring of the lacquer core (x, y) in mm, starting at the +X side (y = 0), running over the FRONT (-Y)
    to the -X side and back over the back face.  LOD0/1: 16 points (front/back face centres included); LOD2: 10
    (side-face and centre points dropped, silhouette width kept).  Returns (pts (n,2), keep_mask_for_lod2)."""
    c, b = W / 2.0, D / 2.0
    q = [(c, 0.0), (c, -SEC_SIDE_Y * b), (SEC_CHAMF * c, -SEC_CHAMF_Y * b), (SEC_FRONT * c, -b), (0.0, -b)]
    front = q + [(-x, y) for x, y in q[-2::-1]]                      # +X side .. front .. -X side (9 points)
    back = [(x, -y) for x, y in front[-2:0:-1]]                       # -X side (excl.) .. back .. +X side (excl.)
    ring = np.array(front + back, float)                               # 16 points
    return ring


#: ring indices kept at LOD2 (drop the side-face tops and the face centres)
CORE_LOD2 = [0, 2, 3, 5, 6, 8, 10, 11, 13, 14]


# --------------------------------------------------------------------------- fittings: silhouettes (front view)
T_SHELL = 1.2            # metal fitting wall over the core (DESIGNED)
T_THROAT = 2.0           # the throat stands 2.0 mm proud of the core (sleeve: spec 2.5 px = 1.7 mm per side)
T_BAND = 2.75            # the band rings are 4 px (2.75 mm) proud of the body per side (spec section 4)
WING_E = 1.7             # half-thickness of a fitting flange at its tip (DESIGNED)

# Throat plates: DESIGNED outlines on the spec's measured tips (section 3).  (dx_px, row), dx = x_px - 505.5, i.e.
# image-right positive; the right-hand plates are mirrored to the left.  Layer = stacking order (higher = in front).
THROAT_PLATES = {
    "up": ([(0, 38), (9, 52), (11, 66), (0, 74), (-11, 66), (-9, 52)], 0, False),
    "upper": ([(11, 84), (12, 72), (19, 60), (32, 50), (55.5, 44), (55.5, 51), (54.0, 58), (55.5, 64),
               (58.5, 68), (57.0, 75), (49, 81), (32, 87)], 1, True),
    "lateral": ([(24, 97), (30, 88), (44, 82), (61, 82), (73.5, 88.5), (68, 95), (58, 102), (48, 107),
                 (34, 106)], 2, True),
    "lower": ([(18, 104), (40, 104), (54, 112), (57.5, 124), (57.5, 134), (53, 140), (41, 137), (28, 128),
               (19, 117)], 1, True),
    "drop": ([(0, 100), (19, 108), (15, 126), (7, 147), (0, 165), (-7, 147), (-15, 126), (-19, 108)], 2, False),
}
THROAT_COLLAR_ROWS = (31.0, 40.0)
THROAT_SLEEVE_ROWS = (142.0, 167.0)
THROAT_SLEEVE_HALF_PX = 51.0            # 102 px (2.5 px proud of the body per side)
THROAT_BLOSSOM = ((505.0, 87.0), 60.0)  # centre (x_px, row), diameter px; one petal up (MEASURED)
#: the spec's tier maxima, used to check the designed outlines: rows -> width px
THROAT_TIERS = [((41, 63), 112.0), ((65, 80), 117.0), ((81, 141), 147.0), ((127, 139), 115.0), ((143, 167), 102.0)]

BAND_ROWS = (284.0, 317.0)
BAND_RING_HALF_PX = 52.5                # rings 104-106 px
BAND_FRIEZE = (292.0, 308.0, 300.0, 58.5)   # rows, row of the pointed ends, half-width of the ends (117 px)
BAND_BLOSSOM = ((504.0, 300.0), 44.0)   # 50 x 40 px measured; one round blossom of 44 px (DESIGNED compromise)

CHAPE_TOP_ROW = 1262.0
CHAPE_PX = [(1262, 72.4), (1292, 72.4), (1300, 75.0), (1320, 79.0), (1344, 84.0), (1362, 81.0), (1375, 78.0),
            (1386.5, 75.0), (1388.0, 68.0), (1400, 66.0), (1420, 60.0), (1440, 50.0), (1460, 38.0), (1480, 21.0),
            (1492, 8.0), (1496, 3.0)]
CHAPE_BLOSSOM = ((505.0, 1330.0), 54.0)
#: chape plates (dx_px, row) (DESIGNED on the measured tips, spec section 5)
CHAPE_PLATES = {
    "lancet": ([(0, 1266), (9, 1284), (12, 1300), (0, 1308), (-12, 1300), (-9, 1284)], 0, False),
    "upper": ([(9, 1306), (17, 1292), (30, 1282), (36, 1290), (34, 1304), (22, 1316), (12, 1318)], 0, True),
    "lateral": ([(12, 1320), (24, 1318), (35, 1328), (40.5, 1346), (35, 1357), (21, 1354), (11, 1342)], 1, True),
    "lowlat": ([(7, 1350), (21, 1354), (30, 1368), (31.5, 1383), (22, 1387), (12, 1377), (6, 1362)], 1, True),
    "down": ([(0, 1346), (12, 1355), (8, 1378), (0, 1398), (-8, 1378), (-12, 1355)], 2, False),
    "lancet_outer": ([(0, 1396), (31, 1390), (27, 1420), (20, 1444), (11, 1466), (0, 1490), (-11, 1466), (-20, 1444),
                      (-27, 1420), (-31, 1390)], 0, False),
    "lancet_inner": ([(0, 1404), (21, 1398), (17, 1422), (11, 1440), (0, 1457), (-11, 1440), (-17, 1422),
                      (-21, 1398)], 1, False),
}
CHAPE_POCKET_END_ROW = 1296.0            # the lacquer core ends here, inside the chape sleeve (hidden); look-match r1: 1266 -> 1296
#                                          (the arch plate above the sleeve sits on the lacquer; min wall 1.58 mm, measured)


def _mirror(outline):
    return [(-dx, r) for dx, r in outline]


def plate_outlines(table):
    """name -> list of (outline [(x_mm, z_mm)], layer).  Right-hand plates are mirrored to the left."""
    out = {}
    for name, (pts, layer, pair) in table.items():
        variants = [("R", pts), ("L", _mirror(pts)[::-1])] if pair else [("", pts)]
        for tag, p in variants:
            xy = [(float(xp(X_AXIS_PX + dx)), float(zr(r))) for dx, r in p]
            out[name + tag] = (xy, layer)
    return out


def _poly_halfwidth_at(outline, z):
    """max |x| of a closed polygon at height z (edge intersections), or None."""
    P = np.asarray(outline, float)
    best = None
    n = len(P)
    for i in range(n):
        (x0, z0), (x1, z1) = P[i], P[(i + 1) % n]
        if (z0 - z) * (z1 - z) <= 0 and z0 != z1:
            x = x0 + (x1 - x0) * (z - z0) / (z1 - z0)
            best = abs(x) if best is None else max(best, abs(x))
    return best


def throat_half(row):
    """Outer half-width (mm) of the throat fitting at a reference row (union of the plate outlines, collar, sleeve,
    never less than the core + wall)."""
    row = float(row)
    base = float(core_w(row)) / 2 + T_THROAT
    best = base
    if THROAT_SLEEVE_ROWS[0] <= row <= THROAT_SLEEVE_ROWS[1]:
        best = max(best, THROAT_SLEEVE_HALF_PX * K)
    z = float(zr(row))
    for name, (poly, _) in plate_outlines(THROAT_PLATES).items():
        h = _poly_halfwidth_at(poly, z)
        if h is not None:
            best = max(best, h)
    return best


def band_half(row):
    row = float(row)
    base = float(core_w(row)) / 2 + T_BAND
    r0, r1, rc, hp = BAND_FRIEZE
    h = BAND_RING_HALF_PX
    if r0 <= row <= r1:
        h = max(h, hp - (hp - BAND_RING_HALF_PX) * abs(row - rc) / (r1 - rc if row > rc else rc - r0))
    return max(base, h * K)


def chape_half(row):
    r, w = zip(*CHAPE_PX)
    return float(np.interp(float(row), r, w)) * K / 2


def chape_depth(row):
    """DESIGNED: the chape is flush with the body (depth + 0.3) to the ogive, which then thins toward the point."""
    row = float(row)
    d0 = float(body_d(min(row, 1388.0))) + 0.3
    if row <= 1388.0:
        return d0
    f = chape_half(row) / chape_half(1388.0)
    return max(3.0, d0 * f ** 0.65)


def throat_width_check():
    """Designed throat silhouette vs the spec's tier maxima (px)."""
    rep = []
    for (r0, r1), w in THROAT_TIERS:
        m = max(2 * throat_half(r) / K for r in np.arange(r0, r1 + 0.01, 0.5))
        rep.append({"rows": [r0, r1], "spec_px": w, "designed_px": round(m, 1), "delta_px": round(m - w, 1)})
    return rep


# --------------------------------------------------------------------------- vine (front face only)
def spec_rows():
    d = json.loads(SPEC_JSON.read_text(encoding="utf-8"))
    return {(r["section"], r["row"]): r for r in d["rows"]}


def vine_path_px():
    rows = spec_rows()
    for (sec, row), r in rows.items():
        if sec == "6 vine" and row.startswith("path (row, x)"):
            return [tuple(p) for p in r["value"]]
    raise KeyError("vine path")


def vine_blossoms_px():
    rows = spec_rows()
    for (sec, row), r in rows.items():
        if sec == "6 vine" and row.startswith("open blossoms"):
            return r["value"]
    raise KeyError("vine blossoms")


def stem_width_px(row):
    """Look-match round 1: a thick sculpted branch, ~13 px under the throat tapering to ~6.5 px into the chape (the
    reference crops at 3-4x; the spec's 9 / 6-7 / 4-6 px read only the specular core of the stem), with knots."""
    w = float(np.interp(row, [160, 200, 240, 286, 322, 400, 560, 700, 900, 1100, 1262],
                        [14.0, 13.0, 11.5, 10.5, 9.5, 9.2, 9.0, 8.8, 8.6, 8.4, 7.8]))
    for kr in VINE_KNOTS:
        w *= 1.0 + 0.22 * math.exp(-((row - kr) / 6.0) ** 2)
    return w


#: knots (rows) where twigs, buds and blossoms leave the stem
VINE_KNOTS = [205, 262, 352, 455, 520, 600, 652, 700, 808, 905, 1010, 1090, 1170, 1232]
VINE_SQUASH = 0.72

#: buds (row, dx_px) - rows MEASURED (spec section 6), lateral offsets DESIGNED beside the stem
BUDS = [(216, 9), (224, -8), (356, 10), (361, -9), (366, 7), (452, -10), (458, 8), (523, 11), (558, -9),
        (636, -10), (648, 9), (668, -8), (684, 10), (1009, 9), (1016, -10), (1023, 7), (1094, 9), (1100, -8)]
BUD_DIAM_PX = 7.0
#: teardrop pods (x_px, row), ~12 x 22 px (MEASURED)
PODS = [((506.0, 820.0), (12.0, 22.0)), ((501.0, 919.0), (12.0, 22.0))]
#: small pointed leaves (x_px, row) (MEASURED two, DESIGNED four more near the clusters)
LEAVES = [(472.0, 523.0, 1.0), (482.0, 1125.0, -1.0), (530.0, 470.0, -1.0), (540.0, 705.0, 1.0),
          (528.0, 1060.0, -1.0), (522.0, 350.0, 1.0)]
#: second, thinner stem (spec: twines around the main stem rows ~930-1000, runs beside it rows 1060-1200)
SECOND_STEM = [((930.0, 1000.0), "twine")]          # look-match: the parallel strand rows 1060-1200 removed
SECOND_STEM_PX = 2.8
TWIG_PX = 3.2
#: etched twigs in the lacquer (flat, albedo only): (row0, row1, side) side +1 = image left (+X), -1 = right
ETCHED = [(420.0, 470.0, 1), (550.0, 600.0, -1), (1100.0, 1230.0, 1), (1100.0, 1230.0, -1)]

# --------------------------------------------------------------------------- fit / sockets
import os as _os
#: look-match round 1: the sword is built in parallel; the sheath keeps fitting THE CURRENT (pre-look-match) sword,
#: set SH4_SWORD_DIR to the protected backup (Backups/SnowFlower_v4_pre_lookmatch_2026-09-27/Exports_v4) while the sword
#: builder may be rewriting Exports/SnowFlower/v4/SM_SnowFlower.fbx (the Verify phase refits to the final sword)
SWORD_DIR = Path(_os.environ.get("SH4_SWORD_DIR", str(ROOT / "Exports" / "SnowFlower" / "v4")))
SWORD_FBX = SWORD_DIR / "SM_SnowFlower.fbx"
SWORD_REPORT = ROOT / "WorkFiles" / "SnowFlower" / "v4" / "sword_report.json"
CLEARANCE = 0.6            # blade (any LOD vertex, swept along its own axis) to the cavity wall
MIN_WALL = 1.2             # cavity to the outer surface, laterally (design gate; the fit leaves >= 1.5 in practice)
GUARD_GAP = 0.4            # lowest point of the guard's LEAF BODY above the mouth plane (final pass; was: any hilt vertex)
#: the part of the hilt allowed INTO the mouth (sword frame, mm): the front/back pendant leaves and the hub's bottom ring
#: (|x| < 15.5 below the leaf body, z > 104) and anything on the blade's own section (|y| < 6.3, z > 96)
PLUG_HALF_X = 15.5
PLUG_Z = 104.0
PLUG_BLADE_HALF_Y = 6.3
CAVITY_DIRS = {0: 16, 1: 16, 2: 16}     # support-polygon directions per LOD (the blade edge is a thin wedge)
CAVITY_STEP = {0: 20.0, 1: 30.0, 2: 50.0}   # final pass: finer LOD1/LOD2 knots (the deeper seat)

#: sheath LODs and textures
LOD_SCREEN_SIZES = (1.0, 0.5, 0.25)
ATLAS = 4096
PAD_PX = 16
BUDGET_TRIS = 16000
#: qa texel target (px/cm over UV0, 4096 map), set from the measured atlas density - see SHEATH_REPORT
QA_TEXEL_TARGET = 64.0     # look-match r1: visible islands 79.6 px/cm; the aggregate adds the hidden interior (6 %),
#                            the plate undersides (10 %) and the back plates (70 %) - measured 56 px/cm (80 before)

# --------------------------------------------------------------------------- material slots (final pass 2026-09-26)
#: the silver slot is named for its part (the fittings: throat, band, chape, vine, blossoms), matching the sword's
#: M_SnowFlower_Fittings, so the pack's instances read MI_SnowFlower_Sheath_Lacquer / MI_SnowFlower_Sheath_Fittings
SLOT_LACQUER = "M_SnowFlower_Sheath_Lacquer"
SLOT_SILVER = "M_SnowFlower_Sheath_Fittings"
#: the lacquer's tint-ready Detail map ships at half the atlas (memory: the 4096 sRGB G8 built as 85 MiB BGRA8)
LACQUER_DETAIL_MAP = 2048


# =========================================================================== LOOK-MATCH ROUND 1 (2026-09-27)
# The reference's throat, band and chape are RAISED, BEVELLED, OVERLAPPING CAST PLATES (shv4_plates).  The numbers
# below place them.  Plates: spine [(dx_px, row)] base -> tip in the reference front view (dx = x_px - 505.5, image
# right +) and half-width profiles [(t, px)] on side a (the lower / outer side of a spine that runs up and outward)
# and side b.  Paired plates are designed on the image-RIGHT and mirrored.  Tiers stack front-most last.
# DESIGNED on the reference crops (References/SnowFlower/SnowFlower_sheath_reference.png, 4-6x zoom) and adjusted by
# overlaying the outlines on the crop (WorkFiles/SnowFlower/v4/lookmatch/sheath_r1/design_*.png).

BUDGET_TRIS = 25000            # hero budget for the look-match round (was 16k)

# ---- throat crown: a superellipse bulb |y| = crown_Yb(row) * se(|x| / CROWN_AX, CROWN_M), clipped at the sleeve's
# half-width (crown_half); the same surface, continued beyond the bulb's sides, carries the flaring leaves
CROWN_AX = 72.0            # iter 4: 56 -> 72 (gentler flare: the floating lateral leaves folded)
CROWN_M = 2.6
CROWN_SIDE_M = 3.2             # the bulb rounds into its sides (squircle exponent)
CROWN_EXTRA_Y = 1.2            # extra front/back depth under the mouth ring (fades with the throat depth extra)


def crown_Yb(row):
    row = float(row)
    a, b = THROAT_DEPTH_ROWS
    e = CROWN_EXTRA_Y * float(np.clip((b - row) / (b - a), 0.0, 1.0))
    return float(body_d(row)) / 2 + T_THROAT + e


def crown_half(row):
    return float(core_w(row)) / 2 + T_THROAT


#: the mouth ring (rows 31-41): a rounded, cupped lip - fillet at the mouth plane, a convex bead, a groove under it
COLLAR_FILLET = (3.0, 1.3)     # fillet radius across (x) and front-back (y) at the mouth plane
COLLAR_BEAD = (31.0, 41.5, 0.9)  # rows, outward bulge (mm)
COLLAR_GROOVE = (42.6, 1.4, 1.2)  # row, half-width rows, depth (mm)

THROAT_LEAVES = [
    # the back tier: two broad leaves rising from behind the blossom to the upper outer corners (curl outward)
    dict(name="upper", spine=[(6, 84), (30, 62), (55, 44)], wa=[(0, 0), (0.12, 9), (0.45, 16), (0.75, 15), (0.92, 8), (1, 0)],
         wb=[(0, 0), (0.12, 10), (0.5, 15), (0.8, 8), (0.94, 3), (1, 0)], tier=0, fill="dish", curl=2.2, F=4.1, T=2.5),
    # behind them, only their tips show in the notch at rows 65-80
    dict(name="upper2", spine=[(10, 96), (36, 80), (58, 69)], wa=[(0, 0), (0.2, 8), (0.6, 10), (0.9, 4), (1, 0)],
         wb=[(0, 0), (0.2, 8), (0.6, 9), (0.9, 4), (1, 0)], tier=0, fill="dish", curl=1.2, lift0=-0.6, F=2.9, T=2.1),
    # the central plate behind the blossom's top petal, pointing up
    dict(name="up", spine=[(0, 92), (0, 39)], wa=[(0, 0), (0.15, 12), (0.55, 11), (0.85, 5), (1, 0)], tier=0,
         fill="keel", pair=False, F=2.7, T=2.1),
    # the big lateral leaves: tip at the upper outer corner, broad belly down to row ~140
    dict(name="lateral", spine=[(18, 120), (45, 100), (72, 84)], wa=[(0, 0), (0.1, 17), (0.35, 27), (0.65, 24), (0.88, 11), (1, 0)],
         wb=[(0, 0), (0.1, 12), (0.35, 17), (0.6, 11), (0.85, 5), (1, 0)], tier=1, fill="dish", curl=1.2, F=4.6, T=2.6, cup=0.5),
    # the drop plate under the blossom, a folded (keel) inset
    dict(name="drop", spine=[(0, 104), (0, 165)], wa=[(0, 0), (0.05, 15), (0.2, 17), (0.5, 11), (0.8, 5), (1, 0)],
         tier=2, fill="keel", pair=False, F=4.2, T=2.6),
]
THROAT_BLOSSOM_TIER_LIFT = 5.6     # the throat blossom's base above the crown envelope (over tier 2)

# ---- chape (look-match): the lacquer core now runs down to row 1296 under the chape SLEEVE (rows 1292-1388, a solid
# silver fitting whose lateral leaves widen the silhouette), then the solid silver OGIVE (rows 1388-1496) with a thick
# bevelled rim and nested lancet plates.  The arch plate above the sleeve (rows 1265-1300) sits on the lacquer.
CHAPE_SLEEVE_TOP = 1292.0
CHAPE_OGIVE_ROW = 1388.0
CHAPE_SLEEVE_HALF_PX = 36.6      # 73.2 px: the body (72.4) + 0.4 px proud per side


def chape_body_half(row):
    """Half-width (mm) of the chape's solid body: the sleeve, then the ogive's own silhouette."""
    row = float(row)
    if row < CHAPE_OGIVE_ROW:
        return CHAPE_SLEEVE_HALF_PX * K
    return chape_half(row)


def chape_ax(row):
    row = float(row)
    return chape_body_half(row) * (1.12 if row < CHAPE_OGIVE_ROW else 1.07)


def chape_m(row):
    return 3.0 if float(row) < CHAPE_OGIVE_ROW else 2.3


CHAPE_M = 3.0


def chape_Yb(row):
    """Front half-depth (mm) of the chape body: contains the core + 0.15 (sleeve), thins toward the point (ogive)."""
    row = float(row)
    if row < CHAPE_OGIVE_ROW:
        return 1.08 * float(body_d(row)) / 2 + 0.35
    return max(1.4, chape_depth(row) / 2)


CHAPE_LEAVES = [
    # the pointed arch over the lacquer above the sleeve (the vine enters it): an OPEN frame (the lacquer shows inside)
    dict(name="arch", spine=[(7, 1308), (7, 1262)], wa=[(0, 0), (0.08, 25), (0.3, 20), (0.65, 11), (0.9, 4), (1, 0)],
         wb=[(0, 0), (0.08, 23), (0.3, 19), (0.65, 10), (0.9, 4), (1, 0)], tier=0, env="core", fill="open", pair=False,
         F=3.4, T=2.0),
    # the upper side leaves: from behind the blossom up to the sleeve's top outer corners (they cover the sleeve)
    dict(name="upper", spine=[(6, 1344), (22, 1318), (37, 1297)], wa=[(0, 0), (0.12, 12), (0.45, 19), (0.8, 12), (0.95, 4), (1, 0)],
         wb=[(0, 0), (0.12, 8), (0.5, 11), (0.8, 7), (0.95, 2), (1, 0)], tier=0, fill="dish", F=3.0, T=2.0, curl=0.6),
    # the lower side leaves: from behind the blossom down-outward to the sleeve's lower corners (bellying to x 41)
    dict(name="lower", spine=[(6, 1346), (24, 1360), (31, 1387)], wa=[(0, 0), (0.12, 7), (0.5, 9), (0.85, 5), (1, 0)],
         wb=[(0, 0), (0.12, 11), (0.4, 16), (0.75, 11), (0.93, 4), (1, 0)], tier=1, fill="dish", F=3.0, T=2.0),
    # the drop plate under the blossom
    dict(name="drop", spine=[(0, 1350), (0, 1402)], wa=[(0, 0), (0.1, 12), (0.35, 10), (0.7, 5), (1, 0)], tier=2,
         fill="keel", pair=False, F=2.6, T=2.0),
    # ogive: the narrow side lancets hugging the rim, and the central lancet frame round its dark inset
    dict(name="oside", spine=[(27, 1382), (26, 1415), (20, 1442), (13, 1462)], wa=[(0, 0), (0.08, 3.8), (0.8, 3.4), (1, 0)],
         tier=0, env="chape", fill="dish", F=1.1, T=0.9),
    dict(name="ocentre", spine=[(0, 1360), (0, 1466)], wa=[(0, 0), (0.12, 20), (0.3, 26), (0.55, 20), (0.8, 10), (1, 0)],
         tier=1, env="chape", fill="dish", pair=False, F=4.0, T=1.9),
]
CHAPE_BLOSSOM_LIFT = 4.3
CHAPE_TOP_LIP = (1292.0, 1299.0, 1.1)   # the sleeve's top edge is a raised, rounded lip (rows, outward mm)

# ---- mid band (look-match): two raised rounded rims (rows 284-292, 309-317) round a recessed dark frieze with a
# silver leaf scroll and pointed side ends; the blossom sits over it; filigree leaf plates above and below it
BAND_T_FRIEZE = 1.5
BAND_RIMS = [(284.0, 292.5), (308.5, 317.0)]
BAND_RIM_H = 1.6                       # rim crest above the frieze (flat-topped band with rounded edges)
BAND_BLOSSOM = ((504.0, 300.0), 60.0)  # look-match: ~61 px across on the 6x crop (was 44)
BAND_BLOSSOM_LIFT = 3.2
BAND_LEAVES = [
    # acanthus-like filigree plates beside the stem, above and below the band (antique silver, engraved in the high)
    dict(name="above", spine=[(12, 287), (19, 275), (21, 262)], wa=[(0, 0), (0.15, 10), (0.5, 11), (0.85, 5), (1, 0)],
         wb=[(0, 0), (0.15, 6), (0.5, 7), (0.85, 3), (1, 0)], tier=0, env="core", fill="silver", F=1.4, T=0.9, cup=0.3,
         lobes=4, rows0=16, hmat=7, sides=(-1,)),
    dict(name="below", spine=[(12, 315), (20, 329), (23, 344)], wa=[(0, 0), (0.15, 7), (0.5, 8), (0.85, 3), (1, 0)],
         wb=[(0, 0), (0.15, 10), (0.5, 12), (0.85, 5), (1, 0)], tier=0, env="core", fill="silver", F=1.4, T=0.9, cup=0.3,
         lobes=4, rows0=16, hmat=7, sides=(-1,)),
]

# ---- throat lace (look-match): the filigree fringe hanging from the lower sleeve (antique silver, bake only)
THROAT_LACE_DX = [-47, -41, -35, -29, -23, -17, 17, 23, 29, 35, 41, 47]   # px from the axis (the drop plate holds the centre)
THROAT_LACE_ROWS = (150.0, 167.5)
