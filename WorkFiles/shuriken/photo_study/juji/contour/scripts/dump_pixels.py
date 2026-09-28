import bpy, numpy as np, sys
argv = sys.argv[sys.argv.index("--")+1:]
src, dst = argv[0], argv[1]
img = bpy.data.images.load(src)
w, h = img.size
px = np.empty(w*h*4, dtype=np.float32)
img.pixels.foreach_get(px)
px = px.reshape(h, w, 4)[::-1]  # top-origin rows
print("size", w, h, "colorspace", img.colorspace_settings.name, "min/max", px[...,:3].min(), px[...,:3].max())
np.save(dst, px[..., :3].astype(np.float32))
