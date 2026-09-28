"""Round 2 light calibration v2: whole rigs (strip softboxes) on the textured dev LOD0.
    blender -b --factory-startup DEV/Assets/Flashbang.blend --python r2_light_cal2.py -- OUT rigs.json [spp] [closeups]
rigs.json: {"tag": [[name, shape, [x,y,z], [tx,ty,tz], size, size_y, power, [r,g,b]], ...], ...}
"""
import json
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
rigs = json.loads(Path(argv[1]).read_text())
spp = int(argv[2]) if len(argv) > 2 else 64
closeups = argv[3].split(",") if len(argv) > 3 and argv[3] else []
lod0 = bpy.data.objects.get("SM_Flashbang_LOD0")
ref = GAL.ref_image() * 255.0
HS = (0.23, 1.136, 1.25, 1.77, 2.68)


def prof(im, v, H):
    y = int(GAL.VIEW_BOTTOM[v] - H * GAL.D_PX)
    row = im[y - 3:y + 4].mean(0) @ np.array([0.2126, 0.7152, 0.0722])
    return [int(row[int(GAL.VIEW_CX[v] + x * GAL.D_PX)]) for x in np.linspace(-0.45, 0.45, 10)]


def region_stats(im, v, h0, h1, x0=-0.45, x1=0.45):
    y0 = int(GAL.VIEW_BOTTOM[v] - h1 * GAL.D_PX)
    y1 = int(GAL.VIEW_BOTTOM[v] - h0 * GAL.D_PX)
    xa = int(GAL.VIEW_CX[v] + x0 * GAL.D_PX)
    xb = int(GAL.VIEW_CX[v] + x1 * GAL.D_PX)
    lum = im[y0:y1, xa:xb] @ np.array([0.2126, 0.7152, 0.0722])
    return [int(np.percentile(lum, q)) for q in (10, 50, 90)]


res = {"ref": {"prof": {v: {str(H): prof(ref, v, H) for H in HS} for v in ("v2", "v3")},
               "cap": {v: region_stats(ref, v, 0.05, 0.40) for v in ("v1", "v2", "v3", "v4")},
               "head": {v: region_stats(ref, v, 3.2, 3.6, -0.3, 0.3) for v in ("v1", "v2", "v3", "v4")}}}
for tag, rig in rigs.items():
    LK.LIGHTS = [(n, sh, tuple(l), tuple(t), sz, sy, pw, tuple(c)) for n, sh, l, t, sz, sy, pw, c in rig]
    png = out / f"row_{tag}.png"
    GAL.render_row(lod0, png, None, samples=spp)
    im = LK.load_png(png) * 255.0
    m = GAL.row_metrics(str(png))
    res[tag] = {"prof": {v: {str(H): prof(im, v, H) for H in HS} for v in ("v2", "v3")},
                "paint": {v: m[v]["paint_p10_p50_p90_ours"] for v in ("v1", "v2", "v3", "v4")},
                "cap": {v: region_stats(im, v, 0.05, 0.40) for v in ("v1", "v2", "v3", "v4")},
                "head": {v: region_stats(im, v, 3.2, 3.6, -0.3, 0.3) for v in ("v1", "v2", "v3", "v4")},
                "bg": m["background_p50_ours"]}
    for k in closeups:
        GAL.render_closeup(lod0, k, out / f"{k}_{tag}.png", samples=spp)
res["ref"]["paint"] = {v: m[v]["paint_p10_p50_p90_ref"] for v in ("v1", "v2", "v3", "v4")}
res["ref"]["bg"] = m["background_p50_ref"]
(out / "cal.json").write_text(json.dumps(res, indent=1))
for k, v in res.items():
    print(k, "bg", v.get("bg"), "paint", v["paint"])
    print("    cap", v["cap"], "head", v["head"])
    for vv in v["prof"]:
        print("   ", vv, v["prof"][vv])
