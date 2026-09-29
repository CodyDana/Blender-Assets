"""Mesh building for the Card Shop Kit: a millimetre face list -> one Blender mesh object with the kit's UV layout.

UV layout (CARDSHOP_KIT_SPEC.md 4.1):
* UV0 ``UVMap``: every print face spans a full 0-1 tile: front (0,0), back (1,0), label (0,1). A face gets its UV0 from
  its *region*'s planar projection. Region 0 faces (edges, insides, frames) are unwrapped automatically into the
  U -1..0 tile when the mesh has print, or into 0-1 when it has none.
* UV1 ``Lightmap``: a unique 0-1 layout of every face (lightmap + per-mesh ORM bake).

Faces are authored counter-clockwise seen from outside (a cavity's faces point into the cavity), so no normal
recalculation is run: ``recalc_face_normals`` would turn a void inside out. ``check_outward`` verifies the winding of
convex shells.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import bmesh
import bpy
from mathutils import Matrix, Vector

from .shapes import Builder, Face, Fill, chamfer_rect, rect, rounded_rect  # noqa: F401
from .spec import MM

Vec3 = Tuple[float, float, float]
Projection = Callable[[float, float, float], Tuple[float, float]]
REGION_LAYER = "csk_region"


# --------------------------------------------------------------------------- to Blender

def _material(name: str) -> "bpy.types.Material":
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
    return mat


def build_bmesh(b: Builder) -> "bmesh.types.BMesh":
    bm = bmesh.new()
    region = bm.faces.layers.int.new(REGION_LAYER)
    bv = [bm.verts.new(Vector(p) * MM) for p in b.verts]
    for f in b.faces:
        face = bm.faces.new([bv[i] for i in f.verts])
        face.material_index = f.mat
        face[region] = f.region
    for fl in b.fills:
        edges = []
        for loop in fl.loops:
            for i in range(len(loop)):
                a, c = bv[loop[i]], bv[loop[(i + 1) % len(loop)]]
                e = bm.edges.get((a, c)) or bm.edges.new((a, c))
                edges.append(e)
        res = bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=edges,
                                      normal=Vector(fl.normal))
        want = Vector(fl.normal)
        for face in res["geom"]:
            if not isinstance(face, bmesh.types.BMFace):
                continue
            face.normal_update()
            if face.normal.dot(want) < 0:
                face.normal_flip()
            face.material_index = fl.mat
            face[region] = fl.region
    ngons = [f for f in bm.faces if len(f.verts) > 4]
    if ngons:
        bmesh.ops.triangulate(bm, faces=ngons)
    bm.normal_update()
    return bm


def bevel_edges(bm: "bmesh.types.BMesh", width_mm: float, min_angle_deg: float = 60.0, segments: int = 1) -> int:
    """Chamfer every edge sharper than ``min_angle_deg`` (1 segment); new faces become region 0. Returns the count."""
    region = bm.faces.layers.int[REGION_LAYER]
    edges = [e for e in bm.edges if e.is_manifold and len(e.link_faces) == 2
             and math.degrees(e.calc_face_angle(0.0)) > min_angle_deg]
    if not edges:
        return 0
    res = bmesh.ops.bevel(bm, geom=edges, offset=width_mm * MM, offset_type="OFFSET", segments=segments, profile=0.5,
                          affect="EDGES", clamp_overlap=True)
    for f in res["faces"]:
        f[region] = 0
    bm.normal_update()
    return len(edges)


def mark_sharp(bm: "bmesh.types.BMesh", angle_deg: float = 30.0) -> None:
    for e in bm.edges:
        e.smooth = not (len(e.link_faces) == 2 and math.degrees(e.calc_face_angle(0.0)) > angle_deg)


def _select_faces(obj: "bpy.types.Object", pick: Callable[[int, int], bool]) -> int:
    """Select faces by (index, region); return the count."""
    me = obj.data
    reg = me.attributes[REGION_LAYER].data
    n = 0
    for p in me.polygons:
        p.select = bool(pick(p.index, reg[p.index].value))
        n += p.select
    return n


def _uv_overlaps(obj: "bpy.types.Object", uv_name: str) -> int:
    """Overlapping UV triangle pairs among the selected faces (the house qa_check test)."""
    import numpy as np
    from pipeline.qa_check import uv_overlap_sat
    me = obj.data
    uv = me.uv_layers[uv_name].data
    tris = []
    for p in me.polygons:
        if not p.select:
            continue
        li = list(p.loop_indices)
        for i in range(1, len(li) - 1):
            tris.append([uv[li[0]].uv[:], uv[li[i]].uv[:], uv[li[i + 1]].uv[:]])
    return uv_overlap_sat(np.array(tris)) if len(tris) > 1 else 0


def _smart_project(obj: "bpy.types.Object", uv_name: str, margin: float) -> None:
    """Smart project + pack. 66 degrees first; if a projection group folds faces onto each other (a boolean pocket's
    inner wall facing the same way as an outer wall), retry with a tighter angle limit."""
    me = obj.data
    me.uv_layers.active = me.uv_layers[uv_name]
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    for angle in (66.0, 45.0, 30.0):
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_mode(type="FACE")
        bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=margin, correct_aspect=True,
                                 scale_to_bounds=False)
        bpy.ops.uv.select_all(action="SELECT")
        bpy.ops.uv.pack_islands(margin=margin, rotate=True, shape_method="AABB")   # concave packing: ~10 s a call
        bpy.ops.object.mode_set(mode="OBJECT")
        if _uv_overlaps(obj, uv_name) == 0:
            return


def _apply_boolean(obj: "bpy.types.Object", operation: str, b: Builder) -> None:
    """Apply an exact boolean with the closed shell ``b`` (mm). Face tags (region, material index) of the cutter's
    faces carry over, so a cut face can be given its own region / material by the cutter's builder."""
    bm = build_bmesh(b)
    me = bpy.data.meshes.new("__csk_cutter")
    bm.to_mesh(me)
    bm.free()
    cutter = bpy.data.objects.new("__csk_cutter", me)
    bpy.context.scene.collection.objects.link(cutter)
    mod = obj.modifiers.new("csk_bool", "BOOLEAN")
    mod.operation = operation
    mod.solver = "EXACT"
    mod.object = cutter
    try:
        mod.material_mode = "INDEX"
    except (AttributeError, TypeError):
        pass
    from pipeline.helpers import apply_modifier
    apply_modifier(obj, mod)
    bpy.data.objects.remove(cutter, do_unlink=True)
    bpy.data.meshes.remove(me)


def to_object(name: str, b: Builder, materials: Sequence[str], projections: Dict[int, Projection],
              bevel_mm: Optional[float] = None, weighted_normals: bool = True,
              collection: Optional["bpy.types.Collection"] = None,
              ops: Sequence[Tuple[str, Builder]] = (), bevel_segments: int = 1,
              bevel_angle: float = 60.0, bevel_first: bool = False,
              extra: Optional[Builder] = None) -> "bpy.types.Object":
    """Build ``name`` from ``b``: booleans (``ops``: ("DIFFERENCE" | "UNION", builder)), bevel, sharp edges, UV0
    (print projections + auto), UV1 (unique), materials. ``bevel_first`` bevels the base shell before the booleans,
    so cut edges stay crisp and the bevel never meets a cut (no collinear slivers). ``extra`` is joined after the bevel
    and the booleans (small crisp parts, e.g. slotted standards)."""
    bm = build_bmesh(b)
    if bevel_mm and bevel_first:
        bevel_edges(bm, bevel_mm, bevel_angle, bevel_segments)
        ngons = [f for f in bm.faces if len(f.verts) > 4]
        if ngons:
            bmesh.ops.triangulate(bm, faces=ngons)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in materials:
        me.materials.append(_material(m))
    obj = bpy.data.objects.new(name, me)
    (collection or bpy.context.scene.collection).objects.link(obj)
    for operation, cb in ops:
        _apply_boolean(obj, operation, cb)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    if REGION_LAYER not in bm.faces.layers.int:
        bm.faces.layers.int.new(REGION_LAYER)
    if bevel_mm and not bevel_first:
        bevel_edges(bm, bevel_mm, bevel_angle, bevel_segments)
    if extra is not None:                   # append the extra parts (BMesh.from_mesh adds to what is there)
        eb = build_bmesh(extra)
        tmp = bpy.data.meshes.new("__csk_extra")
        eb.to_mesh(tmp)
        eb.free()
        bm.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
    for _ in range(3):              # bevel + boolean slivers: dissolve zero-area faces, re-triangulate what it merges
        bmesh.ops.dissolve_degenerate(bm, dist=1e-6, edges=list(bm.edges))
        ngons = [f for f in bm.faces if len(f.verts) > 4]
        if ngons:
            bmesh.ops.triangulate(bm, faces=ngons)
        if not any(f.calc_area() < 1e-12 for f in bm.faces):
            break
    mark_sharp(bm)
    bm.to_mesh(obj.data)
    bm.free()
    me = obj.data
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))

    uv0 = me.uv_layers.new(name="UVMap")
    me.uv_layers.new(name="Lightmap")
    reg = me.attributes[REGION_LAYER].data
    has_print = any(reg[p.index].value > 0 for p in me.polygons)
    # region 0 first (smart project writes only the selected faces), then shift it to the U -1 tile
    if _select_faces(obj, lambda i, r: r == 0):
        _smart_project(obj, "UVMap", 0.02)
        me = obj.data                                   # edit mode rebuilt the arrays: never reuse old handles
        reg, uv0 = me.attributes[REGION_LAYER].data, me.uv_layers["UVMap"]
        if has_print:
            for p in me.polygons:
                if reg[p.index].value == 0:
                    for li in p.loop_indices:
                        u, v = uv0.data[li].uv
                        uv0.data[li].uv = (u - 1.0, v)
    for p in me.polygons:
        r = reg[p.index].value
        if r == 0:
            continue
        proj = projections[r]
        for li, vi in zip(p.loop_indices, p.vertices):
            co = me.vertices[vi].co / MM
            uv0.data[li].uv = proj(co.x, co.y, co.z)
    _select_faces(obj, lambda i, r: True)
    _smart_project(obj, "Lightmap", 0.01)
    me = obj.data
    me.uv_layers.active_index = 0
    for layer in me.uv_layers:
        layer.active_render = layer.name == "UVMap"
    if weighted_normals:
        mod = obj.modifiers.new("WeightedNormal", "WEIGHTED_NORMAL")
        mod.keep_sharp = True
        mod.weight = 50
        from pipeline.helpers import apply_modifier
        apply_modifier(obj, mod)
    return obj


def triangles(obj: "bpy.types.Object") -> int:
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def aabb_mm(obj: "bpy.types.Object") -> Tuple[Vec3, Vec3]:
    """Local-space render AABB in mm (the fit test uses render bounds, spec 4.2)."""
    xs = [v.co for v in obj.data.vertices]
    mn = tuple(min(c[i] for c in xs) / MM for i in range(3))
    mx = tuple(max(c[i] for c in xs) / MM for i in range(3))
    return mn, mx  # type: ignore[return-value]


def degenerate_uv_faces(obj: "bpy.types.Object", layer: str, min_area: float = 1e-9) -> int:
    """Faces whose UV area on ``layer`` is ~0 (Unreal's tangent build warns on them; lightmaps smear)."""
    me = obj.data
    uv = me.uv_layers[layer].data
    bad = 0
    for p in me.polygons:
        pts = [uv[li].uv for li in p.loop_indices]
        area = 0.0
        for i in range(len(pts)):
            a, c = pts[i], pts[(i + 1) % len(pts)]
            area += a[0] * c[1] - c[0] * a[1]
        if abs(area) / 2 < min_area:
            bad += 1
    return bad


def box_hull(parent: "bpy.types.Object", index: int, mn: Vec3, mx: Vec3) -> "bpy.types.Object":
    """``UCX_<parent>_NN``: a closed box hull in the parent's space (mm in), as ``helpers.make_ucx_hull`` names and
    parents it."""
    name = f"UCX_{parent.name}_{index:02d}"
    b = Builder()
    b.box(mn, mx)
    bm = build_bmesh(b)
    bm.faces.layers.int.remove(bm.faces.layers.int[REGION_LAYER])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    hull = bpy.data.objects.new(name, me)
    for col in parent.users_collection:
        col.objects.link(hull)
    hull.parent = parent
    hull.matrix_parent_inverse = Matrix.Identity(4)
    hull.hide_render = True
    hull.display_type = "WIRE"
    hull["ue_collision"] = "UCX"
    return hull


def check_outward(obj: "bpy.types.Object") -> int:
    """Faces that point toward the centre of their own loose part (a winding check for convex parts)."""
    me = obj.data
    parent = list(range(len(me.vertices)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for e in me.edges:
        ra, rb = find(e.vertices[0]), find(e.vertices[1])
        if ra != rb:
            parent[ra] = rb
    sums = {}
    for v in me.vertices:
        r = find(v.index)
        acc = sums.setdefault(r, [Vector(), 0])
        acc[0] += v.co
        acc[1] += 1
    bad = 0
    for p in me.polygons:
        acc = sums[find(p.vertices[0])]
        centre = acc[0] / acc[1]
        if (p.center - centre).dot(p.normal) < -1e-9:
            bad += 1
    return bad
