import sys, math, dataclasses, time
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
import numpy as np
from props_lib.fan_spec import FAN
from props_lib import fan_fold as F
SP = dataclasses.replace(FAN, rib_thick_mm=0.37)
print("stack", SP.stack_mm, "leaf pitch z", SP.leaf_z_pitch, flush=True)
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
    @staticmethod
    def _step_limit(s_lo):
        return 0.01 if s_lo < 0.1 else 0.1
def evaluate(fa, ss):
    out = []
    for s in ss:
        g = fa.solve(s)
        G = fa.symmetry(1, s)
        a_rib = F.apply(g.TA, fa.A_rib); b_prev = F.apply(np.linalg.inv(G), F.apply(g.TB, fa.B_rib))
        v = np.linalg.norm(a_rib - b_prev, axis=1).max(); m = np.linalg.norm(F.apply(g.TA, fa.A_mid) - F.apply(g.TB, fa.B_mid), axis=1).max()
        out.append((s, v, m))
    return out
t0 = time.time()
base = Alt(SP)
for r in evaluate(base, (0.8, 0.5, 0.2, 0.05, 0.0)): print("base s=%.2f valley=%.4f mountain=%.4f" % r, flush=True)
print("t", time.time() - t0, flush=True)
def obj(p):
    fa = Alt(SP, p)
    return max(max(v, m) for _, v, m in evaluate(fa, (0.6, 0.3, 0.0)))
# Nelder-Mead
n = 6; X = [np.zeros(n)] + [np.eye(n)[k] * 0.3 for k in range(n)]
Fv = [obj(x) for x in X]
print("init", min(Fv), flush=True)
for it in range(150):
    o = np.argsort(Fv); X = [X[k] for k in o]; Fv = [Fv[k] for k in o]
    c = np.mean(X[:-1], 0); xr = c + (c - X[-1]); fr = obj(xr)
    if fr < Fv[0]:
        xe = c + 2 * (c - X[-1]); fe = obj(xe)
        X[-1], Fv[-1] = (xe, fe) if fe < fr else (xr, fr)
    elif fr < Fv[-2]:
        X[-1], Fv[-1] = xr, fr
    else:
        xc = c + 0.5 * (X[-1] - c); fc = obj(xc)
        if fc < Fv[-1]:
            X[-1], Fv[-1] = xc, fc
        else:
            X = [X[0]] + [X[0] + 0.5 * (x - X[0]) for x in X[1:]]; Fv = [Fv[0]] + [obj(x) for x in X[1:]]
    if it % 10 == 0: print(it, round(min(Fv), 5), np.round(X[int(np.argmin(Fv))], 3), round(time.time() - t0), flush=True)
p = X[int(np.argmin(Fv))]
print("best", p.tolist(), min(Fv), flush=True)
fa = Alt(SP, p)
for r in evaluate(fa, (0.9, 0.7, 0.5, 0.3, 0.2, 0.1, 0.05, 0.02, 0.01, 0.0)): print("opt s=%.2f valley=%.4f mountain=%.4f" % r, flush=True)
