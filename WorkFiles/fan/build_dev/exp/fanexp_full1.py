import sys, math, time
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
import numpy as np
from props_lib.fan_spec import FAN
from props_lib import fan_fold as F
from props_lib import fan_geom as G
t0 = time.time()
OFF = None
fs = F.FoldSolver(FAN, OFF); print("closed tilt", fs.page_tilt_deg(0.0))
mb, info, sa = G.build_lod(FAN, 0, fs.tpl)
print(info, time.time()-t0)
P, T, B = mb.arrays()
names = mb.bone_names
TG = np.array(mb.TG); TP = np.array(mb.TP)
print("tris", len(T), "verts", len(P))
bone_of_tri = B[T[:, 0]]
def pose(s):
    Ts = {}
    for i, M in enumerate(fs.sticks_T(s)): Ts[f"stick_{i:02d}"] = M
    for j, M in enumerate(fs.face_T(s)): Ts[f"leaf_{j:02d}"] = M
    Ts["pivot"] = np.eye(4)
    Q = np.empty_like(P)
    for bi, bn in enumerate(names):
        m = B == bi
        Q[m] = F.apply(Ts[bn], P[m])
    return Q
# groups: leaf faces (front layer) and sticks
is_leaf = np.array([p in ("leaf", "flaps") for p in TP])
is_stick = TP == "sticks"; is_rivet = TP == "rivet"
grp = TG
def leaf_face_index(g):
    return int(g.split("_")[1]) if g.startswith("leaf_") else (-1 if g == "flap_front" else 50)
lfi = np.array([leaf_face_index(g) if l else -99 for g, l in zip(grp, is_leaf)])
stick_idx = np.array([int(g.split("_")[1]) if g.startswith("stick_") else -1 for g in grp])
ss = [1.0, 0.9, 0.75, 0.6, 0.45, 0.3, 0.2, 0.12, 0.08, 0.05, 0.03, 0.02, 0.012, 0.008, 0.005, 0.003, 0.0015, 0.0]
for s in ss:
    Q = pose(s)
    tri = Q[T]
    c = fs.cracks(s)
    L = np.nonzero(is_leaf)[0]; S = np.nonzero(is_stick)[0]; Rv = np.nonzero(is_rivet)[0]
    # leaf vs leaf: exclude same or adjacent faces (|di|<=1); flaps adjacent to faces 0 / 49
    ex = lambda a, b: np.abs(lfi[L][a] - lfi[L][b]) <= 1
    n_ll, ex_ll = F.count_intersections(tri[L], tri[L], same=True, exclude=ex)
    n_ls, ex_ls = F.count_intersections(tri[L], tri[S])
    # flaps belong to guards: exclude flap vs its own guard
    ex2 = lambda a, b: stick_idx[S][a] == stick_idx[S][b]
    n_ss, ex_ss = F.count_intersections(tri[S], tri[S], same=True, exclude=ex2)
    n_lr, _ = F.count_intersections(tri[L], tri[Rv])
    n_sr, ex_sr = F.count_intersections(tri[S], tri[Rv])
    # leaf z extent relative to the guards' planes
    zl = tri[L][:, :, 2]
    print(f"s={s:.4f} open={FAN.opening_at(s):7.2f} crack v={c['valley_mm']:.4f} m={c['mountain_mm']:.4f} off={c['leaf_off_rib_mm']:.4f} "
          f"hits LL={n_ll} LS={n_ls} SS={n_ss} LR={n_lr} SR={n_sr} leafz=[{zl.min():.2f},{zl.max():.2f}]", ex_ls[:3], ex_ll[:3], ex_ss[:2], ex_sr[:2])
print("time", time.time() - t0)
