"""Per-material texel density and UV overlap estimate on the rev-3 game mesh (read-only).
blender -b SnowFlower_Game.blend --factory-startup --python inspect_uv_permaterial.py -- out.json
"""
import bpy, sys, json, math
import numpy as np
from collections import defaultdict
out = sys.argv[sys.argv.index('--') + 1]
o = bpy.data.objects['SM_SnowFlower']
me = o.data
uv = me.uv_layers[0].data
nm = len(o.material_slots)
wa = defaultdict(float); ua = defaultdict(float); tris = defaultdict(int)
# raster overlap per material at 512
R = 512
cover = {i: np.zeros((R, R), np.uint16) for i in range(nm)}
co = np.array([v.co[:] for v in me.vertices])
for p in me.polygons:
    li = list(p.loop_indices)
    pts = [co[me.loops[i].vertex_index] for i in li]
    uvs = [np.array(uv[i].uv[:]) for i in li]
    m = p.material_index
    for k in range(1, len(li) - 1):
        a = np.cross(pts[k] - pts[0], pts[k+1] - pts[0]); wa[m] += np.linalg.norm(a) / 2
        e1 = uvs[k] - uvs[0]; e2 = uvs[k+1] - uvs[0]
        ua[m] += abs(e1[0]*e2[1] - e1[1]*e2[0]) / 2
        tris[m] += 1
        # rasterise triangle centroid-ish coverage (bbox sample)
        tri = np.array([uvs[0], uvs[k], uvs[k+1]]) * R
        x0, y0 = np.floor(tri.min(0)).astype(int); x1, y1 = np.ceil(tri.max(0)).astype(int)
        x0 = max(x0, 0); y0 = max(y0, 0); x1 = min(x1, R); y1 = min(y1, R)
        if x1 <= x0 or y1 <= y0: continue
        xs, ys = np.meshgrid(np.arange(x0, x1) + .5, np.arange(y0, y1) + .5)
        P = np.stack([xs, ys], -1)
        v0 = tri[2] - tri[0]; v1 = tri[1] - tri[0]; v2 = P - tri[0]
        d00 = v0 @ v0; d01 = v0 @ v1; d11 = v1 @ v1
        den = d00 * d11 - d01 * d01
        if abs(den) < 1e-12: continue
        d02 = v2 @ v0; d12 = v2 @ v1
        u = (d11 * d02 - d01 * d12) / den; v = (d00 * d12 - d01 * d02) / den
        inside = (u >= 0) & (v >= 0) & (u + v <= 1)
        cover[m][y0:y1, x0:x1] += inside.astype(np.uint16)
res = {}
for i, s in enumerate(o.material_slots):
    mat = s.material
    size = None
    for n in mat.node_tree.nodes:
        if n.type == 'TEX_IMAGE' and n.image and 'BaseColor' in n.image.name:
            size = n.image.size[0]
    td = math.sqrt(ua[i] / wa[i]) * size / 100 if wa[i] else None
    c = cover[i]
    res[mat.name] = {'tris': tris[i], 'world_area_cm2': wa[i] * 1e4, 'uv_area': ua[i], 'basecolor_px': size,
                     'texel_px_per_cm': td, 'uv_fill_fraction': float((c > 0).mean()),
                     'overlap_fraction_of_covered': float((c > 1).sum() / max(1, (c > 0).sum()))}
res['uv_layers'] = [l.name for l in me.uv_layers]
json.dump(res, open(out, 'w'), indent=1)
print('WROTE', out)
