import sys; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/contour/scripts")
from common import *
rgb = load()
D = np.load(ROOT + "D.npy").astype(np.float64)
h, w = D.shape
# light 3x3 box smoothing of D to suppress JPEG block noise
Ds = sum(shift(D, dy, dx, 0) for dy in (-1, 0, 1) for dx in (-1, 0, 1)) / 9.0
Ds[0, :] = D[0, :]; Ds[-1, :] = D[-1, :]; Ds[:, 0] = D[:, 0]; Ds[:, -1] = D[:, -1]
t_otsu = otsu(Ds)
res = {}
for t in (0.08, t_otsu, 0.16):
    bgc = Ds < t
    lab, n = label(bgc)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    outside = np.isin(lab, list(border))
    piece = ~outside
    # interior background-like components = candidate holes
    sizes = np.bincount(lab.ravel(), minlength=n + 1)
    holes = [(k, sizes[k]) for k in range(1, n + 1) if k not in border]
    big_holes = [(k, s) for k, s in holes if s > 20]
    # keep largest piece component
    pl, pn = label(piece)
    ps = np.bincount(pl.ravel()); ps[0] = 0
    main = pl == ps.argmax()
    ys, xs = np.nonzero(main)
    print(f"t={t:.4f} piece px={main.sum()} comps={pn} holes(>20px)={big_holes[:10]} bbox x[{xs.min()},{xs.max()}] y[{ys.min()},{ys.max()}] row0 cols={np.nonzero(main[0])[0][[0,-1]] if main[0].any() else None}")
    res[t] = main
np.save(ROOT + "mask_otsu.npy", res[t_otsu])
np.save(ROOT + "mask_lo.npy", res[0.08]); np.save(ROOT + "mask_hi.npy", res[0.16])
m = res[t_otsu]
write_png(ROOT + "juji_mask.png", m.astype(np.float32))
# overlay: tint outside, draw boundary
edge = m & ~erode(m, 1)
ov = rgb.copy()
ov[~m] = ov[~m] * 0.6 + np.array([0.0, 0.2, 0.4]) * 0.4
ov[edge] = [1, 0, 0]
eh = res[0.16] & ~erode(res[0.16], 1); el = res[0.08] & ~erode(res[0.08], 1)
ov[eh & ~edge] = [1, 1, 0]; ov[el & ~edge] = [0, 1, 0]
write_png(ROOT + "debug_mask_overlay.png", ov)
print("otsu", t_otsu)
