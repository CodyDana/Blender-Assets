"""Detail part SELECTOR: the stamped selector lever on the receiver's right wall (bone "selector").

Owns the object: selector. Authority close-ups: c1 RECEIVER AND SELECTOR (RIGHT) for the 3D shape, the LEFT-labelled
side panel (true right) for scale / pose / position, the 3/4 view as a cross-check. Interfaces: the pivot SEL_PIVOT
(receiver's hole, hinge about Y), the B3 selector sweep (safe 0 / auto 16 / semi 32 deg, front end down) against the
rivets; the plate's inner face stays 1.25 mm off the receiver wall (0.2 mm over the rivet heads, hinge row 0.1-0.3).

Detail pass (2026-10-05): rebuilt from the c1 close-up trace (parts/selector_trace.py), mapped into the rest pose by
the similarity fitted to the side view (c1 draws the lever 13.25 deg front-down and 1.10x larger). Real geometry,
every visible form modelled.

History of what the blind judges read (so it is not tried again):
  r1  pressed raised edge band round a lower panel  -> "thin raised outline rim round a recessed hollow slot"
  r2  edge groove + valley wedge                    -> "raised rim round a recessed channel, hollow, an outline"
  r3  deep valley pocket with a lip on every side   -> still a dark slot cut into the lever (orchestrator check)
The common fault: the wedge between c1's top edge and its bright diagonal line was a POCKET (a lip on all sides),
and the all-round double line was a rim standing UP. c1 at 8x (trace_overlay.png) and the judges' reading of the
reference ("one solid stamped plate with a raised diagonal stiffening rib", "the plate sits inside a shallow stamped
outline") say the opposite on both, so detail round 2 (second workflow) builds:
  * ONE solid plate whose outline step goes DOWN: the main plate (full 2.0 mm) is the outline inset 1.1 mm, standing
    on a 0.9 mm skirt that fills the traced outer outline (c1's outer line / dark band / inner line all round,
    except on the tab, which is full thickness to the outer line: c1's notch where the tab starts);
  * the plate face shaped as real geometry (the face is cut along lines parallel to c1's crease and displaced, every
    step under the bevel angle so it shades smooth): a low rounded RIB along the crease (0.20 mm proud, its upper
    flank sweeping down into the wedge = the up-facing bright band, broad at the hump, narrowing to the front), and
    the wedge above it a solid face rising from the flank foot to the face at the plate's top edge (it reads darker; no
    lip), fading in behind the hump and ramping back up just before the tab;
  * the tab bent outward 12 deg about the traced bend line as a real sheet bend, a small flat-topped pin on it;
  * on the pivot: a raised washer collar and a large low-crowned button head (no slot, no centre boss: c1 shows a
    plain polished head filling the washer).
The plate and skirt prisms are bevelled while clean, before the relief and unions (Blender's bevel overlap clamp is
global: on the finished part it had shrunk every bevel to ~0.01-0.04 mm).
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
T_PLATE = 2.0                   # solid stamped lever plate
Y_F = Y_IN - T_PLATE            # lever face
EMBED = 0.05                    # layers overlap so no boolean faces are coplanar
# outline step (c1's double line): the main plate is the outline inset STEP_W, on a skirt T_SKIRT thick that fills the
# outer outline; the tab (forward of the bend line) is full thickness to the outer outline
STEP_W = 1.10                   # c1 2.3 px (selector_trace.C1_EDGE_BAND_PX) at the rest-frame scale
T_SKIRT = 0.90
SKIRT_GAP = 0.35
# face relief (s = mm above c1's crease line, toward the top edge; t = mm along the crease from its rear end;
# u = mm behind the tab bend line): (s, h) knots, h outward from the face, the crest part fixed, the upper flank
# dropping to -D(t) at s = S_FLOOR, then the wedge floor rising linearly to 0 at the plate's top edge (no lip)
RIB_LOWER = [(-0.80, 0.0), (-0.50, 0.08), (-0.25, 0.16), (-0.05, 0.20), (0.03, 0.20)]
# the upper flank is the broad up-facing slope (~33 deg at the hump, ~20 deg at the front) that catches the upper-left
# key: c1's bright band (12x zoom: ~3.3 px = 1.6 mm wide at the hump, fading toward the tab). The crest turns
# +11 -> -32 deg within ~0.5 mm (each knot < 24 deg, so the bevel leaves it), a worn high point like c1's
RIB_UPPER_F = [(0.12, 0.03), (0.28, 0.10), (0.50, 0.24), (0.80, 0.44), (1.10, 0.64), (1.40, 0.82), (1.65, 0.95),
               (1.85, 1.0)]
S_FLOOR = 1.85
D_HUMP = 0.80                   # floor depth at the crease from the hump back
D_FRONT = 0.45                  # ... at the front end
CREST_FRONT = 0.55              # rib crest height factor at the front end (c1: the bright band tapers out)
T_FADE = (0.0, 1.2, 2.4, 3.6)   # rear fade-in knots along t (weights 0, .3, .75, 1)
W_FADE = (0.0, 0.30, 0.75, 1.0)
U_RAMP = (0.30, 0.65, 1.05, 1.50)   # front ramp knots behind the bend line (weights 0, .35, .75, 1)
W_RAMP = (0.0, 0.35, 0.75, 1.0)
TAB_BEND_DEG = 12.0
RECIPE = [(0.20, 1, 24.0)]      # the plate and the skirt prisms, each bevelled ALONE while still clean, before the face
                                # relief and the unions: Blender's bevel overlap clamp is global, and on the finished
                                # part (relief cuts, boolean seams, the pin's 0.2 mm profile steps) it had shrunk every
                                # bevel to ~0.01-0.04 mm (measured on the chamfer strips, r3 included); the washer, head
                                # and pin carry their chamfers in their revolve profiles; the relief (every knot
                                # < 24 deg, zero on the rim) and the 12 deg bend stay unbevelled
MIN_EDGE_MM = 0.30              # outline points closer than this are merged (the bevel's overlap clamp is global)
T_STEP = 4.0                    # relief cuts across the crease every T_STEP mm (the wedge's top edge is not straight)
ROOM_MM = (1.0, 2.8)            # relief weight 0 -> 1 as the wedge (crease to top edge) widens over this range (mm)
FLANK_GAP = 0.6                 # where the wedge is narrow, the flank ends this far below the top edge


def _px(P):
    return ST.c1_to_rest(P, SEL_PIVOT)


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


def _on_line(P, a, n, tol=1e-6):
    return np.abs((P - a) @ n) < tol


def _splice(A, B, a, n):
    """Join polygon A (clipped to (p - a).n <= 0) and B (clipped to >= 0), both CCW and each with one edge on the line
    (a, n): A's ring minus its line edge, then B's ring minus its line edge (the joint steps along the line)."""
    def ring_from_line(P):
        on = _on_line(P, a, n, 1e-5)
        m = len(P)
        for i in range(m):
            if on[i] and on[(i + 1) % m]:
                return np.roll(P, -(i + 1), axis=0)     # starts at the edge's end point, ends at its start point
        raise RuntimeError("no edge on the line")
    RA = ring_from_line(A)
    RB = ring_from_line(B)
    return G.dedupe(np.vstack([RA, RB]), 1e-4)


def _outlines():
    """(O outer outline, M main plate outline = inset STEP_W behind the bend line + the full tab) in rest XZ."""
    O = _px(ST.c1_outline_px(n_arc=36))
    O = G.ccw(G.dp_simplify(G.dedupe(O, 0.05), LOD.tol(0.03)))          # LOD: coarser outline
    _, (ba, bb, nb) = _lines()
    Oin = G.ccw(G.dedupe(G.offset(O, -STEP_W), 0.05))
    A = G.ccw(_clip_half(Oin, ba, -nb))
    B = G.ccw(_clip_half(O, ba, nb))
    M = G.ccw(G.dedupe(_splice(A, B, ba, nb), MIN_EDGE_MM))
    return O, M


def _interp(x, X, Y):
    return float(np.interp(x, X, Y))


def _depth_at(t, t_hump, t_end):
    if t <= t_hump:
        return D_HUMP
    return D_HUMP + (D_FRONT - D_HUMP) * min(1.0, (t - t_hump) / max(t_end - t_hump, 1e-6))


def _s_top_fn(F, crease):
    """s_top(t): how far above the crease (mm) the face boundary F (the bevelled plate's flat top) lies at station t
    along the crease (the largest crossing of the line ca + t d + s nc with F); -inf where there is none."""
    ca, cb, nc = crease
    d = (cb - ca) / np.linalg.norm(cb - ca)
    S = (F - ca) @ nc
    T = (F - ca) @ d

    def f(t):
        best = -np.inf
        for k in range(len(F)):
            t0, t1 = T[k - 1], T[k]
            if (t0 - t) * (t1 - t) <= 0 and t0 != t1:
                best = max(best, S[k - 1] + (S[k] - S[k - 1]) * (t - t0) / (t1 - t0))
        return float(best)
    return f


def _relief_h(p, crease, bend, t_hump, t_end, s_top):
    """Outward displacement (mm) of the plate face at rest-frame XZ point p. Zero on the face boundary: the wedge
    floor rises from -D at S_FLOOR to 0 at the plate's top edge (s_top), so the edge keeps its full thickness and its
    bevel and no lip forms; the whole relief fades where the wedge is too narrow for it (behind the hump)."""
    ca, cb, nc = crease
    ba, _, nb = bend
    d = (cb - ca) / np.linalg.norm(cb - ca)
    s = float((p - ca) @ nc)
    t = float((p - ca) @ d)
    u = float((ba - p) @ nb)
    if s <= RIB_LOWER[0][0] or t <= T_FADE[0] or u <= U_RAMP[0]:
        return 0.0
    st = s_top(t)
    if s >= st - 1e-6:
        return 0.0
    room = _interp(st, ROOM_MM, (0.0, 1.0))                       # the wedge's width above the crease
    w = _interp(t, T_FADE, W_FADE) * _interp(u, U_RAMP, W_RAMP) * room
    if w <= 0.0:
        return 0.0
    # behind the hump the wedge is narrower than the flank: the flank is squeezed to end FLANK_GAP below the edge
    # (c1's band runs out into the top edge line there)
    sf = min(S_FLOOR, max(st - FLANK_GAP, 0.5))
    k = sf / S_FLOOR
    D = _depth_at(t, t_hump, t_end)
    c = 1.0 + (CREST_FRONT - 1.0) * (D_HUMP - D) / (D_HUMP - D_FRONT)
    crest = RIB_LOWER[-1][1] * c
    if s <= RIB_LOWER[-1][0]:
        h = c * _interp(s, [k_[0] for k_ in RIB_LOWER], [k_[1] for k_ in RIB_LOWER])
    elif s <= sf:
        f = _interp(s / k, [RIB_LOWER[-1][0]] + [k_[0] for k_ in RIB_UPPER_F], [0.0] + [k_[1] for k_ in RIB_UPPER_F])
        h = crest - (crest + D) * f
    else:
        h = -D * (st - s) / max(st - sf, 1e-6)
    return w * h



def _uniq(it):
    """Ordered de-duplication (a Python set of BMesh elements iterates by memory address, which made the relief's
    bisects, and so the selector's triangles, differ from one build to the next)."""
    return list(dict.fromkeys(it))

def _relief(ob, offset):
    """Shape the bevelled main plate's flat face (verts at Y_F; the rim bevel is not touched): bisect it along the
    relief's knot lines (parallel to the crease, across it every T_STEP mm, parallel to the bend line), displace
    outward by _relief_h, dissolve what stayed flat, triangulate. Real geometry; every knot turn is < 24 deg so the
    rib shades round."""
    import bmesh
    from mathutils import Vector
    off = np.asarray(offset, float)
    crease, bend = _lines()
    ca, cb, nc = crease
    ba, bb, nb = bend
    d = (cb - ca) / np.linalg.norm(cb - ca)
    t_end = float((ba - ca) @ nb / (d @ nb))        # crease meets the bend line
    _, Mo = _outlines()
    F = G.ccw(G.offset(Mo, -RECIPE[0][0]))          # the flat face's boundary after the rim bevel
    s_top = _s_top_fn(F, crease)
    sm = (Mo - ca) @ nc
    tm = (Mo - ca) @ d
    sel = (tm > 0) & (tm < t_end)
    t_hump = float(tm[sel][np.argmax(sm[sel])]) if sel.any() else 0.0

    def ymm(v):
        return v.co.y * 1000.0 + off[1]

    def top_faces(bm):
        return [f for f in bm.faces if all(abs(ymm(v) - Y_F) < 1e-3 for v in f.verts)]

    planes = []
    s_knots = sorted({k[0] for k in RIB_LOWER} | {k[0] for k in RIB_UPPER_F} | {S_FLOOR})
    for s in s_knots:
        planes.append((ca + s * nc, nc))
    t_knots = sorted(set(list(T_FADE) + [t_hump] + list(np.arange(T_FADE[-1] + LOD.step(T_STEP), t_end, LOD.step(T_STEP)))))
    for t in t_knots:
        planes.append((ca + t * d, d))
    for u in U_RAMP:
        planes.append((ba - u * nb, nb))
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    for (p2, n2) in planes:
        top = top_faces(bm)
        geom = _uniq(v for f in top for v in f.verts) + _uniq(e for f in top for e in f.edges) + top   # ordered: reproducible bisects
        co = Vector(((np.array([p2[0], Y_F, p2[1]]) - off) * 0.001).tolist())
        bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-7, plane_co=co, plane_no=Vector((n2[0], 0.0, n2[1])))
    top = top_faces(bm)
    moved = set()
    hmin, hmax = 0.0, 0.0
    tv = _uniq(v for f in top for v in f.verts)
    bmesh.ops.triangulate(bm, faces=top, quad_method="BEAUTY", ngon_method="BEAUTY")
    for v in tv:
        p = np.array([v.co.x * 1000.0 + off[0], v.co.z * 1000.0 + off[2]])
        h = _relief_h(p, crease, bend, t_hump, t_end, s_top)
        if abs(h) > 1e-6:
            v.co.y = (Y_F - h - off[1]) * 0.001
            moved.add(v)
            hmin, hmax = min(hmin, h), max(hmax, h)
    # what stayed flat goes back to big faces (the cut lines cross the whole face)
    bm.normal_update()
    flat_l = [f for f in bm.faces if all(abs(ymm(v) - Y_F) < 1e-6 for v in f.verts) and abs(f.normal.y) > 0.999]
    flat = set(flat_l)
    fe = [e for e in _uniq(e for f in flat_l for e in f.edges) if len(e.link_faces) == 2 and all(g in flat for g in e.link_faces)]
    if fe:
        bmesh.ops.dissolve_edges(bm, edges=fe, use_verts=True, use_face_split=False)
    ng = [f for f in bm.faces if len(f.verts) > 4]
    if ng:
        bmesh.ops.triangulate(bm, faces=ng, quad_method="BEAUTY", ngon_method="BEAUTY")
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    print("[selector] relief: t_hump %.2f t_end %.2f, %d t-cuts, %d verts moved, h %.2f..%.2f"
          % (t_hump, t_end, len(t_knots), len(moved), hmin, hmax))
    return len(moved)


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


def _head_profile(r):
    """Domed bolt head (t outward, radius): a straight skirt (its side reads as the dark ring c1 draws between head and
    washer), a rounded shoulder and a full dome. Integration round 2b: the r2b judge read our low 1.31 crown in thin
    rings as "a stamped disc"; c1 at 5x draws a domed bolt head standing in a thick washer with a distinct shoulder."""
    return [(0.0, 0.0), (0.0, r), (0.60, r), (0.82, r - 0.10), (1.12, r - 0.45), (1.42, r - 1.05), (1.66, r - 1.85),
            (1.80, r - 2.75), (1.84, 0.0)]


H_WASHER = 1.2                  # washer collar height (r2b 0.7: read as a thin ring), crisp 0.12 shoulder chamfer


def _parts():
    """The lever's solids (frame M, rest pose, tab not yet bent): main plate (relief applied later), unions."""
    O, Mo = _outlines()
    _, (ba, bb, nb) = _lines()
    main = MS.prism(Mo, Y_F, Y_IN)                                  # full thickness (tab included)
    # skirt: the outer outline, ending SKIRT_GAP behind the bend line (an end face ON the bend plane went non-manifold
    # in the bend's bisect; the small slot it leaves under the tab's notch is c1's notch)
    Os = G.ccw(G.dedupe(_clip_half(O, ba - SKIRT_GAP * nb, -nb), MIN_EDGE_MM))
    skirt = MS.prism(Os, Y_IN - T_SKIRT, Y_IN)
    px_, pz_ = SEL_PIVOT
    hub = [ycyl(px_, pz_, 5.0, Y_WALL - 0.2, Y_IN - EMBED, 16),          # hub and shaft into the receiver's hole
           ycyl(px_, pz_, 3.0, Y_WALL - 0.25, -18.0, 16)]                # (joined to the skirt first)
    unions = []
    bx, bz = _px(ST.C1_NOSE_BOSS_PX)[0]
    rp, rb = ST.c1_len(ST.C1_NOSE_PIN_R_PX), ST.c1_len(ST.C1_NOSE_BOSS_R_PX)
    # c1's nose: a thin raised ring round the pin (washer face) and the pin's small flat head proud of it
    unions.append(_ycap(bx, bz, [(0.0, 0.0), (0.0, rb), (0.10, rb), (0.24, rb - 0.14), (0.24, rp + 0.25),
                                 (0.30, rp), (0.48, rp), (0.56, rp - 0.1), (0.56, 0.0)], Y_F + EMBED, 16))
    # pivot: raised washer collar, large low-crowned button head; hub and shaft into the receiver
    px_, pz_ = SEL_PIVOT
    r_ring, r_dome = ST.c1_len(ST.C1_RING_R_PX), ST.c1_len(ST.C1_DOME_R_PX)
    h_ring = H_WASHER
    unions.append(_ycap(px_, pz_, [(0.0, 0.0), (0.0, r_ring), (h_ring - 0.12, r_ring), (h_ring, r_ring - 0.12),
                                   (h_ring, 0.0)], Y_F + EMBED, 24))
    y_ring_top = Y_F + EMBED - h_ring
    unions.append(_ycap(px_, pz_, _head_profile(r_dome), y_ring_top + EMBED, 24))

    return {"main": main, "skirt": skirt, "hub": hub, "unions": unions, "outline": O, "main_outline": Mo}


JOINT = {"type": "hinge", "parent": "receiver", "pivot_M": [SEL_PIVOT[0], 0, SEL_PIVOT[1]], "axis_M": [0, 1, 0],
         "positions_deg": {"safe": 0.0, "auto": 16.0, "semi": 32.0}, "clearance_mm": [0.1, 0.3]}


def selector(coll, offset):
    """Custom builder (gunlib.parts.BuildCtx provider(coll, offset)): bevelled main plate, its face relief, the
    bevelled skirt (+ hub and shaft), washer, head and pin, then the sheet bend."""
    import json
    import time
    import bpy
    from gunlib import bl
    t0 = time.time()
    P = _parts()
    ob = P["main"].to_object("selector", coll, offset, smooth_deg=30.0)
    short = _short_edges(ob, 2.0 * RECIPE[0][0])
    n_pre = len(ob.data.polygons)
    for st in RECIPE:                                       # the clean prism alone: the full bevel (the clamp is global)
        bl.bevel(ob, st[0], st[1], st[2], harden=False)
    if LOD.LEVEL < 2:                                       # LOD2: the pressed relief is painted only
        _relief(ob, offset)                                 # then the flat face inside the rim bevel
    bl.clean(ob)
    sk = P["skirt"].to_object("_selector_skirt", coll, offset, smooth_deg=30.0)
    for st in RECIPE:
        bl.bevel(sk, st[0], st[1], st[2], harden=False)
    bl.boolean_many(sk, P["hub"], "UNION", offset=offset)
    bl.clean(sk)
    bl.boolean(ob, sk, "UNION", offset=offset)
    bpy.data.objects.remove(sk, do_unlink=True)
    bl.clean(ob)
    bl.triangulate_ngons(ob)                                # relief slivers out before the EXACT unions: one collection
    bl.fix_slivers(ob)                                      # union of all five left 2 non-manifold edges at the notch
    _collapse_short(ob, 0.02)
    bl.clean(ob)
    for u in P["unions"]:                                   # one at a time (washer, head, pin)
        bl.boolean(ob, u, "UNION", offset=offset)
        bl.clean(ob)
    bt, bb = _px(ST.C1_BEND_PX[0])[0], _px(ST.C1_BEND_PX[1])[0]
    moved = _bend(ob, offset, bb, bt, TAB_BEND_DEG)
    n_coll = _collapse_short(ob, 0.01)                      # boolean / bisect micro edges only
    bl.clean(ob)
    bl.finish(ob)
    bl.fix_slivers(ob)
    bl.weighted_normals(ob)
    ob["gun_part"] = json.dumps({"bone": "selector", "class": "S-cut", "slot": "M_AR01_Metal", "joint": JOINT,
                                 "spec_id": "selector", "recipe": [list(s) for s in RECIPE]})
    rep = bl.manifold_report(ob)
    rep["short_edges_main_prism"] = short
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
