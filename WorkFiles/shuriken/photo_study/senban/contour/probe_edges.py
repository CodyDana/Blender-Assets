# Probe: averaged profiles across the hole sides and the outer top side, to locate the crisp
# metal edges hidden behind the soft shadow/defocus ramps.
import sys, math, numpy as np
D = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/senban/contour/"
sys.path.insert(0, D)
from measure import run
from strips import unwrap
from hole_strips import hole_unwrap

np.set_printoptions(linewidth=260)
R = run(); A = R["_arrays"]
L, Yw = A["L"], A["Yw"]
for k, nm in enumerate(["top", "right", "bottom", "left"]):
    ts, ds, o, nout, u = hole_unwrap(A, k, d0=-30, d1=25, img=dict(L=L, Y=Yw))
    n = len(ts); sl = slice(int(0.15 * n), int(0.85 * n))
    Lp = o["L"][:, sl].mean(1); Yp = o["Y"][:, sl].mean(1)
    print(f"HOLE {nm}: d", ds.astype(int)); print("  L", Lp.round(0).astype(int)); print("  Y", Yp.round(0).astype(int))
    g = np.diff(Lp); print("  dL", g.round(0).astype(int))
# outer top: steepest drop depth per station in [5, 22]
ts, ds, o, _ = unwrap(A, 0, d0=-15, d1=45, ncol=860, img=dict(L=L, Y=Yw))
Ls = o["L"]
k = 7
Lsm = np.array([Ls[:, max(0, c - k):c + k + 1].mean(1) for c in range(Ls.shape[1])]).T
g = np.diff(Lsm, axis=0)          # derivative with depth
dmid = 0.5 * (ds[1:] + ds[:-1])
sel = (dmid >= 4) & (dmid <= 22)
print("TOP outer: t, steepest-drop depth, L before/after, black-to-plate rise depth")
for t in [0.02, 0.04, 0.06, 0.08, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.92, 0.94, 0.96, 0.98]:
    c = int(round(t * (Ls.shape[1] - 1)))
    gi = np.where(sel, g[:, c], 1e9); j = int(np.argmin(gi))
    sel2 = (dmid > dmid[j] + 3) & (dmid <= 45)
    gj = np.where(sel2, g[:, c], -1e9); j2 = int(np.argmax(gj))
    print(f"  t={t:.2f} edge d={dmid[j]:5.1f} (dL={g[j, c]:6.1f})  crease d={dmid[j2]:5.1f} (dL={g[j2, c]:5.1f})  prof:", Lsm[::3, c].round(0).astype(int))
