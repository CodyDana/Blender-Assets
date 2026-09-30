"""Dojo courtyard arena GREY-BOX (WorkFiles/world/DOJO_ARENA_SPEC.md, true scale, simple blocks, flat collision).

Builds every grey-box piece at the origin (collection "Kit", UCX_ collision children, pivot at the piece's minimum corner),
an assembled compound from the placement table (collection "Assembly", linked copies at the pivots), writes
WorkFiles/dojo/build/layout.json (pieces, instances with folder + collision class, materials, GASP traversal markers,
player starts, sun, cameras, walk and climb routes), runs the pipeline QA, exports each piece through Scripts/pipeline
(Exports/DojoKit/SM_DGB_*.fbx) and saves Assets/Dojo/DojoGreybox.blend.

Frame (spec section 1): metres, origin = the inside south-west corner of the compound at courtyard level, X east (0-44),
Y north (0-36), Z up. Unreal: (x*100, -y*100, z*100), yaw = -rot_z (every grey-box instance has rot_z 0).

Grey-box deviations from the spec (measured reasons in WorkFiles/dojo/build/GASP_TRAVERSAL.md, flagged in BUILD_NOTES.md):
  * GASP cannot mantle onto a sloped roof edge: its top sweep (a capsule 2 cm above the ledge, Visibility channel) hits a
    25 degree slope about 0.10 m in, so the obstacle depth is < 0.59 m, the back ledge is invalidated and no chooser row
    matches. Every route that ends on an eave therefore arrives on a flat LANDING (yellow): wall-line piers at +3.25 next
    to the gatehouse and the storehouse / residence (routes 2 and 6), 0.75 m deep pads at the lower eave above the
    cisterns (route 4) and at the pavilion eave (route 7), a 0.75 m flat front band on the shed lean-to (route 7).
  * Route 5: the AC unit top is +5.10 (spec +4.75) so the last rise onto the upper eave is a 0.40 m walk-up step (CMC step
    height 0.45 m); the AC stands entirely outside the upper eave line (1.0 m deep).
  * The gatehouse roof is hipped at the sides (eaves on all four sides at +3.25, ridge +4.4) so the wall-top runner reaches
    an eave (route 6); the sheet's plain gable would put the verge 2.2-2.4 m above the wall top.
  * The storehouse / residence roofs extend over the perimeter wall (X -1 / 45), whose top they sit on.
Run: blender -b --factory-startup --python Scripts/dojo/build_dojo_greybox.py -- [--no-export]
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Scripts"))
from pipeline.export_fbx import export_fbx  # noqa: E402
from pipeline.qa_check import qa_check  # noqa: E402
from pipeline.lock import assert_owner  # noqa: E402

EXPORT_DIR = ROOT / "Exports" / "DojoKit"
WORK = ROOT / "WorkFiles" / "dojo" / "build"
BLEND = ROOT / "Assets" / "Dojo" / "DojoGreybox.blend"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
TILE = 2.0   # UV0 world tile (flat colours: the UV only has to exist)

# ------------------------------------------------------------------------------------------------ spec numbers
# every height below is the spec's (DOJO_ARENA_SPEC section 4) unless a comment says otherwise
WALL_TOP = 2.0
GATE_OPEN = (20.0, 24.0, 3.5)            # X from, X to, clear height
GATE_EAVE, GATE_RIDGE = 3.25, 4.4
GATE_ROOF = (18.0, 26.0, -2.5, 2.5)      # X 18-26, Y -2.5..2.5 (spec 8 x 5 m; the posts stand 3.5 m apart in Y)
VERANDA_Z = 0.5
LOWER_EAVE, LOWER_TOP = 3.0, 4.17        # lower roof: eave +3.0 at Y 21.5 / X 10.5 / 33.5, +4.17 at the hall wall
UPPER_EAVE, UPPER_RIDGE = 5.5, 8.3
OUT_EAVE, OUT_RIDGE = 3.25, 5.25         # storehouse / residence
CORR_EAVE, CORR_RIDGE = 3.0, 3.7
SHED_BACK, SHED_FRONT = 3.0, 2.5
PAV_EAVE, PAV_APEX, PAV_PLINTH = 3.25, 4.5, 1.0
CISTERN_TOP, CRATE_TOP, VENDING_TOP = 1.25, 1.25, 1.75
AC_TOP = 5.10                            # DEVIATION: spec 4.75 (see the docstring)
LANDING_DEPTH = 0.75                     # measured need >= 0.49 m of flat before a 25 deg slope (GASP_TRAVERSAL.md)
SLAB = 0.2                               # roof slab thickness (collision = one flat plane per slope)
P1, P2 = (14.5, 10.5), (29.5, 10.5)


def lower_front_z(y):
    return LOWER_EAVE + (y - 21.5) * (LOWER_TOP - LOWER_EAVE) / 2.5


def srgb_to_lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


# grey-box colours per class (sRGB hex; STYLE_GUIDE palette where one exists)
MATERIALS = {
    "M_DGB_Sand": "#B3A791", "M_DGB_Path": "#7F7B76", "M_DGB_Gravel": "#9C9486", "M_DGB_Outside": "#5E6B4A",
    "M_DGB_Wall": "#A88D6A", "M_DGB_Plaster": "#D9CFBD", "M_DGB_Timber": "#3A2E26", "M_DGB_Veranda": "#9C8466",
    "M_DGB_Stone": "#8A8680", "M_DGB_RoofHall": "#55585C", "M_DGB_RoofLower": "#6A6E74", "M_DGB_RoofOut": "#62666B",
    "M_DGB_Steel": "#A7AAAD", "M_DGB_ClimbProp": "#D98A2B", "M_DGB_Landing": "#E6C229", "M_DGB_Modern": "#4E7C7A",
    "M_DGB_Thin": "#7A6A58", "M_DGB_Trunk": "#4A3A2A", "M_DGB_Canopy": "#4F5A35", "M_DGB_Boundary": "#C0392B",
    "M_DGB_Fence": "#6B4E3A", "M_DGB_Drum": "#8E1F1F",
}

# collision classes (spec 5.3) -> Unreal responses, applied per actor by dj_level.py
COLLISION = {
    "ground":    {"pawn": "block", "camera": "block", "visibility": "block"},
    "building":  {"pawn": "block", "camera": "block", "visibility": "block"},
    "roof":      {"pawn": "block", "camera": "block", "visibility": "block"},
    "climbprop": {"pawn": "block", "camera": "ignore", "visibility": "block"},
    "landing":   {"pawn": "block", "camera": "block", "visibility": "block"},
    "thin":      {"pawn": "block", "camera": "ignore", "visibility": "ignore"},
    "tree":      {"pawn": "block", "camera": "ignore", "visibility": "ignore"},
    "boundary":  {"pawn": "block", "camera": "ignore", "visibility": "ignore", "hidden_in_game": True},
}


# ------------------------------------------------------------------------------------------------ geometry parts
def box_part(x0, x1, y0, y1, z0, z1):
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (3, 0, 4, 7), (1, 2, 6, 5)]
    return v, f


def prism_part(top, t=SLAB):
    """A slab under a planar top polygon (counter-clockwise seen from above), extruded straight down by t."""
    n = len(top)
    v = [tuple(p) for p in top] + [(p[0], p[1], p[2] - t) for p in top]
    f = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
    for i in range(n):
        j = (i + 1) % n
        f.append((n + i, n + j, j, i))
    return v, f


def gable_part(x0, x1, y0, y1, z0, zr):
    """A solid triangular prism along X (gable wall fill): base Y y0..y1 at z0, ridge at the middle at zr."""
    ym = (y0 + y1) / 2
    v = [(x0, y0, z0), (x0, y1, z0), (x0, ym, zr), (x1, y0, z0), (x1, y1, z0), (x1, ym, zr)]
    f = [(0, 2, 1), (3, 4, 5), (0, 3, 5, 2), (1, 2, 5, 4), (0, 1, 4, 3)]
    return v, f


def cyl_part(cx, cy, z0, z1, r, sides=16):
    v, f = [], []
    for i in range(sides):
        a = 2 * math.pi * i / sides
        v += [(cx + r * math.cos(a), cy + r * math.sin(a), z0), (cx + r * math.cos(a), cy + r * math.sin(a), z1)]
    v += [(cx, cy, z0), (cx, cy, z1)]
    c0, c1 = 2 * sides, 2 * sides + 1
    for i in range(sides):
        j = (i + 1) % sides
        f.append((2 * i, 2 * j, 2 * j + 1, 2 * i + 1))
        f.append((c0, 2 * j, 2 * i))
        f.append((c1, 2 * i + 1, 2 * j + 1))
    return v, f


class Piece:
    """World-space parts and hulls -> one mesh with a pivot at its minimum corner, UV0 / UV1 and UCX hulls."""
    count = 0

    def __init__(self, name, cls, folder, note=""):
        self.name, self.cls, self.folder, self.note = name, cls, folder, note
        self.parts = []      # (verts, faces, material)
        self.hulls = []      # point lists (world)
        self.offsets = [(0.0, 0.0, 0.0)]   # extra instances: translation of the whole piece

    def box(self, x0, x1, y0, y1, z0, z1, mat, col=True):
        self.parts.append(box_part(x0, x1, y0, y1, z0, z1) + (mat,))
        if col:
            self.hulls.append(box_part(x0, x1, y0, y1, z0, z1)[0])
        return self

    def prism(self, top, mat, t=SLAB, col=True):
        p = prism_part(top, t)
        self.parts.append(p + (mat,))
        if col:
            self.hulls.append(p[0])
        return self

    def gable(self, x0, x1, y0, y1, z0, zr, mat, col=True):
        p = gable_part(x0, x1, y0, y1, z0, zr)
        self.parts.append(p + (mat,))
        if col:
            self.hulls.append(p[0])
        return self

    def cyl(self, cx, cy, z0, z1, r, mat, col=True, sides=16):
        p = cyl_part(cx, cy, z0, z1, r, sides)
        self.parts.append(p + (mat,))
        if col:
            self.hulls.append(p[0][:2 * sides])
        return self

    def also_at(self, dx, dy, dz=0.0):
        self.offsets.append((dx, dy, dz))
        return self

    def pivot(self):
        pts = [p for v, _f, _m in self.parts for p in v]
        return tuple(round(min(p[i] for p in pts), 3) for i in range(3))

    def build(self, coll):
        pv = Vector(self.pivot())
        mats = []
        bm = bmesh.new()
        uv = bm.loops.layers.uv.new("UV0")
        for verts, faces, m in self.parts:
            Piece.count += 1
            g = 0.0003 + (Piece.count % 997) * 2e-6   # unique growth: abutting parts never share coincident vertices
            c = Vector([sum(p[i] for p in verts) / len(verts) for i in range(3)])
            ext = max(max(p[i] for p in verts) - min(p[i] for p in verts) for i in range(3))
            k = 1.0 + 2.0 * g / max(ext, 1e-3)
            bv = [bm.verts.new(c + (Vector(p) - c) * k - pv) for p in verts]
            if m not in mats:
                mats.append(m)
            for fi in faces:
                face = bm.faces.new([bv[i] for i in fi])
                face.material_index = mats.index(m)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])   # every part is a closed shell: normals point out
        bm.normal_update()
        for face in bm.faces:
            n = face.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            a, b = [i for i in range(3) if i != ax]
            for loop in face.loops:
                co = loop.vert.co + pv
                loop[uv].uv = (co[a] / TILE, co[b] / TILE)
        mesh = bpy.data.meshes.new(self.name)
        bm.to_mesh(mesh)
        bm.free()
        for m in mats:
            mesh.materials.append(bpy.data.materials[m])
        obj = bpy.data.objects.new(self.name, mesh)
        coll.objects.link(obj)
        add_uv1(obj)
        for i, pts in enumerate(self.hulls):
            hb = bmesh.new()
            vs = [hb.verts.new(Vector(p) - pv) for p in pts]
            bmesh.ops.convex_hull(hb, input=vs)
            for v in [v for v in hb.verts if not v.link_faces]:
                hb.verts.remove(v)
            hm = bpy.data.meshes.new(f"UCX_{self.name}_{i:02d}")
            hb.to_mesh(hm)
            hb.free()
            h = bpy.data.objects.new(f"UCX_{self.name}_{i:02d}", hm)
            coll.objects.link(h)
            h.parent = obj
            h.hide_render = True
            h.display_type = "WIRE"
        return obj


def add_uv1(obj):
    me = obj.data
    me.uv_layers.new(name="UV1")
    me.uv_layers.active_index = 1
    with bpy.context.temp_override(active_object=obj, object=obj, selected_objects=[obj], selected_editable_objects=[obj]):
        bpy.ops.uv.lightmap_pack(PREF_CONTEXT="ALL_FACES", PREF_PACK_IN_ONE=False, PREF_NEW_UVLAYER=False,
                                 PREF_BOX_DIV=12, PREF_MARGIN_DIV=0.2)
    me.uv_layers.active_index = 0


# ------------------------------------------------------------------------------------------------ the compound
def hip_roof(pc, x0, x1, y0, y1, eave, ridge, mat, ridge_along_x=True):
    """Four slabs: two trapezoids and two hip triangles, equal run on every side (a hip roof)."""
    if ridge_along_x:
        run = (y1 - y0) / 2.0
        ym = (y0 + y1) / 2.0
        rx0, rx1 = x0 + run, x1 - run
        pc.prism([(x0, y0, eave), (x1, y0, eave), (rx1, ym, ridge), (rx0, ym, ridge)], mat)          # south
        pc.prism([(x1, y1, eave), (x0, y1, eave), (rx0, ym, ridge), (rx1, ym, ridge)], mat)          # north
        pc.prism([(x0, y1, eave), (x0, y0, eave), (rx0, ym, ridge)], mat)                            # west hip
        pc.prism([(x1, y0, eave), (x1, y1, eave), (rx1, ym, ridge)], mat)                            # east hip
    return pc


def gable_roof_x(pc, x0, x1, y0, y1, eave, ridge, mat):
    """Two slabs, ridge along X at the middle of Y."""
    ym = (y0 + y1) / 2.0
    pc.prism([(x0, y0, eave), (x1, y0, eave), (x1, ym, ridge), (x0, ym, ridge)], mat)
    pc.prism([(x1, y1, eave), (x0, y1, eave), (x0, ym, ridge), (x1, ym, ridge)], mat)
    return pc


def pieces():
    P = []
    add = lambda p: (P.append(p), p)[1]   # noqa: E731
    z0 = -0.2
    # ---- ground zones (flat colour zones, one flat UCX per rectangle)
    add(Piece("SM_DGB_Floor_Fight", "ground", "Ground", "28 x 17 m raked-sand fight floor, dead flat")
        .box(8, 21, 2, 19, z0, 0, "M_DGB_Sand").box(23, 36, 2, 19, z0, 0, "M_DGB_Sand"))
    add(Piece("SM_DGB_Floor_Path", "ground", "Ground", "flush stone path gate -> hall steps")
        .box(21, 23, 0, 21.4, z0, 0, "M_DGB_Path"))
    yard = Piece("SM_DGB_Floor_Yards", "ground", "Ground", "gravel yards round the floor")
    for r in ((0, 21, 0, 2), (23, 44, 0, 2), (0, 8, 2, 36), (36, 44, 2, 36), (8, 21, 19, 36), (23, 36, 19, 36),
              (21, 23, 21.4, 36)):
        yard.box(r[0], r[1], r[2], r[3], z0, 0, "M_DGB_Gravel")
    add(yard)
    out = Piece("SM_DGB_Ground_Outside", "ground", "Ground", "outside the walls (out of bounds in the 1v1)")
    for r in ((-15, 59, -15, -1), (-15, 59, 37, 51), (-15, -1, -1, 37), (45, 59, -1, 37)):
        out.box(r[0], r[1], r[2], r[3], z0, 0, "M_DGB_Outside")
    add(out)
    # ---- perimeter wall (top +2.0, 1.0 thick, flat walkable top). Split round the landing piers and the gate.
    for name, r in (("S_W1", (-1, 17, -1, 0)), ("S_W2", (18, 19.7, -1, 0)), ("S_E1", (24.3, 26, -1, 0)),
                    ("S_E2", (27, 45, -1, 0)), ("W_S", (-1, 0, 0, 26.4)), ("W_N", (-1, 0, 27.4, 36)),
                    ("E_S", (44, 45, 0, 26.4)), ("E_N", (44, 45, 27.4, 36)), ("N", (-1, 45, 36, 37))):
        add(Piece(f"SM_DGB_Wall_{name}", "building", "Wall", "perimeter wall run, top +2.0")
            .box(r[0], r[1], r[2], r[3], 0, WALL_TOP, "M_DGB_Wall"))
    # ---- landings (DEVIATION, flagged): wall-line piers whose flat top is flush with the eave they lead to
    add(Piece("SM_DGB_Landing_Pier", "landing", "Landings", "1 x 1 m wall pier, top +3.25 (routes 2 and 6)")
        .box(17, 18, -1, 0, 0, GATE_EAVE, "M_DGB_Landing").also_at(9, 0).also_at(-18, 27.4).also_at(27, 27.4))
    # ---- gatehouse (hipped roof, eave +3.25, ridge +4.4, opening 4.0 x 3.5 m)
    gh = Piece("SM_DGB_Gatehouse", "building", "Gatehouse", "gatehouse frame: posts, door posts, lintel, threshold")
    for x in (19.2, 24.4):
        for y in (-1.95, 1.55):
            gh.box(x, x + 0.4, y, y + 0.4, 0, 3.40, "M_DGB_Timber")
    gh.box(19.7, 20.0, -1, 0, 0, 3.9, "M_DGB_Timber").box(24.0, 24.3, -1, 0, 0, 3.9, "M_DGB_Timber")
    gh.box(20.0, 24.0, -1, 0, 3.5, 3.9, "M_DGB_Timber")
    gh.box(20.0, 24.0, -1, 0, 0, 0.1, "M_DGB_Stone")
    add(gh)
    add(Piece("SM_DGB_Gate_Leaves", "building", "Gatehouse", "iron-strapped double doors, CLOSED in the 1v1")
        .box(20.0, 24.0, -0.6, -0.4, 0.1, GATE_OPEN[2], "M_DGB_Timber"))
    add(hip_roof(Piece("SM_DGB_Gatehouse_Roof", "roof", "Gatehouse", "hipped roof 8 x 5 m, eave +3.25, ridge +4.4"),
                 *GATE_ROOF, GATE_EAVE, GATE_RIDGE, "M_DGB_RoofHall"))
    # ---- dojo hall
    add(Piece("SM_DGB_Hall_Veranda", "ground", "Hall", "veranda (engawa) floor +0.5, front and sides")
        .box(11, 33, 21.7, 34, 0, VERANDA_Z, "M_DGB_Veranda"))
    add(Piece("SM_DGB_Hall_StepBand", "ground", "Hall", "stone step band, 0.25 m riser (the veranda front is the 2nd)")
        .box(11, 33, 21.4, 21.7, 0, 0.25, "M_DGB_Stone"))
    hb = Piece("SM_DGB_Hall_Body", "building", "Hall", "hall body 18 x 10 m, closed in the 1v1")
    hb.box(13, 31, 24, 34, VERANDA_Z, 5.7, "M_DGB_Plaster")
    for x in (16, 21, 26):
        hb.box(x, x + 2, 23.94, 24.0, VERANDA_Z, 2.5, "M_DGB_Timber", col=False)
    add(hb)
    lr = Piece("SM_DGB_Hall_RoofLower", "roof", "Hall", "lower roof, 25 deg, eave +3.0, +4.17 at the hall wall")
    lr.prism([(10.5, 21.5, LOWER_EAVE), (33.5, 21.5, LOWER_EAVE), (33.5, 24.0, LOWER_TOP), (10.5, 24.0, LOWER_TOP)],
             "M_DGB_RoofLower")
    lr.prism([(10.5, 34.0, LOWER_EAVE), (10.5, 21.5, LOWER_EAVE), (13.0, 21.5, LOWER_TOP), (13.0, 34.0, LOWER_TOP)],
             "M_DGB_RoofLower")
    lr.prism([(33.5, 21.5, LOWER_EAVE), (33.5, 34.0, LOWER_EAVE), (31.0, 34.0, LOWER_TOP), (31.0, 21.5, LOWER_TOP)],
             "M_DGB_RoofLower")
    add(lr)
    ur = hip_roof(Piece("SM_DGB_Hall_RoofUpper", "roof", "Hall", "upper roof, 25 deg hip, eave +5.5, ridge +8.3"),
                  12.1, 31.9, 23.1, 34.9, UPPER_EAVE, UPPER_RIDGE, "M_DGB_RoofHall")
    ur.box(18.0, 26.0, 28.85, 29.15, UPPER_RIDGE - 0.05, 8.7, "M_DGB_RoofHall", col=False)   # crest tiles to +8.7
    add(ur)
    # ---- outbuildings (gable roofs along X, extended over the perimeter wall they sit on)
    for name, bx, rx, door in (("Storehouse", (0.0, 7.0), (-1.0, 7.6), 3.0), ("Residence", (37.0, 44.0), (36.4, 45.0), 39.5)):
        o = Piece(f"SM_DGB_{name}", "building", "Outbuildings", f"{name.lower()}: body + gable fill, door closed")
        o.box(bx[0], bx[1], 28.0, 36.0, 0, 3.2, "M_DGB_Plaster")
        o.gable(bx[0], bx[1], 28.0, 36.0, 3.2, 5.0, "M_DGB_Plaster")
        o.box(door, door + 1.5, 27.94, 28.0, 0, 2.2, "M_DGB_Steel", col=False)
        add(o)
        add(gable_roof_x(Piece(f"SM_DGB_{name}_Roof", "roof", "Outbuildings", "gable roof, eave +3.25, ridge +5.25"),
                         rx[0], rx[1], 27.4, 36.0, OUT_EAVE, OUT_RIDGE, "M_DGB_RoofOut"))
    for name, fx, rx, x0w in (("W", (7.0, 11.0), (7.6, 10.5), 7.6), ("E", (33.0, 37.0), (33.5, 36.4), 33.5)):
        c = Piece(f"SM_DGB_Corridor_{name}", "building", "Outbuildings", "covered corridor: floor +0.5, north wall, posts")
        c.box(fx[0], fx[1], 29.5, 32.5, 0, VERANDA_Z, "M_DGB_Veranda")
        c.box(rx[0], rx[1], 32.3, 32.5, VERANDA_Z, 2.8, "M_DGB_Plaster")
        for x in (rx[0], rx[1] - 0.2):
            c.box(x, x + 0.2, 29.5, 29.7, VERANDA_Z, 2.8, "M_DGB_Timber")
        add(c)
        add(gable_roof_x(Piece(f"SM_DGB_Corridor_{name}_Roof", "roof", "Outbuildings", "corridor roof +3.0..+3.7"),
                         rx[0], rx[1], 29.5, 32.5, CORR_EAVE, CORR_RIDGE, "M_DGB_RoofOut"))
    # ---- training shed (SW): steel lean-to, +3.0 at the wall, +2.5 at the front; DEVIATION: flat 0.75 m front band
    sh = Piece("SM_DGB_Shed", "building", "Yard", "steel training shed: back wall, east wall, front posts")
    sh.box(0, 6, 0, 0.2, 0, SHED_BACK, "M_DGB_Steel").box(5.8, 6.0, 0.2, 4.25, 0, 2.3, "M_DGB_Steel")
    sh.box(0.0, 0.2, 4.8, 5.0, 0, 2.3, "M_DGB_Timber").box(5.8, 6.0, 4.8, 5.0, 0, 2.3, "M_DGB_Timber")
    add(sh)
    band_y = 5.0 - LANDING_DEPTH
    add(Piece("SM_DGB_Shed_Roof", "roof", "Yard", "lean-to roof +3.0 -> +2.5 with a flat 0.75 m front band (landing)")
        .prism([(0, 0, SHED_BACK), (6, 0, SHED_BACK), (6, band_y, SHED_FRONT), (0, band_y, SHED_FRONT)], "M_DGB_Steel")
        .prism([(0, band_y, SHED_FRONT), (6, band_y, SHED_FRONT), (6, 5.0, SHED_FRONT), (0, 5.0, SHED_FRONT)],
               "M_DGB_Landing"))
    # ---- drum pavilion (SE): plinth +1.0, pyramid roof eave +3.25, apex +4.5
    pv = Piece("SM_DGB_Pavilion", "building", "Yard", "drum pavilion: plinth +1.0, corner posts, drum")
    pv.box(39, 43, 1, 5, 0, PAV_PLINTH, "M_DGB_Stone")
    for x in (39.1, 42.6):
        for y in (1.1, 4.6):
            pv.box(x, x + 0.3, y, y + 0.3, PAV_PLINTH, 3.40, "M_DGB_Timber")
    pv.cyl(41.0, 3.0, PAV_PLINTH, 2.2, 0.6, "M_DGB_Drum")
    add(pv)
    pr = Piece("SM_DGB_Pavilion_Roof", "roof", "Yard", "pyramid roof, eave +3.25, apex +4.5")
    a = (41.0, 3.0, PAV_APEX)
    e = [(38.4, 0.4), (43.6, 0.4), (43.6, 5.6), (38.4, 5.6)]
    for i in range(4):
        p, q = e[i], e[(i + 1) % 4]
        pr.prism([(p[0], p[1], PAV_EAVE), (q[0], q[1], PAV_EAVE), a], "M_DGB_RoofHall")
    add(pr)
    # ---- climb props (orange / teal) and landings (yellow)
    add(Piece("SM_DGB_Cistern", "climbprop", "ClimbProps", "1.2 x 1.2 m wooden water tank, top +1.25 (route 4)")
        .box(13.05, 14.25, 19.3, 20.5, 0, CISTERN_TOP, "M_DGB_ClimbProp").also_at(16.7, 0))
    add(Piece("SM_DGB_Landing_EavePad", "landing", "Landings", "0.75 m pad at the lower eave +3.0 above a cistern")
        .box(13.05, 14.25, 21.5 - LANDING_DEPTH, 21.5, LOWER_EAVE - SLAB, LOWER_EAVE, "M_DGB_Landing").also_at(16.7, 0))
    ac_y0 = 22.1
    add(Piece("SM_DGB_ACUnit", "climbprop", "ClimbProps", "AC unit 1.2 x 1.0 m on the lower roof, top +5.10 (route 5)")
        .box(15.0, 16.2, ac_y0, 23.1, lower_front_z(ac_y0) - 0.1, AC_TOP, "M_DGB_Modern").also_at(12.8, 0))
    add(Piece("SM_DGB_Crate", "climbprop", "ClimbProps", "1.0 m crate, top +1.25 (route 7)")
        .box(2.5, 3.5, 5.3, 6.3, 0, CRATE_TOP, "M_DGB_ClimbProp").also_at(33.85, -2.8))
    add(Piece("SM_DGB_Landing_PavilionPad", "landing", "Landings", "0.75 m pad at the pavilion eave +3.25 (route 7)")
        .box(38.4 - LANDING_DEPTH, 38.4, 2.25, 3.75, PAV_EAVE - SLAB, PAV_EAVE, "M_DGB_Landing"))
    add(Piece("SM_DGB_Vending", "climbprop", "ClimbProps", "vending machine 0.9 x 0.8 m, top +1.75 (route 8)")
        .box(12.0, 12.9, 0.0, 0.8, 0, VENDING_TOP, "M_DGB_Modern"))
    # ---- yard dressing: low cover and thin uprights (rule R8)
    add(Piece("SM_DGB_WeaponRack", "thin", "Yard", "weapon rack 2.0 x 0.4 x 1.2 m (hurdle)")
        .box(3.8, 4.2, 7.5, 9.5, 0, 1.2, "M_DGB_Thin").also_at(36.0, 0))
    add(Piece("SM_DGB_TrainingPost", "thin", "Yard", "makiwara post 0.2 m square, 1.5 m")
        .box(6.4, 6.6, 13.9, 14.1, 0, 1.5, "M_DGB_Thin").also_at(0, -7).also_at(31, 0).also_at(31, -7))
    add(Piece("SM_DGB_Dummy", "thin", "Yard", "wooden training dummy 0.4 m, 1.7 m")
        .box(1.8, 2.2, 11.8, 12.2, 0, 1.7, "M_DGB_Thin").also_at(40, 0))
    add(Piece("SM_DGB_StoneLantern", "thin", "Yard", "stone lantern 0.6 m, 1.8 m, in front of the hall")
        .box(18.7, 19.3, 20.2, 20.8, 0, 1.8, "M_DGB_Stone").also_at(6, 0))
    add(Piece("SM_DGB_Well", "building", "Yard", "well, 1.5 m across, 0.8 m (low cover)")
        .cyl(41.0, 22.0, 0, 0.8, 0.75, "M_DGB_Stone"))
    add(Piece("SM_DGB_Tree", "tree", "Trees", "tree: trunk (collision) + canopy volume from +4.0 (no collision)")
        .box(3.25, 3.75, 15.75, 16.25, 0, 4.5, "M_DGB_Trunk").cyl(3.5, 16.0, 4.0, 7.5, 3.2, "M_DGB_Canopy", col=False)
        .also_at(37, 0))
    add(Piece("SM_DGB_AlleyFence", "building", "Boundary_1v1", "rear-alley fence, 2.0 m (1v1 only)")
        .box(10.5, 13.0, 34.0, 34.1, 0, 2.0, "M_DGB_Fence").also_at(20.5, 0))
    # ---- the 1v1 boundary: its own invisible Pawn-only blocker (spec 5.4), hidden in game
    b = Piece("SM_DGB_Boundary_1v1", "boundary", "Boundary_1v1", "invisible Pawn-only blockers of the 1v1 (spec 5.4)")
    for r in ((-1.1, 45.1, -1.1, -1.0, 0, 20), (-1.1, 45.1, 37.0, 37.1, 0, 20), (-1.1, -1.0, -1.0, 37.0, 0, 20),
              (45.0, 45.1, -1.0, 37.0, 0, 20), (-1.1, 45.1, -1.1, 37.1, 20, 20.1),        # outer ring + ceiling
              (12.1, 31.9, 29.0, 29.1, 5.3, 20),                                         # hall ridge (rear slope)
              (-1.0, 7.6, 31.7, 31.8, 3.0, 20), (36.4, 45.0, 31.7, 31.8, 3.0, 20),        # outbuilding ridges
              (7.6, 10.5, 31.0, 31.1, 3.0, 20), (33.5, 36.4, 31.0, 31.1, 3.0, 20),        # corridor ridges
              (7.6, 36.4, 36.0, 37.0, 2.0, 20)):                                         # north wall top
        b.box(*r, "M_DGB_Boundary")
    add(b)
    return P


# ------------------------------------------------------------------------------------------------ GASP traversal markers
def markers():
    """LevelBlock_Traversable boxes (GASP_TRAVERSAL.md): dj_level spawns one per entry, invisible, collision =
    Traversable channel only. Box = the climbable volume; its four top edges become GASP's ledges."""
    M = []
    m = lambda name, box, route, note: M.append({"name": name, "box": [round(v, 4) for v in box],   # noqa: E731
                                                 "route": route, "note": note})
    for name, r in (("Wall_S_W1", (-1, 17, -1, 0)), ("Wall_S_W2", (18, 19.7, -1, 0)), ("Wall_S_E1", (24.3, 26, -1, 0)),
                    ("Wall_S_E2", (27, 45, -1, 0)), ("Wall_W_S", (-1, 0, 0, 26.4)), ("Wall_W_N", (-1, 0, 27.4, 36)),
                    ("Wall_E_S", (44, 45, 0, 26.4)), ("Wall_E_N", (44, 45, 27.4, 36)), ("Wall_N", (-1, 45, 36, 37))):
        m(name, (*r, 0, WALL_TOP), "1", "wall top +2.0 (mantle 2.0 from the courtyard)")
    for i, (x, y) in enumerate(((17, -1), (26, -1), (-1, 26.4), (44, 26.4))):
        m(f"Landing_Pier_{'GW GE SW SE'.split()[i]}", (x, x + 1, y, y + 1, 0, GATE_EAVE), "6" if i < 2 else "2",
          "pier +3.25 (mantle 1.25 from the wall top)")
    for i, dx in enumerate((0, 16.7)):
        m(f"Cistern_{'WE'[i]}", (13.05 + dx, 14.25 + dx, 19.3, 20.5, 0, CISTERN_TOP), "4", "cistern +1.25")
        m(f"Landing_EavePad_{'WE'[i]}", (13.05 + dx, 14.25 + dx, 21.5 - LANDING_DEPTH, 21.5, CISTERN_TOP, LOWER_EAVE), "4",
          "pad at the lower eave +3.0 (mantle 1.75 from the cistern)")
        m(f"ACUnit_{'WE'[i * 1]}", (15.0 + 12.8 * i, 16.2 + 12.8 * i, 22.1, 23.1, lower_front_z(22.1) - 0.1, AC_TOP), "5",
          "AC top +5.10 (mantle about 1.95 from the lower roof)")
    m("Crate_Shed", (2.5, 3.5, 5.3, 6.3, 0, CRATE_TOP), "7", "crate +1.25")
    m("Crate_Pavilion", (36.35, 37.35, 2.5, 3.5, 0, CRATE_TOP), "7", "crate +1.25")
    m("Shed_FrontBand", (0, 6, 5.0 - LANDING_DEPTH, 5.0, 0, SHED_FRONT), "7", "shed front band +2.5 (mantle 1.25)")
    m("Landing_PavilionPad", (38.4 - LANDING_DEPTH, 38.4, 2.25, 3.75, CRATE_TOP, PAV_EAVE), "7",
      "pad at the pavilion eave +3.25 (mantle 2.0 from the crate)")
    m("Vending", (12.0, 12.9, 0.0, 0.8, 0, VENDING_TOP), "8", "vending machine +1.75")
    m("Pavilion_Plinth", (39, 43, 1, 5, 0, PAV_PLINTH), "-", "plinth +1.0")
    m("Hall_Veranda", (11, 33, 21.7, 34, 0, VERANDA_Z), "-", "veranda +0.5 from the side yards")
    for i, dx in enumerate((0, 36.0)):
        m(f"WeaponRack_{'WE'[i]}", (3.8 + dx, 4.2 + dx, 7.5, 9.5, 0, 1.2), "-", "weapon rack 1.2 (hurdle)")
    return M


# ------------------------------------------------------------------------------------------------ routes / cameras
def climb_routes():
    """Spec 5.1 routes, one entry per climb: the stance (capsule centre XY), the floor under it, the facing (Blender XY)
    and the marker GASP must find. 'walk' entries are rises the CMC walks (step height 0.45 m)."""
    R = []
    c = lambda route, step, xy, floor, face, marker=None, **k: R.append(dict(   # noqa: E731
        {"route": route, "step": step, "stance": list(xy), "floor_z": round(floor, 4), "face": list(face),
         "marker": marker}, **k))
    c("1", "courtyard -> south wall top", (14.5, 0.36), 0.0, (0, -1), "Wall_S_W1")
    c("1", "courtyard -> west wall top", (0.36, 10.0), 0.0, (-1, 0), "Wall_W_S")
    c("1", "courtyard -> east wall top", (43.64, 10.0), 0.0, (1, 0), "Wall_E_S")
    c("2", "west wall top -> pier +3.25", (-0.5, 26.04), WALL_TOP, (0, 1), "Landing_Pier_SW")
    c("2", "pier top -> storehouse eave +3.25", (-0.5, 26.9), GATE_EAVE, (0, 1), walk_to=OUT_EAVE)
    c("2", "east wall top -> pier +3.25", (44.5, 26.04), WALL_TOP, (0, 1), "Landing_Pier_SE")
    c("3", "storehouse roof -> corridor roof (drop)", (8.0, 31.0), OUT_EAVE + (31.0 - 27.4) * (OUT_RIDGE - OUT_EAVE) / 4.3,
      (1, 0), walk_to=CORR_RIDGE)
    c("3", "corridor roof -> hall lower roof side", (10.3, 31.0), CORR_RIDGE, (1, 0),
      walk_to=LOWER_EAVE + (10.9 - 10.5) * (LOWER_TOP - LOWER_EAVE) / 2.5)
    c("4", "courtyard -> cistern +1.25", (13.65, 18.94), 0.0, (0, 1), "Cistern_W")
    c("4", "cistern -> lower eave pad +3.0", (13.65, 20.14), CISTERN_TOP, (0, 1), "Landing_EavePad_W")
    c("4", "courtyard -> east cistern +1.25", (30.35, 18.94), 0.0, (0, 1), "Cistern_E")
    c("4", "east cistern -> lower eave pad +3.0", (30.35, 20.14), CISTERN_TOP, (0, 1), "Landing_EavePad_E")
    c("5", "lower roof -> AC unit top +5.10", (15.6, 21.78), lower_front_z(21.78), (0, 1), "ACUnit_W")
    c("5", "AC top -> upper eave +5.5 (walk-up step)", (15.6, 22.85), AC_TOP, (0, 1), walk_to=UPPER_EAVE)
    c("6", "south wall top -> gate pier +3.25 (west)", (16.64, -0.5), WALL_TOP, (1, 0), "Landing_Pier_GW")
    c("6", "gate pier -> gatehouse hip eave +3.25", (17.5, -0.5), GATE_EAVE, (1, 0), walk_to=GATE_EAVE)
    c("6", "south wall top -> gate pier +3.25 (east)", (27.36, -0.5), WALL_TOP, (-1, 0), "Landing_Pier_GE")
    c("7", "courtyard -> shed crate +1.25", (3.0, 6.64), 0.0, (0, -1), "Crate_Shed")
    c("7", "crate -> shed front band +2.5", (3.0, 5.6), CRATE_TOP, (0, -1), "Shed_FrontBand")
    c("7", "courtyard -> pavilion crate +1.25", (36.0, 3.0), 0.0, (1, 0), "Crate_Pavilion")
    c("7", "crate -> pavilion eave pad +3.25", (37.05, 3.0), CRATE_TOP, (1, 0), "Landing_PavilionPad")
    c("8", "courtyard -> vending machine +1.75", (12.45, 1.14), 0.0, (0, -1), "Vending")
    c("8", "vending top -> wall top +2.0 (walk-up step)", (12.45, 0.3), VENDING_TOP, (0, -1), walk_to=WALL_TOP)
    c("-", "side yard -> veranda +0.5", (10.64, 27.0), 0.0, (1, 0), "Hall_Veranda")
    c("-", "courtyard -> pavilion plinth +1.0", (38.64, 3.0), 0.0, (1, 0), "Pavilion_Plinth")
    c("-", "yard -> over the weapon rack (hurdle)", (3.46, 8.5), 0.0, (1, 0), "WeaponRack_W")
    # the spec as written (no landing): cistern top straight onto the 25 deg lower eave, AC top 4.75 onto the upper eave
    # (the cistern top imagined reaching under the player 0.6 m short of the eave line; no pad / no AC in the way)
    c("4-spec", "SPEC AS WRITTEN: cistern -> lower eave +3.0 (no pad)", (13.65, 20.9), CISTERN_TOP, (0, 1),
      virtual_marker=[13.05, 14.25, 21.5, 24.0, CISTERN_TOP, LOWER_EAVE], exclude_class=["landing", "climbprop"])
    c("5-spec", "SPEC AS WRITTEN: AC top +4.75 -> upper eave +5.5", (15.6, 22.6), 4.75, (0, 1),
      virtual_marker=[15.0, 16.2, 23.1, 24.0, 4.75, UPPER_EAVE], exclude_class=["landing", "climbprop"],
      walk_to=UPPER_EAVE)
    return R


def walk_routes():
    """Ground routes for the capsule walk check (start floor, points). CONTROL routes must be blocked."""
    W = {
        "P1_to_P2_across_the_floor": (0.0, [P1, P2]),
        "P1_round_west_yard_past_tree": (0.0, [P1, (7.2, 10.5), (7.2, 18.5), (1.2, 18.5), (1.2, 5.0)]),
        "P2_round_east_yard_past_well": (0.0, [P2, (38.5, 12.0), (38.8, 24.0), (43.0, 24.5)]),
        "gate_along_path_up_steps_onto_veranda": (0.0, [(22.0, 0.5), (22.0, 21.0), (22.0, 23.0)]),
        "veranda_front_to_west_side_to_corridor": (VERANDA_Z, [(22.0, 23.0), (12.0, 23.0), (12.0, 30.5), (8.0, 31.0)]),
        "veranda_front_to_east_side_to_corridor": (VERANDA_Z, [(22.0, 23.0), (32.0, 23.0), (32.0, 30.5), (36.0, 31.0)]),
        "floor_to_vending_front": (0.0, [P1, (12.45, 1.16)]),
        "floor_to_shed_crate_front": (0.0, [P1, (7.3, 6.0), (4.5, 6.0), (4.5, 6.8), (3.0, 6.66)]),
        "floor_to_pavilion_crate_front": (0.0, [P2, (35.98, 3.0)]),
        "floor_under_gatehouse_to_gate_leaves": (0.0, [(22.0, 3.0), (22.0, 0.0)]),
        "west_wall_top_run": (WALL_TOP, [(-0.5, 0.5), (-0.5, 26.0)]),
        "south_wall_top_run_west": (WALL_TOP, [(-0.5, -0.5), (16.6, -0.5)]),
        "south_wall_top_run_east": (WALL_TOP, [(44.5, -0.5), (27.4, -0.5)]),
        "CONTROL_through_the_closed_gate": (0.0, [(22.0, 3.0), (22.0, -3.0)]),
        "CONTROL_into_the_hall": (VERANDA_Z, [(22.0, 23.0), (22.0, 26.0)]),
        "CONTROL_wall_top_into_gate_pier": (WALL_TOP, [(15.0, -0.5), (17.6, -0.5)]),
        "CONTROL_off_the_wall_top_outside": (WALL_TOP, [(-0.5, 10.0), (-2.0, 10.0)]),
    }
    return {k: {"floor_z": v[0], "points": [list(p) for p in v[1]]} for k, v in W.items()}


def sun():
    """Sunset (user decision): a low sun from the west-north-west, as reference 2 (the sky glows behind the hall, left)."""
    elev, azim_from = 7.0, 160.0   # azimuth of the SUN measured from +X (east) counter-clockwise: 160 = W-N-W
    el, az = math.radians(elev), math.radians(azim_from)
    to_sun = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
    d = -to_sun
    return {"type": "sun", "name": "Sun_Sunset", "elev_deg": elev, "azimuth_deg_from_x": azim_from, "kelvin": 3000,
            "travel_dir": [round(c, 5) for c in d], "lux": 12.0}


CAMERAS = [
    # (name, loc, look_at, horizontal FOV deg, out w, out h, note)
    ("CAM_Overview", (22.0, -17.0, 27.0), (22.0, 15.0, 0.0), 70.0, 1920, 1080, "overview from above the gate (ref 1)"),
    ("CAM_Establishing", (22.0, 1.8, 2.7), (22.0, 30.0, 0.4), 78.0, 1448, 1086,
     "from the gate, eye height on the threshold side, toward the hall (reference 2's framing and aspect)"),
    ("CAM_WallTop", (-0.5, 6.0, 3.62), (0.8, 30.0, 2.4), 75.0, 1920, 1080,
     "a player's eye on the west wall top, looking north along it to the storehouse pier (route 2)"),
]


# ------------------------------------------------------------------------------------------------ main
def main():
    assert_owner("DojoKit", "claude")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    for name, hx in MATERIALS.items():
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        col = tuple(srgb_to_lin(int(hx[i:i + 2], 16) / 255.0) for i in (1, 3, 5)) + (1.0,)
        bsdf.inputs["Base Color"].default_value = col
        bsdf.inputs["Roughness"].default_value = 0.85
        mat.diffuse_color = col
    kit = bpy.data.collections.new("Kit")
    sc.collection.children.link(kit)
    asm = bpy.data.collections.new("Assembly")
    sc.collection.children.link(asm)
    P = pieces()
    names = [p.name for p in P]
    assert len(names) == len(set(names)), "duplicate piece names"
    objs = {p.name: p.build(kit) for p in P}
    kit.hide_render = True
    kit.hide_viewport = True
    inst = []
    for p in P:
        base = Vector(p.pivot())
        for off in p.offsets:
            loc = base + Vector(off)
            n = len(inst)
            o = bpy.data.objects.new(f"{p.name}__{n:03d}", objs[p.name].data)
            o.matrix_world = Matrix.Translation(loc)
            asm.objects.link(o)
            if p.cls == "boundary":
                o.hide_render = True
            pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
            inst.append({"piece": p.name, "loc": [round(v, 4) for v in loc], "rot_z": 0.0, "folder": p.folder,
                         "collision_class": p.cls, "note": p.note,
                         "bbox_min_max": [round(min(q[i] for q in pts), 4) for i in range(3)] +
                                         [round(max(q[i] for q in pts), 4) for i in range(3)]})
    WORK.mkdir(parents=True, exist_ok=True)
    tris = {k: sum(len(pl.vertices) - 2 for pl in o.data.polygons) for k, o in objs.items()}
    data = {
        "units": "metres, Blender frame (UE: x*100, -y*100, z*100, yaw = -rot_z)",
        "spec": "WorkFiles/world/DOJO_ARENA_SPEC.md",
        "pieces": {p.name: {"class": p.cls, "folder": p.folder, "note": p.note, "ucx": len(p.hulls),
                            "tris": tris[p.name], "slots": [m.name for m in objs[p.name].data.materials]} for p in P},
        "instances": inst,
        "collision_classes": COLLISION,
        "materials": {k: {"srgb": v, "roughness": 0.85} for k, v in MATERIALS.items()},
        "traversal_markers": markers(),
        "player_starts": [{"name": "PlayerStart_P1", "tag": "P1", "loc": [P1[0], P1[1], 0.0], "rot_z": 0.0},
                          {"name": "PlayerStart_P2", "tag": "P2", "loc": [P2[0], P2[1], 0.0], "rot_z": 180.0}],
        "sun": sun(),
        "cameras": [{"name": c[0], "loc": list(c[1]), "look_at": list(c[2]), "hfov_deg": c[3], "out_wh": [c[4], c[5]],
                     "note": c[6]} for c in CAMERAS],
        "climb_routes": climb_routes(),
        "walk_routes": walk_routes(),
        "numbers": {"wall_top": WALL_TOP, "gate_eave": GATE_EAVE, "gate_ridge": GATE_RIDGE, "lower_eave": LOWER_EAVE,
                    "lower_top": LOWER_TOP, "upper_eave": UPPER_EAVE, "upper_ridge": UPPER_RIDGE, "ac_top": AC_TOP,
                    "landing_depth": LANDING_DEPTH, "p1": P1, "p2": P2},
    }
    (WORK / "layout.json").write_text(json.dumps(data, indent=1), encoding="utf-8")
    # KIT 1 (build_kit1.py) reads this copy and writes layout.json again with the kit in place of the grey-box wall
    # and gate: after re-running the grey-box, re-run build_kit1.py
    (WORK / "layout_greybox.json").write_text(json.dumps(data, indent=1), encoding="utf-8")

    qa = {}
    waive = {"uv0_tile_range", "uv_no_overlap"}
    for name, o in objs.items():
        r = qa_check([o], require_uv1=True)
        fails = [c for c in r["checks"] if not c["passed"]]
        hard = [c for c in fails if c["name"] not in waive]
        qa[name] = {"hard_fails": hard, "waived": sorted({c["name"] for c in fails if c["name"] in waive}),
                    "tris": r["triangles"].get(name)}
    (WORK / "qa_report.json").write_text(json.dumps(qa, indent=1, default=str), encoding="utf-8")
    hard_total = sum(len(v["hard_fails"]) for v in qa.values())
    print(f"QA: {len(objs)} pieces, {len(inst)} instances, hard fails {hard_total}")
    for k, v in qa.items():
        for c in v["hard_fails"]:
            print("  FAIL", k, c["name"], str(c["detail"])[:200])
    if "--no-export" not in ARGS and hard_total == 0:
        kit.hide_viewport = False
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        for f in EXPORT_DIR.glob("SM_DGB_*.fbx"):
            if f.stem not in objs:
                f.unlink()   # our own stale grey-box exports only
        res = {}
        for name, o in objs.items():
            r = export_fbx(str(EXPORT_DIR / f"{name}.fbx"), [o], kind="static", sidecar=False)
            res[name] = {"objects": r["objects"], "warnings": r["warnings"]}
        (WORK / "export_report.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
        kit.hide_viewport = True
        print(f"exported {len(res)} FBX to {EXPORT_DIR}")
    BLEND.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    print("saved", BLEND)


main()
