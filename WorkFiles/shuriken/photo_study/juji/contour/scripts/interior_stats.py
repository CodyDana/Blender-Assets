import sys; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/contour/scripts")
from common import *
rgb = load().astype(np.float64)
v, S = hsv(rgb)
L = rgb @ np.array([0.2126, 0.7152, 0.0722])
Fs = np.load(ROOT + "Fs.npy")
T = np.load(ROOT + "texture.npy")
m = np.load(ROOT + "mask_refined.npy")
samples = {"diamond": (660, 690), "left lens": (670, 245), "right lens": (645, 1100), "top slit": (200, 680), "bottom lens": (1050, 705),
           "left upper bevel (shadow side)": (625, 250), "right upper bevel (shadow side)": (600, 1100), "left lower bevel (lit)": (715, 250),
           "right lower bevel (lit)": (700, 1100), "top arm left bevel": (300, 650), "top arm right bevel": (300, 725),
           "bottom arm left bevel": (1100, 660), "bottom arm right bevel": (1100, 760), "left neck upper": (630, 450), "left neck lower": (668, 450)}
for k, (y, x) in samples.items():
    sl = (slice(y - 4, y + 5), slice(x - 4, x + 5))
    print(f"{k:34s} srgb {rgb[sl].reshape(-1,3).mean(0).round(3)} L {L[sl].mean():.3f} S {S[sl].mean():.3f} F {Fs[sl].mean():.4f} tex {T[sl].mean():.4f} inmask {m[y, x]}")
inner = erode(m, 4)
print("F within piece pct 5/25/50/75/95", np.percentile(Fs[inner], [5, 25, 50, 75, 95]).round(4))
print("L within piece pct 5/25/50/75/95", np.percentile(L[inner], [5, 25, 50, 75, 95]).round(3))
print("S within piece pct 5/25/50/75/95", np.percentile(S[inner], [5, 25, 50, 75, 95]).round(3))
print("otsu F in piece", otsu(Fs[inner]), "otsu S in piece", otsu(S[inner]))
