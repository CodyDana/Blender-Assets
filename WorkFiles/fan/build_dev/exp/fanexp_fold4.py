import sys, math, dataclasses
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
import numpy as np
from props_lib.fan_spec import FAN
from props_lib import fan_fold as F
SP = dataclasses.replace(FAN, rib_thick_mm=0.37)
print("stack", SP.stack_mm, "leaf pitch z", SP.leaf_z_pitch)
class Alt(F.FoldSolver):
    W_ANCHOR = 0.15
    def __init__(self, spec, dmid=None):
        super().__init__(spec)
        if dmid is not None:
            self.A_mid = self.A_mid + dmid.reshape(2, 3); self.B_mid = self.A_mid.copy()
            self.cA = np.vstack([self.A_rib, self.A_mid]).mean(0); self.cB = np.vstack([self.B_mid, self.B_rib]).mean(0)
    def _residual(self, x, tA, tB):
        TA = F.rigid(F.rotvec(x[0:3]), self.cA, x[3:6]); TB = F.rigid(F.rotvec(x[6:9]), self.cB, x[9:12])
        G = self.symmetry(1, self._s)
        a_rib = F.apply(TA, self.A_rib); b_rib = F.apply(TB, self.B_rib)
        return np.concatenate([(a_rib - F.apply(np.linalg.inv(G), b_rib)).ravel(),
                               (F.apply(TA, self.A_mid) - F.apply(TB, self.B_mid)).ravel(),
                               self.W_ANCHOR * (a_rib - tA).ravel(), self.W_ANCHOR * (b_rib - tB).ravel()])
    def _solve(self, s, x0):
        self._s = s; return super()._solve(s, x0)
def evaluate(fa, ss=(0.8, 0.5, 0.2, 0.05, 0.0)):
    out = []
    for s in ss:
        g = fa.solve(s)
        G = fa.symmetry(1, s)
        a_rib = F.apply(g.TA, fa.A_rib); b_prev = F.apply(np.linalg.inv(G), F.apply(g.TB, fa.B_rib))
        v = np.linalg.norm(a_rib - b_prev, axis=1).max(); m = np.linalg.norm(F.apply(g.TA, fa.A_mid) - F.apply(g.TB, fa.B_mid), axis=1).max()
        out.append((s, v, m))
    return out
base = Alt(SP)
for r in evaluate(base): print("base s=%.2f valley=%.4f mountain=%.4f" % r)
def obj(p):
    fa = Alt(SP, p)
    return max(max(v, m) for _, v, m in evaluate(fa, (0.5, 0.0)))
from itertools import product
p = np.zeros(6); f = obj(p); step = 0.2
print("start", f)
for it in range(60):
    improved = False
    for k in range(6):
        for sgn in (1, -1):
            q = p.copy(); q[k] += sgn*step
            fq = obj(q)
            if fq < f - 1e-6:
                p, f, improved = q, fq, True
    if not improved:
        step *= 0.5
        if step < 0.005: break
    print(it, round(f, 5), np.round(p, 3), step)
fa = Alt(SP, p)
for r in evaluate(fa, (0.9, 0.7, 0.5, 0.3, 0.2, 0.1, 0.05, 0.02, 0.01, 0.0)): print("opt s=%.2f valley=%.4f mountain=%.4f" % r)
