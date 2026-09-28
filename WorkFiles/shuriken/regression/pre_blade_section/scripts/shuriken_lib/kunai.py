"""Kunai generator (library 3.10): SM_Kunai_Plain, the pack's first knife, and its FormGeometry hook.

The fifth generator family (radial star, square plate, bar, outline plate, knife), plugged in through the non-radial
Form hook as ``Form(geometry=KunaiGeometry(SPEC))``.  kunai_spec has the frame, the numbers and the analytic head
(columns along the outline, the diamond stations, the shoulder, the run-out, the plunge, the plateau polygon); this
module authors it and everything behind it.

Construction, every LOD (one mesh object, TWO material slots; four closed shells that interpenetrate where they join,
the usual game-asset construction):

    head   (steel, slot 0) the blade and the bare front neck, authored as the upper half (y >= 0) and mirrored in y,
           the top face authored and mirrored in z: an edge band along the outline (column pairs: the facet from the
           wall top to the inner line, its z-mirror, the wall), the diamond blade as structured strips (grind line ->
           ridge per station), one planar plunge triangle per side, the flat stock (the neck plateau) triangulated once
           per LOD by Blender's constrained Delaunay (mathutils.geometry.delaunay_2d_cdt).  The run-out interval (knife
           -> chamfer, twisted) is authored as explicit triangles.
    wrap   (cloth, slot 1) the tape itself: a 9 mm-pitch helix whose exposed edge stands one tape thickness proud
           (kunai_spec.tape_radius), wound down onto the tang over the last TAPER_L at both ends (a lashing), capped
           there by a fan over the cut end.  It is authored in the UNROLLED grip: one strip per grip face, cut by every
           line of ``wrap_cut_lines`` (the tape's profile breaks and the rings inside the wound-down ends), each piece
           a flat face whose corners carry the analytic radius.  3.10.1, the build review: a normal-map-only helix on
           a smooth cylinder with raised collars read as a moulded rubber grip, and the front collar towered 8 mm over
           the 6 mm bare neck, which mirrored it as a black slot in the hero
    neck   (steel) the bare rear tang between the wrap and the ring, an octagon (a chamfered 16 x 5 mm bar) tapering to
           12 x 4.4 mm, its ends buried in the wrap and in the ring
    ring   (steel) a flat forged ring, ID 20 / OD 32 mm, 5 mm stock, edges rounded r 1 mm (8-point section; the rounds
           carry analytic arc normals, the spike's 3.8.1 technique)

Every vertex goes through a 1 nm position-keyed factory (``KeyedBuilder``, one per shell), so a duplicate vertex cannot
exist and the two halves weld on the axis by key; a face loop drops repeated corners (a collapsed quad becomes a
triangle), so the land-0 walls of LOD2, the un-ground reference and the tip need no special case.  No bmesh.ops.bevel.

UVs (hook ``lod_uv``): every LOD's UV0 is written by ONE analytic function of the face's island (recorded at authoring)
and its vertex positions, so all LODs share one texture layout exactly: the head's top and bottom planar, the 0.15 mm
knife lands unfolded onto the top island (a separate 140 mm x 0.15 mm strip was a chart Unreal's lightmap packer laid over
another), the other walls as strips unrolled along the outline, the ring's flats planar and its walls + rounds as strips,
the rear neck's faces, the whole grip unrolled as ONE island (seam on -Z) with the lettering band a rectangle inside it
(3.10.1: its own island left a seam round the band that the visual review read as an outlined panel), the two cut ends.
No island is mirrored (3.10.1: the ring's wall strips, the wrap's caps and two neck chamfers were).  The two material slots sample their own maps
in their own UV TILE: the steel islands in u 0..1 (T_Kunai_Plain_BC / _ORM / _N, 2048, ~134 px/cm), the wrap islands in
u 1..2 (T_Kunai_Wrap_BC / _ORM / _N, 1024, 100 px/cm; texture addressing Wrap, Unreal's default, reads them from the
same texels as u - 1), so no UV0 triangle overlaps another (qa_check's rule holds for the whole mesh, and Unreal's
lightmap UV is generated from non-overlapping charts).  The lettering band is its own straight, unrolled island in the
wrap tile; the wrap material remaps its rectangle to 0..1 and samples T_Kunai_Lettering (kunai_wrap).
"""
from __future__ import annotations

import math
from dataclasses import asdict
from typing import Dict, List, Optional, Tuple

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.geometry import delaunay_2d_cdt

import pipeline

from .geometry import (DEGENERATE_AREA, DEGENERATE_EDGE, EDGE_ATTR, FACE_CLASS_ATTR, GRIND_ATTR, HOLE_ATTR,
                       HULL_TOLERANCE, KNIFE_CREASE_DEG, KNIFE_SHADING_GATE_DEG, NO_HOLE_DISTANCE, SCALLOP_ATTR,
                       coincident_pairs, hull_outside_distance, hygiene_problems, knife_shading, segment_distance,
                       write_grind_layer)
from .hooks import FormGeometry
from .kunai_spec import (BAND_HALF_DEG, BAND_X0, BAND_X1, BLADE_BASE_HALF, BLADE_MAX_AT, BLADE_MAX_HALF, CHAMFER,
                         RIDGE_TIP_AT, dh_blade,
                         CORE_G_CM3, CORE_R, EDGE_T, LAND, NECK_END_HALF, NECK_HALF, NECK_HALF_W, NECK_X0, NECK_X2,
                         REAR_X, RING_A, RING_B, RING_CX, RING_R, RING_ROUND, RUNOUT, STEEL_G_CM3, STOCK, TAN_GRIND,
                         TAPE_BEND, TAPE_G_CM3, TAPE_PITCH, TAPE_RISE, TAPE_T, TAPE_W, TAPER_L, WRAP_R, WRAP_R_FLAT,
                         WRAP_R_SMOOTH, WRAP_X0, WRAP_X1, X_TIP, KunaiLodSpec, KunaiOutline, KunaiPlan, KunaiSpec,
                         grip_angles, h_blade, lash_radius, lash_section, ridge_blade, tape_phase, tape_radius,
                         unground_lod, wrap_radius)
from .material import (CAVITY_ATTR, CAVITY_MODE_PROP, CLASS_ATTR, CLASS_MODE_PROP, RUNOUT_ATTR, RUNOUT_TAPER_PROP,
                       RUST_R, TIP_WEAR, WALL_S_ATTR, WRAP_ATTR, tag_common)
from .measure import evaluated_bm
from .spec import MM, SNAP, scaled_lod_screen_sizes

ISLAND_ATTR = "kunai_island"           # temporary INT face attribute: the UV island a face belongs to
ROUND_ATTR = "kunai_round"             # temporary INT face attribute: 2 the ring's rounds (arc normals), 1 its flats / walls
CLASS_FLAT_KNIFE = 1                   # FACE_CLASS_ATTR value of the knife facets (geometry.knife_shading gate)
WALL_HARD_DEG = 10.0                   # a wall edge is hard above this (the kite corner 23 deg, the shoulder 16 deg)
SMOOTH_HARD_DEG = 12.0                 # inside the diamond, the plateau and the ring flats: hard above this
WRAP_HARD_DEG = 40.0                   # the collar steps (45 deg) are hard, the grip's 18 deg turns smooth

# island ids
I_TOP, I_BOT = 0, 1
I_WALL = {("front", 1): 2, ("front", -1): 3, ("rear", 1): 4, ("rear", -1): 5}
I_WRAP, I_CAP_F, I_CAP_R = 8, 10, 11       # 3.10.1: the lettering band is part of the wrap's own straight unroll
I_RING = {"top": 12, "bottom": 23, "out": 24, "in": 25}
# the knife lands (the 0.15 mm walls between knife columns) are unfolded onto the head's TOP island along the edge they
# hang from (3.10 build review: as part of the wall strip they made a 140 mm x 0.15 mm chart that Unreal's lightmap packer,
# which sees only a chart's texels, laid across the wrap's chart - UV1 overlap on LOD0 / LOD1)
I_LAND = {1: 26, -1: 27}
I_NECK = {"+z": 13, "-z": 14, "+y": 15, "-y": 16, "pp": 17, "np": 18, "pn": 19, "nn": 20, "end_f": 21, "end_r": 22}
ISLAND_NAMES = {I_TOP: "head_top", I_BOT: "head_bottom", I_WRAP: "wrap",
                I_CAP_F: "wrap_cap_front", I_CAP_R: "wrap_cap_rear"}
ISLAND_NAMES.update({v: f"ring_{k}" for k, v in I_RING.items()})
ISLAND_NAMES.update({v: f"land_{'pos' if k > 0 else 'neg'}_y" for k, v in I_LAND.items()})
ISLAND_NAMES.update({v: f"wall_{k[0]}_{'pos' if k[1] > 0 else 'neg'}_y" for k, v in I_WALL.items()})
ISLAND_NAMES.update({v: f"neck_{k}" for k, v in I_NECK.items()})
WRAP_ISLANDS = {I_WRAP, I_CAP_F, I_CAP_R}

# material classes (FACE float shuriken_class, M_Shuriken_Master class mode): coat 1, ground facet 0.5, wall 0
M_COAT, M_FACET, M_WALL = 1.0, 0.5, 0.0
SLOT_STEEL, SLOT_WRAP = 0, 1
SHELLS = ("head", "wrap", "neck", "ring")


# =========================================================================== the vertex factory


class KeyedBuilder:
    """1 nm position-keyed vertex factory for ONE shell (design mm in, stored metres out) plus a face sink that drops
    repeated corners (a collapsed quad becomes a triangle, a fully collapsed one disappears)."""

    def __init__(self, shift_mm: float) -> None:
        self.shift = shift_mm
        self.verts: List[Tuple[float, float, float]] = []
        self.index: Dict[tuple, int] = {}
        self.faces: List[Tuple[int, ...]] = []
        self.classes: List[tuple] = []
        self.islands: List[int] = []
        self.mclass: List[float] = []

    def add(self, x: float, y: float, z: float) -> int:
        key = (round((x - self.shift) * MM / SNAP), round(y * MM / SNAP), round(z * MM / SNAP))
        found = self.index.get(key)
        if found is not None:
            return found
        found = len(self.verts)
        self.index[key] = found
        self.verts.append((key[0] * SNAP, key[1] * SNAP, key[2] * SNAP))
        return found

    def face(self, cls: tuple, island: int, mclass: float, *indices: int) -> None:
        loop: List[int] = []
        for i in indices:
            if not loop or loop[-1] != i:
                loop.append(i)
        while len(loop) > 1 and loop[0] == loop[-1]:
            loop.pop()
        if len(loop) >= 3 and len(set(loop)) == len(loop):
            self.faces.append(tuple(loop))
            self.classes.append(cls)
            self.islands.append(island)
            self.mclass.append(mclass)


# =========================================================================== the head


def plateau_triangles(o: KunaiOutline) -> List[Tuple[int, int, int]]:
    """Constrained Delaunay of the plateau polygon (upper half) + its Steiner points; indices into boundary+steiner.
    The count must be Euler's n_b + 2 n_i - 2."""
    points = list(o.plateau) + list(o.steiner)
    vin = [Vector((x, y)) for x, y in points]
    result = delaunay_2d_cdt(vin, [], [list(range(len(o.plateau)))], 1, 1e-7, True)
    vout, faces, orig = result[0], result[2], result[3]
    if len(vout) != len(points):
        raise RuntimeError(f"plateau CDT changed the vertex set ({len(points)} -> {len(vout)})")
    tris = []
    for face in faces:
        idx = [orig[i][0] for i in face]
        (ax, ay), (bx, by), (cx, cy) = (points[i] for i in idx)
        if (bx - ax) * (cy - ay) - (cx - ax) * (by - ay) < 0.0:
            idx = [idx[0], idx[2], idx[1]]
        tris.append(tuple(idx))
    expected = len(o.plateau) + 2 * len(o.steiner) - 2
    if len(tris) != expected:
        raise RuntimeError(f"plateau triangulation has {len(tris)} triangles, Euler says {expected}")
    return tris


def author_head(bld: KeyedBuilder, o: KunaiOutline) -> dict:
    """The steel head: both halves (y mirror), both faces (z mirror)."""
    cols = o.cols
    i_ctop, i_first = o.runout
    tris = plateau_triangles(o)
    stats = {"plateau_triangles_per_face_half": len(tris), "columns_per_half": len(cols),
             "plateau_boundary_points": len(o.plateau), "plateau_steiner_points": len(o.steiner)}

    for sgn in (1, -1):
        def P(x, y, z):
            return bld.add(x, sgn * y, z)

        def W(c, zs):
            return P(c.ex, c.ey, zs * c.zw)

        def I(c, zs):
            return P(c.ix, c.iy, zs * c.iz)

        # --- edge band: the facet (top, bottom) and the wall between consecutive columns
        for i in range(len(cols) - 1):
            a, b = cols[i], cols[i + 1]
            # the wall between two columns belongs to the FIRST column's chain: the neck's side (shoulder -> rear corner)
            # is on the front chain's reference polyline, the hidden rear face on the rear chain's (3.10 build review: the
            # second column's chain put the neck side on the rear strip, where every point of it unrolled to s = 0)
            chain = a.chain
            wall_island = I_WALL[(chain, sgn)]
            if (i, i + 1) == (i_first, i_ctop):
                # the run-out: the knife narrows into the chamfer; twisted, so two explicit triangles per face
                for zs, island in ((1, I_TOP), (-1, I_BOT)):
                    cls = ("runout", sgn, zs)
                    bld.face(cls, island, M_FACET, W(b, zs), W(a, zs), I(a, zs))
                    bld.face(cls, island, M_FACET, W(b, zs), I(a, zs), I(b, zs))
            else:
                kind = "chamfer" if (a.zone == "chamfer" and b.zone == "chamfer") else "knife"
                for zs, island in ((1, I_TOP), (-1, I_BOT)):
                    bld.face((kind, chain, sgn, zs), island, M_FACET, W(a, zs), W(b, zs), I(b, zs), I(a, zs))
            land = a.zone in ("knife", "tip") and b.zone in ("knife", "tip")
            bld.face(("wall", chain, sgn), I_LAND[sgn] if land else wall_island, M_WALL,
                     W(a, 1), W(a, -1), W(b, -1), W(b, 1))

        # --- diamond strips, the plunge and the plateau (each face)
        for zs, island in ((1, I_TOP), (-1, I_BOT)):
            for st_a, st_b in zip(o.blade, o.blade[1:]):
                if st_a.past_apex:
                    break
                ga, gb = cols[st_a.col], cols[st_b.col]
                ra = st_a.ridge
                rb = st_b.ridge if st_b.ridge is not None else (gb.ix, gb.iy, gb.iz)
                bld.face(("diamond", sgn, zs), island, M_COAT,
                         I(ga, zs), P(ra[0], ra[1], zs * ra[2]), P(rb[0], rb[1], zs * rb[2]), I(gb, zs))
            last = o.blade[-1]
            if not last.past_apex:
                # the un-ground reference has no apex: the last diamond section closes on the tip
                g = cols[last.col]
                r = last.ridge
                tip = cols[0]
                bld.face(("diamond", sgn, zs), island, M_COAT, I(g, zs), P(r[0], r[1], zs * r[2]), I(tip, zs))
            ct, c0, ridge = cols[o.plunge[0]], cols[o.plunge[1]], o.plunge[2]
            bld.face(("plunge", sgn, zs), island, M_COAT, P(ridge[0], ridge[1], zs * ridge[2]), I(ct, zs), I(c0, zs))
            pts = list(o.plateau) + list(o.steiner)
            zp = zs * 0.5 * STOCK
            idx = [P(x, y, zp) for x, y in pts]
            for t in tris:
                bld.face(("plateau", zs), island, M_COAT, *(idx[k] for k in t))
    return stats


# =========================================================================== wrap, neck, ring


def grip_point(x: float, r: float, phi: float) -> Tuple[float, float, float]:
    """phi from +Z (the lettering face) toward +Y."""
    return x, r * math.sin(phi), r * math.cos(phi)


TAPE_BREAKS = (0.0, TAPE_RISE, TAPE_RISE + TAPE_BEND)     # the profile's phases: riser foot, crown, end of the bend
RING_CLEAR = 0.18                                          # mm of x a ring line keeps from every helix crossing


def _ring_clearance(x: float, phis: List[float]) -> float:
    """How far (in x) a ring at ``x`` stays from the tape's helix lines where they cross the grip's vertex lines.

    A ring that crosses a helix line a hair from a vertex line cuts a cell into a hair-thin sliver, and Unreal's
    importer drops a triangle that thin (measured: it dropped two of 2,178 on LOD0), so the engine's mesh would no
    longer be the authored one."""
    best = 1e9
    for c in TAPE_BREAKS:
        for phi in list(phis) + [math.pi]:
            t = (x - WRAP_X0) / TAPE_PITCH + phi / (2.0 * math.pi) - c
            x_helix = WRAP_X0 + TAPE_PITCH * (round(t) + c - phi / (2.0 * math.pi))
            best = min(best, abs(x - x_helix))
    return best


def wrap_cut_lines(lod: KunaiLodSpec) -> List[Tuple[str, float]]:
    """The lines of the unrolled grip that MUST be mesh edges: every break of the tape's profile (a helix, one line per
    break per turn) and the rings inside the wound-down ends.  Everything between them is a flat quad.

    A ring is nudged up to +-1.5 mm from its nominal station to keep RING_CLEAR of every helix crossing (see
    ``_ring_clearance``); the rings only sample the eased taper, so a fraction of a millimetre does not matter."""
    lines: List[Tuple[str, float]] = []
    if lod.tape_relief:
        q_lo = tape_phase(WRAP_X0, math.pi) - 1.0
        q_hi = tape_phase(WRAP_X1, -math.pi) + 1.0
        for k in range(int(math.floor(q_lo)), int(math.ceil(q_hi)) + 1):
            for c in TAPE_BREAKS:
                lines.append(("helix", k + c))
    phis = grip_angles(lod.grip_sides)
    for j in range(lod.taper_rings + 1):
        t = j / (lod.taper_rings + 1)
        for x_target in (WRAP_X1 - TAPER_L + TAPER_L * t, WRAP_X0 + TAPER_L - TAPER_L * t):
            x = x_target
            if lod.tape_relief and _ring_clearance(x_target, phis) < RING_CLEAR:
                best = None
                for step in range(-150, 151):
                    trial = round(x_target + step * 0.01, 6)
                    clear = _ring_clearance(trial, phis)
                    key = (min(clear, RING_CLEAR), -abs(trial - x_target))
                    if best is None or key > best[0]:
                        best = (key, trial)
                x = best[1]
            lines.append(("ring", x))
    return lines


def _line_x(kind: str, value: float):
    """The cut line as design x at a grip angle phi."""
    if kind == "ring":
        return lambda phi: value
    return lambda phi: WRAP_X0 + TAPE_PITCH * (value - phi / (2.0 * math.pi))


# Cut points are exact.  Snapping a cut onto a nearby corner was tried and reverted: a snap is a decision about ONE
# cell, and the cell across the cut line's other edge makes the opposite decision, which tears the shell (15 boundary
# edges) or leaves a corner collinear with its neighbours - a UV-degenerate triangle, which is what Unreal's lightmap
# packer folds a chart over.  Near-coincident cuts therefore author the occasional thin cell (LOD0's smallest edge is
# ~0.02 mm, nothing degenerate: qa_check's limits are 1 um and 1 um2).
CUT_SNAP = 0.0            # mm: off (see above)
CUT_MIN_AREA = 1e-9       # mm2: a piece of literally no area is not a face


def _cut_convex(poly: List[Tuple[float, float]], line, eps: float = 1e-6, snap: float = CUT_SNAP):
    """Split a convex polygon of (x, phi) corners by the line x = line(phi); returns (below, above), either None.

    A corner within ``eps`` mm of the line belongs to both pieces, and a new corner is snapped exactly onto the line, so
    neighbouring pieces (and neighbouring column strips) share the same point and no T-junction can appear.  A cut that
    would land within ``snap`` of an existing corner takes that corner instead: the line then misses that cell by a
    few hundredths of a millimetre and no 20 um sliver is authored.  Both neighbours of an edge see the same points, so
    the mesh stays watertight either way."""
    d = [p[0] - line(p[1]) for p in poly]
    if max(d) <= eps:
        return poly, None
    if min(d) >= -eps:
        return None, poly
    low: List[Tuple[float, float]] = []
    high: List[Tuple[float, float]] = []
    n = len(poly)
    for i in range(n):
        j = (i + 1) % n
        di, dj = d[i], d[j]
        if abs(di) <= eps:
            low.append(poly[i])
            high.append(poly[i])
        elif di < 0.0:
            low.append(poly[i])
        else:
            high.append(poly[i])
        if (di < -eps and dj > eps) or (di > eps and dj < -eps):
            t = di / (di - dj)
            phi = poly[i][1] + t * (poly[j][1] - poly[i][1])
            point = (line(phi), phi)
            near = None
            for k in (i, j):
                if math.hypot(point[0] - poly[k][0], (point[1] - poly[k][1]) * WRAP_R) <= snap:
                    near = k
                    break
            if near is None:
                low.append(point)
                high.append(point)
            else:
                # the cut lands on an existing corner: the corner's own side already has it (or gets it next
                # iteration), the other side takes it here, and no sliver cell is created
                (high if d[near] < 0.0 else low).append(poly[near])

    def area(piece):
        if len(piece) < 3:
            return 0.0
        return 0.5 * abs(sum(piece[k][0] * piece[(k + 1) % len(piece)][1] * WRAP_R
                             - piece[(k + 1) % len(piece)][0] * piece[k][1] * WRAP_R for k in range(len(piece))))
    a_low, a_high = area(low), area(high)
    # a line that only grazes the cell (after the snap) is not a cut: leaving the cell whole keeps its corners off the
    # straight edges, where a collinear corner would make a UV-degenerate triangle - which is what Unreal's lightmap
    # packer folds a chart over
    if a_low <= CUT_MIN_AREA:
        return None, poly
    if a_high <= CUT_MIN_AREA:
        return poly, None
    return (low if len(low) >= 3 else None), (high if len(high) >= 3 else None)


def _drop_collinear(poly: List[Tuple[float, float]], tol: float = 1e-6) -> List[Tuple[float, float]]:
    """Drop a corner that lies ON the straight edge between its neighbours along an END RING (x = WRAP_X0 / WRAP_X1).

    A helix line clipped at the wrap's end leaves such a corner, and a fan over it authors a flat fin between two radii
    (a zero-area piece of the unrolled domain).  There the radius is the wound-down end's section, which does not
    depend on the helix phase, so the corner carries nothing; it is the only piece that touches that segment of the
    ring, and the cut end's fan is built from the corners this function keeps, so the shell stays closed."""
    out = list(poly)
    changed = True
    while changed and len(out) > 3:
        changed = False
        for k in range(len(out)):
            a, b, c = out[k - 1], out[k], out[(k + 1) % len(out)]
            if min(abs(b[0] - WRAP_X0), abs(b[0] - WRAP_X1)) > 1e-9:
                continue
            area = 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) * WRAP_R - (c[0] - a[0]) * (b[1] - a[1]) * WRAP_R)
            if area <= tol:
                del out[k]
                changed = True
                break
    return out


def author_wrap(bld: KeyedBuilder, lod: KunaiLodSpec) -> dict:
    """The cloth tape: a helix whose OVERLAP IS GEOMETRY, wound down onto the tang at both ends.

    The grip is authored in its unrolled (x, phi) domain: one column strip per grip face, cut by every line of
    ``wrap_cut_lines`` (the tape's profile breaks and the rings of the wound-down ends).  Each piece is a flat face
    whose corners carry the analytic radius ``wrap_radius``; the cut points are snapped onto their line, so the pieces
    of neighbouring strips share vertices exactly (the 1 nm keyed factory then welds them)."""
    phis = grip_angles(lod.grip_sides)
    n = len(phis)
    lines = [(kind, value, _line_x(kind, value)) for kind, value in wrap_cut_lines(lod)]
    ends: Dict[str, Dict[int, Tuple[int, float]]] = {"front": {}, "rear": {}}
    faces = 0

    def point(x: float, phi: float) -> int:
        r = wrap_radius(x, phi, relief=lod.tape_relief)
        index = bld.add(*grip_point(x, r, phi))
        for key, xs in (("front", WRAP_X1), ("rear", WRAP_X0)):
            if abs(x - xs) <= 1e-6:
                ends[key][round(phi * 1e6)] = (index, phi)
        return index

    for j in range(n):
        p0 = phis[j]
        p1 = phis[j + 1] if j + 1 < n else math.pi
        pieces = [[(WRAP_X0, p0), (WRAP_X1, p0), (WRAP_X1, p1), (WRAP_X0, p1)]]
        for _kind, _value, line in lines:
            out: List[List[Tuple[float, float]]] = []
            for piece in pieces:
                low, high = _cut_convex(piece, line)
                out += [p for p in (low, high) if p is not None]
            pieces = out
        for piece in pieces:
            piece = _drop_collinear(piece)
            area = 0.5 * abs(sum(piece[k][0] * piece[(k + 1) % len(piece)][1] * WRAP_R
                                 - piece[(k + 1) % len(piece)][0] * piece[k][1] * WRAP_R for k in range(len(piece))))
            if len(piece) < 3 or area <= 1e-6:
                continue
            idx = [point(x, phi) for x, phi in piece]
            if len(idx) <= 4:
                bld.face(("wrap", "body"), I_WRAP, M_COAT, *idx)
            else:                                   # a cut corner: fan the convex piece (no n-gon may ship)
                for k in range(1, len(idx) - 1):
                    bld.face(("wrap", "body"), I_WRAP, M_COAT, idx[0], idx[k], idx[k + 1])
            faces += 1
    # the two cut ends: a fan round a centre vertex (which sits inside the steel), over the boundary ring as authored
    for key, island, xs in (("front", I_CAP_F, WRAP_X1), ("rear", I_CAP_R, WRAP_X0)):
        ring = sorted(ends[key].values(), key=lambda item: item[1])
        centre = bld.add(xs, 0.0, 0.0)
        for k in range(len(ring)):
            a, b = ring[k][0], ring[(k + 1) % len(ring)][0]
            bld.face(("wrap_cap", island), island, M_COAT, centre, b, a)
    front, rear = lash_section(True), lash_section(False)
    return {"sides": n, "tape_relief": bool(lod.tape_relief), "cut_lines": len(lines), "pieces": faces,
            "end_ring_vertices": {"front": len(ends["front"]), "rear": len(ends["rear"])},
            "grip_angles_deg": [round(math.degrees(p), 6) for p in phis],
            "tape": {"width_mm": TAPE_W, "pitch_mm": TAPE_PITCH, "thickness_mm": TAPE_T,
                     "turns": round((WRAP_X1 - WRAP_X0) / TAPE_PITCH, 4),
                     "radius_mm": [WRAP_R_FLAT, WRAP_R] if lod.tape_relief else [WRAP_R_SMOOTH, WRAP_R_SMOOTH]},
            "wound_down_ends": {"length_mm": TAPER_L,
                                "front_section_mm": [round(v, 4) for v in front],
                                "rear_section_mm": [round(v, 4) for v in rear]}}


def neck_half(x: float) -> Tuple[float, float]:
    t = min(max((x - NECK_X0) / (NECK_X2 - NECK_X0), 0.0), 1.0)
    return (NECK_HALF[0] + (NECK_END_HALF[0] - NECK_HALF[0]) * t, NECK_HALF[1] + (NECK_END_HALF[1] - NECK_HALF[1]) * t)


def neck_section(x: float, chamfer: float):
    """The rear neck's section at design x, CCW seen from +X: [(y, z)] (octagon, or a rectangle without a chamfer)."""
    hw, ht = neck_half(x)
    c = chamfer
    if c <= 0.0:
        return [(hw, ht), (-hw, ht), (-hw, -ht), (hw, -ht)]
    return [(hw, ht - c), (hw - c, ht), (-(hw - c), ht), (-hw, ht - c), (-hw, -(ht - c)), (-(hw - c), -ht),
            (hw - c, -ht), (hw, -(ht - c))]


def author_neck(bld: KeyedBuilder, lod: KunaiLodSpec) -> dict:
    xs = [NECK_X0, NECK_X2]
    secs = [neck_section(x, lod.neck_chamfer) for x in xs]
    rows = [[bld.add(x, y, z) for (y, z) in sec] for x, sec in zip(xs, secs)]
    m = len(secs[0])
    names = ["pp", "+z", "np", "-y", "nn", "-z", "pn", "+y"] if m == 8 else ["+z", "-y", "-z", "+y"]
    for k in range(m):
        k1 = (k + 1) % m
        name = names[k]
        mc = M_WALL if name in ("+y", "-y") else M_COAT
        bld.face(("neck", name), I_NECK[name], mc, rows[0][k], rows[1][k], rows[1][k1], rows[0][k1])
    for j, name in ((0, "end_f"), (1, "end_r")):                 # both ends buried: fans
        ring = rows[j]
        for k in range(1, m - 1):
            bld.face(("neck", name), I_NECK[name], M_WALL, ring[0], ring[k], ring[k + 1])
    return {"section_points": m, "chamfer_mm": lod.neck_chamfer, "x_mm": xs}


def ring_section(kind: str) -> List[Tuple[float, float, str, str]]:
    """(dr, z, face kind, UV island of the side from this point to the next) around the ring's section, CCW in (dr, z).
    Islands: the flat top and bottom are planar ("top" / "bottom"); the outer wall with its two rounds is one strip
    ("out"), the inner wall with its rounds another ("in") - so no UV seam crosses a flat face."""
    a, b, rho = RING_A, RING_B, RING_ROUND
    if kind == "square":
        return [(a, b, "flat_top", "top"), (-a, b, "wall_in", "in"), (-a, -b, "flat_bottom", "bottom"),
                (a, -b, "wall_out", "out")]
    return [(a, b - rho, "round", "out"), (a - rho, b, "flat_top", "top"), (-(a - rho), b, "round", "in"),
            (-a, b - rho, "wall_in", "in"), (-a, -(b - rho), "round", "in"), (-(a - rho), -b, "flat_bottom", "bottom"),
            (a - rho, -b, "round", "out"), (a, -(b - rho), "wall_out", "out")]


def ring_point(theta: float, dr: float, z: float) -> Tuple[float, float, float]:
    rr = RING_R + dr
    return RING_CX + rr * math.cos(theta), rr * math.sin(theta), z


def author_ring(bld: KeyedBuilder, lod: KunaiLodSpec) -> dict:
    n = lod.ring_segments
    sec = ring_section(lod.ring_section)
    m = len(sec)
    grid = [[bld.add(*ring_point(2.0 * math.pi * i / n, dr, z)) for dr, z, _k, _i in sec] for i in range(n)]
    for i in range(n):
        i1 = (i + 1) % n
        for j in range(m):
            j1 = (j + 1) % m
            kind, island = sec[j][2], sec[j][3]
            mc = M_WALL if kind.startswith("wall") else M_COAT
            bld.face(("ring", kind), I_RING[island], mc, grid[i][j], grid[i1][j], grid[i1][j1], grid[i][j1])
    return {"segments": n, "section": lod.ring_section, "section_points": m}


# =========================================================================== one LOD mesh


def build_kunai_bmesh(plan: KunaiPlan, lod: KunaiLodSpec, shift_mm: float, parts=SHELLS):
    """All shells through their own keyed factories, merged into one bmesh with smoothing baked by class."""
    o = plan.outline(lod)
    shells, stats = [], {}
    for name in parts:
        b = KeyedBuilder(shift_mm)
        stats[name] = {"head": lambda: author_head(b, o), "wrap": lambda: author_wrap(b, lod),
                       "neck": lambda: author_neck(b, lod), "ring": lambda: author_ring(b, lod)}[name]()
        shells.append((name, b))

    bm = bmesh.new()
    # layers are created before any face (adding one later reallocates the faces)
    class_layer = bm.faces.layers.int.new(FACE_CLASS_ATTR)
    island_layer = bm.faces.layers.int.new(ISLAND_ATTR)
    round_layer = bm.faces.layers.int.new(ROUND_ATTR)
    mclass_layer = bm.faces.layers.float.new(CLASS_ATTR)
    wrap_layer = bm.faces.layers.float.new(WRAP_ATTR)
    face_class, vert_shell, face_shell = {}, [], {}
    for name, b in shells:
        made = [bm.verts.new(co) for co in b.verts]
        vert_shell += [name] * len(made)
        for loop, cls, island, mc in zip(b.faces, b.classes, b.islands, b.mclass):
            face = bm.faces.new([made[i] for i in loop])
            face_class[face] = cls
            face_shell[face] = name
            face[class_layer] = CLASS_FLAT_KNIFE if cls[0] in ("knife", "runout") else 0
            face[island_layer] = island
            # 1 the ring's flats (face normal), 2 its rounds (arc normal), 3 its walls (radial normal: 3.10.1, the
            # 24-gon's walls shade as the round wall they stand for instead of flat panels)
            face[round_layer] = ((2 if cls[1] == "round" else (3 if cls[1].startswith("wall") else 1))
                                 if cls[0] == "ring" else 0)
            face[mclass_layer] = mc
            is_wrap = cls[0] in ("wrap", "wrap_cap")
            face[wrap_layer] = 1.0 if is_wrap else 0.0
            face.material_index = SLOT_WRAP if is_wrap else SLOT_STEEL
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.normal_update()

    crease = math.radians(KNIFE_CREASE_DEG)
    counts = {"knife_crease": 0, "hard_corner": 0}
    for face in bm.faces:
        face.smooth = True
    for edge in bm.edges:
        linked = edge.link_faces
        smooth = False
        if len(linked) == 2:
            ca, cb = face_class[linked[0]], face_class[linked[1]]
            kind = ca[0]
            angle = linked[0].normal.angle(linked[1].normal, 0.0)
            if kind == "wrap" and cb[0] == "wrap":
                smooth = angle <= math.radians(WRAP_HARD_DEG)
            elif ca == cb:
                if kind in ("knife", "runout"):
                    smooth = angle <= crease
                    counts["knife_crease"] += not smooth
                elif kind == "wall":
                    smooth = angle <= math.radians(WALL_HARD_DEG)
                elif kind in ("diamond", "plateau", "chamfer", "wrap_cap"):
                    smooth = angle <= math.radians(SMOOTH_HARD_DEG)
                elif kind == "ring":
                    smooth = True                         # curved around the ring; the flats' corners get arc normals
                elif kind == "neck":
                    smooth = angle <= math.radians(SMOOTH_HARD_DEG)
                counts["hard_corner"] += (not smooth and kind not in ("knife", "runout"))
            elif kind == "ring" and cb[0] == "ring":
                smooth = True                             # flat <-> round: continuous through the arc normals
        edge.smooth = smooth

    grind_segments = write_grind_layer(bm, lambda f: face_class[f][0] in ("diamond", "plateau", "plunge"),
                                       lambda f: face_class[f][0] in ("knife", "runout"))
    volumes = {}
    for name, _b in shells:
        vol6, mom = 0.0, np.zeros(3)
        for face in bm.faces:
            if face_shell[face] != name:
                continue
            pts = [np.array(v.co[:], dtype=np.float64) for v in face.verts]
            for k in range(1, len(pts) - 1):
                tv = float(np.dot(pts[0], np.cross(pts[k], pts[k + 1])))
                vol6 += tv
                mom += tv * (pts[0] + pts[k] + pts[k + 1])
        volumes[name] = (vol6 / 6.0, mom / (4.0 * vol6) if vol6 else np.zeros(3))
    shell_counts = {name: (len(b.verts), len(b.faces)) for name, b in shells}
    st = {
        "authored_vertices": len(bm.verts),
        "authored_faces": len(bm.faces),
        "quads": sum(1 for f in bm.faces if len(f.verts) == 4),
        "tris": sum(1 for f in bm.faces if len(f.verts) == 3),
        "ngons": sum(1 for f in bm.faces if len(f.verts) > 4),
        "non_manifold_edges": sum(1 for e in bm.edges if len(e.link_faces) > 2 or not e.link_faces),
        "boundary_edges": sum(1 for e in bm.edges if len(e.link_faces) == 1),
        "loose_verts": sum(1 for v in bm.verts if not v.link_edges),
        "zero_length_edges": sum(1 for e in bm.edges if e.calc_length() <= DEGENERATE_EDGE),
        "zero_area_faces": sum(1 for f in bm.faces if f.calc_area() <= DEGENERATE_AREA),
        "sharp_edges": sum(1 for e in bm.edges if not e.smooth),
        "knife_crease_edges": counts["knife_crease"],
        "hard_corner_edges": counts["hard_corner"],
        "knife_faces": sum(1 for f in bm.faces if face_class[f][0] in ("knife", "runout")),
        "grind_line_segments": grind_segments,
        "signed_volume_m3": bm.calc_volume(signed=True),
        "min_edge_mm": min(e.calc_length() for e in bm.edges) / MM,
        "min_face_area_mm2": min(f.calc_area() for f in bm.faces) / (MM ** 2),
        "shells": {name: {"vertices": shell_counts[name][0], "faces": shell_counts[name][1],
                          "volume_mm3": round(volumes[name][0] / MM ** 3, 4),
                          "centroid_mm": [round(float(c) / MM + (shift_mm if i == 0 else 0.0), 6)
                                          for i, c in enumerate(volumes[name][1])]}
                   for name, _b in shells},
        "per_shell_signed_volume_positive": all(volumes[name][0] > 0.0 for name in volumes),
        "material_slots": {"steel": sum(1 for f in bm.faces if f.material_index == SLOT_STEEL),
                           "wrap": sum(1 for f in bm.faces if f.material_index == SLOT_WRAP)},
    }
    st.update({f"{k}_detail": v for k, v in stats.items()})
    coords = np.array([v.co[:] for v in bm.verts], dtype=np.float64)
    st["coincident_vertices"] = coincident_pairs(coords)
    st["triangles"] = st["tris"] + 2 * st["quads"] + sum(len(f.verts) - 2 for f in bm.faces if len(f.verts) > 4)
    return bm, st, o, vert_shell, face_class


# =========================================================================== analytic distances (material attributes)


class HeadDistances:
    """Reference polylines of the analytic outline (design mm), cached per plan."""

    def __init__(self, plan: KunaiPlan) -> None:
        ref = plan.reference_chains(step=0.05)
        self.chains = {k: np.array(v, dtype=np.float64) for k, v in ref.items()}
        self.cum = {}
        for k, p in self.chains.items():
            seg = np.linalg.norm(np.diff(p, axis=0), axis=1)
            self.cum[k] = np.concatenate([[0.0], np.cumsum(seg)])
        self.outline = np.concatenate([self.chains["front"], self.chains["rear"]])
        front = self.chains["front"]
        ctop = np.array(plan.ctop)
        i0 = int(np.argmin(np.linalg.norm(front - ctop, axis=1)))
        # the non-cutting outline: from the chamfer's run-out end back round the shoulder, along the neck, the rear
        self.chamfer_poly = np.concatenate([np.array([plan.ctop]), front[i0 + 1:], self.chains["rear"]])
        # the knife edge from its full-knife start (the plunge station) toward the tip, and the run-out behind it
        xp = plan.x_plunge
        self.knife = np.array([(x, h_blade(x)) for x in np.linspace(xp, X_TIP, 3000)])
        self.runout_edge = np.array([(plan.shoulder[0] + t * plan.e1[0], plan.shoulder[1] + t * plan.e1[1])
                                     for t in np.linspace(xp / plan.e1[0], 0.0, 160)])
        self.plan = plan

    @staticmethod
    def _poly_dist(pts: np.ndarray, poly: np.ndarray) -> np.ndarray:
        return segment_distance(pts, poly[:-1], poly[1:], chunk=128)

    def arc_length(self, chain: str, pts: np.ndarray) -> np.ndarray:
        """Arc length (mm) along a reference chain of the nearest chain point to each (x, |y|)."""
        poly = self.chains[chain]
        a, b = poly[:-1], poly[1:]
        d = b - a
        l2 = np.maximum(np.einsum("sj,sj->s", d, d), 1e-30)
        out = np.empty(len(pts))
        for start in range(0, len(pts), 64):
            p = pts[start:start + 64][:, None, :]
            t = np.clip(np.einsum("psj,sj->ps", p - a[None], d) / l2, 0.0, 1.0)
            closest = a[None] + t[..., None] * d[None]
            dist = np.linalg.norm(p - closest, axis=-1)
            k = np.argmin(dist, axis=1)
            out[start:start + 64] = self.cum[chain][k] + t[np.arange(len(k)), k] * np.sqrt(l2[k])
        return out

    def attributes(self, xy: np.ndarray) -> dict:
        """Design-frame plan points (x, y) -> the material's distances, metres."""
        q = np.column_stack([xy[:, 0], np.abs(xy[:, 1])])
        edge = self._poly_dist(q, self.outline)
        scallop = self._poly_dist(q, self.chamfer_poly)
        # run-out distance: nearest knife / run-out edge sample -> contour distance past the full knife's start
        kn_len = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(self.knife, axis=0), axis=1))])
        ro_len = -np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(self.runout_edge, axis=0), axis=1))])
        cp = np.concatenate([self.knife, self.runout_edge])
        cv = np.concatenate([kn_len, ro_len])
        runout = np.empty(len(q))
        for start in range(0, len(q), 128):
            d = np.linalg.norm(q[start:start + 128, None, :] - cp[None], axis=-1)
            runout[start:start + 128] = cv[np.argmin(d, axis=1)]
        # the chamfer-zone outline is not a blade (the hooked cross's RUNOUT_NOT_BLADE for points nearer to it)
        not_blade = scallop < edge + 1e-9
        runout = np.where(not_blade & (edge < 3.0), -10.0, runout)
        return {"edge": edge * MM, "scallop": scallop * MM, "runout": runout * MM}


def write_kunai_attributes(mesh, dist: HeadDistances, shift_mm: float, vert_shell: List[str]) -> dict:
    nv = len(mesh.vertices)
    co = np.empty(nv * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3).astype(np.float64)
    xy = np.column_stack([co[:, 0] / MM + shift_mm, co[:, 1] / MM])
    head = np.array([s == "head" for s in vert_shell])
    far = NO_HOLE_DISTANCE
    vals = {"edge": np.full(nv, far), "scallop": np.full(nv, far), "runout": np.full(nv, -0.01)}
    if head.any():
        got = dist.attributes(xy[head])
        for k in vals:
            vals[k][head] = got[k]
    # 3.10.1: arc length ALONG a wall, so the material can lay its scratch and pit cells in the wall's own plane
    # (material.WALL_S_ATTR): the outline's arc length on the head, the ring's own arc length round it, design x on
    # the rear neck (its walls are its +-y faces).  Unused on the wrap (its own material) and on non-wall faces.
    wall_s = np.zeros(nv)
    if head.any():
        wall_s[head] = dist.arc_length("front", np.column_stack([xy[head, 0], np.abs(xy[head, 1])])) * MM
    neck = np.array([s == "neck" for s in vert_shell])
    if neck.any():
        wall_s[neck] = xy[neck, 0] * MM
    ring = np.array([s == "ring" for s in vert_shell])
    if ring.any():
        theta = np.arctan2(xy[ring, 1], xy[ring, 0] - RING_CX) % (2.0 * math.pi)
        wall_s[ring] = theta * RING_R * MM
    grind = mesh.attributes.get(GRIND_ATTR)
    g = np.empty(nv, dtype=np.float32)
    grind.data.foreach_get("value", g)
    grind.data.foreach_set("value", np.where(head, g, 1.0).astype(np.float32))
    for name, values in ((EDGE_ATTR, vals["edge"]), (HOLE_ATTR, np.full(nv, far)), (SCALLOP_ATTR, vals["scallop"]),
                         (CAVITY_ATTR, np.full(nv, far)), (RUNOUT_ATTR, vals["runout"]), (WALL_S_ATTR, wall_s)):
        attr = mesh.attributes.get(name) or mesh.attributes.new(name, "FLOAT", "POINT")
        attr.data.foreach_set("value", np.asarray(values, dtype=np.float32))
    mesh.update()
    return {"head_vertices": int(head.sum()), "other_vertices": int((~head).sum())}


def write_ring_normals(mesh, shift_mm: float) -> dict:
    """Custom split normals on the ring: the analytic normal of the true (round) surface on every loop of its r 1 mm
    rounds AND of its inner / outer walls, the exact face normal on its flats; the mesh's own corner normals (from its
    smooth / sharp edges) everywhere else.

    A round vertex (dr, z) lies on the arc of radius RING_ROUND about its corner's centre (sign(dr) (a - rho),
    sign(z) (b - rho)) in the ring's section plane (the spike's 3.8.1 technique).  A WALL vertex takes the radial
    direction, so the 24-gon's walls shade as the round wall they stand for - 3.10.1, visual review: they were
    flat-shaded panels with a hard seam on every facet edge, unlike the stars' smooth hole walls, and the ring read
    faceted in close-ups and in Fab's orbit viewer."""
    kinds = np.empty(len(mesh.polygons), dtype=np.int32)
    mesh.attributes[ROUND_ATTR].data.foreach_get("value", kinds)
    corner = np.empty(len(mesh.loops) * 3, dtype=np.float64)
    mesh.corner_normals.foreach_get("vector", corner)
    normals = corner.reshape(-1, 3).copy()
    co = np.empty(len(mesh.vertices) * 3, dtype=np.float64)
    mesh.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    loop_vert = np.empty(len(mesh.loops), dtype=np.int64)
    mesh.loops.foreach_get("vertex_index", loop_vert)
    cx = (RING_CX - shift_mm) * MM
    ca, cb = (RING_A - RING_ROUND) * MM, (RING_B - RING_ROUND) * MM
    worst, rounds, flats, walls = 0.0, 0, 0, 0
    for poly in mesh.polygons:
        kind = int(kinds[poly.index])
        if kind == 0:
            continue
        if kind == 1:
            normals[poly.loop_start:poly.loop_start + poly.loop_total] = tuple(poly.normal)
            flats += poly.loop_total
            continue
        if kind == 3:                             # a wall: the radial direction, outward for the face it belongs to
            out = 1.0 if (poly.normal[0] * (poly.center[0] - cx) + poly.normal[1] * poly.center[1]) > 0.0 else -1.0
            for li in poly.loop_indices:
                p = co[loop_vert[li]]
                dx, dy = p[0] - cx, p[1]
                rr = math.hypot(dx, dy)
                normals[li] = (out * dx / rr, out * dy / rr, 0.0)
                walls += 1
            continue
        for li in poly.loop_indices:
            p = co[loop_vert[li]]
            dx, dy = p[0] - cx, p[1]
            rr = math.hypot(dx, dy)
            ux, uy = dx / rr, dy / rr
            dr = rr - RING_R * MM
            er, ez = dr - math.copysign(ca, dr), p[2] - math.copysign(cb, p[2])
            rad = math.hypot(er, ez)
            worst = max(worst, abs(rad - RING_ROUND * MM))
            normals[li] = (ux * er / rad, uy * er / rad, ez / rad)
            rounds += 1
    mesh.normals_split_custom_set([tuple(n) for n in normals])
    mesh.update()
    return {"method": ("custom split normals on the ring: the analytic arc normal on every loop of its r 1 mm rounds, "
                       "the radial normal on its inner and outer walls (they stand for a round wall), the face normal "
                       "on its flats; the mesh's own corner normals elsewhere"),
            "round_loops": rounds, "wall_loops": walls, "flat_loops": flats,
            "round_vertex_radius_error_mm": round(worst / MM, 9)}


def author_kunai_lod(plan: KunaiPlan, dist: HeadDistances, lod: KunaiLodSpec, shift_mm: float, name: str,
                     collection):
    bm, stats, o, vert_shell, face_class = build_kunai_bmesh(plan, lod, shift_mm)
    problems = hygiene_problems(stats)
    if not stats["per_shell_signed_volume_positive"]:
        problems.append("a shell is inside out")
    if problems:
        bm.free()
        raise RuntimeError(f"{name} failed its own hygiene gate on " + ", ".join(problems))
    if stats["triangles"] > lod.band[1]:
        bm.free()
        raise RuntimeError(f"{name}: {stats['triangles']} triangles is over its ceiling {lod.band}")
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    stats.update(knife_shading(mesh, {CLASS_FLAT_KNIFE}, drop_attribute=True))
    if stats["knife_shading_max_dev_deg"] is not None and stats["knife_shading_max_dev_deg"] > KNIFE_SHADING_GATE_DEG:
        raise RuntimeError(f"{name}: a knife facet's corner normal is {stats['knife_shading_max_dev_deg']:.3f} deg off "
                           f"its face normal (gate {KNIFE_SHADING_GATE_DEG} deg)")
    stats["attributes"] = write_kunai_attributes(mesh, dist, shift_mm, vert_shell)
    ranges, start = {}, 0
    for shell in SHELLS:
        count = sum(1 for v in vert_shell if v == shell)
        ranges[shell] = (start, start + count)
        start += count
    stats["shell_vertex_ranges"] = ranges
    stats["outline_info"] = {k: (list(v) if isinstance(v, tuple) else v) for k, v in o.info.items()}
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.matrix_world = Matrix.Identity(4)
    return obj, stats, lod


def finish_normals(obj, shift_mm: float) -> dict:
    """After UV0 exists: the ring's custom normals, then the temporary round attribute goes."""
    mesh = obj.data
    out = write_ring_normals(mesh, shift_mm)
    mesh.attributes.remove(mesh.attributes[ROUND_ATTR])
    return out


# =========================================================================== UV layout (every LOD, analytic)


class UVLayout:
    """Deterministic island rectangles in pixels (origin at the map's lower-left) per tile, and the island functions.

    Tile 0 (u 0..1): the steel islands on a ``steel_px`` map at ``steel_px_per_mm``.  Tile 1 (u 1..2): the wrap islands
    on a ``wrap_px`` map at ``wrap_px_per_mm`` - the wrap body unrolled with its seam on -Z, the lettering band as its own
    straight island, the two caps."""

    GAP = 24.0
    BORDER = 16.0

    def __init__(self, spec: KunaiSpec, dist: HeadDistances) -> None:
        S, Wp = float(spec.steel_px), float(spec.wrap_px)
        self.S, self.Wp = S, Wp
        ds, dw = spec.steel_px_per_mm, spec.wrap_px_per_mm
        self.ds, self.dw = ds, dw
        b, g = self.BORDER, self.GAP
        self.head_x0, self.head_y0 = REAR_X, -18.0
        head_w, head_h = (X_TIP - REAR_X) * ds, 36.0 * ds
        steel, wrap = {}, {}
        steel["head_top"] = (b, b, head_w, head_h)
        steel["head_bottom"] = (b, b + head_h + g, head_w, head_h)
        self.chain_len = {k: float(dist.cum[k][-1]) for k in dist.cum}
        # the front wall strip starts at the plunge station (the knife lands are on the top island)
        xp = dist.plan.x_plunge
        self.chain_start = {"front": float(dist.arc_length("front", np.array([[xp, h_blade(xp)]]))[0]) - 0.05,
                            "rear": 0.0}
        self.land_half = 0.5 * LAND
        strip_h = STOCK * ds
        front_len = (self.chain_len["front"] - self.chain_start["front"]) * ds
        y = b + 2.0 * (head_h + g)
        steel["wall_front_pos_y"] = (b, y, front_len, strip_h)
        steel["wall_front_neg_y"] = (b + front_len + g, y, front_len, strip_h)
        y += strip_h + g
        a, bb, rho = RING_A, RING_B, RING_ROUND
        self.ring_out_r, self.ring_in_r = RING_R + a, RING_R - a
        self.ring_strip = 2.0 * (bb - rho) + math.pi * rho          # a wall and its two quarter rounds, mm
        d_out = 2.0 * self.ring_out_r * ds
        steel["ring_top"] = (b, y, d_out, d_out)
        steel["ring_bottom"] = (b + d_out + g, y, d_out, d_out)
        ys = y + d_out + g
        steel["ring_out"] = (b, ys, 2.0 * math.pi * self.ring_out_r * ds, self.ring_strip * ds)
        steel["ring_in"] = (b, ys + self.ring_strip * ds + g, 2.0 * math.pi * self.ring_in_r * ds,
                            self.ring_strip * ds)
        x = b + 2.0 * (d_out + g)
        neck_len = NECK_X0 - NECK_X2
        steel["neck_+z"] = (x, y, neck_len * ds, 2.0 * NECK_HALF[0] * ds)
        steel["neck_-z"] = (x + neck_len * ds + g, y, neck_len * ds, 2.0 * NECK_HALF[0] * ds)
        x2 = x + 2.0 * (neck_len * ds + g)
        steel["neck_+y"] = (x2, y, neck_len * ds, 2.0 * NECK_HALF[1] * ds)
        steel["neck_-y"] = (x2, y + 2.0 * NECK_HALF[1] * ds + g, neck_len * ds, 2.0 * NECK_HALF[1] * ds)
        x3 = x2 + neck_len * ds + g
        ch_h = max(NECK_HALF[0], NECK_HALF[1]) * 0.0 + 0.6 * math.sqrt(2.0) * ds
        for k, key in enumerate(("neck_pp", "neck_np", "neck_pn", "neck_nn")):
            steel[key] = (x3, y + k * (ch_h + g), neck_len * ds, ch_h)
        x4 = x3 + neck_len * ds + g
        q = 0.25
        steel["neck_end_f"] = (x4, y, 2.0 * NECK_HALF[0] * ds * q, 2.0 * NECK_HALF[1] * ds * q)
        steel["neck_end_r"] = (x4, y + 2.0 * NECK_HALF[1] * ds * q + g, 2.0 * NECK_HALF[0] * ds * q,
                               2.0 * NECK_HALF[1] * ds * q)
        yw = y + 2.0 * NECK_HALF[0] * ds + g
        steel["wall_rear_pos_y"] = (x, yw, self.chain_len["rear"] * ds, strip_h)
        steel["wall_rear_neg_y"] = (x + self.chain_len["rear"] * ds + g, yw, self.chain_len["rear"] * ds, strip_h)
        # ---- wrap tile: the grip unrolled as ONE island (x along u, the arc around it along v, seam on -Z), the
        # lettering band a RECTANGLE INSIDE it (3.10.1: its own island left a seam across the grip that the visual
        # review read as an outlined panel), and the two cut ends
        wrap_len = WRAP_X1 - WRAP_X0
        wrap["wrap"] = (b, b, wrap_len * dw, 2.0 * math.pi * WRAP_R * dw)
        self.band_half = math.radians(BAND_HALF_DEG)
        self.cap_px_per_mm = 9.0
        cap_f, cap_r = lash_section(True), lash_section(False)
        cap_w = 2.0 * max(cap_f[0], cap_r[0]) * self.cap_px_per_mm
        cap_h = 2.0 * max(cap_f[1], cap_r[1]) * self.cap_px_per_mm
        self.cap_half = (max(cap_f[0], cap_r[0]), max(cap_f[1], cap_r[1]))
        yc = b + 2.0 * math.pi * WRAP_R * dw + g
        wrap["wrap_cap_front"] = (b, yc, cap_w, cap_h)
        wrap["wrap_cap_rear"] = (b + cap_w + g, yc, cap_w, cap_h)
        self.rects = {"steel": steel, "wrap": wrap}
        for tile, rects, size in (("steel", steel, S), ("wrap", wrap, Wp)):
            for name, (rx, ry, rw, rh) in rects.items():
                if rx < b - 1e-6 or ry < b - 1e-6 or rx + rw > size - b + 1e-6 or ry + rh > size - b + 1e-6:
                    raise ValueError(f"UV layout: {name} {rx:.1f},{ry:.1f} {rw:.1f}x{rh:.1f} leaves the {size:g} map")
            names = list(rects)
            for i, n1 in enumerate(names):
                ax, ay, aw, ah = rects[n1]
                for n2 in names[i + 1:]:
                    bx, by, bw, bh = rects[n2]
                    if ax < bx + bw + 8 and bx < ax + aw + 8 and ay < by + bh + 8 and by < ay + ah + 8:
                        raise ValueError(f"UV layout: {n1} and {n2} are closer than 8 px")

    def tile_of(self, name: str) -> str:
        return "wrap" if name in self.rects["wrap"] else "steel"

    def rect(self, name: str):
        if name.startswith("land_"):
            return self.rects["steel"]["head_top"]          # the lands are unfolded onto the top island
        return self.rects[self.tile_of(name)][name]

    def lettering(self) -> dict:
        """The lettering band's UV rectangle: UV0 as stored (tile u 1..2), the same in the wrap maps' own 0..1 and in
        their pixels, and in Unreal's convention (V flipped by the FBX importer, with the image).

        3.10.1: the band is a rectangle INSIDE the wrap's own straight unroll (x -90..-18 on the +Z face, +-BAND_ARC/2
        of arc), not a separate island - the same straight, square-texel mapping, with no island seam round it."""
        wx, wy, _ww, _wh = self.rects["wrap"]["wrap"]
        dw = self.dw
        x = wx + (BAND_X0 - WRAP_X0) * dw
        y = wy + (math.pi - self.band_half) * WRAP_R * dw
        w = (BAND_X1 - BAND_X0) * dw
        h = 2.0 * self.band_half * WRAP_R * dw
        Wp = self.Wp
        u0, v0, u1, v1 = x / Wp, y / Wp, (x + w) / Wp, (y + h) / Wp
        return {
            "uv0_blender": {"u_min": round(1.0 + u0, 8), "u_max": round(1.0 + u1, 8), "v_min": round(v0, 8),
                            "v_max": round(v1, 8)},
            "wrap_texture_0_1_blender": {"u_min": round(u0, 8), "u_max": round(u1, 8), "v_min": round(v0, 8),
                                         "v_max": round(v1, 8)},
            "uv0_unreal": {"u_min": round(1.0 + u0, 8), "u_max": round(1.0 + u1, 8), "v_min": round(1.0 - v1, 8),
                           "v_max": round(1.0 - v0, 8)},
            "wrap_texture_pixels_png_top_left": {"x_min": round(x, 3), "x_max": round(x + w, 3),
                                                 "row_min": round(Wp - (y + h), 3), "row_max": round(Wp - y, 3),
                                                 "map_px": int(Wp)},
            "island_px": [round(w, 3), round(h, 3)], "island_px_per_mm": self.dw,
            "on_the_model_mm": {"x_from": BAND_X0, "x_to": BAND_X1, "arc_mm": round(2.0 * self.band_half * WRAP_R, 6),
                                "half_angle_about_plus_z_deg": round(BAND_HALF_DEG, 6), "grip_radius_mm": WRAP_R,
                                "frame": "design mm (X = 0 at the shoulder, +X to the tip, +Z the lettering face)"},
            "orientation": ("U runs from the ring end (x -90) toward the blade (x -18); V toward +Y, seen from +Z. Seen "
                            "from the +Z face with the tip pointing right, the mask's top edge is the band's +Y edge: "
                            "text drawn upright in the image reads upright and left to right"),
        }

    # ------------------------------------------------------------------ per island
    def uv(self, island: int, p: np.ndarray, sgn_y: float, phi=None, theta=None, s=None) -> np.ndarray:
        ds, dw = self.ds, self.dw
        name = ISLAND_NAMES[island]
        tile = self.tile_of(name)
        size = self.S if tile == "steel" else self.Wp
        rx, ry, rw, rh = self.rect(name)
        x, y, z = p[:, 0], p[:, 1], p[:, 2]
        if island == I_TOP:
            u, v = rx + (x - self.head_x0) * ds, ry + (y - self.head_y0) * ds
        elif island == I_BOT:
            u, v = rx + (x - self.head_x0) * ds, ry + (-y - self.head_y0) * ds
        elif island in I_WALL.values():
            # u along the chain; the -y copy runs the other way so no strip is mirrored (u x v = outward normal)
            chain = name.split("_")[1]
            s0 = self.chain_start[chain]
            u = rx + (s - s0) * ds if sgn_y > 0 else rx + rw - (s - s0) * ds
            v = ry + (z + 0.5 * STOCK) * ds
        elif island in I_LAND.values():
            # unfolded from the top facet's outer edge: the land's top edge (z = +land/2) is the top island's outline,
            # its bottom edge lies land/2 - z further out along the outline's outward normal (mitred at the kite corner)
            sg = 1.0 if island == I_LAND[1] else -1.0
            nx, ny = land_normal(x, sg)
            off = np.where(z > 0.0, 0.0, self.land_half - z)           # the top edge: exactly the top island's UVs
            u = rx + (x + nx * off - self.head_x0) * ds
            v = ry + (y + ny * off - self.head_y0) * ds
        elif island == I_WRAP:
            u, v = rx + (x - WRAP_X0) * dw, ry + (phi + math.pi) * WRAP_R * dw
        elif island == I_CAP_F:                        # the +X end: seen from outside (+X), +Y runs to the RIGHT
            dc = self.cap_px_per_mm
            u, v = rx + (y + self.cap_half[0]) * dc, ry + (z + self.cap_half[1]) * dc
        elif island == I_CAP_R:                        # the -X end: seen from outside (-X), +Y runs to the LEFT
            dc = self.cap_px_per_mm
            u, v = rx + (-y + self.cap_half[0]) * dc, ry + (z + self.cap_half[1]) * dc
        elif island == I_RING["top"]:                  # seen from +Z: X right, Y up
            u, v = rx + (x - RING_CX + self.ring_out_r) * ds, ry + (y + self.ring_out_r) * ds
        elif island == I_RING["bottom"]:               # seen from -Z: X right, Y down
            u, v = rx + (x - RING_CX + self.ring_out_r) * ds, ry + (-y + self.ring_out_r) * ds
        elif island == I_RING["out"]:                  # seen from OUTSIDE the ring, +theta runs to the right
            u, v = rx + theta * self.ring_out_r * ds, ry + s * ds
        elif island == I_RING["in"]:                   # seen from the hole, +theta runs to the LEFT: reversed
            u, v = rx + rw - theta * self.ring_in_r * ds, ry + s * ds
        else:
            key = [k for k, val in I_NECK.items() if val == island][0]
            xa = NECK_X2
            if key == "+z":
                u, v = rx + (x - xa) * ds, ry + (y + NECK_HALF[0]) * ds
            elif key == "-z":
                u, v = rx + (x - xa) * ds, ry + (-y + NECK_HALF[0]) * ds
            elif key == "+y":
                u, v = rx + (NECK_X0 - x) * ds, ry + (z + NECK_HALF[1]) * ds
            elif key == "-y":
                u, v = rx + (x - xa) * ds, ry + (z + NECK_HALF[1]) * ds
            elif key in ("pp", "np", "pn", "nn"):
                # across the chamfer by |z| (0 where it meets the side face, its true width where it meets top / bottom)
                ht = np.array([neck_half(float(xx))[1] for xx in x])
                frac = (np.abs(z) - (ht - 0.6)) / 0.6
                # u runs with -x on the +y+z and -y-z chamfers, with +x on the other two: on each one u x v is then the
                # OUTWARD normal (3.10.1: pn and nn were mirrored, and the old comment's handedness was wrong)
                u = rx + (NECK_X0 - x) * ds if key in ("pp", "nn") else rx + (x - xa) * ds
                v = ry + np.clip(frac, 0.0, 1.0) * 0.6 * math.sqrt(2.0) * ds
            else:
                k = 0.25
                if key == "end_f":                     # the +X end: seen from outside, +Y runs to the right
                    u, v = rx + (y + NECK_HALF[0]) * ds * k, ry + (z + NECK_HALF[1]) * ds * k
                else:                                  # the -X end (buried in the ring): +Y to the left
                    u, v = rx + (-y + NECK_HALF[0]) * ds * k, ry + (z + NECK_HALF[1]) * ds * k
        offset = 1.0 if tile == "wrap" else 0.0
        return np.column_stack([offset + u / size, v / size])


def land_normal(x: np.ndarray, sgn: float):
    """Outward plan normal of the blade outline at design x on the +y (sgn 1) or -y (sgn -1) edge, per point, scaled so
    that an offset along it is perpendicular distance on both sides of the kite corner (mitred there)."""
    xs = np.asarray(x, dtype=np.float64)
    out_x, out_y = np.empty(len(xs)), np.empty(len(xs))
    for i, xv in enumerate(xs):
        xv = min(max(float(xv), 0.0), X_TIP)
        if abs(xv - BLADE_MAX_AT) < 1e-4:
            na = np.array([-dh_blade(BLADE_MAX_AT, -1), sgn])
            nb = np.array([-dh_blade(BLADE_MAX_AT, +1), sgn])
            na, nb = na / np.linalg.norm(na), nb / np.linalg.norm(nb)
            m = na + nb
            m = m / np.linalg.norm(m)
            m = m / float(m @ na)
        else:
            m = np.array([-dh_blade(xv), sgn])
            m = m / np.linalg.norm(m)
        out_x[i], out_y[i] = m
    return out_x, out_y


def ring_strip_param(dr: np.ndarray, z: np.ndarray, outer: bool) -> np.ndarray:
    """Arc length (mm) up a ring wall strip, from the flat bottom's edge round the lower quarter round, up the wall and
    round the upper quarter round to the flat top's edge; a LOD-independent function of the section position (a
    square-section LOD's corners land at the rounds' middles)."""
    a, b, rho = RING_A, RING_B, RING_ROUND
    e = np.abs(dr) - (a - rho)                       # outward from the rounds' centres (the same on both walls)
    lower = np.arctan2(np.maximum(e, 0.0), -(z + (b - rho)))
    upper = np.arctan2(z - (b - rho), np.maximum(e, 0.0))
    wall = 0.5 * math.pi * rho + (z + (b - rho))
    s = np.where(z < -(b - rho), rho * np.clip(lower, 0.0, 0.5 * math.pi),
                 np.where(z > b - rho, 0.5 * math.pi * rho + 2.0 * (b - rho) + rho * np.clip(upper, 0.0, 0.5 * math.pi),
                          wall))
    return s


def _unwrap_angle(values: np.ndarray, centre: float) -> np.ndarray:
    """Angles brought within pi of ``centre`` (one branch for every corner of a face)."""
    out = np.where(values - centre > math.pi, values - 2.0 * math.pi, values)
    return np.where(centre - out > math.pi, out + 2.0 * math.pi, out)


def write_uvs(obj, layout: UVLayout, dist: HeadDistances, shift_mm: float, drop_island_attribute: bool = True) -> dict:
    """UV0 of one LOD from the face islands recorded at authoring (every LOD, one function)."""
    mesh = obj.data
    if not mesh.uv_layers:
        mesh.uv_layers.new(name="UVMap")
    npoly, nloop = len(mesh.polygons), len(mesh.loops)
    islands = np.empty(npoly, dtype=np.int64)
    mesh.attributes[ISLAND_ATTR].data.foreach_get("value", islands)
    loop_vert = np.empty(nloop, dtype=np.int64)
    mesh.loops.foreach_get("vertex_index", loop_vert)
    start = np.empty(npoly, dtype=np.int64)
    total = np.empty(npoly, dtype=np.int64)
    mesh.polygons.foreach_get("loop_start", start)
    mesh.polygons.foreach_get("loop_total", total)
    co = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3).astype(np.float64)
    design = np.column_stack([co[:, 0] / MM + shift_mm, co[:, 1] / MM, co[:, 2] / MM])
    uv = np.zeros((nloop, 2), dtype=np.float64)
    counts: Dict[str, int] = {}
    for f in range(npoly):
        loops = np.arange(start[f], start[f] + total[f])
        p = design[loop_vert[loops]]
        island = int(islands[f])
        name = ISLAND_NAMES[island]
        counts[name] = counts.get(name, 0) + 1
        kw = {}
        sgn = 1.0
        if island in I_WALL.values():
            chain = name.split("_")[1]
            sgn = 1.0 if name.endswith("pos_y") else -1.0
            kw["s"] = dist.arc_length(chain, np.column_stack([p[:, 0], np.abs(p[:, 1])]))
        elif island == I_WRAP:
            phi = np.arctan2(p[:, 1], p[:, 2])                            # (-pi, pi], 0 at +Z, seam at -Z
            centre = math.atan2(float(p[:, 1].mean()), float(p[:, 2].mean()))
            kw["phi"] = _unwrap_angle(phi, centre)
        elif island in (I_RING["out"], I_RING["in"]):
            dx, dy = p[:, 0] - RING_CX, p[:, 1]
            theta = np.arctan2(dy, dx) % (2.0 * math.pi)                  # seam at +X (under the rear neck)
            ct = math.atan2(float(dy.mean()), float(dx.mean())) % (2.0 * math.pi)
            kw["theta"] = _unwrap_angle(theta, ct)
            kw["s"] = ring_strip_param(np.hypot(dx, dy) - RING_R, p[:, 2], outer=island == I_RING["out"])
        uv[loops] = layout.uv(island, p, sgn, **kw)
    mesh.uv_layers[0].data.foreach_set("uv", uv.astype(np.float32).ravel())
    if drop_island_attribute:
        mesh.attributes.remove(mesh.attributes[ISLAND_ATTR])
    mesh.update()
    return {"method": ("shuriken_lib.kunai.write_uvs: one analytic function of the face's island (recorded at authoring) "
                       "and its vertex positions, identical on every LOD - no packer, no transfer"),
            "faces_per_island": counts, "uv_range": [round(float(uv[:, 0].min()), 6), round(float(uv[:, 1].min()), 6),
                                                     round(float(uv[:, 0].max()), 6), round(float(uv[:, 1].max()), 6)],
            "island_map_deviation": {"max_px_at_2048": 0.0,
                                     "note": "every LOD's UV0 is the same analytic map of position (no affine fit)"}}


# =========================================================================== hulls


def hull_mesh(co: List[Tuple[float, float, float]]):
    """(vertices, triangles) of the convex hull of ``co`` (metres), by bmesh."""
    bm = bmesh.new()
    verts = [bm.verts.new(p) for p in co]
    bmesh.ops.convex_hull(bm, input=verts)
    for v in [v for v in bm.verts if not v.link_faces]:
        bm.verts.remove(v)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.verts.index_update()
    out_co = np.array([v.co[:] for v in bm.verts], dtype=np.float64)
    faces = [[v.index for v in f.verts] for f in bm.faces]
    volume = bm.calc_volume(signed=False)
    bm.free()
    return out_co, faces, volume


def _hull_object(obj, name: str, co: List[Tuple[float, float, float]]):
    bm = bmesh.new()
    verts = [bm.verts.new(p) for p in co]
    bmesh.ops.convex_hull(bm, input=verts)
    for v in [v for v in bm.verts if not v.link_faces]:
        bm.verts.remove(v)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
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
    return hull, np.array([v.co[:] for v in mesh.vertices], dtype=np.float64), [list(p.vertices) for p in mesh.polygons]


HULL_TANGENTS = (60.0, 95.0, 122.0)       # design x of the blade tangents that circumscribe the plan hull
HULL_LASH_MARGIN = 0.12                   # mm: the grip hull's margin inside the wound-down ends (eased profile)


def head_hull_points(plan: KunaiPlan, dist: HeadDistances, lod0_head_co_mm: np.ndarray) -> List[Tuple[float, float, float]]:
    """Design-mm points whose convex hull is the head's collider.

    3.10.1 (geometry review: the 3.10 hull was not mirror-symmetric, overshot the tip by 0.86 mm and carried 26
    vertices).  The plan hull is now built from SUPPORTING LINES instead of a simplified vertex hull: the blade's base
    edge, a tangent to the leaf at each of HULL_TANGENTS, and the tip plane x = X_TIP.  Consecutive lines meet in the
    hull's plan vertices, which therefore lie OUTSIDE the outline everywhere (worst ~0.13 mm between tangents) and
    never past the point.  Every vertex is emitted as a +-y pair, so the hull is exactly mirror-symmetric; the ridge
    line, the neck's flat stock and the shoulder are added at their own heights."""
    def tangent(at: float):
        return h_blade(at) - dh_blade(at) * at, dh_blade(at)          # y = c + m x

    lines = [(BLADE_BASE_HALF, (BLADE_MAX_HALF - BLADE_BASE_HALF) / BLADE_MAX_AT)]      # the straight base edge
    lines += [tangent(at) for at in HULL_TANGENTS]
    chain = []
    for (c0, m0), (c1, m1) in zip(lines, lines[1:]):
        x = (c1 - c0) / (m0 - m1)
        chain.append((x, c0 + m0 * x))
    c, m = lines[-1]
    chain.append((X_TIP, c + m * X_TIP))                              # the tip plane closes the chain
    pts = []
    for x, y in chain:
        if x < plan.x_plunge + 1.0:
            continue                                      # the base is covered by the neck block below
        for ys in (1.0, -1.0):
            for zs in (1.0, -1.0):
                pts.append((x, ys * y, zs * 0.5 * EDGE_T))
    for x in (REAR_X, BLADE_MAX_AT, 125.0, 132.0, 137.0):             # the ridge line at its own height
        for zs in (1.0, -1.0):
            pts.append((x, 0.0, zs * 0.5 * ridge_blade(min(x, RIDGE_TIP_AT))))
    # the neck block and the shoulder at full stock (the plateau reaches the chamfer's run-out end)
    ct = plan.ctop
    for x, y in ((REAR_X, NECK_HALF_W), (ct[0], ct[1])):
        for ys in (1.0, -1.0):
            for zs in (1.0, -1.0):
                pts.append((x, ys * y, zs * 0.5 * STOCK))
    xp = plan.x_plunge
    for ys in (1.0, -1.0):
        for zs in (1.0, -1.0):
            pts.append((xp + 0.5, ys * (h_blade(xp + 0.5) + 0.05), zs * 1.2))
    return pts


def grip_hull_points() -> List[Tuple[float, float, float]]:
    """Design-mm points whose convex hull is the grip + neck + ring collider: circumscribed octagons round the tape's
    ridge radius where the wound-down ends begin, the rectangle of each wound-down end section, and a circumscribed
    octagon round the ring plan outline at the ring's thickness (3.10.1: the wrap's ends are lashings now, so the
    collider follows them down instead of running a 21 mm collar prism to the very end)."""
    k8 = 1.0 / math.cos(math.pi / 8.0)
    pts = []
    # the full-radius prism runs a quarter of the way into each wound-down end: the eased profile leaves the tape at
    # its ridge radius over the first millimetre or so, which a hull that started narrowing at the taper would cut
    for xs in (WRAP_X1 - 0.75 * TAPER_L, WRAP_X0 + 0.75 * TAPER_L):
        for k in range(8):
            a = math.pi / 8.0 + k * math.pi / 4.0
            pts.append((xs, WRAP_R * k8 * math.cos(a), WRAP_R * k8 * math.sin(a)))
    # the wound-down ends: a rectangle round the tape's ENVELOPE at three stations each (the envelope takes the tape at
    # its ridge radius, so the helix between two stations cannot poke out), with a margin for the eased profile's
    # curvature between them
    for x_end, x_taper in ((WRAP_X1, WRAP_X1 - TAPER_L), (WRAP_X0, WRAP_X0 + TAPER_L)):
        for t, margin in ((0.55, HULL_LASH_MARGIN), (1.0, 0.0)):
            xs = x_taper + (x_end - x_taper) * t
            half_w = wrap_radius(xs, 0.5 * math.pi, envelope=True) + margin
            half_t = wrap_radius(xs, 0.0, envelope=True) + margin
            for ys in (1.0, -1.0):
                for zs in (1.0, -1.0):
                    pts.append((xs, ys * half_w, zs * half_t))
    k8r = 1.0 / math.cos(math.pi / 8.0)
    ring_out = (RING_R + RING_A) * k8r
    for k in range(8):
        a = math.pi / 8.0 + k * math.pi / 4.0
        for z in (RING_B, -RING_B):
            pts.append((RING_CX + ring_out * math.cos(a), ring_out * math.sin(a), z))
    return pts


def author_kunai_hulls(obj, shift_mm: float, plan: KunaiPlan, dist: HeadDistances, ranges: dict):
    """Two convex hulls on LOD0 (study 5): _00 the head (blade + front neck), _01 the grip, the rear neck and the ring.
    Both contain their parts by construction; the build checks every vertex of each part against its hull."""
    mesh_co = np.array([v.co[:] for v in obj.data.vertices], dtype=np.float64)
    design = mesh_co / MM + np.array([shift_mm, 0.0, 0.0])
    h_lo, h_hi = ranges["head"]

    def to_obj(pts):
        return [((x - shift_mm) * MM, y * MM, z * MM) for x, y, z in pts]
    hull0, h0co, h0f = _hull_object(obj, f"UCX_{obj.name}_00", to_obj(head_hull_points(plan, dist, design[h_lo:h_hi])))
    hull1, h1co, h1f = _hull_object(obj, f"UCX_{obj.name}_01", to_obj(grip_hull_points()))
    out0 = hull_outside_distance(h0co, h0f, mesh_co[h_lo:h_hi])
    out1 = hull_outside_distance(h1co, h1f, mesh_co[h_hi:])
    if out0 > HULL_TOLERANCE or out1 > HULL_TOLERANCE:
        raise RuntimeError(f"kunai hulls do not enclose their parts: head {out0 / MM:.5f} mm, grip {out1 / MM:.5f} mm")
    vol = {}
    for key, h in (("UCX_00", hull0), ("UCX_01", hull1)):
        bm = bmesh.new()
        bm.from_mesh(h.data)
        vol[key] = bm.calc_volume(signed=False) / MM ** 3
        bm.free()
    info = {"UCX_00": {"parts": "blade and bare front neck (the head shell, x >= -6.5 mm)",
                       "vertices": len(hull0.data.vertices), "faces": len(hull0.data.polygons),
                       "volume_mm3": round(vol["UCX_00"], 3), "outside_mm": round(out0 / MM, 9)},
            "UCX_01": {"parts": "wrap, rear neck and ring (x <= -6 mm)", "vertices": len(hull1.data.vertices),
                       "faces": len(hull1.data.polygons), "volume_mm3": round(vol["UCX_01"], 3),
                       "outside_mm": round(out1 / MM, 9)}}
    return [hull0, hull1], info


def hull_alternatives(obj, hulls, shift_mm: float) -> dict:
    """One hull, two hulls, three hulls: volumes against the render mesh, and the hull-derived centre of mass (Unreal
    derives the body's centre of mass from its collision shapes at uniform density)."""
    mesh_co = [tuple(v.co) for v in obj.data.vertices]
    _c, _f, one = hull_mesh(mesh_co)
    two = []
    moments = np.zeros(3)
    total = 0.0
    for h in hulls:
        bm = bmesh.new()
        bm.from_mesh(h.data)
        vol = bm.calc_volume(signed=False)
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
        vol6, mom = 0.0, np.zeros(3)
        for f in bm.faces:
            a, b, c = (np.array(v.co[:], dtype=np.float64) for v in f.verts)
            t = float(np.dot(a, np.cross(b, c)))
            vol6 += t
            mom += t * (a + b + c)
        bm.free()
        centroid = mom / (4.0 * vol6)
        two.append({"name": h.name, "volume_mm3": round(vol / MM ** 3, 3),
                    "centroid_mm": [round(float(v) / MM, 4) for v in centroid]})
        moments += vol * centroid
        total += vol
    com = moments / total
    # three hulls: the grip hull split into the wrap (octagon prism) and the ring + rear neck
    k8 = 1.0 / math.cos(math.pi / 8.0)
    wrap_pts = [((xs - shift_mm) * MM, WRAP_R * k8 * math.cos(math.pi / 8 + k * math.pi / 4) * MM,
                 WRAP_R * k8 * math.sin(math.pi / 8 + k * math.pi / 4) * MM) for xs in (WRAP_X1, WRAP_X0)
                for k in range(8)]
    ring_pts = [p for p in grip_hull_points() if p[0] < WRAP_X0 - 1.0]
    ring_pts += [(WRAP_X0, NECK_HALF[0], NECK_HALF[1] * s) for s in (1, -1)] + \
                [(WRAP_X0, -NECK_HALF[0], NECK_HALF[1] * s) for s in (1, -1)]
    _c, _f, v_wrap = hull_mesh(wrap_pts)
    _c, _f, v_ring = hull_mesh([((x - shift_mm) * MM, y * MM, z * MM) for x, y, z in ring_pts])
    bm = evaluated_bm(obj)
    render_volume = bm.calc_volume(signed=True)
    bm.free()
    head = two[0]["volume_mm3"]
    return {
        "render_mesh_volume_mm3": round(render_volume / MM ** 3, 3),
        "note_render_volume": "the LOD0 shells' volumes summed (they interpenetrate where they join, so this counts the "
                              "joins twice: an upper bound of the solid)",
        "one_hull_mm3": round(one / MM ** 3, 3),
        "two_hulls_mm3": round(total / MM ** 3, 3),
        "three_hulls_mm3": round(head + (v_wrap + v_ring) / MM ** 3, 3),
        "one_over_two": round(one / total, 4),
        "two_hulls": two,
        "hull_derived_centre_of_mass_mm": [round(float(v) / MM, 4) for v in com],
        "unreal_com_nudge_cm": [round(-float(com[0]) / MM / 10.0, 4), 0.0, 0.0],
        "com_note": ("Unreal derives the body's centre of mass from the collision shapes at uniform density: the two hulls "
                     "put it at the x above (object frame, origin = the true mass-weighted centre). Set the Body "
                     "Instance's Center Of Mass Offset (COM Nudge) to unreal_com_nudge_cm to move it back onto the "
                     "pivot, and Mass (kg) to the physics override"),
    }


# =========================================================================== mass and centre of mass


def ring_inside(x, y, z, section: str = "round") -> np.ndarray:
    rr = np.hypot(x - RING_CX, y)
    dr = rr - RING_R
    inside = (np.abs(dr) <= RING_A) & (np.abs(z) <= RING_B)
    if section == "round":
        cr, cz = RING_A - RING_ROUND, RING_B - RING_ROUND
        ex, ez = np.maximum(np.abs(dr) - cr, 0.0), np.maximum(np.abs(z) - cz, 0.0)
        inside &= np.hypot(ex, ez) <= RING_ROUND
    return inside


def neck_inside(x, y, z) -> np.ndarray:
    t = np.clip((x - NECK_X0) / (NECK_X2 - NECK_X0), 0.0, 1.0)
    hw = NECK_HALF[0] + (NECK_END_HALF[0] - NECK_HALF[0]) * t
    ht = NECK_HALF[1] + (NECK_END_HALF[1] - NECK_HALF[1]) * t
    return (x <= NECK_X0) & (x >= NECK_X2) & (np.abs(y) <= hw) & (np.abs(z) <= ht)


def overlap_neck_ring(section: str, step: float = 0.04) -> Tuple[float, float]:
    """(volume mm3, centroid x) of the rear neck's end buried in the ring (analytic shapes, a fine grid)."""
    xs = np.arange(NECK_X2, NECK_X2 + 6.0, step) + 0.5 * step
    ys = np.arange(-8.2, 8.2, step) + 0.5 * step
    zs = np.arange(-2.6, 2.6, step) + 0.5 * step
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
    both = neck_inside(X, Y, Z) & ring_inside(X, Y, Z, section)
    vol = float(both.sum()) * step ** 3
    cx = float(X[both].mean()) if both.any() else NECK_X2
    return vol, cx


def kunai_mass(plan: KunaiPlan, lod: KunaiLodSpec, unground: bool = False) -> dict:
    """Steel, wrap and assembled mass and the mass-weighted centre (design mm) from the authored shells of ``lod``."""
    use = unground_lod(lod) if unground else lod
    bm, st, _o, _vs, _fc = build_kunai_bmesh(plan, use, 0.0)
    bm.free()
    problems = hygiene_problems(st)
    if problems:
        raise RuntimeError(f"kunai_mass ({'un-ground' if unground else 'finished'}): " + ", ".join(problems))
    sh = st["shells"]
    head_v, head_x = sh["head"]["volume_mm3"], sh["head"]["centroid_mm"][0]
    neck_v, neck_x = sh["neck"]["volume_mm3"], sh["neck"]["centroid_mm"][0]
    ring_v, ring_x = sh["ring"]["volume_mm3"], sh["ring"]["centroid_mm"][0]
    wrap_v, wrap_x = sh["wrap"]["volume_mm3"], sh["wrap"]["centroid_mm"][0]
    # The hidden tang: the study's 16 x 5 mm tang stock (3.10.1 geometry review: 3.10 used the rear neck's CHAMFERED
    # octagon, 79.28 mm2, which is not what the study's basis counts - the tang under the wrap is plain bar).
    area = 2.0 * NECK_HALF_W * STOCK
    sec = neck_section(NECK_X0, use.neck_chamfer)
    neck_area = 0.5 * abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(sec, sec[1:] + sec[:1])))
    tang_len = REAR_X - NECK_X0
    tang_v, tang_x = area * tang_len, 0.5 * (REAR_X + NECK_X0)
    ov_v, ov_x = overlap_neck_ring(use.ring_section)
    # steel inside the wrap's core: the tang, the head's stub behind the wrap's front cap, the neck before its rear cap
    head_in = (WRAP_X1 - REAR_X) * 2.0 * NECK_HALF_W * STOCK
    neck_in = (NECK_X0 - WRAP_X0) * neck_area
    steel_v = head_v + tang_v + neck_v + ring_v - ov_v
    steel_mx = head_v * head_x + tang_v * tang_x + neck_v * neck_x + ring_v * ring_x - ov_v * ov_x
    # The wooden core fills the grip between the wound-down ends (3.10.1: over the last TAPER_L at each end the tape is
    # wound down onto the tang, where an 18 mm core cannot fit).  Everything else inside the wrap shell is tape: the
    # shell minus the core, minus the steel that runs through the two wound-down ends.
    core_x0, core_x1 = WRAP_X0 + TAPER_L, WRAP_X1 - TAPER_L
    core_full = math.pi * CORE_R ** 2 * (core_x1 - core_x0)
    steel_in_lash = TAPER_L * (area + neck_area)          # the tang through the front end, the rear neck through the rear
    tape_v = wrap_v - core_full - steel_in_lash
    core_v = core_full - area * (core_x1 - core_x0)       # the tang (16 x 5) runs the whole length of the core
    core_x = 0.5 * (core_x0 + core_x1)
    steel_g = steel_v * STEEL_G_CM3 * 1e-3
    tape_g = tape_v * TAPE_G_CM3 * 1e-3
    core_g = core_v * CORE_G_CM3 * 1e-3
    total_g = steel_g + tape_g + core_g
    com = (steel_mx * STEEL_G_CM3 * 1e-3 + tape_g * wrap_x + core_g * core_x) / total_g
    solid_wrap = wrap_v - tang_v - head_in - neck_in
    naive = (steel_mx + solid_wrap * wrap_x) / (steel_v + solid_wrap)
    return {"head_mm3": round(head_v, 3), "tang_hidden_mm3": round(tang_v, 3), "neck_mm3": round(neck_v, 3),
            "ring_mm3": round(ring_v, 3), "neck_in_ring_mm3": round(ov_v, 3), "steel_mm3": round(steel_v, 3),
            "steel_g": round(steel_g, 4), "steel_centroid_x_mm": round(steel_mx / steel_v, 4),
            "wrap_shell_mm3": round(wrap_v, 3), "tape_mm3": round(tape_v, 3), "core_mm3": round(core_v, 3),
            "tape_g": round(tape_g, 4), "core_g": round(core_g, 4), "wrap_g": round(tape_g + core_g, 4),
            "assembled_g": round(total_g, 4), "centre_of_mass_x_mm": round(com, 4),
            "centre_if_uniform_density_x_mm": round(naive, 4),
            "densities_g_cm3": {"steel": STEEL_G_CM3, "core": CORE_G_CM3, "tape": TAPE_G_CM3},
            "tang_note": (f"the tang under the wrap is never visible and is not modelled: the study's 16 x 5 mm bar "
                          f"({area:.3f} mm2) x {tang_len:.1f} mm from the head's rear face (x {REAR_X}) to the rear "
                          f"neck's hidden start (x {NECK_X0}) is counted analytically"),
            "wrap_note": (f"wrap shell volume minus the 18 mm core cylinder between the wound-down ends "
                          f"(x {core_x0:.1f} .. {core_x1:.1f}) and minus the steel that runs through those ends = the "
                          f"tape ({TAPE_G_CM3} g/cm3); the core ({CORE_G_CM3} g/cm3) less the tang inside it")}


# =========================================================================== measurement


def measure_kunai(obj, spec: KunaiSpec, plan: KunaiPlan, lod: KunaiLodSpec, shift_mm: float, masses: dict,
                  unground: dict, ranges: dict) -> dict:
    bm = evaluated_bm(obj)
    try:
        co = np.array([v.co[:] for v in bm.verts], dtype=np.float64)
        min_edge = min(e.calc_length() for e in bm.edges)
        min_area = min(f.calc_area() for f in bm.faces)
        zero_edges = sum(1 for e in bm.edges if e.calc_length() <= DEGENERATE_EDGE)
        zero_faces = sum(1 for f in bm.faces if f.calc_area() <= DEGENERATE_AREA)
        # what Blender's "Origin to Center of Mass (Volume)" would return on THIS mesh: the signed-volume centroid of
        # the whole thing, the interpenetrating shells' joins counted twice (3.10.1: the report used to quote a
        # different uniform-density figure for it)
        vol6, moment = 0.0, np.zeros(3)
        for face in bm.faces:
            pts = [np.array(v.co[:], dtype=np.float64) for v in face.verts]
            for k in range(1, len(pts) - 1):
                tv = float(np.dot(pts[0], np.cross(pts[k], pts[k + 1])))
                vol6 += tv
                moment += tv * (pts[0] + pts[k] + pts[k + 1])
        volume_centroid = float(moment[0] / (4.0 * vol6)) if vol6 else 0.0
    finally:
        bm.free()
    design = np.column_stack([co[:, 0] / MM + shift_mm, co[:, 1] / MM, co[:, 2] / MM])
    x0, x1 = float(design[:, 0].min()), float(design[:, 0].max())
    head = np.zeros(len(design), dtype=bool)
    head[ranges["head"][0]:ranges["head"][1]] = True
    wrap = np.zeros(len(design), dtype=bool)
    wrap[ranges["wrap"][0]:ranges["wrap"][1]] = True
    ring = np.zeros(len(design), dtype=bool)
    ring[ranges["ring"][0]:ranges["ring"][1]] = True
    tip_pts = design[design[:, 0] > X_TIP - 1e-3]          # the chisel edge (float32 storage: 1 um slack)
    tip_edge = float(np.ptp(tip_pts[:, 2])) if len(tip_pts) else None
    centre = 0.5 * (co.min(axis=0) + co.max(axis=0))
    ue_r = float(np.max(np.linalg.norm(co - centre, axis=1)))
    blade = head & (design[:, 0] >= 0.0)
    rr = np.hypot(design[ring, 0] - RING_CX, design[ring, 1])
    grind_width = {k: round(plan.grind_width(x, lod.land if lod.land >= 0 else LAND), 4)
                   for k, x in (("at_plunge", plan.x_plunge), ("at_widest", BLADE_MAX_AT), ("mid_leaf", 90.0),
                                ("near_apex", 130.0))}
    rng = spec.study_mass_range_g
    out = {
        "length_mm": round(x1 - x0, 6), "across_mm": round(x1 - x0, 6),
        "blade_length_mm": round(x1 - 0.0, 6),
        "blade_max_width_mm": round(float(np.ptp(design[blade, 1])), 6),
        "blade_base_width_mm": 2.0 * h_blade(0.0),
        "thickness_mm": round(float(np.ptp(design[head, 2])), 6),
        "grip_diameter_mm": round(2.0 * WRAP_R, 4),
        "grip_over_collars_mm": round(float(np.ptp(design[wrap, 2])), 6),
        "ring_od_mm": round(2.0 * float(rr.max()), 6), "ring_id_mm": round(2.0 * float(rr.min()), 6),
        "ring_stock_mm": round(float(np.ptp(design[ring, 2])), 6),
        "overall_z_mm": round(float(np.ptp(design[:, 2])), 6),
        "overall_y_mm": round(float(np.ptp(design[:, 1])), 6),
        "tip_x_mm": round(x1, 6), "ring_end_x_mm": round(x0, 6),
        "tip_edge_height_mm": round(tip_edge, 6) if tip_edge is not None else None,
        "tip_radius_mm": round(0.5 * tip_edge, 6) if tip_edge is not None else None,
        "grind": {"grind_angle_deg": 35.0, "edge_land_mm": lod.land if lod.land >= 0 else None,
                  "tip_radius_mm": round(0.5 * tip_edge, 6) if tip_edge is not None else None,
                  "tip_edge_height_mm": round(tip_edge, 6) if tip_edge is not None else None,
                  "grind_width_mm": grind_width,
                  "note": ("35 deg per side to the land on both blade edges (knife columns solve the facet against the "
                           "diamond face); past the apex the facets meet in a ridge and the point ends in a vertical "
                           "chisel edge the height of the land")},
        "apex_x_mm": round(plan.x_apex, 4),
        "shoulder": {"x_mm": 0.0, "blade_base_width_mm": 2.0 * h_blade(0.0), "neck_width_mm": 2.0 * NECK_HALF_W,
                     "corner_turn_deg": round(math.degrees(math.atan2(plan.e1[1], plan.e1[0])), 4),
                     "chamfer_mm": CHAMFER, "chamfer_past_corner_mm": 0.4, "runout_mm": RUNOUT,
                     "plunge_station_x_mm": round(plan.x_plunge, 4),
                     "plunge_ridge_x_mm": round(plan.outline(lod).plunge[2][0], 4)},
        "centre_of_mass_mm": [0.0, 0.0, 0.0],
        "pivot_design_x_mm": round(shift_mm, 6),
        "centre_of_volume_x_mm": round(volume_centroid / MM + shift_mm, 4),
        "centre_of_volume_note": ("what Blender's Origin to Center of Mass (VOLUME) returns on this mesh: the signed-"
                                  "volume centroid of the four shells as one solid, their joins counted twice. Not the "
                                  "pivot: it counts the 20 mm grip as steel"),
        "pivot_note": ("the object origin is the MASS-weighted centre (steel 7.85, core 0.70, tape 0.75 g/cm3): design "
                       f"x = {shift_mm:.3f} mm from the shoulder ({abs(shift_mm - WRAP_X1):.3f} mm inside the grip); "
                       "Origin to Center of Mass (Volume) on this mesh would give "
                       f"{volume_centroid / MM + shift_mm:.3f} mm (the grip counted as steel), and the same idea on "
                       f"the analytic shells {masses['centre_if_uniform_density_x_mm']:.3f} mm"),
        "unreal_bounds_sphere_radius_mm": round(ue_r / MM, 6),
        "mass_g": masses["assembled_g"],
        "ground_mass_g": masses["assembled_g"],        # the FINISHED kunai: ground steel + the wrap
        "outline_mass_g": unground["steel_g"],
        "assembled_mass_g": masses["assembled_g"],
        "steel_ground_mass_g": masses["steel_g"],
        "steel_unground_mass_g": unground["steel_g"],
        "wrap_mass_g": masses["wrap_g"],
        "mass_target_g": spec.mass_target_g,
        "mass_error_g": round(unground["steel_g"] - spec.mass_target_g, 4),
        "mass_within_tolerance": abs(unground["steel_g"] - spec.mass_target_g) <= spec.mass_tolerance_g,
        "mass_gate": {"evaluated_on": ("the UN-GROUND steel: the same head authored with no knife grind and no chamfer "
                                       "(1.5 mm edges, square neck edges) + the rear neck without chamfer + the ring "
                                       "with a square 6 x 5 mm section + the hidden tang (the study's basis)"),
                      "outline_mass_g": unground["steel_g"], "target_g": spec.mass_target_g,
                      "tolerance_g": spec.mass_tolerance_g,
                      "passed": abs(unground["steel_g"] - spec.mass_target_g) <= spec.mass_tolerance_g,
                      "target_source": ("KUNAI_STUDY.md 4 arithmetic with the prongs and the fork web removed "
                                        "(WorkFiles/kunai/plain_calc/kunai_plain_mass_check.json: un-ground steel "
                                        "19,493 mm3 = 153.0 g)")},
        "ground_mass_vs_study_range": {"ground_mass_g": masses["assembled_g"],
                                       "study_min_max_g": list(rng) if rng else None,
                                       "study_typical_g": [spec.assembled_target_g, spec.assembled_target_g],
                                       "within_min_max": (rng[0] <= masses["assembled_g"] <= rng[1]) if rng else None,
                                       "note": "the ASSEMBLED mass (ground steel + wrap at its own density), reported"},
        "masses_finished": masses, "masses_unground": unground,
        "density_g_cm3": STEEL_G_CM3,
        "plate_area_mm2": None,
        "volume_mm3": masses["steel_mm3"],
        "outline_volume_mm3": unground["steel_mm3"],
        "min_edge_mm": round(min_edge / MM, 6), "min_face_area_mm2": round(min_area / MM ** 2, 9),
        "zero_length_edges": zero_edges, "zero_area_faces": zero_faces, "coincident_vertices": coincident_pairs(co),
    }
    return out


def kunai_topology_quality(obj) -> dict:
    bm = evaluated_bm(obj)
    try:
        min_angle, under5, tris, aspects = 180.0, 0, 0, []
        for face in bm.faces:
            cos = [v.co.copy() for v in face.verts]
            for k in range(1, len(cos) - 1):
                a, b, c = cos[0], cos[k], cos[k + 1]
                tri = [math.degrees((b - a).angle(c - a, 0.0)), math.degrees((a - b).angle(c - b, 0.0)),
                       math.degrees((a - c).angle(b - c, 0.0))]
                tris += 1
                min_angle = min(min_angle, min(tri))
                under5 += min(tri) < 5.0
            longest = max((cos[k] - cos[(k + 1) % len(cos)]).length for k in range(len(cos)))
            aspects.append(longest ** 2 / max(face.calc_area(), 1e-30))
    finally:
        bm.free()
    return {"faces": len(aspects), "triangles": tris, "min_triangle_angle_deg": round(min_angle, 4),
            "triangles_under_5deg": int(under5), "face_aspect_median": round(float(np.median(aspects)), 3),
            "face_aspect_max": round(float(max(aspects)), 3),
            "note": ("aspect = longest edge^2 / area.  The knife lands (0.15 mm tall, several mm long), the wall strips "
                     "and the wrap caps' fans are long by design; nothing is degenerate (qa_check's 1 um / 1 um2)")}


def mirror_deviation(obj, axis: int, vrange=None) -> float:
    co = np.array([v.co[:] for v in obj.data.vertices], dtype=np.float64)
    if vrange is not None:
        lo, hi = vrange
        co = co[lo:hi]
    flip = np.ones(3)
    flip[axis] = -1.0
    mirrored = co * flip
    worst = 0.0
    for start in range(0, len(co), 256):
        d = np.linalg.norm(mirrored[start:start + 256, None, :] - co[None], axis=-1).min(axis=1)
        worst = max(worst, float(d.max()))
    return round(worst / MM, 9)


def mirrored_uv_area(obj) -> dict:
    """Fraction of the mesh's area whose UV0 winding is OPPOSITE to its outward normal (a mirrored island).

    MikkTSpace handles mirrored charts, so this is a report figure, not a gate; the kunai's own islands are all
    unmirrored from 3.10.1 (the ring's wall strips, the wrap's end caps and two rear-neck chamfers were mirrored in
    3.10, and the code comments' handedness reasoning was wrong)."""
    mesh = obj.data
    mesh.calc_loop_triangles()
    uv = np.empty(len(mesh.loops) * 2, dtype=np.float64)
    mesh.uv_layers[0].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    co = np.empty(len(mesh.vertices) * 3, dtype=np.float64)
    mesh.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    mirrored, total_area, mirrored_area, count = 0, 0.0, 0.0, 0
    for tri in mesh.loop_triangles:
        a, b, c = (co[i] for i in tri.vertices)
        ua, ub, uc = (uv[i] for i in tri.loops)
        area = 0.5 * float(np.linalg.norm(np.cross(b - a, c - a)))
        cross = (ub[0] - ua[0]) * (uc[1] - ua[1]) - (uc[0] - ua[0]) * (ub[1] - ua[1])
        face_n = np.cross(b - a, c - a)
        outward = float(face_n @ np.array(mesh.polygons[tri.polygon_index].normal[:]))
        flip = (cross < 0.0) if outward >= 0.0 else (cross > 0.0)
        total_area += area
        count += 1
        if flip and abs(cross) > 1e-14:
            mirrored += 1
            mirrored_area += area
    return {"triangles": count, "mirrored_triangles": mirrored,
            "mirrored_area_fraction": round(mirrored_area / total_area, 6) if total_area else 0.0}


def _shell_object(obj, vrange, name: str):
    """A temporary object holding only the faces of ``obj`` whose vertices lie in ``vrange`` (UVs kept)."""
    lo, hi = vrange
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    drop = [v for v in bm.verts if not (lo <= v.index < hi)]
    bmesh.ops.delete(bm, geom=drop, context="VERTS")
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    tmp = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(tmp)
    tmp.matrix_world = obj.matrix_world.copy()
    return tmp


# =========================================================================== render info


class KunaiRenderInfo:
    """What the shared gallery rig reads (render.py), with the knife's optional attributes."""

    def __init__(self, shift_mm: float, spec: KunaiSpec) -> None:
        self.n = 2
        self.half_t = WRAP_R * MM                      # the kunai rests on the tape's ridges
        self.x_tip = (X_TIP - shift_mm) * MM
        self.x_butt = (-X_TIP - shift_mm) * MM
        self.r_tip = self.x_tip
        self.hero_yaw_deg = spec.hero_yaw_deg
        self.hero_rig_match = True
        self.lod_strip_axis = "y"
        self.grind_target_back_m = 0.016
        self.top_frame_height = 0.18                   # a 280 mm knife does not fit the pack's 0.13 m frame
        self.top_centre_xy = (0.5 * (self.x_tip + self.x_butt), 0.0)
        self.wrap_mask = True                          # mask BLUE = the cloth wrap: excluded from the steel gates
        self.a = 0.5 * STOCK * MM

    def tip_extents(self):
        return self.x_tip - self.x_butt, 2.0 * 18.0 * MM


# =========================================================================== the hook


class KunaiGeometry(FormGeometry):
    """FormGeometry of a kunai: mirror-symmetric about XZ and XY, four shells, two material slots, analytic UVs on
    every LOD (steel in UV tile u 0..1, the wrap in u 1..2)."""

    kind = "kunai"
    consistency_class = "knife"
    noun = "kunai"
    outline_wording = "un-ground steel (no knife grind, no chamfer, square ring section; 1.5 mm edges) + hidden tang"
    fill_unused_texels = True
    material_slots = ("M_Shuriken_Master", "M_Kunai_Wrap")
    # every material slot's UV0 islands must lie in their own unit tile (pack.build_form's in-square gate, per slot)
    uv_tiles = {SLOT_STEEL: (0.0, 1.0), SLOT_WRAP: (1.0, 2.0)}

    def __init__(self, spec: KunaiSpec) -> None:
        super().__init__(spec)
        self.plan = KunaiPlan(prongs=spec.prongs)
        self.dist = HeadDistances(self.plan)
        self.masses = kunai_mass(self.plan, spec.lods[0])
        self.shift_mm = self.masses["centre_of_mass_x_mm"]
        self.unground = kunai_mass(self.plan, spec.lods[0], unground=True)
        self.ranges: Dict[str, dict] = {}
        self.ranges_by_level: Dict[int, dict] = {}
        self.normals_info: Dict[str, dict] = {}
        self.layout = UVLayout(spec, self.dist)
        self.hull_info = None
        self.hull_choice = None
        self.render = KunaiRenderInfo(self.shift_mm, spec)

    @property
    def order(self) -> int:
        return 2

    def validate(self) -> None:
        self.spec.validate()

    def build_to(self) -> dict:
        return {"form": "plain kunai (single leaf blade, no prongs), study build-to table",
                "pivot_design_x_mm": round(self.shift_mm, 4)}

    def author(self, level: int, name: str, collection):
        obj, stats, lod = author_kunai_lod(self.plan, self.dist, self.spec.lods[level], self.shift_mm, name, collection)
        self.ranges[obj.name] = stats["shell_vertex_ranges"]
        self.ranges_by_level[level] = stats["shell_vertex_ranges"]
        return obj, stats, lod

    def tag(self, obj) -> None:
        from .kunai_wrap import tag_wrap, wrap_material
        s = self.shift_mm
        rust = (((95.0 - s) * MM, 4.5 * MM, 1.0, RUST_R[0]), ((20.0 - s) * MM, -9.0 * MM, -1.0, RUST_R[1]))
        tag_common(obj, points=1, r_tip=(X_TIP - s) * MM, r_hub=NECK_HALF_W * MM,
                   chamfer_w=0.95 * self.plan.grind_width(130.0) * MM,
                   scallop_w=CHAMFER * MM, hole_w=0.0, centre_r=0.0, land=LAND * MM, rust=rust,
                   half_t=0.5 * STOCK * MM, wall_top=CHAMFER * TAN_GRIND * MM)
        obj[CAVITY_MODE_PROP] = 1.0
        obj[RUNOUT_TAPER_PROP] = 1.0
        obj[CLASS_MODE_PROP] = 1.0
        tag_wrap(obj, s)
        mats = obj.data.materials
        if len(mats) < 2:
            mats.append(wrap_material())

    def make_hull(self, lod0, options):
        hulls, info = author_kunai_hulls(lod0, self.shift_mm, self.plan, self.dist, self.ranges[lod0.name])
        self.hull_info = info
        self.hull_choice = hull_alternatives(lod0, hulls, self.shift_mm)
        return hulls, ("kunai: two explicit convex hulls (shuriken_lib.kunai.author_kunai_hulls) - _00 the head (the "
                       "blade's plan hull reduced to circumscribing vertices at the edge thickness, the ridge line at "
                       "its own height, the neck at full stock), _01 the grip + rear neck + ring (circumscribed octagons "
                       "at both wrap ends and a 16-gon round the ring); each contains its part, checked vertex by vertex")

    def make_sockets(self, lod0) -> None:
        s, spec = self.shift_mm, self.spec
        for name, x in (("Grip", spec.grip_x_mm), ("Trail", spec.trail_x_mm), ("Tip", spec.tip_x_mm),
                        ("Ring", spec.ring_x_mm)):
            pipeline.make_socket(lod0, name, ((x - s) * MM, 0.0, 0.0), rotation_euler=(0.0, 0.0, 0.0))

    def density(self, lod_used) -> dict:
        out = {"per_lod": {}}
        for level, lod in enumerate(lod_used):
            out["per_lod"][f"LOD{level}"] = {k: v for k, v in asdict(lod).items() if k not in ("note",)}
        return out

    def wear_range(self):
        return (X_TIP - self.shift_mm) * MM - TIP_WEAR, (X_TIP - self.shift_mm) * MM

    def split_radius(self) -> float:
        return abs(0.0 - self.shift_mm) * MM              # 'hub_and_hole' reads the grip end, 'arms' the blade

    def measure(self, obj, lod_used) -> dict:
        ranges = self.ranges.get(obj.name) or self.ranges_by_level.get(list(self.spec.lods).index(lod_used))
        return measure_kunai(obj, self.spec, self.plan, lod_used, self.shift_mm, self.masses, self.unground, ranges)

    def topology_quality(self, obj) -> dict:
        return kunai_topology_quality(obj)

    def render_outline(self):
        return self.render

    def custom_unwrap(self, obj, island_margin: float):
        out = write_uvs(obj, self.layout, self.dist, self.shift_mm)
        self.normals_info[obj.name] = finish_normals(obj, self.shift_mm)
        out["layout_px"] = {tile: {k: [round(v, 3) for v in r] for k, r in rects.items()}
                            for tile, rects in self.layout.rects.items()}
        out["tiles"] = {"steel": {"uv_u": [0, 1], "map_px": self.spec.steel_px, "px_per_mm": self.spec.steel_px_per_mm},
                        "wrap": {"uv_u": [1, 2], "map_px": self.spec.wrap_px, "px_per_mm": self.spec.wrap_px_per_mm}}
        out["lettering"] = self.layout.lettering()
        out["normals"] = self.normals_info[obj.name]
        return out

    def lod_uv(self, lod0, obj):
        out = write_uvs(obj, self.layout, self.dist, self.shift_mm)
        self.normals_info[obj.name] = finish_normals(obj, self.shift_mm)
        out["normals"] = self.normals_info[obj.name]
        return out

    def _level_of(self, obj) -> int:
        name = obj.name
        return int(name.rsplit("_LOD", 1)[1]) if "_LOD" in name else 0

    def cross_lod_uv(self, lod0, obj, texture_size: int) -> dict:
        """uv.cross_lod_uv run shell against shell (head / wrap / neck / ring) and merged: the worst of each figure,
        with the per-shell breakdown.  The shells interpenetrate where they join (the neck's end is buried in the ring,
        the head's stub in the wrap), so on the whole mesh a coarse LOD's ring face could find the buried neck's surface
        nearer than the ring's own LOD0 surface.  px: the steel shells at the steel map's size, the wrap at the wrap's."""
        from .uv import cross_lod_uv as _xlod
        r0 = self.ranges_by_level[0]
        r1 = self.ranges_by_level[self._level_of(obj)]
        per, made = {}, []
        try:
            for shell in SHELLS:
                a = _shell_object(lod0, r0[shell], f"__xlod0_{shell}")
                b = _shell_object(obj, r1[shell], f"__xlod1_{shell}")
                made += [a, b]
                size = self.spec.wrap_px if shell == "wrap" else self.spec.steel_px
                half_t = 0.5 * STOCK * MM if shell in ("head", "ring") else None
                per[shell] = _xlod(a, b, texture_size=size, half_t=half_t)
        finally:
            for o in made:
                mesh = o.data
                bpy.data.objects.remove(o)
                bpy.data.meshes.remove(mesh)
        out = {"texture_size": {"steel": self.spec.steel_px, "wrap": self.spec.wrap_px}, "per_shell": per,
               "method": "uv.cross_lod_uv per shell (head, wrap, neck, ring), merged by the worst figure; px at each "
                         "shell's own map"}
        for key in ("top_plate", "surface", "surface_plate", "surface_non_plate", "surface_off_lod0"):
            vals = [d.get(key) or {} for d in per.values()]
            merged = {"samples": int(sum(v.get("samples", 0) for v in vals)),
                      "metric": (vals[0].get("metric", "") + " (per shell, worst)") if vals else ""}
            for fig in ("max_px", "p95_px", "median_px"):
                got = [v[fig] for v in vals if fig in v]
                if got:
                    merged[fig] = max(got)
            if key == "top_plate":
                merged["max_uv"] = max((v.get("max_uv", 0.0) for v in vals), default=0.0)
                merged["skipped_no_lod0_plate_under"] = int(sum(v.get("skipped_no_lod0_plate_under", 0) for v in vals))
            out[key] = merged
        return out

    def texture_size(self, default):
        return int(self.spec.steel_px)

    def bake(self, lod0, material, out_dir, options) -> dict:
        from .kunai_wrap import bake_kunai
        return bake_kunai(self, lod0, material, out_dir, options)

    def preview_materials(self, textures: dict) -> dict:
        from .kunai_wrap import wrap_preview_material
        return {SLOT_WRAP: wrap_preview_material(textures)}

    def lod_deviation_headline(self) -> str:
        return "two_sided"

    def bounds_radius(self, lod0) -> float:
        co = np.array([v.co[:] for v in lod0.data.vertices], dtype=np.float64)
        centre = 0.5 * (co.min(axis=0) + co.max(axis=0))
        return float(np.max(np.linalg.norm(co - centre, axis=1)))

    def surface_snapshot(self, obj) -> dict:
        from .measure import surface_snapshot
        snap = surface_snapshot(obj, 2)
        snap.pop("tip_radius_per_arm_mm", None)
        co = np.array([v.co[:] for v in obj.data.vertices], dtype=np.float64)
        snap.update({"x_tip_mm": round(float(co[:, 0].max()) / MM, 6), "x_butt_mm": round(float(co[:, 0].min()) / MM, 6),
                     "span_y_mm": round(float(np.ptp(co[:, 1])) / MM, 6)})
        return snap

    def _steel_range(self, obj):
        ranges = self.ranges.get(obj.name) or self.ranges_by_level.get(self._level_of(obj)) or {}
        return ranges.get("head", (0, 0))[0], ranges.get("ring", (0, 0))[1]

    def symmetry_deviation(self, obj) -> float:
        """The STEEL's y mirror (the head, the rear neck and the ring): exactly 0, both halves authored and negated.

        The tape wrap is a helix and therefore chiral by design (study 5), so it is measured separately in
        symmetry_extra instead of being averaged into the form's figure."""
        head = (self.ranges.get(obj.name) or self.ranges_by_level.get(self._level_of(obj)) or {}).get("head")
        if head is None:
            return mirror_deviation(obj, 1)
        steel = [r for name, r in (self.ranges.get(obj.name) or self.ranges_by_level[self._level_of(obj)]).items()
                 if name != "wrap"]
        return round(max(mirror_deviation(obj, 1, vrange=r) for r in steel), 9)

    def symmetry_method(self) -> str:
        return ("max nearest-neighbour distance after a mirror y -> -y of the STEEL shells' stored vertices (head, rear "
                "neck, ring: the upper half is authored and negated exactly, so 0.0). The tape wrap is a right-handed "
                "HELIX (study 5: the wrap is chiral) and is reported separately in symmetry.wrap_helix; "
                "mirror_max_deviation_mm adds the z mirror")

    def symmetry_extra(self, lod_objects) -> Optional[dict]:
        wrap = {}
        for obj in lod_objects:
            ranges = self.ranges.get(obj.name) or self.ranges_by_level.get(self._level_of(obj)) or {}
            if "wrap" in ranges:
                wrap[obj.name] = {"y": mirror_deviation(obj, 1, vrange=ranges["wrap"]),
                                  "z": mirror_deviation(obj, 2, vrange=ranges["wrap"])}
        return {"group": "the steel is mirror-symmetric about XZ and XY; the tape wrap is a chiral helix",
                "mirror_max_deviation_mm": {obj.name: {"y": mirror_deviation(obj, 1), "z": mirror_deviation(obj, 2)}
                                            for obj in lod_objects},
                "wrap_helix": {"per_lod_mm": wrap,
                               "note": ("the wound tape cannot be mirror-symmetric: one turn advances TAPE_PITCH along "
                                        "the axis, so the mirror is the opposite hand. LOD1 / LOD2 carry no tape "
                                        "relief, so their wrap is a surface of revolution and mirrors exactly")},
                "uv_mirrored_islands": {obj.name: mirrored_uv_area(obj) for obj in lod_objects}}

    def lod_note(self) -> str:
        return ("LODs are authored by the kunai generator at their own counts, not decimated: fewer blade stations, a "
                "10-sided grip with plain collar steps (LOD1) or an 8-sided grip without collars (LOD2), a coarser ring; "
                "LOD2's cutting edges are the edge line (land 0), its neck edges square and its ring section square. "
                "Every LOD keeps the lettering band's mesh lines. Deviation is two-sided.")

    def lod_strategy(self) -> dict:
        return {"method": "parametric: every LOD authored by shuriken_lib.kunai at its own counts",
                "bands": [list(lod.band) for lod in self.spec.lods],
                "naming": "LODn objects are created as <mesh>_LODn; pipeline.make_lod_group renames LOD0 with its "
                          "UCX_/SOCKET_ children, so the hulls are UCX_<mesh>_LOD0_00 / _01"}

    def lod_switching_extra(self, report: dict) -> Optional[dict]:
        from .spec import screen_size_distance_m
        r = report["lod_switching"].get("bounds_radius_mm")
        sizes = list(self.spec.lod_screen_sizes[:len(self.spec.lods)])
        return {"scaled_for_bounding_radius": {
            "reference_radius_mm": 50.0, "form_radius_mm": r,
            "form_radius_definition": "Unreal's bounds sphere about the bounding-box centre: the tip and the ring's far "
                                      "end, ~140 mm each side",
            "scaled_sizes": list(scaled_lod_screen_sizes(r)),
            "switch_distance_m_at_unreal_radius": [None] + [round(screen_size_distance_m(s, r * MM), 4)
                                                            for s in sizes[1:]]}}


__all__ = ["KeyedBuilder", "KunaiGeometry", "KunaiRenderInfo", "UVLayout", "author_kunai_lod", "build_kunai_bmesh",
           "hull_alternatives", "kunai_mass", "measure_kunai", "write_uvs", "ISLAND_ATTR", "ISLAND_NAMES", "SHELLS",
           "SLOT_STEEL", "SLOT_WRAP"]
