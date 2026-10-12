"""The lower receiver moulding (trigger housing + magwell + guard + grip + end block, one moulding: spec
lower_receiver, magwell, trigger_guard, pistol_grip, end_block; RP12, RP13, RP20, RP21; R31) and the grip cover.

Zones united, then cut to the traced side silhouette and the seam:
  end block        full height behind the upper (its top lowered under the rail's rear end, R32), spec Y box
  trigger housing  full receiver width down to the housing's bottom line (the guard top), the tang curve behind the grip
  magwell          the narrower well (R31) behind the front face, its rear wall parallel to the magazine (C1), the
                   insertion flare band along the lip line (2.0 per side, 45 deg chamfered top)
  guard            the traced loop at the bar width, its opening cut (incl. the trigger's area)
  clevis ears      two ears straddling the paddle's top, carrying its pin
  grip             a loft of rounded sections perpendicular to the grip axis (front strap / back strap radii), the
                   traced front and back edges at every station; the cover below a 0.3 seam is its own part
Then: the magwell cavity (+0.3 per side, the mouth flare, up into the upper's cavity), the catch window, the paddle's
slot and the nose's slot, the trigger slot (the blade's 0..+13 deg sweep + 0.3), the selector shaft bore with its seat
bosses, the trigger axle bore, the lower-rail pocket, the oblong recess (left), the seam boss (left, through the upper's
clearance), the stipple panel border (0.55 step), the receiver-side hinge knuckles and the latch lug (end block),
flush pin holes. Edges: R 1.4 outer rounds, a 0.4 break on the seam edges, 0.35 on the cut lips.
"""
from __future__ import annotations

import math

import numpy as np

from gunlib import geo2d as G
from gunlib.mesh import Mesh, box, cylinder, loft, prism
from gunlib.parts import mag_box as MB
from gunlib.parts import hardware as HW
from gunlib.parts import hinge as HG

import smg_geom as SG
from smg_common import dims, box as sbox, feature, D as SPECD, BORE_Z, trace
from smg_parts import Ops
from . import FURN, METAL, GAP, pcyl, loft_capped
from .receiver import (SEAM, H, X_EBF, X_EBR, X_RAIL0, Z_TOP, Z_BODY_BOT, EB_Y, MW, TG, PG, EB, MR, SE, TRG, MAGD,
                       mag_M, mag_M4, MAG_Z, MAG_X, MAG_O, wall_line_x, mag_rear_x, region_lower, master_prism,
                       pin_holes, face_y, LEDGE, Z_LEDGE, stadium_xz, SH, LO_INSET, face_y_lower, pin_face_y,
                       selector_pad_xz)

GRIP_W = float(PG["width_Y"])                          # 32 (real norm, unseen)
RF, RB = 0.5 * sum(PG["front_strap_R"]), 0.5 * sum(PG["back_strap_R"])
RAKE = math.radians(float(PG["axis_rake_deg_from_vertical"]))
U_DN = np.array([-math.sin(RAKE), -math.cos(RAKE)])     # down the grip axis (XZ)
V_FW = np.array([math.cos(RAKE), -math.sin(RAKE)])      # forward, perpendicular to the axis
GRIP_O = np.array([SPECD["frames"]["B"]["Grip_in_M"][0], SPECD["frames"]["B"]["Grip_in_M"][2]])
MW_BODY = float(MW["outer_width_body"]) / 2.0
MW_LIP = float(MW["outer_width_lip"]) / 2.0
PAD_TOP_L = float(face_y(1.0, *SE["pivot_XZ"])) + float(SE["seat_boss_proud"])      # the LEFT pad's top (Y_L + 1.0)
PAD_TOP_R = float(face_y(-1.0, *SE["pivot_XZ"])) - float(SE["seat_boss_proud"])     # the RIGHT seat's top


def _crossings(rings, p, d):
    """Signed distances t along d from p where the line p + t d crosses the rings."""
    out = []
    for P in rings:
        Q = np.vstack([P, P[:1]])
        for a, b in zip(Q[:-1], Q[1:]):
            e = b - a
            M = np.array([[d[0], -e[0]], [d[1], -e[1]]])
            if abs(np.linalg.det(M)) < 1e-12:
                continue
            t, u = np.linalg.solve(M, a - p)
            if 0.0 <= u < 1.0:
                out.append(float(t))
    return sorted(out)


def grip_axis_s_of(xz):
    return float((np.asarray(xz, float) - GRIP_O) @ U_DN)


BOTTOM_R = 2.5                                          # the grip cover's traced bottom-corner radius (side view)


def grip_bottom_s():
    """The grip bottom face (perpendicular to the axis): the traced heel and toe."""
    gr = SG.part_ring("grip", 0.3)
    s = [(p - GRIP_O) @ U_DN for p in gr]
    return float(max(s)) - 0.4


def grip_edges(ss):
    """The grip's back / front edge offsets (along V_FW from the axis) at stations ss: the traced outline's crossings
    (master outline + its holes) sampled every 1 mm and smoothed with a local quadratic over +-5 mm (the trace's
    pixel steps would otherwise ripple the moulded surface)."""
    rings_all = [SG.master_outer(0.25)] + SG.master_holes(0.25)
    s_lim = grip_bottom_s() - BOTTOM_R          # below this the traced bottom corners round in (crossings unstable)
    s0, s1 = float(np.min(ss)) - 6.0, min(float(np.max(ss)) + 6.0, s_lim)
    sd = np.arange(s0, s1 + 1e-6, 1.0)
    tb, tf = [], []
    for s in sd:
        t = _crossings(rings_all, GRIP_O + s * U_DN, V_FW)
        tb.append(max([v for v in t if v < 0.0], default=np.nan))
        tf.append(min([v for v in t if v > 0.0], default=np.nan))
    tb, tf = np.array(tb), np.array(tf)
    # upper half: where the guard's rear bar meets the grip front the master outline runs on along the guard, and the
    # front edge's samples > 1 mm beyond the run's median (s < 0) are dropped and bridged from their
    # neighbours
    for y in (tb, tf):
        ok = ~np.isnan(y)
        med = float(np.median(y[ok & (sd > 0.0)])) if np.any(ok & (sd > 0.0)) else float(np.nanmedian(y))
        if y is not tf:
            continue
        bad = ok & (sd < 0.0) & (y - med > 1.0)
        good = ok & ~bad
        y[bad] = np.interp(sd[bad], sd[good], y[good])

    def smooth(y, sign):
        out = []
        for s in ss:
            if s > s_lim:                            # the traced bottom corner: a quarter round of radius BOTTOM_R
                d = min(s - s_lim, BOTTOM_R)
                out.append(float(edge_at_lim(y)) - sign * (BOTTOM_R - math.sqrt(max(BOTTOM_R ** 2 - d * d, 0.0))))
                continue
            m = (np.abs(sd - s) <= 2.0) & ~np.isnan(y)
            if m.sum() < 3:
                out.append(float(np.interp(s, sd[~np.isnan(y)], y[~np.isnan(y)])))
                continue
            c = np.polyfit(sd[m] - s, y[m], 2)
            out.append(float(c[-1]))
        return np.array(out)
    def edge_at_lim(y):
        m = (sd >= s_lim - 5.0) & ~np.isnan(y)
        c = np.polyfit(sd[m] - s_lim, y[m], 1)
        return c[-1]
    return smooth(tb, -1.0), smooth(tf, 1.0)


def grip_sections(s_top, s_bot, step=3.0, n=40, grow=0.0, s_valid=None):
    """Rounded sections (n points) perpendicular to the grip axis at stations s_top..s_bot: fore-aft from the traced
    back / front edges (the master outline and its holes), width GRIP_W, corner radii RF (front) / RB (back). Above
    s_valid (the highest station the trace reads) the section is held: the loft runs on up into the housing.
    (W3) From gunlib.lod level 2 on the loft thins with the level's rules: n points per section x RING_FACTOR, the
    station step x STEP_FACTOR (LOD0 and LOD1 unchanged: LOD1 keeps the grip / cover fit of LOD0)."""
    from gunlib import lod as _lod
    if _lod.LEVEL >= 2:
        n = _lod.ring(n)
        step = _lod.step(step)
    ss = np.arange(s_top, s_bot + 1e-6, step)
    if ss[-1] < s_bot - 1e-6:
        ss = np.r_[ss, s_bot]
    TB, TF = grip_edges(ss if s_valid is None else np.maximum(ss, s_valid))
    out = []
    for s, tb, tf in zip(ss, TB - grow, TF + grow):
        p = GRIP_O + s * U_DN
        L = tf - tb
        w = GRIP_W + 2.0 * grow
        sec = MB.section(L, w, min(RF, 0.45 * L, 0.49 * w), min(RB, 0.45 * L, 0.49 * w), 6, n)
        # sec: x fore-aft centred, y across -> M: centre + x * V_FW, y, axis point
        c = p + 0.5 * (tb + tf) * V_FW
        ring = np.c_[c[0] + sec[:, 0] * V_FW[0], sec[:, 1], c[1] + sec[:, 0] * V_FW[1]]
        out.append(ring)
    return out, ss


def grip_loft():
    s_bot = grip_bottom_s()
    cover_h = float(PG["cover_height"])
    s_seam = s_bot - cover_h
    s_top = grip_axis_s_of((300.0, Z_BODY_BOT + 4.0))
    # the sections are perpendicular to the raked axis: at s_top the front strap's top corner sits 14 mm under the
    # housing (a wedge of daylight the sheet fills); held sections run 16 mm on up into the housing's solid
    rings, ss = grip_sections(s_top - 16.0, s_seam - 0.2, 3.0, s_valid=s_top)
    return loft_capped(rings), (s_top, s_seam, s_bot)


def grip_cover():
    """The separate grip bottom cover (RP13): the grip's section below a 0.3 seam, its base lip flared 3 mm proud as the
    trace draws it (the traced edges include the flare), a flat bottom face (R 1 rim)."""
    s_bot = grip_bottom_s()
    cover_h = float(PG["cover_height"])
    s0 = s_bot - cover_h + 0.2
    rings, ss = grip_sections(s0, s_bot, 0.8)      # (W4 review fixes, G3: 1.6 -> 0.8 mm stations, the flared lip's
    #                                                 front corner read as 2-4 flat facets at 3x)
    m = loft_capped(rings)
    from gunlib.parts import PartDef
    zb = float(np.min(np.vstack(rings)[:, 2]))
    nb = np.array([-U_DN[0], 0.0, -U_DN[1]]) * -1.0           # down the grip axis = the bottom face's outward normal

    def bottom_rim(mid, d, n1, n2, dih, convex):
        return 1.0 if convex and dih > 40.0 and max(abs(n1 @ nb), abs(n2 @ nb)) > 0.95 and             (mid[:2] @ np.array([0.0, 0.0]) == 0.0) and ((mid[[0, 2]] - GRIP_O) @ U_DN) > s_bot - 2.5 else 0.0
    return PartDef("grip_cover", [m], bone="body", cls="P-round", slot=FURN, recipe=[(1.0, 4, "WC", bottom_rim)],
                   joint={"type": "butt", "parent": "lower_receiver", "gap_mm": [0.3, 0.5]}, spec_id="pistol_grip")


def _catmull(pts, n=6):
    """Centripetal Catmull-Rom through pts (open; the end tangents from the end chords)."""
    P = np.asarray(pts, float)
    P = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        t0 = 0.0
        t1 = t0 + np.linalg.norm(p1 - p0) ** 0.5
        t2 = t1 + np.linalg.norm(p2 - p1) ** 0.5
        t3 = t2 + np.linalg.norm(p3 - p2) ** 0.5
        for t in np.linspace(t1, t2, n, endpoint=False):
            a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
            a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
            b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
            b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
            out.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    out.append(P[-2])
    return np.array(out)


# (W1 realism round 1) The trigger blade as one fair curve through the traced outline: the trace's lower end is a pixel
# zig-zag (a stepped, jagged tip and a notch in the finger face at Z -72..-75, the judges' 'bad boolean') and its top
# is the dark band of the housing's edge that the trace labels trigger (the L2 convention measures the blade below the
# housing line). Control points read off the trace's stairs at their middles: the rear edge from the housing down to the
# tip, the forward-curled tip (front 378.3 / -80.6, bottom -82.75), the finger face (370.9 at Z -66.5, spec finger face
# 370.8 / -70.6) back up into the housing, the root flaring to the drawn 360.2 .. 374.0 at the opening's top; the
# blade continues 4 mm up into its slot (hidden).
TRIGGER_REAR = [(360.2, -47.0), (360.2, -51.0), (360.7, -53.3), (361.9, -55.6), (362.3, -60.0), (362.6, -64.6),
                (363.4, -69.5),
                (365.0, -73.6), (368.6, -78.3), (371.9, -81.9), (373.6, -82.75), (375.6, -82.6), (377.3, -81.9),
                (378.2, -80.7), (377.8, -79.5), (376.5, -78.0), (374.6, -75.9), (372.7, -73.3), (371.4, -70.5),
                (370.9, -66.5), (371.1, -62.0), (371.5, -57.6), (372.4, -55.3), (373.3, -52.9), (373.9, -51.3),
                (374.0, -47.0)]


def trigger_blade():
    C = _catmull(TRIGGER_REAR, 6)
    return G.ccw(G.dedupe(G.dp_simplify(C, 0.01), 0.05))


def trigger_profile():
    """The trigger blade's side outline (one fair curve through the trace) + the tongue up to and round its axle
    (inside the housing)."""
    blade = trigger_blade()
    ax, az = TRG["pivot_XZ"]
    tongue = np.vstack([G.arc(ax, az, 4.2, 0.0, 180.0, 9), [[ax - 4.2, Z_BODY_BOT - 3.0], [ax + 4.2, Z_BODY_BOT - 3.0]]])
    return blade, tongue


def _hull2d(P):
    """Convex hull (Andrew's monotone chain), counter-clockwise."""
    pts = sorted(set(map(tuple, np.round(np.asarray(P, float), 9))))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    return np.array(lo[:-1] + hi[:-1], float)


def _rotY(P, c, deg):
    t = math.radians(deg)
    a = P - c
    return np.c_[c[0] + a[:, 0] * math.cos(t) + a[:, 1] * math.sin(t), c[1] - a[:, 0] * math.sin(t) + a[:, 1] *
                 math.cos(t)]


def splice_front(P, F, x_edge, tol=1e-6):
    """P (CCW, clipped at X <= x_edge) with the outline F (CCW, clipped at X >= x_edge) joined along P's front edge
    (the vertical run at x_edge, going up in a CCW ring): F's points beyond the edge inserted between the run's ends."""
    P, F = G.ccw(np.asarray(P, float)), G.ccw(np.asarray(F, float))
    if len(F) < 3:
        return P
    on = np.abs(F[:, 0] - x_edge) < 1e-4
    zf0, zf1 = float(F[on, 1].min()), float(F[on, 1].max())
    n = len(P)
    for i in range(n):
        a, b = P[i], P[(i + 1) % n]
        if abs(a[0] - x_edge) < 1e-4 and abs(b[0] - x_edge) < 1e-4 and a[1] < zf0 and b[1] > zf1:
            k0 = int(np.where(on & (np.abs(F[:, 1] - zf0) < 1e-6))[0][0])
            ring = np.roll(F, -k0, axis=0)                     # starts at the bottom point on the edge, CCW
            ring = ring[1:]
            ring = ring[:int(np.where(np.abs(ring[:, 0] - x_edge) < 1e-4)[0][0]) + 1]   # up to the top point
            ins = np.vstack([[F[k0]], ring])
            return G.ccw(np.vstack([P[:i + 1], ins, P[i + 1:]]))
    return P


def guard_opening(fillet=True):
    """The trigger guard's opening (XZ, CCW): the traced hole wraps round the DRAWN blade (a peninsula hanging from the
    housing); its run along the blade (points within 2.5 of the fair blade) is dropped and the opening closes along
    its straight top, then faired. (Split in two holes by a blade drawn to the bottom bar, the chains are joined rear ->
    front the same way.)"""
    raw = [np.array(r["mm"], float) for r in SG.trace("LEFT")["gun_without_magazine"] if r["kind"] == "hole"]
    gh = [SG.fair_ring(hr, corner_deg=25.0, sigma=0.8) for hr in raw if 330.0 < hr[:, 0].min() and hr[:, 0].max() < 410.0
          and hr[:, 1].max() < -40.0] or SG.part_holes("trigger_guard")
    rings = sorted(gh, key=lambda h: float(h[:, 0].mean()))
    drawn = trigger_blade()                          # the fair blade (the traced ring carries the housing band)
    Q = np.vstack([drawn, drawn[:1]])

    def dist_to_blade(p):
        A, B = Q[:-1], Q[1:]
        AB = B - A
        t = np.clip(((p - A) * AB).sum(1) / np.maximum((AB * AB).sum(1), 1e-12), 0.0, 1.0)
        d = float(np.min(np.linalg.norm(A + AB * t[:, None] - p, axis=1)))
        return 0.0 if G.point_in_poly(p, drawn) else d

    chains = []
    for h in rings:
        h = G.ccw(G.resample(h, 0.4))
        zt = float(drawn[:, 1].min()) - 0.2        # the opening's bottom run under the blade's tip stays
        keep = np.array([dist_to_blade(p) > 2.5 or p[1] < zt for p in h])     # 2.5: the closing top clears the
        #                                                                          trigger slot's swept walls
        k0 = int(np.argmin(keep))                    # a dropped point: start the scan there
        order = [(k0 + i) % len(h) for i in range(len(h))]
        runs, cur = [], []
        for i in order:
            if keep[i]:
                cur.append(i)
            elif cur:
                runs.append(cur)
                cur = []
        if cur:
            runs.append(cur)
        chains.append(h[max(runs, key=len)])
    if len(chains) == 1:
        # the opening's top across the blade's root at the front run's level (the drawn root flares into the housing's
        # edge there, the trace labels it trigger): the rear run's top (Z -52.3) rises on a 45 deg step 1.4 behind the
        # trigger slot's swept rear wall
        c = chains[0]
        ztf = float(np.max(c[c[:, 0] > float(drawn[:, 0].max()), 1]))   # the front run's top (the drawn -51.3)
        zr = float(c[0, 1])
        xr0 = float(drawn[:, 0].min()) - 0.3 - 1.4
        top = c[:, 1] > ztf - 0.6
        c = np.c_[c[:, 0], np.where(top & (c[:, 0] > float(drawn[:, 0].max())) & (c[:, 0] < c[:, 0].max() - 3.0), ztf,
                                    c[:, 1])]                   # the front run's top held straight at its level
        P = np.vstack([c, [[xr0, ztf], [xr0 - (ztf - zr), zr]]]) if c[-1, 0] > c[0, 0] else c
    else:
        P = np.vstack(chains)
    P = G.ccw(SG.fair_ring(P, corner_deg=25.0, sigma=0.8))
    if not fillet:
        return P                                     # the loop's outer offset is grown from the unrounded opening
    # (W1 realism round 2) the drawn 45 deg corner chamfers rounded at the spec's inner corner radius (trigger_guard
    # inner_corner_R 6-8; the tangent clamp keeps each arc on its chamfer): the judges read the crisp-cornered loop as a
    # thin octagonal stamping
    # (the faired ring's dense short edges clamp a fillet to nothing: simplified at 0.2 first, so each chamfer is one
    # edge and the R 6 arcs fit)
    Q = G.ccw(G.dedupe(G.dp_simplify(P, 0.2), 0.3))
    # (W4 review fixes, craft G3) 8 segments per corner (was 3: 15 deg facets on the R 6 rounds at 3x)
    return G.ccw(G.fillet(Q, float(TG["inner_corner_R"][0]), _guard_seg(), min_turn_deg=8.0))


def _guard_seg():
    """The guard's corner segments: 8 at LOD0; at LOD1+ the LOD count (4). (W4 resume: at LOD1 the 8-segment rounds of
    the gentle corners put 0.3 mm chords on the guard's flat side faces, and their triangulation left 2 needles,
    0.005-0.007 mm high: UD1 / UD2; 4 segments double the chord and quadruple that height)"""
    from gunlib import lod as _lod
    return _lod.count(8, 2)


def _round_outer(P, r, x_keep):
    P = G.ccw(G.dedupe(G.dp_simplify(G.ccw(P), 0.1), 0.3))
    n = len(P)
    radii = []
    for i in range(n):
        a, b, c = P[i - 1], P[i], P[(i + 1) % n]
        u, v = b - a, c - b
        turn = math.degrees(abs(math.atan2(u[0] * v[1] - u[1] * v[0], float(u @ v))))
        radii.append(r if (12.0 < turn < 60.0 and b[0] < x_keep - 1.0) else 0.0)
    return G.ccw(G.fillet(P, r, _guard_seg(), min_turn_deg=8.0, radii=radii))


FUNNEL_DEG = 35.0                                      # the funnel chamfer from horizontal
FUNNEL_Z0 = -49.6                                      # its start on the housing's side faces (the housing's bottom at
#                                                        the well's front, X 462; behind it the bottom lies up to 1.15
#                                                        lower: a matching 35 deg chamfer along its bottom edges)


def magwell_funnel():
    """A YZ section prism (along X) intersected with the housing zone only: everything outside the two 35 deg lines
    through the set-in side faces at Z FUNNEL_Z0 (down to 1.0 inside the well's body width, which the magwell zone
    fills) goes."""
    t = math.tan(math.radians(FUNNEL_DEG))
    al, ar = SG.Y_L - LO_INSET, -(SG.Y_R + LO_INSET)
    yi = MW_BODY - 1.0
    sec = np.array([[-yi, -130.0], [yi, -130.0], [yi, FUNNEL_Z0 - (al - yi) * t], [60.0, FUNNEL_Z0 + (60.0 - al) * t],
                    [60.0, 40.0], [-60.0, 40.0], [-60.0, FUNNEL_Z0 + (60.0 - ar) * t],
                    [-yi, FUNNEL_Z0 - (ar - yi) * t]])
    return prism(G.ccw(sec), X_EBF - H - 5.0, 505.0, "YZ")


def lower_receiver():
    bz = BORE_Z
    opening = guard_opening()
    # ---------------- zones (XZ outline x Y range)
    eb = prism(G.rounded_rect(X_EBR + 0.2, X_EBF - H + 0.6, -60.0, 60.0, 0.0), EB_Y[0], EB_Y[1], "XZ")
    # (W1 realism round 2) the skirt beside the magwell (X 0.4 inside the well's rear wall .. the front face, down to
    # Z -58) cut by the 35 deg funnel chamfer (magwell_funnel): the full-width housing flares into the narrower well as
    # one moulding (the judges: the well a separate block stacked under a shelf)
    zl462 = Z_BODY_BOT + (462.0 - 500.0) * ((-50.7 - Z_BODY_BOT) / (409.2 - 500.0))
    body_xz = SG.polygon_from([(X_EBF - H, 20.0), (500.0, 20.0), (500.0, Z_BODY_BOT), (462.0, zl462), (462.0, -58.0),
                               (wall_line_x(-58.0) + 0.4, -58.0), (wall_line_x(-50.75) + 0.4, -50.75),
                               (341.4, -50.8), (323.4, -48.7), (289.3, -43.4), (272.2, -32.8), (X_EBF - H, -30.0)])
    body = prism(body_xz, SG.Y_R + LO_INSET, SG.Y_L - LO_INSET, "XZ")
    zw0 = Z_BODY_BOT + 1.0
    mw_xz = SG.polygon_from([(wall_line_x(zw0), zw0), (520.0, zw0), (520.0, -110.0), (wall_line_x(-110.0), -110.0)])
    mw_body = prism(mw_xz, -MW_BODY, MW_BODY, "XZ")
    lf, lr = MW["lip_lower_edge_front_XZ"], MW["lip_lower_edge_rear_XZ"]
    slope = (lf[1] - lr[1]) / (lf[0] - lr[0])
    fh = float(np.mean(MW["flare_height"]))
    zl = lambda x: lr[1] + slope * (x - lr[0])          # noqa: E731
    band_xz = SG.polygon_from([(wall_line_x(zl(400.0) + fh), zl(400.0) + fh - 0.0), (520.0, zl(520.0) + fh),
                               (520.0, zl(520.0) - 12.0), (wall_line_x(zl(400.0) - 12.0), zl(400.0) - 12.0)])
    band = prism(band_xz, -MW_LIP, MW_LIP, "XZ")
    # (W1 realism round 1) the guard loop: the joined opening grown 8 mm at the bar width, its front face at the drawn
    # front leg (X 402.2, the paddle's slot in front of it), cut to the side silhouette by the master outline and
    # hollowed by the opening (ops): the bar's inner faces come from the opening alone, its outer faces from the
    # master. (The guard part ring's own pixel-stair inner run crossed the faired opening: a 0.3 ledge where the web
    # ended, multi-face edges, the judges' chipped rim.)
    xl_ = float(TG["front_leg"]["X"][1]) - 0.15      # the leg's front face 0.15 behind the drawn 402.2: the paddle's
    #                                                 rear face sweeps 0.02 off it there (B3 row >= 0.1; the old traced
    #                                                 ring's face wandered 0.1-0.3 behind the line)
    g_out = G.ccw(G.clip_x(G.offset(guard_opening(fillet=False), 8.0), None, xl_))
    # (W4 review fixes, craft G3) the offset's mitred chamfer corners (one 22-45 deg kink each, the guard's 'chunky
    # bends' at 3x) take the inner corners' radius + the bar (R 14), <= 7.5 deg per segment; the clip line's corners at
    # the front leg (X xl_) stay sharp (the paddle's slot and the foot splice need them)
    g_out = _round_outer(g_out, float(TG["inner_corner_R"][0]) + 8.0, xl_)
    # the guard's front foot as drawn (the bar's lower front corner runs on forward under the paddle to the magwell,
    # X 402..409, Z -75..-80): the guard part ring in front of the leg below Z -74 (away from the opening), spliced
    # into the loop's front edge (one outline: a separate prism met the loop coplanar, multi-face edges)
    foot_xz = G.ccw(G.clip_y(G.clip_x(SG.part_ring("trigger_guard"), xl_, None), None, -74.0))
    g_out = splice_front(g_out, foot_xz, xl_)
    guard = prism(g_out, -TG["bar_width_Y"] / 2.0, TG["bar_width_Y"] / 2.0, "XZ")
    foot = None
    # the web where the guard's rear bar runs into the grip's front strap (the master outline fills it; the grip's
    # rounded sections stop at the strap): guard-bar wide, from 3 mm inside the strap, clipped by the master outline
    # and the guard opening
    web = box(336.0, 356.0, -TG["bar_width_Y"] / 2.0, TG["bar_width_Y"] / 2.0, -88.0, Z_BODY_BOT + 1.0)   # (r1: its floor
    #                                   at -84.0 left a 0.02 mm sliver under the joined opening's bottom run; the master clips it)
    # (W1 realism round 2) the guard's rear bar flares into the grip's front strap (a moulded web, half width 9.0 at
    # X 330 inside the strap -> the bar's 5.45 at X 352, below Z -74; clipped by the master outline, hollowed by the
    # opening): the
    # judges read the bar running into the grip as a thin bar with no blend
    hw_ = TG["bar_width_Y"] / 2.0
    web_flare = prism(np.array([[330.0, -9.0], [352.0, -hw_], [352.0, hw_], [330.0, 9.0]]), -95.0, -74.0,
                      "XY")
    # clevis ears (2.0 thick each side of the paddle, 0.3 off it), from the housing bottom down past the pin
    pz_top, pz_bot = TG["paddle_clevis"]["Z"][0], TG["paddle_clevis"]["Z"][1]
    pw = MR["width_Y"] / 2.0
    xr0 = float(TG["front_leg"]["X"][1]) - 0.5
    ears = [box(xr0, wall_line_x(pz_bot) + 0.4, s * (pw + 0.3), s * (pw + 0.3 + 2.0), pz_bot, Z_BODY_BOT + 0.6)
            for s in (1.0, -1.0)]
    ears = [box(xr0, wall_line_x(pz_bot) + 0.4, min(b.verts()[:, 1]), max(b.verts()[:, 1]), pz_bot, Z_BODY_BOT + 0.6)
            for b in ears]
    # ---------------- edge predicates
    seam_z = float(SEAM[0, 1]) - H

    lo_seam = SG.offset_polyline(SEAM, -H)

    def near_seam(x, z, tol=1.3):
        p = np.array([x, z])
        for a, b in zip(lo_seam[:-1], lo_seam[1:]):
            ab = b - a
            t = np.clip((p - a) @ ab / max(ab @ ab, 1e-12), 0.0, 1.0)
            if np.linalg.norm(a + t * ab - p) < tol:
                return True
        return False

    def outer_round(mid, d, n1, n2, dih, convex):
        if not convex or dih < 35.0:
            return 0.0
        if near_seam(mid[0], mid[2]):
            return 0.0                                           # the seam edges (horizontal run, tab, V, face)
        if MW_BODY - 0.1 <= abs(mid[1]) <= MW_LIP + 0.1 and -3.5 < mid[2] - (zl(mid[0]) + fh) < 1.0:
            return 0.0                                           # the flare band's 45 deg top chamfer (its own step)
        if X_EBF - H - 0.8 < mid[0] < X_EBF and mid[2] > seam_z - 1.2:
            return 0.0                                           # the end block's front seam
        if mid[2] > Z_TOP - 0.8 and mid[0] > X_RAIL0 - 1.0:
            return 0.0                                           # under the rail
        if ox0 < mid[0] < ox1 and oz0 < mid[2] < oz1 + 0.5 and G.point_in_poly((mid[0], mid[2]), opening_g):
            # the guard opening's rim: R 1.05 (the 2.2 front leg) on the guard's faces; not its rear run, where the grip
            # loft's front strap meets the guard's faces (a many-edge corner the bevel tore open)
            return 0.75 if mid[0] > ox0 + 10.5 and abs(mid[1]) < TG["bar_width_Y"] / 2.0 + 0.1 else 0.0
        return 1.0

    ox0, ox1 = float(opening[:, 0].min()) - 0.5, float(opening[:, 0].max()) + 0.5
    oz0, oz1 = float(opening[:, 1].min()) - 0.5, float(opening[:, 1].max())
    opening_g = G.offset(opening, 0.6)
    x_run = float(SEAM[1, 0]) - 0.5

    def seam_break(mid, d, n1, n2, dih, convex):
        if not convex or not (60.0 <= dih <= 120.0):
            return 0.0
        return 1.0 if (abs(mid[2] - seam_z) < 0.6 and X_EBF - H - 1.0 < mid[0] < x_run) or \
            (X_EBF - H - 0.8 < mid[0] < X_EBF and mid[2] > seam_z) else 0.0

    def flare_chamfer(mid, d, n1, n2, dih, convex):
        if not convex or not (60.0 <= dih <= 120.0):
            return 0.0
        # (r1) the band's top as built lies 1.2 under the lip line + flare height (the master outline's drawn flare
        # clips it): the window was 0.6 round the nominal and the chamfer never ran (0 edges); the judges read the
        # unchamfered band under the R 1.4 round as an architectural cornice
        if abs(abs(mid[1]) - MW_LIP) < 0.1 and -1.9 < mid[2] - (zl(mid[0]) + fh) < 0.6:
            return 1.0
        return 0.0

    # ---------------- cuts
    cuts = []
    # the guard opening: ONE moulded opening (W1 realism round 1). The traced hole wraps round the drawn blade; cut
    # as traced, plus the blade's region (+0.6, a 0.3 relief over the opening's top), it left notches, slivers and the
    # relief in the opening's top (the judges' broken guard rim). guard_opening() drops the blade's run and closes the
    # opening along its straight top; it is cut before the rounds (ops below) so its rim is rounded like the guard.
    # magwell cavity: the magazine + 0.3 per side, up into the upper's cavity; the mouth flare (1.6 per side at the lip
    # to 0 at 9.5 above it, along the mag axis)
    fa = MAGD["foreaft"] / 2.0 + 0.3
    th = MAGD["thickness"] / 2.0 + 0.3
    # concentric with the magazine's corners (R 3.0 / 2.5 + 0.3), 6 segments per corner, no resample (a 36-point
    # resample cut the corners as chords 0.33 inside the magazine's round corners)
    sec_in = MB.section(2 * fa, 2 * th, 3.3, 2.8, 6)
    # the insertion lead-in (real pattern: the moulded well's mouth is a shallow taper, the guide is the outer flare
    # band and the magazine's own tapered top; W1b fix round, M2): +0.25 per side at the lip, back to the 0.3 fit 2.5
    # above it, following the slanted lip line in the mag frame, so the seam seen at the well's lower edge is 0.55
    # (M2 <= 0.6). The former 1.6 mouth flare left a 1.9 mm visible gap all round.
    lead, lead_h = 0.25, 2.5
    sec_lead = MB.section(2 * fa + 2 * lead, 2 * th + 2 * lead, 3.3 + lead, 2.8 + lead, 6)
    zt = MAGD["top_along_axis"] + 12.0
    M4 = mag_M4()
    lf_l = [(np.array([p[0], 0.0, p[1]]) - MAG_O) for p in (MW["lip_lower_edge_front_XZ"], MW["lip_lower_edge_rear_XZ"])]
    (xf_, zf_), (xr_, zr_) = [(float(d @ MAG_X), float(d @ MAG_Z)) for d in lf_l]
    z_lip = lambda x: zr_ + (zf_ - zr_) * (np.asarray(x) - xr_) / (xf_ - xr_)      # noqa: E731

    def ring(sec, dz):
        return np.c_[sec, z_lip(sec[:, 0]) + dz]
    rings = [ring(sec_lead, -25.0), ring(sec_lead, 0.0), ring(sec_in, lead_h), np.c_[sec_in, np.full(len(sec_in), zt)]]
    cuts.append(loft(rings).transformed(M4))
    # the catch window in the rear wall (the paddle's nose passes through it to the notch)
    cw = MW["catch_window"]
    cuts.append(box(mag_rear_x(cw["Z"][1]) - MW["wall"] - 3.5, mag_rear_x(cw["Z"][0]) + 1.0, -cw["width_Y"] / 2.0,
                    cw["width_Y"] / 2.0, cw["Z"][0], cw["Z"][1]))
    # the paddle's slot: open between the guard's front leg and the rear wall below the housing; through the housing
    # bottom for the paddle's upper body (0.3 per side) and its nose (3.2 half width + 0.3) up to the window
    xl = float(TG["front_leg"]["X"][1])
    # (its front face 0.1 into the wall's outer face: coplanar with the well's rear face it left a 0.002 mm strip and a
    # degenerate triangle where the traced outline crosses the wall line, W1b fix round UD1-UD2)
    cuts.append(prism(np.array([[xl, -100.0], [wall_line_x(-100.0) + 0.1, -100.0], [wall_line_x(Z_BODY_BOT) + 0.1,
                                Z_BODY_BOT + 0.0], [xl, Z_BODY_BOT + 0.0]]), -(pw + 0.3), pw + 0.3, "XZ"))
    # the nose's slot: open 3.6 behind the guard leg's line too (released, the nose swings 3.5 rearward)
    nose_slot = np.array([[xl - 3.6, Z_BODY_BOT - 1.0], [wall_line_x(Z_BODY_BOT) + 0.3, Z_BODY_BOT - 1.0],
                          [wall_line_x(cw["Z"][0] + 0.2) + 0.3, cw["Z"][0] + 0.2], [xl - 3.6, cw["Z"][0] + 0.2]])
    # (r1: its top 0.2 into the catch window: level with the window's floor the two cuts met coplanar, 6 multi-face
    # edges left to the repair)
    cuts.append(prism(nose_slot, -3.6, 3.6, "XZ"))
    # the guard leg's front face relieved 1.2 above the pin (released, the paddle's top swings 0.8 rearward)
    cuts.append(box(xl - 1.2, xl + 0.5, -(pw + 0.3), pw + 0.3, float(MR["pivot_XZ"][1]) - 0.9, Z_BODY_BOT + 0.5))
    # the trigger slot: the blade + tongue swept 0..+13 deg about the axle, grown 0.3, 6.6 wide
    blade, tongue = trigger_profile()
    tp = TRG["pivot_XZ"]
    trig_cutters = [prism(_rotY(G.offset(G.ccw(blade), 0.3), np.array(tp), a), -TRG["width"] / 2.0 - 0.3,
                          TRG["width"] / 2.0 + 0.3, "XZ")
                    for a in np.linspace(0.0, float(TRG["pull_rot_Y_deg"]) + 1.0, 3)]
    # the tongue's arc is concentric with the axle: three rotated copies laid coincident arcs on each other and the
    # booleans left 0.006 mm2 fan slivers on the slot walls (UD1). One cutter instead: the hull of the tongue swept
    # 0..+14 deg, its arc simplified to 0.02 mm sagitta (chords ~0.85 mm)
    tw = np.vstack([_rotY(G.offset(G.ccw(tongue), 0.3), np.array(tp), a)
                    for a in np.linspace(0.0, float(TRG["pull_rot_Y_deg"]) + 1.0, 29)])
    tongue_sw = G.ccw(G.dp_simplify(G.ccw(_hull2d(tw)), 0.02))
    trig_cutters.append(prism(tongue_sw, -TRG["width"] / 2.0 - 0.3, TRG["width"] / 2.0 + 0.3, "XZ"))
    cuts += trig_cutters
    # bores: selector shaft (dia 5.0 + 0.3), trigger axle (press 0.02), paddle pin in the ears (press 0.02)
    sp = SE["pivot_XZ"]
    cuts.append(cylinder((sp[0], -45.0, sp[1]), (sp[0], 45.0, sp[1]), 2.5 + 0.15, 32))
    cuts.append(cylinder((tp[0], -40.0, tp[1]), (tp[0], 40.0, tp[1]), dims("pins_fasteners")["list"][3]["dia"] / 2.0 + 0.04,
                         32))                                        # press fit 0.04 (G5 >= 0.01 after the repair)
    mp = MR["pivot_XZ"]
    cuts.append(cylinder((mp[0], -10.0, mp[1]), (mp[0], 10.0, mp[1]), MR["pin_dia"] / 2.0 + GAP, 24))
    # the lower rail's rear end butts against the lower's front (0.3 clearance). (W1 realism round 1: a pocket tucked
    # the rail end 4.1 into the well; the lower's thin walls round it, cut to the outline's step there, read as a torn
    # hooked flap above the magwell. The lower now ends in one flat face across the rail band, X 484.2.)
    lr0 = float(sbox("lower_rail")["X"][0])
    cuts.append(box(lr0 - 0.3, 525.0, -40.0, 40.0, float(dims("lower_rail")["bottom_Z"]) - 0.5,
                    float(dims("lower_rail")["top_seam_Z"]) + 0.2))
    # oblong recess (LEFT only, 0.8 deep, R 0.3 rim)
    orc = feature("lower_receiver", "oblong_recess")
    cuts.append(prism(stadium_xz(orc["X"][0], orc["X"][1], 0.5 * sum(orc["Z"]), orc["Z"][1] - orc["Z"][0]),
                      SG.Y_L - LO_INSET - 0.8, SG.Y_L + 1.0, "XZ"))
    # flush pin holes
    for name, side, xz, d in pin_holes("lower"):
        yf = pin_face_y(side, xz[0], xz[1])
        cuts.append(HW.place(HW.pin_hole_cutter(d, 2.6, 0.15), (xz[0], yf, xz[1]), (0, side, 0)))
    sbp = [q for q in dims("pins_fasteners")["list"] if q["name"] == "seam boss pin"][0]
    sbf = feature("lower_receiver", "seam_boss")
    cuts.append(HW.place(HW.pin_hole_cutter(sbp["dia"], 2.0, 0.15), (sbp["XZ"][0], PAD_TOP_L, sbp["XZ"][1]),
                         (0, 1.0, 0)))           # in the pad's boss lobe (2.4 thick over the upper's pocket): 2.0 deep
    # the stipple panel's border: the panel set in 0.55 on both grip sides (a rounded rect along the grip axis)
    s_top, s_seam, s_bot = grip_loft()[1]
    pan = PG["stipple_panel"]
    Ltot = s_bot - s_top
    sa, sb_ = s_top + pan["top_inset_frac"] * Ltot + 4.0, s_bot - pan["bottom_inset_frac"] * Ltot - float(PG["cover_height"])
    rings_all = [SG.master_outer(0.25)] + SG.master_holes(0.25)
    pts_b, pts_f = [], []
    for s in np.linspace(sa, sb_, 12):
        p = GRIP_O + s * U_DN
        t = _crossings(rings_all, p, V_FW)
        tb = max([v for v in t if v < 0.0], default=-20.0) + pan["strap_inset"]
        tf = min([v for v in t if v > 0.0], default=20.0) - pan["strap_inset"]
        pts_b.append(p + tb * V_FW)
        pts_f.append(p + tf * V_FW)
    panel = G.fillet(np.array(pts_f + pts_b[::-1]), 4.0, 4)
    step = float(np.mean(pan["border_step"]))
    for sgn in (1.0, -1.0):
        y0 = sgn * (GRIP_W / 2.0 - step)
        cuts.append(prism(panel, min(y0, sgn * (GRIP_W / 2.0 + 3.0)), max(y0, sgn * (GRIP_W / 2.0 + 3.0)), "XZ"))
    # ---------------- unions after the main rounds: seat bosses, seam boss, hinge knuckles, latch lug
    # the seats rise from the set-in housing face to 1.0 over the upper's face (the selector rides on them as before);
    # LEFT: the seat and the seam boss are one pad (selector_pad_xz)
    seat_r_ = float(LO_feature("selector_seats")["dia"]) / 2.0
    seats = [pcyl((sp[0], -(abs(face_y_lower(-1.0, sp[0], sp[1])) - 0.6), sp[1]), (sp[0], PAD_TOP_R, sp[1]), seat_r_,
                  64)]
    pad = selector_pad_xz()
    seam_boss = prism(pad, face_y_lower(1.0, sp[0], sp[1]) - 0.6, PAD_TOP_L, "XZ")
    pad_g = G.offset(pad, 0.6)

    def pad_round(mid, d, n1, n2, dih, convex):
        if not convex or dih < 35.0:
            return 0.0
        if abs(mid[1] - PAD_TOP_L) < 0.06 and G.point_in_poly((mid[0], mid[2]), pad_g):
            return 1.0
        if abs(mid[1] - PAD_TOP_R) < 0.06 and math.hypot(mid[0] - sp[0], mid[2] - sp[1]) < seat_r_ + 0.6:
            return 1.0
        return 0.0
    ax, ay = SH["axis_X"], SH["axis_Y"]
    r_k = SH["knuckle_od"] / 2.0
    kn = HG.knuckle_stack((ax, ay, 0.0), (0, 0, 1), [(-22.0, -10.0, "fixed"), (-10.0, 18.0, "moving"),
                                                     (18.0, 30.0, "fixed")], r_k, SH["axle_dia"] / 2.0, 0.15, 0.15, 48)
    lug = SH["latch"]["lug"]
    lug_box = box(lug["X"][0], X_EBR + 1.0, lug["Y"][0], lug["Y"][1], lug["Z"][0], lug["Z"][1])
    lug_cuts = [cylinder((lug["bore"]["centre_XZ"][0], lug["Y"][0] - 1.0, lug["bore"]["centre_XZ"][1]),
                         (lug["bore"]["centre_XZ"][0], lug["Y"][1] + 1.0, lug["bore"]["centre_XZ"][1]),
                         lug["bore"]["dia"] / 2.0 + 0.01, 32),          # 4.32: the 32-gon chords keep 0.15
                # the lug's outer face relieved 0.8 under the latch button (X < 245.4): folding, the pressed button
                # and the bolt's outer shoulder drift up to 0.46 inward across it
                box(lug["X"][0] - 1.0, 245.4, lug["Y"][1] - 0.8, lug["Y"][1] + 1.0, lug["Z"][0] - 1.0,
                    lug["Z"][1] + 1.0),
                box(lug["X"][0] - 1.0, lug["bore"]["centre_XZ"][0], lug["Y"][0] - 1.0, lug["Y"][1] + 1.0,
                    lug["bore"]["centre_XZ"][1] - lug["exit_slot"]["width_Z"] / 2.0,
                    lug["bore"]["centre_XZ"][1] + lug["exit_slot"]["width_Z"] / 2.0)]
    knuckle_bores = [cylinder((ax, ay, -24.0), (ax, ay, 32.0), SH["axle_dia"] / 2.0 + 0.15, 48),
                     # the stock-side centre knuckle's clearance in the end block's corner (hinge row 0.3)
                     cylinder((ax, ay, -10.0 - 0.15), (ax, ay, 18.0 + 0.15), r_k + 0.3, 64)]

    faces = [SG.Y_L - LO_INSET, SG.Y_R + LO_INSET, MW_BODY, -MW_BODY, MW_LIP, -MW_LIP, TG["bar_width_Y"] / 2.0,
             -TG["bar_width_Y"] / 2.0,
             EB_Y[0], EB_Y[1], GRIP_W / 2.0 - step, -(GRIP_W / 2.0 - step)]

    def lip_break(mid, d, n1, n2, dih, convex):
        if not convex or not (60.0 <= dih <= 120.0):
            return 0.0
        if 318.0 < mid[0] < 412.0 and mid[2] < -44.0 and abs(mid[1]) < 7.0:
            return 0.0              # the guard bar, trigger slot and clevis: edges closer than the break's width
        return 1.0 if any(abs(mid[1] - f) < 0.06 for f in faces) and mid[2] < seam_z - 0.8 else 0.0

    base = body
    gl, _ = grip_loft()
    # (W4 review fixes, craft G17 / G5) the housing's tongue (the V's lower leg, up to the apex at X 484) follows the
    # upper's plan, set in LO_INSET under it all the way: in front of the upper's 45 deg fore-end step (X 482.6-486.5)
    # it was held at the body width (Y_R + 0.8 = -30.8), 3.1 mm proud of the fore-end's face (F_R -27.7; left 1.0 over
    # F_L 29.0): a standing wedge face along the V's front leg (the review's stair-stepped edge and black sliver at the
    # catch / V-panel junction, and the dark seam segment on the left)
    xs = SG.FORE_END_STEP_X
    plan = np.array([[X_EBF - H - 6.0, SG.Y_R + LO_INSET], [xs - (SG.F_R - SG.Y_R), SG.Y_R + LO_INSET],
                     [xs, SG.F_R + LO_INSET], [530.0, SG.F_R + LO_INSET], [530.0, SG.F_L - LO_INSET],
                     [xs, SG.F_L - LO_INSET], [xs - (SG.Y_L - SG.F_L), SG.Y_L - LO_INSET],
                     [X_EBF - H - 6.0, SG.Y_L - LO_INSET]])
    plan_lower = prism(G.ccw(plan), -200.0, 80.0, "XY")
    faces += [SG.F_L - LO_INSET, SG.F_R + LO_INSET]
    ops = [("intersect", [magwell_funnel()]), ("intersect", [plan_lower]),
           ("union", [eb, mw_body, band, guard, foot, web_flare] + ears),     # (r1: the web is inside the grown guard)
           ("intersect", [master_prism()]), ("intersect", [prism(region_lower(), -60.0, 60.0, "XZ")]),
           ("union", [gl]),
           ("diff", [prism(opening, -20.0, 20.0, "XZ")]),
           ("bevel_wc", (1.8, 1, flare_chamfer)),
           ("bevel_wc", (1.4, 2, outer_round)), ("bevel_wc", (0.4, 1, seam_break)),
           ("union", seats + [seam_boss] + kn["fixed"] + [lug_box]),
           ("bevel_wc", (0.6, 2, pad_round)),
           ("diff", cuts + lug_cuts + knuckle_bores),
           ("bevel_wc", (0.35, 1, lip_break))]
    return Ops("lower_receiver", base, ops, bone="body", cls="P-round", slot=FURN, spec_id="lower_receiver",
               joint={"type": "seam", "parent": "upper_receiver", "gap_mm": [0.3, 0.5], "depth_mm": 0.6})


def LO_feature(name):
    return feature("lower_receiver", name)


def build_all():
    return [lower_receiver(), grip_cover()]
