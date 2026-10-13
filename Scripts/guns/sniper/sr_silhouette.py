"""SR01 silhouette gates L1 / L2 / L3 (plain Python): the built triangles (scratch npz, frame M mm) projected into the
sheet panels with the trace's own mm -> px mapping (least squares from the traced rings' px / mm pairs), rasterised,
compared with the traced silhouettes (GR, GL, TOP); per-part IoU on GR from a painter's-order label raster.

    py -3 -B Scripts/guns/sniper/sr_silhouette.py --npz scratch/w1/blockout_tris.npz --stage blockout
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from sr_common import TRACE, SCRATCH, REVIEW, trace  # noqa: E402
from gunlib import compare as C  # noqa: E402

VIEWS = {"GR": ("XZ", +1), "GL": ("XZ", -1), "TOP": ("XY", 0)}

# trace part key -> our object-name prefixes (form) ; the blockout's names match the keys' WIDTH map
PART_MAP = {
    "butt_pad": ["butt_pad"], "pad_plate": ["pad_plate"], "butt": ["butt"], "cheek_riser": ["cheek_riser", "riser_post"],
    "chassis_centre": ["chassis"], "chassis_forend": ["chassis"], "trigger_guard": ["chassis"], "grip": ["grip"],
    "trigger": ["trigger"], "mag_release": ["mag_release"], "magazine": ["magazine"], "rail": ["rail"],
    "bipod": ["bipod"], "bolt_handle": ["bolt_handle", "bolt_knob"], "receiver": ["receiver"],
    "bolt_shroud": ["bolt_shroud", "bolt"], "barrel": ["barrel"], "muzzle_device": ["muzzle_device"],
    "scope": ["scope"], "bipod": ["bipod"],
}


def affine(rings_px, rings_mm):
    P = np.vstack([np.asarray(r, float) for r in rings_px])
    Q = np.vstack([np.asarray(r, float) for r in rings_mm])
    A = np.c_[Q, np.ones(len(Q))]
    X, *_ = np.linalg.lstsq(A, P, rcond=None)          # px = [mmx, mmy, 1] @ X
    res = np.sqrt(((A @ X - P) ** 2).sum(1))
    return X, float(np.percentile(res, 95))


def project(V, view, X):
    plane, _ = VIEWS[view]
    Q = np.c_[V[:, 0], V[:, 2]] if plane == "XZ" else np.c_[V[:, 0], V[:, 1]]
    return np.c_[Q, np.ones(len(Q))] @ X


def ref_mask(view):
    return np.asarray(Image.open(TRACE / f"{view}_silhouette.png").convert("L")) > 127


def overlay(ours, ref, path, scale=2):
    H, W = ref.shape
    im = np.full((H, W, 3), 255, np.uint8)
    im[ours & ref] = (150, 150, 150)
    im[ref & ~ours] = (220, 30, 30)
    im[ours & ~ref] = (30, 60, 230)
    Image.fromarray(im).resize((W * scale, H * scale), Image.NEAREST).save(path)


def run(npz, stage, out_json=None, img_dir=None, exclude=(), with_npz=None, with_names=()):
    z = np.load(npz, allow_pickle=True)
    V, T, lab, names = z["V"], z["T"], z["lab"], [str(n) for n in z["names"]]
    if with_npz:      # declared stand-in parts from another build (the blockout scope until W1b builds the attachment)
        w = np.load(with_npz, allow_pickle=True)
        wn = [str(n) for n in w["names"]]
        sel = np.array([wn[l] in with_names for l in w["lab"]])
        remap = {}
        for l in sorted(set(w["lab"][sel].tolist())):
            remap[l] = len(names)
            names.append(wn[l])
        T = np.vstack([T, w["T"][sel] + len(V)])
        lab = np.concatenate([lab, np.array([remap[l] for l in w["lab"][sel]], lab.dtype)])
        V = np.vstack([V, w["V"]])
    keep = np.array([not any(names[l].startswith(e) for e in exclude) for l in lab])
    T, lab = T[keep], lab[keep]
    img_dir = Path(img_dir or (REVIEW / stage))
    img_dir.mkdir(parents=True, exist_ok=True)
    res = {"stage": stage, "npz": str(Path(npz).name), "triangles": int(len(T)), "views": {}}
    for view in VIEWS:
        j = trace(view)
        X, fit_p95 = affine(j["silhouette"]["px"], j["silhouette"]["mm"])
        ref = ref_mask(view)
        P2 = project(V, view, X)
        ours = C.raster_tris(P2, T, ref.shape, ss=4) > 0.5
        iou = C.iou(ours, ref)
        cd = C.contour_distance(ours, ref)
        overlay(ours, ref, img_dir / f"{view}_overlay.png")
        res["views"][view] = {"iou": round(iou, 4), "contour_p50_px": round(cd["p50"], 2),
                              "contour_p95_px": round(cd["p95"], 2), "contour_max_px": round(cd["max"], 2),
                              "mapping_fit_p95_px": round(fit_p95, 3),
                              "ours_px": int(ours.sum()), "ref_px": int(ref.sum())}
        if view == "TOP":
            # declared convention (spec I2 + the TOP's +6-10 % round-part inflation, MEASUREMENT_NOTES): the TOP's right
            # edge (image-down) carries a floor-shadow bias and its round parts are drawn wide, so the build is also
            # compared after a bounded Y-only fit: scale 1.00..1.10 and shift 0..-5 mm (toward the right / shadow)
            # declared window (spec I1 / L3 'knob X from GR only'): the TOP draws the bolt knob 32 mm further back
            H, W = ref.shape
            yy, xx = np.mgrid[0:H, 0:W].astype(float)
            Xi = np.linalg.inv(np.r_[X.T, [[0, 0, 1]]].T.T) if False else None
            A = np.r_[X.T, [[0.0, 0.0, 1.0]]]                       # [px_x, px_y, 1] = A @ [mmx, mmy, 1]
            Ai = np.linalg.inv(A)
            mmx = Ai[0, 0] * xx + Ai[0, 1] * yy + Ai[0, 2]
            mmy = Ai[1, 0] * xx + Ai[1, 1] * yy + Ai[1, 2]
            valid = ~((mmx > 300) & (mmx < 400) & (mmy < -27.0))
            best = (C.iou(ours, ref, valid), 1.0, 0.0, ours)
            for sy in np.arange(1.0, 1.1001, 0.01):
                for dy in np.arange(0.0, -5.01, -0.5):
                    V2 = V.copy()
                    V2[:, 1] = V2[:, 1] * sy + dy
                    o2 = C.raster_tris(project(V2, view, X), T, ref.shape, ss=2) > 0.5
                    v = C.iou(o2, ref, valid)
                    if v > best[0]:
                        best = (v, sy, dy, o2)
            cs = C.contour_distance(best[3], ref)
            overlay(best[3], ref, img_dir / "TOP_fit_overlay.png")
            er = ref & ~__import__("scipy.ndimage", fromlist=["x"]).binary_erosion(ref)
            res["views"]["TOP"]["iou_knob_window_out"] = round(C.iou(ours, ref, valid), 4)
            res["views"]["TOP"]["sheet_1px_sensitivity_iou"] = round(C.iou(ref & ~er, ref), 4)
            res["views"]["TOP_fit"] = {"iou": round(best[0], 4), "y_scale": round(best[1], 3), "y_shift_mm": best[2],
                                       "contour_p95_px": round(cs["p95"], 2),
                                       "note": "bounded Y-only fit for the TOP's shadow bias + round-part inflation"}
        if view == "GR":
            # per part: painter's order (viewer at -Y: larger Y = farther)
            L = C.raster_labels(P2, T, V[:, 1], lab, ref.shape, ss=4, nlab=len(names))
            parts = {}
            for key, rec in j["parts"].items():
                pref = PART_MAP.get(key, [key])
                ids = [k for k, n in enumerate(names) if any(n.startswith(p) for p in pref)]
                if not ids:
                    continue
                tm = C.rings_mask(rec["px"], ref.shape)
                om = L[ids].sum(0) > 0.5
                # the trace splits the chassis into three labels: compare inside the label's own box (+2 px)
                if pref == ["chassis"]:
                    yy, xx = np.nonzero(tm)
                    win = np.zeros_like(tm)
                    win[max(yy.min() - 2, 0):yy.max() + 3, max(xx.min() - 2, 0):xx.max() + 3] = True
                    om = om & win & ~(np.zeros_like(tm))
                    others = np.zeros_like(tm)
                    for k2, r2 in j["parts"].items():
                        if k2 != key and PART_MAP.get(k2) == ["chassis"]:
                            others |= C.rings_mask(r2["px"], ref.shape)
                    om &= ~others
                parts[key] = {"iou": round(C.iou(om, tm), 4), "area_px": int(tm.sum())}
            res["views"][view]["parts"] = parts
    if out_json:
        Path(out_json).write_text(json.dumps(res, indent=1), encoding="utf-8")
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz", required=True)
    ap.add_argument("--stage", default="blockout")
    ap.add_argument("--json", default=None)
    ap.add_argument("--exclude", default="")
    ap.add_argument("--with-npz", default=None)
    ap.add_argument("--with-names", default="scope_blockout,scope_rings")
    a = ap.parse_args()
    r = run(a.npz, a.stage, a.json or (SCRATCH / f"sil_{a.stage}.json"),
            exclude=[e for e in a.exclude.split(",") if e], with_npz=a.with_npz,
            with_names=[e for e in a.with_names.split(",") if e])
    print(json.dumps({v: {k: x for k, x in d.items() if k != "parts"} for v, d in r["views"].items()}, indent=1))
    if "parts" in r["views"]["GR"]:
        print(json.dumps(r["views"]["GR"]["parts"]))
