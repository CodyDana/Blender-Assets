import bpy, numpy as np
o = bpy.data.objects["SM_SnowFlower_Sheath_LOD0"]; me = o.data
mats = [m.name for m in me.materials]
V = np.array([v.co[:] for v in me.vertices]) * 1000
for p in me.polygons:
    pass
cz = np.array([p.center[2] for p in me.polygons]) * 1000
cy = np.array([p.center[1] for p in me.polygons]) * 1000
cx = np.array([p.center[0] for p in me.polygons]) * 1000
mi = np.array([p.material_index for p in me.polygons])
nz = np.array([p.normal[:] for p in me.polygons])
K = 0.687
for r0, r1 in [(20, 31.5), (31.5, 45), (45, 100), (100, 145), (145, 172), (172, 200)]:
    z0, z1 = (r0 - 304) * K, (r1 - 304) * K
    sel = (cz >= z0) & (cz < z1)
    print(f"rows {r0}-{r1}: faces {sel.sum()}  by mat", {mats[k]: int((sel & (mi == k)).sum()) for k in range(len(mats))},
          "x", np.round([cx[sel].min(), cx[sel].max()], 1) if sel.any() else None, "y", np.round([cy[sel].min(), cy[sel].max()], 1) if sel.any() else None)
# lacquer faces in throat rows: are there outward (core outer) faces?
z0, z1 = (45 - 304) * K, (140 - 304) * K
sel = (cz >= z0) & (cz < z1) & (mi == mats.index("M_SnowFlower_Sheath_Lacquer"))
r = np.hypot(cx[sel], cy[sel]); print("lacquer faces in throat rows", sel.sum(), "radial pct", np.percentile(r, [5, 50, 95]).round(1))
print("uv layers", [u.name for u in me.uv_layers])
