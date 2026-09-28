# Judge check renders for 2B private step A. Opens the base .blend read-only; NEVER saves it.
import bpy, sys, os, bmesh
from mathutils import Vector
OUT = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/Characters/2B_private/checks/"
sc = bpy.context.scene
sc.render.resolution_x = 900; sc.render.resolution_y = 900
try:
    sc.cycles.samples = 96
except Exception: pass
cam = sc.camera
cam.data.lens = 85
objs = {o.name: o for o in bpy.data.objects}
body = [o for o in bpy.data.objects if o.name.startswith("BODY_")]
clo = [o for o in bpy.data.objects if o.name.startswith("CLO_")]
hair = [o for o in bpy.data.objects if o.name.startswith("HAIR_")]

def show(sets):
    for o in body + clo + hair:
        o.hide_render = o.name not in sets
    # hard rule: underwear always visible whenever the body is rendered
    if any(n.startswith("BODY_") for n in sets):
        objs["CLO_Underwear"].hide_render = False

def aim(target, direction, dist):
    t = Vector(target); d = Vector(direction).normalized()
    cam.location = t + d * dist
    q = (t - cam.location).to_track_quat('-Z', 'Y')
    cam.rotation_euler = q.to_euler()

def shot(name, sets, target, direction, dist, lens=85):
    show(sets); cam.data.lens = lens
    aim(target, direction, dist)
    sc.render.filepath = OUT + name + ".png"
    bpy.ops.render.render(write_still=True)
    print("WROTE", sc.render.filepath)

def wbbox(o, pred):
    m = o.matrix_world
    pts = [m @ v.co for v in o.data.vertices]
    pts = [p for p in pts if pred(p)]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi, (lo + hi) / 2

BODYSKIN = {o.name for o in body}
legs = objs["BODY_Legs"]; arms = objs["BODY_Arms"]
lo, hi, rfoot = wbbox(legs, lambda p: p.x < 0 and p.z < 0.14)
lo2, hi2, lfoot = wbbox(legs, lambda p: p.x > 0 and p.z < 0.14)
print("RFOOT", lo, hi, "LFOOT", lo2, hi2)
def handc(sign):
    ps = [arms.matrix_world @ v.co for v in arms.data.vertices]
    ps = [p for p in ps if p.x * sign > 0]
    zmin = min(p.z for p in ps)
    sel = [p for p in ps if p.z < zmin + 0.12]
    return sum(sel, Vector()) / len(sel)
rhand = handc(-1); lhand = handc(1)
print("RHAND", rhand, "LHAND", lhand)

# 1. crushed right foot, barefoot, from outside, front, and below-ish
shot("rfoot_out", BODYSKIN, rfoot, (-1, -0.2, 0.15), 0.55)
shot("rfoot_front", BODYSKIN, rfoot, (-0.2, -1, 0.3), 0.55)
shot("rfoot_in", BODYSKIN, rfoot, (1, -0.3, 0.1), 0.55)
shot("feet_back", BODYSKIN, (rfoot + lfoot) / 2, (0, 1, 0.25), 0.8)
# 2. hands / wrist seams (body + kimono upper for cover, sleeves hidden)
cover = BODYSKIN | {"CLO_Upper", "CLO_UpEdge01", "CLO_UpperEdge02", "CLO_Belt", "CLO_LowerOut", "CLO_LowerIn", "CLO_LowerEdge"}
shot("rhand", cover, rhand, (-0.6, -1, 0.2), 0.45)
shot("lhand", cover, lhand, (0.6, -1, 0.2), 0.45)
# 3. neck seam, no hair, with kimono for cover
_, _, neck = wbbox(objs["BODY_Body"], lambda p: p.z > 1.40)
print("NECK", neck)
shot("neck_front", cover, neck, (0, -1, 0.1), 0.5)
shot("neck_back", cover, neck, (0.3, 1, 0.1), 0.5)
# 4. outfit fit: neckline, belt, slit, sleeves -- full outfit
full = BODYSKIN | {o.name for o in clo} | {o.name for o in hair}
_, _, chest = wbbox(objs["BODY_Body"], lambda p: 1.15 < p.z < 1.40)
shot("fit_chest_front", full, chest, (0, -1, 0.05), 0.75)
shot("fit_chest_tq", full, chest, (-0.8, -0.7, 0.05), 0.75)
shot("fit_waist_side", full, chest - Vector((0, 0, 0.25)), (-1, 0, 0.05), 0.9)
shot("fit_slit", full, Vector((0, 0, 0.62)), (0.3, -1, 0.1), 1.0)
shot("fit_boots", full, Vector((0, 0, 0.25)), (-0.4, -1, 0.1), 1.0)
# 5. clothing on the bare body without kimono to look for poke-through of skin through kimono
shot("fit_back", full, chest - Vector((0, 0, 0.1)), (0, 1, 0.1), 1.0)
# 6. Head texture region check: Torso-C downsample
img = bpy.data.images.get("Torso-C")
if img:
    c = img.copy(); c.scale(1024, 1024); c.filepath_raw = OUT + "tex_TorsoC.png"; c.file_format = 'PNG'; c.save()
img = bpy.data.images.get("hair_d")
if img:
    c = img.copy(); c.filepath_raw = OUT + "tex_hair_d.png"; c.file_format = 'PNG'; c.save()
print("DONE")
