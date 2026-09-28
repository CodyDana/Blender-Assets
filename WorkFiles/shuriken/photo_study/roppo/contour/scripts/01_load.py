# Blender headless: load a JPEG read-only and dump raw stored pixel values (sRGB-encoded) as top-origin float32 npy.
import bpy, sys, numpy as np, os
argv = sys.argv[sys.argv.index('--') + 1:]
src, dst = argv[0], argv[1]
img = bpy.data.images.load(src, check_existing=False)
W, H = img.size
px = np.empty(W * H * img.channels, dtype=np.float32)
img.pixels.foreach_get(px)
a = px.reshape(H, W, img.channels)[::-1, :, :3].copy()
np.save(dst, a)
print("LOADED", W, H, img.channels, img.colorspace_settings.name, a.min(), a.max())
