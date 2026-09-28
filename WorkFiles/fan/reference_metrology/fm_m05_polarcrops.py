"""Stage 5: polar crops (theta ranges) with local contrast stretch for visual rib/pleat counting."""
import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/reference_metrology")
from fm_lib import *
import json
spec = json.loads(sys.argv[sys.argv.index('--')+1])
for i, t0, t1, r0, r1, name in spec:
    P = np.load(os.path.join(OUT, f"fm_polar{i}.npy"))
    j0 = int(round((t0+20)*10)); j1 = int(round((t1+20)*10))
    C = P[r0:r1, j0:j1][::-1]      # r up
    C = C[:, ::-1]                 # theta increasing to the left = same handedness as photo
    L = C @ LUMW.astype(np.float32)
    lo, hi = np.percentile(L, 2), np.percentile(L, 90)
    C = np.clip((C-lo)/(hi-lo+1e-6), 0, 1)
    # tick marks every 5 deg along the bottom row, every 1 deg short
    C = C.copy()
    for k in range(C.shape[1]):
        tdeg = t1 - k*0.1
        if abs(tdeg*10 - round(tdeg)*10) < 1e-6:
            n = 12 if round(tdeg) % 5 == 0 else 5
            C[-n:, k] = [1, 0, 0] if round(tdeg) % 10 == 0 else [1, 1, 0]
    save_png(C, name, 1)
print("done")
