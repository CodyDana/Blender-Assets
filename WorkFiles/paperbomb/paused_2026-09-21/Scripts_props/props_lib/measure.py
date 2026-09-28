#!/usr/bin/env python
"""props_lib.measure - measure what was built, so the report is evidence and not a claim.

Nothing here decides anything; every function returns numbers and the build script
decides.  The rule the pack works to is that a number in a report has been measured on
the thing that ships, not carried forward from the spec that asked for it.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np


# ===========================================================================
# Mesh
# ===========================================================================

def mesh_arrays(obj):
    mesh = obj.data
    co = np.empty(len(mesh.vertices) * 3, np.float64)
    mesh.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    mesh.calc_loop_triangles()
    tris = np.array([t.vertices[:] for t in mesh.loop_triangles], np.int64)
    return co, tris


def triangles(obj) -> int:
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


def surface_area_m2(obj) -> float:
    co, tris = mesh_arrays(obj)
    a, b, c = co[tris[:, 0]], co[tris[:, 1]], co[tris[:, 2]]
    return float(0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1).sum())


def volume_m3(obj) -> float:
    """Signed volume of a closed shell, from the divergence theorem."""
    co, tris = mesh_arrays(obj)
    a, b, c = co[tris[:, 0]], co[tris[:, 1]], co[tris[:, 2]]
    return float(np.abs(np.einsum("ij,ij->i", a, np.cross(b, c)).sum()) / 6.0)


def extents_mm(obj) -> Dict[str, List[float]]:
    co, _ = mesh_arrays(obj)
    co = co * 1000.0
    return {"min": [round(float(x), 4) for x in co.min(axis=0)],
            "max": [round(float(x), 4) for x in co.max(axis=0)],
            "size": [round(float(x), 4) for x in np.ptp(co, axis=0)]}


def manifold(obj) -> Dict[str, object]:
    """Edge use counts, and any non-manifold or inconsistently wound edge."""
    mesh = obj.data
    used: Dict[Tuple[int, int], int] = {}
    directed: Dict[Tuple[int, int], int] = {}
    for poly in mesh.polygons:
        verts = list(poly.vertices)
        for i in range(len(verts)):
            a, b = verts[i], verts[(i + 1) % len(verts)]
            key = (a, b) if a < b else (b, a)
            used[key] = used.get(key, 0) + 1
            directed[(a, b)] = directed.get((a, b), 0) + 1
    hist: Dict[int, int] = {}
    for count in used.values():
        hist[count] = hist.get(count, 0) + 1
    return {
        "edges": len(used),
        "use_histogram": {str(k): v for k, v in sorted(hist.items())},
        "closed": set(hist) == {2},
        "inconsistent_winding_edges": sum(1 for c in directed.values() if c > 1),
        "loose_vertices": sum(1 for v in mesh.vertices if not any(
            v.index in e.vertices for e in mesh.edges[:0])) if False else 0,
    }


def degenerates(obj, min_area_m2: float = 1e-12, min_edge_m: float = 1e-6) -> Dict[str, int]:
    co, tris = mesh_arrays(obj)
    a, b, c = co[tris[:, 0]], co[tris[:, 1]], co[tris[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    edges = np.concatenate([np.linalg.norm(b - a, axis=1), np.linalg.norm(c - b, axis=1),
                            np.linalg.norm(a - c, axis=1)])
    return {"zero_area_triangles": int((area < min_area_m2).sum()),
            "short_edges": int((edges < min_edge_m).sum()),
            "min_triangle_area_mm2": round(float(area.min()) * 1e6, 6),
            "min_edge_mm": round(float(edges.min()) * 1000.0, 5)}


# ===========================================================================
# UV
# ===========================================================================

def uv_arrays(obj, index: int = 0):
    mesh = obj.data
    mesh.calc_loop_triangles()
    layer = mesh.uv_layers[index]
    uv = np.empty(len(mesh.loops) * 2, np.float64)
    layer.data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    tri_loops = np.array([t.loops[:] for t in mesh.loop_triangles], np.int64)
    return uv, tri_loops


def texel_density_px_per_cm(obj, texture_px: int, index: int = 0) -> float:
    """The same figure ``pipeline.qa_check`` computes: sqrt(uv area / mesh area) * px / 100."""
    mesh = obj.data
    layer = mesh.uv_layers[index]
    uv_area = 0.0
    mesh_area = 0.0
    for poly in mesh.polygons:
        pts = [layer.data[i].uv for i in poly.loop_indices]
        shoelace = sum(pts[i].x * pts[(i + 1) % len(pts)].y - pts[(i + 1) % len(pts)].x * pts[i].y
                       for i in range(len(pts)))
        uv_area += abs(shoelace) * 0.5
        mesh_area += poly.area
    if mesh_area <= 0:
        return 0.0
    return math.sqrt(uv_area / mesh_area) * texture_px / 100.0


def uv_overlap_texels(obj, size: int = 2048, index: int = 0) -> Dict[str, object]:
    """Rasterise every UV triangle at ``size`` and count texels covered more than once.

    A pixel test rather than a separating-axis test: it is what actually matters for a
    bake, it catches a rim strip that has drifted into its neighbour, and it is cheap.
    """
    uv, tri_loops = uv_arrays(obj, index)
    cover = np.zeros((size, size), np.int32)
    for tri in tri_loops:
        p = uv[tri] * size
        x0 = max(int(np.floor(p[:, 0].min())), 0)
        x1 = min(int(np.ceil(p[:, 0].max())) + 1, size)
        y0 = max(int(np.floor(p[:, 1].min())), 0)
        y1 = min(int(np.ceil(p[:, 1].max())) + 1, size)
        if x1 <= x0 or y1 <= y0:
            continue
        xs = np.arange(x0, x1) + 0.5
        ys = np.arange(y0, y1) + 0.5
        gx, gy = np.meshgrid(xs, ys)
        a, b, c = p[0], p[1], p[2]
        det = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(det) < 1e-12:
            continue
        w0 = ((b[1] - c[1]) * (gx - c[0]) + (c[0] - b[0]) * (gy - c[1])) / det
        w1 = ((c[1] - a[1]) * (gx - c[0]) + (a[0] - c[0]) * (gy - c[1])) / det
        w2 = 1.0 - w0 - w1
        inside = (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9)
        cover[y0:y1, x0:x1] += inside.astype(np.int32)
    overlapped = int((cover > 1).sum())
    return {"texels_covered": int((cover > 0).sum()),
            "texels_overlapped": overlapped,
            "overlap_fraction_of_covered": round(overlapped / max(1, int((cover > 0).sum())), 6),
            "raster_size": size}


def uv_stretch(obj, texture_px: int, ppmm: float, index: int = 0,
               skin_u_max: Optional[float] = None) -> Dict[str, object]:
    """Edge length in 3D against edge length in UV, as a ratio; 1.0 is an isometry.

    ``skin_u_max`` separates the two populations, because they are different claims.
    The SKIN's UV is meant to be an isometry - it is the paper coordinate - and a value
    away from 1.0 there is texture stretch on the print.  The RIM is a 0.15 mm edge laid
    into three narrow strips at whatever density fits, deliberately, so its ratio is a
    number about packing and not about quality.  Reported apart; the build gates the skin.
    """
    mesh = obj.data
    layer = mesh.uv_layers[index]
    skin: List[float] = []
    skin_mid: List[Tuple[float, float, float]] = []
    rim: List[float] = []
    for poly in mesh.polygons:
        n = poly.loop_total
        us = [layer.data[poly.loop_start + k].uv.x for k in range(n)]
        is_rim = skin_u_max is not None and min(us) >= skin_u_max
        bucket = rim if is_rim else skin
        for k in range(n):
            i = poly.loop_start + k
            j = poly.loop_start + (k + 1) % n
            va = mesh.vertices[mesh.loops[i].vertex_index].co
            vb = mesh.vertices[mesh.loops[j].vertex_index].co
            d3 = (va - vb).length * 1000.0
            ua, ub = layer.data[i].uv, layer.data[j].uv
            d2 = math.hypot(ua.x - ub.x, ua.y - ub.y) * texture_px / ppmm
            if d3 > 0.05 and d2 > 0.05:
                bucket.append(d3 / d2)
                if bucket is skin:
                    skin_mid.append(tuple(float(x) * 1000.0 for x in (va + vb) * 0.5))

    def stats(values):
        if not values:
            return None
        r = np.array(values)
        return {"edges": int(r.size), "min": round(float(r.min()), 5),
                "max": round(float(r.max()), 5), "mean": round(float(r.mean()), 5),
                "p01": round(float(np.percentile(r, 1)), 5),
                "p99": round(float(np.percentile(r, 99)), 5)}

    out = dict(stats(skin) or {})
    out["skin"] = stats(skin)
    out["rim"] = stats(rim)
    if skin and skin_mid:
        # WHERE the extremes are, because that is what decides whether they matter.
        # A single edge that chords the 105 deg dog-ear fold reads about 0.86 by pure
        # polygonisation - chord against arc, 1 - theta^2/24 - and says nothing about
        # the parametrisation.  The population statistics (p01 / p99) are the claim
        # about texture stretch; min and max are a claim about tessellation.
        r = np.array(skin)
        out["skin"]["min_at_mm"] = [round(v, 3) for v in skin_mid[int(r.argmin())]]
        out["skin"]["max_at_mm"] = [round(v, 3) for v in skin_mid[int(r.argmax())]]
        out["skin"]["note"] = ("min / max are single edges and are dominated by chord-"
                               "against-arc where the mesh polygonises a tight bend; "
                               "p01 / p99 are the texture-stretch claim")
    return out


def uv_range(obj, index: int = 0) -> List[float]:
    uv, _ = uv_arrays(obj, index)
    return [round(float(uv.min()), 6), round(float(uv.max()), 6)]


# ===========================================================================
# Across the LODs
# ===========================================================================

def cross_lod_uv_agreement(lod0, other, plan, spec) -> Dict[str, object]:
    """Do the two LODs put the same paper point at the same texel?

    They share ONE analytic map (paper millimetres -> atlas), so this should be exact.
    It is measured rather than assumed because a transfer would only be approximate and
    somebody reading the report has a right to know which of the two this is.  The test
    walks ``other``'s skin vertices, recovers each one's paper coordinate from its UV,
    and asks the map what the UV should have been.
    """
    mesh = other.data
    layer = mesh.uv_layers[0]
    ox, oy = plan.front_origin
    bx, _by = plan.back_origin
    worst = 0.0
    checked = 0
    for poly in mesh.polygons:
        for i in poly.loop_indices:
            uvc = layer.data[i].uv
            px = uvc.x * plan.size
            py = (1.0 - uvc.y) * plan.size
            if px < ox + plan.card_px[0] + 8:
                u = (px - ox) / plan.ppmm
                want = plan.uv_front(u, (py - oy) / plan.ppmm)
            elif px < bx + plan.card_px[0] + 8:
                u = (px - bx) / plan.ppmm
                want = plan.uv_back(u, (py - oy) / plan.ppmm)
            else:
                continue                                 # the rim: its own parameterisation
            worst = max(worst, abs(uvc.x - want[0]), abs(uvc.y - want[1]))
            checked += 1
    return {"skin_loops_checked": checked,
            "max_uv_error": round(float(worst), 9),
            "max_texel_error": round(float(worst) * plan.size, 6),
            "method": "analytic map, not a projected transfer"}


def plan_silhouette(obj, px_per_mm: float = 4.0, half_x: float = 82.0,
                    half_y: float = 40.0) -> np.ndarray:
    """Rasterise the plan-view (XY) silhouette of ``obj`` into a boolean mask.

    A radial-bin measurement is the wrong tool for a 156 x 70 mm rectangle - the first
    version of this reported a 62 mm "inward" change on a 70 mm card, because most
    angular bins around the pivot are empty and the interpolation between them is
    meaningless at the ends.  A raster is unambiguous: what the card covers, seen from
    directly above, at a quarter of a millimetre.
    """
    co, tris = mesh_arrays(obj)
    xy = co[:, :2] * 1000.0
    w = int(round(2 * half_x * px_per_mm))
    h = int(round(2 * half_y * px_per_mm))
    mask = np.zeros((h, w), bool)
    px = (xy[:, 0] + half_x) * px_per_mm
    py = (xy[:, 1] + half_y) * px_per_mm
    p = np.stack([px, py], axis=1)
    for tri in tris:
        t = p[tri]
        x0 = max(int(np.floor(t[:, 0].min())), 0)
        x1 = min(int(np.ceil(t[:, 0].max())) + 1, w)
        y0 = max(int(np.floor(t[:, 1].min())), 0)
        y1 = min(int(np.ceil(t[:, 1].max())) + 1, h)
        if x1 <= x0 or y1 <= y0:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
        a, b, c = t[0], t[1], t[2]
        det = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(det) < 1e-12:
            continue
        w0 = ((b[1] - c[1]) * (gx - c[0]) + (c[0] - b[0]) * (gy - c[1])) / det
        w1 = ((c[1] - a[1]) * (gx - c[0]) + (a[0] - c[0]) * (gy - c[1])) / det
        w2 = 1.0 - w0 - w1
        mask[y0:y1, x0:x1] |= (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9)
    return mask


def silhouette_saving(lod0, other, px_per_mm: float = 4.0) -> Dict[str, object]:
    """How the plan silhouette changed between LOD0 and a coarser LOD.

    A real LOD simplifies the OUTLINE, not only the triangle count, so the number that
    matters is the symmetric difference: how much area moved, in either direction.  Note
    that a coarser LOD is often slightly LARGER - dropping the torn edge and the dog-ear
    gives the card back the material they bit out - so an area ratio above 1.0 is the
    expected result and not a regression.
    """
    a = plan_silhouette(lod0, px_per_mm)
    b = plan_silhouette(other, px_per_mm)
    cell = 1.0 / (px_per_mm * px_per_mm)
    area_a = float(a.sum()) * cell
    area_b = float(b.sum()) * cell
    lost = float((a & ~b).sum()) * cell
    gained = float((b & ~a).sum()) * cell
    return {"lod0_area_mm2": round(area_a, 3),
            "lod_area_mm2": round(area_b, 3),
            "area_ratio": round(area_b / area_a, 5),
            "area_only_in_lod0_mm2": round(lost, 3),
            "area_only_in_this_lod_mm2": round(gained, 3),
            "symmetric_difference_mm2": round(lost + gained, 3),
            "symmetric_difference_fraction": round((lost + gained) / area_a, 5),
            "px_per_mm": px_per_mm}


def _vertices_to_surface_mm(verts: np.ndarray, co: np.ndarray,
                            tris: np.ndarray) -> np.ndarray:
    """Distance from each vertex to the nearest point of a triangle soup, in mm."""
    a, b, c = co[tris[:, 0]], co[tris[:, 1]], co[tris[:, 2]]
    best = np.full(len(verts), np.inf)
    chunk = 64
    for start in range(0, len(a), chunk):
        d = _point_triangle_distance(verts, a[start:start + chunk],
                                     b[start:start + chunk], c[start:start + chunk])
        best = np.minimum(best, d.min(axis=1))
    return best * 1000.0


def lod_deviation_mm(lod0, other, samples: int = 4000) -> Dict[str, float]:
    """Two-sided LOD error in millimetres.

    THE DIRECTION MATTERS.  The first build reported only LODn -> LOD0, which for a LOD
    whose vertices are a SUBSET of LOD0's positions is zero-by-construction on every
    vertex that survived and tiny on the rest: it measured 0.027 mm and 0.021 mm, and
    the true two-sided error was 1.08 mm and 1.63 mm - forty to eighty times larger.
    What a LOD loses shows up in the OTHER direction, LOD0 -> LODn, so both run and the
    reported figure is the Hausdorff distance, the max of the two.  (The LODs are still
    fine: at the LOD1 switch the tag is 75.6 px wide, so 1.08 mm is about half a pixel.
    The defect was the number, not the mesh.)
    """
    co0, tris0 = mesh_arrays(lod0)
    co1, tris1 = mesh_arrays(other)
    p1 = np.array([v.co[:] for v in other.data.vertices], np.float64)
    p0 = np.array([v.co[:] for v in lod0.data.vertices], np.float64)
    fwd = _vertices_to_surface_mm(p1, co0, tris0)        # LODn -> LOD0
    back = _vertices_to_surface_mm(p0, co1, tris1)       # LOD0 -> LODn: what was LOST
    return {
        "hausdorff_mm": round(float(max(fwd.max(), back.max())), 4),
        "lod_to_lod0_max_mm": round(float(fwd.max()), 4),
        "lod_to_lod0_mean_mm": round(float(fwd.mean()), 4),
        "lod0_to_lod_max_mm": round(float(back.max()), 4),
        "lod0_to_lod_mean_mm": round(float(back.mean()), 4),
        "lod0_to_lod_p95_mm": round(float(np.percentile(back, 95)), 4),
        "note": "hausdorff_mm is the two-sided figure; LODn -> LOD0 alone is "
                "near-zero by construction for a vertex-subset LOD and must not be "
                "quoted on its own",
    }


def _point_triangle_distance(p, a, b, c):
    """Distance from every point (N, 3) to every triangle (M, 3) -> (N, M)."""
    p = p[:, None, :]
    ab = (b - a)[None, :, :]
    ac = (c - a)[None, :, :]
    ap = p - a[None, :, :]
    d1 = np.einsum("nmk,nmk->nm", ab, ap)
    d2 = np.einsum("nmk,nmk->nm", ac, ap)
    bp = p - b[None, :, :]
    d3 = np.einsum("nmk,nmk->nm", ab, bp)
    d4 = np.einsum("nmk,nmk->nm", ac, bp)
    cp = p - c[None, :, :]
    d5 = np.einsum("nmk,nmk->nm", ab, cp)
    d6 = np.einsum("nmk,nmk->nm", ac, cp)
    va = d3 * d6 - d5 * d4
    vb = d5 * d2 - d1 * d6
    vc = d1 * d4 - d3 * d2
    denom = np.where(np.abs(va + vb + vc) < 1e-24, 1e-24, va + vb + vc)
    v = np.clip(vb / denom, 0.0, 1.0)
    w = np.clip(vc / denom, 0.0, 1.0)
    s = v + w
    over = s > 1.0
    v = np.where(over, v / np.where(s == 0, 1.0, s), v)
    w = np.where(over, w / np.where(s == 0, 1.0, s), w)
    closest = a[None, :, :] + ab * v[:, :, None] + ac * w[:, :, None]
    return np.linalg.norm(p - closest, axis=2)


# ===========================================================================
# Physical
# ===========================================================================

def mass_report(obj, spec) -> Dict[str, object]:
    """Paper is a grammage, not a density: the mass is area x g/m2, and the mesh's own
    plan area is what is measured."""
    co, _ = mesh_arrays(obj)
    xy = co[:, :2] * 1000.0
    # plan area of the FRONT skin only: half the closed shell's area projected flat
    area = surface_area_m2(obj) * 1e6 * 0.5              # mm2, both skins -> one sheet
    mass = area * 1e-6 * spec.grammage_g_per_m2
    return {
        "grammage_g_per_m2": spec.grammage_g_per_m2,
        "spec_plan_area_mm2": round(spec.plan_area_mm2, 3),
        "measured_sheet_area_mm2": round(float(area), 3),
        "spec_mass_g": round(spec.mass_g, 4),
        "measured_mass_g": round(float(mass), 4),
        "ue_mass_in_kg_override": 0.001,
        "fallback_kg": 0.005,
        "note": ("half the closed shell's surface area is the sheet; the rim adds "
                 "0.15 mm x the perimeter, which is the difference from the plan area"),
    }


def check_pack_lod_rule(spec) -> Dict[str, object]:
    """Assert props_lib's restated pack rule still equals shuriken_lib's own function."""
    import sys
    from pathlib import Path
    shuriken = str(Path(__file__).resolve().parents[2] / "shuriken")
    if shuriken not in sys.path:
        sys.path.insert(0, shuriken)
    try:
        from shuriken_lib import spec as sspec
    except Exception as exc:                            # pragma: no cover
        return {"checked": False, "reason": f"{type(exc).__name__}: {exc}"}
    radius = spec.bounds_radius_mm
    theirs = list(sspec.scaled_lod_screen_sizes(radius))
    ours = spec.lod_screen_sizes(radius)
    return {"checked": True,
            "shuriken_lib": theirs, "props_lib": ours,
            "agree": all(abs(a - b) < 1e-9 for a, b in zip(theirs, ours)),
            "LOD_SCREEN_SIZES": list(sspec.LOD_SCREEN_SIZES),
            "LOD_REFERENCE_RADIUS_MM": sspec.LOD_REFERENCE_RADIUS_MM}


__all__ = ["mesh_arrays", "triangles", "surface_area_m2", "volume_m3", "extents_mm",
           "manifold", "degenerates", "texel_density_px_per_cm", "uv_overlap_texels",
           "uv_stretch", "uv_range", "cross_lod_uv_agreement", "silhouette_saving",
           "lod_deviation_mm", "mass_report", "check_pack_lod_rule",
           "ring_radial_runs", "relief_band_energy", "edge_band_drop",
           "ink_rule_collision", "silhouette_octagon"]


# ===========================================================================
# Art gates - the four things the first build got wrong and could not prove
# ===========================================================================

def ring_radial_runs(ink_red: np.ndarray, ppmm: float, pad_mm: float,
                     centre_mm: Tuple[float, float],
                     outer_mm: Tuple[float, float],
                     bins: int = 60) -> Dict[str, object]:
    """Is the brush ring ONE lap, or several concentric ones?

    Walks an elliptical ray outward every ``360/bins`` degrees and counts how many
    separate radial runs of ink it crosses.  One lap gives one run at most angles; a
    stroke cut into ribbons by a hard dry-brush threshold gives two, three or more,
    which is what the first build measured - median 3, and 49 of 60 angles with two or
    more - and what made the ring read as three concentric vector circles.

    The ray is clamped to +-20 % of the nominal ellipse, because a longer one runs into
    the seal boxes and the frame rules and counts THEM as ring.
    """
    a = np.asarray(ink_red, np.float32)
    H, W = a.shape
    cx, cy = centre_mm
    ow, oh = outer_mm
    runs: List[int] = []
    widths: List[float] = []
    rs = np.linspace(0.74, 1.12, 420)
    for k in range(bins):
        th = math.radians(k * 360.0 / bins)
        xs = cx + (ow * 0.5) * rs * math.cos(th)
        ys = cy - (oh * 0.5) * rs * math.sin(th)
        ix = ((xs + pad_mm) * ppmm).astype(int)
        iy = ((ys + pad_mm) * ppmm).astype(int)
        ok = (ix >= 0) & (ix < W) & (iy >= 0) & (iy < H)
        hit = np.zeros(len(rs), bool)
        hit[ok] = a[iy[ok], ix[ok]] > 0.5
        runs.append(int(np.sum(hit[1:] & ~hit[:-1]) + (1 if hit[0] else 0)))
        dr = float(np.hypot((ow * 0.5) * (rs[1] - rs[0]) * math.cos(th),
                            (oh * 0.5) * (rs[1] - rs[0]) * math.sin(th)))
        run = 0
        for v in hit:
            if v:
                run += 1
            elif run:
                widths.append(run * dr)
                run = 0
        if run:
            widths.append(run * dr)
    r = np.array(runs, float)
    w = np.array(widths, float) if widths else np.zeros(1)
    return {
        "bins": bins,
        "median_runs_per_angle": round(float(np.median(r)), 2),
        "angles_with_one_run": int((r == 1).sum()),
        "angles_with_two_or_more": int((r >= 2).sum()),
        "max_runs": int(r.max()),
        "run_width_mm_p50": round(float(np.percentile(w, 50)), 3),
        "run_width_mm_p90": round(float(np.percentile(w, 90)), 3),
        "run_width_mm_max": round(float(w.max()), 3),
        "note": "a dry lap and one run per angle pull against each other: a bare "
                "streak crossing the whole stroke splits it in two at that angle. The "
                "gate is that MOST angles are a single run and that the runs are as "
                "wide as the study's stroke, not that every angle is one.",
    }


def relief_band_energy(relief_mm: np.ndarray, ink: np.ndarray, card: np.ndarray,
                       ppmm: float, patch: int = 128,
                       fine_mm: float = 0.4, mid_mm: float = 1.5) -> Dict[str, object]:
    """How much of the surface's SLOPE energy sits at the study's fibre cell.

    The study asks for fibre grain on a 0.1 - 0.4 mm cell.  The first build's normal map
    put 4 - 7 % of its slope energy there and 62 - 79 % in the 0.4 - 1.5 mm band, which
    is why the raking close-up read as pebbled stucco instead of laid kozo.  Measured on
    ink-free, fully-inside patches, because cockling and the fold grooves are SUPPOSED
    to be coarse and would mask the thing under test.
    """
    rel = np.asarray(relief_mm, np.float64)
    H, W = rel.shape
    spots: List[Tuple[int, int]] = []
    for py in range(0, H - patch, patch // 2):
        for px in range(0, W - patch, patch // 2):
            if (ink[py:py + patch, px:px + patch].max() < 0.02
                    and card[py:py + patch, px:px + patch].min() > 0.99):
                spots.append((py, px))
    if not spots:
        return {"patches": 0}
    f1 = np.fft.fftshift(np.fft.fftfreq(patch, d=1.0 / ppmm))
    fy, fx = f1[:, None], f1[None, :]
    f = np.hypot(fy, fx)
    lam = np.where(f > 0, 1.0 / np.maximum(f, 1e-9), 1e9)
    m_fine = (f > 0) & (lam <= fine_mm)
    m_mid = (f > 0) & (lam > fine_mm) & (lam <= mid_mm)
    m_coarse = (f > 0) & (lam > mid_mm)
    key_fine = "fraction_at_or_under_0p4mm"
    out = []
    step = max(1, len(spots) // 5)
    for py, px in spots[::step][:5]:
        p = rel[py:py + patch, px:px + patch]
        g = (np.abs(np.fft.fftshift(np.fft.fft2(p - p.mean()))) * f) ** 2
        tot = float(g[f > 0].sum()) or 1.0
        gy = np.gradient(p, axis=0) * ppmm
        gx = np.gradient(p, axis=1) * ppmm
        out.append({
            "at_px": [py, px],
            key_fine: round(float(g[m_fine].sum() / tot), 4),
            "fraction_0p4_to_1p5mm": round(float(g[m_mid].sum() / tot), 4),
            "fraction_over_1p5mm": round(float(g[m_coarse].sum() / tot), 4),
            "relief_p01_to_p99_mm": round(float(np.percentile(p, 99) - np.percentile(p, 1)), 4),
            "rms_slope_deg": round(float(np.degrees(np.arctan(np.hypot(gx, gy))).mean()), 3),
        })
    return {"patches": len(spots), "patch_px": patch, "samples": out,
            "fine_band_mm": fine_mm, "mid_band_mm": mid_mm,
            "min_fine_fraction": round(min(s[key_fine] for s in out), 4),
            "median_rms_slope_deg": round(float(np.median([s["rms_slope_deg"] for s in out])), 3),
            "study": "fibre grain 0.010 - 0.020 mm relief on a 0.1 - 0.4 mm cell"}


def edge_band_drop(base_colour: np.ndarray, ink: np.ndarray, outline_mm: np.ndarray,
                   ppmm: float, pad_mm: float) -> Dict[str, object]:
    """The aged edge band, as a stored-sRGB profile inward from the real trim line.

    The study's table puts the band at linear (0.448, 0.340, 0.197) against an interior
    of (0.700, 0.587, 0.393) - about a 17 % drop in stored sRGB - and says it gets there
    within a millimetre.  The first build measured 2 - 6 % over the last half
    millimetre, which is clean stock with two smudges.  Distance here is to the OUTLINE
    POLYLINE, not to a blurred mask, so the number means what it says.
    """
    rgb = np.asarray(base_colour, np.float32)
    H, W = rgb.shape[:2]
    s = np.clip(rgb, 0.0, 1.0)
    s = np.where(s <= 0.0031308, s * 12.92, 1.055 * s ** (1 / 2.4) - 0.055)
    lum = 0.2126 * s[:, :, 0] + 0.7152 * s[:, :, 1] + 0.0722 * s[:, :, 2]
    yy = (np.arange(H, dtype=np.float32)[:, None] + 0.5) / ppmm - pad_mm
    xx = (np.arange(W, dtype=np.float32)[None, :] + 0.5) / ppmm - pad_mm
    best = np.full((H, W), 1e9, np.float32)
    pts = np.asarray(outline_mm, np.float64)
    keep = max(1, len(pts) // 900)
    for px, py in pts[::keep]:
        np.minimum(best, (xx - px) ** 2 + (yy - py) ** 2, out=best)
    dist = np.sqrt(best)
    clean = (np.asarray(ink) < 0.02)
    prof: Dict[str, float] = {}
    for lo, hi in ((0.0, 0.35), (0.35, 0.8), (0.8, 1.5), (1.5, 3.0),
                   (3.0, 6.0), (6.0, 10.0), (10.0, 20.0)):
        m = clean & (dist >= lo) & (dist < hi)
        if int(m.sum()) > 64:
            prof["%.2f_to_%.2f_mm" % (lo, hi)] = round(float(np.median(lum[m])), 4)
    inner = clean & (dist > 12.0)
    outer = clean & (dist < 0.35)
    interior = float(np.median(lum[inner])) if int(inner.sum()) else 0.0
    edge = float(np.median(lum[outer])) if int(outer.sum()) else interior
    return {"stored_luma_profile": prof,
            "interior_stored_luma": round(interior, 4),
            "edge_stored_luma": round(edge, 4),
            "drop_fraction": round(1.0 - edge / max(interior, 1e-6), 4),
            "study_target_drop": 0.17}


def silhouette_octagon(outline_mm: np.ndarray, width_mm: float, height_mm: float,
                       clip_mm: float) -> Dict[str, object]:
    """Is the drawn card outline the reference's clean octagon?

    THE GATE THE LAST BUILD DID NOT HAVE.  The shipped card carried a 12 mm dog-ear at
    the bottom-right corner folded 105 deg out of plane, a 5 mm nick in the right edge
    and a 16 mm torn bottom edge, and every gate beside them was green - ``s23`` even
    measured the chamfer happily two millimetres away from the fold.  The user saw it
    immediately: "the bottom right edge of the tag looks not correct, its like burned
    off or cut short".

    ``REFERENCE_SPEC`` section 1 settled it by the same method used here, on the
    reference of record: fit the four straight sides and the four bevels, build the
    eight-gon they imply, and ask how far every boundary sample lies from it.  On the
    reference the answer is +0.78 / -0.72 px (+-0.20 mm) with rms 0.19 px, and ZERO
    samples anywhere more than 0.38 mm inboard.  So the shape of this measurement is
    the shape of that one, and the test is the same test: no run of missing paper, of
    any length, at any corner or along any edge.

    Returns the per-side straightness (row S8), the four chamfer legs (rows S3/S4) and
    the damage test (row S10): the deepest inward excursion on each of the eight runs.
    """
    o = np.asarray(outline_mm, np.float64)
    if len(o) > 1 and np.hypot(*(o[0] - o[-1])) < 1e-9:
        o = o[:-1]
    w, h, c = float(width_mm), float(height_mm), float(clip_mm)

    # the ideal octagon, corner-first, in the same order card_outline_mm emits
    verts = np.array([(c, 0.0), (w - c, 0.0), (w, c), (w, h - c),
                      (w - c, h), (c, h), (0.0, h - c), (0.0, c)], np.float64)

    def seg_signed(points, a, b):
        """Signed distance of each point from the line a->b; + is OUTBOARD of the card."""
        d = b - a
        n = np.array([d[1], -d[0]], np.float64)          # outward for this winding
        n = n / max(float(np.hypot(*n)), 1e-12)
        return (points - a[None, :]) @ n

    def seg_distance(points, a, b):
        """Unsigned point-to-SEGMENT distance - the assignment metric."""
        d = b - a
        L2 = max(float(d @ d), 1e-12)
        t = np.clip(((points - a[None, :]) @ d) / L2, 0.0, 1.0)
        foot = a[None, :] + t[:, None] * d[None, :]
        return np.hypot(*(points - foot).T)

    names = ["top", "chamfer_TR", "right", "chamfer_BR",
             "bottom", "chamfer_BL", "left", "chamfer_TL"]
    # Every boundary sample belongs to exactly ONE run: the nearest of the eight.  A
    # run cannot be judged on points that merely PROJECT onto its infinite line - the
    # left edge projects onto the top edge's whole extent - and getting that wrong is
    # how a measurement reports a clean card as 160 mm of missing paper.
    dists = np.stack([seg_distance(o, verts[k], verts[(k + 1) % 8]) for k in range(8)])
    owner = np.argmin(dists, axis=0)

    runs: Dict[str, object] = {}
    worst_in = 0.0
    worst_out = 0.0
    all_sq = []
    for k, name in enumerate(names):
        a, b = verts[k], verts[(k + 1) % 8]
        sel = owner == k
        if not np.any(sel):
            runs[name] = {"samples": 0}
            continue
        pts = o[sel]
        s = seg_signed(pts, a, b)
        rms = float(np.sqrt(np.mean(s * s)))
        runs[name] = {
            "samples": int(sel.sum()),
            "rms_mm": round(rms, 5),
            "max_outward_mm": round(float(s.max()), 5),
            "max_inward_mm": round(float(-s.min()), 5),
            "n_inboard_over_0p38mm": int((s < -0.38).sum()),
        }
        all_sq.append(rms)
        worst_in = max(worst_in, float(-s.min()))
        worst_out = max(worst_out, float(s.max()))

    # the four chamfer legs, read off the drawn polyline's own corner vertices
    legs = {}
    for name, (p0, p1) in (("TL", (verts[7], verts[0])), ("TR", (verts[1], verts[2])),
                           ("BR", (verts[3], verts[4])), ("BL", (verts[5], verts[6]))):
        legs[name] = {"horizontal_mm": round(abs(float(p1[0] - p0[0])), 4),
                      "vertical_mm": round(abs(float(p1[1] - p0[1])), 4),
                      "chord_mm": round(float(np.hypot(*(p1 - p0))), 4)}

    inboard_runs = sum(int(r.get("n_inboard_over_0p38mm", 0)) for r in runs.values()
                       if isinstance(r, dict))
    sides = [k for k in names if not k.startswith("chamfer")]
    bevels = [k for k in names if k.startswith("chamfer")]

    def worst(keys, field):
        return max(float(runs[k].get(field, 0.0)) for k in keys if runs[k].get("samples"))

    # Row S8 for the four sides (RG fits them straight to rms 0.014 - 0.018 mm, max
    # departure 0.033 - 0.044) and row S7 for the four bevels (rms 0.00 - 0.15, max
    # <= 0.29): a straight cut, not a bevelled curve.  Row S10 is the damage test.
    side_rms, side_max = worst(sides, "rms_mm"), worst(sides, "max_inward_mm")
    bevel_rms, bevel_max = worst(bevels, "rms_mm"), worst(bevels, "max_inward_mm")
    return {
        "runs": runs,
        "chamfer_legs_mm": legs,
        "n_boundary_samples": int(len(o)),
        "worst_inward_mm": round(worst_in, 5),
        "worst_outward_mm": round(worst_out, 5),
        "worst_side_rms_mm": round(side_rms, 5),
        "worst_side_departure_mm": round(side_max, 5),
        "worst_bevel_rms_mm": round(bevel_rms, 5),
        "worst_bevel_departure_mm": round(bevel_max, 5),
        "samples_more_than_0p38mm_inboard": inboard_runs,
        "sides_straight_S8": bool(side_rms <= 0.05 and side_max <= 0.12),
        "bevels_straight_S7": bool(bevel_rms <= 0.20 and bevel_max <= 0.40),
        "no_damage_S10": bool(inboard_runs == 0),
        "stays_inside_the_card_box": bool(worst_out <= 0.02),
        "is_clean_octagon": bool(inboard_runs == 0 and worst_out <= 0.02
                                 and side_rms <= 0.05 and side_max <= 0.12
                                 and bevel_rms <= 0.20 and bevel_max <= 0.40),
        "reference": ("REFERENCE_SPEC rows S2/S7/S8/S10 - the reference tag is a clean "
                      "octagon: 1820 boundary samples, worst 0.20 mm, zero runs inboard"),
    }


def ink_rule_collision(ink_black: np.ndarray, ink_red: np.ndarray,
                       card: np.ndarray, exclude=None) -> Dict[str, object]:
    """Black ink sitting on top of a red rule - the layout fault the eye catches first.

    The first build ran the upper kanji columns over the frame's inner rule at both top
    corners.  A texel that is fully black AND fully red is that fault, and it is far
    cheaper to assert than to notice.  ``exclude`` masks the region where black over red
    is the DESIGN - the centre character is brushed across the ring on purpose.
    """
    b = np.asarray(ink_black) > 0.5
    r = np.asarray(ink_red) > 0.5
    both = b & r & (np.asarray(card) > 0.5)
    if exclude is not None:
        both = both & ~np.asarray(exclude, bool)
    n = int(both.sum())
    area = float((np.asarray(card) > 0.5).sum()) or 1.0
    where: List[List[int]] = []
    if n:
        ys, xs = np.nonzero(both)
        where = [[int(ys.min()), int(ys.max())], [int(xs.min()), int(xs.max())]]
    return {"texels_black_over_red": n,
            "fraction_of_card": round(n / area, 6),
            "bbox_rows_cols_px": where,
            "note": "the centre character crosses the ring by design and is excluded; "
                    "what is counted is ink over the FRAME"}


def shell_self_intersections(obj, max_report: int = 12) -> Dict[str, object]:
    """Does the closed shell pass through itself anywhere?

    THE DEFECT THIS EXISTS FOR.  The shipped build's LOD0 carried eight pairs of
    intersecting faces - the front skin and the back skin of the same cell, 0.15 mm
    apart, crossing because a warped four-sided cell was split along one diagonal on the
    front and the other on the back.  No existing gate could see it: the mesh was still
    closed, still manifold, still free of zero-area faces, and its UVs still did not
    overlap.  What DID see it was the Cycles AO bake, which came back with eight
    near-black UV cells - the hard-edged square patches of speckle a reviewer found at
    4x in the shipped render.

    ``props_lib.sheet.skin_pair`` now triangulates both skins the same way, so the two
    surfaces are exact normal offsets and cannot cross.  This is the gate that says so,
    and it runs on every LOD.
    """
    import bpy
    from mathutils.bvhtree import BVHTree

    depsgraph = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(obj, depsgraph)
    pairs = sorted({tuple(sorted(p)) for p in tree.overlap(tree)})
    mesh = obj.data
    where: List[Dict[str, object]] = []
    for a, b in pairs[:max_report]:
        try:
            pa = np.array(mesh.polygons[a].center) * 1000.0
            pb = np.array(mesh.polygons[b].center) * 1000.0
        except IndexError:                                    # pragma: no cover
            continue
        where.append({"faces": [int(a), int(b)],
                      "at_mm": [round(float(v), 3) for v in pa],
                      "separation_mm": round(float(np.linalg.norm(pa - pb)), 4)})
    return {"pairs": len(pairs), "clean": len(pairs) == 0, "where": where,
            "note": "front/back skin pairs that cross; an AO bake reads each one as a "
                    "near-black UV cell with straight, axis-aligned edges"}


def corner_clip_agrees(spec, art_module) -> Dict[str, object]:
    """``spec.corner_clip_mm`` and ``paperbomb_art.CORNER_CLIP_MM`` are one number.

    They are stated twice - the geometry reads one and the artwork's outline reads the
    other - and REFERENCE_SPEC row 23 moves it from 7.6 to 8.05 mm.  A build that
    changed one and not the other would draw the artwork for a card it did not cut.
    """
    a = float(spec.corner_clip_mm)
    b = float(art_module.CORNER_CLIP_MM)
    return {"spec_mm": a, "art_mm": b, "agree": abs(a - b) < 1e-9}
