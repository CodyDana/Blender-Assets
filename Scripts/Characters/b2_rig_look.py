"""b2_rig_look.py - PRIVATE / DO NOT SHIP. Quick look renders of any step C1 blend (debug, never saves the blend).

  blender -b <blend> -P b2_rig_look.py -- <out_prefix> <spec.json | inline json>
spec: {"res": [w, h], "samples": 32, "shots": [{"name": "front", "view": "front", "center": [x,y,z], "dist": 3.0,
        "fit": true, "lens": 70, "hide": ["obj"], "only": ["obj"], "wire": false, "xray_joints": false}]}
"""
import bpy, os, sys, json, math
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from b2_rig_common import *  # noqa


def main():
    a = argv()
    prefix = a[0]
    spec = json.loads(open(a[1]).read()) if a[1].endswith(".json") else json.loads(a[1])
    sc = bpy.context.scene
    enable_gpu()
    try:
        sc.render.engine = 'CYCLES'
    except TypeError:
        pass
    sc.render.resolution_x, sc.render.resolution_y = spec.get("res", [800, 1100])
    sc.cycles.samples = spec.get("samples", 32)
    sc.cycles.use_denoising = True
    cam = sc.camera or bpy.data.objects.get("RIG_Camera")
    sc.camera = cam
    meshes = [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith("RIG_")]
    for shot in spec["shots"]:
        only = shot.get("only"); hide = set(shot.get("hide", []))
        for o in meshes:
            o.hide_render = (only is not None and o.name not in only) or o.name in hide
        cam.data.lens = shot.get("lens", 70)
        d = view_dir(shot["view"]) if isinstance(shot["view"], str) else Vector(shot["view"]).normalized()
        if shot.get("fit", False):
            vis = [o for o in meshes if not o.hide_render]
            mn, mx = world_bbox(vis)
            pts = [Vector((x, y, z)) for x in (mn.x, mx.x) for y in (mn.y, mx.y) for z in (mn.z, mx.z)]
            c = Vector(shot["center"]) if "center" in shot else (mn + mx) / 2
            frame_camera(cam, c, d, pts, shot.get("margin", 1.06))
        elif "bone" in shot:
            arm = bpy.data.objects["root"]
            pb = arm.pose.bones[shot["bone"]]
            c = arm.matrix_world @ pb.head
            if "bone2" in shot:
                c = (c + arm.matrix_world @ arm.pose.bones[shot["bone2"]].head) / 2
            look_at(cam, c + Vector(shot.get("offset", (0, 0, 0))), d, shot["dist"])
        else:
            look_at(cam, shot["center"], d, shot["dist"])
        render_to(f"{prefix}_{shot['name']}.png")


main()
