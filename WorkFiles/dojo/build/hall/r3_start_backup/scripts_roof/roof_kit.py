"""DOJO ROOF SYSTEM (kit 4): a reusable kawara roof API for every dojo building (hall, storehouse, residence,
corridors, pavilion, shed). Pure geometry: it fills kit1_geo.Geo containers (raw parts, per-face material name and UV
frame) and returns collision hull point lists; the kit build script turns them into meshes with the shared mesh
module Scripts/dojo/roof/kit_mesh.py (Piece, geo_to_object, UV1 / LOD helpers), so a kit never imports the hall
builder.

Reference: References/Dojo/dojo_roof_details_ref.png (AI-generated modelling reference, REFERENCE_LOG.md), panels
  a  tile field: pans + round tiles in courses, round-ended eave tiles (plain disc: rim, inner ring, low boss), a
     fascia board (kayaoi) over closely spaced square rafter ends with X-marked iron caps
                                                                            -> tile_field, eave_trim, rafters(caps)
  b  ridge: mortar bed, stacked flat ridge tiles (noshi), a banded round cap tile with iron straps; the stepped
     block-and-disc ridge end                                                             -> ridge, ridge_end
  c  hip-and-gable corner: a banded round hip cap on noshi, straps, a disc end block at the eave corner, gentle
     upsweep                                                                              -> hip, sag_warp
  d  gable end of the hip-and-gable roof: dark vertical boarding (or plaster in a timber frame), tie beam, king post
                                                                                          -> gable_face, bargeboards
  e  verge of a plain gable roof: verge noshi + round verge roll ending in a disc, bargeboard, plain ridge end
                                                                                          -> verge, gable_roof
  f  half-round gutter on hooked brackets, round downpipe with a two-bend swan neck and wall clamps
                                                                                          -> gutter, downpipe
  (hall sheet) the frieze board closing the rafter bays over a wall line                  -> eave_blocking
Compound builders (world coordinates, 25 deg by default; spec rule R4):
  irimoya(...)      hip-and-gable roof (the hall's upper roof): returns separate Geos for the main slopes, the two
                    ends and the ridge, so a kit can split them into instanced pieces; optional front_recess (the
                    hall sheet's raised centre eave framed by two descending diagonal ridges)
  lean_to_wrap(...) a lean-to that wraps the front and both sides of a body with hips at the front corners and verges
                    at the back (the hall's lower veranda roof)
  chidori_hafu(...) a small front-facing gable standing on a lean-to slope (the hall sheet's side view)
  gable_roof(...)   plain gable (kirizuma), for the storehouse / residence / corridors
Collision (spec 5.3): one flat slab per slope (the tile tops = the walkable plane); tiles themselves have none.

Frames: a slope is RoofSlope(eave_a, eave_b, z_eave): the eave line in plan from a to b with the roof on its LEFT,
z_eave = the COLLISION (tile-top) height at the eave. Its kit1_geo.Slope `sl` sits on the tile BASE plane
(TILE_TOP below the collision plane, measured normal to the slope): u along the eave from a, s up the slope.
Kit 1's tile code (Scripts/dojo/kit1_geo.py) is imported, not edited; the tile field / roll run are copied here with
the roof sheet's plain eave disc.
"""
import math
import sys
from pathlib import Path

from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))       # Scripts/dojo (kit1_geo)
import kit1_geo as K  # noqa: E402
from kit1_geo import Geo, Slope, box, obox, prism, lathe, dome, clip, warp  # noqa: E402,F401

VERSION = "1.1.0"   # 1.1.0 (hall fix round): eave_blocking, rafter X caps, banded + strapped ridge / hip caps,
                    # stepped block-and-disc ends (lower), irimoya front_recess + plaster gable frame, chidori_hafu
TILE = "M_DJ_RoofTile"
TIMBER = "M_DJ_TimberDark"
IRON = "M_DJ_Iron"
PLASTER = "M_DJ_PlasterCream"
UNDER = "M_DJ_RoofTile"            # the upper face of the sarking (never brown between the courses: kit 1 f2 lesson)

P = K.P                            # round-tile pitch 0.25
ROLL_R = K.ROLL_R
ROLL_NC = K.ROLL_NC
PAN_BASE = K.PAN_BASE
PAN_D = K.PAN_D
STEP_E = K.STEP_E
DISC_R = K.DISC_R
TILE_TOP = K.TILE_TOP              # 0.105: roll top above the tile base plane (= the collision plane)
ARC = K.ARC
PITCH_DEG = 25.0


def base_off(pitch_deg=PITCH_DEG):
    """Vertical offset from the collision plane down to the tile base plane."""
    return TILE_TOP / math.cos(math.radians(pitch_deg))


# ------------------------------------------------------------------------------------------------ slope frame
class RoofSlope:
    """One roof plane. eave_a / eave_b: the eave line in plan (x, y), the roof on its LEFT; z_eave: collision height at
    the eave line; pitch in degrees."""

    def __init__(self, eave_a, eave_b, z_eave, pitch=PITCH_DEG):
        a, b = Vector((eave_a[0], eave_a[1], 0.0)), Vector((eave_b[0], eave_b[1], 0.0))
        self.a2, self.b2 = a, b
        self.U2 = (b - a).normalized()
        self.S2 = Vector((-self.U2.y, self.U2.x, 0.0))               # inward (left of a -> b), in plan
        self.pitch = pitch
        self.tn = math.tan(math.radians(pitch))
        self.cs = math.cos(math.radians(pitch))
        self.sn = math.sin(math.radians(pitch))
        self.z_eave = z_eave
        self.length = (b - a).length
        S = self.S2 * self.cs + Vector((0, 0, self.sn))
        self.sl = Slope(a + Vector((0, 0, z_eave - base_off(pitch))), self.U2, S)

    # plan run (horizontal distance from the eave) <-> slope distance
    def s_of_run(self, run):
        return run / self.cs

    def run_of(self, p):
        return (Vector((p[0], p[1], 0.0)) - self.a2).dot(self.S2)

    def u_of(self, p):
        return (Vector((p[0], p[1], 0.0)) - self.a2).dot(self.U2)

    def zcol(self, p):
        """Collision height over plan point p."""
        return self.z_eave + self.run_of(p) * self.tn

    def col_pt(self, x, y):
        return Vector((x, y, self.zcol((x, y))))

    def at(self, u, s, n=0.0):
        return self.sl.at(u, s, n)


# ------------------------------------------------------------------------------------------------ discs / rolls
def plain_disc(g, centre, facing, up, r, thick, mat=TILE, nseg=16):
    """The roof sheet's round end tile: a short cylinder whose face (at `centre`, facing `facing`) has a raised rim, a
    recessed field with a thin raised inner ring and a low centre boss. Plain: no crest, no swirl (STYLE_GUIDE 10)."""
    rc = 0.007
    prof = [(-thick, r), (0.0, r), (0.0, r * 0.82), (-rc, r * 0.82), (-rc, r * 0.52), (-0.002, r * 0.52),
            (-0.002, r * 0.43), (-rc, r * 0.43), (-rc, r * 0.20), (-0.003, r * 0.15), (-0.001, r * 0.07),
            (-0.001, 0.0)]
    lathe(g, centre, facing, up, prof, mat, arc=None, nseg=nseg)
    return g


def course_off(s, C):
    """Course step profile at slope distance s for course length C: the tile thickness STEP_E showing at each course's
    lower edge, falling linearly to 0 at the course's top (so each course laps the one below)."""
    f = (s / C) % 1.0
    return STEP_E * (1.0 - f)


def pan_shape(u, phase):
    return 0.5 + 0.5 * math.cos(2 * math.pi * (u - phase) / P)


def seg_profile(Lr, r, first):
    if first:
        return [(0.0, r + 0.004), (Lr, r - 0.003)]
    return [(0.0, r - 0.014), (0.0, r + 0.011), (0.022, r + 0.011), (0.040, r + 0.004), (Lr, r - 0.003)]


def roll_run(g, sl, uc, s0, s1, C, mat=TILE, eave=True, arc_seg=8, r=ROLL_R, nc=ROLL_NC, disc_r=DISC_R):
    """One line of round tiles up a slope at u = uc (interlocking segments, one per course), a plain end disc at the
    eave."""
    fr = sl.frame()
    j = int(math.floor(s0 / C + 1e-9))
    first = True
    while j * C < s1 - 1e-6:
        sa = max(j * C, s0)
        sb = min((j + 1) * C, s1)
        if sb - sa < 0.01:
            j += 1
            continue
        lap = (abs(sa - j * C) < 1e-6) and not (first and eave)
        ca = sl.at(uc, sa, nc + course_off(sa + 1e-7, C))
        cb = sl.at(uc, sb, nc + course_off(sb - 1e-7, C))
        axis = cb - ca
        Lr = axis.length
        axis.normalize()
        lathe(g, ca, axis, sl.N, seg_profile(Lr, r, not lap), mat, arc=ARC, nseg=arc_seg, frame=fr)
        if first and eave:
            plain_disc(g, ca - axis * 0.004, -axis, sl.N, disc_r, 0.028, mat)
        first = False
        j += 1
    return g


def tile_field(g, sl, u0, u1, s0, s1, C, mat=TILE, eave=True, phase=0.0, roll_margin=0.02, pan_per_p=6, arc_seg=8,
               u_skip=(), rolls=True):
    """Pans + round tiles over u in [u0, u1], s in [s0, s1] on the kit1_geo Slope `sl` (courses anchored at s = 0,
    the eave). Rolls at u = phase + (k + 0.5) P fully inside [u0 + margin, u1 - margin]. eave: the pan lip and the end
    discs at s = 0 (only when s0 == 0). u_skip: roll centres to leave out."""
    fr = sl.frame()
    step = P / pan_per_p
    us = {u0, u1}
    k0 = math.floor((u0 - phase) / step)
    k1 = math.ceil((u1 - phase) / step)
    for k in range(k0, k1 + 1):
        u = phase + k * step
        if u0 + 1e-4 < u < u1 - 1e-4:
            us.add(u)
    us = sorted(us)
    rows = []
    j0 = int(math.floor(s0 / C + 1e-9))
    if eave and s0 <= 1e-9:
        rows.append((0.0, PAN_BASE - 0.045 + STEP_E))
        rows.append((0.0, PAN_BASE + STEP_E))
    else:
        rows.append((s0, PAN_BASE + course_off(s0, C)))
    j = j0 + 1
    while j * C < s1 - 1e-6:
        sj = j * C
        if sj > s0 + 1e-6:
            rows.append((sj, PAN_BASE + 0.0))
            rows.append((sj, PAN_BASE + STEP_E))
        j += 1
    rows.append((s1, PAN_BASE + course_off(s1 - 1e-7, C)))
    verts, faces = [], []
    for (s, n) in rows:
        for u in us:
            verts.append(sl.at(u, s, n - PAN_D * pan_shape(u, phase)))
    m = len(us)
    for r in range(len(rows) - 1):
        for i in range(m - 1):
            a = r * m + i
            faces.append((a, a + 1, a + 1 + m, a + m))
    g.add(verts, faces, mat, fr)
    if not rolls:
        return g
    kmin = math.floor((u0 - phase) / P) - 1
    kmax = math.ceil((u1 - phase) / P) + 1
    for k in range(kmin, kmax + 1):
        uc = phase + (k + 0.5) * P
        if uc - ROLL_R < u0 + roll_margin or uc + ROLL_R > u1 - roll_margin:
            continue
        if any(abs(uc - x) < 1e-6 for x in u_skip):
            continue
        roll_run(g, sl, uc, s0, s1, C, mat, eave=eave and s0 <= 1e-9, arc_seg=arc_seg)
    return g


def roll_line(g, p0, p1, up, mat=TILE, r=ROLL_R, seg=0.30, disc_start=None, disc_end=None, nseg=8):
    """Straight run of interlocking round tiles p0 -> p1 (ridge, verge, hip); each tile's lapping collar at its p0
    end; plain end discs."""
    p0, p1 = Vector(p0), Vector(p1)
    axis = p1 - p0
    Ltot = axis.length
    axis.normalize()
    n = max(1, int(round(Ltot / seg)))
    ls = Ltot / n
    for i in range(n):
        ca = p0 + axis * (i * ls)
        lathe(g, ca, axis, up, seg_profile(ls, r, i == 0 and disc_start is not None), mat, arc=ARC, nseg=nseg)
    if disc_start:
        plain_disc(g, p0 - axis * 0.004, -axis, up, disc_start, 0.03, mat)
    if disc_end:
        plain_disc(g, p1 + axis * 0.004, axis, up, disc_end, 0.03, mat)
    return g


noshi_stack = K.noshi_stack


# ------------------------------------------------------------------------------------------------ clipping
def plan_clip(g, a, b, keep):
    """Keep the part of g on the side of the vertical plane through plan points a -> b that contains plan point keep."""
    a3, b3 = Vector((a[0], a[1], 0.0)), Vector((b[0], b[1], 0.0))
    d = (b3 - a3).normalized()
    n = Vector((-d.y, d.x, 0.0))
    if (Vector((keep[0], keep[1], 0.0)) - a3).dot(n) < 0:
        n = -n
    return clip(g, [(a3, n)])


def plane_clip(g, point, normal):
    """Keep the part of g on the side of the plane through `point` that `normal` points to (any plane, not only
    vertical ones; e.g. the main roof plane under a chidori-hafu). Returns a new Geo."""
    return clip(g, [(Vector(point), Vector(normal))])


def clip_poly2(poly, a, b, keep):
    """Clip a convex plan polygon [(x, y), ...] to the side of the line a -> b that contains plan point `keep`
    (Sutherland-Hodgman). Used to split the collision slabs along the same lines the geometry is clipped on."""
    ax, ay = a
    dx, dy = b[0] - a[0], b[1] - a[1]

    def side(p):
        return dx * (p[1] - ay) - dy * (p[0] - ax)
    sk = 1.0 if side(keep) >= 0 else -1.0
    out = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        sp, sq = side(p) * sk, side(q) * sk
        if sp >= 0:
            out.append(p)
        if (sp >= 0) != (sq >= 0):
            t = sp / (sp - sq)
            out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    return out


def poly2_area(poly):
    return 0.5 * abs(sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
                         for i in range(len(poly))))


# ------------------------------------------------------------------------------------------------ slope parts
def slope_tiles(rs, u0, u1, s0, s1, C, phase=0.0, eave=True, mat=TILE, roll_margin=0.02, u_skip=()):
    """A new Geo holding one tile field (pans + round tiles) on the RoofSlope rs over u0..u1 along the eave and s0..s1
    up the slope (courses of length C from the eave; eave discs only when s0 == 0). Thin wrapper of tile_field."""
    g = Geo()
    tile_field(g, rs.sl, u0, u1, s0, s1, C, mat, eave=eave, phase=phase, roll_margin=roll_margin, u_skip=u_skip)
    return g


def sarking(g, rs, u0, u1, s0, s1, nstrips=8, th=0.025, gap=0.004, mat=TIMBER, top_mat=UNDER):
    """Boards under the tiles (the soffit seen from below), in strips up the slope so they follow a warped (sagged)
    slope; the upper face carries the tile colour (nothing brown shows between the courses)."""
    sl = rs.sl
    for k in range(nstrips):
        sa = s0 + (s1 - s0) * k / nstrips
        sb = s0 + (s1 - s0) * (k + 1) / nstrips
        c = sl.at((u0 + u1) / 2, (sa + sb) / 2, -gap - th / 2)
        obox(g, c, sl.U, sl.S, sl.N, (u1 - u0) / 2, (sb - sa) / 2, th / 2, mat, skip=("+z",))
        q = [sl.at(u0, sa, -gap), sl.at(u1, sa, -gap), sl.at(u1, sb, -gap), sl.at(u0, sb, -gap)]
        g.add(q, [(0, 1, 2, 3)], top_mat, sl.frame())
    return g


def rafter_cap(g, centre, out, up, w, d, mat=IRON, t=0.004, bar=0.011):
    """The roof sheet's X-marked end cap (panel a) on a square rafter / purlin end: a thin iron plate on the end face
    (centre, facing `out`) with two crossed flat bars proud of it."""
    f = Vector(out).normalized()
    u = Vector(up)
    u = (u - f * u.dot(f)).normalized()
    s = u.cross(f).normalized()
    c = Vector(centre)
    obox(g, c + f * (t / 2), f, s, u, t / 2, w / 2 - 0.006, d / 2 - 0.006, mat)
    L = math.hypot(w - 0.022, d - 0.022) / 2
    for sd in (-1, 1):
        a = (s * (w - 0.022) + u * (sd * (d - 0.022))).normalized()
        b = f.cross(a).normalized()
        obox(g, c + f * (t + t / 2), f, a, b, t / 2, L, bar / 2, mat)
    return g


def rafters(g, rs, u0, u1, s_tail, s_end, spacing=0.45, w=0.09, d=0.10, gap=0.004, sark=0.025, mat=TIMBER,
            u_list=None, caps=False, cap_mat=IRON):
    """Rafters (taruki) under the sarking from s_tail (<= 0: the square tails project past the eave line) to s_end.
    caps: an X-marked iron cap on every tail end (roof sheet panel a). Returns the u positions."""
    sl = rs.sl
    if u_list is None:
        n = max(1, int(round((u1 - u0) / spacing)))
        u_list = [u0 + (u1 - u0) * (i + 0.5) / n for i in range(n)]
    for u in u_list:
        c = sl.at(u, (s_tail + s_end) / 2, -gap - sark - d / 2)
        obox(g, c, sl.S, sl.U, sl.N, (s_end - s_tail) / 2, w / 2, d / 2, mat)
        if caps:
            rafter_cap(g, sl.at(u, s_tail, -gap - sark - d / 2), -sl.S, sl.N, w, d, cap_mat)
    return u_list


def eave_blocking(g, rs, u0, u1, run, rafter_d=0.10, t=0.045, drop=0.10, gap=0.004, sark=0.025, mat=TIMBER):
    """Frieze board (menado-ita) over a wall line: a plumb board at plan distance `run` from the eave line of the
    RoofSlope rs, u0..u1 along it, from just inside the sarking down past the rafter underside by `drop` (it laps the
    wall plate below). It closes the open bays between the rafters, so the roof space never shows between the wall
    plate and the sarking."""
    zsu = lambda r: rs.z_eave + r * rs.tn - base_off(rs.pitch) - (gap + sark) / rs.cs   # noqa: E731
    zt = zsu(run - t / 2) + 0.01
    zb = zsu(run) - rafter_d / rs.cs - drop
    pc = rs.a2 + rs.U2 * ((u0 + u1) / 2) + rs.S2 * run
    obox(g, Vector((pc.x, pc.y, (zt + zb) / 2)), rs.U2, rs.S2, (0, 0, 1), (u1 - u0) / 2, t / 2, (zt - zb) / 2, mat)
    return g


def eave_trim(g, rs, u0, u1, fascia_h=0.075, fascia_t=0.05, lip=0.02, mat=TIMBER):
    """The kayaoi: a fascia board along the eave under the tile lip, lying on the rafter tails (panel a)."""
    sl = rs.sl
    c = sl.at((u0 + u1) / 2, -lip + fascia_t / 2, -0.004 - fascia_h / 2 + 0.012)
    obox(g, c, sl.U, sl.S, sl.N, (u1 - u0) / 2, fascia_t / 2, fascia_h / 2, mat)
    return g


def beam(g, a, b, w, h, mat=TIMBER, up=(0, 0, 1)):
    """A timber member from a to b (centre line), w wide, h deep (h along `up`)."""
    a, b = Vector(a), Vector(b)
    ax = (b - a).normalized()
    upv = Vector(up)
    upv = (upv - ax * upv.dot(ax)).normalized()
    side = upv.cross(ax).normalized()
    obox(g, (a + b) / 2, ax, side, upv, (b - a).length / 2, w / 2, h / 2, mat)
    return g


# ------------------------------------------------------------------------------------------------ ridge / hips
def cap_straps(g, p0, p1, up, r, seg, w=0.034, t=0.006, mat=IRON, arc=(-24.0, 204.0), nseg=12, skip_first=True):
    """Iron straps over a banded round cap (ridge_cap): one thin band round the cap at every tile joint (`seg` apart
    from p0, the joints of kit1_geo.ridge_tube), so the cap reads as strapped segments (roof sheet panel b)."""
    p0, p1 = Vector(p0), Vector(p1)
    ax = p1 - p0
    L = ax.length
    ax.normalize()
    nt = max(1, int(round(L / seg)))
    ls = L / nt
    for i in range(1 if skip_first else 0, nt):
        c = p0 + ax * (i * ls - 0.004)
        lathe(g, c, ax, up, [(0.0, r - 0.004), (0.0, r + t), (w, r + t), (w, r - 0.004)], mat, arc=arc, nseg=nseg)
    return g


def ridge_cap(g, p0, p1, up, r, seg=0.40, mat=TILE, straps=True, strap_mat=IRON, band_dr=0.016, band_w=0.036,
              cap_start=True, cap_end=True):
    """The banded round cap tile (kanmuri-gawara) of a ridge or hip, p0 -> p1 on its axis: kit1_geo.ridge_tube's
    tiles, each with a raised collar at its lapping joint, and an iron strap over every joint."""
    K.ridge_tube(g, p0, p1, up, mat, r, seg=seg, band_w=band_w, band_dr=band_dr, nseg=14, cap_start=cap_start,
                 cap_end=cap_end)
    if straps:
        cap_straps(g, p0, p1, up, r + band_dr, seg, w=band_w + 0.012, mat=strap_mat)
    return g


def ridge(g, p0, p1, z_planes, widths=(0.52, 0.48, 0.44, 0.40), h=0.065, roll_r=0.12, bed_w=0.56, mat=TILE,
          bed_mat=TILE, seed=41, seg=0.40, straps=True):
    """Main ridge along p0 -> p1 (plan points, horizontal): a bed from the tile base up, stacked noshi layers and a
    banded round cap tile with an iron strap over every joint (roof sheet panel b). z_planes = where the collision
    planes meet. Returns (cap top z, noshi base z)."""
    p0, p1 = Vector((p0[0], p0[1], 0.0)), Vector((p1[0], p1[1], 0.0))
    ax = (p1 - p0).normalized()
    side = Vector((0, 0, 1)).cross(ax).normalized()
    zb = z_planes - 0.13
    z0 = z_planes - 0.02
    c = (p0 + p1) / 2
    obox(g, Vector((c.x, c.y, (zb + z0) / 2)), ax, side, (0, 0, 1), (p1 - p0).length / 2, bed_w / 2, (z0 - zb) / 2,
         bed_mat)
    a = Vector((p0.x, p0.y, z0))
    b = Vector((p1.x, p1.y, z0))
    top = noshi_stack(g, a + ax * 0.04, b - ax * 0.04, (0, 0, 1), list(widths), h, mat, seg=0.30, seed=seed)
    kz = z0 + top + roll_r * 0.45
    ridge_cap(g, Vector((p0.x, p0.y, kz)) + ax * 0.06, Vector((p1.x, p1.y, kz)) - ax * 0.06, (0, 0, 1), roll_r,
              seg=seg, mat=mat, straps=straps)
    return kz + roll_r + 0.016, z0


def _oct_prism(g, face_c, f, s, u, hw, hh, depth, ch, mat):
    """A chamfered-rectangle (octagon) prism: its show face centred at face_c facing f, hw / hh half sizes across (s)
    and up (u), extruded `depth` back along -f."""
    ch = min(ch, 0.45 * hw, 0.45 * hh)
    pts = [(-hw + ch, -hh), (hw - ch, -hh), (hw, -hh + ch), (hw, hh - ch), (hw - ch, hh), (-hw + ch, hh),
           (-hw, hh - ch), (-hw, -hh + ch)]
    prism(g, [face_c + s * a + u * b for a, b in pts], f, depth, mat, frame=(f, s, u))
    return g


def ridge_end(g, base, facing, W=0.80, H=0.95, T=0.45, mat=TILE, wings=True):
    """The roof sheet's stepped block-and-disc ridge end (panel b, onigawara; plain, no symbol): a wide chamfered plinth
    tier with a projecting band, a narrower chamfered second tier, and a big round disc tile standing on it (raised rim,
    inner ring, low boss on its show face); small stepped wing blocks either side of the second tier. It stays low: the
    whole end is H tall (the fix round keeps it within 0.5 m of the ridge cap). base = bottom centre, show face ->
    facing. Returns the top height above base."""
    f = Vector(facing).normalized()
    u = Vector((0, 0, 1))
    u = (u - f * u.dot(f)).normalized()
    s = u.cross(f).normalized()
    b = Vector(base)
    h1, h2 = 0.26 * H, 0.16 * H
    _oct_prism(g, b + u * (h1 / 2) + f * (T / 2), f, s, u, W / 2, h1 / 2, T, 0.035, mat)
    obox(g, b + u * (h1 - 0.014), f, s, u, T / 2 + 0.014, W / 2 + 0.014, 0.014, mat)
    _oct_prism(g, b + u * (h1 + h2 / 2) + f * (0.44 * T), f, s, u, 0.39 * W, h2 / 2, 0.88 * T, 0.03, mat)
    R = min(0.45 * W, (H - h1 - h2) / 1.92)
    zc = H - R
    c = b + u * zc
    # the disc tile: a thick round tile standing at the front of the second tier, a low backing block behind it
    dt = max(0.10, 0.34 * T)
    prism(g, K.ngon(c + f * (0.44 * T), s, u, R, 28), f, dt, mat, frame=(f, s, u))
    plain_disc(g, c + f * (0.44 * T + 0.022), f, u, 0.97 * R, 0.022, mat, nseg=28)
    _oct_prism(g, b + u * (h1 + h2 + 0.30 * R) + f * (0.44 * T - dt + 0.01), f, s, u, 0.62 * R, 0.30 * R,
               0.84 * T - dt, 0.02, mat)
    if wings:
        for sd in (-1, 1):
            obox(g, b + u * (h1 + 0.5 * h2 + 0.02) + s * (sd * (0.39 * W + 0.05)), f, s, u, 0.34 * T, 0.05,
                 0.5 * h2 + 0.02, mat)
    return H


def hip(g, a, b, n_left, n_right, widths=(0.34, 0.31, 0.28), h=0.055, roll_r=0.10, end_disc=0.15, lift=0.0, mat=TILE,
        bed_mat=TILE, sumi_oni=None, seed=7, seg=0.40, straps=True):
    """A hip or descending ridge (panel c) from the eave corner a to b (3D points ON the collision surface along the
    line): a bed, noshi layers, a banded round cap tile with an iron strap over every joint and a plain end disc at the
    eave corner (profile about 0.3 m). n_left / n_right: the two slope normals (the stack's up = their bisector; equal
    for a ridge laid on one plane). sumi_oni = (W, H, T) puts a small stepped block-and-disc end at the corner in place
    of the bare disc. Returns the cap's top offset."""
    a, b = Vector(a), Vector(b)
    ax = (b - a).normalized()
    up = (Vector(n_left) + Vector(n_right)).normalized()
    up = (up - ax * up.dot(ax)).normalized()
    side = up.cross(ax).normalized()
    z0 = -0.05 + lift
    L = (b - a).length
    c = (a + b) / 2 + up * (z0 - 0.05)
    obox(g, c, ax, side, up, L / 2, widths[0] / 2 + 0.02, 0.05, bed_mat)
    top = noshi_stack(g, a + up * z0 + ax * 0.10, b + up * z0, up, list(widths), h, mat, seg=0.30, seed=seed)
    rz = z0 + top + roll_r * 0.45
    p0 = a + up * rz + ax * 0.02
    ridge_cap(g, p0, b + up * rz, up, roll_r, seg=seg, mat=mat, straps=straps, cap_start=True, cap_end=True)
    if not sumi_oni and end_disc:
        plain_disc(g, p0 - ax * 0.004, -ax, up, end_disc, 0.035, mat, nseg=24)
    if sumi_oni:
        W, H, T = sumi_oni
        hor = Vector((-ax.x, -ax.y, 0.0)).normalized()
        ridge_end(g, a + up * (z0 - 0.02) + ax * 0.02, hor, W, H, T, mat, wings=False)
    return rz + roll_r


def wall_flashing(g, p0, p1, n_slope, widths=(0.22, 0.18), h=0.04, mat=TILE, seed=11):
    """Where a lean-to meets a wall: a short noshi stack laid along the top of the tiles against the wall."""
    top = noshi_stack(g, Vector(p0), Vector(p1), n_slope, list(widths), h, mat, seg=0.30, seed=seed)
    return top


# ------------------------------------------------------------------------------------------------ verge / gable
def verge(g, rs, u_edge, s0, s1, inward=1, widths=(0.26, 0.22), h=0.042, roll_r=0.075, seat=0.030, mat=TILE,
          disc=0.085, board=True, board_h=0.26, board_t=0.056, board_mat=TIMBER, seed=5, banded=False):
    """Verge (panel e): along the slope edge u = u_edge, a stack of flat verge tiles under a round verge roll with a
    plain end disc at the eave, and a bargeboard (hafu) under the edge. inward: +1 if the roof lies at u > u_edge.
    banded=True: the roll is the strapped banded cap (ridge_cap), as on the hall's descending ridges."""
    sl = rs.sl
    uc = u_edge + inward * 0.14
    a0 = sl.at(uc, s0 + 0.02, seat)
    a1 = sl.at(uc, s1 - 0.02, seat)
    top = noshi_stack(g, a0, a1, sl.N, list(widths), h, mat, seg=0.30, seed=seed)
    if banded:
        p0 = sl.at(uc, s0 + 0.03, seat + top + roll_r * 0.45)
        ridge_cap(g, p0, sl.at(uc, s1 - 0.05, seat + top + roll_r * 0.45), sl.N, roll_r, seg=0.40, mat=mat)
        if disc:
            plain_disc(g, p0 - sl.S * 0.004, -sl.S, sl.N, disc, 0.03, mat, nseg=24)
        top = top + roll_r * 0.45 - 0.05
    else:
        roll_line(g, sl.at(uc, s0 + 0.03, seat + top + 0.05), sl.at(uc, s1 - 0.05, seat + top + 0.05), sl.N, mat,
                  r=roll_r, seg=0.30, disc_start=disc)
    if board:
        ub = u_edge + inward * (board_t / 2 + 0.003)
        a = sl.at(ub, s0 - 0.02, -0.03 - board_h / 2)
        b = sl.at(ub, s1, -0.03 - board_h / 2)
        ax = (b - a).normalized()
        obox(g, (a + b) / 2, ax, sl.U, sl.N, (b - a).length / 2, board_t / 2, board_h / 2, board_mat)
    return seat + top + 0.05 + roll_r


def gable_face(g, x, y0, y1, z_foot, y_apex, z_apex, facing, style="boards", board_w=0.20, t=0.03, mat=TIMBER,
               plaster=PLASTER, tie_h=0.24, tie_w=0.18, post_w=0.18, seed=3, tie_drop=0.0, frame=False):
    """The gable triangle in the vertical plane X = x (panel d): its base from (y0, z_foot) to (y1, z_foot), apex
    (y_apex, z_apex); facing = +1 / -1 along X (the outside). style 'boards': dark vertical boarding with battens;
    'plaster': a cream plaster triangle. Plus a tie beam along the base and a king post to the apex. frame=True (the
    hall sheet's side view): a timber frame proud of the plaster, a horizontal beam (nuki) at about 45 % of the
    height and two short studs under it."""
    fx = facing
    if frame:
        zm = z_foot + tie_h + 0.45 * (z_apex - z_foot - tie_h)
        hw = (y_apex - y0) * (1.0 - (zm - z_foot) / (z_apex - z_foot))
        hw1 = (y1 - y_apex) * (1.0 - (zm - z_foot) / (z_apex - z_foot))
        xa, xc = sorted((x - fx * 0.05, x + fx * 0.045))
        box(g, xa, xc, y_apex - hw + 0.02, y_apex + hw1 - 0.02, zm - 0.075, zm + 0.075, mat, grain="y")
        for k in (-1, 1):
            yy = y_apex + k * 0.5 * (hw if k < 0 else hw1)
            box(g, xa, xc, yy - 0.06, yy + 0.06, z_foot + tie_h - 0.01, zm - 0.07, mat, grain="z")

    def top_z(y):
        if y <= y_apex:
            return z_foot + (z_apex - z_foot) * (y - y0) / (y_apex - y0)
        return z_foot + (z_apex - z_foot) * (y1 - y) / (y1 - y_apex)

    xb = x
    if style == "plaster":
        pts = [Vector((xb, y0, z_foot)), Vector((xb, y1, z_foot)), Vector((xb, y_apex, z_apex))]
        prism(g, [p + Vector((fx * 0.0, 0, 0)) for p in pts], (fx, 0, 0), 0.10, plaster,
              frame=(Vector((0, 1, 0)), Vector((0, 0, 1)), Vector((1, 0, 0))))
    else:
        n = max(2, int(round((y1 - y0) / board_w)))
        bw = (y1 - y0) / n
        for i in range(n):
            ya, yb = y0 + i * bw + 0.002, y0 + (i + 1) * bw - 0.002
            pts = [(ya, z_foot), (yb, z_foot), (yb, top_z(yb))]
            if ya < y_apex < yb:
                pts.append((y_apex, z_apex))
            pts.append((ya, top_z(ya)))
            poly = [Vector((xb, p[0], p[1])) for p in pts]
            dx = 0.004 * ((i * 7919 + seed) % 3 - 1)
            poly = [p + Vector((fx * dx, 0, 0)) for p in poly]
            prism(g, poly, (fx, 0, 0), t, mat, frame=(Vector((0, 0, 1)), Vector((0, 1, 0)), Vector((1, 0, 0))))
        for i in range(1, n):     # battens over the joints, proud of the boards
            yb_ = y0 + i * bw
            zt = top_z(yb_) - 0.04
            if zt - (z_foot + tie_h) > 0.10:
                xa, xc = sorted((xb, xb + fx * 0.022))
                box(g, xa, xc, yb_ - 0.02, yb_ + 0.02, z_foot + tie_h, zt, mat, grain="z")

    def xs(back, front):
        return sorted((xb - fx * back, xb + fx * front))
    # tie beam along the base, king post to the apex, a plain block where they meet
    xa, xc = xs(0.10, 0.06)
    box(g, xa, xc, y0 - 0.10, y1 + 0.10, z_foot - tie_drop, z_foot + tie_h, mat, grain="y")
    xa, xc = xs(0.06, 0.05)
    box(g, xa, xc, y_apex - post_w / 2, y_apex + post_w / 2, z_foot + tie_h, z_apex - 0.05, mat, grain="z")
    xa, xc = xs(0.02, 0.09)
    box(g, xa, xc, y_apex - 0.14, y_apex + 0.14, z_foot + tie_h - 0.02, z_foot + tie_h + 0.20, mat, grain="z")
    return g


def bargeboards(g, x, y0, y1, z0, y_apex, z_apex, facing, h=0.30, t=0.06, mat=TIMBER, gegyo=True):
    """Bargeboards (hafu) along both rakes of a gable in the plane X = x, from the feet (y0 / y1 at z0) to the apex,
    plus a plain hanging board (gegyo) at the apex."""
    fx = facing
    for yf in (y0, y1):
        a = Vector((x, yf, z0))
        b = Vector((x, y_apex, z_apex))
        ax = (b - a).normalized()
        w = ax.cross(Vector((1, 0, 0))).normalized()
        if w.z < 0:
            w = -w
        obox(g, (a + b) / 2 - w * (h / 2), ax, (1, 0, 0), w, (b - a).length / 2 + 0.03, t / 2, h / 2, mat)
    if gegyo:
        za = z_apex - 0.05
        poly = [(x + fx * t, y_apex - 0.16, za - 0.30), (x + fx * t, y_apex + 0.16, za - 0.30),
                (x + fx * t, y_apex + 0.22, za - 0.12), (x + fx * t, y_apex, za), (x + fx * t, y_apex - 0.22, za - 0.12)]
        prism(g, poly, (fx, 0, 0), 0.05, mat, frame=(Vector((0, 0, 1)), Vector((0, 1, 0)), Vector((1, 0, 0))))
    return g


# ------------------------------------------------------------------------------------------------ tubes (gutter, pipe)
def tube(g, centres, r, mat=IRON, nseg=12, up=(0, 0, 1), cap0=False, cap1=False):
    """A closed round tube through `centres` (list of Vectors; ring frames parallel-transported), optional flat caps."""
    n = len(centres)
    tangents = []
    for i in range(n):
        p0 = centres[max(i - 1, 0)]
        p1 = centres[min(i + 1, n - 1)]
        tangents.append((p1 - p0).normalized())
    ref = Vector(up)
    if abs(ref.dot(tangents[0])) > 0.95:
        ref = Vector((1, 0, 0)) if abs(tangents[0].x) < 0.9 else Vector((0, 1, 0))
    x = (ref - tangents[0] * ref.dot(tangents[0])).normalized()
    verts, rings = [], []
    for i in range(n):
        t = tangents[i]
        x = (x - t * x.dot(t)).normalized()          # parallel transport
        y = t.cross(x).normalized()
        idx = []
        for k in range(nseg):
            a = 2 * math.pi * k / nseg
            idx.append(len(verts))
            verts.append(centres[i] + x * (r * math.cos(a)) + y * (r * math.sin(a)))
        rings.append(idx)
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(nseg):
            k1 = (k + 1) % nseg
            faces.append((r0[k], r0[k1], r1[k1], r1[k]))
    if cap0:
        c = len(verts)
        verts.append(centres[0])
        for k in range(nseg):
            faces.append((c, rings[0][(k + 1) % nseg], rings[0][k]))
    if cap1:
        c = len(verts)
        verts.append(centres[-1])
        for k in range(nseg):
            faces.append((c, rings[-1][k], rings[-1][(k + 1) % nseg]))
    g.add(verts, faces, mat, (tangents[0], x, tangents[0].cross(x)))
    return g


def fillet_path(pts, radius, steps=6):
    """Polyline with every inner corner rounded by an arc of `radius` (bends of a pipe)."""
    pts = [Vector(p) for p in pts]
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        a, b, c = pts[i - 1], pts[i], pts[i + 1]
        d0, d1 = (b - a).normalized(), (c - b).normalized()
        ang = math.acos(max(-1.0, min(1.0, d0.dot(d1))))
        if ang < 1e-3:
            out.append(b)
            continue
        t = min(radius * math.tan(ang / 2), (b - a).length * 0.45, (c - b).length * 0.45)
        p0, p1 = b - d0 * t, b + d1 * t
        for k in range(steps + 1):
            f = k / steps
            q0 = p0.lerp(b, f)
            q1 = b.lerp(p1, f)
            out.append(q0.lerp(q1, f))
    out.append(pts[-1])
    clean = [out[0]]
    for p in out[1:]:
        if (p - clean[-1]).length > 1e-4:
            clean.append(p)
    return clean


def gutter(g, pts, r=0.07, t=0.004, mat=IRON, bracket_every=0.9, fascia_side=None, nseg=10, caps=(True, True)):
    """Half-round gutter along the polyline `pts` (its rim centre line, horizontal): outer and inner skins, rolled rim
    beads, hooked strap brackets every `bracket_every` m fixed to the fascia on `fascia_side` (a unit Vector
    pointing from the gutter to the fascia; None = no brackets), end caps. Panel f."""
    pts = [Vector(p) for p in pts]
    for a, b in zip(pts, pts[1:]):
        ax = (b - a).normalized()
        side = Vector((0, 0, 1)).cross(ax).normalized()
        L = (b - a).length
        m = max(2, int(math.ceil(L / 0.5)))
        for skin, rr, flip in (("out", r, False), ("in", r - t, True)):
            verts, faces = [], []
            for i in range(m + 1):
                c = a + ax * (L * i / m)
                for k in range(nseg + 1):
                    th = math.pi + math.pi * k / nseg                   # lower half: 180 .. 360 deg
                    verts.append(c + side * (rr * math.cos(th)) + Vector((0, 0, rr * math.sin(th))))
            for i in range(m):
                for k in range(nseg):
                    q = (i * (nseg + 1) + k, i * (nseg + 1) + k + 1, (i + 1) * (nseg + 1) + k + 1,
                         (i + 1) * (nseg + 1) + k)
                    faces.append(tuple(reversed(q)) if flip else q)
            g.add(verts, faces, mat, (ax, side, Vector((0, 0, 1))))
        for sd in (-1, 1):                                              # rolled rim beads
            c0 = a + side * (sd * (r - t / 2)) + Vector((0, 0, 0.004))
            tube(g, [c0, c0 + ax * L], 0.0085, mat, nseg=8)
        if fascia_side is not None:
            fs = Vector(fascia_side).normalized()
            nb = max(1, int(L / bracket_every))
            for i in range(nb):
                c = a + ax * (L * (i + 0.5) / nb)
                arc_pts = []
                for k in range(9):
                    th = math.pi + math.pi * k / 8
                    arc_pts.append(c + side * ((r + 0.006) * math.cos(th)) + Vector((0, 0, (r + 0.006) * math.sin(th))))
                if fs.dot(side) < 0:
                    arc_pts.reverse()
                strap_end = arc_pts[-1]
                arc_pts.append(strap_end + Vector((0, 0, 0.03)))
                arc_pts.append(strap_end + Vector((0, 0, 0.03)) + fs * 0.05)
                for p0_, p1_ in zip(arc_pts, arc_pts[1:]):
                    d = (p1_ - p0_)
                    if d.length < 1e-4:
                        continue
                    w = d.normalized().cross(ax).normalized()
                    obox(g, (p0_ + p1_) / 2, d.normalized(), ax, w, d.length / 2 + 0.002, 0.012, 0.003, mat)
                pc = strap_end + Vector((0, 0, 0.03)) + fs * 0.056
                obox(g, pc + Vector((0, 0, -0.02)), fs, ax, (0, 0, 1), 0.004, 0.022, 0.06, mat)
    if caps[0] or caps[1]:
        ends = []
        if caps[0]:
            ends.append((pts[0], (pts[0] - pts[1]).normalized()))
        if caps[1]:
            ends.append((pts[-1], (pts[-1] - pts[-2]).normalized()))
        for c, f in ends:
            side = Vector((0, 0, 1)).cross(f).normalized()
            poly = [c + side * (r * math.cos(math.pi + math.pi * k / nseg)) +
                    Vector((0, 0, r * math.sin(math.pi + math.pi * k / nseg))) for k in range(nseg + 1)]
            prism(g, [p + f * 0.004 for p in poly], f, 0.006, mat)
    return g


def downpipe(g, pts, r=0.045, mat=IRON, bend_r=0.12, clamps=(), clamp_to=None, shoe=True, nseg=12):
    """Round downpipe through the polyline `pts` (top first), every corner a smooth bend (the swan neck), collars at
    the joints, strap clamps at the heights in `clamps` fixed toward `clamp_to` (unit Vector to the wall/post), and a
    shoe at the bottom. Panel f."""
    path = fillet_path(pts, bend_r, steps=7)
    tube(g, path, r, mat, nseg=nseg, cap0=True, cap1=not shoe)
    # socket collars at the straight joints (every 1.5 m on the long run) and at each bend end
    straight = []
    for a, b in zip(pts, pts[1:]):
        a, b = Vector(a), Vector(b)
        L = (b - a).length
        d = (b - a).normalized()
        for k in range(1, int(L / 1.5) + 1):
            c = a + d * (L * k / (int(L / 1.5) + 1))
            straight.append((c, d))
    for c, d in straight:
        tube(g, [c - d * 0.03, c + d * 0.03], r + 0.006, mat, nseg=nseg, cap0=True, cap1=True)
    if clamp_to is not None:
        cw = Vector(clamp_to).normalized()
        for z in clamps:
            for a, b in zip(pts, pts[1:]):
                a, b = Vector(a), Vector(b)
                if min(a.z, b.z) <= z <= max(a.z, b.z) and abs(a.z - b.z) > 0.2:
                    f = (z - a.z) / (b.z - a.z)
                    c = a.lerp(b, f)
                    tube(g, [c - Vector((0, 0, 0.025)), c + Vector((0, 0, 0.025))], r + 0.010, mat, nseg=nseg,
                         cap0=True, cap1=True)
                    side = cw.cross(Vector((0, 0, 1))).normalized()
                    for sd in (-1, 1):
                        pe = c + side * (sd * (r + 0.02)) + cw * (r * 0.3)
                        obox(g, pe + cw * 0.03, cw, side, (0, 0, 1), 0.04, 0.004, 0.022, mat)
                    obox(g, c + cw * (r + 0.07), side, cw, (0, 0, 1), r + 0.05, 0.004, 0.03, mat)
                    break
    if shoe:
        end = Vector(pts[-1])
        d = (Vector(pts[-1]) - Vector(pts[-2])).normalized()
        out = Vector((0, 0, 0)) - Vector(clamp_to or (1, 0, 0)).normalized()
        out.z = 0
        out = out.normalized()
        shoe_pts = fillet_path([end - d * 0.001, end + Vector((0, 0, -0.10)), end + Vector((0, 0, -0.10)) + out * 0.16],
                               0.07, steps=6)
        tube(g, shoe_pts, r, mat, nseg=nseg, cap1=False)
    return g


# ------------------------------------------------------------------------------------------------ collision
def slab(poly, th=0.2):
    """Hull points of a roof collision slab: the planar polygon (the collision surface) and a copy th below."""
    pts = [Vector(q) for q in poly]
    return pts + [q - Vector((0, 0, th)) for q in pts]


# ------------------------------------------------------------------------------------------------ warps
def sag_warp(slopes, depth, corners=(), upturn=0.0, reach=3.0):
    """A displacement function for warp(): a gentle sag (depth, m) mid-way up each slope (sin profile over its run from
    eave to top) and an upsweep `upturn` (m) near every eave corner (radial falloff over `reach` m in plan).
    slopes: list of (RoofSlope, run_top, poly_plan) - the sag applies to points whose plan position is inside
    poly_plan (first match)."""
    def inside(p, poly):
        c = False
        n = len(poly)
        for i in range(n):
            (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
            if (y0 > p.y) != (y1 > p.y):
                xc = x0 + (p.y - y0) * (x1 - x0) / (y1 - y0)
                if p.x < xc:
                    c = not c
        return c

    def fn(v):
        dz = 0.0
        for rs, run_top, poly in slopes:
            if inside(v, poly):
                t = max(0.0, min(1.0, rs.run_of(v) / run_top))
                dz -= depth * math.sin(math.pi * t)
                break
        for (cx, cy) in corners:
            d = math.hypot(v.x - cx, v.y - cy)
            if d < reach:
                dz += upturn * (1.0 - d / reach) ** 2
        return Vector((0, 0, dz))
    return fn


# ------------------------------------------------------------------------------------------------ compound roofs
def _courses(s_len, target=0.28):
    """Split a slope run of s_len (m, along the slope) into equal tile courses close to `target` m long. Returns
    (course length, number of courses)."""
    n = max(1, int(round(s_len / target)))
    return s_len / n, n


def _lift(poly, z_of):
    return [(p[0], p[1], z_of(p)) for p in poly]


def _line_at_y(p0, p1, y):
    t = (y - p0[1]) / (p1[1] - p0[1])
    return (p0[0] + (p1[0] - p0[0]) * t, y)


def irimoya(x0, x1, y0, y1, z_eave, pitch=PITCH_DEG, gable_in=2.3, verge_ov=0.45, overhang=0.9, upturn=0.12,
            reach=3.2, gable_style="boards", gable_frame=False, ridge_layers=(0.52, 0.48, 0.44, 0.40), ridge_roll=0.12,
            ridge_h=0.065, oni=(0.80, 0.95, 0.45), sumi_oni=(0.44, 0.50, 0.22), hip_roll=0.10,
            hip_layers=(0.34, 0.31, 0.28), verge_layers=(0.32, 0.29, 0.26), verge_roll=0.10,
            verge_oni=(0.40, 0.46, 0.20), rafter_spacing=0.30, rafter_caps=True, blocking=True, front_recess=None):
    """Hip-and-gable roof (irimoya) over the plan rectangle x0..x1, y0..y1 (eave lines, collision height z_eave on all
    four sides), ridge along X at the middle. gable_in: plan distance from the side eave to the gable face; verge_ov:
    the main slopes' overhang beyond the gable face; overhang: eave overhang beyond the walls (the soffit band that
    gets sarking, closely spaced capped rafters and, with blocking=True, the frieze board over every wall line).
    front_recess = {"x_a", "x_b", "rise"[, "top_in"]} (the hall sheet): the front slope's eave is cut back over x_a..x_b
    along the same plane, so the centre eave sits `rise` higher; two descending diagonal ridges run from the ridge ends
    down past the centre eave corners to the outer eave, and the collision slabs are split along them.
    World coordinates. Returns dict with Geos 'slope_front', 'slope_back' (the plain slope turned 180 deg), 'end_w',
    'end_e' (the west end turned 180 deg), 'ridge', 'hulls' (same keys: lists of point lists) and 'numbers'."""
    tn = math.tan(math.radians(pitch))
    cs = math.cos(math.radians(pitch))
    sn = math.sin(math.radians(pitch))
    bo = base_off(pitch)
    W, D = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    run_r = D / 2
    ZR = z_eave + run_r * tn
    xg0, xg1 = x0 + gable_in, x1 - gable_in
    xv0, xv1 = xg0 - verge_ov, xg1 + verge_ov
    yA, yB = y0 + gable_in, y1 - gable_in
    z_foot = z_eave + gable_in * tn
    s_foot = gable_in / cs
    C, n_foot = _courses(s_foot)
    s_ridge = (run_r - 0.20) / cs
    s_wall = overhang / cs + 0.12
    n_raf = max(1, int(round(W / rafter_spacing)))
    u_raf = [W * (i + 0.5) / n_raf for i in range(n_raf)]
    nf = Vector((0, -sn, cs))

    def zf(p):
        return z_eave + (p[1] - y0) * tn

    # ---------------- the main slope (front frame; the back is it turned 180 deg)
    rs = RoofSlope((x0, y0), (x1, y0), z_eave, pitch)
    gA = Geo()
    tile_field(gA, rs.sl, 0.0, W, 0.0, s_foot, C, TILE, eave=True, phase=0.0, roll_margin=0.0)
    sarking(gA, rs, 0.0, W, -0.04, s_wall, nstrips=3)
    for u in u_raf:
        s_end = min(s_wall, min(u, W - u) / cs + 0.05)
        if s_end > 0.05:
            rafters(gA, rs, 0, 0, -0.07, s_end, u_list=[u], caps=rafter_caps)
    eave_trim(gA, rs, 0.0, W)
    if blocking:
        eave_blocking(gA, rs, overhang, W - overhang, overhang)
    gA = plan_clip(gA, (x0, y0), (xg0, yA), (cx, y0 + 0.3))
    gA = plan_clip(gA, (x1, y0), (xg1, yA), (cx, y0 + 0.3))
    gB = Geo()
    tile_field(gB, rs.sl, xv0 - x0, xv1 - x0, s_foot, s_ridge, C, TILE, eave=False, phase=0.0, roll_margin=0.16)
    for ue, inw in ((xv0 - x0, 1), (xv1 - x0, -1)):
        verge(gB, rs, ue, s_foot + 0.10, s_ridge + 0.10, inward=inw, widths=verge_layers, h=0.05, roll_r=verge_roll,
              disc=None, board=False, banded=True)
        if verge_oni:   # the descending (verge) ridge ends at the gable foot in a small block-and-disc end
            vW, vH, vT = verge_oni
            ridge_end(gB, rs.at(ue + inw * 0.14, s_foot + vT / 2, 0.02), (0, -1, 0), vW, vH, vT, TILE, wings=False)
    # soffit of the verge overhang (between the verge and the gable face) and three purlin ends through the gable
    for xa_, xb_ in ((xv0, xg0), (xg1, xv1)):
        sarking(gB, rs, xa_ - x0, xb_ - x0, s_foot, s_ridge + 0.1, nstrips=4)
        for k in (0.25, 0.55, 0.85):
            s = s_foot + (s_ridge - s_foot) * k
            ua, ub = (xa_ - x0 - 0.02, xb_ - x0 + 0.25) if xa_ < cx else (xa_ - x0 - 0.25, xb_ - x0 + 0.02)
            a = rs.at(ua, s, -0.004 - 0.025 - 0.09)
            b = rs.at(ub, s, -0.004 - 0.025 - 0.09)
            obox(gB, (a + b) / 2, rs.sl.U, rs.sl.S, rs.sl.N, (b - a).length / 2, 0.08, 0.09, TIMBER)
            if rafter_caps:
                end = a if xa_ < cx else b
                rafter_cap(gB, end, -rs.sl.U if xa_ < cx else rs.sl.U, rs.sl.N, 0.16, 0.18)
    # bargeboards (hafu) along the verges, ending where they would meet the end slope's tiles
    hb = 0.30
    z_end_at_verge = z_eave + (xv0 - x0) * tn
    y_bfoot = y0 + (z_end_at_verge + 0.06 + hb + bo + 0.03 - z_eave) / tn
    for xv, fx in ((xv0, -1), (xv1, 1)):
        za = z_eave + (y_bfoot - y0) * tn - bo - 0.03
        zb = ZR - bo - 0.03
        a = Vector((xv - fx * 0.03, y_bfoot, za))
        b = Vector((xv - fx * 0.03, cy, zb))
        ax = (b - a).normalized()
        w = ax.cross(Vector((1, 0, 0))).normalized()
        if w.z < 0:
            w = -w
        obox(gB, (a + b) / 2 - w * (hb / 2), ax, (1, 0, 0), w, (b - a).length / 2, 0.03, hb / 2, TIMBER)
        obox(gB, a - w * (hb / 2) - ax * 0.03, ax, (1, 0, 0), w, 0.05, 0.04, hb / 2 + 0.01, TIMBER)
    plain = Geo()
    plain.extend(gA)
    plain.extend(gB)
    polys_plain = [[(x0, y0), (x1, y0), (xg1, yA), (xg0, yA)], [(xv0, yA), (xv1, yA), (xv1, cy), (xv0, cy)]]
    hf_plain = [slab(_lift(p, zf)) for p in polys_plain]
    # ---------------- the front slope: plain, or with the raised centre eave (front_recess)
    rec_numbers = None
    if front_recess:
        xa, xb, rise = front_recess["x_a"], front_recess["x_b"], front_recess["rise"]
        d_in = front_recess.get("top_in", 0.35)
        sb = rise / tn
        yR = y0 + sb
        yT = cy - 0.25
        L0, L1 = (xv0 + d_in, yT), (xa, yR)
        R0, R1 = (xv1 - d_in, yT), (xb, yR)
        Le, Re = _line_at_y(L0, L1, y0), _line_at_y(R0, R1, y0)
        kL, kR, kC = (x0, y0 + 0.2), (x1, y0 + 0.2), (cx, yR + 0.3)
        outer = plan_clip(plain, L0, L1, kL)
        outer.extend(plan_clip(plain, R0, R1, kR))
        rc = RoofSlope((x0, yR), (x1, yR), z_eave + rise, pitch)
        s_ridge_c = (run_r - sb - 0.20) / cs
        s_wall_c = (overhang - sb) / cs + 0.12
        ua, ub = xv0 - x0, xv1 - x0
        gC = Geo()
        tile_field(gC, rc.sl, ua, ub, 0.0, s_ridge_c, C, TILE, eave=True, phase=0.0, roll_margin=0.0)
        sarking(gC, rc, ua, ub, -0.04, s_wall_c, nstrips=2)
        rafters(gC, rc, 0, 0, -0.07, s_wall_c, u_list=[u for u in u_raf if ua - 0.5 < u < ub + 0.5], caps=rafter_caps)
        eave_trim(gC, rc, ua, ub)
        if blocking:
            eave_blocking(gC, rc, ua, ub, overhang - sb)
        gC = plan_clip(gC, L0, L1, kC)
        gC = plan_clip(gC, R0, R1, kC)
        front = outer
        front.extend(gC)
        # the descending diagonal ridges (laid on the one plane: up = its normal), a stepped disc end at each foot,
        # and a short board under each cut edge between the outer eave and the centre eave
        for k, (Pe, P0, P1) in enumerate(((Le, L0, L1), (Re, R0, R1))):
            a = Vector((Pe[0], Pe[1], zf(Pe)))
            b = Vector((P0[0], P0[1], zf(P0)))
            hip(front, a, b, nf, nf, widths=hip_layers, h=0.055, roll_r=hip_roll, sumi_oni=sumi_oni, seed=51 + k)
            pa, pb = Vector((Pe[0], Pe[1], 0.0)), Vector((P1[0], P1[1], 0.0))
            dd = (pb - pa).normalized()
            nrm = Vector((-dd.y, dd.x, 0.0))
            if nrm.dot(Vector((cx, 0, 0)) - Vector((Pe[0], 0, 0))) < 0:
                nrm = -nrm
            za_, zb_ = zf(Pe) - bo - 0.16, zf(P1) - bo - 0.16
            beam(front, Vector((pa.x, pa.y, za_)) + nrm * 0.03 - dd * 0.02, Vector((pb.x, pb.y, zb_)) + nrm * 0.03,
                 0.05, 0.30, TIMBER)
        hf = []
        for poly in polys_plain:
            parts = [clip_poly2(poly, L0, L1, kL), clip_poly2(poly, R0, R1, kR),
                     clip_poly2(clip_poly2(clip_poly2(poly, L0, L1, kC), R0, R1, kC), (x0, yR), (x1, yR), kC)]
            hf += [slab(_lift(p, zf)) for p in parts if len(p) >= 3 and poly2_area(p) > 0.02]
        for (Pe, P0) in ((Le, L0), (Re, R0)):
            dd = Vector((P0[0] - Pe[0], P0[1] - Pe[1], 0.0)).normalized()
            nrm = Vector((-dd.y, dd.x, 0.0))
            pts = []
            for P in (Pe, P0):
                for sd in (-0.17, 0.17):
                    q = (P[0] + nrm.x * sd, P[1] + nrm.y * sd)
                    pts += [(q[0], q[1], zf(q) - 0.05), (q[0], q[1], zf(q) + 0.25)]
            hf.append(pts)
        rec_numbers = {"x_a": xa, "x_b": xb, "rise": rise, "setback_m": round(sb, 4), "centre_eave_y": round(yR, 4),
                       "centre_eave_z": round(z_eave + rise, 4),
                       "diagonal_left": [[round(v, 4) for v in Le], [round(v, 4) for v in L0]],
                       "diagonal_right": [[round(v, 4) for v in Re], [round(v, 4) for v in R0]],
                       "diagonal_hull_height_m": 0.25}
    else:
        front = Geo()
        front.extend(plain)
        hf = hf_plain
    # ---------------- west end (hip slope + hips + gable)
    re_ = RoofSlope((x0, y1), (x0, y0), z_eave, pitch)
    gE = Geo()
    tile_field(gE, re_.sl, 0.0, D, 0.0, s_foot - 0.05, C, TILE, eave=True, phase=0.0, roll_margin=0.0)
    sarking(gE, re_, 0.0, D, -0.04, s_wall, nstrips=3)
    n = max(1, int(round(D / rafter_spacing)))
    for i in range(n):
        u = D * (i + 0.5) / n
        s_end = min(s_wall, min(u, D - u) / cs + 0.05)
        if s_end > 0.05:
            rafters(gE, re_, 0, 0, -0.07, s_end, u_list=[u], caps=rafter_caps)
    eave_trim(gE, re_, 0.0, D)
    if blocking:
        eave_blocking(gE, re_, overhang, D - overhang, overhang)
    gE = plan_clip(gE, (x0, y0), (xg0, yA), (x0 + 0.3, cy))
    gE = plan_clip(gE, (x0, y1), (xg0, yB), (x0 + 0.3, cy))
    # flashing along the gable foot (the end slope's top edge) and the gable face
    ua, ub = re_.u_of((x0, yB)), re_.u_of((x0, yA))
    pa = re_.at(ua + 0.25, s_foot - 0.16, 0.03)
    pb = re_.at(ub - 0.25, s_foot - 0.16, 0.03)
    top_f = wall_flashing(gE, pa, pb, re_.sl.N, widths=(0.30, 0.26), h=0.045)
    ridge_cap(gE, pa + re_.sl.N * (top_f + 0.04), pb + re_.sl.N * (top_f + 0.04), re_.sl.N, 0.07, seg=0.40)
    z_base = z_foot + 0.07
    under = bo + 0.004 + 0.025 + 0.02
    ya_g = y0 + (z_base + under - z_eave) / tn
    yb_g = y1 - (z_base + under - z_eave) / tn
    gable_face(gE, xg0, ya_g, yb_g, z_base, cy, ZR - under, facing=-1, style=gable_style, tie_drop=0.17,
               frame=gable_frame)
    # hips along the hip lines (collision points); the end slope and the main slopes share them
    nb = Vector((0, sn, cs))
    ne = Vector((-sn, 0, cs))
    for (py, ny, yt) in ((y0, nf, yA), (y1, nb, yB)):
        a = Vector((x0, py, z_eave))
        b = Vector((xg0, yt, z_foot))
        b = b + (b - a).normalized() * 0.10
        hip(gE, a, b, ny, ne, widths=hip_layers, h=0.055, roll_r=hip_roll, sumi_oni=sumi_oni, seed=int(py * 10) % 97)
    # ---------------- ridge + ridge ends
    gR = Geo()
    rtop, z0r = ridge(gR, (xv0 + 0.20, cy), (xv1 - 0.20, cy), ZR, widths=ridge_layers, h=ridge_h, roll_r=ridge_roll)
    oW, oH, oT = oni
    for xe, f in ((xv0 + 0.02, -1), (xv1 - 0.02, 1)):
        ridge_end(gR, (xe - f * oT / 2, cy, z0r - 0.10), (f, 0, 0), oW, oH, oT, TILE)
    oni_top = z0r - 0.10 + oH
    # ---------------- corner upsweep (visual only; the collision stays planar)
    corners = [(x0, y0), (x1, y0), (x0, y1), (x1, y1)]
    fn = sag_warp([], 0.0, corners=corners, upturn=upturn, reach=reach)
    for g_ in (plain, front, gE):
        warp(g_, fn)
    rot = Matrix.Translation((cx, cy, 0)) @ Matrix.Rotation(math.pi, 4, "Z") @ Matrix.Translation((-cx, -cy, 0))
    out = {"slope_front": front, "slope_back": plain.transformed(rot), "end_w": gE, "end_e": gE.transformed(rot),
           "ridge": gR, "pivot": (cx, cy, 0.0)}
    he = [slab([(x0, y1, z_eave), (x0, y0, z_eave), (xg0, yA, z_foot), (xg0, yB, z_foot)]),
          [(xg0 + dx, y, z) for dx in (-0.06, 0.06) for (y, z) in ((ya_g, z_base), (yb_g, z_base), (cy, ZR - under))]]
    hr = [[(x, y, z) for x in (xv0 + 0.20, xv1 - 0.20) for y in (cy - 0.28, cy + 0.28) for z in (ZR - 0.13, rtop)]]
    for xe, f in ((xv0 + 0.02, -1), (xv1 - 0.02, 1)):
        hr.append([(x, y, z) for x in (xe, xe - f * oT) for y in (cy - oW / 2, cy + oW / 2)
                   for z in (z0r - 0.10, oni_top)])

    def rot_pts(pts):
        return [tuple(rot @ Vector(p)) for p in pts]
    out["hulls"] = {"slope_front": hf, "slope_back": [rot_pts(h) for h in hf_plain], "end_w": he,
                    "end_e": [rot_pts(h) for h in he], "ridge": hr}
    out["numbers"] = {"pitch_deg": pitch, "eave": z_eave, "planes_meet": round(ZR, 4), "ridge_cap_top": round(rtop, 4),
                      "ridge_end_top": round(oni_top, 4), "ridge_end_above_cap_m": round(oni_top - rtop, 3),
                      "ridge_x": [xv0 + 0.20, xv1 - 0.20],
                      "ridge_to_eave_length": round((xv1 - xv0 - 0.40) / W, 3), "gable_face_x": [xg0, xg1],
                      "verge_x": [xv0, xv1], "gable_foot_z": round(z_foot, 4), "gable_base_y": [yA, yB],
                      "courses_per_gable_run": n_foot, "course_m": round(C, 4), "corner_upturn_m": upturn,
                      "gable_style": gable_style, "gable_frame": gable_frame, "rafter_spacing_m": rafter_spacing,
                      "rafter_caps": rafter_caps, "eave_blocking": blocking, "front_recess": rec_numbers}
    return out


def lean_to_wrap(x0, x1, y_front, y_back, xw0, xw1, y_wall, z_eave, pitch=PITCH_DEG, upturn=0.05, reach=2.4,
                 rafter_spacing=0.30, end_board=True, wall_gap=0.10, rafter_caps=True):
    """A lean-to wrapping the front (eave y_front, x0..x1) and both sides (eaves x0 / x1, back to y_back) of a body
    whose walls stand at y = y_wall (front) and x = xw0 / xw1 (sides); hips at the front corners, verges at the back
    ends. Returns dict 'front', 'side_w', 'side_e' Geos (world), 'gutter' polylines (rim centre; add with gutter()),
    'hulls', 'numbers'."""
    tn = math.tan(math.radians(pitch))
    cs = math.cos(math.radians(pitch))
    bo = base_off(pitch)
    run = y_wall - y_front
    s_top = (run - wall_gap) / cs
    s_wall = run / cs
    C, ncourse = _courses(s_top)
    z_wall = z_eave + run * tn
    rs = RoofSlope((x0, y_front), (x1, y_front), z_eave, pitch)
    W = x1 - x0
    gF = Geo()
    tile_field(gF, rs.sl, 0.0, W, 0.0, s_top, C, TILE, eave=True, roll_margin=0.0)
    sarking(gF, rs, 0.0, W, -0.04, s_wall, nstrips=8)
    n = max(1, int(round(W / rafter_spacing)))
    for i in range(n):
        u = W * (i + 0.5) / n
        s_end = min(s_wall, min(u, W - u) / cs + 0.05)
        if s_end > 0.05:
            rafters(gF, rs, 0, 0, -0.07, s_end, u_list=[u], caps=rafter_caps)
    eave_trim(gF, rs, 0.0, W)
    gF = plan_clip(gF, (x0, y_front), (xw0, y_wall), ((x0 + x1) / 2, y_front + 0.3))
    gF = plan_clip(gF, (x1, y_front), (xw1, y_wall), ((x0 + x1) / 2, y_front + 0.3))
    pa = rs.at(xw0 - x0 + 0.30, s_top - 0.04, 0.02)
    pb = rs.at(xw1 - x0 - 0.30, s_top - 0.04, 0.02)
    wall_flashing(gF, pa, pb, rs.sl.N)
    nf = rs.sl.N.copy()
    sides = {}
    for key, (xe, xw, sgn) in (("side_w", (x0, xw0, 1)), ("side_e", (x1, xw1, -1))):
        if sgn > 0:
            rsd = RoofSlope((x0, y_back), (x0, y_front), z_eave, pitch)
        else:
            rsd = RoofSlope((x1, y_front), (x1, y_back), z_eave, pitch)
        L = abs(y_back - y_front)
        g = Geo()
        tile_field(g, rsd.sl, 0.0, L, 0.0, s_top, C, TILE, eave=True, roll_margin=0.0)
        sarking(g, rsd, 0.0, L, -0.04, s_wall, nstrips=8)
        n = max(1, int(round(L / rafter_spacing)))
        for i in range(n):
            u = L * (i + 0.5) / n
            d_hip = (L - u) if sgn > 0 else u
            s_end = min(s_wall, d_hip / cs + 0.05)
            if s_end > 0.05 and 0.12 < u < L - 0.12:
                rafters(g, rsd, 0, 0, -0.07, s_end, u_list=[u], caps=rafter_caps)
        eave_trim(g, rsd, 0.0, L)
        g = plan_clip(g, (xe, y_front), (xw, y_wall), (xe + sgn * 0.3, (y_front + y_back) / 2))
        u_edge = 0.0 if sgn > 0 else L
        verge(g, rsd, u_edge, 0.0, s_top, inward=1 if sgn > 0 else -1, disc=0.075, board=True, board_h=0.22)
        if end_board:
            zlo = z_eave - bo - 0.20
            pts = [Vector((xe + sgn * 0.03, y_back - 0.02, zlo)), Vector((xw, y_back - 0.02, zlo)),
                   Vector((xw, y_back - 0.02, z_wall - bo - 0.17))]
            prism(g, pts, (0, 1, 0), 0.03, TIMBER, frame=(Vector((0, 0, 1)), Vector((1, 0, 0)), Vector((0, 1, 0))))
        ua, ub = rsd.u_of((xe, y_back - 0.3)), rsd.u_of((xe, y_wall + 0.3))
        wall_flashing(g, rsd.at(min(ua, ub), s_top - 0.04, 0.02), rsd.at(max(ua, ub), s_top - 0.04, 0.02), rsd.sl.N,
                      seed=13 + sgn)
        sides[key] = (g, rsd)
    for key, (xe, xw, sgn) in (("side_w", (x0, xw0, 1)), ("side_e", (x1, xw1, -1))):
        a = Vector((xe, y_front, z_eave))
        b = Vector((xw, y_wall, z_wall))
        nsd = sides[key][1].sl.N
        hip(gF, a, b - (b - a).normalized() * 0.15, nf, nsd, widths=(0.32, 0.29, 0.26), h=0.055, roll_r=0.10,
            end_disc=0.12, sumi_oni=(0.40, 0.46, 0.20), seed=17 + sgn)
    corners = [(x0, y_front), (x1, y_front)]
    fn = sag_warp([], 0.0, corners=corners, upturn=upturn, reach=reach)
    warp(gF, fn)
    for key in sides:
        warp(sides[key][0], fn)
    zg = z_eave - bo - 0.055
    off = 0.09
    gpts = {"w": [(x0 - off, y_back - 0.05, zg), (x0 - off, y_front - off, zg)],
            "f": [(x0 - off, y_front - off, zg), (x1 + off, y_front - off, zg)],
            "e": [(x1 + off, y_front - off, zg), (x1 + off, y_back - 0.05, zg)]}
    hulls = {"front": [slab([(x0, y_front, z_eave), (x1, y_front, z_eave), (xw1, y_wall, z_wall),
                             (xw0, y_wall, z_wall)])],
             "side_w": [slab([(x0, y_front, z_eave), (xw0, y_wall, z_wall), (xw0, y_back, z_wall),
                              (x0, y_back, z_eave)])],
             "side_e": [slab([(x1, y_back, z_eave), (xw1, y_back, z_wall), (xw1, y_wall, z_wall),
                              (x1, y_front, z_eave)])]}
    return {"front": gF, "side_w": sides["side_w"][0], "side_e": sides["side_e"][0], "gutter": gpts,
            "gutter_z": zg, "gutter_off": off, "hulls": hulls,
            "numbers": {"pitch_deg": pitch, "eave": z_eave, "at_wall": round(z_wall, 4), "course_m": round(C, 4),
                        "courses": ncourse, "corner_upturn_m": upturn, "rafter_spacing_m": rafter_spacing,
                        "rafter_caps": rafter_caps}}


def chidori_hafu(x_face, y_c, half_w, main_eave_x, main_eave_z, x_wall, main_pitch=PITCH_DEG, pitch=38.0,
                 verge_ov=0.35, gable_style="plaster", oni=(0.40, 0.50, 0.20), ridge_layers=(0.34, 0.31, 0.28),
                 ridge_roll=0.09, mirror_about_x=None):
    """Chidori-hafu (the hall sheet's side view): a small front-facing gable standing on a lean-to slope, its ridge
    running back to the wall. Built facing -X on a lean-to that rises toward +X (collision plane
    z = main_eave_z + (x - main_eave_x) tan(main_pitch)); mirror_about_x = X mirrors it for the other side.
    x_face: the gable face (tympanum) plane; y_c: its centre line; half_w: half its width at the tympanum base; pitch:
    its own slopes (walkable when under 44.8 deg); verge_ov: the rakes' overhang in front of the face; x_wall: the
    wall face the ridge runs into (its tiles are cut there). Parts: tile fields on both slopes cut along the valleys
    (where they meet the lean-to), banded verge ridges with end discs, bargeboards with a hanging board, the tympanum
    (plaster in a timber frame, or boards), a ridge with a small stepped block-and-disc end, iron valley flashings.
    Returns dict 'geo', 'hulls' (one convex hull: the walkable roof volume), 'numbers'."""
    tm = math.tan(math.radians(main_pitch))
    tc = math.tan(math.radians(pitch))
    cc = math.cos(math.radians(pitch))
    snm, csm = math.sin(math.radians(main_pitch)), math.cos(math.radians(main_pitch))

    def zm(x):
        return main_eave_z + (x - main_eave_x) * tm
    xv = x_face - verge_ov
    zr = zm(x_face) + half_w * tc
    bo = base_off(pitch)
    y_e = y_c - (zr - zm(xv)) / tc
    y_w = y_c - (zr - zm(x_wall)) / tc
    rs = RoofSlope((xv, y_e), (x_wall + 0.05, y_e), zm(xv), pitch)
    L = x_wall + 0.05 - xv
    s_top = ((y_c - y_e) - 0.10) / cc
    C, _ = _courses(s_top)
    half = Geo()
    tile_field(half, rs.sl, 0.0, L, 0.0, s_top, C, TILE, eave=False, roll_margin=0.16)
    sarking(half, rs, 0.0, (x_face - xv) + 0.06, 0.0, s_top + 0.05, nstrips=4)
    # the verge starts where its stack clears the lean-to (the valley foot would otherwise cut it into steps)
    s_v0 = min(0.45 / cc, 0.4 * s_top)
    verge(half, rs, 0.0, s_v0, s_top + 0.02, inward=1, widths=(0.28, 0.25), h=0.045, roll_r=0.085, disc=0.09,
          board=False, banded=True)
    M = Matrix(((1, 0, 0, 0), (0, -1, 0, 2 * y_c), (0, 0, 1, 0), (0, 0, 0, 1)))
    g = Geo()
    g.extend(half)
    g.extend(half.transformed(M, mirror=True))
    bargeboards(g, xv + 0.03, y_e, 2 * y_c - y_e, zm(xv) - bo - 0.03, y_c, zr - bo - 0.03, facing=-1, h=0.24, t=0.06)
    under = bo + 0.004 + 0.025 + 0.02
    z_base = zm(x_face) + 0.02
    z_ap = zr - under
    hwb = (z_ap - z_base) / tc
    gable_face(g, x_face, y_c - hwb, y_c + hwb, z_base, y_c, z_ap, facing=-1, style=gable_style, tie_h=0.16,
               post_w=0.14, tie_drop=0.08, frame=(gable_style == "plaster"))
    nm = Vector((-snm, 0.0, csm))
    g = plane_clip(g, (main_eave_x, y_c, main_eave_z - 0.06 / csm), nm)
    g = plan_clip(g, (x_wall, 0.0), (x_wall, 1.0), (x_wall - 1.0, y_c))
    # ridge back to the wall + the small ridge end over the rakes
    rtop, z0r = ridge(g, (xv + 0.04, y_c), (x_wall, y_c), zr, widths=ridge_layers, h=0.05, roll_r=ridge_roll, bed_w=0.36)
    oW, oH, oT = oni
    ridge_end(g, (xv + oT / 2 - 0.02, y_c, z0r - 0.08), (-1, 0, 0), oW, oH, oT, TILE, wings=False)
    # iron valley flashings on the lean-to where the two slopes meet it
    for sgn in (-1, 1):
        pa = Vector((xv, y_c - sgn * (y_c - y_e), zm(xv) + 0.012))
        pb = Vector((x_wall, y_c - sgn * (y_c - y_w), zm(x_wall) + 0.012))
        d = (pb - pa).normalized()
        v = nm.cross(d).normalized()
        obox(g, (pa + pb) / 2, d, v, nm, (pb - pa).length / 2, 0.09, 0.004, IRON)
    hull = [(xv, y_e, zm(xv) - 0.05), (xv, 2 * y_c - y_e, zm(xv) - 0.05), (xv, y_c, zr),
            (x_wall, y_w, zm(x_wall) - 0.05), (x_wall, 2 * y_c - y_w, zm(x_wall) - 0.05), (x_wall, y_c, zr)]
    hulls = [hull]
    if mirror_about_x is not None:
        g = K.mirror_x(g, mirror_about_x)
        hulls = [[(2 * mirror_about_x - p[0], p[1], p[2]) for p in h] for h in hulls]
    nums = {"face_x": x_face, "verge_x": xv, "centre_y": y_c, "pitch_deg": pitch, "plane_at_ridge": round(zr, 4),
            "ridge_cap_top": round(rtop, 4), "ridge_end_top": round(z0r - 0.08 + oH, 4),
            "width_at_verge_foot": round(2 * (y_c - y_e), 3), "width_at_wall": round(2 * (y_c - y_w), 3),
            "tympanum_base_z": round(z_base, 4), "tympanum_width": round(2 * hwb, 3)}
    if mirror_about_x is not None:
        nums.update({"face_x": round(2 * mirror_about_x - x_face, 4), "verge_x": round(2 * mirror_about_x - xv, 4)})
    return {"geo": g, "hulls": hulls, "numbers": nums}


def gable_roof(x0, x1, y0, y1, z_eave, pitch=PITCH_DEG, verge_ov=0.0, gable_style="plaster",
               ridge_layers=(0.40, 0.37, 0.34), ridge_roll=0.09, oni=(0.55, 0.62, 0.30), rafter_spacing=0.30,
               upturn=0.0, gable_face_on=True, rafter_caps=True, blocking_run=None, gable_frame=False):
    """Plain gable (kirizuma): eaves along X at y0 and y1 (collision z_eave), ridge along X at the middle, verges at
    x0 / x1 with bargeboards, verge rolls ending in plain discs, stepped block-and-disc ridge ends and (optionally) a
    gable face set verge_ov inside each verge. blocking_run: plan distance from each eave line to its wall line (adds
    the frieze board over the walls, eave_blocking). Returns dict 'roof' Geo, 'hulls', 'numbers' (the storehouse /
    residence / corridor kits call this)."""
    tn = math.tan(math.radians(pitch))
    cs = math.cos(math.radians(pitch))
    bo = base_off(pitch)
    cy = (y0 + y1) / 2
    run_r = (y1 - y0) / 2
    ZR = z_eave + run_r * tn
    s_ridge = (run_r - 0.18) / cs
    C, nc = _courses(s_ridge)
    W = x1 - x0
    g = Geo()
    rot = Matrix.Translation(((x0 + x1) / 2, cy, 0)) @ Matrix.Rotation(math.pi, 4, "Z") @ \
        Matrix.Translation((-(x0 + x1) / 2, -cy, 0))
    half = Geo()
    rs = RoofSlope((x0, y0), (x1, y0), z_eave, pitch)
    tile_field(half, rs.sl, 0.0, W, 0.0, s_ridge, C, TILE, eave=True, roll_margin=0.16)
    sarking(half, rs, 0.0, W, -0.04, s_ridge + 0.1, nstrips=10)
    rafters(half, rs, 0.10, W - 0.10, -0.07, s_ridge, spacing=rafter_spacing, caps=rafter_caps)
    eave_trim(half, rs, 0.0, W)
    if blocking_run:
        eave_blocking(half, rs, 0.12, W - 0.12, blocking_run)
    for ue, inw in ((0.0, 1), (W, -1)):
        verge(half, rs, ue, 0.0, s_ridge + 0.10, inward=inw, disc=0.085, board=True)
    g.extend(half)
    g.extend(half.transformed(rot))
    rtop, z0r = ridge(g, (x0 + 0.20, cy), (x1 - 0.20, cy), ZR, widths=ridge_layers, roll_r=ridge_roll, bed_w=0.44)
    oW, oH, oT = oni
    for xe, f in ((x0 + 0.02, -1), (x1 - 0.02, 1)):
        ridge_end(g, (xe - f * oT / 2, cy, z0r - 0.08), (f, 0, 0), oW, oH, oT, TILE)
    if gable_face_on:
        under = bo + 0.004 + 0.025 + 0.10 + 0.02
        for xg, f in ((x0 + verge_ov + 0.08, -1), (x1 - verge_ov - 0.08, 1)):
            z_b = z_eave - under + 0.40 * tn
            gable_face(g, xg, y0 + 0.40, y1 - 0.40, z_b, cy, ZR - under, facing=f, style=gable_style,
                       frame=gable_frame)
    if upturn:
        warp(g, sag_warp([], 0.0, corners=[(x0, y0), (x1, y0), (x0, y1), (x1, y1)], upturn=upturn, reach=2.0))
    hulls = [slab([(x0, y0, z_eave), (x1, y0, z_eave), (x1, cy, ZR), (x0, cy, ZR)]),
             slab([(x1, y1, z_eave), (x0, y1, z_eave), (x0, cy, ZR), (x1, cy, ZR)]),
             [(x, y, z) for x in (x0, x1) for y in (cy - 0.24, cy + 0.24) for z in (ZR - 0.13, rtop)]]
    return {"roof": g, "hulls": hulls, "numbers": {"planes_meet": round(ZR, 4), "ridge_cap_top": round(rtop, 4),
                                                   "course_m": round(C, 4), "courses": nc}}
