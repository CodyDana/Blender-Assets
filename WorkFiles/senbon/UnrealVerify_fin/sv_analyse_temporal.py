"""Reduce passC3 (temporal AA probe) frames: distinct values (binary vs fractional) and column continuity."""
import json, sys
from pathlib import Path
import bpy
import numpy as np
sys.dont_write_bytecode = True
HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\senbon\UnrealVerify_fin")
c3 = json.loads((HERE / "passC3.json").read_text())
out = {}
for run in c3["runs"]:
    dm = run["distance_m"]; px = 2 * dm * 100 / 1920
    c_lo, c_hi = 960 - 6.5 / px, 960 + 6.5 / px
    sp = c_hi - c_lo; a, b = int(np.ceil(c_lo + .05 * sp)), int(np.floor(c_hi - .05 * sp))
    for i, fn in run["files"].items():
        img = bpy.data.images.load(str(HERE / "renders_mask" / fn)); img.colorspace_settings.name = "Non-Color"
        w, h = img.size; arr = np.empty(w * h * 4, np.float32); img.pixels.foreach_get(arr)
        L = arr.reshape(h, w, 4)[::-1, :, :3].max(-1); bpy.data.images.remove(img)
        band = L[500:580, a:b + 1]
        vals = np.unique((band[band > 0.004] * 255).round())
        out[f"{dm:.2f}_c{i}"] = {"distinct_nonzero_levels": int(len(vals)), "max": float(L.max()),
                                 "cont_any>0.02": float((band.max(0) > 0.02).mean()),
                                 "cont_any>0.5max": float((band.max(0) > 0.5 * max(L.max(), 1e-6)).mean()),
                                 "col_sum_mean": float(band.sum(0).mean()), "col_sum_min": float(band.sum(0).min())}
(HERE / "analysis_temporal.json").write_text(json.dumps(out, indent=1))
print("SV_TEMPORAL_DONE")
