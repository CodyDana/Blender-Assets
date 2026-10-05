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

Round 2b (2026-10-05, re-run on the integrated build, against the round-1 judge's tells): ratchet teeth moved to the
rails' OUTER edges as sawtooth V-grooves (flat rail tops, through slot); the notch blade became a two-lobed block as
wide as the slider with stepped shoulders, joined to the slider skirt; the shoulder band is rolled (half ellipse) behind
a small ledge along the side face's S-edge; the front housing's corners are rounded (hood) and the rear corners and lip
too; the traced slanted slot is a short upright slot; the retainer link is a little broader. Gates:
WorkFiles/guns/rifle/gates/detail_rear_sight_r2.json.
"""
from __future__ import annotations

import math

import numpy as np

from gunlib import geo2d as G
from gunlib import lod as LOD
from gunlib import mesh as MS
from gunlib.parts import PartDef
from rifle_parts import GAP, COVER_O
from rifle_parts2 import TUBE_Z, TUBE_R, ycyl, xcyl


# ======================================================================================== rear sight
LEAF_PIVOT = (504.0, 41.0)


def _held(fn, *a, **k):
    """Build a hinge mesh at LOD0 resolution up to LOD1 (the knuckle in its seat keeps the 0.10-0.30 hinge row)."""
    with LOD.hold(1):
        return fn(*a, **k)

KNUCKLE_R = 5.6
SIGHT_CH_HW, SIGHT_CH_Z = 1.6, 45.0       # game-stage fix: sight channel through the knuckle crown (gate S2)
LEAF_ZB, LEAF_ZT = 40.6, 44.7             # leaf bottom / flat rail top at rest (2b: 44.7 = mean of the traced 44.1-45.4 tooth bumps)
LEAF_Z2 = 42.3                            # top of the leaf's base plate; the rails stand on it
TOOTH_Z = 45.1                            # side trace tooth tops (Z 44.1-45.4 at X 472-491); only bounds the slot cutter now
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
SIGHT_GROOVE_HW = 1.2                     # detail fix: sight groove through the slider roof (half width)
SLIDER_HW = 10.0                          # slider body half width (wraps the leaf)
CATCH_HW = 13.4                           # side clamps / catches reach (c2's big near-side box)
# FORM REALISM ROUND (gate B4, R48): the slider's roof stood at the traced 48.5, 0.5 above the notch top (48.0) and
# right in front of it, so from the ADS eye on the Sight line its top edge (and its groove) formed the visible notch
# top, 0.58 mm above the real one, and the post tip sat low in a 'second notch'. On the real pattern the slider sits
# below the notch top; 47.6 is 0.4 under it (0.5 sheet px from the trace: inside its noise; L3 slider tol 2.43)
SLIDER_ZB, SLIDER_ZT = LEAF_ZB - 1.0, 47.6
BAR_HW = 15.5                             # transverse rounded bar on the front housing (c2's hinge bar)
DECK_HW = 13.0                            # deck / cam walls half width above the shoulder (leaf + thin walls)
TOOTH_PITCH = 1.45                        # DETAIL FIX (user checklist 6): FINE ratchet teeth (real pattern ~1.2 mm; r2b 2.8)
TOOTH_X = np.arange(467.4, 497.4, TOOTH_PITCH)   # sawtooth serrations along both rails' outer edges
NOTCH_LOBE_HW = 7.2                       # 2b: notch block lobes' upper (stepped) part, half width
BLOCK_ZB = 41.2                           # 2b: notch block / foot bottom (wraps down over the leaf's sides)
# side face top edge (where the shoulder starts), X -> Z: low rear part, a step / S-rise at X 472-478 (the side
# panel's face edge at Z 35.6 / 37.4), then the swoop up into the full-height front housing from X ~504
SIDE_TOP = [(440.0, 34.8), (462.0, 34.8), (468.0, 34.3), (474.0, 34.0), (481.0, 34.4), (488.0, 35.3),
            (494.0, 36.4), (499.0, 37.8), (503.0, 39.4), (506.5, 41.6), (509.5, 44.4), (511.5, 60.0), (540.0, 60.0)]
SHOULDER_H = 5.6                          # shoulder rise from the side face top edge to the deck edge
SHOULDER_N = 5                            # rolled band: points across it
LEDGE_W = 1.4                             # DETAIL FIX (user checklist 6): a clear STEP in the sculpted side wall (2b 0.9)
ROLL = 0.6                                # 0 = straight chamfer, 1 = full elliptical quarter (tangent at the face)
REAR_R, REAR_R_Z0 = 3.5, 24.0             # 2b: rear vertical corners' plan radius, from Z (above the cover's side)
FRONT_R = 4.0                             # 2b: front housing's vertical front corners, plan radius
TOOTH_DEPTH = 0.75                        # DETAIL FIX: fine V-grooves' depth below the rail top (2b 1.5)
TOOTH_W = 1.6                             # DETAIL FIX: toothed strip along each rail's outer edge (2b 2.6)


def _shoulder_loft():
    """Intersect volume for the block: full width (the cover's 43.5) up to SIDE_TOP, then a rounded shoulder rolling
    in to the deck (Y +-DECK_HW), which runs up past everything. Section = elliptical quarter, 4 segments a side."""
    W = COVER_O + 0.05
    Wb = W - LEDGE_W                              # 2b: the band starts behind a small ledge (c2's bright S-line)
    # round 2b: a ROLLED band (round-1 judge: "sharp diagonal chamfer" vs the drawing's "softer, rolled transitions"):
    # half elliptical quarter, half chamfer, so the band bulges but both its edges still catch a crisp line (c2's two
    # bright S-lines)
    t = np.linspace(0.0, 1.0, SHOULDER_N)
    a = t * math.pi / 2
    cy = ROLL * np.cos(a) + (1 - ROLL) * (1 - t)            # 1 -> 0 across the band
    cz = ROLL * np.sin(a) + (1 - ROLL) * t                  # 0 -> 1

    def ring(x, zs):
        q = [(-W, 5.0), (W, 5.0)]
        band = [(Wb, zs + 0.12)] + [(DECK_HW + (Wb - DECK_HW) * u, zs + 0.12 + SHOULDER_H * v) for u, v in zip(cy[1:], cz[1:])]
        q += [(W, zs)] + band
        q += [(DECK_HW, 75.0), (-DECK_HW, 75.0)]
        q += [(-y, z) for y, z in band[::-1]] + [(-W, zs)]
        s = np.asarray(q, float)
        return np.c_[np.full(len(s), x), s[:, 0], s[:, 1]]
    return MS.loft([ring(x, z) for x, z in SIDE_TOP])


def _cam_line():
    """Cam walls' top, front -> rear order reversed below: low beside the leaf (the leaf stands fully clear above
    them, as c2 draws it; from X 487.5 they reach the leaf bottom, so the side view shows no gap there), then a smooth
    rise into the front housing."""
    return [(481.0, 39.7), (487.5, 40.75), (494.0, 40.85), (500.0, 41.0), (504.0, 41.5), (507.0, 42.3),
            (509.5, 43.1), (511.5, 43.5), (514.0, 43.6)]


def _corner_cutter(x, y, r, sy, n=7, sx=1, z0=0.0, z1=80.0, ext=1.0):
    """Plan-view (XY) negative of a rounded vertical corner at (x, y): the region outside a quarter circle of radius
    r, extruded over Z z0..z1. sy = +1 for a +Y (left) corner, -1 for the right; sx = +1 front corner, -1 rear."""
    cx, cy = x - sx * r, y - sy * r
    arc = [(cx + sx * r * math.cos(t), cy + sy * r * math.sin(t)) for t in np.linspace(0.0, math.pi / 2, n)]
    P = [(x + sx * ext, cy), *arc, (cx, y + sy * 1.0), (x + sx * ext, y + sy * 1.0)]
    return MS.prism(P, z0, z1, "XY")


def _screw(x, z, r=1.3, h=0.5, n=10):
    """Small domed screw head on the block's right side face (Y = -COVER_O), sunk 0.1 into it."""
    y = -COVER_O
    return MS.revolve([(-0.1, r), (0.0, r), (h * 0.55, r * 0.8), (h, 0.0)], (x, y, z), (0, -1, 0), n)


def rear_sight_block() -> PartDef:
    """Contoured block on the front trunnion: full-width lower body to the swooping side-face edge, rounded shoulders
    into the deck and cam walls flanking the leaf, the traced see-through sliver under the leaf, the full-height front
    housing with the leaf hinge seat; a channel (Y +-CHAN_HW) holds the leaf."""
    # the see-through gap under the leaf follows the trace's hole ring (LEFT_outline parts.rear_sight, the negative
    # ring): a 2 mm slit Z 38.7-40.9 from X 465.8 to the hinge block at X 487.5. Round 2b: the trace's slanted slot
    # down to (472.5, 34.8) read as a chip in the shoulder band in c2 (lit slanted floor); it is now a short upright
    # slot (1.2 wide, rounded bottom at Z 36.0) mostly in the leaf's shadow, which keeps L3's bbox inside tolerance
    # (Z0 36.0 vs 34.8; dropping the slot entirely gave 37.5, error 2.7 > 2.43) and per-part L2 >= 0.96
    cam = _cam_line()
    body = ([(454.92, 10.60), (485.28, 10.60), (485.28, 13.12), (523.98, 13.12), (523.98, 34.3), (522.4, 34.3),
             (522.4, 40.6), (522.1, 41.6), (521.2, 42.6), (519.9, 43.3), (518.7, 43.6)] + cam[::-1] +
            [(477.3, 37.4), (476.1, 37.7), (474.3, 38.0), (473.7, 38.7), (466.4, 38.7), (465.8, 39.2),
             (465.8, 40.3), (459.0, 40.3), (458.6, 39.2), (457.9, 38.7), (453.4, 38.7), (452.7, 38.4),
             (452.35, 37.8), (452.45, 37.1), (453.0, 36.4), (454.92, 34.4)])
    # the front housing's transverse rounded bar (c2's hinge bar from the pin head across; side trace: the bump to
    # Z 44.7 at X 508-514 between the knuckle and the retainer boss)
    bar = MS.cylinder((510.8, -BAR_HW, 41.4), (510.8, BAR_HW, 41.4), 3.3, 16, phase_deg=11.25)
    sol = [MS.prism(body, -COVER_O, COVER_O)]
    cut = [MS.box(480.0, 509.5, -CHAN_HW, CHAN_HW, 40.4, 50.0),                                   # leaf channel
           _held(ycyl, LEAF_PIVOT[0], LEAF_PIVOT[1], KNUCKLE_R + 0.2, -CHAN_HW, CHAN_HW, 24),      # hinge seat (LOD1 = LOD0)
           # slider pocket, stepped (integration 2026-10-05): the body's pocket only as wide as the slider body, the
           # catches' pocket starts at their bottom; one full-width box cut through the shoulder band and left a
           # 0.25 mm see-through slit under the slider that joined the traced gap under the leaf (L3 bbox X0 460)
           MS.box(FLOOR_X0 - 0.4, SLIDER_X[1] + 0.4, -SLIDER_HW - 0.25, SLIDER_HW + 0.25, SLIDER_ZB - 0.25, 50.0),
           MS.box(FLOOR_X0 - 0.4, SLIDER_X[1] + 0.4, -CATCH_HW - 0.25, CATCH_HW + 0.25, SKIRT_ZB - 0.1, 50.0)]
    cut.append(xcyl(0.0, TUBE_Z, TUBE_R + GAP, 519.0, 530.0, 32))                         # gas-tube rear recess
    # round 2b: the front housing's vertical front corners rounded R FRONT_R in plan (c2: a rounded hood wraps the
    # block's front beside the pin head; round-1 judge: "rounded hood with a smooth curved top that wraps over",
    # "softer, rolled transitions" where ours had a sharp chamfer); the top-front corner is an arc too (body outline)
    cut += [_corner_cutter(523.98, -COVER_O - 0.05, FRONT_R, -1), _corner_cutter(523.98, COVER_O + 0.05, FRONT_R, 1)]
    # ... and the rear vertical corners above the dust cover's crown (c2: the block's rear edge sweeps round into the
    # cover instead of standing as a sharp square corner)
    cut += [_corner_cutter(455.0, sy * (COVER_O + 0.05), REAR_R, sy, sx=-1, z0=REAR_R_Z0, ext=4.0) for sy in (-1, 1)]
    screws = [_screw(512.5, 21.0), _screw(489.0, 31.0)]
    p = PartDef("rear_sight_block", sol, unions=[bar] + screws, cutters=cut,
                cls="M-chamfer")
    # the bevel's fillet in the concave corner over the lower handguard's rear-top edge (X 485.28 / Z 13.12) reached
    # 0.2 mm into the handguard (G5, integration round): trim it, leaving 0.015 above the guard's top (13.1)
    p.post_cutters = [MS.box(485.30, 530.0, -30.0, 30.0, 0.0, 13.115)]
    # integration round (r2b): the short upright slot is cut AFTER the bevel, as a clean prism through the full width.
    # Cut into the profile before the shoulder intersect and the bevel, its walls met the rolled band at grazing angles
    # and the bevel threw a jagged shard there (c2 crop: a "torn crease" across the block's upper side, judge r2b)
    # A 1.45 mm slot still rendered its lit end wall as a thin shard in the band (c2); it is now a broader rounded
    # scallop (U, r 2.1, bottom Z 36.05 as before: L3 gap bbox Z0 unchanged), which c2 reads as the "curved notch" the
    # reference's block has where the band meets the leaf
    sc = [(475.3 + 2.1 * math.cos(t), 38.15 + 2.1 * math.sin(t)) for t in np.linspace(math.pi, 2 * math.pi, 13)]
    p.post_cutters.append(MS.prism([(473.2, 40.2)] + sc + [(477.4, 40.2)], -COVER_O - 1.0, COVER_O + 1.0))
    p.section_intersect_pre = [_shoulder_loft()]
    return p


def _notch_block_section():
    """Y-Z section of the rear notch block: two lobes either side of the notch, each with a stepped outer shoulder."""
    hw, hs, zt, zs, zb, c = SLIDER_HW, NOTCH_LOBE_HW, 48.0, 46.7, BLOCK_ZB, 0.45
    half = [(hw, zb), (hw, zs - c), (hw - c, zs), (hs + c * 0.6, zs), (hs, zs + c * 0.6), (hs, zt - c), (hs - c, zt)]
    return np.asarray(half + [(-y, z) for y, z in half[::-1]], float)


def rear_sight_leaf():
    px, pz = LEAF_PIVOT
    zb, hw = LEAF_ZB, LEAF_HW
    xr = 448.7                                                         # leaf rear end (spec box_M X 448.7)
    # base plate: rear-bottom lip rounded down to Z 39.8 over the cover's front end (side trace 39.65 at X 450-452)
    base = [(xr, LEAF_Z2), (xr, 41.0), (449.3, 40.1), (450.3, 39.8), (452.0, 39.8), (454.0, zb), (px - 1.0, zb),
            (px - 1.0, LEAF_Z2)]
    # flat-topped rails; round 2b: the ratchet serrations run along each rail's OUTER edge (c2: the near rail's bright
    # saw-toothed near edge with its flat top between the teeth and the slot; the slider's catches engage these edges;
    # round-1 judge: "toothed, ratchet-like serrated edges along both rails"), the slot between flat rail tops
    rails = [(xr, LEAF_Z2 - 0.3), (px - 1.0, LEAF_Z2 - 0.3), (px - 1.0, LEAF_ZT), (xr, LEAF_ZT)]
    sol = [MS.prism(base, -hw, hw)]
    uni = [MS.prism(rails, -RAIL_HW, RAIL_HW),
           _held(MS.cylinder, (px, -hw, pz), (px, hw, pz), KNUCKLE_R, 16, phase_deg=11.25)]   # no vertex on the leaf faces
    # rear notch block (round 2b): one chunky transverse block as wide as the slider, the U notch splitting it into two
    # lobes with stepped shoulders, wrapping down over the leaf's sides and running forward under the slider's skirt
    # so notch block + slider read as one assembly (round-1 judge: "a chunkier two-lobed block with stepped
    # shoulders", not a separate small U block); notch 2.0 wide, bottom 45.5 = spec notch_bottom_Z
    uni.append(MS.prism(_notch_block_section(), xr, 451.4, "YZ"))
    uni.append(MS.prism(G.rounded_rect(-SLIDER_HW, SLIDER_HW, BLOCK_ZB, SKIRT_Z, 0.5, 2), 451.0, SKIRT_X0 - 0.2, "YZ"))
    cut = [MS.box(447.0, 452.5, -1.0, 1.0, 45.5, 50.0),                                    # U notch
           # GAME STAGE FIX (2026-10-05, gate S2): the hinge knuckle (R 5.6 about Z 41.0, top 46.6, the traced bump)
           # stood 1.2 mm above the spec sight line (notch bottom 45.5 -> post tip 45.0; 45.43 at the pivot X) and
           # hid the front post from the Sight eye point. A sight channel through the knuckle's crown along the sight
           # line (3.2 wide, floor 45.0) clears it; the knuckle's sides keep the traced side silhouette
           MS.box(px - KNUCKLE_R - 1.0, px + KNUCKLE_R + 1.0, -SIGHT_CH_HW, SIGHT_CH_HW, SIGHT_CH_Z, 52.0),
           MS.box(SLOT_X[0], SLOT_X[1], -SLOT_HW, SLOT_HW, zb - 1.0, TOOTH_Z + 1.0)]          # deep centre slot, through (2b)
    # ratchet teeth along both rails' outer edges: sawtooth V-grooves (steep rear flank, sloping front flank) cut
    # across an outer strip TOOTH_W wide, so the edge reads as a row of standing teeth from above and behind (c2's
    # bright triangles along the near rail) with the flat rail top between the teeth and the slot
    p_, d_ = TOOTH_PITCH, TOOTH_DEPTH
    k_ = (d_ + 1.0) / d_                                   # the V extended 1.0 above the rail top
    for x in (TOOTH_X if LOD.LEVEL < 2 else ()):        # LOD2: 1.45 mm teeth are 0.3 px at 6.7 m
        bx, bz = x + 0.12 * p_, LEAF_ZT - d_                # groove bottom; steep rear flank, sloping front flank
        tri = [(bx + (x - bx) * k_, LEAF_ZT + 1.0), (bx + (x + 0.8 * p_ - bx) * k_, LEAF_ZT + 1.0), (bx, bz)]
        cut.append(MS.prism(tri, RAIL_HW - TOOTH_W, RAIL_HW + 1.0))
        cut.append(MS.prism(tri, -RAIL_HW - 1.0, -RAIL_HW + TOOTH_W))
    # slider: rounded roof, wraps the leaf; side clamps / catches wrap down over the rails' sides
    # slider: raised rounded roof over SLIDER_X, a lower skirt back to the notch blade, long side clamps / catches
    # that wrap down over the rails' sides (c2's three stepped blocks at the leaf's rear end, the near one biggest)
    so = np.vstack([[(SKIRT_X0, SKIRT_ZB), (FLOOR_X0, SKIRT_ZB), (FLOOR_X0, SLIDER_ZB)], G.arc(SLIDER_X[1] - 1.6, SLIDER_ZB + 1.6, 1.6, -90, 0, 3),
                    G.arc(SLIDER_X[1] - 1.6, SLIDER_ZT - 1.6, 1.6, 0, 90, 3), G.arc(SLIDER_X[0] + 1.6, SLIDER_ZT - 1.6, 1.6, 90, 180, 3),
                    [(SLIDER_X[0], SKIRT_Z)], G.arc(SKIRT_X0 + 0.6, SKIRT_Z - 0.6, 0.6, 90, 180, 3)[1:]])
    slider = MS.prism(so, -SLIDER_HW, SLIDER_HW)
    catch_o = G.rounded_rect(SKIRT_X0 + 0.3, SLIDER_X[1] - 0.4, SKIRT_ZB + 0.15, SLIDER_ZT - 0.6, 1.6, 2)   # (form realism: under the roof)
    catches = [MS.prism(catch_o, SLIDER_HW - 0.3, CATCH_HW), MS.prism(catch_o, -CATCH_HW, -(SLIDER_HW - 0.3))]
    slider_cut = MS.box(SKIRT_X0 - 0.5, SLIDER_X[1] + 0.5, -hw - 0.15, hw + 0.15, zb - 0.15, LEAF_ZT + 0.15)
    # DETAIL FIX (ADS realism shot, 2026-10-05): the slider's top (Z 48.5, traced) stood 3 mm above the notch bottom
    # (45.5) right in front of the notch and BLOCKED THE SIGHT LINE (no front post in the sight picture). A sight groove
    # 2.4 wide runs through the slider's roof down to the leaf channel along the sight line, as on the real pattern's
    # slider (the side silhouette and the L3 slider reading at Y 6.6 are unchanged)
    sight_groove = MS.box(SKIRT_X0 - 0.5, SLIDER_X[1] + 0.5, -SIGHT_GROOVE_HW, SIGHT_GROOVE_HW, LEAF_ZT + 0.1, 52.0)
    return PartDef("rear_sight_leaf", sol, unions=uni, cutters=cut, bone="sight_rear",
                   cls="M-chamfer", recipe=[(0.25, 1, 40.0)],          # 40 deg: the teeth's sloping flanks stay unbevelled
                   joint={"type": "hinge", "parent": "rear_sight_block", "pivot_M": [px, 0.0, pz],
                          "axis_M": [0, 1, 0], "range_deg": [0.0, 6.0], "clearance_mm": [0.1, 0.3]}), \
        PartDef("rear_sight_slider", [slider], unions=catches, post_cutters=[slider_cut, sight_groove], bone="sight_rear",
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
    # round 2b: a little broader (boss r 3.3 -> 3.9, end 2.9 -> 3.5, slot r 1.3 -> 1.65): the 3/4 view draws the link
    # ~1.5x wider than ours with a big open slot; the LEFT panel zoom reads ~7.5 mm across the bars
    sol = [MS.prism(_stadium(boss_c, end_c, 3.9, 3.5), yb - t, yb)]
    s0, s1 = np.add(boss_c, u * 0.27 * L), np.add(boss_c, u * 0.80 * L)
    cut = [MS.prism(_stadium(s0, s1, 1.65, 1.65, 7), yb - t - 1.0, yb + 0.5)]       # open slot (3/4 view, LEFT)
    # prominent pivot pin: collar + domed head (c2's big round pin head at the block's top front corner)
    y0 = yb - t + 0.05
    pin = MS.revolve([(0.0, 3.6), (1.1, 3.6), (1.25, 3.3), (1.75, 2.8), (2.2, 1.7), (2.35, 0.0)],
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
