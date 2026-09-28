"""Outline-plate generator (library 3.9): the hooked cross, SM_Shuriken_HookedCross, and its FormGeometry hook.

The fourth generator family (radial star, square plate, bar, outline plate).  It reuses the radial generator's
vertex factory (``geometry.Builder``: 1 nm snapped, wedge-keyed, seams welded by key, trig-free quarter turns, so
every LOD is EXACTLY C4 and a duplicate vertex cannot exist) and authors one wedge (-45..+45 deg, arm 0 on +X)
per quarter turn from ``outline_spec.HookedOutline.columns``:

    edge band     per pair of neighbouring columns: the top facet (wall top -> plate edge / ridge), the bottom
                  facet (its z-mirror, never an XY mirror) and the wall (wall top -> wall bottom); a collapsed
                  quad becomes a triangle (Builder.face), so the tip's roof, the square edges of LOD2 and the land-0
                  walls need no special case
    plate         the plate-edge polygon of the wedge closed through the centre along both seams, triangulated
                  ONCE per LOD by Blender's constrained Delaunay (mathutils.geometry.delaunay_2d_cdt) with
                  structured Steiner points - the arm axis at every arm station, a bend path from the arm into the
                  hook, the middle of the hook strip, graded seam points and a helper off the hook-corner fillet -
                  so the plate is a strip of near-square pairs along each arm and hook instead of a fan of slivers;
                  the triangle count is exact by Euler (n_boundary + 2 n_inner - 2 per face) and checked

NO MIRROR ANYWHERE.  A plate's bottom face is authored with z negated and the winding reversed - the only
reflection in this module is z -> -z, which maps the outline onto itself.  No X or Y coordinate is ever negated
(the Builder's quarter turns are rotations), no Mirror modifier and no negative scale exist in the path, and
``handedness_gate`` checks the result on every build: in the Blender top view the arm along +X must hook toward
+Y and the arm along +Y toward -X (study 2.6).  ``handedness_negative_control`` feeds the gate the same mesh
mirrored (y -> -y, and also mirrored about the 35 deg line, which keeps the tip angles but moves the arms) and
proves it FAILS - so a mirrored outline cannot pass unnoticed.

Smoothing by face class: the inner edge's knife facets (the flat blade grind; the roof facets lie in the same
plane) and its run-out are flat-shaded and gated by geometry.knife_shading (<= 0.5 deg); the back arc's facets are
one smooth class per zone (arm-end chamfer, run-out, blade + roof; hard between zones) and its wall one smooth
class (curved surfaces: reported, like the senban's curved sides); each non-cutting
chamfer chain and wall chain (inner run-out end -> hook fillet -> leading edge -> junction fillet -> next arm's
trailing edge, tangent-continuous) is one smooth class; every convex corner (elbow, tip) and the ridge is hard, and
(3.9.1) so is any edge inside a smooth class whose faces turn by more than SMOOTH_CHAIN_HARD_DEG (LOD2's sharp concave
corners).

The texture sheets (3.9.1, visual review).  Smart UV Project maps the underside's island as seen from below, i.e. as the
mirrored form; ``OutlinePlateGeometry.uv_mirror_underside`` has pack.unwrap mirror it in U before the packer, and
``texture_handedness`` gates every LOD's UV0 (each plate face turns the same way in UV as in plan seen from +Z; each
LOD0 plate island reads as the left-facing form in the PNG as displayed), with the u-mirrored layout as its negative
control.
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

from .geometry import (DEGENERATE_AREA, DEGENERATE_EDGE, FACE_CLASS_ATTR, KNIFE_CREASE_DEG, KNIFE_SHADING_GATE_DEG,
                       NO_HOLE_DISTANCE, Builder, coincident_pairs, hull_outside_distance, hygiene_problems,
                       knife_shading, segment_distance, write_distance_attributes, write_grind_layer)
from .hooks import FormGeometry
from .material import CAVITY_ATTR, CAVITY_MODE_PROP, RUNOUT_ATTR, RUNOUT_TAPER_PROP, RUST_R, TIP_WEAR, tag_common
from .measure import cn_deviation, evaluated_bm, grind_figures, mass_figures
from .outline_spec import SQRT_HALF, HookedCrossSpec, HookedOutline, OutlineLodSpec, Run
from .spec import MM, SNAP, rotate, scaled_lod_screen_sizes

SMOOTH_KINDS = {"plate", "kf", "kr", "af", "cf", "aw", "w"}
FLAT_KINDS = {"kf", "kr"}              # flat knife facets: hard where two faces' normals differ by > KNIFE_CREASE_DEG
CLASS_FLAT_KNIFE = 1                   # FACE_CLASS_ATTR values (temporary, for knife_shading)
CLASS_CURVED_KNIFE = 2
HULL_VERTS_PER_QUARTER = 3             # tip + 2 circumscribing vertices per quarter: 24 hull vertices (study 4: 8-24)
# 3.9.1 (geometry review): an edge inside a smooth class whose two faces turn by more than this is hard - the sharp
# concave corners of LOD2's square walls (85 deg at a junction, 77 deg at a hook corner) were smoothed across and
# bent their corner normals 45 deg; every filleted corner's chord (LOD0 <= 21 deg, LOD1 <= 43 deg) stays smooth
SMOOTH_CHAIN_HARD_DEG = 60.0
PIECE_TANGENT = ("trail", "arc", "inner", "hk", "lead", "j")


# =========================================================================== plate triangulation


def _hook_pairs(runs: List[Run]):
    """(arc column, inner column) pairs across the hook strip, root -> apex (knife columns, not roof)."""
    arc = [c for c in runs[2].columns if not c.roof and c.zone == "knife"]
    inner = list(reversed([c for c in runs[3].columns if not c.roof and c.zone == "knife"]))
    return list(zip(arc, inner))


def plate_plan(o: HookedOutline, lod: OutlineLodSpec, runs: Optional[List[Run]] = None) -> dict:
    """The wedge's plate: boundary polygon (metres, CCW), Steiner points, CDT triangles and the seam flags.

    Boundary: the centre, the lower-seam points, the plate edge (roof columns skipped: the plate has run out
    there), the upper-seam points.  Seam points are (q, -q) / (q, q) from the same floats.  Steiner points (all
    strictly inside): the arm axis at every arm station, ``lod.end_axis_points`` + a bend path from the last
    axis point to the hook root's midpoint, the middle of every inner hook pair whose strip is wider than 1.5 mm,
    and a helper off the hook-corner fillet.  The triangulation must have exactly n_b + 2 n_i - 2 triangles
    (Euler for a triangulated polygon without added vertices); anything else raises.
    """
    runs = runs if runs is not None else o.columns(lod)
    edge = []
    for run in runs:
        for c in run.columns:
            if c.roof:
                continue
            if edge and abs(c.ex - edge[-1][0]) < 1e-12 and abs(c.ey - edge[-1][1]) < 1e-12:
                continue
            edge.append((c.ex, c.ey))
    qe = runs[0].columns[0].seam_qe
    if abs(edge[0][0] - qe) > 1e-15 or abs(edge[-1][0] - runs[-1].columns[-1].seam_qe) > 1e-15:
        raise RuntimeError("plate edge does not start / end on the seams")
    seam_q = sorted(qe - d * SQRT_HALF for d in lod_seam_offsets(lod, qe))
    boundary = [(0.0, 0.0)] + [(q, -q) for q in seam_q] + edge + [(q, q) for q in reversed(seam_q)]
    upper = [False] + [False] * len(seam_q) + [False] * (len(edge) - 1) + [True] + [True] * len(seam_q)
    steiner = []
    trail = runs[1].columns
    n_arm = lod.arm_intervals
    if lod.axis_points:
        steiner += [(c.x, 0.0) for c in trail[1:n_arm + 1]]
    pairs = _hook_pairs(runs)
    mids = [(0.5 * (a.ex + b.ex), 0.5 * (a.ey + b.ey), math.hypot(a.ex - b.ex, a.ey - b.ey)) for a, b in pairs[:-1]]
    if lod.hook_points:
        steiner += [(x, y) for x, y, width in mids if width > 1.5 * MM]
    # bend: a quadratic path from the last axis point to the hook root's midpoint (the arm's medial line turning up
    # into the hook), end_axis_points samples
    if lod.end_axis_points and mids:
        a0 = (trail[n_arm].x, 0.0)
        h0 = (mids[0][0], mids[0][1])
        ctrl = (h0[0], 0.0)
        nb = lod.end_axis_points
        for k in range(1, nb + 1):
            t = k / (nb + 1)
            steiner.append(((1 - t) ** 2 * a0[0] + 2 * (1 - t) * t * ctrl[0] + t * t * h0[0],
                            (1 - t) ** 2 * a0[1] + 2 * (1 - t) * t * ctrl[1] + t * t * h0[1]))
    if lod.hook_fillet_segments:
        hf = o.hook_fillet()
        a1 = hf["a1"] if hf["a1"] < hf["a2"] else hf["a1"] - 2.0 * math.pi
        a_mid = 0.5 * (hf["a2"] + a1)
        r = hf["r"] + o.chamfer_of(lod)[0] + 1.0 * MM
        steiner.append((hf["centre"][0] + r * math.cos(a_mid), hf["centre"][1] + r * math.sin(a_mid)))
    points = boundary + steiner
    scale = 1.0 / MM                       # the CDT runs in millimetres (float32 inside mathutils)
    vin = [Vector((x * scale, y * scale)) for x, y in points]
    result = delaunay_2d_cdt(vin, [], [list(range(len(boundary)))], 1, 1e-6, True)
    vout, faces, orig = result[0], result[2], result[3]
    if len(vout) != len(points):
        raise RuntimeError(f"CDT changed the vertex set ({len(points)} -> {len(vout)}): a Steiner point sits on an "
                           "edge or outside the plate")
    tris = []
    for face in faces:
        idx = [orig[i][0] for i in face]
        (ax, ay), (bx, by), (cx, cy) = (points[i] for i in idx)
        if (bx - ax) * (cy - ay) - (cx - ax) * (by - ay) < 0.0:
            idx = [idx[0], idx[2], idx[1]]
        tris.append(tuple(idx))
    expected = len(boundary) + 2 * len(steiner) - 2
    if len(tris) != expected:
        raise RuntimeError(f"plate triangulation has {len(tris)} triangles, Euler says {expected}")
    return {"boundary": boundary, "steiner": steiner, "points": points, "tris": tris,
            "upper_seam": upper + [False] * len(steiner), "n_boundary": len(boundary), "n_inner": len(steiner)}


def lod_seam_offsets(lod: OutlineLodSpec, qe: float) -> List[float]:
    """Seam Steiner points as distances (m) from the seam's plate-edge point toward the centre: graded (1 mm off the
    junction fillet, then halfway to the centre)."""
    if lod.seam_points <= 0:
        return []
    reach = qe / SQRT_HALF
    out = [min(1.0 * MM, 0.3 * reach)]
    for k in range(1, lod.seam_points):
        out.append(out[-1] + (reach - out[-1]) * 0.5)
    return out


# =========================================================================== authoring


class _TaggedBuilder(Builder):
    """Builder that also records a per-face tag (1 = the knife grind: the grind line's knife side)."""

    def __init__(self, n: int) -> None:
        super().__init__(n)
        self.tags: List[int] = []

    def face(self, face_class, *indices: int, tag: int = 0) -> None:
        before = len(self.faces)
        super().face(face_class, *indices)
        if len(self.faces) > before:
            self.tags.append(tag)


def _interval_zone(a, b) -> str:
    if a.zone == "knife" and b.zone == "knife":
        return "knife"
    if a.zone == "chamfer" and b.zone == "chamfer":
        return "chamfer"
    return "runout"


def outline_wedge(bld: _TaggedBuilder, o: HookedOutline, lod: OutlineLodSpec, runs: List[Run], plan: dict) -> None:
    """One wedge (arm ``bld.turn``): edge band column by column, then the plate top and bottom."""
    turn = bld.turn
    prev = (turn - 1) % 4
    ht = o.half_t

    def verts(c):
        seam = c.seam == 1
        zw = ht - c.d
        ze = ht - c.ez_drop
        return (bld.add(c.x, c.y, zw, seam=seam), bld.add(c.x, c.y, -zw, seam=seam),
                bld.add(c.ex, c.ey, ze, seam=seam), bld.add(c.ex, c.ey, -ze, seam=seam))

    for run in runs:
        piece = run.piece
        cache = [verts(c) for c in run.columns]
        for j in range(len(run.columns) - 1):
            a, b = run.columns[j], run.columns[j + 1]
            (wa, wa_b, ea, ea_b), (wb, wb_b, eb, eb_b) = cache[j], cache[j + 1]
            zone = _interval_zone(a, b)
            knife = int(piece in ("arc", "inner") and zone != "chamfer")
            if piece == "arc":
                # one smooth class per zone of the curved facet (arm-end chamfer / run-out / blade incl. the roof): the
                # run-out bends the facet ~9 deg along the arc, so the zones meet in hard edges; the wall is one
                # cylinder whatever its height and stays one smooth class
                ftop, fbot, wall = ("af", turn, 1, zone), ("af", turn, -1, zone), ("aw", turn)
            elif piece == "inner" and zone == "knife":
                ftop, fbot, wall = ("kf", turn, 1), ("kf", turn, -1), ("w", turn)
            elif piece == "inner" and zone == "runout":
                ftop, fbot, wall = ("kr", turn, 1), ("kr", turn, -1), ("w", turn)
            elif piece in ("inner", "hk", "lead", "jout"):
                ftop, fbot, wall = ("cf", turn, 1), ("cf", turn, -1), ("w", turn)
            else:                                    # jin, trail: the chain that started on the previous arm
                ftop, fbot, wall = ("cf", prev, 1), ("cf", prev, -1), ("w", prev)
            bld.face(ftop, wa, wb, eb, ea, tag=knife)
            bld.face(fbot, ea_b, eb_b, wb_b, wa_b, tag=knife)
            bld.face(wall, wa, wa_b, wb_b, wb)

    pts, upper = plan["points"], plan["upper_seam"]
    top = [bld.add(x, y, ht, seam=up) for (x, y), up in zip(pts, upper)]
    bot = [bld.add(x, y, -ht, seam=up) for (x, y), up in zip(pts, upper)]
    for i, j, k in plan["tris"]:
        bld.face(("plate", 1), top[i], top[j], top[k])
        bld.face(("plate", -1), bot[k], bot[j], bot[i])


def build_outline_bmesh(o: HookedOutline, lod: OutlineLodSpec):
    """All four wedges through one shared vertex factory; smoothing baked by class."""
    runs = o.columns(lod)
    plan = plate_plan(o, lod, runs)
    bld = _TaggedBuilder(4)
    for turn in range(4):
        bld.turn = turn
        outline_wedge(bld, o, lod, runs, plan)

    # 3.9.1: an eased run-out over several intervals is a twisted surface (planar quads, a few degrees apart) that
    # leaves the knife facet and meets the chamfer - one smooth class, reported with the curved facets; a single
    # straight run-out interval stays a flat knife facet as before
    flat_kinds = {"kf"} if (lod.runout_ease and lod.runout_intervals > 1) else FLAT_KINDS
    bm = bmesh.new()
    class_layer = bm.faces.layers.int.new(FACE_CLASS_ATTR)
    made = [bm.verts.new(co) for co in bld.verts]
    bm.verts.ensure_lookup_table()
    face_class, face_tag = {}, {}
    for loop, cls, tag in zip(bld.faces, bld.classes, bld.tags):
        face = bm.faces.new([made[i] for i in loop])
        face_class[face] = cls
        face_tag[face] = tag
        face[class_layer] = (CLASS_FLAT_KNIFE if cls[0] in flat_kinds else
                             CLASS_CURVED_KNIFE if (cls[0] in ("af", "kr") and tag) else 0)
    bm.faces.ensure_lookup_table()
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.normal_update()
    crease = math.radians(KNIFE_CREASE_DEG)
    hard_corner = math.radians(SMOOTH_CHAIN_HARD_DEG)
    creases = corners = 0
    for face in bm.faces:
        face.smooth = True
    for edge in bm.edges:
        linked = edge.link_faces
        smooth = (len(linked) == 2 and face_class[linked[0]] == face_class[linked[1]]
                  and face_class[linked[0]][0] in SMOOTH_KINDS)
        if smooth and face_class[linked[0]][0] in flat_kinds and linked[0].normal.angle(linked[1].normal, 0.0) > crease:
            smooth = False
            creases += 1
        if smooth and linked[0].normal.angle(linked[1].normal, 0.0) > hard_corner:
            smooth = False                       # a sharp corner inside a smooth chain (LOD2's concave corners)
            corners += 1
        edge.smooth = smooth
    grind_segments = write_grind_layer(bm, lambda f: face_class[f][0] == "plate", lambda f: bool(face_tag[f]))

    top = [f for f in bm.faces if face_class[f] == ("plate", 1)]
    bottom = [f for f in bm.faces if face_class[f] == ("plate", -1)]
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
        "folded_plate_faces": sum(1 for f in top if f.normal.z < 0.999) + sum(1 for f in bottom if f.normal.z > -0.999),
        "sharp_edges": sum(1 for e in bm.edges if not e.smooth),
        "knife_crease_edges": creases,
        "hard_corner_edges": corners,
        "knife_faces": sum(1 for f in bm.faces if face_tag[f]),
        "flat_knife_faces": sum(1 for f in bm.faces if face_class[f][0] in flat_kinds),
        "grind_line_segments": grind_segments,
        "plate_triangles_per_face": len(top),
        "plate_boundary_points_per_wedge": plan["n_boundary"],
        "plate_steiner_points_per_wedge": plan["n_inner"],
        "signed_volume_m3": bm.calc_volume(signed=True),
        "min_edge_mm": min(e.calc_length() for e in bm.edges) / MM,
        "min_face_area_mm2": min(f.calc_area() for f in bm.faces) / (MM ** 2),
        "columns_per_wedge": sum(len(r.columns) for r in runs) - (len(runs) - 1),
    }
    coords = np.array([v.co[:] for v in bm.verts], dtype=np.float64)
    stats["coincident_vertices"] = coincident_pairs(coords)
    stats["triangles"] = stats["tris"] + 2 * stats["quads"]
    return bm, stats, runs, plan


def _loop_triangles(loop) -> int:
    """Triangles of a face loop after Builder.face drops repeated corners (0 if it collapses)."""
    uniq = []
    for k in loop:
        if not uniq or uniq[-1] != k:
            uniq.append(k)
    while len(uniq) > 1 and uniq[0] == uniq[-1]:
        uniq.pop()
    return len(uniq) - 2 if len(uniq) >= 3 else 0


def predicted_triangles(o: HookedOutline, lod: OutlineLodSpec) -> int:
    """Triangle count from the columns and the plate plan alone (no bmesh): each band face has (unique corners - 2)
    triangles, the plate 2 (n_b + 2 n_i - 2) per wedge; four wedges."""
    runs = o.columns(lod)
    plan = plate_plan(o, lod, runs)
    ht = o.half_t

    def key(x, y, z):
        return (round(x / SNAP), round(y / SNAP), round(z / SNAP))

    total = 0
    for run in runs:
        for a, b in zip(run.columns, run.columns[1:]):
            wa, wb = key(a.x, a.y, ht - a.d), key(b.x, b.y, ht - b.d)
            ea, eb = key(a.ex, a.ey, ht - a.ez_drop), key(b.ex, b.ey, ht - b.ez_drop)
            wa_b, wb_b = key(a.x, a.y, -(ht - a.d)), key(b.x, b.y, -(ht - b.d))
            total += 2 * _loop_triangles((wa, wb, eb, ea)) + _loop_triangles((wa, wa_b, wb_b, wb))
    total += 2 * (plan["n_boundary"] + 2 * plan["n_inner"] - 2)
    return 4 * total


def author_outline_lod(o: HookedOutline, lod: OutlineLodSpec, name: str, collection):
    """One hooked-cross LOD object.  Nothing is padded.  Returns ``(obj, stats, lod_used)``."""
    bm, stats, runs, plan = build_outline_bmesh(o, lod)
    stats["predicted_triangles"] = predicted_triangles(o, lod)
    problems = hygiene_problems(stats)
    if stats["folded_plate_faces"]:
        problems.append(f"folded_plate_faces={stats['folded_plate_faces']}")
    if stats["triangles"] != stats["predicted_triangles"]:
        problems.append(f"triangles {stats['triangles']} != predicted {stats['predicted_triangles']}")
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
    flat = knife_shading(mesh, {CLASS_FLAT_KNIFE}, drop_attribute=False)
    curved = knife_shading(mesh, {CLASS_CURVED_KNIFE}, drop_attribute=True)
    stats.update(flat)
    stats.update({"curved_facet_shading_max_dev_deg": curved["knife_shading_max_dev_deg"],
                  "curved_facet_max_warp_mm": curved["knife_face_max_warp_mm"],
                  "curved_facets_measured": curved["knife_faces_measured"]})
    if stats["knife_shading_max_dev_deg"] is not None and stats["knife_shading_max_dev_deg"] > KNIFE_SHADING_GATE_DEG:
        raise RuntimeError(f"{name}: a flat knife facet's corner normal is {stats['knife_shading_max_dev_deg']:.3f} deg "
                           f"off its face normal (gate {KNIFE_SHADING_GATE_DEG} deg)")
    co = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", co)
    xy = co.reshape(-1, 3)[:, :2].astype(np.float64)
    edge_d, scallop_d = outline_distances(o, xy)
    write_distance_attributes(mesh, edge_d, np.full(len(xy), NO_HOLE_DISTANCE), scallop_d)
    cav = mesh.attributes.new(CAVITY_ATTR, "FLOAT", "POINT")
    cav.data.foreach_set("value", cavity_distance(o, xy).astype(np.float32))
    run = mesh.attributes.new(RUNOUT_ATTR, "FLOAT", "POINT")
    run.data.foreach_set("value", runout_distance(o, xy).astype(np.float32))
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.matrix_world = Matrix.Identity(4)       # authored at the origin: no transform to apply, never a negative scale
    return obj, stats, lod


# =========================================================================== analytic distances


_DISTANCE_CACHE: Dict[int, tuple] = {}


def _labelled_outline(o: HookedOutline, step: float = 0.01 * MM):
    """The exact outline of the whole plate as segments, each flagged cutting (the hook blade: back arc from the
    shoulder to the tip, inner edge from the tip to the fillet's tangent point, run-outs included) or not."""
    key = id(o)
    if key in _DISTANCE_CACHE:
        return _DISTANCE_CACHE[key]
    rb = o.runout_bounds()
    hf = o.hook_fillet()
    pts, cut, corner = [], [], []
    for name, piece in zip(("jin", "trail", "arc", "inner", "hk", "lead", "jout"), o.pieces()):
        if piece[0] == "line":
            (ax, ay), (bx, by) = piece[1], piece[2]
            n = max(1, int(math.ceil(math.hypot(bx - ax, by - ay) / step)))
            seg = [(ax + (bx - ax) * k / n, ay + (by - ay) * k / n) for k in range(n)]
            is_inner = abs(ax - o.tip[0]) < 1e-12 and abs(ay - o.tip[1]) < 1e-12 and abs(bx - hf["h2"][0]) < 1e-12
            length = math.hypot(bx - ax, by - ay)
            flags = [is_inner and length * k / n <= rb["inner_r1"] + 1e-12 for k in range(n)]
        else:
            (cx, cy), r, a0, a1 = piece[1], piece[2], piece[3], piece[4]
            n = max(1, int(math.ceil(abs(a1 - a0) * r / step)))
            seg, flags = [], []
            is_arc = abs(r - o.R) < 1e-12
            for k in range(n):
                a = a0 + (a1 - a0) * k / n
                seg.append((cx + r * math.cos(a), cy + r * math.sin(a)))
                flags.append(bool(is_arc and a >= rb["phi_b0"] - 1e-12))
        pts += seg
        cut += flags
        corner += [name in ("jin", "hk", "jout")] * len(seg)
    wedge = np.array(pts, dtype=np.float64)
    flags = np.array(cut, dtype=bool)
    corners = np.array(corner, dtype=bool)
    all_pts, all_flags, all_corners = [], [], []
    for k in range(4):
        x, y = wedge[:, 0], wedge[:, 1]
        rot = {0: (x, y), 1: (-y, x), 2: (-x, -y), 3: (y, -x)}[k]
        all_pts.append(np.column_stack(rot))
        all_flags.append(flags)
        all_corners.append(corners)
    p = np.concatenate(all_pts)
    f = np.concatenate(all_flags)
    c = np.concatenate(all_corners)
    # a segment belongs to a concave corner only if it starts AND ends on one (the fillet's own chords)
    c = c & np.roll(c, -1)
    a, b = p, np.roll(p, -1, axis=0)
    out = (a, b, f, c)
    _DISTANCE_CACHE[key] = out
    return out


def outline_distances(o: HookedOutline, xy: np.ndarray):
    """(distance to the outline, distance to the NON-cutting outline) for each XY point (m).

    The second is the material's SCALLOP_ATTR: 0 along the arm edges, the arm end, the fillets (their small chamfer
    and wall read as the scallops' lightly brightened chamfer and walls), growing across the knife grind of the
    hook blade (which reads as the pack's two-finish grind)."""
    a, b, cutting, _corner = _labelled_outline(o)
    edge = segment_distance(xy, a, b, chunk=64)
    keep = ~cutting
    scallop = segment_distance(xy, a[keep], b[keep], chunk=64)
    return edge, scallop


RUNOUT_NOT_BLADE = -0.01                # m: the runout distance of a point whose nearest outline is not a blade edge


def runout_distance(o: HookedOutline, xy: np.ndarray, step: float = 0.02 * MM) -> np.ndarray:
    """The material's RUNOUT_ATTR (3.9.1, taper mode): for each XY point, the contour distance (m) from its nearest outline
    point to where that blade edge's FULL knife grind starts - positive toward the tip, negative into the run-out -
    and RUNOUT_NOT_BLADE where the nearest outline is not a blade edge (the arm edges, the arm end, the fillets).  The
    polished band narrows over the last material.RUNOUT_FEATHER of the full knife and only a thin line runs on along
    the run-out.  C4: every point is turned into arm 0's wedge by exact quarter turns first."""
    rb = o.runout_bounds()
    phi_t = o.arc_angle(o.tip)
    pts, vals = [], []
    for name, piece in zip(PIECES_ORDER, o.pieces()):
        if piece[0] == "line":
            (ax, ay), (bx, by) = piece[1], piece[2]
            length = math.hypot(bx - ax, by - ay)
            n = max(1, int(math.ceil(length / step)))
            inner = name == "inner"
            for k in range(n + 1):
                pts.append((ax + (bx - ax) * k / n, ay + (by - ay) * k / n))
                vals.append(rb["inner_r0"] - length * k / n if inner else RUNOUT_NOT_BLADE)
        else:
            (cx, cy), r, a0, a1 = piece[1], piece[2], piece[3], piece[4]
            n = max(1, int(math.ceil(abs(a1 - a0) * r / step)))
            arc = name == "arc"
            for k in range(n + 1):
                a = a0 + (a1 - a0) * k / n
                pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
                vals.append(min(o.R * (a - rb["phi_b1"]), o.R * (phi_t - rb["phi_b1"])) if arc else RUNOUT_NOT_BLADE)
    pts = np.array(pts, dtype=np.float64)
    vals = np.array(vals, dtype=np.float64)
    x, y = xy[:, 0], xy[:, 1]
    turn = np.floor((np.arctan2(y, x) + 0.25 * math.pi) / (0.5 * math.pi)).astype(np.int64) % 4
    lx = np.where(turn == 0, x, np.where(turn == 1, y, np.where(turn == 2, -x, -y)))
    ly = np.where(turn == 0, y, np.where(turn == 1, -x, np.where(turn == 2, -y, x)))
    local = np.column_stack([lx, ly])
    out = np.empty(len(local))
    for start in range(0, len(local), 256):
        d = np.linalg.norm(local[start:start + 256, None, :] - pts[None], axis=-1)
        out[start:start + 256] = vals[np.argmin(d, axis=1)]
    return out


PIECES_ORDER = ("jin", "trail", "arc", "inner", "hk", "lead", "jout")


def cavity_distance(o: HookedOutline, xy: np.ndarray) -> np.ndarray:
    """Distance (m) to the concave corners (junction and hook-corner fillets): the material's CAVITY_ATTR."""
    a, b, _cutting, corner = _labelled_outline(o)
    return segment_distance(xy, a[corner], b[corner], chunk=64)


# =========================================================================== handedness


def _inside_triangles(points: np.ndarray, tris: np.ndarray) -> np.ndarray:
    """Which 2D points lie inside any of the 2D triangles (tris: (m, 3, 2))."""
    inside = np.zeros(len(points), dtype=bool)
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    for start in range(0, len(points), 256):
        p = points[start:start + 256][:, None, :]
        d1 = (p[..., 0] - b[None, :, 0]) * (a[None, :, 1] - b[None, :, 1]) - (a[None, :, 0] - b[None, :, 0]) * (p[..., 1] - b[None, :, 1])
        d2 = (p[..., 0] - c[None, :, 0]) * (b[None, :, 1] - c[None, :, 1]) - (b[None, :, 0] - c[None, :, 0]) * (p[..., 1] - c[None, :, 1])
        d3 = (p[..., 0] - a[None, :, 0]) * (c[None, :, 1] - a[None, :, 1]) - (c[None, :, 0] - a[None, :, 0]) * (p[..., 1] - a[None, :, 1])
        neg = (d1 < 0) | (d2 < 0) | (d3 < 0)
        pos = (d1 > 0) | (d2 > 0) | (d3 > 0)
        inside[start:start + 256] = np.any(~(neg & pos), axis=1)
    return inside


def top_face_triangles(obj) -> np.ndarray:
    """The +Z (presented) face's flat triangles in plan, (m, 3, 2), from the evaluated mesh."""
    bm = evaluated_bm(obj)
    try:
        zmax = max(v.co.z for v in bm.verts)
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
        tris = [[v.co.xy[:] for v in f.verts] for f in bm.faces
                if f.normal.z > 0.999 and all(abs(v.co.z - zmax) < 1e-9 for v in f.verts)]
    finally:
        bm.free()
    return np.array(tris, dtype=np.float64)


def handedness_from_plan(tris: np.ndarray, verts_xy: np.ndarray, probe_r: float, r_tip: float) -> dict:
    """The study 2.6 gate on a plan view (Blender top view: +Z toward the viewer, X right, Y up).

    1. Arm axes: sample the circle r = ``probe_r`` (inside the arms, short of the hooks) against the presented face's
       triangles; the covered angles form four intervals whose midpoints are the arm axes.
    2. Hook tips: the four vertices farthest from the centre.
    3. Each arm's hook tip is the tip nearest its axis in angle; its signed offset (tip - axis, wrapped to +-180)
       must be POSITIVE (counter-clockwise) and the four offsets equal (C4).
    4. The study's words, literally: the arm along +X hooks toward +Y (its tip has y > 0) and the arm along +Y hooks
       toward -X (its tip has x < 0) - which also requires arms ON the axes.
    The mirrored (right-facing) outline has negative offsets and fails 3 and 4.
    """
    n = 2880
    ang = np.linspace(-math.pi, math.pi, n, endpoint=False)
    probe = np.column_stack([probe_r * np.cos(ang), probe_r * np.sin(ang)])
    covered = _inside_triangles(probe, tris) if len(tris) else np.zeros(n, dtype=bool)
    # covered runs on the circle (wrap-around aware)
    runs = []
    if covered.any() and not covered.all():
        start = int(np.argmin(covered))                     # begin at an uncovered sample
        idx = [(start + k) % n for k in range(n)]
        cur = None
        for i in idx:
            if covered[i] and cur is None:
                cur = [i, i]
            elif covered[i]:
                cur[1] = i
            elif cur is not None:
                runs.append(cur)
                cur = None
        if cur is not None:
            runs.append(cur)
    axes = []
    for i0, i1 in runs:
        span = (i1 - i0) % n
        mid = ang[(i0 + span // 2) % n] + (math.pi / n if span % 2 else 0.0)
        axes.append(math.degrees(math.atan2(math.sin(mid), math.cos(mid))))
    radial = np.hypot(verts_xy[:, 0], verts_xy[:, 1])
    rmax = float(radial.max())
    tip_idx = np.nonzero(radial > rmax - 1e-7)[0]
    tip_ang = np.degrees(np.arctan2(verts_xy[tip_idx, 1], verts_xy[tip_idx, 0]))
    tips = []
    for a in tip_ang:                                       # cluster the tip vertices (top / bottom of the land)
        if not any(abs(((a - b) + 180.0) % 360.0 - 180.0) < 1.0 for b in tips):
            tips.append(float(a))
    arms = []
    for axis in sorted(axes):
        if not tips:
            break
        offs = [((t - axis) + 180.0) % 360.0 - 180.0 for t in tips]
        k = int(np.argmin(np.abs(offs)))
        tip = tips[k]
        arms.append({"axis_deg": round(axis, 3), "tip_deg": round(tip, 4), "tip_offset_deg": round(offs[k], 4),
                     "tip_xy_mm": [round(float(r_tip * math.cos(math.radians(tip)) / MM), 4),
                                   round(float(r_tip * math.sin(math.radians(tip)) / MM), 4)]})
    offsets = [a["tip_offset_deg"] for a in arms]

    def arm_near(target):
        cands = [a for a in arms if abs(((a["axis_deg"] - target) + 180.0) % 360.0 - 180.0) < 5.0]
        return cands[0] if cands else None

    px, py = arm_near(0.0), arm_near(90.0)
    tip_px = (math.cos(math.radians(px["tip_deg"])), math.sin(math.radians(px["tip_deg"]))) if px else None
    tip_py = (math.cos(math.radians(py["tip_deg"])), math.sin(math.radians(py["tip_deg"]))) if py else None
    checks = {
        "four_arms_found": len(arms) == 4 and len(tips) == 4,
        "arms_on_the_axes": bool(px) and bool(py) and all(
            min(abs(((a["axis_deg"] - c) + 180.0) % 360.0 - 180.0) for c in (0.0, 90.0, 180.0, -90.0)) < 1.0 for a in arms),
        "every_hook_counter_clockwise_of_its_arm": bool(offsets) and all(0.0 < v < 90.0 for v in offsets),
        "c4_equal_offsets": bool(offsets) and (max(offsets) - min(offsets) < 0.5),
        "plus_x_arm_hooks_toward_plus_y": bool(tip_px) and tip_px[1] > 0.0,
        "plus_y_arm_hooks_toward_minus_x": bool(tip_py) and tip_py[0] < 0.0,
    }
    return {"passed": all(checks.values()), "checks": checks, "arms": arms, "probe_radius_mm": round(probe_r / MM, 3),
            "reads": ("left-facing hooked cross (counter-clockwise hooks): the required presented face"
                      if all(checks.values()) else "NOT the required handedness")}


def handedness_from_mask(path, px_per_mm: float, o: HookedOutline, centre_px=None, flip: bool = False) -> dict:
    """The same gate read off a RENDERED straight-down view (the gallery's top / wire / LOD-strip masks): alpha > 0.5 is
    the silhouette; image x is +X and image up is +Y exactly when the camera looks down on +Z, so the image reads the
    presented face.  ``flip`` mirrors the image left-right first (the negative control: it must fail)."""
    from .render import load_pixels
    alpha = load_pixels(path)[..., 3] > 0.5
    if flip:
        alpha = alpha[:, ::-1]
    h, w = alpha.shape
    rows, cols = np.nonzero(alpha)
    if centre_px is None:
        centre_px = (0.5 * (cols.min() + cols.max()), 0.5 * (rows.min() + rows.max()))
    cx, cy = centre_px
    x = (cols + 0.5 - cx) / px_per_mm * MM
    y = (cy - rows - 0.5) / px_per_mm * MM
    return _handedness_from_pixels(alpha, x, y, cx, cy, px_per_mm, o)


def _handedness_from_pixels(alpha, x, y, cx, cy, px_per_mm, o: HookedOutline) -> dict:
    h, w = alpha.shape
    probe_r = 0.55 * o.u_hook
    n = 1440
    ang = np.linspace(-math.pi, math.pi, n, endpoint=False)
    pc = np.clip(np.round(cx + probe_r / MM * px_per_mm * np.cos(ang) - 0.5).astype(int), 0, w - 1)
    pr = np.clip(np.round(cy - probe_r / MM * px_per_mm * np.sin(ang) - 0.5).astype(int), 0, h - 1)
    covered = alpha[pr, pc]
    # rendered masks carry anti-aliasing: a one-pixel notch at an arm's edge (the wire overlay of the LOD strip) splits
    # its run; merge covered runs closer than 3 deg and drop slivers under 5 deg (an arm is ~29 deg wide at the probe)
    axes = _merge_runs(covered, ang)
    r = np.hypot(x, y)
    far = r > np.percentile(r, 99.95)
    tips = []
    for a in np.degrees(np.arctan2(y[far], x[far])):
        if not any(abs(((a - b) + 180.0) % 360.0 - 180.0) < 10.0 for b in tips):
            tips.append(float(a))
    arms = []
    for axis in sorted(axes):
        offs = [((t - axis) + 180.0) % 360.0 - 180.0 for t in tips]
        if offs:
            k = int(np.argmin(np.abs(offs)))
            arms.append({"axis_deg": round(axis, 2), "tip_deg": round(tips[k], 2), "tip_offset_deg": round(offs[k], 2)})

    def near(target):
        c = [a for a in arms if abs(((a["axis_deg"] - target) + 180.0) % 360.0 - 180.0) < 5.0]
        return c[0] if c else None

    px, py = near(0.0), near(90.0)
    checks = {
        "four_arms_four_tips": len(arms) == 4 and len(tips) == 4,
        "every_hook_counter_clockwise_of_its_arm": bool(arms) and all(0.0 < a["tip_offset_deg"] < 90.0 for a in arms),
        "plus_x_arm_hooks_toward_plus_y": bool(px) and math.sin(math.radians(px["tip_deg"])) > 0.0,
        "plus_y_arm_hooks_toward_minus_x": bool(py) and math.cos(math.radians(py["tip_deg"])) < 0.0,
    }
    return {"passed": all(checks.values()), "checks": checks, "arms": arms}


def _merge_runs(covered: np.ndarray, ang: np.ndarray, gap_deg: float = 3.0, min_deg: float = 5.0) -> List[float]:
    """Midpoint angles (deg) of the covered runs on a sampled circle, gaps under ``gap_deg`` closed and runs under
    ``min_deg`` dropped (wrap-around aware)."""
    n = len(covered)
    if not covered.any() or covered.all():
        return []
    step = 360.0 / n
    closed = covered.copy()
    gap = max(1, int(round(gap_deg / step)))
    start = int(np.argmax(covered))                         # begin on a covered sample
    k = 0
    while k < n:
        i = (start + k) % n
        if not closed[i]:
            j = k
            while j < n and not covered[(start + j) % n]:
                j += 1
            if j - k <= gap:
                for m in range(k, j):
                    closed[(start + m) % n] = True
            k = j
        else:
            k += 1
    runs, run = [], None
    begin = int(np.argmin(closed))
    for k in range(n):
        i = (begin + k) % n
        if closed[i]:
            run = [k, k] if run is None else [run[0], k]
        elif run is not None:
            runs.append(run)
            run = None
    if run is not None:
        runs.append(run)
    out = []
    for r0, r1 in runs:
        if (r1 - r0 + 1) * step < min_deg:
            continue
        mid = (begin + (r0 + r1) / 2.0) % n
        a = math.degrees(float(ang[int(math.floor(mid))]) + (mid - math.floor(mid)) * math.radians(step))
        out.append(((a + 180.0) % 360.0) - 180.0)
    return out


def handedness_of_strip(path, px_per_mm: float, o: HookedOutline, count: int, flip: bool = False) -> dict:
    """The LOD strip: ``count`` plan views side by side (labels under each).  Each object is the top-most run of rows
    in its own column band; its centre is its bounding-box centre (the outline is C4, so that is the origin)."""
    from .render import load_pixels
    alpha = load_pixels(path)[..., 3] > 0.5
    if flip:
        alpha = alpha[:, ::-1]
    # the objects share one row band at the top; the labels sit in a separate band below it
    rowcov = alpha.any(axis=1)
    rows = np.nonzero(rowcov)[0]
    r_end = rows[0]
    while r_end + 1 < len(rowcov) and rowcov[r_end + 1]:
        r_end += 1
    alpha = alpha.copy()
    alpha[r_end + 1:] = False
    colcov = alpha.any(axis=0)
    bands, start = [], None
    for c, v in enumerate(colcov):
        if v and start is None:
            start = c
        elif not v and start is not None:
            bands.append((start, c))
            start = None
    if start is not None:
        bands.append((start, len(colcov)))
    bands = sorted(sorted(bands, key=lambda b: b[1] - b[0], reverse=True)[:count])
    out = []
    for c0, c1 in bands:
        sub = alpha[:, c0:c1]
        rowcov = sub.any(axis=1)
        rows = np.nonzero(rowcov)[0]
        r0 = rows[0]
        r1 = r0
        while r1 + 1 < len(rowcov) and rowcov[r1 + 1]:
            r1 += 1
        obj = np.zeros_like(alpha)
        obj[r0:r1 + 1, c0:c1] = sub[r0:r1 + 1]
        rr, cc = np.nonzero(obj)
        cx, cy = 0.5 * (cc.min() + cc.max() + 1), 0.5 * (rr.min() + rr.max() + 1)
        x = (cc + 0.5 - cx) / px_per_mm * MM
        y = (cy - rr - 0.5) / px_per_mm * MM
        out.append(_handedness_from_pixels(obj, x, y, cx, cy, px_per_mm, o))
    return {"passed": len(out) == count and all(g["passed"] for g in out), "panels": out}


def handedness_gate(obj, o: HookedOutline) -> dict:
    """The gate on a built LOD (its +Z face and its vertices)."""
    tris = top_face_triangles(obj)
    co = np.array([v.co[:] for v in obj.data.vertices], dtype=np.float64)
    out = handedness_from_plan(tris, co[:, :2], 0.55 * o.u_hook, o.r_tip)
    out["object"] = obj.name
    out["presented_face"] = "+Z (the top face: faces with normal z > 0.999 at z = +t/2)"
    return out


def handedness_negative_control(obj, o: HookedOutline) -> dict:
    """The same gate on mirrored copies of the built outline (in memory, never a mesh): it must FAIL both.

    ``mirror_y``: y -> -y (the plate turned over about X, or an axis flip in an exporter): the 'back face' reading.
    ``mirror_35``: reflected about the line at +35 deg - the tips land on exactly the same angles, only the arms move,
    so a gate that looked at the tip angles alone would pass it."""
    tris = top_face_triangles(obj)
    co = np.array([v.co[:] for v in obj.data.vertices], dtype=np.float64)[:, :2]
    out = {}
    c, s = math.cos(math.radians(70.0)), math.sin(math.radians(70.0))
    for name, mat in (("mirror_y", np.array([[1.0, 0.0], [0.0, -1.0]])),
                      ("mirror_35", np.array([[c, s], [s, -c]]))):
        t2 = tris @ mat.T
        v2 = co @ mat.T
        res = handedness_from_plan(t2, v2, 0.55 * o.u_hook, o.r_tip)
        out[name] = {"gate_passed": res["passed"], "checks": res["checks"],
                     "offsets_deg": [a["tip_offset_deg"] for a in res["arms"]]}
    # and the analytic outline itself, mirrored, as a pure-geometry control (no mesh involved)
    out["caught"] = all(not v["gate_passed"] for v in out.values() if isinstance(v, dict))
    return out


# =========================================================================== the texture sheets


def _plate_faces(obj):
    """(loop start, loop total, plate side +-1) of every flat plate face (|N.z| > 0.999, every corner at |z| = t/2)."""
    mesh = obj.data
    co = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3).astype(np.float64)
    half_t = float(np.abs(co[:, 2]).max())
    out = []
    for poly in mesh.polygons:
        z = co[list(poly.vertices), 2]
        if abs(poly.normal.z) > 0.999 and np.all(np.abs(np.abs(z) - half_t) < 1e-9):
            out.append((poly.loop_start, poly.loop_total, 1 if poly.normal.z > 0.0 else -1))
    return co, half_t, out


def uv_plate_orientation(obj, mirror_u: bool = False) -> dict:
    """Every plate face's orientation in UV0 against its orientation in plan seen from +Z (the same corner order).

    A face whose UV triangle turns the same way as its plan outline seen from +Z maps into the texture as seen from the
    presented face; the opposite turn is the view from below - the mirror image.  ``mirror_u`` negates u first (the
    negative control)."""
    mesh = obj.data
    co, _half_t, faces = _plate_faces(obj)
    loop_vert = np.empty(len(mesh.loops), dtype=np.int64)
    mesh.loops.foreach_get("vertex_index", loop_vert)
    uv = np.empty(len(mesh.loops) * 2, dtype=np.float32)
    mesh.uv_layers[0].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2).astype(np.float64)
    if mirror_u:
        uv[:, 0] = -uv[:, 0]
    counts = {"top": [0, 0], "bottom": [0, 0]}                 # [same turn, opposite turn]
    for start, total, side in faces:
        loops = np.arange(start, start + total)
        p = co[loop_vert[loops], :2]
        q = uv[loops]
        plan = 0.5 * float(np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1]))
        tex = 0.5 * float(np.sum(q[:, 0] * np.roll(q[:, 1], -1) - np.roll(q[:, 0], -1) * q[:, 1]))
        counts["top" if side > 0 else "bottom"][0 if plan * tex > 0.0 else 1] += 1
    return {"object": obj.name, "plate_faces": len(faces),
            "top_faces_as_seen_from_plus_z": counts["top"][0], "top_faces_mirrored": counts["top"][1],
            "bottom_faces_as_seen_from_plus_z": counts["bottom"][0], "bottom_faces_mirrored": counts["bottom"][1],
            "passed": bool(faces) and counts["top"][1] == 0 and counts["bottom"][1] == 0}


def uv_island_reading(lod0, o: HookedOutline, mirror_u: bool = False) -> dict:
    """How each plate island of LOD0's UV0 (= the baked texture sheets) READS: the determinant of its plan -> UV map and
    the four hook tips' angles past their arm axes measured IN the texture (u right, v up: the PNG as displayed)."""
    from .uv import lod0_island_maps
    islands = lod0_island_maps(lod0)
    _co, half_t, faces = _plate_faces(lod0)
    starts = {int(p.loop_start): p.index for p in lod0.data.polygons}
    sides: Dict[int, set] = {}
    for start, _total, side in faces:
        sides.setdefault(int(islands["island_of_face"][starts[int(start)]]), set()).add(side)
    out = []
    for island, side_set in sorted(sides.items()):
        M = np.array(islands["maps"][island], dtype=np.float64)          # (x, y, z, 1) -> (u, v)
        if mirror_u:
            M[:, 0] = -M[:, 0]
        J = M[:2, :].T                                                   # d(u, v) / d(x, y)
        det = float(np.linalg.det(J))
        offsets = []
        for side in sorted(side_set):
            z = side * half_t

            def to_uv(x, y):
                return np.array([x, y, z, 1.0]) @ M

            centre = to_uv(0.0, 0.0)
            for k in range(4):
                ax, ay = rotate(k, 4, 20.0 * MM, 0.0)
                tx, ty = rotate(k, 4, *o.tip)
                a, t = to_uv(ax, ay) - centre, to_uv(tx, ty) - centre
                ang = math.degrees(math.atan2(a[0] * t[1] - a[1] * t[0], a[0] * t[0] + a[1] * t[1]))
                offsets.append(round(ang, 3))
        out.append({"island": int(island), "faces": "+Z plate" if side_set == {1} else "-Z plate" if side_set == {-1}
                    else "both", "determinant_uv_per_m2": round(det, 3),
                    "tip_offsets_in_texture_deg": offsets,
                    "reads": "as seen from +Z (left-facing)" if det > 0 and all(0 < v < 90 for v in offsets)
                    else "MIRRORED (as seen from -Z)"})
    return {"islands": out, "passed": bool(out) and all(r["reads"].startswith("as seen from +Z") for r in out)}


def texture_handedness(lod_objects, o: HookedOutline) -> dict:
    """The form gate (3.9.1, the visual review's major): the baked maps' plate islands must read as the presented +Z face,
    on every LOD's UV0, with the u-mirrored layout as the negative control (it must fail)."""
    faces = {obj.name: uv_plate_orientation(obj) for obj in lod_objects}
    reading = uv_island_reading(lod_objects[0], o)
    neg_faces = {obj.name: uv_plate_orientation(obj, mirror_u=True) for obj in lod_objects}
    neg_reading = uv_island_reading(lod_objects[0], o, mirror_u=True)
    control = {"mirrored_u_faces_pass": {k: v["passed"] for k, v in neg_faces.items()},
               "mirrored_u_islands_pass": neg_reading["passed"],
               "mirrored_u_tip_offsets_deg": [r["tip_offsets_in_texture_deg"] for r in neg_reading["islands"]]}
    control["caught"] = not any(control["mirrored_u_faces_pass"].values()) and not control["mirrored_u_islands_pass"]
    return {"rule": ("every flat plate face of every LOD maps into UV0 turning the same way as its plan outline seen from "
                     "+Z, and every plate island of LOD0 (the baked BC / ORM / N sheets) has a positive plan -> UV "
                     "determinant with each hook tip counter-clockwise of its arm in the texture (u right, v up, i.e. "
                     "the PNG as displayed): both the +Z and the -Z island read as the presented face"),
            "faces": faces, "lod0_islands": reading, "negative_control": control,
            "passed": all(v["passed"] for v in faces.values()) and reading["passed"]}


# =========================================================================== hull


def plan_hull(o: HookedOutline) -> List[Tuple[float, float]]:
    """A convex polygon enclosing the plate in plan, exactly C4: per quarter the tip plus two vertices where
    three supporting lines of the next arm's back arc meet (the line from the tip tangent to the arc, the tangent at
    the arc's midpoint between that tangent point and the next tip, the tangent at the next tip)."""
    tip = o.tip
    C1 = rotate(1, 4, *o.C)                                  # arm 1's arc centre
    tip1 = rotate(1, 4, *tip)
    elbow1 = rotate(1, 4, *o.elbow)
    dx, dy = tip[0] - C1[0], tip[1] - C1[1]
    dist = math.hypot(dx, dy)
    base = math.atan2(dy, dx)
    off = math.acos(o.R / dist)
    phi_e1 = math.atan2(elbow1[1] - C1[1], elbow1[0] - C1[0])
    phi_t1 = math.atan2(tip1[1] - C1[1], tip1[0] - C1[0])
    cands = [base + off, base - off]

    def within(phi):
        a = (phi - phi_e1) % (2.0 * math.pi)
        return a <= (phi_t1 - phi_e1) % (2.0 * math.pi)

    tangent = [p for p in cands if within(p)]
    if tangent:
        phi0 = tangent[0]
        p0 = (C1[0] + o.R * math.cos(phi0), C1[1] + o.R * math.sin(phi0))
    else:                                                    # the supporting line from the tip touches the elbow
        phi0 = phi_e1
        p0 = elbow1
    phi_m = 0.5 * (phi0 + phi_t1)

    def tangent_line(phi):
        px, py = C1[0] + o.R * math.cos(phi), C1[1] + o.R * math.sin(phi)
        return (px, py), (-math.sin(phi), math.cos(phi))

    from .outline_spec import _intersect
    l0 = (tip, (p0[0] - tip[0], p0[1] - tip[1]))
    l1 = tangent_line(phi_m)
    l2 = tangent_line(phi_t1)
    v1 = _intersect(l0[0], l0[1], l1[0], l1[1])
    v2 = _intersect(l1[0], l1[1], l2[0], l2[1])
    quarter = [tip, v1, v2]
    out = []
    for k in range(4):
        out += [rotate(k, 4, x, y) for x, y in quarter]
    return out


def author_outline_hull(obj, o: HookedOutline, index: int = 0):
    """``UCX_<obj.name>_NN``: the plan hull as a prism at full plate thickness (24 vertices, exactly C4, convex)."""
    name = f"UCX_{obj.name}_{index:02d}"
    if bpy.data.objects.get(name) is not None:
        raise ValueError(f"{name!r} already exists")
    rim = plan_hull(o)
    n = len(rim)
    co = [(x, y, o.half_t) for x, y in rim] + [(x, y, -o.half_t) for x, y in rim]
    faces = []
    for k in range(n):
        k1 = (k + 1) % n
        faces.append((n + k, n + k1, k1))
        faces.append((n + k, k1, k))
    for k in range(1, n - 1):
        faces.append((0, k, k + 1))
        faces.append((n, n + k + 1, n + k))
    coords = np.array(co, dtype=np.float64)
    # convexity in plan (every turn left)
    for k in range(n):
        a, b, c = np.array(rim[k]), np.array(rim[(k + 1) % n]), np.array(rim[(k + 2) % n])
        if (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]) <= 0.0:
            raise RuntimeError(f"{name}: plan hull is not strictly convex at vertex {(k + 1) % n}")
    mesh_co = np.array([v.co[:] for v in obj.data.vertices], dtype=np.float64)
    outside = hull_outside_distance(coords, faces, mesh_co)
    if outside > 1e-7:
        raise RuntimeError(f"{name}: the hull does not enclose {obj.name} (a vertex is {outside / MM:.4f} mm outside)")
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


# =========================================================================== measurement


def _fit_circle(points: np.ndarray):
    x, y = points[:, 0], points[:, 1]
    A = np.column_stack([2.0 * x, 2.0 * y, np.ones(len(x))])
    (cx, cy, c), *_ = np.linalg.lstsq(A, x * x + y * y, rcond=None)
    r = math.sqrt(c + cx * cx + cy * cy)
    return float(cx), float(cy), r, float(np.abs(np.hypot(x - cx, y - cy) - r).max())


def unground_plate(spec: HookedCrossSpec, lod: OutlineLodSpec) -> dict:
    """``lod`` authored again with NO grind and NO chamfer (bmesh only) and measured: the polygonised outline."""
    o = spec.outline()
    plain = replace(lod, chamfer=False, grind=False)
    bm, stats, _runs, _plan = build_outline_bmesh(o, plain)
    try:
        volume = bm.calc_volume(signed=True)
    finally:
        bm.free()
    volume_mm3 = volume / MM ** 3
    return {"volume_mm3": round(volume_mm3, 6), "plate_area_mm2": round(volume_mm3 / spec.thickness_mm, 6),
            "mass_g": round(volume / (0.01 ** 3) * spec.density_g_cm3, 6), "triangles": stats["triangles"]}


def measure_outline(obj, spec: HookedCrossSpec, lod: OutlineLodSpec) -> dict:
    """Build-to figures measured on the finished mesh (never copied from the spec)."""
    o = spec.outline()
    bm = evaluated_bm(obj)
    try:
        co = np.array([v.co[:] for v in bm.verts], dtype=np.float64)
        volume = bm.calc_volume(signed=True)
        face_verts = [[v.index for v in f.verts] for f in bm.faces]
        normals = np.array([f.normal[:] for f in bm.faces], dtype=np.float64)
        areas = np.array([f.calc_area() for f in bm.faces], dtype=np.float64)
        min_edge = min(e.calc_length() for e in bm.edges)
        min_area = min(f.calc_area() for f in bm.faces)
        zero_edges = sum(1 for e in bm.edges if e.calc_length() <= DEGENERATE_EDGE)
        zero_faces = sum(1 for f in bm.faces if f.calc_area() <= DEGENERATE_AREA)
    finally:
        bm.free()
    xy = co[:, :2]
    zs = co[:, 2]
    radial = np.hypot(xy[:, 0], xy[:, 1])
    edge_d, scallop_d = outline_distances(o, xy)
    on_outline = edge_d < 1e-7
    half_t = float(zs.max())
    # tips: the four farthest points; tip to tip = the largest distance between two of them (opposite arms)
    rmax = float(radial.max())
    tips = xy[radial > rmax - 1e-7]
    tip_to_tip = max(float(np.linalg.norm(a - b)) for a in tips for b in tips)
    # arm 0 in its own frame: outline vertices in the -45..45 deg wedge, top half
    ang = np.arctan2(xy[:, 1], xy[:, 0])
    w0 = (np.abs(ang) < math.radians(44.0)) & on_outline & (zs > 0.0)
    wx, wy = xy[w0, 0], xy[w0, 1]
    # arm widths at stations: leading (y > 0) and trailing (y < 0) outline vertices at the same x (the arm stations)
    widths = {}
    for u_mm in (10.0, 20.0, 30.0):
        u = u_mm * MM
        lead = [(x, y) for x, y in zip(wx, wy) if abs(y - o.lead_v(x)) < 1e-6 and 5.0 * MM < x < o.u_hook]
        trail = [(x, y) for x, y in zip(wx, wy) if abs(y + o.lead_v(x)) < 1e-6 and 5.0 * MM < x < o.elbow[0]]
        if lead and trail:
            la = np.array(lead)
            ta = np.array(trail)
            lf = np.polyfit(la[:, 0], la[:, 1], 1)
            tf = np.polyfit(ta[:, 0], ta[:, 1], 1)
            widths[f"u{u_mm:g}"] = round((np.polyval(lf, u) - np.polyval(tf, u)) / MM, 6)
            widths.setdefault("edge_fit", {"leading_slope": round(float(lf[0]), 7), "trailing_slope": round(float(tf[0]), 7),
                                           "taper_included_deg": round(math.degrees(math.atan(-lf[0]) + math.atan(tf[0])), 5)})
    widths["u0_extrapolated"] = round((np.polyval(lf, 0.0) - np.polyval(tf, 0.0)) / MM, 6) if lead and trail else None
    # the back arc of arm 0: outline vertices near the analytic circle, within the arm-0 wedge
    d_arc = np.abs(np.hypot(wx - o.C[0], wy - o.C[1]) - o.R)
    arc_pts = np.column_stack([wx, wy])[(d_arc < 1e-6)]
    fit = _fit_circle(arc_pts) if len(arc_pts) >= 3 else None
    # the inner edge: outline vertices on the analytic inner line, between the tip and the hook corner
    dx, dy = o.d_inner
    rel = np.column_stack([wx - o.tip[0], wy - o.tip[1]])
    along = rel @ np.array([dx, dy])
    perp = rel @ np.array([-dy, dx])
    inner_len = math.hypot(o.hk[0] - o.tip[0], o.hk[1] - o.tip[1])
    inner_pts = np.column_stack([wx, wy])[(np.abs(perp) < 1e-6) & (along > -1e-9) & (along < inner_len - 0.3 * MM)]
    inner_deg = None
    if len(inner_pts) >= 2:
        p = np.polyfit(inner_pts[:, 1], inner_pts[:, 0], 1)          # x as a function of y (steep line)
        inner_deg = math.degrees(math.atan2(1.0, p[0]))
    # tip: the +X arm's tip (the farthest vertex in the arm-0 wedge)
    t0 = tips[np.argmax(tips[:, 0])]
    tip_deg = math.degrees(math.atan2(t0[1], t0[0]))
    included = None
    if fit is not None and inner_deg is not None:
        cx, cy, r, _res = fit
        rad = np.array([t0[0] - cx, t0[1] - cy]) / r
        tan_back = np.array([rad[1], -rad[0]])               # back along the arc from the tip (clockwise about C)
        in_dir = np.array([o.hk[0] - t0[0], o.hk[1] - t0[1]])
        in_dir /= np.linalg.norm(in_dir)
        included = math.degrees(math.acos(float(np.clip(tan_back @ in_dir, -1.0, 1.0))))
    # fillets: vertices ON the analytic fillet circles (junction at -45 deg, hook corner)
    fillets = {}
    jl, hf = o.junction(False), o.hook_fillet()
    for name, info in (("junction", jl), ("hook_corner", hf)):
        if info.get("sharp"):
            continue
        cx, cy = info["centre"]
        sel = np.abs(np.hypot(xy[:, 0] - cx, xy[:, 1] - cy) - info["r"]) < 1e-7
        pts = xy[sel & on_outline]
        uniq = np.unique(np.round(pts / 1e-9).astype(np.int64), axis=0) * 1e-9 if len(pts) else pts
        if len(uniq) >= 3:
            f = _fit_circle(uniq)
            fillets[name] = {"radius_mm": round(f[2] / MM, 6), "max_residual_mm": round(f[3] / MM, 9),
                             "vertices": int(len(uniq))}
        else:
            fillets[name] = {"radius_mm": None, "vertices": int(len(uniq))}
    # knife grind figures: the cutting zone = vertices away from the non-cutting edges (scallop distance)
    knife_w, _dk = o.knife_of(lod)
    # the FULL knife only: off the non-cutting edges and not in a run-out (3.9.1: an eased run-out has intermediate
    # columns - its facets twist and its wall grows toward the chamfer's - which are not the grind's angle or land)
    zone = (scallop_d > 0.6 * MM) & (runout_distance(o, xy) >= -1e-6)
    ridge = None
    rpts = co[(zs > 0.0) & (edge_d > 1e-7) & (edge_d < knife_w - 1e-7) & (np.abs(zs - half_t) > 1e-7)
              & (np.hypot(xy[:, 0] - o.tip[0], xy[:, 1] - o.tip[1]) < 9.5 * MM)]
    if len(rpts) >= 2:
        # ridge vertices: equidistant from both edges (the arc and the inner line)
        d_in = np.abs((rpts[:, 0] - o.tip[0]) * (-dy) + (rpts[:, 1] - o.tip[1]) * dx)
        d_ar = o.R - np.hypot(rpts[:, 0] - o.C[0], rpts[:, 1] - o.C[1])
        on_r = np.abs(d_in - d_ar) < 1e-6
        if on_r.sum() >= 2:
            dist_tip = np.hypot(rpts[on_r, 0] - o.tip[0], rpts[on_r, 1] - o.tip[1])
            ridge = np.column_stack([dist_tip, rpts[on_r, 2]])
    grind = grind_figures(co, face_verts, normals, areas, edge_d, knife_w, zone, o.r_tip, math.degrees(o.alpha),
                          o.t - 2.0 * o.knife.depth if lod.knife_land else 0.0, ridge)
    if ridge is not None:
        slope = float(np.polyfit(ridge[:, 0], ridge[:, 1], 1)[0])
        grind["tip_ridge_rise_deg"] = round(math.degrees(math.atan(slope)), 4)
        grind.pop("tip_ridge_included_deg", None)
    grind["grind_width_mm"] = round(knife_w / MM, 6)
    grind["land_mode"] = "edge land" if lod.knife_land else "facets meet in a sharp edge line (land 0)"
    # grind extent measured on the mesh: along each blade edge, the outline vertices where the facet reaches full
    # knife width (plate-edge vertex 0.95 x the knife width in along the normal)
    extent = grind_extent(co, o, lod)
    # small chamfer on the non-cutting edges: the lowest |z| of outline vertices there is the wall top
    nc = on_outline & (scallop_d < 1e-7) & (zs > 0.0)
    wall_top = float(zs[nc].min()) if nc.any() else None
    plain = unground_plate(spec, lod)
    masses = mass_figures(volume, plain["volume_mm3"] * MM ** 3, spec)
    volume_mm3 = volume / MM ** 3
    tip_z = np.abs(zs[radial > rmax - 1e-7])
    return {
        "tip_to_tip_mm": round(tip_to_tip / MM, 6),
        "across_mm": round((co[:, 0].max() - co[:, 0].min()) / MM, 6),
        "across_y_mm": round((co[:, 1].max() - co[:, 1].min()) / MM, 6),
        "bbox_mm": [round((co[:, i].max() - co[:, i].min()) / MM, 6) for i in range(3)],
        "thickness_mm": round((zs.max() - zs.min()) / MM, 6),
        "tip_radius_mm": round(rmax / MM, 6),
        "tip_angle_deg_ccw_of_arm": round(tip_deg, 5),
        "arm_widths_mm": widths,
        "back_arc_fit": ({"radius_mm": round(fit[2] / MM, 5), "centre_mm": [round(fit[0] / MM, 4), round(fit[1] / MM, 4)],
                          "max_residual_mm": round(fit[3] / MM, 7), "vertices": int(len(arc_pts)),
                          "axis_crossing_mm": round((fit[0] + math.sqrt(fit[2] ** 2 - fit[1] ** 2)) / MM, 5)}
                         if fit else None),
        "inner_edge_deg_to_arm": round(inner_deg, 5) if inner_deg is not None else None,
        "tip_included_deg": round(included, 5) if included is not None else None,
        "fillets": fillets,
        "grind": grind,
        "grind_extent": extent,
        "small_chamfer_wall_mm": round(2.0 * wall_top / MM, 6) if wall_top is not None else 0.0,
        "tip_edge_height_mm": round(2.0 * float(tip_z.max()) / MM, 6) if len(tip_z) else None,
        "volume_mm3": round(volume_mm3, 4),
        "plate_area_mm2": round(volume_mm3 / (o.t / MM), 4),
        "outline_volume_mm3": plain["volume_mm3"],
        "outline_plate_area_mm2": plain["plate_area_mm2"],
        "analytic_area_mm2": round(4.0 * o.wedge_area() / MM ** 2, 6),
        **masses,
        "min_edge_mm": round(min_edge / MM, 6),
        "min_face_area_mm2": round(min_area / MM ** 2, 9),
        "zero_length_edges": zero_edges,
        "zero_area_faces": zero_faces,
        "coincident_vertices": coincident_pairs(co),
    }


def grind_extent(co: np.ndarray, o: HookedOutline, lod: OutlineLodSpec) -> dict:
    """Where the knife grind is at full width, measured on the mesh (arm 0, top face).

    For every plate-edge vertex (z = +t/2) near the back arc or the inner edge, its plan distance to that edge; the
    grind is 'full' where it is within 2 % of the knife width.  Reported as contour distances from the tip."""
    knife_w, _ = o.knife_of(lod)
    xy, z = co[:, :2], co[:, 2]
    top = np.abs(z - z.max()) < 1e-9
    ang = np.arctan2(xy[:, 1], xy[:, 0])
    arm0 = (np.abs(ang) < math.radians(44.0)) & top
    d_arc = o.R - np.hypot(xy[:, 0] - o.C[0], xy[:, 1] - o.C[1])
    dx, dy = o.d_inner
    rel = xy - np.array(o.tip)
    along = rel @ np.array([dx, dy])
    d_in = rel @ np.array([-dy, dx])
    phi = np.arctan2(xy[:, 1] - o.C[1], xy[:, 0] - o.C[0])
    phi_t = o.arc_angle(o.tip)
    out = {}
    sel = arm0 & (np.abs(d_arc - knife_w) < 0.02 * knife_w) & (d_in > 0.5 * knife_w)
    if sel.any():
        s = (phi_t - phi[sel]) * o.R
        out["back_arc_full_width_from_tip_mm"] = [round(float(s.min()) / MM, 4), round(float(s.max()) / MM, 4)]
    sel = arm0 & (np.abs(d_in - knife_w) < 0.02 * knife_w) & (d_arc > 0.5 * knife_w) & (along > 0.0)
    if sel.any():
        out["inner_edge_full_width_from_tip_mm"] = [round(float(along[sel].min()) / MM, 4),
                                                    round(float(along[sel].max()) / MM, 4)]
    rb = o.runout_bounds()
    out["design"] = {"back_arc": {"full_knife_from_tip_mm": round(o.R * (phi_t - rb["phi_b1"]) / MM, 4),
                                  "runout_ends_from_tip_mm": round(o.R * (phi_t - rb["phi_b0"]) / MM, 4),
                                  "shoulder_from_tip_mm": round(o.R * (phi_t - o.arc_angle(o.shoulder)) / MM, 4)},
                     "inner_edge": {"full_knife_from_tip_mm": round(rb["inner_r0"] / MM, 4),
                                    "runout_ends_from_tip_mm": round(rb["inner_r1"] / MM, 4),
                                    "fillet_from_tip_mm": round(rb["inner_fillet"] / MM, 4)}}
    return out


def outline_topology_quality(obj) -> dict:
    """Face-shape figures of the flat plate faces and every triangle (the wireframe review)."""
    bm = evaluated_bm(obj)
    try:
        half_t = max(v.co.z for v in bm.verts)
        aspects = []
        min_angle, under5, tris = 180.0, 0, 0
        plate_min, plate_under5, plate_under15, strip_under5 = 180.0, 0, 0, 0
        for face in bm.faces:
            co = [v.co.copy() for v in face.verts]
            flat = all(abs(abs(v.co.z) - half_t) < 1e-9 for v in face.verts) and abs(face.normal.z) > 0.999
            for k in range(1, len(co) - 1):
                a, b, c = co[0], co[k], co[k + 1]
                tri = [math.degrees((b - a).angle(c - a)), math.degrees((a - b).angle(c - b)),
                       math.degrees((a - c).angle(b - c))]
                tris += 1
                min_angle = min(min_angle, min(tri))
                under5 += min(tri) < 5.0
                if flat:
                    plate_min = min(plate_min, min(tri))
                    plate_under5 += min(tri) < 5.0
                    plate_under15 += min(tri) < 15.0
                else:
                    strip_under5 += min(tri) < 5.0
            if all(abs(v.co.z - half_t) < 1e-9 for v in face.verts):
                longest = max((co[k] - co[(k + 1) % len(co)]).length for k in range(len(co)))
                aspects.append(longest ** 2 / face.calc_area())
    finally:
        bm.free()
    return {
        "plate_top_faces": len(aspects),
        "plate_aspect_median": round(float(np.median(aspects)), 3) if aspects else None,
        "plate_aspect_max": round(float(max(aspects)), 3) if aspects else None,
        "plate_faces_aspect_over_8": int(sum(a > 8.0 for a in aspects)),
        "plate_min_triangle_angle_deg": round(plate_min, 3),
        "plate_triangles_under_5deg": int(plate_under5),
        "plate_triangles_under_15deg": int(plate_under15),
        "strip_triangles_under_5deg": int(strip_under5),
        "min_triangle_angle_deg": round(min_angle, 3),
        "triangles_under_5deg": int(under5),
        "triangles": tris,
        "note": ("plate_* are the flat top and bottom faces (a constrained Delaunay of the plate edge with structured "
                 "Steiner points); strips are the facets and walls, long thin quads along the edge by construction"),
    }


# =========================================================================== the hook


class OutlinePlateGeometry(FormGeometry):
    """FormGeometry of the hooked cross: C4 (no mirror symmetry), no hole, knife grind on the hook blades."""

    kind = "outline_plate"
    noun = "hooked cross"
    # 3.9.1 (visual review, the texture sheets): the -Z UV islands are mirrored in U before the packer, so both plate
    # islands of the baked maps read as the presented +Z face (texture_handedness gates it)
    uv_mirror_underside = True
    # 3.9.1 (geometry review): LOD2's square walls (2.5 mm) are taller than LOD0's (1.87 mm under the chamfers); their
    # corners are clamped onto LOD0's wall islands so no LOD2 wall maps into the bake margin at the texture border
    uv_clamp_walls = True

    def __init__(self, spec: HookedCrossSpec) -> None:
        super().__init__(spec)
        self.o = spec.outline()

    @property
    def order(self) -> int:
        return 4

    def validate(self) -> None:
        self.spec.validate()

    def build_to(self) -> dict:
        spec = self.spec
        out = {
            "points": 4,
            "outline": "photo-matched swept-blade hooked cross (PHOTO_MEASUREMENT.md 2.5; the user's choice B)",
            "tip_to_tip_mm": 2.0 * spec.tip_radius_mm,
            "thickness_mm": spec.thickness_mm,
            "arm_half_width_mm": f"{spec.arm_half_width_mm} - {math.tan(math.radians(spec.taper_per_edge_deg)):.6f} u",
            "taper_per_edge_deg": spec.taper_per_edge_deg,
            "hook_corner_u_mm": spec.hook_corner_u_mm,
            "tip": f"r = {spec.tip_radius_mm} mm, {spec.tip_offset_deg} deg counter-clockwise of each arm axis",
            "back_arc": f"one convex arc, R {spec.back_arc_radius_mm} mm, crossing the arm axis at {spec.back_arc_axis_mm} mm",
            "concave_fillet_mm": spec.fillet_mm,
            "convex_corners": "sharp (elbow, tip)",
            "hole": "none",
            "handedness": ("left-facing: presented face +Z; the +X arm hooks toward +Y, the +Y arm toward -X; no mirror "
                           "anywhere in the build (study 2.6)"),
            "grind": ("knife (35 deg per side, 0.15 mm land) on the hook blades only: the back arc from the tip to the "
                      "shoulder and the inner edge from the tip to the hook-corner fillet, each running out over "
                      f"{spec.runout_mm} mm into the small chamfer; every other edge a {spec.chamfer_mm} mm chamfer at "
                      "35 deg over a wall"),
            "grind_angle_deg": spec.grind_angle_deg, "edge_land_mm": spec.edge_land_mm,
            "chamfer_mm": spec.chamfer_mm, "runout_mm": spec.runout_mm,
            "mass_g": spec.mass_target_g,
            "mass_gate": "outline (un-ground plate) mass within +-2 g of 37.09 g (self-consistency with the photo outline)",
            "source": f"References/Shuriken/SHURIKEN_STUDY.md section {spec.study_section}; "
                      "WorkFiles/shuriken/photo_study/PHOTO_MEASUREMENT.md 2.5",
        }
        out["derived"] = self.o.summary()
        return out

    def author(self, level: int, name: str, collection):
        obj, stats, lod = author_outline_lod(self.o, self.spec.lods[level], name, collection)
        # the handedness gate, in the build: a LOD that does not read as the left-facing form on +Z stops the build
        gate = handedness_gate(obj, self.o)
        stats["handedness_gate_passed"] = gate["passed"]
        if not gate["passed"]:
            raise RuntimeError(f"{name}: HANDEDNESS GATE FAILED (study 2.6) - {gate['checks']} arms {gate['arms']}")
        return obj, stats, lod

    def tag(self, obj) -> None:
        o = self.o
        # two sub-pixel rust specks: one on the top face of arm 1's plate, one on the bottom face near the centre
        x1, y1 = 17.0 * MM, 1.2 * MM
        x2, y2 = 2.4 * MM, -1.1 * MM
        rx1, ry1 = rotate(1, 4, x1, y1)
        rx2, ry2 = rotate(2, 4, x2, y2)
        tag_common(obj, points=4, r_tip=o.r_tip, r_hub=o.q_j * math.sqrt(2.0), chamfer_w=o.knife.width,
                   scallop_w=o.small.width, hole_w=0.0, centre_r=0.0, land=o.t - 2.0 * o.knife.depth,
                   rust=((rx1, ry1, 1.0, RUST_R[0]), (rx2, ry2, -1.0, RUST_R[1])), half_t=o.half_t,
                   wall_top=o.small.wall_top_drop)
        obj[CAVITY_MODE_PROP] = 1.0          # cavity terms from the concave corners, not every non-cutting edge
        obj[RUNOUT_TAPER_PROP] = 1.0         # 3.9.1: the polished band narrows through the blade run-outs

    def make_hull(self, lod0, options):
        hull = author_outline_hull(lod0, self.o, index=0)
        return hull, ("outline_prism: shuriken_lib.outline_plate.author_outline_hull, the plan hull circumscribed by "
                      "supporting lines of the back arcs (per quarter: the tip + 2 vertices; 24 vertices, exactly C4, "
                      "strictly convex) at full plate thickness; the build refuses it if any LOD0 vertex is outside")

    def make_sockets(self, lod0) -> None:
        o = self.o
        q = o.junction(True)["q_mid"]        # the junction between arms 0 and 1, ON the outline (the fillet midpoint)
        pipeline.make_socket(lod0, "Grip", (q, q, 0.0), rotation_euler=(0.0, 0.0, 0.25 * math.pi))
        pipeline.make_socket(lod0, "Trail", (0.0, 0.0, 0.0), rotation_euler=(0.0, 0.0, 0.0))

    def density(self, lod_used) -> dict:
        lod = lod_used[0]
        runs = self.o.columns(lod)
        plan = plate_plan(self.o, lod, runs)
        return {
            "points": 4,
            **{k: v for k, v in asdict(lod).items() if k not in ("band", "note")},
            "columns_per_wedge": sum(len(r.columns) for r in runs) - (len(runs) - 1),
            "plate_boundary_points_per_wedge": plan["n_boundary"],
            "plate_steiner_points_per_wedge": plan["n_inner"],
            "back_arc_max_chord_sagitta_mm": round(self._arc_sagitta(runs) / MM, 6),
        }

    def _arc_sagitta(self, runs) -> float:
        arc = [c for c in runs[2].columns]
        worst = 0.0
        for a, b in zip(arc, arc[1:]):
            chord = math.hypot(b.x - a.x, b.y - a.y)
            worst = max(worst, self.o.R - math.sqrt(max(0.0, self.o.R ** 2 - 0.25 * chord * chord)))
        return worst

    def wear_range(self):
        return self.o.r_tip - TIP_WEAR, self.o.r_tip

    def split_radius(self) -> float:
        return self.o.q_j * math.sqrt(2.0) + 2.0 * MM

    def measure(self, obj, lod_used) -> dict:
        return measure_outline(obj, self.spec, lod_used)

    def topology_quality(self, obj) -> dict:
        return outline_topology_quality(obj)

    def render_outline(self):
        return OutlineRenderInfo(self.o)

    def island_margin(self, default: float) -> float:
        return default if self.spec.island_margin is None else self.spec.island_margin

    def wall_projection(self):
        """Every wall face to a planar island per piece and arm, projected along the piece's travel direction (u) and
        z (v): the straight edges exactly, the back arc along its elbow -> tip chord (19 deg of arc), each fillet along
        its chord; a junction fillet is ONE island across the seam."""
        o = self.o
        hf = o.hook_fillet()
        tangents = {
            "trail": (1.0, o.T), "lead": (-1.0, o.T),
            "arc": (o.tip[0] - o.elbow[0], o.tip[1] - o.elbow[1]),
            "inner": o.d_inner, "hk": (hf["h1"][0] - hf["h2"][0], hf["h1"][1] - hf["h2"][1]),
            "jin": (1.0, 1.0), "jout": (-1.0, 1.0),
        }
        tangents = {k: (v[0] / math.hypot(*v), v[1] / math.hypot(*v)) for k, v in tangents.items()}
        labels = _wedge_labels(o)

        def classify(centre, normal):
            if abs(normal[2]) >= 0.01:
                return None
            x, y = float(centre[0]), float(centre[1])
            ang = math.atan2(y, x)
            turn = int(math.floor((ang + 0.25 * math.pi) / (0.5 * math.pi))) % 4
            lx, ly = rotate(-turn % 4, 4, x, y)
            piece = labels(lx, ly)
            tx, ty = tangents[piece]
            wx, wy = rotate(turn, 4, tx, ty)
            if piece == "jin":
                return ("j", (turn - 1) % 4), (wx, wy)
            if piece == "jout":
                return ("j", turn), (wx, wy)
            return (piece, turn), (wx, wy)

        return classify

    def symmetry_method(self) -> str:
        return ("max nearest-neighbour distance after a 90 deg rotation of the stored (float32) vertices (quarter turns "
                "are trig-free, so exact 0.0).  C4 only: the form has NO mirror symmetry (mirror_max_deviation_mm is "
                "large on purpose - the mirror image is the form the study forbids)")

    def symmetry_extra(self, lod_objects) -> Optional[dict]:
        out = {"group": "C4 (no mirror)"}
        dev = {}
        for obj in lod_objects:
            co = np.array([v.co[:] for v in obj.data.vertices], dtype=np.float64)
            mirrored = co * np.array([1.0, -1.0, 1.0])
            worst = 0.0
            for p in mirrored:
                worst = max(worst, float(np.min(np.linalg.norm(co - p, axis=1))))
            dev[obj.name] = round(worst / MM, 6)
        out["mirror_max_deviation_mm"] = dev
        out["note"] = "a mirror about X moves vertices by up to this much: the outline is chiral, as it must be"
        return out

    def lod_note(self) -> str:
        return ("LODs are authored by the outline-plate generator at reduced column counts, not decimated: LOD1 halves "
                "the arm stations, arc and blade columns, keeps the knife grind with its land, the small chamfers and "
                "one-chord fillets; LOD2 keeps a single-facet knife grind whose facets meet in an edge line (land 0), "
                "squares the non-cutting edges and sharpens the concave corners. max_surface_deviation_mm is two-sided.")

    def lod_strategy(self) -> dict:
        return {
            "method": "parametric: every LOD authored by shuriken_lib.outline_plate at its own column counts",
            "table": ("study 4's LOD rules adapted to a hole-less plate (its bands are for stars: ceilings only, nothing "
                      "padded): LOD0 full silhouette, knife grind with its land on the hook blades, small chamfers and "
                      "0.56 mm fillets elsewhere; LOD1 columns halved, grind + land + chamfers kept, fillets one chord; "
                      "LOD2 single-facet grind to an edge line, square non-cutting edges, sharp concave corners"),
            "naming": "LODn objects are created as <mesh>_LODn; pipeline.make_lod_group renames LOD0 with its "
                      "UCX_/SOCKET_ children, so the hull is UCX_<mesh>_LOD0_00",
        }

    def lod_switching_extra(self, report: dict) -> Optional[dict]:
        return {"scaled_for_bounding_radius": {
            "reference_radius_mm": 50.0, "form_radius_mm": round(self.o.r_tip / MM, 4),
            "scaled_sizes": list(scaled_lod_screen_sizes(self.o.r_tip / MM)),
            "note": ("the hook tips sit at r = 50 mm, exactly the pack's reference radius, so the pack's 1.0 / 0.10 / "
                     "0.035 are already the scaled sizes: switches at ~0.89 m and ~2.54 m")}}


def _wedge_labels(o: HookedOutline):
    """A classifier (x, y) in arm 0's wedge -> the nearest contour piece of the exact outline."""
    samples, names = [], []
    for name, piece in zip(("jin", "trail", "arc", "inner", "hk", "lead", "jout"), o.pieces()):
        if piece[0] == "line":
            (ax, ay), (bx, by) = piece[1], piece[2]
            for k in range(41):
                samples.append((ax + (bx - ax) * k / 40, ay + (by - ay) * k / 40))
                names.append(name)
        else:
            (cx, cy), r, a0, a1 = piece[1], piece[2], piece[3], piece[4]
            for k in range(41):
                a = a0 + (a1 - a0) * k / 40
                samples.append((cx + r * math.cos(a), cy + r * math.sin(a)))
                names.append(name)
    pts = np.array(samples)

    def label(x, y):
        d = np.hypot(pts[:, 0] - x, pts[:, 1] - y)
        return names[int(np.argmin(d))]

    return label


class OutlineRenderInfo:
    """What the shared rig reads from a form (render.build_preview_rig and friends)."""

    def __init__(self, o: HookedOutline) -> None:
        self._o = o
        self.n = 4
        self.half_t = o.half_t
        self.r_tip = o.r_tip
        # the LOD close-up aims at arm 0's hook tip and looks at the blade across the point, the view the stars get
        # of their point on +X, turned with the blade (render.render_lod_grind: grind_target_xy / grind_azimuth_deg)
        back = 0.011
        bis = _tip_bisector(o)
        self.grind_target_xy = (o.tip[0] - back * bis[0], o.tip[1] - back * bis[1])
        self.grind_azimuth_deg = math.degrees(math.atan2(bis[1], bis[0])) - 34.0
        self.hero_yaw_deg = float(o.spec.hero_yaw_deg)
        # every gallery camera must look down on +Z (render.camera_side; the render raises otherwise)
        self.presented_face = "+Z"
        # 3.9.1: the hero lamps follow the turned close-up camera (render.render_lod_grind), so the close-up is lit as a
        # star's point is and the lamps' floor highlight stays out of the frame
        self.grind_lamps_follow = True

    def tip_extents(self):
        pts = np.array(self._o.dense_contour(0.05 * MM))
        return float(np.ptp(pts[:, 0])), float(np.ptp(pts[:, 1]))


def _tip_bisector(o: HookedOutline) -> Tuple[float, float]:
    """Unit direction the hook tip points to (the bisector of its two edges, outward)."""
    dx, dy = o.d_inner                                        # tip -> hook corner
    phi = o.arc_angle(o.tip)
    bx, by = math.sin(phi), -math.cos(phi)                    # tip -> back along the arc
    sx, sy = -(dx + bx), -(dy + by)
    n = math.hypot(sx, sy)
    return sx / n, sy / n


__all__ = ["OutlinePlateGeometry", "OutlineRenderInfo", "author_outline_hull", "author_outline_lod",
           "texture_handedness", "uv_island_reading", "uv_plate_orientation", "SMOOTH_CHAIN_HARD_DEG",
           "build_outline_bmesh", "handedness_from_plan", "handedness_gate", "handedness_negative_control",
           "measure_outline", "outline_distances", "outline_topology_quality", "plan_hull", "plate_plan",
           "predicted_triangles", "top_face_triangles", "unground_plate"]
