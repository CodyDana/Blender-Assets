"""Scratch: mound / base close-up of a variant (look.blend): front-low and 3/4-high, the ref crop beside it."""
import bpy, sys
from pathlib import Path
import numpy as np
ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
sys.path.insert(0, str(ROOT / "Scripts/dojo/pines"))
argv = sys.argv[sys.argv.index("--") + 1:]
v, out = argv[0], Path(argv[1])
import render_pines as rpn
rpn.setup_cycles(40); rpn.studio_rig()
sc = bpy.context.scene
rpn.set_view("final"); rpn.make_world(0.8, (0.8, 0.8, 0.8))
fam = v[4]
for o in bpy.data.objects:
    if o.type == "MESH":
        o.hide_render = not (o.name.startswith(f"SM_DKN_{v}_") or o.name == f"SM_DKN_BaseMound_{fam}") or o.name.startswith("UCX_")
S = rpn.SPEC[v]
if "mound" in S:
    m = S["mound"]; c = np.array([m["cx"], m["cy"], 0.1]); w = 2 * m["rx"] * 1.15
else:
    c = np.array([0.0, 0.0, 0.6]); w = 2.2
sc.render.resolution_x, sc.render.resolution_y = 1000, 700
d = w / (36.0 / 50.0)
for name, off, look in (("front", (0, -d, 0.25 * d * 0.3), (0, 0, 0.12 if "mound" in S else 0.55)), ("high", (0.5 * d, -0.8 * d, 0.55 * d), (0, 0, 0.05 if "mound" in S else 0.5))):
    rpn.persp_camera(c + np.array(off), c + np.array(look) - np.array([0, 0, c[2]]), 50)
    rpn.render(out / f"mound_{v}_{name}.png")
