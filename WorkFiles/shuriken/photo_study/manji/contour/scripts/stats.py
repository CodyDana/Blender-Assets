import sys; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/manji/contour/scripts")
from common import *
px = np.load(BASE + "/manji_pixels.npy")
h, w, _ = px.shape
L = px @ np.array([0.2126, 0.7152, 0.0722], np.float32)
mx = px.max(2); mn = px.min(2)
S = np.where(mx > 1e-4, (mx - mn) / np.maximum(mx, 1e-4), 0)
print("shape", px.shape)
for name, arr in [("L", L), ("S", S)]:
    print(name, "percentiles", np.percentile(arr, [1, 5, 25, 50, 75, 95, 99]).round(3))
# border strips
for nm, sl in [("top", L[:20]), ("bottom", L[-20:]), ("left", L[:, :20]), ("right", L[:, -20:])]:
    print(nm, sl.mean().round(3), sl.min().round(3), sl.max().round(3))
# column means of top rows band to see gradient
print("L row 1200 every 100 px:", L[1200, ::100].round(2))
print("L row 300 every 100 px:", L[300, ::100].round(2))
print("S row 300 every 100 px:", S[300, ::100].round(2))
