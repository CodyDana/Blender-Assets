import sys, numpy as np, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/metrology")
from fb_lib import *
sil = np.load(DBG + "/fb_sil.npy").copy()
ref = load_srgb()
H, W = sil.shape
# floor-shadow cleanup: below y=690 keep only columns within the cap side extents (+1)
CAP = dict(v1=(40, 345, 58.3, 254.0), v2=(345, 615, 371.0, 560.9), v3=(615, 950, 649.0, 842.9), v4=(950, 1240, 1003.9, 1202.9))
for v, (x0, x1, cl, cr) in CAP.items():
    sub = sil[690:, x0:x1]
    xs = np.arange(x0, x1)
    sub[:, (xs < cl - 1) | (xs > cr + 1)] = False
    sil[690:, x0:x1] = sub
np.save(DBG + "/fb_sil_clean.npy", sil)
def trace(mask):
    """Moore-neighbour boundary trace of the largest blob touching the top-most pixel. returns list of (x,y)."""
    ys, xs = np.nonzero(mask)
    i = np.lexsort((xs, ys))[0]; start = (int(xs[i]), int(ys[i]))
    nb = [(-1, 0), (-1, -1), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1)]
    pts = [start]; cur = start; back = 0  # came from the west
    h, w = mask.shape
    for _ in range(200000):
        found = False
        for k in range(8):
            d = (back + 1 + k) % 8
            nx, ny = cur[0] + nb[d][0], cur[1] + nb[d][1]
            if 0 <= nx < w and 0 <= ny < h and mask[ny, nx]:
                back = (d + 4) % 8
                cur = (nx, ny); found = True; break
        if not found: break
        if cur == start: break
        pts.append(cur)
    return pts
def dp(pts, eps):
    pts = np.asarray(pts, float)
    if len(pts) < 3: return pts
    keep = np.zeros(len(pts), bool); keep[0] = keep[-1] = True
    st = [(0, len(pts)-1)]
    while st:
        a, b = st.pop()
        if b <= a + 1: continue
        p, q = pts[a], pts[b]; seg = q - p; n = np.hypot(*seg)
        d = np.abs(np.cross(seg, pts[a+1:b] - p)) / n if n > 0 else np.hypot(*(pts[a+1:b] - p).T)
        j = int(np.argmax(d))
        if d[j] > eps:
            keep[a+1+j] = True; st += [(a, a+1+j), (a+1+j, b)]
    return pts[keep]
out = {}
vis = ref[:745]*0.55
for v, (x0, x1, cl, cr) in CAP.items():
    m = np.zeros_like(sil); m[:, x0:x1] = sil[:, x0:x1]
    # largest component approx: keep pixels connected to the body centre via flood
    cx = int(0.5*(cl+cr)); seed = np.zeros_like(m); seed[450, cx] = True
    comp = seed.copy()
    for it in range(3000):
        n = comp.copy(); n[1:] |= comp[:-1]; n[:-1] |= comp[1:]; n[:, 1:] |= comp[:, :-1]; n[:, :-1] |= comp[:, 1:]
        n &= m
        if (n == comp).all(): break
        comp = n
    pts = trace(comp)
    simp = dp(pts, 0.8)
    out[v] = dict(n_raw=len(pts), polygon_ref_px=[[round(float(a), 1), round(float(b), 1)] for a, b in simp],
                  bbox=[int(np.nonzero(comp)[1].min()), int(np.nonzero(comp)[0].min()), int(np.nonzero(comp)[1].max()), int(np.nonzero(comp)[0].max())])
    # interior background holes (ring interior etc.)
    for (a, b) in pts: vis[b, a] = [1, 0.2, 0.2]
    print(v, len(pts), len(simp), out[v]['bbox'])
json.dump(out, open(DBG + "/fb_outlines_auto.json", "w"))
save_png(DBG + "/outline_check.png", vis)
