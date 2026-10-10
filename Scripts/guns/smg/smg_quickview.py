"""Quick workbench views of a built SMG01 blend (development aid; inside Blender):

    blender -b <blend> --factory-startup --python Scripts/guns/smg/smg_quickview.py -- --out dir [--only a,b]
            [--views left,right,top,q34,front,rear,bottom,q34r] [--res 1600] [--focus x0,x1,z0,z1] [--wire]
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
sys.path.insert(0, str(Path(__file__).resolve().parent))


def arg(n, d=None):
    return argv[argv.index(n) + 1] if n in argv else d


out = Path(arg("--out", "."))
out.mkdir(parents=True, exist_ok=True)
only = [v for v in (arg("--only", "") or "").split(",") if v]
views = (arg("--views", "left,right,top,q34") or "").split(",")
res = int(arg("--res", "1600"))
objs = [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("_") and (not only or o.name in only)]
for o in bpy.data.objects:
    if o.type == "MESH":
        o.hide_render = o not in objs
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sh = sc.display.shading
sh.light = "STUDIO"
sh.color_type = "SINGLE"
sh.single_color = (0.55, 0.56, 0.6)
sh.show_cavity = True
sh.cavity_type = "BOTH"
sh.show_object_outline = False
try:
    sh.show_specular_highlight = True
except Exception:  # noqa: BLE001
    pass
sc.render.film_transparent = False
sc.world = sc.world or bpy.data.worlds.new("W")
P = np.vstack([np.array([o.matrix_world @ Vector(c) for c in o.bound_box]) for o in objs])
lo, hi = P.min(0), P.max(0)
foc = arg("--focus")
if foc:
    x0, x1, z0, z1 = [float(v) * 0.001 for v in foc.split(",")]
    from smg_common import GRIP  # noqa
    x0, x1 = x0 - GRIP[0] * 0.001, x1 - GRIP[0] * 0.001
    z0, z1 = z0 - GRIP[2] * 0.001, z1 - GRIP[2] * 0.001
    lo = np.array([x0, lo[1], z0])
    hi = np.array([x1, hi[1], z1])
c = (lo + hi) / 2
ext = float(np.max(hi - lo))
cam_d = bpy.data.cameras.new("QC")
cam = bpy.data.objects.new("QC", cam_d)
sc.collection.objects.link(cam)
sc.camera = cam
sc.render.resolution_x = res
sc.render.resolution_y = int(res * 0.62)
DIRS = {"left": (0, 1, 0), "right": (0, -1, 0), "top": (0, 0, 1), "bottom": (0, 0, -1), "front": (1, 0, 0),
        "rear": (-1, 0, 0), "q34": (0.75, 0.62, 0.25), "q34r": (0.75, -0.62, 0.25), "q34b": (-0.6, 0.7, -0.35),
        "q34rb": (-0.6, -0.7, 0.35)}
for v in views:
    d = np.array(DIRS[v], float)
    d /= np.linalg.norm(d)
    cam_d.type = "ORTHO"
    # fit the projected extent (view-plane width / height) with the render aspect
    rgt = np.cross(d, np.array([0, 0, 1.0])) if abs(d[2]) < 0.9 else np.array([0, 1.0, 0])
    rgt /= np.linalg.norm(rgt)
    upv = np.cross(rgt, d)
    corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
    wv = float(np.ptp(corners @ rgt))
    hv = float(np.ptp(corners @ upv))
    cam_d.ortho_scale = max(wv, hv / 0.62) * 1.06
    cam.location = Vector(c + d * 2.0)
    up = Vector((0, 0, 1)) if abs(d[2]) < 0.9 else Vector((1, 0, 0))
    rot = (Vector(-d)).to_track_quat("-Z", "Y")
    # roll so that 'up' is up
    cam.rotation_euler = rot.to_euler()
    m = cam.matrix_world.to_3x3()
    ax_up = m @ Vector((0, 1, 0))
    if ax_up.dot(up) < 0:
        cam.rotation_euler.rotate_axis("Z", math.pi)
    cam_d.clip_end = 10.0
    sc.render.filepath = str(out / f"{v}.png")
    bpy.ops.render.render(write_still=True)
print("QUICKVIEW_DONE", out)
