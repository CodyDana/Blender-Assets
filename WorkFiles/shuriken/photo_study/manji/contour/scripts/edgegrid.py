# composite of zoomed edge crops: edgegrid.py out.png sc half x,y x,y ...
import sys; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/manji/contour/scripts")
from common import *
out = sys.argv[1]; sc = int(sys.argv[2]); hw = int(sys.argv[3])
pts = [tuple(map(int, a.split(","))) for a in sys.argv[4:]]
px = np.load(BASE + "/manji_pixels.npy")
tiles = []
for (x, y) in pts:
    c = px[y - hw:y + hw, x - hw:x + hw].copy()
    c = np.repeat(np.repeat(c, sc, 0), sc, 1)
    c[:, :2] = 1; c[:2, :] = 1
    # tick marks at the centre
    c[hw * sc - 1:hw * sc + 1, :6] = [1, 0, 0]; c[:6, hw * sc - 1:hw * sc + 1] = [1, 0, 0]
    tiles.append(c)
ncol = 4
while len(tiles) % ncol: tiles.append(np.ones_like(tiles[0]))
rows = [np.concatenate(tiles[i:i + ncol], 1) for i in range(0, len(tiles), ncol)]
write_png(out, np.concatenate(rows, 0))
