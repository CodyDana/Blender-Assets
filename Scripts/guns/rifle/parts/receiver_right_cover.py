"""Detail round 2 helpers for receiver_right: the dust cover's shouldered cross-section and the crown studs.

Evidence (round-2 judge + c1 / c2 / q34 / LEFT-labelled side panel at 6x):
- c1 draws the cover side as TWO lengthwise bands: a rounded upper crown band and a flat lower skirt band, split by a
  deep pressed crease; the side panel shows the crease as a lit line at Z ~22.7 over the port (c1 relative reading
  20-23.5); q34 / c2 show a fuller, boxier crown on vertical skirts (the old semicircle R 21.75 read as a 'tall flat-
  sided slab' with a plain top).
- the side panel's top silhouette has four 0.7-0.8 mm bumps at X ~270, 311, 373, 422 (trace parts.dust_cover); c1
  draws the first three as round studs on the crown (c1 x 180 / 420 / 730 map to X 268 / 312 / 368 on its own rivet
  scale).
The section keeps every interface: half width 21.75 (key dim 43.5), crown Z 32.7, skirt inner face at COVER_I, and the
new section CONTAINS the old semicircle (the carrier / cover clearances only grow).
"""
from __future__ import annotations

import math

import numpy as np

from gunlib import geo2d as G
from gunlib import lod as LOD

HALF_W = 21.75           # skirt outer half width (rifle_parts.COVER_O)
CROWN_Z = 32.7
CREASE_Z = 22.2          # crease bottom (side panel lit line 22.7 incl. its upper roll)
CREASE_DEPTH = 1.3       # how far the crease presses in from the skirt face (c1 draws a deep, dark crease). Detail fix:
                         # kept (0.3-1.0 tried: the cover's weighted bevel then catches ~250-650 more edges, over budget)
SKIRT_BOW = 0.3          # DETAIL FIX (user checklist 5: "dust cover slightly rounded in section"): the skirt's outer face
                         # bows: 0.3 in at its bottom edge, full width from 55 % of the skirt height up
CROWN_C = 22.0           # crown ellipse centre Z (equator just above the crease)
CROWN_A = 21.5           # crown ellipse half width (0.25 inside the skirt: the crown band sits just in from it)
INNER_DROP, INNER_K, INNER_DZ, INNER_FOOT = 0.6, 1.0, -0.1, 1.5   # inner crease placement: sheet >= 0.92 everywhere
STUDS_X = (271.0, 311.0, 373.0, 422.0)
STUD_R, STUD_H = 2.4, 1.2       # c1 draws ~4.2 x 1.4 at its 1.25x feature scale; side bumps 0.7-0.8 (+-1 sheet px)


def crown_z(y):
    b = CROWN_Z - CROWN_C
    return CROWN_C + b * math.sqrt(max(0.0, 1.0 - (y / CROWN_A) ** 2))


def _section(zb, half_w, skirt_top, crease_y, crease_z, a, b, foot_z, r_skirt, r_crease, r_foot, n_crown=11, bow=0.0):
    t0 = math.asin(min(1.0, (foot_z - CROWN_C) / b))
    ts = np.linspace(t0, math.pi / 2, LOD.arc_points(n_crown))        # LOD: fewer crown points
    right = np.c_[a * np.cos(ts), CROWN_C + b * np.sin(ts)]       # crown band foot -> top
    if bow > 0:
        zm = zb + 0.55 * (skirt_top - zb)
        corners = [(half_w - bow, zb), (half_w, zm), (half_w, skirt_top), (crease_y, crease_z)]
    else:
        corners = [(half_w, zb), (half_w, skirt_top), (crease_y, crease_z)]
    half = np.vstack([corners, right[:-1]])                        # right side, bottom -> top (top excluded)
    left = half[::-1] * [-1.0, 1.0]
    P = np.vstack([half, [[0.0, CROWN_C + b]], left])               # CCW in (Y, Z)
    lead = [0.0] * (len(corners) - 2)
    radii = lead + [r_skirt, r_crease, r_foot] + [0.0] * (len(half) - len(corners) - 1)
    radii = radii + [0.0] + radii[::-1]
    return G.fillet(P, 1.0, 3, radii=radii)


def cover_section_outer(zb):
    """Closed CCW (Y, Z) polygon of the cover's outer section, bottom at zb."""
    return _section(zb, HALF_W, CREASE_Z - 1.0, HALF_W - CREASE_DEPTH, CREASE_Z, CROWN_A, CROWN_Z - CROWN_C,
                    CREASE_Z + 1.0, 1.6, 0.5, 1.4, bow=SKIRT_BOW)


def cover_section_inner(zb, inner_half_w, wt):
    """Inner face: same construction one sheet thickness in (skirt at inner_half_w = COVER_I, crown ellipse a - wt,
    b - wt about the same centre); the convex outer rolls become the concave inner rolls and vice versa."""
    return _section(zb, inner_half_w, CREASE_Z - 1.0 - INNER_DROP, HALF_W - CREASE_DEPTH - wt * INNER_K,
                    CREASE_Z + INNER_DZ, CROWN_A - wt, CROWN_Z - CROWN_C - wt, CREASE_Z + INNER_FOOT, 0.6, 1.5, 0.5)
