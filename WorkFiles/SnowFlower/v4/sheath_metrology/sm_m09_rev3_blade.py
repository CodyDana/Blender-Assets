# sm_m09: slice the rev-3 master blade (read-only; the file is never saved)
# blade axis = +Z (tip at z max), width = X, thickness = Y
import bpy, json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
dg = bpy.context.evaluated_depsgraph_get()

def world_mesh(names):
    V, E = [], []
    off = 0
    for n in names:
        o = bpy.data.objects[n]
        oe = o.evaluated_get(dg)
        me = oe.to_mesh()
        M = np.array(o.matrix_world)
        v = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", v); v = v.reshape(-1, 3)
        v = (np.c_[v, np.ones(len(v))] @ M.T)[:, :3]
        e = np.empty(len(me.edges) * 2, int); me.edges.foreach_get("vertices", e); e = e.reshape(-1, 2)
        V.append(v); E.append(e + off); off += len(v)
        oe.to_mesh_clear()
    return np.vstack(V), np.vstack(E)

def slice_z(V, E, z):
    a = V[E[:, 0]]; b = V[E[:, 1]]
    s = (a[:, 2] - z) * (b[:, 2] - z) <= 0
    a = a[s]; b = b[s]
    dz = b[:, 2] - a[:, 2]
    t = np.where(np.abs(dz) > 1e-12, (z - a[:, 2]) / np.where(np.abs(dz) > 1e-12, dz, 1), 0.5)
    return a + (b - a) * t[:, None]

names_blade = ["SF_Blade"]
relief = [o.name for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith("SF_BladeRelief")]
guard = [o.name for o in bpy.data.objects if o.type == 'MESH' and (o.name.startswith("SF_Guard") or o.name.startswith("SF_GuardFlower"))]
Vb, Eb = world_mesh(names_blade)
Vr, Er = world_mesh(relief)
Vg, Eg = world_mesh(guard)
print("blade z range", Vb[:, 2].min(), Vb[:, 2].max())
tipz = Vb[:, 2].max(); tip = Vb[Vb[:, 2].argmax()]
print("tip point", tip)
# guard lower (blade-side) faces
print("guard z range", Vg[:, 2].min(), Vg[:, 2].max())
rows = []
for z in np.r_[np.arange(0.14, 1.08, 0.01), [1.075, 1.08, 1.083]]:
    p = slice_z(Vb, Eb, z)
    if len(p) == 0:
        continue
    r = dict(z=float(z), xmin=float(p[:, 0].min()), xmax=float(p[:, 0].max()), ymin=float(p[:, 1].min()), ymax=float(p[:, 1].max()))
    pr = slice_z(Vr, Er, z)
    if len(pr):
        r.update(rxmin=float(pr[:, 0].min()), rxmax=float(pr[:, 0].max()), rymin=float(pr[:, 1].min()), rymax=float(pr[:, 1].max()))
    pg = slice_z(Vg, Eg, z)
    if len(pg):
        r.update(gxmin=float(pg[:, 0].min()), gxmax=float(pg[:, 0].max()), gymin=float(pg[:, 1].min()), gymax=float(pg[:, 1].max()))
    rows.append(r)
for r in rows:
    print("z %.3f  blade x [%+.4f %+.4f] w %.4f c %+.4f  t [%+.4f %+.4f]  relief y [%s] guard %s" % (
        r["z"], r["xmin"], r["xmax"], r["xmax"] - r["xmin"], (r["xmax"] + r["xmin"]) / 2, r["ymin"], r["ymax"],
        ("%+.4f %+.4f x %+.4f %+.4f" % (r["rymin"], r["rymax"], r["rxmin"], r["rxmax"])) if "rymin" in r else "-",
        ("x %+.4f %+.4f y %+.4f %+.4f" % (r["gxmin"], r["gxmax"], r["gymin"], r["gymax"])) if "gxmin" in r else "-"))
# edge vs spine: which side is sharp? look at the blade cross-section at mid (thin side)
z = 0.6
p = slice_z(Vb, Eb, z)
for side, sel in (("xmin side", p[:, 0] < p[:, 0].min() + 0.004), ("xmax side", p[:, 0] > p[:, 0].max() - 0.004)):
    q = p[sel]
    print(side, "thickness within 4mm of edge:", q[:, 1].max() - q[:, 1].min())
mats = {}
json.dump(dict(tip=tip.tolist(), rows=rows, relief_objects=relief), open(os.path.join(HERE, "sm_s09.json"), "w"), indent=0)
