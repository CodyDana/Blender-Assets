"""Side-by-side contact strip of images (over white), each scaled to a common height. Usage:
blender -b --factory-startup --python v2m_contact.py -- <out.png> <height> img1 img2 ..."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import v2m_lib as L
a = sys.argv[sys.argv.index("--") + 1:]
out, Ht, imgs = os.path.abspath(a[0]), int(a[1]), [os.path.abspath(p) for p in a[2:]]
import bpy
def load_rgba(p):
    im = bpy.data.images.load(p, check_existing=False); im.colorspace_settings.name = "Non-Color"
    w, h = im.size; x = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(x); bpy.data.images.remove(im)
    x = x.reshape(h, w, 4)[::-1]
    if im.channels == 3 if False else False: pass
    return x
tiles = []
for p in imgs:
    x = load_rgba(p); rgb = x[..., :3] * x[..., 3:4] + (1 - x[..., 3:4])
    h, w = rgb.shape[:2]; k = Ht / h
    Y, X = np.mgrid[0:Ht, 0:int(w * k)].astype(np.float64)
    t = L.bilinear(rgb * 255, (X + 0.5) / k - 0.5, (Y + 0.5) / k - 0.5, 255.0)
    tiles.append(t); tiles.append(np.full((Ht, 8, 3), 128.0))
L.save(out, np.concatenate(tiles[:-1], 1))
print("CONTACT", out)
