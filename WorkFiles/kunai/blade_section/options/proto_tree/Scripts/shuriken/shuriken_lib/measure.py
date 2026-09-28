"""Measurement: the report records what the finished mesh IS, never what was requested.

Every figure here is read back from the evaluated mesh (``evaluated_get(depsgraph)
.to_mesh()`` with ``to_mesh_clear()`` afterwards, the Blender 5.2 pattern).  Mass is the
correctness check for the OUTLINE (study 2.1: one real object, 39 g at 7.85 g/cm3), so since
the knife grind pass it is evaluated on the un-ground plate - the same outline authored without
any grind, i.e. outline x thickness, which the grind does not change - and the ground (finished)
mass is reported beside it as a finish property against the study's min-max range
(``mass_figures``).  ``grind_figures`` measures the knife grind itself on the mesh: the facet
angle from the facet normals, the edge land from the outline vertices, the run-out, and the
point (vertical edge height, the tip radius as half of it, and the ridges' included angle).
"""
from __future__ import annotations

import math
from typing import Optional

import bmesh
import bpy
import numpy as np

from .geometry import DEGENERATE_AREA, DEGENERATE_EDGE, coincident_pairs
from .spec import MM, LodSpec, Outline, RadialStarSpec


def mass_figures(ground_volume_m3: float, outline_volume_m3: float, spec) -> dict:
    """The mass gate on the un-ground plate and the ground mass as a finish property."""
    density = spec.density_g_cm3
    outline_g = outline_volume_m3 / (0.01 ** 3) * density
    ground_g = ground_volume_m3 / (0.01 ** 3) * density
    rng = getattr(spec, "study_mass_range_g", None)
    typical = getattr(spec, "study_mass_typical_g", None)
    out = {
        "mass_g": round(ground_g, 4),
        "ground_mass_g": round(ground_g, 4),
        "outline_mass_g": round(outline_g, 4),
        "grind_removes_g": round(outline_g - ground_g, 4),
        "mass_target_g": spec.mass_target_g,
        "mass_error_g": round(outline_g - spec.mass_target_g, 4),
        "mass_within_tolerance": abs(outline_g - spec.mass_target_g) <= spec.mass_tolerance_g,
        "mass_gate": {
            "evaluated_on": ("the UN-GROUND plate: the same outline authored with no grind, chamfer or deburr "
                             "(outline x thickness), which the knife grind does not change"),
            "outline_mass_g": round(outline_g, 4), "target_g": spec.mass_target_g,
            "tolerance_g": spec.mass_tolerance_g,
            "passed": abs(outline_g - spec.mass_target_g) <= spec.mass_tolerance_g,
            "why": ("the study mass gate proves the OUTLINE proportions match a real sourced object; the grind is a "
                    "finish, so the finished (ground) mass is reported, not gated"),
        },
        "ground_mass_vs_study_range": {
            "ground_mass_g": round(ground_g, 4),
            "study_min_max_g": list(rng) if rng else None,
            "study_typical_g": list(typical) if typical else None,
            "within_min_max": (rng[0] <= ground_g <= rng[1]) if rng else None,
            "within_typical": (typical[0] <= ground_g <= typical[1]) if typical else None,
            "note": "reported, not gated (decision B)",
        },
        "density_g_cm3": density,
    }
    return out


def _tilt_stats(tilts: np.ndarray, areas: np.ndarray) -> dict:
    if not len(tilts):
        return {}
    return {"area_weighted_mean": round(float((tilts * areas).sum() / areas.sum()), 4),
            "min": round(float(tilts.min()), 4), "max": round(float(tilts.max()), 4), "faces": int(len(tilts))}


def grind_figures(co: np.ndarray, face_verts, normals: np.ndarray, areas: np.ndarray, edge_dist: np.ndarray,
                  knife_width: float, knife_zone: np.ndarray, tip_radius: float, spec_angle: float,
                  spec_land: float, ridge=None) -> dict:
    """The knife grind measured on the mesh (metres in, millimetres / degrees out).

    ``edge_dist`` is the plan distance of every VERTEX to the outline, ``knife_zone`` a per-vertex
    mask of the cutting edges (the stars: arm-local x past the root run-out, off the scallops
    and the hole).  Facets: faces whose every vertex is in the knife zone and within the grind
    width of the outline and whose normal is neither the plate's nor a wall's; the angle is
    their tilt from the plate normal.  Land: twice |z| of the outline (wall-top) vertices in the
    knife zone.  Point: the vertices at the tip radius - their vertical extent is the point's
    edge, the tip radius is half of it (the point is exactly sharp in plan: the silhouette is
    unchanged); ``ridge`` (x, z) samples along the point's axis give the ridges' included angle.
    """
    faces_in = []
    for f, verts in enumerate(face_verts):
        nz = abs(normals[f][2])
        if not 0.05 < nz < 0.98:
            continue
        idx = np.asarray(verts)
        if knife_zone[idx].all() and (edge_dist[idx] <= knife_width + 1e-7).all():
            faces_in.append(f)
    faces_in = np.array(faces_in, dtype=np.int64)
    tilts = np.degrees(np.arccos(np.clip(np.abs(normals[faces_in, 2]), 0.0, 1.0))) if len(faces_in) else np.zeros(0)
    main = tilts > 5.0
    outline = (edge_dist < 1e-7) & knife_zone
    lands = 2.0 * np.abs(co[outline, 2]) if outline.any() else np.zeros(0)
    radial = np.hypot(co[:, 0], co[:, 1])
    tip = radial > tip_radius - 1e-7
    tip_edge = 2.0 * float(np.abs(co[tip, 2]).max()) if tip.any() else None
    out = {
        "grind_angle_deg": _tilt_stats(tilts[main], areas[faces_in][main]) if len(faces_in) else {},
        "grind_angle_spec_deg": spec_angle,
        "edge_land_mm": ({"min": round(float(lands.min()) / MM, 6), "max": round(float(lands.max()) / MM, 6),
                          "median": round(float(np.median(lands)) / MM, 6), "outline_vertices": int(outline.sum())}
                         if len(lands) else {}),
        "edge_land_spec_mm": round(spec_land / MM, 6),
        "tip_edge_height_mm": round(tip_edge / MM, 6) if tip_edge is not None else None,
        "tip_radius_mm": round(0.5 * tip_edge / MM, 6) if tip_edge is not None else None,
        "tip_radius_definition": ("radius of the smallest circle holding the point's end in the vertical section "
                                  "through the point's axis (half the vertical edge the two lands leave there); "
                                  "in plan the point is exactly sharp - the silhouette is unchanged"),
    }
    if ridge is not None and len(ridge) >= 2:
        xs, zs = np.asarray(ridge)[:, 0], np.asarray(ridge)[:, 1]
        slope = abs(float(np.polyfit(xs, zs, 1)[0])) if np.ptp(xs) > 0 else 0.0
        out["tip_ridge_included_deg"] = round(2.0 * math.degrees(math.atan(slope)), 4)
    out["grind_angle_within_spec"] = bool(out["grind_angle_deg"]) and abs(
        out["grind_angle_deg"]["area_weighted_mean"] - spec_angle) < 0.5
    out["edge_land_within_0_25"] = bool(out["edge_land_mm"]) and out["edge_land_mm"]["max"] <= 0.25 + 1e-6
    return out


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


def uv_coverage(obj, texture_size=2048) -> dict:
    """UV square coverage and area-weighted texel density.

    ``texture_size`` is an int (a square map) or, since 3.8.1, a (width, height) pair (the spike's 2048 x 512):
    the density is then sqrt(uv_area x width x height / world area), texels per metre on the map."""
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
    if isinstance(texture_size, (tuple, list)):
        texels_per_m = math.sqrt(uv_area * texture_size[0] * texture_size[1] / world_area)
        texture_size = [int(texture_size[0]), int(texture_size[1])]
    else:
        texels_per_m = math.sqrt(uv_area * (texture_size ** 2) / world_area)
    return {
        "uv_square_coverage": round(uv_area, 6),
        "u_range": [round(min(us), 5), round(max(us), 5)],
        "v_range": [round(min(vs), 5), round(max(vs), 5)],
        "texture_size": texture_size,
        "texels_per_m": round(texels_per_m, 1),
        "px_per_cm": round(texels_per_m / 100.0, 3),
    }


def _arm_local(co: np.ndarray, n: int, k: int) -> np.ndarray:
    """``co`` rotated by -k n-th turns, so arm k lies on +X."""
    angle = -2.0 * math.pi * k / n
    c, s = math.cos(angle), math.sin(angle)
    return np.column_stack((c * co[:, 0] - s * co[:, 1], s * co[:, 0] + c * co[:, 1], co[:, 2]))


def taper_and_bevel(co: np.ndarray, faces, normals: np.ndarray, o: Outline, half_width: float) -> dict:
    """Tip angle fitted to the actual taper edges, and the chamfer measured in arm-local x / y.

    Per arm: the outline is the largest |y| at each x station (the wall top); stations
    narrower than the measured parallel run are the taper, and a straight line is fitted
    to each edge (the included angle is the sum of the two edge angles).  The chamfer is
    every face whose normal is neither the plate's nor a wall's (0.02 < |N.z| < 0.98): its
    plan width is the wall-top outline minus the plate edge on the parallel run (exact,
    perpendicular to the edge) and, on the taper, the same difference times cos(half tip)
    at every station where both a wall-top and a plate vertex exist; its depth is the wall
    top's drop below the plate face; it starts at the smallest arm-local x of a facet vertex.
    """
    n = o.n
    half_t = float(np.abs(co[:, 2]).max())
    angles, residuals, shoulders, starts, drops, run_widths, taper_insets = [], [], [], [], [], [], []
    facet_faces = [f for f, nrm in zip(faces, normals) if 0.02 < abs(nrm[2]) < 0.98]
    facet_verts = np.unique(np.concatenate([np.asarray(f) for f in facet_faces])) if facet_faces else np.zeros(0, int)
    # The outline is traced by the wall-top vertices only: with a chamfer they sit below the
    # plate by the wall top's drop (the mitred shoulder ring puts chamfer vertices at other x
    # and y, which must not be read as outline points).
    z_wall = float(np.abs(co[facet_verts, 2]).min()) if len(facet_verts) else half_t
    for k in range(n):
        local = _arm_local(co, n, k)
        in_arm = (np.abs(np.arctan2(local[:, 1], local[:, 0])) < o.half_sector) & (local[:, 0] > o.r_hub + 0.5 * MM)
        pts = local[in_arm]
        if not len(pts):
            continue
        xs = np.round(pts[:, 0] / 1e-7).astype(np.int64)
        edges = {}
        plate_edges = {}
        for key, (x, y, z) in zip(xs, pts[:, :3]):
            if abs(abs(z) - z_wall) < 1e-9:
                lo, hi = edges.get(key, (math.inf, -math.inf))
                edges[key] = (min(lo, y), max(hi, y))
            if abs(abs(z) - half_t) < 1e-9:
                plate_edges[key] = max(plate_edges.get(key, 0.0), abs(y))
        # plan width on the parallel run: the arm half width minus the plate's half width there
        # (past the root run-out: before it the grind is still narrowing into the scallop chamfer)
        run_plate = local[(np.abs(np.abs(local[:, 2]) - half_t) < 1e-9) & (local[:, 0] > o.x_run - 1e-6)
                          & (local[:, 0] < o.x_taper + 1e-6) & (np.abs(local[:, 1]) < half_width - 1e-9)]
        if len(run_plate) and len(facet_verts):
            run_widths.append(half_width - float(np.abs(run_plate[:, 1]).max()))
        taper = [(key * 1e-7, lo, hi) for key, (lo, hi) in sorted(edges.items()) if hi < half_width - 1e-7]
        if len(taper) >= 2:
            x = np.array([t[0] for t in taper])
            fits = []
            for column in (2, 1):
                y = np.array([t[column] for t in taper])
                a, b = np.polyfit(x, y, 1)
                fits.append((a, b))
                residuals.append(float(np.abs(y - (a * x + b)).max()))
            angles.append(math.degrees(math.atan(abs(fits[0][0])) + math.atan(abs(fits[1][0]))))
            shoulders.append((half_width - fits[0][1]) / fits[0][0])
        if len(facet_verts):
            fv = local[facet_verts]
            # the arm's own chamfer: inside the arm's angular range (the notch chamfer starts there too)
            fin = (np.abs(np.arctan2(fv[:, 1], fv[:, 0])) <= o.arm_half_angle + 1e-9) & (fv[:, 0] > o.r_hub - o.half_w)
            fv = fv[fin]
            if len(fv):
                starts.append(float(fv[:, 0].min()))
                drops.append(half_t - float(np.abs(fv[:, 2]).min()))
        for key, (lo, hi) in edges.items():
            plate_y = plate_edges.get(key)
            if plate_y is None or hi < 1e-9:
                continue
            if hi < half_width - 1e-7 and plate_y > 1e-9 and angles:
                taper_insets.append((hi - plate_y) * math.cos(math.radians(0.5 * angles[-1])))
    out = {}
    if angles:
        out.update({
            "tip_included_deg": round(float(np.mean(angles)), 6),
            "tip_included_deg_range": [round(min(angles), 6), round(max(angles), 6)],
            "tip_edge_fit_residual_mm": round(max(residuals) / MM, 9),
            "shoulder_arm_x_mm": round(float(np.mean(shoulders)) / MM, 6),
            "tip_angle_arms_fitted": len(angles),
        })
    if starts:
        out.update({
            "chamfer_start_arm_x_mm": round(float(np.mean(starts)) / MM, 6),
            "chamfer_wall_top_drop_mm": round(float(np.mean(drops)) / MM, 6),
        })
    if run_widths:
        out["chamfer_width_measured_mm"] = round(float(np.mean(run_widths)) / MM, 6)
        out["chamfer_width_spread_mm"] = round((max(run_widths) - min(run_widths)) / MM, 9)
    if taper_insets:
        out["chamfer_taper_inset_mm"] = round(float(np.mean(taper_insets)) / MM, 6)
        out["chamfer_taper_inset_spread_mm"] = round((max(taper_insets) - min(taper_insets)) / MM, 9)
    return out


def topology_quality(obj, o: Outline) -> dict:
    """Face-shape figures the gallery wireframe exposes (visual review metric).

    ``hub_aspect``: longest edge squared over area of every top-plate face inside the hub
    circle (a square is 1, an equilateral triangle 2.31).  ``hub_mirror_misses``: top hub
    faces whose mirror image about the arm axis is not a face - a chiral (pinwheel) fan
    misses them all.  Triangle angles are over the fan triangulation of every face.
    """
    bm = evaluated_bm(obj)
    try:
        half_t = max(v.co.z for v in bm.verts)
        aspects, keys = [], set()
        min_angle, under5, tris = 180.0, 0, 0
        for face in bm.faces:
            co = [v.co.copy() for v in face.verts]
            for k in range(1, len(co) - 1):
                a, b, c = co[0], co[k], co[k + 1]
                tri = [math.degrees((b - a).angle(c - a)), math.degrees((a - b).angle(c - b)),
                       math.degrees((a - c).angle(b - c))]
                tris += 1
                min_angle = min(min_angle, min(tri))
                under5 += min(tri) < 5.0
            if all(abs(v.co.z - half_t) < 1e-9 for v in face.verts) and \
                    max(math.hypot(v.co.x, v.co.y) for v in face.verts) <= o.r_hub + 1e-9:
                longest = max((co[k] - co[(k + 1) % len(co)]).length for k in range(len(co)))
                aspects.append(longest ** 2 / face.calc_area())
                centre = face.calc_center_median()
                keys.add((float(centre.x), float(centre.y), len(co)))
    finally:
        bm.free()
    cent = np.array([(x, y) for x, y, _k in keys]) if keys else np.zeros((0, 2))
    sizes = np.array([k for _x, _y, k in keys])
    misses = 0
    for (x, y), size in zip(cent, sizes):
        d = np.hypot(cent[:, 0] - x, cent[:, 1] + y)
        misses += not np.any((d < 1e-7) & (sizes == size))
    return {
        "hub_top_faces": len(aspects),
        "hub_aspect_median": round(float(np.median(aspects)), 3) if aspects else None,
        "hub_aspect_max": round(float(max(aspects)), 3) if aspects else None,
        "hub_faces_aspect_over_8": int(sum(a > 8.0 for a in aspects)),
        "hub_mirror_misses": int(misses),
        "min_triangle_angle_deg": round(min_angle, 3),
        "triangles_under_5deg": int(under5),
        "triangles": tris,
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
        faces = [[v.index for v in f.verts] for f in bm.faces]
        normals = np.array([f.normal[:] for f in bm.faces], dtype=np.float64)
        areas = np.array([f.calc_area() for f in bm.faces], dtype=np.float64)
    finally:
        bm.free()

    radial = np.hypot(co[:, 0], co[:, 1])
    zs = co[:, 2]
    half_t = o.half_t
    volume_mm3 = volume / (MM ** 3)
    mass_g = (volume / (0.01 ** 3)) * spec.density_g_cm3   # m3 -> cm3 -> grams

    # Arm width, measured on the long edge of arm 0's parallel-sided run only (the
    # shoulder ring is excluded; LODs with a single straight interval fall back to it).
    # The band is the OUTLINE: per x station the largest |y| of the candidates, so the
    # chamfer's plate-edge and level vertices (1.2 mm inside the wall, inside the +-1.5 mm
    # search band) do not read as a 2.4 mm width spread on a parallel arm.
    local_angle = np.abs(np.arctan2(co[:, 1], co[:, 0]))
    on_arm0 = local_angle < o.half_sector
    edge_band = (np.abs(co[:, 1]) > o.half_w - 1.5 * MM) & (np.abs(co[:, 1]) <= o.half_w + 1.5 * MM)
    on_edge = on_arm0 & edge_band & (co[:, 0] >= o.r_hub + 1.0 * MM) & (co[:, 0] <= o.x_taper - 0.5 * MM)
    width_source = "parallel run"
    if not on_edge.any():
        on_edge = on_arm0 & edge_band & (np.abs(co[:, 0] - o.x_taper) < 1e-7)
        width_source = "shoulder ring"
    stations: dict = {}
    for x_key, y_abs in zip(np.round(co[on_edge, 0] / 1e-7).astype(np.int64), np.abs(co[on_edge, 1])):
        stations[x_key] = max(stations.get(x_key, 0.0), float(y_abs))
    band = np.array(list(stations.values()), dtype=np.float64)
    # Chamfer: the only vertices with |z| strictly between 0 and half_t are the facet.
    facet = (np.abs(zs) > 1e-9) & (np.abs(zs) < half_t - 1e-9)
    inter = np.abs(zs)[facet]
    bevel_z = float(half_t - inter.min()) if len(inter) else 0.0
    # Hole: across-flats is the real opening, across-corners the circumscribed radius.
    hole_total = lod.hole_segments * o.n
    # Only the hole ring itself: with graded hub rings (LodSpec.hub_rings) the first ring can sit
    # inside the old "halfway to the hub" cut-off, so select the polygon's own radius band.
    hole_r = (radial[radial <= o.hole_polygon_radius(hole_total) + 1e-6] if lod.has_hole else radial[:0])
    flats = (round(2.0 * float(hole_r.min()) * math.cos(math.pi / hole_total) / MM, 6)
             if len(hole_r) else None)
    tip_sel = np.abs(zs)[radial > o.r_tip - 1e-7]
    hub_sel = radial[(radial > o.r_hub - 1.0 * MM) & (radial < o.r_hub + 0.5 * MM)]
    shape = taper_and_bevel(co, faces, normals, o, float(band.max()) if len(band) else o.half_w)

    # --- the knife grind, measured (grind_figures) and the two masses (mass_figures)
    from .geometry import hole_distance, outline_distance, scallop_distance
    xy = co[:, :2]
    edge_d = outline_distance(o, xy)
    sector = 2.0 * math.pi / o.n
    ang = np.arctan2(co[:, 1], co[:, 0])
    local_x = radial * np.cos(ang - np.round(ang / sector) * sector)
    zone = ((local_x > o.x_run - 1e-7) & (scallop_distance(o, xy) > o.scallop.width + 1e-7)
            & (hole_distance(o, lod, xy) > 1e-3))
    axis = (np.abs(np.sin(ang - np.round(ang / sector) * sector)) * radial < 1e-7) & (local_x > o.x_apex - 1e-7) \
        & (co[:, 2] > 0.0)
    ridge = np.column_stack([local_x[axis], co[axis, 2]]) if axis.any() else None
    knife = o.knife_of(lod) if lod.has_bevel else None
    grind = grind_figures(co, faces, normals, areas, edge_d, knife.width if knife else 0.0, zone, o.r_tip,
                          o.grind_angle_deg, o.edge_land, ridge) if knife else {}
    if knife is not None:
        grind["grind_width_mm"] = round(knife.width / MM, 6)
        grind["runout_mm"] = round(o.runout / MM, 6) if lod.has_runout_station else round((o.x_taper - o.x_root(0.0)) / MM, 6)
        grind["runout_note"] = ("the knife grind runs out into the scallop chamfer (or, square scallops, to nothing) "
                                "between the arm root and this far out along the parallel run; the edge land there "
                                "grows from the land to the scallop's wall")
        grind["land_mode"] = "edge land" if lod.knife_land else "facets meet in a sharp edge line (land 0)"
    plain = unbevelled_plate_area_mm2(spec, lod)
    masses = mass_figures(volume, plain["volume_mm3"] * MM ** 3, spec)
    outline_land = 2.0 * float(np.abs(co[edge_d < 1e-7, 2]).min()) if (edge_d < 1e-7).any() else o.thickness

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
        # Fitted to the taper edges of every arm (was copied from the spec before the
        # maintenance pass); the spec value is kept alongside for comparison.
        "tip_included_deg": shape.get("tip_included_deg"),
        "tip_included_deg_spec": spec.tip_included_deg,
        "tip_included_deg_range": shape.get("tip_included_deg_range"),
        "tip_edge_fit_residual_mm": shape.get("tip_edge_fit_residual_mm"),
        "shoulder_arm_x_mm": shape.get("shoulder_arm_x_mm"),
        # The full-length ground chamfer, all measured on the mesh (requested values alongside):
        # plan width on the parallel run (exact), perpendicular inset on the taper, the wall
        # top's drop (depth plus the round-over) and where it starts in arm-local x (the root
        # mitre).  edge_land_mm is the rim wall left between the two chamfers.
        "grind": grind,
        "chamfer_width_requested_mm": round(o.chamfer_w / MM, 6) if lod.has_bevel else 0.0,
        "chamfer_width_measured_mm": shape.get("chamfer_width_measured_mm", 0.0),
        "chamfer_width_spread_mm": shape.get("chamfer_width_spread_mm"),
        "chamfer_taper_inset_mm": shape.get("chamfer_taper_inset_mm"),
        "chamfer_depth_requested_mm": round(o.chamfer.depth / MM, 6) if lod.has_bevel else 0.0,
        "chamfer_round_requested_mm": round(o.chamfer.round / MM, 6) if lod.has_bevel else 0.0,
        "chamfer_wall_top_drop_mm": round(bevel_z / MM, 6),
        "chamfer_wall_top_drop_requested_mm": round(o.chamfer.wall_top_drop / MM, 6) if lod.has_bevel else 0.0,
        "chamfer_start_arm_x_mm": shape.get("chamfer_start_arm_x_mm"),
        "chamfer_root_mitre_requested_mm": [round(o.x_root(0.0) / MM, 6),
                                            round(o.x_root(o.scallop_of(lod)) / MM, 6)],
        "chamfer_segments": lod.bevel_segments,
        "scallop_chamfer_mm": round(o.scallop_of(lod) / MM, 6),
        "hole_chamfer_mm": round(o.hole_chamfer.width / MM, 6) if lod.has_hole_bevel else 0.0,
        "edge_land_mm": round(outline_land / MM, 6),
        "flat_rim_band_mm": round(outline_land / MM, 6),
        "tip_edge_height_mm": round(2.0 * float(tip_sel.max()) / MM, 6) if len(tip_sel) else None,
        "volume_mm3": round(volume_mm3, 4),
        "plate_area_mm2": round(volume_mm3 / (o.thickness / MM), 4),
        "outline_volume_mm3": plain["volume_mm3"],
        "outline_plate_area_mm2": plain["plate_area_mm2"],
        **masses,
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
    plain = replace(lod, bevel_segments=0, tip_intervals=0, pyramid_tip=False, taper_intervals=max(1, lod.taper_intervals))
    bm, stats = build_star_bmesh(o, plain, plain.taper_intervals)
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


__all__ = ["cn_deviation", "evaluated_bm", "grind_figures", "lod_deviation", "mass_figures", "measure", "mesh_extents",
           "surface_deviation", "surface_samples", "surface_snapshot", "taper_and_bevel", "topology_quality",
           "triangles_array", "triangles_of", "unbevelled_plate_area_mm2", "uv_coverage", "vertices_of"]
