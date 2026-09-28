"""Stage 12: luminance profiles perpendicular to each end edge (guards), sampled along the edge line."""
import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/reference_metrology")
from fm_lib import *
import json
S2 = json.load(open(os.path.join(OUT, "fm_s02_rivet.json"))); S11 = json.load(open(os.path.join(OUT, "fm_s11_ends.json")))
def bil(a, x, y):
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int); fx = x-x0; fy = y-y0
    return (a[y0, x0]*(1-fx)*(1-fy) + a[y0, x0+1]*fx*(1-fy) + a[y0+1, x0]*(1-fx)*fy + a[y0+1, x0+1]*fx*fy)
res = {}
for i in (1, 2):
    cx, cy = S2[str(i)]["rivet_bright_centroid"]
    L = load(i) @ LUMW.astype(np.float32)
    out = {}
    for side, key in (('right', 'right_end_line_r150'), ('left', 'left_end_line_r150')):
        ln = S11[str(i)][key]; m, b = ln['slope'], ln['icpt']
        u = np.array([1.0, m]); u /= np.linalg.norm(u)          # along the line (image x,y down)
        if side == 'left': u = -u                               # pointing away from rivet
        # foot of rivet on the line
        p0 = np.array([cx, m*cx + b]); t = np.dot(np.array([cx, cy]) - p0, u); foot = p0 + t*u
        nrm = np.array([-u[1], u[0]])
        # inward normal = towards fan interior (towards the rivet-up direction)
        if nrm[1] > 0: nrm = -nrm
        prof = {}
        for s in range(60, 400, 20):
            base = foot + s*u
            if not (5 < base[0] < 795 and 5 < base[1] < 795): continue
            ks = np.arange(-6, 50, 1.0)
            vals = []
            for k in ks:
                pts = base[None, :] + k*nrm[None, :] + np.linspace(-3, 3, 7)[:, None]*u[None, :]
                vals.append(float(np.mean(bil(L, pts[:, 0], pts[:, 1]))))
            prof[s] = [round(v, 3) for v in vals]
        out[side] = dict(offsets=list(range(-6, 50)), prof=prof)
    res[i] = out
json.dump(res, open(os.path.join(OUT, "fm_s12_guardprof.json"), "w"))
for i in (1, 2):
    for side in ('right', 'left'):
        for s, v in res[i][side]['prof'].items():
            print(f"G{i}{side[0]} s={s:3d} " + " ".join(f"{int(x*100):2d}" for x in v))
