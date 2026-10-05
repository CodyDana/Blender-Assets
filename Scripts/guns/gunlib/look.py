"""ROUGH LOOK: the review-only shader set for detail-pass renders (import inside Blender, Cycles).

Judges must compare DESIGN, not placeholder grey, so every review render from the detail pass on uses this look:
  RL_Steel   dark worn blued steel: blue-black base, roughness varied by two noise scales, fine directional
             scratches, slightly lighter / smoother worn edges from a Bevel-node edge mask
  RL_Wood    reddish-brown wood with procedural grain along the object's long axis (PCA of its vertices), plus
             broad colour variation and a light shellac coat
  backdrop   transparent film composited (plain Python) onto the reference panel's own fitted backdrop, so our crop
             sits on the same sheet-like grey; the world gives a neutral grey environment
  lights     soft key from the camera's upper left, weak fill from the right, rim from behind-above (placed relative
             to each shot's camera)
These are NOT the final textures (stage 5 bakes those); nothing here is exported.
Frames: objects live in frame B (metres); grain scales are per metre.
"""
from __future__ import annotations


import bpy
import numpy as np
from mathutils import Vector

STEEL_BASE = (50, 51, 55)          # sRGB, blue-black
STEEL_EDGE = (132, 133, 136)       # worn edges
WOOD_DARK = (62, 26, 13)
WOOD_LIGHT = (112, 52, 28)


def srgb_to_lin(c):
    c = np.asarray(c, float) / 255.0
    return tuple(float(v) for v in np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4))


def _inp(node, name, typ=None):
    for s in node.inputs:
        if s.name == name and (typ is None or s.type == typ) and s.enabled:
            return s
    for s in node.inputs:
        if s.name == name and (typ is None or s.type == typ):
            return s
    raise KeyError(f"{node.bl_idname} has no input {name} ({typ})")


def _out(node, name, typ=None):
    for s in node.outputs:
        if s.name == name and (typ is None or s.type == typ):
            return s
    raise KeyError(f"{node.bl_idname} has no output {name}")


def _fac(node):
    """Texture factor output ("Factor" in Blender 5.x, "Fac" before)."""
    for nm in ("Factor", "Fac"):
        for s in node.outputs:
            if s.name == nm:
                return s
    raise KeyError(f"{node.bl_idname} has no factor output")


def _set(node, name, value):
    try:
        _inp(node, name).default_value = value
    except KeyError:
        pass


def _mix_rgb(nt, fac, a, b):
    m = nt.nodes.new("ShaderNodeMix")
    m.data_type = "RGBA"
    L = nt.links
    if isinstance(fac, (int, float)):
        _inp(m, "Factor", "VALUE").default_value = fac
    else:
        L.new(fac, _inp(m, "Factor", "VALUE"))
    for nm, v in (("A", a), ("B", b)):
        s = _inp(m, nm, "RGBA")
        if isinstance(v, tuple):
            s.default_value = (*v, 1.0)
        else:
            L.new(v, s)
    return _out(m, "Result", "RGBA")


def _maprange(nt, val, a, b, c=0.0, d=1.0):
    m = nt.nodes.new("ShaderNodeMapRange")
    nt.links.new(val, _inp(m, "Value", "VALUE"))
    _inp(m, "From Min", "VALUE").default_value = a
    _inp(m, "From Max", "VALUE").default_value = b
    _inp(m, "To Min", "VALUE").default_value = c
    _inp(m, "To Max", "VALUE").default_value = d
    m.clamp = True
    return _out(m, "Result", "VALUE")


def _noise(nt, vec, scale, detail=4.0, rough=0.55):
    n = nt.nodes.new("ShaderNodeTexNoise")
    if vec is not None:
        nt.links.new(vec, _inp(n, "Vector"))
    _set(n, "Scale", scale)
    _set(n, "Detail", detail)
    _set(n, "Roughness", rough)
    return n


def _new_mat(name):
    m = bpy.data.materials.get(name)
    if m is not None:
        bpy.data.materials.remove(m)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    return m, nt, bsdf


def rough_steel(name="RL_Steel", base=STEEL_BASE, edge=STEEL_EDGE, edge_mm=0.5):
    m, nt, bsdf = _new_mat(name)
    L = nt.links
    tc = nt.nodes.new("ShaderNodeTexCoord")
    obj = _out(tc, "Object")
    # edge mask: 1 - N_bevel . N  (Cycles Bevel node), mapped to 0..1
    bev = nt.nodes.new("ShaderNodeBevel")
    _set(bev, "Radius", edge_mm / 1000.0)
    bev.samples = 8
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    dot = nt.nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    L.new(_out(bev, "Normal"), dot.inputs[0])
    L.new(_out(geo, "Normal"), dot.inputs[1])
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    L.new(_out(dot, "Value"), inv.inputs[1])
    # break the edge mask up with noise so the wear is patchy
    nwear = _noise(nt, obj, 260.0, 3.0, 0.6)
    wear = nt.nodes.new("ShaderNodeMath")
    wear.operation = "MULTIPLY"
    L.new(_maprange(nt, _out(inv, "Value", "VALUE"), 0.004, 0.06), wear.inputs[0])
    L.new(_maprange(nt, _fac(nwear), 0.35, 0.7, 0.25, 1.0), wear.inputs[1])
    wearv = _out(wear, "Value")
    # fine directional scratches: noise on coordinates stretched along a slant
    mp = nt.nodes.new("ShaderNodeMapping")
    L.new(obj, _inp(mp, "Vector"))
    _inp(mp, "Rotation").default_value = (0.3, 0.7, 0.45)
    _inp(mp, "Scale").default_value = (90.0, 1100.0, 900.0)
    nsc = _noise(nt, _out(mp, "Vector"), 1.0, 2.0, 0.5)
    scr = _maprange(nt, _fac(nsc), 0.70, 0.76, 0.0, 0.7)
    # roughness: two noise scales
    nr1 = _noise(nt, obj, 45.0, 4.0, 0.6)
    nr2 = _noise(nt, obj, 300.0, 2.0, 0.5)
    r1 = _maprange(nt, _fac(nr1), 0.3, 0.7, 0.42, 0.64)     # detail fix: 0.34-0.58 -> 0.42-0.64 (no polished / chrome
                                                             # read on small curved parts: brake, trigger, pins)
    r2 = _maprange(nt, _fac(nr2), 0.3, 0.7, -0.06, 0.06)
    radd = nt.nodes.new("ShaderNodeMath")
    radd.operation = "ADD"
    L.new(r1, radd.inputs[0])
    L.new(r2, radd.inputs[1])
    rsub = nt.nodes.new("ShaderNodeMath")
    rsub.operation = "MULTIPLY_ADD"
    L.new(wearv, rsub.inputs[0])
    rsub.inputs[1].default_value = -0.18
    L.new(_out(radd, "Value"), rsub.inputs[2])
    rs2 = nt.nodes.new("ShaderNodeMath")
    rs2.operation = "MULTIPLY_ADD"
    L.new(scr, rs2.inputs[0])
    rs2.inputs[1].default_value = -0.12
    L.new(_out(rsub, "Value"), rs2.inputs[2])
    L.new(_out(rs2, "Value"), _inp(bsdf, "Roughness"))
    # colour: blue-black base, faint mottling, scratches and worn edges lighter
    ncol = _noise(nt, obj, 30.0, 3.0, 0.6)
    mot = _maprange(nt, _fac(ncol), 0.3, 0.7, 0.0, 1.0)
    c0 = _mix_rgb(nt, mot, srgb_to_lin(tuple(v * 0.8 for v in base)), srgb_to_lin(base))
    c1 = _mix_rgb(nt, scr, c0, srgb_to_lin(tuple(min(255, v * 1.9) for v in base)))
    c2 = _mix_rgb(nt, wearv, c1, srgb_to_lin(edge))
    L.new(c2, _inp(bsdf, "Base Color"))
    _set(bsdf, "Metallic", 0.88)
    _set(bsdf, "Specular IOR Level", 0.5)
    m.diffuse_color = (*srgb_to_lin(base), 1.0)
    return m


def rough_wood(name="RL_Wood", axis=(1.0, 0.0, 0.0)):
    """Wood with grain along `axis` (object space)."""
    m, nt, bsdf = _new_mat(name)
    L = nt.links
    tc = nt.nodes.new("ShaderNodeTexCoord")
    q = Vector(axis).normalized().rotation_difference(Vector((1.0, 0.0, 0.0)))
    rot = nt.nodes.new("ShaderNodeMapping")
    L.new(_out(tc, "Object"), _inp(rot, "Vector"))
    _inp(rot, "Rotation").default_value = q.to_euler("XYZ")
    st = nt.nodes.new("ShaderNodeMapping")
    L.new(_out(rot, "Vector"), _inp(st, "Vector"))
    _inp(st, "Scale").default_value = (9.0, 700.0, 700.0)            # grain ~ 1.5 mm apart, streaks ~ 110 mm long
    g = _noise(nt, _out(st, "Vector"), 1.0, 6.0, 0.62)
    _set(g, "Distortion", 0.6)
    grain = _maprange(nt, _fac(g), 0.38, 0.7, 0.0, 0.7)
    st2 = nt.nodes.new("ShaderNodeMapping")
    L.new(_out(rot, "Vector"), _inp(st2, "Vector"))
    _inp(st2, "Scale").default_value = (3.0, 40.0, 40.0)
    b = _noise(nt, _out(st2, "Vector"), 1.0, 3.0, 0.5)
    broad = _maprange(nt, _fac(b), 0.3, 0.7, 0.0, 1.0)
    c0 = _mix_rgb(nt, broad, srgb_to_lin(tuple(v * 0.85 for v in WOOD_LIGHT)), srgb_to_lin(WOOD_LIGHT))
    c1 = _mix_rgb(nt, grain, c0, srgb_to_lin(WOOD_DARK))
    L.new(c1, _inp(bsdf, "Base Color"))
    _set(bsdf, "Metallic", 0.0)
    rr = _maprange(nt, grain, 0.0, 1.0, 0.42, 0.6)
    L.new(rr, _inp(bsdf, "Roughness"))
    _set(bsdf, "Coat Weight", 0.18)
    _set(bsdf, "Coat Roughness", 0.3)
    m.diffuse_color = (*srgb_to_lin(WOOD_LIGHT), 1.0)
    return m


def long_axis(ob):
    V = np.array([v.co[:] for v in ob.data.vertices])
    if len(V) < 3:
        return (1.0, 0.0, 0.0)
    V = V - V.mean(0)
    w, U = np.linalg.eigh(V.T @ V)
    a = U[:, -1]
    if a[np.argmax(np.abs(a))] < 0:
        a = -a
    return tuple(float(x) for x in a)


STEEL_WORN_BASE = (80, 80, 82)     # sRGB: lacquer scratched through to bare steel (e.g. a butt plate's finish)
STEEL_WORN_EDGE = (168, 168, 170)


def apply_rough_look(objs, is_wood, worn=()):
    """Steel on everything except objects for which is_wood(ob) is true (wood, per-object grain axis); objects named
    in `worn` get the lighter worn steel (a finish the spec records as more bare than the rest)."""
    steel = rough_steel()
    worn_m = rough_steel("RL_SteelWorn", STEEL_WORN_BASE, STEEL_WORN_EDGE) if worn else None
    for ob in objs:
        if ob.type != "MESH":
            continue
        ob.data.materials.clear()
        if is_wood(ob):
            ob.data.materials.append(rough_wood(f"RL_Wood_{ob.name}", long_axis(ob)))
        else:
            ob.data.materials.append(worn_m if ob.name in set(worn) else steel)


def rough_world(sc, rgb_srgb=(126, 126, 126), env=0.45):
    w = bpy.data.worlds.new("RL_World")
    sc.world = w
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (*srgb_to_lin(rgb_srgb), 1.0)
    bg.inputs["Strength"].default_value = env
    sc.render.film_transparent = True
    return w


def clear_lights():
    for ob in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        bpy.data.objects.remove(ob, do_unlink=True)


def _area(name, loc, target, size, energy):
    ld = bpy.data.lights.new(name, "AREA")
    ld.size = size
    ld.energy = energy
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return ob


def rough_lights(cam_ob, target_B, dist=1.1, k=1.0):
    """Soft key from the camera's upper left (toward the camera), weak fill from the right, rim from behind-above."""
    clear_lights()
    Mw = cam_ob.matrix_world
    right = Vector(Mw.col[0][:3]).normalized()
    up = Vector(Mw.col[1][:3]).normalized()
    back = Vector(Mw.col[2][:3]).normalized()         # camera looks along -Z: +Z points back toward the viewer
    t = Vector(target_B)

    def at(r, u, b):
        d = (right * r + up * u + back * b).normalized()
        return t + d * dist
    _area("RL_Key", at(-0.62, 0.62, 0.48), t, 1.3, 30.0 * k)
    _area("RL_Fill", at(0.85, -0.15, 0.5), t, 1.6, 7.0 * k)
    _area("RL_Top", at(0.0, 1.0, -0.15), t, 1.4, 10.0 * k)
    _area("RL_Rim", at(0.35, 0.45, -0.85), t, 1.0, 10.0 * k)
