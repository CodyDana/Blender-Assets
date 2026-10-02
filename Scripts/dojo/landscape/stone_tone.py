"""LANDSCAPE ROUND (world stage): the stone kit's Unreal material-instance tone, MEASURED (plain Python + numpy).

The owner's target (LANDSCAPE_PLAN 0 / 4.2): mid-grey granite with moss, NOT the tan the kit reads in its Blender
renders; "under the daylight test light after G.look(), saturation at most about 0.12, R/B 1.05-1.15, moss in the
joints". A neutral daylight test light on a Lambert surface returns the albedo, so the gate is computed on the albedo
the M_DJ_Lib_Opaque graph makes (dj_sc_materials.build_lib_opaque + G.look, the moss / wear terms off = the stone
face, not the joints):
    col = lerp(BC x Tint, MeanColour, FlattenToMean);  col = lerp(luma(col), col, Saturation) x ValueMult
measured over every texel of T_DJ_Granite_BC (sRGB decoded), reported as sRGB mean, HSV saturation of the mean,
R/B of the sRGB mean, and the value. The catalog (f3) values are measured first as the 'before'.
Out: world/json/stone_tone.json (the MI values dj_ls_materials.py applies)
"""
import colorsys
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
BC = np.asarray(Image.open(ROOT / "Exports/DojoKit/Materials/Textures/T_DJ_Granite_BC.png").convert("RGB"),
                np.float64) / 255.0
LIN = np.where(BC <= 0.04045, BC / 12.92, ((BC + 0.055) / 1.055) ** 2.4).reshape(-1, 3)
CAT = json.loads((ROOT / "WorkFiles/dojo/build/stonekit/kit_catalog.json").read_text(encoding="utf-8"))
MATS = CAT["tracks"]["stairs"]["materials"]
LUMA = np.array([0.2126, 0.7152, 0.0722])


def srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1 / 2.4) - 0.055)


def albedo(tint, mean, flatten, sat=1.0, vm=1.0):
    col = LIN * np.asarray(tint)
    col = col + (np.asarray(mean) - col) * flatten
    lum = (col * LUMA).sum(-1, keepdims=True)
    col = (lum + (col - lum) * sat) * vm
    m = col.mean(0)
    s = srgb(m) * 255
    h, sa, v = colorsys.rgb_to_hsv(*(s / 255))
    return {"linear_mean": [round(float(x), 4) for x in m], "srgb_mean": [round(float(x), 1) for x in s],
            "hsv_saturation": round(float(sa), 3), "hue_deg": round(float(h) * 360, 1), "r_over_b_srgb": round(float(s[0] / s[2]), 3),
            "value": round(float(v), 3), "texel_luma_p10_p90_srgb": [round(float(np.percentile(srgb((col * LUMA).sum(-1)), q))
                                                                    * 255, 1) for q in (10, 90)]}


# target: neutral mid grey with a whisper of warmth (R/B 1.10 in sRGB), per-slot values keeping the kit's ladder
# (StepGranite lighter than WallGranite, StepRiser darker, CopeGranite between); the moss colour is unchanged
TARGET_SRGB = {"M_DKT_WallGranite": 118, "M_DKT_CopeGranite": 108, "M_DKT_StepGranite": 138, "M_DKT_StepRiser": 88,
               "M_DKT_JointDark": 22, "M_DKT_MossPad": 30}
RB = 1.10


def solve(name):
    m = MATS[name]
    flat = m["flatten_to_mean"]
    base = albedo(m["tint_linear"], m["mean_linear"], flat)
    tgt = TARGET_SRGB[name]
    # a neutral-cool tint on the texture, a mean at the target grey with R/B 1.10, the texture's own chroma cut to 0.3
    g = (tgt / 255.0)
    g_lin = g / 12.92 if g <= 0.04045 else ((g + 0.055) / 1.055) ** 2.4
    # sRGB channel targets: R = g * k, B = g / k with k^2 = RB, G = g
    k = RB ** 0.5
    tgt_srgb = np.array([g * k, g, g / k])
    tgt_lin = np.where(tgt_srgb <= 0.04045, tgt_srgb / 12.92, ((tgt_srgb + 0.055) / 1.055) ** 2.4)
    tex_mean = LIN.mean(0)
    tint = tgt_lin / tex_mean                       # BC x Tint lands on the target mean
    sat = 0.3
    out = albedo(tint, tgt_lin, flat, sat)
    # one correction pass on the measured value (the flatten/saturation mix is not linear in sRGB)
    for _ in range(6):
        s = np.array(out["srgb_mean"]) / 255.0
        corr = np.where(tgt_srgb <= 0.04045, tgt_srgb / 12.92, ((tgt_srgb + 0.055) / 1.055) ** 2.4) / \
            np.where(s <= 0.04045, s / 12.92, ((s + 0.055) / 1.055) ** 2.4)
        tint = tint * corr
        tgt_lin2 = tgt_lin * corr
        out = albedo(tint, tgt_lin2, flat, sat)
        tgt_lin = tgt_lin2
    return {"catalog_f3": {"tint": m["tint_linear"], "mean": m["mean_linear"], "flatten": flat, "measured": base},
            "unreal": {"Tint": [round(float(x), 4) for x in tint], "MeanColour": [round(float(x), 5) for x in tgt_lin],
                       "FlattenToMean": flat, "Saturation": sat, "NormalStrength": m["normal_strength"],
                       "MossColour": m["moss"]["colour_linear"], "measured": out},
            "gate": {"sat_le_0.12": bool(out["hsv_saturation"] <= 0.12), "rb_1.05_1.15": bool(1.05 <= out["r_over_b_srgb"] <= 1.15)}}


def main():
    rep = {"rule": __doc__.split("\n")[3].strip(), "slots": {}}
    for name in TARGET_SRGB:
        rep["slots"][name] = solve(name)
    rep["passed"] = all(v["gate"]["sat_le_0.12"] and v["gate"]["rb_1.05_1.15"] for k, v in rep["slots"].items()
                        if k not in ("M_DKT_JointDark", "M_DKT_MossPad"))
    out = ROOT / "WorkFiles/dojo/build/landscape/world/json/stone_tone.json"
    out.write_text(json.dumps(rep, indent=1), encoding="utf-8")
    for k, v in rep["slots"].items():
        b, a = v["catalog_f3"]["measured"], v["unreal"]["measured"]
        print(f"{k:20s} f3 sRGB {b['srgb_mean']} sat {b['hsv_saturation']} R/B {b['r_over_b_srgb']}  ->  "
              f"UE {a['srgb_mean']} sat {a['hsv_saturation']} R/B {a['r_over_b_srgb']}")
    print("STONE_TONE passed", rep["passed"])


main()
