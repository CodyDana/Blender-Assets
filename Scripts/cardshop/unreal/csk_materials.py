"""CardShopKit G1 step: materials (pythonscript commandlet, -nullrhi). Test masters + instances for gate G1 test 1.

These are G1 TEST materials, not the kit's final masters (P6, spec 5.1). They prove the two buyer-art paths on the
exported UVs (spec 4.1):

M_CSK_G1_Print (opaque, Used with Instanced Static Meshes). UV0 tiles choose the face (Unreal's V is flipped against
Blender's, so Blender's label tile (0,1) arrives as V in [-1, 0]):
    tile (0,0) front, tile (1,0) back, tile (0,-1) label, U < 0 non-print (a flat colour)
    each face samples its own texture parameter (Front / Back / Label Texture) at
        uv = lerp(frac(UV), CellOffset + frac(UV) * CellSize, Use Atlas)
    so Use Atlas = 0 is the plain-texture path (the whole image on the face) and Use Atlas = 1 reads the csk_pack_cards
    cell rects (top-left origin, as the JSON index gives them).
M_CSK_G1_Glass (translucent, Surface ForwardShading, the armory glass graph) for glass, acrylic and PVC.
M_CSK_G1_Surface (opaque flat colour + emissive) for frame, base, LED, board.

Each mesh slot gets a default instance by slot name, so a mesh dropped in a level shows the plain path; the G1 map
overrides per actor for the atlas rows.
"""
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unreal  # noqa: E402
import csk_common as C  # noqa: E402

EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
MP = unreal.MaterialProperty


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
    def __init__(self, mat):
        self.m, self.n = mat, 0

    def node(self, cls, **props):
        self.n += 1
        e = MEL.create_material_expression(self.m, cls, -400 - 260 * (self.n // 10), 140 * (self.n % 10))
        for k, v in props.items():
            e.set_editor_property(k, v)
        return e

    def scalar(self, name, v, group="Print"):
        return self.node(unreal.MaterialExpressionScalarParameter, parameter_name=name, default_value=float(v),
                         group=group)

    def vector(self, name, v, group="Print"):
        return self.node(unreal.MaterialExpressionVectorParameter, parameter_name=name, default_value=lc(v),
                         group=group)

    def link(self, a, a_out, b, b_in):
        if not MEL.connect_material_expressions(a, a_out, b, b_in):
            raise RuntimeError(f"connect {a.get_name()}.{a_out!r} -> {b.get_name()}.{b_in!r} failed")

    def out(self, a, a_out, prop):
        if not MEL.connect_material_property(a, a_out, prop):
            raise RuntimeError(f"connect {a.get_name()}.{a_out!r} -> {prop} failed")

    def op(self, cls, a, a_out="", b=None, b_out=""):
        e = self.node(cls)
        self.link(a, a_out, e, "A" if b is not None else "")
        if b is not None:
            self.link(b, b_out, e, "B")
        return e

    def unary(self, cls, a, a_out=""):
        e = self.node(cls)
        self.link(a, a_out, e, "")
        return e

    def mask(self, a, a_out="", r=True, g=False, b=False, alpha=False):
        e = self.node(unreal.MaterialExpressionComponentMask, r=r, g=g, b=b, a=alpha)
        self.link(a, a_out, e, "")
        return e

    def lerp(self, a, b, alpha, a_out="", b_out="", alpha_out=""):
        e = self.node(unreal.MaterialExpressionLinearInterpolate)
        self.link(a, a_out, e, "A")
        self.link(b, b_out, e, "B")
        self.link(alpha, alpha_out, e, "Alpha")
        return e

    def const(self, v):
        return self.node(unreal.MaterialExpressionConstant, r=float(v))


def reset(mat, blend=unreal.BlendMode.BLEND_OPAQUE):
    MEL.delete_all_material_expressions(mat)
    mat.set_editor_property("blend_mode", blend)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    mat.set_editor_property("two_sided", False)
    mat.set_editor_property("use_material_attributes", False)
    for flag in ("used_with_instanced_static_meshes",):
        try:
            mat.set_editor_property(flag, True)
        except Exception:  # noqa: BLE001
            pass


def default_texture():
    t = unreal.load_asset(f"{C.TEX_DEST}/T_CSK_G1_CardFront_BC")
    return t if t is not None else unreal.load_asset("/Engine/EngineResources/DefaultTexture")


def build_print(mat):
    reset(mat)
    g = G(mat)
    tc = g.node(unreal.MaterialExpressionTextureCoordinate, coordinate_index=0)
    fl = g.unary(unreal.MaterialExpressionFloor, tc)
    fr = g.unary(unreal.MaterialExpressionFrac, tc)
    tx = g.mask(fl, r=True)
    ty = g.mask(fl, r=False, g=True)
    neg = g.const(-1.0)
    is_back = g.unary(unreal.MaterialExpressionSaturate, tx)
    is_np = g.unary(unreal.MaterialExpressionSaturate, g.op(unreal.MaterialExpressionMultiply, tx, "", neg, ""))
    is_label = g.unary(unreal.MaterialExpressionSaturate, g.op(unreal.MaterialExpressionMultiply, ty, "", neg, ""))
    use_atlas = g.scalar("Use Atlas", 0.0)
    samples = {}
    for face in ("Front", "Back", "Label"):
        off = g.mask(g.vector(f"{face} Cell Offset", (0, 0, 0)), r=True, g=True)
        size = g.mask(g.vector(f"{face} Cell Size", (1, 1, 0)), r=True, g=True)
        atl = g.op(unreal.MaterialExpressionAdd, off, "", g.op(unreal.MaterialExpressionMultiply, fr, "", size, ""), "")
        uv = g.lerp(fr, atl, use_atlas)
        t = g.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name=f"{face} Texture",
                   texture=default_texture(), sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_COLOR,
                   group="Print")      # a sampler parameter without a default texture does not compile
        g.link(uv, "", t, "UVs")
        samples[face] = t
    c = g.lerp(samples["Front"], samples["Back"], is_back, "RGB", "RGB")
    c = g.lerp(c, samples["Label"], is_label, "", "RGB")
    c = g.lerp(c, g.vector("Non Print Colour", (0.9, 0.9, 0.9)), is_np)
    g.out(c, "", MP.MP_BASE_COLOR)
    g.out(g.scalar("Roughness", 0.35, "Surface"), "", MP.MP_ROUGHNESS)
    g.out(g.scalar("Specular", 0.5, "Surface"), "", MP.MP_SPECULAR)
    g.out(g.const(0.0), "", MP.MP_METALLIC)


def build_glass(mat):
    reset(mat, blend=unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property("translucency_lighting_mode", unreal.TranslucencyLightingMode.TLM_SURFACE)
    g = G(mat)
    g.out(g.vector("Base Colour", (0.9, 1.0, 0.95), "Glass"), "", MP.MP_BASE_COLOR)
    g.out(g.scalar("Roughness", 0.02, "Glass"), "", MP.MP_ROUGHNESS)
    g.out(g.scalar("Specular", 0.5, "Glass"), "", MP.MP_SPECULAR)
    g.out(g.const(0.0), "", MP.MP_METALLIC)
    fres = g.node(unreal.MaterialExpressionFresnel, exponent=5.0, base_reflect_fraction=0.0)
    lerp = g.lerp(g.scalar("Opacity", 0.12, "Glass"), g.scalar("Edge Opacity", 0.5, "Glass"), fres)
    g.out(lerp, "", MP.MP_OPACITY)


def build_surface(mat):
    reset(mat)
    g = G(mat)
    g.out(g.vector("Base Colour", (0.5, 0.5, 0.5), "Surface"), "", MP.MP_BASE_COLOR)
    g.out(g.scalar("Roughness", 0.5, "Surface"), "", MP.MP_ROUGHNESS)
    g.out(g.scalar("Metallic", 0.0, "Surface"), "", MP.MP_METALLIC)
    em = g.op(unreal.MaterialExpressionMultiply, g.vector("Emissive Colour", (1, 1, 1), "Emission"), "",
              g.scalar("Emissive Intensity", 0.0, "Emission"), "")
    g.out(em, "", MP.MP_EMISSIVE_COLOR)


MASTERS = {"M_CSK_G1_Print": build_print, "M_CSK_G1_Glass": build_glass, "M_CSK_G1_Surface": build_surface}


def cell(index_json, i):
    """(offset, size) of cell ``i`` of a csk_pack_cards index, as vectors (top-left UV origin)."""
    u, v, du, dv = C.atlas_index(index_json)["cells"][i]["rect_uv"]
    return (u, v, 0.0), (du, dv, 0.0)


def instances():
    """name -> (master, scalars, vectors, textures). Cells follow g1_placeholder_art.py's file order:
    cards 0-5 fronts (Pyrecall 01-02, Lumenfold 01-02, Rimvault 01-02), 6 = the back; packs 2k front, 2k+1 back
    for k = Pyrecall, Lumenfold, Rimvault; labels 0 Clearmark, 1 Halcyon."""
    I = {}
    plain_face = {"Use Atlas": 0.0}
    I["MI_CSK_G1_Card_Plain"] = ("M_CSK_G1_Print", plain_face, {"Non Print Colour": (0.92, 0.92, 0.9)},
                                 {"Front Texture": "T_CSK_G1_CardFront_BC", "Back Texture": "T_CSK_G1_CardBack_BC",
                                  "Label Texture": "T_CSK_G1_CardFront_BC"})
    back_off, back_size = cell("T_CSK_G1_Cards_BC", 6)
    for i in range(6):
        off, size = cell("T_CSK_G1_Cards_BC", i)
        I[f"MI_CSK_G1_Card_Atlas_{i}"] = ("M_CSK_G1_Print", {"Use Atlas": 1.0},
                                          {"Front Cell Offset": off, "Front Cell Size": size,
                                           "Back Cell Offset": back_off, "Back Cell Size": back_size,
                                           "Non Print Colour": (0.92, 0.92, 0.9)},
                                          {"Front Texture": "T_CSK_G1_Cards_BC", "Back Texture": "T_CSK_G1_Cards_BC",
                                           "Label Texture": "T_CSK_G1_Cards_BC"})
    I["MI_CSK_G1_Pack_Plain"] = ("M_CSK_G1_Print", plain_face, {"Non Print Colour": (0.75, 0.75, 0.78)},
                                 {"Front Texture": "T_CSK_G1_PackFront_BC", "Back Texture": "T_CSK_G1_PackBack_BC",
                                  "Label Texture": "T_CSK_G1_PackFront_BC"})
    for k in range(3):
        fo, fs = cell("T_CSK_G1_Packs_BC", 2 * k)
        bo, bs = cell("T_CSK_G1_Packs_BC", 2 * k + 1)
        I[f"MI_CSK_G1_Pack_Atlas_{k}"] = ("M_CSK_G1_Print", {"Use Atlas": 1.0},
                                          {"Front Cell Offset": fo, "Front Cell Size": fs, "Back Cell Offset": bo,
                                           "Back Cell Size": bs, "Non Print Colour": (0.75, 0.75, 0.78)},
                                          {"Front Texture": "T_CSK_G1_Packs_BC", "Back Texture": "T_CSK_G1_Packs_BC",
                                           "Label Texture": "T_CSK_G1_Packs_BC"})
    I["MI_CSK_G1_SlabBody_Plain"] = ("M_CSK_G1_Print", plain_face, {"Non Print Colour": (0.93, 0.94, 0.96)},
                                     {"Front Texture": "T_CSK_G1_Label_BC", "Back Texture": "T_CSK_G1_Label_BC",
                                      "Label Texture": "T_CSK_G1_Label_BC"})
    for k in range(2):
        lo, ls = cell("T_CSK_G1_Labels_BC", k)
        I[f"MI_CSK_G1_SlabBody_Atlas_{k}"] = ("M_CSK_G1_Print", {"Use Atlas": 1.0},
                                              {"Label Cell Offset": lo, "Label Cell Size": ls,
                                               "Non Print Colour": (0.93, 0.94, 0.96)},
                                              {"Front Texture": "T_CSK_G1_Labels_BC", "Back Texture": "T_CSK_G1_Labels_BC",
                                               "Label Texture": "T_CSK_G1_Labels_BC"})
    I["MI_CSK_G1_SlabFilled_Plain"] = ("M_CSK_G1_Print", plain_face, {"Non Print Colour": (0.93, 0.94, 0.96)},
                                       {"Front Texture": "T_CSK_G1_CardFront_BC", "Back Texture": "T_CSK_G1_CardBack_BC",
                                        "Label Texture": "T_CSK_G1_Label_BC"})
    fo, fs = cell("T_CSK_G1_Cards_BC", 2)
    lo, ls = cell("T_CSK_G1_Labels_BC", 1)
    I["MI_CSK_G1_SlabFilled_Atlas"] = ("M_CSK_G1_Print", {"Use Atlas": 1.0},
                                       {"Front Cell Offset": fo, "Front Cell Size": fs, "Back Cell Offset": back_off,
                                        "Back Cell Size": back_size, "Label Cell Offset": lo, "Label Cell Size": ls,
                                        "Non Print Colour": (0.93, 0.94, 0.96)},
                                       {"Front Texture": "T_CSK_G1_Cards_BC", "Back Texture": "T_CSK_G1_Cards_BC",
                                        "Label Texture": "T_CSK_G1_Labels_BC"})
    I["MI_CSK_G1_BoxPrint_Plain"] = ("M_CSK_G1_Print", plain_face, {"Non Print Colour": (0.8, 0.78, 0.72)},
                                     {"Front Texture": "T_CSK_G1_BoxDieline_BC", "Back Texture": "T_CSK_G1_BoxDieline_BC",
                                      "Label Texture": "T_CSK_G1_BoxDieline_BC"})
    I["MI_CSK_G1_Glass"] = ("M_CSK_G1_Glass", {"Opacity": 0.1, "Edge Opacity": 0.45, "Roughness": 0.02},
                            {"Base Colour": (0.9, 1.0, 0.95)}, {})
    I["MI_CSK_G1_Acrylic"] = ("M_CSK_G1_Glass", {"Opacity": 0.08, "Edge Opacity": 0.35, "Roughness": 0.03},
                              {"Base Colour": (1, 1, 1)}, {})
    I["MI_CSK_G1_PVC"] = ("M_CSK_G1_Glass", {"Opacity": 0.12, "Edge Opacity": 0.4, "Roughness": 0.08},
                          {"Base Colour": (0.9, 0.95, 1.0)}, {})
    I["MI_CSK_G1_Frame"] = ("M_CSK_G1_Surface", {"Roughness": 0.3, "Metallic": 1.0}, {"Base Colour": (0.8, 0.8, 0.82)}, {})
    I["MI_CSK_G1_Base"] = ("M_CSK_G1_Surface", {"Roughness": 0.5}, {"Base Colour": (0.03, 0.03, 0.035)}, {})
    I["MI_CSK_G1_LED"] = ("M_CSK_G1_Surface", {"Emissive Intensity": 8.0}, {"Base Colour": (1, 1, 1),
                                                                           "Emissive Colour": (1, 0.95, 0.85)}, {})
    I["MI_CSK_G1_Board"] = ("M_CSK_G1_Surface", {"Roughness": 0.85}, {"Base Colour": (0.62, 0.5, 0.36)}, {})
    I["MI_CSK_G1_Oak"] = ("M_CSK_G1_Surface", {"Roughness": 0.55}, {"Base Colour": (0.36, 0.22, 0.1)}, {})
    I["MI_CSK_G1_Deck"] = ("M_CSK_G1_Surface", {"Roughness": 0.5}, {"Base Colour": (0.7, 0.62, 0.48)}, {})
    I["MI_CSK_G1_Film"] = ("M_CSK_G1_Glass", {"Opacity": 0.06, "Edge Opacity": 0.3, "Roughness": 0.1},
                           {"Base Colour": (1, 1, 1)}, {})
    # The 12 families' slots (WorkFiles/cardshop/families/*.md): test looks on the same three masters, one MI per
    # slot, named MI_CSK_G1_<Part>. Print slots take the plain path on the G1 test-pattern textures, so every print
    # face shows its orientation (TL red, TR green, BL blue, BR yellow) until the kit's own atlases exist.
    for part, (rgb, rough, metal) in SURFACE.items():
        I[f"MI_CSK_G1_{part}"] = ("M_CSK_G1_Surface", {"Roughness": rough, "Metallic": metal}, {"Base Colour": rgb}, {})
    for part, (rgb, emit, intensity) in EMISSIVE.items():
        rough = 0.7 if part == "LED_Panel" else 0.2           # a panel's diffuser is matte, not a mirror
        I[f"MI_CSK_G1_{part}"] = ("M_CSK_G1_Surface", {"Roughness": rough, "Emissive Intensity": intensity},
                                  {"Base Colour": rgb, "Emissive Colour": emit}, {})
    for part, (opacity, edge, rough, rgb) in CLEAR.items():
        I[f"MI_CSK_G1_{part}"] = ("M_CSK_G1_Glass", {"Opacity": opacity, "Edge Opacity": edge, "Roughness": rough},
                                  {"Base Colour": rgb}, {})
    for part, (front, back, label, np_rgb) in PRINT_PLAIN.items():
        I[f"MI_CSK_G1_{part}"] = ("M_CSK_G1_Print", plain_face, {"Non Print Colour": np_rgb},
                                  {"Front Texture": front, "Back Texture": back, "Label Texture": label})
    for line in ("Lumenfold", "Rimvault"):    # box colourways (per-actor overrides, e.g. the shop room)
        tex = f"T_CSK_G1_BoxDieline_{line}_BC"
        for part in ("BoxPrint_Plain", "BoxPrintL"):
            I[f"MI_CSK_G1_{part}_{line}"] = ("M_CSK_G1_Print", plain_face, {"Non Print Colour": (0.8, 0.78, 0.72)},
                                             {"Front Texture": tex, "Back Texture": tex, "Label Texture": tex})
    return I


# Family slot looks (linear RGB; E, from each family's sheet notes). Variants that are not a slot default (for a
# per-actor override) sit at the end of each table.
SURFACE = {  # part: (base colour, roughness, metallic)
    "Metal": ((0.85, 0.85, 0.87), 0.15, 1.0), "Chrome": ((0.9, 0.9, 0.92), 0.08, 1.0),
    "Aluminium": ((0.6, 0.6, 0.62), 0.35, 1.0), "PackInner": ((0.8, 0.8, 0.82), 0.25, 1.0),
    "Coin": ((1.0, 0.77, 0.34), 0.3, 1.0),
    "Steel": ((0.6, 0.61, 0.62), 0.5, 0.0), "SteelDark": ((0.12, 0.12, 0.13), 0.5, 0.0),
    "SteelBlack": ((0.02, 0.02, 0.022), 0.45, 0.0), "SteelOrange": ((0.8, 0.25, 0.02), 0.5, 0.0),
    "SteelBlue": ((0.03, 0.15, 0.5), 0.5, 0.0), "PowderBlack": ((0.02, 0.02, 0.022), 0.55, 0.0),
    "Felt": ((0.02, 0.02, 0.022), 0.95, 0.0), "Slatwall": ((0.8, 0.8, 0.78), 0.45, 0.0),
    "MDF": ((0.45, 0.33, 0.2), 0.9, 0.0), "Laminate": ((0.82, 0.82, 0.8), 0.4, 0.0),
    "PriceStrip": ((0.85, 0.85, 0.85), 0.3, 0.0), "Tray": ((0.01, 0.01, 0.01), 0.1, 0.0),
    "Cardboard": ((0.45, 0.32, 0.18), 0.85, 0.0), "Kraft": ((0.5, 0.36, 0.2), 0.85, 0.0),
    "BoardWhite": ((0.85, 0.85, 0.83), 0.8, 0.0), "Chipboard": ((0.55, 0.42, 0.28), 0.9, 0.0),
    "Tape": ((0.45, 0.3, 0.12), 0.3, 0.0), "Paper": ((0.9, 0.9, 0.88), 0.8, 0.0),
    "Foam": ((0.25, 0.25, 0.26), 1.0, 0.0), "Rubber": ((0.02, 0.02, 0.02), 0.9, 0.0),
    "Plastic": ((0.02, 0.02, 0.022), 0.45, 0.0), "PlasticWhite": ((0.85, 0.85, 0.85), 0.4, 0.0),
    "PlasticGrey": ((0.3, 0.3, 0.31), 0.6, 0.0), "BagBlack": ((0.01, 0.01, 0.01), 0.2, 0.0),
    "Bubble": ((0.8, 0.82, 0.85), 0.3, 0.0), "MagHolderBody": ((0.02, 0.02, 0.022), 0.15, 0.0),
    "BinderCover": ((0.03, 0.03, 0.035), 0.6, 0.0), "BinderSpine": ((0.03, 0.03, 0.035), 0.5, 0.0),
    "BinderPages": ((0.9, 0.9, 0.88), 0.7, 0.0), "Stitch": ((0.1, 0.1, 0.1), 0.8, 0.0),
    "Resin": ((0.6, 0.05, 0.05), 0.2, 0.0), "TableTop": ((0.85, 0.85, 0.85), 0.5, 0.0),
    "Vinyl": ((0.02, 0.02, 0.02), 0.35, 0.0), "AccentRed": ((0.6, 0.03, 0.03), 0.4, 0.0),
    "AccentYellow": ((0.8, 0.6, 0.02), 0.4, 0.0), "AccentGreen": ((0.05, 0.45, 0.08), 0.4, 0.0),
    "AccentBlue": ((0.03, 0.12, 0.5), 0.4, 0.0), "Cord": ((0.05, 0.05, 0.05), 0.8, 0.0),
    "Plaster": ((0.8, 0.79, 0.76), 0.9, 0.0), "FloorVinyl": ((0.35, 0.33, 0.3), 0.6, 0.0),
    "CeilingTile": ((0.85, 0.85, 0.85), 0.95, 0.0),
    # variants (not slot defaults): a_display's white table legs, g_devices' silver and copper coins
    "Steel_White": ((0.85, 0.85, 0.85), 0.5, 0.0), "Coin_Silver": ((0.9, 0.9, 0.92), 0.3, 1.0),
    "Coin_Copper": ((0.95, 0.64, 0.54), 0.35, 1.0),
}
EMISSIVE = {  # part: (base colour, emissive colour, intensity)
    "Screen": ((0.01, 0.01, 0.012), (0.2, 0.35, 0.6), 2.0), "ScanWindow": ((0.3, 0.0, 0.0), (1.0, 0.05, 0.05), 3.0),
    "SignLit": ((0.9, 0.9, 0.9), (1.0, 0.97, 0.9), 4.0),     # G1 Print has no emissive: a lit flat panel for now
    "LED_Panel": ((0.9, 0.9, 0.9), (1.0, 0.97, 0.92), 60.0),  # variant: a ceiling panel's diffuser (the strip MI is 8)
}
CLEAR = {  # part: (opacity, edge opacity, roughness, base colour)
    "MagHolderWindow": (0.08, 0.35, 0.03, (1, 1, 1)), "FilmStack": (0.6, 0.8, 0.4, (0.95, 0.95, 0.97)),
}
_CF, _CB, _LB, _BD = "T_CSK_G1_CardFront_BC", "T_CSK_G1_CardBack_BC", "T_CSK_G1_Label_BC", "T_CSK_G1_BoxDieline_BC"
PRINT_PLAIN = {  # part: (front, back, label texture, non-print colour)
    "BoxPrintL": (_BD, _BD, _BD, (0.8, 0.78, 0.72)), "Label": (_LB, _LB, _LB, (0.9, 0.9, 0.88)),
    "TopLoaderFilled": (_CF, _CB, _LB, (0.9, 0.95, 1.0)), "MagHolderFilled": (_CF, _CB, _LB, (0.02, 0.02, 0.022)),
    "SleeveBack": (_CB, _CB, _CB, (0.2, 0.05, 0.05)), "Playmat": (_CF, _CB, _LB, (0.02, 0.02, 0.02)),
    "Money": (_CF, _CB, _LB, (0.8, 0.85, 0.75)), "Sign": (_CF, _CB, _LB, (0.9, 0.9, 0.9)),
    "Poster": (_CF, _CB, _LB, (0.9, 0.9, 0.9)), "PriceTag": (_CF, _CB, _LB, (0.95, 0.95, 0.95)),
    "BagPrint": (_CF, _CB, _LB, (0.5, 0.36, 0.2)), "CuttingMat": (_CF, _CB, _LB, (0.05, 0.3, 0.12)),
}


# mesh slot name -> default instance (the plain path)
SLOT_DEFAULT = {"M_CSK_Card": "MI_CSK_G1_Card_Plain", "M_CSK_Pack": "MI_CSK_G1_Pack_Plain",
                "M_CSK_SlabBody": "MI_CSK_G1_SlabBody_Plain", "M_CSK_SlabWindow": "MI_CSK_G1_Acrylic",
                "M_CSK_SlabFilled": "MI_CSK_G1_SlabFilled_Plain", "M_CSK_PVC": "MI_CSK_G1_PVC",
                "M_CSK_BoxPrint": "MI_CSK_G1_BoxPrint_Plain", "M_CSK_Board": "MI_CSK_G1_Board",
                "M_CSK_Frame": "MI_CSK_G1_Frame", "M_CSK_Base": "MI_CSK_G1_Base", "M_CSK_LED": "MI_CSK_G1_LED",
                "M_CSK_Glass": "MI_CSK_G1_Glass", "M_CSK_Oak": "MI_CSK_G1_Oak", "M_CSK_Deck": "MI_CSK_G1_Deck",
                "M_CSK_Film": "MI_CSK_G1_Film", "M_CSK_Acrylic": "MI_CSK_G1_Acrylic"}
SLOT_DEFAULT.update({f"M_CSK_{p}": f"MI_CSK_G1_{p}" for t in (SURFACE, EMISSIVE, CLEAR, PRINT_PLAIN) for p in t
                     if "_" not in p})       # the "_" parts are variants


def main():
    t0 = time.time()
    rep = {"engine": unreal.SystemLibrary.get_engine_version(), "masters": {}, "instances": {}, "meshes": {}}
    masters = {}
    for name, fn in MASTERS.items():
        e = {}
        try:
            mat, created = get_or_create(f"{C.MAT_DEST}/{name}", unreal.Material, unreal.MaterialFactoryNew())
            fn(mat)
            MEL.layout_material_expressions(mat)
            MEL.recompile_material(mat)
            e = {"created": created, "expressions": int(MEL.get_num_material_expressions(mat)),
                 "saved": bool(EAL.save_loaded_asset(mat, False))}
            masters[name] = mat
        except Exception:  # noqa: BLE001
            e["error"] = traceback.format_exc()[-1500:]
        rep["masters"][name] = e
    mis = {}
    try:
        table = instances()
    except Exception:  # noqa: BLE001 - e.g. a missing atlas index: still write the report
        table = {}
        rep["instances_error"] = traceback.format_exc()[-1500:]
    for name, (master, scal, vec, tex) in table.items():
        e = {}
        try:
            mi, created = get_or_create(f"{C.MAT_DEST}/{name}", unreal.MaterialInstanceConstant,
                                        unreal.MaterialInstanceConstantFactoryNew())
            MEL.clear_all_material_instance_parameters(mi)
            MEL.set_material_instance_parent(mi, masters[master])
            for k, v in scal.items():
                MEL.set_material_instance_scalar_parameter_value(mi, k, float(v))
            for k, v in vec.items():
                MEL.set_material_instance_vector_parameter_value(mi, k, lc(v))
            for k, v in tex.items():
                t = unreal.load_asset(f"{C.TEX_DEST}/{v}")
                if t is None:
                    raise RuntimeError(f"texture {v} not imported")
                MEL.set_material_instance_texture_parameter_value(mi, k, t)
            MEL.update_material_instance(mi)
            e = {"created": created, "master": master,
                 "readback": {k: round(float(MEL.get_material_instance_scalar_parameter_value(mi, k)), 5) for k in scal},
                 "saved": bool(EAL.save_loaded_asset(mi, False))}
            mis[name] = mi
        except Exception:  # noqa: BLE001
            e["error"] = traceback.format_exc()[-1500:]
        rep["instances"][name] = e
    for name in C.MESHES:
        e = {"slots": {}, "unmatched": []}
        try:
            mesh = unreal.load_asset(f"{C.MESH_DEST}/{name}")
            for i, s in enumerate(mesh.get_editor_property("static_materials")):
                slot = str(s.get_editor_property("material_slot_name"))
                mi = mis.get(SLOT_DEFAULT.get(slot, ""))
                if mi is None:
                    e["unmatched"].append(slot)
                    continue
                mesh.set_material(i, mi)
                e["slots"][slot] = mi.get_name()
            e["saved"] = bool(EAL.save_loaded_asset(mesh, False))
        except Exception:  # noqa: BLE001
            e["error"] = traceback.format_exc()[-1500:]
        rep["meshes"][name] = e
    errs = [k for sec in ("masters", "instances", "meshes") for k, v in rep[sec].items() if v.get("error")]
    unmatched = {k: v["unmatched"] for k, v in rep["meshes"].items() if v.get("unmatched")}
    rep["errors"], rep["unmatched_slots"] = errs, unmatched
    rep["passed"] = not errs and not unmatched and "instances_error" not in rep
    rep["sec"] = round(time.time() - t0, 1)
    C.write_json(C.OUT / "materials.json", rep)
    unreal.log(f"CSK_STEP_DONE materials passed={rep['passed']} masters={len(masters)} instances={len(mis)}")


main()
