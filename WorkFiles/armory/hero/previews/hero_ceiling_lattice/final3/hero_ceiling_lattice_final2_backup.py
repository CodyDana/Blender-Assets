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

Fix round 3 (blind judge): kumiko 22 mm deep (2.5 x), 13 mm wide; the cell glow in register with the bars (a dim sheet
plus three concentric insets per cell in small tone steps, no facets across the cells); the inner LED tucked behind a
lip, a 1.9 cm pale-gold slot head with a falloff wash on sloped reveal walls; five stepped log-cabin tiers; soft dark
edge wear instead of copper outlines, GU 7 for visible grain; 45-degree channel ends; a V seam splitting the lower
outer face into two boards; smooth-shaded 10-sided bronze bosses (no facet glints).

Final 2 (blind judge: flat peach panel, dark side view): the backing is a saturated amber-gold ladder (GLOW 0-6,
emission dominated, core ~#E6A355 in the AgX review render), four insets per cell set in from each bar by how squarely
it faces SHADOW (light-to-shadow inside every triangle), lifted two / one levels toward the panel centre (radial
falloff), sunk between the bars (INSET_Z) with backlit kumiko sides (M_AK_HKumikoLit), so a low side view reads as a
glowing field; the timber is the shared espresso M_AK_Timber (hero_shared, grain along U: Acc.emit swaps the UVs, GU 1)
with a subtle copper-red worn arris (M_AK_HTimberEdge); the frame ring is unchanged.

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
Timber UVs: the builders run V along every member; Acc.emit swaps them for the shared T_AK_HTimber (grain along U).
ENABLED stays False: the user reviews images before anything goes in.
"""
import math

ENABLED = False          # the user reviews images of every piece BEFORE anything goes into the armory; never set True

WA, ED, LE = "M_AK_HLatticeWash", "M_AK_HTimberEdge", "M_AK_HLatticeLED"
WL, HL, KS = "M_AK_HLatticeSpill", "M_AK_HLatticeLine", "M_AK_HKumikoLit"
GLOW = [f"M_AK_HLatticeGlow{k}" for k in range(7)]   # the backlit panel's tone ladder, 0 = the shadowed sheet
# final 2 (blind judge: the panel read flat peach): a saturated amber-gold ladder, emission dominated (a near-black
# base colour, so no room / studio light washes it to cream): (emission colour, strength) per level; AgX-measured
# output: centre cells ~#E8A04A core, rim cells ~#D8902E (the ~#F0A040 core). Each cell uses four levels (shadow
# side -> core), shifted up toward the panel centre (the radial falloff), see diffuser()
LADDER = [("#FFA010", 0.30), ("#FFA210", 0.44), ("#FFA410", 0.58), ("#FFA410", 0.74), ("#FFA40C", 0.92),
          ("#FFA408", 1.12), ("#FFA400", 1.36)]
MATERIALS = {
    # the backlit panel behind the kumiko (history: the kit's M_AK_GoldGlow read pale peach and also lights the rear
    # alcove screens; fix 3 concentric per-cell tones read flat peach; final 2: the amber ladder above)
    **{GLOW[k]: (None, 1.0, {"color": "#24160A", "emit": s, "emit_color": c}) for k, (c, s) in enumerate(LADDER)},
    # final 2: the kumiko side faces catch the backlight (the sheet's thin amber lines inside every cell, and what makes
    # the side view from below read as a glowing lattice field, not a dark field): lit amber-brown wood
    KS: (None, 1.0, {"color": "#3A2614", "rough": 0.7, "emit": 0.24, "emit_color": "#FF9420"}),
    # the reveal surfaces lit by the hidden LED line: an amber wash on the upper walls, a dim spill lower down (fix 3)
    WA: (None, 1.0, {"color": "#5E4020", "emit": 0.3, "emit_color": "#FFB040"}),
    WL: (None, 1.0, {"color": "#2E2016", "emit": 0.09, "emit_color": "#FFA030"}),
    # fix 3: the narrow slot head over the hidden inner LED: the sheet's pale warm-gold line
    HL: (None, 1.0, {"color": "#E0A444", "emit": 1.0, "emit_color": "#FFB23C"}),
    # the LED emitters (outer channel back, the hidden inner pocket): amber-gold, not peach
    LE: (None, 1.0, {"color": "#FFB23A", "emit": 1.15, "emit_color": "#FFA82A"}),
    # worn edges of the dark-stained timber. Fix 3: a soft rubbed wear only a shade warmer than the timber (the fix-2
    # copper #5E3822 drew crisp orange outlines round every member), on the main arrises only. Final 2: the sheet's
    # worn copper-red arris highlight, kept subtle (darker than fix 2, a little sheen so it catches as a highlight)
    ED: (None, 1.0, {"color": "#401C11", "rough": 0.78}),
}

T, BZ = "M_AK_Timber", "M_AK_Bronze"
TILE = 2.0               # M_AK_Timber tiles every 2 m
# final 2: the shared espresso M_AK_Timber (hero_shared: T_AK_HTimber, fine wire-brushed grain along U at the 2 m tile)
# needs no across-grain compression (fix 3 used 7 for the kit's broad T_AK_Timber streaks)
GU = 1.0                # across-grain UV scale

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
    (0.037, 0.008, T),    # shelf arris
    (0.034, 0.005, T),    # outer face, lower tier (set back 4 mm): upper board
    (0.034, -0.021, T),   # fix 3: the seam between the two stacked lower boards (a small V)
    (0.038, -0.025, T),
    (0.034, -0.029, T),   # lower board
    (0.034, -0.052, ED),
    (0.042, -0.060, T),   # rail underside
    (0.122, -0.060, ED),
    (0.130, -0.052, T),   # rail inner face
    (0.130, -0.036, T),   # groove head
    (0.136, -0.036, T),   # step outer face
    (0.136, -0.043, T),
    (0.140, -0.047, T),   # step underside, sloping up toward the slot (coffer-like)
    (0.158, -0.041, WL),  # the lip nose: a dim spill of the hidden LED
    (0.165, -0.034, WL),  # lip inner face
    (0.165, -0.018, WA),  # pocket floor (top of the lip)
    (0.151, -0.018, LE),  # the hidden inner LED (faces the slot, tucked behind the lip)
    (0.151, -0.004, HL),  # slot head: the pale-gold line (1.9 cm seen from below, 0.165-0.184)
    (0.184, -0.004, WA),  # far wall of the slot, sloping in as it goes down: wash, then spill, then dark
    (0.187, -0.020, WL),
    (0.190, -0.036, T),
    (0.191, -0.045, ED),
    (0.196, -0.050, T),   # inner rail underside
    (0.221, -0.050, ED),
    (0.225, -0.046, T),   # inner rail inner face, sloping back to the glow panel (coffer-like)
    (0.231, -0.003, None),   # 1 mm past the backing (no shared vertices with it)
]
TOP_Z = 0.130
GLOW_Z = -0.004           # the backing sits 1 mm over the highest kumiko family (fix 2: closer, the cells glow through)
POCKET = 0.225            # lattice opening, d 0.225 .. 1.775
CH = 0.005                # chamfer on the corner stack blocks

# corner stacks (fix 2): a post (d POST) and rail-end tiers that cross it, alternately projecting 17 mm past the post
# in X and in Y and set back 24 mm behind it in the other axis (stepped, notched side view); the top tier is a cap
# projecting both ways; under the post a 2 x 2 cap of equal end blocks split by a deep cross groove
# fix 3: five tiers (z0, z1, d out in X, d out in Y, grain along X), stepping out 1.5-3 cm going down as a stair in
# both side views, the log-cabin alternation (each tier projects in one axis, sits back in the other) on top of it
POST = (0.046, 0.124, -0.060, 0.184)
TIERS = [(0.136, 0.186, 0.036, 0.036, False),
         (0.084, 0.132, 0.024, 0.044, True),
         (0.032, 0.080, 0.040, 0.016, False),
         (-0.020, 0.028, 0.004, 0.026, True),
         (-0.060, -0.024, 0.016, 0.002, False)]
TIER_END = 0.132
END_Z = (-0.079, -0.061)               # the 2 x 2 end blocks under each stack (18 mm, the groove as deep)
END_G = 0.008                          # cross groove width
N_COL, N_ROW = 8, 5                    # asanoha: column intervals across, row periods along (sheet count)
# fix 3: the bars 2.5 x deeper (22 mm, 13 mm wide): the sheet's deep kumiko with side faces and shadowed pockets
STRIP_W, STRIP_D, STRIP_CH = 0.013, 0.022, 0.002
FAM_DZ = 0.0012
STRIP_Z = GLOW_Z - 0.004 - 5 * FAM_DZ - STRIP_D     # the highest family's back 1 mm under the core glow inset
# final 2: per cell four glowing insets (shadow tone .. core), each edge set in from its bar line by t0 + tsh *
# (how squarely the bar faces the shadow direction SHADOW): a light-to-shadow falloff inside every triangle (the deep
# bars shade one side of the cell, the core leans to the lit side), in register with the bars. The bar half width is
# 6.5 mm, so the first inset leaves a 2 mm slit of the dim sheet along every bar.
INSETS = ((0.0085, 0.0), (0.0095, 0.0070), (0.0107, 0.0150), (0.0121, 0.0245))
SHADOW = (0.5, -0.866)                  # the direction the bars' soft shadows fall across the panel (constant)
INSET_Z = -0.023                        # the insets sit down between the bars (their backs 18 mm into the 22 mm
                                        # depth), so a low side view sees the lit cells, not only the bar sides
RADIAL = (0.42, 0.78)                   # cell centre distance / half opening: centre, middle ring, rim (+2, +1, +0 levels)


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
        """Final 2: the builders lay the grain along V; the shared T_AK_HTimber grain runs along U (hero_shared), so the
        timber faces get (u, v) swapped here."""
        if self.f:
            uv = [[(b, a) for a, b in f] if m == T else f for f, m in zip(self.uv, self.m)]
            piece.mesh(self.v, self.f, uv, self.m, smooth=False)


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
            for z0, z1, xa, ya, ax in TIERS:
                x0, x1 = span(xa, TIER_END, lx)
                y0, y1 = span(ya, TIER_END, ly)
                cbox(acc, x0, x1, y0, y1, z0, z1, along_x=ax)
            c0, c1, cz0, cz1 = POST
            x0, x1 = span(c0, c1, lx)
            y0, y1 = span(c0, c1, ly)
            cbox(acc, x0, x1, y0, y1, cz0, cz1, ch=0.002, along_x=False)
            e0, e1 = 0.003, TIER_END
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


def asanoha(acc, o0, o1, bacc=None):
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
            # final 2: side faces lit by the backlight (KS), the worn copper-red arris on the two chamfers
            bar(acc, s[0], s[1], sec, [KS, ED, T, ED, KS], uoff=(n * 0.618) % 1.0 * TILE, caps=False)
    for (x, y) in stars:
        boss(bacc or acc, x, y)
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


def halfplane(poly, p0, n, t):
    """Sutherland-Hodgman against one line: the part of convex poly with n . (p - p0) >= t."""
    out = []
    f = [n[0] * (p[0] - p0[0]) + n[1] * (p[1] - p0[1]) - t for p in poly]
    for k in range(len(poly)):
        a, b, fa, fb = poly[k], poly[(k + 1) % len(poly)], f[k], f[(k + 1) % len(poly)]
        if fa >= 0:
            out.append(a)
        if (fa >= 0) != (fb >= 0):
            u = fa / (fa - fb)
            out.append((a[0] + u * (b[0] - a[0]), a[1] + u * (b[1] - a[1])))
    return out


def diffuser(acc, o0, o1):
    """The backlit backing. Fix 3: one dim amber sheet (GLOW[0]) behind the whole opening, and per asanoha cell glowing
    insets in register with the bars. Final 2: the insets sit down between the bars (INSET_Z), each is set in from
    every bar line by t0 + tsh * (how squarely that bar faces SHADOW), so every triangle falls from a bright core on
    its lit side into the shadow of its bars; the four insets take ladder levels base+1 .. base+4 where base
    is 2 at the panel centre, 1 in the middle ring and 0 at the rim (the centre-bright radial falloff toward the frame).
    Cells cut by the rail are clipped against the opening edges the same way (the rail throws the same shadow)."""
    L = o1 - o0
    c, P = L / N_COL, L / N_ROW
    e = o0 - 0.007
    base = acc.add([(e, e, GLOW_Z), (2 - e, e, GLOW_Z), (2 - e, 2 - e, GLOW_Z), (e, 2 - e, GLOW_Z)])
    acc.face(base, [(acc.v[i][0] / TILE, acc.v[i][1] / TILE) for i in base], GLOW[0], (0, 0, -1))
    sl = math.hypot(*SHADOW)
    sd = (SHADOW[0] / sl, SHADOW[1] / sl)
    half = L / 2
    rect = [((o0, 0.0), (1.0, 0.0)), ((o1, 0.0), (-1.0, 0.0)), ((0.0, o0), (0.0, 1.0)), ((0.0, o1), (0.0, -1.0))]

    def pt(k, j):
        return (o0 + k * c, o0 + j * P / 2)
    n = 0
    for k in range(N_COL):
        for j in range(-4, 2 * N_ROW + 3):
            if (j + k) % 2:
                continue
            for tri in ((pt(k, j), pt(k, j + 2), pt(k + 1, j + 1)), (pt(k + 1, j + 1), pt(k + 1, j + 3), pt(k, j + 2))):
                g = (sum(p[0] for p in tri) / 3, sum(p[1] for p in tri) / 3)
                for e3 in range(3):
                    cell = [tri[e3], tri[(e3 + 1) % 3], g]
                    cc = (sum(p[0] for p in cell) / 3, sum(p[1] for p in cell) / 3)
                    if not (o0 < cc[0] < o1 and o0 < cc[1] < o1):
                        if not halfplane(halfplane(halfplane(halfplane(cell, *rect[0], 0.0), *rect[1], 0.0),
                                                   *rect[2], 0.0), *rect[3], 0.0):
                            continue
                    lines = []
                    for q in range(3):
                        a, b, o = cell[q], cell[(q + 1) % 3], cell[(q + 2) % 3]
                        nx, ny = -(b[1] - a[1]), b[0] - a[0]
                        ln = math.hypot(nx, ny)
                        nx, ny = nx / ln, ny / ln
                        if nx * (o[0] - a[0]) + ny * (o[1] - a[1]) < 0:
                            nx, ny = -nx, -ny
                        lines.append((a, (nx, ny)))
                    lines += rect
                    rr = math.hypot(cc[0] - 1.0, cc[1] - 1.0) / half
                    lift = 2 if rr < RADIAL[0] else (1 if rr < RADIAL[1] else 0)
                    for li, ((t0, tsh), lvl) in enumerate(zip(INSETS, (1, 2, 3, 4))):
                        poly = list(cell)
                        for p0, nn in lines:
                            sh = max(0.0, nn[0] * sd[0] + nn[1] * sd[1])
                            poly = halfplane(poly, p0, nn, t0 + tsh * sh)
                            if len(poly) < 3:
                                break
                        if len(poly) < 3:
                            continue
                        clean = []
                        for p in poly:
                            if not clean or math.dist(p, clean[-1]) > 1e-4:
                                clean.append(p)
                        if len(clean) > 3 and math.dist(clean[0], clean[-1]) <= 1e-4:
                            clean.pop()
                        k2 = 0
                        while len(clean) > 3 and k2 < len(clean):   # drop collinear points (no zero-area fan tris)
                            a, p, b = clean[k2 - 1], clean[k2], clean[(k2 + 1) % len(clean)]
                            if abs((p[0] - a[0]) * (b[1] - p[1]) - (p[1] - a[1]) * (b[0] - p[0])) < 1e-8:
                                clean.pop(k2)
                            else:
                                k2 += 1
                        if len(clean) < 3:
                            continue
                        pa = 0.0
                        for q in range(len(clean)):
                            a, b = clean[q], clean[(q + 1) % len(clean)]
                            pa += a[0] * b[1] - b[0] * a[1]
                        if abs(pa) < 2e-5:
                            continue
                        z = INSET_Z - 0.001 * li
                        idx = acc.add([(x, y, z) for x, y in clean])
                        uv = [(x / TILE, y / TILE) for x, y in clean]
                        for q in range(1, len(idx) - 1):
                            acc.face([idx[0], idx[q], idx[q + 1]], [uv[0], uv[q], uv[q + 1]], GLOW[lvl + lift],
                                     (0, 0, -1))
                        n += 1
    return n


def channel_ends(acc):
    """Fix 3: the outer LED channel ends are chamfered at 45 degrees into the corner stacks (the sheet's side view):
    a wedge at each end of each side, its slope lit by the strip, its outer face flush with the rail face."""
    a0, a1 = TIER_END - 0.004, TIER_END - 0.004 + 0.056
    z0, z1 = 0.008, 0.064
    d0, d1 = 0.032, 0.078
    for side in range(4):
        for lo in (True, False):
            def P(a, d, z):
                a = a if lo else 2.0 - a
                return ((a, d, z), (a, 2 - d, z), (d, a, z), (2 - d, a, z))[side]
            dn = ((0, -1), (0, 1), (-1, 0), (1, 0))[side]           # outward normal of this side
            along = (1.0 if lo else -1.0)
            ax = (along, 0.0) if side < 2 else (0.0, along)        # toward the open channel
            q = acc.add([P(a0, d0, z1), P(a0, d1, z1), P(a1, d1, z0), P(a1, d0, z0)])
            L = math.dist(acc.v[q[0]], acc.v[q[3]])
            acc.face(q, [(0.3, 0.3), (0.3 + 0.046 * GU / TILE, 0.3), (0.3 + 0.046 * GU / TILE, 0.3 + L / TILE),
                         (0.3, 0.3 + L / TILE)], WA, (ax[0], ax[1], 1.0))
            tr = [q[0], q[3], acc.add([P(a0, d0, z0)])[0]]      # shares the slope's outer edge (no doubled vertices)
            acc.face(tr, [(0.5, 0.5), (0.5 + 0.056 / TILE, 0.5 - 0.056 / TILE), (0.5, 0.5 - 0.056 / TILE)], T,
                     (dn[0], dn[1], 0.0))


def boss(acc, x, y, r=0.0135, sides=10):
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
    channel_ends(acc)
    bacc = Acc()                       # fix 3b: the bosses are their own smooth-shaded part (no facet glints)
    asanoha(acc, POCKET, 2.0 - POCKET, bacc)
    diffuser(acc, POCKET, 2.0 - POCKET)
    acc.emit(pc)
    if bacc.f:
        pc.mesh(bacc.v, bacc.f, bacc.uv, bacc.m, smooth=True)
    pc.col(0, 2, 0, 2, -0.06, 0.20)   # the scripted collision, unchanged
    return pc


def pieces(G):
    return [lattice_panel(G)]
