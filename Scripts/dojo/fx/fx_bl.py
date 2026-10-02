"""Blender-side helpers for the DojoFX build (bpy): scene setup, node helpers, petal materials, Cycles GPU."""
from __future__ import annotations

import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import fx_common as fx  # noqa: E402


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    return sc


def cycles(scene, samples=128, res=(1024, 1024), transparent=False, denoise=True, view="Standard"):
    scene.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for dev_type in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = dev_type
            prefs.get_devices()
            ok = False
            for d in prefs.devices:
                d.use = d.type == dev_type
                ok = ok or d.use
            if ok:
                scene.cycles.device = "GPU"
                break
        except TypeError:
            continue
    scene.cycles.samples = samples
    scene.cycles.use_denoising = denoise
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = transparent
    scene.view_settings.view_transform = view
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA" if transparent else "RGB"
    scene.render.image_settings.color_depth = "8"
    return scene


def node(tree, kind, loc=(0, 0), **props):
    n = tree.nodes.new(kind)
    n.location = loc
    for k, v in props.items():
        setattr(n, k, v)
    return n


def inp(n, name, kind=None):
    for s in n.inputs:
        if s.name == name and (kind is None or s.type == kind) and s.enabled:
            return s
    for s in n.inputs:
        if s.name == name and (kind is None or s.type == kind):
            return s
    raise KeyError(f"{n.bl_idname} has no input {name} ({kind})")


def out(n, name, kind=None):
    for s in n.outputs:
        if s.name == name and (kind is None or s.type == kind) and s.enabled:
            return s
    for s in n.outputs:
        if s.name == name and (kind is None or s.type == kind):
            return s
    raise KeyError(f"{n.bl_idname} has no output {name} ({kind})")


def mix_rgb(tree, fac, a, b, loc=(0, 0), blend="MIX"):
    m = node(tree, "ShaderNodeMix", loc, data_type="RGBA", blend_type=blend)
    link(tree, fac, inp(m, "Factor", "VALUE")) if not isinstance(fac, (int, float)) else None
    if isinstance(fac, (int, float)):
        inp(m, "Factor", "VALUE").default_value = fac
    for sock, val in ((inp(m, "A", "RGBA"), a), (inp(m, "B", "RGBA"), b)):
        if isinstance(val, (tuple, list)):
            sock.default_value = val
        else:
            link(tree, val, sock)
    return out(m, "Result", "RGBA")


def link(tree, a, b):
    tree.links.new(a, b)


def image(path, colorspace="sRGB", alpha_mode="STRAIGHT"):
    img = bpy.data.images.load(str(path), check_existing=True)
    img.colorspace_settings.name = colorspace
    img.alpha_mode = alpha_mode
    return img


def tex(tree, img, loc, uv=None):
    t = node(tree, "ShaderNodeTexImage", loc, image=img, interpolation="Cubic")
    if uv is not None:
        link(tree, uv, inp(t, "Vector"))
    return t


def dx_normal(tree, tex_node, loc, strength=1.0):
    """DirectX normal texture -> Blender (OpenGL) tangent normal."""
    sep = node(tree, "ShaderNodeSeparateColor", (loc[0], loc[1]))
    link(tree, out(tex_node, "Color"), inp(sep, "Color"))
    inv = node(tree, "ShaderNodeMath", (loc[0] + 160, loc[1] - 40), operation="SUBTRACT")
    inv.inputs[0].default_value = 1.0
    link(tree, out(sep, "Green"), inv.inputs[1])
    comb = node(tree, "ShaderNodeCombineColor", (loc[0] + 320, loc[1]))
    link(tree, out(sep, "Red"), inp(comb, "Red"))
    link(tree, inv.outputs[0], inp(comb, "Green"))
    link(tree, out(sep, "Blue"), inp(comb, "Blue"))
    nm = node(tree, "ShaderNodeNormalMap", (loc[0] + 480, loc[1]))
    inp(nm, "Strength").default_value = strength
    link(tree, out(comb, "Color"), inp(nm, "Color"))
    return out(nm, "Normal")


def petal_material(name, prefix, has_back=True, translucency=0.8):
    """Two-sided masked petal: front/back BC via Backfacing, DX normal, ORM roughness, SSS-driven translucency."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = False
    tree = mat.node_tree
    tree.nodes.clear()
    T = fx.TEX
    bc = tex(tree, image(T / f"T_DKF_{prefix}_BC.png"), (-1200, 300))
    bk = tex(tree, image(T / f"T_DKF_{prefix}Back_BC.png"), (-1200, 0)) if has_back else bc
    nt = tex(tree, image(T / f"T_DKF_{prefix}_N.png", "Non-Color"), (-1200, -300))
    orm = tex(tree, image(T / f"T_DKF_{prefix}_ORM.png", "Non-Color"), (-1200, -600))
    sss = tex(tree, image(T / f"T_DKF_{prefix}_SSS.png", "Non-Color"), (-1200, -900))
    geo = node(tree, "ShaderNodeNewGeometry", (-1000, 500))
    if has_back:
        col = mix_rgb(tree, out(geo, "Backfacing"), out(bc, "Color"), out(bk, "Color"), (-800, 300))
    else:
        dark = mix_rgb(tree, 0.0, out(bc, "Color"), (0.8, 0.8, 0.8, 1), (-900, 150), blend="MULTIPLY")
        col = mix_rgb(tree, out(geo, "Backfacing"), out(bc, "Color"), dark, (-800, 300))
    nrm = dx_normal(tree, nt, (-1000, -300))
    sep = node(tree, "ShaderNodeSeparateColor", (-900, -600))
    link(tree, out(orm, "Color"), inp(sep, "Color"))
    bsdf = node(tree, "ShaderNodeBsdfPrincipled", (-300, 200))
    link(tree, col, inp(bsdf, "Base Color"))
    link(tree, out(sep, "Green"), inp(bsdf, "Roughness"))
    link(tree, nrm, inp(bsdf, "Normal"))
    inp(bsdf, "Specular IOR Level").default_value = 0.35
    tr = node(tree, "ShaderNodeBsdfTranslucent", (-300, -300))
    tcol = mix_rgb(tree, 1.0, col, out(sss, "Color"), (-600, -300), blend="MULTIPLY")
    link(tree, tcol, inp(tr, "Color"))
    link(tree, nrm, inp(tr, "Normal"))
    fac = node(tree, "ShaderNodeMath", (-600, -520), operation="MULTIPLY")
    link(tree, out(sss, "Color"), fac.inputs[0])
    fac.inputs[1].default_value = translucency
    # transmission is ADDED on top of the reflection (Unreal Two Sided Foliage / Substrate two-sided wrap
    # behaviour), so a petal lit from the front reads at its albedo and a back-lit one glows
    trw = node(tree, "ShaderNodeMixShader", (-100, -250))
    link(tree, fac.outputs[0], trw.inputs[0])
    link(tree, out(tr, "BSDF"), trw.inputs[2])
    mix = node(tree, "ShaderNodeAddShader", (0, 0))
    link(tree, out(bsdf, "BSDF"), mix.inputs[0])
    link(tree, trw.outputs[0], mix.inputs[1])
    transp = node(tree, "ShaderNodeBsdfTransparent", (0, 250))
    cut = node(tree, "ShaderNodeMath", (-300, 450), operation="GREATER_THAN")
    link(tree, out(bc, "Alpha"), cut.inputs[0])
    cut.inputs[1].default_value = 0.5  # masked, like the Unreal material (opacity mask clip 0.5)
    mix2 = node(tree, "ShaderNodeMixShader", (200, 100))
    link(tree, cut.outputs[0], mix2.inputs[0])
    link(tree, out(transp, "BSDF"), mix2.inputs[1])
    link(tree, mix.outputs[0], mix2.inputs[2])
    mo = node(tree, "ShaderNodeOutputMaterial", (400, 100))
    link(tree, mix2.outputs[0], inp(mo, "Surface"))
    return mat


def simple_material(name, color, rough=0.6):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    b = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    return mat


def textured_material(name, bc_path, n_path=None, orm_path=None, scale=1.0, tint=(1, 1, 1), box=False):
    """A tiling PBR ground material from our own kit textures (object-space XY projection, metres / scale)."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    tc = node(tree, "ShaderNodeTexCoord", (-1400, 0))
    mp = node(tree, "ShaderNodeMapping", (-1200, 0))
    inp(mp, "Scale").default_value = (1 / scale, 1 / scale, 1 / scale)
    link(tree, out(tc, "Object"), inp(mp, "Vector"))
    bsdf = node(tree, "ShaderNodeBsdfPrincipled", (-200, 0))
    b = tex(tree, image(bc_path), (-900, 300), out(mp, "Vector"))
    boxes = [b]
    col = mix_rgb(tree, 1.0, out(b, "Color"), (*tint, 1), (-600, 300), blend="MULTIPLY")
    link(tree, col, inp(bsdf, "Base Color"))
    if n_path:
        n = tex(tree, image(n_path, "Non-Color"), (-900, -100), out(mp, "Vector"))
        boxes.append(n)
        link(tree, dx_normal(tree, n, (-700, -100)), inp(bsdf, "Normal"))
    if orm_path:
        o = tex(tree, image(orm_path, "Non-Color"), (-900, -500), out(mp, "Vector"))
        boxes.append(o)
        sep = node(tree, "ShaderNodeSeparateColor", (-600, -500))
        link(tree, out(o, "Color"), inp(sep, "Color"))
        link(tree, out(sep, "Green"), inp(bsdf, "Roughness"))
    if box:
        for t in boxes:
            t.projection = "BOX"
            t.projection_blend = 0.25
    mo = node(tree, "ShaderNodeOutputMaterial", (200, 0))
    link(tree, out(bsdf, "BSDF"), inp(mo, "Surface"))
    return mat


def look_at(obj, target):
    from mathutils import Vector
    d = Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def camera(name, loc, target, lens=50.0, ortho=None):
    cam_data = bpy.data.cameras.new(name)
    cam = bpy.data.objects.new(name, cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = loc
    look_at(cam, target)
    if ortho:
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = ortho
    else:
        cam_data.lens = lens
    cam_data.clip_start = 0.0005
    cam_data.clip_end = 500
    bpy.context.scene.camera = cam
    return cam


def world_color(scene, color, strength=1.0):
    w = bpy.data.worlds.new("W") if scene.world is None else scene.world
    scene.world = w
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (*color, 1)
    bg.inputs["Strength"].default_value = strength
    return w
