"""AR-01 per-part wood tone ratios (orchestrator ruling L5, 2026-10-05), plain Python:

    py -3 -B Scripts/guns/rifle/rifle_wood_tone.py [--l5 WorkFiles/guns/rifle/scratch/game/l5.json] [--reset]

The sheet's four wood parts are four different pieces of walnut (side-panel R/B: grip 2.04, upper handguard 2.12, lower
handguard 2.47, stock 2.57), as mismatched furniture on real rifles of this pattern is. The furniture stays ONE
recolourable stain (rifle_spec walnut #6B3C27, the pack's recolour rule); each part carries a tone ratio relative to the
stain (linear RGB multipliers, rifle_paint.WOOD_TONE), baked into T_AR01_Furniture_BC.

Calibration (one step per call, on the physical L5 rig): for each wood part, tone *= lin(sheet median) / lin(our median)
per channel, from an L5 record of a render of the current maps (rifle_l5_fit.py). Two or three rounds of
[paint Furniture -> rifle_l5_fit -> this] converge (the specular term is additive, so one step is not exact).

How the pack's recolour treats it (M_Fabric_Master: BaseColor = Colour x n(Detail), n a SCALAR detail; no master
change): rifle_recolour.py derives the Detail16 map from lum(BC), so each part's VALUE ratio (lum of its tone) is in
the detail and moves with any buyer colour; the part's HUE offset (the chroma of its tone, unit luminance) lives only in
the shipped BC. A recolour therefore moves all four parts together to the buyer's hue, keeping their relative values;
the default look (the sheet's four tones) is the baked BC (Use Original Baked Colours, or the recolour at the default
Colour within the measured per-part chroma offset: rifle_recolour.py records it).

Writes WorkFiles/guns/rifle/wood_tone.json (tone_linear per part, its unit-luminance chroma and value, history).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
W = ROOT / "WorkFiles" / "guns" / "rifle"
OUT = W / "wood_tone.json"
PART_REGION = {"buttstock": "stock", "pistol_grip": "pistol_grip", "lower_handguard": "handguard_lower",
               "upper_handguard": "handguard_upper"}
R4_VALUE = {"upper_handguard": 1.12, "lower_handguard": 1.04, "pistol_grip": 0.97, "buttstock": 1.0}
LUM = np.array([0.2126, 0.7152, 0.0722])


def s2l(c):
    c = np.asarray(c, float) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--l5", default=str(W / "scratch" / "game" / "l5.json"))
    ap.add_argument("--reset", action="store_true", help="start from the r4 grey per-part values")
    a = ap.parse_args()
    doc = json.loads(OUT.read_text()) if OUT.exists() and not a.reset else {
        "tone_linear": {k: [v, v, v] for k, v in R4_VALUE.items()}, "history": []}
    if a.reset:
        OUT.write_text(json.dumps(_finish(doc), indent=1))
        print("[wood-tone] reset to the r4 values")
        return
    l5 = json.loads(Path(a.l5).read_text())
    step = {}
    for part, reg in PART_REGION.items():
        r = l5["regions"][reg]
        ratio = s2l(r["sheet"]["median_srgb"]) / np.maximum(s2l(r["ours"]["median_srgb"]), 1e-5)
        t = np.asarray(doc["tone_linear"][part], float) * ratio
        doc["tone_linear"][part] = [round(float(x), 5) for x in t]
        step[part] = {"delta_before": r["delta"], "ratio": [round(float(x), 4) for x in ratio]}
    doc["history"].append({"l5": Path(a.l5).name, "k": l5.get("fit", {}).get("light_scale"), "step": step})
    OUT.write_text(json.dumps(_finish(doc), indent=1))
    for p, v in doc["tone_linear"].items():
        print("[wood-tone]", p, v, step[p]["delta_before"])


def _finish(doc):
    stain = s2l([0x6B, 0x3C, 0x27])
    doc["stain_srgb"] = "#6B3C27"
    doc["parts"] = {}
    for p, t in doc["tone_linear"].items():
        t = np.asarray(t, float)
        c = stain * t
        val = float(c @ LUM / (stain @ LUM))
        doc["parts"][p] = {"value_ratio": round(val, 4), "chroma_ratio_unit_lum": [round(float(x), 4) for x in t / val],
                           "base_srgb8": [int(round(float(x))) for x in
                                          255 * np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1 / 2.4) - 0.055)],
                           "base_rb_srgb": round(float((c[0] / c[2]) ** (1 / 2.4)), 3)}
    doc["recolour"] = ("value_ratio -> the Detail16 map (moves with the buyer's colour); chroma_ratio -> the baked BC "
                       "only (a recolour gives every part the buyer's hue, keeping the value ratios)")
    return doc


if __name__ == "__main__":
    main()
