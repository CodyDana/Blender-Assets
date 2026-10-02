"""Blender preview materials for the pilot rocks: the same recipe the Unreal instances will use (catalog
"unreal_material"), so Blender renders show what the master will do. bpy only.

MI_DKR_<Rock> (master plan: M_ST_RockUnique, study 5.4):
  base   = GraniteDetail_BC (tiling, UV0 x m_per_uv / tile) x Tint
  base   = lerp(base, MeanColour, Flatten)                       FlattenToMean: grain reads at 1-3 m, not terrazzo
  tone   = M.A signed: > 0.5 -> base x StainColour (tan iron weathering, never the base colour: owner),
                       < 0.5 -> base x GrimeColour (the sheet's dark grey weathering mottles)
  cavity = base x lerp(1, ORM.R, CavityDarken)
  lichen = lerp(base, LichenColour x grain, M.G x LichenAmount)
  wet    = base x lerp(1, WetDarken, M.B);  roughness -> WetRoughness
  moss   = lerp(base, MossDetail_BC x MossTint, M.R);  roughness -> 0.92
  normal = unique N (DirectX; green flipped here for Blender) + GraniteDetail height as a light bump
MI_DKR_RockMoss: cushion shells. MossDetail_BC in object space, sheen for the fuzz, roughness 0.92.
MI_DKR_GrassTuft: blade colour from vertex colour R (base -> tip), G (per-blade variation).
"""
from __future__ import annotations

from pathlib import Path

import bpy

PARAMS = {
    "Tint": (0.66, 0.60, 0.55),           # linear multiply on the neutral tile: the landscape-ref grey family,
                                          # hue ~28 deg, R/B ~1.2 (measured: ref_measure.json landscape crops)
    "StainColour": (0.78, 0.60, 0.40),   # tan / iron weathering (the sheet's brown, used as weathering only)
    "StainAmount": 0.85,
    "GrimeColour": (0.16, 0.155, 0.15),  # the sheet's dark grey weathering mottles and flecks
    "GrimeAmount": 0.85,
    "Flatten": 0.45,                     # FlattenToMean on the grain tile (study 5.4 step 1): kills the terrazzo
    "MeanColour": (0.416, 0.400, 0.377), # the grain tile's mean (linear)
    "CavityDarken": 0.55,
    "LichenColour": (0.60, 0.62, 0.55),  # pale grey-green rosettes and specks
    "LichenAmount": 0.9,
    "WetDarken": 0.30,
    "WetRoughness": 0.16,
    "MossTint": (0.85, 0.85, 0.70),
    "DetailBump": 0.22,
    "TileM": 1.0,
}


def _img(path, data):
    path = str(path)
    for im in bpy.data.images:
        if bpy.path.abspath(im.filepath) == path:
            return im
    im = bpy.data.images.load(path, check_existing=True)
    im.colorspace_settings.name = "Non-Color" if data else "sRGB"
    return im


def _socket(node, name, kind, out=False):
    socks = node.outputs if out else node.inputs
    for s in socks:
        if s.name == name and s.type == kind and s.enabled:
            return s
    for s in socks:
        if s.name == name and s.type == kind:
            return s
    raise KeyError(f"{node.bl_idname}: no {kind} socket {name}")


class G:
    def __init__(self, mat):
        self.nt = mat.node_tree
        for n in list(self.nt.nodes):
            self.nt.nodes.remove(n)
        self.N, self.L = self.nt.nodes, self.nt.links
        self.x = 0

    def node(self, kind, **kw):
        n = self.N.new(kind)
        n.location = (self.x, 0)
        self.x += 180
        for k, v in kw.items():
            setattr(n, k, v)
        return n

    def link(self, a, b):
        self.L.new(a, b)

    def mix(self, fac, a, b, blend="MIX"):
        """Colour mix; ``fac``/``a``/``b`` may be sockets or values."""
        m = self.node("ShaderNodeMix", data_type="RGBA", blend_type=blend)
        m.clamp_result = True
        f = m.inputs[0]
        A = _socket(m, "A", "RGBA")
        B = _socket(m, "B", "RGBA")
        for s, v in ((f, fac), (A, a), (B, b)):
            if isinstance(v, bpy.types.NodeSocket):
                self.link(v, s)
            elif isinstance(v, (tuple, list)):
                s.default_value = (*v, 1.0) if len(v) == 3 else v
            else:
                s.default_value = v
        return _socket(m, "Result", "RGBA", out=True)

    def mathf(self, op, a, b=0.0):
        m = self.node("ShaderNodeMath", operation=op)
        for s, v in ((m.inputs[0], a), (m.inputs[1], b)):
            if isinstance(v, bpy.types.NodeSocket):
                self.link(v, s)
            else:
                s.default_value = v
        return m.outputs[0]

    def tex(self, img, vec):
        t = self.node("ShaderNodeTexImage")
        t.image = img
        t.interpolation = "Linear"
        self.link(vec, t.inputs["Vector"])
        return t


def rock_material(name, maps, m_per_uv, P=None):
    """maps: dict N, ORM, M, DBC, DH, MOSS (paths). m_per_uv: metres per UV0 unit (the detail tile scale)."""
    P = dict(PARAMS, **(P or {}))
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    g = G(mat)
    out = g.node("ShaderNodeOutputMaterial")
    bsdf = g.node("ShaderNodeBsdfPrincipled")
    uv = g.node("ShaderNodeUVMap", uv_map="UVMap")
    mp = g.node("ShaderNodeMapping")
    s = m_per_uv / P["TileM"]
    mp.inputs["Scale"].default_value = (s, s, 1.0)
    g.link(uv.outputs["UV"], mp.inputs["Vector"])
    tN = g.tex(_img(maps["N"], True), uv.outputs["UV"])
    tORM = g.tex(_img(maps["ORM"], True), uv.outputs["UV"])
    tM = g.tex(_img(maps["M"], True), uv.outputs["UV"])
    tM.image.alpha_mode = "CHANNEL_PACKED"
    tD = g.tex(_img(maps["DBC"], False), mp.outputs["Vector"])
    tH = g.tex(_img(maps["DH"], True), mp.outputs["Vector"])
    # DirectX -> OpenGL for Blender: flip green
    sep = g.node("ShaderNodeSeparateColor")
    g.link(tN.outputs["Color"], sep.inputs["Color"])
    comb = g.node("ShaderNodeCombineColor")
    g.link(sep.outputs[0], comb.inputs[0])
    g.link(g.mathf("SUBTRACT", 1.0, sep.outputs[1]), comb.inputs[1])
    g.link(sep.outputs[2], comb.inputs[2])
    nm = g.node("ShaderNodeNormalMap", uv_map="UVMap")
    g.link(comb.outputs[0], nm.inputs["Color"])
    bump = g.node("ShaderNodeBump")
    bump.inputs["Strength"].default_value = P["DetailBump"]
    bump.inputs["Distance"].default_value = 0.003
    g.link(tH.outputs["Color"], bump.inputs["Height"])
    g.link(nm.outputs["Normal"], bump.inputs["Normal"])
    sORM = g.node("ShaderNodeSeparateColor")
    g.link(tORM.outputs["Color"], sORM.inputs["Color"])
    sM = g.node("ShaderNodeSeparateColor")
    g.link(tM.outputs["Color"], sM.inputs["Color"])
    moss, lichen, wet = sM.outputs[0], sM.outputs[1], sM.outputs[2]
    stain = tM.outputs["Alpha"]
    dcol = g.mix(P["Flatten"], tD.outputs["Color"], P["MeanColour"])
    base = g.mix(1.0, dcol, P["Tint"], "MULTIPLY")
    # M.A is a signed tone: > 0.5 tan stain, < 0.5 grime
    t2 = g.mathf("MULTIPLY", stain, 2.0)
    tanf = g.mathf("MAXIMUM", g.mathf("SUBTRACT", t2, 1.0), 0.0)
    grimef = g.mathf("MAXIMUM", g.mathf("SUBTRACT", 1.0, t2), 0.0)
    base = g.mix(g.mathf("MULTIPLY", tanf, P["StainAmount"]), base,
                 g.mix(1.0, base, P["StainColour"], "MULTIPLY"))
    base = g.mix(g.mathf("MULTIPLY", grimef, P["GrimeAmount"]), base,
                 g.mix(1.0, base, P["GrimeColour"], "MULTIPLY"))
    cav = g.mix(P["CavityDarken"], (1.0, 1.0, 1.0), sORM.outputs[0])
    base = g.mix(1.0, base, cav, "MULTIPLY")
    lum = g.node("ShaderNodeRGBToBW")
    g.link(tD.outputs["Color"], lum.inputs[0])
    lgrain = g.mix(1.0, P["LichenColour"], g.mix(0.5, (1, 1, 1), lum.outputs[0]), "MULTIPLY")
    base = g.mix(g.mathf("MULTIPLY", lichen, P["LichenAmount"]), base, lgrain)
    wetc = g.mix(wet, (1.0, 1.0, 1.0), (P["WetDarken"],) * 3)
    base = g.mix(1.0, base, wetc, "MULTIPLY")
    tMoss = g.tex(_img(maps["MOSS"], False), mp.outputs["Vector"])
    mossc = g.mix(1.0, tMoss.outputs["Color"], P["MossTint"], "MULTIPLY")
    base = g.mix(moss, base, mossc)
    rough = g.node("ShaderNodeMix", data_type="FLOAT")
    g.link(wet, rough.inputs[0])
    g.link(sORM.outputs[1], _socket(rough, "A", "VALUE"))
    _socket(rough, "B", "VALUE").default_value = P["WetRoughness"]
    rough2 = g.node("ShaderNodeMix", data_type="FLOAT")
    g.link(moss, rough2.inputs[0])
    g.link(_socket(rough, "Result", "VALUE", out=True), _socket(rough2, "A", "VALUE"))
    _socket(rough2, "B", "VALUE").default_value = 0.92
    g.link(base, bsdf.inputs["Base Color"])
    g.link(_socket(rough2, "Result", "VALUE", out=True), bsdf.inputs["Roughness"])
    g.link(bump.outputs["Normal"], bsdf.inputs["Normal"])
    g.link(bsdf.outputs[0], out.inputs["Surface"])
    mat["unreal_plan"] = "MI of M_ST_RockUnique; params as PARAMS in Scripts/dojo/rocks/rocks_material.py"
    return mat


def moss_material(maps, name="MI_DKR_RockMoss"):
    mat = bpy.data.materials.get(name)
    if mat is not None:
        return mat
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    g = G(mat)
    out = g.node("ShaderNodeOutputMaterial")
    bsdf = g.node("ShaderNodeBsdfPrincipled")
    tc = g.node("ShaderNodeTexCoord")
    mp = g.node("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (2.6, 2.6, 2.6)
    g.link(tc.outputs["Object"], mp.inputs["Vector"])
    t = g.tex(_img(maps["MOSS"], False), mp.outputs["Vector"])
    t.projection = "BOX"
    t.projection_blend = 0.3
    nz = g.node("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 3.0
    g.link(mp.outputs["Vector"], nz.inputs["Vector"])
    c = g.mix(1.0, t.outputs["Color"], PARAMS["MossTint"], "MULTIPLY")
    c = g.mix(g.mathf("MULTIPLY", nz.outputs["Fac"], 0.5), c, (0.10, 0.13, 0.03))
    g.link(c, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.92
    for k in ("Sheen Weight",):
        if k in bsdf.inputs:
            bsdf.inputs[k].default_value = 0.45
    bump = g.node("ShaderNodeBump")
    nz2 = g.node("ShaderNodeTexNoise")
    nz2.inputs["Scale"].default_value = 140.0
    g.link(tc.outputs["Object"], nz2.inputs["Vector"])
    g.link(nz2.outputs["Fac"], bump.inputs["Height"])
    bump.inputs["Strength"].default_value = 0.6
    bump.inputs["Distance"].default_value = 0.004
    g.link(bump.outputs["Normal"], bsdf.inputs["Normal"])
    g.link(bsdf.outputs[0], out.inputs["Surface"])
    mat["unreal_plan"] = "MI of M_ST_RockUnique (UseMoss forced 1) or a small M_ST_Moss; MossDetail_BC local-space"
    return mat


def grass_material(name="MI_DKR_GrassTuft"):
    mat = bpy.data.materials.get(name)
    if mat is not None:
        return mat
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    g = G(mat)
    out = g.node("ShaderNodeOutputMaterial")
    bsdf = g.node("ShaderNodeBsdfPrincipled")
    at = g.node("ShaderNodeAttribute", attribute_name="Col", attribute_type="GEOMETRY")
    sep = g.node("ShaderNodeSeparateColor")
    g.link(at.outputs["Color"], sep.inputs["Color"])
    ramp = g.node("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position = 0.0
    cr.elements[0].color = (0.06, 0.09, 0.02, 1)
    cr.elements[1].position = 1.0
    cr.elements[1].color = (0.48, 0.50, 0.16, 1)
    e = cr.elements.new(0.5)
    e.color = (0.22, 0.30, 0.06, 1)
    g.link(sep.outputs[0], ramp.inputs["Fac"])
    dry = g.mix(g.mathf("MULTIPLY", g.mathf("GREATER_THAN", sep.outputs[1], 0.7), sep.outputs[0]),
                ramp.outputs["Color"], (0.42, 0.36, 0.16))
    g.link(dry, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.55
    g.link(bsdf.outputs[0], out.inputs["Surface"])
    mat["unreal_plan"] = "MI of a two-sided opaque foliage master; VertexColor.R base->tip, G variation"
    return mat
