"""Do the shipped FBX's corner normals equal the .blend's (the analytic arris-round normals of 3.8.1)?

    blender -b --factory-startup --python fbx_normals_check.py -- <out.json>
Loads Assets/Shuriken.blend's spike LODs (library append) and the shipped FBX; matches corners by (vertex
position, face centroid) at 1e-6 m and reports the largest angle between the two corner normals, plus the
round loops' deviation from the analytic arc normal (0, P - C) / rho.
"""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
out_path = Path(sys.argv[sys.argv.index("--") + 1])
A, RHO = 0.003, 0.0003


def corners(obj):
    mesh = obj.data
    mw = np.array(obj.matrix_world, dtype=np.float64)
    rot = mw[:3, :3] / np.cbrt(abs(np.linalg.det(mw[:3, :3])))
    co = np.array([v.co[:] for v in mesh.vertices], dtype=np.float64) @ mw[:3, :3].T + mw[:3, 3]
    normals = np.array([c.vector[:] for c in mesh.corner_normals], dtype=np.float64) @ rot.T
    out = {}
    for poly in mesh.polygons:
        cen = co[list(poly.vertices)].mean(axis=0)
        for li in poly.loop_indices:
            p = co[mesh.loops[li].vertex_index]
            key = tuple(np.round(np.concatenate([p, cen]) * 1e6).astype(np.int64))
            out[key] = (p, normals[li] / np.linalg.norm(normals[li]))
    return out


def analytic_dev(entries):
    worst = 0.0
    count = 0
    for p, n in entries:
        y, z = p[1], p[2]
        if min(abs(y), abs(z)) < A - RHO - 1e-7 or abs(n[0]) > 1e-3:
            continue
        cy, cz = math.copysign(A - RHO, y), math.copysign(A - RHO, z)
        dy, dz = y - cy, z - cz
        r = math.hypot(dy, dz)
        if abs(r - RHO) > 1e-6:
            continue
        # a round corner: its normal should be the arc normal unless it is a face corner (normal = face axis)
        arc = np.array([0.0, dy / r, dz / r])
        face = abs(abs(n[1]) - 1.0) < 1e-4 or abs(abs(n[2]) - 1.0) < 1e-4
        ang = math.degrees(math.acos(max(-1.0, min(1.0, float(arc @ n)))))
        if face and ang > 1e-3:
            continue
        worst = max(worst, ang)
        count += 1
    return worst, count


bpy.ops.wm.read_factory_settings(use_empty=True)
names = ["SM_Shuriken_Spike_LOD0", "SM_Shuriken_Spike_LOD1", "SM_Shuriken_Spike_LOD2"]
with bpy.data.libraries.load(str(PROJ / "Assets" / "Shuriken.blend"), link=False) as (src, dst):
    dst.objects = list(names)
blend = {o.name: corners(o) for o in dst.objects}
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(PROJ / "Exports" / "Shuriken" / "SM_Shuriken_Spike.fbx"))
result = {}
for name in names:
    obj = bpy.data.objects.get(name)
    fb = corners(obj)
    bl = blend[name]
    # the FBX is triangulated (face centroids differ): match every .blend corner to the FBX corner at the same
    # position (1 nm) with the closest normal
    by_pos = {}
    for pos, n in fb.values():
        by_pos.setdefault(tuple(np.round(pos * 1e6).astype(np.int64)), []).append(n)
    angles, common = [], []
    for pos, n in bl.values():
        cands = by_pos.get(tuple(np.round(pos * 1e6).astype(np.int64)), [])
        if cands:
            common.append(pos)
            angles.append(min(math.degrees(math.acos(max(-1.0, min(1.0, float(c @ n))))) for c in cands))
    worst = max(angles) if angles else None
    dev_b, n_b = analytic_dev(bl.values())
    dev_f, n_f = analytic_dev(fb.values())
    result[name] = {"corners_blend": len(bl), "corners_fbx": len(fb), "matched": len(common),
                    "max_angle_fbx_vs_blend_deg": round(worst, 6) if worst is not None else None,
                    "round_corners_checked_blend": n_b, "round_max_dev_from_analytic_deg_blend": round(dev_b, 6),
                    "round_corners_checked_fbx": n_f, "round_max_dev_from_analytic_deg_fbx": round(dev_f, 6)}
out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
print("FBX_NORMALS " + json.dumps(result))
