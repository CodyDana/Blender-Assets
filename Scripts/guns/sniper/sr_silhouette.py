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


def _trigger_blade_only(tm):
    """declared trace fix: the GR 'trigger' label also carries the guard's bottom bar (a component wider than tall
    under the blade, which is chassis); keep the components taller than wide (the blade)."""
    from scipy import ndimage
    lab, n = ndimage.label(tm)
    keep = np.zeros_like(tm)
    dropped = 0
    for k, sl in enumerate(ndimage.find_objects(lab), 1):
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if h >= w:
            keep |= lab == k
        else:
            dropped += int((lab == k).sum())
    return keep, {"dropped_px": dropped, "why": "guard bottom bar labelled trigger in the trace (it is chassis)"}


TRACE_LABEL_FIX = {"trigger": _trigger_blade_only}


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


def raster_zbuffer(P2, T, depth, labels, shape, ss=3):
    """Per-pixel z-buffer label map (W1 follow-up: the painter's order by triangle MEAN depth let the long n-gon fans
    of the chassis faces paint over the trigger and the release paddle, which read 0.0). Smaller depth = nearer.
    Returns the label image (H, W) at pixel centres of an ss x ss supersample, majority-reduced (-1 = empty)."""
    H, W = shape
    Hs, Ws = H * ss, W * ss
    zb = np.full((Hs, Ws), np.inf)
    lb = np.full((Hs, Ws), -1, np.int32)
    Q = (np.asarray(P2, float) + 0.5) * ss - 0.5
    dv = np.asarray(depth, float)
    for i in range(len(T)):
        a, b, c = Q[T[i, 0]], Q[T[i, 1]], Q[T[i, 2]]
        x0, x1 = int(max(np.floor(min(a[0], b[0], c[0])), 0)), int(min(np.ceil(max(a[0], b[0], c[0])), Ws - 1))
        y0, y1 = int(max(np.floor(min(a[1], b[1], c[1])), 0)), int(min(np.ceil(max(a[1], b[1], c[1])), Hs - 1))
        if x1 < x0 or y1 < y0:
            continue
        den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(den) < 1e-12:
            continue
        yy, xx = np.mgrid[y0:y1 + 1, x0:x1 + 1]
        w0 = ((b[1] - c[1]) * (xx - c[0]) + (c[0] - b[0]) * (yy - c[1])) / den
        w1 = ((c[1] - a[1]) * (xx - c[0]) + (a[0] - c[0]) * (yy - c[1])) / den
        w2 = 1.0 - w0 - w1
        ins = (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9)
        if not ins.any():
            continue
        z = w0 * dv[T[i, 0]] + w1 * dv[T[i, 1]] + w2 * dv[T[i, 2]]
        sub_z = zb[y0:y1 + 1, x0:x1 + 1]
        sub_l = lb[y0:y1 + 1, x0:x1 + 1]
        win = ins & (z < sub_z)
        sub_z[win] = z[win]
        sub_l[win] = labels[i]
    return lb


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
        if view == "GL":
            # declared sheet window (W1 follow-up, sr_l2_columns evidence): GL draws the forend underside X 555..700
            # 5-13 mm higher than GR does (GR matches the build there within 1 px); compared with that band left out
            H, W = ref.shape
            yy, xx = np.mgrid[0:H, 0:W].astype(float)
            Ai = np.linalg.inv(np.r_[X.T, [[0.0, 0.0, 1.0]]])
            mmx = Ai[0, 0] * xx + Ai[0, 1] * yy + Ai[0, 2]
            mmz = Ai[1, 0] * xx + Ai[1, 1] * yy + Ai[1, 2]
            valid = ~((mmx > 555) & (mmx < 700) & (mmz < -38.0) & (mmz > -66.0))
            res["views"]["GL"]["iou_forend_underside_window_out"] = round(C.iou(ours, ref, valid), 4)
            res["views"]["GL"]["contour_p95_px_window_out"] = round(C.contour_distance(ours & valid, ref & valid)["p95"], 2)
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
            # per part: z-buffer (viewer at -Y: smaller Y = nearer), coverage per label from the ss x ss samples
            ss = 3
            LB = raster_zbuffer(P2, T, V[:, 1], lab, ref.shape, ss=ss)
            Hh, Ww = ref.shape

            class _Cov:
                def __getitem__(self, ids):
                    m = np.isin(LB, ids).astype(float)
                    return m.reshape(Hh, ss, Ww, ss).mean(axis=(1, 3))[None]
            L = _Cov()
            parts = {}
            for key, rec in j["parts"].items():
                pref = PART_MAP.get(key, [key])
                ids = [k for k, n in enumerate(names) if any(n.startswith(p) for p in pref)]
                if not ids:
                    continue
                tm = C.rings_mask(rec["px"], ref.shape)
                fix = None
                if key in TRACE_LABEL_FIX:
                    tm, fix = TRACE_LABEL_FIX[key](tm)
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
                if fix:
                    parts[key]["trace_label_fix"] = fix
                # what covers the traced label where we disagree (label, not silhouette, disagreements)
                miss = tm & ~om
                lbm = LB.reshape(Hh, ss, Ww, ss)[:, ss // 2, :, ss // 2]
                u, c = np.unique(lbm[miss], return_counts=True)
                parts[key]["missed_px_covered_by"] = {("empty" if q < 0 else names[q]): int(n)
                                                      for q, n in sorted(zip(u, c), key=lambda t: -t[1])[:3]}
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
