"""Detail part PISTOL GRIP: loft of rounded sections on the traced side outline, flat bottom, checkered
panels on both sides.

Owns the object: pistol_grip (LOD0) and the review/bake-only checker field pistol_grip_checker (build_checker_field;
NOT built by build(), see grip_checker.py). Authority close-ups: c6 PISTOL GRIP AND TRIGGER (LEFT) and c1 (right), the
3/4 view; H1 hand-fit gate (rifle_h1.py: width / girth at the Grip socket) and the side silhouette must keep passing.
Interfaces: the flange joint Z -34.82, the guard leg GRIP_LEG, the Grip socket (frame B origin).
Detail round 1 (2026-10-05): the checker panel is the quadrilateral measured on c6 + c1 (grip_checker.PANEL_TS,
front-high raked top, ~46 % of the depth in the front half) instead of the axis-aligned 15.9 mm rounded rectangle;
the diamond field is a modelled bead / pyramid slab (groove spacing 1.67 / 1.89, two ~91 deg families measured by FFT)
= the normal-map bake source, rendered in review in place of the bake; recess 0.75; the guard-leg slot is only the
leg's width. Review driver: grip_review.py / grip_loop.py; measurements: grip_measure.py; H1: grip_h1.py.
Detail round 2 (2026-10-05; round-1 blind judge tells): the side outline is the trace reshaped to c6's form
(grip_shape.py: square top-back corner + straight edge into the neck instead of the swell-and-dip, a straight block face
and a soft R 8 / R 16 shoulder under the guard instead of the notch, squarer R 4 heel, round toe nose); flatter sides
with defined strap edges (front R 7, R 4 on the block, back R 9, crown 0.35); bottom round 2.5 (3 seg) with the flange
break as its own pass; the panel = the c6 corners alone, R 0.8, crisp 0.15 wall and a 0.7 flat border band; the cells
= continuous diagonal ridges with shallow cross-notches (A 46 deg / 1.61, B -49 / 1.72); the bake-source field is
clipped with bisect planes (manifold). Inspection: grip_overlay.py (silhouettes), grip_views.py (Workbench views).
"""
from __future__ import annotations

import json
import math

import numpy as np

from rifle_common import SPEC
from gunlib import geo2d as G
from gunlib import mesh as MS
from rifle_parts import GAP


# ======================================================================================== furniture
def trace_outline():
    """The traced side outline (spec side_profile_M), smoothed, top on the flange joint, bottom at the key's Z."""
    P = G.clean_smooth(SPEC.profile("pistol_grip"), 1.4, 1.8, 35.0)
    top = P[:, 1] > -37.6
    P[top & (P[:, 0] > 244.0) & (P[:, 0] < 301.5), 1] = -34.82
    zb = SPEC.key["grip"]["bottom_Z"]
    P[:, 1] = -34.82 + (P[:, 1] + 34.82) * ((zb + 34.82) / (P[:, 1].min() + 34.82))
    P = G.dedupe(P, 0.05)
    return P


_OUTLINE = None


def grip_outline():
    """Detail round 2: the trace reshaped to the c6 close-up's form (grip_shape.py: square top-back corner and a straight
    edge into the neck, a soft shoulder under the guard, squarer heel, round toe nose)."""
    global _OUTLINE
    if _OUTLINE is None:
        from parts import grip_shape
        _OUTLINE = grip_shape.reshape(trace_outline())
    return _OUTLINE.copy()


# ---- pistol grip (form fix round 1): a LOFT of rounded sections, not a slab with edge bevels.
# The slab (flat +-15 sides, 7.5 mm weighted bevel) clamped to almost nothing on the dense traced outline: girth
# 141 mm and a slab look in the 3/4 view. The spec's section is "a rounded oblong (30 wide), flatter sides where the
# checkering sits, straps R 8-10"; the side outline stays the trace. Construction:
#   rings   horizontal sections at Z levels (the top is the horizontal flange joint); each ring is the
#           perpendicular section (rounded rectangle D x W, strap radius R, sides crowned C1-smoothly by `crown`)
#           stretched along X onto the outline's back..front interval at that Z (D = interval * cos(rake));
#   bottom  the rings run on past the heel / toe and the traced bottom chain is cut with a boolean (flat end),
#           then the bottom edges get a 1.0 mm round (2 seg) and the flange edge a 0.5 mm break;
#   panels  checkered panel border = real geometry: a 0.6 mm recess that follows the rounded side (panel prism
#           minus the loft shrunk 0.6 in Y), border bevel 0.3; the diamonds go in the normal map.
GRIP_RAKE = 22.35          # axis rake from vertical (spec)
GRIP_W = float(SPEC.dims("pistol_grip")["width_Y"])   # section width Y (spec; real AK grips 30-36 mm, rifle_h1)
# detail round 2: flatter sides with defined edges where they meet the straps (c6; the round-1 judge read the R 9 /
# R 13.5 straps as "evenly tapered, smoothly blended, almost like rubber"): front strap R 7, back strap R 9, crown
# 0.35 (spec R 9 / R 13.5 / -: proposal in review/detail/grip/spec_proposal.json); H1 girth stays in its band
GRIP_R = 9.0               # front strap R (integration round: 7.0 -> 9.0, the spec R33 value; at R 7 the solved 3/4 view
                           # read the front strap 10 px proud (region core 243 px, 3/4 IoU 0.9137 < 0.915); R 4 on the block stays)
GRIP_R_BACK = 9.0
GRIP_R_TOP = 4.0           # front strap radius on the block beside the guard leg (Z above R_TOP_Z0), ramped to GRIP_R by
R_TOP_Z0, R_TOP_Z1 = -50.0, -68.0   # R_TOP_Z1: c6 draws the block as a flat-sided wedge with a crisp front edge
GRIP_CROWN = 0.35          # side crown at mid-depth (flatter sides where the checkering sits)
GRIP_NR = 34               # vertices per ring (round 1: 30; the tighter strap radii need the samples)
GRIP_Z_TOP = -34.82
# heel / toe cut levels: the outline's rearmost heel point and foremost toe point (vertical tangents), from the
# reshaped outline (round 1 constants: -117.21 / -127.78)
from parts import grip_shape as _GS  # noqa: E402
GRIP_Z_BACK_CUT, GRIP_Z_FRONT_CUT = _GS.cut_levels(grip_outline())
GRIP_Z_END = -137.0
CARRY_OUT = 0.02           # rings below the heel / toe cut levels: this far outside the outline (round 1: 0.6)


def _hits_x(P, z):
    Q = np.vstack([P, P[:1]])
    xs = []
    for a, b in zip(Q[:-1], Q[1:]):
        if (a[1] - z) * (b[1] - z) <= 0 and a[1] != b[1]:
            t = (z - a[1]) / (b[1] - a[1])
            xs.append(a[0] + t * (b[0] - a[0]))
    return (min(xs), max(xs)) if len(xs) >= 2 else None


def _rrect2(a0, a1, b0, b1, ra, rb, seg=24):
    """Rounded rectangle with corner radius ra at the a0 end (back strap) and rb at the a1 end (front strap)."""
    pts = []
    for (cx, cy, r, s0) in ((a1 - rb, b0 + rb, rb, -90), (a1 - rb, b1 - rb, rb, 0), (a0 + ra, b1 - ra, ra, 90),
                            (a0 + ra, b0 + ra, ra, 180)):
        pts.append(G.arc(cx, cy, r, s0, s0 + 90, seg + 1))
    return G.dedupe(np.vstack(pts))


def grip_section(D, W=GRIP_W, R=GRIP_R, crown=GRIP_CROWN, n=GRIP_NR, Rb=None):
    """Perpendicular section, s = 0 at the back strap .. D at the front strap, y across. Starts at the back strap
    middle (s 0, y 0) and runs CCW in (s, y); n points by arc length (consistent rings for the loft). R = front strap
    radius, Rb = back strap radius (default GRIP_R_BACK)."""
    Rb = GRIP_R_BACK if Rb is None else Rb
    R = min(R, 0.5 * W - 1e-3, 0.5 * D - 1e-3)
    Rb = min(Rb, 0.5 * W - 1e-3, 0.5 * D - 1e-3)
    h = 0.5 * W - crown
    rr = G.ccw(_rrect2(0.0, D, -h, h, Rb, R, 24))
    rr = G.resample(rr, 0.15)
    # crown the flat side runs (C1: zero value and slope where the strap arcs begin)
    s0, s1 = Rb, D - R
    u = (rr[:, 0] - 0.5 * (s0 + s1)) / max(0.5 * (s1 - s0), 1e-6)
    flat = (np.abs(u) < 1.0) & (np.abs(rr[:, 1]) > h - 1e-6)
    rr[flat, 1] += np.sign(rr[flat, 1]) * crown * (1 - u[flat] ** 2) ** 2
    k = int(np.argmin(rr[:, 0] + 10 * np.abs(rr[:, 1])))          # back strap middle
    rr = np.roll(rr, -k, axis=0)
    Q = np.vstack([rr, rr[:1]])
    dd = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Q, axis=0), axis=1))]
    t = np.linspace(0, dd[-1], n, endpoint=False)
    return np.c_[np.interp(t, dd, Q[:, 0]), np.interp(t, dd, Q[:, 1])]


def grip_levels(P, tol=0.12, max_gap=6.0):
    """Z levels for the rings: a level wherever the outline's back or front leaves the straight line between the
    last kept level and the next by > tol mm (chordal error), at most max_gap apart. Form fix round 2: round 1 kept a
    level wherever the back/front MOVED 1.2 mm, which the 22 deg rake alone triggers every ~3 mm on straight runs
    (40 rings; the receiver's restored 0.3 mm arc bevel needs the triangles)."""
    zs = np.arange(GRIP_Z_TOP - 0.25, GRIP_Z_BACK_CUT + 0.2, -0.25)
    hits = {}

    def H(z):
        if z not in hits:
            hits[z] = _hits_x(P, min(z, GRIP_Z_TOP - 1e-3))
        return hits[z]

    keep = [GRIP_Z_TOP]
    i0 = -1                                   # index in zs of the last kept level (-1 = the top)
    i = 0
    while i < len(zs):
        z0 = keep[-1]
        ok_i = None
        for j in range(i, len(zs)):
            z1 = zs[j]
            if z0 - z1 > max_gap:
                break
            h0, h1 = H(z0), H(z1)
            if h0 is None or h1 is None:
                continue
            bad = False
            for k in range(i, j):
                zk = zs[k]
                hk = H(zk)
                if hk is None:
                    continue
                t = (z0 - zk) / (z0 - z1)
                if (abs(hk[0] - (h0[0] + t * (h1[0] - h0[0]))) > tol
                        or abs(hk[1] - (h0[1] + t * (h1[1] - h0[1]))) > tol):
                    bad = True
                    break
            if bad:
                break
            ok_i = j
        if ok_i is None:
            ok_i = i
        keep.append(float(zs[ok_i]))
        i = ok_i + 1
    keep = [z for z in keep if z > GRIP_Z_BACK_CUT + 0.5]
    keep.append(GRIP_Z_BACK_CUT)
    low = [-121.2, -124.5, -126.5, -129.0, -131.0, -134.0]   # round 2: -122.0 met the panel's front-bottom fillet (2 multi-face edges)
    low = [z for z in low if z < GRIP_Z_BACK_CUT - 0.5 and abs(z - GRIP_Z_FRONT_CUT) > 0.5]
    keep += sorted(low + [GRIP_Z_FRONT_CUT], reverse=True) + [GRIP_Z_END]
    return np.array(keep)


def grip_intervals(P):
    """(z, x_back, x_front) per ring: exact outline hits down to the heel / toe cut levels, then carried straight
    down just outside the outline so the bottom boolean, not the loft, makes the traced bottom. The cut levels are
    the outline's rearmost heel / foremost toe points (vertical tangents), so the carried rings continue the straps
    tangentially; form fix round 2 carries them 0.02 mm outside (round 1: 0.6 mm, which bent the strap out between
    the cut level and the next ring and left a 0.6 mm lip at the toe where the cut met it)."""
    out = []
    xb_heel = _hits_x(P, GRIP_Z_BACK_CUT)[0]
    xf_toe = _hits_x(P, GRIP_Z_FRONT_CUT)[1]
    for z in grip_levels(P):
        h = _hits_x(P, min(z, GRIP_Z_TOP - 1e-3))
        xb = h[0] if (h is not None and z >= GRIP_Z_BACK_CUT) else xb_heel - CARRY_OUT
        xf = h[1] if (h is not None and z >= GRIP_Z_FRONT_CUT) else xf_toe + CARRY_OUT
        out.append((float(z), float(xb), float(xf)))
    return out


def grip_rings(W=GRIP_W, R=GRIP_R, crown=GRIP_CROWN, n=GRIP_NR, dy=0.0, dr=0.0, Rb=None):
    """Rings in frame M. dy / dr shrink the half width / strap radius (the panel-recess inner loft)."""
    P = grip_outline()
    c = math.cos(math.radians(GRIP_RAKE))
    rings = []
    for z, xb, xf in grip_intervals(P):
        D = (xf - xb) * c
        u = min(max((z - R_TOP_Z1) / (R_TOP_Z0 - R_TOP_Z1), 0.0), 1.0)
        u = u * u * (3 - 2 * u)                        # smoothstep: 1 on the block, 0 below R_TOP_Z1
        Rz = min(R, R + u * (GRIP_R_TOP - R))
        sec = grip_section(D, W - 2 * dy, Rz - dr, crown, n, (GRIP_R_BACK if Rb is None else Rb) - dr)
        x = xb + sec[:, 0] / D * (xf - xb)
        rings.append(np.c_[x, sec[:, 1], np.full(n, z)])
    return rings


def grip_bottom_cutter():
    """XZ polygon below the traced bottom chain, from the heel cut level round the toe to the front cut level."""
    P = G.ccw(grip_outline())
    b = np.array([_hits_x(P, GRIP_Z_BACK_CUT)[0], GRIP_Z_BACK_CUT])
    f = np.array([_hits_x(P, GRIP_Z_FRONT_CUT)[1], GRIP_Z_FRONT_CUT])
    # CCW (Z up) runs back strap -> heel -> bottom -> toe -> front strap: walk from the vertex after b to before f
    k0 = int(np.argmin(np.hypot(*(P - b).T)))
    k1 = int(np.argmin(np.hypot(*(P - f).T)))
    idx = [(k0 + i) % len(P) for i in range(((k1 - k0) % len(P)) + 1)]
    chain = P[idx]
    chain = chain[(chain[:, 1] < GRIP_Z_BACK_CUT - 1e-6) & (chain[:, 1] < GRIP_Z_FRONT_CUT - 1e-6)
                  | ((chain[:, 0] < 255.0) & (chain[:, 1] < GRIP_Z_BACK_CUT - 1e-6))]
    chain = chain[(np.hypot(*(chain - b).T) > 0.05) & (np.hypot(*(chain - f).T) > 0.05)]
    poly = np.vstack([[b + (-15.0, 0.0)], [b], chain, [f], [f + (15.0, 0.0)],
                      [(f[0] + 15.0, -160.0)], [(b[0] - 15.0, -160.0)]])
    return G.dedupe(poly, 1e-4)


def grip_panel_outline():
    """Checkered panel (per side): the quadrilateral measured on c6 / c1 (grip_checker.PANEL_TS), corners R 2."""
    from parts import grip_checker as GC
    return GC.panel_outline_xz()


BORDER_BEVEL = 0.15        # panel recess wall / leg slot edges (round 1: 0.3; the judge read the rim as soft: "cut into
                           # the surface, with a distinct border line" in the reference)
GRIP_LEG = [(298.6, -34.0), (303.3, -34.0), (303.3, -60.0), (298.4, -60.0)]   # guard rear leg (cut back 0.02)
GRIP_LEG_HALF_W = 5.0      # the guard loop's half width (trigger_guard.LOOP_W): detail round 1 cuts the leg slot only
                           # this wide (+ LEG_SIDE_GAP), the full-width cut left a flat notch face and a ledge at Z -60 that
                           # the 3/4 view showed; c6 / 3/4 draw the grip's rounded front wrapping the leg
LEG_SIDE_GAP = 0.05        # slot side clearance: the slot / top / strap corner's bevels pull a vertex ~0.024 into the
                           # slot, so 0.02 left a 0.004 mm gap; 0.05 keeps >= 0.01 (clearance row 0.01-0.05)


def grip_mesh_numpy(W=GRIP_W, R=GRIP_R, crown=GRIP_CROWN, Rb=None):
    """Plain-numpy approximation for silhouette sweeps: the loft with vertices outside the traced bottom moved onto
    it (the Blender build cuts it with a boolean instead)."""
    m = MS.loft(grip_rings(W, R, crown, Rb=Rb))
    V = m.verts()
    cut = grip_bottom_cutter()
    inside = np.array([G.point_in_poly((v[0], v[2]), cut) for v in V])
    P = grip_outline()
    chain = P[P[:, 1] < -110.0]
    for i in np.nonzero(inside)[0]:
        d = np.hypot(chain[:, 0] - V[i, 0], chain[:, 1] - V[i, 2])
        k = int(np.argmin(d))
        V[i, 0], V[i, 2] = chain[k]
    out = MS.Mesh()
    out.add_verts(V)
    out.F = list(m.F)
    return out


BOTTOM_ROUND = 2.5         # bottom end round (round 1: 1.0, 2 seg): c6 draws the toe nose and base edges well rounded
                           # (the round-1 toe read as a thin flange with a sharp lip)


def pred_grip_bottom(mid, d, n1, n2, dih):
    if dih < 25:
        return 0.0
    if mid[2] < GRIP_Z_BACK_CUT + 1.0 or (mid[2] < GRIP_Z_FRONT_CUT + 1.0 and mid[0] > 262.0):
        return 1.0                                   # bottom end: BOTTOM_ROUND mm round
    return 0.0


def pred_grip_flange(mid, d, n1, n2, dih):
    return 1.0 if (dih >= 25 and mid[2] > GRIP_Z_TOP - 0.3) else 0.0   # flange joint: 0.5 mm break


def build_pistol_grip(coll, offset):
    import bpy
    from gunlib import bl
    ob = MS.loft(grip_rings()).to_object("pistol_grip", coll, offset, smooth_deg=35.0)
    bl.boolean_many(ob, [MS.prism(grip_bottom_cutter(), -40.0, 40.0),
                         MS.prism(G.offset(G.ccw(np.array(GRIP_LEG)), GAP), -GRIP_LEG_HALF_W - LEG_SIDE_GAP,
                                  GRIP_LEG_HALF_W + LEG_SIDE_GAP)], "DIFFERENCE", offset=offset)
    bl.clean(ob)
    bl.bevel_weighted(ob, BOTTOM_ROUND, 3, pred_grip_bottom, offset)
    bl.bevel_weighted(ob, 0.5, 1, pred_grip_flange, offset)   # separate pass: a 0.25-weight share of the 3-segment
                                                                # bottom bevel broke the flange edge into notches
    # panel recess: panel prisms minus the loft shrunk RECESS in Y (the recess follows the rounded side)
    from parts import grip_checker as GC
    panel = grip_panel_outline()
    cut = MS.prism(panel, -25.0, -8.0).to_object("_gpanel", coll, offset)
    bl.boolean(cut, MS.prism(panel, 8.0, 25.0), "UNION", offset=offset)
    inner = MS.loft(grip_rings(dy=GC.RECESS, dr=GC.RECESS)).to_object("_ginner", coll, offset)
    bl.boolean(cut, inner, "DIFFERENCE")
    bpy.data.objects.remove(inner, do_unlink=True)
    bl.boolean(ob, cut, "DIFFERENCE")
    bpy.data.objects.remove(cut, do_unlink=True)
    bl.clean(ob)
    bl.bevel(ob, BORDER_BEVEL, 1, 50.0)
    bl.finish(ob)
    bl.weighted_normals(ob)
    # form fix round 2: the boolean/bevel triangulation left shading blotches beside the checker panel under weighted
    # normals; faces on the loft (or on the recess floor) take the smooth loft normals instead
    src = [MS.loft(grip_rings()).to_object("_gsrc_outer", coll, offset),
           MS.loft(grip_rings(dy=GC.RECESS, dr=GC.RECESS)).to_object("_gsrc_floor", coll, offset)]
    n_on = bl.surface_normals_from(ob, src, tol_mm=0.05, max_angle_deg=20.0)
    for o in src:
        bpy.data.objects.remove(o, do_unlink=True)
    print("[AR01] pistol_grip: %d faces take the loft's smooth normals" % n_on)
    ob["gun_part"] = json.dumps({"bone": "body", "class": "W-round", "slot": "M_AR01_Furniture",
                                 "spec_id": "pistol_grip", "joint": {"type": "butt", "parent": "receiver",
                                                                     "gap_mm": [0.01, 0.05]},
                                 "recipe": [[BOTTOM_ROUND, 3, "weighted bottom"], [0.5, 1, "weighted flange"], [BORDER_BEVEL, 1, 50.0]],
                                 "section": {"construction": "loft of rounded sections", "width_Y": GRIP_W,
                                             "strap_R": GRIP_R, "strap_R_back": GRIP_R_BACK,
                                             "strap_R_block": [GRIP_R_TOP, R_TOP_Z0, R_TOP_Z1], "side_crown": GRIP_CROWN},
                                 "checker_panel": {"corners_ts": GC.PANEL_TS, "corner_R": GC.PANEL_R,
                                                   "recess": GC.RECESS, "border_bevel": BORDER_BEVEL, "border_band": GC.PANEL_SHRINK,
                                                   "cells": {"families_deg_from_vertical": [GC.FAM_A_DEG, GC.FAM_B_DEG],
                                                             "pitch": [GC.PITCH_A, GC.PITCH_B], "apex_h": GC.APEX_H,
                                                             "source": "normal map baked from pistol_grip_checker"}}})
    return ob


def build_checker_field(coll, offset, name="pistol_grip_checker"):
    """The modelled bead / pyramid field on both panels (closed slabs intersected with the panel prism): the normal-map BAKE
    SOURCE. Not part of the LOD0 mesh or the export; the review driver adds it so ROUGH LOOK renders show the cells."""
    from gunlib import bl
    from parts import grip_checker as GC
    import bmesh
    from mathutils import Vector
    floor = GC.floor_fn(grip_rings(dy=GC.RECESS, dr=GC.RECESS))
    fo = GC.field_outline_xz()
    m = GC.pyramid_slab(floor, fo, +1)
    m.extend(GC.pyramid_slab(floor, fo, -1))
    ob = m.to_object(name, coll, offset, smooth_deg=None)
    # clip to the field quad with four bisect planes + cap fills (round 2: the EXACT intersect with the field prism left
    # 1-4 non-manifold edges where lattice lines met the walls; the field quad's corners are R 0.1 after the 0.7 inset,
    # so planes along its straight edges are the same outline to 0.04 mm)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    for p0, nrm in GC.field_clip_planes():
        co = Vector(((p0[0] - offset[0]) / 1000.0, 0.0, (p0[1] - offset[2]) / 1000.0))
        no = Vector((nrm[0], 0.0, nrm[1]))
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        res = bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-9, plane_co=co, plane_no=no, clear_outer=True)
        cut = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
        bmesh.ops.holes_fill(bm, edges=cut, sides=0)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    bl.finish(ob)
    ob.data.polygons.foreach_set("use_smooth", [False] * len(ob.data.polygons))
    ob.data.update()
    ob["gun_part"] = json.dumps({"bone": "body", "class": "bake-source", "slot": "M_AR01_Furniture",
                                 "spec_id": "pistol_grip", "bake_source_for": "pistol_grip", "lod0": False,
                                 "export": False})
    return ob


REVIEW_EXTRAS = (("pistol_grip_checker", build_checker_field),)   # review-only objects (grip_review.py)


# ======================================================================================== module interface
OBJECTS = ('pistol_grip',)            # registry keys built here (rifle_parts.ORDER)
CLOSEUPS = ('c6', 'c1', 'q34')          # sheet panels that are this part's shape authority (rifle_detail.py)


def build(spec, ctx):
    """Build this module's objects into ctx (gunlib.parts.BuildCtx). Returns {registry key: [objects]}; keys that
    ctx.only excludes come back empty. `spec` is the rifle GunSpec (the same object as rifle_common.SPEC)."""
    return {k: ctx.make(k, f) for k, f in (("pistol_grip", build_pistol_grip),)}
