import sys, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rio

IMG = "C:/Users/Cody/Desktop/Blender_Projects/References/Shuriken/images/Roppo.JPG"
rgb = rio.load_rgb(IMG)
HCX, HCY, HR = 628.43, 529.22, 285.9


def crop(x0, x1, y0, y1, Z, circle=True, name="crop"):
    c = np.clip(rgb[y0:y1, x0:x1].copy(), 0, 1)
    lo, hi = np.percentile(c, 2), np.percentile(c, 98)
    c = np.clip((c - lo) / max(hi - lo, 1e-6), 0, 1)
    big = np.repeat(np.repeat(c, Z, axis=0), Z, axis=1)
    if circle:
        for a in np.arange(0, 360, 0.01):
            th = np.radians(a)
            px = (HCX + np.cos(th) * HR - x0) * Z
            py = (HCY + np.sin(th) * HR - y0) * Z
            i, j = int(round(py)), int(round(px))
            if 0 <= i < big.shape[0] and 0 <= j < big.shape[1]:
                big[i, j] = (1, 1, 0)
    # 5 px ticks along the top edge
    for t in range(0, x1 - x0, 5):
        big[0:6, t * Z:t * Z + 1] = (1, 0, 0)
    rio.save_rgb(os.path.join(HERE, name + ".png"), big)


crop(500, 780, 215, 300, 5, True, "toparc_band")
crop(400, 450, 305, 355, 16, True, "root_2ccw_16x")
crop(890, 935, 570, 615, 16, True, "root_0cw_16x")
crop(690, 735, 780, 825, 16, True, "root_5cw_16x")
crop(690, 740, 215, 265, 16, True, "root_1ccw_16x")
print("ok")
