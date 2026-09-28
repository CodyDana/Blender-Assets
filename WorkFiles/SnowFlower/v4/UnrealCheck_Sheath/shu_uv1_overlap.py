"""UV1 (Unreal's generated lightmap UV) overlap, read from Unreal's own FBX export (pass 3):
texels covered by more than one triangle's interior, per LOD, at 1024 and 2048."""
import json
from pathlib import Path

import bpy
import numpy as np

H = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\SnowFlower\v4\UnrealCheck_Sheath")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(H / "unreal_roundtrip.fbx"))


def overlap(tris, size):
    count = np.zeros((size, size), np.int32)
    for t in tris * size:
        x0, y0 = np.floor(t.min(axis=0)).astype(int)
        x1, y1 = np.ceil(t.max(axis=0)).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, size), min(y1, size)
        if x1 <= x0 or y1 <= y0:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
        (ax, ay), (bx, by), (cx, cy) = t
        d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(d) < 1e-12:
            continue
        l1 = ((by - cy) * (xs - cx) + (cx - bx) * (ys - cy)) / d
        l2 = ((cy - ay) * (xs - cx) + (ax - cx) * (ys - cy)) / d
        l3 = 1 - l1 - l2
        inside = (l1 > 1e-6) & (l2 > 1e-6) & (l3 > 1e-6)
        count[y0:y1, x0:x1] += inside
    return int((count > 1).sum()), int((count > 0).sum())


out = {}
for o in bpy.data.objects:
    if o.type != "MESH" or o.name.upper().startswith("UCX"):
        continue
    me = o.data
    me.calc_loop_triangles()
    if len(me.uv_layers) < 2:
        out[o.name] = {"uv_layers": [l.name for l in me.uv_layers], "error": "no UV1"}
        continue
    uv = np.empty(len(me.loops) * 2, np.float32)
    me.uv_layers[1].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2).astype(np.float64)
    tris = np.array([[uv[l] for l in t.loops] for t in me.loop_triangles])
    e = {"uv_layers": [l.name for l in me.uv_layers], "uv1_range": [float(uv.min()), float(uv.max())]}
    for size in (1024, 2048):
        ov, cov = overlap(tris, size)
        e[f"overlap_texels_{size}"] = ov
        e[f"covered_texels_{size}"] = cov
    out[o.name] = e
(H / "uv1_overlap.json").write_text(json.dumps(out, indent=2))
print("UV1", json.dumps(out))
