"""KIT 1: perimeter wall + main gatehouse for the dojo courtyard arena, built on the grey-box layout.

Specs: WorkFiles/world/DOJO_ARENA_SPEC.md (heights, climbs, collision classes), WorkFiles/world/STYLE_GUIDE.md (palette,
texel density, IP). Look: References/Dojo/dojo_wall_ref.png and dojo_gatehouse_ref.png (AI-generated modelling reference,
REFERENCE_LOG.md). Decisions and deviations: WorkFiles/dojo/build/BUILD_NOTES.md, sections "KIT 1" and "KIT 1 fix f1".

WALL KIT (modular, every module's pivot on the INNER face at its own base; the wall runs along local +X, the inner face
is local y = 0, the thickness goes to local -Y; the cross-section is symmetric, so a module turned 180 deg fits too):
  SM_DK_WallFooting_{1,2,4}m      0.65 m granite footing (about a third of the wall, as the sheet): a row of squared
                                  capstones over three courses of rough polygonal field stone, moss in the joints (R)
  SM_DK_WallFooting_End / _Corner the same, wrapping the exposed end / corner in quoins
  SM_DK_WallBody_{1,2,4}m_T{200,250,300}   earthen plaster from +0.65 to the cap (tops 2.0 / 2.5 / 3.0 m); grime in
                                  vertex colour G; plaster is mapped in world space (height-independent)
  SM_DK_WallCap_{1,2,4}m          kawara cap (the shared tile system), 8 deg, widened for the 1.0 m wall; the collision
                                  is ONE flat box whose top is the wall top; the ridge roll stands 6.5 cm above it so
                                  every tile at the wall faces stays within 0.15 m of the walk plane (spec 4.1, f1)
  SM_DK_WallCap_End               1 m cap with the gabled end (tie beam, bargeboards, verge rolls, ridge-end discs)
  SM_DK_WallCap_Corner            1 x 1 m corner cap: mitred ridge + round finial, hip roll outside, valley roll inside
  SM_DK_Wall_StepPier             1 m stepped wall section, flat walkable top +3.25 (route 2 landing), gabled both ends
  SM_DK_Wall_GateReturn_W / _E    f1: beside the gatehouse the wall turns north (a corner module) and returns 2 m at
                                  +2.0 to a 1 x 1 m stepped block at the courtyard eave corner (flat top +3.25, route 6
                                  landing); a stepped join (+3.0) under the verge closes the wall line to the wall post
  SM_DK_Wall_FramePier            f1: the wall sheet's freestanding timber-framed pier (slab plinth, stone base, posts
                                  and beams, exposed earthen panels, gabled cap); a terminal for the BR wall openings
GATEHOUSE (pivot at the gate centre on the inner wall face, world (22, 0, 0)):
  SM_DK_Gate_Frame (door posts, wall posts, front + rear corner posts on plinth blocks, bracket clusters, layered eave
  beams, tie beams, gables, lintel, plank side panels), SM_DK_Gate_Roof (plain gable / kirizuma 8 x 5 m, eave +3.25,
  slope planes meeting at +4.416, verge bargeboards, verge rolls, plain round stacked ridge-end tiles),
  SM_DK_Gate_Leaf_L / _R (pivot on the hinge axis), SM_DK_Gate_Lamp (x4), SM_DK_Gate_Paving

Run: blender -b --factory-startup --python Scripts/dojo/build_kit1.py -- [--no-export] [--no-lods]
Out: Assets/Dojo/DojoKit1.blend, Exports/DojoKit/Kit1/SM_DK_*.fbx, WorkFiles/dojo/build/layout.json (kit 1 in place of
the grey-box wall and gate), WorkFiles/dojo/build/kit1/{qa_report,export_report,kit1_report}.json
Re-running build_dojo_greybox.py overwrites layout.json: re-run this script after it.
"""
import json
import math
import random
import sys
import time
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector, noise

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pipeline.export_fbx import export_fbx  # noqa: E402
from pipeline.qa_check import qa_check  # noqa: E402
from pipeline.lock import assert_owner  # noqa: E402
from pipeline.helpers import decimate_lods, make_lod_group  # noqa: E402
import kit1_geo as G  # noqa: E402
from kit1_geo import Geo, Slope  # noqa: E402

WORK = ROOT / "WorkFiles" / "dojo" / "build"
K1 = WORK / "kit1"
TEX = ROOT / "Exports" / "DojoKit" / "Kit1" / "Textures"
EXPORT_DIR = ROOT / "Exports" / "DojoKit" / "Kit1"
GREY_BLEND = ROOT / "Assets" / "Dojo" / "DojoGreybox.blend"
BLEND = ROOT / "Assets" / "Dojo" / "DojoKit1.blend"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

# ------------------------------------------------------------------------------------------------ numbers
WALL_T = 1.0
FOOT_H = 0.60                    # f2: 0.65 -> 0.60 (the sheet's footing is about 0.53 of a 1.9 m wall)
CAPSTONE_H = 0.19                # the squared block course on top of the footing
PROUD = 0.015                    # f2: rubble rims stand 1.5 cm proud of the plaster plane, their cushions 4-6 cm
CAP_OVER = 0.20                  # cap eave beyond the wall face (sheet: about 0.15-0.2)
CAP_TH = math.radians(22.0)      # f2: 8 -> 22 deg (the judge: the cap read as a thin strip; the sheet's is 30-35)
CAP_BASE = 0.04                  # tile base plane above the body top at the eave line
CAP_COURSES = 4                  # f2: four courses per slope (the sheet shows 4-5 in the front view)
RIDGE_HW = 0.15                  # tile field stops this far from the ridge line (under the noshi)
NOSHI_BED = 0.030                # ridge bed above the tile base at the ridge
NOSHI_N = 3                      # f2: three noshi layers (was two)
NOSHI_H = 0.030
NOSHI_W = [0.36, 0.32, 0.28]
KAN_GAP = 0.012                  # noshi top -> ridge roll axis
KAN_R = 0.052                    # ridge roll radius
CAP_SINK = 0.040                 # the ridge roll's top stands this far above the flat walk plane (the wall top)
TOPS = {"T200": 2.0, "T250": 2.5, "T300": 3.0}
GATE_EAVE, GATE_RIDGE = 3.25, 4.4
PITCH = math.radians(25.0)
PIER_TOP = 3.25
GC = Vector((22.0, 0.0, 0.0))    # gatehouse pivot (world)

T_, IR, GR, TL, EP, MO, LG = ("M_DK_Timber", "M_DK_Iron", "M_DK_Granite", "M_DK_RoofTile", "M_DK_EarthPlaster",
                              "M_DK_Mortar", "M_DK_LampGlow")
EC = "M_DK_EarthCore"            # the frame piers' exposed straw-earth panel (f2: its own texture set, no tint)
UL = "M_DK_Underlay"             # f2: dark grey underlay under the gate tiles (was timber sarking: brown in the gaps)
# name: (texture set, tile m, params). world=True: Blender review material maps it in world space (UE: world-aligned)
MATERIALS = {
    EP: ("EarthPlaster", 4.0, {"world": True, "grime": 0.75, "grime_color": "#5A4632"}),
    EC: ("EarthCore", 4.0, {"world": True, "grime": 0.45}),
    GR: ("Granite", 4.0, {"moss": True, "grime": 0.45}),
    TL: ("RoofTile", 4.0, {"crest": True, "grime": 0.55, "grime_color": "#4B4A3E"}),
    T_: ("Timber", 4.0, {"grime": 0.6, "grime_color": "#3C3530"}),
    IR: ("Iron", 4.0, {}),
    MO: (None, 4.0, {"color": "#6E675C", "rough": 0.95}),     # f2: lighter joints (flat colours keep the UV scale)
    UL: (None, 4.0, {"color": "#33312E", "rough": 0.95}),
    LG: (None, 4.0, {"color": "#FFCE8A", "emit": 26.0, "emit_color": "#FF9A42"}),   # f2: warmer amber (about 2400 K)
}


def srgb_to_lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hexcol(h):
    return tuple(srgb_to_lin(int(h[i:i + 2], 16) / 255.0) for i in (1, 3, 5)) + (1.0,)


def clamp01(x):
    return max(0.0, min(1.0, x))


# ------------------------------------------------------------------------------------------------ vertex colour rules
def moss_rule(z_top=0.42, grime=0.0):
    def f(co):
        n = noise.noise(co * 3.1) * 0.5 + 0.5
        m = clamp01((z_top - co.z) / z_top) ** 1.3 * (0.30 + 0.70 * n)
        return (m, grime, 1.0)
    return f


def stone_moss(z_top=FOOT_H):
    """Per-vertex moss for the field stones: strongest in the joints and low down, a touch on the upper faces."""
    def f(v, joint, upf):
        nz = noise.noise(v * 3.1) * 0.5 + 0.5
        low = clamp01((z_top - v.z) / z_top) ** 1.1
        streak = clamp01((0.22 - v.z) / 0.22) * (0.5 + 0.5 * (noise.noise(Vector((v.x * 6.0, v.y * 6.0, 0.3))) * 0.5 + 0.5))
        return clamp01((0.18 + 0.82 * joint) * (0.30 + 0.70 * low) * (0.30 + 0.70 * nz) + 0.35 * upf * nz
                       + 0.55 * streak)
    return f


def grime_rule(z_lo, z_hi, top=0.50, bottom=0.35):
    """f2: mottled water staining on the plaster (G): darkest under the cap's drip line, fading down over `top`, and a
    splash band above the footing; broken up by low-frequency noise (the material adds the vertical streaks)."""
    def f(co):
        nz = noise.noise(Vector((co.x * 1.7, co.y * 1.7, co.z * 0.5))) * 0.5 + 0.5
        g = max(0.90 * clamp01(1 - (z_hi - co.z) / top) ** 0.8, 0.65 * clamp01(1 - (co.z - z_lo) / bottom))
        return (0.0, clamp01(g * (0.50 + 0.70 * nz)), 1.0)
    return f


# ------------------------------------------------------------------------------------------------ piece container
class Piece:
    def __init__(self, name, cls, folder, note):
        self.name, self.cls, self.folder, self.note = name, cls, folder, note
        self.g = Geo()
        self.hulls = []          # point lists (piece local)
        self.nanite = False
        self.extra = {}

    def hull_box(self, x0, x1, y0, y1, z0, z1):
        self.hulls.append([(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)])
        return self

    def hull_pts(self, pts):
        self.hulls.append([tuple(p) for p in pts])
        return self


def lattice_surface(g, xs, ys, zs, mat, vc=None, frame=None):
    """The closed surface of a box subdivided at the given coordinates (welded, outward quads)."""
    grid, verts, faces = {}, [], []

    def vid(i, j, k):
        if (i, j, k) not in grid:
            grid[(i, j, k)] = len(verts)
            verts.append((xs[i], ys[j], zs[k]))
        return grid[(i, j, k)]

    nx, ny, nz = len(xs) - 1, len(ys) - 1, len(zs) - 1
    for (fixed, val, a1, n1, a2, n2, flip) in ((0, 0, 1, ny, 2, nz, True), (0, nx, 1, ny, 2, nz, False),
                                               (1, 0, 0, nx, 2, nz, False), (1, ny, 0, nx, 2, nz, True),
                                               (2, 0, 0, nx, 1, ny, True), (2, nz, 0, nx, 1, ny, False)):
        for p in range(n1):
            for q in range(n2):
                quad = []
                for (dp, dq) in ((0, 0), (1, 0), (1, 1), (0, 1)):
                    ijk = [0, 0, 0]
                    ijk[fixed] = val
                    ijk[a1] = p + dp
                    ijk[a2] = q + dq
                    quad.append(vid(*ijk))
                faces.append(tuple(reversed(quad)) if flip else tuple(quad))
    g.add(verts, faces, mat, frame, vc)
    return g


# ------------------------------------------------------------------------------------------------ footing stones (f2)
def stone_face(g, origin, t, n, length, seed, moss=True):
    """Lay the stones of one exposed footing face (origin at a = 0 on the face plane at z = 0, t = along, n = outward).
    f2 (the sheet's footing): one course of squared blocks with slightly cushioned faces (FOOT_H - CAPSTONE_H ..
    FOOT_H) over two courses of rounded, bulging, pillow-faced rubble of varied size (a jittered Voronoi packing whose
    outlines are rounded), set in light, shallow mortar joints, moss low down and in the joints."""
    rng = random.Random(seed * 7 + 3)
    mfn = stone_moss() if moss else None
    zc0 = FOOT_H - CAPSTONE_H
    gap = 0.016
    # squared blocks
    a = 0.0
    widths = []
    while a < length - 1e-6:
        w = rng.uniform(0.28, 0.56)
        widths.append(w)
        a += w
    k = length / sum(widths)
    a = 0.0
    for i, w in enumerate(widths):
        w *= k
        j = [rng.uniform(-0.006, 0.006) for _ in range(4)]
        poly = [(a + gap / 2 + j[0], zc0 + gap / 2), (a + w - gap / 2 + j[1], zc0 + gap / 2),
                (a + w - gap / 2 + j[2], FOOT_H - 0.006), (a + gap / 2 + j[3], FOOT_H - 0.006)]
        G.pillow_stone(g, poly, origin, t, n, 0.13, PROUD + 0.010 + rng.uniform(0.0, 0.008), rng.uniform(0.010, 0.018),
                       seed * 131 + i, GR, rough=0.006, edge=0.012, moss=mfn, rounds=2, keep=0.10,
                       rings=(0.97, 0.90, 0.72, 0.42))
        a += w
    # rubble: two courses of rounded field stones, widths 0.17-0.40 m (the sheet's mix of small and large)
    seeds = []
    rows = 2
    for r in range(rows):
        z = (r + 0.5) * zc0 / rows + rng.uniform(-0.015, 0.015)
        x = rng.uniform(-0.08, 0.06) + (0.11 if r % 2 else 0.0)
        while x < length + 0.2:
            seeds.append((x + rng.uniform(-0.04, 0.04), z + rng.uniform(-0.035, 0.035)))
            x += rng.uniform(0.17, 0.40)
    for i, cell in enumerate(G.voronoi_cells(seeds, 0.0, length, 0.0, zc0 - gap / 2)):
        inner = G.inset_convex(cell, gap / 2 + rng.uniform(0.0, 0.004))
        if inner is None or abs(G.poly_area(inner)) < 0.004:
            continue
        w_ = max(p_[0] for p_ in inner) - min(p_[0] for p_ in inner)
        h_ = max(p_[1] for p_ in inner) - min(p_[1] for p_ in inner)
        bulge = max(0.028, min(0.060, 0.26 * min(w_, h_))) * rng.uniform(0.85, 1.15)
        G.pillow_stone(g, inner, origin, t, n, 0.15, PROUD + rng.uniform(-0.006, 0.008), bulge, seed * 997 + i, GR,
                       rough=0.010, edge=0.022, moss=mfn, rounds=2, keep=0.25)
    return g


def quoin(g, corner, n1, n2, seed, q=0.36, gap=0.016):
    """Corner stones (squared, rough-faced, cushioned): `corner` = the corner point of the two face planes at z = 0;
    n1 / n2 = the two outward normals. The long side alternates between the courses (a real quoin bond)."""
    n1, n2, up = Vector(n1).normalized(), Vector(n2).normalized(), Vector((0, 0, 1))
    vc = moss_rule(FOOT_H)
    zc0 = FOOT_H - CAPSTONE_H
    courses = ((zc0, FOOT_H), (zc0 / 2, zc0), (0.0, zc0 / 2))
    pr = PROUD + 0.012
    for i, (z0, z1) in enumerate(courses):
        h = (q + pr) / 2 - gap / 2
        c = Vector(corner) + n1 * (pr - (q + pr) / 2) + n2 * (pr - (q + pr) / 2) + up * ((z0 + z1) / 2)
        G.rounded_stone(g, c, (-n2, -n1, up), (h * (1.15 if i % 2 else 0.9), h, (z1 - z0) / 2 - gap / 2),
                        0.22 * min(h, (z1 - z0) / 2), seed * 31 + i, GR, bulge=0.018, rough=0.010, n=(5, 5, 4), vc=vc)
    return g


def footing(x0, x1, y0, y1, faces, quoins, seed, z_top=FOOT_H):
    """faces: subset of '-y', '+y', '-x', '+x' that show stones; quoins: corners like ('-x', '-y')."""
    g = Geo()
    q = 0.36
    # the core the stones are set into (dark mortar shows in the joints)
    ins = 0.004        # f2: the mortar core stands almost flush with the face plane (shallow, light joints)
    G.box(g, x0 + (ins if "-x" in faces else 0), x1 - (ins if "+x" in faces else 0),
          y0 + (ins if "-y" in faces else 0), y1 - (ins if "+y" in faces else 0), 0.0, z_top - 0.002, MO)

    def span(lo, hi, lo_key, hi_key, other):
        a = lo + (q if (lo_key, other) in quoins or (other, lo_key) in quoins else 0.0)
        b = hi - (q if (hi_key, other) in quoins or (other, hi_key) in quoins else 0.0)
        return a, b

    if "-y" in faces:
        a, b = span(x0, x1, "-x", "+x", "-y")
        stone_face(g, (a, y0, 0), (1, 0, 0), (0, -1, 0), b - a, seed + 1)
    if "+y" in faces:
        a, b = span(x0, x1, "-x", "+x", "+y")
        stone_face(g, (b, y1, 0), (-1, 0, 0), (0, 1, 0), b - a, seed + 2)
    if "-x" in faces:
        a, b = span(y0, y1, "-y", "+y", "-x")
        stone_face(g, (x0, b, 0), (0, -1, 0), (-1, 0, 0), b - a, seed + 3)
    if "+x" in faces:
        a, b = span(y0, y1, "-y", "+y", "+x")
        stone_face(g, (x1, a, 0), (0, 1, 0), (1, 0, 0), b - a, seed + 4)
    for i, (kx, ky) in enumerate(quoins):
        cx = x0 if kx == "-x" else x1
        cy = y0 if ky == "-y" else y1
        n1 = Vector((0, -1, 0)) if ky == "-y" else Vector((0, 1, 0))
        n2 = Vector((-1, 0, 0)) if kx == "-x" else Vector((1, 0, 0))
        quoin(g, (cx, cy, 0), n1, n2, seed + 10 + i)
    return g


# ------------------------------------------------------------------------------------------------ cap
def cap_dims(thick=WALL_T, over=CAP_OVER):
    half = thick / 2 + over
    run = half - RIDGE_HW
    tn = math.tan(CAP_TH)
    base_ridge = CAP_BASE + run * tn
    noshi0 = base_ridge + NOSHI_BED
    kan_c = noshi0 + 2 * NOSHI_H + KAN_GAP
    top = kan_c + KAN_R
    return {"half": half, "run": run, "s_len": run / math.cos(CAP_TH), "base_ridge": base_ridge, "noshi0": noshi0,
            "kan_c": kan_c, "visual_top": top, "H": top - CAP_SINK, "apex": CAP_BASE + half * tn}


CD = cap_dims()
CAP_H = CD["H"]                  # the cap's collision top above its pivot (= the wall top)


def cap_geo(xa, xb, thick=WALL_T, over=CAP_OVER, gable_lo=False, gable_hi=False, ledger=True, close_hi=False):
    """A straight cap from x = xa to xb over a wall y in [-thick, 0]. gable_*: close that end with a verge (the
    geometry then runs `over` past the end)."""
    d = cap_dims(thick, over)
    g = Geo()
    yc = -thick / 2
    x0 = xa - (over if gable_lo else 0.0)
    x1 = xb + (over if gable_hi else 0.0)
    L = x1 - x0
    tn, cs = math.tan(CAP_TH), math.cos(CAP_TH)
    s_len = d["s_len"]
    C = s_len / 3.0                                   # f1: three courses per slope (was two)
    slA = Slope((x0, yc - d["half"], CAP_BASE), (1, 0, 0), (0, cs, math.sin(CAP_TH)))
    slB = Slope((x1, yc + d["half"], CAP_BASE), (-1, 0, 0), (0, -cs, math.sin(CAP_TH)))
    phA = (xa - x0) % G.P
    phB = (x1 - xa) % G.P
    for sl, ph, (lo_g, hi_g) in ((slA, phA, (gable_lo, gable_hi)), (slB, phB, (gable_hi, gable_lo))):
        verge_u = []
        if lo_g:
            verge_u.append(0.045)
        if hi_g:
            verge_u.append(L - 0.045)
        G.tile_field(g, sl, 0.0, L, 0.0, s_len, C, TL, eave=True, phase=ph,
                     roll_margin=0.06 if (lo_g or hi_g) else 0.0)
        for uv in verge_u:
            G.roll_run(g, sl, uv, 0.0, s_len, C, TL, eave=True)
        ob_s = over / cs
        G.obox(g, sl.at(L / 2, ob_s / 2, -0.014), sl.U, sl.S, sl.N, L / 2, ob_s / 2, 0.012, T_)
    for side in (-1, 1):
        ye = yc + side * d["half"]
        G.box(g, x0, x1, min(ye, ye - side * 0.028), max(ye, ye - side * 0.028), CAP_BASE - 0.07, CAP_BASE - 0.004, T_,
              grain="x")
        if ledger:
            yf = yc + side * thick / 2
            G.box(g, xa if not gable_lo else xa - 0.02, xb if not gable_hi else xb + 0.02,
                  min(yf, yf + side * 0.022), max(yf, yf + side * 0.022), -0.055, 0.0, T_, grain="x")
    zf = CAP_BASE + over * tn
    G.prism(g, [(xb, -thick, 0.0), (xb, 0.0, 0.0), (xb, 0.0, zf), (xb, yc, d["apex"] - 0.02), (xb, -thick, zf)],
            (1, 0, 0), xb - xa, MO)
    # f1: at a plain module end the ridge bed and the noshi run to the exact end, so neighbouring modules' ridges meet
    # with no gap (the renders showed light ticks at the module joints); gable ends keep their small inset
    ia, ib = (0.01 if gable_lo else 0.0), (0.01 if gable_hi else 0.0)
    G.box(g, x0 + ia, x1 - ib, yc - 0.14, yc + 0.14, d["base_ridge"] - 0.02, d["noshi0"], MO)
    G.noshi_stack(g, (x0 + ia / 2, yc, d["noshi0"]), (x1 - ib / 2, yc, d["noshi0"]), (0, 0, 1), [0.30, 0.26], NOSHI_H,
                  TL, seg=0.25, seed=int(1000 * (xb - xa)) + (7 if gable_lo else 0) + (3 if gable_hi else 0))
    kz = d["kan_c"]
    G.roll_line(g, (x0, yc, kz), (x1, yc, kz), (0, 0, 1), TL, r=KAN_R, seg=0.25,
                disc_start=0.062 if gable_lo else None, disc_end=0.062 if gable_hi else None)
    if close_hi:      # a plain tile end plate closing the section (the gate step pier's end under the verge)
        G.prism(g, [(xb, yc - d["half"], CAP_BASE - 0.07), (xb, yc + d["half"], CAP_BASE - 0.07),
                    (xb, yc + d["half"], CAP_BASE + 0.07), (xb, yc, d["visual_top"]), (xb, yc - d["half"], CAP_BASE + 0.07)],
                (1, 0, 0), 0.02, TL, frame=(Vector((0, 0, 1)), Vector((0, 1, 0)), Vector((1, 0, 0))))
    for (on, xe, sgn) in ((gable_lo, x0, -1), (gable_hi, x1, 1)):
        if not on:
            continue
        xin = xa if sgn < 0 else xb
        # gable board on the wall end plane
        G.prism(g, [(xin, yc - d["half"] + 0.05, CAP_BASE - 0.07), (xin, yc + d["half"] - 0.05, CAP_BASE - 0.07),
                    (xin, yc + d["half"] - 0.05, CAP_BASE), (xin, yc, d["apex"]), (xin, yc - d["half"] + 0.05, CAP_BASE)],
                (sgn, 0, 0), 0.03, EP, frame=(Vector((0, 0, 1)), Vector((0, 1, 0)), Vector((1, 0, 0))))
        # f1: the sheet's end frame: a small timber tie beam across the gable with square ends past both eaves
        xt0, xt1 = (xin, xin + sgn * 0.075)
        G.box(g, min(xt0, xt1), max(xt0, xt1), yc - d["half"] - 0.05, yc + d["half"] + 0.05, CAP_BASE - 0.13,
              CAP_BASE - 0.05, T_, grain="y")
        # bargeboards under the verge, standing proud of the gable (the sheet's end elevation)
        for sl in (slA, slB):
            u = 0.03 if (sl is slA) == (sgn < 0) else L - 0.03
            G.obox(g, sl.at(u, s_len / 2 - 0.01, -0.075), sl.S, sl.U, sl.N, s_len / 2 + 0.03, 0.028, 0.068, T_)
        # a short king post from the tie beam to the apex
        G.box(g, min(xin, xin + sgn * 0.06), max(xin, xin + sgn * 0.06), yc - 0.05, yc + 0.05, CAP_BASE - 0.05,
              d["apex"] - 0.06, T_, grain="z")
        G.box(g, xe - 0.01 if sgn > 0 else xe - 0.035, xe + 0.035 if sgn > 0 else xe + 0.01, yc - 0.13, yc + 0.13,
              d["base_ridge"] + 0.02, d["noshi0"] + 2 * NOSHI_H, TL)
        G.disc(g, (xe + sgn * 0.035, yc, d["noshi0"] + NOSHI_H), (sgn, 0, 0), (0, 0, 1), 0.056, 0.03, TL, relief=True)
        # the sheet's round ridge-end: a larger relief disc standing on the ridge roll end
        G.disc(g, (xe + sgn * 0.05, yc, d["kan_c"] + 0.035), (sgn, 0, 0), (0, 0, 1), 0.07, 0.035, TL, relief=True)
        G.lathe(g, (xe + sgn * 0.012, yc, d["kan_c"] + 0.035), (sgn, 0, 0), (0, 0, 1),
                [(0.0, 0.0), (0.0, 0.066), (0.035, 0.066), (0.035, 0.0)], TL, nseg=16)
    return g, d


def corner_cap():
    """The 1 x 1 m corner block's cap (block x in [-1, 0], y in [-1, 0]; legs leave through x = 0 and y = 0)."""
    d = CD
    leg, _ = cap_geo(-1.25, 0.0)
    leg = G.clip(leg, [((0, 0, 0), (1, -1, 0))])            # x-leg keeps x > y
    g = G.weld(Geo().extend(leg).extend(G.reflect_xy(leg)), 1e-6)   # the two cut faces meet exactly on x = y
    tn, cs = math.tan(CAP_TH), math.cos(CAP_TH)
    yc = -0.5
    top_off = G.TILE_TOP / cs

    def ztop(dy):
        return CAP_BASE + (d["half"] - dy) * tn + top_off

    a = RIDGE_HW
    # hip roll (outside) along the diagonal, relief disc at the eave corner
    p0 = Vector((yc - a, yc - a, ztop(a) + 0.01))
    p1 = Vector((yc - d["half"] + 0.03, yc - d["half"] + 0.03, ztop(d["half"] - 0.03) + 0.01))
    G.roll_line(g, p0, p1, (0.35, 0.35, 1.0), TL, r=0.055, seg=0.22, disc_end=0.07)
    # f1: valley (inside): a board under the cut roll ends plus a mitred cover roll along the valley line
    v0 = Vector((yc + a, yc + a, CAP_BASE + (d["half"] - a) * tn + 0.02))
    v1 = Vector((yc + d["half"], yc + d["half"], CAP_BASE + 0.02))
    ax = (v1 - v0).normalized()
    side = Vector((0, 0, 1)).cross(ax).normalized()
    G.obox(g, (v0 + v1) / 2, ax, side, ax.cross(side), (v1 - v0).length / 2, 0.08, 0.012, TL)
    q0 = Vector((yc + a, yc + a, ztop(a) + 0.004))
    q1 = Vector((yc + d["half"] - 0.03, yc + d["half"] - 0.03, ztop(d["half"] - 0.03) + 0.004))
    G.roll_line(g, q0, q1, (-0.35, -0.35, 1.0), TL, r=0.052, seg=0.22, disc_end=0.066)
    # f1: a round finial where the mitred ridges meet (the sheet's V view): stepped base, neck, ball
    kz = d["kan_c"]
    G.lathe(g, (yc, yc, kz - 0.04), (0, 0, 1), (1, 0, 0),
            [(0.0, 0.0), (0.0, 0.080), (0.035, 0.080), (0.045, 0.062), (0.060, 0.040), (0.070, 0.050), (0.085, 0.058),
             (0.105, 0.056), (0.125, 0.044), (0.140, 0.024), (0.146, 0.0)], TL, nseg=18)
    return g


# ------------------------------------------------------------------------------------------------ wall pieces
def body_geo(x0, x1, y0, y1, z0, z1, mat, step=0.5):
    g = Geo()
    xs = [x0 + (x1 - x0) * i / max(1, round((x1 - x0) / step)) for i in range(int(max(1, round((x1 - x0) / step))) + 1)]
    ys = [y0 + (y1 - y0) * i / max(1, round((y1 - y0) / step)) for i in range(int(max(1, round((y1 - y0) / step))) + 1)]
    zs = sorted({z0, min(z1, z0 + 0.15), min(z1, z0 + 0.35), max(z0, z1 - 0.50), max(z0, z1 - 0.25),
                 max(z0, z1 - 0.10), z1})
    lattice_surface(g, xs, ys, zs, mat, vc=grime_rule(z0, z1))
    return g


PIER_Y = (-1.2, 0.2)       # 1.4 m deep, centred on the wall (0.2 proud of both faces): rotation-safe, and a capsule
                            # can stand in line with the gate ridge (y 0) for route 6


def step_pier(name, length, gable_lo, gable_hi, note, seed):
    """A stepped wall section (the wall's own footing / plaster / cap, raised, 1.4 m deep like the grey-box pier): flat
    walkable top +3.25 over its first 1.0 m; any further length (the gate one) is tucked under the gate verge and
    blocks up to +3.74."""
    p = Piece(name, "landing", "Landings", note)
    th = PIER_Y[1] - PIER_Y[0]
    pd = cap_dims(th)
    pz = PIER_TOP - pd["H"]
    faces = ["-y", "+y"] + (["-x"] if gable_lo else []) + (["+x"] if gable_hi else [])
    quo = ([("-x", "-y"), ("-x", "+y")] if gable_lo else []) + ([("+x", "-y"), ("+x", "+y")] if gable_hi else [])
    g = footing(0, length, PIER_Y[0], PIER_Y[1], tuple(faces), tuple(quo), seed)
    g.extend(body_geo(0, length, PIER_Y[0], PIER_Y[1], FOOT_H, pz, EP, step=0.8))
    cg, _ = cap_geo(0, length, thick=th, gable_lo=gable_lo, gable_hi=gable_hi, close_hi=not gable_hi)
    g.extend(cg.transformed(Matrix.Translation((0, PIER_Y[1], pz))))
    p.g = g
    p.hull_box(0, min(1.0, length), PIER_Y[0], PIER_Y[1], 0, PIER_TOP)
    if length > 1.0:
        p.hull_box(1.0, length, PIER_Y[0], PIER_Y[1], 0, 3.74)
    p.nanite = True
    p.extra = {"body_top": round(pz, 4), "walk_top": PIER_TOP, "flat_landing_x": [0.0, min(1.0, length)]}
    return p


RET_L = 2.0                # the return wall's length (y 0 .. 2, world)
STEP_X = (-0.08, 0.92)     # the step block (piece local x; the west piece's pivot is world (17, 0)): its east end stops
                           # 8 cm short of the gate verge (world x 18.0), clear of the verge roll's end disc
STEP_Y = (2.0, 3.0)        # at the gatehouse's courtyard eave (y 2.5)
JOIN_X = (1.0, 1.55)       # the stepped join from the corner block to the gate's wall post (post face at 1.62; its
                           # proud end stones stop 2-3 cm short of the post and its plinth)
JOIN_TOP = 3.0             # its flat top, under the verge (verge underside >= 3.57 over it)


def gate_return(name, mirror, note, seed):
    """Route 6 on the plain gable (f1 direction: the grey-box way, a flat landing at the eave; the roof form is the
    sheet's). At each side of the gatehouse the wall turns the corner (a standard corner module, placed separately) and
    returns north along the outside of the gate verge at the wall height (+2.0, 2 m): the wall top leads on to a 1 x 1 m
    stepped block at the gatehouse's courtyard eave corner, flat walkable top +3.25 (the route-6 landing: a 1.25 m
    mantle from the return wall top, then a walk onto the eave). Where the wall meets the gate's wall post it steps up
    under the verge (+3.0, the sheet's side view), so no wall top is left under the verge.
    West piece: pivot world (17, 0, 0); mirror=True gives the east piece (pivot world (27, 0, 0))."""
    p = Piece(name, "landing", "Landings", note)
    zb200 = TOPS["T200"] - CAP_H
    # the return wall (built along +x in the wall frame, then turned +90 deg: local (x, y) -> (-y, x))
    r = footing(0, RET_L, -WALL_T, 0, ("-y", "+y"), (), seed)
    r.extend(body_geo(0, RET_L, -WALL_T, 0, FOOT_H, zb200, EP))
    cg, _ = cap_geo(0, RET_L, close_hi=True)
    r.extend(cg.transformed(Matrix.Translation((0, 0, zb200))))
    g = r.transformed(Matrix.Rotation(math.radians(90.0), 4, "Z"))
    # the step block (wall frame: along +x, y -1 .. 0, then moved to y 2 .. 3)
    pz = PIER_TOP - CAP_H
    s = footing(0, 1.0, -WALL_T, 0, ("-y", "+y", "-x", "+x"),
                (("-x", "-y"), ("-x", "+y"), ("+x", "-y"), ("+x", "+y")), seed + 3)
    s.extend(body_geo(0, 1.0, -WALL_T, 0, FOOT_H, pz, EP))
    cg, _ = cap_geo(0, 1.0, gable_lo=True, close_hi=True)
    s.extend(cg.transformed(Matrix.Translation((0, 0, pz))))
    g.extend(s.transformed(Matrix.Translation((STEP_X[0], STEP_Y[1], 0.0))))
    # the stepped join in the wall line (already in the wall frame)
    jz = JOIN_TOP - CAP_H
    j = footing(JOIN_X[0], JOIN_X[1], -WALL_T, 0, ("-y", "+y", "+x"), (("+x", "-y"), ("+x", "+y")), seed + 7)
    j.extend(body_geo(JOIN_X[0], JOIN_X[1], -WALL_T, 0, FOOT_H, jz, EP))
    cg, _ = cap_geo(JOIN_X[0], JOIN_X[1], gable_lo=True, close_hi=True)
    j.extend(cg.transformed(Matrix.Translation((0, 0, jz))))
    g.extend(j)
    p.hull_box(0.0, WALL_T, 0.0, RET_L, 0, TOPS["T200"])
    p.hull_box(STEP_X[0], STEP_X[1], STEP_Y[0], STEP_Y[1], 0, PIER_TOP)
    p.hull_box(JOIN_X[0], JOIN_X[1], -WALL_T, 0, 0, JOIN_TOP)
    if mirror:
        g = G.mirror_x(g)
        p.hulls = [[(-x, y, z) for (x, y, z) in h] for h in p.hulls]
    p.g = g
    p.nanite = True
    sx = (-STEP_X[1], -STEP_X[0]) if mirror else STEP_X
    p.extra = {"return_top": TOPS["T200"], "step_top": PIER_TOP, "step_x_local": [round(v, 3) for v in sx],
               "step_y": list(STEP_Y), "join_top": JOIN_TOP, "join_x_local": [round(-v if mirror else v, 3) for v in JOIN_X]}
    return p


SLAB_H = 0.08


def frame_pier():
    """The wall sheet's freestanding timber-framed pier (bottom right of dojo_wall_ref.png): a granite slab plinth, the
    squared stone base, a post-and-beam frame (corner posts, sill, head beams with square ends past the posts), an
    exposed earthen panel recessed between the timbers on all four faces, and the gabled kawara cap at the wall top.
    1.0 x 1.0 m, the wall's own frame (runs along +x, inner face y = 0, pivot at the base); a wall terminal for the BR
    openings (the wickets are solid wall in the 1v1, so it is not placed in the 1v1 layout)."""
    p = Piece("SM_DK_Wall_FramePier", "building", "Wall",
              "freestanding timber-framed pier 1 x 1 m: slab plinth, stone base, post-and-beam frame, exposed earthen "
              "panels, gabled cap (top +2.0)")
    g = Geo()
    poly = [(-0.14, -1.14), (1.14, -1.14), (1.14, 0.14), (-0.14, 0.14)]
    G.polystone(g, poly, (0, 0, SLAB_H - 0.004), (1, 0, 0), (0, 0, 1), 0.14, 0.0, 211, GR, chamfer=0.018, bulge=0.003,
                rough=0.004, step=0.14,
                moss=lambda v, j, u: clamp01(0.10 + 0.5 * (noise.noise(v * 4.0) * 0.5 + 0.5) * (1.0 - u)), grime=0.5)
    base = footing(0, 1, -WALL_T, 0, ("-y", "+y", "-x", "+x"),
                   (("-x", "-y"), ("-x", "+y"), ("+x", "-y"), ("+x", "+y")), 223)
    g.extend(base.transformed(Matrix.Translation((0, 0, SLAB_H))))
    z0 = SLAB_H + FOOT_H
    zc = TOPS["T200"] - CAP_H                   # the cap sits where the wall's T200 cap sits
    zh1 = zc - 0.055                            # head beam top (under the cap's ledgers)
    zh0 = zh1 - 0.17
    ps = 0.15
    # earthen core (recessed 3 cm behind the timbers on every face)
    rec = 0.03
    lattice_surface(g, [rec, 0.5, 1 - rec], [-WALL_T + rec, -0.5, -rec], [z0 + 0.10, (z0 + zh0) / 2, zh0], EC,
                    vc=lambda co: (0.0, 0.25 + 0.20 * (noise.noise(co * 5.0) * 0.5 + 0.5), 1.0))
    # corner posts
    for (xa, xb) in ((0.0, ps), (1 - ps, 1.0)):
        for (ya, yb) in ((-WALL_T, -WALL_T + ps), (-ps, 0.0)):
            G.box(g, xa, xb, ya, yb, z0, zh1, T_, grain="z")
    # sill beams on the base (all four sides), head beams with square ends past the posts
    G.box(g, 0.0, 1.0, -WALL_T, -WALL_T + 0.12, z0, z0 + 0.10, T_, grain="x")
    G.box(g, 0.0, 1.0, -0.12, 0.0, z0, z0 + 0.10, T_, grain="x")
    G.box(g, 0.0, 0.12, -WALL_T + ps, -ps, z0, z0 + 0.10, T_, grain="y")
    G.box(g, 1 - 0.12, 1.0, -WALL_T + ps, -ps, z0, z0 + 0.10, T_, grain="y")
    for (ya, yb) in ((-WALL_T - 0.012, -WALL_T + 0.13), (-0.13, 0.012)):
        G.box(g, -0.09, 1.09, ya, yb, zh0, zh1, T_, grain="x")
    for (xa, xb) in ((-0.012, 0.13), (0.87, 1.012)):
        G.box(g, xa, xb, -WALL_T - 0.09, 0.09, zh0 + 0.02, zh1 - 0.02, T_, grain="y")
    # a mid rail on each face (the sheet's panel is split low by a rail over the stone base)
    for (ya, yb) in ((-WALL_T, -WALL_T + 0.08), (-0.08, 0.0)):
        G.box(g, ps, 1 - ps, ya, yb, zh0 - 0.34, zh0 - 0.26, T_, grain="x")
    for (xa, xb) in ((0.0, 0.08), (0.92, 1.0)):
        G.box(g, xa, xb, -WALL_T + ps, -ps, zh0 - 0.34, zh0 - 0.26, T_, grain="y")
    # a plaster band between the head beam and the cap's ledgers is covered by the ledgers; the cap, gabled both ends
    cg, _ = cap_geo(0, 1, gable_lo=True, gable_hi=True)
    g.extend(cg.transformed(Matrix.Translation((0, 0, zc))))
    p.g = g
    p.hull_box(-0.14, 1.14, -1.14, 0.14, 0, SLAB_H)
    p.hull_box(0, 1, -WALL_T, 0, 0, TOPS["T200"])
    p.nanite = True
    p.extra = {"top": TOPS["T200"], "slab_h": SLAB_H, "base_top": round(z0, 3), "cap_z": round(zc, 4)}
    return p


def wall_pieces():
    P = []
    zb = {k: round(v - CAP_H, 4) for k, v in TOPS.items()}
    seeds = {1: 11, 2: 23, 4: 47}
    for L in (1, 2, 4):
        p = Piece(f"SM_DK_WallFooting_{L}m", "building", "Wall", f"granite footing {L} m, {FOOT_H} m tall")
        p.g = footing(0, L, -WALL_T, 0, ("-y", "+y"), (), seeds[L])
        p.hull_box(0, L, -WALL_T, 0, 0, FOOT_H)
        p.nanite = True
        P.append(p)
        for key, top in TOPS.items():
            b = Piece(f"SM_DK_WallBody_{L}m_{key}", "building", "Wall",
                      f"earthen plaster body {L} m, +{FOOT_H} -> {zb[key]:.3f} (wall top {top})")
            b.g = body_geo(0, L, -WALL_T, 0, 0.0, zb[key] - FOOT_H, EP)
            b.hull_box(0, L, -WALL_T, 0, 0, zb[key] - FOOT_H)
            b.extra = {"pivot_z": FOOT_H, "top": top}
            P.append(b)
        c = Piece(f"SM_DK_WallCap_{L}m", "building", "Wall", f"kawara wall cap {L} m, flat walkable collision")
        c.g, _ = cap_geo(0, L)
        c.hull_box(0, L, -WALL_T, 0, 0, CAP_H)
        c.nanite = True
        P.append(c)
    e = Piece("SM_DK_WallFooting_End", "building", "Wall", "granite footing 1 m wrapping the +X end in stone")
    e.g = footing(0, 1, -WALL_T, 0, ("-y", "+y", "+x"), (("+x", "-y"), ("+x", "+y")), 71)
    e.hull_box(0, 1, -WALL_T, 0, 0, FOOT_H)
    e.nanite = True
    P.append(e)
    ec = Piece("SM_DK_WallCap_End", "building", "Wall", "1 m wall cap with the gabled end at +X")
    ec.g, _ = cap_geo(0, 1, gable_hi=True)
    ec.hull_box(0, 1, -WALL_T, 0, 0, CAP_H)
    ec.nanite = True
    P.append(ec)
    cf = Piece("SM_DK_WallFooting_Corner", "building", "Wall", "1 x 1 m corner footing, quoin at the outer corner")
    cf.g = footing(-1, 0, -1, 0, ("-x", "-y"), (("-x", "-y"),), 83)
    cf.hull_box(-1, 0, -1, 0, 0, FOOT_H)
    cf.nanite = True
    P.append(cf)
    cc = Piece("SM_DK_WallCap_Corner", "building", "Wall", "1 x 1 m corner cap: mitred ridge + finial, hip out, valley in")
    cc.g = corner_cap()
    cc.hull_box(-1, 0, -1, 0, 0, CAP_H)
    cc.nanite = True
    P.append(cc)
    P.append(step_pier("SM_DK_Wall_StepPier", 1.0, True, True,
                       "stepped wall section 1 m, flat walkable top +3.25 (route 2 landing), gabled both ends", 97))
    for side, mir, seed in (("W", False, 113), ("E", True, 127)):
        P.append(gate_return(f"SM_DK_Wall_GateReturn_{side}", mir,
                             f"gate return ({side}): the wall returning 2 m north beside the gatehouse (+2.0), a 1 x 1 m "
                             "stepped block at the courtyard eave corner (flat top +3.25: route 6 landing, 1.25 mantle "
                             "from the wall top, walk onto the eave), a stepped join (+3.0) under the verge to the gate's "
                             "wall post", seed))
    P.append(frame_pier())
    return P, zb


# ------------------------------------------------------------------------------------------------ gatehouse numbers
TN = math.tan(PITCH)
CS = math.cos(PITCH)
BASE_OFF = G.TILE_TOP / CS          # vertical offset collision plane -> tile base plane
GX, GY = 4.0, 2.5                   # roof half sizes (8 x 5 m, spec)
GP = 3.2                            # gable plane / corner and wall posts (x)
PY = 1.75                           # front / rear post lines (y)
HINGE_X, HINGE_Y, LEAF_Z = 2.24, -0.66, 0.11
LEAF_W, LEAF_H, LEAF_TT = 2.237, 3.385, 0.24     # leaf width, height, total thickness incl. hardware
RAFT_STUB = (1.40, 2.36)            # courtyard-side rafters here stop at the rear keta (the leaves' swing, measured)
UNDER = 0.1225 + 0.004 + 0.025 + 0.10   # collision plane -> rafter underside (tiles, sarking, rafter)


def zcol_s(y):
    """Collision (tile top) height of the S / N slopes at |y|."""
    return GATE_EAVE + (GY - abs(y)) * TN


ZR = zcol_s(0.0)                    # the slope planes meet here (4.4158)


def roof_under(y):
    """Rafter underside at |y| (the lowest roof timber over a point)."""
    return zcol_s(y) - UNDER


def gate_roof():
    p = Piece("SM_DK_Gate_Roof", "roof", "Gatehouse",
              "kirizuma (plain gable) roof 8 x 5 m: eave +3.25 front and back, slope planes meet at +4.416, verge "
              "bargeboards and rolls, plain round stacked ridge-end tiles")
    g = Geo()
    s_ridge = (GY - 0.19) / CS
    C = s_ridge / 9.0                 # f1: nine courses per slope
    zb0 = GATE_EAVE - BASE_OFF
    sn = math.sin(PITCH)
    rafter_x = [s * (0.225 + 0.45 * k) for k in range(9) for s in (-1, 1)]
    rafter_x = [x for x in rafter_x if abs(x) < GX - 0.1]
    for sgn in (-1, 1):
        if sgn < 0:
            sl = Slope((-GX, -GY, zb0), (1, 0, 0), (0, CS, sn))
        else:
            sl = Slope((GX, GY, zb0), (-1, 0, 0), (0, -CS, sn))
        G.tile_field(g, sl, 0.0, 2 * GX, 0.0, s_ridge, C, TL, eave=True, phase=0.0, roll_margin=0.10)
        # verge: a roll along each verge edge (relief disc at the eave corner) and the edge tiles hanging over the
        # bargeboard
        for u in (0.058, 2 * GX - 0.058):
            G.roll_run(g, sl, u, 0.0, s_ridge + 0.05, C, TL, eave=True, r=0.060, disc_r=0.10)
            uu = 0.004 if u < GX else 2 * GX - 0.004
            a = sl.at(uu, 0.0, 0.0)
            b = sl.at(uu, s_ridge + 0.08, 0.0)
            ax = (b - a).normalized()
            G.obox(g, (a + b) / 2 - sl.N * 0.035, ax, sl.U, sl.N, (b - a).length / 2, 0.008, 0.045, TL)
        zu = lambda y: zcol_s(y) - BASE_OFF - 0.004   # noqa: E731
        # sarking (timber underside)
        poly = [(-GX + 0.02, sgn * GY, zu(GY)), (GX - 0.02, sgn * GY, zu(GY)), (GX - 0.02, 0.0, zu(0)),
                (-GX + 0.02, 0.0, zu(0))]
        if sgn > 0:
            poly = list(reversed(poly))
        G.prism(g, poly, sl.N, 0.025, T_, frame=(sl.S, sl.U, sl.N))
        # kayaoi (thin fascia) at the eave over the rafter tails
        ye0, ye1 = sgn * (GY - 0.07), sgn * (GY - 0.015)
        G.box(g, -GX + 0.02, GX - 0.02, min(ye0, ye1), max(ye0, ye1), zb0 - 0.055, zb0 - 0.006, T_, grain="x")
        # rafters with square tails showing under the kayaoi
        for x in rafter_x:
            # over the leaves' swing (courtyard side) the rafters are tail stubs resting on the rear keta: a full
            # rafter's underside drops below the leaf top (+3.495) beyond y +1.435
            stub = sgn > 0 and RAFT_STUB[0] <= abs(x) <= RAFT_STUB[1]
            ya, yb = sgn * (GY - 0.05), sgn * (1.64 if stub else 0.12)
            a = Vector((x, ya, zu(GY - 0.05) - 0.025 - 0.05))
            b = Vector((x, yb, zu(abs(yb)) - 0.025 - 0.05))      # f1: the stub ends on the slope (not at ridge height)
            ax = (b - a).normalized()
            G.obox(g, (a + b) / 2, ax, (1, 0, 0), ax.cross(Vector((1, 0, 0))), (b - a).length / 2, 0.045, 0.05, T_)
    # bargeboards (hafu) under the verges, a hanging board (gegyo) at each apex
    for sx in (-1, 1):
        xb = sx * (GX - 0.035)
        for sy in (-1, 1):
            a = Vector((xb, sy * (GY + 0.02), zcol_s(GY) - BASE_OFF - 0.004 - 0.13))
            b = Vector((xb, 0.0, ZR - BASE_OFF - 0.004 - 0.13))
            ax = (b - a).normalized()
            w = ax.cross(Vector((1, 0, 0))).normalized()
            if w.z < 0:
                w = -w
            G.obox(g, (a + b) / 2, ax, (1, 0, 0), w, (b - a).length / 2 + 0.02, 0.028, 0.13, T_)
            # a small end block at the bargeboard foot
            G.box(g, xb - 0.045, xb + 0.045, sy * (GY + 0.02) - 0.07, sy * (GY + 0.02) + 0.07,
                  zcol_s(GY) - BASE_OFF - 0.30, zcol_s(GY) - BASE_OFF - 0.16, T_, grain="y")
        za = ZR - BASE_OFF - 0.004
        G.prism(g, [(xb, -0.16, za - 0.22), (xb, 0.16, za - 0.22), (xb, 0.20, za - 0.08), (xb, 0.0, za),
                    (xb, -0.20, za - 0.08)], (sx, 0, 0), 0.05, T_,
                frame=(Vector((0, 0, 1)), Vector((0, 1, 0)), Vector((1, 0, 0))))
    # ridge: bed, 3 noshi layers, ridge roll; ridge-end tiles (stacked: base block, roll-end drum, big plain disc;
    # no symbol, per the f1 direction)
    zr0 = ZR - 0.10
    G.box(g, -GX + 0.06, GX - 0.06, -0.20, 0.20, ZR - BASE_OFF - 0.02, zr0, MO)
    top = G.noshi_stack(g, (-GX + 0.06, 0, zr0), (GX - 0.06, 0, zr0), (0, 0, 1), [0.42, 0.38, 0.34], 0.045, TL, seg=0.3,
                        seed=41)
    kz = zr0 + top + 0.024
    G.roll_line(g, (-GX + 0.12, 0, kz), (GX - 0.12, 0, kz), (0, 0, 1), TL, r=0.068, seg=0.3)
    ONI_R = 0.205
    oni_top = kz + 0.045 + ONI_R
    for sx in (-1, 1):
        xe = sx * GX
        G.box(g, min(xe - sx * 0.14, xe + sx * 0.06), max(xe - sx * 0.14, xe + sx * 0.06), -0.27, 0.27, zr0 - 0.07,
              kz + 0.03, TL, grain="y")
        G.lathe(g, (xe + sx * 0.05, 0, zr0 + 0.06), (sx, 0, 0), (0, 0, 1),
                [(0.0, 0.0), (0.0, 0.125), (0.08, 0.125), (0.08, 0.0)], TL, nseg=18)        # lower tier
        G.lathe(g, (xe + sx * 0.05, 0, kz + 0.01), (sx, 0, 0), (0, 0, 1),
                [(0.0, 0.0), (0.0, 0.15), (0.10, 0.15), (0.10, 0.0)], TL, nseg=20)          # roll-end drum
        dc = Vector((xe + sx * 0.17, 0, kz + 0.045))
        # f1 direction: a plain round face (no symbol, no emblem): raised rim, a stepped inner ring and a low boss
        G.disc(g, dc, (sx, 0, 0), (0, 0, 1), ONI_R, 0.10, TL, recess=0.014, rim=0.86, nseg=32)
        G.lathe(g, dc - Vector((sx * 0.014, 0, 0)), (sx, 0, 0), (0, 0, 1),
                [(0.0, ONI_R * 0.62), (0.010, ONI_R * 0.62), (0.010, ONI_R * 0.52), (0.0, ONI_R * 0.52)], TL, nseg=28)
        G.dome(g, dc - Vector((sx * 0.014, 0, 0)), (sx, 0, 0), (0, 0, 1), ONI_R * 0.22, TL, nseg=16, rings=3)
    # f1: a gentle sag of the slopes (about 3 cm mid-slope) and a slight upturn of the eave towards the corners
    def sag(v):
        ay = abs(v.y)
        if ay > GY + 0.1:
            return Vector()
        s = max(0.0, min(1.0, (GY - ay) / GY))
        dz = -0.03 * math.sin(math.pi * s)
        dz += 0.05 * max(0.0, (abs(v.x) - 2.0) / 2.0) ** 2 * max(0.0, 1.0 - (GY - ay) / 1.0)
        return Vector((0, 0, dz))
    G.warp(g, sag)
    p.g = g
    # collision: one flat plane per slope (0.2 m slabs), the ridge stack, the two ridge-end tiles
    sl_th = 0.2

    def slab(poly):
        pts = [Vector(q) for q in poly]
        return pts + [q - Vector((0, 0, sl_th)) for q in pts]

    for sgn in (-1, 1):
        p.hull_pts(slab([(-GX, sgn * GY, zcol_s(GY)), (GX, sgn * GY, zcol_s(GY)), (GX, 0.0, ZR), (-GX, 0.0, ZR)]))
    p.hull_box(-GX + 0.06, GX - 0.06, -0.21, 0.21, zr0, kz + 0.068)
    for sx in (-1, 1):
        p.hull_box(min(sx * (GX - 0.14), sx * (GX + 0.17)), max(sx * (GX - 0.14), sx * (GX + 0.17)), -0.31, 0.31,
                   zr0 - 0.07, oni_top)
    p.nanite = True
    p.extra = {"ridge_roll_top": round(kz + 0.068, 3), "planes_meet": round(ZR, 4), "ridge_end_top": round(oni_top, 3),
               "ridge_end_face_x": GX + 0.17, "gable_x": GP, "verge_x": GX, "pitch_deg": 25.0,
               "sag_mid_slope_m": 0.03, "eave_corner_upturn_m": 0.05}
    return p


def post(g, x, y, hx, hy, z0, z1, bolts=True):
    G.box(g, x - hx, x + hx, y - hy, y + hy, z0, z1, T_, grain="z")
    if bolts:
        for zb in (z1 - 0.35, z0 + 0.6):
            for (fx, fy) in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                c = Vector((x + fx * (hx + 0.004), y + fy * (hy + 0.004), zb))
                n = Vector((fx, fy, 0))
                G.obox(g, c, Vector((0, 0, 1)), Vector((-fy, fx, 0)), n, 0.08, min(hx, hy) * 0.7, 0.004, IR)
                G.dome(g, c + n * 0.004, n, (0, 0, 1), 0.018, IR, nseg=8, rings=2)


def plinth(g, x0, x1, y0, y1, z1, seed):
    """A squared granite plinth block with moss low down and grime (the sheet's post bases)."""
    G.rounded_stone(g, ((x0 + x1) / 2, (y0 + y1) / 2, z1 / 2), ((1, 0, 0), (0, -1, 0), (0, 0, 1)),
                    ((x1 - x0) / 2, (y1 - y0) / 2, z1 / 2), 0.025, seed, GR, bulge=0.004, rough=0.008, n=(4, 4, 2),
                    vc=moss_rule(z1 + 0.05, grime=0.55))


def plank_panel(g, x0, x1, y0, y1, z0, z1, n_planks, ch=0.012):
    """Vertical planks with deep V grooves between x0..x1 (plank faces at y0 / y1)."""
    w = (x1 - x0) / n_planks
    for i in range(n_planks):
        a, b = x0 + i * w, x0 + (i + 1) * w
        poly = [(a + ch, y0, z1), (b - ch, y0, z1), (b, y0 + ch, z1), (b, y1 - ch, z1), (b - ch, y1, z1),
                (a + ch, y1, z1), (a, y1 - ch, z1), (a, y0 + ch, z1)]
        G.prism(g, poly, (0, 0, 1), z1 - z0, T_, frame=(Vector((0, 0, 1)), Vector((1, 0, 0)), Vector((0, 1, 0))))


def gate_frame():
    p = Piece("SM_DK_Gate_Frame", "building", "Gatehouse",
              "gatehouse frame: door posts, wall posts, front + rear corner posts on plinths, bracket clusters, layered "
              "eave beams, tie beams, gables, lintel, plank side panels")
    g = p.g
    for sx in (-1, 1):
        # plinth blocks
        for sy in (-1, 1):
            plinth(g, sx * GP - 0.28, sx * GP + 0.28, sy * PY - 0.28, sy * PY + 0.28, 0.20, 7 + sx + 3 * sy)
        plinth(g, min(sx * 3.00, sx * 3.38), max(sx * 3.00, sx * 3.38), -0.70, -0.30, 0.20, 17 + sx)
        plinth(g, min(sx * 2.245, sx * 2.62), max(sx * 2.245, sx * 2.62), -0.95, -0.10, 0.20, 21 + sx)
        plinth(g, min(sx * 2.62, sx * 3.00), max(sx * 2.62, sx * 3.00), -0.66, -0.34, 0.30, 25 + sx)
        # corner posts + bracket clusters (daito, crossed bracket arms, small blocks)
        for sy in (-1, 1):
            cx, cy = sx * GP, sy * PY
            post(g, cx, cy, 0.18, 0.18, 0.20, 2.70)
            G.box(g, cx - 0.23, cx + 0.23, cy - 0.23, cy + 0.23, 2.70, 2.84, T_, grain="x")
            G.box(g, cx - 0.62, cx + 0.62, cy - 0.08, cy + 0.08, 2.84, 2.98, T_, grain="x")
            G.box(g, cx - 0.08, cx + 0.08, cy - 0.62, cy + 0.62, 2.84, 2.98, T_, grain="y")
            for (dx, dy) in ((-0.52, 0), (0.52, 0), (0, -0.52), (0, 0.52), (0, 0)):
                G.box(g, cx + dx - 0.10, cx + dx + 0.10, cy + dy - 0.10, cy + dy + 0.10, 2.98, 3.06, T_, grain="x")
        # wall post (the gable's centre post: the wall runs into it)
        post(g, sx * GP, -0.5, 0.18, 0.18, 0.20, 3.06)
        # door post (heavy, 0.375 x 0.84) with pintle plates on its inner face
        xa, xb = sorted((sx * 2.25, sx * 2.625))
        G.box(g, xa, xb, -0.92, -0.08, 0.20, 3.85, T_, grain="z")
        for zc in (LEAF_Z + 0.80, LEAF_Z + 2.55):
            xi = sx * 2.25
            G.box(g, min(xi, xi - sx * 0.008), max(xi, xi - sx * 0.008), -0.84, -0.70, zc - 0.12, zc + 0.12, IR)
        for zb in (0.9, 2.2, 3.3):
            G.box(g, xa - 0.004, xb + 0.004, -0.924, -0.076, zb - 0.035, zb + 0.035, IR, grain="x")
        # plank side panel between the door post and the wall post, framed by rails
        pa, pb = sorted((sx * 2.625, sx * 3.02))
        G.box(g, pa, pb, -0.60, -0.40, 0.30, 0.42, T_, grain="x")
        G.box(g, pa, pb, -0.60, -0.40, 3.38, 3.50, T_, grain="x")
        plank_panel(g, pa, pb, -0.58, -0.42, 0.42, 3.38, 3)
        for (ya, yb) in ((-0.64, -0.58), (-0.42, -0.36)):
            G.box(g, pa, pb, ya, yb, 1.70, 1.82, T_, grain="x")          # mid rail on both faces
        # f1: the courtyard half of each side is closed by a vertical-plank panel from the wall post to the rear corner
        # post, on a granite sill (the return wall runs outside it; no capsule-sized gap is left between them)
        xa_, xb_ = sorted((sx * GP - 0.06, sx * GP + 0.06))
        plinth(g, xa_ - 0.03, xb_ + 0.03, -0.29, 1.46, 0.20, 31 + sx)
        nps = 5
        wps = (1.57 + 0.32) / nps
        for i in range(nps):
            ya_, yb_ = -0.32 + i * wps + 0.005, -0.32 + (i + 1) * wps - 0.005
            G.box(g, xa_ + 0.01, xb_ - 0.01, ya_, yb_, 0.20, 3.06, T_, grain="z")
        for (zr0_, zr1_) in ((0.20, 0.34), (1.70, 1.82), (2.92, 3.06)):
            G.box(g, xa_, xb_, -0.32, 1.57, zr0_, zr1_, T_, grain="y")
        # tie beam along y at the gable (ends past the eave beams as square blocks)
        G.box(g, sx * GP - 0.11, sx * GP + 0.11, -2.02, 2.02, 3.06, 3.30, T_, grain="y")
        # gable: centre block, king post, short tie, block under the ridge beam, dark board infill (set back)
        G.box(g, sx * GP - 0.14, sx * GP + 0.14, -0.14, 0.14, 3.30, 3.42, T_, grain="x")
        G.box(g, sx * GP - 0.08, sx * GP + 0.08, -0.09, 0.09, 3.42, 3.98, T_, grain="z")
        G.box(g, sx * GP - 0.06, sx * GP + 0.06, -0.62, 0.62, 3.64, 3.74, T_, grain="y")
        G.box(g, sx * GP - 0.12, sx * GP + 0.12, -0.12, 0.12, 3.86, 3.98, T_, grain="x")
        yb_ = GY - (3.30 + 0.02 + UNDER - GATE_EAVE) / TN
        xin = sx * (GP - 0.10)
        tri = [(xin, -yb_, 3.30), (xin, yb_, 3.30), (xin, 0.0, roof_under(0.0) - 0.02)]
        if sx < 0:
            tri = [tri[1], tri[0], tri[2]]
        G.prism(g, tri, (sx, 0, 0), 0.03, T_, frame=(Vector((0, 0, 1)), Vector((0, 1, 0)), Vector((1, 0, 0))))
        for kb in range(-6, 7):
            yb = kb * 0.26
            ztop_b = roof_under(yb) - 0.03
            if ztop_b - 3.30 < 0.08 or abs(yb) > yb_:
                continue
            G.box(g, min(xin, xin + sx * 0.02), max(xin, xin + sx * 0.02), yb - 0.03, yb + 0.03, 3.30, ztop_b, T_,
                  grain="z")
    # layered eave beams on the front and rear post lines: lower beam, keta, dentil blocks under the keta's outer edge
    for sy in (-1, 1):
        cy = sy * PY
        G.box(g, -3.90, 3.90, cy - 0.09, cy + 0.09, 3.06, 3.20, T_, grain="x")
        G.box(g, -3.95, 3.95, cy - 0.14, cy + 0.14, 3.20, 3.36, T_, grain="x")
        yo0, yo1 = sorted((cy + sy * 0.09, cy + sy * 0.19))
        for k in range(-8, 9):
            x = k * 0.40
            if abs(abs(x) - GP) < 0.3:
                continue
            G.box(g, x - 0.055, x + 0.055, yo0, yo1, 3.10, 3.20, T_, grain="y")
        # keta end blocks past the corner posts
        for sx in (-1, 1):
            G.box(g, min(sx * 3.95, sx * 4.07), max(sx * 3.95, sx * 4.07), cy - 0.16, cy + 0.16, 3.18, 3.36, T_,
                  grain="y")
    # ridge beam and mid purlins (their ends show in the gables)
    G.box(g, -3.95, 3.95, -0.10, 0.10, 3.98, roof_under(0.0) - 0.004, T_, grain="x")
    for sy in (-1, 1):
        G.box(g, -3.95, 3.95, sy * 0.9 - 0.07, sy * 0.9 + 0.07, roof_under(0.97) - 0.12, roof_under(0.97) - 0.004, T_,
              grain="x")
    # lintel over the doors and the side panels (deep), head rail on it
    G.box(g, -3.02, 3.02, -0.80, -0.24, 3.50, 3.85, T_, grain="x")
    # collision
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.hull_box(sx * GP - 0.28, sx * GP + 0.28, sy * PY - 0.28, sy * PY + 0.28, 0.0, 2.70)
        p.hull_box(min(sx * 2.25, sx * 2.625), max(sx * 2.25, sx * 2.625), -0.95, -0.08, 0.0, 3.85)
        p.hull_box(min(sx * 2.625, sx * 3.38), max(sx * 2.625, sx * 3.38), -0.70, -0.30, 0.0, 3.50)
        p.hull_box(sx * GP - 0.11, sx * GP + 0.11, -2.02, 2.02, 3.06, 3.30)
        p.hull_box(sx * GP - 0.09, sx * GP + 0.09, -0.32, 1.57, 0.0, 3.06)          # f1 courtyard-half side panel
        # the gable (tie beam up to the roof): nobody climbs into the roof space
        p.hull_pts([(sx * GP - 0.10, -yb_, 3.30), (sx * GP - 0.10, yb_, 3.30), (sx * GP + 0.10, -yb_, 3.30),
                    (sx * GP + 0.10, yb_, 3.30), (sx * GP - 0.10, 0.0, roof_under(0.0)),
                    (sx * GP + 0.10, 0.0, roof_under(0.0))])
    for sy in (-1, 1):
        p.hull_box(-3.95, 3.95, sy * PY - 0.14, sy * PY + 0.14, 3.06, 3.36)
    p.hull_box(-3.02, 3.02, -0.80, -0.24, 3.50, 3.85)
    p.nanite = True
    p.extra = {"passage_headroom_m": 3.06, "door_posts_inner_x": 2.25, "corner_posts": [GP, PY]}
    return p


def gate_leaf():
    """The LEFT leaf: pivot on the hinge axis at the courtyard face, bottom; the leaf runs along +X (local x 0.004 ..
    LEAF_W), its street face at y = -LEAF_TT; it opens by rotating +90 deg (inward). Nothing goes below local x 0
    (the door post's hull) or outside y in [-LEAF_TT, 0]."""
    g = Geo()
    x0, x1 = 0.004, LEAF_W
    H = LEAF_H
    st = 0.14
    yc0, yc1 = -0.16, -0.04          # core (stiles, rails, planks)
    G.box(g, x0, x0 + st, yc0, yc1, 0, H, T_, grain="z")
    G.box(g, x1 - st, x1, yc0, yc1, 0, H, T_, grain="z")
    G.box(g, x0 + st, x1 - st, yc0, yc1, 0, 0.14, T_, grain="x")
    G.box(g, x0 + st, x1 - st, yc0, yc1, H - 0.14, H, T_, grain="x")
    plank_panel(g, x0 + st, x1 - st, yc0 + 0.008, yc1 - 0.008, 0.14, H - 0.14, 8, ch=0.014)
    # street face: three battens with rows of round-head nails
    yo = yc0
    bat = [(0.20, 0.38), (1.62, 1.82), (H - 0.42, H - 0.24)]
    for (za, zb_) in bat:
        G.box(g, x0 + 0.02, x1 - 0.02, yo - 0.04, yo, za, zb_, T_, grain="x")
        for zrow in (za + 0.045, zb_ - 0.045):
            xs = x0 + 0.09
            while xs < x1 - 0.06:
                G.dome(g, (xs, yo - 0.04, zrow), (0, -1, 0), (0, 0, 1), 0.016, IR, nseg=8, rings=2)
                xs += 0.15
    # two long L-shaped strap hinges with spear tips (about 60 % of the leaf), nailed
    ys = yo - 0.012
    for zc in (0.80, 2.55):
        G.box(g, x0 + 0.005, x0 + 0.60 * LEAF_W, ys, yo, zc - 0.045, zc + 0.045, IR, grain="x")
        G.box(g, x0 + 0.02, x0 + 0.11, ys, yo, zc - 0.30, zc + 0.30, IR, grain="z")        # the L's leg
        xt = x0 + 0.60 * LEAF_W
        tip = [(xt - 0.02, ys, zc - 0.07), (xt + 0.20, ys, zc), (xt - 0.02, ys, zc + 0.07), (xt - 0.05, ys, zc)]
        G.prism(g, list(reversed(tip)), (0, -1, 0), 0.012, IR)
        xn = x0 + 0.20
        while xn < xt - 0.05:
            G.dome(g, (xn, ys, zc), (0, -1, 0), (0, 0, 1), 0.021, IR, nseg=8, rings=2)
            xn += 0.22
        for zn in (zc - 0.22, zc + 0.22):
            G.dome(g, (x0 + 0.065, ys, zn), (0, -1, 0), (0, 0, 1), 0.019, IR, nseg=8, rings=2)
        # knuckle round the pintle (inside the hinge stile's footprint: x >= 0)
        G.lathe(g, (0.030, -0.10, zc - 0.10), (0, 0, 1), (1, 0, 0), [(0.0, 0.0), (0.0, 0.026), (0.20, 0.026), (0.20, 0.0)],
                IR, nseg=10)
    # large round studs and a ring knocker at the meeting stile, on the middle batten
    mz = (bat[1][0] + bat[1][1]) / 2
    yb = yo - 0.04
    for zz in (mz - 0.05, mz + 0.05):
        G.dome(g, (x1 - 0.07, yb, zz), (0, -1, 0), (0, 0, 1), 0.030, IR, nseg=12, rings=3)
    G.dome(g, (x1 - 0.30, yb, mz + 0.04), (0, -1, 0), (0, 0, 1), 0.038, IR, nseg=12, rings=3)
    ring = [(0.012 * math.sin(2 * math.pi * k / 8), 0.062 + 0.011 * math.cos(2 * math.pi * k / 8)) for k in range(8)]
    G.lathe(g, (x1 - 0.30, yb - 0.022, mz - 0.02), (0, -1, 0), (0, 0, 1), ring, IR, nseg=16)
    # courtyard face: three battens with studs and two diagonal braces (the courtyard side is what the 1v1 sees)
    for (za, zb_) in ((0.30, 0.50), (1.60, 1.80), (H - 0.52, H - 0.32)):
        G.box(g, x0 + 0.02, x1 - 0.02, yc1, 0.0, za, zb_, T_, grain="x")
        for zrow in (za + 0.05, zb_ - 0.05):
            xs = x0 + 0.14
            while xs < x1 - 0.1:
                G.dome(g, (xs, -0.012, zrow), (0, 1, 0), (0, 0, 1), 0.012, IR, nseg=8, rings=2)
                xs += 0.36
    for (za, zb_) in ((0.50, 1.60), (1.80, H - 0.52)):
        a = Vector((x0 + 0.12, yc1 / 2, za + 0.06))
        b = Vector((x1 - 0.12, yc1 / 2, zb_ - 0.06))
        ax = (b - a).normalized()
        G.obox(g, (a + b) / 2, ax, (0, 1, 0), ax.cross(Vector((0, 1, 0))), (b - a).length / 2, -yc1 / 2 - 0.002, 0.07, T_)
    return g


def gate_leaves():
    L = Piece("SM_DK_Gate_Leaf_L", "building", "Gatehouse", "left gate leaf, pivot on the hinge axis (opens +90)")
    L.g = gate_leaf()
    L.hull_box(0.0, LEAF_W, -LEAF_TT, 0.0, 0.0, LEAF_H)
    L.nanite = True
    R = Piece("SM_DK_Gate_Leaf_R", "building", "Gatehouse", "right gate leaf, pivot on the hinge axis (opens -90)")
    R.g = G.mirror_x(gate_leaf())
    R.hull_box(-LEAF_W, 0.0, -LEAF_TT, 0.0, 0.0, LEAF_H)
    R.nanite = True
    return [L, R]


def gate_lamp():
    """Bracket lantern (f1: the sheet's lantern): an iron wall plate, a scrolled bracket arm, a tall glazed lantern
    (iron frame, four glass panes, flared base, hipped cap, finial ring). Pivot on the post face at the plate centre;
    the lantern stands out along -Y."""
    p = Piece("SM_DK_Gate_Lamp", "thin", "Gatehouse", "iron bracket lantern, warm emissive glass (x4 on the corner posts)")
    g = p.g
    G.box(g, -0.05, 0.05, -0.02, 0.0, -0.36, 0.26, IR, grain="z")                       # wall plate
    for zz in (-0.30, 0.20):
        G.dome(g, (0, -0.02, zz), (0, -1, 0), (0, 0, 1), 0.016, IR, nseg=8, rings=2)
    # scrolled arm: from the plate out to the hanger, curling down and back under itself
    cen, ups, rad = [], [], []
    for i in range(15):
        t = i / 14
        y = -0.02 - 0.30 * t
        z = 0.20 + 0.05 * math.sin(math.pi * t)
        cen.append(Vector((0, y, z)))
        ups.append(Vector((1, 0, 0)))
        rad.append(0.013)
    G.sweep(g, cen, ups, rad, IR, arc=(0.0, 350.0), nseg=8)
    sc = []
    for i in range(13):
        a = math.pi * 0.5 + 1.7 * math.pi * i / 12
        rr = 0.075 * (1 - 0.45 * i / 12)
        sc.append(Vector((0, -0.12 + rr * math.cos(a), 0.12 + rr * math.sin(a))))
    G.sweep(g, sc, [Vector((1, 0, 0))] * len(sc), [0.010] * len(sc), IR, arc=(0.0, 350.0), nseg=8)
    a, b = Vector((0, -0.02, -0.12)), Vector((0, -0.20, 0.16))
    ax = (b - a).normalized()
    G.obox(g, (a + b) / 2, ax, (1, 0, 0), ax.cross(Vector((1, 0, 0))), (b - a).length / 2, 0.010, 0.010, IR)   # stay
    G.lathe(g, (0, -0.32, 0.13), (0, 0, 1), (1, 0, 0), [(0.0, 0.0), (0.0, 0.012), (0.08, 0.012), (0.08, 0.0)], IR,
            nseg=8)                                                                        # hanger rod
    # the lantern: centre (0, -0.32), body z -0.28 .. 0.06
    cy = -0.32
    G.lathe(g, (0, cy, -0.36), (0, 0, 1), (1, 0, 0), [(0.0, 0.0), (0.0, 0.05), (0.03, 0.11), (0.06, 0.13), (0.08, 0.13),
                                                     (0.08, 0.0)], IR, nseg=4)             # flared base (square)
    for sx in (-1, 1):
        for sy in (-1, 1):
            G.box(g, sx * 0.11 - 0.012, sx * 0.11 + 0.012, cy + sy * 0.11 - 0.012, cy + sy * 0.11 + 0.012, -0.28, 0.06,
                  IR, grain="z")
    G.box(g, -0.10, 0.10, cy - 0.10, cy + 0.10, -0.28, 0.06, LG)                          # glass
    for zz in (-0.28, -0.11, 0.06):
        for sy in (-1, 1):
            G.box(g, -0.12, 0.12, cy + sy * 0.11 - 0.008, cy + sy * 0.11 + 0.008, zz - 0.008, zz + 0.008, IR, grain="x")
        for sx in (-1, 1):
            G.box(g, sx * 0.11 - 0.008, sx * 0.11 + 0.008, cy - 0.12, cy + 0.12, zz - 0.008, zz + 0.008, IR, grain="y")
    G.lathe(g, (0, cy, 0.06), (0, 0, 1), (1, 1, 0), [(0.0, 0.0), (0.0, 0.18), (0.02, 0.18), (0.07, 0.10), (0.10, 0.05),
                                                    (0.11, 0.035), (0.11, 0.0)], IR, nseg=4)   # hipped cap
    ring = [(0.008 * math.sin(2 * math.pi * k / 8), 0.035 + 0.008 * math.cos(2 * math.pi * k / 8)) for k in range(8)]
    G.lathe(g, (0, cy, 0.215), (1, 0, 0), (0, 0, 1), ring, IR, nseg=12)                    # finial ring
    p.hull_box(-0.14, 0.14, -0.46, 0.0, -0.40, 0.30)
    p.extra = {"light_local": [0.0, cy, -0.11]}
    return p


def slab_field(g, rng, x0, x1, y0, y1, top, big=False, moss=0.05, grime=0.35):
    """Granite paving slabs of varied sizes over a rectangle (rows of random depth, random lengths, a few big ones)."""
    y = y0
    while y < y1 - 0.05:
        d = min(rng.uniform(0.40, 0.80 if big else 0.62), y1 - y)
        if y1 - (y + d) < 0.22:
            d = y1 - y
        x = x0
        while x < x1 - 0.05:
            w = min(rng.uniform(0.45, 1.30), x1 - x)
            if x1 - (x + w) < 0.28:
                w = x1 - x
            gp = 0.008
            jj = [rng.uniform(-0.006, 0.006) for _ in range(4)]
            poly = [(x + gp + jj[0], y + gp), (x + w - gp, y + gp + jj[1]), (x + w - gp + jj[2], y + d - gp),
                    (x + gp, y + d - gp + jj[3])]
            G.polystone(g, poly, (0, 0, top - 0.004), (1, 0, 0), (0, 0, 1), 0.10, 0.0, rng.randrange(10 ** 6), GR,
                        chamfer=0.012, bulge=0.004, rough=0.003, step=0.12,
                        moss=(lambda v, j, u, m=moss: clamp01(m + 0.55 * j * (0.4 + 0.6 * (noise.noise(v * 4.0) * 0.5 + 0.5)))),
                        grime=grime)
            x += w
        y += d


def gate_paving():
    rng = random.Random(5)
    p = Piece("SM_DK_Gate_Paving", "ground", "Gatehouse",
              "granite paving of varied slabs: front step +0.05, apron +0.10, threshold +0.10, courtyard side +0.03")
    g = p.g
    slab_field(g, rng, -3.2, 3.2, -3.0, -2.5, 0.05, big=True)
    slab_field(g, rng, -3.9, 3.9, -2.5, -1.25, 0.10)
    slab_field(g, rng, -3.36, 3.36, -1.25, -1.05, 0.10)            # clear of the 1.4 m step piers (|x| > 3.38)
    for sx in (-1, 1):
        a, b = sorted((sx * 2.25, sx * 3.36))
        slab_field(g, rng, a, b, -1.05, -0.95, 0.10)
    # granite threshold: two long stones (flat top +0.10, the closed leaves hang 1 cm over it), moss and grime
    for (xa, xb) in ((-2.24, 0.0), (0.0, 2.24)):
        G.polystone(g, [(xa + 0.006, -1.05), (xb - 0.006, -1.05), (xb - 0.006, -0.55), (xa + 0.006, -0.55)],
                    (0, 0, 0.098), (1, 0, 0), (0, 0, 1), 0.12, 0.0, int(xa * 10) % 97 + 3, GR, chamfer=0.016,
                    bulge=0.0, rough=0.002, step=0.15,
                    moss=lambda v, j, u: clamp01(0.08 + 0.6 * j * (noise.noise(v * 5.0) * 0.5 + 0.5)), grime=0.6)
    slab_field(g, rng, -2.24, 2.24, -0.55, 0.0, 0.03)
    slab_field(g, rng, -3.36, 3.36, 0.0, 0.25, 0.03)
    slab_field(g, rng, -3.9, 3.9, 0.25, 2.5, 0.03)
    p.hull_box(-3.2, 3.2, -3.0, -2.5, -0.08, 0.05)
    p.hull_box(-3.9, 3.9, -2.5, -1.25, -0.08, 0.10)
    p.hull_box(-3.36, 3.36, -1.25, -0.95, -0.08, 0.10)
    p.hull_box(-2.24, 2.24, -1.05, -0.55, -0.08, 0.10)
    p.hull_box(-2.24, 2.24, -0.55, 0.0, -0.08, 0.03)
    p.hull_box(-3.36, 3.36, 0.0, 0.25, -0.08, 0.03)
    p.hull_box(-3.9, 3.9, 0.25, 2.5, -0.08, 0.03)
    p.nanite = True
    return p


# ------------------------------------------------------------------------------------------------ materials
def build_material(name):
    tex, tile, p = MATERIALS[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    if tex is None:
        bsdf.inputs["Base Color"].default_value = hexcol(p["color"])
        bsdf.inputs["Roughness"].default_value = p.get("rough", 0.8)
        if "emit" in p:
            bsdf.inputs["Emission Color"].default_value = hexcol(p["emit_color"])
            bsdf.inputs["Emission Strength"].default_value = p["emit"]
        mat.diffuse_color = hexcol(p["color"])
        return mat

    def img(suffix, noncolor, vec=None):
        node = nt.nodes.new("ShaderNodeTexImage")
        image = bpy.data.images.load(str(TEX / f"T_DK_{tex}_{suffix}.png"), check_existing=True)
        if noncolor:
            image.colorspace_settings.name = "Non-Color"
        node.image = image
        if vec is not None:
            nt.links.new(vec, node.inputs["Vector"])
        return node

    if p.get("world"):
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(geo.outputs["Position"], sep.inputs[0])
        nsep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(geo.outputs["Normal"], nsep.inputs[0])

        def vec2(a, b):
            c = nt.nodes.new("ShaderNodeCombineXYZ")
            for i, src in enumerate((a, b)):
                m = nt.nodes.new("ShaderNodeMath")
                m.operation = "DIVIDE"
                m.inputs[1].default_value = tile
                nt.links.new(sep.outputs[src], m.inputs[0])
                nt.links.new(m.outputs[0], c.inputs[i])
            return c.outputs[0]

        cols, orms, nrms, ws = [], [], [], []
        for (a, b, nrm_axis) in ((1, 2, 0), (0, 2, 1), (0, 1, 2)):
            v = vec2(a, b)
            cols.append(img("BC", False, v).outputs["Color"])
            orms.append(img("ORM", True, v).outputs["Color"])
            ab = nt.nodes.new("ShaderNodeMath")
            ab.operation = "ABSOLUTE"
            nt.links.new(nsep.outputs[nrm_axis], ab.inputs[0])
            pw = nt.nodes.new("ShaderNodeMath")
            pw.operation = "POWER"
            pw.inputs[1].default_value = 6.0
            nt.links.new(ab.outputs[0], pw.inputs[0])
            ws.append(pw.outputs[0])
        s1 = nt.nodes.new("ShaderNodeMath")
        nt.links.new(ws[0], s1.inputs[0])
        nt.links.new(ws[1], s1.inputs[1])
        s2 = nt.nodes.new("ShaderNodeMath")
        nt.links.new(s1.outputs[0], s2.inputs[0])
        nt.links.new(ws[2], s2.inputs[1])

        def blend3(outs):
            acc = None
            for o, w in zip(outs, ws):
                d = nt.nodes.new("ShaderNodeMath")
                d.operation = "DIVIDE"
                nt.links.new(w, d.inputs[0])
                nt.links.new(s2.outputs[0], d.inputs[1])
                m = nt.nodes.new("ShaderNodeVectorMath")
                m.operation = "SCALE"
                nt.links.new(o, m.inputs[0])
                nt.links.new(d.outputs[0], m.inputs["Scale"])
                if acc is None:
                    acc = m.outputs[0]
                else:
                    ad = nt.nodes.new("ShaderNodeVectorMath")
                    nt.links.new(acc, ad.inputs[0])
                    nt.links.new(m.outputs[0], ad.inputs[1])
                    acc = ad.outputs[0]
            return acc

        bc_out = blend3(cols)
        orm_out = blend3(orms)
        nrm_out = None
        # relief from the normal map's height proxy: the ORM's AO carries cracks and trowel lines (f1: stronger)
        hsep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(orm_out, hsep.inputs["Color"])
        bw = nt.nodes.new("ShaderNodeRGBToBW")
        nt.links.new(bc_out, bw.inputs[0])
        addh = nt.nodes.new("ShaderNodeMath")
        nt.links.new(bw.outputs[0], addh.inputs[0])
        nt.links.new(hsep.outputs[0], addh.inputs[1])
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.45
        bump.inputs["Distance"].default_value = 0.004
        nt.links.new(addh.outputs[0], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    else:
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "UV0"
        bc = img("BC", False, uvn.outputs[0])
        orm = img("ORM", True, uvn.outputs[0])
        nrm = img("N", True, uvn.outputs[0])
        bc_out, orm_out, nrm_out = bc.outputs["Color"], orm.outputs["Color"], nrm.outputs["Color"]
    col = bc_out
    if p.get("tint"):          # f1 EarthCore: the plaster set multiplied by a tint (UE: the MI's Tint parameter)
        tm = nt.nodes.new("ShaderNodeMix")
        tm.data_type = "RGBA"
        tm.blend_type = "MULTIPLY"
        tm.inputs["Factor"].default_value = 1.0
        nt.links.new(col, tm.inputs["A"])
        tm.inputs["B"].default_value = hexcol(p["tint"])          # plaster x tint = the sheet's muddy earth brown
        col = tm.outputs["Result"]
    attr = nt.nodes.new("ShaderNodeVertexColor")
    attr.layer_name = "Col"
    asep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(attr.outputs["Color"], asep.inputs[0])
    if p.get("grime"):
        geo2 = nt.nodes.new("ShaderNodeNewGeometry")
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (7.0, 7.0, 0.35)
        nt.links.new(geo2.outputs["Position"], mp.inputs["Vector"])
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = 2.0
        nz.inputs["Detail"].default_value = 4.0
        nt.links.new(mp.outputs[0], nz.inputs["Vector"])
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value = 0.35
        mr.inputs["From Max"].default_value = 0.65
        nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
        mul = nt.nodes.new("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        nt.links.new(asep.outputs[1], mul.inputs[0])
        nt.links.new(mr.outputs[0], mul.inputs[1])
        k = nt.nodes.new("ShaderNodeMath")
        k.operation = "MULTIPLY"
        k.inputs[1].default_value = p["grime"]
        nt.links.new(mul.outputs[0], k.inputs[0])
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        nt.links.new(k.outputs[0], mix.inputs["Factor"])
        nt.links.new(col, mix.inputs["A"])
        mix.inputs["B"].default_value = hexcol("#6A5A48")
        col = mix.outputs["Result"]
    if p.get("moss"):
        mm = nt.nodes.new("ShaderNodeTexImage")
        mimg = bpy.data.images.load(str(TEX / "T_DK_MossMask_M.png"), check_existing=True)
        mimg.colorspace_settings.name = "Non-Color"
        mm.image = mimg
        geo3 = nt.nodes.new("ShaderNodeNewGeometry")
        mp3 = nt.nodes.new("ShaderNodeMapping")
        mp3.inputs["Scale"].default_value = (1.3, 1.3, 1.3)
        nt.links.new(geo3.outputs["Position"], mp3.inputs["Vector"])
        mm.projection = "BOX"
        mm.projection_blend = 0.3
        nt.links.new(mp3.outputs[0], mm.inputs["Vector"])
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value = 0.10
        mr.inputs["From Max"].default_value = 0.40
        mul = nt.nodes.new("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        nt.links.new(asep.outputs[0], mul.inputs[0])
        nt.links.new(mm.outputs["Color"], mul.inputs[1])
        nt.links.new(mul.outputs[0], mr.inputs["Value"])
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        nt.links.new(mr.outputs[0], mix.inputs["Factor"])
        nt.links.new(col, mix.inputs["A"])
        mix.inputs["B"].default_value = hexcol("#56613A")
        col = mix.outputs["Result"]
    nt.links.new(col, bsdf.inputs["Base Color"])
    osep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(orm_out, osep.inputs["Color"])
    nt.links.new(osep.outputs[1], bsdf.inputs["Roughness"])
    nt.links.new(osep.outputs[2], bsdf.inputs["Metallic"])
    if nrm_out is not None:
        sn = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(nrm_out, sn.inputs["Color"])
        inv = nt.nodes.new("ShaderNodeMath")
        inv.operation = "SUBTRACT"
        inv.inputs[0].default_value = 1.0
        nt.links.new(sn.outputs[1], inv.inputs[1])
        cmb = nt.nodes.new("ShaderNodeCombineColor")
        nt.links.new(sn.outputs[0], cmb.inputs[0])
        nt.links.new(inv.outputs[0], cmb.inputs[1])
        nt.links.new(sn.outputs[2], cmb.inputs[2])
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.uv_map = "UV0"
        nt.links.new(cmb.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    mat.diffuse_color = hexcol(p["tint"]) if p.get("tint") else hexcol({"EarthPlaster": "#B9A488", "Granite": "#8A8680", "RoofTile": "#50565E",
                                "Timber": "#45352A", "Iron": "#3A3937"}[tex])
    return mat


# ------------------------------------------------------------------------------------------------ mesh build
def build_mesh(piece, coll):
    g = piece.g
    mats = []
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UV0")
    col = bm.loops.layers.color.new("Col")
    vs = [bm.verts.new(p) for p in g.v]
    bad = 0
    for fi, f in enumerate(g.f):
        try:
            face = bm.faces.new([vs[i] for i in f])
        except ValueError:
            bad += 1
            continue
        m = g.fm[fi]
        if m not in mats:
            mats.append(m)
        face.material_index = mats.index(m)
        face.normal_update()
        n = face.normal
        fr = g.fr[fi]
        axes = list(fr) if fr is not None else [Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))]
        ni = max(range(3), key=lambda i: abs(n.dot(axes[i])))
        inplane = [i for i in range(3) if i != ni]
        ui = 0 if 0 in inplane else inplane[0]
        vi = [i for i in inplane if i != ui][0]
        U, Vv = axes[ui], axes[vi]
        tile = MATERIALS[m][1]
        rule = g.fc[fi]
        for loop, vidx in zip(face.loops, f):
            co = loop.vert.co
            loop[uvl].uv = (co.dot(U) / tile, co.dot(Vv) / tile)
            if vidx in g.vcol:
                c = g.vcol[vidx]
            else:
                c = rule(co) if rule else (0.0, 0.0, 1.0)
            loop[col] = (c[0], c[1], c[2], 1.0)
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
    mesh = bpy.data.meshes.new(piece.name)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(bpy.data.materials[m])
    obj = bpy.data.objects.new(piece.name, mesh)
    coll.objects.link(obj)
    add_uv1(obj)
    for i, pts in enumerate(piece.hulls):
        hb = bmesh.new()
        hv = [hb.verts.new(Vector(p)) for p in pts]
        bmesh.ops.convex_hull(hb, input=hv)
        for v in [v for v in hb.verts if not v.link_faces]:
            hb.verts.remove(v)
        hm = bpy.data.meshes.new(f"UCX_{piece.name}_{i:02d}")
        hb.to_mesh(hm)
        hb.free()
        h = bpy.data.objects.new(f"UCX_{piece.name}_{i:02d}", hm)
        coll.objects.link(h)
        h.parent = obj
        h.hide_render = True
        h.display_type = "WIRE"
    obj["nanite"] = piece.nanite
    return obj, bad


def fix_lod(obj):
    """After a Collapse decimate: drop faces that make an edge non-manifold (> 2 faces) and re-pack UV1 (decimation
    folds the lightmap islands)."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    extra = set()
    for e in bm.edges:
        if len(e.link_faces) > 2:
            for f in sorted(e.link_faces, key=lambda f: f.calc_area())[:len(e.link_faces) - 2]:
                extra.add(f)
    if extra:
        bmesh.ops.delete(bm, geom=list(extra), context="FACES")
    wire = [e for e in bm.edges if not e.link_faces]           # f1: collapse can leave face-less (wire) edges
    if wire:
        bmesh.ops.delete(bm, geom=wire, context="EDGES")
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.to_mesh(obj.data)
    bm.free()
    me = obj.data
    me.uv_layers.active_index = 1
    with bpy.context.temp_override(active_object=obj, object=obj, selected_objects=[obj], selected_editable_objects=[obj]):
        bpy.ops.uv.lightmap_pack(PREF_CONTEXT="ALL_FACES", PREF_PACK_IN_ONE=False, PREF_NEW_UVLAYER=False,
                                 PREF_BOX_DIV=12, PREF_MARGIN_DIV=0.2)
    me.uv_layers.active_index = 0
    obj["lod_fixed_faces"] = len(extra)


def add_uv1(obj):
    me = obj.data
    me.uv_layers.new(name="UV1")
    me.uv_layers.active_index = 1
    with bpy.context.temp_override(active_object=obj, object=obj, selected_objects=[obj], selected_editable_objects=[obj]):
        bpy.ops.uv.lightmap_pack(PREF_CONTEXT="ALL_FACES", PREF_PACK_IN_ONE=False, PREF_NEW_UVLAYER=False,
                                 PREF_BOX_DIV=12, PREF_MARGIN_DIV=0.2)
    me.uv_layers.active_index = 0


# ------------------------------------------------------------------------------------------------ layout
def place(piece, loc, rot):
    return {"piece": piece, "loc": [round(v, 4) for v in loc], "rot_z": float(rot)}


def run_module(side, a, L):
    """World pivot + rotation of a module that occupies [a, a + L] along a side's run coordinate."""
    if side == "S":
        return (a, 0.0, 0.0), 0.0
    if side == "N":
        return (a + L, 36.0, 0.0), 180.0
    if side == "W":
        return (0.0, a + L, 0.0), -90.0
    if side == "E":
        return (44.0, a, 0.0), 90.0
    raise ValueError(side)


def flipped(loc, rot, L):
    """The same module turned 180 deg about its centre line (pivot moves to local (L, -1))."""
    R = Matrix.Rotation(math.radians(rot), 4, "Z")
    far = Matrix.Translation(loc) @ R @ Vector((L, -WALL_T, 0.0))
    return (far.x, far.y, 0.0), (rot + 180.0 + 180.0) % 360.0 - 180.0


RUNS = {   # side: list of (start, length) modules, from the grey-box wall runs (the piers cover the joints they hide)
    "S": [(0, 4), (4, 4), (8, 4), (12, 4), (16, 1), (27, 1), (28, 4), (32, 4), (36, 4), (40, 4)],
    "N": [(x, 4) for x in range(0, 44, 4)],
    "W": [(0, 4), (4, 4), (8, 4), (12, 4), (16, 4), (20, 4), (24, 2), (26, 1), (27, 1), (28, 4), (32, 4)],
    "E": [(0, 4), (4, 4), (8, 4), (12, 4), (16, 4), (20, 4), (24, 2), (26, 1), (27, 1), (28, 4), (32, 4)],
}
CORNERS = [((0.0, 0.0, 0.0), 0.0), ((44.0, 0.0, 0.0), 90.0), ((44.0, 36.0, 0.0), 180.0), ((0.0, 36.0, 0.0), -90.0)]
GATE_CORNERS = [((17.0, 0.0, 0.0), 90.0), ((27.0, 0.0, 0.0), 0.0)]    # the wall turns north beside the gatehouse
PIERS = [("SM_DK_Wall_GateReturn_W", (17.0, 0.0, 0.0), 0.0), ("SM_DK_Wall_GateReturn_E", (27.0, 0.0, 0.0), 0.0),
         ("SM_DK_Wall_StepPier", (-1.0, 26.4, 0.0), 90.0), ("SM_DK_Wall_StepPier", (44.0, 26.4, 0.0), 90.0)]
LEAF_CLOSED = [((GC.x - HINGE_X, HINGE_Y, LEAF_Z), 0.0), ((GC.x + HINGE_X, HINGE_Y, LEAF_Z), 0.0)]
LEAF_OPEN = [((GC.x - HINGE_X, HINGE_Y, LEAF_Z), 90.0), ((GC.x + HINGE_X, HINGE_Y, LEAF_Z), -90.0)]
LAMPS = [((GC.x - GP, -PY - 0.18, 2.35), 0.0), ((GC.x + GP, -PY - 0.18, 2.35), 0.0),
         ((GC.x - GP, PY + 0.18, 2.35), 180.0), ((GC.x + GP, PY + 0.18, 2.35), 180.0)]


def lamp_light_world(loc, rot, local):
    return list(Matrix.Translation(loc) @ Matrix.Rotation(math.radians(rot), 4, "Z") @ Vector(local))


def kit1_instances(zb):
    inst = []
    k = 0
    for side, mods in RUNS.items():
        for (a, L) in mods:
            loc, rot = run_module(side, a, L)
            floc, frot = (flipped(loc, rot, L) if k % 2 else (loc, rot))
            inst.append(place(f"SM_DK_WallFooting_{L}m", floc, frot))
            inst.append(place(f"SM_DK_WallBody_{L}m_T200", (loc[0], loc[1], FOOT_H), rot))
            inst.append(place(f"SM_DK_WallCap_{L}m", (loc[0], loc[1], zb["T200"]), rot))
            k += 1
    for loc, rot in CORNERS + GATE_CORNERS:
        inst.append(place("SM_DK_WallFooting_Corner", loc, rot))
        off = Matrix.Rotation(math.radians(rot), 4, "Z") @ Vector((-1.0, 0.0, 0.0))
        inst.append(place("SM_DK_WallBody_1m_T200", (loc[0] + off.x, loc[1] + off.y, FOOT_H), rot))
        inst.append(place("SM_DK_WallCap_Corner", (loc[0], loc[1], zb["T200"]), rot))
    for piece, loc, rot in PIERS:
        inst.append(place(piece, loc, rot))
    inst.append(place("SM_DK_Gate_Frame", tuple(GC), 0.0))
    inst.append(place("SM_DK_Gate_Roof", tuple(GC), 0.0))
    inst.append(place("SM_DK_Gate_Paving", tuple(GC), 0.0))
    inst.append(place("SM_DK_Gate_Leaf_L", *LEAF_CLOSED[0]))
    inst.append(place("SM_DK_Gate_Leaf_R", *LEAF_CLOSED[1]))
    for loc, rot in LAMPS:
        inst.append(place("SM_DK_Gate_Lamp", loc, rot))
    return inst


def route6_update(L, roof):
    """Route 6 on the plain gable (f1 direction: the grey-box way, a flat landing at the eave; the roof form stays the
    sheet's): south wall top +2.0 -> round the gate corner and north along the return wall top (+2.0) -> 1.25 mantle
    onto the stepped block (+3.25, 1 x 1 m, at the gatehouse's courtyard eave corner, as onto the grey-box pier) ->
    walk east onto the N eave corner (+3.25 at y 2.5; +3.34 where the runner steps on, y 2.3) -> the N slope. The step
    block's traversal marker is the block itself (1.0 m ledge facing the return wall, 1.0 m deep)."""
    wx = [GC.x - 5.0 + v for v in STEP_X]              # west step block, world x (17 + local)
    ex = [GC.x + 5.0 - v for v in reversed(STEP_X)]    # east, mirrored
    markers = [m for m in L["traversal_markers"] if m["name"] not in ("Landing_GateRidge_W", "Landing_GateRidge_E")]
    pier_boxes = {"Landing_Pier_GW": [round(wx[0], 4), round(wx[1], 4), STEP_Y[0], STEP_Y[1], 0, PIER_TOP],
                  "Landing_Pier_GE": [round(ex[0], 4), round(ex[1], 4), STEP_Y[0], STEP_Y[1], 0, PIER_TOP],
                  "Landing_Pier_SW": [-1.2, 0.2, 26.4, 27.4, 0, PIER_TOP], "Landing_Pier_SE": [43.8, 45.2, 26.4, 27.4, 0, PIER_TOP]}
    for m in markers:
        if m["name"] in pier_boxes:
            m["box"] = pier_boxes[m["name"]]
            if m["name"] in ("Landing_Pier_GW", "Landing_Pier_GE"):
                m["note"] = ("gate step block +3.25 at the gatehouse's courtyard eave corner (mantle 1.25 from the "
                             "return wall top)")
    L["traversal_markers"] = markers
    y_step = 2.30                                        # where the runner steps off the block onto the eave corner
    z_step = round(zcol_s(y_step), 4)
    cw, ce = (wx[0] + wx[1]) / 2, (ex[0] + ex[1]) / 2
    routes = [r for r in L["climb_routes"] if r["route"] != "6"]
    routes.append({"route": "6", "step": "return wall top (+2.0) -> gate step block +3.25 (west)",
                   "stance": [round(cw, 3), 1.55], "floor_z": 2.0, "face": [0, 1], "marker": "Landing_Pier_GW"})
    routes.append({"route": "6", "step": "return wall top (+2.0) -> gate step block +3.25 (east)",
                   "stance": [round(ce, 3), 1.55], "floor_z": 2.0, "face": [0, 1], "marker": "Landing_Pier_GE"})
    for side, x in (("west", cw), ("east", ce)):
        routes.append({"route": "6", "step": f"gate step block -> gatehouse courtyard eave corner ({side})",
                       "stance": [round(x, 3), y_step], "floor_z": PIER_TOP, "face": [1 if side == "west" else -1, 0],
                       "marker": None, "walk_to": z_step,
                       "note": "step onto the N slope plane at y 2.3 (roof_walk_check.json replays it on the hulls)"})
    L["climb_routes"] = routes
    # the wall-top runs now go round the gate corners and up the return walls to the mantle stance
    L["walk_routes"]["south_wall_top_run_west"] = {"floor_z": 2.0, "points": [[-0.5, -0.5], [17.5, -0.5], [17.5, 1.55]]}
    L["walk_routes"]["south_wall_top_run_east"] = {"floor_z": 2.0, "points": [[44.5, -0.5], [26.5, -0.5], [26.5, 1.55]]}
    L["walk_routes"]["CONTROL_wall_top_into_gate_pier"] = {"floor_z": 2.0, "points": [[15.0, -0.5], [18.6, -0.5]]}
    L["walk_routes"]["CONTROL_step_pier_under_the_verge"] = {"floor_z": 2.0, "points": [[26.5, -0.5], [25.4, -0.5]]}
    L["walk_routes"]["CONTROL_return_wall_top_into_the_step_block"] = {"floor_z": 2.0,
                                                                       "points": [[17.5, 1.0], [17.5, 2.4]]}
    L["walk_routes"]["gate_open_passage_street_to_courtyard"] = {"floor_z": 0.0, "points": [[22.0, -3.6], [22.0, 3.0]],
                                                                 "leaves": "open", "note": "run with the open leaves"}


# ------------------------------------------------------------------------------------------------ main
REPLACED = {"SM_DGB_Wall_S_W1", "SM_DGB_Wall_S_W2", "SM_DGB_Wall_S_E1", "SM_DGB_Wall_S_E2", "SM_DGB_Wall_W_S",
            "SM_DGB_Wall_W_N", "SM_DGB_Wall_E_S", "SM_DGB_Wall_E_N", "SM_DGB_Wall_N", "SM_DGB_Landing_Pier",
            "SM_DGB_Gatehouse", "SM_DGB_Gate_Leaves", "SM_DGB_Gatehouse_Roof"}


def main():
    t0 = time.time()
    assert_owner("DojoKit", "claude")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    grey_layout_path = WORK / "layout_greybox.json"
    if not grey_layout_path.exists():
        raise SystemExit("layout_greybox.json missing (run build_dojo_greybox.py first)")
    GL = json.loads(grey_layout_path.read_text(encoding="utf-8"))
    for name in MATERIALS:
        build_material(name)
    kit = bpy.data.collections.new("Kit")
    sc.collection.children.link(kit)
    asm = bpy.data.collections.new("Assembly")
    sc.collection.children.link(asm)
    keep = [n for n in GL["pieces"] if n not in REPLACED]
    with bpy.data.libraries.load(str(GREY_BLEND), link=False) as (src, dst):
        wanted = set(keep)
        dst.objects = [n for n in src.objects if n in wanted or any(n.startswith(f"UCX_{k}_") for k in wanted)]
    for o in dst.objects:
        kit.objects.link(o)
    objs = {n: bpy.data.objects[n] for n in keep}
    WP, zb = wall_pieces()
    roof = gate_roof()
    lamp = gate_lamp()
    P = WP + [gate_frame(), roof] + gate_leaves() + [lamp, gate_paving()]
    build_stats = {}
    for p in P:
        t1 = time.time()
        o, bad = build_mesh(p, kit)
        objs[p.name] = o
        build_stats[p.name] = {"tris": sum(len(pl.vertices) - 2 for pl in o.data.polygons), "bad_faces": bad,
                               "sec": round(time.time() - t1, 2)}
        print("BUILT", p.name, build_stats[p.name])
    # STYLE_GUIDE 7: Nanite on every opaque static piece over about 2k triangles
    for p in P:
        if build_stats[p.name]["tris"] >= 2000 and p.name != "SM_DK_Gate_Lamp":
            p.nanite = True
            objs[p.name]["nanite"] = True
    kit.hide_render = True
    kit.hide_viewport = True
    inst = [dict(i) for i in GL["instances"] if i["piece"] not in REPLACED]
    k1 = kit1_instances(zb)
    pieces_k1 = {p.name: p for p in P}
    for it in k1:
        p = pieces_k1[it["piece"]]
        it.update({"folder": p.folder, "collision_class": p.cls, "note": p.note})
    inst += k1
    for n, it in enumerate(inst):
        o = bpy.data.objects.new(f"{it['piece']}__{n:03d}", objs[it["piece"]].data)
        o.matrix_world = Matrix.Translation(it["loc"]) @ Matrix.Rotation(math.radians(it.get("rot_z", 0.0)), 4, "Z")
        asm.objects.link(o)
        if it["collision_class"] == "boundary":
            o.hide_render = True
        pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
        it["bbox_min_max"] = [round(min(q[i] for q in pts), 4) for i in range(3)] + \
                             [round(max(q[i] for q in pts), 4) for i in range(3)]
    L = dict(GL)
    L["pieces"] = {k: v for k, v in GL["pieces"].items() if k not in REPLACED}
    for p in P:
        o = objs[p.name]
        L["pieces"][p.name] = {"class": p.cls, "folder": p.folder, "note": p.note, "ucx": len(p.hulls),
                               "tris": build_stats[p.name]["tris"], "slots": [m.name for m in o.data.materials],
                               "nanite": p.nanite, "kit": "kit1", **({"extra": p.extra} if p.extra else {})}
    L["instances"] = inst
    L["materials_kit1"] = {k: {"texture": v[0], "tile_m": v[1], "params": v[2],
                               "textures": ([f"Exports/DojoKit/Kit1/Textures/T_DK_{v[0]}_{s}.png" for s in ("BC", "N", "ORM")]
                                            if v[0] else [])} for k, v in MATERIALS.items()}
    route6_update(L, roof)
    L["kit1"] = {
        "date": "2026-09-27", "round": "f1",
        "cap_height_m": round(CAP_H, 4), "cap_visual_top_m": round(CD["visual_top"], 4),
        "cap_pitch_deg": round(math.degrees(CAP_TH), 2), "cap_noshi0_m": round(CD["noshi0"], 4), "cap_noshi_h_m": NOSHI_H,
        "cap_ridge_roll_above_walk_plane_m": CAP_SINK,
        "gate_returns": {"W": {"piece": "SM_DK_Wall_GateReturn_W", "corner": list(GATE_CORNERS[0]),
                               "step_world_x": [round(GC.x - 5.0 + v, 4) for v in STEP_X],
                               "step_world_y": list(STEP_Y), "step_top": PIER_TOP,
                               "return_world_x": [17.0, 18.0], "return_world_y": [0.0, RET_L],
                               "join_world_x": [round(GC.x - 5.0 + v, 4) for v in JOIN_X], "join_top": JOIN_TOP},
                         "E": {"piece": "SM_DK_Wall_GateReturn_E", "corner": list(GATE_CORNERS[1]),
                               "step_world_x": [round(GC.x + 5.0 - v, 4) for v in reversed(STEP_X)],
                               "step_world_y": list(STEP_Y), "step_top": PIER_TOP,
                               "return_world_x": [26.0, 27.0], "return_world_y": [0.0, RET_L],
                               "join_world_x": [round(GC.x + 5.0 - v, 4) for v in reversed(JOIN_X)],
                               "join_top": JOIN_TOP}},
        "frame_pier": {"piece": "SM_DK_Wall_FramePier", "placed": False,
                       "note": "kit piece for the BR wall openings; the wickets are solid wall in the 1v1"},
        "cap_eave_overhang_m": CAP_OVER, "body_top_z": zb, "wall_tops": TOPS, "footing_h": FOOT_H,
        "wall_variants": {k: [{"piece": "SM_DK_WallFooting_4m", "z": 0.0},
                              {"piece": f"SM_DK_WallBody_4m_{k}", "z": FOOT_H},
                              {"piece": "SM_DK_WallCap_4m", "z": zb[k]}] for k in TOPS},
        "gate_leaf_placements": {
            "closed": [place("SM_DK_Gate_Leaf_L", *LEAF_CLOSED[0]), place("SM_DK_Gate_Leaf_R", *LEAF_CLOSED[1])],
            "open": [place("SM_DK_Gate_Leaf_L", *LEAF_OPEN[0]), place("SM_DK_Gate_Leaf_R", *LEAF_OPEN[1])]},
        "gate_leaf": {"hinge_local": [HINGE_X, HINGE_Y, LEAF_Z], "width": LEAF_W, "height": LEAF_H,
                      "thickness_total": LEAF_TT},
        "lamp_lights_world": [[round(c, 4) for c in lamp_light_world(loc, rot, lamp.extra["light_local"])]
                              for loc, rot in LAMPS],
        "gate_roof": {"form": "kirizuma (plain gable)", "eave": GATE_EAVE, "ridge_planes_meet": round(ZR, 4),
                      "gable_x_local": GP, "verge_x_local": GX, "pitch_deg": 25.0, **roof.extra},
        "replaced_greybox": sorted(REPLACED),
    }
    K1.mkdir(parents=True, exist_ok=True)
    tmp = WORK / "layout.json.kit1tmp"
    tmp.write_text(json.dumps(L, indent=1), encoding="utf-8")
    import os
    os.replace(tmp, WORK / "layout.json")          # atomic: parallel stages read the grey-box positions from it
    (K1 / "layout_kit1.json").write_text(json.dumps({"pieces": {k: v for k, v in L["pieces"].items() if v.get("kit") == "kit1"},
                                                     "instances": k1, "materials": L["materials_kit1"], "kit1": L["kit1"]},
                                                    indent=1), encoding="utf-8")
    qa = {}
    waive = {"uv0_tile_range", "uv_no_overlap"}
    for p in P:
        o = objs[p.name]
        r = qa_check([o], require_uv1=True, texel_density=5.12, tolerance=0.25)
        fails = [c for c in r["checks"] if not c["passed"]]
        hard = [c for c in fails if c["name"] not in waive]
        tex = next((c["detail"] for c in r["checks"] if c["name"] == "texel_density"), "")
        qa[p.name] = {"hard_fails": hard, "waived": sorted({c["name"] for c in fails if c["name"] in waive}),
                      "tris": r["triangles"].get(p.name), "texel": tex}
    hard_total = sum(len(v["hard_fails"]) for v in qa.values())
    print(f"QA kit1: {len(P)} pieces, hard fails {hard_total}")
    for k, v in qa.items():
        for c in v["hard_fails"]:
            print("  FAIL", k, c["name"], str(c["detail"])[:220])
    exp = {}
    if "--no-export" not in ARGS and hard_total == 0:
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        kit.hide_viewport = False
        for p in P:
            o = objs[p.name]
            tris = qa[p.name]["tris"]
            if "--no-lods" in ARGS or tris < 400:
                r = export_fbx(str(EXPORT_DIR / f"{p.name}.fbx"), [o], kind="static", sidecar=False)
                exp[p.name] = {"lods": 1, "lod_tris": [tris], "warnings": r["warnings"], "objects": r["objects"]}
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
                fix_lod(lo)
            grp = make_lod_group(p.name, [c0] + lods)
            lq = qa_check([c0] + lods, require_uv1=True, require_ucx=False)
            lod_hard = [c for c in lq["checks"] if not c["passed"] and c["name"] not in waive]
            r = export_fbx(str(EXPORT_DIR / f"{p.name}.fbx"), [grp], kind="static", sidecar=True)
            exp[p.name] = {"lods": 3, "lod_tris": [lq["triangles"].get(x.name) for x in [c0] + lods],
                           "lod_qa_fails": [(c["name"], c["object"], str(c["detail"])[:120]) for c in lod_hard],
                           "screen_sizes": r.get("lod_screen_sizes"), "warnings": r["warnings"]}
            for ob in list(tmpc.objects):
                bpy.data.objects.remove(ob, do_unlink=True)
            bpy.data.collections.remove(tmpc)
        kit.hide_viewport = True
        (K1 / "export_report.json").write_text(json.dumps(exp, indent=1, default=str), encoding="utf-8")
        print(f"exported {len(exp)} FBX to {EXPORT_DIR}")
    (K1 / "qa_report.json").write_text(json.dumps(qa, indent=1, default=str), encoding="utf-8")
    rep = {"pieces": {p.name: {"class": p.cls, "tris": build_stats[p.name]["tris"], "nanite": p.nanite,
                               "ucx": len(p.hulls), "slots": [m.name for m in objs[p.name].data.materials],
                               "lods": exp.get(p.name, {}).get("lod_tris")} for p in P},
           "tris_total_unique": sum(build_stats[p.name]["tris"] for p in P),
           "instances_kit1": len(k1), "instances_total": len(inst), "cap_h": CAP_H, "body_top_z": zb,
           "bad_faces": {k: v["bad_faces"] for k, v in build_stats.items() if v["bad_faces"]},
           "qa_hard_fails": hard_total, "seconds": round(time.time() - t0, 1)}
    (K1 / "kit1_report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    BLEND.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    print("saved", BLEND, "seconds", rep["seconds"])


main()
