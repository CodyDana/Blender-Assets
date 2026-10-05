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
from gunlib import mesh as MS
import parts.muzzle_brake_geo as MBG

X0 = 848.82              # rear face (against the front sight's collar, r 10.1 to X 848.78)
R0, RF = 9.6, 9.85       # body flare: rear face -> front (c3 / q34 draw the brake wider at the front); integration
                         # round: the widest point is the raised rim ring LIP_R = 10.1 (key dia 20.2, L4)
LIP_R, LIP_L, LIP_STEP = 10.1, 3.4, 0.35   # rim ring: radius, length behind the face (along X), ramp
COLLAR_R = 8.7           # the front sight's front collar under the knob (front_sight.FRONT_COLLAR_R)
XF, PW = 880.0, 1.5      # flare ends at the lip; convex (the front swells)
RIA, RIB = 7.1, 7.1      # chamber: a plain bore r 7.1 (integration round: c3's flat-floored oval mouth with a visible inner wall)
XIA, XIB = 864.0, 881.0
X_CH = 858.5             # chamber floor (rear wall 848.82-858.5 with the bullet hole; nearer the mouth: c3 shows the floor)
R_BORE = 4.1             # bullet hole through the rear wall (barrel bore 3.81)
A = math.radians(37.5)   # cut angle from vertical (side L2: LEFT trace X 868 at Z 6.8, 880 at Z -9; LS mid fit 39.7)
XC = float(__import__('os').environ.get('MB_XC', '873.098'))   # cut plane at Z 0 (LEFT trace; tuned so the chin's front is X 880.0, key overall length)
N = 32                   # segments round the body
# slot (true right side): side-view position, c3 shape (narrow, rounded ends, widening downward, front edge leaning
# less than the face so the web thickens downward)
SR0, SR_K = 862.0, 0.20  # rear edge X = SR0 - SR_K z
SF0, SF_K = 870.0, 0.55  # front edge X = SF0 - SF_K z (integration round: a long oblong ending close to the rim band,
                         # web to the face plane ~1.6 / 3.2 / 4.5 at Z 7 / 0 / -6; c3, judge tell 'ending almost at the rim')
Z_TOP, Z_BOT = 7.2, -5.9 # c3 back-projected through the brake-only camera: top 7.25, bottom -5.85
SLOT_R = 0.35            # slot outer-edge round (real geometry in the cutter; 0.65 read as a raised filleted lip)
KX0, KX1 = 847.4, 852.4  # detent knob: rear / front end (c3 / q34 top-left of the junction; the side L2 allows
KZ0, KZ1 = 10.6, 11.15   # ~1 px behind the rear face); ends / crown height (side views show nothing above the collar)


def plane_x(z, d=0.0):
    """X of the plane parallel to the cut, d mm behind it (d < 0), at height z."""
    return XC - z * math.tan(A) + d / math.cos(A)


def slot_outline() -> np.ndarray:
    """Side slot in XZ: narrow (c3 / q34: ~0.4 of the mouth's width; 4.7 wide at the top, 6.6 at Z 0, 8.2 low), the
    front edge leaning 25 deg behind the rim with the web thickening downward, the rear edge 11 deg, both measured
    against the reference's own rim in c3 (back-projected through the brake-only camera: web 3.4 / 4.2 / 6.2 and
    width 5.1 / 6.8 / 7.3 at Z 4.8 / 0 / -2.5); a full round top and generously rounded bottom corners (c3: rounded ends)."""
    P = np.array([[SR0 - SR_K * Z_BOT, Z_BOT], [SF0 - SF_K * Z_BOT, Z_BOT],
                  [SF0 - SF_K * Z_TOP, Z_TOP], [SR0 - SR_K * Z_TOP, Z_TOP]], float)
    return G.fillet(P, 1.0, seg=5, radii=[2.2, 2.4, 2.4, 2.4])


SLOT = slot_outline()


def knob():
    """Detent knob at the front sight / brake junction (c3 top-left, q34): a small domed block, the front part higher
    (Z 11.85) than the rear (Z 11.2), X 842.4-850.2, Y +-2.2. Its rear part rides 0.03 above the FSB collar (r 10.1,
    X 842.6-848.78); a stem roots it in the brake body at X 849.1-850.2. Rounded in both views (XZ profile INTERSECT
    YZ profile). Round 1's notched rectangular clip on a separate rear ring is gone (judge: 'one plain collar with a
    different small knob up at top-left')."""
    # integration round: the front sight's front collar is now a narrow ring (r COLLAR_R), so the knob's rear part
    # comes down onto it (0.03 above) instead of riding over a r 10.1 collar
    zb = COLLAR_R + 0.03
    prof = np.array([[KX0, zb], [849.3, zb], [849.3, 9.0], [KX1, 9.0], [KX1, KZ0], [KX1 - 1.3, KZ1],
                     [KX0 + 1.3, KZ1], [KX0, KZ0]], float)
    side = MS.prism(G.fillet(prof, 0.4, seg=4, radii=[0.25, 0, 0, 0, 0.8, 1.6, 1.6, 0.8]), -2.6, 2.6)
    end = MS.prism(G.rounded_rect(-2.0, 2.0, zb - 0.4, KZ1 + 0.3, 1.2, 4), KX0 - 0.5, KX1 + 0.5, "YZ")
    return side, end


GEO = {"A": A, "XC": XC, "X0": X0, "R0": R0, "RF": RF, "XF": XF, "PW": PW, "RIA": RIA, "RIB": RIB, "XIA": XIA, "XIB": XIB, "X_CH": X_CH,
       "R_BORE": R_BORE, "CH": 0.35, "FO0": 0.66, "FO1": 0.8, "TB0": 0.7, "TB1": 2.6,
       "LIP_R": LIP_R, "LIP_L": LIP_L, "LIP_STEP": LIP_STEP, "RO_F0": 0.6, "RO_F1": 2.0, "RI_F": 0.5,
       "K_OUT": 2, "SEG_O": 4, "SEG_I": 3, "K_CH": 1}


def R_at(x):
    return MBG.R_of(x, GEO)


def body():
    """Lofted body with the rounded rim built into every section (muzzle_brake_geo)."""
    return MBG.body_loft(GEO, N)


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
    side, end = knob()
    kn = side.to_object("_knob", coll, offset)
    bl.boolean(kn, end, "INTERSECT", offset=offset)
    bl.boolean(ob, kn, "UNION", offset=offset)
    bpy.data.objects.remove(kn, do_unlink=True)
    slot = MBG.rounded_side_slot(SLOT, lambda x, z: SLOT_R, R_at).to_object("_slot", coll, offset)
    _outward(slot)
    bl.boolean(ob, slot, "DIFFERENCE")
    bpy.data.objects.remove(slot, do_unlink=True)
    bl.clean(ob)
    bl.finish(ob)
    bl.weighted_normals(ob)
    ob["gun_part"] = json.dumps({"bone": "muzzle_device", "class": "M-chamfer-front", "slot": "M_AR01_Metal",
                                 "joint": {"type": "fixed", "parent": "barrel"}, "spec_id": "muzzle_brake",
                                 "recipe": [["loft bullnose rim (Bezier) outer share, chin t_body", GEO["FO0"], GEO["TB1"]],
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
