"""SprayBurst by a Mantaflow FLIP liquid sim (method change: the point-sprite spray read as beads / dust).

A liquid blob strikes a thin pool at speed: the crown sheet rises and tears into fingers, then the Worthington column
jets up (the sheet's two spray cut-outs, crown and column, as one life cycle). The liquid surface is rendered white
and colour-neutral with the six light groups of render_flipbooks.py, plus our droplet points (fine spray) and a soft
spray-mist volume at the base. The pool surface is faded out below the base line in the shader so the sprite has no
horizon band.

    blender -b --factory-startup --python Scripts/dojo/fx/spray_sim.py -- [--res 128] [--bake-only] [--frames a,b]
        [--preview] [--cell 512] [--samples 192]
"""
from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fx_bl as B  # noqa: E402
import fx_common as fx  # noqa: E402
import render_flipbooks as RF  # noqa: E402

FPS = 100
IMPACT_FRAME = 6          # the blob reaches the pool at about this sim frame
FIRST, LAST = 7, 70       # 64 sim frames -> 64 flipbook cells
WINDOW = 1.3
CX = 0.0                  # sprite window centre x (set per scene)
BASE_Z = -0.92            # pool surface


def args():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--res", type=int, default=176)
    p.add_argument("--scene", default="rock", choices=["rock", "drop"],
                   help="rock: a rapid's surge slams a boulder and sheets up (default); drop: blob into a pool (crown)")
    p.add_argument("--cell", type=int, default=512)
    p.add_argument("--samples", type=int, default=192)
    p.add_argument("--frames", default=None)
    p.add_argument("--bake-only", action="store_true")
    p.add_argument("--preview", action="store_true")
    return p.parse_args(a)


def box(name, x, y, z):
    me = bpy.data.meshes.new(name)
    v = [(xx, yy, zz) for xx in x for yy in y for zz in z]
    f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    me.from_pydata(v, [], f)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def water_material():
    mat = bpy.data.materials.new("M_SprayWater")
    mat.use_nodes = True
    t = mat.node_tree
    t.nodes.clear()
    bs = B.node(t, "ShaderNodeBsdfPrincipled", (0, 0))
    B.inp(bs, "Base Color").default_value = (0.95, 0.96, 0.97, 1)
    B.inp(bs, "Roughness").default_value = 0.3
    B.inp(bs, "Specular IOR Level").default_value = 0.6
    # whitewater is aerated: light passes through thin sheets (back / top light glows through like the sheet)
    tl = B.node(t, "ShaderNodeBsdfTranslucent", (0, -200))
    B.inp(tl, "Color").default_value = (0.95, 0.96, 0.97, 1)
    ww = B.node(t, "ShaderNodeMixShader", (150, -100))
    ww.inputs[0].default_value = 0.45
    B.link(t, B.out(bs, "BSDF"), ww.inputs[1])
    B.link(t, B.out(tl, "BSDF"), ww.inputs[2])
    tr = B.node(t, "ShaderNodeBsdfTransparent", (0, 200))
    tc = B.node(t, "ShaderNodeTexCoord", (-600, 0))
    sep = B.node(t, "ShaderNodeSeparateXYZ", (-400, 0))
    B.link(t, B.out(tc, "Object"), sep.inputs[0])
    mr = B.node(t, "ShaderNodeMapRange", (-200, 200))
    B.link(t, sep.outputs[2], B.inp(mr, "Value"))
    # the surge ring round the crater reads as a flat slab side-on: fade it (and the pool) out below +0.30,
    # with a noise-broken edge so the splash base is foamy, not cut
    nz = B.node(t, "ShaderNodeTexNoise", (-700, 150))
    B.link(t, B.out(tc, "Object"), B.inp(nz, "Vector"))
    B.inp(nz, "Scale").default_value = 9.0
    B.inp(nz, "Detail").default_value = 4.0
    zj = B.node(t, "ShaderNodeMath", (-400, 150), operation="MULTIPLY_ADD")
    B.link(t, B.out(nz, "Factor"), zj.inputs[0])
    zj.inputs[1].default_value = 0.18
    B.link(t, sep.outputs[2], zj.inputs[2])
    B.link(t, zj.outputs[0], B.inp(mr, "Value"))
    B.inp(mr, "From Min").default_value = BASE_Z + 0.14
    B.inp(mr, "From Max").default_value = BASE_Z + 0.38
    mr.interpolation_type = "SMOOTHSTEP"
    # and fade toward the sprite window's side edges (|x| 0.8 -> 1.0)
    cxs = B.node(t, "ShaderNodeMath", (-500, 350), operation="SUBTRACT")
    B.link(t, sep.outputs[0], cxs.inputs[0])
    cxs.inputs[1].default_value = CX
    ax = B.node(t, "ShaderNodeMath", (-400, 350), operation="ABSOLUTE")
    B.link(t, cxs.outputs[0], ax.inputs[0])
    mx = B.node(t, "ShaderNodeMapRange", (-200, 400))
    B.link(t, ax.outputs[0], B.inp(mx, "Value"))
    B.inp(mx, "From Min").default_value = WINDOW / 2
    B.inp(mx, "From Max").default_value = WINDOW / 2 - 0.15
    mx.interpolation_type = "SMOOTHSTEP"
    fm0 = B.node(t, "ShaderNodeMath", (0, 300), operation="MULTIPLY")
    B.link(t, B.out(mr, "Result"), fm0.inputs[0])
    B.link(t, B.out(mx, "Result"), fm0.inputs[1])
    # keep the splash, drop the still / slowly heaving pool: alpha by speed (0.6 -> 2.0 m/s)
    va = B.node(t, "ShaderNodeAttribute", (-600, 500))
    va.attribute_name = "velocity"
    vl_ = B.node(t, "ShaderNodeVectorMath", (-400, 500), operation="LENGTH")
    B.link(t, B.out(va, "Vector"), vl_.inputs[0])
    ms = B.node(t, "ShaderNodeMapRange", (-200, 550))
    B.link(t, B.out(vl_, "Value"), B.inp(ms, "Value"))
    B.inp(ms, "From Min").default_value = 0.6
    B.inp(ms, "From Max").default_value = 2.0
    ms.interpolation_type = "SMOOTHSTEP"
    fm = B.node(t, "ShaderNodeMath", (100, 350), operation="MULTIPLY")
    B.link(t, fm0.outputs[0], fm.inputs[0])
    # (the baked 'velocity' attribute reads 0 with cache_type ALL, so the speed fade is off); instead a per-frame
    # life value fades the settling water out over the last 40 % of the flipbook
    lifev = B.node(t, "ShaderNodeValue", (-100, 600))
    lifev.name = "life"
    lifev.outputs[0].default_value = 1.0
    B.link(t, lifev.outputs[0], fm.inputs[1])
    mix = B.node(t, "ShaderNodeMixShader", (200, 100))
    B.link(t, fm.outputs[0], mix.inputs[0])
    B.link(t, B.out(tr, "BSDF"), mix.inputs[1])
    B.link(t, ww.outputs[0], mix.inputs[2])
    mo = B.node(t, "ShaderNodeOutputMaterial", (400, 100))
    B.link(t, mix.outputs[0], B.inp(mo, "Surface"))
    return mat


def build_rock(res):
    """The river case: a surge of water runs into a boulder (collision) and throws a sheet / column up its face."""
    global FIRST, LAST, CX
    FIRST, LAST = 22, 85
    CX = 0.28
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 1, LAST
    sc.gravity = (0, 0, -9.81)
    dom = box("Domain", (-1.7, 1.7), (-0.7, 0.7), (-1, 1))
    md = dom.modifiers.new("Fluid", "FLUID")
    md.fluid_type = "DOMAIN"
    d = md.domain_settings
    d.domain_type = "LIQUID"
    d.resolution_max = res
    d.use_mesh = True
    d.mesh_particle_radius = 1.2
    d.mesh_scale = 2
    d.use_adaptive_timesteps = True
    d.cfl_condition = 2.0
    d.timesteps_max = 8
    d.cache_type = "ALL"
    d.cache_frame_start, d.cache_frame_end = 1, LAST
    cache = fx.SRC_TEX / f"SpraySim_rock_cache_r{res}"
    cache.mkdir(parents=True, exist_ok=True)
    d.cache_directory = str(cache)
    pool = box("Pool", (-1.9, 1.9), (-0.8, 0.8), (-1.2, BASE_Z))
    fp = pool.modifiers.new("Fluid", "FLUID")
    fp.fluid_type = "FLOW"
    fp.flow_settings.flow_type = "LIQUID"
    fp.flow_settings.flow_behavior = "GEOMETRY"
    fp.flow_settings.flow_source = "MESH"
    surge = box("Surge", (-1.75, -1.35), (-0.45, 0.45), (BASE_Z - 0.05, BASE_Z + 0.16))
    fs_ = surge.modifiers.new("Fluid", "FLUID")
    fs_.fluid_type = "FLOW"
    f = fs_.flow_settings
    f.flow_type = "LIQUID"
    f.flow_behavior = "INFLOW"
    f.flow_source = "MESH"
    f.use_initial_velocity = True
    f.velocity_coord = (6.5, 0.0, 0.6)
    f.use_inflow = True
    f.keyframe_insert("use_inflow", frame=1)
    f.use_inflow = False
    f.keyframe_insert("use_inflow", frame=20)
    out = box("Drain", (1.45, 1.75), (-0.8, 0.8), (-1.2, 1.0))
    fo = out.modifiers.new("Fluid", "FLUID")
    fo.fluid_type = "FLOW"
    fo.flow_settings.flow_type = "LIQUID"
    fo.flow_settings.flow_behavior = "OUTFLOW"
    fo.flow_settings.flow_source = "MESH"
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=(0.15, 0.0, BASE_Z - 0.02), segments=32, ring_count=16)
    rock = bpy.context.active_object
    rock.name = "Rock"
    rock.scale = (0.34, 0.46, 0.40)
    rock.rotation_euler = (0.0, 0.25, 0.0)  # face leaning back toward the surge: the sheet runs up it
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    fe = rock.modifiers.new("Fluid", "FLUID")
    fe.fluid_type = "EFFECTOR"
    fe.effector_settings.effector_type = "COLLISION"
    for o in (pool, surge, out, rock):
        o.hide_render = True
    return sc, dom


def build(res):
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 1, LAST
    sc.gravity = (0, 0, -9.81)
    dom = box("Domain", (-1.7, 1.7), (-0.7, 0.7), (-1, 1))  # wider than the sprite window: no wall slosh in view
    md = dom.modifiers.new("Fluid", "FLUID")
    md.fluid_type = "DOMAIN"
    d = md.domain_settings
    d.domain_type = "LIQUID"
    d.resolution_max = res
    d.use_mesh = True
    d.use_speed_vectors = True  # mesh 'velocity' attribute: the shader keeps only moving water
    d.mesh_particle_radius = 1.2
    d.mesh_scale = 2
    d.use_adaptive_timesteps = True
    d.cfl_condition = 2.0
    d.timesteps_max = 8
    d.cache_type = "ALL"
    d.cache_frame_start, d.cache_frame_end = 1, LAST
    cache = fx.SRC_TEX / f"SpraySim_cache_r{res}"
    cache.mkdir(parents=True, exist_ok=True)
    d.cache_directory = str(cache)
    pool = box("Pool", (-1.9, 1.9), (-0.8, 0.8), (-1.2, BASE_Z))
    fp = pool.modifiers.new("Fluid", "FLUID")
    fp.fluid_type = "FLOW"
    fp.flow_settings.flow_type = "LIQUID"
    fp.flow_settings.flow_behavior = "GEOMETRY"
    fp.flow_settings.flow_source = "MESH"
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.18, location=(0.05, 0.0, BASE_Z + 0.45), segments=24, ring_count=12)
    blob = bpy.context.active_object
    blob.name = "Blob"
    blob.scale = (1.0, 1.0, 1.3)
    fb = blob.modifiers.new("Fluid", "FLUID")
    fb.fluid_type = "FLOW"
    fs = fb.flow_settings
    fs.flow_type = "LIQUID"
    fs.flow_behavior = "GEOMETRY"
    fs.flow_source = "MESH"
    fs.use_initial_velocity = True
    fs.velocity_coord = (0.7, 0.0, -8.5)  # angled strike: the crown leans like the sheet's
    for o in (pool, blob):
        o.hide_render = True
    return sc, dom


def main():
    a = args()
    sc = B.reset_scene()
    sc, dom = build_rock(a.res) if a.scene == "rock" else build(a.res)
    for o in bpy.context.view_layer.objects:
        o.select_set(o == dom)
    bpy.context.view_layer.objects.active = dom
    d = dom.modifiers["Fluid"].domain_settings
    if not d.has_cache_baked_any:
        t0 = time.time()
        with bpy.context.temp_override(object=dom, active_object=dom, selected_objects=[dom]):
            bpy.ops.fluid.bake_all()
        print(f"BAKE res {a.res} {time.time() - t0:.1f}s")
    if a.bake_only:
        return
    # render setup on top of the flipbook scene conventions (six light groups, ortho, transparent)
    RF_sc = sc
    B.cycles(sc, samples=a.samples, res=(a.cell, a.cell), transparent=True, denoise=False, view="Standard")
    sc.cycles.volume_step_rate = 0.5
    sc.cycles.max_bounces = 8
    sc.cycles.transparent_max_bounces = 32
    sc.cycles.use_adaptive_sampling = False
    sc.render.image_settings.media_type = "MULTI_LAYER_IMAGE"
    sc.render.image_settings.file_format = "OPEN_EXR_MULTILAYER"
    sc.render.image_settings.color_depth = "16"
    w = bpy.data.worlds.new("Black")
    sc.world = w
    w.use_nodes = True
    next(n for n in w.node_tree.nodes if n.type == "BACKGROUND").inputs["Strength"].default_value = 0.0
    from mathutils import Vector
    vl = sc.view_layers[0]
    for name, dvec in RF.LIGHTS.items():
        vl.lightgroups.add(name=name)
        ld = bpy.data.lights.new(name, "SUN")
        ld.energy = 3.0
        ld.angle = math.radians(10)
        ob = bpy.data.objects.new(name, ld)
        sc.collection.objects.link(ob)
        ob.rotation_euler = Vector(dvec).to_track_quat("Z", "Y").to_euler()
        ob.lightgroup = name
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.type = "ORTHO"
    # frame the splash (the sim domain is wider than the sprite): window 1.3 units, base 7 % above the bottom
    cam.data.ortho_scale = WINDOW
    cam.location = (CX, -5, BASE_Z - 0.03 + WINDOW / 2 - 0.02)
    cam.rotation_euler = (math.pi / 2, 0, 0)
    dom.data.materials.clear()
    dom.data.materials.append(water_material())
    # fine droplets + base mist from the particle version (the sheets now come from the sim)
    upd = RF.spray_setup(sc, seed=5, n_drops=1800, n_foam=2500)
    import render_flipbooks as _rf
    _rf.sheet_points = lambda T, seed: ([], [])  # no fake sheets: the liquid surface is the sheet
    k_ = WINDOW / 2.0  # the droplet / mist rig was authored in a 2-unit window with its base at -0.86
    for nm in ("Drops", "SprayMist"):
        o = bpy.data.objects[nm]
        o.scale = (k_, k_, k_)
        o.location = (CX - 0.05, 0.0, BASE_Z + 0.86 * k_)
    src = fx.SRC_TEX / "SprayBurst"
    src.mkdir(parents=True, exist_ok=True)
    f0, f1 = 0, LAST - FIRST
    if a.frames:
        f0, f1 = (int(v) for v in a.frames.split(","))
    for k in range(f0, f1 + 1):
        sc.frame_set(FIRST + k)
        T = k / (LAST - FIRST)
        # the droplet / mist rig starts when the surge hits the boulder (18 % into the rock flipbook)
        t0_ = 0.18 if a.scene == "rock" else 0.0
        drops = bpy.data.objects["Drops"]
        drops.hide_render = T < t0_
        n = upd(max(0.0, (T - t0_) / (1 - t0_)))
        wm = dom.data.materials[0] if dom.data.materials else None
        if wm is not None:
            wm.node_tree.nodes["life"].outputs[0].default_value = 1.0 - RF.smooth(0.55, 1.0, T)
        sc.render.filepath = str(src / f"SprayBurst_{k:03d}.exr")
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"FRAME SprayBurst {k} {time.time() - t0:.1f}s drops {n}")
        if a.preview:
            alpha, lg = RF.frame_passes(RF.read_exr(src / f"SprayBurst_{k:03d}.exr"))
            am = np.maximum(alpha, 1e-3)
            raw = (0.55 * lg["PZ"] + 0.35 * lg["NY"] + 0.25 * lg["PY"]) / am
            ref = float(np.percentile(raw[alpha > 0.05], 99)) if (alpha > 0.05).any() else 1.0
            lum = np.clip(raw / ref, 0, 1) * alpha
            fx.save_png(np.stack([lum, lum, lum], -1), fx.WORK / f"renders/flipbooks/preview/SprayBurst_{k:03d}.png")
    if not a.preview and a.frames is None:
        meta = RF.pack("SprayBurst", 64, 8, a.cell, {"method": "Mantaflow FLIP liquid sim res %d + droplet points + "
                                                             "mist volume" % a.res})
        path = fx.WORK / "json/flipbooks.json"
        old = fx.load_json(path) if path.exists() else {}
        old["SprayBurst"] = meta
        fx.write_json(path, old)
    print("DONE spray")


if __name__ == "__main__":
    main()
