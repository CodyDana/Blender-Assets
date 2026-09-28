# Run with Blender 5.2 headless: dumps the photo's raw stored (sRGB-encoded) pixels to .npy, top-origin rows.
import bpy, sys, numpy as np, json, os
argv = sys.argv[sys.argv.index("--") + 1:]
src, out = argv[0], argv[1]
img = bpy.data.images.load(src, check_existing=False)
w, h = img.size
ch = img.channels
px = np.empty(w * h * ch, dtype=np.float32)
img.pixels.foreach_get(px)
px = px.reshape(h, w, ch)[::-1]  # flip: row 0 at top
np.save(out, px[:, :, :3].astype(np.float32))
info = dict(src=src, width=w, height=h, channels=ch, colorspace=img.colorspace_settings.name,
            is_float=img.is_float, file_format=img.file_format)
print("INFO", json.dumps(info))
with open(os.path.splitext(out)[0] + "_info.json", "w") as f:
    json.dump(info, f, indent=1)
