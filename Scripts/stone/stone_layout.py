"""Stone layouts in unrolled face coordinates (STONE_BUILDING_STUDY.md 4.5): pure Python, no bpy, track-neutral.

A layout works in (a, z): a along the wall, z up (z = -s, s = depth below the top line). It returns convex outlines
(before any joint inset) plus the per-stone shape data a stone builder needs; the kit turns each outline into a 3D
stone (inset by its half joint, corners rounded per corner, crown, tilt) and moves it rigidly onto its batter.

coursed_rounded(...)   rough-coursed rounded field stone (nozura / uchikomi RANZUMI read as rough courses), the
                       measured mix of the dojo terrace trace (References/Dojo/trace_terrace_lower.json):
                       * stone aspect drawn from a measured h/w mixture (MIX_TERRACE: upright share ~0.70),
                       * course boundaries wandering between pins (module ends stay on the global course table),
                       * joints between neighbours LEAN (top and bottom offsets of opposite sign, alternating runs:
                         the reference's leaning upright ovals),
                       * broken courses: a slot splits into two stacked smaller stones now and then,
                       * uprights through two courses,
                       * per-corner cuts (0.5-1.5 x the stone's mean, one corner sometimes nearly sharp) that the
                         stone builder rounds (Chaikin) into egg / lens outlines.
coursed_fitted(...)    f3: the same coursed frame with FITTED outlines: every T-junction turned into a Y-junction
                       (neighbours share edges; tooth ends interlock with fixed numbers); pure-Python convex_hull,
                       inset_convex and chaikin for simulating a layout outside Blender (sim_layout_f3.py)
layout_json(...)       the stone_layout/1 record Scripts/stone/stone_measure.py reads (SG3 / SG4 / SG7 / SG9 flat).
"""
from __future__ import annotations

import math
import random

# h/w mixture measured on the terrace trace (body zone, 33 stones, 2026-09-30): aspect median 1.18, p10 0.78, p90 1.84,
# upright (h > w) 0.70, tall (h > 1.2 w) 0.49. Rows: (share, hw_lo, hw_hi).
# The drawn target sits above the measured numbers because leaning joints, per-corner cuts and the joint inset lower the
# built stones' bounding-box h/w (tuned by simulation: 3 seeds of a 4 m x 3 m face give upright 0.68, tall 0.48,
# median 1.17, p10 0.72, p90 1.75, area CV 0.57-0.61).
MIX_TERRACE = ((0.52, 1.30, 2.10), (0.24, 1.05, 1.30), (0.16, 0.80, 1.05), (0.08, 0.55, 0.80))


def smooth01(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


class Boundary:
    """A course boundary s(a): the course depth s0 wandering +-amp between control points `spacing` apart, pinned
    back to s0 near the pins (module ends interlock on the global course table)."""

    def __init__(self, s0, a_lo, a_hi, pins, rng, amp, spacing=(0.34, 0.60)):
        self.s0, self.pins = s0, pins
        self.cp = []
        a = a_lo - 0.6
        while a < a_hi + 0.6:
            self.cp.append((a, rng.uniform(-amp, amp)))
            a += rng.uniform(*spacing)
        self.cp.append((a, rng.uniform(-amp, amp)))

    def __call__(self, a):
        cp = self.cp
        w = 0.0
        for i in range(len(cp) - 1):
            if cp[i][0] <= a <= cp[i + 1][0]:
                f = (a - cp[i][0]) / (cp[i + 1][0] - cp[i][0])
                w = cp[i][1] + (cp[i + 1][1] - cp[i][1]) * f
                break
        tp = min([smooth01((abs(a - p) - 0.12) / 0.40) for p in self.pins] + [1.0])
        return self.s0 + w * tp


def draw_widths(total, ch, rng, mix=MIX_TERRACE, first=None, last=None, w_min=0.15):
    """Widths summing to `total` for a course of height ch, each drawn from the h/w mixture (w = ch / hw); optional
    forced first / last widths (corner stones). Returns [(w, target_hw)]."""
    if total <= 0.0:
        return []
    ws_f = [(rng.uniform(*first), None)] if first else []
    ws_l = [(rng.uniform(*last), None)] if last else []
    fixed = sum(w for w, _ in ws_f + ws_l)
    if fixed > total - 0.20:
        return [(total, None)]
    rest = total - fixed
    raw = []
    cum = [0.0]
    for sh, _, _ in mix:
        cum.append(cum[-1] + sh)
    while sum(w for w, _ in raw) < rest - 0.5 * ch / 1.2:
        r = rng.random() * cum[-1]
        k = next(i for i in range(len(mix)) if r <= cum[i + 1])
        hw = rng.uniform(mix[k][1], mix[k][2])
        raw.append((max(w_min, ch / hw), hw))
    if not raw:
        raw = [(rest, None)]
    kk = rest / sum(w for w, _ in raw)
    return ws_f + [(w * kk, hw) for w, hw in raw] + ws_l


def corner_cuts(n, short, rng, mean=(0.13, 0.22), spread=(0.5, 1.5), sharp_p=0.25):
    """Per-corner cut lengths (study 4.4 item 1): a stone mean from `mean` x its short side, each corner 0.5-1.5 x
    that, one corner nearly sharp now and then."""
    m = rng.uniform(*mean) * short
    cuts = [m * rng.uniform(*spread) for _ in range(n)]
    if rng.random() < sharp_p:
        cuts[rng.randrange(n)] = m * 0.35
    return cuts


def cut_corners(poly, cuts):
    """Cut every corner i of a convex polygon by cuts[i] along both edges (at most 45 % of either edge)."""
    out = []
    n = len(poly)
    for i in range(n):
        p = poly[i]
        pa, pb = poly[i - 1], poly[(i + 1) % n]
        ea = (pa[0] - p[0], pa[1] - p[1])
        eb = (pb[0] - p[0], pb[1] - p[1])
        la, lb = math.hypot(*ea), math.hypot(*eb)
        c = cuts[i]
        ca, cb = min(c, 0.45 * la), min(c, 0.45 * lb)
        if ca < 1e-4 or cb < 1e-4:
            out.append(tuple(p))
            continue
        out.append((p[0] + ea[0] / la * ca, p[1] + ea[1] / la * ca))
        out.append((p[0] + eb[0] / lb * cb, p[1] + eb[1] / lb * cb))
    return out


def coursed_rounded(courses, s_top, s_bot, lohi, pins, seed, mix=MIX_TERRACE, amp=0.065, lean=(0.012, 0.050),
                    lean_alt=0.72, split_p=0.015, tall_p=0.10, force_first=None, force_last=None, cut_mean=(0.13, 0.22)):
    """Rough-coursed rounded stones between depths s_top .. s_bot on a course table `courses` (depths). lohi(k, sa,
    sb) -> ((lo_top, lo_bot), (hi_top, hi_bot)): course k's end lines. pins: a values where boundaries stay on the
    table. Returns stones [{"quad": [(a, z) x4], "poly": corner-cut outline, "cuts": [...], "course": k,
    "kind": "field"|"tall"|"split"|"forced", "target_hw": ...}]."""
    rng = random.Random(seed)
    ks = [k for k in range(len(courses) - 1) if courses[k] < s_bot - 0.02 and courses[k + 1] > s_top + 0.02]
    if not ks:
        return []

    def sab(k):
        return max(courses[k], s_top), min(courses[k + 1], s_bot)
    bounds = {}
    for k in ks + [ks[-1] + 1]:
        s0 = courses[k] if k < len(courses) else s_bot
        if s0 <= s_top + 1e-6 or s0 >= s_bot - 1e-6:
            s0 = min(max(s0, s_top), s_bot)
            bounds[k] = (lambda a, s0=s0: s0)
        else:
            bounds[k] = Boundary(s0, -12.0, 12.0, pins, rng, amp)
    talls = {}
    for k in ks[:-1]:
        if k % 2 or k + 1 not in ks or courses[k + 2] > s_bot + 0.05:
            continue
        (lo1, _), (hi1, _) = lohi(k, *sab(k))
        (lo2, _), (hi2, _) = lohi(k + 1, *sab(k + 1))
        lo, hi = max(lo1, lo2) + 0.40, min(hi1, hi2) - 0.40
        a = lo + rng.uniform(0.0, 0.9)
        lst = []
        ch2 = courses[k + 2] - courses[k]
        while a + 0.30 < hi:
            if any(abs(a - p) < 0.5 for p in pins):
                a += 0.35
                continue
            if rng.random() < tall_p:
                w = ch2 * rng.uniform(0.40, 0.58)
                if a + w > hi:
                    break
                jl = rng.uniform(-0.03, 0.03)
                jr = rng.uniform(-0.03, 0.03)
                lst.append(((a + jl, a - jl), (a + w + jr, a + w - jr)))
                a += w + rng.uniform(1.0, 2.2)
            else:
                a += rng.uniform(0.5, 1.1)
        if lst:
            talls[k] = lst
    out = []

    def add(quad, k, kind, hw):
        a_ = [p[0] for p in quad]
        z_ = [p[1] for p in quad]
        short = max(0.05, min(max(a_) - min(a_), max(z_) - min(z_)))
        cuts = corner_cuts(len(quad), short, rng, mean=cut_mean)
        out.append({"quad": [tuple(p) for p in quad], "poly": cut_corners(quad, cuts), "cuts": cuts, "course": k,
                    "kind": kind, "target_hw": hw})

    sign = 1.0
    for k in ks:
        sa, sb = sab(k)
        s_up, s_dn = bounds[k], bounds[k + 1]
        (lo_t, lo_b), (hi_t, hi_b) = lohi(k, sa, sb)
        if hi_t - lo_t < 0.08 and hi_b - lo_b < 0.08:
            continue
        blocks = sorted(list(talls.get(k, [])) + list(talls.get(k - 1, [])), key=lambda b: b[0][0])
        segs, left, lkind = [], (lo_t, lo_b), "end"
        for (bl, br) in blocks:
            segs.append((left, bl, lkind, "tall"))
            left, lkind = br, "tall"
        segs.append((left, (hi_t, hi_b), lkind, "end"))
        ch = max(0.12, sb - sa)
        for si, (L, R_, lk, rk) in enumerate(segs):
            if min(R_[0] - L[0], R_[1] - L[1]) < 0.06:
                continue
            first = force_first.get(k % 2) if (force_first and si == 0 and lk == "end") else None
            last = force_last.get(k % 2) if (force_last and si == len(segs) - 1 and rk == "end") else None
            total = (R_[0] + R_[1]) / 2 - (L[0] + L[1]) / 2
            ws = draw_widths(total, ch, rng, mix, first, last)
            lines = [(L[0], L[1])]
            a = 0.0
            for w, _ in ws[:-1]:
                a += w
                f = a / total
                if rng.random() > lean_alt:          # leaning runs: the sign holds for a few joints
                    sign = -sign
                j = sign * rng.uniform(*lean)
                lines.append((L[0] + (R_[0] - L[0]) * f + j, L[1] + (R_[1] - L[1]) * f - j))
            lines.append((R_[0], R_[1]))
            for idx, ((lt, lb), (rt, rb)) in enumerate(zip(lines, lines[1:])):
                if min(rt - lt, rb - lb) < 0.07:
                    continue
                hw = ws[idx][1]
                kind = "forced" if hw is None else "field"
                w_mean = ((rt - lt) + (rb - lb)) / 2
                if kind == "field" and w_mean > 0.85 * ch and rng.random() < split_p * 2.5:
                    # broken course: the slot splits into two stacked stones for this one slot
                    fm = rng.uniform(0.40, 0.60)
                    mid = lambda a_, fm=fm: -(s_up(a_) + (s_dn(a_) - s_up(a_)) * fm)   # noqa: E731
                    add([(lb, -s_dn(lb)), (rb, -s_dn(rb)), (rb, mid(rb)), (lb, mid(lb))], k, "split", hw)
                    add([(lt, mid(lt)), (rt, mid(rt)), (rt, -s_up(rt)), (lt, -s_up(lt))], k, "split", hw)
                    continue
                add([(lb, -s_dn(lb)), (rb, -s_dn(rb)), (rt, -s_up(rt)), (lt, -s_up(lt))], k, kind, hw)
    for k, lst in talls.items():
        for (bl, br) in lst:
            s_up, s_dn = bounds[k], bounds[k + 2]
            add([(bl[1], -s_dn(bl[1])), (br[1], -s_dn(br[1])), (br[0], -s_up(br[0])), (bl[0], -s_up(bl[0]))], k,
                "tall", None)
    return out


def layout_json(piece, zones):
    """zones: {name: {"stones": [{"poly": [(a, z)], "crown": m, "corner_r": [m]}], "z_top": m, "z_bot": m}}."""
    return {"schema": "stone_layout/1", "piece": piece,
            "zones": {z: {"z_top": d.get("z_top"), "z_bot": d.get("z_bot"),
                          "stones": [{"poly": [[round(float(x), 4), round(float(y), 4)] for x, y in s["poly"]],
                                      "crown": s.get("crown"), "corner_r": s.get("corner_r"), "kind": s.get("kind")}
                                     for s in d["stones"]]} for z, d in zones.items()}}


# ------------------------------------------------------------------------------------------------ f3: fitted coursing
# STONE_BUILDING_STUDY 4.5 / 3.2 (Ano-shu: "its outline follows its neighbours") and the judge-steer-checked delta of
# stone kit f3: the reference's stones FIT each other (thin joints, Y-junctions), where f2's coursed quads met at
# T-junctions and every rounded corner opened a dark triangle (pitfall P52). coursed_fitted keeps the coursed frame
# (global course table, wandering boundaries, leaning joints in runs, uprights through two courses, module-end teeth on
# the pins) and then turns every T-junction into a Y: the stone that runs through gets a point pushed a little way up
# the head joint, and the two stones whose corners meet there are chamfered to match, so all three outlines share
# edges. Joints stay one inset wide everywhere; the kit's corner rounding then only softens obtuse corners.
# Module ends: junctions at a TOOTH end (an end line near a pin) use FIXED push / chamfer numbers, and a corner at a
# tooth end whose through-stone lies in the NEXT module is chamfered by the same fixed numbers, so two modules
# interlock with matching outlines. Hard ends (corner blocks, openings) are left square.

def _unit(dx, dy):
    L = math.hypot(dx, dy)
    return (dx / L, dy / L) if L > 1e-12 else (0.0, 0.0)


def poly_area(p):
    return 0.5 * sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))


def convex_hull(pts):
    P = sorted(set((round(float(a), 7), round(float(b), 7)) for a, b in pts))
    if len(P) < 3:
        return P

    def cr(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in P:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(P):
        while len(hi) >= 2 and cr(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    return lo[:-1] + hi[:-1]


def inset_convex(poly, d):
    """Pure-Python inward offset of a convex polygon by d (kit1_geo.inset_convex without mathutils). None on collapse."""
    if poly_area(poly) < 0:
        poly = list(reversed(poly))
    pts = []
    for p in poly:
        if not pts or math.hypot(p[0] - pts[-1][0], p[1] - pts[-1][1]) > 1e-5:
            pts.append(p)
    if len(pts) > 2 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 1e-5:
        pts.pop()
    n = len(pts)
    lines = []
    for i in range(n):
        p, q = pts[i], pts[(i + 1) % n]
        e = _unit(q[0] - p[0], q[1] - p[1])
        if e == (0.0, 0.0):
            continue
        lines.append(((p[0] - e[1] * d, p[1] + e[0] * d), e))
    out = []
    for i in range(len(lines)):
        (p1, e1), (p2, e2) = lines[i - 1], lines[i]
        den = e1[0] * e2[1] - e1[1] * e2[0]
        if abs(den) < 1e-9:
            continue
        t = ((p2[0] - p1[0]) * e2[1] - (p2[1] - p1[1]) * e2[0]) / den
        out.append((p1[0] + e1[0] * t, p1[1] + e1[1] * t))
    if len(out) < 3 or poly_area(out) <= 1e-5:
        return None
    for (x, y) in out:
        for i in range(n):
            p, q = pts[i], pts[(i + 1) % n]
            if (q[0] - p[0]) * (y - p[1]) - (q[1] - p[1]) * (x - p[0]) < -1e-7:
                return None
    return out


def chaikin(poly, iters=2, keep=0.2):
    pts = [tuple(p) for p in poly]
    for _ in range(iters):
        out = []
        n = len(pts)
        for i in range(n):
            (ax, ay), (bx, by) = pts[i], pts[(i + 1) % n]
            out.append((ax + (bx - ax) * keep, ay + (by - ay) * keep))
            out.append((ax + (bx - ax) * (1 - keep), ay + (by - ay) * (1 - keep)))
        pts = out
    return pts


def _merge_narrow(lines, min_w):
    """Drop interior joint lines that would leave a stone narrower than min_w (top or bottom): the slot merges into
    its neighbour instead of being skipped (f2 skipped it and left a hole: a dark void in the wall)."""
    if len(lines) <= 2:
        return lines
    keep = [lines[0]]
    for ln in lines[1:-1]:
        if min(ln[0] - keep[-1][0], ln[1] - keep[-1][1]) >= min_w:
            keep.append(ln)
    last = lines[-1]
    while len(keep) > 1 and min(last[0] - keep[-1][0], last[1] - keep[-1][1]) < min_w:
        keep.pop()
    return keep + [last]


class _Stone:
    __slots__ = ("poly", "course", "kind", "hw", "ends", "quad")


class _FlatBoundary:
    """A Boundary whose wander is exactly zero within `flat` of a pin (a tooth junction sits on the course table in
    both modules), fading in over the next 0.4 m."""

    def __init__(self, b, flat):
        self.b, self.flat = b, flat

    def __call__(self, a):
        cp = self.b.cp
        w = 0.0
        for i in range(len(cp) - 1):
            if cp[i][0] <= a <= cp[i + 1][0]:
                f = (a - cp[i][0]) / (cp[i + 1][0] - cp[i][0])
                w = cp[i][1] + (cp[i + 1][1] - cp[i][1]) * f
                break
        tp = min([smooth01((abs(a - p) - self.flat) / 0.40) for p in self.b.pins] + [1.0])
        return self.b.s0 + w * tp


# The drawn h/w mixture for fitted layouts (tuned by sim_layout_f3.py so the BUILT outlines land on the trace: the
# fitted chamfers shrink a stone's bounding box less than coursed_rounded's corner cuts did).
MIX_FITTED = ((0.38, 1.25, 1.95), (0.26, 1.0, 1.25), (0.24, 0.75, 1.0), (0.12, 0.52, 0.75))


def coursed_fitted(courses, s_top, s_bot, lohi, pins, seed, mix=MIX_FITTED, amp=0.12, lean=(0.012, 0.055),
                   lean_alt=0.72, split_p=0.015, tall_p=0.30, force_first=None, force_last=None,
                   push=(0.24, 0.40), chamfer=(0.9, 1.4), end_push=0.070, end_cham=0.085, tooth_d=0.18,
                   min_w=0.14, flat=0.30, spacing=(0.24, 0.48)):
    """Coursed rounded field stone with FITTED outlines (Y-junctions): the coursed frame of coursed_rounded, then every
    T-junction becomes a Y (see the block comment above). Same inputs as coursed_rounded; returns stones
    [{"quad", "poly" (fitted, before any joint inset), "cuts": None, "course", "kind", "target_hw"}]; the first
    stone also carries "junctions" (the count of Y-junctions made)."""
    rng = random.Random(seed)
    ks = [k for k in range(len(courses) - 1) if courses[k] < s_bot - 0.02 and courses[k + 1] > s_top + 0.02]
    if not ks:
        return []

    def sab(k):
        return max(courses[k], s_top), min(courses[k + 1], s_bot)
    bounds = {}
    for k in ks + [ks[-1] + 1]:
        s0 = courses[k] if k < len(courses) else s_bot
        if s0 <= s_top + 1e-6 or s0 >= s_bot - 1e-6:
            s0 = min(max(s0, s_top), s_bot)
            bounds[k] = (lambda a, s0=s0: s0)
        else:
            bounds[k] = _FlatBoundary(Boundary(s0, -12.0, 12.0, pins, rng, amp, spacing=spacing), flat)
    talls = {}
    for k in ks[:-1]:
        if k % 2 or k + 1 not in ks or courses[k + 2] > s_bot + 0.05:
            continue
        (lo1, _), (hi1, _) = lohi(k, *sab(k))
        (lo2, _), (hi2, _) = lohi(k + 1, *sab(k + 1))
        lo, hi = max(lo1, lo2) + 0.40, min(hi1, hi2) - 0.40
        a = lo + rng.uniform(0.0, 0.7)
        lst = []
        ch2 = courses[k + 2] - courses[k]
        while a + 0.30 < hi:
            if any(abs(a - p) < 0.5 for p in pins):
                a += 0.35
                continue
            if rng.random() < tall_p:
                w = ch2 * rng.uniform(0.40, 0.62)
                if a + w > hi:
                    break
                jl = rng.uniform(-0.035, 0.035)
                jr = rng.uniform(-0.035, 0.035)
                lst.append(((a + jl, a - jl), (a + w + jr, a + w - jr)))
                a += w + rng.uniform(0.8, 1.9)
            else:
                a += rng.uniform(0.45, 1.0)
        if lst:
            talls[k] = lst

    def near_pin(a):          # a tooth end: TOOTH off a pin (or on it: a free end)
        return any(abs(abs(a - p) - tooth_d) < 0.04 or abs(a - p) < 0.02 for p in pins)

    stones = []

    def add(quad, k, kind, hw, ends):
        st = _Stone()
        st.quad = [tuple(p) for p in quad]
        st.poly = [tuple(p) for p in quad]
        st.course, st.kind, st.hw, st.ends = k, kind, hw, ends
        stones.append(st)

    sign = 1.0
    for k in ks:
        sa, sb = sab(k)
        s_up, s_dn = bounds[k], bounds[k + 1]
        (lo_t, lo_b), (hi_t, hi_b) = lohi(k, sa, sb)
        if hi_t - lo_t < 0.08 and hi_b - lo_b < 0.08:
            continue
        lo_kind = "tooth" if near_pin((lo_t + lo_b) / 2) else "hard"
        hi_kind = "tooth" if near_pin((hi_t + hi_b) / 2) else "hard"
        blocks = sorted(list(talls.get(k, [])) + list(talls.get(k - 1, [])), key=lambda b: b[0][0])
        segs, left, lkind = [], (lo_t, lo_b), lo_kind
        for (bl, br) in blocks:
            segs.append((left, bl, lkind, None))
            left, lkind = br, None
        segs.append((left, (hi_t, hi_b), lkind, hi_kind))
        ch = max(0.12, sb - sa)
        for si, (L, R_, lk, rk) in enumerate(segs):
            if min(R_[0] - L[0], R_[1] - L[1]) < 0.06:
                continue
            first = force_first.get(k % 2) if (force_first and si == 0 and lk is not None) else None
            last = force_last.get(k % 2) if (force_last and si == len(segs) - 1 and rk is not None) else None
            total = (R_[0] + R_[1]) / 2 - (L[0] + L[1]) / 2
            ws = draw_widths(total, ch, rng, mix, first, last)
            lines = [(L[0], L[1])]
            a = 0.0
            for w, _ in ws[:-1]:
                a += w
                f = a / total
                if rng.random() > lean_alt:
                    sign = -sign
                j = sign * rng.uniform(*lean)
                lines.append((L[0] + (R_[0] - L[0]) * f + j, L[1] + (R_[1] - L[1]) * f - j))
            lines.append((R_[0], R_[1]))
            if not (first or last):
                lines = _merge_narrow(lines, min_w)
            nst = len(lines) - 1
            for idx, ((lt, lb), (rt, rb)) in enumerate(zip(lines, lines[1:])):
                if min(rt - lt, rb - lb) < 0.05:
                    continue
                hw = ws[idx][1] if idx < len(ws) else None
                kind = "forced" if hw is None else "field"
                ends = (lk if idx == 0 else None, rk if idx == nst - 1 else None)
                w_mean = ((rt - lt) + (rb - lb)) / 2
                if kind == "field" and w_mean > 0.85 * ch and rng.random() < split_p * 2.5:
                    fm = rng.uniform(0.40, 0.60)
                    mid = lambda a_, fm=fm: -(s_up(a_) + (s_dn(a_) - s_up(a_)) * fm)   # noqa: E731
                    add([(lb, -s_dn(lb)), (rb, -s_dn(rb)), (rb, mid(rb)), (lb, mid(lb))], k, "split", hw, ends)
                    add([(lt, mid(lt)), (rt, mid(rt)), (rt, -s_up(rt)), (lt, -s_up(lt))], k, "split", hw, ends)
                    continue
                add([(lb, -s_dn(lb)), (rb, -s_dn(rb)), (rt, -s_up(rt)), (lt, -s_up(lt))], k, kind, hw, ends)
    for k, lst in talls.items():
        for (bl, br) in lst:
            s_up, s_dn = bounds[k], bounds[k + 2]
            add([(bl[1], -s_dn(bl[1])), (br[1], -s_dn(br[1])), (br[0], -s_up(br[0])), (bl[0], -s_up(bl[0]))], k,
                "tall", None, (None, None))
    n_j = _fit_junctions(stones, -s_top, -s_bot, rng, push, chamfer, end_push, end_cham)
    out = [{"quad": st.quad, "poly": st.poly, "cuts": None, "course": st.course, "kind": st.kind,
            "target_hw": st.hw} for st in stones]
    if out:
        out[0]["junctions"] = n_j
    return out


def _fit_junctions(stones, z_top, z_bot, rng, push, chamfer, end_push, end_cham, tol=0.016):
    """Turn T-junctions into Y-junctions in place (stones: _Stone, .poly CCW, starting as the quads). Returns the
    number of junctions changed."""
    def is_zone_edge(p):
        return abs(p[1] - z_top) < 1e-4 or abs(p[1] - z_bot) < 1e-4

    def same(p, q):
        return abs(p[0] - q[0]) < 1e-7 and abs(p[1] - q[1]) < 1e-7

    def corner_side(st, p):
        for i, c in enumerate(st.quad):
            if same(c, p):
                return 0 if i in (0, 3) else 1
        return None

    groups = {}
    for si, st in enumerate(stones):
        for c in st.quad:
            if is_zone_edge(c):
                continue
            groups.setdefault((round(c[0], 6), round(c[1], 6)), []).append((si, c))
    n_j = 0
    for _key, members in groups.items():
        J = members[0][1]
        kinds = []
        for si, c in members:
            sd = corner_side(stones[si], c)
            kinds.append(stones[si].ends[sd] if sd is not None else None)
        if "hard" in kinds:
            continue
        tooth = "tooth" in kinds
        mids = {si for si, _ in members}
        across = None
        for sj, st in enumerate(stones):
            if sj in mids:
                continue
            P = st.poly
            for m in range(len(P)):
                A, B = P[m], P[(m + 1) % len(P)]
                ab = (B[0] - A[0], B[1] - A[1])
                L = math.hypot(*ab)
                if L < 0.06:
                    continue
                t = ((J[0] - A[0]) * ab[0] + (J[1] - A[1]) * ab[1]) / (L * L)
                if t * L < 0.035 or (1 - t) * L < 0.035:
                    continue
                if abs((J[0] - A[0]) * ab[1] - (J[1] - A[1]) * ab[0]) / L < tol:
                    across = (sj, m, t, L)
                    break
            if across:
                break
        if across is None and not tooth:
            continue
        if across is not None:
            PA = stones[across[0]].poly
            A, B = PA[across[1]], PA[(across[1] + 1) % len(PA)]
            e_ab = _unit(B[0] - A[0], B[1] - A[1])
        hd = [0.0, 0.0]
        beds, hlens, blens = [], [], []
        for si, c in members:
            P = stones[si].poly
            k = next((i for i, q in enumerate(P) if same(q, c)), None)
            if k is None:
                continue
            prv, nxt = P[k - 1], P[(k + 1) % len(P)]
            up_ = _unit(prv[0] - c[0], prv[1] - c[1])
            un_ = _unit(nxt[0] - c[0], nxt[1] - c[1])
            if across is not None:      # the bed neighbour runs along the through-stone's edge
                head_is_prev = abs(up_[0] * e_ab[0] + up_[1] * e_ab[1]) < abs(un_[0] * e_ab[0] + un_[1] * e_ab[1])
            else:                       # a tooth corner: the head runs along the (near-vertical) end line
                head_is_prev = abs(up_[1]) > abs(un_[1])
            h, b = (up_, un_) if head_is_prev else (un_, up_)
            hn, bn = (prv, nxt) if head_is_prev else (nxt, prv)
            hd[0] += h[0]
            hd[1] += h[1]
            beds.append((si, k, head_is_prev, b))
            hlens.append(math.hypot(hn[0] - c[0], hn[1] - c[1]))
            blens.append(math.hypot(bn[0] - c[0], bn[1] - c[1]))
        if not beds:
            continue
        hdir = _unit(*hd)
        if tooth:
            e_, c_ = end_push, end_cham
        else:
            e_ = rng.uniform(*push) * min(hlens)
            c_ = e_ * rng.uniform(*chamfer)
        e_ = min(e_, 0.36 * min(hlens))
        c_ = min(c_, 0.42 * min(blens))
        if across is not None:
            _, m, t, L = across
            c_ = min(c_, t * L - 0.02, (1 - t) * L - 0.02)
        if e_ < 0.012 or c_ < 0.012:
            continue
        Jp = (J[0] + hdir[0] * e_, J[1] + hdir[1] * e_)
        pb_pts = []
        for (si, k, head_is_prev, b) in beds:
            P = stones[si].poly
            Pb = (J[0] + b[0] * c_, J[1] + b[1] * c_)
            pb_pts.append(Pb)
            stones[si].poly = P[:k] + ([Jp, Pb] if head_is_prev else [Pb, Jp]) + P[k + 1:]
        if across is not None:
            sj, m, t, L = across
            P = stones[sj].poly
            A = P[m]
            pts = list(pb_pts)
            if len(pts) == 1:          # the other corner lies in the next module: mirror its bed point
                d0 = (pts[0][0] - J[0]) * e_ab[0] + (pts[0][1] - J[1]) * e_ab[1]
                pts.append((J[0] - e_ab[0] * d0, J[1] - e_ab[1] * d0))
            pts.sort(key=lambda q: (q[0] - A[0]) * e_ab[0] + (q[1] - A[1]) * e_ab[1])
            stones[sj].poly = P[:m + 1] + [pts[0], Jp, pts[-1]] + P[m + 1:]
        n_j += 1
    return n_j
