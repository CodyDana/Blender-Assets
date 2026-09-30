"""Scratch: render one pad of a variant from front / above / below-front at close range (look.blend)."""
import bpy, sys, json, math
from pathlib import Path
import numpy as np
from mathutils import Vector
ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
sys.path.insert(0, str(ROOT / "Scripts/dojo/pines"))
argv = sys.argv[sys.argv.index("--") + 1:]
v, pi, out = argv[0], int(argv[1]), Path(argv[2])
import render_pines as rpn
rpn.setup_cycles(32)
rpn.studio_rig()
sc = bpy.context.scene
rpn.set_view("final"); rpn.make_world(0.8, (0.8, 0.8, 0.8))
for o in bpy.data.objects:
    if o.type == "MESH":
        o.hide_render = not o.name.startswith(f"SM_DKN_{v}_") or o.name.startswith("UCX_")
pad = rpn.SPEC[v]["pads"][pi]
c = np.array(pad.get("profile", {}).get("centre", pad["centre"]))
w = 2 * pad.get("profile", {}).get("hx", pad["rx"])
d = 1.1 * w / (36.0 / 50.0)
sc.render.resolution_x, sc.render.resolution_y = 900, 700
sc.render.film_transparent = False
for name, off in {"front": (0, -d, 0.05), "top": (0, -0.05, d), "under": (0, -d * 0.9, -d * 0.35), "side": (d, 0, 0.05)}.items():
    rpn.persp_camera(c + np.array(off), c + np.array([0, 0, 0.05]), 50)
    rpn.render(out / f"pad{pi}_{name}.png")
