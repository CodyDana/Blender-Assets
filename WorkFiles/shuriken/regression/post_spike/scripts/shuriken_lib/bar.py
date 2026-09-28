"""Throwing-spike (bo-shuriken) generator and its FormGeometry hook (library 3.8).

The first BAR in the pack (study 2.5), plugged in through the non-radial Form hook exactly
like the senban: ``Form(geometry=BarGeometry(SPEC))``; pack.py only gained two OPTIONAL
hook methods (a form's own LOD0 unwrap, a form's own symmetry measure) whose defaults are
the old code paths, so every plate form builds bit-for-bit as before.

Construction (bar_spec has the frame and the numbers).  Every vertex goes through the
pack's 1 nm position-keyed factory (``geometry.Builder``; one "wedge", keyed on the snapped
position), so duplicates cannot exist and the quadrants weld by key; one quadrant is authored
and turned by trig-free quarter turns about +X, so the mesh is exactly C4 (and, the round's
profile being mirrored about the diagonal by construction, D4):

    face     the flat face between the two arris rounds, tail base -> point base: ONE quad
             (it is a plane; the study: "at 1:25 the silhouette is nearly all straight line")
    round    the arris round, K chords (quads); each chord line P_j is cut by the point and tail
             facet of its dominant face, so the round runs out into the facets and the pyramid
             ridges beyond are sharp.  Odd K: the middle chord crosses the diagonal and ends in
             a triangle at each run-out (the ridge's first point)
    point    one planar facet per face, base edge -> run-out points -> ridge -> tip flat, authored
             as the quad strip zipped between its two mirrored chains (all coplanar)
    tail     the same toward the butt
    tip      the 0.15 mm square tip flat (tip radius 0.075 mm, the stars' figure)
    butt     the 3 mm square butt face

Smoothing by class, as in the other generators: every edge between two classes is hard; the
round (K >= 2) is smooth-shaded across its chords (a rounded arris, reported like the senban's
curved facets); the point / tail facets and faces are single planes, flat.  A temporary int
face class feeds ``geometry.knife_shading``; a FLOAT FACE attribute ``shuriken_ground`` (1 on
the round, the point facets and the tip) tells M_Shuriken_Master's bar mode what is ground,
polished steel; the four float point attributes the plate forms carry are written with their
"none" values (the bar mode computes its grind line analytically in object space).

The origin is the centre of mass BY VOLUME of the finished LOD0 (study 4 pivot rule for the
spikes): LOD0 is authored once in bar-local x (butt at 0), its volume centroid computed exactly
(divergence theorem over its own triangles) and every LOD is then authored with x - x_com
before the 1 nm snap.  The point is thinner than the tail, so the centre sits toward the butt.
"""
from __future__ import annotations

import math
from dataclasses import asdict, replace
from typing import Dict, List, Optional, Tuple

import bmesh
import bpy
import numpy as np
from mathutils import Matrix

import pipeline

from .bar_spec import (BAR_CLASS_CODE, BAR_CLASSES, GROUND_CLASSES, BarLodSpec, BarOutline, BarSpec, bar_analytic,
                       bar_triangles)
from .geometry import (DEGENERATE_AREA, DEGENERATE_EDGE, FACE_CLASS_ATTR, GRIND_ATTR, HULL_TOLERANCE, NO_HOLE_DISTANCE,
                       Builder, coincident_pairs, hull_outside_distance, hygiene_problems, knife_shading,
                       write_distance_attributes)
from .hooks import FormGeometry
from .material import GROUND_ATTR, TIP_WEAR, tag_bar
from .measure import evaluated_bm, mass_figures
from .spec import MM, scaled_lod_screen_sizes

UV_FRAMES = {
    # dominant normal -> (u axis, v axis); u x v = the outward normal (no mirrored island)
    "+z": ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
    "-z": ((1.0, 0.0, 0.0), (0.0, -1.0, 0.0)),
    "+y": ((1.0, 0.0, 0.0), (0.0, 0.0, -1.0)),
    "-y": ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    "tip": ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
    "butt": ((0.0, 0.0, 1.0), (0.0, 1.0, 0.0)),
}


def quarter(q: int, y: float, z: float) -> Tuple[float, float]:
    """(y, z) turned by q quarter turns about +X, trig-free (sign flips and swaps: exact)."""
    q %= 4
    if q == 0:
        return y, z
    if q == 1:
        return -z, y
    if q == 2:
        return -y, -z
    return z, -y


# =========================================================================== authoring


def _chain(o: BarOutline, k: int) -> List[Tuple[float, float]]:
    """(y, z) of one facet's +y chain, base -> ridge start: the profile points on this face's side."""
    prof = o.profile(k)
    if k == 0:
        return [prof[0]]
    if k % 2 == 0:
        return prof[:k // 2 + 1]
    d = o.diagonal(k)
    return prof[:(k - 1) // 2 + 1] + [(d, d)]


def bar_quadrant(bld: Builder, o: BarOutline, lod: BarLodSpec, q: int) -> None:
    """Quadrant q: its face, the arris round at its +y edge, its point and tail facets."""
    k = lod.arris_segments
    prof = o.profile(k)
    length, a, e = o.length, o.a, o.e
    x_pb = length - o.lp

    def v(x, y, z):
        yy, zz = quarter(q, y, z)
        return bld.add(x - o.shift, yy, zz)

    def m_of(p):
        return max(abs(p[0]), abs(p[1]))

    w = prof[0][0]                                       # a - rho (a when the arrises are square)
    bld.face(("face", q), v(o.lt, -w, a), v(x_pb, -w, a), v(x_pb, w, a), v(o.lt, w, a))

    right = _chain(o, k)
    point = [(o.x_point_cut(m_of(p)), p[0], p[1]) for p in right] + [(length, o.tau, o.tau)]
    tail = [(o.x_tail_cut(m_of(p)), p[0], p[1]) for p in right] + [(0.0, e, e)]
    for cls, chain in (("point", point), ("tail", tail)):
        for i in range(len(chain) - 1):
            (x0, y0, z0), (x1, y1, z1) = chain[i], chain[i + 1]
            bld.face((cls, q), v(x0, y0, z0), v(x1, y1, z1), v(x1, -y1, z1), v(x0, -y0, z0))

    if k == 0:
        return
    d = o.diagonal(k)
    for j in range(k):
        p0, p1 = prof[j], prof[j + 1]
        m0, m1 = m_of(p0), m_of(p1)
        t0, t1 = v(o.x_tail_cut(m0), *p0), v(o.x_tail_cut(m1), *p1)
        f0, f1 = v(o.x_point_cut(m0), *p0), v(o.x_point_cut(m1), *p1)
        bld.face(("round", q), t0, f0, f1, t1)
        if k % 2 == 1 and j == (k - 1) // 2:
            # the middle chord crosses the diagonal: it ends in a triangle at each run-out (the ridge's start)
            bld.face(("round", q), t1, v(o.x_tail_cut(d), d, d), t0)
            bld.face(("round", q), f0, v(o.x_point_cut(d), d, d), f1)


def bar_centroid(bm) -> Tuple[float, np.ndarray]:
    """(volume m3, volume centroid) of a closed, outward-oriented bmesh (divergence theorem, float64)."""
    vol6 = 0.0
    mom = np.zeros(3)
    for face in bm.faces:
        pts = [np.array(v.co[:], dtype=np.float64) for v in face.verts]
        for i in range(1, len(pts) - 1):
            a, b, c = pts[0], pts[i], pts[i + 1]
            t = float(np.dot(a, np.cross(b, c)))
            vol6 += t
            mom += t * (a + b + c)
    return vol6 / 6.0, mom / (4.0 * vol6)


def build_bar_bmesh(o: BarOutline, lod: BarLodSpec):
    """All four quadrants plus the tip flat and the butt through one keyed factory; smoothing baked by class."""
    bld = Builder(1)
    for q in range(4):
        bar_quadrant(bld, o, lod, q)

    def v(x, y, z):
        return bld.add(x - o.shift, y, z)

    t, e, length = o.tau, o.e, o.length
    bld.face(("tip",), v(length, t, t), v(length, -t, t), v(length, -t, -t), v(length, t, -t))   # gone when tau = 0
    bld.face(("butt",), v(0.0, e, e), v(0.0, e, -e), v(0.0, -e, -e), v(0.0, -e, e))

    bm = bmesh.new()
    class_layer = bm.faces.layers.int.new(FACE_CLASS_ATTR)
    made = [bm.verts.new(co) for co in bld.verts]
    bm.verts.ensure_lookup_table()
    face_class = {}
    for loop, cls in zip(bld.faces, bld.classes):
        face = bm.faces.new([made[i] for i in loop])
        face_class[face] = cls
        face[class_layer] = BAR_CLASS_CODE[cls[0]]
    bm.faces.ensure_lookup_table()
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.normal_update()
    for face in bm.faces:
        face.smooth = True
    for edge in bm.edges:
        linked = edge.link_faces
        edge.smooth = len(linked) == 2 and face_class[linked[0]] == face_class[linked[1]]
    volume, centroid = bar_centroid(bm)
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
        "round_faces": sum(1 for f in bm.faces if face_class[f][0] == "round"),
        "point_facet_faces": sum(1 for f in bm.faces if face_class[f][0] == "point"),
        "tail_facet_faces": sum(1 for f in bm.faces if face_class[f][0] == "tail"),
        "signed_volume_m3": bm.calc_volume(signed=True),
        "divergence_volume_m3": volume,
        "centroid_mm": [round(float(c) / MM, 9) for c in centroid],
        "min_edge_mm": min(e.calc_length() for e in bm.edges) / MM,
        "min_face_area_mm2": min(f.calc_area() for f in bm.faces) / (MM ** 2),
    }
    coords = np.array([v.co[:] for v in bm.verts], dtype=np.float64)
    stats["coincident_vertices"] = coincident_pairs(coords)
    stats["triangles"] = stats["tris"] + 2 * stats["quads"]
    return bm, stats


def centre_of_mass_shift(spec: BarSpec) -> Tuple[float, dict]:
    """Bar-local x (mm) of the finished LOD0's volume centroid, and how it was found."""
    o = spec.outline(0.0)
    bm, stats = build_bar_bmesh(o, spec.lods[0])
    try:
        volume, centroid = bar_centroid(bm)
    finally:
        bm.free()
    return centroid[0] / MM, {"lod0_volume_mm3": volume / MM ** 3,
                              "centroid_bar_local_mm": [float(c) / MM for c in centroid],
                              "method": "divergence theorem over LOD0's own triangles, authored with the butt at x = 0"}


def author_bar_lod(o: BarOutline, lod: BarLodSpec, name: str, collection):
    """One spike LOD object.  Returns ``(obj, stats, lod)``; nothing is padded."""
    bm, stats = build_bar_bmesh(o, lod)
    stats["predicted_triangles"] = bar_triangles(lod)
    problems = hygiene_problems(stats)
    if stats["triangles"] != stats["predicted_triangles"]:
        problems.append(f"triangles {stats['triangles']} != predicted {stats['predicted_triangles']}")
    if problems:
        bm.free()
        raise RuntimeError(f"{name} failed its own hygiene gate on " + ", ".join(problems))
    if stats["triangles"] > lod.band[1]:
        bm.free()
        raise RuntimeError(f"{name}: {stats['triangles']} triangles is over its ceiling {lod.band}")
    layer = bm.faces.layers.int[FACE_CLASS_ATTR]
    ground = [1.0 if BAR_CLASSES[f[layer]] in GROUND_CLASSES else 0.0 for f in bm.faces]
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    # flat knife surfaces (the point facets, the tip flat; a K = 1 chamfer) are gated flat; the K >= 2 round is
    # smooth across its chords by design and reported like the senban's curved facets
    flat_codes = {BAR_CLASS_CODE["point"], BAR_CLASS_CODE["tip"]}
    if lod.arris_segments == 1:
        flat_codes.add(BAR_CLASS_CODE["round"])
    stats.update(knife_shading(mesh, flat_codes, drop_attribute=False))
    curved = knife_shading(mesh, {BAR_CLASS_CODE["round"]} if lod.arris_segments >= 2 else set(), drop_attribute=True)
    stats.update({"curved_facet_shading_max_dev_deg": curved["knife_shading_max_dev_deg"],
                  "curved_facet_max_warp_mm": curved["knife_face_max_warp_mm"],
                  "curved_facets_measured": curved["knife_faces_measured"]})
    attr = mesh.attributes.new(GROUND_ATTR, "FLOAT", "FACE")
    attr.data.foreach_set("value", np.asarray(ground, dtype=np.float32))
    nv = len(mesh.vertices)
    write_distance_attributes(mesh, np.zeros(nv), np.full(nv, NO_HOLE_DISTANCE), np.full(nv, NO_HOLE_DISTANCE))
    grind = mesh.attributes.get(GRIND_ATTR) or mesh.attributes.new(GRIND_ATTR, "FLOAT", "POINT")
    grind.data.foreach_set("value", np.zeros(nv, dtype=np.float32))
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.matrix_world = Matrix.Identity(4)
    return obj, stats, lod


# =========================================================================== hull, sockets, unwrap


def author_bar_hull(obj, o: BarOutline, index: int = 0):
    """``UCX_<obj.name>_NN``: the un-rounded bar itself (16 vertices: butt, tail base, point base, tip flat).

    The spike is convex, so its convex hull is the bar with square arrises: exactly C4, 28
    triangles, every LOD inside it (the round only removes material).  Built and parented like
    geometry.author_tip_prism_hull (hidden from render, identity matrices, ``ue_collision``).
    """
    name = f"UCX_{obj.name}_{index:02d}"
    if bpy.data.objects.get(name) is not None:
        raise ValueError(f"{name!r} already exists")
    stations = [(o.x_butt, o.e), (o.x_tail_base, o.a), (o.x_point_base, o.a), (o.x_tip, o.tau)]
    co = []
    for x, h in stations:
        co += [(x, h, h), (x, -h, h), (x, -h, -h), (x, h, -h)]
    faces = [(0, 1, 2), (0, 2, 3), (12, 14, 13), (12, 15, 14)]
    for s in range(3):
        b, t = 4 * s, 4 * (s + 1)
        for c in range(4):
            c1 = (c + 1) % 4
            faces += [(b + c, t + c, t + c1), (b + c, t + c1, b + c1)]
    coords = np.array(co, dtype=np.float64)
    mesh_co = np.array([v.co[:] for v in obj.data.vertices], dtype=np.float64)
    outside = hull_outside_distance(coords, faces, mesh_co)
    if outside > HULL_TOLERANCE:
        raise RuntimeError(f"{name}: the bar hull does not enclose {obj.name} ({outside / MM:.4f} mm outside)")
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


def _uv_group(normal) -> str:
    nx, ny, nz = normal
    if abs(nx) > 0.9:
        return "tip" if nx > 0.0 else "butt"
    if abs(nz) >= abs(ny):
        return "+z" if nz > 0.0 else "-z"
    return "+y" if ny > 0.0 else "-y"


def bar_unwrap(obj, island_margin: float) -> dict:
    """LOD0 UV0: one planar island per side of the bar, packed.

    Every face goes to the side its normal points at (the four faces with their point facet,
    tail facet and the half of each arris round on their side; the tip flat; the butt) and
    is projected along that side's normal: u along the bar, v across it (u x v = the outward
    normal, so no island is mirrored).  One planar projection per island is what the LOD1..n
    transfer needs (shuriken_lib.uv fits an exact affine map per island); Smart UV Project
    would split the rounds by its angle limit instead.  The islands are packed with the pack's
    packer settings (concave, free rotation, scaled margin).
    """
    mesh = obj.data
    if not mesh.uv_layers:
        mesh.uv_layers.new(name="UVMap")
    data = mesh.uv_layers[0].data
    counts: Dict[str, int] = {}
    for poly in mesh.polygons:
        key = _uv_group(poly.normal)
        counts[key] = counts.get(key, 0) + 1
        u_axis, v_axis = UV_FRAMES[key]
        for li in poly.loop_indices:
            co = mesh.vertices[mesh.loops[li].vertex_index].co
            data[li].uv = (co.x * u_axis[0] + co.y * u_axis[1] + co.z * u_axis[2],
                           co.x * v_axis[0] + co.y * v_axis[1] + co.z * v_axis[2])
    mesh.update()
    view_layer = bpy.context.view_layer
    for other in view_layer.objects:
        other.select_set(False)
    obj.select_set(True)
    view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(rotate=True, rotate_method="ANY", shape_method="CONCAVE",
                            margin_method="SCALED", margin=island_margin, scale=True)
    bpy.ops.object.mode_set(mode="OBJECT")
    obj.select_set(False)
    return {"method": ("shuriken_lib.bar.bar_unwrap: one planar projection per side (+-Z, +-Y faces with their "
                       "facets and half-rounds, the tip flat, the butt), u along the bar, then the pack's "
                       "pack_islands (concave, any rotation, scaled margin)"),
            "faces_per_island": counts, "island_margin": island_margin}


# =========================================================================== measurement


def c4_about_x_deviation(obj) -> float:
    """Max nearest-neighbour distance (mm) after a quarter turn of the stored vertices about +X."""
    co = np.array([v.co[:] for v in obj.data.vertices], dtype=np.float64)
    turned = np.column_stack((co[:, 0], -co[:, 2], co[:, 1]))
    worst = 0.0
    for point in turned:
        worst = max(worst, float(np.min(np.linalg.norm(co - point, axis=1))))
    return round(worst / MM, 9)


def mirror_deviation(obj, axis: int) -> float:
    co = np.array([v.co[:] for v in obj.data.vertices], dtype=np.float64)
    flip = np.ones(3)
    flip[axis] = -1.0
    mirrored = co * flip
    worst = 0.0
    for point in mirrored:
        worst = max(worst, float(np.min(np.linalg.norm(co - point, axis=1))))
    return round(worst / MM, 9)


def unground_bar(spec: BarSpec, shift_mm: float) -> dict:
    """The un-ground outline (square arrises, a sharp point, no tip flat) authored and measured: the mass gate."""
    o = spec.outline(shift_mm, sharp=True)
    bm, stats = build_bar_bmesh(o, BarLodSpec(arris_segments=0))
    try:
        volume, centroid = bar_centroid(bm)
    finally:
        bm.free()
    return {"volume_mm3": round(volume / MM ** 3, 6), "mass_g": round(volume / (0.01 ** 3) * spec.density_g_cm3, 6),
            "centroid_mm": [round(float(c) / MM, 6) for c in centroid], "triangles": stats["triangles"],
            "note": "same generator, arris_segments 0 and tip flat 0 (the pyramid runs to a point at 150 mm)"}


def measure_bar(obj, spec: BarSpec, o: BarOutline, lod: BarLodSpec) -> dict:
    """Build-to figures measured on the finished mesh (never copied from the spec)."""
    bm = evaluated_bm(obj)
    try:
        co = np.array([v.co[:] for v in bm.verts], dtype=np.float64)
        volume, centroid = bar_centroid(bm)
        min_edge = min(e.calc_length() for e in bm.edges)
        min_area = min(f.calc_area() for f in bm.faces)
        zero_edges = sum(1 for e in bm.edges if e.calc_length() <= DEGENERATE_EDGE)
        zero_faces = sum(1 for f in bm.faces if f.calc_area() <= DEGENERATE_AREA)
        facet_normals = [f.normal.copy() for f in bm.faces if f.normal.x > 0.05 and f.normal.x < 0.9]
        tail_normals = [f.normal.copy() for f in bm.faces if f.normal.x < -0.05 and f.normal.x > -0.9]
    finally:
        bm.free()
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    a = float(z.max())
    x0, x1 = float(x.min()), float(x.max())
    top = np.abs(z - a) < 1e-9
    top_x = x[top]
    tip = x > x1 - 1e-9
    butt = x < x0 + 1e-9
    face_half = float(np.abs(y[top]).max()) if top.any() else None     # the face's edge = the round's first chord
    x_tail_base, x_point_base = float(top_x.min()), float(top_x.max())
    facet_deg = [math.degrees(math.asin(min(1.0, abs(n.x)))) for n in facet_normals]
    tail_deg = [math.degrees(math.asin(min(1.0, abs(n.x)))) for n in tail_normals]
    tip_side = float(np.ptp(y[tip])) if tip.any() else 0.0
    plain = unground_bar(spec, o.shift / MM)
    masses = mass_figures(volume, plain["volume_mm3"] * MM ** 3, spec)
    length = x1 - x0
    middle = 0.5 * (x0 + x1)
    ue_radius = float(np.max(np.linalg.norm(co - np.array([middle, 0.5 * (y.max() + y.min()),
                                                           0.5 * (z.max() + z.min())]), axis=1)))
    return {
        "length_mm": round(length / MM, 6),
        "across_mm": round(length / MM, 6),
        "section_y_mm": round(float(np.ptp(y)) / MM, 6),
        "section_z_mm": round(float(np.ptp(z)) / MM, 6),
        "thickness_mm": round(float(np.ptp(z)) / MM, 6),
        "point_length_mm": round((x1 - x_point_base) / MM, 6),
        "tail_taper_mm": round((x_tail_base - x0) / MM, 6),
        "tail_end_mm": round(float(np.ptp(y[butt])) / MM, 6) if butt.any() else None,
        "tip_flat_mm": round(tip_side / MM, 6),
        "tip_radius_mm": round(0.5 * tip_side / MM, 6),
        "arris_round_mm": round((a - face_half) / MM, 6) if face_half is not None else None,
        "arris_segments": lod.arris_segments,
        "point_facet_angle_to_axis_deg": round(float(np.mean(facet_deg)), 5) if facet_deg else None,
        "point_facet_angle_spread_deg": round(float(np.ptp(facet_deg)), 6) if facet_deg else None,
        "point_included_deg": round(2.0 * float(np.mean(facet_deg)), 5) if facet_deg else None,
        "tail_facet_angle_to_axis_deg": round(float(np.mean(tail_deg)), 5) if tail_deg else None,
        "grind": {"grind_angle_deg": None, "edge_land_mm": None,
                  "tip_radius_mm": round(0.5 * tip_side / MM, 6), "tip_edge_height_mm": round(tip_side / MM, 6),
                  "note": ("a bar has no knife grind: the point is four flat ground facets ending in a square tip "
                           "flat (tip radius = half its side, the stars' 0.075 mm); the arrises carry a round")},
        "centre_of_mass_mm": [round(float(c) / MM, 6) for c in centroid],
        "centre_of_mass_from_butt_mm": round((0.0 - x0) / MM, 6),
        "centre_of_mass_from_middle_mm": round((0.0 - middle) / MM, 6),
        "centre_of_mass_note": ("the object origin is the centre of mass by volume (study 4); negative = toward the "
                                "butt: the 25 mm point removes more steel than the 20 mm tail taper"),
        "unreal_bounds_sphere_radius_mm": round(ue_radius / MM, 6),
        "volume_mm3": round(volume / MM ** 3, 4),
        "outline_volume_mm3": plain["volume_mm3"],
        "unground_bar": plain,
        **masses,
        "min_edge_mm": round(min_edge / MM, 6),
        "min_face_area_mm2": round(min_area / MM ** 2, 9),
        "zero_length_edges": zero_edges,
        "zero_area_faces": zero_faces,
        "coincident_vertices": coincident_pairs(co),
    }


def bar_topology_quality(obj) -> dict:
    """Face shapes (every triangle's smallest angle; long strips are inherent to a bar) and the C4 face check."""
    bm = evaluated_bm(obj)
    try:
        min_angle, under5, tris, aspects, cent = 180.0, 0, 0, [], []
        for face in bm.faces:
            co = [v.co.copy() for v in face.verts]
            for k in range(1, len(co) - 1):
                a, b, c = co[0], co[k], co[k + 1]
                tri = [math.degrees((b - a).angle(c - a)), math.degrees((a - b).angle(c - b)),
                       math.degrees((a - c).angle(b - c))]
                tris += 1
                min_angle = min(min_angle, min(tri))
                under5 += min(tri) < 5.0
            longest = max((co[k] - co[(k + 1) % len(co)]).length for k in range(len(co)))
            aspects.append(longest ** 2 / face.calc_area())
            m = face.calc_center_median()
            cent.append((m.x, m.y, m.z))
    finally:
        bm.free()
    cent = np.array(cent)
    turned = np.column_stack((cent[:, 0], -cent[:, 2], cent[:, 1]))
    misses = sum(1 for p in turned if float(np.min(np.linalg.norm(cent - p, axis=1))) > 1e-9)
    return {"faces": len(aspects), "triangles": tris, "min_triangle_angle_deg": round(min_angle, 4),
            "triangles_under_5deg": int(under5), "face_aspect_median": round(float(np.median(aspects)), 3),
            "face_aspect_max": round(float(max(aspects)), 3), "c4_face_misses": int(misses),
            "note": ("aspect = longest edge^2 / area.  The body faces and arris-round chords are single planar strips "
                     "tail base -> point base by design (a straight bar: nothing to subdivide); their slivers are "
                     "long, not degenerate (every triangle is well above qa_check's 1 um / 1 um2 thresholds)")}


# =========================================================================== the hook


class BarGeometry(FormGeometry):
    """FormGeometry of the throwing spike (study 2.5): C4 square bar along +X, rounded arrises, no hole."""

    kind = "bar"
    consistency_class = "bar"

    def __init__(self, spec: BarSpec) -> None:
        super().__init__(spec)
        shift_mm, self.com_method = centre_of_mass_shift(spec)
        self.shift_mm = shift_mm
        self.o = spec.outline(shift_mm)
        self.analytic = bar_analytic(spec)

    @property
    def order(self) -> int:
        return 4

    def validate(self) -> None:
        self.spec.validate()

    def build_to(self) -> dict:
        spec, o = self.spec, self.o
        return {
            "form": "bo-shuriken (straight square throwing spike), Katori / Meifu Shinkage pattern",
            "length_mm": spec.length_mm, "section_mm": spec.section_mm, "point_mm": spec.point_mm,
            "tail_taper_mm": spec.tail_taper_mm, "tail_end_mm": spec.tail_end_mm,
            "tip_flat_mm": spec.tip_flat_mm, "tip_radius_mm": 0.5 * spec.tip_flat_mm,
            "arris_round_mm": spec.arris_mm,
            "arris_round_definition": "radius of the round = Blender Bevel 'Offset' (0.3 mm from the old arris along each face)",
            "mass_g": spec.mass_target_g,
            "status": {"length": "SOURCED [8][12][13]", "section": "SOURCED [8][13] (6 mm, never the reseller's 8 mm)",
                       "point": "SOURCED [8]", "mass": "SOURCED [12][13]", "tail_taper": "ESTIMATE (study 2.5)",
                       "arris_round": "study 2.5 modelling plan (about 0.3 mm)",
                       "tip_flat": "the pack's tip radius (0.075 mm, the stars')"},
            "orientation": "long axis X, +X toward the point, lying on a flat face (faces normal to +-Y / +-Z)",
            "symmetry": "C4 about the long axis (and the D4 mirrors), not an array shape (study 4)",
            "pivot": "centre of mass by volume of the finished LOD0 (study 4, the spikes)",
            "centre_of_mass_from_butt_mm": round(self.shift_mm, 6),
            "point_included_deg": round(self.analytic["point_included_deg"], 5),
            "mass_gate": "outline (un-ground: square arrises, sharp point) mass within +-2 g of the target; finished mass reported",
            "analytic": {k: (round(v, 6) if isinstance(v, float) else v) for k, v in self.analytic.items()},
            "source": f"References/Shuriken/SHURIKEN_STUDY.md section {spec.study_section}",
        }

    def author(self, level: int, name: str, collection):
        return author_bar_lod(self.o, self.spec.lods[level], name, collection)

    def tag(self, obj) -> None:
        tag_bar(obj, self.o)

    def make_hull(self, lod0, options):
        hull = author_bar_hull(lod0, self.o, index=0)
        return hull, ("bar_prism: shuriken_lib.bar.author_bar_hull, the un-rounded bar itself (16 vertices: butt, "
                      "tail base, point base, tip flat; 28 triangles) - the spike is convex, so this is its exact "
                      "convex hull less the arris round; exactly C4, encloses every LOD")

    def make_sockets(self, lod0) -> None:
        o, spec = self.o, self.spec
        pipeline.make_socket(lod0, "Grip", (o.x_butt + spec.grip_from_butt_mm * MM, 0.0, 0.0),
                             rotation_euler=(0.0, 0.0, 0.0))
        pipeline.make_socket(lod0, "Trail", (o.x_butt, 0.0, 0.0), rotation_euler=(0.0, 0.0, 0.0))

    def density(self, lod_used) -> dict:
        o = self.o
        out = {"points": 4, "segments_along_the_body": 1,
               "why": "a straight bar: faces and rounds are single planar strips; the vertices are at the run-outs and the point",
               "per_lod": {}}
        for level, lod in enumerate(lod_used):
            k = lod.arris_segments
            out["per_lod"][f"LOD{level}"] = {"arris_segments": k, "triangles": bar_triangles(lod),
                                             **({kk: round(vv, 6) for kk, vv in o.runout_mm(k).items()} if k else {})}
        out.update({"x_butt_mm": o.x_butt / MM, "x_tail_base_mm": o.x_tail_base / MM,
                    "x_point_base_mm": o.x_point_base / MM, "x_tip_mm": o.x_tip / MM,
                    "point_slope": o.point_slope, "tail_slope": o.tail_slope})
        return out

    def wear_range(self):
        return self.o.x_tip - TIP_WEAR, self.o.x_tip

    def split_radius(self) -> float:
        return self.o.x_point_base

    def measure(self, obj, lod_used) -> dict:
        return measure_bar(obj, self.spec, self.o, lod_used)

    def topology_quality(self, obj) -> dict:
        return bar_topology_quality(obj)

    def render_outline(self):
        return self.o

    def island_margin(self, default: float) -> float:
        return default if self.spec.island_margin is None else self.spec.island_margin

    def custom_unwrap(self, obj, island_margin: float):
        return bar_unwrap(obj, island_margin)

    def symmetry_deviation(self, obj) -> float:
        return c4_about_x_deviation(obj)

    def symmetry_method(self) -> str:
        return ("max nearest-neighbour distance after a quarter turn ABOUT THE LONG AXIS (+X) of the stored "
                "(float32) vertices; quarter turns are trig-free sign swaps of 1 nm-snapped positions, so exact 0.0; "
                "mirror_max_deviation_mm does the same after mirrors in Y and Z")

    def symmetry_extra(self, lod_objects) -> Optional[dict]:
        return {"group": "D4 about +X", "axis": "+X (the long axis)",
                "mirror_max_deviation_mm": {obj.name: {"y": mirror_deviation(obj, 1), "z": mirror_deviation(obj, 2)}
                                            for obj in lod_objects}}

    def lod_note(self) -> str:
        return ("LODs are authored by the bar generator, not decimated: LOD0 rounds the four long arrises with 4 chords "
                "(radius 0.3 mm, smooth-shaded), LOD1 with 2 chords, LOD2 leaves them square; the point facets, the "
                "0.15 mm tip flat, the tail taper and the butt are the same planes on every LOD. max_surface_deviation_mm "
                "is two-sided; the split radius is the point base's distance from the origin, so 'hub_and_hole' reads "
                "as the body and 'arms' as the point and the tail taper.")

    def lod_strategy(self) -> dict:
        return {
            "method": "parametric: every LOD authored by shuriken_lib.bar at its own arris segment count",
            "table": ("study 4's rules for a bar (its star bands do not apply: a bar's LOD0 carries less shape than a "
                      "star's LOD2): LOD0 4-chord arris round, LOD1 2-chord round, LOD2 square arrises; the point, "
                      "tip flat, tail taper and butt identical on every LOD; nothing padded"),
            "bands": [list(lod.band) for lod in self.spec.lods],
            "naming": "LODn objects are created as <mesh>_LODn; pipeline.make_lod_group renames LOD0 with its "
                      "UCX_/SOCKET_ children, so the hull is UCX_<mesh>_LOD0_00",
        }

    def lod_switching_extra(self, report: dict) -> Optional[dict]:
        o = self.o
        ue_r = math.sqrt((0.5 * o.length) ** 2 + 2.0 * o.e ** 2) / MM
        from .spec import screen_size_distance_m
        sizes = list(self.spec.lod_screen_sizes[:len(self.spec.lods)])
        return {
            "scaled_for_bounding_radius": {
                "reference_radius_mm": 50.0,
                "form_radius_mm": round(ue_r, 4),
                "form_radius_definition": ("Unreal's bounds sphere radius: the largest vertex distance from the "
                                           "bounding-box CENTRE (sqrt(75^2 + 2 x 1.5^2), the butt corners), which is "
                                           "what ComputeBoundsScreenSize uses; bounds_radius_mm above is measured "
                                           "from the origin, the centre of mass, and is not"),
                "scaled_sizes": list(scaled_lod_screen_sizes(ue_r)),
                "switch_distance_m_at_unreal_radius": [None] + [round(screen_size_distance_m(s, ue_r * MM), 4)
                                                                for s in sizes[1:]],
                "note": ("the pack's 0.10 / 0.035 are for a ~50 mm star; S = 1.778 R / d, so the spike's 75.03 mm "
                         "bounding radius scales them by 1.5006 to keep the pack's switch distances (~0.89 m, ~2.54 m)"),
            },
        }


__all__ = ["BarGeometry", "author_bar_hull", "author_bar_lod", "bar_centroid", "bar_quadrant", "bar_topology_quality",
           "bar_unwrap", "build_bar_bmesh", "c4_about_x_deviation", "centre_of_mass_shift", "measure_bar",
           "mirror_deviation", "quarter", "unground_bar"]
