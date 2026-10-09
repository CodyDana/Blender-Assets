"""Tangent-safe meshes (Blender side; import inside Blender).

STATUS (AR-01 stage 8, 2026-10-09): DIAGNOSTICS + EXPERIMENTAL FIXES, NOT WIRED INTO ANY BUILD.
- Reliable and used by the stage-8 harness: unreal_drops() reproduces exactly the triangles Unreal 5.8's static FBX
  import drops (measured: equal to Unreal's own counts at every LOD of SM_AR01 / SM_AR01_Mag); collapsed() /
  float32_zero_corners() / edge_on_corners() flag the corners whose MikkTSpace frame collapses (conservative).
- The fixes (unreal_safe = unreal_min_area + make_tangent_safe) made the stage-8 test meshes import with 0 warnings,
  0 dropped triangles and 0 zero tangents in Unreal, but on the export meshes they also opened 3-face edges, moved
  vertices up to ~1 mm, put UVs outside their tile and multiplied Unreal's generated-lightmap overlaps; the link-checked
  live-bmesh variant oscillates without converging. Kept for the method change the stage-8 summary recommends (fix the
  micro strips where the part generators make them), not for use as an export step.

Unreal 5.8's static-mesh FBX import computes MikkTSpace tangents from the exported triangles, corner normals and UV0
and logs "has some nearly zero tangents / bi-normals" and "has degenerate tangent bases" for any vertex instance whose
tangent frame collapses (measured at the AR-01 stage-8 import: SM_AR01 and SM_AR01_Mag; the skeletal import computes the
same frames without a warning). Blender's mesh.calc_tangents is the same MikkTSpace code, so the collapsed corners can
be found and fixed here, before export, and the fix is accepted only when Blender's MikkTSpace finds none left.

Why a corner collapses (measured on the stage-7 bytes, gunlib.tspace diagnostics in WorkFiles/guns/rifle/UnrealCheck):
- A: a needle corner of a micro strip (bevel / boolean run-outs 4-25 microns wide): MikkTSpace weights each face by its
  corner angle in the tangent plane, a 0.01 deg corner rounds to 0 in float32, and a corner alone in its UV / normal
  group then gets no tangent at all. Fix: collapse the strip's short edge to its midpoint (custom normals kept).
- B: a face whose UV collapsed onto a line or a point (LOD faces snapped onto a LOD0 island edge, UV area below 1e-3
  texel^2): tangent and bitangent come out parallel ("degenerate tangent basis") or zero. Fix: the face gets its own
  UV corners, a 0.5-texel copy of its 3D shape at its old UV centroid, wound like the rest of its material (it sampled
  one texel line or point before, so its colour does not change).
- C: a face seen edge-on by its own corner normal (a narrow bevel / side face carrying its neighbour's shading normal):
  the face projects onto a line in the tangent plane, its corner angle is 0 again. Fix: tilt that corner's normal
  towards the face normal by a few degrees (the corner is alone in its group, so no other corner's shading moves).
Tried (stage 8) as an export conditioning step on the joined export meshes (rifle_rig: SK_AR01 LOD0-3 and the twin;
rifle_mag: SM_AR01_Mag LOD0-3), after every stage gate measured the part objects; unreal_safe reports the largest
vertex move against the gated mesh. All three moves are below a texel / a pixel at the closest view (A: collapses edges <= 50 microns or needles under
20 microns high, B: <= 0.5 texel, C: <= 15 deg on the corner of a face seen edge-on).
"""
from __future__ import annotations

import math
from typing import Dict, Optional

import numpy as np


def texels(me, UV, texel_uv):
    """One texel in UV units per corner: None (4096), a scalar, a callable uv(N,2) -> (N,), or {"by_slot": {i: t}}
    (per material slot)."""
    if isinstance(texel_uv, dict) and "by_slot" in texel_uv:
        mi = np.empty(len(me.polygons), np.int64)
        me.polygons.foreach_get("material_index", mi)
        lt = np.empty(len(me.polygons), np.int64)
        me.polygons.foreach_get("loop_total", lt)
        per_face = np.array([texel_uv["by_slot"].get(int(m), 1.0 / 4096) for m in mi], float)
        return np.repeat(per_face, lt)
    if callable(texel_uv):
        return np.asarray(texel_uv(UV), float)
    return np.full(len(UV), 1.0 / 4096 if texel_uv is None else float(texel_uv))


def frames(me, uvmap: str):
    """MikkTSpace tangent / bitangent per corner (Blender's calc_tangents, the same code Unreal uses)."""
    me.calc_tangents(uvmap=uvmap)
    n = len(me.loops)
    T = np.empty(n * 3, np.float32)
    B = np.empty(n * 3, np.float32)
    me.loops.foreach_get("tangent", T)
    me.loops.foreach_get("bitangent", B)
    me.free_tangents()
    return T.reshape(-1, 3).astype(float), B.reshape(-1, 3).astype(float)


def collapsed(me, uvmap: Optional[str] = None, eps: float = 1e-4, unreal: bool = True,
              theta_min_deg: float = 0.05) -> np.ndarray:
    """Corners whose tangent or bitangent is shorter than eps, or whose tangent x bitangent is (Unreal's 1e-4), by
    Blender's MikkTSpace; with unreal=True also the corners float32_zero_corners finds (Unreal's stricter result)."""
    if not me.uv_layers or not len(me.loops):
        return np.zeros(0, int)
    T, B = frames(me, uvmap or me.uv_layers[0].name)
    tl = np.linalg.norm(T, axis=1)
    bl = np.linalg.norm(B, axis=1)
    cr = np.linalg.norm(np.cross(T, B), axis=1)
    bad = np.where((tl < eps) | (bl < eps) | (cr < eps))[0]
    if unreal:
        bad = np.union1d(bad, float32_zero_corners(me, uvmap, theta_min_deg))
        bad = np.union1d(bad, edge_on_corners(me, uvmap))
    return bad


def float32_zero_corners(me, uvmap: Optional[str] = None, theta_min_deg: float = 0.1) -> np.ndarray:
    """Corners whose MikkTSpace tangent group gets (almost) no angle weight: every face of the group (same vertex,
    corner normal and UV, same UV winding) meets the vertex at a corner angle below theta_min_deg once projected onto
    the plane normal to the corner normal. Unreal's MikkTSpace (float32 acos, degenerate fix-up off) returns a zero
    tangent there even where Blender's port still finds one (measured: the stage-8 tangent test)."""
    uvmap = uvmap or me.uv_layers[0].name
    UV, LV, V, CN = _arrays(me, uvmap)
    nl = len(LV)
    ls = np.empty(len(me.polygons), np.int64)
    lt = np.empty(len(me.polygons), np.int64)
    me.polygons.foreach_get("loop_start", ls)
    me.polygons.foreach_get("loop_total", lt)
    nxt = np.empty(nl, np.int64)
    prv = np.empty(nl, np.int64)
    face = np.empty(nl, np.int64)
    for f, (a, n) in enumerate(zip(ls, lt)):
        idx = np.arange(a, a + n)
        nxt[idx] = np.roll(idx, -1)
        prv[idx] = np.roll(idx, 1)
        face[idx] = f
    P = V[LV]
    e1 = V[LV[nxt]] - P
    e2 = V[LV[prv]] - P
    n = CN / np.maximum(np.linalg.norm(CN, axis=1), 1e-12)[:, None]
    e1 = e1 - n * (e1 * n).sum(1)[:, None]
    e2 = e2 - n * (e2 * n).sum(1)[:, None]
    ang = np.degrees(np.arctan2(np.linalg.norm(np.cross(e1, e2), axis=1), (e1 * e2).sum(1)))
    # face UV winding (MikkTSpace splits groups by it)
    u0 = UV[ls]
    area = np.zeros(len(ls))
    for k in range(1, int(lt.max()) - 1):
        ok = lt > k + 1
        a = UV[np.minimum(ls + k, nl - 1)] - u0
        b = UV[np.minimum(ls + k + 1, nl - 1)] - u0
        area += np.where(ok, a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0], 0.0)
    wind = np.sign(area)[face]
    key = np.c_[LV, np.round(CN * 1e5), np.round(UV * 1e7), wind]
    _, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.ravel()
    best = np.zeros(inv.max() + 1)
    np.maximum.at(best, inv, ang)
    return np.nonzero(best[inv] < theta_min_deg)[0]


def mikk_float32(me, uvmap: Optional[str] = None, scale: float = 0.1):
    """A float32 re-run of MikkTSpace's per-vertex accumulation as Unreal calls it (genTangSpaceDefault, degenerate
    fix-up off): per face vOs = normalize(t31.y*d1 - t21.y*d2) * sign(UV area) (none when the float32 UV area is 0),
    per corner the angle between the two edges projected onto the plane normal to the corner normal (float32 acos),
    groups = corners with the same position, normal, UV and UV winding. Returns |sum of angle x projected vOs| per
    corner (0 = Unreal stores a zero tangent). Positions in Unreal centimetres (scale: mesh units -> cm)."""
    uvmap = uvmap or me.uv_layers[0].name
    UV, LV, V, CN = _arrays(me, uvmap)
    f32 = np.float32
    UV = UV.astype(f32)
    P = (V * scale).astype(f32)[LV]
    CN = CN.astype(f32)
    nl = len(LV)
    ls = np.empty(len(me.polygons), np.int64)
    lt = np.empty(len(me.polygons), np.int64)
    me.polygons.foreach_get("loop_start", ls)
    me.polygons.foreach_get("loop_total", lt)
    if (lt != 3).any():
        raise ValueError("mikk_float32 expects triangles")
    i0, i1, i2 = ls, ls + 1, ls + 2
    d1 = P[i1] - P[i0]
    d2 = P[i2] - P[i0]
    t21 = UV[i1] - UV[i0]
    t31 = UV[i2] - UV[i0]
    area = (t21[:, 0] * t31[:, 1] - t21[:, 1] * t31[:, 0]).astype(f32)
    vOs = (t31[:, 1:2] * d1 - t21[:, 1:2] * d2).astype(f32)
    ln = np.linalg.norm(vOs, axis=1).astype(f32)
    good = (np.abs(area) > np.finfo(f32).tiny) & (ln > np.finfo(f32).tiny)
    vOs = np.where(good[:, None], vOs / np.maximum(ln, 1e-30)[:, None] * np.sign(area)[:, None], 0).astype(f32)
    face = np.repeat(np.arange(len(ls)), 3)
    corner = np.arange(nl)
    k = corner - ls[face]
    nxt = ls[face] + (k + 1) % 3
    prv = ls[face] + (k + 2) % 3
    n = CN
    v1 = (P[prv] - P[corner]).astype(f32)   # mikk: p0 - p1 and p2 - p1 around the corner p1
    v2 = (P[nxt] - P[corner]).astype(f32)
    v1 = v1 - n * (v1 * n).sum(1, keepdims=True)
    v2 = v2 - n * (v2 * n).sum(1, keepdims=True)
    l1 = np.linalg.norm(v1, axis=1)
    l2 = np.linalg.norm(v2, axis=1)
    v1 = np.where(l1[:, None] > 0, v1 / np.maximum(l1, 1e-30)[:, None], v1).astype(f32)
    v2 = np.where(l2[:, None] > 0, v2 / np.maximum(l2, 1e-30)[:, None], v2).astype(f32)
    c = np.clip((v1 * v2).sum(1).astype(f32), -1, 1)
    ang = np.arccos(c).astype(f32)
    vo = vOs[face]
    vo = vo - n * (vo * n).sum(1, keepdims=True)
    lo = np.linalg.norm(vo, axis=1)
    vo = np.where(lo[:, None] > 0, vo / np.maximum(lo, 1e-30)[:, None], vo)
    contrib = vo * ang[:, None]
    wind = np.sign(area)[face]
    base = np.c_[np.round(P.astype(float) * 1e6), np.round(CN.astype(float) * 1e6), np.round(UV.astype(float) * 1e9)]
    key = np.c_[base, wind]
    _, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.ravel()
    acc = np.zeros((inv.max() + 1, 3))
    np.add.at(acc, inv, contrib)
    mag = np.linalg.norm(acc, axis=1)[inv]
    # GROUP_WITH_ANY: a corner of a face with zero float32 UV area joins a group of either winding at the same welded
    # vertex (position, normal, UV) and takes its tangent; alone, it gets none
    degen_c = ~good[face]
    if degen_c.any():
        _, inv2 = np.unique(base, axis=0, return_inverse=True)
        inv2 = inv2.ravel()
        best = np.zeros(inv2.max() + 1)
        np.maximum.at(best, inv2[~degen_c], mag[~degen_c])
        mag = np.where(degen_c, best[inv2], mag)
    return mag


def edge_on_corners(me, uvmap: Optional[str] = None, max_dot: float = 0.1) -> np.ndarray:
    """Corners of tangent groups (vertex, corner normal, UV) whose every face is seen edge-on by the group's normal
    (|face normal . corner normal| < max_dot): each face projects onto a line in the tangent plane, its corner angle is
    0 or 180 degrees and Unreal's MikkTSpace can return no tangent (measured on the AR-01 LOD1 / LOD2 end caps)."""
    uvmap = uvmap or me.uv_layers[0].name
    UV, LV, V, CN = _arrays(me, uvmap)
    fn = np.empty(len(me.polygons) * 3)
    me.polygons.foreach_get("normal", fn)
    fn = fn.reshape(-1, 3)
    ls = np.empty(len(me.polygons), np.int64)
    lt = np.empty(len(me.polygons), np.int64)
    me.polygons.foreach_get("loop_start", ls)
    me.polygons.foreach_get("loop_total", lt)
    face = np.repeat(np.arange(len(ls)), lt)
    dot = np.abs((fn[face] * CN).sum(1))
    key = np.c_[LV, np.round(CN * 1e5), np.round(UV * 1e9)]
    _, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.ravel()
    best = np.zeros(inv.max() + 1)
    np.maximum.at(best, inv, dot)
    return np.nonzero(best[inv] < max_dot)[0]


def tiny_uv_faces(me, UV, tex, rel=1e-3, rel_h=0.01):
    """Faces whose UV area is below rel x (one texel)^2 or whose UV height over the longest UV edge is below rel_h
    texel (a few float32 ulps of a 0..1 UV: Unreal reads UVs as float32, so such a face can land on exactly zero
    area)."""
    ls = np.empty(len(me.polygons), np.int64)
    lt = np.empty(len(me.polygons), np.int64)
    me.polygons.foreach_get("loop_start", ls)
    me.polygons.foreach_get("loop_total", lt)
    nl = len(UV)
    u0 = UV[ls]
    area = np.zeros(len(ls))
    for k in range(1, int(lt.max()) - 1):
        ok = lt > k + 1
        a = UV[np.minimum(ls + k, nl - 1)] - u0
        b = UV[np.minimum(ls + k + 1, nl - 1)] - u0
        area += np.where(ok, 0.5 * (a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]), 0.0)
    longest = np.zeros(len(ls))
    for k in range(int(lt.max())):
        i0 = ls + np.minimum(k, lt - 1)
        i1 = ls + (np.minimum(k, lt - 1) + 1) % lt
        longest = np.maximum(longest, np.linalg.norm(UV[i1] - UV[i0], axis=1))
    height = 2.0 * np.abs(area) / np.maximum(longest, 1e-15)
    t = tex[ls]
    return np.nonzero((np.abs(area) < rel * t ** 2) | (height < rel_h * t))[0].tolist()


def _arrays(me, uvmap):
    nl = len(me.loops)
    UV = np.empty(nl * 2, np.float32)
    me.uv_layers[uvmap].data.foreach_get("uv", UV)
    LV = np.empty(nl, np.int64)
    me.loops.foreach_get("vertex_index", LV)
    V = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", V)
    CN = np.array([c.vector[:] for c in me.corner_normals], float)
    return UV.reshape(-1, 2).astype(float), LV, V.reshape(-1, 3).astype(float), CN


def _bm_begin(ob):
    import bmesh
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    cn = me.corner_normals
    lay = bm.loops.layers.float_vector.new("_cn")
    li = 0
    bm.faces.ensure_lookup_table()
    for f in bm.faces:                       # bmesh loops come face by face in mesh order
        for lp in f.loops:
            lp[lay] = cn[li].vector
            li += 1
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    return bm, lay


def _bm_end(ob, bm, lay):
    me = ob.data
    per_loop = [tuple(lp[lay]) for f in bm.faces for lp in f.loops]
    bm.loops.layers.float_vector.remove(lay)
    bm.to_mesh(me)
    bm.free()
    if len(per_loop) == len(me.loops):
        me.normals_split_custom_set(per_loop)
    me.update()


def _ring(v):
    return {e.other_vert(v) for e in v.link_edges}


def _link_ok(bm, va, vb):
    """Edge-collapse link condition: the two vertices share no neighbour beyond the apexes of the faces on their edge,
    so welding them cannot make an edge with three faces or a duplicate face."""
    common = (_ring(va) & _ring(vb)) - {va, vb}
    ed = bm.edges.get((va, vb))
    return len(common) <= (len(ed.link_faces) if ed is not None else 0)


def _snap_uvs(bm, verts, uv_snap):
    """A welded vertex's corners keep their own UVs: corners whose UVs lie within uv_snap of each other (the two ends of
    the collapsed micro edge, a fraction of a texel) take one shared UV again, so no UV seam opens and the UV / lightmap
    charts stay whole."""
    for uvl in bm.loops.layers.uv.values():
        for v in verts:
            if not v.is_valid:
                continue
            loops = list(v.link_loops)
            done = set()
            for i, l in enumerate(loops):
                if i in done:
                    continue
                u0 = l[uvl].uv.copy()
                group = [i] + [k for k in range(i + 1, len(loops)) if k not in done and (loops[k][uvl].uv - u0).length <= uv_snap]
                if len(group) > 1:
                    for k in group:
                        loops[k][uvl].uv = u0
                done.update(group)


def _collapse_edges(ob, pairs, uv_snap: float = 2.0 / 4096):
    """Weld each (a, b) vertex pair at its midpoint (bmesh), corner normals carried in a loop layer and set again; a pair
    is skipped when it fails the link condition or touches a vertex (or its 1-ring) already edited in this call."""
    import bmesh
    bm, lay = _bm_begin(ob)
    targetmap = {}
    used = set()
    for a, b in pairs:
        if a == b:
            continue
        va, vb = bm.verts[a], bm.verts[b]
        if va in used or vb in used or not _link_ok(bm, va, vb):
            continue
        mid = (va.co + vb.co) * 0.5
        va.co = mid
        vb.co = mid
        # keep the vertex with the lower index (the twin and the shipped magazine are built from the same parts in
        # the same order, so both keep the same one)
        keep, drop = (va, vb) if a < b else (vb, va)
        targetmap[drop] = keep
        used.update({va, vb} | _ring(va) | _ring(vb))
    keeps = list(set(targetmap.values()))
    if targetmap:
        bmesh.ops.weld_verts(bm, targetmap=targetmap)
    _snap_uvs(bm, keeps, uv_snap)
    _bm_end(ob, bm, lay)
    return len(targetmap)


def _split_needles(ob, needles, uv_snap: float = 2.0 / 4096):
    """Remove needle triangles without moving anything more than the needle's height: split the long edge at the apex's
    projection and weld the apex onto the new vertex (the needle disappears, the neighbour across the edge becomes
    two triangles). needles: (apex, u, v) vertex indices."""
    import bmesh
    bm, lay = _bm_begin(ob)
    targetmap = {}
    used = set()
    refs = [(bm.verts[w], bm.verts[u], bm.verts[v]) for w, u, v in needles]     # before any split adds vertices
    for vw, vu, vv in refs:
        if not (vw.is_valid and vu.is_valid and vv.is_valid):
            continue
        if used & ({vw, vu, vv} | _ring(vw) | _ring(vu) | _ring(vv)):
            continue
        ed = bm.edges.get((vu, vv))
        if ed is None or len(ed.link_faces) > 2:
            continue
        others = {x for f in ed.link_faces for x in f.verts} - {vu, vv, vw}
        if others & _ring(vw):
            continue
        d = vv.co - vu.co
        t = max(0.02, min(0.98, (vw.co - vu.co).dot(d) / max(d.length_squared, 1e-30)))
        ne, nv = bmesh.utils.edge_split(ed, vu, t)
        targetmap[vw] = nv
        used.update({vw, vu, vv, nv} | _ring(vw) | _ring(vu) | _ring(vv))
    if targetmap:
        bmesh.ops.weld_verts(bm, targetmap=targetmap)
        ngons = [f for f in bm.faces if len(f.verts) > 3]
        if ngons:
            bmesh.ops.triangulate(bm, faces=ngons)
    _snap_uvs(bm, list(set(targetmap.values())), uv_snap)
    _bm_end(ob, bm, lay)
    return len(targetmap)


def make_tangent_safe(ob, texel_uv=None, uvmap: Optional[str] = None, short_mm: float = 0.05,
                      max_rounds: int = 48, max_tilt_deg: float = 15.0,
                      theta_min_deg: float = 0.05) -> Dict:
    """Fix every collapsed MikkTSpace corner of `ob` (see the module note). texel_uv: one texel in UV units (scalar, or
    callable uv(N,2) -> (N,) for per-set atlas sizes). Object scale: the mesh is in metres (object transform applied).
    Returns a report; 'collapsed_after' must be 0."""
    me = ob.data
    if not me.uv_layers or not len(me.polygons):
        return {"skipped": "no UV / no faces"}
    uvmap = uvmap or me.uv_layers[0].name
    sc = float(ob.matrix_world.to_scale()[0]) * 1000.0      # mesh units -> mm
    bad = collapsed(me, uvmap, theta_min_deg=theta_min_deg)
    rep = {"collapsed_before": int(len(bad)), "A_edges_collapsed": 0, "B_uv_moves": 0, "C_normal_tilts": 0,
           "max_uv_move_texels": 0.0, "max_tilt_deg": 0.0, "rounds": 0}
    for rnd in range(max_rounds):
        if len(bad) == 0:
            UV0, _, _, _ = _arrays(me, uvmap)
            tex0 = texels(me, UV0, texel_uv)
            if not tiny_uv_faces(me, UV0, tex0):
                break
        rep["rounds"] = rnd + 1
        UV, LV, V, CN = _arrays(me, uvmap)
        tex = texels(me, UV, texel_uv)
        lp_face = np.empty(len(me.loops), np.int64)
        for p in me.polygons:
            lp_face[p.loop_start:p.loop_start + p.loop_total] = p.index
        pairs, needles, degen, tilts = [], [], set(), {}
        # every face whose UV area is below 1e-3 texel^2 (a point or a line: Unreal's MikkTSpace gives its lone corners
        # no usable frame even where Blender's port borrows one from a neighbour)
        for fi in tiny_uv_faces(me, UV, tex):
            p = me.polygons[fi]
            vid = list(p.vertices)
            P = V[vid] * sc
            n = len(vid)
            e = sorted((float(np.linalg.norm(P[(k + 1) % n] - P[k])), vid[k], vid[(k + 1) % n]) for k in range(n))
            area2 = float(np.linalg.norm(sum(np.cross(P[k] - P[0], P[k + 1] - P[0]) for k in range(1, n - 1))))
            if e[0][0] < short_mm:                                            # a micro face: collapse its edge
                pairs.append((e[0][1], e[0][2]))
            elif n == 3 and area2 / max(e[-1][0], 1e-12) < 0.05:              # a 3D needle: split it away
                u_, v_ = e[-1][1], e[-1][2]
                needles.append((next(x for x in vid if x not in (u_, v_)), u_, v_))
            else:
                degen.add(fi)
        Tf, Bf = frames(me, uvmap)
        tlen = np.linalg.norm(Tf, axis=1)
        z32 = np.zeros(len(tlen), bool)
        z32[float32_zero_corners(me, uvmap, theta_min_deg)] = True
        eon = np.zeros(len(tlen), bool)
        eon[edge_on_corners(me, uvmap)] = True
        for li in bad:
            p = me.polygons[int(lp_face[li])]
            L = list(p.loop_indices)
            vid = [int(LV[j]) for j in L]
            P = V[vid] * sc
            n = len(L)
            e = [(float(np.linalg.norm(P[(k + 1) % n] - P[k])), vid[k], vid[(k + 1) % n]) for k in range(n)]
            e.sort()
            needle = z32[li] or (tlen[li] < 1e-4 and not eon[li])   # the corner's angle weight rounds to 0
            angle_type = needle or eon[li] or tlen[li] < 1e-4
            area2 = float(np.linalg.norm(sum(np.cross(P[k] - P[0], P[k + 1] - P[0]) for k in range(1, n - 1))))
            height = area2 / max(e[-1][0], 1e-12)          # the face's height over its longest edge, mm
            if needle and e[0][0] < short_mm:                               # A: micro strip
                pairs.append((e[0][1], e[0][2]))
                continue
            if needle and n == 3 and height < 0.05:                         # A: collinear needle (split, no collapse)
                u_, v_ = e[-1][1], e[-1][2]
                needles.append((next(x for x in vid if x not in (u_, v_)), u_, v_))
                continue
            if angle_type:                                                   # C: face edge-on to its corner normal
                tilts[int(li)] = np.array(p.normal[:], float)
                continue
            U = UV[L]
            ua = 0.0
            for k in range(1, n - 1):
                ua += 0.5 * ((U[k][0] - U[0][0]) * (U[k + 1][1] - U[0][1]) - (U[k + 1][0] - U[0][0]) * (U[k][1] - U[0][1]))
            tx = float(tex[L[0]])
            ulen = max(float(np.linalg.norm(U[(k + 1) % n] - U[k])) for k in range(n))
            # a tangent but no independent bitangent: the face's UV is on a line or a point (B / D); the face with the
            # smallest UV area of the corner's faces is the degenerate one
            degen.add(p.index)
        # ---- A
        if pairs or needles:
            got = _collapse_edges(ob, pairs) if pairs else 0
            if not got and needles:
                got = _split_needles(ob, needles)
            rep["A_edges_collapsed"] += got
            bad = collapsed(me, uvmap, theta_min_deg=theta_min_deg)
            if got:
                continue                       # indices changed: B / C run on the next round's classification
        # ---- B / D: give each degenerate UV face its own tiny copy of its 3D shape (0.5 texel across) at its old UV
        # centroid
        if degen:
            key = {}
            for i in range(len(LV)):
                key.setdefault((int(LV[i]), round(float(UV[i, 0]), 9), round(float(UV[i, 1]), 9)), []).append(i)
            good_loop = np.ones(len(LV), bool)
            for fi in degen:
                pp = me.polygons[fi]
                good_loop[pp.loop_start:pp.loop_start + pp.loop_total] = False
            mi = np.empty(len(me.polygons), np.int64)
            me.polygons.foreach_get("material_index", mi)
            fsign = {}
            for pp in me.polygons:
                if pp.index in degen:
                    continue
                L = list(pp.loop_indices)
                U = UV[L]
                a = sum((U[k][0] - U[0][0]) * (U[k + 1][1] - U[0][1]) - (U[k + 1][0] - U[0][0]) * (U[k][1] - U[0][1])
                        for k in range(1, len(L) - 1))
                fsign.setdefault(int(mi[pp.index]), []).append(a)
            wsign = {m: (1.0 if (np.array(v) > 0).sum() >= (np.array(v) < 0).sum() else -1.0) for m, v in fsign.items()}
            done = set()
            for fi in sorted(degen):
                pp = me.polygons[fi]
                L = list(pp.loop_indices)
                tx = float(tex[L[0]])
                P = V[[int(LV[j]) for j in L]] * sc
                c3 = P.mean(0)
                ax = P[1] - P[0]
                if np.linalg.norm(ax) < 1e-9:
                    ax = P[2] - P[0]
                ax /= max(np.linalg.norm(ax), 1e-12)
                fn = np.array(pp.normal[:], float)
                ay = np.cross(fn, ax)
                Q = np.c_[(P - c3) @ ax, (P - c3) @ ay]
                # each axis spread on its own (0.5 texel along the face, >= 0.25 texel across): a needle face gets a
                # UV height of many float32 ulps
                for c in (0, 1):
                    span = float(Q[:, c].max() - Q[:, c].min())
                    Q[:, c] = (Q[:, c] - Q[:, c].mean()) / max(span, 1e-12) * (0.5 if c == 0 else 0.25) * tx
                Q[:, 1] *= wsign.get(int(mi[fi]), 1.0)
                cu = UV[L].mean(0)
                # the face gets its own UV corners (a sub-texel island at its old UV centroid): a one-face seam on a face
                # that already sampled a single texel line / point, so nothing visible changes
                for k, j in enumerate(L):
                    UV[j] = cu + Q[k]
                moved_any = True
                rep["B_uv_moves"] += 1
                rep["max_uv_move_texels"] = max(rep["max_uv_move_texels"], 0.5)
            me.uv_layers[uvmap].data.foreach_set("uv", UV.astype(np.float32).ravel())
            me.update()
        # ---- C
        if tilts:
            new = CN.copy()
            gkey = {}
            for i in range(len(LV)):
                gkey.setdefault((int(LV[i]), tuple(np.round(CN[i], 5)), round(float(UV[i, 0]), 9), round(float(UV[i, 1]), 9)), []).append(i)
            seen = set()
            for li, fn in tilts.items():
                k = (int(LV[li]), tuple(np.round(CN[li], 5)), round(float(UV[li, 0]), 9), round(float(UV[li, 1]), 9))
                if k in seen:
                    continue
                seen.add(k)
                c = CN[li]
                ang = math.degrees(math.acos(max(-1.0, min(1.0, float(c @ fn)))))
                t = min(max_tilt_deg, ang, 2.0 * (rnd + 1))
                ax = np.cross(c, fn)
                if np.linalg.norm(ax) < 1e-9:
                    continue
                ax /= np.linalg.norm(ax)
                th = math.radians(t)
                r = c * math.cos(th) + np.cross(ax, c) * math.sin(th) + ax * (ax @ c) * (1 - math.cos(th))
                for j in gkey.get(k, [li]):        # the whole tangent group turns together (it stays one group)
                    new[j] = r / np.linalg.norm(r)
                rep["C_normal_tilts"] += 1
                rep["max_tilt_deg"] = max(rep["max_tilt_deg"], t)
            me.normals_split_custom_set([tuple(x) for x in new])
            me.update()
        bad = collapsed(me, uvmap, theta_min_deg=theta_min_deg)
    rep["collapsed_after"] = int(len(bad))
    UV1, _, _, _ = _arrays(me, uvmap)
    tex1 = texels(me, UV1, texel_uv)
    rep["tiny_uv_faces_after"] = len(tiny_uv_faces(me, UV1, tex1))
    if len(bad):
        Tf, Bf = frames(me, uvmap)
        UV, LV, V, CN = _arrays(me, uvmap)
        lp_face = {}
        for p in me.polygons:
            for j in p.loop_indices:
                lp_face[j] = p
        rep["left"] = []
        for li in bad[:6]:
            p = lp_face[int(li)]
            L = list(p.loop_indices)
            rep["left"].append({"T": np.round(Tf[li], 3).tolist(), "B": np.round(Bf[li], 3).tolist(),
                                "cn": np.round(CN[li], 3).tolist(), "fn": np.round(p.normal[:], 3).tolist(),
                                "P_mm": np.round(V[[int(LV[j]) for j in L]] * sc, 3).tolist(),
                                "UV": np.round(UV[L], 6).tolist()})
    return rep


# ====================================================================== Unreal's degenerate-triangle drop
UNREAL_MIN_CROSS_CM2 = 1e-4     # FFbxImporter::BuildStaticMeshFromGeometry: GetSafeNormal(SMALL_NUMBER) on cross(cm)


def unreal_drops(ob) -> np.ndarray:
    """Faces Unreal 5.8's static FBX import drops with Remove Degenerates on (the default): |cross of two edges|^2 <
    1e-8 in centimetres, float32 (FbxStaticMeshImport.cpp GetTriangleAreaThreshold), i.e. area < 0.005 mm^2. Measured
    on the stage-8 import: the prediction equals Unreal's own triangle counts at every LOD of SM_AR01 / SM_AR01_Mag."""
    me = ob.data
    s = float(ob.matrix_world.to_scale()[0]) * 100.0            # mesh units -> cm
    V = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", V)
    V = (V.reshape(-1, 3) * s).astype(np.float32)
    out = []
    for p in me.polygons:
        vs = list(p.vertices)
        for k in range(1, len(vs) - 1):
            a, b, c = V[vs[0]], V[vs[k]], V[vs[k + 1]]
            cr = np.cross(b - c, a - c).astype(np.float64)
            if (cr ** 2).sum() < 1e-8:
                out.append(p.index)
                break
    return np.array(out, np.int64)


def unreal_min_area(ob, margin: float = 2.0, short_mm: float = 0.05, needle_mm: float = 0.05,
                    max_ops: int = 200000, max_passes: int = 60, verbose: bool = False, dissolve_mm: float = 0.25) -> Dict:
    """Remove every face Unreal would drop (and those within `margin` x its threshold: area < 0.01 mm^2), one face at a
    time in one live bmesh, without moving any vertex more than half a micro edge (<= short_mm / 2) or a needle's height
    (<= needle_mm):
    - a face with an edge under short_mm: that edge collapses to its midpoint (link condition checked, so no edge ever
      gets a third face);
    - a needle (height under needle_mm): its long edge is split at the apex's projection and the apex merged onto the
      new vertex (the needle disappears, the neighbour across the edge becomes two triangles);
    - otherwise the face's longest edge is flipped.
    Corner normals ride along in a loop layer; corners of a merged vertex whose UVs were within a fraction of a texel
    take one UV (no seam opens). Faces this small are invisible at any view and Unreal would delete them anyway,
    leaving hairline cracks. Returns counts; unreal_drops_after must be 0."""
    import bmesh
    me = ob.data
    s = float(ob.matrix_world.to_scale()[0]) * 1000.0            # mesh units -> mm
    thr = 0.005 * margin / (s * s)                                # mesh units^2
    short = short_mm / s
    ndl = needle_mm / s
    dis = dissolve_mm / s
    rep = {"faces_before": len(me.polygons), "unreal_drops_before": int(len(unreal_drops(ob))),
           "collapsed": 0, "needles_split": 0, "flipped": 0, "dissolved": 0, "stuck": 0}
    bm, lay = _bm_begin(ob)
    uvls = list(bm.loops.layers.uv.values())
    stuck = set()
    flipped = set()                    # each vertex pair flips once (no ping-pong)
    ops = 0

    def area(f):
        return f.calc_area()

    def merge(keep, drop, co):
        """Merge `drop` into `keep` at `co`; snap the merged corners' UVs."""
        keep.co = co
        drop.co = co
        bmesh.ops.pointmerge(bm, verts=[keep, drop], merge_co=co)
        v = keep if keep.is_valid else (drop if drop.is_valid else None)
        if v is not None:
            _snap_uvs(bm, [v], 2.0 / 4096)

    changed = True
    passes = 0
    while changed and ops < max_ops and passes < max_passes:
        changed = False
        passes += 1
        bm.faces.index_update()
        small = [f for f in bm.faces if f.is_valid and area(f) < thr]
        if verbose:
            print("[tspace] pass", passes, "small", len(small), "ops", ops, flush=True)
        for f in small:
            if not f.is_valid or area(f) >= thr:
                continue
            vs = list(f.verts)
            n = len(vs)
            es = sorted(f.edges, key=lambda e: e.calc_length())
            e0 = es[0]
            if e0.calc_length() <= short or n != 3:
                va, vb = e0.verts
                if _link_ok(bm, va, vb):
                    merge(va, vb, (va.co + vb.co) * 0.5)
                    rep["collapsed"] += 1
                    ops += 1
                    changed = True
                    continue
            el = es[-1]
            vu, vv = el.verts
            vw = next(v for v in vs if v not in (vu, vv))
            h = 2.0 * area(f) / max(el.calc_length(), 1e-30)
            if h <= ndl and len(el.link_faces) <= 2:
                others = {x for g in el.link_faces for x in g.verts} - {vu, vv, vw}
                if not (others & _ring(vw)):
                    d = vv.co - vu.co
                    t = max(0.02, min(0.98, (vw.co - vu.co).dot(d) / max(d.length_squared, 1e-30)))
                    ne, nv = bmesh.utils.edge_split(el, vu, t)
                    for g in list(nv.link_faces):
                        if g.is_valid and len(g.verts) > 3:
                            bmesh.ops.triangulate(bm, faces=[g])
                    if _link_ok(bm, nv, vw):
                        merge(nv, vw, nv.co.copy())
                        rep["needles_split"] += 1
                        ops += 1
                        changed = True
                        continue
            key = frozenset((vu.index, vv.index))
            if len(el.link_faces) == 2 and key not in flipped:
                flipped.add(key)
                r = bmesh.ops.rotate_edges(bm, edges=[el], use_ccw=False)
                if r.get("edges"):
                    rep["flipped"] += 1
                    ops += 1
                    changed = True
                    continue
            # last resort: dissolve one of the face's vertices whose whole fan is micro (every edge <= dissolve_mm):
            # its faces merge into one polygon (re-triangulated), nothing moves, the surface changes by at most the
            # fan's size
            done_ = False
            for v in sorted(vs, key=lambda x: max(e.calc_length() for e in x.link_edges)):
                if v.is_valid and not v.is_boundary and max(e.calc_length() for e in v.link_edges) <= dis and len(v.link_faces) >= 3:
                    ring = _ring(v)
                    bmesh.ops.dissolve_verts(bm, verts=[v], use_face_split=False, use_boundary_tear=False)
                    ng = list({g for u in ring if u.is_valid for g in u.link_faces if g.is_valid and len(g.verts) > 3})
                    if ng:
                        bmesh.ops.triangulate(bm, faces=ng)
                    rep["dissolved"] += 1
                    ops += 1
                    changed = done_ = True
                    break
            if done_:
                continue
            stuck.add(f)
        if not changed:
            break
    rep["stuck"] = sum(1 for f in stuck if f.is_valid and area(f) < thr)
    rep["passes"] = passes
    ngons = [f for f in bm.faces if len(f.verts) > 3]
    if ngons:
        bmesh.ops.triangulate(bm, faces=ngons)
    _bm_end(ob, bm, lay)
    rep["faces_after"] = len(me.polygons)
    rep["unreal_drops_after"] = int(len(unreal_drops(ob)))
    return rep


def unreal_safe(ob, texel_uv=None) -> Dict:
    """Both Unreal import rules on one mesh: no face Unreal drops (unreal_min_area), then no collapsed MikkTSpace
    frame (make_tangent_safe), then the drop check again (the tangent pass may collapse micro strips). Gate:
    unreal_drops_after == 0 (exact: Unreal's own rule). collapsed_after counts what the conservative Blender-side
    detectors still flag (they over-report: the stage-8 test meshes with 4 such flags imported with 0 warnings and 0
    zero tangents in Unreal's render data); Unreal's import (stage 8) is the authority there."""
    from mathutils.bvhtree import BVHTree
    me = ob.data
    sc = float(ob.matrix_world.to_scale()[0]) * 1000.0
    V0 = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", V0)
    V0 = V0.reshape(-1, 3)
    F0 = [tuple(p.vertices) for p in me.polygons]
    tree0 = BVHTree.FromPolygons([tuple(v) for v in V0], F0, all_triangles=False, epsilon=0.0)
    CN0 = np.array([c.vector[:] for c in me.corner_normals], float)
    r1 = unreal_min_area(ob)
    r2 = make_tangent_safe(ob, texel_uv=texel_uv)
    r2.pop("left", None)
    r3 = unreal_min_area(ob)
    r4 = make_tangent_safe(ob, texel_uv=texel_uv) if r3["collapsed"] or r3["flipped"] else {"collapsed_after": r2["collapsed_after"]}
    r4.pop("left", None)
    V1 = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", V1)
    V1 = V1.reshape(-1, 3)
    moved = max((tree0.find_nearest(tuple(p))[3] for p in V1), default=0.0) * sc     # distance to the gated surface
    return {"min_area": r1, "tangents": r2, "min_area_2": r3, "tangents_2": r4,
            "max_surface_deviation_mm": round(float(moved), 5), "corners_before": int(len(CN0)),
            "unreal_drops_after": r3["unreal_drops_after"], "collapsed_after": r4["collapsed_after"],
            "faces_before": r1["faces_before"], "faces_after": len(ob.data.polygons),
            "pass": r3["unreal_drops_after"] == 0}
