"""One-off: turn the r3 build spec into the final-pass (v2) spec. Run with the system Python:

    py -3 WorkFiles/materials/final/update_spec_v2.py

Reads WorkFiles/materials/final/pre_final_snapshot/material_spec.json (the r3 spec, snapshotted before this pass) and
writes Scripts/unreal/materials/material_spec.json. Every change is listed in the spec's own "changes_v2" section.
"""
import copy
import json
from pathlib import Path

P = Path("C:/Users/Cody/Desktop/Blender_Projects")
SRC = P / "WorkFiles/materials/final/pre_final_snapshot/material_spec.json"
DST = P / "Scripts/unreal/materials/material_spec.json"
s = json.loads(SRC.read_text(encoding="utf-8"))
old = copy.deepcopy(s)

ADV_FAB = "08 Advanced (matched to the detail map - do not change)"
ADV_PAP = "08 Advanced (matched to the paper maps - do not change)"
BAKED = "Use Original Baked Colours"
DEF = "Scripts/unreal/materials/default_textures/"

s["schema"] = "ninjapack.material_spec/2"
s["status"] = ("FINAL PASS v2 (2026-09-26): recolour fixes (black floor, lightest-colour cap, mip compensation, paper "
               "colour limit, neutral red pool), base/leaf instance chain, neutral master default textures, one "
               "parameter-group scheme, buyer tooltips. See changes_v2.")
s["plan"] = s.get("plan", "") + " | v2: WorkFiles/materials/MATERIALS_REPORT.md section 'Final pass'"
s["unreal"]["folders"]["base"] = "/Game/NinjaPack/MaterialInstances/Base"
s["unreal"]["folders"]["default_textures"] = "/Game/NinjaPack/Textures/Default"

# --------------------------------------------------------------------------------------------- functions (docs)
mf = s["material_functions"]
mf["MF_TintDetail"]["inputs"] = mf["MF_TintDetail"]["inputs"] + [
    "LightestColour", "MipLevel", "MipCompensation1to4 (V4)", "MipCompensation5to8 (V4)", "MipCompensationPower"]
mf["MF_TintDetail"]["outputs"] = ["Albedo (V3, before roll-off)", "Headroom"]
mf["MF_TintDetail"]["math"] = [
    "Colour_f = Colour + max(0.01 - max3(Colour), 0)            (v2: pure black is lifted to ~#1A1A1A, hue kept)",
    "Colour_e = Colour_f * min(1, LightestColour / max3(Colour_f)) (v2: very light picks scale down so the highlights keep detail)",
    "n      = DetailBias + DetailScale * Detail",
    "H      = log(AlbedoCeiling / max3(Colour_e)) / log(HighlightRatio)",
    "C_hi   = min(DetailStrength, max(H, 0)); C_lo = lerp(DetailStrength, C_hi, DarkFollow)",
    "n'     = n <= 1 ? pow(n, C_lo) : pow(n, C_hi)",
    "E(C)   = El(C_lo) + Eh(C_hi) (cubic moment fits, covered texels only in v2)",
    "K      = exp(-A(MipLevel) * max(1 - C_hi, 0)^P), A piecewise linear from the increments (v2: mip compensation)",
    "Albedo = Colour_e * n' * (DetailMean / E(C)) * K",
    "MipLevel (master) = 0.5 * log2(max(min(|dUV/dx|^2, |dUV/dy|^2), max(...)/64) * DetailMapSize^2), clamped 0..8"]
mf["MF_TintDetail"]["default_exactness"] = (
    "At the default Colour: Colour > 0.01 and < LightestColour (guards inactive), H >= 1 so C = 1, E(1) = DetailMean "
    "and K = exp(0) = 1, so Albedo = Colour * n: the item contract, at every mip (derive_constants.py gates).")
mf["MF_InkDerive"]["math"] = mf["MF_InkDerive"]["math"] + [
    "v2: PoolGain_e = lerp(mean(RedPoolGain), RedPoolGain, saturate(sat(RedInk) / RedPoolDefaultSaturation)), "
    "sat(c) = (max3 - min3) / max3: a neutral red-ink pick pools neutral; the default is exact"]

# --------------------------------------------------------------------------------------------- masters
def P_(name, typ, group, sort, desc=None, default=None, lo=None, hi=None, **kw):
    d = {"name": name, "type": typ, "group": group, "sort": sort}
    if default is not None:
        d["default"] = default
    if lo is not None:
        d["min"], d["max"] = lo, hi
    if desc:
        d["desc"] = desc
    d.update(kw)
    return d


def keep(master, name):
    return next(p for p in old["masters"][master]["parameters"] if p["name"] == name)


steel = s["masters"]["M_Steel_Master"]
steel["graph"]["BaseColor"] = "saturate(BaseColourMap.rgb * SteelTint)"
steel["settings"] = {"used_with_instanced_static_meshes": True}
steel["parameters"] = [
    P_("Steel Tint", "vector", "01 Colour", 0,
       "Multiplies the steel's colour. White = exactly as shipped. Try warm (1.0, 0.8, 0.6) for a bronze tone or cool "
       "(0.8, 0.9, 1.0) for blued steel. Values above 1 are clamped.", [1, 1, 1, 1]),
    P_("Roughness Adjust", "scalar", "03 Surface", 0,
       "Added to the baked roughness. Negative = more polished, positive = duller. 0 = as shipped.", 0.0, -0.25, 0.25),
    P_("Normal Strength", "scalar", "03 Surface", 1,
       "Strength of the normal map's scratches and relief. 1 = as shipped, 0 = flat.", 1.0, 0.0, 2.0),
    P_("Base Colour Map", "texture", "09 Textures", 0, "The steel's colour map (sRGB).", sampler="Color"),
    P_("ORM Map", "texture", "09 Textures", 1, "R ambient occlusion, G roughness, B metallic (linear).", sampler="Masks"),
    P_("Normal Map", "texture", "09 Textures", 2, "Normal map (DirectX / Unreal convention).", sampler="Normal"),
]

fab = s["masters"]["M_Fabric_Master"]
fab["graph"]["BaseColor"] = ("UseOriginalBakedColours ? BaseColourMap.rgb : MF_AlbedoRollOff(MF_TintDetail(DetailMap.r, "
                             "Colour, LightestColour, ..., MipLevel), 0.85, 0.95); then UseLettering ? MF_LetteringBand(...)")
fab["settings"] = {"float_precision_mode": "MFPM_FULL", "used_with_instanced_static_meshes": True}
sheen_col = keep("M_Fabric_Master", "Sheen Colour")
fab["parameters"] = [
    P_("Colour", "vector", "01 Colour", 0,
       "The colour of this part: its average colour. Click the swatch and pick any colour (the picker's Hex sRGB field "
       "takes web colours). The weave, fibre and wear detail follow the new colour. Very light picks are capped by "
       "Lightest Colour so the highlights keep their detail; pure black is lifted to about #1A1A1A so the detail stays "
       "visible. The default is the shipped look.", "per instance"),
    P_("Lightest Colour", "scalar", "01 Colour", 1,
       "The lightest average brightness this part will take (linear). Lighter picks are scaled down to it, keeping "
       "their hue, so the highlights never blow out into flat white. Raise it for a brighter result with softer "
       "highlight detail (0.9 = no limit).", "per instance", 0.3, 0.9),
    P_(BAKED, "static_switch", "01 Colour", 2,
       "On = ignore the colour settings and show the original baked colour map exactly as shipped (fixed colour).",
       False),
    P_("Detail Strength", "scalar", "02 Detail", 0,
       "How strong the cloth or straw detail is. 1 = as shipped, 0 = flat colour. On very light colours the highlight "
       "detail is limited automatically, so values above 1 mainly deepen the darker weave.", 1.0, 0.0, 1.5),
    P_("Roughness Adjust", "scalar", "03 Surface", 0,
       "Added to the baked roughness. Negative = shinier, positive = duller. 0 = as shipped.", 0.0, -0.25, 0.25),
    P_("Specular Strength", "scalar", "03 Surface", 1,
       "Strength of the surface reflection. On the smoke bomb and the hat it scales the baked specular mask, which "
       "keeps the cloth from looking greyed. 0.5 = standard.", "per instance", 0.0, 1.0),
    P_("Normal Strength", "scalar", "03 Surface", 2,
       "Strength of the normal map's weave and folds. 1 = as shipped, 0 = flat.", 1.0, 0.0, 2.0),
    P_("Cloth Sheen", "static_switch", "04 Sheen", 0,
       "Optional soft, velvety cloth sheen (Unreal's Cloth shading model). Off by default: without it the part matches "
       "the original look more closely.", False),
    dict(sheen_col, desc="Colour of the soft sheen at grazing angles. Used when Cloth Sheen is on."),
    P_("Sheen Amount", "scalar", "04 Sheen", 2, "Strength of the cloth sheen. Used when Cloth Sheen is on.",
       0.35, 0.0, 1.0),
    P_("Use Lettering", "static_switch", "05 Lettering", 0,
       "Kunai only: paints the Lettering Mask onto the grip's lettering band. The shipped mask is blank, so this is "
       "off; see the kunai README to paint your own text.", False),
    P_("Lettering Colour", "vector", "05 Lettering", 1, "Colour of the painted lettering (white in the mask = ink).",
       [0.62, 0.56, 0.44, 1.0]),
    P_("Lettering Roughness", "scalar", "05 Lettering", 2, "Roughness of the painted lettering.", 0.62, 0.0, 1.0),
    P_("Lettering Mask", "texture", "05 Lettering", 3,
       "Greyscale lettering mask, 1536 x 256, white = ink (kunai README, 'Lettering').", sampler="LinearGrayscale"),
    P_("Lettering Band UV", "vector", "05 Lettering", 4,
       "Where the lettering band sits in the kunai's UVs (u min, v min, u max, v max). Do not change unless you "
       "re-map the mesh.", [1.1328125, 0.61898509, 1.8359375, 0.73617259, 0.0]),
]
adv_desc = "Matched to this part's detail map. Do not change."
for i, (name, typ) in enumerate([("Detail Bias", "scalar"), ("Detail Scale", "scalar"), ("Detail Mean", "scalar"),
                                 ("Detail Highlight Ratio", "scalar"), ("Detail Moments Low", "vector"),
                                 ("Detail Moments High", "vector"), ("Dark Detail Follow", "scalar"),
                                 ("Albedo Ceiling", "scalar"), ("Detail Map Size", "scalar"),
                                 ("Detail Mip Compensation 1-4", "vector"), ("Detail Mip Compensation 5-8", "vector"),
                                 ("Detail Mip Compensation Power", "scalar")]):
    d = {"Dark Detail Follow": 0.5, "Albedo Ceiling": 0.9}.get(name)
    extra = {"Dark Detail Follow": "How much of the highlight softening the dark weave follows on light colours. ",
             "Albedo Ceiling": "The brightest a highlight may get on light colours. ",
             "Detail Map Size": "The detail map's width in texels (for the distance correction). ",
             "Detail Mip Compensation 1-4": "Keeps a recoloured part the same colour at a distance as up close. ",
             "Detail Mip Compensation 5-8": "Keeps a recoloured part the same colour at a distance as up close. ",
             "Detail Mip Compensation Power": "Keeps a recoloured part the same colour at a distance as up close. "}.get(name, "")
    fab["parameters"].append(P_(name, typ, ADV_FAB, i, extra + adv_desc, d))
fab["parameters"] += [
    P_("Specular From ORM Alpha", "static_switch", "09 Textures", 0,
       "On = the ORM map's alpha holds a baked specular mask (smoke bomb, hat). Off = constant specular.", True),
    P_("Detail Map", "texture", "09 Textures", 1,
       "16-bit linear greyscale detail map that drives the recolour. Swap it only together with its matched settings "
       "in 08 Advanced.", sampler="LinearGrayscale"),
    P_("Base Colour Map", "texture", "09 Textures", 2,
       "The original baked colour map, used when Use Original Baked Colours is on.", sampler="Color"),
    P_("ORM Map", "texture", "09 Textures", 3, "R ambient occlusion, G roughness, B metallic, A specular mask (linear).",
       sampler="Masks"),
    P_("Normal Map", "texture", "09 Textures", 4, "Normal map (DirectX / Unreal convention).", sampler="Normal"),
]

pap = s["masters"]["M_PaperInk_Master"]
pap["graph"]["BaseColor"] = ("UseOriginalBakedColours ? BaseColourMap.rgb : min(PaperColour_e*(PaperDetail.rgb*PaperWeightScale) "
                             "+ BlackInk*Ink.r + BlackDry*Ink.g + RedInk*Ink.b + RedDry*Ink.a + RedPool*PaperDetail.a, "
                             "AlbedoCeiling); then * lerp(1, ORM.R, BakedAOInColour). PaperColour_e = floor + "
                             "PaperColour * min(1, PaperColourLimit / max3)")
pap["settings"] = {"float_precision_mode": "MFPM_FULL", "used_with_instanced_static_meshes": True}
pap["parameters"] = [
    P_("Paper Colour", "vector", "01 Colour", 0,
       "The paper's average colour. Grain, ageing, stains and the show-through on the back follow it. The lightest "
       "paper is about #F3F3F3 so the grain stays visible; pure black is lifted to about #1A1A1A. The default is the "
       "shipped look.", "per instance"),
    P_("Black Ink Colour", "vector", "01 Colour", 1,
       "Colour of the brushed text and emblem. The dry-brush strokes follow it.", "per instance"),
    P_("Red Ink Colour", "vector", "01 Colour", 2,
       "Colour of the border, ring and seals. The dry and pooled strokes follow it; pooled ink is always darker.",
       "per instance"),
    P_(BAKED, "static_switch", "01 Colour", 9,
       "On = ignore the colour settings and show the original baked colour map exactly as shipped (fixed colour).",
       False),
    P_("Roughness Adjust", "scalar", "03 Surface", 0,
       "Added to the baked roughness. Negative = shinier, positive = duller. 0 = as shipped.", 0.0, -0.25, 0.25),
    P_("Specular Strength", "scalar", "03 Surface", 1, "Strength of the surface reflection. 0.5 = standard.",
       0.5, 0.0, 1.0),
    P_("Normal Strength", "scalar", "03 Surface", 2, "Strength of the paper's creases and relief. 1 = as shipped.",
       1.0, 0.0, 2.0),
    P_("Baked AO In Colour", "scalar", "03 Surface", 3,
       "How much of the baked ambient occlusion darkens the colour itself. 1 = the original look, 0 = none.",
       1.0, 0.0, 1.0),
]
adv = [("Paper Weight Scale", "scalar", None), ("Black Ink Dry Paper Mix", "scalar", None),
       ("Black Ink Dry Gain", "vector", None), ("Red Ink Dry Value Scale", "scalar", 0.82),
       ("Red Ink Pool Saturation", "scalar", None), ("Red Ink Pool Gain", "vector", None),
       ("Albedo Ceiling", "scalar", 0.962), ("Paper Colour Limit", "scalar", None),
       ("Red Ink Pool Default Saturation", "scalar", None)]
for i, (name, typ, d) in enumerate(adv):
    pap["parameters"].append(P_(name, typ, ADV_PAP, i, "Matched to this item's paper and ink maps. Do not change.", d))
pap["parameters"] += [
    P_("Base Colour Map", "texture", "09 Textures", 1, "The original baked colour map, used when Use Original Baked "
       "Colours is on.", sampler="Color"),
    P_("ORM Map", "texture", "09 Textures", 2, "R ambient occlusion, G roughness, B metallic (linear).", sampler="Masks"),
    P_("Normal Map", "texture", "09 Textures", 3, "Normal map (DirectX / Unreal convention).", sampler="Normal"),
    P_("Paper Detail Map", "texture", "09 Textures", 4,
       "Paper grain and pooled-ink weights that drive the paper recolour. Swap only with its matched settings.",
       sampler="Color"),
    P_("Ink Weights Map", "texture", "09 Textures", 5,
       "Where each ink sits (R black, G dry black, B red, A dry red). Swap only with its matched settings.",
       sampler="LinearColor"),
]

# --------------------------------------------------------------------------------------------- slots
for item in s["items"]:
    for slot in item["slots"]:
        prm = slot.get("params") or {}
        if "Use Baked Colour Map" in prm:
            prm[BAKED] = prm.pop("Use Baked Colour Map")
        if slot["master"] == "M_Fabric_Master":
            for key in ("Colour", "Detail Bias", "Detail Scale", "Detail Mean", "Detail Highlight Ratio",
                        "Detail Moments Low", "Detail Moments High"):
                if key in prm:
                    prm[key] = "GENERATOR (recolour_constants.json, derived from recolour_maps.json over covered texels)"
        if slot["instance"] == "MI_Kunai_Plain_Wrap":
            prm["Use Lettering"] = False
            slot["lettering_note"] = "v2: Use Lettering OFF until a real mask exists (blank mask: no visible effect, +16 PS instructions)"
        for pr in slot.get("presets") or []:
            if "Use Baked Colour Map" in pr["params"]:
                pr["params"][BAKED] = pr["params"].pop("Use Baked Colour Map")
            pr["parent"] = pr["parent"] + "_Base"
        slot["base_instance"] = slot["instance"] + "_Base"

# --------------------------------------------------------------------------------------------- instances list
inst = []
for i in s["instances"]:
    if i.get("folder") == "Presets":
        inst.append({**i, "parent": i["parent"] + "_Base"})
        continue
    inst.append({"name": i["name"] + "_Base", "parent": i["parent"], "folder": "Base",
                 "role": "holds every texture and matched setting of the part"})
    inst.append({"name": i["name"], "parent": i["name"] + "_Base", "role": "buyer-facing: overrides only the colour(s)"})
s["instances"] = inst

# --------------------------------------------------------------------------------------------- build
b = s["build"]
b.pop("master_default_textures", None)
b["recolour_constants"] = {g: f"Exports/{g}/Textures/Recolour/recolour_constants.json"
                           for g in ("Shuriken", "SmokeBomb", "BlackHat", "PaperBomb")}
b["recolour_constants_note"] = ("Scripts/unreal/materials/maps/derive_constants.py derives them from the Recolour maps; "
                                "their params override recolour_maps.json. run_build.sh 'maps_check' verifies the sha256 chain.")
b["default_textures"] = {
    f"{DEF}T_NP_Default_BC.png": "BC", f"{DEF}T_NP_Default_ORM.png": "ORM_rgba", f"{DEF}T_NP_Default_N.png": "N",
    f"{DEF}T_NP_Default_Detail16.png": "Detail16", f"{DEF}T_NP_Default_Lettering.png": "Lettering",
    f"{DEF}T_NP_Default_PaperDetail.png": "PaperDetail_sRGB", f"{DEF}T_NP_Default_InkWeights.png": "InkWeights_linear"}
tex = lambda n: f"{DEF}T_NP_Default_{n}.png"  # noqa: E731
b["master_defaults"] = {
    "note": ("v2: masters reference ONLY the neutral 8x8 textures in /Game/NinjaPack/Textures/Default (no item's maps: "
             "no dependency drag), and neutral parameter values (a flat grey preview). Every Base instance overrides them."),
    "M_Steel_Master": {"textures": {"Base Colour Map": tex("BC"), "ORM Map": tex("ORM"), "Normal Map": tex("N")},
                       "params": {}},
    "M_Fabric_Master": {
        "textures": {"Detail Map": tex("Detail16"), "Base Colour Map": tex("BC"), "ORM Map": tex("ORM"),
                     "Normal Map": tex("N"), "Lettering Mask": tex("Lettering")},
        "params": {"Colour": [0.18, 0.18, 0.18, 1.0], "Lightest Colour": 0.6, "Specular Strength": 0.5,
                   "Detail Bias": 0.0, "Detail Scale": 2.0, "Detail Mean": 1.0, "Detail Highlight Ratio": 2.0,
                   "Detail Moments Low": [1.0, 0.0, 0.0, 0.0], "Detail Moments High": [0.0, 0.0, 0.0, 0.0],
                   "Detail Map Size": 8.0, "Detail Mip Compensation 1-4": [0.0, 0.0, 0.0, 0.0],
                   "Detail Mip Compensation 5-8": [0.0, 0.0, 0.0, 0.0], "Detail Mip Compensation Power": 1.0}},
    "M_PaperInk_Master": {
        "textures": {"Base Colour Map": tex("BC"), "ORM Map": tex("ORM"), "Normal Map": tex("N"),
                     "Paper Detail Map": tex("PaperDetail"), "Ink Weights Map": tex("InkWeights")},
        "params": {"Paper Colour": [0.7, 0.7, 0.7, 1.0], "Black Ink Colour": [0.005, 0.005, 0.005, 1.0],
                   "Red Ink Colour": [0.66, 0.01, 0.004, 1.0], "Paper Weight Scale": 1.0,
                   "Black Ink Dry Paper Mix": 0.0, "Black Ink Dry Gain": [1.0, 1.0, 1.0, 1.0],
                   "Red Ink Pool Saturation": 0.3, "Red Ink Pool Gain": [0.08, 0.08, 0.08, 1.0],
                   "Paper Colour Limit": 0.9, "Red Ink Pool Default Saturation": 1.0}},
}
b["instance_chain"] = {
    "base_folder": "/Game/NinjaPack/MaterialInstances/Base", "base_suffix": "_Base",
    "leaf_overrides": {"M_Steel_Master": [], "M_Fabric_Master": ["Colour"],
                       "M_PaperInk_Master": ["Paper Colour", "Black Ink Colour", "Red Ink Colour"]},
    "why": ("Buyer review: every instance was a direct child of the master, whose defaults were the smoke bomb's, so "
            "resetting a parameter on the hat or kunai silently gave the smoke bomb's colour and constants. Now "
            "MI_<Item>_<Part>_Base holds every texture and matched setting, and the buyer-facing MI_<Item>_<Part> "
            "(the one on the mesh) overrides only its colour(s): reset-to-default restores that part's shipped look.")}
b["clean_policy"] = ("v2: 'clean' deletes only the assets the spec authors (functions, masters, base, leaf and preset "
                     "instances) and REFUSES if Materials/ or MaterialInstances/ hold anything else (a buyer's or "
                     "artist's own variant would be listed, never deleted). Add variants as spec presets.")

s["changes_v2"] = [
    "BLOCKER light colours: MF_TintDetail caps the mean at 'Lightest Colour' (per part, min(0.6, 0.9 / HighlightRatio^0.2)) so C_hi >= 0.2: no flat highlight plateau",
    "MAJOR mips: MF_TintDetail multiplies by exp(-A(lod)(1-C_hi)^P), fitted per part on the Unreal mip chain (derive_constants.py): a recoloured part keeps its colour at distance",
    "MAJOR black: Colour and Paper Colour get a hue-preserving floor (max channel >= 0.01): 000000 keeps its detail",
    "MAJOR paper full intensity: Paper Colour is scaled to at most 'Paper Colour Limit' (0.962 / p99.9 paper weight) before the 0.962 ceiling: no clipped grain. The hard min stays (the art's own clip; a soft knee would change the default)",
    "MINOR red pool: the pool gain's chroma fades with the red ink's saturation (neutral picks pool neutral)",
    "MINOR constants over covered texels only (recolour_constants.json): Colour = the visible mean",
    "MAJOR reset trap: MI_<Item>_<Part>_Base holds everything; the buyer MI overrides only its colour(s)",
    "MAJOR dependency drag: masters reference only /Game/NinjaPack/Textures/Default 8x8 maps",
    "MAJOR compatibility: Float Precision Mode Full on the fabric and paper masters; Used With Instanced Static Meshes preset on all three",
    "MINOR tooltips in buyer language; one group scheme (01 Colour, 02 Detail, 03 Surface, 04 Sheen, 05 Lettering, 08 Advanced, 09 Textures); 'Use Baked Colour Map' renamed 'Use Original Baked Colours' and moved to 01 Colour; Steel Tint clamped",
    "MINOR the kunai wrap ships Use Lettering OFF",
    "MINOR clean deletes only spec'd assets; run_build.sh checks the Recolour map sha256 chain; paths derived from the script location",
]
DST.write_text(json.dumps(s, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print("wrote", DST)
