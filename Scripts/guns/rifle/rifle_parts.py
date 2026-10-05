"""Stage 2 form: every AR-01 part as real geometry (frame M, mm), from rifle_spec.json.

Rules (RIFLE_BUILD_PLAN 4, GUN_BUILDING_STUDY 3.1/3.2/3.7):
- side outlines come from the traced profiles (spec side_profile_M), cleaned (Douglas-Peucker for steel, smoothing
  for wood) or authored from the trace numbers where the trace is noisy; widths from TOP; sections from the
  close-ups and the real pattern;
- every part a closed solid; butt joints keep a 0.02 mm modelled gap (no shared vertices); moving parts are
  separate solids with their pivot, axis and limits (sweep: fit.py);
- every opening the sheet shows is cut with its wall; fasteners are real geometry.
"""
from __future__ import annotations

import json
import math
from typing import Dict, List

import numpy as np

from rifle_common import SPEC, GRIP, TRACE
from gunlib import geo2d as G
from gunlib import mesh as MS
from gunlib.mesh import Mesh
from gunlib.parts import PartDef, RECIPES

GAP = 0.02            # butt-joint modelled gap (clearance table 3.7: 0.01-0.05)
WO = 20.75            # receiver wall outer half width (key dim 41.5)
WT = 1.0              # sheet thickness
COVER_O = 21.75       # dust cover outer half width (key dim 43.5)
COVER_I = WO + GAP    # dust cover inner half width
LEDGE = [(241.0, -32.85), (255.0, -32.5), (300.0, -31.3), (360.0, -29.5), (370.0, -29.25)]


def ledge_z(x):
    return float(G.polyline_interp(LEDGE, x))


def prof(pid, tol=0.55):
    return G.clean_hard(SPEC.profile(pid), tol)


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
    unions.append(MS.box(368.8, 433.0, -15.5, 15.5, -30.3, -11.0))
    unions.append(MS.box(367.8, 368.85, -15.5, 15.5, -29.0, -11.0))
    post = []
    post.append(MS.box(368.8, 432.0, -14.5, 14.5, -45.0, -5.0))                       # well opening + bore
    # ejection port (right wall only), R1 corners
    port = G.rounded_rect(338.0, 452.0, 3.0, 17.0, 1.0, 3)
    post.append(MS.prism(port, -24.0, -WO + WT + 0.85))          # through the whole 1.0 wall
    # selector pivot hole (right wall), trigger slot (bottom)
    post.append(MS.cylinder((282.8, -24.0, -7.8), (282.8, -18.9, -7.8), 3.2, 32))
    post.append(MS.box(301.5, 329.0, -3.25, 3.25, -40.0, -27.0))
    # barrel bore through the front trunnion (barrel r 7.5 + gap)
    post.append(MS.cylinder((450.0, 0, 0), (490.0, 0, 0), 7.5 + GAP, 48))
    # lower handguard tenon pocket in the front face (X 484.0 - 485.3)
    post.append(lower_handguard_tenon(GAP, 483.98, 490.0))
    post.append(lower_handguard_tenon(1.5, 484.75, 490.0))      # mouth relief: room for the tenon's root fillet
    # side dimples (pressed: outer recess 1.0 deep, inner bump keeps the 1.0 wall)
    for s in (-1, 1):
        unions.append(dimple_lens((397.0, s * (WO - WT), -17.0), s, 9.0, 5.5, 1.0, inner=True))
        post.append(dimple_lens((397.0, s * WO, -17.0), s, 9.0, 5.5, 1.0, inner=False))
    # pressed groove (left wall only, as the true-left panel draws it)
    post.append(MS.capsule((421.5, WO + 1.5 - 0.8, -20.0), (458.5, WO + 1.5 - 0.8, -20.0), 1.5, 20, 4))
    # flush pin, right: inset ring 0.3 deep
    post.append(MS.tube((388.0, -WO - 1.0, -8.0), (388.0, -WO + 0.3, -8.0), 1.45, 1.75, 32))
    # trigger-guard flange relief is a separate part; the rear-section bottom meets the grip
    rec = [(1.6, 3, "W", pred_bend_bottom), (0.3, 1, 40.0)]
    return PartDef("receiver", solids, cutters=cut + post, unions=unions, cls="S-bend", recipe=rec,
                   joint={"type": "fixed", "parent": None})


def dimple_lens(c, side, ax, az, depth, inner=False, nu=28, nr=6) -> Mesh:
    """Pressed oval dimple (semi-axes ax, az): a cosine-profile depression of the given depth with zero slope at
    the rim. inner=False -> the cutter (flat face 2 mm outside the wall, dished face going in); inner=True -> the
    bump left on the inner face (so the sheet keeps its 1.0 mm)."""
    c = np.asarray(c, float)
    m = Mesh()
    th = np.linspace(0, 2 * math.pi, nu, endpoint=False)
    rings_d, rings_f = [], []
    for j in range(nr + 1):
        t = j / nr
        d = depth * 0.5 * (1 + math.cos(math.pi * t))
        x = c[0] + ax * t * np.cos(th)
        z = c[2] + az * t * np.sin(th)
        rings_d.append(np.c_[x, np.full(nu, c[1] - side * d + (side * 0.002 if j == nr else 0.0)), z])
        rings_f.append(np.c_[x, np.full(nu, c[1] + side * (2.0 if not inner else 0.6)), z])
    dish = [m.add_verts(r) for r in rings_d]
    flat = [m.add_verts(r) for r in rings_f]
    ctr_d = m.add_verts([[c[0], c[1] - side * depth, c[2]]])[0]
    ctr_f = m.add_verts([[c[0], c[1] + side * (2.0 if not inner else 0.6), c[2]]])[0]
    for k in range(nu):
        k2 = (k + 1) % nu
        m.face((ctr_d, dish[1][k], dish[1][k2]))
        m.face((ctr_f, flat[1][k2], flat[1][k]))
        for j in range(1, nr):
            m.face((dish[j][k], dish[j + 1][k], dish[j + 1][k2], dish[j][k2]))
            m.face((flat[j][k2], flat[j + 1][k2], flat[j + 1][k], flat[j][k]))
        m.face((dish[nr][k], flat[nr][k], flat[nr][k2], dish[nr][k2]))
    return m


def lower_handguard_tenon(grow, x0, x1) -> Mesh:
    """Hidden tenon on the lower handguard's rear end (sits in the receiver's front cup, X 484.0-485.3); with
    grow > 0 it is the matching pocket cutter."""
    sec = G.rounded_rect(-16.0 - grow, 16.0 + grow, -25.5 - grow, 8.5 + grow, 3.0, 3)
    m = MS.prism(np.c_[sec[:, 0], sec[:, 1]], x0, x1, "YZ")
    return m


def rear_trunnion() -> PartDef:
    d = 2 * GAP                     # rear face 0.04 forward of the stock's front face (which is this outline)
    o = [(225.2 + d, 7.0), (225.2 + d, -17.5), (228.7 + d, -22.0), (229.0 + d, -28.5), (230.1 + d, -34.0),
         (231.6 + d, -37.2), (240.9 - GAP, -37.2), (240.9 - GAP, 10.38), (238.2, 10.38), (237.2, 7.8), (226.4, 7.8)]
    # TOP: the block is the stock-wrist width (33) back to X ~233, then flares to the receiver width
    rear = MS.prism(G.clip_x(np.array(o, float), None, 234.0), -16.6, 16.6)
    front = MS.prism(G.clip_x(np.array(o, float), 233.0, None), -WO, WO)
    return PartDef("rear_trunnion", [rear], unions=[front], cls="M-chamfer", recipe=[(0.45, 1, 40.0)],
                   joint={"type": "butt", "parent": "receiver", "gap_mm": [0.01, 0.05]})


def dust_cover() -> PartDef:
    """Smooth stamped cover: semicircular crown (R 21.75) on short skirts, closed rounded rear end, open front
    tucked under the rear sight block, right skirt cut out over the port, button hole at the rear top."""
    zc = 32.7 - COVER_O                      # crown centre height 10.95
    x0, x1 = 239.4, 454.9 - GAP
    rear = [(241.5, 13.5), (245.0, 20.1), (250.0, 22.6), (255.0, 25.6), (260.0, 29.3), (265.0, 32.1), (268.5, 32.7)]
    rear_s = open_chaikin([(x0, 10.6), (x0, 11.6)] + rear + [(280.0, 32.7)], 3)
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
    def section(r, zb, circumscribe=False):
        a = np.linspace(0, math.pi, 25)
        rr = r / math.cos(0.5 * (a[1] - a[0])) if circumscribe else r     # inner face: chords never inside r
        arcp = np.c_[rr * np.cos(a), zc + rr * np.sin(a)]
        arcp[0, 0], arcp[-1, 0] = r, -r
        arcp[0, 1] = arcp[-1, 1] = zc
        return np.vstack([[r, zb], arcp, [-r, zb]])

    outer = MS.prism(section(COVER_O, -2.0), x0 - 1, x1, "YZ")
    # build the outer as section-prism INTERSECT side-prism via a cutter = big box minus side prism
    big = MS.box(x0 - 5, x1 + 5, -40, 40, 0, 50)
    p = PartDef("dust_cover", [outer], cls="S-bend")
    inner_sec = MS.prism(section(COVER_I, -8.0, True), x0 - 10, x1 + 10, "YZ")
    p.side_outline = side_s
    p.side_inner = side_in
    p.inner_sec = inner_sec
    p.big = big
    return p


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
    cuts = [MS.prism(G.rounded_rect(338.0, 452.0, 8.0, 17.0, 1.0, 3), -30.0, -15.0),      # port / skirt cutout
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


def rivets() -> PartDef:
    r = SPEC.feature("receiver", "rivets_right")["XZ"]
    l = SPEC.feature("receiver", "rivets_left")["XZ"]
    rng = np.random.default_rng(7)
    sol = []
    for (x, z) in r:
        h = 1.0 + rng.uniform(-0.1, 0.1)
        sol.append(MS.dome((x, -WO - GAP, z), (0, -1, 0), 2.25, h, 12, 2))
    for (x, z) in l:
        h = 1.0 + rng.uniform(-0.1, 0.1)
        sol.append(MS.dome((x, WO + GAP, z), (0, 1, 0), 2.25, h, 12, 2))
    return PartDef("rivets", sol, cls="none", recipe=[], wn=False, smooth_deg=60.0,
                   joint={"type": "butt", "parent": "receiver", "gap_mm": [0.01, 0.05]})


# ======================================================================================== bolt carrier (moving)
CARRIER_TRAVEL = 444.25 - (338.0 + 3.0)          # handle stops 3 mm before the port's rear wall


def bolt_carrier() -> PartDef:
    """Carrier block (flat flank in the port, D-shaped top under the cover crown), recessed bolt behind it, charging
    handle tab (stem through the port's front end, flat-topped tab with rounded outer corners outside)."""
    zc = 32.7 - COVER_O
    r_top = COVER_I - WT - 1.0                # 1 mm under the cover's inner crown
    # carrier section (YZ): rectangle y +-18.75, z -4..top, intersected with the crown circle
    a = np.linspace(math.radians(10), math.radians(170), 33)
    yc = 18.75
    z_side = zc + math.sqrt(r_top ** 2 - yc ** 2)
    arcp = np.c_[r_top * np.cos(a), zc + r_top * np.sin(a)]
    arcp = arcp[np.abs(arcp[:, 0]) <= yc]
    sec = np.vstack([[[yc, -4.0], [yc, z_side]], arcp[::1], [[-yc, z_side], [-yc, -4.0]]])
    carrier = MS.prism(sec, 378.0, 450.0, "YZ")
    bolt = MS.cylinder((355.0, 0, 9.0), (378.2, 0, 9.0), 8.0, 32)      # rear end clears the spring-guide button at full travel
    # charging handle: stem in the port (X 444.25-451.75, Z 11.25-16.75), tab outside
    stem = MS.prism(G.rounded_rect(444.25, 451.75, 11.25, 16.75, 0.75, 3), -22.3, -18.5)   # port corners R1 - 0.25
    tab_o = G.rounded_rect(444.0, 458.0, 11.0, 22.0, 2.0, 4)
    tab = MS.prism(tab_o, -35.2, -22.0)
    cut = [MS.cylinder((433.5, 0, 0), (452.0, 0, 0), 7.5 + 0.3, 48)]     # chamber pocket round the barrel end
    return PartDef("bolt_carrier", [carrier], bone="bolt", cls="M-chamfer", cutters=cut,
                   unions=[bolt, stem, tab], joint={"type": "sliding", "parent": "receiver", "axis_M": [-1, 0, 0],
                                     "travel_mm": round(CARRIER_TRAVEL, 3), "clearance_mm": [0.15, 0.4]},
                   recipe=[(0.4, 1, 30.0)])


RECEIVER_RAILS = None


def receiver_rails() -> PartDef:
    """Carrier guide rails pressed into the inner walls (below the port, X 262-452): the carrier's lateral guide,
    0.25 mm per side."""
    sol = [MS.box(262.0, 451.98, 19.0, WO - WT - GAP, -4.6, -1.0), MS.box(262.0, 451.98, -(WO - WT - GAP), -19.0, -4.6, -1.0)]
    return PartDef("receiver_rails", sol, cls="M-chamfer", recipe=[(0.2, 1, 30.0)],
                   joint={"type": "butt", "parent": "receiver", "gap_mm": [0.01, 0.05]})


# ======================================================================================== harness
def part_defs() -> Dict[str, object]:
    """name -> PartDef or a builder callable(coll, offset) -> object."""
    d = {}
    d["receiver"] = receiver
    d["rear_trunnion"] = rear_trunnion
    d["dust_cover"] = build_dust_cover
    d["recoil_spring_button"] = recoil_button
    d["rivets"] = rivets
    d["receiver_rails"] = receiver_rails
    d["bolt_carrier"] = bolt_carrier
    import rifle_parts2 as R2
    for name, fn in (("rear_sight_block", R2.rear_sight_block), ("rear_sight_leaf", R2.rear_sight_leaf),
                     ("handguard_retainer", R2.retainer), ("gas_tube_rear_cap", R2.gas_tube_rear_cap),
                     ("upper_handguard", R2.upper_handguard), ("lower_handguard", R2.lower_handguard),
                     ("handguard_front_band", R2.front_band), ("gas_tube", R2.gas_tube), ("gas_piston", R2.gas_piston), ("gas_block", R2.gas_block),
                     ("barrel", R2.barrel), ("cleaning_rod", R2.cleaning_rod),
                     ("front_sight_block", R2.front_sight_block), ("front_sight_post", R2.front_sight_post),
                     ("muzzle_brake", R2.muzzle_brake), ("trigger", R2.trigger), ("trigger_guard", R2.trigger_guard),
                     ("mag_catch", R2.mag_catch), ("pistol_grip", R2.pistol_grip), ("buttstock", R2.buttstock),
                     ("butt_plate", R2.butt_plate), ("butt_screws", R2.butt_screws),
                     ("sling_swivel_base", R2.sling_swivel), ("sling_swivel_loop", R2.sling_loop),
                     ("stock_hardware", R2.stock_hardware), ("selector", R2.selector),
                     ("magazine", R2.magazine), ("magazine_floor_plate", R2.magazine_floor)):
        d[name] = fn
    for k, v in EXTRA.items():
        d[k] = v
    return d


EXTRA: Dict[str, object] = {}


def build_all(only=None):
    import bpy
    from gunlib import bl
    from gunlib.parts import build_part
    from rifle_common import SCRATCH, GATES
    coll = bl.collection("AR01_Parts")
    objs, report = [], {}
    for name, fn in part_defs().items():
        if only and name not in only:
            continue
        r = fn() if fn.__code__.co_argcount == 0 else None
        if r is None:
            built = [fn(coll, GRIP)]
        else:
            built = [build_part(q, coll, GRIP) for q in (r if isinstance(r, tuple) else (r,))]
        for ob in built:
            rep = bl.manifold_report(ob)
            report[ob.name] = rep
            objs.append(ob)
            print("[AR01] part %-24s tris %6d  boundary %d  multi %d  shells %d" % (
                ob.name, rep["triangles"], rep["boundary_edges"], rep["multi_face_edges"], rep["shells"]))
    tag = "form" if not only else "form_partial"
    bl.export_npz(objs, SCRATCH / f"{tag}_tris.npz", GRIP, [o.name for o in objs])
    (SCRATCH / f"{tag}_build_report.json").write_text(json.dumps(report, indent=1))
    print("[AR01] total tris", sum(r["triangles"] for r in report.values()))
    return objs, report
