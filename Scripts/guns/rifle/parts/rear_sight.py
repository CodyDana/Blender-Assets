"""Detail part REAR SIGHT: block on the front trunnion (incl. its rear step over the dust cover's front end),
the leaf (hinged, bone "sight_rear") with its notch blade, the range slider, and the handguard retainer lever on the
block's right side.

Owns the objects: rear_sight_block, rear_sight_leaf (+ rear_sight_slider), handguard_retainer.
Authority close-ups: c2 DUST COVER AND REAR SIGHT (TOP LEFT) and the 3/4 view. Interfaces: the dust cover's front end
at X 454.9 (receiver_right), the gas-tube rear recess (TUBE_Z / TUBE_R), the leaf pivot LEAF_PIVOT (B3 sight sweep).

Detail pass round 2 (2026-10-05). Round 1's c2 camera looked at the block's side face square on, so the leaf read
small and the block read as a slab; round 2 re-solved the c2 part camera on the rear sight's own landmarks
(rear_sight_dev.py camera) and rebuilt the forms against it. X/Z stations stay those of the side trace (L2 / L3);
everything below lives in the third dimension or inside the side silhouette:
- block: a contoured casting, not a slab. The vertical side face stops at a swooping top edge (SIDE_TOP: low over the
  rear, an S-rise into the tall front hinge housing, as c2's bright S-curves and the side panel's face edge at Z ~37
  show); above it a rounded shoulder rolls in to the narrow deck / cam walls flanking the leaf (section-intersect
  loft). The front housing (X >= 511) is full width and full height and carries the retainer's pivot pin. Two small
  screw heads on the side face (c2 shows several fasteners round the block);
- leaf: a ladder: a base plate with two raised rails standing on it, each rail with fine sawtooth serrations along
  its top (c2's bright teeth rows; the side trace's 1 mm bumps), split by a deep centre slot running nearly its whole
  length. Physical teeth only, no numerals or tick marks (no-markings rule);
- notch blade: a narrower transverse blade on top of the leaf's rear end with a square-bottomed U notch (bottom
  45.5 = spec notch_bottom_Z), rounded top corners;
- slider: the notched-looking block at the leaf's rear end in c2: as wide as the leaf plus its walls, rounded roof,
  with a side clamp / catch on each side that wraps down over the rails (c2's big near-side box);
- retainer lever: a slim stamped slotted link (c2 draws its bars as thin bright lines) from a prominent round pivot
  pin head (collar + domed head, c2's big round pin at the top front) to a lower end with a small screw head.
"""
from __future__ import annotations

import math

import numpy as np

from gunlib import geo2d as G
from gunlib import mesh as MS
from gunlib.parts import PartDef
from rifle_parts import GAP, COVER_O
from rifle_parts2 import TUBE_Z, TUBE_R, ycyl, xcyl


# ======================================================================================== rear sight
LEAF_PIVOT = (504.0, 41.0)
KNUCKLE_R = 5.6
LEAF_ZB, LEAF_ZT = 40.6, 44.4             # leaf bottom / rail top at rest (teeth stand to TOOTH_Z)
LEAF_Z2 = 42.3                            # top of the leaf's base plate; the rails stand on it
TOOTH_Z = 45.1                            # side trace: 1 mm bumps along the leaf top, Z 44.1-45.4 at X 472-491
LEAF_HW = 8.5                             # leaf half width: 17 (c2 + TOP; spec dims.leaf_width 12 -> proposal)
RAIL_HW = 8.0                             # rails' outer half width (0.5 step onto the base plate)
SLOT_HW = 2.8                             # centre slot half width (dark full-length slot in c2 / TOP)
SLOT_X = (466.8, 497.8)
CHAN_HW = LEAF_HW + 0.2                   # leaf channel / hinge seat half width (hinge row 0.1-0.3)
SLIDER_X = (457.5, 465.5)                 # spec dims.slider_X (the raised roof)
SKIRT_X0 = 452.6                          # the slider's lower rear skirt runs back to the notch blade (side trace Z 45.0 at X 450.6-455.4)
SKIRT_Z = 45.3
SKIRT_ZB = 40.8                           # skirt / catches bottom: the side trace shows background under the leaf at X 452-458.6, Z 38.6-40.7
FLOOR_X0 = 458.8                          # the slider's floor under the leaf starts here
SLIDER_HW = 10.0                          # slider body half width (wraps the leaf)
CATCH_HW = 13.4                           # side clamps / catches reach (c2's big near-side box)
SLIDER_ZB, SLIDER_ZT = LEAF_ZB - 1.0, 48.5
BAR_HW = 15.5                             # transverse rounded bar on the front housing (c2's hinge bar)
DECK_HW = 10.8                            # deck / cam walls half width above the shoulder (leaf + thin walls)
TOOTH_PITCH = 2.8
TOOTH_X = np.arange(467.4, 497.6, TOOTH_PITCH)   # sawtooth serrations (c2: 10-11 bright teeth per rail)
NOTCH_HW = 6.6                            # notch blade half width
# side face top edge (where the shoulder starts), X -> Z: low rear part, a step / S-rise at X 472-478 (the side
# panel's face edge at Z 35.6 / 37.4), then the swoop up into the full-height front housing from X ~504
SIDE_TOP = [(440.0, 34.8), (462.0, 34.8), (468.0, 34.3), (474.0, 34.0), (481.0, 34.4), (488.0, 35.3),
            (494.0, 36.4), (499.0, 37.8), (503.0, 39.4), (506.5, 41.6), (509.5, 44.4), (511.5, 60.0), (540.0, 60.0)]
SHOULDER_H = 5.6                          # shoulder rise from the side face top edge to the deck edge
FENCE_W = 2.2                             # width of the serrated strip along each rail's slot edge


def _shoulder_loft():
    """Intersect volume for the block: full width (the cover's 43.5) up to SIDE_TOP, then a rounded shoulder rolling
    in to the deck (Y +-DECK_HW), which runs up past everything. Section = elliptical quarter, 4 segments a side."""
    W = COVER_O + 0.05
    a = np.radians([0.0, 90.0])                   # a straight chamfer band: crisp edges top and bottom (c2's S-lines)

    def ring(x, zs):
        q = [(-W, 5.0), (W, 5.0)]
        q += [(DECK_HW + (W - DECK_HW) * math.cos(t), zs + SHOULDER_H * math.sin(t)) for t in a]
        q += [(DECK_HW, 75.0), (-DECK_HW, 75.0)]
        q += [(-DECK_HW - (W - DECK_HW) * math.cos(t), zs + SHOULDER_H * math.sin(t)) for t in a[::-1]]
        s = np.asarray(q, float)
        return np.c_[np.full(len(s), x), s[:, 0], s[:, 1]]
    return MS.loft([ring(x, z) for x, z in SIDE_TOP])


def _cam_line():
    """Cam walls' top, front -> rear order reversed below: low beside the leaf (the leaf stands fully clear above
    them, as c2 draws it; from X 487.5 they reach the leaf bottom, so the side view shows no gap there), then a smooth
    rise into the front housing."""
    return [(481.0, 39.7), (487.5, 40.75), (494.0, 40.85), (500.0, 41.0), (504.0, 41.5), (507.0, 42.3),
            (509.5, 43.1), (511.5, 43.5), (514.0, 43.6)]


def _screw(x, z, r=1.3, h=0.5, n=10):
    """Small domed screw head on the block's right side face (Y = -COVER_O), sunk 0.1 into it."""
    y = -COVER_O
    return MS.revolve([(-0.1, r), (0.0, r), (h * 0.55, r * 0.8), (h, 0.0)], (x, y, z), (0, -1, 0), n)


def rear_sight_block() -> PartDef:
    """Contoured block on the front trunnion: full-width lower body to the swooping side-face edge, rounded shoulders
    into the deck and cam walls flanking the leaf, the traced see-through sliver under the leaf, the full-height front
    housing with the leaf hinge seat; a channel (Y +-CHAN_HW) holds the leaf."""
    # the see-through gap under the leaf follows the trace's hole ring (LEFT_outline parts.rear_sight, the negative
    # ring) point for point: a 2 mm slit Z 38.7-40.9 from X 465.8 to the hinge block at X 487.5, with the narrow
    # (~1.3 mm) slanted slot the trace shows dropping from it to (472.5, 34.8) (round 2 tried dropping it: per-part
    # L2 0.952 -> 0.948, so it stays)
    cam = _cam_line()
    body = ([(454.92, 10.60), (485.28, 10.60), (485.28, 13.12), (523.98, 13.12), (523.98, 34.3), (522.4, 34.3),
             (522.4, 41.4), (518.7, 43.6)] + cam[::-1] +
            [(477.3, 37.4), (476.1, 37.7), (474.9, 36.1), (472.5, 34.8), (471.9, 35.5),
             (474.3, 38.0), (473.7, 38.7), (466.4, 38.7), (465.8, 39.2),
             (465.8, 40.3), (459.0, 40.3), (458.6, 39.2), (457.9, 38.7), (453.0, 38.7), (452.4, 37.6),
             (454.92, 34.4)])
    # the front housing's transverse rounded bar (c2's hinge bar from the pin head across; side trace: the bump to
    # Z 44.7 at X 508-514 between the knuckle and the retainer boss)
    bar = MS.cylinder((510.8, -BAR_HW, 41.4), (510.8, BAR_HW, 41.4), 3.3, 16, phase_deg=11.25)
    sol = [MS.prism(body, -COVER_O, COVER_O)]
    cut = [MS.box(480.0, 509.5, -CHAN_HW, CHAN_HW, 40.4, 50.0),                                   # leaf channel
           ycyl(LEAF_PIVOT[0], LEAF_PIVOT[1], KNUCKLE_R + 0.2, -CHAN_HW, CHAN_HW, 24),             # hinge seat
           # slider pocket, stepped (integration 2026-10-05): the body's pocket only as wide as the slider body, the
           # catches' pocket starts at their bottom; one full-width box cut through the shoulder band and left a
           # 0.25 mm see-through slit under the slider that joined the traced gap under the leaf (L3 bbox X0 460)
           MS.box(FLOOR_X0 - 0.4, SLIDER_X[1] + 0.4, -SLIDER_HW - 0.25, SLIDER_HW + 0.25, SLIDER_ZB - 0.25, 50.0),
           MS.box(FLOOR_X0 - 0.4, SLIDER_X[1] + 0.4, -CATCH_HW - 0.25, CATCH_HW + 0.25, SKIRT_ZB - 0.1, 50.0)]
    cut.append(xcyl(0.0, TUBE_Z, TUBE_R + GAP, 519.0, 530.0, 32))                         # gas-tube rear recess
    screws = [_screw(512.5, 21.0), _screw(489.0, 31.0)]
    p = PartDef("rear_sight_block", sol, unions=[bar] + screws, cutters=cut,
                cls="M-chamfer")
    # the bevel's fillet in the concave corner over the lower handguard's rear-top edge (X 485.28 / Z 13.12) reached
    # 0.2 mm into the handguard (G5, integration round): trim it, leaving 0.015 above the guard's top (13.1)
    p.post_cutters = [MS.box(485.30, 530.0, -30.0, 30.0, 0.0, 13.115)]
    p.section_intersect_pre = [_shoulder_loft()]
    return p


def _leaf_teeth_top(x_front, x_rear):
    """Rail top line front -> rear with the sawtooth serrations (steep rear flank, sloping front flank)."""
    top = [(x_front, LEAF_ZT)]
    for x in TOOTH_X[::-1]:
        top += [(x + 1.75, LEAF_ZT), (x + 0.75, TOOTH_Z), (x + 0.35, TOOTH_Z), (x, LEAF_ZT)]
    top += [(x_rear, LEAF_ZT)]
    return top


def rear_sight_leaf():
    px, pz = LEAF_PIVOT
    zb, hw = LEAF_ZB, LEAF_HW
    xr = 448.7                                                         # leaf rear end (spec box_M X 448.7)
    # base plate: rear-bottom lip rounded down to Z 39.8 over the cover's front end (side trace 39.65 at X 450-452)
    base = [(xr, LEAF_Z2), (xr, 41.0), (449.3, 40.1), (450.3, 39.8), (452.0, 39.8), (454.0, zb), (px - 1.0, zb),
            (px - 1.0, LEAF_Z2)]
    # flat-topped rails; the sawtooth serrations stand along each rail's slot-side edge (c2: the bright teeth rows
    # flank the dark slot), so the slot reads flanked by teeth and the rails' outer parts stay plain
    rails = [(xr, LEAF_Z2 - 0.3), (px - 1.0, LEAF_Z2 - 0.3), (px - 1.0, LEAF_ZT), (xr, LEAF_ZT)]
    fence = [(SLOT_X[0] - 0.3, LEAF_ZT - 0.4), (SLOT_X[1] + 0.3, LEAF_ZT - 0.4)] + _leaf_teeth_top(SLOT_X[1] + 0.3, SLOT_X[0] - 0.3)
    sol = [MS.prism(base, -hw, hw)]
    uni = [MS.prism(rails, -RAIL_HW, RAIL_HW),
           MS.prism(fence, SLOT_HW - 0.2, SLOT_HW + FENCE_W), MS.prism(fence, -SLOT_HW - FENCE_W, -SLOT_HW + 0.2),
           MS.cylinder((px, -hw, pz), (px, hw, pz), KNUCKLE_R, 16, phase_deg=11.25)]   # no vertex on the leaf faces
    # notch blade on the rails' rear end: rounded top corners, square-bottomed U notch 2.0 wide to Z 45.5
    uni.append(MS.prism(G.rounded_rect(-NOTCH_HW, NOTCH_HW, LEAF_ZT - 0.4, 48.0, 1.4, 2), xr, 451.4, "YZ"))
    cut = [MS.box(447.0, 452.5, -1.0, 1.0, 45.5, 50.0),                                    # U notch
           MS.box(SLOT_X[0], SLOT_X[1], -SLOT_HW, SLOT_HW, zb + 0.7, TOOTH_Z + 1.0)]          # deep centre slot
    # slider: rounded roof, wraps the leaf; side clamps / catches wrap down over the rails' sides
    # slider: raised rounded roof over SLIDER_X, a lower skirt back to the notch blade, long side clamps / catches
    # that wrap down over the rails' sides (c2's three stepped blocks at the leaf's rear end, the near one biggest)
    so = np.vstack([[(SKIRT_X0, SKIRT_ZB), (FLOOR_X0, SKIRT_ZB), (FLOOR_X0, SLIDER_ZB)], G.arc(SLIDER_X[1] - 1.6, SLIDER_ZB + 1.6, 1.6, -90, 0, 3),
                    G.arc(SLIDER_X[1] - 1.6, SLIDER_ZT - 1.6, 1.6, 0, 90, 3), G.arc(SLIDER_X[0] + 1.6, SLIDER_ZT - 1.6, 1.6, 90, 180, 3),
                    [(SLIDER_X[0], SKIRT_Z)], G.arc(SKIRT_X0 + 0.6, SKIRT_Z - 0.6, 0.6, 90, 180, 3)[1:]])
    slider = MS.prism(so, -SLIDER_HW, SLIDER_HW)
    catch_o = G.rounded_rect(SKIRT_X0 + 0.3, SLIDER_X[1] - 0.4, SKIRT_ZB + 0.15, 47.4, 1.6, 2)
    catches = [MS.prism(catch_o, SLIDER_HW - 0.3, CATCH_HW), MS.prism(catch_o, -CATCH_HW, -(SLIDER_HW - 0.3))]
    slider_cut = MS.box(SKIRT_X0 - 0.5, SLIDER_X[1] + 0.5, -hw - 0.15, hw + 0.15, zb - 0.15, LEAF_ZT + 0.15)
    return PartDef("rear_sight_leaf", sol, unions=uni, cutters=cut, bone="sight_rear",
                   cls="M-chamfer", recipe=[(0.25, 1, 40.0)],          # 40 deg: the teeth's sloping flanks stay unbevelled
                   joint={"type": "hinge", "parent": "rear_sight_block", "pivot_M": [px, 0.0, pz],
                          "axis_M": [0, 1, 0], "range_deg": [0.0, 6.0], "clearance_mm": [0.1, 0.3]}), \
        PartDef("rear_sight_slider", [slider], unions=catches, post_cutters=[slider_cut], bone="sight_rear",
                cls="M-chamfer", recipe=[(0.25, 1, 30.0)], spec_id="rear_sight_leaf",
                joint={"type": "sliding", "parent": "rear_sight_leaf", "clearance_mm": [0.15, 0.4],
                       "note": "range adjuster; no bone (static in the clips)"})


def _stadium(a, b, ra, rb, n=9):
    d = np.subtract(b, a)
    L = float(np.hypot(*d))
    ang = math.degrees(math.atan2(d[1], d[0]))
    P = np.vstack([G.arc(L, 0, rb, -90, 90, n), G.arc(0, 0, ra, 90, 270, n)])
    return G.rot(P, ang, (0, 0)) + np.asarray(a, float)


def retainer() -> PartDef:
    yb = -COVER_O - GAP
    t = 1.6                                        # stamped link thickness
    boss_c, end_c = (516.5, 41.0), (500.0, 24.0)   # read off a 10x zoom of the LEFT panel
    u = np.subtract(end_c, boss_c)
    L = float(np.hypot(*u))
    u = u / L
    sol = [MS.prism(_stadium(boss_c, end_c, 3.3, 2.9), yb - t, yb)]          # slim link (c2: thin bright bars)
    s0, s1 = np.add(boss_c, u * 0.27 * L), np.add(boss_c, u * 0.80 * L)
    cut = [MS.prism(_stadium(s0, s1, 1.3, 1.3, 7), yb - t - 1.0, yb + 0.5)]       # open slot (3/4 view, LEFT)
    # prominent pivot pin: collar + domed head (c2's big round pin head at the block's top front corner)
    y0 = yb - t + 0.05
    pin = MS.revolve([(0.0, 3.5), (1.1, 3.5), (1.25, 3.25), (1.75, 2.8), (2.2, 1.7), (2.35, 0.0)],
                     (boss_c[0], y0, boss_c[1]), (0, -1, 0), 14)
    screw = MS.revolve([(0.0, 1.2), (0.35, 0.95), (0.55, 0.0)], (end_c[0], y0, end_c[1]), (0, -1, 0), 10)
    left = ycyl(boss_c[0], boss_c[1], 3.4, COVER_O + GAP, COVER_O + GAP + 1.8, 14)
    return PartDef("handguard_retainer", sol + [left], unions=[pin, screw], cutters=cut, cls="S-cut",
                   recipe=[(0.3, 1, 30.0)], spec_id="handguard_retainer_lever")


# ======================================================================================== module interface
OBJECTS = ('rear_sight_block', 'rear_sight_leaf', 'handguard_retainer')            # registry keys built here (rifle_parts.ORDER)
CLOSEUPS = ('c2', 'q34')          # sheet panels that are this part's shape authority (rifle_detail.py)


def build(spec, ctx):
    """Build this module's objects into ctx (gunlib.parts.BuildCtx). Returns {registry key: [objects]}; keys that
    ctx.only excludes come back empty. `spec` is the rifle GunSpec (the same object as rifle_common.SPEC)."""
    return {k: ctx.make(k, f) for k, f in (("rear_sight_block", rear_sight_block), ("rear_sight_leaf", rear_sight_leaf), ("handguard_retainer", retainer),)}
