"""Pistol grip side outline, detail round 2 (2026-10-05): the traced side outline (spec side_profile_M, the authority
for scale and position) reshaped where the c6 close-up (the grip's shape authority) and the round-1 blind judge show
a different FORM, each change kept small enough that the side-view L2 per-part gate (pistol_grip IoU >= 0.95) holds:

  back top   the trace's rounded swell just under the receiver (back edge 245.9 at Z -40.5, then a dip to 250.9 at
             Z -53) read as a hump; c6 draws a squarer flat top corner and an almost straight edge running forward-down
             into the neck -> a straight line from a square top corner (BACK_TOP) to the neck (BACK_NECK), blended
             C1 into the traced backstrap by BACK_BLEND_Z.
  front      the trace's shoulder under the trigger guard (vertical block to Z -58, a 53 deg chamfer, a corner at Z -64)
             read as a small sharp notch / step, and its block face swelled 1.3 mm at Z -50 under a concave top; c6
             draws a straight block face directly behind the leg and one broad soft sweep into the raked front strap ->
             a straight block face (BLOCK_X) and the chamfer's corners rounded FRONT_R. (Tried: the block face behind
             the leg with no slot; the guard's rear face in the current asset runs 298.7-300.5, which opened a visible
             gap in the side view.)
  heel       squarer than the trace's ~10 mm chamfer-round: the back line and the bottom line (least-squares fits on the
             trace) meet in a HEEL_R fillet.
  toe        c6 draws a fuller, more defined forward toe flare with a round nose (the trace's nose is a point): a
             round nose 1 mm further forward (TOE_NOSE) between the traced bottom and the traced front strap.
All functions take and return a CCW outline in the side plane (x = frame-M X, y = frame-M Z); CCW walks UP the front
strap, back along the top, DOWN the back strap, round the heel, forward along the bottom and up round the toe.
"""
from __future__ import annotations

import numpy as np

from gunlib import geo2d as G

Z_TOP = -34.82
BACK_TOP = (248.6, Z_TOP)       # square top-back corner (trace: rounded 251.3 -> 247.6 over Z -36 .. -37.3, swell 245.9)
BACK_NECK = (251.0, -48.0)      # end of the straight edge (the trace is at 249.9 here, its neck 250.9 at Z -53)
BACK_BLEND_Z = -64.0            # C1 blend from the straight edge into the traced backstrap
FRONT_B_Z = -82.0               # the traced strap (fitted over Z -67 .. -82) is kept below here
BLOCK_X = 300.0                 # block front face (the trace runs 299.2 at the flange, 300.4 at Z -50, 299.1 at Z -58:
                                # a swell under a concave top); hidden behind the guard leg in the side view
FRONT_R = (8.0, 16.0)           # fillets: convex under the block, concave into the strap (the trace: two sharp corners)
HEEL_R = 8.0                    # heel fillet radius (2b: c6 draws the heel rounder than round 2's R 4, which stood 4 panel px
                                # proud of the c6 heel; the trace is a ~10 chamfer-round; round 2: R 4)
TOE_NOSE = (271.2, -127.4)      # toe nose: foremost point, vertical tangent (trace 270.2 at Z -127.6, pointed)
TOE_TOP_Z = -116.0              # toe curve joins the traced front strap here ...
TOE_BOT_X = 261.0               # ... and the traced bottom here
TOE_L = (0.7, 0.8, 0.6, 0.9)    # Hermite tangent lengths / chord: bottom, nose (in), nose (out), strap


def _hits(P, z):
    Q = np.vstack([P, P[:1]])
    xs = []
    for a, b in zip(Q[:-1], Q[1:]):
        if (a[1] - z) * (b[1] - z) <= 0 and a[1] != b[1]:
            t = (z - a[1]) / (b[1] - a[1])
            xs.append(a[0] + t * (b[0] - a[0]))
    return (min(xs), max(xs)) if len(xs) >= 2 else None


def _nearest(P, pt, mask=None):
    d = np.hypot(P[:, 0] - pt[0], P[:, 1] - pt[1])
    if mask is not None:
        d = np.where(mask, d, np.inf)
    return int(np.argmin(d))


def _splice(P, i0, i1, new):
    """Replace P[i0..i1] (inclusive, CCW order, may wrap) with `new` (ordered from P[i0] to P[i1])."""
    n = len(P)
    run = [(i0 + k) % n for k in range(((i1 - i0) % n) + 1)]
    keep = [i for i in range(n) if i not in set(run)]
    # rotate so the kept chain starts right after the run
    start = (i1 + 1) % n
    order = [(start + k) % n for k in range(n) if (start + k) % n in set(keep)]
    return np.vstack([P[order], np.asarray(new, float)])


def _hermite(p0, p1, m0, m1, n=40):
    t = np.linspace(0.0, 1.0, n)[:, None]
    h00 = 2 * t ** 3 - 3 * t ** 2 + 1
    h10 = t ** 3 - 2 * t ** 2 + t
    h01 = -2 * t ** 3 + 3 * t ** 2
    h11 = t ** 3 - t ** 2
    return h00 * p0 + h10 * m0 + h01 * p1 + h11 * m1


def _fit_line(pts):
    """Least-squares line through pts: (point, unit direction)."""
    c = pts.mean(0)
    u, s, vt = np.linalg.svd(pts - c)
    return c, vt[0]


def back_top(P):
    """Square top corner + straight edge to the neck + C1 blend into the traced backstrap (back chain walked down)."""
    back = P[:, 0] < 265.0
    i0 = _nearest(P, (256.0, Z_TOP), back & (np.abs(P[:, 1] - Z_TOP) < 0.05))        # on the flat top
    i1 = _nearest(P, (P[:, 0][back].min(), BACK_BLEND_Z), back & (np.abs(P[:, 1] - BACK_BLEND_Z) < 1.5))
    p1 = P[i1]
    # traced slope dx/dz at the blend end
    j = _nearest(P, (p1[0], p1[1] - 4.0), back & (P[:, 1] < p1[1] - 2.0) & (P[:, 1] > p1[1] - 6.0))
    m1 = (P[j, 0] - p1[0]) / (P[j, 1] - p1[1])
    a, b = np.array(BACK_TOP), np.array(BACK_NECK)
    m0 = (b[0] - a[0]) / (b[1] - a[1])
    line = np.c_[np.linspace(a[0], b[0], 12), np.linspace(a[1], b[1], 12)]
    zz = np.linspace(b[1], p1[1], 14)
    s = (zz - b[1]) / (p1[1] - b[1])
    dz = p1[1] - b[1]
    xx = ((2 * s ** 3 - 3 * s ** 2 + 1) * b[0] + (s ** 3 - 2 * s ** 2 + s) * m0 * dz
          + (-2 * s ** 3 + 3 * s ** 2) * p1[0] + (s ** 3 - s ** 2) * m1 * dz)
    new = np.vstack([P[i0], line, np.c_[xx, zz][1:]])
    return _splice(P, i0, i1, new)


def _intersect(c1, d1, c2, d2):
    t = np.linalg.solve(np.c_[d1, -d2], c2 - c1)
    return c1 + t[0] * d1


def _fillet_open(pts, radii, seg=10):
    """Open polyline with every interior corner rounded by its radius (tangent arcs)."""
    out = [pts[0]]
    for k in range(1, len(pts) - 1):
        a, K, b = pts[k - 1], pts[k], pts[k + 1]
        u, v = (K - a) / np.hypot(*(K - a)), (b - K) / np.hypot(*(b - K))
        turn = np.arccos(np.clip(u @ v, -1, 1))
        if turn < 1e-6:
            out.append(K)
            continue
        r = radii[k - 1]
        tl = r * np.tan(turn / 2)
        T1, T2 = K - u * tl, K + v * tl
        side = np.sign(u[0] * v[1] - u[1] * v[0])        # + = left turn
        nrm = side * np.array([-u[1], u[0]])
        O = T1 + nrm * r
        a0 = np.arctan2(*(T1 - O)[::-1])
        aa = a0 + side * np.linspace(0, turn, seg)
        out.extend(np.c_[O[0] + r * np.cos(aa), O[1] + r * np.sin(aa)])
    out.append(pts[-1])
    return np.array(out)


def front_shoulder(P):
    """Front of the grip from the flange down to the raked strap (FRONT_B_Z): the block's straight front face (BLOCK_X;
    the guard leg sits in grip.GRIP_LEG's slot, which now runs out through the convex sweep), then the trace's shoulder chamfer with its two corners rounded FRONT_R (convex R 8 under the
    block, broad concave R 16 into the strap). CCW walks the front UP: the run goes from B (strap) to a point on the
    flat top."""
    front = P[:, 0] > 265.0
    iB = _nearest(P, (_hits(P, FRONT_B_Z)[1], FRONT_B_Z), front)
    top = (np.abs(P[:, 1] - Z_TOP) < 0.05) & (P[:, 0] > 280.0) & (P[:, 0] < 296.0)
    iT = _nearest(P, (294.0, Z_TOP), top)
    B = P[iB].copy()
    L0, db = np.array([BLOCK_X, Z_TOP]), np.array([0.0, -1.0])
    cs, ds = _fit_line(P[front & (P[:, 1] < -67.0) & (P[:, 1] > -82.01)])
    cc, dc = _fit_line(P[front & (P[:, 1] < -60.0) & (P[:, 1] > -64.5)])
    ds = ds if ds[1] > 0 else -ds
    K2 = _intersect(cs, ds, cc, dc)                      # strap x chamfer (concave)
    K1 = _intersect(cc, dc, L0, db)                      # chamfer x block face (convex)
    Kt = L0 + db * ((Z_TOP - L0[1]) / db[1])             # block face x flange (square corner, 0.5 break)
    Bp = cs + ds * ((B[1] - cs[1]) / ds[1])
    new = _fillet_open(np.array([Bp, K2, K1, Kt]), [FRONT_R[1], FRONT_R[0]], 12)
    return _splice(P, iB, iT, np.vstack([new, P[iT]]))


def heel(P):
    """Back line and bottom line meeting in a HEEL_R fillet (CCW: down the back, round the heel, forward along the
    bottom)."""
    back = (P[:, 0] < 240.0) & (P[:, 1] < -100.0) & (P[:, 1] > -116.5)
    c1, d1 = _fit_line(P[back])
    d1 = d1 if d1[1] < 0 else -d1                    # going down
    bot = (P[:, 0] > 236.0) & (P[:, 0] < 256.5) & (P[:, 1] < -124.0)
    c2, d2 = _fit_line(P[bot])
    d2 = d2 if d2[0] > 0 else -d2                    # going forward
    # corner = intersection
    M = np.c_[d1, -d2]
    t = np.linalg.solve(M, c2 - c1)
    C = c1 + t[0] * d1
    # fillet: centre on the bisector inside the corner
    turn = np.arccos(np.clip(-d1 @ d2, -1, 1))       # interior angle at C
    dist = HEEL_R / np.tan(turn / 2)
    T1 = C - d1 * dist
    T2 = C + d2 * dist
    nrm1 = np.array([-d1[1], d1[0]])                 # left of travel = interior for CCW
    O = T1 + nrm1 * HEEL_R
    a0 = np.arctan2(*(T1 - O)[::-1])
    aa = np.linspace(a0, a0 + (np.pi - turn), 10)   # centre on the left of travel: the point runs CCW round O
    arc = np.c_[O[0] + HEEL_R * np.cos(aa), O[1] + HEEL_R * np.sin(aa)]
    assert np.hypot(*(arc[-1] - T2)) < 1e-6, (arc[-1], T2)
    i0 = _nearest(P, (P[(P[:, 0] < 245) & (np.abs(P[:, 1] + 110.0) < 1.2), 0].min(), -110.0),
                  (P[:, 0] < 245) & (np.abs(P[:, 1] + 110.0) < 1.2))
    i1 = _nearest(P, (241.0, -127.0), P[:, 1] < -124.0)
    p0, p1 = P[i0], P[i1]
    seg1 = np.c_[np.linspace(p0[0], T1[0], 6), np.linspace(p0[1], T1[1], 6)]
    seg2 = np.c_[np.linspace(T2[0], p1[0], 5), np.linspace(T2[1], p1[1], 5)]
    new = np.vstack([seg1, arc[1:-1], seg2])
    return _splice(P, i0, i1, new), {"corner": C.round(2).tolist(), "T1": T1.round(2).tolist(),
                                     "T2": T2.round(2).tolist()}


def toe(P):
    """Round toe nose: the traced bottom (TOE_BOT_X) -> the nose (TOE_NOSE, vertical tangent) -> a concave scoop -> the
    traced front strap (TOE_TOP_Z); two cubic Hermite pieces. CCW walks forward along the bottom and up the front."""
    bot = P[:, 1] < -128.5
    i0 = _nearest(P, (TOE_BOT_X, -132.0), bot & (P[:, 0] < 262.0))
    front = (P[:, 0] > 262.0) & (P[:, 1] > -125.0)
    i1 = _nearest(P, (_hits(P, TOE_TOP_Z)[1], TOE_TOP_Z), front)
    p0, p1 = P[i0].copy(), P[i1].copy()
    sel = bot & (P[:, 0] > p0[0] - 10.0) & (P[:, 0] < p0[0] + 0.01)
    _, d0 = _fit_line(P[sel])
    d0 = d0 if d0[0] > 0 else -d0
    sel = (P[:, 0] > 262.0) & (P[:, 1] > p1[1] - 0.01) & (P[:, 1] < p1[1] + 10.0)
    _, d1 = _fit_line(P[sel])
    d1 = d1 if d1[1] > 0 else -d1
    N = np.array(TOE_NOSE)
    up = np.array([0.0, 1.0])
    c0, c1 = np.hypot(*(N - p0)), np.hypot(*(p1 - N))
    a = _hermite(p0, N, TOE_L[0] * c0 * d0, TOE_L[1] * c0 * up, 22)
    b = _hermite(N, p1, TOE_L[2] * c1 * up, TOE_L[3] * c1 * d1, 18)
    return _splice(P, i0, i1, np.vstack([a, b[1:]]))


def reshape(P):
    P = G.ccw(np.asarray(P, float))
    P = back_top(P)
    P = G.ccw(P)
    P = front_shoulder(P)
    P, info = heel(P)
    P = G.ccw(P)
    P = toe(P)
    P = G.dedupe(G.ccw(P), 0.05)
    return P


def cut_levels(P):
    """(heel cut Z, toe cut Z): the outline's rearmost heel point and foremost toe point (vertical tangents)."""
    h = P[(P[:, 1] < -100.0) & (P[:, 0] < 250.0)]
    zb = float(h[np.argmin(h[:, 0]), 1])
    t = P[(P[:, 1] < -118.0) & (P[:, 0] > 255.0)]
    zf = float(t[np.argmax(t[:, 0]), 1])
    return zb, zf
