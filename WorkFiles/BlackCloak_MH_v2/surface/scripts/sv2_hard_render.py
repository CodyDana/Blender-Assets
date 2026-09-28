# Clasp + fray check render: the clasp appended from BlackCloakV2_Clasp.blend on a 30 cm cloth swatch with a fray card
# along its lower edge, calibrated studio (white card 0.90 linear, Standard).  Two views: 3/4 close and straight-on.
import sys, os, json, math
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/Scripts/garments/blackcloak_v2")
import bpy, bmesh
from mathutils import Vector
import bcv2_material as BM
import bcv2_studio as ST

S = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_MH_v2/surface/"
tag = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "final"
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
sc = bpy.context.scene
P = BM.load_params()
with bpy.data.libraries.load(S + "BlackCloakV2_Clasp.blend", link=False) as (src, dst):
    dst.objects = ["BlackCloakV2_Clasp"]
clasp = dst.objects[0]
sc.collection.objects.link(clasp)


def plane(name, w, h, uvfn):
    bm = bmesh.new()
    vs = [bm.verts.new((x, 0, z)) for x, z in ((-w / 2, 0), (w / 2, 0), (w / 2, h), (-w / 2, h))]
    f = bm.faces.new(vs[::-1])
    uv = bm.loops.layers.uv.new("UVMap")
    for l in f.loops:
        l[uv].uv = uvfn(l.vert.co)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    sc.collection.objects.link(ob)
    return ob


sw = plane("SV2_ClothSwatch", 0.30, 0.30, lambda c: (c.x / 0.45 + 0.3, c.z / 0.45 + 0.1))
sw.location = (0, 0, 0.85)
sw.data.materials.append(BM.cloth_material(P))
fr = plane("SV2_FrayCard", 0.30, 0.056, lambda c: (c.x / 0.45 + 0.3, c.z / 0.056))
fr.location = (0, 0.0005, 0.85 - 0.056 + 0.014)        # card overlaps the swatch edge by its 14 mm opaque band
fr.data.materials.append(BM.fray_material(P))
clasp.location = (0.02, -0.001, 1.02)
clasp.rotation_euler = (math.radians(90), 0, 0)        # local +Z -> world -Y (towards the camera)
cam = bpy.data.objects.new("SV2_Cam", bpy.data.cameras.new("SV2_Cam"))
sc.collection.objects.link(cam)
cam.data.lens = 85
tgt = Vector((0.0, 0, 0.93))
cam.location = tgt + Vector((-0.28, -0.75, 0.12))
cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
info = {"studio": ST.studio(sc, cam, centre=(0, 0, 0.93), card_offset=(0, -0.3, 0.1))}
bpy.data.objects["ST_Floor"].hide_render = True
sc.camera = cam
sc.render.resolution_x, sc.render.resolution_y = 720, 720
sc.cycles.samples = 256
sc.cycles.use_denoising = True
sc.render.film_transparent = False
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGB"
sc.render.image_settings.color_depth = "8"
sc.render.filepath = S + "renders/%s_clasp_fray_q34.png" % tag
bpy.ops.render.render(write_still=True)
cam2 = bpy.data.objects.new("SV2_Cam2", bpy.data.cameras.new("SV2_Cam2"))
sc.collection.objects.link(cam2)
cam2.data.lens = 100
t2 = Vector((0.02, 0, 1.02))
cam2.location = t2 + Vector((0.0, -0.32, 0.0))
cam2.rotation_euler = (t2 - cam2.location).to_track_quat("-Z", "Y").to_euler()
sc.camera = cam2
sc.render.resolution_x, sc.render.resolution_y = 512, 512
sc.render.filepath = S + "renders/%s_clasp_front.png" % tag
bpy.ops.render.render(write_still=True)
json.dump(info, open(S + "logs/%s_clasp_fray.json" % tag, "w"), indent=1)
print("HARD ok", info["studio"]["calibration"]["white_card_linear_after"])
