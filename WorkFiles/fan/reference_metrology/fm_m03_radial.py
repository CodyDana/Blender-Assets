"""Stage 3: radial extents vs theta (outer silhouette radius, leaf inner edge) and angular profiles in the leaf and bare-rib bands."""
import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/reference_metrology")
from fm_lib import *
import json
res = {}
for i in (1, 2):
    P = np.load(os.path.join(OUT, f"fm_polar{i}.npy"))  # [r, th]
    lum = P @ LUMW.astype(np.float32)
    bg = 1.0 if i == 1 else 0.9647
    dark = lum < bg - 0.12
    nth = lum.shape[1]; th = -20 + 0.1*np.arange(nth)
    # outer radius: last dark r scanning outward with at most small gaps
    rout = np.full(nth, np.nan)
    for j in range(nth):
        col = dark[:, j]
        nz = np.nonzero(col)[0]
        if len(nz): rout[j] = nz.max()
    np.save(os.path.join(OUT, f"fm_rout{i}.npy"), rout)
    # print outer radius every 2 deg
    tab = {f"{t:.0f}": (None if np.isnan(rout[j]) else int(rout[j])) for j, t in enumerate(th) if abs(t*10 % 20) < 1e-6 or abs((t*10) % 20 - 20) < 1e-6}
    res[i] = dict(rout_every2deg=tab)
json.dump(res, open(os.path.join(OUT, "fm_s03_radial.json"), "w"), indent=0)
print("FMRES", json.dumps(res))
