"""Round 6 fix f1: Workbench silhouette previews of candidate camera framings on the composed showcase
(Assets/Dojo/DojoShowcase.blend, read only: nothing is saved). Args: -- <out_dir> <cams.json>
cams.json: [[name, [x,y,z], [lx,ly,lz], hfov_deg, [w,h]], ...] (Blender frame, metres)."""
import bpy, json, math, sys
from mathutils import Vector
a = sys.argv[sys.argv.index("--") + 1:]
out, cams = a[0], json.load(open(a[1]))
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sh = sc.display.shading
sh.light = "STUDIO"; sh.color_type = "OBJECT"; sh.show_shadows = True; sh.show_cavity = True
sh.background_type = "WORLD" if hasattr(sh, "background_type") else sh.background_type
if sc.world is None:
    sc.world = bpy.data.worlds.new("W")
sc.world.color = (0.55, 0.62, 0.8)
sc.display.shading.background_type = "WORLD"
import random
rnd = random.Random(3)
for o in bpy.data.objects:
    n = o.name
    if n.startswith("UCX_") or "Boundary" in n or "_1v1_" in n or "SM_DGB_Ground_Outside" in n:
        o.hide_render = True
        continue
    base = o.instance_collection.name if o.instance_type == "COLLECTION" and o.instance_collection else n
    col = (0.6, 0.6, 0.6, 1)
    if "Ridge" in base: col = (0.35, 0.38, 0.5, 1)
    elif "FarTown" in base: col = (0.75, 0.45, 0.3, 1)
    elif "DKX_House" in base: col = (0.9, 0.55, 0.2, 1)
    elif "DKH_" in base: col = (0.3, 0.3, 0.3, 1)
    elif "DKO_" in base or "DKC_" in base: col = (0.5, 0.5, 0.35, 1)
    elif "DGB_Tree" in base: col = (0.2, 0.6, 0.2, 1)
    o.color = col
cam = bpy.data.objects.new("PrevCam", bpy.data.cameras.new("PrevCam"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.clip_end = 5000.0
for name, loc, look, hfov, wh in cams:
    cam.location = Vector(loc)
    d = Vector(look) - Vector(loc)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.sensor_fit = "HORIZONTAL"
    cam.data.angle = math.radians(hfov)
    sc.render.resolution_x, sc.render.resolution_y = wh[0] // 2, wh[1] // 2
    sc.render.filepath = f"{out}/{name}.png"
    bpy.ops.render.render(write_still=True)
    print("WB", name, flush=True)
