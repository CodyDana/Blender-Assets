"""Hero pieces from the user's reference sheets WorkFiles/armory/reference/banner.png and ceiling_coffer.png:

SM_AK_Banner             the black silk banner: a two-layer cloth (0.55 x 1.65 m, 1 : 3.0) with soft vertical folds that
                         bow the side view into a shallow lens, wrapped round a round 2.7 cm black lacquer rod, polished
                         brass spool end caps with a 2.5 cm run of bare rod between cap and cloth (sheet), two fine black
                         silk cords from the bare rod up to a small ceiling rose at the ceiling line (the scripted banner's
                         cords, kept: it hangs from the ceiling), and a gold tassel under each
                         bottom corner (beaded cord, woven diamond-weave knot, collar, a skirt of light / dark gold
                         strands with a flat-cut end). The cloth keeps T_AK_Banner (the user's emblem and the gold border)
                         with remapped UVs: the emblem squeezed to 63 % of the width (round) with its centre 21.5 % down
                         the cloth, the side lines running up the sleeve, the small crests near the bottom skipped (the
                         sheet is plain there), and a geometry top line 1.6 cm under the rod
SM_AK_Ceiling_Coffer_2x2 the coffer between the Beam_4 / Rib_2 grid, from the grid edge inward: a dark soffit lip with an
                         upstand, a concealed thin LED line (1.4 cm, ~3000 K warm white, tilted 45 degrees up in a trough
                         behind the upstand: no line of sight from below) that WASHES a deep stepped timber cove (upper
                         soffit, riser, lower soffit, the moulding's outer face: brightest by the lip, falling off inward
                         and down, the grain visible in the lit wood), a 45-degree lip on the moulding's outer edge, a
                         two-step bevelled mitred moulding with a shadow step, and a recessed dark
                         timber panel of planks with soft V joints (4: half plank - 3 planks - half plank, as the sheet).
                         Timber UVs: U along the member / plank / side (T_AK_HTimber's grain runs along U).
                         The panel face is the ceiling line (z 0): the banner cords and the downlights sit on it.
                         No light fitting: only 22 of the 42 coffers get a Down_ spot in lights(), so the fitting is:
SM_AK_H_Ceiling_Downlight  NEW: the flush round downlight (dark bronze trim ring, thin brass bezel, a lens burning warm
                         white in the middle, amber toward the bezel) placed by instances() at exactly the lights() Down_
                         positions (x 3/5/7/9, y 3..15, not the lattice)
SM_AK_H_Ceiling_Joint    NEW: the sheet's corner blocks: a chunky two-tier cross-lap of laminated boards with vertical
                         splits and vertical grain (a beam cap lapped over a rib cap, 6.5 cm proud of the beam / rib
                         faces, and a bevelled block under the crossing: 3.4 / 4.9 / 7.8 cm below the beam soffit), at
                         every Beam_4 x Rib_2 crossing (x 2..10, y 2..14); plain members run into it (hero_shared)

Frames (the kit's): the banner is freestanding-centred, cloth facing -Y, tassel feet at z 0, cord roses at z 2.40 (the
ceiling line when hung at BANNER_Z); the coffer spans local 0-2 x 0-2 with z 0 = CEIL; the new pieces are centred on
their light / crossing with z 0 = CEIL.
"""
import math

import bmesh

ENABLED = False   # the user reviews images of every piece before anything goes into the armory

GC = "M_AK_HGoldCord"
GD = "M_AK_HGoldCordDk"
CD = "M_AK_HCord"
GV = "M_AK_HGroove"
LN = "M_AK_HLens"
LC = "M_AK_HLensCore"
CL = "M_AK_HCoveLED"
MATERIALS = {
    # warm gold silk cord, slightly glossy (the tassels): a light and a darker strand gold, so the skirt reads as
    # threads and the knot as a diamond weave
    GC: (None, 1.0, {"color": "#D2A043", "rough": 0.42, "metal": 0.45}),
    GD: (None, 1.0, {"color": "#9E7028", "rough": 0.50, "metal": 0.35}),
    # the fine black silk hanging cords
    CD: (None, 1.0, {"color": "#0D0B0A", "rough": 0.6}),
    # the dark shadow slots between the ceiling planks
    GV: (None, 1.0, {"color": "#0A0806", "rough": 0.9}),
    # the downlight lens: amber toward the bezel, a hot warm-white core
    LN: (None, 1.0, {"color": "#7A5A34", "emit": 4.0, "emit_color": "#FFC27A"}),
    LC: (None, 1.0, {"color": "#FFF0D8", "emit": 16.0, "emit_color": "#FFE4B8"}),
    # the concealed cove LED line (~3000 K warm white, NOT a saturated amber: the orange comes from the lit timber, so
    # the grain reads in the washed area): a 1.4 cm strip lying face-up in a trough behind the lip's upstand, never
    # seen from below; it washes the stepped cove soffit and the moulding face, falling off away from the lip
    CL: (None, 1.0, {"color": "#FFE0BC", "emit": 130.0, "emit_color": "#FFCF9C"}),
}
T, LQ, BR, BZ = "M_AK_Timber", "M_AK_Lacquer", "M_AK_Brass", "M_AK_Bronze"
LED, BN = "M_AK_LED", "M_AK_Banner"
LP = T   # the lit lip on the moulding edge
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


def lathe(part, profile, sides, mats, axis="z", c=(0.0, 0.0, 0.0), rfac=None, hoff=None, smooth=True, a0=0.0):
    """Surface of revolution. profile: [(r, h)], r == 0 -> pole. mats: one per segment (or one name).
    axis 'z': h is z; axis 'x': h is x, the circle in the y-z plane. rfac(k, i) scales ring k, vertex i (ridges, weave);
    hoff(k, i) shifts it along the axis (a ragged hem)."""
    if isinstance(mats, str):
        mats = [mats] * (len(profile) - 1)
    mfun = mats if callable(mats) else (lambda k, i: mats[k])   # mats(k, i): a per-face material (weave, strands)
    if isinstance(smooth, bool):
        smooth = [smooth] * (len(profile) - 1)
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
            hh = h + (hoff(k, i) if hoff else 0.0)
            if axis == "z":
                ring.append(part.vert((c[0] + rr * math.cos(a), c[1] + rr * math.sin(a), c[2] + hh)))
            else:
                ring.append(part.vert((c[0] + hh, c[1] + rr * math.cos(a), c[2] + rr * math.sin(a))))
        rings.append(ring)
    arc = [0.0]
    for k in range(1, len(profile)):
        arc.append(arc[-1] + math.dist(profile[k - 1], profile[k]))
    for k in range(len(profile) - 1):
        a, b = rings[k], rings[k + 1]
        for i in range(sides):
            j = (i + 1) % sides
            uv = [(i / sides, arc[k]), (j / sides, arc[k]), (j / sides, arc[k + 1]), (i / sides, arc[k + 1])]
            m = mfun(k, i)
            if profile[k][0] == 0:
                part.face((a[i], b[j], b[i]), [uv[0], uv[2], uv[3]], m, smooth[k])
            elif profile[k + 1][0] == 0:
                part.face((a[i], a[j], b[i]), [uv[0], uv[1], uv[3]], m, smooth[k])
            else:
                part.face((a[i], a[j], b[j], b[i]), uv, m, smooth[k])
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
            uvs = [((part.v[i][0] * d[0] + part.v[i][1] * d[1]) / tile,
                    arc[k if q < 2 else k + 1] / tile) for q, i in enumerate(ids)]
            part.face(ids, uvs, mats[k])
    for ring, m in ((L[0], caps[0]), (L[-1], caps[1])):
        if m:
            part.face(ring, [(part.v[i][0] / tile, part.v[i][1] / tile) for i in ring], m)
    return part


def prism_x(part, section, x0, x1, mats, tile=TILE_T, cap=None):
    """A closed prism along X with a convex (y, z) section: grain (texture v) along X, fan-triangulated caps.
    mats: one per section edge (or one name); cap: material of the two end caps."""
    n = len(section)
    if isinstance(mats, str):
        mats = [mats] * n
    a = [part.vert((x0, y, z)) for y, z in section]
    b = [part.vert((x1, y, z)) for y, z in section]
    arc = [0.0]
    for k in range(1, n + 1):
        arc.append(arc[-1] + math.dist(section[k - 1], section[k % n]))
    for k in range(n):
        j = (k + 1) % n
        part.face((a[k], a[j], b[j], b[k]),
                  [(x0 / tile, arc[k] / tile), (x0 / tile, arc[k + 1] / tile),
                   (x1 / tile, arc[k + 1] / tile), (x1 / tile, arc[k] / tile)], mats[k])
    for ring in (a, b):
        for k in range(1, n - 1):
            ids = (ring[0], ring[k], ring[k + 1])
            part.face(ids, [(part.v[i][1] / tile, part.v[i][2] / tile) for i in ids], cap or mats[0])
    return part


# --------------------------------------------------------------------------- the banner

W2 = 0.275             # cloth half width (the scripted 0.55 m; banner.png: the cloth is ~79 % of the rod-plus-caps)
ZC, RR = 1.871, 0.0135  # rod axis height and radius (sheet: a 2.7 cm rod); set by the 1 : 3.0 cloth over the tassels
RV = 0.019             # sleeve vertices round the rod (the 80-degree chords between them clear the rod by 1 mm)
ZS = ZC - 0.020        # sleeve seam: the cloth wraps the rod above it
FT = ZC + RV           # the visible top of the cloth (the sleeve over the rod)
ZL1 = ZC - RR - 0.016  # the top border line: its top edge 1.6 cm under the rod (sheet), 7.5 mm wide like the side lines
ZL0 = ZL1 - 0.0075
ZB = 0.240             # cloth bottom hem; the tassels hang below it to z 0 (sheet: ~14 % of the cloth height)
HF = FT - ZB           # cloth height 1.65 m: 1 : 3.0 (sheet 1 : 2.95, reference 2 1 : 3.9)
ZJ = ZB + 0.242        # V jumps over the texture's small crests here (the sheet is plain near the bottom)
DE = 0.63 * 2 * W2     # emblem ring 63 % of the cloth width (sheet 62-64 %)
ZE = FT - 0.215 * HF   # emblem centre 21.5 % down the cloth (sheet)
ET, EB = ZE + DE / 2, ZE - DE / 2
EV0, EV1 = 0.6274, 0.8091          # T_AK_Banner emblem rows (v) ...
EU0, EU1 = 0.1367, 0.8613          # ... and columns (u); side lines u 0.039-0.051 / 0.949-0.961
VS = 2.2               # true texture scale of the plain field, m per V
VSE = DE / (EV1 - EV0)  # the emblem's scale (round: the same m per texel in U and V)
FE = 0.5 - DE / (4 * W2)   # cloth fraction of the emblem's left edge (0.185)
# cloth columns (fractions of the width): fixed breakpoints for the emblem's U remap, 8 even columns across the emblem
FR = [0.0, 0.05, 0.10, FE] + [FE + (1 - 2 * FE) * k / 8 for k in range(1, 8)] + [1 - FE, 0.90, 0.95, 1.0]
NU = len(FR) - 1
CX = 0.2875            # the hanging cords sit on the bare rod between the cloth edge and the caps
TASSEL_X = W2 - 0.014  # tassels just inside the bottom corners (sheet)


def vmap(z, zmid):
    """T_AK_Banner V for a cloth height (zmid: the face's mid height, picks the band). Texture rows: bottom line
    v 0.010-0.013, small crests v 0.123-0.152 (skipped), emblem v 0.627-0.809, side lines end at v 0.977."""
    if zmid <= ZJ:
        return (z - ZB) / VS                                         # bottom band, true scale (v 0 - 0.110)
    if zmid <= EB:
        return 0.160 + (EV0 - 0.160) * (z - ZJ) / (EB - ZJ)          # plain field
    if zmid <= ET:
        return EV0 + (z - EB) / VSE                                  # the emblem, round
    return EV1 + (z - ET) / VS                                       # plain + side lines up into the sleeve (sheet)


def umap(f, emblem):
    """T_AK_Banner U for a cloth width fraction. In the emblem band the emblem is squeezed to 63 % of the width (the
    side lines stay where they are: identity outside f 0.10-0.90)."""
    if not emblem or f <= 0.10 or f >= 0.90:
        return f
    g = min(f, 1 - f)
    if g <= FE:
        u = 0.10 + (g - 0.10) * (EU0 - 0.10) / (FE - 0.10)
    else:
        u = EU0 + (g - FE) * (0.5 - EU0) / (0.5 - FE)
    return u if f <= 0.5 else 1 - u


def fold_amp(z):
    """Fold amplitude: gathers ~1.35 cm deep at mid height (the side view bows into a ~3 cm lens), weighted
    flatter at the hem, sewn flat under the top border line."""
    t = (z - ZB) / (ZS - ZB)
    flat = min(1.0, max(0.0, (ZL0 - 0.002 - z) / 0.12))
    return (0.003 + 0.0105 * math.sin(math.pi * t)) * flat


def cloth_y(x, z):
    """Centre line of the two cloth layers (3 soft vertical folds, zero at both side edges) and the half gap."""
    return fold_amp(z) * math.sin(2 * math.pi * (x + W2) / (2 * W2 / 3)), 0.002


def banner(P):
    p = P("SM_AK_Banner")
    zs = [ZB, ZJ, 0.80, 1.13, EB, ZE, ET, ZL0, ZS]
    xs = [-W2 + 2 * W2 * f for f in FR]
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
    for r in range(len(zs) - 1):
        zm = (zs[r] + zs[r + 1]) / 2
        v0, v1 = vmap(zs[r], zm), vmap(zs[r + 1], zm)
        uf = [umap(f, EB < zm < ET) for f in FR]
        for i in range(NU):
            cl.face((F[r][i], F[r][i + 1], F[r + 1][i + 1], F[r + 1][i]),
                    [(uf[i], v0), (uf[i + 1], v0), (uf[i + 1], v1), (uf[i], v1)], BN, True)
            cl.face((B[r][i], B[r + 1][i], B[r + 1][i + 1], B[r][i + 1]),     # the back reads the right way round
                    [(1 - uf[i], v0), (1 - uf[i], v1), (1 - uf[i + 1], v1), (1 - uf[i + 1], v0)], BN, True)
        for i, u in ((0, 0.006), (NU, 0.994)):   # closed side edges below the sleeve seam (a black hem)
            cl.face((F[r][i], F[r + 1][i], B[r + 1][i], B[r][i]), [(u, v0), (u, v1), (u + 0.002, v1), (u + 0.002, v0)],
                    BN, False)
    for i in range(NU):   # bottom hem
        cl.face((F[0][i], B[0][i], B[0][i + 1], F[0][i + 1]),
                [(FR[i], 0.003), (FR[i], 0.006), (FR[i + 1], 0.006), (FR[i + 1], 0.003)], BN, False)
    # the sleeve: front seam row -> round the rod (4 rows, 80 deg apart, 3.5 mm off it) -> back seam row; the side
    # lines run up it to the rod (sheet)
    angs = [math.radians(a) for a in (210, 130, 50, -30)]
    rows = [F[-1]] + [[cl.vert((x, RV * math.cos(a), ZC + RV * math.sin(a))) for x in xs] for a in angs] + [B[-1]]
    v_s = vmap(ZS, ZS + 0.01)
    vv = [v_s + 0.002 * q for q in (0, 1, 2, 2, 1, 0)]
    for r in range(len(rows) - 1):
        for i in range(NU):
            cl.face((rows[r][i], rows[r][i + 1], rows[r + 1][i + 1], rows[r + 1][i]),
                    [(FR[i], vv[r]), (FR[i + 1], vv[r]), (FR[i + 1], vv[r + 1]), (FR[i], vv[r + 1])], BN, True)
    cl.emit(p)

    # the top border line (T_AK_Banner has the side and bottom lines only): a 7.5 mm strip on both faces between the
    # side lines, mapped onto the texture's own vertical border line so the embroidery matches the other three lines
    xl = W2 * (1 - 2 * 20.0 / 512)
    for side in (-1, 1):
        st = Part()
        y = side * (0.002 + 0.0006)
        q = [st.vert((-xl, y, ZL0)), st.vert((xl, y, ZL0)), st.vert((xl, y, ZL1)), st.vert((-xl, y, ZL1))]
        u0, u1 = 20.5 / 512, 25.5 / 512
        st.face(q, [(u0, 0.30), (u0, 0.70), (u1, 0.70), (u1, 0.30)], BN)
        if side > 0:   # the back strip faces +Y
            st.f[-1] = tuple(reversed(st.f[-1]))
            st.uv[-1] = list(reversed(st.uv[-1]))
        st.emit(p, orient=False)

    # rod: black lacquer, running into the caps (a 2.5 cm run of bare rod between the cloth and each cap, as the sheet)
    rod = Part()
    lathe(rod, [(0, -0.305), (RR, -0.305), (RR, 0.305), (0, 0.305)], 10, LQ, axis="x", c=(0.0, 0.0, ZC))
    rod.emit(p)
    # polished brass end caps (sheet): a 4.5 cm spool, a rounded lip ring at each end round a slim waist
    cap = [(0, 0.300), (0.0220, 0.300), (0.0220, 0.3085), (0.0194, 0.3110), (0.0194, 0.3340), (0.0220, 0.3365),
           (0.0220, 0.345), (0, 0.345)]
    for sx in (-1, 1):
        cp = Part()
        lathe(cp, [(r, sx * h) for r, h in cap], 10, BR, axis="x", c=(0.0, 0.0, ZC),
              smooth=[False, True, False, True, False, True, False])
        cp.emit(p)
    # two fine black silk hanging cords from the bare rod to the ceiling line (tied round the rod; a small black
    # ceiling rose 1 mm into the coffer panel at +2.40), as the scripted banner's cords
    for sx in (-1, 1):
        x = sx * CX
        kn = Part()
        lathe(kn, [(RR + 0.0002, -0.0035), (RR + 0.0028, -0.0022), (RR + 0.0028, 0.0022), (RR + 0.0002, 0.0035)], 6,
              CD, axis="x", c=(x, 0.0, ZC), smooth=True)
        kn.emit(p, orient=False)
        cd = Part()
        lathe(cd, [(0, ZC + RR - 0.001), (0.0018, ZC + RR - 0.001), (0.0018, 2.3955), (0, 2.3955)], 6, CD,
              c=(x, 0.0, 0.0), smooth=[False, True, False])
        cd.emit(p)
        fl = Part()
        lathe(fl, [(0, 2.395), (0.0085, 2.395), (0.0085, 2.401), (0, 2.401)], 8, LQ, c=(x, 0.0, 0.0),
              smooth=[False, True, False])
        fl.emit(p)
    # tassels under the bottom corners (sheet): a beaded cord, a woven 'pineapple' knot with a diamond weave, a collar
    # and a long skirt of fine gold threads (alternating light / dark strands) with a flat-cut end
    skirt = [(0, 0.0006), (0.0272, 0.0), (0.0224, 0.080), (0.0168, 0.150), (0, 0.1505)]
    collar = [(0, 0.1475), (0.0188, 0.1475), (0.0188, 0.1660), (0, 0.1660)]
    knot = [(0, 0.1655), (0.0135, 0.1680), (0.0205, 0.1750), (0.0225, 0.1860), (0.0205, 0.1970), (0.0140, 0.2050),
            (0.0060, 0.2105), (0, 0.2110)]
    neck = [(0, 0.2100), (0.0050, 0.2112), (0.0056, 0.2165), (0.0030, 0.2205), (0.0030, ZB + 0.0005),
            (0, ZB + 0.0005)]   # a bead and the hanging cord

    def strands(k, i):   # fine thread ridges down the skirt (32 facets: 16 bundles)
        if k in (1, 2):
            return 1.09 if i % 2 else 0.91
        if k == 3:
            return 1.05 if i % 2 else 0.95
        return 1.0

    def weave(k, i):     # the woven knot: a checker of bumps -> diamond facets
        return 1.0 + 0.09 * (-1) ** (i + k) if 1 <= k <= 6 else 1.0

    def thread(k, i):    # light / dark gold strands; the flat-cut end in the darker gold
        return GD if k == 0 or i % 2 == 0 else GC

    def diamond(k, i):
        return GC if (i + k) % 2 else GD

    for sx in (-1, 1):
        x = sx * TASSEL_X
        y = cloth_y(x, ZB)[0]   # hangs from the middle of the hem, between the two cloth layers
        tp = Part()
        lathe(tp, skirt, 32, thread, c=(x, y, 0.0), rfac=strands, smooth=[False, True, True, False])
        lathe(tp, collar, 12, GC, c=(x, y, 0.0), smooth=[False, True, False])
        lathe(tp, knot, 12, diamond, c=(x, y, 0.0), rfac=weave, smooth=True)
        lathe(tp, neck, 6, GC, c=(x, y, 0.0))
        tp.emit(p)
    # the scripted banner's collision, unchanged
    return p.col(-0.345, 0.345, -0.03, 0.03, 0, 2.40)


# --------------------------------------------------------------------------- the coffer

# profile from the grid edge inward: (inset from the clear edge of the beam/rib, or None = grid edge; z; material of
# the segment to the next point). z 0 is the ceiling line = the plank panel face.
COFFER_PROFILE = [
    (None, 0.200, T),     # outer wall of the coffer body (hidden under the beams / ribs / in the walls)
    (None, -0.165, T),    # soffit lip (5 cm showing past the beam / rib), 16.5 cm below the panel
    (0.046, -0.165, T),   # bevel
    (0.054, -0.157, T),   # inner face of the lip, up to the upstand
    (0.054, -0.094, T),   # upstand chamfer
    (0.050, -0.090, T),   # upstand top (faces up: never seen from below)
    (0.042, -0.090, T),   # back of the upstand, down into the LED trough
    (0.042, -0.104, CL),  # the concealed LED line: 1.4 cm, tilted 45 degrees up toward the cove, its top 4 mm below
    (0.032, -0.094, T),   # the upstand's top (no line of sight from below); trough back wall up, 14 cm into a deep
    (0.032, 0.045, T),    # cove (so the line's light spreads across the soffit instead of one hot stripe)
    (0.100, 0.045, T),    # upper cove soffit: brightest near the lip, falling off inward; step riser down (faces the
    (0.100, 0.030, T),    # strip: catches it)
    (0.170, 0.030, T),    # lower cove soffit, dimmer; the moulding's outer face down (washed at the top, falling off
                          # down to the upstand's shadow line)
    (0.170, -0.094, LP),  # the lip: a 2.3 cm 45-degree flat on the moulding's outer edge (bounce light from the cove)
    (0.193, -0.117, T),   # small round
    (0.196, -0.120, T),   # moulding underside, first step (mitred at the corners)
    (0.204, -0.120, T),   # bevel
    (0.207, -0.117, T),   # shadow step up
    (0.207, -0.101, T),   # second step
    (0.214, -0.101, T),   # bevel
    (0.220, -0.095, T),   # inner face of the moulding, up
    (0.220, -0.010, T),   # shadow reveal
    (0.228, -0.004, T),   # wall up past the panel face (the plank ends run into it)
    (0.228, 0.090, None),
]
PANEL_Z0, PANEL_Z1 = 0.0, 0.065   # the plank panel: face on the ceiling line
GROOVE, PCH = 0.001, 0.004        # soft V joints: 4 mm timber arrises round a 2 mm shadow slot


def coffer(P):
    c = P("SM_AK_Ceiling_Coffer_2x2")
    body = Part()
    loops, mats = [], []
    for d, z, m in COFFER_PROFILE:
        ix, iy = (0.0, 0.0) if d is None else (EX + d, EY + d)
        loops.append((ix, iy, 2 - ix, 2 - iy, z))
        mats.append(m)
    sweep_rect(body, loops, mats[:-1], caps=(T, GV))   # the cap over the panel shows only down the joints: dark
    body.emit(c)
    # the recessed panel: planks along X, joints at the centre +/- 0.5 and 1.5 plank widths (sheet: a half plank at
    # each edge, three whole planks, the downlight in the middle of the centre plank)
    d_in = COFFER_PROFILE[-1][0]
    x0, x1 = EX + d_in - 0.005, 2 - EX - d_in + 0.005          # ends 5 mm into the wall
    y0, y1 = EY + d_in - 0.005, 2 - EY - d_in + 0.005
    pw = (2 - 2 * EY - 2 * d_in) / 4
    edges = [y0] + [1.0 + k * pw for k in (-1.5, -0.5, 0.5, 1.5)] + [y1]
    for k in range(5):
        a, b = edges[k], edges[k + 1]
        ga = GROOVE if k > 0 else 0.0
        gb = GROOVE if k < 4 else 0.0
        a, b = a + ga, b - gb
        ca, cb = (PCH if k > 0 else 0.0015), (PCH if k < 4 else 0.0015)
        sec = [(a, PANEL_Z1), (a, PANEL_Z0 + ca), (a + ca, PANEL_Z0), (b - cb, PANEL_Z0), (b, PANEL_Z0 + cb), (b, PANEL_Z1)]
        pm = [GV if k > 0 else T, T, T, T, GV if k < 4 else T, T]
        pl = Part()
        prism_x(pl, sec, x0, x1, pm, cap=T)
        pl.emit(c)
    return c.col(0, 2, 0, 2, -0.06, 0.20)   # the scripted coffer's collision, unchanged


def downlight(P):
    """The sheet's flush round downlight: a dark bronze trim ring 15 cm across, 11 mm proud of the panel, a thin brass
    inner bezel and a lens set up into it that burns warm white in the middle, amber toward the bezel. Local origin:
    the coffer centre at the ceiling line."""
    d = P("SM_AK_H_Ceiling_Downlight")
    z = PANEL_Z0
    prof = [(0, z + 0.004), (0.0735, z + 0.004), (0.0755, z + 0.001), (0.0755, z - 0.005), (0.0715, z - 0.010),
            (0.0600, z - 0.011), (0.0565, z - 0.009), (0.0550, z - 0.006), (0.0515, z - 0.005), (0.0505, z - 0.001),
            (0.0290, z - 0.001), (0, z - 0.001)]
    mats = [BZ, BZ, BZ, BZ, BZ, BR, BR, BR, BZ, LN, LC]
    lp = Part()
    lathe(lp, prof, 24, mats, smooth=[False, False, True, True, False, True, True, False, False, False, False])
    lp.emit(d)
    return d.col(-0.0755, 0.0755, -0.0755, 0.0755, z - 0.011, z + 0.004)


def kerf_rect(hx, hy, kx=(0.0,), ky=(0.0,), kw=0.003, kd=0.004):
    """A rectangle +-hx, +-hy in plan, CCW, with a vertical V kerf (half width kw, depth kd) at each x in kx on the
    two long faces and at each y in ky on the two end faces: the splits between the laminated boards."""
    pts = [(-hx, -hy)]
    pts += [q for x in kx for q in ((x - kw, -hy), (x, -hy + kd), (x + kw, -hy))]
    pts.append((hx, -hy))
    pts += [q for y in ky for q in ((hx, y - kw), (hx - kd, y), (hx, y + kw))]
    pts.append((hx, hy))
    pts += [q for x in reversed(kx) for q in ((x + kw, hy), (x, hy - kd), (x - kw, hy))]
    pts.append((-hx, hy))
    pts += [q for y in reversed(ky) for q in ((-hx, y + kw), (-hx + kd, y), (-hx, y - kw))]
    return pts


def sweep_block(part, loops, mat, tile=TILE_T, kx=(0.0,), ky=(0.0,)):
    """Loft kerf_rect outlines down through loops [(hx, hy, z)] (the kerfs keep their size, so the bevel loops only
    pull the flat faces in); both ends fan-capped from the centre (the outline is star-shaped)."""
    L = []
    for hx, hy, z in loops:
        L.append([part.vert((x, y, z)) for x, y in kerf_rect(hx, hy, kx, ky)])
    n = len(L[0])
    for k in range(len(loops) - 1):
        for s in range(n):
            t = (s + 1) % n
            ids = (L[k][s], L[k][t], L[k + 1][t], L[k + 1][s])
            p, q = part.v[ids[0]], part.v[ids[1]]
            along = 0 if abs(q[0] - p[0]) > abs(q[1] - p[1]) else 1
            part.face(ids, [(part.v[i][2] / tile, part.v[i][along] / tile) for i in ids], mat)   # grain (U) runs down
    for R, (hx, hy, z) in ((L[0], loops[0]), (L[-1], loops[-1])):
        cidx = part.vert((0.0, 0.0, z))
        ax = 0 if hx >= hy else 1   # the end faces: the grain (U) along the block's longer side
        for s in range(n):
            ids = (cidx, R[s], R[(s + 1) % n])
            part.face(ids, [(part.v[i][ax] / tile, part.v[i][1 - ax] / tile) for i in ids], mat)
    return part


JB = 0.065   # the joint's cross-lap bars stand 6.5 cm proud of the beam / rib side faces


def joint(P):
    """The sheet's corner blocks at a Beam_4 x Rib_2 crossing: a chunky two-tier cross-lap of laminated boards with
    vertical splits (the plain beams / ribs of the shared pass run into it).
    Tier 1 is a cross in plan: a beam cap (long in X) 6.5 cm proud of the beam faces and running 6 cm past the rib cap,
    lapped over a rib cap (long in Y) 6.5 cm proud of the rib faces and running 6.5 cm past the beam cap; the rib cap
    drops 1.5 cm lower, so the lap reads. Tier 2 is a bevelled square block under the crossing. The beam cap stands
    3.4 cm, the rib cap 4.9 cm and tier 2 7.8 cm below the beam soffit (-0.40). Local origin: the crossing at the
    ceiling line; the tops (-0.160 / -0.162: no shared cap centre vertex) sit 3-5 mm up into the coffer lips (their
    undersides are at -0.165)."""
    j = P("SM_AK_H_Ceiling_Joint")
    bx, by = EX + JB + 0.060, EY + JB             # beam cap: 0.205 x 0.190 half
    rx, ry = EX + JB, EY + JB + 0.065             # rib cap:  0.145 x 0.255 half
    bc = Part()
    sweep_block(bc, [(bx, by, -0.160), (bx, by, -0.430), (bx - 0.004, by - 0.004, -0.434)], T,
                kx=(-0.068, 0.068), ky=(0.0,))
    bc.emit(j)
    rc = Part()
    sweep_block(rc, [(rx, ry, -0.162), (rx, ry, -0.445), (rx - 0.004, ry - 0.004, -0.449)], T,
                kx=(0.0,), ky=(-0.085, 0.085))
    rc.emit(j)
    t2 = Part()
    sweep_block(t2, [(0.115, 0.135, -0.447), (0.115, 0.135, -0.472), (0.109, 0.129, -0.478)], T)
    t2.emit(j)
    return j.col(-bx, bx, -by, by, -0.434, -0.160).col(-rx, rx, -ry, ry, -0.449, -0.162).col(
        -0.115, 0.115, -0.135, 0.135, -0.478, -0.447)


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
