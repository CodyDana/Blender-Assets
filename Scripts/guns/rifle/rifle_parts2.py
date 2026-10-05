"""Stage 2 form, continued: the parts that are NOT in the detail pass (frame M, mm) - fore-end (gas tube cap, upper
and lower handguards, front band), gas tube / piston / block, barrel, buttstock, rear sling swivel and the stock
hardware - plus the shared helpers (xprism / ycyl / xcyl) and interface constants (BORE_R, TUBE_Z / TUBE_R,
ROD_Z / ROD_R, CATCH_PIVOT) the detail-part modules import. The detailed parts live in Scripts/guns/rifle/parts/
(detail pass 2026-10-04). See rifle_parts.py for the rules."""
from __future__ import annotations

import math

import numpy as np

from rifle_common import SPEC
from gunlib import geo2d as G
from gunlib import mesh as MS
from gunlib import lod as LOD
from gunlib.parts import PartDef
import rifle_parts as RP
from rifle_parts import GAP, prof

BORE_R = 7.5                     # barrel radius (dia 15.0)
TUBE_Z, TUBE_R = 24.2, 9.7       # gas tube axis and radius
ROD_Z, ROD_R = -12.1, 2.0


def grown_prism(outline, grow=GAP, y=40.0):
    return MS.prism(G.offset(G.ccw(outline), grow), -y, y)


def xprism(sec_yz, x0, x1):
    return MS.prism(np.asarray(sec_yz, float), x0, x1, "YZ")


def ycyl(x, z, r, y0, y1, n=32):
    return MS.cylinder((x, y0, z), (x, y1, z), r, n)


def xcyl(y, z, r, x0, x1, n=32):
    return MS.cylinder((x0, y, z), (x1, y, z), r, n)


# ======================================================================================== fore-end
def upper_hg_section(zt, half_w=15.5, zb=13.12, n=24):     # (24: integration-round budget; every user takes the default)
    zc = zt - half_w
    a = np.linspace(0, math.pi, LOD.ring(n))          # LOD: fewer arc points (every user, so the rings match)
    arc = np.c_[half_w * np.cos(a), zc + half_w * np.sin(a)]
    return np.vstack([[half_w, zb], arc, [-half_w, zb]])


def upper_top(x):
    pts = [(534.0, 41.6), (540.0, 42.4), (566.0, 42.7), (594.0, 42.2), (620.0, 41.0), (637.8, 39.6), (639.5, 37.0), (641.0, 37.0)]
    return float(G.polyline_interp(pts, x))


def gas_tube_rear_cap() -> PartDef:
    sec = upper_hg_section(41.1, 16.0, 13.12)
    sol = [xprism(sec, 524.02, 536.2)]
    side = [(524.02, 13.12), (535.0, 13.12), (535.0, 39.6), (533.4, 41.1),
            (528.4, 41.1), (526.3, 36.8), (524.02, 35.6)]
    p = PartDef("gas_tube_rear_cap", sol, cls="M-chamfer")
    p.section_intersect_pre = [MS.prism(side, -30, 30)]
    p.cutters = [xcyl(0.0, TUBE_Z, TUBE_R + GAP, 520.0, 540.0, 32),
                 xprism(upper_hg_section(39.8 + GAP, 14.3 + GAP, 13.0), 534.0 - GAP, 540.0)]     # tenon pocket
    return p


def upper_handguard() -> PartDef:
    xs = np.r_[535.02, 540.0, 553.0, 566.0, 580.0, 594.0, 607.0, 620.0, 629.0, 637.8, 639.5, 640.88]   # the top polyline's knots (budget; was 13 even stations)
    rings = [upper_hg_section(upper_top(x), 15.5, 13.12) for x in xs]
    rings3 = [np.c_[np.full(len(r), x), r[:, 0], r[:, 1]] for x, r in zip(xs, rings)]
    body = MS.loft(rings3)
    tenon = xprism(upper_hg_section(39.8, 14.3, 13.12), 534.0, 535.1)
    cut = [xcyl(0.0, TUBE_Z, TUBE_R + GAP, 530.0, 645.0, 32),
           MS.box(530.0, 645.0, -(TUBE_R + GAP), TUBE_R + GAP, 12.0, TUBE_Z)]       # channel open to the bottom
    for xa, xb in ((543.0, 571.0), (595.0, 623.0)):
        o = G.rounded_rect(xa, xb, 10.0, 16.6, 1.0, 3)
        for s in (-1, 1):
            cut.append(MS.prism(o, min(s * 12.5, s * 20), max(s * 12.5, s * 20)))
    return PartDef("upper_handguard", [body], unions=[tenon], cutters=cut, cls="W-round", slot="M_AR01_Furniture",
                   recipe=[(1.0, 2, "W", _upper_hg_bevel)], joint={"type": "butt", "parent": "gas_tube", "gap_mm": [0.01, 0.05]})


def _upper_hg_bevel(mid, d, n1, n2, dih):
    """The W-round 1.0 pass on every >= 35 deg edge except the concave tenon junction at the rear face: its fillet
    grew 0.02 behind the face into the rear cap (G5, integration round)."""
    if dih < 35.0:
        return 0.0
    if mid[0] > 639.2:                               # the front end inside the band's pocket (hidden): its concave
        return 0.0                                   # step fillet reached into the band (G5)
    if mid[0] < 535.6 and abs(mid[1]) < 14.9 and (mid[2] <= 25.5 or math.hypot(mid[1], mid[2] - 25.5) < 14.9):
        return 0.0                                   # inside the tenon's outline (straight sides + arc)
    return 1.0


def lower_bottom(x):
    pts = [(484.0, -29.6), (485.5, -31.3), (489.6, -32.9), (495.6, -33.2), (498.0, -32.9), (502.9, -31.8),
           (504.2, -31.1), (512.7, -28.7), (526.0, -26.0), (554.0, -24.8), (631.8, -22.9), (636.7, -22.3),
           (639.5, -19.6), (641.0, -19.6)]
    return float(G.polyline_interp(pts, x))


def lower_halfw(x):
    return float(np.interp(x, [484.0, 560.0, 639.5, 641.0], [21.2, 21.2, 19.8, 19.8]))


def lower_hg_section(x, top=13.1, n_c=6):
    w = lower_halfw(x) - 0.5          # TOP width includes the 0.5 side swell
    zb = lower_bottom(x)
    rb = min(13.0, 0.45 * (top - zb))
    pts = [[w, top]]
    pts += [[w, zb + rb]]
    pts += list(G.arc(w - rb, zb + rb, rb, 0, -90, n_c + 1)[1:])
    pts += list(G.arc(-w + rb, zb + rb, rb, -90, -180, n_c + 1))
    pts += [[-w, top]]
    P = np.array(pts, float)
    # slight swell of the sides (0.5 mm at mid-height)
    zm = 0.5 * (top + zb)
    side = np.abs(P[:, 0]) > w - 0.01
    P[side, 0] += np.sign(P[side, 0]) * 0.5 * np.clip(1 - ((P[side, 1] - zm) / (0.5 * (top - zb))) ** 2, 0, 1)
    return G.fillet(P, 1.5, 3)


def lower_handguard() -> PartDef:
    xs = np.r_[np.linspace(485.32, 512.0, 6), np.linspace(516.0, 636.7, 4), 639.5, 640.88]   # (4: the bottom is straight there; budget)
    rings = []
    for x in xs:
        s = lower_hg_section(x)
        rings.append(np.c_[np.full(len(s), x), s[:, 0], s[:, 1]])
    n = min(len(r) for r in rings)
    rings = [r[:n] if len(r) == n else r for r in rings]
    body = MS.loft(rings)
    tenon = RP.lower_handguard_tenon(0.0, 484.0, 485.4)
    cav = G.rounded_rect(-11.0, 11.0, -15.0, 20.0, 6.0, 4)
    cut = [xprism(cav, 480.0, 645.0)]
    # slot dips under the upper guard's slots: sloped notch, 13.1 at the slot's rear to 10.5 at its front wall
    for xa, xb in ((543.0, 571.0), (595.0, 623.0)):
        o = [(xa, 13.1), (xb, 10.5), (xb, 20.0), (xa, 20.0)]
        for s in (-1, 1):
            cut.append(MS.prism(o, min(s * 12.5, s * 30), max(s * 12.5, s * 30)))
    return PartDef("lower_handguard", [body], unions=[tenon], cutters=cut, cls="W-round", slot="M_AR01_Furniture",
                   recipe=[(1.2, 2, 35.0)], joint={"type": "butt", "parent": "receiver", "gap_mm": [0.01, 0.05]})


def front_band() -> PartDef:
    # outer section: lower part follows the lower guard (+0.6), upper part the upper guard (+0.6)
    lo = lower_hg_section(640.9)
    lo = G.offset(G.ccw(lo), 0.6)
    up = upper_hg_section(upper_top(640.9) + 0.6, 15.5 + 0.6, 12.5)
    sol = [xprism(lo, 639.6, 647.1), xprism(up, 639.6, 647.1)]
    cut = [xprism(G.offset(G.ccw(lower_hg_section(640.9)), GAP), 639.0, 640.9 + GAP),
           xprism(upper_hg_section(upper_top(640.9) + GAP, 15.5 + GAP, 13.0), 639.0, 640.9 + GAP),
           xcyl(0.0, 0.0, BORE_R + GAP, 630.0, 650.0, 48),
           xcyl(0.0, TUBE_Z, TUBE_R + GAP, 630.0, 650.0, 32),
           xcyl(0.0, ROD_Z, ROD_R + GAP, 630.0, 650.0, 16),
           xprism(G.rounded_rect(-11.0, 11.0, -15.0, 20.0, 6.0, 4), 639.0, 640.9 + GAP)]
    return PartDef("handguard_front_band", sol[:1], unions=sol[1:], cutters=cut, cls="S-bend",
                   recipe=[(0.6, 1, 30.0)])


def gas_tube() -> PartDef:
    t = MS.tube((519.02, 0, TUBE_Z), (690.98, 0, TUBE_Z), 8.4, TUBE_R, 32)
    cut = []
    for xc in (664.25, 670.5, 676.75):
        o = G.rounded_rect(xc - 2.5, xc + 2.5, TUBE_Z - 1.5, TUBE_Z + 1.5, 1.49, 4)
        cut.append(MS.prism(o, -12.0, 12.0))
    p = PartDef("gas_tube", [t], cutters=cut, cls="M-chamfer", recipe=[(0.3, 1, 30.0)])
    return p


def gas_piston() -> PartDef:
    """Piston head inside the gas tube, seen through the vents (static here; 0.4 mm radial clearance)."""
    return PartDef("gas_piston", [xcyl(0.0, TUBE_Z, 8.0, 655.0, 689.0, 32)], cls="M-chamfer",
                   recipe=[(0.3, 1, 30.0)], spec_id="gas_tube",
                   joint={"type": "sliding", "parent": "gas_tube", "clearance_mm": [0.15, 0.4],
                          "note": "rides with the carrier in reality; static at this stage"})


def gas_block() -> PartDef:
    P = prof("gas_block", 0.5)
    side = MS.prism(P, -10.75, 10.75)
    stad = np.vstack([G.arc(0, 23.05, 10.75, 0, 180, 17), G.arc(0, 0.0, 10.75, 180, 360, 17)])
    lug = G.rounded_rect(-5.0, 5.0, -18.5, -6.0, 1.0, 2)
    p = PartDef("gas_block", [side], cls="M-chamfer-front", recipe=[(0.6, 1, 30.0)])
    p.section_intersect_pre = [xprism(G.ccw(stad), 670.0, 745.0), xprism(lug, 670.0, 745.0)]
    p.cutters = [xcyl(0.0, TUBE_Z, TUBE_R + GAP, 676.0, 691.0, 32),
                 xcyl(0.0, 0.0, BORE_R + GAP, 676.0, 745.0, 48),
                 xcyl(0.0, ROD_Z, ROD_R + GAP, 676.0, 745.0, 16)]
    p.unions = [ycyl(713.5, 12.0, 2.4, -11.3, 11.3, 24)]           # pin boss both sides (on the arm)
    return p


def barrel() -> PartDef:
    b = xcyl(0.0, 0.0, BORE_R, 433.8, 848.78, 48)
    cut = [xcyl(0.0, 0.0, 3.81, 820.0, 849.5, 32),                 # bore, >= 2 calibres deep
           MS.revolve([(0.0, 3.81 + 0.6), (0.6, 3.81), (0.61, 0.0)], (848.78 + 0.001, 0, 0), (-1, 0, 0), 32)]
    # (integration round, budget: the chamber cuts at the rear end are gone; that end sits inside the carrier's
    # pocket, never seen)
    return PartDef("barrel", [b], cutters=cut, cls="M-chamfer", recipe=[(0.4, 1, 30.0)])
# ======================================================================================== trigger group interface
CATCH_PIVOT = (362.0, -50.0)    # mag catch pin: the catch (parts/receiver_right) and its cheeks (parts/trigger_guard)


# ======================================================================================== furniture


def stock_zt_zb():
    P = G.clean_smooth(SPEC.profile("buttstock"), 0.6, 1.2, 35.0)
    return P


def stock_halfw(x):
    w = SPEC.dims("buttstock")["width_by_X_TOP"]
    xs = np.array(sorted(float(k) for k in w))
    ws = np.array([w[k] for k in sorted(w, key=float)])
    return np.interp(x, xs, ws) / 2.0


# section edge radius. The spec read "edges R 6-8"; the 3/4 view (form fix round 1, gates/form.json "stock 3/4
# section sweep") shows a rounder butt: zone IoU 0.9115 at R 7 -> 0.9185 at R 13, saturating at 13-15, and c7 draws
# the plate ends with radii ~0.35 of the width (~13 mm). The wrist keeps R 7 (round 0, spec range) so the flat left inlet
# plate stays seated on a flat side.
STOCK_R = 13.0
STOCK_NR = 46          # ring vertices (corner-weighted sampling: ~5 segments per R 13 corner)
STOCK_R_WRIST = 7.0    # the radius blends from STOCK_R (X <= 140) to this at the wrist (X >= 185)


def stock_r(x):
    if STOCK_R_WRIST is None:
        return STOCK_R
    t = min(max((x - 140.0) / 45.0, 0.0), 1.0)
    return STOCK_R + (STOCK_R_WRIST - STOCK_R) * t


def stock_section(x, zt, zb, n=160, w_override=None, r_max=None):
    w = (stock_halfw(x) if w_override is None else w_override) - 0.6     # TOP width includes the 0.6 side swell
    h = zt - zb
    r = min(stock_r(x) if r_max is None else r_max, 0.3 * h, 0.45 * 2 * w)
    rr = G.rounded_rect(-w, w, zb, zt, r, 6)
    R = G.resample(rr, (2 * (2 * w + h)) / n)[:n]
    zm = 0.5 * (zt + zb)
    side = np.abs(R[:, 0]) > w - r * 0.3
    bul = 0.6 * np.clip(1 - ((R[:, 1] - zm) / (0.5 * h - r + 1e-6)) ** 2, 0, 1)
    R[:, 0] += np.sign(R[:, 0]) * bul * side
    return R


def resample_ring(P, n, start_angle=-90.0, turn_weight=0.0):
    """Resample a closed ring to n points starting at the point nearest the given polar angle (consistent lofts).
    turn_weight (mm per radian) adds the turning angle to the arc-length measure, so rounded corners get more of
    the n points than flat runs (the same rule on every ring keeps the loft consistent)."""
    P = G.ccw(P)
    c = P.mean(axis=0)
    ang = np.degrees(np.arctan2(P[:, 1] - c[1], P[:, 0] - c[0]))
    k = int(np.argmin(np.abs(((ang - start_angle) + 180) % 360 - 180)))
    P = np.roll(P, -k, axis=0)
    Q = np.vstack([P, P[:1]])
    seg = np.diff(Q, axis=0)
    ln = np.linalg.norm(seg, axis=1)
    if turn_weight > 0:
        hd = np.arctan2(seg[:, 1], seg[:, 0])
        turn = np.abs((np.diff(np.r_[hd[-1], hd]) + np.pi) % (2 * np.pi) - np.pi)
        ln = ln + turn_weight * 0.5 * (turn + np.r_[turn[1:], turn[:1]])
    dd = np.r_[0, np.cumsum(ln)]
    t = np.linspace(0, dd[-1], n, endpoint=False)
    return np.c_[np.interp(t, dd, Q[:, 0]), np.interp(t, dd, Q[:, 1])]


def _gauss_smooth_1d(y, sigma_pts):
    if sigma_pts <= 0:
        return y
    r = int(3 * sigma_pts) + 1
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma_pts) ** 2)
    k /= k.sum()
    yp = np.r_[np.full(r, y[0]), y, np.full(r, y[-1])]
    return np.convolve(yp, k, mode="same")[r:-r]


def stock_lines():
    """Top / bottom lines and half width of the stock, sampled every 1 mm and smoothed along X (the comb nose
    step X 150-170 keeps a short kernel so its crisp concave turn survives)."""
    P = stock_zt_zb()
    xs = np.arange(9.0, 234.0, 1.0)
    zt, zb = [], []
    for x in xs:
        xx = min(max(x, P[:, 0].min() + 0.3), P[:, 0].max() - 0.3)
        h = _vertical_hits(P, xx)
        zb.append(h[0])
        zt.append(h[1])
    zt, zb = np.array(zt), np.array(zb)
    zb[xs < 30.0] = np.minimum(zb[xs < 30.0], -106.6)
    zt[(xs < 14.0)] = np.maximum(zt[(xs < 14.0)], 0.4)
    zt[xs > 224.0] = 7.8
    zb[xs > 224.0] = -38.2
    zt_s = _gauss_smooth_1d(zt, 4.0)
    zt_n = _gauss_smooth_1d(zt, 1.0)
    nose = (xs > 148) & (xs < 172)
    zt_s[nose] = zt_n[nose]
    zb_s = _gauss_smooth_1d(zb, 4.0)
    zb_s[xs < 30.0] = zb[xs < 30.0]
    # the swivel seat: the trace's short horizontal flat (X 69.5-77.5, Z -90.85) survives with its short ramps
    zb_n = _gauss_smooth_1d(zb, 0.8)
    seat = (xs >= SW_FLAT_X[0] - 3.0) & (xs <= SW_FLAT_X[1] + 3.0)
    zb_s[seat] = zb_n[seat]
    zb_s[(xs >= SW_FLAT_X[0]) & (xs <= SW_FLAT_X[1])] = SW_FLAT_Z
    w = _gauss_smooth_1d(stock_halfw(xs), 6.0)
    return xs, zt_s, zb_s, w


def stock_stations(xs, zt, zb, w, tol=0.1, max_gap=12.0):
    """Greedy chordal-error stations along X: the next station is the farthest one whose straight run keeps the top
    line, the bottom line and the half width within tol mm of the sampled lines."""
    keep = [0]
    while keep[-1] < len(xs) - 1:
        i0 = keep[-1]
        best = i0 + 1
        for j in range(i0 + 1, len(xs)):
            if xs[j] - xs[i0] > max_gap:
                break
            t = (xs[i0:j + 1] - xs[i0]) / (xs[j] - xs[i0])
            err = max(float(np.abs(a[i0:j + 1] - (a[i0] + t * (a[j] - a[i0]))).max()) for a in (zt, zb, w))
            if err > tol:
                break
            best = j
        keep.append(best)
    return xs[keep]


def buttstock() -> PartDef:
    xs_all, zt_all, zb_all, w_all = stock_lines()
    # ring stations (form fix round 2): chosen by chordal error (top line, bottom line and half width each within
    # 0.1 mm of the straight run between stations, at most 12 mm apart) instead of fixed linspaces; 36 rings where
    # round 1 had 41, with the density where the lines bend (comb nose, swivel flat, butt)
    forced = np.array([SW_FLAT_X[0] - 3.0, SW_FLAT_X[0], SW_FLAT_X[1], SW_FLAT_X[1] + 3.0])      # swivel flat
    ch = stock_stations(xs_all, zt_all, zb_all, w_all, LOD.tol(0.1), LOD.step(12.0))   # LOD: coarser chords
    if LOD.LEVEL:      # the butt end keeps LOD0's stations: the plate's heel meets the stock's top line there (gap row)
        ch0 = stock_stations(xs_all, zt_all, zb_all, w_all, 0.1, 12.0)
        ch = np.unique(np.r_[ch, ch0[ch0 < 16.0]])
    ch = ch[(np.abs(ch[:, None] - forced[None, :]).min(1) > 1.0) & ~((ch > SW_FLAT_X[0]) & (ch < SW_FLAT_X[1]))]
    xs = np.unique(np.round(np.r_[ch, forced], 3))
    rings = []
    for x in xs:
        zt = float(np.interp(x, xs_all, zt_all))
        zb = float(np.interp(x, xs_all, zb_all))
        w = float(np.interp(x, xs_all, w_all))
        s = stock_section(x, zt, zb, w_override=w)
        nr = LOD.ring(STOCK_NR)
        s = resample_ring(s, nr, turn_weight=8.0)
        rings.append(np.c_[np.full(nr, x), s[:, 0], s[:, 1]])
    body = MS.loft(rings)
    trn = [(225.2, 7.0), (225.2, -17.5), (228.7, -22.0), (229.0, -28.5), (230.1, -34.0), (231.4, -36.77),
           (231.4, -45.0), (240.9, -45.0), (240.9, 12.0), (225.2, 12.0)]
    from parts.butt_plate import butt_plate_outline, _rear_face_x      # the plate's outline cuts the stock's end
    bpo = butt_plate_outline()
    # behind the plate's rear face: no stock (with the R 13 section the toe ring at X 9 otherwise leaves a 0.3 mm
    # sliver shell under the plate's raked toe)
    zz = np.linspace(bpo[:, 1].min() + 0.05, bpo[:, 1].max() - 0.05, 80)
    rear = [(_rear_face_x(bpo, z), z) for z in zz[::-1]]
    behind = np.array([(-10.0, zz[-1])] + rear + [(-10.0, zz[0])])
    cut = [MS.prism(np.array(trn), -40, 40),
           MS.prism(G.offset(G.ccw(bpo), GAP), -40, 40),
           MS.prism(G.ccw(behind), -40, 40)]
    cut.append(MS.prism(G.offset(G.ccw(np.array([(222.5, -4.0), (197.5, -14.0), (222.5, -24.0)], float)), GAP),
                        stock_halfw(210) - 0.6 - GAP, 40))                                        # inlet plate seat
    zt219 = float(np.interp(219.0, xs_all, zt_all))
    post = [MS.cylinder((219.0, 0.0, zt219 - 0.8), (219.0, 0.0, zt219 + 6.0), 3.0 + GAP, 24)]       # tang screw seat
    post += swivel_seat_cutters()
    p = PartDef("buttstock", [body], cutters=cut, post_cutters=post, cls="W-round", slot="M_AR01_Furniture",
                recipe=[(1.6, 2, 40.0)])
    if LOD.LEVEL >= 1:
        # LOD1+: no edge round on the stock (1.6 mm is 0.8 px at the 2.7 m switch); its one-segment version came
        # within 0.0075 mm of the butt plate's heel (row 0.01-0.05)
        p.recipe = []
    return p


def _vertical_hits(P, x):
    Q = np.vstack([P, P[:1]])
    zs = []
    for a, b in zip(Q[:-1], Q[1:]):
        if (a[0] - x) * (b[0] - x) <= 0 and a[0] != b[0]:
            t = (x - a[0]) / (b[0] - a[0])
            zs.append(a[1] + t * (b[1] - a[1]))
    if len(zs) < 2:
        return None
    return min(zs), max(zs)


# ---- rear sling swivel (form fix round 1): fitted to the trace (LEFT_outline parts.sling_swivel_rear).
# The trace shows a D-ring hanging below a short horizontal flat in the stock's bottom line (X 69.5-77.5 at
# Z -90.85, traced as part of the stock): straight top bar along the flat, round bottom, outer X 67.6-77.7,
# lowest Z -99.6 at X 72.6. Built in frame M (no tilt): a flush base plate in the flat, a lug under it with a
# transverse hole, and the D-ring (wire 2.5, spec) whose top bar passes through the hole (0.25 radial clearance).
SW_X = 72.65            # ring centre X (trace: lowest point 72.6, sides 67.6 / 77.7)
SW_FLAT_Z = -90.85      # the traced flat in the stock's bottom line
SW_FLAT_X = (69.5, 77.5)
SW_WIRE_R = 1.25
SW_HALF = 3.8           # centreline half width (outer +-5.05)
SW_BAR_Z = -92.35       # top bar centreline (outer top 0.15 below the base plate)
SW_BOTTOM_Z = -99.6     # outer bottom (trace)
SW_HOLE_R = 1.5


def swivel_seat_cutters():
    return [MS.box(69.8 - GAP, 75.8 + GAP, -4.0 - GAP, 4.0 + GAP, SW_FLAT_Z - 1.0, SW_FLAT_Z + 1.9 + GAP)]


def sling_swivel() -> PartDef:
    base = MS.box(69.8, 75.8, -4.0, 4.0, SW_FLAT_Z - 0.1, SW_FLAT_Z + 1.9)     # 0.1 proud of the flat, 1.9 inset
    lug = MS.box(SW_X - 0.65, SW_X + 0.65, -2.2, 2.2, -94.5, SW_FLAT_Z - 0.08)
    hole = xcyl(0.0, SW_BAR_Z, SW_HOLE_R, SW_X - 3.0, SW_X + 3.0, 24)
    return PartDef("sling_swivel_base", [base], unions=[lug], cutters=[hole], cls="S-cut", recipe=[(0.3, 1, 30.0)],
                   spec_id="sling_swivel_rear")


def sling_loop_path(step=0.7):
    rt = 1.0
    xl, xr = SW_X - SW_HALF, SW_X + SW_HALF
    zc = SW_BOTTOM_Z + SW_WIRE_R + SW_HALF                   # bottom semicircle centre
    pts = [np.c_[np.linspace(xl + rt, xr - rt, 8), np.full(8, SW_BAR_Z)][:-1]]
    pts.append(G.arc(xr - rt, SW_BAR_Z - rt, rt, 90, 0, 5)[:-1])
    pts.append(np.c_[np.full(3, xr), np.linspace(SW_BAR_Z - rt, zc, 3)][:-1])
    pts.append(G.arc(SW_X, zc, SW_HALF, 0, -180, 25)[:-1])
    pts.append(np.c_[np.full(3, xl), np.linspace(zc, SW_BAR_Z - rt, 3)][:-1])
    pts.append(G.arc(xl + rt, SW_BAR_Z - rt, rt, 180, 90, 5)[:-1])
    P = G.resample(np.vstack(pts), step)
    return np.c_[P[:, 0], np.zeros(len(P)), P[:, 1]]


def sling_loop() -> PartDef:
    path = sling_loop_path()
    circ = G.arc(0, 0, SW_WIRE_R, 0, 360, 9)[:-1]      # 8-gon wire (integration-round budget; was 12)
    m = MS.sweep_profile(path, circ, ups=[[0, 1, 0]] * len(path), closed_path=True)
    return PartDef("sling_swivel_loop", [m], cls="none", recipe=[], wn=False, smooth_deg=60.0,
                   spec_id="sling_swivel_rear", joint={"type": "hinge", "parent": "sling_swivel_base",
                                                       "clearance_mm": [0.1, 0.3], "note": "static, no bone"})


def stock_hardware() -> PartDef:
    """Tang screw on top of the wrist (X 219) and the left wrist inlet plate (V outline, 2 screws)."""
    P = stock_zt_zb()
    xs_all, zt_all, zb_all, w_all = stock_lines()
    zt = float(np.interp(219.0, xs_all, zt_all))
    head = MS.cylinder((219.0, 0.0, zt - 0.78), (219.0, 0.0, zt + 0.1), 3.0, 24)
    sol = [head, MS.dome((219.0, 0.0, zt + 0.08), (0, 0, 1), 3.0, 0.7, 24, 3)]
    # left inlet plate: pointed rearward V, 25 x 20, flush 0.2 proud on the left wrist
    v = np.array([(222.5, -4.0), (197.5, -14.0), (222.5, -24.0)], float)
    v = G.fillet(G.ccw(v), 2.0, 3)
    sol.append(MS.prism(v, stock_halfw(210) - 0.6, stock_halfw(210) + 0.2))
    for (x, z) in ((217.0, -9.0), (217.0, -19.0)):
        sol.append(MS.dome((x, stock_halfw(210) + 0.2 + GAP, z), (0, 1, 0), 1.8, 0.6, 16, 3))
    return PartDef("stock_hardware", sol, cls="none", recipe=[], wn=False, smooth_deg=50.0, spec_id="buttstock")
