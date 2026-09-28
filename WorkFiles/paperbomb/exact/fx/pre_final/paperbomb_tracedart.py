#!/usr/bin/env python
"""props_lib.paperbomb_tracedart - the printed face of SM_PaperBomb, built from the user's
reference by tracing and sampling it.

The paper bomb is the USER'S OWN design and they asked for it to be traced from their one
reference, References/PaperBomb/paperbomb_guide_v2_real_glyphs.png (300 x 653 px, about
3.9 px/mm).  This module turns that reference into the front face's layers at the
texture's own grid (12.923 px/mm, 25.846 with the shipping 2x supersample).  Nothing on the
face is drawn from a procedure of ours except the paper's fibre ABOVE the reference's
Nyquist limit, where the reference carries no information at all.

HOW EACH PART IS MADE
---------------------
SHAPES (every mark on the face).  ``props_lib/paperbomb_traced.json`` holds every inked
element as resolution-independent curves in card millimetres (props_lib.paperbomb_trace:
sub-pixel contours, spline fits, analysis-by-synthesis refinement; the frame rules as
centreline + width strokes).  They are rasterised here with exact-area nonzero coverage,
so an edge is as crisp at the texture's grid as the curve is - the reference's 3.9 px/mm
blur is never upsampled into the map.  That covers the flame emblem, 爆, the four text
columns (the font detective found no font on the machine that is the user's hand, so they
are traced too), both seals and the small seal's 火道, the ring, the rules, the corner
flourishes, the centreline chain and its leaves.

TONE (how much ink is in the mark).  A traced shape carries only the ink at or above half
strength.  Inside it, the reference's own ink field divided by what the shape predicts
through the source's point spread gives the local ink LOAD (a dry passage in the ring
reads 0.6, a charged stroke 0.97); outside it, the ink the shapes do not explain (the
dry-brush streaks under half strength, ring soft IoU 0.954 without them) is the
RESIDUAL.  Both are sampled from the reference - never invented - and neither is simply
upsampled: a partial value is turned into crisp hair-width bristle marks whose area
fraction equals the sampled value (``crisp``), running ALONG the local stroke direction
measured from the reference's structure tensor.  So a dry passage is paper between hard
bristle streaks at 4x, and the same grey at the reference's resolution.  The residual is
only taken more than a pixel clear of a shape's edge, so no grey fringe can form round
a stroke.

COLOUR.  Composited in the reference's own space (stored sRGB), exactly as the tracer's
unmixing model reads it: pixel = paper (1 - k - r) + red_local r + black_local k, red
under black (``red_behind``) so there is no seam where 爆 crosses the ring.  The red is
the reference's LOCAL red (a normalised mean of the red cores within ~0.6 mm), so the
ring, the seals, the rules and the chain keep their own reds instead of one pigment at one
weight.  The black is likewise the local black core colour.

PAPER.  Derived from the reference with the ink removed: the confidently-bare paper
pixels are kept exactly, the paper under and beside ink is filled by multi-scale
normalised convolution, and the result is interpolated (cubic B-spline) to the texture's
grid.  That reproduces the reference's paper colour, its mottle where it actually is and
its aged edge band exactly.  ABOVE the reference's Nyquist (2 cycles/mm) a fine anisotropic
fibre band is added at the amplitude the reference's own finest measurable band carries.
Why this and not a procedural paper tuned to the reference's statistics: at gallery size a
side-by-side shows WHERE the mottle and edge ageing are, not only how strong they are, and
a procedural field can only match the statistics; at 4x the reference has no detail to
copy, so the procedural fibre band is what fills the texture's extra octave either way.

Deterministic numpy: the same source bytes, the same traced JSON and the same seed give
the same layers byte for byte.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import dataclass

import numpy as np

from . import trace as T
from . import paperbomb_trace as PT

TRACEDART_VERSION = "1.2.0"

#: the reference's paper is kept exactly where its unmixed ink is under this
PAPER_INK_MAX = 0.03
#: ...and more than this far (mm) inside the card's edge (the edge pixels mix with the
#: white background)
PAPER_EDGE_KEEP_MM = 0.40
#: the residual (ink the shapes do not explain) is only taken where the shapes' own
#: predicted ink is below this - i.e. more than about a pixel clear of a traced edge -
#: which is what keeps a grey fringe from forming round every stroke
RESID_PSF_MAX = 0.30
#: residual below this is unmixing noise on bare paper (99th percentile of the far field
#: is 0.068 black / 0.096 red); black is held higher because a black edge's own blur in
#: the reference is a little wider than the point-spread model and leaves ~0.1 there
RESID_FLOOR = {"black": 0.12, "red": 0.07}
#: a residual streak must lie within this distance (mm) of that layer's traced ink
RESID_REACH_MM = {"black": 1.0, "red": 1.6}
#: ...and this far inside the card's edge (the reference's edge staining is paper)
RESID_EDGE_MM = 2.4
#: a tone at or above this inside a shape is a charged stroke and is laid as it is;
#: below it the tone is split into crisp bristle marks
TONE_SOLID = 0.86
#: bristle geometry, mm: length along the stroke, width across it
BRISTLE_ALONG_MM = 0.55
BRISTLE_ACROSS_MM = 0.045
#: softness of a bristle edge, in units of the crisp threshold (smaller = harder)
BRISTLE_EDGE = 0.18
#: the orientation field is constant over tiles of this size (mm), blended bilinearly
ORIENT_TILE_MM = 2.5
#: the fibre band added above the reference's Nyquist: stored-luma standard deviation
FIBRE_STD = 0.0045
#: POOLED INK.  Where the black is a pool on the red (the knob where the top-left
#: flourish's hook meets the rule), the reference shows a soft dark-maroon-to-black
#: wash - black at 0.3 - 0.8 over full red - not a black shape.  The frame's black
#: CONTOUR part is laid as that wash: the reference's own black field, sharpened back
#: through the source's point spread (Van Cittert), within this reach (mm) of the
#: traced pool
WASH_REACH_MM = 1.0
WASH_DECONV_ITERS = 4
#: THE POOL SITS ON THE RED.  Round the pool (not the rule's dry run-out) the wash is
#: kept only where the traced red is: the reference's pool is a dark-maroon knob with a
#: tight black rim, and the sharpened black field's reach onto the bare paper beside the
#: knob (the edge pixels' mix of black and paper) laid a grey-black smudge there
POOL_ON_RED = True
#: ...and this far (mm, Gaussian) past the red edge: the rim of black the reference shows
POOL_RIM_MM = 0.10
#: THE DRY RUN-OUT.  The black middle of the top rule is laid as a crisp stroke only
#: while it is at least this wide (mm); where it thins below that it has gone DRY -
#: the reference shows a soft black-to-grey fade there, not a hair - and that run is
#: laid as the same wash as the pool: the reference's own black field, sharpened back
#: through its point spread
RULE_DRY_WIDTH_MM = 0.20


# ===========================================================================
# 1.  The reference model: every field this module samples, at the source's grid
# ===========================================================================

@dataclass
class RefModel:
    L: PT.Layers
    unm: T.Unmixed
    traced: dict
    traced_sha256: str
    polys_mm: dict                 # layer -> [ (N, 2) card-mm polygons ]
    erase_mm: dict                 # layer -> crisp polygons erased from that layer
    soft_mm: dict                  # layer -> [(soft_px, polygons)] erased soft
    ink_mm: dict                   # layer -> spike outlines laid over the erased ink
    pool_weight: np.ndarray        # the pool's reach (0..1, source grid)
    wash_mm: list                  # black polygons laid as a pooled wash, not a shape
    stroke_black_mm: list          # the black rule strokes' body (laid solid, never bristled)
    shape_black_mm: list           # every black polygon laid as a crisp shape
    wash_field: np.ndarray         # black wash coverage at the source grid (sharpened)
    wash_weight: np.ndarray        # where the wash replaces the shape (0..1, source grid)
    wash_red: np.ndarray           # the red UNDER the pool (unmixed, sharpened), source grid
    group_polys_mm: dict           # (group, layer) -> polygons
    psf: dict                      # layer -> shapes rendered through the source PSF
    tone: dict                     # layer -> ink load inside shapes (0..1)
    resid: dict                    # layer -> residual ink outside shapes (0..1)
    red_rgb: np.ndarray            # local red, stored sRGB (H, W, 3)
    black_rgb: np.ndarray          # local black, stored sRGB (H, W, 3)
    paper_rgb: np.ndarray          # reference paper with the ink removed, stored sRGB
    orient: np.ndarray             # (H, W, 2): cos 2t, sin 2t of the stroke direction
    stats: dict


_MODEL: dict = {}


def _to_px(fit, p):
    x, y = fit.mm_to_px(p[:, 0], p[:, 1])
    return np.stack([x, y], 1)


def _fill_hierarchical(values: np.ndarray, weight: np.ndarray,
                       sigmas=(1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0)) -> np.ndarray:
    """Inpaint: keep ``values`` where ``weight`` is 1, fill the rest from the nearest
    scale whose normalised convolution has support (coarse first, finer overwrites)."""
    w = weight.astype(np.float64)
    out = None
    for s in sigmas[::-1]:
        est = T.norm_conv(values, w, s, np.nan)
        sup = T.gauss_blur(w, s)
        if out is None:
            out = np.where(np.isfinite(est), est, np.nanmean(values[weight > 0], 0))
            continue
        a = np.clip((sup - 0.05) / 0.25, 0.0, 1.0)
        if values.ndim == 3:
            a = a[..., None]
        out = np.where(np.isfinite(est), out * (1 - a) + np.nan_to_num(est) * a, out)
    if values.ndim == 3:
        out = np.where(weight[..., None] > 0, values, out)
    else:
        out = np.where(weight > 0, values, out)
    return out


CARD_CLIP_MM = 8.05


def octagon_edge_distance(xm, ym):
    """Signed distance (mm, positive inside) to the card's octagon: four sides, four
    45 deg chamfers of ``CARD_CLIP_MM``."""
    d = np.minimum(np.minimum(xm, PT.CARD_W_MM - xm), np.minimum(ym, PT.CARD_H_MM - ym))
    for cx, cy, sx, sy in ((0, 0, 1, 1), (PT.CARD_W_MM, 0, -1, 1),
                           (0, PT.CARD_H_MM, 1, -1), (PT.CARD_W_MM, PT.CARD_H_MM, -1, -1)):
        d = np.minimum(d, ((xm - cx) * sx + (ym - cy) * sy - CARD_CLIP_MM) / math.sqrt(2.0))
    return d


def reference_model() -> RefModel:
    """Build (once per process) every source-grid field the face is made from."""
    traced_path = PT.TRACED_JSON
    with open(traced_path, "rb") as fh:
        tsha = hashlib.sha256(fh.read()).hexdigest()
    key = tsha
    if key in _MODEL:
        return _MODEL[key]
    traced = PT.load_traced(traced_path, verify_source=True)
    src = T.read_source()
    if src.sha256 != traced["provenance"]["source_sha256"]:
        raise PT.TracedSourceMismatch("reference on disk does not match the traced shapes")
    fit = T.fit_card(src)
    ak, behind, unm = T.ink_layers(src, fit)
    H, W = ak.shape
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    xm, ym = fit.px_to_mm(xx, yy)
    inside = (xm > 0.0) & (xm < PT.CARD_W_MM) & (ym > 0.0) & (ym < PT.CARD_H_MM)
    dens = {}
    for name, a in (("black", ak), ("red", behind)):
        core = T.erode(a > 0.5, 1)
        dens[name] = np.clip(T.norm_conv(a, core.astype(np.float64), 1.5, 0.97), 0.6, 1.0)
    L = PT.Layers(src=src, fit=fit, black=ak, red=unm.alpha_r, red_behind=behind,
                  density=dens, xm=xm, ym=ym, inside=inside)

    polys_mm = {"black": [], "red": []}
    erase_mm = {"black": [], "red": []}
    soft_mm = {"black": [], "red": []}
    ink_mm = {"black": [], "red": []}
    gpolys = {}
    wash_mm, stroke_black_mm, shape_black_mm, pool_mm = [], [], [], []
    for g in traced["groups"]:
        ps = PT.group_polys_mm(g, step_mm=0.01)
        gpolys[(g["group"], g["layer"])] = ps
        polys_mm[g["layer"]] += ps
        erase_mm[g["layer"]] += PT.knockout_polys_mm(g)
        soft_mm[g["layer"]] += PT.soft_knockouts_mm(g)
        ink_mm[g["layer"]] += PT.ink_polys_mm(g)
        if g["group"] == PT.FRAME and g["layer"] == "black":
            # the pool (contour part) and the dry run-out are washes; the body is a shape
            pool_mm += PT.contour_only_polys_mm(g, step_mm=0.01)
            wash_mm += PT.contour_only_polys_mm(g, step_mm=0.01)
            for r in g.get("strokes_mm", []):
                c = np.asarray(r["centre_mm"], np.float64)
                w = np.asarray(r["width_mm"], np.float64)
                gap = PT.RULE_GAP_WIDTH_PX / 3.917 * 0.999
                body = PT._orient(PT.stroke_polys(c, np.where(w >= RULE_DRY_WIDTH_MM, w, 0.0), gap),
                                  r.get("winding", 1.0))
                dry = PT._orient(PT.stroke_polys(c, np.where(w < RULE_DRY_WIDTH_MM, w, 0.0), gap),
                                 r.get("winding", 1.0))
                stroke_black_mm += body
                shape_black_mm += body
                wash_mm += dry
        elif g["layer"] == "black":
            shape_black_mm += ps

    # distance of every source pixel inside the card's octagon from its edge, mm
    clip = 8.05
    edge_d = np.minimum(np.minimum(xm, PT.CARD_W_MM - xm), np.minimum(ym, PT.CARD_H_MM - ym))
    for cx, cy, sx, sy in ((0, 0, 1, 1), (PT.CARD_W_MM, 0, -1, 1),
                           (0, PT.CARD_H_MM, 1, -1), (PT.CARD_W_MM, PT.CARD_H_MM, -1, -1)):
        edge_d = np.minimum(edge_d, ((xm - cx) * sx + (ym - cy) * sy - clip) / math.sqrt(2.0))
    ppmm_s = fit.ppmm

    psf, tone, resid = {}, {}, {}
    stats = {}
    for layer, obs in (("black", ak), ("red", behind)):
        box = PT.compose_coverage(
            lambda ps: T.fill_polys([_to_px(fit, q) for q in ps], H, W, ss=16),
            polys_mm[layer], erase_mm[layer], soft_mm[layer], ink_mm[layer])
        p = T.gauss_blur(box, T.SOURCE_PSF_SIGMA_PX)
        psf[layer] = p
        # TONE: observed ink over the shapes' prediction, where the shapes are solid
        # enough for the ratio to mean something, spread smoothly to every pixel
        wgt = np.where(p > 0.5, p * p, 0.0)
        ratio = np.clip(obs / np.maximum(p, 1e-6), 0.0, 1.0)
        tn = T.norm_conv(ratio, wgt, 0.8, np.nan)
        tn2 = T.norm_conv(ratio, wgt, 3.0, 0.97)
        tn = np.where(np.isfinite(tn), tn, tn2)
        tone[layer] = np.clip(tn, 0.0, 1.0)
        # RESIDUAL: ink the shapes do not explain.  Only where it can be a brush's dry
        # streak: clear of a shape's own edge (the edge's blur is the shape's, not
        # extra ink), within RESID_REACH_MM of that layer's ink (a streak trails off a
        # stroke; a stain in the middle of the paper is paper), clear of the card's
        # aged edge (the reference's brown edge staining unmixes as a little red and
        # is PAPER - it goes into the paper below, not into the ink), above the
        # unmixing's noise, and in clusters (an isolated pixel is the paper's tooth).
        r = np.clip(obs - p * dens[layer], 0.0, 1.0)
        floor = RESID_FLOOR[layer]
        far = np.clip((RESID_PSF_MAX - p) / (RESID_PSF_MAX * 0.6), 0.0, 1.0)
        keep = np.clip((r - floor) / floor, 0.0, 1.0)
        reach = T.dilate(p > 0.5, int(round(RESID_REACH_MM[layer] * ppmm_s)))
        on = (r > floor) & reach & (edge_d > RESID_EDGE_MM) & inside
        nb = sum(np.roll(np.roll(on, dy, 0), dx, 1).astype(np.int32)
                 for dy in (-1, 0, 1) for dx in (-1, 0, 1))
        clustered = T.dilate(on & (nb >= 3), 1) & on
        resid[layer] = np.where(clustered, r * far * keep, 0.0)
        stats[layer] = {
            "tone_p05_p50_in_shapes": [round(float(v), 3) for v in
                                       np.percentile(tone[layer][p > 0.5], [5, 50])],
            "resid_px_over_0.1": int((resid[layer] > 0.1).sum()),
            "resid_ink_px": round(float(resid[layer].sum()), 1),
            "resid_rejected_ink_px": round(float((r * far * keep)[~clustered & inside].sum()), 1),
            "shape_ink_px": round(float((p * dens[layer]).sum()), 1),
        }

    rgb = src.rgb
    # LOCAL INK COLOURS, stored sRGB.  Red: the mean colour of the pure red cores within
    # ~0.25 mm (sigma 0.9 px), so the ring's load mottling, the dark pooled frame red and
    # the seal's panel keep their own values; where no core is that near, the
    # unmixing's own local red endmember (2.5 / 8 px), which is what the reference's red
    # pixels were unmixed against.  Black: see build_front_traced (the endmember).
    rcore = (behind > 0.93) & (ak < 0.05) & unm.red_first & inside
    red_fine = T.norm_conv(rgb, rcore.astype(np.float64), 0.9, np.nan)
    red_sup = T.gauss_blur(rcore.astype(np.float64), 0.9)
    a_ = np.clip((red_sup - 0.02) / 0.10, 0.0, 1.0)[..., None]
    red_rgb = np.clip(np.where(np.isfinite(red_fine), red_fine * a_ + unm.red * (1 - a_),
                               unm.red), 0.0, 1.0)
    kcore = (ak > 0.93) & inside
    black_rgb = np.clip(T.norm_conv(rgb, kcore.astype(np.float64), 2.0,
                                    np.array(T.BLACK_STORED)), 0.0, 1.0)

    # PAPER with the ink removed: every card pixel the ink model does not claim is
    # paper and is kept EXACTLY (staining, specks, the aged edge band included); the
    # pixels under and beside the traced shapes and the kept residual are inpainted
    card_in = edge_d > PAPER_EDGE_KEEP_MM
    claimed = (psf["black"] > 0.02) | (psf["red"] > 0.02)         | (resid["black"] > 0.0) | (resid["red"] > 0.0)
    paper_px = card_in & ~T.dilate(claimed, 1)
    paper = _fill_hierarchical(rgb, paper_px)
    # NOTE ON THE CUT EDGE.  The reference draws a thin dark line round the card that
    # lies just OUTSIDE the edge fitted by warmth (fit_card): a deconvolution that forces
    # it inside the card saturates (A 0.95, lambda 0.08 mm) and made the photographed trim
    # worse, not better.  It is the card's silhouette, which the mesh edge, its rim and
    # its shadow carry in the render; the texture's outer 0.4 mm is extrapolated paper.

    # STROKE ORIENTATION: structure tensor of the ink, as doubled-angle components
    ink = T.gauss_blur(np.clip(ak + behind, 0, 1), 1.0)
    gy, gx = np.gradient(ink)
    jxx = T.gauss_blur(gx * gx, 2.5); jyy = T.gauss_blur(gy * gy, 2.5)
    jxy = T.gauss_blur(gx * gy, 2.5)
    # gradient angle phi; the stroke runs at phi + 90 deg, i.e. doubled angle + 180
    c2 = -(jxx - jyy); s2 = -(2 * jxy)
    mag = np.hypot(c2, s2)
    wv = np.clip(mag / (np.percentile(mag[mag > 0], 60) + 1e-12), 0.0, 1.0)
    # where there is no structure the paper fibre runs down the card (theta 90 deg)
    c2 = np.where(mag > 0, c2 / np.maximum(mag, 1e-12), -1.0) * wv + (-1.0) * (1 - wv)
    s2 = np.where(mag > 0, s2 / np.maximum(mag, 1e-12), 0.0) * wv
    orient = np.stack([c2, s2], -1)

    # POOLED WASH: the observed black near the traced pool, sharpened back through the
    # source's footprint (pixel box ~ Gaussian 0.29 px, with the PSF's 0.4 px) so that
    # photographing it again gives back what the reference shows, not a softer pool
    wash_weight = np.zeros((H, W))
    wash_field = np.zeros((H, W))
    wash_red = np.zeros((H, W))
    pool_weight = np.zeros((H, W))
    if pool_mm and POOL_ON_RED:
        pbox = T.fill_polys([_to_px(fit, p) for p in pool_mm], H, W, ss=16) > 0.02
        preach = T.dilate(pbox, int(round(WASH_REACH_MM * ppmm_s)) + 2)
        pool_weight = np.clip(T.gauss_blur(preach.astype(np.float64), 0.7) * 1.6 - 0.3, 0.0, 1.0)
    if wash_mm:
        wbox = T.fill_polys([_to_px(fit, p) for p in wash_mm], H, W, ss=16) > 0.02
        reach = T.dilate(wbox, int(round(WASH_REACH_MM * ppmm_s)))
        wash_weight = np.clip(T.gauss_blur(reach.astype(np.float64), 0.7) * 1.6 - 0.3, 0.0, 1.0)
        obs_k = np.where(T.dilate(reach, 2), ak, 0.0)
        sig = math.hypot(T.SOURCE_PSF_SIGMA_PX, 0.29)
        est = obs_k.copy()
        for _ in range(WASH_DECONV_ITERS):
            est = np.clip(est + (obs_k - T.gauss_blur(est, sig)), 0.0, 1.0)
        # support: only where the reference itself has black (a sharpened field rings
        # a little past its edge, which spilt a grey smudge onto the paper round the pool)
        wash_field = est * T.dilate(obs_k > 0.03, 1)
        # the red the pool lies on: the unmixing's red with the black lifted, sharpened
        # the same way (the pool's rim is maroon, i.e. black over red, not black on paper)
        obs_r = np.where(T.dilate(reach, 2), behind, 0.0)
        est = obs_r.copy()
        for _ in range(WASH_DECONV_ITERS):
            est = np.clip(est + (obs_r - T.gauss_blur(est, sig)), 0.0, 1.0)
        wash_red = est * T.dilate(obs_r > 0.03, 1)
    stats["wash_px"] = int((wash_weight > 0.5).sum())
    stats["erase_polys"] = {k: len(v) for k, v in erase_mm.items()}
    stats["soft_erase_sets"] = {k: len(v) for k, v in soft_mm.items()}
    stats["spike_ink_polys"] = {k: len(v) for k, v in ink_mm.items()}
    stats["pool_px"] = int((pool_weight > 0.5).sum())
    stats["paper_px_kept"] = int(paper_px.sum())
    stats["paper_detail_luma_std"] = round(float(
        ((rgb - T.norm_conv(rgb, paper_px.astype(float), 3.0, [0.96, 0.89, 0.75]))
         @ np.array([0.2126, 0.7152, 0.0722]))[paper_px].std()), 5)
    m = RefModel(L=L, unm=unm, traced=traced, traced_sha256=tsha, polys_mm=polys_mm,
                 erase_mm=erase_mm, soft_mm=soft_mm, ink_mm=ink_mm, pool_weight=pool_weight,
                 wash_mm=wash_mm, stroke_black_mm=stroke_black_mm,
                 shape_black_mm=shape_black_mm,
                 wash_field=wash_field, wash_weight=wash_weight, wash_red=wash_red,
                 group_polys_mm=gpolys, psf=psf, tone=tone, resid=resid, red_rgb=red_rgb,
                 black_rgb=black_rgb, paper_rgb=paper, orient=orient, stats=stats)
    _MODEL[key] = m
    return m


# ===========================================================================
# 2.  Sampling source-grid fields at texture pixels
# ===========================================================================

def _prefilter(f: np.ndarray) -> np.ndarray:
    return T._bspline_prefilter(T._bspline_prefilter(f, 0), 1)


def _bspline_w(t):
    """Cubic B-spline weights for taps at offsets -1, 0, 1, 2 given fraction t."""
    t2 = t * t; t3 = t2 * t
    w0 = (1 - t) ** 3 / 6.0
    w1 = (4 - 6 * t2 + 3 * t3) / 6.0
    w2 = (1 + 3 * t + 3 * t2 - 3 * t3) / 6.0
    w3 = t3 / 6.0
    return (w0, w1, w2, w3)


def sample_fields(coef: np.ndarray, px: np.ndarray, py: np.ndarray) -> np.ndarray:
    """Cubic B-spline interpolation of prefiltered fields ``coef`` (C, H, W) at continuous
    source coordinates (px, py) (pixel centres at +0.5), mirror-clamped at the borders."""
    C, H, W = coef.shape
    x = px - 0.5; y = py - 0.5
    ix = np.floor(x).astype(np.int64); iy = np.floor(y).astype(np.int64)
    wx = _bspline_w(x - ix); wy = _bspline_w(y - iy)
    out = np.zeros((C,) + px.shape, np.float64)
    for a in range(4):
        yi = np.clip(iy + a - 1, 0, H - 1)
        for b in range(4):
            xi = np.clip(ix + b - 1, 0, W - 1)
            w = wy[a] * wx[b]
            out += coef[:, yi, xi] * w[None]
    return out


def texture_to_source(fit, ppmm: float, pad_mm: float, H: int, W: int):
    """Continuous source coordinates of every texture pixel centre."""
    ys = (np.arange(H, dtype=np.float64) + 0.5) / ppmm - pad_mm
    xs = (np.arange(W, dtype=np.float64) + 0.5) / ppmm - pad_mm
    xm, ym = np.meshgrid(xs, ys)
    return fit.mm_to_px(xm, ym), (xm, ym)


def _upsample2(a: np.ndarray, H: int, W: int) -> np.ndarray:
    """Base-grid field -> supersampled grid (factor s), pixel-centre aligned bilinear."""
    h, w = a.shape[-2:]
    sy = H / h; sx = W / w
    yc = (np.arange(H) + 0.5) / sy - 0.5
    xc = (np.arange(W) + 0.5) / sx - 0.5
    iy = np.clip(np.floor(yc).astype(np.int64), 0, h - 2); fy = np.clip(yc - iy, 0, 1)
    ix = np.clip(np.floor(xc).astype(np.int64), 0, w - 2); fx = np.clip(xc - ix, 0, 1)
    top = a[..., iy, :][..., ix] * (1 - fx) + a[..., iy, :][..., ix + 1] * fx
    bot = a[..., iy + 1, :][..., ix] * (1 - fx) + a[..., iy + 1, :][..., ix + 1] * fx
    return top * (1 - fy[:, None]) + bot * fy[:, None]


# ===========================================================================
# 3.  Bristles: a partial value as crisp marks along the stroke
# ===========================================================================

def _lattice_noise(lat: np.ndarray, u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Value noise on a periodic lattice at continuous (u, v), smootherstep weights."""
    gh, gw = lat.shape
    iu = np.floor(u).astype(np.int64); iv = np.floor(v).astype(np.int64)
    fu = u - iu; fv = v - iv
    fu = fu * fu * fu * (fu * (fu * 6 - 15) + 10)
    fv = fv * fv * fv * (fv * (fv * 6 - 15) + 10)
    i0 = iv % gh; i1 = (iv + 1) % gh; j0 = iu % gw; j1 = (iu + 1) % gw
    a = lat[i0, j0] * (1 - fu) + lat[i0, j1] * fu
    b = lat[i1, j0] * (1 - fu) + lat[i1, j1] * fu
    return a * (1 - fv) + b * fv


def bristle_field(seed: int, xm: np.ndarray, ym: np.ndarray, orient_c2: np.ndarray,
                  orient_s2: np.ndarray) -> np.ndarray:
    """A UNIFORM [0, 1) field of bristle streaks: long along the local stroke direction,
    hair-wide across it.  Thresholding it at a value v covers a fraction v of the area,
    so a partial tone becomes crisp marks of exactly the same mean.

    The direction is constant over ORIENT_TILE_MM tiles and the four nearest tiles'
    fields are blended - rotating the coordinates per pixel instead would compress the
    streaks wherever the direction turns."""
    rng = np.random.default_rng([int(seed), 0xB215])
    lat = rng.random((4096, 512))
    lat2 = rng.random((4096, 512))
    t = ORIENT_TILE_MM
    gx = xm / t - 0.5; gy = ym / t - 0.5
    ix0 = np.floor(gx).astype(np.int64); iy0 = np.floor(gy).astype(np.int64)
    fx = gx - ix0; fy = gy - iy0
    # tile orientations from the per-pixel field, averaged per tile centre
    theta_c = 0.5 * np.arctan2(orient_s2, orient_c2)
    acc = np.zeros_like(xm)
    wsum = np.zeros_like(xm)
    for dy in (0, 1):
        for dx in (0, 1):
            ty = iy0 + dy; tx = ix0 + dx
            w = (fx if dx else 1 - fx) * (fy if dy else 1 - fy)
            w = w * w * (3 - 2 * w)          # smoother blend
            # coordinates are taken relative to the tile's own centre, so the local
            # direction turning across a tile only skews a streak by |p| * dtheta
            # (at most ~0.1 mm over the ring's curvature), never compresses the field
            th = theta_c
            c, s = np.cos(th), np.sin(th)
            ox = (tx * 7919 + ty * 104729) % 4096
            oy = (tx * 15485863 + ty * 32452843) % 512
            px_ = xm - (tx + 0.5) * t; py_ = ym - (ty + 0.5) * t
            along = (px_ * c + py_ * s) / BRISTLE_ALONG_MM
            across = (-px_ * s + py_ * c) / BRISTLE_ACROSS_MM
            n = (_lattice_noise(lat, along + oy, across + ox) * 0.7
                 + _lattice_noise(lat2, along * 2.1 + ox, across * 0.47 + oy) * 0.3)
            acc += w * n
            wsum += w
    n = acc / np.maximum(wsum, 1e-12)
    # rank-equalise to a uniform distribution (deterministic: stable sort)
    flat = n.ravel()
    order = np.argsort(flat, kind="stable")
    u = np.empty_like(flat)
    u[order] = (np.arange(flat.size) + 0.5) / flat.size
    return u.reshape(n.shape)


def crisp(value: np.ndarray, field: np.ndarray, edge: float = BRISTLE_EDGE) -> np.ndarray:
    """Crisp marks covering, on average, EXACTLY ``value`` of the area for a uniform
    ``field``: the ramp is scaled by (1 + edge) so 0 gives no ink and 1 gives solid ink,
    with no speckle floor and no ceiling short of 1."""
    return np.clip((value - field) * ((1.0 + edge) / edge) + 0.5, 0.0, 1.0)


# ===========================================================================
# 4.  The text report (the columns' character boxes, from the traced shapes)
# ===========================================================================

SLOTS = (("upper_left", "col_TL", "火遁術"),
         ("upper_right", "col_TR", "爆炎陣"),
         ("lower_right", "col_BR", "焼尽"),
         ("lower_centre", "col_BC", "瞬業"),
         ("small_seal", "small_seal", "火道"))


def text_report(model: RefModel, ppmm: float = 10.0) -> dict:
    """Per slot, per character: the ink box of the traced glyph (centre, width, height).

    Each column's traced ink is split into its characters at the widest gaps of its
    row projection (n characters -> the n - 1 widest gaps)."""
    out = {}
    for slot, group, chars in SLOTS:
        layer = "red" if slot == "small_seal" else "black"
        polys = model.group_polys_mm.get((group, layer), [])
        if not polys:
            continue
        allp = np.concatenate(polys)
        x0, y0 = allp.min(0) - 0.5; x1, y1 = allp.max(0) + 0.5
        if slot == "small_seal":
            # the seal's glyphs sit inside its box; the box is part of the frame group
            x0, y0, x1, y1 = 56.2, 137.0, 62.8, 150.6
        Hh = int(math.ceil((y1 - y0) * ppmm)); Ww = int(math.ceil((x1 - x0) * ppmm))
        cov = T.fill_polys([(p - [x0, y0]) * ppmm for p in polys], Hh, Ww, ss=4) > 0.5
        rows_ink = cov.sum(1)
        on = rows_ink > 0
        runs = PT._runs(on)
        n = len(chars)
        if len(runs) < n:
            cuts = [runs[0][0] + (runs[-1][1] - runs[0][0]) * k // n for k in range(1, n)]
        else:
            gaps = sorted(((runs[i + 1][0] - runs[i][1], runs[i][1], runs[i + 1][0])
                           for i in range(len(runs) - 1)), reverse=True)[:n - 1]
            cuts = sorted((a + b) // 2 for _, a, b in gaps)
        edges = [0] + cuts + [Hh]
        rows = []
        for k, ch in enumerate(chars):
            sub = cov[edges[k]:edges[k + 1]]
            ys, xs = np.nonzero(sub)
            if len(ys) == 0:
                continue
            gy0 = (edges[k] + ys.min()) / ppmm + y0; gy1 = (edges[k] + ys.max() + 1) / ppmm + y0
            gx0 = xs.min() / ppmm + x0; gx1 = (xs.max() + 1) / ppmm + x0
            rows.append({"char": "U+%04X" % ord(ch),
                         "centre_mm": [round(0.5 * (gx0 + gx1), 3), round(0.5 * (gy0 + gy1), 3)],
                         "ink_w_mm": round(gx1 - gx0, 3), "ink_h_mm": round(gy1 - gy0, 3),
                         "source": "traced (%s)" % group})
        out[slot] = rows
    return out


# ===========================================================================
# 5.  The face
# ===========================================================================

def element_derivation() -> dict:
    d = "traced: paperbomb_traced.json group %s, rasterised at the texture grid; tone and " \
        "residual dry-brush sampled from the reference, laid as crisp bristle marks"
    return {
        "emblem": d % "'emblem'",
        "centre": d % "'centre'",
        "ring": d % "'ring'",
        "seal_big": d % "'seal_big'" + " (the white tall curling flame is its knocked-out holes; "
                    "the two corner sparkles are sub-pixel knock-outs fitted by analysis by "
                    "synthesis, paperbomb_finefit)",
        "small_seal": d % "'small_seal' + 'frame'" + " (box and 火道 traced; the slots between "
                      "the bars of 道's 目 are sub-pixel knock-outs fitted by analysis by "
                      "synthesis, paperbomb_finefit)",
        "chain": d % "'chain'" + " (leaves are traced tapered shapes)",
        "corners": d % "'frame' (contour part)" + "; the black pool on the top-left knob is "
                   "the reference's own black field laid as a wash (sharpened back through "
                   "the source PSF), not a shape",
        "rules": "traced: paperbomb_traced.json group 'frame' strokes (centreline + width, "
                 "gaps only where the reference lifts; the black middle run integrated over "
                 "the whole rule band so it thins to a hair where the reference greys, laid "
                 "solid without bristles)",
        "columns": d % "'col_TL' / 'col_TR' / 'col_BR' / 'col_BC'"
                   + " (no font on the machine is the user's hand: fontid_result.json)",
        "ink_colour": "sampled: the reference's local red (unmixing endmember) and local "
                      "black core colour",
        "paper": "derived from the reference with the ink removed (kept where bare, "
                 "multi-scale inpaint under ink), cubic B-spline to the texture grid; "
                 "procedural fibre only above the reference's Nyquist",
    }


def build_front_traced(cfg, lay):
    """The printed face at ``cfg.px`` (supersampled), as a ``paperbomb_art.TagArt``."""
    from . import paperbomb_art as A

    model = reference_model()
    fit = model.L.fit
    px = cfg.px
    W, H = A.raster_size(cfg)
    s = int(cfg.supersample)
    card, outline = A._card_mask(cfg, lay, W, H)

    # --- source fields at the BASE grid (they are band-limited to 3.9 px/mm, so the
    # base grid at 12.9 px/mm over-samples them 3x and a bilinear step to the
    # supersampled grid loses nothing)
    Wb, Hb = int(round(W / s)), int(round(H / s))
    (spx, spy), (bxm, bym) = texture_to_source(fit, cfg.ppmm, cfg.pad_mm, Hb, Wb)
    chans = [model.tone["black"], model.resid["black"], model.tone["red"], model.resid["red"],
             model.red_rgb[..., 0], model.red_rgb[..., 1], model.red_rgb[..., 2],
             model.paper_rgb[..., 0], model.paper_rgb[..., 1], model.paper_rgb[..., 2],
             model.orient[..., 0], model.orient[..., 1],
             model.wash_field, model.wash_weight, model.wash_red, model.pool_weight]
    coef = np.stack([_prefilter(c) for c in chans], 0)
    base = np.empty((len(chans), Hb, Wb), np.float32)
    step = 256
    for r0 in range(0, Hb, step):
        base[:, r0:r0 + step] = sample_fields(coef, spx[r0:r0 + step], spy[r0:r0 + step])
    if s > 1:
        full = np.empty((len(chans), H, W), np.float32)
        for c in range(len(chans)):
            full[c] = _upsample2(base[c], H, W)
    else:
        full = base
    tone_k, res_k, tone_r, res_r = (np.clip(full[i], 0, 1) for i in range(4))
    red_rgb = np.clip(np.moveaxis(full[4:7], 0, -1), 0, 1)
    # black: the unmixing's own endmember.  The reference's black pixels were unmixed
    # against it, so compositing with it at the sampled coverage gives back the observed
    # colour, dry grey passages included (the core's own colour already has ~3 % paper
    # in it and would come out that much lighter)
    blk_rgb = np.array(T.BLACK_STORED, np.float32)[None, None, :]
    paper_st = np.clip(np.moveaxis(full[7:10], 0, -1), 0, 1)
    oc2, os2 = full[10], full[11]
    wash_f = np.clip(full[12], 0, 1)
    wash_w = np.clip(full[13], 0, 1)
    wash_r = np.clip(full[14], 0, 1)
    pool_w = np.clip(full[15], 0, 1)
    del full, base, coef

    # --- the traced shapes at the supersampled grid
    S = {}
    for layer in ("black", "red"):
        # black: the pool and the rule's dry run-out are laid as a wash below, not as shapes
        polys = model.shape_black_mm if layer == "black" else model.polys_mm[layer]
        cov = PT.compose_coverage(
            lambda ps: PT.rasterise_mm(ps, px, cfg.pad_mm, H, W, ss=4),
            polys, model.erase_mm[layer], model.soft_mm[layer], model.ink_mm[layer],
            blur_scale=px / fit.ppmm)
        S[layer] = cov.astype(np.float32)
    # the black rule strokes are laid at their sampled tone, never split into bristles:
    # their width already carries the dry run-out (it thins to a hair where the
    # reference greys), so a bristle split there frayed the end into a splay
    stroke_k = PT.rasterise_mm(model.stroke_black_mm, px, cfg.pad_mm, H, W, ss=4) \
        .astype(np.float32) if model.stroke_black_mm else np.zeros((H, W), np.float32)

    # --- bristles
    yy = ((np.arange(H, dtype=np.float64) + 0.5) / px - cfg.pad_mm)[:, None]
    xx = ((np.arange(W, dtype=np.float64) + 0.5) / px - cfg.pad_mm)[None, :]
    xm = np.broadcast_to(xx, (H, W)); ym = np.broadcast_to(yy, (H, W))
    field_k = bristle_field(cfg.seed, xm, ym, oc2, os2).astype(np.float32)
    field_r = bristle_field(cfg.seed + 1, xm, ym, oc2, os2).astype(np.float32)

    def layer_alpha(Sx, tone, res, fld, solid=None):
        # a crisp inner mark is laid at the solid tone, so its mean is the sampled tone
        inner = np.where(tone >= TONE_SOLID, tone,
                         crisp(np.clip(tone / TONE_SOLID, 0, 1), fld) * TONE_SOLID)
        if solid is not None:
            inner = np.where(solid > 0.0, tone, inner)
        outer = crisp(np.clip(res / TONE_SOLID, 0, 1), fld) * TONE_SOLID
        outer = np.where(res > 1e-4, outer, 0.0)
        return np.clip(Sx * inner + (1.0 - Sx) * outer, 0.0, 1.0).astype(np.float32)

    # the black residual inside the wash's reach belongs to the wash
    res_k = res_k * (1.0 - wash_w)
    res_k = np.where(stroke_k > 0.0, 0.0, res_k)
    # KNOCK-OUT WINDOWS (the seal's sparkles, the slots of 道): there the fitted erase
    # shapes carry every bit of paper the reference shows, so the red round them is laid
    # SOLID at full load - a sampled tone under the bristle split turned the leftover
    # sub-pixel deficit into ragged specks round the marks
    kowin = np.zeros((H, W), np.float32)
    kw_polys = []
    for g in model.traced["groups"]:
        for k in g.get("knockouts_mm", []):
            x0, y0, x1, y1 = k["window_mm"]
            kw_polys.append(np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], np.float64))
    if kw_polys:
        kowin = PT.rasterise_mm(kw_polys, px, cfg.pad_mm, H, W, ss=2).astype(np.float32)
        tone_r = np.where(kowin > 0.0, np.maximum(tone_r, 0.985), tone_r)
        res_r = res_r * (1.0 - kowin)
    # round the pool the wash lies only on the traced red and a hair past its edge (the
    # rim: POOL_RIM_MM), not on the paper beside it (see POOL_ON_RED)
    on_red = np.ones((H, W), np.float32)
    if (pool_w > 0.0).any():
        ys, xs = np.nonzero(pool_w > 0.0)
        m = int(math.ceil(4 * POOL_RIM_MM * px)) + 2
        y0, y1 = max(0, ys.min() - m), min(H, ys.max() + m + 1)
        x0, x1 = max(0, xs.min() - m), min(W, xs.max() + m + 1)
        near = np.clip(T.gauss_blur(np.clip(S["red"][y0:y1, x0:x1], 0.0, 1.0).astype(np.float64),
                                    POOL_RIM_MM * px) * 2.0, 0.0, 1.0)
        on_red[y0:y1, x0:x1] = 1.0 - pool_w[y0:y1, x0:x1] * (1.0 - near)
    ak = layer_alpha(S["black"], tone_k, res_k, field_k, solid=stroke_k)
    ak = np.maximum(ak, (wash_w * wash_f * on_red).astype(np.float32))
    arb = layer_alpha(S["red"], tone_r, res_r, field_r, solid=kowin if kw_polys else None)
    arb = np.maximum(arb, (wash_w * wash_r * on_red).astype(np.float32))
    del field_k, field_r

    # --- paper: the reference's, plus a fibre band above its Nyquist
    rng = A._rng(cfg.seed, "tracedart_fibre")
    fib = A.noise(rng, H, W, max(1.5, 0.30 * px), aniso=0.28) - 0.5
    fib = fib - A.blur(fib, max(0.8, 0.26 * px))            # keep only > ~2 cycles/mm
    fib2 = A.noise(rng, H, W, max(1.5, 0.11 * px)) - 0.5
    fib2 = fib2 - A.blur(fib2, max(0.8, 0.12 * px))
    hf = fib * 1.0 + fib2 * 0.6
    hf = hf / max(float(hf.std()), 1e-9) * FIBRE_STD
    paper_st = np.clip(paper_st * (1.0 + hf[..., None].astype(np.float32)), 0, 1)

    # --- composite in the reference's space: paper (1 - k - r) + R r + K k, red behind
    ar = arb * (1.0 - ak)
    comp = (paper_st * (1.0 - ak - ar)[..., None] + red_rgb * ar[..., None]
            + blk_rgb * ak[..., None])
    pal = A.palette_for(cfg)
    floor_lin, ceil_lin = A.ink_floor(cfg)
    rgb = np.clip(T.srgb_to_linear(comp), floor_lin, ceil_lin).astype(np.float32)
    paper_lin = np.clip(T.srgb_to_linear(paper_st), floor_lin, ceil_lin).astype(np.float32)

    # --- roughness, relief: the sheet's procedural fields (paper_ground) carry the
    # fibre relief, creases and roughness; only its colour is replaced by the reference's
    paper = A.paper_ground(cfg, lay, W, H, card, side="front")
    red = A.Ink(H, W); black = A.Ink(H, W)
    red.a = arb; red.d = np.ones_like(arb)
    black.a = ak; black.d = np.ones_like(ak)
    rough = (paper["rough"] * (1.0 - ak - ar) + pal.rough_red_wet * ar
             + pal.rough_black_wet * ak)
    rough = np.clip(rough, 0.30, 0.98).astype(np.float32)
    relief = A._relief(paper, red, black, cfg, A._rng(cfg.seed, "relief_front"))
    fringe = A._fringe_field(cfg, lay, card, W, H)
    scorch = A._scorch_field(cfg, lay, W, H)
    ink_mask = np.maximum(arb, ak).astype(np.float32)

    art = A.TagArt(
        side="front", ppmm=cfg.ppmm, width=W, height=H,
        base_colour=rgb, paper_rgb=paper_lin, roughness=rough, relief=relief,
        card_mask=card, fringe=fringe, scorch=scorch, ink_mask=ink_mask,
        ink_black=black, ink_red=red, outline_mm=outline,
    )
    art.report = {
        "art_source": "traced",
        "tracedart": TRACEDART_VERSION,
        "traced_sha256": model.traced_sha256,
        "source_sha256": model.L.src.sha256,
        "text": text_report(model),
        "centre": {"source": "traced group 'centre'"},
        "seals": {"source": "traced groups 'seal_big', 'small_seal', 'frame'"},
        "ornaments": {"source": "traced groups 'frame', 'chain'"},
        "knockouts": [{"group": g["group"], "name": k["name"], "kind": k["kind"],
                       "loss": k["loss"]} for g in model.traced["groups"]
                      for k in g.get("knockouts_mm", [])],
        "wash": {"reach_mm": WASH_REACH_MM, "deconv_iters": WASH_DECONV_ITERS,
                 "px_source": model.stats.get("wash_px"), "pool_on_red": POOL_ON_RED},
        "spikes": [{"group": g["group"], "name": k["name"], "loss": k["loss"]}
                   for g in model.traced["groups"] for k in g.get("spikes_mm", [])],
        "model_stats": model.stats,
        "pad_mm": cfg.pad_mm, "supersample": cfg.supersample, "ink_floor": cfg.ink_floor,
        "paper_choice": ("derived from the reference, ink removed, + fibre band above its "
                         "Nyquist (FIBRE_STD %.4f stored luma)" % FIBRE_STD),
    }
    if cfg.supersample > 1:
        art = A._downsample(art, cfg.supersample)
    return art
