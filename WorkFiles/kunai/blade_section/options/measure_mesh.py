"""Measure one option's SHIPPED-STYLE LOD0 mesh (read-only; the .blend is never saved): true cross-sections at stations,
the ridge thickness, the face slope, the grind band in section, and the head island's texel density.

  blender -b <option.blend> --factory-startup --python measure_mesh.py -- <report.json> <out.json>

Sections: bmesh bisect of LOD0 at design x (object x = (x - pivot) mm), the cut vertices ordered round their centroid
(the blade section is convex).  face_slope is fitted on the TOP diamond face between 0.2 h and the grind line (least
squares, |z| vs |y|), both halves; ridge = the section's thickness on the axis; edge_z = the thickness at the land.
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:]
report = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
out_path = Path(argv[1])
shift = float(report["measured"]["pivot_design_x_mm"])
MM = 0.001
STATIONS = [13.4, 26.7, 35.0, 39.4, 56.7, 74.1, 91.4, 108.7, 125.0]
obj = bpy.data.objects["SM_Kunai_Plain_LOD0"]


def section(x_design, ob=None):
    bm = bmesh.new()
    bm.from_mesh((ob or obj).data)
    xo = (x_design - shift) * MM
    res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(xo, 0.0, 0.0),
                                 plane_no=(1.0, 0.0, 0.0), dist=1e-9)
    pts = [(v.co.y / MM, v.co.z / MM) for v in res["geom_cut"] if isinstance(v, bmesh.types.BMVert)]
    bm.free()
    pts = np.array(sorted(set((round(y, 6), round(z, 6)) for y, z in pts)))
    c = pts.mean(axis=0)
    ang = np.arctan2(pts[:, 1] - c[1], pts[:, 0] - c[0])
    return pts[np.argsort(ang)]


def z_top_at(poly, y):
    """Top surface z at y (the polygon's max z on the vertical line)."""
    zs = []
    n = len(poly)
    for i in range(n):
        (y0, z0), (y1, z1) = poly[i], poly[(i + 1) % n]
        if (y0 - y) * (y1 - y) <= 0 and abs(y1 - y0) > 1e-12:
            zs.append(z0 + (z1 - z0) * (y - y0) / (y1 - y0))
    return max(zs) if zs else None


def z_bot_at(poly, y):
    zs = []
    n = len(poly)
    for i in range(n):
        (y0, z0), (y1, z1) = poly[i], poly[(i + 1) % n]
        if (y0 - y) * (y1 - y) <= 0 and abs(y1 - y0) > 1e-12:
            zs.append(z0 + (z1 - z0) * (y - y0) / (y1 - y0))
    return min(zs) if zs else None


rows = {}
for x in STATIONS:
    poly = section(x)
    h = float(poly[:, 0].max())
    ridge = z_top_at(poly, 0.0) - z_bot_at(poly, 0.0)
    # the grind line on the top face: the vertex where the slope changes most near the edge
    top = poly[poly[:, 1] > 0]
    ys = np.linspace(0.2 * h, 0.98 * h, 60)
    zt = np.array([z_top_at(poly, y) for y in ys])
    # a steep drop marks the knife facet: keep the diamond part (local slope below tan 25 deg)
    d = -np.gradient(zt, ys)
    keep = d < math.tan(math.radians(25.0))
    last = np.argmax(~keep) if (~keep).any() else len(ys)
    yk, zk = ys[:max(last - 1, 3)], zt[:max(last - 1, 3)]
    slope = float(-np.polyfit(yk, zk, 1)[0])
    grind_start_y = float(ys[last]) if last < len(ys) else None
    rows[f"{x:g}"] = {
        "x_mm": x, "half_width_mm": round(h, 4), "ridge_thickness_mm": round(ridge, 4),
        "face_slope_mesh": round(slope, 4), "face_angle_deg": round(math.degrees(math.atan(slope)), 2),
        "ridge_ratio_mesh": round(0.5 * ridge / h, 4),
        "grind_band_in_section_mm": round(h - grind_start_y, 3) if grind_start_y is not None else None,
        "outline_yz_mm": [[round(float(a), 4), round(float(b), 4)] for a, b in poly],
    }
# head island texel density: steel faces of the head (x >= -6.5 design), UV area vs surface area
mesh = obj.data
uv = np.empty(len(mesh.loops) * 2, dtype=np.float64)
mesh.uv_layers[0].data.foreach_get("uv", uv)
uv = uv.reshape(-1, 2)
tot_t, tot_a, coat_t, coat_a = 0.0, 0.0, 0.0, 0.0
for p in mesh.polygons:
    if p.material_index != 0 or p.area <= 1e-12:
        continue
    cx = p.center.x / MM + shift
    if cx < 0.0:
        continue
    q = uv[list(p.loop_indices)]
    a_uv = 0.5 * abs(float(np.sum(q[:, 0] * np.roll(q[:, 1], -1) - np.roll(q[:, 0], -1) * q[:, 1])))
    texels = a_uv * 2048.0 * 2048.0
    area = p.area / MM ** 2
    tot_t += texels
    tot_a += area
    if abs(p.normal.z) >= 0.95:
        coat_t += texels
        coat_a += area
# LOD ridge fidelity: the ridge thickness of LOD1 / LOD2 against LOD0 along the blade (the diamond is where the
# section change could open a gap between LODs; the report's two-sided deviation max is set by the grip)
lod_ridge = {}
for name in ("SM_Kunai_Plain_LOD1", "SM_Kunai_Plain_LOD2"):
    ob = bpy.data.objects.get(name)
    if ob is None:
        continue
    worst = (0.0, None)
    per = {}
    for xs in [5.0 + 2.5 * i for i in range(53)]:
        p0, p1 = section(xs), section(xs, ob)
        r0 = z_top_at(p0, 0.0) - z_bot_at(p0, 0.0)
        r1 = z_top_at(p1, 0.0) - z_bot_at(p1, 0.0)
        per[f"{xs:g}"] = round(r1 - r0, 4)
        if abs(r1 - r0) > abs(worst[0]):
            worst = (r1 - r0, xs)
    lod_ridge[name] = {"max_ridge_thickness_delta_mm": round(worst[0], 4), "at_x_mm": worst[1], "per_x": per}
res = {"pivot_design_x_mm": shift, "stations": rows, "lod_ridge_vs_lod0": lod_ridge,
       "blade_texel_px_per_mm_area_weighted": round(math.sqrt(tot_t / tot_a), 4),
       "blade_coat_faces_px_per_mm": round(math.sqrt(coat_t / coat_a), 4) if coat_a else None,
       "blade_steel_surface_mm2": round(tot_a, 2)}
out_path.write_text(json.dumps(res, indent=1), encoding="utf-8")
print("MEASURE", json.dumps({k: {kk: v[kk] for kk in ("ridge_thickness_mm", "face_slope_mesh", "half_width_mm",
                                                       "grind_band_in_section_mm")} for k, v in rows.items()}))
print("TEXEL", res["blade_texel_px_per_mm_area_weighted"], res["blade_coat_faces_px_per_mm"])
print("LODRIDGE", {k: (v["max_ridge_thickness_delta_mm"], v["at_x_mm"]) for k, v in lod_ridge.items()})
