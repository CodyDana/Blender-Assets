"""Stage 16: polar crop with radius gridlines (every 10 px, red every 50) for visual reading of radii."""
import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/reference_metrology")
from fm_lib import *
import json
for i, t0, t1, r0, r1, sc, gain, name in json.loads(sys.argv[sys.argv.index('--')+1]):
    P = np.load(os.path.join(OUT, f"fm_polar{i}.npy"))
    j0 = int(round((t0+20)*10)); j1 = int(round((t1+20)*10))
    C = np.clip(P[r0:r1, j0:j1]*gain, 0, 1)**0.7
    C = np.repeat(np.repeat(C, sc, 0), sc, 1)
    for r in range(r0, r1):
        if r % 10 == 0:
            y = (r - r0)*sc
            C[y, ::4] = [1, 0, 0] if r % 50 == 0 else [1, 1, 0]
    C = C[::-1, ::-1]
    save_png(C, name, 1)
print("done")
