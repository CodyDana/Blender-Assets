import sys; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/contour/scripts")
from common import *
rgb = load()
M = np.load(ROOT + "M.npy").astype(np.float64)
h, w = M.shape
def box(a, r):
    # separable box filter with edge replicate
    k = 2 * r + 1
    p = np.pad(a, r, mode="edge")
    c = np.cumsum(np.cumsum(p, 0), 1)
    c = np.pad(c, ((1, 0), (1, 0)))
    return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)
Ms = box(M, 2)
np.save(ROOT + "Ms.npy", Ms.astype(np.float32))
t_otsu = float(np.expm1(otsu(np.log1p(Ms))))
print("otsu on log1p(Ms) ->", round(t_otsu, 3))
far = ~dilate(np.load(ROOT + "mask_lo.npy"), 15)
print("Ms bg pct 50/99/99.9/max", np.percentile(Ms[far], [50, 99, 99.9, 100]).round(2))
masks = {}
for t in (2.5, 3.5, t_otsu, 5.0):
    bgc = Ms < t
    lab, n = label(bgc)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    piece = ~np.isin(lab, list(border))
    sizes = np.bincount(lab.ravel(), minlength=n + 1)
    inner = sorted([(int(sizes[k]), k) for k in range(1, n + 1) if k not in border], reverse=True)[:5]
    pl, pn = label(piece)
    ps = np.bincount(pl.ravel()); ps[0] = 0
    main = pl == ps.argmax()
    # opening r=2 to cut hair-like spurs, then keep largest again
    op = dilate(erode(main, 2), 2)
    pl, pn = label(op); ps = np.bincount(pl.ravel()); ps[0] = 0; main = pl == ps.argmax()
    ys, xs = np.nonzero(main)
    print(f"t={t:.3f} area={main.sum()} bbox x[{xs.min()},{xs.max()}] y[{ys.min()},{ys.max()}] enclosed bg-like comps (size,label) {inner} row0 {np.nonzero(main[0])[0][[0,-1]] if main[0].any() else None}")
    masks[round(t, 3)] = main
    # save enclosed candidate holes map for inspection
    if abs(t - 3.5) < 1e-6:
        holes = np.zeros((h, w), bool)
        for s, k in inner:
            holes |= lab == k
        np.save(ROOT + "enclosed_bglike_t3.5.npy", holes)
keys = sorted(masks)
np.save(ROOT + "mask_primary.npy", masks[3.5])
for k in keys:
    np.save(ROOT + f"mask_t{k}.npy", masks[k])
m = masks[3.5]
write_png(ROOT + "juji_mask.png", m.astype(np.float32))
ov = rgb.copy()
ov[~m] = ov[~m] * 0.65 + np.array([0.0, 0.2, 0.45]) * 0.35
cols = {2.5: [0, 1, 0], 5.0: [1, 1, 0]}
for k, c in cols.items():
    mk = masks[k]; e = mk & ~erode(mk, 1); ov[e] = c
e = m & ~erode(m, 1); ov[e] = [1, 0, 0]
write_png(ROOT + "debug_mask_overlay.png", ov)
