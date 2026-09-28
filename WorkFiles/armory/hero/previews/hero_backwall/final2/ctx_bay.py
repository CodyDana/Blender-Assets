"""Private check render: the hero rear bay + scripted context (header beam, north wall, ceiling beams) in a dark room lit
mostly by its own emissives, front ortho + an entrance-side perspective. Scratch only."""
import math
import os
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
OUT = Path(sys.argv[sys.argv.index("--") + 1])
SPEC = Path(sys.argv[sys.argv.index("--") + 2]).read_text().strip()
SAMPLES = int(sys.argv[sys.argv.index("--") + 3]) if len(sys.argv) > sys.argv.index("--") + 3 else 48
os.environ["ARMORY_HERO_ONLY"] = "hero_backwall"
sys.path.insert(0, str(ROOT / "Scripts" / "armory"))
bpy.ops.wm.read_factory_settings(use_empty=True)
import build_armory_kit as K  # noqa: E402

sc = bpy.context.scene
for name in K.MATERIALS:
    K.build_material(name)
hero = {p.name: p for m in K.HERO.MODULES for p in m.pieces(K.HERO.G)}
scripted = {p.name: p for p in K.kit() + K.EXT.kit()}
ctx = [("SM_AK_Ceiling_Beam_4", (4.0, 15.85, 4.35), 0), ("SM_AK_Ceiling_Rib_2", (4.0, 14.0, 4.8), 90), ("SM_AK_Ceiling_Rib_2", (6.0, 14.0, 4.8), 90), ("SM_AK_Ceiling_Rib_2", (8.0, 14.0, 4.8), 90), ("SM_AK_EmblemDisc_12", (6.0, 13.43, 0.508), 0), ("SM_AK_Ceiling_Beam_4", (0.0, 14.0, 4.8), 0),
       ("SM_AK_Ceiling_Beam_4", (4.0, 14.0, 4.8), 0), ("SM_AK_Ceiling_Beam_4", (8.0, 14.0, 4.8), 0)]
for x0 in range(0, 12, 2):
    ctx.append(("SM_AK_WallLower_2", (x0 + 2, 16.0, 0), 180))
    ctx.append(("SM_AK_WallUpper_Plain_2", (x0 + 2, 16.0, 2.5), 180))
    ctx.append(("SM_AK_Ceiling_Coffer_2x2", (x0, 14.0, 4.8), 0))
spec = []
for item in SPEC.split(";"):
    name, _, at = item.partition("@")
    v = [float(t) for t in at.split(",")]
    spec.append((name, (v[0], v[1], v[2]), v[3] if len(v) > 3 else 0.0))
coll = bpy.data.collections.new("C")
sc.collection.children.link(coll)
for name, loc, rz in spec:
    o = hero[name].build(coll)
    o.matrix_world = Matrix.Translation(loc) @ Matrix.Rotation(math.radians(rz), 4, "Z")
    for ch in o.children:
        ch.hide_render = True
for name, loc, rz in ctx:
    if name not in scripted:
        continue
    o = scripted[name].build(coll)
    o.matrix_world = Matrix.Translation(loc) @ Matrix.Rotation(math.radians(rz), 4, "Z")
    for ch in o.children:
        ch.hide_render = True
# floor
me = bpy.data.meshes.new("F")
me.from_pydata([(-2, 8, 0), (14, 8, 0), (14, 16, 0), (-2, 16, 0)], [], [(0, 1, 2, 3)])
fl = bpy.data.objects.new("F", me)
me.materials.append(bpy.data.materials["M_AK_Plank"])
sc.collection.objects.link(fl)
sc.render.engine = "CYCLES"
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "OPTIX"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = True
    sc.cycles.device = "GPU"
except Exception as e:  # noqa: BLE001
    print(e)
sc.cycles.samples = SAMPLES
sc.cycles.use_denoising = True
sc.view_settings.view_transform = "AgX"
sc.view_settings.look = "AgX - Medium High Contrast"
w = bpy.data.worlds.new("W")
sc.world = w
w.use_nodes = True
bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs["Color"].default_value = (0.02, 0.018, 0.015, 1)
bg.inputs["Strength"].default_value = 1.0
# a soft warm fill from the room side, like the reference's ambient
for nm, loc, en, sz in (("Fill", (6.0, 9.0, 3.2), 900, 6.0),):
    ld = bpy.data.lights.new(nm, "AREA")
    ld.energy, ld.size, ld.color = en, sz, (1.0, 0.85, 0.7)
    lo = bpy.data.objects.new(nm, ld)
    lo.location = loc
    lo.rotation_euler = (Vector((6.0, 15.5, 2.0)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    sc.collection.objects.link(lo)
# downlight spots under the canopy lights
for x in (4.425, 5.425, 6.575, 7.575):
    ld = bpy.data.lights.new("S", "SPOT")
    ld.energy, ld.spot_size, ld.color, ld.shadow_soft_size = 60, math.radians(70), (1.0, 0.75, 0.5), 0.05
    lo = bpy.data.objects.new("S", ld)
    lo.location = (x, 15.41, 4.00)
    sc.collection.objects.link(lo)


def shot(name, loc, target, ortho=None, lens=35, res=(1400, 900)):
    cd = bpy.data.cameras.new(name)
    cam = bpy.data.objects.new(name, cd)
    sc.collection.objects.link(cam)
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    else:
        cd.lens = lens
    cd.clip_end = 100
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.filepath = str(OUT / f"{name}.png")
    bpy.ops.render.render(write_still=True)


shot("ctx_front", (6.0, 5.0, 2.4), (6.0, 16.0, 2.4), ortho=6.4)
shot("ctx_persp", (4.2, 9.5, 1.7), (6.0, 15.5, 1.6), lens=30)
