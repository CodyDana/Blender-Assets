# Method B step 3: Moore-neighbour tracing of the Otsu(L+S) mask, Douglas-Peucker, tips/notches,
# first-pass line fits. Output: b3_contour.json, contour.npy
import numpy as np, os, json, sys
OUT = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/happo/contour"
mfile = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "mask_filled.npy"
M = np.load(os.path.join(OUT, mfile))
H, W = M.shape

def moore_trace(M):
    # start: topmost-leftmost foreground pixel; Moore neighbour tracing with Jacob's stopping criterion
    ys, xs = np.nonzero(M)
    i = np.lexsort((xs, ys))[0]
    start = (int(ys[i]), int(xs[i]))
    # neighbour order clockwise starting West (in image coords y down): W, NW, N, NE, E, SE, S, SW
    nb = [(0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1)]
    def fg(p):
        y, x = p
        return 0 <= y < H and 0 <= x < W and M[y, x]
    cont = [start]
    b = (start[0], start[1] - 1)          # backtrack pixel (west of start is background)
    c = start
    first_b = b
    it = 0
    while True:
        it += 1
        # index of backtrack in neighbourhood of c
        d = (b[0] - c[0], b[1] - c[1])
        k = nb.index(d)
        found = False
        for j in range(1, 9):
            kk = (k + j) % 8
            q = (c[0] + nb[kk][0], c[1] + nb[kk][1])
            if fg(q):
                pb = (c[0] + nb[(kk - 1) % 8][0], c[1] + nb[(kk - 1) % 8][1])
                b, c = pb, q
                found = True
                break
        if not found:
            break
        if c == start and b == first_b:
            break
        if c == start and len(cont) > 2:
            # Jacob's criterion fallback
            break
        cont.append(c)
        if it > 10 * (H + W) * 4:
            break
    return np.array(cont, dtype=np.float64)  # (y, x)

C = moore_trace(M)
print("contour length (px count)", len(C))
np.save(os.path.join(OUT, "contour_" + mfile), C)

def dp(pts, eps):
    # iterative Douglas-Peucker on an open polyline
    keep = np.zeros(len(pts), bool); keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        if b <= a + 1: continue
        p, q = pts[a], pts[b]
        d = q - p; n = np.hypot(*d)
        seg = pts[a + 1:b] - p
        if n < 1e-9: dist = np.hypot(seg[:, 0], seg[:, 1])
        else: dist = np.abs(seg[:, 0] * d[1] - seg[:, 1] * d[0]) / n
        k = np.argmax(dist)
        if dist[k] > eps:
            keep[a + 1 + k] = True
            stack += [(a, a + 1 + k), (a + 1 + k, b)]
    return pts[keep], np.nonzero(keep)[0]

# close contour for DP: split at the farthest point from start
xy = C[:, ::-1].copy()                  # (x, y)
far = np.argmax(np.hypot(*(xy - xy[0]).T))
p1, i1 = dp(xy[:far + 1], 1.5)
p2, i2 = dp(np.vstack([xy[far:], xy[:1]]), 1.5)
poly = np.vstack([p1, p2[1:-1]])
print("DP(1.5px) vertices", len(poly))

# centroid (area) of mask
ys, xs = np.nonzero(M)
cx, cy = xs.mean(), ys.mean()
r = np.hypot(xy[:, 0] - cx, xy[:, 1] - cy)
th = np.degrees(np.arctan2(-(xy[:, 1] - cy), xy[:, 0] - cx)) % 360   # math angle (y up)
# tips: local maxima of r over +-20 deg windows
order = np.argsort(-r)
tips = []
for i in order:
    if all(min(abs(th[i] - th[j]), 360 - abs(th[i] - th[j])) > 20 for j in tips):
        tips.append(i)
    if len(tips) == 8: break
tips = sorted(tips, key=lambda i: th[i])
notches = []
for a_, b_ in zip(tips, tips[1:] + tips[:1]):
    # contour index range between consecutive tips (by angle)
    ta, tb = th[a_], th[b_]
    span = (tb - ta) % 360
    sel = np.nonzero(((th - ta) % 360) < span)[0]
    sel = sel[((th[sel] - ta) % 360) > 0]
    j = sel[np.argmin(r[sel])]
    notches.append(j)
print("centroid", cx, cy)
for k, i in enumerate(tips):
    print("tip %d idx %d xy (%.1f,%.1f) r %.1f th %.1f" % (k, i, xy[i, 0], xy[i, 1], r[i], th[i]))
for k, i in enumerate(notches):
    print("notch %d idx %d xy (%.1f,%.1f) r %.1f th %.1f" % (k, i, xy[i, 0], xy[i, 1], r[i], th[i]))
json.dump(dict(mask=mfile, centroid=[cx, cy], n_contour=len(C), n_dp=len(poly),
               dp_poly=poly.tolist(),
               tips=[dict(idx=int(i), x=float(xy[i, 0]), y=float(xy[i, 1]), r=float(r[i]), th=float(th[i])) for i in tips],
               notches=[dict(idx=int(i), x=float(xy[i, 0]), y=float(xy[i, 1]), r=float(r[i]), th=float(th[i])) for i in notches]),
          open(os.path.join(OUT, "b3_contour_" + mfile.replace(".npy", "") + ".json"), "w"), indent=1)
