"""Pistol grip checkering (detail pass, grip round 1): the measured panel and the modelled pyramid field.

MEASURED ON THE CLOSE-UPS (2026-10-05; WorkFiles/guns/rifle/review/detail/grip/measure_r1.json, grip_measure.py):
  panel   corners picked on 5x gridded zooms of c6 (true left) and c1 (true right) and back-projected through the
          solved part cameras onto the grip surface. c1 and c6 agree within 0.9 mm across the axis (s) and 0.3-0.9 mm
          along it at the bottom corners; the top corners differ by 5.6-5.9 mm along it. In the grip axis frame (t down the 22.35 deg axis from
          the junction (280.67, -36.0), s toward the front strap) the panel is a quadrilateral, NOT an axis-aligned
          rectangle: its top edge is raked front-HIGH (t 18.0 at the front, 29.8 at the rear), its bottom edge is
          square to the axis (t ~88), its edges lean ~3-4 deg forward of the axis (front s 11.2 -> 15.5, rear -6.9 ->
          -3.9), ~46 % of the grip's depth, hugging the front half. Corners R 2 (drawn nearly sharp). c6 (the grip's
          primary authority) is weighted 2 : 1 over c1; the two differ mainly in the top edge (c6 t 16.1 / 27.9, c1
          21.7 / 33.8: the close-ups are stylised drawings, each camera is fitted to the grip's own outline).
  cells   FFT of the checkered field (c6 five windows, c1 four; medians): two groove families ~91 deg apart, family
          A along 49.9 deg from vertical (running down toward the REAR; c6 48.2, c1 51.5), family B along 40.8 deg
          the other way (down toward the FRONT; c6 45.0, c1 36.6), perpendicular spacing A 1.67 mm (c6 1.64, c1 1.70),
          B 1.89 mm (c6 1.90, c1 1.88) -> near-square diamonds set ~45 deg to the side view (the spec's "pitch
          1.2-1.5, elongated along the axis" is the craft note; the close-up is the authority, proposal in
          review/detail/grip/spec_proposal.json).
CONSTRUCTION: the LOD0 grip carries the panel border as real geometry (0.6 recess, 0.3 bevel, grip.py); the diamonds
are a separate modelled pyramid field (this module) = the BAKE SOURCE for the crisp normal map (user default
2026-10-04). It is not part of SK_AR01 / SM_AR01 and not in the LOD0 count: the production build leaves it out; the
review driver (grip_review.py) adds it so the ROUGH LOOK renders, which have no per-part normal maps, show what the
bake will show. Cells are beads on the ~90-deg lattice (a heightfield on a lattice-aligned sub-grid, bead_height): crowns 0.70 above
the recess floor (0.05 under the border surface), narrow steep A grooves 0.05 under the floor, shallow B grooves
(saddle 0.50): c6 / c1 draw rows of bright beads along A between dark A grooves; each side is a closed slab
intersected with the panel prism.
ROUND 2 (2026-10-05): see the constants below (c6-only panel corners, R 0.8, 0.7 border band; lattice re-measured with
spectra summed over 40 px windows through the solved cameras; ridges + shallow notches instead of beads); the field is
clipped with four bisect planes (field_clip_planes) instead of the prism intersect.
ROUND 2b (2026-10-05; judge: "coarse, raised, pillow-like diamonds ... looks embossed" vs "fine, shallow cut"): crowns
lowered to 0.50 over the floor (0.25 under the border surface: the field sits cut into the side), gable crests instead of
the flat crown plateau (U profile 0 / 0.72 / 1.0 / 0.72 at 0 / 0.1 / 0.5 / 0.9), B notches 0.43; c6 FFT A 0.998 /
-1.3 deg, B 1.058 / -3.5 deg, ridge / notch amplitude 2.64 (ref 4.48; a sharp symmetric V gave 1.04 = a square net).
floor_fn reads rings on tilted lines (the grip's base rings since round 2b).
"""
from __future__ import annotations

import math

import numpy as np

from gunlib import geo2d as G
from gunlib import mesh as MS

AX_RAKE = 22.35
JUNCTION = np.array([280.67, -36.0])
# panel corners (t, s): front-top, rear-top, rear-bottom, front-bottom (c6 weighted 2 : c1 1, see the docstring)
# round 2: c6 alone (the grip's shape authority; round 1 averaged c6 2 : c1 1, which lowered the front-top corner 1.9 mm
# and flattened the raked top edge the judge missed); corners nearly sharp as drawn (R 0.8; round 1 R 2)
PANEL_TS = [(16.12, 10.97), (27.86, -7.06), (87.99, -4.12), (87.59, 15.19)]
PANEL_R = 0.8
RECESS = 0.75            # border step = groove depth (90-deg-ish cutter at the measured 1.67-1.89 pitch; H1 width
                         # through the floor keeps >= 30 - 0.25)
# diamond lattice (frame M, side plane XZ): groove family directions from vertical (+ = down toward the rear)
# round 2 (grip_fft.py: power spectrum summed over 5 windows of 40 px, directions through the solved cameras):
# c6 A 44.3 deg / 1.59 mm, B -52.1 / 1.63 (B power 1/20 of A); c1 A 51.1 / 1.66, B -41.1 / 2.07; c6 weighted 2 : 1
FAM_A_DEG = 46.0
FAM_B_DEG = -49.0
# DETAIL FIX (2026-10-05, user checklist 1): real-pattern DIAMOND checkering, two equal crossed V-cut families at one
# pitch (round 2b's ridges + shallow notches read as hatching, not checkering); pitch 1.7 (real pattern 1.5-2 mm)
PITCH_A = 1.80           # FORM REALISM ROUND: 1.5 -> 1.8 (c6 FFT 1.6-1.9; real 1.5-2): at 1.5 the field averaged to a
                         # flat tone in the realism views ('reads like a decal'); 1.8 resolves as cut diamonds
PITCH_B = 1.80           # family B
PITCH = 0.5 * (PITCH_A + PITCH_B)
APEX_H = 0.70            # detail fix: diamond tops 0.05 under the border surface = the cut field (the grooves are cut INTO
                         # the wood, the tops are what is left of the surface; 2b: 0.50, round 2: 0.70)
SADDLE_H = 0.0           # B-notch bottom above the floor: shallow, narrow cross-notches on continuous A ridges (the
                         # reference's B family carries ~1/20 of A's power: elongated beads on diagonal ridges)
GROOVE_SINK = 0.05       # groove lines below the recess floor (hidden in the floor)
SLAB_BACK = 0.5          # slab back face below the floor
PANEL_SHRINK = 0.30      # integration r2b: 0.7 -> 0.35 (the flat band read as a raised border lip); field outline inside the recess wall: a flat border band (round 1: 0.05, cells ran into the
                         # wall); the reference draws a distinct border line round the cut field


def axis_frame():
    a = math.radians(AX_RAKE)
    d = np.array([-math.sin(a), -math.cos(a)])           # down the grip axis
    p = np.array([math.cos(a), -math.sin(a)])            # toward the front strap
    return d, p


def ts_to_xz(T):
    d, p = axis_frame()
    T = np.asarray(T, float)
    return JUNCTION + T[:, :1] * d + T[:, 1:2] * p


def xz_to_ts(P):
    d, p = axis_frame()
    Q = np.asarray(P, float) - JUNCTION
    return np.c_[Q @ d, Q @ p]


# DETAIL FIX (2026-10-05, user checklist 1): the panel border FOLLOWS THE GRIP'S CURVED OUTLINE with rounded corners
# (rounds 1-2b: the c6 quadrilateral with R 0.8 corners, which read as a pasted-on slab). Built in the axis frame (t
# down the axis, s toward the front strap): the back edge runs PANEL_MB inside the back strap's outline, the front edge
# PANEL_MF inside the front strap's (both following their curves; the toe flare / shoulder bulge are clamped off at
# FRONT_S_MAX so the edge follows the strap, not the flare), the top edge is c6's raked front-high line and the bottom
# edge runs parallel to the grip's sloped base PANEL_E above it; corners R PANEL_CORNER_R.
PANEL_MB = 13.5                  # back edge inside the back strap outline (c6: s -7.1 at t 28 -> -4.1 at t 88)
PANEL_MF = (8.5, 6.0)            # front edge inside the front strap outline at the top / bottom (c6: s 11.0 -> 15.2)
FRONT_S_MAX = 20.6               # the front strap's s without the toe flare / shoulder bulge
PANEL_TOP = ((16.12, 10.97), (27.86, -7.06))   # c6's raked top edge (t, s), front-high
PANEL_E = 11.0                   # bottom edge height above the grip's base line (c6 corners: rear e 12, front e 10)
PANEL_CORNER_R = 3.5
_PANEL = {}


def _cross2(u, v):
    return float(u[0] * v[1] - u[1] * v[0])


def _strap_s(TS, t):
    Q = np.vstack([TS, TS[:1]])
    ss = []
    for a, b in zip(Q[:-1], Q[1:]):
        if (a[0] - t) * (b[0] - t) <= 0 and a[0] != b[0]:
            u = (t - a[0]) / (b[0] - a[0])
            ss.append(a[1] + u * (b[1] - a[1]))
    return (min(ss), max(ss)) if len(ss) >= 2 else None


def panel_outline_xz(seg=4, r=None):
    """Checkered panel (per side), XZ (frame M), CCW: back / front edges follow the grip's strap outlines (smoothed),
    top = c6's raked line, bottom = parallel to the grip's base; rounded corners R PANEL_CORNER_R."""
    key = (seg, r)
    if key in _PANEL:
        return _PANEL[key].copy()
    from parts import grip as GR
    from parts import magazine_geo as MG
    TS = xz_to_ts(GR.grip_outline())
    back, front = [], []
    for t in np.arange(4.0, 110.01, 1.0):
        h = _strap_s(TS, t)
        if h is None:
            continue
        w = float(np.clip((t - 16.0) / 72.0, 0.0, 1.0))
        back.append((t, h[0] + PANEL_MB))
        front.append((t, min(h[1], FRONT_S_MAX) - (PANEL_MF[0] + w * (PANEL_MF[1] - PANEL_MF[0]))))
    back, front = np.array(back), np.array(front)
    k = np.ones(5) / 5.0                                    # smooth the strap edges (the outline's pixel wobble)
    for E in (back, front):
        E[2:-2, 1] = np.convolve(E[:, 1], k, "valid")
    P = G.ccw(ts_to_xz(np.vstack([front[::-1], back])))
    inside = ts_to_xz([(60.0, 3.0)])[0]
    a, b = ts_to_xz(list(PANEL_TOP))
    P = MG.clip_halfplane(P, a, b - a, _cross2(b - a, inside - a) > 0)
    c, d, nrm = GR.bottom_line()
    p0 = c + PANEL_E * nrm
    P = MG.clip_halfplane(P, p0, d, _cross2(d, inside - p0) > 0)
    P = G.dp_simplify(G.ccw(G.dedupe(P, 0.05)), 0.2)      # long chords along the straps (<= 0.2 off the curve) so the
                                                          # corner fillets are not clamped by short edges
    P = G.ccw(G.fillet(G.ccw(P), PANEL_CORNER_R if r is None else r, seg=seg + 2, min_turn_deg=25.0))
    _PANEL[key] = P
    return P.copy()


def floor_fn(rings):
    """y(x, z) of the +Y side of a lofted surface given as rings: each ring lies on a LINE in the side plane (horizontal,
    or tilted since grip detail round 2b: z = z0 + k x). Linear in x along each ring's +Y half; between the two rings
    whose lines bracket z at that x, linear in the ring heights there."""
    lines, halves = [], []
    for r in rings:
        h = r[r[:, 1] > 1e-6]
        o = np.argsort(h[:, 0])
        halves.append((h[o, 0], h[o, 1]))
        if np.ptp(r[:, 0]) > 1e-6:
            k, z0 = np.polyfit(r[:, 0], r[:, 2], 1)
        else:
            k, z0 = 0.0, float(r[0, 2])
        lines.append((k, z0))
    K = np.array([l[0] for l in lines])
    Z0 = np.array([l[1] for l in lines])

    def f(x, z):
        x = np.atleast_1d(np.asarray(x, float))
        z = np.atleast_1d(np.asarray(z, float))
        out = np.empty(len(x))
        for i, (xi, zi) in enumerate(zip(x, z)):
            zr = Z0 + K * xi                                   # every ring's height at this x (top to bottom)
            o = np.argsort(zr)
            zs = zr[o]
            j = int(np.clip(np.searchsorted(zs, zi), 1, len(zs) - 1))
            z_lo, z_hi = zs[j - 1], zs[j]
            w = 0.0 if z_hi == z_lo else (zi - z_lo) / (z_hi - z_lo)
            a = halves[o[j - 1]]
            b = halves[o[j]]
            out[i] = (1 - w) * np.interp(xi, a[0], a[1]) + w * np.interp(xi, b[0], b[1])
        return out
    return f


def lattice_basis():
    """Unit normals of the two groove families in XZ (orthonormal when the families are 90 deg apart)."""
    def nrm(deg):
        a = math.radians(deg)
        d = np.array([-math.sin(a), -math.cos(a)])        # line direction, + = down toward the rear (-X)
        return np.array([-d[1], d[0]])
    return nrm(FAM_A_DEG), nrm(FAM_B_DEG)


# DETAIL FIX (2026-10-05, user checklist 1): REAL-PATTERN DIAMOND CHECKERING. Two equal V-cut families at one pitch:
# each cell is a small pyramid (worn flat top 16 % of the cell) between crossed grooves. Rounds 1-2b modelled continuous
# A ridges with shallow B notches (read as hatching / stripes, judge: "smooth recessed oval panel"); the user's
# checklist asks for the crossed cut diamonds of the real pattern. Sub-grid per cell: groove line, flat-top start,
# flat-top end (both families).
U_FR = (0.0, 0.42, 0.58)
V_FR = (0.0, 0.42, 0.58)
FADE = 0.35              # the diamonds run down into the groove floor over this width at the field's (curved) edge


def bead_height(fu, fv, saddle=0.0):
    """Height fraction (0 = groove bottom, 1 = the diamond's flat top) at cell fractions fu, fv: the lower of the two
    families' triangle profiles (a pyramid). `saddle` is unused (kept for the old signature)."""
    fr, hh = [0.0, 0.42, 0.58, 1.0], [0.0, 1.0, 1.0, 0.0]
    return np.minimum(np.interp(fu, fr, hh), np.interp(fv, fr, hh))


def _signed_dist(P, Q):
    """Signed distance of points P (n, 2) to the closed polygon Q (negative inside)."""
    R = np.vstack([Q, Q[:1]])
    a, b = R[:-1], R[1:]
    e = b - a
    L2 = np.maximum((e * e).sum(1), 1e-12)
    d = np.full(len(P), np.inf)
    for i in range(len(a)):
        t = np.clip(((P - a[i]) @ e[i]) / L2[i], 0.0, 1.0)
        X = a[i] + t[:, None] * e[i]
        d = np.minimum(d, np.hypot(*(P - X).T))
    inside = np.zeros(len(P), bool)                      # even-odd ray test, vectorised over the points
    for i in range(len(a)):
        (x0, y0), (x1, y1) = a[i], b[i]
        cr = (y0 > P[:, 1]) != (y1 > P[:, 1])
        xint = x0 + (P[:, 1] - y0) * (x1 - x0) / ((y1 - y0) if y1 != y0 else 1e-300)
        inside ^= cr & (P[:, 0] < xint)
    return np.where(inside, -d, d)


def pyramid_slab(floor, outline_xz, side=+1, pa=PITCH_A, pb=PITCH_B, margin=1):
    """Closed slab over the outline's lattice bounding box: the diamond heightfield on top (sub-grid U_FR x V_FR per
    cell: grooves GROOVE_SINK under the recess floor, flat tops APEX_H above it), faded to the groove floor outside the
    field outline, a back face SLAB_BACK under the floor, walls round the box. side +1 = +Y (true left), -1 = -Y.
    Each pyramid corner quad is split along the diagonal through its odd corner, so the four facets are planar."""
    nA, nB = lattice_basis()
    M2 = np.vstack([nA / pa, nB / pb])                     # (a, b) = M2 @ xz: groove indices of the two families
    ab = outline_xz @ M2.T
    a0, b0 = np.floor(ab.min(0)).astype(int) - margin
    a1, b1 = np.ceil(ab.max(0)).astype(int) + margin
    Minv = np.linalg.inv(M2)
    ua = np.concatenate([a + np.array(U_FR) for a in range(a0, a1)] + [[float(a1)]])
    vb = np.concatenate([b + np.array(V_FR) for b in range(b0, b1)] + [[float(b1)]])
    A, B = np.meshgrid(ua, vb, indexing="ij")
    P = np.c_[A.ravel(), B.ravel()] @ Minv.T
    fl = floor(P[:, 0], P[:, 1])
    lo, hi = -GROOVE_SINK, APEX_H
    f = bead_height(A.ravel() % 1.0, B.ravel() % 1.0)
    sd = _signed_dist(P, outline_xz)
    f = np.minimum(f, np.clip(-sd / FADE, 0.0, 1.0))
    h = lo + (hi - lo) * f
    nu, nv = len(ua), len(vb)
    F = f.reshape(nu, nv)
    m = MS.Mesh()
    iT = m.add_verts(np.c_[P[:, 0], side * (fl + h), P[:, 1]]).reshape(nu, nv)
    iK = m.add_verts(np.c_[P[:, 0], side * (fl - SLAB_BACK), P[:, 1]]).reshape(nu, nv)
    for i in range(nu - 1):
        for j in range(nv - 1):
            c = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
            hv = [F[q] for q in c]
            odd = None
            for k in range(4):
                others = [hv[x] for x in range(4) if x != k]
                if max(others) - min(others) < 1e-9 and abs(hv[k] - others[0]) > 1e-9:
                    odd = k
            if odd is not None and odd % 2 == 1:           # diagonal (i+1, j) - (i, j+1)
                m.face((iT[c[0]], iT[c[1]], iT[c[3]]))
                m.face((iT[c[1]], iT[c[2]], iT[c[3]]))
            else:                                          # diagonal (i, j) - (i+1, j+1)
                m.face((iT[c[0]], iT[c[1]], iT[c[2]]))
                m.face((iT[c[0]], iT[c[2]], iT[c[3]]))
            m.face((iK[i, j + 1], iK[i + 1, j + 1], iK[i + 1, j], iK[i, j]))
    ring = ([(i, 0) for i in range(nu - 1)] + [(nu - 1, j) for j in range(nv - 1)]
            + [(i, nv - 1) for i in range(nu - 1, 0, -1)] + [(0, j) for j in range(nv - 1, 0, -1)])
    for k in range(len(ring)):
        p_, q_ = ring[k], ring[(k + 1) % len(ring)]
        m.face((iT[p_], iK[p_], iK[q_], iT[q_]))
    return m                                               # winding fixed by to_object's recalc (closed solid)


def field_outline_xz(extra=0.0):
    return G.offset(panel_outline_xz(), -(PANEL_SHRINK + extra))


def field_clip_planes(pad=0.6):
    """Convex hull of the field outline (grown pad) as (point, outward normal) pairs in XZ: the clip planes of the
    bake-source field (grip.build_checker_field). Inside the hull the cells fade to the groove floor outside the
    (possibly concave) field outline (pyramid_slab)."""
    Q = field_outline_xz()
    pts = sorted(set(map(tuple, np.round(Q, 6))))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    H = G.ccw(np.array(lower[:-1] + upper[:-1]))
    H = G.offset(H, pad)
    out = []
    for k in range(len(H)):
        a, b = H[k], H[(k + 1) % len(H)]
        if np.hypot(*(b - a)) < 1e-6:
            continue
        d = (b - a) / np.hypot(*(b - a))
        out.append((a, np.array([d[1], -d[0]])))        # right of travel = outward for CCW
    return out
