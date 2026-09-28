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

GZ = S.GUARD_BLOSSOM_Z
#: (name, base (x, z), tip (x, z), width, base depth, tip depth) for the FRONT set (y<0); the back
#: set mirrors y. Sheet guard detail: two upper and two lower pointed almond leaves radiating in an
#: X around the blossom, a pendant leaf down over the blade base; wing arms end in angular hooks.
LEAVES = [   # sheet guard detail: broad almond leaves (width ~0.7 of length) with thick bevelled rims
    ("UL", (-6.0, GZ - 3.0), (-38.0, 62.0), 28.0, 13.0, 27.0),
    ("UR", (6.0, GZ - 3.0), (38.0, 62.0), 28.0, 13.0, 27.0),
    ("LL", (-6.0, GZ + 3.0), (-45.0, 105.0), 30.0, 13.0, 28.0),
    ("LR", (6.0, GZ + 3.0), (45.0, 105.0), 30.0, 13.0, 28.0),
]
PENDANT = ("PD", (0.0, 93.0), (0.0, S.Z_PENDANT_TIP), 26.0, 15.0, 10.5)

#: wing outline (+X side, XZ, CCW seen from the front -Y ... listed root-top -> hook -> end -> root-bottom)
WING_OUTLINE = [(14.0, 70.0), (30.0, 70.0), (41.0, 67.5), (50.0, 62.8), (57.5, 60.2), (59.0, 66.0),
                (58.2, 76.0), (58.0, 90.0), (55.0, 97.5), (47.0, 101.0), (32.0, 99.5), (14.0, 99.0)]
WING_LOD2 = [0, 2, 4, 5, 7, 9, 11]


def _wing_points(sign):
    pts = [(sign * x, z) for x, z in WING_OUTLINE]
    return pts if sign > 0 else pts[::-1]


def _hm(level):
    """High-poly material slots per region (None for game levels: one steel slot)."""
    if level != "high":
        return None
    import sfv4_rev3 as R3
    return {"hub": R3.BLACKSTEEL, "boss": R3.RECESS,
            "wing": {"rim": R3.SILVER, "field": R3.BLACKSTEEL, "side": R3.SILVER, "back": R3.BLACKSTEEL},
            "crown": {"rim": R3.SILVER, "field": R3.INLAY, "side": R3.SILVER, "back": R3.SILVER},
            "leaf": {"rim": R3.SILVER, "field": R3.BLACKSTEEL, "rib": R3.INLAY, "side": R3.SILVER, "back": R3.BLACKSTEEL}}


def guard_low(mb: MB, level, mat=STEEL):
    """Guard at game level 0/1/2 (and the base shapes of the high level)."""
    hm = _hm(level)
    na = _res(level, 20, 12, 7, 4)
    nf = _res(level, 8, 4, 3, 2)
    # hub: superellipse loft (hidden core the leaves and wings attach to)
    segs = _res(level, 48, 24, 16, 10)
    rings = []
    for z, a, b in ((57.0, 19.0, 16.5), (70.0, 19.5, 17.0), (98.0, 19.5, 17.0), (110.0, 15.0, 11.0)):
        rings.append(superellipse_ring(a, b, 3.2, segs, z))
    loft_rings(mb, rings, "guard_hub", hm["hub"] if hm else mat)
    # wings (both sides): one closed two-sided plate each in the XZ plane (front face toward -Y)
    for sign in (-1, 1):
        base = WING_OUTLINE if level != 2 else [WING_OUTLINE[k] for k in WING_LOD2]
        pts = np.array([(sign * x, z) for x, z in base])
        if sign < 0:
            pts = pts[::-1]
        tag = "R" if sign > 0 else "L"
        th = lambda p: 4.5 + 3.0 * max(0.0, (abs(p[0]) - 14.0) / 44.0)
        plate2(mb, pts, (0, 0, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0), th, f"guard_wing{tag}", mat,
               rim=4.2, recess=_res(level, 1.3, 1.3, 1.0, 0.0), bevel=1.1, rim_rise=0.4,
               mats=hm["wing"] if hm else None, face_detail=(level != 2))
    # crown chevrons on the four faces under the collar (sheet front AND side views show the V)
    for side, U, N, hw, t0, tb in (("F", (1, 0, 0), (0, -1, 0), 21.0, 20.5, -16.0), ("B", (-1, 0, 0), (0, 1, 0), 21.0, 20.5, -16.0),
                                   ("R", (0, 1, 0), (1, 0, 0), 17.5, 23.0, -18.5), ("L", (0, -1, 0), (-1, 0, 0), 17.5, 23.0, -18.5)):
        # CCW in the plate's (u, z) frame
        crown = [(hw, 58.0), (hw, 62.5), (5.0, 76.5), (0.0, 79.0), (-5.0, 76.5), (-hw, 62.5), (-hw, 58.0)]
        outl = np.array(crown)
        plate(mb, outl, (0, 0, 0), U, (0, 0, 1), N, lambda p, t0=t0: t0 + 0.12 * (p[1] - 58.0), tb,
              f"guard_crown{side}", mat, rim=2.2, recess=_res(level, 0.8, 0.8, 0.6, 0.0), bevel=0.7,
              mats=hm["crown"] if hm else None)
    # leaves
    for side in (-1, 1):
        tagS = "F" if side < 0 else "B"
        for name, b, t, w, d0, d1 in LEAVES + [PENDANT]:
            base = (b[0], side * d0, b[1])
            tip = (t[0], side * d1, t[1])
            nrm = (0.0, float(side), 0.0)
            if name == "PD":
                nrm = (0.0, float(side), -0.35)
            leaf(mb, base, tip, nrm, w, 3.6, f"guard_leaf{name}{tagS}", mat, na=na, nf=nf, rim=0.27, rim_rise=0.6,
                 recess=_res(level, 1.6, 1.6, 1.2, 0.3), rib=_res(level, 0.3, 0.3, 0.2, 0.0),
                 fold=_res(level, 1.3, 1.3, 1.0, 0.3),
                 cup=2.2 if name != "PD" else 1.2, curl=1.5 if name != "PD" else -1.5,
                 mats=hm["leaf"] if hm else None)
        # blossom boss + blossom proxy
        by = side * 16.0
        segs_b = _res(level, 32, 16, 10, 8)
        prof = [(0.0, 0.0), (9.5, 0.0), (9.5, 5.5), (7.0, 6.8), (0.0, 7.2)]
        # boss along Y: build around Z then rotate: do it directly with rings in the XZ plane
        ang = np.linspace(0, 2 * math.pi, segs_b, endpoint=False)
        rings = []
        for r, h in prof[1:4]:
            rings.append([(r * math.cos(a), by + side * h, GZ + r * math.sin(a)) for a in ang])
        loft_rings(mb, rings, f"guard_boss{tagS}", hm["boss"] if hm else mat, cap0=True, cap1=True)
        if level in (0, 1):
            flower_disc(mb, (0.0, side * 22.8, GZ), S.GUARD_BLOSSOM_R, (0.0, side, 0.0), math.pi / 2 * side,
                        f"guard_bloss{tagS}", mat, n_out=_res(level, 60, 40, 25, 15), up_hint=(0, 0, -1),
                        height=0.22, sink=1.2)


def guard_high(mb: MB, sink):
    """High-poly guard: the low construction at high resolution plus the revision-3 blossom
    (kept), the thorn lace inside the wing panels and the leaf ribs."""
    import sfv4_rev3 as R3
    from mathutils import Vector
    guard_low(mb, "high")
    for side in (-1, 1):
        # KEPT: revision-3 guard blossom construction (large, hilt petals), re-seated on the v4 boss
        R3.flower(sink, Vector((0.0, side * 23.3, GZ)), S.GUARD_BLOSSOM_R, Vector((0, side, 0)),
                  side * math.pi / 2, large=True, blade=False, up_hint=(1, 0, 0))
        # thorn lace inside each wing panel (revision-3 shoulder scrolls, re-fitted)
        for sign in (-1, 1):
            for k, curve in enumerate([
                [(22, 76), (32, 78), (42, 82), (49, 88), (45, 94)],
                [(28, 84), (37, 84), (42, 89), (41, 95), (35, 97)],
                [(49, 88), (48, 83), (44, 81), (40, 84), (41, 90)],
            ]):
                th = 9.0 + 5.0 * max(0.0, (35.0 - 14.0) / 44.0)
                pts = [Vector((sign * x, side * (th - 0.7), z)) for x, z in curve]
                pp = R3.smooth_path(pts, 7)
                R3.tube(sink, pp, lambda t: 0.62 * (1 - 0.3 * t), R3.INLAY, 7)
                for j in (1, 3):
                    p = Vector((sign * curve[j][0], side * (th - 0.7), curve[j][1]))
                    q = p + Vector((sign * 1.8, side * 0.1, -3.4))
                    R3.tube(sink, [p, p.lerp(q, .5) + Vector((sign * 1.0, 0, 0)), q],
                            lambda t: .6 * (1 - .85 * t), R3.SILVER, 6)
        # pendant thorn scroll (revision 3) on the pendant field
        for sign in (-1, 1):
            base = np.array([0, side * 15.0, 94.0])
            pts = [(0, 104.0), (sign * 1.9, 108.0), (sign * 4.2, 109.5), (sign * 3.2, 112.5), (sign * 5.6, 113.5),
                   (sign * 4.4, 116.0)]
            vv = []
            for x, z in pts:
                a = (z - 94.0) / (S.Z_PENDANT_TIP - 94.0)
                y = side * (15.0 + (10.5 - 15.0) * a + 1.1 - (-1.5) * 0 + 0.2)
                vv.append(Vector((x, y - side * 0.35 * (z - 94.0) * 0.0, z)))
            R3.tube(sink, R3.smooth_path(vv, 5), lambda t: .55 * (1 - .3 * t), R3.SILVER, 6)


# ====================================================================== collar

def collar(mb: MB, level, mat=STEEL):
    segs = _res(level, 96, 32, 20, 12)
    prof_z = [(S.Z_COLLAR_BOT - 1.0, 20.2, 17.6), (S.Z_COLLAR_BOT, 21.3, 18.8), (S.Z_COLLAR_BOT + 1.4, 21.6, 19.1),
              (S.Z_COLLAR_BOT + 2.4, 21.0, 18.5), (50.0, 21.4, 18.9), (56.0, 22.6, 20.0), (60.5, 23.8, 21.0),
              (S.Z_COLLAR_TOP, 23.2, 20.4)]
    if level == 2:
        prof_z = [prof_z[0], prof_z[1], prof_z[4], prof_z[6], prof_z[7]]
    elif level == 1:
        prof_z = [prof_z[0], prof_z[1], prof_z[3], prof_z[4], prof_z[5], prof_z[6], prof_z[7]]
    rings = [superellipse_ring(a, b, 2.3, segs, z) for z, a, b in prof_z]
    if level == "high":
        import sfv4_rev3 as R3
        mat = R3.SILVER
    loft_rings(mb, rings, "collar", mat, cap0=False, cap1=True)


def collar_high(mb: MB, sink):
    import sfv4_rev3 as R3
    from mathutils import Vector
    collar(mb, "high")
    # engraved thorn band on the ferrule (revision-3 scroll band idea, re-seated)
    for k in range(14):
        a = 2 * math.pi * k / 14
        pts = []
        for j in range(9):
            t = j / 8
            aa = a + t * 2 * math.pi / 14
            z = 50.5 + 2.2 * math.sin(t * math.pi * 2)
            rx, ry = 21.55, 19.05
            pts.append(Vector((rx * math.cos(aa), ry * math.sin(aa), z)))
        R3.tube(sink, pts, 0.28, R3.SILVER, 5)


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


def grip_core(mb: MB, level, offset, mat=WRAP, prefix="wrap"):
    """Oval loft of the grip. Low levels sit at ``offset`` = half the cord height over the core so the
    bake cage straddles the cord. Islands: 4 around x 2 along = 8 near-square islands (U tile 1..2)."""
    segs = _res(level, 128, 32, 20, 12)
    nz = _res(level, 120, 22, 12, 6)
    zs = np.linspace(S.Z_GRIP_BOT - 1.0, S.Z_GRIP_TOP + 1.0, nz)
    ang = np.linspace(0, 2 * math.pi, segs, endpoint=False) - math.pi / 4
    rings = np.array([[grip_surface(a, z, offset)[0] for a in ang] for z in zs])
    if level == "high":
        grid(mb, rings, True, "HIGH", mat)
        return
    # UV: u = angle x mean perimeter/2pi, v = z; islands by quadrant and half-length
    per = np.array([arclen(r, closed=True)[-1] for r in rings])
    uv = np.zeros((nz, segs + 1, 2))
    for i in range(nz):
        s = arclen(rings[i], closed=True)
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
    """Tight near-black cord wrap: two counter-wound bands of three cords each, alternating
    over/under at every crossing (revision-3 weave idea, finer and rounder)."""
    import sfv4_rev3 as R3
    grip_core(mb_core, "high", 0.0, mat=R3.CORE)
    turns = S.WRAP_TURNS
    z0, z1 = S.Z_GRIP_BOT + 1.0, S.Z_GRIP_TOP - 0.5
    steps = int(turns * 72)
    band_w = 9.5
    prof = []
    for j in range(13):
        h = math.sin(math.pi * j / 12.0) ** 0.55
        prof.append((j / 12.0 - 0.5, h))
    for direction in (-1, 1):
        rows = []
        for i in range(steps + 1):
            t = i / steps
            alpha = 2 * math.pi * turns * t
            theta = direction * alpha - math.pi / 2
            z = z0 + (z1 - z0) * t
            lift = 0.30 + direction * 0.30 * math.cos(alpha)
            a, b = grip_ab(z)
            # direction across the band inside the surface: along the helix normal (approx axial)
            pitch = (z1 - z0) / (2 * math.pi * turns)
            arc = math.hypot(a * math.sin(theta), b * math.cos(theta))
            den = math.hypot(arc, pitch)
            ring = []
            for w, h in prof:
                ww = w * band_w
                th2 = theta - direction * pitch * ww / (den * arc)
                zz = z + arc * ww / den
                p, n = grip_surface(th2, zz, lift + 0.05 + h * (S.WRAP_THICK - 0.25))
                ring.append(p)
            back = []
            for w, h in prof[::-1]:
                ww = w * band_w
                th2 = theta - direction * pitch * ww / (den * arc)
                zz = z + arc * ww / den
                p, n = grip_surface(th2, zz, lift - 0.05)
                back.append(p)
            rows.append(ring + back)
        rows = np.array(rows)
        idx = grid(mb_cord, rows, True, "HIGH", R3.CORD)
        fan_cap(mb_cord, list(idx[0]), rows[0].mean(axis=0), "HIGH", R3.CORD, flip=True)
        fan_cap(mb_cord, list(idx[-1]), rows[-1].mean(axis=0), "HIGH", R3.CORD)


# ---------------------------------------------------------------------- grip ornament

#: revision-3 grip clusters (hilt_revision.py), knots (x, z) in m, re-seated: the cluster near the
#: collar and the one near the pommel, shifted toward the spine side where the sheet shows them.
R3_GRIP = [
    {"stem": [(-.0052, .105), (-.0028, .095), (-.0043, .085), (.0004, .076), (-.0018, .065), (.0015, .053)],
     "twigs": [([(-.0043, .085), (.0005, .086), (.0054, .080)], .0054, .080, .0052),
               ([(-.0028, .095), (.0018, .099), (.0046, .096)], .0046, .096, .0035),
               ([(-.0018, .065), (-.0050, .064), (-.0066, .068)], -.0066, .068, .0033)],
     "buds": [([(.0004, .076), (-.0045, .073), (-.0075, .075)], -.0075, .075)],
     "zmap": lambda z: (z - .079) * 1000 * 1.25 + 8.0},
    {"stem": [(.0046, -.116), (.0014, -.107), (.0035, -.097), (-.0018, -.086), (-.0004, -.075), (-.0035, -.062)],
     "twigs": [([(-.0018, -.086), (.0026, -.084), (.0061, -.089)], .0061, -.089, .0048),
               ([(-.0004, -.075), (-.0036, -.073), (-.0060, -.077)], -.0060, -.077, .0038),
               ([(.0014, -.107), (-.0024, -.107), (-.0047, -.101)], -.0047, -.101, .0026)],
     "buds": [([(.0035, -.097), (.0064, -.099), (.0080, -.096)], .0080, -.096)],
     "zmap": lambda z: (z + .089) * 1000 * 1.25 - 100.0},
]
GRIP_ORN_X = 8.0          # shift toward +X (spine side, the sheet's left)
GRIP_ORN_XS = 1.35        # lateral scale
GRIP_BLOSSOM_SCALE = 1.7  # audit: enlarge the grip blossoms (sheet: ~12-14 mm)
ORN_OFFSET = S.WRAP_THICK + 0.25


def _gp(x_m, z_m, side, cl, off):
    """Grip surface point from a revision-3 (x, z) knot: x -> angle on the oval (front side -Y)."""
    x = x_m * 1000 * GRIP_ORN_XS + GRIP_ORN_X
    z = cl["zmap"](z_m)
    a, b = grip_ab(z)
    theta = math.acos(np.clip(x / a, -0.95, 0.95))
    if side < 0:
        theta = -theta
    return grip_surface(theta, z, off)


def grip_ornament(level, side, mb=None, sink=None, mat=STEEL):
    import sfv4_rev3 as R3
    from mathutils import Vector
    tag = "F" if side < 0 else "B"
    for ci, cl in enumerate(R3_GRIP):
        sgn = 1 if side < 0 else -1
        paths = [("stem", cl["stem"], 1.6)] + [(f"tw{k}", tw[0], 1.15) for k, tw in enumerate(cl["twigs"])] + \
                [(f"bd{k}", bd[0], 0.8) for k, bd in enumerate(cl["buds"])]
        for pname, knots, rad in paths:
            kn = [(x * sgn, z) for x, z in knots]
            pts3 = [_gp(x, z, side, cl, ORN_OFFSET)[0] for x, z in kn]
            path = catmull(pts3, 8 if level == "high" else 3)
            # re-project to the surface
            proj = []
            for p in path:
                a, b = grip_ab(p[2])
                th = math.atan2(p[1] / b, p[0] / a)
                proj.append(grip_surface(th, p[2], ORN_OFFSET)[0])
            proj = np.array(proj)
            if level == "high":
                R3.tube(sink, [Vector(p) for p in proj], lambda t, r=rad: r * (1 - .55 * t) * (1 + .09 * math.sin(t * 19 + .3)),
                        R3.SILVER, 7)
            elif level == 0:
                # the same path and radius law as the high tube (revision-3 construction), round
                tube(mb, proj, lambda t, r=rad: r * (1 - .55 * t), sides=6,
                     island=f"gorn_{tag}{ci}_{pname}", mat=mat, cap=("flat", "flat"))
        for k, (kn, x, z, r) in enumerate(cl["twigs"]):
            p, n = _gp(x * sgn, z, side, cl, ORN_OFFSET + 0.3)
            rr = r * 1000 * GRIP_BLOSSOM_SCALE
            if level == "high":
                R3.flower(sink, Vector(p), rr, Vector(n), .24 + k * .71 + ci * .35, blade=True, up_hint=(0, 0, 1))
            elif level in (0, 1):
                flower_disc(mb, p, rr, n, .24 + k * .71 + ci * .35, f"gorn_{tag}{ci}_bl{k}", mat,
                            n_out=25 if level == 0 else 15, sink=0.5)
        for k, (kn, x, z) in enumerate(cl["buds"]):
            p, n = _gp(x * sgn, z, side, cl, ORN_OFFSET + 0.2)
            if level == "high":
                tng = np.cross(n, [0, 0, 1])
                tng = _norm(tng)
                R3.ellipsoid(sink, Vector(p), Vector(tng * .9), Vector((0, 0, 1.25)), Vector(n * .55), R3.SILVER, 10, 5)


# ====================================================================== pommel (end cap)

ZP = S.Z_POMMEL_TOP
POMMEL_PROFILE = [  # (r, z) from the end-face centre outward and down to the ring; rounded bezel
    (0.0, ZP + 3.0), (8.0, ZP + 3.0), (16.2, ZP + 3.0), (16.6, ZP + 1.4), (17.6, ZP + 0.3), (19.3, ZP + 0.1),
    (20.9, ZP + 1.1), (21.8, ZP + 3.4), (22.0, ZP + 7.0), (22.0, ZP + 14.0), (21.6, ZP + 20.0), (20.4, ZP + 23.4),
    (18.9, ZP + 25.3), (18.9, ZP + 27.0), (19.5, ZP + 27.0), (19.5, ZP + 32.4), (18.7, ZP + 33.0), (15.0, ZP + 33.0),
    (0.0, ZP + 33.0)]
POMMEL_BANDS_L0 = [(0, 3, "planar"), (3, 8, "planar"), (8, 13, "cyl"), (13, 16, "cyl"), (16, 18, "planar")]


POMMEL_PROFILE_HIGH = POMMEL_PROFILE[:8] + [(22.0, ZP + 7.0), (21.1, ZP + 7.6), (21.0, ZP + 19.2), (21.7, ZP + 19.9)] +     POMMEL_PROFILE[11:]


def pommel(mb: MB, level, mat=STEEL):
    segs = _res(level, 160, 40, 24, 14)
    prof = list(POMMEL_PROFILE)
    bands = POMMEL_BANDS_L0
    band_mats = None
    if level == 2:
        keep = [0, 2, 5, 7, 10, 12, 14, 15, 17, 18]
        prof = [POMMEL_PROFILE[k] for k in keep]
        bands = [(0, 2, "planar"), (2, 3, "planar"), (3, 6, "cyl"), (6, 8, "cyl"), (8, 9, "planar")]
    elif level == "high":
        import sfv4_rev3 as R3
        prof = list(POMMEL_PROFILE_HIGH)
        bands = [(0, 3, "planar"), (3, 8, "planar"), (8, 9, "cyl"), (9, 10, "cyl"), (10, 11, "cyl"),
                 (11, 14, "cyl"), (14, len(prof) - 1, "planar")]
        band_mats = [R3.RECESS, R3.SILVER, R3.SILVER, R3.RECESS, R3.SILVER, R3.SILVER, R3.SILVER]
    lathe(mb, prof, segs, bands, mat, prefix="pommel" if level != "high" else "HIGHP", band_mats=band_mats)
    if level in (0, 1):
        flower_disc(mb, (0.0, 0.0, ZP + 2.4), 13.6, (0, 0, -1), -math.pi / 2, "pommel_bloss", mat,
                    n_out=40 if level == 0 else 25, up_hint=(0, 1, 0), height=0.2, sink=0.4)


def pommel_high(mb: MB, sink):
    """End cap at high resolution + the KEPT revision-3 medallion parts (flower, three concentric
    rims, thorn wreath, ten thorn scrolls) re-seated on the END FACE, and the pierced vine band on
    the side (revision-3 scroll band construction). No cord lug."""
    import sfv4_rev3 as R3
    from mathutils import Vector
    pommel(mb, "high")
    zf = ZP + 2.7   # field plane

    def wp(angle, radius, h):
        return Vector((radius * math.cos(angle), radius * math.sin(angle), zf - h))

    sc = 16.3 / 18.2 * 1000
    for r, h, wire in ((.01550, .01080 / 2.65, .00036), (.01480, .01150 / 2.65, .00023), (.01370, .01130 / 2.65, .00017)):
        R3.tube(sink, [wp(2 * math.pi * i / 128, r * sc * 1.03, min(h * 1000 * 0.55, 2.2)) for i in range(128)],
                wire * 1000 * 1.1, R3.SILVER, 8, True)
    R3.flower(sink, Vector((0, 0, zf)), 13.6, Vector((0, 0, -1)), -math.pi / 2, large=True, blade=False, up_hint=(0, 1, 0))
    wreath = []
    for i in range(240):
        a = 2 * math.pi * i / 240
        rad = (.01325 + .00034 * math.sin(5 * a + .2) + .00011 * math.sin(15 * a)) * .90 * sc
        wreath.append(wp(a, rad, 0.35))
    R3.tube(sink, wreath, .15 * 1.1, R3.INLAY, 6, True)

    def curve(knots, sub):
        return [(float(p[0]), float(p[1])) for p in catmull([(a, b) for a, b in knots], sub)]
    for k in range(10):
        a0 = 2 * math.pi * k / 10 - math.pi / 2
        d = 1 if k % 2 else -1
        start = .01325 + .00034 * math.sin(5 * a0 + .2) + .00011 * math.sin(15 * a0)
        knots = [(0, start), (.105, .01415), (.225, .01475), (.355, .01420), (.330, .01340), (.220, .01278),
                 (.105, .01293), (.115, .01347)]
        path = [wp(a0 + d * da, rad * .90 * sc, 0.45) for da, rad in curve(knots, 6)]
        R3.tube(sink, path, lambda t: .165 * 1.1 * (1 - .34 * t), R3.SILVER, 6)
        thorn = [(.225, .01475), (.125, .01503), (.050, .01455)]
        R3.tube(sink, [wp(a0 + d * da, rad * .90 * sc, 0.5) for da, rad in curve(thorn, 6)],
                lambda t: .135 * 1.1 * (1 - .48 * t), R3.SILVER, 5)
    # pierced vine band on the side wall (z ZP+8 .. ZP+20), revision-3 scroll band re-seated on r=21
    zc = ZP + 14.0
    half = 5.2
    motifs = 12
    rr = 21.45

    def surf(a, z):
        return Vector((rr * math.cos(a), rr * math.sin(a), z))
    spine = [surf(2 * math.pi * i / (motifs * 24), zc + half * .18 * math.sin(2 * math.pi * i / 24)) for i in range(motifs * 24)]
    R3.tube(sink, spine, .42, R3.SILVER, 6, True)
    for k in range(motifs):
        a = 2 * math.pi * k / motifs
        width = math.pi / motifs
        for direction in (-1, 1):
            flip = direction * (1 if k % 2 else -1)
            knots = [(0, 0), (.38, .22), (.74, .70), (.92, .43), (.72, -.10), (.46, -.16), (.44, .13)]
            path = [surf(a + direction * width * u, zc + flip * half * v) for u, v in curve(knots, 6)]
            R3.tube(sink, path, lambda t: .40 * (1 - .30 * t), R3.SILVER, 6)
            thorn = [(.74, .70), (.60, .96), (.40, .78)]
            R3.tube(sink, [surf(a + direction * width * u, zc + flip * half * v) for u, v in curve(thorn, 5)],
                    lambda t: .34 * (1 - .45 * t), R3.SILVER, 5)
