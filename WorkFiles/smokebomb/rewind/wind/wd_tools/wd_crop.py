"""wd_crop - zoom crops of the reference with a labelled px grid (measurement/preview only).
usage: python wd_crop.py x0 y0 x1 y1 scale name [gamma]
grid: thin every 20 px (dark red), thick every 100 px (bright red)."""
import sys, numpy as np
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/rewind/wind/tools")
from wd_png import write_png
REF = np.load(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/reference_metrology/sb_ref_srgb.npy")
def crop(x0, y0, x1, y1, k, name, gamma=0.5, local=False):
    a = REF[y0:y1, x0:x1, :3].astype(np.float64)
    a = np.clip(a, 0, 1) ** gamma
    if local:
        from numpy.lib.stride_tricks import sliding_window_view
    a = np.repeat(np.repeat(a, k, 0), k, 1)
    ys = np.arange(y0, y1).repeat(k); xs = np.arange(x0, x1).repeat(k)
    for i, x in enumerate(xs):
        if x % 50 == 0 and (i % k == 0):
            a[:, i] = [0.6, 0.1, 0.1] if x % 100 else [1, 0, 0]
    for j, y in enumerate(ys):
        if y % 50 == 0 and (j % k == 0):
            a[j, :] = [0.6, 0.1, 0.1] if y % 100 else [1, 0, 0]
    write_png(rf"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/rewind/wind/wd_crops/{name}.png", a)
if __name__ == "__main__":
    x0, y0, x1, y1, k = map(int, sys.argv[1:6]); name = sys.argv[6]
    g = float(sys.argv[7]) if len(sys.argv) > 7 else 0.5
    crop(x0, y0, x1, y1, k, name, g)
