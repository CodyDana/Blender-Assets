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


def master_outer(tol=0.3):
    rr = [r for r in trace("LEFT")["gun_without_magazine"] if r["kind"] == "outer"]
    r = max(rr, key=lambda r: abs(r["area_px"]))
    return G.ccw(clean_ring_true(np.array(r["mm"], float)))


def master_holes(tol=0.25):
    # the see-through holes keep the DP + Chaikin clean-up (their bias is small: IoU +0.001 with the new one, while the
    # guard opening's smoothed polyline left slivers on the guard bar's faces at the lip break)
    return [clean_ring(np.array(r["mm"], float), tol) for r in trace("LEFT")["gun_without_magazine"]
            if r["kind"] == "hole"]


def part_ring(part, tol=0.3, view="LEFT", raw=False):
    rr = trace(view)["parts"][part]
    r = max((r for r in rr if r["kind"] == "outer"), key=lambda r: abs(r["area_px"]))
    P = np.array(r["mm"], float)
    return G.ccw(G.dp_simplify(P, tol) if raw else clean_ring(P, tol))


def part_holes(part, tol=0.25):
    return [clean_ring(np.array(r["mm"], float), tol) for r in trace("LEFT")["parts"][part] if r["kind"] == "hole"]


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
