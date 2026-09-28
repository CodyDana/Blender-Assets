"""Square-plate (senban) generator and its FormGeometry hook.

The first non-radial form.  It reuses the radial generator's vertex factory
(``geometry.Builder``: 1 nm snapped, wedge-keyed, seams welded by key, trig-free quarter
turns - so the plate is exactly C4 and a duplicate vertex cannot exist) and its zipper
(``geometry._zip_half``), and authors its own wedge: one corner of the square, -45..+45 deg.
The upper half-wedge is authored and the lower half is its exact mirror (y -> -y), so every
LOD is D4 by construction; points on the corner's axis are shared by both halves and points
on the 45 deg seams weld to the next wedge.

Per half wedge, inside out (see plate_spec for the contours):

    hole wall        the hole contour (fillet chords + the straight half side), top to bottom
    hole chamfer     hole contour (wall top) -> the contour offset by the deburr chamfer's width
    plate            hole (chamfer) contour -> rings -> plate edge, zipped band by band
    knife grind      plate edge -> facet contours -> wall top, quads (ChamferProfile.knife)
    outer wall       the concave edge's land, wall top to wall bottom (none on a land-0 LOD2)

Smoothing is decided by face class, as in the radial generator: a class per SIDE for the
wall and for each face's facet (so the two halves of a side, which meet tangentially at
the side midpoint, shade smoothly, and the corner - where two sides meet at 54 deg - stays
hard), one class for a filleted hole wall (per hole side when the corners are sharp), one
per plate face.
"""
from __future__ import annotations

import math
from dataclasses import asdict
from typing import Dict, List, Optional, Tuple

import bmesh
import bpy
import numpy as np
from mathutils import Matrix

import pipeline

from .geometry import (DEGENERATE_AREA, DEGENERATE_EDGE, NO_HOLE_DISTANCE, Builder, _zip_half, author_tip_prism_hull,
                       coincident_pairs, hygiene_problems, write_distance_attributes, write_grind_layer)
from .hooks import FormGeometry
from .material import TIP_WEAR, tag_common
from .measure import evaluated_bm, grind_figures, mass_figures
from .plate_spec import SQRT_HALF, PlateLodSpec, PlateOutline, SquarePlateSpec, plate_analytic_area, plate_triangles
from .spec import MM, scaled_lod_screen_sizes

SMOOTH_KINDS = {"plate", "facet", "wall", "hole", "holech"}


# =========================================================================== authoring


def _half_faces(inner_u: List[float], outer_u: List[float]):
    """Faces (('i'|'o', index), ...) of the band between two half contours, CCW from +Z."""
    return _zip_half(list(range(len(inner_u))), list(range(len(outer_u))), inner_u, outer_u, 0, 0)


def plate_wedge(bld: Builder, o: PlateOutline, lod: PlateLodSpec) -> None:
    """One corner wedge (-45..+45 deg) of the square plate, corner on +X."""
    turn = bld.turn
    side_upper, side_lower = turn, (turn - 1) % 4
    half_t = o.half_t
    K = lod.bevel_segments
    b = o.chamfer_w if lod.has_bevel else 0.0
    eu, hu = lod.edge_u(), lod.hole_u()
    z_hole = half_t - o.hole_chamfer.wall_top_drop if lod.has_hole_bevel else half_t

    def contour(points_xy, us, z):
        """(upper, lower) vertex index lists of a contour at height z (index 0 on the axis)."""
        upper, lower = [], []
        for (x, y), u in zip(points_xy, us):
            seam = u == 1.0
            upper.append(bld.add(x, y, z, seam=seam))
            lower.append(bld.add(x, -y, z, seam=seam))
        return upper, lower

    def band(inner, outer, inner_u, outer_u, cls_upper, cls_lower, flip=False):
        """Faces of one band in both halves; ``flip`` reverses the winding (bottom face)."""
        (iu, il), (ou, ol) = inner, outer
        for face in _half_faces(inner_u, outer_u):
            up = [(iu if ring == "i" else ou)[k] for ring, k in face]
            lo = [(il if ring == "i" else ol)[k] for ring, k in reversed(face)]
            if flip:
                up, lo = up[::-1], lo[::-1]
            bld.face(cls_upper, *up)
            bld.face(cls_lower, *lo)

    # --- plate contours: hole (or the hole chamfer's plate contour) -> rings -> plate edge (top and bottom)
    hole_xy = [o.hole_point(u, lod) for u in hu]
    edge_b = [o.edge_point(u, b) for u in eu]
    if lod.has_hole_bevel:
        plate_contours = [([o.hole_point(u, lod, o.hole_chamfer.width) for u in hu], hu)]
    else:
        plate_contours = [(hole_xy, hu)]
    for delta in lod.offsets_mm:
        plate_contours.append(([o.hole_point(u, lod, delta * MM) for u in hu], hu))
    base = lod.offsets_mm[-1] * MM if lod.offsets_mm else 0.0
    for samples, lam in lod.rings:
        us = lod.ring_u(samples)
        pts = []
        for u in us:
            hx, hy = o.hole_point(u, lod, base)
            ex, ey = o.edge_point(u, b)
            pts.append(((1.0 - lam) * hx + lam * ex, (1.0 - lam) * hy + lam * ey))
        plate_contours.append((pts, us))
    plate_contours.append((edge_b, eu))
    tops = [contour(pts, us, half_t) for pts, us in plate_contours]
    bots = [contour(pts, us, -half_t) for pts, us in plate_contours]
    for level in range(len(plate_contours) - 1):
        iu_, ou_ = plate_contours[level][1], plate_contours[level + 1][1]
        band(tops[level], tops[level + 1], iu_, ou_, ("plate", 1), ("plate", 1))
        band(bots[level], bots[level + 1], iu_, ou_, ("plate", -1), ("plate", -1), flip=True)

    # --- knife grind: plate edge -> facet contours -> wall top (same columns: quads)
    facet_top, facet_bot = [tops[-1]], [bots[-1]]
    for k in range(1, K + 1):
        s, z = o.facet_profile(k, K, lod)
        pts = [o.edge_point(u, s) for u in eu]
        facet_top.append(contour(pts, eu, z))
        facet_bot.append(contour(pts, eu, -z))
    for k in range(K):
        band(facet_top[k], facet_top[k + 1], eu, eu, ("facet", side_upper, 1), ("facet", side_lower, 1))
        band(facet_bot[k], facet_bot[k + 1], eu, eu, ("facet", side_upper, -1), ("facet", side_lower, -1),
             flip=True)

    # --- outer wall: the concave edge (wall top -> wall bottom)
    (wt_u, wt_l), (wb_u, wb_l) = facet_top[-1], facet_bot[-1]
    for j in range(len(eu) - 1):
        bld.face(("wall", side_upper), wt_u[j], wb_u[j], wb_u[j + 1], wt_u[j + 1])
        bld.face(("wall", side_lower), wt_l[j + 1], wb_l[j + 1], wb_l[j], wt_l[j])

    # --- hole chamfer (wall top contour -> the plate's first contour), then the hole wall
    if lod.has_hole_bevel:
        wall_top = contour(hole_xy, hu, z_hole)
        wall_bot = contour(hole_xy, hu, -z_hole)
        band(wall_top, tops[0], hu, hu, ("holech", 1), ("holech", 1))
        band(wall_bot, bots[0], hu, hu, ("holech", -1), ("holech", -1), flip=True)
        (ht_u, ht_l), (hb_u, hb_l) = wall_top, wall_bot
    else:
        (ht_u, ht_l), (hb_u, hb_l) = tops[0], bots[0]
    hole_upper = ("hole", 0) if lod.has_fillet else ("hole", side_upper)
    hole_lower = ("hole", 0) if lod.has_fillet else ("hole", side_lower)
    for j in range(len(hu) - 1):
        bld.face(hole_upper, ht_u[j], ht_u[j + 1], hb_u[j + 1], hb_u[j])
        bld.face(hole_lower, ht_l[j + 1], ht_l[j], hb_l[j], hb_l[j + 1])


def build_plate_bmesh(o: PlateOutline, lod: PlateLodSpec):
    """All four corner wedges through one shared vertex factory; smoothing baked by class."""
    bld = Builder(o.n)
    for turn in range(o.n):
        bld.turn = turn
        plate_wedge(bld, o, lod)

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
        edge.smooth = (len(linked) == 2 and face_class[linked[0]] == face_class[linked[1]]
                       and face_class[linked[0]][0] in SMOOTH_KINDS)
    grind_segments = write_grind_layer(bm, lambda f: face_class[f][0] == "plate", lambda f: face_class[f][0] == "facet")

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
        # a plate face whose normal points the wrong way after recalc is a folded (self-overlapping) band
        "folded_plate_faces": sum(1 for f in top if f.normal.z < 0.999) + sum(1 for f in bottom if f.normal.z > -0.999),
        "sharp_edges": sum(1 for e in bm.edges if not e.smooth),
        "knife_faces": sum(1 for f in bm.faces if face_class[f][0] == "facet"),
        "grind_line_segments": grind_segments,
        "signed_volume_m3": bm.calc_volume(signed=True),
        "min_edge_mm": min(e.calc_length() for e in bm.edges) / MM,
        "min_face_area_mm2": min(f.calc_area() for f in bm.faces) / (MM ** 2),
    }
    coords = np.array([v.co[:] for v in bm.verts], dtype=np.float64)
    stats["coincident_vertices"] = coincident_pairs(coords)
    stats["triangles"] = stats["tris"] + 2 * stats["quads"]
    return bm, stats


def author_plate_lod(o: PlateOutline, lod: PlateLodSpec, name: str, collection):
    """One square-plate LOD object.  Nothing is padded: the counts are the spec's.

    Returns ``(obj, stats, lod_used)`` like ``geometry.author_lod``.  A LOD over its ceiling,
    one that fails the hygiene gate, or one with a folded plate face is an error.
    """
    bm, stats = build_plate_bmesh(o, lod)
    stats["predicted_triangles"] = plate_triangles(lod)
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
    co = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", co)
    xy = co.reshape(-1, 3)[:, :2].astype(np.float64)
    write_distance_attributes(mesh, plate_outline_distance(o, xy), plate_hole_distance(o, xy))
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.matrix_world = Matrix.Identity(4)
    return obj, stats, lod


def plate_outline_distance(o: PlateOutline, xy: np.ndarray) -> np.ndarray:
    """Distance (m) from each XY point to the nearest concave side (the rim wall).

    The plate lies outside the four side circles, so inside the plate the distance to a side
    is |p - c_i| - rho and the outline distance is the smallest of the four (the corners are
    convex, so the minimum is exact everywhere in the plate).
    """
    x, y = xy[:, 0], xy[:, 1]
    q = o.centre_q
    best = None
    for cx, cy in ((q, q), (-q, q), (-q, -q), (q, -q)):
        d = np.hypot(x - cx, y - cy) - o.rho
        best = d if best is None else np.minimum(best, d)
    return np.maximum(best, 0.0)


def plate_hole_distance(o: PlateOutline, xy: np.ndarray) -> np.ndarray:
    """Distance (m) from each XY point to the square hole's flats (its fillets ignored)."""
    if o.hole_side <= 0.0:
        return np.full(len(xy), NO_HOLE_DISTANCE)
    # the hole's sides are parallel to the outer square, i.e. at 45 deg to the axes
    u = (np.abs(xy[:, 0] + xy[:, 1]) + np.abs(xy[:, 0] - xy[:, 1])) * (0.5 * math.sqrt(2.0))
    return np.maximum(u - o.hole_flat, 0.0)


# =========================================================================== measurement


def _fit_circle(points: np.ndarray):
    """Least-squares circle through 2D points: (cx, cy, r, max residual)."""
    x, y = points[:, 0], points[:, 1]
    A = np.column_stack([2.0 * x, 2.0 * y, np.ones(len(x))])
    rhs = x * x + y * y
    (cx, cy, c), *_ = np.linalg.lstsq(A, rhs, rcond=None)
    r = math.sqrt(c + cx * cx + cy * cy)
    residual = float(np.abs(np.hypot(x - cx, y - cy) - r).max())
    return float(cx), float(cy), r, residual


def measure_plate(obj, spec: SquarePlateSpec, lod: PlateLodSpec) -> dict:
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
        wall_verts, hole_verts = set(), set()
        split = 0.5 * (o.r_mid + o.hole_a)
        for f in bm.faces:
            if abs(f.normal.z) < 1e-6:
                radii = [math.hypot(v.co.x, v.co.y) for v in f.verts]
                if min(radii) > split:
                    wall_verts.update(v.index for v in f.verts)
                elif max(radii) < split:
                    hole_verts.update(v.index for v in f.verts)
    finally:
        bm.free()
    radial = np.hypot(co[:, 0], co[:, 1])
    zs = co[:, 2]
    half_t = float(zs.max())
    volume_mm3 = volume / MM ** 3
    mass_g = volume / (0.01 ** 3) * spec.density_g_cm3
    angle = np.degrees(np.arctan2(co[:, 1], co[:, 0]))

    # corners: the four farthest points, one per axis
    corner_idx = [int(np.argmax(np.where(np.abs(((angle - a + 180.0) % 360.0) - 180.0) < 1.0, radial, -1)))
                  for a in (0.0, 90.0, 180.0, -90.0)]
    corners = co[corner_idx]
    chords = [float(np.linalg.norm(corners[i, :2] - corners[(i + 1) % 4, :2])) for i in range(4)]
    # outer edge: wall vertices of side 0 (between the +X and +Y corners), fitted by a circle
    wall = co[sorted(wall_verts)] if wall_verts else co[:0]
    side0 = wall[(wall[:, 0] > -1e-9) & (wall[:, 1] > -1e-9)] if len(wall) else wall
    fit = _fit_circle(side0[:, :2]) if len(side0) >= 3 else None
    on_seam = np.abs(angle - 45.0) < 1e-4
    mid_r = float(radial[on_seam].max()) if on_seam.any() else None      # the side midpoint, on the wall
    included = None
    if fit is not None:
        cx, cy, r, _res = fit
        # tangent of the fitted arc at the +X corner, against the corner's axis
        tip = corners[0, :2]
        radius_dir = (tip - np.array([cx, cy])) / r
        tangent = np.array([-radius_dir[1], radius_dir[0]])
        included = 2.0 * math.degrees(math.acos(min(1.0, abs(float(tangent @ np.array([1.0, 0.0]))))))
    # hole: the hole-wall vertices; across flats from the side midpoints, the fillet from the axis apex
    hole_pts = co[sorted(hole_verts)] if hole_verts else co[:0]
    hole_r = np.hypot(hole_pts[:, 0], hole_pts[:, 1])
    hole_ang = np.degrees(np.arctan2(hole_pts[:, 1], hole_pts[:, 0]))
    flats = 2.0 * float(hole_r.min()) if len(hole_r) else None
    on_axis = np.abs(hole_ang) < 1e-4
    apex = float(hole_r[on_axis].max()) if on_axis.any() else None
    fillet = (o.hole_a - apex) / (math.sqrt(2.0) - 1.0) if apex is not None else None
    hole_corner_angle = float(hole_ang[int(np.argmax(hole_r))]) if len(hole_r) else None
    # knife grind: the land is twice the lowest |z| on the outline (the wall tops; 0 when the facets
    # meet in an edge line), the facet angle from the facet normals (grind_figures)
    edge_d = plate_outline_distance(o, co[:, :2])
    on_outline = edge_d < 1e-7
    land = 2.0 * float(np.abs(zs[on_outline]).min()) if on_outline.any() else None
    tip_z = np.abs(zs[radial > o.r_tip - 1e-7])
    seam_top = co[on_seam & (np.abs(zs - half_t) < 1e-9)]
    plate_edge_r = float(np.hypot(seam_top[:, 0], seam_top[:, 1]).max()) if len(seam_top) else None
    knife = o.knife_of(lod) if lod.has_bevel else None
    grind = {}
    if knife is not None:
        zone = plate_hole_distance(o, co[:, :2]) > 1e-3
        ang = np.arctan2(co[:, 1], co[:, 0])
        folded = np.abs(ang - np.round(ang / (0.5 * math.pi)) * (0.5 * math.pi))
        axis = (folded * radial < 1e-7) & (radial > o.edge_point(0.0, knife.width)[0] - 1e-7) & (zs > 0.0)
        ridge = np.column_stack([radial[axis], zs[axis]]) if axis.any() else None
        grind = grind_figures(co, face_verts, normals, areas, edge_d, knife.width, zone, o.r_tip, o.grind_angle_deg,
                              o.edge_land, ridge)
        grind["grind_width_mm"] = round(knife.width / MM, 6)
        grind["land_mode"] = "edge land" if lod.knife_land else "facets meet in a sharp edge line (land 0)"
    plain = unbevelled_plate(spec, lod)
    masses = mass_figures(volume, plain["volume_mm3"] * MM ** 3, spec)
    return {
        "across_mm": round((co[:, 0].max() - co[:, 0].min()) / MM, 6),
        "across_y_mm": round((co[:, 1].max() - co[:, 1].min()) / MM, 6),
        "corner_to_corner_mm": round(float(np.linalg.norm(corners[0, :2] - corners[2, :2])) / MM, 6),
        "thickness_mm": round((zs.max() - zs.min()) / MM, 6),
        "corner_radius_mm": round(float(radial.max()) / MM, 6),
        "tip_radius_mm": round(float(radial.max()) / MM, 6),
        "side_chord_mm": [round(c / MM, 6) for c in chords],
        "side_midpoint_radius_mm": round(mid_r / MM, 6) if mid_r is not None else None,
        "sagitta_mm": round(0.5 * float(np.mean(chords)) / MM - mid_r / MM, 6) if mid_r is not None else None,
        "side_arc_fit": ({"radius_mm": round(fit[2] / MM, 4), "centre_mm": [round(fit[0] / MM, 4), round(fit[1] / MM, 4)],
                          "max_residual_mm": round(fit[3] / MM, 6), "vertices": int(len(side0)),
                          "note": "circle fitted to the wall vertices of side 0 (they lie ON the arc)"}
                         if fit else None),
        "corner_included_deg": round(included, 4) if included is not None else None,
        "hole_across_flats_mm": round(flats / MM, 6) if flats is not None else None,
        "hole_mm": round(flats / MM, 6) if flats is not None else None,
        "hole_fillet_radius_mm": round(fillet / MM, 6) if fillet is not None and lod.has_fillet else 0.0,
        "hole_corner_angle_deg": round(hole_corner_angle, 4) if hole_corner_angle is not None else None,
        "hole_orientation": ("parallel: hole corners on the axes, pointing at the outer corners"
                             if hole_corner_angle is not None and abs(((hole_corner_angle + 45.0) % 90.0) - 45.0) < 1.0
                             else "diagonal"),
        "hole_wall_vertices": int(len(hole_pts)),
        "hole_across_corners_mm": round(2.0 * float(hole_r.max()) / MM, 6) if len(hole_r) else None,
        "grind": grind,
        "facet_plan_width_mm": round((mid_r - plate_edge_r) / MM, 6) if (mid_r and plate_edge_r and lod.has_bevel)
        else 0.0,
        "facet_drop_mm": round((half_t - 0.5 * land) / MM, 6) if land is not None else 0.0,
        "facet_segments": lod.bevel_segments,
        "edge_land_mm": round(land / MM, 6) if land is not None else round(2.0 * half_t / MM, 6),
        "tip_edge_height_mm": round(2.0 * float(tip_z.max()) / MM, 6) if len(tip_z) else None,
        "edge_intervals_per_half_side": lod.edge_intervals,
        "hole_chamfer_mm": round(o.hole_chamfer.width / MM, 6) if lod.has_hole_bevel else 0.0,
        "volume_mm3": round(volume_mm3, 4),
        "plate_area_mm2": round(volume_mm3 / (o.thickness / MM), 4),
        "outline_volume_mm3": plain["volume_mm3"],
        "outline_plate_area_mm2": plain["plate_area_mm2"],
        **masses,
        "min_edge_mm": round(min_edge / MM, 6),
        "min_face_area_mm2": round(min_area / MM ** 2, 9),
        "zero_length_edges": zero_edges,
        "zero_area_faces": zero_faces,
        "coincident_vertices": coincident_pairs(co),
    }


def plate_topology_quality(obj, o: PlateOutline) -> dict:
    """Face-shape figures of the flat plate faces (the wireframe review) and every triangle.

    ``plate_aspect``: longest edge squared over area of every top-plate face (a square is 1, an
    equilateral triangle 2.31).  ``plate_mirror_misses``: top faces whose mirror image about the
    corner axis (y -> -y) is not a face - zero on a D4 mesh.  Triangle angles are over the fan
    triangulation of every face.
    """
    bm = evaluated_bm(obj)
    try:
        half_t = max(v.co.z for v in bm.verts)
        aspects, keys = [], []
        min_angle, under5, tris = 180.0, 0, 0
        plate_min, plate_under5, strip_under5 = 180.0, 0, 0
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
                else:
                    strip_under5 += min(tri) < 5.0
            if all(abs(v.co.z - half_t) < 1e-9 for v in face.verts):
                longest = max((co[k] - co[(k + 1) % len(co)]).length for k in range(len(co)))
                aspects.append(longest ** 2 / face.calc_area())
                centre = face.calc_center_median()
                keys.append((float(centre.x), float(centre.y), len(co)))
    finally:
        bm.free()
    cent = np.array([(x, y) for x, y, _k in keys]) if keys else np.zeros((0, 2))
    sizes = np.array([k for _x, _y, k in keys])
    misses = 0
    for (x, y), size in zip(cent, sizes):
        d = np.hypot(cent[:, 0] - x, cent[:, 1] + y)
        misses += not np.any((d < 1e-7) & (sizes == size))
    return {
        "plate_top_faces": len(aspects),
        "plate_aspect_median": round(float(np.median(aspects)), 3) if aspects else None,
        "plate_aspect_max": round(float(max(aspects)), 3) if aspects else None,
        "plate_faces_aspect_over_8": int(sum(a > 8.0 for a in aspects)),
        "plate_mirror_misses": int(misses),
        "plate_min_triangle_angle_deg": round(plate_min, 3),
        "plate_triangles_under_5deg": int(plate_under5),
        "strip_triangles_under_5deg": int(strip_under5),
        "min_triangle_angle_deg": round(min_angle, 3),
        "triangles_under_5deg": int(under5),
        "triangles": tris,
        "note": ("plate_* are the flat top and bottom faces (where a fan of slivers would show); strips are the "
                 "facet, outer wall and hole wall, long thin quads along the edge by construction"),
    }


def mirror_deviation(obj) -> float:
    """Max nearest-neighbour distance (mm) after mirroring the stored vertices about the X axis."""
    co = np.array([v.co[:] for v in obj.data.vertices], dtype=np.float64)
    mirrored = co * np.array([1.0, -1.0, 1.0])
    worst = 0.0
    for point in mirrored:
        worst = max(worst, float(np.min(np.linalg.norm(co - point, axis=1))))
    return round(worst / MM, 9)


def unbevelled_plate(spec: SquarePlateSpec, lod: PlateLodSpec) -> dict:
    """``lod`` authored again WITHOUT its facet (bmesh only) and measured: the polygonised plate."""
    from dataclasses import replace
    o = spec.outline()
    plain = replace(lod, bevel_segments=0, hole_bevel=False, knife_land=True)
    bm, stats = build_plate_bmesh(o, plain)
    try:
        volume = bm.calc_volume(signed=True)
    finally:
        bm.free()
    volume_mm3 = volume / MM ** 3
    return {"volume_mm3": round(volume_mm3, 6), "plate_area_mm2": round(volume_mm3 / spec.thickness_mm, 6),
            "mass_g": round(volume / (0.01 ** 3) * spec.density_g_cm3, 6), "triangles": stats["triangles"]}


# =========================================================================== the hook


class SquarePlateGeometry(FormGeometry):
    """FormGeometry of the senban (study 2.3): D4 square plate, concave sides, square hole."""

    kind = "square_plate"

    def __init__(self, spec: SquarePlateSpec) -> None:
        super().__init__(spec)
        self.o = spec.outline()

    @property
    def order(self) -> int:
        return 4

    def validate(self) -> None:
        self.spec.validate()

    def build_to(self) -> dict:
        spec, o = self.spec, self.o
        return {
            "points": 4,
            "side_mm": spec.side_mm,
            "corner_to_corner_mm": round(o.r_tip * 2.0 / MM, 4),
            "corner_to_corner_study_rounded_mm": 108.0,
            "thickness_mm": spec.thickness_mm,
            "sagitta_mm": spec.sagitta_mm,
            "arc_radius_mm": round(o.rho / MM, 4),
            "side_midpoint_radius_mm": round(o.r_mid / MM, 4),
            "corner_included_deg": round(2.0 * math.degrees(o.corner_half_angle), 4),
            "hole_side_mm": spec.hole_side_mm,
            "hole_orientation": spec.hole_orientation,
            "hole_fillet_mm": spec.hole_fillet_mm,
            "edge_grind": spec.edge_grind,
            "grind": "knife: both faces, every concave side, to an edge land",
            "grind_angle_deg": spec.grind_angle_deg,
            "edge_land_mm": spec.edge_land_mm,
            "grind_width_mm": round(o.chamfer_w / MM, 4),
            "grind_depth_mm": round(o.chamfer.depth / MM, 4),
            "chamfer_width_mm": round(o.chamfer_w / MM, 4),
            "chamfer_wall_top_drop_mm": round(o.chamfer.wall_top_drop / MM, 4),
            "hole_chamfer_mm": spec.hole_chamfer_mm,
            "hole_chamfer_deg": spec.hole_chamfer_deg,
            "mass_g": spec.mass_target_g,
            "mass_gate": "outline (un-ground plate) mass within +-2 g of the target; ground mass reported",
            "source": f"References/Shuriken/SHURIKEN_STUDY.md section {spec.study_section}",
        }

    def author(self, level: int, name: str, collection):
        return author_plate_lod(self.o, self.spec.lods[level], name, collection)

    def tag(self, obj) -> None:
        # the "hub" of a plate is its inscribed circle (the side midpoints); no scallops; grime gathers
        # toward the hole over ~half the inscribed radius; two rust specks on the plate, off the hole
        o = self.o
        r1, r2 = 0.52 * o.r_mid, 0.40 * o.r_mid
        tag_common(obj, points=4, r_tip=o.r_tip, r_hub=o.r_mid, chamfer_w=o.chamfer_w, scallop_w=0.0,
                   hole_w=o.hole_chamfer.width, centre_r=0.70 * o.r_mid,
                   rust=((r1 * math.cos(math.radians(24.0)), r1 * math.sin(math.radians(24.0)), 1.0, 0.00030),
                         (r2 * math.cos(math.radians(213.0)), r2 * math.sin(math.radians(213.0)), -1.0, 0.00022)))

    def make_hull(self, lod0, options):
        hull = author_tip_prism_hull(lod0, self.o, index=0)
        return hull, ("tip_prism: shuriken_lib.geometry.author_tip_prism_hull, the square prism through the four "
                      "corners at full plate thickness - the plate's exact convex hull in plan (the sides are "
                      "concave), exactly C4, encloses LOD0")

    def make_sockets(self, lod0) -> None:
        o = self.o
        q = o.r_mid * SQRT_HALF          # side 0's midpoint, ON the rim (the sagitta inward of the chord)
        pipeline.make_socket(lod0, "Grip", (q, q, 0.0), rotation_euler=(0.0, 0.0, 0.25 * math.pi))
        pipeline.make_socket(lod0, "Trail", (0.0, 0.0, 0.0), rotation_euler=(0.0, 0.0, 0.0))

    def density(self, lod_used) -> dict:
        lod = lod_used[0]
        o = self.o
        return {
            "points": 4,
            "EDGE_INTERVALS_PER_HALF_SIDE": lod.edge_intervals,
            "edge_chords_total": 8 * lod.edge_intervals,
            "FILLET_SEGMENTS_PER_HALF_CORNER": lod.fillet_segments,
            "fillet_chords_total": 8 * lod.fillet_segments,
            "HOLE_INTERVALS": lod.hole_intervals,
            "BEVEL_SEGMENTS": lod.bevel_segments,
            "plate_contours": ("hole " + str(lod.contour_intervals()[0]) + " -> "
                               + "".join(f"offset {d} mm -> " for d in lod.offsets_mm)
                               + " -> ".join(f"ring {len(lod.ring_u(s)) - 1} at lam {lam}" for s, lam in lod.rings)
                               + (" -> " if lod.rings else "") + f"plate edge {lod.edge_intervals} (per half side)"),
            "arc_radius_mm": o.rho / MM,
            "edge_chord_sagitta_mm": o.rho * (1.0 - math.cos(0.5 * (0.5 * self._arc_angle()) / lod.edge_intervals)) / MM,
            "mitre_point_from_tip_mm": (o.r_tip - o.edge_point(0.0, o.chamfer_w)[0]) / MM,
        }

    def _arc_angle(self) -> float:
        return 2.0 * math.asin(0.5 * self.o.side / self.o.rho)

    def wear_range(self):
        return self.o.r_tip - TIP_WEAR, self.o.r_tip

    def split_radius(self) -> float:
        # the hole region: everything inside the hole's corner radius plus the first ring's reach
        return 1.5 * self.o.hole_a

    def measure(self, obj, lod_used) -> dict:
        return measure_plate(obj, self.spec, lod_used)

    def topology_quality(self, obj) -> dict:
        return plate_topology_quality(obj, self.o)

    def render_outline(self):
        return self.o

    island_margin_reason = (
        "LOD2 has no facet, so its top plate runs to the edge and its 4-chord sides sit outside the concave "
        "arc: up to ~1.1 mm (~15 px at 2048) past LOD0's top-plate island. At the pack's 0.005 that grazed the "
        "hole-wall island packed beside it (1 overlapping UV pair on LOD2); at 0.008 the transfer's clamp "
        "moved a LOD2 plate corner 1.8 px (cross-LOD gate 0.5 px); at 0.012 both gates pass with 0.5 pt less "
        "coverage.")

    def island_margin(self, default: float) -> float:
        return default if self.spec.island_margin is None else self.spec.island_margin

    def symmetry_method(self) -> str:
        return ("max nearest-neighbour distance after a 90 deg rotation of the stored (float32) vertices "
                "(quarter turns are trig-free, so exact 0.0); mirror_max_deviation_mm does the same after a "
                "mirror about the corner axis (y -> -y): D4, both exact by construction")

    def symmetry_extra(self, lod_objects) -> Optional[dict]:
        return {"group": "D4", "mirror_max_deviation_mm": {obj.name: mirror_deviation(obj) for obj in lod_objects}}

    def lod_note(self) -> str:
        return ("LODs are authored by the square-plate generator at reduced counts, not decimated: LOD1 halves "
                "the edge chords, the fillet chords and the facet segments; LOD2 drops the facet and the fillets "
                "but KEEPS a plain square hole (the form's defining feature, ~5 px across at the LOD2 switch). "
                "max_surface_deviation_mm is two-sided; the split is the hole region (inside 1.5 x the hole "
                "corner radius) against the rest of the plate.")

    def lod_strategy(self) -> dict:
        return {
            "method": "parametric: every LOD authored by shuriken_lib.plate at its own counts",
            "table": ("study 4's LOD rules adapted to a plate (its bands are for stars): LOD0 full silhouette, "
                      "facet and filleted hole; LOD1 edge / fillet chords and facet segments halved; LOD2 facet "
                      "and fillets dropped, the square hole kept; nothing padded"),
            "naming": "LODn objects are created as <mesh>_LODn; pipeline.make_lod_group renames LOD0 with its "
                      "UCX_/SOCKET_ children, so the hull is UCX_<mesh>_LOD0_00",
        }

    def lod_switching_extra(self, report: dict) -> Optional[dict]:
        return {
            "scaled_for_bounding_radius": {
                "reference_radius_mm": 50.0,
                "form_radius_mm": round(self.o.r_tip / MM, 4),
                "scaled_sizes": list(scaled_lod_screen_sizes(self.o.r_tip / MM)),
                "note": ("the pack's 0.10 / 0.035 are for a ~50 mm star; S = 1.778 R / d, so the senban's "
                         "53.88 mm corner radius scales them by 1.0776 to keep the pack's switch distances "
                         "(~0.89 m and ~2.54 m)"),
            },
        }


__all__ = ["SquarePlateGeometry", "author_plate_lod", "build_plate_bmesh", "measure_plate", "mirror_deviation",
           "plate_hole_distance", "plate_outline_distance", "plate_topology_quality", "plate_wedge",
           "unbevelled_plate"]
