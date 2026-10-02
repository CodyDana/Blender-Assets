"""LANDSCAPE ROUND, FX + LIGHTING stage, Unreal step 1 (pythonscript commandlet, -nullrhi, with our DojoFXTools editor
plugin installed for the run by fxlight/tools/run_fx.sh): the FX ASSETS, from our own DojoFX textures and meshes
(Exports/DojoKit/FX, recipe WorkFiles/dojo/build/fx/fx_catalog.json). Nothing here touches the level.

Materials (/Game/DojoKit/FX/Materials):
  M_DKF_SixWayMist   lit translucent sprite master for the six-way flipbooks (MistPuff / MistWisp / SprayBurst): both
                     maps through a SubUV sampler (8 x 8, blended); the key light = the six-way formula with the sun
                     direction (SunDir: the UDS sun, locked at 1730, written at build time from the layout sun record)
                     in the camera basis; the engine's translucency lighting (UDS sun + sky light, volumetric
                     non-directional) carries the colour and the exposure, so the mist sits in the scene's own light;
                     opacity = P.a x particle alpha x depth fade (soft particles)
  MI_DKF_MistPuff / MI_DKF_MistWisp / MI_DKF_SprayBurst
  M_DKF_HazeSprite + MI_DKF_RiverHaze   T_DKF_Haze_M (R opacity, G top-lit, B back-lit) on Z-locked sprites
  M_DKF_Droplet + MI_DKF_Droplet        a soft round white drop for the spray droplets (velocity-aligned)
  M_DKF_PetalScatterDecal + MI_DKF_PetalScatter_0..3   deferred decal, DBuffer colour / normal / roughness, one atlas
                     cell per instance (catalog: 0 sparse, 1 medium, 2 dense drift, 3 strays)
  MI_DKF_FoamWake    child of M_DJL_RapidsFoam (the world stage's white-water master): denser white water for the
                     wakes behind the boulders
  usage flags        M_DKF_Petal + the new masters: Niagara sprites / mesh particles, instanced static meshes
Niagara systems (/Game/DojoKit/FX/Niagara): LIGHTWEIGHT (stateless) emitters, each a copy of the engine template
  /Niagara/DefaultAssets/Templates/Systems/FountainLightweight configured through DojoFXTools (reflection):
  NS_DKF_PetalDrift    the light courtyard / terrace drift layer (mesh particles: Petal_A..F + PetalOld_A 1 in 14)
  NS_DKF_PetalCanopy   one per CherrySlot (canopy fall from a 3 m sphere 4.5 m up), ready for the cherries
  NS_DKF_MistPuff      rising puffs at the rapids / rock impacts
  NS_DKF_MistWisp      long wisps drifting down-stream over the rapids
  NS_DKF_RapidSpray    SprayBurst flipbook splashes on the upstream faces of the boulders
  NS_DKF_SprayDroplets small drops thrown up by the splashes
  NS_DKF_RiverHaze     large Z-locked haze sheets low over the water
Result: WorkFiles/dojo/build/landscape/fxlight/json/fxl_assets.json
"""
import json
import math
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
sys.path.insert(0, str(ROOT / "Scripts/dojo/unreal"))
import unreal  # noqa: E402
import dj_sc_common as S  # noqa: E402

O = ROOT / "WorkFiles/dojo/build/landscape/fxlight"
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
MP = unreal.MaterialProperty
ST = unreal.MaterialSamplerType
FXL = unreal.DojoFXToolsLibrary
FX = "/Game/DojoKit/FX"
FMAT = FX + "/Materials"
FTEX = FX + "/Textures"
FNS = FX + "/Niagara"
TEMPLATE = "/Niagara/DefaultAssets/Templates/Systems/FountainLightweight"
REP = {"engine": unreal.SystemLibrary.get_engine_version(), "errors": [], "materials": {}, "systems": {}, "set_errors": []}

# the sun: direction TO the sun in the UE frame (layout sun record = the UDS sun at 1730, measured in round 9: 9.08 deg)
_TD = S.load()["sun"]["travel_dir"]
SUN_TO = [-_TD[0], _TD[1], -_TD[2]]          # Blender travel (x, y, z) -> UE (x, -y, z), negated
# the scene wind for the FX: from the west (the sun side) toward the east, down the courtyard axis (UE frame)
WIND = [0.98, -0.13, 0.0]


def lc(v):
    v = list(v) + [1.0] * (4 - len(v))
    return unreal.LinearColor(*[float(x) for x in v[:4]])


def get_or_create(path, cls, factory):
    if EAL.does_asset_exist(path):
        a = unreal.load_asset(path)
        if not isinstance(a, cls):
            raise TypeError(f"{path} exists as {type(a).__name__}")
        return a
    folder, name = path.rsplit("/", 1)
    return AT.create_asset(name, folder, cls, factory)


def tex(path):
    t = unreal.load_asset(path)
    if t is None:
        raise RuntimeError(f"texture missing {path}")
    return t


class G:
    def __init__(self, mat):
        self.m, self.n = mat, 0

    def node(self, cls, **props):
        self.n += 1
        e = MEL.create_material_expression(self.m, cls, -600 - 260 * (self.n // 12), 130 * (self.n % 12))
        for k, v in props.items():
            e.set_editor_property(k, v)
        return e

    def link(self, a, ao, b, bi):
        if not MEL.connect_material_expressions(a, ao, b, bi):
            raise RuntimeError(f"connect {a.get_name()}.{ao!r} -> {b.get_name()}.{bi!r}")

    def out(self, a, prop):
        if not MEL.connect_material_property(a[0], a[1], prop):
            raise RuntimeError(f"connect -> {prop}")

    def scalar(self, name, v, group="P"):
        return (self.node(unreal.MaterialExpressionScalarParameter, parameter_name=name, default_value=float(v),
                          group=group), "")

    def vector(self, name, v, group="P"):
        return (self.node(unreal.MaterialExpressionVectorParameter, parameter_name=name, default_value=lc(v),
                          group=group), "")

    def const(self, v):
        return (self.node(unreal.MaterialExpressionConstant, r=float(v)), "")

    def const2(self, a, b):
        return (self.node(unreal.MaterialExpressionConstant2Vector, r=float(a), g=float(b)), "")

    def const3(self, v):
        return (self.node(unreal.MaterialExpressionConstant3Vector, constant=lc(v)), "")

    def _bin(self, cls, a, b):
        e = self.node(cls)
        self.link(a[0], a[1], e, "A")
        self.link(b[0], b[1], e, "B")
        return (e, "")

    def mul(self, a, b):
        return self._bin(unreal.MaterialExpressionMultiply, a, b)

    def add(self, a, b):
        return self._bin(unreal.MaterialExpressionAdd, a, b)

    def sub(self, a, b):
        return self._bin(unreal.MaterialExpressionSubtract, a, b)

    def dot(self, a, b):
        return self._bin(unreal.MaterialExpressionDotProduct, a, b)

    def mx(self, a, b):
        return self._bin(unreal.MaterialExpressionMax, a, b)

    def append(self, a, b):
        return self._bin(unreal.MaterialExpressionAppendVector, a, b)

    def lerp(self, a, b, t):
        e = self.node(unreal.MaterialExpressionLinearInterpolate)
        self.link(a[0], a[1], e, "A")
        self.link(b[0], b[1], e, "B")
        self.link(t[0], t[1], e, "Alpha")
        return (e, "")

    def un(self, cls, src, **props):
        e = self.node(cls, **props)
        self.link(src[0], src[1], e, "")
        return (e, "")

    def sat(self, a):
        return self.un(unreal.MaterialExpressionSaturate, a)

    def mask(self, a, ch):
        return self.un(unreal.MaterialExpressionComponentMask, a, r="R" in ch, g="G" in ch, b="B" in ch, a="A" in ch)

    def uv(self, i=0):
        return (self.node(unreal.MaterialExpressionTextureCoordinate, coordinate_index=i), "")

    def view_axis(self, v):
        """A view-space unit axis in world space (X right, Y up, Z forward)."""
        return self.un(unreal.MaterialExpressionTransform, self.const3(v),
                       transform_source_type=unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_VIEW,
                       transform_type=unreal.MaterialVectorCoordTransform.TRANSFORM_WORLD)

    def pcolor(self):
        return self.node(unreal.MaterialExpressionParticleColor)

    def depth_fade(self, opacity, dist_param, dist):
        e = self.node(unreal.MaterialExpressionDepthFade)
        self.link(opacity[0], opacity[1], e, "Opacity")
        d = self.scalar(dist_param, dist)
        self.link(d[0], d[1], e, "FadeDistance")
        return (e, "")


def sampler_for(t):
    """The sampler type a texture's own settings need (owned / engine textures are not always stored as named)."""
    cs = str(t.get_editor_property("compression_settings")).upper()
    srgb = bool(t.get_editor_property("srgb"))
    if "MASKS" in cs:
        return ST.SAMPLERTYPE_MASKS
    if "GRAYSCALE" in cs:
        return ST.SAMPLERTYPE_GRAYSCALE if srgb else ST.SAMPLERTYPE_LINEAR_GRAYSCALE
    if "NORMAL" in cs:
        return ST.SAMPLERTYPE_NORMAL
    return ST.SAMPLERTYPE_COLOR if srgb else ST.SAMPLERTYPE_LINEAR_COLOR


def new_master(path, blend, shading=unreal.MaterialShadingModel.MSM_DEFAULT_LIT, domain=None, usages=()):
    m = get_or_create(path, unreal.Material, unreal.MaterialFactoryNew())
    MEL.delete_all_material_expressions(m)
    if domain is not None:
        m.set_editor_property("material_domain", domain)
    m.set_editor_property("blend_mode", blend)
    m.set_editor_property("shading_model", shading)
    for u in usages:
        try:
            MEL.set_material_usage(m, u)
        except Exception as exc:  # noqa: BLE001
            REP["set_errors"].append(f"{path} usage {u}: {exc}")
    return m


def finish(mat, path, extra=None):
    MEL.layout_material_expressions(mat)
    MEL.recompile_material(mat)
    ok = bool(EAL.save_loaded_asset(mat, False))
    REP["materials"][path] = dict({"expressions": int(MEL.get_num_material_expressions(mat)), "saved": ok}, **(extra or {}))


def make_mi(path, parent, scalars=None, vectors=None, textures=None):
    mi = get_or_create(path, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.clear_all_material_instance_parameters(mi)
    MEL.set_material_instance_parent(mi, parent)
    for k, v in (scalars or {}).items():
        MEL.set_material_instance_scalar_parameter_value(mi, k, float(v))
    for k, v in (vectors or {}).items():
        MEL.set_material_instance_vector_parameter_value(mi, k, lc(v))
    for k, v in (textures or {}).items():
        MEL.set_material_instance_texture_parameter_value(mi, k, tex(v))
    MEL.update_material_instance(mi)
    EAL.save_loaded_asset(mi, False)
    REP["materials"][path] = {"parent": parent.get_path_name(), "scalars": scalars or {}, "vectors": vectors or {},
                              "textures": textures or {}}
    return mi


U = unreal.MaterialUsage
SPRITE_USAGE = (U.MATUSAGE_NIAGARA_SPRITES,)
MESH_USAGE = (U.MATUSAGE_NIAGARA_MESH_PARTICLES, U.MATUSAGE_INSTANCED_STATIC_MESHES)


# ---------------------------------------------------------------------------------------------------- materials
def six_way():
    path = f"{FMAT}/M_DKF_SixWayMist"
    m = new_master(path, unreal.BlendMode.BLEND_TRANSLUCENT, usages=SPRITE_USAGE)
    for k, v in (("translucency_lighting_mode", unreal.TranslucencyLightingMode.TLM_VOLUMETRIC_PER_VERTEX_NON_DIRECTIONAL),
                 ("two_sided", True)):
        try:
            m.set_editor_property(k, v)
        except Exception as exc:  # noqa: BLE001
            REP["set_errors"].append(f"{path}.{k}: {exc}")
    g = G(m)
    P = g.node(unreal.MaterialExpressionTextureSampleParameterSubUV, parameter_name="SixWayP",
               texture=tex(f"{FTEX}/T_DKF_MistPuff_SixWayP"), sampler_type=ST.SAMPLERTYPE_LINEAR_COLOR, blend=True,
               group="Textures")
    N = g.node(unreal.MaterialExpressionTextureSampleParameterSubUV, parameter_name="SixWayN",
               texture=tex(f"{FTEX}/T_DKF_MistPuff_SixWayN"), sampler_type=ST.SAMPLERTYPE_LINEAR_COLOR, blend=True,
               group="Textures")
    L = g.vector("SunDir", SUN_TO, "Light")
    L3 = g.mask(L, "RGB")
    ls = g.append(g.append(g.dot(L3, g.view_axis((1, 0, 0))), g.dot(L3, g.view_axis((0, 1, 0)))),
                  g.dot(L3, g.view_axis((0, 0, 1))))
    lp = g.mx(ls, g.const3((0, 0, 0)))
    ln = g.mx(g.mul(ls, g.const(-1.0)), g.const3((0, 0, 0)))
    key = g.add(g.dot(lp, g.mask((P, "RGB"), "RGB")), g.dot(ln, g.mask((N, "RGB"), "RGB")))
    amb = g.add(g.add(g.mul(g.mask((P, "RGB"), "G"), g.const(0.5)), g.mul(g.mask((N, "RGB"), "B"), g.const(0.3))),
                g.const(0.2))
    shade = g.add(g.mul(key, g.scalar("KeyGain", 1.4, "Light")), g.mul(amb, g.scalar("AmbientGain", 0.55, "Light")))
    pc = g.pcolor()
    col = g.mul(g.mul(g.sat(shade), g.vector("Tint", (0.92, 0.94, 0.97), "Look")), (pc, ""))
    g.out(col, MP.MP_BASE_COLOR)
    g.out(g.const(1.0), MP.MP_ROUGHNESS)
    g.out(g.const(0.0), MP.MP_SPECULAR)
    op = g.mul(g.mul((P, "A"), (pc, "A")), g.scalar("Opacity", 1.0, "Look"))
    g.out(g.sat(g.depth_fade(op, "DepthFadeCm", 150.0)), MP.MP_OPACITY)
    finish(m, path, {"sun_to": SUN_TO})
    # probe pa: the puffs and wisps stacked into a white wall over the rapids (CAM_RiverRapids mean 108 -> 115):
    # opacity x 0.45
    for name, tp, sc in (("MistPuff", "MistPuff", {"Opacity": 0.25, "DepthFadeCm": 250.0}),
                         ("MistWisp", "MistWisp", {"Opacity": 0.22, "DepthFadeCm": 300.0}),
                         ("SprayBurst", "SprayBurst", {"Opacity": 0.6, "DepthFadeCm": 40.0, "KeyGain": 1.6})):
        make_mi(f"{FMAT}/MI_DKF_{name}", m, scalars=sc,
                textures={"SixWayP": f"{FTEX}/T_DKF_{tp}_SixWayP", "SixWayN": f"{FTEX}/T_DKF_{tp}_SixWayN"})


def haze():
    path = f"{FMAT}/M_DKF_HazeSprite"
    m = new_master(path, unreal.BlendMode.BLEND_TRANSLUCENT, usages=SPRITE_USAGE)
    m.set_editor_property("translucency_lighting_mode", unreal.TranslucencyLightingMode.TLM_VOLUMETRIC_PER_VERTEX_NON_DIRECTIONAL)
    m.set_editor_property("two_sided", True)
    g = G(m)
    t = g.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="Haze", texture=tex(f"{FTEX}/T_DKF_Haze_M"),
               sampler_type=ST.SAMPLERTYPE_MASKS, group="Textures")
    g.link(*g.uv(0), t, "UVs")
    pc = g.pcolor()
    shade = g.add(g.const(0.55), g.add(g.mul((t, "G"), g.const(0.3)), g.mul((t, "B"), g.scalar("BackLit", 0.35))))
    g.out(g.mul(g.mul(g.sat(shade), g.vector("Tint", (0.9, 0.92, 0.96))), (pc, "")), MP.MP_BASE_COLOR)
    g.out(g.const(1.0), MP.MP_ROUGHNESS)
    g.out(g.const(0.0), MP.MP_SPECULAR)
    op = g.mul(g.mul((t, "R"), (pc, "A")), g.scalar("Opacity", 1.0))
    g.out(g.sat(g.depth_fade(op, "DepthFadeCm", 300.0)), MP.MP_OPACITY)
    finish(m, path)
    make_mi(f"{FMAT}/MI_DKF_RiverHaze", m, scalars={"Opacity": 0.55})


def droplet():
    path = f"{FMAT}/M_DKF_Droplet"
    m = new_master(path, unreal.BlendMode.BLEND_TRANSLUCENT, usages=SPRITE_USAGE)
    m.set_editor_property("translucency_lighting_mode", unreal.TranslucencyLightingMode.TLM_VOLUMETRIC_PER_VERTEX_NON_DIRECTIONAL)
    g = G(m)
    d = g.node(unreal.MaterialExpressionDistance)
    uvn = g.uv(0)
    g.link(uvn[0], uvn[1], d, "A")
    c = g.const2(0.5, 0.5)
    g.link(c[0], c[1], d, "B")
    r = g.sat(g.sub(g.const(1.0), g.mul((d, ""), g.const(2.0))))
    pc = g.pcolor()
    g.out(g.mul(g.vector("Tint", (0.86, 0.9, 0.92)), (pc, "")), MP.MP_BASE_COLOR)
    g.out(g.const(0.2), MP.MP_ROUGHNESS)
    g.out(g.sat(g.mul(g.mul(r, r), g.mul((pc, "A"), g.scalar("Opacity", 0.9)))), MP.MP_OPACITY)
    finish(m, path)
    make_mi(f"{FMAT}/MI_DKF_Droplet", m)


def scatter_decal():
    path = f"{FMAT}/M_DKF_PetalScatterDecal"
    m = new_master(path, unreal.BlendMode.BLEND_TRANSLUCENT, domain=unreal.MaterialDomain.MD_DEFERRED_DECAL)
    g = G(m)
    cell = g.scalar("Cell", 0.0)
    # UV = TexCoord * 0.5 + (fmod(Cell, 2), floor(Cell / 2)) * 0.5
    fm = g.node(unreal.MaterialExpressionFmod)
    g.link(cell[0], cell[1], fm, "A")
    two = g.const(2.0)
    g.link(two[0], two[1], fm, "B")
    fl = g.un(unreal.MaterialExpressionFloor, g.mul(cell, g.const(0.5)))
    off = g.mul(g.append((fm, ""), fl), g.const(0.5))
    uv = g.add(g.mul(g.uv(0), g.const(0.5)), off)
    bc = g.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="BC",
                texture=tex(f"{FTEX}/T_DKF_PetalScatter_BC"), sampler_type=ST.SAMPLERTYPE_COLOR, group="Textures")
    nm = g.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="N",
                texture=tex(f"{FTEX}/T_DKF_PetalScatter_N"), sampler_type=ST.SAMPLERTYPE_NORMAL, group="Textures")
    orm = g.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="ORM",
                 texture=tex(f"{FTEX}/T_DKF_PetalScatter_ORM"), sampler_type=ST.SAMPLERTYPE_MASKS, group="Textures")
    for t in (bc, nm, orm):
        g.link(uv[0], uv[1], t, "UVs")
    g.out(g.mul((bc, "RGB"), g.vector("Tint", (1, 1, 1))), MP.MP_BASE_COLOR)
    g.out((nm, "RGB"), MP.MP_NORMAL)
    g.out((orm, "G"), MP.MP_ROUGHNESS)
    g.out(g.sat(g.mul((bc, "A"), g.scalar("Fade", 1.0))), MP.MP_OPACITY)
    finish(m, path)
    for i in range(4):
        make_mi(f"{FMAT}/MI_DKF_PetalScatter_{i}", m, scalars={"Cell": float(i)})


def foam_wake():
    """M_DKF_FoamWake: the white water trailing each boulder (probe pa: a child of the strip master read as hard-edged
    rectangles, its fade runs along one axis only). Translucent lit; two layers of our tileable T_DKF_Foam_M on world
    XY (one panning down the rapids' mean flow), thresholded; an elliptical soft mask over the plane's UVs (head at
    the rock, the tail thinning); the engine's T_WaterFlow_01 foam breaks it up."""
    path = f"{FMAT}/M_DKF_FoamWake"
    m = new_master(path, unreal.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property("translucency_lighting_mode", unreal.TranslucencyLightingMode.TLM_SURFACE)
    g = G(m)
    wp = (g.node(unreal.MaterialExpressionWorldPosition), "")
    xy = g.mul(g.mask(wp, "RG"), g.const(0.01))
    t = (g.node(unreal.MaterialExpressionTime), "")
    flow = g.const2(-0.63, 0.77)
    # it3: our Voronoi foam read as pebble scales from the elevated cameras (caps/it2): the engine's white-water foam
    # (T_WaterFlow_01_Foam_Tiled, as the world stage's rapids strips) carries the pattern, our T_DKF_Foam_M breaks it up
    ft = tex("/Water/Textures/Foam/T_WaterFlow_01_Foam_Tiled")
    fm = tex(f"{FTEX}/T_DKF_Foam_M")
    def samp(uvx, t_, name):
        e = g.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name=name, texture=t_,
                   sampler_type=sampler_for(t_),
                   group="Textures")
        g.link(uvx[0], uvx[1], e, "UVs")
        return (e, "R")
    uv1 = g.sub(g.mul(xy, g.const(1.0 / 3.2)), g.mul(flow, g.mul(t, g.scalar("Speed", 0.55))))
    uv2 = g.sub(g.mul(xy, g.const(1.0 / 1.4)), g.mul(flow, g.mul(t, g.const(0.9))))
    f = g.mul(g.add(samp(uv1, ft, "Foam1"), g.mul(samp(uv2, ft, "Foam2"), g.const(0.7))),
              g.add(g.const(0.35), g.mul(samp(g.mul(xy, g.const(1.0 / 9.0)), fm, "Breakup"), g.const(0.9))))
    uv0 = g.uv(0)
    c = g.mul(g.sub(uv0, g.const2(0.5, 0.5)), g.const2(2.0, 2.0))
    dist = g.un(unreal.MaterialExpressionLength, c) if hasattr(unreal, "MaterialExpressionLength") else None
    if dist is None:
        dist = g.un(unreal.MaterialExpressionSquareRoot, g.dot(c, c))
    # it4: the ellipse read as smooth pads (caps/it3): its edge is eaten by a low-frequency breakup so the white water
    # frays into streaks; Opacity per instance (emergent boulders 0.95, the pour-over stones 0.5)
    brk = samp(g.mul(xy, g.const(1.0 / 4.0)), fm, "EdgeBreakup")
    mask = g.sat(g.sub(g.mul(g.sub(g.const(1.0), dist), g.const(2.6)), g.mul(brk, g.const(0.9))))
    thr = g.scalar("Threshold", 0.12)
    fo = g.sat(g.mul(g.sub(f, thr), g.scalar("Contrast", 2.5)))
    op = g.sat(g.mul(g.mul(fo, mask), g.scalar("Opacity", 0.95)))
    g.out(g.vector("FoamColour", (0.86, 0.9, 0.93)), MP.MP_BASE_COLOR)
    g.out(g.const(0.55), MP.MP_ROUGHNESS)
    g.out(op, MP.MP_OPACITY)
    finish(m, path)
    make_mi(f"{FMAT}/MI_DKF_FoamWake", m)
    make_mi(f"{FMAT}/MI_DKF_FoamWakeSoft", m, scalars={"Opacity": 0.5, "Threshold": 0.2})


def petal_usage():
    m = unreal.load_asset(f"{FMAT}/M_DKF_Petal")
    rec = {}
    for u in MESH_USAGE:
        rec[str(u)] = str(MEL.set_material_usage(m, u))
    MEL.recompile_material(m)
    rec["saved"] = bool(EAL.save_loaded_asset(m, False))
    rec["shading_model"] = str(m.get_editor_property("shading_model"))
    rec["blend_mode"] = str(m.get_editor_property("blend_mode"))
    REP["materials"][f"{FMAT}/M_DKF_Petal"] = rec


# ---------------------------------------------------------------------------------------------------- niagara helpers
def f(v):
    return f"{float(v):.6f}"


def d_range(lo, hi=None):
    """FNiagaraDistributionRangeFloat text (uniform range / constant)."""
    hi = lo if hi is None else hi
    mode = "UniformConstant" if lo == hi else "UniformRange"
    cc = f"({f(lo)})" if lo == hi else f"({f(lo)},{f(hi)})"
    return f"(Min={f(lo)},Max={f(hi)},Mode={mode},ChannelConstantsAndRanges={cc})"


def d_int(lo, hi=None):
    hi = lo if hi is None else hi
    mode = "UniformConstant" if lo == hi else "UniformRange"
    return f"(Min={int(lo)},Max={int(hi)},Mode={mode})"


def vec(v, k=("X", "Y", "Z")):
    return "(" + ",".join(f"{a}={f(b)}" for a, b in zip(k, v)) + ")"


def d_v3(lo, hi=None):
    hi = lo if hi is None else hi
    mode = "NonUniformConstant" if list(lo) == list(hi) else "NonUniformRange"
    cc = ",".join(f(x) for x in (list(lo) if lo == hi else list(lo) + list(hi)))
    return f"(Min={vec(lo)},Max={vec(hi)},Mode={mode},ChannelConstantsAndRanges=({cc}))"


def d_v3_uniform(lo, hi):
    """A uniform (all-axes-equal) Vector3 range: one random scalar for all three channels."""
    return (f"(Min={vec((lo, lo, lo))},Max={vec((hi, hi, hi))},Mode=UniformRange,"
            f"ChannelConstantsAndRanges=({f(lo)},{f(hi)}))")


def d_v2(lo, hi, uniform=True):
    if uniform:
        return (f"(Min={vec((lo, lo), ('X', 'Y'))},Max={vec((hi, hi), ('X', 'Y'))},Mode=UniformRange,"
                f"ChannelConstantsAndRanges=({f(lo)},{f(hi)}))")
    return (f"(Min={vec(lo, ('X', 'Y'))},Max={vec(hi, ('X', 'Y'))},Mode=NonUniformRange,"
            f"ChannelConstantsAndRanges=({f(lo[0])},{f(lo[1])},{f(hi[0])},{f(hi[1])}))")


def rich_curve(keys):
    return "(Keys=(" + ",".join(f"(Time={f(t)},Value={f(v)})" for t, v in keys) + "))"


def sample(keys, n=16):
    out = []
    for i in range(n):
        t = i / (n - 1)
        for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
            if t0 <= t <= t1:
                out.append(v0 + (v1 - v0) * ((t - t0) / max(t1 - t0, 1e-6)))
                break
    return out


def d_color_alpha_curve(alpha_keys, rgb=(1.0, 1.0, 1.0)):
    """FNiagaraDistributionColor: RGB constant, alpha over normalized age (curve, sampled to Values)."""
    a = sample(alpha_keys)
    vals = ",".join(f"(R={f(rgb[0])},G={f(rgb[1])},B={f(rgb[2])},A={f(x)})" for x in a)
    curves = ",".join([rich_curve([(0, rgb[0]), (1, rgb[0])]), rich_curve([(0, rgb[1]), (1, rgb[1])]),
                       rich_curve([(0, rgb[2]), (1, rgb[2])]), rich_curve(alpha_keys)])
    return f"(Values=({vals}),ValuesTimeRange=(X=0.000000,Y=1.000000),Mode=NonUniformCurve,ChannelCurves=({curves}))"


def d_color_const(c):
    vals = f"(R={f(c[0])},G={f(c[1])},B={f(c[2])},A={f(c[3])})"
    return f"(Values=({vals},{vals}),ValuesTimeRange=(X=0.000000,Y=1.000000),Mode=NonUniformConstant,ChannelConstantsAndRanges=({','.join(f(x) for x in c)}))"


def d_color_range(lo, hi):
    a = f"(R={f(lo[0])},G={f(lo[1])},B={f(lo[2])},A={f(lo[3])})"
    b = f"(R={f(hi[0])},G={f(hi[1])},B={f(hi[2])},A={f(hi[3])})"
    return f"(Values=({a},{b}),ValuesTimeRange=(X=0.000000,Y=1.000000),Mode=NonUniformRange,ChannelConstantsAndRanges=({','.join(f(x) for x in list(lo) + list(hi))}))"


def d_scale_curve3(keys):
    """FNiagaraDistributionVector3 uniform scale curve over normalized age."""
    s = sample(keys)
    vals = ",".join(vec((x, x, x)) for x in s)
    return (f"(Values=({vals}),ValuesTimeRange=(X=0.000000,Y=1.000000),Mode=UniformCurve,"
            f"ChannelCurves=({rich_curve(keys)}))")


def d_scale_curve2(keys):
    s = sample(keys)
    vals = ",".join(vec((x, x), ("X", "Y")) for x in s)
    return (f"(Values=({vals}),ValuesTimeRange=(X=0.000000,Y=1.000000),Mode=UniformCurve,"
            f"ChannelCurves=({rich_curve(keys)}))")


def setp(obj, path, value, rec):
    err = FXL.set_prop(obj, path, value)
    if err:
        REP["set_errors"].append(f"{rec}: {path}: {err}")
    return not err


MODULES = ("AccelerationForce", "AddVelocity", "CameraOffset", "CurlNoiseForce", "DecalAttributes", "Drag",
           "DynamicMaterialParameters", "GravityForce", "InitializeParticle", "InitialMeshOrientation", "LightAttributes",
           "MeshIndex", "MeshRotationRate", "ScaleColor", "ScaleMeshSize", "ScaleMeshSizeBySpeed", "ScaleRibbonWidth",
           "ScaleSpriteSize", "ScaleSpriteSizeBySpeed", "ShapeLocation", "SolveVelocitiesAndForces",
           "SpriteFacingAndAlignment", "SpriteRotationRate", "SubUVAnimation", "RotateAroundPoint")


def new_system(name, spec):
    """spec: {"spawn": [spawninfo text], "bounds": (min, max) cm, "modules": {Module: {prop: text}}, "renderer":
    ("mesh"|"sprite", {prop: text})}. Every module not named is disabled."""
    path = f"{FNS}/{name}"
    # an existing system (the level references it) is re-configured in place: every setting below is written
    # explicitly (spawn, bounds, every module's enable flag and values, the renderer replaced)
    sysa = unreal.load_asset(path) if EAL.does_asset_exist(path) else AT.duplicate_asset(name, FNS, unreal.load_asset(TEMPLATE))
    em = FXL.find_inner(sysa, "NiagaraStatelessEmitter", "")
    rec = name
    setp(em, "SpawnInfos", "(" + ",".join(spec["spawn"]) + ")", rec)
    lo, hi = spec["bounds"]
    setp(em, "FixedBounds", f"(Min={vec(lo)},Max={vec(hi)},IsValid=True)", rec)
    setp(em, "RandomSeed", str(spec.get("seed", 0)), rec)
    for mod in MODULES:
        m = FXL.find_inner(sysa, "NiagaraStatelessModule_" + mod, "")
        if m is None:
            continue
        on = mod in spec["modules"] or mod == "SolveVelocitiesAndForces"
        setp(m, "bModuleEnabled", "True" if on else "False", rec)
        for k, v in spec["modules"].get(mod, {}).items():
            setp(m, k, v, f"{rec}.{mod}")
    kind, props = spec["renderer"]
    cls = unreal.load_class(None, "/Script/Niagara.NiagaraMeshRendererProperties" if kind == "mesh"
                            else "/Script/Niagara.NiagaraSpriteRendererProperties")
    r = FXL.replace_array_with_new(em, "RendererProperties", cls)
    if r is None:
        raise RuntimeError(f"{name}: renderer not created")
    for k, v in props.items():
        setp(r, k, v, f"{rec}.renderer")
    fin = FXL.finalize_system(sysa)
    ok = bool(EAL.save_loaded_asset(sysa, False))
    REP["systems"][path] = {"finalize": fin, "saved": ok, "spawn": spec["spawn"], "bounds_cm": spec["bounds"],
                            "modules_on": sorted(set(spec["modules"]) | {"SolveVelocitiesAndForces"}), "renderer": kind,
                            "est_particles": spec.get("est"), "check": {
                                "SpawnInfos": FXL.get_prop(em, "SpawnInfos")[:400],
                                "renderer_material": FXL.get_prop(r, "Material" if kind == "sprite" else "Meshes")[:600]}}
    return sysa


def spawn_rate(lo, hi):
    return f"(Type=Rate,Rate={d_range(lo, hi)})"


def mesh_list(names):
    return "(" + ",".join(f'(Mesh="/Game/DojoKit/FX/Meshes/{n}.{n}")' for n in names) + ")"


PETALS = ["SM_DKF_Petal_A", "SM_DKF_Petal_B", "SM_DKF_Petal_C", "SM_DKF_Petal_D", "SM_DKF_Petal_E", "SM_DKF_Petal_F",
          "SM_DKF_PetalOld_A"]
# wind as an acceleration under drag: terminal drift = accel / drag
DRAG = 6.0


DEBUG_SCALE = float(__import__("os").environ.get("DJ_FXL_DEBUG_PETAL_SCALE", "1"))   # render test only (x 25: visible)


def petal_modules(life, scale_lo, scale_hi, shape, wind_cms, fall_cms):
    scale_lo, scale_hi = scale_lo * DEBUG_SCALE, scale_hi * DEBUG_SCALE
    acc = [WIND[0] * wind_cms * DRAG, WIND[1] * wind_cms * DRAG, 0.0]
    return {
        "InitializeParticle": {"LifetimeDistribution": d_range(*life), "MeshScaleDistribution": d_v3_uniform(scale_lo, scale_hi),
                               "ColorDistribution": d_color_const((1, 1, 1, 1)), "MassDistribution": d_range(1.0)},
        "ShapeLocation": shape,
        "InitialMeshOrientation": {"MeshOrientationMode": "Random"},
        "MeshIndex": {"MeshIndex": d_int(0, len(PETALS) - 1), "MeshIndexWeight": "(1,1,1,1,1,1,0.45)"},
        "MeshRotationRate": {"RotationRateDistribution": d_v3((-420, -420, -300), (420, 420, 300))},
        "GravityForce": {"GravityDistribution": d_v3((0, 0, -fall_cms * DRAG))},
        "AccelerationForce": {"AccelerationDistribution": d_v3(acc), "CoordinateSpace": "World"},
        "Drag": {"DragDistribution": d_range(DRAG * 0.85, DRAG * 1.15)},
        "CurlNoiseForce": {"NoiseStrength": "90.0", "NoiseFrequency": "8.0"},
        # stateless particles never collide: they shrink away over the last 15 % of life instead of piling up
        "ScaleMeshSize": {"ScaleDistribution": d_scale_curve3([(0.0, 0.0), (0.04, 1.0), (0.85, 1.0), (1.0, 0.0)])},
    }


MESH_R = {"Meshes": mesh_list(PETALS), "bCastShadows": "False", "SortMode": "None", "bEnableCameraDistanceCulling": "True",
          "MinCameraDistance": "0.0", "MaxCameraDistance": "9000.0"}


def sprite_r(mi, sub=True, facing="FaceCamera", align="Unaligned", pivot=(0.5, 0.5), sort="ViewDepth", maxd=40000.0):
    r = {"Material": f'"{FMAT}/{mi}.{mi}"', "FacingMode": facing, "Alignment": align,
         "PivotInUVSpace": f"(X={f(pivot[0])},Y={f(pivot[1])})", "SortMode": sort, "bCastShadows": "False",
         "bEnableCameraDistanceCulling": "True", "MinCameraDistance": "0.0", "MaxCameraDistance": f(maxd)}
    if sub:
        r.update({"SubImageSize": "(X=8.000000,Y=8.000000)", "bSubImageBlend": "True"})
    return r


def systems():
    # 1 petal drift layer over the courtyard / terrace: a 60 x 60 m box 6-16 m above the actor (placed at the courtyard
    #   centre), 26-34 /s, life 10-14 s (fall ~1 m/s: they cross the eye band and shrink away near the ground)
    box = {"ShapePrimitive": "Box", "BoxSize": d_v3((6000, 6000, 1000)),
           "TransformOffset": "(Values=((X=0.000000,Y=0.000000,Z=1100.000000),(X=0.000000,Y=0.000000,Z=1100.000000)),ValuesTimeRange=(X=0.000000,Y=1.000000),Mode=NonUniformConstant,ChannelConstantsAndRanges=(0.000000,0.000000,1100.000000))"}
    new_system("NS_DKF_PetalDrift", {
        "spawn": [spawn_rate(26, 34)], "bounds": ((-5000, -5000, -300), (5000, 5000, 2000)), "est": 30 * 12,
        "modules": petal_modules((10, 14), 1.0, 1.4, box, 110, 95), "renderer": ("mesh", MESH_R)})
    # 2 canopy fall per CherrySlot: a 3 m sphere at the actor (placed 0.6 x the slot height up), 2-5 /s, life 7-10 s
    sph = {"ShapePrimitive": "Sphere", "SphereRadius": d_range(0, 300)}
    new_system("NS_DKF_PetalCanopy", {
        "spawn": [spawn_rate(2, 5)], "bounds": ((-1500, -1500, -900), (1500, 1500, 500)), "est": 3.5 * 8.5,
        "modules": petal_modules((7, 10), 1.0, 1.4, sph, 90, 90), "renderer": ("mesh", MESH_R)})
    # 3 mist puffs at the rapids: 2-4 /s, life 4-7 s, 3-7 m sprites (x 1.4: the visible mist is ~0.7 of the cell), rising
    #   20-50 cm/s and drifting down-stream (actor +X = down-stream) 60-150 cm/s, alpha 0.25-0.45 with a fade in / out
    fade = [(0.0, 0.0), (0.18, 1.0), (0.7, 0.8), (1.0, 0.0)]
    common_sub = {"SubUVAnimation": {"NumFrames": "64", "AnimationMode": "Linear"}}
    new_system("NS_DKF_MistPuff", {
        "spawn": [spawn_rate(2, 4)], "bounds": ((-1500, -1500, -400), (2500, 1500, 1200)), "est": 3 * 5.5,
        "modules": dict(common_sub, **{
            "InitializeParticle": {"LifetimeDistribution": d_range(4, 7), "SpriteSizeDistribution": d_v2(420, 980),
                                   "SpriteRotationDistribution": d_range(-15, 15),
                                   "ColorDistribution": d_color_range((1, 1, 1, 0.25), (1, 1, 1, 0.45))},
            "ShapeLocation": {"ShapePrimitive": "Sphere", "SphereRadius": d_range(0, 250)},
            "AddVelocity": {"VelocityType": "Linear", "LinearVelocityDistribution": d_v3((60, -20, 20), (150, 20, 50)),
                            "CoordinateSpace": "Local"},
            "ScaleColor": {"ScaleDistribution": d_color_alpha_curve(fade)},
            "ScaleSpriteSize": {"ScaleDistribution": d_scale_curve2([(0.0, 0.6), (1.0, 1.25)])}}),
        "renderer": ("sprite", sprite_r("MI_DKF_MistPuff"))})
    # 4 wisps along the river: 4-8 /s per actor... per actor 1-2 /s (several actors along the reach), life 6-10 s,
    #   (8-14) x (4-7) m, down-stream 80-200 cm/s + up 10-30, alpha 0.2-0.35
    new_system("NS_DKF_MistWisp", {
        "spawn": [spawn_rate(1.0, 2.0)], "bounds": ((-1500, -1500, -400), (3500, 1500, 1000)), "est": 1.5 * 8,
        "modules": dict(common_sub, **{
            "InitializeParticle": {"LifetimeDistribution": d_range(6, 10),
                                   "SpriteSizeDistribution": d_v2((1120, 560), (1960, 980), uniform=False),
                                   "SpriteRotationDistribution": d_range(-6, 6),
                                   "ColorDistribution": d_color_range((1, 1, 1, 0.2), (1, 1, 1, 0.35))},
            "ShapeLocation": {"ShapePrimitive": "Box", "BoxSize": d_v3((1200, 900, 60))},
            "AddVelocity": {"VelocityType": "Linear", "LinearVelocityDistribution": d_v3((80, -20, 10), (200, 20, 30)),
                            "CoordinateSpace": "Local"},
            "ScaleColor": {"ScaleDistribution": d_color_alpha_curve(fade)}}),
        "renderer": ("sprite", sprite_r("MI_DKF_MistWisp"))})
    # 5 spray bursts on the boulder faces: 1 every 0.8-1.8 s, life 0.64-0.9 s (64 frames), pivot (0.5, 0.96); probe pb:
    #   the catalog's 1.5-3 m sheets read as large white cut-outs from the elevated cameras: 1.0-1.8 m, opacity 0.6
    new_system("NS_DKF_RapidSpray", {
        "spawn": [spawn_rate(0.55, 1.25)], "bounds": ((-500, -500, -100), (500, 500, 600)), "est": 0.9 * 0.77,
        "modules": dict(common_sub, **{
            "InitializeParticle": {"LifetimeDistribution": d_range(0.64, 0.9), "SpriteSizeDistribution": d_v2(100, 180),
                                   "SpriteRotationDistribution": d_range(-8, 8),
                                   "ColorDistribution": d_color_const((1, 1, 1, 1))},
            "ShapeLocation": {"ShapePrimitive": "Sphere", "SphereRadius": d_range(0, 40)}}),
        "renderer": ("sprite", sprite_r("MI_DKF_SprayBurst", facing="FaceCameraPosition", pivot=(0.5, 0.96)))})
    # 6 droplets thrown by the splashes: ~80 /s per boulder in short bursts approximated by a rate, cone 35 deg up,
    #   250-450 cm/s, gravity, life 0.6-0.9 s, 2-4 cm drops (legibility over the catalog's 1-3 cm), velocity-aligned
    new_system("NS_DKF_SprayDroplets", {
        "spawn": [spawn_rate(50, 90)], "bounds": ((-600, -600, -100), (600, 600, 700)), "est": 70 * 0.75,
        "modules": {
            "InitializeParticle": {"LifetimeDistribution": d_range(0.6, 0.9), "SpriteSizeDistribution": d_v2(2, 4),
                                   "ColorDistribution": d_color_const((1, 1, 1, 0.9))},
            "ShapeLocation": {"ShapePrimitive": "Sphere", "SphereRadius": d_range(0, 50)},
            "AddVelocity": {"VelocityType": "InCone", "ConeVelocityDistribution": d_range(250, 450), "ConeAngle": "35.0",
                            "CoordinateSpace": "Local"},
            "GravityForce": {"GravityDistribution": d_v3((0, 0, -980))},
            "ScaleColor": {"ScaleDistribution": d_color_alpha_curve([(0.0, 1.0), (0.7, 1.0), (1.0, 0.0)])},
            "ScaleSpriteSizeBySpeed": {}},
        "renderer": ("sprite", dict(sprite_r("MI_DKF_Droplet", sub=False, align="VelocityAligned", sort="None",
                                             maxd=6000.0)))})
    # 7 haze sheets: 20-40 x 8-12 m, Z-locked (face the camera position, up = Z), life 25-40 s, down-stream 20-50 cm/s,
    #   alpha 0.12-0.2
    new_system("NS_DKF_RiverHaze", {
        "spawn": [spawn_rate(0.12, 0.2)], "bounds": ((-3000, -2500, -300), (5000, 2500, 1200)), "est": 0.16 * 32,
        "modules": {
            "InitializeParticle": {"LifetimeDistribution": d_range(25, 40),
                                   "SpriteSizeDistribution": d_v2((2000, 800), (4000, 1200), uniform=False),
                                   "ColorDistribution": d_color_range((1, 1, 1, 0.12), (1, 1, 1, 0.2))},
            "ShapeLocation": {"ShapePrimitive": "Box", "BoxSize": d_v3((2000, 1200, 100))},
            "AddVelocity": {"VelocityType": "Linear", "LinearVelocityDistribution": d_v3((20, -5, 0), (50, 5, 3)),
                            "CoordinateSpace": "Local"},
            "ScaleColor": {"ScaleDistribution": d_color_alpha_curve([(0.0, 0.0), (0.25, 1.0), (0.75, 1.0), (1.0, 0.0)])}},
        "renderer": ("sprite", sprite_r("MI_DKF_RiverHaze", sub=False, facing="FaceCameraPosition", maxd=60000.0))})


def step(name, fn):
    t = time.time()
    try:
        fn()
    except Exception:  # noqa: BLE001
        REP["errors"].append(name)
        REP.setdefault("tracebacks", {})[name] = traceback.format_exc()[-2500:]
    REP.setdefault("sec", {})[name] = round(time.time() - t, 1)


def main():
    t0 = time.time()
    for name, fn in (("six_way", six_way), ("haze", haze), ("droplet", droplet), ("scatter_decal", scatter_decal),
                     ("foam_wake", foam_wake), ("petal_usage", petal_usage), ("systems", systems)):
        step(name, fn)
    try:
        EAL.delete_directory(f"{FX}/ProbeTmp")
    except Exception:  # noqa: BLE001
        pass
    REP["passed"] = not REP["errors"] and not REP["set_errors"] and all(
        v.get("saved") for v in REP["systems"].values()) and len(REP["systems"]) == 7
    REP["sec_total"] = round(time.time() - t0, 1)
    (O / "json").mkdir(parents=True, exist_ok=True)
    (O / "json/fxl_assets.json").write_text(json.dumps(REP, indent=1, default=str), encoding="utf-8")
    unreal.log(f"DJ_STEP_DONE fxl_assets passed={REP['passed']} errors={REP['errors']} set_errors={len(REP['set_errors'])} "
               f"systems={len(REP['systems'])} materials={len(REP['materials'])}")


main()
