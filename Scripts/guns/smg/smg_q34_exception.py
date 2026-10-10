"""SMG01 3/4 view: the residual-region analysis behind the L2 3/4 exception rule (spec R38; the AR-01's rifle_q34.py
exception_analysis adapted). Plain Python, called by smg_q34.py on the form stages.

Every residual region (8-connected, its far part > 3 px outside the other mask) between our camera-solved 3/4 silhouette
and the panel's is classified:
  CONTRADICTION   the involved parts match the side authority (their L2 per-part keys pass) and no width the
                  authorities allow removes it: for parts on the TOP silhouette, every Y scale whose TOP half-width error
                  at the parts' own width stations stays at P95 <= 2 TOP px; hidden parts +-15 %; the grip the sections
                  whose girth stays in the real band (H1: 143.8 .. 167.3); the magazine the documented thickness band
                  [27, 31] (R26). A width that shrinks one region by growing another of the same parts is an offset
                  between the views (the side view places them): a contradiction too (the AR-01's integration rule).
  R26 MAGAZINE    a magazine-only region that the panel's preferred thickness (the sweep's peak, inside the band)
                  shrinks: the spec keeps 27.0 (the real minimum; R26)
  OURS            anything else (an involved part fails the side view, or an allowed width fits the 3/4 there)
The gate (R38): IoU >= 0.93 and contour P95 <= 3 px outright; else the camera-solved IoU >= 0.915 (the AR-01's floor)
AND, with the CONTRADICTION and R26 MAGAZINE regions left out of both masks, the rest meets the same bar (IoU >= 0.93,
P95 <= 3 px), every region is classified with evidence images (review/<stage>/q34_exception/), and no OURS region
remains. Below the floor the camera does not explain the panel, so no region is excused (the panel-consistency evidence
in q34_result.json then goes to the user: Q11, regenerate the panel or rule on it).
"""
from __future__ import annotations

import json
import math

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

from smg_common import SCRATCH, REVIEW, TRACE, D as SPECD, dims
from gunlib import compare as C
import smg_silhouette as SS

MAG_BAND = (27.0, 31.0)
IOU_FLOOR = 0.915                              # the AR-01's floor for its documented exception
GIRTH_BAND = (143.8, 167.3)                    # H1: the real polymer SMG grips' lower bound .. the + 10 % limit
TOP_X_MIN = float(SPECD["gates"]["look"]["L2_TOP_exclusion_X"])


def obj_keys(nm):
    if nm in SS.ALLOWED:
        return list(SS.ALLOWED[nm])
    k = SS.PART_MAP.get(nm)
    return [k] if k else []


def grip_girth(Vg, Tg):
    """Perimeter of the grip section perpendicular to the grip axis at the Grip origin (the H1 section)."""
    pg = dims("pistol_grip")
    ang = math.radians(float(pg["axis_rake_deg_from_vertical"]))
    n = np.array([-math.sin(ang), 0.0, -math.cos(ang)])
    o = np.array(SPECD["frames"]["B"]["Grip_in_M"], float)
    d = (Vg - o) @ n
    L = 0.0
    for t in Tg:
        dd = d[t]
        if (dd > 0).all() or (dd < 0).all():
            continue
        pts = []
        for a, b in ((0, 1), (1, 2), (2, 0)):
            if (dd[a] > 0) != (dd[b] > 0):
                u = dd[a] / (dd[a] - dd[b])
                pts.append(Vg[t[a]] + u * (Vg[t[b]] - Vg[t[a]]))
        if len(pts) == 2:
            L += float(np.linalg.norm(pts[1] - pts[0]))
    return L


def _crop(panel, ours, ref, box, scale, extra=None):
    x0, y0, x1, y1 = box
    return C.overlay(panel[y0:y1, x0:x1], ours[y0:y1, x0:x1], ref[y0:y1, x0:x1], None, scale=scale,
                     extra=None if extra is None else [(m[y0:y1, x0:x1], c) for m, c in extra]).convert("RGB")


def _pad(b, p, shape):
    H, W = shape
    return [max(b[0] - p, 0), max(b[1] - p, 0), min(b[2] + p + 1, W), min(b[3] + p + 1, H)]


def analyse(cam, V, T, lab, names, ours, ref, panel, stage, magzone, selm, mag_pref_t):
    sil = json.loads((SCRATCH / ("sil_%s.json" % stage)).read_text())
    side = sil["views"]["LEFT"]["parts"]
    edir = REVIEW / stage / "q34_exception"
    edir.mkdir(parents=True, exist_ok=True)
    for f in edir.glob("*.png"):
        f.unlink()
    L3 = C.raster_labels(cam.project(V), T, cam.depth(V), lab, ref.shape, nlab=len(names))
    lm = L3.argmax(0)
    lm[L3.sum(0) < 0.5] = -1
    _, (iy, ix) = ndi.distance_transform_edt(lm < 0, return_indices=True)
    near = lm[iy, ix]
    frT, jT = C.load_trace(TRACE, "TOP")
    refT = C.rings_mask([r["px"] for r in jT["silhouette"]], frT.shape)
    PT = C.top_px(frT, V)
    oursT = C.raster_tris(PT, T, frT.shape) > 0.5
    labT = C.raster_labels(PT, T, -V[:, 2], lab, frT.shape, nlab=len(names))
    lmT = labT.argmax(0)
    lmT[labT.sum(0) < 0.5] = -1
    HT, WT = frT.shape
    yy, xx = np.mgrid[0:HT, 0:WT]
    mmT_all = frT.mm(np.c_[xx.ravel(), yy.ravel()]).reshape(HT, WT, 2)
    validT = mmT_all[..., 0] >= TOP_X_MIN
    ysT, xsT = np.nonzero(oursT & validT)
    mmT = mmT_all[ysT, xsT]
    labTv = lmT[ysT, xsT]
    wprof = [w for w in jT["width_profile_mm_X_Yleft_Yright"] if w[0] >= TOP_X_MIN]
    frL, jL = C.load_trace(TRACE, "LEFT")
    refL = C.rings_mask([r["px"] for r in jL["silhouette"]], frL.shape)
    PL = C.side_px(frL, V)
    oursL = C.raster_tris(PL, T, frL.shape) > 0.5
    labL = C.raster_labels(PL, T, -V[:, 1], lab, frL.shape, nlab=len(names))
    lmL = labL.argmax(0)
    lmL[labL.sum(0) < 0.5] = -1
    panL, panT = SS.panel_rgb("LEFT"), SS.panel_rgb("TOP")
    regions = C.residual_regions(ours, ref, 3.0)
    recs = []
    for n_r, rg in enumerate(regions, 1):
        m = rg["mask"]
        labs = (lm[m] if rg["kind"] == "ours_only" else near[m])
        labs = labs[labs >= 0]
        cnt = np.bincount(labs, minlength=len(names)) if len(labs) else np.zeros(len(names), int)
        order = [int(k) for k in np.argsort(-cnt) if cnt[k] > 0][:3]
        objs = [names[k] for k in order if cnt[k] >= 0.15 * cnt[order[0]]] if order else []
        keys = sorted({k for o in objs for k in obj_keys(o)})
        side_res = {k: (side.get(k, {}).get("pass") or side.get(k, {}).get("pass_waived")) for k in keys if k in side}
        side_ok = bool(side_res) and all(side_res.values())
        ids = [names.index(o) for o in objs]
        errs, pairs = [], []
        for X, yl, yr in wprof:
            col = np.abs(mmT[:, 0] - X) <= 0.65
            if not col.any():
                continue
            ys = mmT[col, 1]
            kl, kr = int(np.argmax(ys)), int(np.argmin(ys))
            ll = labTv[col]
            for k_, yt in ((kl, yl), (kr, yr)):
                if ll[k_] in ids:
                    errs.append(abs(ys[k_] - yt))
                    pairs.append((ys[k_], yt))
        win = _pad(rg["bbox"], 12, ref.shape)
        win_m = np.zeros_like(ref)
        win_m[win[1]:win[3], win[0]:win[2]] = True
        mag_only = bool(objs) and all(o.startswith("magazine") for o in objs)

        def core_with_y_scale(f):
            sel_o = selm if mag_only else np.isin(lab, ids)
            idx = np.unique(T[sel_o].ravel())
            Vw = V.copy()
            Vw[idx, 1] = V[idx, 1] * f
            alt = ndi.binary_fill_holes(C.raster_tris(cam.project(Vw), T, ref.shape) > 0.5)
            regs = [r for r in C.residual_regions(alt, ref, 3.0)
                    if (r["mask"] & m).any() or (r["mask"] & win_m).sum() > 0.5 * r["px"]]
            return int(sum(r["core_px"] for r in regs))
        hw = float(np.abs(V[np.unique(T[np.isin(lab, ids)].ravel()), 1]).max()) if ids else 0.0
        top = None
        if len(errs) >= 2:
            e = np.array(errs) * frT.s
            top = {"stations": len(errs), "width_err_p95_px": round(float(np.percentile(e, 95)), 2)}
            ysa = np.array([q[0] for q in pairs])
            yta = np.array([q[1] for q in pairs])
            fs = np.round(np.arange(0.70, 1.3001, 0.005), 3)
            e95 = np.array([np.percentile(np.abs(f * ysa - yta), 95) * frT.s for f in fs])
            ok = e95 <= 2.0
            if ok.any():
                j1 = int(np.argmin(np.abs(fs - 1.0)))
                if not ok[j1]:
                    nz = np.nonzero(ok)[0]
                    j1 = int(nz[np.argmin(np.abs(nz - j1))])
                lo_i = hi_i = j1
                while lo_i > 0 and ok[lo_i - 1]:
                    lo_i -= 1
                while hi_i < len(fs) - 1 and ok[hi_i + 1]:
                    hi_i += 1
                flo, fhi = float(fs[lo_i]), float(fs[hi_i])
            else:
                flo = fhi = float(fs[int(np.argmin(e95))])
            allowed = {"source": "TOP width error P95 <= 2 px", "scale_range": [flo, fhi],
                       "half_width_mm_range": [round(hw * flo, 2), round(hw * fhi, 2)]}
            cand = sorted({flo, fhi, round(0.5 * (1.0 + flo), 4), round(0.5 * (1.0 + fhi), 4)} - {1.0})
            tests = {"top_allowed_x%.3f" % f: f for f in cand}
        elif mag_only:
            t0 = float(dims("magazine_body")["thickness"])
            allowed = {"source": "magazine thickness band %s (R26)" % (list(MAG_BAND),), "thickness_mm_range": list(MAG_BAND)}
            tests = {"thickness_%gmm" % t: t / t0 for t in (29.0, MAG_BAND[1])}
        elif objs and all(o in ("lower_receiver", "grip_cover") for o in objs) and "grip" in keys:
            kg = [names.index(o) for o in ("lower_receiver", "grip_cover") if o in names]
            ig = np.unique(T[np.isin(lab, kg)].ravel())
            remap = -np.ones(len(V), int)
            remap[ig] = np.arange(len(ig))
            Tg = remap[T[np.isin(lab, kg)]]
            fs = np.round(np.arange(0.85, 1.2001, 0.01), 3)
            okf = []
            for f in fs:
                Vg = V[ig].copy()
                Vg[:, 1] *= f
                g_ = grip_girth(Vg, Tg)
                okf.append(GIRTH_BAND[0] <= g_ <= GIRTH_BAND[1])
            okf = np.array(okf)
            if okf.any():
                nz = np.nonzero(okf)[0]
                flo, fhi = float(fs[nz.min()]), float(fs[nz.max()])
            else:
                flo = fhi = 1.0
            allowed = {"source": "grip sections in the H1 girth band %s" % (list(GIRTH_BAND),), "scale_range": [flo, fhi]}
            cand = sorted({flo, fhi} - {1.0})
            tests = {"h1_allowed_x%.2f" % f: f for f in cand} or {"none": 1.0}
        else:
            allowed = {"source": "hidden part, +-15 %", "scale_range": [0.85, 1.15]}
            tests = {"width_x0.85": 0.85, "width_x1.15": 1.15}
        width_test = {k: core_with_y_scale(f) for k, f in tests.items()} if ids else {}
        width_fits = bool(width_test) and min(width_test.values()) < 0.5 * rg["core_px"]
        mag_dep = None
        if mag_only and mag_pref_t:
            t0 = float(dims("magazine_body")["thickness"])
            c_pref = core_with_y_scale(float(mag_pref_t) / t0)
            mag_dep = {"spec_thickness_mm": t0, "panel_preferred_mm": round(float(mag_pref_t), 2),
                       "core_px_at_spec": rg["core_px"], "core_px_at_preferred": c_pref}
        r26 = bool(mag_only and side_ok and mag_dep is not None and mag_dep["core_px_at_preferred"] <= 0.8 * rg["core_px"])
        if not side_ok:
            verdict = "OURS: an involved part misses the side view (or no part identified)"
        elif r26:
            verdict = ("R26 MAGAZINE: the panel's %.1f mm magazine shrinks it (core %d -> %d px); the spec keeps %.1f "
                       "(the real minimum)" % (mag_dep["panel_preferred_mm"], rg["core_px"], mag_dep["core_px_at_preferred"],
                                               mag_dep["spec_thickness_mm"]))
        elif width_fits:
            verdict = "OURS: a width the authorities allow (%s) fits the 3/4 here" % allowed["source"]
        else:
            verdict = ("3/4 CONTRADICTS the authority views: the parts match LEFT (per-part L2) and no width the "
                       "authorities allow (%s) removes it" % allowed["source"])
        dx, dy, i0, i1, p0, p1 = C.best_local_shift(ours, ref, win, 8)
        rec = {"id": n_r, "kind": rg["kind"], "bbox_px": rg["bbox"], "px": rg["px"], "core_px_beyond_3": rg["core_px"],
               "max_dist_px": rg["max_dist_px"], "objects": objs, "trace_keys": keys, "side_per_part_pass": side_res,
               "top": top, "allowed_widths": allowed, "width_test_core_px": width_test,
               "magazine_thickness_dependence": mag_dep, "local_shift": {"dx": dx, "dy": dy, "window_iou": [round(i0, 4), round(i1, 4)]},
               "verdict": verdict, "is_contradiction": verdict.startswith("3/4 CONTRADICTS"), "is_r26_magazine": r26}
        recs.append(rec)
        tiles = [("3/4 panel (region %d, %s, %.1f px)" % (n_r, rg["kind"], rg["max_dist_px"]),
                  _crop(panel, ours, ref, win, 6, extra=[(m, (255, 200, 0))]))]
        selL = np.isin(lmL, ids)
        if selL.any():
            ys, xs = np.nonzero(selL)
            bL = _pad([xs.min(), ys.min(), xs.max(), ys.max()], 10, frL.shape)
            sc = max(2, min(6, int(360 / max(bL[2] - bL[0], bL[3] - bL[1], 1))))
            tiles.append(("LEFT panel: %s" % ", ".join("%s %s" % (k, "pass" if v else "FAIL") for k, v in side_res.items()),
                          _crop(panL, oursL, refL, bL, sc, extra=[(selL & C.boundary(oursL), (255, 200, 0))])))
        selT = C.boundary(oursT) & validT & np.isin(lmT, ids)
        if selT.sum() >= 3:
            ys, xs = np.nonzero(selT)
            bT = _pad([xs.min(), ys.min(), xs.max(), ys.max()], 10, frT.shape)
            sc = max(2, min(6, int(360 / max(bT[2] - bT[0], bT[3] - bT[1], 1))))
            tiles.append(("TOP panel: width error P95 %s px" % ((top or {}).get("width_err_p95_px", "-")),
                          _crop(panT, oursT, refT, bT, sc, extra=[(selT, (255, 200, 0))])))
        Hh = max(t[1].height for t in tiles) + 40
        Ww = sum(t[1].width for t in tiles) + 10 * (len(tiles) + 1)
        canvas = Image.new("RGB", (Ww, Hh + 30), (255, 255, 255))
        dr = ImageDraw.Draw(canvas)
        x = 10
        for cap, im in tiles:
            canvas.paste(im, (x, 30))
            dr.text((x, 8), cap, fill=(0, 0, 0))
            x += im.width + 10
        dr.text((10, Hh + 8), "verdict: " + verdict, fill=(0, 110, 0) if (rec["is_contradiction"] or r26) else (160, 0, 0))
        canvas.save(edir / ("region_%02d.png" % n_r))
    # the AR-01 integration rule: a width only FITS when it removes most of the residual summed over every region of the
    # same parts; one that shrinks a region by growing another of the same parts is an offset between the views
    for r in recs:
        if not r["verdict"].startswith("OURS: a width"):
            continue
        grp = [q for q in recs if set(q["objects"]) == set(r["objects"]) and set(q["width_test_core_px"]) == set(r["width_test_core_px"])]
        if len(grp) < 2:
            continue
        tot0 = sum(q["core_px_beyond_3"] for q in grp)
        tot = {k: sum(q["width_test_core_px"][k] for q in grp) for k in r["width_test_core_px"]}
        r["group_width_test"] = {"regions": [q["id"] for q in grp], "core_px_at_built": tot0, "core_px_by_test": tot}
        if min(tot.values()) >= 0.5 * tot0:
            r["verdict"] = ("3/4 CONTRADICTS the authority views: the width that shrinks this region grows region(s) %s of "
                            "the same parts (summed core %d px built, %s by width): an offset between the views, which "
                            "the side view (per-part L2 pass) decides" % ([q["id"] for q in grp if q is not r], tot0, tot))
            r["is_contradiction"] = True
    H, W = ours.shape
    A = np.zeros((H, W, 3), np.uint8)
    A[ours & ref] = (235, 235, 235)
    A[ours & ~ref] = (230, 50, 50)
    A[~ours & ref] = (50, 110, 255)
    im = Image.fromarray(A).resize((W * 3, H * 3), Image.NEAREST)
    dr = ImageDraw.Draw(im)
    for r in recs:
        b = r["bbox_px"]
        col = (0, 200, 0) if r["is_contradiction"] else (120, 200, 255) if r["is_r26_magazine"] else (255, 160, 0)
        dr.rectangle([b[0] * 3 - 6, b[1] * 3 - 6, b[2] * 3 + 6, b[3] * 3 + 6], outline=col, width=2)
        dr.text((b[0] * 3 - 6, max(b[1] * 3 - 20, 0)), str(r["id"]), fill=col)
    im.save(edir / "index.png")
    return recs, regions


def gate(out, recs, regions, ours, ref):
    """R38: the outright bar, else the bar on what the panel does not contradict."""
    big = [r for r in recs if r["max_dist_px"] > 3.0]
    excl = np.zeros_like(ref)
    for r, rg in zip(recs, regions):
        if r["is_contradiction"] or r["is_r26_magazine"]:
            excl |= ndi.binary_dilation(rg["mask"], iterations=1)
    iou_x = C.iou(ours, ref, ~excl)
    cd_x = C.contour_distance(ours, ref, ~excl)
    outright = bool(out["iou"] >= 0.93 and out["contour_px"]["p95"] is not None and out["contour_px"]["p95"] <= 3.0)
    unexpl = [{"id": r["id"], "objects": r["objects"], "verdict": r["verdict"]} for r in big
              if not (r["is_contradiction"] or r["is_r26_magazine"])]
    floor_ok = bool(out["iou"] >= IOU_FLOOR)
    ok_x = bool(floor_ok and iou_x >= 0.93 and cd_x["p95"] is not None and cd_x["p95"] <= 3.0 and not unexpl)
    return {"rule": "R38: pass if IoU >= 0.93 and contour P95 <= 3 px; else pass only if the camera-solved IoU >= %.3f "
                    "(the AR-01's floor: the camera must explain the panel before regions can be called contradictions) "
                    "AND, with the regions the study proves 3/4-panel contradictions (and the R26 magazine-thickness "
                    "regions) left out of both masks, the rest meets the same bar and no region > 3 px is unexplained"
                    % IOU_FLOOR,
            "floor_iou": IOU_FLOOR, "floor_pass": floor_ok,
            "outright_pass": outright, "regions": len(recs), "regions_over_3px": len(big),
            "contradictions": sum(r["is_contradiction"] for r in big), "r26_magazine": sum(r["is_r26_magazine"] for r in big),
            "excluded_px": int(excl.sum()), "iou_without_contradictions": round(iou_x, 4),
            "contour_p95_without_contradictions": None if cd_x["p95"] is None else round(cd_x["p95"], 3),
            "not_explained": unexpl, "pass": bool(outright or ok_x)}
