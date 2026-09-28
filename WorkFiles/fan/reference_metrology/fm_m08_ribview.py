"""Stage 8: gamma-boosted polar strips of the whole radius range with detected rib-band minima (red) and leaf maxima (green) ticked."""
import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/reference_metrology")
from fm_lib import *
import json
E = json.load(open(os.path.join(OUT, "fm_s07_extrema.json")))
args = json.loads(sys.argv[sys.argv.index('--')+1])
for i, t0, t1, r0, r1, sc, name in args:
    P = np.load(os.path.join(OUT, f"fm_polar{i}.npy"))
    j0 = int(round((t0+20)*10)); j1 = int(round((t1+20)*10))
    C = P[r0:r1, j0:j1]
    C = np.clip(C/0.35, 0, 1)**0.6
    C = C[::-1, ::-1].copy()
    H = C.shape[0]
    pad = np.ones((14, C.shape[1], 3), np.float32)
    C = np.concatenate([pad, C, pad.copy()], 0)
    def col(t): return int(round((t1 - t)*10))
    mins = sorted(set(E[str(i)]['rib']['min_deg'])); maxs = sorted(set(E[str(i)]['leaf']['max_deg']))
    for t in mins:
        k = col(t)
        if 0 <= k < C.shape[1]: C[:14, k] = [1, 0, 0]
    for t in maxs:
        k = col(t)
        if 0 <= k < C.shape[1]: C[-14:, k] = [0, 0.7, 0]
    for t in range(int(np.ceil(t0)), int(t1)+1):
        k = col(t)
        if 0 <= k < C.shape[1] and t % 5 == 0: C[:6 if t % 10 else 14, k] = [0, 0, 1]
    save_png(C, name, sc)
print("done")
