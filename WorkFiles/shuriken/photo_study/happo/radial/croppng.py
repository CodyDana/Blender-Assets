import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, imglib as L, bpy
OUT = os.path.dirname(os.path.abspath(__file__))
a = sys.argv[sys.argv.index("--")+1:]
src, dst = a[0], a[1]
x0, y0, x1, y1, sc = map(int, a[2:7])
img = bpy.data.images.load(os.path.join(OUT, src))
w, h = img.size
buf = np.empty(w*h*img.channels, dtype=np.float32); img.pixels.foreach_get(buf)
arr = buf.reshape(h, w, img.channels)[::-1, :, :3]
c = arr[y0:y1, x0:x1]
c = np.repeat(np.repeat(c, sc, 0), sc, 1)
L.save_png(os.path.join(OUT, dst), c)
