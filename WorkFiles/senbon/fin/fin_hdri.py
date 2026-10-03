"""Finalise look gate: is the heavy's ground point (facets) at least as bright as the blackened body under real HDRIs?
blender -b <Senbon.blend> --factory-startup --python fin_hdri.py -- <texdir> <out_prefix>
Renders the heavy's point (LOD0, shipped maps) under 4 Blender studio-light HDRIs x 3 rolls, plus an emission mask
(ground = BC luminance > 0.25), and writes <out_prefix>.json: mean linear value of facet pixels vs coat pixels."""
import json
import math
import sys

import bpy
import numpy as np
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:]
texdir, out = a[0], a[1]
HD = "C:/Program Files/Blender Foundation/Blender 5.2/5.2/datafiles/studiolights/world"
sc = bpy.context.scene
sc.render.engine = "CYCLES"
try:
    pr = bpy.context.preferences.addons["cycles"].preferences
    pr.compute_device_type = "OPTIX"
    pr.get_devices()
    for d in pr.devices:
        d.use = d.type == "OPTIX"
    sc.cycles.device = "GPU"
except Exception:
    sc.cycles.device = "CPU"
sc.cycles.samples = 64
sc.render.resolution_x, sc.render.resolution_y = 600, 400
sc.render.film_transparent = True
sc.view_settings.view_transform = "Standard"
sc.render.image_settings.file_format = "OPEN_EXR"
for o in list(bpy.data.objects):
    if o.type in ("CAMERA", "LIGHT"):
        bpy.data.objects.remove(o, do_unlink=True)
H = bpy.data.objects["SM_Senbon_Heavy_LOD0"]
for o in bpy.data.objects:
    o.hide_render = o is not H


def tex_nodes(mat, stem, mask):
    nt = mat.node_tree
    nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial")

    def img(suf, data):
        im = bpy.data.images.load(f"{texdir}/{stem}_{suf}.png", check_existing=True)
        im.colorspace_settings.name = "Non-Color" if data else "sRGB"
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = im
        return n
    bc = img("BC", False)
    if mask:
        em = nt.nodes.new("ShaderNodeEmission")
        if "Wrap" in stem:
            em.inputs["Color"].default_value = (0, 0, 0, 1)
        else:
            gt = nt.nodes.new("ShaderNodeMath")
            gt.operation = "GREATER_THAN"
            gt.inputs[1].default_value = 0.25
            bw = nt.nodes.new("ShaderNodeRGBToBW")
            nt.links.new(bc.outputs["Color"], bw.inputs["Color"])
            nt.links.new(bw.outputs["Val"], gt.inputs[0])
            nt.links.new(gt.outputs["Value"], em.inputs["Color"])
        nt.links.new(em.outputs["Emission"], o.inputs["Surface"])
        return
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bs.outputs["BSDF"], o.inputs["Surface"])
    orm, nn = img("ORM", True), img("N", True)
    nt.links.new(bc.outputs["Color"], bs.inputs["Base Color"])
    sp = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(orm.outputs["Color"], sp.inputs["Color"])
    nt.links.new(sp.outputs["Green"], bs.inputs["Roughness"])
    nt.links.new(sp.outputs["Blue"], bs.inputs["Metallic"])
    sn = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(nn.outputs["Color"], sn.inputs["Color"])
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    nt.links.new(sn.outputs["Green"], inv.inputs[1])
    cm = nt.nodes.new("ShaderNodeCombineColor")
    nt.links.new(sn.outputs["Red"], cm.inputs["Red"])
    nt.links.new(inv.outputs["Value"], cm.inputs["Green"])
    nt.links.new(sn.outputs["Blue"], cm.inputs["Blue"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.uv_map = "UVMap"
    nt.links.new(cm.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bs.inputs["Normal"])


def set_mats(mask):
    for slot in H.material_slots:
        if slot.material:
            tex_nodes(slot.material, "T_Senbon_Heavy_Wrap" if "Wrap" in slot.material.name else "T_Senbon_Heavy", mask)


w = bpy.data.worlds.new("WH")
sc.world = w
w.use_nodes = True
wnt = w.node_tree
bgn = next(n for n in wnt.nodes if n.type == "BACKGROUND")
env = wnt.nodes.new("ShaderNodeTexEnvironment")
wnt.links.new(env.outputs["Color"], bgn.inputs["Color"])
cam_d = bpy.data.cameras.new("C")
cam_d.lens = 85
cam_d.clip_start = 0.001
cam = bpy.data.objects.new("C", cam_d)
sc.collection.objects.link(cam)
sc.camera = cam
bb = [H.matrix_world @ Vector(c) for c in H.bound_box]
x1 = max(v.x for v in bb)
tgt = Vector((x1 - 0.016, 0, 0))
el, az = math.radians(30), math.radians(-65)
cam.location = tgt + 0.07 * Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()


def render(path):
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(path)
    W, Hh = im.size
    px = np.array(im.pixels[:], np.float32).reshape(Hh, W, 4)
    bpy.data.images.remove(im)
    return px


res = {}
for roll in (0, 120, 240):
    H.rotation_euler = (math.radians(roll), 0, 0)
    set_mats(True)
    w.node_tree.nodes  # keep
    bgn.inputs["Strength"].default_value = 0.0
    m = render(f"{out}_mask_{roll}.exr")
    ground = (m[..., 0] > 0.5) & (m[..., 3] > 0.99)
    coat = (m[..., 0] < 0.05) & (m[..., 3] > 0.99)
    set_mats(False)
    bgn.inputs["Strength"].default_value = 1.0
    for hd in ("courtyard", "studio", "interior", "sunset"):
        env.image = bpy.data.images.load(f"{HD}/{hd}.exr", check_existing=True)
        b = render(f"{out}_{hd}_{roll}.exr")
        lum = b[..., :3] @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        g, c = float(lum[ground].mean()), float(lum[coat].mean())
        res[f"{hd}_{roll}"] = {"ground_mean": round(g, 4), "coat_mean": round(c, 4), "ratio": round(g / max(c, 1e-6), 3),
                               "ground_px": int(ground.sum()), "coat_px": int(coat.sum())}
res["min_ratio"] = min(v["ratio"] for v in res.values() if isinstance(v, dict))
res["pass_ground_ge_coat_everywhere"] = res["min_ratio"] >= 1.0
open(out + ".json", "w").write(json.dumps(res, indent=1))
print("FINHDRI", json.dumps(res))
