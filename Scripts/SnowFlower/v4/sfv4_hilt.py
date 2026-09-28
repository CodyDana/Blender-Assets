"""Snow Flower v4 hilt: guard (rebuilt), collar, grip core + cord wrap, grip ornament, pommel end cap.

Every part is generated from the same parameters at four levels: "high" (bake source, with the
revision-3 ornament construction where it was kept) and 0/1/2 (game LODs, parametric UVs).
Coordinates in mm, model frame (sfv4_spec).
"""
from __future__ import annotations

import math

import numpy as np

import sfv4_spec as S
from sfv4_mesh import MB, _norm, catmull, fan_cap, tube, grid, arclen
from sfv4_prims import lathe, leaf, plate, plate2, superellipse_ring, loft_rings
from sfv4_blade import flower_disc

STEEL, WRAP = 0, 1


def _res(level, high, l0, l1, l2):
    return {"high": high, 0: l0, 1: l1, 2: l2}[level]


# ====================================================================== guard layout
# LOOK-MATCH R1 (2026-09-27), traced on the sheet with a mm grid (lookmatch/sword_r1/ref/grid_guard_*.png):
#   front view: bat wings with a pointed HOOK at the upper outer corner (x 45.5, z 61), outermost at (60, 87), a lower
#   point at (43, 110); thick silver frames, dark fields with thorn lace; broad thick-rimmed cupped leaves in an X
#   (upper tips (35, 63.5), lower tips (39, 112.5)) and the pendant leaf to z 128.5; a large DOMED central blossom.
#   side view: the guard is V / bat shaped - each wing is TWO framed panels (front and back) splayed like a V in plan
#   (root |y| ~11 at x 15, |y| 30 at the outer end), their top rims forming the V (tips |y| 29 at z 60, apex hidden by
#   the hub at z ~77) and their lower points hanging as the "ears" (|y| 22 at z 108).

GZ = S.GUARD_BLOSSOM_Z
#: (name, base (x, z), tip (x, z), width, base depth, tip depth) for the FRONT set (y<0); the back set mirrors y.
LEAVES = [
    ("UL", (-6.0, GZ - 3.0), (-33.0, 64.5), 17.5, 13.0, 25.5),
    ("UR", (6.0, GZ - 3.0), (33.0, 64.5), 17.5, 13.0, 25.5),
    ("LL", (-6.0, GZ + 3.0), (-38.0, 112.5), 35.0, 14.0, 26.5),
    ("LR", (6.0, GZ + 3.0), (38.0, 112.5), 35.0, 14.0, 26.5),
]
PENDANT = ("PD", (0.0, 93.0), (0.0, S.Z_PENDANT_TIP), 26.0, 15.0, 10.5)

#: wing panel outline (+X wing, (x, z)), root hidden behind the leaves/hub
WING_OUTLINE = [(15.0, 71.0), (28.0, 69.0), (37.0, 67.0), (41.0, 65.5), (45.5, 60.8), (49.0, 65.0), (53.0, 70.5),
                (57.5, 78.5), (60.0, 87.0), (59.0, 94.0), (54.5, 101.0), (48.0, 106.0), (43.0, 110.0), (38.0, 104.5),
                (30.0, 100.5), (15.0, 99.0)]
WING_LOD2 = [0, 2, 4, 6, 8, 10, 12, 14, 15]
#: panel plane y = -(PY0 + PA * x + PB * z) for the front panel (+y mirrored for the back panel), x = |x|
PY0, PA, PB = -17.53, -0.388, 0.174
GUARD_BLOSSOM_Y = 21.0
V_BRIDGE_X = 46.0
V_BRIDGE = [(-25.2, 61.4), (0.0, 72.0), (25.2, 61.4), (25.6, 67.4), (0.0, 78.4), (-25.6, 67.4)]
GUARD_BLOSSOM_CURVE = 0.011
GUARD_BLOSSOM_LIFT = 3.0


def panel_y(x, z, side):
    """y of the wing panel (side -1 front, +1 back) at |x|, z."""
    return -side * (PY0 + PA * abs(x) + PB * z)


def _ccw(pts):
    P = np.asarray(pts, float)
    a = 0.5 * np.sum(P[:, 0] * np.roll(P[:, 1], -1) - np.roll(P[:, 0], -1) * P[:, 1])
    return P if a > 0 else P[::-1]


def _hm(level):
    """High-poly material slots per region (None for game levels: one steel slot)."""
    if level != "high":
        return None
    import sfv4_rev3 as R3
    return {"hub": R3.BLACKSTEEL, "boss": R3.RECESS,
            "wing": {"rim": R3.SILVER, "field": R3.BLACKSTEEL, "side": R3.SILVER, "back": R3.BLACKSTEEL},
            "leaf": {"rim": R3.SILVER, "field": R3.BLACKSTEEL, "rib": R3.BLACKSTEEL, "side": R3.SILVER, "back": R3.BLACKSTEEL}}


def wing_frame(sign, side):
    """plate() frame of the wing panel: (O, U, V, N) with local (u, v) = (|x|, z)."""
    O = np.array([0.0, -side * PY0, 0.0])
    U = np.array([float(sign), -side * PA, 0.0])
    V = np.array([0.0, -side * PB, 1.0])
    N = _norm(np.cross(U, V))
    if N[1] * side < 0:          # N points away from the hub (front panel: -y)
        N = -N
    return O, U, V, N


def guard_low(mb: MB, level, mat=STEEL):
    """Guard at game level 0/1/2 (and the base shapes of the high level)."""
    hm = _hm(level)
    na = _res(level, 20, 12, 7, 4)
    nf = _res(level, 8, 4, 3, 2)
    segs = _res(level, 48, 24, 16, 10)
    rings = []
    for z, a, b in ((57.0, 19.0, 16.5), (70.0, 19.5, 17.0), (98.0, 19.5, 17.0), (110.0, 15.0, 11.0)):
        rings.append(superellipse_ring(a, b, 3.2, segs, z))
    loft_rings(mb, rings, "guard_hub", hm["hub"] if hm else mat)
    # wings: a front and a back framed panel per side, splayed in plan (the side view's V)
    base = WING_OUTLINE if level != 2 else [WING_OUTLINE[k] for k in WING_LOD2]
    outl = _ccw(base)
    for sign in (-1, 1):
        for side in (-1, 1):
            tag = ("R" if sign > 0 else "L") + ("F" if side < 0 else "B")
            O, U, V, N = wing_frame(sign, side)
            plate(mb, outl, O, U, V, N, 3.1, 3.1, f"guard_wing{tag}", mat, rim=_res(level, 5.0, 5.0, 4.6, 3.4),
                  recess=_res(level, 1.5, 1.5, 1.2, 0.0), bevel=1.1, rim_rise=0.5, mats=hm["wing"] if hm else None)
    # V bridge across the top of each wing just inboard of the hooks (the sheet's side view: a thick silver chevron
    # joining the front and back hook tips; from the front it thickens the hook)
    for sign in (-1, 1):
        tag = "R" if sign > 0 else "L"
        vb = _ccw(V_BRIDGE)
        plate(mb, vb, (sign * V_BRIDGE_X, 0.0, 0.0), (0, 1, 0), (0, 0, 1), (sign, 0, 0), 2.6, 2.6, f"guard_vbr{tag}", mat,
              rim=_res(level, 1.9, 1.9, 1.8, 1.5), recess=_res(level, 0.6, 0.6, 0.5, 0.0), bevel=0.8, rim_rise=0.3,
              mats={k: hm["wing"]["rim"] for k in ("rim", "field", "side", "back")} if hm else None)
    # leaves
    for side in (-1, 1):
        tagS = "F" if side < 0 else "B"
        for name, b, t, w, d0, d1 in LEAVES + [PENDANT]:
            base_p = (b[0], side * d0, b[1])
            tip = (t[0], side * d1, t[1])
            nrm = (0.0, float(side), 0.0)
            if name == "PD":
                nrm = (0.0, float(side), -0.35)
            leaf(mb, base_p, tip, nrm, w, 5.6, f"guard_leaf{name}{tagS}", mat, na=na, nf=nf, rim=0.42, rim_rise=1.2,
                 recess=_res(level, 2.4, 2.4, 1.8, 0.4), widest=0.45 if name[0] == "L" else 0.42, rim_flat=True, rib=_res(level, 0.35, 0.35, 0.25, 0.0),
                 fold=_res(level, 1.2, 1.2, 1.0, 0.3),
                 cup=2.4 if name != "PD" else 1.2, curl=1.5 if name != "PD" else -1.5,
                 mats=hm["leaf"] if hm else None)
        # blossom boss + the domed cast blossom (real petals at every LOD)
        by = side * 16.0
        segs_b = _res(level, 32, 16, 10, 8)
        prof = [(0.0, 0.0), (9.5, 0.0), (9.5, 5.5), (7.0, 6.8), (0.0, 7.2)]
        ang = np.linspace(0, 2 * math.pi, segs_b, endpoint=False)
        rings = []
        for r, h in prof[1:4]:
            rings.append([(r * math.cos(a), by + side * h, GZ + r * math.sin(a)) for a in ang])
        loft_rings(mb, rings, f"guard_boss{tagS}", hm["boss"] if hm else mat, cap0=True, cap1=True)
        if level in (0, 1, 2):
            import sfv4_lm_flower as FL
            FL.blossom_low(mb, (0.0, side * GUARD_BLOSSOM_Y, GZ), S.GUARD_BLOSSOM_R, (0.0, side, 0.0),
                           math.pi / 2 * side, f"guard_bloss{tagS}", mat, level=level, up_hint=(0, 0, -1),
                           curve=GUARD_BLOSSOM_CURVE, lift=GUARD_BLOSSOM_LIFT)


def _panel_point(sign, side, x, z, h):
    O, U, V, N = wing_frame(sign, side)
    return O + U * x + V * z + N * h


def guard_high(mb: MB, sink):
    """High-poly guard: the low construction at high resolution + the cast blossom, the thorn lace in the wing panels,
    the filigree above and below the blossom."""
    import sfv4_rev3 as R3
    import sfv4_lm_flower as FL
    guard_low(mb, "high")
    SV = sink.mb(R3.SILVER)
    for side in (-1, 1):
        FL.blossom_high(sink, (0.0, side * GUARD_BLOSSOM_Y, GZ), S.GUARD_BLOSSOM_R, (0.0, side, 0.0), math.pi / 2 * side,
                        up_hint=(0, 0, -1), curve=GUARD_BLOSSOM_CURVE, lift=GUARD_BLOSSOM_LIFT)
        # thorn lace inside each wing panel (sheet: curling thorny scrolls in the dark fields)
        for sign in (-1, 1):
            h = 3.1 - 1.5 + 0.55
            for curve, rad in (([(22, 79), (31, 77.5), (40, 78), (48, 81), (53, 87), (50, 94)], 0.75),
                               ([(26, 92), (35, 90), (42, 92), (45, 97), (41, 101)], 0.65),
                               ([(53, 87), (51, 80.5), (47, 77.5), (43, 79.5), (44, 84)], 0.6),
                               ([(40, 78), (41, 73), (44, 70)], 0.5),
                               ([(45, 97), (49, 99), (50, 103)], 0.5)):
                pts = catmull([(x, z) for x, z in curve], 8)
                P = np.array([_panel_point(sign, side, x, z, h) for x, z in pts])
                tube(SV, P, lambda t, r=rad: r * (1 - 0.35 * t), sides=7, island="HIGH", mat=R3.SILVER)
                for jj in range(2, len(curve) - 1, 2):
                    x, z = curve[jj]
                    p = _panel_point(sign, side, x, z, h)
                    q = _panel_point(sign, side, x + 2.2, z - 3.0, h + 0.2)
                    tube(SV, np.array([p, 0.5 * (p + q), q]), lambda t: 0.55 * (1 - 0.85 * t), sides=6,
                         island="HIGH", mat=R3.SILVER)
        # filigree fleur below the blossom, on the pendant leaf (sheet: a silver lace arrowhead pointing down)
        fl = [[(0.0, 96.0), (0.0, 106.5)],
              [(0.0, 97.0), (3.2, 98.5), (5.6, 97.2), (6.2, 99.8), (4.0, 102.5), (0.0, 106.5)],
              [(0.0, 97.0), (-3.2, 98.5), (-5.6, 97.2), (-6.2, 99.8), (-4.0, 102.5), (0.0, 106.5)],
              [(2.0, 100.5), (3.6, 100.0), (3.0, 101.8)], [(-2.0, 100.5), (-3.6, 100.0), (-3.0, 101.8)]]
        for path in fl:
            pts = catmull(path, 6) if len(path) > 2 else np.array(path, float)
            P = np.array([(x, 0.0, z) for x, z in pts])
            # sit on the pendant leaf surface: its body runs from y 15 (z 93) to 10.5 (z 128.5), + its rim height
            P[:, 1] = side * (15.0 + (10.5 - 15.0) * (P[:, 2] - 93.0) / (S.Z_PENDANT_TIP - 93.0) + 3.3)
            tube(SV, P, lambda t: 0.6 * (1 - 0.3 * t), sides=7, island="HIGH", mat=R3.SILVER)
        # filigree above the blossom on the hub face, between the upper leaves (sheet: lace scrolls under the collar)
        for d in (-1, 1):
            path = catmull([(d * 2.0, 64.5), (d * 7.0, 63.5), (d * 11.5, 66.0), (d * 12.0, 70.0), (d * 8.5, 71.0),
                            (d * 7.8, 68.0)], 6)
            P = np.array([(x, side * 17.8, z) for x, z in path])
            tube(SV, P, lambda t: 0.55 * (1 - 0.3 * t), sides=7, island="HIGH", mat=R3.SILVER)


# ====================================================================== collar
# LOOK-MATCH R1: the sheet's collar (front/side/back crops at 8x, guard detail) is a TALL FACETED polished band
# (z ~48.5-62, ~47 mm across, flared toward the guard, lipped at both ends) with a pointed CHEVRON plate rising from its
# top onto the wrap on the front and back (~20 mm wide, ~13 mm tall, rimmed) and silver vine work crossing over the band
# top between them.

COLLAR_RINGS = [  # (z, half-width X, half-depth Y)
    (45.8, 20.9, 18.6), (47.4, 21.6, 19.4), (48.5, 22.5, 20.3), (50.0, 22.7, 20.5), (50.6, 22.3, 20.1),
    (51.4, 22.7, 20.5), (58.4, 23.5, 21.3), (59.2, 24.0, 21.8), (61.2, 24.0, 21.8), (62.2, 23.2, 21.0)]
CHEVRON = [(-10.0, 49.6), (-9.2, 45.0), (0.0, 36.0), (9.2, 45.0), (10.0, 49.6)]   # (arc mm from the face centre, z)


def facet_ring(a, b, z, per_side, sides=8, chamfer=0.18):
    """Faceted ring: an octagon (a facet facing each axis) inscribed in the ellipse, corners slightly chamfered."""
    out = []
    ang = [2 * math.pi * (k + 0.5) / sides for k in range(sides)]
    corners = [np.array([a * math.cos(t) / math.cos(math.pi / sides), b * math.sin(t) / math.cos(math.pi / sides)]) for t in ang]
    for k in range(sides):
        p0, p1 = corners[k - 1], corners[k]
        for j in range(per_side):
            t = j / per_side
            q = p0 + (p1 - p0) * t
            # pull the corner neighbourhood inward a little (chamfer)
            d = min(t, 1 - t)
            if d < chamfer:
                q = q * (1 - 0.018 * (1 - d / chamfer))
            out.append((q[0], q[1], z))
    # rotate so the list starts at angle ~ -pi/4 like the other lofts (seam at the back-right corner)
    return out


def collar(mb: MB, level, mat=STEEL):
    per = _res(level, 12, 4, 3, 2)
    rings = COLLAR_RINGS
    if level == 2:
        rings = [rings[k] for k in (0, 2, 5, 7, 9)]
    elif level == 1:
        rings = [rings[k] for k in (0, 1, 2, 3, 5, 6, 7, 8, 9)]
    R = [facet_ring(a, b, z, per) for z, a, b in rings]
    hm = None
    if level == "high":
        import sfv4_rev3 as R3
        mat = R3.SILVER
    loft_rings(mb, R, "collar", mat, cap0=False, cap1=True)
    # chevron plates front (-Y) and back (+Y), laid on the wrap
    for side in (-1, 1):
        tag = "F" if side < 0 else "B"

        def mapper(p2, h, side=side):
            s_mm, z = p2
            a, b = grip_ab(z)
            th0 = -math.pi / 2 if side < 0 else math.pi / 2
            per_r = 0.5 * (a + b)
            theta = th0 - side * s_mm / per_r
            p, n = grip_surface(theta, z, S.WRAP_THICK + 0.1 + h)
            return p
        hm2 = None
        if level == "high":
            import sfv4_rev3 as R3
            hm2 = {"rim": R3.SILVER, "field": R3.SILVER, "side": R3.SILVER, "back": R3.SILVER}
        plate(mb, np.array(CHEVRON), (0, 0, 0), (1, 0, 0), (0, 0, 1), (0, 0, 1), 2.6, 0.9, f"collar_chev{tag}", mat,
              rim=1.8, recess=_res(level, 0.7, 0.7, 0.5, 0.0), bevel=0.5, mats=hm2, mapper=mapper)
    # vine work over the band top (LOD0 as round tubes, LOD1 as 4-sided strips, none at LOD2)
    if level in (0, 1):
        for k, path in enumerate(_collar_vines(level)):
            tube(mb, path, lambda t: 0.75 * (1 - 0.35 * t), sides=6 if level == 0 else 4,
                 island=f"collar_vine{k}", mat=mat, cap=("flat", "flat"))


def _collar_vines(level):
    """Crossing S-vines around the band top between the two chevrons (both sides), 1.6 mm above the wrap."""
    paths = []
    n = 26 if level == "high" else (10 if level == 0 else 6)
    for side in (-1, 1):
        th_c = -math.pi / 2 if side < 0 else math.pi / 2
        for d in (-1, 1):
            pts = []
            for t in np.linspace(0, 1, n):
                theta = th_c + d * (0.42 + 1.18 * t)
                z = 47.2 - 6.5 * math.sin(math.pi * t) ** 1.2 * (1 if d > 0 else 0.8) + 0.9 * math.sin(3 * math.pi * t)
                a, b = grip_ab(z)
                pts.append(grip_surface(theta, z, S.WRAP_THICK + 0.8)[0])
            paths.append(np.array(pts))
    return paths


def collar_high(mb: MB, sink):
    import sfv4_rev3 as R3
    collar(mb, "high")
    SV = sink.mb(R3.SILVER)
    for path in _collar_vines("high"):
        tube(SV, path, lambda t: 0.75 * (1 - 0.35 * t) * (1 + 0.08 * math.sin(t * 23)), sides=8, island="HIGH",
             mat=R3.SILVER)
        # thorns along the vine
        for k in (5, 12, 19):
            p = path[k]
            q = path[k + 1] + (path[k + 1] - path[k]) * 0.5
            n = _norm(p * np.array([1, 1, 0]))
            tip = p + _norm(q - p) * 2.2 + n * 0.5 + np.array([0, 0, -1.2 if k % 2 else 1.2])
            tube(SV, np.array([p, 0.5 * (p + tip), tip]), lambda t: 0.55 * (1 - 0.85 * t), sides=5, island="HIGH",
                 mat=R3.SILVER)
    # a vine climbing each chevron: stem up the centre line with two leaf curls (sheet: vine work on the plates)
    for side in (-1, 1):
        th0 = -math.pi / 2 if side < 0 else math.pi / 2
        def on(s_mm, z, h):
            a, b = grip_ab(z)
            return grip_surface(th0 - side * s_mm / (0.5 * (a + b)), z, S.WRAP_THICK + 0.1 + h)[0]
        stem = np.array([on(0.9 * math.sin(t * 5), 48.6 - 10.5 * t, 2.9) for t in np.linspace(0, 1, 16)])
        tube(SV, stem, lambda t: 0.55 * (1 - 0.5 * t), sides=6, island="HIGH", mat=R3.SILVER)
        for d in (-1, 1):
            curl = np.array([on(d * (1.0 + 4.0 * math.sin(t * 2.4)), 46.0 - 3.0 * t - 1.2 * math.sin(t * 3.3), 2.9)
                             for t in np.linspace(0, 1, 12)])
            tube(SV, curl, lambda t: 0.42 * (1 - 0.6 * t), sides=6, island="HIGH", mat=R3.SILVER)


# ====================================================================== grip

def grip_ab(z):
    t = np.clip((z - S.Z_GRIP_BOT) / (S.Z_GRIP_TOP - S.Z_GRIP_BOT), 0, 1)
    a = S.GRIP_A[0] + (S.GRIP_A[1] - S.GRIP_A[0]) * t
    b = S.GRIP_B[0] + (S.GRIP_B[1] - S.GRIP_B[0]) * t
    return float(a), float(b)


def grip_surface(theta, z, offset):
    a, b = grip_ab(z)
    c, s = math.cos(theta), math.sin(theta)
    p = np.array([a * c, b * s, z])
    n = _norm([c / a, s / b, 0.0])
    return p + n * offset, n


#: LOOK-MATCH R1: the sheet's wrap is a RAISED DIAMOND CROSS-WRAP: flat ~10 mm braided cord bands crossing in X's
#: on EVERY view (front, side and back all show the diagonal lattice) with ~11 crossings down the front and small
#: diamond windows between them.  Built as a woven lattice: WRAP_BANDS bands wound each way on a 29 deg helix
#: (pitch WRAP_PITCH), crossing at six angles around the grip (front, back, +-60, +-120 deg); each band goes over and
#: under alternately (a weave), so every crossing shows one band on top.
WRAP_BAND_W = 9.8
WRAP_BANDS = 3
WRAP_PITCH = 64.0            # mm per turn of one band: front crossings every WRAP_PITCH / WRAP_BANDS = 21.3 mm
WRAP_Z = (S.Z_GRIP_BOT + 1.0, S.Z_GRIP_TOP - 0.5)


def _band_profile(u):
    """Cord cross-profile, u in -1..1 across the band: flat braided top, rounded edges (0..1)."""
    return max(0.0, 1 - abs(u) ** 10) ** 0.35


def _band_theta0(i):
    return -math.pi / 2 + 2 * math.pi * i / WRAP_BANDS


def _wrap_lift(theta, direction):
    """Weave: +1 bands over the -1 bands at alternate crossings (crossings every 60 deg of theta)."""
    return 0.32 + direction * 0.32 * math.cos(WRAP_BANDS * (theta + math.pi / 2))


def _band_theta_range(i, direction):
    """Unwrapped theta range of band i so that its z covers the grip."""
    z0, z1 = WRAP_Z
    span = 2 * math.pi * (z1 - z0) / WRAP_PITCH
    return _band_theta0(i), span


def _band_z(t_rel, direction):
    z0, _ = WRAP_Z
    # t_rel = theta travelled from the band start (>= 0); both directions climb +z
    return z0 + WRAP_PITCH * t_rel / (2 * math.pi)


def wrap_height(theta, z):
    """Cord top height above the core at (theta, z) (0 in the diamond windows) - the low grip follows it."""
    z0, z1 = WRAP_Z
    best = 0.0
    a, b = grip_ab(z)
    for direction in (-1, 1):
        for i in range(WRAP_BANDS):
            th0 = _band_theta0(i)
            # theta = th0 + direction * t_rel ;  z = z0 + P t_rel / 2pi
            t_base = direction * (theta - th0)
            for k in range(-1, int((z1 - z0) / WRAP_PITCH) + 3):
                t_rel = t_base + 2 * math.pi * k
                if t_rel < -2 * math.pi / WRAP_BANDS - 0.3:
                    continue
                zc = _band_z(t_rel, direction)
                if zc > z1 + 2 * WRAP_PITCH / WRAP_BANDS + 6 or abs(z - zc) > 14.0:
                    continue
                arc = math.hypot(a * math.sin(theta), b * math.cos(theta))
                dz = WRAP_PITCH / (2 * math.pi)
                d = abs(z - zc) * arc / math.hypot(arc, dz)
                u = d / (0.5 * WRAP_BAND_W)
                if u < 1.0:
                    h = _wrap_lift(theta, direction) + 0.05 + _band_profile(u) * (S.WRAP_THICK - 0.25)
                    best = max(best, h)
    return best


def grip_core(mb: MB, level, offset, mat=WRAP, prefix="wrap"):
    """Oval loft of the grip. High: the plain core under the cords.  Game levels: the core displaced by the cord height
    field (LOD0 fully, LOD1 half, LOD2 not) so the cross-wrap ridges and diamond windows are real geometry.
    Islands: 4 around x 2 along = 8 near-square islands (U tile 1..2)."""
    segs = _res(level, 128, 48, 24, 12)
    nz = _res(level, 120, 96, 30, 6)
    zs = np.linspace(S.Z_GRIP_BOT - 1.0, S.Z_GRIP_TOP + 1.0, nz)
    ang = np.linspace(0, 2 * math.pi, segs, endpoint=False) - math.pi / 4
    if level == "high":
        rings = np.array([[grip_surface(a, z, offset)[0] for a in ang] for z in zs])
        grid(mb, rings, True, "HIGH", mat)
        return
    amp = {0: 0.85, 1: 0.45, 2: 0.0}[level]
    base = 0.35 if level != 2 else offset
    rings = np.array([[grip_surface(a, z, base + amp * wrap_height(a, z))[0] for a in ang] for z in zs])
    # UV: u = arclength of the UNdisplaced ring (a stable parametrisation), v = z; islands by quadrant and half-length
    flat = np.array([[grip_surface(a, z, offset)[0] for a in ang] for z in zs])
    per = np.array([arclen(r, closed=True)[-1] for r in flat])
    uv = np.zeros((nz, segs + 1, 2))
    for i in range(nz):
        s = arclen(flat[i], closed=True)
        uv[i, :, 0] = s / per[i] * per.mean()
        uv[i, :, 1] = zs[i]
    zmid = 0.5 * (zs[0] + zs[-1])
    quarter = segs // 4
    idx = np.array(mb.vs(rings.reshape(-1, 3))).reshape(nz, segs)
    for r in range(nz - 1):
        half = 0 if 0.5 * (zs[r] + zs[r + 1]) < zmid else 1
        for c in range(segs):
            c2 = (c + 1) % segs
            q = min(c // quarter, 3)
            isl = f"{prefix}_q{q}h{half}"
            u = [uv[r, c], uv[r, c + 1], uv[r + 1, c + 1], uv[r + 1, c]]
            mb.f([idx[r, c], idx[r, c2], idx[r + 1, c2], idx[r + 1, c]], [tuple(x) for x in u], isl, mat)


def wrap_high(mb_cord: MB, mb_core: MB):
    """Near-black woven diamond cross-wrap (see WRAP_BANDS / WRAP_PITCH), each band a closed flat braided strip."""
    import sfv4_rev3 as R3
    grip_core(mb_core, "high", 0.0, mat=R3.CORE)
    z0, z1 = WRAP_Z
    nprof = 15
    us = np.linspace(-1, 1, nprof)
    for direction in (-1, 1):
        for i in range(WRAP_BANDS):
            th0 = _band_theta0(i)
            # start a little below the grip bottom so every band covers the whole length; clip at the ends
            t0 = -2 * math.pi / WRAP_BANDS
            t_end = 2 * math.pi * (z1 - z0) / WRAP_PITCH + 2 * math.pi / WRAP_BANDS
            steps = int((t_end - t0) / (2 * math.pi) * 110) + 2
            rows = []
            for kk in range(steps + 1):
                t_rel = t0 + (t_end - t0) * kk / steps
                theta = th0 + direction * t_rel
                z = _band_z(t_rel, direction)
                lift = _wrap_lift(theta, direction)
                a, b = grip_ab(z)
                arc = math.hypot(a * math.sin(theta), b * math.cos(theta))
                dz = WRAP_PITCH / (2 * math.pi)
                den = math.hypot(arc, dz)
                ps, pz = -dz / den, direction * arc / den
                ring, back = [], []
                for u in us:
                    w = 0.5 * WRAP_BAND_W * u
                    th2 = theta + direction * (w * ps) / arc
                    zz = float(np.clip(z + w * pz, S.Z_GRIP_BOT + 0.3, S.Z_GRIP_TOP + 0.5))
                    ring.append(grip_surface(th2, zz, lift + 0.05 + _band_profile(u) * (S.WRAP_THICK - 0.25))[0])
                for u in us[::-1]:
                    w = 0.5 * WRAP_BAND_W * u
                    th2 = theta + direction * (w * ps) / arc
                    zz = float(np.clip(z + w * pz, S.Z_GRIP_BOT + 0.3, S.Z_GRIP_TOP + 0.5))
                    back.append(grip_surface(th2, zz, lift - 0.05)[0])
                rows.append(ring + back)
            rows = np.array(rows)
            idx = grid(mb_cord, rows, True, "HIGH", R3.CORD)
            fan_cap(mb_cord, list(idx[0]), rows[0].mean(axis=0), "HIGH", R3.CORD, flip=True)
            fan_cap(mb_cord, list(idx[-1]), rows[-1].mean(axis=0), "HIGH", R3.CORD)


# ---------------------------------------------------------------------- grip ornament
# LOOK-MATCH R1: traced on the sheet's front view with a mm grid (lookmatch/sword_r1/ref/grid_grip_both.png).  Each
# face carries two COMPACT clusters of 4-5 crowded cast blossoms (r ~5-6 mm) on a thick knobbly silver branch that
# runs diagonally across the face (upper: from the -X edge at z -126 down to the +X edge; lower: from the +X edge at
# z -16 down toward the collar).  Coordinates: (x projected on the front face, z) mm; the back face mirrors x.

GRIP_CLUSTERS = [
    {"branch": [(-12.5, -127.0), (-7.0, -112.0), (-1.0, -104.0), (4.0, -97.0), (9.0, -88.0), (13.0, -78.0),
                (15.0, -67.0), (14.5, -58.0)],
     "twigs": [[(0.5, -103.0), (-4.0, -96.5), (-8.0, -91.5)], [(12.0, -80.0), (7.0, -73.0), (4.5, -70.0)]],
     "blossoms": [(5.0, -99.0, 7.3), (11.0, -91.0, 7.1), (7.5, -82.5, 6.9), (12.5, -74.5, 6.0), (-7.5, -90.0, 5.3)],
     "buds": [(-9.5, -95.0), (4.0, -68.5), (-5.5, -110.0)]},
    {"branch": [(18.5, -24.0), (15.0, -11.0), (11.5, -1.0), (9.0, 8.0), (8.0, 18.0), (7.5, 28.0), (6.0, 38.0)],
     "twigs": [[(10.5, 1.0), (5.5, 5.0), (2.0, 8.5)], [(8.2, 22.0), (12.5, 26.0), (15.0, 31.0)]],
     "blossoms": [(11.5, 2.0, 7.0), (3.5, 7.0, 7.0), (12.5, 12.5, 6.7), (4.5, 16.5, 6.2), (11.5, 21.5, 5.0)],
     "buds": [(1.0, 10.5), (15.5, 32.0), (17.0, -18.0)]},
]
GRIP_BRANCH_R = 1.85
ORN_OFFSET = S.WRAP_THICK + 0.45


def _gpx(x, z, side, off):
    """Grip surface point for a front-projected x (back face: x mirrored)."""
    xx = x if side < 0 else -x
    a, b = grip_ab(z)
    theta = math.acos(float(np.clip(xx / a, -0.97, 0.97)))
    if side < 0:
        theta = -theta
    return grip_surface(theta, z, off)


def _on_grip(path3, off):
    out = []
    for p in path3:
        a, b = grip_ab(p[2])
        th = math.atan2(p[1] / b, p[0] / a)
        out.append(grip_surface(th, p[2], off)[0])
    return np.array(out)


def grip_ornament(level, side, mb=None, sink=None, mat=STEEL):
    import sfv4_rev3 as R3
    import sfv4_lm_flower as FL
    tag = "F" if side < 0 else "B"
    for ci, cl in enumerate(GRIP_CLUSTERS):
        paths = [("stem", cl["branch"], GRIP_BRANCH_R)] + [(f"tw{k}", tw, 1.15) for k, tw in enumerate(cl["twigs"])]
        for pname, knots, rad in paths:
            pts3 = [_gpx(x, z, side, ORN_OFFSET)[0] for x, z in knots]
            path = _on_grip(catmull(pts3, 10 if level == "high" else 3), ORN_OFFSET + 0.2)
            if level == "high":
                tube(sink.mb(R3.SILVER), path,
                     lambda t, r=rad: r * (1 - .38 * t) * (1 + .12 * math.sin(t * 29 + .3) + .06 * math.sin(t * 71)),
                     sides=9, island="HIGH", mat=R3.SILVER)
            elif level == 0:
                tube(mb, path, lambda t, r=rad: r * (1 - .38 * t), sides=6,
                     island=f"gorn_{tag}{ci}_{pname}", mat=mat, cap=("flat", "flat"))
            elif level == 1 and pname == "stem":
                # LOD1 keeps the main branch (4-sided), so its blossoms never float on the cord
                tube(mb, path[::2] if len(path) > 6 else path, lambda t, r=rad: r * (1 - .38 * t), sides=4,
                     island=f"gorn_{tag}{ci}_{pname}", mat=mat, cap=("flat", "flat"))
        for k, (x, z, r) in enumerate(cl["blossoms"]):
            p, n = _gpx(x, z, side, ORN_OFFSET + 0.9)
            ph = 0.24 + k * 0.71 + ci * 0.35
            if level == "high":
                FL.blossom_high(sink, p, r, n, ph, up_hint=(0, 0, 1), curve=0.004, lift=0.4)
            elif level in (0, 1):
                FL.blossom_low(mb, p, r, n, ph, f"gorn_{tag}{ci}_bl{k}", mat, level=level + 1, up_hint=(0, 0, 1),
                               curve=0.004, lift=0.4)
        if level == "high":
            for (x, z) in cl["buds"]:
                p, n = _gpx(x, z, side, ORN_OFFSET + 0.6)
                tng = _norm(np.cross(n, [0, 0, 1]))
                R3.ellipsoid(sink, p, tng * 1.5, np.array([0, 0, 2.1]), n * 1.1, R3.INLAY, 12, 6)


# ====================================================================== pommel (end cap)
# LOOK-MATCH R1 (2026-09-27): the sheet's pommel is a DOMED cap (front/side silhouette: ~15 mm of dome over a ~46 mm
# cap) with a STEPPED rim (thick rounded bezel, groove, thin raised ring) around a domed dark field whose cast blossom
# fills ~85 % of it, engraved scrolls in the gaps, and a thick PIERCED scroll band on the side.  Profile (r, depth d
# from the top); the field is the dome d = 2.0 + FIELD_K r^2.

ZP = S.Z_POMMEL_TOP
FIELD_K = 0.025
FIELD_R = 16.0
POMMEL_BLOSSOM_R = 13.6
_PD = [(0.0, 2.6), (5.0, 3.23), (10.0, 5.1), (14.0, 7.5), (16.0, 9.0), (16.3, 9.5), (16.6, 8.8), (17.6, 9.5),
       (17.9, 10.6), (18.4, 11.0), (18.7, 10.2), (20.0, 11.4), (21.3, 12.9), (22.4, 14.8), (23.1, 16.6), (23.4, 18.0),
       (23.1, 18.6), (22.2, 18.9), (22.2, 25.3), (23.0, 25.6), (23.5, 26.3), (23.4, 27.1), (22.6, 27.5), (19.5, 27.7),
       (19.5, 32.4), (18.7, 33.0), (15.0, 33.0), (0.0, 33.0)]
POMMEL_PROFILE = [(r, ZP + d) for r, d in _PD]
POMMEL_BANDS_L0 = [(0, 4, "planar"), (4, 13, "planar"), (13, 17, "cyl"), (17, 18, "cyl"), (18, 23, "cyl"),
                   (23, 25, "cyl"), (25, 27, "planar")]
BAND_Z = (ZP + 18.9, ZP + 25.3)
BAND_R = 22.2


def field_z(r):
    return ZP + 2.6 + FIELD_K * r * r


def pommel(mb: MB, level, mat=STEEL):
    segs = _res(level, 160, 40, 24, 14)
    prof = list(POMMEL_PROFILE)
    bands = POMMEL_BANDS_L0
    band_mats = None
    if level == 2:
        keep = [0, 2, 4, 7, 11, 13, 15, 17, 18, 20, 22, 23, 24, 26, 27]
        prof = [POMMEL_PROFILE[k] for k in keep]
        bands = [(0, 2, "planar"), (2, 5, "planar"), (5, 7, "cyl"), (7, 8, "cyl"), (8, 11, "cyl"), (11, 12, "cyl"),
                 (12, 14, "planar")]
    elif level == 1:
        keep = [0, 1, 2, 3, 4, 6, 7, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27]
        prof = [POMMEL_PROFILE[k] for k in keep]
        bands = [(0, 4, "planar"), (4, 10, "planar"), (10, 14, "cyl"), (14, 15, "cyl"), (15, 20, "cyl"),
                 (20, 22, "cyl"), (22, 24, "planar")]
    elif level == "high":
        import sfv4_rev3 as R3
        bands = [(0, 5, "planar"), (5, 8, "planar"), (8, 10, "planar"), (10, 17, "cyl"), (17, 18, "cyl"),
                 (18, 27, "cyl")]
        band_mats = [R3.RECESS, R3.SILVER, R3.RECESS, R3.SILVER, R3.RECESS, R3.SILVER]
    lathe(mb, prof, segs, bands, mat, prefix="pommel" if level != "high" else "HIGHP", band_mats=band_mats)
    if level in (0, 1, 2):
        import sfv4_lm_flower as FL
        FL.blossom_low(mb, (0.0, 0.0, ZP + 2.6), POMMEL_BLOSSOM_R, (0, 0, -1), -math.pi / 2, "pommel_bloss", mat,
                       level=level, up_hint=(1, 0, 0), curve=FIELD_K)


def _scroll_band_paths(motifs=10):
    """Pierced scroll band (sheet pommel crop): a row of pointed-oval (lancet) openings framed by thick S-scrolls with a
    thorn at every crossing.  Returns (angle, z) polylines on the band cylinder."""
    z0, z1 = BAND_Z
    zc, hz = 0.5 * (z0 + z1), 0.5 * (z1 - z0) - 1.0
    out = []
    for k in range(motifs):
        a0 = 2 * math.pi * k / motifs
        w = 2 * math.pi / motifs
        # two S-scrolls crossing: upper and lower arcs of the lancet
        for sgn in (-1, 1):
            pts = []
            for t in np.linspace(0, 1, 18):
                a = a0 + w * t
                z = zc + sgn * hz * math.sin(math.pi * t) ** 0.9
                pts.append((a, z))
            out.append(("rib", pts))
        # a short thorn sprouting into each lancet opening (no inner curl: it read as an "eye")
        out.append(("thorn", [(a0 + 0.5 * w, zc + hz * 0.95), (a0 + 0.5 * w + 0.05 * w, zc + hz * 0.35)]))
        # thorn at the crossing
        out.append(("thorn", [(a0, zc), (a0 + 0.08 * w, zc - 1.6), (a0 + 0.02 * w, zc - 2.6)]))
    return out


def pommel_high(mb: MB, sink):
    """Domed end cap at high resolution: stepped rim, dark dome field with the CAST blossom (fills ~85 % of the field),
    engraved scroll vines in the gaps, and the thick pierced scroll band on the side (tassel removed: no lug)."""
    import sfv4_rev3 as R3
    import sfv4_lm_flower as FL
    pommel(mb, "high")
    FL.blossom_high(sink, (0.0, 0.0, ZP + 2.6), POMMEL_BLOSSOM_R, (0, 0, -1), -math.pi / 2, up_hint=(1, 0, 0),
                    curve=FIELD_K)

    def fp(r, a, lift=0.0):
        return np.array([r * math.cos(a), r * math.sin(a), field_z(r) - lift])

    # engraved scroll vines on the field (sheet: flowing silver vine lines that curl around the petal tips and into
    # the gaps, with small thorns): per gap one tangential S-vine just inside the ring with an inward curl at each end,
    # and one curl reaching in toward the centre between the petals
    def curl(r0, a0, d, size, turns=1.4, n=14):
        out = []
        for t in np.linspace(0, turns * math.pi, n):
            rr = size * (1 - t / (turns * math.pi * 1.25))
            out.append((r0 - rr * math.sin(t), a0 + d * rr * (1 - math.cos(t)) / max(r0, 1.0)))
        return out

    SV = sink.mb(R3.SILVER)
    for k in range(5):
        amid = -math.pi / 2 + 2 * math.pi * (k + 0.5) / 5
        # tangential vine across the gap, bowing inward between the petal tips
        path = [(14.6 - 1.4 * math.sin(math.pi * t), amid - 0.62 + 1.24 * t + 0.05 * math.sin(2 * math.pi * t))
                for t in np.linspace(0, 1, 26)]
        tube(SV, np.array([fp(r, a, 0.30) for r, a in path]), lambda x: 0.40 * (1 - 0.25 * abs(2 * x - 1)), sides=6,
             island="HIGH", mat=R3.SILVER)
        for d, (r0, a0) in ((-1, path[0]), (1, path[-1])):
            c = curl(r0, a0, -d, 1.5)
            tube(SV, np.array([fp(r, a, 0.30) for r, a in c]), lambda x: 0.34 * (1 - 0.5 * x), sides=5, island="HIGH",
                 mat=R3.SILVER)
        # inward tendril in the gap, ending in a curl
        path = [(13.3 - 5.2 * t, amid + 0.16 * math.sin(math.pi * 1.5 * t)) for t in np.linspace(0, 1, 16)]
        path += curl(path[-1][0], path[-1][1], 1, 1.2)[1:]
        tube(SV, np.array([fp(r, a, 0.30) for r, a in path]), lambda x: 0.36 * (1 - 0.55 * x), sides=6, island="HIGH",
             mat=R3.SILVER)
        # thorns / leaf spikes along the vines
        for (r, a, dr, da) in ((13.4, amid - 0.30, -1.2, -0.10), (13.4, amid + 0.30, -1.2, 0.10), (10.6, amid + 0.07, -0.4, 0.16),
                               (11.8, amid - 0.02, 0.2, -0.17)):
            p = fp(r, a, 0.30)
            q = fp(r + dr, a + da, 0.12)
            tube(SV, np.array([p, 0.5 * (p + q), q]), lambda x: 0.26 * (1 - 0.85 * x), sides=5, island="HIGH",
                 mat=R3.SILVER)
    # pierced scroll band: thick raised silver scrolls on the dark band, flattened against the cylinder
    rr = BAND_R + 0.55
    for kind, path in _scroll_band_paths():
        P = np.array([(rr * math.cos(a), rr * math.sin(a), z) for a, z in path])
        up = np.array([(math.cos(a), math.sin(a), 0.0) for a, _ in path])
        rad = {"rib": lambda x: 0.95, "curl": lambda x: 0.62 * (1 - 0.4 * x), "thorn": lambda x: 0.7 * (1 - 0.8 * x)}[kind]
        tube(sink.mb(R3.SILVER), P, rad, sides=8, island="HIGH", mat=R3.SILVER, squash=0.7, up=up)
