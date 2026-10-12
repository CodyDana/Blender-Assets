"""SMG01 outline geometry from the traces (plain Python + numpy; safe inside Blender).

- the master side outline (LEFT gun_without_magazine: outer ring + see-through holes), Douglas-Peucker simplified;
- the upper / lower split (the drawn seam, the V tongue, the magwell front face) as polylines in M, from the trace
  CONFIG's hand-read seam points (panel px -> M through the LEFT trace's own mapping);
- the TOP-view body widths (spec widths; the fore-end step and the front corner chamfers read off the TOP trace);
- small 2D helpers (open-polyline offset, polygon from a polyline + closure).
"""
from __future__ import annotations

import math

import numpy as np

from smg_common import PanelMap, trace, trace_rings, dims, box, D as SPECD
from gunlib import geo2d as G

LM = PanelMap("LEFT")


def L(pts):
    return LM.mm(np.asarray(pts, float))


# ------------------------------------------------------------------------------------------------ master outline
# The sheet is 0.94 px/mm: a traced ring carries ~1 mm pixel stairs on every slanted or curved edge. Rings are cleaned
# before they become geometry: Douglas-Peucker at up to 0.9 mm (below one pixel; scaled down for small parts), then
# corner-preserving Chaikin rounds on the curved runs (turns < 40 deg), so a moulded edge reads as a clean line or a
# fair curve and a real corner stays crisp.
CLEAN_TOL_MAX = 0.9
CORNER_DEG = 40.0


def _turns(P):
    a = P - np.roll(P, 1, 0)
    b = np.roll(P, -1, 0) - P
    cr = a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]
    return np.degrees(np.abs(np.arctan2(cr, (a * b).sum(1))))


def chaikin_keep_corners(P, corner_deg=CORNER_DEG, iters=2):
    P = np.asarray(P, float)
    corner = _turns(P) >= corner_deg
    for _ in range(iters):
        n = len(P)
        out, oc = [], []
        for i in range(n):
            a, b = P[i], P[(i + 1) % n]
            if corner[i]:
                out.append(a)
                oc.append(True)
            else:
                out.append(0.75 * a + 0.25 * b)
                oc.append(False)
            if not corner[(i + 1) % n]:
                out.append(0.25 * a + 0.75 * b)
                oc.append(False)
        P, corner = np.array(out), np.array(oc)
    return P


def clean_ring(P, tol=0.3):
    P = np.asarray(P, float)
    x, y = P[:, 0], P[:, 1]
    area = 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))
    r_eq = math.sqrt(area / math.pi)
    t = max(tol, min(CLEAN_TOL_MAX, 0.1 * r_eq))
    Q = G.dp_simplify(P, t)
    if len(Q) < 4:
        return Q
    return G.dedupe(chaikin_keep_corners(Q))


def clean_ring_true(P, tol=0.5, sigma_mm=1.0, straight_mm=6.0, snap_mm=0.8, sag_mm=0.05):
    """(W1b fix round) The master outline's clean-up without the corner-cutting bias: a Gaussian-smoothed contour
    (sigma 1.0 mm: the 1 px stairs go, crisp corners > 40 deg pinned: geo2d.clean_smooth) whose points along every
    straight run (a Douglas-Peucker 0.5 segment >= 6 mm) are snapped onto that run, then simplified at 0.05 mm sagitta.
    Measured on the LEFT master silhouette: IoU 0.9932 against the trace (the DP 0.9 + Chaikin clean_ring: 0.9857, its
    corner cutting pushed every concave run outward, e.g. 86 px of the stock neck). (Tried and dropped in the same
    round: smoothing without pins, with or without snapping: the booleans of the stock frame / lower receiver broke and
    the lower strut fell under 0.95. The pins' blend back to the raw stairs leaves short zig-zags here and there: noted
    for the close-up realism pass.)"""
    P = G.ccw(np.asarray(P, float))
    D = G.ccw(G.dp_simplify(P, tol))
    S = G.ccw(G.clean_smooth(P, 0.6, sigma_mm))
    S2 = S.copy()
    for i in range(len(D)):
        a, b = D[i], D[(i + 1) % len(D)]
        ab = b - a
        L2 = float(ab @ ab)
        if L2 < straight_mm ** 2:
            continue
        t = ((S - a) @ ab) / L2
        proj = a + np.outer(t, ab)
        m = (t > 0.0) & (t < 1.0) & (np.linalg.norm(S - proj, axis=1) < snap_mm)
        S2[m] = proj[m]
    Q = G.dedupe(G.dp_simplify(S2, sag_mm), 0.2)        # no edge under 0.2 mm
    return G.ccw(G.dp_simplify(Q, sag_mm))


def _turn_deg(a, b, c):
    u, v = b - a, c - b
    return math.degrees(abs(math.atan2(u[0] * v[1] - u[1] * v[0], float(u @ v))))


def _smooth_open(R, sig_pts):
    """Gaussian smoothing of an open run with both ends held (odd reflection about the ends: a straight run stays
    straight, the end tangents are kept)."""
    n = len(R)
    if n < 4 or sig_pts <= 0:
        return R.copy()
    r = int(3 * sig_pts) + 1
    a, b = R[0], R[-1]
    pre = 2 * a - R[1:r + 1][::-1]
    post = 2 * b - R[-r - 1:-1][::-1]
    if len(pre) < r:
        pre = np.vstack([np.repeat(pre[:1], r - len(pre), 0), pre])
    if len(post) < r:
        post = np.vstack([post, np.repeat(post[-1:], r - len(post), 0)])
    E = np.vstack([pre, R, post])
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sig_pts) ** 2)
    k /= k.sum()
    out = np.zeros_like(R)
    for j, w in zip(range(-r, r + 1), k):
        out += w * E[r + j: r + j + n]
    out[0], out[-1] = a, b
    return out


# (W1 realism round 1) The close-up judges read the traced outlines' residue as torn / chipped edges: the pins of
# clean_ring_true blend back to the raw pixel stairs (short zig-zags), clean_ring's DP 0.3 keeps sub-pixel steps on the
# small parts (the trigger's stepped tip, the guard's notched rim) and every long gentle run keeps a slow wobble (the
# stock arm's lumpy top). fair_ring:
#   1. the true corners: vertices of the Douglas-Peucker 0.75 polyline (the 1.065 mm pixel stair's half-diagonal is
#      0.53: the stairs go, a drawn edge stays) turning >= 40 deg with an adjacent segment >= 1.5 mm (longer than a
#      pixel step);
#   2. each run of the RAW ring between two corners resampled at 0.4 mm and Gaussian-smoothed (sigma 1.5 mm) with its
#      ends held (odd reflection: corners stay crisp, the curve passes through the stairs' middle, unbiased);
#   3. every straight stretch (a DP segment >= 5 mm) snapped onto the total-least-squares line of its raw points (the
#      slow wobble of a gently sloped edge, whose stair period is longer than any smoothing, goes);
#   4. simplified at 0.04 mm sagitta, no edge under 0.2 mm. No point is ever pulled back to the raw stairs.
FAIR_DP, FAIR_CORNER_DEG, FAIR_MIN_SEG, FAIR_SIGMA, FAIR_STRAIGHT = 0.75, 40.0, 1.5, 1.5, 5.0


def _tls_line(Q):
    c = Q.mean(0)
    u = np.linalg.svd(Q - c)[2][0]
    return c, u / np.linalg.norm(u)


def fair_ring(P, dp=FAIR_DP, corner_deg=FAIR_CORNER_DEG, min_seg=FAIR_MIN_SEG, sigma=FAIR_SIGMA, step=0.4,
              sag=0.04, straight=FAIR_STRAIGHT, snap=0.8, min_edge=0.2):
    P = G.dedupe(G.ccw(np.asarray(P, float)), 1e-6)
    r_eq = math.sqrt(abs(G.area(P)) / math.pi)          # small rings: tolerances scale down (a 3 mm part keeps its shape)
    dp, sigma, min_seg = min(dp, 0.15 * r_eq), min(sigma, 0.2 * r_eq), min(min_seg, 0.3 * r_eq)
    D = G.dp_simplify(P, dp)
    n = len(D)
    if n < 4:
        return G.ccw(D)
    di = [int(np.argmin(np.einsum("ij,ij->i", P - d, P - d))) for d in D]     # D's vertices as indices into P
    order = np.argsort(di)
    D, di = D[order], [di[k] for k in order]
    L = np.linalg.norm(np.roll(D, -1, 0) - D, axis=1)          # segment i: D[i] -> D[i + 1]
    corners = [i for i in range(n) if _turn_deg(D[i - 1], D[i], D[(i + 1) % n]) >= corner_deg
               and (L[i - 1] >= min_seg or L[i] >= min_seg)]
    N = len(P)

    def raw_run(i0, i1):                                         # P[i0] .. P[i1] along the ring (wrapping)
        if i1 <= i0:
            i1 += N
        return np.array([P[k % N] for k in range(i0, i1 + 1)])

    if not corners:
        S = G.smooth(G.resample(P, step), sigma / step)
    else:
        out = []
        for k, ci in enumerate(corners):
            cj = corners[(k + 1) % len(corners)]
            run = raw_run(di[ci], di[cj])
            R = G.resample(run, step, closed=False)
            R[0], R[-1] = run[0], run[-1]
            out.append(_smooth_open(R, sigma / step)[:-1])
        S = np.vstack(out)
    # straight stretches onto their least-squares lines
    for i in range(n):
        if L[i] < straight:
            continue
        a, b = D[i], D[(i + 1) % n]
        c, u = _tls_line(raw_run(di[i], di[(i + 1) % n]))
        ab = b - a
        t = ((S - a) @ ab) / float(ab @ ab)
        nrm = np.array([-u[1], u[0]])
        dist = (S - c) @ nrm
        m = (t > 0.08) & (t < 0.92) & (np.abs(dist) < snap)
        S[m] = S[m] - np.outer(dist[m], nrm)
    Q = G.dedupe(G.dp_simplify(G.dedupe(S, 0.05), sag), min_edge)      # no outline edge under 0.2 mm: the
    return G.ccw(G.dp_simplify(Q, sag))                                 # prisms' side faces stay UD-safe


def straight_span(P, a, b):
    """Replace the ring's run between the vertices nearest a and b (the shorter way round) by the straight segment."""
    P = np.asarray(P, float)
    ia = int(np.argmin(np.linalg.norm(P - np.asarray(a, float), axis=1)))
    ib = int(np.argmin(np.linalg.norm(P - np.asarray(b, float), axis=1)))
    i0, i1 = min(ia, ib), max(ia, ib)
    if i1 - i0 <= len(P) - (i1 - i0):
        return np.vstack([P[:i0 + 1], P[i1:]])
    return P[i0:i1 + 1].copy()


# (W1 realism round 1) the lower rail's rear end: the trace's 2-3 mm stair notch between the fore-end bottom (485.1,
# -32.0) and the rail's bottom (490.0, -37.3) built a hooked flap of the lower's wall round the rail end (judges: torn /
# jagged geometry above the magwell). The sheet draws one rounded step there: a straight chamfer between the two.
MASTER_SPANS = [((485.08, -32.04), (490.04, -37.28))]

# (W1 realism round 2) Two drawn concave curves kept a few 20-25 deg corner clusters after fair_ring (its corner rule
# holds them crisp, its 0.04 sag simplification leaves long flats between): across the full-width prisms they read as
# hard crease lines (judges: the stock arm's curved top 'visibly faceted', the tang behind the grip 'lumpy, faceted,
# polygonal steps'). The sheet draws both as one smooth sweep. Each run between two held vertices on straight stretches
# is re-smoothed (Gaussian sigma 3.0 mm, ends held) and kept dense (1.0 mm chords, turn per chord <= ~5 deg):
#   the top strut rising into the hinge head (X 181 .. 233.7), the tang from the end block's flat bottom down into the
#   grip's back strap (X 253 .. 294.9)
#   and (sigma 1.5-2.0) the trigger guard's outer corners: its front-bottom chamfer down to the foot under the paddle
#   (X 386 .. 412.8) and the notch where the bottom bar meets the grip's front strap (X 331 .. 349.7; judges: the bar
#   runs into the grip with no blend; real guards are moulded into the grip with a radius)
MASTER_CURVES = [((181.25, 13.26), (233.68, 25.05), 3.0), ((253.1, -29.1), (294.9, -57.7), 3.0),
                 ((386.18, -89.55), (412.8, -78.07), 1.5, 0.5), ((331.19, -97.3), (349.65, -89.34), 2.0, 0.5)]
# (W4 review fixes, craft G3) the guard's two smoothed corners kept at 0.5 mm chords (were 1.6: on their ~3 mm radii
# that is 2-4 flat facets of ~30 deg each at 3x); 0.5 keeps each chord <= ~9 deg, sagitta <= 0.01 mm


def smooth_span(P, a, b, sigma, step=0.3, out_step=1.0):
    """Replace the ring's run between the vertices nearest a and b (the shorter way round) by its Gaussian-smoothed
    version (ends held), resampled at out_step."""
    P = G.ccw(np.asarray(P, float))
    n = len(P)
    ia = int(np.argmin(np.linalg.norm(P - np.asarray(a, float), axis=1)))
    P = np.roll(P, -ia, axis=0)
    ib = int(np.argmin(np.linalg.norm(P - np.asarray(b, float), axis=1)))
    rev = ib > n - ib
    if rev:                                                     # the shorter run goes backwards: walk it forwards
        P = np.vstack([P[:1], P[1:][::-1]])
        ib = n - ib
    run = P[:ib + 1]
    R = G.resample(run, step, closed=False)
    R[0], R[-1] = run[0], run[-1]
    S = _smooth_open(R, sigma / step)
    S2 = G.resample(S, out_step, closed=False)
    S2[0], S2[-1] = run[0], run[-1]
    Q = np.vstack([S2, P[ib + 1:]])
    return G.ccw(G.dedupe(Q, 0.05))


# (W1 realism round 2) the receiver's front face above the barrel's flange: the trace zig-zags there (563.1 / 15.6 ->
# 564.1 / 16.7 -> 563.8 / 20.9 -> back down to 562.9 / 19.0 -> 562.3 / 19.6 .. 25.5 -> 561.9 / 27.5), a 1 mm step back
# and a stack of near-parallel prism strips across the whole width; round the eyelet they fanned into the streaks the
# judges saw on the 'flat front face'. The drawn face is one plane (X 563.3, spec front_face_X) up to the top chamfer,
# whose own traced line (561.9 / 27.46 -> 559.95 / 36.9, 11.7 deg) meets it at Z 20.68 (the trace's 562.28 / 25.46
# lies on that line within 0.03).
MASTER_POLYS = [((563.86, 15.41), (559.95, 36.9), [(563.3, 16.0), (563.3, 20.68)])]


def replace_span(P, a, b, pts):
    """Replace the ring's run between the vertices nearest a and b (the shorter way round) by a -> pts -> b."""
    P = G.ccw(np.asarray(P, float))
    n = len(P)
    ia = int(np.argmin(np.linalg.norm(P - np.asarray(a, float), axis=1)))
    P = np.roll(P, -ia, axis=0)
    ib = int(np.argmin(np.linalg.norm(P - np.asarray(b, float), axis=1)))
    mid = np.asarray(pts, float)
    if ib > n - ib:                       # the shorter run goes backwards (a, n-1, .., b): forwards it is b .. a
        Q = np.vstack([P[:ib + 1], mid[::-1]])
    else:
        Q = np.vstack([P[:1], mid, P[ib:]])
    return G.ccw(G.dedupe(Q, 0.05))


def master_outer(tol=0.3):
    rr = [r for r in trace("LEFT")["gun_without_magazine"] if r["kind"] == "outer"]
    r = max(rr, key=lambda r: abs(r["area_px"]))
    P = fair_ring(np.array(r["mm"], float))
    for a, b in MASTER_SPANS:
        P = straight_span(P, a, b)
    for a, b, pts in MASTER_POLYS:
        P = replace_span(P, a, b, pts)
    for c in MASTER_CURVES:
        P = smooth_span(P, c[0], c[1], c[2], out_step=c[3] if len(c) > 3 else 1.0)
    return G.ccw(P)


def master_holes(tol=0.25):
    return [fair_ring(np.array(r["mm"], float)) for r in trace("LEFT")["gun_without_magazine"]
            if r["kind"] == "hole"]


def part_ring(part, tol=0.3, view="LEFT", raw=False):
    rr = trace(view)["parts"][part]
    r = max((r for r in rr if r["kind"] == "outer"), key=lambda r: abs(r["area_px"]))
    P = np.array(r["mm"], float)
    return G.ccw(G.dp_simplify(P, tol) if raw else fair_ring(P))


def part_holes(part, tol=0.25):
    return [fair_ring(np.array(r["mm"], float)) for r in trace("LEFT")["parts"][part] if r["kind"] == "hole"]


# ------------------------------------------------------------------------------------------------ the seam
# the trace CONFIG's seam points (LEFT panel px): end-block seam, horizontal seam, the lower's front tab, the V tongue,
# the magwell front face (trace_reference.CONFIG LEFT regions)
# (W1b fix round: the horizontal run's row 211.0 -> 210.5: the drawn seam line is one pixel; the trace's part labels give
# it to the lower, so the upper / lower boundary lies on the line's upper edge, Z -16.3, not its centre -16.8)
SEAM_PX = [(352.5, 210.5), (219.0, 210.5), (217.0, 206.5), (191.0, 206.5), (172.0, 231.0), (147.0, 205.5),
           (141.0, 228.0)]
END_BLOCK_FRONT_X = float(L([(352.5, 150.0)])[0, 0])           # the end block's front edge seam (X ~265.2)
END_BLOCK_REAR_X = float(L([(369.5, 150.0)])[0, 0])            # the hinge gap (X ~247.2)
SEAM_GAP = 0.4                                                  # design seam 0.3-0.5 wide (RP19)


def seam_polyline():
    """Rear -> front: (end block front, seam Z) ... the V ... down the magwell front face, extended 12 mm below."""
    S = L(SEAM_PX)
    a, b = S[-2], S[-1]
    d = (b - a) / np.linalg.norm(b - a)
    return np.vstack([S, b + d * 12.0])


def offset_polyline(P, d):
    """Offset an open polyline by d (left of the direction of travel = +), mitered joins."""
    P = np.asarray(P, float)
    n = len(P)
    N = []
    for i in range(n - 1):
        t = P[i + 1] - P[i]
        t /= np.linalg.norm(t)
        N.append(np.array([-t[1], t[0]]))
    out = [P[0] + N[0] * d]
    for i in range(1, n - 1):
        m = N[i - 1] + N[i]
        m /= np.linalg.norm(m)
        out.append(P[i] + m * d / max(float(m @ N[i]), 0.3))
    out.append(P[-1] + N[-1] * d)
    return np.array(out)


def seam_z_at(x):
    """Seam Z (the horizontal run) at X (rear part only)."""
    S = seam_polyline()
    return float(np.interp(x, [S[0, 0], S[1, 0]], [S[0, 1], S[1, 1]]))


def line_x_at_z(a, b, z):
    a, b = np.asarray(a, float), np.asarray(b, float)
    return float(a[0] + (b[0] - a[0]) * (z - a[1]) / (b[1] - a[1]))


# ------------------------------------------------------------------------------------------------ TOP widths
UP = dims("upper_receiver")
Y_L, Y_R = UP["width_Y_left_right"]                     # body (spec, TOP)
F_L, F_R = UP["width_fore_end_X560_584"]                # fore-end (spec, TOP)
FORE_END_STEP_X = 486.5                                 # the fore-end step's front end (the trace's region seam X 484.0
#                                                         + 2.5: kept off the V tongue's top corner, which sits there)
FRONT_FACE_X = float(UP["front_face_X"])
FRONT_CHAMFER = 3.5                                     # the vertical front corners (3/4 + TOP: ~4 mm in at X 556-560)


def top_outline_upper(x0, x_front=None):
    """Plan outline (X, Y) of the upper receiver: the body width, a 45 deg step in to the fore-end, the chamfered
    vertical front corners."""
    xf = FRONT_FACE_X if x_front is None else x_front
    s = FORE_END_STEP_X
    c = FRONT_CHAMFER
    dl, dr = Y_L - F_L, F_R - Y_R                       # step sizes (left in, right in)
    P = [(x0, Y_R), (s - dr, Y_R), (s, F_R), (xf - c, F_R), (xf, F_R + c), (xf, F_L - c), (xf - c, F_L), (s, F_L),
         (s - dl, Y_L), (x0, Y_L)]
    return np.array(P, float)


def polygon_from(pts):
    return G.ccw(G.dedupe(np.asarray(pts, float)))
