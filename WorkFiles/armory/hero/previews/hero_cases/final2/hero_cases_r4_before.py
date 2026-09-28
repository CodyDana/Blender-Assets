"""Hero display cases (user, 2026-09-27: hero pieces that match the per-piece reference sheets "to the T").

References (WorkFiles/armory/reference): case_standard.png (the design), case_detail.png (corner, brass band, fluted
slats, recessed LED base, medallion profile), case_tall.png, hero_plinth.png, back_wall.png, armory3_reference2.png.

ONE parametric design for the five glass cases of build_armory_kit.CASES (L, LN, M, S, Tall) plus the hero plinth:

  plinth  a dark-bronze base shoe inset 2.5 cm under the body, its upper face and an under-body strip glowing amber
          (M_AK_HAmber / M_AK_HAmberHot), so the body floats on a glowing line; a black gloss-lacquer body built from four corner stiles with softly rounded
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

Fix 1 (blind judge): case-only flat materials M_AK_HLacquer (mirror gloss), M_AK_HBrass (bright), M_AK_HBronze (dark
antique bronze), M_AK_HAmber / M_AK_HAmberHot (saturated amber); 16 mm deep rounded ribs; a 2.7 cm brass L-cap band;
25 mm frames; one domed puck light under each top corner and on each bottom corner; medallion scaled to the panel.

Fix 2 (blind judge): the LED base is a brushed-bronze kick plate (M_AK_HBronzeKick) recessed under the overhang with a
narrow hot strip hung under the body 9 mm off it (lights the plate from the top down and pools on the floor); matte
groove floors / slat walls (M_AK_HLacquerGroove) and a 56 % slat fill so the flutes read head-on; a 3.2 cm brushed brass
band (M_AK_HBrassBrushed) with a rounded top edge; a pale glint line down each corner post (M_AK_HGlint); medallion on
the back only for the aisle cases (L, LN, M); hero: narrow recessed strip, bronze feet, brushed pinstripes, slimmer disc.

Fix 3 (blind judge): glossier lacquer, lighter warm bronze, 28 mm posts / frames with a bronze L-channel foot and a
slimmer top rail, a low LED line along the foot of the glass, a charcoal suede deck floor inside a lacquer margin; 21 mm
flutes, 10 wider square-edged slats per end band, a near-flush centre panel with a hairline seam; a 2.3 cm paler brass
band; the kick plate's top leans back in a cove that mirrors the hot strip (lit amber top fading to dark bronze); Tall:
19 % end bands and a 0.27 m disc; hero: slimmer brass lines, the second 3.9 cm down, feet not lit orange.

Every piece keeps the scripted piece's name, pivot, facing, footprint / height (bbox within ~2 cm) and its exact col()
boxes. ENABLED stays False: the user reviews images of every piece before anything goes into the armory.
"""
import math

ENABLED = False          # the user reviews images of every piece BEFORE anything goes into the armory; never set True
# fix 1 (blind judge, every case): the kit's lacquer read matte charcoal, the brass dull olive, the frames copper and
# the under-glow pale peach next to the sheets. Four flat-param case materials (no textures):
MATERIALS = {
    # mirror-gloss black piano lacquer (case_standard / case_detail: sharp specular streaks on slats and deck)
    "M_AK_HLacquer": (None, 1.0, {"color": "#0D0C0B", "rough": 0.035, "coat": 1.0}),   # fix 3: glossier
    # bright brushed brass (band, deck edge, medallion)
    "M_AK_HBrass": (None, 1.0, {"color": "#D2A35C", "rough": 0.20, "metal": 1.0}),
    # dark antique bronze (glass frames, base shoe, puck cans, hero feet)
    "M_AK_HBronze": (None, 1.0, {"color": "#735A3C", "rough": 0.32, "metal": 1.0}),   # fix 3: warm antique, lighter
    # saturated amber under-glow (a lower strength keeps the hue through AgX; the kit's LEDGlow tone-maps to peach)
    # (a dark base so the case lights do not wash it out; kept low so the hue survives AgX: #FF9A10 at 1.2 read peach)
    "M_AK_HAmber": (None, 1.0, {"color": "#3A2208", "emit": 5.0, "emit_color": "#FFA838"}),   # fix 3: a hot thin line
    # the downward faces of the under-body strips: hotter, they throw the amber pool on the floor and the shoe
    # (fix 2: 3 -> 9, the recessed strip alone now lights the bronze kick plate and the floor pool)
    "M_AK_HAmberHot": (None, 1.0, {"color": "#3A2208", "emit": 14.0, "emit_color": "#FF9A10"}),   # fix 3: 12 -> 14 (it
    # only lights the kick cove and the floor now: the strip's front face is the thin M_AK_HAmber line)
    # fix 2: brushed bronze kick plate / hero feet (case_detail bottom-left: a lighter brushed bronze than the frames)
    "M_AK_HBronzeKick": (None, 1.0, {"color": "#6E5436", "rough": 0.38, "metal": 1.0}),   # fix 3: darker kick
    # fix 2: the glass-edge glint down each corner post (the panes read by their lit edges; pale, low emission)
    "M_AK_HGlint": (None, 1.0, {"color": "#E8E2D6", "emit": 0.6, "emit_color": "#FFE9C8"}),
    # fix 2: the flute grooves (groove floor and slat walls): dead-matte black, so the glossy slat faces read head-on
    "M_AK_HLacquerGroove": (None, 1.0, {"color": "#020202", "rough": 0.75}),
    # fix 2: brushed brass for the top band (a broader lobe picks up the studio key: bright gold in the orthos)
    "M_AK_HBrassBrushed": (None, 1.0, {"color": "#E2BC78", "rough": 0.38, "metal": 1.0}),   # fix 3: paler brass
    # fix 3: the charcoal textured deck inside the glass (case_standard / case_tall top views: a matte suede floor)
    "M_AK_HDeckSuede": (None, 1.0, {"color": "#252321", "rough": 0.92}),
}

LQ, BR, BZ, GL = "M_AK_HLacquer", "M_AK_HBrass", "M_AK_HBronze", "M_AK_Glass"
LGH = "M_AK_HAmberHot"
BK, GRV, BRB = "M_AK_HBronzeKick", "M_AK_HLacquerGroove", "M_AK_HBrassBrushed"
SLAT_MATS = [GRV, "M_AK_HLacquer", "M_AK_HLacquer", "M_AK_HLacquer", GRV, GRV]   # slat walls matte, chamfers + face gloss
LG, LL, LED, FE, EM = "M_AK_HAmber", "M_AK_LEDLine", "M_AK_LED", "M_AK_DeckLacquer", "M_AK_Emblem"

# ---- plinth section (metres). Heights above the plinth base; H = plinth height from CASES.
SKIN = 0.003          # brass band proud of the body face (band outer face = the scripted footprint W/2, D/2)
GROOVE = 0.021        # flute groove depth: body face -> core face (fix 3: 16 -> 21 mm, deep shadow gaps; fix 1: 10 -> 16)
STILE = 0.045         # corner stile width on each face
PITCH = 0.032         # target flute pitch (fix 3: 10 raised slats per 0.32 m end band, case_detail / case_standard)
SLAT_FILL = 0.62      # slat width / pitch (fix 3: 0.56 -> 0.62, wider square slats; fix 2: 0.70 -> 0.56)
SLAT_C = 0.0015       # slat edge chamfer (fix 3: 3 -> 1.5 mm, square-edged slats)
PANEL_C = 0.0008      # centre panel edge chamfer (fix 3: a hairline seam, not a bevelled border)
PANEL_GAP = 0.0015    # centre panel reveal against the rails and the fluted bands (fix 3: 3-5 mm -> 1.5 mm)
RIB = {1, 2, 3}       # slat faces shaded smooth across the chamfers: each rib catches a rounded highlight
BAND_FRAC = 0.178     # end band width / case width
SHOE_IN = 0.025       # base shoe inset from the band line
Z_BODY = 0.055        # body underside
Z_BRAIL = 0.080       # bottom rail top (case_detail: a plain lacquer rail under the slats)
BAND_Z0, BAND_Z1 = 0.053, 0.030   # brass L-cap band H - 0.053 .. H - 0.030 (fix 3: a 2.3 cm face, the sheets' thin
BAND_R = 0.004                    # brushed band; fix 2: 3.2 cm with a rounded top edge; fix 1: 2.7 cm)
DECK_IN = 0.015       # deck slab inset from the band line
DECK_TOP = 0.004      # deck top = H + 0.004
MED_FRAC = 0.66       # medallion diameter / slat-panel height (fix 3: 0.56 -> 0.66; case_standard ~0.6, case_tall ~0.72)
MED_W = 0.18          # medallion diameter cap / case width (case_tall: ~18 % of the width)
BAND_FRACS = {"Tall": 0.19}   # fix 3: case_tall's fluted end panels ~19 % of the width each
MED_FRACS = {"Tall": 0.74}    # fix 3: case_tall.png: the disc ~0.27 m (~18 % of the 1.5 m width)
# ---- glass hood
GLASS_IN = 0.032      # glass outer face inset from W/2 (scripted 0.020: frames stand 12 mm inside the deck edge)
FR = 0.028            # square-section bronze frame / post size (fix 3: 25 -> 28 mm; fix 1: 18 -> 25 mm)
LIP = 0.010           # fix 3: the bronze L-channel foot of the bottom frame (case_detail top-left), out over the deck


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
    side between the last and first point open (a face buried in the body behind it). smooth: set of side indices.
    mat: one name, or one per side (the caps then take the first)."""
    n = len(poly)
    mats = [mat] * n if isinstance(mat, str) else list(mat)
    mat = mats[0]
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
        a.face([b[i], b[j], t[j], t[i]], [(s[i], z0), (s[i + 1], z0), (s[i + 1], z1), (s[i], z1)], mats[i],
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


def loft(a, hx, hy, r, segs, profile, mats, closed=False, cap_first=None, cap_last=None, smooth_corners=True,
         smooth_prof=()):
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
            sm = (smooth_corners and r > 0 and base[i][2] == base[j][2]) or k in smooth_prof
            a.face([ia[i], ia[j], ib[j], ib[i]],
                   [(per[k][i], vs[k]), (per[k][i + 1], vs[k]), (per[k2][i + 1], vs[k + 1]), (per[k2][i], vs[k + 1])],
                   mats[k], hint, smooth=sm)
    uvf = lambda v: (v[0], v[1])
    for cap, (ids, _pts, z) in ((cap_first, loops[0]), (cap_last, loops[-1])):
        if cap:
            a.cap(ids, cap[0], (0, 0, cap[1]), uvf, centre=None if len(ids) == 4 else (0.0, 0.0, z))


def medallion(a, cx, y_face, cz, R, facing, sides=48, k=1.0):
    """The user's emblem as a brass medallion (case_detail: a thick brass disc with a slim raised rim, standing off the
    panel on a dark spacer). The emblem face (M_AK_Emblem, unique 0-1 UV over it, read left to right from outside) is
    recessed inside the rim. y_face = the panel face; facing -1 shows to -Y, +1 to +Y."""
    prof = [(0.88 * R, -0.001), (0.88 * R, 0.003 * k), (R - 0.0012, 0.003 * k), (R, 0.0042 * k), (R, 0.0115 * k),
            (R - 0.0015, 0.013 * k), (0.925 * R, 0.013 * k), (0.91 * R, 0.0115 * k)]   # k: stand-off scale
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
    # fix 2 (case_detail bottom-left): a brushed-bronze kick plate recessed 2.5 cm under the lacquer overhang, and a
    # narrow LED strip tucked up in the shadow under the overhang: its underside and its thin outer edge glow hot, so
    # the light falls down the bronze plate and pools on the floor (fix 1's flat lit band on the shoe is gone)
    # fix 3: the kick's top edge leans back in a 22 deg cove: the brushed bronze mirrors the hot strip there, so the
    # plate reads lit amber at the top fading to dark bronze at the floor (case_detail bottom-left), not a flat block
    loft(a, hw - SHOE_IN, hd - SHOE_IN, 0, 0, [(0, 0.0), (0, 0.034), (-0.005, 0.047), (-0.005, 0.058)], BK,
         smooth_prof={1})
    # fix 3: a thin strip (6 mm, was 10.5 mm) tucked under the overhang: a hot thin outer line, the kick below it dark
    loft(a, hw - SHOE_IN, hd - SHOE_IN, 0, 0, [(0.004, 0.0505), (0.015, 0.0505), (0.015, 0.0565), (0.004, 0.0565)],
         [LGH, LG, LG, LGH], closed=True)   # hung 1 mm into the bottom rail, 9 mm off the cove it lights
    # lacquer core (the groove floor: dead-matte black so the slats read), underside capped
    loft(a, hwc, hdc, 0, 0, [(0, 0.0565), (0, H - 0.030)], GRV, cap_first=(LQ, -1))
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
    # bottom rail (underside and groove ledge visible); at the top the slats run straight into the brass band
    ri = STILE - 0.001
    zt = H - BAND_Z0                            # brass band underside = top of the slat field
    for f in (-1, 1):
        box(a, -(hwb - ri), hwb - ri, *sorted((f * hdb, f * (hdc - 0.0005))), Z_BODY + 0.0005, Z_BRAIL, LQ)
        box(a, *sorted((f * hwb, f * (hwc - 0.0005))), -(hdb - ri), hdb - ri, Z_BODY + 0.0005, Z_BRAIL, LQ)
    zs0, zs1 = Z_BRAIL - 0.001, zt + 0.001
    c = SLAT_C

    def front_prism(f, u0, u1, panel=False):
        sec = _slat(u0, u1, -0.0005, GROOVE, PANEL_C if panel else c)
        if panel:   # the smooth centre panel: near flush, a hairline reveal against both rails (fix 3)
            prism(a, [(u, f * (hdc + d)) for u, d in sec], Z_BRAIL + PANEL_GAP, zt - PANEL_GAP, LQ, closed=False)
        else:       # slats run into the rails
            prism(a, [(u, f * (hdc + d)) for u, d in sec], zs0, zs1, SLAT_MATS, closed=False, cap0=False,
                  cap1=False, smooth=RIB)

    def side_prism(g, u0, u1):
        sec = _slat(u0, u1, -0.0005, GROOVE, c)
        prism(a, [(g * (hwc + d), u) for u, d in sec], zs0, zs1, SLAT_MATS, closed=False, cap0=False, cap1=False,
              smooth=RIB)

    # front and back: a fluted band at each end, the smooth centre panel between, the medallion on it
    xs = hwb - STILE
    bw = BAND_FRACS.get(t, BAND_FRAC) * W
    n = max(5, round(bw / PITCH))
    p = bw / n
    sw = SLAT_FILL * p
    xp = xs - bw + (p - sw) / 2 - PANEL_GAP     # fix 3: the panel a hairline off the innermost slat
    hz = zt - Z_BRAIL
    R = min(MED_FRACS.get(t, MED_FRAC) * hz / 2, MED_W * W / 2, 0.40 * xp)
    for f in (-1, 1):
        for side in (-1, 1):
            for i in range(n):
                uc = side * (xs - (i + 0.5) * p)
                front_prism(f, uc - sw / 2, uc + sw / 2)
        front_prism(f, -xp, xp, panel=True)
        # fix 2: the medallion on the front; on the back too only for the free-standing aisle cases (L, LN, M: seen
        # from behind), not on S / Tall whose backs stand against the long walls (CASE_TABLE, rot +-90)
        if f < 0 or t in ("L", "LN", "M"):
            medallion(a, 0.0, f * hdb, (Z_BRAIL + zt) / 2, R, f)
    # the sides: fluted end to end between the stiles
    ys = hdb - STILE
    ns = max(5, round(2 * ys / PITCH))
    ps = 2 * ys / ns
    for g in (-1, 1):
        for i in range(ns):
            uc = -ys + (i + 0.5) * ps
            side_prism(g, uc - SLAT_FILL * ps / 2, uc + SLAT_FILL * ps / 2)
    # brass L-cap band at the top edge: proud of the body, wrapping over the top edge as a brass ledge round the deck
    # (fix 2: brushed brass, a 5 mm rounded top edge shaded smooth: a bright gold line along the edge as in case_detail)
    arc = [(SKIN - BAND_R + BAND_R * math.cos(math.radians(a_)), H - BAND_Z1 - BAND_R + BAND_R * math.sin(
        math.radians(a_))) for a_ in (0, 30, 60, 90)]
    loft(a, hwb, hdb, 0, 0, [(-0.022, H - BAND_Z0), (SKIN, H - BAND_Z0)] + arc + [(-0.022, H - BAND_Z1)], BRB,
         closed=True, smooth_prof={2, 3, 4})
    # black lacquer deck slab stepped in, softly chamfered: a gloss lacquer margin out to under the glass frame, the
    # charcoal suede floor inside it (fix 3: case_standard / case_tall top views); slim brass inlay inside the glass
    dm = GLASS_IN - DECK_IN + FR / 2            # margin: deck edge -> under the middle of the glass frame
    loft(a, hw - DECK_IN, hd - DECK_IN, 0, 0, [(0, H - 0.0325), (0, H + DECK_TOP - 0.002), (-0.002, H + DECK_TOP),
                                               (-dm, H + DECK_TOP)], LQ, cap_last=("M_AK_HDeckSuede", 1))
    gi = GLASS_IN + FR + 0.002
    loft(a, hw - gi, hd - gi, 0, 0, [(-0.006, H + DECK_TOP - 0.0005), (0, H + DECK_TOP - 0.0005),
                                     (0, H + DECK_TOP + 0.0015), (-0.006, H + DECK_TOP + 0.0015)], BR, closed=True)
    a.emit(pl)
    return pl.col(-hw, hw, -hd, hd, 0, H)      # the scripted collision, unchanged


# --------------------------------------------------------------------------- the glass hood

def puck(a, x, y, zm, down, r=0.018, sides=10):
    """A round puck light (fix 1: the sheets' bright corner dots): a dark-bronze can mounted at zm (its back 0.5 mm
    into the plate it hangs from / stands on), a bronze bezel and a glowing domed lens (M_AK_LED) facing down (down=True)
    or up, so it reads as a bright dot from the front, the side and from above / below."""
    s = -1.0 if down else 1.0
    z0 = zm - s * 0.0005
    zc = zm + s * 0.006                      # can face
    rings = [(r, z0), (r, zc), (0.86 * r, zc), (0.60 * r, zc + s * 0.0050)]
    ids = []
    for rr, z in rings:
        ids.append([a.vert((x + rr * math.cos(2 * math.pi * i / sides), y + rr * math.sin(2 * math.pi * i / sides), z))
                    for i in range(sides)])
    for k in range(len(rings) - 1):
        dr = rings[k + 1][0] - rings[k][0]
        dz = rings[k + 1][1] - rings[k][1]
        mat = LED if k == 2 else BZ
        for i in range(sides):
            j = (i + 1) % sides
            ang = 2 * math.pi * (i + 0.5) / sides
            if abs(dr) < 1e-9:               # the can wall
                hint = (math.cos(ang), math.sin(ang), 0.0)
            else:                            # bezel annulus / lens cone: facing away from the mount
                hint = (0.3 * math.cos(ang) * (1 if k == 2 else 0), 0.3 * math.sin(ang) * (1 if k == 2 else 0), s)
            a.face([ids[k][i], ids[k][j], ids[k + 1][j], ids[k + 1][i]],
                   [(i / sides, k * 0.01), ((i + 1) / sides, k * 0.01), ((i + 1) / sides, (k + 1) * 0.01),
                    (i / sides, (k + 1) * 0.01)], mat, hint, smooth=(k != 1))
    a.cap(ids[-1], LED, (0, 0, s), lambda v: (v[0], v[1]), centre=(x, y, zc + s * 0.0075))


def case_glass(G, t, W, D, Gh):
    gl = G["Piece"](f"SM_AK_Case_{t}_Glass")
    a = Acc()
    ox, oy = W / 2 - GLASS_IN, D / 2 - GLASS_IN
    zb = DECK_TOP - 0.001                       # sits on the deck (1 mm into it)
    FB, FH = 0.026, 0.021                       # bottom / top frame height (fix 3: a slimmer top rail, 24 -> 21 mm)
    # bottom frame: a bronze L-channel, its foot 10 mm out over the black deck step (fix 3: case_detail top-left)
    loft(a, ox, oy, 0, 0, [(-FR, zb), (LIP, zb), (LIP, zb + 0.0045), (0, zb + 0.0045), (0, zb + FB), (-FR, zb + FB)],
         BZ, closed=True)
    # top frame: square-section bronze
    loft(a, ox, oy, 0, 0, [(-FR, Gh - FH), (0, Gh - FH), (0, Gh - 0.0015), (-0.0015, Gh), (-FR, Gh)], BZ,
         closed=True)
    # corner posts
    c = 0.0015
    for sx in (-1, 1):
        for sy in (-1, 1):
            poly = [(ox - FR, oy - FR), (ox, oy - FR), (ox, oy - c), (ox - c, oy), (ox - FR, oy)]
            poly = [(sx * x, sy * y) for x, y in poly]
            prism(a, poly, zb + FB - 0.001, Gh - FH + 0.001, BZ, cap0=False, cap1=False)
    # glass panes set in the middle of the frame section, their edges buried in the posts and frames
    pz0, pz1 = zb + FB - 0.002, Gh - FH + 0.002
    e = FR - 0.003
    g0, g1 = FR / 2 - 0.003, FR / 2 + 0.003
    for f in (-1, 1):
        box(a, -(ox - e), ox - e, *sorted((f * (oy - g0), f * (oy - g1))), pz0, pz1, GL, cap0=False, cap1=False)
        box(a, *sorted((f * (ox - g0), f * (ox - g1))), -(oy - e), oy - e, pz0, pz1, GL, cap0=False, cap1=False)
    box(a, -(ox - e), ox - e, -(oy - e), oy - e, Gh - 0.014, Gh - 0.008, GL)
    # warm LED line under the inner edge of the top frame, all four sides
    loft(a, ox - FR, oy - FR, 0, 0, [(-0.007, Gh - FH - 0.004), (0.001, Gh - FH - 0.004), (0.001, Gh - FH + 0.0008),
                                     (-0.007, Gh - FH + 0.0008)], LL, closed=True)
    # fix 3: and a low LED line along the foot of the glass on the deck (case_standard / case_tall front: the bright line
    # at the deck edge inside the glass), its bottom 0.5 mm into the deck, its back 1 mm into the bottom frame
    loft(a, ox - FR, oy - FR, 0, 0, [(-0.005, zb + 0.0005), (0.001, zb + 0.0005), (0.001, zb + 0.0055),
                                     (-0.005, zb + 0.0055)], LL, closed=True)
    # corner plates: a downlight puck under each top corner, an uplight puck on a plate at each bottom corner (the
    # sheets' 8 bright corner dots)
    zp = Gh - FH - 0.009                        # top plate underside
    for sx in (-1, 1):
        for sy in (-1, 1):
            xa, xb = sorted((sx * (ox - 0.070), sx * (ox - FR + 0.002)))
            ya, yb = sorted((sy * (oy - 0.070), sy * (oy - FR + 0.002)))
            box(a, xa, xb, ya, yb, zp, Gh - FH + 0.001, BZ, cap1=False)
            puck(a, sx * (ox - 0.047), sy * (oy - 0.047), zp, True)
            xa, xb = sorted((sx * (ox - 0.070), sx * (ox - FR + 0.002)))
            ya, yb = sorted((sy * (oy - 0.070), sy * (oy - FR + 0.002)))
            box(a, xa, xb, ya, yb, zb, zb + 0.008, BZ, cap0=False)
            puck(a, sx * (ox - 0.047), sy * (oy - 0.047), zb + 0.008, False)
            # fix 2: a slim LED line down the inner edge of each corner post, plate to plate (case_standard: the bright
            # vertical glints along the posts that make the panes read)
            xa, xb = sorted((sx * (ox - FR - 0.0025), sx * (ox - FR + 0.001)))
            ya, yb = sorted((sy * (oy - FR - 0.0025), sy * (oy - FR + 0.001)))
            box(a, xa, xb, ya, yb, zb + 0.0075, zp + 0.0005, "M_AK_HGlint", cap0=False, cap1=False)
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
    # brass top rim wrapping over the edge (hero_plinth top view: a clear brass outline round the top)
    # fix 3: slimmer lines (rim face 10 -> 7 mm, second line 6 -> 4 mm) and the second line lower (its top 3.9 cm
    # under the top edge, hero_plinth.png)
    loft(a, bx, by, rr, segs, [(-0.003, H - 0.007), (0.0025, H - 0.007), (0.0025, H - 0.0012), (0.0013, H),
                               (-0.010, H)], BRB, closed=True)   # fix 2: brushed brass
    loft(a, bx, by, rr, segs, [(-0.003, H - 0.043), (0.0020, H - 0.043), (0.0020, H - 0.039), (-0.003, H - 0.039)],
         BRB, closed=True)
    # recessed base, the amber LED strip under the body (its underside and outer edge glow onto the floor and the
    # base: hero_plinth.png's amber band and floor pool), and four dark-bronze feet at the corners
    loft(a, hw - 0.060, hd - 0.060, 0.010, 2, [(0, 0.0), (0, z0 + 0.002)], LQ)
    loft(a, hw - 0.060, hd - 0.060, 0.010, 2, [(-0.001, 0.042), (0.024, 0.042), (0.024, 0.049), (-0.001, 0.049)],
         [LGH, LG, LG, LG], closed=True)   # fix 3: runs between the feet, 1 mm behind their faces (fix 2: 2.7 cm back)
    fc = 0.002
    for sx in (-1, 1):
        for sy in (-1, 1):
            x0, x1, y0, y1 = hw - 0.095, hw - 0.035, hd - 0.095, hd - 0.035
            poly = [(x0 + fc, y0), (x1 - fc, y0), (x1, y0 + fc), (x1, y1 - fc), (x1 - fc, y1), (x0 + fc, y1),
                    (x0, y1 - fc), (x0, y0 + fc)]
            prism(a, [(sx * x, sy * y) for x, y in poly], 0.0, z0 + 0.002, BK, cap0=False, cap1=False)
    medallion(a, 0.0, -by, (z0 + H - 0.043) / 2, 0.09, -1, k=0.7)   # fix 2: a slimmer disc (9 mm stand-off)
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
