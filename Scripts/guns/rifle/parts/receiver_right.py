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
"""
from __future__ import annotations

import json
import math

import numpy as np

from rifle_common import SPEC
from gunlib import geo2d as G
from gunlib import mesh as MS
from gunlib.mesh import Mesh
from gunlib.parts import PartDef
from rifle_parts import GAP, WO, WT, COVER_O, COVER_I, LEDGE, ledge_z, prof, lower_handguard_tenon
from rifle_parts2 import CATCH_PIVOT, ycyl

from parts import receiver_right_cover as RC  # noqa: E402


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


def pred_cover_bend(mid, d, n1, n2, dih):
    """Dust cover, one weighted pass (1.2 mm base): the rear end wall's pressed bend into crown and skirts gets
    1.0; every other sharp edge (cut edges, port, hole) gets 0.21 (0.25 mm land)."""
    if dih < 40:
        return 0.0
    if mid[0] > 454.5 and abs(n1[0]) + abs(n2[0]) > 0.9:
        return 0.0          # detail r2: the front end face butts on the rear sight block (unseen): no bevel ring
    if mid[0] < 272 and mid[2] > 11.5 and (abs(n1[0]) > 0.35) != (abs(n2[0]) > 0.35):
        return 1.0
    return 0.21


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
    # interior: 1.0 mm walls, rear wall, front trunnion solid from X 452; open top (closed by the cover)
    ib = [(x_r + WT, -34.78 + WT), (250.98, -34.78 + WT), (250.98, ledge_z(250.98) + WT)]
    ib += [(x, z + WT) for x, z in LEDGE if 250.98 < x < 369.8]
    ib += [(369.8, ledge_z(369.8) + WT), (369.8, -30.85 + WT), (431.0, -30.85 + WT), (431.0, -29.52 + WT),
           (447.0, -29.3 + WT), (452.0, -29.05 + WT)]
    inner = ib + [(452.0, 30.0), (x_r + WT, 30.0)]
    cut = [MS.prism(inner, -WO + WT, WO - WT)]
    unions = []
    # magazine well liner (sheet walls round the opening, up to Z -11)
    # well liner: side/front walls down into the bottom sheet; the rear wall stops inside the sheet above the ledge
    # opening = magazine thickness + 1.0 (spec magazine_well), liner walls 1.0 (R32: magazine 26.0)
    mh = float(SPEC.key["magazine"]["thickness"]) / 2 + 0.5
    unions.append(MS.box(368.8, 433.0, -(mh + 1.0), mh + 1.0, -30.3, -11.0))
    unions.append(MS.box(367.8, 368.85, -(mh + 1.0), mh + 1.0, -29.0, -11.0))
    post = []
    post.append(MS.box(368.8, 432.0, -mh, mh, -45.0, -5.0))                           # well opening + bore
    # ejection port (right wall only), R1 corners
    # detail r2: stepped rear edge: full height from X 346 (the carrier's rear at rest), only Z >= PORT_STEP_Z over X
    # 338-346 where the handle stem stops at full travel (stem Z >= 8.6): the wall hides the empty space behind the
    # carrier, so the port reads as one slot with a slanted rear (c1) instead of opening on a black block
    port = G.fillet(np.array([(PORT_STEP_X, 3.0), (452.0, 3.0), (452.0, 17.0), (338.0, 17.0), (338.0, PORT_STEP_Z),
                              (PORT_STEP_X, PORT_STEP_Z)], float), 1.0, 3, radii=[1.0, 1.0, 1.0, 1.0, 1.0, 0.5])
    post.append(MS.prism(port, -24.0, -WO + WT + 0.85))          # through the whole 1.0 wall
    # selector pivot hole (right wall), trigger slot (bottom)
    post.append(MS.cylinder((282.8, -24.0, -7.8), (282.8, -18.9, -7.8), 3.2, 32))
    post.append(MS.box(301.5, 329.0, -3.25, 3.25, -40.0, -27.0))
    # barrel bore through the front trunnion (barrel r 7.5 + gap)
    post.append(MS.cylinder((450.0, 0, 0), (490.0, 0, 0), 7.5 + GAP, 48))
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
        post.append(dimple_crisp((397.0, s * WO, -17.0), s, 9.0, 5.5, DIMPLE_DEPTH, inner=False))
    # detail r1: pressed teardrop recess under the port's rear half (c1: wide rounded top just under the port edge,
    # tapering to a rounded point; side view X ~365-380 under the port edge), 0.6 deep in the 1.0 sheet
    post.append(MS.prism(teardrop_outline(TEAR_TOP), -WO - 1.0, -WO + 0.6))
    # detail r2: c1 draws the drop as a CUTOUT (dark inside, judge: 'B's cutout'): a through hole 1.3 inside the
    # pressed rim, so the rim keeps its highlight and the interior (carrier flank, rail) shows dark through it
    if TEAR_RIM > 0:
        post.append(MS.prism(teardrop_outline(TEAR_TOP, TEAR_RIM), -WO - 1.0, -WO + WT + 0.5))
    # pressed groove (left wall only, as the true-left panel draws it)
    post.append(MS.capsule((421.5, WO + 1.5 - 0.8, -20.0), (458.5, WO + 1.5 - 0.8, -20.0), 1.5, 20, 4))
    # flush pin, right: inset ring 0.3 deep
    post.append(MS.tube((388.0, -WO - 1.0, -8.0), (388.0, -WO + 0.3, -8.0), 1.45, 1.75, 20))
    # trigger-guard flange relief is a separate part; the rear-section bottom meets the grip
    # 0.3 pass angle limit 35 (form fix round 2): at 40 the limit sat inside a cluster of 39.4-40.0 deg edges (the
    # bottom kink at X 479.8), half of a corner's edges were bevelled, and Blender 5.2's arc outer miter with overlap
    # clamping threw 36 corner vertices to ~1e21 (the guard fell back to a sharp miter). 35 keeps the 1.6 pass's 30 deg
    # ring steps out and takes the whole kink.
    rec = [(1.6, 3, "W", pred_bend_bottom), (0.3, 1, 35.0)]
    return PartDef("receiver", solids, cutters=cut + post, unions=unions, cls="S-bend", recipe=rec,
                   joint={"type": "fixed", "parent": None})


PORT_STEP_X, PORT_STEP_Z = 346.0, 8.2      # ejection port rear step (detail r2)
DIMPLE_DEPTH = 0.85                # recess depth (spec 1.0); the 1.0 sheet keeps a 0.1-0.15 floor, no inner bump
TEAR_TOP = (372.0, 1.8)            # teardrop recess: top-centre (X, Z), frame M
TEAR_RIM = 1.3                     # detail r2: pressed rim width around the through cutout
TEAR_SCALE = 1.1                   # r1i1 read 20 % small against c1 (fillets shrink the outline)


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


def dust_cover() -> PartDef:
    """Smooth stamped cover: semicircular crown (R 21.75) on short skirts, closed rounded rear end, open front
    tucked under the rear sight block, right skirt cut out over the port, button hole at the rear top."""
    zc = 32.7 - COVER_O                      # crown centre height 10.95
    x0, x1 = 239.4, 454.9 - GAP
    rear = [(241.5, 13.5), (245.0, 20.1), (250.0, 22.6), (255.0, 25.6), (260.0, 29.3), (265.0, 32.1), (268.5, 32.7)]
    rear_s = open_chaikin([(x0, 10.6), (x0, 11.6)] + rear + [(280.0, 32.7)], 2)   # r2: 2 iters (the denser section x rear grid)
    rear_s = rear_s[rear_s[:, 0] <= 268.6]
    # skirt bottom (trace): deep at the rear (Z 0.75 to X 302.3), a slanted step up to 10.6 at X 313-314
    bottom = [(241.0, 9.6), (241.0, 0.75), (302.3, 0.8), (313.2, 10.3), (314.4, 10.6)]
    side = bottom + [(x1, 10.6), (x1, 32.7), (268.6, 32.7)] + [tuple(q) for q in rear_s[::-1] if q[1] > 10.7]
    side_s = G.fillet(G.ccw(G.dedupe(np.array(side, float))), 1.0, 3)
    off = G.offset(side_s, -WT)
    rp = off[(off[:, 0] < 268.0) & (off[:, 1] > 11.8) & (off[:, 0] > 239.0)]
    # CCW order runs bottom -> front -> top -> rear: the rear points come top-first; keep that run in order
    rp = rp[np.argsort(-rp[:, 1])]
    # open at the bottom and below Z 11.6 at the rear (the skirts pass outside the receiver's rear wall)
    side_in = np.vstack([[[230.0, -5.0], [x1 + 10, -5.0], [x1 + 10, 32.7 - WT]], [[268.5, 32.7 - WT]], rp,
                         [[rp[-1, 0], 11.6], [230.0, 11.6]]])
    # detail r2: shouldered section (vertical skirts, deep lengthwise crease, fuller elliptical crown) instead of the
    # plain semicircle (receiver_right_cover.py); it contains the old section, so every clearance only grows
    outer = MS.prism(RC.cover_section_outer(-2.0), x0 - 1, x1, "YZ")
    # build the outer as section-prism INTERSECT side-prism via a cutter = big box minus side prism
    big = MS.box(x0 - 5, x1 + 5, -40, 40, 0, 50)
    p = PartDef("dust_cover", [outer], cls="S-bend")
    inner_sec = MS.prism(RC.cover_section_inner(-8.0, COVER_I, WT), x0 - 10, x1 + 10, "YZ")
    p.side_outline = side_s
    p.side_inner = side_in
    p.inner_sec = inner_sec
    p.big = big
    return p


# skirt cutout over the port. Detail r2: a slanted (~47 deg) step from the lifted rear edge (Z 12.3: the handle stem,
# Z <= 11.85 at X 341-348.5 at full travel, passes under it) up to Z 19.2 at X 349-355.5, where the carrier's raised
# Z 19.6 step begins, so the whole opening ahead of the step shows the carrier's lit flank (c1: one long slot,
# slanted rear step, lit carrier bar, dark band under it; side panel: dark slot from X ~355; q34: rise at the selector
# tip). r1 had the rise at X 372-378.5 and the top at 19.2, which left the port's rear third hidden ('only a small
# black notch'). Top: c2 / q34 / the side panel show the opening up to just under the crease (Z ~21-22), c1 lower
# (~40 % of the skirt band kept): held at 19.2, the L3 port-corner limit (17 + 2.43); see spec_proposal.json.
CUT_REAR_Z, CUT_TOP_Z, CUT_RISE_X = 12.3, 19.2, (349.0, 355.5)


def cover_cut_outline():
    P = np.array([(338.0, 6.0), (452.0, 6.0), (452.0, CUT_TOP_Z), (CUT_RISE_X[1], CUT_TOP_Z),
                  (CUT_RISE_X[0], CUT_REAR_Z), (338.0, CUT_REAR_Z)], float)
    return G.fillet(P, 1.0, 4, radii=[0.0, 0.0, 1.0, 1.6, 1.2, 0.8])


def build_dust_cover(coll, offset):
    """Cover needs intersections, so it is built with explicit boolean steps."""
    import bpy
    from gunlib import bl
    p = dust_cover()
    ob = p.solids[0].to_object("dust_cover", coll, offset)
    bl.boolean(ob, MS.prism(p.side_outline, -40.0, 40.0), "INTERSECT", offset=offset)
    inner = p.inner_sec.to_object("_cov_in", coll, offset)
    bl.boolean(inner, MS.prism(G.ccw(p.side_inner), -40.0, 40.0), "INTERSECT", offset=offset)
    bl.boolean(ob, inner, "DIFFERENCE")
    bpy.data.objects.remove(inner, do_unlink=True)
    cuts = [MS.prism(cover_cut_outline(), -30.0, -15.0),                                    # port / skirt cutout
            MS.box(243.0 - 0.15, 251.0 + 0.15, -3.0 - 0.15, 3.0 + 0.15, 11.0, 40.0)]      # spring-guide button hole
    bl.boolean_many(ob, cuts, "DIFFERENCE", offset=offset)
    bl.clean(ob)
    bl.bevel_weighted(ob, 1.2, 2, pred_cover_bend, offset)
    bl.finish(ob)
    bl.weighted_normals(ob)
    ob["gun_part"] = json.dumps({"bone": "body", "class": "S-bend", "slot": "M_AR01_Metal", "spec_id": "dust_cover",
                                 "joint": {"type": "butt", "parent": "receiver", "gap_mm": [0.01, 0.05]}})
    return ob


def recoil_button() -> PartDef:
    """Recoil spring guide button: squared tab through a hole in the cover's sloped rear end, 1.5 mm proud of the
    slope (the TOP view's small squared tab); its top follows the slope."""
    side = dust_cover().side_outline

    def ztop(x):
        Q = np.vstack([side, side[:1]])
        zs = []
        for p0, p1 in zip(Q[:-1], Q[1:]):
            if (p0[0] - x) * (p1[0] - x) <= 0 and p0[0] != p1[0]:
                t = (x - p0[0]) / (p1[0] - p0[0])
                zs.append(p0[1] + t * (p1[1] - p0[1]))
        return max(zs)
    o = [(243.0, 12.0), (251.0, 12.0), (251.0, ztop(251.0) + 1.5), (243.0, ztop(243.0) + 1.5)]
    o = G.fillet(G.ccw(np.array(o, float)), 1.0, 3)
    return PartDef("recoil_spring_button", [MS.prism(o, -3.0, 3.0)], cls="M-round",
                   recipe=[(0.5, 2, 30.0)], joint={"type": "butt", "parent": "dust_cover", "gap_mm": [0.01, 0.05]})


RIVET_R, RIVET_H = 2.55, 1.0        # c1 draws the heads ~5 mm (spec 4.5 +- the sheet's 1.2 mm px); height kept for the selector sweep
CLIP_AT = (350.0, -25.0)           # c1 draws a wire retainer clip where the side view's dot (350, -25) is


def rivet_head(c, normal, r, h, nseg=8) -> Mesh:
    """Flat-topped button rivet head (integration round, 2026-10-05; the round-2 judge on c1: the reference shows
    'flat-headed' rivets, ours read as identical domes): a rolled shoulder (0.6 h at 0.93 r) up to a flat crown at
    0.62 r, height h; 8 segments (budget)."""
    prof = [(0.0, 0.0), (0.0, r), (0.6 * h, 0.93 * r), (h, 0.62 * r), (h, 0.0)]
    return MS.revolve(prof, c, normal, nseg)


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


def rivets() -> PartDef:
    r = SPEC.feature("receiver", "rivets_right")["XZ"]
    l = SPEC.feature("receiver", "rivets_left")["XZ"]
    rng = np.random.default_rng(7)
    sol = []
    for (x, z) in r:
        h = RIVET_H + rng.uniform(-0.1, 0.1)
        if (x, z) == CLIP_AT:
            continue
        sol.append(rivet_head((x, -WO - GAP, z), (0, -1, 0), RIVET_R, h, 8))
    for (x, z) in l:
        h = RIVET_H + rng.uniform(-0.1, 0.1)
        sol.append(rivet_head((x, WO + GAP, z), (0, 1, 0), RIVET_R, h, 8))     # r2: 8 segments on the left (budget)
    sol.append(retainer_clip(CLIP_AT))
    # detail r2: round studs on the cover crown (side-panel top bumps at X ~270/311/373/422, c1 draws three)
    for x in RC.STUDS_X:
        sol.append(rivet_head((x, 0.0, RC.CROWN_Z + GAP), (0, 0, 1), RC.STUD_R, RC.STUD_H, 8))
    return PartDef("rivets", sol, cls="none", recipe=[], wn=False, smooth_deg=60.0,
                   joint={"type": "butt", "parent": "receiver", "gap_mm": [0.01, 0.05]})


# ======================================================================================== bolt carrier (moving)
CARRIER_TRAVEL = 444.25 - (338.0 + 3.0)          # handle stops 3 mm before the port's rear wall


CARRIER_X = (346.0, 450.0)
# stepped rear (side, XZ): the full D section from X 369 (clears the cover's sloped rear end at full travel), Z <= 17
# from 355 (clears it too), Z <= 11.4 from 346 (passes under the spring-guide button, 0.83 mm off the rear wall at
# full travel); the flat flank then fills the port from X 346 (detail r1: no round chrome bolt in the port); detail r2:
# the flank below Z 9.5 is recessed 14.75 mm (CAVITY_*) so the port's lower half reads dark, the upper half a lit bar
CARRIER_STEPS = [(346.0, 11.4), (355.0, 19.6), (369.0, 40.0)]   # r2: middle step 17 -> 19.6 (fills the raised cutout)
HANDLE_Z = (8.0, 17.0)             # tab; its bottom stays 1.2 above the selector lever (Z 6.8) at full travel
STEM_Z = (8.6, 11.85)              # stem in the wall port; passes under the cutout's slanted rear step at full travel
CARRIER_FLAT_Z, CARRIER_TOP_B = 20.0, 9.7     # detail r2 section (top Z 29.7 as before)
# integration (2026-10-05): the recess floor stops at Y -8.5 (was -4.0): deeper, it opened into the chamber pocket round
# the barrel end (r 7.8) and the barrel showed through the port (side L2 'barrel' max 175 px); still 10.25 mm deep
CAVITY_X, CAVITY_Z, CAVITY_Y = (346.0 - 1.0, 443.0), (2.5, 9.5), 8.5     # flank recess (carrier frame at rest)


def bolt_carrier() -> PartDef:
    """Carrier block (flat flank in the port, D-shaped top under the cover crown) with a stepped rear that fills the
    port's visible length; charging handle tab (stem through the port's front end, flat-topped tab with rounded
    outer corners outside)."""
    # detail r2: flat flanks up to Z CARRIER_FLAT_Z (the flank shows as a flat lit bar through the whole skirt cutout,
    # c1 / c2 / q34), then an elliptical top 2 mm under the new cover crown (receiver_right_cover)
    yc = 18.75
    a = np.linspace(0.0, math.pi, 41)[1:-1]
    top = np.c_[yc * np.cos(a), CARRIER_FLAT_Z + CARRIER_TOP_B * np.sin(a)]
    sec = np.vstack([[[yc, -4.0], [yc, CARRIER_FLAT_Z]], top, [[-yc, CARRIER_FLAT_Z], [-yc, -4.0]]])
    carrier = MS.prism(sec, CARRIER_X[0], CARRIER_X[1], "YZ")
    side = [(CARRIER_X[0], -10.0), (CARRIER_X[1] + 5.0, -10.0), (CARRIER_X[1] + 5.0, 40.0)]
    for i in range(len(CARRIER_STEPS) - 1, -1, -1):
        x, z = CARRIER_STEPS[i]
        side += [(x, z)]
        if i > 0:
            side += [(x, CARRIER_STEPS[i - 1][1])]
    side_prism = MS.prism(G.ccw(np.array(side, float)), -30.0, 30.0)
    stem = MS.prism(G.rounded_rect(444.25, 451.75, STEM_Z[0], STEM_Z[1], 0.75, 3), -22.3, -18.5)
    tab = MS.prism(G.rounded_rect(444.0, 458.0, HANDLE_Z[0], HANDLE_Z[1], 2.0, 4), -35.2, -22.0)
    cut = [MS.cylinder((433.5, 0, 0), (452.0, 0, 0), 7.5 + 0.3, 32)]     # chamber pocket round the barrel end (unseen)
    # detail r2: deep recess in the right flank below the lit bar (c1 draws a dark shadow band under the carrier face,
    # q34 a dark gap under it): the port reads as a dark slot instead of a flush wall-coloured face
    cut.append(MS.prism(G.rounded_rect(CAVITY_X[0], CAVITY_X[1], CAVITY_Z[0], CAVITY_Z[1], 0.6, 2), -30.0, -CAVITY_Y))
    p = PartDef("bolt_carrier", [carrier], bone="bolt", cls="M-chamfer", cutters=cut,
                unions=[stem, tab], joint={"type": "sliding", "parent": "receiver", "axis_M": [-1, 0, 0],
                                           "travel_mm": round(CARRIER_TRAVEL, 3), "clearance_mm": [0.15, 0.4]},
                recipe=[(0.4, 1, 30.0)])
    p.section_intersect_pre = [side_prism]
    return p


def receiver_rails() -> PartDef:
    """Carrier guide rails pressed into the inner walls (below the port, X 262-452): the carrier's lateral guide,
    0.25 mm per side."""
    sol = [MS.box(262.0, 451.98, 19.0, WO - WT - GAP, -4.6, -1.0), MS.box(262.0, 451.98, -(WO - WT - GAP), -19.0, -4.6, -1.0)]
    return PartDef("receiver_rails", sol, cls="M-chamfer", recipe=[(0.2, 1, 30.0)],
                   joint={"type": "butt", "parent": "receiver", "gap_mm": [0.01, 0.05]})


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


# ======================================================================================== module interface
OBJECTS = ('receiver', 'dust_cover', 'recoil_spring_button', 'rivets', 'receiver_rails', 'bolt_carrier', 'mag_catch')            # registry keys built here (rifle_parts.ORDER)
CLOSEUPS = ('c1', 'c2', 'q34')          # sheet panels that are this part's shape authority (rifle_detail.py)


def build(spec, ctx):
    """Build this module's objects into ctx (gunlib.parts.BuildCtx). Returns {registry key: [objects]}; keys that
    ctx.only excludes come back empty. `spec` is the rifle GunSpec (the same object as rifle_common.SPEC)."""
    return {k: ctx.make(k, f) for k, f in (("receiver", receiver), ("dust_cover", build_dust_cover), ("recoil_spring_button", recoil_button), ("rivets", rivets), ("receiver_rails", receiver_rails), ("bolt_carrier", bolt_carrier), ("mag_catch", mag_catch),)}
