"""ArmoryLab step 2 (pythonscript commandlet, -nullrhi): the ArmoryKit materials, built here and ONLY here.

The pack material system (Scripts/unreal/materials, material_spec.json) is not touched and not referenced: ArmoryLab is its
own project, and the kit materials live in /Game/ArmoryKit/Materials.

Masters (rebuilt from scratch on every run, so the graph always equals this file):
    M_AK_Textured_Master  BC x Tint, ORM (R AO, G roughness, B metallic), N (DirectX), UV0 x UV Scale
    M_AK_TexturedTwoSided_Master  the same, two-sided (hero round: Blender two_sided cloth without alpha)
    M_AK_TexturedMasked_Master / M_AK_Foliage_Master  masked two-sided cards (alpha; translucent leaves)
    M_AK_EmissiveTex_Master / M_AK_EmissiveTexMasked_Master  emissive pictures (emit_image; unlit = Base Colour Scale 0)
    M_AK_Flat_Master      Base Colour, Roughness, Metallic, Clear Coat, Clear Coat Roughness (clear-coat shading model,
                          material attributes: the lacquer)
    M_AK_FlatNoCoat_Master  Base Colour, Roughness, Metallic, Specular, default lit (brass, felt, linen, back board)
    M_AK_Emissive_Master  Base Colour, Emissive Colour x Emissive Intensity (scene radiance units), Roughness
    M_AK_Glass_Master     translucent, surface forward shading: Base Colour, Opacity (face-on) -> Edge Opacity (Fresnel),
                          Roughness, Specular
Hero round (2026-09-28): generic over layout.json "materials" (every M_AK_H* hero material included); the per-material
spec (master, scalars, vectors, maps: tint on texture sets, glass refl, emit_image / unlit / alpha / two_sided, coat and
roughness) is ak_common.material_spec, which ak_verify re-checks against layout.json.
Instances: one MaterialInstanceConstant per Blender material name (build_armory_kit.py MATERIALS), named exactly like the
Blender material (M_AK_Timber ...), with the Blender look values; then every kit mesh gets, per slot, the instance whose
name equals the slot name. Emissive values = Blender emission strength x K (ak_common: lux per Blender W/m2).
Result: WorkFiles/armory/build/unreal/materials.json
"""
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unreal  # noqa: E402
import ak_common as C  # noqa: E402

EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
MP = unreal.MaterialProperty
K = C.K_LUX

# The Blender material table (build_armory_kit.py MATERIALS, hero modules included) travels in layout.json "materials";
# ak_common.blender_materials applies the Unreal-only UE_OVERRIDES and ak_common.material_spec maps each one to a master
# and its parameters (hero round: moved to ak_common so ak_verify checks the instances against layout.json itself).
BLENDER = C.blender_materials()
GLASS = C.GLASS   # the master's defaults (per-material refl scales Specular / Edge Opacity on the instance)
TEX_OF_MASTER = {}   # master -> the first layout.json material's maps (the master's default textures, generic)
for _n, (_t, _p) in BLENDER.items():
    _m, _s, _v, _tx, _no = C.material_spec(_t, _p)
    for _k, _stem in _tx.items():
        TEX_OF_MASTER.setdefault(_m, {}).setdefault(_k, _stem)


def lc(v):
    v = list(v) + [1.0] * (4 - len(v))
    return unreal.LinearColor(*[float(x) for x in v[:4]])


def get_or_create(path, cls, factory):
    if EAL.does_asset_exist(path):
        a = unreal.load_asset(path)
        if not isinstance(a, cls):
            raise TypeError(f"{path} exists as {type(a).__name__}, not {cls.__name__}: refusing to touch it")
        return a, False
    folder, name = path.rsplit("/", 1)
    a = AT.create_asset(name, folder, cls, factory)
    if a is None:
        raise RuntimeError(f"could not create {path}")
    return a, True


class G:
    """Tiny graph helper: node creation with a column layout."""

    def __init__(self, mat):
        self.m, self.n = mat, 0

    def node(self, cls, **props):
        self.n += 1
        e = MEL.create_material_expression(self.m, cls, -300 - 250 * (self.n // 8), 150 * (self.n % 8))
        for k, v in props.items():
            e.set_editor_property(k, v)
        return e

    def scalar(self, name, v, group="Surface"):
        return self.node(unreal.MaterialExpressionScalarParameter, parameter_name=name, default_value=float(v), group=group)

    def vector(self, name, v, group="Surface"):
        return self.node(unreal.MaterialExpressionVectorParameter, parameter_name=name, default_value=lc(v), group=group)

    def link(self, a, a_out, b, b_in):
        if not MEL.connect_material_expressions(a, a_out, b, b_in):
            raise RuntimeError(f"connect {a.get_name()}.{a_out!r} -> {b.get_name()}.{b_in!r} failed")

    def out(self, a, a_out, prop):
        if not MEL.connect_material_property(a, a_out, prop):
            raise RuntimeError(f"connect {a.get_name()}.{a_out!r} -> {prop} failed")

    def mul(self, a, a_out, b, b_out):
        m = self.node(unreal.MaterialExpressionMultiply)
        self.link(a, a_out, m, "A")
        self.link(b, b_out, m, "B")
        return m


def reset(mat, blend=unreal.BlendMode.BLEND_OPAQUE, shading=unreal.MaterialShadingModel.MSM_DEFAULT_LIT):
    MEL.delete_all_material_expressions(mat)
    mat.set_editor_property("blend_mode", blend)
    mat.set_editor_property("shading_model", shading)
    mat.set_editor_property("two_sided", False)
    mat.set_editor_property("use_material_attributes", False)


def default_tex(master, pname):
    """Hero round: a master's default texture is the first layout.json material's map on that master (the old fixed
    T_AK_Timber / T_AK_Plum / T_AKX_Hills defaults went out of the kit with the hero sets). None if no material uses it."""
    stem = TEX_OF_MASTER.get(master, {}).get(pname)
    return unreal.load_asset(f"{C.TEX_DEST}/{stem}") if stem else None


def build_textured(mat, two_sided=False, master="M_AK_Textured_Master"):
    reset(mat)
    if two_sided:   # hero round: opaque two-sided cloth (M_AK_HBannerSatin: Blender two_sided without alpha)
        mat.set_editor_property("two_sided", True)
    g = G(mat)
    tc = g.node(unreal.MaterialExpressionTextureCoordinate, coordinate_index=0)
    uvs = g.mul(tc, "", g.scalar("UV Scale", 1.0, "UV"), "")
    tex = {}
    for pname, st in (("Base Colour Map", unreal.MaterialSamplerType.SAMPLERTYPE_COLOR),
                      ("ORM Map", unreal.MaterialSamplerType.SAMPLERTYPE_MASKS),
                      ("Normal Map", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)):
        t = g.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name=pname,
                   texture=default_tex(master, pname), sampler_type=st, group="Textures")
        g.link(uvs, "", t, "UVs")
        tex[pname] = t
    bc = g.mul(tex["Base Colour Map"], "RGB", g.vector("Tint", (1, 1, 1)), "")
    g.out(bc, "", MP.MP_BASE_COLOR)
    g.out(tex["ORM Map"], "R", MP.MP_AMBIENT_OCCLUSION)
    g.out(tex["ORM Map"], "G", MP.MP_ROUGHNESS)
    g.out(tex["ORM Map"], "B", MP.MP_METALLIC)
    g.out(tex["Normal Map"], "RGB", MP.MP_NORMAL)


def build_flat(mat):
    """Clear coat has no public MaterialProperty (MP_CustomData0/1 are hidden from Python), so this master uses material
    attributes: MakeMaterialAttributes carries ClearCoat / ClearCoatRoughness pins."""
    reset(mat, shading=unreal.MaterialShadingModel.MSM_CLEAR_COAT)
    mat.set_editor_property("use_material_attributes", True)
    g = G(mat)
    mma = g.node(unreal.MaterialExpressionMakeMaterialAttributes)
    g.link(g.vector("Base Colour", (0.5, 0.5, 0.5)), "", mma, "BaseColor")
    g.link(g.scalar("Roughness", 0.5), "", mma, "Roughness")
    g.link(g.scalar("Metallic", 0.0), "", mma, "Metallic")
    g.link(g.scalar("Specular", 0.5), "", mma, "Specular")
    g.link(g.scalar("Clear Coat", 0.0, "Coat"), "", mma, "ClearCoat")
    g.link(g.scalar("Clear Coat Roughness", 0.05, "Coat"), "", mma, "ClearCoatRoughness")
    g.out(mma, "", MP.MP_MATERIAL_ATTRIBUTES)


def build_flat_nocoat(mat):
    """Default-lit flat surface for the flat materials without a clear coat (Blender coat 0)."""
    reset(mat)
    g = G(mat)
    g.out(g.vector("Base Colour", (0.5, 0.5, 0.5)), "", MP.MP_BASE_COLOR)
    g.out(g.scalar("Roughness", 0.5), "", MP.MP_ROUGHNESS)
    g.out(g.scalar("Metallic", 0.0), "", MP.MP_METALLIC)
    g.out(g.scalar("Specular", 0.5), "", MP.MP_SPECULAR)


def build_emissive(mat):
    reset(mat)
    g = G(mat)
    g.out(g.vector("Base Colour", (0.5, 0.5, 0.5)), "", MP.MP_BASE_COLOR)
    g.out(g.scalar("Roughness", 0.8), "", MP.MP_ROUGHNESS)
    em = g.mul(g.vector("Emissive Colour", (1, 1, 1), "Emission"), "",
               g.scalar("Emissive Intensity", 1.0, "Emission"), "")
    g.out(em, "", MP.MP_EMISSIVE_COLOR)


def build_glass(mat):
    reset(mat, blend=unreal.BlendMode.BLEND_TRANSLUCENT)
    # TLM_Surface = "Surface ForwardShading" (specular from every light, the right mode for glass)
    mat.set_editor_property("translucency_lighting_mode", unreal.TranslucencyLightingMode.TLM_SURFACE)
    g = G(mat)
    g.out(g.vector("Base Colour", GLASS["Base Colour"]), "", MP.MP_BASE_COLOR)
    g.out(g.scalar("Roughness", GLASS["Roughness"]), "", MP.MP_ROUGHNESS)
    g.out(g.scalar("Specular", GLASS["Specular"]), "", MP.MP_SPECULAR)
    g.out(g.scalar("Metallic", 0.0), "", MP.MP_METALLIC)
    fr = g.node(unreal.MaterialExpressionFresnel, exponent=5.0, base_reflect_fraction=0.0)
    lerp = g.node(unreal.MaterialExpressionLinearInterpolate)
    g.link(g.scalar("Opacity", GLASS["Opacity"]), "", lerp, "A")
    g.link(g.scalar("Edge Opacity", GLASS["Edge Opacity"]), "", lerp, "B")
    g.link(fr, "", lerp, "Alpha")
    g.out(lerp, "", MP.MP_OPACITY)


def build_emissive_tex(mat, masked=False):
    """look2: an emissive picture: the BC map drives base colour (x Base Colour Scale: 0 = unlit, exterior stage) and
    emission. Exterior stage: the masked, two-sided variant carries the alpha-masked tree-line cards."""
    if masked:
        reset(mat, blend=unreal.BlendMode.BLEND_MASKED)
        mat.set_editor_property("two_sided", True)
    else:
        reset(mat)
    g = G(mat)
    t = g.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="Base Colour Map",
               texture=default_tex("M_AK_EmissiveTexMasked_Master" if masked else "M_AK_EmissiveTex_Master",
                                   "Base Colour Map"),
               sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, group="Textures")
    g.out(g.mul(t, "RGB", g.scalar("Base Colour Scale", 1.0), ""), "", MP.MP_BASE_COLOR)
    g.out(g.scalar("Roughness", 1.0), "", MP.MP_ROUGHNESS)
    g.out(g.mul(t, "RGB", g.scalar("Emissive Intensity", 1.0, "Emission"), ""), "", MP.MP_EMISSIVE_COLOR)
    if masked:
        g.out(t, "A", MP.MP_OPACITY_MASK)


def build_textured_masked(mat, foliage=False):
    """Exterior stage: alpha-masked, two-sided textured cards (plum sprays, banner, pine pads, maple leaves). The opacity
    mask is the BC alpha, faded out where a card is seen edge-on (Edge Fade 1: |N . V| x 3, as the Blender material's
    Layer Weight fade), so thin cards do not streak."""
    reset(mat, blend=unreal.BlendMode.BLEND_MASKED,
          shading=unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE if foliage else unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    mat.set_editor_property("two_sided", True)
    g = G(mat)
    tc = g.node(unreal.MaterialExpressionTextureCoordinate, coordinate_index=0)
    uvs = g.mul(tc, "", g.scalar("UV Scale", 1.0, "UV"), "")
    tex = {}
    master = "M_AK_Foliage_Master" if foliage else "M_AK_TexturedMasked_Master"
    for pname, st in (("Base Colour Map", unreal.MaterialSamplerType.SAMPLERTYPE_COLOR),
                      ("ORM Map", unreal.MaterialSamplerType.SAMPLERTYPE_MASKS),
                      ("Normal Map", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)):
        t = g.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name=pname,
                   texture=default_tex(master, pname) or default_tex("M_AK_Textured_Master", pname),
                   sampler_type=st, group="Textures")
        g.link(uvs, "", t, "UVs")
        tex[pname] = t
    g.out(g.mul(tex["Base Colour Map"], "RGB", g.vector("Tint", (1, 1, 1)), ""), "", MP.MP_BASE_COLOR)
    g.out(tex["ORM Map"], "R", MP.MP_AMBIENT_OCCLUSION)
    g.out(tex["ORM Map"], "G", MP.MP_ROUGHNESS)
    g.out(tex["ORM Map"], "B", MP.MP_METALLIC)
    g.out(tex["Normal Map"], "RGB", MP.MP_NORMAL)
    dp = g.node(unreal.MaterialExpressionDotProduct)
    g.link(g.node(unreal.MaterialExpressionVertexNormalWS), "", dp, "A")
    g.link(g.node(unreal.MaterialExpressionCameraVectorWS), "", dp, "B")
    ab = g.node(unreal.MaterialExpressionAbs)
    g.link(dp, "", ab, "")
    sat = g.node(unreal.MaterialExpressionSaturate)
    g.link(g.mul(ab, "", g.scalar("Edge Fade Gain", 3.0, "Mask"), ""), "", sat, "")
    lerp = g.node(unreal.MaterialExpressionLinearInterpolate)
    g.link(g.scalar("Edge Fade Off", 1.0, "Mask"), "", lerp, "A")
    g.link(sat, "", lerp, "B")
    g.link(g.scalar("Edge Fade", 0.0, "Mask"), "", lerp, "Alpha")
    g.out(g.mul(tex["Base Colour Map"], "A", lerp, ""), "", MP.MP_OPACITY_MASK)
    if foliage:
        g.out(g.mul(tex["Base Colour Map"], "RGB", g.scalar("Translucency", 0.2, "Foliage"), ""), "",
              MP.MP_SUBSURFACE_COLOR)


def build_foliage(mat):
    """Unreal rebuild: the leaf cards with Blender "translucent" (pine pads, maples): the masked two-sided graph on the
    Two Sided Foliage shading model, subsurface colour = BC x Translucency (Blender mixes a translucent BSDF of the BC
    colour at that weight), so sunlit leaves glow when seen against the light."""
    build_textured_masked(mat, foliage=True)


MASTERS = {"M_AK_Textured_Master": build_textured,
           "M_AK_TexturedTwoSided_Master": lambda m: build_textured(m, True, "M_AK_TexturedTwoSided_Master"),
           "M_AK_Foliage_Master": build_foliage, "M_AK_Flat_Master": build_flat,
           "M_AK_EmissiveTex_Master": build_emissive_tex,
           "M_AK_EmissiveTexMasked_Master": lambda m: build_emissive_tex(m, masked=True),
           "M_AK_TexturedMasked_Master": build_textured_masked,
           "M_AK_FlatNoCoat_Master": build_flat_nocoat,
           "M_AK_Emissive_Master": build_emissive, "M_AK_Glass_Master": build_glass}


def instance_spec(name):
    """-> (master, scalars, vectors, textures, notes) for a Blender material name (ak_common.material_spec)."""
    tex, p = BLENDER[name]
    return C.material_spec(tex, p)


def main():
    t0 = time.time()
    rep = {"engine": unreal.SystemLibrary.get_engine_version(), "K_lux_per_blender_unit": K, "masters": {},
           "instances": {}, "meshes": {}}
    masters = {}
    for name, fn in MASTERS.items():
        path = f"{C.MAT_DEST}/{name}"
        e = {}
        try:
            mat, created = get_or_create(path, unreal.Material, unreal.MaterialFactoryNew())
            fn(mat)
            MEL.layout_material_expressions(mat)
            MEL.recompile_material(mat)
            e["created"] = created
            e["expressions"] = int(MEL.get_num_material_expressions(mat))
            e["saved"] = bool(EAL.save_loaded_asset(mat, False))
            masters[name] = mat
        except Exception:  # noqa: BLE001
            e["error"] = traceback.format_exc()[-1500:]
        rep["masters"][name] = e
    mis = {}
    for name in BLENDER:
        path = f"{C.MAT_DEST}/{name}"
        e = {}
        try:
            master, scal, vec, tex, notes = instance_spec(name)
            mi, created = get_or_create(path, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
            MEL.clear_all_material_instance_parameters(mi)
            MEL.set_material_instance_parent(mi, masters[master])
            for k, v in scal.items():
                MEL.set_material_instance_scalar_parameter_value(mi, k, float(v))
            for k, v in vec.items():
                MEL.set_material_instance_vector_parameter_value(mi, k, lc(v))
            for k, v in tex.items():
                MEL.set_material_instance_texture_parameter_value(mi, k, unreal.load_asset(f"{C.TEX_DEST}/{v}"))
            MEL.update_material_instance(mi)
            e = {"created": created, "master": master, "scalars": scal, "vectors": {k: list(v) for k, v in vec.items()},
                 "textures": tex, "notes": notes}
            missing_tex = [v for v in tex.values() if not EAL.does_asset_exist(f"{C.TEX_DEST}/{v}")]
            if missing_tex:
                raise RuntimeError(f"textures not imported: {missing_tex}")
            e["readback"] = {k: round(float(MEL.get_material_instance_scalar_parameter_value(mi, k)), 5) for k in scal}
            e["saved"] = bool(EAL.save_loaded_asset(mi, False))
            mis[name] = mi
        except Exception:  # noqa: BLE001
            e["error"] = traceback.format_exc()[-1500:]
        rep["instances"][name] = e
    used = set()
    for path in sorted(EAL.list_assets(C.MESH_DEST, recursive=False, include_folder=False)):
        mesh = unreal.load_asset(path.split(".")[0])
        if not isinstance(mesh, unreal.StaticMesh):
            continue
        e = {"slots": {}, "unmatched": []}
        try:
            for i, s in enumerate(mesh.get_editor_property("static_materials")):
                slot = str(s.get_editor_property("material_slot_name"))
                mi = mis.get(slot)
                if mi is None:
                    e["unmatched"].append(slot)
                    continue
                mesh.set_material(i, mi)
                used.add(slot)
                e["slots"][slot] = mi.get_path_name()
            e["saved"] = bool(EAL.save_loaded_asset(mesh, False))
        except Exception:  # noqa: BLE001
            e["error"] = traceback.format_exc()[-1500:]
        rep["meshes"][mesh.get_name()] = e
    rep["instances_unused_by_any_slot"] = sorted(set(BLENDER) - used)
    # Unreal rebuild: delete our own stale instances (materials the Blender table dropped: M_AK_Felt, M_AK_ShojiLit ...)
    # after every slot above was re-assigned, so nothing in the kit still points at them. Masters are kept.
    rep["stale_instances_deleted"] = []
    for path in sorted(EAL.list_assets(C.MAT_DEST, recursive=False, include_folder=False)):
        base = path.split(".")[0]
        name = base.rsplit("/", 1)[-1]
        if name in BLENDER or name in MASTERS:
            continue
        if isinstance(unreal.load_asset(base), unreal.MaterialInstanceConstant) and EAL.delete_asset(base):
            rep["stale_instances_deleted"].append(base)
    errs = [k for sec in ("masters", "instances", "meshes") for k, v in rep[sec].items() if v.get("error")]
    unmatched = {k: v["unmatched"] for k, v in rep["meshes"].items() if v.get("unmatched")}
    rep["errors"], rep["unmatched_slots"] = errs, unmatched
    rep["passed"] = (not errs and not unmatched and len(rep["meshes"]) == C.n_meshes() and len(mis) == len(BLENDER)
                     and all(v.get("saved") for v in rep["meshes"].values()))
    rep["sec"] = round(time.time() - t0, 1)
    C.write_json(C.OUT / "materials.json", rep)
    unreal.log(f"AK_STEP_DONE materials passed={rep['passed']} masters={len(masters)} instances={len(mis)} "
               f"meshes={len(rep['meshes'])}")


main()
