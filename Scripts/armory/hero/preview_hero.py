"""Develop one hero module in isolation: build its pieces (and optionally the scripted pieces they replace) with the
kit's own materials and Piece builder, run the pipeline QA on them, and render a 2 x 2 reference-style sheet (front,
side, top orthographic + one 3/4 perspective on a mid-grey studio background), like the user's reference sheets in
WorkFiles/armory/reference/<name>.png. Never touches ArmoryKit.blend, layout.json or the exports.

Run (Git Bash):
  "/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
      --python Scripts/armory/hero/preview_hero.py -- --module hero_cases \
      --pieces "SM_AK_Case_L_Plinth;SM_AK_Case_L_Glass@0,0,0.50" --front -y --label case_L --out <abs dir> \
      [--scripted] [--samples 48] [--save]

--pieces   ';'-separated piece names, each optionally placed with @x,y,z (m) and @x,y,z,rz (deg), so a plinth and its
           glass hood can be shown stacked as one case
--front    the direction the assembly's front faces: -y (default), +y, -x or +x
--scripted also render the scripted versions of the same pieces at the same placements and framing (<label>_scripted.png)
--save     save the hero objects to Assets/Armory/Hero/<module>.blend (for the user to open)
Writes <out>/<label>_hero.png, [<label>_scripted.png], <label>.json (bbox per piece, hero vs scripted, tris, QA).
"""
import json
import math
import os
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default=None):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


MODULE = arg("--module")
assert MODULE, "--module hero_<group> is required"
os.environ["ARMORY_HERO_ONLY"] = MODULE
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Scripts" / "armory"))
bpy.ops.wm.read_factory_settings(use_empty=True)
import build_armory_kit as K  # noqa: E402   (main() does not run on import)

OUT = Path(arg("--out", str(ROOT / "WorkFiles" / "armory" / "hero" / "previews")))
OUT.mkdir(parents=True, exist_ok=True)
LABEL = arg("--label", MODULE)
FRONT = {"-y": Vector((0, -1, 0)), "+y": Vector((0, 1, 0)), "-x": Vector((-1, 0, 0)),
         "+x": Vector((1, 0, 0))}[arg("--front", "-y")]
UP = Vector((0, 0, 1))
RIGHT = UP.cross(FRONT)    # the viewer's right when facing the front
TILE_W, TILE_H = 768, 512


def parse_pieces(spec):
    out = []
    for item in spec.split(";"):
        name, _, at = item.partition("@")
        v = [float(t) for t in at.split(",")] if at else [0, 0, 0]
        out.append((name.strip(), Vector(v[:3]), v[3] if len(v) > 3 else 0.0))
    return out


def world_bbox(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    return lo, hi


def studio(sc):
    sc.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        sc.cycles.device = "GPU"
    except Exception as e:   # noqa: BLE001  CPU fallback
        print("GPU unavailable:", e)
    sc.cycles.samples = int(arg("--samples", "48"))
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = TILE_W, TILE_H
    sc.render.film_transparent = False
    try:
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    w = bpy.data.worlds.new("Studio")
    sc.world = w
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.20, 0.20, 0.20, 1)
    bg.inputs["Strength"].default_value = 0.6


def add_floor_and_lights(lo, hi):
    size = max((hi - lo).length * 6, 8)
    me = bpy.data.meshes.new("StudioFloor")
    s = size / 2
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    fl = bpy.data.objects.new("StudioFloor", me)
    m = bpy.data.materials.new("StudioGrey")
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (0.20, 0.20, 0.20, 1)
    b.inputs["Roughness"].default_value = 0.9
    me.materials.append(m)
    c = (lo + hi) / 2
    fl.location = (c.x, c.y, lo.z - 0.0005)
    bpy.context.scene.collection.objects.link(fl)
    ext = max((hi - lo).length, 0.5)
    for name, d, power, size_k in (("Key", FRONT * 1.0 - RIGHT * 0.8 + UP * 1.2, 90, 0.8),
                                   ("Fill", FRONT * 1.0 + RIGHT * 1.0 + UP * 0.4, 30, 1.0),
                                   ("Rim", -FRONT * 1.0 + UP * 1.0, 40, 0.6)):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy = power * ext * ext
        ld.size = ext * size_k
        lo_ = bpy.data.objects.new(name, ld)
        lo_.location = c + d.normalized() * ext * 2.2
        lo_.rotation_euler = (c - lo_.location).to_track_quat("-Z", "Y").to_euler()
        bpy.context.scene.collection.objects.link(lo_)


def camera(name, lo, hi, kind):
    c = (lo + hi) / 2
    ext = hi - lo
    cd = bpy.data.cameras.new(name)
    cam = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(cam)
    dist = ext.length * 3 + 2
    cd.clip_end = dist * 4

    def span(axis):
        return abs(ext.dot(axis))
    if kind == "top":
        cd.type = "ORTHO"
        cam.location = c + UP * dist
        back = -FRONT
        cam.rotation_euler = (0, 0, math.atan2(-back.x, back.y))
        w, h = span(RIGHT), span(FRONT)
    elif kind in ("front", "side"):
        cd.type = "ORTHO"
        view = FRONT if kind == "front" else RIGHT
        cam.location = c + view * dist
        cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
        w, h = span(RIGHT if kind == "front" else FRONT), ext.z
    else:
        cd.type = "PERSP"
        cd.lens = 50
        d = (FRONT + RIGHT * 0.9 + UP * 0.55).normalized()
        fit = ext.length * 1.5
        cam.location = c + d * (fit / (2 * math.tan(cd.angle / 2)))
        cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
        return cam
    cd.ortho_scale = max(w, h * TILE_W / TILE_H) * 1.15
    return cam


def render_sheet(objs, path):
    sc = bpy.context.scene
    lo, hi = world_bbox(objs)
    tiles = []
    for kind in ("front", "side", "top", "persp"):
        cam = camera(f"CAM_{kind}", lo, hi, kind)
        sc.camera = cam
        tmp = OUT / f"_{LABEL}_{kind}.png"
        sc.render.filepath = str(tmp)
        bpy.ops.render.render(write_still=True)
        im = bpy.data.images.load(str(tmp))
        px = np.array(im.pixels[:], dtype=np.float32).reshape(TILE_H, TILE_W, 4)
        tiles.append(px)
        bpy.data.images.remove(im)
        tmp.unlink()
        bpy.data.objects.remove(cam, do_unlink=True)
    # Blender pixel rows run bottom-up: the top row of the sheet is (front, side), the bottom row (top, 3/4)
    top = np.concatenate([tiles[0], tiles[1]], axis=1)
    bot = np.concatenate([tiles[2], tiles[3]], axis=1)
    sheet = np.concatenate([bot, top], axis=0)
    sheet[:, TILE_W - 1:TILE_W + 1, :3] = 0.55
    sheet[TILE_H - 1:TILE_H + 1, :, :3] = 0.55
    img = bpy.data.images.new("sheet", 2 * TILE_W, 2 * TILE_H, alpha=True)
    img.pixels.foreach_set(sheet.ravel())
    img.filepath_raw = str(path)
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def place(pieces_by_name, spec, coll):
    objs, report = [], {}
    for name, loc, rz in spec:
        p = pieces_by_name.get(name)
        if p is None:
            report[name] = "missing"
            continue
        o = p.build(coll)
        o.matrix_world = Matrix.Translation(loc) @ Matrix.Rotation(math.radians(rz), 4, "Z")
        for ch in o.children:
            ch.hide_set(True)
            ch.hide_render = True
        bpy.context.view_layer.update()
        me = o.data
        vs = [Vector(v.co) for v in me.vertices]
        report[name] = {"local_bbox_min": [round(min(v[i] for v in vs), 4) for i in range(3)],
                        "local_bbox_max": [round(max(v[i] for v in vs), 4) for i in range(3)],
                        "tris": sum(len(f.vertices) - 2 for f in me.polygons),
                        "materials": [m.name for m in me.materials if m]}
        objs.append(o)
    return objs, report


def main():
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    for name in K.MATERIALS:
        K.build_material(name)
    spec = parse_pieces(arg("--pieces"))
    hero = {p.name: p for m in K.HERO.MODULES for p in m.pieces(K.HERO.G)}
    result = {"module": MODULE, "label": LABEL, "front": arg("--front", "-y"), "pieces": {}}
    hc = bpy.data.collections.new("Hero")
    sc.collection.children.link(hc)
    hobjs, hrep = place(hero, spec, hc)
    waive = {"uv0_tile_range", "uv_no_overlap"}
    for o, (name, _l, _r) in zip(hobjs, [s for s in spec if s[0] in hero]):
        r = K.qa_check([o], require_uv1=True)
        hard = [{"name": c["name"], "detail": str(c["detail"])[:300]} for c in r["checks"]
                if not c["passed"] and c["name"] not in waive]
        hrep[name]["qa_hard_fails"] = hard
    result["pieces"]["hero"] = hrep
    studio(sc)
    add_floor_and_lights(*world_bbox(hobjs))
    if "--scripted" in ARGS:
        scripted = {p.name: p for p in K.kit() + K.EXT.kit() + [K.ITEMS.tray_piece()]}
        scc = bpy.data.collections.new("Scripted")
        sc.collection.children.link(scc)
        sobjs, srep = place(scripted, spec, scc)
        result["pieces"]["scripted"] = srep
        for o in hobjs:
            o.hide_render = True
        render_sheet(sobjs, OUT / f"{LABEL}_scripted.png")
        for o in sobjs:
            o.hide_render = True
        for o in hobjs:
            o.hide_render = False
    render_sheet(hobjs, OUT / f"{LABEL}_hero.png")
    if "--save" in ARGS:
        blend = ROOT / "Assets" / "Armory" / "Hero" / f"{MODULE}.blend"
        blend.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        result["saved"] = str(blend)
    (OUT / f"{LABEL}.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    print("PREVIEW", json.dumps(result))


main()
