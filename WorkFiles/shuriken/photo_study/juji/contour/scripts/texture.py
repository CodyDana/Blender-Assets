import sys; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/contour/scripts")
from common import *
from geom import bilinear
rgb = load().astype(np.float64)
h, w, _ = rgb.shape
def gauss1d(sig):
    r = int(3 * sig + 0.5); x = np.arange(-r, r + 1); k = np.exp(-x**2 / (2 * sig**2)); return k / k.sum()
def gblur2(a, sig):
    k = gauss1d(sig); r = len(k) // 2
    p = np.pad(a, ((r, r), (0, 0)), mode="edge"); a1 = sum(k[i] * p[i:i + a.shape[0]] for i in range(len(k)))
    p = np.pad(a1, ((0, 0), (r, r)), mode="edge"); return sum(k[i] * p[:, i:i + a.shape[1]] for i in range(len(k)))
# texture on each channel: high-pass energy
T = np.zeros((h, w))
for c in range(3):
    ch = rgb[..., c]
    hp = ch - gblur2(ch, 1.5)
    T += gblur2(hp ** 2, 3.0)
T = np.sqrt(T)
np.save(ROOT + "texture.npy", T.astype(np.float32))
far = ~dilate(np.load(ROOT + "mask_lo.npy"), 12)
m5 = np.load(ROOT + "mask_t5.0.npy")
core = erode(m5, 12)
print("texture bg pct 50/95/99", np.percentile(T[far], [50, 95, 99]).round(4), " piece core pct 5/25/50", np.percentile(T[core], [5, 25, 50]).round(4))
write_png(ROOT + "debug_texture.png", np.clip(T / np.percentile(T[core], 50), 0, 1))
Pr = np.load(ROOT + "contour_initial.npy"); N = np.load(ROOT + "contour_normals.npy")
L = rgb @ np.array([0.2126, 0.7152, 0.0722])
ts = np.arange(-14, 16.01, 1.0)
for tx, ty in [(640, 450), (300, 755), (1100, 540), (805, 1100), (1100, 725), (581, 150), (779, 152), (1300, 600)]:
    i = np.argmin(np.hypot(Pr[:, 0] - tx, Pr[:, 1] - ty)); p, n = Pr[i], N[i]
    X = p[0] + ts * n[0]; Y = p[1] + ts * n[1]
    print(f"pt {p.round(0)} T*1000:", " ".join(f"{a*1000:4.0f}" for a in bilinear(T, X, Y)))
