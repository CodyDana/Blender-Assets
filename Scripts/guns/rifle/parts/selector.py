"""Detail part SELECTOR: the stamped selector lever on the receiver's right wall (bone "selector").

Owns the object: selector. Authority: the LEFT-labelled side panel (true right) for scale / pose / position and the
outline (spec feature face_outline_M), c1 RECEIVER AND SELECTOR (RIGHT) for the outline's details (rounded rear end,
step, nose tab and its bend line, the crease), the real stamped pattern for how it is made. Interfaces: the pivot
SEL_PIVOT (receiver's hole, hinge about Y), the B3 selector sweep (safe 0 / auto 16 / semi 32 deg, front end down)
against the rivets; the plate's inner face stays 1.25 mm off the receiver wall (over the rivet heads, hinge row
0.1-0.3); the charging handle's stem / knob pass over the blade's front at full bolt travel (B3 bolt sweep).

FORM REALISM ROUND (2026-10-05). Both realism judges on the detail-pass lever: "a short stubby paddle sitting high;
real: a long thin stamped blade reaching forward over the charging-handle slot, closing most of it on safe". The
detail-pass lever was a 2.0 plate on a 0.9 stepped skirt (a double outline), a sculpted rib / wedge relief, a 1.2 mm
washer and a 1.84 mm domed bolt head (3 mm of hardware standing off the blade). Rebuilt as the real part is made:
  * ONE flat stamped blade, 2.0 mm, full outline, crisp 0.3 mm edge breaks (no stepped skirt, no sculpted relief);
  * the upper edge from the step forward raised to Z TOP_Z (8.0): on safe the blade now covers the slot band (wall cut
    Z 3-9.2) up to 1.6 mm under the cover's skirt edge (9.6) -- it closes ~76 % of the slot as on the real lever;
    8.0 keeps the charging-handle stem (Z >= 8.6) and knob (Z >= 8.2) clear over the full bolt travel (B3);
  * c1's crease as a shallow pressed step (the strip above it set in 0.35 mm), a lit line along the blade;
  * the nose tab bent outward 12 deg about c1's bend line (a real sheet bend), a small flat pin on it;
  * the pivot: a low washer (0.5) and a low button head (0.9): the axle end, not a bolt standing off the lever.
Old build: git history (247d02bd, parts/selector.py).

LAST SHAPE ROUND (2026-10-05, orchestrator ruling 2: "the REAL long flat stamped plate from the rear pivot forward to
the charging-handle slot, covering the slot in the safe position; the sheet's shorter lever is an AI artifact").
Method: measured on a museum photo of the real stamped-receiver rifle (WorkFiles/guns/rifle/scratch/realref,
AKM_1980_assault_rifle.jpg, right side square on; scale from the selector pivot -> charging-handle knob, 0.192 mm/px):
pivot -> front tip 91 mm (ours was 73), the upper edge's step at X ~300-310, the flat top at Z ~8.5, the lower edge
rising at ~0.18 (ours 0.21), the front end ~9.5 mm tall with the finger tab. The c1 outline (its rounded rear end,
hub, step, crease, nose tab and bend line) is kept and STRETCHED forward about X STRETCH_X0 (ahead of the hub) by
STRETCH_K, which lands every one of those real proportions (tip X ~372, step 299-308.5, lower-edge slope 0.17); the
top stays at TOP_Z 8.0 under the charging handle (B3 bolt sweep) and the plate closes the slot band on safe.
"""
from __future__ import annotations

import math

import numpy as np

from rifle_common import SPEC  # noqa: F401  (interface: modules import the spec from rifle_common)
from gunlib import geo2d as G
from gunlib import lod as LOD
from gunlib import mesh as MS
from rifle_parts import WO
from rifle_parts2 import ycyl

from . import selector_trace as ST

# ======================================================================================== selector
SEL_PIVOT = (282.8, -7.8)

Y_WALL = -WO                    # receiver wall outer face (right side)
Y_IN = Y_WALL - 1.25            # plate inner face (0.2 mm over the rivet heads at -21.8)
T_PLATE = 2.0                   # stamped blade
Y_F = Y_IN - T_PLATE            # blade face
EMBED = 0.05                    # layers overlap so no boolean faces are coplanar
TOP_Z = 8.0                     # raised upper edge (closes the slot band; under the stem 8.6 / knob 8.2)
STEP_X = (299.0, 308.5)         # the upper edge's step (last shape round: the stretched c1 step; real photo X ~300-310)
STRETCH_X0, STRETCH_K = 290.0, 1.25   # last shape round: c1 outline stretched forward of X0 (front tip 355.6 -> 372)
CREASE_SET = 0.35               # the strip above c1's crease pressed in by this much (a lit step line)
EDGE = 0.30                     # crisp edge break on the blade
H_WASHER, H_HEAD = 0.5, 0.9     # low washer collar and button head on the pivot
TAB_BEND_DEG = 12.0
MIN_EDGE_MM = 0.35              # outline points closer than this are merged (the bevel's overlap clamp is global)


def _stretch(Q):
    """Last shape round: the real lever's length (see the module notes): X' = X0 + (X - X0) K ahead of X0."""
    Q = np.array(Q, float)
    m = Q[..., 0] > STRETCH_X0
    Q[..., 0] = np.where(m, STRETCH_X0 + (Q[..., 0] - STRETCH_X0) * STRETCH_K, Q[..., 0])
    return Q


def _px(P):
    return _stretch(ST.c1_to_rest(P, SEL_PIVOT))


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


def _collapse_short(ob, lim_mm, rounds=4, sharp_deg=None):
    """Collapse edges shorter than lim_mm (boolean slivers) to their midpoints; with sharp_deg only those whose
    dihedral is >= sharp_deg (the ones that set the bevel's global overlap clamp). Returns the count."""
    import bmesh
    n = 0
    for _ in range(rounds):
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        es = [e for e in bm.edges if e.calc_length() * 1000.0 < lim_mm and
              (sharp_deg is None or (len(e.link_faces) == 2 and math.degrees(e.calc_face_angle()) >= sharp_deg))]
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


def outline():
    """Blade outline (rest pose, frame M, XZ, CCW): c1's traced outer outline mapped onto the side view, its upper edge
    from the step to the tab's bend line replaced by a cosine step ramp up to TOP_Z and a straight top (the side
    trace's flat top raised 1.1 mm)."""
    O = _px(ST.c1_outline_px(n_arc=36))
    O = G.ccw(G.dedupe(O, 0.05))
    _, (ba, bb, nb) = _lines()
    xb = float(ba[0]) - 0.15                                       # the blade's top runs to just behind the bend line
    drop = (O[:, 0] > STEP_X[0] - 0.01) & (O[:, 0] < xb + 0.6) & (O[:, 1] > 0.0)
    idx = np.nonzero(drop)[0]
    i0, i1 = int(idx.min()), int(idx.max())
    assert np.all(drop[i0:i1 + 1]), "the upper-edge run is not contiguous in the ring"
    up = O[(~drop) & (O[:, 1] > 0.0) & (O[:, 0] < STEP_X[0])]
    z0 = float(up[np.argmax(up[:, 0]), 1])                         # the hub line's height at the step's foot
    xs = np.linspace(STEP_X[0], STEP_X[1], 7)
    ramp = [(x, z0 + (TOP_Z - z0) * 0.5 * (1 - math.cos(math.pi * (x - STEP_X[0]) / (STEP_X[1] - STEP_X[0]))))
            for x in xs]
    # CCW ring: the upper edge runs front -> rear
    top = [(xb, TOP_Z)] + [(x, TOP_Z) for x in np.arange(xb - 12.0, STEP_X[1] + 1.0, -12.0)] + ramp[::-1]
    new = np.vstack([O[:i0], np.array(top, float), O[i1 + 1:]])
    return G.ccw(G.dedupe(new, MIN_EDGE_MM))


def _crease_cutter():
    """The strip above c1's crease, from 2 mm along it to 0.8 mm behind the bend line, set in CREASE_SET."""
    (ca, cb, nc), (ba, bb, nb) = _lines()
    d = (cb - ca) / np.linalg.norm(cb - ca)
    t_end = float((ba - ca) @ nb / (d @ nb)) - 0.8
    A, B = ca + 2.0 * d, ca + t_end * d
    P = np.array([A, B, B + 20.0 * nc, A + 20.0 * nc])
    return MS.prism(G.ccw(P), Y_F - 1.0, Y_F + CREASE_SET)


def _hardware():
    px_, pz_ = SEL_PIVOT
    r_ring, r_dome = ST.c1_len(ST.C1_RING_R_PX), ST.c1_len(ST.C1_DOME_R_PX)
    washer = _ycap(px_, pz_, [(0.0, 0.0), (0.0, r_ring), (H_WASHER - 0.12, r_ring), (H_WASHER, r_ring - 0.12),
                              (H_WASHER, 0.0)], Y_F + EMBED, 24)
    y_top = Y_F + EMBED - H_WASHER
    head = _ycap(px_, pz_, [(0.0, 0.0), (0.0, r_dome), (0.25, r_dome), (0.45, r_dome - 0.35), (0.7, r_dome - 1.3),
                            (H_HEAD, r_dome - 2.6), (H_HEAD, 0.0)], y_top + EMBED, 24)
    bx, bz = _px(ST.C1_NOSE_BOSS_PX)[0]
    rp = ST.c1_len(ST.C1_NOSE_PIN_R_PX)
    pin = _ycap(bx, bz, [(0.0, 0.0), (0.0, rp + 0.35), (0.25, rp + 0.35), (0.35, rp + 0.2), (0.35, 0.0)],
                Y_F + EMBED, 12)
    hub = [ycyl(px_, pz_, 5.0, Y_WALL - 0.2, Y_IN - EMBED, 16),          # hub and shaft into the receiver's hole
           ycyl(px_, pz_, 3.0, Y_WALL - 0.25, -18.0, 16)]
    return hub, [washer, head, pin]


JOINT = {"type": "hinge", "parent": "receiver", "pivot_M": [SEL_PIVOT[0], 0, SEL_PIVOT[1]], "axis_M": [0, 1, 0],
         "positions_deg": {"safe": 0.0, "auto": 16.0, "semi": 32.0}, "clearance_mm": [0.1, 0.3]}


def selector(coll, offset):
    """Custom builder (gunlib.parts.BuildCtx provider(coll, offset)): the blade prism bevelled alone while clean, the
    crease step, hub and shaft, washer / head / pin, then the tab's sheet bend."""
    import json
    import time
    from gunlib import bl
    t0 = time.time()
    O = outline()
    ob = MS.prism(O, Y_F, Y_IN).to_object("selector", coll, offset, smooth_deg=30.0)
    bl.bevel(ob, EDGE, 1, 30.0, harden=False)
    if LOD.LEVEL < 2:
        bl.boolean(ob, _crease_cutter(), "DIFFERENCE", offset=offset)
        bl.clean(ob)
    hub, caps = _hardware()
    if LOD.LEVEL >= 2:          # LOD2: the hub and shaft are hidden in the receiver wall, the nose pin is < 1 px at 6.7 m
        hub, caps = [], caps[:2]
    if hub:
        bl.boolean_many(ob, hub, "UNION", offset=offset)
        bl.clean(ob)
    for u in caps:
        bl.boolean(ob, u, "UNION", offset=offset)
        bl.clean(ob)
    bt, bb_ = _px(ST.C1_BEND_PX[0])[0], _px(ST.C1_BEND_PX[1])[0]
    moved = _bend(ob, offset, bb_, bt, TAB_BEND_DEG)
    n_coll = _collapse_short(ob, 0.01)
    bl.clean(ob)
    bl.finish(ob)
    bl.fix_slivers(ob)
    bl.weighted_normals(ob)
    ob["gun_part"] = json.dumps({"bone": "selector", "class": "S-cut", "slot": "M_AR01_Metal", "joint": JOINT,
                                 "spec_id": "selector", "recipe": [[EDGE, 1, 30.0]]})
    rep = bl.manifold_report(ob)
    rep["collapsed_edges"] = n_coll
    print("[selector] tab verts bent %d, %.1fs, %s" % (moved, time.time() - t0, json.dumps(rep)))
    return ob


# ======================================================================================== module interface
OBJECTS = ('selector',)            # registry keys built here (rifle_parts.ORDER)
CLOSEUPS = ('c1', 'q34')          # sheet panels that are this part's shape authority (rifle_detail.py)


def build(spec, ctx):
    """Build this module's objects into ctx (gunlib.parts.BuildCtx). Returns {registry key: [objects]}; keys that
    ctx.only excludes come back empty. `spec` is the rifle GunSpec (the same object as rifle_common.SPEC)."""
    return {k: ctx.make(k, f) for k, f in (("selector", selector),)}
