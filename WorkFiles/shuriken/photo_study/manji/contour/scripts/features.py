# Contour -> DP(1.5 px) -> split into per-arm features between the four hook tips using turning-angle peaks.
import sys, json; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/manji/contour/scripts")
from common import *
def load_features(verbose=True):
    m = np.load(BASE + "/mask_final.npy")
    C = moore_trace(m); N = len(C)
    dp = douglas_peucker(C, 1.5)
    tips = json.load(open(BASE + "/tips_info.json"))
    order = ["top", "right", "bottom", "left"]           # clockwise order of tips in image coords
    ti = {k: int(np.argmin(np.hypot(*(C - np.array(tips[k]["apparent_tip"])).T))) for k in order}
    # arc length
    seg = np.hypot(*np.diff(np.vstack([C, C[:1]]), axis=0).T); s = np.concatenate([[0], np.cumsum(seg)])[:-1]; P = s[-1] + seg[-1]
    # tangent from points +-12 px of arc length -> turning angle
    def at(sv): return np.interp(sv % P, np.r_[s, P], np.r_[C[:, 0], C[0, 0]]), np.interp(sv % P, np.r_[s, P], np.r_[C[:, 1], C[0, 1]])
    w = 12.0
    xa, ya = at(s - 2 * w); xb, yb = at(s - w * 0); xc, yc = at(s + 2 * w)
    a1 = np.arctan2(yb - ya, xb - xa); a2 = np.arctan2(yc - yb, xc - xb)
    turn = np.degrees(np.angle(np.exp(1j * (a2 - a1))))   # + = right turn in image coords (clockwise traversal: convex)
    feats = {}
    for k in range(4):
        t0, t1 = order[k], order[(k + 1) % 4]
        i0, i1 = ti[t0], ti[t1]
        idx = (i0 + np.arange((i1 - i0) % N + 1)) % N
        ss = (s[idx] - s[i0]) % P
        L_ = ss[-1]
        valid = (ss > 90) & (ss < L_ - 90)
        tv = np.where(valid, np.abs(turn[idx]), 0)
        peaks = []
        for _ in range(3):
            j = int(np.argmax(tv)); peaks.append(j)
            tv[np.abs(ss - ss[j]) < 80] = 0
        peaks.sort()
        names = [f"{t0}_hook_back", f"{t0}_arm_outer", f"{t1}_arm_inner", f"{t1}_hook_inner"]
        cn = [f"{t0}_outer_elbow", f"centre_{t0}_{t1}", f"{t1}_inner_corner"]
        bounds = [0] + peaks + [len(idx) - 1]
        for e in range(4):
            feats[names[e]] = dict(idx=idx[bounds[e]:bounds[e + 1] + 1], s0=ss[bounds[e]], s1=ss[bounds[e + 1]])
        for c_ in range(3):
            j = peaks[c_]
            feats[cn[c_]] = dict(i=int(idx[j]), xy=C[idx[j]].tolist(), turn_deg=float(turn[idx[j]]))
        if verbose:
            print(f"section {t0}->{t1}: len {L_:.0f} px, corners at", [(C[idx[j]].round(0).tolist(), round(float(turn[idx[j]]), 1)) for j in peaks])
    return C, dp, feats, tips, ti, turn, s
if __name__ == "__main__":
    C, dp, feats, tips, ti, turn, s = load_features()
    print("contour points", len(C), "DP(1.5) vertices", len(dp))
    for k, v in feats.items():
        if "idx" in v: print(k, "points", len(v["idx"]), "from", C[v["idx"][0]].round(0), "to", C[v["idx"][-1]].round(0))
