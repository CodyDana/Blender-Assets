"""Silhouette gates for SMG01 (plain Python): L1 (blockout) and the silhouette parts of L2 / L3 (form).

    py -3 -B Scripts/guns/smg/smg_silhouette.py --npz <tris.npz> --stage blockout|form [--json out.json]

Views (frame M -> panel px with each trace's own mapping, gunlib.compare; no camera error):
  LEFT   the gun's left side (both side panels are authority views here: the labels are true, spec R3)
  RIGHT  the gun's right side (the panel is traced mirrored; orthographic silhouettes from +Y / -Y are identical,
         so this measures the RIGHT panel's own drawing: the port side)
  TOP    X >= the spec's exclusion X (the stock is drawn obliquely, R18; checked by its widths instead)
Per part (form): visible labels (painter's order from the viewer's side) vs the trace's part masks; integral mouldings
are split by the trace's own label map at each triangle's centroid.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from smg_common import SPEC, TRACE, SHEET, REVIEW, D as SPECD  # noqa: E402
from gunlib import compare as C  # noqa: E402

TOP_X_MIN = float(SPECD["gates"]["look"]["L2_TOP_exclusion_X"])
L2_AREAS = SPECD["gates"]["look"]["L2_part_areas_px"]

# our object -> trace part key (separate parts); integral mouldings are split by the trace label map
PART_MAP = {"upper_receiver": None, "lower_receiver": None, "stock_frame": None, "grip_cover": "grip",
            "top_rail": "top_rail", "rail_screws": "top_rail", "lower_rail": "lower_rail",
            "sight_rear_base": "sight_rear", "sight_rear_leaf": "sight_rear", "sight_rear_pin": "sight_rear",
            "sight_front_base": "sight_front", "sight_front_leaf": "sight_front", "sight_front_pin": "sight_front",
            "barrel": "barrel", "muzzle_device": "muzzle_device", "trigger": "trigger", "trigger_axle": "receiver_lower",
            "mag_release": "mag_release", "mag_release_pin": "mag_release", "magazine": "magazine",
            "magazine_follower": "magazine", "magazine_floor_plate": "magazine", "butt_pad": "butt_pad",
            "hinge_axle": "stock_hinge_knuckle", "stock_latch_button": "stock_hinge_knuckle",
            "stock_latch_bolt": "stock_hinge_knuckle", "charging_handle": "handguard_area",
            "charging_slide": "receiver_upper", "bolt": "receiver_upper", "bolt_rails": "receiver_upper",
            "selector": "receiver_lower", "pins_fasteners": None,
            # blockout names
            "upper_fore_end": "handguard_area", "magwell": "mag_well", "trigger_guard": "trigger_guard",
            "pistol_grip": "grip", "end_block": "hinge_block", "stock_hinge": "stock_hinge_knuckle",
            "stock_neck": "stock_neck", "stock_top_strut": "stock_top_strut", "stock_lower_strut": "stock_lower_strut",
            "stock_web": "stock_web", "stock_rear_upright": "stock_rear_upright"}
ALLOWED = {"upper_receiver": ("receiver_upper", "handguard_area"),
           "lower_receiver": ("receiver_lower", "mag_well", "trigger_guard", "grip", "hinge_block"),
           "stock_frame": ("stock_neck", "stock_top_strut", "stock_lower_strut", "stock_web", "stock_rear_upright",
                           "stock_hinge_knuckle"),
           "pins_fasteners": ("receiver_lower", "receiver_upper", "hinge_block", "mag_well", "handguard_area"),
           "upper_receiver_blockout": ()}


def panel_rgb(view):
    j = json.loads((TRACE / f"{view}_outline.json").read_text())
    x0, y0, x1, y1 = j["panel_box_sheet_px"]
    a = np.asarray(Image.open(SHEET).convert("RGB"))[y0:y1 + 1, x0:x1 + 1]
    return a[:, ::-1] if j.get("mirrored") else a


def label_map():
    lab = np.asarray(Image.open(TRACE / "LEFT_parts_index.png"))
    names = json.loads((TRACE / "LEFT_parts_labels.json").read_text())["labels"]
    return lab, {int(k): v for k, v in names.items()}


def assign_keys(V, T, lab_obj, names, frL):
    """Trace part key per triangle: the separate parts by PART_MAP, the integral mouldings by the trace label map at
    the triangle centroid (nearest allowed label)."""
    lab, lnames = label_map()
    keys = sorted(set(v for v in lnames.values() if v not in ("background", "unassigned")))
    kidx = {k: i for i, k in enumerate(keys)}
    out = np.full(len(T), -1)
    cen = V[T].mean(axis=1)
    P = C.side_px(frL, cen)
    H, W = lab.shape
    # nearest-label lookup per allowed set
    cache = {}
    for oi, nm in enumerate(names):
        sel = np.nonzero(lab_obj == oi)[0]
        if not len(sel):
            continue
        k = PART_MAP.get(nm, "NA")
        if k not in (None, "NA"):
            out[sel] = kidx[k]
            continue
        allowed = ALLOWED.get(nm)
        if not allowed:
            continue
        ak = tuple(allowed)
        if ak not in cache:
            m = np.zeros_like(lab, bool)
            ids = [i for i, v in lnames.items() if v in allowed]
            m = np.isin(lab, ids)
            d, (iy, ix) = ndi.distance_transform_edt(~m, return_indices=True)
            cache[ak] = (iy, ix)
        iy, ix = cache[ak]
        px = np.clip(np.round(P[sel]).astype(int), [0, 0], [W - 1, H - 1])
        ny, nx = iy[px[:, 1], px[:, 0]], ix[px[:, 1], px[:, 0]]
        lv = lab[ny, nx]
        out[sel] = [kidx.get(lnames.get(int(v), ""), -1) for v in lv]
    return out, keys


def run(npz, stage, tag=""):
    D_ = np.load(npz)
    V, T, lab, names = D_["V"], D_["T"], D_["lab"], [str(n) for n in D_["names"]]
    res = {"stage": stage, "npz": str(Path(npz).name), "triangles": int(len(T)), "views": {}}
    out_dir = REVIEW / stage
    out_dir.mkdir(parents=True, exist_ok=True)
    mag_ids = [i for i, n in enumerate(names) if n.startswith("magazine")]
    is_mag = np.isin(lab, mag_ids)
    for view in ("LEFT", "RIGHT"):
        fr, j = C.load_trace(TRACE, view)
        ref = C.rings_mask([r["px"] for r in j["silhouette"]], fr.shape)
        ours = C.raster_tris(C.side_px(fr, V), T, fr.shape) > 0.5
        i0 = C.iou(ours, ref)
        p, i1, _ = C.similarity_fit(lambda: (C.side_px(fr, V), T), ref)
        cd = C.contour_distance(ours, ref)
        e = {"iou_identity": round(i0, 4), "iou_fit": round(i1, 4), "fit_params_s_rotdeg_tx_ty": p,
             "contour_px": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in cd.items()},
             "ours_px": int(ours.sum()), "ref_px": int(ref.sum())}
        if mag_ids:
            refm = C.rings_mask([r["px"] for r in j["magazine"]], fr.shape)
            om = C.raster_tris(C.side_px(fr, V), T[is_mag], fr.shape) > 0.5
            e["magazine_iou"] = round(C.iou(om, refm), 4)
            refn = C.rings_mask([r["px"] for r in j["gun_without_magazine"]], fr.shape)
            on = C.raster_tris(C.side_px(fr, V), T[~is_mag], fr.shape) > 0.5
            e["gun_without_mag_iou"] = round(C.iou(on, refn), 4)
        if view == "RIGHT":
            # the sheet's own ceiling: the LEFT trace (the authority for X / Z, R3) mapped into the RIGHT frame. A model
            # that matches LEFT exactly scores this against the RIGHT panel (the panels are near mirror copies only)
            jl = json.loads((TRACE / "LEFT_outline.json").read_text())
            rl = [C.side_px(fr, np.c_[np.array(r["mm"])[:, 0], np.zeros(len(r["mm"])), np.array(r["mm"])[:, 1]])
                  for r in jl["silhouette"]]
            ceil = C.rings_mask(rl, fr.shape)
            e["sheet_ceiling_iou_LEFT_trace_vs_RIGHT"] = round(C.iou(ceil, ref), 4)
            e["ours_minus_ceiling"] = round(i0 - C.iou(ceil, ref), 4)
        res["views"][view] = e
        C.overlay(panel_rgb(view), ours, ref, out_dir / f"{view.lower()}_overlay{tag}.png")
        C.diff_image(ours, ref, out_dir / f"{view.lower()}_diff{tag}.png")
    # ---------------- per part (LEFT, visible labels from +Y)
    frL, jL = C.load_trace(TRACE, "LEFT")
    tk, keys = assign_keys(V, T, lab, names, frL)
    ok = tk >= 0
    covs = C.raster_labels(C.side_px(frL, V), T[ok], -V[:, 1], tk[ok], frL.shape, nlab=len(keys))
    parts_res = {}
    for ki, k in enumerate(keys):
        if k not in jL["parts"]:
            continue
        refp = C.rings_mask([r["px"] for r in jL["parts"][k]], frL.shape)
        op = covs[ki] > 0.5
        area = float(L2_AREAS.get(k, refp.sum()))
        cdp = C.contour_distance(op, refp)
        e = {"area_px": round(area, 1), "iou": round(C.iou(op, refp), 4),
             "contour_p95_px": None if cdp["p95"] is None else round(cdp["p95"], 3),
             "contour_max_px": None if cdp["max"] is None else round(cdp["max"], 3)}
        if area >= 400.0:
            e["rule"] = "IoU >= 0.95"
            e["pass"] = e["iou"] >= 0.95
        else:
            opf, refpf = ndi.binary_fill_holes(op), ndi.binary_fill_holes(refp)
            cdf = C.contour_distance(opf, refpf)
            e["contour_p95_px"] = None if cdf["p95"] is None else round(cdf["p95"], 3)
            e["contour_max_px"] = None if cdf["max"] is None else round(cdf["max"], 3)
            e["iou_filled"] = round(C.iou(opf, refpf), 4)
            e["rule"] = "outer contour (holes filled) P95 <= 1.0 px, max <= 2 px"
            e["pass"] = cdf["p95"] is not None and cdf["p95"] <= 1.0 and cdf["max"] <= 2.0
        if k == "mag_release":
            e["declared"] = "mag_release.dims.declared_deviation: the paddle is built behind the drawn lever (C1); the " \
                            "per-part contour rule is waived; L3 gates the pin head and the Z range"
            e["pass_waived"] = True
        parts_res[k] = e
        if not e["pass"]:
            ys, xs = np.nonzero(op | refp)
            if len(ys):
                y0, y1 = max(ys.min() - 6, 0), min(ys.max() + 7, op.shape[0])
                x0, x1 = max(xs.min() - 6, 0), min(xs.max() + 7, op.shape[1])
                pdir = out_dir / "parts"
                pdir.mkdir(exist_ok=True)
                C.diff_image(op[y0:y1, x0:x1], refp[y0:y1, x0:x1], pdir / f"{k}{tag}.png", scale=6)
    res["views"]["LEFT"]["parts"] = parts_res
    # ---------------- TOP (X >= TOP_X_MIN)
    frT, jT = C.load_trace(TRACE, "TOP")
    refT = C.rings_mask([r["px"] for r in jT["silhouette"]], frT.shape)
    oursT = C.raster_tris(C.top_px(frT, V), T, frT.shape) > 0.5
    H, W = frT.shape
    yy, xx = np.mgrid[0:H, 0:W]
    Pm = frT.mm(np.c_[xx.ravel(), yy.ravel()])
    valid = (Pm[:, 0] >= TOP_X_MIN).reshape(H, W)
    t0 = C.iou(oursT, refT, valid)
    pT, t1, _ = C.similarity_fit(lambda: (C.top_px(frT, V), T), refT, valid)
    cdT = C.contour_distance(oursT, refT, valid)
    res["views"]["TOP"] = {"iou_identity_valid": round(t0, 4), "iou_fit_valid": round(t1, 4),
                           "iou_identity_all_pixels": round(C.iou(oursT, refT), 4), "fit_params_s_rotdeg_tx_ty": pT,
                           "valid_rule": "X >= %.1f (spec gates.look.L2_TOP_exclusion_X)" % TOP_X_MIN,
                           "contour_px": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in cdT.items()}}
    C.overlay(panel_rgb("TOP"), oursT, refT, out_dir / f"top_overlay{tag}.png")
    C.diff_image(oursT, refT, out_dir / f"top_diff{tag}.png", valid=valid)
    return res


def gate_l1(res):
    l, r, t = res["views"]["LEFT"]["iou_fit"], res["views"]["RIGHT"]["iou_fit"], res["views"]["TOP"]["iou_fit_valid"]
    ce = res["views"]["RIGHT"].get("sheet_ceiling_iou_LEFT_trace_vs_RIGHT")
    ri = res["views"]["RIGHT"]["iou_identity"]
    exc = ce is not None and ri >= ce - 0.005
    return [{"name": "L1 LEFT IoU (similarity fit)", "value": l, "threshold": ">= 0.95", "pass": l >= 0.95},
            {"name": "L1 RIGHT IoU (similarity fit)", "value": r, "threshold": ">= 0.95, or within 0.005 of the sheet's "
             "own LEFT/RIGHT ceiling (identity)", "pass": r >= 0.95 or exc,
             "note": "sheet ceiling (the LEFT trace vs the RIGHT panel, identity) %s; ours (identity) %.4f%s" % (
                 ce, ri, "; passes by the documented ceiling exception" if (exc and r < 0.95) else "")},
            {"name": "L1 TOP IoU (X >= %.0f, fit)" % TOP_X_MIN, "value": t, "threshold": ">= 0.92", "pass": t >= 0.92},
            {"name": "L1 stop rule (change the method below 0.90)", "value": min(l, r, t), "threshold": ">= 0.90",
             "pass": min(l, r, t) >= 0.90}]


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
    print(json.dumps({v: {k: x for k, x in e.items() if k != "parts"} for v, e in r["views"].items()}, indent=1))
    if a.json:
        Path(a.json).write_text(js)
