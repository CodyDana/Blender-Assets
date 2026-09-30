"""Rock close-ups on a build blend (perspective, studio rig of render_pines): front, 3/4, high 3/4, back.

blender -b <blend> --factory-startup --python rock_look.py -- --out DIR [--variants PineD1,PineD2] [--samples 64]
"""
import math
import sys
from pathlib import Path

import bpy

ROOT = Path(r"C:/Users/Cody/Desktop/Blender_Projects")
sys.path.insert(0, str(ROOT / "Scripts" / "dojo" / "pines"))
sys.argv = [sys.argv[0]] + (sys.argv[sys.argv.index("--"):] if "--" in sys.argv else [])
import argparse  # noqa: E402
import render_pines as R  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--variants", default="PineD1,PineD2")
ap.add_argument("--samples", type=int, default=64)
ap.add_argument("--res", type=int, default=900)
ap.add_argument("--no-mound", action="store_true")
a = ap.parse_args(argv)
out = Path(a.out).resolve()
out.mkdir(parents=True, exist_ok=True)
R.setup_cycles(a.samples)
R.studio_rig()
R.set_view("final")
sc = bpy.context.scene
sc.render.resolution_x = a.res
sc.render.resolution_y = a.res
sc.render.film_transparent = False
for v in a.variants.split(","):
    R.show_only(v)
    if a.no_mound:
        m = bpy.data.objects.get(f"SM_DKN_BaseMound_{v[4]}")
        if m:
            m.hide_render = True
    look = (0.0, 0.0, 0.62)
    for name, az, el, dist in (("front", 0, 8, 3.4), ("q3", 45, 12, 3.4), ("high", -40, 38, 3.2),
                               ("back", 180, 10, 3.4)):
        ar, er = math.radians(az), math.radians(el)
        loc = (dist * math.sin(ar) * math.cos(er), -dist * math.cos(ar) * math.cos(er), look[2] + dist * math.sin(er))
        R.persp_camera(loc, look, lens=50)
        R.render(out / f"{v}_rock_{name}.png")
