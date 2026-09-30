"""Debug probe: which object / material / local point does a pixel of an assembly shot hit?
Run: blender -b --factory-startup --python probe_pixel.py -- <shot name> <px> <py> [<px> <py> ...]"""
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(r"C:/Users/Cody/Desktop/Blender_Projects")
sys.path.insert(0, str(ROOT / "Scripts" / "dojo" / "stonekit"))
import sk_shared as S  # noqa: E402

RS = S.load_builder(ROOT / "Scripts" / "dojo" / "stonekit" / "render_stairs.py", "render_stairs_mod")
args = sys.argv[sys.argv.index("--") + 1:]
shot = args[0]
pix = [(float(args[i]), float(args[i + 1])) for i in range(1, len(args), 2)]
sc, kit, pieces = RS.load_kit()
placed, lights = RS.assembly(pieces, kit)
nm, loc, look, lens, w, h = next(s for s in RS.assembly_shots() if s[0] == shot)
c = RS.cam(nm, loc, look, lens=lens)
sc.render.resolution_x, sc.render.resolution_y = w, h
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
fr = c.data.view_frame(scene=sc)          # camera-space corners: top-right, bottom-right, bottom-left, top-left
tr, br, bl, tl = fr
for (px, py) in pix:
    u, v = px / w, py / h
    p_cam = tl + (tr - tl) * u + (bl - tl) * v
    d = (c.matrix_world.to_3x3() @ p_cam).normalized()
    hit, co, nrm, fi, ob, mw = sc.ray_cast(dg, c.matrix_world.translation, d)
    if not hit:
        print("PROBE", px, py, "miss")
        continue
    me = ob.data
    mat = me.materials[me.polygons[fi].material_index].name if me.materials else None
    lp = ob.matrix_world.inverted() @ co
    print("PROBE", px, py, ob.name, me.name, mat, "world", tuple(round(x, 3) for x in co), "local",
          tuple(round(x, 3) for x in lp), "normal", tuple(round(x, 2) for x in nrm))
