"""Quick Workbench previews of the stage caches (local frame, right shoe).

    blender -b --factory-startup --python Scripts/SnowFlowerHeels/hb_preview.py -- <tag> [npz ...]

Renders side (lateral), top, back and a reference-like 3/4 view to WorkFiles/SnowFlowerHeels/r1/preview/<tag>_*.png.
Meshes: every npz key pair <name>_v / <name>_q|<name>_t|<name>_f; foot always in grey.
"""
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Euler, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hb_common as C  # noqa: E402


def mesh_from(name, v, faces, color):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, x)) for x in v], [], [tuple(map(int, f)) for f in faces])
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.color = color
    for p in me.polygons:
        p.use_smooth = True
    return ob


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    tag = argv[0]
    files = argv[1:] or [str(C.CACHE / "last_r.npz")]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    palette = [(0.55, 0.35, 0.25, 1), (0.25, 0.45, 0.7, 1), (0.7, 0.7, 0.3, 1), (0.4, 0.7, 0.4, 1), (0.7, 0.3, 0.6, 1)]
    ci = 0
    for f in files:
        z = np.load(f)
        names = sorted({k[:-2] for k in z.files if k.endswith("_v")})
        for n in names:
            faces = []
            for suf in ("_q", "_t", "_f"):
                if n + suf in z.files and len(z[n + suf]):
                    faces += z[n + suf].tolist()
            col = (0.8, 0.8, 0.8, 1) if n.startswith("foot") else palette[ci % len(palette)]
            if not n.startswith("foot"):
                ci += 1
            mesh_from(n, z[n + "_v"], faces, col)
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.world = bpy.data.worlds.new("w"); sc.world.color = (1, 1, 1)
    sh = sc.display.shading
    sh.light = "STUDIO"
    sh.color_type = "OBJECT"
    sh.show_shadows = False
    sh.show_cavity = True
    sc.render.resolution_x = 1000
    sc.render.resolution_y = 800
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.type = "ORTHO"
    out = C.R1 / "preview"
    out.mkdir(parents=True, exist_ok=True)
    center = Vector((110, 5, 140))
    views = {
        "side_lat": (Vector((0, -1, 0)), 330),
        "side_med": (Vector((0, 1, 0)), 330),
        "top": (Vector((0, 0, 1)), 330),
        "back": (Vector((-1, 0, 0.0)), 330),
        "front": (Vector((1, 0, 0.0)), 330),
        "ref34": (Vector((math.cos(math.radians(48)) * math.cos(math.radians(24)),
                          -math.sin(math.radians(48)) * math.cos(math.radians(24)), math.sin(math.radians(24)))), 360),
    }
    for vn, (d, scale) in views.items():
        cam.data.ortho_scale = scale
        cam.location = center + d * 800
        up = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler() if abs(d.z) < 0.9 else Euler((0, 0, -math.pi / 2))
        cam.data.clip_end = 5000
        sc.render.filepath = str(out / f"{tag}_{vn}.png")
        bpy.ops.render.render(write_still=True)
    print("PREVIEW_OK", out)


main()
