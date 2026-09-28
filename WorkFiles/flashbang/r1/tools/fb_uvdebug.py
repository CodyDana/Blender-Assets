"""DEV: per-island UV overlap / mirrored / tiny-triangle report for each LOD (numpy, bundled python)."""
import sys, math
from pathlib import Path
P = Path(r"C:/Users/Cody/Desktop/Blender_Projects")
sys.path.insert(0, str(P / "Scripts/props"))
import numpy as np
from props_lib import flashbang_geom as G
from props_lib.flashbang_spec import FLASHBANG as S

def fix(mb):
    V = np.array(mb.verts); votes = {}
    for f in mb.faces:
        Pp = V[list(f.v[:3])]; n = np.cross(Pp[1]-Pp[0], Pp[2]-Pp[0]); uv = np.array(f.uv[:3])
        a = (uv[1,0]-uv[0,0])*(uv[2,1]-uv[0,1])-(uv[2,0]-uv[0,0])*(uv[1,1]-uv[0,1])
        votes[f.island] = votes.get(f.island, 0) + np.sign(a)*np.linalg.norm(n)
    flip = {k for k, v in votes.items() if v < 0}
    for f in mb.faces:
        if f.island in flip: f.uv = tuple((-u, v) for u, v in f.uv)
mbs = [G.build_lod(S, l)[0] for l in range(3)]
for mb in mbs: fix(mb)
pk = G.pack_islands(mbs)
for lod, mb in enumerate(mbs):
    V = np.array(mb.verts)
    tris = []
    for f in mb.faces:
        uv = [pk.uv(f.island, u, v) for u, v in f.uv]
        for k in range(1, len(f.v) - 1):
            tris.append((f.island, f.part, (f.v[0], f.v[k], f.v[k+1]), (uv[0], uv[k], uv[k+1])))
    mir = {}; small = {}
    for isl, part, vv, uv in tris:
        Pp = V[list(vv)]; n = np.cross(Pp[1]-Pp[0], Pp[2]-Pp[0]); a3 = 0.5*np.linalg.norm(n)
        u = np.array(uv); a = (u[1,0]-u[0,0])*(u[2,1]-u[0,1])-(u[2,0]-u[0,0])*(u[1,1]-u[0,1])
        if a3 < 0.005: small[isl] = small.get(isl, 0) + 1
        # handedness: MikkT style
        e1, e2 = Pp[1]-Pp[0], Pp[2]-Pp[0]; d1, d2 = u[1]-u[0], u[2]-u[0]
        det = d1[0]*d2[1]-d1[1]*d2[0]
        if abs(det) < 1e-20: mir[isl+'(collapsed)'] = mir.get(isl+'(collapsed)', 0)+1; continue
        dpu = (e1*d2[1]-e2*d1[1])/det; dpv = (e2*d1[0]-e1*d2[0])/det
        if np.dot(np.cross(dpu, dpv), n) < 0: mir[isl] = mir.get(isl, 0) + 1
    # overlap per island pair (bbox of triangles), coarse: raster each triangle at 4096 and count shared texels
    R = 4096; owner = {}
    over = {}
    for ti, (isl, part, vv, uv) in enumerate(tris):
        u = np.array(uv) * R
        x0, y0 = np.floor(u.min(0)).astype(int); x1, y1 = np.ceil(u.max(0)).astype(int)
        xs, ys = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
        def edge(a, b, px, py): return (b[0]-a[0])*(py-a[1])-(b[1]-a[1])*(px-a[0])
        w0 = edge(u[1], u[2], xs, ys); w1 = edge(u[2], u[0], xs, ys); w2 = edge(u[0], u[1], xs, ys)
        ins = ((w0 > 1e-3) & (w1 > 1e-3) & (w2 > 1e-3)) | ((w0 < -1e-3) & (w1 < -1e-3) & (w2 < -1e-3))
        for x, y in zip(xs[ins].astype(int), ys[ins].astype(int)):
            k = (x, y)
            if k in owner and owner[k] != ti:
                key = (tris[owner[k]][0], isl); over[key] = over.get(key, 0) + 1
            else: owner[k] = ti
    print("LOD", lod, "mirrored/collapsed", mir, "small", small, "overlap", dict(list(over.items())[:10]))
