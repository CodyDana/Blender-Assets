"""Kunai generator (library 3.10): SM_Kunai, the pack's first knife, and its FormGeometry hook.

The fifth generator family (radial star, square plate, bar, outline plate, knife), plugged in through the non-radial
Form hook as ``Form(geometry=KunaiGeometry(SPEC))``.  kunai_spec has the frame, the numbers and the analytic head
(columns along the outline, the diamond stations, the plunges, the plateau polygon); this module authors it.

Construction, every LOD (one mesh object; four closed shells that interpenetrate where they join):

    head   the steel head, authored as its upper half (y >= 0) and mirrored in y, top face authored and mirrored in z:
           an edge band along the outline (column pairs: the top facet from the wall top to the inner line, its
           z-mirror, the wall), the three diamond blades as structured strips (grind line -> ridge per station), one
           planar plunge triangle per blade side, and the flat plateau triangulated once per LOD by Blender's
           constrained Delaunay (mathutils.geometry.delaunay_2d_cdt) with a few Steiner points.  The run-out
           intervals (knife -> chamfer, twisted) are authored as explicit triangles.
    wrap   a 20 / 10-sided cylinder with collars (doubled tape turns at both ends), capped at both ends; the grip's
           +Z lettering band is bounded by mesh lines (rings at X = -90 / -18, vertex lines at +-36 deg) on every LOD
    neck   the bare tang between the wrap and the ring, an octagon (chamfered 16 x 5 mm bar) tapering to 8 x 4 mm,
           its ends buried in the wrap and in the ring
    ring   a torus with an elliptical 6 x 5 mm section (ID 20, OD 32 mm)

Every vertex goes through a 1 nm position-keyed factory (``KeyedBuilder``, one per shell), so a duplicate vertex
cannot exist and the two halves weld on the axis by key; a face loop drops repeated corners (a collapsed quad becomes
a triangle), so the land-0 walls of LOD2 and the tips need no special case.  No bmesh.ops.bevel anywhere.

UVs (library 3.10 hook ``lod_uv``): every LOD's UV0 is written by ONE analytic function of the face's island (recorded
at authoring) and its vertex positions, so all LODs share one texture layout exactly: planar projections for the
head's top and bottom (u, v = x, +-y), arc-length strips for its walls, the unrolled cylinder for the wrap, its own
straight island for the lettering band, the unrolled torus for the ring.  The maps are 4096 x 2048 (steel 13.5 px/mm,
the pack's density band; wrap 10 px/mm; lettering band 15 px/mm).
"""
from __future__ import annotations

import math
from dataclasses import asdict, replace
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
from .kunai_spec import (BAND_HALF_DEG, BAND_X0, BAND_X1, CHAMFER, COLLAR_BEVEL, COLLAR_L, COLLAR_R, CORE_G_CM3,
                         CORE_R, EDGE_T, FILLET_R, LAND, NECK_CHAMFER, NECK_END_HALF, NECK_HALF, NECK_X0, NECK_X2,
                         PRONG_L, REAR_HALF, REAR_X, RING_A, RING_B, RING_CX, RING_R, STEEL_G_CM3, STOCK, TAN_GRIND,
                         TAPE_G_CM3, WRAP_R, WRAP_X0, WRAP_X1, X_TIP, KunaiGeometryPlan, KunaiLodSpec, KunaiOutline,
                         KunaiSpec, h_blade, unground_lod)
from .material import (CAVITY_ATTR, CAVITY_MODE_PROP, CLASS_ATTR, CLASS_MODE_PROP, COLLAR_ATTR, RUNOUT_ATTR,
                       RUNOUT_TAPER_PROP, RUST_R, TIP_WEAR, TIPDIST_ATTR, WRAP_ATTR, tag_common, tag_wrap)
from .measure import evaluated_bm, mass_figures
from .spec import MM, SNAP, scaled_lod_screen_sizes

ISLAND_ATTR = "kunai_island"           # temporary INT face attribute: the UV island a face belongs to
DIAMOND_HARD_DEG = 1.5                 # inside a diamond face class an edge is hard above this (the kite corner)
SMOOTH_HARD_DEG = 60.0                 # inside any smooth class an edge is hard above this
WRAP_HARD_DEG = 40.0                   # the collar steps (45 deg) are hard, the 10-gon's 36 deg turns smooth
CLASS_FLAT_KNIFE = 1

# island ids
I_TOP, I_BOT = 0, 1
I_WALL = {("front", 1): 2, ("front", -1): 3, ("outer", 1): 4, ("outer", -1): 5, ("rear", 1): 6, ("rear", -1): 7}
I_WRAP, I_LETTER, I_CAP_F, I_CAP_R, I_RING = 8, 9, 10, 11, 12
I_NECK = {"+z": 13, "-z": 14, "+y": 15, "-y": 16, "pp": 17, "np": 18, "pn": 19, "nn": 20, "end_f": 21, "end_r": 22}
ISLAND_NAMES = {I_TOP: "head_top", I_BOT: "head_bottom", I_WRAP: "wrap", I_LETTER: "lettering_band",
                I_CAP_F: "wrap_cap_front", I_CAP_R: "wrap_cap_rear", I_RING: "ring"}
ISLAND_NAMES.update({v: f"wall_{k[0]}_{'pos' if k[1] > 0 else 'neg'}_y" for k, v in I_WALL.items()})
ISLAND_NAMES.update({v: f"neck_{k}" for k, v in I_NECK.items()})

# material classes (FACE float shuriken_class): coat 1, ground facet 0.5, wall 0
M_COAT, M_FACET, M_WALL = 1.0, 0.5, 0.0


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
    runout = {tuple(sorted(pair)) for pair in o.runouts}
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

        # --- edge band
        for i in range(len(cols) - 1):
            a, b = cols[i], cols[i + 1]
            chain = "outer" if a.tag == "ptip" else a.chain
            wall_island = I_WALL[(chain, sgn)]
            if (i, i + 1) in runout:
                ctop, c0 = (a, b) if a.zone == "chamfer" else (b, a)
                for zs, island in ((1, I_TOP), (-1, I_BOT)):
                    cls = ("runout", chain, sgn, zs, i)
                    bld.face(cls, island, M_FACET, W(ctop, zs), W(c0, zs), I(c0, zs))
                    bld.face(cls, island, M_FACET, W(ctop, zs), I(c0, zs), I(ctop, zs))
                bld.face(("wall", chain, sgn), wall_island, M_WALL, W(a, 1), W(a, -1), W(b, -1), W(b, 1))
                continue
            kind = "chamfer" if (a.zone == "chamfer" and b.zone == "chamfer") else "knife"
            mc = M_FACET
            for zs, island in ((1, I_TOP), (-1, I_BOT)):
                bld.face((kind, chain, sgn, zs), island, mc, W(a, zs), W(b, zs), I(b, zs), I(a, zs))
            bld.face(("wall", chain, sgn), wall_island, M_WALL, W(a, 1), W(a, -1), W(b, -1), W(b, 1))

        # --- diamond strips
        for zs, island in ((1, I_TOP), (-1, I_BOT)):
            for st_a, st_b in zip(o.blade, o.blade[1:]):
                if st_a.past_apex:
                    break
                ga, gb = cols[st_a.cols[0]], cols[st_b.cols[0]]
                ra = st_a.ridge
                rb = st_b.ridge if st_b.ridge is not None else (gb.ix, gb.iy, gb.iz)
                bld.face(("diamond", "blade", sgn, zs), island, M_COAT,
                         I(ga, zs), P(ra[0], ra[1], zs * ra[2]), P(rb[0], rb[1], zs * rb[2]), I(gb, zs))
            for st_a, st_b in zip(o.prong, o.prong[1:]):
                if st_a.past_apex:
                    break
                ia, oa = cols[st_a.cols[0]], cols[st_a.cols[1]]
                ib, ob = cols[st_b.cols[0]], cols[st_b.cols[1]]
                ra = st_a.ridge
                rb = st_b.ridge if st_b.ridge is not None else (ib.ix, ib.iy, ib.iz)
                bld.face(("diamond", "prong_in", sgn, zs), island, M_COAT,
                         I(ia, zs), P(ra[0], ra[1], zs * ra[2]), P(rb[0], rb[1], zs * rb[2]), I(ib, zs))
                bld.face(("diamond", "prong_out", sgn, zs), island, M_COAT,
                         P(ra[0], ra[1], zs * ra[2]), I(oa, zs), I(ob, zs), P(rb[0], rb[1], zs * rb[2]))
            # --- plunges: (ridge at stock height, the chamfer line's run-out end, the first grind point)
            for part, i_top, i_c0, ridge in o.plunges:
                ct, c0 = cols[i_top], cols[i_c0]
                bld.face(("plunge", part, sgn, zs), island, M_COAT,
                         P(ridge[0], ridge[1], zs * ridge[2]), I(ct, zs), I(c0, zs))
            # --- plateau
            pts = list(o.plateau) + list(o.steiner)
            zp = zs * 0.5 * STOCK
            idx = [P(x, y, zp) for x, y in pts]
            for t in tris:
                bld.face(("plateau", zs), island, M_COAT, *(idx[k] for k in t))
    return stats


# =========================================================================== wrap, neck, ring


def wrap_rings(lod: KunaiLodSpec) -> List[Tuple[float, float, str]]:
    """(x, r, zone) rings of the wrap profile from the front cap to the rear cap."""
    x1, x0 = WRAP_X1, WRAP_X0
    if lod.collars == "bevel":
        rb, cb = COLLAR_R - COLLAR_BEVEL, COLLAR_BEVEL
        return [(x1, rb, "collar"), (x1 - cb, COLLAR_R, "collar"), (x1 - COLLAR_L + cb, COLLAR_R, "collar"),
                (x1 - COLLAR_L - cb, WRAP_R, "body"), (BAND_X1, WRAP_R, "body"), (BAND_X0, WRAP_R, "body"),
                (x0 + COLLAR_L + cb, WRAP_R, "body"), (x0 + COLLAR_L - cb, COLLAR_R, "collar"),
                (x0 + cb, COLLAR_R, "collar"), (x0, rb, "collar")]
    if lod.collars == "step":
        cb = COLLAR_BEVEL
        return [(x1, COLLAR_R, "collar"), (x1 - COLLAR_L + cb, COLLAR_R, "collar"),
                (x1 - COLLAR_L - cb, WRAP_R, "body"), (BAND_X1, WRAP_R, "body"), (BAND_X0, WRAP_R, "body"),
                (x0 + COLLAR_L + cb, WRAP_R, "body"), (x0 + COLLAR_L - cb, COLLAR_R, "collar"),
                (x0, COLLAR_R, "collar")]
    return [(x1, WRAP_R, "body"), (BAND_X1, WRAP_R, "body"), (BAND_X0, WRAP_R, "body"), (x0, WRAP_R, "body")]


def grip_point(x: float, r: float, psi: float) -> Tuple[float, float, float]:
    """psi from the bottom (-Z) through -Y (psi 90) to the top (+Z, psi 180) and +Y (psi 270)."""
    return x, -r * math.sin(psi), -r * math.cos(psi)


def author_wrap(bld: KeyedBuilder, lod: KunaiLodSpec) -> dict:
    n = lod.grip_sides
    rings = wrap_rings(lod)
    psis = [2.0 * math.pi * k / n for k in range(n)]
    band_lo, band_hi = math.radians(180.0 - BAND_HALF_DEG), math.radians(180.0 + BAND_HALF_DEG)
    grid = [[bld.add(*grip_point(x, r, psi)) for psi in psis] for x, r, _z in rings]
    for j in range(len(rings) - 1):
        (xa, ra, za), (xb, rb, zb) = rings[j], rings[j + 1]
        collar = 1.0 if (za == "collar" or zb == "collar" or abs(ra - rb) > 1e-9) else 0.0
        in_band_x = (BAND_X0 - 1e-9 <= min(xa, xb)) and (max(xa, xb) <= BAND_X1 + 1e-9)
        for k in range(n):
            k1 = (k + 1) % n
            p_lo = psis[k]
            p_hi = psis[k1] if k1 else 2.0 * math.pi
            band = in_band_x and p_lo >= band_lo - 1e-9 and p_hi <= band_hi + 1e-9
            island = I_LETTER if band else I_WRAP
            cls = ("wrap", "collar" if collar and abs(ra - rb) > 1e-9 else "side")
            bld.face(cls, island, M_COAT, grid[j][k], grid[j + 1][k], grid[j + 1][k1], grid[j][k1])
    # caps: a centre vertex fan (the centre sits inside the steel)
    for j, island, xs in ((0, I_CAP_F, rings[0][0]), (len(rings) - 1, I_CAP_R, rings[-1][0])):
        c = bld.add(xs, 0.0, 0.0)
        for k in range(n):
            k1 = (k + 1) % n
            bld.face(("wrap_cap", island), island, M_COAT, c, grid[j][k1], grid[j][k])
    return {"sides": n, "rings": len(rings), "ring_x_mm": [r[0] for r in rings], "ring_r_mm": [r[1] for r in rings]}


def neck_section(x: float, chamfer: float):
    """Octagon (chamfered rectangle) of the neck at design x, CCW seen from +X: [(y, z)]."""
    t = (x - NECK_X0) / (NECK_X2 - NECK_X0)
    t = min(max(t, 0.0), 1.0)
    hw = NECK_HALF[0] + (NECK_END_HALF[0] - NECK_HALF[0]) * t
    ht = NECK_HALF[1] + (NECK_END_HALF[1] - NECK_HALF[1]) * t
    c = chamfer
    if c <= 0.0:
        return [(hw, ht), (-hw, ht), (-hw, -ht), (hw, -ht)], ["+z", "+y", "-z", "-y"][::1]
    pts = [(hw, ht - c), (hw - c, ht), (-(hw - c), ht), (-hw, ht - c), (-hw, -(ht - c)), (-(hw - c), -ht),
           (hw - c, -ht), (hw, -(ht - c))]
    return pts, None


def author_neck(bld: KeyedBuilder, lod: KunaiLodSpec) -> dict:
    xs = [NECK_X0, NECK_X2]
    secs = [neck_section(x, lod.neck_chamfer)[0] for x in xs]
    rows = [[bld.add(x, y, z) for (y, z) in sec] for x, sec in zip(xs, secs)]
    m = len(secs[0])
    if m == 8:
        names = ["pp", "+z", "np", "-y", "nn", "-z", "pn", "+y"]     # side between point k and k + 1
        # point k=0 (hw, ht-c) -> 1 (hw-c, ht): the +y+z chamfer; 1 -> 2: top; 2 -> 3: -y+z chamfer; 3 -> 4: -y side
        names = ["pp", "+z", "np", "-y", "nn", "-z", "pn", "+y"]
    else:
        # (hw, ht) -> (-hw, ht): top; -> (-hw, -ht): -y; -> (hw, -ht): bottom; -> (hw, ht): +y
        names = ["+z", "-y", "-z", "+y"]
    for k in range(m):
        k1 = (k + 1) % m
        name = names[k]
        mc = M_FACET if name in ("pp", "np", "nn", "pn") else (M_WALL if name in ("+y", "-y") else M_COAT)
        bld.face(("neck", name), I_NECK[name], mc, rows[0][k], rows[1][k], rows[1][k1], rows[0][k1])
    # end caps (both buried): fans
    for j, name in ((0, "end_f"), (1, "end_r")):
        ring = rows[j]
        for k in range(1, m - 1):
            bld.face(("neck", name), I_NECK[name], M_WALL, ring[0], ring[k], ring[k + 1])
    return {"section_points": m, "chamfer_mm": lod.neck_chamfer, "x_mm": xs}


def ring_point(theta: float, phi: float) -> Tuple[float, float, float]:
    rr = RING_R + RING_A * math.cos(phi)
    return RING_CX + rr * math.cos(theta), rr * math.sin(theta), RING_B * math.sin(phi)


def author_ring(bld: KeyedBuilder, lod: KunaiLodSpec) -> dict:
    n, m = lod.ring_segments, lod.ring_section
    grid = [[bld.add(*ring_point(2.0 * math.pi * i / n, 2.0 * math.pi * j / m)) for j in range(m)] for i in range(n)]
    for i in range(n):
        i1 = (i + 1) % n
        for j in range(m):
            j1 = (j + 1) % m
            bld.face(("ring",), I_RING, M_COAT, grid[i][j], grid[i1][j], grid[i1][j1], grid[i][j1])
    return {"segments": n, "section": m}


# =========================================================================== one LOD mesh


def _shell_volume_centroid(verts: np.ndarray, faces) -> Tuple[float, np.ndarray]:
    """(volume, centroid) of a closed outward shell by the divergence theorem (float64), fan triangulation."""
    vol6, mom = 0.0, np.zeros(3)
    for f in faces:
        a = verts[f[0]]
        for k in range(1, len(f) - 1):
            b, c = verts[f[k]], verts[f[k + 1]]
            t = float(np.dot(a, np.cross(b, c)))
            vol6 += t
            mom += t * (a + b + c)
    if vol6 == 0.0:
        return 0.0, np.zeros(3)
    return vol6 / 6.0, mom / (4.0 * vol6)


def build_kunai_bmesh(plan: KunaiGeometryPlan, lod: KunaiLodSpec, shift_mm: float, parts=("head", "wrap", "neck",
                                                                                               "ring")):
    """All shells through their own keyed factories, merged into one bmesh with smoothing baked by class."""
    o = plan.outline(lod)
    shells, stats = [], {}
    if "head" in parts:
        b = KeyedBuilder(shift_mm)
        stats["head"] = author_head(b, o)
        shells.append(("head", b))
    if "wrap" in parts:
        b = KeyedBuilder(shift_mm)
        stats["wrap"] = author_wrap(b, lod)
        shells.append(("wrap", b))
    if "neck" in parts:
        b = KeyedBuilder(shift_mm)
        stats["neck"] = author_neck(b, lod)
        shells.append(("neck", b))
    if "ring" in parts:
        b = KeyedBuilder(shift_mm)
        stats["ring"] = author_ring(b, lod)
        shells.append(("ring", b))

    bm = bmesh.new()
    class_layer = bm.faces.layers.int.new(FACE_CLASS_ATTR)
    island_layer = bm.faces.layers.int.new(ISLAND_ATTR)
    mclass_layer = bm.faces.layers.float.new(CLASS_ATTR)
    wrap_layer = bm.faces.layers.float.new(WRAP_ATTR)
    collar_layer = bm.faces.layers.float.new(COLLAR_ATTR)
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
            face[mclass_layer] = mc
            face[wrap_layer] = 1.0 if cls[0] in ("wrap", "wrap_cap") else 0.0
            face[collar_layer] = 1.0 if (cls[0] == "wrap" and cls[1] == "collar") else 0.0
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.normal_update()
    # collar faces flagged by radius (the wrap's collar zone includes the flat collar tops)
    for face in bm.faces:
        cls = face_class[face]
        if cls[0] == "wrap":
            r = max(math.hypot(v.co.y, v.co.z) for v in face.verts)
            if r > (WRAP_R + 0.05) * MM:
                face[collar_layer] = 1.0

    crease = math.radians(KNIFE_CREASE_DEG)
    diamond = math.radians(DIAMOND_HARD_DEG)
    hard_any = math.radians(SMOOTH_HARD_DEG)
    wrap_hard = math.radians(WRAP_HARD_DEG)
    smooth_kinds = {"plateau", "diamond", "knife", "runout", "chamfer", "wall", "wrap", "ring"}
    flat_kinds = {"knife", "runout"}
    counts = {"knife_crease": 0, "diamond_crease": 0, "hard_corner": 0}
    for face in bm.faces:
        face.smooth = True
    for edge in bm.edges:
        linked = edge.link_faces
        smooth = False
        if len(linked) == 2:
            ca, cb = face_class[linked[0]], face_class[linked[1]]
            kind = ca[0]
            same = ca == cb or (kind == "wrap" and cb[0] == "wrap")
            smooth = same and kind in smooth_kinds
            if smooth:
                angle = linked[0].normal.angle(linked[1].normal, 0.0)
                if kind in flat_kinds and angle > crease:
                    smooth = False
                    counts["knife_crease"] += 1
                elif kind == "diamond" and angle > diamond:
                    smooth = False
                    counts["diamond_crease"] += 1
                elif kind == "wrap" and angle > wrap_hard:
                    smooth = False
                    counts["hard_corner"] += 1
                elif kind in ("wrap", "ring"):
                    pass                                  # a curved surface: smooth whatever the chord angle
                elif angle > hard_any:
                    smooth = False
                    counts["hard_corner"] += 1
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
        "diamond_crease_edges": counts["diamond_crease"],
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
    }
    st.update({f"{k}_detail": v for k, v in stats.items()})
    coords = np.array([v.co[:] for v in bm.verts], dtype=np.float64)
    st["coincident_vertices"] = coincident_pairs(coords)
    st["triangles"] = st["tris"] + 2 * st["quads"] + sum(len(f.verts) - 2 for f in bm.faces if len(f.verts) > 4)
    return bm, st, o, vert_shell, face_class


# =========================================================================== analytic distances (material attributes)


class HeadDistances:
    """Reference polylines of the analytic outline (design mm), cached per plan."""

    def __init__(self, plan: KunaiGeometryPlan) -> None:
        ref = plan.reference_chains(step=0.05)
        self.chains = {k: np.array(v, dtype=np.float64) for k, v in ref.items()}
        self.cum = {}
        for k, p in self.chains.items():
            seg = np.linalg.norm(np.diff(p, axis=0), axis=1)
            self.cum[k] = np.concatenate([[0.0], np.cumsum(seg)])
        allp = np.concatenate([self.chains["front"], self.chains["outer"], self.chains["rear"]])
        self.outline = allp
        g = plan
        # non-cutting (chamfer-zone) outline: the crotch run (ctop_b .. ctop_in) and ctop_out .. the rear axis
        front = self.chains["front"]
        d_ctop_b = np.linalg.norm(front - np.array([g.x_ctop_b, h_blade(g.x_ctop_b)]), axis=1)
        i0 = int(np.argmin(d_ctop_b))
        ci = g.prong.edge(g.u_ctop_in, -1)
        i1 = int(np.argmin(np.linalg.norm(front - np.array(ci), axis=1)))
        outer = self.chains["outer"]
        co = g.prong.edge(g.u_ctop_out, +1)
        j0 = int(np.argmin(np.linalg.norm(outer - np.array(co), axis=1)))
        self.chamfer_polys = [front[i0:i1 + 1], np.concatenate([outer[j0:], self.chains["rear"]])]
        ox, oy = g.fillet_centre
        a1 = math.atan2(g.t1[1] - oy, g.t1[0] - ox)
        a2 = math.atan2(g.t2[1] - oy, g.t2[0] - ox)
        while a2 < a1:
            a2 += 2.0 * math.pi
        if a2 - a1 > math.pi:
            a2 -= 2.0 * math.pi
        self.fillet = np.array([(ox + FILLET_R * math.cos(a1 + (a2 - a1) * k / 60),
                                 oy + FILLET_R * math.sin(a1 + (a2 - a1) * k / 60)) for k in range(61)])
        # knife edges from their full-knife start (the plunge station) toward the tip, arc length (mm)
        self.knife = []
        xb = g.x_plunge_b
        blade = [(x, h_blade(x)) for x in np.linspace(xb, X_TIP, 2400)]
        self.knife.append(np.array(blade))
        for side, u0 in ((-1, g.u_plunge), (1, g.u_plunge)):
            self.knife.append(np.array([g.prong.edge(u, side) for u in np.linspace(u0, PRONG_L, 1200)]))
        self.runout_edges = []            # the run-out parts, measured backward (negative)
        self.runout_edges.append(np.array([(x, h_blade(x)) for x in np.linspace(xb, g.x_ctop_b, 120)]))
        self.runout_edges.append(np.array([g.prong.edge(u, -1) for u in np.linspace(g.u_plunge, g.u_ctop_in, 120)]))
        self.runout_edges.append(np.array([g.prong.edge(u, 1) for u in np.linspace(g.u_plunge, g.u_ctop_out, 120)]))
        self.tips = np.array([(X_TIP, 0.0), g.prong.xy(PRONG_L, 0.0)], dtype=np.float64)

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
        """Design-frame plan points (x, |y|) -> the material's distances, metres."""
        q = np.column_stack([xy[:, 0], np.abs(xy[:, 1])])
        edge = self._poly_dist(q, self.outline)
        scallop = np.minimum(*(self._poly_dist(q, poly) for poly in self.chamfer_polys))
        cavity = self._poly_dist(q, self.fillet)
        tipdist = np.minimum(np.linalg.norm(q - self.tips[0], axis=1), np.linalg.norm(q - self.tips[1], axis=1))
        # run-out distance: nearest knife / run-out edge sample -> signed contour distance from the full knife's start
        cand_pts, cand_val = [], []
        for poly in self.knife:
            seg = np.linalg.norm(np.diff(poly, axis=0), axis=1)
            cand_pts.append(poly)
            cand_val.append(np.concatenate([[0.0], np.cumsum(seg)]))
        for poly in self.runout_edges:
            seg = np.linalg.norm(np.diff(poly, axis=0), axis=1)
            cand_pts.append(poly)
            cand_val.append(-np.concatenate([[0.0], np.cumsum(seg)]))
        cp = np.concatenate(cand_pts)
        cv = np.concatenate(cand_val)
        runout = np.empty(len(q))
        for start in range(0, len(q), 128):
            d = np.linalg.norm(q[start:start + 128, None, :] - cp[None], axis=-1)
            k = np.argmin(d, axis=1)
            runout[start:start + 128] = cv[k]
        # the chamfer-zone outline is not a blade: the hooked cross's RUNOUT_NOT_BLADE for points nearer to it
        not_blade = scallop < edge + 1e-9
        runout = np.where(not_blade & (edge < 3.0), -10.0, runout)
        return {"edge": edge * MM, "scallop": scallop * MM, "cavity": cavity * MM, "tipdist": tipdist * MM,
                "runout": runout * MM}


def write_kunai_attributes(mesh, plan: KunaiGeometryPlan, dist: HeadDistances, shift_mm: float,
                           vert_shell: List[str]) -> dict:
    nv = len(mesh.vertices)
    co = np.empty(nv * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3).astype(np.float64)
    xy = np.column_stack([co[:, 0] / MM + shift_mm, co[:, 1] / MM])
    head = np.array([s == "head" for s in vert_shell])
    far = 1.0
    vals = {"edge": np.full(nv, far), "scallop": np.full(nv, far), "cavity": np.full(nv, far),
            "tipdist": np.full(nv, far), "runout": np.full(nv, -0.01)}
    if head.any():
        got = dist.attributes(xy[head])
        for k in vals:
            vals[k][head] = got[k]
    grind = mesh.attributes.get(GRIND_ATTR)
    g = np.empty(nv, dtype=np.float32)
    grind.data.foreach_get("value", g)
    g = np.where(head, g, 1.0).astype(np.float32)
    grind.data.foreach_set("value", g)
    for name, values in ((EDGE_ATTR, vals["edge"]), (HOLE_ATTR, np.full(nv, NO_HOLE_DISTANCE)),
                         (SCALLOP_ATTR, vals["scallop"]), (CAVITY_ATTR, vals["cavity"]),
                         (RUNOUT_ATTR, vals["runout"]), (TIPDIST_ATTR, vals["tipdist"])):
        attr = mesh.attributes.get(name) or mesh.attributes.new(name, "FLOAT", "POINT")
        attr.data.foreach_set("value", np.asarray(values, dtype=np.float32))
    mesh.update()
    return {"head_vertices": int(head.sum()), "other_vertices": int((~head).sum())}


def author_kunai_lod(plan: KunaiGeometryPlan, dist: HeadDistances, lod: KunaiLodSpec, shift_mm: float, name: str,
                     collection):
    bm, stats, o, vert_shell, _fc = build_kunai_bmesh(plan, lod, shift_mm)
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
    stats["attributes"] = write_kunai_attributes(mesh, plan, dist, shift_mm, vert_shell)
    ranges, start = {}, 0
    for shell in ("head", "wrap", "neck", "ring"):
        count = sum(1 for v in vert_shell if v == shell)
        ranges[shell] = (start, start + count)
        start += count
    stats["shell_vertex_ranges"] = ranges
    stats["outline_info"] = {k: (list(v) if isinstance(v, tuple) else v) for k, v in o.info.items()}
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.matrix_world = Matrix.Identity(4)
    return obj, stats, lod


# =========================================================================== UV layout (every LOD, analytic)


class UVLayout:
    """Deterministic island rectangles in pixels (origin at the map's lower-left) and the island functions."""

    GAP = 24.0
    BORDER = 16.0

    def __init__(self, spec: KunaiSpec, dist: HeadDistances) -> None:
        W, H = spec.texture_px
        self.W, self.H = float(W), float(H)
        ds, dw, dl = spec.steel_px_per_mm, spec.wrap_px_per_mm, spec.letter_px_per_mm
        self.ds, self.dw, self.dl = ds, dw, dl
        b, g = self.BORDER, self.GAP
        self.head_x0, self.head_y0 = REAR_X, -50.0
        head_w, head_h = (X_TIP - REAR_X) * ds, 100.0 * ds
        rects = {}
        rects["head_top"] = (b, b, head_w, head_h)
        rects["head_bottom"] = (b + head_w + 2 * b, b, head_w, head_h)
        band_y0 = b + head_h + g
        wrap_len = WRAP_X1 - WRAP_X0
        rects["wrap"] = (b, band_y0, wrap_len * dw, 2.0 * math.pi * WRAP_R * dw)
        x0 = b + wrap_len * dw + g
        self.chain_len = {k: float(dist.cum[k][-1]) for k in dist.cum}
        strip_h = STOCK * ds
        neck_len = NECK_X0 - NECK_X2
        y = band_y0
        rects["wall_front_pos_y"] = (x0, y, self.chain_len["front"] * ds, strip_h)
        y += strip_h + g
        rects["wall_front_neg_y"] = (x0, y, self.chain_len["front"] * ds, strip_h)
        y += strip_h + g
        x = x0
        for key in ("wall_outer_pos_y", "wall_rear_pos_y", "wall_outer_neg_y", "wall_rear_neg_y"):
            chain = key.split("_")[1]
            rects[key] = (x, y, self.chain_len[chain] * ds, strip_h)
            x += self.chain_len[chain] * ds + g
        for key in ("neck_+y", "neck_-y"):
            rects[key] = (x, y, neck_len * ds, strip_h)
            x += neck_len * ds + g
        ch_h = NECK_CHAMFER * math.sqrt(2.0) * ds
        for col in (("neck_pp", "neck_np"), ("neck_pn", "neck_nn")):
            rects[col[0]] = (x, y, neck_len * ds, ch_h)
            rects[col[1]] = (x, y + ch_h + g, neck_len * ds, ch_h)
            x += neck_len * ds + g
        rects["neck_end_f"] = (x, y, 0.25 * 16.0 * ds, 0.25 * STOCK * ds)
        rects["neck_end_r"] = (x, y + 0.25 * STOCK * ds + g, 0.25 * 16.0 * ds, 0.25 * STOCK * ds)
        y += strip_h + g
        self.ring_perimeter = math.pi * (3.0 * (RING_A + RING_B) - math.sqrt((3.0 * RING_A + RING_B)
                                                                              * (RING_A + 3.0 * RING_B)))
        rects["ring"] = (x0, y, 2.0 * math.pi * RING_R * ds, self.ring_perimeter * ds)
        x = x0 + 2.0 * math.pi * RING_R * ds + g
        band_len = BAND_X1 - BAND_X0
        band_arc = math.radians(2.0 * BAND_HALF_DEG) * WRAP_R
        rects["lettering_band"] = (x, y, band_len * dl, band_arc * dl)
        x += band_len * dl + g
        self.cap_px_per_mm = 0.6 * dw
        cap = 2.0 * COLLAR_R * self.cap_px_per_mm
        rects["wrap_cap_front"] = (x, y, cap, cap)
        x += cap + g
        rects["wrap_cap_rear"] = (x, y, cap, cap)
        x += cap + g
        rects["neck_+z"] = (x, y, neck_len * ds, 16.0 * ds)
        x += neck_len * ds + g
        rects["neck_-z"] = (x, y, neck_len * ds, 16.0 * ds)
        self.rects = rects
        for name, (rx, ry, rw, rh) in rects.items():
            if rx < b - 1e-6 or ry < b - 1e-6 or rx + rw > self.W - b + 1e-6 or ry + rh > self.H - b + 1e-6:
                raise ValueError(f"UV layout: {name} {rx:.1f},{ry:.1f} {rw:.1f}x{rh:.1f} leaves the {W}x{H} map")
        names = list(rects)
        for i, a in enumerate(names):
            ax, ay, aw, ah = rects[a]
            for bname in names[i + 1:]:
                bx, by, bw, bh = rects[bname]
                if ax < bx + bw + 8 and bx < ax + aw + 8 and ay < by + bh + 8 and by < ay + ah + 8:
                    raise ValueError(f"UV layout: {a} and {bname} are closer than 8 px")

    def lettering(self) -> dict:
        x, y, w, h = self.rects["lettering_band"]
        W, H = self.W, self.H
        return {"texture": "T_Kunai_BC (and optionally _ORM / _N)", "texture_px": [int(W), int(H)],
                "uv_rect_0_1": {"u_min": round(x / W, 6), "v_min": round(y / H, 6), "u_max": round((x + w) / W, 6),
                                "v_max": round((y + h) / H, 6)},
                "uv_rect_note": "Blender / Unreal UV convention: u right, v up from the texture's bottom edge "
                                "(Unreal flips V on import together with the image, so the same rectangle holds)",
                "pixels_blender_origin_bottom_left": {"x_min": round(x, 3), "y_min": round(y, 3),
                                                      "x_max": round(x + w, 3), "y_max": round(y + h, 3)},
                "pixels_png_origin_top_left": {"x_min": round(x, 3), "x_max": round(x + w, 3),
                                               "row_min": round(H - (y + h), 3), "row_max": round(H - y, 3)},
                "size_px": [round(w, 3), round(h, 3)], "px_per_mm": self.dl,
                "on_the_model_mm": {"x_from": BAND_X0, "x_to": BAND_X1, "arc": round(math.radians(
                    2.0 * BAND_HALF_DEG) * WRAP_R, 4), "angle_about_top_deg": BAND_HALF_DEG,
                    "frame": "design mm (X = 0 at the fork plane, +X to the tip)"}}

    # ------------------------------------------------------------------ per island
    def uv(self, island: int, p: np.ndarray, sgn_y: float, psi: Optional[np.ndarray] = None,
           theta=None, phi=None, s=None) -> np.ndarray:
        W, H = self.W, self.H
        ds, dw, dl = self.ds, self.dw, self.dl
        name = ISLAND_NAMES[island]
        rx, ry, rw, rh = self.rects[name]
        x, y, z = p[:, 0], p[:, 1], p[:, 2]
        if island == I_TOP:
            u, v = rx + (x - self.head_x0) * ds, ry + (y - self.head_y0) * ds
        elif island == I_BOT:
            u, v = rx + (x - self.head_x0) * ds, ry + (-y - self.head_y0) * ds
        elif island in I_WALL.values():
            # u along the chain; the -y copy runs the other way so no strip is mirrored (u x v = outward normal)
            u = rx + s * ds if sgn_y > 0 else rx + rw - s * ds
            v = ry + (z + 0.5 * STOCK) * ds
            if name.startswith("wall_front") or name.startswith("wall_outer") or name.startswith("wall_rear"):
                pass
        elif island == I_WRAP:
            u, v = rx + (x - WRAP_X0) * dw, ry + psi * WRAP_R * dw
        elif island == I_LETTER:
            u = rx + (x - BAND_X0) * dl
            v = ry + (psi - math.radians(180.0 - BAND_HALF_DEG)) * WRAP_R * dl
        elif island == I_CAP_F:
            dc = self.cap_px_per_mm
            u, v = rx + (y + COLLAR_R) * dc, ry + (z + COLLAR_R) * dc
        elif island == I_CAP_R:
            dc = self.cap_px_per_mm
            u, v = rx + (-y + COLLAR_R) * dc, ry + (z + COLLAR_R) * dc
        elif island == I_RING:
            u = rx + theta * RING_R * ds
            v = ry + phi * self.ring_perimeter / (2.0 * math.pi) * ds
        else:
            key = [k for k, val in I_NECK.items() if val == island][0]
            xa = NECK_X2
            if key == "+z":
                u, v = rx + (x - xa) * ds, ry + (y + 8.0) * ds
            elif key == "-z":
                u, v = rx + (x - xa) * ds, ry + (-y + 8.0) * ds
            elif key == "+y":
                u, v = rx + (NECK_X0 - x) * ds, ry + (z + 0.5 * STOCK) * ds
            elif key == "-y":
                u, v = rx + (x - xa) * ds, ry + (z + 0.5 * STOCK) * ds
            elif key in ("pp", "np", "pn", "nn"):
                # across the chamfer: 0 at the side face's edge, 1 at the top / bottom face's edge (its true width)
                tt = np.clip((x - NECK_X0) / (NECK_X2 - NECK_X0), 0.0, 1.0)
                ht = NECK_HALF[1] + (NECK_END_HALF[1] - NECK_HALF[1]) * tt
                frac = (np.abs(z) - (ht - NECK_CHAMFER)) / NECK_CHAMFER
                u = rx + (NECK_X0 - x) * ds
                v = ry + frac * NECK_CHAMFER * math.sqrt(2.0) * ds
            else:
                k = 0.25
                if key == "end_f":
                    u, v = rx + (y + 8.0) * ds * k, ry + (z + 0.5 * STOCK) * ds * k
                else:
                    u, v = rx + (-y + 8.0) * ds * k, ry + (z + 0.5 * STOCK) * ds * k
        return np.column_stack([u / W, v / H])


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
        elif island in (I_WRAP, I_LETTER):
            psi = np.arctan2(-p[:, 1], -p[:, 2]) % (2.0 * math.pi)
            centre = math.atan2(-p[:, 1].mean(), -p[:, 2].mean()) % (2.0 * math.pi)
            psi = np.where(psi - centre > math.pi, psi - 2.0 * math.pi, psi)
            psi = np.where(centre - psi > math.pi, psi + 2.0 * math.pi, psi)
            kw["psi"] = psi
        elif island == I_RING:
            dx, dy = p[:, 0] - RING_CX, p[:, 1]
            theta = np.arctan2(dy, dx) % (2.0 * math.pi)
            rr = np.hypot(dx, dy)
            phi = (np.arctan2(p[:, 2] / RING_B, (rr - RING_R) / RING_A) - math.pi) % (2.0 * math.pi)
            ct = math.atan2(dy.mean(), dx.mean()) % (2.0 * math.pi)
            theta = np.where(theta - ct > math.pi, theta - 2.0 * math.pi, theta)
            theta = np.where(ct - theta > math.pi, theta + 2.0 * math.pi, theta)
            cp = (math.atan2(p[:, 2].mean() / RING_B, (rr.mean() - RING_R) / RING_A) - math.pi) % (2.0 * math.pi)
            phi = np.where(phi - cp > math.pi, phi - 2.0 * math.pi, phi)
            phi = np.where(cp - phi > math.pi, phi + 2.0 * math.pi, phi)
            kw["theta"], kw["phi"] = theta, phi
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


def _simplify_convex(poly: List[Tuple[float, float]], target: int) -> List[Tuple[float, float]]:
    """Reduce a convex CCW polygon to ``target`` vertices by removing the edge whose neighbours' extension adds the
    least area (the result always CONTAINS the input)."""
    pts = [tuple(p) for p in poly]
    while len(pts) > target:
        best, best_i, best_p = None, None, None
        n = len(pts)
        for i in range(n):
            a0, a1 = pts[(i - 1) % n], pts[i]
            b0, b1 = pts[(i + 1) % n], pts[(i + 2) % n]
            da = (a1[0] - a0[0], a1[1] - a0[1])
            db = (b1[0] - b0[0], b1[1] - b0[1])
            den = da[0] * db[1] - da[1] * db[0]
            if abs(den) < 1e-12:
                continue
            t = ((b0[0] - a0[0]) * db[1] - (b0[1] - a0[1]) * db[0]) / den
            if t < 1.0:
                continue                                  # the extensions meet behind: not convex-removable
            q = (a0[0] + t * da[0], a0[1] + t * da[1])
            area = 0.5 * abs((a1[0] - q[0]) * (b0[1] - q[1]) - (b0[0] - q[0]) * (a1[1] - q[1]))
            if best is None or area < best:
                best, best_i, best_p = area, i, q
        if best_i is None:
            break
        n = len(pts)
        i = best_i
        pts[i] = best_p
        del pts[(i + 1) % n]
    return pts


def _convex_hull_2d(points: np.ndarray) -> List[Tuple[float, float]]:
    pts = sorted(set((round(float(x), 9), round(float(y), 9)) for x, y in points))
    if len(pts) < 3:
        return pts

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
    return lower[:-1] + upper[:-1]


def _hull_object(obj, name: str, co: List[Tuple[float, float, float]]):
    bm = bmesh.new()
    verts = [bm.verts.new(p) for p in co]
    bmesh.ops.convex_hull(bm, input=verts)
    for v in [v for v in bm.verts if not v.link_faces]:
        bm.verts.remove(v)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    hull_co = np.array([v.co[:] for v in bm.verts], dtype=np.float64)
    faces = [[v.index for v in f.verts] for f in bm.faces]
    bm.verts.index_update()
    faces = [[v.index for v in f.verts] for f in bm.faces]
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
    return hull, np.array([v.co[:] for v in mesh.vertices], dtype=np.float64), \
        [list(p.vertices) for p in mesh.polygons]


def author_kunai_hulls(obj, shift_mm: float, head_plan_points: np.ndarray, ranges: dict):
    """Two convex hulls on LOD0 (study 5): _00 the head (blade + prongs + fork) as a prism of its simplified plan hull
    at full stock thickness; _01 the grip, neck and ring: the convex hull of circumscribed octagons round the collar
    radius at both wrap ends and a circumscribed octagon round the ring's plan outline at the ring's thickness.  Both
    contain their parts by construction; the build checks every vertex of the parts against them."""
    mesh_co = np.array([v.co[:] for v in obj.data.vertices], dtype=np.float64)
    design_x = mesh_co[:, 0] / MM + shift_mm
    plan = _convex_hull_2d(head_plan_points)
    plan = _simplify_convex(plan, 8)
    t = 0.5 * STOCK
    co0 = [((x - shift_mm) * MM, y * MM, z * t * MM) for x, y in plan for z in (1.0, -1.0)]
    hull0, h0co, h0f = _hull_object(obj, f"UCX_{obj.name}_00", co0)
    k8 = 1.0 / math.cos(math.pi / 8.0)
    co1 = []
    for xs in (WRAP_X1, WRAP_X0):
        for k in range(8):
            a = math.pi / 8.0 + k * math.pi / 4.0
            co1.append(((xs - shift_mm) * MM, COLLAR_R * k8 * math.cos(a) * MM, COLLAR_R * k8 * math.sin(a) * MM))
    ring_out = (RING_R + RING_A) * k8
    for k in range(8):
        a = math.pi / 8.0 + k * math.pi / 4.0
        for z in (RING_B, -RING_B):
            co1.append(((RING_CX + ring_out * math.cos(a) - shift_mm) * MM, ring_out * math.sin(a) * MM, z * MM))
    hull1, h1co, h1f = _hull_object(obj, f"UCX_{obj.name}_01", co1)
    h_lo, h_hi = ranges["head"]
    out0 = hull_outside_distance(h0co, h0f, mesh_co[h_lo:h_hi])
    out1 = hull_outside_distance(h1co, h1f, mesh_co[h_hi:])
    if out0 > HULL_TOLERANCE or out1 > HULL_TOLERANCE:
        raise RuntimeError(f"kunai hulls do not enclose their parts: head {out0 / MM:.4f} mm, grip {out1 / MM:.4f} mm")
    info = {"UCX_00": {"parts": "blade, prongs, fork (x >= -6 mm)", "vertices": len(hull0.data.vertices),
                       "faces": len(hull0.data.polygons), "plan_vertices": len(plan),
                       "outside_mm": round(out0 / MM, 9)},
            "UCX_01": {"parts": "wrap, neck, ring (x <= -5.5 mm)", "vertices": len(hull1.data.vertices),
                       "faces": len(hull1.data.polygons), "outside_mm": round(out1 / MM, 9)}}
    return hull0, hull1, info


# =========================================================================== mass and centre of mass


def neck_inside(x, y, z) -> np.ndarray:
    t = np.clip((x - NECK_X0) / (NECK_X2 - NECK_X0), 0.0, 1.0)
    hw = NECK_HALF[0] + (NECK_END_HALF[0] - NECK_HALF[0]) * t
    ht = NECK_HALF[1] + (NECK_END_HALF[1] - NECK_HALF[1]) * t
    inside = (x <= NECK_X0) & (x >= NECK_X2) & (np.abs(y) <= hw) & (np.abs(z) <= ht)
    return inside


def ring_inside(x, y, z) -> np.ndarray:
    rr = np.hypot(x - RING_CX, y)
    return ((rr - RING_R) / RING_A) ** 2 + (z / RING_B) ** 2 <= 1.0


def overlap_neck_ring(step: float = 0.04) -> Tuple[float, float]:
    """(volume mm3, centroid x) of the neck's end buried in the ring (analytic shapes, a fine grid)."""
    xs = np.arange(NECK_X2, NECK_X2 + 5.0, step) + 0.5 * step
    ys = np.arange(-4.6, 4.6, step) + 0.5 * step
    zs = np.arange(-2.6, 2.6, step) + 0.5 * step
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
    both = neck_inside(X, Y, Z) & ring_inside(X, Y, Z)
    vol = float(both.sum()) * step ** 3
    cx = float(X[both].mean()) if both.any() else NECK_X2
    return vol, cx


def kunai_mass(plan: KunaiGeometryPlan, lod: KunaiLodSpec, unground: bool = False) -> dict:
    """Steel, wrap and assembled mass and the mass-weighted centre (design mm) from the authored shells of ``lod``."""
    use = unground_lod(lod) if unground else lod
    bm, st, _o, _vs, _fc = build_kunai_bmesh(plan, use, 0.0)
    bm.free()
    sh = st["shells"]
    head_v, head_x = sh["head"]["volume_mm3"], sh["head"]["centroid_mm"][0]
    neck_v, neck_x = sh["neck"]["volume_mm3"], sh["neck"]["centroid_mm"][0]
    ring_v, ring_x = sh["ring"]["volume_mm3"], sh["ring"]["centroid_mm"][0]
    wrap_v, wrap_x = sh["wrap"]["volume_mm3"], sh["wrap"]["centroid_mm"][0]
    # the hidden tang: the neck's full section from the head's rear face to the neck's start
    sec = neck_section(NECK_X0, use.neck_chamfer)[0]
    area = 0.5 * abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(sec, sec[1:] + sec[:1])))
    tang_len = REAR_X - NECK_X0
    tang_v, tang_x = area * tang_len, 0.5 * (REAR_X + NECK_X0)
    ov_v, ov_x = overlap_neck_ring()
    # steel inside the wrap (tang, the head's stub behind the wrap's front cap, the neck's start before its rear cap)
    head_in = (WRAP_X1 - REAR_X) * 2.0 * REAR_HALF * STOCK
    neck_in = (NECK_X0 - WRAP_X0) * area
    steel_v = head_v + tang_v + neck_v + ring_v - ov_v
    steel_mx = head_v * head_x + tang_v * tang_x + neck_v * neck_x + ring_v * ring_x - ov_v * ov_x
    length = WRAP_X1 - WRAP_X0
    core_full = math.pi * CORE_R ** 2 * length
    tape_v = wrap_v - core_full
    core_v = core_full - (tang_v + head_in + neck_in)
    core_x = 0.5 * (WRAP_X0 + WRAP_X1)
    steel_g = steel_v * STEEL_G_CM3 * 1e-3
    tape_g = tape_v * TAPE_G_CM3 * 1e-3
    core_g = core_v * CORE_G_CM3 * 1e-3
    total_g = steel_g + tape_g + core_g
    com = (steel_mx * STEEL_G_CM3 * 1e-3 + tape_g * wrap_x + core_g * core_x) / total_g
    naive = (steel_mx + (wrap_v - tang_v - head_in - neck_in) * wrap_x) / (steel_v + wrap_v - tang_v - head_in
                                                                         - neck_in)
    return {"head_mm3": round(head_v, 3), "tang_hidden_mm3": round(tang_v, 3), "neck_mm3": round(neck_v, 3),
            "ring_mm3": round(ring_v, 3), "neck_in_ring_mm3": round(ov_v, 3), "steel_mm3": round(steel_v, 3),
            "steel_g": round(steel_g, 4), "steel_centroid_x_mm": round(steel_mx / steel_v, 4),
            "wrap_shell_mm3": round(wrap_v, 3), "tape_mm3": round(tape_v, 3), "core_mm3": round(core_v, 3),
            "tape_g": round(tape_g, 4), "core_g": round(core_g, 4), "wrap_g": round(tape_g + core_g, 4),
            "assembled_g": round(total_g, 4), "centre_of_mass_x_mm": round(com, 4),
            "centre_if_uniform_density_x_mm": round(naive, 4),
            "densities_g_cm3": {"steel": STEEL_G_CM3, "core": CORE_G_CM3, "tape": TAPE_G_CM3},
            "tang_note": (f"the tang under the wrap is never visible and is not modelled: its section ({area:.3f} mm2, "
                          f"the neck's) x {tang_len:.1f} mm from the head's rear face (x {REAR_X}) to the neck's hidden "
                          f"start (x {NECK_X0}) is counted analytically"),
            "wrap_note": (f"wrap shell volume minus an 18 mm core cylinder = the tape ({TAPE_G_CM3} g/cm3); the core "
                          f"({CORE_G_CM3} g/cm3) less the steel inside it (tang, head stub, neck start)")}


# =========================================================================== measurement


def measure_kunai(obj, spec: KunaiSpec, plan: KunaiGeometryPlan, lod: KunaiLodSpec, shift_mm: float,
                  masses: dict, unground: dict, ranges: dict) -> dict:
    bm = evaluated_bm(obj)
    try:
        co = np.array([v.co[:] for v in bm.verts], dtype=np.float64)
        min_edge = min(e.calc_length() for e in bm.edges)
        min_area = min(f.calc_area() for f in bm.faces)
        zero_edges = sum(1 for e in bm.edges if e.calc_length() <= DEGENERATE_EDGE)
        zero_faces = sum(1 for f in bm.faces if f.calc_area() <= DEGENERATE_AREA)
    finally:
        bm.free()
    design = np.column_stack([co[:, 0] / MM + shift_mm, co[:, 1] / MM, co[:, 2] / MM])
    x0, x1 = float(design[:, 0].min()), float(design[:, 0].max())
    head = np.zeros(len(design), dtype=bool)
    head[ranges["head"][0]:ranges["head"][1]] = True
    tip_pts = design[design[:, 0] > X_TIP - 1e-6]
    tip_edge = float(np.ptp(tip_pts[:, 2])) if len(tip_pts) else None
    centre = 0.5 * (co.min(axis=0) + co.max(axis=0))
    ue_r = float(np.max(np.linalg.norm(co - centre, axis=1)))
    g = plan
    grind_width = {}
    for name, xq in (("blade_at_widest", 35.0), ("blade_mid", 90.0)):
        col, past, s = g.blade_col(xq, 0.5 * LAND)
        grind_width[name] = round(s, 4)
    col, past, s = g.prong_col(30.0, 1, 0.5 * LAND)
    grind_width["prong_mid"] = round(s, 4)
    out = {
        "length_mm": round(x1 - x0, 6), "across_mm": round(x1 - x0, 6),
        "prong_span_mm": round(float(np.ptp(design[:, 1])), 6),
        "thickness_mm": round(float(np.ptp(design[head, 2])), 6),
        "grip_diameter_mm": round(2.0 * WRAP_R, 4), "grip_over_collars_mm": round(2.0 * COLLAR_R, 4),
        "overall_z_mm": round(float(np.ptp(design[:, 2])), 6),
        "blade_length_mm": X_TIP, "blade_max_width_mm": 2.0 * h_blade(35.0),
        "tip_x_mm": round(x1, 6), "ring_end_x_mm": round(x0, 6),
        "tip_edge_height_mm": round(tip_edge, 6) if tip_edge is not None else None,
        "grind": {"grind_angle_deg": 35.0, "edge_land_mm": lod.land if lod.land >= 0 else None,
                  "tip_radius_mm": round(0.5 * tip_edge, 6) if tip_edge is not None else None,
                  "tip_edge_height_mm": round(tip_edge, 6) if tip_edge is not None else None,
                  "grind_width_mm": grind_width,
                  "note": ("35 deg per side to the land on every cutting edge (knife columns solve the facet against "
                           "the diamond face); past each apex the facets meet in a ridge and the point ends in a "
                           "vertical chisel edge the height of the land")},
        "apex": {"blade_x_mm": round(g.x_apex, 4), "prong_u_mm": round(g.u_apex, 4)},
        "plunge": {"blade_x_mm": round(g.x_plunge_b, 4), "prong_u_mm": round(g.u_plunge, 4),
                   "runout_mm": 3.0, "crotch_mm": [round(v, 4) for v in g.crotch],
                   "fillet_centre_mm": [round(v, 4) for v in g.fillet_centre]},
        "centre_of_mass_mm": [round(float(v), 6) for v in (0.0, 0.0, 0.0)],
        "pivot_design_x_mm": round(shift_mm, 6),
        "pivot_note": ("the object origin is the MASS-weighted centre (steel 7.85, core 0.70, tape 0.75 g/cm3): design "
                       f"x = {shift_mm:.3f} mm from the fork plane; Origin to Center of Mass (Volume) on this mesh "
                       f"would give {masses['centre_if_uniform_density_x_mm']:.3f} mm (the grip counted as steel)"),
        "unreal_bounds_sphere_radius_mm": round(ue_r / MM, 6),
        "mass_g": masses["assembled_g"],
        "ground_mass_g": masses["assembled_g"],
        "outline_mass_g": unground["steel_g"],
        "steel_ground_mass_g": masses["steel_g"],
        "steel_unground_mass_g": unground["steel_g"],
        "wrap_mass_g": masses["wrap_g"],
        "assembled_mass_g": masses["assembled_g"],
        "mass_target_g": spec.mass_target_g,
        "mass_error_g": round(unground["steel_g"] - spec.mass_target_g, 4),
        "mass_within_tolerance": abs(unground["steel_g"] - spec.mass_target_g) <= spec.mass_tolerance_g,
        "mass_gate": {"evaluated_on": ("the UN-GROUND steel: the same head authored with no knife grind and no chamfer "
                                       "(1.5 mm edges, square plateau edges) + the neck without chamfer + the ring + "
                                       "the hidden tang"),
                      "outline_mass_g": unground["steel_g"], "target_g": spec.mass_target_g,
                      "tolerance_g": spec.mass_tolerance_g,
                      "passed": abs(unground["steel_g"] - spec.mass_target_g) <= spec.mass_tolerance_g,
                      "target_source": "KUNAI_STUDY.md 4 / notes: un-ground steel 22,530 mm3 = 176.9 g (the gate basis)"},
        "ground_mass_vs_study_range": {"ground_mass_g": masses["assembled_g"],
                                       "study_min_max_g": [187.0, 192.0], "study_typical_g": [190.0, 190.0],
                                       "within_min_max": 187.0 <= masses["assembled_g"] <= 192.0,
                                       "note": "the assembled mass (ground steel + wrap), reported, not gated"},
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
            "note": ("aspect = longest edge^2 / area.  The knife lands (0.15 mm tall, several mm long) and the wall strips "
                     "are long by design; nothing is degenerate (qa_check's 1 um / 1 um2 thresholds)")}


def mirror_deviation(obj, axis: int) -> float:
    co = np.array([v.co[:] for v in obj.data.vertices], dtype=np.float64)
    flip = np.ones(3)
    flip[axis] = -1.0
    mirrored = co * flip
    worst = 0.0
    for start in range(0, len(co), 256):
        d = np.linalg.norm(mirrored[start:start + 256, None, :] - co[None], axis=-1).min(axis=1)
        worst = max(worst, float(d.max()))
    return round(worst / MM, 9)


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
    """What the shared gallery rig reads (render.py), with the kunai's optional attributes."""

    def __init__(self, shift_mm: float, spec: KunaiSpec) -> None:
        self.n = 2
        self.half_t = COLLAR_R * MM                    # the ground sits under the grip's collars
        self.x_tip = (X_TIP - shift_mm) * MM
        self.x_butt = (-X_TIP - shift_mm) * MM
        self.r_tip = self.x_tip
        self.hero_yaw_deg = spec.hero_yaw_deg
        self.hero_rig_match = True
        self.lod_strip_axis = "y"
        self.grind_target_back_m = 0.011
        self.top_frame_height = 0.195                  # 1.5 x the pack frame: a 280 mm knife does not fit 0.13 m
        self.top_centre_xy = (0.5 * (self.x_tip + self.x_butt), 0.0)
        self.wrap_mask = True
        self.a = 0.5 * STOCK * MM

    def tip_extents(self):
        return self.x_tip - self.x_butt, 2.0 * 49.94 * MM


# =========================================================================== the hook


class KunaiGeometry(FormGeometry):
    """FormGeometry of SM_Kunai: mirror-symmetric about XZ and XY, four shells, analytic UVs on every LOD."""

    kind = "kunai"
    consistency_class = "knife"
    noun = "kunai"
    outline_wording = "un-ground steel (no knife grind, no chamfer; 1.5 mm edges) + hidden tang"
    fill_unused_texels = True

    def __init__(self, spec: KunaiSpec) -> None:
        super().__init__(spec)
        self.plan = KunaiGeometryPlan()
        self.dist = HeadDistances(self.plan)
        self.masses = kunai_mass(self.plan, spec.lods[0])
        self.shift_mm = self.masses["centre_of_mass_x_mm"]
        self.ranges: Dict[str, dict] = {}
        self.ranges_by_level: Dict[int, dict] = {}
        self.unground = kunai_mass(self.plan, spec.lods[0], unground=True)
        self.layout = UVLayout(spec, self.dist)
        self.hull_info = None
        self.render = KunaiRenderInfo(self.shift_mm, spec)

    @property
    def order(self) -> int:
        return 2

    def validate(self) -> None:
        self.spec.validate()

    def build_to(self) -> dict:
        return {"form": "three-prong kunai (the user's winged look), study build-to table",
                "pivot_design_x_mm": round(self.shift_mm, 4)}

    def author(self, level: int, name: str, collection):
        obj, stats, lod = author_kunai_lod(self.plan, self.dist, self.spec.lods[level], self.shift_mm, name, collection)
        self.ranges[obj.name] = stats["shell_vertex_ranges"]
        self.ranges_by_level[level] = stats["shell_vertex_ranges"]
        return obj, stats, lod

    def tag(self, obj) -> None:
        s = self.shift_mm
        rust = (((95.0 - s) * MM, 4.5 * MM, 1.0, RUST_R[0]), ((-2.0 - s) * MM, -12.0 * MM, -1.0, RUST_R[1]))
        tag_common(obj, points=3, r_tip=(X_TIP - s) * MM, r_hub=REAR_HALF * MM, chamfer_w=1.0 * MM,
                   scallop_w=CHAMFER * MM, hole_w=0.0, centre_r=0.0, land=LAND * MM, rust=rust,
                   half_t=0.5 * STOCK * MM, wall_top=CHAMFER * TAN_GRIND * MM)
        obj[CAVITY_MODE_PROP] = 1.0
        obj[RUNOUT_TAPER_PROP] = 1.0
        obj[CLASS_MODE_PROP] = 1.0
        tag_wrap(obj, shift_mm=s, band_x=(BAND_X0, BAND_X1), band_half_deg=BAND_HALF_DEG, wrap_r=WRAP_R,
                 grip_x=(WRAP_X0, WRAP_X1))

    def make_hull(self, lod0, options):
        pts = np.array([(c.ex, sgn * c.ey) for c in self.plan.outline(self.spec.lods[0]).cols for sgn in (1, -1)])
        dense = self.dist.outline
        pts = np.concatenate([pts, dense, dense * np.array([1.0, -1.0])])
        h0, h1, info = author_kunai_hulls(lod0, self.shift_mm, pts, self.ranges[lod0.name])
        self.hull_info = info
        self.extra_hull = h1
        return h0, ("kunai: two explicit convex hulls (shuriken_lib.kunai.author_kunai_hulls) - _00 the head prism "
                    "(its plan hull reduced to 8 circumscribing vertices at full 5 mm stock), _01 the grip + neck + "
                    "ring (circumscribed octagons at both wrap ends and round the ring); both contain their parts, "
                    "checked vertex by vertex")

    def make_sockets(self, lod0) -> None:
        s = self.shift_mm
        pipeline.make_socket(lod0, "Grip", ((self.spec.grip_x_mm - s) * MM, 0.0, 0.0), rotation_euler=(0.0, 0.0, 0.0))
        pipeline.make_socket(lod0, "Trail", ((self.spec.trail_x_mm - s) * MM, 0.0, 0.0),
                             rotation_euler=(0.0, 0.0, 0.0))

    def density(self, lod_used) -> dict:
        out = {"per_lod": {}}
        for level, lod in enumerate(lod_used):
            out["per_lod"][f"LOD{level}"] = {k: v for k, v in asdict(lod).items() if k not in ("note",)}
        return out

    def wear_range(self):
        return (X_TIP - self.shift_mm) * MM - TIP_WEAR, (X_TIP - self.shift_mm) * MM

    def split_radius(self) -> float:
        return abs(REAR_X - self.shift_mm) * MM          # 'hub_and_hole' reads the grip end, 'arms' the head

    def measure(self, obj, lod_used) -> dict:
        ranges = self.ranges.get(obj.name) or self.ranges_by_level.get(list(self.spec.lods).index(lod_used))
        return measure_kunai(obj, self.spec, self.plan, lod_used, self.shift_mm, self.masses, self.unground, ranges)

    def topology_quality(self, obj) -> dict:
        return kunai_topology_quality(obj)

    def render_outline(self):
        return self.render

    def custom_unwrap(self, obj, island_margin: float):
        out = write_uvs(obj, self.layout, self.dist, self.shift_mm)
        out["layout_px"] = {k: [round(v, 3) for v in r] for k, r in self.layout.rects.items()}
        out["lettering"] = self.layout.lettering()
        return out

    def lod_uv(self, lod0, obj):
        return write_uvs(obj, self.layout, self.dist, self.shift_mm)

    def _level_of(self, obj) -> int:
        name = obj.name
        return int(name.rsplit("_LOD", 1)[1]) if "_LOD" in name else 0

    def cross_lod_uv(self, lod0, obj, texture_size: int) -> dict:
        """uv.cross_lod_uv run shell against shell (head / wrap / neck / ring) and merged: the worst of each figure,
        with the per-shell breakdown.  The shells interpenetrate where they join (the neck's end is buried in the ring,
        the head's stub in the wrap), so on the whole mesh a coarse LOD's ring face can find the buried neck's surface
        nearer than the ring's own LOD0 surface and compare a ring texel with a neck texel."""
        from .uv import cross_lod_uv as _xlod
        r0 = self.ranges_by_level[0]
        r1 = self.ranges_by_level[self._level_of(obj)]
        per, made = {}, []
        try:
            for shell in ("head", "wrap", "neck", "ring"):
                a = _shell_object(lod0, r0[shell], f"__xlod0_{shell}")
                b = _shell_object(obj, r1[shell], f"__xlod1_{shell}")
                made += [a, b]
                per[shell] = _xlod(a, b, texture_size=texture_size)
        finally:
            for o in made:
                mesh = o.data
                bpy.data.objects.remove(o)
                bpy.data.meshes.remove(mesh)
        out = {"texture_size": texture_size, "per_shell": per,
               "method": "uv.cross_lod_uv per shell (head, wrap, neck, ring), merged by the worst figure"}
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
        return tuple(int(v) for v in self.spec.texture_px)

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

    def symmetry_deviation(self, obj) -> float:
        return mirror_deviation(obj, 1)

    def symmetry_method(self) -> str:
        return ("max nearest-neighbour distance after a mirror y -> -y of the stored vertices (the kunai is achiral: "
                "the upper half is authored and negated exactly, so 0.0); mirror_max_deviation_mm adds the z mirror")

    def symmetry_extra(self, lod_objects) -> Optional[dict]:
        return {"group": "mirror-symmetric about XZ and XY (achiral)",
                "mirror_max_deviation_mm": {obj.name: {"y": mirror_deviation(obj, 1), "z": mirror_deviation(obj, 2)}
                                            for obj in lod_objects}}

    def lod_note(self) -> str:
        return ("LODs are authored by the kunai generator at their own counts, not decimated: fewer blade and prong "
                "stations, a shorter crotch fillet, a 10-sided grip with plain collars (LOD1) or none (LOD2), a coarser "
                "ring; LOD2's cutting edges are the edge line (land 0) and its plateau edges square.  Deviation is "
                "two-sided.")

    def lod_strategy(self) -> dict:
        return {"method": "parametric: every LOD authored by shuriken_lib.kunai at its own counts",
                "bands": [list(lod.band) for lod in self.spec.lods],
                "naming": "LODn objects are created as <mesh>_LODn; pipeline.make_lod_group renames LOD0 with its "
                          "UCX_/SOCKET_ children, so the hulls are UCX_<mesh>_LOD0_00 / _01"}

    def lod_switching_extra(self, report: dict) -> Optional[dict]:
        from .spec import screen_size_distance_m
        r = 0.5 * (X_TIP + X_TIP)
        sizes = list(self.spec.lod_screen_sizes[:len(self.spec.lods)])
        return {"scaled_for_bounding_radius": {
            "reference_radius_mm": 50.0, "form_radius_mm": r,
            "form_radius_definition": "Unreal's bounds sphere about the bounding-box centre: the tip and the ring end, "
                                      "140 mm each side",
            "scaled_sizes": list(scaled_lod_screen_sizes(r)),
            "switch_distance_m_at_unreal_radius": [None] + [round(screen_size_distance_m(s, r * MM), 4)
                                                            for s in sizes[1:]]}}


__all__ = ["KeyedBuilder", "KunaiGeometry", "KunaiRenderInfo", "UVLayout", "author_kunai_lod", "build_kunai_bmesh",
           "kunai_mass", "measure_kunai", "write_uvs", "ISLAND_ATTR", "ISLAND_NAMES"]
