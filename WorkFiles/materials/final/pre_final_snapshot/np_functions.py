"""The pack's five material functions (MATERIAL_PLAN.md sections 3-4, material_spec.json material_functions).

Each builder receives an EMPTY function (np_assets.fresh_function deletes every expression first), so a rebuild
produces the same graph from nothing.

    MF_TintDetail     Albedo = Colour * n' * DetailMean / E(C)   (exactly Colour * n at the default colour)
    MF_AlbedoRollOff  hue-preserving soft ceiling above the knee (identity below it)
    MF_NormalStrength normalize(lerp((0,0,1), N, Strength))
    MF_LetteringBand  LETTERING_HOWTO.md section 5: ink = mask(band UV) inside the band rectangle
    MF_InkDerive      dry / pooled ink colours derived from the buyer's ink colours (exact at the defaults)
"""
from __future__ import annotations

import unreal

from np_graph import Graph

FIT = unreal.FunctionInputType
S, V2, V3, V4, T2D = (FIT.FUNCTION_INPUT_SCALAR, FIT.FUNCTION_INPUT_VECTOR2, FIT.FUNCTION_INPUT_VECTOR3,
                      FIT.FUNCTION_INPUT_VECTOR4, FIT.FUNCTION_INPUT_TEXTURE2D)
LUM = (0.2126, 0.7152, 0.0722)

DESCRIPTIONS = {
    "MF_TintDetail": (
        "Recolours a greyscale detail map. n = DetailBias + DetailScale x Detail is each texel's multiple of the "
        "part's MEAN colour. The detail exponent shrinks with the colour's headroom, H = log(AlbedoCeiling / "
        "max(Colour)) / log(HighlightRatio): C_hi = min(DetailStrength, max(H, 0)) for n > 1, C_lo = lerp("
        "DetailStrength, C_hi, DarkFollow) for n <= 1. Albedo = Colour x n^C x DetailMean / E(C), E from the "
        "two cubic moment fits, so the part's average stays Colour x DetailMean. At the shipped colour H >= 1, "
        "C = 1 and the result is exactly Colour x n (the item's baked colour)."),
    "MF_AlbedoRollOff": (
        "Hue-preserving soft ceiling: below Knee the colour is unchanged; above it the largest channel eases "
        "towards Limit (Knee + (Limit - Knee)(1 - exp(-(m - Knee)/(Limit - Knee)))) and the other channels "
        "follow in proportion."),
    "MF_NormalStrength": "normalize(lerp((0, 0, 1), Normal, Strength)). Strength 1 = the map as shipped.",
    "MF_LetteringBand": (
        "The kunai grip's lettering band (References/Kunai/LETTERING_HOWTO.md section 5). BandRect = (u min, "
        "v min, u max, v max) in UV0; Ink = LetteringMask(band UV).r inside the rectangle, 0 outside; "
        "BaseColor and Roughness blend to the lettering values by Ink. A blank mask changes nothing."),
    "MF_InkDerive": (
        "Paper-bomb ink colours derived from the buyer's colours. BlackDry = lerp(BlackInk, Paper, Mix) x Gain; "
        "RedDry = sRGBdecode(ValueScale x sRGBencode(RedInk)); RedPool = lerp(Y(RedInk), RedInk, Saturation) x "
        "PoolGain. The gains are fitted so every derived colour equals the art's palette at the default colours."),
}


def _poly(g: Graph, m, c):
    """Cubic with ASCENDING coefficients in m.rgba: R + c (G + c (B + c A))  (Horner)."""
    return g.add(g.mask(m, "r"), g.mul(c, g.add(g.mask(m, "g"), g.mul(c, g.add(g.mask(m, "b"),
                                                                              g.mul(c, g.mask(m, "a")))))))


def build_tint_detail(mf):
    g = Graph(mf, is_function=True)
    detail = g.fn_input("Detail", S, 0, "Linear detail value (Detail Map .R, 0..1)")
    colour = g.fn_input("Colour", V3, 1, "The part's mean colour (linear)")
    bias = g.fn_input("DetailBias", S, 2)
    scale = g.fn_input("DetailScale", S, 3)
    mean = g.fn_input("DetailMean", S, 4, "mean of n over the map (~1)")
    strength = g.fn_input("DetailStrength", S, 5, "1 = as shipped, 0 = flat")
    ratio = g.fn_input("HighlightRatio", S, 6, "p99.9 of n")
    follow = g.fn_input("DarkFollow", S, 7, "how far the dark weave follows the highlight softening (0..1)")
    ceiling = g.fn_input("AlbedoCeiling", S, 8, "brightest albedo a highlight may reach")
    m_lo = g.fn_input("MomentsLow", V4, 9, "cubic E[n^c; n <= 1], ascending coefficients")
    m_hi = g.fn_input("MomentsHigh", V4, 10, "cubic E[n^c; n > 1], ascending coefficients")

    n = g.max(g.add(bias, g.mul(scale, detail)), 1e-6)
    cmax = g.max(g.max3(colour), 1e-4)
    headroom = g.div(g.log2(g.div(ceiling, cmax)), g.log2(ratio))
    c_hi = g.min(strength, g.max(headroom, 0.0))
    c_lo = g.lerp(strength, c_hi, follow)
    expo = g.if_(n, 1.0, c_hi, c_lo, c_lo)
    n_soft = g.pow(n, expo)
    e = g.add(_poly(g, m_lo, c_lo), _poly(g, m_hi, c_hi))
    albedo = g.mul(colour, g.mul(n_soft, g.div(mean, e)))
    g.fn_output("Albedo", 0, albedo, "before MF_AlbedoRollOff")
    g.fn_output("Headroom", 1, headroom, "H: >= 1 means the colour keeps the full detail")
    return g


def build_albedo_rolloff(mf):
    g = Graph(mf, is_function=True)
    a = g.fn_input("Albedo", V3, 0)
    knee = g.fn_input("Knee", S, 1, "0.85 in the fabric master")
    limit = g.fn_input("Limit", S, 2, "0.95 in the fabric master")
    m = g.max3(a)
    w = g.max(g.sub(limit, knee), 1e-4)
    t = g.max(g.sub(m, knee), 0.0)
    mm = g.add(knee, g.mul(w, g.one_minus(g.exp(g.div(g.mul(t, -1.0), w)))))
    out = g.mul(a, g.div(mm, g.max(m, knee)))
    g.fn_output("Albedo", 0, out)
    return g


def build_normal_strength(mf):
    g = Graph(mf, is_function=True)
    nrm = g.fn_input("Normal", V3, 0, "tangent-space normal (sampled normal map)")
    strength = g.fn_input("Strength", S, 1, "1 = as shipped")
    out = g.normalize(g.lerp((0.0, 0.0, 1.0), nrm, strength))
    g.fn_output("Normal", 0, out)
    return g


def build_lettering_band(mf):
    g = Graph(mf, is_function=True)
    base = g.fn_input("BaseColor", V3, 0)
    rough = g.fn_input("Roughness", S, 1)
    ink_colour = g.fn_input("LetteringColour", V3, 2)
    ink_rough = g.fn_input("LetteringRoughness", S, 3)
    rect = g.fn_input("BandRect", V4, 4, "u min, v min, u max, v max in UV0")
    mask_tex = g.fn_input("LetteringMask", T2D, 5, "greyscale, white = ink, sampled with Clamp")
    uv = g.texcoord(0)
    lo = g.mask(rect, "rg")
    hi = g.mask(rect, "ba")
    band_uv = g.div(g.sub(uv, lo), g.sub(hi, lo))
    d = g.sub(g.abs(g.sub(band_uv, 0.5)), 0.5)
    outside = g.sat(g.ceil(g.max(g.mask(d, "r"), g.mask(d, "g"))))
    inside = g.one_minus(outside)
    sample = g.sample(mask_tex, band_uv, unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
    ink = g.mul(sample.r, inside)
    g.fn_output("BaseColor", 0, g.lerp(base, ink_colour, ink))
    g.fn_output("Roughness", 1, g.lerp(rough, ink_rough, ink))
    g.fn_output("Ink", 2, ink)
    return g


def _srgb_encode(g: Graph, x):
    x = g.sat(x)
    lin = g.mul(x, 12.92)
    curve = g.sub(g.mul(g.pow(x, 1.0 / 2.4), 1.055), 0.055)
    return g.if_(x, 0.0031308, curve, lin, lin)


def _srgb_decode(g: Graph, s):
    s = g.sat(s)
    lin = g.div(s, 12.92)
    curve = g.pow(g.div(g.add(s, 0.055), 1.055), 2.4)
    return g.if_(s, 0.04045, curve, lin, lin)


def build_ink_derive(mf):
    g = Graph(mf, is_function=True)
    paper = g.fn_input("PaperColour", V3, 0)
    black = g.fn_input("BlackInkColour", V3, 1)
    red = g.fn_input("RedInkColour", V3, 2)
    mix = g.fn_input("BlackDryPaperMix", S, 3)
    gain = g.fn_input("BlackDryGain", V3, 4)
    value_scale = g.fn_input("RedDryValueScale", S, 5, "0.82: the palette scales red_wet in STORED (sRGB) space")
    pool_sat = g.fn_input("RedPoolSaturation", S, 6)
    pool_gain = g.fn_input("RedPoolGain", V3, 7)

    black_dry = g.mul(g.lerp(black, paper, mix), gain)
    chans = []
    for ch in ("r", "g", "b"):
        c = g.mask(red, ch)
        chans.append(_srgb_decode(g, g.mul(_srgb_encode(g, c), value_scale)))
    red_dry = g.append(g.append(chans[0], chans[1]), chans[2])
    y = g.dot(red, LUM)
    red_pool = g.mul(g.lerp(y, red, pool_sat), pool_gain)
    g.fn_output("BlackDry", 0, black_dry)
    g.fn_output("RedDry", 1, red_dry)
    g.fn_output("RedPool", 2, red_pool)
    return g


BUILDERS = {
    "MF_TintDetail": build_tint_detail,
    "MF_AlbedoRollOff": build_albedo_rolloff,
    "MF_NormalStrength": build_normal_strength,
    "MF_LetteringBand": build_lettering_band,
    "MF_InkDerive": build_ink_derive,
}
