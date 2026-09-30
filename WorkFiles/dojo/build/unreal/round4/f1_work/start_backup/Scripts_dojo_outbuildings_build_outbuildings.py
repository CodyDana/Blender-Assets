"""KIT 5 (round 4): the STOREHOUSE (NW, kura) and the RESIDENCE / wash house (NE), built on the shared roof system
(Scripts/dojo/roof/roof_kit.py 1.3.0), the shared kit mesh module (Scripts/dojo/roof/kit_mesh.py) and the shared dojo
material library (Scripts/dojo/materials, M_DJ_*; nothing forked, no texture of our own).

Spec (wins on size): WorkFiles/world/DOJO_ARENA_SPEC.md 4.5: roof X 0-7.6 / 36.4-44, Y 27.4-36, eave +3.25, ridge +5.25
along X. Gameplay numbers: the grey-box's proven ones (Scripts/dojo/build_dojo_greybox.py, layout.json):
  * both roofs extend over the perimeter wall (X -1 / 45): roof X -1..7.6 and 36.4..45, Y 27.4..36, one flat collision
    slab per slope from +3.25 at the eaves to +5.25 at Y 31.7 (the grey-box pitch atan(2.0 / 4.3) = 24.944 deg), so
  * route 2 (kit 1's step pier, flat top +3.25 at X -1..0 / 44..45, Y 26.4..27.4) walks straight onto the south eave
    (+3.25, a 0.0 m step), and
  * route 3 walks along the south slope (Y 31.0, +4.924) and off the east / west verge (X 7.6 / 36.4) onto the corridor
    roof (+3.7): the 1.22 m walk-off drop, then 0.51 m down onto the hall's lower roof.
Look: References/Dojo/dojo_outbuildings_ref.png (+ the small elevations on dojo_roof_details_ref.png, the overviews
dojo1_reference1/2.png); AI-generated modelling references (REFERENCE_LOG.md), measured, never sampled.

DEVIATION (flagged): the sheet puts each door + canopy on a GABLE end. Here the ridge must run along X (the spec, route 2
arrives on the south EAVE, route 3 leaves over the east verge), so the courtyard face is the south EAVE wall: the door,
its canopy (and the residence's lattice window + hood + meter box) are on that wall; the gable vents stay on the gables.

Pieces (SM_DKO_*; pivots / placements in layout_outbuildings.json; walls are piece-local modules, BR-reusable):
  Store_Bay_2m / Store_Bay_2p5 / Store_Bay_Door   kura eave-wall bays: 2-course hewn granite band (+1.0), cream
                            plaster, plaster wall plate + frieze between the rafters; the door bay adds the timber frame,
                            granite threshold + step (the steel leaves are their own piece)             building
  Store_Gable               gable end (full body depth incl. both corners): band with corner returns, plaster to the
                            roof underside, the framed gable vent                                       building
  Res_Bay_1p1 / Res_Bay_2p15 / Res_Bay_Door / Res_Bay_Window   residence eave-wall bays: granite foundation course,
                            sill beam, board-and-batten wainscot (+0.95), rail, cream plaster, timber wall plate +
                            frieze; door bay (jamb posts, lintel, step), window bay (posts, sill, head)  building
  Res_Gable                 gable end: corner posts, the same base, tie beam, plaster triangle, slatted vent, purlin
                            ends under the verge                                                        building
  Door_Steel / Door_Wood / Window_Lattice                                                               building
  Canopy_2p8 / Canopy_2p2 / Canopy_Window   small tiled lean-to canopies on brackets (store door, residence door,
                            residence window hood)                                                      building
  MeterBox                  the residence's electric meter box with its two conduits (its own asset)    thin
  Roof_Slope (x2 per building: south, and turned 180 deg for the north) / Roof_Ridge   the gable roof   roof
  Gutter (7.05 m, both eaves) / Downpipe (swan neck, clamps, shoe)                                      thin

Run: blender -b --factory-startup --python Scripts/dojo/outbuildings/build_outbuildings.py -- [--quick] [--no-export]
     [--no-context]
Out: Assets/Dojo/DojoOutbuildings.blend (Kit = our pieces + the showcase compound's pieces for the checks, Assembly =
     the showcase with our buildings in place of the grey-box storehouse / residence), Exports/DojoKit/Outbuildings/,
     WorkFiles/dojo/build/outbuildings/{layout_outbuildings.json, layout_outbuildings_checks.json, qa_report.json,
     export_report.json, outbuildings_report.json}
"""
import json
import math
import random
import sys
import time
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Scripts"))
sys.path.insert(0, str(ROOT / "Scripts" / "dojo"))
sys.path.insert(0, str(ROOT / "Scripts" / "dojo" / "roof"))
sys.path.insert(0, str(ROOT / "Scripts" / "dojo" / "materials"))
from pipeline.export_fbx import export_fbx  # noqa: E402
from pipeline.qa_check import qa_check  # noqa: E402
from pipeline.lock import assert_owner  # noqa: E402
from pipeline.helpers import decimate_lods, make_lod_group  # noqa: E402
import roof_kit as RK  # noqa: E402
import kit1_geo as K  # noqa: E402
from roof_kit import Geo  # noqa: E402
import dojo_materials as djm  # noqa: E402
import kit_mesh as KM  # noqa: E402
from kit_mesh import Piece, cbox, cobox, member, quad, geo_to_object, add_uv1, fix_lod  # noqa: E402,F401
from kit_mesh import TD, TDE, TA, TAE, GR, PL, IR, TL, GL  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
QUICK = "--quick" in ARGS
WORK = ROOT / "WorkFiles" / "dojo" / "build"
OW = WORK / "outbuildings"
EXPORT_DIR = ROOT / "Exports" / "DojoKit" / "Outbuildings"
BLEND = ROOT / "Assets" / "Dojo" / "DojoOutbuildings.blend"
SHOWCASE_BLEND = ROOT / "Assets" / "Dojo" / "DojoShowcase.blend"
SHOWCASE_LAYOUT = WORK / "showcase" / "layout_showcase.json"
KIT = "outbuildings"

# ------------------------------------------------------------------------------------------------ numbers (world)
EAVE, RIDGE_Z = 3.25, 5.25                 # spec 4.5 (grey-box OUT_EAVE / OUT_RIDGE)
Y0, Y1 = 27.4, 36.0                        # roof eave lines (spec footprint)
CY = (Y0 + Y1) / 2                          # 31.7
RUN = CY - Y0                               # 4.3
TN = (RIDGE_Z - EAVE) / RUN                 # the grey-box slope: tan = 2.0 / 4.3 (24.944 deg), planes meet at +5.25
PITCH = math.degrees(math.atan(TN))
CS = math.cos(math.radians(PITCH))
BO = RK.base_off(PITCH)                     # collision plane -> tile base plane (vertical)
SARK_UNDER = BO + 0.004 + 0.025             # collision plane -> sarking underside
RAFTER_UNDER = SARK_UNDER + 0.10            # collision plane -> rafter underside
ROOF_X = {"store": (-1.0, 7.6), "res": (36.4, 45.0)}      # over the perimeter wall (grey-box)
BODY_X = {"store": (0.0, 7.0), "res": (37.0, 44.0)}       # grey-box body
FACE_S, FACE_N = 27.94, 35.46               # plaster faces (south = the grey-box door face the modern props sit on;
                                            # north placed symmetric about the ridge: 0.54 m eaves both sides)
FACE_RUN = FACE_S - Y0                      # 0.54: eave line -> wall face
WT = 0.25                                   # wall thickness (gables span the full body depth, eave walls fit between)
DEPTH = FACE_N - FACE_S                     # 7.52


def zcol(run):
    """Collision (tile-top) height at plan distance `run` from an eave line toward the ridge."""
    return EAVE + run * TN


PLATE_TOP = zcol(FACE_RUN) - RAFTER_UNDER - 0.002    # wall plate top = the rafter underside at the face (+3.248)
PLATE_BOT = PLATE_TOP - 0.16
FRIEZE_TOP = zcol(FACE_RUN - 0.035) - SARK_UNDER - 0.003   # frieze board top: just under the sarking at its face
GUTTER_OFF = 0.09                           # gutter rim centre outside the eave line (roof_kit lean_to_wrap)
GUTTER_Z = EAVE - BO - 0.055                # gutter rim (roof_kit lean_to_wrap)
PIPE_OFF = 0.105                            # downpipe axis in front of the plaster face (clears the 4 cm band)
BAND_TOP = 1.0                              # store granite band (sheet: about 1 m, two courses)
BAND_PROUD = 0.04
# residence base (sheet: a low granite course, a sill beam, a board wainscot to about 0.9 m, a rail)
R_FOUND = 0.15
R_SILL = 0.27
R_RAIL = (0.95, 1.03)
# the kit-1 route-2 step pier stands under each south eave's outer end (X -1.44..0.44 / 43.56..45.44 visual): the
# south gutters stop clear of it and the corner downpipe stands beside it
PIER_CLEAR = {"store": 0.44, "res": 43.56}


def local_piece(name, cls, folder, note):
    p = Piece(name, cls, folder, note)
    p.local = True
    p.kit = KIT
    return p


# ------------------------------------------------------------------------------------------------ small helpers
def hewn(g, x0, x1, y0, y1, z0, z1, seed, exposed=("-d",), mat=GR, ch=0.018, pitch=0.009):
    """A squared, chamfered granite block with pitched exposed faces (kit 1's hewn_box)."""
    K.hewn_box(g, ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
               ((x1 - x0) / 2, (y1 - y0) / 2, (z1 - z0) / 2), ch, seed, mat, exposed=exposed, pitch=pitch,
               rough=0.002)


def split_run(x0, x1, target, rng, first=None):
    """Joint positions splitting x0..x1 into stones about `target` long (first stone length optional)."""
    cuts = [x0]
    x = x0 + (first if first else target * rng.uniform(0.85, 1.15))
    while x < x1 - 0.30:
        cuts.append(x)
        x += target * rng.uniform(0.80, 1.20)
    cuts.append(x1)
    return cuts


def granite_band(g, x0, x1, courses, seed, face_y=-BAND_PROUD, back_y=WT, end_lo=False, end_hi=False, gap=0.012,
                 target=0.72):
    """Dressed granite courses (the sheet's base band: squared blocks, staggered, pitched faces) from x0 to x1 along
    the wall face (local -y); courses = [(z0, z1), ...]. end_lo / end_hi: the end blocks wrap a corner (their end faces
    are exposed and reach BAND_PROUD past x0 / x1). A dark granite core behind the joints (never see-through)."""
    rng = random.Random(seed)
    for ci, (z0, z1) in enumerate(courses):
        xa = x0 - (BAND_PROUD if end_lo else 0.0)
        xb = x1 + (BAND_PROUD if end_hi else 0.0)
        first = target * (0.5 if ci % 2 else 1.0) * rng.uniform(0.9, 1.1)
        cuts = split_run(xa, xb, target, rng, first=first)
        for k, (a, b) in enumerate(zip(cuts, cuts[1:])):
            ex = ["-d"]
            if k == 0 and end_lo:
                ex.append("-a")
            if k == len(cuts) - 2 and end_hi:
                ex.append("+a")
            aa = a + (0.0 if k == 0 else gap / 2)
            bb = b - (0.0 if k == len(cuts) - 2 else gap / 2)
            hewn(g, aa, bb, face_y + rng.uniform(-0.005, 0.005), back_y, z0 + (gap / 2 if ci else 0.0),
                 z1 - gap / 2, seed * 31 + ci * 7 + k, exposed=tuple(ex), ch=0.024, pitch=0.013)
    # core behind the joints (inside the band, 1.2 cm behind the block faces)
    cbox(g, x0 + 0.01, x1 - 0.01, face_y + 0.03, back_y - 0.01, courses[0][0] + 0.005, courses[-1][1] - 0.005, GR,
         ch=0.002)


def boards(g, x0, x1, z0, z1, y_face, t=0.022, w=0.16, battens=True, mat=TD, seed=0):
    """Vertical board-and-batten wainscot: boards about w wide laid tight on a backing, a batten over every other
    joint (the residence sheet)."""
    n = max(1, int(round((x1 - x0) / w)))
    bw = (x1 - x0) / n
    for i in range(n):
        cbox(g, x0 + i * bw + 0.0015, x0 + (i + 1) * bw - 0.0015, y_face, y_face + t, z0, z1, mat, ch=0.003)
    cbox(g, x0, x1, y_face + t - 0.002, y_face + t + 0.02, z0, z1, mat, ch=0.002)
    if battens:
        for i in range(1, n):
            if i % 2 == 0:
                continue
            xj = x0 + i * bw
            cbox(g, xj - 0.022, xj + 0.022, y_face - 0.016, y_face + 0.002, z0 + 0.01, z1 - 0.01, mat, ch=0.004)


def frieze(g, x0, x1, mat):
    """The frieze (menado-ita) over the eave wall line, from the wall plate to just under the sarking: it closes the
    bays between the rafters, which pass through it (roof_kit.eave_blocking, placed with the wall module)."""
    cbox(g, x0, x1, -0.035, 0.012, PLATE_TOP - 0.03, FRIEZE_TOP, mat, ch=0.004)


def calm_boards(obj, seed=4242, jitter=0.035, set_name="TimberDark"):
    """The hall's calm board fix (build_hall.calm_boards): every wainscot board samples the same window of the timber
    tile with a small jitter, so a panel keeps one tone (no barcode). Boards = thin (<= 3.5 cm in local y) TimberDark
    parts 5-20 cm wide and at least 12 cm tall."""
    me = obj.data
    end_m = set_name.replace("Timber", "M_DJ_Timber") + "End"
    face_m = "M_DJ_" + set_name
    td = [i for i, m in enumerate(me.materials) if m.name in (face_m, end_m)]
    if not td:
        return 0
    end_i = next((i for i, m in enumerate(me.materials) if m.name == end_m), None)
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    fset = {f.index for f in bm.faces if f.material_index in td}
    seen, found = set(), []
    for fi in sorted(fset):
        if fi in seen:
            continue
        stack, part = [bm.faces[fi]], []
        seen.add(fi)
        while stack:
            c = stack.pop()
            part.append(c.index)
            for e in c.edges:
                for f2 in e.link_faces:
                    if f2.index in fset and f2.index not in seen:
                        seen.add(f2.index)
                        stack.append(f2)
        vs = [v.co for i in part for v in bm.faces[i].verts]
        dx = max(v.x for v in vs) - min(v.x for v in vs)
        dy = max(v.y for v in vs) - min(v.y for v in vs)
        dz = max(v.z for v in vs) - min(v.z for v in vs)
        if dy <= 0.035 and 0.05 <= dx <= 0.20 and dz >= 0.12:
            found.append(part)
    bm.free()
    rng = random.Random(seed)
    for part in found:
        djm.grain_uv(obj, set_name, end_set=set_name + "End", faces=part, end_material_index=end_i, seed=seed)
        uv = me.uv_layers["UVMap"].data
        du, dv = rng.uniform(-jitter, jitter), rng.uniform(-jitter, jitter)
        for fi in part:
            for li in me.polygons[fi].loop_indices:
                uv[li].uv = (uv[li].uv[0] + du, uv[li].uv[1] + dv)
    return len(found)


def clean_iron_uv(obj, period, u0=0.255, k=0.85):
    """The library's Iron texture carries rust patches in its outer columns (u < 0.25 and > 0.66 of the tile); the
    sheets show CLEAN grey steel on the store door and the meter box. Their Iron faces are mapped planar (dominant
    axis) into the rust-free column band u 0.25..0.66 of the tile (measured on T_DJ_Iron_BC: 0 % rust there): u along
    the horizontal in-plane axis, compressed k (texel density 0.85 x nominal, inside the QA tolerance), repeating every
    `period` m (one door leaf); v = height at the nominal 2 m tile. The UV choice only: the material is the library's."""
    me = obj.data
    im = next((i for i, m in enumerate(me.materials) if m.name == IR), None)
    if im is None:
        return 0
    uv = me.uv_layers["UVMap"].data
    n = 0
    for poly in me.polygons:
        if poly.material_index != im:
            continue
        nr = poly.normal
        ax = max(range(3), key=lambda i: abs(nr[i]))
        a_i, b_i = {0: (1, 2), 1: (0, 2), 2: (0, 1)}[ax]
        ca = poly.center[a_i]
        a0 = math.floor(ca / period) * period
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uv[li].uv = (u0 + (co[a_i] - a0) * 0.5 * k, co[b_i] * 0.5 + 0.13)
        n += 1
    return n


# ------------------------------------------------------------------------------------------------ STOREHOUSE walls
STORE_COURSES = [(0.0, 0.5), (0.5, BAND_TOP)]
SD = {"x": (0.30, 2.20), "z": (0.15, 2.35), "post": 0.12, "lintel": 0.18}   # store door opening in the 2.5 m bay


def store_upper(g, x0, x1, z0=BAND_TOP):
    """Plaster from the band top to the plate, the plaster plate, the frieze (kura: plastered to the eaves)."""
    cbox(g, x0, x1, 0.0, WT, z0 - 0.004, PLATE_BOT + 0.004, PL, ch=0.004)
    cbox(g, x0, x1, -0.012, WT, PLATE_BOT, PLATE_TOP, PL, ch=0.008)
    frieze(g, x0, x1, PL)


def store_bay(L, seed):
    p = local_piece({2.0: "SM_DKO_Store_Bay_2m", 2.5: "SM_DKO_Store_Bay_2p5"}[L], "building",
                    "Outbuildings/Storehouse",
                    f"storehouse eave-wall bay {L} m (kura): two courses of hewn granite to +1.0 (proud 4 cm, "
                    "staggered, pitched faces), cream plaster to the wall plate, plastered plate + frieze between the "
                    "rafters; face at local y 0 (outward -y), 0.25 m thick; BR-reusable module")
    g = p.g
    granite_band(g, 0.0, L, STORE_COURSES, seed)
    store_upper(g, 0.0, L)
    p.hull_box(0.0, L, -BAND_PROUD, WT, 0.0, PLATE_TOP)
    p.extra = {"length": L, "face_y": 0.0, "top": round(PLATE_TOP, 4)}
    return p


def store_door_bay():
    L = 2.5
    p = local_piece("SM_DKO_Store_Bay_Door", "building", "Outbuildings/Storehouse",
                    "storehouse door bay 2.5 m: the granite band either side, a dark timber door frame (jamb posts, "
                    "lintel) round a 1.9 x 2.2 m opening, granite threshold and a wide granite step (sheet), plaster "
                    "over the lintel to the plate; the steel leaves are SM_DKO_Door_Steel")
    g = p.g
    (xa, xb), (za, zb) = SD["x"], SD["z"]
    pw, lh = SD["post"], SD["lintel"]
    granite_band(g, 0.0, xa - pw, STORE_COURSES, 71, end_hi=False)
    granite_band(g, xb + pw, L, STORE_COURSES, 72, end_lo=False)
    # plaster either side of the frame and over the lintel
    cbox(g, 0.0, xa - pw + 0.004, 0.0, WT, BAND_TOP - 0.004, PLATE_BOT + 0.004, PL, ch=0.004)
    cbox(g, xb + pw - 0.004, L, 0.0, WT, BAND_TOP - 0.004, PLATE_BOT + 0.004, PL, ch=0.004)
    cbox(g, xa - pw, xb + pw, 0.0, WT, zb + lh - 0.004, PLATE_BOT + 0.004, PL, ch=0.004)
    cbox(g, 0.0, L, -0.012, WT, PLATE_BOT, PLATE_TOP, PL, ch=0.008)
    frieze(g, 0.0, L, PL)
    # frame: jamb posts, lintel (proud 5 cm), a plain reveal behind the leaves
    for x0 in (xa - pw, xb):
        cbox(g, x0, x0 + pw, -0.05, WT, za, zb + lh, TD, ch=0.01)
    cbox(g, xa - pw - 0.03, xb + pw + 0.03, -0.055, WT, zb, zb + lh, TD, ch=0.01)
    cbox(g, xa, xb, 0.105, WT - 0.01, za, zb, TD, ch=0.004)           # backing behind the leaves (closed)
    # granite threshold and the step (sheet: a step about 2.9 m wide, 0.15 high)
    hewn(g, xa - pw, xb + pw, -0.06, WT, 0.0, za, 73, exposed=("-d", "+u"))
    hewn(g, -0.2, L + 0.2, -0.47, -0.045, 0.0, 0.15, 74, exposed=("-d", "+u", "-a", "+a"), ch=0.02)
    p.hull_box(0.0, L, -BAND_PROUD, WT, 0.0, PLATE_TOP)
    p.hull_box(-0.2, L + 0.2, -0.47, -BAND_PROUD, 0.0, 0.15)
    p.extra = {"length": L, "door_opening_x": [xa, xb], "door_opening_z": [za, zb], "step_top": 0.15,
               "leaves_at_local": [xa, 0.0, za]}
    return p


def gable_top(x):
    """Local gable top (the sarking underside) at local x along the body depth (x 0 = the south face)."""
    run = FACE_RUN + min(x, DEPTH - x)
    return zcol(run) - SARK_UNDER - 0.003


def gable_prism(g, x0, x1, y0, y1, zb, mat, top_off=0.0):
    """The gable wall body from zb up to the roof underside, x0..x1 local (x along the body depth), y0..y1 thickness."""
    xm = DEPTH / 2
    pts = [(x0, zb), (x1, zb), (x1, gable_top(x1) - top_off)]
    if x0 < xm < x1:
        pts.append((xm, gable_top(xm) - top_off))
    pts.append((x0, gable_top(x0) - top_off))
    poly = [Vector((px, y1, pz)) for px, pz in pts]          # prism extrudes AGAINST the direction: from y1 to y0
    K.prism(g, poly, (0, 1, 0), y1 - y0, mat, frame=(Vector((1, 0, 0)), Vector((0, 0, 1)), Vector((0, 1, 0))))


def gable_hulls(p, zb=0.0, y0=-0.02):
    """Box to the plate + the triangular prism to the roof underside (kept 5 cm under the roof slab's top)."""
    zt = PLATE_TOP
    p.hull_box(0.0, DEPTH, y0, WT, zb, zt)
    xm = DEPTH / 2
    pts = []
    for x in (0.0, xm, DEPTH):
        for y in (y0, WT):
            pts.append((x, y, gable_top(x) - 0.05))
    for x in (0.0, DEPTH):
        for y in (y0, WT):
            pts.append((x, y, zt - 0.01))
    p.hulls.append(pts)


def store_vent(g, xc, zc):
    """The sheet's gable vent: a small square opening with a raised plaster surround, a dark timber frame and
    vertical bars over a dark recess (modelled proud of the wall face)."""
    # a plaster surround 7 cm proud with a 0.44 m opening through it, a dark timber frame lining the opening,
    # vertical bars, a dark board at the wall face behind (the opening reads about 7 cm deep)
    o, t = 0.22, 0.11
    for (xa, xb, za, zb) in ((xc - o - t, xc - o, zc - o - t, zc + o + t), (xc + o, xc + o + t, zc - o - t, zc + o + t),
                             (xc - o, xc + o, zc - o - t, zc - o), (xc - o, xc + o, zc + o, zc + o + t)):
        cbox(g, xa, xb, -0.07, 0.01, za, zb, PL, ch=0.012)
    for (xa, xb, za, zb) in ((xc - o, xc - o + 0.045, zc - o, zc + o), (xc + o - 0.045, xc + o, zc - o, zc + o),
                             (xc - o, xc + o, zc - o, zc - o + 0.045), (xc - o, xc + o, zc + o - 0.045, zc + o)):
        cbox(g, xa, xb, -0.075, -0.002, za, zb, TD, ch=0.006)
    cbox(g, xc - o, xc + o, -0.004, 0.004, zc - o, zc + o, TD, ch=0.001)                 # dark board behind
    for i in range(4):
        x = xc - o + 0.045 + (2 * o - 0.09) * (i + 0.5) / 4
        cbox(g, x - 0.014, x + 0.014, -0.05, -0.004, zc - o + 0.04, zc + o - 0.04, TD, ch=0.003)   # bars


def store_gable():
    p = local_piece("SM_DKO_Store_Gable", "building", "Outbuildings/Storehouse",
                    "storehouse gable end over the full body depth (both corners): the granite band wrapping both "
                    "corners, cream plaster up to the roof underside, the small framed gable vent (sheet); local x "
                    "along the depth 0..7.52 (x 0 = the south corner), face at y 0 (outward -y); placed east (turned "
                    "90) and west (turned -90)")
    g = p.g
    granite_band(g, 0.0, DEPTH, STORE_COURSES, 81, end_lo=True, end_hi=True)
    # plaster: rectangle from the band to the plate + the triangle to the roof underside (one prism), and the ends
    gable_prism(g, 0.0, DEPTH, 0.0, WT, BAND_TOP - 0.004, PL)
    store_vent(g, DEPTH / 2, gable_top(DEPTH / 2) - 0.78)
    gable_hulls(p, y0=-BAND_PROUD)
    p.extra = {"depth": DEPTH, "apex_under_sarking": round(gable_top(DEPTH / 2), 4),
               "vent_centre_z": round(gable_top(DEPTH / 2) - 0.78, 3)}
    return p


# ------------------------------------------------------------------------------------------------ RESIDENCE walls
RP = 0.18          # residence post (sheet: slender dark posts)
PURLIN_OUT = 0.53  # purlin ends out to just behind the bargeboard of the 0.6 m verge (sheet: blocks under the rake)
BARGE_H = 0.16     # bargeboard depth (sheets: a slim rake board; roof_kit's default 0.26 hid the purlin ends)


def res_base(g, x0, x1, seed, end_lo=False, end_hi=False):
    """Granite foundation course, sill beam (dodai), board-and-batten wainscot, rail."""
    granite_band(g, x0, x1, [(0.0, R_FOUND)], seed, face_y=-0.03, end_lo=end_lo, end_hi=end_hi, target=0.9)
    cbox(g, x0 - (0.02 if end_lo else 0.0), x1 + (0.02 if end_hi else 0.0), -0.02, WT, R_FOUND, R_SILL, TD, ch=0.01)
    boards(g, x0, x1, R_SILL - 0.004, R_RAIL[0] + 0.004, -0.004, seed=seed)
    cbox(g, x0, x1, -0.022, 0.06, R_RAIL[0], R_RAIL[1], TD, ch=0.008)


def res_upper(g, x0, x1, z0=R_RAIL[1]):
    cbox(g, x0, x1, 0.0, WT, z0 - 0.004, PLATE_BOT + 0.004, PL, ch=0.004)


def res_plate(g, x0, x1):
    cbox(g, x0, x1, -0.025, WT, PLATE_BOT, PLATE_TOP, TD, ch=0.012)
    frieze(g, x0, x1, TD)


def res_post(g, x0, z0=R_SILL - 0.01, z1=None, y0=-0.028):
    cbox(g, x0, x0 + RP, y0, WT, z0, (PLATE_BOT + 0.004) if z1 is None else z1, TD, ch=0.012)


def res_bay_plain(L, seed):
    tag = {1.1: "1p1", 2.15: "2p15"}[L]
    p = local_piece(f"SM_DKO_Res_Bay_{tag}", "building", "Outbuildings/Residence",
                    f"residence eave-wall bay {L} m (timber-framed): granite foundation course, sill beam, dark "
                    "board-and-batten wainscot to +0.95, rail, cream plaster, timber wall plate + frieze; face at local "
                    "y 0 (outward -y); BR-reusable module")
    g = p.g
    res_base(g, 0.0, L, seed)
    res_upper(g, 0.0, L)
    res_plate(g, 0.0, L)
    p.hull_box(0.0, L, -0.03, WT, 0.0, PLATE_TOP)
    p.extra = {"length": L}
    return p


RDOOR = {"L": 2.0, "x": (RP, 2.0 - RP), "z": (R_SILL, 2.22), "lintel": 0.14}
RWIN = {"L": 2.3, "strip": 0.30, "z": (R_RAIL[1], 2.25)}


def res_bay_door():
    L = RDOOR["L"]
    (xa, xb), (za, zb) = RDOOR["x"], RDOOR["z"]
    p = local_piece("SM_DKO_Res_Bay_Door", "building", "Outbuildings/Residence",
                    "residence door bay 2.0 m: two jamb posts to the plate, a lintel, the sill beam as threshold, "
                    "plaster over the lintel, a granite step; the wooden leaves are SM_DKO_Door_Wood")
    g = p.g
    granite_band(g, 0.0, L, [(0.0, R_FOUND)], 91, face_y=-0.03, target=0.9)
    cbox(g, 0.0, L, -0.02, WT, R_FOUND, R_SILL, TD, ch=0.01)
    res_post(g, 0.0)
    res_post(g, xb)
    cbox(g, xa - 0.02, xb + 0.02, -0.03, WT, zb, zb + RDOOR["lintel"], TD, ch=0.01)
    res_upper(g, xa - 0.004, xb + 0.004, zb + RDOOR["lintel"])
    res_plate(g, 0.0, L)
    cbox(g, xa, xb, 0.08, WT - 0.01, za, zb, TD, ch=0.004)             # backing behind the leaves (closed)
    hewn(g, -0.10, L + 0.10, -0.42, -0.032, 0.0, 0.13, 92, exposed=("-d", "+u", "-a", "+a"), ch=0.018)
    p.hull_box(0.0, L, -0.03, WT, 0.0, PLATE_TOP)
    p.hull_box(-0.10, L + 0.10, -0.42, -0.03, 0.0, 0.13)
    p.extra = {"length": L, "door_opening_x": [xa, xb], "door_opening_z": [za, zb], "leaves_at_local": [xa, 0.0, za]}
    return p


def res_bay_window():
    L, s = RWIN["L"], RWIN["strip"]
    za, zb = RWIN["z"]
    xa, xb = s + RP, L - RP
    p = local_piece("SM_DKO_Res_Bay_Window", "building", "Outbuildings/Residence",
                    "residence window bay 2.3 m: a 0.3 m plain strip, two posts round a 1.64 m lattice window "
                    "(sill = the rail at +0.95..1.03, head rail), wainscot under the sill, plaster over the head; the "
                    "lattice + lit paper are SM_DKO_Window_Lattice")
    g = p.g
    res_base(g, 0.0, L, 93)
    res_upper(g, 0.0, s + 0.004)
    res_post(g, s)
    res_post(g, xb)
    cbox(g, xa - 0.02, xb + 0.02, -0.04, WT, zb, zb + 0.10, TD, ch=0.01)            # head rail
    cbox(g, xa - 0.02, xb + 0.02, -0.06, 0.06, R_RAIL[0], R_RAIL[1] + 0.01, TD, ch=0.008)   # sill (proud)
    res_upper(g, xa - 0.004, xb + 0.004, zb + 0.10)
    res_plate(g, 0.0, L)
    cbox(g, xa, xb, 0.09, WT - 0.01, za, zb, TD, ch=0.004)             # backing behind the window (closed)
    p.hull_box(0.0, L, -0.03, WT, 0.0, PLATE_TOP)
    p.extra = {"length": L, "window_opening_x": [xa, xb], "window_opening_z": [za, zb], "window_at_local": [xa, 0.0, za]}
    return p


def res_vent(g, xc, zc):
    """The residence sheet's gable vent: a small upright opening with a dark frame and vertical slats."""
    cbox(g, xc - 0.16, xc + 0.16, -0.05, -0.015, zc - 0.28, zc + 0.28, TD, ch=0.008)
    cbox(g, xc - 0.11, xc + 0.11, -0.052, -0.05, zc - 0.23, zc + 0.23, TD, ch=0.001)
    for i in range(4):
        x = xc - 0.075 + 0.05 * i
        cbox(g, x - 0.012, x + 0.012, -0.068, -0.05, zc - 0.23, zc + 0.23, TD, ch=0.003)


def res_gable():
    p = local_piece("SM_DKO_Res_Gable", "building", "Outbuildings/Residence",
                    "residence gable end over the full body depth: corner posts, granite course, sill beam, "
                    "board-and-batten wainscot, rail, plaster, the tie beam at the eave line, the plaster triangle "
                    "with a slatted vent, purlin ends under the verge (sheet); placed east (turned 90) and west (-90)")
    g = p.g
    res_base(g, 0.0, DEPTH, 95, end_lo=True, end_hi=True)
    # corner posts (they carry the corners of both walls), proud of both faces
    for x0 in (-0.02, DEPTH - 0.23):
        cbox(g, x0, x0 + 0.25, -0.03, WT, R_SILL - 0.01, PLATE_TOP, TD, ch=0.012)
    # plaster: to the tie beam, and the triangle above it (one prism, the tie beam laid over it)
    gable_prism(g, 0.21, DEPTH - 0.21, 0.0, WT, R_RAIL[1] - 0.004, PL)
    cbox(g, -0.02, DEPTH + 0.02, -0.035, WT, PLATE_BOT, PLATE_TOP, TD, ch=0.012)     # tie beam at the eave line
    xm = DEPTH / 2
    res_vent(g, xm, gable_top(xm) - 0.72)
    # purlin ends (moya) under the rafters, poking 0.40 m out of the gable (sheet), and the ridge purlin
    for x in (xm - 2.4, xm - 1.2, xm, xm + 1.2, xm + 2.4):
        zt = gable_top(x) - 0.10 + 0.003 - 0.002          # purlin top = the rafter underside there
        cbox(g, x - 0.065, x + 0.065, -PURLIN_OUT, WT - 0.02, zt - 0.19, zt, TD, ch=0.012)
    gable_hulls(p, y0=-0.03)
    p.extra = {"depth": DEPTH, "purlin_protrusion": PURLIN_OUT}
    return p


# ------------------------------------------------------------------------------------------------ doors / window
def door_steel():
    W, H = SD["x"][1] - SD["x"][0], SD["z"][1] - SD["z"][0]
    p = local_piece("SM_DKO_Door_Steel", "building", "Outbuildings/Storehouse",
                    "storehouse steel double door (closed): two flat leaves with a narrow raised border, a centre "
                    "meeting stile, two round knob pulls, hinge knuckles; local x 0..1.9, z 0..2.2, face 5 cm behind "
                    "the wall face")
    g = p.g
    yf = 0.05
    for k, (xa, xb) in enumerate(((0.004, W / 2 - 0.003), (W / 2 + 0.003, W - 0.004))):
        cbox(g, xa, xb, yf, yf + 0.045, 0.006, H - 0.004, IR, ch=0.004)                    # leaf
        b = 0.045
        for (x0, x1, z0, z1) in ((xa, xa + b, 0.006, H - 0.004), (xb - b, xb, 0.006, H - 0.004),
                                 (xa + b, xb - b, H - 0.004 - b, H - 0.004), (xa + b, xb - b, 0.006, 0.006 + b)):
            cbox(g, x0 + 0.004, x1 - 0.004, yf - 0.008, yf + 0.002, z0 + 0.004, z1 - 0.004, IR, ch=0.002)
        xk = xb - 0.09 if k == 0 else xa + 0.09
        K.lathe(g, Vector((xk, yf - 0.008, 1.02)), Vector((0, -1, 0)), Vector((0, 0, 1)),
                [(0.0, 0.028), (0.012, 0.028), (0.016, 0.012), (0.034, 0.012), (0.040, 0.030), (0.058, 0.030),
                 (0.062, 0.0)], IR, nseg=16)
        xh = xa + 0.02 if k == 0 else xb - 0.02
        for zh in (0.30, H - 0.35):
            K.lathe(g, Vector((xh, yf - 0.012, zh - 0.07)), Vector((0, 0, 1)), Vector((0, -1, 0)),
                    [(0.0, 0.0), (0.0, 0.016), (0.14, 0.016), (0.14, 0.0)], IR, nseg=10)
    cbox(g, W / 2 - 0.018, W / 2 + 0.018, yf - 0.014, yf + 0.004, 0.01, H - 0.01, IR, ch=0.003)   # meeting stile
    p.hull_box(0.0, W, yf - 0.01, yf + 0.045, 0.0, H)
    p.extra = {"w": W, "h": H}
    return p


def door_wood():
    (xa, xb), (za, zb) = RDOOR["x"], RDOOR["z"]
    W, H = xb - xa, zb - za
    p = local_piece("SM_DKO_Door_Wood", "building", "Outbuildings/Residence",
                    "residence wooden double door (closed): each leaf vertical boards in a frame with a mid rail, "
                    "iron pull plates and strap hinges; local x 0..1.64, z 0..1.95, face 3 cm behind the post faces")
    g = p.g
    yf = 0.02
    for k, (a, b) in enumerate(((0.004, W / 2 - 0.002), (W / 2 + 0.002, W - 0.004))):
        fw = 0.07
        cbox(g, a, a + fw, yf, yf + 0.045, 0.005, H - 0.004, TA, ch=0.006)
        cbox(g, b - fw, b, yf, yf + 0.045, 0.005, H - 0.004, TA, ch=0.006)
        for (z0, z1) in ((0.005, 0.12), (0.92, 1.04), (H - 0.11, H - 0.004)):
            cbox(g, a + fw - 0.004, b - fw + 0.004, yf, yf + 0.045, z0, z1, TA, ch=0.006)
        for (z0, z1) in ((0.12, 0.92), (1.04, H - 0.11)):
            nb = 3
            bw = (b - a - 2 * fw) / nb
            for i in range(nb):
                cbox(g, a + fw + i * bw + 0.002, a + fw + (i + 1) * bw - 0.002, yf + 0.012, yf + 0.04, z0 - 0.004,
                     z1 + 0.004, TA, ch=0.003)
        xs = b - fw / 2 if k == 0 else a + fw / 2
        cbox(g, xs - 0.02, xs + 0.02, yf - 0.004, yf, 0.86, 1.10, IR, ch=0.002)                       # pull plate
        K.lathe(g, Vector((xs, yf - 0.004, 0.98)), Vector((0, -1, 0)), Vector((0, 0, 1)),
                [(0.0, 0.011), (0.018, 0.011), (0.022, 0.016), (0.030, 0.016), (0.030, 0.0)], IR, nseg=10)
        for zh in (0.30, H - 0.30):                                                                     # strap hinges
            xa_, xb_ = (a + 0.005, a + 0.34) if k == 0 else (b - 0.34, b - 0.005)
            cbox(g, xa_, xb_, yf - 0.006, yf, zh - 0.022, zh + 0.022, IR, ch=0.002)
    p.hull_box(0.0, W, yf - 0.006, yf + 0.045, 0.0, H)
    p.extra = {"w": W, "h": H}
    return p


def window_lattice():
    L, s = RWIN["L"], RWIN["strip"]
    W = (L - RP) - (s + RP)
    za, zb = RWIN["z"]
    H = zb - za
    p = local_piece("SM_DKO_Window_Lattice", "building", "Outbuildings/Residence",
                    "residence lattice window (closed): a frame, a square lattice (kumiko) 6 x 8 in front of lit "
                    "paper (GlassAmber, opaque; the interior stays closed) and a dark board behind; local x 0..1.64, "
                    "z 0..1.22")
    g = p.g
    yf = 0.012
    fw = 0.045
    cbox(g, 0.0, fw, yf, yf + 0.05, 0.0, H, TD, ch=0.006)
    cbox(g, W - fw, W, yf, yf + 0.05, 0.0, H, TD, ch=0.006)
    cbox(g, fw - 0.004, W - fw + 0.004, yf, yf + 0.05, 0.0, fw, TD, ch=0.006)
    cbox(g, fw - 0.004, W - fw + 0.004, yf, yf + 0.05, H - fw, H, TD, ch=0.006)
    x0, x1, z0, z1 = fw, W - fw, fw, H - fw
    cols, rows = 6, 8
    bar, dep = 0.022, 0.03
    for i in range(1, cols):
        x = x0 + (x1 - x0) * i / cols
        cbox(g, x - bar / 2, x + bar / 2, yf + 0.004, yf + 0.004 + dep, z0 - 0.004, z1 + 0.004, TD, ch=0.003)
    for j in range(1, rows):
        z = z0 + (z1 - z0) * j / rows
        cbox(g, x0 - 0.004, x1 + 0.004, yf + 0.007, yf + dep + 0.001, z - bar / 2, z + bar / 2, TD, ch=0.003)
    yg = yf + 0.004 + dep + 0.008
    quad(g, [(x0 - 0.004, yg, z0 - 0.004), (x1 + 0.004, yg, z0 - 0.004), (x1 + 0.004, yg, z1 + 0.004),
             (x0 - 0.004, yg, z1 + 0.004)], GL)
    cbox(g, x0 - 0.004, x1 + 0.004, yg + 0.004, yg + 0.02, z0 - 0.004, z1 + 0.004, TD, ch=0.002)
    p.hull_box(0.0, W, yf, yg + 0.02, 0.0, H)
    p.extra = {"w": round(W, 3), "h": round(H, 3), "grid": [cols, rows]}
    return p


# ------------------------------------------------------------------------------------------------ canopies
def canopy(name, W, D, pitch, note, bracket_x=None, ze=0.0):
    """A small tiled lean-to canopy on the wall: local x centred (-W/2..W/2), wall face y 0, projecting to y = -D, its
    tile-top (collision) at the eave line z = ze (placement sets the height). Tiles with eave discs, verges with rolls
    and bargeboards, a tile flashing against the wall, soffit + rafters, a fascia, a wall ledger, and two timber
    brackets (arm + strut) at x = +-bracket_x."""
    p = local_piece(name, "building", "Outbuildings/Canopies", note)
    g = p.g
    tn = math.tan(math.radians(pitch))
    cs = math.cos(math.radians(pitch))
    bo = RK.base_off(pitch)
    rs = RK.RoofSlope((-W / 2, -D), (W / 2, -D), ze, pitch)
    s_top = (D - 0.07) / cs
    C, nc = RK._courses(s_top, 0.26)
    RK.tile_field(g, rs.sl, 0.0, W, 0.0, s_top, C, TL, eave=True, roll_margin=0.10)
    RK.sarking(g, rs, 0.0, W, -0.03, s_top + 0.06, nstrips=4)
    RK.rafters(g, rs, 0.08, W - 0.08, -0.06, D / cs - 0.01, spacing=0.30, w=0.06, d=0.07)
    RK.eave_trim(g, rs, 0.0, W, fascia_h=0.06, fascia_t=0.04)
    for ue, inw in ((0.0, 1), (W, -1)):
        RK.verge(g, rs, ue, 0.0, s_top + 0.04, inward=inw, widths=(0.17, 0.14), h=0.032, roll_r=0.058, disc=0.066,
                 board=True, board_h=0.15, board_t=0.04)
    # flashing against the wall: two noshi courses along the top edge of the tiles
    sl = rs.sl
    zf = ze + (D - 0.10) * tn - 0.035           # on the tile tops 0.10 m in front of the wall
    a = Vector((-W / 2 + 0.03, -0.10, zf))
    b = Vector((W / 2 - 0.03, -0.10, zf))
    RK.noshi_tiles(g, a, b, (0, 0, 1), [0.20, 0.17], [0.045, 0.04], TL, seg=0.30, seed=5)
    z_wall = ze + D * tn                        # collision height at the wall
    z_under_wall = z_wall - bo - 0.004 - 0.025 - 0.07
    # ledger on the wall under the rafters, the front beam (keta) under the rafter line near the eave
    cbox(g, -W / 2 + 0.05, W / 2 - 0.05, -0.08, 0.0, z_under_wall - 0.12, z_under_wall, TD, ch=0.008)
    y_beam = -D + 0.16
    z_beam_top = ze + 0.16 * tn - bo - 0.004 - 0.025 - 0.07
    cbox(g, -W / 2 + 0.10, W / 2 - 0.10, y_beam - 0.05, y_beam + 0.05, z_beam_top - 0.11, z_beam_top, TD, ch=0.008)
    bx = bracket_x if bracket_x is not None else W / 2 - 0.35
    z_arm = z_beam_top - 0.11
    for sx in (-1, 1):
        x = sx * bx
        cbox(g, x - 0.045, x + 0.045, y_beam - 0.07, 0.0, z_arm - 0.10, z_arm, TD, ch=0.008)          # arm
        member(g, (x, -0.05, z_arm - 0.55), (x, y_beam + 0.12, z_arm - 0.07), 0.07, 0.07, TD, up=(0, 1, 0.4))  # strut
        cbox(g, x - 0.05, x + 0.05, -0.05, 0.0, z_arm - 0.62, z_arm - 0.44, TD, ch=0.006)            # wall block
    # collision: a slab under the tile plane (0.15), the eave line to the wall
    p.hulls.append(RK.slab([(-W / 2, -D, ze), (W / 2, -D, ze), (W / 2, 0.0, z_wall), (-W / 2, 0.0, z_wall)], 0.15))
    p.extra = {"w": W, "depth": D, "pitch_deg": pitch, "eave_z_local": ze, "wall_z_local": round(z_wall, 4),
               "bracket_x": bx, "lowest_local": round(z_arm - 0.62, 3)}
    return p


# ------------------------------------------------------------------------------------------------ meter box
def meter_box():
    p = local_piece("SM_DKO_MeterBox", "thin", "Outbuildings/Residence",
                    "the residence sheet's electric meter box: a grey steel box with a small meter window and a hood, "
                    "on a mounting plate, two conduits up to the wall plate and one down into the ground, clamps; "
                    "its own asset (face at local y 0, outward -y; local z = world height)")
    g = p.g
    zc = 1.45
    cbox(g, -0.21, 0.21, -0.012, 0.0, zc - 0.32, zc + 0.29, IR, ch=0.003)         # mounting plate (all steel: one
    #                                                                                texture set, a true texel check)
    cbox(g, -0.17, 0.17, -0.15, -0.02, zc - 0.23, zc + 0.23, IR, ch=0.012)        # box
    cbox(g, -0.19, 0.19, -0.17, -0.02, zc + 0.23, zc + 0.26, IR, ch=0.006)        # hood
    cbox(g, -0.09, 0.09, -0.156, -0.140, zc + 0.02, zc + 0.14, IR, ch=0.004)       # meter window frame (proud)
    cbox(g, -0.075, 0.075, -0.158, -0.150, zc + 0.035, zc + 0.125, IR, ch=0.001)   # window (recessed glass stand-in)
    cbox(g, -0.055, 0.055, -0.160, -0.150, zc - 0.16, zc - 0.08, IR, ch=0.002)     # latch plate
    for x in (-0.05, 0.05):
        RK.tube(g, [Vector((x, -0.06, zc + 0.26)), Vector((x, -0.06, PLATE_BOT - 0.01))], 0.016, IR, nseg=10,
                cap1=True)
        for zz in (2.2, 2.9):
            cbox(g, x - 0.025, x + 0.025, -0.085, -0.001, zz - 0.012, zz + 0.012, IR, ch=0.002)
    RK.tube(g, [Vector((0.0, -0.06, zc - 0.23)), Vector((0.0, -0.06, 0.02))], 0.020, IR, nseg=10, cap1=True)
    for zz in (0.5, 0.9):
        cbox(g, -0.03, 0.03, -0.09, -0.001, zz - 0.012, zz + 0.012, IR, ch=0.002)
    p.hull_box(-0.19, 0.19, -0.17, 0.0, zc - 0.34, zc + 0.30)
    p.extra = {"box_centre_z": zc}
    return p


# ------------------------------------------------------------------------------------------------ roof
def roof_pieces():
    """The gable roof (spec + grey-box numbers) as a shared SLOPE piece (the south slope; the north is the same piece
    turned 180 deg) and a RIDGE piece, both built in the storehouse frame with the pivot at the roof centre, so the
    residence reuses them (its roof X 36.4-45 has the same size). roof_kit gable_roof's parts, split for instancing."""
    x0, x1 = ROOF_X["store"]
    W = x1 - x0
    piv = ((x0 + x1) / 2, CY, 0.0)
    s_ridge = (RUN - 0.18) / CS
    C, nc = RK._courses(s_ridge)
    rs = RK.RoofSlope((x0, Y0), (x1, Y0), EAVE, PITCH)
    g = Geo()
    RK.tile_field(g, rs.sl, 0.0, W, 0.0, s_ridge, C, TL, eave=True, roll_margin=0.16)
    RK.sarking(g, rs, 0.0, W, -0.04, s_ridge + 0.1, nstrips=10)
    RK.rafters(g, rs, 0.10, W - 0.10, -0.07, s_ridge, spacing=0.30, caps=True)
    RK.eave_trim(g, rs, 0.0, W)
    for ue, inw in ((0.0, 1), (W, -1)):
        RK.verge(g, rs, ue, 0.0, s_ridge + 0.10, inward=inw, disc=0.085, board=True, board_h=BARGE_H)
    slope = Piece("SM_DKO_Roof_Slope", "roof", "Outbuildings/Roof",
                  "outbuilding gable roof, ONE slope (the south; the north is the same piece turned 180 deg): tiles "
                  "(pans + round tiles, eave discs), sarking, rafters with X-capped tails, the fascia, verges (tile "
                  "stack + roll + end disc, bargeboard); 8.6 m wide over the perimeter wall (grey-box), eave +3.25, "
                  "planes meet +5.25 at Y 31.7 (the grey-box slope, 24.944 deg); collision = the grey-box slab",
                  pivot=piv)
    slope.g = g
    slope.kit = KIT
    slope.hulls = [RK.slab([(x0, Y0, EAVE), (x1, Y0, EAVE), (x1, CY, RIDGE_Z), (x0, CY, RIDGE_Z)])]
    slope.wear = False
    slope.nanite = True
    rg = Geo()
    ridge_layers, ridge_roll, oni = (0.40, 0.37, 0.34), 0.09, (0.55, 0.62, 0.30)
    rtop, z0r = RK.ridge(rg, (x0 + 0.20, CY), (x1 - 0.20, CY), RIDGE_Z, widths=ridge_layers, roll_r=ridge_roll,
                         bed_w=0.44, courses=None)
    oW, oH, oT = oni
    for xe, f in ((x0 + 0.02, -1), (x1 - 0.02, 1)):
        RK.ridge_end_any(rg, (xe - f * oT / 2, CY, z0r - 0.08), (f, 0, 0), oW, oH, oT, None, TL,
                         cap_z=(rtop - ridge_roll - 0.016) - (z0r - 0.08), cap_r=ridge_roll)
    ridge = Piece("SM_DKO_Roof_Ridge", "roof", "Outbuildings/Roof",
                  "outbuilding ridge (roof_kit 1.3.0 defaults): bed, three courses of real noshi tiles, the round "
                  "cap-tile row with tile collars, the plain onigawara at both verges (bullnose tiers, arched tile "
                  "with a plain round crest, cap-end disc and two lobes; no faces, creatures or symbols)", pivot=piv)
    ridge.g = rg
    ridge.kit = KIT
    ridge.hulls = [[(x, y, z) for x in (x0, x1) for y in (CY - 0.24, CY + 0.24) for z in (RIDGE_Z - 0.13, rtop)]]
    ridge.wear = False
    ridge.nanite = True
    nums = {"pitch_deg": round(PITCH, 4), "planes_meet": RIDGE_Z, "ridge_cap_top": round(rtop, 4),
            "course_m": round(C, 4), "courses": nc, "roof_x": [x0, x1], "roof_y": [Y0, Y1],
            "gutter_rim_z": round(GUTTER_Z, 4), "plate_top": round(PLATE_TOP, 4)}
    return [slope, ridge], nums


def gutter_piece(L=7.05):
    p = local_piece("SM_DKO_Gutter", "thin", "Outbuildings/Roof",
                    f"half-round gutter {L} m on hooked strap brackets (roof sheet panel f), capped both ends; local x "
                    "0..L along the eave, rim centre line at local y 0 z 0, fascia side +y (placed at the eave line "
                    f"- 0.09 m, rim +{GUTTER_Z:.3f}); uniform along its length (the downpipes are placed where they "
                    "drain)")
    RK.gutter(p.g, [(0.0, 0.0, 0.0), (L, 0.0, 0.0)], fascia_side=(0, 1, 0), caps=(True, True))
    p.hull_box(0.0, L, -0.08, 0.08, -0.08, 0.012)
    p.extra = {"length": L}
    return p


def downpipe_piece():
    p = local_piece("SM_DKO_Downpipe", "thin", "Outbuildings/Roof",
                    "round downpipe from the gutter, a two-bend swan neck back to the wall, wall clamps, a shoe; local "
                    "origin = the pipe foot on its axis, 0.105 m in front of the plaster face (local +y = the wall), "
                    "outlet 0.525 m out at the gutter")
    top = GUTTER_Z - 0.04
    out = -(FACE_RUN + GUTTER_OFF - PIPE_OFF)
    RK.downpipe(p.g, [(0, out, top), (0, out, GUTTER_Z - 0.22), (0, 0.0, GUTTER_Z - 0.62), (0, 0.0, 0.14)], r=0.045,
                bend_r=0.14, clamps=(0.95, 1.95), clamp_to=(0, 1, 0))
    RK.tube(p.g, [Vector((0, out, GUTTER_Z - 0.075)), Vector((0, out, GUTTER_Z - 0.12))], 0.056, IR, cap0=True,
            cap1=True)
    p.hull_box(-0.05, 0.05, -0.05, 0.05, 0.0, GUTTER_Z - 0.62)
    p.extra = {"outlet_local": [0.0, round(out, 4), round(top, 4)]}
    return p


# ------------------------------------------------------------------------------------------------ layout
CANOPY_Z = {"store": 2.66, "res_door": 2.56, "res_win": 2.44}   # canopy eave (tile-top) heights, world


def instances():
    I = []
    add = lambda piece, loc, rot, bld: I.append((piece, loc, rot, bld))   # noqa: E731
    # ---- storehouse (NW)
    sx0, sx1 = BODY_X["store"]
    add("SM_DKO_Store_Gable", (sx1, FACE_S, 0.0), 90.0, "store")
    add("SM_DKO_Store_Gable", (sx0, FACE_N, 0.0), -90.0, "store")
    x = sx0 + WT
    for piece, L in (("SM_DKO_Store_Bay_2m", 2.0), ("SM_DKO_Store_Bay_Door", 2.5), ("SM_DKO_Store_Bay_2m", 2.0)):
        add(piece, (x, FACE_S, 0.0), 0.0, "store")
        if piece == "SM_DKO_Store_Bay_Door":
            add("SM_DKO_Door_Steel", (x + SD["x"][0], FACE_S, SD["z"][0]), 0.0, "store")
            add("SM_DKO_Canopy_2p8", (x + L / 2, FACE_S, CANOPY_Z["store"]), 0.0, "store")
        x += L
    x = sx1 - WT
    for piece, L in (("SM_DKO_Store_Bay_2m", 2.0), ("SM_DKO_Store_Bay_2p5", 2.5), ("SM_DKO_Store_Bay_2m", 2.0)):
        add(piece, (x, FACE_N, 0.0), 180.0, "store")
        x -= L
    # ---- residence (NE)
    rx0, rx1 = BODY_X["res"]
    add("SM_DKO_Res_Gable", (rx1, FACE_S, 0.0), 90.0, "res")
    add("SM_DKO_Res_Gable", (rx0, FACE_N, 0.0), -90.0, "res")
    x = rx0 + WT
    for piece, L in (("SM_DKO_Res_Bay_1p1", 1.1), ("SM_DKO_Res_Bay_Door", 2.0), ("SM_DKO_Res_Bay_Window", 2.3),
                     ("SM_DKO_Res_Bay_1p1", 1.1)):
        add(piece, (x, FACE_S, 0.0), 0.0, "res")
        if piece == "SM_DKO_Res_Bay_Door":
            add("SM_DKO_Door_Wood", (x + RDOOR["x"][0], FACE_S, RDOOR["z"][0]), 0.0, "res")
            add("SM_DKO_Canopy_2p2", (x + L / 2, FACE_S, CANOPY_Z["res_door"]), 0.0, "res")
        if piece == "SM_DKO_Res_Bay_Window":
            wx = x + RWIN["strip"] + RP
            add("SM_DKO_Window_Lattice", (wx, FACE_S, RWIN["z"][0]), 0.0, "res")
            add("SM_DKO_Canopy_Window", (x + RWIN["strip"] + (L - RWIN["strip"]) / 2, FACE_S, CANOPY_Z["res_win"]),
                0.0, "res")
        if piece == "SM_DKO_Res_Bay_1p1" and x > rx0 + 3:
            add("SM_DKO_MeterBox", (x + 0.55, FACE_S, 0.0), 0.0, "res")
        x += L
    x = rx1 - WT
    for piece, L in (("SM_DKO_Res_Bay_1p1", 1.1), ("SM_DKO_Res_Bay_2p15", 2.15), ("SM_DKO_Res_Bay_2p15", 2.15),
                     ("SM_DKO_Res_Bay_1p1", 1.1)):
        add(piece, (x, FACE_N, 0.0), 180.0, "res")
        x -= L
    # ---- roofs: the slope piece south (0) + north (180), the ridge; the residence reuses them at its own centre
    for bld in ("store", "res"):
        x0, x1 = ROOF_X[bld]
        c = ((x0 + x1) / 2, CY, 0.0)
        add("SM_DKO_Roof_Slope", c, 0.0, bld)
        add("SM_DKO_Roof_Slope", c, 180.0, bld)
        add("SM_DKO_Roof_Ridge", c, 0.0, bld)
    # ---- gutters + downpipes (south gutters stop clear of kit 1's route-2 step pier; outlets at local 0.15 / L-0.70)
    ys, yn = Y0 - GUTTER_OFF, Y1 + GUTTER_OFF
    add("SM_DKO_Gutter", (0.50, ys, GUTTER_Z), 0.0, "store")          # X 0.50 -> 7.55: pipes at 0.65 / 6.85
    add("SM_DKO_Gutter", (7.55, yn, GUTTER_Z), 180.0, "store")        # X 7.55 -> 0.50: pipes at 6.85 / 0.65
    # (the gutter is uniform: turning it 180 deg only moves its brackets to the other side, toward the fascia)
    add("SM_DKO_Gutter", (36.45, ys, GUTTER_Z), 0.0, "res")           # X 36.45 -> 43.50: pipes at 37.15 / 43.35
    add("SM_DKO_Gutter", (43.50, yn, GUTTER_Z), 180.0, "res")         # X 43.50 -> 36.45: pipes at 43.35 / 37.15
    for bld, xs in (("store", (0.65, 6.85)), ("res", (37.15, 43.35))):
        for xp in xs:
            add("SM_DKO_Downpipe", (xp, FACE_S - PIPE_OFF, 0.0), 0.0, bld)
            add("SM_DKO_Downpipe", (xp, FACE_N + PIPE_OFF, 0.0), 180.0, bld)
    return I


REPLACED = ["SM_DGB_Storehouse", "SM_DGB_Storehouse_Roof", "SM_DGB_Residence", "SM_DGB_Residence_Roof"]
# PROPOSED for the combined import (other kits' props placed on the grey-box faces; applied here only to our check /
# render context, never to their layouts): the modern kit's wall AC stood in front of the residence's lattice window
# (the sheet's window); it moves to the residence's west gable between its corner and the corridor. The storehouse
# junction box sank 4 cm into the granite band; it moves out onto the band face.
PROPOSED_MOVES = [
    {"piece": "SM_DKP_Modern_ACUnit_Wall", "from": [40.8, 27.94, 1.55], "to": [37.0, 28.7, 1.55], "rot_z": -90.0,
     "why": "stood in front of the residence's lattice window (X 40.83-42.47, +1.03..2.25)"},
    {"piece": "SM_DKP_Modern_JunctionBox", "from": [2.2, 27.94, 0.3], "to": [2.2, 27.90, 0.3], "rot_z": 0.0,
     "why": "its back was 4 cm inside the storehouse granite band (face Y 27.90)"},
]


def place(piece, loc, rot, bld):
    return {"piece": piece, "loc": [round(v, 4) for v in loc], "rot_z": float(rot), "building": bld}


# ------------------------------------------------------------------------------------------------ main
def main():
    t0 = time.time()
    assert_owner("DojoOutbuildings", "claude")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    kit = bpy.data.collections.new("Kit")
    sc.collection.children.link(kit)
    asm = bpy.data.collections.new("Assembly")
    sc.collection.children.link(asm)
    roofs, roof_nums = roof_pieces()
    P = [store_bay(2.0, 11), store_bay(2.5, 12), store_door_bay(), store_gable(),
         res_bay_plain(1.1, 21), res_bay_plain(2.15, 22), res_bay_door(), res_bay_window(), res_gable(),
         door_steel(), door_wood(), window_lattice(),
         canopy("SM_DKO_Canopy_2p8", 2.8, 0.72, 25.0,
                "storehouse door canopy 2.8 x 0.72 m (sheet: a small tiled lean-to over the door on two brackets): "
                "tiles with eave discs, verge rolls, wall flashing, soffit + rafters, fascia, ledger, front beam, "
                "two bracket arms with struts; BR-reusable", bracket_x=1.01),
         canopy("SM_DKO_Canopy_2p2", 2.2, 0.66, 25.0,
                "residence door canopy 2.2 x 0.66 m (sheet), same build as the storehouse canopy", bracket_x=0.82),
         canopy("SM_DKO_Canopy_Window", 2.05, 0.46, 22.0,
                "residence window hood 2.05 x 0.46 m, lower than the door canopy (sheet)", bracket_x=0.82),
         meter_box()] + roofs + [gutter_piece(), downpipe_piece()]
    objs, stats = {}, {}
    for p in P:
        t1 = time.time()
        o, bad = geo_to_object(p, kit)
        objs[p.name] = o
        stats[p.name] = {"tris": sum(len(pl.vertices) - 2 for pl in o.data.polygons), "bad_faces": bad,
                         "sec": round(time.time() - t1, 1)}
        print("BUILT", p.name, stats[p.name], flush=True)
    calm = {}
    for name in ("SM_DKO_Res_Bay_1p1", "SM_DKO_Res_Bay_2p15", "SM_DKO_Res_Bay_Window", "SM_DKO_Res_Gable"):
        calm[name] = calm_boards(objs[name])
    print("CALM boards", calm, flush=True)
    clean = {"SM_DKO_Door_Steel": clean_iron_uv(objs["SM_DKO_Door_Steel"], (SD["x"][1] - SD["x"][0]) / 2),
             "SM_DKO_MeterBox": clean_iron_uv(objs["SM_DKO_MeterBox"], 0.5)}
    print("CLEAN iron faces", clean, flush=True)
    for p in P:
        if stats[p.name]["tris"] >= 2000:
            p.nanite = True
        objs[p.name]["nanite"] = p.nanite
    if not QUICK:
        for p in P:
            if p.wear:
                t1 = time.time()
                djm.bake_wear(objs[p.name])
                print("WEAR", p.name, round(time.time() - t1, 1), flush=True)
    # ---- layout (grey-box world frame)
    inst = [place(*i) for i in instances()]
    pieces = {p.name: p for p in P}
    for it in inst:
        p = pieces[it["piece"]]
        it.update({"folder": p.folder, "collision_class": p.cls, "kit": KIT})
    for n, it in enumerate(inst):
        o = bpy.data.objects.new(f"{it['piece']}__o{n:03d}", objs[it["piece"]].data)
        o.matrix_world = Matrix.Translation(it["loc"]) @ Matrix.Rotation(math.radians(it["rot_z"]), 4, "Z")
        asm.objects.link(o)
        pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
        it["bbox_min_max"] = [round(min(q[i] for q in pts), 4) for i in range(3)] + \
                             [round(max(q[i] for q in pts), 4) for i in range(3)]
    kit.hide_render = True
    kit.hide_viewport = True
    OW.mkdir(parents=True, exist_ok=True)
    LO = {
        "date": "2026-09-29", "stage": "round 4: storehouse + residence (kit 5, SM_DKO_*)",
        "units": "m, grey-box world frame (X east, Y north, Z up; Unreal (x*100, -y*100, z*100), yaw = -rot_z)",
        "roof_kit": {"module": "Scripts/dojo/roof/roof_kit.py", "version": RK.VERSION},
        "material_library": "Scripts/dojo/materials (M_DJ_*), textures Exports/DojoKit/Materials/Textures",
        "pieces": {p.name: {"class": p.cls, "folder": p.folder, "note": p.note, "ucx": len(p.hulls),
                            "tris": stats[p.name]["tris"], "slots": [m.name for m in objs[p.name].data.materials],
                            "nanite": p.nanite, "kit": KIT,
                            "pivot_world": None if p.local else [round(v, 4) for v in p.pivot],
                            **({"extra": p.extra} if p.extra else {})} for p in P},
        "instances": inst,
        "replaces_greybox": REPLACED,
        "numbers": {
            "roof": roof_nums, "eave": EAVE, "ridge_planes": RIDGE_Z, "roof_x": ROOF_X, "roof_y": [Y0, Y1],
            "body_x": BODY_X, "faces_y": {"south": FACE_S, "north": FACE_N}, "wall_thickness": WT,
            "plate": [round(PLATE_BOT, 4), round(PLATE_TOP, 4)], "store_band_top": BAND_TOP,
            "res_base": {"foundation": R_FOUND, "sill": R_SILL, "rail": list(R_RAIL)},
            "canopy_eave_z": CANOPY_Z, "gutter_rim_z": round(GUTTER_Z, 4),
            "route2": "kit 1's SM_DK_Wall_StepPier (flat top +3.25, X -1..0 / 44..45, Y 26.4..27.4) -> the south eave "
                      "slab (+3.25 at Y 27.4): 0.0 m step, unchanged from the grey-box",
            "route3": "south slope at Y 31.0 (+4.924) -> off the verge at X 7.6 / 36.4 -> corridor roof (+3.7): "
                      "1.224 m walk-off drop (grey-box slab, unchanged)",
            "prop_faces": {"note": "other kits' props placed on the grey-box south faces (Y 27.94): our plaster face is "
                                   "Y 27.94 (storehouse; the granite band stands 4 cm proud to 27.90, the residence "
                                   "posts 2.8 cm proud, its plaster at 27.94)",
                           "store_plaster": FACE_S, "store_band": round(FACE_S - BAND_PROUD, 3),
                           "res_plaster": FACE_S, "res_posts": round(FACE_S - 0.028, 3)},
        },
    }
    (OW / "layout_outbuildings.json").write_text(json.dumps(LO, indent=1), encoding="utf-8")
    # ---- QA + export
    qa, exp = {}, {}
    waive = {"uv0_tile_range", "uv_no_overlap"}
    if not QUICK:
        for p in P:
            add_uv1(objs[p.name])
        kit.hide_viewport = False
        for p in P:
            o = objs[p.name]
            has_glow = any(m.name == GL for m in o.data.materials)
            ntri = stats[p.name]["tris"]
            r = qa_check([o], require_uv1=True, texel_density=5.12, tolerance=0.25,
                         overlap_method="operator" if ntri > 40000 else "sat")
            w = set(waive) | ({"texel_density"} if has_glow else set())
            fails = [c for c in r["checks"] if not c["passed"]]
            hard = [c for c in fails if c["name"] not in w]
            tex = next((c["detail"] for c in r["checks"] if c["name"] == "texel_density"), "")
            qa[p.name] = {"hard_fails": hard, "waived": sorted({c["name"] for c in fails if c["name"] in w}),
                          "tris": r["triangles"].get(p.name), "texel_qa": tex,
                          "texel_library_p5_p50_p95": djm.texel_density(o)}
            print("QA", p.name, len(hard), sorted({c["name"] for c in fails}), flush=True)
        kit.hide_viewport = True
        hard_total = sum(len(v["hard_fails"]) for v in qa.values())
        print(f"QA outbuildings: {len(P)} pieces, hard fails {hard_total}", flush=True)
        for k, v in qa.items():
            for c in v["hard_fails"]:
                print("  FAIL", k, c["name"], str(c["detail"])[:240])
        (OW / "qa_report.json").write_text(json.dumps(qa, indent=1, default=str), encoding="utf-8")
        if "--no-export" not in ARGS and hard_total == 0:
            EXPORT_DIR.mkdir(parents=True, exist_ok=True)
            kit.hide_viewport = False
            for p in P:
                o = objs[p.name]
                tris = qa[p.name]["tris"]
                if p.nanite or tris < 400:
                    r = export_fbx(str(EXPORT_DIR / f"{p.name}.fbx"), [o], kind="static", sidecar=False)
                    exp[p.name] = {"lods": 1, "lod_tris": [tris], "nanite": p.nanite, "warnings": r["warnings"]}
                    continue
                tmpc = bpy.data.collections.new("TmpLOD")
                sc.collection.children.link(tmpc)
                c0 = o.copy()
                c0.data = o.data.copy()
                c0.name = f"{p.name}_LOD0"
                tmpc.objects.link(c0)
                for h in o.children:
                    hc = h.copy()
                    hc.data = h.data.copy()
                    hc.name = h.name.replace(f"UCX_{p.name}_", f"UCX_{p.name}_LOD0_")
                    tmpc.objects.link(hc)
                    hc.parent = c0
                lods = decimate_lods(c0, (0.5, 0.25))
                for lo in lods:
                    fix_lod(lo, clamp_to=c0)
                grp = make_lod_group(p.name, [c0] + lods)
                lq = qa_check([c0] + lods, require_uv1=True, require_ucx=False)
                lod_hard = [c for c in lq["checks"] if not c["passed"] and c["name"] not in waive | {"texel_density"}]
                r = export_fbx(str(EXPORT_DIR / f"{p.name}.fbx"), [grp], kind="static", sidecar=True)
                exp[p.name] = {"lods": 3, "lod_tris": [lq["triangles"].get(x.name) for x in [c0] + lods],
                               "lod_qa_fails": [(c["name"], c["object"], str(c["detail"])[:120]) for c in lod_hard],
                               "screen_sizes": r.get("lod_screen_sizes"), "warnings": r["warnings"]}
                for ob in list(tmpc.objects):
                    bpy.data.objects.remove(ob, do_unlink=True)
                bpy.data.collections.remove(tmpc)
            kit.hide_viewport = True
            (OW / "export_report.json").write_text(json.dumps(exp, indent=1, default=str), encoding="utf-8")
            print(f"exported {len(exp)} FBX to {EXPORT_DIR}", flush=True)
    if "--no-context" not in ARGS:
        compose_checks(kit, asm, LO)
    rep = {"calm_boards": calm, "pieces": {p.name: {"class": p.cls, "tris": stats[p.name]["tris"], "nanite": p.nanite,
                                                    "ucx": len(p.hulls), "bad_faces": stats[p.name]["bad_faces"]}
                                           for p in P},
           "tris_total_unique": sum(stats[p.name]["tris"] for p in P),
           "tris_placed": sum(stats[it["piece"]]["tris"] for it in inst),
           "instances": len(inst), "seconds": round(time.time() - t0, 1), "quick": QUICK}
    (OW / "outbuildings_report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    BLEND.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    print("saved", BLEND, "seconds", rep["seconds"], flush=True)


def compose_checks(kit, asm, LO):
    """Load the showcase compound (read-only) around our buildings: its Kit pieces + UCX and its Assembly instances,
    minus the grey-box storehouse / residence; write layout_outbuildings_checks.json (layout_showcase.json with the swap)."""
    if not SHOWCASE_BLEND.exists():
        print("no showcase blend; checks skipped")
        return

    def base_of(name):
        b = name.split("__")[0].split(".")[0]
        if b.startswith("UCX_"):
            b = b[4:].rsplit("_", 1)[0]
            if b.endswith("_LOD0"):
                b = b[:-5]
        return b

    with bpy.data.libraries.load(str(SHOWCASE_BLEND), link=False) as (src, dst):
        dst.objects = [n for n in src.objects if base_of(n) not in REPLACED and not base_of(n).startswith("SM_DKO_")]
    keep = 0
    for o in dst.objects:
        if o is None:
            continue
        if "__" in o.name:
            asm.objects.link(o)
            keep += 1
        elif o.type in ("MESH", "EMPTY"):
            kit.objects.link(o)
    L = json.loads(SHOWCASE_LAYOUT.read_text(encoding="utf-8"))
    L["pieces"] = {k: v for k, v in L["pieces"].items() if k not in REPLACED and not k.startswith("SM_DKO_")}
    for k, v in LO["pieces"].items():
        L["pieces"][k] = {"class": v["class"], "kit": KIT, "nanite": v["nanite"], "ucx": v["ucx"]}
    L["instances"] = [i for i in L["instances"] if i["piece"] not in REPLACED and not i["piece"].startswith("SM_DKO_")] \
        + LO["instances"]
    moved = []
    for mv in PROPOSED_MOVES:
        for it in L["instances"]:
            if it["piece"] == mv["piece"] and all(abs(u - v) < 0.02 for u, v in zip(it["loc"], mv["from"])):
                it["loc"] = list(mv["to"])
                it["rot_z"] = mv["rot_z"]
                it["rot_xyz_deg"] = [0.0, 0.0, mv["rot_z"]]
                it["note"] = (it.get("note", "") + " | OUTBUILDINGS r4 PROPOSAL: " + mv["why"]).strip(" |")
                moved.append(mv["piece"])
        for o in asm.objects:
            if o.name.split("__")[0] == mv["piece"] and                     all(abs(u - v) < 0.02 for u, v in zip(o.location, mv["from"])):   # (loaded objects: no
                #                                                  evaluated matrix_world yet; the location is stored)
                o.location = mv["to"]
                o.rotation_euler = (0.0, 0.0, math.radians(mv["rot_z"]))
    L["outbuildings_proposed_moves"] = PROPOSED_MOVES
    print("proposed moves applied to the check context:", moved, flush=True)
    L["stage"] = "outbuildings checks: the showcase with the storehouse + residence (SM_DKO_*) in place of the grey-box"
    L["outbuildings"] = LO["numbers"]
    (OW / "layout_outbuildings_checks.json").write_text(json.dumps(L, indent=1), encoding="utf-8")
    print("context: assembly instances kept", keep, "layout_outbuildings_checks.json written", flush=True)


if __name__ == "__main__":
    main()
