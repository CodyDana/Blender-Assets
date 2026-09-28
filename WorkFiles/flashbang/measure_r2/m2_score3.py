import numpy as np, glob, os
W = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/measure_r2/"
ref = np.zeros((1254, 1254), bool); ref[:745] = np.load(W + "m2_refmask.npy")
VB = {"v1": (40, 345, "-140"), "v2": (345, 615, "165"), "v3": (615, 950, "-105"), "v4": (950, 1240, "-20")}
for f in sorted(glob.glob(W + "m2_sw_f*.npz")):
    z = np.load(f); s = []; tb = []
    for v, (x0, x1, k) in VB.items():
        O = z[k][:, x0:x1]; Rr = ref[:, x0:x1]
        s.append((O & Rr).sum() / (O | Rr).sum())
        yo = np.flatnonzero(O.any(1)); yr = np.flatnonzero(Rr.any(1)); tb.append((int(yo.min()) - int(yr.min()), int(yo.max()) - int(yr.max())))
    print(os.path.basename(f), [round(x, 3) for x in s], round(float(np.mean(s)), 4), tb)
