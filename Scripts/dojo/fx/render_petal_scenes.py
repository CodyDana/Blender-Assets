"""Sunset tests for the petals and the fallen-petal decal bake (headless Blender 5.2, Cycles GPU).

    blender -b Assets/Dojo/DojoFX.blend --factory-startup --python Scripts/dojo/fx/render_petal_scenes.py -- \
        --out DIR [--only drift,pavers,moss,gravel,decal] [--samples 256]

drift   petals falling against a low backlit sun with depth of field (the sheet's sunset panel)
pavers  fallen petals + SM_DKF_PetalDrift_B on granite pavers (the dojo kit's T_DJ_Granite)
moss    fallen petals on moss (T_DKN_Moss) against a granite boulder (SM_DKN_PineD1_Rock, the pines kit)
gravel  fallen petals on raked gravel (T_DKG_Gravel on raked ridges)
decal   top-down orthographic bake of four scatter cells -> T_DKF_PetalScatter_BC / _N / _ORM (2048, 2x2 atlas)

Every test uses the owner's sun: ~9 deg elevation, warm. Ground textures are our own kit maps (no sourced scenery in
these Blender tests; the Unreal level uses the owner's Megascans).
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fx_bl as B  # noqa: E402
import fx_common as fx  # noqa: E402

KIT = fx.ROOT / "Exports/DojoKit"
PETAL_KEYS = ["A", "B", "C", "D", "E", "F"]
SUN_COLOUR = (1.0, 0.56, 0.30)
OLD_RATIO = 1 / 8


def args():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--out", default=str(fx.WORK / "renders/scenes"))
    p.add_argument("--only", default="drift,pavers,moss,gravel,decal")
    p.add_argument("--samples", type=int, default=256)
    return p.parse_args(a)


def new_scene(name, samples, res, view="AgX", transparent=False):
    sc = bpy.data.scenes.new(name)
    sc.unit_settings.system = "METRIC"
    B.cycles(sc, samples=samples, res=res, transparent=transparent, view=view)
    return sc


def render(sc, path):
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True, scene=sc.name)


def mesh_obj(sc, name, verts, faces, mat=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    sc.collection.objects.link(ob)
    if mat:
        me.materials.append(mat)
    return ob


def grid(sc, name, size, n, height_fn=None, mat=None, uv_scale=1.0):
    xs = np.linspace(-size / 2, size / 2, n + 1)
    verts = []
    for y in xs:
        for x in xs:
            verts.append((x, y, height_fn(x, y) if height_fn else 0.0))
    faces = [(j * (n + 1) + i, j * (n + 1) + i + 1, (j + 1) * (n + 1) + i + 1, (j + 1) * (n + 1) + i)
             for j in range(n) for i in range(n)]
    ob = mesh_obj(sc, name, verts, faces, mat)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def sun(sc, elev_deg, azim_deg, strength=4.0, colour=SUN_COLOUR, angle=1.5):
    ld = bpy.data.lights.new("Sun", "SUN")
    ld.energy = strength
    ld.color = colour
    ld.angle = math.radians(angle)
    ob = bpy.data.objects.new("Sun", ld)
    sc.collection.objects.link(ob)
    # the light shines along its -Z: point it from (elev, azim) toward the origin
    d = Vector((math.cos(math.radians(elev_deg)) * math.cos(math.radians(azim_deg)),
                math.cos(math.radians(elev_deg)) * math.sin(math.radians(azim_deg)),
                math.sin(math.radians(elev_deg))))
    ob.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    return ob


def sky(sc, horizon=(1.0, 0.62, 0.42), zenith=(0.30, 0.34, 0.50), strength=0.6):
    w = bpy.data.worlds.new("Sky_" + sc.name)
    sc.world = w
    w.use_nodes = True
    t = w.node_tree
    bg = next(n for n in t.nodes if n.type == "BACKGROUND")
    tc = B.node(t, "ShaderNodeTexCoord", (-900, 0))
    sep = B.node(t, "ShaderNodeSeparateXYZ", (-700, 0))
    B.link(t, B.out(tc, "Generated"), sep.inputs[0])
    tc2 = B.node(t, "ShaderNodeNewGeometry", (-900, -200))
    sep2 = B.node(t, "ShaderNodeSeparateXYZ", (-700, -200))
    B.link(t, B.out(tc2, "Incoming"), sep2.inputs[0])
    mr = B.node(t, "ShaderNodeMapRange", (-500, -200))
    B.link(t, sep2.outputs[2], B.inp(mr, "Value"))
    B.inp(mr, "From Min").default_value = 0.0
    B.inp(mr, "From Max").default_value = -0.6
    col = B.mix_rgb(t, B.out(mr, "Result"), (*horizon, 1), (*zenith, 1), (-300, 0))
    B.link(t, col, bg.inputs["Color"])
    bg.inputs["Strength"].default_value = strength
    return w


def link_dup(sc, src, name=None):
    ob = bpy.data.objects.new(name or src.name + "_i", src.data)
    sc.collection.objects.link(ob)
    return ob


def petal_sources():
    ps = [bpy.data.objects[f"SM_DKF_Petal_{k}"] for k in PETAL_KEYS]
    old = bpy.data.objects["SM_DKF_PetalOld_A"]
    return ps, old


def rest_offset(ob_data, rot3):
    """Distance from the origin to the lowest vertex along local Z after a rotation (to rest on a surface)."""
    return -min((rot3 @ v.co).z for v in ob_data.vertices)


_BVH = {}


def bvh_of(ob):
    """World-space BVH of a mesh object's own data (works in scenes that are not the evaluated context scene)."""
    from mathutils.bvhtree import BVHTree
    key = (ob.name, tuple(round(v, 6) for v in ob.matrix_world.translation))
    if key not in _BVH:
        mw = ob.matrix_world
        verts = [mw @ v.co for v in ob.data.vertices]
        _BVH[key] = BVHTree.FromPolygons(verts, [tuple(p.vertices) for p in ob.data.polygons])
    return _BVH[key]


def scatter_on(sc, surface, n, centre, radius, rng, clumps=3, flat_weight=0.75, old_ratio=OLD_RATIO,
               region=None):
    """Drop n petal instances onto `surface` by ray casts; clumped + strays; ~old_ratio browned."""
    ps, old = petal_sources()
    flat = [ps[0], ps[1], ps[3], ps[5]]
    curly = [ps[2], ps[4]]
    sc.view_layers[0].update()
    dg = bpy.context.evaluated_depsgraph_get() if sc == bpy.context.scene else sc.view_layers[0].depsgraph
    cl = [Vector((centre[0] + rng.uniform(-radius, radius) * 0.6, centre[1] + rng.uniform(-radius, radius) * 0.6, 0))
          for _ in range(clumps)]
    placed = []
    inv = surface.matrix_world.inverted()
    for k in range(n):
        if region is not None:
            x, y = rng.uniform(region[0], region[1]), rng.uniform(region[2], region[3])
        elif rng.random() < 0.35:
            r = radius * math.sqrt(rng.random()); th = rng.uniform(0, 2 * math.pi)
            x, y = centre[0] + r * math.cos(th), centre[1] + r * math.sin(th)
        else:
            c = cl[rng.integers(0, len(cl))]
            r = radius * 0.3 * abs(rng.normal()); th = rng.uniform(0, 2 * math.pi)
            x, y = c.x + r * math.cos(th), c.y + r * math.sin(th)
        loc, nrm, _i, _d = bvh_of(surface).ray_cast(Vector((x, y, 5.0)), Vector((0, 0, -1)))
        if loc is None:
            continue
        nrm = nrm.normalized()
        if nrm.z < 0:
            nrm = -nrm
        src = old if rng.random() < old_ratio else (flat[rng.integers(0, 4)] if rng.random() < flat_weight
                                                   else curly[rng.integers(0, 2)])
        flip = rng.random() < 0.3
        local = Euler((math.pi if flip else 0.0, rng.normal(0, 0.1), rng.uniform(0, 2 * math.pi)), "XYZ").to_matrix()
        align = nrm.to_track_quat("Z", "Y").to_matrix()
        rot = align @ local
        off = rest_offset(src.data, local)
        lift = 0.00025 + sum(0.0005 for p in placed if (p - loc).length < 0.007)
        ob = link_dup(sc, src)
        ob.matrix_world = Matrix.Translation(loc + nrm * (off + lift)) @ rot.to_4x4()
        placed.append(loc)
    return len(placed)


# --------------------------------------------------------------------------- scenes

def scene_drift(a, out):
    sc = new_scene("Drift", a.samples, (1600, 720))
    rng = np.random.default_rng(3)
    ps, old = petal_sources()
    cam = bpy.data.objects.new("CamDrift", bpy.data.cameras.new("CamDrift"))
    sc.collection.objects.link(cam)
    cam.location = (0, -0.55, 0.0)
    B.look_at(cam, (0, 0, 0))
    cam.data.lens = 85
    cam.data.clip_start = 0.01
    sc.camera = cam
    cam.data.dof.use_dof = True
    cam.data.dof.focus_distance = 0.55
    cam.data.dof.aperture_fstop = 2.2
    for k in range(95):
        depth = rng.uniform(-0.10, 0.40)
        dist = 0.55 + depth
        half_w = dist * 18 / 85 * 1.05
        x = rng.uniform(-half_w, half_w)
        z = rng.uniform(-half_w * 0.45, half_w * 0.45)
        src = old if rng.random() < 1 / 14 else ps[rng.integers(0, 6)]
        ob = link_dup(sc, src)
        ob.location = (x, depth, z)
        ob.rotation_euler = Euler((rng.uniform(0, 2 * math.pi), rng.uniform(0, 2 * math.pi), rng.uniform(0, 2 * math.pi)))
    # background: dark foliage card with warm out-of-focus lights and the low sun upper left
    bgm = B.simple_material("M_BG", (0.035, 0.028, 0.025), rough=1.0)
    grid(sc, "BG", 6.0, 1, mat=bgm).rotation_euler = (math.pi / 2, 0, 0)
    sc.objects["BG"].location = (0, 3.0, 0)
    em = bpy.data.materials.new("M_Bokeh")
    em.use_nodes = True
    t = em.node_tree
    t.nodes.clear()
    e = B.node(t, "ShaderNodeEmission", (0, 0))
    e.inputs["Color"].default_value = (1.0, 0.55, 0.28, 1)
    e.inputs["Strength"].default_value = 1.6
    mo = B.node(t, "ShaderNodeOutputMaterial", (200, 0))
    B.link(t, e.outputs[0], mo.inputs[0])
    sm = bpy.data.materials.new("M_SunDisk")
    sm.use_nodes = True
    t2 = sm.node_tree
    t2.nodes.clear()
    e2 = B.node(t2, "ShaderNodeEmission", (0, 0))
    e2.inputs["Color"].default_value = (1.0, 0.72, 0.42, 1)
    e2.inputs["Strength"].default_value = 160.0
    mo2 = B.node(t2, "ShaderNodeOutputMaterial", (200, 0))
    B.link(t2, e2.outputs[0], mo2.inputs[0])
    for k in range(36):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=rng.uniform(0.004, 0.014), segments=12, ring_count=6)
        s = bpy.context.active_object
        for c in list(s.users_collection):
            c.objects.unlink(s)
        sc.collection.objects.link(s)
        s.location = (rng.uniform(-1.0, 0.9), 2.9, rng.uniform(-0.15, 0.45) + (0.3 if rng.random() < 0.3 else 0))
        s.data.materials.append(em if rng.random() < 0.8 else bgm)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.30, segments=24, ring_count=12)
    s = bpy.context.active_object
    for c in list(s.users_collection):
        c.objects.unlink(s)
    sc.collection.objects.link(s)
    s.location = (-0.75, 2.95, 0.42)
    s.data.materials.append(sm)
    sun(sc, 12, 115, strength=5.0)  # from behind-left: back-lit petals with rim glow
    sky(sc, horizon=(1.0, 0.6, 0.3), zenith=(0.06, 0.05, 0.06), strength=0.35)
    sc.view_settings.exposure = 0.5
    render(sc, out / "drift_sunset.png")


def ground_panel(a, out, kind):
    sc = new_scene(kind.capitalize(), a.samples, (1280, 800))
    rng = np.random.default_rng({"pavers": 11, "moss": 12, "gravel": 13}[kind])
    T = KIT
    if kind == "pavers":
        mat = B.textured_material("M_Granite", T / "Materials/Textures/T_DJ_Granite_BC.png",
                                  T / "Materials/Textures/T_DJ_Granite_N.png", T / "Materials/Textures/T_DJ_Granite_ORM.png",
                                  scale=0.14, tint=(1.25, 1.25, 1.27), box=True)
        joint = B.simple_material("M_Joint", (0.05, 0.045, 0.04), rough=1.0)
        grid(sc, "Bed", 3.0, 1, mat=joint)
        pitch = 0.080  # granite setts ~7.4 cm (the sheet's pavers are small setts ~5-6 petal lengths across)
        for i in range(-7, 8):
            for j in range(-5, 12):
                w, d, h = 0.074 + rng.uniform(-0.004, 0.004), 0.074 + rng.uniform(-0.003, 0.003), 0.03 + rng.uniform(0, 0.004)
                x0, y0 = i * pitch + (pitch / 2 if j % 2 else 0) + rng.normal(0, 0.002), j * pitch
                bpy.ops.mesh.primitive_cube_add(size=1)
                c = bpy.context.active_object
                for cc in list(c.users_collection):
                    cc.objects.unlink(c)
                sc.collection.objects.link(c)
                c.scale = (w, d, h)
                c.location = (x0, y0, h / 2 - 0.005)
                c.rotation_euler = (rng.normal(0, 0.006), rng.normal(0, 0.006), rng.normal(0, 0.01))
                c.data.materials.append(mat)
                c.name = f"Paver_{i}_{j}"
        sc.view_layers[0].update()
        # the exported drift mesh on the pavers + strays by ray cast on the slabs
        drift = link_dup(sc, bpy.data.objects["SM_DKF_PetalDrift_B"], "Drift_B")
        drift.location = (0.02, 0.10, 0.0272)
        count = 0
        slabs = [o for o in sc.objects if o.name.startswith("Paver_")]
        for k in range(1100):
            s = slabs[rng.integers(0, len(slabs))]
            if (s.location.xy - Vector((0.0, 0.1))).length > 0.35:
                continue
            count += scatter_on(sc, s, 2, (s.location.x, s.location.y), 0.03, rng, old_ratio=1 / 7)
        cam_loc, target = (0.0, -0.10, 0.16), (0.02, 0.10, 0.02)
        sun_az = 160
    elif kind == "moss":
        mat = B.textured_material("M_Moss", T / "Pines/Textures/T_DKN_Moss_BC.png", T / "Pines/Textures/T_DKN_Moss_N.png",
                                  T / "Pines/Textures/T_DKN_Moss_ORM.png", scale=0.18, tint=(1.1, 1.25, 1.0))
        def hf(x, y):
            return 0.012 * math.sin(7 * x + 1.3) * math.sin(5 * y + 0.4) + 0.006 * math.sin(23 * x + 17 * y)
        g = grid(sc, "Moss", 2.4, 160, hf, mat)
        sc.view_layers[0].update()
        bpy.ops.wm.fbx_import(filepath=str(T / "Pines/SM_DKN_PineD1_Rock.fbx")) if hasattr(bpy.ops.wm, "fbx_import") \
            else bpy.ops.import_scene.fbx(filepath=str(T / "Pines/SM_DKN_PineD1_Rock.fbx"))
        rocks = [o for o in bpy.context.scene.objects if o.name.startswith("SM_DKN_PineD1_Rock") and o.type == "MESH"]
        gran = B.textured_material("M_RockGranite", T / "Materials/Textures/T_DJ_Granite_BC.png",
                                   T / "Materials/Textures/T_DJ_Granite_N.png", T / "Materials/Textures/T_DJ_Granite_ORM.png",
                                   scale=0.8, tint=(0.8, 0.8, 0.82), box=True)
        for r in rocks:
            for c in list(r.users_collection):
                c.objects.unlink(r)
            sc.collection.objects.link(r)
            r.data.materials.clear()
            r.data.materials.append(gran)
            r.location = (0, 0, 0)
            r.rotation_euler = (0, 0, 0.6)
            sc.view_layers[0].update()
            bb = [r.matrix_world @ Vector(c) for c in r.bound_box]
            # boulder behind-right of the moss patch, like the sheet's panel (bbox min x 0.06, min y 0.16)
            r.location = (-0.02 - min(v.x for v in bb), 0.10 - min(v.y for v in bb), -0.06)
        for o in list(bpy.context.scene.objects):
            if o.name.startswith("UCX_SM_DKN_PineD1_Rock"):
                o.hide_render = True
        sc.view_layers[0].update()
        scatter_on(sc, g, 320, (0.02, 0.08), 0.20, rng, clumps=5)
        cam_loc, target = (-0.06, -0.13, 0.15), (0.03, 0.10, 0.01)
        sun_az = 150
    else:
        mat = B.textured_material("M_Gravel", T / "Ground/Textures/T_DKG_Gravel_BC.png", T / "Ground/Textures/T_DKG_Gravel_N.png",
                                  T / "Ground/Textures/T_DKG_Gravel_ORM.png", scale=0.25, tint=(1.35, 1.28, 1.22))
        def hf(x, y):
            u = x * math.cos(0.5) + y * math.sin(0.5)
            return 0.0035 * math.sin(2 * math.pi * u / 0.045 + 0.8 * math.sin(3.1 * x + 1.7 * y)) + 0.0008 * math.sin(41 * x + 29 * y)
        g = grid(sc, "Gravel", 2.4, 400, hf, mat)
        sc.view_layers[0].update()
        scatter_on(sc, g, 240, (0.0, 0.06), 0.20, rng, clumps=6, old_ratio=1 / 6)
        cam_loc, target = (0.0, -0.12, 0.15), (0.0, 0.08, 0.0)
        sun_az = 165
    cam = bpy.data.objects.new("Cam_" + kind, bpy.data.cameras.new("Cam_" + kind))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.location = cam_loc
    B.look_at(cam, target)
    cam.data.lens = 50
    cam.data.clip_start = 0.01
    cam.data.dof.use_dof = True
    cam.data.dof.focus_distance = (Vector(cam_loc) - Vector(target)).length
    cam.data.dof.aperture_fstop = 5.6
    sun(sc, 9, sun_az, strength=4.5)
    sky(sc, strength=0.55)
    sc.view_settings.exposure = 0.2
    render(sc, out / f"fallen_{kind}.png")


def scene_decal(a, out):
    """Four 0.35 m scatter cells rendered top-down (albedo, normal, alpha) and packed into a 2048 atlas."""
    cell = 0.35
    sc = new_scene("DecalBake", 64, (2048, 2048), view="Standard", transparent=True)
    rng = np.random.default_rng(21)
    # flat invisible catcher to ray cast on (holdout-free: it is not rendered)
    g = grid(sc, "Catcher", 2 * cell, 1)
    g.hide_render = True
    specs = [(45, 0.12, 2), (80, 0.13, 3), (170, 0.12, 2), (60, 0.16, 1)]  # sparse, medium, dense drift, strays
    for ci, (n, rad, clumps) in enumerate(specs):
        cx = (ci % 2 - 0.5) * cell
        cy = (0.5 - ci // 2) * cell
        m = 0.03  # keep petals off the cell border (no bleed between atlas cells)
        scatter_on(sc, g, n, (cx, cy), rad, rng, clumps=clumps,
                   region=(cx - cell / 2 + m, cx + cell / 2 - m, cy - cell / 2 + m, cy + cell / 2 - m) if ci == 3 else None)
    # clip anything that strayed over a cell border
    for o in list(sc.objects):
        if o.type == "MESH" and o.name.startswith("SM_DKF"):
            cx = (0.5 if o.location.x > 0 else -0.5) * cell
            cy = (0.5 if o.location.y > 0 else -0.5) * cell
            if abs(o.location.x - cx) > cell / 2 - 0.012 or abs(o.location.y - cy) > cell / 2 - 0.012:
                bpy.data.objects.remove(o)
    cam = bpy.data.objects.new("CamTop", bpy.data.cameras.new("CamTop"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 2 * cell
    cam.location = (0, 0, 1.0)
    cam.rotation_euler = (0, 0, 0)
    B.world_color(sc, (1, 1, 1), 1.0)
    # no transmission during the bake: the albedo pass must hold the reflectance only
    saved = {}
    for mname in ("MI_DKF_Petal", "MI_DKF_PetalOld"):
        mt = bpy.data.materials[mname]
        for n in mt.node_tree.nodes:
            if n.type == "MATH" and n.operation == "MULTIPLY":
                saved[(mname, n.name)] = n.inputs[1].default_value
                n.inputs[1].default_value = 0.0
    vl = sc.view_layers[0]
    vl.use_pass_diffuse_color = True
    vl.use_pass_normal = True
    vl.use_pass_glossy_color = False
    sc.render.image_settings.media_type = "MULTI_LAYER_IMAGE"
    sc.render.image_settings.file_format = "OPEN_EXR_MULTILAYER"
    sc.render.image_settings.color_depth = "32"
    exr = out / "decal_bake.exr"
    render(sc, exr)
    for (mname, nname), v in saved.items():
        bpy.data.materials[mname].node_tree.nodes[nname].inputs[1].default_value = v
    # read passes from the multilayer EXR via render result API
    import OpenImageIO as oiio  # bundled with Blender
    inp = oiio.ImageInput.open(str(exr))
    layers = {}
    k = 0
    while inp.seek_subimage(k, 0):
        spec = inp.spec()
        arr = np.array(inp.read_image(k, 0, 0, spec.nchannels, oiio.FLOAT)).reshape(spec.height, spec.width, spec.nchannels)
        for ci, cn in enumerate(spec.channelnames):
            layers[cn.split(".", 1)[1]] = arr[..., ci]
        k += 1
    inp.close()
    names = sorted(layers)

    def chans(prefix, suffixes):
        return np.stack([layers[f"{prefix}.{s}"] for s in suffixes], axis=-1)

    alpha = chans("Combined", ["A"])[..., 0]
    albedo = chans("Diffuse Color", ["R", "G", "B"])
    normal = chans("Normal", ["X", "Y", "Z"])
    a_ = np.clip(alpha, 0, 1)
    alb = albedo / np.maximum(a_[..., None], 1e-4)  # passes are coverage-weighted at the edges
    bc = fx.dilate_rgb(fx.lin_to_srgb(np.clip(alb, 0, 1)), a_, iters=16)
    nn = normal / np.maximum(np.linalg.norm(normal, axis=-1, keepdims=True), 1e-6)
    nn[a_ < 0.02] = (0, 0, 1)
    # a two-sided petal seen from above shows whichever face is up: face the normal to the camera
    nn = np.where(nn[..., 2:3] < 0, -nn, nn)
    tn = np.stack([nn[..., 0], -nn[..., 1], nn[..., 2]], axis=-1) * 0.5 + 0.5  # top view: tangent = world, DX flips G
    rough = np.where(a_ > 0.5, 0.55, 1.0)
    orm = np.stack([np.ones_like(a_), rough, np.zeros_like(a_)], axis=-1)
    # EXR rows are top-down already
    fx.save_png(np.dstack([bc, a_]), fx.TEX / "T_DKF_PetalScatter_BC.png")
    fx.save_png(tn, fx.TEX / "T_DKF_PetalScatter_N.png")
    fx.save_png(orm, fx.TEX / "T_DKF_PetalScatter_ORM.png")
    # a preview over grey stone for the sheet
    prev = bc * a_[..., None] + np.array([0.35, 0.35, 0.36]) * (1 - a_[..., None])
    fx.save_png(prev, out / "decal_preview.png")
    fx.write_json(out / "decal_bake.json", {"coverage": [round(float(a_[r::1][:, :].mean()), 4) for r in (0,)],
                                           "cells_m": cell, "px_per_mm": round(1024 / (cell * 1000), 2),
                                           "channels": names})


def main():
    a = args()
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    only = set(a.only.split(","))
    if "drift" in only:
        scene_drift(a, out)
    for k in ("pavers", "moss", "gravel"):
        if k in only:
            ground_panel(a, out, k)
    if "decal" in only:
        scene_decal(a, out)
    print("DONE", out)


if __name__ == "__main__":
    main()
