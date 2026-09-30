"""STONE KIT track (9): the STAIR PATH kit (granite flights, landings, rubble cheeks, timber handrails, path lanterns).

Look: References/Dojo/dojo_landscape_ref.png (the stone stair path climbing the cliff at the lower left: granite block
steps with rounded, worn nosings, flagstone landings edged with blocks, low stepped stone cheeks, dark round timber
posts with a top and a mid rail, small square timber lanterns with warm panes and a dark hipped hood). The stone
language is the dojo's own: kit 1's footing (pillow-faced rubble under a dressed course, kit1_geo.pillow_face /
rough_block, material M_DK_FootingStone) and the gate apron's granite, all on the shared material library.

GRID (every piece snaps; heights in 0.5 m steps, turns in 90 deg steps; details in kit_catalog.json):
  riser R = 1/6 m (0.1667), tread T = 1/3 m (0.3333): pitch 1:2 (26.57 deg), 3 risers per 0.5 m rise per 1.0 m run
  Flight_W{120,180}_R{050,100,200}   pivot = the foot of the first riser on the flight's centre line at the LOWER level;
                                    out-snap (0, run, rise), run = 2 x rise; the top tread is the first 1/3 m of the
                                    upper level (flush with the landing that follows)
  Landing{,L,SB}_W{120,180}          pivot = the centre of the paved top (z = 0); edge snaps N / S / E / W
                                    L  = a turn landing: upstand curbs on the two OUTSIDE edges (+Y, -X); arrive -Y,
                                         leave +X (right turn) or, walked the other way, arrive +X and leave -Y
                                    SB = a switchback: 2W + 0.40 wide (the 0.40 divider = one cheek wall), arrive at
                                         x = -(W + 0.4) / 2 on the -Y edge, leave at x = +(W + 0.4) / 2 back along -Y
  Cheek_R{050,100,200} / Cheek_L{120,180} / CheekCorner   0.40 m rubble cheek walls (both faces laid), pivot on the
                                    wall's centre line at its start, level 0; stepped tops 0.30 above the highest tread
                                    of each 1 m (the flight's 3 treads); place at x = +-(W / 2 + 0.20) beside a flight
  Rail_Slope_R{050,100,200} / Rail_Flat_L{120,150,180} / Rail_Flat_T{120,180} / Rail_EndPost / Rail_CornerPost
                                    pivot = the post base on the rail line; a span carries its START post only (the
                                    next span's post, an end post or a corner post closes it); place a flight's rail
                                    at (+-(W / 2 - 1/6), -1/6, 0) in flight space: posts then stand mid-tread on the
                                    flight, span W exactly over a W landing, and W - 1/3 (the T spans) across the
                                    outside of a turn
  Lantern_Timber (1.33 m) / Lantern_Stone (0.90 m, the courtyard short lantern at 0.75 scale; a kit extra, not in
                                    the reference path)   pivot base centre

f1 FIX ROUND (judge 6/10): the kit granite family (sk_shared.KIT_MATS: pale grey-beige, per-stone tone, light tops,
dark undersides, moss in joints / on ledges); treads light and smooth, risers dark and rough, a 4.0 cm riser set-back
under a rounded worn nosing (measured overhang 2-3 cm), 1-2 slabs a step; flight sides in wall-stone polygon courses;
flush Voronoi flag landings with no curbs; LOW cheeks (+0.15 over the treads); round poles through the posts, slopes
carry both end posts, flats are poles only; a narrow-shaft lantern on splayed feet with a steep pointed roof.

COLLISION: flights = one convex ramp through the tread MIDPOINTS (26.57 deg) with an 8 cm lip at the foot; landings =
one flat box (+ curb boxes); cheeks = one box per 1 m segment (walkable flat tops); rails / lanterns = thin uprights.
GASP (WorkFiles/dojo/build/GASP_TRAVERSAL.md): MaxStepHeight 45 cm, walkable 44.77 deg -> risers 16.7 cm, ramp 26.6 deg.

f2 FIX ROUND (the owner's reading of the reference; f1 went the wrong way): steps of 3-5 SHORT squared blocks per
tread with staggered end joints (like round 0), lighter walked tread tops (M_DKT_StepGranite), darker rougher risers
(M_DKT_StepRiser), a small worn nosing (~1 cm), calmer surface noise; flush, large, near-rectangular flag landings in
tight joints at path level; a separate low KERB of squared blocks (Stair_Kerb_*); flight sides, landing sides and cheek
bases in the wall's ROUNDED pillow stones (sk_shared.lay_rounded); a single-course low cheek variant (Cheek_Low_*) with
moss where the cheek meets the soil; ROUND posts with rounded tops carrying SQUARED rails housed into the posts, in a
darker weathered timber (M_DKT_TimberWeathered); Lantern_Timber keeps its f1 form with warmer amber panes
(M_DKT_GlassAmberWarm), the darker weathered body and a charcoal hood (M_DKT_HoodCharcoal: no rust).

Run:  blender -b --factory-startup --python Scripts/dojo/stonekit/build_stairs.py -- [--no-export] [--only a,b]
Out:  Exports/DojoKit/StoneKit/SM_DKT_Stair_*.fbx, WorkFiles/dojo/build/stonekit/{kit_catalog.json (track "stairs"),
      stairs/qa_report.json, stairs/export_report.json, stairs/measure.json, stairs/StairKit_build.blend},
      Assets/Dojo/DojoStoneKit.blend (collection StoneKit_Stairs, merged under a file lock)
"""
import json
import math
import random
import sys
import time
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sk_shared as S  # noqa: E402
from sk_shared import G, Piece, clamp01, djm  # noqa: E402
from pipeline.lock import assert_owner  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
TRACK = "stairs"
PREFIX = "SM_DKT_Stair_"
OUT = S.WORK / "stairs"
BUILD_BLEND = OUT / "StairKit_build.blend"
COLL = "StoneKit_Stairs"

# ------------------------------------------------------------------------------------------------ the grid
R = 1.0 / 6.0            # riser 0.1667 (GASP: <= 0.45; brief 0.15-0.18)
T = 1.0 / 3.0            # tread 0.3333 (brief 0.30-0.40); pitch atan(R / T) = 26.57 deg (walkable <= 44.77)
NOSE = 0.022             # each step stone's nosing stands this far proud of its riser line
TUCK = 0.07              # and runs this far back under the next stone
SINK = 0.06              # and this far down into the stone below
CORE_BOT = -0.35         # every stone piece runs 0.35 m below its walking level (buried in the terrain)
WIDTHS = {"W120": 1.2, "W180": 1.8}
RISERS = {"R050": 3, "R100": 6, "R200": 12}
TW = 0.40                # cheek wall thickness (= the switchback divider)
CH = 0.30                # cheek top above the highest tread of its 1 m segment
COPE_H = 0.20            # the cheek's dressed coping course
KW = 0.24                # landing kerb depth
UP_H = 0.20              # turn / switchback upstand curb height above the paving
RAIL_IN = T / 2          # the rail line stands 1/6 m in from a flight's / landing's edge: = the posts' -T/2 set-back,
                         # so a rail turning a landing corner meets the grid exactly (outside-turn span W - 1/3)
PR = 0.048               # post radius (f3: dia 9.6 cm, slimmer like the reference's round posts; f2 11 cm)
POST_H = 0.86            # post top above its base (f1: 0.94 -> 0.86, the sheet's posts are shorter)
TOP_Z, MID_Z = 0.76, 0.38    # rail centre lines above the rail base line (the tread-midpoint line)

# f1 (judge 6/10, delta 2 / 3): the kit-wide granite family (sk_shared.KIT_MATS): treads and flags lighter and smoother
# (M_DKT_StepGranite), risers and step ends darker and rougher (M_DKT_StepRiser), cheeks and the flight sides in the
# wall stone (M_DKT_WallGranite), the joint core M_DKT_JointDark
SG = "M_DKT_StepGranite"
SR = "M_DKT_StepRiser"
SG_TINT = tuple(S.KIT_MATS[SG]["tint"])
SG_FLAT = S.KIT_MATS[SG]["flat"]
SG_MOSS = S.KIT_MOSS
SG_NRM = S.KIT_MATS[SG]["normal"]
FS = "M_DKT_WallGranite"             # cheeks / flight sides: the wall's stone (was kit 1's M_DK_FootingStone)
JE = "M_DKT_JointDark"               # the joint core (was kit 1's M_DK_JointEarth)
RB = "M_DJ_GraniteRubble"
TD, TDE = "M_DKT_TimberWeathered", "M_DKT_TimberWeatheredEnd"     # f2: darker weathered timber (library TimberDark x tint)
IR, LG = "M_DKT_HoodCharcoal", "M_DKT_GlassAmberWarm"              # f2: charcoal hood (no rust), warmer amber panes

K1 = S.load_builder(S.KIT1_BUILDER, "dojo_build_kit1")        # kit 1, imported (its main() not run)


# ------------------------------------------------------------------------------------------------ moss passes
def _wear(obj):
    return obj.data.color_attributes["Wear"]


def step_moss(hw):
    """The sheet's steps: clean worn centres, olive moss creeping in from the outer ends, into the joints and along
    the back of each tread / the foot of each riser, patchy."""
    def f(obj, slot):
        me = obj.data
        ca = _wear(obj)
        n_f = 0
        for poly in me.polygons:
            if poly.material_index != slot:
                continue
            n_f += 1
            nz, ny = poly.normal.z, poly.normal.y
            for li in poly.loop_indices:
                co = me.vertices[me.loops[li].vertex_index].co
                col = ca.data[li].color
                patch = S.moss_noise(co, 6.0)
                fine = S.moss_noise(co, 17.0, (1.7, 2.9, 5.3))
                m = clamp01((0.62 * patch + 0.38 * fine - 0.38) * 3.0)
                edge = clamp01((abs(co.x) - (hw - 0.24)) / 0.20)
                fy = ((co.y + NOSE) % T) / T
                back = clamp01((fy - 0.70) / 0.22) if nz > 0.5 else 0.0
                foot = clamp01(1.0 - ((co.z + 1e-4) % R) / 0.05) if ny < -0.5 else 0.0
                joint = clamp01((col[0] - 0.45) * 2.2)
                a = m * clamp01(0.9 * edge + 0.45 * back + 0.30 * foot + 0.45 * joint)   # f2: lighter moss
                ca.data[li].color = (col[0], col[1], col[2], clamp01(a) * 0.80)
        me.update()
        return n_f
    return f


def paving_moss(obj, slot):
    """Landings: moss in the joints and round the kerb's outer foot, the paving centre clean."""
    me = obj.data
    ca = _wear(obj)
    n_f = 0
    for poly in me.polygons:
        if poly.material_index != slot:
            continue
        n_f += 1
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            col = ca.data[li].color
            m = clamp01((0.62 * S.moss_noise(co, 6.0) + 0.38 * S.moss_noise(co, 17.0, (1.7, 2.9, 5.3)) - 0.36) * 3.0)
            joint = clamp01((col[0] - 0.40) * 2.2)
            low = clamp01((-0.02 - co.z) / 0.20)
            a = m * clamp01(0.95 * joint + 0.75 * low)
            ca.data[li].color = (col[0], col[1], col[2], clamp01(a) * 0.9)
    me.update()
    return n_f


def stone_moss(low_z=None):
    """f1: wall-granite moss (cheeks, flight sides): in the joints (occluded rims, Wear R) and on upward ledges,
    patchy; never a tint across whole faces."""
    def f(obj, slot):
        me = obj.data
        ca = _wear(obj)
        n_f = 0
        zs = [v.co.z for v in me.vertices]
        z0 = min(zs) if low_z is None else low_z
        for poly in me.polygons:
            if poly.material_index != slot:
                continue
            n_f += 1
            nz = poly.normal.z
            for li in poly.loop_indices:
                co = me.vertices[me.loops[li].vertex_index].co
                col = ca.data[li].color
                patch = S.moss_noise(co, 5.0)
                m = clamp01((0.65 * patch + 0.35 * S.moss_noise(co, 15.0, (1.7, 2.9, 5.3)) - 0.42) * 3.0)
                low = clamp01(1.0 - (co.z - z0) / 0.8)
                joint = clamp01((col[0] - 0.38) * 2.6)
                ledge = clamp01((nz - 0.5) * 2.5)
                a = joint * (0.35 + 0.45 * low) * (0.35 + 0.65 * patch) + ledge * m * 0.55 + 0.2 * low * m
                ca.data[li].color = (col[0], col[1], col[2], clamp01(a) * 0.88)
        me.update()
        return n_f
    return f


def core_moss(obj, slot):
    me = obj.data
    ca = _wear(obj)
    n_f = 0
    for poly in me.polygons:
        if poly.material_index != slot:
            continue
        n_f += 1
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            col = ca.data[li].color
            ca.data[li].color = (1.0, 0.0, 0.0, 0.16 * clamp01((S.moss_noise(co, 3.3) - 0.50) * 2.2))  # f2: dark
    me.update()
    return n_f


def footing_moss(top):
    def f(obj, slot):
        return K1.moss_alpha(obj, slot, top)
    return f


# ------------------------------------------------------------------------------------------------ stone helpers
OVER = 0.014             # f2: a SMALL worn nosing: the riser face sits 1.4 cm behind the nosing line (the rounded
                         # arris takes about half of it: a measured overhang of ~1 cm; f1's 4 cm shelf is gone)
LIP = 0.035              # the nosing lip's thickness (the riser face is set back below it)


def step_cuts(W, i, rng):
    """f2 (the owner's reading, like round 0): 3-5 SHORT squared blocks per tread with STAGGERED end joints: n = 3
    blocks on W 1.2, 4 on W 1.8 (bw = W / n, 0.40-0.45 m); even steps cut at the block grid, odd steps half a block
    over (n - 1 full blocks + two half-length end blocks = n + 1 stones), every cut jittered +-12 % of a block, so no
    joint lines up with the one below."""
    # f3 (judge delta 7, checked against the reference's lower flight: small near-cubic setts about 0.30-0.40 m long,
    # within the owner's 3-5 blocks a tread): even steps n blocks (W 1.2: 4 x 0.30, W 1.8: 5 x 0.36), odd steps n - 1
    # blocks (0.40 / 0.45), so the end joints never line up with the step below; every cut jittered +-10 %
    hw = W / 2
    n = 4 if W < 1.5 else 5
    m = n if i % 2 == 0 else n - 1
    bw = W / m
    cuts = [-hw + k * bw + rng.uniform(-0.10, 0.10) * bw for k in range(1, m)]
    xs = [-hw] + sorted(cuts) + [hw]
    out = [xs[0]]
    for x in xs[1:-1]:
        if x - out[-1] >= 0.18 and hw - x >= 0.18:
            out.append(x)
    return out + [hw]


def worn_block(g, x0, x1, y0, y1, ztop, h, seed, rng, mat=SG, wear_x=0.0, r_round=0.022, dip=0.006, chips=True,
               riser=SR, over=OVER, slope=None):
    """One granite step / kerb stone: kit1_geo.rough_block (rounded, smooth-shaded), its front on -Y, then a worn,
    slightly uneven top: a foot-traffic hollow round wear_x deepest near the nosing, a per-stone tilt and height jitter,
    0-2 chips out of the nosing arris. f1: the riser face is set back `over` below a LIP-thick nosing (overhang shadow
    line), the upward faces take `mat` (the light, smooth tread granite) and every other face `riser` (darker,
    rougher); slope (dz/dy): the underside is sheared to the flight pitch so all the stones' bottoms of a flight lie on
    one line (the flight's side courses meet it)."""
    hx, hy, hz = (x1 - x0) / 2 - 0.004, (y1 - y0) / 2, h / 2           # f3: 0.8 cm end joints (f2 1.2: dark slots)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    nx = max(8, int(round((x1 - x0) / 0.045)))
    ny = max(8, int(round((y1 - y0) / 0.04)))
    nz_ = 6 if h > 0.3 else 4
    v0 = len(g.v)
    f0 = len(g.f)
    G.rough_block(g, (cx, cy, ztop - hz), ((1, 0, 0), (0, 1, 0), (0, 0, 1)), (hx, hy, hz), r_round, seed, mat,
                  bulge=0.003, rough=0.0012, fine=0.0004, n=(nx, ny, nz_))           # f2: calmer surface noise
    tx, ty, dz = rng.uniform(-0.004, 0.004), rng.uniform(-0.003, 0.003), rng.uniform(-0.003, 0.003)
    chip = []
    if chips:
        for _ in range(rng.choice((0, 1, 1, 2))):
            if x1 - x0 > 0.16:
                chip.append((rng.uniform(x0 + 0.06, x1 - 0.06), rng.uniform(0.004, 0.009), rng.uniform(0.03, 0.05)))
    for i in range(v0, len(g.v)):
        v = g.v[i]
        if v.z > ztop - 0.012:              # worn smooth: the top keeps 20 % of rough_block's relief
            v = Vector((v.x, v.y, ztop + (v.z - ztop) * 0.20))
        if over > 0.0 and v.y < y0 + 0.036:  # the riser face set back below the nosing lip
            wy = clamp01((y0 + 0.036 - v.y) / 0.02)
            wz = clamp01(((ztop - LIP) - v.z) / 0.022)
            v = v + Vector((0.0, over * wy * (wz * wz * (3 - 2 * wz)), 0.0))
        if slope is not None and v.z < ztop - 0.10:     # the underside on the pitch line
            fz = clamp01(((ztop - 0.10) - v.z) / max(h - 0.10, 1e-3))
            v = v + Vector((0.0, 0.0, fz * (v.y - (y0 - 0.0)) * slope))
        k = clamp01((v.z - (ztop - 0.035)) / 0.035)
        if k <= 0.0:
            g.v[i] = v
            continue
        near = clamp01(1.0 - (v.y - y0) / max(2 * hy, 1e-3))
        hollow = dip * math.exp(-((v.x - wear_x) / 0.30) ** 2) * (0.35 + 0.65 * near)
        dzz = tx * (v.x - cx) / max(hx, 1e-3) + ty * (v.y - cy) / max(hy, 1e-3) + dz - hollow
        off = Vector((0.0, 0.0, dzz * k))
        for (xc, depth, wid) in chip:
            if v.y < y0 + 0.05:
                w_ = math.exp(-((v.x - xc) / wid) ** 2) * clamp01(1.0 - (v.y - y0) / 0.05) * k
                off += Vector((0.0, 0.7, -0.7)) * (depth * w_)
        g.v[i] = v + off
    if riser and riser != mat:              # tread (upward faces) vs riser / ends / underside
        for fi in range(f0, len(g.f)):
            f = g.f[fi]
            a_, b_, c_ = g.v[f[0]], g.v[f[1]], g.v[f[2]]
            nrm = (b_ - a_).cross(c_ - a_)
            if len(f) > 3:
                nrm = nrm + (c_ - a_).cross(g.v[f[3]] - a_)
            if nrm.length > 1e-12 and nrm.normalized().z < 0.55:
                g.fm[fi] = riser
    return g


def split_points(a0, a1, lo, hi, rng):
    """Interior boundaries splitting [a0, a1] into lengths about lo..hi (kit 1's _partition)."""
    return K1._partition(a0, a1, lo, hi, rng)


# ------------------------------------------------------------------------------------------------ flights
STEP_H = 0.40            # f1: a step slab is 0.40 deep at its nosing (its underside sheared to the pitch)


def under_line():
    """The step slabs' common underside on a flight: z = R - STEP_H + (y + NOSE) R / T."""
    return lambda y: R - STEP_H + (y + NOSE) * R / T


def side_stone(g, F, poly, rng, seed):
    """f2: the wall's rounded pillow stone (sk_shared.pillow_stone), a little flatter on these low faces."""
    return S.pillow_stone(g, F, poly, rng, seed, FS, depth=0.14, scale=0.8)


def side_courses(g, hw, run, ul, seed, x_face=0.022):
    """Both side faces of a flight: dressed wall-granite polygon stones (sk_shared.lay_courses) from CORE_BOT up to
    the slabs' underside (clipped 12 mm under it), faces 2.2 cm inside the step ends."""
    kp = R / T
    c0 = R - STEP_H + NOSE * kp - 0.012
    z_hi = ul(run) + 0.05
    rng = random.Random(seed)
    s = -CORE_BOT
    cs = [s]
    while s > -z_hi:
        s -= rng.uniform(0.28, 0.42)
        cs.append(s)
    cs = sorted(cs)
    n = 0
    Fp = S.PlaneFace((hw - x_face, 0, 0), (0, 1, 0), (1, 0, 0))
    n += S.lay_rounded(g, Fp, cs, cs[0], -CORE_BOT, lambda k, sa, sb: ((0.03, 0.03), (run - 0.02, run - 0.02)),
                       [0.03, run - 0.02], seed, side_stone, clip=[(-kp, 1.0, c0)], tall_p=0.0)
    Fm = S.PlaneFace((-(hw - x_face), 0, 0), (0, -1, 0), (-1, 0, 0))
    n += S.lay_rounded(g, Fm, cs, cs[0], -CORE_BOT, lambda k, sa, sb: ((-(run - 0.02), -(run - 0.02)), (-0.03, -0.03)),
                       [-(run - 0.02), -0.03], seed + 1, side_stone, clip=[(kp, 1.0, c0)], tall_p=0.0)
    return n


def flight(wkey, rkey):
    W, n = WIDTHS[wkey], RISERS[rkey]
    hw, run, rise = W / 2, n * T, n * R
    p = Piece(f"{PREFIX}Flight_{wkey}_{rkey}", "walk_ramp",
              f"granite block flight {W:.1f} m wide, {n} risers x {R:.4f} over {run:.2f} m, rise {rise:.1f} m", TRACK)
    g = p.g
    rng = random.Random(9000 + 17 * n + int(W * 10))
    wear_x = 0.0
    kp = R / T
    for i in range(n):
        y0 = i * T - NOSE
        y1 = min((i + 1) * T + TUCK, run)
        ztop = (i + 1) * R
        wear_x = max(-0.18, min(0.18, wear_x + rng.uniform(-0.06, 0.06)))
        xs = step_cuts(W, i, rng)
        for j in range(len(xs) - 1):
            worn_block(g, xs[j], xs[j + 1], y0, y1, ztop, STEP_H, 9100 + 131 * i + 7 * j + n, rng, wear_x=wear_x,
                       slope=kp, r_round=0.030)        # f3: a softer, worn, rounded nosing (2.2 -> 3.0 cm)
    # f1 (judge delta 4): the flight's exposed sides in the WALL stone family: dressed polygon stones in rough courses
    # under the step slabs' sloped underside (every slab's bottom lies on z = under(y)), over a dark joint core
    xi = hw - 0.10
    ul = under_line()
    prof = [(0.03, CORE_BOT), (0.03, ul(0.03) - 0.01), (run - 0.02, ul(run - 0.02) - 0.01), (run - 0.02, CORE_BOT)]
    G.prism(g, [(xi, y, z) for (y, z) in prof], (1, 0, 0), 2 * xi, JE)
    p.extra_side = side_courses(g, hw, run, ul, 9300 + n + int(W * 10))
    # collision: ONE convex ramp through the tread midpoints (z = R y / T + R / 2), an 8 cm lip at the foot, flat on
    # the top tread; the character's feet sit within +-R/2 (8.3 cm) of the stone (GASP foot IK)
    p.hull_pts(S.hull_slope(-hw, hw, [(-NOSE, CORE_BOT), (-NOSE, R / 2), (run - T / 2, rise), (run, rise),
                                       (run, CORE_BOT)]), "walk_ramp")
    p.nanite = True
    p.moss = {SG: step_moss(hw), SR: step_moss(hw), FS: stone_moss(), JE: core_moss}
    p.snap("in", (0, 0, 0), (0, -1, 0), "foot of the first riser, lower walking level")
    p.snap("out", (0, run, rise), (0, 1, 0), "top of the flight: the next flight's pivot or a landing's S edge")
    for sd, sx in (("L", -1), ("R", 1)):
        p.snap(f"rail_{sd}", (sx * (hw - RAIL_IN), -T / 2, 0), (0, 1, 0), "a Rail_Slope pivot (its first post)")
        p.snap(f"cheek_{sd}", (sx * (hw + TW / 2), 0, 0), (0, 1, 0), "a Cheek_R pivot (wall centre line)")
    p.extra = {"side_stones": p.extra_side, "stones_per_step": "f3: 4 (W120, 0.30 m) / 5 (W180, 0.36 m) on even "
               "steps, one fewer on odd steps (0.40 / 0.45 m; staggered end joints)", "nosing_setback_m": OVER,
               "width": W, "risers": n, "riser_m": round(R, 4), "tread_m": round(T, 4), "run": round(run, 4),
               "rise": round(rise, 4), "pitch_deg": round(math.degrees(math.atan2(R, T)), 2),
               "collision_ramp_deg": round(math.degrees(math.atan2(R, T)), 2), "collision_lip_m": round(R / 2, 4)}
    return p


# ------------------------------------------------------------------------------------------------ landings
def flag_field(g, x0, x1, y0, y1, rng, seed):
    """Dressed flagstones (kit1_geo.pillow_face laid flat: a flat crown, low relief) in rows of random depth with
    slanted joints, tops at z = 0 +- 3 mm."""
    ys = [y0] + split_points(y0, y1, 0.32, 0.55, rng) + [y1]
    k = 0
    for r_ in range(len(ys) - 1):
        ya, yb = ys[r_], ys[r_ + 1]
        cuts = [x0] + split_points(x0, x1, 0.38, 0.78, rng) + [x1]
        lines = [(cuts[0], cuts[0])] + [(c + rng.uniform(-0.03, 0.03), c + rng.uniform(-0.03, 0.03)) for c in cuts[1:-1]] \
            + [(cuts[-1], cuts[-1])]
        for L_, R_ in zip(lines, lines[1:]):
            quad = [(L_[0], ya), (R_[0], ya), (R_[1], yb), (L_[1], yb)]
            inner = G.inset_convex(G.clean_poly(quad), rng.uniform(0.005, 0.007))
            if inner is None:
                continue
            G.pillow_face(g, inner, (0, 0, -0.005), (1, 0, 0), (0, 0, 1), 0.08, 0.0, rng.uniform(0.003, 0.006),
                          seed * 71 + k, SG, edge=rng.uniform(0.010, 0.014), rough=0.0022, fine=0.0014, step=0.03,
                          rounds=2, keep=0.12, crown=rng.uniform(4.0, 5.5), wobble=0.002, peak_off=0.2,
                          uv_off=(rng.uniform(0, 1), rng.uniform(0, 1)))
            k += 1
    return k


def kerb_side(g, a0, a1, fixed, side, rng, seed, z_top=0.0, h=0.30, depth=KW):
    """Kerb stones along one edge of a landing (rough_block, the outward face pillowed). side: '-y' '+y' '-x' '+x';
    a = the along coordinate (x for y edges, y for x edges); `fixed` = the edge's outer coordinate."""
    cuts = [a0] + split_points(a0, a1, 0.40, 0.70, rng) + [a1]
    D = {"-y": (0, 1, 0), "+y": (0, -1, 0), "-x": (1, 0, 0), "+x": (-1, 0, 0)}[side]
    for j in range(len(cuts) - 1):
        la, lb = cuts[j] + 0.005, cuts[j + 1] - 0.005
        c_along = (la + lb) / 2
        c_in = fixed + (depth / 2) * (1 if side in ("-y", "-x") else -1)
        c = (c_along, c_in) if side in ("-y", "+y") else (c_in, c_along)
        tz = z_top + rng.uniform(-0.002, 0.002)
        G.rough_block(g, (c[0], c[1], tz - h / 2), ((0, 0, 0), D, (0, 0, 1)), ((lb - la) / 2, depth / 2 - 0.004, h / 2),
                      0.026, seed * 13 + j, SG, bulge=0.004, rough=0.004, fine=0.0018,
                      n=(max(8, int((lb - la) / 0.05)), 6, 5))


def voronoi_all(seeds, x0, x1, y0, y1):
    """Convex Voronoi cells of 2D seeds in a box, clipped against EVERY other seed (no radius cut-off: the landing
    flags are big)."""
    cells = []
    for i, (sx, sy) in enumerate(seeds):
        poly = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        for j, (tx, ty) in enumerate(seeds):
            if i == j:
                continue
            a, b = tx - sx, ty - sy
            c = (tx * tx + ty * ty - sx * sx - sy * sy) / 2.0
            poly = G.convex_clip(poly, a, b, c)
            if len(poly) < 3:
                break
        if len(poly) >= 3:
            cells.append(poly)
    return cells


def flag_paving(g, x0, x1, y0, y1, rng, seed, spacing=0.62):
    """f1 (judge delta 5): FLUSH, large, irregular flagstones (Voronoi cells of a jittered grid, 0.45-0.9 m) over the
    whole landing to its edges, tight joints (1.0-1.2 cm), flat dressed tops at z = 0 +- 3 mm (kit1_geo.pillow_face
    laid flat: 6 mm arris, 2-3 mm crown), 14 cm thick; the edge flags' outer sides are the landing's straight edges."""
    nx = max(2, int(round((x1 - x0) / spacing)))
    ny = max(2, int(round((y1 - y0) / spacing)))
    dx, dy = (x1 - x0) / nx, (y1 - y0) / ny
    seeds = []
    for j in range(ny):
        for i in range(nx):
            off = 0.5 * dx * (j % 2) * 0.6
            seeds.append((x0 + (i + 0.5) * dx + off + rng.uniform(-0.24, 0.24) * dx,
                          y0 + (j + 0.5) * dy + rng.uniform(-0.24, 0.24) * dy))
    seeds = [(min(max(sx, x0 + 0.08), x1 - 0.08), sy) for (sx, sy) in seeds]
    k = 0
    for cell in voronoi_all(seeds, x0, x1, y0, y1):
        inner = G.inset_convex(G.clean_poly(cell), rng.uniform(0.005, 0.006))
        if inner is None:
            continue
        v0 = len(g.v)
        G.pillow_face(g, inner, (0, 0, -0.003), (1, 0, 0), (0, 0, 1), 0.14, 0.0, rng.uniform(0.002, 0.003),
                      seed * 71 + k, SG, edge=0.006, rough=0.0012, fine=0.0005, step=0.035, rounds=1, keep=0.10,
                      crown=6.0, wobble=0.0015, peak_off=0.2, uv_off=(rng.uniform(0, 1), rng.uniform(0, 1)))
        tx, ty = rng.uniform(-0.004, 0.004), rng.uniform(-0.004, 0.004)
        cx = sum(p_[0] for p_ in inner) / len(inner)
        cy = sum(p_[1] for p_ in inner) / len(inner)
        for vi in range(v0, len(g.v)):
            v = g.v[vi]
            if v.z > -0.02:
                g.v[vi] = Vector((v.x, v.y, v.z + tx * (v.x - cx) + ty * (v.y - cy)))
        k += 1
    return k


def flag_rect(g, x0, x1, y0, y1, rng, seed):
    """f2 (the owner's reading): FLUSH, LARGE, NEAR-RECTANGULAR flags in tight joints at path level: rows 0.45-0.75 m
    deep across the landing, each row cut into flags 0.55-0.95 m long (the rows' joints fall where they may: staggered),
    joint lines only 1.5 cm off square, 0.8-1.2 cm between the rims, flat dressed tops at z = 0 +- 3 mm
    (kit1_geo.pillow_face laid flat: 8 mm arris, 2-4 mm crown), 14 cm thick; the edge flags' outer sides are the
    landing's straight edges."""
    ys = [y0] + split_points(y0, y1, 0.45, 0.75, rng) + [y1]
    k = 0
    for r_ in range(len(ys) - 1):
        ya, yb = ys[r_], ys[r_ + 1]
        if r_ > 0:
            ya += 0.0
        cuts = [x0] + split_points(x0, x1, 0.55, 0.95, rng) + [x1]
        lines = [(cuts[0], cuts[0])] + [(c + rng.uniform(-0.015, 0.015), c + rng.uniform(-0.015, 0.015))
                                        for c in cuts[1:-1]] + [(cuts[-1], cuts[-1])]
        for L_, R_ in zip(lines, lines[1:]):
            quad = [(L_[0], ya), (R_[0], ya), (R_[1], yb), (L_[1], yb)]
            inner = G.inset_convex(G.clean_poly(quad), rng.uniform(0.004, 0.006))
            if inner is None:
                continue
            v0 = len(g.v)
            G.pillow_face(g, inner, (0, 0, -0.004), (1, 0, 0), (0, 0, 1), 0.14, 0.0, rng.uniform(0.002, 0.004),
                          seed * 71 + k, SG, edge=0.008, rough=0.0012, fine=0.0005, step=0.035, rounds=1, keep=0.08,
                          crown=5.5, wobble=0.0015, peak_off=0.2, uv_off=(rng.uniform(0, 1), rng.uniform(0, 1)))
            tx, ty = rng.uniform(-0.003, 0.003), rng.uniform(-0.003, 0.003)
            cx = sum(p_[0] for p_ in inner) / len(inner)
            cy = sum(p_[1] for p_ in inner) / len(inner)
            for vi in range(v0, len(g.v)):
                v = g.v[vi]
                if v.z > -0.02:
                    g.v[vi] = Vector((v.x, v.y, v.z + tx * (v.x - cx) / 0.5 + ty * (v.y - cy) / 0.5))
            k += 1
    return k


def landing_sides(g, x0, x1, y0, y1, seed):
    """One low course of dressed wall-granite stones round the landing's sides under the flags (CORE_BOT .. -0.15),
    faces 1.8 cm inside the edges."""
    n = 0
    cs = [0.15, -CORE_BOT]
    for k_, (O, t, nrm, a0, a1) in enumerate((((0, y0 + 0.018, 0), (1, 0, 0), (0, -1, 0), x0, x1),
                                             ((0, y1 - 0.018, 0), (-1, 0, 0), (0, 1, 0), -x1, -x0),
                                             ((x0 + 0.018, 0, 0), (0, -1, 0), (-1, 0, 0), -y1, -y0),
                                             ((x1 - 0.018, 0, 0), (0, 1, 0), (1, 0, 0), y0, y1))):
        F = S.PlaneFace(O, t, nrm)
        lo, hi = a0 + 0.03, a1 - 0.03
        n += S.lay_rounded(g, F, cs, 0.15, -CORE_BOT, lambda k, sa, sb, lo=lo, hi=hi: ((lo, lo), (hi, hi)), [lo, hi],
                           seed + 13 * k_, side_stone, tall_p=0.0)
    return n


def landing(wkey, kind):
    """f1 (judge delta 5): a flush landing: big irregular flags to the edges at path level, tight joints, NO raised
    curbs (the r0 kerb ring and upstands read as a tray); a low course of side stones under the flags."""
    W = WIDTHS[wkey]
    X = 2 * W + TW if kind == "SB" else W
    x0, x1, y0, y1 = -X / 2, X / 2, -W / 2, W / 2
    label = {"": "square", "L": "90 deg turn", "SB": "switchback"}[kind]
    p = Piece(f"{PREFIX}Landing{kind}_{wkey}", "walk_flat",
              f"{label} landing {X:.2f} x {W:.2f} m: flush, large, near-rectangular granite flags in tight joints, "
              f"top at 0 (edge it with Stair_Kerb_* on open sides)", TRACK)
    g = p.g
    rng = random.Random(7000 + int(W * 10) + len(kind) * 31)
    seed = 700 + int(W * 10) + len(kind) * 7
    nf = flag_rect(g, x0, x1, y0, y1, rng, seed)          # f2: near-rectangular flags (f1: Voronoi crazy paving)
    ns = landing_sides(g, x0, x1, y0, y1, seed + 50)
    G.box(g, x0 + 0.10, x1 - 0.10, y0 + 0.10, y1 - 0.10, CORE_BOT + 0.02, -0.13, JE)
    p.hull_box(x0, x1, y0, y1, CORE_BOT, 0.0, "walk_flat")
    p.nanite = True
    p.moss = {SG: paving_moss, FS: stone_moss(), JE: core_moss}
    for nm, loc, fac in (("S", (0, y0, 0), (0, -1, 0)), ("N", (0, y1, 0), (0, 1, 0)), ("W", (x0, 0, 0), (-1, 0, 0)),
                         ("E", (x1, 0, 0), (1, 0, 0))):
        p.snap(nm, loc, fac, "edge centre")
    if kind == "SB":
        p.snap("arrive", (-(W + TW) / 2, y0, 0), (0, -1, 0), "the arriving flight's out-snap (flight rot = landing rot)")
        p.snap("depart", ((W + TW) / 2, y0, 0), (0, -1, 0), "the departing flight's pivot (flight rot = landing rot + 180)")
        p.snap("divider", (0, y0, 0), (0, -1, 0), "a Cheek between the two flights (rot = landing rot + 180)")
    if kind == "L":
        p.snap("arrive", (0, y0, 0), (0, -1, 0), "arrive over the S edge")
        p.snap("leave", (x1, 0, 0), (1, 0, 0), "leave over the E edge (a right turn); walked the other way: a left turn")
    p.extra = {"size_x": round(X, 3), "size_y": round(W, 3), "kind": label, "upstand_edges": [], "upstand_h": 0.0,
               "flags": nf, "side_stones": ns, "joints_m": "0.8-1.2 between flag rims (f2: rows 0.45-0.75, flags "
               "0.55-0.95 m, joints 1.5 cm off square)"}
    return p


# ------------------------------------------------------------------------------------------------ f2: kerbs
KB_W = 0.22              # kerb block width (across the path edge)
KB_UP = 0.09             # kerb top above the path level (f3: 9 cm, the reference's lower-path kerbs stand 8-10 cm proud)
KB_BOT = -0.25           # buried to


def kerb_moss(obj, slot):
    """Kerbs: moss where the kerb meets the soil (the outer foot band just above path level and below it), in the end
    joints, a little on the outer top arris; the walked inner side cleaner."""
    me = obj.data
    ca = _wear(obj)
    n_f = 0
    for poly in me.polygons:
        if poly.material_index != slot:
            continue
        n_f += 1
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            col = ca.data[li].color
            m = clamp01((0.62 * S.moss_noise(co, 6.0) + 0.38 * S.moss_noise(co, 17.0, (1.7, 2.9, 5.3)) - 0.36) * 3.0)
            soil = clamp01((0.03 - co.z) / 0.06)
            joint = clamp01((col[0] - 0.36) * 2.2)
            outer = clamp01((co.x - 0.02) / 0.08)            # the kerb's outer (+x, soil) side
            a = m * clamp01(0.9 * soil * (0.5 + 0.5 * outer) + 0.8 * joint + 0.35 * outer)
            ca.data[li].color = (col[0], col[1], col[2], clamp01(a) * 0.9)
    me.update()
    return n_f


def kerb(length=None, corner=False):
    """A low KERB / edging of squared granite blocks (the reference's path edge): blocks 0.30-0.50 m long, KB_W wide,
    tops KB_UP above the path level, buried to KB_BOT; the walked top light (M_DKT_StepGranite), the sides darker
    (M_DKT_StepRiser); built along +Y from the pivot (the kerb's centre line at path level); its outer side is +X."""
    if corner:
        name, note, L = f"{PREFIX}Kerb_Corner", f"kerb corner block {KB_W:.2f} x {KB_W:.2f} m (two kerbs at 90 deg)", KB_W
    else:
        L = length
        name = f"{PREFIX}Kerb_L{int(round(L * 100)):03d}"
        note = (f"low kerb {L:.2f} m: squared granite blocks {KB_W:.2f} wide, top +{KB_UP:.2f} over the path, buried "
                f"to {KB_BOT:.2f}")
    p = Piece(name, "kerb", note, TRACK)
    rng = random.Random(4100 + int(L * 100) + (7 if corner else 0))
    sub = G.Geo()
    if corner:
        cuts = [0.0, L]
    else:
        cuts = [0.0] + split_points(0.0, L, 0.30, 0.50, rng) + [L]
    for j in range(len(cuts) - 1):
        # build along X (worn_block's front on -y), turned onto +Y below
        worn_block(sub, cuts[j], cuts[j + 1], -KB_W / 2, KB_W / 2, KB_UP + rng.uniform(-0.004, 0.004),
                   KB_UP - KB_BOT, 4200 + 13 * j + int(L * 10), rng, mat=SG, wear_x=(cuts[j] + cuts[j + 1]) / 2,
                   r_round=0.018, dip=0.002, chips=False, riser=SR, over=0.0)
    M = Matrix.Rotation(math.radians(90.0), 4, "Z")
    tg = sub.transformed(M)                        # (x, y) -> (-y, x): along the kerb = +Y, the block's -y front -> +X
    p.g = tg
    p.hull_box(-KB_W / 2, KB_W / 2, 0.0, L, KB_BOT, KB_UP, "kerb")
    p.nanite = False
    p.moss = {SG: kerb_moss, SR: kerb_moss}
    p.ground_z = -0.02
    p.snap("start", (0, 0, 0), (0, 1, 0), "kerb centre line at path level (its outer side +X)")
    p.snap("end", (0, L, 0), (0, 1, 0), "the next kerb's start")
    p.extra = {"length": round(L, 3), "width": KB_W, "top_above_path_m": KB_UP, "buried_to_m": KB_BOT,
               "blocks": len(cuts) - 1,
               "placing": "beside a landing / path edge at x = +-(W/2 + %.3f), the path level z 0" % (KB_W / 2 + 0.004)}
    return p


# ------------------------------------------------------------------------------------------------ cheek walls
PROUD = 0.015
STONE_DEPTH = 0.12


def wall_stone(g, quad, origin, t, n, rng, seed):
    """One pillow-faced rubble stone (kit 1's footing big-row recipe: rounded square / oval, full pillow), from its
    joint quad in face coordinates, one or two corners knocked off (irregular field stone)."""
    for _ in range(rng.choice((0, 1, 1, 2))):
        m_ = len(quad)
        i_ = rng.randrange(m_)
        pa, pc, pb = Vector(quad[i_ - 1]), Vector(quad[i_]), Vector(quad[(i_ + 1) % m_])
        f1, f2 = rng.uniform(0.15, 0.32), rng.uniform(0.15, 0.32)
        quad = quad[:i_] + [tuple(pc.lerp(pa, f1)), tuple(pc.lerp(pb, f2))] + quad[i_ + 1:]
    inner = G.inset_convex(G.clean_poly(quad), rng.uniform(*K1.JOINT_HALF))
    if inner is None or abs(G.poly_area(inner)) < 0.004:
        return 0
    w_ = max(q[0] for q in inner) - min(q[0] for q in inner)
    h_ = max(q[1] for q in inner) - min(q[1] for q in inner)
    s_ = min(w_, h_)
    if s_ < 0.06:
        return 0
    r = G.pillow_face(g, inner, origin, t, n, STONE_DEPTH, PROUD + rng.uniform(-0.004, 0.008),
                      min(0.036, max(0.014, 0.11 * s_ + rng.uniform(-0.004, 0.006))), seed, FS,
                      edge=rng.uniform(0.016, 0.026), rough=rng.uniform(0.006, 0.009), fine=0.003, step=0.032,
                      rounds=3, keep=rng.uniform(0.10, 0.18), crown=rng.uniform(2.0, 3.0), wobble=0.004, peak_off=0.12,
                      uv_off=(rng.uniform(0, 1), rng.uniform(0, 1)))
    return int(r is not None)


def rows_between(za, zb, lo, hi, rng):
    n = max(1, int(round((zb - za) / ((lo + hi) / 2))))
    ws = [rng.uniform(0.8, 1.2) for _ in range(n)]
    k = (zb - za) / sum(ws)
    out, z = [], za
    for w in ws[:-1]:
        z += w * k
        out.append(z)
    return [za] + out + [zb]


def rubble_wall(p, segs, seed):
    """A 0.40 m cheek wall along +Y (x in [-0.2, 0.2]) from CORE_BOT to stepped tops: segs = [(ya, yb, top), ...]
    contiguous, tops rising. Both faces laid in kit 1's pillow-faced rubble courses (M_DK_FootingStone), a dressed
    coping course (rough_block through-stones) on every segment, squared quoin through-stones at the wall's ends and at
    every step face, a dark joint-earth core."""
    g = p.g
    rng = random.Random(seed)
    y_end = segs[-1][1]
    cbs = [top - COPE_H for (_, _, top) in segs]
    levels = rows_between(CORE_BOT, cbs[0], 0.22, 0.30, rng)
    starts = [segs[0][0]] * (len(levels) - 1)
    for k in range(1, len(segs)):
        lv = rows_between(cbs[k - 1], cbs[k], 0.22, 0.28, rng)
        levels += lv[1:]
        starts += [segs[k][0]] * (len(lv) - 1)
    rows = [(levels[j], levels[j + 1], starts[j]) for j in range(len(levels) - 1)]
    hw = TW / 2
    n_st = 0
    for j, (za, zb, ys) in enumerate(rows):
        q0 = 0.34 if j % 2 == 0 else 0.22          # quoin lengths alternate course by course
        q1 = 0.22 if j % 2 == 0 else 0.34
        for (yq, ln, D) in ((ys, q0, (0, 1, 0)), (y_end, q1, (0, -1, 0))):
            cy = yq + (ln / 2 if D[1] > 0 else -ln / 2)
            G.rough_block(g, (0.0, cy, (za + zb) / 2), ((0, 0, 0), D, (0, 0, 1)),
                          (hw + PROUD + 0.004, ln / 2 - 0.008, (zb - za) / 2 - 0.008), 0.030, seed * 31 + j * 2 + (D[1] < 0),
                          FS, bulge=rng.uniform(0.006, 0.012), rough=0.007, fine=0.0028, n=(9, 7, 7))
            n_st += 1
        a_lo, a_hi = ys + q0 + 0.004, y_end - q1 - 0.004
        if a_hi - a_lo < 0.10:
            continue
        for face in ("+x", "-x"):
            if face == "+x":
                origin, t, nrm, A0, A1 = (hw, 0, 0), (0, 1, 0), (1, 0, 0), a_lo, a_hi
            else:
                origin, t, nrm, A0, A1 = (-hw, 0, 0), (0, -1, 0), (-1, 0, 0), -a_hi, -a_lo
            cuts = [A0] + split_points(A0, A1, 0.26, 0.48, rng) + [A1]
            lines = [(cuts[0], cuts[0])] + [(c + rng.uniform(-0.035, 0.035), c + rng.uniform(-0.035, 0.035))
                                            for c in cuts[1:-1]] + [(cuts[-1], cuts[-1])]
            for L_, R_ in zip(lines, lines[1:]):
                quad = [(L_[0], za), (R_[0], za), (R_[1], zb), (L_[1], zb)]
                n_st += wall_stone(g, quad, origin, t, nrm, rng, seed * 977 + n_st)
    for k, (ya, yb, top) in enumerate(segs):
        cuts = [ya] + split_points(ya, yb, 0.30, 0.55, rng) + [yb]
        for j in range(len(cuts) - 1):
            la, lb = cuts[j] + 0.006, cuts[j + 1] - 0.006
            G.rough_block(g, (0.0, (la + lb) / 2, top - COPE_H / 2 + 0.002), ((0, 0, 0), (1, 0, 0), (0, 0, 1)),
                          ((lb - la) / 2, hw + 0.025, COPE_H / 2 - 0.004), 0.030, seed * 53 + k * 11 + j, FS,
                          bulge=0.006, rough=0.005, fine=0.0022, n=(max(7, int((lb - la) / 0.05)), 9, 5))
            n_st += 1
        # the joint-earth core, recessed CORE_IN behind every exposed face: at the wall's ends AND behind each step
        # face (above the lower segment's coping line), so it only ever shows deep in the joints
        y_b = yb - (K1.CORE_IN if k == len(segs) - 1 else 0.0)
        if k == 0:
            G.box(g, -hw + K1.CORE_IN, hw - K1.CORE_IN, ya + K1.CORE_IN, y_b, CORE_BOT, top - COPE_H + 0.006, JE)
        else:
            G.box(g, -hw + K1.CORE_IN, hw - K1.CORE_IN, ya - 0.002, y_b, CORE_BOT, cbs[k - 1] - 0.002, JE)
            G.box(g, -hw + K1.CORE_IN, hw - K1.CORE_IN, ya + K1.CORE_IN, y_b, cbs[k - 1] - 0.004,
                  top - COPE_H + 0.006, JE)
        p.hull_box(-hw, hw, ya, yb, CORE_BOT, top, "walk_flat_top")
    return n_st


CH_LOW = 0.15            # f1 (judge delta 10): the cheek stands only 0.15 m over the tread / landing it flanks
CB_THIN = 0.30           # the cheek block's height at its thin (right) end


def cheek_block(g, ya, yb, top_fn, bot_fn, seed, rng, hw=TW / 2, mat=FS):
    """A dressed through-stone across the cheek (x -hw..hw), from bot_fn(y) to top_fn(y) (both sheared to follow a
    slope when they are sloped lines): kit1_geo.rough_block, calm relief, crisp rounded arrises."""
    yc = (ya + yb) / 2
    t_c, b_c = top_fn(yc), bot_fn(yc)
    H = t_c - b_c
    v0 = len(g.v)
    G.rough_block(g, (0.0, yc, (t_c + b_c) / 2), ((0, 1, 0), (1, 0, 0), (0, 0, 1)),
                  ((yb - ya) / 2 - 0.006, hw + 0.012, H / 2 - 0.004), 0.028, seed, mat, bulge=rng.uniform(0.004, 0.008),
                  rough=0.0020, fine=0.0006, n=(max(7, int((yb - ya) / 0.05)), 9, max(5, int(H / 0.06))))
    for i in range(v0, len(g.v)):
        v = g.v[i]
        f = clamp01((v.z - b_c) / max(H, 1e-3))          # 0 at the bottom, 1 at the top
        dz = f * (top_fn(v.y) - t_c) + (1 - f) * (bot_fn(v.y) - b_c)
        g.v[i] = Vector((v.x, v.y, v.z + dz))
    return g


def cheek_body(g, p, y_end, bl, seed, rng):
    """Under the cheek blocks: end quoins (through-stones) and dressed wall-granite polygon stones on both faces from
    CORE_BOT up to the blocks' underside bl(y) (clipped 12 mm below it), over a dark core."""
    hw = TW / 2
    q = 0.30
    for (ya, yb) in ((0.0, q), (y_end - q, y_end)):
        cheek_block(g, ya, yb, lambda y: bl(y) - 0.012, lambda y: CORE_BOT, seed * 7 + int(ya * 10), rng)
    kp = (bl(1.0) - bl(0.0))
    c0 = bl(0.0) - 0.012
    s_hi = -(max(bl(0.0), bl(y_end)) + 0.05)
    cs, s = [-CORE_BOT], -CORE_BOT
    while s > s_hi:
        s -= rng.uniform(0.26, 0.38)
        cs.append(s)
    cs.sort()
    lo, hi = q + 0.004, y_end - q - 0.004
    n = 0
    if hi - lo > 0.12:
        Fp = S.PlaneFace((hw - 0.018, 0, 0), (0, 1, 0), (1, 0, 0))
        n += S.lay_rounded(g, Fp, cs, cs[0], -CORE_BOT, lambda k, sa, sb: ((lo, lo), (hi, hi)), [lo, hi], seed,
                           side_stone, clip=[(-kp, 1.0, c0)], tall_p=0.0)
        Fm = S.PlaneFace((-(hw - 0.018), 0, 0), (0, -1, 0), (-1, 0, 0))
        n += S.lay_rounded(g, Fm, cs, cs[0], -CORE_BOT, lambda k, sa, sb: ((-hi, -hi), (-lo, -lo)), [-hi, -lo],
                           seed + 1, side_stone, clip=[(kp, 1.0, c0)], tall_p=0.0)
    xi = hw - 0.09
    prof = [(q - 0.02, CORE_BOT), (q - 0.02, bl(q) - 0.02), (y_end - q + 0.02, bl(y_end - q) - 0.02),
            (y_end - q + 0.02, CORE_BOT)]
    G.prism(g, [(xi, y, z) for (y, z) in prof], (1, 0, 0), 2 * xi, JE)
    return n


CH_LOWV = 0.12           # f2: the single-course low cheek stands 0.12 m over the tread / paving
CB_LOWV = 0.34           # and its blocks are 0.34 m tall (0.22 m of each sits in the soil)


def soil_moss(kp):
    """f2 (the owner's reading): moss where the cheek meets the soil: a band up to ~0.16 m over the soil line
    z = y kp - 0.04 (the pitch line beside a flight, level beside a landing), heaviest at the line, patchy; plus the
    wall-stone moss in the joints and on ledges."""
    base = stone_moss()

    def f(obj, slot):
        n_f = base(obj, slot)
        me = obj.data
        ca = _wear(obj)
        for poly in me.polygons:
            if poly.material_index != slot:
                continue
            for li in poly.loop_indices:
                co = me.vertices[me.loops[li].vertex_index].co
                col = ca.data[li].color
                zs = max(0.0, co.y) * kp - 0.04
                band = clamp01(1.0 - (co.z - zs) / 0.16) * clamp01((co.z - (zs - 0.25)) / 0.10)
                m = clamp01((0.6 * S.moss_noise(co, 5.0, (4.1, 0.3, 2.2)) + 0.4 * S.moss_noise(co, 16.0) - 0.30) * 2.6)
                ca.data[li].color = (col[0], col[1], col[2], clamp01(max(col[3], 0.92 * band * m)))
        me.update()
        return n_f
    return f


def cheek(rkey=None, length=None, low=False):
    """f1 / f2: the stepped cheek: one course of dressed through-stones standing CH_LOW (0.15 m) over the treads it
    flanks (one stone per tread, stepped, their undersides on the pitch line) or over the landing (flat), on a buried
    base of the wall's rounded pillow stones (f2), moss where it meets the soil.
    low=True (f2, Cheek_Low_*): the SINGLE-COURSE low cheek: only the through-stones, CB_LOWV tall, standing CH_LOWV
    (0.12 m) over the tread and sitting 0.22 m into the soil (no base courses)."""
    rng = random.Random(3100 + (RISERS[rkey] if rkey else int(length * 10)) + (57 if low else 0))
    up, thin = (CH_LOWV, CB_LOWV) if low else (CH_LOW, CB_THIN)
    tag = "Cheek_Low_" if low else "Cheek_"
    kp = R / T if rkey else 0.0
    if rkey:
        n = RISERS[rkey]
        y_end = n * T
        bl = (lambda y: y * kp + up - thin)                         # the blocks' underside (thin end = `thin`)
        name = f"{PREFIX}{tag}{rkey}"
        note = (f"single-course low cheek beside a {rkey} flight: one dressed stone per tread standing +{up:.2f} over "
                f"it, {thin - up:.2f} m of it in the soil, no base" if low else
                f"low stepped cheek beside a {rkey} flight, 0.40 thick: one dressed stone per tread standing "
                f"+{up:.2f} over it, a base of rounded wall stones")
        end = (0, n * T, n * R)
        segs = [(i * T, (i + 1) * T, (i + 1) * R + up) for i in range(n)]
    else:
        y_end = length
        bl = (lambda y: up - (thin if low else 0.32))
        name = f"{PREFIX}{tag}L{int(round(length * 100)):03d}"
        note = (f"single-course low flat cheek {length:.2f} m: dressed stones +{up:.2f} over the paving, no base" if low
                else f"low flat cheek {length:.2f} m (landing sides), one dressed course +{up:.2f} over the paving, "
                f"a base of rounded wall stones")
        end = (0, length, 0)
        cuts = [0.0] + split_points(0.0, length, 0.42, 0.70, rng) + [length]
        segs = [(cuts[k], cuts[k + 1], up) for k in range(len(cuts) - 1)]
    p = Piece(name, "wall", note, TRACK)
    g = p.g
    for k, (ya, yb, top) in enumerate(segs):
        cheek_block(g, ya, yb, (lambda y, top=top: top), bl, 3200 + 17 * k + len(segs) + (91 if low else 0), rng)
        p.hull_box(-TW / 2, TW / 2, ya, yb, (bl((ya + yb) / 2) if low else CORE_BOT), top, "walk_flat_top")
    ns = 0 if low else cheek_body(g, p, y_end, bl, 3300 + len(segs), rng)
    p.extra = {"blocks": len(segs), "base_stones": ns, "height_over_tread_m": up, "courses": 1 if low else "1 + base",
               "segments": [[round(a, 3), round(b, 3), round(c, 3)] for a, b, c in segs], "thickness": TW}
    p.nanite = not low
    p.moss = {FS: soil_moss(kp), JE: core_moss}
    p.ground_z = (-0.05 if low else CORE_BOT + 0.35)
    p.snap("start", (0, 0, 0), (0, -1, 0), "wall centre line at its start, level 0")
    p.snap("end", end, (0, 1, 0), "the next cheek's start")
    return p


def cheek_corner():
    p = Piece(f"{PREFIX}CheekCorner", "wall", f"0.40 x 0.40 pier closing two low cheeks at a turn, top +{CH_LOW:.2f}",
              TRACK)
    g = p.g
    rng = random.Random(3301)
    hw = TW / 2
    G.rough_block(g, (0, 0, CH_LOW - 0.16), ((1, 0, 0), (0, 1, 0), (0, 0, 1)), (hw + 0.012, hw + 0.012, 0.156), 0.028,
                  3310, FS, bulge=0.006, rough=0.0020, fine=0.0006, n=(9, 9, 6))
    zb = CH_LOW - 0.32 - 0.012
    G.rough_block(g, (0, 0, (zb + CORE_BOT) / 2), ((0, 1, 0), (1, 0, 0), (0, 0, 1)),
                  (hw + 0.008, hw + 0.008, (zb - CORE_BOT) / 2 - 0.004), 0.028, 3311, FS, bulge=0.006, rough=0.0035,
                  fine=0.0010, n=(9, 9, 5))
    p.hull_box(-hw, hw, -hw, hw, CORE_BOT, CH_LOW, "walk_flat_top")
    p.nanite = True
    p.moss = {FS: stone_moss()}
    p.ground_z = 0.0
    p.snap("centre", (0, 0, 0), (0, 1, 0), "pier centre, level 0; its faces line up with 0.40 cheeks meeting at 90 deg")
    return p


# ------------------------------------------------------------------------------------------------ handrails
# f1 (judge delta 7): round rustic poles let THROUGH the posts (no face-bolted squared rails, no bosses); posts a little
# shorter with domed tops; every Rail_Slope carries the posts at BOTH its ends (a run never cantilevers); the flat spans
# are the poles alone, hung between the posts other pieces supply (a slope's end / start post, Rail_CornerPost,
# Rail_EndPost), so no two pieces ever put a post in the same place along a path.
POLE_R = {"top": 0.034, "mid": 0.028}


RAIL_SEC = {"top": (0.050, 0.075), "mid": (0.044, 0.064)}     # f2: squared rails (width, height), m


def sq_rail(g, p0, p1, sec, seed):
    """f2 (the owner's reading): a SQUARED timber rail from post centre to post centre, its ends HOUSED in the round
    posts (the rail's end sits inside the post: a mortise), lightly chamfered (6 mm), its section upright (the sides
    vertical, the top square to the rail's slope)."""
    p0, p1 = Vector(p0), Vector(p1)
    A = (p1 - p0).normalized()
    D = Vector((0.0, 0.0, 1.0)).cross(A)
    if D.length < 1e-6:
        D = Vector((1.0, 0.0, 0.0))
    D.normalize()
    U = A.cross(D).normalized()
    if U.z < 0:
        U, D = -U, -D
    L = (p1 - p0).length
    w, h = sec
    G.hewn_box(g, (p0 + p1) / 2, (A, D, U), (L / 2, w / 2, h / 2), 0.006, seed, TD, exposed=())


def pole(g, p0, p1, r, seed):
    """A round timber pole from post centre to post centre (its ends run inside the posts: let through), a slight
    taper and a sag-free straight axis; 10 sides."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    ax = d.normalized()
    up = Vector((0, 0, 1)) if abs(ax.z) < 0.9 else Vector((1, 0, 0))
    rr = random.Random(seed)
    r = r * rr.uniform(0.94, 1.06)
    G.lathe(g, p0, ax, up, [(0.0, 0.0), (0.0, r), (L * 0.5, r * 1.03), (L, r * 0.97), (L, 0.0)], TD, nseg=10)


def post(g, x, y, zb, r=PR, top=POST_H, cross=False):
    """A round timber post with a domed top, 0.10 m below its base (the rails pass through it: no pegs)."""
    tz = top + 0.10
    G.lathe(g, (x, y, zb - 0.10), (0, 0, 1), (1, 0, 0),
            [(0.0, 0.0), (0.0, r), (tz - 0.050, r), (tz - 0.034, r * 0.95), (tz - 0.020, r * 0.82),
             (tz - 0.008, r * 0.55), (tz, r * 0.12), (tz + 0.002, 0.0)], TD, nseg=14)


def rail_span(name, run, rise, bays, note, posts=True):
    p = Piece(name, "thin_upright", note, TRACK)
    g = p.g
    slope = rise / run if run else 0.0
    ys = [run * k / bays for k in range(bays + 1)]
    if posts:
        for k in range(bays + 1):
            post(g, 0.0, ys[k], ys[k] * slope)
            p.hull_box(-0.07, 0.07, ys[k] - 0.07, ys[k] + 0.07, ys[k] * slope - 0.10, ys[k] * slope + POST_H, "post")
    for k in range(bays):
        ya, yb = ys[k], ys[k + 1]
        for lvl, zz in (("top", TOP_Z), ("mid", MID_Z)):
            sq_rail(g, (0, ya, ya * slope + zz), (0, yb, yb * slope + zz), RAIL_SEC[lvl],
                    len(name) * 131 + k * 7 + (lvl == "top"))
        za, zb_ = ya * slope, yb * slope
        p.hull_pts([(x, y, z) for x in (-0.04, 0.04) for (y, z) in
                    ((ya, za + 0.15), (yb, zb_ + 0.15), (ya, za + TOP_Z + 0.04), (yb, zb_ + TOP_Z + 0.04))], "rail")
    p.ground_z = -0.10
    p.snap("start", (0, 0, 0), (0, -1, 0), "this span's start: " + ("its own first post base" if posts else
                                                                     "the post it hangs from (a slope's end post, a "
                                                                     "corner post or an end post)"))
    p.snap("end", (0, run, rise), (0, 1, 0), "the far post: " + ("this piece's own end post" if posts else
                                                                   "a slope's start post / corner post / end post"))
    spacing = math.hypot(run / bays, rise / bays)
    p.extra = {"run": round(run, 4), "rise": round(rise, 4), "bays": bays, "post_spacing_along_rail_m": round(spacing, 3),
               "posts_in_piece": (bays + 1) if posts else 0, "rail_centres_above_base_line_m": [TOP_Z, MID_Z],
               "rails": "squared rails %.1f x %.1f cm (top) / %.1f x %.1f cm (mid), housed into the round posts "
                        "(f2)" % (100 * RAIL_SEC["top"][0], 100 * RAIL_SEC["top"][1], 100 * RAIL_SEC["mid"][0],
                                  100 * RAIL_SEC["mid"][1])}
    return p


def rail_post(name, r, cross, note):
    p = Piece(name, "thin_upright", note, TRACK)
    post(p.g, 0.0, 0.0, 0.0, r=r, top=POST_H + (0.02 if cross else 0.0), cross=cross)
    p.hull_box(-r - 0.01, r + 0.01, -r - 0.01, r + 0.01, -0.10, POST_H + 0.02, "post")
    p.ground_z = -0.10
    p.snap("base", (0, 0, 0), (0, 1, 0), "post base on the rail line")
    return p


# ------------------------------------------------------------------------------------------------ lanterns
def square_loft(g, rings, mat, segs=8, apex=None, bottom=None, inside=(0.0, 0.0, 0.0)):
    """A loft through square rings [(half, z, corner_upturn)], each side subdivided `segs` times; the upturn lifts
    the corners with |t|^5 falloff (the sheet's hood tips). apex / bottom: z of a closing fan point on the axis.
    Faces are wound outward from the point `inside`."""
    def ring(h, z, up):
        pts = []
        cs = [(-h, -h), (h, -h), (h, h), (-h, h)]
        for s in range(4):
            (x0, y0), (x1, y1) = cs[s], cs[(s + 1) % 4]
            for k in range(segs):
                t = k / segs
                u = abs(2 * t - 1)
                pts.append(Vector((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, z + up * u ** 5)))
        return pts
    R_ = [ring(*r) for r in rings]
    m = len(R_[0])
    verts = [p for r in R_ for p in r]
    faces = []
    for i in range(len(R_) - 1):
        for j in range(m):
            faces.append((i * m + j, i * m + (j + 1) % m, (i + 1) * m + (j + 1) % m, (i + 1) * m + j))
    for zc, ri in ((apex, len(R_) - 1), (bottom, 0)):
        if zc is None:
            continue
        verts.append(Vector((0.0, 0.0, zc)))
        c = len(verts) - 1
        for j in range(m):
            faces.append((ri * m + j, ri * m + (j + 1) % m, c))
    cin = Vector(inside)
    out = []
    for f in faces:
        vs = [verts[i] for i in f]
        fc = sum(vs, Vector()) / len(vs)
        n = (vs[1] - vs[0]).cross(vs[2] - vs[0])
        out.append(tuple(f) if n.dot(fc - cin) >= 0 else tuple(reversed(f)))
    g.add(verts, out, mat, None, None)
    return g


def lantern_timber():
    """f1 (judge delta 6): the sheet's path lantern: a panelled timber shaft NARROWER than the head (0.176 m, 31 % under
    the r0 0.244) on a splayed foot (four small flared legs under a flared skirt), a cove bracket up to the cornice, a
    square light box (corner posts, rails, a middle mullion: two warm panes a face, library GlassAmber), a head rail, a
    STEEP pointed hipped iron roof with curved, upturned eaves and a tall bulb finial."""
    p = Piece(f"{PREFIX}Lantern_Timber", "thin_upright",
              "square timber path lantern 1.33 m (f2: darker weathered body, warm amber panes, charcoal hood): "
              "narrow panelled shaft on splayed feet, two amber panes a face, steep "
              "pointed iron roof with upturned eaves and a tall finial (the sheet's stair lanterns)", TRACK)
    g = p.g
    ax = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    # splayed feet: four small legs leaning out from under the skirt (their tops tucked in, their toes out)
    for sx in (-1, 1):
        for sy in (-1, 1):
            o = Vector((sx * 0.100, sy * 0.100, 0.0))
            lean = Vector((sx * 0.030, sy * 0.030, 0.0))
            top = o + Vector((0, 0, 0.075))
            foot = o + lean
            d = (top - foot)
            c = (top + foot) / 2
            u = d.normalized()
            a_ = Vector((1, 0, 0)) - u * u.x
            a_.normalize()
            G.obox(g, c, a_, u.cross(a_).normalized(), u, 0.020, 0.020, d.length / 2, TD)
    # the flared skirt: from the foot plinth (0.13) curving in to the shaft (0.088)
    square_loft(g, [(0.132, 0.070, 0.0), (0.128, 0.082, 0.0), (0.116, 0.096, 0.0), (0.102, 0.112, 0.0),
                    (0.092, 0.130, 0.0), (0.088, 0.145, 0.0)], TD, segs=1, bottom=0.070, inside=(0, 0, 0.11))
    G.hewn_box(g, (0, 0, 0.345), ax, (0.088, 0.088, 0.200), 0.006, 13, TD, exposed=())      # shaft 0.145 .. 0.545
    fr, hwp = 0.018, 0.088                                                                    # panel frames, 4 mm proud
    for (n_, t_) in (((0, -1, 0), (1, 0, 0)), ((0, 1, 0), (-1, 0, 0)), ((-1, 0, 0), (0, -1, 0)), ((1, 0, 0), (0, 1, 0))):
        n_, t_ = Vector(n_), Vector(t_)
        c0 = n_ * (hwp + 0.002)
        for (a0, a1, z0, z1) in ((-0.070, 0.070, 0.175, 0.175 + fr), (-0.070, 0.070, 0.515 - fr, 0.515),
                                 (-0.070, -0.070 + fr, 0.175 + fr, 0.515 - fr), (0.070 - fr, 0.070, 0.175 + fr, 0.515 - fr),
                                 (-0.070, 0.070, 0.345 - fr / 2, 0.345 + fr / 2)):
            cc = c0 + t_ * ((a0 + a1) / 2) + Vector((0, 0, (z0 + z1) / 2))
            G.obox(g, cc, t_ if (a1 - a0) > (z1 - z0) else Vector((0, 0, 1)), n_,
                   Vector((0, 0, 1)) if (a1 - a0) > (z1 - z0) else t_,
                   max(a1 - a0, z1 - z0) / 2, 0.003, min(a1 - a0, z1 - z0) / 2, TD)
    # cove bracket from the shaft out to the cornice
    square_loft(g, [(0.088, 0.545, 0.0), (0.094, 0.552, 0.0), (0.108, 0.558, 0.0), (0.128, 0.562, 0.0),
                    (0.146, 0.564, 0.0)], TD, segs=1, inside=(0, 0, 0.50))
    G.hewn_box(g, (0, 0, 0.5755), ax, (0.152, 0.152, 0.0115), 0.005, 14, TD, exposed=())  # cornice 0.564 .. 0.587
    G.hewn_box(g, (0, 0, 0.598), ax, (0.138, 0.138, 0.011), 0.004, 15, TD, exposed=())     # sill 0.587 .. 0.609
    zb, zt = 0.61, 0.95                      # f3: a taller light box (h/w 0.34 / 0.29 ~ 1.2, the reference's)
    hwb = 0.128
    for sx in (-1, 1):
        for sy in (-1, 1):
            G.box(g, sx * hwb - 0.016, sx * hwb + 0.016, sy * hwb - 0.016, sy * hwb + 0.016, zb, zt, TD, grain="z")
    for zz, hh in ((zb + 0.013, 0.013), (zt - 0.013, 0.013)):
        for sy in (-1, 1):
            G.box(g, -hwb, hwb, sy * hwb - 0.012, sy * hwb + 0.012, zz - hh, zz + hh, TD, grain="x")
        for sx in (-1, 1):
            G.box(g, sx * hwb - 0.012, sx * hwb + 0.012, -hwb + 0.016, hwb - 0.016, zz - hh, zz + hh, TD, grain="y")
    for sy in (-1, 1):
        G.box(g, -0.008, 0.008, sy * (hwb + 0.004) - 0.007, sy * (hwb + 0.004) + 0.007, zb + 0.026, zt - 0.026, TD, grain="z")
    for sx in (-1, 1):
        G.box(g, sx * (hwb + 0.004) - 0.007, sx * (hwb + 0.004) + 0.007, -0.008, 0.008, zb + 0.026, zt - 0.026, TD, grain="z")
    G.box(g, -0.117, 0.117, -0.117, 0.117, zb + 0.004, zt - 0.004, LG)                   # the panes (a glass box)
    G.hewn_box(g, (0, 0, zt + 0.0125), ax, (0.150, 0.150, 0.0125), 0.006, 16, TD, exposed=())  # head 0.88 .. 0.905
    zh = zt + 0.025
    # f1 roof: steep and pointed (rise 0.27 over a 0.44 eave: the flanks reach ~50 deg), concave flanks, the eaves curve
    # up to 3.8 cm tips
    # f3 (judge delta 10, checked on the reference lantern): a STRAIGHTER, steeper pyramid (flanks ~57 deg) with a
    # smaller eave (0.38 m, f2 0.44) and only a slight upturn at the tips (1.6 cm, f2 3.8 cm)
    hr = 0.29
    square_loft(g, [(0.140, zh - 0.002, 0.0), (0.190, zh, 0.016), (0.194, zh + 0.013, 0.018), (0.178, zh + 0.030, 0.012),
                    (0.150, zh + 0.072, 0.004), (0.120, zh + 0.117, 0.001), (0.090, zh + 0.160, 0.0),
                    (0.062, zh + 0.202, 0.0), (0.038, zh + 0.238, 0.0),
                    (0.018, zh + hr - 0.010, 0.0)], IR, segs=8, apex=zh + hr, bottom=zh - 0.002, inside=(0, 0, zh + 0.05))
    # tall finial: a neck, a collar, a bulb (hoju) with a point
    z0 = zh + hr - 0.012
    # f3: the finial about twice as tall (a taller neck and knob: the reference's tall finial)
    fz = 1.9
    G.lathe(g, (0, 0, z0), (0, 0, 1), (1, 0, 0),
            [(0.0, 0.0), (0.0, 0.014), (0.030 * fz, 0.010), (0.038 * fz, 0.019), (0.046 * fz, 0.019), (0.052 * fz, 0.011),
             (0.060 * fz, 0.016), (0.074 * fz, 0.027), (0.090 * fz, 0.029), (0.104 * fz, 0.023), (0.116 * fz, 0.012),
             (0.126 * fz, 0.004), (0.134 * fz, 0.0)], IR, nseg=12)
    top = z0 + 0.134 * fz
    p.hull_box(-0.13, 0.13, -0.13, 0.13, 0.0, 0.59, "post")
    p.hull_box(-0.15, 0.15, -0.15, 0.15, 0.59, zh + 0.03, "lamp")
    p.hull_pts([(sx * 0.24, sy * 0.24, zh) for sx in (-1, 1) for sy in (-1, 1)] + [(0, 0, top)], "lamp")
    p.ground_z = 0.0
    p.snap("base", (0, 0, 0), (0, -1, 0), "base centre on the paving / ground; front faces -Y")
    p.extra = {"height_m": round(top, 3), "shaft_w_m": 0.176, "head_w_m": 0.30, "roof_rise_m": hr,
               "light_local": [0.0, 0.0, round((zb + zt) / 2, 3)],
               "light": "UE point light, warm 2200-2700 K, a separate actor (showcase rule); the glass lights only the pane"}
    return p


def lantern_stone(sc_coll):
    """The courtyard SHORT granite lantern (build_stone_props.LANTERN_SHORT, imported, not forked) at 0.75 scale: a
    0.90 m path lantern; its own builder makes the geometry, UVs, moss cushions and library wear."""
    SP = S.load_builder(S.STONE_PROPS_BUILDER, "dojo_build_stone_props")
    s = 0.75
    d = {}
    for k, v in SP.LANTERN_SHORT.items():
        if k == "note":
            continue
        if isinstance(v, (int, float)):
            d[k] = v * s
        elif isinstance(v, tuple):
            d[k] = tuple(x * s for x in v)
        else:
            d[k] = [tuple(x * s for x in t) for t in v]
    d["note"] = "path lantern: the courtyard short granite lantern at 0.75 scale (0.90 m)"
    SP.G.seed(8201)
    part = SP.lantern(f"{PREFIX}Lantern_Stone", d)
    o = part.build(sc_coll)
    stats = SP.apply_library(o)
    p = Piece(f"{PREFIX}Lantern_Stone", "thin_upright", d["note"], TRACK)
    p.part = o
    p.ground_z = 0.0
    p.snap("base", (0, 0, 0), (0, -1, 0), "base centre; front (four-pane window) faces -Y")
    box = d["box"]
    p.extra = {"height_m": round(d["top"], 3), "scale_of_LanternShort": s, "light_local": [0.0, 0.0, round((box[2] + box[3]) / 2, 3)],
               "library_pass": {k: (v if not isinstance(v, dict) else {kk: vv for kk, vv in v.items() if isinstance(vv, (int, float))})
                                for k, v in stats.items() if k != "wear"}}
    o["nanite"] = False
    return p, SP


# ------------------------------------------------------------------------------------------------ materials
def materials(need_sp):
    S.kit_materials()                      # f1: the kit granite family first (same recipes as track 8)
    S.lib_variants()                       # f2: weathered timber (+ end), charcoal hood, warm amber panes
    K1.lib_materials()                     # the library set (+ kit 1's recipes; unused slots are not assigned)



# ------------------------------------------------------------------------------------------------ measurement
def measure(obj, p):
    """Measured, not assumed: flights - the centre-line tread heights (ray cast down mid-tread), risers, tread
    depth, the UCX ramp angle and lip; landings - the paving flatness (7 x 7 rays); rails - post spacing and rail
    heights over the base line; everything - bbox, tris, hulls."""
    rec = S.mesh_stats(obj)
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bvh = BVHTree.FromBMesh(bm)
    bm.free()

    def down(x, y, z0=5.0):
        h = bvh.ray_cast(Vector((x, y, z0)), Vector((0, 0, -1)), 20.0)
        return None if h[0] is None else h[0].z

    if "Flight" in p.name:
        n = p.extra["risers"]
        tops = []
        for i in range(n):
            zs = [down(xx, i * T + T * 0.45) for xx in (-0.37, -0.29, -0.21, -0.13, -0.05, 0.03, 0.11, 0.19, 0.27)]
            zs = sorted(z for z in zs if z is not None)
            tops.append(zs[len(zs) // 2])        # f2: the median (3-5 blocks a tread: a ray down an end joint is not
                                                 # the tread)
        risers = [tops[0]] + [tops[i] - tops[i - 1] for i in range(1, n)]
        rec["tread_tops_centre_m"] = [round(z, 4) for z in tops]
        rec["risers_measured_m"] = {"min": round(min(risers), 4), "max": round(max(risers), 4)}
        over = []
        for i in range(1, n):
            for xx in (-0.25, 0.0, 0.25):
                zt_ = tops[i]
                ys_ = []
                for dz_ in (0.006, 0.012, 0.018, 0.024, 0.030, 0.036):
                    hl = bvh.ray_cast(Vector((xx, i * T - 0.5, zt_ - dz_)), Vector((0, 1, 0)), 1.0)
                    if hl[0] is not None:
                        ys_.append(hl[0].y)
                hr_ = bvh.ray_cast(Vector((xx, i * T - 0.5, zt_ - 0.11)), Vector((0, 1, 0)), 1.0)
                if ys_ and hr_[0] is not None:
                    over.append(hr_[0].y - min(ys_))           # riser face behind the nosing's frontmost point
        ok_ = sorted(o_ for o_ in over if 0.005 < o_ < 0.06)       # rays through a slab joint hit the next step
        if ok_:
            rec["nosing_overhang_m"] = {"min": round(ok_[0], 4), "max": round(ok_[-1], 4),
                                        "median": round(ok_[len(ok_) // 2], 4), "samples": len(ok_),
                                        "rays_through_joints": len(over) - len(ok_)}
        noses = [down(0.0, i * T - NOSE + 0.004) for i in range(n)]
        rec["nosing_drop_m"] = round(max((tops[i] - noses[i]) for i in range(n) if noses[i] is not None), 4)
        hull = [ch for ch in obj.children if ch.name.startswith("UCX_")][0]
        hv = [v.co for v in hull.data.vertices]
        top_z = max(v.z for v in hv)
        lip = [v for v in hv if v.y < 0.0 and v.z > CORE_BOT + 0.01]
        lip_z = max(v.z for v in lip)
        up = [v for v in hv if abs(v.z - top_z) < 1e-4]
        y_up = min(v.y for v in up)
        y_lip = max(v.y for v in lip)
        rec["ucx_ramp_deg"] = round(math.degrees(math.atan2(top_z - lip_z, y_up - y_lip)), 2)
        rec["ucx_lip_m"] = round(lip_z, 4)
        rec["ucx_vs_tread_mid_m"] = round(max(abs((R * (i * T + T / 2) / T + R / 2) - tops[i]) for i in range(n - 1)), 4)
        rec["gasp_ok"] = rec["ucx_ramp_deg"] < 44.77 and rec["ucx_lip_m"] <= 0.45 and rec["risers_measured_m"]["max"] <= 0.45
    if "Landing" in p.name:
        X, Y = p.extra["size_x"], p.extra["size_y"]
        zs = []
        for i in range(7):
            for j in range(7):
                x = -X / 2 + 0.05 + (X - 0.10) * i / 6
                y = -Y / 2 + 0.05 + (Y - 0.10) * j / 6
                if p.extra["upstand_edges"] and (y > Y / 2 - 0.30 or abs(x) > X / 2 - 0.30):
                    continue                        # the curbs (their own tops are measured in the bbox)
                z = down(x, y, 1.0)
                if z is not None and z < 0.1:
                    zs.append(z)
        top = [z for z in zs if z > -0.02]
        rec["paving_top_m"] = {"min": round(min(top), 4), "max": round(max(top), 4), "samples": len(top),
                               "rays_into_joints": len(zs) - len(top)}
    if p.name.startswith(PREFIX + "Rail_") and "Post" not in p.name:
        rec["post_spacing_along_rail_m"] = p.extra["post_spacing_along_rail_m"]
    return rec


# ------------------------------------------------------------------------------------------------ main
def all_pieces(only):
    out = []
    for wk in WIDTHS:
        for rk in RISERS:
            out.append(("flight", (wk, rk)))
    for wk in WIDTHS:
        for kind in ("", "L", "SB"):
            out.append(("landing", (wk, kind)))
    for rk in RISERS:
        out.append(("cheek", (rk, None)))
    for L in (1.2, 1.8):
        out.append(("cheek", (None, L)))
    for rk in RISERS:                                   # f2: the single-course low cheek variant
        out.append(("cheek", (rk, None, True)))
    for L in (1.2, 1.8):
        out.append(("cheek", (None, L, True)))
    out.append(("cheek_corner", ()))
    for L in (0.6, 1.2, 1.8):                           # f2: low kerbs (the reference's path edging)
        out.append(("kerb", (L,)))
    out.append(("kerb_corner", ()))
    for rk, bays in (("R050", 1), ("R100", 2), ("R200", 3)):
        out.append(("rail_slope", (rk, bays)))
    for L in (1.2, 1.5, 1.8):
        out.append(("rail_flat", (L,)))
    for W in (1.2, 1.8):
        out.append(("rail_turn", (W,)))
    out += [("rail_end", ()), ("rail_corner", ()), ("lantern_timber", ()), ("lantern_stone", ())]
    if only:
        out = [o for o in out if any(s in o[0] + "_" + "_".join(str(a) for a in o[1]) for s in only)]
    return out


def make(kind, args, coll):
    if kind == "flight":
        return flight(*args)
    if kind == "landing":
        return landing(*args)
    if kind == "cheek":
        return cheek(*args)
    if kind == "cheek_corner":
        return cheek_corner()
    if kind == "kerb":
        return kerb(args[0])
    if kind == "kerb_corner":
        return kerb(corner=True)
    if kind == "rail_slope":
        rk, bays = args
        n = RISERS[rk]
        return rail_span(f"{PREFIX}Rail_Slope_{rk}", n * T, n * R, bays,
                         f"timber handrail on a {rk} flight: {bays} bay(s), {bays + 1} round posts (BOTH ends), top + mid round "
                         f"poles let through the posts")
    if kind == "rail_flat":
        L = args[0]
        return rail_span(f"{PREFIX}Rail_Flat_L{int(round(L * 100)):03d}", L, 0.0, 1,
                         f"flat handrail span {L:.2f} m (landings / paths): top + mid round poles only, hung between "
                         f"the posts of the neighbouring pieces (slope end / corner / end post)", posts=False)
    if kind == "rail_turn":
        W = args[0]
        return rail_span(f"{PREFIX}Rail_Flat_T{int(round(W * 100)):03d}", W - 2 * RAIL_IN, 0.0, 1,
                         f"flat span {W - 2 * RAIL_IN:.4f} m (W - 1/3) across the outside of a turn on a W {W:.1f} "
                         f"landing: poles only, from the corner post to the next flight's first post", posts=False)
    if kind == "rail_end":
        return rail_post(f"{PREFIX}Rail_EndPost", PR, False, "end post: starts or closes a rail run, or carries a flat span between two flat spans")
    if kind == "rail_corner":
        return rail_post(f"{PREFIX}Rail_CornerPost", PR + 0.01, True, "corner post (dia 13 cm) at an outside turn")
    if kind == "lantern_timber":
        return lantern_timber()
    raise ValueError(kind)


def main():
    t0 = time.time()
    assert_owner("DojoStoneKit", "claude")
    only = []
    if "--only" in ARGS:
        only = ARGS[ARGS.index("--only") + 1].split(",")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    jobs = all_pieces(only)
    need_sp = any(k == "lantern_stone" for k, _ in jobs)
    kit = bpy.data.collections.new(COLL)
    sc.collection.children.link(kit)
    SP = None
    if need_sp:                              # the stone-props materials first (it renames a rebuilt library granite)
        SP = S.load_builder(S.STONE_PROPS_BUILDER, "dojo_build_stone_props")
        SP.build_material(SP.GRT)
        for name in SP.MATERIALS:
            if name != SP.GRT:
                SP.build_material(name)
    materials(need_sp)
    pieces, objs, build = [], {}, {}
    for kind, args in jobs:
        t1 = time.time()
        if kind == "lantern_stone":
            p, SP = lantern_stone(kit)
            o = p.part
            bad = 0
        else:
            p = make(kind, args, kit)
            o, bad = S.build_mesh(p, kit, _NoUV1(p.nanite))      # f1: Nanite pieces ship without UV1 (as track 8)
        pieces.append(p)
        objs[p.name] = o
        build[p.name] = {"tris": sum(len(pl.vertices) - 2 for pl in o.data.polygons), "bad_faces": bad,
                         "sec": round(time.time() - t1, 1)}
        print("BUILT", p.name, build[p.name], flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    qa, meas, exp = {}, {}, {}
    for p in pieces:
        o = objs[p.name]
        texel = 5.12 if (p.nanite and "Lantern" not in p.name) else None
        qa[p.name] = S.qa_piece(o, texel=texel, require_uv1=not p.nanite)
        meas[p.name] = measure(o, p)
    hard_total = sum(len(v["hard_fails"]) for v in qa.values())
    print(f"QA stairs: {len(pieces)} pieces, hard fails {hard_total}", flush=True)
    for k, v in qa.items():
        for c in v["hard_fails"]:
            print("  FAIL", k, c["name"], c["detail"][:200], flush=True)
    if "--no-export" not in ARGS and hard_total == 0:
        for p in pieces:
            exp[p.name] = S.export_piece(objs[p.name], K1, lods=not p.nanite)
            print("  export", p.name, exp[p.name]["lod_tris"], exp[p.name].get("lod_qa_hard_fails", ""), flush=True)
        (OUT / "export_report.json").write_text(json.dumps(exp, indent=1, default=str), encoding="utf-8")
    (OUT / "qa_report.json").write_text(json.dumps(qa, indent=1, default=str), encoding="utf-8")
    (OUT / "measure.json").write_text(json.dumps(meas, indent=1, default=str), encoding="utf-8")
    # ------------------------------------------------------------------ catalog (track 'stairs' + its pieces)
    cls_doc = {
        "walk_ramp": "Pawn + Camera + Visibility block; one convex ramp hull through the tread midpoints (walkable)",
        "walk_flat": "Pawn + Camera + Visibility block; flat box top = the paving (walkable); curbs as boxes",
        "wall": "block all; one box per cheek stone (per tread on sloped cheeks), flat walkable tops",
        "kerb": "block all; one box (a 7 cm upstand: GASP steps over it, MaxStepHeight 45 cm)",
        "thin_upright": "Pawn block, Camera ignore, Visibility ignore (thin posts / rails / lanterns: GASP vaults low items)"}
    cat_pieces = {}
    for p in pieces:
        o = objs[p.name]
        e = exp.get(p.name, {})
        cat_pieces[p.name] = {
            "track": TRACK, "class": p.cls, "collision": cls_doc[p.cls], "note": p.note,
            "size_m": meas[p.name]["size_m"], "bbox_min": meas[p.name]["bbox_min"], "bbox_max": meas[p.name]["bbox_max"],
            "tris_lod0": build[p.name]["tris"], "nanite": p.nanite,
            "budget": ("Nanite, LOD0 only; budget <= 250k tris per piece (fallback mesh: UE auto, 1 % / 2k)"
                       if p.nanite else "LOD0 <= 12k tris, LOD1 50 %, LOD2 25 % (screen sizes 1.0 / 0.5 / 0.25)"),
            "lod_tris": e.get("lod_tris"), "slots": [m.name for m in o.data.materials],
            "ucx": [{"name": h["name"], "kind": (p.hull_kinds[i] if i < len(p.hull_kinds) else "block"),
                     "min": h["min"], "max": h["max"]} for i, h in enumerate(meas[p.name]["ucx"])],
            "pivot": "see snaps: every piece's pivot is its 'in' / 'start' / 'base' / centre snap at (0, 0, 0)",
            "snaps": p.snaps, "extra": p.extra,
            "fbx": str(Path(e["path"]).relative_to(S.ROOT)).replace("\\", "/") if e.get("path") else None,
            "qa_hard_fails": len(qa[p.name]["hard_fails"]),
            "measured": {k: v for k, v in meas[p.name].items() if k not in ("ucx", "bbox_min", "bbox_max", "size_m",
                                                                             "slots", "tris")}}
    track = {
        "date": time.strftime("%Y-%m-%d"), "builder": "Scripts/dojo/stonekit/build_stairs.py",
        "reference": "References/Dojo/dojo_landscape_ref.png (the stone stair path, lower left)",
        "grid": {"riser_m": round(R, 5), "tread_m": round(T, 5), "pitch": "1:2 (26.57 deg)",
                 "rise_steps_m": 0.5, "run_per_0.5m_rise_m": 1.0, "widths_m": list(WIDTHS.values()),
                 "flight_runs_m": {k: round(v * T, 4) for k, v in RISERS.items()},
                 "flight_rises_m": {k: round(v * R, 4) for k, v in RISERS.items()},
                 "cheek_thickness_m": TW, "cheek_offset_from_flight_centre_m": "W/2 + 0.20",
                 "rail_line": {"x": "+-(W/2 - 1/6)", "y": "-T/2 (-0.1667) in flight space", "post_base_line":
                               "z = R (y_flight / T + 1/2): the tread midpoints; posts stand mid-tread"},
                 "rail_heights_m": {"top_rail_centre": TOP_Z, "mid_rail_centre": MID_Z, "post_top": POST_H},
                 "below_grade_m": CORE_BOT,
                 "rotation": "any multiple of 90 deg about Z; all pieces are built on +Y (walking up / along +Y)"},
        "how_to_chain": [
            "flight -> flight: next.loc = this.loc + R(rot) (0, run, rise), same rot (a longer straight flight)",
            "flight -> landing (W x W): landing.loc = flight.out + R(rot) (0, W/2, 0)",
            "landing -> flight straight on: flight.loc = landing.loc + R(rot) (0, W/2, 0); right turn: + R(rot) (W/2, 0, 0) "
            "with flight rot = rot - 90; left turn: - R(rot) (W/2, 0, 0) with rot + 90",
            "turn landing (LandingL): at the landing's rot it takes a RIGHT turn (arrive over S, leave over E); for a "
            "LEFT turn give it rot - 90 (arrive S, leave W). f1: every landing is flush paving to its edges (no curbs), "
            "so Landing and LandingL differ only in their flag layout and snaps",
            "switchback (LandingSB): loc = arriving flight.out + R(rot) ((W + 0.4)/2, W/2, 0); the departing flight "
            "pivot = landing.loc + R(rot) ((W + 0.4)/2, -W/2, 0), rot + 180; a Cheek between them at x = 0",
            "rails (the rail line is inset T/2 = 1/6 m from every edge, so corners land exactly on the grid). f1: "
            "Rail_Slope_Rxxx carries the posts at BOTH its ends (a run never cantilevers): place it at flight.loc + "
            "R(rot) (+-(W/2 - 1/6), -1/6, 0). f2: round posts with rounded tops, SQUARED rails housed into them. "
            "Rail_Flat_L{W} / Rail_Flat_T{W} are the two squared rails alone, hung "
            "between posts that other pieces supply: on a landing between two flights the slope below's end post and "
            "the slope above's start post (span W exactly); round an OUTSIDE turn: Rail_Flat_L{W} to a Rail_CornerPost, "
            "then Rail_Flat_T{W} (W - 1/3) turned 90 deg to the next slope's start post; a flat run that starts or ends "
            "the rail (or joins two flat spans) takes a Rail_EndPost. Two slopes chained with no landing between share "
            "one post position: prefer the longer slope piece (R100 + R100 = R200); if both are used the coincident "
            "posts are identical geometry",
            "cheeks: Cheek_Rxxx at flight.loc + R(rot) (+-(W/2 + 0.2), 0, 0): one dressed stone per tread "
            "standing +0.15 over it on a base of rounded wall stones; Cheek_L{W} along landing sides (+0.15 over the "
            "paving); f2: Cheek_Low_Rxxx / Cheek_Low_L{W} = the SINGLE-COURSE low variant (+0.12, 0.22 m in the soil, "
            "no base), same placement; CheekCorner where two meet at 90 deg. Moss sits where the cheek meets the soil. "
            "Reference-matching paths use the cheek on the cliff side only (or none) and natural rock",
            "kerbs (f2): Stair_Kerb_L{060,120,180} = low edging of squared blocks (+0.07 over the path), pivot on its "
            "centre line at path level, running +Y, outer (soil) side +X: along a landing / path edge at "
            "x = +-(W/2 + 0.115) (rot 0 on the +X edge, rot 180 from the far end on the -X edge); Stair_Kerb_Corner "
            "closes two kerbs at 90 deg. The reference edges its paths and landings with them on the open side",
            "lanterns: Lantern_Timber is the reference's path lantern: ONE per landing (never two side by side), on the "
            "cliff side, >= 0.5 m clear of any rail line and of any rail's plan (its eave is 0.44 m wide, top 1.31 m: a "
            "rail must never run into its roof); Lantern_Stone is a kit extra, not in the reference path"],
        "materials": {
            **{m: {"library": "Granite", "kit_variant": True, "tint_linear": list(r["tint"]),
                   "flatten_to_mean": r["flat"], "normal_strength": r["normal"],
                   "mean_linear": [round(a * b, 5) for a, b in zip(S.TEX_MEAN, r["tint"])],
                   "moss": {"source": "'Wear' vertex colour ALPHA", "colour_linear": list(S.KIT_MOSS)},
                   "recipe": "M_DJ_Lib_Opaque instance (Tint, FlattenToMean, MeanColour, moss lerp on VertexColor.A) "
                             "with these numbers; UseWear on; TileM (4, 4)",
                   "textures": [f"Exports/DojoKit/Materials/Textures/T_DJ_Granite_{x}.png" for x in ("BC", "N", "ORM")]}
               for m, r in S.KIT_MATS.items()},
            "use": {SG: "treads, landing flags, kerb tops (upward faces): LIGHTER walked tops, calm", SR: "risers, "
                    "step ends, kerb sides, undersides: darker, rougher", FS: "cheeks, flight sides, landing sides "
                    "(the wall's rounded stone)", JE: "joint core (dark)"},
            "wear_colours": "Wear RGBA per corner: R grime (AO + per-stone tone offset + darker undersides), G edge wear "
                            "(+ light weathered tops on upward faces), B ground dirt, A moss (joints and ledges)",
            **{m: {"library": b, "override": {k: (list(v) if isinstance(v, tuple) else v) for k, v in ov.items()},
                   "recipe": "MI of the library master of %s with Tint = override.tint%s" % (
                       b, "; EmissiveIntensity scaled by override.emission_strength / 5 from the library's"
                       if "emission_strength" in ov else "")}
               for m, (b, ov) in S.LIB_VARIANTS.items()},
            "use_timber": {TD: "rails, posts, lantern body (darker weathered timber; + %s on end grain)" % TDE,
                           IR: "lantern hood + finial (charcoal, no rust)", LG: "lantern panes (warm amber, a separate "
                           "slot; light = a separate UE point light)"},
            "M_DJ_Granite_Tri / M_DKP_Stone_*": "the stone lantern keeps the courtyard lantern's own slots"},
        "gasp": "MaxStepHeight 45 cm, walkable 44.77 deg (GASP_TRAVERSAL.md): risers 16.7 cm, ramp hull 26.57 deg, "
                "landing tops flat, cheek tops flat boxes",
        "qa_hard_fails": hard_total, "pieces": sorted(p.name for p in pieces),
        "exported": bool(exp), "seconds": round(time.time() - t0, 1)}
    if not only:
        S.merge_catalog(TRACK, {"track": track, "pieces": cat_pieces}, PREFIX)
    else:
        (OUT / "catalog_partial.json").write_text(json.dumps({"track": track, "pieces": cat_pieces}, indent=1),
                                                  encoding="utf-8")
    # ------------------------------------------------------------------ blends
    for o in list(kit.objects):
        if o.parent is None and o.name in objs:
            o.hide_render = False
    bpy.ops.wm.save_as_mainfile(filepath=str(BUILD_BLEND))
    print("saved", BUILD_BLEND, flush=True)
    if not only and "--no-merge" not in ARGS:
        merge_into_blend()
    print("DONE seconds", round(time.time() - t0, 1), flush=True)


class _NoUV1:
    """sk_shared.build_mesh calls K1.add_uv1(obj): skipped for Nanite pieces (Lumen, no lightmaps; UE's Generate
    Lightmap UVs if static lighting is ever used), kit 1's checked packer otherwise."""

    def __init__(self, nanite):
        self.nanite = nanite

    def add_uv1(self, obj):
        if not self.nanite:
            K1.add_uv1(obj)

    def fix_lod(self, obj):
        K1.fix_lod(obj)


def merge_into_blend():
    """Assets/Dojo/DojoStoneKit.blend holds both tracks: under the file lock, open it (if it exists), drop the old
    StoneKit_Stairs collection, append the fresh one from the build blend, fold duplicate library datablocks back
    onto the originals, save."""
    with S.file_lock(S.BLEND):
        if S.BLEND.exists():
            bpy.ops.wm.open_mainfile(filepath=str(S.BLEND))
            S.drop_collection_for_append(COLL)          # f2: objects, meshes, own materials, orphans
            with bpy.data.libraries.load(str(BUILD_BLEND), link=False) as (src, dst):
                dst.collections = [COLL]
            for c in dst.collections:
                bpy.context.scene.collection.children.link(c)
            S.fold_into_kit()          # f2: the kit's own recipes take the NEW copy, library data folds as before
            bpy.ops.outliner.orphans_purge(do_recursive=True) if bpy.context.area else None
            bpy.ops.wm.save_as_mainfile(filepath=str(S.BLEND))
        else:
            S.BLEND.parent.mkdir(parents=True, exist_ok=True)
            bpy.ops.wm.save_as_mainfile(filepath=str(S.BLEND), copy=True)
    print("merged into", S.BLEND, flush=True)


main()
