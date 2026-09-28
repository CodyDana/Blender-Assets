"""Radial-star generator: C_n plate, full-length ground chamfer, hole ring - authored, never operated.

Hard-won rules carried over from the rev-2 four-point (see build_four_point.py history):

* The plate, including the ground chamfer, is authored explicitly.  ``bmesh.ops.bevel``
  silently clamped a requested 0.9 mm bevel to 0.323 mm and left 16 coincident
  vertices / 16 zero-length edges / 16 zero-area triangles at the bevel run-outs,
  which Unreal then stripped (1664 in Blender, 1632 in engine).
* Every vertex goes through a position-keyed factory snapped to 1 nm, so a duplicate
  vertex cannot exist by construction, and every face loop drops repeated indices, so
  a collapsed quad becomes a triangle rather than a sliver.  The build asserts all of
  this before an object is created.
* The hub ring bridges the hole ring k:1 (2:1 on the four-point LOD0) instead of a
  sunburst, and the hole polygon is circumscribed so its minimum opening is the stated
  diameter (rev 1's inscribed 16-gon was 7.846 mm across the flats for an "8 mm" hole).
* A large hub around a small hole (the eight-point: 22 mm hub, 9.5 mm hole) makes that
  k:1 fan a pinwheel of 17 mm slivers (median aspect 14, max 19.6).  ``LodSpec.hub_rings``
  switches such a form to graded rings - hole ring, intermediate rings, hub rim - joined
  by a zipper that is authored on the half wedge and mirrored, so every band is mirror-
  symmetric about the arm axis (no chirality) and places one triangle per extra segment.

Edge treatment, knife grind (style pass 2; spec.py has the numbers).  The cutting edges -
the arm's parallel edges and its taper edges - carry ``Outline.chamfer``, a knife grind
(``ChamferProfile.knife``: one flat facet at the grind angle down to a 0.15 mm land) on both
faces; the notch arcs carry the small ``Outline.scallop`` chamfer at the same angle over a
tall wall; the hole a 45 deg deburr chamfer (``Outline.hole_chamfer``).  At the arm root the
grind RUNS OUT into the scallop chamfer: the root ring is the scallop's mitre (below), the
next station (``Outline.x_run``, 3 mm out) already carries the full knife, and the bridge
between them is the run-out: its facet widens from the scallop chamfer to the full grind and
steepens a little on the way (measured 30.6 -> 34.8 deg on the four-point, so it is NOT a
constant-angle, planar quad), and the wall between them is a trapezoid from the scallop's tall
wall down to the land.  Each run-out facet is therefore authored as two explicit triangles with
mirrored diagonals top / bottom and +y / -y (``_bridge(split_facets=True)``), so Blender's loop
triangulation (bake, gallery) and the FBX exporter's triangulation are the same surface.
LOD2 (``LodSpec.knife_land`` /
``pyramid_tip`` / ``scallop`` False) keeps a one-facet grind whose facets meet in an edge
line (land 0: the wall quads collapse by key), square scallops, and a shoulder ring that
caps straight onto the point.  What the first style pass wrote about its full-length
chamfer still describes the construction:

* Along the arm's parallel edges and its taper edges the chamfer is a set of levels
  (plan inset ``s`` from the wall, depth ``drop`` below the plate) authored as extra
  rows of every arm cross-section (``_ring``): the wall top is level 0, the plate edge
  level K.  On the taper each inset leans with the edge (``Outline.chamfer_y``).
* The shoulder (parallel run -> taper) is a convex corner, so the inset polylines have
  their corner ``s tan(theta/2)`` BEFORE the shoulder: the shoulder ring is authored
  mitred, each level at its own x, which keeps every chamfer quad planar and exact.
* Past the apex the arm is narrower than two chamfers and the facets meet in a ridge on
  the axis; the levels are re-spaced over the available inset so no row collapses until
  the point, which ends in a vertical chisel edge the height of the land.
* The notch arcs carry the same levels as concentric rings (radius ``r_hub - s``); the
  hub PLATE therefore ends at ``r_hub - width`` on the notch and the arm plate is
  ``half_w - width`` wide.  The arm root is a concave corner: the arm's inset line and
  the notch's inset circle intersect (``Outline.x_root``), so the two chamfer bands meet
  in a mitre line from the outline corner inward, and that mitre row is authored ONCE
  (the notch ring's first point is the arm ring's chamfer point) so nothing can drift.
* Four float point attributes are written on every LOD for the material (no FBX carries
  them; only the LOD0 bake reads them): the distance from the outline, from the hole edge
  and from the concave notch arcs, computed analytically at each vertex (``EDGE_ATTR`` /
  ``HOLE_ATTR`` / ``SCALLOP_ATTR``), and ``GRIND_ATTR``, the signed plan distance from the
  line where the knife grind meets the flat plate (positive on the plate, negative on the
  grind), measured on the authored mesh itself (its plate / knife-facet boundary edges), so
  the edge nicks follow the real grind line through the root run-out.

C_n symmetry is exact.  One canonical wedge (arm 0 on +X, spanning -180/n..+180/n) is
authored per integer n-th turn.  Vertex keys are the snapped *wedge-local* position
plus the wedge index, so every wedge is keyed identically; a point on the upper seam of
wedge k is keyed as the mirrored lower-seam point of wedge k+1, which welds the seams by
key rather than by a float coincidence; points on the axis are shared by all wedges.
World positions come from ``spec.rotate``, which is trig-free for quarter turns, so a
C4 form's four arms land on bit-identical floats and any other n is symmetric to float
rounding (~1e-18 m).
"""
from __future__ import annotations

import math
from dataclasses import replace
from typing import Dict, List, Tuple

import bmesh
import bpy
import numpy as np
from mathutils import Matrix

from .spec import MM, SNAP, LodSpec, Outline, lod_triangles, rotate

# Face classes.  Smoothing is decided by class, not by dihedral angle: the chamfer needs
# smooth shading *inside* the facet (its round-over) and a hard edge where it meets the
# dead-flat plate and the rim wall, and the mitre lines where two chamfer bands meet must
# stay hard (Blender 5.2 has no use_auto_smooth, and the Smooth by Angle modifier cannot
# express this either).  The knife facets are FLAT: one class spans the root run-out, the
# parallel run and the taper of one edge, so inside a knife class an edge is also hard where
# its two faces' normals differ by more than KNIFE_CREASE_DEG (the shoulder mitre ~11 deg,
# the run-out / parallel-run crease ~9-10 deg, the folded run-out diagonal).  Smoothing across
# those creases bent the stored normals of the flat facets by up to 7.5 deg and made LOD1's
# single parallel facet reflect like the taper (geometry review, style pass 2).
# ``knife_shading_max_dev_deg`` (author_lod) is the gate: the largest angle between a corner
# normal and its own face normal over every knife facet, <= KNIFE_SHADING_GATE_DEG.
F_PLATE = 0
F_WALL_ARM = 1
F_WALL_NOTCH = 2
F_WALL_HOLE = 3
F_CH_TP = 4        # top chamfer, +y edge (parallel run and taper: one band)
F_CH_TN = 5        # top chamfer, -y edge
F_CH_BP = 6        # bottom chamfer, +y edge
F_CH_BN = 7        # bottom chamfer, -y edge
F_CH_NOTCH_T = 8   # top chamfer along the notch arc (the scallop chamfer)
F_CH_NOTCH_B = 9   # bottom chamfer along the notch arc
F_CH_HOLE_T = 10   # top deburr chamfer of the centre hole
F_CH_HOLE_B = 11   # bottom deburr chamfer of the centre hole
SMOOTH_CLASSES = {F_PLATE, F_WALL_NOTCH, F_WALL_HOLE, F_CH_TP, F_CH_TN, F_CH_BP, F_CH_BN, F_CH_NOTCH_T,
                  F_CH_NOTCH_B, F_CH_HOLE_T, F_CH_HOLE_B}
CHAMFER_CLASSES = {F_CH_TP, F_CH_TN, F_CH_BP, F_CH_BN, F_CH_NOTCH_T, F_CH_NOTCH_B, F_CH_HOLE_T, F_CH_HOLE_B}
KNIFE_CLASSES = {F_CH_TP, F_CH_TN, F_CH_BP, F_CH_BN}

KNIFE_CREASE_DEG = 0.5       # a knife-class edge is hard where its faces' normals differ by more than this
KNIFE_SHADING_GATE_DEG = 0.5  # max corner-normal vs face-normal angle on any knife facet
FACE_CLASS_ATTR = "shuriken_face_class"   # temporary INT face attribute (removed once measured)

EDGE_ATTR = "shuriken_edge"     # float, POINT: distance to the outline (the rim wall) in the plate plane, m
HOLE_ATTR = "shuriken_hole"     # float, POINT: distance to the hole edge, m (NO_HOLE_DISTANCE without a hole)
SCALLOP_ATTR = "shuriken_scallop"   # float, POINT: distance to the concave notch arcs, m (NO_HOLE_DISTANCE: none)
GRIND_ATTR = "shuriken_grind"   # float, POINT: signed distance from the knife grind's plate line, m (+ on the plate)
NO_HOLE_DISTANCE = 1.0

DEGENERATE_AREA = 1e-12     # m2
HULL_TOLERANCE = 1e-7       # m: a vertex this far outside a tip-prism hull still counts as enclosed
DEGENERATE_EDGE = 1e-6      # m
HYGIENE_KEYS = ("non_manifold_edges", "boundary_edges", "loose_verts", "ngons",
                "zero_length_edges", "zero_area_faces", "coincident_vertices")


class Builder:
    """Orbit-keyed vertex factory plus a face sink that cannot emit a degenerate.

    ``turn`` is the wedge being authored.  ``add`` takes wedge-local coordinates; the
    key is (wedge, snapped local position), so two calls that land on the same point of
    the same wedge return the same index and no ``remove_doubles`` pass is ever needed
    (the pass that used to run *before* the bevel is exactly how rev 1 shipped 16
    coincident pairs).  ``seam=True`` marks a point on a wedge boundary: the upper
    boundary (+180/n) is re-keyed as the lower boundary (-180/n) of the next wedge,
    which the generator authors as an exact mirror, so the seams weld by key.
    ``face`` drops repeated indices, so a quad whose far edge has collapsed becomes a
    triangle and a fully collapsed quad disappears.
    """

    def __init__(self, n: int) -> None:
        self.n = n
        self.verts: List[Tuple[float, float, float]] = []
        self.index: Dict[tuple, int] = {}
        self.faces: List[Tuple[int, ...]] = []
        self.classes: List[int] = []
        self.turn = 0

    def add(self, x: float, y: float, z: float, seam: bool = False) -> int:
        ix, iy, iz = round(x / SNAP), round(y / SNAP), round(z / SNAP)
        if ix == 0 and iy == 0:
            wedge, key = 0, ("axis", iz)
        elif seam and iy > 0:
            wedge = (self.turn + 1) % self.n
            iy = -iy
            key = (wedge, ix, iy, iz)
        else:
            wedge = self.turn
            key = (wedge, ix, iy, iz)
        found = self.index.get(key)
        if found is not None:
            return found
        found = len(self.verts)
        self.index[key] = found
        wx, wy = rotate(wedge, self.n, ix * SNAP, iy * SNAP)
        self.verts.append((wx, wy, iz * SNAP))
        return found

    def face(self, face_class: int, *indices: int) -> None:
        loop: List[int] = []
        for i in indices:
            if not loop or loop[-1] != i:
                loop.append(i)
        while len(loop) > 1 and loop[0] == loop[-1]:
            loop.pop()
        if len(loop) >= 3:
            self.faces.append(tuple(loop))
            self.classes.append(face_class)


def _fracs(columns: int) -> List[float]:
    """Plate columns as fractions of the half width, exactly antisymmetric (-1.0 and 1.0 exact)."""
    return [(2.0 * j - columns) / columns for j in range(columns + 1)]


def _ring(bld: Builder, o: Outline, x: float, profile, fracs, segments: int, mitre: bool = False):
    """One cross-section of the arm at ``x`` as an index bundle.

    ``top``/``bot`` are the plate columns; ``('ct', s)`` / ``('cb', s)`` are the grind
    levels on side ``s``, running from the wall top (k=0) to the plate edge (k=segments).
    ``profile`` is the station's ``ChamferProfile`` (the LOD's knife, ``Outline.knife_of``) or
    None for an unground section, whose level lists repeat the corner index (Builder.face then
    collapses the chamfer quads).  ``mitre`` authors the shoulder: level k sits
    ``s_k tan(theta/2)`` before ``x``, where the inset line of the parallel run meets the inset
    line of the taper.  Past the apex (the arm narrower than two grinds) the section is a roof:
    the levels are re-spaced over the inset where the facets meet and the last level is the
    ridge on the axis.  A land-0 profile puts the wall top on the mid-plane, so the top and
    bottom level-0 points are one vertex (by key) and the wall quads collapse.
    """
    half_t = o.half_t
    ring = {}
    if profile is None:
        half = o.half_width(x)
        top = [bld.add(x, f * half, half_t) for f in fracs]
        bot = [bld.add(x, f * half, -half_t) for f in fracs]
        ring["top"], ring["bot"] = top, bot
        for side in (1, -1):
            corner_t = top[-1] if side > 0 else top[0]
            corner_b = bot[-1] if side > 0 else bot[0]
            ring[("ct", side)] = [corner_t] * (segments + 1)
            ring[("cb", side)] = [corner_b] * (segments + 1)
        return ring

    levels = profile.levels(segments)            # (inset, drop) from the wall top to the plate edge
    width = profile.width
    if mitre:
        tan_half = math.tan(0.5 * o.half_tip_rad)
        plate_half = o.half_w - width
        x_plate = x - width * tan_half
        ring["top"] = [bld.add(x_plate, f * plate_half, half_t) for f in fracs]
        ring["bot"] = [bld.add(x_plate, f * plate_half, -half_t) for f in fracs]
        for side in (1, -1):
            ct, cb = [], []
            for s, drop in levels:
                xk, yk, zk = x - s * tan_half, side * (o.half_w - s), half_t - drop
                ct.append(bld.add(xk, yk, zk))
                cb.append(bld.add(xk, yk, -zk))
            ring[("ct", side)] = ct
            ring[("cb", side)] = cb
        return ring

    half = o.half_width(x)
    lean = 1.0 / math.cos(o.half_tip_rad) if x > o.x_taper else 1.0   # y per unit of perpendicular inset
    inset_y = width * lean
    # At the apex station half == inset_y up to float rounding; which branch a 1e-19 m error
    # picks must not matter, so anything within half a snap step counts as the plate
    # branch with a zero-width plate (the columns then weld to one point by key).
    scale = 1.0
    if half >= inset_y - 0.5 * SNAP:
        plate_half = max(0.0, half - inset_y)
        ring["top"] = [bld.add(x, f * plate_half, half_t) for f in fracs]
        ring["bot"] = [bld.add(x, f * plate_half, -half_t) for f in fracs]
    else:
        # The facets have met: the plate has run out and the section is a roof.
        s_max = half / lean
        scale = s_max / width
        z_ridge = half_t - profile.drop_at(s_max)
        ridge_t = bld.add(x, 0.0, z_ridge)
        ridge_b = bld.add(x, 0.0, -z_ridge)
        ring["top"] = [ridge_t] * len(fracs)
        ring["bot"] = [ridge_b] * len(fracs)
    last = len(levels) - 1
    for side in (1, -1):
        ct, cb = [], []
        for k, (s, drop) in enumerate(levels):
            if scale != 1.0:
                s = s * scale
                drop = profile.drop_at(s)
            y = 0.0 if (scale != 1.0 and k == last) else half - s * lean
            z = half_t - drop
            ct.append(bld.add(x, side * y, z))
            cb.append(bld.add(x, side * y, -z))
        ring[("ct", side)] = ct
        ring[("cb", side)] = cb
    return ring


def _point_ring(bld: Builder, o: Outline, profile, fracs, segments: int):
    """The point itself as a ring bundle (every index the tip vertex): a pyramid tip's cap."""
    z = o.half_t - profile.wall_top_drop
    tip_t = bld.add(o.r_tip, 0.0, z)
    tip_b = bld.add(o.r_tip, 0.0, -z)
    ring = {"top": [tip_t] * len(fracs), "bot": [tip_b] * len(fracs)}
    for side in (1, -1):
        ring[("ct", side)] = [tip_t] * (segments + 1)
        ring[("cb", side)] = [tip_b] * (segments + 1)
    return ring


def _bridge(bld: Builder, a, b, segments: int, split_facets: bool = False) -> None:
    """Faces between two consecutive arm cross-sections.

    ``split_facets`` authors every facet quad as two explicit triangles (the root run-out,
    whose quads are folded ~9-10 deg): the diagonal runs from ring ``a``'s level k to ring
    ``b``'s level k + 1 on the top face and is its z-mirror on the bottom face, the same on
    both sides of the arm, so the run-out is mirror-symmetric and every consumer (Blender's
    loop triangulation, the bake, the FBX exporter) sees the same two planar triangles.
    """
    top_a, top_b = a["top"], b["top"]
    bot_a, bot_b = a["bot"], b["bot"]
    for j in range(len(top_a) - 1):
        bld.face(F_PLATE, top_a[j], top_b[j], top_b[j + 1], top_a[j + 1])
        bld.face(F_PLATE, bot_a[j + 1], bot_b[j + 1], bot_b[j], bot_a[j])
    for side in (1, -1):
        ct_a, ct_b = a[("ct", side)], b[("ct", side)]
        cb_a, cb_b = a[("cb", side)], b[("cb", side)]
        top_class = F_CH_TP if side > 0 else F_CH_TN
        bot_class = F_CH_BP if side > 0 else F_CH_BN
        for k in range(segments):
            if split_facets:
                bld.face(top_class, ct_a[k], ct_b[k], ct_b[k + 1])
                bld.face(top_class, ct_a[k], ct_b[k + 1], ct_a[k + 1])
                bld.face(bot_class, cb_a[k + 1], cb_b[k + 1], cb_a[k])
                bld.face(bot_class, cb_b[k + 1], cb_b[k], cb_a[k])
            else:
                bld.face(top_class, ct_a[k], ct_b[k], ct_b[k + 1], ct_a[k + 1])
                bld.face(bot_class, cb_a[k + 1], cb_b[k + 1], cb_b[k], cb_a[k])
        bld.face(F_WALL_ARM, ct_a[0], ct_b[0], cb_b[0], cb_a[0])


def _bridge_root_runout(bld: Builder, o: Outline, a, b, segments: int, profile) -> None:
    """The root bridge of a LOD with square scallops and no run-out station (LOD2).

    The root ring ``a`` is the square notch corner (every grind level collapsed onto it) and
    ``b`` the first knife station (the shoulder), so a plain ``_bridge`` would make ONE wall
    triangle from the full-thickness corner to the wall top at the shoulder: a vertical face
    the length of the parallel run where LOD0 has only its 3 mm run-out wall and the thin land.
    Its transferred UVs then cover empty UV space beyond LOD0's run-out island and overlap the
    next island.  A vertex R on the wall-top line at ``Outline.x_run`` (the end of LOD0's
    run-out) splits it: the wall is the triangle corner / R / corner (land 0) - LOD0's run-out
    wall in miniature - and the first facet triangle becomes the run-out facet (corner, R,
    plate edge) plus the knife facet (R, wall top, plate edge), which lies in the knife plane.
    """
    top_a, top_b = a["top"], b["top"]
    bot_a, bot_b = a["bot"], b["bot"]
    for j in range(len(top_a) - 1):
        bld.face(F_PLATE, top_a[j], top_b[j], top_b[j + 1], top_a[j + 1])
        bld.face(F_PLATE, bot_a[j + 1], bot_b[j + 1], bot_b[j], bot_a[j])
    z_wall = o.half_t - profile.wall_top_drop
    for side in (1, -1):
        ct_a, ct_b = a[("ct", side)], b[("ct", side)]
        cb_a, cb_b = a[("cb", side)], b[("cb", side)]
        r_t = bld.add(o.x_run, side * o.half_w, z_wall)
        r_b = bld.add(o.x_run, side * o.half_w, -z_wall)
        top_class = F_CH_TP if side > 0 else F_CH_TN
        bot_class = F_CH_BP if side > 0 else F_CH_BN
        # k = 0, split through R: polygon (a0, R, b0, b1) as two explicit triangles
        bld.face(top_class, ct_a[0], r_t, ct_b[1])
        bld.face(top_class, r_t, ct_b[0], ct_b[1])
        bld.face(bot_class, cb_a[0], cb_b[1], r_b)
        bld.face(bot_class, cb_b[1], cb_b[0], r_b)
        for k in range(1, segments):
            bld.face(top_class, ct_a[k], ct_b[k], ct_b[k + 1], ct_a[k + 1])
            bld.face(bot_class, cb_a[k + 1], cb_b[k + 1], cb_b[k], cb_a[k])
        bld.face(F_WALL_ARM, ct_a[0], r_t, r_b, cb_a[0])
        bld.face(F_WALL_ARM, r_t, ct_b[0], cb_b[0], r_b)


def hub_angles(o: Outline, lod: LodSpec) -> List[float]:
    """Hub PLATE rim angles of one wedge: half notch, arm root arc, half notch.

    The rim is the ring the hub plate ends on: radius ``r_hub - chamfer`` with the arm
    plate ``half_w - chamfer`` wide (``Outline.rim_radius`` / ``rim_half_w``; the plain
    hub circle and arm width on a LOD without a chamfer).  Built as an exact mirror (the
    lower half is the negated upper half), so the wedge boundary points at -180/n and
    +180/n are bit-exact mirror images - which is what lets Builder weld the seams by key.
    """
    fracs = _fracs(lod.columns)
    r, hw = o.rim_radius(lod), o.rim_half_w(lod)
    arm = [math.asin(f * hw / r) for f in fracs]
    a_root = math.asin(hw / r)
    upper = [a_root + (o.half_sector - a_root) * k / lod.notch_segments
             for k in range(1, lod.notch_segments + 1)]
    upper[-1] = o.half_sector
    lower = [-a for a in reversed(upper)]
    return lower + arm + upper


def hole_angles(o: Outline, lod: LodSpec) -> List[float]:
    m = lod.hole_segments
    return [o.half_sector * (2 * k - m) / m for k in range(m + 1)]


def ring_angles(o: Outline, lod: LodSpec, kind: str) -> List[float]:
    """Angles of an intermediate hub ring over one wedge, exactly mirror-symmetric."""
    if kind == "seam":
        return [-o.half_sector, o.half_sector]
    if kind == "hole":
        return hole_angles(o, lod)
    if kind == "rim":
        return hub_angles(o, lod)
    if kind == "arm":
        rim = hub_angles(o, lod)
        n_notch = lod.notch_segments
        arm = rim[n_notch:n_notch + lod.columns + 1]
        return [rim[0]] + arm + [rim[-1]]
    raise ValueError(f"unknown hub ring kind {kind!r}")


def _zip_half(inner: List[int], outer: List[int], inner_ang: List[float], outer_ang: List[float],
              i: int, j: int) -> List[Tuple[Tuple[str, int], ...]]:
    """Faces between two ring polylines from positions (i, j) up to both ends.

    Advances whichever ring's next point comes first in angle; equal angles close a
    quad.  Faces are (ring, index) tuples in counter-clockwise order seen from +Z:
    inner(a) -> outer(b) -> ... -> inner(a'), the same winding as the k:1 bridge.
    """
    faces = []
    last_i, last_j = len(inner_ang) - 1, len(outer_ang) - 1
    while i < last_i or j < last_j:
        if i == last_i:
            faces.append((("i", i), ("o", j), ("o", j + 1)))
            j += 1
        elif j == last_j:
            faces.append((("i", i), ("o", j), ("i", i + 1)))
            i += 1
        else:
            na, nb = inner_ang[i + 1], outer_ang[j + 1]
            if abs(na - nb) <= 1e-12:
                faces.append((("i", i), ("o", j), ("o", j + 1), ("i", i + 1)))
                i += 1
                j += 1
            elif na < nb:
                faces.append((("i", i), ("o", j), ("i", i + 1)))
                i += 1
            else:
                faces.append((("i", i), ("o", j), ("o", j + 1)))
                j += 1
    return faces


def band_faces(inner_ang: List[float], outer_ang: List[float]) -> List[Tuple[Tuple[str, int], ...]]:
    """Mirror-symmetric faces of the band between two symmetric angle lists of one wedge.

    The upper half (angles >= 0) is zipped and mirrored onto the lower half, so the band
    is symmetric about the arm axis by construction.  Whatever straddles the axis is one
    symmetric face: a quad when neither ring has a point on it, a triangle when one does.
    Both lists must start at -180/n and end at +180/n (the wedge seams).
    """
    ni, no = len(inner_ang), len(outer_ang)
    zi = next((k for k, a in enumerate(inner_ang) if a == 0.0), None)
    zo = next((k for k, a in enumerate(outer_ang) if a == 0.0), None)
    faces = []
    if zi is not None and zo is not None:
        start = (zi, zo)
    elif zi is None and zo is not None:
        lo, hi = ni // 2 - 1, ni // 2
        faces.append((("i", lo), ("o", zo), ("i", hi)))
        start = (hi, zo)
    elif zi is not None:
        lo, hi = no // 2 - 1, no // 2
        faces.append((("i", zi), ("o", lo), ("o", hi)))
        start = (zi, hi)
    else:
        ilo, ihi, olo, ohi = ni // 2 - 1, ni // 2, no // 2 - 1, no // 2
        faces.append((("i", ilo), ("o", olo), ("o", ohi), ("i", ihi)))
        start = (ihi, ohi)
    upper = _zip_half(list(range(ni)), list(range(no)), inner_ang, outer_ang, *start)
    faces += upper
    size = {"i": ni, "o": no}
    for face in upper:
        faces.append(tuple((ring, size[ring] - 1 - k) for ring, k in reversed(face)))
    return faces


def _ring_vertices(bld: Builder, radius: float, angles: List[float], z: float) -> List[int]:
    last = len(angles) - 1
    return [bld.add(radius * math.cos(a), radius * math.sin(a), z, seam=i in (0, last))
            for i, a in enumerate(angles)]


def _ring_hub(bld: Builder, o: Outline, lod: LodSpec, hub_t, hub_b, hole_t, hole_b) -> None:
    """Hub annulus (or disc) as graded rings: hole ring / axis -> hub_rings -> hub plate rim."""
    half_t = o.half_t
    rings = []
    if lod.has_hole:
        rings.append((hole_angles(o, lod), hole_t, hole_b))
    for kind, t in lod.hub_rings:
        angles = ring_angles(o, lod, kind)
        radius = o.hub_ring_radius(lod, t)
        rings.append((angles, _ring_vertices(bld, radius, angles, half_t),
                      _ring_vertices(bld, radius, angles, -half_t)))
    rings.append((hub_angles(o, lod), hub_t, hub_b))
    if not lod.has_hole:
        # Disc: the innermost ring is fanned from the axis point shared by all wedges.
        angles, ring_t, ring_b = rings[0]
        centre_t = bld.add(0.0, 0.0, half_t)
        centre_b = bld.add(0.0, 0.0, -half_t)
        for i in range(len(angles) - 1):
            bld.face(F_PLATE, centre_t, ring_t[i], ring_t[i + 1])
            bld.face(F_PLATE, centre_b, ring_b[i + 1], ring_b[i])
    for (ang_in, in_t, in_b), (ang_out, out_t, out_b) in zip(rings, rings[1:]):
        top = {"i": in_t, "o": out_t}
        bot = {"i": in_b, "o": out_b}
        for face in band_faces(ang_in, ang_out):
            bld.face(F_PLATE, *[top[ring][k] for ring, k in face])
            bld.face(F_PLATE, *[bot[ring][k] for ring, k in reversed(face)])


def _notch_levels(bld: Builder, o: Outline, lod: LodSpec, levels):
    """The notch arc's (scallop) chamfer levels as concentric rings, one per (inset, drop).

    ``levels`` is ``Outline.scallop_levels(lod)``: the scallop chamfer, or K + 1 copies of the
    corner (0, 0) on a LOD with square scallops, whose rings then all weld by key.

    Returns ``(top, bottom)``: per level a ``{side: [indices]}`` running from the mitre
    point (where the notch's inset arc meets the arm's inset edge, ``Outline.x_root``) to
    the wedge seam.  The mitre point is authored here in cartesian form and REUSED by the
    arm's root ring, so the two chamfer bands share their mitre row by index.
    """
    half_t = o.half_t
    n_notch = lod.notch_segments
    top, bottom = [], []
    for s, drop in levels:
        r_k, y_k, z_k = o.r_hub - s, o.half_w - s, half_t - drop
        x_m = o.x_root(s)
        a_root = math.asin(y_k / r_k)
        ring_t, ring_b = {}, {}
        for side in (1, -1):
            pts_t = [bld.add(x_m, side * y_k, z_k)]
            pts_b = [bld.add(x_m, side * y_k, -z_k)]
            for j in range(1, n_notch + 1):
                seam = j == n_notch
                a = o.half_sector if seam else a_root + (o.half_sector - a_root) * j / n_notch
                x, y = r_k * math.cos(a), r_k * math.sin(a)
                pts_t.append(bld.add(x, side * y, z_k, seam=seam))
                pts_b.append(bld.add(x, side * y, -z_k, seam=seam))
            ring_t[side], ring_b[side] = pts_t, pts_b
        top.append(ring_t)
        bottom.append(ring_b)
    return top, bottom


def wedge(bld: Builder, o: Outline, lod: LodSpec, taper_intervals: int) -> None:
    """One 360/n wedge: arm 0 on +X, its hub wedge and the matching hole segments."""
    half_t = o.half_t
    segments = lod.bevel_segments
    fracs = _fracs(lod.columns)
    n_notch, n_col = lod.notch_segments, lod.columns
    levels = o.scallop_levels(lod)
    n_levels = len(levels)
    knife = o.knife_of(lod) if lod.has_bevel else None

    # --- notch chamfer levels (level 0 = the wall top on the hub circle, level K = the plate edge).
    notch_t, notch_b = _notch_levels(bld, o, lod, levels)
    rim_t, rim_b = notch_t[-1], notch_b[-1]

    # --- hub plate rim: the plate-edge notch rings plus the arm root arc between the mitre points.
    r_rim, hw = o.rim_radius(lod), o.rim_half_w(lod)
    arm_t, arm_b = [], []
    for f in fracs:
        if f == -1.0:
            arm_t.append(rim_t[-1][0])
            arm_b.append(rim_b[-1][0])
        elif f == 1.0:
            arm_t.append(rim_t[1][0])
            arm_b.append(rim_b[1][0])
        else:
            a = math.asin(f * hw / r_rim)
            x, y = r_rim * math.cos(a), r_rim * math.sin(a)
            arm_t.append(bld.add(x, y, half_t))
            arm_b.append(bld.add(x, y, -half_t))
    hub_t = rim_t[-1][::-1][:-1] + arm_t + rim_t[1][1:]
    hub_b = rim_b[-1][::-1][:-1] + arm_b + rim_b[1][1:]

    hole_t = hole_b = wall_t = wall_b = None
    if lod.has_hole:
        r_poly = o.hole_polygon_radius(lod.hole_segments * o.n)
        hole_ang = hole_angles(o, lod)
        hlast = len(hole_ang) - 1

        def hole_ring(radius: float, z: float):
            return [bld.add(radius * math.cos(a), radius * math.sin(a), z, seam=i in (0, hlast))
                    for i, a in enumerate(hole_ang)]

        if lod.has_hole_bevel:
            # the deburr chamfer: wall top ring on the hole polygon, plate ring offset by its width
            z_wall = half_t - o.hole_chamfer.wall_top_drop
            wall_t, wall_b = hole_ring(r_poly, z_wall), hole_ring(r_poly, -z_wall)
            r_plate = o.hole_plate_radius(lod)
            hole_t, hole_b = hole_ring(r_plate, half_t), hole_ring(r_plate, -half_t)
        else:
            hole_t, hole_b = hole_ring(r_poly, half_t), hole_ring(r_poly, -half_t)
            wall_t, wall_b = hole_t, hole_b
    if lod.hub_rings:
        _ring_hub(bld, o, lod, hub_t, hub_b, hole_t, hole_b)
    elif lod.has_hole:
        ratio = lod.hub_segments // lod.hole_segments
        # --- hub annulus: the hole ring bridged k:1 to the hub plate rim.
        for k in range(lod.hole_segments):
            off = k * ratio
            for i in range(ratio - 1):
                bld.face(F_PLATE, hole_t[k], hub_t[off + i], hub_t[off + i + 1])
                bld.face(F_PLATE, hole_b[k], hub_b[off + i + 1], hub_b[off + i])
            bld.face(F_PLATE, hole_t[k], hub_t[off + ratio - 1], hub_t[off + ratio], hole_t[k + 1])
            bld.face(F_PLATE, hole_b[k + 1], hub_b[off + ratio], hub_b[off + ratio - 1], hole_b[k])
    else:
        # --- no hole (LOD2): the hub is a disc fanned from the axis point, shared by all wedges.
        centre_t = bld.add(0.0, 0.0, half_t)
        centre_b = bld.add(0.0, 0.0, -half_t)
        for i in range(len(hub_t) - 1):
            bld.face(F_PLATE, centre_t, hub_t[i], hub_t[i + 1])
            bld.face(F_PLATE, centre_b, hub_b[i + 1], hub_b[i])

    # --- notch: rim wall between the level-0 rings, chamfer bands between consecutive levels.
    for side in (1, -1):
        wt, wb = notch_t[0][side], notch_b[0][side]
        for j in range(n_notch):
            if side > 0:
                bld.face(F_WALL_NOTCH, wt[j], wt[j + 1], wb[j + 1], wb[j])
            else:
                bld.face(F_WALL_NOTCH, wt[j + 1], wt[j], wb[j], wb[j + 1])
        for k in range(n_levels - 1):
            outer_t, inner_t = notch_t[k][side], notch_t[k + 1][side]
            outer_b, inner_b = notch_b[k][side], notch_b[k + 1][side]
            for j in range(n_notch):
                if side > 0:
                    bld.face(F_CH_NOTCH_T, outer_t[j], outer_t[j + 1], inner_t[j + 1], inner_t[j])
                    bld.face(F_CH_NOTCH_B, inner_b[j], inner_b[j + 1], outer_b[j + 1], outer_b[j])
                else:
                    bld.face(F_CH_NOTCH_T, outer_t[j + 1], outer_t[j], inner_t[j], inner_t[j + 1])
                    bld.face(F_CH_NOTCH_B, inner_b[j + 1], inner_b[j], outer_b[j], outer_b[j + 1])

    # --- hole wall, and the hole's deburr chamfer (wall top ring -> plate ring, top and bottom).
    if lod.has_hole:
        for i in range(lod.hole_segments):
            bld.face(F_WALL_HOLE, wall_t[i], wall_t[i + 1], wall_b[i + 1], wall_b[i])
        if lod.has_hole_bevel:
            for i in range(lod.hole_segments):
                bld.face(F_CH_HOLE_T, wall_t[i], hole_t[i], hole_t[i + 1], wall_t[i + 1])
                bld.face(F_CH_HOLE_B, wall_b[i + 1], hole_b[i + 1], hole_b[i], wall_b[i])

    # --- arm: row 0 IS the hub plate's arm arc, and its grind levels are the scallop's mitre
    # points (the corner itself, K + 1 times, without a scallop).  The bridge from there to the
    # first station is the knife grind's run-out.
    root = {"top": arm_t, "bot": arm_b}
    for side in (1, -1):
        root[("ct", side)] = [notch_t[k][side][0] for k in range(n_levels)]
        root[("cb", side)] = [notch_b[k][side][0] for k in range(n_levels)]

    s = lod.straight_intervals
    if lod.has_runout_station:
        straight_x = [o.x_run] + [o.x_run + (o.x_taper - o.x_run) * k / s for k in range(1, s + 1)]
    else:
        straight_x = [o.r_hub + (o.x_taper - o.r_hub) * k / s for k in range(1, s + 1)]
    if lod.has_bevel and lod.pyramid_tip:
        taper_x = []
    elif lod.has_bevel:
        taper_x = [o.x_taper + (o.x_apex - o.x_taper) * k / taper_intervals
                   for k in range(1, taper_intervals + 1)]
        taper_x += [o.x_apex + (o.r_tip - o.x_apex) * k / lod.tip_intervals
                    for k in range(1, lod.tip_intervals + 1)]
    else:
        taper_x = [o.x_taper + (o.r_tip - o.x_taper) * k / taper_intervals
                   for k in range(1, taper_intervals + 1)]

    last = len(straight_x) - 1
    rings = [root]
    rings += [_ring(bld, o, x, knife, fracs, segments, mitre=(lod.has_bevel and k == last))
              for k, x in enumerate(straight_x)]
    rings += [_ring(bld, o, x, knife, fracs, segments) for x in taper_x]
    if lod.has_bevel and lod.pyramid_tip:
        rings.append(_point_ring(bld, o, knife, fracs, segments))
    first = 0
    if lod.has_bevel and not lod.has_scallop and not lod.has_runout_station:
        _bridge_root_runout(bld, o, rings[0], rings[1], segments, knife)
        first = 1
    elif lod.has_scallop and lod.has_runout_station:
        # the run-out from the scallop mitre to x_run: folded quads, authored as explicit triangles
        _bridge(bld, rings[0], rings[1], segments, split_facets=True)
        first = 1
    for i in range(first, len(rings) - 1):
        _bridge(bld, rings[i], rings[i + 1], segments)


def coincident_pairs(coords: np.ndarray, tolerance: float = 1e-7) -> int:
    """Number of vertex pairs closer together than ``tolerance`` (lexicographic sweep)."""
    if len(coords) < 2:
        return 0
    order = np.lexsort((coords[:, 2], coords[:, 1], coords[:, 0]))
    sorted_co = coords[order]
    pairs = 0
    for i in range(len(sorted_co)):
        j = i + 1
        while j < len(sorted_co) and sorted_co[j, 0] - sorted_co[i, 0] <= tolerance:
            if np.linalg.norm(sorted_co[j] - sorted_co[i]) <= tolerance:
                pairs += 1
            j += 1
    return pairs


def outline_distance(o: Outline, xy: np.ndarray) -> np.ndarray:
    """Distance (m) from each XY point to the star's outline (the rim wall), in the plate plane.

    Exact for points inside the plate: the outline of one folded wedge (arm 0 on +X, the
    upper half) is the arm edge segment from the root corner to the shoulder, the taper
    edge segment from the shoulder to the point, and the notch arc from the root corner
    to the seam; the nearest of the three, with segment ends and the arc's end clamped.
    """
    x, y = xy[:, 0], xy[:, 1]
    r = np.hypot(x, y)
    sector = 2.0 * math.pi / o.n
    ang = np.arctan2(y, x)
    a = ang - np.round(ang / sector) * sector
    xp, yp = r * np.cos(a), r * np.abs(np.sin(a))
    x_root, x_taper, hw = o.x_root(0.0), o.x_taper, o.half_w
    # arm edge segment (x_root, hw) -> (x_taper, hw)
    d_arm = np.hypot(np.maximum(np.maximum(x_root - xp, xp - x_taper), 0.0), np.abs(yp - hw))
    # taper edge segment (x_taper, hw) -> (r_tip, 0)
    ex, ey = o.r_tip - x_taper, -hw
    length2 = ex * ex + ey * ey
    t = np.clip(((xp - x_taper) * ex + (yp - hw) * ey) / length2, 0.0, 1.0)
    d_taper = np.hypot(xp - (x_taper + t * ex), yp - (hw + t * ey))
    # notch arc: radius r_hub over |angle| in [arm_half_angle, half_sector]; else its end (the root corner)
    in_arc = np.abs(a) >= o.arm_half_angle
    d_notch = np.where(in_arc, np.abs(r - o.r_hub), np.hypot(xp - x_root, yp - hw))
    return np.minimum(np.minimum(d_arm, d_taper), d_notch)


def scallop_distance(o: Outline, xy: np.ndarray) -> np.ndarray:
    """Distance (m) from each XY point to the concave notch arcs (the scallops) in the plate plane.

    Folded into one half wedge: inside the notch's angular range the distance is |r - r_hub|;
    inside an arm's range the nearest notch point is the arc's end, the root corner.
    """
    x, y = xy[:, 0], xy[:, 1]
    r = np.hypot(x, y)
    sector = 2.0 * math.pi / o.n
    ang = np.arctan2(y, x)
    a = ang - np.round(ang / sector) * sector
    xp, yp = r * np.cos(a), r * np.abs(np.sin(a))
    corner = np.hypot(xp - o.x_root(0.0), yp - o.half_w)
    return np.where(np.abs(a) >= o.arm_half_angle, np.abs(r - o.r_hub), corner)


def segment_distance(points: np.ndarray, seg_a: np.ndarray, seg_b: np.ndarray, chunk: int = 512) -> np.ndarray:
    """Smallest 2D distance from each point to a set of segments (a -> b)."""
    if not len(seg_a):
        return np.full(len(points), NO_HOLE_DISTANCE)
    d = seg_b - seg_a
    length2 = np.maximum(np.einsum("sj,sj->s", d, d), 1e-30)
    out = np.empty(len(points))
    for start in range(0, len(points), chunk):
        p = points[start:start + chunk][:, None, :]
        t = np.clip(np.einsum("psj,sj->ps", p - seg_a[None], d) / length2, 0.0, 1.0)
        closest = seg_a[None] + t[..., None] * d[None]
        out[start:start + chunk] = np.linalg.norm(p - closest, axis=-1).min(axis=1)
    return out


def write_grind_layer(bm, is_plate, is_knife) -> int:
    """Write GRIND_ATTR as a bmesh float layer: signed plan distance from the grind's plate line.

    The plate line is every edge between a plate face (``is_plate(face)``) and a knife facet
    (``is_knife(face)``), taken on the top face (the bottom mirrors it in plan).  Vertices of
    a plate face get +distance, all others -distance, so the value is 0 on the line, grows into
    the flat face and falls across the grind.  Returns the number of line segments.
    """
    seg_a, seg_b = [], []
    for edge in bm.edges:
        faces = edge.link_faces
        if len(faces) != 2:
            continue
        pair = (is_plate(faces[0]) and is_knife(faces[1])) or (is_plate(faces[1]) and is_knife(faces[0]))
        if pair and edge.verts[0].co.z > 0.0 and edge.verts[1].co.z > 0.0:
            seg_a.append(edge.verts[0].co.xy[:])
            seg_b.append(edge.verts[1].co.xy[:])
    points = np.array([v.co.xy[:] for v in bm.verts], dtype=np.float64)
    dist = segment_distance(points, np.array(seg_a, dtype=np.float64).reshape(-1, 2),
                            np.array(seg_b, dtype=np.float64).reshape(-1, 2))
    layer = bm.verts.layers.float.get(GRIND_ATTR) or bm.verts.layers.float.new(GRIND_ATTR)
    for v, value in zip(bm.verts, dist):
        on_plate = any(is_plate(f) for f in v.link_faces)
        v[layer] = float(value if on_plate else -value)
    return len(seg_a)


def hole_distance(o: Outline, lod: LodSpec, xy: np.ndarray) -> np.ndarray:
    """Distance (m) from each XY point to the hole's minimum opening; NO_HOLE_DISTANCE without a hole."""
    if not lod.has_hole:
        return np.full(len(xy), NO_HOLE_DISTANCE)
    return np.maximum(np.hypot(xy[:, 0], xy[:, 1]) - o.r_hole, 0.0)


def write_distance_attributes(mesh, edge: np.ndarray, hole: np.ndarray, scallop: np.ndarray = None) -> None:
    """Write the analytic material attributes (float, POINT domain) onto ``mesh``."""
    if scallop is None:
        scallop = np.full(len(edge), NO_HOLE_DISTANCE)
    for name, values in ((EDGE_ATTR, edge), (HOLE_ATTR, hole), (SCALLOP_ATTR, scallop)):
        attr = mesh.attributes.get(name)
        if attr is None:
            attr = mesh.attributes.new(name, "FLOAT", "POINT")
        attr.data.foreach_set("value", np.asarray(values, dtype=np.float32).ravel())
    mesh.update()


def build_star_bmesh(o: Outline, lod: LodSpec, taper_intervals: int):
    """Author all n wedges through one shared vertex factory and bake smoothing."""
    bld = Builder(o.n)
    for turn in range(o.n):
        bld.turn = turn
        wedge(bld, o, lod, taper_intervals)

    bm = bmesh.new()
    # created before any face: adding a layer later reallocates the faces and invalidates face_class's keys
    class_layer = bm.faces.layers.int.new(FACE_CLASS_ATTR)
    made = [bm.verts.new(co) for co in bld.verts]
    bm.verts.ensure_lookup_table()
    face_class = {}
    for loop, cls in zip(bld.faces, bld.classes):
        face = bm.faces.new([made[i] for i in loop])
        face_class[face] = cls
        face[class_layer] = cls
    bm.faces.ensure_lookup_table()
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.normal_update()

    for face in bm.faces:
        face.smooth = True
    crease = math.radians(KNIFE_CREASE_DEG)
    knife_creases = 0
    for edge in bm.edges:
        linked = edge.link_faces
        smooth = (len(linked) == 2
                  and face_class[linked[0]] == face_class[linked[1]]
                  and face_class[linked[0]] in SMOOTH_CLASSES)
        if smooth and face_class[linked[0]] in KNIFE_CLASSES and linked[0].normal.angle(linked[1].normal, 0.0) > crease:
            smooth = False                   # a real crease between two flat knife facets stays hard
            knife_creases += 1
        edge.smooth = smooth
    grind_segments = write_grind_layer(bm, lambda f: face_class[f] == F_PLATE,
                                       lambda f: face_class[f] in KNIFE_CLASSES)

    stats = {
        "authored_vertices": len(bld.verts),
        "authored_faces": len(bld.faces),
        "quads": sum(1 for f in bm.faces if len(f.verts) == 4),
        "tris": sum(1 for f in bm.faces if len(f.verts) == 3),
        "ngons": sum(1 for f in bm.faces if len(f.verts) > 4),
        "non_manifold_edges": sum(1 for e in bm.edges if len(e.link_faces) > 2 or not e.link_faces),
        "boundary_edges": sum(1 for e in bm.edges if len(e.link_faces) == 1),
        "loose_verts": sum(1 for v in bm.verts if not v.link_edges),
        "zero_length_edges": sum(1 for e in bm.edges if e.calc_length() <= DEGENERATE_EDGE),
        "zero_area_faces": sum(1 for f in bm.faces if f.calc_area() <= DEGENERATE_AREA),
        "sharp_edges": sum(1 for e in bm.edges if not e.smooth),
        "knife_crease_edges": knife_creases,
        "chamfer_faces": sum(1 for f in bm.faces if face_class[f] in CHAMFER_CLASSES),
        "knife_faces": sum(1 for f in bm.faces if face_class[f] in KNIFE_CLASSES),
        "grind_line_segments": grind_segments,
        "signed_volume_m3": bm.calc_volume(signed=True),
        "min_edge_mm": min(e.calc_length() for e in bm.edges) / MM,
        "min_face_area_mm2": min(f.calc_area() for f in bm.faces) / (MM ** 2),
    }
    coords = np.array([v.co[:] for v in bm.verts], dtype=np.float64)
    stats["coincident_vertices"] = coincident_pairs(coords)
    stats["triangles"] = stats["tris"] + 2 * stats["quads"]
    return bm, stats


def hygiene_problems(stats: dict) -> List[str]:
    problems = [f"{key}={stats[key]}" for key in HYGIENE_KEYS if stats[key]]
    if stats["signed_volume_m3"] <= 0.0:
        problems.append(f"normals point inward (signed volume {stats['signed_volume_m3']})")
    return problems


def knife_shading(mesh, knife_classes, drop_attribute: bool = True) -> dict:
    """Shading figures of the knife facets, read from the mesh's own corner normals.

    Uses the temporary ``FACE_CLASS_ATTR`` the generator wrote (and removes it unless
    ``drop_attribute`` is False): ``knife_shading_max_dev_deg`` is the largest angle between a
    corner normal and its own face normal over every knife-class face (0 for flat facets
    shaded flat; the smoothed-across-creases pass-2 build was 7.5 deg), and
    ``knife_face_max_warp_mm`` the largest distance of a knife face's vertex from its plane.
    ``knife_classes`` is a set of class values, or a predicate on the stored class value.
    """
    attr = mesh.attributes.get(FACE_CLASS_ATTR)
    if attr is None:
        return {"knife_shading_max_dev_deg": None, "knife_face_max_warp_mm": None, "knife_faces_measured": 0}
    is_knife = knife_classes if callable(knife_classes) else (lambda value: value in knife_classes)
    classes = np.empty(len(mesh.polygons), dtype=np.int32)
    attr.data.foreach_get("value", classes)
    co = np.empty(len(mesh.vertices) * 3, dtype=np.float64)
    mesh.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    corner = np.empty(len(mesh.loops) * 3, dtype=np.float64)
    mesh.corner_normals.foreach_get("vector", corner)
    corner = corner.reshape(-1, 3)
    worst, warp, count = 0.0, 0.0, 0
    for poly in mesh.polygons:
        if not is_knife(int(classes[poly.index])):
            continue
        count += 1
        normal = np.array(poly.normal[:], dtype=np.float64)
        for li in range(poly.loop_start, poly.loop_start + poly.loop_total):
            cos = float(np.clip(corner[li] @ normal / max(np.linalg.norm(corner[li]), 1e-12), -1.0, 1.0))
            worst = max(worst, math.degrees(math.acos(cos)))
        pts = co[list(poly.vertices)]
        warp = max(warp, float(np.abs((pts - pts.mean(axis=0)) @ normal).max()))
    if drop_attribute:
        mesh.attributes.remove(mesh.attributes[FACE_CLASS_ATTR])
    return {"knife_shading_max_dev_deg": round(worst, 4), "knife_face_max_warp_mm": round(warp / MM, 6),
            "knife_faces_measured": count}


def author_lod(o: Outline, lod: LodSpec, name: str, collection, max_pad: int = 16):
    """Author one LOD object, raising ``taper_intervals`` until the band floor is met.

    Returns ``(obj, stats, lod_used)``.  A LOD over its band ceiling is an error: the
    spec asked for more density than study 4 allows and the builder will not guess
    which feature to cut.  A LOD that fails the hygiene gate is an error too - nothing
    with a degenerate is ever handed to Blender, let alone to Unreal.  The generator's
    own triangle count must equal ``spec.wedge_triangles``' prediction.
    """
    taper = lod.taper_intervals
    for _attempt in range(max_pad + 1):
        bm, stats = build_star_bmesh(o, lod, taper)
        # (a pyramid tip has no taper stations: nothing to pad with)
        if stats["triangles"] >= lod.band[0] or taper >= lod.taper_intervals + max_pad or lod.pyramid_tip:
            break
        bm.free()
        taper += 1
    lod_used = replace(lod, taper_intervals=taper)
    # The analytic count in spec.wedge_triangles is what specs plan LODs with; a
    # disagreement is a generator change the formula missed and is refused here rather
    # than silently mis-sizing the next form's LODs.
    stats["predicted_triangles"] = lod_triangles(lod_used, o.n)
    problems = hygiene_problems(stats)
    if stats["triangles"] != stats["predicted_triangles"]:
        problems.append(f"triangles {stats['triangles']} != predicted {stats['predicted_triangles']}")
    if problems:
        bm.free()
        raise RuntimeError(f"{name} failed its own hygiene gate on " + ", ".join(problems))
    if stats["triangles"] > lod.band[1]:
        bm.free()
        raise RuntimeError(f"{name}: {stats['triangles']} triangles is over the study 4 band "
                           f"{lod.band}; reduce its LodSpec counts")

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    stats.update(knife_shading(mesh, KNIFE_CLASSES))
    if stats["knife_shading_max_dev_deg"] > KNIFE_SHADING_GATE_DEG:
        raise RuntimeError(f"{name}: a knife facet's corner normal is {stats['knife_shading_max_dev_deg']:.3f} deg "
                           f"off its face normal (gate {KNIFE_SHADING_GATE_DEG} deg): flat facets are smoothed "
                           f"across a crease")
    co = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", co)
    xy = co.reshape(-1, 3)[:, :2].astype(np.float64)
    write_distance_attributes(mesh, outline_distance(o, xy), hole_distance(o, lod, xy), scallop_distance(o, xy))
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    # Nothing here calls bpy.ops.object.transform_apply: the mesh is authored at the
    # origin with an identity matrix, and the origin is the geometric centre = centre of mass.
    obj.matrix_world = Matrix.Identity(4)
    return obj, stats, lod_used


def hull_outside_distance(hull_co: np.ndarray, hull_faces, points: np.ndarray) -> float:
    """Largest distance (m) by which any of ``points`` lies outside the convex hull's face planes."""
    worst = -math.inf
    centre = hull_co.mean(axis=0)
    for face in hull_faces:
        a, b, c = (hull_co[i] for i in face[:3])
        normal = np.cross(b - a, c - a)
        normal /= np.linalg.norm(normal)
        if np.dot(normal, a - centre) < 0.0:
            normal = -normal
        worst = max(worst, float(((points - a) @ normal).max()))
    return worst


def author_tip_prism_hull(obj, o: Outline, index: int = 0):
    """``UCX_<obj.name>_NN``: the n-gon prism through the tips, at full plate thickness.

    2n vertices, exactly C_n (the tips come from ``spec.rotate``), all faces triangles, so
    it matches what pipeline.make_ucx_hull hands the exporter (closed, convex, no material,
    hidden from render, parented to the render node with an identity matrix, tagged
    ``ue_collision``) - only its vertices are chosen, not decimated.  It encloses the mesh:
    the build raises if any vertex of ``obj`` is outside it by more than HULL_TOLERANCE.  The cost is
    a conservative collider at the very points (full plate thickness where the steel ends
    in a chisel edge), which for a spinning projectile is the right side to err on.
    """
    name = f"UCX_{obj.name}_{index:02d}"
    if bpy.data.objects.get(name) is not None:
        raise ValueError(f"{name!r} already exists")
    n = o.n
    rim = [rotate(k, n, o.r_tip, 0.0) for k in range(n)]
    co = [(x, y, o.half_t) for x, y in rim] + [(x, y, -o.half_t) for x, y in rim]
    faces = []
    for k in range(n):
        k1 = (k + 1) % n
        faces.append((n + k, n + k1, k1))          # side wall, two triangles
        faces.append((n + k, k1, k))
    for k in range(1, n - 1):
        faces.append((0, k, k + 1))                # top cap fan
        faces.append((n, n + k + 1, n + k))        # bottom cap fan
    coords = np.array(co, dtype=np.float64)
    mesh_co = np.array([v.co[:] for v in obj.data.vertices], dtype=np.float64)
    outside = hull_outside_distance(coords, faces, mesh_co)
    # The tip vertices lie ON the prism's side walls; float32 vertex storage puts them up to
    # a few nm either side, so the tolerance is 100 nm, not the 1 nm authoring snap.
    if outside > HULL_TOLERANCE:
        raise RuntimeError(f"{name}: the tip prism does not enclose {obj.name} (a vertex is "
                           f"{outside / MM:.4f} mm outside); use hull='pipeline' for this form")
    bm = bmesh.new()
    verts = [bm.verts.new(p) for p in co]
    for face in faces:
        bm.faces.new([verts[i] for i in face])
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    hull = bpy.data.objects.new(name, mesh)
    for collection in (list(obj.users_collection) or [bpy.context.scene.collection]):
        collection.objects.link(hull)
    hull.parent = obj
    hull.matrix_parent_inverse = Matrix.Identity(4)
    hull.matrix_basis = Matrix.Identity(4)
    hull.hide_render = True
    hull.display_type = "WIRE"
    hull["ue_collision"] = "UCX"
    return hull


__all__ = [
    "Builder", "CHAMFER_CLASSES", "FACE_CLASS_ATTR", "KNIFE_CREASE_DEG", "KNIFE_SHADING_GATE_DEG", "knife_shading", "DEGENERATE_AREA", "DEGENERATE_EDGE", "EDGE_ATTR", "F_CH_BN", "F_CH_BP",
    "F_CH_HOLE_B", "F_CH_HOLE_T", "F_CH_NOTCH_B", "F_CH_NOTCH_T", "F_CH_TN", "F_CH_TP", "F_PLATE", "F_WALL_ARM",
    "F_WALL_HOLE", "F_WALL_NOTCH", "GRIND_ATTR", "HOLE_ATTR", "HULL_TOLERANCE", "KNIFE_CLASSES", "NO_HOLE_DISTANCE",
    "SCALLOP_ATTR", "SMOOTH_CLASSES", "author_lod", "author_tip_prism_hull", "band_faces", "build_star_bmesh",
    "coincident_pairs", "hole_angles", "hole_distance", "hub_angles", "hull_outside_distance", "hygiene_problems",
    "outline_distance", "ring_angles", "scallop_distance", "segment_distance", "wedge", "write_distance_attributes",
    "write_grind_layer",
]
