"""HP01 tracer stage 2: frame, hand reads, outlines in mm, measured numbers, overlay (called by trace_reference.py).

READS are sheet px on the LEFT panel (muzzle to image left), read on 3-4x gridded zooms (tools/gridzoom.py,
scratch/g_*.png), +-1 px unless noted. Profiles (serrations, rail, TOP edges) are measured, not read.
"""
from __future__ import annotations

import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

import refimg

READS = {
    # muzzle group
    "crown_front_x": 27.0, "crown_y": [192.0, 232.0],                 # barrel crown boss proud of the face plate
    "face_plate_x": [31.0, 41.0], "face_plate_y": [176.0, 250.0],     # front plate (thin band, 45 deg lower chamfer)
    "face_plate_lower_chamfer": [[40.0, 250.0], [50.0, 270.0]],
    "slide_front_x": 42.0,
    # front sight (dovetailed block with a white-free dot pin), on the barrel rib
    "front_sight_x": [45.0, 82.0], "front_sight_top_y": 145.0, "front_sight_top_x": [51.0, 70.0],
    "front_sight_base_y": 169.0,
    # top line (rib top): rises toward the rear
    "top_line": [[80.0, 171.0], [210.0, 166.0], [345.0, 161.0]],
    # facet bands on the flank (side view): upper chamfer band (light) and lower chamfer
    "upper_facet_y": [177.0, 197.0], "flank_y": [198.0, 248.0], "lower_band_y": [250.0, 279.0],
    "upper_facet_rear_taper": [[400.0, 197.0], [455.0, 185.0]],      # facet runs out in a diagonal (barrel hood end)
    # rail recess on the top (front wall, rear ramp) and crossbar caps (side view: 6 bars)
    "rail_recess_x": [349.0, 484.0], "rail_cap_y": 157.0, "rail_floor_y": 170.0,
    "rail_bars_x": [[355.0, 366.0], [377.0, 388.0], [399.0, 409.0], [421.0, 432.0], [443.0, 456.0], [467.0, 479.0]],
    "rail_bars_top_view": 5,
    # rear block of the slide
    "rear_block_top_y": 158.0, "rear_block_front_x": 485.0,
    "rear_sight_x": [504.0, 535.0], "rear_sight_top_y": 140.0, "rear_sight_base_y": 170.0,
    "slide_rear_top": [540.0, 178.0], "slide_rear_bottom": [560.0, 248.0],
    # serration field (parallelogram, grooves lean top-forward)
    "serr_field_top": [[457.0, 181.0], [519.0, 181.0]], "serr_field_bottom": [[477.0, 248.0], [538.0, 248.0]],
    # slide flank tab (sheet part, both sides)
    "flank_tab": [[375.0, 222.0], [425.0, 222.0], [432.0, 236.0], [425.0, 243.0], [378.0, 243.0]],
    # safety lever (dark block at the slide rear, beside the hammer), hammer spur
    "safety_box": [[543.0, 185.0], [565.0, 250.0]], "hammer_box": [[555.0, 183.0], [591.0, 250.0]],
    "hammer_spur_tip": [589.0, 190.0],
    # frame
    "slide_frame_seam_y": 250.0, "frame_front_x": 262.0, "frame_top_band_y": [250.0, 278.0],
    "guard_outer_front": [[265.0, 250.0], [283.0, 300.0], [288.0, 345.0]], "guard_bottom_y": 355.0,
    "guard_opening": [[302.0, 278.0], [393.0, 347.0]], "guard_pin": [286.0, 283.0, 4.0],
    "trigger_box": [[360.0, 278.0], [396.0, 340.0]], "trigger_tip": [365.0, 338.0], "trigger_pivot": [378.0, 281.0],
    "slide_stop": [[483.0, 252.0], [552.0, 252.0], [540.0, 262.0], [510.0, 272.0], [490.0, 262.0]],
    "beavertail_tip": [599.0, 270.0],
    "front_strap": [[395.0, 348.0], [440.0, 488.0]],
    "grip_panel": [[410.0, 282.0], [500.0, 282.0], [540.0, 478.0], [450.0, 478.0]],
    "backstrap_groove": [[515.0, 300.0], [560.0, 478.0]],
    "grip_bottom_y": 490.0, "mag_base": [[438.0, 490.0], [568.0, 500.0]],
}


def ring_mm(r, fr):
    return [[round(fr["X"](x), 2), round(fr["Z"](y), 2)] for x, y in r]


def stage2(rgb, res, side, top, OUT, TR, SC, REAL):
    bL = side[0]["box"]
    FL = side[0]["F"]
    rings = [r for r in refimg.marching_squares(np.where(side[0]["m"], FL, np.minimum(FL, 0.49)), 0.5)
             if abs(refimg.signed_area(r)) > 2000]
    ring = max(rings, key=lambda r: abs(refimg.signed_area(r)))
    ring[:, 0] += bL[0]
    ring[:, 1] += bL[1]
    x_front, x_rear = float(ring[:, 0].min()), float(ring[:, 0].max())
    y_top, y_bot = float(ring[:, 1].min()), float(ring[:, 1].max())
    L_px = x_rear - x_front
    s = L_px / REAL["overall_mm"]
    bore_y = 0.5 * sum(READS["crown_y"])
    fr = {"X": lambda x: (x_front - x) / s, "Z": lambda y: (bore_y - y) / s}
    X, Z = fr["X"], fr["Z"]

    maj = res["ruler"]["RIGHT"]["major_x"]
    ruler_px_mm = float(np.mean(np.diff(maj))) / 50.0
    scale = {"rule": "real overall length of the class (GUN_BUILDING_STUDY 3.5 [E49]); rulers are reported only",
             "real": REAL, "sheet_len_px": round(L_px, 2), "px_per_mm": round(s, 4),
             "ruler_px_per_mm": round(ruler_px_mm, 4), "ruler_length_mm": round(L_px / ruler_px_mm, 1),
             "ruler_error_pct": round(100 * (L_px / ruler_px_mm / REAL["overall_mm"] - 1), 1),
             "sheet_height_mm": round((READS["mag_base"][1][1] - READS["rear_sight_top_y"]) / s, 1),
             "height_over_length_sheet": round((READS["mag_base"][1][1] - READS["rear_sight_top_y"]) / L_px, 4),
             "height_over_length_real": round(REAL["height_mm"] / REAL["overall_mm"], 4)}

    # ---------------------------------------------------------------- measured profiles
    g = rgb.astype(float).mean(axis=2)
    # serrations: groove minima on rows across the field
    serr = []
    (ta, tb), (ba, bb) = READS["serr_field_top"], READS["serr_field_bottom"]
    for y in (190, 205, 220, 235):
        t = (y - ta[1]) / (ba[1] - ta[1])
        x0 = int(round(ta[0] + t * (ba[0] - ta[0]))) - 2
        x1 = int(round(tb[0] + t * (bb[0] - tb[0]))) + 2
        r = ndi.gaussian_filter1d(g[y, x0:x1], 0.7)
        mins = [i for i in range(2, len(r) - 2) if r[i] == r[i - 2:i + 3].min() and r[i] < 75]
        serr.append([x0 + i for i in mins])
    n_grooves = int(np.median([len(m) for m in serr]))
    pitch_h = float(np.median(np.concatenate([np.diff(m) for m in serr])))
    a, b = READS["serr_field_top"][0], READS["serr_field_bottom"][0]
    lean = math.degrees(math.atan2(b[0] - a[0], b[1] - a[1]))
    serrations = {"rows_px": serr, "grooves": n_grooves, "pitch_along_X_mm": round(pitch_h / s, 2),
                  "pitch_normal_mm": round(pitch_h / s * math.cos(math.radians(lean)), 2),
                  "lean_deg_top_forward": round(lean, 1),
                  "field_F": [[round(X(p[0]), 1), round(Z(p[1]), 1)] for p in
                              (READS["serr_field_top"] + READS["serr_field_bottom"][::-1])]}
    bars = READS["rail_bars_x"]
    cen = [0.5 * (p + q) for p, q in bars]
    rail = {"bars_side": len(bars), "bars_top_view": READS["rail_bars_top_view"],
            "bar_centres_X": [round(X(c), 1) for c in cen],
            "pitch_mm_sheet": round((cen[-1] - cen[0]) / (len(cen) - 1) / s, 2),
            "bar_width_mm_sheet": round(float(np.mean([q - p for p, q in bars])) / s, 2),
            "recess_X": [round(X(READS["rail_recess_x"][1]), 1), round(X(READS["rail_recess_x"][0]), 1)],
            "cap_Z": round(Z(READS["rail_cap_y"]), 1), "floor_Z": round(Z(READS["rail_floor_y"]), 1)}

    # ---------------------------------------------------------------- TOP: outer edges per column, width profile
    bT = top[2]["box"]
    gT = ndi.gaussian_filter(g[bT[1]:bT[3] + 1, bT[0]:bT[2] + 1], 0.6)
    grad = np.abs(np.diff(gT, axis=0))
    mT = top[2]["m"]
    xs = np.nonzero(mT.any(axis=0))[0]
    xT0, xT1 = int(xs.min()), int(xs.max())
    prof = []
    for x in range(xT0 + 2, xT1 - 1):
        idx = np.nonzero(grad[200:360, x] > 6)[0]
        if len(idx) < 2:
            continue
        prof.append((x, 200 + idx.min() + 0.5, 200 + idx.max() + 0.5))
    prof = np.array(prof, float)
    yc = float(np.median(0.5 * (prof[:, 1] + prof[:, 2])))
    sT = (xT1 - xT0) / REAL["overall_mm"]
    width = []
    for Xmm in np.arange(-270.0, 0.1, 5.0):
        xpx = xT0 + (-Xmm) * sT
        k = int(np.argmin(np.abs(prof[:, 0] - xpx)))
        width.append([round(float(Xmm), 1), round(float((prof[k, 2] - prof[k, 1]) / s), 1)])
    slide_w = float(np.median([w for x_, w in width if -150 <= x_ <= -30]))
    top_res = {"len_px": xT1 - xT0, "px_per_mm_own": round(sT, 4), "axis_y_panel_px": round(yc, 2),
               "width_profile_mm_every_5": width, "slide_width_mm_sheet": round(slide_w, 1),
               "max_width_mm_sheet": round(max(w for _, w in width), 1),
               "note": "edges from the luma-gradient envelope (the steel flats match the backdrop luma, so the "
                       "soft field fails on TOP); +-1 px"}

    # 3/4 cross-check of the width (crown ellipse foreshortening)
    q34 = {"crown_ellipse_px": [36.0, 60.0], "face_plate_px": [51.0, 117.0],
           "cos_theta": round(36.0 / 60.0, 3),
           "plate_w_over_h_34": round(51.0 / (36.0 / 60.0) / 117.0, 3),
           "plate_w_over_h_side_top": round(83.0 / 94.0, 3),
           "reading": "the 3/4 draws the front plate ~17 % narrower (relative to its height) than TOP + side; "
                      "pitch would make the 3/4 ratio smaller still. A proportion disagreement, not a design one"}

    # ---------------------------------------------------------------- outlines
    def mirror_ring():
        bR = side[1]["box"]
        FR = side[1]["F"][:, ::-1]
        mR = side[1]["m"][:, ::-1]
        rr = [r for r in refimg.marching_squares(np.where(mR, FR, np.minimum(FR, 0.49)), 0.5)
              if abs(refimg.signed_area(r)) > 2000]
        r = max(rr, key=lambda r: abs(refimg.signed_area(r))).copy()
        dx = x_front - (r[:, 0].min() + bL[0])
        r[:, 0] += bL[0] + dx
        r[:, 1] += bL[1]
        return r, dx

    ringR, dxR = mirror_ring()
    ringL_s = refimg.dp_simplify(ring, 0.25)
    ringR_s = refimg.dp_simplify(ringR, 0.25)
    shape = rgb.shape[:2]
    mLs = refimg.rings_to_mask([ring], shape)
    mRs = refimg.rings_to_mask([ringR], shape)
    self_iou = refimg.iou(mLs, mRs)

    # TOP outline from the gradient envelope (columns) -> polygon
    topring = np.concatenate([np.c_[prof[:, 0], prof[:, 1]], np.c_[prof[::-1, 0], prof[::-1, 2]]])
    topring[:, 0] += bT[0]
    topring[:, 1] += bT[1]
    frT = {"X": lambda x: (bT[0] + xT0 - x) / s, "Y": lambda y: (y - (bT[1] + yc)) / s}

    feats = {}
    for k, v in READS.items():
        arr = np.array(v, float)
        if arr.ndim == 1 and len(arr) == 2 and k.endswith(("_x",)):
            feats[k + "_F"] = [round(X(arr[1]), 1), round(X(arr[0]), 1)]
        elif arr.ndim == 1 and len(arr) == 2 and k.endswith(("_y",)):
            feats[k + "_F"] = [round(Z(arr[1]), 1), round(Z(arr[0]), 1)]
        elif arr.ndim == 2:
            feats[k + "_F"] = [[round(X(p[0]), 1), round(Z(p[1]), 1)] for p in arr]
        elif arr.ndim == 1 and len(arr) == 2:
            feats[k + "_F"] = [round(X(arr[0]), 1), round(Z(arr[1]), 1)]
        elif k.endswith("_y") and arr.ndim == 0:
            feats[k + "_F"] = round(Z(float(arr)), 1)
        elif k.endswith("_x") and arr.ndim == 0:
            feats[k + "_F"] = round(X(float(arr)), 1)
        elif k == "guard_pin":
            feats[k + "_F"] = [round(X(arr[0]), 1), round(Z(arr[1]), 1), round(arr[2] / s, 1)]

    key = {
        "overall_X": [round(X(x_rear), 1), 0.0],
        "height_Z": [round(Z(READS["mag_base"][1][1]), 1), round(Z(READS["rear_sight_top_y"]), 1)],
        "height_mm_reads": round((READS["mag_base"][1][1] - READS["rear_sight_top_y"]) / s, 1),
        "barrel_visible_X": [round(X(READS["slide_front_x"]), 1), 0.0],
        "bore_axis_Z": 0.0,
        "crown_diameter_mm": round((READS["crown_y"][1] - READS["crown_y"][0]) / s, 1),
        "slide_length_mm": round((READS["slide_rear_bottom"][0] - READS["face_plate_x"][0]) / s, 1),
        "slide_height_mm_mid": round((250.0 - 165.0) / s, 1),
        "slide_plus_lower_band_mm": round((279.0 - 166.0) / s, 1),
        "sight_radius_mm": round((0.5 * sum(READS["rear_sight_x"]) - 0.5 * sum(READS["front_sight_top_x"])) / s, 1),
        "sight_line_above_bore_mm": round(Z(READS["rear_sight_top_y"] + 3.0), 1),
        "top_line_rise_deg": round(math.degrees(math.atan2(171.0 - 161.0, 345.0 - 80.0)), 2),
        "grip_angle_deg_front_strap": round(math.degrees(math.atan2(440.0 - 395.0, 490.0 - 350.0)), 1),
        "grip_angle_deg_backstrap_groove": round(math.degrees(math.atan2(575.0 - 520.0, 480.0 - 300.0)), 1),
        "trigger_reach_to_backstrap_mm": None,
        "mag_base_length_mm": round((570.0 - 437.0) / s, 1),
        "guard_opening_mm": [round((393.0 - 302.0) / s, 1), round((347.0 - 278.0) / s, 1)],
    }
    # trigger reach: trigger face mid (372, 315) to the backstrap rear edge along the bore direction at that height
    row = side[0]["m"][315 - bL[1]]
    back_x = bL[0] + int(np.nonzero(row)[0].max())
    key["trigger_reach_to_backstrap_mm"] = round((back_x - 372.0) / s, 1)

    meas = {"meta": {"code": "HP01", "name": "Heavy Pistol HP-01", "tool": "WorkFiles/guns/pistol/tools/trace_reference.py",
                     "frame": "F: +X muzzle, +Z up, X = 0 at the crown front, Z = 0 on the bore axis (mm)",
                     "tags": "[S] sheet trace / read, [D] derived, [K] public class figure (unverified offline)"},
            **{k: res[k] for k in ("sheet", "size", "panels", "ruler", "mirror_test", "silhouette_bbox_panel_px",
                                   "backdrop_resid_sd")},
            "scale": scale, "frame_px": {"x_front": round(x_front, 2), "x_rear": round(x_rear, 2),
                                         "bore_y": bore_y, "y_top": round(y_top, 2), "y_bot": round(y_bot, 2)},
            "self_consistency": {"LEFT_vs_RIGHT_mirrored_iou": round(self_iou, 4), "RIGHT_shift_px": round(dxR, 2),
                                 "LEFT_len_vs_TOP_len_px": [round(L_px, 1), xT1 - xT0],
                                 "rail_bars_side_vs_top": [len(bars), READS["rail_bars_top_view"]],
                                 "width_34_check": q34},
            "key_dimensions": key, "serrations": serrations, "rail": rail, "top": top_res,
            "features_F": feats, "reads_px": READS}
    json.dump(meas, open(os.path.join(OUT, "hp01_measured.json"), "w"), indent=1)

    holes = []
    for r in refimg.marching_squares(np.where(side[0]["m"], FL, np.minimum(FL, 0.49)), 0.5):
        if refimg.signed_area(r) < -200:
            h = refimg.dp_simplify(r + np.array([bL[0], bL[1]]), 0.25)
            holes.append({"px": [[round(a, 2), round(b, 2)] for a, b in h], "mm": ring_mm(h, fr)})
    json.dump({"view": "LEFT", "px": [[round(a, 2), round(b, 2)] for a, b in ringL_s],
               "mm": ring_mm(ringL_s, fr), "holes": holes, "frame": meas["meta"]["frame"], "px_per_mm": s},
              open(os.path.join(TR, "LEFT_outline.json"), "w"))
    json.dump({"view": "RIGHT_mirrored", "px": [[round(a, 2), round(b, 2)] for a, b in ringR_s],
               "mm": ring_mm(ringR_s, fr), "shift_px": dxR},
              open(os.path.join(TR, "RIGHT_outline.json"), "w"))
    tr = refimg.dp_simplify(topring, 0.25)
    json.dump({"view": "TOP", "px": [[round(a, 2), round(b, 2)] for a, b in tr],
               "mm_XY": [[round(frT["X"](a), 2), round(frT["Y"](b), 2)] for a, b in tr],
               "Y": "+Y = image down = gun LEFT (camera above, muzzle to image left)"},
              open(os.path.join(TR, "TOP_outline.json"), "w"))

    # TOP mask from the gradient-envelope polygon (replaces the soft-field mask written by stage 1, which fails on TOP)
    mt = refimg.poly_coverage([topring - np.array([bT[0], bT[1]])], top[2]["m"].shape) > 0.5
    Image.fromarray((mt * 255).astype(np.uint8)).save(os.path.join(TR, "TOP_silhouette.png"))

    # ---------------------------------------------------------------- overlay
    im = Image.fromarray(rgb.copy())
    d = ImageDraw.Draw(im)
    d.line([tuple(p) for p in ringL_s] + [tuple(ringL_s[0])], fill=(255, 0, 0), width=1)
    rr = ringR_s.copy()
    rr[:, 0] = 2 * bL[0] + 0  # placeholder replaced below
    # RIGHT outline drawn back in its own panel (un-mirrored)
    bR = side[1]["box"]
    wR = bR[2] - bR[0]
    rr = ringR_s.copy()
    rr[:, 0] = bR[0] + (wR - (rr[:, 0] - bL[0] - dxR))
    d.line([tuple(p) for p in rr] + [tuple(rr[0])], fill=(255, 0, 0), width=1)
    d.line([tuple(p) for p in tr] + [tuple(tr[0])], fill=(255, 0, 0), width=1)
    for k, v in READS.items():
        arr = np.array(v, float)
        if arr.ndim == 2 and arr.shape[1] == 2 and (k.endswith("_box") or k in ("guard_opening", "mag_base")):
            d.rectangle([tuple(arr[0]), tuple(arr[1])], outline=(0, 255, 255))
        elif arr.ndim == 2 and arr.shape[1] == 2 and len(arr) >= 2 and k not in ("trigger_box",):
            d.line([tuple(p) for p in arr], fill=(0, 255, 255), width=1)
    d.line([(bL[0], bore_y), (bL[2], bore_y)], fill=(255, 255, 0), width=1)
    im.save(os.path.join(OUT, "HP01_TRACE_OVERLAY.png"))
    im.crop((0, 120, 624, 520)).resize((1248, 800), Image.LANCZOS).save(os.path.join(SC, "qa_overlay_left.png"))
    print("scale", scale)
    print("self", meas["self_consistency"]["LEFT_vs_RIGHT_mirrored_iou"], "top", top_res["slide_width_mm_sheet"],
          top_res["max_width_mm_sheet"])
    print("key", key)
    print("serr", serrations)
    print("rail", rail)
    return meas
