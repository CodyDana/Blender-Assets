"""Stage 2 form, continued: sights, fore-end, barrel group, front sight, brake, trigger group, furniture, butt,
selector and the magazine block-in (frame M, mm). See rifle_parts.py for the rules."""
from __future__ import annotations

import json
import math

import numpy as np

from rifle_common import SPEC, TRACE
from gunlib import geo2d as G
from gunlib import mesh as MS
from gunlib.mesh import Mesh
from gunlib.parts import PartDef
import rifle_parts as RP
from rifle_parts import GAP, WO, COVER_O, ledge_z, prof

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


# ======================================================================================== rear sight
LEAF_PIVOT = (504.0, 41.0)
KNUCKLE_R = 5.6


def rear_sight_block() -> PartDef:
    """Full-width block (43.5) on the front trunnion: low rear part under the leaf with the traced see-through
    sliver, tall front part (to Z 44.6) carrying the retainer lever on its side; a channel (Y +-6.2) holds the leaf,
    whose knuckle sits in a cylindrical seat round the hinge."""
    # the see-through gap under the leaf follows the trace's hole ring (LEFT_outline parts.rear_sight, the negative
    # ring) point for point: a 2 mm slit Z 38.7-40.9 from X 465.8 to the hinge block at X 487.5, with the narrow
    # (~1.3 mm) slanted slot the trace shows dropping from it to (472.5, 34.8). Form fix round 1: the round-0 wedge
    # down to Z 34.9 left 15 traced-solid px open
    body = [(454.92, 10.60), (485.28, 10.60), (485.28, 13.12), (523.98, 13.12), (523.98, 34.3), (523.0, 34.3),
            (523.0, 41.6), (518.7, 43.6), (516.3, 44.6), (497.5, 44.6), (487.5, 44.2), (487.5, 40.4),
            (481.0, 39.7), (477.3, 37.4), (476.1, 37.7), (474.9, 36.1), (472.5, 34.8), (471.9, 35.5),
            (474.3, 38.0), (473.7, 38.7), (466.4, 38.7), (465.8, 39.2),
            (465.8, 40.3), (452.4, 40.3), (452.4, 37.6), (454.92, 34.4)]
    sol = [MS.prism(body, -COVER_O, COVER_O)]
    cut = [MS.box(486.0, 509.5, -6.2, 6.2, 40.4, 50.0),                                   # leaf channel
           ycyl(LEAF_PIVOT[0], LEAF_PIVOT[1], KNUCKLE_R + 0.2, -6.2, 6.2, 40),             # hinge seat
           MS.box(456.5, 467.0, -7.2, 7.2, 39.0, 50.0)]                                    # slider clearance
    cut.append(xcyl(0.0, TUBE_Z, TUBE_R + GAP, 519.0, 530.0, 32))                         # gas-tube rear recess
    return PartDef("rear_sight_block", sol, cutters=cut, cls="M-chamfer")


def rear_sight_leaf() -> PartDef:
    px, pz = LEAF_PIVOT
    zb, zt = 40.6, 44.4                         # leaf bottom / top at rest
    leaf = MS.box(450.9, px, -6.0, 6.0, zb, zt)
    strip = MS.box(452.0, px - 6.0, -2.4, 2.4, zt - 0.1, zt + 0.6)            # raised centre strip
    knuckle = ycyl(px, pz, KNUCKLE_R, -6.0, 6.0, 40)
    # notch plate: tall transverse plate at the rear end with a square-bottomed U notch (2.0 x 2.5, bottom 45.5)
    plate = MS.box(448.7, 451.0, -6.0, 6.0, zb - 0.2, 48.0)
    notch = MS.box(447.0, 452.5, -1.0, 1.0, 45.5, 50.0)
    # slider riding on the leaf (wraps it; 0.02 gap)
    slider_o = G.rounded_rect(457.5, 465.5, zb - 1.0, 48.5, 0.8, 2)
    slider = MS.prism(slider_o, -7.0, 7.0)
    slider_cut = MS.box(457.0, 466.0, -6.15, 6.15, zb - 0.15, zt + 0.75)     # adjustable: sliding row
    return PartDef("rear_sight_leaf", [leaf], unions=[strip, knuckle, plate], cutters=[notch], bone="sight_rear",
                   cls="M-chamfer", recipe=[(0.3, 1, 30.0)],
                   joint={"type": "hinge", "parent": "rear_sight_block", "pivot_M": [px, 0.0, pz],
                          "axis_M": [0, 1, 0], "range_deg": [0.0, 6.0], "clearance_mm": [0.1, 0.3]}) , \
        PartDef("rear_sight_slider", [slider], cutters=[slider_cut], bone="sight_rear", cls="M-chamfer",
                recipe=[(0.25, 1, 30.0)], spec_id="rear_sight_leaf",
                joint={"type": "sliding", "parent": "rear_sight_leaf", "clearance_mm": [0.15, 0.4],
                       "note": "range adjuster; no bone (static in the clips)"})


def retainer() -> PartDef:
    yb = -COVER_O - GAP
    boss_c, end_c = (516.5, 41.0), (500.0, 24.0)   # read off a 10x zoom of the LEFT panel
    d = np.subtract(end_c, boss_c)
    L = float(np.hypot(*d))
    a = math.degrees(math.atan2(d[1], d[0]))
    # arm outline: stadium from boss to end, 6 mm wide at the boss tapering to 5.2
    t = np.linspace(-90, 90, 13)
    end_arc = G.arc(L, 0, 3.0, -90, 90, 13)
    boss_arc = G.arc(0, 0, 3.4, 90, 270, 13)
    arm = G.rot(np.vstack([end_arc, boss_arc]), a, (0, 0)) + boss_c
    sol = [MS.prism(arm, yb - 2.0, yb)]
    uni = [ycyl(boss_c[0], boss_c[1], 3.4, yb - 2.9, yb, 32)]
    cut = [ycyl(end_c[0], end_c[1], 1.0, yb - 4, yb + 1, 16)]
    left = ycyl(boss_c[0], boss_c[1], 3.4, COVER_O + GAP, COVER_O + GAP + 1.8, 32)
    return PartDef("handguard_retainer", sol + [left], unions=uni, cutters=cut, cls="S-cut",
                   recipe=[(0.3, 1, 30.0)], spec_id="handguard_retainer_lever")


# ======================================================================================== fore-end
def upper_hg_section(zt, half_w=15.5, zb=13.12, n=28):
    zc = zt - half_w
    a = np.linspace(0, math.pi, n)
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
    xs = np.r_[np.linspace(535.02, 637.8, 13), 639.5, 640.88]
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
                   recipe=[(1.0, 2, 30.0)], joint={"type": "butt", "parent": "gas_tube", "gap_mm": [0.01, 0.05]})


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
    xs = np.r_[np.linspace(485.32, 512.0, 6), np.linspace(516.0, 636.7, 7), 639.5, 640.88]
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
                   recipe=[(1.2, 2, 30.0)], joint={"type": "butt", "parent": "receiver", "gap_mm": [0.01, 0.05]})


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
           MS.revolve([(0.0, 3.81 + 0.6), (0.6, 3.81), (0.61, 0.0)], (848.78 + 0.001, 0, 0), (-1, 0, 0), 32),
           xcyl(0.0, 0.0, 5.6, 433.0, 446.0, 32), xcyl(0.0, 0.0, 3.81, 440.0, 460.0, 32)]       # chamber
    return PartDef("barrel", [b], cutters=cut, cls="M-chamfer", recipe=[(0.4, 1, 30.0)])


def cleaning_rod() -> PartDef:
    r = xcyl(0.0, ROD_Z, ROD_R, 641.0, 806.8, 16)
    head = MS.box(806.8 - 0.4, 811.98, -2.6, 2.6, ROD_Z - 2.8, ROD_Z + 2.4)
    return PartDef("cleaning_rod", [r], unions=[head], cls="M-round", recipe=[(0.4, 2, 30.0)])


# ======================================================================================== front sight + brake
EAR_IN, EAR_OUT = 8.2, 10.7


def front_sight_block() -> PartDef:
    base = [(806.1, -7.9), (809.7, -9.1), (810.3, -14.0), (813.0, -15.8), (830.0, -15.8), (832.4, -14.5),
            (836.0, -14.3), (837.8, -12.7), (837.8, -9.6), (839.9, -8.7), (839.9, 8.7), (837.2, 11.1),
            (806.1, 11.1)]
    collar_r = 11.0
    side = MS.prism(base, -collar_r, collar_r)
    sec = G.ccw(np.vstack([G.arc(0, 0, collar_r, -60, 240, 31), [[-5.0, -18.0], [5.0, -18.0]]]))
    front_collar = xcyl(0.0, 0.0, 8.7, 839.85, 842.8, 32)
    front_collar2 = xcyl(0.0, 0.0, 10.1, 842.6, 848.78, 32)
    # ears run down into the round collar (c3: they rise straight from it). Round 0 stopped them at Z 9.0 and kept
    # a full-width 0.2 mm slab at Z 10.9-11.1, which showed as thin fins beside the collar in the early crop
    # (form fix round 1: ears from Z 2.0, slab removed)
    ear_o = [(807.6, 2.0), (807.6, 9.0), (818.2, 45.5), (819.0, 49.4), (832.2, 49.4), (833.0, 47.0), (833.0, 2.0)]
    ear_o = G.fillet(G.ccw(np.array(ear_o, float)), 1.6, 3)
    ears = [MS.prism(ear_o, EAR_IN, EAR_OUT), MS.prism(ear_o, -EAR_OUT, -EAR_IN)]
    # boss rings (raised 0.4) round the hole on each ear's outer face
    boss = [ycyl(824.7, 29.9, 3.0, EAR_OUT - 0.1, EAR_OUT + 0.4, 20), ycyl(824.7, 29.9, 3.0, -EAR_OUT - 0.4, -EAR_OUT + 0.1, 20)]
    plunger = MS.cylinder((840.7, 0, 7.0), (840.7, 0, 9.55), 1.1, 16)
    # cross pin: round heads proud 0.8 on the collar sides (c3); the TOP's 37 mm wide item at X ~800 does not
    # agree with c3 or the side view and is not modelled
    pin = ycyl(826.0, -5.0, 2.2, -11.8, 11.8, 20)
    p = PartDef("front_sight_block", [side], unions=[front_collar, front_collar2] + ears + boss + [plunger, pin],
                cls="M-chamfer-front", recipe=[(0.6, 1, 30.0)], spec_id="front_sight_block")
    p.section_intersect_pre = [xprism(sec, 800.0, 840.0), MS.box(839.0, 850.0, -40, 40, -40, 60),
                               MS.box(800.0, 850.0, -40, 40, 11.2, 60)]
    win = G.ccw(np.array([(813.7, 11.8), (827.2, 11.8), (827.2, 21.6), (818.6, 21.6)], float))
    win = G.fillet(win, 1.2, 3)
    p.cutters = [xcyl(0.0, 0.0, BORE_R + GAP, 800.0, 850.0, 48),
                 MS.prism(win, -12.0, 12.0),
                 ycyl(824.7, 29.9, 1.75, -12.0, 12.0, 16),
                 MS.box(806.38, 812.0, -2.6 - GAP, 2.6 + GAP, ROD_Z - 2.8 - GAP, ROD_Z + 2.4 + GAP),    # rod head seat
                 xcyl(0.0, ROD_Z, ROD_R + GAP, 800.0, 812.5, 16)]
    return p


def front_sight_post() -> PartDef:
    drum = ycyl(825.3, 31.0, 4.0, -EAR_IN + GAP, EAR_IN - GAP, 32)
    post = MS.cylinder((825.3, 0, 34.0), (825.3, 0, 45.0), 1.0, 16)
    return PartDef("front_sight_post", [drum], unions=[post], cls="M-round", recipe=[(0.3, 2, 30.0)],
                   spec_id="front_sight_ears_post")


def muzzle_brake() -> PartDef:
    r = 10.1
    x0, x1 = 848.82, 880.0
    body = xcyl(0.0, 0.0, r, x0, 880.0, 40)
    # slant cut: plane through (862.1, +r) toward the bottom lip, 40.8 deg from vertical
    a = math.radians(40.8)
    dvec = np.array([math.sin(a), -math.cos(a)])
    p0 = np.array([873.0, 0.0]) - dvec * (12.0 / math.cos(a))     # traced slant: X 873.0 at Z 0 (LS fit)
    far = p0 + dvec * 40
    cutp = [p0 - dvec * 5, far, far + np.array([30, 0]), (p0 - dvec * 5) + np.array([30, 30])]
    cut = [MS.prism(np.array(cutp), -15.0, 15.0),
           xcyl(0.0, 0.0, 7.0, 852.0, 890.0, 48),               # expansion chamber (thin worn rim at the cut)
           xcyl(0.0, 0.0, 4.1, 846.0, 853.0, 32),                # bullet hole through the rear wall
           MS.prism(G.rounded_rect(860.5, 869.5, -3.2, 3.2, 3.1, 4), -14.0, -5.0)]   # side scallop, right side (c3)
    return PartDef("muzzle_brake", [body], cutters=cut, bone="muzzle_device", cls="M-chamfer-front",
                   recipe=[(0.7, 2, 30.0)], joint={"type": "fixed", "parent": "barrel"})


# ======================================================================================== trigger group
TRIG_PIVOT = (318.0, -20.0)
CATCH_PIVOT = (362.0, -50.0)


def trigger() -> PartDef:
    P = prof("trigger", 0.4)
    blade = MS.prism(P, -3.0, 3.0)
    stem = [(313.6, -35.2), (321.2, -35.2), (320.6, -21.0), (315.4, -21.0)]
    uni = [MS.prism(stem, -3.0, 3.0), ycyl(TRIG_PIVOT[0], TRIG_PIVOT[1], 3.0, -3.0, 3.0, 24)]
    cut = [ycyl(TRIG_PIVOT[0], TRIG_PIVOT[1], 1.2, -4, 4, 16)]
    return PartDef("trigger", [blade], unions=uni, cutters=cut, bone="trigger", cls="C-fillet",
                   recipe=[(0.6, 2, 30.0)],
                   joint={"type": "hinge", "parent": "receiver", "pivot_M": [TRIG_PIVOT[0], 0, TRIG_PIVOT[1]],
                          "axis_M": [0, 1, 0], "range_deg": [0.0, 12.0], "clearance_mm": [0.1, 0.3]})


def trigger_guard() -> PartDef:
    P = prof("trigger_guard", 0.55)
    # the loop's top points (Z -34.96..-34.6) straddled the flange bottom plane Z -34.8, leaving a 0.16 mm sliver
    # that the 0.6 mm bevel collapsed (non-manifold after finish() once the build frame moved): lift them into the
    # flange (the joint is hidden inside the flange)
    P = P.copy()
    P[P[:, 1] > -35.0, 1] = -34.7
    loop = MS.prism(P, -5.0, 5.0)
    xs = np.array([252.0, 255.0, 300.0, 360.0, 367.9])
    top = [(x, ledge_z(x) - GAP) for x in xs]
    flange = MS.prism([(252.0, -34.8), (367.9, -34.8)] + top[::-1], -WO, WO)
    # catch housing cheeks either side of the catch tongue + the catch pin with heads
    cheek_o = [(354.8, -34.82), (367.6, -34.82), (367.6, -46.5), (365.6, -51.5), (354.8, -51.5)]
    # cheeks 0.02 inside the loop faces (Y 5.0): coplanar faces left sub-micron bevel vertices that finish() merged
    uni = [flange, MS.prism(cheek_o, 3.75, 4.98), MS.prism(cheek_o, -4.98, -3.75),
           ycyl(CATCH_PIVOT[0], CATCH_PIVOT[1], 1.5, -5.6, 5.6, 20),
           ycyl(CATCH_PIVOT[0], CATCH_PIVOT[1], 2.2, 4.99, 5.6, 24), ycyl(CATCH_PIVOT[0], CATCH_PIVOT[1], 2.2, -5.6, -4.99, 24)]
    cut = [MS.box(301.5, 329.0, -3.25, 3.25, -40.0, -27.0),                 # trigger slot through the flange
           MS.box(352.0, 355.6, -3.75, 3.75, -34.9, -51.6)]                 # catch tongue relief in the front leg
    return PartDef("trigger_guard", [loop], unions=uni, cutters=cut, cls="S-bend",
                   recipe=[(0.6, 2, 40.0)])


def mag_catch() -> PartDef:
    P = prof("mag_catch", 0.4)
    P = G.clip_x(G.clip_y(P, None, -34.9), 355.45, 368.3)
    cx, cz = CATCH_PIVOT
    tongue = MS.prism(G.clip_y(P, -54.0, None), -3.5, 3.5)
    paddle = MS.prism(G.clip_y(P, None, -54.0), -5.0, 5.0)
    # top cut to an arc about the pivot (r 15.0): rotation-invariant clearance under the flange
    r = 15.0
    arch = np.vstack([[[cx + r, cz], [cx + 40, cz], [cx + 40, cz + 40], [cx - 40, cz + 40], [cx - r, cz]],
                      G.arc(cx, cz, r, 180, 0, 49)[1:-1]])
    cut = [MS.prism(G.ccw(arch), -6.0, 6.0), ycyl(cx, cz, 1.5 + 0.2, -6, 6, 20)]
    return PartDef("mag_catch", [tongue], unions=[paddle], cutters=cut, bone="mag_release", cls="S-cut",
                   recipe=[(0.3, 1, 30.0)],
                   joint={"type": "hinge", "parent": "receiver", "pivot_M": [cx, 0, cz], "axis_M": [0, -1, 0],
                          "range_deg": [0.0, 10.0], "direction": "+ = top rearward (release)",
                          "clearance_mm": [0.1, 0.3]})


# ======================================================================================== furniture
def grip_outline():
    P = G.clean_smooth(SPEC.profile("pistol_grip"), 1.4, 1.8, 35.0)
    top = P[:, 1] > -37.6
    P[top & (P[:, 0] > 244.0) & (P[:, 0] < 301.5), 1] = -34.82
    zb = SPEC.key["grip"]["bottom_Z"]
    P[:, 1] = -34.82 + (P[:, 1] + 34.82) * ((zb + 34.82) / (P[:, 1].min() + 34.82))
    P = G.dedupe(P, 0.05)
    return P


# ---- pistol grip (form fix round 1): a LOFT of rounded sections, not a slab with edge bevels.
# The slab (flat +-15 sides, 7.5 mm weighted bevel) clamped to almost nothing on the dense traced outline: girth
# 141 mm and a slab look in the 3/4 view. The spec's section is "a rounded oblong (30 wide), flatter sides where the
# checkering sits, straps R 8-10"; the side outline stays the trace. Construction:
#   rings   horizontal sections at Z levels (the top is the horizontal flange joint); each ring is the
#           perpendicular section (rounded rectangle D x W, strap radius R, sides crowned C1-smoothly by `crown`)
#           stretched along X onto the outline's back..front interval at that Z (D = interval * cos(rake));
#   bottom  the rings run on past the heel / toe and the traced bottom chain is cut with a boolean (flat end),
#           then the bottom edges get a 1.0 mm round (2 seg) and the flange edge a 0.5 mm break;
#   panels  checkered panel border = real geometry: a 0.6 mm recess that follows the rounded side (panel prism
#           minus the loft shrunk 0.6 in Y), border bevel 0.3; the diamonds go in the normal map.
GRIP_RAKE = 22.35          # axis rake from vertical (spec)
GRIP_W = float(SPEC.dims("pistol_grip")["width_Y"])   # section width Y (spec; real AK grips 30-36 mm, rifle_h1)
GRIP_R = 10.0              # strap radius in the perpendicular section (spec "straps R 8-10"; 3/4-view sweep)
GRIP_CROWN = 0.5           # side crown at mid-depth (flatter sides where the checkering sits)
GRIP_NR = 30               # vertices per ring
GRIP_Z_TOP = -34.82
GRIP_Z_BACK_CUT = -117.21  # heel: lowest Z with an exact back point (the outline's most rearward heel point)
GRIP_Z_FRONT_CUT = -128.6  # toe: lowest Z with an exact front point (just below the toe flare's front max)
GRIP_Z_END = -137.0


def _hits_x(P, z):
    Q = np.vstack([P, P[:1]])
    xs = []
    for a, b in zip(Q[:-1], Q[1:]):
        if (a[1] - z) * (b[1] - z) <= 0 and a[1] != b[1]:
            t = (z - a[1]) / (b[1] - a[1])
            xs.append(a[0] + t * (b[0] - a[0]))
    return (min(xs), max(xs)) if len(xs) >= 2 else None


def grip_section(D, W=GRIP_W, R=GRIP_R, crown=GRIP_CROWN, n=GRIP_NR):
    """Perpendicular section, s = 0 at the back strap .. D at the front strap, y across. Starts at the back strap
    middle (s 0, y 0) and runs CCW in (s, y); n points by arc length (consistent rings for the loft)."""
    R = min(R, 0.5 * W - 1e-3, 0.5 * D - 1e-3)
    h = 0.5 * W - crown
    rr = G.ccw(G.rounded_rect(0.0, D, -h, h, R, 24))
    rr = G.resample(rr, 0.15)
    # crown the flat side runs (C1: zero value and slope where the strap arcs begin)
    u = (rr[:, 0] - 0.5 * D) / max(0.5 * D - R, 1e-6)
    flat = (np.abs(u) < 1.0) & (np.abs(rr[:, 1]) > h - 1e-6)
    rr[flat, 1] += np.sign(rr[flat, 1]) * crown * (1 - u[flat] ** 2) ** 2
    k = int(np.argmin(rr[:, 0] + 10 * np.abs(rr[:, 1])))          # back strap middle
    rr = np.roll(rr, -k, axis=0)
    Q = np.vstack([rr, rr[:1]])
    dd = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Q, axis=0), axis=1))]
    t = np.linspace(0, dd[-1], n, endpoint=False)
    return np.c_[np.interp(t, dd, Q[:, 0]), np.interp(t, dd, Q[:, 1])]


def grip_levels(P):
    """Z levels for the rings: dense where the outline's back or front moves > 1.2 mm, at most 5 mm apart."""
    zs = np.arange(GRIP_Z_TOP - 0.5, GRIP_Z_BACK_CUT + 0.2, -0.25)
    keep = [GRIP_Z_TOP]
    last = _hits_x(P, GRIP_Z_TOP - 1e-3)
    for z in zs:
        h = _hits_x(P, z)
        if h is None:
            continue
        if max(abs(h[0] - last[0]), abs(h[1] - last[1])) > 1.2 or keep[-1] - z >= 5.0:
            keep.append(float(z))
            last = h
    keep.append(GRIP_Z_BACK_CUT)
    keep += [-119.5, -122.0, -124.5, -126.5, -127.8, GRIP_Z_FRONT_CUT, -131.0, -134.0, GRIP_Z_END]
    return np.array(keep)


def grip_intervals(P):
    """(z, x_back, x_front) per ring: exact outline hits down to the heel / toe cut levels, then carried on just
    outside the outline (0.6 mm) so the bottom boolean, not the loft, makes the traced bottom."""
    out = []
    xb_heel = _hits_x(P, GRIP_Z_BACK_CUT)[0]
    xf_toe = _hits_x(P, GRIP_Z_FRONT_CUT)[1]
    for z in grip_levels(P):
        h = _hits_x(P, min(z, GRIP_Z_TOP - 1e-3))
        xb = h[0] if (h is not None and z >= GRIP_Z_BACK_CUT) else xb_heel - 0.6
        xf = h[1] if (h is not None and z >= GRIP_Z_FRONT_CUT) else xf_toe + 0.6
        out.append((float(z), float(xb), float(xf)))
    return out


def grip_rings(W=GRIP_W, R=GRIP_R, crown=GRIP_CROWN, n=GRIP_NR, dy=0.0, dr=0.0):
    """Rings in frame M. dy / dr shrink the half width / strap radius (the panel-recess inner loft)."""
    P = grip_outline()
    c = math.cos(math.radians(GRIP_RAKE))
    rings = []
    for z, xb, xf in grip_intervals(P):
        D = (xf - xb) * c
        sec = grip_section(D, W - 2 * dy, R - dr, crown, n)
        x = xb + sec[:, 0] / D * (xf - xb)
        rings.append(np.c_[x, sec[:, 1], np.full(n, z)])
    return rings


def grip_bottom_cutter():
    """XZ polygon below the traced bottom chain, from the heel cut level round the toe to the front cut level."""
    P = G.ccw(grip_outline())
    b = np.array([_hits_x(P, GRIP_Z_BACK_CUT)[0], GRIP_Z_BACK_CUT])
    f = np.array([_hits_x(P, GRIP_Z_FRONT_CUT)[1], GRIP_Z_FRONT_CUT])
    # CCW (Z up) runs back strap -> heel -> bottom -> toe -> front strap: walk from the vertex after b to before f
    k0 = int(np.argmin(np.hypot(*(P - b).T)))
    k1 = int(np.argmin(np.hypot(*(P - f).T)))
    idx = [(k0 + i) % len(P) for i in range(((k1 - k0) % len(P)) + 1)]
    chain = P[idx]
    chain = chain[(chain[:, 1] < GRIP_Z_BACK_CUT - 1e-6) & (chain[:, 1] < GRIP_Z_FRONT_CUT - 1e-6)
                  | ((chain[:, 0] < 255.0) & (chain[:, 1] < GRIP_Z_BACK_CUT - 1e-6))]
    chain = chain[(np.hypot(*(chain - b).T) > 0.05) & (np.hypot(*(chain - f).T) > 0.05)]
    poly = np.vstack([[b + (-15.0, 0.0)], [b], chain, [f], [f + (15.0, 0.0)],
                      [(f[0] + 15.0, -160.0)], [(b[0] - 15.0, -160.0)]])
    return G.dedupe(poly, 1e-4)


def grip_panel_outline():
    """Checkered panel (per side), axis-aligned rounded rectangle down the grip from the junction (c1 / c6)."""
    ang = math.radians(GRIP_RAKE)
    d = np.array([-math.sin(ang), -math.cos(ang)])        # down the grip axis
    pdir = np.array([math.cos(ang), -math.sin(ang)])      # toward the front strap
    j = np.array([280.67, -36.0])
    rr = G.rounded_rect(26.0, 91.7, -1.5, 14.4, 3.0, 4)
    return np.array([j + t * d + s * pdir for t, s in rr])


GRIP_LEG = [(298.6, -34.0), (303.3, -34.0), (303.3, -60.0), (298.4, -60.0)]   # guard rear leg (cut back 0.02)


def grip_mesh_numpy(W=GRIP_W, R=GRIP_R, crown=GRIP_CROWN):
    """Plain-numpy approximation for silhouette sweeps: the loft with vertices outside the traced bottom moved onto
    it (the Blender build cuts it with a boolean instead)."""
    m = MS.loft(grip_rings(W, R, crown))
    V = m.verts()
    cut = grip_bottom_cutter()
    inside = np.array([G.point_in_poly((v[0], v[2]), cut) for v in V])
    P = grip_outline()
    chain = P[P[:, 1] < -110.0]
    for i in np.nonzero(inside)[0]:
        d = np.hypot(chain[:, 0] - V[i, 0], chain[:, 1] - V[i, 2])
        k = int(np.argmin(d))
        V[i, 0], V[i, 2] = chain[k]
    out = MS.Mesh()
    out.add_verts(V)
    out.F = list(m.F)
    return out


def pred_grip_ends(mid, d, n1, n2, dih):
    if dih < 25:
        return 0.0
    if mid[2] < GRIP_Z_BACK_CUT + 1.0 or (mid[2] < GRIP_Z_FRONT_CUT + 1.0 and mid[0] > 262.0):
        return 1.0                                   # bottom end: 1.0 mm round
    if mid[2] > GRIP_Z_TOP - 0.3:
        return 0.5                                   # flange joint: 0.5 mm break
    return 0.0


def build_pistol_grip(coll, offset):
    import bpy
    from gunlib import bl
    ob = MS.loft(grip_rings()).to_object("pistol_grip", coll, offset, smooth_deg=35.0)
    bl.boolean_many(ob, [MS.prism(grip_bottom_cutter(), -40.0, 40.0),
                         MS.prism(G.offset(G.ccw(np.array(GRIP_LEG)), GAP), -40, 40)], "DIFFERENCE", offset=offset)
    bl.clean(ob)
    bl.bevel_weighted(ob, 1.0, 2, pred_grip_ends, offset)
    # panel recess: panel prisms minus the loft shrunk 0.6 in Y (the recess follows the rounded side)
    panel = grip_panel_outline()
    cut = MS.prism(panel, -25.0, -8.0).to_object("_gpanel", coll, offset)
    bl.boolean(cut, MS.prism(panel, 8.0, 25.0), "UNION", offset=offset)
    inner = MS.loft(grip_rings(dy=0.6, dr=0.6)).to_object("_ginner", coll, offset)
    bl.boolean(cut, inner, "DIFFERENCE")
    bpy.data.objects.remove(inner, do_unlink=True)
    bl.boolean(ob, cut, "DIFFERENCE")
    bpy.data.objects.remove(cut, do_unlink=True)
    bl.clean(ob)
    bl.bevel(ob, 0.3, 1, 50.0)
    bl.finish(ob)
    bl.weighted_normals(ob)
    ob["gun_part"] = json.dumps({"bone": "body", "class": "W-round", "slot": "M_AR01_Furniture",
                                 "spec_id": "pistol_grip", "joint": {"type": "butt", "parent": "receiver",
                                                                     "gap_mm": [0.01, 0.05]},
                                 "recipe": [[1.0, 2, "weighted ends"], [0.3, 1, 50.0]],
                                 "section": {"construction": "loft of rounded sections", "width_Y": GRIP_W,
                                             "strap_R": GRIP_R, "side_crown": GRIP_CROWN}})
    return ob


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


def buttstock() -> PartDef:
    xs_all, zt_all, zb_all, w_all = stock_lines()
    xs = np.r_[np.linspace(9.0, 146.0, 16), np.linspace(148.0, 176.0, 12), np.linspace(180.0, 233.0, 9),
               [SW_FLAT_X[0] - 3.0, SW_FLAT_X[0], SW_FLAT_X[1], SW_FLAT_X[1] + 3.0]]      # swivel flat
    xs = np.unique(np.round(xs, 3))
    xs = xs[np.r_[True, np.diff(xs) > 1.0]]
    rings = []
    for x in xs:
        zt = float(np.interp(x, xs_all, zt_all))
        zb = float(np.interp(x, xs_all, zb_all))
        w = float(np.interp(x, xs_all, w_all))
        s = stock_section(x, zt, zb, w_override=w)
        s = resample_ring(s, STOCK_NR, turn_weight=8.0)
        rings.append(np.c_[np.full(STOCK_NR, x), s[:, 0], s[:, 1]])
    body = MS.loft(rings)
    trn = [(225.2, 7.0), (225.2, -17.5), (228.7, -22.0), (229.0, -28.5), (230.1, -34.0), (231.4, -36.77),
           (231.4, -45.0), (240.9, -45.0), (240.9, 12.0), (225.2, 12.0)]
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


def butt_plate_outline():
    P = G.clean_hard(SPEC.profile("butt_plate"), 0.65)
    return P


def butt_plate() -> PartDef:
    P = butt_plate_outline()
    body = MS.prism(P, -18.45, 18.45)
    # plate section: the stock's end section + 0.3 (rounded corners STOCK_R + 0.3)
    sec = G.rounded_rect(-18.45, 18.45, -110.5, 0.5, STOCK_R + 0.3, 8)
    p = PartDef("butt_plate", [body], cls="S-bend", recipe=[(1.0, 3, 30.0)])
    p.section_intersect_pre = [xprism(sec, -5.0, 35.0)]
    # counterbores for the two cross-slotted screws on the rear face (centre line)
    cut = []
    screws = []
    for z in (-10.0, -87.5):
        xf = _rear_face_x(P, z)
        nrm = np.array([-math.cos(math.radians(5.23)), 0.0, -math.sin(math.radians(5.23))])
        c = np.array([xf, 0.0, z])
        cut.append(MS.cylinder(c - nrm * 0.6, c - nrm * (-3.0), 4.25, 32))
        screws.append((c - nrm * 0.6, nrm))
    p.cutters = cut
    p.screws = screws
    return p


def _rear_face_x(P, z):
    Q = np.vstack([P, P[:1]])
    xs = []
    for a, b in zip(Q[:-1], Q[1:]):
        if (a[1] - z) * (b[1] - z) <= 0 and a[1] != b[1]:
            t = (z - a[1]) / (b[1] - a[1])
            xs.append(a[0] + t * (b[0] - a[0]))
    return min(xs)


def butt_screws() -> PartDef:
    bp = butt_plate()
    sol, cut = [], []
    rng = np.random.default_rng(11)
    for c, nrm in bp.screws:
        c = np.asarray(c, float) + nrm * 0.6               # back to the rear face point
        floor = c - nrm * 0.6
        sol.append(MS.cylinder(floor + nrm * GAP, c - nrm * 0.1, 3.5, 32))
        e1 = np.array([0.0, 1.0, 0.0])
        e2 = np.cross(nrm, e1)
        ang = math.radians(rng.uniform(0, 90))
        for k in (0.0, math.pi / 2):
            u = math.cos(ang + k) * e1 + math.sin(ang + k) * e2
            w = np.cross(nrm, u)
            b0 = c - nrm * 0.45
            P = np.array([b0 + u * 4 + w * 0.45, b0 - u * 4 + w * 0.45, b0 - u * 4 - w * 0.45, b0 + u * 4 - w * 0.45])
            m = MS.Mesh()
            ids = m.add_verts(np.vstack([P, P + nrm * 1.5]))
            m.face(ids[[3, 2, 1, 0]])
            m.face(ids[[4, 5, 6, 7]])
            for i in range(4):
                j = (i + 1) % 4
                m.face((ids[i], ids[j], ids[4 + j], ids[4 + i]))
            cut.append(m)
    return PartDef("butt_screws", sol, cutters=cut, cls="M-chamfer", recipe=[(0.25, 1, 30.0)],
                   spec_id="butt_plate", joint={"type": "butt", "parent": "butt_plate", "gap_mm": [0.01, 0.05]})


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
    circ = G.arc(0, 0, SW_WIRE_R, 0, 360, 13)[:-1]
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


# ======================================================================================== selector
SEL_PIVOT = (282.8, -7.8)


def selector() -> PartDef:
    face = np.array(SPEC.feature("selector", "face_outline_M")["XZ"], float)
    face = G.clean_hard(face, 0.4)
    y_wall = -WO
    yi, yo = y_wall - 1.25, y_wall - 3.75
    main = G.clip_x(face, None, 342.0)
    tab = G.clip_x(face, 342.0, None)
    plate = MS.prism(main, yo, yi)
    tabm = MS.prism(tab, yo, yi)
    # bend the tab outward 15 deg about a vertical axis at X 342
    V = tabm.verts()
    k = math.radians(10.0)
    dx = V[:, 0] - 342.0
    V2 = V.copy()
    V2[:, 0] = 342.0 + dx * math.cos(k)
    V2[:, 1] = V[:, 1] - dx * math.sin(k)
    tb = MS.Mesh()
    tb.add_verts(V2)
    tb.F = tabm.F
    px, pz = SEL_PIVOT
    boss = MS.revolve([(0.0, 0.0), (0.0, 6.7), (3.6, 6.7), (4.4, 5.9), (5.0, 4.2), (5.2, 2.6), (5.25, 0.0)],
                      (px, y_wall - 0.2, pz), (0, -1, 0), 32)
    shaft = ycyl(px, pz, 3.0, y_wall - 0.25, -18.0, 32)
    ridge = MS.capsule((292.0, yo + 0.1, -6.5), (338.0, yo + 0.1, -1.2), 0.75, 12, 3)
    return PartDef("selector", [plate], unions=[tb, boss, shaft, ridge], bone="selector", cls="S-cut",
                   recipe=[(0.3, 1, 30.0)],
                   joint={"type": "hinge", "parent": "receiver", "pivot_M": [px, 0, pz], "axis_M": [0, 1, 0],
                          "positions_deg": {"safe": 0.0, "auto": 16.0, "semi": 32.0}, "clearance_mm": [0.1, 0.3]})


# ======================================================================================== magazine block-in
MAG_C = np.array([604.8, 3.3])
# floor line (form fix round 1): the spec's floor-plate corners (456.2, -183.9) / (493.1, -138.9) give the line's
# direction; its offset is set so the plate's lowest point lands on the LOWEST POINT OF THE TRACED SILHOUETTE
# (LEFT_outline silhouette, read at run time: -183.224), the same outline every other overall L4 number is read from
# (ear top 49.36, grip bottom -132.72). Round 0 used the spec's magazine bottom_Z -183.4, which was read from the
# separately traced magazine ring (-183.376, the same edge 0.13 px lower); with the ear top at 49.4 that made the
# overall height 232.78 against the spec's 232.6 (= 49.4 + 183.2 from the silhouette). The spec value is amended
# to -183.2 with resolution R30 in tools/make_spec.py.
_FN = np.array([0.7728, -0.6346])
_FT = np.array([0.6341, 0.7733])
FLOOR_BEVEL_LIFT = 0.247     # the plate's 0.6 mm S-bend bevel raises its lowest corner by this (measured, round 0)


def _traced_lowest_z():
    j = json.loads((TRACE / "LEFT_outline.json").read_text())
    return min(min(p[1] for p in r["mm"]) for r in j["silhouette"])


def _floor_line():
    c0, c1 = np.array([456.2, -183.9]), np.array([493.1, -138.9])
    corner_z = c0[1] - 0.3 * _FT[1]                       # plate outer rear corner (0.3 past the floor end)
    shift = (_traced_lowest_z() - (corner_z + FLOOR_BEVEL_LIFT)) / -_FN[1]
    return c0 - shift * _FN, c1 - shift * _FN, shift


FLOOR = _floor_line()[:2]
R_F, R_R = 180.8, 239.0


def mag_outline():
    a_top, a_bot = -175.0, -128.3
    fr = G.arc(MAG_C[0], MAG_C[1], R_F, a_top, a_bot, 26)
    rr = G.arc(MAG_C[0], MAG_C[1], R_R, a_bot, a_top, 30)
    P = np.vstack([fr, rr])
    P = G.clip_y(G.ccw(P), None, -12.0)
    return P


def _arc_floor_angle(Rr):
    """Angle (deg) where the arc of radius Rr about the magazine centre meets the floor line."""
    f0, f1 = FLOOR
    best = None
    for a in np.linspace(-140.0, -115.0, 2501):
        q = MAG_C + Rr * np.array([math.cos(math.radians(a)), math.sin(math.radians(a))])
        t = np.cross(f1 - f0, q - f0)
        if best is None or abs(t) < best[1]:
            best = (a, abs(t))
    return best[0]


def magazine() -> PartDef:
    P = mag_outline()
    body = MS.prism(P, -14.0, 14.0)
    # well part: inside the liner (X 368.8-432, 0.5 clear) above the receiver bottom
    cut = [MS.box(300.0, 369.3, -20, 20, -31.2, 0.0), MS.box(431.5, 470.0, -20, 20, -31.2, 0.0)]
    # floor plate seat: the body stops 2.0 above the floor line (plate is its own part)
    fl0, fl1 = FLOOR
    nrm = np.array([0.7728, -0.6346])
    off = -2.0
    a = fl0 + nrm * off
    b = fl1 + nrm * off
    tdir = (b - a) / np.linalg.norm(b - a)
    poly = [a - tdir * 20, b + tdir * 20, b + tdir * 20 + nrm * 30, a - tdir * 20 + nrm * 30]
    cut.append(MS.prism(np.array(poly), -20, 20))
    ribs = []
    for frac in (0.17, 0.34, 0.51, 0.66):
        Rr = R_R - frac * (R_R - R_F)
        a_top = -180.0 + math.degrees(math.asin((MAG_C[1] + 38.5) / Rr))
        a_floor = _arc_floor_angle(Rr)
        a_end = a_floor - math.degrees(16.0 / Rr)
        arcp = G.arc(MAG_C[0], MAG_C[1], Rr, a_top, a_end, 18)
        for s in (-1, 1):
            path = np.c_[arcp[:, 0], np.full(len(arcp), s * 14.0), arcp[:, 1]]
            sec = G.arc(0, 0, 1.25, 0, 180, 5)
            sec = np.vstack([sec, [[-1.25, -0.3], [1.25, -0.3]]])
            ribs.append(MS.sweep_profile(path, np.c_[sec[:, 0], sec[:, 1] * 0.8] if s > 0 else
                                         np.c_[sec[:, 0], sec[:, 1] * 0.8], ups=[[0, s, 0]] * len(path)))
    return PartDef("magazine", [body], unions=ribs, cutters=cut, bone="magazine", cls="S-bend",
                   slot="M_AR01_Mag", recipe=[(1.2, 2, 50.0)], spec_id="magazine_body",
                   joint={"type": "seated_mag", "parent": "receiver", "note": "block-in (stage 6 builds it)"})


def magazine_floor() -> PartDef:
    fl0, fl1 = FLOOR
    nrm = np.array([0.7728, -0.6346])
    tdir = (fl1 - fl0) / np.linalg.norm(fl1 - fl0)
    a = fl0 - tdir * 0.0 + nrm * (-2.0 + GAP)
    b = fl1 + nrm * (-2.0 + GAP)
    poly = [a - tdir * 0.3, b + tdir * 1.2, b + tdir * 1.2 + nrm * (2.0 - GAP), a - tdir * 0.3 + nrm * (2.0 - GAP)]
    m = MS.prism(np.array(poly), -15.5, 15.5)
    return PartDef("magazine_floor_plate", [m], bone="magazine", cls="S-bend", slot="M_AR01_Mag",
                   recipe=[(0.6, 2, 30.0)], spec_id="magazine_floor_plate")
