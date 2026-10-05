"""Detail part BUTT PLATE: the steel butt plate on the stock's end (its side outline also cuts the stock) and the
two cross-slotted screws in counterbores.

Owns the objects: butt_plate, butt_screws. Authority close-ups: c7 BUTT PLATE (END) and the 3/4 view; scale and
position from the spec and the side views (box_M, side_profile_M, TOP width 36.9).
Interfaces: butt_plate_outline() and _rear_face_x() are read by rifle_parts2.buttstock (the stock's end cut);
butt_plate_section() is the plate's end-view (YZ) outline, offered to the stock for its end section (detail round 1
spec proposal, WorkFiles/guns/rifle/review/detail/butt_plate/spec_proposal.json).

Detail round 1 (2026-10-05), built from c7's own shape (butt_plate_dev.py traces it):
  * end view: c7 draws a long lozenge (blunt rounded heel tip, sides bowed out to the widest row at 41 % of the
    height, a longer gentler taper to the toe), not the round-0 rounded rectangle. Its half-width profile was traced
    (sub-pixel row widths, perspective-corrected) and fitted by a two-sided power curve, RMS 0.017 of the width;
    mapped onto the spec box (width 36.9 from TOP at the widest row, height from the side profile). c7 is not to scale
    (it draws the plate at ~0.65x the TOP width), so only the shape comes from it.
  * side outline: the traced side profile, with the pixel staircase removed (rear face Gaussian-smoothed with the
    heel and toe pinned; band front edge a least-squares line, the band 11-12 mm as traced) and the toe "tail" the
    trace drew to X 28.9 dropped (a contact shadow under the stock's toe in the zoomed side panels, not steel).
  * rim: the rear face rolls into the skirt with a 1.5 mm round (c7's dark band round the face); the edge against the
    wood is a crisp 0.3 chamfer.
  * screws: c7 draws each head as a dome inside a dark gap ring with a bright counterbore lip, the slots as an "X" with
    about 60 deg between them (narrow angle on the plate's long axis), the lower head turned ~7 deg further; heads
    7.0 in an 8.5 counterbore (spec), head edge 0.6 below the face, dome to 0.15 below it, slots 0.8 wide x 0.9 deep.

Detail round 2 (2026-10-05), from the round-1 blind judge's tells (round 1 = A, picked confidently):
  * end-view outline: round 1 rendered ~0.05 (of the width) wider than c7 on every row away from the widest one (a
    rounded rectangle with parallel sides). The section profile is re-fitted to the c7 trace through the rendered
    plate: f_new = f_old x (c7 row width / our rendered row width), smoothed, then fitted by the two-sided power curve
    with a bow term (1 - k s^2) that bows the long sides; widest row at 40 % (TOP width 36.9 stays there). Unit-box
    IoU 0.959 -> 0.981, rows within 0.03 (butt_plate_dev.py profile).
  * border: c7's distinct border round the whole face (judge: "a dark raised lip or gasket-like border"): the face
    lies 0.4 below a raised lip 2.2 wide in all (pocket_cutter), whose outer edge is a 1.0 45 deg band into the skirt
    with both edges broken 0.3 (the bright lines c7 shows at the face edge). The face itself stays on the side
    profile (side view and TOP unchanged); the lip's 0.4 fades out over 2 mm at the heel top and toe bottom, where the
    stock's heel corner sits 0.02 off the outline.
  * face: slightly convex across the width (spec "face slightly convex"; judge: ours "flat and slab-like"): a shallow
    tent (0.6 at the outline's edge) whose faces take the normals of the matching smooth parabola (no star shading
    round the countersinks either: surface_normals_from).
  * screws: c7 draws them flush in countersunk holes with cut (engraved) slots (judge: our domed heads with an
    "embossed" X read proud): spec heads 7.0 nearly flush (apex 0.1 below the face, dome 0.25), a 0.15 dark gap, a 45
    deg countersink to the spec ring 8.5 (its edge broken 0.3: the bright ring); slots 0.55 wide with a 0.06 edge
    break (round 1's 0.15 lit both slot edges like a ridge). Heads of 6.0 (c7 at its height scale) were tried and
    read tiny against our wider plate: spec kept.
  * the toe lip's concave corner against the band front edge has a 0.8 fillet (the stock's mitred cut came within
    0.004 of the sharp corner; now >= 0.016 everywhere); coplanar faces are merged before triangulating (2100 -> 1992).
  NOT fixable here: c7 draws the plate ~0.65x the TOP width with wood beside it (the TOP panel shows a flush steel
  cap, 36.5 at X 5.7): proposal BP-5. The stock's faceted end section is the stock's (BP-1).

Detail round 2b (2026-10-05, re-run of round 2 on top of the integration round; butt_plate_ends.py, butt_plate_gaps.py):
  * ends at the WIDTH scale: with c7 at aspect 0.22 and ours 0.34, the unit-box fit left each end's arch too flat for
    our width and a pointed tip. c7's half-width vs distance from the tip, both in plate widths, is the target for the
    end regions (END_HEEL / END_TOE), fitted by the same concave model (END_FIT): end IoU in that frame 0.932 / 0.936
    -> 0.967 / 0.974 (heel / toe); unit-box IoU 0.981 -> 0.952 (the price: the unit box assumes c7's aspect).
  * the section is sampled densely and Douglas-Peucker'd (SEC_TOL 0.05): the caps are smooth arcs, not the cosine
    rows' chamfer facets.
  * heel top up 0.75 (HEEL_RAISE), flush with the stock's top line: no strip of stock end grain above the plate.
  * screws: a straight counterbore to the spec ring 8.5 round the 7.0 head (c7's dark gap ring; the 45 deg countersink
    rendered as a bright cone), 3.5 deep, flat heads (the 0.08 dome still shaded as a star), 0.5 slots at c7's angles
    (re-measured; round 2 had the toe screw mirrored).
  * rim stays one 1.6 rolled band (c7's dark band measures 4.2 % of the plate width = 1.55 at 36.9; 2.4 was tried and
    read no darker: its tone is the finish's, BP-4).
"""
from __future__ import annotations

import math

import numpy as np

from rifle_common import SPEC
from gunlib import geo2d as G
from gunlib import lod as LOD
from gunlib import mesh as MS
from gunlib.parts import PartDef
from rifle_parts import GAP
from rifle_parts2 import xprism

HALF_W = 18.45                      # spec width 36.9 (TOP), the plate's widest row
HEEL_RAISE = 0.75                   # round 2b: the heel top rises 0.75 (to Z 0.51-0.61, the stock's top line there is
                                    # 0.43-0.47): no strip of the stock's end grain above the plate (c7 shows none; the
                                    # round-1 judge's "odd light rectangle sticking up at the top")
SEC_TOP, SEC_BOT = -0.14 + HEEL_RAISE, -109.91   # the profile rows span the side outline (heel top, toe); tips stand TIP_OUT
TIP_OUT = 0.4                       # beyond it, so the outline trims a short blunt flat and no faces nearly coincide
# c7 half-width profile (v = 0 heel tip .. 1 toe tip), round 2 (butt_plate_dev.py profile: round-1 fit corrected by
# the c7 / rendered row-width ratio, then fitted):
#   f(v) = (1 - s^a)^b (1 - k s^2), s = (VC - v) / VC above the widest row, (v - VC) / (1 - VC) below it
C7_FIT = {"vc": 0.4042, "a_top": 12.0, "b_top": 0.6106, "k_top": 0.4001,
          "a_bot": 10.4141, "b_bot": 0.3641, "k_bot": 0.2337}
CROWN = 0.25                        # rear face convex across the width: 0.25 forward at |y| = HALF_W + 2 (see crown_dx)
                                    # (integration r2b: 0.6 -> 0.25; the r2b judge read the face as domed / pillowed
                                    # where c7's face is flat with straight edges)
TILT = 5.23                         # rear face tilt, toe forward (spec dims)
RIM_W = 3.0                         # DETAIL FIX (user checklist 8): ONE THICK rounded bevel band (1.6 -> 3.0, 4 seg). Was: the face's edge: one rounded band into the skirt (integration round: 3 segments, was a
                                    # 1.0 45 deg band + a raised lip; judge: 'one thick dark rounded bevel band', no inner border)
RIM_SEG = 3                         # (round 2b measured c7's dark band at 4.2 % of the plate width: 1.55 at 36.9)
EDGE_R = 0.3                        # its two edges broken 0.3
POCKET_INSET, POCKET_D = 2.2, 0.0   # integration round: NO raised lip (round 2 had 0.4; the judge read it as an extra
#                                     stepped inner border the reference does not have). Round 2: a lip 0.4 proud of the face whose outer
#                                     edge is the band above (border 2.2 in all; c7 ~1.9-2.0 at the width scale). The
#                                     face stays on the side profile; the lip stands behind it (side view unchanged)
Y_EXT = HALF_W + 2.0                # the side-outline body spans |y| <= Y_EXT (the section prism trims it)
SCREW_Z = (-10.0, -87.5)
FLAT_HALF = 5.4                     # half height of the flat face strip round each screw (bore 4.25 + lip 0.4 + margin)
HEAD_R = 3.5                        # spec head 7.0
HOLE_R = 2.1                        # DETAIL FIX (user checklist 8): PLAIN COUNTERSINKS: a 4.2 shank hole under a 90 deg (45 deg
                                    # half-angle) countersink to the spec ring 8.5, the flat slotted head flush in it.
_HOLE_R_R2B = 4.25                  # round 2b: a straight counterbore to the spec ring 8.5, 0.75 radial gap round the
                                    # 7.0 head: the dark gap ring c7 draws (head / ring 0.85 on c7). Integration round had a
                                    # 0.05 gap + 45 deg countersink, which rendered as a bright cone round the head
CSK_R = 4.25                        # countersink outer radius at the face (== HOLE_R: none)
BORE_R = CSK_R                      # (the rim predicate keeps clear of the countersinks)
RING_DEPTH = 0.08                   # head top below the face (detail fix: flush; r2b 0.2)
BORE_DEPTH = 3.5                    # hole depth (round 2b: 2.2 -> 3.5, the gap ring reads darker)
DOME = 0.0                          # head dome height (round 2b: flat; integration round 0.08 still shaded as a star)
SLOT_W, SLOT_D = 0.7, 0.9           # detail fix: one real slot per head (r2b: two 0.5 slots, an X)
_SLOT_W_R2B = 0.5           # round 2b: 0.75 -> 0.5 (c7's slots are thin dark lines)
SLOT_ANGLES = ((-31.0, 42.0), (-32.0, 46.0))   # deg from the plate's long axis (heel up), per screw, as c7 draws them
                                               # (round 2b: re-measured on c7 at 4x; round 2 had them mirrored at the toe)


def c7_profile(v, c=None):
    v = np.asarray(v, float)
    c = C7_FIT if c is None else c
    top = v < c["vc"]
    s = np.clip(np.where(top, (c["vc"] - v) / c["vc"], (v - c["vc"]) / (1.0 - c["vc"])), 0.0, 1.0)
    a = np.where(top, c["a_top"], c["a_bot"])
    b = np.where(top, c["b_top"], c["b_bot"])
    k = np.where(top, c["k_top"], c["k_bot"])
    return np.clip(1.0 - s ** a, 0.0, 1.0) ** b * (1.0 - k * s * s)


# Round 2b: the ENDS matched at the WIDTH scale (butt_plate_ends.py). c7 draws the plate at aspect 0.22, the spec at
# ~0.34 (BP-5), so the unit-box fit of rounds 1-2 left each end's arch 1/1.5 as tall relative to the width as c7 draws
# it, with a pointed tip (heel read "flat-topped, chamfered corners", toe "a blunt faceted point"). The targets are
# c7's own half-width w(d) (d = distance from the tip, both in plate widths; smoothed c7 trace rows): END_HEEL /
# END_TOE for d <= 0.9, the unit-box profile from d >= 1.15. They are fitted by the same smooth concave model as C7_FIT
# (END_FIT, rms 0.020 heel / 0.008 toe of the width): a first try blended the tables into C7_FIT directly and put two
# inflections in the side (a wavy plate edge in the 3/4 view). Widest row 0.40, TOP width 36.9 unchanged.
END_D = (0.0, 0.01, 0.02, 0.035, 0.05, 0.075, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1)
END_HEEL = (0.03, 0.08, 0.11, 0.15, 0.183, 0.222, 0.252, 0.29, 0.312, 0.328, 0.345, 0.375, 0.403, 0.425, 0.439, 0.448,
            0.455, 0.461, 0.467)
END_TOE = (0.06, 0.113, 0.145, 0.178, 0.205, 0.24, 0.265, 0.3, 0.323, 0.343, 0.362, 0.388, 0.402, 0.414, 0.428,
           0.438, 0.443, 0.448, 0.455)
END_FIT = dict(C7_FIT, a_top=28.7891, b_top=0.7498, k_top=0.5581, a_bot=15.4729, b_bot=0.4234, k_bot=0.3816)


def plate_profile(v):
    """Half-width (fraction of HALF_W) at v (0 heel tip .. 1 toe tip): c7_profile's model with END_FIT."""
    return c7_profile(v, END_FIT)


def butt_plate_section():
    """End-view (YZ) outline of the plate: c7's shape on the spec box (plate_profile). Denser rows near the tips."""
    # round 2b: dense rows, then Douglas-Peucker (SEC_TOL) on one side: vertices go where the outline turns (the
    # ends' caps), so the caps read as smooth arcs, not chamfered corners (round 1-2: 14 cosine rows per side)
    v = np.linspace(0.0, 1.0, 1201)[1:-1]
    f = plate_profile(v)
    z = SEC_TOP - v * (SEC_TOP - SEC_BOT)
    chain = np.vstack([[0.0, SEC_TOP + TIP_OUT], np.c_[-HALF_W * f, z], [0.0, SEC_BOT - TIP_OUT]])   # -Y = gun right
    chain = _dp_open(chain, SEC_TOL)
    left = chain[1:-1][::-1] * np.array([-1.0, 1.0])
    return G.ccw(G.dedupe(np.vstack([chain, left])))


SEC_TOL = 0.05                       # mm, section chordal tolerance


def _dp_open(P, tol):
    """Douglas-Peucker on an open polyline (both ends kept)."""
    keep = np.zeros(len(P), bool)
    keep[[0, -1]] = True
    stack = [(0, len(P) - 1)]
    while stack:
        a, b = stack.pop()
        if b - a < 2:
            continue
        A, B = P[a], P[b]
        ab = B - A
        nn = float(np.hypot(*ab))
        seg = P[a + 1:b]
        d = np.abs(ab[0] * (seg[:, 1] - A[1]) - ab[1] * (seg[:, 0] - A[0])) / max(nn, 1e-12)
        k = int(np.argmax(d))
        if d[k] > tol:
            keep[a + 1 + k] = True
            stack += [(a, a + 1 + k), (a + 1 + k, b)]
    return P[keep]


def _smooth_chain(Pc, sig_mm, step=0.4, pin_mm=4.0):
    """Open polyline -> resampled every `step` mm, Gaussian-smoothed along its length (sigma in mm), both ends pinned
    with a linear blend over pin_mm (they are the outline's corners: heel top, toe bottom, the tail's corners)."""
    Pc = np.asarray(Pc, float)
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Pc, axis=0), axis=1))]
    t = np.linspace(0, d[-1], max(int(d[-1] / LOD.step(step)) + 1, 3))
    R = np.c_[np.interp(t, d, Pc[:, 0]), np.interp(t, d, Pc[:, 1])]
    sg = sig_mm / step
    r = int(3 * sg) + 1
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sg) ** 2)
    k /= k.sum()
    Rp = np.vstack([np.repeat(R[:1], r, 0), R, np.repeat(R[-1:], r, 0)])
    S = np.c_[np.convolve(Rp[:, 0], k, "same"), np.convolve(Rp[:, 1], k, "same")][r:-r]
    n = max(int(pin_mm / step), 2)
    for end in (0, -1):
        idx = np.arange(len(S))[:n] if end == 0 else np.arange(len(S))[-n:][::-1]
        for j, i in enumerate(idx):
            w = max(0.0, 1.0 - j / (n - 1))
            S[i] = w * R[i] + (1.0 - w) * S[i]
    return S


REAR_SIGMA, FRONT_SIGMA = 2.0, 5.0     # mm; screened against the side trace (2D IoU 0.986 -> 0.981, round 0 0.986)
OUTLINE_TOL = 0.08                     # mm, Douglas-Peucker on the cleaned side outline (vertex budget: plate + stock end)
SEC_ROWS = 14                          # (unused since round 2b: the section is sampled densely + Douglas-Peucker, SEC_TOL)
REAR_SHIFT_X = -0.21                   # integration round: the smoothed trace's heel sits at X 0.16 and the rounded rim
                                       # band pulls the rearmost point to 0.21; the whole plate (and the stock end cut,
                                       # which follows this outline) moves back so the heel is X 0.0 (L4 overall length)


def butt_plate_outline():
    """Side (XZ) outline: the traced profile with the pixel staircase smoothed out (rear face sigma 2 mm, band front
    edge sigma 5 mm, corners pinned); the short toe lip the side trace and the 3/4 view both show is kept. CCW, M.
    LOD1 uses the LOD0 outline (the stock's end cut follows this outline; the coarser LOD1 chain left a 0.007 mm
    butt gap at the toe lip, under the 0.01 row)."""
    with LOD.hold(1):
        return _butt_plate_outline()


def _butt_plate_outline():
    raw = np.asarray(SPEC.profile("butt_plate"), float)
    i_toe = int(np.argmin(raw[:, 1]))                 # toe bottom (14.25, -109.91)
    i_tip = int(np.argmax(raw[:, 0]))                 # toe lip front (28.87, -107.21)
    i_lip = i_tip + 2                                 # lip top meets the band front edge (21.54, -106.46)
    rear = _smooth_chain(raw[:i_toe + 1], REAR_SIGMA)     # heel top (9.27, -0.14) -> rear face -> toe bottom
    # a flat strip of the face round each screw (the counterbore + lip lie in one plane: no shading streaks from
    # long triangles spanning facets of the curved face; the chord leaves the smoothed curve by < 0.1 mm)
    for zs in SCREW_Z:
        band = (rear[:, 1] < zs + FLAT_HALF) & (rear[:, 1] > zs - FLAT_HALF)
        idx = np.nonzero(band)[0]
        if len(idx) >= 2:
            a, b = idx[0], idx[-1]
            t = (rear[a:b + 1, 1] - rear[a, 1]) / (rear[b, 1] - rear[a, 1])
            rear[a:b + 1, 0] = rear[a, 0] + t * (rear[b, 0] - rear[a, 0])
    front = _smooth_chain(raw[i_lip:], FRONT_SIGMA)       # band front edge, toe lip -> heel top (10.54, -0.24)
    P = np.vstack([rear, raw[i_toe + 1:i_lip], front])
    P = G.dp_simplify(G.dedupe(P, 1e-3), OUTLINE_TOL)
    # round 2: the concave corner where the toe lip meets the band's front edge gets a 0.8 fillet; sharp, the stock's
    # mitred cut (outline grown GAP) came within 0.004 of it (butt-gap rule 0.01-0.05)
    radii = np.zeros(len(P))
    radii[int(np.argmin(np.linalg.norm(P - LIP_CORNER, axis=1)))] = LIP_CORNER_R
    P = G.fillet(P, 0.0, seg=3, radii=radii)
    P[:, 0] += REAR_SHIFT_X
    # round 2b: the heel top up HEEL_RAISE (flush with the stock's top line), fading out 1-4 mm below it
    t = np.clip((P[:, 1] + 4.0) / 3.0, 0.0, 1.0)
    P[:, 1] += HEEL_RAISE * t * t * (3.0 - 2.0 * t)
    return G.ccw(P)


LIP_CORNER, LIP_CORNER_R = np.array([21.54, -106.46]), 0.8


def _rear_face_x(P, z):
    Q = np.vstack([P, P[:1]])
    xs = []
    for a, b in zip(Q[:-1], Q[1:]):
        if (a[1] - z) * (b[1] - z) <= 0 and a[1] != b[1]:
            t = (z - a[1]) / (b[1] - a[1])
            xs.append(a[0] + t * (b[0] - a[0]))
    return min(xs)


def _face_normal(P, z):
    """Outward rear-face normal at height z (from the side outline's local slope)."""
    dz = 1.5
    x0, x1 = _rear_face_x(P, z + dz), _rear_face_x(P, z - dz)
    t = np.array([x0 - x1, 0.0, 2 * dz])              # tangent (up the face)
    n = np.cross(t, [0.0, 1.0, 0.0])                  # points -X (out of the rear face)
    n /= np.linalg.norm(n)
    return n if n[0] < 0 else -n


def _is_rim(mid, d, n1, n2, dih):
    """The rear face (and heel / toe roll) meeting the skirt: one face from the side-outline prism (n_y ~ 0, not the
    front edge), the other from the section prism (n_x ~ 0)."""
    if dih < 50.0:
        return 0.0
    if any(abs(mid[2] - zs) < BORE_R + 1.5 and abs(mid[1]) < BORE_R + 1.5 for zs in SCREW_Z):
        return 0.0                                    # the counterbores (their lip comes from the 0.3 pass)
    for a, b in ((n1, n2), (n2, n1)):
        if abs(a[1]) < 0.15 and a[0] < 0.3 and abs(b[0]) < 0.05:      # (the crown tilts the face by <= 0.07)
            return 1.0
    return 0.0


def _rear_chain_mask(P):
    """True on the outline's rear chain: CCW from the heel top (topmost point of the rear half) to the toe bottom."""
    n = len(P)
    i_top = int(np.argmax(np.where(P[:, 0] < 11.0, P[:, 1], -1e9)))
    i_bot = int(np.argmin(P[:, 1]))
    m = np.zeros(n, bool)
    i = i_top
    while True:
        m[i] = True
        if i == i_bot:
            break
        i = (i + 1) % n
    return m


def crown_dx(y, smooth=False):
    """Forward shift of the rear face at y: the geometry is a shallow tent (CROWN at |y| = Y_EXT, a ridge on the centre
    line, 1.7 deg); its shading comes from the smooth parabola through the same end points (smooth=True), whose
    normals the face takes (build_butt_plate). Tent vs parabola: <= CROWN / 4 = 0.15 apart."""
    t = np.abs(np.asarray(y, float)) / Y_EXT
    return CROWN * (t * t if smooth else t)


SHIFT_FADE = 2.0                       # mm of height over which the lip's shift fades out at the heel top / toe bottom


def crowned_body(P, shift=0.0, smooth=False):
    """The side outline extruded across Y as a loft whose rear chain moves forward by crown_dx(y) + shift: the rear face
    is convex across the width; the band's front edge (against the stock) stays straight. Geometry: 3 stations (tent);
    smooth=True: 17 stations on the parabola (the normals source). The shift fades to 0 over SHIFT_FADE at the chain's
    ends (heel top, toe bottom), so the plate never leaves the outline the stock is cut to (0.02 gap)."""
    rear = _rear_chain_mask(P)
    zr = P[rear, 1]
    w = np.clip((zr.max() - P[:, 1]) / SHIFT_FADE, 0, 1) * np.clip((P[:, 1] - zr.min()) / SHIFT_FADE, 0, 1)
    rings = []
    for y in np.linspace(-Y_EXT, Y_EXT, (17 if LOD.LEVEL < 2 else LOD.count(16, 2) + 1) if smooth else 3):   # LOD1 keeps the crown (stock butt gap)
        dx = float(crown_dx(y, smooth)) + shift * w
        x = P[:, 0] + np.where(rear, dx, 0.0)
        rings.append(np.c_[x, np.full(len(P), y), P[:, 1]])
    return MS.loft(rings)


def butt_plate() -> PartDef:
    P = butt_plate_outline()
    body = crowned_body(P, shift=-POCKET_D)               # the lip's level; the pocket brings the face back to P
    p = PartDef("butt_plate", [body], cls="S-bend",
                recipe=[(RIM_W, RIM_SEG, "W", _is_rim), (EDGE_R, 1, "W", _rear_break), (EDGE_R, 1, "W", _plain_break)])
    p.section_intersect_pre = [xprism(butt_plate_section(), -5.0, 35.0)]
    cut, screws = [], []
    for z in SCREW_Z:
        nrm = _face_normal(P, z)
        c = np.array([_rear_face_x(P, z), 0.0, z])       # on the face (the pocket floor)
        # hole + 45 deg countersink (continued outward past the face)
        prof = [(-BORE_DEPTH, 0.0), (-BORE_DEPTH, HOLE_R)]
        if CSK_R > HOLE_R:
            prof += [(-(CSK_R - HOLE_R), HOLE_R), (2.5, CSK_R + 2.5), (2.5, 0.0)]
        else:                                         # round 2b: a straight counterbore (c7's dark gap ring)
            prof += [(2.5, HOLE_R), (2.5, 0.0)]
        if LOD.LEVEL < 2:                             # LOD2: no screws (dropped), no counterbores; painted only
            cut.append(MS.revolve(prof, c, nrm, 24))
        screws.append((c, nrm))
    p.cutters = cut                                   # before the bevels
    p.post_cutters = [pocket_cutter(P)] if POCKET_D > 0 else []   # the face pocket after the bevels (crisp step)
    p.post_recipe = []                                # (a 0.08 break on the step cost ~700 sliver triangles)
    p.screws = screws
    return p


_P_CACHE = []


def _rear_zone(mid, depth=2.5):
    """Edge midpoint within `depth` of the rear face (in X, at its height): the rim, the countersinks and the pocket,
    never the band's front edge against the stock (whose concave lip corner a bevel would push into the 0.02 gap)."""
    if not _P_CACHE:
        _P_CACHE.append(butt_plate_outline())
    P = _P_CACHE[0]
    z = float(np.clip(mid[2], P[:, 1].min() + 0.01, P[:, 1].max() - 0.01))
    return mid[0] < _rear_face_x(P, z) + depth


def _in_hole(mid):
    """Edge inside a screw hole (shank bore / countersink foot): never bevelled (a fillet there meets the screw)."""
    return any(math.hypot(mid[1], mid[2] - zs) < CSK_R - 0.6 for zs in SCREW_Z)


def _plain_break(mid, d, n1, n2, dih):
    """The plain 0.3 break on every edge of 52 deg or more, except inside the screw holes (detail fix: the countersunk
    screws' shanks sit 0.02 off the bore, so the bore floor's concave fillet met them)."""
    return 1.0 if dih >= 52.0 and not _in_hole(mid) else 0.0


def _rear_break(mid, d, n1, n2, dih):
    """0.3 break on the 40-52 deg edges of the rear zone: the rim band's two edges and the countersinks' (the bright
    lines c7 shows at the face edge and round each screw). The plain 52 deg pass takes the rest."""
    if _in_hole(mid):
        return 0.0          # detail fix: not the countersink's concave foot inside the hole (its fillet met the screw head)
    return 1.0 if 40.0 <= dih < 52.0 and _rear_zone(mid) else 0.0




def _section_halfwidth(Q, z):
    """Half-width of a CCW YZ polygon Q at height z (max |y| of the row's crossings, Y-symmetric outline)."""
    R = np.vstack([Q, Q[:1]])
    ys = []
    for a, b in zip(R[:-1], R[1:]):
        if (a[1] - z) * (b[1] - z) <= 0 and a[1] != b[1]:
            t = (z - a[1]) / (b[1] - a[1])
            ys.append(a[0] + t * (b[0] - a[0]))
    return (max(ys) - min(ys)) / 2.0 if len(ys) >= 2 else 0.0


def pocket_cutter(P):
    """The face pocket: inside the plate's end outline inset POCKET_INSET, from behind the lip down to the face (the side
    profile + the tent crown). A loft of per-row rings (row = Z level; ring = the floor across the row at y = -hw, 0, hw,
    then back along a line behind the lip); rows at every rear-face vertex (the floor stays on the face's facets) and at
    the inset outline's rows (0.6 apart within 12 mm of the tips, 2.0 elsewhere)."""
    inner = G.offset(G.ccw(butt_plate_section()), -POCKET_INSET)
    rear = P[_rear_chain_mask(P)]
    zt, zb = inner[:, 1].max(), inner[:, 1].min()
    keep_z = set(np.round(rear[:, 1], 4))                     # the floor stays parallel to the face's facets
    zs = np.r_[inner[:, 1], rear[:, 1]]
    zs = np.unique(np.round(zs[(zs < zt - 0.15) & (zs > zb + 0.15)], 4))[::-1]          # top -> bottom
    thin = [zs[0]]
    for z in zs[1:]:
        gap = 0.6 if (z > zt - 12.0 or z < zb + 12.0) else 2.0
        if z in keep_z or thin[-1] - z > gap:
            thin.append(z)
    zs = np.array(thin)
    rings = []
    for z in zs:
        hw = _section_halfwidth(inner, z)
        if hw < 0.25:
            continue
        xr = _rear_face_x(P, z)
        y = np.array([-hw, 0.0, hw])
        top = np.c_[xr + crown_dx(y), y, np.full(3, z)]
        bot = np.c_[np.full(3, xr - POCKET_D - 2.0), y[::-1], np.full(3, z)]
        rings.append(np.vstack([top, bot]))
    m = MS.loft(rings)
    V = m.verts()
    vol = 0.0
    for f in m.F:
        for k in range(1, len(f) - 1):
            vol += np.dot(V[f[0]], np.cross(V[f[k]], V[f[k + 1]])) / 6.0
    if vol < 0:
        m = MS.loft([r[::-1] for r in rings])
    return m


def build_butt_plate(coll, offset):
    """butt_plate through gunlib.parts.build_part's steps (the post pass weighted: build_part's post_recipe is angle-only),
    then the faces on the crowned face and on the lip take the smooth crowned loft's normals (the countersinks and the
    pocket re-triangulate the face into long thin triangles that weighted normals shade as a star round each screw)."""
    import json
    import time
    import bpy
    from gunlib import bl
    t0 = time.time()
    p = butt_plate()
    base = MS.Mesh()
    for sld in p.solids:
        base.extend(sld)
    ob = base.to_object(p.name, coll, offset, smooth_deg=p.smooth_deg)
    sec = p.section_intersect_pre[0].to_object("_sec", coll, offset)
    bl.boolean(ob, sec, "INTERSECT")
    bpy.data.objects.remove(sec, do_unlink=True)
    bl.boolean_many(ob, p.cutters, "DIFFERENCE", offset=offset)
    bl.clean(ob)
    for step in p.recipe:
        if len(step) == 4:
            bl.bevel_weighted(ob, step[0], step[1], step[3], offset)
        else:
            bl.bevel(ob, step[0], step[1], step[2])
    bl.boolean_many(ob, p.post_cutters, "DIFFERENCE", offset=offset)
    bl.clean(ob)
    for step in p.post_recipe:
        bl.bevel_weighted(ob, step[0], step[1], step[3], offset)
    # the exact booleans leave the flat face strips split into many coplanar triangles (their count swings by
    # hundreds with tiny outline changes): merge coplanar faces (0.5 deg), finish() re-triangulates them minimally
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(0.5), use_dissolve_boundaries=False,
                             verts=bm.verts[:], edges=bm.edges[:])
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    bl.finish(ob)
    bl.weighted_normals(ob)
    rec = {"bone": p.bone, "class": p.cls, "slot": p.slot, "joint": p.joint, "spec_id": p.spec_id,
           "recipe": [[s_[0], s_[1], s_[2] if len(s_) == 3 else "weighted"] for s_ in p.recipe + p.post_recipe]}
    ob["gun_part"] = json.dumps(rec)
    p.report = bl.manifold_report(ob)
    p.report["seconds"] = round(time.time() - t0, 2)
    P = butt_plate_outline()
    src = [crowned_body(P, smooth=True).to_object("_bp_src", coll, offset),
           crowned_body(P, shift=-POCKET_D, smooth=True).to_object("_bp_src_lip", coll, offset)]
    n_on = bl.surface_normals_from(ob, src, tol_mm=0.2, max_angle_deg=12.0)
    for o in src:
        bpy.data.objects.remove(o, do_unlink=True)
    print("[AR01] butt_plate: %d faces take the crowned face's smooth normals" % n_on)
    return ob


def _slot_cutter(c, nrm, ang_deg, z_top):
    """Box slot through the head along direction ang_deg from the plate's long axis (heel up), cut from z_top - SLOT_D
    (along -nrm) outward."""
    up = np.array([0.0, 0.0, 1.0])
    e_up = up - (up @ nrm) * nrm
    e_up /= np.linalg.norm(e_up)
    e_side = np.cross(nrm, e_up)
    a = math.radians(ang_deg)
    u = math.cos(a) * e_up + math.sin(a) * e_side
    w = np.cross(nrm, u)
    L = HEAD_R + 0.8
    b0 = c - nrm * z_top - nrm * SLOT_D
    Q = np.array([b0 + u * L + w * SLOT_W / 2, b0 - u * L + w * SLOT_W / 2, b0 - u * L - w * SLOT_W / 2,
                  b0 + u * L - w * SLOT_W / 2])
    m = MS.Mesh()
    ids = m.add_verts(np.vstack([Q, Q + nrm * (SLOT_D + 2.0)]))
    m.face(ids[[3, 2, 1, 0]])
    m.face(ids[[4, 5, 6, 7]])
    for i in range(4):
        j = (i + 1) % 4
        m.face((ids[i], ids[j], ids[4 + j], ids[4 + i]))
    return m


def butt_screws() -> PartDef:
    """Two low-domed heads nearly flush in the countersunk holes, engraved X slots; bottoms 0.02 off the hole floors."""
    bp = butt_plate()
    sol, cut = [], []
    for (c, nrm), angs in zip(bp.screws, SLOT_ANGLES):
        c = np.asarray(c, float)
        floor_t = -BORE_DEPTH + GAP                   # along nrm from the face point
        edge_t = -RING_DEPTH
        apex_t = edge_t + DOME
        # DETAIL FIX: flat countersunk head: shank in the hole, a 45 deg cone GAP (normal) inside the countersink, the
        # flat top RING_DEPTH under the face (flush)
        D = CSK_R - HOLE_R
        g2 = GAP * math.sqrt(2.0)
        t_c = -D + g2 - GAP
        prof = [(floor_t, 0.0), (floor_t, HOLE_R - GAP), (t_c, HOLE_R - GAP),
                (edge_t, CSK_R + edge_t - g2), (edge_t, 0.0)]
        sol.append(MS.revolve(prof, c, nrm, 24))      # 24 = the hole cutter's: facets parallel, the 0.02 gap holds
        cut.append(_slot_cutter(c, nrm, angs[0], -apex_t))
    return PartDef("butt_screws", sol, cutters=cut, cls="M-chamfer", recipe=[(0.06, 1, 50.0)],   # 50: not the 45 deg concave shank-cone corner
                   spec_id="butt_plate", joint={"type": "butt", "parent": "butt_plate", "gap_mm": [0.01, 0.05]})


# ======================================================================================== module interface
OBJECTS = ('butt_plate', 'butt_screws')            # registry keys built here (rifle_parts.ORDER)
CLOSEUPS = ('c7', 'q34')          # sheet panels that are this part's shape authority (rifle_detail.py)


def build(spec, ctx):
    """Build this module's objects into ctx (gunlib.parts.BuildCtx). Returns {registry key: [objects]}; keys that
    ctx.only excludes come back empty. `spec` is the rifle GunSpec (the same object as rifle_common.SPEC)."""
    return {k: ctx.make(k, f) for k, f in (("butt_plate", build_butt_plate), ("butt_screws", butt_screws),)}
