"""MIL-STD-1913 accessory rail (gunlib 0.2.0; GUN_BUILDING_STUDY 5.4, SMG_BUILD_PLAN 5). Plain Python (numpy).

Profile (MIL-STD-1913 Figure 1, numbers in gun_standard.json ``rail_1913``): a hexagonal head 21.2 mm across its V
points with 45 deg flanks above and below the V, the gauge width 19.0 (0.748 in) at two lines 2.743 (0.108 in basic)
apart, the lower one 4.10 below the top (0.164 -0.020 in); a neck 15.67 (0.617 in) wide; the base below it with a
radius at the neck-base corner (<= 1.52, R 0.060 in max). Slots 5.24 wide (0.206 in), square-bottomed, 3.00 deep
(0.118 in) at a 10.01 pitch (0.394 in). With the lower gauge line at 4.10 the V face ends exactly at the slot floor:
the slot floor meets the V face's lower edge with no sliver (UD2).

Construction (no booleans, no run-out strips): the body below the slot floor is one prism of the body section with a
station at every slot wall; each tooth is a prism of the head section between two slot walls whose bottom edge shares
the body's vertices; slot floors and relief flats are the body's top faces between teeth. A closed manifold by
construction. Edge breaks: a weighted 1-segment chamfer (default 0.3 mm, never < 0.1) on the slot walls' and the end
faces' outer edges only (the 45 deg profile edges stay crisp as machined; the floor junctions and the mounting face
stay sharp).

Frame: the rail's own: +X along the slots from the rear end (X 0), +Y across, +Z out of the rail top; the mounting face
at Z 0, the top at Z = height. ``place(M4)`` moves the result into the gun frame.

LODs (gunlib.lod.LEVEL): 0 and 1 the full profile (LOD1 drops the chamfer through gunlib.lod's 0.8 mm minimum);
2 a trapezoid section (no undercut, no neck radius), teeth as plain blocks; 3 the rail's box.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from .. import lod as _lod
from ..mesh import Mesh
from .. import standard as _std

STD = _std.rail()
PITCH = STD["slot_pitch"]
SLOT_W = STD["slot_width"]
SLOT_D = STD["slot_depth"]
V_HALF = STD["width_across_V"] / 2.0                 # 10.6
GAUGE_HALF = STD["gauge_width"] / 2.0                # 9.5
NECK_HALF = STD["neck_width"] / 2.0                  # 7.835
D_GAUGE_LO = STD["lower_gauge_depth"]                # 4.10
D_GAUGE_UP = D_GAUGE_LO - STD["gauge_lines_apart"]   # 1.357
D_VTOP = D_GAUGE_UP + (V_HALF - GAUGE_HALF)          # 2.457
D_VBOT = D_GAUGE_LO - (V_HALF - GAUGE_HALF)          # 3.000
D_NECK = D_VBOT + (V_HALF - NECK_HALF)               # 5.765
TOP_HALF = GAUGE_HALF - D_GAUGE_UP                   # 8.143
MIN_TOOTH_MM = 0.5                                   # a tooth / floor run under this merges into its neighbour (UD)


def profile_numbers() -> Dict[str, float]:
    return {"top_flat_width": round(2 * TOP_HALF, 4), "V_width": round(2 * V_HALF, 4), "V_face_depths":
            [round(D_VTOP, 4), round(D_VBOT, 4)], "neck_width": round(2 * NECK_HALF, 4), "neck_top_depth": round(D_NECK, 4),
            "gauge_width": round(2 * GAUGE_HALF, 4), "gauge_depths": [round(D_GAUGE_UP, 4), round(D_GAUGE_LO, 4)],
            "flank_deg": 45.0, "slot_width": SLOT_W, "slot_depth": SLOT_D, "pitch": PITCH}


def _body_half(H, base_half, shoulder_depth, radius, level):
    """Right half of the body section, from the floor corner (V_HALF, H - D_VBOT) down to the base (y >= 0)."""
    zf = H - D_VBOT
    if level >= 2:
        return [(V_HALF, zf), (base_half, 0.0)] if abs(base_half - V_HALF) > 1e-9 else [(V_HALF, zf), (V_HALF, 0.0)]
    pts = [(V_HALF, zf), (NECK_HALF, H - D_NECK)]
    zs = H - shoulder_depth
    if base_half > NECK_HALF + 1e-6 and zs > 0.0:
        r = min(radius, 0.45 * (H - D_NECK - zs), 0.45 * (base_half - NECK_HALF))
        if r >= 0.2:
            # concave fillet: centre (NECK_HALF + r, zs + r); from the neck (angle 180) down to the shoulder (270)
            n = _lod.arc_points(5)
            for t in np.radians(np.linspace(180.0, 270.0, n)):
                pts.append((NECK_HALF + r + r * math.cos(t), zs + r + r * math.sin(t)))
        else:
            pts += [(NECK_HALF, zs)]
        pts += [(base_half, zs), (base_half, 0.0)]
    else:
        pts += [(NECK_HALF, 0.0)]
    # drop repeats
    out = [pts[0]]
    for p in pts[1:]:
        if math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > 1e-6:
            out.append(p)
    return out


def _tooth_chain(H, level):
    """Head section above the slot floor, right floor corner -> over the top -> left floor corner."""
    zf = H - D_VBOT
    if level >= 2:
        return [(V_HALF, zf), (TOP_HALF, H), (-TOP_HALF, H), (-V_HALF, zf)]
    return [(V_HALF, zf), (V_HALF, H - D_VTOP), (TOP_HALF, H), (-TOP_HALF, H), (-V_HALF, H - D_VTOP), (-V_HALF, zf)]


def layout(n_slots: int, pad_rear: float, pad_front: float, cut: Optional[Sequence[int]] = None,
           flats: Sequence[Tuple[float, float]] = ()) -> Dict:
    """Slot centres and the tooth / floor runs along X. Slot k's centre is at pad_rear + SLOT_W / 2 + k x PITCH."""
    cut = list(range(n_slots)) if cut is None else sorted(set(int(k) for k in cut))
    L = pad_rear + (n_slots - 1) * PITCH + SLOT_W + pad_front
    centres = {k: pad_rear + SLOT_W / 2.0 + k * PITCH for k in range(n_slots)}
    floors = [(centres[k] - SLOT_W / 2.0, centres[k] + SLOT_W / 2.0) for k in cut]
    floors += [(max(0.0, a), min(L, b)) for a, b in flats]
    floors.sort()
    merged: List[List[float]] = []
    for a, b in floors:
        if merged and a <= merged[-1][1] + MIN_TOOTH_MM:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    runs, x = [], 0.0
    for a, b in merged:
        if a - x >= MIN_TOOTH_MM:
            runs.append(("tooth", x, a))
        else:
            a = x                                       # a tooth sliver (< MIN_TOOTH_MM) goes to the floor
        runs.append(("floor", a, b))
        x = b
    if L - x >= MIN_TOOTH_MM:
        runs.append(("tooth", x, L))
    elif runs and L - x > 1e-9:
        runs[-1] = (runs[-1][0], runs[-1][1], L)
    return {"length": L, "centres": centres, "cut": cut, "runs": runs}


def rail_1913(n_slots: int, pad_front: float = 2.5, pad_rear: float = 2.5, height: Optional[float] = None,
              lod: Optional[int] = None, cut: Optional[Sequence[int]] = None,
              flats: Sequence[Tuple[float, float]] = (), base_width: Optional[float] = None,
              shoulder_depth: Optional[float] = None, neck_radius: float = 0.8) -> Tuple[Mesh, Dict]:
    """A closed rail solid in its own frame + its record (slot centres, length, profile, runs).

    n_slots    slot positions 0..n_slots-1 (slot 0 rearmost); ``cut`` the ones machined (default all)
    pad_rear   solid length behind slot 0's rear wall; pad_front in front of the last position's front wall
    height     mounting face to top (default the standard's 9.5; the SMG sheet's 10.2)
    flats      (x0, x1) runs machined down to the slot floor (relief flats the sheet draws)
    base_width the base below the neck (default = the V width, a plain riser); shoulder_depth: top to the base's top
    """
    level = _lod.LEVEL if lod is None else int(lod)
    H = float(height if height is not None else STD["height_default"])
    bw = float(base_width if base_width is not None else 2 * V_HALF)
    sd = float(shoulder_depth if shoulder_depth is not None else max(D_NECK + 1.5, H - 2.5))
    lay = layout(n_slots, pad_rear, pad_front, cut, flats)
    L = lay["length"]
    rec = {"length": round(L, 4), "height": H, "slot_centres": {k: round(v, 4) for k, v in lay["centres"].items()},
           "cut": lay["cut"], "runs": [(k, round(a, 4), round(b, 4)) for k, a, b in lay["runs"]],
           "profile": profile_numbers(), "lod": level, "frame": "rail: +X along the slots from the rear end, +Z out "
           "of the top, mounting face Z 0", "top_z": H, "floor_z": round(H - D_VBOT, 4)}
    if level >= 3:
        from ..mesh import box
        return box(0.0, L, -max(V_HALF, bw / 2), max(V_HALF, bw / 2), 0.0, H), rec
    right = _body_half(H, bw / 2.0, sd, neck_radius, level)
    body = right + [(-y, z) for y, z in reversed(right)]          # right top -> base -> left top
    nb = len(body)
    chain = _tooth_chain(H, level)                                 # right floor corner -> left floor corner
    xs = sorted({0.0, L} | {a for _, a, _ in lay["runs"]} | {b for _, _, b in lay["runs"]})
    m = Mesh()
    rings = {}
    for x in xs:
        rings[x] = m.add_verts([(x, y, z) for y, z in body])
    i_r, i_l = 0, nb - 1                                           # the floor corners in each body ring
    teeth = {}
    for kind, a, b in lay["runs"]:
        if kind != "tooth":
            continue
        ia = m.add_verts([(a, y, z) for y, z in chain[1:-1]])
        ib = m.add_verts([(b, y, z) for y, z in chain[1:-1]])
        teeth[(a, b)] = (ia, ib)
    run_at = {}
    for kind, a, b in lay["runs"]:
        run_at[(a, b)] = kind
    # body side faces (every section edge but the top one) between consecutive stations
    for x0, x1 in zip(xs[:-1], xs[1:]):
        r0, r1 = rings[x0], rings[x1]
        for k in range(nb - 1):
            m.face((r0[k], r1[k], r1[k + 1], r0[k + 1]))
        kind = run_at.get((x0, x1), "floor")
        if kind == "floor":
            m.face((r0[i_l], r1[i_l], r1[i_r], r0[i_r]))           # slot floor / relief flat
        else:
            ia, ib = teeth[(x0, x1)]
            ca = [r0[i_r]] + list(ia) + [r0[i_l]]                  # tooth chain at x0 (shares the floor corners)
            cb = [r1[i_r]] + list(ib) + [r1[i_l]]
            for k in range(len(ca) - 1):
                m.face((ca[k], ca[k + 1], cb[k + 1], cb[k]))
            if x0 > 1e-9:
                m.face(ca)                                         # rear slot wall of the tooth
            if x1 < L - 1e-9:
                m.face(cb[::-1])                                   # front slot wall
    # end caps: the full section where a tooth reaches the end, else the body section
    for x, first in ((0.0, True), (L, False)):
        r = rings[x]
        tooth = next(((a, b) for (a, b), k in run_at.items() if k == "tooth" and (abs(a - x) < 1e-9 or abs(b - x) < 1e-9)),
                     None)
        loop = list(r)
        if tooth is not None:
            ia, ib = teeth[tooth]
            mid = list(ia if abs(tooth[0] - x) < 1e-9 else ib)
            loop = loop + mid[::-1]                                # base ring right->left, then the head left->right
        m.face(loop if not first else loop[::-1])
    return m, rec


def transform(m: Mesh, M4) -> Mesh:
    return m.transformed(M4)


def placement(origin_M, x_axis=(1.0, 0.0, 0.0), z_axis=(0.0, 0.0, 1.0)) -> np.ndarray:
    """4x4 from the rail frame into the gun frame: the rail's (0, 0, 0) (rear end, mounting face, centre line) at
    origin_M, its +X / +Z along the given axes (a bottom rail: z_axis (0, 0, -1))."""
    x = np.asarray(x_axis, float)
    x /= np.linalg.norm(x)
    z = np.asarray(z_axis, float)
    z = z - (z @ x) * x
    z /= np.linalg.norm(z)
    y = np.cross(z, x)
    M = np.eye(4)
    M[:3, 0], M[:3, 1], M[:3, 2], M[:3, 3] = x, y, z, np.asarray(origin_M, float)
    return M


def chamfer_predicate(M4, rec, width_mm: float = 0.3):
    """Bevel-weight predicate (gunlib.bl.set_bevel_weights, frame M mid points) for the rail placed by M4: the outer
    edges of the slot walls and the end faces (edges lying in a plane normal to the rail's X with a ~90 deg dihedral),
    not the floor junctions (Z at the slot floor) and not the mounting face (Z 0)."""
    Minv = np.linalg.inv(np.asarray(M4, float))
    R = np.asarray(M4, float)[:3, :3]
    xr = R[:, 0]
    floor = rec["floor_z"]

    def pred(mid, d, n1, n2, dih):
        p = Minv[:3, :3] @ mid + Minv[:3, 3]
        if abs(float(d @ xr)) > 0.2:                               # along the rail: profile edges stay crisp
            return 0.0
        if not (abs(abs(float(n1 @ xr)) - 1.0) < 0.05 or abs(abs(float(n2 @ xr)) - 1.0) < 0.05):
            return 0.0                                             # not on a slot wall / end face
        if dih < 60.0:
            return 0.0
        if p[2] < floor + 0.05 or p[2] < 0.05:
            return 0.0                                             # floor junction / mounting face
        return 1.0
    return pred


def part(name: str, M4, n_slots: int, slot="M_Metal", bone="body", chamfer_mm: float = 0.3, joint=None,
         spec_id=None, **kw):
    """A PartDef (gunlib.parts) for the rail placed by M4 (rail frame -> gun frame M): the solid plus the weighted
    chamfer recipe. Returns (PartDef, record with the slot centres in M)."""
    from . import PartDef
    chamfer_mm = max(float(chamfer_mm), STD["edge_chamfer_min"])
    m, rec = rail_1913(n_slots, **kw)
    mm = m.transformed(M4)
    rec = dict(rec)
    rec["slot_centres_M"] = {k: np.round(np.asarray(M4)[:3, :3] @ np.array([x, 0.0, rec["top_z"]]) +
                                         np.asarray(M4)[:3, 3], 4).tolist() for k, x in rec["slot_centres"].items()}
    recipe = [(chamfer_mm, 1, "W", chamfer_predicate(M4, rec, chamfer_mm))] if rec["lod"] < 3 else []
    p = PartDef(name, [mm], bone=bone, cls="M-chamfer", slot=slot, recipe=recipe, smooth_deg=30.0,
                joint=joint or {"type": "butt", "gap_mm": [0.01, 0.05]}, spec_id=spec_id)
    return p, rec
