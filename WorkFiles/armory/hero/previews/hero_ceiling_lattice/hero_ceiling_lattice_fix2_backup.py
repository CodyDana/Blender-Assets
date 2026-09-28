"""Hero ornamental ceiling lattice (user, 2026-09-27: hero pieces that match the per-piece reference sheets "to the T").

References (WorkFiles/armory/reference): ceiling_lattice.png (the design: views from below, side, 3/4 from below),
armory3_reference2.png (the lattice panels over the centre aisle and the platform).

Replaces SM_AK_Ceiling_Lattice_2x2 (build_armory_kit.kit(), coffer_ring()): pivot at the cell corner, the cell X 0-2,
Y 0-2, the ceiling line at local z 0 (layout() places it at CEIL), collision col(0, 2, 0, 2, -0.06, 0.20) unchanged.
layout() puts six of them in the coffer grid (LATTICE_COFFERS) among the plain coffers: the Ceiling_Beam_4 lines (25 cm,
40 cm deep) cover local Y 0-0.125 / 1.875-2, the Ceiling_Rib_2 lines (16 cm, 30 cm deep) cover X 0-0.08 / 1.92-2, the
hero joint blocks (hero_banner_coffer) wrap the crossings. The piece brings no beams of its own.

Fix round 1 (blind judge): the frame is the full 2 x 2 m panel of the sheet (corner stacks to the cell edge), built
of two stacked rail tiers (19 cm deep, most of it above the ceiling line so the in-grid silhouette stays that of a
recessed coffer) with the glowing LED slot between the tiers on the outer faces, log-cabin corner stacks (five tiers
alternately projecting in X and Y, a 2 x 2 end-block cap split by a cross groove underneath), no plain slab showing.

Fix round 2 (blind judge): the outer LED is a recessed channel (56 mm, emitter at the back, shadowed above it, under
a projecting lip over a lower shelf); the inner LED hides in a pocket behind the step lip, so from below the reveal
shows one amber-gold wash; the backing sits just over the (now 13 x 9 mm, chamfered, copper-edged) kumiko and is
faceted in three honey tones per cell (a shallow paper pyramid look); the corner stacks cross a post with rail ends
projecting 17 mm / set back 24 mm, over a 2 x 2 cap of equal bevelled end blocks with an 8 x 16 mm cross groove;
the timber UVs compress across the grain (GU) so T_AK_Timber's streaks read as brushed grain.

Design, measured off the sheet's view from below (d = in from the cell edge; the sheet: corner blocks 0-0.121, rail
0.026-0.129, groove, step 0.138-0.157, lit reveal 0.157-0.188 with the LED at its inner side, inner rail 0.19-0.225,
lattice 1.55 m square):
  corner stacks  d 0-0.132, tiers of dark timber with worn (reddish) chamfers, 2 x 2 end blocks at the bottom
  outer rail     d 0.030-0.130, underside z -0.060, chamfered; outer faces: upper tier, LED slot, lower tier
  groove + step  d 0.130-0.158, step 15 mm above the rail underside
  reveal         d 0.158-0.188, up to z -0.004: a warm wash on its walls and head, the LED line (M_AK_LEDLine) at the
                 inner side of the head, small square blocks over the slot ends at the inner corners
  inner rail     d 0.188-0.225, underside z -0.050
  lattice        asanoha kumiko as geometry: 8 column intervals x 5 row periods (the sheet), 13 x 13 mm dark strips
                 (triangle grid + three spokes per star), a domed dark-bronze boss on each of the 32 full stars, in
                 front of the backlit amber panel (M_AK_HLatticeGlow). The six strip families sit 1.5 mm apart in depth,
                 so crossing strips never share a plane.
Timber UVs: the grain of T_AK_Timber runs along V, so V runs along every member.
ENABLED stays False: the user reviews images before anything goes in.
"""
import math

ENABLED = False          # the user reviews images of every piece BEFORE anything goes into the armory; never set True

GB, GD = "M_AK_HLatticeGlowHi", "M_AK_HLatticeGlowLo"
GL, WA, ED, LE = "M_AK_HLatticeGlow", "M_AK_HLatticeWash", "M_AK_HTimberEdge", "M_AK_HLatticeLED"
MATERIALS = {
    # the backlit panel behind the kumiko: saturated honey amber (the kit's M_AK_GoldGlow read pale peach here and it
    # also lights the rear alcove screens, so the lattice gets its own). Fix 2: the backing is faceted in three
    # tones of it (the kit's M_AK_LanternPaper glow picture was tried: at its fixed 0.4 emission
    # the cells rendered a third too dark or, sampled nearer its core, grey-cream)
    GL: (None, 1.0, {"color": "#C88A10", "emit": 0.9, "emit_color": "#FFA600"}),
    # fix 2: the faceted glow, two more tones of the same honey: light gold facets and deep amber facets
    GB: (None, 1.0, {"color": "#D89A30", "emit": 1.08, "emit_color": "#FFB030"}),
    GD: (None, 1.0, {"color": "#B0700C", "emit": 0.7, "emit_color": "#FF9C00"}),
    # the reveal surfaces lit by the hidden LED line: one amber-gold wash (fix 2: the pale-peach LEDLine next to a
    # saturated orange wash read two-tone; the hidden emitter's own light makes the gradient toward the step)
    WA: (None, 1.0, {"color": "#8A6128", "emit": 0.62, "emit_color": "#FFAE38"}),
    # the LED emitters (outer channel back, the hidden inner pocket): amber-gold, not peach
    LE: (None, 1.0, {"color": "#FFB23A", "emit": 1.15, "emit_color": "#FFA82A"}),
    # worn edges of the dark-stained timber: the sheet's warm copper-bronze edge wear on the chamfers and arrises
    ED: (None, 1.0, {"color": "#5E3822", "rough": 0.45, "metal": 0.3}),
}

T, BZ = "M_AK_Timber", "M_AK_Bronze"
TILE = 2.0               # M_AK_Timber tiles every 2 m
GU = 20.0                # across-grain UV compression: the broad streaks of T_AK_Timber read as brushed grain on rails

# frame profile (d in from the cell edge, z up from the ceiling line, material of the segment to the next point).
# Fix 2: the outer LED is a real recessed channel (56 mm tall, 48 mm deep) under a projecting upper tier, the
# emitter at its back, over a lower rail shelf; the inner LED hides in a pocket behind the step lip, so from below
# only its amber wash shows on the reveal head (brightest at the step side, as the sheet)
PROFILE = [
    (0.030, 0.130, T),    # outer face, upper tier
    (0.030, 0.068, ED),   # lip arris
    (0.034, 0.064, T),    # LED channel: underside of the lip (lit by the emitter, shadowed toward the back)
    (0.078, 0.064, T),    # channel back, dark above the emitter
    (0.078, 0.048, LE),   # the emitter strip, low at the back
    (0.078, 0.016, WA),   # channel back, washed below the emitter
    (0.078, 0.008, WA),   # channel floor (the lower shelf's top)
    (0.037, 0.008, ED),   # shelf arris
    (0.034, 0.005, T),    # outer face, lower tier (set back 4 mm)
    (0.034, -0.052, ED),
    (0.042, -0.060, T),   # rail underside
    (0.122, -0.060, ED),
    (0.130, -0.052, T),   # rail inner face
    (0.130, -0.032, T),   # groove head
    (0.138, -0.032, T),   # step outer face
    (0.138, -0.041, ED),
    (0.142, -0.045, T),   # step underside
    (0.154, -0.045, WA),  # lit chamfer
    (0.158, -0.041, WA),  # reveal wall (step side), up to the pocket lip
    (0.158, -0.014, WA),  # pocket floor (top of the step lip)
    (0.146, -0.014, LE),  # the hidden inner LED (faces the reveal, not seen from below)
    (0.146, 0.004, WA),   # reveal head, lit by the hidden LED (the part over the lip stays hidden)
    (0.188, 0.004, WA),   # reveal wall (inner rail side)
    (0.188, -0.046, ED),
    (0.192, -0.050, T),   # inner rail underside
    (0.221, -0.050, ED),
    (0.225, -0.046, T),   # inner rail inner face, up to the glow panel
    (0.225, -0.003, None),   # 1 mm past the backing (no shared vertices with it)
]
TOP_Z = 0.130
GLOW_Z = -0.004           # the backing sits 1 mm over the highest kumiko family (fix 2: closer, the cells glow through)
POCKET = 0.225            # lattice opening, d 0.225 .. 1.775
CH = 0.005                # chamfer on the corner stack blocks

# corner stacks (fix 2): a post (d POST) and rail-end tiers that cross it, alternately projecting 17 mm past the post
# in X and in Y and set back 24 mm behind it in the other axis (stepped, notched side view); the top tier is a cap
# projecting both ways; under the post a 2 x 2 cap of equal end blocks split by a deep cross groove
POST = (0.020, 0.124, -0.060, 0.184)
TIERS = [(-0.063, -0.022, "x"), (-0.018, 0.020, "y"), (0.024, 0.070, "x"), (0.074, 0.126, "y"), (0.132, 0.186, "xy")]
TIER_OUT, TIER_IN, TIER_END = 0.003, 0.044, 0.132
END_Z = (-0.079, -0.061)               # the 2 x 2 end blocks under each stack (18 mm, the groove as deep)
END_G = 0.008                          # cross groove width
N_COL, N_ROW = 8, 5                    # asanoha: column intervals across, row periods along (sheet count)
STRIP_W, STRIP_D, STRIP_Z, STRIP_CH = 0.013, 0.009, -0.020, 0.002
FAM_DZ = 0.0012


# --------------------------------------------------------------------------- mesh accumulator

class Acc:
    def __init__(self):
        self.v, self.f, self.uv, self.m = [], [], [], []

    def add(self, pts):
        i = len(self.v)
        self.v.extend(pts)
        return list(range(i, i + len(pts)))

    def face(self, idx, uvs, mat, out_dir):
        """Append a face, winding it so its normal points along out_dir."""
        p = [self.v[i] for i in idx]
        n = [0.0, 0.0, 0.0]
        for k in range(len(p)):
            a, b = p[k], p[(k + 1) % len(p)]
            n[0] += (a[1] - b[1]) * (a[2] + b[2])
            n[1] += (a[2] - b[2]) * (a[0] + b[0])
            n[2] += (a[0] - b[0]) * (a[1] + b[1])
        if n[0] * out_dir[0] + n[1] * out_dir[1] + n[2] * out_dir[2] < 0:
            idx, uvs = list(reversed(idx)), list(reversed(uvs))
        self.f.append(list(idx))
        self.uv.append(list(uvs))
        self.m.append(mat)

    def emit(self, piece):
        if self.f:
            piece.mesh(self.v, self.f, self.uv, self.m, smooth=False)


def bar(acc, p0, p1, section, mat, uoff=0.0, caps=True):
    """A straight member along p0 -> p1 (XY points), open cross-section [(s, z)] (top open, it sits against something).
    V runs along the member (the timber grain), U round the section. mat: one material or one per section segment;
    caps=False leaves the ends open (ends buried in the rail or inside a kumiko joint)."""
    mats = mat if isinstance(mat, (list, tuple)) else [mat] * (len(section) - 1)
    ax, ay = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(ax, ay)
    ax, ay = ax / L, ay / L
    nx, ny = -ay, ax
    sc = sum(s for s, _ in section) / len(section)
    zc = sum(z for _, z in section) / len(section)

    def ring(p):
        return acc.add([(p[0] + nx * s, p[1] + ny * s, z) for s, z in section])
    r0, r1 = ring(p0), ring(p1)
    per = [0.0]
    for k in range(1, len(section)):
        per.append(per[-1] + math.dist(section[k - 1], section[k]))
    v0, v1 = uoff / TILE, (uoff + L) / TILE
    for k in range(len(section) - 1):
        sm, zm = (section[k][0] + section[k + 1][0]) / 2 - sc, (section[k][1] + section[k + 1][1]) / 2 - zc
        u0, u1 = per[k] * GU / TILE + 0.21, per[k + 1] * GU / TILE + 0.21
        acc.face([r0[k], r1[k], r1[k + 1], r0[k + 1]], [(u0, v0), (u0, v1), (u1, v1), (u1, v0)], mats[k],
                 (nx * sm, ny * sm, zm))
    for r, d in (((r0, (-ax, -ay, 0.0)), (r1, (ax, ay, 0.0))) if caps else ()):
        uvs = [((s - sc) / TILE + 0.3, (z - zc) / TILE + 0.3) for s, z in section]
        for k in range(1, len(section) - 1):   # fan: sections are convex
            acc.face([r[0], r[k], r[k + 1]], [uvs[0], uvs[k], uvs[k + 1]], mats[0], d)


def cbox(acc, x0, x1, y0, y1, z0, z1, ch=CH, mat=T, emat=ED, along_x=True):
    """A closed block with its four long edges chamfered (worn-edge material), flat ends. Along X or along Y."""
    if along_x:
        a0, a1, b0, b1 = x0, x1, y0, y1
    else:
        a0, a1, b0, b1 = y0, y1, x0, x1
    sec = [(b0 + ch, z0), (b1 - ch, z0), (b1, z0 + ch), (b1, z1 - ch), (b1 - ch, z1), (b0 + ch, z1), (b0, z1 - ch),
           (b0, z0 + ch)]
    mats = [mat, emat, mat, emat, mat, emat, mat, emat]
    bc, zc = (b0 + b1) / 2, (z0 + z1) / 2

    def P(a, b, z):
        return (a, b, z) if along_x else (b, a, z)
    r0 = acc.add([P(a0, b, z) for b, z in sec])
    r1 = acc.add([P(a1, b, z) for b, z in sec])
    per = [0.0]
    for k in range(8):
        per.append(per[-1] + math.dist(sec[k], sec[(k + 1) % 8]))
    uo = (a0 * 3.7 + b0 * 1.3) % 1.0
    for k in range(8):
        j = (k + 1) % 8
        bm, zm = (sec[k][0] + sec[j][0]) / 2 - bc, (sec[k][1] + sec[j][1]) / 2 - zc
        u0, u1 = per[k] * GU / TILE + uo, per[k + 1] * GU / TILE + uo
        v0, v1 = a0 / TILE, a1 / TILE
        acc.face([r0[k], r1[k], r1[j], r0[j]], [(u0, v0), (u0, v1), (u1, v1), (u1, v0)], mats[k], P(0.0, bm, zm))
    for r, s in ((r0, -1.0), (r1, 1.0)):
        uvs = [((b - bc) / TILE + uo, (z - zc) / TILE + 0.5) for b, z in sec]
        for k in range(1, 7):
            acc.face([r[0], r[k], r[k + 1]], [uvs[0], uvs[k], uvs[k + 1]], mat, P(s, 0.0, 0.0))


# --------------------------------------------------------------------------- frame

def frame(acc):
    """The rail profile swept round the square with mitred corners (the mitres sit inside the corner stacks) and the
    top plate closing the frame; the glowing backing (diffuser()) closes the lattice pocket."""
    rings = []
    for d, z, _ in PROFILE:
        rings.append(acc.add([(d, d, z), (2 - d, d, z), (2 - d, 2 - d, z), (d, 2 - d, z)]))
    inward = [(0, 1, 0), (-1, 0, 0), (0, -1, 0), (1, 0, 0)]
    per = [0.0]
    for k in range(1, len(PROFILE)):
        per.append(per[-1] + math.dist(PROFILE[k - 1][:2], PROFILE[k][:2]))
    for k in range(len(PROFILE) - 1):
        (d0, z0, mat), (d1, z1, _) = PROFILE[k], PROFILE[k + 1]
        nd, nz = z1 - z0, -(d1 - d0)
        for s in range(4):
            a, b = s, (s + 1) % 4
            idx = [rings[k][a], rings[k][b], rings[k + 1][b], rings[k + 1][a]]
            ax = 0 if s % 2 == 0 else 1          # the coordinate that runs along this side
            uvs = [(per[kk] * GU / TILE + 0.13 * s, acc.v[i][ax] / TILE)
                   for kk, i in ((k, idx[0]), (k, idx[1]), (k + 1, idx[2]), (k + 1, idx[3]))]
            n = inward[s]
            acc.face(idx, uvs, mat, (nd * n[0], nd * n[1], nz))
    top = rings[0]
    acc.face(top, [(acc.v[i][0] / TILE, acc.v[i][1] / TILE) for i in top], T, (0, 0, 1))


def span(a, b, lo):
    """d range [a, b] measured in from the low or the high cell edge -> coordinate range."""
    return (a, b) if lo else (2.0 - b, 2.0 - a)


def end_block(acc, x0, x1, y0, y1, z0, z1, ch=0.004):
    """An end block seen from below: square, all four bottom edges chamfered (worn edge), so the four quadrants of a
    stack's cap read alike whatever their position."""
    top = acc.add([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)])
    mid = acc.add([(x0, y0, z0 + ch), (x1, y0, z0 + ch), (x1, y1, z0 + ch), (x0, y1, z0 + ch)])
    bot = acc.add([(x0 + ch, y0 + ch, z0), (x1 - ch, y0 + ch, z0), (x1 - ch, y1 - ch, z0), (x0 + ch, y1 - ch, z0)])
    out = [(0, -1, 0), (1, 0, 0), (0, 1, 0), (-1, 0, 0)]
    uo = (x0 * 3.1 + y0 * 1.7) % 1.0
    for i in range(4):
        j = (i + 1) % 4
        L = math.dist(acc.v[top[i]][:2], acc.v[top[j]][:2])
        hs = (z1 - z0 - ch) * GU / TILE
        acc.face([mid[i], mid[j], top[j], top[i]], [(uo, 0), (uo, L / TILE), (uo + hs, L / TILE), (uo + hs, 0)], T,
                 out[i])
        o = out[i]
        acc.face([bot[i], bot[j], mid[j], mid[i]], [(uo, 0), (uo, L / TILE), (uo + 0.01, L / TILE), (uo + 0.01, 0)],
                 ED, (o[0], o[1], -1))
    acc.face(bot, [(uo + acc.v[k][0] * GU / TILE, acc.v[k][1] / TILE) for k in bot], T, (0, 0, -1))
    acc.face(top, [(uo + acc.v[k][0] / TILE, acc.v[k][1] / TILE) for k in top], T, (0, 0, 1))


def corner_stacks(acc):
    """Log-cabin stacks: a post crossed by rail-end tiers that alternately project past it in X and in Y (and sit back
    behind it in the other axis), a projecting cap tier on top, and under the post a 2 x 2 cap of equal end blocks
    split by a deep cross groove."""
    for lx in (True, False):
        for ly in (True, False):
            for z0, z1, proj in TIERS:
                xa = TIER_OUT if "x" in proj else TIER_IN
                ya = TIER_OUT if "y" in proj else TIER_IN
                x0, x1 = span(xa, TIER_END, lx)
                y0, y1 = span(ya, TIER_END, ly)
                cbox(acc, x0, x1, y0, y1, z0, z1, along_x=(proj == "x"))
            c0, c1, cz0, cz1 = POST
            x0, x1 = span(c0, c1, lx)
            y0, y1 = span(c0, c1, ly)
            cbox(acc, x0, x1, y0, y1, cz0, cz1, ch=0.002, along_x=False)
            e0, e1 = TIER_OUT, TIER_END
            q = (e1 - e0 - END_G) / 2
            for i in range(2):
                for j in range(2):
                    x0, x1 = span(e0 + i * (q + END_G), e0 + i * (q + END_G) + q, lx)
                    y0, y1 = span(e0 + j * (q + END_G), e0 + j * (q + END_G) + q, ly)
                    end_block(acc, x0, x1, y0, y1, END_Z[0], END_Z[1])


def inner_blocks(acc):
    """Small square blocks at the inner corners, over the ends of the reveal (the sheet's inner corner blocks)."""
    for lx in (True, False):
        for ly in (True, False):
            x0, x1 = span(0.152, 0.214, lx)
            y0, y1 = span(0.152, 0.214, ly)
            cbox(acc, x0, x1, y0, y1, -0.053, -0.002, ch=0.003)


# --------------------------------------------------------------------------- asanoha kumiko

def clip(p0, p1, r):
    """Liang-Barsky: the part of segment p0-p1 inside rect r = (x0, x1, y0, y1), or None."""
    t0, t1 = 0.0, 1.0
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    for p, q in ((-dx, p0[0] - r[0]), (dx, r[1] - p0[0]), (-dy, p0[1] - r[2]), (dy, r[3] - p0[1])):
        if abs(p) < 1e-12:
            if q < 0:
                return None
            continue
        t = q / p
        if p < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
    if t1 - t0 <= 1e-9:
        return None
    return (p0[0] + t0 * dx, p0[1] + t0 * dy), (p0[0] + t1 * dx, p0[1] + t1 * dy)


def asanoha(acc, o0, o1):
    L = o1 - o0
    c, P = L / N_COL, L / N_ROW
    inner = (o0 + 0.002, o1 - 0.002, o0 + 0.002, o1 - 0.002)   # a strip must show inside the opening
    under = (o0 - 0.012, o1 + 0.012, o0 - 0.012, o1 + 0.012)   # ... and runs 12 mm up into the inner rail
    segs = {f: [] for f in range(6)}   # families: 0 vertical, 1 / 2 diagonals, 3 horizontal spokes, 4 / 5 steep spokes

    def pt(k, j):   # column k (x), row j in half periods
        return (o0 + k * c, o0 + j * P / 2)
    for k in range(1, N_COL):
        segs[0].append((pt(k, -2), pt(k, 2 * N_ROW + 2)))
    for m in range(-N_ROW - 2, 2 * N_ROW + 3):
        segs[1].append((pt(-1, 2 * m - 1), pt(N_COL + 1, 2 * m + N_COL + 1)))
        segs[2].append((pt(-1, 2 * m + 1), pt(N_COL + 1, 2 * m - N_COL - 1)))
    stars = []
    ext = STRIP_W * 0.55   # spokes run just past the centroid, so the three meeting there close the joint
    for k in range(-1, N_COL + 2):
        for j in range(-2, 2 * N_ROW + 3):
            if (j + k) % 2:
                continue   # even columns on whole periods, odd columns on half periods
            vx, vy = pt(k, j)
            if o0 + 0.01 < vx < o1 - 0.01 and o0 + 0.01 < vy < o1 - 0.01:
                stars.append((vx, vy))
            for fam, (dx, dy) in ((3, (2 * c / 3, 0.0)), (4, (c / 3, P / 2)), (5, (c / 3, -P / 2))):
                ln = math.hypot(dx, dy)
                ex, ey = dx / ln * ext, dy / ln * ext
                segs[fam].append(((vx - dx - ex, vy - dy - ey), (vx + dx + ex, vy + dy + ey)))
    n = 0
    for fam, lst in segs.items():
        zb = STRIP_Z + fam * FAM_DZ
        w, c2 = STRIP_W / 2, STRIP_CH
        sec = [(w, zb + STRIP_D), (w, zb + c2), (w - c2, zb), (-w + c2, zb), (-w, zb + c2), (-w, zb + STRIP_D)]
        for p0, p1 in lst:
            if not clip(p0, p1, inner):
                continue
            s = clip(p0, p1, under)
            if math.dist(*s) < 0.004:
                continue
            n += 1
            bar(acc, s[0], s[1], sec, [T, ED, T, ED, T], uoff=(n * 0.618) % 1.0 * TILE, caps=False)
    for (x, y) in stars:
        boss(acc, x, y)
    return len(stars)


def clip_poly(poly, r):
    """Sutherland-Hodgman: polygon [(x, y)] clipped to rect r = (x0, x1, y0, y1)."""
    for axis, lim, keep_hi in ((0, r[0], True), (0, r[1], False), (1, r[2], True), (1, r[3], False)):
        out = []
        for k in range(len(poly)):
            a, b = poly[k], poly[(k + 1) % len(poly)]
            ina = a[axis] >= lim if keep_hi else a[axis] <= lim
            inb = b[axis] >= lim if keep_hi else b[axis] <= lim
            if ina:
                out.append(a)
            if ina != inb:
                t = (lim - a[axis]) / (b[axis] - a[axis])
                out.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
        poly = out
        if len(poly) < 3:
            return []
    return poly


def diffuser(acc, o0, o1):
    """The backlit backing, cut along the asanoha lines into its cells (each grid triangle split at its centroid into
    three) and each cell into three facets meeting at the cell's centre, like a shallow paper pyramid lit from one
    side (the sheet's faceted glow): the facet facing the light glows light gold (GB), the one facing away deep amber
    (GD), the rest honey (GL); cells near the rail drop one step (the sheet's brighter core). Facets cut by the rail
    are clipped to the opening."""
    L = o1 - o0
    c, P = L / N_COL, L / N_ROW
    mid = (o0 + o1) / 2
    rect = (o0, o1, o0, o1)
    welded = {}
    lx, ly = -0.60, 0.80                       # in-plane light direction of the faceting
    tones = [GD, GL, GB]

    def vid(x, y):   # one welded vertex per position: the facets form one continuous sheet
        key = (round(x, 5), round(y, 5))
        if key not in welded:
            welded[key] = acc.add([(x, y, GLOW_Z)])[0]
        return welded[key]

    def pt(k, j):
        return (o0 + k * c, o0 + j * P / 2)
    n = 0
    for k in range(N_COL):
        for j in range(-4, 2 * N_ROW + 3):
            if (j + k) % 2:
                continue
            for tri in ((pt(k, j), pt(k, j + 2), pt(k + 1, j + 1)), (pt(k + 1, j + 1), pt(k + 1, j + 3), pt(k, j + 2))):
                g = (sum(p[0] for p in tri) / 3, sum(p[1] for p in tri) / 3)
                for e in range(3):
                    cell = [tri[e], tri[(e + 1) % 3], g]
                    cc = (sum(p[0] for p in cell) / 3, sum(p[1] for p in cell) / 3)
                    rim = max(abs(cc[0] - mid), abs(cc[1] - mid)) > L * 0.40
                    for q0 in range(3):
                        E0, E1 = cell[q0], cell[(q0 + 1) % 3]
                        mx, my = (E0[0] + E1[0]) / 2 - cc[0], (E0[1] + E1[1]) / 2 - cc[1]
                        dl = (mx * lx + my * ly) / math.hypot(mx, my)
                        tone = 2 if dl > 0.35 else (0 if dl < -0.35 else 1)
                        if rim:
                            tone = max(0, tone - 1)
                        poly = clip_poly([E0, E1, cc], rect)
                        if len(poly) < 3:
                            continue
                        area = 0.0
                        for q in range(len(poly)):
                            pa, pb = poly[q], poly[(q + 1) % len(poly)]
                            area += pa[0] * pb[1] - pb[0] * pa[1]
                        if abs(area) < 2e-6:
                            continue
                        idx, pts = [], []
                        for x, y in poly:            # drop repeated points (a clip exactly on a vertex)
                            v = vid(x, y)
                            if v not in idx:
                                idx.append(v)
                                pts.append((x, y))
                        if len(idx) < 3:
                            continue
                        uv = [(x / TILE, y / TILE) for x, y in pts]
                        for q in range(1, len(idx) - 1):
                            acc.face([idx[0], idx[q], idx[q + 1]], [uv[0], uv[q], uv[q + 1]], tones[tone], (0, 0, -1))
                        n += 1
    return n


def boss(acc, x, y, r=0.0135, sides=8):
    """A domed dark-bronze boss on a star centre: a short drum and a low cone (its top sits inside the strips)."""
    z_top, z0, z_apex = STRIP_Z + 0.006, STRIP_Z - 0.003, STRIP_Z - 0.0075
    ring = lambda z, rr: acc.add([(x + rr * math.cos(2 * math.pi * (i + 0.5) / sides),
                                   y + rr * math.sin(2 * math.pi * (i + 0.5) / sides), z) for i in range(sides)])
    hi, lo, mid = ring(z_top, r), ring(z0, r), ring(z0 - 0.0028, r * 0.62)
    ap = acc.add([(x, y, z_apex)])[0]
    uv = lambda v: (0.5 + (acc.v[v][0] - x) * 0.5, 0.5 + (acc.v[v][1] - y) * 0.5 + (acc.v[v][2] - z0) * 0.5)
    for i in range(sides):
        j = (i + 1) % sides
        a = 2 * math.pi * (i + 1) / sides
        out = (math.cos(a), math.sin(a), 0.0)
        acc.face([lo[i], lo[j], hi[j], hi[i]], [uv(lo[i]), uv(lo[j]), uv(hi[j]), uv(hi[i])], BZ, out)
        acc.face([mid[i], mid[j], lo[j], lo[i]], [uv(mid[i]), uv(mid[j]), uv(lo[j]), uv(lo[i])], BZ,
                 (out[0], out[1], -1.2))
        acc.face([ap, mid[j], mid[i]], [uv(ap), uv(mid[j]), uv(mid[i])], BZ, (out[0] * 0.3, out[1] * 0.3, -1))


# --------------------------------------------------------------------------- piece

def lattice_panel(G):
    pc = G["Piece"]("SM_AK_Ceiling_Lattice_2x2")
    acc = Acc()
    frame(acc)
    corner_stacks(acc)
    inner_blocks(acc)
    asanoha(acc, POCKET, 2.0 - POCKET)
    diffuser(acc, POCKET, 2.0 - POCKET)
    acc.emit(pc)
    pc.col(0, 2, 0, 2, -0.06, 0.20)   # the scripted collision, unchanged
    return pc


def pieces(G):
    return [lattice_panel(G)]
