"""Silhouette gates for the AR-01 (plain Python): L1 (blockout) and the silhouette parts of L2 / L3.

    py -3 -B Scripts/guns/rifle/rifle_silhouette.py --npz <tris.npz> --stage blockout|form [--out-tag x]

Views (frame M -> panel px with the trace's own mapping):
  side   LEFT-labelled panel (= true right side), the authority for X/Z
  top    TOP panel (image up = gun left); excluded zones per spec gates_look.excluded_zones: the left-side bumps
         (X 236-295, 353-462 beyond the cover) and the right-side knob the sheet draws 25 mm too far forward
         (X 466-486), plus our own handle at its side-view X (444-458), which the TOP panel shows elsewhere
  left   RIGHT-labelled panel mirrored (= true left side), cross-check (sheet self-IoU 0.893)
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rifle_common import SPEC, TRACE, GATES, SCRATCH, SHEET, REVIEW, RENDERS  # noqa: E402
from gunlib import compare as C  # noqa: E402


# trace part key -> our object names (per-part L2 labels)
PART_MAP = {"receiver": ["receiver", "rear_trunnion", "rivets", "receiver_rails", "bolt_carrier", "selector"],
            "dust_cover": ["dust_cover", "recoil_spring_button"],
            "rear_sight": ["rear_sight_block", "rear_sight_leaf", "rear_sight_slider", "handguard_retainer"],
            "gas_tube_rear_cap": ["gas_tube_rear_cap"], "handguard_upper": ["upper_handguard"],
            "handguard_lower": ["lower_handguard"], "handguard_front_band": ["handguard_front_band"],
            "gas_tube": ["gas_tube", "gas_piston"], "gas_block": ["gas_block"], "barrel": ["barrel"],
            "cleaning_rod": ["cleaning_rod"], "front_sight_block": ["front_sight_block", "front_sight_post"],
            "muzzle_brake": ["muzzle_brake"], "trigger": ["trigger"], "trigger_guard": ["trigger_guard"],
            "mag_catch": ["mag_catch"], "pistol_grip": ["pistol_grip"], "stock": ["buttstock", "stock_hardware", "rear_tang"],
            "butt_plate": ["butt_plate", "butt_screws"],
            "sling_swivel_rear": ["sling_swivel_base", "sling_swivel_loop"],
            "magazine": ["magazine", "magazine_floor_plate"]}


def panel_rgb(view):
    j = json.loads((TRACE / f"{view}_outline.json").read_text())
    x0, y0, x1, y1 = j["panel_box_sheet_px"]
    a = np.asarray(Image.open(SHEET).convert("RGB"))[y0:y1 + 1, x0:x1 + 1]
    return a[:, ::-1] if j.get("mirrored") else a


def zone_mask(fr, polys_mm, shape):
    return C.poly_cov([fr.px(np.asarray(p, float)) for p in polys_mm], shape) > 0.0


def top_exclusions():
    return [
        [[230, 21.9], [300, 21.9], [300, 45], [230, 45]],          # left bump X 236-295 (not real)
        [[348, 21.9], [468, 21.9], [468, 45], [348, 45]],          # left plate X 353-462 (not real)
        [[462, -22.0], [490, -22.0], [490, -45], [462, -45]],      # handle knob drawn 25 mm forward
        [[440, -22.0], [462, -22.0], [462, -45], [440, -45]],      # our handle at the side-view X
    ]


def run(npz, stage, tag=""):
    D = np.load(npz)
    V, T, lab, names = D["V"], D["T"], D["lab"], [str(n) for n in D["names"]]
    res = {"stage": stage, "npz": str(Path(npz).name), "triangles": int(len(T)), "views": {}}
    out_dir = REVIEW / stage
    out_dir.mkdir(parents=True, exist_ok=True)

    # ---------------- side (authority)
    frL, jL = C.load_trace(TRACE, "LEFT")
    ref = C.rings_mask([r["px"] for r in jL["silhouette"]], frL.shape)
    cov = C.raster_tris(C.side_px(frL, V), T, frL.shape)
    ours = cov > 0.5
    i0 = C.iou(ours, ref)
    p, i1, ours_fit = C.similarity_fit(lambda: (C.side_px(frL, V), T), ref)
    cd = C.contour_distance(ours, ref)
    res["views"]["side"] = {"iou_identity": round(i0, 4), "iou_fit": round(i1, 4), "fit_params_s_rotdeg_tx_ty": p,
                            "contour_px": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in cd.items()},
                            "ours_px": int(ours.sum()), "ref_px": int(ref.sum())}
    C.overlay(panel_rgb("LEFT"), ours, ref, out_dir / f"side_overlay{tag}.png")
    C.diff_image(ours, ref, out_dir / f"side_diff{tag}.png")
    # magazine-only and no-magazine
    magk = names.index("magazine") if "magazine" in names else None
    if magk is not None:
        selm = lab == magk
        refm = C.rings_mask([r["px"] for r in jL["magazine"]], frL.shape)
        om = C.raster_tris(C.side_px(frL, V), T[selm], frL.shape) > 0.5
        res["views"]["side"]["magazine_iou"] = round(C.iou(om, refm), 4)
        refn = C.rings_mask([r["px"] for r in jL["rifle_without_magazine"]], frL.shape)
        on = C.raster_tris(C.side_px(frL, V), T[~selm], frL.shape) > 0.5
        res["views"]["side"]["rifle_without_mag_iou"] = round(C.iou(on, refn), 4)

    # ---------------- per part, visible labels (painter's order from -Y) vs the trace's part masks
    keys = list(PART_MAP)
    remap = np.full(len(names), -1)
    for ki, k in enumerate(keys):
        for nm in PART_MAP[k]:
            if nm in names:
                remap[names.index(nm)] = ki
    tl = remap[lab]
    # label conventions of the trace: the guard's top flange belongs to the receiver label (spec receiver
    # bottom_Z_note); the catch housing cheeks to the mag_catch label
    tc = V[T].mean(axis=1)
    if "trigger_guard" in names:
        g = lab == names.index("trigger_guard")
        tl[g & (tc[:, 2] > -34.85) & (tc[:, 0] < 368.0)] = keys.index("receiver")
        # (-54.5: the catch housing cheeks reach the paddle's top at Z -53.87 since detail round 2; -52.0 was the old cheek
        # bottom, not a property of the trace: review/detail/trigger_guard/spec_proposal.json, accepted at integration)
        tl[g & (tc[:, 0] > 355.3) & (tc[:, 2] > -54.5) & (tc[:, 2] <= -34.85)] = keys.index("mag_catch")
    if "bolt_carrier" in names:
        tl[(lab == names.index("bolt_carrier")) & (tc[:, 2] > 10.6)] = keys.index("dust_cover")
    ok = tl >= 0
    covs = C.raster_labels(C.side_px(frL, V), T[ok], V[:, 1], tl[ok], frL.shape, nlab=len(keys))
    gl = SPEC.gates["L2_parts"]
    thr = gl["area_threshold_px"]
    parts_res = {}
    for ki, k in enumerate(keys):
        if k not in jL["parts"]:
            continue
        refp = C.rings_mask([r["px"] for r in jL["parts"][k]], frL.shape)
        op = covs[ki] > 0.5
        area = float(gl["areas_px"].get(k, refp.sum()))
        cdp = C.contour_distance(op, refp)
        e = {"area_px": round(area, 1), "iou": round(C.iou(op, refp), 4),
             "contour_p95_px": None if cdp["p95"] is None else round(cdp["p95"], 3),
             "contour_max_px": None if cdp["max"] is None else round(cdp["max"], 3)}
        if area >= thr:
            e["rule"] = "IoU >= 0.95"
            e["pass"] = e["iou"] >= 0.95
        else:
            # thin parts: the OUTER contour (holes filled in both masks). The trace records a part's holes only where
            # the background shows through at 1.2 mm/px; a ring's shaded interior (the rear swivel's D-ring) is traced
            # solid, so comparing our open interior's edge against no edge would test the tracer, not the shape.
            # The unfilled numbers are kept beside it.
            opf, refpf = ndi.binary_fill_holes(op), ndi.binary_fill_holes(refp)
            cdf = C.contour_distance(opf, refpf)
            e["contour_unfilled_p95_px"], e["contour_unfilled_max_px"] = e["contour_p95_px"], e["contour_max_px"]
            e["contour_p95_px"] = None if cdf["p95"] is None else round(cdf["p95"], 3)
            e["contour_max_px"] = None if cdf["max"] is None else round(cdf["max"], 3)
            e["iou_filled"] = round(C.iou(opf, refpf), 4)
            e["rule"] = "outer contour (holes filled) P95 <= 1.0 px, max <= 2 px"
            e["pass"] = cdf["p95"] is not None and cdf["p95"] <= 1.0 and cdf["max"] <= 2.0
        parts_res[k] = e
        if not e["pass"]:
            ys, xs = np.nonzero(op | refp)
            y0, y1 = max(ys.min() - 6, 0), min(ys.max() + 7, op.shape[0])
            x0, x1 = max(xs.min() - 6, 0), min(xs.max() + 7, op.shape[1])
            pdir = out_dir / "parts"
            pdir.mkdir(exist_ok=True)
            C.diff_image(op[y0:y1, x0:x1], refp[y0:y1, x0:x1], pdir / f"{k}{tag}.png", scale=6)
    res["views"]["side"]["parts"] = parts_res
    # label images: ours vs trace
    rng = np.random.default_rng(3)
    pal = (rng.uniform(60, 255, (len(keys) + 1, 3))).astype(np.uint8)
    pal[0] = 0
    H, W = frL.shape
    A = np.zeros((H, W, 3), np.uint8)
    Bm = np.zeros((H, W, 3), np.uint8)
    for ki, k in enumerate(keys):
        A[covs[ki] > 0.5] = pal[ki + 1]
        if k in jL["parts"]:
            Bm[C.rings_mask([r["px"] for r in jL["parts"][k]], frL.shape)] = pal[ki + 1]
    Image.fromarray(np.vstack([A, Bm])).resize((W * 2, H * 4), Image.NEAREST).save(out_dir / f"side_labels{tag}.png")

    # ---------------- top
    frT, jT = C.load_trace(TRACE, "TOP")
    refT = C.rings_mask([r["px"] for r in jT["silhouette"]], frT.shape)
    oursT = C.raster_tris(C.top_px(frT, V), T, frT.shape) > 0.5
    excl = zone_mask(frT, top_exclusions(), frT.shape)
    valid = ~excl
    t0 = C.iou(oursT, refT, valid)
    tall = C.iou(oursT, refT)
    pT, t1, _ = C.similarity_fit(lambda: (C.top_px(frT, V), T), refT, valid)
    cdT = C.contour_distance(oursT, refT, valid)
    res["views"]["top"] = {"iou_identity_valid": round(t0, 4), "iou_fit_valid": round(t1, 4),
                           "iou_identity_all_pixels": round(tall, 4), "fit_params_s_rotdeg_tx_ty": pT,
                           "excluded_px": int(excl.sum()),
                           "contour_px": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in cdT.items()}}
    C.overlay(panel_rgb("TOP"), oursT, refT, out_dir / f"top_overlay{tag}.png")
    C.diff_image(oursT, refT, out_dir / f"top_diff{tag}.png", valid=valid)

    # ---------------- true left vs the RIGHT-labelled panel (mirrored)
    frR, jR = C.load_trace(TRACE, "RIGHT")
    refR = C.rings_mask([r["px"] for r in jR["silhouette"]], frR.shape)
    oursR = C.raster_tris(C.side_px(frR, V), T, frR.shape) > 0.5
    r0 = C.iou(oursR, refR)
    pR, r1, _ = C.similarity_fit(lambda: (C.side_px(frR, V), T), refR, max_scale=0.04, max_shift=14.0)
    res["views"]["left_vs_RIGHT_panel"] = {"iou_identity": round(r0, 4), "iou_fit": round(r1, 4),
                                           "fit_params_s_rotdeg_tx_ty": pR,
                                           "note": "orthographic silhouettes from +Y and -Y are identical; this "
                                                   "measures the sheet's left panel drawing (self-IoU 0.893)"}
    C.overlay(panel_rgb("RIGHT"), oursR, refR, out_dir / f"left_overlay{tag}.png")
    return res


def gate_l1(res):
    s = res["views"]["side"]["iou_fit"]
    t = res["views"]["top"]["iou_fit_valid"]
    g = [{"name": "L1 side IoU (fit)", "value": s, "threshold": ">= 0.95", "pass": s >= 0.95},
         {"name": "L1 top IoU (fit, excluded zones masked)", "value": t, "threshold": ">= 0.92", "pass": t >= 0.92},
         {"name": "L1 stop rule", "value": min(s, t), "threshold": ">= 0.90 else change method",
          "pass": min(s, t) >= 0.90}]
    return g


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz", required=True)
    ap.add_argument("--stage", default="blockout")
    ap.add_argument("--tag", default="")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    r = run(a.npz, a.stage, a.tag)
    if a.stage == "blockout":
        r["gates"] = gate_l1(r)
    js = json.dumps(r, indent=1)
    print(js)
    if a.json:
        Path(a.json).write_text(js)
