"""Pilot rock renders (study 6.4): headless Cycles, denoised. Modes:

  clay    grey clay, studio light, front / side / top orthographic + a 3/4 perspective (form check)
  sil     silhouettes (alpha) for SG15 IoU: ortho front / side at elevations 0-15 deg, top at 90 and oblique
  sheet   the sheet layout per rock (main + top + side + the 1.8 m figure, light-grey studio), final materials
  close   close-ups matching the sheet's: grain, fracture edge, moss, wet-to-dry line, lichen
  river   the sunset riverbank test (stand-in stream bed, the dojo's low western sun)

    blender -b --factory-startup --python Scripts/dojo/rocks/rocks_render.py -- <mode> [rocks...] [--src dense|blend]

Sources: --src dense loads WorkFiles/dojo/build/rocks/work/<Rock>_dense.npz (form stage); --src blend appends the
shipped SM_DKR_* objects (with their materials) from Assets/Dojo/DojoRocks.blend.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
for p in (ROOT / "Scripts" / "stone", ROOT / "Scripts" / "dojo" / "rocks", ROOT / "Scripts"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import bpy  # noqa: E402
from mathutils import Vector, Euler  # noqa: E402

from rocks_plans import PLANS  # noqa: E402

BUILD = ROOT / "WorkFiles" / "dojo" / "build" / "rocks"
WORK = BUILD / "work"
PILOT = BUILD / "pilot"
BLEND = ROOT / "Assets" / "Dojo" / "DojoRocks.blend"
BG_SRGB = 186 / 255.0


def log(*a):
    print("[render]", *a, flush=True)


# ----------------------------------------------------------------------------------------------- scene
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    try:
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        sc.cycles.device = "GPU"
    except Exception as e:  # noqa: BLE001
        log("GPU unavailable, CPU:", e)
    sc.cycles.samples = 128
    sc.cycles.use_denoising = True
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.film_transparent = True
    sc.world = bpy.data.worlds.new("W")
    sc.world.use_nodes = True
    return sc


def world_colour(rgb, strength=1.0):
    w = bpy.context.scene.world
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (*rgb, 1.0)
    bg.inputs[1].default_value = strength


def area_light(name, loc, target, size, energy, colour=(1, 1, 1)):
    ld = bpy.data.lights.new(name, "AREA")
    ld.size = size
    ld.energy = energy
    ld.color = colour
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


def sun(name, elev_deg, azim_deg, strength, colour=(1, 1, 1), angle_deg=1.0):
    ld = bpy.data.lights.new(name, "SUN")
    ld.energy = strength
    ld.color = colour
    ld.angle = math.radians(angle_deg)
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    # the sun shines FROM azimuth (0 = +y, 90 = +x) at elevation
    az, el = math.radians(azim_deg), math.radians(elev_deg)
    d = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))
    ob.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    return ob


def studio(key=320.0):
    """Light-grey sheet studio: soft key from the front-left above, fill from the right, a top light, a dim grey
    world. The floor is a shadow catcher; the grey backdrop is composited afterwards (film transparent)."""
    # the sheet's rocks show strong form shading (lit upper left, dark lower and right sides): a dominant key,
    # weak fill (round 2's 0.30 fill + 0.55 world flattened the forms; the sheet's figure is an unshaded
    # silhouette, so it is no lighting cue)
    world_colour((0.55, 0.55, 0.56), 0.32)
    area_light("Key", (-4.5, -6.0, 6.5), (0, 0, 0.8), 3.0, key * 1.25)
    area_light("Fill", (6.0, -4.0, 2.5), (0, 0, 0.8), 5.0, key * 0.15)
    area_light("Top", (0.5, 1.0, 8.0), (0, 0, 0.5), 6.0, key * 0.22)
    floor = bpy.data.objects.new("Floor", bpy.data.meshes.new("Floor"))
    s = 40.0
    floor.data.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    bpy.context.scene.collection.objects.link(floor)
    floor.is_shadow_catcher = True
    return floor


def holdout_ground():
    """A holdout box under grade: the buried skirt never shows in silhouettes."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, -5.0))
    ob = bpy.context.active_object
    ob.scale = (200, 200, 10.0)
    ob.name = "HoldoutGround"
    m = bpy.data.materials.new("Holdout")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    h = nt.nodes.new("ShaderNodeHoldout")
    nt.links.new(h.outputs[0], out.inputs["Surface"])
    ob.data.materials.append(m)
    return ob


def clay_material(v=0.42):
    m = bpy.data.materials.new("Clay")
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (v, v, v, 1)
    b.inputs["Roughness"].default_value = 0.75
    return m


def mesh_from_npz(name, path):
    d = np.load(path, allow_pickle=True)
    V, F = d["V"].astype(float), d["F"].astype(np.int64)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(V))
    me.vertices.foreach_set("co", V.ravel())
    me.loops.add(F.size)
    me.loops.foreach_set("vertex_index", F.ravel())
    me.polygons.add(len(F))
    me.polygons.foreach_set("loop_start", np.arange(0, F.size, 3))
    me.update()
    me.validate()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def append_from_blend(names):
    with bpy.data.libraries.load(str(BLEND), link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n in names or any(n.startswith(x + "_") for x in names)]
    out = {}
    for ob in dst.objects:
        if ob is None:
            continue
        bpy.context.scene.collection.objects.link(ob)
        if ob.name.startswith("UCX_"):
            ob.hide_render = True
        out[ob.name] = ob
    return out


def figure(x, y=0.0, h=1.8, colour=116 / 255.0):
    """The sheet's 1.8 m grey figure: a skin-modifier mannequin (stick skeleton + radii, subdivided)."""
    import bmesh
    s = h / 1.8
    pts = {"ft_l": (-0.10, 0.02, 0.06), "kn_l": (-0.10, 0.0, 0.50), "hp_l": (-0.09, 0.0, 0.90),
           "ft_r": (0.10, 0.02, 0.06), "kn_r": (0.10, 0.0, 0.50), "hp_r": (0.09, 0.0, 0.90),
           "pel": (0.0, 0.0, 0.96), "ch": (0.0, 0.0, 1.28), "nk": (0.0, 0.0, 1.50), "hd": (0.0, 0.0, 1.62),
           "hd2": (0.0, 0.0, 1.70), "sh_l": (-0.19, 0.0, 1.42), "el_l": (-0.24, 0.0, 1.13), "hn_l": (-0.26, 0.0, 0.86),
           "sh_r": (0.19, 0.0, 1.42), "el_r": (0.24, 0.0, 1.13), "hn_r": (0.26, 0.0, 0.86)}
    rad = {"ft_l": (0.05, 0.05), "kn_l": (0.055, 0.055), "hp_l": (0.075, 0.075), "ft_r": (0.05, 0.05),
           "kn_r": (0.055, 0.055), "hp_r": (0.075, 0.075), "pel": (0.15, 0.10), "ch": (0.17, 0.11),
           "nk": (0.05, 0.05), "hd": (0.095, 0.10), "hd2": (0.09, 0.095), "sh_l": (0.055, 0.055),
           "el_l": (0.045, 0.045), "hn_l": (0.04, 0.04), "sh_r": (0.055, 0.055), "el_r": (0.045, 0.045),
           "hn_r": (0.04, 0.04)}
    edges = [("ft_l", "kn_l"), ("kn_l", "hp_l"), ("hp_l", "pel"), ("ft_r", "kn_r"), ("kn_r", "hp_r"),
             ("hp_r", "pel"), ("pel", "ch"), ("ch", "nk"), ("nk", "hd"), ("hd", "hd2"), ("ch", "sh_l"),
             ("sh_l", "el_l"), ("el_l", "hn_l"), ("ch", "sh_r"), ("sh_r", "el_r"), ("el_r", "hn_r")]
    keys = list(pts)
    me = bpy.data.meshes.new("Figure")
    me.from_pydata([tuple(c * s for c in pts[k]) for k in keys], [(keys.index(a), keys.index(b)) for a, b in edges],
                   [])
    ob = bpy.data.objects.new("Figure", me)
    bpy.context.scene.collection.objects.link(ob)
    sk = ob.modifiers.new("skin", "SKIN")
    for i, k in enumerate(keys):
        me.skin_vertices[0].data[i].radius = tuple(r * s for r in rad[k])
    me.skin_vertices[0].data[keys.index("pel")].use_root = True
    sub = ob.modifiers.new("sub", "SUBSURF")
    sub.levels = 2
    sub.render_levels = 2
    ob.location = (x, y, 0.0)
    m = bpy.data.materials.new("FigureGrey")
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (colour ** 2.2,) * 3 + (1,)
    b.inputs["Roughness"].default_value = 0.9
    me.materials.append(m)
    return ob


# ----------------------------------------------------------------------------------------------- cameras
def camera(name, loc, target, ortho=None, lens=85.0):
    cd = bpy.data.cameras.new(name)
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    else:
        cd.lens = lens
    cd.clip_start = 0.05
    cd.clip_end = 500
    ob = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = ob
    return ob


def view_cam(bbox, view, elev=0.0, ortho=True, margin=1.12, lens=85.0, aspect=None):
    lo, hi = np.asarray(bbox[0]), np.asarray(bbox[1])
    c = (lo + hi) / 2
    c[2] = max(hi[2], 0.01) / 2
    ext = hi - lo
    if view == "front":
        d = np.array([0.0, -1.0, 0.0]); w, h = ext[0], hi[2]
    elif view == "side":
        d = np.array([1.0, 0.0, 0.0]); w, h = ext[1], hi[2]
    elif view == "back":
        d = np.array([0.0, 1.0, 0.0]); w, h = ext[0], hi[2]
    elif view == "top":
        d = np.array([0.0, -1e-3, 1.0]); w, h = ext[0], ext[1]
        elev = 90.0
    elif view == "q34":
        d = np.array([0.7, -1.0, 0.0]); w, h = math.hypot(ext[0], ext[1]), hi[2]
    if view != "top" and elev:
        e = math.radians(elev)
        d = d * math.cos(e) + np.array([0, 0, math.sin(e)])
    d = d / np.linalg.norm(d)
    asp = bpy.context.scene.render.resolution_x / max(bpy.context.scene.render.resolution_y, 1)
    if aspect:
        asp = aspect
    size = max(w, h * asp) * margin
    dist = 30.0 if ortho else size / (36.0 / lens) * 1.15
    loc = c + d * dist
    cam = camera(f"Cam_{view}", tuple(loc), tuple(c), ortho=size if ortho else None, lens=lens)
    return cam


def render(path, res=(1200, 900), samples=None):
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    if samples:
        sc.cycles.samples = samples
    sc.render.filepath = str(path)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(write_still=True)
    log("wrote", path)


# ----------------------------------------------------------------------------------------------- modes
def bbox_of(ob):
    V = np.array([ob.matrix_world @ Vector(c) for c in ob.bound_box])
    return V.min(0), V.max(0)


def mode_clay(rocks, src):
    out = PILOT / "form"
    for r in rocks:
        reset()
        studio()
        ob = mesh_from_npz(r, WORK / f"{r}_dense.npz") if src == "dense" else \
            list(append_from_blend([PLANS[r]["prefix"]]).values())[0]
        ob.data.materials.clear()
        ob.data.materials.append(clay_material())
        bb = bbox_of(ob)
        bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 1400, 1000
        for v, el in (("front", 8.0), ("side", 8.0), ("top", 90.0), ("q34", 18.0)):
            view_cam(bb, v, elev=el, ortho=(v != "q34"))
            render(out / f"clay_{r}_{v}.png", res=(1400, 1000), samples=64)


def mode_sil(rocks, src):
    out = PILOT / "sil"
    meta = {}
    for r in rocks:
        reset()
        world_colour((1, 1, 1), 1.0)
        ob = mesh_from_npz(r, WORK / f"{r}_dense.npz") if src == "dense" else \
            list(append_from_blend([PLANS[r]["prefix"]]).values())[0]
        ob.data.materials.clear()
        ob.data.materials.append(clay_material(0.0))
        for o in list(bpy.data.objects):
            if o.name.startswith("UCX_"):
                bpy.data.objects.remove(o)
        holdout_ground()
        bb = bbox_of(ob)
        meta[r] = {"bbox": [bb[0].tolist(), bb[1].tolist()]}
        bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 800, 800
        shots = [("front", e) for e in (0, 5, 10, 15)] + [("side", e) for e in (0, 5, 10, 15)] + \
                [("back", 0), ("top", 90)] + [("front", e) for e in (30, 45, 60)]
        bpy.context.scene.cycles.samples = 4
        bpy.context.scene.cycles.use_denoising = False
        for v, e in shots:
            view_cam(bb, v, elev=e, ortho=True, margin=1.1)
            render(out / f"sil_{r}_{v}_e{e:02d}.png", res=(800, 800))
    (PILOT / "sil" / "sil_meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    src = "dense"
    if "--src" in argv:
        i = argv.index("--src")
        src = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    mode = argv[0]
    rocks = argv[1:] or list(PLANS)
    if mode == "clay":
        mode_clay(rocks, src)
    elif mode == "sil":
        mode_sil(rocks, src)
    else:
        import rocks_render_final as rfin
        getattr(rfin, "mode_" + mode)(rocks, src)


if __name__ == "__main__":
    main()
