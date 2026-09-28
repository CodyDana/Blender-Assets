# Dump Senban.jpg raw stored pixels (sRGB-encoded) to a top-origin uint8 npy.
import bpy, numpy as np, sys
src = "C:/Users/Cody/Desktop/Blender_Projects/References/Shuriken/images/Senban.jpg"
out = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/senban/contour/cache/senban_rgb.npy"
img = bpy.data.images.load(src, check_existing=False)
w, h = img.size
px = np.empty(w * h * 4, dtype=np.float32)
img.pixels.foreach_get(px)
px = px.reshape(h, w, 4)[::-1]  # row 0 at top
arr = np.clip(np.round(px[..., :3] * 255.0), 0, 255).astype(np.uint8)
np.save(out, arr)
print("SIZE", w, h, "colorspace", img.colorspace_settings.name, "mean", arr.reshape(-1,3).mean(0))
