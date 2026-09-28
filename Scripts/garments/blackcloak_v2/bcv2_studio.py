"""Calibrated product-shot studio for BlackCloak v2 renders (Blender 5.2, Cycles).

The rig and the calibration are the male cloak review's (WorkFiles/BlackCloak_Review/male/blender/scripts/render_view.py,
read-only, copied): white world (strength 4), a 3x3 m key front-left, a 3x3 m fill front-right, a 2.5 m top light,
a shadow-catcher floor, then every light and the world are scaled so that a white Lambertian card (base 1, roughness 1,
specular 0) facing the camera at the subject centre reads 0.90 LINEAR.  View transform Standard, look None,
exposure 0, gamma 1 (AgX/Filmic would lift the blacks and change the garment median).

    import bcv2_studio as ST
    info = ST.studio(scene, cam, centre=(0, 0, 1.0), yaw_deg=0.0)   # after the camera is placed
"""
import math
import os
import tempfile
import bpy
import bmesh
import numpy as np
from mathutils import Vector


def s2l(x):
    x = np.asarray(x, np.float64)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def cycles_gpu(scene):
    scene.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = (d.type == "OPTIX")
        scene.cycles.device = "GPU"
        return "OPTIX"
    except Exception as e:  # noqa: BLE001
        return "CPU (%s)" % e


def studio(scene, cam, centre=(0.0, 0.0, 1.0), yaw_deg=0.0, floor_z=0.0, amb=4.0, card_offset=(0.0, -0.3, 0.25),
           card_size=0.3, cal_samples=64):
    info = {"device": cycles_gpu(scene)}
    c = Vector(centre)
    floor_me = bpy.data.meshes.new("ST_Floor")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=6)
    bm.to_mesh(floor_me)
    bm.free()
    floor = bpy.data.objects.new("ST_Floor", floor_me)
    scene.collection.objects.link(floor)
    floor.location = (0, 0, floor_z)
    floor.is_shadow_catcher = True
    w = bpy.data.worlds.new("ST_World")
    scene.world = w
    try:
        w.use_nodes = True
    except Exception:
        pass
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (1, 1, 1, 1)
    bg.inputs[1].default_value = amb
    lights = []
    yr = math.radians(yaw_deg)

    def rot(v):
        return Vector((v.x * math.cos(yr) - v.y * math.sin(yr), v.x * math.sin(yr) + v.y * math.cos(yr), v.z))

    def area(name, loc, size, power, aim):
        l = bpy.data.lights.new(name, "AREA")
        l.shape = "RECTANGLE"
        l.size = size[0]
        l.size_y = size[1]
        l.energy = power
        o = bpy.data.objects.new(name, l)
        scene.collection.objects.link(o)
        o.location = loc
        o.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        lights.append(o)
        return o
    area("ST_Key", c + rot(Vector((-1.6, -3.0, 1.4))), (3.0, 3.0), 1000, c)
    area("ST_Fill", c + rot(Vector((1.9, -2.8, 0.5))), (3.0, 3.0), 350, c)
    area("ST_Top", c + Vector((0, 0, 3.0)), (2.5, 2.5), 400, Vector((c.x, c.y, 0)))
    vs = scene.view_settings
    vs.view_transform = "Standard"
    vs.look = "None"
    vs.exposure = 0.0
    vs.gamma = 1.0
    scene.render.film_transparent = True
    # ---- calibration card
    hidden = {}
    for o in scene.objects:
        if o.type == "MESH":
            hidden[o.name] = o.hide_render
            o.hide_render = True
    me = bpy.data.meshes.new("ST_Card")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=card_size)
    bm.to_mesh(me)
    bm.free()
    card = bpy.data.objects.new("ST_Card", me)
    scene.collection.objects.link(card)
    cm = bpy.data.materials.new("ST_White")
    try:
        cm.use_nodes = True
    except Exception:
        pass
    cb = next(n for n in cm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    cb.inputs["Base Color"].default_value = (1, 1, 1, 1)
    cb.inputs["Roughness"].default_value = 1.0
    cb.inputs["Specular IOR Level"].default_value = 0.0
    card.data.materials.append(cm)
    card.location = c + rot(Vector(card_offset))
    card.rotation_euler = (cam.location - card.location).to_track_quat("Z", "Y").to_euler()
    rx, ry, rp = scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage
    samples = scene.cycles.samples
    fmt = (scene.render.image_settings.file_format, scene.render.image_settings.color_mode,
           scene.render.image_settings.color_depth)
    cam_prev = scene.camera
    scene.camera = cam
    # a dedicated calibration camera framing the card (works for any shot camera, macro or wide)
    ccam = bpy.data.objects.new("ST_CalCam", bpy.data.cameras.new("ST_CalCam"))
    scene.collection.objects.link(ccam)
    d = (cam.location - card.location).normalized()
    ccam.location = card.location + d * 1.0
    ccam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    ccam.data.type = "ORTHO"
    ccam.data.ortho_scale = card_size * 0.5
    scene.camera = ccam
    scene.render.resolution_x = scene.render.resolution_y = 16
    scene.render.resolution_percentage = 100
    scene.cycles.samples = cal_samples
    scene.render.image_settings.file_format = "OPEN_EXR"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "32"
    tmp = os.path.join(tempfile.gettempdir(), "bcv2_cal_%d.exr" % os.getpid())
    scene.render.filepath = tmp

    def read():
        bpy.ops.render.render(write_still=True)
        im = bpy.data.images.load(tmp, check_existing=False)
        a = np.empty(16 * 16 * 4, np.float32)
        im.pixels.foreach_get(a)
        bpy.data.images.remove(im)
        os.remove(tmp)
        return float(a.reshape(16, 16, 4)[4:12, 4:12, :3].mean())      # EXR = scene-linear
    cal = read()
    k = 0.90 / max(cal, 1e-6)
    for o in lights:
        o.data.energy *= k
    bg.inputs[1].default_value = amb * k
    after = read()
    info["calibration"] = {"white_card_linear_before": cal, "white_card_linear_after": after, "scale": k,
                           "target_linear": 0.90,
                           "energies_W": {o.name: o.data.energy for o in lights}, "world_strength": amb * k,
                           "view_transform": "Standard", "look": "None", "exposure": 0.0}
    bpy.data.objects.remove(card, do_unlink=True)
    bpy.data.objects.remove(ccam, do_unlink=True)
    for n, h in hidden.items():
        bpy.data.objects[n].hide_render = h
    scene.camera = cam_prev or cam
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = rx, ry, rp
    scene.cycles.samples = samples
    (scene.render.image_settings.file_format, scene.render.image_settings.color_mode,
     scene.render.image_settings.color_depth) = fmt
    info["floor"] = floor.name
    info["lights"] = [o.name for o in lights]
    return info

