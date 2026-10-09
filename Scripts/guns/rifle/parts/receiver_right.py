"""Detail part RECEIVER (RIGHT): the stamped receiver body and everything on its right face.

Owns the objects: receiver (body, port, dimples, flush pin, groove), dust_cover, recoil_spring_button, rivets,
receiver_rails, bolt_carrier (bolt + carrier + charging handle; moving, bone "bolt") and mag_catch (bone "mag_release").
Detail-pass scope (judge pair 01): rivet layout, pins, the retainer clip and hole above the magazine well, the ejection
port and the bolt carrier's visible face, the dimple, the mag catch area.
Authority close-ups: c1 RECEIVER AND SELECTOR (RIGHT) and the 3/4 view; c2 for the dust cover's top.
Interfaces kept fixed for the neighbours: wall half width WO / cover COVER_O (rifle_parts), the selector pivot hole
(282.8, -7.8), the trigger slot, the bolt travel CARRIER_TRAVEL (B3 sweep), CATCH_PIVOT (rifle_parts2; the catch pin
and its cheeks are on the trigger guard).
Detail round 1 (2026-10-05): carrier fills the port (stepped rear, no round bolt), skirt cutout lifted with a rise
(CUT_*), handle lowered (HANDLE_Z / STEM_Z), retainer clip at CLIP_AT instead of that rivet, teardrop recess, crisp
floored dimples, button rivet heads. Private build/render/gate loop: parts/receiver_right_run.py; numbers in
WorkFiles/guns/rifle/gates/detail_receiver_right_r1.json; spec changes it needs: review/detail/receiver_right/
spec_proposal.json.
Detail round 2 (2026-10-05, judge r1 on c1): dust cover = shouldered section with a deep lengthwise crease and a fuller
crown + four crown studs (receiver_right_cover.py); skirt cutout rises at X 349-355.5 to Z 19.2 so the port reads as
one long slot; carrier: flat flanks to Z 20, raised middle step (19.6), deep flank recess below Z 9.5 (dark band under
a lit bar); port rear edge stepped (wall hides the empty space behind the carrier); teardrop = through cutout inside
a pressed rim; c1 part camera re-registered on the c1 receiver landmarks (receiver_right_register.py). Gates:
WorkFiles/guns/rifle/gates/detail_receiver_right_r2.json.
Detail round 2 rerun (r2b, judge r1 tells on c1): one slot from the skirt step (wall cut under a 9.6 skirt edge, full
port from PORT_X0, cutout rise back at X 372-378.5), dark notch interior (carrier recess to its bottom, rail gap),
domed rivets and pin head, hairpin wire clip, 1.5 deep right dimple on an inner block, rolled rear edges.
LAST SHAPE ROUND (2026-10-05, orchestrator rulings 1 / 3 / 5): cover ribs removed and tighter R 3.2 shoulders
(receiver_right_cover.py); the REAL charging handle (handle_knob: a flat stem and a bent-up knob 24.85 mm proud of the
wall; real-pattern photos in WorkFiles/guns/rifle/scratch/realref); the mag catch paddle as a pressed-rib stamping.
MAGAZINE-FIT LOOP-BACK (2026-10-06, R51; stage 6 failed M2 / M3 on an empty shell): the FRONT TRUNNION is a block
inside the receiver front (X >= TRUNNION_X0 below TRUNNION_TOP_Z, under the carrier) with the barrel's chamber mouth
and a feed ramp on its rear face; the magazine well, the lug pocket, the tab channel and its LEDGE, and the trunnion's
underside over the magazine's front zone are the swept envelopes of the magazine's silhouettes over the reload path
plus their clearance rows (Scripts/guns/rifle/rifle_magfit.py: seam 0.06 over the sweep, never under 0.26 to the
seated magazine, lug 0.2, top stop 0.2); the bottom sheet behind the opening is cut back along the rock-start pose's
tilted rear face; the catch's top in front of a notch is an arc about the catch pin (its nose under the magazine's
rear lug). LOD2 (6.7 m+): no feed ramp and one lug/tab pocket (both inside the trunnion, never seen; the LOD2 share
of LOD0 went 18.1 % -> 17.8 %, limit 18 %).
"""
from __future__ import annotations

import json
import math

import numpy as np

from rifle_common import SPEC
from gunlib import geo2d as G
from gunlib import lod as LOD
from gunlib import mesh as MS
from gunlib.mesh import Mesh
from gunlib.parts import PartDef
from rifle_parts import GAP, WO, WT, COVER_O, COVER_I, LEDGE, ledge_z, prof, lower_handguard_tenon
from rifle_parts2 import CATCH_PIVOT, ycyl

from parts import receiver_right_cover as RC  # noqa: E402
import rifle_magfit as MF  # noqa: E402

TRUNNION_X0 = 418.0             # R51: the front trunnion's rear face (under the carrier); the cuts below carve it
TRUNNION_TOP_Z = -5.0           # its top inside the receiver: 1.0 under the carrier's bottom (-4.0 before the bevels)
TRUNNION_FRONT_X = 452.03       # the block's face above its top (the old solid front was 452.0: coplanar with the port's
#                                 front end, the block's top corner left a 0.006 mm sliver; the rails end 0.05 short)
RAMP = ((417.0, -13.6), (431.0, -7.6), 7.0)    # feed ramp on the rear face: line (X, Z) -> (X, Z), half width
CHAMBER_X = 431.0               # the bore through the trunnion starts here (the barrel's rear end is at 433.8)
# STAGE-7 FIX ROUND (craft review item 3, 2026-10-08: 'the receiver is an empty shell at full bolt travel; no bolt
# head, no chamber'): the real pattern's rotating BOLT now rides in the carrier (bolt_carrier, BOLT_*), its head in a
# bore through the trunnion's rear (BOLT_BORE_R) up to the barrel's breech; over the barrel's rear end the trunnion
# stands up to TRUNNION_UP_Z (the barrel end sits in the trunnion, as on the real receiver, instead of in a pocket of
# the carrier), so the port's front shows the trunnion block, and at full travel the bolt face + extractor show at the
# port's rear with the trunnion, the chamber mouth and the magazine top ahead of them
TRUNNION_UP_X = 434.0           # the raised block's rear face (the barrel's breech at 433.8 sits just inside it)
TRUNNION_UP_Z = 8.0             # its top: 1.0 under the carrier's front section (Z 9.0), 0.6 under the handle stem
BOLT_BORE_R = 8.0               # bolt head bore through the trunnion's rear (bolt r 7.6: 0.4 radial clearance)


# ======================================================================================== bevel predicates
def pred_bend_bottom(mid, d, n1, n2, dih):
    """Receiver bottom bends: edge along X between a wall face (normal +-Y) and a bottom face (normal -Z, or +Z
    inside)."""
    if abs(d[0]) < 0.8 or dih < 60:
        return 0.0
    a = abs(n1[1]) > 0.8 and abs(n2[2]) > 0.8
    b = abs(n2[1]) > 0.8 and abs(n1[2]) > 0.8
    if (a or b) and mid[2] < -26.0 and abs(mid[1]) > 18.5:
        return 1.0
    return 0.0


def pred_bend_receiver(mid, d, n1, n2, dih):
    """pred_bend_bottom + (detail r2b) the rear end's vertical outer edges (X 240.92, wall faces +-Y against the rear
    face -X): the side panel draws a bright rolled rear edge and c1 a rounded transition, not a cut slab. Weight
    REAR_ROLL / 1.6 (the 1.0 walls keep ~0.7 at the corner)."""
    w = pred_bend_bottom(mid, d, n1, n2, dih)
    if w > 0:
        if 365.0 < mid[0] < 435.0 and mid[1] < 0 and abs(mid[1]) < WO - 0.5:
            return 0.0          # inner (unseen) right corner along the dimple block: the 1.6 ring would cross the block
        return w
    if abs(d[2]) > 0.8 and dih > 60 and mid[0] < 241.6 and abs(mid[1]) > 19.5 and mid[2] < 10.0:
        a = abs(n1[0]) > 0.8 and abs(n2[1]) > 0.8
        b = abs(n2[0]) > 0.8 and abs(n1[1]) > 0.8
        if a or b:
            return REAR_ROLL / 1.6
    return 0.0


def pred_cover_cut(mid, d, n1, n2, dih):
    """Dust cover (form realism round): a crisp 0.3 break on the CUT edges only -- skirt bottoms and the lip's bottom
    (horizontal faces), lip end / front end / button-hole ends (faces square to X), button-hole sides (square to Y
    near the centre) and the port cutout walls (normals in the XZ plane on the right skirt). The two lofted sheet
    faces are smooth and never bevelled (the squashed rear rings make steep but smooth turns)."""
    if dih < 40.0:
        return 0.0
    for n in (n1, n2):
        if abs(n[2]) > 0.999 or abs(n[0]) > 0.999:
            return 1.0
        if abs(n[1]) > 0.999 and abs(mid[1]) < 3.4:
            return 1.0
        if abs(n[1]) < 0.02 and mid[1] < -15.0:
            return 1.0
    return 0.0


def open_chaikin(P, iters=3):
    P = np.asarray(P, float)
    for _ in range(iters):
        Q = [P[0]]
        for a, b in zip(P[:-1], P[1:]):
            Q += [0.75 * a + 0.25 * b, 0.25 * a + 0.75 * b]
        Q.append(P[-1])
        P = np.array(Q)
    return P


# ======================================================================================== receiver group
def receiver() -> PartDef:
    x_r, x_f = 240.92, 485.3
    top_cov, top_fr = 11.0, 10.58
    bottom = [(x_r, -34.78), (251.98, -34.78), (251.98, ledge_z(251.98))]
    bottom += [(x, z) for x, z in LEDGE if 251.98 < x < 368.8]
    # ahead of the well: the traced line lifted 0.2 so its mean equals the spec's -28.8
    bottom += [(368.8, ledge_z(368.8)), (368.8, -30.85), (432.0, -30.85), (432.0, -29.52), (447.0, -29.3),
               (472.5, -27.9), (479.8, -28.3), (481.0, -29.4), (x_f, -29.4)]
    outer = bottom + [(x_f, top_fr), (454.9, top_fr), (454.9, top_cov), (x_r, top_cov)]
    solids = [MS.prism(outer, -WO, WO)]
    # interior: 1.0 mm walls, rear wall, the front trunnion block (R51: X >= 418 under Z -5, its upper face at 451); open
    # top (closed by the cover)
    ib = [(x_r + WT, -34.78 + WT), (250.98, -34.78 + WT), (250.98, ledge_z(250.98) + WT)]
    ib += [(x, z + WT) for x, z in LEDGE if 250.98 < x < 369.8]
    # R51: the interior stops at the front trunnion's rear face below its top (the block the well / pocket cuts carve)
    ib += [(369.8, ledge_z(369.8) + WT), (369.8, -30.85 + WT), (TRUNNION_X0, -30.85 + WT),
           (TRUNNION_X0, TRUNNION_TOP_Z), (TRUNNION_UP_X, TRUNNION_TOP_Z), (TRUNNION_UP_X, TRUNNION_UP_Z),
           (TRUNNION_FRONT_X, TRUNNION_UP_Z), (TRUNNION_FRONT_X, 30.0)]
    inner = ib + [(x_r + WT, 30.0)]
    # detail r2b: a 1.0 mm block stays behind the right dimple (the sheet pressed inward), so the dimple can be pressed
    # DIMPLE_DEPTH deep (c1 'deep round hole', side panel: strong rim, dark floor): the right wall's first 1.0 mm of
    # interior is cut with the inner outline notched up from the bottom at the block (hidden: between the wall and
    # the magazine-well liner)
    bx0, bx1, bz1 = DIMPLE_BLOCK
    ibn = []
    for q in ib:
        ibn.append(q)
        if q == (369.8, -30.85 + WT):
            ibn += [(bx0, -30.85 + WT), (bx0, bz1), (bx1, bz1), (bx1, -30.85 + WT)]
    assert len(ibn) == len(ib) + 4
    inner_n = ibn + [(x_r + WT, 30.0)]
    cut = [MS.prism(inner, -WO + WT + 1.0, WO - WT), MS.prism(inner_n, -WO + WT, -WO + WT + 1.02)]
    unions = []
    # magazine well liner (sheet walls round the opening, up to Z -11)
    # well liner: side/front walls down into the bottom sheet; the rear wall stops inside the sheet above the ledge
    # opening = magazine thickness + 1.0 (spec magazine_well), liner walls 1.0 (R32: magazine 26.0)
    mh = float(SPEC.key["magazine"]["thickness"]) / 2 + 0.5
    unions.append(MS.box(368.8, 433.0, -(mh + 1.0), mh + 1.0, -30.3, -11.0))
    unions.append(MS.box(367.8, 368.85, -(mh + 1.0), mh + 1.0, -29.0, -11.0))
    post = []
    late = []                       # detail r2b: cut after the bevel passes (PartDef.post_cutters)
    post += well_cutters(mh)                                                           # R51: well, pocket, ramp
    # ejection port (right wall only), R1 corners
    # detail r2b: ONE opening from the cover's skirt step to X 452 (side panel at 16x: a black band Z ~6.5-10.5 runs
    # from the step's slant at X ~312 forward, the selector lever's top edge forming its lower edge; c1: the slot starts
    # at that slant, one rear end): the wall is cut from the step line (0.3 behind the skirt edge, hidden by it) up to
    # BAND_TOP_Z, and full height (Z 3-17) from PORT_X0 (the L3 port scan at Z 10 finds the opening there); the
    # skirt above (CUT_SKIRT_Z 9.6, lifted to CUT_LOW_Z at PORT_X0, rise to CUT_TOP_Z at CUT_RISE_X) closes it
    port = np.array([(step_x(3.0) - 0.3, 3.0), (452.0, 3.0), (452.0, 17.0), (PORT_X0, 17.0), (PORT_X0, BAND_TOP_Z),
                     (step_x(BAND_TOP_Z) - 0.3, BAND_TOP_Z)], float)
    port = G.fillet(port, 1.0, 3, radii=[0.6, 1.0, 1.0, 0.6, 0.6, 0.0])
    post.append(MS.prism(port, -24.0, -WO + WT + 0.85))          # through the whole 1.0 wall
    # selector pivot hole (right wall), trigger slot (bottom)
    post.append(MS.cylinder((282.8, -24.0, -7.8), (282.8, -18.9, -7.8), 3.2, 32))
    post.append(MS.box(301.5, 329.0, -3.25, 3.25, -40.0, -27.0))
    # barrel bore through the front trunnion (barrel r 7.5 + gap)
    post.append(MS.cylinder((CHAMBER_X, 0, 0), (490.0, 0, 0), 7.5 + GAP, 48))     # R51: chamber mouth from 431
    # stage-7: the bolt head's bore through the trunnion's rear (the bolt rides into it to the breech)
    post.append(MS.cylinder((TRUNNION_X0 - 1.0, 0, 0), (BOLT_X[1] + 0.4, 0, 0), BOLT_BORE_R, 48))
    # lower handguard tenon pocket in the front face (X 484.0 - 485.3)
    post.append(lower_handguard_tenon(GAP, 483.98, 490.0))
    post.append(lower_handguard_tenon(1.5, 484.75, 490.0))      # mouth relief: room for the tenon's root fillet
    # side dimples, detail r1: flat-bottomed stadium-like oval with a crisp ~2 mm rim roll (c1, q34 and the side view
    # draw a sharp rim highlight, not the old soft cosine lens)
    # The form build's inner bumps never survived (the interior cut, applied after the unions, removed them), so the
    # 1.0-deep recess left a zero-thickness point; with the flat floor that became a see-through sliver. Re-ordering
    # the booleans changed the receiver's triangulation and the 0.3 bevel then overshot into three butt gaps, so the
    # recess is 0.85 deep (centre 0.9) and the sheet keeps a floor; the inner face stays flat (unseen).
    for s in (-1, 1):
        # r2b: right side DIMPLE_DEPTH on the inner block, left side as before (0.85, no block); cut after the bevels
        # (late): the deeper rim roll put edges past the 0.3 pass's 35 deg limit and its arc miter threw vertices
        if LOD.LEVEL < 2:          # LOD2: pressed recesses are painted, not modelled (sub-pixel relief at 6.7 m)
            late.append(dimple_crisp((397.0, s * WO, -17.0), s, 9.0, 5.5, DIMPLE_DEPTH if s < 0 else 0.85, inner=False))
    # detail r1: pressed teardrop recess under the port's rear half (c1: wide rounded top just under the port edge,
    # tapering to a rounded point; side view X ~365-380 under the port edge), 0.6 deep in the 1.0 sheet
    if LOD.LEVEL < 2:
        post.append(MS.prism(teardrop_outline(TEAR_TOP), -WO - 1.0, -WO + 0.6))
    # detail r2: c1 draws the drop as a CUTOUT (dark inside, judge: 'B's cutout'): a through hole 1.3 inside the
    # pressed rim, so the rim keeps its highlight and the interior (carrier flank, rail) shows dark through it
    if TEAR_RIM > 0 and LOD.LEVEL < 2:
        post.append(MS.prism(teardrop_outline(TEAR_TOP, TEAR_RIM), -WO - 1.0, -WO + WT + 0.5))
    # pressed groove (left wall only, as the true-left panel draws it)
    if LOD.LEVEL < 2:
        post.append(MS.capsule((421.5, WO + 1.5 - 0.8, -20.0), (458.5, WO + 1.5 - 0.8, -20.0), 1.5, 20, 4))
    # flush pin, right: inset ring 0.3 deep
    # detail r2b: c1 / side draw a small domed screw head (judge: 'small domed screw', ours 'a flat engraved ring'):
    # the flush ring is replaced by a domed head (PIN_HEAD, rivets object) whose rolled foot gives the dark ring
    # (no ring cut: on the flat wall its fan triangles drew radial shading streaks round the pin in the ROUGH LOOK)
    # trigger-guard flange relief is a separate part; the rear-section bottom meets the grip
    # 0.3 pass angle limit 35 (form fix round 2): at 40 the limit sat inside a cluster of 39.4-40.0 deg edges (the
    # bottom kink at X 479.8), half of a corner's edges were bevelled, and Blender 5.2's arc outer miter with overlap
    # clamping threw 36 corner vertices to ~1e21 (the guard fell back to a sharp miter). 35 keeps the 1.6 pass's 30 deg
    # ring steps out and takes the whole kink.
    rec = [(1.6, 3, "W", pred_bend_receiver), (0.3, 1, 35.0)]
    return PartDef("receiver", solids, cutters=cut + post, unions=unions, cls="S-bend", recipe=rec, post_cutters=late,
                   joint={"type": "fixed", "parent": None})


def well_cutters(mh):
    """R51 cutters (frame M prisms across Y) from the magazine's swept envelopes (rifle_magfit):
    - well (|Y| <= mh): the opening's rear edge X 368.8, its front = the body's swept front spine + 0.06 (seam) up to
      the trunnion's underside over the magazine's front zone (body roof), then back to the trunnion's rear face;
    - lug band (|Y| <= lug + 0.2): the lug body's pocket; tab band (|Y| <= tab + 0.2): the hook tab's channel up the
      trunnion's lower rear face, its ledge, the pocket and its roof (the front top stop);
    - the feed ramp (|Y| <= RAMP[2]) on the trunnion's rear face, from above the pocket roof up to the chamber mouth."""
    x_back = TRUNNION_X0 - 0.1
    prof, roof = MF.well_front_profile()
    rear = MF.well_rear_profile()          # the sheet behind the opening, cut back along the rock's tilted rear face
    xr = rear[-1][0]                         # the opening's rear edge below the ledge sheet
    P = [(xr, prof[0][1])] + list(prof) + [(prof[-1][0], roof), (x_back, roof), (x_back, -4.0), (368.8, -4.0)]
    P += [(368.8, rear[0][1] + 0.5)] + [q for q in rear]
    out = [MS.prism(G.ccw(np.array(P, float)), -mh, mh)]
    lug, tab, roof_t = MF.pocket_profile()
    bands = [(lug, MF.LUG_HW + MF.C_LUG, lug[-1][1]), (tab, MF.TAB_HW + MF.C_LUG, roof_t)]
    if LOD.LEVEL >= 2:              # LOD2: one pocket (the tab band's envelope, which holds the lug's, at the wider of
        #                             the two widths): inside the trunnion, never seen at 6.7 m+; LOD budget
        bands = [(tab, max(MF.LUG_HW, MF.TAB_HW) + MF.C_LUG, roof_t)]
    for pr, hw, top in bands:
        P = [(x_back, pr[0][1])] + list(pr) + ([(pr[-1][0], top)] if top > pr[-1][1] + 1e-6 else []) + [(x_back, top)]
        out.append(MS.prism(G.ccw(np.array(P, float)), -hw, hw))
    if LOD.LEVEL >= 2:              # LOD2 (6.7 m+): the ramp is inside, under the carrier: never seen; LOD budget
        return out
    (ax, az), (bx, bz), rhw = RAMP
    out.append(MS.prism(G.ccw(np.array([(ax, az), (bx, bz), (bx + 2.0, -4.0), (ax, -4.0)], float)), -rhw, rhw))
    return out


SKIRT_STEP = ((302.3, 0.8), (313.2, 10.3))     # the cover's traced skirt step (rear deep skirt -> raised skirt)
CUT_SKIRT_Z = 9.6               # r2b: raised skirt's bottom (trace 10.3-10.6; 0.4 below the L3 port scan line Z 10)
BAND_TOP_Z = 9.2                # r2b: wall cut top behind PORT_X0 (just under the skirt bottom: one visible edge)
PORT_X0 = 336.5                 # r2b: full-height port from here (spec 338 +- 2.43; L3 scan at Z 10)
CUT_LOW_Z = 12.3                # skirt cutout's low part (the handle stem, Z <= 11.85, passes under it)
CUT_LOW_SLANT = ((333.9, CUT_SKIRT_Z), (337.4, CUT_LOW_Z))   # r2b: slanted lift of the skirt edge at PORT_X0
CUT_RISE_X = (372.0, 378.5)     # r2b: back to r1's rise (side panel: the cover lip curves up at X ~375-380)


def step_x(z):
    (x0, z0), (x1, z1) = SKIRT_STEP
    return x0 + (z - z0) * (x1 - x0) / (z1 - z0)


# detail r2b: 1.5 deep (spec 1.0: proposal) on a 1.0 inner block behind the wall (DIMPLE_BLOCK: X0, X1, top Z)
DIMPLE_DEPTH = 1.5
DIMPLE_BLOCK = (385.0, 409.0, -9.0)
REAR_ROLL = 0.6                    # form realism round: crisp sheet edge (detail r2b 1.5: a soft rolled corner)
PIN_HEAD = (1.75, 0.6)             # detail r2b: domed head of the right flush pin (r, proud)
TEAR_TOP = (372.0, 2.3)            # teardrop recess: top-centre (X, Z), frame M (r2b: 1.8 -> 2.3, c1: the notch hangs
                                   # from the port's bottom edge line)
TEAR_RIM = 0.9                     # pressed rim width around the through cutout (r2 1.3; r2b: c1 draws a thin rolled lip)
TEAR_SCALE = 1.1                   # r1i1 read 20 % small against c1 (fillets shrink the outline)


# drop shape (r1; c1 at 9x confirms it: flat top on the port's bottom line, straight rear side, broad round bottom
# bulging toward the muzzle); the r1 judge's 'shallow shield-shaped engraved outline' was its DEPTH: r2b shows a dark
# interior through it (CAVITY_Z_LOW, RAIL_GAP_X) and a thinner lip
TEAR_BASE = np.array([(-4.2, 0.0), (4.4, 0.0), (4.4, -3.5), (3.2, -6.6), (0.6, -8.3), (-2.2, -7.6), (-3.9, -5.0)])
TEAR_RADII = [1.0, 1.0, 2.5, 2.5, 2.5, 2.5, 2.5]


def teardrop_outline(top, inset=0.0):
    """c1 'hole' under the port: ~9.6 wide, 9.3 tall drop: flat top just under the port edge, straight rear side,
    broad rounded bottom bulging toward the muzzle (r1i2: the first, pointed shield read too sharp). inset > 0: the
    same drop offset inward BEFORE filleting (offsetting the filleted curve by more than its 1.0 corner radius made
    self-intersecting loops and a non-manifold receiver)."""
    x0, z0 = top
    P = G.ccw(TEAR_BASE * TEAR_SCALE + (x0, z0))
    radii = TEAR_RADII
    if inset > 0:
        P = G.offset(P, -inset)
        radii = [max(0.5, r - inset) for r in TEAR_RADII]
    return G.fillet(P, 2.0, 3, radii=radii)


def dimple_crisp(c, side, ax, az, depth, inner=False, n_exp=2.6, t0=0.62):
    """Pressed oval dimple with a flat bottom and a crisp rim roll: superellipse outline (semi-axes ax, az, exponent
    n_exp: flatter top / bottom like the drawn stadium-like oval), full depth inside t0 of the radius (centre 6 %
    deeper so the floor has one deepest point), cosine roll to zero slope at the rim. inner=False -> the cutter (flat
    face 2 mm outside the wall); inner=True -> a matching low-res bump (unused: see receiver())."""
    c = np.asarray(c, float)
    if inner:
        nu, ts = 20, [0.0, t0, 0.81, 1.0]
    else:
        nu, ts = 28, [0.0, t0, 0.72, 0.81, 0.9, 0.96, 1.0]
    th = np.linspace(0, 2 * math.pi, nu, endpoint=False)
    cu, su = np.cos(th), np.sin(th)
    ex = np.sign(cu) * np.abs(cu) ** (2.0 / n_exp)
    ez = np.sign(su) * np.abs(su) ** (2.0 / n_exp)
    m = Mesh()
    flat_off = side * (2.0 if not inner else 0.6)
    dish, flat = [], []
    for j, t in enumerate(ts[1:], 1):
        f = 1.0 if t <= t0 else 0.5 * (1 + math.cos(math.pi * (t - t0) / (1.0 - t0)))
        d = depth * f
        x = c[0] + ax * t * ex
        z = c[2] + az * t * ez
        last = j == len(ts) - 1
        dish.append(m.add_verts(np.c_[x, np.full(nu, c[1] - side * d + (side * 0.002 if last else 0.0)), z]))
        flat.append(m.add_verts(np.c_[x, np.full(nu, c[1] + flat_off), z]))
    ctr_d = m.add_verts([[c[0], c[1] - side * depth * 1.06, c[2]]])[0]     # 0.06 dish: one deepest point (L3)
    ctr_f = m.add_verts([[c[0], c[1] + flat_off, c[2]]])[0]
    nr = len(dish)
    for k in range(nu):
        k2 = (k + 1) % nu
        m.face((ctr_d, dish[0][k], dish[0][k2]))
        m.face((ctr_f, flat[0][k2], flat[0][k]))
        for j in range(nr - 1):
            m.face((dish[j][k], dish[j + 1][k], dish[j + 1][k2], dish[j][k2]))
            m.face((flat[j][k2], flat[j + 1][k2], flat[j + 1][k], flat[j][k]))
        m.face((dish[nr - 1][k], flat[nr - 1][k], flat[nr - 1][k2], dish[nr - 1][k2]))
    return m


def dust_cover_parts(x1=454.9 - GAP):
    """Form realism round: the pressed-sheet cover (receiver_right_cover): outer loft, cavity loft and the boxes that
    open it below the lip line and behind X 241 under it (the skirts' rear edge, side trace)."""
    outer = RC.outer_mesh(x1)
    inner = RC.inner_mesh(x1, COVER_I)
    under = MS.box(230.0, x1 + 12.0, -COVER_I, COVER_I, -20.0, RC.Z_BASE)
    rear = MS.box(230.0, 241.0, -30.0, 30.0, -20.0, RC.Z_BASE)
    return outer, [inner, under, rear]


# skirt cutout over the port. Detail r2: a slanted (~47 deg) step from the lifted rear edge (Z 12.3: the handle stem,
# Z <= 11.85 at X 341-348.5 at full travel, passes under it) up to Z 19.2 at X 349-355.5, where the carrier's raised
# Z 19.6 step begins, so the whole opening ahead of the step shows the carrier's lit flank (c1: one long slot,
# slanted rear step, lit carrier bar, dark band under it; side panel: dark slot from X ~355; q34: rise at the selector
# tip). r1 had the rise at X 372-378.5 and the top at 19.2, which left the port's rear third hidden ('only a small
# black notch'). Top: c2 / q34 / the side panel show the opening up to just under the crease (Z ~21-22), c1 lower
# (~40 % of the skirt band kept): held at 19.2, the L3 port-corner limit (17 + 2.43); see spec_proposal.json.
CUT_TOP_Z = 19.2
# detail r2b: the low part (Z 12.3) runs from PORT_X0 to the rise at X 372-378.5 (r1's position, as the side panel
# draws it), now that the band ahead of the skirt step carries the slot's rear part (r2's early rise at X 349-355.5 made
# a separate tall notch behind a black block)


def cover_cut_outline():
    (a, za), (b, zb) = CUT_LOW_SLANT
    P = np.array([(a - (za - 6.0) * (b - a) / (zb - za), 6.0), (452.0, 6.0), (452.0, CUT_TOP_Z),
                  (CUT_RISE_X[1], CUT_TOP_Z), (CUT_RISE_X[0], CUT_LOW_Z), (b, zb)], float)
    return G.fillet(P, 1.0, 4, radii=[0.0, 0.0, 1.0, 1.6, 1.2, 0.8])


def build_dust_cover(coll, offset):
    """Pressed-sheet cover: outer loft minus the cavity (explicit boolean steps), the port cutout and the button hole,
    then a crisp 0.3 break on the cut edges only (pred_cover_cut)."""
    from gunlib import bl
    outer, cav = dust_cover_parts()
    ob = outer.to_object("dust_cover", coll, offset, smooth_deg=40.0)
    bl.boolean_many(ob, cav, "DIFFERENCE", offset=offset)
    bl.clean(ob)
    cuts = [MS.prism(cover_cut_outline(), -30.0, -15.0),                                    # port / skirt cutout
            MS.box(243.0 - 0.15, 251.0 + 0.15, -3.0 - 0.15, 3.0 + 0.15, 11.0, 40.0)]      # spring-guide button hole
    bl.boolean_many(ob, cuts, "DIFFERENCE", offset=offset)
    bl.clean(ob)
    bl.bevel_weighted(ob, 0.3, 1, pred_cover_cut, offset)
    bl.finish(ob)
    bl.weighted_normals(ob)
    ob["gun_part"] = json.dumps({"bone": "body", "class": "S-bend", "slot": "M_AR01_Metal", "spec_id": "dust_cover",
                                 "joint": {"type": "butt", "parent": "receiver", "gap_mm": [0.01, 0.05]},
                                 "recipe": [[0.3, 1, "weighted: cut edges only"]]})
    return ob


def recoil_button() -> PartDef:
    """Recoil spring guide button: squared tab through the hole in the cover's formed rear lip, 1.5 mm proud of the
    lip's centreline slope (the TOP view's small squared tab); its top follows the slope."""
    o = [(243.0, 12.0), (251.0, 12.0), (251.0, RC.centre_top_z(251.0) + 1.5), (243.0, RC.centre_top_z(243.0) + 1.5)]
    o = G.fillet(G.ccw(np.array(o, float)), 1.0, 3)
    return PartDef("recoil_spring_button", [MS.prism(o, -3.0, 3.0)], cls="M-round",
                   recipe=[(0.5, 2, 30.0)], joint={"type": "butt", "parent": "dust_cover", "gap_mm": [0.01, 0.05]})


RIVET_R, RIVET_H = 2.55, 1.0        # c1 draws the heads ~5 mm (spec 4.5 +- the sheet's 1.2 mm px); height kept for the selector sweep
RIVET_SEG = 24                      # stage-7 (G3): 15 deg per segment, the crown's smooth-shaded normals carry the dome
CLIP_AT = (350.0, -25.0)           # c1 draws a wire retainer clip where the side view's dot (350, -25) is


def rivet_head(c, normal, r, h, nseg=8, domed=False) -> Mesh:
    """Button rivet head. domed=False: flat-topped (integration round: a rolled shoulder (0.6 h at 0.93 r) up to a
    flat crown at 0.62 r). domed=True (detail r2b, judge r1 on c1: 'B's rivet heads are domed with highlights, A's
    plain small spheres'; c1 / side draw a low round dome with one bright crown highlight and a dark foot): a steep
    rolled foot and a continuous low dome, so the crown catches the key light."""
    if domed:
        prof = [(0.0, 0.0), (0.0, r), (0.42 * h, 0.93 * r), (0.84 * h, 0.58 * r), (h, 0.0)]   # 3 rings (budget)
    elif nseg > 8:
        # stage-7 (G3 at 24 segments inside the 50k LOD0 ceiling): the flat crown on a straight rolled flank, one ring
        # fewer (4n triangles, was 6n); the 60 deg auto-smooth carries the flank-to-crown roll in the shading
        prof = [(0.0, 0.0), (0.0, r), (h, 0.62 * r), (h, 0.0)]
    else:
        prof = [(0.0, 0.0), (0.0, r), (0.6 * h, 0.93 * r), (h, 0.62 * r), (h, 0.0)]
    return MS.revolve(prof, c, normal, nseg)


def retainer_clip_r2b(at, rw=0.46) -> Mesh:
    """Detail r2b: the wire clip as c1 draws it (judge: 'a raised loop of wire', ours 'a tiny flat hook mark'): a
    long hairpin ~11.6 x 2.6 mm lying along X: round closed end at the rear round the eye (350, -25), the upper leg
    forward ending in a short down-curl, the lower leg a little longer ending in a short up-turn. Wire 0.92 dia, a
    hexagon vertex toward the wall, 0.02 off it (top 0.94 proud: under the rivet crowns for the selector sweep)."""
    x0, z0 = at
    e = 1.3                                            # half height of the loop (wire centre)
    a = np.radians(np.linspace(90.0, 270.0, 9))        # rear round end, top -> bottom
    end = np.c_[x0 + e * np.cos(a), z0 + e * np.sin(a)]
    c = np.radians(np.linspace(90.0, 0.0, 4))[1:]      # upper leg's front down-curl (r 0.6)
    top = np.c_[[x0 + 9.6, x0 + 4.5, x0 + 1.0], [z0 + e] * 3]
    curl = np.c_[x0 + 9.6 + 0.6 * np.cos(c), z0 + e - 0.6 + 0.6 * np.sin(c)]
    bot = np.c_[[x0 + 1.0, x0 + 5.5, x0 + 10.6], [z0 - e] * 3]
    u = np.radians(np.linspace(-90.0, 0.0, 4))[1:]     # lower leg's up-turn (r 0.7)
    turn = np.c_[x0 + 10.6 + 0.7 * np.cos(u), z0 - e + 0.7 + 0.7 * np.sin(u)]
    path2 = np.vstack([curl[::-1], top, end[1:-1], bot, turn])
    y = -(WO + GAP + rw)
    path = np.c_[path2[:, 0], np.full(len(path2), y), path2[:, 1]]
    th = np.radians(90.0 + 60.0 * np.arange(6))
    sec = np.c_[rw * np.cos(th), rw * np.sin(th)]
    return MS.sweep_profile(path, sec, ups=[(0.0, 1.0, 0.0)] * len(path))


def retainer_clip(at, rw=0.45) -> Mesh:
    """Wire retainer clip on the right wall (c1, judge pair 01): an elongated open eye at the rear round the side
    view's dot, a straight leg forward from its bottom and a short up-turn at the front. Wire 0.9 dia lying 0.02 off
    the wall (a hexagon vertex toward the wall), so it stays below the rivet heads under the selector's sweep."""
    x0, z0 = at
    ax, az = 1.8, 1.1                                  # eye (wire centre) semi-axes: c1 draws a long flat loop
    a = np.radians(np.linspace(30.0, 270.0, 15))
    eye = np.c_[x0 + ax * np.cos(a), z0 + az * np.sin(a)]
    leg_end = (x0 + 7.5, z0 - az)
    rh = 0.8
    b = np.radians(np.linspace(-90.0, -10.0, 4))
    hook = np.c_[leg_end[0] + rh * np.cos(b), leg_end[1] + rh + rh * np.sin(b)]
    path2 = np.vstack([eye, [[x0 + 3.0, z0 - az]], [leg_end], hook[1:]])
    y = -(WO + GAP + rw)
    path = np.c_[path2[:, 0], np.full(len(path2), y), path2[:, 1]]
    th = np.radians(90.0 + 60.0 * np.arange(6))
    sec = np.c_[rw * np.cos(th), rw * np.sin(th)]
    return MS.sweep_profile(path, sec, ups=[(0.0, 1.0, 0.0)] * len(path))


DPLATE = (12.4, 4.4, 0.75, 0.3)    # detent plate: length, height, proud, edge roll


def detent_plate(at) -> Mesh:
    """DETAIL FIX: a stamped spring-steel detent plate lying on the right wall above the trigger guard (stadium
    12.4 x 4.4, 0.75 proud, edges rolled 0.3, a faint crown), its rear end round the side view's dot (350, -25). It
    stays under the rivet crowns (the selector lever's sweep passes over it)."""
    x0, z0 = at
    L, Hh, t, e = DPLATE
    xa, xb = x0 - Hh / 2 + 0.4, x0 - Hh / 2 + 0.4 + L
    y0 = -(WO + GAP)
    rings = []
    for dy, ins in ((0.0, 0.0), (t - e, 0.0), (t - e * 0.3, e * 0.29), (t, e)):
        P = G.rounded_rect(xa + ins, xb - ins, z0 - Hh / 2 + ins, z0 + Hh / 2 - ins, Hh / 2 - ins, 5)
        rings.append(np.c_[P[:, 0], np.full(len(P), y0 - dy), P[:, 1]])
    return MS.loft(rings)


SLING_LOOP = (236.6, 2.2, 2.7, 0.75, 25.0)   # centre X, leg Z, loop radius, wire radius, tilt out from the wall (deg)


def sling_loop_rear() -> Mesh:
    """DETAIL FIX: the rear sling loop on the rear trunnion's right side (c1 top-left): a D of 1.5 mm wire, its straight
    leg lying 0.02 off the trunnion face, the bow tilted SLING_LOOP[4] deg out from the wall; inside the side
    silhouette (the side views show no bump there)."""
    xc, zl, rl, rw, tilt = SLING_LOOP
    y_leg = -(WO + GAP + rw)
    tl = math.radians(tilt)
    w = np.array([0.0, -math.sin(tl), math.cos(tl)])        # the bow's 'up' in its tilted plane
    base = np.array([xc, y_leg, zl])
    pts = [base + np.array([rl * math.cos(ph), 0.0, 0.0]) + rl * math.sin(ph) * w
           for ph in np.linspace(0.0, math.pi, 11)]
    pts += [base + np.array([-rl + 2 * rl * k / 4.0, 0.0, 0.0]) for k in range(1, 4)]   # the straight leg back
    path = np.array(pts)
    nrm = np.cross([1.0, 0.0, 0.0], w)
    th = np.radians(90.0 + 60.0 * np.arange(6))
    sec = np.c_[rw * np.cos(th), rw * np.sin(th)]
    return MS.sweep_profile(path, sec, ups=[tuple(nrm)] * len(path), closed_path=True)


def rivets() -> PartDef:
    r = SPEC.feature("receiver", "rivets_right")["XZ"]
    l = SPEC.feature("receiver", "rivets_left")["XZ"]
    rng = np.random.default_rng(7)
    sol = []
    for (x, z) in r:
        h = RIVET_H + rng.uniform(-0.1, 0.1)
        if (x, z) == CLIP_AT:
            continue
        # DETAIL FIX (user checklist 5): FLAT-TOPPED rivet heads (real pattern; r2b: domed)
        # stage-7 fix round (craft review item 8, G3 'facet angle <= 7.5 deg on rounds at LOD0'): 8 -> RIVET_SEG
        # segments (the 8-sided crowns read as octagons at 3x and at 35 cm first person); LOD1 12, LOD2 6 (gunlib.lod)
        sol.append(rivet_head((x, -WO - GAP, z), (0, -1, 0), RIVET_R, h, RIVET_SEG, domed=False))
    for (x, z) in l:
        h = RIVET_H + rng.uniform(-0.1, 0.1)
        sol.append(rivet_head((x, WO + GAP, z), (0, 1, 0), RIVET_R, h, RIVET_SEG, domed=False))
    # DETAIL FIX (user checklist 5): the stamped DETENT PLATE above the trigger guard (r2b: a floating wire hairpin)
    sol.append(detent_plate(CLIP_AT))
    # DETAIL FIX (user checklist 5): the rear sling loop on the rear trunnion (c1 draws it at the receiver's rear top)
    sol.append(sling_loop_rear())
    # detail r2b: domed head of the right flush pin inside its ring (c1 / side: a small domed screw)
    # integration r2b: c1 draws this pin as a small ring round a dark hole (a hollow pin end), not a dome (judge r2b:
    # "A has a small round hole ... B has a rivet"): a ring 0.45 proud, r 0.95-1.75, the wall showing in its centre
    sol.append(MS.tube((388.0, -WO - GAP, -8.0), (388.0, -WO - GAP - 0.45, -8.0), 0.95, PIN_HEAD[0], 16))
    # (detail round 2's crown studs are gone: form realism round, real covers and the sheet have none)
    return PartDef("rivets", sol, cls="none", recipe=[], wn=False, smooth_deg=60.0,
                   joint={"type": "butt", "parent": "receiver", "gap_mm": [0.01, 0.05]})


# ======================================================================================== bolt carrier (moving)
CARRIER_TRAVEL = 444.25 - (338.0 + 3.0)          # handle stops at X 341 (4.5 ahead of PORT_X0)


CARRIER_X = (346.0, 450.0)
# stepped rear (side, XZ): the full D section from X 369 (clears the cover's sloped rear end at full travel), Z <= 17
# from 355 (clears it too), Z <= 11.4 from 346 (passes under the spring-guide button, 0.83 mm off the rear wall at
# full travel); the flat flank then fills the port from X 346 (detail r1: no round chrome bolt in the port); detail r2:
# the flank below Z 9.5 is recessed 14.75 mm (CAVITY_*) so the port's lower half reads dark, the upper half a lit bar
CARRIER_STEPS = [(346.0, 11.4), (355.0, 19.6), (369.0, 40.0)]   # r2: middle step 17 -> 19.6 (fills the raised cutout)
HANDLE_Z = (8.0, 17.0)             # tab; its bottom stays 1.2 above the selector lever (Z 6.8) at full travel
KNOB_X = 449.6                     # charging handle centre X (stem X 444.25-451.75; last shape round: the knob is lofted)
STEM_Z = (8.6, 11.85)              # stem in the wall port; passes under the cutout's slanted rear step at full travel
CARRIER_FLAT_Z, CARRIER_TOP_B = 20.0, 9.7     # detail r2 section (top Z 29.7 as before)
# integration (2026-10-05): the recess floor stops at Y -8.5 (was -4.0): deeper, it opened into the chamber pocket round
# the barrel end (r 7.8) and the barrel showed through the port (side L2 'barrel' max 175 px); still 10.25 mm deep
CAVITY_X, CAVITY_Z, CAVITY_Y = (346.0 - 1.0, 443.0), (2.5, 9.5), 8.5     # flank recess (carrier frame at rest)
# detail r2b: the recess also runs down to the carrier bottom, and the right guide rail has a gap behind the notch
# (RAIL_GAP_X), so the notch under the port shows a dark interior instead of a lit face 1 mm behind the wall
CAVITY_Z_LOW = -4.5
RAIL_GAP_X = (361.0, 383.0)


BOLT_R = 7.6                       # stage-7: the rotating bolt (real pattern: ~15 mm body), on the bore axis
BOLT_X = (395.0, 433.4)            # at rest: from inside the carrier's rear section to 0.4 short of the barrel's breech
CORE_X = 397.5                     # the carrier's full section ends here; ahead of it only its upper body (Z >= CORE_Z)
CORE_Z = 9.0                       # (1.0 over the trunnion's raised top; the bolt hangs below it in the open)
EXTRACTOR_DEG = 40.0               # the extractor's centre angle above the right horizontal (it shows through the port,
#                                    whose bottom edge is Z 3: real bolts carry it high on the right of the head)


def bolt_parts():
    """Stage-7 fix round: the bolt (cylinder r BOLT_R, crisp face with the case-head recess and the firing-pin hole)
    and the extractor (a flat claw plate 0.3 proud on the bolt's upper right, its claw hooked over the face's rim)."""
    bolt = MS.cylinder((BOLT_X[0], 0, 0), (BOLT_X[1], 0, 0), BOLT_R, 24)       # (seen through the port only: 24)
    a0 = math.radians(EXTRACTOR_DEG)
    da = math.radians(16.0)

    def plate(r0, r1, half):
        aa = np.linspace(a0 - half, a0 + half, 5)
        outer = np.c_[-r1 * np.cos(aa), r1 * np.sin(aa)]
        inner = np.c_[-r0 * np.cos(aa[::-1]), r0 * np.sin(aa[::-1])]
        return np.vstack([outer, inner])
    ext = MS.prism(plate(BOLT_R - 0.6, BOLT_R + 0.3, da), 409.0, BOLT_X[1] + 0.15, "YZ")
    claw = MS.prism(plate(BOLT_R - 1.3, BOLT_R + 0.3, math.radians(11.0)), BOLT_X[1] - 0.9, BOLT_X[1] + 0.15, "YZ")
    cut = [MS.cylinder((BOLT_X[1] - 0.9, 0, 0), (BOLT_X[1] + 1.0, 0, 0), 5.7, 20),       # case-head recess 0.9 deep
           MS.cylinder((BOLT_X[1] - 4.0, 0, 0), (BOLT_X[1] + 1.0, 0, 0), 1.0, 8)]        # firing-pin hole
    return [bolt, ext, claw], cut


def bolt_carrier() -> PartDef:
    """Carrier block (flat flank in the port, D-shaped top under the cover crown) with a stepped rear that fills the
    port's visible length; charging handle tab (stem through the port's front end, flat-topped tab with rounded
    outer corners outside). Stage-7: ahead of CORE_X only the carrier's upper body (Z >= CORE_Z) runs forward; the
    rotating bolt with its extractor rides under it (bolt_parts)."""
    # detail r2: flat flanks up to Z CARRIER_FLAT_Z (the flank shows as a flat lit bar through the whole skirt cutout,
    # c1 / c2 / q34), then an elliptical top 2 mm under the new cover crown (receiver_right_cover)
    yc = 18.75
    a = np.linspace(0.0, math.pi, 41)[1:-1]
    top = np.c_[yc * np.cos(a), CARRIER_FLAT_Z + CARRIER_TOP_B * np.sin(a)]
    sec = np.vstack([[[yc, -4.0], [yc, CARRIER_FLAT_Z]], top, [[-yc, CARRIER_FLAT_Z], [-yc, -4.0]]])
    carrier = MS.prism(sec, CARRIER_X[0], CORE_X, "YZ")
    sec_up = np.vstack([[[yc, CORE_Z], [yc, CARRIER_FLAT_Z]], top, [[-yc, CARRIER_FLAT_Z], [-yc, CORE_Z]]])
    upper = MS.prism(sec_up, CORE_X - 0.5, CARRIER_X[1], "YZ")
    bolt, bolt_cut = bolt_parts()
    side = [(CARRIER_X[0], -10.0), (CARRIER_X[1] + 5.0, -10.0), (CARRIER_X[1] + 5.0, 40.0)]
    for i in range(len(CARRIER_STEPS) - 1, -1, -1):
        x, z = CARRIER_STEPS[i]
        side += [(x, z)]
        if i > 0:
            side += [(x, CARRIER_STEPS[i - 1][1])]
    side_prism = MS.prism(G.ccw(np.array(side, float)), -30.0, 30.0)
    # LAST SHAPE ROUND (ruling 3): the REAL charging handle -- a flat stem straight out of the carrier through the slot
    # and a knob on its end bent up, standing HANDLE_OUT mm proud of the receiver wall (real-pattern photos, scratch/
    # realref: ~25 mm out, knob ~9-10 mm, bent up ~25 deg, its top level with the old tab). Round 2's 10 mm collar knob
    # read as a stub. It travels with the carrier (bolt bone); the stem stays in its old Z band (B3: over the selector's
    # top edge Z 8.0 at full travel, under the cover cutout's low edge 12.3)
    stem = MS.prism(G.rounded_rect(444.25, 451.75, STEM_Z[0], STEM_Z[1], 0.75, 3), -29.5, -18.5)
    tab = handle_knob()
    # (stage-7: the chamber pocket round the barrel end is gone: the barrel's rear end sits in the trunnion now)
    cut = list(bolt_cut)
    # detail r2: deep recess in the right flank below the lit bar (c1 draws a dark shadow band under the carrier face,
    # q34 a dark gap under it): the port reads as a dark slot instead of a flush wall-coloured face
    cut.append(MS.prism(G.rounded_rect(CAVITY_X[0], CAVITY_X[1], CAVITY_Z_LOW, CAVITY_Z[1], 0.6, 2), -30.0, -CAVITY_Y))
    # DETAIL FIX (user checklist 5): a LAYERED, stepped carrier flank in the port: under the lit top bar (Z 14.2-20)
    # a second face stepped in 1.1 mm (Z 9.5-14.2), then the deep recess; a 0.8 mm lengthwise groove in the bar
    cut.append(MS.prism(G.rounded_rect(CAVITY_X[0], CAVITY_X[1], CAVITY_Z[1] - 0.5, 14.2, 0.4, 1), -30.0, -(18.75 - 1.1)))
    p = PartDef("bolt_carrier", [carrier], bone="bolt", cls="M-chamfer", cutters=cut,
                unions=[upper] + bolt + [stem, tab], joint={"type": "sliding", "parent": "receiver", "axis_M": [-1, 0, 0],
                                           "travel_mm": round(CARRIER_TRAVEL, 3), "clearance_mm": [0.15, 0.4]},
                recipe=[(0.4, 1, 30.0)])
    p.section_intersect_pre = [side_prism]
    return p


HANDLE_OUT = 24.5                  # knob end proud of the wall (Y -WO - HANDLE_OUT)
KNOB_PATH = ((-25.5, 10.225), (-36.0, 10.225), (-42.6, 13.4))   # quadratic Bezier in YZ at X = KNOB_X (stem -> knob)
KNOB_AX = ((0.0, 3.75), (0.45, 3.85), (0.8, 4.55), (1.0, 4.6))    # section half width along X over the path parameter
KNOB_AZ = ((0.0, 1.62), (0.45, 1.9), (0.8, 3.3), (1.0, 3.45))     # section half thickness across the path


def handle_knob():
    """The charging handle's knob: superellipse sections (exponent 2.6: a pressed flat-sided knob, not a ball) lofted
    along KNOB_PATH (flat out of the stem, then bent up ~26 deg), closed by a domed end (quarter ellipse, 4 rings) whose
    tip reaches Y -WO - HANDLE_OUT."""
    p0, p1, p2 = (np.asarray(q, float) for q in KNOB_PATH)
    ts = np.linspace(0.0, 1.0, LOD.count(11, 5))
    nu = LOD.ring(20)
    ph = np.linspace(0.0, 2.0 * math.pi, nu, endpoint=False)
    e = 2.0 / 2.6
    cu, su = np.cos(ph), np.sin(ph)
    eu, ev = np.sign(cu) * np.abs(cu) ** e, np.sign(su) * np.abs(su) ** e
    rings = []

    def ring_at(c, tan, ax, az):
        n = np.array([-tan[1], tan[0]])           # in YZ, rotated +90 deg: up for a -Y tangent
        if n[1] < 0:
            n = -n
        return np.c_[np.full(nu, KNOB_X) + ax * eu, c[0] + az * ev * n[0], c[1] + az * ev * n[1]]
    for t in ts:
        c = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t * t * p2
        d = 2 * (1 - t) * (p1 - p0) + 2 * t * (p2 - p1)
        d = d / np.linalg.norm(d)
        ax = float(np.interp(t, [a for a, _ in KNOB_AX], [b for _, b in KNOB_AX]))
        az = float(np.interp(t, [a for a, _ in KNOB_AZ], [b for _, b in KNOB_AZ]))
        rings.append(ring_at(c, d, ax, az))
    d = (p2 - p1) / np.linalg.norm(p2 - p1)
    tip_len = abs((-WO - HANDLE_OUT) - p2[0]) / max(abs(d[0]), 1e-6)       # dome length along the end tangent
    ax1, az1 = KNOB_AX[-1][1], KNOB_AZ[-1][1]
    for a in np.radians([25.0, 50.0, 70.0, 84.0]):
        rings.append(ring_at(p2 + d * tip_len * math.sin(a), d, ax1 * math.cos(a), az1 * math.cos(a)))
    return MS.loft(rings)


def receiver_rails() -> PartDef:
    """Carrier guide rails pressed into the inner walls (below the port, X 262-452): the carrier's lateral guide,
    0.25 mm per side."""
    # (stage-7: the rails end GAP short of the trunnion's raised block, TRUNNION_UP_X)
    xe = TRUNNION_UP_X - GAP
    sol = [MS.box(262.0, xe, 19.0, WO - WT - GAP, -4.6, -1.0),
           MS.box(262.0, RAIL_GAP_X[0], -(WO - WT - GAP), -19.0, -4.6, -1.0),
           MS.box(RAIL_GAP_X[1], xe, -(WO - WT - GAP), -19.0, -4.6, -1.0)]       # r2b: gap behind the notch
    return PartDef("receiver_rails", sol, cls="M-chamfer", recipe=[(0.2, 1, 30.0)],
                   joint={"type": "butt", "parent": "receiver", "gap_mm": [0.01, 0.05]})


PADDLE_HW, PADDLE_RIB_HW = 5.0, 1.6


def mag_catch() -> PartDef:
    P = prof("mag_catch", 0.4)
    P = G.clip_x(G.clip_y(P, None, -34.9), 355.45, 368.3)
    cx, cz = CATCH_PIVOT
    tongue = MS.prism(G.clip_y(P, -54.0, None), -3.5, 3.5)
    # LAST SHAPE ROUND (ruling 5): the real-pattern paddle (scratch/realref akbuilder_mag_catch_*.jpg: a stamped flat
    # paddle with a pressed rib down its middle): the traced side outline (the flared lower end) is the centre RIB
    # (+-RIB_HW), and the paddle's two wings are the outline pulled back 2.0 mm from its front edge and 1 mm from its
    # ends (offset 1.0 in, shifted 1.0 rearward), so the front reads as a pressed plate with a raised rib. A 13 mm
    # paddle was tried first: the 3/4 panel's paddle is the 10 mm one (q34 residual unexplained), so the width stays
    Pp = G.clip_y(P, None, -54.0)
    # STAGE-7 FIX ROUND (craft review item 5: 'a melted chrome lump, a T / Y-section wedge with bent normals'): the
    # rib + pulled-back wings made a T section whose many near-coplanar faces smoothed into one blob. The paddle is
    # now ONE flat stamped plate (the traced side outline, PADDLE_HW each side) with crisp 0.3 edges and flat-shaded
    # faces (wn off, sharp at 30 deg), on the tongue as before; finish: satin bluing (rifle_surface)
    paddle = MS.prism(Pp, -PADDLE_HW, PADDLE_HW)
    # top cut to an arc about the pivot (r 15.0): rotation-invariant clearance under the flange
    r = 15.0
    arch = np.vstack([[[cx + r, cz], [cx + 40, cz], [cx + 40, cz + 40], [cx - 40, cz + 40], [cx - r, cz]],
                      G.arc(cx, cz, r, 180, 0, 49)[1:-1]])
    cut = [MS.prism(G.ccw(arch), -6.0, 6.0), ycyl(cx, cz, 1.5 + 0.2, -6, 6, 20)]
    # R51: the NOSE under the magazine's rear lug: in front of the notch (MF.CATCH_NOTCH_X) the top is an arc about the
    # pin (r MF.CATCH_NOSE_R, rotation-invariant: the release never lifts the magazine); the notch's back wall stands
    # 0.2 behind the lug's rear face
    rn = MF.CATCH_NOSE_R
    a0 = math.degrees(math.acos((MF.CATCH_NOTCH_X - cx) / rn))
    nose = np.vstack([G.arc(cx, cz, rn, a0, 20.0, 12), [[cx + 20.0, cz + 4.0], [cx + 20.0, cz + 30.0],
                                                         [MF.CATCH_NOTCH_X, cz + 30.0]]])
    cut.append(MS.prism(G.ccw(nose), -6.0, 6.0))
    return PartDef("mag_catch", [tongue], unions=[paddle], cutters=cut, bone="mag_release", cls="S-cut",
                   recipe=[(0.3, 1, 30.0)], wn=False, smooth_deg=30.0,
                   joint={"type": "hinge", "parent": "receiver", "pivot_M": [cx, 0, cz], "axis_M": [0, -1, 0],
                          "range_deg": [0.0, 10.0], "direction": "+ = top rearward (release)",
                          "clearance_mm": [0.1, 0.3]})


# ======================================================================================== module interface
OBJECTS = ('receiver', 'dust_cover', 'recoil_spring_button', 'rivets', 'receiver_rails', 'bolt_carrier', 'mag_catch')            # registry keys built here (rifle_parts.ORDER)
CLOSEUPS = ('c1', 'c2', 'q34')          # sheet panels that are this part's shape authority (rifle_detail.py)


def build(spec, ctx):
    """Build this module's objects into ctx (gunlib.parts.BuildCtx). Returns {registry key: [objects]}; keys that
    ctx.only excludes come back empty. `spec` is the rifle GunSpec (the same object as rifle_common.SPEC)."""
    return {k: ctx.make(k, f) for k, f in (("receiver", receiver), ("dust_cover", build_dust_cover), ("recoil_spring_button", recoil_button), ("rivets", rivets), ("receiver_rails", receiver_rails), ("bolt_carrier", bolt_carrier), ("mag_catch", mag_catch),)}
