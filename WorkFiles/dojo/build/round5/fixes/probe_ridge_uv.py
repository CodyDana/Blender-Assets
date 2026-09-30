"""Read-only probe: the mean T_DJ_RoofTile_BC colour sampled at the UV of each face (area weighted) of the ridge vs the
roof slope; and the ridge faces' UV extents. Run on Assets/Dojo/DojoOutbuildings.blend."""
import bpy, numpy as np, json
from pathlib import Path
img = bpy.data.images.load(r"C:\Users\Cody\Desktop\Blender_Projects\Exports\DojoKit\Materials\Textures\T_DJ_RoofTile_BC.png")
W, H = img.size
px = np.array(img.pixels[:]).reshape(H, W, 4)[..., :3]
def lin2s(c): return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)
out = {}
for name in ("SM_DKO_Roof_Ridge", "SM_DKO_Roof_Slope"):
    o = bpy.data.objects[name]
    me = o.data
    uv = me.uv_layers[0].data
    acc, wsum = np.zeros(3), 0.0
    vert = {"up": [np.zeros(3), 0.0], "side": [np.zeros(3), 0.0]}
    spans = []
    for p in me.polygons:
        if not me.materials[p.material_index].name.startswith("M_DJ_RoofTile"):
            continue
        us = np.array([uv[li].uv[:] for li in p.loop_indices])
        c = us.mean(0)
        spans.append(float(np.ptp(us[:, 0]) + np.ptp(us[:, 1])))
        x, y = int((c[0] % 1) * W) % W, int((c[1] % 1) * H) % H
        col = px[y, x]
        acc += col * p.area; wsum += p.area
        k = "up" if abs(p.normal.z) > 0.7 else "side"
        vert[k][0] += col * p.area; vert[k][1] += p.area
    out[name] = {"mean_srgb": (lin2s(acc / wsum) * 255).round(1).tolist(), "area": round(wsum, 3),
                 "by_normal": {k: ((lin2s(v[0] / v[1]) * 255).round(1).tolist() if v[1] else None, round(v[1], 3)) for k, v in vert.items()},
                 "uv_span_median": float(np.median(spans))}
print("PROBE", json.dumps(out))
