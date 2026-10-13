"""SR01 form stage: every part as a closed solid in frame M (mm) with its process bevels, internals, bone, joint row,
pivot / axis / limits (gun_part record), built inside Blender through gunlib.bl booleans + bevels.

Construction: side profiles = the traced GR part rings (Douglas-Peucker, crisp corners) clipped at the declared butt
joints; plan widths = the TOP left half-widths (sr_common); round parts revolve; internals are boolean cuts (bolt
raceway + lug grooves + lug-recess annulus, port to the stroke, magazine well with shelf / feed opening / catch
window, release clevis, trigger pocket, riser post bores, barrel channel). Part list and geometry rulings:
SR01_BUILD_PLAN 2-5, CRAFT_STUDY RP1-RP15, sr01_spec.json (wins).
"""
from __future__ import annotations

import json
import math
import time

import numpy as np

from gunlib import bl
from gunlib import geo2d as G
from gunlib import mesh as MS
from gunlib.parts import PartDef, build_part
from gunlib.parts import hardware as HW
from gunlib.parts import rail_1913 as RAIL
from sr_common import (CODE, GRIP, PARTS_COLL, SLOT_CHASSIS, SLOT_METAL, SLOT_MAG, dims, part_rings, trace,
                       signed_area, CHASSIS_HALF, BUTT_HALF, half_at)
import sr_motion as MO

BIG = 400.0
NO_BEVEL = False
STRIP_MM = 0.03          # strip collapses limited to 0.03 mm moves (the 0.1 default shifted joints / clearances)
# the repair moved gate-critical surfaces on these (inlet lip into the receiver, the knob centre, the well walls):
# their UD drops are left for the W2 generator fix (no micro bevel strips at the source)
REPAIR_SKIP = {"chassis", "bolt_handle", "magazine"}
REPAIR_ONLY = None       # None = every part failing UD; a set = only those
RELAXED = False          # the relaxed final pass moved real geometry on the gun (hook, knob, well): off


# ------------------------------------------------------------------------------------------------ 2D helpers
def rings(key, tol=0.6, min_area=300.0):
    outs, _ = part_rings(key)
    return [G.ccw(G.dp_simplify(r, tol)) for r in outs if abs(signed_area(r)) >= min_area]


def ring(key, tol=0.6):
    rr = rings(key, tol)
    return max(rr, key=lambda r: abs(G.area(r)))


def clip(P, x0=None, x1=None, z0=None, z1=None):
    Q = G.clip_x(P, x0, x1)
    if len(Q) >= 3 and (z0 is not None or z1 is not None):
        Q = G.clip_y(Q, z0, z1)
    return G.ccw(G.dedupe(Q))


def stadium(x0, x1, z0, z1, n=8):
    r = 0.5 * (z1 - z0)
    zc = 0.5 * (z0 + z1)
    a = [(x1 - r + r * math.cos(t), zc + r * math.sin(t)) for t in np.linspace(-math.pi / 2, math.pi / 2, n)]
    b = [(x0 + r + r * math.cos(t), zc + r * math.sin(t)) for t in np.linspace(math.pi / 2, 3 * math.pi / 2, n)]
    return np.array(a + b)


def rrect(x0, x1, z0, z1, r, seg=4):
    return G.rounded_rect(x0, x1, z0, z1, r, seg)


def plan_prism(table, z0=-250.0, z1=150.0, x_ext=(None, None)):
    up = [(x, half_at(table, x)) for x, _ in table]
    if x_ext[0] is not None:
        up = [(x_ext[0], up[0][1])] + up
    if x_ext[1] is not None:
        up = up + [(x_ext[1], up[-1][1])]
    # W3 Part 0 (UD3): drop collinear points (the table's last point stayed on the extended side face and left a
    # zero-tangent sliver at the forend nose after the round)
    up = [p for i, p in enumerate(up) if i in (0, len(up) - 1) or not (up[i - 1][1] == p[1] == up[i + 1][1])]
    P = np.array(up + [(x, -y) for x, y in reversed(up)])
    return MS.prism(P, z0, z1, "XY")


def yz_prism(P_yz, x0, x1):
    return MS.prism(P_yz, x0, x1, "YZ")


def sector(x0, x1, r0, r1, a0, a1, n=12):
    """Annular sector prism along X (angles in deg from +Y toward +Z)."""
    t = np.radians(np.linspace(a0, a1, n))
    outer = [(r1 * math.cos(a), r1 * math.sin(a)) for a in t]
    inner = [(r0 * math.cos(a), r0 * math.sin(a)) for a in t[::-1]] if r0 > 0 else [(0.0, 0.0)]
    return yz_prism(np.array(outer + inner), x0, x1)


def bar(p0, p1, r, nseg=24):
    return MS.cylinder(p0, p1, r, nseg)


def ycyl(x, z, y0, y1, r, nseg=32):
    return MS.cylinder((x, y0, z), (x, y1, z), r, nseg)


def xcyl(x0, x1, r, y=0.0, z=0.0, nseg=32):
    return MS.cylinder((x0, y, z), (x1, y, z), r, nseg)


def joint(kind, **kw):
    rows = {"butt": [0.01, 0.05], "sliding": [0.15, 0.40], "hinge": [0.10, 0.30], "seated_mag": [0.2, 0.6]}
    d = {"type": kind, "gap_mm": rows.get(kind)}
    d.update(kw)
    return d


CH = [(0.6, 1, 30.0)]             # M-chamfer (machined aluminium / steel): 0.6 x 45
CH4 = [(0.4, 1, 30.0)]
RND = [(0.8, 2, 30.0)]
RND1 = [(1.0, 1, 30.0)]          # L8 fix round: machined outer edges broken with a 1.0 radius (judges: razor slabs)
POLY = [(1.8, 3, 30.0)]
RUB = [(3.0, 3, 30.0)]


# ------------------------------------------------------------------------------------------------ custom builder
class Part:
    """Ordered boolean steps (ops: ("U"|"I"|"D", [Mesh])) then the bevel recipe, post cutters, finish, record."""

    def __init__(self, name, base, ops=(), bone="body", cls="M-chamfer", slot=SLOT_METAL, recipe=CH, jnt=None,
                 post=(), spec_id=None, smooth_deg=30.0, motion=None, weld_mm=None):
        self.name, self.base, self.ops, self.bone, self.cls, self.slot = name, base, list(ops), bone, cls, slot
        self.recipe, self.jnt, self.post, self.spec_id = recipe, jnt or joint("butt"), list(post), spec_id or name
        self.smooth_deg, self.motion = smooth_deg, motion
        self.weld_mm = weld_mm

    def build(self, coll):
        t0 = time.time()
        ob = self.base.to_object(self.name, coll, GRIP, smooth_deg=self.smooth_deg)
        for op, meshes in self.ops:
            meshes = [m for m in meshes if m is not None and len(m.F)]
            if not meshes:
                continue
            bl.boolean_many(ob, meshes, {"U": "UNION", "I": "INTERSECT", "D": "DIFFERENCE"}[op], offset=GRIP) \
                if op != "I" else [bl.boolean(ob, m, "INTERSECT", offset=GRIP) for m in meshes]
        bl.clean(ob)
        if NO_BEVEL:
            self.recipe = []
        for w, s, a in self.recipe:
            bl.bevel(ob, w, s, a)
        if self.post:
            bl.boolean_many(ob, self.post, "DIFFERENCE", offset=GRIP)
            bl.clean(ob)
        if self.weld_mm:
            # generator step (W1 follow-up UD1): weld the near-duplicate vertex pairs (0.005-0.01 mm apart) the exact
            # boolean leaves where the round meets the traced outline; max move weld_mm / 2, no strip collapse (0.016: 0 drops and manifold; 0.02+ made 2 multi-face edges)
            bl.clean(ob, dist_m=self.weld_mm * 1e-3)
        bl.finish(ob)
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        loose = [e for e in bm.edges if not e.link_faces]
        if loose:
            bmesh.ops.delete(bm, geom=loose, context="EDGES")
            bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_edges], context="VERTS")
            bm.to_mesh(ob.data)
        bm.free()
        from gunlib import ud as _ud
        u0 = _ud.check_object(ob)
        self.ud_pre = {k: u0.get(k) for k in ("unreal_drops", "edges_under_0.05mm", "needles_under_0.02mm",
                                              "strip_polygons_under_0.1mm")}
        if not (u0.get("pass_ud1") and u0.get("pass_ud2")) and (REPAIR_ONLY is None or self.name in REPAIR_ONLY)                 and self.name not in REPAIR_SKIP:
            keep = ob.data.copy()
            self.ud_repair = _ud.repair(ob, strip_mm=STRIP_MM, relaxed_final=RELAXED)  # generator-side (gunlib 0.2.1)
            u1 = _ud.check_object(ob)
            score = lambda u: (u.get("unreal_drops") or 0, (u.get("edges_under_0.05mm") or 0)
                               + (u.get("needles_under_0.02mm") or 0) + (u.get("strip_polygons_under_0.1mm") or 0))
            if score(u1) > score(u0):                                    # never keep a worse mesh
                bad = ob.data
                ob.data = keep
                bpy_ = __import__("bpy")
                bpy_.data.meshes.remove(bad)
        # SMG lesson (gunlib 0.2.1): drop the bevel's stale custom normals, then face-area weighting at 100 so flat
        # faces keep their own normal next to the chamfers (no shading smear across the big n-gon fans)
        bl.weighted_normals(ob, sharp_deg=self.smooth_deg, weight=100, clear_custom=True)
        rec = {"bone": self.bone, "class": self.cls, "slot": self.slot, "joint": self.jnt, "spec_id": self.spec_id,
               "recipe": [list(r) for r in self.recipe], "motion": self.motion}
        ob["gun_part"] = json.dumps(rec)
        rep = bl.manifold_report(ob)
        try:
            from gunlib import ud
            u = ud.check_object(ob)
            rep["ud"] = {k: u.get(k) for k in ("unreal_drops", "min_area_mm2", "edges_under_0.05mm",
                                               "needles_under_0.02mm", "strip_polygons_under_0.1mm", "pass_ud1",
                                               "pass_ud2")}
        except Exception as e:  # pragma: no cover
            rep["ud"] = {"error": str(e)}
        rep["seconds"] = round(time.time() - t0, 2)
        rep["bone"], rep["slot"] = self.bone, self.slot
        rep["ud_pre_repair"] = getattr(self, "ud_pre", None)
        return ob, rep



# ------------------------------------------------------------------------------------------------ chassis
Z_GRIP_SPLIT = -55.97          # chassis | grip butt joint (grip below -56.00)
X_GRIP_FRONT = 330.6           # grip | guard boundary
X_BUTT_JOINT = 244.8


def chassis():
    cen = clip(ring("chassis_centre", 1.3), x0=X_BUTT_JOINT + 0.02)
    fore = G.offset(ring("chassis_forend", 1.3), 0.25)
    fore = clip(fore, x0=560.0)
    guard = G.offset(ring("trigger_guard", 1.3), 0.25)   # UD1: 1.3 like the centre (0.8 left sub-width segments)
    base = MS.prism(cen, -BIG / 4, BIG / 4)
    # (W4 review C2) the guard's bottom bar: the sheet draws a closed loop (the trace's opening Z -94.7..-62.8), but the
    # trace gave the bar to the chassis label and the guard ring stopped at two hooked arms. The bar spans the arms
    # (X 336.5-399.5) from their lowest point up past the opening's floor (the opening cut trims it back to -94.7);
    # its sides sit 0.4 inside the guard's (Y +-8.6): coplanar with the arms' +-9 faces, or ending at X 338 / 398, the
    # union left 1-10 UD1 slivers (variants in scratch/w4/FIX_LOG)
    gz0 = float(np.asarray(guard)[:, 1].min())
    bar = MS.prism(rrect(336.5, 399.5, gz0, -94.2, 1.5), -8.6, 8.6)
    unions = [MS.prism(fore, -BIG / 4, BIG / 4), MS.prism(guard, -9.0, 9.0), bar,
              # (W3 Part 0, UD2: both boxes stand past the plan width and under the traced top, so the plan / ring
              # faces cut them cleanly; at Y +-27 / +-36.9 and Z 15.9 they were coincident and left 0.035-0.047 mm edges
              # and 0.019 mm needles)
              MS.box(344.0, 395.0, -28.0, 28.0, -50.0, -11.6),                 # under the bolt knob (hidden in GR)
              MS.box(558.0, 600.0, -38.0, 38.0, -39.58, 15.6),                 # forend root (overlaps the clip at 560)
              MS.prism(np.array([(X_BUTT_JOINT + 0.02, -40.0), (346.0, -40.0), (346.0, -10.5), (326.0, -10.5),
                                 (318.0, -14.0), (X_BUTT_JOINT + 0.02, -14.0)]), -BIG / 4, BIG / 4)]
    plan = plan_prism(CHASSIS_HALF, x_ext=(X_BUTT_JOINT + 0.02, 840.0))
    # guard opening = the traced silhouette hole
    hole = [np.array(r, float) for r in trace("GR")["silhouette"]["mm"]
            if signed_area(r) < 0 and np.array(r)[:, 0].min() > 330 and np.array(r)[:, 0].max() < 400][0]
    cut = [MS.prism(G.ccw(G.dp_simplify(hole, 1.0)), -40.0, 40.0),
           MS.prism(np.array([(X_BUTT_JOINT - 1.0, -14.0), (318.0, -14.0), (326.0, -10.5), (346.5, -10.5),
                              (346.5, 60.0), (X_BUTT_JOINT - 1.0, 60.0)]), -BIG / 4, BIG / 4),   # clean top line
           MS.box(240.0, X_GRIP_FRONT, -40.0, 40.0, -200.0, Z_GRIP_SPLIT),       # the grip's seat
           MS.box(740.0, 845.0, -40.0, 40.0, -200.0, -39.58)]                   # flat dovetail seat for the clamp
    # UD1 at the source (W1 follow-up): the internal pockets and bores go AFTER the 1.0 round (post cutters), so the
    # bevel never meets them (it left 35 Unreal-drop slivers where it ran into the inlet, pocket and bore edges)
    post = []
    # receiver inlet (butt 0.02), bolt raceway behind the receiver (r 12.5), barrel channel (>= 3.0 radial, U open)
    post += [xcyl(381.96, 567.34, 17.19, nseg=48), xcyl(250.0, 382.5, 12.5, nseg=40),
            xcyl(566.0, 845.0, 20.6, nseg=48), MS.box(566.0, 845.0, -20.6, 20.6, 0.0, 40.0)]   # 1.34 into the inlet: no strip
    # bolt-stem relief (right) and the safety pocket (right tang)
    # (W3 Part 0, UD2: the relief's inner face at Y -10.2, not -10.5: -10.5 met the inlet's 48-gon 0.035 mm from a
    # facet vertex)
    post += [MS.prism(rrect(376.0, 397.0, -24.0, 2.0, 5.0), -60.0, -10.2),
            MS.prism(rrect(351.5, 369.5, -22.5, 1.0, 3.0), -40.0, -17.0)]
    # magazine well (mag 414.1..503.3 x +-13.25, clearance 0.3; body top -20.0 -> shelf -19.7), feed opening
    post += [MS.box(413.8, 503.6, -13.55, 13.55, -90.0, -19.7), MS.box(417.5, 488.5, -9.0, 9.0, -19.8, -8.0)]
    # release clevis: the paddle (X 405.6..410.6, Y +-5) swings -4.5 (hook back above the pivot, pad forward below);
    # the catch window through the well's rear wall at the hook
    post += [MS.prism(np.array([(403.0, -74.0), (403.0, -46.5), (410.9, -46.5), (410.9, -74.0), (416.5, -74.0),
                               (416.5, -130.0), (405.0, -130.0), (405.0, -74.0)])[::-1], -5.3, 5.3),
            MS.box(410.0, 414.5, -5.3, 5.3, -53.0, -46.5),
            ycyl(408.6, -74.0, -8.1, 8.1, 1.52, 24)]           # (W4 C9) the bore stops inside the cheeks
    # trigger pocket (hub r 4.2 + blade root), pin bore
    # (W3 Part 0: the slot runs 6 mm further back for the blade moved 5 mm rearward; it swings back on the pull)
    post += [ycyl(368.0, -57.0, -3.2, 3.2, 4.2, 32), MS.box(357.6, 373.4, -3.2, 3.2, -64.0, -57.0),
            ycyl(368.0, -57.0, -30.0, 30.0, 1.52, 24)]
    # safety pin bore
    post += [ycyl(360.0, -16.0, -30.0, -12.0, 1.52, 24)]
    # forend slots (through), dovetail band flanks (45 deg, depth 6 under Z -25.1), forend top chamfers (4 x 45)
    for s in dims("chassis")["slots"]:
        cut.append(MS.prism(stadium(s["X"][0], s["X"][1], s["Z"][0], s["Z"][1]), -50.0, 50.0))
    b0, b1 = dims("chassis")["dovetail_band"]["X"]
    for sg in (1, -1):
        cut.append(yz_prism(np.array([(sg * 45.0, -24.55), (sg * 37.5, -24.55), (sg * 30.9, -31.15), (sg * 30.9, -80.0),
                                      (sg * 45.0, -80.0)])[::(1 if sg > 0 else -1)], b0, b1))
    # fastener seats (counterbores the drawn heads sit in)
    post += [ycyl(389.6, -38.3, -40.0, -25.6, 4.0, 24)]
    return Part("chassis", base, [("U", unions), ("I", [plan]), ("D", cut)], slot=SLOT_CHASSIS, recipe=RND1,
                post=post, spec_id="chassis", weld_mm=0.016)


# ------------------------------------------------------------------------------------------------ butt group
def butt():
    rr = rings("butt", 1.3, min_area=300.0)
    main = max(rr, key=lambda r: abs(G.area(r)))
    tower = [r for r in rr if r is not main]
    P = clip(main, x0=68.92, x1=X_BUTT_JOINT - 0.02)
    base = MS.prism(P, -BIG / 4, BIG / 4)
    un = []
    plan = plan_prism(BUTT_HALF, x_ext=(60.0, 252.0))
    cut = [MS.box(222.0, 250.0, -40.0, 40.0, -200.0, Z_GRIP_SPLIT),
           MS.box(60.0, 181.6, -40.0, 40.0, -16.7, 80.0),                    # riser seat Z -16.7
           MS.box(179.0, 212.0, -40.0, 40.0, -17.9, 80.0)]                   # the riser front block's recess
    for x in dims("cheek_riser")["posts_X"]:                                    # post bores (sliding 0.15)
        cut.append(MS.cylinder((x, 0, -66.0), (x, 0, -16.0), 5.15, 32))
    cut.append(MS.cylinder((122.0, 31.0, -70.0), (122.0, 24.0, -70.0), 6.0, 32))      # QD cup (left)
    cut.append(MS.cylinder((122.0, 31.0, -70.0), (122.0, 21.0, -70.0), 3.2, 24))
    return Part("butt", base, [("U", un), ("I", [plan]), ("D", cut)], slot=SLOT_CHASSIS, recipe=RND1)


def butt_pad():
    P = G.ccw(G.dp_simplify(G.clean_smooth(clip(ring("butt_pad"), x1=52.88), step=1.0, sigma_mm=1.2, corner_deg=60.0), 0.25))
    P = clip(P, x0=0.0, x1=52.88)
    base = MS.prism(P, -30.6, 30.6)
    cut = []
    for z in (-112.0, -69.0, -26.0):
        for sg in (1, -1):
            cut.append(MS.prism(rrect(5.0, 47.0, z - 1.0, z + 1.0, 0.95), sg * 29.8, sg * 40.0))
    return Part("butt_pad", base, [("D", cut)], cls="P-round", slot=SLOT_CHASSIS, recipe=[(3.0, 2, 30.0)],
                spec_id="butt_pad")


def pad_plate():
    P = clip(ring("pad_plate", 1.0), x0=52.92, x1=68.88)
    base = MS.prism(P, -24.0, 24.0)
    return Part("pad_plate", base, slot=SLOT_CHASSIS, recipe=CH4)


def cheek_riser():
    d = dims("cheek_riser")
    z0, z1 = d["plate_Z"]
    P = np.array([(68.9, z0 + 6.0), (74.9, z0), (179.9, z0), (179.9, z1), (68.9, z1)])
    base = MS.prism(P, -34.5, 34.5)
    # side skirts (the sheet draws the riser as a closed block down to the butt): they hang outside the butt's sides
    # (|Y| 30.0..34.5, 0.4 clear of the butt at +-29.6) and slide down beside it at the low stop
    sk = np.array([(84.0, -16.4), (176.0, -16.4), (179.9, -12.5), (179.9, z0 + 0.5), (72.0, z0 + 0.5)])
    skirts = [MS.prism(sk, 30.0, 34.5), MS.prism(sk, -34.5, -30.0)]
    # the riser's front block (traced as the strip X 183.6..209.4, Z -4.7..31.8; background below it on the sheet)
    rr = rings("butt", 1.3, min_area=300.0)
    main = max(rr, key=lambda r: abs(G.area(r)))
    for t in [r for r in rr if r is not main]:
        skirts.append(MS.prism(clip(G.offset(t, 0.2), x0=179.0, z0=-4.7, z1=31.0), -29.0, 29.0))   # top 31.0 (L2)
        skirts.append(MS.box(179.5, 185.0, -29.0, 29.0, -4.7, 30.9))
    # cheek dish on the left top (1.5 mm), comb top edges 3 mm chamfers
    cut = [MS.ellipsoid((128.0, 26.0, z1 + 60.0), 60.0, 30.0, 61.5, 48, 16)]
    for sg in (1, -1):
        cut.append(yz_prism(np.array([(sg * 31.5, z1 + 1), (sg * 40.0, z1 + 1), (sg * 40.0, z1 - 7.5)])[::(1 if sg > 0 else -1)],
                            60.0, 190.0))
    mo = {"kind": "translate", "axis": [0, 0, 1], "range": list(d["travel_Z"])}
    return Part("cheek_riser", base, [("U", skirts), ("D", cut)], bone="cheek_riser", slot=SLOT_CHASSIS, recipe=RND1,
                jnt=joint("sliding", parent="butt"), motion=mo)


def riser_posts():
    d = dims("cheek_riser")
    m = MS.Mesh()
    for x in d["posts_X"]:
        m.extend(MS.revolve([(0.0, 0.0), (0.0, 4.38), (0.6, 4.98), (43.15 - 0.6, 4.98), (43.15, 4.38), (43.15, 0.0)],
                            (x, 0, -46.7), (0, 0, 1), 32))
    return Part("riser_posts", m, bone="cheek_riser", recipe=[], jnt=joint("sliding", parent="butt"),
                spec_id="cheek_riser", motion={"kind": "translate", "axis": [0, 0, 1], "range": list(d["travel_Z"])})


def riser_lever():
    # on the butt's left below the riser skirts' lowest reach (Z -29.3 at the low stop); GL draws it at Z -10, where
    # the skirts now hang (declared)
    m = MS.prism(rrect(84.0, 104.0, -40.0, -34.0, 2.5), 29.62, 32.6)
    return Part("riser_lever", m, [("U", [ycyl(92.0, -37.0, 29.62, 34.2, 4.0, 24)])], recipe=CH4, spec_id="cheek_riser")


def butt_knobs():
    m = MS.Mesh()
    for k in dims("butt")["clamp_knobs"]:
        x, z = k["centre_XZ"]
        r = k["dia"] / 2
        y0 = -half_at(BUTT_HALF, x) - 0.02
        prof = [(0.0, 0.0), (0.0, r * 0.7), (0.4, r - 0.6), (0.9, r), (1.6, r), (2.0, r - 0.5), (2.0, 0.0)]
        m.extend(MS.revolve(prof, (x, y0, z), (0, -1, 0), 24))
    # knurl as geometry: 24 shallow flutes on each cap's skirt
    cut = []
    for k in dims("butt")["clamp_knobs"]:
        x, z = k["centre_XZ"]
        r = k["dia"] / 2
        y0 = -half_at(BUTT_HALF, x)
        for i in range(16):
            a = 2 * math.pi * i / 16
            c = np.array([x + (r + 0.1) * math.cos(a), 0, z + (r + 0.1) * math.sin(a)])
            cut.append(MS.cylinder(c + [0, y0 + 0.6, 0], c + [0, y0 - 2.6, 0], 0.45, 8))
    return Part("butt_knobs", m, [("D", cut)], recipe=[], spec_id="butt")


# ------------------------------------------------------------------------------------------------ action
def receiver():
    base = MS.revolve([(0.0, 0.0), (0.0, 16.6), (0.55, 17.15), (185.3 - 0.55, 17.15), (185.3, 16.6), (185.3, 0.0)],
                      (382.0, 0, 0), (1, 0, 0), 48)
    cut = [xcyl(370.0, 493.0, 9.15, nseg=40),                                   # bolt bore (sliding 0.25)
           xcyl(492.6, 505.3, 12.95, nseg=48),                                  # lug-rotation annulus
           xcyl(505.3, 580.0, 13.02, nseg=48),                                   # barrel tenon thread bore
           xcyl(566.4, 568.0, 13.6, nseg=48)]                                   # thread relief at the front face
    for a in (330.0, 90.0, 210.0):                                              # lug raceway grooves (unlocked)
        cut.append(sector(370.0, 492.7, 0.0, 12.95, a - 26.0, a + 26.0, 10))
    cut.append(MS.prism(rrect(415.0, 507.1, -1.0, 14.3, 3.0), -40.0, -2.0))    # ejection port (right)
    cut.append(MS.box(417.5, 488.5, -9.0, 9.0, -30.0, -5.0))                    # feed port (bottom)
    cut.append(sector(370.0, 397.0, 0.0, 25.0, 108.0, 252.0, 18))              # bolt-handle notch (rear right)
    return Part("receiver", base, [("D", cut)], recipe=CH4)


def rail():
    d = dims("rail")
    M4 = RAIL.placement((385.8, 0.0, 20.5))
    p, rec = RAIL.part("rail", M4, 15, slot=SLOT_METAL, pad_rear=d["end_webs"], pad_front=d["end_webs"])
    m = MS.Mesh()
    for s in p.solids:
        m.extend(s)
    saddle = MS.box(386.3, 546.1, -8.0, 8.0, 14.0, 20.8)
    pt = Part("rail", m, [("U", [saddle]), ("D", [xcyl(380.0, 552.0, 17.19, nseg=48)])], recipe=[])
    pt.rec = rec
    return pt


def rail_screws():
    d = dims("rail")
    m = MS.Mesh()
    floor_z = 30.0 - 3.0
    for k in d["screws_in_slots"]:
        x = d["slot0_X"] + k * d["pitch"]
        h = HW.button_head(2.5, shank_len=0.01, nseg=8)
        m.extend(HW.place(h, (x, 0.0, floor_z + 0.02), (0, 0, 1), ref=(math.cos(k), math.sin(k), 0)))
    return Part("rail_screws", m, recipe=[], spec_id="rail")


def bolt():
    # body r 8.9 X 380..505 (face recessed), shroud X 345.4..380 r 12.0 with a rear dome, 3 lugs (locked at 30/150/270)
    prof = [(345.4, 0.0), (345.4, 4.0), (346.2, 8.0), (348.0, 11.0), (350.0, 12.0), (379.4, 12.0), (380.0, 11.4),
            (380.0, 8.9), (504.4, 8.9), (505.0, 8.3), (505.0, 0.0)]
    x0 = prof[0][0]
    base = MS.revolve([(x - x0, r) for x, r in prof], (x0, 0, 0), (1, 0, 0), 32)
    un = [sector(493.0, 505.0, 7.5, 12.7, a - 25.0, a + 25.0, 10) for a in (30.0, 150.0, 270.0)]
    un.append(xcyl(343.4, 345.6, 2.2, nseg=16))                                  # cocking indicator tip
    cut = [xcyl(504.0, 506.0, 6.1, nseg=32),                                      # recessed face
           MS.box(503.8, 506.0, -9.5, -5.0, -1.6, 1.6),                           # extractor slot (right)
           MS.cylinder((500.0, 0, 3.2), (506.0, 0, 3.2), 1.2, 12)]               # ejector plunger hole
    mo = {"kind": "bolt", "rotate_x_deg": [0.0, MO.BOLT_ROT], "slide_mm": [0.0, MO.BOLT_TRAVEL]}
    return Part("bolt", base, [("U", un), ("D", cut)], bone="bolt", cls="M-round", recipe=[(0.3, 1, 30.0)],
                jnt=joint("sliding", also="lugs hinge 0.10-0.30 while turning"), motion=mo)


def bolt_handle():
    k = dims("bolt_handle")
    kc = np.array(k["knob_centre_M"], float)
    rk = k["knob_dia"] / 2
    ang = math.atan2(kc[2], kc[1])
    root = np.array([388.5, 8.0 * math.cos(ang), 8.0 * math.sin(ang)])
    d = kc - root
    L = np.linalg.norm(d)
    u = d / L
    stem_end = kc - u * (rk - 1.0)
    tc = L + 1.5                                                               # knob centre on the profile axis
    f0 = math.asin(3.6 / rk)
    ball = [(tc - rk * math.cos(f), rk * math.sin(f)) for f in np.linspace(f0, math.pi, 14)]
    ball[-1] = (tc + rk, 0.0)
    m = MS.revolve([(-1.5, 0.0), (-1.5, 6.0), (4.0, 5.6), (12.0, 4.7), (L - rk - 4.0, 4.0), (L - rk - 1.5, 4.0),
                    (L - rk - 1.2, 3.6)] + ball, root - u * 1.5, u, 28)
    # the boss runs 2 mm past the stem's base disk at the rear (the stem poked 1.1 mm out of its end face: slivers)
    boss = MS.cylinder(root - u * 1.0 + np.array([-7.5, 0, 0]), root - u * 1.0 + np.array([5.0, 0, 0]), 5.6, 24)
    mo = {"kind": "bolt", "rotate_x_deg": [0.0, MO.BOLT_ROT], "slide_mm": [0.0, MO.BOLT_TRAVEL]}
    return Part("bolt_handle", m, [("U", [boss]), ("D", [xcyl(370.0, 410.0, 8.95, nseg=40)])], bone="bolt", cls="M-round",
                recipe=[], jnt=joint("integral", parent="bolt"), motion=mo)


def safety():
    p = MO.SAFETY_PIVOT
    P = np.array([(356.0, -19.0), (364.0, -19.0), (364.5, -4.0), (363.0, -2.0), (357.0, -2.0), (355.5, -4.0)])
    m = MS.prism(P, -21.5, -17.6)
    hub = ycyl(p[0], p[2], -21.5, -17.6, 3.6, 24)
    cut = [ycyl(p[0], p[2], -25.0, -15.0, 1.7, 20)]
    for i in range(4):                                                           # serrated thumb face
        z = -3.0 - i * 1.2
        cut.append(MS.box(355.0, 366.0, -21.9, -21.1, z - 0.3, z + 0.3))
    mo = {"kind": "rotate", "axis": [0, 1, 0], "pivot_M": p.tolist(), "range": [-12.0, 0.0]}
    return Part("safety", m, [("U", [hub]), ("D", cut)], bone="selector", recipe=CH4, jnt=joint("hinge"), motion=mo)


def pins():
    """Transverse pins (hidden or flush): trigger, release, safety."""
    m = MS.Mesh()
    hw = half_at(CHASSIS_HALF, 368.0) - 0.02
    m.extend(ycyl(368.0, -57.0, -hw, hw, 1.48, 24))
    m.extend(ycyl(408.6, -74.0, -8.0, 8.0, 1.48, 24))          # (W4 C9) hidden: its end sat on the outline, half in air
    m.extend(ycyl(360.0, -16.0, -21.8, -12.5, 1.48, 24))
    return Part("pins", m, recipe=[(0.2, 1, 30.0)], spec_id="pins_fasteners")


TRIGGER_BACK_MM = 5.0


def trigger():
    face = [(366.0, -61.0), (364.4, -66.0), (363.4, -71.0), (363.2, -75.0), (363.5, -80.0), (364.6, -84.5),
            (366.6, -88.0), (368.8, -89.6)]
    back = [(370.6, -88.0), (369.6, -84.0), (368.8, -80.0), (368.6, -75.0), (369.0, -70.0), (370.0, -65.0),
            (371.2, -61.0)]
    # W3 Part 0 (user OK 2026-10-13): the blade 5 mm further back, as drawn (the trace's blade sits 5-6 mm behind the
    # W1 one); the root at the pivot stays (blend from Z -61.5 to -67), the hub and pocket are unchanged
    def back5(x, z):
        return x - TRIGGER_BACK_MM * min(max((-61.5 - z) / 5.5, 0.0), 1.0)
    face = [(back5(x, z), z) for x, z in face]
    back = [(back5(x, z), z) for x, z in back]
    P = np.array([(365.0, -57.0)] + face + back + [(371.4, -57.0)])
    m = MS.prism(P, -3.0, 3.0)
    hub = ycyl(368.0, -57.0, -3.0, 3.0, 4.0, 32)
    mo = {"kind": "rotate", "axis": [0, 1, 0], "pivot_M": MO.TRIGGER_PIVOT.tolist(), "range": [0.0, 6.0]}
    return Part("trigger", m, [("U", [hub]), ("D", [ycyl(368.0, -57.0, -5, 5, 1.65, 20)])], bone="trigger", cls="C-fillet",
                recipe=[(0.8, 2, 30.0)], jnt=joint("hinge"), motion=mo)


CATCH_NOSE = (415.75, -47.5)          # the hook's top-front corner, seated (frame M, XZ)
# the M4 spring-catch mode (gunlib magfit_check): the magazine cams the catch back, nose move <= 0.6 mm per 0.5 mm step
CATCH_SPRING = {"nose_M": [CATCH_NOSE[0], 0.0, CATCH_NOSE[1]], "cam_mm_per_step": 0.6}


def mag_release():
    # (W4 A1) the real spring-catch hook: a flat bearing top at Z -47.5 (0.2 under the notch's top face), the nose at
    # X 415.75 (1.65 into the notch), and a 41 deg ramp underside the magazine's rear wall cams back on the way in
    # (was a square hook with a sloped top: bearing 0.87, engagement 1.45, the nose rode the wall at rest)
    P = np.array([(405.6, -114.0), (409.0, -114.5), (410.6, -112.0), (410.6, -52.6), (412.8, -52.6),
                  (CATCH_NOSE[0], CATCH_NOSE[1] - 1.7), CATCH_NOSE, (405.6, -47.5)])
    m = MS.prism(P, -5.0, 5.0)
    cut = [ycyl(408.6, -74.0, -6, 6, 1.65, 20),
           MS.box(410.9, 416.0, 4.4, 6.0, -53.0, -47.0), MS.box(410.9, 416.0, -6.0, -4.4, -53.0, -47.0)]  # hook 8.8 wide
    for i in range(5):                                                           # finger-pad grooves
        z = -98.0 - i * 3.0
        cut.append(MS.box(410.0, 411.2, -6.0, 6.0, z - 0.5, z + 0.5))
    mo = {"kind": "rotate", "axis": [0, 1, 0], "pivot_M": MO.RELEASE_PIVOT.tolist(), "range": [-4.5, 0.0]}
    return Part("mag_release", m, [("D", cut)], bone="mag_release", recipe=CH4, jnt=joint("hinge"), motion=mo)


def grip():
    P = G.ccw(G.dp_simplify(G.clean_smooth(ring("grip", 0.5), step=1.0, sigma_mm=1.5, corner_deg=50.0), 0.2))
    P = clip(P, x0=222.03, x1=X_GRIP_FRONT - 0.03, z1=Z_GRIP_SPLIT - 0.03)
    base = MS.prism(P, -16.0, 16.0)
    # flared base (+1.5 per side below Z -150), 1.5 deg draft taper toward the top front
    un = [MS.prism(clip(P, z1=-150.0), -17.2, 17.2)]
    return Part("grip", base, [("U", un)], cls="P-round", slot=SLOT_CHASSIS, recipe=POLY)


def barrel():
    b = dims("barrel")
    r0, r1 = b["od_at_forend"] / 2, b["od_at_device"] / 2
    xs = 505.5

    def rr(x):
        return r0 + (r1 - r0) * (x - 567.3) / (1049.7 - 567.3)

    prof = [(505.5, 0.0), (505.5, 12.2), (506.0, 12.97), (566.8, 12.97), (567.32, 17.0), (567.9, r0), (1049.2, r1),
            (1049.7, r1 - 0.5), (1049.7, 7.95), (1063.5, 7.95), (1064.5, 6.95), (1064.5, 0.0)]
    prof[3:5] = [(567.33, 12.97), (567.34, 17.0)]

    base = MS.revolve([(x - xs, r) for x, r in prof], (xs, 0, 0), (1, 0, 0), 48)
    fx0, fx1 = b["flutes"]["X"]
    cut = []
    for i in range(6):
        a = math.radians(30.0 + 60.0 * i)
        dirv = np.array([0.0, math.cos(a), math.sin(a)])
        p0 = np.array([fx0 + 3.0, 0, 0]) + dirv * (rr(fx0 + 3.0) + 1.0)
        p1 = np.array([fx1 - 3.0, 0, 0]) + dirv * (rr(fx1 - 3.0) + 1.0)
        cut.append(MS.capsule(p0, p1, 3.0, 16, 4))
    cut.append(xcyl(1034.0, 1066.0, 3.9, nseg=24))                              # bore, darkened in W2
    return Part("barrel", base, [("D", cut)], recipe=[(0.3, 1, 30.0)])


def muzzle_device():
    """Closed-sleeve linear compensator as one revolved loop (no booleans): tenon bore, expansion chamber, a baffle
    with a 9.2 mm hole, the 12 mm exit, the rear collar step and the 2 x 45 front chamfer."""
    from gunlib.parts.sights_flip import revolve_loop
    x0 = 1049.74                       # (W1 follow-up G5) 0.04 axial to the barrel shoulder (0.02 sampled 0.0072)
    loop = [(0.9, 8.04), (0.0, 8.9), (0.0, 17.55), (2.28, 17.55), (2.58, 18.05), (48.28, 18.05), (50.28, 16.05), (50.28, 6.0),
            (44.28, 6.0), (44.28, 12.0), (31.28, 12.0), (31.28, 4.6), (29.28, 4.6), (29.28, 12.0), (14.88, 12.0),
            (14.88, 8.04)]
    m = revolve_loop(loop, (x0, 0, 0), (1, 0, 0), 32)
    return Part("muzzle_device", m, bone="muzzle_device", recipe=[(0.4, 1, 30.0)])


# ------------------------------------------------------------------------------------------------ magazine
# (W4 A1) body top -20.0 -> -21.2: the shelf (-19.7) is the magazine's stop at 1.5 mm overtravel (was 0.3, under the
# gunlib 1.0-2.0 row); the lips and the top round rise 0.5 (round top to the bolt 2.32 -> 1.82)
MAG = dict(x0=414.1, x1=503.3, hy=13.25, z_bottom=-128.0, z_body_top=-21.2)
MAG_TOP_RISE = 0.5
MAG_FLOOR_K = 0.0945     # W1 follow-up L2: both side views draw the floor rising 5.4 deg toward the front (spec)


def mag_floor_z(x, dz=0.0):
    return MAG["z_bottom"] + MAG_FLOOR_K * (np.asarray(x, float) - MAG["x0"]) + dz


def magazine():
    g = MAG
    def rr3(c, z):
        P = G.rounded_rect(g["x0"] + c, g["x1"] - c, -g["hy"] + c, g["hy"] - c, 2.0 - c, 4)
        return np.c_[P, np.full(len(P), z)]
    ch = 0.6                                                                    # the 0.6 x 45 chamfers, as geometry
    def rrf(c, dz):                                                             # a ring on the sloped floor
        P = rr3(c, 0.0)
        P[:, 2] = mag_floor_z(P[:, 0], dz)
        return P
    base = MS.loft([rrf(ch, 0.0), rrf(0.0, ch), rr3(0.0, g["z_body_top"] - ch), rr3(ch, g["z_body_top"])])
    lp = lambda c, z: np.c_[G.rounded_rect(418.0 + c, 488.0 - c, -8.0 + c, 8.0 - c, 1.5 - c, 3),
                            np.full(len(G.rounded_rect(418.0 + c, 488.0 - c, -8.0 + c, 8.0 - c, 1.5 - c, 3)), z)]
    lips = MS.loft([lp(0.0, g["z_body_top"] - 1.0), lp(0.0, -14.3 + MAG_TOP_RISE)])          # square top: the round's nose cuts one plane
    # top round (its nose ends square at r 2.8: the lip plane 0.6 over its axis then cuts the end disk, not the tip)
    rnd = MS.revolve([(0.0, 0.0), (0.0, 3.0), (2.0, 3.9), (52.0, 3.9), (58.0, 2.8), (58.0, 0.0)],
                     (425.0, 2.2, -14.9 + MAG_TOP_RISE), (1, 0, 0), 24)
    cut = [MS.box(g["x0"] - 1.0, g["x0"] + 2.2, -4.8, 4.8, -52.4, -47.3)]           # catch notch (rear wall, 2.2 deep)
    for x in (440.0, 478.0):                                                    # pressed ribs (recessed 0.8)
        for sg in (1, -1):
            cut.append(MS.prism(stadium(-117.0, -74.0, x - 2.0, x + 2.0)[:, ::-1], sg * (g["hy"] - 0.8), sg * 20.0))
    mo = {"kind": "translate", "axis": [0, 0, -1], "range": [0.0, 67.8], "path": "straight"}
    return Part("magazine", base, [("U", [lips, rnd]), ("D", cut)], bone="magazine", cls="S-bend", slot=SLOT_MAG,
                recipe=[], jnt=joint("seated_mag"), motion=mo)


def magazine_floorplate():
    g = MAG
    sec = G.rounded_rect(g["x0"] - 1.5, g["x1"] + 1.5, -g["hy"] - 1.5, g["hy"] + 1.5, 3.0, 4)
    ring = lambda dz: np.c_[sec, mag_floor_z(sec[:, 0], dz)]                     # follows the sloped floor
    m = MS.loft([ring(-4.3), ring(-0.03)])
    return Part("magazine_floorplate", m, bone="magazine", cls="P-round", slot=SLOT_MAG, recipe=[(1.0, 2, 30.0)],
                jnt=joint("seated_mag"), spec_id="magazine")


# ------------------------------------------------------------------------------------------------ bipod
HUBX, HUBZ = 719.6, -62.3
LEG_R = 9.7
COLLAR = (877.6, 896.4)
FOOT = (896.6, 925.6)


def bipod_clamp():
    c = dims("bipod_mount")["clamp"]
    x0, x1 = c["X"]
    # jaw plate (Y +-25, Z -44.0..-39.61) on the dovetail seat over a narrow swivel housing (Y +-9.0, down to -52.4):
    # the folded legs (|Y| >= 9.8) cant +-15 beside the housing (W0 analytic worst 7.7 mm to the forend)
    P = np.array([(-9.0, -52.4), (9.0, -52.4), (9.0, -44.0), (25.0, -44.0), (25.0, -40.6), (24.0, -39.61),
                  (-24.0, -39.61), (-25.0, -40.6), (-25.0, -44.0), (-9.0, -44.0)])
    m = yz_prism(P, x0, x1)
    cut = [xcyl(x0 - 1, x1 + 1, 6.0, z=MO.CANT_Z, nseg=32), MS.box(x0 - 1, x1 + 1, -5.0, 5.0, -53.0, -46.0)]
    un = [HW.place(HW.socket_cap(2.8, 3.0, 24), (780.0, 25.0, -41.9), (0, 1, 0))]       # left throw screw (plain)
    return Part("bipod_clamp", m, [("D", cut), ("U", un)], slot=SLOT_CHASSIS, recipe=[(0.5, 1, 30.0)],
                spec_id="bipod_mount")


def bipod_swivel():
    c = dims("bipod_mount")["clamp"]
    x0, x1 = c["X"]
    m = xcyl(x0 + 0.3, x1 - 0.3, 5.8, z=MO.CANT_Z, nseg=32)                     # cant hub in the clamp channel
    disk = [(HUBX - 6.5 + 23.0 * math.cos(t), HUBZ + 18.0 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 40, endpoint=False)]
    yoke = MS.prism(clip(G.ccw(np.array(disk)), z1=-46.8), -9.55, 9.55)
    neck = MS.prism(np.array([(735.0, -56.0), (x0 + 6.0, -56.0), (x0 + 6.0, -46.0), (735.0, -46.0)]), -3.0, 3.0)
    arm = MS.box(705.0, 752.0, -3.0, 3.0, -50.5, -46.0)
    knob_sh = xcyl(730.0, 736.0, 3.0, z=-78.2, nseg=20)
    # L8 fix round: a real yoke: a rear web behind the knuckles (free in both leg poses) carrying two outboard pivot
    # cheeks (|Y| 29.5..32.4, 0.3 off the knuckles), all below Z -54 so the bracket cants +-15 under the forend
    web = MS.box(691.0, 704.0, -32.4, 32.4, -79.0, -54.0)
    cheeks, cut = [], []
    for side, sg in (("l", 1), ("r", -1)):
        # splay (user 2026-10-13): each pin is rolled SPLAY about its leg axis; the cheek, its bore and the yoke's
        # side face roll with it (the knuckle sits 0.25 off a face square to its own pin)
        Rr = MO.leg_roll(side)
        cp = [(HUBX + 11.5 * math.cos(t), HUBZ + 11.5 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 28, endpoint=False)]
        ya, yb = min(sg * 29.5, sg * 32.4), max(sg * 29.5, sg * 32.4)
        # (the roll lifts the cheek's outer top ~2.7 mm: clipped at -56.8 so it stays under Z -54 as in W1; at -54
        # the rolled cheeks met the forend underside at cant +-15)
        cheeks.append(MS.prism(clip(G.ccw(np.array(cp)), z1=-56.8), ya, yb).transformed(Rr))
        cheeks.append(MS.box(690.5, HUBX, ya, yb, HUBZ - 11.5, -56.8).transformed(Rr))
        yl = sg * MO.LEG_Y
        cut.append(ycyl(HUBX, HUBZ, min(yl - sg * 16.5, yl + sg * 16.5), max(yl - sg * 16.5, yl + sg * 16.5), 2.52,
                        24).transformed(Rr))                                       # leg pin bore
        y0, y1 = yl - sg * 9.95, yl - sg * 9.95 + sg * 12.0                      # the knuckle's slot in the yoke
        cut.append(MS.box(704.5, 745.0, min(y0, y1), max(y0, y1), -95.0, -40.0).transformed(Rr))
    # (the web behind the knuckles, X < 704, stays whole: the slot cutters start at 704.5)
    mo = {"kind": "rotate", "axis": [1, 0, 0], "pivot_M": [0.0, 0.0, MO.CANT_Z], "range": [-15.0, 15.0]}
    return Part("bipod_swivel", m, [("U", [yoke, neck, arm, knob_sh, web] + cheeks), ("D", cut)], bone="bipod", slot=SLOT_CHASSIS,
                recipe=[(0.5, 1, 30.0)], jnt=joint("hinge"), spec_id="bipod_mount", motion=mo)


def bipod_knob():
    prof = [(0.0, 0.0), (0.0, 6.2), (0.6, 7.0), (9.4, 7.0), (10.0, 6.2), (10.0, 0.0)]
    m = MS.revolve(prof, (736.02, 0, -78.2), (1, 0, 0), 24)
    cut = []
    for i in range(10):
        a = 2 * math.pi * i / 10
        c = np.array([0, 7.0 * math.cos(a), -78.2 + 7.0 * math.sin(a)])
        cut.append(MS.cylinder(c + [737.5, 0, 0], c + [744.5, 0, 0], 0.55, 6))
    mo = {"kind": "rotate", "axis": [1, 0, 0], "pivot_M": [0.0, 0.0, MO.CANT_Z], "range": [-15.0, 15.0]}
    return Part("bipod_knob", m, [("D", cut)], bone="bipod", recipe=[(0.3, 1, 30.0)], spec_id="bipod_mount",
                motion=mo)


def bipod_pins():
    m = MS.Mesh()
    for side, sg in (("l", 1), ("r", -1)):
        Rr = MO.leg_roll(side)                                                  # angled pins (splay)
        y0, y1 = sg * 9.6, sg * 32.5
        m.extend(ycyl(HUBX, HUBZ, min(y0, y1), max(y0, y1), 2.45, 24).transformed(Rr))
        m.extend(ycyl(HUBX, HUBZ, min(sg * 32.42, sg * 34.0), max(sg * 32.42, sg * 34.0), 4.5, 24).transformed(Rr))
    mo = {"kind": "rotate", "axis": [1, 0, 0], "pivot_M": [0.0, 0.0, MO.CANT_Z], "range": [-15.0, 15.0]}
    return Part("bipod_pins", m, bone="bipod", recipe=[(0.2, 1, 30.0)], spec_id="bipod_mount", motion=mo)


def bipod_leg(side):
    y = MO.LEG_Y if side == "l" else -MO.LEG_Y
    sg = 1 if side == "l" else -1
    m = MS.revolve([(0.0, 0.0), (0.0, 4.0), (3.0, 8.0), (9.0, LEG_R), (COLLAR[0] - HUBX, LEG_R), (COLLAR[0] - HUBX, 0.0)],
                   (HUBX - 9.0, y, HUBZ), (1, 0, 0), 20)
    collar = MS.revolve([(0.0, 0.0), (0.0, 13.2), (0.8, 14.0), (18.0, 14.0), (18.8, 13.2), (18.8, 0.0)],
                        (COLLAR[0], y, HUBZ), (1, 0, 0), 20)
    knuckle = ycyl(HUBX, HUBZ, y - LEG_R, y + LEG_R, 9.0, 24)
    button = MS.revolve([(0.0, 0.0), (0.0, 3.5), (3.0, 3.5), (3.6, 2.9), (3.6, 0.0)], (887.0, y + sg * 12.9, HUBZ),
                        (0, sg, 0), 20)
    detent = ycyl(HUBX, HUBZ, y + sg * (LEG_R - 0.5), y + sg * (LEG_R + 0.1), 7.0, 24)   # notched hub disk
    cut = [ycyl(HUBX, HUBZ, y - 12, y + 12, 2.65, 20),                          # pin bore (hinge 0.15)
           xcyl(800.0, 897.0, 8.2, y=y, z=HUBZ, nseg=20)]                       # telescoping bore (sliding 0.25)
    for a in (0.0, 90.0):                                                       # the two detent notches
        t = math.radians(a + 180.0)
        c = np.array([HUBX + 5.6 * math.cos(t), 0, HUBZ - 5.6 * math.sin(t)])
        cut.append(MS.cylinder(c + [0, y + sg * (LEG_R - 0.6), 0], c + [0, y + sg * (LEG_R + 1.5), 0], 1.1, 12))
    # the mount bottom 0.2 above the folded leg: the knuckle's top under the swivel yoke is trimmed by the yoke gap
    mo = {"kind": "rotate", "axis": [0, 1, 0], "pivot_M": [HUBX, y, HUBZ], "range": [0.0, 90.0], "detents": [0.0, 90.0]}
    Rr = MO.leg_roll(side)                                                      # built on the angled pin (splay)
    m, collar, knuckle, button, detent = (x.transformed(Rr) for x in (m, collar, knuckle, button, detent))
    cut = [c.transformed(Rr) for c in cut]
    return Part(f"bipod_leg_{side}", m, [("U", [collar, knuckle, button, detent]), ("D", cut)],
                bone=f"bipod_leg_{side}", cls="M-round", slot=SLOT_CHASSIS, recipe=[(0.6, 1, 30.0)],
                jnt=joint("hinge"), spec_id=f"bipod_leg_{side}", motion=mo)


def bipod_ext(side):
    y = MO.LEG_Y if side == "l" else -MO.LEG_Y
    m = xcyl(800.4, FOOT[0] + 4.0, 7.95, y=y, z=HUBZ, nseg=20)
    cut = []
    for k in range(5):                                                          # detent notch rings every 19 mm
        x = 801.0 + 19.0 * k + 10.0
        cut.append(MS.tube((x, y, HUBZ), (x + 2.4, y, HUBZ), 7.15, 9.0, 20))
    mo = {"kind": "translate", "axis_in_leg": [1, 0, 0], "range": [0.0, 76.0], "detents": [0.0, 19.0, 38.0, 57.0, 76.0]}
    Rr = MO.leg_roll(side)
    m, cut = m.transformed(Rr), [c.transformed(Rr) for c in cut]
    return Part(f"bipod_ext_{side}", m, [("D", cut)], bone=f"bipod_leg_{side}_ext", cls="M-round",
                recipe=[(0.3, 1, 30.0)], jnt=joint("sliding"), spec_id=f"bipod_ext_{side}", motion=mo)


def bipod_foot(side):
    y = MO.LEG_Y if side == "l" else -MO.LEG_Y
    x0, x1 = FOOT
    prof = [(0.0, 0.0), (0.0, 14.0), (1.2, 17.0), (4.0, 18.5), (12.0, 18.0), (14.5, 17.6), (17.0, 18.0), (25.0, 18.5),
            (27.8, 17.0), (29.0, 14.0), (29.0, 0.0)]
    m = MS.revolve(prof, (x0, y, HUBZ), (1, 0, 0), 28)
    cut = [xcyl(x0 - 1.0, x0 + 5.0, 7.97, y=y, z=HUBZ, nseg=20),
           MS.revolve([(0.0, 0.0), (0.0, 3.0), (1.2, 3.0), (1.2, 0.0)], (x1 - 1.2, y, HUBZ), (1, 0, 0), 24)]
    for xr in (x0 + 7.0, x0 + 22.0):                                            # moulded tread rings
        cut.append(MS.tube((xr, y, HUBZ), (xr + 1.4, y, HUBZ), 17.4, 20.0, 28))
    mo = {"kind": "translate", "axis_in_leg": [1, 0, 0], "range": [0.0, 76.0]}
    Rr = MO.leg_roll(side)
    m, cut = m.transformed(Rr), [c.transformed(Rr) for c in cut]
    return Part(f"bipod_foot_{side}", m, [("D", cut)], bone=f"bipod_leg_{side}_ext", cls="P-round",
                slot=SLOT_CHASSIS, recipe=[(0.8, 1, 30.0)], spec_id=f"bipod_ext_{side}", motion=mo)


def fasteners():
    m = MS.Mesh()
    for s in dims("pad_plate")["screws"]:
        x, z = s["centre_XZ"]
        d = s["dia"] / 1.5
        m.extend(HW.place(HW.socket_cap(d, 0.01, 16), (x, -24.0 - 0.03, z), (0, -1, 0), ref=(0.3, 0, 1)))
    m.extend(HW.place(HW.socket_cap(5.0, 0.01, 16), (389.6, -25.6 - 0.03, -38.3), (0, -1, 0), ref=(1, 0, 0.4)))
    return Part("fasteners", m, recipe=[], spec_id="pins_fasteners")


# ------------------------------------------------------------------------------------------------ registry
PARTS = {
    "chassis": chassis, "butt": butt, "butt_pad": butt_pad, "pad_plate": pad_plate, "cheek_riser": cheek_riser,
    "riser_posts": riser_posts, "riser_lever": riser_lever, "butt_knobs": butt_knobs, "receiver": receiver,
    "rail": rail, "rail_screws": rail_screws, "bolt": bolt, "bolt_handle": bolt_handle, "safety": safety,
    "pins": pins, "trigger": trigger, "mag_release": mag_release, "grip": grip, "barrel": barrel,
    "muzzle_device": muzzle_device, "magazine": magazine, "magazine_floorplate": magazine_floorplate,
    "bipod_clamp": bipod_clamp, "bipod_swivel": bipod_swivel, "bipod_knob": bipod_knob, "bipod_pins": bipod_pins,
    "bipod_leg_l": lambda: bipod_leg("l"), "bipod_leg_r": lambda: bipod_leg("r"),
    "bipod_ext_l": lambda: bipod_ext("l"), "bipod_ext_r": lambda: bipod_ext("r"),
    "bipod_foot_l": lambda: bipod_foot("l"), "bipod_foot_r": lambda: bipod_foot("r"),
    "fasteners": fasteners,
}


def build_all(only=None):
    coll = bl.collection(PARTS_COLL)
    res = {}
    for name, fn in PARTS.items():
        if only and name not in only:
            continue
        t0 = time.time()
        try:
            p = fn()
            ob, rep = p.build(coll)
            res[name] = rep
            print(f"[{CODE}] part {name}: tris {rep.get('triangles')} shells {rep.get('shells')} "
                  f"boundary {rep.get('boundary_edges')} in {time.time() - t0:.1f}s")
        except Exception as e:
            import traceback
            traceback.print_exc()
            res[name] = {"error": repr(e)}
            print(f"[{CODE}] part {name} FAILED: {e!r}")
    return res
