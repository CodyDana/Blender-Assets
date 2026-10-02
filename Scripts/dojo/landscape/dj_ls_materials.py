"""LANDSCAPE ROUND (world stage), Unreal step 2 (pythonscript commandlet, -nullrhi): the materials of this round, built
here and only here (DojoLab's own /Game/DojoKit and /Game/DojoLandscape folders; nothing in Scripts/unreal/materials,
nothing in any content source):

  stone kit   MIs of the existing M_DJ_Lib_Opaque / M_DJ_Lib_Emissive masters, one per kit slot, in
              /Game/DojoKit/StoneKit/Materials, the tone from stone_tone.json (MEASURED mid-grey granite, R/B ~1.09,
              saturation 0.08; the kit's f3 catalog tone read tan); moss by the kit's 'Wear' vertex alpha (UseMoss)
  pines       masters M_DKN_Bark (UV0 tiling bark x Tint, UV2 unique AO, vertex G moss, B branch AO),
              M_DKN_Needle (Two Sided Foliage, subsurface = BC x SubsurfaceTint x SSS x strength, canopy AO from
              UV3.x, Pivot Painter 2 wind: each pad rotates about its PP2 pivot (UV2 -> PivotPos EXR / XVector) round the
              horizontal axis across its branch, weighted by vertex R, phase = vertex G + an actor hash; needle flutter by
              vertex B; Max WPO displacement 6 cm) and M_DKN_RockUnique (the library granite tiled on UV0 x S/4 under the
              rock's unique N / ORM / M maps: moss, lichen, dirt); MIs per variant; the mound / moss / soil / pine-rock
              slots are Lib_Opaque MIs of the kit's own maps
  landscape   M_DJL_Valley: layers by world masks + slope, owned textures only (Fishermans grass / dirt / rock 4K,
              Scenery_Tutorial Megascans moss / mossy rock / forest ground / creek stones), T_MacroVariation, shared
              wrap samplers; M_DJL_Far: forest canopy / rock / snow by HEIGHT + SLOPE (the snow-peak material we make),
              world-space only so the same material dresses SM_Mountain_01 meshes
  water       MI_DJL_River: child of the engine's Water_Material_River, retuned turquoise
  rocks       MI_DJL_Rocks_Granite: child of Fishermans MI_Rocks_01, tint toward the kit's granite (measured)
  fx          M_DKF_Petal (two-sided masked) + MIs on the petal meshes (the FX stage builds the systems)
Also exports the owned stamps + T_Rocks_D to PNG (world/stamps) for make_terrain.py / the rock tone check.
Result: WorkFiles/dojo/build/landscape/world/json/ls_materials.json
"""
import json
import os
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
import unreal  # noqa: E402

EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
MP = unreal.MaterialProperty
ST = unreal.MaterialSamplerType
W = ROOT / "WorkFiles/dojo/build/landscape/world"
TONE = json.loads((W / "json/stone_tone.json").read_text(encoding="utf-8"))
CAT = json.loads((ROOT / "WorkFiles/dojo/build/stonekit/kit_catalog.json").read_text(encoding="utf-8"))
MASTERS = "/Game/DojoKit/Materials/Masters"
LIBTEX = "/Game/DojoKit/Materials/Textures"
PTEX = "/Game/DojoKit/Pines/Textures"
PMAT = "/Game/DojoKit/Pines/Materials"
SMAT = "/Game/DojoKit/StoneKit/Materials"
LMAT = "/Game/DojoLandscape/Materials"
REP = {"engine": unreal.SystemLibrary.get_engine_version(), "errors": [], "masters": {}, "instances": {}, "meshes": {},
       "probes": {}}


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
        e = MEL.create_material_expression(self.m, cls, -500 - 260 * (self.n // 12), 130 * (self.n % 12))
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

    def div(self, a, b):
        return self._bin(unreal.MaterialExpressionDivide, a, b)

    def append(self, a, b):
        return self._bin(unreal.MaterialExpressionAppendVector, a, b)

    def cross(self, a, b):
        return self._bin(unreal.MaterialExpressionCrossProduct, a, b)

    def dot(self, a, b):
        return self._bin(unreal.MaterialExpressionDotProduct, a, b)

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

    def smoothstep(self, a, lo, hi):
        x = self.sat(self.div(self.sub(a, lo if isinstance(lo, tuple) else self.const(lo)),
                              self.const(hi - lo) if not isinstance(lo, tuple) else hi))
        return self.mul(self.mul(x, x), self.sub(self.const(3.0), self.mul(self.const(2.0), x)))

    def uv(self, i):
        return (self.node(unreal.MaterialExpressionTextureCoordinate, coordinate_index=i), "")

    def t2d(self, pname, kind, texture, uv, shared=False, group="Textures"):
        st = {"C": ST.SAMPLERTYPE_COLOR, "L": ST.SAMPLERTYPE_LINEAR_COLOR, "M": ST.SAMPLERTYPE_MASKS,
              "N": ST.SAMPLERTYPE_NORMAL, "G": ST.SAMPLERTYPE_GRAYSCALE, "LG": ST.SAMPLERTYPE_LINEAR_GRAYSCALE}[kind]
        # owned pack textures are not always stored the way their names say (Fishermans T_Rocks_N is a linear colour
        # texture, not a normal map): the sampler type follows the texture's own compression / sRGB flag
        cs = str(texture.get_editor_property("compression_settings")).upper()
        srgb = bool(texture.get_editor_property("srgb"))
        if kind in ("C", "L") and "MASKS" in cs:
            st = ST.SAMPLERTYPE_MASKS
        elif kind in ("C", "L") and "GRAYSCALE" in cs:
            st = ST.SAMPLERTYPE_GRAYSCALE if srgb else ST.SAMPLERTYPE_LINEAR_GRAYSCALE
        elif kind in ("C", "L"):
            st = ST.SAMPLERTYPE_COLOR if srgb else ST.SAMPLERTYPE_LINEAR_COLOR
        elif kind == "N" and "NORMALMAP" not in cs:
            st = ST.SAMPLERTYPE_LINEAR_COLOR
            REP.setdefault("normal_as_linear", []).append(texture.get_path_name())
        elif kind == "M" and "MASKS" not in cs:
            st = ST.SAMPLERTYPE_COLOR if srgb else ST.SAMPLERTYPE_LINEAR_COLOR
        elif kind in ("G", "LG") and "GRAYSCALE" not in cs:
            st = ST.SAMPLERTYPE_COLOR if srgb else ST.SAMPLERTYPE_LINEAR_COLOR
        t = self.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name=pname, sampler_type=st,
                      texture=texture, group=group)
        if shared:
            t.set_editor_property("sampler_source", unreal.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS)
        if uv is not None:
            self.link(uv[0], uv[1], t, "UVs")
        return t

    def wp(self):
        return (self.node(unreal.MaterialExpressionWorldPosition), "")

    def vc(self):
        return self.node(unreal.MaterialExpressionVertexColor)

    def nws(self):
        return (self.node(unreal.MaterialExpressionVertexNormalWS), "")

    def time(self):
        return (self.node(unreal.MaterialExpressionTime), "")

    def sine(self, a):
        return self.un(unreal.MaterialExpressionSine, a, period=1.0)


def FOLIAGE_SM():
    M = unreal.MaterialShadingModel
    return next(getattr(M, n) for n in dir(M) if "FOLIAGE" in n.upper() and "TWO" in n.upper())


def reset(mat, shading=unreal.MaterialShadingModel.MSM_DEFAULT_LIT, blend=unreal.BlendMode.BLEND_OPAQUE,
          two_sided=False):
    MEL.delete_all_material_expressions(mat)
    mat.set_editor_property("blend_mode", blend)
    mat.set_editor_property("shading_model", shading)
    mat.set_editor_property("two_sided", two_sided)
    # usage flags set up front (a flag the engine has to add at load time is passed back to the game thread; with
    # the Voxels flag on the Nanite-Voxelize needles that raced and crashed a load in run 3)
    for k, v in (("used_with_nanite", True), ("used_with_instanced_static_meshes", True), ("used_with_voxels", True),
                 ("used_with_skeletal_mesh", False)):
        try:
            mat.set_editor_property(k, v)
        except Exception:  # noqa: BLE001
            pass


def finish(mat, path):
    MEL.layout_material_expressions(mat)
    MEL.recompile_material(mat)
    ok = bool(EAL.save_loaded_asset(mat, False))
    REP["masters"][path] = {"expressions": int(MEL.get_num_material_expressions(mat)), "saved": ok}


def make_mi(path, parent, scalars=None, vectors=None, textures=None, switches=None):
    mi = get_or_create(path, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.clear_all_material_instance_parameters(mi)
    MEL.set_material_instance_parent(mi, parent)
    for k, v in (scalars or {}).items():
        MEL.set_material_instance_scalar_parameter_value(mi, k, float(v))
    for k, v in (vectors or {}).items():
        MEL.set_material_instance_vector_parameter_value(mi, k, lc(v))
    for k, v in (textures or {}).items():
        MEL.set_material_instance_texture_parameter_value(mi, k, tex(v) if isinstance(v, str) else v)
    for k, v in (switches or {}).items():
        MEL.set_material_instance_static_switch_parameter_value(mi, k, bool(v))
    MEL.update_material_instance(mi)
    EAL.save_loaded_asset(mi, False)
    REP["instances"][path] = {"parent": parent.get_path_name(), "scalars": scalars or {}, "vectors": vectors or {},
                              "textures": {k: (v if isinstance(v, str) else v.get_path_name())
                                           for k, v in (textures or {}).items()}}
    return mi


def assign(mesh_path, mapping):
    mesh = unreal.load_asset(mesh_path)
    rec = {"slots": {}, "unmatched": []}
    for i, s in enumerate(mesh.get_editor_property("static_materials")):
        slot = str(s.get_editor_property("material_slot_name"))
        mi = mapping(slot)
        if mi is None:
            rec["unmatched"].append(slot)
            continue
        mesh.set_material(i, mi)
        rec["slots"][slot] = mi.get_path_name()
    rec["saved"] = bool(EAL.save_loaded_asset(mesh, False))
    REP["meshes"][mesh_path] = rec


def step(name, fn):
    try:
        fn()
    except Exception:  # noqa: BLE001
        REP["errors"].append(name)
        REP.setdefault("tracebacks", {})[name] = traceback.format_exc()[-2500:]


# ---------------------------------------------------------------------------------------------------- exports
def export_pngs():
    out = W / "stamps"
    out.mkdir(parents=True, exist_ok=True)
    rec = {}
    for p in ("/Game/Landscape/Patches/T_Land_Mountain01", "/Game/Landscape/Patches/T_Land_Mountain02",
              "/Game/Landscape/Patches/T_Land_Erosion00", "/Game/Landscape/Patches/T_Land_Erosion01",
              "/Game/Fishermans_Cabin/Textures/Tiling_Textures/Rock/T_Rocks_D",
              "/Game/Fishermans_Cabin/Textures/Rocks/T_Rocks_Mask"):
        t = unreal.load_asset(p)
        task = unreal.AssetExportTask()
        fn = str(out / (p.rsplit("/", 1)[1] + ".png"))
        for k, v in (("object", t), ("filename", fn), ("automated", True), ("prompt", False), ("replace_identical", True)):
            task.set_editor_property(k, v)
        try:
            task.set_editor_property("exporter", unreal.TextureExporterPNG())
        except Exception:  # noqa: BLE001
            pass
        ok = unreal.Exporter.run_asset_export_task(task)
        rec[p] = {"ok": bool(ok), "file": fn, "exists": Path(fn).exists(),
                  "size": [int(t.blueprint_get_size_x()), int(t.blueprint_get_size_y())]}
    REP["exports"] = rec


def probes():
    P = REP["probes"]
    for p in ("/Game/Fishermans_Cabin/Materials/Material_Instances/Unique/MI_Rocks_01",
              "/Game/Fishermans_Cabin/Materials/Material_Instances/Tiling/MI_Mountain",
              "/Water/Materials/WaterSurface/Water_Material_River",
              "/Game/Fishermans_Cabin/Materials/Material_Instances/Foliage/MI_Tree_Leaves"):
        m = unreal.load_asset(p)
        if m is None:
            P[p] = None
            continue
        r = {"class": type(m).__name__}
        try:
            r["scalars"] = {str(n): round(float(MEL.get_material_instance_scalar_parameter_value(m, n)), 4)
                            for n in MEL.get_scalar_parameter_names(m)}
            r["vectors"] = {}
            for n in MEL.get_vector_parameter_names(m):
                c = MEL.get_material_instance_vector_parameter_value(m, n)
                r["vectors"][str(n)] = [round(c.r, 4), round(c.g, 4), round(c.b, 4), round(c.a, 4)]
            r["textures"] = [str(n) for n in MEL.get_texture_parameter_names(m)]
            r["switches"] = [str(n) for n in MEL.get_static_switch_parameter_names(m)]
        except Exception as exc:  # noqa: BLE001
            r["err"] = str(exc)[:200]
        P[p] = r
    for p in ("/Game/Megaplant_Library/Tree_Japanese_Cypress/Tree_Japanese_Cypress_01/Tree_Japanese_Cypress_01_A",
              "/Game/Fishermans_Cabin/Meshes/Foliage/Tree/SM_Fir_Tree_01",
              "/Game/Fishermans_Cabin/Meshes/Foliage/Tree/SMF_Fir_Tree_Billboard",
              "/Game/Fishermans_Cabin/Meshes/Mountains/SM_Mountain_01",
              "/Game/Fishermans_Cabin/Meshes/Rocks/SM_Rocks_02",
              "/Game/DojoKit/Greybox/Meshes/SM_DGB_Tree"):
        a = unreal.load_asset(p)
        r = {"class": type(a).__name__ if a else None}
        if isinstance(a, unreal.StaticMesh):
            bb = a.get_bounding_box()
            r["bbox_cm"] = [[round(bb.min.x), round(bb.min.y), round(bb.min.z)], [round(bb.max.x), round(bb.max.y),
                                                                                   round(bb.max.z)]]
            r["nanite"] = bool(a.get_editor_property("nanite_settings").get_editor_property("enabled"))
            agg = a.get_editor_property("body_setup").get_editor_property("agg_geom")
            r["convex"] = len(agg.get_editor_property("convex_elems"))
            r["boxes"] = len(agg.get_editor_property("box_elems"))
            r["spheres"] = len(agg.get_editor_property("sphyl_elems"))
            r["materials"] = [m.get_editor_property("material_interface").get_path_name() if m.get_editor_property(
                "material_interface") else None for m in a.get_editor_property("static_materials")]
        elif a is not None:
            try:
                bb = a.get_bounds()
                r["bounds"] = str(bb)[:300]
            except Exception as exc:  # noqa: BLE001
                r["bounds_err"] = str(exc)[:120]
        P[p] = r


# ---------------------------------------------------------------------------------------------------- stone kit
def stone():
    opaque = unreal.load_asset(f"{MASTERS}/M_DJ_Lib_Opaque")
    emissive = unreal.load_asset(f"{MASTERS}/M_DJ_Lib_Emissive")
    gran = {"BC": f"{LIBTEX}/T_DJ_Granite_BC", "ORM": f"{LIBTEX}/T_DJ_Granite_ORM", "N": f"{LIBTEX}/T_DJ_Granite_N",
            "WearMask": f"{LIBTEX}/T_DJ_WearMask_M"}
    mis = {}
    for slot, v in TONE["slots"].items():
        u = v["unreal"]
        mis[slot] = make_mi(f"{SMAT}/{slot}", opaque,
                            scalars={"FlattenToMean": u["FlattenToMean"], "Saturation": u["Saturation"],
                                     "NormalStrength": u["NormalStrength"], "RoughMult": 1.0, "AOStrength": 0.4,
                                     "ValueMult": 1.0},
                            vectors={"Tint": u["Tint"], "MeanColour": u["MeanColour"], "MossColour": u["MossColour"],
                                     "TileM": [4, 4, 0, 0]},
                            textures=gran, switches={"UseWear": True, "UseMoss": True})
    lib = "/Game/DojoKit/Materials/Materials/Library"
    tim = {"BC": f"{LIBTEX}/T_DJ_TimberDark_BC", "ORM": f"{LIBTEX}/T_DJ_TimberDark_ORM", "N": f"{LIBTEX}/T_DJ_TimberDark_N",
           "WearMask": f"{LIBTEX}/T_DJ_WearMask_M"}
    time_end = dict(tim, BC=f"{LIBTEX}/T_DJ_TimberDarkEnd_BC", ORM=f"{LIBTEX}/T_DJ_TimberDarkEnd_ORM",
                    N=f"{LIBTEX}/T_DJ_TimberDarkEnd_N")
    # the rails / posts / lantern body: the library dark timber look (round-9 values) x the kit's weathered tint
    base = unreal.load_asset(f"{lib}/M_DJ_TimberDark")
    sc = {n: float(MEL.get_material_instance_scalar_parameter_value(base, n)) for n in
          ("ValueMult", "Saturation", "AOStrength", "FlattenToMean", "NormalStrength", "RoughMult")}
    mean = MEL.get_material_instance_vector_parameter_value(base, "MeanColour")
    mis["M_DKT_TimberWeathered"] = make_mi(f"{SMAT}/M_DKT_TimberWeathered", opaque, scalars=sc,
                                           vectors={"Tint": [0.38 * 2.2, 0.355 * 2.2, 0.34 * 2.2],
                                                    "MeanColour": [mean.r * 0.8, mean.g * 0.85, mean.b * 0.9],
                                                    "TileM": [4, 4, 0, 0]}, textures=tim, switches={"UseWear": True})
    mis["M_DKT_TimberWeatheredEnd"] = make_mi(f"{SMAT}/M_DKT_TimberWeatheredEnd", opaque, scalars=sc,
                                              vectors={"Tint": [0.38 * 2.2, 0.355 * 2.2, 0.34 * 2.2],
                                                       "MeanColour": [mean.r * 0.7, mean.g * 0.75, mean.b * 0.8],
                                                       "TileM": [2, 2, 0, 0]}, textures=time_end,
                                              switches={"UseWear": True})
    roof = unreal.load_asset(f"{lib}/M_DJ_RoofTile")
    rs = {n: float(MEL.get_material_instance_scalar_parameter_value(roof, n)) for n in
          ("ValueMult", "Saturation", "RoughMult", "FlattenToMean", "Specular", "AOStrength")}
    mis["M_DKT_HoodCharcoal"] = make_mi(f"{SMAT}/M_DKT_HoodCharcoal", opaque, scalars=rs,
                                        vectors={"Tint": [0.85, 0.97, 1.3], "MeanColour": [0.045, 0.05, 0.072],
                                                 "TileM": [4, 4, 0, 0]},
                                        textures={"BC": f"{LIBTEX}/T_DJ_RoofTile_BC", "ORM": f"{LIBTEX}/T_DJ_RoofTile_ORM",
                                                  "N": f"{LIBTEX}/T_DJ_RoofTile_N"}, switches={"UseWear": False})
    glass = unreal.load_asset(f"{lib}/M_DJ_GlassAmber")
    gs = {n: float(MEL.get_material_instance_scalar_parameter_value(glass, n)) for n in
          ("EmissiveIntensity", "BaseMult", "RoughMult", "NormalStrength", "Saturation")}
    gs["EmissiveIntensity"] = gs["EmissiveIntensity"] * 1.15 / 5.0 * 4.0
    mis["M_DKT_GlassAmberWarm"] = make_mi(f"{SMAT}/M_DKT_GlassAmberWarm", emissive, scalars=gs,
                                          vectors={"EmissiveTint": [1.0, 0.55, 0.18]},
                                          textures={"BC": f"{LIBTEX}/T_DJ_GlassAmber_BC",
                                                    "ORM": f"{LIBTEX}/T_DJ_GlassAmber_ORM",
                                                    "N": f"{LIBTEX}/T_DJ_GlassAmber_N"})
    REP["stone_glass_emissive"] = gs["EmissiveIntensity"]
    shared = {"M_DJ_Granite_Tri": f"{lib}/M_DJ_Granite_Tri", "M_DJ_GlassAmber": f"{lib}/M_DJ_GlassAmber",
              "M_DJ_TimberDark": f"{lib}/M_DJ_TimberDark", "M_DJ_TimberDarkEnd": f"{lib}/M_DJ_TimberDarkEnd",
              "M_DKP_Stone_Moss": "/Game/DojoKit/Props/Stone/Materials/M_DKP_Stone_Moss"}

    def mp(slot):
        if slot in mis:
            return mis[slot]
        if slot in shared:
            return unreal.load_asset(shared[slot])
        return None
    for name in CAT["pieces"]:
        assign(f"/Game/DojoKit/StoneKit/Meshes/{name}", mp)


# ---------------------------------------------------------------------------------------------------- pines
def pine_masters():
    # M_DKN_Bark
    path = f"{PMAT}/Masters/M_DKN_Bark"
    m = get_or_create(path, unreal.Material, unreal.MaterialFactoryNew())
    reset(m)
    g = G(m)
    uv0 = g.mul(g.uv(0), g.scalar("BarkTile", 1.0, "UV"))
    bc = g.t2d("BarkBC", "C", tex(f"{PTEX}/T_DKN_Bark_BC"), uv0)
    orm = g.t2d("BarkORM", "M", tex(f"{PTEX}/T_DKN_Bark_ORM"), uv0)
    nm = g.t2d("BarkN", "N", tex(f"{PTEX}/T_DKN_Bark_N"), uv0)
    uao = g.t2d("TrunkORM", "M", tex(f"{PTEX}/T_DKN_PineA1_Trunk_ORM"), g.uv(2))
    vc = g.vc()
    col = g.mul((bc, "RGB"), g.vector("Tint", (1, 1, 1)))
    moss = g.mul(g.vector("MossTint", (0.10, 0.12, 0.03)), g.const(1.0))
    col = g.lerp(col, moss, g.sat(g.mul((vc, "G"), g.scalar("MossAmount", 1.0))))
    col = g.mul(col, g.lerp(g.const(1.0), (vc, "B"), g.scalar("BranchAO", 0.35)))
    lum = g.dot(col, g.const3((0.2126, 0.7152, 0.0722)))
    col = g.mul(g.lerp(lum, col, g.scalar("Saturation", 1.0)), g.scalar("ValueMult", 1.0))
    g.out(col, MP.MP_BASE_COLOR)
    ao = g.mul((orm, "R"), g.lerp(g.const(1.0), (uao, "R"), g.scalar("UniqueAO", 1.0)))
    g.out(ao, MP.MP_AMBIENT_OCCLUSION)
    g.out(g.mul((orm, "G"), g.scalar("RoughMult", 1.0)), MP.MP_ROUGHNESS)
    g.out(g.lerp(g.const3((0, 0, 1)), (nm, "RGB"), g.scalar("NormalStrength", 1.0)), MP.MP_NORMAL)
    finish(m, path)

    # M_DKN_Needle (Two Sided Foliage + PP2 wind)
    path = f"{PMAT}/Masters/M_DKN_Needle"
    m = get_or_create(path, unreal.Material, unreal.MaterialFactoryNew())
    reset(m, shading=FOLIAGE_SM(), two_sided=True)
    try:
        m.set_editor_property("max_world_position_offset_displacement", 6.0)
    except Exception as exc:  # noqa: BLE001
        REP["needle_maxwpo_err"] = str(exc)[:160]
    g = G(m)
    uv0 = g.uv(0)
    bc = g.t2d("NeedleBC", "C", tex(f"{PTEX}/T_DKN_Needle_BC"), uv0)
    orm = g.t2d("NeedleORM", "M", tex(f"{PTEX}/T_DKN_Needle_ORM"), uv0)
    nm = g.t2d("NeedleN", "N", tex(f"{PTEX}/T_DKN_Needle_N"), uv0)
    sss = g.t2d("NeedleSSS", "LG", tex(f"{PTEX}/T_DKN_Needle_SSS"), uv0)
    cao = g.lerp(g.scalar("CanopyAOMin", 0.55), g.const(1.0), g.mask(g.uv(3), "R"))
    col = g.mul(g.mul((bc, "RGB"), g.vector("Tint", (1, 1, 1))), cao)
    lum = g.dot(col, g.const3((0.2126, 0.7152, 0.0722)))
    col = g.mul(g.lerp(lum, col, g.scalar("Saturation", 1.0)), g.scalar("ValueMult", 1.0))
    g.out(col, MP.MP_BASE_COLOR)
    g.out((orm, "R"), MP.MP_AMBIENT_OCCLUSION)
    g.out(g.mul((orm, "G"), g.scalar("RoughMult", 1.0)), MP.MP_ROUGHNESS)
    g.out(g.lerp(g.const3((0, 0, 1)), (nm, "RGB"), g.scalar("NormalStrength", 1.0)), MP.MP_NORMAL)
    ssc = g.mul(g.mul(g.mul(col, g.vector("SubsurfaceTint", (1.0, 1.15, 0.55))), (sss, "")),
                g.scalar("TranslucencyStrength", 0.45))
    g.out(ssc, MP.MP_SUBSURFACE_COLOR)
    # --- Pivot Painter 2 pad sway (study 5.4 Route A): pivot + branch axis from the variant's PP2 textures at UV2
    uv2 = g.uv(2)
    pv = g.t2d("PivotPos", "L", tex(f"{PTEX}/T_DKN_PineA1_PivotPos"), uv2, group="Wind")
    xv = g.t2d("XVector", "L", tex(f"{PTEX}/T_DKN_PineA1_XVector"), uv2, group="Wind")
    piv_l = (pv, "RGB")
    tp = g.node(unreal.MaterialExpressionTransformPosition,
                transform_source_type=unreal.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL,
                transform_type=unreal.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD)
    g.link(piv_l[0], piv_l[1], tp, "")
    axis_l = g.sub(g.mul((xv, "RGB"), g.const(2.0)), g.const(1.0))
    tv = g.node(unreal.MaterialExpressionTransform,
                transform_source_type=unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,
                transform_type=unreal.MaterialVectorCoordTransform.TRANSFORM_WORLD)
    g.link(axis_l[0], axis_l[1], tv, "")
    rax = g.un(unreal.MaterialExpressionNormalize, g.add(g.cross((tv, ""), g.const3((0, 0, 1))),
                                                          g.const3((0.001, 0.0, 0.0))))
    vc = g.vc()
    h = g.un(unreal.MaterialExpressionFrac, g.mul(g.un(unreal.MaterialExpressionSine, g.dot(
        (g.node(unreal.MaterialExpressionObjectPositionWS), ""), g.const3((0.1299, 0.7823, 0.3772))), period=1.0),
        g.const(437.585)))
    wind = g.scalar("WindStrength", 1.0, "Wind")
    ph = g.add(g.mul(g.time(), g.scalar("PadSwayFreq", 0.35, "Wind")), g.add((vc, "G"), h))
    ang = g.mul(g.mul(g.sine(ph), g.scalar("PadSwayTurns", 0.004, "Wind")), wind)
    rot = g.node(unreal.MaterialExpressionRotateAboutAxis, period=1.0)
    g.link(rax[0], rax[1], rot, "NormalizedRotationAxis")
    g.link(ang[0], ang[1], rot, "RotationAngle")
    g.link(tp, "", rot, "PivotPoint")
    g.link(g.node(unreal.MaterialExpressionWorldPosition), "", rot, "Position")
    sway = g.mul((rot, ""), (vc, "R"))
    fl = g.mul(g.mul(g.mul(g.nws(), g.sine(g.add(g.mul(g.time(), g.scalar("TuftFlutterFreq", 2.2, "Wind")), (vc, "B")))),
                     g.scalar("TuftFlutterCm", 0.6, "Wind")), g.mul((vc, "R"), wind))
    g.out(g.add(sway, fl), MP.MP_WORLD_POSITION_OFFSET)
    finish(m, path)

    # M_DKN_RockUnique (study 4.9.5 a, simplified): library granite tiled x Tint under the rock's unique maps
    path = f"{PMAT}/Masters/M_DKN_RockUnique"
    m = get_or_create(path, unreal.Material, unreal.MaterialFactoryNew())
    reset(m)
    g = G(m)
    uv0 = g.uv(0)
    ts = g.mul(uv0, g.scalar("GraniteTile", 0.95, "UV"))
    gbc = g.t2d("GraniteBC", "C", tex(f"{LIBTEX}/T_DJ_Granite_BC"), ts)
    un = g.t2d("RockN", "N", tex(f"{PTEX}/T_DKN_PineD1_Rock_N"), uv0)
    uo = g.t2d("RockORM", "M", tex(f"{PTEX}/T_DKN_PineD1_Rock_ORM"), uv0)
    um = g.t2d("RockM", "M", tex(f"{PTEX}/T_DKN_PineD1_Rock_M"), uv0)
    mbc = g.t2d("MossBC", "C", tex(f"{PTEX}/T_DKN_Moss_BC"), g.mul(uv0, g.scalar("MossTile", 1.9, "UV")))
    col = g.lerp(g.mul((gbc, "RGB"), g.vector("Tint", (0.68, 0.67, 0.665))), g.vector("MeanColour", (0.12, 0.12, 0.115)),
                 g.scalar("FlattenToMean", 0.5))
    col = g.lerp(col, g.vector("Lichen", (0.34, 0.32, 0.18)), g.mul((um, "G"), g.const(0.8)))
    col = g.lerp(col, g.vector("Soil", (0.075, 0.058, 0.042)), g.mul((um, "B"), g.const(0.55)))
    col = g.lerp(col, g.mul((mbc, "RGB"), g.vector("MossTint", (1, 1, 1))), (um, "R"))
    g.out(col, MP.MP_BASE_COLOR)
    g.out((uo, "R"), MP.MP_AMBIENT_OCCLUSION)
    g.out(g.mul((uo, "G"), g.scalar("RoughMult", 1.0)), MP.MP_ROUGHNESS)
    g.out((un, "RGB"), MP.MP_NORMAL)
    finish(m, path)


def pines():
    pine_masters()
    bark = unreal.load_asset(f"{PMAT}/Masters/M_DKN_Bark")
    needle = unreal.load_asset(f"{PMAT}/Masters/M_DKN_Needle")
    rockm = unreal.load_asset(f"{PMAT}/Masters/M_DKN_RockUnique")
    opaque = unreal.load_asset(f"{MASTERS}/M_DJ_Lib_Opaque")
    common = {}
    common["MI_DKN_MoundMoss"] = make_mi(f"{PMAT}/MI_DKN_MoundMoss", opaque,
                                         scalars={"Saturation": 0.8, "ValueMult": 1.0, "NormalStrength": 1.0},
                                         vectors={"Tint": [0.95, 1.0, 0.85], "TileM": [1, 1, 0, 0]},
                                         textures={"BC": f"{PTEX}/T_DKN_Moss_BC", "ORM": f"{PTEX}/T_DKN_Moss_ORM",
                                                   "N": f"{PTEX}/T_DKN_Moss_N"}, switches={"UseWear": False})
    common["M_DKN_Soil"] = make_mi(f"{PMAT}/MI_DKN_Soil", opaque, scalars={"Saturation": 0.8},
                                   vectors={"Tint": [1, 1, 1], "TileM": [1, 1, 0, 0]},
                                   textures={"BC": f"{PTEX}/T_DKN_Soil_BC", "ORM": f"{PTEX}/T_DKN_Soil_ORM",
                                             "N": f"{PTEX}/T_DKN_Soil_N"}, switches={"UseWear": False})
    wall = TONE["slots"]["M_DKT_WallGranite"]["unreal"]
    common["MI_DKN_PineRock"] = make_mi(f"{PMAT}/MI_DKN_PineRock", opaque,
                                        scalars={"FlattenToMean": wall["FlattenToMean"], "Saturation": 0.3},
                                        vectors={"Tint": wall["Tint"], "MeanColour": wall["MeanColour"],
                                                 "TileM": [4, 4, 0, 0]},
                                        textures={"BC": f"{LIBTEX}/T_DJ_Granite_BC", "ORM": f"{LIBTEX}/T_DJ_Granite_ORM",
                                                  "N": f"{LIBTEX}/T_DJ_Granite_N", "WearMask": f"{LIBTEX}/T_DJ_WearMask_M"},
                                        switches={"UseWear": True})
    common["MI_DKN_Groundcover"] = make_mi(f"{PMAT}/MI_DKN_Groundcover", needle,
                                           vectors={"Tint": [1.25, 1.12, 0.62]}, scalars={"WindStrength": 0.0})
    variants = ["PineA1", "PineA2", "PineB1", "PineB2", "PineC1", "PineC2", "PineD1", "PineD2"]
    for v in variants:
        b = make_mi(f"{PMAT}/MI_DKN_{v}_Bark", bark, textures={"TrunkORM": f"{PTEX}/T_DKN_{v}_Trunk_ORM"})
        n = make_mi(f"{PMAT}/MI_DKN_{v}_Needle", needle, textures={"PivotPos": f"{PTEX}/T_DKN_{v}_PivotPos",
                                                                  "XVector": f"{PTEX}/T_DKN_{v}_XVector"})
        assign(f"/Game/DojoKit/Pines/Meshes/SM_DKN_{v}_Trunk", lambda s, b=b: b if "Bark" in s or "Trunk" in s else None)
        assign(f"/Game/DojoKit/Pines/Meshes/SM_DKN_{v}_Foliage",
               lambda s, n=n: common["MI_DKN_Groundcover"] if "Groundcover" in s else n)
        if v.startswith("PineD"):
            r = make_mi(f"{PMAT}/MI_DKN_{v}_Rock", rockm, textures={"RockN": f"{PTEX}/T_DKN_{v}_Rock_N",
                                                                    "RockORM": f"{PTEX}/T_DKN_{v}_Rock_ORM",
                                                                    "RockM": f"{PTEX}/T_DKN_{v}_Rock_M"},
                        vectors={"Tint": wall["Tint"], "MeanColour": wall["MeanColour"]})
            assign(f"/Game/DojoKit/Pines/Meshes/SM_DKN_{v}_Rock",
                   lambda s, r=r: common["MI_DKN_MoundMoss"] if "Moss" in s else r)
    for mnd in "ABCD":
        assign(f"/Game/DojoKit/Pines/Meshes/SM_DKN_BaseMound_{mnd}",
               lambda s: next((mi for k, mi in common.items() if k in s), common["MI_DKN_MoundMoss"]))


# ---------------------------------------------------------------------------------------------------- landscape
FT = "/Game/Fishermans_Cabin/Textures/Tiling_Textures"
MS = "/Game/Megascans/Surfaces"


def valley_master():
    path = f"{LMAT}/M_DJL_Valley"
    m = get_or_create(path, unreal.Material, unreal.MaterialFactoryNew())
    reset(m)
    g = G(m)
    wp = g.wp()
    xy = g.mask(wp, "RG")
    layers = [  # name, BC, N, tile m, tint
        # fix round: darker, greener (the 0.55 / 0.74 / 0.46 tint read tan in the 9 deg sun)
        ("Grass", f"{FT}/Ground_Grass/T_Grass_D", f"{FT}/Ground_Grass/T_Grass_N", 4.0, (0.40, 0.56, 0.30)),
        ("MossyGrass", f"{MS}/MossyGrass/T_MossyGrass_01_BC", f"{MS}/MossyGrass/T_MossyGrass_01_N", 3.0, (1, 1, 1)),
        ("MossyRock", f"{MS}/Mossy_Rocky_Ground_vcrkeax/T_Mossy_Rocky_Ground_vcrkeax_4K_D",
         f"{MS}/Mossy_Rocky_Ground_vcrkeax/T_Mossy_Rocky_Ground_vcrkeax_4K_N", 3.0, (1, 1, 1)),
        ("Forest", f"{MS}/ForestGround/T_ForestGround_A", f"{MS}/ForestGround/T_ForestGround_N", 4.0, (1, 1, 1)),
        ("Rock", f"{FT}/Rock/T_Rocks_D", f"{FT}/Rock/T_Rocks_N", 6.0, (0.9, 0.92, 0.95)),
        ("Dirt", f"{FT}/Ground_Dirt/T_Ground_Dirt_D", f"{FT}/Ground_Dirt/T_Ground_Dirt_N", 4.0, (1, 1, 1)),
        ("RiverBed", f"{MS}/MossyCreekStones/T_MossyCreekStones_A", f"{MS}/MossyCreekStones/T_MossyCreekStones_N", 3.0,
         (1, 1, 1)),
    ]
    S = {}
    for name, bcp, np_, tile, tint in layers:
        uvw = g.div(xy, g.mul(g.scalar(f"{name}Tile_m", tile, "Tiles"), g.const(100.0)))
        bc = g.t2d(f"{name}BC", "C", tex(bcp), uvw, shared=True, group="Layers")
        ntex = tex(np_)
        nm = g.t2d(f"{name}N", "N", ntex, uvw, shared=True, group="Layers")
        nrgb = (nm, "RGB")
        if "NORMALMAP" not in str(ntex.get_editor_property("compression_settings")).upper():
            nrgb = g.sub(g.mul(nrgb, g.const(2.0)), g.const(1.0))
        S[name] = (g.mul((bc, "RGB"), g.vector(f"{name}Tint", tint, "Tints")), nrgb)
    # FIX ROUND (delta 8): the slope rock (the cliff faces beside the stair, the steep banks) was projected straight
    # down (world XY), so every face over ~60 deg showed vertical streaks: triplanar for the Rock layer (XY / XZ / YZ,
    # weights |n|^4); the normals blend the same way (approximate, enough at landscape scale)
    nabs = g.un(unreal.MaterialExpressionAbs, g.nws())
    n2 = g.mul(nabs, nabs)
    n4 = g.mul(n2, n2)
    wsum = g.add(g.add(g.mask(n4, "R"), g.mask(n4, "G")), g.mask(n4, "B"))
    wx, wy, wz = (g.div(g.mask(n4, c), wsum) for c in ("R", "G", "B"))
    rtile = g.mul(g.scalar("RockTile_m", 6.0, "Tiles"), g.const(100.0))
    pos = g.mask(wp, "RGB")
    uv_yz = g.div(g.append(g.mask(pos, "G"), g.mask(pos, "B")), rtile)
    uv_xz = g.div(g.append(g.mask(pos, "R"), g.mask(pos, "B")), rtile)
    uv_xy = g.div(xy, rtile)
    rbc, rn = tex(f"{FT}/Rock/T_Rocks_D"), tex(f"{FT}/Rock/T_Rocks_N")
    tri_c, tri_n = None, None
    for k, (uvp, w) in enumerate(((uv_yz, wx), (uv_xz, wy), (uv_xy, wz))):
        c = g.t2d(f"RockTriBC{k}", "C", rbc, uvp, shared=True, group="Layers")
        nm = g.t2d(f"RockTriN{k}", "N", rn, uvp, shared=True, group="Layers")
        nr = (nm, "RGB")
        if "NORMALMAP" not in str(rn.get_editor_property("compression_settings")).upper():
            nr = g.sub(g.mul(nr, g.const(2.0)), g.const(1.0))
        cc, nn = g.mul((c, "RGB"), w), g.mul(nr, w)
        tri_c = cc if tri_c is None else g.add(tri_c, cc)
        tri_n = nn if tri_n is None else g.add(tri_n, nn)
    # it4: the owned T_Rocks_D is tan (sRGB 132, 107, 81); the steep banks read as pale tan earth: tinted to the owner's
    # mid-grey granite (linear 0.097 / 0.091 / 0.083, like the kit's measured wall tone)
    # it6: (0.42, 0.62, 1.0) read blue slate beside the stair: (0.45, 0.63, 0.95) = linear (0.104, 0.093, 0.079), R/B 1.13
    S["Rock"] = (g.mul(tri_c, g.vector("RockTint", (0.45, 0.63, 0.95), "Tints")), tri_n)
    # FIX ROUND (delta 2 / 12): the forest floor under the (now closed) fir canopy reads dark, not as tan litter
    S["Forest"] = (g.mul(S["Forest"][0], g.vector("ForestFloorDark", (0.45, 0.5, 0.42), "Tints")), S["Forest"][1])
    # the plan's world masks (make_world_layout.py -> T_DJL_ValleyMask): R dirt, G forest floor, B moss, A river bed
    mu = g.div(g.sub(g.mask(wp, "R"), g.scalar("MaskOriginX", -48200.0, "Mask")), g.scalar("MaskSize", 100800.0, "Mask"))
    mv = g.div(g.sub(g.mask(wp, "G"), g.scalar("MaskOriginY", -52200.0, "Mask")), g.scalar("MaskSize", 100800.0, "Mask"))
    mk = g.t2d("ValleyMask", "M", tex(f"{LIBTEX}/T_DJ_WearMask_M"), g.append(mu, mv), shared=False, group="Mask")
    macro = g.t2d("Macro", "C", tex("/Game/Landscape/Textures/T_MacroVariation"),
                  g.div(xy, g.const(9000.0)), shared=True, group="Mask")
    nz = g.mask(g.nws(), "B")
    rock_w = g.sub(g.const(1.0), g.smoothstep(nz, 0.70, 0.84))           # steeper than ~35-45 deg
    mossrock_w = g.mul(g.smoothstep(g.sub(g.const(1.0), nz), 0.06, 0.18), g.sub(g.const(1.0), rock_w))
    col, nrm = S["Grass"]
    col = g.lerp(col, S["MossyGrass"][0], g.mul((mk, "B"), g.const(0.7)))
    nrm = g.lerp(nrm, S["MossyGrass"][1], g.mul((mk, "B"), g.const(0.7)))
    col = g.lerp(col, S["Forest"][0], (mk, "G"))
    nrm = g.lerp(nrm, S["Forest"][1], (mk, "G"))
    col = g.lerp(col, S["MossyRock"][0], mossrock_w)
    nrm = g.lerp(nrm, S["MossyRock"][1], mossrock_w)
    col = g.lerp(col, S["Dirt"][0], (mk, "R"))
    nrm = g.lerp(nrm, S["Dirt"][1], (mk, "R"))
    col = g.lerp(col, S["Rock"][0], rock_w)
    nrm = g.lerp(nrm, S["Rock"][1], rock_w)
    col = g.lerp(col, S["RiverBed"][0], (mk, "A"))
    nrm = g.lerp(nrm, S["RiverBed"][1], (mk, "A"))
    col = g.mul(col, g.lerp(g.const(1.0), g.mul((macro, "RGB"), g.const(1.6)), g.scalar("MacroAmount", 0.35, "Mask")))
    # plan FZ4: beyond the near field the forest is a canopy colour under the billboards (not bare grass)
    dxy = g.sub(xy, g.append(g.const(2200.0), g.const(-1800.0)))
    dist = g.un(unreal.MaterialExpressionLength, dxy)
    # FIX ROUND (blocker 2): the canopy blend starts at 60 m (was 130 m) and is full by 170 m (was 320 m), and inside
    # the forest zones (mask G) the canopy colour takes 55 % from the first metre: the hills read as forest, not tan
    far_w = g.mul(g.smoothstep(dist, g.scalar("CanopyStart_cm", 6000.0, "Look"), g.scalar("CanopyRamp_cm", 11000.0, "Look")),
                  g.sub(g.const(1.0), (mk, "A")))
    far_w = g.sat(g.add(far_w, g.mul((mk, "G"), g.scalar("CanopyInForest", 0.55, "Look"))))
    # fix round it2: the canopy albedo 0.016 / 0.028 / 0.022 crushed the forest background (CAM_Ref2Match top half 23 -> 31 %
    #   under luma 40 in it1): a canopy-like 0.026 / 0.044 / 0.036
    canopy = g.mul(g.vector("Canopy", (0.026, 0.044, 0.036), "Look"),
                   g.add(g.const(0.55), g.mul(g.mask((macro, "RGB"), "R"), g.const(0.9))))
    col = g.lerp(col, canopy, g.mul(far_w, g.sub(g.const(1.0), g.mul(rock_w, g.const(0.6)))))
    lum = g.dot(col, g.const3((0.2126, 0.7152, 0.0722)))
    col = g.mul(g.lerp(lum, col, g.scalar("Saturation", 0.85, "Look")), g.scalar("ValueMult", 1.0, "Look"))
    g.out(col, MP.MP_BASE_COLOR)
    rough = g.lerp(g.scalar("RoughDry", 0.85), g.scalar("RoughWet", 0.45), (mk, "A"))
    g.out(rough, MP.MP_ROUGHNESS)
    g.out(g.lerp(g.const3((0, 0, 1)), nrm, g.scalar("NormalStrength", 0.8, "Look")), MP.MP_NORMAL)
    finish(m, path)
    return m


def far_master():
    """M_DJL_Far: the snow-peak material (height + slope), forest canopy and rock on the far landscape and on the owned
    SM_Mountain_01 meshes; world space only."""
    path = f"{LMAT}/M_DJL_Far"
    m = get_or_create(path, unreal.Material, unreal.MaterialFactoryNew())
    reset(m)
    g = G(m)
    wp = g.wp()
    xy = g.mask(wp, "RG")
    zm = g.div(g.mask(wp, "B"), g.const(100.0))
    nz = g.mask(g.nws(), "B")
    macro = g.t2d("Macro", "C", tex("/Game/Landscape/Textures/T_MacroVariation"), g.div(xy, g.const(60000.0)), True)
    noise = g.mask((macro, "RGB"), "R")
    rock = g.t2d("RockBC", "C", tex(f"{FT}/Rock/T_Rocks_D"), g.div(xy, g.const(4000.0)), True)
    snow = g.t2d("SnowBC", "C", tex(f"{MS}/Snow/T_snow_02_diff_1k"), g.div(xy, g.const(2500.0)), True)
    grass = g.t2d("GrassBC", "C", tex(f"{FT}/Ground_Grass/T_Grass_D"), g.div(xy, g.const(1500.0)), True)
    canopy = g.mul(g.vector("Canopy", (0.026, 0.044, 0.036)), g.add(g.const(0.55), g.mul(noise, g.const(0.9))))
    rockc = g.mul((rock, "RGB"), g.vector("RockTint", (0.55, 0.56, 0.6)))
    meadow = g.mul((grass, "RGB"), g.vector("MeadowTint", (0.55, 0.6, 0.45)))
    # forest on moderate slopes below the tree line, bare rock above it and on cliffs
    tree = g.sub(g.const(1.0), g.smoothstep(g.add(zm, g.mul(noise, g.const(250.0))), 780.0, 1050.0))
    forest_w = g.mul(tree, g.smoothstep(nz, 0.5, 0.66))
    col = g.lerp(rockc, canopy, forest_w)
    low = g.sub(g.const(1.0), g.smoothstep(zm, 2.0, 14.0))
    col = g.lerp(col, meadow, g.mul(low, g.smoothstep(nz, 0.85, 0.95)))
    snow_h = g.smoothstep(g.add(zm, g.mul(g.sub(noise, g.const(0.5)), g.scalar("SnowNoise_m", 260.0))),
                          g.scalar("SnowLine_m", 1120.0), g.scalar("SnowFade_m", 160.0))
    snow_s = g.smoothstep(nz, g.scalar("SnowSlopeMinNz", 0.42), g.const(0.2))
    snow_w = g.mul(snow_h, g.add(g.mul(snow_s, g.const(0.85)), g.const(0.15)))
    # FIX ROUND (delta 3): exposed rock ribs in the snowfield (the reference's ridged snow massifs): snow thins on the
    # steeper faces by a slope-scaled noise, so couloirs and ribs show
    rib = g.sat(g.mul(g.sub(g.add(noise, g.mul(g.sub(g.const(1.0), nz), g.scalar("RibSlope", 1.6))), g.const(0.95)),
                      g.const(3.0)))
    snow_w = g.mul(snow_w, g.sub(g.const(1.0), g.mul(rib, g.scalar("RibAmount", 0.55))))
    col = g.lerp(col, g.mul((snow, "RGB"), g.scalar("SnowBright", 1.15)), snow_w)
    # FIX ROUND (delta 3): aerial perspective in the albedo: the far layers go cool violet-blue with distance (1.5 ->
    # 7.5 km from the compound), so the ridges recede in steps instead of one brown at every depth; the sunset light
    # keeps the lit faces warm
    cdist = g.un(unreal.MaterialExpressionLength, g.sub(xy, g.append(g.const(2200.0), g.const(-1800.0))))
    ap = g.mul(g.smoothstep(cdist, g.scalar("AerialStart_cm", 150000.0, "Aerial"), g.scalar("AerialRamp_cm", 600000.0,
                                                                                                "Aerial")),
               g.scalar("AerialMax", 0.6, "Aerial"))
    ap = g.mul(ap, g.sub(g.const(1.0), g.mul(snow_w, g.const(0.6))))
    apc = g.vector("AerialColour", (0.30, 0.34, 0.52), "Aerial")
    col = g.lerp(col, apc, ap)
    g.out(col, MP.MP_BASE_COLOR)
    g.out(g.lerp(g.const(0.85), g.const(0.55), snow_w), MP.MP_ROUGHNESS)
    em = g.add(g.mul(g.mul(col, snow_w), g.scalar("SnowEmissiveLift", 0.0)),
               g.mul(g.mul(apc, ap), g.scalar("AerialEmissive", 0.0, "Aerial")))
    g.out(em, MP.MP_EMISSIVE_COLOR)
    finish(m, path)
    return m


def landscape():
    v = valley_master()
    f = far_master()
    make_mi(f"{LMAT}/MI_DJL_Valley", v)
    make_mi(f"{LMAT}/MI_DJL_Far", f)
    make_mi(f"{LMAT}/MI_DJL_Mountain", f, scalars={"SnowLine_m": 1120.0})


# the smoothstep helper above takes a tuple for a parameter-driven edge: patch G.smoothstep for (node, out) edges
def _ss(self, a, lo, hi):
    if isinstance(lo, tuple):
        x = self.sat(self.div(self.sub(a, lo), hi if isinstance(hi, tuple) else self.const(hi)))
    else:
        x = self.sat(self.div(self.sub(a, self.const(lo)), self.const(hi - lo)))
    return self.mul(self.mul(x, x), self.sub(self.const(3.0), self.mul(self.const(2.0), x)))


G.smoothstep = _ss


# ---------------------------------------------------------------------------------------------------- water, rocks, fx
def water():
    base = unreal.load_asset("/Water/Materials/WaterSurface/Water_Material_River")
    d = {}
    for n in ("Absorption", "Scattering", "Water Albedo"):
        c = MEL.get_material_instance_vector_parameter_value(base, n)
        d[n] = [c.r, c.g, c.b, c.a]
    REP["water_defaults"] = d
    # the engine's Absorption reads as a travel distance per channel (R 10 / G 150 / B 350: red dies first); turquoise
    # = green carried nearly as far as blue, a blue-green scattering, the default albedo kept
    ab, sc = d["Absorption"], d["Scattering"]
    make_mi(f"{LMAT}/MI_DJL_River", base,
            vectors={"Absorption": [ab[0] * 1.2, 260.0, 320.0, ab[3]],
                     "Scattering": [0.35, 1.0, 0.9, sc[3]]},
            # white water: more, finer, harder foam on the fast reach (velocity-driven in the engine graph)
            scalars={"Foam Boost": 3.0, "FoamContrast": 2.0, "River Foam Scale": 700.0,
                     "River Flowmap Detection Velocity": 32.0, "Foam powr": 0.12, "MaxFlowVelocity": 700.0})


def firs():
    """The Fishermans fir needles carry a warm Color Multiply (2.0, 1.3, 0.43) that read yellow at sunset; the
    reference's slope conifers are dark blue-green: child MIs, the pack's MIs untouched."""
    base = unreal.load_asset("/Game/Fishermans_Cabin/Materials/Material_Instances/Foliage/MI_Tree_Leaves")
    make_mi(f"{LMAT}/MI_DJL_FirLeaves", base, vectors={"Color Multiply": [0.62, 0.86, 0.55, 1.0]})
    bb = unreal.load_asset("/Game/Fishermans_Cabin/Materials/Material_Instances/Foliage/MI_Tree_Billboard")
    vn = [str(n) for n in MEL.get_vector_parameter_names(bb)]
    REP["billboard_params"] = {"vectors": vn, "scalars": [str(n) for n in MEL.get_scalar_parameter_names(bb)]}
    vec = {"Color Multiply": [0.62, 0.86, 0.55, 1.0]} if "Color Multiply" in vn else {}
    make_mi(f"{LMAT}/MI_DJL_FirBillboard", bb, vectors=vec)


def foam():
    """M_DJL_RapidsFoam: translucent lit white water on the rapids strips. Two layers of the engine's
    T_WaterFlow_01_Foam_Tiled (2K) panning down-stream (world UVs, the reach's mean flow direction), broken up by our
    T_DKF_Foam_M, faded at the strip's long edges (plane UV v)."""
    path = f"{LMAT}/M_DJL_RapidsFoam"
    m = get_or_create(path, unreal.Material, unreal.MaterialFactoryNew())
    reset(m, blend=unreal.BlendMode.BLEND_TRANSLUCENT)
    try:
        m.set_editor_property("translucency_lighting_mode", unreal.TranslucencyLightingMode.TLM_SURFACE)
    except Exception:  # noqa: BLE001
        pass
    g = G(m)
    xy = g.div(g.mask(g.wp(), "RG"), g.const(100.0))            # metres
    flow = g.const3((-0.63, 0.77, 0.0))                         # UE xy of the R4 -> R7 mean flow
    t = g.time()
    ft = tex("/Water/Textures/Foam/T_WaterFlow_01_Foam_Tiled")
    fm = tex("/Game/DojoKit/FX/Textures/T_DKF_Foam_M")
    # FIX ROUND (delta 1): the isotropic tiles read as a cracked-ice web; the foam is now STREAKED along the flow
    # (flow-aligned UVs, ~3.5 : 1) and the breakup only modulates it at 25 m, so the white water reads as moving water
    along = g.dot(xy, g.mask(flow, "RG"))
    across = g.dot(xy, g.mask(g.const3((0.77, 0.63, 0.0)), "RG"))
    uv1 = g.append(g.div(across, g.scalar("Across1_m", 1.5)),
                   g.sub(g.div(along, g.scalar("Along1_m", 5.5)), g.mul(t, g.scalar("Speed1", 0.35))))
    uv2 = g.append(g.div(across, g.scalar("Across2_m", 0.65)),
                   g.sub(g.div(along, g.scalar("Along2_m", 2.2)), g.mul(t, g.scalar("Speed2", 0.75))))
    f1 = g.t2d("Foam1", "L", ft, uv1, group="Foam")
    f2 = g.t2d("Foam2", "L", ft, uv2, group="Foam")
    br = g.t2d("Breakup", "L", fm, g.div(xy, g.const(25.0)), group="Foam")
    v = g.mask(g.uv(0), "G")
    edge = g.mul(g.smoothstep(v, 0.0, 0.22), g.smoothstep(g.sub(g.const(1.0), v), 0.0, 0.22))
    # f = the two layers' mean (0.23 / 0.47 / 0.72 at p5 / p50 / p95 of the exported texture, fix/probe), the breakup
    # +-35 % at 25 m; opacity = smoothstep(f, Threshold, Soft); the colour runs from an aerated turquoise-grey in the
    # thin foam to white on the crests (a flat white sheet read as a sandbar in it1)
    f = g.mul(g.div(g.add(g.mask((f1, "RGB"), "R"), g.mul(g.mask((f2, "RGB"), "R"), g.const(0.7))), g.const(1.7)),
              g.lerp(g.const(1.0), g.mul(g.mask((br, "RGB"), "R"), g.const(3.8)), g.scalar("BreakupAmount", 0.35)))
    thr = g.scalar("Threshold", 0.31)
    op = g.sat(g.mul(g.mul(g.smoothstep(f, thr, g.scalar("Soft", 0.2)), edge), g.scalar("Opacity", 0.95)))
    crest = g.smoothstep(f, g.add(thr, g.const(0.05)), g.scalar("CrestSoft", 0.3))
    g.out(g.lerp(g.vector("GapColour", (0.2, 0.36, 0.36)), g.vector("FoamColour", (0.85, 0.88, 0.88)), crest),
          MP.MP_BASE_COLOR)
    g.out(g.const(0.6), MP.MP_ROUGHNESS)
    g.out(op, MP.MP_OPACITY)
    finish(m, path)
    # it5 measured sparse flecks on the rapids; the reference reads ~40 % white water there: a lower threshold
    # fix round: the runs (between the pours) and the pours (MI_DJL_RapidsFoamDrop: the water tumbling over a ledge
    # is near-solid white, faster)
    # coverage (fix/probe maths on the exported texture): run ~67 %, pour ~86 %, the reach's two ends ~49 % (no hard
    # edge where the white water starts / stops)
    # it4: run 0.30 -> 0.33 (it3 measured 89 % foam in the rapids boxes against the judge's 70-80 % target), pour 0.2 ->
    # 0.23; the reach's two ends fade over graded MIs (MI_DJL_RapidsFoamTail_0..5: ~45 % -> ~3 %), it3's two-step tail
    # still left a hard edge where the white water stopped
    # it6: it5 (the white water extended to key 8.3) measured 92 % in the boxes: run 0.37 (~55 %), pour 0.27 (~78 %)
    make_mi(f"{LMAT}/MI_DJL_RapidsFoam", m, scalars={"Threshold": 0.37, "Soft": 0.2, "Opacity": 0.95})
    make_mi(f"{LMAT}/MI_DJL_RapidsFoamDrop", m, scalars={"Threshold": 0.27, "Soft": 0.2, "Opacity": 1.0,
                                                         "Speed1": 0.9, "Speed2": 1.6, "Along1_m": 3.0})
    for i, (thr, op) in enumerate(((0.40, 0.9), (0.45, 0.8), (0.50, 0.7), (0.55, 0.6), (0.60, 0.5), (0.66, 0.4))):
        make_mi(f"{LMAT}/MI_DJL_RapidsFoamTail_{i}", m, scalars={"Threshold": thr, "Soft": 0.14, "Opacity": op})


def fir_voxelize():
    """Plan 3.11: the forest firs Voxelize (our DojoLab copies only; the vault source is never written)."""
    try:
        sms = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    except Exception:  # noqa: BLE001
        sms = None
    sms = sms or unreal.new_object(unreal.StaticMeshEditorSubsystem)
    rec = {}
    for i in range(1, 9):
        p = f"/Game/Fishermans_Cabin/Meshes/Foliage/Tree/SM_Fir_Tree_0{i}"
        mesh = unreal.load_asset(p)
        ns = mesh.get_editor_property("nanite_settings")
        before = str(ns.get_editor_property("shape_preservation")).split(".")[-1].split(":")[0]
        if "VOXEL" not in before.upper():
            ns.set_editor_property("shape_preservation", unreal.NaniteShapePreservation.VOXELIZE)
            sms.set_nanite_settings(mesh, ns, True)
            EAL.save_loaded_asset(mesh, False)
        after = str(mesh.get_editor_property("nanite_settings").get_editor_property("shape_preservation")).split(".")[-1]
        rec[p] = {"before": before, "after": after.split(":")[0]}
    REP["fir_voxelize"] = rec


def rocks():
    base = unreal.load_asset("/Game/Fishermans_Cabin/Materials/Material_Instances/Unique/MI_Rocks_01")
    # T_Rocks_D measures sRGB (132, 107, 81), saturation 0.39, R/B 1.63 (tan); the kit wall reads (123, 118, 113):
    # desaturate and cool through the master's own diffuse controls
    # it3 measured the switch path ("Enable Diffuse Color Controls?" + Diffuse Saturation / Tint) rendering the rocks
    # pure black (sRGB 0, 0, 0): the child MI keeps the pack's own colour path; its tone is measured in the captures
    # it7 still measured the rocks at sRGB (0, 0, 0) with the pack's own path: the master's RVT blend samples a
    # Runtime Virtual Texture that DojoLab has no volume for. Off, with the top-layer blend (also RVT-fed); the colour
    # stays the pack's (T_Rocks_D: sRGB (132, 107, 81))
    make_mi(f"{LMAT}/MI_DJL_Rocks_Granite", base,
            switches={"Enable RVT Blend?": False, "Enable Toplayer Blend?": False})
    small = unreal.load_asset("/Game/Fishermans_Cabin/Materials/Material_Instances/Unique/MI_Small_Rocks")
    make_mi(f"{LMAT}/MI_DJL_SmallRocks", small, switches={"Enable RVT Blend?": False, "Enable Toplayer Blend?": False})


def fx():
    path = "/Game/DojoKit/FX/Materials/M_DKF_Petal"
    m = get_or_create(path, unreal.Material, unreal.MaterialFactoryNew())
    reset(m, shading=FOLIAGE_SM(), blend=unreal.BlendMode.BLEND_MASKED,
          two_sided=True)
    g = G(m)
    uv0 = g.uv(0)
    bc = g.t2d("BC", "C", tex("/Game/DojoKit/FX/Textures/T_DKF_Petal_BC"), uv0)
    orm = g.t2d("ORM", "M", tex("/Game/DojoKit/FX/Textures/T_DKF_Petal_ORM"), uv0)
    sss = g.t2d("SSS", "LG", tex("/Game/DojoKit/FX/Textures/T_DKF_Petal_SSS"), uv0)
    # fix round (delta 9): a Tint (default 1 = the texture as before); MI_DKF_Petal pinks the pale T_DKF_Petal_BC
    # (median sRGB 236, 211, 218) toward the reference's petals (~230, 190, 200): (0.96, 0.72, 0.82) linear
    bcol = g.mul((bc, "RGB"), g.vector("Tint", (1.0, 1.0, 1.0)))
    g.out(bcol, MP.MP_BASE_COLOR)
    g.out((bc, "A"), MP.MP_OPACITY_MASK)
    g.out((orm, "G"), MP.MP_ROUGHNESS)
    g.out(g.mul(g.mul(bcol, (sss, "")), g.scalar("SSSStrength", 0.8)), MP.MP_SUBSURFACE_COLOR)
    for k in ("used_with_niagara_mesh_particles", "used_with_instanced_static_meshes"):
        try:
            m.set_editor_property(k, True)
        except Exception:  # noqa: BLE001
            pass
    finish(m, path)
    pet = make_mi("/Game/DojoKit/FX/Materials/MI_DKF_Petal", m, vectors={"Tint": (0.96, 0.72, 0.82)})
    old = make_mi("/Game/DojoKit/FX/Materials/MI_DKF_PetalOld", m,
                  textures={"BC": "/Game/DojoKit/FX/Textures/T_DKF_PetalOld_BC",
                            "ORM": "/Game/DojoKit/FX/Textures/T_DKF_PetalOld_ORM",
                            "SSS": "/Game/DojoKit/FX/Textures/T_DKF_PetalOld_SSS"})
    for a in EAL.list_assets("/Game/DojoKit/FX/Meshes", recursive=False):
        p = a.split(".")[0]
        assign(p, lambda s: old if "Old" in s else pet)


def main():
    t0 = time.time()
    for name, fn in (("export_pngs", export_pngs), ("probes", probes), ("stone", stone), ("pines", pines),
                     ("landscape", landscape), ("water", water), ("rocks", rocks), ("firs", firs), ("foam", foam), ("fir_voxelize", fir_voxelize), ("fx", fx)):
        # fix round: DJ_LS_STEPS (comma list) runs only the named steps (the others' assets stay as they are)
        only = [x for x in os.environ.get("DJ_LS_STEPS", "").split(",") if x]
        if only and name not in only:
            continue
        step(name, fn)
    REP["steps_only"] = os.environ.get("DJ_LS_STEPS", "")
    REP["unmatched_slots"] = {k: v["unmatched"] for k, v in REP["meshes"].items() if v.get("unmatched")}
    REP["passed"] = not REP["errors"] and not REP["unmatched_slots"]
    REP["sec"] = round(time.time() - t0, 1)
    (Path(os.environ["DJ_LS_OUT"]) if os.environ.get("DJ_LS_OUT") else W / "json/ls_materials.json").write_text(json.dumps(REP, indent=1, default=str), encoding="utf-8")
    unreal.log(f"DJ_STEP_DONE ls_materials passed={REP['passed']} errors={REP['errors']} "
               f"masters={len(REP['masters'])} instances={len(REP['instances'])} meshes={len(REP['meshes'])} "
               f"unmatched={len(REP['unmatched_slots'])}")


main()
