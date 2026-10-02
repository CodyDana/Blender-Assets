"""Pilot reference measurement on the owner's rock sheet (References/Dojo/dojo_rocks_ref.png): silhouettes of the
three pilot rocks in every view the sheet draws, the 1.8 m figure scale per row, sizes in metres, shape measures, and
value / hue per region (study 6.1). Writes WorkFiles/dojo/build/rocks/ref_measure.json, the masks and overlays.

    py -3 -B Scripts/dojo/rocks/rocks_ref.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Scripts" / "stone"))
import rock_ref as rr          # noqa: E402
import stone_measure as sm     # noqa: E402

SHEET = ROOT / "References" / "Dojo" / "dojo_rocks_ref.png"
LAND = ROOT / "References" / "Dojo" / "dojo_landscape_ref.png"
OUT = ROOT / "WorkFiles" / "dojo" / "build" / "rocks"
REF = OUT / "pilot" / "refcrops"

# Figure boxes (the 1.8 m figure per row; the silhouette's top-to-feet height in px).
FIGURES = {"row2": (0, 250, 65, 445), "row4": (0, 600, 62, 835)}

# Views of the pilot rocks: ROI boxes in sheet px (x0, y0, x1, y1). "scale" says how the view's px map to metres:
# "row" = the row figure's px/m (drawn at the main scale), "rel:<view>" = scaled so its width matches that view's
# length (the reduced lower views of row 2 and the reduced side views of row 4).
VIEWS = {
    # row 2, boulder 2: the rounded one (a loaf: broad front, domed top, steep sides), with a full-scale end view
    "RiverRound": {
        "front": dict(box=(334, 252, 506, 364), scale="row2"),
        "side": dict(box=(503, 262, 600, 364), scale="row2"),
        "top": dict(box=(340, 364, 512, 440), scale="rel:front"),
        "side_small": dict(box=(510, 364, 592, 440), scale="rel:top"),
    },
    # row 2, boulder 3: the long, low one (two fused lobes, a vertical crack at the join)
    "RiverLong": {
        "front": dict(box=(612, 255, 898, 364), scale="row2"),
        "top": dict(box=(632, 364, 800, 440), scale="rel:front"),
        "side": dict(box=(800, 364, 884, 440), scale="rel:top"),
    },
    # row 4, chunk 1: blocky jointed granite, stepped ledges, vertical cracks, grass on the ledges
    "CliffChunk": {
        "front": dict(box=(58, 600, 266, 836), scale="row4"),
        "top": dict(box=(252, 600, 358, 688), scale="rel:front"),
        "side": dict(box=(268, 682, 356, 834), scale="rel:front_h"),
    },
}

# Close-up panels (bottom row) and the riverbank scene.
CLOSEUPS = {"grain": (8, 845, 178, 1080), "fracture": (184, 845, 346, 1080), "moss": (351, 845, 521, 1080),
            "wetline": (527, 845, 700, 1080), "lichen": (706, 845, 866, 1080), "riverbank": (873, 840, 1448, 1086)}

# The landscape reference's river boulders (study 3.11's colour family), sheet px boxes inside one boulder each.
LAND_CROPS = {"land_boulder_A": (412, 1205, 520, 1320), "land_boulder_B": (560, 1172, 632, 1215),
              "land_boulder_C": (410, 1012, 505, 1125)}


def figure_px(img, box):
    x0, y0, x1, y1 = box
    L = img[y0:y1, x0:x1].mean(-1)
    m = L < 150
    ys = np.nonzero(m.any(1))[0]
    return int(ys.max() - ys.min() + 1)


def regions(mask):
    """Row bands of a silhouette: top 25 %, middle, bottom 30 % (the wet band on river boulders)."""
    ys, xs = np.nonzero(mask)
    y0, y1 = ys.min(), ys.max() + 1
    h = y1 - y0
    yy = np.arange(mask.shape[0])[:, None]
    top = mask & (yy < y0 + 0.25 * h)
    bot = mask & (yy >= y0 + 0.70 * h)
    mid = mask & ~top & ~bot
    return {"all": mask, "top25": top, "mid": mid, "bottom30": bot}


def value_regions(img, box, mask):
    x0, y0, x1, y1 = box
    rgb = img[y0:y1, x0:x1] / 255.0
    out = {}
    for k, m in regions(mask).items():
        if m.sum() < 50:
            continue
        v = sm.image_values(rgb, m)
        out[k] = {"luma_p5_p25_p50_p75_p95": v["method_A"]["luma_p5_p25_p50_p75_p95"],
                  "local_std_16px": v["method_A"]["local_std_16px"], "R_over_B": v["method_A"]["R_over_B"],
                  "p90_over_p50": v["method_C"]["p90_over_p50"], "hue": v["method_C"]["stone_hue_deg"],
                  "sat": v["method_C"]["stone_sat"], "moss_share": v["moss_share"]}
    return out


def main():
    img = rr.load(SHEET)
    REF.mkdir(parents=True, exist_ok=True)
    fig = {k: figure_px(img, b) for k, b in FIGURES.items()}
    ppm = {k: v / 1.8 for k, v in fig.items()}
    res = {"sheet": str(SHEET.relative_to(ROOT)), "sha256": rr.sha256(SHEET), "figure_px": fig,
           "px_per_m": {k: round(v, 2) for k, v in ppm.items()},
           "scale_uncertainty": "figure top/feet +-2 px (1.5 %); the figure stands in the rocks' plane (assumed)",
           "method": "Scripts/stone/rock_ref.py silhouette (seed mode), checked by overlay", "rocks": {}}
    for rock, views in VIEWS.items():
        R = {}
        masks = {}
        for vname, v in views.items():
            m, info = rr.silhouette(img, v["box"])
            masks[vname] = m
            rr.save_mask(rr.crop_to_mask(m), REF / f"mask_{rock}_{vname}.png")
            np.save(REF / f"mask_{rock}_{vname}.npy", rr.crop_to_mask(m))
            rr.overlay(img, v["box"], m, REF / f"ovl_{rock}_{vname}.png")
            x0, y0, x1, y1 = info["bbox_px"]
            Image.fromarray(img[y0:y1, x0:x1].astype(np.uint8)).save(REF / f"crop_{rock}_{vname}.png")
            info["shape"] = rr.shape_measures(m)
            info["values"] = value_regions(img, v["box"], m)
            R[vname] = info
        # metres
        row = [v["scale"] for v in views.values() if v["scale"].startswith("row")][0]
        k = ppm[row]
        for vname, v in views.items():
            sc = v["scale"]
            if sc.startswith("row"):
                s = k
            elif sc == "rel:front":     # a reduced view whose WIDTH is the front's length
                s = R[vname]["w_px"] / (R["front"]["w_px"] / k)
            elif sc == "rel:front_h":   # a reduced view whose HEIGHT is the front's height
                s = R[vname]["h_px"] / (R["front"]["h_px"] / k)
            elif sc == "rel:top":       # drawn at the same reduced scale as the top view
                s = R["top"]["px_per_m"]
            R[vname]["px_per_m"] = round(s, 2)
            R[vname]["w_m"] = round(R[vname]["w_px"] / s, 3)
            R[vname]["h_m"] = round(R[vname]["h_px"] / s, 3)
        res["rocks"][rock] = R
    # close-ups and landscape colour family
    cl = {}
    for k, b in CLOSEUPS.items():
        rgb = img[b[1]:b[3], b[0]:b[2]] / 255.0
        Image.fromarray(img[b[1]:b[3], b[0]:b[2]].astype(np.uint8)).save(REF / f"close_{k}.png")
        v = sm.image_values(rgb)
        cl[k] = {"box": list(b), "luma_p5_p25_p50_p75_p95": v["method_A"]["luma_p5_p25_p50_p75_p95"],
                 "local_std_16px": v["method_A"]["local_std_16px"], "R_over_B": v["method_A"]["R_over_B"],
                 "p90_over_p50": v["method_C"]["p90_over_p50"], "hue": v["method_C"]["stone_hue_deg"],
                 "sat": v["method_C"]["stone_sat"], "moss_share": v["moss_share"]}
    # grain: dark speckle share (luma < 0.25) and bright share (> 0.75) on the grain close-up
    b = CLOSEUPS["grain"]
    rgb = img[b[1]:b[3], b[0]:b[2]] / 255.0
    lu = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
    cl["grain"]["dark_lt_0.25"] = round(float((lu < 0.25).mean()), 4)
    cl["grain"]["bright_gt_0.75"] = round(float((lu > 0.75).mean()), 4)
    res["closeups"] = cl
    land = rr.load(LAND)
    lc = {}
    for k, b in LAND_CROPS.items():
        rgb = land[b[1]:b[3], b[0]:b[2]] / 255.0
        Image.fromarray(land[b[1]:b[3], b[0]:b[2]].astype(np.uint8)).save(REF / f"{k}.png")
        v = sm.image_values(rgb)
        lc[k] = {"box": list(b), "luma_p5_p25_p50_p75_p95": v["method_A"]["luma_p5_p25_p50_p75_p95"],
                 "local_std_16px": v["method_A"]["local_std_16px"], "R_over_B": v["method_A"]["R_over_B"],
                 "p90_over_p50": v["method_C"]["p90_over_p50"], "hue": v["method_C"]["stone_hue_deg"],
                 "sat": v["method_C"]["stone_sat"], "stone_srgb_mean": v["method_C"]["stone_srgb_mean"]}
    res["landscape_colour_family"] = {"image": str(LAND.relative_to(ROOT)), "sha256": rr.sha256(LAND), "crops": lc}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "ref_measure.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    for rock, R in res["rocks"].items():
        for vname, info in R.items():
            print(rock, vname, info["w_px"], info["h_px"], info["w_m"], info["h_m"], info["shape"])
    print(json.dumps(res["closeups"], indent=0)[:1500])
    print(json.dumps(lc, indent=0))


if __name__ == "__main__":
    main()
