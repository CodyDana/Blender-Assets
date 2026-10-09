import bpy, sys, json, numpy as np
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
exec(compile(open(HERE / "arD_analyse.py").read().split("def split_shells")[0].split("def uv_overlap")[1].join(["def uv_overlap", ""]) if False else "", "x", "exec"))
def uv_overlap(tris, res_px):
    grid = np.zeros((res_px, res_px), np.uint16)
    for a, b, c in tris:
        mn = np.clip(np.floor(np.minimum(np.minimum(a, b), c) * res_px).astype(int), 0, res_px - 1)
        mx = np.clip(np.ceil(np.maximum(np.maximum(a, b), c) * res_px).astype(int), 0, res_px)
        if mx[0] <= mn[0] or mx[1] <= mn[1]:
            continue
        xs = (np.arange(mn[0], mx[0]) + 0.5) / res_px; ys = (np.arange(mn[1], mx[1]) + 0.5) / res_px
        X, Y = np.meshgrid(xs, ys)
        w0 = (b[0] - X) * (c[1] - Y) - (c[0] - X) * (b[1] - Y); w1 = (c[0] - X) * (a[1] - Y) - (a[0] - X) * (c[1] - Y); w2 = (a[0] - X) * (b[1] - Y) - (b[0] - X) * (a[1] - Y)
        ins = ((w0 > 0) & (w1 > 0) & (w2 > 0)) | ((w0 < 0) & (w1 < 0) & (w2 < 0))
        grid[mn[1]:mx[1], mn[0]:mx[0]] += ins.astype(np.uint16)
    return int((grid > 1).sum())
out = {}
for f in sorted((HERE / "lmtest").glob("*.fbx")):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(f))
    for ob in sorted([o for o in bpy.data.objects if o.type == "MESH"], key=lambda o: o.name):
        me = ob.data; me.calc_loop_triangles()
        lay = me.uv_layers.get("LightMapUV")
        if lay is None: continue
        U = np.array([d.uv for d in lay.data]); LT = np.array([t.loops[:] for t in me.loop_triangles])
        out[f"{f.stem}:{ob.name}"] = [uv_overlap(U[LT], r) for r in (256, 1024)]
print("LM", json.dumps(out))
