import numpy as np, math, itertools, sys
src = open(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/blackhat/final_pass/hull_proto.py").read().split('for n_az, elevs')[0]
exec(src)
def ev(dirs):
    V, dn, h = support_vertices(body, dirs, 1.0)
    gap = (V @ T.T).max(0) - hp
    return V, gap
for base_az in (8, 10, 12):
  for elevs in ((0, 64), (0, 64, 80)):
    dirs = dirs_set(base_az, elevs)
    V, gap = ev(dirs)
    hist = [(len(dirs), len(V), gap.mean(), gap.max())]
    while True:
        cands = T[np.argsort(-gap)[:40]]
        best = None
        for c in cands:
            V2, g2 = ev(np.vstack([dirs, c]))
            if len(V2) > 50: continue
            if best is None or g2.mean() < best[0]: best = (g2.mean(), c, V2, g2)
        if best is None or best[0] >= gap.mean() - 0.05: break
        dirs = np.vstack([dirs, best[1]]); V, gap = best[2], best[3]
        hist.append((len(dirs), len(V), gap.mean(), gap.max()))
    print(base_az, elevs, "final planes %d verts %d mean %.2f max %.2f p95 %.2f" % (len(dirs), len(V), gap.mean(), gap.max(), np.percentile(gap,95)))
