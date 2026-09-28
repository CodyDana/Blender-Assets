"""Blend vs shipped FBX surface check (maintenance round), headless:

    blender -b --factory-startup --python blend_vs_fbx.py -- <Shuriken.blend> <export_dir> <out.json>

For every form's LOD0..2 in the .blend and the same node re-imported from the shipped FBX:
volume (mm3), volume-centroid z (mm; 0 for a top/bottom-mirror-symmetric surface), triangle
count, and the largest distance from any triangle centroid of one to the other's triangle
centroids (a different triangulation of a folded quad shows up here).  Also the stored
corner-normal deviation on faces whose normal is 30-40 deg off Z (the knife facets of the stars).
Never saves anything.
"""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:]
BLEND, EXPORT, OUT = Path(argv[0]), Path(argv[1]), Path(argv[2])
MESHES = ("SM_Shuriken_FourPoint", "SM_Shuriken_EightPoint", "SM_Shuriken_SquarePlate")


def arrays(obj):
    me = obj.data
    me.calc_loop_triangles()
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    mw = np.array(obj.matrix_world)
    co = co @ mw[:3, :3].T + mw[:3, 3]
    tri = np.empty(len(me.loop_triangles) * 3, dtype=np.int64)
    me.loop_triangles.foreach_get("vertices", tri)
    return co, tri.reshape(-1, 3)


def volume(co, tri):
    a, b, c = co[tri[:, 0]], co[tri[:, 1]], co[tri[:, 2]]
    v = np.einsum("ij,ij->i", a, np.cross(b, c)) / 6.0
    cz = ((a + b + c)[:, 2] / 4.0 * v).sum() / v.sum()
    return v.sum(), cz


def corner_dev(obj):
    me = obj.data
    corner = np.empty(len(me.loops) * 3)
    me.corner_normals.foreach_get("vector", corner)
    corner = corner.reshape(-1, 3)
    worst = 0.0
    for poly in me.polygons:
        n = np.array(poly.normal[:])
        tilt = math.degrees(math.acos(min(1.0, abs(n[2]))))
        if not 30.0 < tilt < 40.0:
            continue
        for li in range(poly.loop_start, poly.loop_start + poly.loop_total):
            c = corner[li] / max(np.linalg.norm(corner[li]), 1e-12)
            worst = max(worst, math.degrees(math.acos(max(-1.0, min(1.0, float(c @ n))))))
    return worst


def lods_in_scene(prefix):
    return {o.name: o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith(prefix + "_LOD")}


result = {}
bpy.ops.wm.open_mainfile(filepath=str(BLEND))
blend = {}
for mesh in MESHES:
    for name, obj in lods_in_scene(mesh).items():
        co, tri = arrays(obj)
        vol, cz = volume(co, tri)
        blend[name] = {"co": co, "tri": tri, "volume_mm3": vol * 1e9, "centroid_z_mm": cz * 1e3,
                       "tris": len(tri), "corner_dev_deg_30_40": corner_dev(obj)}
for mesh in MESHES:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(EXPORT / f"{mesh}.fbx"))
    for name, obj in lods_in_scene(mesh).items():
        co, tri = arrays(obj)
        scale = 1.0
        vol, cz = volume(co, tri)
        ref = blend.get(name)
        entry = {"fbx_volume_mm3": round(vol * 1e9, 4), "fbx_centroid_z_mm": round(cz * 1e3, 9),
                 "fbx_tris": len(tri), "fbx_corner_dev_deg_30_40": round(corner_dev(obj), 4)}
        if ref is not None:
            ca = ref["co"][ref["tri"]].mean(axis=1)
            cb = co[tri].mean(axis=1)
            worst = 0.0
            for start in range(0, len(ca), 256):
                d = np.linalg.norm(ca[start:start + 256, None, :] - cb[None, :, :], axis=-1).min(axis=1)
                worst = max(worst, float(d.max()))
            entry.update({"blend_volume_mm3": round(ref["volume_mm3"], 4),
                          "blend_centroid_z_mm": round(ref["centroid_z_mm"], 9), "blend_tris": ref["tris"],
                          "blend_corner_dev_deg_30_40": round(ref["corner_dev_deg_30_40"], 4),
                          "volume_delta_mm3": round(vol * 1e9 - ref["volume_mm3"], 5),
                          "max_triangle_centroid_mismatch_mm": round(worst * 1e3, 6)})
        result[name] = entry
OUT.write_text(json.dumps(result, indent=1), encoding="utf-8")
print(json.dumps(result, indent=1))
print("BLEND_VS_FBX_DONE")
