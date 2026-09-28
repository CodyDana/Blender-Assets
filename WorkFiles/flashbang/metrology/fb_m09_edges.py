import sys, numpy as np, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/metrology")
from fb_lib import *
ref = load_srgb()
def edge(y0, y1, xa, xb):
    p = ref[y0:y1+1, :, :].mean(0)          # W x 3
    p = gauss_blur(p[None].repeat(3, 0), 0.8)[1] if False else p
    g = np.abs(p[2:] - p[:-2]).sum(1) / 2    # gradient at x=1..W-2
    xs = np.arange(1, len(p)-1)
    m = (xs >= xa) & (xs <= xb)
    i = np.argmax(np.where(m, g, -1))
    if 0 < i < len(g)-1:
        a, b, c = g[i-1], g[i], g[i+1]; d = (a - c) / (2*(a - 2*b + c) + 1e-9)
    else: d = 0
    return float(xs[i] + d), float(g[i])
# (label, y0, y1, left window, right window)
J = {
 'v1': [('sleeve', 215, 250, (55, 72), None), ('body_web_A_B', 375, 395, (60, 78), (240, 256)), ('body_web_B_C', 490, 515, (60, 78), (240, 256)),
        ('body_low', 600, 620, (60, 78), (240, 256)), ('cap', 650, 690, (50, 66), (250, 265)), ('collar', 160, 178, (85, 105), None)],
 'v2': [('sleeve', 210, 250, (368, 384), (552, 570)), ('body_web_A_B', 375, 395, (372, 388), (550, 566)), ('body_web_B_C', 490, 515, (372, 388), (550, 566)),
        ('body_low', 600, 620, (372, 388), (550, 566)), ('cap', 650, 690, (362, 378), (556, 572)), ('collar', 162, 178, (395, 410), (530, 545))],
 'v3': [('sleeve', 210, 250, (645, 662), (830, 845)), ('body_web_A_B', 375, 395, (650, 666), (826, 842)), ('body_web_B_C', 490, 515, (650, 666), (826, 842)),
        ('body_low', 600, 620, (650, 666), (826, 842)), ('cap', 650, 690, (640, 656), (836, 852)), ('collar', 162, 178, (670, 690), None)],
 'v4': [('sleeve', 210, 250, None, (1195, 1210)), ('body_web_A_B', 375, 395, (1005, 1020), (1188, 1202)), ('body_web_B_C', 490, 515, (1005, 1020), (1188, 1202)),
        ('body_low', 600, 620, (1005, 1020), (1188, 1202)), ('cap', 650, 690, (995, 1011), (1195, 1212)), ('collar', 162, 178, None, None)],
}
out = {}
for v, js in J.items():
    out[v] = {}
    for lab, y0, y1, wl, wr in js:
        l = edge(y0, y1, *wl) if wl else None
        r = edge(y0, y1, *wr) if wr else None
        out[v][lab] = dict(y=[y0, y1], left=l, right=r, width=(r[0]-l[0]) if (l and r) else None, centre=(0.5*(r[0]+l[0])) if (l and r) else None)
        print(v, lab, l, r, out[v][lab]['width'], out[v][lab]['centre'])
json.dump(out, open(DBG + "/fb_edges.json", "w"), indent=1)
