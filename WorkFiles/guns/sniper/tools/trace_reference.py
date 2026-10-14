"""Trace and measure the SR01 (Sniper Rifle SR-01) reference sheet (References/Guns/Sniper/sniper_sheetA.webp).

    py -3 -B WorkFiles/guns/sniper/tools/trace_reference.py

Written for the sniper from the SMG01 / AR-01 tracers (same helpers: tools/refimg.py, copied unchanged from the SMG).
Regenerates the 2D outline authority:
  WorkFiles/guns/sniper/scratch/crops/*.png      the 4 panels at full resolution (local only)
  WorkFiles/guns/sniper/trace/*.png              masks (silhouettes, sub-masks, LEFT part labels) (local only)
  WorkFiles/guns/sniper/trace/*.json             outlines (sub-pixel marching squares, simplified) in px and in mm
  WorkFiles/guns/sniper/sr01_measured.json       all numbers (scales, panel boxes, agreement, dimensions + uncertainty)
  WorkFiles/guns/sniper/SR01_TRACE_OVERLAY.png   QA overlay (outlines and part labels on the panels)

Sheet layout (found by pixel analysis): four grey panels on white, captions LEFT, RIGHT, TOP, 3/4 FRONT RIGHT. No
ruler. **The side labels are swapped** (verified by handed features, MEASUREMENT_NOTES.md "Sides"): the panel labelled
LEFT shows the gun's RIGHT side (bolt handle and knob, muzzle image-right); the panel labelled RIGHT shows the gun's
LEFT side (muzzle image-left; no knob). The TOP view has the muzzle image-right and the gun's right image-down (the
knob protrudes image-down). The 3/4 view is from the front right (knob visible).

Panel names in this tool are the gun's sides: GR = gun right (sheet "LEFT"), GL = gun left (sheet "RIGHT", mirrored
before tracing so the muzzle is image-right like GR), TOP, Q34.

Frames
  Panel px: (x right, y down), pixel-centre coordinates inside each panel crop (boxes in sr01_measured.json). GL
            coordinates in CONFIG are AFTER mirroring (x' = W - 1 - x).
  Gun mm (frame M): +X toward the muzzle, +Z up, +Y = the gun's LEFT side (GUN_BUILDING_STUDY 5.1). X = 0 at the
            rearmost point of the butt pad, Z = 0 on the bore axis, Y = 0 on the mid-plane. The bore axis: direction
            from the barrel's straight top edge and the scope tube (both horizontal to < 0.1 deg); height = the
            muzzle device centre line.
  Each view gets its own frame (own axis, own X = 0, own scale so its overall length = OVERALL_MM); views are compared
  in mm without fitting.

Only numpy, scipy and Pillow are needed. Hand inputs (seams not on the silhouette, part boxes, face features) are the
CONFIG below, read off gridded 4-8x zooms (tools/gridzoom.py; zooms in scratch/zoom/), +-1 px (+-1.9 mm).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import refimg as R  # noqa: E402

ROOT = HERE.parents[3]
SHEET = ROOT / "References" / "Guns" / "Sniper" / "sniper_sheetA.webp"
OUT = ROOT / "WorkFiles" / "guns" / "sniper"
TRACE = OUT / "trace"
SCRATCH = OUT / "scratch"
CROPS = SCRATCH / "crops"

OVERALL_MM = 1100.0         # ruling R2 (SR01_STUDY.md): the sheet's own anchors (34 mm scope tube, eyepiece, bell, rail
                            # pitch, length of pull, knob) agree on ~0.53 px/mm = ~1100 mm; a .308-class chassis rifle
SCOPE_TUBE_MM = 34.0        # anchor: the commonest long-range tube class (30 / 34 / 35 / 36 mm exist)
RAIL_PITCH = 10.01          # MIL-STD-1913 slot pitch
PANEL_ORDER = ["GR", "GL", "TOP", "Q34"]          # find_panels order: sheet LEFT, RIGHT, TOP, 3/4
SHEET_LABEL = {"GR": "LEFT (labelled; shows the gun's RIGHT)", "GL": "RIGHT (labelled; shows the gun's LEFT)",
               "TOP": "TOP", "Q34": "3/4 FRONT RIGHT"}

# ------------------------------------------------------------------------------------------------ CONFIG
# Coordinates: panel-crop px (pixel centres). GL: after mirroring. Read off scratch/zoom/*.png (+-1 px).
CONFIG = {
    "GR": {
        "min_obj": 25,                       # components smaller than this are dropped (dust, captions none here)
        # sub-masks (first match wins), panel px polygons
        "scope_region": [(158, 150), (400, 150), (400, 222.2), (158, 222.2)],      # above the rail top (rings stand on it)
        "bipod_region": [(384, 261.2), (416, 261.2), (416, 259.2), (456, 259.2), (456, 261.2), (522, 261.2),
                         (522, 300), (384, 300)],                                    # below the fore-end bottom
        "mag_region": [(240.6, 274.7), (293, 274.7), (293, 318), (240.6, 318)],      # below the mag-well lower edge
        # gun parts (first match wins; the sub-masks above are assigned first). Seams read off the 6-8x zooms:
        #   butt pad / pad plate x 48.5; pad plate / butt x 57; butt / chassis (no hinge drawn) x 150;
        #   riser plate y 221-240 on posts to y 247 (x 57-116); bolt shroud x 204-223; receiver x 223-322 (top under
        #   the rail y 227.5, chassis top y 243); rail x 225.5-311, top y 222.2; fore-end front x 466; barrel
        #   x 466-578.5 (flutes x 466-572); device x 578.5-605.5; guard x 197-239 (opening x 202-231, y 271.5-290);
        #   release lever x 237.5-241.5 (y 276-299); grip below y 268 behind the guard
        "regions": [
            ("muzzle_device", [(578.5, 215), (620, 215), (620, 260), (578.5, 260)]),
            ("barrel", [(466, 215), (578.5, 215), (578.5, 258), (466, 258)]),
            ("rail", [(225.5, 218), (311.5, 218), (311.5, 227.6), (225.5, 227.6)]),
            ("bolt_handle", [(207, 244), (226, 244), (226, 263.5), (207, 263.5)]),
            ("bolt_shroud", [(195, 228), (223.5, 228), (223.5, 244), (195, 244)]),
            ("receiver", [(223.5, 225), (322, 225), (322, 243.2), (223.5, 243.2)]),
            ("cheek_riser", [(50, 215), (118, 215), (118, 247.2), (50, 247.2)]),
            ("butt_pad", [(0, 215), (48.5, 215), (48.5, 330), (0, 330)]),
            ("pad_plate", [(48.5, 245), (57, 245), (57, 330), (48.5, 330)]),
            ("trigger", [(206, 271.5), (225, 271.5), (225, 291.5), (206, 291.5)]),
            ("mag_release", [(237.5, 275), (241.5, 275), (241.5, 300), (237.5, 300)]),
            ("trigger_guard", [(196.5, 266.5), (239.5, 266.5), (239.5, 295), (196.5, 295)]),
            ("grip", [(140, 267.5), (205, 267.5), (205, 300), (198, 330), (140, 330)]),
            ("butt", [(57, 245), (150, 245), (150, 330), (57, 330)]),
            ("chassis_forend", [(330, 225), (466.5, 225), (466.5, 275), (330, 275)]),
            ("chassis_centre", [(140, 225), (330, 225), (330, 300), (140, 300)]),
            ("butt", [(48.5, 215), (150, 215), (150, 330), (48.5, 330)]),          # catch-all: comb strip under the riser
            ("chassis_centre", [(140, 200), (470, 200), (470, 330), (140, 330)]),   # catch-all
        ],
        # face features (outline boxes / circles in px, +-1 px)
        "features": {
            "bolt_knob": {"circle": (216.0, 256.0, 6.6)},
            "ejection_port": {"box": (245.0, 230.5, 290.0, 235.5)},
            "forend_slot_1": {"box": (372.5, 240.0, 391.5, 245.0)},
            "forend_slot_2": {"box": (400.5, 240.0, 420.0, 245.0)},
            "forend_slot_3": {"box": (428.5, 240.0, 451.5, 245.0)},
            "forend_lower_band": {"box": (330.0, 251.5, 462.0, 259.5)},
            "ring_rear": {"box": (234.0, 196.5, 246.5, 222.2)},
            "ring_front": {"box": (290.0, 196.5, 301.5, 222.2)},
            "turret_elev": {"box": (257.5, 185.3, 274.5, 198.0)},
            "turret_saddle": {"box": (256.0, 198.0, 277.0, 219.8)},
            "bipod_hub": {"circle": (403.0, 271.0, 9.8)},
            "bipod_mount": {"box": (418.0, 259.2, 452.5, 266.0)},
            "bipod_leg": {"box": (418.0, 266.0, 490.0, 277.0)},
            "bipod_collar": {"box": (487.0, 264.5, 497.0, 279.5)},
            "bipod_foot": {"box": (497.0, 262.0, 512.5, 282.5)},
            "bipod_tension_knob": {"box": (402.0, 276.0, 417.0, 283.5)},
            "riser_plate": {"box": (57.0, 221.0, 116.0, 240.0)},
            "riser_posts": {"box": (60.0, 240.0, 98.0, 247.0)},
            "butt_adjust_knobs": {"circles": [(73.0, 274.0, 4.0), (89.0, 274.0, 4.0)]},
            "pad_screws": {"circles": [(52.5, 252.0, 1.6), (52.5, 275.0, 2.2), (52.5, 293.0, 1.6)]},
            "safety_candidate": {"circle": (227.5, 258.5, 2.0), "note": "small dark head behind/below the bolt root; real-pattern 2-position safety placed here (craft RP)"},
        },
        "trigger_box": (206, 271.5, 226, 291.5),
        "guard_opening_seed": (215, 281),
        "grip_rear_y": (280, 312), "grip_front_y": (295, 316), "grip_x": (140, 206),
    },
    "GL": {
        "min_obj": 25,
        "scope_region": [(158, 150), (400, 150), (400, 222.2), (158, 222.2)],
        "bipod_region": [(384, 261.2), (416, 261.2), (416, 259.2), (456, 259.2), (456, 261.2), (522, 261.2),
                         (522, 300), (384, 300)],
        "mag_region": [(240.6, 274.7), (293, 274.7), (293, 318), (240.6, 318)],
        "guard_opening_seed": (215, 281),
    },
}


# ------------------------------------------------------------------------------------------------ helpers
def load_panels():
    im = np.asarray(Image.open(SHEET).convert("RGB"))
    boxes = R.find_panels(im)
    assert len(boxes) == 4, boxes
    out = {}
    for name, (x0, y0, x1, y1) in zip(PANEL_ORDER, boxes):
        crop = im[y0:y1 + 1, x0:x1 + 1].copy()
        out[name] = {"box": (x0, y0, x1, y1), "rgb": crop[:, ::-1].copy() if name == "GL" else crop}
    return out


def lum_chroma(rgb):
    f = rgb.astype(float)
    return f.mean(axis=2), f.max(axis=2) - f.min(axis=2)


def poly_mask(poly, shape):
    return R.poly_coverage([np.array(poly, float)], shape, ss=4) > 0.5


def side_silhouette(rgb, cfg):
    """Side view: soft field, small specks dropped, every component kept (the bipod is drawn detached), holes filled
    except backdrop-coloured ones (real see-through gaps: guard opening, under the riser, between rings and scope)."""
    L, S = lum_chroma(rgb)
    bg, sd = R.fit_background(L, S)
    F = R.soft_field(L, S, bg)
    band = np.zeros(F.shape, bool)
    band[150:330, 5:-5] = True                         # the gun's band; excludes the panel borders' vignette
    m = R.drop_small((F > 0.5) & band, cfg["min_obj"])
    # the studio floor line (y >= 318) under the pad and grip: drop components that start below y 318
    lab0, n0 = ndi.label(m)
    for i in range(1, n0 + 1):
        yy0 = np.nonzero(lab0 == i)[0]
        if yy0.min() >= 318:
            m &= lab0 != i
    filled = ndi.binary_fill_holes(m)
    lab, n = ndi.label(filled & ~m)
    keep_holes = []
    for i in range(1, n + 1):
        h = lab == i
        a = int(h.sum())
        dL = float(np.mean(L[h] - bg[h]))
        ch = float(np.mean(S[h]))
        if a >= 6 and abs(dL) < 14 and ch < 6:
            keep_holes.append(h)
    sil = filled.copy()
    for h in keep_holes:
        sil &= ~h
    # soft field for sub-pixel contours: inside the silhouette force >= 0.5 where filled holes were closed
    Fc = F.copy()
    Fc[filled & ~m] = 1.0
    for h in keep_holes:
        Fc[h] = 0.0
    Fc[~ndi.binary_dilation(sil, iterations=2)] = 0.0
    return {"F": Fc, "mask": sil, "bg_sd": sd, "holes_kept": len(keep_holes), "L": L, "S": S, "bg": bg}


def top_silhouette(rgb):
    """TOP view: the backdrop above the gun is clean; below it (the gun's right side, image-down) a soft floor shadow
    ramps from ~75 to ~140 levels. Upper edge = soft-field crossing from above; lower edge = the last step of >= 20
    levels met scanning up from the bottom (the shadow ramp changes <= 3 levels/px), sub-pixel at the step's middle."""
    L, S = lum_chroma(rgb)
    bg, sd = R.fit_background(L, S)
    F = R.soft_field(L, S, bg)
    H, W = L.shape
    spans = np.full((W, 2), np.nan)
    for x in range(W):
        col = F[:, x]
        ys = np.nonzero(col[200:330] > 0.5)[0]
        if len(ys) < 3:
            continue
        y0 = 200 + ys[0]
        t = y0 - 1 + (0.5 - col[y0 - 1]) / (col[y0] - col[y0 - 1]) if col[y0] != col[y0 - 1] else y0
        Lc = L[:, x]
        b = None
        for y in range(335, y0, -1):
            if Lc[y] - Lc[y - 1] >= 20:
                b = y - 0.5
                break
        if b is None or b - t < 2:
            continue
        spans[x] = (t, b)
    mask = np.zeros((H, W), bool)
    yy = np.arange(H)[:, None]
    ok = ~np.isnan(spans[:, 0])
    mask[:, ok] = (yy >= spans[ok, 0][None, :]) & (yy <= spans[ok, 1][None, :])
    mask = R.drop_small(mask, 200)          # keeps the butt pad (a 1-column gap separates it from the riser block)
    return {"mask": mask, "spans": spans, "bg_sd": sd}


def q34_silhouette(rgb):
    """3/4 view: stricter luminance threshold (the floor shadow is neutral and 30-60 levels darker), holes filled
    except backdrop-coloured ones, largest component plus the detached bipod feet."""
    L, S = lum_chroma(rgb)
    bg, sd = R.fit_background(L, S)
    F = R.soft_field(L, S, bg, dl=62.0, ds=22.0, db=26.0)
    m = R.drop_small(F > 0.5, 40)
    filled = ndi.binary_fill_holes(m)
    lab, n = ndi.label(filled & ~m)
    sil = filled.copy()
    for i in range(1, n + 1):
        h = lab == i
        if h.sum() >= 8 and abs(float(np.mean(L[h] - bg[h]))) < 14 and float(np.mean(S[h])) < 6:
            sil &= ~h
    return {"mask": sil, "F": np.where(sil, np.maximum(F, 0.51), np.minimum(F, 0.49)), "bg_sd": sd}


def rings_of_mask_field(F, mask, tol=0.25):
    Fm = np.where(ndi.binary_dilation(mask, iterations=1), F, 0.0)
    Fm = np.where(mask, np.maximum(Fm, 0.5001), np.minimum(Fm, 0.4999))
    rings = R.marching_squares(Fm, 0.5)
    out = []
    for r in rings:
        if abs(R.signed_area(r)) < 4:
            continue
        out.append(R.dp_simplify(r, tol))
    return out


def edge_top(F, x, y0, y1, l=0.5):
    c = F[y0:y1, x]
    for i in range(1, len(c)):
        if c[i - 1] <= l < c[i]:
            return y0 + i - 1 + (l - c[i - 1]) / (c[i] - c[i - 1])
    return None


def edge_bot(F, x, y0, y1, l=0.5):
    c = F[y0:y1, x]
    for i in range(len(c) - 1, 0, -1):
        if c[i] <= l < c[i - 1]:
            return y0 + i - 1 + (c[i - 1] - l) / (c[i - 1] - c[i])
    return None


def edge_left(F, y, x0, x1, l=0.5):
    r = F[y, x0:x1]
    for i in range(1, len(r)):
        if r[i - 1] <= l < r[i]:
            return x0 + i - 1 + (l - r[i - 1]) / (r[i] - r[i - 1])
    return None


def edge_right(F, y, x0, x1, l=0.5):
    r = F[y, x0:x1]
    for i in range(len(r) - 1, 0, -1):
        if r[i] <= l < r[i - 1]:
            return x0 + i - 1 + (r[i - 1] - l) / (r[i - 1] - r[i])
    return None


def med(vals):
    v = [a for a in vals if a is not None]
    return float(np.median(v)) if v else None


def rnd(v, n=2):
    if v is None:
        return None
    if isinstance(v, (list, tuple, np.ndarray)):
        return [rnd(a, n) for a in v]
    return round(float(v), n)


# ------------------------------------------------------------------------------------------------ side view
def measure_side(name, P):
    cfg = CONFIG[name]
    rgb = P["rgb"]
    sv = side_silhouette(rgb, cfg)
    F, sil = sv["F"], sv["mask"]
    H, W = sil.shape
    ys, xs = np.nonzero(sil)
    # overall extents (sub-pixel): rearmost butt pad point and muzzle face, on rows through the pad / device
    x_rear = min(edge_left(F, y, 0, 120) or 1e9 for y in range(240, 312))
    x_front = max(edge_right(F, y, 500, W) or -1e9 for y in range(231, 246))
    # bore: device centre line (x 584-600) and barrel near the muzzle (x 545-575)
    dev = [(edge_top(F, x, 215, 262), edge_bot(F, x, 215, 262)) for x in range(584, 601)]
    dev = np.array([d for d in dev if None not in d])
    bar = [(edge_top(F, x, 215, 262), edge_bot(F, x, 215, 262)) for x in range(545, 576)]
    bar = np.array([d for d in bar if None not in d])
    bore_y = float(np.median(dev.mean(axis=1)))
    # axis direction: barrel top edge x 470-575 and scope tube edges (between rings / turret)
    bt = np.array([(x, edge_top(F, x, 215, 262)) for x in range(470, 576)], float)
    bt = bt[~np.isnan(bt).any(axis=1)]
    k_bar, _, rms_bar = R.fit_line(bt[:, 0], bt[:, 1])
    tube_x = [x for x in list(range(224, 233)) + list(range(248, 255)) + list(range(280, 290)) + list(range(304, 318))]
    tt = np.array([(x, edge_top(F, x, 180, 222), edge_bot(F, x, 180, 221)) for x in tube_x], float)
    tt = tt[~np.isnan(tt).any(axis=1)]
    k_tube, _, rms_tube = R.fit_line(tt[:, 0], (tt[:, 1] + tt[:, 2]) / 2)
    tilt_deg = math.degrees(math.atan(0.5 * (k_bar + k_tube)))
    tube_px = float(np.median(tt[:, 2] - tt[:, 1]))
    overall_px = x_front - x_rear
    ppm = overall_px / OVERALL_MM
    def X(x):
        return (x - x_rear) / ppm
    def Z(y):
        return (bore_y - y) / ppm
    # sub-masks
    sub = {}
    remaining = sil.copy()
    for key in ("scope_region", "bipod_region", "mag_region"):
        m = poly_mask(cfg[key], sil.shape) & remaining
        sub[key.replace("_region", "")] = m
        remaining &= ~m
    sub["gun"] = remaining
    res = {"panel": SHEET_LABEL[name], "bg_residual_sd": rnd(sv["bg_sd"]), "holes_kept": sv["holes_kept"],
           "x_rear_px": rnd(x_rear), "x_front_px": rnd(x_front), "overall_px": rnd(overall_px),
           "px_per_mm": round(ppm, 5), "mm_per_px": round(1 / ppm, 4), "bore_y_px": rnd(bore_y),
           "axis_tilt_deg": rnd(tilt_deg, 3), "barrel_top_rms_px": rnd(rms_bar), "scope_axis_rms_px": rnd(rms_tube),
           "scope_tube_px": rnd(tube_px), "scope_tube_mm": rnd(tube_px / ppm, 1)}
    res["ppm_if_tube_34"] = rnd(tube_px / SCOPE_TUBE_MM, 4)
    # ---- barrel and device
    ods = []
    for x0, x1, lab_ in ((470, 480, "barrel_at_forend"), (500, 520, "barrel_mid"), (550, 575, "barrel_at_device"),
                         (584, 600, "device")):
        d = [edge_bot(F, x, 215, 262) - edge_top(F, x, 215, 262) for x in range(x0, x1)]
        ods.append((lab_, float(np.median(d))))
    res["diameters_mm"] = {k: rnd(v / ppm, 1) for k, v in ods}
    res["device_centre_Z"] = rnd(Z(float(np.median(dev.mean(axis=1)))))
    res["barrel_centre_Z_at_device"] = rnd(Z(float(np.median(bar.mean(axis=1)))))
    res["barrel_top_Z"] = rnd(Z(float(np.median(bt[:, 1]))))
    # ---- scope (sub-mask)
    sc = sub["scope"]
    sy, sx = np.nonzero(sc)
    res["scope"] = {"X": rnd([X(sx.min() - 0.5), X(sx.max() + 0.5)], 1), "Z_top": rnd(Z(sy.min() - 0.5), 1),
                    "axis_Z": rnd(Z(float(np.median((tt[:, 1] + tt[:, 2]) / 2))), 1),
                    "tube_dia": rnd(tube_px / ppm, 1)}
    prof = []
    for x in range(int(sx.min()), int(sx.max()) + 1):
        col = np.nonzero(sc[:, x])[0]
        if len(col):
            prof.append((x, col.min(), col.max()))
    prof = np.array(prof, float)
    res["scope"]["max_height_mm"] = rnd((prof[:, 2] - prof[:, 1] + 1).max() / ppm, 1)
    # eyepiece = rear 50 px, objective = front 60 px (outer silhouette height)
    rear = prof[prof[:, 0] < sx.min() + 50]
    front = prof[prof[:, 0] > sx.max() - 50]
    res["scope"]["eyepiece_dia"] = rnd(np.median(rear[:, 2] - rear[:, 1] + 1) / ppm, 1)
    res["scope"]["objective_bell_dia"] = rnd(np.max(front[:, 2] - front[:, 1] + 1) / ppm, 1)
    # ---- magazine
    mg = sub["mag"]
    my, mx = np.nonzero(mg)
    rows = []
    for y in range(int(my.min()) + 3, int(my.max()) - 3):
        r_ = np.nonzero(mg[y])[0]
        if len(r_) > 10:
            rows.append((y, edge_left(F, y, int(r_.min()) - 3, int(r_.min()) + 3) or r_.min(),
                         edge_right(F, y, int(r_.max()) - 3, int(r_.max()) + 4) or r_.max()))
    rows = np.array(rows, float)
    kr, cr, rr = R.fit_line(rows[:, 0], rows[:, 1])
    kf, cf, rf = R.fit_line(rows[:, 0], rows[:, 2])
    res["magazine"] = {"X_rear": rnd(X(np.median(rows[:, 1])), 1), "X_front": rnd(X(np.median(rows[:, 2])), 1),
                       "Z_top_cut": rnd(Z(274.7), 1), "Z_bottom": rnd(Z(my.max() + 0.5), 1),
                       "foreaft": rnd(np.median(rows[:, 2] - rows[:, 1]) / ppm, 1),
                       "rake_deg_rear_edge": rnd(math.degrees(math.atan(kr)), 2),
                       "rake_deg_front_edge": rnd(math.degrees(math.atan(kf)), 2),
                       "edge_fit_rms_px": rnd([rr, rf])}
    # ---- bipod (sub-mask)
    bp = sub["bipod"]
    by, bx = np.nonzero(bp)
    res["bipod_folded"] = {"X": rnd([X(bx.min() - 0.5), X(bx.max() + 0.5)], 1),
                           "Z": rnd([Z(by.max() + 0.5), Z(by.min() - 0.5)], 1),
                           "area_px": int(bp.sum())}
    # ---- trigger, guard, LOP (GR only: hand boxes)
    if name == "GR":
        x0, y0, x1, y1 = cfg["trigger_box"]
        L = sv["L"]
        trig = (L[int(y0):int(y1), int(x0):int(x1)] < 70)
        ty, tx = np.nonzero(trig)
        tx = tx + int(x0)
        ty = ty + int(y0)
        mid = (ty >= 277) & (ty <= 284)
        x_face = float(tx[mid].max()) + 0.5 if mid.any() else None
        res["trigger"] = {"X_range": rnd([X(tx.min() - 0.5), X(tx.max() + 0.5)], 1),
                          "Z_range": rnd([Z(ty.max() + 0.5), Z(ty.min() - 0.5)], 1),
                          "face_X_at_mid": rnd(X(x_face), 1) if x_face else None}
        res["length_of_pull_mm"] = rnd(X(x_face), 1) if x_face else None
        # grip straps
        gx0, gx1 = cfg["grip_x"]
        rr_ = []
        for y in range(*cfg["grip_rear_y"]):
            e = edge_left(F, y, gx0, gx1)
            if e:
                rr_.append((y, e))
        ff_ = []
        for y in range(*cfg["grip_front_y"]):
            e = edge_right(F, y, gx0, gx1)
            if e:
                ff_.append((y, e))
        rr_, ff_ = np.array(rr_), np.array(ff_)
        kgr, _, rgr = R.fit_line(rr_[:, 0], rr_[:, 1])
        kgf, _, rgf = R.fit_line(ff_[:, 0], ff_[:, 1])
        gb = max(edge_bot(F, x, 300, 330) or 0 for x in range(150, 195))
        res["grip"] = {"rear_strap_deg_from_vertical": rnd(-math.degrees(math.atan(kgr)), 1),
                       "front_strap_deg_from_vertical": rnd(-math.degrees(math.atan(kgf)), 1),
                       "fit_rms_px": rnd([rgr, rgf]), "bottom_Z": rnd(Z(gb), 1),
                       "foreaft_at_Z_mid": None}
        # fore-aft width perpendicular to the mean axis at y 300
        e1 = edge_left(F, 300, gx0, gx1)
        e2 = edge_right(F, 300, gx0, gx1)
        ang = math.radians(0.5 * (res["grip"]["rear_strap_deg_from_vertical"] + res["grip"]["front_strap_deg_from_vertical"]))
        res["grip"]["foreaft_perp_at_y300"] = rnd((e2 - e1) * math.cos(ang) / ppm, 1)
        res["grip"]["mean_axis_deg_from_vertical"] = rnd(math.degrees(ang), 1)
        # web line: where the grip's rear strap meets the chassis bottom (y ~268) and the front meets the guard
        # guard opening (hole kept)
        lab, n = ndi.label(~sil)
        gs = cfg["guard_opening_seed"]
        op = lab == lab[int(gs[1]), int(gs[0])]
        oy, ox = np.nonzero(op)
        res["guard_opening"] = {"X": rnd([X(ox.min() - 0.5), X(ox.max() + 0.5)], 1),
                                "Z": rnd([Z(oy.max() + 0.5), Z(oy.min() - 0.5)], 1),
                                "length": rnd((ox.max() - ox.min() + 1) / ppm, 1),
                                "height": rnd((oy.max() - oy.min() + 1) / ppm, 1)}
        # chassis top line over the action (x 160-200) and the rail top (tooth tops x 247-290)
        res["chassis_top_Z_x160_200"] = rnd(Z(med([edge_top(F, x, 238, 250) for x in range(165, 200)])), 1)
        res["forend"] = {"top_Z": rnd(Z(med([edge_top(F, x, 222, 236) for x in range(335, 455)])), 1),
                         "bottom_Z": rnd(Z(med([edge_bot(F, x, 245, 275) for x in range(390, 440)])), 1),
                         "front_X": rnd(X(max(edge_right(F, y, 440, 480) or 0 for y in range(250, 258))), 1)}
        res["rail"] = {"top_Z": rnd(Z(222.2), 1), "X": rnd([X(225.5), X(311.0)], 1),
                       "drawn_pitch_px": 5.64, "drawn_pitch_mm": rnd(5.64 / ppm, 2),
                       "note": "tooth dips on row y 222 at x 247.5..287 (8 dips, 7 pitches); RIGHT reads 5.0-5.5 (noisier)"}
        res["butt_pad"] = {"X": rnd([0.0, X(48.5)], 1),
                           "Z": rnd([Z(max(edge_bot(F, x, 300, 330) or 0 for x in range(25, 46))),
                                     Z(min(edge_top(F, x, 220, 240) or 999 for x in range(25, 46)))], 1)}
        res["cheek_riser"] = {"X": rnd([X(57.0), X(116.0)], 1),
                              "Z_top": rnd(Z(min(edge_top(F, x, 214, 232) or 999 for x in range(62, 112))), 1),
                              "plate_Z_bottom": rnd(Z(240.0), 1), "stock_top_Z": rnd(Z(247.0), 1)}
        res["features_mm"] = {}
        for k, f in cfg["features"].items():
            if "circle" in f:
                cx, cy, r = f["circle"]
                res["features_mm"][k] = {"centre_XZ": rnd([X(cx), Z(cy)], 1), "dia": rnd(2 * r / ppm, 1)}
            elif "circles" in f:
                res["features_mm"][k] = [{"centre_XZ": rnd([X(cx), Z(cy)], 1), "dia": rnd(2 * r / ppm, 1)}
                                         for cx, cy, r in f["circles"]]
            else:
                a, b, c, d = f["box"]
                res["features_mm"][k] = {"X": rnd([X(a), X(c)], 1), "Z": rnd([Z(d), Z(b)], 1)}
            if "note" in f:
                res["features_mm"][k]["note"] = f["note"]
    res["height_total_mm"] = rnd((ys.max() - ys.min() + 1) / ppm, 1)
    gy = np.nonzero(sub["gun"] | sub["mag"])[0]
    res["height_without_scope_mm"] = rnd((gy.max() - gy.min() + 1) / ppm, 1)
    return res, sv, sub, (X, Z, ppm, x_rear, bore_y)


# ------------------------------------------------------------------------------------------------ parts (GR)
def label_parts(sil, sub, F):
    cfg = CONFIG["GR"]
    labels = {}
    taken = np.zeros_like(sil)
    for key in ("scope", "bipod", "mag"):
        labels["magazine" if key == "mag" else key] = sub[key]
        taken |= sub[key]
    for name, poly in cfg["regions"]:
        m = poly_mask(poly, sil.shape) & sil & ~taken
        labels[name] = labels.get(name, np.zeros_like(sil)) | m
        taken |= m
    labels["unassigned"] = sil & ~taken
    return labels


def to_mm_rings(rings, X, Z):
    return [[[round(X(x), 2), round(Z(y), 2)] for x, y in r] for r in rings]


def ring_json(rings):
    return [[[round(float(x), 2), round(float(y), 2)] for x, y in r] for r in rings]


# ------------------------------------------------------------------------------------------------ main
def main():
    for d in (TRACE, SCRATCH, CROPS):
        d.mkdir(parents=True, exist_ok=True)
    panels = load_panels()
    for k, P in panels.items():
        Image.fromarray(P["rgb"]).save(CROPS / f"{k}.png")
    meas = {"meta": {"tool": "WorkFiles/guns/sniper/tools/trace_reference.py", "sheet": "References/Guns/Sniper/sniper_sheetA.webp",
                     "sheet_size": list(np.asarray(Image.open(SHEET)).shape[:2]), "overall_mm": OVERALL_MM,
                     "frame": "M: +X muzzle, +Z up, +Y gun left; X 0 = butt pad rear, Z 0 = bore (device centre line)",
                     "uncertainty": "silhouette edges +-0.4 px, hand seams/boxes +-1 px; 1 px = %.2f mm at the chosen scale" % (1 / (584.0 / OVERALL_MM))},
            "panels": {k: {"sheet_label": SHEET_LABEL[k], "box_xyxy": list(P["box"]), "mirrored": k == "GL"}
                       for k, P in panels.items()}}
    side = {}
    for name in ("GR", "GL"):
        res, sv, sub, fr = measure_side(name, panels[name])
        side[name] = (res, sv, sub, fr)
        meas[name] = res
    # ---------------- side outlines + parts
    resR, svR, subR, (XR, ZR, ppmR, xr0R, byR) = side["GR"]
    labels = label_parts(svR["mask"], subR, svR["F"])
    out_GR = {"view": "GR (sheet LEFT): the gun's right side, muzzle image-right", "frame": "px panel crop; mm frame M (X, Z)",
              "px_per_mm": resR["px_per_mm"], "x_rear_px": resR["x_rear_px"], "bore_y_px": resR["bore_y_px"]}
    rings = rings_of_mask_field(svR["F"], svR["mask"])
    out_GR["silhouette"] = {"px": ring_json(rings), "mm": to_mm_rings(rings, XR, ZR)}
    for key, m in (("scope", subR["scope"]), ("bipod_folded", subR["bipod"]), ("magazine", subR["mag"]), ("gun_body", subR["gun"])):
        rr = rings_of_mask_field(svR["F"], m)
        out_GR[key] = {"px": ring_json(rr), "mm": to_mm_rings(rr, XR, ZR), "area_px": int(m.sum())}
    out_GR["parts"] = {}
    lab_img = np.zeros(svR["mask"].shape, np.uint8)
    part_names = [k for k in labels if k != "unassigned"]
    for i, k in enumerate(part_names, 1):
        m = labels[k]
        lab_img[m] = i
        if not m.any():
            continue
        rr = rings_of_mask_field(svR["F"], m, tol=0.35)
        yy, xx = np.nonzero(m)
        out_GR["parts"][k] = {"index": i, "area_px": int(m.sum()),
                              "box_mm": {"X": rnd([XR(xx.min() - 0.5), XR(xx.max() + 0.5)], 1),
                                         "Z": rnd([ZR(yy.max() + 0.5), ZR(yy.min() - 0.5)], 1)},
                              "px": ring_json(rr), "mm": to_mm_rings(rr, XR, ZR)}
    out_GR["unassigned_px"] = int(labels["unassigned"].sum())
    out_GR["features_mm"] = resR.get("features_mm", {})
    (TRACE / "GR_outline.json").write_text(json.dumps(out_GR), encoding="utf-8")
    Image.fromarray((svR["mask"] * 255).astype(np.uint8)).save(TRACE / "GR_silhouette.png")
    Image.fromarray(lab_img).save(TRACE / "GR_parts_index.png")
    resL, svL, subL, (XL, ZL, ppmL, xr0L, byL) = side["GL"]
    ringsL = rings_of_mask_field(svL["F"], svL["mask"])
    out_GL = {"view": "GL (sheet RIGHT, mirrored): the gun's left side, muzzle image-right after mirroring",
              "px_per_mm": resL["px_per_mm"], "x_rear_px": resL["x_rear_px"], "bore_y_px": resL["bore_y_px"],
              "silhouette": {"px": ring_json(ringsL), "mm": to_mm_rings(ringsL, XL, ZL)}}
    for key, m in (("scope", subL["scope"]), ("bipod_folded", subL["bipod"]), ("magazine", subL["mag"]), ("gun_body", subL["gun"])):
        rr = rings_of_mask_field(svL["F"], m)
        out_GL[key] = {"px": ring_json(rr), "mm": to_mm_rings(rr, XL, ZL), "area_px": int(m.sum())}
    (TRACE / "GL_outline.json").write_text(json.dumps(out_GL), encoding="utf-8")
    Image.fromarray((svL["mask"] * 255).astype(np.uint8)).save(TRACE / "GL_silhouette.png")
    # ---------------- view agreement GR vs GL, in mm (no fitting): rasterise both at 1 mm/px
    def raster_mm(rings_mm, x0=-20, x1=1120, z0=-200, z1=140, s=1.0):
        Wd, Hd = int((x1 - x0) / s), int((z1 - z0) / s)
        P = [np.array([[(x - x0) / s, (z1 - z) / s] for x, z in r]) for r in rings_mm]
        return R.rings_to_mask(P, (Hd, Wd), ss=2)
    mGR = raster_mm(out_GR["silhouette"]["mm"])
    mGL = raster_mm(out_GL["silhouette"]["mm"])
    agree = {"silhouette_iou": rnd(R.iou(mGR, mGL), 3)}
    for key in ("scope", "bipod_folded", "magazine", "gun_body"):
        agree[key + "_iou"] = rnd(R.iou(raster_mm(out_GR[key]["mm"]), raster_mm(out_GL[key]["mm"])), 3)
    dt_a = ndi.distance_transform_edt(~(mGR ^ ndi.binary_erosion(mGR)))
    edgeL = mGL ^ ndi.binary_erosion(mGL)
    d = dt_a[edgeL]
    agree["boundary_distance_mm_GL_to_GR"] = {"median": rnd(np.median(d), 2), "p90": rnd(np.percentile(d, 90), 2),
                                             "p99": rnd(np.percentile(d, 99), 2)}
    agree["overall_px_ratio_GL_over_GR"] = rnd(resL["overall_px"] / resR["overall_px"], 4)
    meas["agreement_GR_GL"] = agree
    # ---------------- TOP
    tv = top_silhouette(panels["TOP"]["rgb"])
    spans = tv["spans"]
    okx = np.nonzero(~np.isnan(spans[:, 0]))[0]
    xt0 = float(okx.min()) - 0.5
    xt1 = float(okx.max()) + 0.5
    # centre line: exposed barrel ahead of the folded bipod feet + device, x 524-600 (the feet and legs splay beside
    # the barrel at x 460-520 and would bias the centre)
    bar = np.array([(x, 0.5 * (spans[x, 0] + spans[x, 1])) for x in range(524, 601) if not np.isnan(spans[x, 0])])
    kc, cc, rc = R.fit_line(bar[:, 0], bar[:, 1])
    ppmT = (xt1 - xt0) / OVERALL_MM
    def XT(x):
        return (x - xt0) / ppmT
    def YT(x, y):
        return ((kc * x + cc) - y) / ppmT                        # + = image-up = gun LEFT
    prof = []
    for x in okx:
        prof.append([round(XT(x), 1), round(YT(x, spans[x, 0]), 2), round(YT(x, spans[x, 1]), 2)])
    prof = np.array(prof)
    def wspan(xa, xb):
        sel = (prof[:, 0] >= xa) & (prof[:, 0] <= xb)
        return rnd([np.median(prof[sel, 1]), np.median(prof[sel, 2]), np.median(prof[sel, 1] - prof[sel, 2])], 1)
    def wmax(xa, xb):
        sel = (prof[:, 0] >= xa) & (prof[:, 0] <= xb)
        return rnd([prof[sel, 1].max(), prof[sel, 2].min(), (prof[sel, 1] - prof[sel, 2]).max()], 1)
    top = {"panel": "TOP", "x_rear_px": rnd(xt0), "x_front_px": rnd(xt1), "overall_px": rnd(xt1 - xt0),
           "px_per_mm": round(ppmT, 5), "centre_line_tilt_deg": rnd(math.degrees(math.atan(kc)), 3),
           "centre_line_fit_rms_px": rnd(rc), "bg_residual_sd": rnd(tv["bg_sd"]),
           "rule": "Y left (+) / right (-) edges and width; median over the X window unless 'max'",
           "widths_mm_Yleft_Yright_W": {}}
    win = {"butt_pad": (2, 50, "median"), "cheek_riser_block": (75, 175, "median"), "stock_neck": (215, 245, "median"),
           "action_with_bolt_shroud": (330, 360, "median"), "bolt_knob": (330, 375, "max"),
           "chassis_at_mag": (420, 500, "median"), "forend": (600, 800, "median"), "forend_front": (800, 845, "median"),
           "barrel_exposed": (880, 900, "median"), "bipod_feet_zone": (885, 960, "max"),
           "barrel_ahead_of_feet": (990, 1060, "median"), "muzzle_device": (1068, 1095, "median"),
           "scope_turret_zone": (440, 480, "max"), "scope_objective": (580, 640, "max")}
    for k, (a, b, how) in win.items():
        top["widths_mm_Yleft_Yright_W"][k] = (wmax if how == "max" else wspan)(a, b) + [how, [a, b]]
    meas["TOP"] = top
    out_T = {"view": "TOP: muzzle image-right, the gun's right image-down; Y + = gun left", "px_per_mm": round(ppmT, 5),
             "width_profile_mm_X_Yleft_Yright": prof.tolist()}
    rT = rings_of_mask_field(np.where(tv["mask"], 1.0, 0.0), tv["mask"])
    out_T["silhouette"] = {"px": ring_json(rT), "mm": [[[round(XT(x), 2), round(YT(x, y), 2)] for x, y in r] for r in rT]}
    (TRACE / "TOP_outline.json").write_text(json.dumps(out_T), encoding="utf-8")
    Image.fromarray((tv["mask"] * 255).astype(np.uint8)).save(TRACE / "TOP_silhouette.png")
    # ---------------- Q34
    qv = q34_silhouette(panels["Q34"]["rgb"])
    rQ = rings_of_mask_field(qv["F"], qv["mask"])
    (TRACE / "Q34_outline.json").write_text(json.dumps({"view": "3/4 FRONT RIGHT (perspective; px only)",
                                                       "silhouette_px": ring_json(rQ),
                                                       "area_px": int(qv["mask"].sum()),
                                                       "note": "for the camera-solved L2 gate at form; the floor contact shadows under the feet, mag and grip are partly inside (threshold dl 62)"}),
                                            encoding="utf-8")
    Image.fromarray((qv["mask"] * 255).astype(np.uint8)).save(TRACE / "Q34_silhouette.png")
    meas["Q34"] = {"area_px": int(qv["mask"].sum()), "bg_residual_sd": rnd(qv["bg_sd"])}
    # ---------------- cross-view
    meas["cross_view"] = {
        "overall_px": {"GR": resR["overall_px"], "GL": resL["overall_px"], "TOP": top["overall_px"]},
        "TOP_over_GR": rnd(top["overall_px"] / resR["overall_px"], 4),
        "device_dia_side_vs_top_mm": [resR["diameters_mm"]["device"], top["widths_mm_Yleft_Yright_W"]["muzzle_device"][2]],
        "barrel_dia_side_vs_top_mm": [resR["diameters_mm"]["barrel_at_device"], top["widths_mm_Yleft_Yright_W"]["barrel_ahead_of_feet"][2]],
    }
    meas["scale_anchors"] = scale_anchors(resR, top)
    (OUT / "sr01_measured.json").write_text(json.dumps(meas, indent=1), encoding="utf-8")
    overlay(panels, svR, svL, tv, qv, labels, part_names, rings, ringsL, rT, rQ)
    print(json.dumps({"GR_ppm": resR["px_per_mm"], "GL_ppm": resL["px_per_mm"], "TOP_ppm": top["px_per_mm"],
                      "iou_GR_GL": agree, "unassigned_px": out_GR["unassigned_px"]}, indent=1))


def scale_anchors(resR, top):
    """Each anchor's implied overall length = OVERALL_MM x (real / sheet-at-OVERALL)."""
    a = []
    def add(name, sheet_mm, real_lo, real_hi, src):
        mid = 0.5 * (real_lo + real_hi)
        a.append({"anchor": name, "sheet_mm_at_overall": sheet_mm, "real_range_mm": [real_lo, real_hi],
                  "implied_overall_mm": [round(OVERALL_MM * real_lo / sheet_mm), round(OVERALL_MM * real_hi / sheet_mm)],
                  "implied_overall_mid": round(OVERALL_MM * mid / sheet_mm), "source": src})
    add("scope main tube", resR["scope_tube_mm"], 34.0, 34.0, "34 mm tube class (30 mm would give 970 mm, 36 mm 1165 mm)")
    add("scope eyepiece", resR["scope"]["eyepiece_dia"], 42.0, 46.0, "long-range eyepieces 42-46 mm")
    add("scope objective bell", resR["scope"]["objective_bell_dia"], 62.0, 68.0, "56 mm objective, bell OD 62-68 mm")
    add("rail slot pitch (drawn)", resR["rail"]["drawn_pitch_mm"], 10.01, 10.01, "MIL-STD-1913")
    add("length of pull", resR["length_of_pull_mm"], 330.0, 370.0, "precision chassis LOP 13.0-14.5 in")
    add("bolt knob", resR["features_mm"]["bolt_knob"]["dia"], 20.0, 25.0, "tactical bolt knobs 20-25 mm")
    add("magazine fore-aft", resR["magazine"]["foreaft"], 80.0, 88.0, ".308-class detachable box, body + ribs")
    add("muzzle device OD", resR["diameters_mm"]["device"], 30.0, 36.0, "linear compensator / brake class")
    vals = [x["implied_overall_mid"] for x in a]
    return {"anchors": a, "median_implied_overall_mm": int(np.median(vals)),
            "spread_mm": [int(min(vals)), int(max(vals))]}


def overlay(panels, svR, svL, tv, qv, labels, part_names, rings, ringsL, rT, rQ):
    pal = [(230, 25, 75), (60, 180, 75), (255, 225, 25), (0, 130, 200), (245, 130, 48), (145, 30, 180), (70, 240, 240),
           (240, 50, 230), (210, 245, 60), (250, 190, 212), (0, 128, 128), (220, 190, 255), (170, 110, 40),
           (255, 250, 200), (128, 0, 0), (170, 255, 195), (128, 128, 0), (255, 215, 180), (0, 0, 128), (128, 128, 128)]
    tiles = []
    S = 3
    def crop_band(img, y0, y1):
        return img.crop((0, y0, img.width, y1))
    # tile 1: GR with parts tinted
    base = panels["GR"]["rgb"].astype(float)
    tint = base.copy()
    for i, k in enumerate(part_names):
        m = labels[k]
        c = np.array(pal[i % len(pal)], float)
        tint[m] = 0.55 * base[m] + 0.45 * c
    im = Image.fromarray(tint.astype(np.uint8)).resize((base.shape[1] * S, base.shape[0] * S), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    for r in rings:
        d.line([(x * S + S / 2, y * S + S / 2) for x, y in np.vstack([r, r[:1]])], fill=(0, 255, 255), width=1)
    try:
        f = ImageFont.truetype("arial.ttf", 13)
    except OSError:
        f = ImageFont.load_default()
    for i, k in enumerate(part_names):
        m = labels[k]
        if m.any():
            yy, xx = np.nonzero(m)
            d.text((xx.mean() * S - 10, yy.mean() * S - 6), k, fill=(255, 255, 255), font=f, stroke_width=2,
                   stroke_fill=(0, 0, 0))
    tiles.append(crop_band(im, 175 * S, 335 * S))
    # tile 2: GL with GR silhouette (shifted to GL frame by x_rear and bore) in cyan
    im2 = Image.fromarray(panels["GL"]["rgb"]).resize((620 * S, panels["GL"]["rgb"].shape[0] * S), Image.LANCZOS)
    d2 = ImageDraw.Draw(im2)
    for r in ringsL:
        d2.line([(x * S + S / 2, y * S + S / 2) for x, y in np.vstack([r, r[:1]])], fill=(255, 80, 80), width=1)
    for r in rings:
        d2.line([(x * S + S / 2, y * S + S / 2) for x, y in np.vstack([r, r[:1]])], fill=(0, 255, 255), width=1)
    d2.text((10, 180 * S), "GL (sheet RIGHT, mirrored) red; GR silhouette cyan (no fit)", fill=(255, 255, 0), font=f)
    tiles.append(crop_band(im2, 175 * S, 335 * S))
    im3 = Image.fromarray(panels["TOP"]["rgb"]).resize((panels["TOP"]["rgb"].shape[1] * S, panels["TOP"]["rgb"].shape[0] * S), Image.LANCZOS)
    d3 = ImageDraw.Draw(im3)
    for r in rT:
        d3.line([(x * S + S / 2, y * S + S / 2) for x, y in np.vstack([r, r[:1]])], fill=(255, 0, 255), width=1)
    tiles.append(crop_band(im3, 215 * S, 310 * S))
    im4 = Image.fromarray(panels["Q34"]["rgb"]).resize((panels["Q34"]["rgb"].shape[1] * S, panels["Q34"]["rgb"].shape[0] * S), Image.LANCZOS)
    d4 = ImageDraw.Draw(im4)
    for r in rQ:
        d4.line([(x * S + S / 2, y * S + S / 2) for x, y in np.vstack([r, r[:1]])], fill=(0, 255, 0), width=1)
    tiles.append(crop_band(im4, 100 * S, 400 * S))
    Wt = max(t.width for t in tiles)
    Ht = sum(t.height for t in tiles)
    canvas = Image.new("RGB", (Wt, Ht), (20, 20, 20))
    y = 0
    for t in tiles:
        canvas.paste(t, (0, y))
        y += t.height
    canvas.save(OUT / "SR01_TRACE_OVERLAY.png")


if __name__ == "__main__":
    main()
