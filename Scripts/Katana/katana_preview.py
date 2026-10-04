"""Development preview of the work blend (Workbench, flat part colours): not a shipped render.

    blender -b WorkFiles/katana/build/katana_work.blend --factory-startup --python Scripts/Katana/katana_preview.py -- --lod 0 --out DIR
"""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(n, d):
    return argv[argv.index(n) + 1] if n in argv else d


LOD = int(arg("--lod", "0"))
OUT = Path(arg("--out", "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/katana/build/preview"))
VIEWS = arg("--views", "side,tsuka,tsuka_edge,kissaki,hero,end,habaki").split(",")
OUT.mkdir(parents=True, exist_ok=True)
sc = bpy.context.scene
COLS = {"blade": (0.42, 0.45, 0.48), "habaki": (0.69, 0.55, 0.34), "seppa_blade": (0.72, 0.58, 0.37),
        "seppa_tsuka": (0.72, 0.58, 0.37), "tsuba": (0.22, 0.21, 0.2), "fuchi": (0.22, 0.21, 0.2),
        "kashira": (0.22, 0.21, 0.2), "eyelets": (0.72, 0.58, 0.37), "core": (0.91, 0.89, 0.82),
        "cords": (0.06, 0.06, 0.065), "menuki": (0.6, 0.48, 0.27), "mekugi": (0.66, 0.54, 0.35),
        "band": (0.06, 0.06, 0.065), "shell": (0.3, 0.3, 0.3)}
for c in bpy.data.collections:
    show = c.name == f"LOD{LOD}_parts"
    for o in c.objects:
        o.hide_render = not show
        if show:
            o.color = COLS.get(o.get("kat_part", ""), (0.5, 0.5, 0.5)) + (1.0,)
sc.render.engine = "BLENDER_WORKBENCH"
sh = sc.display.shading
sh.light = "STUDIO"
sh.color_type = "OBJECT"
sh.show_cavity = True
sh.cavity_type = "WORLD"
sh.show_object_outline = True
sh.show_specular_highlight = True
w = bpy.data.worlds.new("w")
w.color = (1, 1, 1)
sc.world = w
sc.view_settings.view_transform = "Standard"
cam_d = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_d)
sc.collection.objects.link(cam)
sc.camera = cam


def cam_axes(right, up):
    r = Vector(right).normalized()
    u = Vector(up)
    u = (u - r * u.dot(r)).normalized()
    z = r.cross(u)
    return Matrix((r, u, z)).transposed()


def shot(name, centre_mm, right, up, ortho_mm, px_w, px_h, persp=None):
    rot = cam_axes(right, up)
    c = Vector(centre_mm) * 0.001
    back = rot.col[2]
    if persp:
        cam_d.type = "PERSP"
        cam_d.lens = persp[1]
        cam.matrix_world = Matrix.Translation(c + back * persp[0] * 0.001) @ rot.to_4x4()
    else:
        cam_d.type = "ORTHO"
        cam_d.ortho_scale = ortho_mm * 0.001
        cam.matrix_world = Matrix.Translation(c + back * 2.0) @ rot.to_4x4()
    cam_d.clip_start = 0.001
    cam_d.clip_end = 10.0
    sc.render.resolution_x = px_w
    sc.render.resolution_y = px_h
    sc.render.filepath = str(OUT / f"L{LOD}_{name}.png")
    bpy.ops.render.render(write_still=True)


V = {
    "side": lambda: shot("side", (20, 0, 275), (0, 0, 1), (-1, 0, 0), 1000, 2400, 400),
    "tsuka": lambda: shot("tsuka", (0, 0, -85), (0, 0, 1), (-1, 0, 0), 310, 2000, 360),
    "tsuka_edge": lambda: shot("tsuka_edge", (0, 0, -85), (0, 0, 1), (0, 1, 0), 310, 2000, 360),
    "kissaki": lambda: shot("kissaki", (60, 0, 720), (math.sin(0.19), 0, math.cos(0.19)), (-math.cos(0.19), 0, math.sin(0.19)), 110, 1600, 900),
    "hero": lambda: shot("hero", (0, 0, -60), (0.35, -0.2, 0.9), (-0.9, -0.15, 0.3), 0, 1800, 1200, persp=(420, 50)),
    "end": lambda: shot("end", (-1, 0, -200), (0, 1, 0), (-1, 0, 0), 60, 1000, 1000) if False else
    shot("end", (0, 0, -215), (0, -1, 0), (-1, 0, 0), 60, 1000, 1000),
    "habaki": lambda: shot("habaki", (0, 0, 60), (0.6, -0.8, 0.0), (0, 0, 1), 0, 1600, 1200, persp=(200, 60)),
}
for v in VIEWS:
    V[v]()
print("PREVIEW_DONE")
