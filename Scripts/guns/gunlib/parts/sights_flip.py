"""Rail-clamp flip sights (gunlib 0.2.0; SMG_BUILD_PLAN 5-6, R12; shared by SMG01 and CB01). Plain Python (numpy).

Real pattern (flip-up backup sights on a 1913 rail): a machined base whose underside wraps the rail head (a flat on the
rail's top flat, the sides past the V points, a jaw under each lower 45 deg flank: the flanks are the clamping
surfaces), a recoil lug in one rail slot (integer slot index: it fixes the sight's X), a transverse cross-bolt
(head one side, nut / knob the other) that pulls the jaws in; above the base a U-channel whose cheeks carry a
transverse pin; the leaf pivots on that pin and is held up or folded by a spring detent. Rear: a round aperture disc
(diopter: a small hole, countersunk on the eye side) between two protective ears. Front: a square post between two
protective ears (a hood without a top).

Frame: the RAIL frame of gunlib.parts.rail_1913 (+X along the slots from the rail's rear end, +Z out of the top, the
rail top at Z = rail height). ``rail_1913.placement`` maps it into the gun frame. Everything is built by construction
(prisms of side / end outlines, loops of revolution); the only booleans are the pin bores and the base's channel cut
between the cheeks (PartDef cutters), each kept >= 0.1 mm from other edges.

The leaf is modelled UP (as drawn); its fold is the bone's rotation about the pin (``joint``): the rear leaf folds
forward (+deg about Y), the front rearward (-deg); ``fold_sweep_group`` gives the B3 group with the detent allowance.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import numpy as np

from .. import lod as _lod
from ..geo2d import rounded_rect
from ..mesh import Mesh, box, cylinder, prism
from . import rail_1913 as RL

GAP = 0.05                 # clamp faces on the rail: a butt joint (0.01-0.05 mm, never a shared vertex)


def revolve_loop(profile, origin, axis, nseg=32) -> Mesh:
    """Revolve a CLOSED (t, r) loop (all r > 0) about the axis: a ring solid (an aperture disc, a knob with a bore)."""
    from ..mesh import _frame
    nseg = _lod.ring(nseg)
    o = np.asarray(origin, float)
    u, v, w = _frame(axis)
    th = np.linspace(0, 2 * math.pi, nseg, endpoint=False)
    D = np.outer(np.cos(th), u) + np.outer(np.sin(th), v)
    m = Mesh()
    rows = [m.add_verts(o + w * t + r * D) for t, r in profile]
    n = len(rows)
    for i in range(n):
        a, b = rows[i], rows[(i + 1) % n]
        for k in range(nseg):
            k2 = (k + 1) % nseg
            m.face((a[k], a[k2], b[k2], b[k]))
    return m


# ------------------------------------------------------------------------------------------------ base
def clamp_section(rail_h: float, width: float, top_z: float, jaw_clear: float = 0.6, c: float = 0.4) -> np.ndarray:
    """The base's YZ section in the rail frame: outside a box ``width`` wide up to ``top_z``; inside the rail head +
    GAP (the top flat, the upper chamfers, the V faces, then a jaw face parallel to each lower flank, GAP off it)
    down to the jaw tips ``jaw_clear`` outside the neck. Counter-clockwise (Y, Z)."""
    H = rail_h
    g = GAP
    s2 = math.sqrt(2.0)
    yt = RL.NECK_HALF + jaw_clear                                   # jaw tip, outside the neck
    z_face = lambda y: H - RL.D_VBOT - (RL.V_HALF - y) - g * s2      # noqa: E731  lower-flank face offset by g
    zj = z_face(yt)
    W = width / 2.0
    right_in = [(yt, zj), (RL.V_HALF + g, z_face(RL.V_HALF + g) + 0.0), (RL.V_HALF + g, H - RL.D_VTOP + g * (s2 - 1.0)),
                (RL.TOP_HALF + g * (s2 - 1.0), H + g)]
    # outside, right half from the jaw bottom up to the top (chamfered top corner)
    right_out = [(W, zj), (W, top_z - c), (W - c, top_z)]
    loop = []
    loop += [(yt, zj), (W, zj)] + right_out[1:]                      # right jaw bottom, right outer side, top corner
    loop += [(-W + c, top_z), (-W, top_z - c), (-W, zj), (-yt, zj)]  # top, left side, left jaw bottom
    loop += [(-y, z) for y, z in right_in[1:]]                        # left inner: up the jaw face, V face, chamfer
    loop += [(y, z) for y, z in reversed(right_in[1:])]               # right inner from the top flat down
    out = []
    for p in loop:
        if not out or math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > 1e-6:
            out.append(p)
    if math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) < 1e-6:
        out.pop()
    return np.array(out, float)


def clamp_base(rail_rec: Dict, slot_k: int, x_rear: float, x_front: float, width: float = 26.0,
               floor_above_rail: float = 2.0, lug_w: float = 4.9) -> Tuple[Mesh, List[Mesh], Dict]:
    """The clamp base on the rail from x_rear to x_front (rail frame): the clamp section extruded along X with a
    floor ``floor_above_rail`` above the rail top, plus the recoil lug (``lug_w`` along X, 0.17 mm per side in the
    5.24 slot: the sliding row's 0.15 lower bound) down to GAP above the slot floor, at slot ``slot_k``'s centre.
    Returns (base mesh, unions [lug], record)."""
    H = rail_rec["height"]
    top = H + floor_above_rail
    sec = clamp_section(H, width, top)
    base = prism(sec, x_rear, x_front, "YZ")
    xc = rail_rec["slot_centres"][slot_k] if slot_k in rail_rec["slot_centres"] else rail_rec["slot_centres"][str(slot_k)]
    if not (x_rear + 1.0 < xc - lug_w / 2.0 and xc + lug_w / 2.0 < x_front - 1.0):
        raise ValueError("the recoil lug (slot %d at X %.2f) is not inside the base %.2f..%.2f" % (slot_k, xc, x_rear, x_front))
    zf = H - RL.SLOT_D + GAP
    lug = box(xc - lug_w / 2.0, xc + lug_w / 2.0, -(RL.TOP_HALF - 0.5), RL.TOP_HALF - 0.5, zf, H + GAP + 0.5)
    rec = {"slot": slot_k, "lug_x": round(xc, 4), "lug_w": lug_w, "lug_clear_per_side": round((RL.SLOT_W - lug_w) / 2, 4),
           "base_x": [x_rear, x_front], "base_top_z": top, "width": width, "gap": GAP,
           "mount_snap": "Mount = lug centre on the rail-top plane = Rail_X + %d x %.2f" % (slot_k, RL.PITCH)}
    return base, [lug], rec


def cheeks(x0: float, x1: float, z0: float, z1: float, inner_half: float, thick: float, r: float = 1.0) -> List[Mesh]:
    """The U-channel's two cheeks (plates ``thick`` wide at |y| = inner_half .. inner_half + thick), side outline a
    rounded rectangle X x0..x1, Z z0..z1 (they overlap the base top by 0.5 mm for the union)."""
    from ..geo2d import arc
    top = np.vstack([arc(x1 - r, z1 - r, r, 0.0, 90.0, 4), arc(x0 + r, z1 - r, r, 90.0, 180.0, 4)])
    P = np.vstack([[(x0, z0 - 0.5), (x1, z0 - 0.5)], top])      # square bottom (inside the base), rounded top
    return [prism(P, inner_half, inner_half + thick, "XZ"), prism(P, -inner_half - thick, -inner_half, "XZ")]


def base_recipe(rail_rec: Dict, M4=None, width_mm: float = 0.3):
    """The base's edge breaks: a convex-aware weighted 1-segment chamfer on its OUTER block edges only (gunlib.bl
    outer_edges_pred). The channel that wraps the rail head (contact faces, GAP off the rail), the recoil lug and the
    union seams stay sharp: their faces are 0.5-0.6 mm bands a 0.3 mm bevel would clamp into strips (UD2)."""
    from ..bl import outer_edges_pred
    H = rail_rec["height"]
    Minv = np.linalg.inv(np.eye(4) if M4 is None else np.asarray(M4, float))

    def channel(mid):
        p = Minv[:3, :3] @ mid + Minv[:3, 3]
        return abs(p[1]) < RL.V_HALF + 0.6 and p[2] < H + GAP + 0.2
    return [(width_mm, 1, "WC", outer_edges_pred(channel))]


def leaf_recipe(keep_out=(), width_mm: float = 0.3):
    """The leaf's edge breaks: the convex block edges of the plate, bar and ears only; the aperture disc's and the
    post's own breaks are modelled geometry, and ``keep_out`` (centre_mm, radius_mm) spheres keep the bevel away from
    them (curved union seams never take a bevel)."""
    from ..bl import outer_edges_pred
    ko = [(np.asarray(c, float), float(r)) for c, r in keep_out]

    def near(mid):
        return any(np.linalg.norm(mid - c) < r for c, r in ko)
    return [(width_mm, 1, "WC", outer_edges_pred(near))]


#: the default leaf recipe (no keep-out zones)
LEAF_RECIPE = leaf_recipe()


# ------------------------------------------------------------------------------------------------ leaves
def aperture_disc(centre, dia: float = 10.0, hole: float = 2.0, thick: float = 2.5, countersink_deg: float = 45.0,
                  eye_side: float = -1.0, nseg: int = 48) -> Mesh:
    """Diopter disc on the sight line (axis X): outer ``dia``, through hole ``hole``, countersunk on the eye side
    (eye_side -1 = toward -X) to half the thickness at ``countersink_deg`` from the axis; 0.2 mm edge breaks."""
    cx = np.asarray(centre, float)
    R, rh, T = dia / 2.0, hole / 2.0, thick
    e = 0.2
    k = 0.5 * T * math.tan(math.radians(countersink_deg))          # radial growth of the countersink
    # loop in (t, r), t along +X from the disc's front face; the eye side is t = -T (eye_side -1)
    if eye_side < 0:
        loop = [(0.0, rh), (0.0, R - e), (-e, R), (-T + e, R), (-T, R - e), (-T, rh + k), (-0.5 * T, rh)]
    else:
        loop = [(0.0, rh + k), (0.0, R - e), (-e, R), (-T + e, R), (-T, R - e), (-T, rh), (-0.5 * T, rh)]
    return revolve_loop(loop, cx + np.array([T / 2.0, 0.0, 0.0]), (1.0, 0.0, 0.0), nseg)


def ears(x0: float, x1: float, z0: float, z_top: float, half_gap: float, thick: float, r_top: float = 1.0) -> List[Mesh]:
    """Two protective ears (plates at |y| = half_gap .. half_gap + thick), side outline X x0..x1, Z z0..z_top with
    rounded top corners (M-round)."""
    P = rounded_rect(x0, x1, z0, z_top, r_top, seg=3)
    return [prism(P, half_gap, half_gap + thick, "XZ"), prism(P, -half_gap - thick, -half_gap, "XZ")]


def post(x_c: float, z0: float, tip_z: float, width: float = 1.85, depth: float = 1.85, brk: float = 0.2) -> Mesh:
    """Square front post, flat tip at tip_z with a ``brk`` mm break on its top edges (the sight picture's edge)."""
    w, d = width / 2.0, depth / 2.0
    P = [(-w, z0), (w, z0), (w, tip_z - brk), (w - brk, tip_z), (-w + brk, tip_z), (-w, tip_z - brk)]
    return prism(P, x_c - d, x_c + d, "YZ")


def leaf_plate(outline_xz, half_w: float) -> Mesh:
    """The leaf body: its side outline (X, Z) extruded across Y +-half_w."""
    return prism(outline_xz, -half_w, half_w, "XZ")


def pin_bore(pivot_xz, r: float, half_len: float, nseg: int = 32) -> Mesh:
    x, z = pivot_xz
    return cylinder((x, -half_len, z), (x, half_len, z), r, nseg)


def joint(pivot_xz, fold_deg: float, rail_M4=None) -> Dict:
    """The leaf's joint record: hinge about Y through the pin, limits 0 (up) .. fold_deg; the sight bones' motion."""
    return {"type": "hinge", "axis": [0.0, 1.0, 0.0], "pivot_rail": [float(pivot_xz[0]), 0.0, float(pivot_xz[1])],
            "limits_deg": [0.0, float(fold_deg)], "row": "hinge", "clearance_mm": [0.10, 0.30],
            "detent": "spring detent at 0 and at the fold (declared allowance <= 0.3 mm in the last <= 2 deg)"}


def fold_sweep_group(parts, pivot_B, fold_deg: float, axis=(0.0, 1.0, 0.0), with_parts=()) -> Dict:
    """The B3 group for a leaf: 0 .. fold_deg, with the plan's detent allowance (<= 0.3 mm in the last <= 2 deg) on
    the listed fixed parts (the base / detent spring)."""
    from .hinge import sweep_group
    a = fold_deg
    win = [a - math.copysign(2.0, a), a]
    al = [{"with": list(with_parts), "window": win, "max_depth_mm": 0.3, "why": "spring detent at the fold"}] \
        if with_parts else []
    return sweep_group(parts, pivot_B, axis, (0.0, fold_deg), allowances=al)


def head_outline(ear_in: float, ear_out: float, z_bottom: float, z_web_top: float, z_ear_top: float,
                 r_top: float = 1.0, post: Optional[Tuple[float, float, float]] = None) -> np.ndarray:
    """The leaf head seen along the sight line (Y, Z): a web across the full width from z_bottom to z_web_top and two
    ears (|y| = ear_in .. ear_out) up to z_ear_top with rounded tops; ``post`` (width, tip_z, break) raises a square
    post from the web's middle in the same outline (front sight: post and ears are one machined head, no union)."""
    from ..geo2d import arc
    n = 4
    P = [(-ear_out, z_bottom), (ear_out, z_bottom)]
    P += arc(ear_out - r_top, z_ear_top - r_top, r_top, 0.0, 90.0, n).tolist()
    P += arc(ear_in + r_top, z_ear_top - r_top, r_top, 90.0, 180.0, n).tolist()
    P += [(ear_in, z_web_top)]
    if post is not None:
        w, tip, brk = post[0] / 2.0, post[1], post[2]
        P += [(w, z_web_top), (w, tip - brk), (w - brk, tip), (-w + brk, tip), (-w, tip - brk), (-w, z_web_top)]
    P += [(-ear_in, z_web_top)]
    P += arc(-ear_in - r_top, z_ear_top - r_top, r_top, 0.0, 90.0, n).tolist()
    P += arc(-ear_out + r_top, z_ear_top - r_top, r_top, 90.0, 180.0, n).tolist()
    return np.array(P, float)


def head(outline_yz, x0: float, x1: float) -> Mesh:
    """The head prism: the (Y, Z) outline extruded along X from x0 to x1."""
    return prism(outline_yz, x0, x1, "YZ")


def aperture_cutter(x_face_eye: float, x_face_front: float, centre_yz, hole: float = 2.0,
                    countersink_deg: float = 45.0, depth_frac: float = 0.5, nseg: int = 48) -> Mesh:
    """The aperture: a through hole along X (dia ``hole``) with a countersink on the eye side (``x_face_eye``),
    ``countersink_deg`` from the axis over ``depth_frac`` of the head thickness; it runs 1 mm past both faces."""
    y, z = centre_yz
    T = abs(x_face_front - x_face_eye)
    s = 1.0 if x_face_front > x_face_eye else -1.0
    rh = hole / 2.0
    k = depth_frac * T * math.tan(math.radians(countersink_deg))
    prof = [(-1.0, 0.0), (-1.0, rh + k + 1.0 * math.tan(math.radians(countersink_deg))), (0.0, rh + k),
            (depth_frac * T, rh), (T + 1.0, rh), (T + 1.0, 0.0)]
    from ..mesh import revolve
    return revolve(prof, (x_face_eye, y, z), (s, 0.0, 0.0), nseg)


# ------------------------------------------------------------------------------------------------ demo pair
def demo_pair(rail_rec: Dict, rear_slot: int, front_slot: int, sight_z_over_rail: float = 26.0,
              aperture: float = 2.0) -> Dict[str, Dict]:
    """A generic rear (aperture) + front (post) pair on a rail, the sight line ``sight_z_over_rail`` above the rail
    top: the gunlib unit test's sights (B4 aperture method, UD, manifold). A gun builds its own from the sheet with
    the same functions. Returns {name: {"pieces": [(Mesh, recipe)], "cutters", "joint", "bone"}} in the rail frame,
    for gunlib.parts.build_composite (each piece edge-broken before the union)."""
    H = rail_rec["height"]
    zl = H + sight_z_over_rail
    br = [(0.3, 1, 50.0)]                                          # 0.3 mm breaks on the ~90 deg block edges
    out = {}
    # rear: base around the rear lug slot; the leaf = an arm plate (XZ) + a head (YZ: web + ears) with the aperture
    # drilled through it; the pin at the arm's front-lower corner (it folds forward)
    xr = rail_rec["slot_centres"][rear_slot]
    b0, b1 = xr - 8.0, xr + 14.0
    base, lug, rec = clamp_base(rail_rec, rear_slot, b0, b1, width=24.0, floor_above_rail=2.0)
    ch = cheeks(b0 + 4.0, b1 - 0.6, H + 2.0, H + 12.0, 4.25, 2.5)     # 0.6 inside the base's ends: no coplanar union
    out["rear_sight_base"] = {"pieces": [(base, base_recipe(rail_rec))] + [(m, []) for m in lug] + [(m, br) for m in ch],
                              "cutters": [], "bone": "body", "record": rec}
    px, pz = b1 - 3.0, H + 7.0
    ap_x = px - 6.0
    T = 2.5
    arm = leaf_plate(rounded_rect(px - 10.0, px + 3.5, pz - 3.0, zl - 4.0, 1.5, seg=3), 4.0)
    hd = head(head_outline(5.0, 7.5, zl - 5.0, zl + 3.5, zl + 8.0), ap_x - T / 2.0, ap_x + T / 2.0)
    out["rear_sight_leaf"] = {"pieces": [(arm, br), (hd, br)],
                              "cutters": [aperture_cutter(ap_x - T / 2.0, ap_x + T / 2.0, (0.0, zl), aperture),
                                          pin_bore((px, pz), 1.65, 6.0)],
                              "bone": "sight_rear", "joint": joint((px, pz), 90.0)}
    # front: base + leaf: an arm plate + a head whose outline holds the post between the ears (one prism)
    xf = rail_rec["slot_centres"][front_slot]
    f0, f1 = xf - 10.0, xf + 8.0
    fbase, flug, frec = clamp_base(rail_rec, front_slot, f0, f1, width=24.0, floor_above_rail=2.0)
    fch = cheeks(f0 + 0.6, f1 - 4.0, H + 2.0, H + 12.0, 4.25, 2.5)
    out["front_sight_base"] = {"pieces": [(fbase, base_recipe(rail_rec))] + [(m, []) for m in flug] +
                               [(m, br) for m in fch], "cutters": [], "bone": "body", "record": frec}
    qx, qz = f0 + 3.0, H + 7.0
    post_x = qx + 6.0
    D = 1.85
    farm = leaf_plate(rounded_rect(qx - 3.5, qx + 8.0, qz - 3.0, zl - 9.0, 1.5, seg=3), 4.0)
    fhd = head(head_outline(4.5, 6.5, zl - 10.0, zl - 7.5, zl + 6.0, post=(D, zl, 0.2)), post_x - D / 2.0, post_x + D / 2.0)
    out["front_sight_leaf"] = {"pieces": [(farm, br), (fhd, [])], "cutters": [pin_bore((qx, qz), 1.65, 6.0)],
                               "bone": "sight_front", "joint": joint((qx, qz), -90.0)}
    out["_sight_line"] = {"z": zl, "aperture_x": ap_x, "post_x": post_x}
    return out
