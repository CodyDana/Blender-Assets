import sys, numpy as np, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/metrology")
from fb_lib import *
ref = load_srgb()
g = ref[..., 1] - 0.5*(ref[..., 0] + ref[..., 2])
E = json.load(open(DBG + "/fb_edges.json"))
out = {}
for v in ['v1', 'v2', 'v3', 'v4']:
    bl = E[v]['body_web_B_C']; xl, xr = bl['left'][0], bl['right'][0]
    c = 0.5*(xl+xr); R = 0.5*(xr-xl)
    out[v] = {}
    for row, cy in dict(A=326, B=442, C=562).items():
        p = g[cy-3:cy+4, int(xl)-2:int(xr)+3].mean(0)
        p = gauss_blur(np.tile(p[None], (3, 1)), 0.8)[1]
        x = np.arange(int(xl)-2, int(xr)+3)
        t = 0.012
        ins = p < t
        segs = []; i = 0
        while i < len(p):
            if ins[i]:
                j = i
                while j < len(p) and ins[j]: j += 1
                segs.append((float(x[i]), float(x[j-1]))); i = j
            else: i += 1
        segs = [s for s in segs if s[1]-s[0] > 8]
        az = []
        for a, b in segs:
            ua = np.clip((a - c)/R, -1, 1); ub = np.clip((b - c)/R, -1, 1)
            az.append((round(a, 1), round(b, 1), round(float(np.degrees(np.arcsin(ua))), 1), round(float(np.degrees(np.arcsin(ub))), 1)))
        out[v][row] = az
        print(v, row, f"c={c:.1f} R={R:.1f}", az)
json.dump(out, open(DBG + "/fb_holeaz.json", "w"))
