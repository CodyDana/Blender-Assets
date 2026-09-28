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

GL, WA, ED = "M_AK_HLatticeGlow", "M_AK_HLatticeWash", "M_AK_HTimberEdge"
MATERIALS = {
    # the backlit panel behind the kumiko: saturated honey amber (the kit's M_AK_GoldGlow read pale peach here and it
    # also lights the rear alcove screens, so the lattice gets its own)
    GL: (None, 1.0, {"color": "#C88A10", "emit": 0.9, "emit_color": "#FFA600"}),
    # the reveal walls lit by the hidden LED line (a warm wash, as hero_banner_coffer's lit cove edge)
    WA: (None, 1.0, {"color": "#7A5222", "emit": 0.5, "emit_color": "#FFA41C"}),
    # worn edges of the dark-stained timber: the sheet's warm reddish-bronze edge wear on the chamfers
    ED: (None, 1.0, {"color": "#4A2A1A", "rough": 0.6}),
}

T, BZ, LL = "M_AK_Timber", "M_AK_Bronze", "M_AK_LEDLine"
TILE = 2.0               # M_AK_Timber tiles every 2 m

# frame profile (d in from the cell edge, z up from the ceiling line, material of the segment to the next point)
PROFILE = [
    (0.030, 0.130, T),    # outer face, upper tier
    (0.030, 0.044, WA),   # LED slot: top face (lit)
    (0.050, 0.044, LL),   # LED slot: the strip at its back
    (0.050, 0.016, WA),   # LED slot: bottom face (lit)
    (0.030, 0.016, T),    # outer face, lower tier
    (0.030, -0.052, ED),
    (0.038, -0.060, T),   # rail underside
    (0.122, -0.060, ED),
    (0.130, -0.052, T),   # rail inner face
    (0.130, -0.032, T),   # groove head
    (0.138, -0.032, T),   # step outer face
    (0.138, -0.041, ED),
    (0.142, -0.045, T),   # step underside
    (0.154, -0.045, WA),  # lit chamfer
    (0.158, -0.041, WA),  # reveal wall (step side)
    (0.158, -0.004, WA),  # reveal head, lit
    (0.174, -0.004, LL),  # the LED line
    (0.188, -0.004, WA),  # reveal wall (inner rail side)
    (0.188, -0.046, ED),
    (0.192, -0.050, T),   # inner rail underside
    (0.221, -0.050, ED),
    (0.225, -0.046, T),   # inner rail inner face, up to the glow panel
    (0.225, 0.006, None),
]
TOP_Z = 0.130
GLOW_Z = 0.006
POCKET = 0.225            # lattice opening, d 0.225 .. 1.775
CH = 0.004                # chamfer on the corner stack blocks

# corner stack tiers: (z0, z1, projects in X?)  the projecting tier reaches the cell edge (d 0), the other stops at
# d 0.014; all reach inward to d 0.132 (just past the rail's inner face)
TIERS = [(-0.063, -0.022, True), (-0.018, 0.020, False), (0.024, 0.070, True), (0.074, 0.126, False),
         (0.132, 0.186, True)]
CORE = (0.022, 0.126, -0.067, 0.182)   # d range and z range of the core seen in the grooves between tiers
END_Z = (-0.075, -0.065)               # the 2 x 2 end blocks under each stack
N_COL, N_ROW = 8, 5                    # asanoha: column intervals across, row periods along (sheet count)
STRIP_W, STRIP_D, STRIP_Z = 0.013, 0.013, -0.028
FAM_DZ = 0.0015


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


def bar(acc, p0, p1, section, mat, uoff=0.0):
    """A straight member along p0 -> p1 (XY points), open cross-section [(s, z)] (top open, it sits against something).
    V runs along the member (the timber grain), U round the section."""
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
        u0, u1 = per[k] / TILE + 0.21, per[k + 1] / TILE + 0.21
        acc.face([r0[k], r1[k], r1[k + 1], r0[k + 1]], [(u0, v0), (u0, v1), (u1, v1), (u1, v0)], mat,
                 (nx * sm, ny * sm, zm))
    for r, d in ((r0, (-ax, -ay, 0.0)), (r1, (ax, ay, 0.0))):
        uvs = [((s - sc) / TILE + 0.3, (z - zc) / TILE + 0.3) for s, z in section]
        for k in range(1, len(section) - 1):   # fan: sections are convex
            acc.face([r[0], r[k], r[k + 1]], [uvs[0], uvs[k], uvs[k + 1]], mat, d)


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
        u0, u1 = per[k] / TILE + uo, per[k + 1] / TILE + uo
        v0, v1 = a0 / TILE, a1 / TILE
        acc.face([r0[k], r1[k], r1[j], r0[j]], [(u0, v0), (u0, v1), (u1, v1), (u1, v0)], mats[k], P(0.0, bm, zm))
    for r, s in ((r0, -1.0), (r1, 1.0)):
        uvs = [((b - bc) / TILE + uo, (z - zc) / TILE + 0.5) for b, z in sec]
        for k in range(1, 7):
            acc.face([r[0], r[k], r[k + 1]], [uvs[0], uvs[k], uvs[k + 1]], mat, P(s, 0.0, 0.0))


# --------------------------------------------------------------------------- frame

def frame(acc):
    """The rail profile swept round the square with mitred corners (the mitres sit inside the corner stacks), the top
    plate closing the frame and the glow panel closing the lattice pocket."""
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
            uvs = [(per[kk] / TILE + 0.13 * s, acc.v[i][ax] / TILE)
                   for kk, i in ((k, idx[0]), (k, idx[1]), (k + 1, idx[2]), (k + 1, idx[3]))]
            n = inward[s]
            acc.face(idx, uvs, mat, (nd * n[0], nd * n[1], nz))
    top = rings[0]
    acc.face(top, [(acc.v[i][0] / TILE, acc.v[i][1] / TILE) for i in top], T, (0, 0, 1))
    glow = rings[-1]
    acc.face(glow, [(acc.v[i][0] / TILE, acc.v[i][1] / TILE) for i in glow], GL, (0, 0, -1))


def span(a, b, lo):
    """d range [a, b] measured in from the low or the high cell edge -> coordinate range."""
    return (a, b) if lo else (2.0 - b, 2.0 - a)


def corner_stacks(acc):
    """Log-cabin stacks: tiers alternately projecting in X and in Y (crossing rail ends), a core showing in the 4 mm
    grooves between them, and a 2 x 2 cap of end blocks split by a cross groove underneath."""
    for lx in (True, False):
        for ly in (True, False):
            for z0, z1, proj_x in TIERS:
                xa = 0.003 if proj_x else 0.016
                ya = 0.016 if proj_x else 0.003
                x0, x1 = span(xa, 0.132, lx)
                y0, y1 = span(ya, 0.132, ly)
                cbox(acc, x0, x1, y0, y1, z0, z1, along_x=not proj_x)
            c0, c1, cz0, cz1 = CORE
            x0, x1 = span(c0, c1, lx)
            y0, y1 = span(c0, c1, ly)
            cbox(acc, x0, x1, y0, y1, cz0, cz1, ch=0.002)
            g, e0, e1 = 0.006, 0.006, 0.128
            q = (e1 - e0 - g) / 2
            for i in range(2):
                for j in range(2):
                    x0, x1 = span(e0 + i * (q + g), e0 + i * (q + g) + q, lx)
                    y0, y1 = span(e0 + j * (q + g), e0 + j * (q + g) + q, ly)
                    cbox(acc, x0, x1, y0, y1, END_Z[0], END_Z[1], ch=0.003, along_x=(i + j) % 2 == 0)


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
        sec = [(STRIP_W / 2, zb + STRIP_D), (STRIP_W / 2, zb), (-STRIP_W / 2, zb), (-STRIP_W / 2, zb + STRIP_D)]
        for p0, p1 in lst:
            if not clip(p0, p1, inner):
                continue
            s = clip(p0, p1, under)
            if math.dist(*s) < 0.004:
                continue
            n += 1
            bar(acc, s[0], s[1], sec, T, uoff=(n * 0.618) % 1.0 * TILE)
    for (x, y) in stars:
        boss(acc, x, y)
    return len(stars)


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
    acc.emit(pc)
    pc.col(0, 2, 0, 2, -0.06, 0.20)   # the scripted collision, unchanged
    return pc


def pieces(G):
    return [lattice_panel(G)]
