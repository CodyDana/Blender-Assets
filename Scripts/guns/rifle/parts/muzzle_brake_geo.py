"""MUZZLE BRAKE geometry helpers (plain numpy, frame M mm): the brake body as ONE lofted solid whose section at every
angle round the bore already carries the rounded rim of the slant face (no bevel modifier on the rim), and the cutter
for the side slot with its outer edge rounded by real geometry.

Why a loft: a boolean slant cut + bevel modifier could not round the rim (round 1: the boolean leaves sub-0.05 mm
edges and Blender's bevel clamp-overlap limit is global, so the whole bevel collapsed). Here each half-plane section
(X, rho) at angle theta is a closed profile with the same vertex count at every theta, lofted round the axis (closed
loop, genus-1 solid through the bore):

  rear face (chamfered) -> outer surface (the body FLARES: rho = R(x), convex, wider at the front; round 2) ->
  [outer round: quadratic Bezier, tangent t_body along the body, t_face along the face] -> slant face (the plane's
  exact trace z = rho sin(theta)) -> [inner round] -> chamber wall (rho = RI(x): a cone, wall 3.4 at the top of
  the face -> 3.0 at the chin) ->
  chamber floor -> bullet hole -> rear face

Round 2 (2026-10-05): no raised bead / step behind the face (the round-1 judge: 'the lip sticks out like a separate
flared ring with a hard step'); the rim blends into the body through a soft roll. At the bottom the outer round has
unequal tangents (long along the body, most of the face width along the face), so the chin is a full round that
stays level with the body instead of a pointed lip (round-1 tell: 'the lower lip juts forward and down into a pointed
chin'), and its front lands on the side trace (X ~880 at Z ~-9) without the round-1 flat.
"""
from __future__ import annotations

import math

import numpy as np

from gunlib import mesh as MS


def R_of(x, P):
    """Body radius at X: R0 at the rear face, convex flare to RF at XF (exponent PW), constant beyond."""
    f = np.clip((np.asarray(x, float) - P["X0"]) / (P["XF"] - P["X0"]), 0.0, 1.0)
    return P["R0"] + (P["RF"] - P["R0"]) * f ** P["PW"]


def RI_of(x, P):
    """Chamber radius at X: RIA up to XIA, a cone to RIB at XIB (the opening is narrower at the top-rear of the face
    than at the chin: c3 / q34's teardrop mouth, and a thicker rim at the top), constant beyond."""
    f = np.clip((np.asarray(x, float) - P["XIA"]) / (P["XIB"] - P["XIA"]), 0.0, 1.0)
    return P["RIA"] + (P["RIB"] - P["RIA"]) * f


def bez(p0, c, p2, n):
    """n + 1 points of the quadratic Bezier p0 -> p2 with control c (tangent-continuous at both ends)."""
    p0, c, p2 = (np.asarray(v, float) for v in (p0, c, p2))
    return [(1 - t) ** 2 * p0 + 2 * t * (1 - t) * c + t ** 2 * p2 for t in np.linspace(0.0, 1.0, n + 1)]


def _cross(P, s, fn):
    """X where the face plane (X = XC - rho s tan A) meets the surface rho = fn(x) (bisection, monotone)."""
    ta = math.tan(P["A"])
    lo, hi = P["X0"], P["X0"] + 80.0
    for _ in range(60):
        m = 0.5 * (lo + hi)
        if m - (P["XC"] - float(fn(m, P)) * s * ta) > 0:
            hi = m
        else:
            lo = m
    return 0.5 * (lo + hi)


def section(theta, P):
    """Closed (X, rho) profile at angle theta (y = rho cos theta, z = rho sin theta). P: parameter dict.

    With P["LIP_R"] (integration round, 2026-10-05) the face is a FLAT band with small rounds (outer RO_F0..RO_F1 mm
    along the face, top -> chin; inner RI_F) and the outer surface steps up to a raised rim ring of radius LIP_R over
    the last LIP_L mm behind the face (a LIP_STEP ramp): c3's thick flat chamfered rim band standing proud of the
    tube. Without it: round 2's bullnose (outer / inner shares FO0 / FO1 of the face)."""
    s = math.sin(theta)
    X0, c, XCH, RB = P["X0"], P["CH"], P["X_CH"], P["R_BORE"]
    R0 = float(R_of(X0, P))
    lip = "LIP_R" in P
    w = max(0.0, -s) ** 1.5                             # 1 at the bottom (the chin)
    if lip:
        xo = _cross(P, s, lambda x, P_: P_["LIP_R"])
        co = np.array([xo, P["LIP_R"]])
    else:
        xo = _cross(P, s, R_of)
        co = np.array([xo, float(R_of(xo, P))])
    xi = _cross(P, s, RI_of)
    ci = np.array([xi, float(RI_of(xi, P))])
    L = float(np.linalg.norm(ci - co))
    u = (ci - co) / L                                   # along the face, outer -> inner
    if lip:
        tf = min(P["RO_F0"] + (P["RO_F1"] - P["RO_F0"]) * w, 0.6 * L)
        ti = min(P["RI_F"], L - tf - 0.3)
    else:
        # bullnose rim: the outer and inner rounds meet on the face (no flat band)
        fo = P["FO0"] + (P["FO1"] - P["FO0"]) * w
        tf, ti = fo * L, (1.0 - fo) * L - 1e-3
    tb = P["TB0"] + (P["TB1"] - P["TB0"]) * w
    xb = xo - tb
    out = [(X0, R0 - c), (X0 + c, R0 + c * 0.0)]
    x_start = X0 + c
    k_out = P["K_OUT"]
    x_end = (xo - P["LIP_L"] - P["LIP_STEP"]) if lip else xb
    for j in range(1, k_out + 1):                       # flare samples (same count at every theta)
        x = x_start + (x_end - x_start) * j / (k_out + 1)
        out.append((x, float(R_of(x, P))))
    if lip:
        out.append((x_end, float(R_of(x_end, P))))
        out.append((x_end + P["LIP_STEP"], P["LIP_R"]))
        p0 = np.array([xb, P["LIP_R"]])
    else:
        p0 = np.array([xb, float(R_of(xb, P))])
    out += [tuple(p) for p in bez(p0, co, co + u * tf, P["SEG_O"])]
    q0 = ci - u * ti
    xq = xi - ti
    q2 = np.array([xq, float(RI_of(xq, P))])
    out += [tuple(p) for p in bez(q0, ci, q2, P["SEG_I"])]
    k_ch = P["K_CH"]
    for j in range(1, k_ch + 1):
        x = xq + (XCH - xq) * j / (k_ch + 1)
        out.append((x, float(RI_of(x, P))))
    out += [(XCH, float(RI_of(XCH, P))), (XCH, RB), (X0, RB)]   # chamber floor and bullet hole (inside: sharp)
    return np.array(out, float)


def body_loft(P, n) -> MS.Mesh:
    rings = []
    for k in range(n):
        th = 2 * math.pi * k / n
        S = section(th, P)
        rings.append(np.c_[S[:, 0], S[:, 1] * math.cos(th), S[:, 1] * math.sin(th)])
    return MS.loft(rings, closed_loop=True)


def miter_dirs(P):
    """Per-vertex outward miter direction x scale (offset by 1 mm) of a closed CCW polygon (2D)."""
    n = len(P)
    out = np.zeros((n, 2))
    for i in range(n):
        a, b, c = P[i - 1], P[i], P[(i + 1) % n]
        e0, e1 = b - a, c - b
        n0 = np.array([e0[1], -e0[0]]) / max(np.linalg.norm(e0), 1e-12)
        n1 = np.array([e1[1], -e1[0]]) / max(np.linalg.norm(e1), 1e-12)
        m = n0 + n1
        lm = np.linalg.norm(m)
        m = n0 if lm < 1e-9 else m / lm
        out[i] = m / max(float(m @ n0), 1.0 / 3.0)
    return out


def rounded_side_slot(outline, radius_at, R_at, y_end=-0.5, phis=(30.0, 60.0, 90.0), lead=0.9, step=1.2):
    """Cutter for a slot through the wall of a body of revolution (radius R_at(x), axis X) on the -Y side, with its
    OUTER edge rounded by real geometry (no bevel modifier): a loft of the XZ outline offset outward by r(1 - sin phi)
    and sunk r(1 - cos phi) radially below the surface (per-vertex radius r = radius_at(x, z)); a lead ring outside
    the surface on the line of the first facet, then straight walls down to y_end. outline: closed polygon (X, Z),
    re-sampled every `step` mm so the rings follow the surface."""
    from gunlib.geo2d import ccw
    P = ccw(np.asarray(outline, float))
    Q = []
    for i in range(len(P)):
        a, b = P[i], P[(i + 1) % len(P)]
        k = max(1, int(math.ceil(np.linalg.norm(b - a) / step)))
        Q += [a + (b - a) * j / k for j in range(k)]
    P = np.array(Q)
    r = np.array([radius_at(x, z) for x, z in P], float)
    M = miter_dirs(P)

    def ring(o, d):
        Q = P + M * o[:, None]
        rr = np.maximum(R_at(Q[:, 0]) - d, 1e-3)
        y = -np.sqrt(np.maximum(rr ** 2 - Q[:, 1] ** 2, 1e-6))
        return np.c_[Q[:, 0], y, Q[:, 1]]
    ph = np.radians(np.asarray(phis, float))
    o1, d1 = r * (1 - math.sin(ph[0])), r * (1 - math.cos(ph[0]))
    lead_ring = ring(r + lead, -lead * d1 / np.maximum(r - o1, 1e-6))
    far = lead_ring.copy()
    far[:, 1] = -float(np.max(R_at(P[:, 0]))) - 4.0      # planar outer cap well outside the surface
    rings = [far, lead_ring]
    for p_ in ph:
        rings.append(ring(r * (1 - math.sin(p_)), r * (1 - math.cos(p_))))
    rings.append(np.c_[P[:, 0], np.full(len(P), y_end), P[:, 1]])
    return MS.loft(rings)
