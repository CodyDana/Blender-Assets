"""Senbon needles: renders from the BAKED maps only (the exported PNGs on the preview materials) + the design compare.

Studio = the shuriken pack's hero recipe (world value ramp, ground 0.150 / rough 0.22, the key / rake / fill / bounce /
top-panel strips at the pack's polar positions and powers), copied as values, not imported (the pack's library is
frozen).  Every image is written to Renders/Senbon/ except the compare sheet (WorkFiles/senbon/).

The kunai and the spike are loaded READ-ONLY from Exports/Shuriken (FBX import + their shipped textures); nothing is
written back there.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List

import bpy
import numpy as np
from mathutils import Matrix, Vector
from bpy_extras.object_utils import world_to_camera_view

from . import senbon_spec as S
from . import bake as PB

PROJECT = S.PROJECT
MM = 0.001
GROUND_COLOUR = (0.150, 0.149, 0.144)          # pack (shuriken_lib.render)
GROUND_ROUGH = 0.22
KEY_W, RAKE_A_W, RAKE_B_W, FILL_W, BOUNCE_W, TOP_W = 1.15, 0.88, 0.68, 2.20, 1.60, 1.30


# =========================================================================== scene
def _polar(d, el, az, c=(0, 0, 0)):
    e, a = math.radians(el), math.radians(az)
    return Vector((c[0] + d * math.cos(e) * math.cos(a), c[1] + d * math.cos(e) * math.sin(a), c[2] + d * math.sin(e)))


def _aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def setup(samples, res):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    try:
        pr = bpy.context.preferences.addons["cycles"].preferences
        pr.compute_device_type = "OPTIX"
        pr.get_devices()
        for d in pr.devices:
            d.use = d.type == "OPTIX"
        sc.cycles.device = "GPU" if any(d.use for d in pr.devices) else "CPU"
    except Exception:
        sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    for t in ("Khronos PBR Neutral", "Standard"):
        try:
            sc.view_settings.view_transform = t
            break
        except Exception:
            continue
    w = bpy.data.worlds.new("W_Senbon_Preview")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    co = nt.nodes.new("ShaderNodeTexCoord")
    sp = nt.nodes.new("ShaderNodeSeparateXYZ")
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = -1.0
    mr.inputs["From Max"].default_value = 1.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(co.outputs["Generated"], sp.inputs["Vector"])
    nt.links.new(sp.outputs["Z"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
    e = ramp.color_ramp.elements
    e[0].position, e[0].color = 0.0, (0.006, 0.006, 0.007, 1.0)
    e[1].position, e[1].color = 0.52, (0.020, 0.020, 0.022, 1.0)
    ramp.color_ramp.elements.new(0.70).color = (0.085, 0.086, 0.092, 1.0)
    ramp.color_ramp.elements.new(1.0).color = (0.045, 0.046, 0.050, 1.0)
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    return sc.cycles.device


class Rig:
    def __init__(self, centre=(0, 0, 0), scale=1.0):
        self.coll = bpy.data.collections.new("SB_RIG")
        bpy.context.scene.collection.children.link(self.coll)
        self.objs = []
        gm = bpy.data.materials.new("SB_Ground")
        gm.use_nodes = True
        b = next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        b.inputs["Base Color"].default_value = (*GROUND_COLOUR, 1.0)
        b.inputs["Roughness"].default_value = GROUND_ROUGH
        me = bpy.data.meshes.new("SB_Ground")
        s = 40.0
        me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
        me.materials.append(gm)
        self.ground = bpy.data.objects.new("SB_Ground", me)
        self.coll.objects.link(self.ground)
        c = centre
        k = scale
        self.lights = [self._strip("Key", _polar(0.62 * k, 32, 158, c), 0.42 * k, 0.075 * k, KEY_W * k * k, c),
                       self._strip("RakeA", _polar(0.34 * k, 7, 96, c), 0.50 * k, 0.022 * k, RAKE_A_W * k * k, c,
                                   (1.0, 0.96, 0.90)),
                       self._strip("RakeB", _polar(0.34 * k, 9, -146, c), 0.44 * k, 0.022 * k, RAKE_B_W * k * k, c,
                                   (0.92, 0.95, 1.0)),
                       self._strip("Fill", _polar(0.40 * k, 16, -34, c), 0.55 * k, 0.55 * k, FILL_W * k * k, c,
                                   (0.88, 0.92, 1.0)),
                       self._strip("Bounce", _polar(0.30 * k, 2, -22, c), 0.90 * k, 0.30 * k, BOUNCE_W * k * k, c,
                                   (0.90, 0.93, 1.0))]
        top = self._strip("Top", _polar(0.70 * k, 80, 158, c), 0.70 * k, 0.70 * k, TOP_W * k * k, c, (0.95, 0.96, 1.0))
        top.visible_diffuse = False
        top.visible_shadow = False
        self.lights.append(top)
        cd = bpy.data.cameras.new("SB_Cam")
        cd.lens = 72.0
        cd.clip_start, cd.clip_end = 0.002, 20.0
        self.cam = bpy.data.objects.new("SB_Cam", cd)
        self.coll.objects.link(self.cam)
        bpy.context.scene.camera = self.cam

    def _strip(self, name, loc, sx, sy, power, target, colour=(1.0, 0.97, 0.93)):
        d = bpy.data.lights.new("SB_" + name, "AREA")
        d.shape = "RECTANGLE"
        d.size, d.size_y = sx, sy
        d.energy = power
        d.color = colour
        o = bpy.data.objects.new("SB_" + name, d)
        self.coll.objects.link(o)
        o.location = loc
        _aim(o, target)
        o.visible_camera = False                     # lamps light the set, they are never in frame
        return o

    def remove(self):
        for o in list(self.coll.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(self.coll)


def render(path):
    sc = bpy.context.scene
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return str(path)


def load_png(path) -> np.ndarray:
    im = bpy.data.images.load(str(path))
    w, h = im.size
    a = np.empty(w * h * 4, np.float32)
    im.pixels.foreach_get(a)
    bpy.data.images.remove(im)
    return a.reshape(h, w, 4)[::-1].copy()                      # top-down


def save_png(path, rgb):
    PB.write_png(path, np.clip(rgb[..., :3], 0, 1))
    return str(path)


def montage(tiles: List[np.ndarray], cols: int, pad=8, bg=0.08):
    h, w = tiles[0].shape[:2]
    rows = int(math.ceil(len(tiles) / cols))
    out = np.full((rows * h + (rows + 1) * pad, cols * w + (cols + 1) * pad, 3), bg, np.float32)
    for i, t in enumerate(tiles):
        r, c = divmod(i, cols)
        y, x = pad + r * (h + pad), pad + c * (w + pad)
        out[y:y + h, x:x + w] = t[..., :3]
    return out


def copy_obj(src, name, matrix):
    o = bpy.data.objects.new(name, src.data)
    bpy.context.scene.collection.objects.link(o)
    o.matrix_world = matrix
    return o


def hide_all_except(keep):
    saved = {o: o.hide_render for o in bpy.data.objects}
    keepset = set(keep)
    for o in bpy.data.objects:
        if o.type in ("MESH", "FONT") and o not in keepset:
            o.hide_render = True
    return saved


def restore(saved):
    for o, v in saved.items():
        try:
            o.hide_render = v
        except ReferenceError:
            pass


def fit(cam, objs, frac=0.86, direction=None, target=None, steps=18):
    """Move the camera along its view axis until the objects' projected bbox spans ``frac`` of the frame."""
    sc = bpy.context.scene
    pts = []
    for o in objs:
        M = o.matrix_world
        for v in o.data.vertices:
            pts.append(M @ v.co)
    if target is None:
        lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        target = (lo + hi) / 2
    d = direction.normalized() if direction is not None else (cam.location - Vector(target)).normalized()
    dist = (cam.location - Vector(target)).length
    target = Vector(target)
    sub = pts[::max(1, len(pts) // 4000)]
    for _ in range(steps):
        cam.location = target + d * dist
        _aim(cam, target)
        bpy.context.view_layer.update()
        cs = [world_to_camera_view(sc, cam, p) for p in sub]
        xs, ys = [c.x for c in cs], [c.y for c in cs]
        span = max(max(xs) - min(xs), (max(ys) - min(ys)))
        cx, cy = 0.5 * (max(xs) + min(xs)) - 0.5, 0.5 * (max(ys) + min(ys)) - 0.5
        W = 2.0 * dist * (0.5 * cam.data.sensor_width / cam.data.lens)
        Hh = W * sc.render.resolution_y / sc.render.resolution_x
        M = cam.matrix_world
        target = target + M.col[0].xyz.normalized() * (cx * W) + M.col[1].xyz.normalized() * (cy * Hh)
        dist *= span / frac
    cam.location = target + d * dist
    _aim(cam, target)
    return Vector(target)


# =========================================================================== objects for the shots
def lying(obj_src, name, x, y, rot_z_deg=0.0, roll_deg=0.0):
    """A copy lying on the ground (z = 0): rotated about its own axis (roll) then about Z, resting on its lowest point."""
    R = Matrix.Rotation(math.radians(rot_z_deg), 4, "Z") @ Matrix.Rotation(math.radians(roll_deg), 4, "X")
    co = np.array([(R @ v.co)[:] for v in obj_src.data.vertices])
    zmin = float(co[:, 2].min())
    o = copy_obj(obj_src, name, Matrix.Translation((x, y, -zmin)) @ R)
    return o


def import_family():
    """SM_Kunai_Plain and SM_Shuriken_Spike LOD0 from Exports/Shuriken (read-only) with their shipped textures."""
    before = set(bpy.data.objects)
    out = {}
    for fbx in ("SM_Shuriken_Spike", "SM_Kunai_Plain"):
        objs0 = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=str(PROJECT / "Exports" / "Shuriken" / f"{fbx}.fbx"),
                                 use_custom_normals=True, axis_forward="-Y", axis_up="Z")
        new = [o for o in bpy.data.objects if o not in objs0]
        lod0 = next(o for o in new if o.type == "MESH" and o.name.startswith(fbx) and o.name.endswith("LOD0"))
        for o in new:
            o.hide_render = True
        # bake the import's parent transform into a fresh object
        me = lod0.data.copy()
        me.transform(lod0.matrix_world)
        ob = bpy.data.objects.new(f"FAM_{fbx}", me)
        bpy.context.scene.collection.objects.link(ob)
        L = (max(v.co.x for v in me.vertices) - min(v.co.x for v in me.vertices))
        out[fbx] = {"obj": ob, "length_m": L, "slots": [m.name if m else None for m in me.materials]}
    tex = PROJECT / "Exports" / "Shuriken" / "Textures"
    # materials from the shipped maps
    for key, o in ((k, v["obj"]) for k, v in out.items()):
        me = o.data
        for i, m in enumerate(list(me.materials)):
            nm = (m.name if m else "").lower()
            if key == "SM_Shuriken_Spike":
                stem = "T_Shuriken_Spike"
            else:
                stem = "T_Kunai_Wrap" if "wrap" in nm else "T_Kunai_Plain"
            mat = bpy.data.materials.new(f"FAM_{stem}_{i}")
            mat.use_nodes = True
            preview(mat, {"BC": tex / f"{stem}_BC.png", "ORM": tex / f"{stem}_ORM.png", "N": tex / f"{stem}_N.png"})
            me.materials[i] = mat
        out[key]["stems"] = [m.name for m in me.materials]
    return out


def preview(mat, paths):
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bs.outputs["BSDF"], out.inputs["Surface"])

    def img(p, data):
        im = bpy.data.images.load(str(p), check_existing=True)
        im.colorspace_settings.name = "Non-Color" if data else "sRGB"
        nd = nt.nodes.new("ShaderNodeTexImage")
        nd.image = im
        return nd
    bc, orm, n = img(paths["BC"], False), img(paths["ORM"], True), img(paths["N"], True)
    nt.links.new(bc.outputs["Color"], bs.inputs["Base Color"])
    nt.nodes.active = bc
    sp = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(orm.outputs["Color"], sp.inputs["Color"])
    nt.links.new(sp.outputs["Green"], bs.inputs["Roughness"])
    nt.links.new(sp.outputs["Blue"], bs.inputs["Metallic"])
    sn = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(n.outputs["Color"], sn.inputs["Color"])
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    nt.links.new(sn.outputs["Green"], inv.inputs[1])
    cm = nt.nodes.new("ShaderNodeCombineColor")
    nt.links.new(sn.outputs["Red"], cm.inputs["Red"])
    nt.links.new(inv.outputs["Value"], cm.inputs["Green"])
    nt.links.new(sn.outputs["Blue"], cm.inputs["Blue"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(cm.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bs.inputs["Normal"])


def clay(name, colour=(0.42, 0.36, 0.32), rough=0.6):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*colour, 1.0)
    b.inputs["Roughness"].default_value = rough
    return m


def emission(name, colour, strength=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*colour, 1.0)
    e.inputs["Strength"].default_value = strength
    nt.links.new(e.outputs["Emission"], o.inputs["Surface"])
    return m


def capsule(name, p0, p1, r, mat):
    bm_mod = __import__("bmesh")
    bm = bm_mod.new()
    bm_mod.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=r)
    # stretch the sphere into a capsule along +Z by moving the upper half
    L = (Vector(p1) - Vector(p0)).length
    for v in bm.verts:
        if v.co.z > 0:
            v.co.z += L
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    d = (Vector(p1) - Vector(p0)).normalized()
    o.matrix_world = Matrix.Translation(p0) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    return o


def hand_proxy():
    """A simple adult-hand-size proxy (not a model): palm 84 x 92 x 26 mm, fingers 18-20 mm thick, middle finger
    82 mm, lying palm down, fingers along +Y."""
    mat = clay("SB_HandProxy")
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= 0.084
        v.co.y *= 0.092
        v.co.z *= 0.022
    me = bpy.data.meshes.new("SB_Palm")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    palm = bpy.data.objects.new("SB_Palm", me)
    bpy.context.scene.collection.objects.link(palm)
    palm.location = (0.0, -0.046, 0.011)
    bv = palm.modifiers.new("bevel", "BEVEL")
    bv.width = 0.011
    bv.segments = 6
    sub = palm.modifiers.new("sub", "SUBSURF")
    sub.levels = sub.render_levels = 2
    for p in me.polygons:
        p.use_smooth = True
    parts = [palm]
    fingers = [(-0.0315, 0.068, 0.0088), (-0.0105, 0.080, 0.0095), (0.0105, 0.077, 0.0092), (0.031, 0.062, 0.0082)]
    for i, (x, L, r) in enumerate(fingers):
        parts.append(capsule(f"SB_Finger{i}", Vector((x, -0.004, r)), Vector((x, L - r, r)), r, mat))
    parts.append(capsule("SB_Thumb", Vector((-0.040, -0.075, 0.011)), Vector((-0.075, -0.020, 0.010)), 0.0105, mat))
    return parts, fingers


# =========================================================================== shots
def wire_copy(src, name, matrix, thick, mat):
    me = src.data.copy()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    o.matrix_world = matrix
    m = o.modifiers.new("wire", "WIREFRAME")
    m.thickness = thick
    m.use_replace = True
    m.use_even_offset = False
    me.materials.clear()
    me.materials.append(mat)
    return o


def text_obj(body, loc, size, mat, align="CENTER", rot=None):
    cu = bpy.data.curves.new("SB_T", "FONT")
    cu.body = body
    cu.size = size
    cu.align_x = align
    cu.materials.append(mat)
    o = bpy.data.objects.new("SB_T", cu)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    if rot is not None:
        o.rotation_euler = rot
    return o


def render_all(objs, report, renders: Path, work: Path, build_work: Path, quick=False, log=print):
    renders.mkdir(parents=True, exist_ok=True)
    tmp = build_work / "gallery_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    spp = 16 if quick else 160
    out = {"device": setup(spp, (1600, 900)), "samples": spp, "files": {}}
    N0, H0 = objs["needle"][0], objs["heavy"][0]
    made = []

    def keep(*xs):
        made.extend(xs)
        return xs

    sc = bpy.context.scene
    rig = Rig(centre=(0, 0, 0), scale=1.0)

    # --- hero: both needles on the ground, 3/4 (the pack's hero camera direction)
    a = lying(N0, "H_needle", 0.0, 0.016, 18.0, 0.0)
    b = lying(H0, "H_heavy", 0.0, -0.016, 18.0, 0.0)
    keep(a, b)
    saved = hide_all_except([a, b, rig.ground])
    rig.cam.data.lens = 72.0
    rig.cam.location = _polar(0.5, 29.0, -22.0)
    fit(rig.cam, [a, b], 0.88)
    out["files"]["hero"] = render(renders / "senbon_hero.png")
    restore(saved)
    log("hero")

    # --- turntable: 8 azimuths per item (camera fixed, the needle turned about Z), 800 x 450 tiles
    sc.render.resolution_x, sc.render.resolution_y = 800, 450
    for key, src in (("needle", N0), ("heavy", H0)):
        tiles = []
        for i, az in enumerate(range(0, 360, 45)):
            o = lying(src, f"TT_{key}_{az}", 0.0, 0.0, float(az), 0.0)
            saved = hide_all_except([o, rig.ground])
            rig.cam.data.lens = 72.0
            rig.cam.location = _polar(0.5, 24.0, -90.0)
            fit(rig.cam, [lying_proxy(o)], 0.80, target=Vector((0, 0, 0.002)))
            p = render(tmp / f"tt_{key}_{az:03d}.png")
            tiles.append(load_png(p))
            restore(saved)
            bpy.data.objects.remove(o, do_unlink=True)
        out["files"][f"turntable_{key}"] = save_png(renders / f"senbon_turntable_{key}.png", montage(tiles, 4))
        log(f"turntable {key}")

    # --- close-ups (macro, 1200 x 900): the needle point, the heavy point, the heavy tail + wrap
    sc.render.resolution_x, sc.render.resolution_y = 1200, 900
    shots = [("needle_point", N0, 0.0, (0.057, 0.0, 0.0013), 0.075, 22.0, -60.0, 100.0),
             ("heavy_point", H0, 0.0, (0.159 - report["pivots"]["heavy_com_mm"] * MM, 0.0, 0.0022), 0.10, 26.0, -55.0, 100.0),
             ("heavy_point_top", H0, 0.0, (0.159 - report["pivots"]["heavy_com_mm"] * MM, 0.0, 0.0022), 0.10, 70.0, -90.0, 100.0),
             ("heavy_wrap", H0, 0.0, (0.028 - report["pivots"]["heavy_com_mm"] * MM, 0.0, 0.0023), 0.16, 24.0, -62.0, 100.0)]
    tiles = []
    for name, src, rz, tgt, dist, el, az, lens in shots:
        o = lying(src, "CU_" + name, 0.0, 0.0, rz, 0.0)
        saved = hide_all_except([o, rig.ground])
        rig.cam.data.lens = lens
        rig.cam.location = _polar(dist, el, az, tgt)
        _aim(rig.cam, tgt)
        p = render(tmp / f"cu_{name}.png")
        tiles.append(load_png(p))
        restore(saved)
        bpy.data.objects.remove(o, do_unlink=True)
    out["files"]["closeups"] = save_png(renders / "senbon_closeups.png", montage(tiles, 2))
    log("closeups")

    # --- hand scale: a hand-size proxy with three needles between the fingers + the heavy beside it
    sc.render.resolution_x, sc.render.resolution_y = 1600, 900
    parts, fingers = hand_proxy()
    keep(*parts)
    held = []
    gaps = [0.5 * (fingers[i][0] + fingers[i + 1][0]) for i in range(3)]
    for i, gx in enumerate(gaps):
        r_f = 0.5 * (fingers[i][2] + fingers[i + 1][2])
        # the needle lies in the valley between two fingers, its middle (Grip) at the proximal joints
        o = copy_obj(N0, f"HS_needle{i}", Matrix.Translation((gx, 0.058 + 0.004 * (1 - i), r_f * 1.45))
                     @ Matrix.Rotation(math.radians(90.0 + (i - 1) * 4.0), 4, "Z"))
        held.append(o)
    hv = lying(H0, "HS_heavy", 0.080, 0.02, 90.0, 0.0)
    keep(*held, hv)
    ruler = ruler_100mm(Vector((-0.045, -0.112, 0.0)))
    keep(*ruler)
    saved = hide_all_except(parts + held + [hv, rig.ground] + ruler)
    rig.cam.data.lens = 60.0
    rig.cam.location = _polar(0.6, 48.0, -70.0, (0.02, 0.0, 0.0))
    fit(rig.cam, parts + held + [hv] + [r for r in ruler if r.type == "MESH"], 0.84)
    out["files"]["hand_scale"] = render(renders / "senbon_hand_scale.png")
    restore(saved)
    log("hand scale")

    # --- family: the needle, the heavy, the pack's spike and kunai (read-only), side by side
    fam = import_family()
    out["family_import"] = {k: {"length_mm": round(v["length_m"] * 1000, 2), "materials": v["stems"]}
                            for k, v in fam.items()}
    spike, kunai = fam["SM_Shuriken_Spike"]["obj"], fam["SM_Kunai_Plain"]["obj"]
    rows = [(kunai, 0.036), (spike, 0.012), (H0, -0.008), (N0, -0.026)]
    placed = []
    for src, y in rows:
        co = np.array([v.co[:] for v in src.data.vertices])
        xc = 0.5 * (co[:, 0].min() + co[:, 0].max())
        o = lying(src, "FAM_" + src.name, -xc + 0.0, y, 0.0, 0.0)
        o.location.x -= xc * 0 + 0.0
        placed.append(o)
    keep(*placed)
    saved = hide_all_except(placed + [rig.ground])
    rig.cam.data.lens = 72.0
    rig.cam.location = _polar(0.7, 36.0, -64.0)
    fit(rig.cam, placed, 0.90)
    out["files"]["family"] = render(renders / "senbon_family.png")
    restore(saved)
    log("family")

    # --- wire + LOD strip: ortho from +Z, the item's LODs stacked, wire overlay (dark, ~1 px)
    rig.ground.hide_render = False
    wmat = emission("SB_Wire", (0.9, 0.55, 0.15), 1.0)
    tmat = emission("SB_Label", (0.85, 0.85, 0.82), 1.0)
    cam_o = ortho_cam()
    for key in ("needle", "heavy"):
        L = objs[key]
        items = []
        y0 = 0.0
        for i, src in enumerate(L):
            M = Matrix.Translation((0.0, -0.016 * i, 0.003))
            c = copy_obj(src, f"LS_{key}_{i}", M)
            w = wire_copy(src, f"LW_{key}_{i}", Matrix.Translation((0, 0, 0.0001)) @ M, 0.00006, wmat)
            tris = report["measure"][key]["triangles"][i]
            sides = (S.NEEDLE_LODS if key == "needle" else S.HEAVY_LODS)[i].sides
            t = text_obj(f"LOD{i}  {tris} tris  {sides} sides", (-0.002, -0.016 * i - 0.0105, 0.004), 0.0042, tmat)
            items += [c, w, t]
        keep(*items)
        saved = hide_all_except(items + [rig.ground])
        span_x = 0.135 if key == "needle" else 0.175
        sc.render.resolution_x, sc.render.resolution_y = 2400, 900
        cam_o.data.ortho_scale = span_x * 1.10
        cox = [v.co.x for v in L[0].data.vertices]
        xc = 0.5 * (min(cox) + max(cox))
        cam_o.location = (xc, -0.0205, 0.3)              # FINALISE: lowered so the LOD2 label is not clipped
        sc.camera = cam_o
        out["files"][f"lods_{key}"] = render(renders / f"senbon_lods_{key}.png")
        restore(saved)
    # point close-ups per LOD with wire (persp)
    sc.camera = rig.cam
    sc.render.resolution_x, sc.render.resolution_y = 800, 600
    tiles = []
    for key, tip_x in (("needle", 0.065), ("heavy", (170.0 - report["pivots"]["heavy_com_mm"]) * MM)):
        for i, src in enumerate(objs[key]):
            o = lying(src, f"LP_{key}_{i}", 0.0, 0.0, 0.0, 0.0)
            w = wire_copy(src, f"LPW_{key}_{i}", o.matrix_world, 0.000025, wmat)
            saved = hide_all_except([o, w, rig.ground])
            tgt = Vector((tip_x - (0.010 if key == "needle" else 0.014), 0, 0.0015))
            rig.cam.data.lens = 100.0
            rig.cam.location = _polar(0.085 if key == "needle" else 0.11, 28.0, -58.0, tgt)
            _aim(rig.cam, tgt)
            tiles.append(load_png(render(tmp / f"lp_{key}_{i}.png")))
            restore(saved)
            bpy.data.objects.remove(o, do_unlink=True)
            bpy.data.objects.remove(w, do_unlink=True)
    out["files"]["lod_points"] = save_png(renders / "senbon_lod_points.png", montage(tiles, 3))
    # wire views: LOD0 of both, 3/4, wire over shaded
    sc.render.resolution_x, sc.render.resolution_y = 1600, 900
    a = lying(N0, "W_needle", 0.0, 0.012, 18.0, 0.0)
    b = lying(H0, "W_heavy", 0.0, -0.012, 18.0, 0.0)
    wa = wire_copy(N0, "W_needle_w", a.matrix_world, 0.00005, wmat)
    wb = wire_copy(H0, "W_heavy_w", b.matrix_world, 0.00005, wmat)
    keep(a, b, wa, wb)
    saved = hide_all_except([a, b, wa, wb, rig.ground])
    rig.cam.data.lens = 72.0
    rig.cam.location = _polar(0.5, 40.0, -30.0)
    fit(rig.cam, [a, b], 0.9)
    out["files"]["wire"] = render(renders / "senbon_wire.png")
    restore(saved)
    log("wire + lods")

    # --- distance strip (report-only): 1.0 / 2.5 / 5 m at 90 deg hFOV 1080p, the spike as the control
    sc.render.resolution_x, sc.render.resolution_y = 640, 360
    # neutral matte set for the strip: flat grey world, matte mid-grey ground, no strip lamps (no reflections of
    # the studio in the ground at 2.5 / 5 m)
    w_saved = sc.world
    wf = bpy.data.worlds.new("W_Senbon_Flat")
    wf.use_nodes = True
    bgn = next(n for n in wf.node_tree.nodes if n.type == "BACKGROUND")
    bgn.inputs["Color"].default_value = (0.55, 0.55, 0.55, 1.0)
    bgn.inputs["Strength"].default_value = 1.0
    sc.world = wf
    gb = next(n for n in rig.ground.data.materials[0].node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    g_saved = (tuple(gb.inputs["Base Color"].default_value), gb.inputs["Roughness"].default_value)
    gb.inputs["Base Color"].default_value = (0.30, 0.30, 0.30, 1.0)
    gb.inputs["Roughness"].default_value = 1.0
    lamp_saved = [(l, l.hide_render) for l in rig.lights]
    for l, _v in lamp_saved:
        l.hide_render = True
    tiles = []
    for d in (1.0, 2.5, 5.0):
        objs_d = []
        for src, y in ((N0, 0.03), (H0, 0.0), (spike, -0.03)):
            objs_d.append(lying(src, f"D_{src.name}_{d}", 0.0, y, 0.0, 0.0))
        saved = hide_all_except(objs_d + [rig.ground])
        rig.cam.data.lens = 18.0 * 36.0 / 36.0                    # 90 deg horizontal on a 36 mm sensor
        rig.cam.data.sensor_fit = "HORIZONTAL"
        rig.cam.location = _polar(d, 30.0, -90.0)
        _aim(rig.cam, (0, 0, 0))
        img = load_png(render(tmp / f"dist_{d}.png"))
        # crop the middle 1/4 of the frame and upscale x4 (nearest) so the sub-pixel widths are visible
        h, w = img.shape[:2]
        cr = img[h * 3 // 8: h * 5 // 8, w * 3 // 8: w * 5 // 8]
        tiles.append(np.kron(cr[..., :3], np.ones((4, 4, 1))))
        restore(saved)
        for o in objs_d:
            bpy.data.objects.remove(o, do_unlink=True)
    sc.world = w_saved
    gb.inputs["Base Color"].default_value = g_saved[0]
    gb.inputs["Roughness"].default_value = g_saved[1]
    for l, v in lamp_saved:
        l.hide_render = v
    out["files"]["distance"] = save_png(renders / "senbon_distance_strip.png", montage(tiles, 3))
    out["distance_note"] = ("640 x 360 at 90 deg hFOV (the 1080p geometry scaled 1/3: px widths are 1/3 of 1080p); "
                            "centre crop x4 nearest; top to bottom: needle, heavy, spike; report-only (plan 11.3 asks "
                            "for the Unreal TSR test, which is the finaliser's)")
    log("distance strip")
    rig.remove()
    # --- design compare (Workbench, the sheet's renderer and scale)
    out["compare"] = design_compare(objs, report, work, tmp)
    log("design compare")
    for o in made:
        try:
            bpy.data.objects.remove(o, do_unlink=True)
        except ReferenceError:
            pass
    return out


def lying_proxy(o):
    return o


def ortho_cam():
    cd = bpy.data.cameras.new("SB_Ortho")
    cd.type = "ORTHO"
    cd.clip_start, cd.clip_end = 0.001, 2.0
    c = bpy.data.objects.new("SB_Ortho", cd)
    bpy.context.scene.collection.objects.link(c)
    return c


def ruler_100mm(origin):
    """A 100 mm scale bar on the ground (cm ticks), light grey, for the hand shot."""
    m = emission("SB_Ruler", (0.75, 0.75, 0.72), 0.8)
    out = []
    import bmesh
    def bar(name, x0, y0, x1, y1):
        bm = bmesh.new()
        vs = [bm.verts.new((x, y, 0.0002)) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
        bm.faces.new(vs)
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        me.materials.append(m)
        o = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(o)
        o.location = origin
        out.append(o)
    bar("SB_Rul", 0.0, 0.0, 0.100, 0.0008)
    for k in range(11):
        h = 0.004 if k % 5 == 0 else 0.0025
        bar(f"SB_Tick{k}", k * 0.01 - 0.0003, 0.0, k * 0.01 + 0.0003, h)
    t = text_obj("100 mm", origin + Vector((0.042, 0.007, 0.0002)), 0.006, m, align="LEFT")
    out.append(t)
    return out


# =========================================================================== design compare
SHEET_PX_PER_MM = 12.0
SHEET_W_MM, SHEET_H_MM = 400.0, 266.6667
X0 = -185.0


def sheet_px(X, Y):
    return (X + SHEET_W_MM / 2) * SHEET_PX_PER_MM, (SHEET_H_MM / 2 - Y) * SHEET_PX_PER_MM


R_SIDE = Matrix.Rotation(-math.pi / 2, 4, "X")
R_TOP = Matrix.Identity(4)
R_END_TIP = Matrix(((0, 1, 0, 0), (0, 0, 1, 0), (1, 0, 0, 0), (0, 0, 0, 1)))


def views(com):
    """(name, item, rotation, sheet anchor (mm), object reference x (our frame), scale, crop (X0, X1, Y0, Y1) sheet mm,
    clip (object x range kept, our frame))."""
    yS, yT, yS2, yT2 = 104.0, 91.0, 69.0, 55.0
    hs = lambda s: s - com                                    # heavy s -> our object x
    return [
        ("needle_side_1to1", "needle", R_SIDE, (X0 + 65.0, yS), 0.0, 1.0, (X0 - 3, X0 + 133, yS - 4.0, yS + 4.0), None),
        ("needle_top_1to1", "needle", R_TOP, (X0 + 65.0, yT), 0.0, 1.0, (X0 - 3, X0 + 133, yT - 4.0, yT + 4.0), None),
        ("heavy_side_1to1", "heavy", R_SIDE, (X0, yS2), hs(0.0), 1.0, (X0 - 3, X0 + 173, yS2 - 4.5, yS2 + 4.5), None),
        ("heavy_top_1to1", "heavy", R_TOP, (X0, yT2), hs(0.0), 1.0, (X0 - 3, X0 + 173, yT2 - 4.5, yT2 + 4.5), None),
        ("D1_needle_point_5to1", "needle", R_SIDE, (-183.0, -20.0), 37.0, 5.0, (-185.0, -40.0, -28.0, -12.0), (37.0, None)),
        ("D2_heavy_point_side_5to1", "heavy", R_SIDE, (10.0, -25.0), hs(140.0), 5.0, (8.0, 162.0, -37.0, -13.0), (hs(140.0), None)),
        ("D2_heavy_point_top_5to1", "heavy", R_TOP, (10.0, -55.0), hs(140.0), 5.0, (8.0, 162.0, -67.0, -43.0), (hs(140.0), None)),
        ("D2_heavy_end_5to1", "heavy", R_END_TIP, (183.0, -64.0), hs(170.0), 5.0, (170.0, 196.0, -77.0, -51.0), (hs(140.0), None)),
        ("D3_heavy_tail_3to1", "heavy", R_SIDE, (-183.0, -84.0), hs(0.0), 3.0, (-187.0, -183.0 + 62 * 3 + 1, -92.0, -76.0), (None, hs(62.0))),
    ]


def _workbench(sc, w, h):
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = "Standard"
    sc.display.render_aa = "16"
    sh = sc.display.shading
    sh.light = "STUDIO"
    sh.color_type = "TEXTURE"
    sh.show_object_outline = True
    sh.object_outline_color = (0.0, 0.0, 0.0)
    sh.show_cavity = True
    sh.cavity_type = "WORLD"
    sh.show_specular_highlight = True


def clipped_copy(src, name, clip, matrix):
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(src.data)
    lo, hi = clip if clip else (None, None)
    for co, no in ((lo, Vector((-1, 0, 0))), (hi, Vector((1, 0, 0)))):
        if co is None:
            continue
        res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-10,
                                     plane_co=Vector((co * MM, 0, 0)), plane_no=no, clear_outer=True)
        ce = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge) and e.is_valid]
        if ce:
            bmesh.ops.holes_fill(bm, edges=ce, sides=0)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in src.data.materials:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    o.matrix_world = matrix
    return o


def design_compare(objs, report, work: Path, tmp: Path):
    com = report["pivots"]["heavy_com_mm"]
    sheet = load_png(S.SHEET_PATH)                                   # top-down RGBA
    sc = bpy.context.scene
    saved_engine = sc.render.engine
    saved_cam = sc.camera
    cam = ortho_cam()
    sc.camera = cam
    panels = []
    for name, item, R, at, ref, scale, crop, clip in views(com):
        src = objs[item][0]
        M = (Matrix.Translation((at[0] * MM, at[1] * MM, 0)) @ Matrix.Scale(scale, 4) @ R
             @ Matrix.Translation((-ref * MM, 0, 0)))
        o = clipped_copy(src, "CMP_" + name, clip if "end" in name else None, M)
        saved = hide_all_except([o])
        X0c, X1c, Y0c, Y1c = crop
        w = int(round((X1c - X0c) * SHEET_PX_PER_MM))
        h = int(round((Y1c - Y0c) * SHEET_PX_PER_MM))
        _workbench(sc, w, h)
        cam.data.ortho_scale = max(X1c - X0c, (Y1c - Y0c) * w / h) * MM
        cam.location = (0.5 * (X0c + X1c) * MM, 0.5 * (Y0c + Y1c) * MM, 0.5)
        cam.rotation_euler = (0, 0, 0)
        p = render(tmp / f"cmp_{name}.png")
        ours = load_png(p)
        restore(saved)
        bpy.data.objects.remove(o, do_unlink=True)
        px0, py0 = sheet_px(X0c, Y1c)
        crop_img = sheet[int(round(py0)):int(round(py0)) + h, int(round(px0)):int(round(px0)) + w, :3]
        bg = np.full((h, w, 3), 0.985, np.float32)
        al = ours[..., 3:4]
        ours_rgb = ours[..., :3] * al + bg * (1 - al)
        # measured: silhouette height of our render vs the sheet's dark (object) pixels in the same column band
        panels.append((name, crop_img, ours_rgb, al[..., 0]))
    sc.camera = saved_cam
    # layout: each panel = sheet crop above ours, label strip above; stacked vertically, two columns
    labels_h = 46
    gap = 18
    colw = max(p[1].shape[1] for p in panels)
    blocks = []
    for name, a, b, al in panels:
        h = a.shape[0] + b.shape[0] + labels_h * 2 + 6
        blk = np.full((h, colw, 3), 1.0, np.float32)
        blk[labels_h:labels_h + a.shape[0], :a.shape[1]] = a
        y = labels_h * 2 + a.shape[0] + 6
        blk[y:y + b.shape[0], :b.shape[1]] = b
        blocks.append((name, blk, a.shape[0]))
    total_h = sum(b[1].shape[0] + gap for b in blocks) + 520
    canvas = np.full((total_h, colw + 2 * 40, 3), 1.0, np.float32)
    y = 220
    pos = []
    for name, blk, ah in blocks:
        canvas[y:y + blk.shape[0], 40:40 + blk.shape[1]] = blk
        pos.append((name, y, ah))
        y += blk.shape[0] + gap
    # text layer (Workbench, flat ink) rendered at the canvas size and laid over
    lines = compare_text(report)
    txt = text_layer(canvas.shape[1], canvas.shape[0], pos, lines, tmp)
    a = txt[..., 3:4]
    canvas = canvas * (1 - a) + txt[..., :3] * a
    path = work / "SENBON_DESIGN_COMPARE.png"
    save_png(path, canvas)
    sc.render.engine = saved_engine
    return {"file": str(path.relative_to(PROJECT)).replace("\\", "/"), "panels": [p[0] for p in panels],
            "method": "each panel: the design sheet crop (top) and ours (below) at the SAME px per mm, rendered by the "
                      "sheet's own renderer settings (Workbench studio light, outline, cavity) with our baked BC; "
                      "measured dimensions vs the spec are listed at the top"}


def compare_text(report):
    m = report["measure"]
    nd, hd = m["needle"]["dimensions"], m["heavy"]["dimensions"]
    ns, hs = m["needle"]["silhouette_lod0"], m["heavy"]["silhouette_lod0"]
    mm = report["mass_model"]
    return [
        "SENBON - design sheet (top of each pair) vs the build (below), same px per mm, same renderer settings",
        f"NEEDLE  length {m['needle']['length_mm']:.2f} (spec 130.0)   D(0) {nd['D_at_0_side_top'][0]:.3f} (2.80 +-0.02)   "
        f"D(+-50) {nd['D_at_+50'][0]:.3f} / {nd['D_at_-50'][0]:.3f} (2.30)   tips {nd['tips_x_mm'][0]:.2f} / {nd['tips_x_mm'][1]:.2f} (+-65.0)   "
        f"silhouette worst {ns['worst_abs_dev_mm']:.4f} mm at x {ns['worst_at_mm']}   mass {mm['needle']['mass_g']:.3f} g (4.615)",
        f"HEAVY  length {m['heavy']['length_mm']:.2f} (170.0)   steel D {hd['steel_D_at_3']:.3f} (2.80)   wrap D {hd['wrap_D_at_30']:.3f} (4.20)   "
        f"bindings D {hd['rear_binding_D_at_6.75']:.3f} / {hd['front_binding_D_at_53.25']:.3f} (4.60)   D(148) {hd['D_at_147.99']:.3f} (4.50)   "
        f"ridges from s {hd['ridges_start_s_mm']} (159.0)   tip s {hd['tip_s_mm']:.2f}",
        f"        silhouette worst {hs['worst_abs_dev_mm']:.4f} mm   mass {mm['heavy']['mass_g']:.3f} g (11.926)   "
        f"centre of mass {mm['heavy']['com_from_butt_mm']:.3f} mm from the butt (93.695)   "
        f"LOD0 tris {m['needle']['triangles'][0]} / {m['heavy']['triangles'][0]}",
    ]


def text_layer(W, H, pos, header, tmp):
    """Black text on a transparent film at exactly W x H px (1 px = 0.1 mm in the text scene)."""
    sc = bpy.context.scene
    saved = hide_all_except([])
    ink = bpy.data.materials.new("SB_Ink")
    ink.diffuse_color = (0.0, 0.0, 0.0, 1.0)
    grey = bpy.data.materials.new("SB_InkGrey")
    grey.diffuse_color = (0.35, 0.35, 0.35, 1.0)
    U = 0.0001
    made = []

    def put(s, xpx, ypx_top, size_px, mat):
        o = text_obj(s, ((xpx - W / 2) * U, (H / 2 - ypx_top) * U, 0.0), size_px * U, mat, align="LEFT")
        made.append(o)
    put(header[0], 40, 60, 34, ink)
    for i, s in enumerate(header[1:]):
        put(s, 40, 110 + i * 34, 22, ink)
    for name, y, ah in pos:
        put(name.replace("_", " ") + "   - design sheet", 44, y + 32, 24, grey)
        put(name.replace("_", " ") + "   - build (LOD0, baked BC)", 44, y + 46 + ah + 38, 24, ink)
    _workbench(sc, W, H)
    sc.display.shading.color_type = "MATERIAL"
    sc.display.shading.light = "FLAT"
    sc.display.shading.show_object_outline = False
    sc.display.shading.show_cavity = False
    cam = ortho_cam()
    cam.data.ortho_scale = max(W, H) * U
    cam.location = (0, 0, 0.5)
    sc.camera = cam
    for o in made:
        o.hide_render = False
    p = render(tmp / "cmp_text.png")
    img = load_png(p)
    for o in made + [cam]:
        bpy.data.objects.remove(o, do_unlink=True)
    restore(saved)
    return img
