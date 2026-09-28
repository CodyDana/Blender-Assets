"""BlackCloak v2 materials for Blender (every stage-1/stage-2 render builds its materials through this module).

Reads Scripts/garments/blackcloak_v2/material_params.json (the one parameter set shared with the Unreal side) and the
maps in Exports/Garments/BlackCloak_MH_v2/Textures/.  Blender 5.2, Cycles/EEVEE.  Nodes are found by type, never by
name.  Use:

    import sys; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/Scripts/garments/blackcloak_v2")
    import bcv2_material as BM
    P = BM.load_params()
    cloth = BM.cloth_material(P)             # M_BlackCloakV2_Cloth (cloth panels + skinned wool share it)
    fray = BM.fray_material(P)               # M_BlackCloakV2_Fray  (alpha edge cards, optional 4th slot)
    clasp = BM.clasp_material(P)             # M_BlackCloakV2_Clasp (hard button)
    lining = BM.cloth_material(P, lining=True)   # optional: same maps, darker (lining/under-layer), same slot rules

Conventions:
* UV0 of the wool is true scale in TILES: u = pattern metres / tile_m (0.45 m); `uv_scale` (default 1.0) multiplies.
  Pattern pieces authored in plain metres use uv_scale = 1 / tile_m.
* Normal map on disk is DirectX (green down); the builder flips green for Blender (OpenGL) inside the graph.
* The ORM R channel (cavity AO) is not wired in Blender: Cycles computes occlusion; Unreal uses it for indirect light.
* Single-layer cloth is two-sided: backface culling off here, Two Sided on in Unreal.
"""
import json
import os
import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
PARAMS = os.path.join(HERE, "material_params.json")
PROJECT = "C:/Users/Cody/Desktop/Blender_Projects"


def load_params(path=PARAMS):
    with open(path) as f:
        return json.load(f)


def _tex_dir(P):
    d = P["texture_dir"]
    return d if os.path.isabs(d) else os.path.join(PROJECT, d)


def _img(P, key, colourspace, tex_dir=None):
    fn = os.path.join(tex_dir or _tex_dir(P), P["textures"][key])
    img = bpy.data.images.load(fn, check_existing=True)
    img.colorspace_settings.name = colourspace
    if key == "fray_bca":
        img.alpha_mode = "STRAIGHT"
    return img


def _principled(nt):
    return next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")


def _set(bsdf, name, value):
    if name in bsdf.inputs:
        bsdf.inputs[name].default_value = value


def _uv_mapping(nt, uv_scale, uv_map=None):
    tc = nt.nodes.new("ShaderNodeUVMap")
    if uv_map:
        tc.uv_map = uv_map
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (uv_scale, uv_scale, 1.0)
    nt.links.new(tc.outputs["UV"], mp.inputs["Vector"])
    return mp.outputs["Vector"]


def _normal_dx(nt, img, vec, strength):
    """DirectX normal texture -> OpenGL tangent normal (flip green) -> Normal Map node."""
    tn = nt.nodes.new("ShaderNodeTexImage")
    tn.image = img
    tn.interpolation = "Linear"
    nt.links.new(vec, tn.inputs["Vector"])
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(tn.outputs["Color"], sep.inputs["Color"])
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    nt.links.new(sep.outputs[1], inv.inputs[1])
    com = nt.nodes.new("ShaderNodeCombineColor")
    nt.links.new(sep.outputs[0], com.inputs[0])
    nt.links.new(inv.outputs[0], com.inputs[1])
    nt.links.new(sep.outputs[2], com.inputs[2])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.inputs["Strength"].default_value = strength
    nt.links.new(com.outputs["Color"], nm.inputs["Color"])
    return nm.outputs["Normal"]


def _new_mat(name):
    old = bpy.data.materials.get(name)
    if old is not None:
        old.name = name + "_old"
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    m.use_backface_culling = False
    return m


def cloth_material(P, name=None, uv_map=None, lining=False, tex_dir=None, overrides=None):
    """The wool. overrides: dict of blender-param overrides (for calibration rounds only)."""
    c = dict(P["cloth"]["blender"])
    if lining:
        c.update(P["lining"]["blender_overrides"])
    if overrides:
        c.update(overrides)
    m = _new_mat(name or (P["lining"]["name"] if lining else P["cloth"]["name"]))
    nt = m.node_tree
    b = _principled(nt)
    vec = _uv_mapping(nt, c["uv_scale"], uv_map)
    tb = nt.nodes.new("ShaderNodeTexImage")
    tb.image = _img(P, "cloth_bc", "sRGB", tex_dir)
    nt.links.new(vec, tb.inputs["Vector"])
    col = tb.outputs["Color"]
    if abs(c.get("albedo_multiplier", 1.0) - 1.0) > 1e-9:          # lining darkening / calibration only
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs["Factor"].default_value = 1.0
        nt.links.new(col, mul.inputs[6])
        v = c["albedo_multiplier"]
        mul.inputs[7].default_value = (v, v, v, 1.0)
        col = mul.outputs[2]
    nt.links.new(col, b.inputs["Base Color"])
    to = nt.nodes.new("ShaderNodeTexImage")
    to.image = _img(P, "cloth_orm", "Non-Color", tex_dir)
    nt.links.new(vec, to.inputs["Vector"])
    so = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(to.outputs["Color"], so.inputs["Color"])
    ra = nt.nodes.new("ShaderNodeMath")
    ra.operation = "ADD"
    ra.use_clamp = True
    ra.inputs[1].default_value = c["roughness_adjust"]
    nt.links.new(so.outputs[1], ra.inputs[0])
    nt.links.new(ra.outputs[0], b.inputs["Roughness"])
    _set(b, "Metallic", 0.0)
    _set(b, "Specular IOR Level", c["specular_ior_level"])
    nt.links.new(_normal_dx(nt, _img(P, "cloth_n", "Non-Color", tex_dir), vec, c["normal_strength"]), b.inputs["Normal"])
    _set(b, "Sheen Weight", c["sheen_weight"])
    _set(b, "Sheen Roughness", c["sheen_roughness"])
    _set(b, "Sheen Tint", tuple(c["sheen_tint"]) + (1.0,))
    m["bcv2_params"] = json.dumps(c)
    return m


def fray_material(P, name=None, uv_map=None, tex_dir=None):
    c = dict(P["fray"]["blender"])
    m = _new_mat(name or P["fray"]["name"])
    nt = m.node_tree
    b = _principled(nt)
    vec = _uv_mapping(nt, c["uv_scale"], uv_map)
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = _img(P, "fray_bca", "sRGB", tex_dir)
    nt.links.new(vec, t.inputs["Vector"])
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(t.outputs["Alpha"], b.inputs["Alpha"])
    _set(b, "Roughness", c["roughness"])
    _set(b, "Specular IOR Level", c["specular_ior_level"])
    _set(b, "Sheen Weight", c["sheen_weight"])
    _set(b, "Sheen Roughness", c["sheen_roughness"])
    _set(b, "Sheen Tint", tuple(c["sheen_tint"]) + (1.0,))
    try:
        m.surface_render_method = "DITHERED"
    except Exception:
        pass
    return m


def clasp_material(P, name=None):
    c = dict(P["clasp"]["blender"])
    m = _new_mat(name or P["clasp"]["name"])
    b = _principled(m.node_tree)
    _set(b, "Base Color", tuple(c["base_colour_linear"]) + (1.0,))
    _set(b, "Metallic", c["metallic"])
    _set(b, "Roughness", c["roughness"])
    _set(b, "Specular IOR Level", c["specular_ior_level"])
    _set(b, "Coat Weight", c.get("coat_weight", 0.0))
    return m
