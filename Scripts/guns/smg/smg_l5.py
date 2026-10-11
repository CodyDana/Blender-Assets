"""SMG01 gate L5 (colour; GUN_BUILDING_STUDY 7.3 / STONE_BUILDING_STUDY 6.2 SG11 tolerances; the AR-01's rifle_l5.py):

    py -3 -B Scripts/guns/smg/smg_l5.py --render <tex_side.png> [--light k] [--json PATH] [--calib receiver_upper]

The render is the LEFT side view from the BAKED MAPS in the sheet panel's own px <-> mm frame (smg_texrender --set
side, 3x), so each traced part label (trace/LEFT_parts_index.png, eroded 3 px: edges and the silhouette difference
stay out) lines up with the sheet. Per region: median sRGB of the sheet vs ours -> luma (Rec. 709 on sRGB 0..1), HSV
saturation, R/B, hue (only where both saturations >= 0.15). Tolerances: luma +-0.05, saturation +-0.05, R/B +-0.1,
hue +-4 deg. The sheet's light is unknown (spec materials.sheet_samples_srgb: lit values), so ONE light scale is fitted
on the largest polymer region (receiver_upper: smg_l5_fit.py) and every other region is a relative test under it.
Also reported (spec gate L5): the polymer / steel luminance ratio of the render vs the sheet's (receiver vs rails +
barrel + device, linear luminance of the medians).
"""
from __future__ import annotations

import argparse
import colorsys
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WORK = ROOT / "WorkFiles" / "guns" / "smg"
TRACE = WORK / "trace"
SHEET = ROOT / "References" / "Guns" / "SMG" / "smg_sheetA.webp"
REGIONS = {"receiver_upper": 23, "handguard_area": 22, "receiver_lower": 21, "mag_well": 20, "grip": 19,
           "trigger_guard": 18, "magazine": 1, "butt_pad": 10, "stock_top_strut": 11, "stock_lower_strut": 12,
           "stock_neck": 13, "stock_rear_upright": 15, "hinge_block": 8, "stock_hinge_knuckle": 9,
           "top_rail": 6, "lower_rail": 7, "barrel": 3, "muzzle_device": 2}
STEEL = ("top_rail", "lower_rail", "barrel", "muzzle_device")
# reported, not graded: the eroded top-rail label is the row of slot GAPS seen end-on (the sheet draws them as voids,
# sRGB 3-6: shadow, no surface colour; any PBR albedo stops at sRGB 30); the rail's own colour is graded on the lower
# rail, the barrel and the device
SHADOW_REGIONS = {"top_rail": "slot gaps seen end-on: voids / shadow (sheet sRGB 3-6 < the PBR albedo floor 30)"}
TOL = {"luma": 0.05, "sat": 0.05, "rb": 0.10, "hue_deg": 4.0}


def erode(m, n):
    for _ in range(n):
        e = m.copy()
        e[1:, :] &= m[:-1, :]
        e[:-1, :] &= m[1:, :]
        e[:, 1:] &= m[:, :-1]
        e[:, :-1] &= m[:, 1:]
        m = e
    return m


def lin(x):
    x = np.asarray(x, float)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def stats(px):
    med = np.median(px, axis=0) / 255.0
    luma = float(0.2126 * med[0] + 0.7152 * med[1] + 0.0722 * med[2])
    h, s, v = colorsys.rgb_to_hsv(*med)
    return {"median_srgb": [round(float(x) * 255, 1) for x in med], "luma": round(luma, 4), "sat": round(s, 4),
            "hue_deg": round(h * 360.0, 2), "rb": round(float(med[0] / max(med[2], 1e-4)), 4),
            "lin_lum": float(lin(med) @ np.array([0.2126, 0.7152, 0.0722]))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", required=True)
    ap.add_argument("--light", type=float, default=1.0)
    ap.add_argument("--json", default=str(WORK / "scratch" / "l5" / "l5.json"))
    ap.add_argument("--calib", default="receiver_upper")
    a = ap.parse_args()
    j = json.loads((TRACE / "LEFT_outline.json").read_text())
    x0, y0, x1, y1 = j["panel_box_sheet_px"]
    sheet = np.asarray(Image.open(SHEET).convert("RGB"), float)[y0:y1 + 1, x0:x1 + 1]
    lab = np.asarray(Image.open(TRACE / "LEFT_parts_index.png"))
    ours = np.asarray(Image.open(a.render).convert("RGB"), float)
    H, W = lab.shape
    ss = ours.shape[0] // H
    ours = ours[:H * ss, :W * ss].reshape(H, ss, W, ss, 3).mean((1, 3))
    bg = np.all(np.abs(ours - 126.0) < 2.5, axis=2)
    out = {"render": Path(a.render).name, "light_scale": a.light, "tolerances": TOL, "regions": {}}
    for name, k in REGIONS.items():
        m = erode(lab == k, 3) & ~bg
        if m.sum() < 30:
            continue
        s_, o_ = stats(sheet[m]), stats(ours[m])
        d = {"luma": round(o_["luma"] - s_["luma"], 4), "sat": round(o_["sat"] - s_["sat"], 4),
             "rb": round(o_["rb"] - s_["rb"], 4)}
        chroma = s_["sat"] >= 0.15 and o_["sat"] >= 0.15
        if chroma:
            d["hue_deg"] = round(((o_["hue_deg"] - s_["hue_deg"]) + 180.0) % 360.0 - 180.0, 2)
        ok = abs(d["luma"]) <= TOL["luma"] and abs(d["sat"]) <= TOL["sat"] and abs(d["rb"]) <= TOL["rb"] and \
            (not chroma or abs(d["hue_deg"]) <= TOL["hue_deg"])
        out["regions"][name] = {"pixels": int(m.sum()), "sheet": s_, "ours": o_, "delta": d, "pass": bool(ok)}
    rec = out["regions"].get(a.calib)
    if rec:
        out["calibration"] = {"region": a.calib, "linear_luminance_ratio_sheet_over_ours":
                              round(rec["sheet"]["lin_lum"] / max(rec["ours"]["lin_lum"], 1e-9), 4)}
    st = [r for n, r in out["regions"].items() if n in STEEL]
    if st and rec:
        ws = np.array([r["pixels"] for r in st], float)
        s_steel = float(np.average([r["sheet"]["lin_lum"] for r in st], weights=ws))
        o_steel = float(np.average([r["ours"]["lin_lum"] for r in st], weights=ws))
        out["polymer_steel_ratio"] = {"sheet": round(rec["sheet"]["lin_lum"] / s_steel, 3),
                                      "ours": round(rec["ours"]["lin_lum"] / o_steel, 3), "spec_band": [1.3, 1.5]}
    calib = set(a.calib.split(","))
    tested = {k: v for k, v in out["regions"].items() if k not in calib and k not in SHADOW_REGIONS}
    out["reported_only"] = {k: dict(reason=SHADOW_REGIONS[k], delta=out["regions"][k]["delta"])
                            for k in SHADOW_REGIONS if k in out["regions"]}
    out["calibration_regions"] = sorted(calib)
    out["pass"] = all(v["pass"] for v in tested.values())
    out["failed"] = [k for k, v in tested.items() if not v["pass"]]
    Path(a.json).parent.mkdir(parents=True, exist_ok=True)
    Path(a.json).write_text(json.dumps(out, indent=1))
    for k, v in out["regions"].items():
        print("[L5] %-20s sheet %-22s ours %-22s d %s %s" % (k, v["sheet"]["median_srgb"], v["ours"]["median_srgb"],
                                                             v["delta"], "PASS" if v["pass"] else "FAIL"))
    print("[L5] ratio", out.get("polymer_steel_ratio"), "calib", out.get("calibration"))
    print("[L5]", "PASS" if out["pass"] else "FAIL", out["failed"])


if __name__ == "__main__":
    main()
