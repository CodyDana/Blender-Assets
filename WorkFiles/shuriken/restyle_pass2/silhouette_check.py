"""Plan-view silhouette of every LOD against restyle pass 1 (knife grind pass gate).

HEADLESS:
    blender -b <new Shuriken.blend> --factory-startup --python silhouette_check.py -- <pass1_npz_dir> <out.json>

<pass1_npz_dir> holds <object>.npz files (co, tri) dumped from
Backups/Shuriken_restyle_pass1_2026-09-18/Shuriken.blend.  For every SM_Shuriken_* LOD mesh of
the open file, the FULL mesh (every triangle, both faces, walls included) is projected onto XY
and rasterised at PIXEL_MM (pixel centres; a triangle covers a centre inside it or on its
edge), for pass 1 and for the current mesh on the same grid.  Reported: pixels that differ
(XOR) and their area, and - exact, not rasterised - the outline vertices (vertices whose XY
lies on the silhouette boundary, i.e. the rim-wall vertices) of each mesh: pass 1's outline
vertices missing from the new mesh, and new outline vertices that are not on pass 1's outline
polygon (distance to its boundary edges).
"""
import json
import sys
from pathlib import Path

import bpy
import numpy as np

PIXEL_MM = 0.02
MM = 0.001


def mesh_arrays(obj):
    me = obj.data
    me.calc_loop_triangles()
    co = np.empty(len(me.vertices) * 3, dtype=np.float64)
    me.vertices.foreach_get("co", co)
    tri = np.empty(len(me.loop_triangles) * 3, dtype=np.int64)
    me.loop_triangles.foreach_get("vertices", tri)
    return co.reshape(-1, 3), tri.reshape(-1, 3)


def rasterise(co, tri, origin, shape, pixel):
    mask = np.zeros(shape, dtype=bool)
    xy = (co[:, :2] - origin) / pixel - 0.5          # pixel-centre coordinates
    for a, b, c in tri:
        pa, pb, pc = xy[a], xy[b], xy[c]
        area = (pb[0] - pa[0]) * (pc[1] - pa[1]) - (pb[1] - pa[1]) * (pc[0] - pa[0])
        if abs(area) < 1e-9:
            continue                                 # a wall: zero area in plan
        x0 = max(int(np.floor(min(pa[0], pb[0], pc[0]))), 0)
        x1 = min(int(np.ceil(max(pa[0], pb[0], pc[0]))), shape[1] - 1)
        y0 = max(int(np.floor(min(pa[1], pb[1], pc[1]))), 0)
        y1 = min(int(np.ceil(max(pa[1], pb[1], pc[1]))), shape[0] - 1)
        if x1 < x0 or y1 < y0:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1, dtype=np.float64), np.arange(y0, y1 + 1, dtype=np.float64))
        s = 1.0 if area > 0 else -1.0
        eps = -1e-7
        w0 = s * ((pb[0] - pa[0]) * (gy - pa[1]) - (pb[1] - pa[1]) * (gx - pa[0]))
        w1 = s * ((pc[0] - pb[0]) * (gy - pb[1]) - (pc[1] - pb[1]) * (gx - pb[0]))
        w2 = s * ((pa[0] - pc[0]) * (gy - pc[1]) - (pa[1] - pc[1]) * (gx - pc[0]))
        inside = (w0 >= eps) & (w1 >= eps) & (w2 >= eps)
        mask[y0:y1 + 1, x0:x1 + 1] |= inside
    return mask


def boundary_edges(co, tri):
    """Plan-boundary edges of the XY projection: edges of plan-visible (non-wall) triangles
    that are used by exactly one such triangle per face side (top or bottom half)."""
    counts = {}
    for a, b, c in tri:
        pa, pb, pc = co[a, :2], co[b, :2], co[c, :2]
        area = (pb[0] - pa[0]) * (pc[1] - pa[1]) - (pb[1] - pa[1]) * (pc[0] - pa[0])
        if abs(area) < 1e-14:
            continue
        top = (co[a, 2] + co[b, 2] + co[c, 2]) > 0.0
        for u, v in ((a, b), (b, c), (c, a)):
            key = (top, min(u, v), max(u, v))
            counts[key] = counts.get(key, 0) + 1
    edges = [(u, v) for (top, u, v), n in counts.items() if n == 1 and top]
    return np.array(edges, dtype=np.int64).reshape(-1, 2)


def seg_distance(points, a, b):
    d = b - a
    l2 = np.maximum((d * d).sum(1), 1e-30)
    out = np.full(len(points), np.inf)
    for start in range(0, len(points), 256):
        p = points[start:start + 256][:, None, :]
        t = np.clip(((p - a[None]) * d[None]).sum(-1) / l2[None], 0.0, 1.0)
        q = a[None] + t[..., None] * d[None]
        out[start:start + 256] = np.linalg.norm(p - q, axis=-1).min(1)
    return out


def outline_points(co, tri):
    """XY of the vertices on the OUTER plan boundary (the largest boundary loop = the outline)."""
    edges = boundary_edges(co, tri)
    verts = np.unique(edges.ravel())
    r = np.hypot(co[verts, 0], co[verts, 1])
    return co[verts, :2], edges, r


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    pass1_dir, out_path = Path(argv[0]), Path(argv[1])
    result = {"pixel_mm": PIXEL_MM, "method": __doc__.strip().splitlines()[0], "objects": {}}
    all_same = True
    for obj in sorted(bpy.data.objects, key=lambda o: o.name):
        if obj.type != "MESH" or not obj.name.startswith("SM_Shuriken_"):
            continue
        ref_file = pass1_dir / f"{obj.name}.npz"
        if not ref_file.exists():
            result["objects"][obj.name] = {"error": "no pass-1 mesh"}
            all_same = False
            continue
        ref = np.load(ref_file)
        co0, tri0 = ref["co"], ref["tri"]
        co1, tri1 = mesh_arrays(obj)
        lo = np.minimum(co0[:, :2].min(0), co1[:, :2].min(0)) - 0.5 * MM
        hi = np.maximum(co0[:, :2].max(0), co1[:, :2].max(0)) + 0.5 * MM
        pixel = PIXEL_MM * MM
        shape = (int(np.ceil((hi[1] - lo[1]) / pixel)), int(np.ceil((hi[0] - lo[0]) / pixel)))
        m0 = rasterise(co0, tri0, lo, shape, pixel)
        m1 = rasterise(co1, tri1, lo, shape, pixel)
        xor = m0 ^ m1
        # exact outline comparison: boundary vertices of each against the other's boundary edges
        p0, e0, _ = outline_points(co0, tri0)
        p1, e1, _ = outline_points(co1, tri1)
        d10 = seg_distance(p1, co0[e0[:, 0], :2], co0[e0[:, 1], :2]) if len(e0) else np.array([np.inf])
        d01 = seg_distance(p0, co1[e1[:, 0], :2], co1[e1[:, 1], :2]) if len(e1) else np.array([np.inf])
        entry = {
            "pass1_triangles": int(len(tri0)), "triangles": int(len(tri1)),
            "raster_px": [int(shape[1]), int(shape[0])],
            "area_pass1_mm2": round(float(m0.sum()) * PIXEL_MM ** 2, 4),
            "area_mm2": round(float(m1.sum()) * PIXEL_MM ** 2, 4),
            "xor_pixels": int(xor.sum()),
            "xor_area_mm2": round(float(xor.sum()) * PIXEL_MM ** 2, 6),
            "boundary_vertices_pass1": int(len(p0)), "boundary_vertices": int(len(p1)),
            "max_new_boundary_vertex_off_pass1_boundary_mm": round(float(d10.max()) / MM, 9),
            "max_pass1_boundary_vertex_off_new_boundary_mm": round(float(d01.max()) / MM, 9),
            "extents_pass1_mm": [round(float(v) / MM, 6) for v in np.ptp(co0[:, :2], axis=0)],
            "extents_mm": [round(float(v) / MM, 6) for v in np.ptp(co1[:, :2], axis=0)],
        }
        same = entry["xor_pixels"] == 0 and entry["max_new_boundary_vertex_off_pass1_boundary_mm"] < 1e-5 \
            and entry["max_pass1_boundary_vertex_off_new_boundary_mm"] < 1e-5
        entry["unchanged"] = bool(same)
        all_same = all_same and same
        result["objects"][obj.name] = entry
    result["all_unchanged"] = bool(all_same)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=1))


main()
