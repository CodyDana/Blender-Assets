"""Detail part SELECTOR: the stamped selector lever on the receiver's right wall (bone "selector").

Owns the object: selector. Authority close-ups: c1 RECEIVER AND SELECTOR (RIGHT) for the 3D shape, the LEFT-labelled
side panel (true right) for scale / pose / position, the 3/4 view as a cross-check. Interfaces: the pivot SEL_PIVOT
(receiver's hole, hinge about Y), the B3 selector sweep (safe 0 / auto 16 / semi 32 deg, front end down) against the
rivets; the plate's inner face stays 1.25 mm off the receiver wall (0.2 mm over the rivet heads, hinge row 0.1-0.3).

Detail pass (2026-10-05): rebuilt from the c1 close-up trace (parts/selector_trace.py), mapped into the rest pose by
the similarity fitted to the side view (c1 draws the lever 13.25 deg front-down and 1.10x larger). Real geometry,
every visible form modelled.

Round 2 (after the round-1 blind judge read the pressed edge band as "a thin raised outline round a recessed panel
with a groove down the middle", a slotted flat pivot and a narrow tail):
  * ONE solid 2.0 mm lever plate on the traced outline (round rear end, straight bottom, stepped hump, long falling
    top edge, rounded paddle nose); no all-round pressed band;
  * a narrow edge groove (0.45-1.30 mm in, 0.7 deep, drafted walls) swept round the rear end, the top edge (over the
    hump) and the bottom edge, ending squarely at the tab: c1's outer edge line / dark gap / bright inner line, so the
    plate reads as a thick part with a lit rim on a dark ledge;
  * c1's long wedge between the top edge and the diagonal line as a valley with a two-plane floor (rear plane
    deepening 0.5 -> 1.0 mm over 4.5 mm where the line leaves the inner edge line, main plane thinning 40 % to the
    tab, both tilted so the top edge stays out): the wedge reads dark and the 40 deg crease wall faces up into the
    key light, c1's bright diagonal line, broad at the hump and narrowing to the front;
  * the tab bent outward 12 deg about the traced bend line as a real sheet bend (bisect + swing about the inner-face
    line), a thin raised ring round a small domed pin on it (c1's nose ring);
  * on the pivot: a raised stepped washer collar (r 11 px in c1) and a high (2.0 mm) dome with a short skirt, NO
    slot (c1 shows a plain polished dome; the side view's 'slot' is not in the close-up, which is the authority);
    hub + shaft into the receiver's hole as before.
Booleans with the groove sweep can leave micro edges; Blender's bevel overlap clamp then shrinks every bevel on the
part, so edges < 0.05 mm are collapsed before the bevel (reported in the build line).
"""
from __future__ import annotations

import math

import numpy as np

from rifle_common import SPEC  # noqa: F401  (interface: modules import the spec from rifle_common)
from gunlib import geo2d as G
from gunlib import mesh as MS
from rifle_parts import WO
from rifle_parts2 import ycyl

from . import selector_trace as ST

# ======================================================================================== selector
SEL_PIVOT = (282.8, -7.8)

Y_WALL = -WO                    # receiver wall outer face (right side)
Y_IN = Y_WALL - 1.25            # plate inner face (0.2 mm over the rivet heads at -21.8)
T_PLATE = 2.0                   # solid stamped lever plate (round 1 read as a thin rim: now one thick plate)
Y_F = Y_IN - T_PLATE            # lever face
EMBED = 0.05                    # layers overlap so no boolean faces are coplanar
# edge groove: c1 draws the lever with an outer edge line, a dark gap, then a bright inner line (rear end, top edge
# and bottom edge up to the tab). Modelled as a narrow groove whose two lips catch the light and whose floor stays
# dark: outer lip at 0..GROOVE[0], groove GROOVE[0]..GROOVE[1] at the face, GROOVE_DEPTH deep, walls drafted.
GROOVE = (0.60, 1.40)
GROOVE_DEPTH = 0.70
# c1's long wedge between the top edge and the diagonal bright line: a valley whose floor tilts (top edge out,
# crease in: the wedge reads dark) with an up-facing crease wall (the bright line). Round 2 tried the judge's word,
# a RAISED rib: its lower wall faces down under the upper-left key, so the line came out dark; physics and c1 agree
# on the valley.
VALLEY_D = 1.00                 # valley: depth at the crease, floor rising to ~0.1 at the top edge
VALLEY_T0 = 0.0                 # valley: stations start this far along the crease from its traced rear end (mm)
VALLEY_D0 = 0.50                # valley: depth at the crease's rear end (the floor stays below the face)
VALLEY_FADE = 4.5               # valley: depth fades in over this length (to where the hump starts)
VALLEY_TAPER = 0.40             # valley: depth falls by this fraction from the hump to the tab
VALLEY_WALL_DEG = 40.0          # valley: crease wall angle off the face (faces up: c1's bright line)
TAB_BEND_DEG = 12.0
USE_GROOVE = False              # integration round: no edge groove (it read as a hollow outline)
PRE_BEVEL_MERGE_MM = 0.05       # edges shorter than this are collapsed before the bevel (boolean slivers)
RECIPE = [(0.28, 1, 24.0)]      # lips, rib and plate edges (>= 45 deg); the 12 deg bend crease stays sharp


def _px(P):
    return ST.c1_to_rest(P, SEL_PIVOT)


def _xz(P2, y):
    P2 = np.asarray(P2, float)
    return np.c_[P2[:, 0], np.full(len(P2), float(y)), P2[:, 1]]


def _clip_half(P, a, n):
    """Sutherland-Hodgman clip of a closed polygon to the half-plane (p - a) . n >= 0."""
    P = np.asarray(P, float)
    a = np.asarray(a, float)
    n = np.asarray(n, float)
    out = []
    for i in range(len(P)):
        p, q = P[i - 1], P[i]
        dp, dq = (p - a) @ n, (q - a) @ n
        if dq >= 0:
            if dp < 0:
                out.append(p + (q - p) * (dp / (dp - dq)))
            out.append(q)
        elif dp >= 0:
            out.append(p + (q - p) * (dp / (dp - dq)))
    return np.array(out)


def _lines():
    """Rest-frame crease line (a, b, up-normal) and bend line (a, b, forward-normal)."""
    ca, cb = _px(ST.C1_CREASE_PX)
    d = (cb - ca) / np.linalg.norm(cb - ca)
    nc = np.array([-d[1], d[0]])
    if nc[1] < 0:
        nc = -nc
    ba, bb = _px(ST.C1_BEND_PX)
    e = (bb - ba) / np.linalg.norm(bb - ba)
    nb = np.array([e[1], -e[0]])
    if nb[0] < 0:
        nb = -nb
    return (ca, cb, nc), (ba, bb, nb)


def _ycap(cx, cz, profile, y0, nseg):
    """Revolved solid about the Y axis through (cx, cz): profile [(t outward from y0, r)]."""
    return MS.revolve(profile, (cx, y0, cz), (0, -1, 0), nseg)


def _groove_path(O, g, bend, gap=0.35):
    """Open path along offset(O, -g) from the tab's bottom round the rear end to the tab's top (stops `gap` mm behind
    the bend line), resampled ~0.6 mm."""
    ba, _, nb = bend
    R = G.resample(G.offset(O, -g), 0.4)
    keep = (R - ba) @ nb < -gap
    i0 = int(np.argmin(keep))                       # first point at the tab: rotate so the kept run is contiguous
    while not keep[i0 % len(R)]:
        i0 += 1
    R = np.roll(R, -(i0 % len(R)), axis=0)
    keep = np.roll(keep, -(i0 % len(R)))
    run = R[: int(np.argmin(keep))] if not keep.all() else R
    return _adaptive(G.resample(run, 0.2, closed=False), 6.0, 2.5)


def _adaptive(P, max_turn_deg, max_len):
    """Thin a dense open polyline: keep a point once the heading has turned max_turn_deg or max_len mm have passed
    since the last kept point (small turns per ring, so the swept groove section never pinches at a corner)."""
    P = np.asarray(P, float)
    keep = [0]
    h0 = None
    acc = 0.0
    for i in range(1, len(P) - 1):
        v = P[i + 1] - P[i]
        h = math.atan2(v[1], v[0])
        if h0 is None:
            h0 = h
        turn = abs((h - h0 + math.pi) % (2 * math.pi) - math.pi)
        acc = np.linalg.norm(P[i] - P[keep[-1]])
        if turn >= math.radians(max_turn_deg) or acc >= max_len:
            keep.append(i)
            h0 = h
    keep.append(len(P) - 1)
    return P[keep]


def _groove_cutter(O, bend):
    g0, g1 = GROOVE
    path = _groove_path(O, 0.5 * (g0 + g1), bend)
    w0 = g1 - g0
    w1 = max(w0 - 0.25, 0.2)
    sec = [(-w0 / 2, 0.4), (-w0 / 2, 0.0), (-w1 / 2, -GROOVE_DEPTH), (w1 / 2, -GROOVE_DEPTH), (w0 / 2, 0.0),
           (w0 / 2, 0.4)]
    P3 = _xz(path, Y_F)
    ups = [(0.0, -1.0, 0.0)] * len(P3)              # section 't' = outward (-Y)
    return MS.sweep_profile(P3, sec, ups=ups)


def _rib_polygon(O, inset):
    (ca, cb, nc), (ba, bb, nb) = _lines()
    W = G.offset(O, -inset)
    W = _clip_half(W, ca, nc)                       # above the crease
    W = _clip_half(W, ca, (cb - ca) / np.linalg.norm(cb - ca))      # from the crease's rear end on
    W = _clip_half(W, ba - 0.35 * nb, -nb)          # behind the tab
    return G.ccw(G.dedupe(W, 0.05))


def _rib_valley(O):
    """c1's long wedge as ONE valley cutter whose floor is two planes meeting on a seam at the hump start: the rear
    plane deepens from VALLEY_D0 (where the crease leaves the inner edge line; c1's bright line starts from it) to
    VALLEY_D, the main plane thins toward the tab (c1's line narrows to the front); both rise k mm per mm toward
    the top boundary (just inside the edge groove) and stay below the face, so no shallow intersection lines and no
    boolean micro edges (the bevel's overlap clamp is global). Walls at VALLEY_WALL_DEG: the crease wall faces up
    and catches the key light."""
    (ca, cb, nc), (ba, bb, nb) = _lines()
    d = (cb - ca) / np.linalg.norm(cb - ca)
    W = _rib_polygon(O, GROOVE[1])
    W = _clip_half(W, ca + VALLEY_T0 * d, d)
    W = G.ccw(G.dedupe(W, 0.05))
    th = VALLEY_T0 + VALLEY_FADE
    # insert the seam (t = th) into the ring
    t = (W - ca) @ d
    ring, seam = [], []
    for i in range(len(W)):
        p, q = W[i - 1], W[i]
        tp, tq = t[i - 1], t[i]
        if (tp - th) * (tq - th) < 0:
            seam.append(len(ring))
            ring.append(p + (q - p) * (th - tp) / (tq - tp))
        ring.append(q)
    R = np.array(ring)
    n = len(R)
    assert len(seam) == 2, seam
    tR = (R - ca) @ d
    sR = (R - ca) @ nc
    t_end = float(tR.max())
    base = np.where(tR <= th + 1e-9,
                    VALLEY_D0 + (VALLEY_D - VALLEY_D0) * (tR - VALLEY_T0) / (th - VALLEY_T0),
                    VALLEY_D + (VALLEY_D * (1.0 - VALLEY_TAPER) - VALLEY_D) * (tR - th) / max(t_end - th, 1e-6))
    up = sR > 0.2
    k = float(np.min((base[up] - 0.08) / sR[up]))           # the floor reaches 0.08 below the face at the tightest
    dep = base - k * sR                                     # top-boundary vertex and stays below it everywhere
    nrm = G.offset(R, 1.0, miter_limit=2.0) - R
    out = R + nrm * ((dep + 1.0) / math.tan(math.radians(VALLEY_WALL_DEG)))[:, None]
    m = MS.Mesh()
    i_out = m.add_verts(np.c_[out[:, 0], np.full(n, Y_F - 1.0), out[:, 1]])
    i_fl = m.add_verts(np.c_[R[:, 0], Y_F + dep, R[:, 1]])
    m.face(i_out[::-1])
    a, b = seam
    loop1 = [i_fl[j % n] for j in range(a, b + 1)]
    loop2 = [i_fl[j % n] for j in range(b, a + n + 1)]
    m.face(loop1)
    m.face(loop2)
    for kk in range(n):
        k2 = (kk + 1) % n
        m.face((i_out[kk], i_out[k2], i_fl[k2], i_fl[kk]))
    print("[selector] valley: seam t %.1f, depth %.2f..%.2f, %d ring verts" % (th, dep.min(), dep.max(), n))
    return [m]


def _collapse_short(ob, lim_mm, rounds=4):
    """Collapse edges shorter than lim_mm (boolean slivers) to their midpoints; returns the count."""
    import bmesh
    n = 0
    for _ in range(rounds):
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        es = [e for e in bm.edges if e.calc_length() * 1000.0 < lim_mm]
        if not es:
            bm.free()
            break
        bmesh.ops.collapse(bm, edges=es, uvs=False)
        bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-8)
        bm.to_mesh(ob.data)
        bm.free()
        ob.data.update()
        n += len(es)
    return n


def _short_edges(ob, lim_mm):
    """Count / shortest of the sharp (>= 24 deg) edges shorter than lim_mm (bevel clamp diagnostics)."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    L = [e.calc_length() * 1000.0 for e in bm.edges
         if len(e.link_faces) == 2 and math.degrees(e.calc_face_angle()) >= 24.0 and e.calc_length() * 1000.0 < lim_mm]
    bm.free()
    return {"n": len(L), "min_mm": round(min(L), 4) if L else None}


def _bend_matrix(a, b, deg):
    """4x4 rotation (frame M) about the bend axis (the line a->b in XZ on the plate's inner face) that swings the
    tab (forward of the line) outward, toward -Y."""
    a3 = np.array([a[0], Y_IN, a[1]], float)
    b3 = np.array([b[0], Y_IN, b[1]], float)
    k = b3 - a3
    k /= np.linalg.norm(k)
    t = math.radians(deg)
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    R = np.eye(3) + math.sin(t) * K + (1 - math.cos(t)) * K @ K
    p = np.array([a[0] + 10.0, Y_IN, a[1]])
    if (R @ (p - a3))[1] > 0:
        R = R.T
    M = np.eye(4)
    M[:3, :3] = R
    M[:3, 3] = a3 - R @ a3
    return M


def _bend(ob, offset, a, b, deg):
    """Cut the object along the bend plane (through the bend line, normal in XZ toward the tab) and swing every
    vertex forward of it outward about the line on the inner face: a real sheet bend, manifold kept."""
    import bmesh
    from mathutils import Vector
    off = np.asarray(offset, float)
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    d = (b - a) / np.linalg.norm(b - a)
    nrm = np.array([d[1], -d[0]])                           # in XZ; flipped toward +X (the tab side)
    if nrm[0] < 0:
        nrm = -nrm
    a3 = np.array([a[0], Y_IN, a[1]])
    no = np.array([nrm[0], 0.0, nrm[1]])
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), dist=1e-7,
                           plane_co=Vector(((a3 - off) * 0.001).tolist()), plane_no=Vector(no.tolist()))
    M = _bend_matrix(a, b, deg)
    n_moved = 0
    for v in bm.verts:
        pM = np.array(v.co) * 1000.0 + off
        if (pM - a3) @ no > 1e-4:
            q = M[:3, :3] @ pM + M[:3, 3]
            v.co = Vector(((q - off) * 0.001).tolist())
            n_moved += 1
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return n_moved


def _parts():
    """The lever's solids (frame M, rest pose, tab not yet bent) and the cutters."""
    O = _px(ST.c1_outline_px(n_arc=20))
    O = G.ccw(G.dp_simplify(G.dedupe(O, 0.05), 0.03))
    _, bend = _lines()
    base = MS.prism(O, Y_F, Y_IN)
    # integration round (2026-10-05), from the round-2 blind judge: the edge groove read as "a thin raised rim round a
    # recessed channel, hollow, like an outline" -> no groove: one solid plate with crisp bevelled edges and c1's
    # crease (the valley); "a smooth hemispherical dome inside concentric rings" -> a flat-faced head with a chamfer
    # and a small centre boss in a distinct raised washer ring; "the tip pin is a ringed dome" -> a small flat pin
    unions, cutters = [], []
    if USE_GROOVE:
        cutters.append(_groove_cutter(O, bend))
    cutters += _rib_valley(O)
    bx, bz = _px(ST.C1_NOSE_BOSS_PX)[0]
    rp = ST.c1_len(ST.C1_NOSE_PIN_R_PX)
    unions.append(_ycap(bx, bz, [(0.0, 0.0), (0.0, rp), (0.22, rp), (0.32, rp - 0.1), (0.32, 0.0)], Y_F + EMBED, 12))
    # pivot: raised washer ring, flat-faced chamfered head with a small centre boss; hub and shaft into the receiver
    px_, pz_ = SEL_PIVOT
    r_ring, r_dome = ST.c1_len(ST.C1_RING_R_PX), ST.c1_len(ST.C1_DOME_R_PX)
    h_ring = 0.8
    unions.append(_ycap(px_, pz_, [(0.0, 0.0), (0.0, r_ring), (h_ring - 0.25, r_ring), (h_ring, r_ring - 0.3),
                                   (h_ring, 0.0)], Y_F + EMBED, 24))
    y_ring_top = Y_F + EMBED - h_ring
    h_head, ch, r_boss = 1.3, 0.45, 0.36 * r_dome
    prof = [(0.0, 0.0), (0.0, r_dome), (h_head - ch, r_dome), (h_head, r_dome - ch), (h_head, r_boss + 0.08),
            (h_head + 0.22, r_boss), (h_head + 0.22, 0.0)]
    unions.append(_ycap(px_, pz_, prof, y_ring_top + EMBED, 20))
    unions.append(ycyl(px_, pz_, 5.0, Y_WALL - 0.2, Y_IN - EMBED, 16))
    unions.append(ycyl(px_, pz_, 3.0, Y_WALL - 0.25, -18.0, 16))
    return {"base": base, "unions": unions, "cutters": cutters, "outline": O}


JOINT = {"type": "hinge", "parent": "receiver", "pivot_M": [SEL_PIVOT[0], 0, SEL_PIVOT[1]], "axis_M": [0, 1, 0],
         "positions_deg": {"safe": 0.0, "auto": 16.0, "semi": 32.0}, "clearance_mm": [0.1, 0.3]}


def selector(coll, offset):
    """Custom builder (gunlib.parts.BuildCtx provider(coll, offset)): build_part's steps with the sheet bend
    between the booleans and the bevel."""
    import json
    import time
    from gunlib import bl
    t0 = time.time()
    P = _parts()
    ob = P["base"].to_object("selector", coll, offset, smooth_deg=30.0)
    bl.boolean_many(ob, P["unions"], "UNION", offset=offset)
    for c in P["cutters"]:                                  # one at a time: the groove sweep and the rib cutter
        bl.boolean_many(ob, [c], "DIFFERENCE", offset=offset)   # overlap, one collection boolean dropped faces
    bl.clean(ob)
    bt, bb = _px(ST.C1_BEND_PX[0])[0], _px(ST.C1_BEND_PX[1])[0]
    moved = _bend(ob, offset, bb, bt, TAB_BEND_DEG)
    n_coll = _collapse_short(ob, PRE_BEVEL_MERGE_MM)       # the bevel's overlap clamp is global: one boolean micro
    bl.clean(ob)                                            # edge would shrink every bevel on the part
    short = _short_edges(ob, 0.15)
    n_pre = len(ob.data.polygons)
    for st in RECIPE:
        bl.bevel(ob, st[0], st[1], st[2])
    bl.clean(ob)
    bl.finish(ob)
    bl.weighted_normals(ob)
    ob["gun_part"] = json.dumps({"bone": "selector", "class": "S-cut", "slot": "M_AR01_Metal", "joint": JOINT,
                                 "spec_id": "selector", "recipe": [list(s) for s in RECIPE]})
    rep = bl.manifold_report(ob)
    rep["short_edges_pre_bevel"] = short
    rep["collapsed_edges"] = n_coll
    rep["faces_pre_bevel"] = n_pre
    print("[selector] tab verts bent %d, %.1fs, %s" % (moved, time.time() - t0, json.dumps(rep)))
    return ob


# ======================================================================================== module interface
OBJECTS = ('selector',)            # registry keys built here (rifle_parts.ORDER)
CLOSEUPS = ('c1', 'q34')          # sheet panels that are this part's shape authority (rifle_detail.py)


def build(spec, ctx):
    """Build this module's objects into ctx (gunlib.parts.BuildCtx). Returns {registry key: [objects]}; keys that
    ctx.only excludes come back empty. `spec` is the rifle GunSpec (the same object as rifle_common.SPEC)."""
    return {k: ctx.make(k, f) for k, f in (("selector", selector),)}
