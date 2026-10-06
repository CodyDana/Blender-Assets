"""Dust cover as a PRESSED SHEET (form realism round, 2026-10-05): section, rear end and the two lofts it is cut from.

Realism verdicts on the detail-pass cover (both judges, first-person / ADS / hero views): "invented domed rivets along
the top centreline (real covers have none); too thick and round, a half cylinder with a flat sharp rear face and a
diagonal shading seam; it should read as ~1 mm pressed sheet with a gentle crown and a formed rear lip over the
recoil-spring-guide button". The sheet agrees (CRAFT_STUDY 2.2: smooth crown, no ribs, a subtle shoulder line where
crown meets skirt; RIFLE_STUDY: "smooth (no ribs), rounded rear corner"). So, replacing the shouldered / creased
section, the crown studs and the section-prism x side-prism construction (whose ruled rear slope rendered as one flat
face):

- SECTION (Y, Z): vertical skirts to Z SKIRT_TOP, a shoulder of radius SHOULDER_R, a gentle top arc of radius TOP_R
  through the crown (Z 32.7, key dim) -- tangent-continuous; half width 21.75 (key dim 43.5). Rise of the top arc
  ~2.9 mm over its +-16.5 mm: the pressed cover's gentle crown. The shoulder start is the lengthwise shoulder line.
  The section contains the round-2 section everywhere (every clearance to the carrier only grows).
- REAR END: a formed hood, doubly curved: at each station X in the rear zone the part of the section above the lip
  line Z_BASE is scaled vertically by phi(X) = (T(X) - Z_BASE) / (32.7 - Z_BASE), T = the traced centreline rear profile
  (steep lip, ramp, roll into the crown). The centreline follows the trace exactly; the shoulders and skirt tops roll
  down along proportionally lower copies of it, so the end reads as one pressed hood, not a planar ruled slope. The lip
  ends ~1 mm tall at X ~240 (Z 11.6-12.6, just over the receiver's top edges) with the spring-guide button through a hole in its slope.
- SHEET: outer solid (lofted rings, filled) minus the inner solid (the same construction one sheet thickness in: skirt
  at COVER_I, concentric shoulder / top arc, rear profile = T offset 0.98 inward) minus a box under Z_BASE (open bottom
  and rear under the lip: the skirts pass outside the receiver's rear wall). Smooth lofts, so the weighted normals have
  no seam; only the CUT edges (skirt bottoms, lip end, front end, port cutout, button hole) get a crisp 0.3 break.
"""
from __future__ import annotations

import math

import numpy as np

from gunlib import geo2d as G
from gunlib import lod as LOD
from gunlib import mesh as MS

HALF_W = 21.75           # skirt outer half width (rifle_parts.COVER_O; key dim dust_cover_width 43.5)
CROWN_Z = 32.7           # key dim dust_cover_crown_Z
SHOULDER_R = 3.2         # shoulder radius (outer); realism round 2: 8.0 -> 5.0 (judges: "a soft inflated lid, rolled
                         # bulging sides"; a real cover is a tight U stamping with defined edges); last shape round
                         # (ruling 1): 5.0 -> 3.2, the thin pressed sheet's tight bend (outer 3.2 / inner 2.2 on the
                         # 0.98 sheet, real stamped covers: ~2-3 mm bend radii), not a pillowy round
TOP_R = 90.0             # top arc radius (outer); realism round 2: 48 -> 90, rise ~1.8 instead of 2.9 ("flatter top")
WT_C = 0.98              # sheet thickness: HALF_W - COVER_I
Z_BASE = 11.6            # lip line: the rear hood rolls down to it (trace: the lip at X 239.4, Z 10.6-11.6); above
                         # the receiver's top edges (Z 11.0) and the rear trunnion (10.38): the hood never dips into them
PHI0 = 1.0 / (CROWN_Z - Z_BASE)     # the lip's end face: 1.0 mm tall at the centreline
N_SH, N_TOP = 4, 3       # section segments: shoulder arc, top arc (per side) (round 2: R 5 shoulder 4; the R 90 top arc
                         # spans only 11.4 deg a side: 3 segments, sagitta 0.05)
REAR_PTS = [(239.4, 11.6), (240.2, 12.7), (241.5, 13.5), (245.0, 20.1), (250.0, 22.6), (255.0, 25.6), (260.0, 29.3),
            (265.0, 32.1), (268.5, 32.7), (282.0, 32.7)]
STUDS_X = ()             # (detail round 2's crown studs: removed, real covers and the sheet have none)
# REALISM ROUND 2 (2026-10-05): transverse stiffening ribs. Both judges: "no transverse stiffening ribs ... mixes design
# generations" -- the receiver carries the stamped pattern's oval magazine-well dimple, and that pattern's thin cover
# "employs both longitudinal and latitudinal reinforcing ribs" (the lengthwise one is the shoulder line, the skirts'
# vertical-wall top); the cross ribs run across the top and stop at the edge of the vertical wall. They are PRESSED IN
# (0.8 into the outer surface): the main views draw the cover's top line smooth at the crown (side
# trace, key dim 32.7, the 3/4 outline); ribs pressed out stood 0.8 above it, broke L4 and moved the 3/4 camera solve
# (the rear-sight residual flipped to "unexplained"); pressed in, every silhouette stays as traced. The sheet shows the
# cover top in light only in the 3/4 panel, which draws transverse lines near X ~316 and ~377 (TOP-panel calibration);
# the rib pitch keeps them. Ribs: centres RIBS_X, top width RIB_W0, flat floor RIB_W1, depth RIB_H on the top arc,
# fading to 0 over the shoulder (smoothstep in the shoulder angle). The flanks fall at ~42 deg, steeper than the
# cover's 40 deg smoothing / 35 deg weighted-normal sharp limit, so each rib reads crisp, not as a soft wave (a
# one-ring rounded rib rendered as a lumpy, wavy top in the first-person view).
RIBS_X = ()             # LAST SHAPE ROUND (ruling 1, 2026-10-05): the ribs are REMOVED. They rendered as stepped
                        # shingles in the first-person / ADS views, and the sheet draws a SMOOTH cover (CRAFT_STUDY 2.2,
                        # RIFLE_STUDY); rib_rings() keeps the mechanism for a Fab variant, unused here
RIB_W0, RIB_W1, RIB_H = 5.0, 3.2, 0.8
SKIRT_Z_REAR, SKIRT_STEP = 0.75, ((302.3, 0.8), (313.2, 10.3))   # deep rear skirt bottom; the traced slanted step


def _geom(hw, ztop, rs):
    """Shoulder centre height and the tangent angle (deg) between the shoulder arc (radius rs about (hw - rs, zc)) and
    the top arc (radius TOP_R - (HALF_W - hw) about (0, CROWN_Z - TOP_R))."""
    rt = TOP_R - (HALF_W - hw)
    zt0 = CROWN_Z - TOP_R
    a = hw - rs
    zc = zt0 + math.sqrt((rt - rs) ** 2 - a * a)
    ang = math.degrees(math.atan2(zc - zt0, a))
    return zc, ang, rt, zt0


ZC_SH, ANG_T, _, _ = _geom(HALF_W, CROWN_Z, SHOULDER_R)
SKIRT_TOP = ZC_SH        # skirts vertical to here (22.26): the lengthwise shoulder line


def half_section(hw, zb, rs):
    """Right half (Y >= 0) of the section, bottom -> crown top (Y 0 included once): [(y, z)]."""
    zc, ang, rt, zt0 = _geom(hw, CROWN_Z, rs)
    pts = [(hw, zb)]
    for a in np.linspace(0.0, ang, LOD.count(N_SH, 3) + 1):
        pts.append((hw - rs + rs * math.cos(math.radians(a)), zc + rs * math.sin(math.radians(a))))
    for a in np.linspace(ang, 90.0, LOD.count(N_TOP, 3) + 1)[1:]:
        pts.append((rt * math.cos(math.radians(a)), zt0 + rt * math.sin(math.radians(a))))
    pts[-1] = (0.0, pts[-1][1])
    return np.array(pts, float)


def rib_weight(h, hw, rs):
    """Per point of a half section: 0 on the skirt, smoothstep over the shoulder arc, 1 on the top arc."""
    zc, ang, _, _ = _geom(hw, CROWN_Z, rs)
    a = np.degrees(np.arctan2(h[:, 1] - zc, h[:, 0] - (hw - rs)))
    t = np.clip(a / ang, 0.0, 1.0)
    t[h[:, 1] <= zc + 1e-6] = 0.0
    t[np.abs(h[:, 0]) < hw - rs - 1e-6] = 1.0
    return t * t * (3.0 - 2.0 * t)


def _section_normals(h):
    """Outward unit normals of the half section's points (Y >= 0 side; the polyline runs bottom -> crown)."""
    t = np.gradient(h, axis=0)
    t /= np.linalg.norm(t, axis=1)[:, None]
    n = np.c_[t[:, 1], -t[:, 0]]
    n[-1] = (0.0, 1.0)
    return n


def ring(x, hw, zb, rs, phi, bump=0.0):
    """Closed ring (3D) at station x: the section, its part above Z_BASE scaled vertically by phi; bump moves the
    shoulder / top part along the section normal (out > 0, in < 0: a transverse rib's depth at this station)."""
    h = half_section(hw, zb, rs)
    if bump != 0.0:
        h = h + (bump * rib_weight(h, hw, rs))[:, None] * _section_normals(h)
        h[-1, 0] = 0.0
    z = h[:, 1].copy()
    up = z > Z_BASE
    z[up] = Z_BASE + (z[up] - Z_BASE) * phi
    h = np.c_[h[:, 0], z]
    full = np.vstack([h, (h[:-1] * [-1.0, 1.0])[::-1]])          # right bottom -> crown -> left bottom
    return np.c_[np.full(len(full), x), full]


def rear_curve(n_chaikin=3):
    """Outer centreline rear profile T (X, Z), lip -> crown, smoothed (open Chaikin)."""
    P = np.asarray(REAR_PTS, float)
    for _ in range(n_chaikin):
        Q = [P[0]]
        for a, b in zip(P[:-1], P[1:]):
            Q += [0.75 * a + 0.25 * b, 0.25 * a + 0.75 * b]
        Q.append(P[-1])
        P = np.array(Q)
    return P


def offset_curve(P, d):
    """Open polyline offset by d to the right of its direction (inward for the rear profile, which runs lip ->
    crown, i.e. up and forward)."""
    P = np.asarray(P, float)
    t = np.gradient(P, axis=0)
    t /= np.linalg.norm(t, axis=1)[:, None]
    n = np.c_[t[:, 1], -t[:, 0]]
    return P + d * n


def _stations(C, z_top, tol):
    """Station X values along a rear curve C (X increasing) from phi0 to the crown: Douglas-Peucker knots of C."""
    z0 = Z_BASE + PHI0 * (CROWN_Z - Z_BASE)
    i0 = int(np.argmax(C[:, 1] >= z0))
    a, b = C[i0 - 1], C[i0]
    x0 = a[0] + (z0 - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
    D = np.vstack([[x0, z0], C[i0:]])
    D = D[D[:, 1] < z_top - 1e-6]
    keep = G.dp_simplify(np.vstack([D, [[D[-1, 0] + 0.01, z_top]]]), tol) if len(D) > 2 else D
    xs = sorted(set([round(float(x0), 4)] + [round(float(x), 4) for x in np.asarray(keep)[:, 0] if x > x0]))
    return xs


def _phi(C, x, z_top):
    z = float(np.interp(x, C[:, 0], C[:, 1]))
    return min(1.0, max(0.0, (z - Z_BASE) / (z_top - Z_BASE)))


def skirt_bottom(x):
    """Outer skirt bottom Z at x (deep rear skirt, the traced slanted step, the raised skirt Z 9.6 ahead of it)."""
    (x0, z0), (x1, z1) = SKIRT_STEP
    zr = 9.6                                             # receiver_right.CUT_SKIRT_Z
    xs = x0 + (zr - z0) * (x1 - x0) / (z1 - z0)
    if x <= x0:
        return SKIRT_Z_REAR
    if x >= xs:
        return zr
    return z0 + (x - x0) * (z1 - z0) / (x1 - x0)


def rib_rings():
    """{station X: bump} of the cross ribs (pressed in: negative)."""
    ribs = {}
    for xc in (RIBS_X if LOD.LEVEL < 2 else ()):
        for dx, b in ((-RIB_W0 / 2, 0.0), (-RIB_W1 / 2, -RIB_H), (RIB_W1 / 2, -RIB_H), (RIB_W0 / 2, 0.0)):
            ribs[round(xc + dx, 4)] = b
    return ribs


def outer_mesh(x_front):
    C = rear_curve()
    xs = _stations(C, CROWN_Z, LOD.tol(0.08))
    (x0, _), (x1, z1) = SKIRT_STEP
    xs_s = x0 + (9.6 - 0.8) * (x1 - x0) / (z1 - 0.8)
    body = [x for x in (C[-1, 0], 290.0, x0, xs_s, x_front) if x > xs[-1] + 0.5]
    ribs = rib_rings()
    body = [x for x in body if all(abs(x - r) > 1.0 for r in ribs)]
    rings = []
    for x in sorted(set(xs + body + list(ribs))):
        phi = PHI0 if x == xs[0] else _phi(C, x, CROWN_Z)
        rings.append(ring(x, HALF_W, skirt_bottom(x), SHOULDER_R, phi, ribs.get(round(x, 4), 0.0)))
    return MS.loft(rings)


def inner_mesh(x_front, hw_in):
    """The cavity: same construction one sheet in (concentric section, rear profile offset WT_C inward), open below
    (skirt to Z -8) and running past the front end."""
    d = HALF_W - hw_in
    C = offset_curve(rear_curve(), d)
    z_top = CROWN_Z - d
    C = C[C[:, 0] >= C[0, 0]]
    xs = _stations(np.vstack([C, [[C[-1, 0] + 20.0, z_top]]]), z_top, LOD.tol(0.08))
    # (the ribs are not repeated on this unseen inner surface: the 24 extra rings cost ~1.1k triangles over the rifle's
    # 50k ceiling; the sheet is 0.18 thick under a rib floor, a closed solid, never seen from inside the receiver)
    rings = []
    for x in xs + [max(C[-1, 0], xs[-1] + 1.0), x_front + 10.0]:
        phi = _phi(C, x, z_top) if x != xs[0] else max(_phi(C, x, z_top), 1e-3)
        r = ring(x, hw_in, -8.0, SHOULDER_R - d, max(phi, 1e-3))
        rings.append(r)
    return MS.loft(rings)


def centre_top_z(x):
    """Outer centreline Z of the cover at x (the rear profile, then the crown)."""
    C = rear_curve()
    return float(np.interp(x, C[:, 0], C[:, 1]))


def cover_section_outer(zb):
    """Closed CCW (Y, Z) outer section (interface kept for review tools)."""
    h = half_section(HALF_W, zb, SHOULDER_R)
    return G.ccw(np.vstack([h, (h[:-1] * [-1.0, 1.0])[::-1]]))


def is_cut_face(n):
    """A face of a cut (not of the two lofts): horizontal (skirt bottoms, lip bottom), square to X (lip end, front
    end, button hole ends) or square to Y near the centre (button hole sides; caller checks Y), or a port cutout wall
    (normal in the XZ plane, caller checks Y)."""
    return abs(n[2]) > 0.999 or abs(n[0]) > 0.999
