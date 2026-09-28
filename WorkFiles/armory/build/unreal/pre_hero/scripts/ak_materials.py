"""ArmoryLab step 2 (pythonscript commandlet, -nullrhi): the ArmoryKit materials, built here and ONLY here.

The pack material system (Scripts/unreal/materials, material_spec.json) is not touched and not referenced: ArmoryLab is its
own project, and the kit materials live in /Game/ArmoryKit/Materials.

Masters (rebuilt from scratch on every run, so the graph always equals this file):
    M_AK_Textured_Master  BC x Tint, ORM (R AO, G roughness, B metallic), N (DirectX), UV0 x UV Scale
    M_AK_Flat_Master      Base Colour, Roughness, Metallic, Clear Coat, Clear Coat Roughness (clear-coat shading model,
                          material attributes: the lacquer)
    M_AK_FlatNoCoat_Master  Base Colour, Roughness, Metallic, Specular, default lit (brass, felt, linen, back board)
    M_AK_Emissive_Master  Base Colour, Emissive Colour x Emissive Intensity (scene radiance units), Roughness
    M_AK_Glass_Master     translucent, surface forward shading: Base Colour, Opacity (face-on) -> Edge Opacity (Fresnel),
                          Roughness, Specular
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

# The Blender material table (build_armory_kit.py MATERIALS) travels in layout.json "materials" (look2). Unreal rebuild:
# the hand-copied fallback table here had gone stale (fix1 values, M_AK_Felt, no f1 / f2 materials), so it is gone: a
# layout.json without "materials" is an error, not a silent fallback.
BLENDER = {k: (v["texture"], v["params"]) for k, v in C.load_layout()["materials"].items()}
# Unreal-only overrides on top of the Blender values (tuned against the Blender golden renders; BUILD_NOTES, Unreal
# rebuild). look2's M_AK_Felt entry is gone with the felt (f1: black lacquer decks).
UE_OVERRIDES = {   # look3: Unreal-only, measured on C1 against the Blender golden render
    "M_AK_Plank": {"tint": 0.62},      # floor read light oak (L 0.43-0.53 vs Blender 0.29-0.44)
    "M_AK_Painting": {"tint": 0.70},   # painting 0.65 vs 0.54
}
for _k, _o in UE_OVERRIDES.items():
    if _k in BLENDER:
        BLENDER[_k] = (BLENDER[_k][0], dict(BLENDER[_k][1], **_o))
# f2: museum anti-reflective glass. Blender: fully transparent plus a mirror at 0.02 x Fresnel (IOR 1.5): 0.1 % face-on,
# up to 2 % at grazing. Unreal thin translucent pane: specular 0.1 (F0 0.008) under a small opacity rising at grazing.
# look2 had Opacity 0.05 / Edge 0.16 / Specular 0.35 (Blender then 0.3 x Fresnel).
GLASS = {"Base Colour": (0.012, 0.013, 0.013), "Opacity": 0.02, "Edge Opacity": 0.06, "Roughness": 0.02, "Specular": 0.1}


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


def build_textured(mat):
    reset(mat)
    g = G(mat)
    tc = g.node(unreal.MaterialExpressionTextureCoordinate, coordinate_index=0)
    uvs = g.mul(tc, "", g.scalar("UV Scale", 1.0, "UV"), "")
    tex = {}
    for pname, stem, st in (("Base Colour Map", "T_AK_Timber_BC", unreal.MaterialSamplerType.SAMPLERTYPE_COLOR),
                            ("ORM Map", "T_AK_Timber_ORM", unreal.MaterialSamplerType.SAMPLERTYPE_MASKS),
                            ("Normal Map", "T_AK_Timber_N", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)):
        t = g.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name=pname,
                   texture=unreal.load_asset(f"{C.TEX_DEST}/{stem}"), sampler_type=st, group="Textures")
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
               texture=unreal.load_asset(f"{C.TEX_DEST}/{'T_AKX_TreeLine_BC' if masked else 'T_AKX_Hills_BC'}"),
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
    for pname, stem, st in (("Base Colour Map", "T_AK_Plum_BC", unreal.MaterialSamplerType.SAMPLERTYPE_COLOR),
                            ("ORM Map", "T_AK_Plum_ORM", unreal.MaterialSamplerType.SAMPLERTYPE_MASKS),
                            ("Normal Map", "T_AK_Plum_N", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)):
        t = g.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name=pname,
                   texture=unreal.load_asset(f"{C.TEX_DEST}/{stem}"), sampler_type=st, group="Textures")
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


MASTERS = {"M_AK_Textured_Master": build_textured, "M_AK_Foliage_Master": build_foliage, "M_AK_Flat_Master": build_flat,
           "M_AK_EmissiveTex_Master": build_emissive_tex,
           "M_AK_EmissiveTexMasked_Master": lambda m: build_emissive_tex(m, masked=True),
           "M_AK_TexturedMasked_Master": build_textured_masked,
           "M_AK_FlatNoCoat_Master": build_flat_nocoat,
           "M_AK_Emissive_Master": build_emissive, "M_AK_Glass_Master": build_glass}


def instance_spec(name):
    """-> (master, scalars, vectors, textures) for a Blender material name."""
    tex, p = BLENDER[name]
    if p.get("emit_image"):
        master = "M_AK_EmissiveTexMasked_Master" if p.get("alpha") else "M_AK_EmissiveTex_Master"
        return master, {"Emissive Intensity": p["emit"] * K, "Base Colour Scale": 0.0 if p.get("unlit") else 1.0}, {},             {"Base Colour Map": f"{C.tex_stem(tex)}_BC"}
    if tex:
        st = C.tex_stem(tex)
        t = {"Base Colour Map": f"{st}_BC", "ORM Map": f"{st}_ORM", "Normal Map": f"{st}_N"}
        s = p.get("tint", 1.0)
        if p.get("translucent"):   # Unreal rebuild: leaf cards on the two-sided foliage master
            return "M_AK_Foliage_Master", {"UV Scale": 1.0, "Edge Fade": 1.0 if p.get("edge_fade") else 0.0,
                                           "Translucency": float(p["translucent"])}, {"Tint": (s, s, s)}, t
        if p.get("alpha") or p.get("two_sided"):   # exterior stage: masked two-sided cards (M_AK_Plum, M_AK_Banner too)
            return "M_AK_TexturedMasked_Master", {"UV Scale": 1.0, "Edge Fade": 1.0 if p.get("edge_fade") else 0.0},                 {"Tint": (s, s, s)}, t
        return "M_AK_Textured_Master", {"UV Scale": 1.0}, {"Tint": (s, s, s)}, t
    if p.get("glass"):
        return "M_AK_Glass_Master", {k: v for k, v in GLASS.items() if not isinstance(v, tuple)}, \
            {"Base Colour": GLASS["Base Colour"]}, {}
    if "emit" in p:
        return "M_AK_Emissive_Master", {"Roughness": 0.8, "Emissive Intensity": p["emit"] * K}, \
            {"Base Colour": C.hexcol(p["color"]), "Emissive Colour": C.hexcol(p.get("emit_color", p["color"]))}, {}
    sc = {"Roughness": p.get("rough", 0.5), "Metallic": p.get("metal", 0.0), "Specular": 0.5}
    if p.get("coat", 0.0) <= 0.0:   # no coat in Blender: plain default-lit master (cheaper, no coat layer at all)
        return "M_AK_FlatNoCoat_Master", sc, {"Base Colour": C.hexcol(p["color"])}, {}
    sc.update({"Clear Coat": p["coat"], "Clear Coat Roughness": 0.05})
    return "M_AK_Flat_Master", sc, {"Base Colour": C.hexcol(p["color"])}, {}


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
            master, scal, vec, tex = instance_spec(name)
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
                 "textures": tex}
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
