"""t7 (2026-10-03, judge r6 item 1: "the parametric lobe generator has missed this in t5 and t6, so change the method"):
the hide skirt below each collar BUILT FROM A TRACE OF THE USER'S PHOTO (pure Python: build_taiko imports it inside
Blender, the t7 fitting / check scripts under system Python).

The 2D outline authority is skirt_trace_t7.json (WorkFiles/dojo/build/props/taiko/t7/trace_skirt_t7.py): the photo's
hem traced column by column in its fitted camera and unprojected onto our collar (lathe angle th -> the hem's depth
below the skirt root X_SK), the slits picked lobe by lobe, and the photo's outline per row through the skirt rows (the
ears). Lobe by lobe:
  * slits at the traced angles on the photo's front (FRONT_TH, design angles; the photo camera faces 4.88 deg); round
    the back (unseen) the front's lobe widths and hem shapes repeat in a fixed shuffled order (whole lobes only); two
    ears per head at the photo's left / right silhouettes, plus the shoulder lobe(s) in front of and the lobe right
    behind each ear: their angle, width, lift, depth, flare and roll fitted to the photo's outline rows
    (t7/fit_ears_t7.py -> skirt_ears_t7.json, which overrides EARS below).
  * every lobe column's hem (the rolled lip's lowest point) at the traced depth for its angle (back lobes: the copied
    front lobe's shape, corrected linearly to meet the slit values at both ends).
  * the sheet tucks SK_BURY under the collar (t6's tangential tuck), lies on the wood, bellies out BULGE (4-8 mm) in
    the lobe's middle (zero at the root and the lip), and its hem ROLLS OUTWARD into a lip of centre-line radius
    RHO_HEAD (18 mm upper head, 13 mm lower; design) through 180-210 deg (the photo's fat rolled tubes).
  * "close" lobes lie on the wood: centre-line lift H 0.8-2.5 mm, the lip's underside a few mm off the lacquer; the
    ears stand off (a rounded hump across the lobe, (1 - u^2)^1.5), their shoulder / behind lobes as fitted.
  * slits are OPEN V cuts: the two edges meet at the slit tip (shared vertices above it) and part (as the square root
    of the way down: a slot) to W_SLIT (8-13 mm design, 8.9-14.4 mm real) at the lip, which stays open round the roll,
    so the tube ends show (the photo's dark slots and C-shaped tube ends).
  * the cradle: within 50 deg of -Z (under the drum in the stand) the hem stays above X_TAB_MIN (the beams' outer faces).
UV (COLLAR material): U = taiko_uv.COLLAR_U_SK minus the arc length below the root (outer; inner + 0.01), V by angle.

t8 (2026-10-04, judge r7 item 3: "a thin segmented tube glued under a flat apron"; the photo's hide rolls outward):
  * the hem is no longer a thin sheet curled 250-285 deg (its free end pressed on the apron left a hard crease and a
    shadow line along the tube's top) but a SOLID rolled BEAD: the outer surface runs down the apron, turns outward
    through a concave fillet of radius RF (9 mm design, 10 mm real: tangent-continuous, no seam) onto a round bead of
    outer radius RO_HEAD (16 mm upper / 12.5 mm lower design; its centre BEAD_SIT x RO off the sheet's inner line),
    round its outside and bottom (the hem's lowest point at the traced depth) and back to the sheet's inner line; the
    inner surface runs straight on along the sheet underneath. The ears get the same full bead (about 35 / 28 mm real
    thick; t7: thin partial curls).
  * slits: the bead TAPERS into each slit (RO x TAPER_NEAR on an extra column NEAR_SLIT from the slit, x TAPER_SLIT on
    the slit edge), so it rounds off into a small end instead of a flat tube-section cap; the slit opens W_SLIT 10-13.5
    mm design (11-15 mm real) at the hem (t7 8-13), so its dark interior shows.
  * UV: U is clamped to >= U_MIN (the long ear / bead arcs ran below U 0 and wrapped onto the WHITE end of the collar
    strip: the white shards at the hem beside the ears); the bead's underside and the slit faces stay in the gold.
"""
import json
import math
import random
from pathlib import Path

import taiko_uv as UVL

HERE = Path(__file__).resolve().parent
TRACE = json.loads((HERE / "skirt_trace_t7.json").read_text(encoding="utf-8"))

COLLAR_T = 0.0045
SK_T = 0.003
SK_BURY, SK_TUCK_IN, SK_PROUD = 0.005, 0.0006, 0.0002
RHO = 0.018                 # rolled lip: centre-line radius (design; real 19.9 mm, outer diameter 2 RHO + SK_T 43 mm):
#                             the photo's rolled hems read 25-35 mm tall from its camera (12 mm read as a thin bead)
RO_HEAD = {1: 0.016, -1: 0.0125}  # t8: the solid bead's outer radius per head (design; t7's tube: centre-line rho
#                                    14.5 / 11 + half the sheet)
RF = 0.009                  # t8: the apron-to-bead concave fillet radius (design; 10 mm real, the judge's >= 8 mm)
BEAD_SIT = 0.75             # t8: the bead centre this many RO off the sheet's inner line (the bead sits on the sheet)
TAPER_SLIT, TAPER_NEAR = 0.32, 0.72   # t8: bead radius factor on the slit edge column / the column NEAR_SLIT from it
NEAR_SLIT = 0.012           # t8: (design m) the extra column beside each slit
A_E_MIN = 0.018              # t8: the flare runs at least this far (design m) below the root before the bead starts
U_MIN = 0.012               # t8: the collar U floor (the strip's U < 0 wraps onto its white end)
RHO_HEAD = {1: 0.0145, -1: 0.011}  # (t7) per head (the photo's lower skirt shows smaller rolls); with the 250-285 deg curl the
#                                    tube stands 2 rho tall, as the photo's rolled tubes (a 180-210 deg curl read as a
#                                    half-round bead, 1.3 rho tall, beside them)
BEND_A = 0.002
NF = 3                      # flare rows (tip -> roll start)
NR_F, NR_B = 2, 7           # t8: bead rows: the concave fillet (2) and the bead (7, about 33 deg a step); t7: 6 roll rows
NR = NR_F + NR_B
B_TIP = 3                   # rows: 0 buried edge, 1 root (X_SK), 2 half way to the tip, 3 the slit tip
B_HEM = B_TIP + NF          # the roll starts here
NB = B_HEM + NR + 1
H_CLOSE = (0.0008, 0.0025)  # centre-line lift of the close lobes (lip underside <= 4.2 mm design, 4.7 mm real)
BULGE = (0.004, 0.008)      # the lobe's belly across its middle, mid-flare only (zero at the root and at the lip: the
#                             lip still lies on the wood); t7 renders: 1.5-3.5 mm read flat beside the photo's pillowy lobes
ROLL_MID, ROLL_SLIT = (250.0, 270.0), (265.0, 285.0)   # a nearly closed tube (the end 0.7-1 rho off the sheet)
W_SLIT = (0.010, 0.0135)    # t8: open V width at the hem (t7 0.008-0.013: 1-2 px hairlines from the photo camera)
L_SLIT = {1: (0.034, 0.046), -1: (0.028, 0.038)}   # t8: shorter (the opened V slits read 25-30 px tall from the
#                             photo camera, the photo's about 20; t7: 48-62 / 36-48 mm); slit length along the sheet, tip to the hem's lowest point (the
#                             photo's slots run 20-30 mm above the rolled lip)
P_CLOSE = 1.3
FRONT_TH = (-60.1, 60.0)    # the photo's front: slits trusted here (deg; t7 design angles, the photo faces 4.99 deg)
HEM_TH = {1: (-46.0, 45.0), -1: (-44.0, 47.0)}   # hem samples trusted here (deg; the ends near the ears are noisy)
CRADLE_TH, CRADLE_HALF = -90.0, 50.0
# the ears (t7/fit_ears_t7.py: fitted to the photo's outline rows in its camera). Per head (+1 = +X, the photo's
# upper skirt; -1 = the lower) and side (-1 = th < 0, the photo's left = -Z; +1 = right = +Z): centre angle (deg),
# width (design m), centre-line lift H, hem depth below X_SK, flare exponent p (< 1: steep near the root, then along
# the body, the photo's curled-up ear), roll (deg)
EARS = {
    (1, -1): dict(th=-83.26, w=0.090, H=0.0284, a_low=0.100, p=1.566, roll=215.0, sh_H=0.004, sh_alow=0.09, sh_p=1.3, sh_roll=200.0, bk_H=0.002, bk_alow=0.07, bk_p=1.3, bk_roll=200.0),
    (1, 1): dict(th=87.91, w=0.190, H=0.0382, a_low=0.0526, p=0.45, roll=120.0, sh_H=0.004, sh_alow=0.09, sh_p=1.3, sh_roll=200.0, bk_H=0.002, bk_alow=0.07, bk_p=1.3, bk_roll=200.0),
    (-1, -1): dict(th=-87.65, w=0.190, H=0.0288, a_low=0.0532, p=0.45, roll=151.5, sh_H=0.004, sh_alow=0.07, sh_p=1.3, sh_roll=200.0, bk_H=0.002, bk_alow=0.07, bk_p=1.3, bk_roll=200.0),
    (-1, 1): dict(th=83.49, w=0.171, H=0.0314, a_low=0.035, p=1.50, roll=215.0, sh_H=0.004, sh_alow=0.07, sh_p=1.3, sh_roll=200.0, bk_H=0.002, bk_alow=0.07, bk_p=1.3, bk_roll=200.0),
}

for _EF in (HERE / "skirt_ears_t7.json", HERE / "skirt_ears_t8.json"):   # t7/fit_ears_t7.py, then t8/fit_ears_t8.py (the
    if _EF.exists():                                                      # bead's refit) write the fitted values here
        for _k, _v in json.loads(_EF.read_text(encoding="utf-8")).items():
            EARS[tuple(int(q) for q in _k.strip("()").split(","))] = dict(EARS.get(tuple(int(q) for q in _k.strip("()").split(",")), {}), **_v["params"])


def body_r(x):
    return UVL.body_r(x)


def _interp(xq, xs, ys):
    if xq <= xs[0]:
        return ys[0]
    if xq >= xs[-1]:
        return ys[-1]
    lo, hi = 0, len(xs) - 1
    while hi - lo > 1:
        m = (lo + hi) // 2
        if xs[m] <= xq:
            lo = m
        else:
            hi = m
    t = (xq - xs[lo]) / (xs[hi] - xs[lo])
    return ys[lo] + (ys[hi] - ys[lo]) * t


def wrap(d):
    return (d + 180.0) % 360.0 - 180.0


def layout(s, ears=None, seed=None):
    """the per-head lobe layout: slit angles (deg, increasing, one full turn from slits[0]), per slit (a_low, a_tip,
    H, p, roll, w), per lobe (ear flag, H, bulge, roll, p, hem function of the fraction across the lobe)"""
    ears = ears or EARS
    key = "upper" if s > 0 else "lower"
    tr = TRACE[key]
    rng = random.Random(seed if seed is not None else 7011 + 13 * s)
    xsk = UVL.X_SK
    hem = sorted((math.degrees(th), xsk - x) for _u, _v, x, th in tr["hem_samples_u_v_x_th"])
    lo_t, hi_t = HEM_TH[s]
    hem = [q for q in hem if lo_t <= q[0] <= hi_t]
    h_th, h_a = [q[0] for q in hem], [q[1] for q in hem]
    # light smoothing (5 samples ~ 1 deg)
    h_a = [sum(h_a[max(0, i - 2):i + 3]) / len(h_a[max(0, i - 2):i + 3]) for i in range(len(h_a))]
    front_hem = lambda t: _interp(t, h_th, h_a)   # noqa: E731
    fs = sorted(math.degrees(th) for _u, _v, _x, th in tr["slits_u_v_x_th"])
    fs = [t for t in fs if FRONT_TH[0] <= t <= FRONT_TH[1]]
    front_lobes = list(zip(fs, fs[1:]))              # (start, end) deg
    # the ears and the back: fill (last front slit .. right ear), (right ear .. left ear + 360), (left ear .. first)
    eL, eR = ears[(s, -1)], ears[(s, 1)]
    r_ref = body_r(xsk - 0.06) + 0.004
    wdeg = lambda w: math.degrees(w / r_ref)          # noqa: E731
    eR0, eR1 = eR["th"] - 0.5 * wdeg(eR["w"]), eR["th"] + 0.5 * wdeg(eR["w"])
    eL0, eL1 = eL["th"] - 0.5 * wdeg(eL["w"]) + 360.0, eL["th"] + 0.5 * wdeg(eL["w"]) + 360.0
    pool = [(a, b) for a, b in front_lobes if b - a > 3.0]
    order = list(range(len(pool)))
    rng.shuffle(order)
    cyc = [pool[i] for i in order]
    ci = [0]

    def fill(t0, t1):
        """lobes copied from the front (widths scaled to fill t0..t1 exactly)"""
        span = t1 - t0
        mean_w = sum(b - a for a, b in cyc) / len(cyc)
        n = max(1, int(round(span / mean_w)))          # whole lobes only (no slivers: every lobe >= ~0.5 x mean)
        picks = [cyc[(ci[0] + j) % len(cyc)] for j in range(n)]
        ci[0] += n
        tot = sum(b - a for a, b in picks)
        k = span / tot
        out, t = [], t0
        for a, b in picks:
            w = (b - a) * k
            out.append(("copy", t, t + w, (a, b)))
            t += w
        return out
    def shoulder(t0, t1, key):
        """t7: the span between the traced front and an ear: its lobes (as copied) get the ear's fitted shoulder
        lift / depth / flare / roll (the photo's outline stands off there too)"""
        return [("shoulder", a, b, key) for _k, a, b, _src in fill(t0, t1)]
    lobes = [("front", a, b, None) for a, b in front_lobes]
    back = fill(eR1, eL0)
    back[0] = ("back", back[0][1], back[0][2], (s, 1))          # the lobe right behind each ear: its own fit too
    back[-1] = ("back", back[-1][1], back[-1][2], (s, -1))
    lobes += shoulder(fs[-1], eR0, (s, 1)) + [("ear", eR0, eR1, (s, 1))] + back + [("ear", eL0, eL1, (s, -1))]
    lobes += shoulder(eL1, fs[0] + 360.0, (s, -1))
    slits = [lb[1] for lb in lobes]
    nS = len(slits)

    def hem_src(lb, f):
        kind, a, b, src = lb
        if kind == "front":
            return front_hem(wrap(a + f * (b - a)))
        if kind == "copy":
            return front_hem(src[0] + f * (src[1] - src[0]))
        return None

    def mid_val(lb):
        kind, _a, _b, src = lb
        return ears[src]["a_low"] if kind == "ear" else (ears[src]["sh_alow"] if kind == "shoulder" else (
            ears[src]["bk_alow"] if kind == "back" else None))

    # slit hem values: the mean of the two lobes' end values (ears take their neighbour's)
    sl = []
    for k in range(nS):
        L, R = lobes[k - 1], lobes[k]
        vals = [v for v in (hem_src(L, 1.0), hem_src(R, 0.0)) if v is not None] or \
            [v for v in (mid_val(L), mid_val(R)) if v is not None]
        sl.append({"th": slits[k], "a_low": sum(vals) / len(vals),
                   "H": rng.uniform(*H_CLOSE), "p": P_CLOSE, "roll": rng.uniform(*ROLL_SLIT),
                   "w": rng.uniform(*W_SLIT), "len": rng.uniform(*L_SLIT[s])})
    for k in range(nS):                                     # the cradle: hems clear the beams' outer faces
        if abs(wrap(sl[k]["th"] - CRADLE_TH)) <= CRADLE_HALF:
            sl[k]["a_low"] = min(sl[k]["a_low"], A_LOW_MAX)
    lb_out = []
    for k, lb in enumerate(lobes):
        kind, a, b, src = lb
        e = ears.get(src) if kind == "ear" else None
        sh = ears.get(src) if kind in ("shoulder", "back") else None
        if sh is not None:
            pf = "sh_" if kind == "shoulder" else "bk_"
            e2 = {"H": sh[pf + "H"], "p": sh[pf + "p"], "roll": sh[pf + "roll"], "a_low": sh[pf + "alow"]}
        d = {"kind": kind, "th0": a, "th1": b, "src": src, "ear": e is not None, "shoulder": sh is not None,
             "H": e["H"] if e else (e2["H"] if sh else rng.uniform(*H_CLOSE)),
             "p": e["p"] if e else (e2["p"] if sh else P_CLOSE),
             "roll": e["roll"] if e else (e2["roll"] if sh else rng.uniform(*ROLL_MID)),
             "bulge": 0.0 if (e or sh) else rng.uniform(*BULGE),
             "a_low_mid": e["a_low"] if e else (e2["a_low"] if sh else None)}
        lb_out.append(d)
    # a slit beside an ear / shoulder / back lobe (fitted curls 110-215 deg) takes the mean of its two lobes' curls, so
    # no column-to-column jump from a closed tube (265-285 deg) to an open curl folds the lip through itself
    for k in range(nS):
        L_, R_ = lb_out[k - 1], lb_out[k]
        if L_["ear"] or L_["shoulder"] or R_["ear"] or R_["shoulder"]:
            sl[k]["roll"] = min(sl[k]["roll"], 0.5 * (L_["roll"] + R_["roll"]))
    return {"s": s, "slits": sl, "lobes": lb_out, "hem_src": hem_src, "lobes_raw": lobes}


A_LOW_MAX = 0.1  # (set by build_taiko from X_TAB_MIN: X_SK - X_TAB_MIN - SK_T / 2 - 0.001)


def profile(H, a_low, a_tip, p, ro):
    """t8: the skirt's cross-section in the (a, n) plane (a = depth below X_SK along the axis, n = height above the
    wood). Rows 0 .. B_HEM: the sheet's centre line (the buried edge, the root, the flare n = n0 + H t^p to the bead
    start a_e), offset +-SK_T / 2 to the outer / inner surface. Rows B_HEM + 1 .. NB - 1: the OUTER surface runs through
    the concave fillet (radius RF) onto the bead (outer radius ro, centre BEAD_SIT ro off the inner line), round its
    outside and bottom (the lowest point, max a, lands on a_low) back to the inner line; the INNER surface runs straight
    on along the sheet (monotone, so every slit cap row pairs up). Returns (outer rows, inner rows, the centre a per
    row (the belly's ramp), the arc length per row from the root (outer), the flare angle at a_e (deg), a_e)."""
    n0 = COLLAR_T + SK_PROUD - 0.5 * SK_T
    n_b = COLLAR_T - SK_TUCK_IN - 0.5 * SK_T
    for _try in range(14):    # a shallow hem (a_low small) cannot hold the full bead: shrink it until the flare fits
        nb = BEAD_SIT * ro - 0.5 * SK_T
        hh = SK_T + RF - BEAD_SIT * ro
        d_t = math.sqrt(max(1e-8, (RF + ro) ** 2 - hh * hh))
        a_e = a_low - ro - d_t
        for _ in range(16):
            al = math.atan(H * p / max(1e-4, a_e - BEND_A))
            a_e = a_low - ro - d_t * math.cos(al) + nb * math.sin(al)
        if a_e >= A_E_MIN and math.degrees(math.atan(H * p / max(1e-4, a_e - BEND_A))) <= 70.0:
            break
        ro *= 0.88
    al = math.atan(H * p / max(1e-4, a_e - BEND_A))
    a_tip = min(a_tip, a_e - 0.006)

    def nn(a):
        t = max(0.0, (a - BEND_A) / (a_e - BEND_A))
        return n0 + H * t ** p, math.atan(H * p * max(t, 1e-6) ** (p - 1) / (a_e - BEND_A)) if t > 0 else 0.0
    cen = [(-SK_BURY, n_b, math.atan((n0 - n_b) / SK_BURY)), (0.0, n0, 0.0)]
    for a in [0.5 * a_tip, a_tip] + [a_tip + (a_e - a_tip) * j / NF for j in range(1, NF + 1)]:
        cen.append((a,) + nn(a))

    def off(q, o):
        return (q[0] - o * math.sin(q[2]), q[1] + o * math.cos(q[2]))
    outer = [off(q, 0.5 * SK_T) for q in cen]
    inner = [off(q, -0.5 * SK_T) for q in cen]
    acen = [q[0] for q in cen]
    ae, ne = cen[-1][0], cen[-1][1]
    ca, sa = math.cos(al), math.sin(al)

    def loc(t, n):            # the bead's frame: t along the sheet's end tangent, n along its outward normal
        return (ae + t * ca - n * sa, ne + t * sa + n * ca)
    fc = (0.0, 0.5 * SK_T + RF)
    bc = (d_t, nb)
    th2 = math.atan2(bc[1] - fc[1], bc[0] - fc[0])
    t_out = []
    for k in range(1, NR_F + 1):
        th = -0.5 * math.pi + (th2 + 0.5 * math.pi) * k / NR_F
        outer.append(loc(fc[0] + RF * math.cos(th), fc[1] + RF * math.sin(th)))
        t_out.append(fc[0] + RF * math.cos(th))
    phi0 = th2 + math.pi
    phi_end = -math.asin(min(0.999, (nb + 0.5 * SK_T) / ro))
    for k in range(1, NR_B + 1):
        ph = phi0 + (phi_end - phi0) * k / NR_B
        outer.append(loc(bc[0] + ro * math.cos(ph), bc[1] + ro * math.sin(ph)))
        t_out.append(bc[0] + ro * math.cos(ph))
    t_cap = bc[0] + ro * math.cos(phi_end) - 0.0015
    t_in = [min(t_, t_cap) for t_ in t_out]
    t_in[-1] = t_cap
    for k in range(len(t_in) - 2, -1, -1):
        t_in[k] = min(t_in[k], t_in[k + 1] - 0.0012)
    for t_ in t_in:
        inner.append(loc(t_, -0.5 * SK_T))
        acen.append(ae)
    arc = [0.0]
    for q0, q1 in zip(outer, outer[1:]):
        arc.append(arc[-1] + math.hypot(q1[0] - q0[0], q1[1] - q0[1]))
    arc = [x_ - arc[1] for x_ in arc]
    return outer, inner, acen, arc, math.degrees(al), a_e


def slit_tip(sp, ro):
    """the slit's tip depth so that it runs sp['len'] along the sheet to the hem's lowest point"""
    lo_a, hi_a = 0.004, sp["a_low"] - 0.02
    for _ in range(30):
        mid = 0.5 * (lo_a + hi_a)
        _o, _i, _c, arc, al, a_e = profile(sp["H"], sp["a_low"], mid, sp["p"], ro)
        length = (arc[B_HEM] - arc[B_TIP]) + ro * math.radians(max(0.0, 90.0 - al))
        if length > sp["len"]:
            lo_a = mid
        else:
            hi_a = mid
    return 0.5 * (lo_a + hi_a)


def mesh(s, lay=None, ears=None, uv=True):
    """the skirt of head s as (verts, faces, face_uvs, info); DESIGN units"""
    lay = lay or layout(s, ears)
    sl, lobes = lay["slits"], lay["lobes"]
    nS = len(sl)
    for sp in sl:
        sp["a_tip"] = slit_tip(sp, TAPER_SLIT * RO_HEAD[s])
    two_pi = 2 * math.pi
    v_org = math.radians(lobes[0]["th0"])        # V = 0 at slit 0 (the skirt's V seam sits in a slit)
    verts, idx, uvmap = [], {}, {}
    faces, fuv = [], []
    info_cols, lip_gap, crest = [], [], []

    def edge_off(sp, b):
        if b <= B_TIP:
            return 0.0
        if b <= B_HEM:
            return 0.5 * sp["w"] * math.sqrt((b - B_TIP) / NF)   # opens fast below the tip: a slot, not a hairline
        return 0.5 * sp["w"]
    for k, lb in enumerate(lobes):
        spL, spR = sl[k], sl[(k + 1) % nS]
        th0, th1 = math.radians(lb["th0"]), math.radians(lb["th1"])
        W = (th1 - th0) * (body_r(UVL.X_SK - 0.06) + 0.004)
        n_int = max(6 if lb["ear"] else 2, int(round(W / (0.028 if lb["ear"] else 0.042))))
        fr = [j / (n_int + 1) for j in range(n_int + 2)]
        dn = NEAR_SLIT / W                   # t8: an extra column NEAR_SLIT from each slit (the bead's taper)
        if dn < 0.6 * fr[1]:
            fr = [0.0, dn] + fr[1:-1] + [1.0 - dn, 1.0]
        near = (1, len(fr) - 2) if dn < 0.6 * (1.0 / (n_int + 1)) else ()
        src_hem = [lay["hem_src"](lay["lobes_raw"][k], f) for f in fr]
        if src_hem[0] is None or lb.get("shoulder"):   # an ear / shoulder: its own depth in the middle, the slits' at the edges
            src_hem = [spL["a_low"] + (spR["a_low"] - spL["a_low"]) * f for f in fr]
        else:                             # corrected linearly to the slit values at both ends
            src_hem = [h + (1 - f) * (spL["a_low"] - src_hem[0]) + f * (spR["a_low"] - src_hem[-1])
                       for f, h in zip(fr, src_hem)]
        for j, f in enumerate(fr):
            u = 2 * f - 1
            if j == 0:
                prm, cid = spL, ("s", k)
            elif j == len(fr) - 1:
                prm, cid = spR, ("s", (k + 1) % nS)
            else:
                m = (1 - abs(u) ** 2.2) if not lb["ear"] else (1 - u * u) ** 1.5
                sp_n = spL if f < 0.5 else spR
                a_low = src_hem[j]
                if lb["ear"] or lb.get("shoulder"):
                    a_low = a_low + (lb["a_low_mid"] - a_low) * m
                th_c = math.degrees(th0 + f * (th1 - th0))
                if abs(wrap(th_c - CRADLE_TH)) <= CRADLE_HALF:
                    a_low = min(a_low, A_LOW_MAX)
                tn = min(1.0, abs(u) / 0.6)
                prm = {"H": sp_n["H"] + (lb["H"] - sp_n["H"]) * m,
                       "a_low": a_low,
                       "p": sp_n["p"] + (lb["p"] - sp_n["p"]) * m,
                       "roll": lb["roll"] + (sp_n["roll"] - lb["roll"]) * tn ** 2,
                       "a_tip": spL["a_tip"] * (1 - f) + spR["a_tip"] * f}
                cid = ("i", k, j)
            a_tip = prm.get("a_tip", None) if j not in (0, len(fr) - 1) else prm["a_tip"]
            ro = RO_HEAD[s] * (TAPER_SLIT if j in (0, len(fr) - 1) else (TAPER_NEAR if j in near else 1.0))
            po, pi_, acen, arc, al, a_e = profile(prm["H"], prm["a_low"], a_tip, prm["p"], ro)
            bulge = 0.0 if j in (0, len(fr) - 1) else lb["bulge"] * (1 - u * u)
            if j not in (0, len(fr) - 1):
                info_cols.append((lb["ear"], prm["H"], prm["a_low"], al))
            side = "L" if j == 0 else ("R" if j == len(fr) - 1 else 0)
            lip_lo = 1e9
            for layer in (0, 1):
                o = (0.5 if layer == 0 else -0.5) * SK_T
                for b in range(NB):
                    a_, n_ = (po if layer == 0 else pi_)[b]
                    a = acen[b]
                    if 1 < b <= B_HEM and a_e > 0:
                        n_ += bulge * math.sin(math.pi * min(1.0, max(0.0, a / a_e)))
                    x = UVL.X_SK - a_
                    r = body_r(x) + n_
                    dL = edge_off(spL, b) / r
                    dR = edge_off(spR, b) / r
                    ang = th0 + dL + f * ((th1 - th0) - dL - dR)
                    if cid[0] == "s":
                        key = (layer, b, cid, 0 if b <= B_TIP else side)
                    else:
                        key = (layer, b, cid)
                    if key not in idx:
                        idx[key] = len(verts)
                        verts.append((s * x, r * math.cos(ang), r * math.sin(ang)))
                    uvmap[(key, k)] = (max(U_MIN, UVL.COLLAR_U_SK - arc[b] / UVL.COLLAR_TILE_U + 0.01 * layer),
                                       0.005 + (UVL.COLLAR_WRAPS - 0.01) * (ang - v_org) / two_pi)
                    if b >= B_HEM:
                        lip_lo = min(lip_lo, n_)
            if j not in (0, len(fr) - 1):
                lip_gap.append((lb["ear"], lip_lo, abs(u) < 0.34))
        lb["cols"] = [(("s", k) if j == 0 else (("s", (k + 1) % nS) if j == len(fr) - 1 else ("i", k, j)),
                       "L" if j == 0 else ("R" if j == len(fr) - 1 else 0)) for j in range(len(fr))]

    def key_of(layer, b, cid, side):
        if cid[0] == "s":
            return (layer, b, cid, 0 if b <= B_TIP else side)
        return (layer, b, cid)

    def quad(keys, ctx):
        faces.append(tuple(idx[q] for q in keys))
        fuv.append([uvmap[(q, ctx)] for q in keys])
    for k, lb in enumerate(lobes):
        cols = lb["cols"]
        nc = len(cols)
        o = lambda b, a: key_of(0, b, *cols[a])   # noqa: E731
        i_ = lambda b, a: key_of(1, b, *cols[a])  # noqa: E731
        for b in range(NB - 1):
            for a in range(nc - 1):
                quad((o(b, a), o(b, a + 1), o(b + 1, a + 1), o(b + 1, a)), k)
                quad((i_(b, a), i_(b + 1, a), i_(b + 1, a + 1), i_(b, a + 1)), k)
        for b in range(B_TIP, NB - 1):            # the two slit walls (below the tips)
            quad((o(b, 0), o(b + 1, 0), i_(b + 1, 0), i_(b, 0)), k)
            quad((o(b, nc - 1), i_(b, nc - 1), i_(b + 1, nc - 1), o(b + 1, nc - 1)), k)
        for a in range(nc - 1):                   # the buried top edge and the lip's cut edge
            quad((o(0, a), i_(0, a), i_(0, a + 1), o(0, a + 1)), k)
            quad((o(NB - 1, a), o(NB - 1, a + 1), i_(NB - 1, a + 1), i_(NB - 1, a)), k)
    # report
    mm = lambda v: [round(1000 * min(v), 1), round(1000 * max(v), 1)] if v else None   # noqa: E731
    close_gap = [g for e, g, mid in lip_gap if not e and mid]
    ear_gap = [g for e, g, mid in lip_gap if e and mid]
    widths = [math.radians(lb["th1"] - lb["th0"]) * (body_r(UVL.X_SK - 0.06) + 0.004) for lb in lobes]
    info = {"construction": "t8: traced from the user's photo (skirt_trace_t7.json); %d lobes / slits, %d ears; open "
                            "V slits; a solid rolled bead of outer radius %.1f mm design through a %.0f mm fillet, "
                            "tapered into each slit" % (nS, sum(lb['ear'] for lb in lobes), 1000 * RO_HEAD[s], 1000 * RF),
            "lobes": nS, "front_lobes_traced": sum(lb["kind"] == "front" for lb in lobes),
            "back_lobes_copied": sum(lb["kind"] == "copy" for lb in lobes),
            "lobe_width_design_mm_min_max": mm(widths),
            "ears_deg_width_H_alow": [[round(lb["th0"], 1), round(lb["th1"], 1), lb["H"], lb["a_low_mid"]]
                                      for lb in lobes if lb["ear"]],
            "slit_width_at_lip_design_mm_min_max": mm([sp["w"] for sp in sl]),
            "slit_length_design_mm_min_max": mm([sp["len"] for sp in sl]),
            "slit_tip_depth_design_mm_min_max": mm([sp["a_tip"] for sp in sl]),
            "hem_depth_below_root_design_mm_min_max": mm([c[2] for c in info_cols]),
            "lip_underside_to_wood_close_lobes_middle_design_mm_min_max": mm(close_gap),
            "lip_underside_to_wood_ears_middle_design_mm_min_max": mm(ear_gap),
            "bead_outer_radius_design_mm": 1000 * RO_HEAD[s], "fillet_radius_design_mm": 1000 * RF,
            "bead_taper_slit_near": [TAPER_SLIT, TAPER_NEAR], "rows": NB, "tris": 2 * len(faces),
            "verts": len(verts)}
    return verts, faces, fuv, info
