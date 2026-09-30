"""Shared mesh side of the dojo building kits: the piece container, chamfered-box primitives and the Geo -> Blender
mesh step (library UVs per material, UCX hulls), plus the UV1 / LOD helpers. Moved out of
Scripts/dojo/hall/build_hall.py (2026-09-28, hall fix round) so the next kits (storehouse, residence, corridors,
pavilion) use the roof system (roof_kit.py) and this module without importing the hall builder.

    import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/dojo/roof")
    import roof_kit as RK
    import kit_mesh as KM
    p = KM.Piece("SM_DKX_Thing", "building", "Kit", "note", pivot=(0, 0, 0))
    KM.cbox(p.g, 0, 1, 0, 1, 0, 2, KM.TD)          # geometry into p.g (a kit1_geo.Geo)
    p.hull_box(0, 1, 0, 1, 0, 2)                    # UCX hulls (world points; the pivot is subtracted)
    obj, bad_faces = KM.geo_to_object(p, collection)

Materials are the shared library's (Scripts/dojo/materials, M_DJ_*); geo_to_object adds the end-grain slots and maps
every material with the library's own helper (grain_uv / box_uv / unit_uv; tiles keep the Geo frame projection in
tile units).
"""
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
for p_ in (HERE, HERE.parent, HERE.parent / "materials"):
    if str(p_) not in sys.path:
        sys.path.insert(0, str(p_))
from kit1_geo import Geo  # noqa: E402
import dojo_materials as djm  # noqa: E402

TD, TDE = "M_DJ_TimberDark", "M_DJ_TimberDarkEnd"
TA, TAE = "M_DJ_TimberAged", "M_DJ_TimberAgedEnd"
GR = "M_DJ_Granite"
GRR = "M_DJ_GraniteRubble"
PL = "M_DJ_PlasterCream"
IR = "M_DJ_Iron"
TL = "M_DJ_RoofTile"
GL = "M_DJ_GlassAmber"


# ------------------------------------------------------------------------------------------------ primitives
def cobox(g, c, u, v, w, hu, hv, hw, ch, mat):
    """Oriented box with chamfered edges (every edge a 45 deg bevel face of width ch * sqrt 2: the library's edge wear
    lands on these narrow faces)."""
    c, u, v, w = Vector(c), Vector(u).normalized(), Vector(v).normalized(), Vector(w).normalized()
    ch = max(0.0005, min(ch, 0.45 * min(hu, hv, hw)))
    verts, idx = [], {}

    def P(a, b, cc):
        return c + u * a + v * b + w * cc
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                idx[(sx, sy, sz, 0)] = len(verts)
                verts.append(P(sx * hu, sy * (hv - ch), sz * (hw - ch)))
                idx[(sx, sy, sz, 1)] = len(verts)
                verts.append(P(sx * (hu - ch), sy * hv, sz * (hw - ch)))
                idx[(sx, sy, sz, 2)] = len(verts)
                verts.append(P(sx * (hu - ch), sy * (hv - ch), sz * hw))
    faces = []
    ring = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    for s in (-1, 1):
        faces.append([idx[(s, a, b, 0)] for a, b in ring])
        faces.append([idx[(a, s, b, 1)] for a, b in ring])
        faces.append([idx[(a, b, s, 2)] for a, b in ring])
    for a in (-1, 1):
        for b in (-1, 1):
            faces.append([idx[(-1, a, b, 1)], idx[(1, a, b, 1)], idx[(1, a, b, 2)], idx[(-1, a, b, 2)]])
            faces.append([idx[(a, -1, b, 0)], idx[(a, 1, b, 0)], idx[(a, 1, b, 2)], idx[(a, -1, b, 2)]])
            faces.append([idx[(a, b, -1, 0)], idx[(a, b, 1, 0)], idx[(a, b, 1, 1)], idx[(a, b, -1, 1)]])
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                faces.append([idx[(sx, sy, sz, 0)], idx[(sx, sy, sz, 1)], idx[(sx, sy, sz, 2)]])
    out = []
    for f in faces:
        pts = [verts[i] for i in f]
        nw = Vector()
        for i in range(len(pts)):
            a_, b_ = pts[i], pts[(i + 1) % len(pts)]
            nw += Vector(((a_.y - b_.y) * (a_.z + b_.z), (a_.z - b_.z) * (a_.x + b_.x), (a_.x - b_.x) * (a_.y + b_.y)))
        cen = sum(pts, Vector()) / len(pts)
        out.append(tuple(f) if nw.dot(cen - c) >= 0 else tuple(reversed(f)))
    ext = sorted(((hu, u), (hv, v), (hw, w)), key=lambda t: -t[0])
    g.add(verts, out, mat, (ext[0][1], ext[1][1], ext[2][1]))
    return g


def cbox(g, x0, x1, y0, y1, z0, z1, mat, ch=0.008):
    """Axis-aligned chamfered box between the given bounds."""
    return cobox(g, ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), (1, 0, 0), (0, 1, 0), (0, 0, 1),
                 (x1 - x0) / 2, (y1 - y0) / 2, (z1 - z0) / 2, ch, mat)


def member(g, a, b, w, h, mat=TD, up=(0, 0, 1), ch=0.008):
    """A chamfered timber member along the centre line a -> b, w wide and h deep (h along `up`)."""
    a, b = Vector(a), Vector(b)
    ax = (b - a).normalized()
    upv = Vector(up)
    upv = (upv - ax * upv.dot(ax)).normalized()
    side = upv.cross(ax).normalized()
    return cobox(g, (a + b) / 2, ax, side, upv, (b - a).length / 2, w / 2, h / 2, ch, mat)


def quad(g, pts, mat):
    g.add([Vector(p) for p in pts], [(0, 1, 2, 3)], mat, None)
    return g


# ------------------------------------------------------------------------------------------------ piece container
class Piece:
    """One exported static mesh: its Geo, UCX hull point lists (world, or piece-local when local=True), the collision
    class for the layout, Nanite flag, whether the library wear bake runs, and extra numbers for the layout json."""

    def __init__(self, name, cls, folder, note, pivot=(0.0, 0.0, 0.0)):
        self.name, self.cls, self.folder, self.note = name, cls, folder, note
        self.pivot = Vector(pivot)
        self.g = Geo()
        self.hulls = []           # point lists in WORLD (the pivot is subtracted at build)
        self.local = False        # True: geometry and hulls are already piece-local
        self.nanite = False
        self.wear = True
        self.extra = {}

    def hull_box(self, x0, x1, y0, y1, z0, z1):
        self.hulls.append([(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)])
        return self


# ------------------------------------------------------------------------------------------------ Geo -> mesh
def geo_to_object(piece, coll):
    """Build the Blender mesh object for a Piece in collection `coll`: faces with library materials, UVs per material
    with the library helpers (tile units), the UCX_<name>_NN hulls parented to it. Returns (object, bad face count)."""
    g = piece.g
    P = Vector((0, 0, 0)) if piece.local else piece.pivot
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    vs = [bm.verts.new(p - P) for p in g.v]
    mats, bad = [], 0
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
        fr = g.fr[fi]
        face.normal_update()
        n = face.normal
        axes = list(fr) if fr is not None else [Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))]
        ni = max(range(3), key=lambda i: abs(n.dot(axes[i])))
        inplane = [i for i in range(3) if i != ni]
        U, Vv = axes[inplane[0]], axes[inplane[1]]
        for loop in face.loops:
            co = loop.vert.co + P
            loop[uvl].uv = (co.dot(U) / 4.0, co.dot(Vv) / 4.0)
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
    mesh = bpy.data.meshes.new(piece.name)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(djm.make_material(m))
    extra_slots = {}
    for face_m, end_m in ((TD, TDE), (TA, TAE)):
        if face_m in mats:
            mesh.materials.append(djm.make_material(end_m))
            extra_slots[face_m] = len(mesh.materials) - 1
    obj = bpy.data.objects.new(piece.name, mesh)
    coll.objects.link(obj)
    by_mat = {}
    for poly in mesh.polygons:
        by_mat.setdefault(mats[poly.material_index], []).append(poly.index)
    for m, faces in by_mat.items():
        if m == TD:
            djm.grain_uv(obj, "TimberDark", end_set="TimberDarkEnd", faces=faces, end_material_index=extra_slots[TD])
        elif m == TA:
            djm.grain_uv(obj, "TimberAged", end_set="TimberAgedEnd", faces=faces, end_material_index=extra_slots[TA])
        elif m == IR:
            djm.grain_uv(obj, "Iron", faces=faces, round_mode=False)
        elif m == PL:
            djm.box_uv(obj, "PlasterCream", faces=faces, space="OBJECT")
        elif m == GR:
            stone_uv(obj, faces, "Granite")
        elif m == GRR:
            stone_uv(obj, faces, "GraniteRubble")
        elif m == GL:
            djm.unit_uv(obj, faces=faces)
    for i, pts in enumerate(piece.hulls):
        hb = bmesh.new()
        hv = [hb.verts.new(Vector(p) - P) for p in pts]
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
    obj["kit"] = getattr(piece, "kit", "hall")
    return obj, bad


def stone_uv(obj, faces, set_name="Granite"):
    """Box UV per stone (each block its own random offset; never mirrored)."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    fset = set(faces)
    seen, parts = set(), []
    for fi in faces:
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
        parts.append(part)
    bm.free()
    groups = [[] for _ in range(8)]
    for k, part in enumerate(parts):
        groups[k % 8].extend(part)
    for k, grp in enumerate(groups):
        if grp:
            djm.box_uv(obj, set_name, faces=grp, space="OBJECT", seed=k * 7 + 1)


def granite_uv(obj, faces):
    return stone_uv(obj, faces, "Granite")


# ------------------------------------------------------------------------------------------------ UV1 / LODs
def grid_uv1(obj, pad=0.08):
    """UV1 for the big Nanite roof pieces (Lumen: no lightmap is baked): every face gets its own cell of a square grid,
    projected in its own plane and fitted inside the cell with a margin, so UV1 is inside 0-1 with no overlap by
    construction (lightmap_pack left thousands of sliver overlaps at 100k+ faces)."""
    me = obj.data
    uv = me.uv_layers["UV1"].data
    n = len(me.polygons)
    k = math.ceil(math.sqrt(n))
    cell = 1.0 / k
    for pi, poly in enumerate(me.polygons):
        nrm = poly.normal
        a = Vector((1, 0, 0)) if abs(nrm.x) < 0.9 else Vector((0, 1, 0))
        u = (a - nrm * a.dot(nrm)).normalized()
        v = nrm.cross(u)
        pts = [me.vertices[me.loops[li].vertex_index].co for li in poly.loop_indices]
        us = [p.dot(u) for p in pts]
        vs = [p.dot(v) for p in pts]
        u0, v0 = min(us), min(vs)
        span = max(max(us) - u0, max(vs) - v0, 1e-9)
        ox, oy = (pi % k) * cell, (pi // k) * cell
        inner = cell * (1.0 - 2 * pad)
        for li, uu, vv in zip(poly.loop_indices, us, vs):
            uv[li].uv = (ox + cell * pad + (uu - u0) / span * inner, oy + cell * pad + (vv - v0) / span * inner)


def add_uv1(obj, grid_over=40000):
    """UV1 (lightmap channel): lightmap_pack, or grid_uv1 above `grid_over` faces."""
    me = obj.data
    me.uv_layers.new(name="UV1")
    me.uv_layers.active_index = 1
    n = len(me.polygons)
    with bpy.context.temp_override(active_object=obj, object=obj, selected_objects=[obj], selected_editable_objects=[obj]):
        if n > grid_over:
            grid_uv1(obj)
        else:
            bpy.ops.uv.lightmap_pack(PREF_CONTEXT="ALL_FACES", PREF_PACK_IN_ONE=False, PREF_NEW_UVLAYER=False,
                                     PREF_BOX_DIV=12, PREF_MARGIN_DIV=0.2)
    me.uv_layers.active_index = 0


def fix_lod(obj, clamp_to=None):
    """Clean a decimated LOD (non-manifold extra faces, wire edges, loose verts) and repack its UV1. clamp_to (round 3,
    the measurer's StepBand LOD1 bulging 3.6 cm past LOD0): an object whose local bounding box every LOD vertex is
    clamped into, so a LOD never reaches past LOD0 (Unreal's non-Nanite render bounds are the union of all LODs)."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    if clamp_to is not None:
        vs = [v.co for v in clamp_to.data.vertices]
        lo = [min(c[i] for c in vs) for i in range(3)]
        hi = [max(c[i] for c in vs) for i in range(3)]
        for v in bm.verts:
            v.co = type(v.co)([min(max(v.co[i], lo[i]), hi[i]) for i in range(3)])
    extra = set()
    for e in bm.edges:
        if len(e.link_faces) > 2:
            for f in sorted(e.link_faces, key=lambda f: f.calc_area())[:len(e.link_faces) - 2]:
                extra.add(f)
    if extra:
        bmesh.ops.delete(bm, geom=list(extra), context="FACES")
    wire = [e for e in bm.edges if not e.link_faces]
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
