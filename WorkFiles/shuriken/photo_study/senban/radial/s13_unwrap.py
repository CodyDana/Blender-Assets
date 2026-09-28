"""Straighten each outer side into a strip image: x = position along side (0..1 of chord), y = depth
from the fitted arc (-20..+45 px, inward down). Lets us see the bevel band along its full length."""
import sys, json, math
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/senban/radial")
import numpy as np
from common import *

R0 = json.load(open(OUT + "senban_radial.json"))
rgb = load_rgb().astype(np.float64)
H, W, _ = rgb.shape
S = json.load(open(OUT + "senban_sides.json"))


def bilinear3(img, x, y):
    x = np.clip(x, 0, W - 1.001); y = np.clip(y, 0, H - 1.001)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
    fx = (x - x0)[..., None]; fy = (y - y0)[..., None]
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy)
            + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)

corners = [np.array(p) for p in R0["corners_virtual_px"]]
strips = []
for q, sd in enumerate(R0["sides"]):
    circ = S["sides"][sd["name"]]["circle_fits"]["0.1-0.9"]
    fcx, fcy = circ["centre"]; R = circ["R"]
    P0 = corners[q]; P1 = corners[(q + 1) % 4]
    a0 = math.atan2(P0[1] - fcy, P0[0] - fcx); a1 = math.atan2(P1[1] - fcy, P1[0] - fcx)
    da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
    ncol = 900
    aa = a0 + np.linspace(0, 1, ncol) * da
    depths = np.arange(-20, 45, 0.25)
    rad = R + depths
    X = fcx + rad[:, None] * np.cos(aa)[None, :]
    Y = fcy + rad[:, None] * np.sin(aa)[None, :]
    im = bilinear3(rgb, X, Y)
    im = np.clip(im / 0.72, 0, 1)
    strips.append(im)
    save_png(im, OUT + "unwrap_%s.png" % sd["name"])
# stack all four (with separators)
sep = np.ones((8, strips[0].shape[1], 3))
save_png(np.concatenate([np.concatenate([s, sep], 0) for s in strips], 0), OUT + "unwrap_all_sides.png")
print("ORDER", [s["name"] for s in R0["sides"]])
