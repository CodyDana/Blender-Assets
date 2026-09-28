"""The three master materials (MATERIAL_PLAN.md section 3, material_spec.json masters).

Every parameter node takes its name, group, sort priority, description (the buyer's tooltip) and slider range from the
spec, and its default from the spec or from build.master_defaults (v2: neutral values and the 8x8 textures in
/Game/NinjaPack/Textures/Default, so a master never references an item's maps; every Base instance overrides them).

    M_Steel_Master     Default Lit. BaseColor = saturate(Base Colour Map x Steel Tint), Metallic ORM.B,
                       Roughness saturate(ORM.G + Roughness Adjust), Specular 0.5, AO ORM.R
    M_Fabric_Master    material attributes; the static switch Cloth Sheen picks Default Lit or Cloth.
                       BaseColor = MF_AlbedoRollOff(MF_TintDetail(Detail Map, Colour, Lightest Colour, ..., mip level))
                       (or the original baked map), optional MF_LetteringBand; Specular = Specular Strength x ORM.A
    M_PaperInk_Master  Default Lit. BaseColor = min(paper + inks, 0.962) x lerp(1, ORM.R, Baked AO In Colour), the
                       paper colour guarded (black floor, Paper Colour Limit)
Material settings (build: masters.<name>.settings): Float Precision Mode Full on the fabric and paper masters (their
log / pow / cubic math), Used With Instanced Static Meshes on all three (foliage / PCG scattering needs no re-save).
"""
from __future__ import annotations

import unreal

from np_graph import Graph, Out, connect_property

MP = unreal.MaterialProperty
MSM = unreal.MaterialShadingModel
ST = unreal.MaterialSamplerType
SAMPLERS = {"Color": ST.SAMPLERTYPE_COLOR, "Masks": ST.SAMPLERTYPE_MASKS, "Normal": ST.SAMPLERTYPE_NORMAL,
            "LinearGrayscale": ST.SAMPLERTYPE_LINEAR_GRAYSCALE, "LinearColor": ST.SAMPLERTYPE_LINEAR_COLOR,
            "Grayscale": ST.SAMPLERTYPE_GRAYSCALE}
BAKED = "Use Original Baked Colours"

# Every spec parameter carries its own buyer tooltip ("desc"); this is only a safety net for a parameter added to the
# spec without one (the verify step lists any parameter whose tooltip ended up empty).
DESC_FALLBACK = {}


class Params:
    """Creates parameter nodes from the spec's master parameter table."""

    def __init__(self, g: Graph, spec_master: dict, defaults: dict, textures: dict):
        self.g = g
        self.table = {p["name"]: p for p in spec_master["parameters"]}
        self.defaults = defaults
        self.textures = textures
        self.created = {}

    def _entry(self, name):
        if name not in self.table:
            raise KeyError(f"parameter {name!r} is not in the spec")
        return self.table[name]

    def _default(self, e):
        v = e.get("default")
        if v is None or isinstance(v, str):
            if e["name"] not in self.defaults:
                raise KeyError(f"no default for {e['name']!r}")
            v = self.defaults[e["name"]]
        return v

    def __call__(self, name, *, as_object=False):
        if name in self.created:
            return self.created[name]
        e = self._entry(name)
        g, desc = self.g, e.get("desc") or DESC_FALLBACK.get(name, "")
        t = e["type"]
        if t == "scalar":
            out = g.scalar(name, self._default(e), e["group"], e["sort"], desc, e.get("min"), e.get("max"))
        elif t == "vector":
            out = g.vector(name, self._default(e), e["group"], e["sort"], desc)
        elif t == "texture":
            tex = self.textures[name]
            sampler = SAMPLERS[e["sampler"]]
            if as_object:
                out = g.texture_object(name, tex, sampler, e["group"], e["sort"], desc)
            else:
                out = g.texture(name, tex, sampler, e["group"], e["sort"], desc)
        else:
            raise TypeError(f"{name}: use switch() for {t}")
        self.created[name] = out
        return out

    def switch(self, name, when_true, when_false):
        e = self._entry(name)
        desc = e.get("desc") or DESC_FALLBACK.get(name, "")
        return self.g.switch(name, bool(e.get("default", False)), e["group"], e["sort"], desc, when_true, when_false)

    def missing(self):
        return sorted(set(self.table) - set(self.created) - set(self.g.params))


def _setup(mat, spec_master, *, attributes=False, shading=MSM.MSM_DEFAULT_LIT):
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)
    mat.set_editor_property("two_sided", False)
    mat.set_editor_property("use_material_attributes", bool(attributes))
    mat.set_editor_property("shading_model", shading)
    settings = spec_master.get("settings") or {}
    if "float_precision_mode" in settings:
        mat.set_editor_property("float_precision_mode",
                                getattr(unreal.MaterialFloatPrecisionMode, settings["float_precision_mode"]))
    if "used_with_instanced_static_meshes" in settings:
        mat.set_editor_property("used_with_instanced_static_meshes", bool(settings["used_with_instanced_static_meshes"]))
    if "used_with_skeletal_mesh" in settings:          # 2026-09-26: the fan (SK_Fan, SK_Fan_Tassel) is a skeletal mesh
        mat.set_editor_property("used_with_skeletal_mesh", bool(settings["used_with_skeletal_mesh"]))


def build_steel(mat, spec_master, defaults, textures, mfs):
    _setup(mat, spec_master)
    g = Graph(mat)
    P = Params(g, spec_master, defaults, textures)
    bc, orm, nrm = P("Base Colour Map"), P("ORM Map"), P("Normal Map")
    tint, radj, nstr = P("Steel Tint"), P("Roughness Adjust"), P("Normal Strength")
    connect_property(g.sat(g.mul(bc.rgb, tint)), MP.MP_BASE_COLOR)
    connect_property(orm.b, MP.MP_METALLIC)
    connect_property(g.sat(g.add(orm.gch, radj)), MP.MP_ROUGHNESS)
    connect_property(g.const(0.5), MP.MP_SPECULAR)
    connect_property(orm.r, MP.MP_AMBIENT_OCCLUSION)
    normal = g.call(mfs["MF_NormalStrength"], {"Normal": nrm.rgb, "Strength": nstr})["Normal"]
    connect_property(normal, MP.MP_NORMAL)
    return g, P.missing()


def mip_level(g: Graph, size):
    """The Detail Map's mip level at this pixel, as the sampler picks it: 0.5 log2 of the squared UV footprint in
    texels along the minor axis (anisotropic filtering, at most 8:1), clamped to 0..8."""
    uv = g.texcoord(0)
    dx, dy = g.ddx(uv), g.ddy(uv)
    px, py = g.dot(dx, dx), g.dot(dy, dy)
    fp = g.max(g.min(px, py), g.div(g.max(px, py), 64.0))
    lod = g.mul(g.log2(g.mul(fp, g.mul(size, size))), 0.5)
    return g.max(g.min(lod, 8.0), 0.0)


def build_fabric(mat, spec_master, defaults, textures, mfs):
    _setup(mat, spec_master, attributes=True, shading=MSM.MSM_FROM_MATERIAL_EXPRESSION)
    g = Graph(mat)
    P = Params(g, spec_master, defaults, textures)
    colour = P("Colour")
    detail = P("Detail Map")
    bc, orm, nrm = P("Base Colour Map"), P("ORM Map"), P("Normal Map")
    tinted = g.call(mfs["MF_TintDetail"], {
        "Detail": detail.r, "Colour": colour,
        "DetailBias": P("Detail Bias"), "DetailScale": P("Detail Scale"), "DetailMean": P("Detail Mean"),
        "DetailStrength": P("Detail Strength"), "HighlightRatio": P("Detail Highlight Ratio"),
        "DarkFollow": P("Dark Detail Follow"), "AlbedoCeiling": P("Albedo Ceiling"),
        "MomentsLow": Graph.rgba(P("Detail Moments Low")), "MomentsHigh": Graph.rgba(P("Detail Moments High")),
        "LightestColour": P("Lightest Colour"), "MipLevel": mip_level(g, P("Detail Map Size")),
        "MipCompensation1to4": Graph.rgba(P("Detail Mip Compensation 1-4")),
        "MipCompensation5to8": Graph.rgba(P("Detail Mip Compensation 5-8")),
        "MipCompensationPower": P("Detail Mip Compensation Power"),
    })["Albedo"]
    rolled = g.call(mfs["MF_AlbedoRollOff"], {"Albedo": tinted, "Knee": 0.85, "Limit": 0.95})["Albedo"]
    base = P.switch(BAKED, bc.rgb, rolled)
    rough = g.sat(g.add(orm.gch, P("Roughness Adjust")))
    band = g.call(mfs["MF_LetteringBand"], {
        "BaseColor": base, "Roughness": rough, "LetteringColour": P("Lettering Colour"),
        "LetteringRoughness": P("Lettering Roughness"), "BandRect": Graph.rgba(P("Lettering Band UV")),
        "LetteringMask": P("Lettering Mask", as_object=True)})
    both = P.switch("Use Lettering", g.append(band["BaseColor"], band["Roughness"]), g.append(base, rough))
    specular = g.mul(P("Specular Strength"), P.switch("Specular From ORM Alpha", orm.a, 1.0))
    normal = g.call(mfs["MF_NormalStrength"], {"Normal": nrm.rgb, "Strength": P("Normal Strength")})["Normal"]
    shading = P.switch("Cloth Sheen", g.shading_model(MSM.MSM_CLOTH), g.shading_model(MSM.MSM_DEFAULT_LIT))
    mma = g.new(unreal.MaterialExpressionMakeMaterialAttributes)
    g.link(g.mask(both, "rgb"), mma, "BaseColor")
    g.link(0.0, mma, "Metallic")
    g.link(specular, mma, "Specular")
    g.link(g.mask(both, "a"), mma, "Roughness")
    g.link(normal, mma, "Normal")
    g.link(orm.r, mma, "AmbientOcclusion")
    g.link(P("Sheen Colour"), mma, "SubsurfaceColor")      # Cloth: SubsurfaceColor = Fuzz Colour
    g.link(P("Sheen Amount"), mma, "ClearCoat")            # Cloth: CustomData0 = the Cloth input
    g.link(shading, mma, "ShadingModel")
    connect_property(Out(g, mma, ""), MP.MP_MATERIAL_ATTRIBUTES)
    return g, P.missing()


def build_paper(mat, spec_master, defaults, textures, mfs):
    _setup(mat, spec_master)
    g = Graph(mat)
    P = Params(g, spec_master, defaults, textures)
    paper_in, black_c, red_c = P("Paper Colour"), P("Black Ink Colour"), P("Red Ink Colour")
    # paper colour guards: lift pure black (hue kept); scale a full-intensity pick down to Paper Colour Limit so the
    # grain never reaches the 0.962 ceiling (the default, max 0.900, is below the limit: unchanged)
    paper_f = g.add(paper_in, g.max(g.sub(0.01, g.max3(paper_in)), 0.0))
    paper_c = g.mul(paper_f, g.min(1.0, g.div(P("Paper Colour Limit"), g.max(g.max3(paper_f), 1e-4))))
    bc, orm, nrm = P("Base Colour Map"), P("ORM Map"), P("Normal Map")
    pd, iw = P("Paper Detail Map"), P("Ink Weights Map")
    ink = g.call(mfs["MF_InkDerive"], {
        "PaperColour": paper_c, "BlackInkColour": black_c, "RedInkColour": red_c,
        "BlackDryPaperMix": P("Black Ink Dry Paper Mix"), "BlackDryGain": P("Black Ink Dry Gain"),
        "RedDryValueScale": P("Red Ink Dry Value Scale"), "RedPoolSaturation": P("Red Ink Pool Saturation"),
        "RedPoolGain": P("Red Ink Pool Gain"), "RedPoolDefaultSaturation": P("Red Ink Pool Default Saturation")})
    total = g.mul(paper_c, g.mul(pd.rgb, P("Paper Weight Scale")))
    total = g.add(total, g.mul(black_c, iw.r))
    total = g.add(total, g.mul(ink["BlackDry"], iw.gch))
    total = g.add(total, g.mul(red_c, iw.b))
    total = g.add(total, g.mul(ink["RedDry"], iw.a))
    total = g.add(total, g.mul(ink["RedPool"], pd.a))
    tag = g.min(total, P("Albedo Ceiling"))
    base = P.switch(BAKED, bc.rgb, tag)
    base = g.mul(base, g.lerp(1.0, orm.r, P("Baked AO In Colour")))
    connect_property(base, MP.MP_BASE_COLOR)
    connect_property(g.const(0.0), MP.MP_METALLIC)
    connect_property(g.sat(g.add(orm.gch, P("Roughness Adjust"))), MP.MP_ROUGHNESS)
    connect_property(P("Specular Strength"), MP.MP_SPECULAR)
    connect_property(orm.r, MP.MP_AMBIENT_OCCLUSION)
    normal = g.call(mfs["MF_NormalStrength"], {"Normal": nrm.rgb, "Strength": P("Normal Strength")})["Normal"]
    connect_property(normal, MP.MP_NORMAL)
    return g, P.missing()


BUILDERS = {"M_Steel_Master": build_steel, "M_Fabric_Master": build_fabric, "M_PaperInk_Master": build_paper}
