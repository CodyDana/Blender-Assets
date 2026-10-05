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
PITCH_A = 1.61           # perpendicular groove spacing, family A
PITCH_B = 1.72           # family B
PITCH = 0.5 * (PITCH_A + PITCH_B)
APEX_H = 0.70            # bead ridge above the recess floor (0.05 under the border surface; facets ~40 deg)
SADDLE_H = 0.60          # B-notch bottom above the floor: shallow, narrow cross-notches on continuous A ridges (the
                         # reference's B family carries ~1/20 of A's power: elongated beads on diagonal ridges)
GROOVE_SINK = 0.05       # groove lines below the recess floor (hidden in the floor)
SLAB_BACK = 0.5          # slab back face below the floor
PANEL_SHRINK = 0.7       # field outline inside the recess wall: a flat border band (round 1: 0.05, cells ran into the
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


def panel_outline_xz(seg=4, r=PANEL_R):
    """Panel quadrilateral with rounded corners, XZ (frame M), CCW."""
    C = ts_to_xz(PANEL_TS)
    return G.ccw(G.fillet(G.ccw(C), r, seg=seg, min_turn_deg=5.0))


def floor_fn(rings):
    """y(x, z) of the +Y side of a lofted surface given as rings (each (n, 3) at constant z): linear in x along each
    ring's +Y half, linear in z between rings."""
    Z = np.array([r[0, 2] for r in rings])
    halves = []
    for r in rings:
        h = r[r[:, 1] > 1e-6]
        o = np.argsort(h[:, 0])
        halves.append((h[o, 0], h[o, 1]))
    order = np.argsort(Z)
    Zs = Z[order]

    def f(x, z):
        x = np.atleast_1d(np.asarray(x, float))
        z = np.atleast_1d(np.asarray(z, float))
        out = np.empty(len(x))
        for i, (xi, zi) in enumerate(zip(x, z)):
            k = int(np.clip(np.searchsorted(Zs, zi), 1, len(Zs) - 1))
            z0, z1 = Zs[k - 1], Zs[k]
            w = 0.0 if z1 == z0 else (zi - z0) / (z1 - z0)
            a = halves[order[k - 1]]
            b = halves[order[k]]
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


# bead profile on a lattice-aligned sub-grid (cell-local fractions): across the A grooves (u) steep flanks to a shoulder
# at 0.15 then a gentle crown (narrow, deep A grooves read as dark crevices with bright bead tops, as c6 / c1 draw);
# along the A lines (v) the shallow B saddle at the cell edge
# round 2: B = narrow shallow notches across continuous A ridges (round 1's equally strong B saddles read as stamped
# square knurls; the reference's ridges dominate, B carries ~1/20 of A's power)
U_FR = (0.0, 0.15, 0.5, 0.85)          # + the next cell's 0: narrow deep A grooves (they read dark in soft light, as the
U_H = (0.0, 0.72, 1.0, 0.72)           # reference's dirt-filled grooves do) and a low crown; a plain V lit along c6's
                                       # ridges vanished (A power 1/3 of the reference)
V_FR = (0.0, 0.2, 0.8)                 # along the ridge: a shallow notch with ~30 deg walls (steep walls drew bright cross
V_H = (None, 1.0, 1.0)                 # lines = a square net; a full bead swell made every bead a bright dot = knurls)


def bead_height(fu, fv, saddle):
    """Height fraction (0 = A groove bottom, 1 = bead crown) at sub-grid fractions fu (across A), fv (along A)."""
    pu = np.interp(fu, list(U_FR) + [1.0], list(U_H) + [0.0])
    pv = np.interp(fv, list(V_FR) + [1.0], [saddle] + list(V_H[1:]) + [saddle])
    return np.minimum(pu, pv)


def pyramid_slab(floor, outline_xz, side=+1, pa=PITCH_A, pb=PITCH_B, margin=1):
    """Closed slab over the outline's lattice bounding box: the bead heightfield on top (sub-grid U_FR x V_FR per
    cell: A grooves GROOVE_SINK under the recess floor, crowns APEX_H above it, B saddles SADDLE_H), a back face
    SLAB_BACK under the floor, walls round the box. side +1 = +Y (true left), -1 = mirrored to -Y."""
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
    saddle = (SADDLE_H - lo) / (hi - lo)
    h = lo + (hi - lo) * bead_height(A.ravel() % 1.0, B.ravel() % 1.0, saddle)
    nu, nv = len(ua), len(vb)
    m = MS.Mesh()
    iT = m.add_verts(np.c_[P[:, 0], side * (fl + h), P[:, 1]]).reshape(nu, nv)
    iK = m.add_verts(np.c_[P[:, 0], side * (fl - SLAB_BACK), P[:, 1]]).reshape(nu, nv)
    for i in range(nu - 1):
        for j in range(nv - 1):
            m.face((iT[i, j], iT[i + 1, j], iT[i + 1, j + 1], iT[i, j + 1]))
            m.face((iK[i, j + 1], iK[i + 1, j + 1], iK[i + 1, j], iK[i, j]))
    ring = ([(i, 0) for i in range(nu - 1)] + [(nu - 1, j) for j in range(nv - 1)]
            + [(i, nv - 1) for i in range(nu - 1, 0, -1)] + [(0, j) for j in range(nv - 1, 0, -1)])
    for k in range(len(ring)):
        p_, q_ = ring[k], ring[(k + 1) % len(ring)]
        m.face((iT[p_], iK[p_], iK[q_], iT[q_]))
    return m                                               # winding fixed by to_object's recalc (closed solid)


def field_outline_xz(extra=0.0):
    return G.offset(panel_outline_xz(), -(PANEL_SHRINK + extra))


def field_clip_planes():
    """The field quad (the panel corners inset PANEL_SHRINK, corners left sharp) as four (point, outward normal) pairs
    in XZ: the clip planes of the bake-source field (grip.build_checker_field)."""
    Q = G.ccw(ts_to_xz(PANEL_TS))
    Q = G.offset(Q, -PANEL_SHRINK)
    out = []
    for k in range(len(Q)):
        a, b = Q[k], Q[(k + 1) % len(Q)]
        d = (b - a) / np.hypot(*(b - a))
        out.append((a, np.array([d[1], -d[0]])))        # right of travel = outward for CCW
    return out
