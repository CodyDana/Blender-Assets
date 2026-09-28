# -*- coding: utf-8 -*-
"""Stage C: full typography / stroke / ring / flame / seal metrology.

Writes typography.json.  Measurement only - no reference pixels are written.
"""
import sys, os, json, math, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pbmetro as P
import pbtag as T
import pbelem as E

HERE = os.path.dirname(os.path.abspath(__file__))
DEBUG = os.path.join(HERE, "debug")
os.makedirs(DEBUG, exist_ok=True)

CW, CH = T.CARD_W_MM, T.CARD_H_MM

REFDIR = r"C:/Users/Cody/Desktop/Blender_Projects/References/PaperBomb"
V1P = os.path.join(REFDIR, "paperbomb_guide.png")
V2P = os.path.join(REFDIR, "paperbomb_guide_v2_real_glyphs.png")
ARTP = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/art/paperbomb_front_bc.png"
ATLP = r"C:/Users/Cody/Desktop/Blender_Projects/Exports/PaperBomb/Textures/T_PaperBomb_BC.png"
CARDP = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/art/paperbomb_front_card.png"
SNAP = (r"C:/Users/Cody/AppData/Local/Temp/claude/C--Users-Cody-Desktop-Blender-Projects/"
        r"70fec35b-8f87-4dbe-ba33-6e5ba8c5d846/scratchpad/snap/T_PaperBomb_BC.snap.png")


# --------------------------------------------------------------------------
class RectTag(T.Tag):
    """Tag whose card rectangle is supplied instead of detected."""
    def __init__(self, path, rect, name):
        self.path = path
        self.name = name
        self.mtime = os.stat(path).st_mtime
        a = P.load_stored(path)
        self.rgb_raw = a[..., :3]
        x0, y0, w, h = rect
        self.diag = dict(quad=dict(tl=(x0, y0), tr=(x0 + w, y0),
                                   br=(x0 + w, y0 + h), bl=(x0, y0 + h)),
                         width_top_px=w, width_bottom_px=w,
                         height_left_px=h, height_right_px=h,
                         rotation_deg_applied=0.0,
                         note="card rect supplied analytically, not detected")
        self.mask_raw = np.ones(self.rgb_raw.shape[:2], dtype=bool)
        self.rgb, self.mask, self.W, self.H, self.Hm = T.rectify(
            self.rgb_raw, self.mask_raw, self.diag,
            out_w=int(round(w)), out_h=int(round(h)))
        self.black, self.red, self.seg = T.segment(self.rgb, self.mask)
        self.px_per_mm_x = self.W / CW
        self.px_per_mm_y = self.H / CH
        self.px_per_mm = 0.5 * (self.px_per_mm_x + self.px_per_mm_y)


def jclean(o):
    if isinstance(o, dict):
        return {k: jclean(v) for k, v in o.items() if k != 'mask' and k != 'sel'}
    if isinstance(o, (list, tuple)):
        return [jclean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        v = float(o)
        return None if (math.isnan(v) or math.isinf(v)) else round(v, 5)
    if isinstance(o, (np.integer, int)):
        return int(o)
    if isinstance(o, (np.bool_, bool)):
        return bool(o)
    return o


# --------------------------------------------------------------------------
def rule_thickness(ink, col_or_row, idx, axis, n=240):
    """Median ink run length through a border rule, = its true drawn thickness."""
    runs = []
    H, W = ink.shape
    if axis == 'v':
        for y in np.linspace(0.20 * H, 0.80 * H, n).astype(int):
            row = ink[y]
            if not row[idx]:
                continue
            a = idx
            while a > 0 and row[a - 1]:
                a -= 1
            b = idx
            while b < W - 1 and row[b + 1]:
                b += 1
            runs.append(b - a + 1)
    else:
        for x in np.linspace(0.20 * W, 0.80 * W, n).astype(int):
            col = ink[:, x]
            if not col[idx]:
                continue
            a = idx
            while a > 0 and col[a - 1]:
                a -= 1
            b = idx
            while b < H - 1 and col[b + 1]:
                b += 1
            runs.append(b - a + 1)
    if not runs:
        return None
    return dict(n=len(runs), median_px=float(np.median(runs)),
                p25_px=float(np.percentile(runs, 25)),
                p75_px=float(np.percentile(runs, 75)))


def frame_lines(tg):
    """The red/black border rule: where are its vertical and horizontal lines?"""
    ink = tg.black | tg.red
    H, W = ink.shape
    ys, xs = np.mgrid[0:H, 0:W]
    xmm = xs / W * CW
    ymm = ys / H * CH
    out = {}
    # vertical rules: columns in the outer margin with tall ink coverage
    for side, lo, hi in (('left', 0.0, 6.4), ('right', CW - 6.6, CW)):
        band = ink & (xmm >= lo) & (xmm <= hi) & (ymm > 0.18 * CH) & (ymm < 0.82 * CH)
        colcount = band.sum(axis=0).astype(np.float64)
        span = 0.64 * H
        peaks = np.flatnonzero(colcount > 0.35 * span)
        if len(peaks):
            groups = []
            cur = [peaks[0]]
            for p in peaks[1:]:
                if p - cur[-1] <= 2:
                    cur.append(p)
                else:
                    groups.append(cur); cur = [p]
            groups.append(cur)
            res = []
            for g in groups:
                idx = int(g[int(np.argmax(colcount[g]))])
                rt = rule_thickness(ink, None, idx, 'v')
                res.append(dict(x_mm=round(tg.mmx(float(np.mean(g))), 3),
                                x_frac=round(float(np.mean(g)) / W, 5),
                                group_width_mm=round(tg.mmx(len(g)), 3),
                                rule_thickness_mm=round(tg.mmx(rt['median_px']), 3) if rt else None,
                                rule_thickness_p25_mm=round(tg.mmx(rt['p25_px']), 3) if rt else None,
                                rule_thickness_p75_mm=round(tg.mmx(rt['p75_px']), 3) if rt else None,
                                coverage=round(float(colcount[g].max() / span), 3)))
            out[side] = res
    for side, lo, hi in (('top', 0.0, 11.0), ('bottom', CH - 11.0, CH)):
        band = ink & (ymm >= lo) & (ymm <= hi) & (xmm > 0.18 * CW) & (xmm < 0.82 * CW)
        rowcount = band.sum(axis=1).astype(np.float64)
        span = 0.64 * W
        peaks = np.flatnonzero(rowcount > 0.35 * span)
        if len(peaks):
            groups = []
            cur = [peaks[0]]
            for p in peaks[1:]:
                if p - cur[-1] <= 2:
                    cur.append(p)
                else:
                    groups.append(cur); cur = [p]
            groups.append(cur)
            res = []
            for g in groups:
                idx = int(g[int(np.argmax(rowcount[g]))])
                rt = rule_thickness(ink, None, idx, 'h')
                res.append(dict(y_mm=round(tg.mmy(float(np.mean(g))), 3),
                                y_frac=round(float(np.mean(g)) / H, 5),
                                group_width_mm=round(tg.mmy(len(g)), 3),
                                rule_thickness_mm=round(tg.mmy(rt['median_px']), 3) if rt else None,
                                coverage=round(float(rowcount[g].max() / span), 3)))
            out[side] = res
    return out


def ring_report(tg, ring):
    prof = ring['prof']
    deg = np.array([p['deg'] for p in prof])
    thick = np.array([p['thick'] for p in prof])
    ithick = np.array([p['ink_thick'] for p in prof])
    cthick = np.array([p['core_thick'] for p in prof])
    cover = np.array([p['cover'] for p in prof])
    runs = np.array([p['runs'] for p in prof])
    npx = np.array([p['n'] for p in prof])
    rin = np.array([p['r_in'] if p['r_in'] is not None else np.nan for p in prof])
    rout = np.array([p['r_out'] if p['r_out'] is not None else np.nan for p in prof])
    have = npx > 0
    el = ring['ellipse']
    # angular gaps
    gaps = []
    i = 0
    n = len(prof)
    while i < n:
        if not have[i]:
            j = i
            while j + 1 < n and not have[(j + 1) % n]:
                j += 1
            gaps.append((i, j))
            i = j + 1
        else:
            i += 1
    if gaps and gaps[0][0] == 0 and gaps[-1][1] == n - 1 and len(gaps) > 1:
        gaps[0] = (gaps[-1][0] - n, gaps[0][1])
        gaps.pop()
    gap_list = [dict(start_deg=round(float(deg[a % n]), 2),
                     end_deg=round(float(deg[b % n]), 2),
                     width_deg=round((b - a + 1) * 360.0 / n, 2)) for a, b in gaps]
    gap_list.sort(key=lambda g: -g['width_deg'])
    # laps: distribution of radial run counts where there is ink
    rc = runs[have]
    lapc = {int(k): int(v) for k, v in zip(*np.unique(rc, return_counts=True))}
    # concentric-band test: histogram of the mid radius
    midr = 0.5 * (rin + rout)
    th = np.nanmean(thick[have])
    rep = dict(
        centre=tg.pt(ring['cx'], ring['cy']),
        centre_offset_from_tag_centre_mm=[round(tg.mmx(ring['cx']) - CW / 2, 3),
                                          round(tg.mmy(ring['cy']) - CH / 2, 3)],
        ellipse=dict(
            semi_major_mm=round(el['semi_major_px'] / tg.px_per_mm, 3),
            semi_minor_mm=round(el['semi_minor_px'] / tg.px_per_mm, 3),
            semi_x_mm=round(float(np.nanmax(np.abs(np.cos(np.radians(deg[have]))) * midr[have])), 3),
            major_axis_deg=round(el['major_axis_deg'], 2),
            axis_ratio=round(el['axis_ratio'], 4),
            eccentricity=round(el['eccentricity'], 4)) if el else None,
        r_mid_mean_mm=round(float(np.nanmean(midr[have])), 3),
        r_mid_min_mm=round(float(np.nanmin(midr[have])), 3),
        r_mid_max_mm=round(float(np.nanmax(midr[have])), 3),
        r_inner_mean_mm=round(float(np.nanmean(rin[have])), 3),
        r_outer_mean_mm=round(float(np.nanmean(rout[have])), 3),
        r_inner_min_mm=round(float(np.nanmin(rin[have])), 3),
        r_outer_max_mm=round(float(np.nanmax(rout[have])), 3),
        diameter_x_mm=round(2 * float(np.nanmean(midr[have])), 3),
        thickness_mm=dict(
            mean=round(float(np.nanmean(thick[have])), 3),
            median=round(float(np.nanmedian(thick[have])), 3),
            p05=round(float(np.nanpercentile(thick[have], 5)), 3),
            p95=round(float(np.nanpercentile(thick[have], 95)), 3),
            min=round(float(np.nanmin(thick[have])), 3),
            max=round(float(np.nanmax(thick[have])), 3),
            cv=round(float(np.nanstd(thick[have]) / max(th, 1e-6)), 4),
            p95_over_p05=round(float(np.nanpercentile(thick[have], 95) /
                                     max(np.nanpercentile(thick[have], 5), 1e-6)), 3)),
        ink_thickness_mm=dict(
            mean=round(float(np.nanmean(ithick[have])), 3),
            median=round(float(np.nanmedian(ithick[have])), 3),
            p05=round(float(np.nanpercentile(ithick[have], 5)), 3),
            p95=round(float(np.nanpercentile(ithick[have], 95)), 3),
            max=round(float(np.nanmax(ithick[have])), 3),
            cv=round(float(np.nanstd(ithick[have]) / max(np.nanmean(ithick[have]), 1e-6)), 4),
            p95_over_p05=round(float(np.nanpercentile(ithick[have], 95) /
                                     max(np.nanpercentile(ithick[have], 5), 1e-6)), 3)),
        core_thickness_mm=dict(
            mean=round(float(np.nanmean(cthick[have])), 3),
            median=round(float(np.nanmedian(cthick[have])), 3),
            p05=round(float(np.nanpercentile(cthick[have], 5)), 3),
            p95=round(float(np.nanpercentile(cthick[have], 95)), 3),
            cv=round(float(np.nanstd(cthick[have]) / max(np.nanmean(cthick[have]), 1e-6)), 4)),
        radial_modes=ring.get('radial_hist'),
        radial_ink_coverage=dict(
            mean=round(float(np.nanmean(cover[have])), 4),
            p05=round(float(np.nanpercentile(cover[have], 5)), 4),
            p95=round(float(np.nanpercentile(cover[have], 95)), 4)),
        angular_coverage=round(float(have.mean()), 4),
        angular_gaps=gap_list[:8],
        n_angular_gaps=len(gap_list),
        radial_run_count_histogram=lapc,
        frac_angles_with_1_band=round(float((rc == 1).mean()), 4),
        frac_angles_with_2plus_bands=round(float((rc >= 2).mean()), 4),
        frac_angles_with_3plus_bands=round(float((rc >= 3).mean()), 4),
        ring_ink_area_mm2=round(float(ring['n_px']) / (tg.px_per_mm_x * tg.px_per_mm_y), 3),
        profile_36=[dict(deg=round(float(deg[i]), 1),
                         r_in=None if not have[i] else round(float(rin[i]), 2),
                         r_out=None if not have[i] else round(float(rout[i]), 2),
                         thick=round(float(thick[i]), 2),
                         ink_thick=round(float(ithick[i]), 2),
                         cover=round(float(cover[i]), 3),
                         runs=int(runs[i])) for i in range(0, len(prof), max(1, len(prof) // 36))],
    )
    rm = ring.get('radial_hist') or {}
    nmod = rm.get('n_radial_modes')
    rep['lap_verdict'] = dict(
        n_radial_modes=nmod,
        mode_rho=rm.get('mode_rho'),
        fwhm_rho=rm.get('fwhm_rho'),
        brush_width_from_fwhm_mm=(round(rm['fwhm_rho'] * rep['r_mid_mean_mm'], 3)
                                  if rm.get('fwhm_rho') else None),
        verdict=('single lap (one radial mode)' if nmod == 1 else
                 f'{nmod} concentric laps (that many radial modes)' if nmod else 'undetermined'),
        note='radial modes are counted in ellipse-normalised radius rho = r / r_ellipse(theta); '
             'dry-brush streaks inside ONE lap show up as many radial runs but only one mode')
    # taper / travel direction: thickness ramp at either side of the biggest gap
    if gap_list:
        g = gap_list[0]
        i_end = int(np.argmin(np.abs(deg - g['start_deg'])))      # arc ends here
        i_start = int(np.argmin(np.abs(deg - g['end_deg'])))      # arc resumes here
        def ramp(i0, step, k=40):
            vals = []
            for t in range(k):
                j = (i0 + step * t) % n
                if have[j]:
                    vals.append(thick[j])
            return float(np.mean(vals)) if vals else float('nan')
        t_after_gap = ramp(i_start, +1)
        t_before_gap = ramp(i_end, -1)
        c_after = float(np.nanmean([cover[(i_start + t) % n] for t in range(40) if have[(i_start + t) % n]]))
        c_before = float(np.nanmean([cover[(i_end - t) % n] for t in range(40) if have[(i_end - t) % n]]))
        # overlap: is the band locally doubled either side of the break?
        near = [j % n for j in range(i_end - 40, i_end + 1)] + \
               [j % n for j in range(i_start, i_start + 41)]
        near = [j for j in near if have[j]]
        med_core = float(np.nanmedian(cthick[have]))
        loc_core = float(np.nanmedian([cthick[j] for j in near])) if near else float('nan')
        loc_runs = float(np.mean([runs[j] for j in near])) if near else float('nan')
        wet_start = c_after > c_before
        rep['lap_ends'] = dict(
            arc_start_deg=round(float(deg[i_start]), 2),
            arc_end_deg=round(float(deg[i_end]), 2),
            thickness_at_start_mm=round(t_after_gap, 3),
            thickness_at_end_mm=round(t_before_gap, 3),
            coverage_at_start=round(c_after, 3),
            coverage_at_end=round(c_before, 3),
            wetter_end=('arc_start' if wet_start else 'arc_end'),
            wet_to_dry_contrast=round(abs(c_after - c_before) / max(c_after, c_before, 1e-6), 3),
            overlap_core_thickness_mm=round(loc_core, 3),
            ring_core_thickness_mm=round(med_core, 3),
            overlap_thickening=round(loc_core / max(med_core, 1e-6), 3),
            overlap_mean_radial_runs=round(loc_runs, 3),
            implied_travel=(
                'clockwise on screen, from the wet start at %.1f deg round to the dry end at %.1f deg'
                % (deg[i_start], deg[i_end]) if wet_start else
                'anticlockwise on screen, from the wet start at %.1f deg round to the dry end at %.1f deg'
                % (deg[i_end], deg[i_start])),
            note='image-space angles: 0 deg = +x (right), +90 deg = straight DOWN because y '
                 'points down, so increasing angle is clockwise on screen. The wetter, more '
                 'solidly inked end of the arc is taken to be where the brush landed.')
    return rep


# --------------------------------------------------------------------------
def measure(tg, label):
    print(f"\n================ {label} ================")
    out = dict(source=os.path.basename(tg.path), label=label,
               file_mtime=tg.mtime,
               rectified_px=[tg.W, tg.H],
               px_per_mm_x=round(tg.px_per_mm_x, 4), px_per_mm_y=round(tg.px_per_mm_y, 4),
               anisotropy_y_over_x=round(tg.px_per_mm_y / tg.px_per_mm_x, 5),
               rectification=jclean({k: v for k, v in tg.diag.items() if k != 'quad'}),
               segmentation=jclean(tg.seg))
    H, W = tg.black.shape
    ys, xs = np.mgrid[0:H, 0:W]
    xmm = xs / W * CW
    ymm = ys / H * CH
    paperish = tg.mask & ~tg.black & ~tg.red

    out['border_rule'] = frame_lines(tg)

    # ---- ring
    ring = E.fit_ring(tg, tg.red, (5.4, 38.0, 64.6, 114.0))
    out['ring'] = ring_report(tg, ring) if ring else None
    el = ring['ellipse']
    rcx, rcy = ring['cx'], ring['cy']
    sa, sb = el['semi_major_px'], el['semi_minor_px']
    thr = math.radians(el['major_axis_deg'])

    def in_ring(px, py, k):
        dx, dy = px - rcx, py - rcy
        u = dx * math.cos(thr) + dy * math.sin(thr)
        v = -dx * math.sin(thr) + dy * math.cos(thr)
        return (u / (k * sa)) ** 2 + (v / (k * sb)) ** 2 <= 1.0

    # ---- adaptive split of the TOP band into [left column | flame | right column]
    topband = tg.black & (ymm > 6.0) & (ymm < 56.0) & (xmm > 5.2) & (xmm < 66.0)
    xproj = topband.sum(axis=0)
    occ = xproj > max(1, int(0.0015 * H))
    gapx = max(1, int(round(1.2 * tg.px_per_mm_x)))
    segs, _ = P.split_profile(topband[:, :], 1, gapx, max(2, int(2.0 * tg.px_per_mm_x)))
    groups = [(tg.mmx(a), tg.mmx(b)) for a, b in segs]
    print(f"  top-band x groups (mm): {[(round(a,2), round(b,2)) for a, b in groups]}")
    if len(groups) >= 3:
        split_l = 0.5 * (groups[0][1] + groups[1][0])
        split_r = 0.5 * (groups[-2][1] + groups[-1][0])
    else:
        split_l, split_r = 24.0, 46.0
    out['top_band_x_groups_mm'] = [[round(a, 3), round(b, 3)] for a, b in groups]
    out['top_band_splits_mm'] = [round(split_l, 3), round(split_r, 3)]
    print(f"  top-band splits: {split_l:.2f} / {split_r:.2f} mm")

    # ---- black components
    minA = max(30, int(0.000012 * W * H))
    cs = E.comps(tg.black, minA, 1)
    used = set()
    buckets = {k: [] for k in ('centre', 'flame', 'upper_left', 'upper_right',
                               'lower_left', 'lower_right', 'lower_centre', 'other')}
    # the centre glyph = the biggest black mass inside the ring, plus every
    # component that overlaps its box and still sits inside the ring
    cand = [(i, c) for i, c in enumerate(cs) if in_ring(c['cx'], c['cy'], 1.0)]
    if cand:
        bi, big = max(cand, key=lambda t: t[1]['area'])
        for i, c in cand:
            buckets['centre'].append(c); used.add(i)
        bx0, by0, bx1, by1 = big['x0'], big['y0'], big['x1'], big['y1']
        for i, c in enumerate(cs):
            if i in used:
                continue
            ox = min(bx1, c['x1']) - max(bx0, c['x0'])
            oy = min(by1, c['y1']) - max(by0, c['y0'])
            if ox <= 0 or oy <= 0:
                continue
            small = (c['x1'] - c['x0']) * (c['y1'] - c['y0'])
            if (ox * oy) / max(small, 1) < 0.10:
                continue
            if in_ring(c['cx'], c['cy'], 1.10):
                buckets['centre'].append(c); used.add(i)
    for i, c in enumerate(cs):
        if i in used:
            continue
        cxm, cym = tg.mmx(c['cx']), tg.mmy(c['cy'])
        w_mm, h_mm = tg.mmx(c['x1'] - c['x0']), tg.mmy(c['y1'] - c['y0'])
        if w_mm < 1.3 and h_mm < 1.3:
            buckets['other'].append(c); continue
        if (split_l <= cxm <= split_r and 12.0 <= cym <= 52.0
                and not (h_mm < 1.5 and w_mm > 6.0 * h_mm)):      # not a border rule
            buckets['flame'].append(c)
        elif cxm < split_l and cym < 88.0 and cxm > 5.2:
            buckets['upper_left'].append(c)
        elif cxm > split_r and cym < 88.0 and cxm < 66.0:
            buckets['upper_right'].append(c)
        elif cxm < 24.0 and 88.0 <= cym < 114.0 and cxm > 5.2:
            buckets['lower_left'].append(c)
        elif cxm > 44.0 and 88.0 <= cym < 130.0 and cxm < 66.0:
            buckets['lower_right'].append(c)
        elif 22.0 <= cxm <= 48.0 and 100.0 <= cym < 143.0:
            buckets['lower_centre'].append(c)
        else:
            buckets['other'].append(c)

    # drop stray specks from the column buckets (they would inflate the bbox)
    for k in ('upper_left', 'upper_right', 'lower_left', 'lower_right', 'lower_centre'):
        tot = sum(c['area'] for c in buckets[k]) or 1
        drop = [c for c in buckets[k] if c['area'] < 0.02 * tot]
        buckets[k] = [c for c in buckets[k] if c['area'] >= 0.02 * tot]
        buckets['other'].extend(drop)

    for k, v in buckets.items():
        print(f"  bucket {k}: {len(v)} comps, area {sum(c['area'] for c in v)}")

    # ---- centre glyph
    if buckets['centre']:
        cm = E.union([c['mask'] for c in buckets['centre']], (H, W))
        g = E.describe_glyph(tg, cm, 'centre_bao')
        g['n_components'] = len(buckets['centre'])
        g['component_boxes'] = [tg.box(c['x0'], c['y0'], c['x1'], c['y1'])
                                for c in buckets['centre']]
        # is the glyph one connected mass, or does a radical float free?
        bl = sorted(buckets['centre'], key=lambda c: -c['area'])
        if len(bl) > 1:
            main = bl[0]
            seps = []
            for c in bl[1:]:
                ox = min(main['x1'], c['x1']) - max(main['x0'], c['x0'])
                oy = min(main['y1'], c['y1']) - max(main['y0'], c['y0'])
                # true ink-to-ink distance, sampled on the smaller component
                cy_, cx_ = np.nonzero(c['mask'])
                dmin = None
                if len(cx_) and main['mask'].any():
                    dd = P.edt(~main['mask'])
                    k = np.linspace(0, len(cx_) - 1, min(len(cx_), 4000)).astype(int)
                    dmin = float(dd[cy_[k], cx_[k]].min())
                seps.append(dict(
                    area_px=c['area'],
                    bbox=tg.box(c['x0'], c['y0'], c['x1'], c['y1']),
                    bbox_overlap_x_mm=round(tg.mmx(ox), 3) if ox > 0 else round(tg.mmx(ox), 3),
                    bbox_overlap_y_mm=round(tg.mmy(oy), 3) if oy > 0 else round(tg.mmy(oy), 3),
                    ink_gap_to_main_mm=round(dmin / tg.px_per_mm, 3) if dmin is not None else None))
            g['satellite_components'] = seps
            g['radical_detached'] = bool(
                seps and (seps[0]['ink_gap_to_main_mm'] or 0) > 1.0 and
                seps[0]['bbox_overlap_x_mm'] <= 0)
        # relation to the ring
        gx0, gy0, gx1, gy1 = E.bbox_of(cm)
        gcx, gcy = 0.5 * (gx0 + gx1), 0.5 * (gy0 + gy1)
        iys, ixs = np.nonzero(cm)
        rmm = 0.5 * (sa / tg.px_per_mm + sb / tg.px_per_mm)
        g['in_ring'] = dict(
            ring_mean_radius_mm=round(rmm, 3),
            ring_mean_diameter_mm=round(2 * rmm, 3),
            glyph_bbox_w_over_ring_diam=round(tg.mmx(gx1 - gx0) / (2 * rmm), 4),
            glyph_bbox_h_over_ring_diam=round(tg.mmy(gy1 - gy0) / (2 * rmm), 4),
            glyph_diag_over_ring_diam=round(
                math.hypot(tg.mmx(gx1 - gx0), tg.mmy(gy1 - gy0)) / (2 * rmm), 4),
            glyph_area_over_ring_inner_area=round(
                (float(cm.sum()) / (tg.px_per_mm_x * tg.px_per_mm_y)) /
                (math.pi * (out['ring']['r_inner_mean_mm'] ** 2)), 4),
            bbox_centre_offset_mm=[round(tg.mmx(gcx) - tg.mmx(rcx), 3),
                                   round(tg.mmy(gcy) - tg.mmy(rcy), 3)],
            ink_centroid_offset_mm=[round(tg.mmx(float(ixs.mean())) - tg.mmx(rcx), 3),
                                    round(tg.mmy(float(iys.mean())) - tg.mmy(rcy), 3)],
        )
        # clear space: per-angle distance from glyph ink to ring inner edge
        prof = ring['prof']
        clears = []
        crossings = 0
        for p in prof:
            if p['r_in'] is None:
                continue
            a = math.radians(p['deg'])
            # march inward from the ring inner radius until we hit glyph ink
            hit = None
            r = p['r_in']
            while r > 1.0:
                px = rcx + (r * math.cos(a)) / CW * W
                py = rcy + (r * math.sin(a)) / CH * H
                ix, iy = int(px), int(py)
                if 0 <= ix < W and 0 <= iy < H and cm[iy, ix]:
                    hit = p['r_in'] - r
                    break
                r -= 0.25
            if hit is not None:
                clears.append(hit)
            # does the glyph cross the ring band?
            px = rcx + ((p['r_in'] + p['r_out']) * 0.5 * math.cos(a)) / CW * W
            py = rcy + ((p['r_in'] + p['r_out']) * 0.5 * math.sin(a)) / CH * H
            ix, iy = int(px), int(py)
            if 0 <= ix < W and 0 <= iy < H and cm[iy, ix]:
                crossings += 1
        if clears:
            g['in_ring']['clear_space_mm'] = dict(
                min=round(float(np.min(clears)), 3),
                p05=round(float(np.percentile(clears, 5)), 3),
                median=round(float(np.median(clears)), 3),
                mean=round(float(np.mean(clears)), 3),
                max=round(float(np.max(clears)), 3),
                n_angles_measured=len(clears))
        g['in_ring']['frac_angles_glyph_crosses_ring_band'] = round(crossings / max(len(prof), 1), 4)
        out['centre_glyph'] = g

    # ---- flame emblem
    if buckets['flame']:
        fm = E.union([c['mask'] for c in buckets['flame']], (H, W))
        f = E.describe_glyph(tg, fm, 'flame_emblem')
        f['n_components'] = len(buckets['flame'])
        f['component_boxes'] = [tg.box(c['x0'], c['y0'], c['x1'], c['y1'])
                                for c in buckets['flame']]
        fx0, fy0, fx1, fy1 = E.bbox_of(fm)
        # tongues: count separate ink runs across the emblem's upper half
        rows = []
        for fr in (0.05, 0.12, 0.20, 0.30, 0.40, 0.50, 0.65, 0.80, 0.92):
            yy = int(fy0 + fr * (fy1 - fy0))
            rr = P.runs_along(fm[yy:yy + 1, fx0:fx1], 1)
            rows.append(dict(at_frac_of_height=fr,
                             n_runs=int(len(rr)),
                             run_widths_mm=[round(float(v) / tg.px_per_mm_x, 2) for v in rr]))
        f['horizontal_cuts'] = rows
        # tongue count = separate components of the emblem's top 45%
        topm = fm.copy()
        topm[int(fy0 + 0.46 * (fy1 - fy0)):, :] = False
        lt, nt = P.label_cc(topm)
        stt = [s for s in P.cc_stats(lt, nt) if s and s['area'] > 0.004 * fm.sum()]
        f['n_tongues_top46pct'] = len(stt)
        f['tongues'] = []
        for s in sorted(stt, key=lambda s: s['cx']):
            sm = (lt == s['label'])
            tb = tg.box(s['x0'], s['y0'], s['x1'], s['y1'])
            tp = P.taper_profile(sm[s['y0']:s['y1'], s['x0']:s['x1']])
            f['tongues'].append(dict(bbox=tb, area_mm2=round(
                s['area'] / (tg.px_per_mm_x * tg.px_per_mm_y), 3),
                length_mm=round(tp['length_px'] / tg.px_per_mm, 3) if tp else None,
                axis_deg=round(tp['axis_deg'], 2) if tp else None,
                taper_profile_px=tp['profile_px'] if tp else None))
        # spiral at the heart: paper-coloured island(s) enclosed by the emblem
        sub = fm[fy0:fy1, fx0:fx1]
        holes = ~sub
        lh, nh = P.label_cc(holes)
        edge = set(np.unique(np.concatenate([lh[0, :], lh[-1, :], lh[:, 0], lh[:, -1]])))
        edge.discard(0)
        hs = [s for s in P.cc_stats(lh, nh) if s and s['label'] not in edge and s['area'] > 6]
        hs.sort(key=lambda s: -s['area'])
        f['n_enclosed_holes'] = len(hs)
        f['enclosed_holes'] = [dict(bbox=tg.box(fx0 + s['x0'], fy0 + s['y0'],
                                                fx0 + s['x1'], fy0 + s['y1']),
                                    area_mm2=round(s['area'] / (tg.px_per_mm_x * tg.px_per_mm_y), 4))
                               for s in hs[:8]]
        # spiral at the heart: cast rays from the centre of the largest enclosed
        # hole and count ink/paper alternations -> number of turns
        # the eye = the largest empty disc inside the emblem's own box, so this
        # works whether the curl closes on itself or stays open
        subf = fm[fy0:fy1, fx0:fx1]
        dpap = P.edt(~subf)
        hh, ww = subf.shape
        core = np.zeros_like(dpap)
        core[int(0.25 * hh):int(0.75 * hh), int(0.25 * ww):int(0.75 * ww)] = 1.0
        ey, ex = np.unravel_index(int(np.argmax(dpap * core)), dpap.shape)
        if True:
            scx = fx0 + float(ex)
            scy = fy0 + float(ey)
            rmax = 0.55 * max(fx1 - fx0, fy1 - fy0)
            crossings = []
            for k in range(72):
                a = k / 72.0 * 2 * math.pi
                seq = []
                r = 1.0
                while r < rmax:
                    ix = int(scx + r * math.cos(a))
                    iy = int(scy + r * math.sin(a))
                    if not (0 <= ix < W and 0 <= iy < H):
                        break
                    seq.append(bool(fm[iy, ix]))
                    r += 0.5
                nr = sum(1 for i in range(1, len(seq)) if seq[i] and not seq[i - 1])
                crossings.append(nr)
            f['spiral'] = dict(
                centre=tg.pt(scx, scy),
                centre_offset_from_emblem_centre_mm=[
                    round(tg.mmx(scx) - tg.mmx(0.5 * (fx0 + fx1)), 3),
                    round(tg.mmy(scy) - tg.mmy(0.5 * (fy0 + fy1)), 3)],
                eye_radius_mm=round(float(dpap[ey, ex]) / tg.px_per_mm, 3),
                largest_enclosed_hole_w_mm=(round(tg.mmx(hs[0]['x1'] - hs[0]['x0']), 3)
                                            if hs else None),
                largest_enclosed_hole_h_mm=(round(tg.mmy(hs[0]['y1'] - hs[0]['y0']), 3)
                                            if hs else None),
                largest_enclosed_hole_area_mm2=(
                    round(hs[0]['area'] / (tg.px_per_mm_x * tg.px_per_mm_y), 4) if hs else None),
                ray_ink_bands_median=float(np.median(crossings)),
                ray_ink_bands_max=int(np.max(crossings)),
                ray_ink_bands_hist={int(k): int(v) for k, v in
                                    zip(*np.unique(crossings, return_counts=True))},
                turns_estimate=round(float(np.median(crossings)) - 0.5, 2),
                note='bands counted outward from the spiral eye; an n-turn spiral '
                     'crosses about n ink bands on a typical ray')
        # mirror symmetry about the emblem's own vertical mid-line
        sub_f = sub.astype(np.float32)
        best = None
        for shift in range(-6, 7):
            a = np.roll(sub_f, shift, axis=1)
            b = a[:, ::-1]
            inter = float((a * b).sum())
            uni = float(((a + b) > 0).sum())
            iou = inter / max(uni, 1)
            if best is None or iou > best[1]:
                best = (shift, iou)
        f['mirror_symmetry'] = dict(best_shift_px=best[0],
                                    best_iou=round(best[1], 4),
                                    verdict=('mirror-symmetric' if best[1] > 0.88 else
                                             'near-symmetric' if best[1] > 0.78 else
                                             'hand-asymmetric'))
        out['flame_emblem'] = f

    # ---- columns
    # V1's side columns are PSEUDO-glyphs, so a known glyph count must not be
    # forced on them; V2 and our build carry the real characters.
    known = label != "V1"
    expect = dict(upper_left=3, upper_right=3, lower_right=2, lower_centre=2) if known else {}
    for key in ('upper_left', 'upper_right', 'lower_left', 'lower_right', 'lower_centre'):
        if not buckets[key]:
            continue
        col = E.describe_column(tg, buckets[key], key, expect.get(key))
        if col:
            col.pop('mask', None)
            out['column_' + key] = col

    # ---- seals
    # keep the border rule out of the seal windows
    fz = np.zeros_like(tg.black)
    for side in ('left', 'right'):
        for rr in (out['border_rule'].get(side) or []):
            fz |= np.abs(xmm - rr['x_mm']) < 0.9
    for side in ('top', 'bottom'):
        for rr in (out['border_rule'].get(side) or []):
            fz |= np.abs(ymm - rr['y_mm']) < 0.9
    out['seal_big'] = E.seal_metrics2(tg, tg.red, paperish, (3.2, 110.0, 32.0, 152.0),
                                      'seal_big', frame_zone=fz)
    out['seal_small'] = E.seal_metrics2(tg, tg.red, paperish, (52.0, 116.0, 66.5, 148.0),
                                        'seal_small', frame_zone=fz)
    # text inside the small seal: red glyphs inside the small seal's inner hole
    if out['seal_small'] and 'inner_bbox' in out['seal_small']:
        ib = out['seal_small']['inner_bbox']
        wx0 = int(ib['x0_frac'] * W); wx1 = int(ib['x1_frac'] * W)
        wy0 = int(ib['y0_frac'] * H); wy1 = int(ib['y1_frac'] * H)
        inner = np.zeros_like(tg.red)
        inner[wy0:wy1, wx0:wx1] = tg.red[wy0:wy1, wx0:wx1]
        if inner.sum() > 20:
            cells, prof = E.column_cells(tg, inner, 0.35, 0.7)
            out['seal_small']['text'] = dict(
                n_cells=len(cells),
                cells=[E.describe_glyph(tg, c, f'small_seal[{i}]') for i, c in enumerate(cells)])
    for k in ('seal_big', 'seal_small'):
        if out.get(k):
            out[k].pop('mask', None)

    # ---- inventory of anything unassigned (ornaments, frame)
    out['unassigned_black'] = [dict(area_px=c['area'],
                                    bbox=tg.box(c['x0'], c['y0'], c['x1'], c['y1']))
                               for c in buckets['other'][:24]]
    return out, ring, buckets


# --------------------------------------------------------------------------
def atlas_card_rect(art_path, atlas_path, art_rect):
    """Map the art map's exact card rect into the shipped atlas by matching the
    black-ink bounding box of the same drawing."""
    a = P.load_stored(art_path)[..., :3]
    b = P.load_stored(atlas_path)[..., :3]
    La = P.luma_stored(a); Lb = P.luma_stored(b)
    ma = La < 0.45
    mb = Lb < 0.45
    mb[:, mb.shape[1] // 2:] = False        # left island only
    xa0, ya0, xa1, ya1 = E.bbox_of(ma)
    xb0, yb0, xb1, yb1 = E.bbox_of(mb)
    sx = (xb1 - xb0) / (xa1 - xa0)
    sy = (yb1 - yb0) / (ya1 - ya0)
    tx = xb0 - sx * xa0
    ty = yb0 - sy * ya0
    x0, y0, w, h = art_rect
    print(f"  atlas match: ink bbox art=({xa0},{ya0},{xa1},{ya1}) atlas=({xb0},{yb0},{xb1},{yb1})")
    print(f"  atlas affine sx={sx:.6f} sy={sy:.6f} tx={tx:.3f} ty={ty:.3f}")
    return (x0 * sx + tx, y0 * sy + ty, w * sx, h * sy), dict(sx=sx, sy=sy, tx=tx, ty=ty)


# --------------------------------------------------------------------------
t0 = time.time()
results = {}
rings = {}

for label, path in (("V1", V1P), ("V2", V2P)):
    tg = T.Tag(path, 'guide', 'left', label)
    r, ring, buckets = measure(tg, label)
    r['tag_detection'] = jclean(tg.diag)
    results[label] = r
    rings[label] = (tg, ring)
    print(f"  [{label}] done {time.time()-t0:.1f}s")

# ours: exact card rect from the module's own geometry, verified by the card mask
ppmm = 12.923
pad = 1.6
ART_RECT = (pad * ppmm, pad * ppmm, CW * ppmm, CH * ppmm)
tg = RectTag(ARTP, ART_RECT, "OURS_ART")
r, ring, buckets = measure(tg, "OURS_ART")
results["OURS_ART"] = r
rings["OURS_ART"] = (tg, ring)
print(f"  [OURS_ART] done {time.time()-t0:.1f}s")

tg2 = T.Tag(SNAP, 'atlas', 'left', "OURS_ATLAS")
r2, ring2, b2 = measure(tg2, "OURS_ATLAS")
r2['tag_detection'] = jclean(tg2.diag)
r2['note'] = ("the shipped T_PaperBomb_BC.png, snapshotted while the build kept "
              "re-exporting; the card UV island was detected from its grain/deckle "
              "edge energy and rectified")
results["OURS_ATLAS"] = r2
rings["OURS_ATLAS"] = (tg2, ring2)
print(f"  [OURS_ATLAS] done {time.time()-t0:.1f}s")

meta = dict(
    generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
    tool="WorkFiles/paperbomb/reference_metrology/stage_c_measure.py (Blender 5.2 python, numpy "
         + np.__version__ + ")",
    colour_convention="all pixel values are STORED (sRGB-encoded) 0..1 unless a key says 'linear'; "
                      "images loaded with colorspace Non-Color so no sRGB->linear conversion is applied",
    coordinate_convention="origin at the TAG's top-left corner, x right, y down; fractions of the "
                          "tag's own W and H, plus mm on the shipped 70.0 x 156.0 mm card",
    ink_threshold_rule="binarised at the 50% contrast crossing between the paper level (luma p75 "
                       "inside the tag) and the ink floor (luma p0.5), so images of different ink "
                       "density are compared on equal footing",
    legal="MEASUREMENT ONLY. No reference pixels, crops, masks, traces or derived images are "
          "written by this tool. Numbers only.",
    files=dict(V1=V1P, V2=V2P, OURS_ART=ARTP, OURS_ATLAS=ATLP),
)
doc = dict(meta=meta, measurements=jclean(results))
outp = os.path.join(HERE, "typography_raw.json")
with open(outp, "w", encoding="utf-8") as fh:
    json.dump(doc, fh, ensure_ascii=False, indent=1)
print("\nwrote", outp, f"{os.path.getsize(outp)} bytes, {time.time()-t0:.1f}s")
