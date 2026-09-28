# zoomed tiles around points with the final-mask edge (red) and coarse edge (yellow)
import sys; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/manji/contour/scripts")
from common import *
out = sys.argv[1]; sc = int(sys.argv[2]); hw = int(sys.argv[3]); mp = sys.argv[4]
pts = [tuple(map(int, a.split(","))) for a in sys.argv[5:]]
px = np.load(BASE + "/manji_pixels.npy"); fm = np.load(mp); cm = np.load(BASE + "/mask_solid.npy")
def edge(mm):
    e = (mm ^ np.roll(mm, 1, 0)) | (mm ^ np.roll(mm, 1, 1)); e[0, :] = e[:, 0] = False; return e
tiles = []
for (x, y) in pts:
    sl = (slice(y - hw, y + hw), slice(x - hw, x + hw))
    c = px[sl].copy(); c = np.repeat(np.repeat(c, sc, 0), sc, 1)
    for mm, col in ((cm, [1, 1, 0]), (fm, [1, 0, 0])):
        e = edge(mm[sl]); e = np.repeat(np.repeat(e, sc, 0), sc, 1)
        # thin the upscaled edge to 1 display px per source px border
        c[e] = c[e] * 0.3 + np.array(col) * 0.7
    c[:, :2] = 1; c[:2, :] = 1
    tiles.append(c)
ncol = min(4, len(tiles))
while len(tiles) % ncol: tiles.append(np.ones_like(tiles[0]))
rows = [np.concatenate(tiles[i:i + ncol], 1) for i in range(0, len(tiles), ncol)]
write_png(out, np.concatenate(rows, 0))
