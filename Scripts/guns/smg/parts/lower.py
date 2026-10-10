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
                       pin_holes, face_y, LEDGE, Z_LEDGE, stadium_xz, SH)

GRIP_W = float(PG["width_Y"])                          # 32 (real norm, unseen)
RF, RB = 0.5 * sum(PG["front_strap_R"]), 0.5 * sum(PG["back_strap_R"])
RAKE = math.radians(float(PG["axis_rake_deg_from_vertical"]))
U_DN = np.array([-math.sin(RAKE), -math.cos(RAKE)])     # down the grip axis (XZ)
V_FW = np.array([math.cos(RAKE), -math.sin(RAKE)])      # forward, perpendicular to the axis
GRIP_O = np.array([SPECD["frames"]["B"]["Grip_in_M"][0], SPECD["frames"]["B"]["Grip_in_M"][2]])
MW_BODY = float(MW["outer_width_body"]) / 2.0
MW_LIP = float(MW["outer_width_lip"]) / 2.0


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
    s_valid (the highest station the trace reads) the section is held: the loft runs on up into the housing."""
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
    rings, ss = grip_sections(s0, s_bot, 1.6)
    m = loft_capped(rings)
    from gunlib.parts import PartDef
    zb = float(np.min(np.vstack(rings)[:, 2]))
    nb = np.array([-U_DN[0], 0.0, -U_DN[1]]) * -1.0           # down the grip axis = the bottom face's outward normal

    def bottom_rim(mid, d, n1, n2, dih, convex):
        return 1.0 if convex and dih > 40.0 and max(abs(n1 @ nb), abs(n2 @ nb)) > 0.95 and             (mid[:2] @ np.array([0.0, 0.0]) == 0.0) and ((mid[[0, 2]] - GRIP_O) @ U_DN) > s_bot - 2.5 else 0.0
    return PartDef("grip_cover", [m], bone="body", cls="P-round", slot=FURN, recipe=[(1.0, 2, "WC", bottom_rim)],
                   joint={"type": "butt", "parent": "lower_receiver", "gap_mm": [0.3, 0.5]}, spec_id="pistol_grip")


def trigger_profile():
    """The trigger blade's side outline (trace) + the tongue up to and round its axle (inside the housing)."""
    blade = SG.part_ring("trigger", 0.2)
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


def lower_receiver():
    bz = BORE_Z
    # ---------------- zones (XZ outline x Y range)
    eb = prism(G.rounded_rect(X_EBR + 0.2, X_EBF - H + 0.6, -60.0, 60.0, 0.0), EB_Y[0], EB_Y[1], "XZ")
    body_xz = SG.polygon_from([(X_EBF - H, 20.0), (500.0, 20.0), (500.0, Z_BODY_BOT), (409.2, -50.7),
                               (341.4, -50.8), (323.4, -48.7), (289.3, -43.4), (272.2, -32.8), (X_EBF - H, -30.0)])
    body = prism(body_xz, SG.Y_R, SG.Y_L, "XZ")
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
    g_out = SG.part_ring("trigger_guard", 0.45)
    guard = prism(g_out, -TG["bar_width_Y"] / 2.0, TG["bar_width_Y"] / 2.0, "XZ")
    # the web where the guard's rear bar runs into the grip's front strap (the master outline fills it; the grip's
    # rounded sections stop at the strap): guard-bar wide, from 3 mm inside the strap, clipped by the master outline
    # and the guard opening
    web = box(336.0, 356.0, -TG["bar_width_Y"] / 2.0, TG["bar_width_Y"] / 2.0, -84.0, Z_BODY_BOT + 1.0)
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
        if X_EBF - H - 0.8 < mid[0] < X_EBF and mid[2] > seam_z - 1.2:
            return 0.0                                           # the end block's front seam
        if mid[2] > Z_TOP - 0.8 and mid[0] > X_RAIL0 - 1.0:
            return 0.0                                           # under the rail
        return 1.0

    x_run = float(SEAM[1, 0]) - 0.5

    def seam_break(mid, d, n1, n2, dih, convex):
        if not convex or not (60.0 <= dih <= 120.0):
            return 0.0
        return 1.0 if (abs(mid[2] - seam_z) < 0.6 and X_EBF - H - 1.0 < mid[0] < x_run) or \
            (X_EBF - H - 0.8 < mid[0] < X_EBF and mid[2] > seam_z) else 0.0

    def flare_chamfer(mid, d, n1, n2, dih, convex):
        if not convex or not (60.0 <= dih <= 120.0):
            return 0.0
        if abs(abs(mid[1]) - MW_LIP) < 0.1 and abs(mid[2] - (zl(mid[0]) + fh)) < 0.6:
            return 1.0
        return 0.0

    # ---------------- cuts
    cuts = []
    # the guard opening (the trace guard's own hole: the opening incl. the trigger's area)
    # the guard opening as the master outline draws it (the guard part's own hole when the master has none there)
    gh = [hr for hr in SG.master_holes(0.25) if 330.0 < hr[:, 0].min() and hr[:, 0].max() < 410.0
          and hr[:, 1].max() < -40.0] or SG.part_holes("trigger_guard", 0.4)
    for hr in gh:
        cuts.append(prism(G.ccw(hr), -20.0, 20.0, "XZ"))
    # the opening's traced hole wraps round the DRAWN trigger blade: the blade's own region (traced ring + 0.6) is cut
    # too, from below up to 0.3 over the opening's top there (a 0.3 relief in the housing band's underside round the
    # blade; level with the top it left a coplanar seam, under it a 0.2 lip; W1b fix round: the drawn blade minus the
    # built blade's 0.3 sweep left ragged polymer slivers beside the trigger)
    tr_ = G.offset(G.ccw(SG.part_ring("trigger", 0.2)), 0.6)
    near_t = np.vstack([h[(h[:, 0] > tr_[:, 0].min() - 3.0) & (h[:, 0] < tr_[:, 0].max() + 3.0)] for h in gh])
    zt_ = float(near_t[:, 1].max()) + 0.3 if len(near_t) else Z_BODY_BOT - 1.2
    tcut = G.clip_y(tr_, -200.0, zt_)
    if len(tcut) >= 3:
        cuts.append(prism(G.ccw(tcut), -20.0, 20.0, "XZ"))
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
                          [wall_line_x(cw["Z"][0]) + 0.3, cw["Z"][0]], [xl - 3.6, cw["Z"][0]]])
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
    # the lower rail's rear end tucks into the magwell's front face (a pocket, 0.3 clearance)
    lr0 = float(sbox("lower_rail")["X"][0])
    cuts.append(box(lr0 - 0.3, lr0 + 9.0, -10.9, 10.9, float(dims("lower_rail")["bottom_Z"]) - 0.5,
                    float(dims("lower_rail")["top_seam_Z"]) + 0.2))
    # oblong recess (LEFT only, 0.8 deep, R 0.3 rim)
    orc = feature("lower_receiver", "oblong_recess")
    cuts.append(prism(stadium_xz(orc["X"][0], orc["X"][1], 0.5 * sum(orc["Z"]), orc["Z"][1] - orc["Z"][0]),
                      SG.Y_L - 0.8, SG.Y_L + 1.0, "XZ"))
    # flush pin holes
    for name, side, xz, d in pin_holes("lower"):
        yf = face_y(side, xz[0], xz[1])
        cuts.append(HW.place(HW.pin_hole_cutter(d, 2.6, 0.15), (xz[0], yf, xz[1]), (0, side, 0)))
    sbp = [q for q in dims("pins_fasteners")["list"] if q["name"] == "seam boss pin"][0]
    sbf = feature("lower_receiver", "seam_boss")
    cuts.append(HW.place(HW.pin_hole_cutter(sbp["dia"], 2.6, 0.15), (sbp["XZ"][0], SG.Y_L + float(sbf["proud"]),
                                                                      sbp["XZ"][1]), (0, 1.0, 0)))
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
    seats = [pcyl((sp[0], s * (abs(face_y(s, sp[0], sp[1])) - 0.6), sp[1]),
                      (sp[0], s * (abs(face_y(s, sp[0], sp[1])) + float(SE["seat_boss_proud"])), sp[1]),
                      float(LO_feature("selector_seats")["dia"]) / 2.0, 64) for s in (1.0, -1.0)]
    sb = feature("lower_receiver", "seam_boss")
    seam_boss = pcyl((sb["XZ"][0], SG.Y_L - 3.6, sb["XZ"][1]), (sb["XZ"][0], SG.Y_L + float(sb["proud"]),
                                                                      sb["XZ"][1]), sb["dia"] / 2.0, 64)
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

    faces = [SG.Y_L, SG.Y_R, MW_BODY, -MW_BODY, MW_LIP, -MW_LIP, TG["bar_width_Y"] / 2.0, -TG["bar_width_Y"] / 2.0,
             EB_Y[0], EB_Y[1], GRIP_W / 2.0 - step, -(GRIP_W / 2.0 - step)]

    def lip_break(mid, d, n1, n2, dih, convex):
        if not convex or not (60.0 <= dih <= 120.0):
            return 0.0
        if 318.0 < mid[0] < 412.0 and mid[2] < -44.0 and abs(mid[1]) < 7.0:
            return 0.0              # the guard bar, trigger slot and clevis: edges closer than the break's width
        return 1.0 if any(abs(mid[1] - f) < 0.06 for f in faces) and mid[2] < seam_z - 0.8 else 0.0

    base = body
    gl, _ = grip_loft()
    ops = [("union", [eb, mw_body, band, guard, web] + ears),
           ("intersect", [master_prism()]), ("intersect", [prism(region_lower(), -60.0, 60.0, "XZ")]),
           ("union", [gl]),
           ("bevel_wc", (1.8, 1, flare_chamfer)),
           ("bevel_wc", (1.4, 2, outer_round)), ("bevel_wc", (0.4, 1, seam_break)),
           ("union", seats + [seam_boss] + kn["fixed"] + [lug_box]),
           ("diff", cuts + lug_cuts + knuckle_bores),
           ("bevel_wc", (0.35, 1, lip_break))]
    return Ops("lower_receiver", base, ops, bone="body", cls="P-round", slot=FURN, spec_id="lower_receiver",
               joint={"type": "seam", "parent": "upper_receiver", "gap_mm": [0.3, 0.5], "depth_mm": 0.6})


def LO_feature(name):
    return feature("lower_receiver", name)


def build_all():
    return [lower_receiver(), grip_cover()]
