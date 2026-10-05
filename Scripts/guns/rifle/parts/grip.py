"""Detail part PISTOL GRIP: loft of rounded sections on the traced side outline, flat bottom, checkered
panels on both sides.

Owns the object: pistol_grip (LOD0) and the review/bake-only checker field pistol_grip_checker (build_checker_field;
NOT built by build(), see grip_checker.py). Authority close-ups: c6 PISTOL GRIP AND TRIGGER (LEFT) and c1 (right), the
3/4 view; H1 hand-fit gate (rifle_h1.py: width / girth at the Grip socket) and the side silhouette must keep passing.
Interfaces: the flange joint Z -34.82, the guard leg GRIP_LEG, the Grip socket (frame B origin).
Detail round 1 (2026-10-05): the checker panel is the quadrilateral measured on c6 + c1 (grip_checker.PANEL_TS,
front-high raked top, ~46 % of the depth in the front half) instead of the axis-aligned 15.9 mm rounded rectangle;
the diamond field is a modelled bead / pyramid slab (groove spacing 1.67 / 1.89, two ~91 deg families measured by FFT)
= the normal-map bake source, rendered in review in place of the bake; recess 0.75; the guard-leg slot is only the
leg's width. Review driver: grip_review.py / grip_loop.py; measurements: grip_measure.py; H1: grip_h1.py.
Detail round 2 (2026-10-05; round-1 blind judge tells): the side outline is the trace reshaped to c6's form
(grip_shape.py: square top-back corner + straight edge into the neck instead of the swell-and-dip, a straight block face
and a soft R 8 / R 16 shoulder under the guard instead of the notch, squarer R 4 heel, round toe nose); flatter sides
with defined strap edges (front R 7, R 4 on the block, back R 9, crown 0.35); bottom round 2.5 (3 seg) with the flange
break as its own pass; the panel = the c6 corners alone, R 0.8, crisp 0.15 wall and a 0.7 flat border band; the cells
= continuous diagonal ridges with shallow cross-notches (A 46 deg / 1.61, B -49 / 1.72); the bake-source field is
clipped with bisect planes (manifold). Inspection: grip_overlay.py (silhouettes), grip_views.py (Workbench views).
Detail round 2b (2026-10-05; round-1 judge tells still open: base, chunkier body, notch under the guard, embossed cells):
the base is LOFTED, not cut: below Z -92.8 the rings turn until they run parallel to the bottom line (grip_chords), the
sides flare out 2.0 mm per side over the last 12 mm and the base rolls under on a R 5 quarter circle (7 rings) to a flat
cap, the chord ends following the trace's heel / toe rounds (no bottom boolean, no bottom bevel; 3126 triangles vs
3974); rounder sides (crown 1.2); front strap on the block R 7 (round 2: R 4, which bulged beside the guard leg in the
3/4 view); heel R 8 (grip_shape.HEEL_R; R 4 stood 4 c6 px proud); top rim round 1.2 (2 seg) outside the leg slot;
the cells are gable-crested ridges with narrow steep A grooves and shallow B notches, crowns 0.25 under the border
surface (cut, not embossed). Checker floor_fn handles the tilted rings.
"""
from __future__ import annotations

import json
import math

import numpy as np

from rifle_common import SPEC
from gunlib import geo2d as G
from gunlib import lod as LOD
from gunlib import mesh as MS
from rifle_parts import GAP


# ======================================================================================== furniture
def trace_outline():
    """The traced side outline (spec side_profile_M), smoothed, top on the flange joint, bottom at the key's Z."""
    P = G.clean_smooth(SPEC.profile("pistol_grip"), 1.4, 1.8, 35.0)
    top = P[:, 1] > -37.6
    P[top & (P[:, 0] > 244.0) & (P[:, 0] < 301.5), 1] = -34.82
    zb = SPEC.key["grip"]["bottom_Z"]
    P[:, 1] = -34.82 + (P[:, 1] + 34.82) * ((zb + 34.82) / (P[:, 1].min() + 34.82))
    P = G.dedupe(P, 0.05)
    return P


_OUTLINE = None


def grip_outline():
    """Detail round 2: the trace reshaped to the c6 close-up's form (grip_shape.py: square top-back corner and a straight
    edge into the neck, a soft shoulder under the guard, squarer heel, round toe nose)."""
    global _OUTLINE
    if _OUTLINE is None:
        from parts import grip_shape
        _OUTLINE = grip_shape.reshape(trace_outline())
    return _OUTLINE.copy()


# ---- pistol grip (form fix round 1): a LOFT of rounded sections, not a slab with edge bevels.
# The slab (flat +-15 sides, 7.5 mm weighted bevel) clamped to almost nothing on the dense traced outline: girth
# 141 mm and a slab look in the 3/4 view. The spec's section is "a rounded oblong (30 wide), flatter sides where the
# checkering sits, straps R 8-10"; the side outline stays the trace. Construction:
#   rings   horizontal sections at Z levels (the top is the horizontal flange joint); each ring is the
#           perpendicular section (rounded rectangle D x W, strap radius R, sides crowned C1-smoothly by `crown`)
#           stretched along X onto the outline's back..front interval at that Z (D = interval * cos(rake));
#   bottom  the rings run on past the heel / toe and the traced bottom chain is cut with a boolean (flat end),
#           then the bottom edges get a 1.0 mm round (2 seg) and the flange edge a 0.5 mm break;
#   panels  checkered panel border = real geometry: a 0.6 mm recess that follows the rounded side (panel prism
#           minus the loft shrunk 0.6 in Y), border bevel 0.3; the diamonds go in the normal map.
GRIP_RAKE = 22.35          # axis rake from vertical (spec)
GRIP_W = float(SPEC.dims("pistol_grip")["width_Y"]) + 1.6   # DETAIL FIX (user checklist 1: "a fuller, rounder grip
                           # section"): 30 -> 31.6 (real-pattern grips 30-36 mm, H1 band [30, 36]; spec proposal R48)
# detail round 2: flatter sides with defined edges where they meet the straps (c6; the round-1 judge read the R 9 /
# R 13.5 straps as "evenly tapered, smoothly blended, almost like rubber"): front strap R 7, back strap R 9, crown
# 0.35 (spec R 9 / R 13.5 / -: proposal in review/detail/grip/spec_proposal.json); H1 girth stays in its band
GRIP_R = 9.0               # front strap R (integration round: 7.0 -> 9.0, the spec R33 value; at R 7 the solved 3/4 view
                           # read the front strap 10 px proud (region core 243 px, 3/4 IoU 0.9137 < 0.915); R 4 on the block stays)
GRIP_R_BACK = 9.0
GRIP_R_TOP = 7.0           # front strap radius on the block beside the guard leg (Z above R_TOP_Z0), ramped to GRIP_R by
R_TOP_Z0, R_TOP_Z1 = -50.0, -68.0   # R_TOP_Z1: c6 draws the block as a flat-sided wedge with a crisp front edge
GRIP_CROWN = 2.0          # side crown (DETAIL FIX 1.2 -> 2.0: a fuller, rounder section; peak toward the front = BELLY)
GRIP_BELLY = 0.55         # DETAIL FIX: the crown's peak sits forward of mid-depth (a belly at the front of the section)
GRIP_NR = 34               # vertices per ring (round 1: 30; the tighter strap radii need the samples)
GRIP_Z_TOP = -34.82
# heel / toe cut levels: the outline's rearmost heel point and foremost toe point (vertical tangents), from the
# reshaped outline (round 1 constants: -117.21 / -127.78)
from parts import grip_shape as _GS  # noqa: E402
GRIP_Z_BACK_CUT, GRIP_Z_FRONT_CUT = _GS.cut_levels(grip_outline())
GRIP_Z_END = -137.0
CARRY_OUT = 0.02           # rings below the heel / toe cut levels: this far outside the outline (round 1: 0.6)


def _hits_x(P, z):
    Q = np.vstack([P, P[:1]])
    xs = []
    for a, b in zip(Q[:-1], Q[1:]):
        if (a[1] - z) * (b[1] - z) <= 0 and a[1] != b[1]:
            t = (z - a[1]) / (b[1] - a[1])
            xs.append(a[0] + t * (b[0] - a[0]))
    return (min(xs), max(xs)) if len(xs) >= 2 else None


def _rrect2(a0, a1, b0, b1, ra, rb, seg=24):
    """Rounded rectangle with corner radius ra at the a0 end (back strap) and rb at the a1 end (front strap)."""
    pts = []
    for (cx, cy, r, s0) in ((a1 - rb, b0 + rb, rb, -90), (a1 - rb, b1 - rb, rb, 0), (a0 + ra, b1 - ra, ra, 90),
                            (a0 + ra, b0 + ra, ra, 180)):
        pts.append(G.arc(cx, cy, r, s0, s0 + 90, seg + 1))
    return G.dedupe(np.vstack(pts))


def grip_section(D, W=GRIP_W, R=GRIP_R, crown=GRIP_CROWN, n=GRIP_NR, Rb=None):
    """Perpendicular section, s = 0 at the back strap .. D at the front strap, y across. Starts at the back strap
    middle (s 0, y 0) and runs CCW in (s, y); n points by arc length (consistent rings for the loft). R = front strap
    radius, Rb = back strap radius (default GRIP_R_BACK)."""
    Rb = GRIP_R_BACK if Rb is None else Rb
    R = min(R, 0.5 * W - 1e-3, 0.5 * D - 1e-3)
    Rb = min(Rb, 0.5 * W - 1e-3, 0.5 * D - 1e-3)
    h = 0.5 * W - crown
    rr = G.ccw(_rrect2(0.0, D, -h, h, Rb, R, 24))
    rr = G.resample(rr, 0.15)
    # crown the flat side runs (C1: zero value and slope where the strap arcs begin)
    s0, s1 = Rb, D - R
    u = (rr[:, 0] - 0.5 * (s0 + s1)) / max(0.5 * (s1 - s0), 1e-6)
    flat = (np.abs(u) < 1.0) & (np.abs(rr[:, 1]) > h - 1e-6)
    uu = np.linspace(-1.0, 1.0, 2001)
    norm = float(((1 - uu ** 2) ** 2 * (1 + GRIP_BELLY * uu)).max())
    rr[flat, 1] += np.sign(rr[flat, 1]) * crown * (1 - u[flat] ** 2) ** 2 * (1 + GRIP_BELLY * u[flat]) / norm
    k = int(np.argmin(rr[:, 0] + 10 * np.abs(rr[:, 1])))          # back strap middle
    rr = np.roll(rr, -k, axis=0)
    Q = np.vstack([rr, rr[:1]])
    dd = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Q, axis=0), axis=1))]
    t = np.linspace(0, dd[-1], LOD.ring(n), endpoint=False)          # LOD: fewer ring points (same on every ring)
    return np.c_[np.interp(t, dd, Q[:, 0]), np.interp(t, dd, Q[:, 1])]


def grip_levels(P, tol=0.12, max_gap=6.0):
    """Z levels for the rings: a level wherever the outline's back or front leaves the straight line between the
    last kept level and the next by > tol mm (chordal error), at most max_gap apart. Form fix round 2: round 1 kept a
    level wherever the back/front MOVED 1.2 mm, which the 22 deg rake alone triggers every ~3 mm on straight runs
    (40 rings; the receiver's restored 0.3 mm arc bevel needs the triangles)."""
    tol, max_gap = LOD.tol(tol), LOD.step(max_gap)                   # LOD: coarser chords
    zs = np.arange(GRIP_Z_TOP - 0.25, GRIP_Z_BACK_CUT + 0.2, -0.25)
    hits = {}

    def H(z):
        if z not in hits:
            hits[z] = _hits_x(P, min(z, GRIP_Z_TOP - 1e-3))
        return hits[z]

    keep = [GRIP_Z_TOP]
    i0 = -1                                   # index in zs of the last kept level (-1 = the top)
    i = 0
    while i < len(zs):
        z0 = keep[-1]
        ok_i = None
        for j in range(i, len(zs)):
            z1 = zs[j]
            if z0 - z1 > max_gap:
                break
            h0, h1 = H(z0), H(z1)
            if h0 is None or h1 is None:
                continue
            bad = False
            for k in range(i, j):
                zk = zs[k]
                hk = H(zk)
                if hk is None:
                    continue
                t = (z0 - zk) / (z0 - z1)
                if (abs(hk[0] - (h0[0] + t * (h1[0] - h0[0]))) > tol
                        or abs(hk[1] - (h0[1] + t * (h1[1] - h0[1]))) > tol):
                    bad = True
                    break
            if bad:
                break
            ok_i = j
        if ok_i is None:
            ok_i = i
        keep.append(float(zs[ok_i]))
        i = ok_i + 1
    keep = [z for z in keep if z > GRIP_Z_BACK_CUT + 0.5]
    keep.append(GRIP_Z_BACK_CUT)
    low = [-121.2, -124.5, -126.5, -129.0, -131.0, -134.0]   # round 2: -122.0 met the panel's front-bottom fillet (2 multi-face edges)
    low = [z for z in low if z < GRIP_Z_BACK_CUT - 0.5 and abs(z - GRIP_Z_FRONT_CUT) > 0.5]
    keep += sorted(low + [GRIP_Z_FRONT_CUT], reverse=True) + [GRIP_Z_END]
    return np.array(keep)


def grip_intervals(P):
    """(z, x_back, x_front) per ring: exact outline hits down to the heel / toe cut levels, then carried straight
    down just outside the outline so the bottom boolean, not the loft, makes the traced bottom. The cut levels are
    the outline's rearmost heel / foremost toe points (vertical tangents), so the carried rings continue the straps
    tangentially; form fix round 2 carries them 0.02 mm outside (round 1: 0.6 mm, which bent the strap out between
    the cut level and the next ring and left a 0.6 mm lip at the toe where the cut met it)."""
    out = []
    xb_heel = _hits_x(P, GRIP_Z_BACK_CUT)[0]
    xf_toe = _hits_x(P, GRIP_Z_FRONT_CUT)[1]
    for z in grip_levels(P):
        h = _hits_x(P, min(z, GRIP_Z_TOP - 1e-3))
        xb = h[0] if (h is not None and z >= GRIP_Z_BACK_CUT) else xb_heel - CARRY_OUT
        xf = h[1] if (h is not None and z >= GRIP_Z_FRONT_CUT) else xf_toe + CARRY_OUT
        out.append((float(z), float(xb), float(xf)))
    return out


# ---- detail round 2b: LOFTED ROUNDED BASE on TILTED RINGS (round-1 judge: "B's base is a thicker, rounder flare and
# blends more gently into the front strap"; c6 / c1 / 3/4 draw a flared, heavily rounded base with a ball-like toe).
# Round 2 cut the loft flat with a boolean along the traced bottom and put a 2.5 mm bevel on it: a thin flat base with a
# sharp toe lip. Horizontal rings cross the ~15 deg sloped bottom, so a profile along it needed ~1.3 mm ring spacing
# (+1300 triangles) and still stair-stepped (2b iterations 1-2); a roll + bevel on the cut read as a chamfer (iteration 4).
# Construction now: rings horizontal down to TILT_Z0, then TRANS_N rings turning progressively until they run parallel
# to the BOTTOM LINE (least squares through the traced bottom chain); base rings at heights e above it (BASE_E), chord
# ends = the outline hits (heel round / toe bulb); the last ROLL rings roll the sides under on a quarter circle of
# radius ROLL_R (sides and strap radii inset by ROLL_R (1 - cos), height ROLL_R (1 - sin)) to a flat bottom cap; their
# chord ends follow the trace's heel / toe rounds (the last two: inset by the remaining roll). No
# bottom boolean, no bottom bevel: the round is modelled. Above the roll the sides flare out (Y only) by FLARE at the
# bottom with a quadratic run-in from FLARE_H.
FLARE = 2.0
FLARE_H = 12.0
ROLL_R = 5.0
ROLL_SEG = 7
ROLL_E_HIT = 0.9                       # roll rings at or above this height take the outline hits as chord ends
TILT_Z0 = -92.82                       # last horizontal ring (a grip_levels level)
TRANS_N = 3                            # rings turning from horizontal to the bottom slope
BASE_E = (13.0, 9.0, 7.0)              # base rings above the roll (e = height above the bottom line, mm); kept >= 1 mm
                                       # from the panel's bottom corners (rear e 12.0, front e 10.0)
_BLINE = None


def bottom_line():
    """(point, forward unit direction, up unit normal) of the least-squares line through the traced bottom chain."""
    global _BLINE
    if _BLINE is None:
        P = grip_outline()
        sel = (P[:, 0] > 234.0) & (P[:, 0] < 262.5) & (P[:, 1] < -124.0)
        c, d = _GS._fit_line(P[sel])
        d = d if d[0] > 0 else -d
        nrm = np.array([-d[1], d[0]])
        nrm = nrm if nrm[1] > 0 else -nrm
        _BLINE = (c, d, nrm)
        # integration (r2b): the least-squares line runs below the traced bottom at its ends, so the flat cap's lowest
        # chord end sat 0.26 under the key's bottom Z (L4 grip.bottom_Z / overall height). Lift the line until the
        # lowest ring chord end is on the key (the rings are planar between their chord ends, so that is the bottom).
        zb = SPEC.key["grip"]["bottom_Z"]
        for _ in range(4):
            low = min(min(A[1], B[1]) for A, B, _f, _r in grip_chords(P))
            if low >= zb - 1e-4:
                break
            c = c + ((zb - low) / nrm[1]) * nrm
            _BLINE = (c, d, nrm)
    return _BLINE


def base_e(x, z):
    """Height (mm) of side-plane points above the bottom line."""
    c, d, nrm = bottom_line()
    return (np.c_[np.atleast_1d(x), np.atleast_1d(z)] - c) @ nrm


def flare_of(e):
    u = min(max(1.0 - e / FLARE_H, 0.0), 1.0)
    return FLARE * u * u


def roll_rings():
    """(e, inset) of the roll-under rings: quarter circle of radius ROLL_R from e = ROLL_R (inset 0) to the cap."""
    th = np.linspace(0.0, 0.5 * math.pi, LOD.count(ROLL_SEG, 2) + 1)
    return [(float(ROLL_R * (1 - math.sin(t))), float(ROLL_R * (1 - math.cos(t)))) for t in th]


def _line_hits(P, Q, u):
    """Parameters t (Q + t u) where the line crosses the closed polygon P, with the crossing points."""
    R = np.vstack([P, P[:1]])
    a, b = R[:-1], R[1:]
    e = b - a
    den = e[:, 0] * u[1] - e[:, 1] * u[0]
    ok = np.abs(den) > 1e-12
    w = a - Q
    dd = np.where(ok, den, 1.0)
    s = np.where(ok, (w[:, 0] * u[1] - w[:, 1] * u[0]) / -dd, -1.0)     # along the edge: a + s e on the line
    X = a + s[:, None] * e
    t = (X - Q) @ u
    m = ok & (s >= 0.0) & (s <= 1.0)
    return t[m], X[m]


def grip_chords(P):
    """Per ring: (A_back, B_front, flare, roll) in the side plane. Horizontal rings: the outline's back / front hits.
    Tilted rings: the extreme hits of the ring line with the outline; roll rings: the chord at e = ROLL_R moved down
    to e and inset `roll` at both ends."""
    out = []
    for z in [z for z in grip_levels(P) if z >= TILT_Z0 - 1e-6]:
        h = _hits_x(P, min(z, GRIP_Z_TOP - 1e-3))
        out.append((np.array([h[0], z]), np.array([h[1], z]), 0.0, 0.0))
    c, d, nrm = bottom_line()
    a = math.radians(GRIP_RAKE)
    ax0, axd = np.array([280.67, -36.0]), np.array([-math.sin(a), -math.cos(a)])   # the grip axis (grip_checker frame)

    def on_axis(Q, u):
        t = np.linalg.solve(np.c_[axd, -u], Q - ax0)
        return ax0 + t[0] * axd

    def chord(Q, u):
        t, X = _line_hits(P, Q, u)
        return X[np.argmin(t)], X[np.argmax(t)]
    A0 = on_axis(np.array([250.0, TILT_Z0]), np.array([1.0, 0.0]))
    A1 = on_axis(c + BASE_E[0] * nrm, d)
    ang1 = math.atan2(d[1], d[0])
    for k in range(1, TRANS_N + 1):
        w = k / (TRANS_N + 1.0)
        ang = (w * w * (3 - 2 * w)) * ang1
        u = np.array([math.cos(ang), math.sin(ang)])
        Ab, Bf = chord(A0 + w * (A1 - A0), u)
        out.append((Ab, Bf, flare_of(float(base_e(*(0.5 * (Ab + Bf)))[0])), 0.0))
    for e in BASE_E:
        Ab, Bf = chord(c + e * nrm, d)
        out.append((Ab, Bf, flare_of(e), 0.0))
    # roll rings: the chord ends follow the trace's own heel round and toe curve (outline hits) down to ROLL_E_HIT; the
    # last rings take that chord moved down and inset by the remaining roll (2b iteration 12: insetting the e = ROLL_R
    # chord by the roll stood ~1.2 mm outside the traced heel and 1.5 mm below the toe and creased the toe)
    Ah = Bh = eh = rh = None
    for e, ins in roll_rings():
        if e >= ROLL_E_HIT - 1e-9:
            Ab, Bf = chord(c + e * nrm, d)
            Ah, Bh, eh, rh = Ab, Bf, e, ins
            out.append((Ab, Bf, flare_of(e), ins))
        else:
            sh = -(eh - e) * nrm
            k = ins - rh
            out.append((Ah + sh + k * d, Bh + sh - k * d, flare_of(e), ins))
    return out


def grip_rings(W=GRIP_W, R=GRIP_R, crown=GRIP_CROWN, n=GRIP_NR, dy=0.0, dr=0.0, Rb=None, base=True):
    """Rings in frame M. dy / dr shrink the half width / strap radius (the panel-recess inner loft). Each ring is the
    perpendicular section (depth D = chord . p, p = the axis-perpendicular) stretched along its chord; base rings add
    the flare to the half width and inset the section by the roll (width, depth and strap radii)."""
    P = grip_outline()
    a = math.radians(GRIP_RAKE)
    p = np.array([math.cos(a), -math.sin(a)])
    rings = []
    for A, B, fl, roll in grip_chords(P):
        if not base:
            fl, roll = 0.0, roll
        D = float((B - A) @ p)
        zc = 0.5 * (A[1] + B[1])
        u = min(max((zc - R_TOP_Z1) / (R_TOP_Z0 - R_TOP_Z1), 0.0), 1.0)
        u = u * u * (3 - 2 * u)                        # smoothstep: 1 on the block, 0 below R_TOP_Z1
        Rz = min(R, R + u * (GRIP_R_TOP - R))
        Wr = W - 2 * dy + 2 * (fl - roll)
        rb = (GRIP_R_BACK if Rb is None else Rb) - dr - roll
        sec = grip_section(D, Wr, max(Rz - dr - roll, 0.6), crown, n, max(rb, 0.6))
        f = sec[:, 0] / D
        x = A[0] + f * (B[0] - A[0])
        z = A[1] + f * (B[1] - A[1])
        rings.append(np.c_[x, sec[:, 1], z])
    return rings


def grip_bottom_cutter():
    """XZ polygon below the traced bottom chain, from the heel cut level round the toe to the front cut level."""
    P = G.ccw(grip_outline())
    b = np.array([_hits_x(P, GRIP_Z_BACK_CUT)[0], GRIP_Z_BACK_CUT])
    f = np.array([_hits_x(P, GRIP_Z_FRONT_CUT)[1], GRIP_Z_FRONT_CUT])
    # CCW (Z up) runs back strap -> heel -> bottom -> toe -> front strap: walk from the vertex after b to before f
    k0 = int(np.argmin(np.hypot(*(P - b).T)))
    k1 = int(np.argmin(np.hypot(*(P - f).T)))
    idx = [(k0 + i) % len(P) for i in range(((k1 - k0) % len(P)) + 1)]
    chain = P[idx]
    chain = chain[(chain[:, 1] < GRIP_Z_BACK_CUT - 1e-6) & (chain[:, 1] < GRIP_Z_FRONT_CUT - 1e-6)
                  | ((chain[:, 0] < 255.0) & (chain[:, 1] < GRIP_Z_BACK_CUT - 1e-6))]
    chain = chain[(np.hypot(*(chain - b).T) > 0.05) & (np.hypot(*(chain - f).T) > 0.05)]
    poly = np.vstack([[b + (-15.0, 0.0)], [b], chain, [f], [f + (15.0, 0.0)],
                      [(f[0] + 15.0, -160.0)], [(b[0] - 15.0, -160.0)]])
    return G.dedupe(poly, 1e-4)


def grip_panel_outline():
    """Checkered panel (per side): the quadrilateral measured on c6 / c1 (grip_checker.PANEL_TS), corners R 2."""
    from parts import grip_checker as GC
    return GC.panel_outline_xz()


BORDER_SEG = 1             # integration r2b: 0.15 x 1 -> 0.4 x 2 (judges r2 / r2b on c1 and c6: our panel had "a crisp raised
                           # border lip", the reference's field is cut in and fades out without a raised border)
BORDER_BEVEL = 0.25        # panel recess wall / leg slot edges (round 1: 0.3; the judge read the rim as soft: "cut into
                           # the surface, with a distinct border line" in the reference)
# FORM REALISM ROUND: the border wall is a crisp CUT edge (0.25 x 1, was 0.4 x 2: a soft rolled lip that read as a
# decal's edge); the recess (grip_checker.RECESS 0.75) and the 0.70 V-cut field are the cut depths
GRIP_LEG = [(298.6, -34.0), (303.3, -34.0), (303.3, -60.0), (298.4, -60.0)]   # guard rear leg (cut back 0.02)
GRIP_LEG_HALF_W = 5.0      # the guard loop's half width (trigger_guard.LOOP_W): detail round 1 cuts the leg slot only
                           # this wide (+ LEG_SIDE_GAP), the full-width cut left a flat notch face and a ledge at Z -60 that
                           # the 3/4 view showed; c6 / 3/4 draw the grip's rounded front wrapping the leg
LEG_SIDE_GAP = 0.05        # slot side clearance: the slot / top / strap corner's bevels pull a vertex ~0.024 into the
                           # slot, so 0.02 left a 0.004 mm gap; 0.05 keeps >= 0.01 (clearance row 0.01-0.05)


def grip_mesh_numpy(W=GRIP_W, R=GRIP_R, crown=GRIP_CROWN, Rb=None):
    """Plain-numpy approximation for silhouette sweeps: the loft with vertices outside the traced bottom moved onto
    it (the Blender build cuts it with a boolean instead)."""
    m = MS.loft(grip_rings(W, R, crown, Rb=Rb))
    V = m.verts()
    cut = grip_bottom_cutter()
    inside = np.array([G.point_in_poly((v[0], v[2]), cut) for v in V])
    P = grip_outline()
    chain = P[P[:, 1] < -110.0]
    for i in np.nonzero(inside)[0]:
        d = np.hypot(chain[:, 0] - V[i, 0], chain[:, 1] - V[i, 2])
        k = int(np.argmin(d))
        V[i, 0], V[i, 2] = chain[k]
    out = MS.Mesh()
    out.add_verts(V)
    out.F = list(m.F)
    return out


BOTTOM_ROUND = 2.5         # bottom end round (round 1: 1.0, 2 seg): c6 draws the toe nose and base edges well rounded
                           # (the round-1 toe read as a thin flange with a sharp lip)


def pred_grip_bottom(mid, d, n1, n2, dih):
    if dih < 25:
        return 0.0
    if mid[2] < GRIP_Z_BACK_CUT + 1.0 or (mid[2] < GRIP_Z_FRONT_CUT + 1.0 and mid[0] > 262.0):
        return 1.0                                   # bottom end: BOTTOM_ROUND mm round
    return 0.0


TOP_ROUND = 2.6            # DETAIL FIX (user checklist 1: "a rounder shoulder where it meets the receiver"): 1.2 -> 2.6,
TOP_SEG = 3                # 3 segments (2b: 1.2 x 2; round 2: a 0.5 break)


def _in_slot_zone(mid):
    return mid[0] > 297.0 and abs(mid[1]) < GRIP_LEG_HALF_W + 1.0


def pred_grip_top(mid, d, n1, n2, dih):
    return 1.0 if (dih >= 25 and mid[2] > GRIP_Z_TOP - 0.3 and not _in_slot_zone(mid)) else 0.0


def pred_grip_flange(mid, d, n1, n2, dih):
    return 1.0 if (dih >= 25 and mid[2] > GRIP_Z_TOP - 0.3 and _in_slot_zone(mid)) else 0.0   # slot top edges: 0.5 break


def build_pistol_grip(coll, offset):
    import bpy
    from gunlib import bl
    ob = MS.loft(grip_rings()).to_object("pistol_grip", coll, offset, smooth_deg=35.0)
    # 2b: the base is lofted and rounded (grip_chords); only the guard-leg slot is cut
    bl.boolean_many(ob, [MS.prism(G.offset(G.ccw(np.array(GRIP_LEG)), GAP), -GRIP_LEG_HALF_W - LEG_SIDE_GAP,
                                  GRIP_LEG_HALF_W + LEG_SIDE_GAP)], "DIFFERENCE", offset=offset)
    bl.clean(ob)
    bl.bevel_weighted(ob, TOP_ROUND, TOP_SEG, pred_grip_top, offset)   # top rim round (outside the guard-leg slot)
    bl.bevel_weighted(ob, 0.5, 1, pred_grip_flange, offset)      # slot top edges: flange joint break
    # panel recess: panel prisms minus the loft shrunk RECESS in Y (the recess follows the rounded side)
    from parts import grip_checker as GC
    panel = grip_panel_outline()
    cut = MS.prism(panel, -25.0, -8.0).to_object("_gpanel", coll, offset)
    bl.boolean(cut, MS.prism(panel, 8.0, 25.0), "UNION", offset=offset)
    inner = MS.loft(grip_rings(dy=GC.RECESS, dr=GC.RECESS)).to_object("_ginner", coll, offset)
    bl.boolean(cut, inner, "DIFFERENCE")
    bpy.data.objects.remove(inner, do_unlink=True)
    bl.boolean(ob, cut, "DIFFERENCE")
    bpy.data.objects.remove(cut, do_unlink=True)
    bl.clean(ob)
    bl.bevel(ob, BORDER_BEVEL, BORDER_SEG, 50.0)
    bl.finish(ob)
    bl.weighted_normals(ob)
    # form fix round 2: the boolean/bevel triangulation left shading blotches beside the checker panel under weighted
    # normals; faces on the loft (or on the recess floor) take the smooth loft normals instead
    src = [MS.loft(grip_rings()).to_object("_gsrc_outer", coll, offset),
           MS.loft(grip_rings(dy=GC.RECESS, dr=GC.RECESS)).to_object("_gsrc_floor", coll, offset)]
    n_on = bl.surface_normals_from(ob, src, tol_mm=0.05, max_angle_deg=20.0)
    for o in src:
        bpy.data.objects.remove(o, do_unlink=True)
    print("[AR01] pistol_grip: %d faces take the loft's smooth normals" % n_on)
    ob["gun_part"] = json.dumps({"bone": "body", "class": "W-round", "slot": "M_AR01_Furniture",
                                 "spec_id": "pistol_grip", "joint": {"type": "butt", "parent": "receiver",
                                                                     "gap_mm": [0.01, 0.05]},
                                 "recipe": [["lofted base roll R %.1f, %d seg" % (ROLL_R, ROLL_SEG)], [TOP_ROUND, 2, "weighted top rim"], [0.5, 1, "weighted slot top"], [BORDER_BEVEL, BORDER_SEG, 50.0]],
                                 "base": {"flare_mm": FLARE, "flare_h_mm": FLARE_H, "roll_R": ROLL_R, "tilted_rings_from_Z": TILT_Z0},
                                 "section": {"construction": "loft of rounded sections", "width_Y": GRIP_W,
                                             "strap_R": GRIP_R, "strap_R_back": GRIP_R_BACK,
                                             "strap_R_block": [GRIP_R_TOP, R_TOP_Z0, R_TOP_Z1], "side_crown": GRIP_CROWN},
                                 "checker_panel": {"corners_ts": GC.PANEL_TS, "corner_R": GC.PANEL_R,
                                                   "recess": GC.RECESS, "border_bevel": BORDER_BEVEL, "border_band": GC.PANEL_SHRINK,
                                                   "cells": {"families_deg_from_vertical": [GC.FAM_A_DEG, GC.FAM_B_DEG],
                                                             "pitch": [GC.PITCH_A, GC.PITCH_B], "apex_h": GC.APEX_H,
                                                             "source": "normal map baked from pistol_grip_checker"}}})
    return ob


def build_checker_field(coll, offset, name="pistol_grip_checker"):
    """The modelled bead / pyramid field on both panels (closed slabs intersected with the panel prism): the normal-map BAKE
    SOURCE. Not part of the LOD0 mesh or the export; the review driver adds it so ROUGH LOOK renders show the cells."""
    from gunlib import bl
    from parts import grip_checker as GC
    import bmesh
    from mathutils import Vector
    floor = GC.floor_fn(grip_rings(dy=GC.RECESS, dr=GC.RECESS))
    fo = GC.field_outline_xz()
    m = GC.pyramid_slab(floor, fo, +1)
    m.extend(GC.pyramid_slab(floor, fo, -1))
    ob = m.to_object(name, coll, offset, smooth_deg=None)
    # clip to the field quad with four bisect planes + cap fills (round 2: the EXACT intersect with the field prism left
    # 1-4 non-manifold edges where lattice lines met the walls; the field quad's corners are R 0.1 after the 0.7 inset,
    # so planes along its straight edges are the same outline to 0.04 mm)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    for p0, nrm in GC.field_clip_planes():
        co = Vector(((p0[0] - offset[0]) / 1000.0, 0.0, (p0[1] - offset[2]) / 1000.0))
        no = Vector((nrm[0], 0.0, nrm[1]))
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        res = bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-9, plane_co=co, plane_no=no, clear_outer=True)
        cut = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
        bmesh.ops.holes_fill(bm, edges=cut, sides=0)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    bl.finish(ob)
    ob.data.polygons.foreach_set("use_smooth", [False] * len(ob.data.polygons))
    ob.data.update()
    ob["gun_part"] = json.dumps({"bone": "body", "class": "bake-source", "slot": "M_AR01_Furniture",
                                 "spec_id": "pistol_grip", "bake_source_for": "pistol_grip", "lod0": False,
                                 "export": False})
    return ob


REVIEW_EXTRAS = (("pistol_grip_checker", build_checker_field),)   # review-only objects (grip_review.py)


# ======================================================================================== module interface
OBJECTS = ('pistol_grip',)            # registry keys built here (rifle_parts.ORDER)
CLOSEUPS = ('c6', 'c1', 'q34')          # sheet panels that are this part's shape authority (rifle_detail.py)


def build(spec, ctx):
    """Build this module's objects into ctx (gunlib.parts.BuildCtx). Returns {registry key: [objects]}; keys that
    ctx.only excludes come back empty. `spec` is the rifle GunSpec (the same object as rifle_common.SPEC)."""
    return {k: ctx.make(k, f) for k, f in (("pistol_grip", build_pistol_grip),)}
