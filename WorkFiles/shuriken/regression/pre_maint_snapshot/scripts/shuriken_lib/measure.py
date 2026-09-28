"""Measurement: the report records what the finished mesh IS, never what was requested.

Every figure here is read back from the evaluated mesh (``evaluated_get(depsgraph)
.to_mesh()`` with ``to_mesh_clear()`` afterwards, the Blender 5.2 pattern).  Mass is the
correctness check for the outline (study 2.1: one real object, 39 g at 7.85 g/cm3).
"""
from __future__ import annotations

import math
from typing import Optional

import bmesh
import bpy
import numpy as np

from .geometry import DEGENERATE_AREA, DEGENERATE_EDGE, coincident_pairs
from .spec import MM, LodSpec, Outline, RadialStarSpec


def evaluated_bm(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
    finally:
        evaluated.to_mesh_clear()
    return bm


def triangles_of(obj) -> int:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        return len(mesh.loop_triangles)
    finally:
        evaluated.to_mesh_clear()


def vertices_of(obj) -> np.ndarray:
    bm = evaluated_bm(obj)
    try:
        return np.array([v.co[:] for v in bm.verts], dtype=np.float64)
    finally:
        bm.free()


def triangles_array(obj) -> np.ndarray:
    bm = evaluated_bm(obj)
    try:
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
        return np.array([[v.co[:] for v in f.verts] for f in bm.faces], dtype=np.float64)
    finally:
        bm.free()


def surface_samples(obj) -> np.ndarray:
    """Vertices, edge midpoints and triangle centroids: a surface sample, not just corners."""
    tris = triangles_array(obj)
    verts = vertices_of(obj)
    mids = np.concatenate([(tris[:, 0] + tris[:, 1]) * 0.5, (tris[:, 1] + tris[:, 2]) * 0.5,
                           (tris[:, 2] + tris[:, 0]) * 0.5])
    centroids = tris.mean(axis=1)
    return np.concatenate([verts, mids, centroids])


def surface_snapshot(obj, n: int) -> dict:
    """Volume, area and silhouette figures per LOD."""
    bm = evaluated_bm(obj)
    try:
        volume = bm.calc_volume(signed=True)
        area = sum(f.calc_area() for f in bm.faces)
        co = np.array([v.co[:] for v in bm.verts], dtype=np.float64)
    finally:
        bm.free()
    radial = np.hypot(co[:, 0], co[:, 1])
    angle = np.degrees(np.arctan2(co[:, 1], co[:, 0])) % 360.0
    window = 88.0 / n            # 22 deg either side of an arm on the four-point
    per_arm = []
    for k in range(n):
        centre = 360.0 * k / n
        delta = np.abs((angle - centre + 180.0) % 360.0 - 180.0)
        sel = radial[delta < window]
        per_arm.append(round(float(sel.max()) / MM, 6) if len(sel) else None)
    return {
        "volume_mm3": round(volume / (MM ** 3), 6),
        "surface_area_mm2": round(area / (MM ** 2), 6),
        "tip_radius_per_arm_mm": per_arm,
        "vertices": int(len(co)),
    }


def uv_coverage(obj, texture_size: int = 2048) -> dict:
    """UV square coverage and area-weighted texel density."""
    bm = evaluated_bm(obj)
    try:
        layer = bm.loops.layers.uv.active
        if layer is None:
            return {}
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
        uv_area = 0.0
        world_area = 0.0
        us, vs = [], []
        for face in bm.faces:
            uv = [tuple(loop[layer].uv) for loop in face.loops]
            us += [p[0] for p in uv]
            vs += [p[1] for p in uv]
            ax, ay = uv[1][0] - uv[0][0], uv[1][1] - uv[0][1]
            bx, by = uv[2][0] - uv[0][0], uv[2][1] - uv[0][1]
            uv_area += 0.5 * abs(ax * by - ay * bx)
            world_area += face.calc_area()
    finally:
        bm.free()
    if world_area <= 0.0:
        return {}
    texels_per_m = math.sqrt(uv_area * (texture_size ** 2) / world_area)
    return {
        "uv_square_coverage": round(uv_area, 6),
        "u_range": [round(min(us), 5), round(max(us), 5)],
        "v_range": [round(min(vs), 5), round(max(vs), 5)],
        "texture_size": texture_size,
        "texels_per_m": round(texels_per_m, 1),
        "px_per_cm": round(texels_per_m / 100.0, 3),
    }


def measure(obj, spec: RadialStarSpec, lod: LodSpec) -> dict:
    """Build-to figures measured on the finished mesh (LOD0 in the report's ``measured``)."""
    o: Outline = spec.outline()
    bm = evaluated_bm(obj)
    try:
        co = np.array([v.co[:] for v in bm.verts], dtype=np.float64)
        volume = bm.calc_volume(signed=True)
        min_edge = min(e.calc_length() for e in bm.edges)
        min_area = min(f.calc_area() for f in bm.faces)
        zero_edges = sum(1 for e in bm.edges if e.calc_length() <= DEGENERATE_EDGE)
        zero_faces = sum(1 for f in bm.faces if f.calc_area() <= DEGENERATE_AREA)
    finally:
        bm.free()

    radial = np.hypot(co[:, 0], co[:, 1])
    zs = co[:, 2]
    half_t = o.half_t
    volume_mm3 = volume / (MM ** 3)
    mass_g = (volume / (0.01 ** 3)) * spec.density_g_cm3   # m3 -> cm3 -> grams

    # Arm width, measured on the long edge of arm 0's parallel-sided run only (the
    # shoulder ring is excluded; LODs with a single straight interval fall back to it).
    local_angle = np.abs(np.arctan2(co[:, 1], co[:, 0]))
    on_arm0 = local_angle < o.half_sector
    edge_band = (np.abs(co[:, 1]) > o.half_w - 1.5 * MM) & (np.abs(co[:, 1]) <= o.half_w + 1.5 * MM)
    on_edge = on_arm0 & edge_band & (co[:, 0] >= o.r_hub + 1.0 * MM) & (co[:, 0] <= o.x_taper - 0.5 * MM)
    width_source = "parallel run"
    if not on_edge.any():
        on_edge = on_arm0 & edge_band & (np.abs(co[:, 0] - o.x_taper) < 1e-7)
        width_source = "shoulder ring"
    band = np.abs(co[on_edge, 1])
    # Bevel: the only vertices with |z| strictly between 0 and half_t are the facet.
    facet = (np.abs(zs) > 1e-9) & (np.abs(zs) < half_t - 1e-9)
    inter = np.abs(zs)[facet]
    bevel_z = float(half_t - inter.min()) if len(inter) else 0.0
    bevel_full = float(o.r_tip - radial[facet].min()) if len(inter) else 0.0
    # Hole: across-flats is the real opening, across-corners the circumscribed radius.
    hole_total = lod.hole_segments * o.n
    hole_r = radial[radial < 0.5 * (o.hole_polygon_radius(hole_total) + o.r_hub)] if lod.has_hole else radial[:0]
    flats = (round(2.0 * float(hole_r.min()) * math.cos(math.pi / hole_total) / MM, 6)
             if len(hole_r) else None)
    tip_sel = np.abs(zs)[radial > o.r_tip - 1e-7]
    hub_sel = radial[(radial > o.r_hub - 1.0 * MM) & (radial < o.r_hub + 0.5 * MM)]

    return {
        "across_mm": round((co[:, 0].max() - co[:, 0].min()) / MM, 6),
        "across_y_mm": round((co[:, 1].max() - co[:, 1].min()) / MM, 6),
        "thickness_mm": round((zs.max() - zs.min()) / MM, 6),
        "tip_radius_mm": round(float(radial.max()) / MM, 6),
        "hub_radius_mm": round(float(hub_sel.max()) / MM, 6) if len(hub_sel) else None,
        "hole_across_flats_mm": flats,
        "hole_mm": flats,
        "hole_across_corners_mm": round(2.0 * float(hole_r.max()) / MM, 6) if len(hole_r) else None,
        "hole_segments": hole_total,
        "arm_width_mm": round(2.0 * float(band.max()) / MM, 6) if len(band) else None,
        "arm_width_spread_mm": round((float(band.max()) - float(band.min())) * 2.0 / MM, 9)
        if len(band) else None,
        "arm_width_stations": int(len(band)),
        "arm_width_source": width_source,
        "tip_included_deg": spec.tip_included_deg,
        "bevel_offset_measured_mm": round(bevel_z / MM, 6),
        "bevel_offset_requested_mm": round(o.bevel_offset / MM, 6) if lod.has_bevel else 0.0,
        # The facet starts at the shoulder with zero width and opens over the run-out,
        # so "run" is the shoulder-to-tip distance and "full width from" is where it
        # reaches the full offset.  Study 2.1 asks for "the last 15 mm of each arm".
        "bevel_run_mm": round(o.taper_len / MM, 6) if lod.has_bevel else 0.0,
        "bevel_full_width_from_tip_mm": round(bevel_full / MM, 6),
        "bevel_segments": lod.bevel_segments,
        "flat_rim_band_mm": round((o.thickness - 2.0 * bevel_z) / MM, 6),
        "tip_edge_height_mm": round(2.0 * float(tip_sel.max()) / MM, 6) if len(tip_sel) else None,
        "volume_mm3": round(volume_mm3, 4),
        "plate_area_mm2": round(volume_mm3 / (o.thickness / MM), 4),
        "mass_g": round(mass_g, 4),
        "mass_target_g": spec.mass_target_g,
        "mass_error_g": round(mass_g - spec.mass_target_g, 4),
        "mass_within_tolerance": abs(mass_g - spec.mass_target_g) <= spec.mass_tolerance_g,
        "density_g_cm3": spec.density_g_cm3,
        "min_edge_mm": round(min_edge / MM, 6),
        "min_face_area_mm2": round(min_area / (MM ** 2), 9),
        "zero_length_edges": zero_edges,
        "zero_area_faces": zero_faces,
        "coincident_vertices": coincident_pairs(co),
    }


def surface_deviation(points: np.ndarray, tris: np.ndarray, chunk: int = 48) -> float:
    """Max distance from ``points`` to the closest point of the triangle soup ``tris``.

    This is the honest "did the LOD lose anything" number: comparing volume or surface
    area cannot see a silhouette that has moved, and comparing vertex sets reports a
    false failure whenever a coplanar interior was re-triangulated.
    """
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    ab, ac = b - a, c - a
    normal = np.cross(ab, ac)
    normal_len = np.linalg.norm(normal, axis=1)
    normal_len[normal_len == 0.0] = 1e-30
    d00 = np.einsum("mj,mj->m", ab, ab)
    d01 = np.einsum("mj,mj->m", ab, ac)
    d11 = np.einsum("mj,mj->m", ac, ac)
    denom = d00 * d11 - d01 * d01
    denom[denom == 0.0] = 1e-30

    def segment(point, s0, s1):
        direction = s1 - s0
        length2 = np.einsum("mj,mj->m", direction, direction)
        length2 = np.where(length2 == 0.0, 1e-30, length2)
        t = np.clip(np.einsum("kmj,mj->km", point - s0[None], direction) / length2, 0.0, 1.0)
        closest = s0[None] + t[..., None] * direction[None]
        return np.linalg.norm(point - closest, axis=-1)

    worst = 0.0
    for start in range(0, len(points), chunk):
        point = points[start:start + chunk][:, None, :]
        rel = point - a[None]
        d20 = np.einsum("kmj,mj->km", rel, ab)
        d21 = np.einsum("kmj,mj->km", rel, ac)
        v = (d11 * d20 - d01 * d21) / denom
        w = (d00 * d21 - d01 * d20) / denom
        inside = (v >= 0.0) & (w >= 0.0) & (v + w <= 1.0)
        plane = np.abs(np.einsum("kmj,mj->km", rel, normal)) / normal_len
        edges = np.minimum(np.minimum(segment(point, a, b), segment(point, b, c)),
                           segment(point, c, a))
        worst = max(worst, float(np.where(inside, plane, edges).min(axis=1).max()))
    return worst


def lod_deviation(lod0, other, split_radius: Optional[float] = None) -> dict:
    """LOD0-vs-LODn surface deviation, in mm.

    ``lod0_vertices_to_lod`` is rev 2's figure (max distance from a LOD0 vertex to the
    LODn surface) kept for comparison.  It is one-sided and corner-only, so it cannot see
    a LOD surface that bulges away between LOD0 vertices (an octagonal hole wall, say);
    ``two_sided`` samples vertices, edge midpoints and triangle centroids of each mesh
    against the other's surface and is the number to quote.  With ``split_radius`` (the
    hub radius) the two-sided figure is also split into the hub/hole region inside it and
    the arms outside it, so a report can say which feature the deviation comes from.
    """
    tris0, tris1 = triangles_array(lod0), triangles_array(other)
    rev2_metric = surface_deviation(vertices_of(lod0), tris1)
    samples0, samples1 = surface_samples(lod0), surface_samples(other)
    forward = surface_deviation(samples0, tris1)
    backward = surface_deviation(samples1, tris0)
    result = {
        "lod0_vertices_to_lod": round(rev2_metric / MM, 6),
        "lod0_surface_to_lod": round(forward / MM, 6),
        "lod_surface_to_lod0": round(backward / MM, 6),
        "two_sided": round(max(forward, backward) / MM, 6),
    }
    if split_radius is not None:
        def region(inner: bool) -> float:
            worst = 0.0
            for samples, tris in ((samples0, tris1), (samples1, tris0)):
                radial = np.hypot(samples[:, 0], samples[:, 1])
                pick = samples[radial < split_radius] if inner else samples[radial >= split_radius]
                if len(pick):
                    worst = max(worst, surface_deviation(pick, tris))
            return round(worst / MM, 6)
        result["two_sided_hub_and_hole"] = region(True)
        result["two_sided_arms"] = region(False)
        result["split_radius_mm"] = round(split_radius / MM, 6)
    return result


def cn_deviation(obj, n: int) -> float:
    """Max nearest-neighbour deviation after a 360/n rotation, in mm."""
    co = vertices_of(obj)
    if n == 4:
        rotated = np.column_stack((-co[:, 1], co[:, 0], co[:, 2]))
    else:
        c, s = math.cos(2.0 * math.pi / n), math.sin(2.0 * math.pi / n)
        rotated = np.column_stack((c * co[:, 0] - s * co[:, 1], s * co[:, 0] + c * co[:, 1], co[:, 2]))
    worst = 0.0
    for point in rotated:
        worst = max(worst, float(np.min(np.linalg.norm(co - point, axis=1))))
    return round(worst / MM, 9)


def unbevelled_plate_area_mm2(spec: RadialStarSpec, lod: LodSpec) -> dict:
    """Author ``lod`` again WITHOUT its ground bevel (bmesh only, no object) and measure it.

    The bridge between ``spec.analytic_area`` and the finished mesh: the un-bevelled mesh
    at the same hub, notch and hole counts must equal the analytic *polygonised* area to
    float precision, and what is left between it and the finished LOD0 is exactly the
    material the ground bevel removes.
    """
    from dataclasses import replace

    from .geometry import build_star_bmesh

    o = spec.outline()
    plain = replace(lod, bevel_segments=0, tip_intervals=0)
    bm, stats = build_star_bmesh(o, plain, lod.taper_intervals)
    try:
        volume = bm.calc_volume(signed=True)
    finally:
        bm.free()
    volume_mm3 = volume / (MM ** 3)
    return {
        "volume_mm3": round(volume_mm3, 6),
        "plate_area_mm2": round(volume_mm3 / spec.thickness_mm, 6),
        "mass_g": round(volume / (0.01 ** 3) * spec.density_g_cm3, 6),
        "triangles": stats["triangles"],
        "counts": {"columns": plain.columns, "notch_segments": plain.notch_segments,
                   "hole_segments": plain.hole_segments, "taper_intervals": plain.taper_intervals},
    }


def mesh_extents(obj) -> Optional[tuple]:
    co = vertices_of(obj)
    if not len(co):
        return None
    return tuple(float(v) for v in (co.max(axis=0) - co.min(axis=0)))


__all__ = ["cn_deviation", "evaluated_bm", "lod_deviation", "measure", "mesh_extents", "surface_deviation",
           "surface_samples", "surface_snapshot", "triangles_array", "triangles_of", "unbevelled_plate_area_mm2",
           "uv_coverage", "vertices_of"]
