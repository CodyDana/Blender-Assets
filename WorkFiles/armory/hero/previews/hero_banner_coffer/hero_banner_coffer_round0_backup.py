"""Hero pieces from the user's reference sheets WorkFiles/armory/reference/banner.png and ceiling_coffer.png:

SM_AK_Banner             the black silk banner: a two-layer cloth with soft vertical folds that wraps a round black
                         lacquer rod in a sleeve (gold piping at the sleeve ends), brass end caps with collars, gold
                         cord loops round the rod up to small brass ceiling roses, and a gold cord tassel (woven knob,
                         collar, fluted skirt) under each bottom corner. The cloth keeps T_AK_Banner (the user's
                         emblem and the gold border are in the texture) with a top-true mapping: the border and the
                         emblem sit exactly where the scripted banner had them under the rod; only the plain field
                         between the emblem and the small crests is shortened to make room for the tassels.
SM_AK_Ceiling_Coffer_2x2 the coffer between the Beam_4 / Rib_2 grid: an outer soffit lip, a warm lit cove (LED line +
                         glowing cove soffit), a bevelled mitred moulding frame and a recessed dark timber panel of
                         planks (4 grooves: half plank - 3 planks - half plank, as the sheet). No light fitting: only
                         22 of the 42 coffers get a Down_ spot in lights(), so the fitting is its own piece:
SM_AK_H_Ceiling_Downlight  NEW: the round downlight (dark bronze trim, brass bezel, warm lens) placed by instances()
                         at exactly the lights() Down_ positions (x 3/5/7/9, y 3..15, not over the lattice coffers)
SM_AK_H_Ceiling_Joint    NEW: the notched timber joint block of the sheet's frame corners, at every Beam_4 x Rib_2
                         crossing (x 2..10, y 2..14)

Frames (the kit's): the banner is freestanding-centred, cloth facing -Y, tassel feet at z 0, cords to z 2.40 (the
ceiling when hung at BANNER_Z); the coffer spans local 0-2 x 0-2 with z 0 = CEIL; the new pieces are centred on their
light / crossing with z 0 = CEIL.
"""
import math

import bmesh

ENABLED = False   # the user reviews images of every piece before anything goes into the armory

CG = "M_AK_HCoveGlow"
CE = "M_AK_HCoveEdge"
GC = "M_AK_HGoldCord"
MATERIALS = {
    # the coffer cove, lit by its hidden LED line (flat params, like the kit's glow materials): the soffit a soft warm
    # wash, the lit edge of the moulding frame a brighter warm line
    CG: (None, 1.0, {"color": "#3E2A18", "emit": 0.20, "emit_color": "#F7B878"}),
    CE: (None, 1.0, {"color": "#8A5A2E", "emit": 0.60, "emit_color": "#FFB060"}),
    # gold silk cord: the tassels, the cord loops and the sleeve piping (a soft sheen, not polished brass)
    GC: (None, 1.0, {"color": "#B88C3C", "rough": 0.5, "metal": 0.35}),
}
T, LQ, BR, BZ = "M_AK_Timber", "M_AK_Lacquer", "M_AK_Brass", "M_AK_Bronze"
LL, LED, BN = "M_AK_LEDLine", "M_AK_LED", "M_AK_Banner"
TILE_T = 2.0   # M_AK_Timber tiles every 2 m

# the ceiling grid (build_armory_kit.kit/layout): Rib_2 is 16 cm wide on the x lines, Beam_4 25 cm on the y lines
EX, EY = 0.08, 0.125


# --------------------------------------------------------------------------- mesh helpers

class Part:
    """Accumulates one mesh part (verts, faces, per-face loop UVs, per-face materials, per-face smooth)."""

    def __init__(self):
        self.v, self.f, self.uv, self.m, self.s = [], [], [], [], []

    def vert(self, co):
        self.v.append(tuple(co))
        return len(self.v) - 1

    def face(self, idx, uvs, mat, smooth=False):
        self.f.append(tuple(idx))
        self.uv.append([tuple(u) for u in uvs])
        self.m.append(mat)
        self.s.append(smooth)

    def emit(self, piece, orient=True):
        faces, uvs = self.f, self.uv
        if orient:
            faces, uvs = _outward(self.v, faces, uvs)
        piece.mesh(self.v, faces, uvs, self.m, smooth=self.s)
        return piece


def _outward(verts, faces, uvs):
    """Consistent outward winding (bmesh recalc_face_normals), carrying the loop UVs along."""
    bm = bmesh.new()
    lay = bm.loops.layers.uv.new("uv")
    vs = [bm.verts.new(v) for v in verts]
    fl = []
    for f, fu in zip(faces, uvs):
        bf = bm.faces.new([vs[i] for i in f])
        for loop, uv in zip(bf.loops, fu):
            loop[lay].uv = uv
        fl.append(bf)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.verts.index_update()
    out_f = [tuple(lp.vert.index for lp in bf.loops) for bf in fl]
    out_uv = [[tuple(lp[lay].uv) for lp in bf.loops] for bf in fl]
    bm.free()
    return out_f, out_uv


def lathe(part, profile, sides, mats, axis="z", c=(0.0, 0.0, 0.0), rfac=None, smooth=True, a0=0.0):
    """Surface of revolution. profile: [(r, h)], r == 0 -> pole. mats: one per segment (or one name).
    axis 'z': h is z; axis 'x': h is x, the circle in the y-z plane. rfac(k, i) scales ring k, vertex i (ridges)."""
    if isinstance(mats, str):
        mats = [mats] * (len(profile) - 1)
    rings = []
    for k, (r, h) in enumerate(profile):
        if r == 0:
            if axis == "z":
                rings.append([part.vert((c[0], c[1], c[2] + h))] * sides)
            else:
                rings.append([part.vert((c[0] + h, c[1], c[2]))] * sides)
            continue
        ring = []
        for i in range(sides):
            a = a0 + 2 * math.pi * i / sides
            rr = r * (rfac(k, i) if rfac else 1.0)
            if axis == "z":
                ring.append(part.vert((c[0] + rr * math.cos(a), c[1] + rr * math.sin(a), c[2] + h)))
            else:
                ring.append(part.vert((c[0] + h, c[1] + rr * math.cos(a), c[2] + rr * math.sin(a))))
        rings.append(ring)
    arc = [0.0]
    for k in range(1, len(profile)):
        arc.append(arc[-1] + math.dist(profile[k - 1], profile[k]))
    for k in range(len(profile) - 1):
        a, b = rings[k], rings[k + 1]
        for i in range(sides):
            j = (i + 1) % sides
            uv = [(i / sides, arc[k]), (j / sides, arc[k]), (j / sides, arc[k + 1]), (i / sides, arc[k + 1])]
            if profile[k][0] == 0:
                part.face((a[i], b[j], b[i]), [uv[0], uv[2], uv[3]], mats[k], smooth)
            elif profile[k + 1][0] == 0:
                part.face((a[i], a[j], b[i]), [uv[0], uv[1], uv[3]], mats[k], smooth)
            else:
                part.face((a[i], a[j], b[j], b[i]), uv, mats[k], smooth)
    return part


def sweep_rect(part, loops, mats, caps=(None, None), tile=TILE_T):
    """Loft a profile round a rectangle with mitred corners. loops: [(x0, y0, x1, y1, z)], mats: one per segment.
    UV: u runs along the profile, v along each side (the timber grain follows the side). caps: material of a quad
    closing the first / last loop (None = open)."""
    L = []
    for (x0, y0, x1, y1, z) in loops:
        L.append([part.vert(p) for p in ((x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z))])
    arc = [0.0]
    for k in range(1, len(loops)):
        pa, pb = loops[k - 1], loops[k]
        arc.append(arc[-1] + math.hypot(pa[0] - pb[0], pa[4] - pb[4]))
    for k in range(len(loops) - 1):
        for s in range(4):
            t = (s + 1) % 4
            ids = (L[k][s], L[k][t], L[k + 1][t], L[k + 1][s])
            d = [part.v[ids[1]][i] - part.v[ids[0]][i] for i in range(2)]
            n = math.hypot(*d) or 1.0
            d = (d[0] / n, d[1] / n)
            uvs = [(arc[k if q < 2 else k + 1] / tile,
                    (part.v[i][0] * d[0] + part.v[i][1] * d[1]) / tile) for q, i in enumerate(ids)]
            part.face(ids, uvs, mats[k])
    for ring, m in ((L[0], caps[0]), (L[-1], caps[1])):
        if m:
            part.face(ring, [(part.v[i][0] / tile, part.v[i][1] / tile) for i in ring], m)
    return part


def prism_x(part, section, x0, x1, mat, tile=TILE_T):
    """A closed prism along X with a convex (y, z) section: grain (texture v) along X, fan-triangulated caps."""
    n = len(section)
    a = [part.vert((x0, y, z)) for y, z in section]
    b = [part.vert((x1, y, z)) for y, z in section]
    arc = [0.0]
    for k in range(1, n + 1):
        arc.append(arc[-1] + math.dist(section[k - 1], section[k % n]))
    for k in range(n):
        j = (k + 1) % n
        part.face((a[k], a[j], b[j], b[k]),
                  [(arc[k] / tile, x0 / tile), (arc[k + 1] / tile, x0 / tile),
                   (arc[k + 1] / tile, x1 / tile), (arc[k] / tile, x1 / tile)], mat)
    for ring in (a, b):
        for k in range(1, n - 1):
            ids = (ring[0], ring[k], ring[k + 1])
            part.face(ids, [(part.v[i][1] / tile, part.v[i][2] / tile) for i in ids], mat)
    return part


def block(part, cx, cy, hx, hy, z_top, z_bot, ch, mat):
    """A timber block hanging from z_top to z_bot with a ch chamfer round its bottom edges (vertical edges sharp)."""
    loops = [(cx - hx, cy - hy, cx + hx, cy + hy, z_top), (cx - hx, cy - hy, cx + hx, cy + hy, z_bot + ch),
             (cx - hx + ch, cy - hy + ch, cx + hx - ch, cy + hy - ch, z_bot)]
    return sweep_rect(part, loops, [mat, mat], caps=(mat, mat))


# --------------------------------------------------------------------------- the banner

W2 = 0.275            # cloth half width (the scripted 0.55 m)
ZC, RR = 2.232, 0.016  # rod axis height and radius (the scripted rod box 2.215-2.25)
RS = RR + 0.0025      # the sleeve round the rod
ZS = ZC - 0.050       # sleeve seam (the gold border starts right under it, as the sheet)
ZB = 0.221            # cloth bottom hem; the tassels hang below it to z 0
Z1, Z2 = ZC - 0.88, ZB + 0.66   # texture kept 1:1 above Z1 (v 0.60, under the emblem) and below Z2 (v 0.30)
TASSEL_X = 0.265
CORD_X = 0.2865       # the cord loops sit on the bare rod between the sleeve and the caps


def vmap(z):
    """Banner texture V for a cloth height: true scale (2.2 m per V) from the top and from the bottom; the plain
    black field between v 0.30 and 0.60 is shortened (x 0.71) to leave room for the tassels."""
    if z >= Z1:
        return 1.0 - (ZC - z) / 2.2
    if z <= Z2:
        return (z - ZB) / 2.2
    return 0.30 + 0.30 * (z - Z2) / (Z1 - Z2)


def cloth_y(x, z):
    """Centre line of the two cloth layers (folds + a slight belly) and the half gap between them."""
    if z >= ZS:
        t = (z - ZS) / (ZC - ZS)
        return 0.0, 0.002 + (RS - 0.002) * t ** 0.55
    t = (z - ZB) / (ZS - ZB)                           # 0 at the hem, 1 at the seam
    amp = 0.0065 + 0.0035 * t                          # gathers stronger toward the top
    amp *= min(1.0, max(0.0, ZS - 0.012 - z) / 0.09)   # sewn flat under the seam (the top border line lies there)
    fold = amp * math.sin(2 * math.pi * (x + W2) / 0.22)
    belly = -0.006 * math.sin(math.pi * t)
    return belly + fold, 0.002


def banner(P):
    p = P("SM_AK_Banner")
    nu = 12
    zs = [ZB, 0.50, Z2, 1.12, Z1, 1.55, 1.75, 2.07, ZS - 0.045, ZS, ZC - 0.022, ZC]
    xs = [-W2 + 2 * W2 * i / nu for i in range(nu + 1)]
    cl = Part()
    F, B = [], []
    for z in zs:
        rf, rb = [], []
        for x in xs:
            yc, h = cloth_y(x, z)
            rf.append(cl.vert((x, yc - h, z)))
            rb.append(cl.vert((x, yc + h, z)))
        F.append(rf)
        B.append(rb)
    uf = [(x + W2) / (2 * W2) for x in xs]
    for r in range(len(zs) - 1):
        v0, v1 = vmap(zs[r]), vmap(zs[r + 1])
        for i in range(nu):
            cl.face((F[r][i], F[r][i + 1], F[r + 1][i + 1], F[r + 1][i]),
                    [(uf[i], v0), (uf[i + 1], v0), (uf[i + 1], v1), (uf[i], v1)], BN, True)
            cl.face((B[r][i], B[r + 1][i], B[r + 1][i + 1], B[r][i + 1]),     # the back reads the right way round
                    [(1 - uf[i], v0), (1 - uf[i], v1), (1 - uf[i + 1], v1), (1 - uf[i + 1], v0)], BN, True)
        if zs[r + 1] <= ZS + 1e-6:   # closed side edges below the sleeve seam (a black hem)
            for i, u in ((0, 0.006), (nu, 0.994)):
                cl.face((F[r][i], F[r + 1][i], B[r + 1][i], B[r][i]), [(u, v0), (u, v1), (u + 0.002, v1), (u + 0.002, v0)],
                        BN, False)
    for i in range(nu):   # bottom hem
        cl.face((F[0][i], B[0][i], B[0][i + 1], F[0][i + 1]),
                [(uf[i], 0.003), (uf[i], 0.006), (uf[i + 1], 0.006), (uf[i + 1], 0.003)], BN, False)
    # the sleeve over the rod: front top row -> over the rod -> back top row
    arcs = [2 * math.pi / 3, math.pi / 3]
    rows = []
    for a in arcs:
        rows.append([cl.vert((x, RS * math.cos(a), ZC + RS * math.sin(a))) for x in xs])
    rows = [F[-1]] + rows + [B[-1]]
    angs = [math.pi] + arcs + [0.0]
    for r in range(len(rows) - 1):
        va, vb = (0.990 + 0.010 * abs(math.cos(angs[r])), 0.990 + 0.010 * abs(math.cos(angs[r + 1])))   # black margin
        for i in range(nu):
            cl.face((rows[r][i], rows[r][i + 1], rows[r + 1][i + 1], rows[r + 1][i]),
                    [(uf[i], va), (uf[i + 1], va), (uf[i + 1], vb), (uf[i], vb)], BN, True)
    cl.emit(p)

    # the top border line (T_AK_Banner has the side and bottom lines only): a 7.5 mm strip right under the sleeve seam
    # on both faces, mapped onto the texture's own vertical border line so the embroidery matches the other three
    zl0, zl1 = ZC - (1 - 1993.5 / 2048) * 2.2, ZC - (1 - 2000.5 / 2048) * 2.2
    xl = W2 * (1 - 2 * 20.0 / 512)
    for side in (-1, 1):
        st = Part()
        y = side * (0.002 + 0.0006)
        q = [st.vert((-xl, y, zl0)), st.vert((xl, y, zl0)), st.vert((xl, y, zl1)), st.vert((-xl, y, zl1))]
        u0, u1 = 20.5 / 512, 25.5 / 512
        st.face(q, [(u0, 0.30), (u0, 0.70), (u1, 0.70), (u1, 0.30)], BN)
        if side > 0:   # the back strip faces +Y
            st.f[-1] = tuple(reversed(st.f[-1]))
            st.uv[-1] = list(reversed(st.uv[-1]))
        st.emit(p, orient=False)

    # gold piping round each sleeve end: a thin band following the sleeve section, 2.5 mm proud of the cloth
    sec = [(cloth_y(W2, z)[0] - cloth_y(W2, z)[1], z) for z in zs if z >= ZS - 1e-6]
    sec += [(RS * math.cos(a), ZC + RS * math.sin(a)) for a in arcs]
    sec += [(cloth_y(W2, z)[0] + cloth_y(W2, z)[1], z) for z in reversed(zs) if z >= ZS - 1e-6]
    for sx in (-1, 1):
        pp = Part()
        xa, xb = sx * (W2 - 0.0095), sx * (W2 - 0.0040)
        outer, inner = [], []
        for k, (y, z) in enumerate(sec):
            # outward normal of the section polyline (the average of the neighbouring segment normals)
            y0, z0 = sec[max(k - 1, 0)]
            y1, z1 = sec[min(k + 1, len(sec) - 1)]
            dy, dz = y1 - y0, z1 - z0
            n = math.hypot(dy, dz)
            ny, nz = dz / n, -dy / n
            if ny * (y - 0.0) + nz * (z - (ZC - 0.02)) < 0:
                ny, nz = -ny, -nz
            outer.append(((y + ny * 0.0020, z + nz * 0.0020), (y + ny * 0.0003, z + nz * 0.0003)))
        A = [(pp.vert((xa, o[0], o[1])), pp.vert((xb, o[0], o[1])), pp.vert((xb, i_[0], i_[1])), pp.vert((xa, i_[0], i_[1])))
             for o, i_ in outer]
        for k in range(len(A) - 1):
            for q in (0, 1, 3):   # outer face and the two side walls (the inner face lies on the cloth)
                r_ = (q + 1) % 4
                pp.face((A[k][q], A[k][r_], A[k + 1][r_], A[k + 1][q]),
                        [(q / 4, k / 10), (r_ / 4, k / 10), (r_ / 4, (k + 1) / 10), (q / 4, (k + 1) / 10)], GC, q in (0, 2))
        for end in (A[0], A[-1]):
            pp.face(end, [(0, 0), (1, 0), (1, 1), (0, 1)], GC)
        pp.emit(p)

    # rod: black lacquer, running into the brass caps
    rod = Part()
    lathe(rod, [(0, -0.300), (RR, -0.300), (RR, 0.300), (0, 0.300)], 12, LQ, axis="x", c=(0.0, 0.0, ZC))
    rod.emit(p)
    cap = [(0, 0.2965), (0.019, 0.2965), (0.0225, 0.2995), (0.0225, 0.3065), (0.0196, 0.3090), (0.0196, 0.3330),
           (0.0225, 0.3355), (0.0225, 0.3425), (0.0190, 0.3450), (0, 0.3450)]
    for sx in (-1, 1):
        cp = Part()
        prof = [(r, sx * h) for r, h in cap]
        lathe(cp, prof, 12, BR, axis="x", c=(0.0, 0.0, ZC))
        cp.emit(p)
    # cord loops round the bare rod, straight up into the ceiling: hung at BANNER_Z (+2.40) under the hero coffer the
    # ceiling the cords meet is the recessed plank panel, PANEL_Z0 above the ceiling line (both banners' cords land on
    # a plank, clear of the grooves), so they run 5 mm into it (hidden inside the scripted coffer's board otherwise)
    for sx in (-1, 1):
        x = sx * CORD_X
        ring = Part()
        maj, mn, tube = 8, 3, 0.0026
        R0 = RR + tube + 0.0004
        idx = []
        for i in range(maj):
            a = 2 * math.pi * i / maj
            row = []
            for j in range(mn):
                b = 2 * math.pi * j / mn + math.pi / 4
                rr = R0 + tube * math.cos(b)
                row.append(ring.vert((x + tube * math.sin(b), rr * math.cos(a), ZC + rr * math.sin(a))))
            idx.append(row)
        for i in range(maj):
            for j in range(mn):
                i2, j2 = (i + 1) % maj, (j + 1) % mn
                ring.face((idx[i][j], idx[i2][j], idx[i2][j2], idx[i][j2]),
                          [(i / maj, j / mn), ((i + 1) / maj, j / mn), ((i + 1) / maj, (j + 1) / mn), (i / maj, (j + 1) / mn)],
                          GC, True)
        ring.emit(p)
        cord = Part()
        ztop = 2.40 + PANEL_Z0 + 0.005
        lathe(cord, [(0, ZC + RR + 0.001), (0.0024, ZC + RR + 0.002), (0.0024, ztop - 0.0005), (0, ztop)], 6, GC,
              c=(x, 0.0, 0.0))
        cord.emit(p)
    # tassels: a short cord and bead under the hem corner, a woven knob, a collar and a stranded skirt
    # the skirt: 16 flat-shaded flutes read as the bundled strands; the head: collar, woven knob, cord and bead
    skirt = [(0, 0.0), (0.0200, 0.0030), (0.0268, 0.0180), (0.0235, 0.0700), (0.0160, 0.1300), (0, 0.1305)]
    head = [(0, 0.1280), (0.0172, 0.1300), (0.0172, 0.1440), (0.0130, 0.1470), (0.0195, 0.1560), (0.0212, 0.1680),
            (0.0165, 0.1810), (0.0050, 0.1880), (0.0032, 0.2050), (0.0058, 0.2100), (0, 0.2235)]
    for sx in (-1, 1):
        x = sx * TASSEL_X
        yc = cloth_y(x, ZB)[0]
        tp = Part()
        lathe(tp, skirt, 16, GC, c=(x, yc, 0.0), rfac=lambda k, i: 1.0 + 0.10 * (-1) ** i if 1 <= k <= 4 else 1.0,
              smooth=False)
        tp.emit(p)
        hp = Part()
        lathe(hp, head, 10, GC, c=(x, yc, 0.0), rfac=lambda k, i: 1.0 + 0.09 * (-1) ** (i + k) if 4 <= k <= 6 else 1.0)
        hp.emit(p)
    # the scripted banner's collision, unchanged
    return p.col(-0.345, 0.345, -0.03, 0.03, 0, 2.40)


# --------------------------------------------------------------------------- the coffer

# profile from the grid edge inward: (inset from the clear edge of the beam/rib, or None = grid edge; z; material of
# the segment to the next point)
COFFER_PROFILE = [
    (None, 0.200, T),     # outer wall of the coffer body (hidden under the beams / ribs / in the walls)
    (None, -0.060, T),    # outer soffit lip (6 cm showing past the beam), stepped as the sheet's dark frame band
    (0.024, -0.060, T),   # small step up
    (0.027, -0.051, T),
    (0.052, -0.051, T),   # bevel
    (0.060, -0.043, T),   # dark riser up into the cove
    (0.060, 0.026, LL),   # the warm LED line in the cove corner
    (0.074, 0.040, CG),   # the lit cove soffit
    (0.175, 0.040, CE),   # the lit outer face of the moulding
    (0.175, 0.000, CE),   # its lit bevel
    (0.183, -0.012, T),   # moulding frame underside (mitred at the corners)
    (0.212, -0.012, T),   # inner bevel
    (0.220, -0.004, T),   # inner face up
    (0.220, 0.052, T),    # small step
    (0.230, 0.062, T),    # reveal up to the panel backing
    (0.230, 0.140, None),
]
PANEL_Z0, PANEL_Z1 = 0.080, 0.145   # the plank panel: face 8 cm above the ceiling line, 9 cm above the moulding frame
GROOVE, PCH = 0.004, 0.004          # 8 mm V grooves between the planks


def coffer(P):
    c = P("SM_AK_Ceiling_Coffer_2x2")
    body = Part()
    loops, mats = [], []
    for d, z, m in COFFER_PROFILE:
        ix, iy = (0.0, 0.0) if d is None else (EX + d, EY + d)
        loops.append((ix, iy, 2 - ix, 2 - iy, z))
        mats.append(m)
    sweep_rect(body, loops, mats[:-1], caps=(T, T))
    body.emit(c)
    # the recessed panel: planks along X, grooves at the centre +/- 0.5 and 1.5 plank widths (sheet: a half plank at
    # each edge, three whole planks, the downlight in the middle of the centre plank)
    d_in = COFFER_PROFILE[-1][0]
    x0, x1 = EX + d_in - 0.005, 2 - EX - d_in + 0.005          # ends 5 mm into the reveal
    y0, y1 = EY + d_in + 0.003, 2 - EY - d_in - 0.003          # 3 mm shadow reveal along the long sides
    pw = (y1 - y0) / 4
    edges = [y0] + [1.0 + k * pw for k in (-1.5, -0.5, 0.5, 1.5)] + [y1]
    for k in range(5):
        a, b = edges[k], edges[k + 1]
        ga = GROOVE if k > 0 else 0.0
        gb = GROOVE if k < 4 else 0.0
        a, b = a + ga, b - gb
        ca, cb = (PCH if k > 0 else 0.002), (PCH if k < 4 else 0.002)
        sec = [(a, PANEL_Z1), (a, PANEL_Z0 + ca), (a + ca, PANEL_Z0), (b - cb, PANEL_Z0), (b, PANEL_Z0 + cb), (b, PANEL_Z1)]
        pl = Part()
        prism_x(pl, sec, x0, x1, T)
        pl.emit(c)
    return c.col(0, 2, 0, 2, -0.06, 0.20)   # the scripted coffer's collision, unchanged


def downlight(P):
    """The sheet's round downlight: a dark bronze trim ring 16 cm across, 12 mm proud of the panel, a brass bezel
    and a warm lens set 7 mm into it. Local origin: the coffer centre at the ceiling line (z 0 = CEIL)."""
    d = P("SM_AK_H_Ceiling_Downlight")
    z = PANEL_Z0
    prof = [(0, z + 0.004), (0.078, z + 0.004), (0.0800, z - 0.002), (0.0800, z - 0.006), (0.0775, z - 0.0105),
            (0.0710, z - 0.0120), (0.0640, z - 0.0120), (0.0610, z - 0.0090), (0.0580, z - 0.0055),
            (0.0545, z - 0.0050), (0, z - 0.0045)]
    mats = [BZ, BZ, BZ, BZ, BZ, BZ, BR, BR, BR, LED]
    lp = Part()
    lathe(lp, prof, 24, mats)
    lp.emit(d)
    return d.col(-0.08, 0.08, -0.08, 0.08, z - 0.012, z + 0.004)


def joint(P):
    """The sheet's frame-corner block, notched in plan (a block wrapping the beam crossed with one wrapping the rib),
    hanging 3-4 cm below the 40 cm beam, bevelled bottom edges. Local origin: the crossing at the ceiling line."""
    j = P("SM_AK_H_Ceiling_Joint")
    a = Part()
    block(a, 0.0, 0.0, 0.105, 0.160, -0.055, -0.440, 0.008, T)   # wraps the Beam_4 (25 cm, along X)
    a.emit(j)
    b = Part()
    block(b, 0.0, 0.0, 0.150, 0.135, -0.057, -0.422, 0.008, T)   # wraps the Rib_2 (16 cm, along Y)
    b.emit(j)
    return j.col(-0.15, 0.15, -0.16, 0.16, -0.44, -0.055)


def pieces(G):
    P = G["Piece"]
    return [banner(P), coffer(P), downlight(P), joint(P)]


def instances():
    """The new pieces, placed exactly where the kit's grid and lights() put them."""
    import armory_hero
    G = armory_hero.G
    ceil, room_w, room_l = G["CEIL"], G["ROOM_W"], G["ROOM_L"]
    lattice = G["LATTICE_COFFERS"]
    out = []
    for x in (3, 5, 7, 9):                          # lights(): Down_{x}_{y}
        for y in range(3, int(room_l), 2):
            if (x - 1, y - 1) in lattice:
                continue
            out.append(("SM_AK_H_Ceiling_Downlight", float(x), float(y), ceil, 0.0))
    for x in range(2, int(room_w), 2):              # Rib_2 lines x 2..10 cross the Beam_4 lines y 2..14
        for y in range(2, int(room_l), 2):
            out.append(("SM_AK_H_Ceiling_Joint", float(x), float(y), ceil, 0.0))
    return out
