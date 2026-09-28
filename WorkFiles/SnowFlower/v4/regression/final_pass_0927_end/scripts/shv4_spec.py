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
CHAPE_POCKET_END_ROW = 1266.0            # the lacquer core ends here, inside the chape (hidden)


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
    """spec: 9 px rows 170-286, 6-7 px 322-700, 4-6 px 700-1100, 4-5 px 1100-1262 (MEASURED, noisy)."""
    return 1.12 * float(np.interp(row, [160, 286, 322, 700, 1100, 1262, 1275], [9.0, 8.5, 6.5, 5.5, 4.8, 4.2, 4.0]))


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
SECOND_STEM = [((930.0, 1000.0), "twine"), ((1060.0, 1200.0), "beside")]
SECOND_STEM_PX = 2.8
TWIG_PX = 2.6
#: etched twigs in the lacquer (flat, albedo only): (row0, row1, side) side +1 = image left (+X), -1 = right
ETCHED = [(420.0, 470.0, 1), (550.0, 600.0, -1), (1100.0, 1230.0, 1), (1100.0, 1230.0, -1)]

# --------------------------------------------------------------------------- fit / sockets
SWORD_FBX = ROOT / "Exports" / "SnowFlower" / "v4" / "SM_SnowFlower.fbx"
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
QA_TEXEL_TARGET = 80.0     # hero target; the aggregate includes the hidden interior islands packed at 6 %

# --------------------------------------------------------------------------- material slots (final pass 2026-09-26)
#: the silver slot is named for its part (the fittings: throat, band, chape, vine, blossoms), matching the sword's
#: M_SnowFlower_Fittings, so the pack's instances read MI_SnowFlower_Sheath_Lacquer / MI_SnowFlower_Sheath_Fittings
SLOT_LACQUER = "M_SnowFlower_Sheath_Lacquer"
SLOT_SILVER = "M_SnowFlower_Sheath_Fittings"
#: the lacquer's tint-ready Detail map ships at half the atlas (memory: the 4096 sRGB G8 built as 85 MiB BGRA8)
LACQUER_DETAIL_MAP = 2048
