import sys; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/contour/scripts")
from common import *
rgb = load().astype(np.float64)
bg = np.load(ROOT + "bgfit.npy").astype(np.float64)
mlo = np.load(ROOT + "mask_lo.npy")
h, w, _ = rgb.shape
res = rgb - bg
bgsel = ~dilate(mlo, 12)
R = res[bgsel]
C = np.cov(R.T); print("bg cov\n", C.round(6)); 
ev, evec = np.linalg.eigh(C); print("eig sd", np.sqrt(ev).round(4), "\nvecs\n", evec.round(3))
Ci = np.linalg.inv(C)
M = np.sqrt(np.einsum("hwi,ij,hwj->hw", res, Ci, res))
print("M bg pct 50/99/99.9", np.percentile(M[bgsel], [50, 99, 99.9]).round(2))
np.save(ROOT + "M.npy", M.astype(np.float32))
write_png(ROOT + "debug_M.png", np.clip(M / 20, 0, 1))
# box smooth M 5x5 in log domain for histogram
lm = np.log1p(M)
t = otsu(lm); print("otsu on log1p(M):", t, "-> M", np.expm1(t))
