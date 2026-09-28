"""Radial-star generator: C_n plate, ground bevel, hole ring - authored, never operated.

Hard-won rules carried over from the rev-2 four-point (see build_four_point.py history):

* The plate, including the ground bevel, is authored explicitly.  ``bmesh.ops.bevel``
  silently clamped a requested 0.9 mm bevel to 0.323 mm and left 16 coincident
  vertices / 16 zero-length edges / 16 zero-area triangles at the bevel run-outs,
  which Unreal then stripped (1664 in Blender, 1632 in engine).
* Every vertex goes through a position-keyed factory snapped to 1 nm, so a duplicate
  vertex cannot exist by construction, and every face loop drops repeated indices, so
  a collapsed quad becomes a triangle rather than a sliver.  The build asserts all of
  this before an object is created.
* The facet is a rounded ground facet over the whole taper: it opens from zero at the
  shoulder over the run-out, and past the point where it is wider than the arm the
  two facets meet in a ridge, so the point ends in a chisel edge, not a stub.
* The hub ring bridges the hole ring k:1 (2:1 on the four-point LOD0) instead of a
  sunburst, and the hole polygon is circumscribed so its minimum opening is the stated
  diameter (rev 1's inscribed 16-gon was 7.846 mm across the flats for an "8 mm" hole).
* A large hub around a small hole (the eight-point: 22 mm hub, 9.5 mm hole) makes that
  k:1 fan a pinwheel of 17 mm slivers (median aspect 14, max 19.6).  ``LodSpec.hub_rings``
  switches such a form to graded rings - hole ring, intermediate rings, hub rim - joined
  by a zipper that is authored on the half wedge and mirrored, so every band is mirror-
  symmetric about the arm axis (no chirality) and places one triangle per extra segment.

C_n symmetry is exact.  One canonical wedge (arm 0 on +X, spanning -180/n..+180/n) is
authored per integer n-th turn.  Vertex keys are the snapped *wedge-local* position
plus the wedge index, so every wedge is keyed identically; a point on the upper seam of
wedge k is keyed as the mirrored lower-seam point of wedge k+1, which welds the seams by
key rather than by a float coincidence; points on the axis are shared by all wedges.
World positions come from ``spec.rotate``, which is trig-free for quarter turns, so a
C4 form reproduces rev 2's floats bit-for-bit and any other n is symmetric to float
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

# Face classes.  Smoothing is decided by class, not by dihedral angle: a rounded bevel
# needs smooth shading *inside* the facet and a hard edge where it meets the dead-flat
# plate, and 15 deg / 30 deg steps cannot be separated by one threshold (Blender 5.2 has
# no use_auto_smooth, and the Smooth by Angle modifier cannot express this either).
F_PLATE = 0
F_WALL_ARM = 1
F_WALL_NOTCH = 2
F_WALL_HOLE = 3
F_CH_TP = 4        # top facet, +y edge
F_CH_TN = 5        # top facet, -y edge
F_CH_BP = 6        # bottom facet, +y edge
F_CH_BN = 7        # bottom facet, -y edge
SMOOTH_CLASSES = {F_PLATE, F_WALL_NOTCH, F_WALL_HOLE, F_CH_TP, F_CH_TN, F_CH_BP, F_CH_BN}

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
    """Plate columns as fractions of the half width, exactly antisymmetric."""
    return [(2.0 * j - columns) / columns for j in range(columns + 1)]


def _ring(bld: Builder, o: Outline, x: float, chamfered: bool, fracs, segments: int):
    """One cross-section of the arm at ``x`` as an index bundle.

    ``top``/``bot`` are the plate columns; ``('ct', s)`` / ``('cb', s)`` are the bevel
    profile on side ``s``, running from the wall top (k=0) to the plate edge
    (k=segments).  When the bevel is absent, or the arm has narrowed past the point where
    the facets meet, the entries repeat an index rather than adding a second vertex at
    the same place - Builder.face then collapses the face for us.
    """
    half = o.half_width(x)
    half_t = o.half_t
    ring = {}
    if not chamfered:
        top = [bld.add(x, f * half, half_t) for f in fracs]
        bot = [bld.add(x, f * half, -half_t) for f in fracs]
        ring["top"], ring["bot"] = top, bot
        for side in (1, -1):
            corner_t = top[-1] if side > 0 else top[0]
            corner_b = bot[-1] if side > 0 else bot[0]
            ring[("ct", side)] = [corner_t] * (segments + 1)
            ring[("cb", side)] = [corner_b] * (segments + 1)
        return ring

    by, bz = o.bevel_y, o.bevel_z
    # At the apex station half == by up to float rounding; which branch a 1e-19 m error
    # picks must not matter, so anything within half a snap step counts as the plate
    # branch with a zero-width plate (the columns then weld to one point by key).
    if half >= by - 0.5 * SNAP:
        plate_half = max(0.0, half - by)
        ring["top"] = [bld.add(x, f * plate_half, half_t) for f in fracs]
        ring["bot"] = [bld.add(x, f * plate_half, -half_t) for f in fracs]
        t_max = 0.5 * math.pi
    else:
        # The facets have met: the plate has run out and the section is a roof.
        t_max = math.acos(min(1.0, (by - half) / by))
        z_ridge = (half_t - bz) + bz * math.sin(t_max)
        ridge_t = bld.add(x, 0.0, z_ridge)
        ridge_b = bld.add(x, 0.0, -z_ridge)
        ring["top"] = [ridge_t] * (len(fracs))
        ring["bot"] = [ridge_b] * (len(fracs))
    for side in (1, -1):
        ct, cb = [], []
        for k in range(segments + 1):
            t = t_max * k / segments
            y = (half - by) + by * math.cos(t)
            z = (half_t - bz) + bz * math.sin(t)
            ct.append(bld.add(x, side * y, z))
            cb.append(bld.add(x, side * y, -z))
        ring[("ct", side)] = ct
        ring[("cb", side)] = cb
    return ring


def _bridge(bld: Builder, a, b, segments: int) -> None:
    """Faces between two consecutive arm cross-sections."""
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
            bld.face(top_class, ct_a[k], ct_b[k], ct_b[k + 1], ct_a[k + 1])
            bld.face(bot_class, cb_a[k + 1], cb_b[k + 1], cb_b[k], cb_a[k])
        bld.face(F_WALL_ARM, ct_a[0], ct_b[0], cb_b[0], cb_a[0])


def hub_angles(o: Outline, lod: LodSpec) -> List[float]:
    """Hub-ring angles of one wedge: half notch, arm root arc, half notch.

    Built as an exact mirror (the lower half is the negated upper half), so the wedge
    boundary points at -180/n and +180/n are bit-exact mirror images - which is what
    lets Builder weld the seams by key.
    """
    fracs = _fracs(lod.columns)
    arm = [math.asin(f * o.half_w / o.r_hub) for f in fracs]
    upper = [o.arm_half_angle + (o.half_sector - o.arm_half_angle) * k / lod.notch_segments
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
    """Hub annulus (or disc) as graded rings: hole ring / axis -> hub_rings -> hub rim."""
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


def wedge(bld: Builder, o: Outline, lod: LodSpec, taper_intervals: int) -> None:
    """One 360/n wedge: arm 0 on +X, its hub wedge and the matching hole segments."""
    half_t = o.half_t
    segments = lod.bevel_segments
    fracs = _fracs(lod.columns)
    hub_ang = hub_angles(o, lod)
    last = len(hub_ang) - 1
    hub_t = [bld.add(o.r_hub * math.cos(a), o.r_hub * math.sin(a), half_t, seam=i in (0, last))
             for i, a in enumerate(hub_ang)]
    hub_b = [bld.add(o.r_hub * math.cos(a), o.r_hub * math.sin(a), -half_t, seam=i in (0, last))
             for i, a in enumerate(hub_ang)]

    hole_t = hole_b = None
    if lod.has_hole:
        r_poly = o.hole_polygon_radius(lod.hole_segments * o.n)
        hole_ang = hole_angles(o, lod)
        hlast = len(hole_ang) - 1
        hole_t = [bld.add(r_poly * math.cos(a), r_poly * math.sin(a), half_t, seam=i in (0, hlast))
                  for i, a in enumerate(hole_ang)]
        hole_b = [bld.add(r_poly * math.cos(a), r_poly * math.sin(a), -half_t, seam=i in (0, hlast))
                  for i, a in enumerate(hole_ang)]
    if lod.hub_rings:
        _ring_hub(bld, o, lod, hub_t, hub_b, hole_t, hole_b)
    elif lod.has_hole:
        ratio = lod.hub_segments // lod.hole_segments
        # --- hub annulus: the hole ring bridged k:1 to the hub ring.
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
        for i in range(last):
            bld.face(F_PLATE, centre_t, hub_t[i], hub_t[i + 1])
            bld.face(F_PLATE, centre_b, hub_b[i + 1], hub_b[i])

    # --- rim wall across the notch arcs only; the arm base arc is interior.
    n_notch, n_col = lod.notch_segments, lod.columns
    notch_spans = list(range(n_notch)) + list(range(n_notch + n_col, 2 * n_notch + n_col))
    for i in notch_spans:
        bld.face(F_WALL_NOTCH, hub_t[i], hub_t[i + 1], hub_b[i + 1], hub_b[i])

    # --- hole wall.
    if lod.has_hole:
        for i in range(lod.hole_segments):
            bld.face(F_WALL_HOLE, hole_t[i], hole_t[i + 1], hole_b[i + 1], hole_b[i])

    # --- arm: row 0 IS the hub arc, so the arm grows straight off the round hub.
    root = {"top": hub_t[n_notch:n_notch + n_col + 1],
            "bot": hub_b[n_notch:n_notch + n_col + 1]}
    for side in (1, -1):
        corner_t = root["top"][-1] if side > 0 else root["top"][0]
        corner_b = root["bot"][-1] if side > 0 else root["bot"][0]
        root[("ct", side)] = [corner_t] * (segments + 1)
        root[("cb", side)] = [corner_b] * (segments + 1)

    s = lod.straight_intervals
    straight_x = [o.r_hub + (o.x_taper - o.r_hub) * k / s for k in range(1, s + 1)]
    if lod.has_bevel:
        taper_x = [o.x_runout]
        taper_x += [o.x_runout + (o.x_apex - o.x_runout) * k / taper_intervals
                    for k in range(1, taper_intervals + 1)]
        taper_x += [o.x_apex + (o.r_tip - o.x_apex) * k / lod.tip_intervals
                    for k in range(1, lod.tip_intervals + 1)]
    else:
        taper_x = [o.x_taper + (o.r_tip - o.x_taper) * k / taper_intervals
                   for k in range(1, taper_intervals + 1)]

    rings = [root]
    rings += [_ring(bld, o, x, False, fracs, segments) for x in straight_x]
    rings += [_ring(bld, o, x, lod.has_bevel, fracs, segments) for x in taper_x]
    for i in range(len(rings) - 1):
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


def build_star_bmesh(o: Outline, lod: LodSpec, taper_intervals: int):
    """Author all n wedges through one shared vertex factory and bake smoothing."""
    bld = Builder(o.n)
    for turn in range(o.n):
        bld.turn = turn
        wedge(bld, o, lod, taper_intervals)

    bm = bmesh.new()
    made = [bm.verts.new(co) for co in bld.verts]
    bm.verts.ensure_lookup_table()
    face_class = {}
    for loop, cls in zip(bld.faces, bld.classes):
        face = bm.faces.new([made[i] for i in loop])
        face_class[face] = cls
    bm.faces.ensure_lookup_table()
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))

    for face in bm.faces:
        face.smooth = True
    for edge in bm.edges:
        linked = edge.link_faces
        edge.smooth = (len(linked) == 2
                       and face_class[linked[0]] == face_class[linked[1]]
                       and face_class[linked[0]] in SMOOTH_CLASSES)

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


def author_lod(o: Outline, lod: LodSpec, name: str, collection, max_pad: int = 16):
    """Author one LOD object, raising ``taper_intervals`` until the band floor is met.

    Returns ``(obj, stats, lod_used)``.  A LOD over its band ceiling is an error: the
    spec asked for more density than study 4 allows and the builder will not guess
    which feature to cut.  A LOD that fails the hygiene gate is an error too - nothing
    with a degenerate is ever handed to Blender, let alone to Unreal.
    """
    taper = lod.taper_intervals
    for _attempt in range(max_pad + 1):
        bm, stats = build_star_bmesh(o, lod, taper)
        if stats["triangles"] >= lod.band[0] or taper >= lod.taper_intervals + max_pad:
            break
        bm.free()
        taper += 1
    lod_used = replace(lod, taper_intervals=taper)
    # The analytic count in spec.wedge_triangles is what specs plan LODs with; record it
    # next to the real count so a disagreement (a generator change the formula missed)
    # shows up in the report instead of silently mis-sizing the next form's LODs.
    stats["predicted_triangles"] = lod_triangles(lod_used, o.n)
    problems = hygiene_problems(stats)
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
    "Builder", "DEGENERATE_AREA", "DEGENERATE_EDGE", "F_CH_BN", "F_CH_BP", "F_CH_TN", "F_CH_TP",
    "F_PLATE", "F_WALL_ARM", "F_WALL_HOLE", "F_WALL_NOTCH", "HULL_TOLERANCE", "SMOOTH_CLASSES",
    "author_lod", "author_tip_prism_hull", "band_faces", "build_star_bmesh", "coincident_pairs", "hole_angles",
    "hub_angles", "hull_outside_distance", "hygiene_problems", "ring_angles", "wedge",
]
