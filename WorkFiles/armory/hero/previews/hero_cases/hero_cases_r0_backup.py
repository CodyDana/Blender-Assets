"""Hero display cases (user, 2026-09-27: hero pieces that match the per-piece reference sheets "to the T").

References (WorkFiles/armory/reference): case_standard.png (the design), case_detail.png (corner, brass band, fluted
slats, recessed LED base, medallion profile), case_tall.png, hero_plinth.png, back_wall.png, armory3_reference2.png.

ONE parametric design for the five glass cases of build_armory_kit.CASES (L, LN, M, S, Tall) plus the hero plinth:

  plinth  a dark-bronze base shoe inset 3 cm under the body with an amber LED strip (M_AK_LEDGlow) on its upper edge, so
          the body floats on a glowing line; a black gloss-lacquer body built from four corner stiles with softly rounded
          vertical edges, top and bottom rails, fluted vertical slat bands (front and back: a band at each end with a
          smooth centre panel carrying the user's emblem medallion; the sides fluted end to end); a brass band proud of
          the body at the top edge; a black lacquer deck slab stepped in on top with a slim brass inlay line just inside
          the glass. Deck top at H + 4 mm (armory_items.DECK_ABOVE_PLINTH).
  glass   thin glass panes between slim dark-bronze square-section corner posts and top / bottom frames, a warm LED line
          under the top frame, a bronze corner plate with two puck lights under each top corner and a single uplight
          puck at each bottom corner.
  hero    the long low hero plinth: one black-lacquer slab with rounded vertical corners, a brass top rim and a second
          brass line below it, the user's emblem medallion on the front, an amber LED strip on a recessed base between
          four dark-bronze corner feet.

Every piece keeps the scripted piece's name, pivot, facing, footprint / height (bbox within ~2 cm) and its exact col()
boxes. ENABLED stays False: the user reviews images of every piece before anything goes into the armory.
"""
import math

ENABLED = False          # the user reviews images of every piece BEFORE anything goes into the armory; never set True
MATERIALS = {}           # the kit's own M_AK_* materials cover everything

LQ, BR, BZ, GL = "M_AK_Lacquer", "M_AK_Brass", "M_AK_Bronze", "M_AK_Glass"
LG, LL, LED, FE, EM = "M_AK_LEDGlow", "M_AK_LEDLine", "M_AK_LED", "M_AK_DeckLacquer", "M_AK_Emblem"

# ---- plinth section (metres). Heights above the plinth base; H = plinth height from CASES.
SKIN = 0.003          # brass band proud of the body face (band outer face = the scripted footprint W/2, D/2)
GROOVE = 0.010        # flute groove depth: body face -> core face
STILE = 0.045         # corner stile width on each face
PITCH = 0.036         # target flute pitch (case_standard front: 9 slats in a 0.32 m band on the 1.8 m case)
SLAT_FILL = 0.80      # slat width / pitch
BAND_FRAC = 0.178     # end band width / case width
SHOE_IN = 0.025       # base shoe inset from the band line
Z_BODY = 0.055        # body underside
Z_BRAIL = 0.068       # bottom rail top
TOP_RAIL = 0.074      # top rail bottom = H - TOP_RAIL
BAND_Z0, BAND_Z1 = 0.050, 0.031   # brass band H - 0.050 .. H - 0.031
DECK_IN = 0.015       # deck slab inset from the band line
DECK_TOP = 0.004      # deck top = H + 0.004
# ---- glass hood
GLASS_IN = 0.032      # glass outer face inset from W/2 (scripted 0.020: frames stand 12 mm inside the deck edge)
FR = 0.018            # square-section bronze frame / post size


# --------------------------------------------------------------------------- mesh accumulator

def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _newell(pts):
    n = [0.0, 0.0, 0.0]
    for i, p in enumerate(pts):
        q = pts[(i + 1) % len(pts)]
        n[0] += (p[1] - q[1]) * (p[2] + q[2])
        n[1] += (p[2] - q[2]) * (p[0] + q[0])
        n[2] += (p[0] - q[0]) * (p[1] + q[1])
    return n


class Acc:
    """Welded mesh parts for one Piece: faces are oriented to a hint direction (outward), n-gons are fanned."""

    def __init__(self):
        self.v, self.f, self.uv, self.m, self.sm = [], [], [], [], []

    def vert(self, p):
        self.v.append(tuple(float(c) for c in p))
        return len(self.v) - 1

    def face(self, idx, uvs, mat, hint, smooth=False):
        n = _newell([self.v[i] for i in idx])
        if _dot(n, hint) < 0:
            idx, uvs = list(reversed(idx)), list(reversed(uvs))
        self.f.append(list(idx))
        self.uv.append([tuple(u) for u in uvs])
        self.m.append(mat)
        self.sm.append(bool(smooth))

    def cap(self, loop, mat, hint, uvf, centre=None):
        """Cap a convex loop: a quad for 4 verts, else a fan (from a centre vertex if given, else from loop[0])."""
        if len(loop) == 4 and centre is None:
            self.face(loop, [uvf(self.v[i]) for i in loop], mat, hint)
            return
        if centre is not None:
            c = self.vert(centre)
            for i in range(len(loop)):
                a, b = loop[i], loop[(i + 1) % len(loop)]
                self.face([c, a, b], [uvf(self.v[c]), uvf(self.v[a]), uvf(self.v[b])], mat, hint)
            return
        for i in range(1, len(loop) - 1):
            tri = [loop[0], loop[i], loop[i + 1]]
            self.face(tri, [uvf(self.v[k]) for k in tri], mat, hint)

    def emit(self, piece):
        if self.f:
            piece.mesh(self.v, self.f, self.uv, self.m, smooth=self.sm)
        return piece


def prism(a, poly, z0, z1, mat, closed=True, cap0=True, cap1=True, smooth=None):
    """A vertical prism from a convex XY polygon; sides face away from the polygon centroid. closed=False leaves the
    side between the last and first point open (a face buried in the body behind it). smooth: set of side indices."""
    n = len(poly)
    cx = sum(p[0] for p in poly) / n
    cy = sum(p[1] for p in poly) / n
    b = [a.vert((x, y, z0)) for x, y in poly]
    t = [a.vert((x, y, z1)) for x, y in poly]
    s = [0.0]
    for i in range(1, n + 1):
        p, q = poly[i - 1], poly[i % n]
        s.append(s[-1] + math.dist(p, q))
    for i in range(n if closed else n - 1):
        j = (i + 1) % n
        mx, my = (poly[i][0] + poly[j][0]) / 2, (poly[i][1] + poly[j][1]) / 2
        a.face([b[i], b[j], t[j], t[i]], [(s[i], z0), (s[i + 1], z0), (s[i + 1], z1), (s[i], z1)], mat,
               (mx - cx, my - cy, 0.0), smooth=bool(smooth and i in smooth))
    uvf = lambda v: (v[0], v[1])
    if cap0:
        a.cap(b, mat, (0, 0, -1), uvf)
    if cap1:
        a.cap(t, mat, (0, 0, 1), uvf)


def box(a, x0, x1, y0, y1, z0, z1, mat, cap0=True, cap1=True):
    prism(a, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1, mat, cap0=cap0, cap1=cap1)


def rrect(hx, hy, r, segs):
    """CCW rounded rectangle (seen from +Z) centred on the origin; returns [(x, y, arc_id)]. r <= 0: 4 sharp corners."""
    if r <= 0:
        return [(hx, -hy, 0), (hx, hy, 1), (-hx, hy, 2), (-hx, -hy, 3)]
    out = []
    for k, (sx, sy, a0) in enumerate(((1, -1, -90), (1, 1, 0), (-1, 1, 90), (-1, -1, 180))):
        cx, cy = sx * (hx - r), sy * (hy - r)
        for i in range(segs + 1):
            ang = math.radians(a0 + 90.0 * i / segs)
            out.append((cx + r * math.cos(ang), cy + r * math.sin(ang), k))
    return out


def loft(a, hx, hy, r, segs, profile, mats, closed=False, cap_first=None, cap_last=None, smooth_corners=True):
    """Sweep a (d, z) profile around a rounded rectangle (d = outward offset from it). The profile must run so the
    solid lies on its left in the (d, z) plane (outer wall going up, top going inward, inner wall down, bottom out):
    then each face's outward normal is (dz, -dd). mats: one name or one per profile segment.
    cap_first / cap_last: (material, +1 / -1) caps the first / last loop, facing +Z / -Z."""
    if isinstance(mats, str):
        mats = [mats] * len(profile)
    loops = []
    for d, z in profile:
        pts = rrect(hx + d, hy + d, (r + d) if r > 0 else 0, segs)
        loops.append(([a.vert((x, y, z)) for x, y, _k in pts], pts, z))
    base = rrect(hx, hy, r, segs)
    m = len(base)
    # outward horizontal normal of every loop edge, and perimeter coordinates per loop
    en = []
    for i in range(m):
        p, q = base[i], base[(i + 1) % m]
        ex, ey = q[0] - p[0], q[1] - p[1]
        ln = math.hypot(ex, ey) or 1.0
        en.append((ey / ln, -ex / ln))
    per = []
    for _ids, pts, _z in loops:
        s = [0.0]
        for i in range(1, m + 1):
            s.append(s[-1] + math.dist(pts[i - 1][:2], pts[i % m][:2]))
        per.append(s)
    vs = [0.0]
    for k in range(1, len(profile)):
        vs.append(vs[-1] + math.dist(profile[k - 1], profile[k]))
    nseg = len(profile) if closed else len(profile) - 1
    if closed:
        vs.append(vs[-1] + math.dist(profile[-1], profile[0]))
    for k in range(nseg):
        k2 = (k + 1) % len(profile)
        (ia, pa, _za), (ib, pb, _zb) = loops[k], loops[k2]
        dd = profile[k2][0] - profile[k][0]
        dz = profile[k2][1] - profile[k][1]
        for i in range(m):
            j = (i + 1) % m
            hint = (dz * en[i][0], dz * en[i][1], -dd)
            sm = smooth_corners and r > 0 and base[i][2] == base[j][2]
            a.face([ia[i], ia[j], ib[j], ib[i]],
                   [(per[k][i], vs[k]), (per[k][i + 1], vs[k]), (per[k2][i + 1], vs[k + 1]), (per[k2][i], vs[k + 1])],
                   mats[k], hint, smooth=sm)
    uvf = lambda v: (v[0], v[1])
    for cap, (ids, _pts, z) in ((cap_first, loops[0]), (cap_last, loops[-1])):
        if cap:
            a.cap(ids, cap[0], (0, 0, cap[1]), uvf, centre=None if len(ids) == 4 else (0.0, 0.0, z))


def medallion(a, cx, y_face, cz, R, facing, sides=48):
    """The user's emblem as a brass medallion (case_detail: a thick brass disc with a slim raised rim, standing off the
    panel on a dark spacer). The emblem face (M_AK_Emblem, unique 0-1 UV over it, read left to right from outside) is
    recessed inside the rim. y_face = the panel face; facing -1 shows to -Y, +1 to +Y."""
    prof = [(0.88 * R, -0.001), (0.88 * R, 0.003), (R - 0.0012, 0.003), (R, 0.0042), (R, 0.0115),
            (R - 0.0015, 0.013), (0.925 * R, 0.013), (0.91 * R, 0.0115)]
    mats = [BZ, BR, BR, BR, BR, BR, BR]
    rings = []
    for r, d in prof:
        ids = []
        for i in range(sides):
            ang = 2 * math.pi * i / sides
            ids.append(a.vert((cx + r * math.cos(ang), y_face + facing * d, cz + r * math.sin(ang))))
        rings.append(ids)
    for k in range(len(prof) - 1):
        dr = prof[k + 1][0] - prof[k][0]
        dd = prof[k + 1][1] - prof[k][1]
        n_r, n_d = dd, -dr                  # outward normal in the (r, d) plane
        wall = abs(dd) > abs(dr)
        for i in range(sides):
            j = (i + 1) % sides
            ang = 2 * math.pi * (i + 0.5) / sides
            hint = (n_r * math.cos(ang), facing * n_d, n_r * math.sin(ang))
            la = [(2 * math.pi * R * i / sides, k * 0.01), (2 * math.pi * R * (i + 1) / sides, k * 0.01),
                  (2 * math.pi * R * (i + 1) / sides, (k + 1) * 0.01), (2 * math.pi * R * i / sides, (k + 1) * 0.01)]
            a.face([rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]], la, mats[k], hint, smooth=wall)
    rf, df = prof[-1]
    sgn = -facing                            # u runs left to right as seen from outside the face

    def uvd(v):
        return (0.5 + sgn * (v[0] - cx) / (2 * rf), 0.5 + (v[2] - cz) / (2 * rf))
    a.cap(rings[-1], EM, (0, facing, 0), uvd, centre=(cx, y_face + facing * df, cz))


# --------------------------------------------------------------------------- the case plinth

def _slat(u0, u1, d0, d1, c):
    """Cross-section (u, d) of a slat / panel with chamfered front edges; open at the back (d0, buried)."""
    return [(u0, d0), (u0, d1 - c), (u0 + c, d1), (u1 - c, d1), (u1, d1 - c), (u1, d0)]


def case_plinth(G, t, W, D, H):
    hw, hd = W / 2, D / 2
    pl = G["Piece"](f"SM_AK_Case_{t}_Plinth")
    a = Acc()
    hwb, hdb = hw - SKIN, hd - SKIN            # body face
    hwc, hdc = hwb - GROOVE, hdb - GROOVE      # core face (groove floor)
    # base shoe (dark bronze) and the amber LED strip on its upper edge, under the body overhang
    loft(a, hw - SHOE_IN, hd - SHOE_IN, 0, 0, [(0, 0.0), (0, 0.058)], BZ)
    loft(a, hw - SHOE_IN, hd - SHOE_IN, 0, 0, [(-0.001, 0.034), (0.004, 0.034), (0.004, 0.054), (-0.001, 0.054)], LG)
    # lacquer core (the groove floor), underside capped
    loft(a, hwc, hdc, 0, 0, [(0, 0.0565), (0, H - 0.030)], LQ, cap_first=(LQ, -1))
    # corner stiles with a softly rounded outer vertical edge
    rs, n_arc = 0.005, 3
    for sx in (-1, 1):
        for sy in (-1, 1):
            x1, y1 = hwb, hdb
            x0, y0 = hwb - STILE, hdb - STILE
            poly = [(x0, y0), (x1, y0)]
            for i in range(n_arc + 1):
                ang = math.radians(90.0 * i / n_arc)
                poly.append((x1 - rs + rs * math.cos(ang), y1 - rs + rs * math.sin(ang)))
            poly.append((x0, y1))
            poly = [(sx * x, sy * y) for x, y in poly]
            prism(a, poly, Z_BODY, H - 0.045, LQ, cap1=False, smooth=set(range(2, 2 + n_arc)))
    # rails: bottom (underside and groove ledge visible) and top (under the brass band)
    ri = STILE - 0.001
    for f in (-1, 1):
        for z0, z1, c1 in ((Z_BODY + 0.0005, Z_BRAIL, True), (H - TOP_RAIL, H - 0.045, False)):
            box(a, -(hwb - ri), hwb - ri, *sorted((f * hdb, f * (hdc - 0.0005))), z0, z1, LQ, cap1=c1)
            box(a, *sorted((f * hwb, f * (hwc - 0.0005))), -(hdb - ri), hdb - ri, z0, z1, LQ, cap1=c1)
    zs0, zs1 = Z_BRAIL - 0.001, H - TOP_RAIL + 0.001
    c = 0.0015

    def front_prism(f, u0, u1, panel=False):
        sec = _slat(u0, u1, -0.0005, GROOVE, c)
        if panel:   # the smooth centre panel: a 3 mm reveal against both rails (case_standard front view)
            prism(a, [(u, f * (hdc + d)) for u, d in sec], Z_BRAIL + 0.003, H - TOP_RAIL - 0.003, LQ, closed=False)
        else:       # slats run into the rails
            prism(a, [(u, f * (hdc + d)) for u, d in sec], zs0, zs1, LQ, closed=False, cap0=False, cap1=False)

    def side_prism(g, u0, u1):
        sec = _slat(u0, u1, -0.0005, GROOVE, c)
        prism(a, [(g * (hwc + d), u) for u, d in sec], zs0, zs1, LQ, closed=False, cap0=False, cap1=False)

    # front and back: a fluted band at each end, the smooth centre panel between, the medallion on it
    xs = hwb - STILE
    bw = BAND_FRAC * W
    n = max(5, round(bw / PITCH))
    p = bw / n
    sw = SLAT_FILL * p
    xp = xs - bw - 0.005
    hz = (H - TOP_RAIL) - Z_BRAIL
    R = min(0.26, max(0.18, 0.60 * hz)) / 2
    for f in (-1, 1):
        for side in (-1, 1):
            for i in range(n):
                uc = side * (xs - (i + 0.5) * p)
                front_prism(f, uc - sw / 2, uc + sw / 2)
        front_prism(f, -xp, xp, panel=True)
        medallion(a, 0.0, f * hdb, (Z_BRAIL + H - TOP_RAIL) / 2, R, f)
    # the sides: fluted end to end between the stiles
    ys = hdb - STILE
    ns = max(5, round(2 * ys / PITCH))
    ps = 2 * ys / ns
    for g in (-1, 1):
        for i in range(ns):
            uc = -ys + (i + 0.5) * ps
            side_prism(g, uc - SLAT_FILL * ps / 2, uc + SLAT_FILL * ps / 2)
    # brass band at the top edge: proud of the body, its top a narrow brass ledge round the deck
    loft(a, hwb, hdb, 0, 0, [(-0.019, H - BAND_Z0), (SKIN, H - BAND_Z0), (SKIN, H - BAND_Z1 - 0.001),
                             (SKIN - 0.001, H - BAND_Z1), (-0.019, H - BAND_Z1)], BR, closed=True)
    # black lacquer deck slab stepped in, softly chamfered, lacquer deck top; slim brass inlay just inside the glass
    loft(a, hw - DECK_IN, hd - DECK_IN, 0, 0, [(0, H - 0.0325), (0, H + DECK_TOP - 0.002), (-0.002, H + DECK_TOP)],
         LQ, cap_last=(FE, 1))
    gi = GLASS_IN + FR + 0.002
    loft(a, hw - gi, hd - gi, 0, 0, [(-0.006, H + DECK_TOP - 0.0005), (0, H + DECK_TOP - 0.0005),
                                     (0, H + DECK_TOP + 0.0015), (-0.006, H + DECK_TOP + 0.0015)], BR, closed=True)
    a.emit(pl)
    return pl.col(-hw, hw, -hd, hd, 0, H)      # the scripted collision, unchanged


# --------------------------------------------------------------------------- the glass hood

def puck(a, x, y, z0, z1, lit_top, r=0.0095, sides=12):
    """A small round puck light: bronze can with a glowing lens lip, LED face on the top (uplight) or the bottom
    (downlight); the lip makes the pucks read as the bright corner dots of the sheets from the side too."""
    poly = [(x + r * math.cos(2 * math.pi * i / sides), y + r * math.sin(2 * math.pi * i / sides)) for i in range(sides)]
    lip = 0.0015
    zm = z1 - lip if lit_top else z0 + lip
    ring0 = [a.vert((px, py, z0)) for px, py in poly]
    ringm = [a.vert((px, py, zm)) for px, py in poly]
    ring1 = [a.vert((px, py, z1)) for px, py in poly]
    for i in range(sides):
        j = (i + 1) % sides
        ang = 2 * math.pi * (i + 0.5) / sides
        hint = (math.cos(ang), math.sin(ang), 0)
        for lo, hi, zl, zh in ((ring0, ringm, z0, zm), (ringm, ring1, zm, z1)):
            lit = (zh == z1) == lit_top
            a.face([lo[i], lo[j], hi[j], hi[i]], [(i / sides, zl), ((i + 1) / sides, zl), ((i + 1) / sides, zh),
                                                  (i / sides, zh)], LED if lit else BZ, hint, smooth=True)
    uvf = lambda v: (v[0], v[1])
    if lit_top:
        a.cap(ring1, LED, (0, 0, 1), uvf, centre=(x, y, z1))
    else:
        a.cap(ring0, LED, (0, 0, -1), uvf, centre=(x, y, z0))


def case_glass(G, t, W, D, Gh):
    gl = G["Piece"](f"SM_AK_Case_{t}_Glass")
    a = Acc()
    ox, oy = W / 2 - GLASS_IN, D / 2 - GLASS_IN
    zb = DECK_TOP - 0.001                       # sits on the deck (1 mm into it)
    # bottom and top frames: square-section dark bronze
    loft(a, ox, oy, 0, 0, [(-FR, zb), (0, zb), (0, zb + 0.020), (-FR, zb + 0.020)], BZ, closed=True)
    loft(a, ox, oy, 0, 0, [(-FR, Gh - 0.022), (0, Gh - 0.022), (0, Gh - 0.0012), (-0.0012, Gh), (-FR, Gh)], BZ,
         closed=True)
    # corner posts
    c = 0.0012
    for sx in (-1, 1):
        for sy in (-1, 1):
            poly = [(ox - FR, oy - FR), (ox, oy - FR), (ox, oy - c), (ox - c, oy), (ox - FR, oy)]
            poly = [(sx * x, sy * y) for x, y in poly]
            prism(a, poly, zb + 0.019, Gh - 0.021, BZ, cap0=False, cap1=False)
    # glass panes set in the middle of the frame section, their edges buried in the posts and frames
    pz0, pz1 = zb + 0.018, Gh - 0.020
    e = FR - 0.002
    for f in (-1, 1):
        box(a, -(ox - e), ox - e, *sorted((f * (oy - 0.005), f * (oy - 0.011))), pz0, pz1, GL, cap0=False, cap1=False)
        box(a, *sorted((f * (ox - 0.005), f * (ox - 0.011))), -(oy - e), oy - e, pz0, pz1, GL, cap0=False, cap1=False)
    box(a, -(ox - e), ox - e, -(oy - e), oy - e, Gh - 0.012, Gh - 0.006, GL)
    # warm LED line under the inner edge of the top frame
    loft(a, ox - FR, oy - FR, 0, 0, [(-0.006, Gh - 0.027), (0.001, Gh - 0.027), (0.001, Gh - 0.0212),
                                     (-0.006, Gh - 0.0212)], LL, closed=True)
    # corner plates: two downlight pucks under each top corner, one uplight puck at each bottom corner
    for sx in (-1, 1):
        for sy in (-1, 1):
            xa, xb = sorted((sx * (ox - 0.058), sx * (ox - 0.0125)))
            ya, yb = sorted((sy * (oy - 0.058), sy * (oy - 0.0125)))
            box(a, xa, xb, ya, yb, Gh - 0.031, Gh - 0.0205, BZ)
            puck(a, sx * (ox - 0.041), sy * (oy - 0.027), Gh - 0.0345, Gh - 0.030, False)
            puck(a, sx * (ox - 0.027), sy * (oy - 0.041), Gh - 0.0345, Gh - 0.030, False)
            xa, xb = sorted((sx * (ox - 0.050), sx * (ox - 0.012)))
            ya, yb = sorted((sy * (oy - 0.050), sy * (oy - 0.012)))
            box(a, xa, xb, ya, yb, zb, zb + 0.008, BZ, cap0=False)
            puck(a, sx * (ox - 0.033), sy * (oy - 0.033), zb + 0.007, zb + 0.0115, True)
    a.emit(gl)
    gw, gd = (W - 0.04) / 2, (D - 0.04) / 2
    return gl.col(-gw, gw, -gd, gd, 0, Gh)      # the scripted collision, unchanged


# --------------------------------------------------------------------------- the hero plinth

def hero_plinth(G, W, D, H):
    """hero_plinth.png: a long low black-lacquer slab with rounded vertical corners, a brass top rim and a second brass
    line below it, the user's emblem medallion centred on the front, an amber LED strip on a recessed base between four
    dark-bronze corner feet. Scripted pivot, footprint, height and collision."""
    hw, hd = W / 2, D / 2
    t = G["Piece"]("SM_AK_Case_Hero_Plinth")
    a = Acc()
    rr, segs = 0.035, 6
    bx, by = hw - 0.003, hd - 0.003
    z0 = 0.050
    loft(a, bx, by, rr, segs, [(0, z0), (0, H - 0.0005)], LQ, cap_first=(LQ, -1), cap_last=(LQ, 1))
    loft(a, bx, by, rr, segs, [(-0.003, H - 0.010), (0.0025, H - 0.010), (0.0025, H - 0.0012), (0.0013, H),
                               (-0.003, H)], BR, closed=True)
    loft(a, bx, by, rr, segs, [(-0.003, H - 0.040), (0.0022, H - 0.040), (0.0022, H - 0.034), (-0.003, H - 0.034)],
         BR, closed=True)
    # recessed base with the LED strip, and four dark-bronze feet at the corners
    loft(a, hw - 0.065, hd - 0.065, 0.010, 2, [(0, 0.0), (0, z0 + 0.002)], LQ)
    loft(a, hw - 0.065, hd - 0.065, 0.010, 2, [(-0.001, 0.034), (0.003, 0.034), (0.003, 0.047), (-0.001, 0.047)], LG)
    fc = 0.002
    for sx in (-1, 1):
        for sy in (-1, 1):
            x0, x1, y0, y1 = hw - 0.095, hw - 0.035, hd - 0.095, hd - 0.035
            poly = [(x0 + fc, y0), (x1 - fc, y0), (x1, y0 + fc), (x1, y1 - fc), (x1 - fc, y1), (x0 + fc, y1),
                    (x0, y1 - fc), (x0, y0 + fc)]
            prism(a, [(sx * x, sy * y) for x, y in poly], 0.0, z0 + 0.002, BZ, cap0=False, cap1=False)
    medallion(a, 0.0, -by, (z0 + H - 0.040) / 2, 0.09, -1)
    a.emit(t)
    return t.col(-hw - 0.013, hw + 0.013, -hd - 0.013, hd + 0.01, 0, H)   # the scripted collision, unchanged


def pieces(G):
    out = []
    for t, (W, D, H, Gh) in G["CASES"].items():
        if t == "Hero":
            out.append(hero_plinth(G, W, D, H))
            continue
        out.append(case_plinth(G, t, W, D, H))
        out.append(case_glass(G, t, W, D, Gh))
    return out
