import sys; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/contour/scripts")
from common import *
rgb = load().astype(np.float64)
h, w, _ = rgb.shape
yy, xx = np.mgrid[0:h, 0:w]
Y = yy / h - 0.5; X = xx / w - 0.5
def design(Xf, Yf, deg=3):
    cols = []
    for i in range(deg + 1):
        for j in range(deg + 1 - i):
            cols.append((Xf ** i) * (Yf ** j))
    return np.stack(cols, -1)
v, s = hsv(rgb)
L = rgb @ np.array([0.2126, 0.7152, 0.0722])
# initial background guess: low saturation and L > 0.40 (conservative), excluding a central cross band
bgm = (s < 0.16) & (L > 0.42)
for it in range(4):
    A = design(X[bgm], Y[bgm])
    bgfit = np.zeros_like(rgb)
    Afull = design(X.ravel(), Y.ravel()).reshape(h, w, -1)
    for c in range(3):
        coef, *_ = np.linalg.lstsq(A, rgb[..., c][bgm], rcond=None)
        bgfit[..., c] = Afull @ coef
    diff = rgb - bgfit
    # colour distance: darkness + chroma difference
    dL = (bgfit @ np.array([0.2126, 0.7152, 0.0722])) - L
    chroma = rgb - L[..., None]; chroma_bg = bgfit - (bgfit @ np.array([0.2126, 0.7152, 0.0722]))[..., None]
    dC = np.linalg.norm(chroma - chroma_bg, axis=-1)
    D = np.sqrt(np.maximum(dL, 0) ** 2 + (2.0 * dC) ** 2 + 0.25 * np.minimum(dL, 0) ** 2)
    t = otsu(D)
    fg = D > t
    bgm = ~dilate(fg, 6)
    res = diff[bgm]
    print("iter", it, "otsu D", round(t, 4), "bg resid sd", res.std(0).round(4), "fg frac", fg.mean().round(4))
np.save(ROOT + "D.npy", D.astype(np.float32)); np.save(ROOT + "bgfit.npy", bgfit.astype(np.float32))
hist, e = np.histogram(D, bins=30, range=(0, 0.3)); print("D hist", hist, "\nedges", e.round(3))
write_png(ROOT + "debug_D.png", np.clip(D / 0.25, 0, 1))
