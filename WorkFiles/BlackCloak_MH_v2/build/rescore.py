# builder helper: re-run the fan proxy on saved jinp previews. blender -b --factory-startup --python rescore.py -- tag1 tag2 ...
import sys, os, math, json, bpy, numpy as np
from mathutils import Vector
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/Scripts/garments/blackcloak_v2")
import bcv2_fanscore as FS
W = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_MH_v2/build"
sc = bpy.context.scene
camd = bpy.data.cameras.new("c"); camd.lens = 85; camd.sensor_fit = "VERTICAL"; camd.sensor_height = 24
cop = bpy.data.objects.new("c", camd); sc.collection.objects.link(cop); sc.camera = cop
tgt = Vector((0, 0, 1.358)); dist = 1.10 / (24 / 85); yw, pt = math.radians(12), math.radians(3)
dv = Vector((math.sin(yw) * math.cos(pt), -math.cos(yw) * math.cos(pt), math.sin(pt))) * dist
cop.location = tgt + dv; cop.rotation_euler = (-dv).to_track_quat("-Z", "Y").to_euler()
sc.render.resolution_x, sc.render.resolution_y = 605, 908
bpy.context.view_layer.update()
from bpy_extras.object_utils import world_to_camera_view
for tag in sys.argv[sys.argv.index("--") + 1:]:
    D = np.load(os.path.join(W, "drape_%s.npz" % tag))
    cpt = Vector(tuple(D["ring_c"] + D["ring_n"] * 0.02))
    ndc = world_to_camera_view(sc, cop, cpt); cx, cy = ndc.x * 605, (1 - ndc.y) * 908
    ppm = 908 * 85 / (24 * (cpt - cop.location).length)
    out = {}
    for which in ("coarse", "fine"):
        p = os.path.join(W, "preview_%s_jinp_%s.png" % (tag, which))
        if not os.path.exists(p): continue
        im = bpy.data.images.load(p); w_, h_ = im.size; px = np.empty(w_ * h_ * 4, np.float32); im.pixels.foreach_get(px)
        px = px.reshape(h_, w_, 4)[::-1].astype(np.float64); bpy.data.images.remove(im)
        lum = (px[..., 0] * 0.2126 + px[..., 1] * 0.7152 + px[..., 2] * 0.0722) * 255
        r = FS.fan_score(lum, px[..., 3] > 0.5, cx, cy, ppm)
        out[which] = {k: (v["cross_-50_10"], v["fan_15_120"], round(v["fan_spread_deg"])) for k, v in r.items()}
    print("RESCORE", tag, [round(cx), round(cy)], json.dumps(out))
