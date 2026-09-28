#!/usr/bin/env python
"""props_lib.paperbomb_fidelity - the BUILT front scored against the user's reference.

``paperbomb_trace`` scores the traced SHAPES.  This scores what ships: the front's base
colour (the raster the BC map is a 1:1 blit of), photographed at the reference's own
grid and compared with the reference pixel for pixel, element by element.

    photograph   every reference pixel is the mean of a 4 x 4 grid of samples of our
                 base colour over that pixel's footprint on the card (bilinear), then the
                 source's own point spread (Gaussian 0.4 px) - i.e. what the reference's
                 own image formation would record of our texture.  The averaging is done
                 in STORED sRGB, because that is how the reference's edge pixels are
                 formed: the tracer's point-spread model, which mixes coverage linearly in
                 stored values, reproduces them to a band MAE of 0.028, and averaging in
                 linear light instead shifts every dark edge ~0.25 px inward.  Off the
                 card, the reference's own background is kept.
    unmix        the photograph goes through the SAME unmixing the reference went
                 through (``trace.ink_layers``), so our ink and theirs are measured by
                 one instrument.
    score        per element (the tracer's element regions): IoU of the half-strength
                 ink, the symmetric contour edge distance (source px and mm), and the
                 CIEDE2000 colour difference - pixel mean over the element's ink, and
                 between the two median ink colours.  The paper is scored on its own.

Nothing here is tuned to pass: the instrument is the tracer's, the reference is the one
source, and the tolerances in ``FIDELITY_TOLERANCE`` are stated before the build.
"""
from __future__ import annotations

import math

import numpy as np

from . import trace as T
from . import paperbomb_trace as PT

FIDELITY_VERSION = "1.0.0"

#: per element, on the BUILT map at the reference's grid.  The traced shapes reach IoU
#: 0.97 - 0.998; the photograph -> unmix round trip adds the unmixing's own noise, so the
#: built map is held a little under the shapes, and the emblem - the user's priority -
#: tighter than the rest.  Edge distance in mm (source px / 3.917), dE2000 on the median
#: ink colour and the pixel mean over the element's ink.
FIDELITY_TOLERANCE = {
    "default": {"iou": 0.95, "edge_mean_mm": 0.030, "de_median": 3.0, "de_mean": 8.0},
    "emblem": {"iou": 0.975, "edge_mean_mm": 0.020, "de_median": 3.0, "de_mean": 8.0},
    "rules": {"iou": 0.90, "edge_mean_mm": 0.040, "de_median": 4.0, "de_mean": 10.0},
    "paper": {"de_median": 1.5, "de_mean": 3.0, "edge_band_drop_diff": 0.01},
}


def photograph(base_linear: np.ndarray, card_mask: np.ndarray, ppmm: float, pad_mm: float,
               src: T.Source, fit: T.CardFit, sub: int = 4) -> np.ndarray:
    """Our base colour as the reference's camera would record it (stored sRGB)."""
    H, W = src.H, src.W
    Ht, Wt = base_linear.shape[:2]
    base_st = T.linear_to_srgb(base_linear)
    acc = np.zeros((H, W, 3), np.float64)
    cov = np.zeros((H, W), np.float64)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    for a in range(sub):
        for b in range(sub):
            spx = xx + (b + 0.5) / sub
            spy = yy + (a + 0.5) / sub
            xm, ym = fit.px_to_mm(spx, spy)
            u = (xm + pad_mm) * ppmm - 0.5
            v = (ym + pad_mm) * ppmm - 0.5
            u = np.clip(u, 0, Wt - 1.000001); v = np.clip(v, 0, Ht - 1.000001)
            j = np.floor(u).astype(np.int64); i = np.floor(v).astype(np.int64)
            fu = (u - j)[..., None]; fv = (v - i)[..., None]
            j1 = np.minimum(j + 1, Wt - 1); i1 = np.minimum(i + 1, Ht - 1)
            s = ((base_st[i, j] * (1 - fu) + base_st[i, j1] * fu) * (1 - fv)
                 + (base_st[i1, j] * (1 - fu) + base_st[i1, j1] * fu) * fv)
            c = ((card_mask[i, j] * (1 - fu[..., 0]) + card_mask[i, j1] * fu[..., 0]) * (1 - fv[..., 0])
                 + (card_mask[i1, j] * (1 - fu[..., 0]) + card_mask[i1, j1] * fu[..., 0]) * fv[..., 0])
            inside = (xm > -1.0) & (xm < PT.CARD_W_MM + 1.0) & (ym > -1.0) & (ym < PT.CARD_H_MM + 1.0)
            c = np.where(inside, c, 0.0)
            acc += s * c[..., None]
            cov += c
    cov /= sub * sub
    ours = acc / (sub * sub)
    # the background off the card: the reference's own, but estimated from pixels clearly
    # OFF the card (> 0.8 mm out), so the reference's edge pixels - which carry its trim
    # line - are never borrowed into our photograph where the card only part-covers them
    from . import paperbomb_tracedart as _TA
    yy2, xx2 = np.mgrid[0:H, 0:W] + 0.5
    exm, eym = fit.px_to_mm(xx2, yy2)
    off = _TA.octagon_edge_distance(exm, eym) < -0.8
    bg = T.norm_conv(src.rgb, off.astype(np.float64), 3.0, [1.0, 1.0, 1.0])
    img = ours + bg * (1.0 - cov)[..., None]
    img = np.stack([T.gauss_blur(img[..., k], T.SOURCE_PSF_SIGMA_PX) for k in range(3)], -1)
    return np.clip(img, 0, 1)


def score(base_linear: np.ndarray, card_mask: np.ndarray, ppmm: float, pad_mm: float,
          model=None) -> dict:
    """Per-element fidelity of a built front.  ``model`` is a tracedart RefModel (reused
    when given, so the reference is read and unmixed once)."""
    if model is None:
        from . import paperbomb_tracedart as TA
        model = TA.reference_model()
    L = model.L
    src, fit = L.src, L.fit
    photo = photograph(base_linear, card_mask, ppmm, pad_mm, src, fit)
    psrc = T.Source(path="photograph", sha256="", nbytes=0, rgb=photo, info={})
    ak2, behind2, unm2 = T.ink_layers(psrc, fit)
    masks = PT.group_masks(L)
    regions = PT.group_regions(L, masks)
    eregs = PT.element_regions(L, masks, regions)
    occluded = L.black > 0.85
    lab_ref = T.srgb_to_lab(src.rgb)
    lab_ours = T.srgb_to_lab(photo)
    de = T.delta_e2000(lab_ref, lab_ours)
    obs = {"black": L.black, "red": L.red_behind}
    ours = {"black": ak2, "red": behind2}
    out = {"version": FIDELITY_VERSION, "method": __doc__.split("\n\n")[1].strip(),
           "ppmm_source": round(fit.ppmm, 4), "elements": {}}
    for e in PT.ELEMENTS:
        rec = {"layers": {}}
        de_px = []
        med_pairs = []
        for layer in ("black", "red"):
            if (e.name, layer) not in eregs:
                continue
            reg = eregs[(e.name, layer)]
            if layer == "red":
                reg = reg & ~occluded
            sc = PT.score_fields(ours[layer], obs[layer], reg, fit.ppmm)
            core = reg & ((obs[layer] > 0.5) | (ours[layer] > 0.5))
            if core.any():
                de_px.append(de[core])
                refc = T.srgb_to_lab(np.median(src.rgb[core & (obs[layer] > 0.5)], 0)) \
                    if (core & (obs[layer] > 0.5)).any() else None
                ourc = T.srgb_to_lab(np.median(photo[core & (ours[layer] > 0.5)], 0)) \
                    if (core & (ours[layer] > 0.5)).any() else None
                if refc is not None and ourc is not None:
                    sc["de_median"] = round(float(T.delta_e2000(refc, ourc)), 3)
                    med_pairs.append((int(core.sum()), sc["de_median"]))
                sc["de_mean"] = round(float(de[core].mean()), 3)
            rec["layers"][layer] = sc
        if not rec["layers"]:
            continue
        ws = [(v.get("ink_px_obs", 0) + v.get("ink_px_pred", 0), v["iou"])
              for v in rec["layers"].values() if v.get("iou") is not None]
        tot = sum(w for w, _ in ws)
        rec["iou"] = round(sum(w * i for w, i in ws) / max(tot, 1), 4)
        em = [v["edge_mean_px"] for v in rec["layers"].values() if "edge_mean_px" in v]
        rec["edge_mean_px"] = round(float(np.mean(em)), 4) if em else None
        rec["edge_mean_mm"] = round(float(np.mean(em)) / fit.ppmm, 4) if em else None
        p95 = [v["edge_p95_px"] for v in rec["layers"].values() if "edge_p95_px" in v]
        rec["edge_p95_mm"] = round(float(max(p95)) / fit.ppmm, 4) if p95 else None
        if de_px:
            allde = np.concatenate(de_px)
            rec["de_mean"] = round(float(allde.mean()), 3)
            rec["de_p90"] = round(float(np.percentile(allde, 90)), 3)
        if med_pairs:
            tw = sum(w for w, _ in med_pairs)
            rec["de_median"] = round(sum(w * d for w, d in med_pairs) / max(tw, 1), 3)
        out["elements"][e.name] = rec
    # the paper, on the reference's bare-paper pixels
    yy, xx = np.mgrid[0:src.H, 0:src.W] + 0.5
    xm, ym = fit.px_to_mm(xx, yy)
    inner = (xm > 1.0) & (xm < PT.CARD_W_MM - 1.0) & (ym > 1.0) & (ym < PT.CARD_H_MM - 1.0)
    bare = inner & ((L.black + L.red) < 0.03) & ((ak2 + unm2.alpha_r) < 0.03)
    lum = np.array([0.2126, 0.7152, 0.0722])
    if bare.any():
        pr = {"px": int(bare.sum()),
              "de_mean": round(float(de[bare].mean()), 3),
              "de_p90": round(float(np.percentile(de[bare], 90)), 3),
              "de_median": round(float(T.delta_e2000(
                  T.srgb_to_lab(np.median(src.rgb[bare], 0)),
                  T.srgb_to_lab(np.median(photo[bare], 0)))), 3),
              "ref_median_hex": "#%02X%02X%02X" % tuple(int(round(v * 255))
                                                        for v in np.median(src.rgb[bare], 0)),
              "ours_median_hex": "#%02X%02X%02X" % tuple(int(round(v * 255))
                                                         for v in np.median(photo[bare], 0))}
        # the aged edge band: stored luma drop over the outer 2 mm, both
        band = ((xm > 0.6) & (xm < 2.0)) | ((xm > PT.CARD_W_MM - 2.0) & (xm < PT.CARD_W_MM - 0.6))
        band &= (ym > 12) & (ym < PT.CARD_H_MM - 12) & ((L.black + L.red) < 0.03)
        mid = inner & (xm > 20) & (xm < 50) & ((L.black + L.red) < 0.03) & ((ak2 + unm2.alpha_r) < 0.03)
        if band.any() and mid.any():
            pr["edge_band_drop_ref"] = round(float(1 - np.median(src.rgb[band] @ lum)
                                                   / np.median(src.rgb[mid] @ lum)), 4)
            pr["edge_band_drop_ours"] = round(float(1 - np.median(photo[band] @ lum)
                                                    / np.median(photo[mid] @ lum)), 4)
        # the cut edge's trim line: +-0.25 mm about the cut, bare card on the straight runs
        # (these pixels mix card and background in both images the same way)
        from . import paperbomb_tracedart as _TA
        ed = _TA.octagon_edge_distance(xm, ym)
        trim = (ed > -0.2) & (ed < 0.3) & ((L.black + L.red) < 0.03)             & ~T.dilate((L.black + L.red) > 0.1, 3)
        if trim.any():
            pr["edge_trim_px"] = int(trim.sum())
            pr["edge_trim_de_mean"] = round(float(de[trim].mean()), 3)
            pr["edge_trim_luma_ref"] = round(float(np.median(src.rgb[trim] @ lum)), 4)
            pr["edge_trim_luma_ours"] = round(float(np.median(photo[trim] @ lum)), 4)
        out["paper"] = pr
    card = (xm > 0.3) & (xm < PT.CARD_W_MM - 0.3) & (ym > 0.3) & (ym < PT.CARD_H_MM - 0.3)
    out["card_de_mean"] = round(float(de[card].mean()), 3)
    out["card_de_p90"] = round(float(np.percentile(de[card], 90)), 3)
    out["_photo"] = photo
    out["_de"] = de
    out["_layers_ours"] = ours
    return out


def gates(fid: dict) -> dict:
    """Pass/fail per element against ``FIDELITY_TOLERANCE``."""
    g = {}
    for name, rec in (fid.get("elements") or {}).items():
        tol = FIDELITY_TOLERANCE.get(name, FIDELITY_TOLERANCE["default"])
        ok = (rec.get("iou") is not None and rec["iou"] >= tol["iou"]
              and rec.get("edge_mean_mm") is not None and rec["edge_mean_mm"] <= tol["edge_mean_mm"]
              and rec.get("de_median", 99) <= tol["de_median"]
              and rec.get("de_mean", 99) <= tol["de_mean"])
        g[name] = {"passed": bool(ok), "iou": rec.get("iou"), "edge_mean_mm": rec.get("edge_mean_mm"),
                   "de_median": rec.get("de_median"), "de_mean": rec.get("de_mean"),
                   "tolerance": tol}
    p = fid.get("paper") or {}
    tp = FIDELITY_TOLERANCE["paper"]
    band_diff = abs(float(p.get("edge_band_drop_ours", 9.0)) - float(p.get("edge_band_drop_ref", 0.0)))
    g["paper"] = {"passed": bool(p and p.get("de_median", 99) <= tp["de_median"]
                                 and p.get("de_mean", 99) <= tp["de_mean"]
                                 and band_diff <= tp["edge_band_drop_diff"]),
                  "de_median": p.get("de_median"), "de_mean": p.get("de_mean"),
                  "edge_band_drop_diff": round(band_diff, 4), "tolerance": tp}
    return g


def public(fid: dict) -> dict:
    """The report-safe part (no arrays)."""
    return {k: v for k, v in fid.items() if not k.startswith("_")}


# ===========================================================================
# Like-for-like: every REFERENCE_SPEC row on the reference and on our photograph
# ===========================================================================

def _control_art(rgb_stored: np.ndarray, black: np.ndarray, red_behind: np.ndarray,
                 fit, cfg, lay, text: dict):
    """A TagArt carrying a SOURCE-GRID image (the reference, or our photograph of the
    build) resampled onto the art grid with the tracer's cubic B-spline, its ink layers
    from the tracer's unmixing.  Both go through exactly this, so the art_metrics
    instruments see the two at the same resolution."""
    from . import paperbomb_art as A
    from . import paperbomb_tracedart as TA
    W, H = A.raster_size(cfg)
    card, outline = A._card_mask(cfg, lay, W, H)
    (spx, spy), _ = TA.texture_to_source(fit, cfg.ppmm, cfg.pad_mm, H, W)
    chans = [T.srgb_to_linear(rgb_stored[..., k]) for k in range(3)] + [black, red_behind]
    coef = np.stack([TA._prefilter(c) for c in chans], 0)
    f = np.concatenate([TA.sample_fields(coef, spx[r:r + 256], spy[r:r + 256])
                        for r in range(0, H, 256)], 1)
    f = np.clip(f, 0, 1).astype(np.float32)
    base = np.ascontiguousarray(np.moveaxis(f[:3], 0, -1))
    red = A.Ink(H, W); blk = A.Ink(H, W)
    red.a = f[4]; blk.a = f[3]
    z = np.zeros((H, W), np.float32)
    art = A.TagArt(side="front", ppmm=cfg.ppmm, width=W, height=H, base_colour=base,
                   paper_rgb=base, roughness=z, relief=z, card_mask=card, fringe=z, scorch=z,
                   ink_mask=np.maximum(f[3], f[4]), ink_black=blk, ink_red=red,
                   outline_mm=outline)
    art.report = {"text": text}
    return art


_LFL_REF: dict = {}


def like_for_like(base_linear: np.ndarray, card_mask: np.ndarray, cfg, lay, text: dict,
                  model=None) -> dict:
    """Every REFERENCE_SPEC row measured on the reference AND on our build photographed at
    the reference's grid, through one pipeline.  A row the reference itself fails is
    miscalibrated for the reference of record; a row the reference passes, ours must."""
    from . import paperbomb_art as A
    from . import art_metrics as AM
    from . import measure as M
    from . import paperbomb_tracedart as TA
    if model is None:
        model = TA.reference_model()
    L = model.L
    fit = L.fit
    key = (model.traced_sha256, round(cfg.ppmm, 6), round(cfg.pad_mm, 6))

    def run(art):
        meas = AM.measure_front(art, cfg, lay)
        g = AM.spec_gates(meas, A.CORNER_CLIP_MM)
        rr = M.ring_radial_runs(art.ink_red.a, art.ppmm, cfg.pad_mm,
                                A.P(*lay.ring_centre), lay.ring_outer_mm)
        return meas, g, rr

    if key not in _LFL_REF:
        _LFL_REF[key] = run(_control_art(L.src.rgb, L.black, L.red_behind, fit, cfg, lay, text))
    mref, gref, rref = _LFL_REF[key]
    photo = photograph(base_linear, card_mask, cfg.ppmm, cfg.pad_mm, L.src, fit)
    ps = T.Source(path="photograph", sha256="", nbytes=0, rgb=photo, info={})
    kb, rb, _u = T.ink_layers(ps, fit)
    mour, gour, rour = run(_control_art(photo, kb, rb, fit, cfg, lay, text))

    def one_lap(r):
        return bool(r and r.get("median_runs_per_angle", 9) <= 2.0
                    and r.get("run_width_mm_p90", 0.0) >= 2.0)
    rows = {k: {"reference": bool(gref[k]), "ours": bool(gour.get(k))} for k in sorted(gref)}
    rows["20_ring_is_one_lap"] = {"reference": one_lap(rref), "ours": one_lap(rour)}
    agree = [k for k, v in rows.items() if v["reference"]]
    return {
        "method": ("the reference and our BC photographed at its grid (paperbomb_fidelity."
                   "photograph), each resampled onto the art grid by cubic B-spline with ink "
                   "layers from the tracer's unmixing, then the SAME art_metrics / measure "
                   "instruments"),
        "rows": rows,
        "reference_fails": [k for k, v in rows.items() if not v["reference"]],
        "ours_fails_where_reference_passes": [k for k in agree if not rows[k]["ours"]],
        "passed": all(rows[k]["ours"] for k in agree),
        "ring_runs": {"reference": rref, "ours": rour},
        "key_numbers": {
            "ring_hole_fraction": [mref["ring"].get("hole_fraction"), mour["ring"].get("hole_fraction")],
            "rule_weight_side_mm": [mref["rules"].get("weight_side_mm"), mour["rules"].get("weight_side_mm")],
            "rule_gap_len_cv_min": [mref["rules"].get("ink_gap_len_cv_min"), mour["rules"].get("ink_gap_len_cv_min")],
            "edge_depth_mean": [mref["edge_ageing"].get("depth_mean"), mour["edge_ageing"].get("depth_mean")],
            "grain_amplitude": [mref["grain"].get("amplitude"), mour["grain"].get("amplitude")],
            "column_raster_w_max_mm": [mref["columns"].get("raster_w_max_mm"), mour["columns"].get("raster_w_max_mm")],
        },
    }
