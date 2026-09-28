import sys; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/manji/contour/scripts")
from common import *
px = np.load(BASE + "/manji_pixels.npy")
L = px @ np.array([0.2126, 0.7152, 0.0722], np.float32)
hp = L - gauss_blur(L, 1.5)
T = np.sqrt(np.maximum(box_mean(hp * hp, 3), 0))
np.save(BASE + "/texture.npy", T)
m = np.load(BASE + "/mask_solid.npy")
print("texture pct bg(far)", np.percentile(T[~m][::50], [50, 90, 99]).round(4))
print("texture pct piece", np.percentile(T[m][::50], [1, 5, 10, 50]).round(4))
for nm, pts in [("a x=1800", [(1800, y) for y in range(1120, 1200, 4)]), ("c y=900", [(x, 900) for x in range(2480, 2545, 3)]), ("b x=900", [(900, y) for y in range(60, 140, 4)])]:
    print(nm, [(p, round(float(T[p[1], p[0]]), 4)) for p in pts])
vis = np.clip(T / 0.04, 0, 1)
write_png(BASE + "/zz_texture_small.png", vis[::3, ::3])
