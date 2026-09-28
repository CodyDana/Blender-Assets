import sys; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/contour/scripts")
from common import *
rgb = load()
h, w, _ = rgb.shape
v, s = hsv(rgb)
L = rgb @ np.array([0.2126, 0.7152, 0.0722])
print("shape", rgb.shape)
for name, (y0, y1, x0, x1) in {"TL": (0, 150, 0, 150), "TR": (0, 150, w-150, w), "BL": (h-150, h, 0, 150), "BR": (h-150, h, w-150, w), "mid-left bg": (300, 450, 200, 350)}.items():
    blk = rgb[y0:y1, x0:x1]
    print(name, "rgb mean", blk.reshape(-1, 3).mean(0).round(3), "sd", blk.reshape(-1, 3).std(0).round(3), "sat", s[y0:y1, x0:x1].mean().round(3), s[y0:y1, x0:x1].std().round(3))
# piece samples
for name, (y, x) in {"top arm left band": (300, 640), "top dark": (200, 690), "centre diamond": (660, 690), "right arm lower band": (690, 1100), "left arm lower": (700, 200), "bottom arm": (1100, 670)}.items():
    blk = rgb[y-5:y+5, x-5:x+5].reshape(-1, 3)
    print(name, blk.mean(0).round(3), "sat", s[y-5:y+5, x-5:x+5].mean().round(3), "L", L[y-5:y+5, x-5:x+5].mean().round(3))
print("otsu L", otsu(L), "otsu S", otsu(s))
hist, e = np.histogram(s, bins=20, range=(0, 1)); print("sat hist", hist)
hist, e = np.histogram(L, bins=20, range=(0, 1)); print("L hist", hist)
