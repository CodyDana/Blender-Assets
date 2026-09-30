import bpy, sys, bmesh
from pathlib import Path
import numpy as np
ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
sys.path.insert(0, str(ROOT / "Scripts/dojo/pines"))
argv = sys.argv[sys.argv.index("--") + 1:]
out = Path(argv[0]); cands = [a.split(":") for a in argv[1:]]
import render_pines as rpn
rpn.setup_cycles(32); rpn.studio_rig()
sc = bpy.context.scene
rpn.set_view("final"); rpn.make_world(0.8, (0.8, 0.8, 0.8))
sc.render.film_transparent = True
[setattr(o, "hide_render", True) for o in bpy.data.objects if o.name == "__floor"]
sc.render.resolution_x, sc.render.resolution_y = 600, 680
for v, pi in cands:
    pi = int(pi)
    rpn.show_only(v)
    for o in bpy.data.objects:
        if "BaseMound" in o.name: o.hide_render = True
    pad = rpn.SPEC[v]["pads"][pi]
    c = np.array(pad.get("profile", {}).get("centre", pad["centre"]))
    w = 2 * pad.get("profile", {}).get("hx", pad["rx"])
    zlo = float(pad["centre"][2]) - float(pad.get("rz_bot", 0.1)) - 0.06
    zhi = float(pad["centre"][2]) + float(pad.get("rz_top", 0.1)) + 0.10
    temps = []
    for o in [o for o in bpy.data.objects if o.type == "MESH" and not o.hide_render and o.name.startswith(f"SM_DKN_{v}_")]:
        t_ = o.copy(); t_.data = o.data.copy(); sc.collection.objects.link(t_)
        bm = bmesh.new(); bm.from_mesh(t_.data)
        bmesh.ops.delete(bm, geom=[vv for vv in bm.verts if not (zlo < vv.co.z < zhi)], context="VERTS")
        bm.to_mesh(t_.data); bm.free(); o.hide_render = True; temps.append((o, t_))
    h = 1.08 * w / (36.0 / 50.0) + 0.1
    rpn.persp_camera(c + np.array([0, -0.02, h]), c, 50)
    rpn.render(out / f"padtop_{v}_{pi}.png")
    for o, t_ in temps:
        me = t_.data; bpy.data.objects.remove(t_); bpy.data.meshes.remove(me); o.hide_render = False
