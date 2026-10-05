"""Game assembly of a gun's static twin (import inside Blender): game materials on the shipped maps, the LOD meshes
joined from the part objects (each set's UV0 moved to its own U tile: slot k on tile k, GUN_BUILDING_STUDY 5.8), the
authored UV1 fallback, UCX hulls from dense surface samples (katana method), sockets from spec records (Unreal
orientation -> Blender local rotation), mass properties, and the LOD group.
"""
from __future__ import annotations

import math
from typing import Dict, List, Sequence

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector


# ====================================================================== materials
def game_material(name, stem, tex_dir):
    """Principled preview of the shipped maps: BC (sRGB), ORM (linear: R AO, G roughness, B metallic), N (DirectX:
    green flipped back for Blender). Image names are the texture file names (qa_check's colour-space rules key on the
    _ORM / _N suffixes)."""
    m = bpy.data.materials.get(name)
    if m is not None:
        m.name = name + "_old"
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bs = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UV0"

    def img(suffix, cs):
        t = nt.nodes.new("ShaderNodeTexImage")
        path = str(tex_dir / f"{stem}_{suffix}.png")
        im = bpy.data.images.load(path, check_existing=True)
        im.name = f"{stem}_{suffix}.png"
        im.colorspace_settings.name = cs
        t.image = im
        t.extension = "REPEAT"
        nt.links.new(uv.outputs["UV"], t.inputs["Vector"])
        return t
    tbc, torm, tn = img("BC", "sRGB"), img("ORM", "Non-Color"), img("N", "Non-Color")
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(torm.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], bs.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], bs.inputs["Metallic"])
    nsep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(tn.outputs["Color"], nsep.inputs["Color"])
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    nt.links.new(nsep.outputs["Green"], inv.inputs[1])
    ncomb = nt.nodes.new("ShaderNodeCombineColor")
    nt.links.new(nsep.outputs["Red"], ncomb.inputs["Red"])
    nt.links.new(inv.outputs[0], ncomb.inputs["Green"])
    nt.links.new(nsep.outputs["Blue"], ncomb.inputs["Blue"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.uv_map = "UV0"
    nt.links.new(ncomb.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bs.inputs["Normal"])
    # AO preview (Unreal applies AO to indirect light only): a gentle multiply on the base colour
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 1.0
    aoc = nt.nodes.new("ShaderNodeMapRange")
    aoc.inputs["To Min"].default_value = 0.6
    nt.links.new(sep.outputs["Red"], aoc.inputs["Value"])
    a_in = next(s_ for s_ in mix.inputs if s_.name == "A" and s_.type == "RGBA")
    b_in = next(s_ for s_ in mix.inputs if s_.name == "B" and s_.type == "RGBA")
    r_out = next(s_ for s_ in mix.outputs if s_.name == "Result" and s_.type == "RGBA")
    nt.links.new(tbc.outputs["Color"], a_in)
    nt.links.new(aoc.outputs["Result"], b_in)
    nt.links.new(r_out, bs.inputs["Base Color"])
    return m


# ====================================================================== twin join
def join_copies(objs, name, coll, slot_of, mats, tile_of=None):
    """Copies of `objs` joined into one mesh `name` with the material slots `mats` (in order); `slot_of(ob)` gives each
    object's slot index; tile_of[k] shifts UV0 of slot k by that many U tiles. Triangulated (the inputs already are)."""
    cops = []
    for o in objs:
        c = o.copy()
        c.data = o.data.copy()
        for k in list(c.keys()):
            del c[k]
        coll.objects.link(c)
        c.data.materials.clear()
        for m in mats:
            c.data.materials.append(m)
        k = slot_of(o)
        c.data.polygons.foreach_set("material_index", [k] * len(c.data.polygons))
        if tile_of and tile_of.get(k):
            lay = c.data.uv_layers["UV0"]
            uv = np.empty(len(lay.data) * 2, np.float32)
            lay.data.foreach_get("uv", uv)
            uv = uv.reshape(-1, 2)
            uv[:, 0] += tile_of[k]
            lay.data.foreach_set("uv", uv.ravel())
        cops.append(c)
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for c in cops:
        c.select_set(True)
    bpy.context.view_layer.objects.active = cops[0]
    bpy.ops.object.join()
    ob = cops[0]
    ob.name = name
    ob.data.name = name
    # remove helper attributes the bake added
    for an in ("pid", "cls", "isl"):
        a = ob.data.attributes.get(an)
        if a is not None:
            ob.data.attributes.remove(a)
    return ob


def uv1_from_uv0(ob, regions: Dict[int, tuple], uv0="UV0", uv1="UV1"):
    """Authored lightmap fallback: each slot's UV0 layout (overlap-free within the slot) scaled into its own square of
    0..1 (regions[slot] = (u0, v0, size)); slots never share a square, so UV1 is overlap-free and inside 0..1."""
    me = ob.data
    lay0 = me.uv_layers[uv0]
    uv = np.empty(len(lay0.data) * 2, np.float32)
    lay0.data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2).astype(float)
    mi = np.empty(len(me.polygons), np.int32)
    me.polygons.foreach_get("material_index", mi)
    lt = np.empty(len(me.polygons), np.int32)
    me.polygons.foreach_get("loop_total", lt)
    lmat = np.repeat(mi, lt)
    out = np.zeros_like(uv)
    for k, (u0, v0, s) in regions.items():
        sel = lmat == k
        q = uv[sel].copy()
        q[:, 0] -= np.floor(q[:, 0].min() + 1e-6)          # back to 0..1 from the slot's tile
        out[sel] = np.c_[u0 + q[:, 0] * s, v0 + q[:, 1] * s]
    lay1 = me.uv_layers.get(uv1) or me.uv_layers.new(name=uv1)
    lay1.data.foreach_set("uv", out.astype(np.float32).ravel())
    me.uv_layers.active = me.uv_layers[uv0]
    try:
        me.uv_layers[uv0].active_render = True
    except Exception:  # noqa: BLE001
        pass


# ====================================================================== hulls (katana_game method, copied)
def dense_samples(V, T, step, rng=None):
    if len(T) == 0:
        return np.zeros((0, 3))
    A, B, C = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    L = np.max(np.stack([np.linalg.norm(B - A, axis=1), np.linalg.norm(C - B, axis=1),
                         np.linalg.norm(A - C, axis=1)], 1), axis=1)
    n = np.maximum(1, np.ceil(L / step).astype(int))
    out = [A, B, C]
    for k in np.unique(n):
        sel = n == k
        a, b, c = A[sel], B[sel], C[sel]
        for i in range(k + 1):
            for j in range(k + 1 - i):
                u, v = i / k, j / k
                if rng is not None:
                    du, dv = rng.random(2) / k
                    if u + du + v + dv <= 1.0:
                        u, v = u + du, v + dv
                out.append(a + (b - a) * u + (c - a) * v)
    return np.vstack(out)


def mesh_vt(o):
    me = o.data
    V = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", V)
    V = V.reshape(-1, 3)
    M = np.array(o.matrix_world)
    V = (np.c_[V, np.ones(len(V))] @ M.T)[:, :3] * 1000.0
    T = []
    for p in me.polygons:
        vs = list(p.vertices)
        for k in range(1, len(vs) - 1):
            T.append((vs[0], vs[k], vs[k + 1]))
    return V, np.array(T, int).reshape(-1, 3)


def _planes(me):
    b = bmesh.new()
    b.from_mesh(me)
    b.faces.ensure_lookup_table()
    pl = [(np.array(f.normal[:]), float(np.dot(np.array(f.normal[:]), np.array(f.verts[0].co[:])))) for f in b.faces]
    b.free()
    return pl


def _grow_to_contain(h, pts, margin=0.00015):
    me = h.data
    for _ in range(80):
        pl = _planes(me)
        worst = 0.0
        for n, d in pl:
            worst = max(worst, float((pts @ n - d).max()))
        if worst <= 0.0:
            return
        V = np.array([v.co[:] for v in me.vertices])
        c = V.mean(axis=0)
        ext = np.maximum(np.abs(V - c).max(axis=0), 1e-5)
        k = 1.0 + (worst + margin) / ext
        for v in me.vertices:
            v.co = Vector(c + (np.array(v.co[:]) - c) * k)
    raise RuntimeError(f"{h.name}: hull could not be grown to contain its points")


def hull_from_points(name, pts_m, parent, coll, max_verts=32, dilate_m=0.0002):
    """Convex hull of points (metres), reduced to <= max_verts by collapse decimation + re-hull, dilated, grown until
    every point is inside, coplanar faces dissolved; a UCX child of `parent`."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from pipeline.helpers import apply_modifier, _hull_only
    c0 = pts_m.mean(0)
    bm = bmesh.new()
    for p in pts_m:
        bm.verts.new(p)
    bmesh.ops.convex_hull(bm, input=bm.verts[:])
    for v in list(bm.verts):
        if not v.link_faces:
            bm.verts.remove(v)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    h = bpy.data.objects.new(name, me)
    coll.objects.link(h)
    for _ in range(30):
        if len(h.data.vertices) <= max_verts:
            break
        mod = h.modifiers.new("dec", "DECIMATE")
        mod.decimate_type = "COLLAPSE"
        mod.ratio = max(0.1, (max_verts * 1.6) / max(len(h.data.polygons), 1))
        apply_modifier(h, mod)
        b2 = bmesh.new()
        b2.from_mesh(h.data)
        _hull_only(b2)
        b2.to_mesh(h.data)
        b2.free()
    # dilate about the centroid by dilate_m along each vertex's direction
    for v in h.data.vertices:
        d = np.array(v.co[:]) - c0
        ln = np.linalg.norm(d)
        if ln > 0:
            v.co = Vector(np.array(v.co[:]) + d / ln * dilate_m)
    _grow_to_contain(h, np.asarray(pts_m))
    b3 = bmesh.new()
    b3.from_mesh(h.data)
    bmesh.ops.dissolve_limit(b3, angle_limit=0.0005, verts=b3.verts[:], edges=b3.edges[:])
    bmesh.ops.triangulate(b3, faces=b3.faces[:])
    b3.to_mesh(h.data)
    b3.free()
    _grow_to_contain(h, np.asarray(pts_m))
    h.data.materials.clear()
    h.parent = parent
    h.matrix_parent_inverse = Matrix.Identity(4)
    h.hide_render = True
    h.display_type = "WIRE"
    h["ue_collision"] = "UCX"
    return h


def inside_union(points_m, hulls, tol_m=1e-7):
    """Bool per point: inside at least one convex hull (plane test)."""
    ins = np.zeros(len(points_m), bool)
    for h in hulls:
        M = np.array(h.matrix_world)
        me = h.data
        V = np.array([(M @ np.r_[v.co[:], 1.0])[:3] for v in me.vertices])
        ok = np.ones(len(points_m), bool)
        for p in me.polygons:
            n = np.array(p.normal[:])
            n = M[:3, :3] @ n
            n /= np.linalg.norm(n)
            d = float(n @ V[p.vertices[0]])
            ok &= points_m @ n - d <= tol_m
        ins |= ok
    return ins


# ====================================================================== sockets
UE_MIRROR = np.diag([1.0, -1.0, 1.0])


def ue_rotator_matrix(roll, pitch, yaw):
    """Unreal's rotator as a matrix: Rz(yaw) @ Ry(-pitch) @ Rx(roll) (pipeline.helpers.ue_rotator's inverse)."""
    return (np.array(Matrix.Rotation(math.radians(yaw), 3, "Z")) @ np.array(Matrix.Rotation(math.radians(-pitch), 3, "Y"))
            @ np.array(Matrix.Rotation(math.radians(roll), 3, "X")))


def blender_euler_for_ue(roll, pitch, yaw):
    """The Blender-local rotation whose Unreal image (mirror y) is the rotator: R_bl = M R_ue M."""
    R = UE_MIRROR @ ue_rotator_matrix(roll, pitch, yaw) @ UE_MIRROR
    return tuple(Matrix(R.tolist()).to_euler("XYZ"))


# ====================================================================== mass
def signed_volume_centroid(o):
    """Volume (mm^3) and centroid (mm, world) of a closed mesh (divergence theorem over its triangles)."""
    V, T = mesh_vt(o)
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    v6 = np.einsum("ij,ij->i", a, np.cross(b, c))
    vol = v6.sum() / 6.0
    if abs(vol) < 1e-9:
        return 0.0, V.mean(0)
    cen = ((a + b + c) * v6[:, None]).sum(0) / (4.0 * v6.sum())
    return float(vol), cen
