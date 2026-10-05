"""3/4 FRONT RIGHT panel: reference mask, camera solve, silhouette gate, magazine-thickness check (plain Python).

    py -3 -B Scripts/guns/rifle/rifle_q34.py --npz <tris.npz> --stage blockout|form [--solve]

--solve   (re)solve the camera: landmarks -> least squares -> silhouette refinement on the rifle WITHOUT the
          magazine region (so the magazine check that follows is independent of the solve); saved to
          scratch/q34/camera.json and reused by later stages and the Blender 3/4 render.
Magazine thickness: with the solved camera, the magazine's visible silhouette is compared (IoU in the magazine zone)
for thickness t in 18..34 mm (Y scaled about the mid-plane); the best t is reported against the spec's 28.0.
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
from rifle_common import ROOT, SHEET, SCRATCH, REVIEW, WORK  # noqa: E402
from gunlib import compare as C  # noqa: E402
from gunlib import camsolve as CS  # noqa: E402

sys.path.insert(0, str(WORK / "tools"))
import refimg as R  # noqa: E402

BOX = (771, 322, 1528, 600)
QDIR = SCRATCH / "q34"
QDIR.mkdir(parents=True, exist_ok=True)

# panel px  <->  frame M (mm). Read off 4x gridded zooms (scratch/q34/g_left.png, g_right.png); +-1.5 px.
LANDMARKS = [
    ("butt top rear corner (near side)", (40.0, 48.0), (2.0, -18.0, -1.0)),
    ("butt bottom rear corner (near side)", (45.0, 137.0), (12.0, -18.0, -108.0)),
    ("grip toe (lowest point)", (190.0, 183.0), (263.5, -12.0, -132.5)),
    ("mag floor plate front corner", (353.0, 221.0), (493.1, -14.0, -138.9)),
    ("mag floor plate rear corner", (312.0, 263.0), (456.2, -14.0, -183.9)),
    ("rear sight notch plate top", (310.0, 23.0), (450.0, 0.0, 48.0)),
    ("front sight near ear top centre", (645.0, 43.0), (825.3, -10.7, 49.4)),
    ("brake bottom lip front", (720.0, 136.0), (880.0, -3.0, -9.0)),
    ("trigger guard bottom", (213.0, 129.0), (312.0, -5.0, -68.0)),
]
MAG_ZONE = [(238, 96), (372, 96), (372, 275), (238, 275)]          # px polygon holding the magazine


def panel():
    a = np.asarray(Image.open(SHEET).convert("RGB")).astype(float)
    return a[BOX[1]:BOX[3] + 1, BOX[0]:BOX[2] + 1]


def ref_mask():
    P = panel()
    L = P.mean(2)
    S = P.max(2) - P.min(2)
    bg, sd = R.fit_background(L, S)
    F = R.soft_field(L, S, bg, dl=30.0)
    # the floor contact shadow under the magazine: demand a much darker pixel there
    Fs = R.soft_field(L, S, bg, dl=75.0)
    zone = np.zeros_like(F, bool)
    zone[248:, 260:370] = True
    F[zone] = Fs[zone]
    F[:3, :] = F[-3:, :] = 0
    F[:, :3] = F[:, -3:] = 0
    m = R.largest_component(F > 0.5)
    m = ndi.binary_fill_holes(m)
    return m, P


def project_np(cam, V):
    return cam.project(V)


# ================================================================================ 3/4 residual vs the authority views
def _crop_overlay(panel_rgb, ours, ref, box, scale, extra=None):
    """Overlay crop (panel greyed, ref boundary blue, ours red) as a PIL image."""
    x0, y0, x1, y1 = box
    im = C.overlay(panel_rgb[y0:y1, x0:x1], ours[y0:y1, x0:x1], ref[y0:y1, x0:x1], None, scale=scale,
                   extra=None if extra is None else [(m[y0:y1, x0:x1], c) for m, c in extra]).convert("RGB")
    return im


def _pad_box(b, pad, shape):
    H, W = shape
    return [max(b[0] - pad, 0), max(b[1] - pad, 0), min(b[2] + pad + 1, W), min(b[3] + pad + 1, H)]


def exception_analysis(cam, V, T, lab, names, ours, ref, P, tag, magzone, selm):
    """Every 3/4 residual region > 3 px: which parts it involves, whether those parts agree with the authority views
    (side = LEFT-labelled panel per-part L2; TOP = local contour of the parts' own boundary pixels, excluded zones
    masked), whether a small local shift removes it (the panel draws the region displaced, not misshaped), and
    whether it depends on the magazine thickness (an unseen dimension: the 3/4 is its only witness). Writes evidence
    images review/<tag>/q34_exception/ and returns the records."""
    from PIL import Image as _I, ImageDraw as _D
    import rifle_silhouette as RS
    from rifle_common import TRACE as _TR
    sil = json.loads((SCRATCH / "sil.json").read_text()) if (SCRATCH / "sil.json").exists() else None
    side_parts = sil["views"]["side"]["parts"] if sil else {}
    obj2key = {o: k for k, objs in RS.PART_MAP.items() for o in objs}
    edir = REVIEW / tag / "q34_exception"
    edir.mkdir(parents=True, exist_ok=True)
    for f in edir.glob("*.png"):
        f.unlink()
    # our visible labels in the 3/4 view
    depth = cam.depth(V)
    L3 = C.raster_labels(cam.project(V), T, depth, lab, ref.shape, nlab=len(names))
    lm = L3.argmax(0)
    lm[L3.sum(0) < 0.5] = -1
    _, (iy, ix) = ndi.distance_transform_edt(lm < 0, return_indices=True)
    near = lm[iy, ix]
    # side view (authority for X/Z) and TOP (authority for widths)
    frL, jL = C.load_trace(_TR, "LEFT")
    refL = C.rings_mask([r["px"] for r in jL["silhouette"]], frL.shape)
    PL = C.side_px(frL, V)
    oursL = C.raster_tris(PL, T, frL.shape) > 0.5
    labL = C.raster_labels(PL, T, V[:, 1], lab, frL.shape, nlab=len(names))
    lmL = labL.argmax(0)
    lmL[labL.sum(0) < 0.5] = -1
    frT, jT = C.load_trace(_TR, "TOP")
    refT = C.rings_mask([r["px"] for r in jT["silhouette"]], frT.shape)
    PT = C.top_px(frT, V)
    oursT = C.raster_tris(PT, T, frT.shape) > 0.5
    labT = C.raster_labels(PT, T, -V[:, 2], lab, frT.shape, nlab=len(names))
    lmT = labT.argmax(0)
    lmT[labT.sum(0) < 0.5] = -1
    validT = ~RS.zone_mask(frT, RS.top_exclusions(), frT.shape)
    bT = C.boundary(oursT) & validT
    yy, xx = np.nonzero(oursT & validT)
    mmT = frT.mm(np.c_[xx, yy])
    labTv = lmT[yy, xx]
    wprof = jT["width_profile_mm_X_Yleft_Yright"]
    # TOP drawing faults, per side (+1 = gun left): the gate's own exclusions (spec sheet_panels) plus, for this
    # width check only, the 37 mm wide item the TOP draws at X ~793-815 that neither the side view nor c3 shows
    # (rifle_parts2.front_sight_block keeps it out); stations within 6 mm of a fault are skipped (fuzzy edges)
    top_zones = [(min(q[0] for q in z), max(q[0] for q in z), 1 if z[0][1] > 0 else -1) for z in RS.top_exclusions()]
    top_zones += [(793.0, 815.0, 1), (793.0, 815.0, -1)]
    panL, panT = RS.panel_rgb("LEFT"), RS.panel_rgb("TOP")
    # magazine-thickness dependence: the residual with the magazine at the 3/4 panel's preferred thickness
    rest = C.raster_tris(cam.project(V), T[~selm], ref.shape) > 0.5
    regions = C.residual_regions(ours, ref, 3.0)
    recs = []
    for n_r, rg in enumerate(regions, 1):
        m = rg["mask"]
        labs = (lm[m] if rg["kind"] == "ours_only" else near[m])
        labs = labs[labs >= 0]
        cnt = np.bincount(labs, minlength=len(names)) if len(labs) else np.zeros(len(names), int)
        order = [int(k) for k in np.argsort(-cnt) if cnt[k] > 0][:3]
        objs = [names[k] for k in order if cnt[k] >= 0.15 * cnt[order[0]]]
        keys = sorted({obj2key.get(o, o) for o in objs})
        side = {k: side_parts.get(k, {}).get("pass") for k in keys}
        side_ok = all(v for v in side.values() if v is not None) and any(v is not None for v in side.values())
        ids = [names.index(o) for o in objs]
        selT = bT & np.isin(lmT, ids)
        # TOP is the authority for WIDTHS only (its X positions are drawn up to 45 mm off, spec sheet_panels): compare
        # the half widths at the traced width-profile stations where these parts form our outer edge
        errs = []
        for X, yl, yr in wprof:
            col = np.abs(mmT[:, 0] - X) <= 0.65
            if not col.any():
                continue
            ys = mmT[col, 1]
            kl, kr = int(np.argmax(ys)), int(np.argmin(ys))
            ll = labTv[col]
            for k, yt, sgn in ((kl, yl, 1), (kr, yr, -1)):
                near_zone = any(z0 - 6.0 <= X <= z1 + 6.0 for z0, z1, zs in top_zones if zs == sgn)
                if ll[k] in ids and not near_zone:
                    errs.append(abs(ys[k] - yt))
        if len(errs) >= 2 and selT.sum() >= 3:
            e = np.array(errs) * frT.s
            top = {"stations": len(errs), "width_err_p95_px": round(float(np.percentile(e, 95)), 2),
                   "width_err_max_px": round(float(e.max()), 2), "p95_px": round(float(np.percentile(e, 95)), 2)}
            top_ok = top["width_err_p95_px"] <= 2.0
        else:
            top = {"stations": len(errs), "note": "not on the TOP silhouette (hidden under wider parts)"}
            top_ok = None
        win = _pad_box(rg["bbox"], 12, ref.shape)
        dx, dy, i0, i1, p0, p1 = C.best_local_shift(ours, ref, win, 8)
        # width tests: could a width change explain this region? For parts on the TOP silhouette, the widths TOP
        # allows (half width +- max(2 px, our measured TOP error)); for hidden parts (no TOP witness), +-15 %
        # (for the magazine also the 3/4 panel's preferred 23 mm). If a tested width removes most of the region
        # (core beyond 3 px below half), the region is about a WIDTH, not about the side-view X/Z shape.
        win_m = np.zeros_like(ref)
        win_m[win[1]:win[3], win[0]:win[2]] = True

        def core_with_y_scale(f):
            sel_o = np.isin(lab, ids)
            idx = np.unique(T[sel_o].ravel())
            Vw = V.copy()
            Vw[idx, 1] = V[idx, 1] * f
            alt = ndi.binary_fill_holes(C.raster_tris(cam.project(Vw), T, ref.shape) > 0.5)
            regs = [r for r in C.residual_regions(alt, ref, 3.0)
                    if (r["mask"] & m).any() or (r["mask"] & win_m).sum() > 0.5 * r["px"]]
            return int(sum(r["core_px"] for r in regs))

        hw = float(np.abs(V[np.unique(T[np.isin(lab, ids)].ravel()), 1]).max())
        if top_ok is not None:
            dmm = max(2.0, top.get("width_err_p95_px", 0.0)) / frT.s
            tests = {"half_width_minus_%.2fmm" % dmm: (hw - dmm) / hw, "half_width_plus_%.2fmm" % dmm: (hw + dmm) / hw}
        else:
            tests = {"width_x0.85": 0.85, "width_x1.15": 1.15}
            if any(o.startswith("magazine") for o in objs):
                tests["magazine_23mm"] = 23.0 / 28.0
        width_test = {k: core_with_y_scale(f) for k, f in tests.items()}
        width_fits = min(width_test.values()) < 0.5 * rg["core_px"]
        mag_dep = {"thickness_mm": 23.0, "region_core_px_at_23": width_test["magazine_23mm"],
                   "region_core_px_at_28": rg["core_px"]} if "magazine_23mm" in width_test else None
        if not side_ok:
            verdict = "OURS: the involved parts also miss the side view"
        elif width_fits and top_ok is not None:
            verdict = "OURS: a width the TOP allows would fit the 3/4 here"
        elif width_fits:
            verdict = "UNSEEN DIMENSION: a different width/thickness (no TOP witness) fits the 3/4 here"
        else:
            verdict = ("3/4 CONTRADICTS the authority views: the parts match LEFT (per-part L2) and no width the TOP "
                       "allows (or, hidden, +-15 %) removes the region")
        rec = {"id": n_r, "kind": rg["kind"], "bbox_px": rg["bbox"], "px": rg["px"], "core_px_beyond_3": rg["core_px"],
               "max_dist_px": rg["max_dist_px"], "objects": objs, "trace_keys": keys, "side_per_part_pass": side,
               "top": top, "local_shift": {"dx": dx, "dy": dy, "window_iou_before": round(i0, 4),
                                           "window_iou_after": round(i1, 4), "window_p95_before": p0,
                                           "window_p95_after": p1},
               "width_test_core_px": width_test, "magazine_thickness_dependence": mag_dep, "verdict": verdict,
               "is_contradiction": verdict.startswith("3/4 CONTRADICTS")}
        recs.append(rec)
        # evidence image: 3/4 crop | side crop of the involved parts | TOP crop (if visible)
        tiles = [("3/4 panel (region %d, %s, %.1f px)" % (n_r, rg["kind"], rg["max_dist_px"]),
                  _crop_overlay(P, ours, ref, win, 6, extra=[(m, (255, 200, 0))]))]
        selL = np.isin(lmL, ids)
        if selL.any():
            ys, xs = np.nonzero(selL)
            bL = _pad_box([xs.min(), ys.min(), xs.max(), ys.max()], 10, frL.shape)
            sc = max(2, min(6, int(360 / max(bL[2] - bL[0], bL[3] - bL[1], 1))))
            tiles.append(("LEFT panel (side authority): %s" % ", ".join("%s %s" % (k, "pass" if v else "FAIL")
                                                                         for k, v in side.items()),
                          _crop_overlay(panL, oursL, refL, bL, sc, extra=[(selL & C.boundary(oursL), (255, 200, 0))])))
        if selT.sum() >= 3:
            ys, xs = np.nonzero(selT)
            bTT = _pad_box([xs.min(), ys.min(), xs.max(), ys.max()], 10, frT.shape)
            sc = max(2, min(6, int(360 / max(bTT[2] - bTT[0], bTT[3] - bTT[1], 1))))
            tiles.append(("TOP panel (width authority): width error P95 %s px" % top.get("p95_px", "-"),
                          _crop_overlay(panT, oursT, refT, bTT, sc, extra=[(selT, (255, 200, 0))])))
        Hh = max(t[1].height for t in tiles) + 40
        Ww = sum(t[1].width for t in tiles) + 10 * (len(tiles) + 1)
        canvas = _I.new("RGB", (Ww, Hh + 30), (255, 255, 255))
        dr = _D.Draw(canvas)
        x = 10
        for cap, im in tiles:
            canvas.paste(im, (x, 30))
            dr.text((x, 8), cap, fill=(0, 0, 0))
            x += im.width + 10
        dr.text((10, Hh + 8), "verdict: " + verdict + "; local shift (%d, %d) px -> window IoU %.3f -> %.3f"
                % (dx, dy, i0, i1), fill=(160, 0, 0) if not rec["is_contradiction"] else (0, 110, 0))
        canvas.save(edir / ("region_%02d.png" % n_r))
    # index image: the 3/4 diff with numbered region boxes
    H, W = ours.shape
    A = np.zeros((H, W, 3), np.uint8)
    A[ours & ref] = (235, 235, 235)
    A[ours & ~ref] = (230, 50, 50)
    A[~ours & ref] = (50, 110, 255)
    im = _I.fromarray(A).resize((W * 3, H * 3), _I.NEAREST)
    dr = _D.Draw(im)
    for r in recs:
        b = r["bbox_px"]
        col = (0, 200, 0) if r["is_contradiction"] else (255, 160, 0)
        dr.rectangle([b[0] * 3 - 6, b[1] * 3 - 6, b[2] * 3 + 6, b[3] * 3 + 6], outline=col, width=2)
        dr.text((b[0] * 3 - 6, max(b[1] * 3 - 20, 0)), str(r["id"]), fill=col)
    im.save(edir / "index.png")
    return recs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz", required=True)
    ap.add_argument("--stage", default="blockout")
    ap.add_argument("--solve", action="store_true")
    a = ap.parse_args()
    D = np.load(a.npz)
    V, T, lab, names = D["V"], D["T"], D["lab"], [str(n) for n in D["names"]]
    ref, P = ref_mask()
    H, W = ref.shape
    magzone = C.poly_cov([np.array(MAG_ZONE, float)], ref.shape) > 0
    magk = [i for i, n in enumerate(names) if n.startswith("magazine")]
    selm = np.isin(lab, magk)
    camf = QDIR / ("camera_blockout.json" if a.stage == "blockout" else "camera.json")
    out = {"stage": a.stage}
    if a.solve or not camf.exists():
        p2 = np.array([l[1] for l in LANDMARKS])
        p3 = np.array([l[2] for l in LANDMARKS])
        cam0, err = CS.solve_landmarks(p2, p3, W / 2, H / 2, init_cam=(1400.0, -1500.0, 450.0),
                                       init_target=(440.0, 0.0, -30.0), f0=2000.0)
        out["landmark_rms_px"] = float(np.sqrt(np.mean(err ** 2)))
        out["landmark_err_px"] = {l[0]: round(float(e), 2) for l, e in zip(LANDMARKS, err)}
        valid = ~magzone
        cam, siou = CS.refine_silhouette(cam0, V, T[~selm], ref, valid=valid)
        out["refine_soft_iou_no_mag"] = siou
        camf.write_text(json.dumps(cam.to_dict(), indent=1))
    cd = json.loads(camf.read_text())
    cam = CS.Camera(cd["rvec"], cd["centre_M_mm"], cd["f_px"], cd["cx"], cd["cy"])
    out["camera"] = {"centre_M_mm": [round(v, 1) for v in cam.C], "f_px": round(cam.f, 1),
                     "distance_to_centre_mm": round(float(np.linalg.norm(cam.C - np.array([440, 0, -30]))), 1),
                     "forward_M": [round(v, 4) for v in cam.R[2]]}
    hfov = 2 * np.degrees(np.arctan(W / 2 / cam.f))
    out["camera"]["hfov_deg"] = round(float(hfov), 2)
    # ---- whole silhouette gate (L2 3/4)
    ours_raw = C.raster_tris(cam.project(V), T, ref.shape) > 0.5
    # the reference mask is hole-filled (ref_mask: binary_fill_holes), so the gate compares OUTER silhouettes: ours is
    # hole-filled too (trigger-guard opening, gas-tube/barrel gap, front-sight windows). Round 0 compared our open
    # holes against the filled reference (IoU 0.897 raw vs 0.910 filled on the same geometry).
    ours = ndi.binary_fill_holes(ours_raw)
    out["iou_raw_unfilled"] = round(C.iou(ours_raw, ref), 4)
    out["iou"] = round(C.iou(ours, ref), 4)
    out["contour_px"] = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in C.contour_distance(ours, ref).items()}
    out["contour_px_raw_unfilled"] = {k: (round(v, 3) if isinstance(v, float) else v)
                                      for k, v in C.contour_distance(ours_raw, ref).items()}
    nm = ~magzone
    out["iou_without_mag_zone"] = round(C.iou(ours, ref, nm), 4)
    tag = a.stage
    (REVIEW / tag).mkdir(parents=True, exist_ok=True)
    C.overlay(P, ours, ref, REVIEW / tag / "q34_overlay.png")
    C.diff_image(ours, ref, REVIEW / tag / "q34_diff.png")
    # ---- magazine thickness sweep
    sweep = {}
    rest = C.raster_tris(cam.project(V), T[~selm], ref.shape) > 0.5
    Vm = V.copy()
    for t in (18, 20, 22, 24, 26, 28, 30, 32, 34):
        Vm[:, 1] = V[:, 1]
        idx = np.unique(T[selm].ravel())
        Vm[idx, 1] = V[idx, 1] * (t / 28.0)
        om = C.raster_tris(cam.project(Vm), T[selm], ref.shape) > 0.5
        both = om | rest
        sweep[t] = round(C.iou(both, ref, magzone), 4)
    best_t = max(sweep, key=sweep.get)
    # parabola through the best and its neighbours
    ts = sorted(sweep)
    k = ts.index(best_t)
    if 0 < k < len(ts) - 1:
        x = np.array(ts[k - 1:k + 2], float)
        y = np.array([sweep[v] for v in ts[k - 1:k + 2]])
        c2, c1, c0 = np.polyfit(x, y, 2)
        t_star = float(-c1 / (2 * c2)) if c2 < 0 else float(best_t)
    else:
        t_star = float(best_t)
    out["magazine_thickness_check"] = {"iou_in_mag_zone_by_thickness_mm": sweep, "best_mm": best_t,
                                       "parabola_peak_mm": round(t_star, 2), "spec_mm": 28.0,
                                       "verdict": "28.0 kept" if abs(t_star - 28.0) <= 3.0 else
                                       "28.0 questioned (peak %.1f)" % t_star}
    if a.stage != "blockout":
        recs = exception_analysis(cam, V, T, lab, names, ours, ref, P, tag, magzone, selm)
        big = [r for r in recs if r["max_dist_px"] > 3.0]
        out["residual_regions_over_3px"] = recs
        out["exception"] = {
            "rule": "pass if IoU >= 0.93; else pass only if IoU >= 0.915 AND every residual region > 3 px is a region "
                    "where the 3/4 panel contradicts the LEFT/RIGHT/TOP authority views",
            "regions_over_3px": len(big), "contradictions": sum(r["is_contradiction"] for r in big),
            "not_contradictions": [{"id": r["id"], "objects": r["objects"], "verdict": r["verdict"]}
                                   for r in big if not r["is_contradiction"]],
            "evidence_dir": "WorkFiles/guns/rifle/review/%s/q34_exception" % tag}
        out["exception"]["pass"] = bool(out["iou"] >= 0.93 or (out["iou"] >= 0.915 and
                                                                 all(r["is_contradiction"] for r in big)))
    print(json.dumps({k: v for k, v in out.items() if k != "residual_regions_over_3px"}, indent=1))
    (REVIEW / tag / "q34_result.json").write_text(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
