"""Detail part MAGAZINE: curved body (pressed ribs, raised top plates over a necked top, lips, front lug, front panel
and spine fold, rear strip, bottom band and flange) and the layered floor plate (bone "magazine").

Owns the objects: magazine, magazine_floor_plate. Authority close-ups: c4 MAGAZINE (LEFT, drawn from the true left)
and c5 MAGAZINE (FRONT), the 3/4 view; rifle_spec section 8 mag fit M1-M9 (R32 thickness 26.0).
Interfaces: the well liner (X 368.8-432, Y +-(MAG_HT + 0.5), receiver bottom Z -30.85), the floor line FLOOR (the
traced silhouette's lowest point), the catch below the well (X 355-369.8), the trigger guard's front tang (X <= 367.9,
Z -34.8 .. -29.3).

Detail pass round 2 (2026-10-05). Round 1's blind judge picked ours on: rod-like ribs on a flat field, no front fold,
a flat outlined top with no plate thickness, a thin wedge lug, a thin single-slab floor plate, inset seam lines.
Shape from c4 unwrapped about its own arc centre (rows = angle, columns = u across the width from the rear edge;
WorkFiles/guns/rifle/review/detail/magazine/notes_r2.json), c5 and the 3/4 view; positions / scale from the spec and
the side views:
- 4 PRESSED ribs per side at the spec's u 0.17 / 0.34 / 0.51 / 0.66, half widths 2.3 / 2.5 / 2.5 / 2.3 (c4: the
  middle two read wider): crowned flat top over 30 % of the width, cosine shoulders (~40 deg flanks), 1.0 proud (L4),
  ends ramped down into the face over 2.8 mm and rounded in plan (a pressed end, not a domed rod); top tips stepped
  0.75 lower per rib toward the front, rear tip Z -36.4 (L3 reads the first vertex past 0.5 proud: ~-38.5);
- NECK: above a line 1.2 under the top plate's lower edge the body is 12.4 per side (0.6 chamfer back to 13.0), so the
  plates and the front block stand 0.9 proud of it and still end at Y +-13.3 inside the well liner (+-13.5, lateral
  clearance 0.2): c4's raised plate with visible thickness and chamfered edges; the lips curl above it;
- top plate u 0.05-0.735 (c4: 0.036-0.68 in its own u, which runs low toward the front), top Z -15.4, lower edge
  -34.0 (rear) .. -36.0 (front); front block u 0.75-0.95, top Z -17.25, lower edge 1.0 under the plate's line;
- FRONT PANEL (c4 u 0.70-0.98: a broad raised zone the full length, the judge's "reinforcing ridge along the front"):
  u 0.745 to 0.5 mm short of the front face, 0.45 proud, from the neck line down to the flange; on it the FRONT SPINE
  fold u 0.905 -> front, 0.9 proud in total, from Z -40.5 down (c4's lit line at its u 0.89; its top stays under the
  L3 rib-tip reading);
- rear strip u 0.012-0.075, 0.45 proud, neck line to the band (c4: the lit line at u 0.086);
- band u 0.025-0.745, 5.6-13.5 above the floor face, 0.7 proud, three spot welds; FLANGE (the body's bottom edge the
  floor plate slides on) 4.0-5.0 above the floor face, 0.7 proud, full width: layered bottom (band, flange, plate);
- feed lips / follower / front zone step as round 1 (c5 posts, follower slot); front lug: a fuller lug (Y +-5.6) with a
  convex front following the clearance envelope of the spec's reload path (18 deg rock about the hook + 8 mm insert
  against the plain well front wall X 432: the lug can stand 3.6 proud at its top but only ~0.5 at Z -27), a nose tab
  on top and a window pocket in its front (c5's U-loop); a chunkier lug needs a recess in the receiver's front liner
  wall (review/detail/magazine/spec_proposal.json);
- spines (c5): two raised lines Y +-4.9 on the front face below the lug (the rear-face pair dropped: unseen, triangles);
- floor plate, layered: 4.0 thick, 1.5 lip each side, 0.3 past the rear and 1.8 past the front arc; the front end
  turned up 2.2 in front of the body (rounded top: c4 / c5 / 3-4's bright front lip); the bottom face stepped out 1.4
  over the front 55 % (the side view's floor runs ~2.7 mm outside the spec line toward the front, R30 lowest point
  kept); a recessed panel in the rear bottom with the lock plate's round detent button.
The rear locking lug c4 draws at the top rear cannot be built: the rear liner wall (X 367.8-368.85, Z -29 .. -11) and
the trigger guard's front tang (X <= 367.9, Z -34.8 .. -29.3) leave 0.2-0.5 mm behind the body (spec_proposal.json).
Shading: weighted normals, then the spine cylinders and every flat side face get their exact normals per corner.
"""
from __future__ import annotations

import json
import math

import numpy as np

from rifle_common import SPEC, TRACE
from gunlib import geo2d as G
from gunlib import mesh as MS
from rifle_parts import GAP
from parts import magazine_geo as MG


# ======================================================================================== frame and outline
MAG_C = np.array([604.8, 3.3])
_FN = np.array([0.7728, -0.6346])                # floor plate outward normal (spec outward_normal_M)
_FT = np.array([0.6341, 0.7733])
R_F, R_R = 180.8, 239.0
MAG_T = float(SPEC.key["magazine"]["thickness"])        # 26.0 (R32: the physical minimum closest to the sheet)
MAG_HT = MAG_T / 2
LIP_Z = -12.0                    # lips top (spec lips_top_Z)
FRONT_TOP_Z = -17.0              # front zone top (c4: the front block's top ~5 mm under the lips)
U_STEP = 0.745                   # rear zone (lips, plate) | front zone (front panel, front block, lug)
PLATE_TH = 5.0                   # floor plate thickness (the body stops PLATE_TH above the floor face)
PLATE_LIP = 1.5                  # floor plate side lip (spec lip_proud)
PLATE_REAR, PLATE_FRONT = 0.3, 2.0        # plate past the rear / front arcs along the floor face
PLATE_R_REAR, PLATE_R_FRONT = 3.5, 1.2    # outer corner radii (side outline)
PLATE_UP = 3.0                   # floor plate front end turned up in front of the body
PLATE_RIM = 1.9                  # the plate's folded top edge (the upper 1.9 mm) stands 0.5 wider than its lower part
PLATE_STEP, PLATE_STEP_S = 1.0, 0.45      # bottom face stepped out by 1.0 from 45 % of the length forward
PLATE_TOP_Z = -13.5              # top plate top, under the lip curl (the necked face curls in from Z -13.7)
PLATE_Y = MAG_HT + 0.3           # top plates / front block outer face (the well liner is MAG_HT + 0.5)
PLATE_PROUD = PLATE_Y - MAG_HT   # 0.3 over the 13.0 body face (kept for magazine_dev's landmarks)
NECK_HT = 12.4                   # necked body above the neck line: the plates stand PLATE_Y - NECK_HT = 0.9
NECK_DROP, NECK_CH = 1.2, 0.65   # neck line under the plate's lower-edge line; chamfer back to MAG_HT
PLATE_U = (0.05, 0.735)
PLATE_LOW_Z = (-34.0, -36.0)     # plate lower edge at PLATE_U[0] / PLATE_U[1]
BLOCK_U = (0.75, 0.95)
BLOCK_DROP = 1.0                 # front block lower edge under the plate's line
RIB_U = (0.17, 0.34, 0.51, 0.66)
RIB_HW = (1.55, 1.7, 1.7, 1.5)    # integration round: narrower (x0.75; judge: 'fat raised pill beads'), ends tapered (RIB_TAPER)
RIB_TAPER = 3.0
RIB_H = 1.0
RIB_TIP_Z0, RIB_TIP_STEP = -37.8, 0.75
RIB_END_D = -14.5                # integration round: lower (spec R: bottom ends 16 +- 2 above the floor plate)
PANEL_U, PANEL_PROUD = 0.745, 0.45
SPINE_U, SPINE_PROUD, SPINE_TOP_Z = 0.905, 0.5, -40.5     # integration round: 0.9 -> 0.5 proud (the solved 3/4 view read the
#                                                          front edge proud: magazine region core 229 -> 171 px; still a lit fold line)
REAR_U, REAR_PROUD = (0.012, 0.075), 0.45
FACE_IN = 0.5                    # strips stop this far inside the front / rear faces (no coplanar faces)
BAND_D = (-12.4, -7.2)
BAND_PROUD = 0.7                 # + 0.25 welds stays inside the ribs' 1.0 (L4 reads the Y bounds)
FLANGE_D = (-6.0, -5.03)
FLANGE_PROUD = 0.7
WELL_REAR_X, WELL_FRONT_X = 369.3, 431.65
POCKET_HW = 6.0                  # follower pocket half width (c5: lip posts |Y| 6.0-9.1)


def _traced_lowest_z():
    j = json.loads((TRACE / "LEFT_outline.json").read_text())
    return min(min(p[1] for p in r["mm"]) for r in j["silhouette"])


def _arc_line_hit(R, p0, t):
    """Point where the line p0 + s t meets the circle of radius R about MAG_C (the solution on the magazine)."""
    d = p0 - MAG_C
    b = 2 * d @ t
    c = d @ d - R * R
    disc = math.sqrt(max(b * b - 4 * c, 0.0))
    s = [(-b - disc) / 2, (-b + disc) / 2]
    pts = [p0 + v * t for v in s]
    return min(pts, key=lambda q: abs(q[1] + 160.0))


def _rear_sd(th):
    """Rear part of the floor plate outline (s, d), shared by the floor-line solve and the plate: inner rear chamfer
    and the outer rear corner R PLATE_R_REAR (the lowest point)."""
    s_r, rr = -PLATE_REAR, PLATE_R_REAR
    corner = [(s_r + rr + rr * math.cos(a), -rr + rr * math.sin(a)) for a in np.linspace(0.5 * math.pi, math.pi, 6)]
    return [(s_r, -th + 0.3), (s_r + 0.3, -th)], corner


def _plate_sd(L, front_arc=None):
    """Floor plate outline in the floor frame (s along the face from the rear-arc point, d along the outward normal;
    outer face d = 0 at the rear). front_arc: list of (s, d) on the body's front arc for the turned-up front."""
    th = PLATE_TH - GAP
    inner_rear, corner_rear = _rear_sd(th)
    s_f = L + PLATE_FRONT
    rf = PLATE_R_FRONT
    P = list(inner_rear)
    if front_arc is None:
        P += [(L - 0.3, -th), (L, -th - PLATE_UP)]
    else:
        # relief notch 0.8 deep at the inner corner (the 0.55 bevel fills a concave corner: it must not reach the
        # body's front-bottom corner), then the back face of the turn-up 0.03 in front of the body's front edge
        s_a = front_arc[0][0] + 0.03
        P += [(s_a - 0.7, -th), (s_a - 0.7, -th + 0.8), (s_a, -th + 0.8)]
        P += [(s + 0.03, d) for s, d in front_arc]
    up_top = -th - PLATE_UP
    s_back = P[-1][0]
    ru = 0.75 * (s_f - s_back)                                                 # rounded top of the turn-up
    P += [(s_f - ru + ru * math.cos(a), up_top + ru - ru * math.sin(a)) for a in np.linspace(0.5 * math.pi, 0.0, 4)]
    d_st = PLATE_STEP
    P += [(s_f - rf + rf * math.cos(a), d_st - rf + rf * math.sin(a)) for a in np.linspace(0.0, 0.5 * math.pi, 4)]
    s1 = PLATE_STEP_S * L
    P += [(s1 + 1.4, d_st), (s1, 0.0)]                                         # the step (45 deg)
    P += corner_rear
    return np.array(P, float)


def _sd_to_xz(P, f0):
    P = np.asarray(P, float)
    return f0 + np.outer(P[:, 0], _FT) + np.outer(P[:, 1], _FN)


def _floor_line():
    """Floor face line: the spec corners' direction; offset so the floor plate's lowest vertex (rounded rear corner)
    lands on the traced silhouette's lowest point (R30). Returns f0 (on the rear arc), f1 (on the front arc), shift."""
    c0 = np.array([456.2, -183.9])
    z_low = _traced_lowest_z()
    shift = 0.0
    th = PLATE_TH - GAP
    for _ in range(6):
        p0 = c0 - shift * _FN
        f0 = _arc_line_hit(R_R, p0, _FT)
        zmin = _sd_to_xz(np.array(_rear_sd(th)[1]), f0)[:, 1].min()
        shift += (z_low - zmin) / -_FN[1]
    p0 = c0 - shift * _FN
    f0, f1 = _arc_line_hit(R_R, p0, _FT), _arc_line_hit(R_F, p0, _FT)
    return f0, f1, shift


_F0, _F1, FLOOR_SHIFT = _floor_line()
FLOOR = (_F0, _F1)
FR = MG.ArcFrame(MAG_C, R_R, R_F, _F0, _F1, _FN)


def mag_outline():
    a_top, a_bot = -175.0, -124.0
    fr = G.arc(MAG_C[0], MAG_C[1], R_F, a_top, a_bot, 22)
    rr = G.arc(MAG_C[0], MAG_C[1], R_R, a_bot, a_top, 24)
    P = np.vstack([fr, rr])
    return G.clip_y(G.ccw(P), None, LIP_Z)


def _floor_poly(d_in, d_out, s_pad=30.0):
    """Region between the floor-parallel lines at depths d_in < d_out, long enough to cover the magazine."""
    a = _F0 + d_in * _FN
    b = _F1 + d_in * _FN
    a2 = _F0 + d_out * _FN
    b2 = _F1 + d_out * _FN
    return np.array([a - _FT * s_pad, b + _FT * s_pad, b2 + _FT * s_pad, a2 - _FT * s_pad])


def _at(u, z):
    R = FR.R(u)
    return FR.pt(R, FR.a_at_z(R, z))


_PA, _PB = _at(PLATE_U[0], PLATE_LOW_Z[0]), _at(PLATE_U[1], PLATE_LOW_Z[1])     # plate lower-edge line (XZ)
_PDIR = (_PB - _PA) / np.linalg.norm(_PB - _PA)


def _plate_line(dz):
    """Point and direction of the plate's lower-edge line moved by dz in Z."""
    return _PA + np.array([0.0, dz]), _PDIR


def neck_z(x):
    return MG.line_z(_PA, _PB, x) - NECK_DROP


# ======================================================================================== body cutters
def _body_cutters():
    cut = []
    # floor plate seat: the body stops PLATE_TH above the floor face
    cut.append(MS.prism(_floor_poly(-PLATE_TH, 30.0), -20, 20))
    # well part: inside the liner (X 368.8-432, 0.5 clear) above the receiver bottom
    rear = np.array([[300.0, -33.5], [367.6, -33.5], [WELL_REAR_X, -30.4], [WELL_REAR_X, 0.0], [300.0, 0.0]])
    cut += [MS.prism(rear, -20, 20), MS.box(WELL_FRONT_X, 470.0, -20, 20, -31.2, 0.0)]
    # front zone step (u > U_STEP) down to FRONT_TOP_Z
    st = G.clip_y(FR.sector(U_STEP, 1.4, -179.5, -165.0, 30), FRONT_TOP_Z, None)
    cut.append(MS.prism(st, -20, 20))
    # follower pocket between the lips
    cut.append(MS.box(373.0, 440.0, -POCKET_HW, POCKET_HW, FRONT_TOP_Z, 0.0))
    # lip curls (side walls rolled inward at the top)
    for s in (-1, 1):
        cut.append(_curl(s, 0.0))
    return cut


def _curl(side, dz):
    P = MG.ellipse_cutter_yz(6.6, -15.9 + dz, 6.8, 4.2, 18.0, -4.0 + dz)
    if side < 0:
        P = G.ccw(P * np.array([-1.0, 1.0]))
    return MS.prism(P, 360.0, 440.0, "YZ")


def _neck_cutters():
    """Above the neck line the side faces go to NECK_HT, with a 45 deg chamfer back to MAG_HT below the line."""
    p0, t = _plate_line(-NECK_DROP)
    big = np.array([[340.0, -60.0], [470.0, -60.0], [470.0, 5.0], [340.0, 5.0]])
    P = MG.clip_halfplane(big, p0, t, keep_left=True)
    out = []
    for s in (-1, 1):
        out.append(MG.side_loft(P, s, NECK_HT, MAG_HT + 0.05, 20.0, (0.0, -(MAG_HT + 0.05 - NECK_HT))))
    return out


# ======================================================================================== details
def _plate_outline():
    P = FR.sector(PLATE_U[0], PLATE_U[1], -179.5, -160.0, 8)
    p0, t = _plate_line(0.0)
    P = MG.clip_halfplane(P, p0, t, keep_left=True)
    P = G.clip_y(P, None, PLATE_TOP_Z)
    return G.dedupe(G.fillet(G.dedupe(P, 0.05), 1.5, 2), 0.05)


def _front_block_outline():
    P = FR.sector(BLOCK_U[0], BLOCK_U[1], -179.5, -160.0, 8)
    p0, t = _plate_line(-BLOCK_DROP)
    P = MG.clip_halfplane(P, p0, t, keep_left=True)
    P = G.clip_y(P, None, FRONT_TOP_Z - 0.25)
    return G.dedupe(G.fillet(G.dedupe(P, 0.05), 1.2, 2), 0.05)


def _strip_outline(u0, u1, z_top=None, top_line=True, d_bot=-(PLATE_TH + 0.3), r=1.0):
    """Side strip between the arcs u0..u1, from the neck line (or z_top) down to the floor-relative depth d_bot."""
    P = FR.sector(u0, u1, -179.5, -112.0, 16)
    if top_line:
        p0, t = _plate_line(-NECK_DROP)
        P = MG.clip_halfplane(P, p0, t, keep_left=False)
    if z_top is not None:
        P = G.clip_y(P, None, z_top)
    lo_p, tt = FR.floor_line(d_bot)
    P = MG.clip_halfplane(P, lo_p, tt, keep_left=True)
    return G.dedupe(G.fillet(G.dedupe(P, 0.05), r, 2), 0.05)


def _band_outline():
    P = FR.sector(0.025, U_STEP + 0.012, -150.0, -112.0, 24)      # into the front panel (no coplanar ends)
    lo_p, t = FR.floor_line(BAND_D[0])
    P = MG.clip_halfplane(P, lo_p, t, keep_left=False)          # d >= -13.5
    hi_p, _ = FR.floor_line(BAND_D[1])
    P = MG.clip_halfplane(P, hi_p, t, keep_left=True)           # d <= BAND_D[1]
    return G.dedupe(G.fillet(G.dedupe(P, 0.05), 0.8, 2), 0.05)


def _flange_outline():
    eps = FACE_IN / (R_R - R_F)
    P = FR.sector(eps * 0.4, 1.0 - eps * 0.4, -150.0, -112.0, 24)
    lo_p, t = FR.floor_line(FLANGE_D[0])
    P = MG.clip_halfplane(P, lo_p, t, keep_left=False)
    hi_p, _ = FR.floor_line(FLANGE_D[1])
    P = MG.clip_halfplane(P, hi_p, t, keep_left=True)
    return G.dedupe(P, 0.05)


def _ribs():
    out = []
    for i, (u, hw) in enumerate(zip(RIB_U, RIB_HW)):
        R = FR.R(u)
        a_top = FR.a_at_z(R, RIB_TIP_Z0 - RIB_TIP_STEP * i)
        a_bot = FR.a_at_d(R, RIB_END_D)
        for s in (-1, 1):
            out.append(MG.side_rib_flat(FR, u, a_top, a_bot, s, MAG_HT, hw, RIB_H, step=24.0, taper=RIB_TAPER))
    return out


def _spine_beads():
    out = []
    R, z_top, outward = R_F, -31.0, -1
    a_top = FR.a_at_z(R, z_top)
    a_bot = FR.a_at_d(R, -(PLATE_TH + PLATE_UP + 1.4))            # clear of the floor plate's turned-up front
    for y0 in (-4.9, 4.9):
        out.append(MG.spine_bead(FR, R, a_top, a_bot, y0, outward, 0.6, 0.4, step=24.0))
    return out


def _welds():
    out = []
    for u in (0.12, 0.42, 0.70):
        R = FR.R(u)
        p = FR.pt(R, FR.a_at_d(R, 0.5 * (BAND_D[0] + BAND_D[1])))
        for s in (-1, 1):
            out.append(MS.dome((p[0], s * (MAG_HT + BAND_PROUD - 0.05), p[1]), (0, s, 0), 0.9, 0.3, 6, 2))
    return out


LUG_FRONT = [(-17.2, 428.4), (-17.6, 428.8), (-19.0, 428.2), (-22.0, 427.25), (-25.0, 427.0), (-27.0, 426.95)]
LUG_HW = 5.6


def _lug_parts():
    """Front locking lug (c4: a lug at the top front with a small tab; c5: ~10.4-11 mm wide, a U-loop / window from
    the front). The front follows the clearance envelope of the spec's reload path against the plain well front wall
    (X 432) with ~0.3 mm margin, so it is fullest at the top (3.6 proud) and runs out toward Z -27. Returns the lug
    solid, its rounding section (intersect), the nose tab and the window cutter."""
    side = [(422.6, -17.2)] + [(x, z) for z, x in LUG_FRONT] + [(422.6, -27.0)]
    a = MS.prism(np.array(side), -LUG_HW, LUG_HW)
    sec = G.rounded_rect(-LUG_HW, LUG_HW, -27.0, -15.0, 2.0, 2)
    tab = MS.prism(G.rounded_rect(425.3, 428.6, -17.6, -15.4, 0.9, 2), -3.4, 3.4)
    # window pocket in the front face (Z -18.4 .. -21.6), 1.0 deep along X
    win = np.array([[427.2, -18.4], [431.0, -18.4], [431.0, -21.6], [426.4, -21.6]])
    return a, MS.prism(sec, 421.0, 433.0, "YZ"), tab, MS.prism(win, -3.3, 3.3)


def _weighted_normals(ob):
    """Weighted normals with the face-area weight at 100 (the large flat and cylindrical faces keep their own normals
    next to the bevels and the rib / bead seams)."""
    from gunlib import bl
    bl.triangulate_ngons(ob)
    bl.mark_sharp(ob, 35.0)
    mod = ob.modifiers.new("wn", "WEIGHTED_NORMAL")
    mod.keep_sharp = True
    mod.mode = "FACE_AREA"
    mod.weight = 100
    bl.apply_modifiers(ob)


def _analytic_normals(ob, offset, spines=True):
    """Harden the big surfaces after the weighted normals: every corner of a face that lies on the front or rear
    spine cylinder (R_F / R_R about MAG_C) or on a flat side plane (any face normal to Y: body, neck, plates, strips,
    band, flange) gets the surface's exact normal at its vertex, so the triangulated strips between the beads, ribs
    and bevels shade as one surface."""
    import math as _m
    me = ob.data
    off = np.asarray(offset, float)
    V = np.array([v.co for v in me.vertices]) * 1000.0 + off
    cn = np.array([v.vector for v in me.corner_normals], float)
    loops_v = np.array([l.vertex_index for l in me.loops])
    changed = 0
    for p in me.polygons:
        n = np.array(p.normal, float)
        c = np.array(p.center, float) * 1000.0 + off
        dx, dz = c[0] - MAG_C[0], c[2] - MAG_C[1]
        r = _m.hypot(dx, dz)
        radial = np.array([dx / r, 0.0, dz / r])
        kind = None
        if abs(n[1]) > 0.9995:
            kind = "side"
        elif spines and abs(r - R_F) < 0.6 and n @ -radial > 0.985:
            kind = "front"
        elif spines and abs(r - R_R) < 0.6 and n @ radial > 0.985:
            kind = "rear"
        if kind is None:
            continue
        for li in p.loop_indices:
            q = V[loops_v[li]]
            if kind == "side":
                cn[li] = (0.0, float(np.sign(n[1])), 0.0)
            else:
                ddx, ddz = q[0] - MAG_C[0], q[2] - MAG_C[1]
                rr = _m.hypot(ddx, ddz)
                cn[li] = np.array([ddx / rr, 0.0, ddz / rr]) * (-1.0 if kind == "front" else 1.0)
            changed += 1
    me.normals_split_custom_set([tuple(v) for v in cn])
    me.update()
    return changed


def _union_all(ob, objs):
    """One EXACT union with a collection operand holding every detail object."""
    import bpy
    from gunlib import bl
    col = bpy.data.collections.new("_mag_details")
    bpy.context.scene.collection.children.link(col)
    for o in objs:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        col.objects.link(o)
    mod = ob.modifiers.new("union", "BOOLEAN")
    mod.operation = "UNION"
    mod.solver = "EXACT"
    mod.operand_type = "COLLECTION"
    mod.collection = col
    bl.apply_modifiers(ob)
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(col)


def build_magazine(coll, offset):
    """magazine body: cut + rounded (S-bend 1.6 / 2) body, the neck cut, then the pre-bevelled plates, block, strips,
    band, flange and lug and the smooth ribs / beads / welds unioned on (explicit boolean steps)."""
    from gunlib import bl
    body = MS.prism(mag_outline(), -MAG_HT, MAG_HT)
    ob = body.to_object("magazine", coll, offset)
    bl.boolean_many(ob, _body_cutters(), "DIFFERENCE", offset=offset)
    bl.clean(ob)
    bl.bevel(ob, 1.6, 2, 50.0)
    bl.boolean_many(ob, _neck_cutters(), "DIFFERENCE", offset=offset)
    bl.clean(ob)
    det = []

    def pre(mesh, name, w, seg, ang=40.0):
        """Detail prism standing on a side face: only its outer loop is rounded (the inner loop is buried by the
        union, bevelling it would only add triangles)."""
        o = mesh.to_object(name, coll, offset)
        y_out = float(np.abs(mesh.verts()[:, 1]).max())
        bl.bevel_weighted(o, w, seg, lambda mid, d, n1, n2, dih: 1.0 if (abs(mid[1]) > y_out - 0.05 and dih > ang)
                          else 0.0, offset)
        det.append(o)
        return o

    rear_o = _strip_outline(REAR_U[0], REAR_U[1], d_bot=BAND_D[0] + 0.5, r=0.6)
    panel_o = _strip_outline(PANEL_U, 1.0 - (FACE_IN + 0.3) / (R_R - R_F))
    spine_o = _strip_outline(SPINE_U, 1.0 - FACE_IN / (R_R - R_F), z_top=SPINE_TOP_Z, top_line=False)
    for s in (-1, 1):
        pre(MG.side_prism(_plate_outline(), s, PLATE_Y - NECK_HT, 0.5, NECK_HT), "_dplate", 0.35, 2)
        pre(MG.side_prism(_front_block_outline(), s, PLATE_Y - NECK_HT, 0.5, NECK_HT), "_dblock", 0.35, 2)
        pre(MG.side_prism(_band_outline(), s, BAND_PROUD, 1.6, MAG_HT), "_dband", 0.25, 1)
        pre(MG.side_prism(_flange_outline(), s, FLANGE_PROUD, 1.6, MAG_HT), "_dflange", 0.25, 1)
        pre(MG.side_prism(rear_o, s, REAR_PROUD, 1.2, MAG_HT), "_drear", 0.2, 1)
        pre(MG.side_prism(panel_o, s, PANEL_PROUD, 1.2, MAG_HT), "_dpanel", 0.3, 2)
        pre(MG.side_prism(spine_o, s, SPINE_PROUD, 0.6, MAG_HT), "_dspine", 0.35, 1)
    fo = MS.box(375.0, 404.0, -4.6, 4.6, FRONT_TOP_Z - 0.5, -14.6).to_object("_dfollower", coll, offset)
    bl.boolean(fo, MS.box(397.4, 401.0, -1.3, 1.3, -16.2, -13.0), "DIFFERENCE", offset=offset)    # c5: slot in its front
    bl.clean(fo)
    bl.bevel(fo, 0.4, 1, 40.0)
    det.append(fo)
    lug, lug_sec, tab, win = _lug_parts()
    lo = lug.to_object("_dlug", coll, offset)
    bl.boolean(lo, lug_sec, "INTERSECT", offset=offset)
    bl.boolean(lo, tab, "UNION", offset=offset)
    bl.boolean(lo, win, "DIFFERENCE", offset=offset)
    bl.clean(lo)
    bl.bevel(lo, 0.3, 1, 40.0)
    det.append(lo)
    smooth = _ribs() + _spine_beads() + _welds()
    smooth_objs = [m.to_object("_dsm", coll, offset, smooth_deg=None) for m in smooth]
    _union_all(ob, det + smooth_objs)
    bl.clean(ob)
    bl.finish(ob)
    _weighted_normals(ob)
    _analytic_normals(ob, offset)
    rec = {"bone": "magazine", "class": "S-bend", "slot": "M_AR01_Mag",
           "joint": {"type": "seated_mag", "parent": "receiver", "note": "detail pass r2; the fit stage fits the hidden top"},
           "spec_id": "magazine_body",
           "recipe": [[1.6, 2, 50.0], [0.35, 2, "details pre-bevelled"]]}
    ob["gun_part"] = json.dumps(rec)
    return ob


def _front_arc_sd():
    """(s, d) of the body's front edge (the outline polygon's chords, which stand up to 0.04 in front of the true arc)
    from just under the seat up the turn-up height."""
    th = PLATE_TH - GAP
    P = mag_outline()
    S = (P - _F0) @ _FT
    D = (P - _F0) @ _FN
    out = []
    for d in np.linspace(-th - 0.8, -th - PLATE_UP, 4):
        best = -1e9
        for i in range(len(P)):
            j = (i + 1) % len(P)
            if (D[i] - d) * (D[j] - d) <= 0 and D[i] != D[j]:
                best = max(best, S[i] + (S[j] - S[i]) * (d - D[i]) / (D[j] - D[i]))
        out.append((float(best), float(d)))
    return out


def build_floor(coll, offset):
    """Layered floor plate: the side outline (turned-up front, stepped bottom, rounded corners) across Y +-(MAG_HT +
    PLATE_LIP), rounded 0.55 / 2, then the bottom panel recess and the detent button, crisp 0.2 / 1."""
    from gunlib import bl
    L = float(np.linalg.norm(_F1 - _F0))
    P = _sd_to_xz(_plate_sd(L, _front_arc_sd()), _F0)
    yl = MAG_HT + PLATE_LIP
    th = PLATE_TH - GAP
    ob = MS.prism(P, -(yl - 0.5), yl - 0.5).to_object("magazine_floor_plate", coll, offset)
    # folded top edge: the outline's part above d = -th + PLATE_RIM, 0.5 wider each side (c4 / 3-4: a lit upper layer
    # over a darker lower one)
    lo_p = _F0 + (-th + PLATE_RIM) * _FN
    rim = MG.clip_halfplane(P, lo_p, _FT, keep_left=True)
    bl.boolean(ob, MS.prism(rim, -yl, yl), "UNION", offset=offset)
    bl.clean(ob)
    bl.bevel(ob, 0.55, 2, 30.0)
    # bottom recess (rear segment) and the lock plate's detent button in it
    s0, s1 = 2.6, PLATE_STEP_S * L - 1.6
    rr = G.rounded_rect(s0, s1, -(yl - 3.0), yl - 3.0, 2.0, 3)

    def ring(d):
        xz = _sd_to_xz(np.c_[rr[:, 0], np.full(len(rr), d)], _F0)
        return np.c_[xz[:, 0], rr[:, 1], xz[:, 1]]
    rec_cut = MS.loft([ring(-0.6), ring(3.0)])
    bl.boolean(ob, rec_cut, "DIFFERENCE", offset=offset)
    c = _sd_to_xz([(s1 - 6.5, -0.9)], _F0)[0]
    c2 = _sd_to_xz([(s1 - 6.5, -0.15)], _F0)[0]
    btn = MS.cylinder((c[0], 0.0, c[1]), (c2[0], 0.0, c2[1]), 2.4, 16)
    bl.boolean(ob, btn, "UNION", offset=offset)
    bl.clean(ob)
    bl.bevel(ob, 0.2, 1, 60.0)
    bl.finish(ob)
    _weighted_normals(ob)
    rec = {"bone": "magazine", "class": "S-bend", "slot": "M_AR01_Mag", "joint": {"type": "butt", "gap_mm": [0.01, 0.05]},
           "spec_id": "magazine_floor_plate", "recipe": [[0.55, 2, 30.0], [0.2, 1, 60.0]]}
    ob["gun_part"] = json.dumps(rec)
    return ob


# ======================================================================================== module interface
OBJECTS = ('magazine', 'magazine_floor_plate')            # registry keys built here (rifle_parts.ORDER)
CLOSEUPS = ('c4', 'c5', 'q34')          # sheet panels that are this part's shape authority (rifle_detail.py)


def build(spec, ctx):
    """Build this module's objects into ctx (gunlib.parts.BuildCtx). Returns {registry key: [objects]}; keys that
    ctx.only excludes come back empty. `spec` is the rifle GunSpec (the same object as rifle_common.SPEC)."""
    return {k: ctx.make(k, f) for k, f in (("magazine", build_magazine), ("magazine_floor_plate", build_floor),)}
