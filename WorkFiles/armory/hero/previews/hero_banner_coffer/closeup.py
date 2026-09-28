"""Close-up / underside renders for hero_banner_coffer (the standard preview only looks from the front/side/top).
blender -b --factory-startup --python closeup.py -- --pieces "H:SM_AK_Banner@0,0,0;S:SM_AK_Ceiling_Beam_4@0,2,0" \
    --cams "name|ortho|scale|lx,ly,lz|tx,ty,tz;name|persp|lens|lx,ly,lz|tx,ty,tz" --out <dir> --label x [--samples 32]
       [--light below|front]
H: = hero piece, S: = scripted piece. Writes <out>/<label>_<cam>.png."""
import math
import os
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

A = sys.argv[sys.argv.index("--") + 1:]


def arg(n, d=None):
    return A[A.index(n) + 1] if n in A else d


os.environ["ARMORY_HERO_ONLY"] = "hero_banner_coffer"
ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
sys.path.insert(0, str(ROOT / "Scripts" / "armory"))
bpy.ops.wm.read_factory_settings(use_empty=True)
import build_armory_kit as K  # noqa: E402

OUT = Path(arg("--out"))
LABEL = arg("--label", "closeup")
sc = bpy.context.scene
for name in K.MATERIALS:
    K.build_material(name)
hero = {p.name: p for m in K.HERO.MODULES for p in m.pieces(K.HERO.G)}
scripted = None
coll = bpy.data.collections.new("C")
sc.collection.children.link(coll)
for item in arg("--pieces").split(";"):
    src, _, rest = item.partition(":")
    name, _, at = rest.partition("@")
    v = [float(t) for t in at.split(",")] if at else [0, 0, 0]
    if src == "S":
        if scripted is None:
            scripted = {p.name: p for p in K.kit()}
        p = scripted[name]
    else:
        p = hero[name]
    o = p.build(coll)
    o.matrix_world = Matrix.Translation(Vector(v[:3])) @ Matrix.Rotation(math.radians(v[3] if len(v) > 3 else 0), 4, "Z")
    for ch in o.children:
        ch.hide_render = True

sc.render.engine = "CYCLES"
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "OPTIX"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = True
    sc.cycles.device = "GPU"
except Exception:
    pass
sc.cycles.samples = int(arg("--samples", "32"))
sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = [int(t) for t in arg("--res", "1024,768").split(",")]
sc.view_settings.view_transform = "AgX"
try:
    sc.view_settings.look = "AgX - Medium High Contrast"
except TypeError:
    pass
w = bpy.data.worlds.new("W")
sc.world = w
w.use_nodes = True
bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs["Color"].default_value = (0.20, 0.20, 0.20, 1)
bg.inputs["Strength"].default_value = float(arg("--world", "0.6"))
mode = arg("--light", "front")
for nm, loc, pw, size in ((("Key", (-2.5, -4, 3), 400, 2.5), ("Fill", (3, -3, 1.5), 150, 3), ("Rim", (0, 4, 3), 200, 2))
                          if mode == "front" else
                          (("Key", (-3, -2, -3), 500, 3), ("Fill", (4, 3, -2.5), 200, 3), ("Rim", (1, 5, -1), 150, 2))):
    ld = bpy.data.lights.new(nm, "AREA")
    ld.energy, ld.size = pw * float(arg("--power", "1")), size
    lo = bpy.data.objects.new(nm, ld)
    c = Vector([float(t) for t in arg("--lc", "0,0,1").split(",")])
    lo.location = c + Vector(loc)
    lo.rotation_euler = (c - lo.location).to_track_quat("-Z", "Y").to_euler()
    sc.collection.objects.link(lo)
for spec in arg("--cams").split(";"):
    nm, kind, val, loc, tgt = spec.split("|")
    cd = bpy.data.cameras.new(nm)
    cam = bpy.data.objects.new(nm, cd)
    sc.collection.objects.link(cam)
    cam.location = Vector([float(t) for t in loc.split(",")])
    t = Vector([float(t) for t in tgt.split(",")])
    d = t - cam.location
    up = "Y" if abs(d.normalized().z) < 0.99 else "Y"
    cam.rotation_euler = d.to_track_quat("-Z", up).to_euler()
    if abs(d.normalized().z) > 0.99:   # straight up/down: keep +Y up in the image
        cam.rotation_euler = (0, math.pi, 0) if d.z > 0 else (0, 0, 0)
        if d.z > 0:
            cam.rotation_euler = (math.pi, 0, 0)
    if kind == "ortho":
        cd.type = "ORTHO"
        cd.ortho_scale = float(val)
    else:
        cd.lens = float(val)
    cd.clip_end = 200
    sc.camera = cam
    sc.render.filepath = str(OUT / f"{LABEL}_{nm}.png")
    bpy.ops.render.render(write_still=True)
print("CLOSEUP done")

# optional: stitch four of the renders into one 2 x 2 sheet (like the user's reference sheets)
if arg("--sheet"):
    import numpy as np
    names = arg("--sheet").split(",")
    tiles = []
    for nm in names:
        im = bpy.data.images.load(str(OUT / f"{LABEL}_{nm}.png"))
        w_, h_ = im.size
        tiles.append(np.array(im.pixels[:], dtype=np.float32).reshape(h_, w_, 4))
        bpy.data.images.remove(im)
    top = np.concatenate([tiles[0], tiles[1]], axis=1)
    bot = np.concatenate([tiles[2], tiles[3]], axis=1)
    sheet = np.concatenate([bot, top], axis=0)
    h_, w_ = sheet.shape[:2]
    sheet[:, w_ // 2 - 1:w_ // 2 + 1, :3] = 0.55
    sheet[h_ // 2 - 1:h_ // 2 + 1, :, :3] = 0.55
    img = bpy.data.images.new("sheet", w_, h_, alpha=True)
    img.pixels.foreach_set(sheet.ravel())
    img.filepath_raw = str(OUT / f"{LABEL}_sheet.png")
    img.file_format = "PNG"
    img.save()
    print("SHEET", OUT / f"{LABEL}_sheet.png")
