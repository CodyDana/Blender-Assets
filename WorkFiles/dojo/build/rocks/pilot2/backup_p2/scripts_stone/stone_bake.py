"""High-to-low for unique-UV rocks (STONE_BUILDING_STUDY.md 4.9.5 a, 4.10, 4.12): the shipped Nanite mid from the
dense SDF source, few-chart unique UV0 at the house texel, UV1 for Fab, and the bakes (normal tangent -> DirectX,
masks by emission, AO by the pipeline). bpy + numpy.

The chart unwrap is the pine rock's (Scripts/dojo/pines/rock_v3.py, pines chat; lifted, not edited): faces grouped
by their SMOOTHED normal into the 6 box directions, small pieces merged, charts unwrapped angle-based with seams at
the chart borders, then average-scaled and packed; charts that still fold are split by 26 directions, single pinched
faces become their own charts, until the qa_check SAT overlap test is clean.
"""
from __future__ import annotations

import math
import time
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np

import bpy
import bmesh

import stone_sdf as sd


# ----------------------------------------------------------------------------------------------- objects
def make_obj(name, V, F, coll=None, smooth=True):
    V = np.asarray(V, float)
    F = np.asarray(F, np.int64)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(V))
    me.vertices.foreach_set("co", V.ravel())
    me.loops.add(F.size)
    me.loops.foreach_set("vertex_index", F.ravel())
    me.polygons.add(len(F))
    me.polygons.foreach_set("loop_start", np.arange(0, F.size, 3))
    me.update()
    me.validate()
    if smooth:
        me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    (coll or bpy.context.scene.collection).objects.link(ob)
    return ob


def mesh_arrays(ob):
    me = ob.data
    V = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", V)
    V = V.reshape(-1, 3)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    bm.verts.index_update()
    F = np.array([[v.index for v in f.verts] for f in bm.faces], dtype=np.int64)
    bm.free()
    return V, F


def _apply(ob, md):
    with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob]):
        bpy.ops.object.modifier_apply(modifier=md.name)


def remesh(ob, voxel):
    md = ob.modifiers.new("remesh", "REMESH")
    md.mode = "VOXEL"
    md.voxel_size = voxel
    md.adaptivity = 0.0
    md.use_smooth_shade = True
    _apply(ob, md)


def decimate(ob, target_tris):
    n = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    md = ob.modifiers.new("dec", "DECIMATE")
    md.decimate_type = "COLLAPSE"
    md.ratio = min(1.0, target_tris / max(n, 1))
    md.use_collapse_triangulate = True
    _apply(ob, md)


def set_point_colour(ob, name, cols):
    me = ob.data
    if name in me.color_attributes:
        me.color_attributes.remove(me.color_attributes[name])
    ca = me.color_attributes.new(name, "FLOAT_COLOR", "POINT")
    cols = np.asarray(cols, float)
    if cols.ndim == 1:
        cols = np.repeat(cols[:, None], 3, 1)
    if cols.shape[1] == 3:
        cols = np.concatenate([cols, np.ones((len(cols), 1))], 1)
    ca.data.foreach_set("color", np.clip(cols, 0, 1).astype(np.float32).ravel())
    return ca


# ----------------------------------------------------------------------------------------------- moss cushions
def cushion_shell(Vm, Fm, field, seed, h=(0.008, 0.035), thresh=0.35):
    """Moss cushions where ``field`` (per mid vertex, 0-1) is high: the mid's faces lifted along the normal by a
    lumpy height that fades under the rock at the shell's rim (never coincident with the rock: qa)."""
    sel = (field[Fm] > thresh).all(1)
    if sel.sum() < 20:
        return None
    Fs = Fm[sel]
    used = np.unique(Fs)
    remap = -np.ones(len(Vm), np.int64)
    remap[used] = np.arange(len(used))
    F2 = remap[Fs]
    V2 = Vm[used].copy()
    N2 = sd.vertex_normals(Vm, Fm)[used]
    E2 = sd.edges_of(F2)
    Eall = np.vstack([F2[:, [0, 1]], F2[:, [1, 2]], F2[:, [2, 0]]])
    Eall.sort(1)
    u, cnt = np.unique(Eall, axis=0, return_counts=True)
    rim = np.zeros(len(V2), bool)
    rim[u[cnt == 1].ravel()] = True
    ring = np.where(rim, 0.0, 9.0)
    for _ in range(12):
        nb = np.full(len(V2), 9.0)
        np.minimum.at(nb, E2[:, 0], ring[E2[:, 1]])
        np.minimum.at(nb, E2[:, 1], ring[E2[:, 0]])
        ring = np.minimum(ring, nb + 1.0)
    el = float(np.median(np.linalg.norm(V2[E2[:, 0]] - V2[E2[:, 1]], axis=1)))
    rise = sd.smoothstep(ring * el, 0.0, 0.04)
    rng = np.random.default_rng(seed)
    lump = np.zeros(len(V2))
    cs = V2[rng.choice(len(V2), max(8, len(V2) // 60), replace=False)]
    for c in cs:
        s = rng.uniform(0.02, 0.05)
        lump += np.exp(-((V2 - c) ** 2).sum(1) / (2 * s * s)) * rng.uniform(0.5, 1.0)
    lump = np.clip(lump, 0, 1.4) / 1.4
    fine = 0.5 + 0.5 * sd.vnoise3(V2 * 70.0, seed + 3)
    hh = (h[0] + (h[1] - h[0]) * (0.6 * lump + 0.25 * fine + 0.15 * field[used])) * rise - 0.002 * (1 - rise)
    hh = np.where(hh >= 0, np.maximum(hh, 0.0015), np.minimum(hh, -0.0015))
    V2 = V2 + N2 * hh[:, None]
    return V2, F2, float(hh.max())


def grass_tufts(sites, normals, seed, blades=(22, 40), height=(0.07, 0.24), spread=0.05):
    """Opaque blade tufts (no alpha; study 4.14 'stone is never masked'): each blade a tapered, curved 3-segment
    strip. Returns (V, F, colour) with colour R = height along the blade, G = per-blade random, B = tuft random."""
    rng = np.random.default_rng(seed)
    Vs, Fs, Cs = [], [], []
    off = 0
    for p, n in zip(sites, normals):
        n = sd.unit(np.asarray(n) * 0.5 + np.array([0, 0, 1.0]))
        t = sd.unit(np.cross(n, [1.0, 0.0, 0.0] if abs(n[0]) < 0.9 else [0.0, 1.0, 0.0]))
        b = np.cross(n, t)
        hb = rng.uniform(*height)
        tuft_r = rng.uniform()
        for _ in range(int(rng.integers(*blades))):
            a = rng.uniform(0, 2 * math.pi)
            r = spread * math.sqrt(rng.uniform())
            base = p + (t * math.cos(a) + b * math.sin(a)) * r - n * 0.006
            out = sd.unit(t * math.cos(a) + b * math.sin(a))
            lean = rng.uniform(0.15, 0.7) * (0.5 + r / spread)
            hgt = hb * rng.uniform(0.55, 1.15)
            w = rng.uniform(0.0035, 0.006)
            side = sd.unit(np.cross(out, n) + rng.normal(0, 0.3, 3))
            pts = []
            for k, s in enumerate((0.0, 0.35, 0.7, 1.0)):
                bend = lean * s * s
                c = base + n * hgt * s * (1 - 0.25 * bend) + out * hgt * bend
                ww = w * (1.0 - s) ** 0.8 + 0.0004
                pts += [c - side * ww, c + side * ww]
            Vb = np.array(pts)
            Fb = []
            for k in range(3):
                i0 = 2 * k
                Fb += [(i0, i0 + 1, i0 + 3), (i0, i0 + 3, i0 + 2)]
            Vs.append(Vb)
            Fs.append(np.array(Fb) + off)
            hs = np.repeat([0.0, 0.35, 0.7, 1.0], 2)
            Cs.append(np.column_stack([hs, np.full(8, rng.uniform()), np.full(8, tuft_r)]))
            off += len(Vb)
    if not Vs:
        return None
    return np.vstack(Vs), np.vstack(Fs), np.vstack(Cs)


# ----------------------------------------------------------------------------------------------- UV charts
BOX6 = np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]], float)
DIR26 = np.array([[x, y, z] for x in (-1, 0, 1) for y in (-1, 0, 1) for z in (-1, 0, 1) if (x, y, z) != (0, 0, 0)],
                 float)
DIR26 /= np.linalg.norm(DIR26, axis=1, keepdims=True)


def _mesh_VF(me):
    V = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", V)
    F = np.empty(len(me.loops), np.int64)
    me.loops.foreach_get("vertex_index", F)
    return V.reshape(-1, 3), F.reshape(-1, 3)


def _face_adjacency(me):
    E = {}
    for p in me.polygons:
        for ek in p.edge_keys:
            E.setdefault(ek, []).append(p.index)
    return E


def _components(n, E, labels):
    parent = np.arange(n)

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for fs in E.values():
        if len(fs) == 2 and labels[fs[0]] == labels[fs[1]]:
            a, b = find(fs[0]), find(fs[1])
            if a != b:
                parent[a] = b
    return np.array([find(i) for i in range(n)])


def merge_small(me, labels, min_faces, E=None):
    labels = labels.copy()
    E = E or _face_adjacency(me)
    nb = defaultdict(list)
    for fs in E.values():
        if len(fs) == 2:
            nb[fs[0]].append(fs[1])
            nb[fs[1]].append(fs[0])
    for _ in range(6):
        comp = _components(len(labels), E, labels)
        ids, cnt = np.unique(comp, return_counts=True)
        small = set(ids[cnt < min_faces].tolist())
        if not small:
            break
        changed = False
        for f in range(len(labels)):
            if comp[f] in small:
                votes = [labels[g] for g in nb.get(f, []) if comp[g] != comp[f]]
                if votes:
                    labels[f] = max(set(votes), key=votes.count)
                    changed = True
        if not changed:
            break
    return labels


def chart_labels(me, smooth_iter=40, min_faces=60, fixed=None):
    """Box-direction labels on smoothed normals; ``fixed`` (face -> label) overrides (separate parts such as moss
    shells and tufts keep their own charts)."""
    V, F = _mesh_VF(me)
    N = sd.smooth_field(sd.vertex_normals(V, F), sd.edges_of(F), smooth_iter)
    fn = N[F].mean(1)
    fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-9)
    labels = np.argmax(fn @ BOX6.T, 1)
    if fixed is not None:
        m = fixed >= 0
        labels[m] = fixed[m]
    return merge_small(me, labels, min_faces)


def split_charts(me, labels, bad, rnd):
    E = _face_adjacency(me)
    comp = _components(len(labels), E, labels)
    bad_comps = {comp[f] for f in bad}
    V, F = _mesh_VF(me)
    N = sd.smooth_field(sd.vertex_normals(V, F), sd.edges_of(F), max(8, 30 - 10 * rnd))
    fn = N[F].mean(1)
    fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-9)
    fine = 100 * (rnd + 1) + np.argmax(fn @ DIR26.T, 1)
    m = np.isin(comp, list(bad_comps))
    out = labels.copy()
    out[m] = fine[m] + 1000 * comp[m] % 7919
    return merge_small(me, out, 30, E)


def unwrap_charts(ob, labels, margin=0.0015, shape="CONCAVE"):
    me = ob.data
    E = _face_adjacency(me)
    ek_seam = {ek for ek, fs in E.items() if len(fs) == 2 and labels[fs[0]] != labels[fs[1]]}
    for e in me.edges:
        e.use_seam = e.key in ek_seam
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.unwrap(method="ANGLE_BASED", margin=margin)
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(rotate=True, shape_method=shape, margin_method="ADD", margin=margin)
    bpy.ops.object.mode_set(mode="OBJECT")
    return int(len(np.unique(_components(len(labels), E, labels))))


def uv_arrays(me, name):
    uv = np.empty(len(me.loops) * 2)
    me.uv_layers[name].data.foreach_get("uv", uv)
    return uv.reshape(-1, 2)


def uv_area(me, uv):
    T = uv.reshape(-1, 3, 2)
    e1 = T[:, 1] - T[:, 0]
    e2 = T[:, 2] - T[:, 0]
    return float(0.5 * np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]).sum())


def overlap_faces(tris, eps=1e-6):
    """Face indices in overlapping UV triangle pairs (the qa_check SAT test, returning the faces)."""
    e1 = tris[:, 1] - tris[:, 0]
    e2 = tris[:, 2] - tris[:, 0]
    keep = np.nonzero(np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]) > 1e-12)[0]
    T = tris[keep]
    mins, maxs = T.min(1), T.max(1)
    cell = max(float(np.median(maxs - mins)) * 2.0, 1e-4)
    lo = np.floor(mins / cell).astype(np.int64)
    hi = np.floor(maxs / cell).astype(np.int64)
    buckets = defaultdict(list)
    for i in range(len(T)):
        for cx in range(lo[i, 0], hi[i, 0] + 1):
            for cy in range(lo[i, 1], hi[i, 1] + 1):
                buckets[(cx, cy)].append(i)
    pairs = set()
    for m in buckets.values():
        if len(m) > 1:
            pairs.update(combinations(m, 2))
    if not pairs:
        return []
    P = np.array(sorted(pairs))
    A, B = T[P[:, 0]], T[P[:, 1]]
    sep = np.any(maxs[P[:, 0]] <= mins[P[:, 1]] + eps, 1) | np.any(maxs[P[:, 1]] <= mins[P[:, 0]] + eps, 1)
    for tri in (A, B):
        for k in range(3):
            ed = tri[:, (k + 1) % 3] - tri[:, k]
            ax = np.stack([-ed[:, 1], ed[:, 0]], -1)
            ax = ax / np.maximum(np.linalg.norm(ax, axis=1, keepdims=True), 1e-12)
            pa = np.einsum("pij,pj->pi", A, ax)
            pb = np.einsum("pij,pj->pi", B, ax)
            sep |= (pa.max(1) <= pb.min(1) + eps) | (pb.max(1) <= pa.min(1) + eps)
    bad = P[~sep]
    return sorted(set(keep[bad.ravel()].tolist()))


def unique_uv(ob, size, texel, fixed=None, log=print):
    """UV0 'UVMap' (unique charts scaled to ``texel`` px/cm at ``size`` px, never above the full packing) and UV1
    'UV1' (the full-tile packing, the Fab lightmap set). Returns info."""
    me = ob.data
    t0 = time.time()
    if "UVMap" not in me.uv_layers:
        me.uv_layers.new(name="UVMap")
    tries = []
    labels = chart_labels(me, fixed=fixed)
    from pipeline.qa_check import uv_overlap_sat
    for rnd in range(5):
        n_charts = unwrap_charts(ob, labels)
        uvt = uv_arrays(me, "UVMap")
        bad = overlap_faces(uvt.reshape(-1, 3, 2))
        tries.append((f"charts{rnd}", n_charts, len(bad)))
        log("uv try", tries[-1], round(time.time() - t0, 1), "s")
        if not bad:
            break
        if len(bad) <= 80:
            labels = labels.copy()
            labels[np.asarray(bad)] = 10 ** 6 + np.asarray(bad)
        else:
            labels = split_charts(me, labels, set(bad), rnd)
    ov = int(uv_overlap_sat(uvt.reshape(-1, 3, 2)))
    tries.append(("final_sat", ov))
    if ov:
        raise RuntimeError(f"{ob.name} UV0 overlaps: {ov}")
    me.uv_layers.new(name="UV1", do_init=True)
    uv = uv_arrays(me, "UVMap")
    a_uv = uv_area(me, uv)
    a_m = float(sum(p.area for p in me.polygons))
    target = (texel * 100.0 / size) ** 2 * a_m
    k = min(1.0, math.sqrt(target / max(a_uv, 1e-9)))
    me.uv_layers["UVMap"].data.foreach_set("uv", (uv * k).ravel())
    me.uv_layers.active = me.uv_layers["UVMap"]
    S = math.sqrt(a_m / (a_uv * k * k))                     # metres per UV0 unit
    return {"uv_tries": tries, "uv0_scale_k": round(k, 4), "uv0_fill_packed": round(a_uv, 4),
            "texel_px_cm": round(math.sqrt(a_uv * k * k / a_m) * size / 100.0, 3), "m_per_uv0": round(S, 4),
            "uv_seconds": round(time.time() - t0, 1)}


# ----------------------------------------------------------------------------------------------- bakes
def gpu(scene):
    scene.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        scene.cycles.device = "GPU"
    except Exception:  # noqa: BLE001
        scene.cycles.device = "CPU"


def new_image(name, size, fill, data=True):
    old = bpy.data.images.get(name)
    if old is not None:
        bpy.data.images.remove(old)
    im = bpy.data.images.new(name, size, size, alpha=True, float_buffer=False, is_data=data)
    im.colorspace_settings.name = "Non-Color" if data else "sRGB"
    im.pixels.foreach_set(np.tile(np.array(fill, np.float32), size * size))
    return im


def emit_material(name, attr, alpha=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    at = nt.nodes.new("ShaderNodeAttribute")
    at.attribute_name = attr
    at.attribute_type = "GEOMETRY"
    nt.links.new(at.outputs["Alpha" if alpha else "Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def bake(target, sources, img, kind, samples=4, extrusion=0.02, ray=0.05, margin=16):
    """Selected-to-active bake (NORMAL or EMIT) from ``sources`` onto ``target``'s active UV into ``img``."""
    sc = bpy.context.scene
    gpu(sc)
    sc.cycles.samples = samples
    mats = [s.material for s in target.material_slots if s.material]
    nodes = []
    for m in dict.fromkeys(mats):
        n = m.node_tree.nodes.new("ShaderNodeTexImage")
        n.image = img
        for o in m.node_tree.nodes:
            o.select = False
        n.select = True
        m.node_tree.nodes.active = n
        nodes.append((m, n))
    b = sc.render.bake
    b.margin = margin
    b.margin_type = "EXTEND"
    b.use_selected_to_active = True
    b.use_cage = False
    b.cage_extrusion = extrusion
    b.max_ray_distance = ray
    b.normal_space = "TANGENT"
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for s in sources:
        s.select_set(True)
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    with bpy.context.temp_override(object=target, active_object=target,
                                   selected_objects=list(sources) + [target],
                                   selected_editable_objects=list(sources) + [target]):
        res = bpy.ops.object.bake(type=kind, use_selected_to_active=True, cage_extrusion=extrusion,
                                  max_ray_distance=ray, margin=margin, margin_type="EXTEND", use_clear=False)
    for m, n in nodes:
        m.node_tree.nodes.remove(n)
    if "FINISHED" not in res:
        raise RuntimeError(f"{kind} bake failed: {res}")


def image_px(img):
    a = np.empty(img.size[0] * img.size[1] * 4, np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(img.size[1], img.size[0], 4)


# ----------------------------------------------------------------------------------------------- measures (SG14)
def plane_fraction(V, F, k=6, ang=15.0, iters=25, seed=0):
    """Share of the above-grade area whose (smoothed) face normal is within ``ang`` of one of ``k`` dominant
    directions (area-weighted spherical k-means): study SG14 '>= 60 % of surface within 15 deg of 3-6 planes'."""
    fn, a = sd.face_normals_areas(V, F)
    above = V[F].mean(1)[:, 2] > 0.02
    fn, a = fn[above], a[above]
    rng = np.random.default_rng(seed)
    C = fn[rng.choice(len(fn), k, replace=False, p=a / a.sum())]
    for _ in range(iters):
        lab = np.argmax(fn @ C.T, 1)
        for j in range(k):
            m = lab == j
            if m.any():
                C[j] = sd.unit((fn[m] * a[m, None]).sum(0))
    cosang = (fn * C[np.argmax(fn @ C.T, 1)]).sum(1)
    hit = cosang > math.cos(math.radians(ang))
    return float(a[hit].sum() / a.sum()), C


def crease_share(V, F, deg=30.0):
    """Share of edges whose dihedral deviation exceeds ``deg`` (sharper than 180 - deg)."""
    fn, _ = sd.face_normals_areas(V, F)
    E = np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    fid = np.tile(np.arange(len(F)), 3)
    key = np.sort(E, 1)
    order = np.lexsort((key[:, 1], key[:, 0]))
    ks = key[order]
    same = (ks[1:] == ks[:-1]).all(1)
    f1 = fid[order][:-1][same]
    f2 = fid[order][1:][same]
    cosd = (fn[f1] * fn[f2]).sum(1)
    return float((cosd < math.cos(math.radians(deg))).mean())


def arris_radius(V, F, H=None, q=(25, 50, 75), thresh=4.0):
    """Arris radius from the mean curvature at convex ridge vertices (r = 1 / H for a cylinder-like arris,
    H = 1/r by the umbrella estimate's 2H convention: r = 1 / H)."""
    if H is None:
        H = sd.mean_curvature(V, F, n_smooth=2)
    above = V[:, 2] > 0.03
    h = H[above & (H > thresh)]
    if not len(h):
        return None
    return [round(float(1.0 / np.percentile(h, 100 - p)), 4) for p in q]
