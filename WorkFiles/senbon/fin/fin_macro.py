"""Finalise look check: macro renders of the heavy wrap and point from a built Senbon.blend (its packed, shipped
maps).  blender -b <Senbon.blend> --factory-startup --python fin_macro.py -- <out_prefix>
Read-only on the blend (never saved)."""
import math
import sys

import bpy
from mathutils import Vector

out = sys.argv[sys.argv.index("--") + 1]
texdir = sys.argv[sys.argv.index("--") + 2]
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
sc.cycles.samples = 96
sc.render.resolution_x, sc.render.resolution_y = 1200, 800
sc.view_settings.view_transform = "AgX" if "AgX" in [i.identifier for i in sc.view_settings.bl_rna.properties["view_transform"].enum_items] else sc.view_settings.view_transform
for o in list(bpy.data.objects):
    if o.type in ("CAMERA", "LIGHT"):
        bpy.data.objects.remove(o, do_unlink=True)
H = bpy.data.objects["SM_Senbon_Heavy_LOD0"]
for o in bpy.data.objects:
    o.hide_render = o is not H
w = bpy.data.worlds.new("W") if sc.world is None else sc.world
sc.world = w
w.use_nodes = True
bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs["Color"].default_value = (0.18, 0.18, 0.19, 1)
bg.inputs["Strength"].default_value = 1.0


def light(name, loc, energy, size):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy = energy
    ld.size = size
    lo = bpy.data.objects.new(name, ld)
    sc.collection.objects.link(lo)
    lo.location = loc
    d = Vector((0, 0, 0)) - Vector(loc)
    lo.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return lo




def shipped(mat, stem):
    nt = mat.node_tree
    nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bs.outputs["BSDF"], o.inputs["Surface"])

    def img(suf, data):
        im = bpy.data.images.load(f"{texdir}/{stem}_{suf}.png")
        im.colorspace_settings.name = "Non-Color" if data else "sRGB"
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = im
        n.extension = "REPEAT"
        return n
    bc, orm, nn = img("BC", False), img("ORM", True), img("N", True)
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


for slot in H.material_slots:
    if slot.material and "Wrap" in slot.material.name:
        shipped(slot.material, "T_Senbon_Heavy_Wrap")
    elif slot.material:
        shipped(slot.material, "T_Senbon_Heavy")
cam_d = bpy.data.cameras.new("C")
cam = bpy.data.objects.new("C", cam_d)
sc.collection.objects.link(cam)
sc.camera = cam
cam_d.lens = 100
cam_d.clip_start = 0.001
com = None
# heavy wrap centre in object space: s 30 -> x = 30 - com; read com from the Trail socket (s 0)
bb = [H.matrix_world @ Vector(c) for c in H.bound_box]
s0 = min(v.x for v in bb)
print("FINMACRO heavy x range", s0, max(v.x for v in bb), "loc", H.matrix_world.translation, "hidden", H.hide_render, H.hide_get())
H.hide_set(False)
shots = {"wrap": (s0 + 0.030, 0.055), "wrapclose": (s0 + 0.020, 0.028), "point": (s0 + 0.160, 0.050)}
L = [light("K", (0.05, -0.08, 0.10), 0.35, 0.08), light("F", (-0.10, -0.05, 0.03), 0.08, 0.15),
     light("R", (0.0, 0.10, 0.05), 0.2, 0.05)]
for name, (x, dist) in shots.items():
    tgt = Vector((x, 0, 0))
    el, az = math.radians(25), math.radians(-70)
    cam.location = tgt + dist * Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
    cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
    for rot in (0, 1):
        H.rotation_euler = (math.radians(37 * rot), 0, 0)
        sc.render.filepath = f"{out}_{name}_{rot}.png"
        bpy.ops.render.render(write_still=True)
