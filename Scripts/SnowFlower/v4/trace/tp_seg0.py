import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, tp_img
OUT = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot/work"
a = np.load(OUT + "/ref_full.npy")[..., :3]
R0, C0 = 20, 420
c = a[R0:190, C0:592]
lum = c @ np.array([0.2126, 0.7152, 0.0722])
sat = c.max(2) - c.min(2)
print("lum pct", np.percentile(lum, [1, 5, 25, 50, 75, 95, 99]))
for nm, (r, q) in {"pearl_top": (70, 506), "pearl_left": (86, 485), "centre": (87, 506), "rim_ul": (47, 460), "inset_lat_L": (100, 460),
                  "inset_ul": (60, 468), "mouth": (35, 506), "drop_inset": (140, 500), "lace": (165, 470), "body": (180, 470), "crest": (50, 506)}.items():
    v = a[r-1:r+2, q-1:q+2].reshape(-1, 3).mean(0)
    print(nm, r, q, np.round(v, 3), round(float(v @ [0.2126, 0.7152, 0.0722]), 3))
cls = np.zeros(lum.shape + (3,), np.float32)
cls[lum < 0.30] = [0.1, 0.1, 0.5]
cls[(lum >= 0.30) & (lum < 0.55)] = [0.2, 0.6, 0.2]
cls[(lum >= 0.55) & (lum < 0.80)] = [0.9, 0.6, 0.1]
cls[lum >= 0.80] = [1, 1, 0.3]
cls[lum > 0.93] = [1, 1, 1]
tp_img.save(OUT + "/seg_classes_x6.png", tp_img.resize(cls, 6))
# chroma: pearl vs silver? print blue-red
br = c[..., 2] - c[..., 0]
print("b-r pct", np.percentile(br, [1, 50, 99]))
tp_img.save(OUT + "/seg_br_x6.png", tp_img.resize(np.clip(0.5 + br * 8, 0, 1), 6))
