"""From-below review renders for hero_ceiling_lattice (preview_hero.py's sheet looks from above / the side only).
Run: blender -b --factory-startup --python below.py -- --out <dir> --label <l> [--samples 32] [--scripted] [--context]
Sheet: bottom ortho (big) | side from slightly below | 3/4 from below | corner close-up. --context puts the panel in
its place in the coffer grid (neighbouring coffers, beams, ribs, as layout() does) and renders a room-eye view.
"""
import math
import os
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(n, d=None):
    return ARGS[ARGS.index(n) + 1] if n in ARGS else d


os.environ["ARMORY_HERO_ONLY"] = "hero_ceiling_lattice"
ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
sys.path.insert(0, str(ROOT / "Scripts" / "armory"))
bpy.ops.wm.read_factory_settings(use_empty=True)
import build_armory_kit as K  # noqa: E402

OUT = Path(arg("--out"))
LABEL = arg("--label", "below")
W, H = 900, 600


def studio(sc):
    sc.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        sc.cycles.device = "GPU"
    except Exception as e:  # noqa: BLE001
        print("GPU unavailable:", e)
    sc.cycles.samples = int(arg("--samples", "32"))
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    w = bpy.data.worlds.new("Studio")
    sc.world = w
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.20, 0.20, 0.20, 1)
    bg.inputs["Strength"].default_value = 0.6


def light(name, loc, target, power, size, color=(1.0, 0.93, 0.84)):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy, ld.size, ld.color = power, size, color
    o = bpy.data.objects.new(name, ld)
    o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(o)


def cam(loc, target, ortho=None, lens=50, up="Y"):
    cd = bpy.data.cameras.new("cam")
    o = bpy.data.objects.new("cam", cd)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", up).to_euler()
    cd.clip_end = 200
    if ortho:
        cd.type, cd.ortho_scale = "ORTHO", ortho
    else:
        cd.lens = lens
    return o


def shot(o, tag):
    sc = bpy.context.scene
    sc.camera = o
    p = OUT / f"_{LABEL}_{tag}.png"
    sc.render.filepath = str(p)
    bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(str(p))
    px = np.array(im.pixels[:], dtype=np.float32).reshape(H, W, 4)
    bpy.data.images.remove(im)
    p.unlink()
    return px


def save(tiles, name):
    top = np.concatenate([tiles[0], tiles[1]], axis=1)
    bot = np.concatenate([tiles[2], tiles[3]], axis=1)
    sheet = np.concatenate([bot, top], axis=0)
    sheet[:, W - 1:W + 1, :3] = 0.55
    sheet[H - 1:H + 1, :, :3] = 0.55
    img = bpy.data.images.new("sheet", 2 * W, 2 * H, alpha=True)
    img.pixels.foreach_set(sheet.ravel())
    img.filepath_raw = str(OUT / name)
    img.file_format = "PNG"
    img.save()


def main():
    sc = bpy.context.scene
    for n in K.MATERIALS:
        K.build_material(n)
    studio(sc)
    coll = bpy.data.collections.new("P")
    sc.collection.children.link(coll)
    if "--scripted" in ARGS:
        src = {p.name: p for p in K.kit()}
    else:
        src = {p.name: p for m in K.HERO.MODULES for p in m.pieces(K.HERO.G)}
    if "--context" in ARGS:
        kit = {p.name: p for p in K.kit()}
        kit.update(src)
        Z = K.CEIL
        objs = []
        for (name, (x, y, z), r) in K.layout()[0]:
            if not name.startswith("SM_AK_Ceiling") or not (2 <= x <= 8.5 and 10 <= y <= 16.5):
                continue
            o = kit[name].build(coll)
            o.matrix_world = Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(r), 4, "Z")
            for ch in o.children:
                ch.hide_render = True
            objs.append(o)
        # warm room bounce from below and a few downlights
        light("Bounce", (6, 13, 0.5), (6, 13, 5), 500, 8)
        light("Key", (3, 9, 1.5), (5, 13, 5), 150, 3)
        tiles = [shot(cam((6.0, 8.0, 1.7), (5.5, 14.5, 4.6), lens=24), "ctx_a"),
                 shot(cam((5.0, 13.0, 0.5), (5.0, 13.0, 5), ortho=6.2), "ctx_b"),
                 shot(cam((3.0, 10.5, 1.7), (5.2, 13.5, 4.7), lens=35), "ctx_c"),
                 shot(cam((6.5, 16.5, 1.7), (5.0, 12.8, 4.7), lens=28, up="Y"), "ctx_d")]
        save(tiles, f"{LABEL}_context.png")
        return
    o = src["SM_AK_Ceiling_Lattice_2x2"].build(coll)
    for ch in o.children:
        ch.hide_render = True
    o.location = (-1, -1, 0)
    light("KeyB", (-3.5, -3.0, -2.0), (0, 0, 0), 520, 2)
    light("FillB", (3.0, -2.0, -2.5), (0, 0, 0), 150, 3)
    light("Under", (0, 0, -4.0), (0, 0, 0), 90, 3)
    if "--closeups" in ARGS:
        tiles = [shot(cam((-0.55, -3.0, -0.25), (-0.80, -1.0, 0.03), lens=85, up="Z"), "c_side"),
                 shot(cam((0.4, -2.2, -1.1), (-0.75, -0.75, 0.0), lens=60, up="Z"), "c_34"),
                 shot(cam((0.2, -1.6, -0.9), (0.0, -0.3, -0.02), lens=50, up="Z"), "c_latt"),
                 shot(cam((-0.3, -1.6, -0.35), (-0.3, -0.8, -0.02), lens=70, up="Z"), "c_slot")]
        save(tiles, f"{LABEL}_close.png")
        return
    tiles = [shot(cam((0, 0, -10), (0, 0, 0), ortho=3.25), "bottom"),
             shot(cam((0, -9.0, -1.4), (0, 0, -0.02), lens=85, up="Z"), "side"),
             shot(cam((4.2, -3.9, -3.4), (0, 0, 0), lens=50, up="Z"), "persp"),
             shot(cam((-0.70, -0.70, -1.2), (-0.70, -0.70, 0), ortho=0.8), "corner")]
    save(tiles, f"{LABEL}_below.png")


main()
