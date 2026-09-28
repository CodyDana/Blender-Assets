"""Exterior stage (2026-09-27, WorkFiles/armory/build/BUILD_NOTES.md): the Japanese courtyard garden in front of the
armory entrance, the building's roof and stone foundation, and the layered scenery around the site.

Imported by build_armory_kit.py (which calls setup(globals()) so this module can use its Piece class and mesh helpers).
Every piece here is prefixed SM_AKX_, lives in the Blender collections "KitExterior" / "AssemblyExterior", is QA'd and
exported through Scripts/pipeline with UCX collision like the room kit, and is placed from the same layout.json, so the
Unreal level script assembles it too. All geometry is procedural and original (no downloads, no third-party assets).

Frame (same as the room): metres, origin at the interior south-west corner at floor level, +X east, +Y north (the rear
platform), Z up. The courtyard lies SOUTH of the entrance: X -4..16, Y -13..-0.3 (20 x 12.7 m), ground top Z 0.

Pieces:
  ground      SM_AKX_Ground_Field (400 x 400 m lawn), SM_AKX_Court_Gravel (raked gravel slab, 20 x 12.7 m),
              SM_AKX_RakeRing_A/B (concentric raked rings around the moss mounds)
  paving      SM_AKX_Landing (cut-granite landing at the entrance), SM_AKX_PathSlab (ishidatami strip),
              SM_AKX_StepStone_A/B/C (irregular stepping stones)
  garden      SM_AKX_MossMound_A/B, SM_AKX_Rock_A/B/C, SM_AKX_Shrub_A/B (clipped mounds), SM_AKX_StoneLantern (toro),
              SM_AKX_Tsukubai (stone basin, water, bamboo spout, flanking stones)
  trees       SM_AKX_Pine_A/B (Japanese black pine, cloud-pruned pads), SM_AKX_MapleRed_A/B, SM_AKX_MapleGreen_A
              (alpha-masked foliage cards; collision on the trunk only)
  enclosure   SM_AKX_Wall_4 (plaster wall on a stone base under a tiled coping), SM_AKX_WallPier, SM_AKX_Gate (roofed
              gate, 2.38 m clear)
  building    SM_AKX_Roof (hipped tile roof, 1.0 m eaves), SM_AKX_Foundation_2 / _1 / _07 / _Corner (stone band)
  scenery     SM_AKX_TreeLine_24 / SM_AKX_TreeLineFar_48 (emissive alpha cards in layers), SM_AKX_Hills_Ring,
              SM_AKX_Mountains_Ring (360 degree emissive silhouettes); none of them casts a shadow
"""
import math
import random

G = {}


def setup(ns):
    """Keep a live reference to build_armory_kit's globals (Piece, lathe, card are defined after the import)."""
    global G
    G = ns


def Piece(name):
    return G["Piece"](name)


T = "M_AK_Timber"
GRAV, STO, MOSS, FIELD, BARK = "M_AKX_Gravel", "M_AKX_Stone", "M_AKX_Moss", "M_AKX_Field", "M_AKX_Bark"
SHRUB, ROOF, WPL, WATER, BAMBOO = "M_AKX_Shrub", "M_AKX_RoofTile", "M_AKX_WallPlaster", "M_AKX_Water", "M_AKX_Bamboo"
PINE, MRED, MGRN = "M_AKX_PinePad", "M_AKX_MapleRed", "M_AKX_MapleGreen"

# name: (texture set or None, tile m, params) -- merged into build_armory_kit.MATERIALS. Texture sets named AKX_* load
# T_AKX_<set>_*.png (Scripts/armory/make_exterior_textures.py).
MATERIALS = {
    GRAV: ("AKX_Gravel", 2.0, {}),
    STO: ("AKX_Stone", 1.0, {}),
    MOSS: ("AKX_Moss", 2.0, {}),
    FIELD: ("AKX_Field", 8.0, {}),
    BARK: ("AKX_Bark", 1.0, {}),
    SHRUB: ("AKX_Shrub", 1.0, {}),
    ROOF: ("AKX_RoofTile", 1.2, {}),
    WPL: ("Plaster", 2.0, {"tint": 0.72}),          # the room's plaster set, dimmed (albedo well under 0.80)
    WATER: (None, 1.0, {"color": "#0A0D0E", "rough": 0.03}),
    BAMBOO: (None, 1.0, {"color": "#7D7244", "rough": 0.42}),
    # alpha-masked, two-sided foliage cards with a little leaf translucency (Unreal: Masked, two-sided foliage)
    PINE: ("AKX_PinePad", None, {"alpha": True, "two_sided": True, "translucent": 0.2, "edge_fade": True}),
    MRED: ("AKX_MapleRed", None, {"alpha": True, "two_sided": True, "translucent": 0.1, "edge_fade": True}),
    MGRN: ("AKX_MapleGreen", None, {"alpha": True, "two_sided": True, "translucent": 0.2, "edge_fade": True}),
    # scenery: emissive pictures (like the old garden backdrop); the tree lines are alpha-masked
    # f1: 7 -> 10 with a warmer near line (make_exterior_textures.treeline): the windows read hot gold-green
    "M_AKX_TreeLine": ("AKX_TreeLine", None, {"emit_image": True, "emit": 10.0, "alpha": True, "two_sided": True, "unlit": True}),
    "M_AKX_TreeLineFar": ("AKX_TreeLineFar", None, {"emit_image": True, "emit": 2.5, "alpha": True, "two_sided": True, "unlit": True}),
    "M_AKX_Hills": ("AKX_Hills", None, {"emit_image": True, "emit": 6.0, "unlit": True}),
    "M_AKX_Mountains": ("AKX_Mountains", None, {"emit_image": True, "emit": 5.0, "unlit": True}),
}
# pieces that never cast a shadow (Blender visible_shadow, Unreal cast_shadow = False): the scenery must not shade the
# side windows or the courtyard
NO_SHADOW = {"SM_AKX_TreeLine_24", "SM_AKX_TreeLineFar_48", "SM_AKX_Hills_Ring", "SM_AKX_Mountains_Ring"}

COURT = (-4.0, 16.0, -13.0, -0.30)       # courtyard X0, X1, Y0, Y1 (wall centre lines / building face)
PLAYER_START = {"loc": [6.0, -10.4, 0.0], "rot_z": 90.0}   # on the path inside the gate, facing the entrance (+Y)
CAMERA = ("CG_Garden", (2.9, -12.3, 1.8), (6.9, -1.0, 2.3), 20)
CAMERA_EXPOSURE = {"CG_Garden": {"golden": -2.8, "gallery": -1.0}}   # review EV (the room presets are +0.6 / +0.8)
ROOF_EAVE, ROOF_PITCH, ROOF_EAVE_Z, ROOF_T = 1.0, 26.0, 4.70, 0.18


# --------------------------------------------------------------------------- vector helpers

def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def mul(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def norm(a):
    L = math.sqrt(dot(a, a)) or 1.0
    return (a[0] / L, a[1] / L, a[2] / L)


def dist(a, b):
    return math.sqrt(dot(sub(a, b), sub(a, b)))


# --------------------------------------------------------------------------- mesh generators

def slab(top, t, top_mat, rest_mat, tile, u_axis=None):
    """A slab under a planar quad `top` (4 corners, counter-clockwise seen from above, so the top faces up), thickness t
    straight down. Top UV: planar, U along corner 0 -> 1 (or u_axis), V across it, in tile units."""
    bot = [(p[0], p[1], p[2] - t) for p in top]
    verts = list(top) + bot
    e1 = norm(sub(top[1], top[0])) if u_axis is None else norm(u_axis)
    nrm = norm(cross(sub(top[1], top[0]), sub(top[3], top[0])))
    e2 = cross(nrm, e1)
    tuv = [(dot(p, e1) / tile, dot(p, e2) / tile) for p in top]
    faces = [(0, 1, 2, 3), (7, 6, 5, 4)]
    uvs = [tuv, [(dot(p, e1) / 2.0, dot(p, e2) / 2.0) for p in reversed(bot)]]
    mats = [top_mat, rest_mat]
    for i in range(4):
        j = (i + 1) % 4
        faces.append((4 + i, 4 + j, j, i))
        L = dist(top[i], top[j])
        uvs.append([(0, 0), (L / 2.0, 0), (L / 2.0, t / 2.0), (0, t / 2.0)])
        mats.append(rest_mat)
    return verts, faces, uvs, mats


def beam(p0, p1, w, h, mat, up=(0, 0, 1)):
    """An oriented box beam from p0 to p1 (centre line along the bottom-centre of the beam), w wide, h tall."""
    d = norm(sub(p1, p0))
    side = norm(cross(d, up))
    upv = cross(side, d)
    L = dist(p0, p1)
    corners = []
    for p in (p0, p1):
        for sx, sz in ((-1, 0), (1, 0), (1, 1), (-1, 1)):
            corners.append(add(p, add(mul(side, sx * w / 2), mul(upv, sz * h))))
    # 0-3 at p0 ring (-s,0) (+s,0) (+s,h) (-s,h); 4-7 at p1
    # side = d x up points to the beam's right, so these windings are the outward ones (checked: the bottom face
    # (1, 0, 4, 5) has normal -up, the p0 end (1, 2, 3, 0) has normal -d)
    faces = [(1, 2, 3, 0), (7, 6, 5, 4), (1, 0, 4, 5), (2, 1, 5, 6), (3, 2, 6, 7), (0, 3, 7, 4)]
    uvs = [[(0, 0), (0, h), (w, h), (w, 0)], [(0, 0), (w, 0), (w, h), (0, h)]]
    uvs += [[(0, 0), (0, 0.2), (L / 2, 0.2), (L / 2, 0)]] * 4
    return corners, faces, uvs, [mat] * 6


def tube(path, radii, sides, cap=True, u_rep=None):
    """A tapering tube along a polyline (parallel-transport frames), outward faces, UV U around (integer repeats of a
    1 m tile), V along the length in metres; an optional pointed cap at the end."""
    n = len(path)
    t0 = norm(sub(path[1], path[0]))
    ref = (0, 0, 1) if abs(t0[2]) < 0.9 else (1, 0, 0)
    nr = norm(cross(ref, t0))
    verts, rings, L = [], [], [0.0]
    t = t0
    for k in range(n):
        if k == 0:
            t = t0
        elif k == n - 1:
            t = norm(sub(path[k], path[k - 1]))
        else:
            t = norm(add(norm(sub(path[k], path[k - 1])), norm(sub(path[k + 1], path[k]))))
        nr = norm(sub(nr, mul(t, dot(nr, t))))
        b = cross(t, nr)
        ring = []
        for i in range(sides):
            a = 2 * math.pi * i / sides
            verts.append(add(path[k], add(mul(nr, math.cos(a) * radii[k]), mul(b, math.sin(a) * radii[k]))))
            ring.append(len(verts) - 1)
        rings.append(ring)
        if k:
            L.append(L[-1] + dist(path[k], path[k - 1]))
    rep = u_rep or max(1, round(2 * math.pi * radii[0]))
    faces, uvs = [], []
    for k in range(n - 1):
        for i in range(sides):
            j = (i + 1) % sides
            faces.append((rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]))
            u0, u1 = i / sides * rep, (i + 1) / sides * rep
            uvs.append([(u0, L[k]), (u1, L[k]), (u1, L[k + 1]), (u0, L[k + 1])])
    if cap:
        verts.append(add(path[-1], mul(t, radii[-1] * 1.5 + 0.004)))
        ti = len(verts) - 1
        for i in range(sides):
            j = (i + 1) % sides
            faces.append((rings[-1][i], rings[-1][j], ti))
            uvs.append([(i / sides * rep, L[-1]), ((i + 1) / sides * rep, L[-1]), ((i + 0.5) / sides * rep, L[-1] + 0.05)])
    return verts, faces, uvs


def quad_card(c, e1, e2, w, h):
    """A foliage card centred on c, spanned by unit vectors e1 (U) and e2 (V), w x h, UV 0-1."""
    hw, hh = mul(e1, w / 2), mul(e2, h / 2)
    verts = [sub(sub(c, hw), hh), sub(add(c, hw), hh), add(add(c, hw), hh), add(sub(c, hw), hh)]
    return verts, [(0, 1, 2, 3)], [[(0, 0), (1, 0), (1, 1), (0, 1)]]


def lathe_uv(profile, sides, tile, cx=0.0, cy=0.0):
    """G['lathe'] with UVs rescaled to a tile: U = arc length around the widest ring (integer repeats), V = profile
    length, both in tile units."""
    verts, faces, uvs = G["lathe"](profile, sides, cx, cy)
    rep = max(1, round(2 * math.pi * max(r for r, _ in profile) / tile))
    uvs = [[(u * rep, v / tile) for (u, v) in f] for f in uvs]
    return verts, faces, uvs


def smooth_noise(rng, k=6, amp=1.0):
    """A smooth random function of a unit direction (sum of a few random plane waves)."""
    waves = [(norm((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1))), rng.uniform(1.5, 3.5), rng.uniform(0, 6.3),
              rng.uniform(0.4, 1.0)) for _ in range(k)]
    tot = sum(w[3] for w in waves)

    def f(d):
        return amp * sum(a * math.sin(fr * dot(d, v) + ph) for v, fr, ph, a in waves) / tot
    return f


def displace(verts, centre, fn, scale=(1, 1, 1)):
    out = []
    for p in verts:
        d = sub(p, centre)
        L = math.sqrt(dot(d, d))
        if L < 1e-9:
            out.append(p)
            continue
        u = mul(d, 1 / L)
        k = 1 + fn(u)
        out.append((centre[0] + d[0] * k * scale[0], centre[1] + d[1] * k * scale[1], centre[2] + d[2] * k * scale[2]))
    return out


def flat_stone(rng, rx, ry, top=0.07, bottom=-0.06, sides=11, cx=0.0, cy=0.0, tile=1.0):
    """An irregular flat stone: a slightly domed top fan, a chamfer ring and sides down into the gravel (open bottom)."""
    angs = sorted((2 * math.pi * (i + rng.uniform(-0.3, 0.3)) / sides) for i in range(sides))
    rad = [(1 + 0.13 * math.sin(3 * a + rng.uniform(0, 6)) + rng.uniform(-0.06, 0.06)) for a in angs]
    outer = [(cx + rx * r * math.cos(a), cy + ry * r * math.sin(a)) for r, a in zip(rad, angs)]
    verts = [(x, y, top - 0.022) for x, y in outer]                                              # 0..s-1 chamfer edge
    verts += [(cx + (x - cx) * 0.86, cy + (y - cy) * 0.86, top) for x, y in outer]              # s..2s-1 top rim
    verts += [(x, y, bottom) for x, y in outer]                                                  # 2s..3s-1 foot
    verts.append((cx, cy, top + 0.006))
    c = len(verts) - 1
    s = sides
    faces, uvs = [], []
    top_uv = lambda p: (p[0] / tile, p[1] / tile)
    for i in range(s):
        j = (i + 1) % s
        faces.append((c, s + i, s + j))
        uvs.append([top_uv(verts[c]), top_uv(verts[s + i]), top_uv(verts[s + j])])
        faces.append((i, j, s + j, s + i))
        uvs.append([top_uv(verts[i]), top_uv(verts[j]), top_uv(verts[s + j]), top_uv(verts[s + i])])
        L = dist(verts[i], verts[j])
        faces.append((2 * s + i, 2 * s + j, j, i))
        uvs.append([(0, 0), (L, 0), (L, top - bottom), (0, top - bottom)])
    return verts, faces, uvs


# --------------------------------------------------------------------------- garden pieces

def ground_pieces():
    out = []
    X0, X1, Y0, Y1 = COURT
    out.append(Piece("SM_AKX_Ground_Field").box(0, 400, 0, 400, -0.40, -0.02, FIELD).col(0, 400, 0, 400, -0.40, -0.02))
    out.append(Piece("SM_AKX_Court_Gravel").box(0, X1 - X0, 0, Y1 - Y0, -0.12, 0.0, GRAV, uv="x")
               .col(0, X1 - X0, 0, Y1 - Y0, -0.12, 0.0))
    # cut-granite landing in front of the entrance (X 3.7-8.3, Y -1.82..-0.42 when placed at (3.7, -1.82))
    ld = Piece("SM_AKX_Landing")
    for k in range(4):
        ld.box(k * 1.15 + 0.006, (k + 1) * 1.15 - 0.006, 0.006, 1.40, -0.08, 0.06, STO)
    out.append(ld.col(0, 4.6, 0, 1.40, -0.08, 0.06))
    # ishidatami strip: rows of rectangular cut stones, 1.2 x 3.0 m
    rng = random.Random(501)
    ps = Piece("SM_AKX_PathSlab")
    y = 0.0
    while y < 2.99:
        h = min(rng.uniform(0.28, 0.46), 3.0 - y)
        x = 0.0
        while x < 1.199:
            w = min(rng.uniform(0.30, 0.62), 1.2 - x)
            if 1.2 - (x + w) < 0.18:
                w = 1.2 - x
            ztop = 0.05 + rng.uniform(-0.004, 0.004)
            ps.box(x + 0.008, x + w - 0.008, y + 0.008, y + h - 0.008, -0.08, ztop, STO)
            x += w
        y += h
    ps.box(-0.08, 0.0, 0, 3.0, -0.08, 0.035, STO).box(1.2, 1.28, 0, 3.0, -0.08, 0.035, STO)   # kerb stones
    out.append(ps.col(-0.08, 1.28, 0, 3.0, -0.08, 0.055))
    for k, (rx, ry, seed) in zip("ABC", ((0.30, 0.25, 511), (0.26, 0.22, 512), (0.36, 0.27, 513))):
        st = Piece(f"SM_AKX_StepStone_{k}")
        st.mesh(*flat_stone(random.Random(seed), rx, ry), STO, smooth=False)
        out.append(st.col(-rx, rx, -ry, ry, -0.06, 0.07))
    # moss mounds and the raked rings around them (rings in the mounds' own frame, same ellipse)
    for k, (rx, ry, hgt, seed) in zip("AB", ((1.4, 1.0, 0.42, 521), (0.95, 0.75, 0.30, 522))):
        mm = Piece(f"SM_AKX_MossMound_{k}")
        prof = [(1.02, -0.06), (1.0, 0.0), (0.92, 0.30), (0.75, 0.62), (0.52, 0.85), (0.26, 0.97), (0, 1.0)]
        v, f, uv = lathe_uv([(r, z) for r, z in prof], 28, 2.0)
        rng = random.Random(seed)
        fn = smooth_noise(rng, 7, 0.10)
        v = [(x * rx, y * ry, (z * hgt) if z > 0 else z) for x, y, z in v]
        v = displace(v, (0, 0, -0.1), lambda d: fn(d) * max(0.0, d[2] + 0.2))
        mm.mesh(v, f, uv, MOSS, smooth=True)
        out.append(mm.col(-rx, rx, -ry, ry, -0.06, hgt * 0.9))
        rr = Piece(f"SM_AKX_RakeRing_{k}")
        out.append(rr.mesh(*rake_ring(rx * 1.04, ry * 1.04, 0.62), GRAV).col(-rx - 0.7, rx + 0.7, -ry - 0.7, ry + 0.7,
                                                                                 -0.01, 0.006))
    # rocks (ishigumi): noise-displaced, partly buried
    for k, (sx, sy, sz, seed) in zip("ABC", ((0.75, 0.55, 0.60, 531), (0.55, 0.45, 0.42, 532), (0.40, 0.34, 0.95, 533))):
        rk = Piece(f"SM_AKX_Rock_{k}")
        prof = [(0, -1.0)] + [(math.sin(a), -math.cos(a)) for a in [i * math.pi / 8 for i in range(1, 8)]] + [(0, 1.0)]
        v, f, uv = lathe_uv(prof, 16, 1.0)
        rng = random.Random(seed)
        fn = smooth_noise(rng, 8, 0.28)
        v = displace(v, (0, 0, 0), fn)
        v = [(x * sx, y * sy, z * sz * 0.5 + sz * 0.38) for x, y, z in v]    # base sunk ~0.12 sz into the ground
        rk.mesh(v, f, uv, STO, smooth=True)
        xs, ys, zs = [p[0] for p in v], [p[1] for p in v], [p[2] for p in v]
        out.append(rk.col(min(xs) * 0.85, max(xs) * 0.85, min(ys) * 0.85, max(ys) * 0.85, 0, max(zs) * 0.95))
    # clipped shrub mounds (karikomi)
    for k, (rx, ry, hgt, seed) in zip("AB", ((0.80, 0.62, 0.78, 541), (0.55, 0.48, 0.55, 542))):
        sh = Piece(f"SM_AKX_Shrub_{k}")
        prof = [(0.80, -0.04), (0.92, 0.10), (1.0, 0.35), (0.95, 0.62), (0.78, 0.85), (0.45, 0.98), (0, 1.02)]
        v, f, uv = lathe_uv(prof, 24, 1.0)
        rng = random.Random(seed)
        fn = smooth_noise(rng, 9, 0.12)
        v = [(x * rx, y * ry, z * hgt) for x, y, z in v]
        v = displace(v, (0, 0, hgt * 0.3), fn)
        sh.mesh(v, f, uv, SHRUB, smooth=True)
        out.append(sh.col(-rx * 0.9, rx * 0.9, -ry * 0.9, ry * 0.9, 0, hgt))
    out.append(stone_lantern())
    out.append(tsukubai())
    return out


def rake_ring(rx, ry, width, seg=56, nr=3):
    """An elliptical annulus just above the gravel (+4 mm) whose UV V runs outward, so the gravel's raked ridges (lines of
    constant V) follow the mound's outline as concentric rings."""
    verts, rings = [], []
    for k in range(nr + 1):
        off = width * k / nr
        ring = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            verts.append(((rx + off) * math.cos(a), (ry + off) * math.sin(a), 0.004))
            ring.append(len(verts) - 1)
        rings.append(ring)
    mid_circ = 2 * math.pi * math.sqrt(((rx + width / 2) ** 2 + (ry + width / 2) ** 2) / 2)
    rep = max(1, round(mid_circ / 2.0))
    faces, uvs = [], []
    for k in range(nr):
        for i in range(seg):
            j = (i + 1) % seg
            faces.append((rings[k + 1][i], rings[k + 1][j], rings[k][j], rings[k][i]))
            u0, u1 = i / seg * rep, (i + 1) / seg * rep
            v0, v1 = width * k / nr / 2.0, width * (k + 1) / nr / 2.0
            uvs.append([(u0, v1), (u1, v1), (u1, v0), (u0, v0)])
    return verts, faces, uvs


def stone_lantern():
    """A Kasuga-style stone lantern (toro), 2.0 m: hexagonal base, round post with a collar, flared middle platform,
    a fire box of six posts around a dim paper core, an upturned twelve-point roof and a jewel finial."""
    tl = Piece("SM_AKX_StoneLantern")
    L = G["lathe"]
    parts = [
        ([(0, 0.0), (0.36, 0.0), (0.36, 0.14), (0.27, 0.22), (0, 0.22)], 6),
        ([(0, 0.21), (0.10, 0.21), (0.10, 0.58), (0.118, 0.60), (0.118, 0.645), (0.10, 0.665), (0.10, 1.01),
          (0, 1.01)], 10),
        ([(0, 1.0), (0.13, 1.0), (0.29, 1.11), (0.31, 1.20), (0, 1.20)], 6),
        ([(0, 1.19), (0.235, 1.19), (0.235, 1.245), (0, 1.245)], 6),
        ([(0, 1.475), (0.235, 1.475), (0.235, 1.53), (0, 1.53)], 6),
        ([(0, 1.83), (0.058, 1.835), (0.075, 1.88), (0.062, 1.94), (0.024, 1.985), (0, 1.995)], 12),
    ]
    for prof, sides in parts:
        v, f, uv = L(prof, sides)
        tl.mesh(v, f, [[(a * 1.4, b) for a, b in fu] for fu in uv], STO, smooth=sides > 8)
    v, f, uv = L([(0, 1.25), (0.185, 1.25), (0.185, 1.47), (0, 1.47)], 6)        # the dim paper core
    tl.mesh(v, f, uv, "M_AK_Paper")
    for i in range(6):                                                                # six fire-box posts
        a = 2 * math.pi * i / 6
        p0, p1 = (0.205 * math.cos(a), 0.205 * math.sin(a), 1.245), (0.205 * math.cos(a), 0.205 * math.sin(a), 1.475)
        tl.mesh(*beam(p0, p1, 0.07, 0.07, STO, up=(math.cos(a), math.sin(a), 0)))
    # roof: 12 sides, the six corner vertices (even index) pushed out and lifted = the upturned warabite
    prof = [(0, 1.525), (0.43, 1.525), (0.47, 1.575), (0.30, 1.70), (0.11, 1.80), (0.07, 1.84), (0, 1.845)]
    v, f, uv = L(prof, 12)
    v2 = []
    for idx, (x, y, z) in enumerate(v):
        r = math.hypot(x, y)
        a = math.atan2(y, x)
        corner = abs(((a / (2 * math.pi / 6)) + 0.5) % 1.0 - 0.5) < 0.05
        if corner and r > 0.40:
            k = 1.10 if r > 0.45 else 1.07
            x, y, z = x * k, y * k, z + (0.055 if r > 0.45 else 0.04)
        v2.append((x, y, z))
    tl.mesh(v2, f, [[(a * 1.4, b) for a, b in fu] for fu in uv], STO)
    return tl.col(-0.36, 0.36, -0.36, 0.36, 0, 2.0)


def tsukubai():
    """A low stone water basin (0.45 m) with a still water surface, a bamboo spout on a bamboo post, the front stone
    and two flanking stones. Origin at the basin centre."""
    tb = Piece("SM_AKX_Tsukubai")
    rng = random.Random(551)
    prof = [(0, -0.05), (0.30, -0.05), (0.36, 0.10), (0.385, 0.28), (0.34, 0.41), (0.27, 0.45), (0.205, 0.435),
            (0.185, 0.37), (0.11, 0.345), (0, 0.34)]
    v, f, uv = lathe_uv(prof, 20, 1.0)
    fn = smooth_noise(rng, 7, 0.07)
    # rough outside and lip; the bowl interior (radius < 0.21 m) stays true so the water surface fits it
    v = [p if math.hypot(p[0], p[1]) < 0.21 and p[2] > 0.3 else q for p, q in zip(v, displace(v, (0, 0, 0.2), fn))]
    tb.mesh(v, f, uv, STO, smooth=True)
    wv, wf, wu = [], [], []
    for i in range(20):
        a = 2 * math.pi * i / 20
        wv.append((0.196 * math.cos(a), 0.196 * math.sin(a), 0.405))
    wv.append((0, 0, 0.405))
    for i in range(20):
        j = (i + 1) % 20
        wf.append((20, i, j))
        wu.append([(0.5, 0.5), (0.5 + 0.5 * math.cos(2 * math.pi * i / 20), 0.5 + 0.5 * math.sin(2 * math.pi * i / 20)),
                   (0.5 + 0.5 * math.cos(2 * math.pi * j / 20), 0.5 + 0.5 * math.sin(2 * math.pi * j / 20))])
    tb.mesh(wv, wf, wu, WATER)
    tb.mesh(*tube([(0.58, 0.22, -0.05), (0.58, 0.22, 0.84)], [0.042, 0.040], 10, cap=False), BAMBOO, smooth=True)
    tb.mesh(*tube([(0.60, 0.20, 0.80), (0.36, 0.11, 0.70), (0.14, 0.03, 0.62)], [0.022, 0.021, 0.020], 8, cap=False),
            BAMBOO, smooth=True)
    tb.mesh(*flat_stone(random.Random(552), 0.34, 0.26, top=0.09, cx=0.0, cy=-0.78), STO)
    for (cx, cy, s, seed) in ((-0.62, -0.25, 0.26, 553), (0.66, -0.36, 0.22, 554)):
        prof2 = [(0, -1.0)] + [(math.sin(a), -math.cos(a)) for a in [i * math.pi / 6 for i in range(1, 6)]] + [(0, 1.0)]
        v, f, uv = lathe_uv(prof2, 12, 1.0)
        fn2 = smooth_noise(random.Random(seed), 6, 0.25)
        v = displace(v, (0, 0, 0), fn2)
        v = [(cx + x * s, cy + y * s * 0.85, z * s * 0.55 + s * 0.35) for x, y, z in v]
        tb.mesh(v, f, uv, STO, smooth=True)
    return tb.col(-0.40, 0.40, -0.40, 0.40, 0, 0.45).col(0.53, 0.63, 0.17, 0.27, 0, 0.84) \
        .col(-0.90, -0.34, -0.50, 0.0, 0, 0.35).col(0.42, 0.90, -0.60, -0.12, 0, 0.30)


# --------------------------------------------------------------------------- trees

def catmull(pts, per=4):
    out = []
    P = [pts[0]] + list(pts) + [pts[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for s in range(per):
            t = s / per
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[k]) + (-p0[k] + p2[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2
                                    + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t3) for k in range(3)))
    out.append(pts[-1])
    return out


def pine_tree(name, seed, height, lean, n_branch, spread):
    """Japanese black pine, cloud-pruned: a leaning S-curved trunk, near-horizontal branches that turn up at the end,
    each carrying a flat needle pad (a horizontal card over a ring of vertical and tilted cards)."""
    rng = random.Random(seed)
    pc = Piece(name)
    lx, ly = lean
    ctrl = [(0, 0, -0.25), (0.05 * lx, 0.05 * ly, 0.5), (0.35 * lx + 0.12, 0.35 * ly, 1.3),
            (0.75 * lx - 0.10, 0.75 * ly + 0.08, 2.2), (0.95 * lx, 0.95 * ly - 0.06, 3.1),
            (0.80 * lx + 0.08, 0.80 * ly, height - 0.6), (0.70 * lx, 0.70 * ly, height)]
    trunk = catmull(ctrl, 3)
    n = len(trunk)
    radii = [0.21 * (1 - 0.72 * k / (n - 1)) + (0.06 if k == 0 else 0) for k in range(n)]
    pc.mesh(*tube(trunk, radii, 9), BARK, smooth=True)
    tris_pad = []

    def pad(c, w, d, heading):
        e1 = (math.cos(heading), math.sin(heading), 0)
        e2 = (-math.sin(heading), math.cos(heading), 0)
        tilt = rng.uniform(-0.12, 0.12)
        pc.mesh(*quad_card(add(c, (0, 0, 0.10)), e1, norm(add(e2, (0, 0, tilt))), w, d), PINE)
        pc.mesh(*quad_card(add(c, (0, 0, -0.04)), e1, norm(add(e2, (0, 0, -tilt))), w * 0.8, d * 0.8), PINE)
        for k in range(3):
            a = heading + k * math.pi / 3 + rng.uniform(-0.2, 0.2)
            e = (math.cos(a), math.sin(a), 0)
            span = w if k == 0 else (w + d) / 2
            pc.mesh(*quad_card(add(c, (0, 0, 0.08)), e, norm((rng.uniform(-0.15, 0.15), 0, 1)), span, 0.58), PINE)
        tris_pad.append(1)

    zs = [1.7 + (height - 2.3) * (i / max(1, n_branch - 1)) ** 0.9 for i in range(n_branch)]
    az = rng.uniform(0, 6.28)
    for i, z in enumerate(zs):
        k = min(range(n), key=lambda q: abs(trunk[q][2] - z))
        base = trunk[k]
        az += 2.4 + rng.uniform(-0.35, 0.35)
        length = spread * (1.0 - 0.55 * i / n_branch) * rng.uniform(0.8, 1.1)
        d = (math.cos(az), math.sin(az), 0)
        pts = [base, add(base, add(mul(d, length * 0.35), (0, 0, -0.05))),
               add(base, add(mul(d, length * 0.7), (0, 0, 0.0))), add(base, add(mul(d, length), (0, 0, 0.22)))]
        path = catmull(pts, 2)
        r0 = max(0.035, radii[k] * 0.45)
        pc.mesh(*tube(path, [r0 * (1 - 0.7 * q / (len(path) - 1)) for q in range(len(path))], 5), BARK, smooth=True)
        w = 1.0 + 0.9 * (1 - i / n_branch) * rng.uniform(0.85, 1.1)
        pad(add(path[-1], (0, 0, 0.18)), w, w * 0.75, az)
        if length > 1.2:   # a second, smaller pad on a side twig
            side = (math.cos(az + 0.9), math.sin(az + 0.9), 0)
            mid = path[len(path) // 2]
            tw = [mid, add(mid, add(mul(side, 0.45), (0, 0, 0.12)))]
            pc.mesh(*tube(tw, [r0 * 0.5, r0 * 0.25], 4), BARK)
            pad(add(tw[-1], (0, 0, 0.14)), w * 0.6, w * 0.45, az + 0.9)
    pad(add(trunk[-1], (0, 0, 0.12)), 1.1, 0.9, az)
    bx, by = trunk[2][0], trunk[2][1]
    return pc.col(bx - 0.25, bx + 0.25, by - 0.25, by + 0.25, 0, 2.2)


def maple_tree(name, seed, trunk_len, levels, leaf_mat, card=1.5, spread=0.9):
    """Japanese maple: a short trunk splitting into leaders, recursive branching to `levels`, clusters of three crossed
    leaf cards (plus a flat one) at every tip and on the last branch level."""
    rng = random.Random(seed)
    pc = Piece(name)
    tips = []

    def grow(p0, d, length, r0, level):
        nseg = 6 if level == 0 else max(3, int(length / 0.45) + 2)
        pts, dd = [p0], d
        for _ in range(nseg):
            dd = norm(add(dd, (rng.gauss(0, 0.16), rng.gauss(0, 0.16), rng.gauss(0, 0.08) + 0.04)))
            pts.append(add(pts[-1], mul(dd, length / nseg)))
        r_end = r0 * 0.55 if level < levels else 0.006
        radii = [r0 + (r_end - r0) * k / nseg for k in range(nseg + 1)]
        pc.mesh(*tube(pts, radii, (8, 6, 5, 4)[min(level, 3)]), BARK, smooth=True)
        if level >= levels:
            tips.append(pts[-1])
            return
        nchild = 3 if level == 0 else rng.choice((2, 3, 3))
        az0 = rng.uniform(0, 6.28)
        for c in range(nchild):
            f = rng.uniform(0.75, 0.95) if level == 0 else rng.uniform(0.5, 1.0)
            k = min(nseg, max(1, int(round(f * nseg))))
            az = az0 + 2 * math.pi * c / nchild + rng.uniform(-0.4, 0.4)
            out = (math.cos(az), math.sin(az), 0)
            up = 0.55 if level == 0 else 0.25
            cd = norm(add(mul(dd, 0.5), add(mul(out, spread), (0, 0, up))))
            grow(pts[k], cd, length * rng.uniform(0.58, 0.74), radii[k] * 0.70, level + 1)
        if level == levels - 1:
            tips.append(pts[-1])

    grow((0, 0, -0.2), (0.05, 0.02, 1), trunk_len, 0.16 if levels >= 3 else 0.11, 0)
    for tp in tips:
        c = add(tp, (0, 0, 0.12))
        s = card * rng.uniform(0.8, 1.15)
        rot = rng.uniform(0, math.pi)
        for k in range(3):
            a = rot + k * math.pi / 3
            e1 = (math.cos(a), math.sin(a), 0)
            e2 = norm((rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), 1))
            pc.mesh(*quad_card(c, e1, e2, s, s * 0.85), leaf_mat)
        a = rot + 0.4
        pc.mesh(*quad_card(add(c, (0, 0, 0.1)), (math.cos(a), math.sin(a), 0),
                           norm((-math.sin(a), math.cos(a), rng.uniform(-0.25, 0.25))), s, s * 0.9), leaf_mat)
    return pc.col(-0.2, 0.2, -0.2, 0.2, 0, 1.8)


def tree_pieces():
    return [pine_tree("SM_AKX_Pine_A", 601, 5.4, (0.9, -0.35), 8, 2.3),
            pine_tree("SM_AKX_Pine_B", 602, 3.6, (-0.4, 0.2), 5, 1.5),
            maple_tree("SM_AKX_MapleRed_A", 611, 1.7, 3, MRED, card=1.55, spread=0.95),
            maple_tree("SM_AKX_MapleRed_B", 612, 1.1, 2, MRED, card=1.35, spread=0.9),
            maple_tree("SM_AKX_MapleGreen_A", 613, 1.9, 3, MGRN, card=1.6, spread=0.85)]


# --------------------------------------------------------------------------- enclosure

def coping(pc, x0, x1, half, ridge_z, eave_z, t=0.05):
    """A tiled gable coping along X: two slabs from the ridge (y = 0) down to the eaves (y = +-half), a ridge cap."""
    pc.mesh(*slab([(x0, -half, eave_z), (x1, -half, eave_z), (x1, -0.003, ridge_z), (x0, -0.003, ridge_z)], t, ROOF, T, 1.2))
    pc.mesh(*slab([(x1, half, eave_z), (x0, half, eave_z), (x0, 0.003, ridge_z), (x1, 0.003, ridge_z)], t, ROOF, T, 1.2))
    pc.box(x0, x1, -0.055, 0.055, ridge_z - 0.03, ridge_z + 0.07, ROOF, uv="x")


def wall_section(pc, x0, x1):
    pc.box(x0, x1, -0.19, 0.19, -0.05, 0.36, STO, uv="x")
    pc.box(x0, x1, -0.15, 0.15, 0.36, 1.62, WPL, uv="x")
    for z in (1.02, 1.14, 1.26):                       # three fine incised lines (sujibei), dark timber fillets
        pc.box(x0, x1, -0.152, 0.152, z, z + 0.018, T, uv="x")
    pc.box(x0, x1, -0.18, 0.18, 1.62, 1.70, T, uv="x")
    coping(pc, x0, x1, 0.36, 1.98, 1.74)


def enclosure_pieces():
    out = []
    w = Piece("SM_AKX_Wall_4")
    wall_section(w, 0.0, 4.0)
    out.append(w.col(0, 4, -0.19, 0.19, -0.05, 2.05))
    pr = Piece("SM_AKX_WallPier")
    pr.box(-0.26, 0.26, -0.26, 0.26, -0.05, 0.40, STO).box(-0.22, 0.22, -0.22, 0.22, 0.40, 1.80, WPL)
    pr.box(-0.25, 0.25, -0.25, 0.25, 1.80, 1.88, T)
    pr.mesh(*slab([(-0.40, -0.40, 1.90), (0.40, -0.40, 1.90), (0.40, -0.003, 2.12), (-0.40, -0.003, 2.12)], 0.05, ROOF, T, 1.2))
    pr.mesh(*slab([(0.40, 0.40, 1.90), (-0.40, 0.40, 1.90), (-0.40, 0.003, 2.12), (0.40, 0.003, 2.12)], 0.05, ROOF, T, 1.2))
    pr.box(-0.40, 0.40, -0.05, 0.05, 2.09, 2.18, ROOF)
    out.append(pr.col(-0.26, 0.26, -0.26, 0.26, -0.05, 2.18))
    # the roofed gate: local X 0-4 fills the wall gap (world X 4-8); posts leave 2.38 m clear (X 0.81-3.19)
    g = Piece("SM_AKX_Gate")
    wall_section(g, 0.0, 0.55)
    wall_section(g, 3.45, 4.0)
    for x in (0.55, 3.19):
        g.box(x, x + 0.26, -0.13, 0.13, -0.05, 2.78, T)
        g.box(x - 0.01, x + 0.27, -0.14, 0.14, -0.05, 0.16, STO)
    g.box(0.35, 3.65, -0.11, 0.11, 2.32, 2.54, T)                      # tie beam (kabuki)
    g.box(0.50, 3.50, -0.09, 0.09, 2.78, 2.90, T)                      # ridge purlin support
    for x in (0.60, 3.30):                                             # rafters' end blocks
        g.box(x, x + 0.10, -0.85, 0.85, 2.72, 2.80, T)
    for sgn in (-1, 1):                                                # the gate roof: gable along X
        a, b = (-0.25, 4.25) if sgn < 0 else (4.25, -0.25)
        g.mesh(*slab([(a, sgn * 1.05, 2.76), (b, sgn * 1.05, 2.76), (b, sgn * 0.003, 3.30), (a, sgn * 0.003, 3.30)], 0.08, ROOF, T, 1.2))
    g.box(-0.30, 4.30, -0.07, 0.07, 3.26, 3.40, ROOF, uv="x")
    for x in (-0.30, 4.30):                                            # ridge-end tiles
        g.box(x - 0.06, x + 0.06, -0.10, 0.10, 3.24, 3.46, ROOF)
    g.col(0, 0.55, -0.19, 0.19, -0.05, 2.05).col(3.45, 4.0, -0.19, 0.19, -0.05, 2.05)
    g.col(0.54, 0.82, -0.14, 0.14, -0.05, 2.78).col(3.18, 3.46, -0.14, 0.14, -0.05, 2.78)
    g.col(-0.30, 4.30, -1.05, 1.05, 2.54, 3.46)
    out.append(g)
    return out


# --------------------------------------------------------------------------- building exterior

def roof_piece():
    """The hipped tile roof over the 12.6 x 16.6 m hall: eaves 1.0 m beyond the outer wall faces (X -1.3..13.3,
    Y -1.3..17.3), 26 degree pitch, top of the eave edge +4.70, slab 0.18 m, so the underside passes over the wall top
    (+5.00) at the outer face. f2 sun (18 deg up, heading 35 deg): the soffit edge (+4.52) shades the outer wall face
    down to +4.12, 2.3 cm above the clear window heads (+4.10), so the whole west opening takes the sun."""
    x0, x1, y0, y1 = -0.30 - ROOF_EAVE, 12.30 + ROOF_EAVE, -0.30 - ROOF_EAVE, 16.30 + ROOF_EAVE
    half = (x1 - x0) / 2
    xr = (x0 + x1) / 2
    zr = ROOF_EAVE_Z + half * math.tan(math.radians(ROOF_PITCH))
    ya, yb = y0 + half, y1 - half
    ze = ROOF_EAVE_Z
    tv = [(x0, y0, ze), (x1, y0, ze), (x1, y1, ze), (x0, y1, ze), (xr, ya, zr), (xr, yb, zr)]   # SW SE NE NW R0 R1
    bv = [(x, y, z - ROOF_T) for x, y, z in tv]
    verts = tv + bv
    SW, SE, NE, NW, R0, R1 = range(6)
    top = [(SW, R0, R1, NW), (SE, NE, R1, R0), (SW, SE, R0), (NE, NW, R1)]
    eave_dir = {0: (0, -1, 0), 1: (0, 1, 0), 2: (1, 0, 0), 3: (-1, 0, 0)}   # U along the eave of each face
    faces, uvs, mats = [], [], []
    tile = 1.2
    for k, f in enumerate(top):
        u = eave_dir[k]
        p0, p1, p2 = verts[f[0]], verts[f[1]], verts[f[2]]
        nrm = norm(cross(sub(p1, p0), sub(p2, p0)))
        vdir = cross(nrm, u)
        faces.append(f)
        uvs.append([(dot(verts[i], u) / tile, dot(verts[i], vdir) / tile) for i in f])
        mats.append(ROOF)
        fb = tuple(6 + i for i in reversed(f))
        faces.append(fb)
        uvs.append([(verts[i][0] / 2.0, verts[i][1] / 2.0) for i in fb])
        mats.append(T)
    for i, j in ((SW, SE), (SE, NE), (NE, NW), (NW, SW)):          # fascia
        faces.append((6 + i, 6 + j, j, i))
        L = dist(verts[i], verts[j])
        uvs.append([(0, 0), (L / 2, 0), (L / 2, ROOF_T / 2), (0, ROOF_T / 2)])
        mats.append(T)
    rf = Piece("SM_AKX_Roof")
    rf.mesh(verts, faces, uvs, mats)
    # ridge and hip caps (tile-clad beams sitting on the roof planes), ridge-end blocks
    rf.mesh(*beam((xr, ya - 0.25, zr - 0.02), (xr, yb + 0.25, zr - 0.02), 0.30, 0.26, ROOF))
    for (cx, cy) in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        top_pt = (xr, ya if cy < 0 else yb, zr - 0.05)
        rf.mesh(*beam((cx + (0.12 if cx < xr else -0.12), cy + (0.12 if cy < 8 else -0.12), ze - 0.04), top_pt,
                      0.22, 0.18, ROOF))
    for y in (ya - 0.35, yb + 0.35):
        rf.box(xr - 0.20, xr + 0.20, y - 0.10, y + 0.10, zr - 0.05, zr + 0.42, ROOF)
    return rf.col(x0, x1, y0, y1, ze - ROOF_T, zr + 0.42)


def foundation_pieces():
    out = []
    for name, L in (("SM_AKX_Foundation_2", 2.0), ("SM_AKX_Foundation_1", 1.0), ("SM_AKX_Foundation_07", 0.7)):
        f = Piece(name).box(0, L, -0.46, -0.30, -0.05, 0.40, STO, uv="x").box(0, L, -0.48, -0.30, 0.40, 0.46, STO, uv="x")
        out.append(f.col(0, L, -0.48, -0.30, -0.05, 0.46))
    c = Piece("SM_AKX_Foundation_Corner").box(-0.46, 0.0, -0.46, 0.0, -0.05, 0.40, STO)
    c.box(-0.48, 0.0, -0.48, 0.0, 0.40, 0.46, STO)
    out.append(c.col(-0.48, 0, -0.48, 0, -0.05, 0.46))
    return out


def facade_pieces():
    """The hall's outer skin (wall-local frame: length along +X, outer face at y = -0.30, facing -Y): dark timber posts
    every 2 m on the foundation band, a base rail, a rail under a light plaster band below the eaves, a top beam. The
    side-wall variant frames each lattice window (rails under and over it, jambs) and keeps the plaster above."""
    out = []
    for name, L in (("SM_AKX_Facade_2", 2.0), ("SM_AKX_Facade_1", 1.0)):
        f = Piece(name)
        f.box(0.0, 0.18, -0.36, -0.30, 0.46, 4.85, T)
        f.box(0.18, L, -0.34, -0.30, 0.46, 0.56, T, uv="x")
        f.box(0.18, L, -0.35, -0.30, 3.45, 3.60, T, uv="x")
        f.box(0.18, L, -0.31, -0.30, 3.60, 4.85, WPL, uv="x")
        f.box(0.0, L, -0.37, -0.30, 4.85, 5.0, T, uv="x")
        out.append(f.col(0, L, -0.37, -0.30, 0.46, 5.0))
    s = Piece("SM_AKX_Facade_Side_2")
    s.box(0.0, 0.18, -0.36, -0.30, 0.46, 4.85, T)
    s.box(0.18, 2.0, -0.34, -0.30, 0.46, 0.56, T, uv="x")
    zh = 2.5 + G["WIN_HEAD"] + 0.031                                   # f1: the kit's window head (+4.13 rough opening)
    s.box(0.18, 2.0, -0.35, -0.30, 2.52, 2.60, T, uv="x")             # under the window (opening +2.62..+4.13)
    s.box(0.18, 2.0, -0.35, -0.30, zh + 0.02, zh + 0.12, T, uv="x")   # over it
    s.box(0.16, 0.215, -0.35, -0.30, 2.60, zh + 0.02, T).box(1.785, 1.84, -0.35, -0.30, 2.60, zh + 0.02, T)   # jambs
    s.box(0.18, 2.0, -0.31, -0.30, zh + 0.12, 4.85, WPL, uv="x")
    s.box(0.0, 2.0, -0.37, -0.30, 4.85, 5.0, T, uv="x")
    out.append(s.col(0, 2.0, -0.37, -0.30, 0.46, 2.60).col(0, 2.0, -0.37, -0.30, zh, 5.0))
    e = Piece("SM_AKX_Facade_Entrance_6")          # the outer skin round the entrance opening (world X 3-9)
    # f1: the entrance is 3.65 m tall (kit ENTRY_H), so the rail rides on the lintel top (+4.05) instead of +3.45, where
    # it would hang 20 cm into the raised opening
    zr = G["ENTRY_H"] + 0.40
    # layout 2: the kit's heavy posts moved inside to the outer ends of the entrance frame (SM_AK_Entrance_12 is a
    # closed wall X 0-12 round the X 4-8 opening), so the street side gets its own dark timber door casing here: two
    # 30 cm jambs (world X 3.7-4.0 / 8.0-8.3, where the old posts stood) and a head beam up to the rail
    e.box(0.70, 1.00, -0.42, -0.30, 0.0, G["ENTRY_H"], T).box(5.00, 5.30, -0.42, -0.30, 0.0, G["ENTRY_H"], T)
    e.box(0.70, 5.30, -0.42, -0.30, G["ENTRY_H"], zr, T, uv="x")
    e.col(0.70, 1.00, -0.42, -0.30, 0.0, G["ENTRY_H"]).col(5.00, 5.30, -0.42, -0.30, 0.0, G["ENTRY_H"])
    e.col(0.70, 5.30, -0.42, -0.30, G["ENTRY_H"], zr)
    e.box(0.0, 0.18, -0.36, -0.30, 0.46, 4.85, T)
    e.box(0.18, 0.70, -0.34, -0.30, 0.46, 0.56, T).box(5.30, 6.0, -0.34, -0.30, 0.46, 0.56, T)
    e.box(0.18, 0.70, -0.35, -0.30, 3.45, 3.60, T, uv="x").box(5.30, 6.0, -0.35, -0.30, 3.45, 3.60, T, uv="x")
    e.box(0.18, 0.70, -0.31, -0.30, 3.60, zr, WPL, uv="x").box(5.30, 6.0, -0.31, -0.30, 3.60, zr, WPL, uv="x")
    e.box(0.18, 6.0, -0.35, -0.30, zr, zr + 0.15, T, uv="x")
    e.box(0.18, 6.0, -0.31, -0.30, zr + 0.15, 4.85, WPL, uv="x")
    e.box(0.0, 6.0, -0.37, -0.30, 4.85, 5.0, T, uv="x")
    out.append(e.col(0, 0.7, -0.37, -0.30, 0.46, 5.0).col(5.3, 6.0, -0.37, -0.30, 0.46, 5.0)
               .col(0.7, 5.3, -0.37, -0.30, zr, 5.0))
    c = Piece("SM_AKX_FacadeCorner").box(-0.37, 0.0, -0.37, 0.0, 0.46, 5.0, T)
    out.append(c.col(-0.37, 0.0, -0.37, 0.0, 0.46, 5.0))
    return out


# --------------------------------------------------------------------------- scenery

def scenery_pieces():
    out = []
    for name, W, H, mat in (("SM_AKX_TreeLine_24", 24.0, 14.0, "M_AKX_TreeLine"),
                            ("SM_AKX_TreeLineFar_48", 48.0, 20.0, "M_AKX_TreeLineFar")):
        pc = Piece(name)
        pc.mesh(*G["card"](0, W, -0.5, H, cx=W / 2), mat)   # faces -Y, U along +X
        out.append(pc.col(0, W, -0.05, 0.05, 0, 2.0))
    for name, R, lo, hi, seed, mat in (("SM_AKX_Hills_Ring", 170.0, 10.0, 34.0, 701, "M_AKX_Hills"),
                                       ("SM_AKX_Mountains_Ring", 720.0, 70.0, 250.0, 702, "M_AKX_Mountains")):
        rng = random.Random(seed)
        waves = [(rng.randint(2, 9), rng.uniform(0, 6.28), rng.uniform(0.3, 1.0)) for _ in range(7)]
        waves += [(rng.randint(12, 40), rng.uniform(0, 6.28), rng.uniform(0.05, 0.18)) for _ in range(6)]
        tot = sum(a for _, _, a in waves)
        N = 256 if R > 500 else 192
        hs = []
        for i in range(N):
            th = 2 * math.pi * i / N
            s = sum(a * math.sin(k * th + ph) for k, ph, a in waves) / tot           # -1..1-ish
            ridge = abs(math.sin(3 * th + 0.7)) ** 0.5 * 0.0 + s
            hs.append(lo + (hi - lo) * max(0.0, min(1.0, 0.5 + 0.9 * ridge)))
        verts = []
        for i in range(N):
            th = 2 * math.pi * i / N
            verts.append((R * math.cos(th), R * math.sin(th), -3.0))
            verts.append((R * math.cos(th), R * math.sin(th), hs[i]))
        faces, uvs = [], []
        for i in range(N):
            j = (i + 1) % N
            faces.append((2 * j, 2 * i, 2 * i + 1, 2 * j + 1))      # winding faces the centre
            uvs.append([((i + 1) / N, 0.0), (i / N, 0.0), (i / N, 1.0), ((i + 1) / N, 1.0)])
        pc = Piece(name).mesh(verts, faces, uvs, mat)
        out.append(pc.col(R - 1.0, R, -0.5, 0.5, 0, 5.0))
    return out


def kit():
    return (ground_pieces() + tree_pieces() + enclosure_pieces() + [roof_piece()] + foundation_pieces()
            + facade_pieces() + scenery_pieces())


# --------------------------------------------------------------------------- placement

def layout(add, room_w, room_l):
    X0, X1, Y0, Y1 = COURT
    cx = 6.0                                              # the entrance axis
    add("SM_AKX_Ground_Field", -194.0, -192.0)
    add("SM_AKX_Court_Gravel", X0, Y0)
    add("SM_AKX_Landing", 3.7, -1.82)
    add("SM_AKX_PathSlab", cx - 0.6, -4.90)                # Y -4.90..-1.90, just short of the landing
    # stepping stones from the ishidatami to the gate: a gentle S, 0.62 m stride
    stones = "ABCBACBCABC"
    for k in range(11):
        y = -5.45 - 0.66 * k
        x = cx + 0.30 * math.sin(k * 0.9 + 0.4)
        add(f"SM_AKX_StepStone_{stones[k]}", round(x, 3), round(y, 3), 0.0, (k * 37) % 180)
    # garden
    add("SM_AKX_MossMound_A", 1.9, -9.6, 0.0, 15)
    add("SM_AKX_RakeRing_A", 1.9, -9.6, 0.0, 15)
    add("SM_AKX_MossMound_B", 11.4, -9.9, 0.0, -20)
    add("SM_AKX_RakeRing_B", 11.4, -9.9, 0.0, -20)
    add("SM_AKX_Rock_A", 2.55, -9.95, 0.0, 30)
    add("SM_AKX_Rock_B", 11.9, -9.6, 0.0, 110)
    add("SM_AKX_Rock_C", 1.35, -9.35, 0.0, 200)
    add("SM_AKX_Rock_B", 13.6, -4.6, 0.0, 250)
    add("SM_AKX_StoneLantern", 8.35, -7.3, 0.0, 20)
    add("SM_AKX_Tsukubai", 3.35, -5.9, 0.0, 70)      # front stone toward the path
    for (x, y, k, r) in ((1.0, -1.25, "A", 0), (2.45, -1.10, "B", 40), (11.0, -1.25, "A", 90), (9.55, -1.10, "B", 10),
                         (-2.9, -11.9, "A", 30), (14.9, -11.8, "A", 60), (-2.8, -4.2, "B", 0), (14.8, -6.6, "B", 20),
                         (9.0, -12.2, "B", 70), (3.0, -12.2, "B", 150)):
        add(f"SM_AKX_Shrub_{k}", x, y, 0.0, r)
    # trees (3 near the building front, 2 by the walls)
    add("SM_AKX_Pine_A", 1.2, -3.6, 0.0, 0)
    add("SM_AKX_MapleRed_A", 11.9, -6.4, 0.0, 0)
    add("SM_AKX_MapleGreen_A", -1.9, -8.2, 0.0, 70)
    add("SM_AKX_MapleRed_B", 13.8, -11.0, 0.0, 200)
    # f1 (measurer: at (9.9, -11.3) its branches crossed the south wall): turned 90 deg and moved to (9.5, -10.16), off
    # the raked ring of mound B. Canopy bbox (layout.json) Y -12.55..-8.65: 9 cm inside the wall face (-12.64) and 8 cm
    # short of the red maple's crown (-8.57)
    add("SM_AKX_Pine_B", 9.5, -10.16, 0.0, 90)
    # enclosure: south wall with the gate on the axis, side walls up to Y +3
    for x in (X0, X0 + 4.0):
        add("SM_AKX_Wall_4", x, Y0)
    add("SM_AKX_Gate", cx - 2.0, Y0)
    for x in (cx + 2.0, cx + 6.0):
        add("SM_AKX_Wall_4", x, Y0)
    for y in (Y0, Y0 + 4.0, Y0 + 8.0, Y0 + 12.0):
        add("SM_AKX_Wall_4", X0, y, 0.0, 90)
        add("SM_AKX_Wall_4", X1, y, 0.0, 90)
    for (x, y) in ((X0, Y0), (X1, Y0), (X0, Y0 + 16.0), (X1, Y0 + 16.0)):
        add("SM_AKX_WallPier", x, y)
    # the building: roof and stone foundation band (south wall stops at the entrance casing X 3.7 / 8.3)
    add("SM_AKX_Roof", 0.0, 0.0)
    for x0, p in ((0.0, "2"), (2.0, "1"), (3.0, "07"), (8.3, "07"), (9.0, "1"), (10.0, "2")):
        add(f"SM_AKX_Foundation_{p}", x0, 0.0)
    for x0 in range(0, int(room_w), 2):
        add("SM_AKX_Foundation_2", x0 + 2, room_l, 0.0, 180)
    for y0 in range(0, int(room_l), 2):
        add("SM_AKX_Foundation_2", 0.0, y0 + 2, 0.0, -90)
        add("SM_AKX_Foundation_2", room_w, y0, 0.0, 90)
    for (x, y, r) in ((0, 0, 0), (room_w, 0, 90), (room_w, room_l, 180), (0, room_l, -90)):
        add("SM_AKX_Foundation_Corner", x, y, 0.0, r)
        add("SM_AKX_FacadeCorner", x, y, 0.0, r)
    # the outer skin: timber frame and plaster band (south: plain X 0-3 / 9-12, the entrance casing piece X 3-9; the
    # kit wall behind it is SM_AK_Entrance_12, X 0-12, closed except the X 4-8 opening)
    for x0, p in ((0.0, "2"), (2.0, "1"), (9.0, "1"), (10.0, "2")):
        add(f"SM_AKX_Facade_{p}", x0, 0.0)
    add("SM_AKX_Facade_Entrance_6", 3.0, 0.0)
    for x0 in range(0, int(room_w), 2):
        add("SM_AKX_Facade_2", x0 + 2, room_l, 0.0, 180)
    for y0 in range(0, int(room_l), 2):
        add("SM_AKX_Facade_Side_2", 0.0, y0 + 2, 0.0, -90)
        add("SM_AKX_Facade_Side_2", room_w, y0, 0.0, 90)
    # scenery: two tree-line layers west, east and north; the far layer only to the south-west and south-east, so the
    # gate opens on the meadow, the hills and the mountains
    for y in (-14.0, 10.0):
        add("SM_AKX_TreeLine_24", -10.0, y, 0.0, 90)          # west, faces +X
    for y in (34.0, 10.0):
        add("SM_AKX_TreeLine_24", room_w + 10.0, y, 0.0, -90)  # east, faces -X
    for x in (-14.0, 10.0):
        add("SM_AKX_TreeLine_24", x, room_l + 10.0, 0.0, 0)    # north, faces -Y
    for y in (-40.0, 8.0):
        add("SM_AKX_TreeLineFar_48", -30.0, y, 0.0, 90)
    for y in (56.0, 8.0):
        add("SM_AKX_TreeLineFar_48", room_w + 30.0, y, 0.0, -90)
    for x in (-40.0, 8.0):
        add("SM_AKX_TreeLineFar_48", x, room_l + 30.0, 0.0, 0)
    add("SM_AKX_TreeLineFar_48", -8.0, -48.0, 0.0, 180)       # south-west, faces +Y (X -56..-8)
    add("SM_AKX_TreeLineFar_48", 68.0, -48.0, 0.0, 180)       # south-east (X 20..68)
    add("SM_AKX_Hills_Ring", cx, 4.0, 0.0, 0)
    add("SM_AKX_Mountains_Ring", cx, 4.0, 0.0, 0)
