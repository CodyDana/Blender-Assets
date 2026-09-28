# helper: save upscaled crops of photo with optional mask boundary overlay
# args: -- maskfile|none spec1 spec2 ...   spec = name:x0:y0:x1:y1:scale
import bpy, numpy as np, os, sys
OUT = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/happo/contour"
a = sys.argv[sys.argv.index("--") + 1:]
mfile = a[0]
rgb = np.load(os.path.join(OUT, "rgb.npy"))
if os.environ.get("CROPSRC") == "grad":
    g = np.clip(np.load(os.path.join(OUT, "grad.npy")) / 0.08, 0, 1); rgb = np.stack([g, g, g], -1)
m = None if mfile == "none" else np.load(os.path.join(OUT, mfile))
os.makedirs(os.path.join(OUT, "crops"), exist_ok=True)
for spec in a[1:]:
    p = spec.split(":")
    name = p[0]; x0, y0, x1, y1, sc = map(int, p[1:6])
    x0 = max(0, x0); y0 = max(0, y0); x1 = min(rgb.shape[1], x1); y1 = min(rgb.shape[0], y1)
    c = rgb[y0:y1, x0:x1].copy()
    c2 = np.repeat(np.repeat(c, sc, 0), sc, 1)
    if m is not None:
        mm = m[y0:y1, x0:x1]
        edge = mm & ~(np.roll(mm, 1, 0) & np.roll(mm, -1, 0) & np.roll(mm, 1, 1) & np.roll(mm, -1, 1))
        e2 = np.repeat(np.repeat(edge, sc, 0), sc, 1)
        mark = np.zeros_like(e2); mark[sc // 2::sc, sc // 2::sc] = True
        c2[e2 & mark] = (1, 0, 0)
    h, w, _ = c2.shape
    im = bpy.data.images.new("o", w, h, alpha=True)
    aa = np.ones((h, w, 4), np.float32); aa[..., :3] = np.clip(c2, 0, 1)
    im.pixels.foreach_set(aa[::-1].ravel())
    im.filepath_raw = os.path.join(OUT, "crops", name + ".png"); im.file_format = 'PNG'; im.save()
    bpy.data.images.remove(im)

