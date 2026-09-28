"""Round 2 light calibration: render the textured LOD0 of a (dev) build in the reference row with a grid of key / fill
settings and write the luminance profiles across the body (the reference's two-sided shading) + paint percentiles.
    blender -b BLEND --factory-startup --python r2_light_cal.py -- OUTDIR key,fill,fx,fy,fz[;...]
"""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np

P = Path(r"C:/Users/Cody/Desktop/Blender_Projects")
sys.path.insert(0, str(P / "Scripts"))
sys.path.insert(0, str(P / "Scripts/props"))
sys.dont_write_bytecode = True
from props_lib import flashbang_look as LK        # noqa: E402
from props_lib import flashbang_gallery as GAL    # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
out = Path(argv[0]).resolve()
out.mkdir(parents=True, exist_ok=True)
cfgs = [tuple(float(x) for x in c.split(",")) for c in argv[1].split(";")]
spp = int(argv[2]) if len(argv) > 2 else 64
lod0 = bpy.data.objects.get("SM_Flashbang_LOD0") or bpy.data.objects["SM_Flashbang"]
ref = GAL.ref_image() * 255.0
HS = (0.23, 1.136, 1.25, 1.77, 2.68)


def prof(im, v, H):
    y = int(GAL.VIEW_BOTTOM[v] - H * GAL.D_PX)
    row = im[y - 3:y + 4].mean(0) @ np.array([0.2126, 0.7152, 0.0722])
    return [int(row[int(GAL.VIEW_CX[v] + x * GAL.D_PX)]) for x in np.linspace(-0.45, 0.45, 10)]


res = {"ref": {v: {str(H): prof(ref, v, H) for H in HS} for v in ("v2", "v3")}}
orig = LK.studio
for (key, fill, fx, fy, fz) in cfgs:
    def studio(rig, *a, _k=key, _f=fill, _p=(fx, fy, fz), **kw):
        r = orig(rig, *a, **kw)
        for lo in rig.lights:
            if lo.name.startswith("FB_Key"):
                lo.data.energy = _k
            if lo.name.startswith("FB_Fill"):
                lo.data.energy = _f
                lo.location = _p
                d = -lo.location.copy()
                d.z += 0.08
                lo.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        return r
    LK.studio = studio
    tag = f"k{key:g}_f{fill:g}_{fx:g}_{fy:g}_{fz:g}"
    png = out / f"cal_{tag}.png"
    GAL.render_row(lod0, png, None, samples=spp)
    im = LK.load_png(png) * 255.0
    m = GAL.row_metrics(str(png))
    res[tag] = {"prof": {v: {str(H): prof(im, v, H) for H in HS} for v in ("v2", "v3")},
                "paint": {v: m[v]["paint_p10_p50_p90_ours"] for v in ("v1", "v2", "v3", "v4")},
                "bg": m["background_p50_ours"]}
LK.studio = orig
res["ref_paint"] = {v: m[v]["paint_p10_p50_p90_ref"] for v in ("v1", "v2", "v3", "v4")}
(out / "cal.json").write_text(json.dumps(res, indent=1))
