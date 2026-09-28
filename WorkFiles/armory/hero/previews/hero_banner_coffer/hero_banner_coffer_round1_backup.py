"""Hero pieces from the user's reference sheets WorkFiles/armory/reference/banner.png and ceiling_coffer.png:

SM_AK_Banner             the black silk banner: a two-layer cloth with soft vertical folds that bow the side view into a
                         shallow lens, wrapped tight round a round black lacquer rod (the top border line ~1 cm under
                         the rod), plain brass end caps with one lip ring and a short run of bare rod between cap and
                         cloth, two slim brass hanger rods (rod brackets) from the rod up to the ceiling line, and a
                         gold tassel (cord, bead, woven ball knot, collar, stranded skirt flaring to a ragged hem)
                         under each bottom corner. The cloth keeps T_AK_Banner (the user's emblem and the gold border)
                         with a remapped V: the emblem sits high (centre ~19 % down the cloth, as the sheet), the plain
                         field is stretched, and the small crests near the bottom are skipped (the sheet is plain there)
SM_AK_Ceiling_Coffer_2x2 the coffer between the Beam_4 / Rib_2 grid, from the grid edge inward: a dark soffit lip, a cove
                         washed by a hidden warm LED strip (tucked in a pocket behind the lip: real light on the
                         timber, brightest at the source and fading across the cove soffit onto the moulding face),
                         a two-step bevelled mitred moulding frame with a shadow step, and a recessed dark timber
                         panel of planks with dark shadow joints (4: half plank - 3 planks - half plank, as the sheet).
                         The panel face is the ceiling line (z 0): the banner hangers and the downlights sit on it.
                         No light fitting: only 22 of the 42 coffers get a Down_ spot in lights(), so the fitting is:
SM_AK_H_Ceiling_Downlight  NEW: the flush round downlight (dark bronze trim ring, thin brass bezel, amber lens) placed
                         by instances() at exactly the lights() Down_ positions (x 3/5/7/9, y 3..15, not the lattice)
SM_AK_H_Ceiling_Joint    NEW: the sheet's two-tier notched joint block (a plus in plan: the crossing members' ends run
                         7.5 cm past both beam faces, a laminated seam round the upper tier, a smaller notched cap
                         under the beam), at every Beam_4 x Rib_2 crossing (x 2..10, y 2..14)

Frames (the kit's): the banner is freestanding-centred, cloth facing -Y, tassel feet at z 0, hanger tops at z 2.40 (the
ceiling line when hung at BANNER_Z); the coffer spans local 0-2 x 0-2 with z 0 = CEIL; the new pieces are centred on
their light / crossing with z 0 = CEIL.
"""
import math

import bmesh

ENABLED = False   # the user reviews images of every piece before anything goes into the armory

GC = "M_AK_HGoldCord"
GV = "M_AK_HGroove"
LN = "M_AK_HLens"
CL = "M_AK_HCoveLED"
MATERIALS = {
    # gold silk cord: the tassels (a soft sheen, not polished brass)
    GC: (None, 1.0, {"color": "#B88C3C", "rough": 0.62, "metal": 0.25}),
    # the dark shadow joints between the ceiling planks (the walls and arrises of the V grooves)
    GV: (None, 1.0, {"color": "#0A0806", "rough": 0.9}),
    # the downlight lens: a warm amber glow (M_AK_LED burns to cream at this size)
    LN: (None, 1.0, {"color": "#7A4A1C", "emit": 1.1, "emit_color": "#FF9422"}),
    # the hidden cove LED strip: bright enough to wash the timber cove and the moulding face with real light (it is
    # tucked in a pocket behind the soffit lip, out of sight from below)
    CL: (None, 1.0, {"color": "#FFB060", "emit": 60.0, "emit_color": "#FFA850"}),
}
T, LQ, BR, BZ = "M_AK_Timber", "M_AK_Lacquer", "M_AK_Brass", "M_AK_Bronze"
LED, BN = "M_AK_LED", "M_AK_Banner"
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
            if profile[k][0] == 0:
                part.face((a[i], b[j], b[i]), [uv[0], uv[2], uv[3]], mats[k], smooth[k])
            elif profile[k + 1][0] == 0:
                part.face((a[i], a[j], b[i]), [uv[0], uv[1], uv[3]], mats[k], smooth[k])
            else:
                part.face((a[i], a[j], b[j], b[i]), uv, mats[k], smooth[k])
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
                  [(arc[k] / tile, x0 / tile), (arc[k + 1] / tile, x0 / tile),
                   (arc[k + 1] / tile, x1 / tile), (arc[k] / tile, x1 / tile)], mats[k])
    for ring in (a, b):
        for k in range(1, n - 1):
            ids = (ring[0], ring[k], ring[k + 1])
            part.face(ids, [(part.v[i][1] / tile, part.v[i][2] / tile) for i in ids], cap or mats[0])
    return part


def plus_outline(A, a, B, b):
    """A plus / notched square in plan, CCW: an arm +-A along X (half width b) crossed with an arm +-B along Y (half
    width a). Returns the 12 outline points."""
    return [(A, -b), (A, b), (a, b), (a, B), (-a, B), (-a, b), (-A, b), (-A, -b), (-a, -b), (-a, -B), (a, -B), (a, -b)]


def offset_outline(pts, d):
    """Inset a right-angled CCW outline by d (outward edge normals, summed per vertex)."""
    n = len(pts)
    out = []
    for i in range(n):
        p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % n]
        e0 = (p1[0] - p0[0], p1[1] - p0[1])
        e1 = (p2[0] - p1[0], p2[1] - p1[1])
        n0 = (e0[1] / math.hypot(*e0), -e0[0] / math.hypot(*e0))
        n1 = (e1[1] / math.hypot(*e1), -e1[0] / math.hypot(*e1))
        out.append((p1[0] - d * (n0[0] + n1[0]), p1[1] - d * (n0[1] + n1[1])))
    return out


def sweep_plus(part, loops, mats, tile=TILE_T):
    """Loft a plus outline down through loops [(A, a, B, b, inset, z)], mats one per band; both ends capped with
    five quads (the centre square and the four arms, sharing the outline's vertices: no T-junctions)."""
    L = []
    for (A, a, B, b, d, z) in loops:
        pts = offset_outline(plus_outline(A, a, B, b), d)
        L.append([part.vert((x, y, z)) for x, y in pts])
    for k in range(len(loops) - 1):
        for s in range(12):
            t = (s + 1) % 12
            ids = (L[k][s], L[k][t], L[k + 1][t], L[k + 1][s])
            p, q = part.v[ids[0]], part.v[ids[1]]
            along = 0 if abs(q[0] - p[0]) > abs(q[1] - p[1]) else 1
            uvs = [(part.v[i][2] / tile, part.v[i][along] / tile) for i in ids]
            part.face(ids, uvs, mats[k])
    for R in (L[0], L[-1]):
        # outline index: 0 (A,-b) 1 (A,b) 2 (a,b) 3 (a,B) 4 (-a,B) 5 (-a,b) 6 (-A,b) 7 (-A,-b) 8 (-a,-b) 9 (-a,-B)
        # 10 (a,-B) 11 (a,-b)
        for q in ((11, 2, 5, 8), (0, 1, 2, 11), (2, 3, 4, 5), (8, 5, 6, 7), (10, 11, 8, 9)):
            ids = [R[i] for i in q]
            part.face(ids, [(part.v[i][0] / tile, part.v[i][1] / tile) for i in ids], mats[0])
    return part


# --------------------------------------------------------------------------- the banner

W2 = 0.275             # cloth half width (the scripted 0.55 m)
ZC, RR = 2.232, 0.016  # rod axis height and radius (the scripted rod box 2.215-2.25)
RV = 0.0195            # sleeve vertices round the rod (the chords between them clear the rod by ~0.8 mm)
ZS = ZC - 0.022        # sleeve seam: the cloth wraps the rod tightly above it
ZL0, ZL1 = ZC - 0.0335, ZC - 0.026   # the top border line (7.5 mm, ~1 cm under the rod)
ZB = 0.216             # cloth bottom hem; the tassels hang below it to z 0
ZJ = ZB + 0.242        # V jumps over the texture's small crests here (the sheet is plain near the bottom)
ET, EB = ZC - 0.19, ZC - 0.59    # emblem band (true scale): ring top ~9 %, centre ~19 % of the cloth below the rod
VS = 2.2               # true texture scale, m per V (T_AK_Banner 512 x 2048 over 0.55 x 2.2 m)
HX = 0.2875            # the hanger rods sit on the bare rod between the cloth edge and the caps
TASSEL_X = W2 - 0.006
NU = 15                # cloth columns: 3 folds, 5 columns each


def vmap(z, zmid):
    """T_AK_Banner V for a cloth height (zmid: the face's mid height, picks the band). Texture rows: bottom line
    v 0.010-0.013, small crests v 0.123-0.152 (skipped), emblem v 0.627-0.809, side lines end at v 0.977."""
    if zmid <= ZJ:
        return (z - ZB) / VS                                         # bottom band, true scale (v 0 - 0.110)
    if zmid <= EB:
        return 0.160 + (0.627 - 0.160) * (z - ZJ) / (EB - ZJ)        # plain field (stretched 15 %)
    if zmid <= ET:
        return 0.627 + (z - EB) / VS                                 # the emblem, true scale (round)
    if zmid <= ZL0:
        return 0.809 + (0.9735 - 0.809) * (z - ET) / (ZL0 - ET)      # the side lines run up to the top border line
    return 0.9735 + (0.990 - 0.9735) * (z - ZL0) / (ZS - ZL0)        # under the top line and the sleeve: black


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
    zs = [ZB, ZJ, 0.75, 1.05, 1.35, EB, (EB + ET) / 2, ET, ZL0, ZS]
    xs = [-W2 + 2 * W2 * i / NU for i in range(NU + 1)]
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
        zm = (zs[r] + zs[r + 1]) / 2
        v0, v1 = vmap(zs[r], zm), vmap(zs[r + 1], zm)
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
                [(uf[i], 0.003), (uf[i], 0.006), (uf[i + 1], 0.006), (uf[i + 1], 0.003)], BN, False)
    # the sleeve: front seam row -> round the rod (5 rows, 60 deg apart, 3.5 mm off it) -> back seam row
    angs = [math.radians(a) for a in (210, 150, 90, 30, -30)]
    rows = [F[-1]] + [[cl.vert((x, RV * math.cos(a), ZC + RV * math.sin(a))) for x in xs] for a in angs] + [B[-1]]
    vv = [0.990, 0.993, 0.996, 0.999, 0.996, 0.993, 0.990]
    for r in range(len(rows) - 1):
        for i in range(NU):
            cl.face((rows[r][i], rows[r][i + 1], rows[r + 1][i + 1], rows[r + 1][i]),
                    [(uf[i], vv[r]), (uf[i + 1], vv[r]), (uf[i + 1], vv[r + 1]), (uf[i], vv[r + 1])], BN, True)
    cl.emit(p)

    # the top border line (T_AK_Banner has the side and bottom lines only): a 7.5 mm strip on both faces, mapped onto
    # the texture's own vertical border line so the embroidery matches the other three lines
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

    # rod: black lacquer, running into the caps
    rod = Part()
    lathe(rod, [(0, -0.300), (RR, -0.300), (RR, 0.300), (0, 0.300)], 10, LQ, axis="x", c=(0.0, 0.0, ZC))
    rod.emit(p)
    # plain brass end caps: a cylinder with one small lip ring on the inner side
    cap = [(0, 0.2995), (0.0215, 0.2995), (0.0215, 0.3045), (0.0195, 0.3050), (0.0195, 0.3420), (0.0172, 0.3450),
           (0, 0.3450)]
    for sx in (-1, 1):
        cp = Part()
        lathe(cp, [(r, sx * h) for r, h in cap], 10, BR, axis="x", c=(0.0, 0.0, ZC),
              smooth=[True, False, True, True, True, True])
        cp.emit(p)
    # rod brackets: a saddle band round the bare rod, a slim brass drop rod and a small ceiling flange (its top 1 mm
    # into the ceiling panel at +2.40)
    for sx in (-1, 1):
        x = sx * HX
        sd = Part()
        lathe(sd, [(RR + 0.0003, -0.003), (RR + 0.0028, -0.003), (RR + 0.0028, 0.003), (RR + 0.0003, 0.003)], 8, BR,
              axis="x", c=(x, 0.0, ZC), smooth=[False, True, False])
        sd.emit(p, orient=False)
        dr = Part()
        lathe(dr, [(0.0022, ZC + RR + 0.0012), (0.0022, 2.395)], 6, BR, c=(x, 0.0, 0.0))
        dr.emit(p, orient=False)
        fl = Part()
        lathe(fl, [(0, 2.3945), (0.0125, 2.3945), (0.0130, 2.3965), (0.0130, 2.401), (0, 2.401)], 8, BR,
              c=(x, 0.0, 0.0), smooth=[False, True, True, False])
        fl.emit(p)
    # tassels under the bottom corners: a short cord and bead, a woven ball knot, a collar and a skirt of fine strands
    # flaring to a ragged hem (loose strand ends)
    skirt = [(0, 0.012), (0.0245, 0.0), (0.0228, 0.028), (0.0175, 0.085), (0.0135, 0.126), (0, 0.128)]
    knot = [(0, 0.1395), (0.0105, 0.1405), (0.0170, 0.1465), (0.0205, 0.1555), (0.0210, 0.1650), (0.0182, 0.1745),
            (0.0112, 0.1810), (0, 0.1830)]
    collar = [(0, 0.1235), (0.0182, 0.1235), (0.0182, 0.1410), (0, 0.1410)]
    neck = [(0, 0.1810), (0.0030, 0.1820), (0.0066, 0.1960), (0.0066, 0.2010), (0.0030, 0.2050),
            (0.0030, ZB + 0.0005), (0, ZB + 0.0005)]

    def strands(k, i):   # fine ridges down the skirt (16 strand bundles)
        return 1.0 + (0.16 if i % 2 else -0.16) if 1 <= k <= 4 else 1.0

    def ragged(k, i):    # loose strand ends: the hem ring zig-zags a few mm
        return (0.0015, 0.0, 0.0045, 0.0005, 0.0030, 0.0)[i % 6] if k == 1 else 0.0

    def weave(k, i):     # the woven knot: a checker of bumps
        return 1.0 + 0.07 * (-1) ** (i + k) if 2 <= k <= 5 else 1.0

    for sx in (-1, 1):
        x = sx * TASSEL_X
        y = cloth_y(x, ZB)[0]   # hangs from the middle of the hem, between the two cloth layers
        tp = Part()
        lathe(tp, skirt, 16, GC, c=(x, y, 0.0), rfac=strands, hoff=ragged)
        lathe(tp, collar, 10, GC, c=(x, y, 0.0), smooth=[False, True, False])
        lathe(tp, knot, 12, GC, c=(x, y, 0.0), rfac=weave)
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
    (0.054, -0.157, T),   # inner face of the lip, up
    (0.054, -0.077, CL),   # the hidden warm LED strip lying on top of the lip, facing up into the cove: never seen
    (0.044, -0.077, T),   # from below, it washes the cove soffit and the moulding face
    (0.044, -0.025, T),   # the cove soffit, washed by the strip
    (0.170, -0.025, T),   # the moulding's outer face (lit by the strip across the cove)
    (0.170, -0.124, T),   # bevel
    (0.176, -0.130, T),   # moulding underside, first step (mitred at the corners)
    (0.194, -0.130, T),   # bevel
    (0.198, -0.126, T),   # shadow step up
    (0.198, -0.101, T),   # second step
    (0.216, -0.101, T),   # bevel
    (0.220, -0.097, T),   # inner face of the moulding, up
    (0.220, -0.010, T),   # shadow reveal
    (0.228, -0.004, T),   # wall up past the panel face (the plank ends run into it)
    (0.228, 0.090, None),
]
PANEL_Z0, PANEL_Z1 = 0.0, 0.065   # the plank panel: face on the ceiling line
GROOVE, PCH = 0.003, 0.003        # 6 mm shadow joints with 3 mm arrises


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
        pm = [GV if k > 0 else T, GV if k > 0 else T, T, GV if k < 4 else T, GV if k < 4 else T, T]
        pl = Part()
        prism_x(pl, sec, x0, x1, pm, cap=T)
        pl.emit(c)
    return c.col(0, 2, 0, 2, -0.06, 0.20)   # the scripted coffer's collision, unchanged


def downlight(P):
    """The sheet's flush round downlight: a dark bronze trim ring 15 cm across, 11 mm proud of the panel, a thin brass
    inner bezel and an amber lens set 1 cm up into it. Local origin: the coffer centre at the ceiling line."""
    d = P("SM_AK_H_Ceiling_Downlight")
    z = PANEL_Z0
    prof = [(0, z + 0.004), (0.0735, z + 0.004), (0.0755, z + 0.001), (0.0755, z - 0.005), (0.0715, z - 0.010),
            (0.0600, z - 0.011), (0.0565, z - 0.009), (0.0550, z - 0.006), (0.0515, z - 0.005), (0.0505, z - 0.001),
            (0, z - 0.001)]
    mats = [BZ, BZ, BZ, BZ, BZ, BR, BR, BR, BZ, LN]
    lp = Part()
    lathe(lp, prof, 24, mats, smooth=[False, False, True, True, False, True, True, False, False, False])
    lp.emit(d)
    return d.col(-0.0755, 0.0755, -0.0755, 0.0755, z - 0.011, z + 0.004)


def joint(P):
    """The sheet's two-tier notched joint block at a Beam_4 x Rib_2 crossing. Upper tier: a plus in plan whose arms run
    7.5 cm past both beam faces (the crossing members' ends passing each other), a laminated seam round it; lower
    tier: a smaller notched cap under the 40 cm beam with bevelled edges. Local origin: the crossing at the ceiling
    line (the upper tier's top is buried in the coffer lips)."""
    j = P("SM_AK_H_Ceiling_Joint")
    up = Part()
    A, a, B, b = 0.155, 0.110, 0.200, 0.155
    sweep_plus(up, [(A, a, B, b, 0.0, -0.150), (A, a, B, b, 0.0, -0.276), (A, a, B, b, 0.003, -0.279),
                    (A, a, B, b, 0.003, -0.283), (A, a, B, b, 0.0, -0.286), (A, a, B, b, 0.0, -0.402),
                    (A, a, B, b, 0.006, -0.408)], [T] * 6)
    up.emit(j)
    lo = Part()
    A2, a2, B2, b2 = 0.118, 0.080, 0.163, 0.120
    sweep_plus(lo, [(A2, a2, B2, b2, 0.0, -0.404), (A2, a2, B2, b2, 0.0, -0.442), (A2, a2, B2, b2, 0.005, -0.447)],
               [T] * 2)
    lo.emit(j)
    return j.col(-0.155, 0.155, -0.20, 0.20, -0.447, -0.150)


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
