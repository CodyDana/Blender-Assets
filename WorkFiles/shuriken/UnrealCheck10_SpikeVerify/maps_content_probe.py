"""UnrealCheck10 informational probe: spike map CONTENTS inside the UV islands (ORM R/G/B as linear masks, BC coat
linear value, N unit length). Headless Blender, read only:  blender.exe -b --factory-startup --python maps_content_probe.py"""
import bpy, numpy as np
base = r"C:\Users\Cody\Desktop\Blender_Projects\Exports\Shuriken\Textures\T_Shuriken_Spike_%s.png"
A = {}
for k in ("BC", "ORM", "N"):
    im = bpy.data.images.load(base % k)
    im.colorspace_settings.name = "Non-Color"
    w, h = im.size
    a = np.empty(w * h * 4, dtype=np.float32); im.pixels.foreach_get(a); A[k] = a.reshape(h, w, 4)
orm = A["ORM"]
isl = orm[..., :3].max(axis=-1) > 0.0
print("PROBE island fraction", round(float(isl.mean()), 4))
print("PROBE ORM R AO p5/p50/p95", np.percentile(orm[..., 0][isl], [5, 50, 95]).round(3))
print("PROBE ORM G rough p5/p50/p95", np.percentile(orm[..., 1][isl], [5, 50, 95]).round(3))
print("PROBE ORM B metal p1/p50/p99", np.percentile(orm[..., 2][isl], [1, 50, 99]).round(3))
bc = A["BC"][..., :3][isl]
lin = np.where(bc <= 0.04045, bc / 12.92, ((bc + 0.055) / 1.055) ** 2.4)
print("PROBE BC sRGB p50", np.percentile(bc, 50, axis=0).round(3), "linear p50", np.percentile(lin, 50, axis=0).round(4), "linear p95", np.percentile(lin, 95, axis=0).round(3))
v = A["N"][..., :3][isl] * 2 - 1
L = np.linalg.norm(v, axis=-1)
print("PROBE N |n| p1/p50/p99", np.percentile(L, [1, 50, 99]).round(3), "z p1/p50", np.percentile(v[:, 2], [1, 50]).round(3), "x p1/p99", np.percentile(v[:, 0], [1, 99]).round(3), "y p1/p99", np.percentile(v[:, 1], [1, 99]).round(3))
