import sys; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/contour/scripts")
from common import *
rgb = load()
names = sys.argv[1:] if len(sys.argv) > 1 else ["contour_initial.npy", "contour_refined.npy"]
cols = [[0, 1, 1], [1, 0, 0], [1, 1, 0], [0, 1, 0]]
curves = [np.load(ROOT + n) for n in names]
def crop(name, y0, y1, x0, x1, k):
    c = rgb[y0:y1, x0:x1].copy()
    lo, hi = np.percentile(c, 1), np.percentile(c, 99.5); c = np.clip((c - lo) / (hi - lo), 0, 1)
    c = np.repeat(np.repeat(c, k, 0), k, 1)
    for P, col in zip(curves, cols):
        # dense sample
        Q = np.vstack([P, P[:1]])
        for i in range(len(P)):
            for f in np.linspace(0, 1, 2 * k):
                x = (Q[i, 0] * (1 - f) + Q[i + 1, 0] * f - x0 + 0.5) * k
                y = (Q[i, 1] * (1 - f) + Q[i + 1, 1] * f - y0 + 0.5) * k
                xi, yi = int(x), int(y)
                if 0 <= xi < c.shape[1] and 0 <= yi < c.shape[0]:
                    c[yi, xi] = col
    write_png(ROOT + name, c)
crop("zoom_toparm_neck.png", 240, 520, 590, 770, 3)
crop("zoom_right_tip.png", 520, 780, 1150, 1370, 3)
crop("zoom_top_blade.png", 0, 260, 560, 800, 3)
crop("zoom_left_tip.png", 560, 780, 10, 260, 3)
crop("zoom_bottom_tip.png", 1120, 1330, 580, 840, 3)
crop("zoom_centre.png", 480, 820, 540, 860, 2)
