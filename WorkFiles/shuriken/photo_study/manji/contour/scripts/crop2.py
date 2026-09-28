# crop2.py x0 y0 x1 y1 scale out.png : original + coarse mask edge (yellow) + refined mask edge (red)
import sys; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/manji/contour/scripts")
from common import *
x0, y0, x1, y1 = map(int, sys.argv[1:5]); sc = float(sys.argv[5]); out = sys.argv[6]
px = np.load(BASE + "/manji_pixels.npy")
def edge(mm):
    e = (mm ^ np.roll(mm, 1, 0)) | (mm ^ np.roll(mm, 1, 1)); e[0, :] = e[:, 0] = False; return e
cm = np.load(BASE + "/mask_solid.npy")[y0:y1, x0:x1]
rm = np.load(sys.argv[7] if len(sys.argv) > 7 else BASE + "/mask_refined.npy")[y0:y1, x0:x1]
c = px[y0:y1, x0:x1].copy()
c[edge(cm)] = [1, 1, 0]; c[edge(rm)] = [1, 0, 0]
if sc >= 1:
    s = int(sc); c = np.repeat(np.repeat(c, s, 0), s, 1)
else:
    s = int(round(1 / sc))
    # keep edges visible when downsampling: max-pool the edge colour
    h2, w2 = c.shape[0] // s, c.shape[1] // s
    c = c[:h2 * s, :w2 * s].reshape(h2, s, w2, s, 3)
    red = (c[..., 0] > 0.99) & (c[..., 1] < 0.01) & (c[..., 2] < 0.01)
    c2 = c.mean((1, 3)); c2[red.any((1, 3))] = [1, 0, 0]; c = c2
write_png(out, c)
