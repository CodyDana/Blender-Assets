import sys, math
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
import numpy as np
from props_lib.fan_spec import FAN
from props_lib import fan_fold as F
fs = F.FoldSolver(FAN)
def cracks(fs, s, TA, TB):
    G = fs.symmetry(1, s); G1 = fs.symmetry(1, 1.0)
    a_rib = F.apply(TA, fs.A_rib); b_rib_prev = F.apply(np.linalg.inv(G) @ TB @ G1, F.apply(np.linalg.inv(G1), fs.B_rib))
    valley = np.linalg.norm(a_rib - b_rib_prev, axis=1).max()
    mount = np.linalg.norm(F.apply(TA, fs.A_mid) - F.apply(TB, fs.B_mid), axis=1).max()
    tA, tB = fs._targets(s)
    off = max(np.linalg.norm(a_rib - tA, axis=1).max(), np.linalg.norm(F.apply(TB, fs.B_rib) - tB, axis=1).max())
    return valley, mount, off
for s in [0.8, 0.4, 0.1, 0.02, 0.0]:
    g = fs.solve(s)
    print("current  s=%.3f valley=%.4f mountain=%.4f off_rib=%.4f" % ((s,) + cracks(fs, s, g.TA, g.TB)))
# alternative objective
class Alt(F.FoldSolver):
    W_ANCHOR = 0.15
    def _residual(self, x, tA, tB):
        RA, RB = F.rotvec(x[0:3]), F.rotvec(x[6:9])
        TA = F.rigid(RA, self.cA, x[3:6]); TB = F.rigid(RB, self.cB, x[9:12])
        s = self._s
        G = self.symmetry(1, s)
        a_rib = F.apply(TA, self.A_rib); b_rib = F.apply(TB, self.B_rib)
        b_prev = F.apply(np.linalg.inv(G), b_rib)
        return np.concatenate([(a_rib - b_prev).ravel(), (F.apply(TA, self.A_mid) - F.apply(TB, self.B_mid)).ravel(),
                               self.W_ANCHOR * (a_rib - tA).ravel(), self.W_ANCHOR * (b_rib - tB).ravel()])
    def _solve(self, s, x0):
        self._s = s
        return super()._solve(s, x0)
for w in (0.3, 0.15, 0.05):
    Alt.W_ANCHOR = w
    fa = Alt(FAN)
    for s in [0.8, 0.4, 0.1, 0.02, 0.0]:
        g = fa.solve(s)
        print("alt w=%.2f s=%.3f valley=%.4f mountain=%.4f off_rib=%.4f" % ((w, s) + cracks(fa, s, g.TA, g.TB)))
