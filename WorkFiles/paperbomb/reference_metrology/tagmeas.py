# -*- coding: utf-8 -*-
"""Ink and colour metrology on a rectified tag.

Input: a rectified (H,W,3) array of STORED sRGB floats whose rectangle is exactly
the tag's paper rectangle. Output: a dict of numbers. No artwork leaves here.

Coordinate convention everywhere: u = x/W, v = y/H from the tag's top-left corner,
and millimetres on the shipped card via CARD_W_MM / CARD_H_MM.
"""
import numpy as np

import pngread as P
import metro as M

CARD_W_MM = 70.0
CARD_H_MM = 156.0


# ----------------------------------------------------------------- helpers
def _r(x, n=6):
    if x is None:
        return None
    if isinstance(x, (list, tuple)):
        return [_r(v, n) for v in x]
    try:
        v = float(x)
    except (TypeError, ValueError):
        return x
    if not np.isfinite(v):
        return None
    return round(v, n)


def colour_report(srgb_rows):
    """srgb_rows: (N,3) stored sRGB floats -> a full colour description."""
    a = np.asarray(srgb_rows, float).reshape(-1, 3)
    if a.shape[0] == 0:
        return {"n": 0}
    med = np.median(a, axis=0)
    mean = a.mean(axis=0)
    lin = P.srgb_to_linear(a)
    lin_med = np.median(lin, axis=0)
    h, s, v = P.rgb_to_hsv(a)
    # circular median for hue
    ang = np.radians(h)
    hm = np.degrees(np.arctan2(np.median(np.sin(ang)), np.median(np.cos(ang)))) % 360.0
    hdev = ((h - hm + 180) % 360) - 180
    return {
        "n": int(a.shape[0]),
        "stored_srgb_median_0_1": _r(med.tolist(), 5),
        "stored_srgb_median_8bit": [int(round(x * 255)) for x in med],
        "stored_srgb_hex": "#%02X%02X%02X" % tuple(int(round(np.clip(x, 0, 1) * 255)) for x in med),
        "stored_srgb_mean_0_1": _r(mean.tolist(), 5),
        "linear_median": _r(lin_med.tolist(), 6),
        "linear_mean": _r(lin.mean(axis=0).tolist(), 6),
        "linear_luma_median": _r(float(0.2126 * lin_med[0] + 0.7152 * lin_med[1] + 0.0722 * lin_med[2]), 6),
        "hsv_stored": {"h_deg": _r(hm, 3), "s": _r(float(np.median(s)), 5),
                       "v": _r(float(np.median(v)), 5)},
        "hsv_variation": {"h_deg_std": _r(float(np.std(hdev)), 3),
                          "h_deg_p5_p95": _r([float(np.percentile(hdev, 5) + hm),
                                              float(np.percentile(hdev, 95) + hm)], 3),
                          "s_std": _r(float(np.std(s)), 5),
                          "s_p5_p95": _r([float(np.percentile(s, 5)), float(np.percentile(s, 95))], 5),
                          "v_std": _r(float(np.std(v)), 5),
                          "v_p5_p95": _r([float(np.percentile(v, 5)), float(np.percentile(v, 95))], 5)},
        "stored_srgb_percentiles_8bit": {
            "p5": [int(round(x * 255)) for x in np.percentile(a, 5, axis=0)],
            "p95": [int(round(x * 255)) for x in np.percentile(a, 95, axis=0)]},
    }


# ----------------------------------------------------------------- core
class TagMeasure(object):
    def __init__(self, rect_srgb, name, native_px_per_mm, native_rect=None,
                 aspect_h_over_w=None):
        self.name = name
        self.rect = np.clip(np.asarray(rect_srgb, float)[..., :3], 0, 1)
        self.H, self.W = self.rect.shape[:2]
        self.native_ppmm = float(native_px_per_mm)
        self.native = native_rect
        self.aspect = aspect_h_over_w
        self.lin = P.srgb_to_linear(self.rect)
        self.h, self.s, self.v = P.rgb_to_hsv(self.rect)
        self.warm = self.rect[..., 0] - self.rect[..., 2]
        self.ppmm = self.W / CARD_W_MM          # rectified px per shipped mm
        self.out = {}

    # -- geometry of the paper support (the octagon inside the rectangle)
    def build_support(self, override=None):
        if override is not None:
            self.support = np.asarray(override, bool)
            how = "supplied analytically by the caller"
        else:
            sup0 = (self.warm > 0.10) | (self.v < 0.80)
            sup_r = np.zeros_like(sup0)
            for y in range(self.H):
                xs = np.flatnonzero(sup0[y])
                if xs.size:
                    sup_r[y, xs[0]:xs[-1] + 1] = True
            sup_c = np.zeros_like(sup0)
            for x in range(self.W):
                ys = np.flatnonzero(sup0[:, x])
                if ys.size:
                    sup_c[ys[0]:ys[-1] + 1, x] = True
            self.support = sup_r & sup_c
            how = "warm(R-B)>0.10 or value<0.80, row- and column-filled"
        self.d_edge = M.edt(self.support)          # px from the paper boundary
        self.sup_area = float(self.support.sum())
        # chamfer: how far the corner cut runs along each edge
        ch = {}
        try:
            rows = np.flatnonzero(self.support.any(axis=1))
            cols = np.flatnonzero(self.support.any(axis=0))
            r0, r1 = int(rows[0]), int(rows[-1])
            c0, c1 = int(cols[0]), int(cols[-1])
            xs_top = np.flatnonzero(self.support[r0])
            xs_bot = np.flatnonzero(self.support[r1])
            ys_lft = np.flatnonzero(self.support[:, c0])
            ys_rgt = np.flatnonzero(self.support[:, c1])
            ch = {
                "top_left_along_x_mm": _r((xs_top[0] - c0) / self.ppmm, 3),
                "top_right_along_x_mm": _r((c1 - xs_top[-1]) / self.ppmm, 3),
                "bottom_left_along_x_mm": _r((xs_bot[0] - c0) / self.ppmm, 3),
                "bottom_right_along_x_mm": _r((c1 - xs_bot[-1]) / self.ppmm, 3),
                "top_left_along_y_mm": _r((ys_lft[0] - r0) / self.ppmm, 3),
                "bottom_left_along_y_mm": _r((r1 - ys_lft[-1]) / self.ppmm, 3),
                "top_right_along_y_mm": _r((ys_rgt[0] - r0) / self.ppmm, 3),
                "bottom_right_along_y_mm": _r((r1 - ys_rgt[-1]) / self.ppmm, 3),
            }
            vals = [v for v in ch.values() if v is not None]
            ch["mean_mm"] = _r(float(np.mean(vals)), 3)
            ch["mean_frac_of_W"] = _r(float(np.mean(vals)) / CARD_W_MM, 5)
        except Exception:
            pass
        self.out["support"] = {
            "how_found": how,
            "area_frac_of_bounding_rect": _r(self.support.mean(), 5),
            "area_mm2": _r(self.sup_area / (self.ppmm ** 2), 2),
            "corner_chamfer": ch,
            "corner_chamfer_note": "the four corners are cut; the bounding rectangle "
                                   "is the paper rectangle, the support is the octagon. "
                                   "Every area fraction below is a fraction of the "
                                   "octagon, not of the rectangle.",
        }
        return self.support

    # -- iterative local paper field
    def build_paper_field(self, iters=3):
        blk = (self.v < 0.45) & (self.s < 0.55)
        red = (((self.h < 25) | (self.h > 330)) & (self.s > 0.55) & (self.v > 0.12))
        ink_rough = M.dilate((blk | red) & self.support, 4)
        paper = self.support & ~ink_rough
        r_coarse = 0.045 * self.W
        for i in range(iters):
            PCc = np.stack([M.masked_blur(self.lin[..., c], paper, r_coarse)[0]
                            for c in range(3)], -1)
            cG = self.lin[..., 1] / np.maximum(PCc[..., 1], 1e-5)
            cR = self.lin[..., 0] / np.maximum(PCc[..., 0], 1e-5)
            a = np.clip(1.0 - cG, 0, 1)
            rn = np.clip(cR - cG, -1, 1)
            paper = self.support & (a < 0.15) & (rn < 0.07)
        self.paper_mask = paper
        self.PC = PCc                                  # coarse local paper, LINEAR
        r_fine = max(2.0, 0.006 * self.W)
        self.PF = np.stack([M.masked_blur(self.lin[..., c], paper, r_fine)[0]
                            for c in range(3)], -1)    # fine paper, LINEAR
        self.cR = self.lin[..., 0] / np.maximum(self.PC[..., 0], 1e-5)
        self.cG = self.lin[..., 1] / np.maximum(self.PC[..., 1], 1e-5)
        self.cB = self.lin[..., 2] / np.maximum(self.PC[..., 2], 1e-5)
        self.alpha = np.clip(1.0 - self.cG, 0, 1)      # ink opacity vs green
        self.redness = np.clip(self.cR - self.cG, -1, 1)
        self.out["segmentation"] = {
            "method": "local paper field = masked box-blur of paper-classified pixels, "
                      "radius 4.5% of tag width, 3 refinement passes; ink opacity "
                      "alpha = 1 - linear_G / paper_field_G; redness = cR - cG",
            "paper_pixels_frac_of_support": _r(paper.sum() / self.sup_area, 5),
            "alpha_ink_threshold": 0.35,
            "redness_red_threshold": 0.12,
        }

    def build_masks(self):
        # "core" erosion: at least 0.20 mm AND at least 1.5 source pixels, so the
        # three sources are compared at the same real depth inside a stroke even
        # though V2 is 2.2x coarser than V1.
        self.core_r = max(0.20 * self.ppmm, 1.5 * (self.ppmm / self.native_ppmm))
        core_area = self.support & (self.d_edge > 0.30 * self.ppmm)   # drop 0.3 mm AA rim
        self.stat_area = core_area
        self.ink = core_area & (self.alpha > 0.35)
        self.black = self.ink & (self.redness <= 0.12)
        self.red = self.ink & (self.redness > 0.12)
        self.stat_n = float(core_area.sum())

    # ------------------------------------------------------- paper colour
    def measure_paper(self):
        pm = self.paper_mask & self.stat_area
        u = (np.arange(self.W) + 0.5) / self.W
        vv = (np.arange(self.H) + 0.5) / self.H
        U, V = np.meshgrid(u, vv)
        centre = pm & (np.abs(U - 0.5) < 0.22) & (np.abs(V - 0.5) < 0.22)
        if centre.sum() < 500:
            centre = pm & (np.abs(U - 0.5) < 0.30) & (np.abs(V - 0.5) < 0.30)
        dmm = self.d_edge / self.ppmm
        edge = pm & (dmm < 2.0)
        deep = pm & (dmm > 12.0)

        res = {
            "whole_tag_paper": colour_report(self.rect[pm]),
            "centre_44pct_box": colour_report(self.rect[centre]),
            "outer_2mm_band": colour_report(self.rect[edge]),
            "interior_beyond_12mm": colour_report(self.rect[deep]),
        }

        # --- edge darkening profile: paper luma vs distance from the paper edge
        lum = 0.2126 * self.PF[..., 0] + 0.7152 * self.PF[..., 1] + 0.0722 * self.PF[..., 2]
        plateau = float(np.median(lum[deep])) if deep.sum() > 200 else float(np.median(lum[pm]))
        bins = np.arange(0, 20.0, 0.5)
        prof = []
        for i in range(len(bins) - 1):
            m = pm & (dmm >= bins[i]) & (dmm < bins[i + 1])
            if m.sum() < 30:
                prof.append(None)
                continue
            prof.append({
                "d_mm": _r(0.5 * (bins[i] + bins[i + 1]), 3),
                "d_frac_of_W": _r(0.5 * (bins[i] + bins[i + 1]) / CARD_W_MM, 5),
                "luma_lin": _r(float(np.median(lum[m])), 6),
                "rel_to_plateau": _r(float(np.median(lum[m])) / plateau, 5),
                "srgb_8bit": [int(round(x * 255)) for x in np.median(self.rect[m], axis=0)],
            })
        def reach_at(level):
            for p in prof:
                if p and p["rel_to_plateau"] is not None and p["rel_to_plateau"] > level:
                    return p["d_mm"]
            return None
        first = next((p for p in prof if p), None)
        depth = (1.0 - first["rel_to_plateau"]) if first else None
        half = reach_at(1.0 - 0.5 * depth) if depth else None
        res["edge_darkening"] = {
            "plateau_luma_lin": _r(plateau, 6),
            "profile": prof,
            "depth_at_outer_0_5mm": _r(depth, 5),
            "depth_at_outer_0_5mm_pct": _r(100.0 * depth if depth else None, 2),
            "reach_mm_to_95pct": _r(reach_at(0.95), 3),
            "reach_mm_to_98pct": _r(reach_at(0.98), 3),
            "reach_mm_to_99pct": _r(reach_at(0.99), 3),
            "reach_frac_of_W_to_99pct": _r(reach_at(0.99) / CARD_W_MM
                                           if reach_at(0.99) else None, 5),
            "half_recovery_mm": _r(half, 3),
            "half_recovery_frac_of_W": _r(half / CARD_W_MM if half else None, 5),
            "shape": ("broad gentle vignette" if (half or 0) > 4.0
                      else "tight burnt rim"),
        }

        # --- evenness: per side and per corner
        sides = {}
        for nm, m in (("top", V < 0.25), ("bottom", V > 0.75),
                      ("left", U < 0.18), ("right", U > 0.82)):
            mm_ = pm & m & (dmm < 3.0)
            if mm_.sum() > 200:
                sides[nm] = {"luma_lin": _r(float(np.median(lum[mm_])), 6),
                             "rel_to_plateau": _r(float(np.median(lum[mm_])) / plateau, 5),
                             "srgb_8bit": [int(round(x * 255)) for x in np.median(self.rect[mm_], axis=0)]}
        vals = [s["rel_to_plateau"] for s in sides.values()]
        sides["spread_max_minus_min"] = _r(max(vals) - min(vals), 5) if vals else None
        sides["even"] = bool(vals and (max(vals) - min(vals)) < 0.05)
        res["edge_darkening_evenness"] = sides

        # --- global illumination gradient (plane fit to paper luma)
        ys, xs = np.nonzero(pm)
        A = np.vstack([xs / self.W, ys / self.H, np.ones(xs.size)]).T
        sol, *_ = np.linalg.lstsq(A, lum[pm], rcond=None)
        res["global_gradient"] = {
            "d_luma_per_tag_width": _r(float(sol[0]), 6),
            "d_luma_per_tag_height": _r(float(sol[1]), 6),
            "pct_across_width": _r(100.0 * sol[0] / plateau, 3),
            "pct_across_height": _r(100.0 * sol[1] / plateau, 3),
        }
        self.paper_luma = lum
        self.paper_plateau = plateau
        self.out["paper"] = res

    # ------------------------------------------------------- mottle/stains
    def measure_mottle(self):
        pm = self.paper_mask & self.stat_area
        lumF = self.paper_luma
        r_c = 0.045 * self.W
        lumC, _ = M.masked_blur(
            0.2126 * self.lin[..., 0] + 0.7152 * self.lin[..., 1] + 0.0722 * self.lin[..., 2],
            self.paper_mask, r_c)
        resid = np.where(pm, lumF / np.maximum(lumC, 1e-6) - 1.0, 0.0)
        rv = resid[pm]
        out = {
            "definition": "fine paper luma (blur 0.6% W) divided by coarse paper luma "
                          "(blur 4.5% W) minus 1; a fractional deviation of the paper "
                          "base, so +-0.05 means +-5% luma",
            "amplitude": {k: _r(v, 6) for k, v in M.stats(rv).items()},
            "rms_pct": _r(100.0 * float(np.sqrt(np.mean(rv ** 2))), 4),
            "p5_p95_pct": _r([100.0 * float(np.percentile(rv, 5)),
                              100.0 * float(np.percentile(rv, 95))], 4),
        }
        # spectrum on clean paper patches
        patches = self._clean_patches(pm, n=6, size=int(0.14 * self.W))
        specs = []
        for (y0, x0, sz) in patches:
            f, p, _ = M.radial_power(resid[y0:y0 + sz, x0:x0 + sz])
            specs.append(p)
        if specs:
            p = np.mean(np.array(specs), axis=0)
            f, _, _ = M.radial_power(resid[patches[0][0]:patches[0][0] + patches[0][2],
                                            patches[0][1]:patches[0][1] + patches[0][2]])
            keep = f > 0.004
            fk, pk = f[keep], p[keep]
            # correlation length: radially averaged autocorrelation -> 1/e crossing.
            # The mottle spectrum is red, so a "peak frequency" is meaningless;
            # the correlation length is the scale of one blotch.
            cl = []
            for (y0, x0, sz) in patches:
                q = resid[y0:y0 + sz, x0:x0 + sz]
                q = q - q.mean()
                F = np.abs(np.fft.fft2(q)) ** 2
                ac = np.fft.fftshift(np.real(np.fft.ifft2(F)))
                ac = ac / ac.max()
                cy, cx = sz // 2, sz // 2
                yy, xx = np.mgrid[0:sz, 0:sz]
                rr = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
                nb = sz // 2
                idx = np.clip(rr.astype(int), 0, nb - 1)
                cnt = np.bincount(idx.ravel(), minlength=nb)
                tot = np.bincount(idx.ravel(), weights=ac.ravel(), minlength=nb)
                prof = tot / np.maximum(cnt, 1)
                below = np.flatnonzero(prof < np.exp(-1.0))
                if below.size:
                    i0 = int(below[0])
                    if i0 > 0:
                        t = ((prof[i0 - 1] - np.exp(-1.0))
                             / max(prof[i0 - 1] - prof[i0], 1e-9))
                        cl.append((i0 - 1 + t) / self.ppmm)
            out["spectrum"] = {
                "n_patches": len(patches),
                "patch_size_frac_of_W": _r(patches[0][2] / self.W, 4),
                "patch_size_mm": _r(patches[0][2] / self.ppmm, 3),
                "correlation_length_mm": _r(float(np.median(cl)) if cl else None, 4),
                "correlation_length_frac_of_W": _r(
                    float(np.median(cl)) / CARD_W_MM if cl else None, 5),
                "correlation_length_note": "radius at which the paper-residual "
                                           "autocorrelation falls to 1/e: the size of "
                                           "one blotch, not a periodic wavelength",
                "slope_loglog": _r(self._loglog_slope(fk, pk), 4),
                "spectrum_shape": "red (power falls with frequency); there is no "
                                  "periodic peak, so band powers are the useful "
                                  "description",
                "band_power_fraction": self._band_powers(fk, pk),
            }
        # distinct stains
        st = {}
        for thr in (0.03, 0.06, 0.10):
            m = pm & (resid < -thr)
            m = M.opening(m, 1.5)
            lab, n = M.label_cc(m)
            cs = M.cc_stats(lab, n)
            cs = [c for c in cs if c["area_px"] > (0.4 * self.ppmm) ** 2]
            d = np.array([c["equiv_diam_px"] / self.ppmm for c in cs]) if cs else np.array([])
            st["darker_than_%d_pct" % int(thr * 100)] = {
                "count": len(cs),
                "count_per_1000mm2": _r(len(cs) / (self.sup_area / self.ppmm ** 2) * 1000.0, 3),
                "total_area_frac_of_tag": _r(sum(c["area_px"] for c in cs) / self.stat_n, 5),
                "equiv_diam_mm": {k: _r(v, 4) for k, v in M.stats(d).items()} if d.size else None,
                "equiv_diam_frac_of_W": _r(float(np.median(d)) / CARD_W_MM, 5) if d.size else None,
                "elongation_median": _r(float(np.median([c["elongation"] for c in cs])), 3) if cs else None,
            }
        for thr in (0.03, 0.06):
            m = pm & (resid > thr)
            m = M.opening(m, 1.5)
            lab, n = M.label_cc(m)
            cs = [c for c in M.cc_stats(lab, n) if c["area_px"] > (0.4 * self.ppmm) ** 2]
            st["lighter_than_%d_pct" % int(thr * 100)] = {
                "count": len(cs),
                "total_area_frac_of_tag": _r(sum(c["area_px"] for c in cs) / self.stat_n, 5),
            }
        out["stains"] = st
        self.mottle_resid = resid
        self.out["mottle_and_stains"] = out

    def _loglog_slope(self, f, p):
        m = (p > 0) & (f > 0)
        if m.sum() < 8:
            return None
        A = np.vstack([np.log10(f[m]), np.ones(m.sum())]).T
        sol, *_ = np.linalg.lstsq(A, np.log10(p[m]), rcond=None)
        return float(sol[0])

    def _band_powers(self, f, p):
        mmf = f * self.ppmm          # cycles per mm
        tot = float(np.sum(p))
        d = {}
        for lo, hi, nm in ((0.0, 0.1, "wavelength_gt_10mm"),
                           (0.1, 0.33, "3_to_10mm"),
                           (0.33, 1.0, "1_to_3mm"),
                           (1.0, 99.0, "lt_1mm")):
            m = (mmf >= lo) & (mmf < hi)
            d[nm] = _r(float(np.sum(p[m])) / tot if tot > 0 else None, 4)
        return d

    def _clean_patches(self, pm, n=6, size=100):
        """Find square patches that are >98% paper."""
        integ = np.cumsum(np.cumsum(pm.astype(np.float32), 0), 1)
        integ = np.pad(integ, ((1, 0), (1, 0)))
        found = []
        step = max(4, size // 4)
        for y0 in range(0, self.H - size, step):
            for x0 in range(0, self.W - size, step):
                s = (integ[y0 + size, x0 + size] - integ[y0, x0 + size]
                     - integ[y0 + size, x0] + integ[y0, x0])
                if s / (size * size) > 0.985:
                    found.append((s, y0, x0))
        found.sort(key=lambda t: -t[0])
        picked = []
        for _, y0, x0 in found:
            if all(abs(y0 - p[0]) > size * 0.8 or abs(x0 - p[1]) > size * 0.8 for p in picked):
                picked.append((y0, x0, size))
            if len(picked) >= n:
                break
        return picked

    # ------------------------------------------------------- folds/creases
    def measure_creases(self):
        lum = self.paper_luma
        pm = self.paper_mask
        c1, _ = M.masked_blur(lum, pm, max(2, 0.004 * self.W))
        c2, _ = M.masked_blur(lum, pm, max(4, 0.016 * self.W))
        band = np.where(pm, c1 - c2, 0.0)
        thr = 2.5 * float(np.std(band[pm]))
        found = []
        for nm, axis in (("horizontal", 1), ("vertical", 0)):
            prof = np.sum(np.where(band < -thr, 1.0, 0.0) * pm, axis=axis)
            width = pm.sum(axis=axis)
            frac = prof / np.maximum(width, 1)
            peak = float(np.max(frac)) if frac.size else 0.0
            idx = np.flatnonzero(frac > 0.45)
            runs = []
            if idx.size:
                brk = np.flatnonzero(np.diff(idx) > 3)
                groups = np.split(idx, brk + 1)
                for g in groups:
                    if g.size >= 1:
                        cpos = float(np.mean(g))
                        span = self.H if axis == 1 else self.W
                        # ignore the paper edge itself: a one-row band at the
                        # boundary is the cut, not a crease
                        if cpos < 1.5 * self.ppmm or cpos > span - 1.5 * self.ppmm:
                            continue
                        runs.append({
                            "pos_frac": _r(cpos / (self.H if axis == 1 else self.W), 4),
                            "pos_mm": _r(cpos / self.ppmm, 3),
                            "run_coverage": _r(float(np.max(frac[g])), 4),
                            "width_mm": _r(g.size / self.ppmm, 3),
                        })
            found.append({"orientation": nm, "peak_line_coverage": _r(peak, 4),
                          "lines": runs})
        self.out["folds_creases_shadows"] = {
            "method": "band-pass of the paper luma (0.4%W minus 1.6%W blur); a crease "
                      "shows as a line of band-pass minima spanning the tag",
            "bandpass_threshold": _r(thr, 6),
            "axes": found,
            "any_full_span_crease": bool(any(r["run_coverage"] > 0.6
                                             for a in found for r in a["lines"])),
            "global_gradient": self.out["paper"]["global_gradient"],
        }

    # ------------------------------------------------------- elements
    def find_elements(self):
        """Locate named elements from connected components + layout rules."""
        els = {}
        u = (np.arange(self.W) + 0.5) / self.W
        vv = (np.arange(self.H) + 0.5) / self.H
        U, V = np.meshgrid(u, vv)
        self.U, self.V = U, V

        # ---- enso ring. A connected-component search finds one arc (kasure breaks
        # the stroke) or the border frame, so fit the annulus directly: score
        # candidate axis-aligned ellipses by the red ink that lies ON them minus
        # the red ink just inside and just outside. The border frame scores badly
        # because it is a rectangle, and the seal blocks because they are solid.
        self.ring_fit = None
        self.ring_bbox = None
        self.ring_rho = None
        self._fit_ring(U, V)
        if self.ring_fit:
            els["ring"] = self.ring_bbox

        # centre glyph: black components that reach inside the ring
        if self.ring_rho is not None:
            seed = self.black & (self.ring_rho < 0.92)
            lab, n = M.label_cc(self.black)
            hit = np.unique(lab[seed])
            hit = hit[hit > 0]
            self.centre_glyph = np.isin(lab, hit)
            els["centre_glyph"] = self._bbox_of(self.centre_glyph)
        else:
            self.centre_glyph = np.zeros_like(self.black)

        # fixed fractional windows for the rest (checked against found ink)
        wins = {
            "border_frame": (0.00, 0.00, 1.00, 1.00),
            "upper_left_column": (0.05, 0.03, 0.30, 0.33),
            "upper_right_column": (0.70, 0.03, 0.98, 0.33),
            "flame_emblem": (0.33, 0.09, 0.67, 0.30),
            "lower_right_column": (0.70, 0.58, 0.98, 0.82),
            "lower_centre_column": (0.38, 0.68, 0.64, 0.95),
            "seal_block_lower_left": (0.05, 0.70, 0.36, 0.95),
            "small_seal_lower_right": (0.72, 0.76, 0.98, 0.95),
        }
        self.windows = {}
        for nm, (a, b, cc, dd) in wins.items():
            self.windows[nm] = ((U >= a) & (U < cc) & (V >= b) & (V < dd))
        self.elements = els
        rep = {"windows_uv": {k: _r(list(v), 4) for k, v in wins.items()}}
        for nm, bb in els.items():
            if bb is None:
                continue
            x0, y0, x1, y1 = bb
            rep[nm] = {
                "bbox_uv": _r([x0 / self.W, y0 / self.H, x1 / self.W, y1 / self.H], 5),
                "bbox_mm": _r([x0 / self.ppmm, y0 / self.ppmm,
                               x1 / self.ppmm, y1 / self.ppmm], 3),
                "size_mm": _r([(x1 - x0) / self.ppmm, (y1 - y0) / self.ppmm], 3),
            }
        self.out["elements"] = rep
        return els

    def _ring_score(self, cands, ra, n=360):
        """cands: (K,4) of cx, cy, rx, ry in px. Higher is more annulus-like."""
        th = np.linspace(0, 2 * np.pi, n, endpoint=False)
        ct, st = np.cos(th)[None, :], np.sin(th)[None, :]
        cx, cy, rx, ry = (cands[:, i][:, None] for i in range(4))
        out = np.zeros(cands.shape[0])
        for rho, wgt in ((0.94, 0.5), (1.0, 1.0), (1.06, 0.5),
                         (0.70, -0.5), (1.38, -0.5)):
            xi = np.clip(np.round(cx + rho * rx * ct).astype(np.int32), 0, self.W - 1)
            yi = np.clip(np.round(cy + rho * ry * st).astype(np.int32), 0, self.H - 1)
            out += wgt * ra[yi, xi].mean(axis=1)
        return out / 2.0

    def _fit_ring(self, U, V):
        ra = np.where(self.red, self.alpha, 0.0)
        if ra.sum() < 2000:
            self.centre_glyph = np.zeros_like(self.black)
            return
        W, H = self.W, self.H

        def search(cxr, cyr, rxr, ryr):
            best, bestc = -1e9, None
            cxs = np.asarray(cxr, float)
            for cy in cyr:
                grid = np.array([[a, cy, c, d] for a in cxs for c in rxr for d in ryr])
                sc = self._ring_score(grid, ra)
                i = int(np.argmax(sc))
                if sc[i] > best:
                    best, bestc = float(sc[i]), grid[i].copy()
            return bestc, best

        c1, s1 = search(np.linspace(0.46 * W, 0.54 * W, 3),
                        np.linspace(0.28 * H, 0.64 * H, 19),
                        np.linspace(0.22 * W, 0.42 * W, 21),
                        np.linspace(0.11 * H, 0.26 * H, 16))
        if c1 is None:
            self.centre_glyph = np.zeros_like(self.black)
            return
        c2, s2 = search(np.linspace(c1[0] - 0.02 * W, c1[0] + 0.02 * W, 7),
                        np.linspace(c1[1] - 0.02 * H, c1[1] + 0.02 * H, 9),
                        np.linspace(c1[2] - 0.012 * W, c1[2] + 0.012 * W, 9),
                        np.linspace(c1[3] - 0.010 * H, c1[3] + 0.010 * H, 9))
        cx, cy, rx, ry = (c2 if s2 >= s1 else c1)
        self.ring_rho = np.sqrt(((U * W - cx) / rx) ** 2 + ((V * H - cy) / ry) ** 2)
        self.ring_fit = {"cx_px": cx, "cy_px": cy, "rx_px": rx, "ry_px": ry,
                         "score": max(s1, s2)}
        # true outer / inner extents of the stroke along the fitted axes
        band = self.red & (self.ring_rho > 0.55) & (self.ring_rho < 1.55)
        rho_in = rho_out = None
        if band.sum() > 500:
            rv = self.ring_rho[band]
            rho_in, rho_out = float(np.percentile(rv, 1.0)), float(np.percentile(rv, 99.0))
        self.ring_bbox = (cx - rx, cy - ry, cx + rx, cy + ry)
        self.out.setdefault("segmentation", {})["ring_fit"] = {
            "method": "direct annulus search: axis-aligned ellipses scored by the red "
                      "ink lying on them (rho 0.94/1.00/1.06) minus the red ink just "
                      "inside and just outside (rho 0.70/1.38), coarse grid then "
                      "refined. Immune to the kasure breaks that split the stroke into "
                      "arcs, and to the border frame and the solid seal blocks.",
            "centre_uv": _r([cx / W, cy / H], 5),
            "centre_mm": _r([cx / self.ppmm, cy / self.ppmm], 3),
            "mid_stroke_semi_axes_mm": _r([rx / self.ppmm, ry / self.ppmm], 3),
            "mid_stroke_semi_axes_frac_of_W_and_H": _r([rx / W, ry / H], 5),
            "mid_stroke_width_mm": _r(2 * rx / self.ppmm, 3),
            "mid_stroke_height_mm": _r(2 * ry / self.ppmm, 3),
            "ellipticity_h_over_w": _r(ry / rx, 4),
            "outer_rho_p99": _r(rho_out, 4),
            "inner_rho_p1": _r(rho_in, 4),
            "outer_width_mm": _r(2 * rx * rho_out / self.ppmm, 3) if rho_out else None,
            "outer_height_mm": _r(2 * ry * rho_out / self.ppmm, 3) if rho_out else None,
            "stroke_width_mm_on_x_axis": _r((rho_out - rho_in) * rx / self.ppmm, 4)
            if rho_out else None,
            "stroke_width_frac_of_W": _r((rho_out - rho_in) * rx / W, 5) if rho_out else None,
        }

    def _bbox_of(self, mask):
        ys, xs = np.nonzero(mask)
        if xs.size == 0:
            return None
        return (float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max()))

    # ------------------------------------------------------- coverage
    def measure_coverage(self):
        A = self.stat_n
        cov = {
            "definition": "alpha = 1 - linear_G / local paper field; 'solid' counts "
                          "pixels with alpha>0.5, 'ink mass' is the mean of alpha over "
                          "the paper (so kasure holes and soft halos are counted "
                          "partially, which is what the eye integrates)",
            "total": {
                "solid_area_frac": _r(float((self.stat_area & (self.alpha > 0.5)).sum()) / A, 5),
                "ink_area_frac_alpha_gt_0_35": _r(float(self.ink.sum()) / A, 5),
                "ink_mass_frac": _r(float(self.alpha[self.stat_area].mean()), 5),
                "black_area_frac": _r(float(self.black.sum()) / A, 5),
                "red_area_frac": _r(float(self.red.sum()) / A, 5),
                "black_over_red_area": _r(float(self.black.sum()) / max(float(self.red.sum()), 1), 4),
                "black_ink_mass_frac": _r(float(np.where(self.black, self.alpha, 0).sum()) / A, 5),
                "red_ink_mass_frac": _r(float(np.where(self.red, self.alpha, 0).sum()) / A, 5),
            },
        }
        per = {}
        ring_mask = None
        if self.ring_rho is not None:
            ring_mask = self.red & (self.ring_rho > 0.60) & (self.ring_rho < 1.30)
            per["enso_ring_red"] = self._cov(ring_mask, A)
            per["centre_glyph_black"] = self._cov(self.centre_glyph, A)
            # radial ink profile across the ring stroke
            prof = []
            for lo in np.arange(0.55, 1.45, 0.05):
                m = self.stat_area & (self.ring_rho >= lo) & (self.ring_rho < lo + 0.05)
                if m.sum() > 100:
                    prof.append({"rho": _r(lo + 0.025, 3),
                                 "mean_red_alpha": _r(float(np.where(self.red, self.alpha, 0)[m].mean()), 4),
                                 "red_area_frac": _r(float(self.red[m].mean()), 4)})
            per["enso_ring_radial_profile"] = prof
        for nm, w in self.windows.items():
            if nm == "border_frame":
                continue
            per[nm + "_black"] = self._cov(self.black & w, A)
            per[nm + "_red"] = self._cov(self.red & w, A)
        # border frame: red ink within 12% of the edge
        dmm = self.d_edge / self.ppmm
        frame = self.stat_area & (dmm < 0.12 * CARD_W_MM)
        per["border_zone_outer_8_4mm_red"] = self._cov(self.red & frame, A)
        per["border_zone_outer_8_4mm_black"] = self._cov(self.black & frame, A)
        cov["per_element"] = per
        self.ring_mask = ring_mask
        self.out["coverage"] = cov

    def _cov(self, m, A):
        return {
            "area_frac_of_tag": _r(float(m.sum()) / A, 5),
            "area_mm2": _r(float(m.sum()) / (self.ppmm ** 2), 2),
            "ink_mass_frac_of_tag": _r(float(np.where(m, self.alpha, 0).sum()) / A, 5),
            "mean_alpha_in_mask": _r(float(self.alpha[m].mean()) if m.sum() else None, 4),
        }

    # ------------------------------------------------------- black ink
    def measure_black(self):
        core = M.erode(self.black, self.core_r)
        res = {
            "core_erosion_px": _r(self.core_r, 2),
            "core_erosion_mm": _r(self.core_r / self.ppmm, 4),
            "colour_core": colour_report(self.rect[core]) if core.sum() else None,
            "colour_all_black_pixels": colour_report(self.rect[self.black]),
            "alpha_distribution": {k: _r(v, 5) for k, v in M.stats(self.alpha[self.black]).items()},
        }
        if core.sum():
            lum_lin = 0.2126 * self.lin[..., 0] + 0.7152 * self.lin[..., 1] + 0.0722 * self.lin[..., 2]
            lc = lum_lin[core]
            sc = np.max(self.rect, axis=-1)[core]
            res["darkest"] = {
                "min_linear_luma": _r(float(lc.min()), 7),
                "p0_1_linear_luma": _r(float(np.percentile(lc, 0.1)), 7),
                "p1_linear_luma": _r(float(np.percentile(lc, 1)), 7),
                "median_linear_luma": _r(float(np.median(lc)), 7),
                "min_stored_srgb_8bit": int(round(float(sc.min()) * 255)),
                "p1_stored_srgb_8bit": int(round(float(np.percentile(sc, 1)) * 255)),
                "median_stored_srgb_8bit": int(round(float(np.median(sc)) * 255)),
                "neutrality_R_minus_B_stored_median": _r(float(np.median(self.warm[core])), 5),
                "neutrality_R_minus_B_stored_p5_p95": _r(
                    [float(np.percentile(self.warm[core], 5)),
                     float(np.percentile(self.warm[core], 95))], 5),
            }
            # within-one-stroke variation: per component spread of core luma
            lab, n = M.label_cc(core)
            cs = M.cc_stats(lab, n)
            cs = [c for c in cs if c["area_px"] > (1.0 * self.ppmm) ** 2]
            spreads, stds = [], []
            for c in cs[:60]:
                m = lab == c["label"]
                x = self.v[m]
                stds.append(float(np.std(x)))
                spreads.append(float(np.percentile(x, 95) - np.percentile(x, 5)))
            res["within_stroke_variation"] = {
                "n_components_measured": len(stds),
                "stored_value_std_median": _r(float(np.median(stds)) if stds else None, 5),
                "stored_value_p5_p95_span_median": _r(float(np.median(spreads)) if spreads else None, 5),
                "stored_value_p5_p95_span_8bit": _r(
                    float(np.median(spreads)) * 255 if spreads else None, 1),
                "verdict": ("flat fill" if spreads and np.median(spreads) < 0.06
                            else "modulated"),
            }
            # loaded-to-dry gradient down each element
            grads = {}
            for nm, w in list(self.windows.items()) + (
                    [("centre_glyph", self.centre_glyph)] if self.ring_rho is not None else []):
                if nm == "border_frame":
                    continue
                m = core & w
                if m.sum() < 400:
                    continue
                ys, xs = np.nonzero(m)
                yy = (ys - ys.min()) / max(ys.max() - ys.min(), 1)
                A_ = np.vstack([yy, np.ones(yy.size)]).T
                sol, *_ = np.linalg.lstsq(A_, self.alpha[m], rcond=None)
                sol2, *_ = np.linalg.lstsq(A_, self.v[m], rcond=None)
                grads[nm] = {
                    "n_px": int(m.sum()),
                    "d_alpha_top_to_bottom": _r(float(sol[0]), 5),
                    "d_stored_value_top_to_bottom": _r(float(sol2[0]), 5),
                    "alpha_top": _r(float(sol[1]), 5),
                    "alpha_bottom": _r(float(sol[1] + sol[0]), 5),
                    "drier_toward_bottom": bool(sol[0] < -0.01),
                }
            res["loaded_to_dry_gradient"] = grads
        self.black_core = core
        self.out["black_ink"] = res

    def _ring_inner_mask(self):
        if self.ring_rho is None:
            return np.zeros(self.rect.shape[:2], bool)
        return self.ring_rho < 1.0

    # ------------------------------------------------------- reds
    def measure_reds(self):
        er = self.core_r
        groups = {}
        dmm = self.d_edge / self.ppmm
        cand = {
            "border_red": self.red & (dmm < 0.12 * CARD_W_MM),
            "ring_red": self.ring_mask if self.ring_mask is not None else None,
            "seal_block_red_lower_left": self.red & self.windows["seal_block_lower_left"],
            "small_seal_red_lower_right": self.red & self.windows["small_seal_lower_right"],
        }
        for nm, m in cand.items():
            if m is None or m.sum() < 200:
                continue
            core = M.erode(m, er)
            if core.sum() < 60:
                core = m
            rep = colour_report(self.rect[core])
            cRm = float(np.median(self.cR[core]))
            cGm = float(np.median(self.cG[core]))
            cBm = float(np.median(self.cB[core]))
            rep["opacity_over_paper"] = {
                "alpha_R": _r(1 - cRm, 5), "alpha_G": _r(1 - cGm, 5), "alpha_B": _r(1 - cBm, 5),
                "transmittance_RGB": _r([cRm, cGm, cBm], 5),
                "note": "alpha_C = 1 - linear_C / local paper field_C; alpha_R well "
                        "below alpha_G is what makes it read as red rather than dark",
            }
            rep["area_frac_of_tag"] = _r(float(m.sum()) / self.stat_n, 5)
            rep["core_px"] = int(core.sum())
            groups[nm] = rep
        # are they the same red?
        keys = [k for k in groups if groups[k].get("n")]
        same = {}
        if len(keys) > 1:
            hs = {k: groups[k]["hsv_stored"]["h_deg"] for k in keys}
            ss = {k: groups[k]["hsv_stored"]["s"] for k in keys}
            vs = {k: groups[k]["hsv_stored"]["v"] for k in keys}
            same = {
                "hue_deg": hs, "sat": ss, "val": vs,
                "hue_spread_deg": _r(max(hs.values()) - min(hs.values()), 3),
                "sat_spread": _r(max(ss.values()) - min(ss.values()), 4),
                "val_spread": _r(max(vs.values()) - min(vs.values()), 4),
            }
            same["same_red"] = bool(same["hue_spread_deg"] < 4.0
                                    and same["sat_spread"] < 0.10
                                    and same["val_spread"] < 0.12)
        self.out["reds"] = {"per_element": groups, "comparison": same}

    # ------------------------------------------------------- kasure
    def _kasure(self, mask, close_r, tangent=None):
        env = M.closing(mask, close_r)
        holes = env & ~mask
        holes = M.opening(holes, 0.6)
        lab, n = M.label_cc(holes)
        cs = M.cc_stats(lab, n)
        cs = [c for c in cs if c["area_px"] >= 2]
        area_env = float(env.sum())
        d = np.array([c["equiv_diam_px"] / self.ppmm for c in cs]) if cs else np.array([])
        el = np.array([min(c["elongation"], 20.0) for c in cs]) if cs else np.array([])
        res = {
            "close_radius_px": _r(close_r, 2),
            "close_radius_mm": _r(close_r / self.ppmm, 4),
            "stroke_envelope_area_frac_of_tag": _r(area_env / self.stat_n, 5),
            "hole_count": len(cs),
            "hole_count_per_100mm2_of_stroke": _r(
                len(cs) / max(area_env / self.ppmm ** 2, 1e-6) * 100.0, 3),
            "hole_area_fraction_of_stroke": _r(float(holes.sum()) / max(area_env, 1), 5),
            "hole_equiv_diam_mm": {k: _r(v, 4) for k, v in M.stats(d).items()} if d.size else None,
            "hole_equiv_diam_frac_of_W": _r(float(np.median(d)) / CARD_W_MM, 6) if d.size else None,
            "hole_elongation": {k: _r(v, 3) for k, v in M.stats(el).items()} if el.size else None,
            "mean_alpha_inside_envelope": _r(float(self.alpha[env].mean()), 4),
            "alpha_inside_envelope": {k: _r(v, 4) for k, v in M.stats(self.alpha[env]).items()},
        }
        if tangent is not None and cs:
            dev = []
            for c in cs:
                if c["elongation"] < 1.35 or c["area_px"] < 6:
                    continue
                t = tangent(c["cx_px"], c["cy_px"])
                if t is None:
                    continue
                dd = abs(((c["angle_deg"] - t + 90) % 180) - 90)
                dev.append(dd)
            if dev:
                dev = np.array(dev)
                res["alignment_with_stroke_direction"] = {
                    "n_elongated_holes": int(dev.size),
                    "abs_angle_to_tangent_deg": {k: _r(v, 3) for k, v in M.stats(dev).items()},
                    "frac_within_20deg_of_stroke": _r(float((dev < 20).mean()), 4),
                    "frac_within_30deg_of_stroke": _r(float((dev < 30).mean()), 4),
                    "random_expectation_within_30deg": 0.3333,
                }
        return res

    def measure_kasure(self):
        out = {}
        cr = max(2.0, 0.012 * self.W)
        if self.ring_mask is not None and self.ring_mask.sum() > 500:
            x0, y0, x1, y1 = self.ring_bbox
            cx, cy = 0.5 * (x0 + x1), 0.5 * (y0 + y1)

            def tangent(px, py):
                a = np.degrees(np.arctan2(py - cy, px - cx))
                return (a + 90.0) % 180.0
            out["enso_ring"] = self._kasure(self.ring_mask, cr, tangent)
        # black: the centre glyph and the side columns
        if self.centre_glyph.sum() > 500:
            out["centre_glyph_black"] = self._kasure(self.centre_glyph, cr)
        for nm in ("upper_left_column", "upper_right_column", "lower_right_column",
                   "lower_centre_column", "flame_emblem"):
            m = self.black & self.windows[nm]
            if m.sum() > 400:
                out[nm + "_black"] = self._kasure(m, max(1.5, 0.008 * self.W))
        allblack = self.black & ~self.centre_glyph
        out["all_black_outside_ring"] = self._kasure(allblack, max(1.5, 0.008 * self.W))
        self.out["kasure_dry_brush"] = out

    # ------------------------------------------------------- edge roughness
    def measure_edge_roughness(self):
        out = {}
        if self.ring_mask is not None and self.ring_mask.sum() > 500:
            out["enso_ring_polar"] = self._ring_polar_roughness()
        for nm, m in (("black_all", self.black), ("red_all", self.red)):
            out[nm] = self._roughness_index(m)
        if self.centre_glyph.sum() > 300:
            out["centre_glyph_black"] = self._roughness_index(self.centre_glyph)
        self.out["stroke_edge_roughness"] = out

    def _ring_polar_roughness(self):
        env = M.closing(self.ring_mask, max(2.0, 0.012 * self.W))
        ys, xs = np.nonzero(env)
        cx, cy = float(xs.mean()), float(ys.mean())
        ang = np.degrees(np.arctan2(ys - cy, xs - cx)) % 360.0
        rad = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)
        nb = 720
        idx = np.clip((ang / 360.0 * nb).astype(int), 0, nb - 1)
        mx = np.full(nb, -np.inf)
        np.maximum.at(mx, idx, rad)
        r_out = np.where(np.isfinite(mx), mx, np.nan)
        mn = np.full(nb, np.inf)
        np.minimum.at(mn, idx, rad)
        r_in = np.where(np.isfinite(mn), mn, np.nan)
        res = {}
        for nm, r in (("outer", r_out), ("inner", r_in)):
            good = np.isfinite(r)
            if good.sum() < nb * 0.7:
                continue
            rr = np.interp(np.arange(nb), np.flatnonzero(good), r[good], period=nb)
            k = 25
            ker = np.ones(k) / k
            base = np.convolve(np.concatenate([rr, rr, rr]), ker, "same")[nb:2 * nb]
            dev = rr - base
            amp = float(np.sqrt(np.mean(dev ** 2)))
            F = np.abs(np.fft.rfft(dev - dev.mean())) ** 2
            f = np.arange(F.size)
            band = (f >= 3) & (f <= 120)
            pk = int(f[band][np.argmax(F[band])]) if band.any() else 0
            circ = float(np.mean(base)) * 2 * np.pi
            res[nm] = {
                "mean_radius_mm": _r(float(np.mean(base)) / self.ppmm, 4),
                "mean_radius_frac_of_W": _r(float(np.mean(base)) / self.W, 5),
                "roughness_rms_px": _r(amp, 4),
                "roughness_rms_mm": _r(amp / self.ppmm, 5),
                "roughness_rms_frac_of_W": _r(amp / self.W, 6),
                "roughness_p5_p95_mm": _r([float(np.percentile(dev, 5)) / self.ppmm,
                                           float(np.percentile(dev, 95)) / self.ppmm], 5),
                "dominant_cycles_per_revolution": pk,
                "dominant_wavelength_mm_along_edge": _r(circ / max(pk, 1) / self.ppmm, 4),
                "dominant_wavelength_frac_of_W": _r(circ / max(pk, 1) / self.W, 5),
            }
        res["centre_u"] = _r(cx / self.W, 5)
        res["centre_v"] = _r(cy / self.H, 5)
        return res

    def _roughness_index(self, mask):
        if mask.sum() < 300:
            return None
        r = max(1.2, 0.0045 * self.W)
        sm = M.opening(M.closing(mask, r), r)
        xo = np.logical_xor(mask, sm)
        # perimeter of the smoothed mask (4-neighbour boundary count)
        p = np.zeros_like(sm)
        p[:-1] |= sm[:-1] != sm[1:]
        p[:, :-1] |= sm[:, :-1] != sm[:, 1:]
        per = float(p.sum())
        lab, n = M.label_cc(xo)
        cs = M.cc_stats(lab, n)
        cs = [c for c in cs if c["area_px"] >= 2]
        amp = float(xo.sum()) / max(per, 1)
        return {
            "smoothing_radius_px": _r(r, 2),
            "smoothing_radius_mm": _r(r / self.ppmm, 4),
            "mean_deviation_amplitude_px": _r(amp, 4),
            "mean_deviation_amplitude_mm": _r(amp / self.ppmm, 5),
            "mean_deviation_amplitude_frac_of_W": _r(amp / self.W, 6),
            "n_ragged_lobes": len(cs),
            "boundary_length_mm": _r(per / self.ppmm, 2),
            "mean_lobe_spacing_mm": _r(per / max(len(cs), 1) / self.ppmm, 4),
            "mean_lobe_spacing_frac_of_W": _r(per / max(len(cs), 1) / self.W, 5),
            "lobe_area_mm2_median": _r(float(np.median([c["area_px"] for c in cs]))
                                       / self.ppmm ** 2 if cs else None, 5),
        }

    # ------------------------------------------------------- bleed
    def measure_bleed(self):
        out = {}
        for nm, m in (("black", self.black), ("red", self.red)):
            if m.sum() < 500:
                continue
            # signed distance from the stroke boundary: negative inside the ink,
            # positive out on the paper. Plateau = alpha well inside the stroke.
            d_in = M.edt(m)
            d_out = M.dist_outside(m)
            signed = np.where(m, -d_in, d_out)
            deep = m & (d_in > max(2.0 * self.core_r, 0.35 * self.ppmm))
            if deep.sum() < 200:
                deep = M.erode(m, self.core_r)
            if deep.sum() < 100:
                continue
            a0 = float(np.median(self.alpha[deep]))
            prof = []
            lo, hi = -1.2 * self.ppmm, 1.2 * self.ppmm
            edges = np.arange(np.floor(lo), np.ceil(hi) + 1.0, 1.0)
            for i in range(len(edges) - 1):
                sel = self.stat_area & (signed >= edges[i]) & (signed < edges[i + 1])
                if sel.sum() < 40:
                    continue
                av = float(np.median(self.alpha[sel]))
                prof.append({
                    "d_px": _r(0.5 * (edges[i] + edges[i + 1]), 2),
                    "d_mm": _r(0.5 * (edges[i] + edges[i + 1]) / self.ppmm, 4),
                    "d_frac_of_W": _r(0.5 * (edges[i] + edges[i + 1]) / self.W, 6),
                    "d_native_px": _r(0.5 * (edges[i] + edges[i + 1])
                                      * self.native_ppmm / self.ppmm, 3),
                    "alpha": _r(av, 5),
                    "alpha_rel_to_plateau": _r(av / max(a0, 1e-9), 5),
                })

            def cross(frac):
                """Outward distance at which alpha falls through frac of plateau."""
                for i in range(1, len(prof)):
                    p0, p1 = prof[i - 1], prof[i]
                    if p0["alpha_rel_to_plateau"] > frac >= p1["alpha_rel_to_plateau"]:
                        t = ((p0["alpha_rel_to_plateau"] - frac)
                             / max(p0["alpha_rel_to_plateau"]
                                   - p1["alpha_rel_to_plateau"], 1e-9))
                        return p0["d_mm"] + t * (p1["d_mm"] - p0["d_mm"])
                return None
            h50, h25, h10 = cross(0.5), cross(0.25), cross(0.10)
            h90 = cross(0.90)
            # 10-90 transition width across the boundary
            t1090 = (h10 - h90) if (h10 is not None and h90 is not None) else None
            # how much of that width is unavoidable raster anti-aliasing
            aa = 1.0 / self.native_ppmm
            tail = [p for p in prof
                    if p["d_mm"] > aa and 0.01 < p["alpha_rel_to_plateau"] < 0.6]
            lam = None
            if len(tail) >= 3:
                x = np.array([p["d_mm"] for p in tail])
                yv = np.log(np.array([p["alpha_rel_to_plateau"] for p in tail]))
                A_ = np.vstack([x, np.ones(x.size)]).T
                sol, *_ = np.linalg.lstsq(A_, yv, rcond=None)
                lam = -1.0 / sol[0] if sol[0] < 0 else None
            out[nm] = {
                "plateau_alpha_deep_inside_stroke": _r(a0, 5),
                "profile_signed_distance_negative_is_inside_the_ink": prof,
                "alpha_50pct_crossing_mm": _r(h50, 5),
                "halo_width_mm_50pct_to_10pct": _r(
                    (h10 - h50) if (h10 is not None and h50 is not None) else None, 5),
                "outward_mm_to_25pct": _r(h25, 5),
                "outward_mm_to_10pct": _r(h10, 5),
                "outward_frac_of_W_to_10pct": _r(h10 / CARD_W_MM if h10 else None, 6),
                "transition_width_10_to_90_mm": _r(t1090, 5),
                "transition_width_10_to_90_frac_of_W": _r(
                    t1090 / CARD_W_MM if t1090 else None, 6),
                "transition_width_in_native_px": _r(
                    t1090 * self.native_ppmm if t1090 else None, 3),
                "exponential_decay_length_mm": _r(lam, 5),
                "native_px_per_mm": _r(self.native_ppmm, 3),
                "one_native_px_mm": _r(aa, 5),
                "soft_halo_beyond_antialiasing_mm": _r(
                    max(t1090 - aa, 0.0) if t1090 else None, 5),
                "note": "a hard-edged stroke drawn on this raster would still show a "
                        "10-90 transition of about one native pixel; only the excess "
                        "over one_native_px_mm is ink bleed",
            }
        self.out["ink_bleed"] = out

    # ------------------------------------------------------- fibre texture
    def measure_fibre(self, native_rgb=None, native_support=None):
        """Measured at NATIVE resolution so the spectrum is not an artefact of
        the rectification resample."""
        if native_rgb is None:
            self.out["paper_fibre_texture"] = {"skipped": "no native raster supplied"}
            return
        a = np.clip(np.asarray(native_rgb, float)[..., :3], 0, 1)
        lin = P.srgb_to_linear(a)
        lum = 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]
        h, s, v = P.rgb_to_hsv(a)
        pm = (v > 0.55) & (s < 0.55) & (h > 20) & (h < 65)
        if native_support is not None:
            pm = pm & native_support
        base = M.boxblur(lum, max(2, int(0.004 * a.shape[1])))
        resid = lum / np.maximum(base, 1e-6) - 1.0
        hh, ww = a.shape[:2]
        integ = np.pad(np.cumsum(np.cumsum(pm.astype(np.float32), 0), 1), ((1, 0), (1, 0)))
        picked, sz, purity = [], None, None
        for frac in (0.22, 0.16, 0.12, 0.09):
            for pur in (0.995, 0.98, 0.95):
                sz = max(24, int(min(hh, ww) * frac))
                found = []
                step = max(4, sz // 5)
                for y0 in range(0, hh - sz, step):
                    for x0 in range(0, ww - sz, step):
                        ssum = (integ[y0 + sz, x0 + sz] - integ[y0, x0 + sz]
                                - integ[y0 + sz, x0] + integ[y0, x0])
                        if ssum / float(sz * sz) > pur:
                            found.append((ssum, y0, x0))
                found.sort(key=lambda t: -t[0])
                picked = []
                for _, y0, x0 in found:
                    if all(abs(y0 - p[0]) > sz * 0.7 or abs(x0 - p[1]) > sz * 0.7
                           for p in picked):
                        picked.append((y0, x0))
                    if len(picked) >= 4:
                        break
                if len(picked) >= 2:
                    purity = pur
                    break
            if len(picked) >= 2:
                break
        if not picked:
            self.out["paper_fibre_texture"] = {"skipped": "no clean native paper patch found"}
            return
        ppmm = self.native_ppmm
        specs, angs, P2 = [], [], None
        for (y0, x0) in picked:
            f, p, (Pm, KX, KY, R) = M.radial_power(resid[y0:y0 + sz, x0:x0 + sz])
            specs.append(p)
            P2 = (Pm, KX, KY, R)
            angs.append((Pm, KX, KY, R))
        p = np.mean(np.array(specs), axis=0)
        keep = (f * ppmm > 0.30) & (f < 0.48)
        fk, pk = f[keep], p[keep]
        i = int(np.argmax(pk)) if fk.size else 0
        peak_f = float(fk[i] * ppmm) if fk.size else None
        # anisotropy in the band around the peak, kept below 0.35 cyc/px so the
        # corners of the FFT grid cannot fake a 45 deg preference
        lo = max(0.02, (peak_f / ppmm) * 0.6) if peak_f else 0.05
        hi = min(0.35, (peak_f / ppmm) * 1.8) if peak_f else 0.25
        if hi <= lo:
            lo, hi = 0.08, 0.32
        aprofs = []
        for (Pm, KX, KY, R) in angs:
            th, ap = M.angular_power(Pm, KX, KY, R, lo, hi, nbins=18)
            aprofs.append(ap)
        ap = np.mean(np.array(aprofs), axis=0)
        aniso = float(ap.max() / max(ap.min(), 1e-12))
        self.out["paper_fibre_texture"] = {
            "measured_at": "native resolution",
            "native_px_per_mm": _r(ppmm, 4),
            "n_patches": len(picked),
            "patch_purity_required": purity,
            "patch_size_px": sz,
            "patch_size_mm": _r(sz / ppmm, 3),
            "residual_rms_pct_of_paper_luma": _r(
                100.0 * float(np.sqrt(np.mean(resid[pm] ** 2))), 4),
            "dominant_cycles_per_mm": _r(peak_f, 4),
            "dominant_cell_size_mm": _r(1.0 / peak_f if peak_f else None, 4),
            "dominant_cell_size_frac_of_W": _r(
                (1.0 / peak_f) / CARD_W_MM if peak_f else None, 6),
            "nyquist_cycles_per_mm": _r(0.5 * ppmm, 3),
            "spectrum_slope_loglog": _r(self._loglog_slope(f[f * ppmm > 0.15],
                                                           p[f * ppmm > 0.15]), 4),
            "anisotropy_max_over_min": _r(aniso, 4),
            "preferred_orientation_deg": _r(float(th[int(np.argmax(ap))]), 2),
            "orientation_note": "0 deg = horizontal ripple direction in the tag frame; "
                                "anisotropy near 1.0 means an isotropic (random-laid) "
                                "fibre field",
            "angular_power_profile": {_r(t, 1): _r(float(x / ap.mean()), 4)
                                      for t, x in zip(th, ap)},
        }

    # ------------------------------------------------------- run all
    def run(self, native_rgb=None, native_support=None, support_override=None):
        self.build_support(support_override)
        self.build_paper_field()
        self.build_masks()
        self.measure_paper()
        self.measure_mottle()
        self.measure_creases()
        self.find_elements()
        self.measure_coverage()
        self.measure_black()
        self.measure_reds()
        self.measure_kasure()
        self.measure_edge_roughness()
        self.measure_bleed()
        self.measure_fibre(native_rgb, native_support)
        self.out["_frame"] = {
            "name": self.name,
            "rect_px": [self.W, self.H],
            "rect_px_per_mm": _r(self.ppmm, 4),
            "native_px_per_mm": _r(self.native_ppmm, 4),
            "tag_aspect_h_over_w": _r(self.aspect, 5),
            "card_mm": [CARD_W_MM, CARD_H_MM],
            "convention": "u=x/W, v=y/H from the tag's top-left paper corner; "
                          "mm = u*70.0, v*156.0",
            "colour_note": "every 'stored' value is the 8-bit sRGB-encoded number in "
                           "the file divided by 255; 'linear' applies the sRGB EOTF. "
                           "Verified: Blender's Image.pixels returns the stored value "
                           "for 8-bit PNGs, so stored == Image.pixels.",
        }
        if self.ring_bbox:
            x0, y0, x1, y1 = self.ring_bbox
            self.out["_frame"]["ring_bbox_uv"] = _r([x0 / self.W, y0 / self.H,
                                                     x1 / self.W, y1 / self.H], 5)
        return self.out
