"""STONE KIT, TRACK 8: the terrace retaining wall (ishigaki style) under the dojo compound.

Reference: References/Dojo/dojo_landscape_ref.png (REFERENCE_LOG.md, "Landscape reference"): the dojo terrace is held by
a tall dry-laid wall of rounded, pillow-faced granite stones in rough courses, dark deep joints with moss, a top course
of squarer dressed blocks with flat tops, and the compound's plaster wall standing on it. Measured on the reference
(WorkFiles/dojo/build/stonekit/renders/wall/refcrops/grid_*.png; 47-50 px/m at the gate steps from a 0.16 m riser,
17-25 px/m at the terrace from the compound wall's 1.3-1.9 m plaster band): body stones 0.28-0.55 m wide and 0.28-0.47 m
tall, many upright; top blocks about 0.34 x 0.24-0.28 m; joints 2-4 cm. The style anchor is the dojo's own footing
(kit 1 round 3): kit1_geo.pillow_face stones and rough_block dressed blocks in M_DK_FootingStone with moss by the 'Wear'
alpha, the M_DK_JointEarth core in the joints, the library Granite for walking stones (the gate apron).

KIT GRID (every piece; metres; Blender +Z up, Unreal = x 100 cm):
  * Z = 0 is the TERRACE GRADE (the dojo's ground plane; the coping's flat top). Walls hang DOWN from it.
  * Local X runs along the wall; the wall FACE looks to local -Y (the valley); the terrace fill is +Y.
  * PIVOT = the face line at terrace grade at the module's start (the coping's outer top arris, x = 0).
  * Plan grid 1 m: straight modules 2 m / 4 m; corners take 1 m of each face; the next piece's pivot is a snap point.
  * Heights H 2 / 3 / 4 / 6 m = terrace grade to the nominal foot. Every wall piece continues BURY 0.40 m below its
    foot (buried stones), so it can sink into uneven ground without showing a bottom edge.
  * Batter (one profile for every piece, so modules of any height share a face): the face stands d(s) out from the
    top line at depth s below grade, d(s) = 0.10 s + 0.035 s^2 (concave: 6 deg from vertical at the top, 13 at 2 m,
    20 at 4 m, 27.5 at 6 m; set-back 0.34 / 0.62 / 0.96 / 1.86 m at the 2 / 3 / 4 / 6 m foot).
  * Courses: one global course table (COURSE_S) below the 0.26 m coping, so every module end meets its neighbour course
    for course; module ends INTERLOCK (teeth): course k runs TOOTH 0.18 m past (even k) or short of (odd k) the grid
    line, the same rule at both ends of every piece.
  * Outside corners: sangi-zumi (long and short dressed corner blocks alternating course by course) and the upswept
    corner (extra outward flare at the arris, F(s) = 0.008 s^2, fading to 0 one metre along each face).

PIECES (SM_DKT_Wall*):
  Wall_{2m,4m}_H{2,3,4,6}          straight modules (coping + body)
  Wall_CornerOut_H*, _CornerIn_H*  corners (1 m of each face); next pivot (1, +-1, 0), yaw +-90
  Wall_EndL_H*, _EndR_H*           wall ends returning 1.2 m into the slope (outside corner + a buried return)
  Wall_StairOpening_H{2,3,4}       a 4 m module pierced by a straight stair: a stone bastion with sode-ishi curbs and
                                   a 1.9 m clear flight (riser H/n about 0.167, tread 0.32) from grade to the foot
  WallCoping_{2m,4m}, WallCoping_CornerOut / _CornerIn   the top course alone (terrace edge on rock / low ground)
  WallFoot_{2m,4m}, WallFoot_CornerOut_H*, _CornerIn_H*  base course + buried-stone skirt; pivot = the wall's
                                   "foot" snap point (the face line at the nominal foot)

f1 FIX ROUND (judge 6/10): face stones are irregular 5-7 sided polygons nested course to course with diagonal joints
(sk_shared.lay_courses), flat dressed faces with small crisp arrises (sk_shared.dressed_stone), joints ~1-2 cm, no packing
chips; the kit granite family (sk_shared.KIT_MATS: pale grey-beige M_DKT_WallGranite, M_DKT_JointDark core, per-stone
tone / light tops / dark undersides / moss in joints and on ledges in the Wear colours, box-projected UVs); the corner
flare is gentler and never shears a stone; H6 inside corners take 3 m arms; the foot skirt is sparse flat angular
rubble; the stair opening uses track 9's f1 steps (1-2 slabs, nosing overhang, light treads / dark risers).

f2 FIX ROUND (the owner's reading of the reference; f1 went the wrong way): ROUNDED pillow-faced stones again (round 0's
construction, sk_shared.lay_rounded / pillow_stone) with more varied sizes and aspect (upright ovals, long stones), dark
deep 2-4 cm joints (M_DKT_JointDark), MID-GREY granite, moss in the bed joints and on top edges; the DEFAULT profile is
a LOW, NEAR-VERTICAL straight batter d(s) = 0.10 s (1:10) with no corner flare; the concave castle sweep (0.10 s +
0.035 s^2, upswept corners) survives only as the optional *_Sweep variant set (straight modules, corners, ends and
their corner feet at H 3 / 4 / 6); squarer, slightly larger, darker coping (M_DKT_CopeGranite, 0.28 m) with moss on
top; the foot is ONE continuous, level, buried footing course (no loose rubble, no skirt).

Run: blender -b --factory-startup --python Scripts/dojo/stonekit/build_wall.py -- [--only A,B] [--no-export] [--quick]
Out: Exports/DojoKit/StoneKit/SM_DKT_Wall*.fbx, WorkFiles/dojo/build/stonekit/wall/{qa,export,build}_report.json,
     kit_catalog.json (tracks.wall + the SM_DKT_Wall* pieces), Assets/Dojo/DojoStoneKit.blend (collection
     StoneKit_Wall), WorkFiles/dojo/build/stonekit/wall/DojoStoneKit_wall.blend (this track alone, for the renders)
"""
import json
import math
import random
import sys
import time
from pathlib import Path

import bpy
from mathutils import Matrix, Vector, noise

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sk_shared as sk  # noqa: E402
from sk_shared import G, djm, clamp01  # noqa: E402
from pipeline.lock import assert_owner  # noqa: E402
from pipeline.qa_check import qa_check  # noqa: E402

K1 = sk.load_builder(sk.KIT1_BUILDER, "dojo_build_kit1")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ONLY = set(ARGS[ARGS.index("--only") + 1].split(",")) if "--only" in ARGS else None
QUICK = "--quick" in ARGS
TRACK = "wall"
PREFIX = "SM_DKT_Wall"
OUT = sk.WORK / "wall"
TRACK_BLEND = OUT / "DojoStoneKit_wall.blend"

# f1 (judge 6/10, delta 2): the kit-wide granite family from sk_shared.KIT_MATS (pale grey-beige, moss by Wear.A, per-
# stone tone in the Wear colours) replaces kit 1's darker footing tint and its pebbled joint earth on this track
FS, JE, GR = "M_DKT_WallGranite", "M_DKT_JointDark", K1.GR
CP = "M_DKT_CopeGranite"                 # f2: the coping / cap course, a little darker than the face stones

# ------------------------------------------------------------------------------------------------ grid + profile
HEIGHTS = (2, 3, 4, 6)
SWEEP_HEIGHTS = (3, 4, 6)                # f2: the optional concave-sweep variant set
BURY = 0.40
COPE_H = 0.34                            # f2r2: the trace's cap course ~1.1 x the body stone height (squarer, slightly larger)
COPE_D = 0.55
PA, PB = 0.10, 0.035
PROFILE = {"kind": "straight", "suffix": ""}   # f2: "straight" (default, 1:10) or "sweep" (the r0 / f1 castle curve)
TOOTH = 0.18
FLARE_E, FLARE_R = 0.005, 1.4            # f1: gentler (0.18 m at a 6 m foot) and wider, so no stone is warped
CORE_IN = 0.100             # the joint core's face behind the stone rims
CORE_BACK = 0.70            # the core's back plane behind the top face line
HULL_BACK = 0.80            # collision reaches this far behind the face line (into the fill)
CORNER_ARM = 1.0
END_RETURN = 1.2
# stair opening (track 9 continues the path at the foot snap)
TREAD = 1.0 / 3.0          # track 9's stair grid (build_stairs.py): riser 1/6, tread 1/3, pitch 26.57 deg
RISER_T = 1.0 / 6.0
NOSE = 0.022                # nosing proud of its riser line (track 9)
FLIGHT = (1.10, 2.90)       # clear width 1.80 = track 9's W180 flights / landings / rails
CURB_W = 0.40
CURB_H = 0.30
CURB_UP = 0.12              # curb top above the nosing line
SIDE_A = 0.05               # the bastion side faces' batter d_side(s') = 0.05 s' (s' below the curb)


def d(s):
    """The face set-back at depth s: f2 default = a straight 1:10 batter; the Sweep variants keep the concave curve."""
    s = max(0.0, s)
    if PROFILE["kind"] == "sweep":
        return PA * s + PB * s * s
    return PA * s


def flare(s):
    """The upswept outside corner: only on the Sweep variants (the straight default follows the plain batter)."""
    if PROFILE["kind"] != "sweep":
        return 0.0
    return FLARE_E * max(0.0, s) ** 2


def _course_table():
    pat = [1.0, 0.86, 1.14, 0.92, 1.08, 0.88, 1.12, 0.96]
    out, s, k = [COPE_H], COPE_H, 0
    while s < 7.0:
        s += (0.34 + 0.030 * s) * pat[k % len(pat)]        # f3: body stones ~0.34 x 0.42 (f2 +30 %: the judge delta the
        # reference confirms: the lower terrace wall's near end, beside the 0.17 m gate risers, shows ~0.4-0.55 m courses)
        out.append(round(s, 4))
        k += 1
    return out


COURSE_S = _course_table()


def tooth(k):
    return TOOTH if k % 2 == 0 else -TOOTH


def smooth01(x):
    x = clamp01(x)
    return x * x * (3 - 2 * x)


def rot_mat(deg, loc=(0, 0, 0)):
    return Matrix.Translation(Vector(loc)) @ Matrix.Rotation(math.radians(deg), 4, "Z")


# ------------------------------------------------------------------------------------------------ faces
class Face:
    """A battered face: top line from O along t; outward o = t turned -90 deg; P(a, z) = O + t a + o D(a, z) + z."""

    def __init__(self, O, t, D=None):
        self.O = Vector(O)
        self.t = Vector(t).normalized()
        self.o = Vector((self.t.y, -self.t.x, 0.0))
        self.D = D if D is not None else (lambda a, z: d(-z))

    def P(self, a, z):
        return self.O + self.t * a + self.o * self.D(a, z) + Vector((0.0, 0.0, z))

    def frame(self, a, z, h=1e-3):
        pa = (self.P(a + h, z) - self.P(a - h, z)) / (2 * h)
        pz = (self.P(a, z + h) - self.P(a, z - h)) / (2 * h)
        t = pa.normalized()
        n = t.cross(pz).normalized()
        return t, n, n.cross(t).normalized()


def stone_step(w, h):
    return 0.030 if QUICK else min(0.032, max(0.021, 0.018 + 0.022 * min(w, h)))


def face_stone(g, F, poly_az, rng, seed, kind="body", proud_off=0.0):
    """f2r2: one ROUNDED pillow-faced stone (sk_shared.pillow_stone_v2: per-corner radius, asymmetric crown, tilt)."""
    return sk.pillow_stone_v2(g, F, poly_az, rng, seed, FS, depth=0.24)


def face_stone_f1(g, F, poly_az, rng, seed, kind="body", proud_off=0.0):
    """f1 (kept for reference, unused: the owner rejected the flat many-sided look): a DRESSED face stone."""
    return sk.dressed_stone(g, F, poly_az, rng, seed, FS, depth=0.22, proud=proud_off,
                            step=0.034 if QUICK else 0.028)


def face_stone_r0(g, F, poly_az, rng, seed, kind="body", proud_off=0.0):
    """r0 (kept for reference, unused): one pillow-faced stone on face F from a convex outline [(a, z)], built on the
    face's tangent plane at its centroid (kit1_geo.pillow_face; the kit-1 footing construction)."""
    ac = sum(p[0] for p in poly_az) / len(poly_az)
    zc = sum(p[1] for p in poly_az) / len(poly_az)
    P0 = F.P(ac, zc)
    t, n, up = F.frame(ac, zc)
    poly = []
    for (a, z) in poly_az:
        q = F.P(a, z) - P0
        poly.append((q.dot(t), q.dot(up)))
    if abs(G.poly_area(poly)) < 0.0025:
        return 0
    w = max(p[0] for p in poly) - min(p[0] for p in poly)
    h = max(p[1] for p in poly) - min(p[1] for p in poly)
    s_ = min(w, h)
    if s_ < 0.045:
        return 0
    uv = (rng.uniform(0, 1), rng.uniform(0, 1))
    if kind == "pack":        # small packing stones in the joint junctions, set back, flat and angular
        r = G.pillow_face(g, poly, P0, t, n, 0.12, 0.002 + proud_off, rng.uniform(0.003, 0.006), seed, FS,
                          edge=min(0.008, 0.25 * s_), rough=0.003, fine=0.0015, step=0.013 if not QUICK else 0.02,
                          rounds=0, keep=0.18, crown=3.5, wobble=0.0, peak_off=0.25, uv_off=uv)
    else:                     # body stones: rounded rectangles / ovals, a full pillow, granular
        r = G.pillow_face(g, poly, P0, t, n, 0.24, 0.018 + rng.uniform(0.0, 0.020) + proud_off,
                          min(0.040, max(0.015, 0.07 * s_ + rng.uniform(-0.004, 0.006))), seed, FS,
                          edge=rng.uniform(0.018, 0.028), rough=rng.uniform(0.005, 0.0075), fine=0.0022,
                          step=stone_step(w, h), rounds=2, keep=rng.uniform(0.14, 0.24), crown=rng.uniform(2.0, 3.0),
                          wobble=0.004, peak_off=0.12, uv_off=uv)
    return int(r is not None)


def _cut(poly, i, c):
    """Cut corner i of a convex polygon by c along both edges."""
    m = len(poly)
    p, pa, pb = Vector(poly[i]), Vector(poly[i - 1]), Vector(poly[(i + 1) % m])
    ea, eb = (pa - p), (pb - p)
    ca, cb = min(c, 0.45 * ea.length), min(c, 0.45 * eb.length)
    q1, q2 = p + ea.normalized() * ca, p + eb.normalized() * cb
    return poly[:i] + [tuple(q1), tuple(q2)] + poly[i + 1:]


class Boundary:
    """A course boundary s(a): the global course depth, wandering +-amp between the pins (piece ends, corners)."""

    def __init__(self, s0, a_lo, a_hi, pins, rng, amp):
        self.s0, self.pins = s0, pins
        self.cp = []
        a = a_lo - 0.6
        while a < a_hi + 0.6:
            self.cp.append((a, rng.uniform(-amp, amp)))
            a += rng.uniform(0.55, 0.85)
        self.cp.append((a, rng.uniform(-amp, amp)))

    def __call__(self, a):
        cp = self.cp
        w = 0.0
        for i in range(len(cp) - 1):
            if cp[i][0] <= a <= cp[i + 1][0]:
                f = (a - cp[i][0]) / (cp[i + 1][0] - cp[i][0])
                w = cp[i][1] + (cp[i + 1][1] - cp[i][1]) * f
                break
        tp = min([smooth01((abs(a - p) - 0.15) / 0.45) for p in self.pins] + [1.0])
        return self.s0 + w * tp


def _widths(total, first, last, wmean, rng):
    """Stone widths summing to `total`: an optional forced first / last width, the rest about wmean each."""
    if total <= 0.0:
        return []
    ws_f = [rng.uniform(*first)] if first else []
    ws_l = [rng.uniform(*last)] if last else []
    if sum(ws_f) + sum(ws_l) > total - 0.22:
        return [total]
    rest = total - sum(ws_f) - sum(ws_l)
    m_ = max(1, int(round(rest / wmean)))
    raw = [rng.uniform(0.60, 1.40) for _ in range(m_)]
    k = rest / sum(raw)
    return ws_f + [w * k for w in raw] + ws_l


def pad_p_for(s_bot):
    """f3: the chance of a moss cushion in the bed joint over a stone at depth z (the owner: moss and dirt in the bed
    joints, denser low down and under the cap; none below grade)."""
    z_foot = -(s_bot - BURY)

    def f(a, z):
        if z < z_foot + 0.05:
            return 0.0
        low = clamp01((1.3 - (z - z_foot)) / 1.3)
        top = 1.0 if z > -(COPE_H + 0.30) else 0.0
        return 0.30 + 0.30 * low + 0.15 * top
    return f


def lay_face(g, F, s_top, s_bot, lohi, pins, seed, clip=None, pack=False, force_first=None, force_last=None):
    """f3: rounded pillow stones in the global courses (COURSE_S) with FITTED outlines (Scripts/stone/stone_layout
    .coursed_fitted: Y-junctions, the measured mix, uprights through two courses, leaning joints, wandering beds), 1.1-
    1.5 cm between rims, and moss cushions in some bed joints (sk_shared.lay_measured)."""
    return sk.lay_measured(g, F, COURSE_S, s_top, s_bot, lohi, pins, seed, face_stone, clip=clip,
                           force_first=force_first, force_last=force_last, zone="body", method="fitted",
                           pad_p=pad_p_for(s_bot))


def lay_face_r0(g, F, s_top, s_bot, lohi, pins, seed, clip=None, pack=True, force_first=None, force_last=None):
    """r0 (kept for reference, unused): lay the body stones of one face between depths s_top and s_bot in the global
    courses (COURSE_S).
    lohi(k, s_a, s_b) -> ((lo_top, lo_bot), (hi_top, hi_bot)): the a of the course's left / right end line at the
    course's top / bottom depths (teeth, corner blocks, corner lines). pins: a values where the course boundaries stay
    exactly on the global table (piece ends). clip: optional half planes (ka, kz, c) in (a, z): keep ka a + kz z <= c.
    force_first / force_last: {course parity: (wmin, wmax)}: the first / last stone's width (long-short corners).
    Junctions (a joint meeting a course boundary) get a notch in both neighbours and a small packing stone about half
    the time. Returns the number of stones."""
    rng = random.Random(seed)
    ks = [k for k in range(len(COURSE_S) - 1) if COURSE_S[k] < s_bot - 0.02 and COURSE_S[k + 1] > s_top + 0.02]
    if not ks:
        return 0

    def sab(k):
        return max(COURSE_S[k], s_top), min(COURSE_S[k + 1], s_bot)
    bounds = {}
    for k in ks + [ks[-1] + 1]:
        s0 = COURSE_S[k]
        if s0 <= s_top + 1e-6 or s0 >= s_bot - 1e-6:
            s0 = min(max(s0, s_top), s_bot)
            bounds[k] = (lambda a, s0=s0: s0)
        else:
            bounds[k] = Boundary(s0, -9.0, 9.0, pins, rng, 0.060 * (1 + 0.03 * s0))
    # tall stones: through two courses, away from the pins
    talls = {}
    for k in ks[:-1]:
        if k % 2 or k + 1 not in ks or COURSE_S[k + 2] > s_bot + 0.05:
            continue                                  # pairs (0,1), (2,3), ...: two talls never share a course
        (lo1, _), (hi1, _) = lohi(k, *sab(k))
        (lo2, _), (hi2, _) = lohi(k + 1, *sab(k + 1))
        lo, hi = max(lo1, lo2) + 0.45, min(hi1, hi2) - 0.45
        a = lo + rng.uniform(0.0, 0.9)
        lst = []
        while a + 0.30 < hi:
            if any(abs(a - p) < 0.5 for p in pins):
                a += 0.35
                continue
            if rng.random() < 0.30:
                w = rng.uniform(0.46, 0.66) * (1 + 0.03 * COURSE_S[k])
                if a + w > hi:
                    break
                jl, jr = rng.uniform(-0.02, 0.02), rng.uniform(-0.02, 0.02)
                lst.append(((a + jl, a - jl), (a + w + jr, a + w - jr)))
                a += w + rng.uniform(0.9, 1.8)
            else:
                a += rng.uniform(0.6, 1.2)
        if lst:
            talls[k] = lst

    def clipped(poly):
        if not clip:
            return poly
        for (ka, kz, c_) in clip:
            poly = G.convex_clip(poly, ka, kz, c_)
            if len(poly) < 3:
                return None
        poly = G.clean_poly(poly)
        return poly if len(poly) >= 3 else None

    n = 0
    packs = []
    for k in ks:
        sa, sb = sab(k)
        s_up, s_dn = bounds[k], bounds[k + 1]
        (lo_t, lo_b), (hi_t, hi_b) = lohi(k, sa, sb)
        if hi_t - lo_t < 0.08 and hi_b - lo_b < 0.08:
            continue
        blocks = sorted(list(talls.get(k, [])) + list(talls.get(k - 1, [])), key=lambda b: b[0][0])
        segs, left, lkind = [], (lo_t, lo_b), "end"
        for (bl, br) in blocks:
            segs.append((left, bl, lkind, "tall"))
            left, lkind = br, "tall"
        segs.append((left, (hi_t, hi_b), lkind, "end"))
        wmean = 0.44 * (1.0 + 0.045 * sa)
        for si, (L, R, lk, rk) in enumerate(segs):
            if min(R[0] - L[0], R[1] - L[1]) < 0.06:
                continue
            first = force_first.get(k % 2) if (force_first and si == 0 and lk == "end") else None
            last = force_last.get(k % 2) if (force_last and si == len(segs) - 1 and rk == "end") else None
            total = (R[0] + R[1]) / 2 - (L[0] + L[1]) / 2
            ws = _widths(total, first, last, wmean, rng)
            lines = [(L[0], L[1], lk)]
            a = 0.0
            for w in ws[:-1]:
                a += w
                f = a / total
                j = rng.uniform(-0.035, 0.035)
                lines.append((L[0] + (R[0] - L[0]) * f + j, L[1] + (R[1] - L[1]) * f - j, "joint"))
            lines.append((R[0], R[1], rk))
            for (lt, lb, lkind_), (rt, rb, rkind_) in zip(lines, lines[1:]):
                if min(rt - lt, rb - lb) < 0.07:
                    continue
                quad = [(lb, -s_dn(lb)), (rb, -s_dn(rb)), (rt, -s_up(rt)), (lt, -s_up(lt))]
                poly = list(quad)
                # junction notches (deterministic per junction, so both neighbours agree): corners 0 BL, 1 BR (the
                # notch rises from the boundary below), 2 TR, 3 TL (it hangs from the boundary above)
                for ci, kind_ in ((3, lkind_), (2, rkind_), (1, rkind_), (0, lkind_)):
                    if not pack or kind_ != "joint":
                        continue
                    key = (round(quad[ci][0], 3), round(quad[ci][1], 3))
                    if -key[1] < s_top + 0.03 or -key[1] > s_bot - 0.03:
                        continue                     # no notch on the piece's top / buried bottom edge
                    r_ = random.Random((hash(key) & 0xFFFFFF) ^ seed)
                    if r_.random() < 0.40:
                        c = r_.uniform(0.07, 0.12)
                        poly = _cut(poly, ci, c)
                        packs.append((key, c, 1.0 if ci < 2 else -1.0))
                if rng.random() < 0.45:          # an irregular outline: one small corner knocked off
                    ci = rng.randrange(len(poly))
                    poly = _cut(poly, ci, rng.uniform(0.025, 0.06))
                poly = G.clean_poly(poly)
                inner = G.inset_convex(poly, rng.uniform(0.005, 0.009))
                if inner is None:
                    continue
                inner = clipped(inner)
                if inner is None:
                    continue
                n += face_stone_r0(g, F, inner, rng, seed * 7919 + n * 31 + k, "body")
    for k, lst in talls.items():
        for (bl, br) in lst:
            s_up, s_dn = bounds[k], bounds[k + 2]
            quad = [(bl[1], -s_dn(bl[1])), (br[1], -s_dn(br[1])), (br[0], -s_up(br[0])), (bl[0], -s_up(bl[0]))]
            inner = G.inset_convex(G.clean_poly(quad), rng.uniform(0.005, 0.009))
            if inner is None:
                continue
            inner = clipped(inner)
            if inner is None:
                continue
            n += face_stone(g, F, inner, rng, seed * 131 + n, "body")
    seen = set()
    for (key, c, side) in packs:
        if key in seen:
            continue
        seen.add(key)
        a_j, z_j = key
        r_ = random.Random((hash(key) & 0xFFFFFF) ^ (seed * 3))
        rad = 0.50 * c
        cz = z_j + side * 0.40 * c
        m = r_.choice((4, 5, 5))
        ph = r_.uniform(0, 6.283)
        ang = sorted(ph + 6.283 * (i + r_.uniform(-0.2, 0.2)) / m for i in range(m))
        pts = [(a_j + 1.25 * rad * r_.uniform(0.65, 1.05) * math.cos(t_),
                cz + 0.85 * rad * r_.uniform(0.65, 1.05) * math.sin(t_)) for t_ in ang]
        if clip and any(ka * q[0] + kz * q[1] > c_ for q in pts for (ka, kz, c_) in clip):
            continue
        n += face_stone(g, F, pts, r_, seed * 17 + len(seen), "pack", proud_off=-0.010)
    return n


def core_slab(g, F, a_lo, a_hi, z_top, z_bot, back=CORE_BACK, mat=None, dz=0.25):
    """The joint core behind the stones (kit 1's M_DK_JointEarth): a closed slab whose front follows the face F at
    CORE_IN behind the rims, from a_lo(z) to a_hi(z) (callables), back plane `back` behind the top line."""
    mat = mat or JE
    dz = min(dz, 0.09)                     # f2r2: a dense, noisy front (soil pockets 6-14 cm behind the face)
    nz = max(2, int(math.ceil((z_top - z_bot) / dz)))
    zs = [z_top - (z_top - z_bot) * i / nz for i in range(nz + 1)]
    span = max(abs(a_hi(z_top) - a_lo(z_top)), abs(a_hi(z_bot) - a_lo(z_bot)))
    na = max(6, int(math.ceil(span / 0.09)))
    verts, faces = [], []
    grid = {}

    def fp(u, z):
        a = a_lo(z) + (a_hi(z) - a_lo(z)) * u
        q = F.P(a, z) - F.o * CORE_IN
        pock = 0.028 * noise.noise(q * 3.1 + Vector((4.1, 0.7, 2.9))) + 0.012 * noise.noise(q * 9.0 + Vector((1.3, 5.5, 0.2)))
        return q + F.o * pock

    def bp(u, z):
        a = a_lo(z) + (a_hi(z) - a_lo(z)) * u
        return F.O + F.t * a - F.o * back + Vector((0, 0, z))

    def vid(kind, i, j):
        key = (kind, i, j)
        if key not in grid:
            u = j / na
            grid[key] = len(verts)
            verts.append(fp(u, zs[i]) if kind == "f" else bp(u, zs[i]))
        return grid[key]

    for i in range(nz):
        for j in range(na):
            faces.append((vid("f", i, j), vid("f", i + 1, j), vid("f", i + 1, j + 1), vid("f", i, j + 1)))
            faces.append((vid("b", i, j), vid("b", i, j + 1), vid("b", i + 1, j + 1), vid("b", i + 1, j)))
        faces.append((vid("f", i, 0), vid("b", i, 0), vid("b", i + 1, 0), vid("f", i + 1, 0)))
        faces.append((vid("f", i, na), vid("f", i + 1, na), vid("b", i + 1, na), vid("b", i, na)))
    for j in range(na):
        faces.append((vid("f", 0, j), vid("f", 0, j + 1), vid("b", 0, j + 1), vid("b", 0, j)))
        faces.append((vid("f", nz, j), vid("b", nz, j), vid("b", nz, j + 1), vid("f", nz, j + 1)))
    # orient outward: test one front face against the outward normal
    a_, b_, c_ = verts[faces[0][0]], verts[faces[0][1]], verts[faces[0][2]]
    if (b_ - a_).cross(c_ - a_).dot(F.o) < 0:
        faces = [tuple(reversed(f)) for f in faces]
    g.add(verts, faces, mat, (F.t, -F.o, Vector((0, 0, 1))))
    return g


# ------------------------------------------------------------------------------------------------ dressed blocks
def sheared_block(g, c, axes, half, r_round, seed, mat, shear_fn, bulge=0.010, rough=0.0022, fine=0.0007, n=(10, 8, 6)):
    """kit1_geo.rough_block (the kit-1 quoins / dressed course) whose vertices are then displaced by shear_fn(v) (the
    batter), so its faces follow the wall face."""
    v0 = len(g.v)
    G.rough_block(g, c, axes, half, r_round, seed, mat, bulge=bulge, rough=rough, fine=fine, n=n)
    for i in range(v0, len(g.v)):
        g.v[i] = g.v[i] + shear_fn(g.v[i])
    return g


def coping_run(g, F, a0, a1, seed, depth=COPE_D, ends=("flat", "flat")):
    """The top course along face F over [a0, a1]: squared dressed blocks (0.36-0.62 m long, COPE_H tall, `depth`
    deep), flat walkable tops at grade, pillowed faces 1-2 cm proud of the batter."""
    rng = random.Random(seed)
    L = a1 - a0
    m = max(1, int(round(L / 0.40)))                  # f2r2: squarer cap stones (0.34-0.46 x 0.34), CopeGranite
    ws = [rng.uniform(0.76, 1.24) for _ in range(m)]
    k = L / sum(ws)
    a = a0
    zc = -COPE_H / 2
    for i, w in enumerate(ws):
        w *= k
        gap = rng.uniform(0.012, 0.018)
        l0 = a + (gap / 2 if (i > 0 or ends[0] != "none") else 0.0)
        l1 = a + w - (gap / 2 if (i < m - 1 or ends[1] != "none") else 0.0)
        pr = rng.uniform(0.010, 0.020)
        ac = (l0 + l1) / 2
        base = F.O + F.t * ac
        cc = base + F.o * (pr - depth / 2) + Vector((0, 0, zc + 0.001))
        # D axis into the wall: the front (pillowed) face is -D = outward
        shear = (lambda v, F=F: F.o * (d(-v.z) - d(COPE_H / 2)))
        sheared_block(g, cc, (F.t, -F.o, Vector((0, 0, 1))), ((l1 - l0) / 2, depth / 2, COPE_H / 2 - 0.004),
                      0.024, seed * 101 + i, CP, shear, bulge=rng.uniform(0.006, 0.012), rough=0.0024, fine=0.0008,
                      n=(max(8, int((l1 - l0) / 0.045)), 10, 8))
        sk.layout_add("cap", [(l0, -COPE_H), (l1, -COPE_H), (l1, 0.0), (l0, 0.0)], None, None, "cap",
                      z_top=0.0, z_bot=-COPE_H)
        # f3: moss cushions on the cap tops (the owner: squarer cap stones "with moss on top"): along some of the top
        # joints between cap blocks, from the front arris back into the terrace, low (1-2 cm) on the walkable top
        if i > 0 and rng.random() < 0.55:
            TF = sk.PlaneFace(F.O + F.t * (a - 0.0), -F.o, Vector((0.0, 0.0, 1.0)))
            TF.frame = (lambda a_, z_, TF=TF: (TF.t, TF.n, TF.up))
            back = rng.uniform(0.18, depth - 0.06)
            sk.moss_pad(g, TF, [(rng.uniform(0.0, 0.05), 0.0), (back, rng.uniform(-0.02, 0.02))], rng,
                        seed * 7 + i, width=(0.020, 0.034), thick=(0.008, 0.015), front=(-0.004, 0.0))
        a += w
    return m


# ------------------------------------------------------------------------------------------------ collision
def band_z(h):
    zs = [0.0, -COPE_H]
    z = -COPE_H
    while z > -h - BURY + 1e-6:
        z = max(z - 1.0, -h - BURY)
        zs.append(z)
    return zs


def face_hulls(p, F, a_lo, a_hi, h, back=HULL_BACK, warp=None):
    """Sloped band hulls following the batter over [a_lo(z), a_hi(z)]; the coping band on top is flat at grade."""
    zs = band_z(h)
    for z1, z0 in zip(zs, zs[1:]):
        pts = []
        for z in (z1, z0):
            for a in (a_lo(z), a_hi(z)):
                front = F.P(a, z)
                back_ = F.O + F.t * a - F.o * back + Vector((0, 0, z))
                pts += [front, back_]
        if warp:
            pts = [q + warp(q) for q in pts]
        p.hull_pts([tuple(q) for q in pts], kind="wall_top" if z1 == 0.0 else "wall_batter")


# ------------------------------------------------------------------------------------------------ moss
def wall_moss(z_foot, band=1.5):
    """Moss on the wall stones (M_DK_FootingStone lerps to the kit-1 moss colour by the 'Wear' ALPHA): patchy olive on
    the lower courses (strongest within `band` of the foot), in the deep joints everywhere (Wear R: occlusion), on the
    stones' upper shoulders; little on the coping."""
    def fn(obj, slot):
        me = obj.data
        ca = me.color_attributes["Wear"]
        n_f = 0
        vco = me.vertices
        for poly in me.polygons:
            if poly.material_index != slot:
                continue
            n_f += 1
            nz = poly.normal.z
            for li in poly.loop_indices:
                co = vco[me.loops[li].vertex_index].co
                col = ca.data[li].color
                hgt = co.z - z_foot
                low = clamp01((band - hgt) / band) ** 0.75
                patch = noise.noise(co * 2.6 + Vector((3.1, 7.7, 1.3))) * 0.5 + 0.5
                fine = noise.noise(co * 11.0 + Vector((1.7, 2.9, 5.3))) * 0.5 + 0.5
                m = clamp01((patch * 0.7 + fine * 0.3 - 0.44) * 3.0)
                # f2 (the owner's reading): moss and dirt in the BED JOINTS (occluded rims, Wear R) and on the stones'
                # TOP EDGES (upward shoulders), patchy, denser low down; the faces' crowns stay clean grey granite
                joint = clamp01((col[0] - 0.34) * 2.4)
                upf = clamp01((nz - 0.28) * 2.2)
                # f2r2: stronger on the top edges (the reference's moss lines along the bed joints)
                a = clamp01(joint * (0.50 + 0.45 * low) * (0.35 + 0.65 * patch) + upf * (0.45 + 0.55 * m) * (0.65 + 0.35 * low)
                            + 0.20 * low * low * m)
                dirt = 0.10 * joint                          # a little grime with it (Wear R: darker in the joints)
                ca.data[li].color = (clamp01(col[0] + dirt), col[1], col[2], 0.90 * a)
        me.update()
        return n_f
    return fn


def core_moss(obj, slot):
    """The joint core (M_DKT_JointDark): patchy olive moss where it shows in the joints."""
    me = obj.data
    ca = me.color_attributes["Wear"]
    n_f = 0
    for poly in me.polygons:
        if poly.material_index != slot:
            continue
        n_f += 1
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            col = ca.data[li].color
            patch = noise.noise(co * 3.3 + Vector((5.1, 1.7, 2.2))) * 0.5 + 0.5
            # f2: dark, deep joints: full grime (R), no edge wear (G), no dust (B: the library dust lerp brightened
            # the f2-dev core to ochre), a little patchy moss
            ca.data[li].color = (1.0, 0.0, 0.0, 0.34 * clamp01((patch - 0.46) * 2.4))   # f2r2: patchy moss, still dark
    me.update()
    return n_f


def cope_moss(obj, slot):
    """f2: the cap stones: moss ON TOP (patchy cushions on the walkable tops, thicker along the front arris and the
    joints) and in the joints; the fronts mostly clean."""
    me = obj.data
    ca = me.color_attributes["Wear"]
    n_f = 0
    for poly in me.polygons:
        if poly.material_index != slot:
            continue
        n_f += 1
        nz = poly.normal.z
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            col = ca.data[li].color
            patch = noise.noise(co * 3.1 + Vector((2.2, 6.1, 4.4))) * 0.5 + 0.5
            fine = noise.noise(co * 12.0 + Vector((1.1, 3.3, 7.7))) * 0.5 + 0.5
            m = clamp01((patch * 0.7 + fine * 0.3 - 0.40) * 2.8)
            top = clamp01((nz - 0.55) * 3.0)
            joint = clamp01((col[0] - 0.34) * 2.4)
            edge = clamp01((col[1] - 0.30) * 2.0) * top      # worn arrises (Wear G) on the top: the front edge
            # f2r2: the owner's "moss on top": cushions over most of the walkable top, thickest along the arrises
            a = clamp01(top * (0.30 + 0.70 * m) + edge * (0.4 + 0.6 * m) + joint * (0.35 + 0.65 * patch) * 0.8)
            ca.data[li].color = (col[0], col[1], col[2], 0.88 * a)
    me.update()
    return n_f


def pad_moss(obj, slot):
    """f3: the moss cushions (M_DKT_MossPad): nearly full moss (Wear.A 0.82-1.0), patchy darker grime (R) so the
    cushions are not one flat green, no edge wear."""
    me = obj.data
    ca = me.color_attributes["Wear"]
    n_f = 0
    for poly in me.polygons:
        if poly.material_index != slot:
            continue
        n_f += 1
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            a = noise.noise(co * 14.0 + Vector((2.2, 0.4, 7.1))) * 0.5 + 0.5
            b = noise.noise(co * 41.0 + Vector((5.5, 3.3, 1.1))) * 0.5 + 0.5
            ca.data[li].color = (clamp01(0.10 + 0.55 * (1.0 - a) * b), 0.0, 0.0, clamp01(0.80 + 0.22 * a))
    me.update()
    return n_f


def moss_for(z_foot, band=1.5):
    return {FS: wall_moss(z_foot, band), JE: core_moss, CP: cope_moss, sk.MOSS_MAT: pad_moss}


# ------------------------------------------------------------------------------------------------ pieces
def new_piece(name, cls, note, h=None):
    """f2: the Sweep variant set carries the suffix '_Sweep' (PROFILE); the default pieces keep their names."""
    if PROFILE["suffix"]:
        name += PROFILE["suffix"]
        note += " (SWEEP variant: concave castle batter 0.10 s + 0.035 s^2, upswept outside corners)"
    p = sk.Piece(name, cls, note, TRACK)
    p.tone_dark = 0.62          # f3: wider still (f2r2 0.48): the reference's light and grey stones side by side (SG10)
    p.extra["height_m"] = h
    p.extra["profile"] = PROFILE["kind"]
    return p


def straight_face(h):
    return Face((0, 0, 0), (1, 0, 0))


def wall_straight(L, h, seed):
    p = new_piece(f"SM_DKT_Wall_{L}m_H{h}", "wall", f"straight {L} m terrace wall module, {h} m from grade to foot "
                  f"(+{BURY} m buried), coping included", h)
    F = straight_face(h)
    g = p.g
    s_bot = h + BURY

    def lohi(k, sa, sb):
        o = tooth(k)
        return (o, o), (L + o, L + o)

    n = lay_face(g, F, COPE_H, s_bot, lohi, [0.0, float(L)], seed)
    core_slab(g, F, lambda z: 0.0, lambda z: float(L), -COPE_H + 0.01, -s_bot)
    coping_run(g, F, 0.0, float(L), seed + 5)
    face_hulls(p, F, lambda z: 0.0, lambda z: float(L), h)
    p.hull_box(0.0, float(L), 0.0, COPE_D + 0.45, -COPE_H, 0.0, kind="wall_top")
    p.extra["stones"] = n
    snaps_straight(p, L, h)
    p.ground_z = -h
    p.moss = moss_for(-h)
    return p


def snaps_straight(p, L, h):
    p.snap("start", (0, 0, 0), (0, -1, 0), "this pivot; the previous module's 'end'")
    p.snap("end", (L, 0, 0), (0, -1, 0), "next straight/corner/end/opening pivot here, same yaw")
    p.snap("foot", (0, -d(h), -h), (0, -1, 0), "WallFoot_2m/4m pivot (face line at the nominal foot)")
    p.snap("foot_end", (L, -d(h), -h), (0, -1, 0), "the next foot piece")


def corner_out_geo(p, h, seed, lenA=CORNER_ARM, endA="tooth", lenB=CORNER_ARM, endB="tooth"):
    """Outside corner in its own frame: face A along +X from x = 0 (lenA of top line) to the arris at x = lenA, face B
    along +Y from the arris (y = 0) to y = lenB. Sangi-zumi blocks at the arris course by course (long face on A in
    even courses, on B in odd), body stones filling each arm, the upswept flare warped in last."""
    g = p.g
    s_bot = h + BURY
    FA = Face((0, 0, 0), (1, 0, 0))
    FB = Face((lenA, 0, 0), (0, 1, 0))
    rng = random.Random(seed)
    blocks = {}
    ks = [k for k in range(len(COURSE_S) - 1) if COURSE_S[k] < s_bot - 0.02]
    for k in ks:
        sa, sb = COURSE_S[k], min(COURSE_S[k + 1], s_bot)
        sm = (sa + sb) / 2
        long_on_A = (k % 2 == 0)
        LL, LS = rng.uniform(0.80, 0.95), rng.uniform(0.40, 0.50)
        LA, LB = (LL, LS) if long_on_A else (LS, LL)
        armA = lenA + d(sm)
        armB = lenB + d(sm)
        loA = tooth(k) if endA == "tooth" else 0.0
        if armA - LA - loA < 0.30 and armA - loA <= 1.30:
            LA = armA - loA
        if endB == "tooth" and armB + tooth(k) - LB < 0.30 and armB + tooth(k) <= 1.30:
            LB = armB + tooth(k)
        blocks[k] = (LA, LB, sa, sb, sm)
        gap = 0.016
        pr = rng.uniform(0.012, 0.020)
        X_ar, Y_ar = lenA + d(sm), -d(sm)
        x0, x1 = X_ar - LA + gap / 2, X_ar + pr
        y0, y1 = Y_ar - pr, Y_ar + LB - gap / 2
        z1, z0 = -sa - gap / 2, -sb + gap / 2
        cc = Vector(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
        if long_on_A:
            axes, half = ((1, 0, 0), (0, 1, 0), (0, 0, 1)), ((x1 - x0) / 2, (y1 - y0) / 2, (z1 - z0) / 2)
        else:
            axes, half = ((0, 1, 0), (-1, 0, 0), (0, 0, 1)), ((y1 - y0) / 2, (x1 - x0) / 2, (z1 - z0) / 2)
        shear = (lambda v, sm=sm: Vector((d(-v.z) - d(sm), -(d(-v.z) - d(sm)), 0.0)))
        big = max(half[0], half[1])
        sheared_block(g, cc, axes, half, 0.030, seed * 71 + k, FS, shear, bulge=rng.uniform(0.010, 0.018),
                      rough=0.0025, fine=0.0008, n=(max(10, int(2 * big / 0.05)), max(6, int(2 * min(half[0], half[1]) / 0.05)),
                                                   max(6, int(2 * half[2] / 0.05))))
    jg = 0.016

    def loA_fn(k, sa, sb):
        o = tooth(k) if endA == "tooth" else 0.0
        return o

    def lohiA(k, sa, sb):
        LA = blocks[k][0]
        lo = loA_fn(k, sa, sb)
        return (lo, lo), (lenA + d(sa) - LA - jg, lenA + d(sb) - LA - jg)

    def lohiB(k, sa, sb):
        LB = blocks[k][1]
        hi = lenB + (tooth(k) if endB == "tooth" else 0.0)
        return (-d(sa) + LB + jg, -d(sb) + LB + jg), (hi, hi)

    fa_v0 = len(g.v)
    n = lay_face(g, FA, COPE_H, s_bot, lohiA, [0.0, lenA], seed + 1)
    fa_v1 = len(g.v)
    n += lay_face(g, FB, COPE_H, s_bot, lohiB, [0.0, lenB], seed + 2)
    core_v0 = len(g.v)
    core_slab(g, FA, lambda z: 0.0, lambda z: lenA + d(-z) - CORE_IN, -COPE_H + 0.01, -s_bot)
    core_slab(g, FB, lambda z: -d(-z) + CORE_IN, lambda z: lenB, -COPE_H + 0.01, -s_bot)
    core_v1 = len(g.v)
    # coping: a big corner block (long on A), then the runs
    cr = random.Random(seed + 9)
    CL = cr.uniform(0.62, 0.74)
    gap = 0.015
    cc = Vector((lenA - CL / 2 + 0.008, COPE_D / 2 - 0.008, -COPE_H / 2 + 0.001))
    shear = (lambda v: Vector((d(-v.z) - d(COPE_H / 2), -(d(-v.z) - d(COPE_H / 2)), 0.0)))
    sheared_block(g, cc, ((1, 0, 0), (0, 1, 0), (0, 0, 1)), (CL / 2 - gap / 2, COPE_D / 2 - gap / 2, COPE_H / 2 - 0.004),
                  0.020, seed * 5 + 3, CP, shear, bulge=0.012, rough=0.0022, fine=0.0007, n=(16, 12, 7))
    coping_run(g, FA, 0.0, lenA - CL, seed + 11)
    coping_run(g, FB, COPE_D, lenB, seed + 12)
    face_hulls(p, FA, lambda z: 0.0, lambda z: lenA + d(-z), h, warp=flare_fn(lenA))
    face_hulls(p, FB, lambda z: -d(-z), lambda z: lenB, h, warp=flare_fn(lenA))
    p.hull_box(0.0, lenA, 0.0, COPE_D + 0.45, -COPE_H, 0.0, kind="wall_top")
    p.hull_box(lenA - COPE_D - 0.45, lenA, 0.0, lenB, -COPE_H, 0.0, kind="wall_top")
    # f1 (judge delta 9): the upswept flare moves every stone RIGIDLY by the flare at its centroid (no stone is sheared
    # along the curve); the joint core stays on the plain batter (it never pokes out past the stones as a curled sheet)
    fl = flare_fn(lenA)
    # the sangi-zumi blocks (added before the faces) move rigidly by the flare at their centroid
    parts = {}
    for fi, f in enumerate(g.f):
        if f[0] < fa_v0:
            parts.setdefault(g.fp[fi], set()).update(f)
    for pid, vs in parts.items():
        c = sum((g.v[i] for i in vs), Vector()) / len(vs)
        dv = fl(c)
        for i in vs:
            g.v[i] = g.v[i] + dv
    # face stones (and the coping, beyond the core): each face's stones take only their own outward component of the
    # flare, per vertex (they bend with the curve a little but are never stretched along the face)
    for i in range(fa_v0, len(g.v)):
        if core_v0 <= i < core_v1:
            continue
        v = g.v[i]
        dv = fl(v)
        if dv.length == 0.0:
            continue
        if i < fa_v1:
            dv = Vector((0.0, dv.y, 0.0))
        elif i < core_v0:
            dv = Vector((dv.x, 0.0, 0.0))
        g.v[i] = v + dv
    p.extra["stones"] = n
    p.extra["sangi_zumi_courses"] = len(blocks)
    return p


def flare_fn(xc, yc=0.0):
    """The upswept outside corner: extra outward push F(s) at the arris (x = xc + d, y = yc - d), fading over FLARE_R
    along each face, diagonal (out A + out B), so the arris line curves out towards the foot."""
    def f(v):
        s = -v.z
        if s <= 0:
            return Vector()
        rA = (xc + d(s)) - v.x
        rB = v.y - (yc - d(s))

        def w(r):
            return 1.0 if r <= 0 else max(0.0, 1.0 - r / FLARE_R) ** 2
        k = flare(s) * w(rA) * w(rB)
        return Vector((k, -k, 0.0))
    return f


def wall_corner_out(h, seed):
    p = new_piece(f"SM_DKT_Wall_CornerOut_H{h}", "wall", f"outside corner, {h} m, sangi-zumi + upswept arris; 1 m of "
                  "each face", h)
    corner_out_geo(p, h, seed)
    p.snap("start", (0, 0, 0), (0, -1, 0), "this pivot")
    p.snap("next", (1, 1, 0), (1, 0, 0), "next piece pivot here, yaw +90")
    p.snap("foot", (0, -d(h), -h), (0, -1, 0), f"WallFoot_CornerOut_H{h} pivot")
    p.snap("foot_next", (1 + d(h), 1, -h), (1, 0, 0), "the next foot piece, yaw +90")
    p.ground_z = -h
    p.moss = moss_for(-h)
    return p


def wall_end(h, seed, side):
    if side == "R":
        p = new_piece(f"SM_DKT_Wall_EndR_H{h}", "wall", f"wall end (the run ends at +X and returns {END_RETURN} m into "
                      "the slope, buried end), {h} m".replace("{h}", str(h)), h)
        corner_out_geo(p, h, seed, lenA=1.0, endA="tooth", lenB=END_RETURN, endB="free")
        p.snap("start", (0, 0, 0), (0, -1, 0), "this pivot: the previous module's 'end'")
        p.snap("foot", (0, -d(h), -h), (0, -1, 0), "a WallFoot piece (the corner's own foot stones are in the skirt)")
    else:
        p = new_piece(f"SM_DKT_Wall_EndL_H{h}", "wall", f"wall start (the run starts at x = 0 coming out of the slope, "
                      f"{END_RETURN} m return), {h} m", h)
        corner_out_geo(p, h, seed, lenA=END_RETURN, endA="free", lenB=1.0, endB="tooth")
        M = Matrix.Translation((0.0, END_RETURN, 0.0)) @ Matrix.Rotation(math.radians(-90.0), 4, "Z")
        tg = p.g.transformed(M)
        p.g = tg
        p.hulls = [[tuple(M @ Vector(q)) for q in pts] for pts in p.hulls]
        p.snap("start", (0, 0, 0), (0, -1, 0), "this pivot (the arris; the return runs back along +Y)")
        p.snap("end", (1, 0, 0), (0, -1, 0), "next module pivot here, same yaw")
        p.snap("foot_end", (1, -d(h), -h), (0, -1, 0), "the next foot piece")
    p.ground_z = -h
    p.moss = moss_for(-h)
    return p


CORNER_IN_ARM = 2.0         # inside corners take 2 m of each face: the batter pulls the corner line in by d(s)


def arm_in(h):
    """f1 (judge delta 9): H6 inside corners take 3 m of each face (a 2 m arm left only 0.14 m of face at the 6 m foot
    and the return leg showed bare core); H2-H4 keep 2 m."""
    return 3.0 if (h >= 6 and PROFILE["kind"] == "sweep") else CORNER_IN_ARM

                            # (0.96 m at 4 m, 1.86 m at 6 m), a 1 m arm would vanish at depth


def wall_corner_in(h, seed):
    """Inside corner: face A along +X to the corner line at x = 2 - d(s), face B from (2, 0) along -Y (outward -X) to
    y = -2. Long corner stones alternate between the faces course by course (long-short), no flare."""
    A = arm_in(h)
    p = new_piece(f"SM_DKT_Wall_CornerIn_H{h}", "wall", f"inside corner, {h} m, alternating long / short corner stones; "
                  f"{A:.0f} m of each face", h)
    g = p.g
    s_bot = h + BURY
    FA = Face((0, 0, 0), (1, 0, 0))
    FB = Face((A, 0, 0), (0, -1, 0))
    jg = 0.012

    def lohiA(k, sa, sb):
        o = tooth(k)
        off = 0.0 if k % 2 == 0 else 0.045
        return (o, o), (A - d(sa) - off - jg, A - d(sb) - off - jg)

    def lohiB(k, sa, sb):
        off = 0.045 if k % 2 == 0 else 0.0
        return (d(sa) + off + jg, d(sb) + off + jg), (A + tooth(k), A + tooth(k))

    n = lay_face(g, FA, COPE_H, s_bot, lohiA, [0.0, A], seed + 1, force_last={0: (0.62, 0.80), 1: (0.26, 0.34)})
    n += lay_face(g, FB, COPE_H, s_bot, lohiB, [0.0, A], seed + 2, force_first={1: (0.62, 0.80), 0: (0.26, 0.34)})
    core_slab(g, FA, lambda z: 0.0, lambda z: A + 0.3, -COPE_H + 0.01, -s_bot)
    core_slab(g, FB, lambda z: d(-z) - 0.3, lambda z: A, -COPE_H + 0.01, -s_bot)
    rng = random.Random(seed + 9)
    # coping: the corner block sits in the re-entrant corner (long on A), the runs beyond
    CL = rng.uniform(0.62, 0.72)
    gap = 0.015
    cc = Vector((A - CL / 2 + COPE_D / 2 + 0.004, COPE_D / 2 - 0.008, -COPE_H / 2 + 0.001))
    shear = (lambda v: Vector((0.0, -(d(-v.z) - d(COPE_H / 2)), 0.0)))
    sheared_block(g, cc, ((1, 0, 0), (0, 1, 0), (0, 0, 1)), ((CL + COPE_D) / 2 - gap / 2 - 0.004, COPE_D / 2 - gap / 2,
                  COPE_H / 2 - 0.004), 0.020, seed * 5 + 3, CP, shear, bulge=0.012, rough=0.0022, fine=0.0007, n=(18, 12, 7))
    coping_run(g, FA, 0.0, A - CL, seed + 11)
    coping_run(g, FB, 0.0, A, seed + 12)
    face_hulls(p, FA, lambda z: 0.0, lambda z: A + HULL_BACK, h)
    face_hulls(p, FB, lambda z: d(-z), lambda z: A, h)
    p.hull_box(0.0, A + COPE_D + 0.45, 0.0, COPE_D + 0.45, -COPE_H, 0.0, kind="wall_top")
    p.hull_box(A, A + COPE_D + 0.45, -A, 0.0, -COPE_H, 0.0, kind="wall_top")
    p.extra["stones"] = n
    p.snap("start", (0, 0, 0), (0, -1, 0), "this pivot")
    p.snap("next", (A, -A, 0), (-1, 0, 0), "next piece pivot here, yaw -90")
    p.snap("foot", (0, -d(h), -h), (0, -1, 0), f"WallFoot_CornerIn_H{h} pivot")
    p.snap("foot_next", (A - d(h), -A, -h), (-1, 0, 0), "the next foot piece, yaw -90")
    p.ground_z = -h
    p.moss = moss_for(-h)
    return p


# ------------------------------------------------------------------------------------------------ stair opening
def stair_numbers(h):
    n = int(round(h / RISER_T))
    return n, h / n


_T9 = {}


def track9():
    """Track 9's builder imported without running it (sk_shared.load_builder): its worn granite step stone and step
    material, so the opening's flight matches the stair-path flights. None if it cannot be imported right now."""
    if "mod" not in _T9:
        try:
            _T9["mod"] = sk.load_builder(Path(__file__).resolve().parent / "build_stairs.py", "dojo_build_stairs")
        except Exception as e:  # noqa: BLE001
            print("track 9 builder not importable, own step blocks:", repr(e), flush=True)
            _T9["mod"] = None
    return _T9["mod"]


def wall_stair_opening(h, seed):
    """A 4 m module pierced by the stair path: a stone bastion projects from the face carrying a straight flight from
    grade (the top landing, flush with the coping) down to the foot; dressed granite steps (library Granite, the gate
    apron's rough_block steps) between sloped sode-ishi curbs; the bastion's side faces are battered stone walls in the
    wall's courses; inside corners where they meet the main face."""
    n, r = stair_numbers(h)
    p = new_piece(f"SM_DKT_Wall_StairOpening_H{h}", "wall_stair", f"4 m module with a straight stair through the wall, "
                  f"{h} m: {n} risers of {r:.4f} m, tread {TREAD} m, clear width {FLIGHT[1] - FLIGHT[0]:.2f} m", h)
    g = p.g
    rng = random.Random(seed)
    s_bot = h + BURY
    X0, X1 = FLIGHT
    CL0, CR1 = X0 - CURB_W, X1 + CURB_W           # 0.65 / 3.35: the curbs' outer faces = the side faces' top line
    kslope = r / TREAD
    y_front = -(n - 1) * TREAD                     # the lowest nosing
    y_end = y_front - 0.10                          # the curbs' and side faces' front end

    def z_nose(y):
        return y * kslope

    def z_curb_bot(y):
        return z_nose(y) + CURB_UP - CURB_H

    def dside(s_):
        return SIDE_A * max(0.0, s_)
    # left side face: outward -X, a = -y; right: outward +X, a = y
    FL = Face((CL0, 0, 0), (0, -1, 0), D=lambda a, z: dside(z_curb_bot(-a) - z))
    FR = Face((CR1, 0, 0), (0, 1, 0), D=lambda a, z: dside(z_curb_bot(a) - z))
    FA = Face((0, 0, 0), (1, 0, 0))
    jg = 0.014
    # main face strips (left: 0..the left side face, right: the right side face..4)

    def lohi_ml(k, sa, sb):
        o = tooth(k)
        return (o, o), (CL0 - dside(sa) - jg - 0.02, CL0 - dside(sb) - jg - 0.02)

    def lohi_mr(k, sa, sb):
        o = tooth(k)
        return (CR1 + dside(sa) + jg + 0.02, CR1 + dside(sb) + jg + 0.02), (4 + o, 4 + o)

    nst = lay_face(g, FA, COPE_H, s_bot, lohi_ml, [0.0, CL0], seed + 1)
    nst += lay_face(g, FA, COPE_H, s_bot, lohi_mr, [CR1, 4.0], seed + 2)
    # side faces: a from the main face line to the front end; clipped under the sloped curb bottom
    a_end = -y_end

    def lohi_sl(k, sa, sb):
        return (d(sa) + jg, d(sb) + jg), (a_end, a_end)

    def lohi_sr(k, sa, sb):
        return (-a_end, -a_end), (-d(sa) - jg, -d(sb) - jg)

    # keep z <= z_curb_bot(y) - joint: left (a = -y): z + kslope * a <= CURB_UP - CURB_H - j
    c_ = CURB_UP - CURB_H - 0.016
    nst += lay_face(g, FL, COPE_H, s_bot, lohi_sl, [], seed + 3, clip=[(kslope, 1.0, c_)])
    nst += lay_face(g, FR, COPE_H, s_bot, lohi_sr, [], seed + 4, clip=[(-kslope, 1.0, c_)])
    # cores: main strips + the bastion (one slab under each side face, a fill wedge under the steps)
    core_slab(g, FA, lambda z: 0.0, lambda z: CL0, -COPE_H + 0.01, -s_bot)
    core_slab(g, FA, lambda z: CR1, lambda z: 4.0, -COPE_H + 0.01, -s_bot)
    # bastion cores: under each curb, the outer face following the battered side face (planar: d_side is linear),
    # the top under the curb's sloped bottom (never above it)
    y_k = (-COPE_H - CURB_UP + CURB_H) / kslope            # where the curb bottom line reaches the coping bottom
    for (xo, xi, sgn) in ((CL0, X0 + 0.05, -1), (CR1, X1 - 0.05, 1)):
        for (ya, yb) in ((0.30, y_k), (y_k, y_end)):
            def top(y):
                return min(z_curb_bot(y), -COPE_H) - 0.012

            def xout(y, z):
                return xo + sgn * (dside(z_curb_bot(y) - z) - CORE_IN)
            zb_ = -s_bot
            pts = [(xout(ya, top(ya)), ya, top(ya)), (xi, ya, top(ya)), (xi, yb, top(yb)), (xout(yb, top(yb)), yb, top(yb)),
                   (xout(ya, zb_), ya, zb_), (xi, ya, zb_), (xi, yb, zb_), (xout(yb, zb_), yb, zb_)]
            hexa(g, pts, JE)
    # the fill under the flight (hidden: blocks light in the step joints)
    fill = []
    for (y, zt_) in ((0.55, -0.30), (0.0, -0.30), (y_end, z_nose(y_end) - 0.30), (y_end, -s_bot), (0.55, -s_bot)):
        fill.append((y, zt_))
    prism_yz(g, fill, X0 + 0.02, X1 - 0.02, JE)
    # steps: track 9's worn granite step stones (f1: light M_DKT_StepGranite treads, darker M_DKT_StepRiser risers, a
    # 4.0 cm set-back riser under a rounded worn nosing, 1-2 slabs per 1.8 m step); own blocks as a fallback
    T9 = track9()
    step_mat = T9.SG if T9 is not None else GR
    wear_x = 0.0
    xm_ = (X0 + X1) / 2
    for i in range(1, n):
        zt_ = -i * r
        y_n = -i * TREAD
        y0_, y1_ = y_n - NOSE, y_n + TREAD + 0.07
        if T9 is not None:          # f1 (judge delta 3): 1-2 long slabs per step (track 9's step_cuts)
            xs = [xm_ + c for c in T9.step_cuts(X1 - X0, i, rng)]
        else:
            xs = [X0, xm_ + rng.uniform(-0.3, 0.3), X1]
        wear_x = max(-0.18, min(0.18, wear_x + rng.uniform(-0.06, 0.06)))
        for j in range(len(xs) - 1):
            if T9 is not None:
                T9.worn_block(g, xs[j], xs[j + 1], y0_, y1_, zt_, r + 0.06, seed * 41 + i * 7 + j, rng,
                              mat=step_mat, wear_x=xm_ + wear_x)
            else:
                cc = Vector(((xs[j] + xs[j + 1]) / 2, (y0_ + y1_) / 2, zt_ - (r + 0.06) / 2))
                G.rough_block(g, cc, ((1, 0, 0), (0, 1, 0), (0, 0, 1)), ((xs[j + 1] - xs[j]) / 2 - 0.005,
                              (y1_ - y0_) / 2, (r + 0.06) / 2), 0.020, seed * 41 + i * 7 + j, GR, bulge=0.003,
                              rough=0.0035, fine=0.0016, n=(12, 8, 4))
    # the bottom step's buried footing (the lowest riser stands on it at the foot)
    G.rough_block(g, Vector(((X0 + X1) / 2, y_front + TREAD / 2 - 0.02, -h - 0.06)), ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
                  ((X1 - X0) / 2 - 0.006, TREAD / 2 + 0.06, 0.12), 0.012, seed * 43, step_mat, bulge=0.003, rough=0.004,
                  fine=0.002, n=(24, 6, 4))
    # the top landing at grade (two slabs), flush with the coping; its front arris is the top nosing
    xm = (X0 + X1) / 2 + rng.uniform(-0.2, 0.2)
    for xa, xb in ((X0, xm), (xm, X1)):
        if T9 is not None:
            T9.worn_block(g, xa, xb, -NOSE, COPE_D, 0.0, 0.22, seed * 47 + int(xa * 10), rng, mat=step_mat,
                          wear_x=xm_, chips=False)
        else:
            G.rough_block(g, Vector(((xa + xb) / 2, COPE_D / 2 - 0.004, -0.11)), ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
                          ((xb - xa) / 2 - 0.006, COPE_D / 2 + 0.004, 0.11), 0.014, seed * 47 + int(xa * 10), GR,
                          bulge=0.003, rough=0.004, fine=0.002, n=(18, 10, 4))
    # coping on the main strips and the curb heads (flat, from the main face out to where the curb line reaches 0)
    FAc = FA
    coping_run(g, FAc, 0.0, CL0, seed + 21)
    coping_run(g, FAc, CR1, 4.0, seed + 22)
    y_head = -(CURB_H - CURB_UP) / kslope * 0.0 - CURB_UP / kslope     # where the curb top line reaches grade
    for (xa, xb, sgn) in ((CL0, X0, -1), (X1, CR1, 1)):
        cc = Vector(((xa + xb) / 2, (COPE_D + y_head) / 2, -COPE_H / 2 + 0.001))
        G.rough_block(g, cc, ((0, -1, 0), (-sgn, 0, 0) if sgn > 0 else (1, 0, 0), (0, 0, 1)),
                      ((COPE_D - y_head) / 2 - 0.008, (xb - xa) / 2 - 0.007, COPE_H / 2 - 0.004), 0.026,
                      seed * 53 + sgn, CP, bulge=0.008, rough=0.0022, fine=0.0007, n=(16, 9, 7))
    # sode-ishi curbs: sloped dressed blocks from the curb head down to the front end
    for (xa, xb, sgn) in ((CL0, X0, -1), (X1, CR1, 1)):
        y = y_head - 0.008
        i = 0
        while y > y_end + 0.05:
            ln = rng.uniform(0.95, 1.30)
            y1 = max(y - ln, y_end)
            if y1 - y_end < 0.35 and y1 > y_end:
                y1 = y_end
            yc = (y + y1) / 2
            zc = z_nose(yc) + CURB_UP - CURB_H / 2
            v0 = len(g.v)
            # outer (pillowed) face = the side face: front = -D, D pointing into the flight
            Dax = (1, 0, 0) if sgn < 0 else (-1, 0, 0)
            G.rough_block(g, Vector(((xa + xb) / 2, yc, zc)), ((0, 1, 0), Dax, (0, 0, 1)),
                          ((y - y1) / 2 - 0.007, (xb - xa) / 2 - 0.006, CURB_H / 2 - 0.004), 0.024, seed * 59 + i * 7 + sgn,
                          FS, bulge=0.008, rough=0.0022, fine=0.0007, n=(max(12, int((y - y1) / 0.05)), 8, 7))
            for vi in range(v0, len(g.v)):          # shear to the flight slope
                v = g.v[vi]
                g.v[vi] = v + Vector((0, 0, (v.y - yc) * kslope))
            y = y1 - 0.0
            i += 1
    # collision: main strips (batter bands), bastion sides (sloped), the flight ramp through the nosings, landing
    face_hulls(p, FA, lambda z: 0.0, lambda z: CL0, h)
    face_hulls(p, FA, lambda z: CR1, lambda z: 4.0, h)
    zb = -s_bot
    for (xo, xi, sgn) in ((CL0, X0, -1), (CR1, X1, 1)):
        foot_out = xo + sgn * dside(h)
        pts = [(xo, 0.0, 0.0), (xi, 0.0, 0.0), (xo, y_end, z_nose(y_end) + CURB_UP),
               (xi, y_end, z_nose(y_end) + CURB_UP), (foot_out, -d(h), zb), (xi, -d(h), zb),
               (xo + sgn * dside(0.3), y_end, zb), (xi, y_end, zb)]
        p.hull_pts(pts, kind="curb_ramp")
    ramp = [(0.0, 0.0), (-n * TREAD, -h), (-n * TREAD, zb), (COPE_D + 0.45, zb), (COPE_D + 0.45, 0.0)]
    p.hull_pts([(x, y, z) for x in (X0, X1) for (y, z) in ramp], kind="stair_ramp")
    p.hull_box(0.0, CL0, 0.0, COPE_D + 0.45, -COPE_H, 0.0, kind="wall_top")
    p.hull_box(CR1, 4.0, 0.0, COPE_D + 0.45, -COPE_H, 0.0, kind="wall_top")
    p.hull_box(CL0, CR1, 0.0, COPE_D + 0.45, -COPE_H, 0.0, kind="landing")
    p.extra.update({"stones": nst, "risers": n, "riser_m": round(r, 4), "tread_m": TREAD,
                    "pitch_deg": round(math.degrees(math.atan(kslope)), 2), "clear_width_m": round(X1 - X0, 3),
                    "flight_run_m": round((n - 1) * TREAD, 3), "curb_top_above_nosing_m": CURB_UP,
                    "bastion_projection_m": round(-y_end, 3)})
    p.snap("start", (0, 0, 0), (0, -1, 0), "this pivot")
    p.snap("end", (4, 0, 0), (0, -1, 0), "next module pivot, same yaw")
    p.snap("stair_top", ((X0 + X1) / 2, 0.30, 0.0), (0, 1, 0), "the top landing at grade (the path continues inland)")
    p.snap("stair_foot", ((X0 + X1) / 2, y_front, -h), (0, -1, 0), "the foot of the lowest riser on the flight's "
           "centre line (ground level): a track-9 W180 Flight's 'out' snap or Landing's N edge meets it (yaw 0)")
    for sd, sx in (("L", -1), ("R", 1)):
        p.snap(f"rail_{sd}", ((X0 + X1) / 2 + sx * ((X1 - X0) / 2 - 0.09), y_front - TREAD / 2, -h), (0, 1, 0),
               "track 9 Rail_Slope pivot (its first post) for a rail up this flight (flight space as track 9)")
    p.snap("foot", (0, -d(h), -h), (0, -1, 0), "WallFoot pieces: 0..0.65 m and 3.35..4 m only (the bastion stands "
           "in between)")
    p.ground_z = -h
    p.moss = dict(moss_for(-h))
    if step_mat != GR:
        p.moss[step_mat] = step_moss
        p.moss[T9.SR] = step_moss
    return p


def hexa(g, pts, mat):
    """A closed six-sided solid from 8 corners: top quad (0..3) then the bottom quad (4..7) under it, same order."""
    faces = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    cen = sum((Vector(v) for v in pts), Vector()) / 8
    out = []
    for f in faces:
        vs = [Vector(pts[i]) for i in f]
        nrm = (vs[1] - vs[0]).cross(vs[2] - vs[0])
        fc = sum(vs, Vector()) / 4
        out.append(f if nrm.dot(fc - cen) >= 0 else tuple(reversed(f)))
    g.add([tuple(p) for p in pts], out, mat, ((1, 0, 0), (0, 1, 0), (0, 0, 1)))


def step_moss(obj, slot):
    """The step stones' moss (their material lerps to moss by the 'Wear' alpha, as track 9's): only deep in the
    joints and at the back of each tread (occlusion), patchy; never on the walked middle."""
    me = obj.data
    ca = me.color_attributes["Wear"]
    n_f = 0
    for poly in me.polygons:
        if poly.material_index != slot:
            continue
        n_f += 1
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            col = ca.data[li].color
            patch = noise.noise(co * 4.0 + Vector((2.3, 5.1, 0.7))) * 0.5 + 0.5
            a = clamp01((col[0] - 0.40) * 1.6) * (0.35 + 0.65 * patch)
            ca.data[li].color = (col[0], col[1], col[2], 0.75 * a)
    me.update()
    return n_f


def prism_yz(g, poly_yz, x0, x1, mat):
    """A prism of a convex YZ polygon over x0..x1 (outward winding)."""
    m = len(poly_yz)
    verts = [(x0, y, z) for (y, z) in poly_yz] + [(x1, y, z) for (y, z) in poly_yz]
    faces = [(0, i + 1, i) for i in range(1, m - 1)] + [(m, m + i, m + i + 1) for i in range(1, m - 1)]
    for i in range(m):
        j = (i + 1) % m
        faces.append((i, j, m + j, m + i))
    # fix winding by the centroid test
    cen = sum((Vector(v) for v in verts), Vector()) / len(verts)
    out = []
    for f in faces:
        vs = [Vector(verts[i]) for i in f]
        nrm = (vs[1] - vs[0]).cross(vs[2] - vs[0])
        fc = sum(vs, Vector()) / len(vs)
        out.append(f if nrm.dot(fc - cen) >= 0 else tuple(reversed(f)))
    g.add(verts, out, mat, ((1, 0, 0), (0, 1, 0), (0, 0, 1)))


# ------------------------------------------------------------------------------------------------ coping alone
def coping_straight(L, seed):
    p = new_piece(f"SM_DKT_WallCoping_{L}m", "wall_top", f"the top course alone, {L} m: squared dressed blocks, flat "
                  "walkable tops at grade (the terrace edge on rock or low ground)")
    F = straight_face(1)
    coping_run(p.g, F, 0.0, float(L), seed)
    core_slab(p.g, F, lambda z: 0.0, lambda z: float(L), -0.02, -COPE_H + 0.01, back=COPE_D - 0.05)
    p.hull_box(0.0, float(L), -0.03, COPE_D, -COPE_H, 0.0, kind="wall_top")
    p.snap("start", (0, 0, 0), (0, -1, 0), "this pivot")
    p.snap("end", (L, 0, 0), (0, -1, 0), "next pivot, same yaw")
    p.ground_z = -COPE_H
    p.moss = moss_for(-COPE_H, band=0.3)
    return p


def coping_corner(kind, seed):
    p = new_piece(f"SM_DKT_WallCoping_Corner{kind}", "wall_top", f"the top course alone, {kind.lower()}side corner "
                  "(1 m of each face)")
    g = p.g
    FA = Face((0, 0, 0), (1, 0, 0))
    rng = random.Random(seed)
    CL = rng.uniform(0.62, 0.72)
    gap = 0.015
    if kind == "Out":
        FB = Face((1, 0, 0), (0, 1, 0))
        cc = Vector((1 - CL / 2 + 0.008, COPE_D / 2 - 0.008, -COPE_H / 2 + 0.001))
        shear = (lambda v: Vector((d(-v.z) - d(COPE_H / 2), -(d(-v.z) - d(COPE_H / 2)), 0.0)))
        sheared_block(g, cc, ((1, 0, 0), (0, 1, 0), (0, 0, 1)), (CL / 2 - gap / 2, COPE_D / 2 - gap / 2,
                      COPE_H / 2 - 0.004), 0.020, seed * 5 + 3, CP, shear, bulge=0.012, n=(16, 12, 7))
        coping_run(g, FA, 0.0, 1.0 - CL, seed + 11)
        coping_run(g, FB, COPE_D, 1.0, seed + 12)
        p.hull_box(0.0, 1.0, -0.03, COPE_D, -COPE_H, 0.0, kind="wall_top")
        p.hull_box(1.0 - COPE_D, 1.03, 0.0, 1.0, -COPE_H, 0.0, kind="wall_top")
        p.snap("next", (1, 1, 0), (1, 0, 0), "next pivot, yaw +90")
    else:
        A = CORNER_IN_ARM
        FB = Face((A, 0, 0), (0, -1, 0))
        cc = Vector((A - CL / 2 + COPE_D / 2 + 0.004, COPE_D / 2 - 0.008, -COPE_H / 2 + 0.001))
        shear = (lambda v: Vector((0.0, -(d(-v.z) - d(COPE_H / 2)), 0.0)))
        sheared_block(g, cc, ((1, 0, 0), (0, 1, 0), (0, 0, 1)), ((CL + COPE_D) / 2 - gap / 2 - 0.004,
                      COPE_D / 2 - gap / 2, COPE_H / 2 - 0.004), 0.020, seed * 5 + 3, CP, shear, bulge=0.012, n=(18, 12, 7))
        coping_run(g, FA, 0.0, A - CL, seed + 11)
        coping_run(g, FB, 0.0, A, seed + 12)
        p.hull_box(0.0, A + COPE_D, -0.03, COPE_D, -COPE_H, 0.0, kind="wall_top")
        p.hull_box(A - 0.03, A + COPE_D, -A, 0.0, -COPE_H, 0.0, kind="wall_top")
        p.snap("next", (A, -A, 0), (-1, 0, 0), "next pivot, yaw -90")
    p.snap("start", (0, 0, 0), (0, -1, 0), "this pivot")
    p.ground_z = -COPE_H
    p.moss = moss_for(-COPE_H, band=0.3)
    return p


# ------------------------------------------------------------------------------------------------ foot + skirt
PLINTH_TOP = 0.06           # f2: ONE continuous, level footing course, mostly buried (top 6 cm over the nominal foot)
PLINTH_BOT = -0.45
PLINTH_PROUD = 0.10


def plinth_run(g, F, a0, a1, seed, ends=("flat", "flat")):
    """The base course (nezuke-ishi): big rounded dressed blocks standing PLINTH_PROUD in front of the wall foot, tops
    PLINTH_TOP above the nominal foot, bottoms buried. F = the foot face (z = 0 at the nominal foot)."""
    rng = random.Random(seed)
    L = a1 - a0
    if L < 0.12:
        return 0
    m = max(1, int(round(L / 0.68)))
    ws = [rng.uniform(0.82, 1.18) for _ in range(m)]
    k = L / sum(ws)
    a = a0
    for i, w in enumerate(ws):
        w *= k
        gap = rng.uniform(0.014, 0.020)
        l0, l1 = a + gap / 2, a + w - gap / 2
        top = PLINTH_TOP + rng.uniform(-0.004, 0.004)           # f2: a LEVEL course (tops within +-4 mm)
        dep = 0.50
        cc = F.O + F.t * ((l0 + l1) / 2) + F.o * (PLINTH_PROUD - dep / 2) + Vector((0, 0, (top + PLINTH_BOT) / 2))
        G.rough_block(g, cc, (F.t, -F.o, Vector((0, 0, 1))), ((l1 - l0) / 2, dep / 2, (top - PLINTH_BOT) / 2),
                      0.022, seed * 61 + i, FS, bulge=rng.uniform(0.005, 0.009), rough=0.0025, fine=0.0008,
                      n=(max(10, int((l1 - l0) / 0.05)), 9, 12))
        a += w
    return m


def skirt(g, F, a0, a1, seed, rows=((-0.30, -0.62), (-0.62, -1.05))):
    """f2: NO skirt (the owner: remove the loose round rubble and the skirt sheets; the foot is one level, buried
    footing course). Kept as a no-op so the corner-foot code reads as before."""
    return 0


def skirt_flat(g, F, a0, a1, seed, rows=((-0.30, -0.62),)):
    """f1 (judge delta 8): the buried skirt as FLAT, ANGULAR rubble slabs, mostly sunk (tops 2-7 cm above grade), one
    sparse row (about 40 % cover) in front of the plinth: no spilled round boulders at the toe."""
    rng = random.Random(seed)
    n = 0
    for (y_in, y_out) in rows:
        a = a0 + rng.uniform(0.0, 0.5)
        while a < a1 - 0.10:
            L = rng.uniform(0.30, 0.60)
            if rng.random() < 0.45:
                a += rng.uniform(0.35, 0.8)
                continue
            dist = rng.uniform(-y_in, -y_out)
            yaw = rng.uniform(-0.35, 0.35)
            ta = (F.t * math.cos(yaw) + F.o * math.sin(yaw)).normalized()
            da = ta.cross(Vector((0, 0, 1))).normalized()
            dep = L * rng.uniform(0.55, 0.85)
            hz = rng.uniform(0.10, 0.16)
            top = rng.uniform(0.02, 0.07)
            c = F.O + F.t * (a + L / 2) + F.o * dist + Vector((0, 0, top - hz))
            G.rough_block(g, c, (ta, da, Vector((0, 0, 1))), (L / 2, dep / 2, hz), 0.022, rng.randrange(10 ** 6), FS,
                          bulge=0.004, rough=0.0025, fine=0.0008, n=(max(6, int(L / 0.06)), 6, 4))
            n += 1
            a += L + rng.uniform(0.25, 0.7)
    return n


def skirt_r0(g, F, a0, a1, seed, rows=((-0.30, -0.62), (-0.62, -1.05))):
    """r0 (kept for reference, unused): rounded boulders half sunk in two staggered rows."""
    rng = random.Random(seed)
    n = 0
    for ri, (y_in, y_out) in enumerate(rows):
        a = a0 + rng.uniform(-0.1, 0.25) + 0.2 * ri
        while a < a1 + 0.05:
            sz = rng.uniform(0.20, 0.55) * (1.0 - 0.25 * ri)
            if rng.random() < 0.22:
                a += rng.uniform(0.15, 0.4)
                continue
            dist = rng.uniform(-y_in, -y_out)
            c = F.O + F.t * (a + sz / 2) + F.o * dist
            sink = rng.uniform(0.35, 0.62)
            hz = sz * rng.uniform(0.35, 0.55)
            c.z = hz * (1 - 2 * sink)
            yaw = rng.uniform(-0.5, 0.5)
            ta = (F.t * math.cos(yaw) + F.o * math.sin(yaw)).normalized()
            da = ta.cross(Vector((0, 0, 1))).normalized()
            hd = sz * rng.uniform(0.32, 0.45)
            G.rounded_stone(g, c, (ta, da, Vector((0, 0, 1))), (sz / 2, hd, hz),
                            0.92 * min(sz / 2, hd, hz), rng.randrange(10 ** 6), FS, bulge=0.03, rough=0.014,
                            n=(10, 8, 7))
            n += 1
            a += sz * rng.uniform(0.75, 1.05)
    return n


def foot_straight(L, seed):
    p = new_piece(f"SM_DKT_WallFoot_{L}m", "wall_foot", f"continuous level footing course (tops +{PLINTH_TOP:.2f}, "
                  f"{PLINTH_PROUD:.2f} proud, buried to {PLINTH_BOT:.2f}), {L} m; pivot = a wall module's 'foot' snap "
                  "(face line at the nominal foot)")
    F = Face((0, 0, 0), (1, 0, 0), D=lambda a, z: 0.0)
    plinth_run(p.g, F, 0.0, float(L), seed)
    n = skirt(p.g, F, 0.0, float(L), seed + 3)
    p.hull_box(0.0, float(L), -PLINTH_PROUD - 0.02, 0.35, PLINTH_BOT, PLINTH_TOP, kind="foot_plinth")
    p.extra["skirt_stones"] = n
    p.snap("start", (0, 0, 0), (0, -1, 0), "this pivot = the wall's 'foot' snap")
    p.snap("end", (L, 0, 0), (0, -1, 0), "the next foot piece")
    p.ground_z = -0.05
    p.moss = moss_for(-0.2, band=0.6)
    return p


def foot_corner(kind, h, seed):
    """Corner foot for height h (pivot = the corner wall's 'foot' snap): the plinth follows face A to the arris / the
    corner line and face B beyond; a corner plinth block; the skirt wraps round."""
    p = new_piece(f"SM_DKT_WallFoot_Corner{kind}_H{h}", "wall_foot", f"{kind.lower()}side corner foot under "
                  f"SM_DKT_Wall_Corner{kind}_H{h}; pivot = that piece's 'foot' snap", h)
    g = p.g
    dh = d(h)
    if kind == "Out":
        F_ = flare(h)
        xa = 1.0 + dh + F_ - 0.0          # arris x (foot-local: the pivot is at (0, -dh, -h) of the wall piece)
        ya = -F_                           # arris y (foot-local; +dh shift cancels the wall's -dh)
        FA = Face((0, 0, 0), (1, 0, 0), D=lambda a, z: 0.0)
        FB = Face((xa, ya, 0), (0, 1, 0), D=lambda a, z: 0.0)
        lenB = 1.0 + dh - ya
        plinth_run(g, FA, 0.0, xa - 0.55, seed)
        plinth_run(g, FB, 0.55, lenB, seed + 1)
        cc = Vector((xa - 0.30 + PLINTH_PROUD / 2, ya + 0.30 - PLINTH_PROUD / 2, (PLINTH_TOP + PLINTH_BOT) / 2))
        G.rough_block(g, cc, ((1, 0, 0), (0, 1, 0), (0, 0, 1)), (0.30 + PLINTH_PROUD / 2 - 0.01, 0.30 + PLINTH_PROUD / 2 - 0.01,
                      (PLINTH_TOP - PLINTH_BOT) / 2), 0.022, seed * 7, FS, bulge=0.008, rough=0.0025, fine=0.0008,
                      n=(12, 12, 12))
        n = skirt(g, FA, -0.1, xa + 0.3, seed + 3)
        n += skirt(g, FB, -0.3, lenB, seed + 4)
        p.hull_box(0.0, xa + PLINTH_PROUD + 0.04, -PLINTH_PROUD - 0.04, 0.35, PLINTH_BOT, PLINTH_TOP, kind="foot_plinth")
        p.hull_box(xa - 0.35, xa + PLINTH_PROUD + 0.04, ya - PLINTH_PROUD - 0.04, lenB, PLINTH_BOT, PLINTH_TOP,
                   kind="foot_plinth")
        p.snap("next", (xa, 1.0 + dh, 0), (1, 0, 0), "the next foot piece, yaw +90")
    else:
        A = arm_in(h)
        xa = A - dh
        FA = Face((0, 0, 0), (1, 0, 0), D=lambda a, z: 0.0)
        FB = Face((xa, 0, 0), (0, -1, 0), D=lambda a, z: 0.0)
        lenB = A - dh
        plinth_run(g, FA, 0.0, xa - PLINTH_PROUD, seed)
        plinth_run(g, FB, PLINTH_PROUD, lenB, seed + 1)
        n = skirt(g, FA, 0.0, xa - 1.1, seed + 3)
        n += skirt(g, FB, 1.1, lenB, seed + 4)
        # the re-entrant pocket: a few boulders set diagonally
        n += skirt(g, Face((xa - 1.1, 0, 0), (1, 0, 0), D=lambda a, z: 0.0), 0.0, 0.45, seed + 5,
                   rows=((-0.30, -0.70),))
        n += skirt(g, Face((xa, -0.6, 0), (0, -1, 0), D=lambda a, z: 0.0), 0.0, 0.5, seed + 6,
                   rows=((-0.30, -0.70),))
        p.hull_box(0.0, xa + 0.35, -PLINTH_PROUD - 0.04, 0.35, PLINTH_BOT, PLINTH_TOP, kind="foot_plinth")
        p.hull_box(xa - PLINTH_PROUD - 0.04, xa + 0.35, -lenB, 0.0, PLINTH_BOT, PLINTH_TOP, kind="foot_plinth")
        p.snap("next", (xa, -A + dh, 0), (-1, 0, 0), "the next foot piece, yaw -90")
    p.extra["skirt_stones"] = n
    p.snap("start", (0, 0, 0), (0, -1, 0), "this pivot = the corner wall's 'foot' snap")
    p.ground_z = -0.05
    p.moss = moss_for(-0.2, band=0.6)
    return p


# ------------------------------------------------------------------------------------------------ catalog
def yaw_of(facing):
    return round(math.degrees(math.atan2(facing[0], -facing[1])), 1)


def catalog_entry(p, obj, qa, exp):
    st = sk.mesh_stats(obj)
    # wall snaps: 'facing' = the next piece's outward face normal (yaw 0 faces -Y); stair / rail snaps: 'facing' = the
    # direction of travel up the path, the track-9 piece's local +Y (yaw 0 = +Y)
    snaps = {k: dict(v, next_yaw_deg=(round(math.degrees(math.atan2(-v["facing"][0], v["facing"][1])), 1)
                                      if k.startswith(("rail_", "stair_")) else yaw_of(v["facing"])))
             for k, v in p.snaps.items()}
    return {"track": TRACK, "class": p.cls, "note": p.note, "height_m": p.extra.get("height_m"),
            "pivot": "face line at terrace grade (Z 0) at the module start; face looks to local -Y"
                     if not p.name.startswith("SM_DKT_WallFoot") else
                     "the wall's 'foot' snap: face line at the nominal foot; face looks to local -Y",
            "bbox_min": st["bbox_min"], "bbox_max": st["bbox_max"], "size_m": st["size_m"],
            "tris": st["tris"], "nanite": p.nanite, "lods": exp.get("lod_tris") if exp else None,
            "budget": ("Nanite, LOD0 %d tris (fallback: UE auto)" % st["tris"]) if p.nanite else
                      ("LOD0-2 %s" % (exp.get("lod_tris") if exp else "")),
            "ucx": [{"name": u["name"], "kind": (p.hull_kinds[i] if i < len(p.hull_kinds) else ""), "min": u["min"],
                     "max": u["max"]} for i, u in enumerate(st["ucx"])],
            "materials": st["slots"], "snaps": snaps,
            "extra": {k: v for k, v in p.extra.items() if k != "height_m"},
            "traversal": traversal_boxes(p, st),
            "fbx": (f"Exports/DojoKit/StoneKit/{p.name}.fbx" if exp else None),
            "qa_hard_fails": len(qa["hard_fails"]) if qa else None}


def traversal_boxes(p, st):
    """f2r2 (STONE_BUILDING_STUDY 4.13): one box per flat top a GASP LevelBlock_Traversable marker should cover (the
    coping / curb-head / landing hulls' top 2 cm, piece space), with the mantle verdict from the piece's height."""
    out = []
    for i, u in enumerate(st["ucx"]):
        kind = p.hull_kinds[i] if i < len(p.hull_kinds) else ""
        if kind not in ("wall_top", "landing", "foot_plinth"):
            continue
        lo, hi = u["min"], u["max"]
        deep = round(hi[1] - lo[1], 3)
        long_ = round(hi[0] - lo[0], 3)
        if deep < 0.49 or long_ < 0.60:
            continue
        h = p.extra.get("height_m")
        out.append({"hull": u["name"], "kind": kind, "min": [lo[0], lo[1], round(hi[2] - 0.02, 4)], "max": hi,
                    "top_slope_deg": 0.0, "depth_m": deep, "ledge_m": long_,
                    "mantle_from_foot": (None if h is None else bool(h + (hi[2] - 0.0) <= 2.75)),
                    "note": "place a hidden LevelBlock_Traversable over this box (GASP_TRAVERSAL.md); flat UCX top"})
    return out


def _batter_doc():
    out = {}
    for kind in ("straight", "sweep"):
        set_profile(kind)
        hs = HEIGHTS if kind == "straight" else SWEEP_HEIGHTS
        out[kind] = {"formula": ("d(s) = %.3f s (straight 1:10 batter)" % PA) if kind == "straight" else
                     ("d(s) = %.3f s + %.4f s^2 (concave castle sweep)" % (PA, PB)),
                     "pieces": "default names" if kind == "straight" else "*_Sweep (Wall_{2m,4m}_H{3,4,6}, CornerOut, "
                     "CornerIn, EndL, EndR, WallFoot_CornerOut / _CornerIn at H 3 / 4 / 6)",
                     "setback_at_foot_m": {str(h): round(d(h), 3) for h in hs},
                     "face_angle_from_vertical_deg": {str(s_): round(math.degrees(math.atan(
                         (d(s_ + 1e-3) - d(s_)) / 1e-3)), 1) for s_ in (0, 1, 2, 3, 4, 5, 6)},
                     "corner_flare": ("none (the sangi-zumi follow the straight batter)" if kind == "straight" else
                                      "outside corners: +%.3f s^2 outward at the arris, fading over %.1f m"
                                      % (FLARE_E, FLARE_R)),
                     "corner_in_arm_m": {str(h): arm_in(h) for h in hs}}
    set_profile("straight")
    out["default"] = "straight"
    out["mixing"] = ("never butt a straight piece against a Sweep piece of the same height: their faces part by "
                     "0.035 s^2 below grade; switch profiles only at a corner or an end")
    return out


def track_doc():
    return {
        "builder": "Scripts/dojo/stonekit/build_wall.py", "date": time.strftime("%Y-%m-%d"),
        "grid": {"plan_m": 1.0, "module_lengths_m": [2, 4], "corner_arm_m": CORNER_ARM, "heights_m": list(HEIGHTS),
                 "datum": "Z 0 = terrace grade (the dojo ground plane, the coping top); walls hang down",
                 "pivot": "face line at grade at the module start; face -> local -Y; fill -> +Y",
                 "bury_m": BURY, "coping_h_m": COPE_H, "coping_depth_m": COPE_D,
                 "tooth_m": TOOTH, "tooth_rule": "course k (COURSE_S) runs +TOOTH (even k) / -TOOTH (odd k) past the "
                                                 "grid line at both ends of every piece: neighbours interlock",
                 "course_s_m": COURSE_S},
        "batter": _batter_doc(),
        "assembly": {
            "straight": "place at the previous piece's 'end' snap, same yaw; walls of different H may sit side by "
                        "side (same face profile; the taller one's end below the shorter's foot is closed by core + "
                        "stones, cover it with terrain or a foot skirt)",
            "corner": "CornerOut: next pivot (1, 1, 0) yaw +90; CornerIn (every straight-profile height and "
                      "CornerIn_H3/H4_Sweep): next pivot (2, -2, 0) yaw -90; CornerIn_H6_Sweep: next pivot (3, -3, 0) "
                      "yaw -90 (a 3 m arm: the sweep pulls the corner line in 1.86 m at the 6 m foot); "
                      "WallCoping_CornerIn: (2, -2, 0)",
            "ends": "EndL starts a run (its 'end' snap feeds the first module), EndR closes one (placed at the last "
                    "module's 'end'); both return %.1f m into the slope" % END_RETURN,
            "foot": "WallFoot_* at each wall piece's 'foot' snap (same yaw): ONE continuous level footing course, "
                    "tops +%.2f over the nominal foot, %.2f proud of the face, buried to %.2f (f2: no skirt, no "
                    "loose rubble); a Sweep wall takes the *_Sweep corner feet" % (PLINTH_TOP, PLINTH_PROUD, PLINTH_BOT),
            "coping_alone": "WallCoping_* has the walls' top course alone (pivot at grade, same face line)",
            "dojo_wall_on_top": "kit 1's perimeter wall stands on the coping: its outer footing face 0.10 m behind "
                                "the coping arris (local y = +0.10 .. +1.10 for the 1.0 m kit-1 wall); its footing "
                                "sits at grade (kit 1 Z 0 = terrace Z 0); the dojo apron / paving meets the coping top "
                                "flush at Z 0 behind y = %.2f" % COPE_D,
            "stair_opening": "Wall_StairOpening_H{2,3,4}: a 4 m module; the stair path (track 9) continues from "
                             "'stair_foot' on the ground and 'stair_top' on the terrace; taller walls: split the "
                             "climb (a 4 m opening on a lower terrace, or track 9's flights on the slope)",
            "gasp": "walls are not walkable (straight batter 84.3 deg; Sweep 84-62 deg): only coping tops, landings, steps and curbs are; "
                    "H2 (2.0 m) is inside GASP's 2.75 m mantle ceiling, H3+ are not; traversal needs "
                    "LevelBlock_Traversable markers placed in the level (GASP_TRAVERSAL.md)"},
        "stairs": {"riser_target_m": RISER_T, "tread_m": TREAD, "clear_width_m": round(FLIGHT[1] - FLIGHT[0], 3),
                   "curb_w_m": CURB_W, "curb_top_above_nosing_m": CURB_UP,
                   "per_height": {str(h): {"risers": stair_numbers(h)[0], "riser_m": round(stair_numbers(h)[1], 4),
                                           "run_m": round((stair_numbers(h)[0] - 1) * TREAD, 3)} for h in (2, 3, 4)},
                   "gasp": "MaxStepHeight 45 cm >> riser 16.7 cm; pitch 27.5 deg < 44.77 walkable; collision = one "
                           "ramp hull through the nosings + sloped curb hulls"},
        "materials": {m: {"recipe": "M_DJ_Lib_Opaque instance: library Granite maps x Tint, FlattenToMean toward "
                                    "MeanColour = TEX_MEAN x Tint, moss lerp by VertexColor.A (KIT_MOSS), normal "
                                    "strength (UE FlattenNormal = 1 - strength), UseWear on, TileM (4, 4)",
                          "tint_linear": list(r["tint"]), "flatten_to_mean": r["flat"], "normal_strength": r["normal"],
                          "mean_linear": [round(a * b, 4) for a, b in zip(sk.TEX_MEAN, r["tint"])],
                          "moss_linear": list(r.get("moss", sk.KIT_MOSS))} for m, r in sk.KIT_MATS.items()},
        "materials_use": {"M_DKT_WallGranite": "face stones, sangi-zumi, curbs, the footing course",
                          "M_DKT_CopeGranite": "the coping / cap course and the curb heads (a little darker, moss on top)",
                          "M_DKT_JointDark": "the joint core behind the stones (moss by Wear.A)",
                          "M_DKT_StepGranite": "stair-opening treads and top landing (upward faces)",
                          "M_DKT_StepRiser": "stair-opening risers, step ends, undersides",
                          "wear_colours": "Wear RGBA per corner: R grime (AO + per-stone tone offset + darker "
                                          "undersides), G edge wear (+ light weathered tops on upward faces), B ground "
                                          "dirt, A moss (joints and ledges)"},
    }


# ------------------------------------------------------------------------------------------------ main
def piece_list():
    P = []
    sd = 800
    for L in (2, 4):
        for h in HEIGHTS:
            sd += 17
            P.append(("wall_straight", (L, h, sd)))
    for h in HEIGHTS:
        P.append(("wall_corner_out", (h, 900 + h)))
        P.append(("wall_corner_in", (h, 950 + h)))
        P.append(("wall_end", (h, 1000 + h, "R")))
        P.append(("wall_end", (h, 1050 + h, "L")))
    for h in (2, 3, 4):
        P.append(("wall_stair_opening", (h, 1100 + h)))
    P.append(("coping_straight", (2, 1201)))
    P.append(("coping_straight", (4, 1202)))
    P.append(("coping_corner", ("Out", 1203)))
    P.append(("coping_corner", ("In", 1204)))
    P.append(("foot_straight", (2, 1301)))
    P.append(("foot_straight", (4, 1302)))
    for h in HEIGHTS:
        P.append(("foot_corner", ("Out", h, 1310 + h)))
        P.append(("foot_corner", ("In", h, 1320 + h)))
    P = [(fn, a, "straight") for fn, a in P]
    # f2: the optional concave-sweep variant set (the r0 / f1 castle profile): modules, corners, ends, corner feet
    sd = 1800
    for L in (2, 4):
        for h in SWEEP_HEIGHTS:
            sd += 17
            P.append(("wall_straight", (L, h, sd), "sweep"))
    for h in SWEEP_HEIGHTS:
        P.append(("wall_corner_out", (h, 1900 + h), "sweep"))
        P.append(("wall_corner_in", (h, 1950 + h), "sweep"))
        P.append(("wall_end", (h, 2000 + h, "R"), "sweep"))
        P.append(("wall_end", (h, 2050 + h, "L"), "sweep"))
        P.append(("foot_corner", ("Out", h, 2310 + h), "sweep"))
        P.append(("foot_corner", ("In", h, 2320 + h), "sweep"))
    return P


def set_profile(kind):
    PROFILE["kind"] = kind
    PROFILE["suffix"] = "_Sweep" if kind == "sweep" else ""


def expected_name(fn, args):
    if fn == "wall_straight":
        return f"SM_DKT_Wall_{args[0]}m_H{args[1]}"
    if fn == "wall_corner_out":
        return f"SM_DKT_Wall_CornerOut_H{args[0]}"
    if fn == "wall_corner_in":
        return f"SM_DKT_Wall_CornerIn_H{args[0]}"
    if fn == "wall_end":
        return f"SM_DKT_Wall_End{args[2]}_H{args[0]}"
    if fn == "wall_stair_opening":
        return f"SM_DKT_Wall_StairOpening_H{args[0]}"
    if fn == "coping_straight":
        return f"SM_DKT_WallCoping_{args[0]}m"
    if fn == "coping_corner":
        return f"SM_DKT_WallCoping_Corner{args[0]}"
    if fn == "foot_straight":
        return f"SM_DKT_WallFoot_{args[0]}m"
    if fn == "foot_corner":
        return f"SM_DKT_WallFoot_Corner{args[0]}_H{args[1]}"


NANITE_MIN = 20000
LAYOUT_OUT = {"SM_DKT_Wall_4m_H3", "SM_DKT_Wall_4m_H4", "SM_DKT_Wall_2m_H2", "SM_DKT_Wall_4m_H6"}


def estimate_nanite(p):
    return p.g.tris() >= NANITE_MIN


def main():
    t0 = time.time()
    assert_owner("DojoStoneKit", "claude")
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    # materials: kit 1's (the footing stone + joint earth) and the library granite
    sk.kit_materials()          # f1: the kit granite family (wall, step tread / riser, joint core): sk_shared.KIT_MATS
    sk.lib_variants()           # f2: weathered timber, charcoal hood, warm amber (track 9's rails / lanterns; harmless here)
    djm.make_material(GR)
    T9 = track9()
    coll = bpy.data.collections.new("StoneKit_Wall")
    sc.collection.children.link(coll)
    build, qa_rep, exp_rep, cat = {}, {}, {}, {}
    funcs = {"wall_straight": wall_straight, "wall_corner_out": wall_corner_out, "wall_corner_in": wall_corner_in,
             "wall_end": wall_end, "wall_stair_opening": wall_stair_opening, "coping_straight": coping_straight,
             "coping_corner": coping_corner, "foot_straight": foot_straight, "foot_corner": foot_corner}
    for fn, args, prof in piece_list():
        set_profile(prof)
        name = expected_name(fn, args) + PROFILE["suffix"]
        if ONLY and name not in ONLY:
            continue
        t1 = time.time()
        sk.layout_reset(name)
        p = funcs[fn](*args)
        if name in LAYOUT_OUT:                 # f2r2: the flat layout record for the study's SG3 / SG4 / SG7 / SG9 gates
            sk.write_layout(OUT / f"layout_{name.replace('SM_DKT_', '')}.json")
        assert p.name == name, (p.name, name)
        p.nanite = estimate_nanite(p)
        t2 = time.time()
        # the Geo -> mesh (sk_shared.build_mesh: library UVs, Wear, moss, UCX); no UV1 on Nanite pieces
        o, bad = sk.build_mesh(p, coll, _Shim(p.nanite))
        build[p.name] = {"tris": sum(len(q.vertices) - 2 for q in o.data.polygons), "bad_faces": bad,
                         "geo_sec": round(t2 - t1, 1), "mesh_sec": round(time.time() - t2, 1), "nanite": p.nanite,
                         "ucx": len(p.hulls), "extra": p.extra}
        print("BUILT", p.name, build[p.name], flush=True)
        r = qa_check([o], require_uv1=not p.nanite, texel_density=5.12, tolerance=0.25)
        fails = [c for c in r["checks"] if not c["passed"]]
        hard = [c for c in fails if c["name"] not in sk.WAIVE]
        qa_rep[p.name] = {"hard_fails": [{"name": c["name"], "object": c["object"], "detail": str(c["detail"])[:300]}
                                         for c in hard],
                          "waived": sorted({c["name"] for c in fails if c["name"] in sk.WAIVE}),
                          "tris": r["triangles"].get(o.name), "uv1": not p.nanite,
                          "texel": next((c["detail"] for c in r["checks"] if c["name"] == "texel_density"), "")}
        for c in hard:
            print("  QA FAIL", p.name, c["name"], str(c["detail"])[:200], flush=True)
        if "--no-export" not in ARGS and not hard:
            try:
                exp_rep[p.name] = sk.export_piece(o, _Shim(False), lods=not p.nanite)
            except Exception as e:  # noqa: BLE001
                exp_rep[p.name] = {"error": repr(e)}
                print("  EXPORT FAIL", p.name, repr(e), flush=True)
        cat[p.name] = catalog_entry(p, o, qa_rep[p.name], exp_rep.get(p.name))
    hard_total = sum(len(v["hard_fails"]) for v in qa_rep.values())
    (OUT / "build_report.json").write_text(json.dumps(build, indent=1, default=str), encoding="utf-8")
    (OUT / "qa_report.json").write_text(json.dumps(qa_rep, indent=1, default=str), encoding="utf-8")
    (OUT / "export_report.json").write_text(json.dumps(exp_rep, indent=1, default=str), encoding="utf-8")
    print(f"QA wall: {len(qa_rep)} pieces, hard fails {hard_total}", flush=True)
    if ONLY is None:
        sk.merge_catalog(TRACK, {"track": track_doc(), "pieces": cat}, PREFIX)
    else:
        (OUT / "catalog_partial.json").write_text(json.dumps(cat, indent=1), encoding="utf-8")
    coll.hide_render = False
    bpy.ops.wm.save_as_mainfile(filepath=str(TRACK_BLEND if ONLY is None else OUT / "DojoStoneKit_wall_partial.blend"))
    if ONLY is None and "--no-export" not in ARGS:
        merge_into_kit_blend()
    print("DONE seconds", round(time.time() - t0, 1), flush=True)


class _Shim:
    """sk_shared.build_mesh calls K1.add_uv1(obj): skip it for Nanite pieces (hint), else kit 1's checked packer."""

    def __init__(self, nanite):
        self.nanite = nanite

    def add_uv1(self, obj):
        if not self.nanite:
            K1.add_uv1(obj)

    def fix_lod(self, obj):
        K1.fix_lod(obj)


def fold_duplicates():
    """f1: the appended collection brings its own copies of the shared kit materials / images / node groups (named
    '<name>.001' when track 9 already put them in the file): remap them onto the originals (as build_stairs does)."""
    return sk.fold_into_kit()          # f2: the kit's own recipes take the NEW copy (sk_shared.fold_into_kit)


def merge_into_kit_blend():
    """Put this track's collection into the shared Assets/Dojo/DojoStoneKit.blend (other tracks' collections kept),
    under sk_shared.file_lock."""
    with sk.file_lock(sk.BLEND):
        if sk.BLEND.exists():
            bpy.ops.wm.open_mainfile(filepath=str(sk.BLEND))
        else:
            bpy.ops.wm.read_factory_settings(use_empty=True)
        sk.drop_collection_for_append("StoneKit_Wall")     # f2: objects, meshes, own materials, orphans
        with bpy.data.libraries.load(str(TRACK_BLEND), link=False) as (src, dst):
            dst.collections = ["StoneKit_Wall"]
        for c in dst.collections:
            if c is not None:
                bpy.context.scene.collection.children.link(c)
        fold_duplicates()
        bpy.data.orphans_purge(do_recursive=True)
        sk.BLEND.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(sk.BLEND))
        print("merged StoneKit_Wall into", sk.BLEND, flush=True)


main()
