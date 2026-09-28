# Method B segmentation: background-flattened luminance darkness + saturation, Otsu thresholds,
# then flood fill of background from the image border (run-based connected components).
import sys, json; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/manji/contour/scripts")
from common import *
px = np.load(BASE + "/manji_pixels.npy")
h, w, _ = px.shape
L = px @ np.array([0.2126, 0.7152, 0.0722], np.float32)
mx = px.max(2); mn = px.min(2)
S = np.where(mx > 1e-4, (mx - mn) / np.maximum(mx, 1e-4), 0).astype(np.float32)

# 1) background illumination model: quadratic-in-x, quadratic-in-y surface fitted to bg pixels (iterative)
yy, xx = np.mgrid[0:h:8, 0:w:8]
Ls = L[::8, ::8]; Ss = S[::8, ::8]
bg = (Ls > otsu(Ls)) & (Ss < 0.08)
def design(x, y):
    x = x / w - 0.5; y = y / h - 0.5
    return np.stack([np.ones_like(x), x, y, x*x, x*y, y*y, x**3, y**3, x*x*y, x*y*y], -1)
for it in range(4):
    A = design(xx[bg].astype(np.float64), yy[bg].astype(np.float64))
    coef, *_ = np.linalg.lstsq(A, Ls[bg].astype(np.float64), rcond=None)
    model = design(xx.astype(np.float64), yy.astype(np.float64)) @ coef
    res = Ls - model
    sd = res[bg].std()
    bg = bg & (np.abs(res) < 3 * sd) | ((res > -3 * sd) & (Ss < 0.08) & (Ls > 0.5))
print("bg model residual sd", round(float(sd), 4), "bg frac", round(float(bg.mean()), 3))
YY, XX = np.mgrid[0:h, 0:w]
Lbg = (design(XX.astype(np.float32), YY.astype(np.float32)).astype(np.float32) @ coef.astype(np.float32))
D = 1 - L / np.maximum(Lbg, 1e-3)          # darkness relative to local background
tD = otsu(D[::2, ::2]); tS = otsu(S[::2, ::2])
print("Otsu thresholds: darkness", round(float(tD), 4), "saturation", round(float(tS), 4))
cand = (D > tD) | (S > tS)
# 2) background = connected non-candidate region touching the border
lab, n = label_runs(~cand)
border = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
border = border[border > 0]
bgmask = np.isin(lab, border)
sizes = np.bincount(lab.ravel())
holes = [(int(i), int(sizes[i])) for i in range(1, n + 1) if i not in set(border.tolist())]
holes.sort(key=lambda t: -t[1])
print("non-candidate components:", n, "border-connected:", len(border), "enclosed (candidate holes) largest 10:", holes[:10])
piece = ~bgmask
# keep largest piece component
plab, pn = label_runs(piece)
psz = np.bincount(plab.ravel()); psz[0] = 0
keep = int(np.argmax(psz))
print("piece components:", pn, "largest", int(psz[keep]), "others (top5):", sorted(psz[1:].tolist())[::-1][1:6])
piece = plab == keep
# enclosed holes inside the kept piece, with centroids
hole_info = []
for i, s in holes:
    if s < 20: continue
    ys, xs = np.nonzero(lab == i)
    hole_info.append(dict(label=i, area_px=s, cx=float(xs.mean()), cy=float(ys.mean()),
                          bbox=[int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
                          meanL=float(L[ys, xs].mean()), meanD=float(D[ys, xs].mean())))
print("holes >=20px:", json.dumps(hole_info, indent=0))
# fill all enclosed specks <= area threshold to make the solid silhouette; record hole state separately
solid = piece | (~bgmask & ~piece & False)
solid = ~bgmask
solid = solid & (plab == keep) | (np.isin(lab, [i for i, s in holes]) )
np.save(BASE + "/mask_solid.npy", solid)
np.save(BASE + "/darkness.npy", D.astype(np.float32))
write_png(BASE + "/manji_mask.png", solid.astype(np.float32))
# quick-look downsample overlay
ov = px.copy()
edge = solid ^ np.roll(solid, 1, 0) | solid ^ np.roll(solid, 1, 1)
ov[edge] = [1, 0, 0]
tint = ov.copy(); tint[solid] = tint[solid] * 0.5 + np.array([0, 0.5, 1]) * 0.5
write_png(BASE + "/seg_check_full.png", tint)
write_png(BASE + "/seg_check_small.png", tint[::3, ::3])
json.dump(dict(tD=float(tD), tS=float(tS), bg_resid_sd=float(sd), holes=hole_info, piece_area_px=int(solid.sum())),
          open(BASE + "/segment_info.json", "w"), indent=1)
print("piece area px", int(solid.sum()))
