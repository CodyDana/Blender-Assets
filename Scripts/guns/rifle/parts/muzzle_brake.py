"""Detail part MUZZLE BRAKE: slant-cut brake on the barrel's muzzle thread (bone "muzzle_device").

Owns the object: muzzle_brake. Authority close-ups: c3 FRONT SIGHT AND MUZZLE (SIDE) and the 3/4 view; X/Z from the
LEFT trace (spec side_profile_M; the per-part L2 gate) and the two side panels.
Interfaces: barrel end X 848.78, rear face X 848.82 against the front sight's collar (r 10.1 to X 848.78).

Detail round 2 (2026-10-05; gates/detail_muzzle_brake_r2.json), fixing the round-1 blind judge's design tells:
- no separate threaded rear ring / hard step and no raised bead: one body from the rear face (r 10.0, chamfer 0.35)
  that FLARES convexly to r 10.5 at the lip (c3 / q34: 'wider at the front than at the collar', 'the front swells');
- the slant face (37.5 deg from vertical, X 873.2 at Z 0: the LEFT trace through the face top X 868 @ Z 6.8 and the
  chin X 880 @ Z -9) is a BULLNOSE rim: the outer and inner rounds (quadratic Bezier, built into every loft section by
  muzzle_brake_geo) meet on the face with no flat band, so it reads as a thick, even rolled lip with a crown
  highlight that blends into the body through a soft roll (judge: 'thick, even raised lip', 'softer beveled roll');
- the chamber is a cone (r 6.7 to X 864 -> r 7.5 at X 881): wall 3.4 at the top of the face, 3.0 at the chin, so the
  opening is narrower at the top-rear (c3's teardrop) and the rim is thick;
- the chin is one long round (tangent 5.5 along the body, 80 % of the face): level with the body, no pointed lip and
  no flat (its front lands at X 879.9 @ Z -9.0, the LEFT trace's lip);
- ONE narrow slot through the RIGHT wall (c3 / q34: ~0.4 of the mouth's width): rear edge X 862.3 - 0.20 Z, front edge
  X 868.9 - 0.47 Z (web to the face plane 2.2 / 4.3 / 6.1 at Z 7 / 0 / -6: thick, thickening downward), Z -5.9..+7.2,
  full round top and rounded bottom corners, outer edge rounded 0.65 by the cutter (real geometry). RIGHT side only
  (round 1 decision, spec_proposal.json);
- a small domed detent knob at the junction (X 847.4-852.4, crown Z 11.15, Y +-2.0), riding 0.03 above the FSB
  collar and rooted in the brake by a stem; round 1's notched rectangular clip is gone ('a different small knob up
  at top-left'). The side views show nothing above the collar there, so it stays low and within ~1 px of the rear
  face (L2).
Detail round 2b (2026-10-05, re-run of round 2 on the integrated build; gates/detail_muzzle_brake_r2.json):
- the side SLOT is a closed spline through c3's own slot edges, read off a luminance table of the panel and
  back-projected onto the body through the brake-only camera (muzzle_brake_trace.py): a narrow round top (Z 6.8), an
  upright rear edge running into a long rounded diagonal down-forward, a flat floor at Z -7.7 (the cutter's flat bottom
  = c3's lit ledge), and a front edge leaning with the rim (web ~1.4 mm at the top, thickening below Z -2); slot
  outline IoU vs the trace 0.727 -> 0.906. The cutter rings follow the 32-gon body (muzzle_brake_geo.facet_y), so the
  0.4 mm outer round no longer tears on the facets;
- no raised rim ring (its seam ran round the body and the slot notched it): the body is a straight cylinder r 10.0 ->
  10.1 (c3: bottom line parallel to the top), the face a flat band with crisp small rounds (outer 0.5 -> 1.2 mm top ->
  chin, inner 0.35), chamber r 7.1 (a 3 mm band, as wide as c3 draws it; r 8.1 drew a thin pipe);
- a rear SHANK of the collar's radius (r 8.7, X 848.82-853.0, hairline joint with the FSB collar) ending in a groove and
  a clear step up to the body at X 853 (c3: sleeve -> narrow collar -> dark groove -> step; c3 draws the body only
  ~13-14.5 mm long at the top, so the step moved forward instead of the brake shrinking: rear face, chin and diameter
  are unchanged for L2 / L4);
- the detent BLOCK straddles the junction (X 847.2-853.4, top 11.0 / rear 10.45, Y +-2.3; its rear rides 0.03 above the
  FSB collar, its front is rooted in the shank) with a transverse pin end on each side (an annular groove round a flush
  head: c3's dark ring round a bright dot) in place of the rounded tab; it ends before X 853.5 so L4's knob exclusion
  holds; it cannot reach c3's X ~843.6 rear end (the side views show nothing above the collar there: L2 max 2 px);
- XC 873.098 -> 872.786 keeps the chin's front at X 880.0 with the crisper rounds (L4 length 31.18).
The c3 part camera is re-solved on the BRAKE ONLY (muzzle_brake_dev.py solve): c3 draws the brake ~14 % larger
relative to the FSB than the side views, and ~35 % shorter relative to its height; the side views keep the
length (L2), which is the remaining proportion difference in c3 (q34 draws it longer, not shorter).
Iteration loop: muzzle_brake_dev.py (private copies; c3 / q34 crops in the ROUGH LOOK, part-ROI IoU, L2, G5 gaps).
"""
from __future__ import annotations

import math
import time

import numpy as np

from gunlib import geo2d as G
from gunlib import lod as LOD
from gunlib import mesh as MS
import parts.muzzle_brake_geo as MBG

X0 = 848.82              # rear face (against the front sight's collar, r 8.7 to X 848.78)
R0, RF = 9.7, 9.7        # DETAIL FIX (user checklist 3): a straight body r 9.7 behind a heavy rounded RIM BAND r 10.1
                         # (LIP_*; the key dia 20.2 is the band). Was: body: rear step -> rim (round 2b: c3 draws the body as a straight cylinder, its bottom line parallel
                         # to its top, and a clear step up from the collar; the key radius 10.1 (L4 key dia 20.2) at XF;
                         # no raised rim ring, so no seam line runs round the body behind the rim)
COLLAR_R = 8.7           # the front sight's front collar under the detent block (front_sight.FRONT_COLLAR_R)
# rear shank (round 2b): c3 draws sleeve -> narrow collar -> a grooved STEP up to the body, the body only ~14.5 mm long
# at the top (rear step -> face top); our rear face stays at X 848.82 (interface), so the brake's first 2.2 mm are a
# shank of the collar's radius and the body steps up at XS (c3: the dark groove line at the foot of the step)
XS, RS, CS_R = 853.0, 8.7, 0.06          # step X, shank radius, shank rear chamfer (a hairline joint with the collar)
GW, GD = 0.75, 0.32                      # groove width / depth at the foot of the step
XF, PW = 867.0, 1.0      # the last 0.1 mm of swell ends at the face top
RIA, RIB = 6.7, 6.7      # DETAIL FIX: a straight flat-floored chamber (no cone), r 6.7: the face band 3.4 incl. the rounds
                         # and the inner wall visible down to the flat floor. Was: chamber (integration r2b: 7.1 -> 6.4, the r2b judge read a thin uniform wall; c3 draws a thick flat annular face): a plain bore, was r 7.1 (c3: the rim band reads ~6-7 panel px wide at the top-left and ~6 at
                         # the right; r 8.1 (round 2b trial) drew a thin-walled pipe)
XIA, XIB = 864.0, 881.0
X_CH = 857.4             # chamber floor (detail fix 858.5 -> 857.4: clear of the big side port's rear edge) (rear wall 848.82-858.5 with the bullet hole; nearer the mouth: c3 shows the floor)
R_BORE = 4.1             # bullet hole through the rear wall (barrel bore 3.81)
A = math.radians(37.5)   # cut angle from vertical (side L2: LEFT trace X 868 at Z 6.8, 880 at Z -9; LS mid fit 39.7)
XC = float(__import__('os').environ.get('MB_XC', '872.943'))   # cut plane at Z 0 (LEFT trace; tuned so the brake is the key length 31.2; detail fix rim band + heavier rounds: 872.786 -> 872.943)
N = 32                   # segments round the body
SLOT_R = 0.6             # port outer-edge round (real geometry in the cutter; detail fix 0.4 -> 0.6)
# DETAIL FIX (user checklist 3): heavy rounded rim band at the mouth and a BIG OVAL side port right behind it
LIP_R, LIP_L, LIP_STEP, LIP_SEG = 10.1, 3.0, 0.9, 3     # band radius, band length behind the face, rounded step
PORT_A, PORT_B, PORT_WEB = 6.6, 3.0, 1.2                # port semi-axes (along / across the face slant), web to the band
# detent block at the junction (c3: a dark block straddling the collar / brake step, 2/3 of it over the collar, its top
# ~1 mm above the brake, a transverse pin end showing on its side as a dark ring round a bright head)
KX0, KX1 = 847.2, 853.4  # rear / front end (c3: step - 5.2 .. step + 3.0; L2 allows little behind X 848.8; L4 excludes the knob only for X < 853.5)
KZ1, KZR = 11.0, 10.45   # top at the front / rear end (the side views show nothing above the collar there: L2)
KY = 2.3                 # half width
PIN_X, PIN_Z, PIN_R = 850.2, 9.95, 0.72   # transverse pin (head recessed in a counterbore r PIN_R + 0.38)


def plane_x(z, d=0.0):
    """X of the plane parallel to the cut, d mm behind it (d < 0), at height z."""
    return XC - z * math.tan(A) + d / math.cos(A)


# c3 slot, back-projected through the brake-only camera onto the body (muzzle_brake_trace.py back; X, Z mm): the rear
# edge nearly upright (X 862.65 @ Z 6.2 -> 863.55 @ -1.2), then a long diagonal down-forward (864.65 @ -4.25, 865.6 @
# -5.2, 866.4 @ -6.3, 867.2 @ -7.2); a flat bottom at Z -7.7 (X 867-870.4: the cutter's flat floor, c3's lit ledge);
# the front edge upright low (871.25 @ -5.45, 871.2 @ -3.6) then leaning with the rim (870.15 @ 0.2, 868.1 @ 3.8,
# 866.6 @ 6.1) so the web to the rim's back edge is ~1.4 mm at the top and thickens below Z -2; a narrow round top
# (Z 6.8, X 862.7-865.8).
SLOT_TRACE = [  # rear edge top -> bottom
    (862.65, 6.22), (862.7, 5.3), (862.95, 3.78), (863.1, 2.18), (863.3, 0.51), (863.55, -1.18), (863.95, -2.85),
    (864.65, -4.25), (865.6, -5.25), (866.4, -6.3), (867.15, -7.2),
    # flat bottom (the cutter's floor)
    (868.05, -7.68), (869.2, -7.7), (870.35, -7.45),
    # front edge bottom -> top
    (871.15, -5.6), (871.2, -3.6), (870.9, -2.19), (870.55, -0.85), (870.15, 0.17), (869.7, 1.1), (869.2, 2.02),
    (868.65, 2.92), (868.1, 3.8), (867.65, 4.71), (867.25, 5.35), (866.6, 6.1), (865.8, 6.62),
    # round top
    (865.0, 6.8), (864.1, 6.76), (863.25, 6.6)]


def slot_outline() -> np.ndarray:
    """Side slot in XZ: a closed spline through the c3 trace (SLOT_TRACE), evenly resampled."""
    return MBG.periodic_spline(G.smooth(np.array(SLOT_TRACE, float), 0.8, 1), 40)


SLOT_R2B = slot_outline()


def port_outline(n=36) -> np.ndarray:
    """DETAIL FIX: the big oval side port, its long axis parallel to the slant face, its front edge PORT_WEB behind the
    rim band's rear edge (XZ, CCW)."""
    u = np.array([-math.sin(A), math.cos(A)])            # along the face slant (up)
    v = np.array([math.cos(A), math.sin(A)])             # toward the face
    c = np.array([XC - LIP_L - LIP_STEP - (PORT_WEB + PORT_B) / math.cos(A), 0.0])
    t = np.linspace(0.0, 2 * math.pi, n, endpoint=False)
    return G.ccw(c + np.outer(PORT_A * np.cos(t), u) + np.outer(PORT_B * np.sin(t), v))


SLOT = port_outline()


def knob():
    """Detent block at the front sight / brake junction (c3 top-left: a dark block straddling the step, X 845.6-851.6,
    top Z 11.1, Y +-2.3): side profile (XZ) with rounded top corners and a slightly domed top INTERSECT an end profile
    (YZ) with rounded top corners. Its rear 3.2 mm ride 0.03 above the FSB collar (r 8.7); the front part is rooted in
    the brake's rear wall. Returns (side, end) prisms; the pin is cut / added in build_object."""
    zb = COLLAR_R + 0.03
    zr = RS - 0.4                     # rooted in our own shank / body (|Y| <= KY: the shank top is above RS - 0.32)
    prof = np.array([[KX0, zb], [848.86, zb], [848.86, zr], [KX1, zr], [KX1, KZ1 - 0.25], [KX1 - 2.0, KZ1],
                     [KX0, KZR]], float)
    side = MS.prism(G.fillet(prof, 0.4, seg=4, radii=[0.2, 0.0, 0.0, 0.0, 1.0, 1.5, 0.9]), -KY - 0.5, KY + 0.5)
    end = MS.prism(G.rounded_rect(-KY, KY, zb - 0.6, KZ1 + 0.4, 0.9, 4), KX0 - 0.5, KX1 + 0.5, "YZ")
    return side, end


def pin_parts():
    """Transverse detent pin end on each side of the block: an annular groove (r PIN_R..PIN_R + 0.38, 0.45 deep) round
    a flush pin head (c3: a dark ring round a bright head). Returns the groove cutters."""
    return [MS.tube((PIN_X, s * (KY + 1.0), PIN_Z), (PIN_X, s * (KY - 0.45), PIN_Z), PIN_R, PIN_R + 0.38, 12)
            for s in (-1, 1)]


GEO = {"A": A, "XC": XC, "X0": X0, "R0": R0, "RF": RF, "XF": XF, "PW": PW, "RIA": RIA, "RIB": RIB, "XIA": XIA, "XIB": XIB, "X_CH": X_CH,
       "R_BORE": R_BORE, "CH": 0.35, "FO0": 0.66, "FO1": 0.8, "TB0": 1.0, "TB1": 2.0,
       "FLAT": True, "RO_F0": 1.0, "RO_F1": 1.6, "RI_F": 0.6,
       "LIP_R": LIP_R, "LIP_L": LIP_L, "LIP_STEP": LIP_STEP, "LIP_SEG": LIP_SEG,
       "XS": XS, "RS": RS, "CS": CS_R, "GW": GW, "GD": GD,
       "K_OUT": 1, "SEG_O": 4, "SEG_I": 3, "K_CH": 1}


def R_at(x):
    return MBG.R_of(x, GEO)


def body():
    """Lofted body with the rounded rim built into every section (muzzle_brake_geo)."""
    P = dict(GEO)
    if LOD.LEVEL:                                   # LOD: fewer sections round the body and fewer points per round
        P.update({k: LOD.count(int(GEO[k]), 1) for k in ("SEG_O", "SEG_I", "LIP_SEG") if k in GEO})
    return MBG.body_loft(P, LOD.ring(N))


def _outward(ob):
    """Make sure a closed cutter's normals point outward (signed volume > 0)."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    if bm.calc_volume(signed=True) < 0:
        bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
        bm.to_mesh(ob.data)
        ob.data.update()
    bm.free()


def build_object(coll, offset):
    """Custom build (explicit steps, no bevel modifier): lofted flared body with the rim rounds in its sections, the
    detent knob unioned, the right slot cut by a cutter whose outer edge round is real geometry; finish, weighted
    normals, the gun_part record."""
    import json
    import bpy
    from gunlib import bl
    t0 = time.time()
    ob = body().to_object("muzzle_brake", coll, offset, smooth_deg=35.0)
    # DETAIL FIX: no detent block on the brake (the detent is a small boss on the front sight base: front_sight.DET_*)
    slot = MBG.rounded_side_slot(SLOT, lambda x, z: SLOT_R, R_at, n_facets=LOD.ring(N),
                                   step=LOD.step(1.2), phis=(30.0, 60.0, 90.0) if LOD.LEVEL < 2 else (90.0,)).to_object("_slot", coll, offset)
    _outward(slot)
    bl.boolean(ob, slot, "DIFFERENCE")
    bpy.data.objects.remove(slot, do_unlink=True)
    bl.clean(ob)
    bl.finish(ob)
    bl.weighted_normals(ob)
    ob["gun_part"] = json.dumps({"bone": "muzzle_device", "class": "M-chamfer-front", "slot": "M_AR01_Metal",
                                 "joint": {"type": "fixed", "parent": "barrel"}, "spec_id": "muzzle_brake",
                                 "recipe": [["loft flat face band, outer round top / chin", GEO["RO_F0"], GEO["RO_F1"]],
                                            ["slot outer round (cutter)", SLOT_R]]})
    rep = bl.manifold_report(ob)
    rep["seconds"] = round(time.time() - t0, 2)
    print("[muzzle_brake]", json.dumps(rep))
    return ob


# ======================================================================================== module interface
OBJECTS = ('muzzle_brake',)            # registry keys built here (rifle_parts.ORDER)
CLOSEUPS = ('c3', 'q34')          # sheet panels that are this part's shape authority (rifle_detail.py)


def build(spec, ctx):
    """Build this module's objects into ctx (gunlib.parts.BuildCtx). Returns {registry key: [objects]}; keys that
    ctx.only excludes come back empty. `spec` is the rifle GunSpec (the same object as rifle_common.SPEC)."""
    return {k: ctx.make(k, f) for k, f in (("muzzle_brake", build_object),)}
