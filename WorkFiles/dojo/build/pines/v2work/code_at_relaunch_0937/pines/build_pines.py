"""Build the four niwaki black pines (two variants each) from pines_spec.json. Headless Blender 5.2 only.

    blender -b --factory-startup --python Scripts/dojo/pines/build_pines.py -- [--variants PineA1,PineC2]
            [--fast] [--no-export] [--out-blend PATH] [--samples 64]

Per variant (TREE_BUILDING_STUDY.md section 4 / 8):
  SM_DKN_<V>_Trunk    bark, opaque; UV0 tiling bark (overlap-free, whole-tile packed), UV1 lightmap, UV2 unique
                      trunk bake; colour R junction blend, G moss, B branch AO; UCX hulls on 2-4 trunk runs
  SM_DKN_<V>_Foliage  modelled needle tufts; UV0 needle cells, UV1 lightmap, UV2 PP2 element index, UV3.U AO;
                      colour R hierarchy weight, G pad phase, B tuft phase; volume normals; NO collision (study 4.10)
  SM_DKN_<V>_Rock     pine D only: granite boulder (shared M_DJ_Granite) + moss, own UCX hulls
  T_DKN_<V>_Trunk_ORM (unique AO bake on UV2), T_DKN_<V>_PivotPos.exr, T_DKN_<V>_XVector.png, SM_DKN_<V>.wind.json
``--fast`` skips the AO bake, QA and export (a render-only iteration build).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for p in (ROOT / "Scripts", ROOT / "Scripts" / "vegetation", ROOT / "Scripts" / "dojo" / "materials", HERE):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from pipeline import helpers, textures  # noqa: E402
from pipeline.export_fbx import export_fbx  # noqa: E402
from pipeline.lock import assert_owner  # noqa: E402
from pipeline.qa_check import qa_check  # noqa: E402

import colonize as col  # noqa: E402
import foliage as fol  # noqa: E402
import meshio  # noqa: E402
import rock as rockmod  # noqa: E402
import skeleton  # noqa: E402
import treegen  # noqa: E402
import tubes  # noqa: E402
import wind_data  # noqa: E402
import rosette as rosmod  # noqa: E402

SPEC = HERE / "pines_spec.json"
EXPORT = ROOT / "Exports" / "DojoKit" / "Pines"
TEX = EXPORT / "Textures"
BUILD = ROOT / "WorkFiles" / "dojo" / "build" / "pines"
BLEND = ROOT / "Assets" / "Dojo" / "DojoPines.blend"
LOCK = "DojoPines"
TILE_M = 1.0
BARK_TEXEL = 10.24


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", default="")
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--no-export", action="store_true")
    ap.add_argument("--out-blend", default="")
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--tuft-spacing", type=float, default=0.0)
    return ap.parse_args(argv)


# ----------------------------------------------------------------------------- scene / materials

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0


def load_img(path, non_color):
    im = bpy.data.images.load(str(path), check_existing=True)
    im.colorspace_settings.name = "Non-Color" if non_color else "sRGB"
    return im


def _tex(nt, image, uvnode, x, y):
    n = nt.nodes.new("ShaderNodeTexImage")
    n.image = image
    n.location = (x, y)
    nt.links.new(uvnode.outputs["UV"], n.inputs["Vector"])
    return n


def _dx_to_gl_normal(nt, ncol, strength, x, y):
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    sep.location = (x, y)
    nt.links.new(ncol, sep.inputs["Color"])
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    inv.location = (x + 150, y)
    nt.links.new(sep.outputs["Green"], inv.inputs[1])
    comb = nt.nodes.new("ShaderNodeCombineColor")
    comb.location = (x + 300, y)
    nt.links.new(sep.outputs["Red"], comb.inputs["Red"])
    nt.links.new(inv.outputs["Value"], comb.inputs["Green"])
    nt.links.new(sep.outputs["Blue"], comb.inputs["Blue"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.location = (x + 450, y)
    nm.inputs["Strength"].default_value = strength
    nt.links.new(comb.outputs["Color"], nm.inputs["Color"])
    return nm.outputs["Normal"]


def _mix(nt, a, b, fac, x, y, blend="MIX"):
    m = nt.nodes.new("ShaderNodeMix")
    m.data_type = "RGBA"
    m.blend_type = blend
    m.location = (x, y)
    if isinstance(fac, float):
        m.inputs["Factor"].default_value = fac
    else:
        nt.links.new(fac, m.inputs["Factor"])
    for sock, val in ((m.inputs[6], a), (m.inputs[7], b)):
        if isinstance(val, tuple):
            sock.default_value = val
        else:
            nt.links.new(val, sock)
    return m.outputs[2]


def bark_material(name, trunk_orm=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    uv0 = nt.nodes.new("ShaderNodeUVMap")
    uv0.uv_map = "UVMap"
    uv0.location = (-1400, 200)
    bc = _tex(nt, load_img(TEX / "T_DKN_Bark_BC.png", False), uv0, -1150, 400)
    nn = _tex(nt, load_img(TEX / "T_DKN_Bark_N.png", True), uv0, -1150, 0)
    orm = _tex(nt, load_img(TEX / "T_DKN_Bark_ORM.png", True), uv0, -1150, -300)
    so = nt.nodes.new("ShaderNodeSeparateColor")
    so.location = (-850, -300)
    nt.links.new(orm.outputs["Color"], so.inputs["Color"])
    vc = nt.nodes.new("ShaderNodeVertexColor")
    vc.layer_name = "Color"
    vc.location = (-1150, 700)
    sv = nt.nodes.new("ShaderNodeSeparateColor")
    sv.location = (-900, 700)
    nt.links.new(vc.outputs["Color"], sv.inputs["Color"])
    # tile AO (crevices) lightly into the colour; Cycles traces the rest
    ao_mix = nt.nodes.new("ShaderNodeMath")
    ao_mix.operation = "POWER"
    ao_mix.location = (-650, -300)
    nt.links.new(so.outputs["Red"], ao_mix.inputs[0])
    ao_mix.inputs[1].default_value = 1.0
    base = _mix(nt, bc.outputs["Color"], ao_mix.outputs["Value"], 1.0, -500, 400, "MULTIPLY")
    base = _mix(nt, base, (0.105, 0.125, 0.030, 1.0), sv.outputs["Green"], -300, 400)
    if trunk_orm is not None:
        uv2 = nt.nodes.new("ShaderNodeUVMap")
        uv2.uv_map = "UV2"
        uv2.location = (-1400, -600)
        t2 = _tex(nt, trunk_orm, uv2, -1150, -650)
        s2 = nt.nodes.new("ShaderNodeSeparateColor")
        s2.location = (-850, -650)
        nt.links.new(t2.outputs["Color"], s2.inputs["Color"])
        mul = nt.nodes.new("ShaderNodeMath")
        mul.operation = "POWER"
        mul.location = (-650, -650)
        nt.links.new(s2.outputs["Red"], mul.inputs[0])
        mul.inputs[1].default_value = 0.3
        base = _mix(nt, base, mul.outputs["Value"], 1.0, -150, 400, "MULTIPLY")
    nt.links.new(base, bsdf.inputs["Base Color"])
    nt.links.new(so.outputs["Green"], bsdf.inputs["Roughness"])
    nt.links.new(_dx_to_gl_normal(nt, nn.outputs["Color"], 1.4, -850, 0), bsdf.inputs["Normal"])
    return m


def needle_material():
    name = "M_DKN_Needle"
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    uv0 = nt.nodes.new("ShaderNodeUVMap")
    uv0.uv_map = "UVMap"
    uv0.location = (-1400, 200)
    bc = _tex(nt, load_img(TEX / "T_DKN_Needle_BC.png", False), uv0, -1150, 400)
    nn = _tex(nt, load_img(TEX / "T_DKN_Needle_N.png", True), uv0, -1150, 0)
    orm = _tex(nt, load_img(TEX / "T_DKN_Needle_ORM.png", True), uv0, -1150, -300)
    sss = _tex(nt, load_img(TEX / "T_DKN_Needle_SSS.png", True), uv0, -1150, -600)
    for n in (bc, nn, orm, sss):
        n.interpolation = "Closest" if n is sss else "Linear"
    so = nt.nodes.new("ShaderNodeSeparateColor")
    so.location = (-850, -300)
    nt.links.new(orm.outputs["Color"], so.inputs["Color"])
    uv3 = nt.nodes.new("ShaderNodeUVMap")
    uv3.uv_map = "UV3"
    uv3.location = (-1150, 700)
    sx = nt.nodes.new("ShaderNodeSeparateXYZ")
    sx.location = (-950, 700)
    nt.links.new(uv3.outputs["UV"], sx.inputs["Vector"])
    aom = nt.nodes.new("ShaderNodeMapRange")
    aom.location = (-750, 700)
    aom.inputs["To Min"].default_value = 0.8
    nt.links.new(sx.outputs["X"], aom.inputs["Value"])
    base = _mix(nt, bc.outputs["Color"], aom.outputs["Result"], 1.0, -500, 400, "MULTIPLY")
    nt.links.new(base, bsdf.inputs["Base Color"])
    nt.links.new(so.outputs["Green"], bsdf.inputs["Roughness"])
    nt.links.new(_dx_to_gl_normal(nt, nn.outputs["Color"], 0.6, -850, 0), bsdf.inputs["Normal"])
    tr = nt.nodes.new("ShaderNodeBsdfTranslucent")
    tr.location = (-100, -300)
    tint = _mix(nt, base, (0.95, 1.12, 0.80, 1.0), 1.0, -300, -300, "MULTIPLY")   # v2: less yellow back-light
    nt.links.new(tint, tr.inputs["Color"])
    fac = nt.nodes.new("ShaderNodeMath")
    fac.operation = "MULTIPLY"
    fac.location = (-300, -600)
    nt.links.new(sss.outputs["Color"], fac.inputs[0])
    fac.inputs[1].default_value = 0.35         # f1: 0.5 darkened front-lit pads (the translucent half gets no front light)
    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.location = (200, 100)
    nt.links.new(fac.outputs["Value"], mix.inputs["Fac"])
    nt.links.new(bsdf.outputs["BSDF"], mix.inputs[1])
    nt.links.new(tr.outputs["BSDF"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return m


def moss_material():
    name = "M_DKN_Moss"
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    uv0 = nt.nodes.new("ShaderNodeUVMap")
    uv0.uv_map = "UVMap"
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (2.0, 2.0, 1.0)   # granite box UVs are 4 m tiles, the moss tile is 2 m
    nt.links.new(uv0.outputs["UV"], mp.inputs["Vector"])

    def t(path, nc):
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = load_img(path, nc)
        nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
        return n
    bc, nn, orm = t(TEX / "T_DKN_Moss_BC.png", False), t(TEX / "T_DKN_Moss_N.png", True), t(TEX / "T_DKN_Moss_ORM.png", True)
    so = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(orm.outputs["Color"], so.inputs["Color"])
    nt.links.new(bc.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(so.outputs["Green"], bsdf.inputs["Roughness"])
    nt.links.new(_dx_to_gl_normal(nt, nn.outputs["Color"], 1.0, -600, -200), bsdf.inputs["Normal"])
    return m


def groundcover_material():
    """Grass / fern tufts at the base: the needle texture set with a yellow-green tint (Unreal: an MI of the needle
    master with Tint; the sheet's base tufts are yellower than the needles)."""
    name = "MI_DKN_Groundcover"
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    base = needle_material().copy()
    base.name = name
    nt = base.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    src = bsdf.inputs["Base Color"].links[0].from_socket
    tinted = _mix(nt, src, (1.25, 1.12, 0.62, 1.0), 1.0, -200, 600, "MULTIPLY")
    nt.links.new(tinted, bsdf.inputs["Base Color"])
    return base


# ----------------------------------------------------------------------------- helpers

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ucx_from_points(parent, points, index):
    """Study 4.10's make_ucx_hull_from_points, done with the pipeline's own make_ucx_hull on a temporary point
    object, then renamed to UCX_<parent>_NN and parented with an identity parent inverse (the pipeline helper
    itself is not changed in this run: shared file)."""
    import bmesh
    pts = np.unique(np.round(np.asarray(points, float), 5), axis=0)
    bm = bmesh.new()
    vs = [bm.verts.new(tuple(map(float, p))) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=vs)
    hull_faces = [g for g in res["geom"] if isinstance(g, bmesh.types.BMFace)]
    bm.verts.index_update()
    keep = sorted({v.index for f in hull_faces for v in f.verts})
    remap = {old: i for i, old in enumerate(keep)}
    bm.verts.ensure_lookup_table()
    coords = [tuple(bm.verts[i].co) for i in keep]
    tris = [[remap[v.index] for v in f.verts] for f in hull_faces]
    bm.free()
    me = bpy.data.meshes.new("tmp_hull_src")
    me.from_pydata(coords, [], tris)
    tmp = bpy.data.objects.new("tmp_hull_src", me)
    for c in parent.users_collection:
        c.objects.link(tmp)
    hull = helpers.make_ucx_hull(tmp, index=0, max_verts=32)
    name = f"UCX_{parent.name}_{index:02d}"
    hull.name = name
    hull.data.name = name
    hull.parent = parent
    hull.matrix_parent_inverse = Matrix.Identity(4)
    hull.matrix_basis = Matrix.Identity(4)
    bpy.data.objects.remove(tmp)
    bpy.data.meshes.remove(me)
    return hull


def trunk_runs(Q, R, max_runs=4, min_runs=2):
    """Split the trunk centreline into nearly straight runs (convex hulls need convex pieces, study 4.10)."""
    s = skeleton.arclength(Q)
    cuts = [0]
    start = 0
    for i in range(2, len(Q)):
        a, b = Q[start], Q[i]
        d = b - a
        L = np.linalg.norm(d)
        if L < 1e-6:
            continue
        seg = Q[start:i + 1]
        dev = np.linalg.norm(np.cross(seg - a, d / L), axis=1).max()
        if dev > 0.45 * float(np.mean(R[start:i + 1])):
            cuts.append(i - 1)
            start = i - 1
    cuts.append(len(Q) - 1)
    runs = [(cuts[k], cuts[k + 1]) for k in range(len(cuts) - 1) if cuts[k + 1] > cuts[k]]
    while len(runs) > max_runs:
        # merge the shortest adjacent pair
        lens = [s[b] - s[a] for a, b in runs]
        k = int(np.argmin([lens[i] + lens[i + 1] for i in range(len(runs) - 1)]))
        runs[k:k + 2] = [(runs[k][0], runs[k + 1][1])]
    while len(runs) < min_runs:
        k = int(np.argmax([s[b] - s[a] for a, b in runs]))
        a, b = runs[k]
        mid = (a + b) // 2
        runs[k:k + 1] = [(a, mid), (mid, b)]
    return runs


def kmeans(P, k, seed=0, iters=25):
    rng = np.random.default_rng(seed)
    C = P[rng.choice(len(P), k, replace=False)]
    for _ in range(iters):
        lab = ((P[:, None, :] - C[None]) ** 2).sum(-1).argmin(1)
        C = np.array([P[lab == j].mean(0) if (lab == j).any() else C[j] for j in range(k)])
    return lab


def normalise_uv(parts, extent, margin=0.01):
    S = max(extent)
    return [p / S * (1 - 2 * margin) + margin for p in parts]


# ----------------------------------------------------------------------------- rock (f1: fused faceted masses)

ROCK_PLAN = {
    # masses split by planes (through the trunk base, normal); judge r0: 'a faceted, angular, darker, lichen-speckled
    # rock stacked from 2-3 masses, with a mossy crown' (P4F: a big left mass and a lower right mass split by the
    # crack the trunk grows from; P4S / P4Q: a taller stacked block)
    "PineD1": dict(planes=[((0.0, 0.0, 0.0), (1.0, 0.35, 0.0)), ((0.0, 0.0, -0.25), (-0.2, 0.25, 1.0))], chips=26),
    "PineD2": dict(planes=[((0.0, 0.0, 0.0), (1.0, -0.3, 0.0)), ((0.0, 0.0, -0.3), (0.25, -0.2, 1.0))], chips=26),
}


def convex_hull_mesh(P):
    """Convex hull of a point cloud (bmesh), triangulated, then long edges subdivided (planar facets stay planar;
    the finer triangles carry the moss / lichen boundaries). Returns (V, F)."""
    import bmesh
    bm = bmesh.new()
    vs = [bm.verts.new(tuple(map(float, p))) for p in np.unique(np.round(P, 5), axis=0)]
    res = bmesh.ops.convex_hull(bm, input=vs)
    for g in res.get("geom_interior", []) + res.get("geom_unused", []):
        if isinstance(g, bmesh.types.BMVert) and g.is_valid:
            bm.verts.remove(g)
    bmesh.ops.dissolve_limit(bm, angle_limit=np.deg2rad(1.0), verts=list(bm.verts), edges=list(bm.edges))
    # drop collinear vertices left on the facet borders (they make zero-area triangles)
    for _ in range(3):
        lone = [v for v in bm.verts if len(v.link_edges) == 2]
        if not lone:
            break
        bmesh.ops.dissolve_verts(bm, verts=lone)
    bmesh.ops.triangulate(bm, faces=list(bm.faces), quad_method="BEAUTY", ngon_method="BEAUTY")
    # uniform refinement: every triangle split into four while its longest edge is over 7.5 cm (planar facets
    # stay planar; the finer triangles carry the moss / lichen boundaries)
    for _ in range(5):
        long = [e for e in bm.edges if e.calc_length() > 0.10]
        if not long:
            break
        bmesh.ops.subdivide_edges(bm, edges=long, cuts=1, use_grid_fill=True)
        bmesh.ops.triangulate(bm, faces=list(bm.faces), quad_method="BEAUTY", ngon_method="BEAUTY")
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-5)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-6, edges=list(bm.edges))
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    # v2: sliver triangles on the flat (clamped) bottom: collapse until none is below the QA area floor
    for _ in range(6):
        bad = [f for f in bm.faces if f.calc_area() < 1e-9]
        if not bad:
            break
        edges = list({min(f.edges, key=lambda e: e.calc_length()) for f in bad})
        bmesh.ops.collapse(bm, edges=edges)
        bmesh.ops.dissolve_degenerate(bm, dist=1e-5, edges=list(bm.edges))
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bm.verts.index_update()
    V = np.array([v.co[:] for v in bm.verts])
    F = np.array([[v.index for v in f.verts] for f in bm.faces], dtype=np.int64)
    bm.free()
    return V, F


def build_rock(vname, spec, rng):
    rs = spec["rock"]
    front = np.asarray(rs["front_xz"], float)
    side = np.asarray(rs["side_yz"], float)
    V0, _ = rockmod.visual_hull(front, side, level=4, rounding=0.55)
    base = np.asarray(spec["trunk"]["pts"][0], float)
    plan = ROCK_PLAN.get(vname, ROCK_PLAN["PineD1"])
    planes = []
    for q, n in plan["planes"]:
        q = np.asarray(q, float).copy()
        q[:2] += base[:2]
        q[2] += base[2]
        planes.append((q, np.asarray(n, float)))
    sink = float(rs.get("sink_m", 0.15))
    masses = rockmod.split_masses(V0, planes, overlap=0.10)
    out = []
    for k, (M, avoid) in enumerate(masses):
        M = rockmod.faceted_mass_points(M, rng, n_chips=plan["chips"], depth=(0.03, 0.12), up_bias=0.25,
                                        avoid=avoid)
        cM = M.mean(0)
        M = cM + (M - cM) * (1.0 + 0.004 * k)       # masses share overlap points: keep their hulls apart (P39)
        low = M[:, 2] < M[:, 2].min() + 0.06
        M[low, 2] -= sink                                        # below grade for sloped placement (study 4.2)
        V, F = convex_hull_mesh(M)
        out.append((V, F))
    allv = np.vstack([o_[0] for o_ in out])
    print(f"[{vname}] rock bbox x {allv[:,0].min():.2f}..{allv[:,0].max():.2f} y {allv[:,1].min():.2f}.."
          f"{allv[:,1].max():.2f} z {allv[:,2].min():.2f}..{allv[:,2].max():.2f}; trace x {front[:,0].min():.2f}.."
          f"{front[:,0].max():.2f} z ..{front[:,1].max():.2f} y {side[:,0].min():.2f}..{side[:,0].max():.2f}; "
          f"trunk base {base.round(2).tolist()}", flush=True)
    return out


def mass_uvs(masses, tile_m=4.0, gap=0.25):
    """Per mass, per dominant axis: a planar chart. A convex mass's faces facing +X project one-to-one onto YZ, so a
    chart never folds; charts are laid side by side with whole-tile offsets (granite tiles: the texture is
    unchanged by a whole-tile shift), so UV0 has no overlaps. Returns (uv0 per mass (F,3,2), uv1 per mass, extent)."""
    charts = []
    uv0s = []
    for mi, (V, F) in enumerate(masses):
        tri = V[F]
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
        ax = np.abs(n).argmax(1)
        sg = np.sign(n[np.arange(len(n)), ax])
        uv = np.zeros((len(F), 3, 2))
        for a in range(3):
            for s in (-1, 1):
                m = (ax == a) & (sg == s)
                if not m.any():
                    continue
                o1, o2 = [k for k in range(3) if k != a]
                if a == 2:
                    u, v = tri[m][..., 0] * s, tri[m][..., 1]
                else:
                    u, v = tri[m][..., o1] * (s if a == 0 else -s), tri[m][..., 2]
                uv[m, :, 0] = u / tile_m
                uv[m, :, 1] = v / tile_m
                charts.append((mi, m, uv[m].reshape(-1, 2).min(0), uv[m].reshape(-1, 2).max(0)))
        uv0s.append(uv)
    # shelf-pack the charts in whole tiles for UV0, and tightly (then normalised) for UV1
    x = 0.0
    x1 = 0.0
    uv1s = [np.zeros_like(u) for u in uv0s]
    row_h = max(c[3][1] - c[2][1] for c in charts) + gap / tile_m
    y1, xrow = 0.0, 0.0
    for (mi, m, lo, hi) in charts:
        w = hi - lo
        du = -np.floor(lo[0]) + np.ceil(x)
        dv = -np.floor(lo[1])
        uv1s[mi][m] = uv0s[mi][m] - lo + np.array([xrow, y1])
        uv0s[mi][m] = uv0s[mi][m] + np.array([du, dv])
        x = uv0s[mi][m][..., 0].max() + 0.001
        xrow += w[0] + gap / tile_m
        if xrow > 3.0:
            xrow, y1 = 0.0, y1 + row_h
    allu = np.concatenate([u.reshape(-1, 2) for u in uv1s])
    S = float(max(allu[:, 0].max(), allu[:, 1].max()))
    uv1s = [u / S * 0.98 + 0.01 for u in uv1s]
    ext = float(max(np.concatenate([u.reshape(-1, 2) for u in uv0s]).max(), 1.0))
    return uv0s, uv1s, ext


def rock_material(name="MI_DKN_PineRock"):
    """Shared granite (Scripts/dojo/materials, M_DJ_Granite) as a darker, warmer instance with our lichen / stain
    overlay (T_DKN_RockOverlay_M on UV0 x 4 = a 1 m tile). Unreal: MI of M_DJ_Granite with Tint, plus the overlay
    lerps in the pines' rock layer function (catalog)."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    base = djm.make_material("M_DJ_Granite", rebuild=True, tint=(0.56, 0.545, 0.51))   # v2: the sheet's rock is a lighter grey
    base.name = name
    nt = base.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    link = bsdf.inputs["Base Color"].links[0]
    col_in = link.from_socket
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (4.0, 4.0, 1.0)
    nt.links.new(uv.outputs["UV"], mp.inputs["Vector"])
    ov = nt.nodes.new("ShaderNodeTexImage")
    ov.image = load_img(TEX / "T_DKN_RockOverlay_M.png", True)
    nt.links.new(mp.outputs["Vector"], ov.inputs["Vector"])
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(ov.outputs["Color"], sep.inputs["Color"])
    f_st = nt.nodes.new("ShaderNodeMath")
    f_st.operation = "MULTIPLY"
    f_st.inputs[1].default_value = 0.55
    nt.links.new(sep.outputs["Green"], f_st.inputs[0])
    col2 = _mix(nt, col_in, (0.075, 0.055, 0.035, 1.0), f_st.outputs["Value"], 300, 300, "MIX")
    f_li = nt.nodes.new("ShaderNodeMath")
    f_li.operation = "MULTIPLY"
    f_li.inputs[1].default_value = 0.75
    nt.links.new(sep.outputs["Red"], f_li.inputs[0])
    lich = _mix(nt, col2, (0.30, 0.27, 0.12, 1.0), f_li.outputs["Value"], 400, 300, "MIX")
    nt.links.new(lich, bsdf.inputs["Base Color"])
    return base


def make_rock_object(name, masses, rng, coll, base_pt, roots_pts=None):
    V = np.vstack([m[0] for m in masses])
    offs = np.cumsum([0] + [len(m[0]) for m in masses])[:-1]
    F = np.vstack([m[1] + o for m, o in zip(masses, offs)])
    mass_of_face = np.concatenate([np.full(len(m[1]), k) for k, m in enumerate(masses)])
    uv0s, uv1s, ext = mass_uvs(masses)
    uv0 = np.vstack(uv0s)
    uv1 = np.vstack(uv1s)
    obj = meshio.make_mesh(name, V, [F], {"UVMap": [uv0], "UV1": [uv1]}, smooth=False, collection=coll)
    me = obj.data
    me.materials.append(rock_material())
    me.materials.append(moss_material())
    # moss (judge r0: 'a mossy crown ... moss on top and down the crevices'): up-facing faces in the upper part,
    # faces in the creases between masses (close to another mass's surface), around the trunk base and at the foot
    from mathutils.bvhtree import BVHTree
    fc = V[F].mean(1)
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
    top = V[:, 2].max()
    crease = np.zeros(len(F), bool)
    for k, (Vk, Fk) in enumerate(masses):
        bvh = BVHTree.FromPolygons([tuple(map(float, v)) for v in Vk], [tuple(map(int, f)) for f in Fk])
        other = mass_of_face != k
        for i in np.nonzero(other)[0]:
            hit = bvh.find_nearest(tuple(map(float, fc[i])), 0.09)
            if hit[0] is not None:
                crease[i] = True
    noise = col.value_noise2(fc[:, 0] * 3 + fc[:, 2], fc[:, 1] * 3 - fc[:, 2] * 2, int(rng.integers(1 << 20)), 0.35)
    near_base = np.linalg.norm((fc - base_pt)[:, :2], axis=1) < 0.55
    moss = (fn[:, 2] > 0.35) & (fc[:, 2] > 0.60 * top) & (noise > 0.42)
    moss |= near_base & (fn[:, 2] > 0.2) & (fc[:, 2] > 0.7 * top) & (noise > 0.25)
    moss |= crease & (noise > 0.25) & (fc[:, 2] > 0.15 * top)
    # v2: moss only in the crevices and on top (the foot's moss and tufts belong to the optional mound)
    me.polygons.foreach_set("material_index", moss.astype(np.int32))
    me.update()
    me.uv_layers.active = me.uv_layers["UVMap"]
    obj["uv0_tile_extent"] = ext
    try:
        djm.bake_wear(obj)
    except Exception as exc:  # noqa: BLE001
        print("bake_wear skipped:", exc)
    return obj, {"moss_share": round(float(moss.mean()), 3), "crease_faces": int(crease.sum()),
                 "masses": len(masses), "tris": int(len(F))}


def seat_trunk_on_rock(rock_obj, spec):
    """The chipped rock top can sit below the traced trunk base: extend the trunk down to the rock surface under it
    (the tree must grow out of the rock, r0 of f1 floated a bulb above it)."""
    from mathutils.bvhtree import BVHTree
    from mathutils import Vector
    me = rock_obj.data
    bvh = BVHTree.FromPolygons([tuple(v.co) for v in me.vertices], [tuple(p.vertices) for p in me.polygons])
    P = [list(p) for p in spec["trunk"]["pts"]]
    R = list(spec["trunk"]["min_r"])
    b = np.array(P[0], float)
    r0 = float(R[0])
    zs = None
    for a in np.linspace(0, 2 * np.pi, 12, endpoint=False):
        q = b + np.array([np.cos(a), np.sin(a), 0.0]) * 0.8 * r0
        hit = bvh.ray_cast(Vector((q[0], q[1], b[2] + 2.0)), Vector((0, 0, -1)), 6.0)
        if hit[0] is not None:
            zs = float(hit[0][2]) if zs is None else max(zs, float(hit[0][2]))
    if zs is None:
        return
    if zs < b[2] - 0.02:
        steps = int(np.ceil((b[2] - zs) / 0.08))
        for k in range(1, steps + 1):
            z = b[2] - (b[2] - zs + 0.03) * k / steps
            P.insert(0, [b[0], b[1], z])
            R.insert(0, R[0])
        spec["trunk"]["pts"] = P
        spec["trunk"]["min_r"] = R
    spec["trunk"]["rock_surface_z"] = zs


def grow_rock_roots(rock_obj, spec, rng, base_r, masses=None):
    """f1 roots (judge r0: 'thin strands draped over the rim like spider legs'): 6-10 thick roots leave the flared
    trunk base, hug the rock (each step is snapped to the nearest rock surface, the root half sunk into it), slide
    down under gravity along the surface, prefer the creases between masses, fork once or twice and taper to the
    ground. The traced root guides of the front panel set the azimuths of the visible front roots."""
    from mathutils.bvhtree import BVHTree
    me = rock_obj.data
    Vr = [tuple(v.co) for v in me.vertices]
    Pr = [tuple(p.vertices) for p in me.polygons]
    bvh = BVHTree.FromPolygons(Vr, Pr)
    base = np.asarray(spec["trunk"]["pts"][0], float)
    ground = -0.1
    # azimuths: 5 across the front half (the sheet's front and 3/4 panels show the roots spreading over the
    # front-left face), 3 round the back; jittered
    az = np.concatenate([np.deg2rad(np.linspace(185, 355, 7)), np.deg2rad([30, 70, 110, 145, 170])])
    az = az + rng.normal(0, np.deg2rad(8), len(az))
    roots = []
    down = np.array([0.0, 0.0, -1.0])
    # v2: the creases between the lobes (vertices of one lobe close to another lobe) attract the roots, so they
    # dive into the cracks on their way to the ground (the sheet's roots run down the rock's clefts)
    crease_pts = np.zeros((0, 3))
    if masses is not None and len(masses) > 1:
        cp_ = []
        for k, (Vk, Fk) in enumerate(masses):
            for j, (Vj, Fj) in enumerate(masses):
                if j == k:
                    continue
                bj = BVHTree.FromPolygons([tuple(map(float, v)) for v in Vj], [tuple(map(int, f)) for f in Fj])
                for v in Vk[:: 2]:
                    hit = bj.find_nearest(tuple(map(float, v)), 0.06)
                    if hit[0] is not None:
                        cp_.append(v)
        crease_pts = np.array(cp_) if cp_ else crease_pts

    def walk(p0, d0, r0, max_len, parent=None, depth=0):
        pts = [p0]
        d = d0 / np.linalg.norm(d0)
        s = 0.0
        step = 0.03
        wob = rng.normal(0, 1, 3)
        while s < max_len:
            p = pts[-1] + d * step
            hit = bvh.find_nearest(tuple(map(float, p)))
            if hit[0] is None:
                break
            loc, nrm = np.array(hit[0]), np.array(hit[1])
            t = s / max_len
            r = max(0.012, r0 * (1.0 - 0.85 * t) ** 0.8)
            p = loc + nrm * 0.30 * r            # v2: shrink-wrapped, a third sunk into rock / moss
            g = down - nrm * float(np.dot(nrm, down))
            gl = np.linalg.norm(g)
            g = g / gl if gl > 1e-6 else np.zeros(3)
            wob = 0.8 * wob + 0.2 * rng.normal(0, 1, 3)
            dn = 0.78 * d + (0.14 + 0.40 * t) * g + 0.10 * wob
            if len(crease_pts):
                dv = crease_pts - p
                dist = np.linalg.norm(dv, axis=1)
                ok = (dist < 0.35) & (dv[:, 2] < 0.02)
                if ok.any():
                    j = int(np.argmin(np.where(ok, dist, 9.0)))
                    dn = dn + 0.35 * dv[j] / max(dist[j], 1e-6)
            dn = dn - nrm * float(np.dot(nrm, dn))
            d = dn / max(np.linalg.norm(dn), 1e-9)
            pts.append(p)
            s += step
            if p[2] < ground:
                break
        P = np.array(pts)
        if len(P) < 4:
            return
        L = arclen = float(skeleton.arclength(P)[-1])
        prof = np.clip(r0 * (1.0 - 0.85 * skeleton.arclength(P) / max(L, 1e-6)) ** 0.8, 0.012, None)
        idx = len(roots)
        roots.append({"pts": P[1:].tolist(), "profile": prof.tolist(), "exact": True,
                      **({"parent_root": parent} if parent is not None else {})})
        if depth < 2 and L > 0.5:
            nfork = 1 if depth == 1 else 2
            for _ in range(nfork):
                k = int(len(P) * rng.uniform(0.3, 0.6))
                dd = P[min(k + 1, len(P) - 1)] - P[k]
                ang = np.deg2rad(rng.choice([-1, 1]) * rng.uniform(30, 50))
                c, s_ = np.cos(ang), np.sin(ang)
                dd = np.array([c * dd[0] - s_ * dd[1], s_ * dd[0] + c * dd[1], dd[2]])
                # v2 (G7): the parent root thins past the fork (pipe rule, n about 2.3)
                pr_ = np.asarray(roots[idx]["profile"], float)
                pr_[k:] *= 0.85
                roots[idx]["profile"] = pr_.tolist()
                walk(P[k], dd, float(prof[k]) * 0.62, (L - arclen * k / len(P)) * 0.8, idx, depth + 1)

    for i, a in enumerate(az):
        r0 = base_r * (0.40 if i < 7 else 0.32) * rng.uniform(0.8, 1.15)   # v2 r4: thinner, more roots
        dirv = np.array([np.cos(a), np.sin(a), -0.25])
        p0 = base + np.array([np.cos(a), np.sin(a), 0.0]) * base_r * 0.7 + np.array([0, 0, 0.35 * base_r])
        walk(p0, dirv, r0, 2.6 if i < 7 else 2.0)
    return roots


# ----------------------------------------------------------------------------- v2 rock: fused rounded lobes

# Lobes in the rock's normalised frame (x: front width, y: side depth, z: height); fitted to the traced outlines
# after construction (the union's bbox is scaled to the traced width, depth and height). Read off the sheet: P4F a big
# front-left lobe and a lower right lobe split by the crack the roots dive into, a crown lobe under the tree; P4Q (D2)
# a tall broad back lobe, a front-left lobe and a small right one.
ROCK_LOBES = {
    # v2 r5 look: egg lobes with a narrow crown read as two eggs with a neck; the sheet's boulder is one broad
    # massive body with a wide, low-domed top the tree sits on, and smaller lobes fused on its flanks
    "PineD1": [((0.00, 0.00, 0.50), (0.85, 0.80, 0.55)), ((-0.58, -0.35, 0.28), (0.45, 0.50, 0.32)),
               ((0.62, 0.25, 0.33), (0.42, 0.50, 0.36)), ((0.05, 0.00, 0.84), (0.60, 0.58, 0.22)),
               ((-0.35, 0.50, 0.22), (0.40, 0.36, 0.26))],
    "PineD2": [((0.05, 0.05, 0.50), (0.85, 0.80, 0.56)), ((-0.55, -0.30, 0.30), (0.46, 0.52, 0.34)),
               ((0.60, -0.35, 0.22), (0.38, 0.45, 0.26)), ((0.00, 0.10, 0.86), (0.58, 0.55, 0.20)),
               ((0.45, 0.50, 0.30), (0.40, 0.38, 0.30))],
}


def _lobe_points(centre, radii, rng, level=3, bump=0.12, n_chips=10):
    """A rounded-but-fractured granite lobe: an ellipsoid with low-frequency bumps and a few planar fracture chips
    (flat facets with crisp edges); convex after the hull, so per-lobe box UVs never fold and the UCX is exact."""
    D, _ = rockmod.icosphere(level)
    k = rng.normal(0, 1, (10, 3))
    ph = rng.uniform(0, 2 * np.pi, 10)
    f = np.ones(len(D))
    for i in range(10):
        fr = 1.4 if i < 5 else 3.0
        f += (bump if i < 5 else 0.45 * bump) / 2 * np.sin(D @ k[i] * fr + ph[i])
    P = np.asarray(centre, float) + D * np.asarray(radii, float) * f[:, None]
    # v2 r4 look: 5 chips left egg-smooth lobes; the sheet's granite is craggy: more, deeper fracture planes
    P = rockmod.faceted_mass_points(P, rng, n_chips=n_chips, depth=(0.04, 0.16), up_bias=0.2)
    return P


def build_rock_v2(vname, spec, rng):
    rs = spec["rock"]
    front = np.asarray(rs["front_xz"], float)
    side = np.asarray(rs["side_yz"], float)
    x0, x1 = front[:, 0].min(), front[:, 0].max()
    y0, y1 = side[:, 0].min(), side[:, 0].max()
    base = np.asarray(spec["trunk"]["pts"][0], float)
    # height: the rock top meets the trunk base (the tree sits ON the rock, its root plate over the top)
    top_z = float(base[2]) - 0.04
    sink = float(rs.get("sink_m", 0.15))
    lobes = ROCK_LOBES.get(vname, ROCK_LOBES["PineD1"])
    raw = [_lobe_points(c, r, rng) for c, r in lobes]
    allp = np.vstack(raw)
    lo, hi = allp.min(0), allp.max(0)
    out = []
    for P in raw:
        Q = np.empty_like(P)
        Q[:, 0] = x0 + (P[:, 0] - lo[0]) / (hi[0] - lo[0]) * (x1 - x0)
        Q[:, 1] = y0 + (P[:, 1] - lo[1]) / (hi[1] - lo[1]) * (y1 - y0)
        Q[:, 2] = -sink + (P[:, 2] - lo[2]) / (hi[2] - lo[2]) * (top_z + sink)
        Q[:, 2] = np.maximum(Q[:, 2], -sink)                      # flat buried bottom
        out.append(convex_hull_mesh(Q))
    allv = np.vstack([o_[0] for o_ in out])
    print(f"[{vname}] rock v2 bbox x {allv[:,0].min():.2f}..{allv[:,0].max():.2f} y {allv[:,1].min():.2f}.."
          f"{allv[:,1].max():.2f} z {allv[:,2].min():.2f}..{allv[:,2].max():.2f}; trunk base {base.round(2).tolist()}",
          flush=True)
    return out


# ----------------------------------------------------------------------------- v2 base mound (optional mesh)

def soil_material():
    name = "M_DKN_Soil"
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = moss_material().copy()
    m.name = name
    for n in m.node_tree.nodes:
        if n.type == "TEX_IMAGE" and n.image is not None:
            suffix = n.image.name.split("_")[-1].split(".")[0]
            path = TEX / f"T_DKN_Soil_{suffix}.png"
            if path.exists():
                n.image = load_img(path, suffix != "BC")
    return m


def _uv_pack_parts(parts):
    """parts: list of (F,k,2) UV arrays in tile units (each part overlap-free inside). UV0: the parts are moved apart
    by whole tiles in U (tiling textures unchanged); UV1: each part's bbox shelf-packed into 0-1, one scale."""
    uv0, boxes = [], []
    u = 0.0
    for P in parts:
        lo = P.reshape(-1, 2).min(0)
        hi = P.reshape(-1, 2).max(0)
        du = np.ceil(u + 1e-6) - np.floor(lo[0])
        dv = -np.floor(lo[1])
        Q = P + np.array([du, dv])
        uv0.append(Q)
        u = float(Q[..., 0].max()) + 0.01
        boxes.append((lo, hi))
    ext = float(max(max(q[..., 0].max(), q[..., 1].max()) for q in uv0))
    sizes = [(hi - lo) for lo, hi in boxes]
    total = sum(float(w[0] * w[1]) for w in sizes)
    scale = np.sqrt(0.50 / max(total, 1e-9))
    x = y = row_h = 0.0
    place = {}
    for i in sorted(range(len(parts)), key=lambda i: -sizes[i][1]):
        w, h = sizes[i] * scale
        if x + w > 0.98:
            x, y, row_h = 0.0, y + row_h + 0.01, 0.0
        place[i] = (x + 0.01, y + 0.01)
        x += w + 0.01
        row_h = max(row_h, h)
    ymax = y + row_h + 0.02
    k = min(1.0, 0.98 / ymax)
    uv1 = []
    for i, P in enumerate(parts):
        lo, _ = boxes[i]
        uv1.append(((P - lo) * scale + np.array(place[i])) * k)
    return uv0, uv1, ext


def build_mound(fam, spec, rng, coll, rock_obj=None):
    """SM_DKN_BaseMound_<fam>: the sheet's mossy soil mound with small stones and grass / fern tufts (optional,
    shares the tree's origin). Pines A-C: an elliptical dome measured on the sheet (spec 'mound'); pine D: a low
    mossy apron round the rock's foot. One UCX hull (walkable ground)."""
    if rock_obj is not None:
        Vr = np.array([v.co[:] for v in rock_obj.data.vertices])
        foot = Vr[Vr[:, 2] < 0.15]
        c = foot[:, :2].mean(0)
        md = {"rx": float(np.ptp(foot[:, 0])) / 2 + 0.22, "ry": float(np.ptp(foot[:, 1])) / 2 + 0.22,
              "cx": float(c[0]), "cy": float(c[1]), "h": 0.10}
    else:
        md = dict(spec["mound"])
        md["ry"] = max(md["ry"], 0.55 * md["rx"])
    rx, ry, cx, cy, h = md["rx"], md["ry"], md["cx"], md["cy"], md["h"]
    nr, ns = 18, 72
    seed = int(rng.integers(1 << 20))
    V = [np.array([cx, cy, h])]
    ring_idx = []
    th = np.linspace(0, 2 * np.pi, ns, endpoint=False)
    wob = 1.0 + 0.06 * np.sin(3 * th + seed % 7) + 0.04 * np.sin(5 * th + seed % 11)
    for i in range(1, nr + 1):
        r = i / nr
        x = cx + rx * r * wob * np.cos(th)
        y = cy + ry * r * wob * np.sin(th)
        lump = col.value_noise2(x * 5.0, y * 5.0, seed, 1.0) - 0.5
        lump2 = col.value_noise2(x * 14.0, y * 14.0, seed + 3, 1.0) - 0.5
        z = h * np.clip(1 - r * r, 0, 1) ** 1.2 + (0.45 * h * lump + 0.05 * lump2) * (1 - r) ** 0.5 - 0.03 * r ** 6
        ring_idx.append(list(range(len(V), len(V) + ns)))
        V.extend(np.stack([x, y, z], 1))
    bot = len(V)
    V.append(np.array([cx, cy, -0.05]))
    V = np.array(V)

    def surf_z(px, py):
        rr = np.sqrt(((px - cx) / rx) ** 2 + ((py - cy) / ry) ** 2)
        return h * np.clip(1 - rr * rr, 0, 1) ** 1.2

    tris = [(0, ring_idx[0][j], ring_idx[0][(j + 1) % ns]) for j in range(ns)]
    quads = []
    for a_, b_ in zip(ring_idx[:-1], ring_idx[1:]):
        for j in range(ns):
            quads.append((a_[j], b_[j], b_[(j + 1) % ns], a_[(j + 1) % ns]))
    rl = ring_idx[-1]
    btris = [(bot, rl[(j + 1) % ns], rl[j]) for j in range(ns)]
    Tt = np.array(tris + btris, np.int64)
    Tq = np.array(quads, np.int64)
    uv_t = V[Tt][..., :2] / 4.0
    uv_t[len(tris):, :, 1] += np.ceil(2 * ry / 4.0) + 1.0          # the bottom cap one tile clear of the top
    uv_q = V[Tq][..., :2] / 4.0
    # ---- stones
    stones = []
    n_st = 14 if rock_obj is None else 9
    for k in range(n_st):
        a = rng.uniform(0, 2 * np.pi)
        rr = rng.uniform(0.3, 0.85) if rock_obj is None else rng.uniform(0.80, 0.97)
        sz = rng.uniform(0.06, 0.20) * (1.3 if h > 0.3 else 1.0)
        px, py = cx + rx * rr * np.cos(a), cy + ry * rr * np.sin(a)
        pz = float(surf_z(px, py))
        P = _lobe_points((px, py, pz), (sz, sz * rng.uniform(0.7, 1.0), sz * rng.uniform(0.45, 0.7)), rng,
                         level=2, bump=0.1, n_chips=3)
        P[:, 2] -= 0.35 * sz
        stones.append(convex_hull_mesh(P))
    st_uv, _, _ = mass_uvs(stones)
    # ---- tufts: grass and fern-like clumps (the sheet's base shows both)
    # v2 r4 look: tall thin blades read as lawn grass; the sheet's base tufts are low bushy clumps and small ferns
    kinds = [fol.make_clump(np.random.default_rng(seed + 1), n_blades=34, height=(0.05, 0.12), width=0.006,
                            spread=0.07),
             fol.make_clump(np.random.default_rng(seed + 2), n_blades=40, height=(0.07, 0.16), width=0.007,
                            spread=0.09),
             fol.make_clump(np.random.default_rng(seed + 3), n_blades=14, height=(0.12, 0.22), width=0.022,
                            spread=0.06)]           # fern-like: few broad arching fronds
    tips = []
    n_t = int(np.clip(round(10 * rx * ry), 10, 26)) if rock_obj is None else 20
    for k in range(n_t):
        a = rng.uniform(0, 2 * np.pi)
        rr = np.sqrt(rng.uniform(0.04, 0.8)) if rock_obj is None else rng.uniform(0.75, 0.95)
        px, py = cx + rx * rr * np.cos(a), cy + ry * rr * np.sin(a)
        pz = float(surf_z(px, py)) - 0.01
        tips.append({"p": np.array([px, py, pz]), "d": np.array([0, 0, 1.0]), "pad": 0,
                     "variant": int(rng.integers(len(kinds))), "scale": rng.uniform(0.8, 1.3)})
    if rock_obj is not None:
        from mathutils.bvhtree import BVHTree
        from mathutils import Vector
        me = rock_obj.data
        bvh = BVHTree.FromPolygons([tuple(v.co) for v in me.vertices], [tuple(p.vertices) for p in me.polygons])
        base = np.asarray(spec["trunk"]["pts"][0], float)
        for _ in range(5):
            a = rng.uniform(0, 2 * np.pi)
            q = base + np.array([np.cos(a), np.sin(a), 0]) * rng.uniform(0.25, 0.5)
            hit = bvh.ray_cast(Vector((q[0], q[1], q[2] + 1.5)), Vector((0, 0, -1)), 4.0)
            if hit[0] is not None:
                tips.append({"p": np.array(hit[0][:]) - np.array([0, 0, 0.02]), "d": np.array([0, 0, 1.0]),
                             "pad": 0, "variant": int(rng.integers(len(kinds))), "scale": rng.uniform(0.7, 1.0)})
    fm = fol.instance(kinds, tips, rng)
    # ---- assemble (the surface's triangles and quads are one chart)
    parts_V = [V] + [st[0] for st in stones] + [fm.V]
    offs = np.cumsum([0] + [len(x) for x in parts_V])[:-1]
    faces = [Tt, Tq] + [st[1] + offs[1 + i] for i, st in enumerate(stones)] + [fm.T + offs[-1]]
    surf = np.concatenate([uv_t.reshape(-1, 2), uv_q.reshape(-1, 2)]).reshape(-1, 1, 2)
    u0, u1, ext = _uv_pack_parts([surf] + st_uv + [fm.uv0])
    s0, s1 = u0[0].reshape(-1, 2), u1[0].reshape(-1, 2)
    nt = uv_t.size // 2
    uv0 = [s0[:nt].reshape(-1, 3, 2), s0[nt:].reshape(-1, 4, 2)] + u0[1:]
    uv1 = [s1[:nt].reshape(-1, 3, 2), s1[nt:].reshape(-1, 4, 2)] + u1[1:]
    allV = np.vstack(parts_V)
    name = f"SM_DKN_BaseMound_{fam}"
    obj = meshio.make_mesh(name, allV, faces, {"UVMap": uv0, "UV1": uv1}, smooth=True, collection=coll)
    me = obj.data
    for m_ in (moss_material(), soil_material(), rock_material(), groundcover_material()):
        me.materials.append(m_)

    def soil_mask(fc):
        rr = np.sqrt(((fc[:, 0] - cx) / rx) ** 2 + ((fc[:, 1] - cy) / ry) ** 2)
        nz = col.value_noise2(fc[:, 0] * 3, fc[:, 1] * 3, seed + 9, 1.0)
        return (rr > 0.88) | ((nz < 0.28) & (rr > 0.5))
    mi = [np.where(soil_mask(V[Tt].mean(1)), 1, 0), np.where(soil_mask(V[Tq].mean(1)), 1, 0)]
    mi += [np.full(len(st[1]), 2) for st in stones] + [np.full(len(fm.T), 3)]
    me.polygons.foreach_set("material_index", np.concatenate(mi).astype(np.int32))
    me.update()
    me.uv_layers.active = me.uv_layers["UVMap"]
    obj["uv0_tile_extent"] = ext
    ucx_from_points(obj, V[:bot], 0)
    return obj, {"rx": round(rx, 3), "ry": round(ry, 3), "h": round(h, 3), "cx": round(cx, 3), "cy": round(cy, 3),
                 "stones": n_st, "tufts": len(tips),
                 "tris": int(sum(len(f) * (2 if f.shape[1] == 4 else 1) for f in faces))}


def ground_tips(spec, rng, rock_obj=None, n=10):
    """Ground-cover clump sites (the sheet shows grass / fern tufts at every tree base and around the rock's foot).
    Returns tip dicts (pad -1) for foliage.instance, variants appended after the needle bursts."""
    tips = []
    if rock_obj is not None:
        V = np.array([v.co[:] for v in rock_obj.data.vertices])
        low = V[V[:, 2] < V[:, 2].min() + 0.2]
        c = low[:, :2].mean(0)
        for _ in range(n + 4):
            q = low[int(rng.integers(len(low)))]
            out = q[:2] - c
            out /= max(np.linalg.norm(out), 1e-6)
            p = np.array([q[0] + out[0] * rng.uniform(0.03, 0.12), q[1] + out[1] * rng.uniform(0.03, 0.12), 0.0])
            tips.append({"p": p, "d": np.array([0, 0, 1.0]), "pad": -1, "kind": 3, "scale": rng.uniform(0.8, 1.3)})
        # a few on the mossy crown by the trunk base
        base = np.asarray(spec["trunk"]["pts"][0], float)
        for _ in range(3):
            a = rng.uniform(0, 2 * np.pi)
            p = base + np.array([np.cos(a), np.sin(a), 0]) * rng.uniform(0.2, 0.4)
            from mathutils.bvhtree import BVHTree  # noqa: F401
            tips.append({"p": p - np.array([0, 0, 0.04]), "d": np.array([0, 0, 1.0]), "pad": -1, "kind": 3,
                         "scale": rng.uniform(0.6, 0.9)})
    else:
        nb = spec.get("nebari", {})
        reach = float(nb.get("reach", 0.3))
        r0 = float(spec["trunk"]["min_r"][0])
        for _ in range(n):
            a = rng.uniform(0, 2 * np.pi)
            rr = r0 + reach * rng.uniform(0.5, 1.4)
            tips.append({"p": np.array([np.cos(a) * rr, np.sin(a) * rr, 0.0]), "d": np.array([0, 0, 1.0]), "pad": -1,
                         "kind": 3, "scale": rng.uniform(0.7, 1.2)})
    return tips


# ----------------------------------------------------------------------------- one variant

def build_variant(vname, spec, height, a, report):
    t0 = time.time()
    rng = np.random.default_rng(spec["seed"])
    coll = bpy.data.collections.new(vname)
    bpy.context.scene.collection.children.link(coll)
    if a.tuft_spacing > 0:
        spec["tuft_spacing"] = a.tuft_spacing
    rock_obj = None
    rock_info = None
    masses = None
    pine = int(spec.get("pine", 1))
    if "rock" in spec:
        masses = build_rock_v2(vname, spec, rng)
        base_r = float(spec["trunk"]["base_r_measured"])
        rock_obj, rock_info = make_rock_object(f"SM_DKN_{vname}_Rock", masses, rng, coll,
                                               np.asarray(spec["trunk"]["pts"][0], float))
        seat_trunk_on_rock(rock_obj, spec)
        spec["roots"] = grow_rock_roots(rock_obj, spec, rng, base_r, masses)
    sk = treegen.build_skeleton(spec, rng)
    # v2: the spec profile already carries the sheet's girth and root swell; the tube flare only adds the
    # nebari foot (short decay), buttress lobes and a twist (C: massive and twisted)
    params = tubes.TubeParams(tile_m=TILE_M, plate_spacing=0.030 if pine == 3 else 0.022,
                              ring_len=0.030 if pine == 3 else 0.022, plate_min_r=0.05,
                              flare_amp=0.30 if pine == 4 else 0.22, flare_len=0.7 if pine == 4 else 0.6,
                              buttress=0.22 if pine == 4 else 0.16, twist=1.3 if pine in (3, 4) else 0.5,
                              lobes=0.08 if pine in (3, 4) else 0.06, plate_ratio=0.12, plate_max=0.03,
                              ellipse_y=float(spec["trunk"].get("ellipse_y", 1.0)))
    ground = 0.0 if "rock" not in spec else float(spec["trunk"]["pts"][0][2])
    ta = treegen.build_trunk_arrays(sk, height, params, rng, ground_z=ground)
    uw, vh = ta["uv_extent"]
    faces = [ta["quads"], ta["tris"]]
    uv0 = [ta["quads_uv"], ta["tris_uv"]]
    uv1 = normalise_uv(uv0, (uw, vh))
    Vt = ta["V"]
    # vertex colour: R junction, G moss, B canopy AO (linear floats)
    ao = treegen.canopy_ao(Vt, sk["envs"], 0.55)
    zrel = Vt[:, 2] - ground
    up = np.clip(ta["nrm"][:, 2] + 0.45, 0, 1)
    mn = col.value_noise2(Vt[:, 0] * 2 + Vt[:, 2], Vt[:, 1] * 2 - Vt[:, 2], spec["seed"], 0.25)
    # judge r0 item 12: mossy blending on the root flare (the sheet's trees all sit in moss)
    moss = np.clip((1.0 - zrel / 0.35), 0, 1) ** 0.7 * up * np.clip((mn - 0.22) * 2.4, 0, 1)
    is_root = np.isin(ta["branch"], [i for i, b in enumerate(sk["branches"]) if b.kind == "root"])
    moss = np.maximum(moss, is_root * up * np.clip((mn - 0.40) * 2.0, 0, 1) * 0.85)
    vc = np.stack([ta["junction"], moss, ao, np.ones(len(Vt))], 1)
    trunk = meshio.make_mesh(f"SM_DKN_{vname}_Trunk", Vt, faces, {"UVMap": uv0, "UV1": uv1, "UV2": uv1},
                             colour=vc, smooth=True, collection=coll)
    bark = bark_material(f"MI_DKN_{vname}_Bark")
    trunk.data.materials.append(bark)
    # ---- foliage: radial needle bursts (no pad cores: judge r0 'brown saucers'), plus ground-cover clumps
    # v2: the hand-shaped rosette library (vegetation/rosette.py), 5 units, instanced one per shoot tip
    tufts = rosmod.library()
    n_b = len(tufts)
    tips = [dict(t, variant=int(rng.integers(n_b))) for t in sk["tips"]]
    gtips = []                  # v2: ground cover lives on the optional mound mesh (SM_DKN_BaseMound_*)
    fm = fol.instance(tufts, tips, rng)
    elems = wind_data.elements(sk, ground)
    pp2 = wind_data.pp2_arrays(elems)
    pad_elem = elems[0]["pad_elem"]
    Vf = fm.V
    Tf = fm.T
    fuv0 = fm.uv0
    ext_f = (fm.grid_w / fol.CELLS_U, np.ceil((fm.cells_used / fm.grid_w + 1) / fol.CELLS_V))
    fuv1 = normalise_uv([fuv0], ext_f)[0]
    n_pads = len(sk["envs"])
    tex_uv = np.array([wind_data.texel_uv(pad_elem[int(p)], pp2["w"], pp2["h"]) for p in range(n_pads)]
                      + [wind_data.texel_uv(0, pp2["w"], pp2["h"])])          # index n_pads: ground cover -> trunk
    pid = np.where(fm.pad_id < 0, n_pads, fm.pad_id)
    fuv2 = tex_uv[pid][Tf]
    fao = treegen.foliage_ao(Vf, fm.pad_id, sk["envs"])
    fuv3 = np.stack([fao, np.zeros_like(fao)], 1)[Tf]
    fcol = wind_data.foliage_colours(Vf, fm.pad_id, fm.tuft_id, elems)
    gmask = fm.pad_id < 0
    if gmask.any():
        fcol[gmask, 0] = np.clip((Vf[gmask, 2] - Vf[gmask, 2].min()) / 0.3, 0, 1)   # grass: sway by height
    envs = sk["envs"]

    def env_normal(P):
        out = np.zeros_like(P)
        out[:, 2] = 1.0
        for pi, e in enumerate(envs):
            m = fm.pad_id == pi
            if m.any():
                out[m] = e.normal(P[m])
        return out
    fnorm = fol.volume_normals(Vf, Tf, env_normal, 0.5)
    foli = meshio.make_mesh(f"SM_DKN_{vname}_Foliage", Vf, [Tf],
                            {"UVMap": [fuv0], "UV1": [fuv1], "UV2": [fuv2], "UV3": [fuv3]},
                            colour=fcol, normals=fnorm, smooth=True, collection=coll)
    foli.data.materials.append(needle_material())
    foli.data.update()
    # ---- collision: trunk runs
    part0 = ta["parts"][0]
    n0 = part0["n"]
    m0 = len(part0["rings"])
    rings = part0["V"][: m0 * n0].reshape(m0, n0, 3)
    runs = trunk_runs(part0["rings"], part0["ring_r"])
    for k, (i0, i1) in enumerate(runs):
        lo = max(i0, 0)
        pts = rings[lo: i1 + 1].reshape(-1, 3)
        pts = pts[pts[:, 2] > ground - 0.12]
        if len(pts) >= 4:
            ucx_from_points(trunk, pts, k)
    if rock_obj is not None:
        # one hull per convex mass (the masses ARE convex, so each hull hugs its mass)
        for k, (Vm, Fm) in enumerate(masses):
            ucx_from_points(rock_obj, Vm, k)
    mound = None
    mound_info = None
    if vname.endswith("1"):
        # v2: one optional base mound per tree family, built with variant 1 (both variants share the origin)
        mound, mound_info = build_mound(vname[4], spec, np.random.default_rng(spec["seed"] + 900), coll, rock_obj)
    info = {"variant": vname, "build_s": 0.0, "tufts": len(sk["tips"]), "pads": len(envs),
            "branches": len(sk["branches"]), "pad_info": sk["pad_info"], "uv0_extent_trunk": [uw, vh],
            "uv0_extent_foliage": list(map(float, ext_f)), "trunk_runs": runs,
            "fork_exponents": skeleton.fork_exponents(sk["branches"]),
            "tris": {"trunk": int(sum(len(f) * (2 if f.shape[1] == 4 else 1) for f in faces)), "foliage": int(len(Tf))},
            "elements": len(elems), "pp2_size": [pp2["w"], pp2["h"]], "girth": spec.get("girth"),
            "roots": len(spec.get("roots", [])) if rock_obj is not None else spec.get("nebari", {}).get("count")}
    if rock_obj is not None:
        info["tris"]["rock"] = len(rock_obj.data.polygons)
        info["rock"] = rock_info
    # G8 flare: trunk radius near the ground / at 1 m above it
    zq = part0["rings"][:, 2] - ground
    rq = part0["ring_r"]
    r_ground = float(np.interp(0.02, zq, rq)) if zq.min() < 0.02 else float(rq[0])
    r_1m = float(np.interp(1.0, zq, rq)) if zq.max() > 1.0 else float(rq[-1])
    info["flare_ratio"] = round(r_ground / max(r_1m, 1e-6), 3)
    zmid = (zq > 0.15 * spec["height_m"]) & (zq < 0.5 * spec["height_m"])
    info["trunk_r_mid_m"] = round(float(np.median(rq[zmid])), 4) if zmid.any() else None
    info["min_twig_r_mm"] = round(1000 * min(float(b.r.min()) for b in sk["branches"]), 2)
    unit_stats = [rosmod.measure(tf) for tf in tufts]
    info["rosette_units"] = unit_stats
    lens = [u["needle_len_cm"][0] / 100 for u in unit_stats] + [u["needle_len_cm"][1] / 100 for u in unit_stats]
    info["needle_len_cm"] = [round(100 * 0.88 * min(lens), 2), round(100 * 1.12 * max(lens), 2)]   # x instance scale 0.88-1.12
    # texel density per order (study 4.6)
    dens = {}
    for bi, p in ta["parts"].items():
        o = sk["branches"][bi].order
        k = p["k"]
        circ = 2 * np.pi * float(np.median(p["ring_r"]))
        dens.setdefault(str(min(o, 3)), []).append(1024 / 100.0 * k * TILE_M / max(circ, 1e-6))
    info["u_texel_px_per_cm_by_order"] = {o: round(float(np.median(v)), 2) for o, v in dens.items()}
    tk = {}
    for bi, p in ta["parts"].items():
        kind = sk["branches"][bi].kind
        tk[kind] = tk.get(kind, 0) + int(sum(len(f) * (2 if f.shape[1] == 4 else 1) for f in p["faces"]))
    info["trunk_tris_by_kind"] = tk
    report["variants"][vname] = info
    if mound is not None:
        info["mound"] = mound_info
        info["tris"]["mound"] = mound_info["tris"]
    objs = {"trunk": trunk, "foliage": foli, "rock": rock_obj, "mound": mound, "sk": sk, "elems": elems, "pp2": pp2,
            "tufts": tufts, "bark": bark, "spec": spec, "fm": fm}
    info["build_s"] = round(time.time() - t0, 1)
    print(f"[{vname}] bursts {info['tufts']} trunk tris {info['tris']['trunk']} foliage tris {info['tris']['foliage']}"
          f" flare {info['flare_ratio']} r_mid {info['trunk_r_mid_m']} kinds {info['trunk_tris_by_kind']} "
          f"{info['build_s']} s", flush=True)
    return objs


def bake_and_finish(vname, o, all_objs, a, report):
    """Unique trunk AO on UV2 (other variants hidden), PP2 textures, wind.json."""
    trunk = o["trunk"]
    hidden = []
    for other in all_objs:
        if other is trunk or other.name.startswith(("UCX_",)):
            continue
        if not (other.name.startswith(f"SM_DKN_{vname}_")):
            if not other.hide_render:
                other.hide_render = True
                hidden.append(other)
    me = trunk.data
    me.uv_layers.active = me.uv_layers["UV2"]
    ao_img = textures.bake_ao(trunk, f"T_DKN_{vname}_Trunk_AO", size=1024, samples=a.samples, margin=8)
    me.uv_layers.active = me.uv_layers["UVMap"]
    for h in hidden:
        h.hide_render = False
    rough = bpy.data.images.new(f"__rough_{vname}", 1024, 1024, alpha=False, float_buffer=False, is_data=True)
    rough.pixels.foreach_set(np.tile(np.array([0.88, 0.88, 0.88, 1.0], np.float32), 1024 * 1024))
    orm_path = TEX / f"T_DKN_{vname}_Trunk_ORM.png"
    textures.pack_orm(ao_img, rough, None, orm_path)
    bpy.data.images.remove(rough)
    bpy.data.images.remove(ao_img)
    orm = load_img(orm_path, True)
    orm.name = f"T_DKN_{vname}_Trunk_ORM"
    # rebuild the bark material with the unique trunk ORM on UV2
    old = o["bark"]
    new = bark_material(f"MI_DKN_{vname}_Bark__tmp", orm)
    trunk.data.materials[0] = new
    bpy.data.materials.remove(old)
    new.name = f"MI_DKN_{vname}_Bark"
    o["bark"] = new
    # PP2 textures
    pp2 = o["pp2"]
    sc = bpy.context.scene
    s = sc.render.image_settings
    s.file_format = "OPEN_EXR"
    s.color_mode = "RGBA"
    s.color_depth = "16"
    s.exr_codec = "ZIP"
    img = bpy.data.images.new(f"T_DKN_{vname}_PivotPos", pp2["w"], pp2["h"], alpha=True, float_buffer=True, is_data=True)
    img.pixels.foreach_set(pp2["pivot_pos"].ravel())
    pos_path = TEX / f"T_DKN_{vname}_PivotPos.exr"
    img.save_render(str(pos_path), scene=sc)
    bpy.data.images.remove(img)
    xv_path = TEX / f"T_DKN_{vname}_XVector.png"
    textures.write_png(pp2["xvector"], xv_path, alpha=True)
    # verify the half-float parent indices survived the EXR writer (study 4.9)
    chk = bpy.data.images.load(str(pos_path))
    chk.colorspace_settings.is_data = True
    px = np.array(chk.pixels[:], np.float32).reshape(pp2["h"], pp2["w"], 4)
    want = [int(e["parent"]) for e in o["elems"]]
    got = [int(np.float16(px[e["id"] // pp2["w"], e["id"] % pp2["w"], 3]).view(np.uint16)) for e in o["elems"]]
    bpy.data.images.remove(chk)
    pad_tufts = {}
    for t in o["sk"]["tips"]:
        pad_tufts[t["pad"]] = pad_tufts.get(t["pad"], 0) + 1
    wj = wind_data.wind_json(f"SM_DKN_{vname}", o["elems"], pp2,
                             {"pivot_pos": pos_path.name, "xvector": xv_path.name}, pad_tufts)
    wj["pp2"]["parent_index_roundtrip_ok"] = want == got
    (EXPORT / f"SM_DKN_{vname}.wind.json").write_text(json.dumps(wj, indent=1), encoding="utf-8")
    report["variants"][vname]["pp2_roundtrip_ok"] = want == got
    report["variants"][vname]["wind_levels"] = wj["levels"]


def unit_qa(tufts, report):
    """Study 4.12: full qa_check (UV0 overlap included) on one tuft of each variant before instancing."""
    out = []
    coll = bpy.data.collections.new("TuftUnits")
    bpy.context.scene.collection.children.link(coll)
    for i, tf in enumerate(tufts):
        fm = fol.instance([tf], [{"p": (0, 0, 0), "d": (0, 0, 1), "pad": 0, "variant": 0}], np.random.default_rng(1))
        ext = (fm.grid_w / fol.CELLS_U, np.ceil((fm.cells_used / fm.grid_w + 1) / fol.CELLS_V))
        uv1 = normalise_uv([fm.uv0], ext)[0]
        name = f"SM_DKN_RosetteUnit{'ABCDEFG'[i]}"
        obj = meshio.make_mesh(name, fm.V, [fm.T], {"UVMap": [fm.uv0], "UV1": [uv1]}, collection=coll)
        obj.data.materials.append(needle_material())
        r = qa_check([obj], require_uv1=True, require_ucx=False, uv0_tile_range=(-0.001, max(ext) + 0.001))
        fails = [c for c in r["checks"] if not c["passed"]]
        out.append({"unit": name, **rosmod.measure(tf), "passed": r["passed"],
                    "fails": fails})
        bpy.data.objects.remove(obj)
    bpy.data.collections.remove(coll)
    report["tuft_unit_qa"] = out


def main():
    a = args()
    assert_owner(LOCK, "claude")
    specs = json.loads(SPEC.read_text(encoding="utf-8"))
    names = [v for v in specs if (not a.variants or v in a.variants.split(","))]
    reset()
    global djm
    import dojo_materials as djm  # noqa: E402
    height = np.load(BUILD / "tex" / "bark_height.npy")
    report = {"built": time.strftime("%Y-%m-%d %H:%M:%S"), "variants": {}, "fast": a.fast}
    built = {}
    for v in names:
        built[v] = build_variant(v, specs[v], height, a, report)
    all_objs = [ob for ob in bpy.data.objects if ob.type == "MESH"]
    if not a.fast:
        for v, o in built.items():
            bake_and_finish(v, o, all_objs, a, report)
        unit_qa(next(iter(built.values()))["tufts"], report)
        qa_all = {}
        for v, o in built.items():
            uw, vh = report["variants"][v]["uv0_extent_trunk"]
            r_t = qa_check([o["trunk"]], require_uv1=True, require_ucx=True, texel_density=BARK_TEXEL,
                           uv0_tile_range=(-0.001, max(uw, vh) + 0.001))
            ext_f = report["variants"][v]["uv0_extent_foliage"]
            r_f = qa_check([o["foliage"]], require_uv1=True, require_ucx=False,
                           uv0_tile_range=(-0.001, max(ext_f) + 0.001))
            qa_all[v] = {"trunk": r_t, "foliage": r_f}
            if o.get("mound") is not None:
                S = float(o["mound"].get("uv0_tile_extent", 2.0))
                qa_all[v]["mound"] = qa_check([o["mound"]], require_uv1=True, require_ucx=True,
                                              uv0_tile_range=(-0.001, S + 0.001))
            if o["rock"] is not None:
                S = float(o["rock"].get("uv0_tile_extent", 2.0))
                qa_all[v]["rock"] = qa_check([o["rock"]], require_uv1=True, require_ucx=True, texel_density=5.12,
                                             uv0_tile_range=(-0.001, S + 0.001))
            for k, r in qa_all[v].items():
                fails = [c for c in r["checks"] if not c["passed"]]
                print(f"QA {v} {k}: passed={r['passed']} fails={[(c['name'], c['detail'][:90]) for c in fails]}",
                      flush=True)
        (BUILD / "qa_report.json").write_text(json.dumps(
            {"waivers": [], "skips": [],
             "notes": ["foliage: require_ucx=False by design (study 4.10: canopies must not block wall-top runs "
                       "and climbs; set the component to NoCollision in Unreal)",
                       "UV0 overlap test RUN on every mesh (not skipped): trunk UV0 is whole-tile packed and "
                       "foliage UV0 gives every needle its own cell, so the study 4.12 skip is not needed"],
             "tuft_unit_qa": report.get("tuft_unit_qa"), "results": qa_all}, indent=1, default=str), encoding="utf-8")
        report["qa_passed"] = {v: {k: r["passed"] for k, r in d.items()} for v, d in qa_all.items()}
        all_ok = all(r["passed"] for d in qa_all.values() for r in d.values()) and             all(u["passed"] for u in report.get("tuft_unit_qa", []))
        report["qa_all_passed"] = all_ok
        if not all_ok:
            print("QA FAILED: nothing exported", flush=True)
        if not a.no_export and all_ok:
            exp = {}
            for v, o in built.items():
                for key in ("trunk", "foliage", "rock", "mound"):
                    ob = o[key]
                    if ob is None:
                        continue
                    path = EXPORT / f"{ob.name}.fbx"
                    res = export_fbx(str(path), [ob], kind="static")
                    exp[ob.name] = {"file": str(path.relative_to(ROOT)), "sha256": sha256(path),
                                    "warnings": res.get("warnings", []),
                                    "objects": [x if isinstance(x, str) else getattr(x, "name", str(x))
                                                for x in res.get("objects", [])]}
            for f in sorted(TEX.glob("T_DKN_*")):
                exp[f.name] = {"file": str(f.relative_to(ROOT)), "sha256": sha256(f)}
            for f in sorted(EXPORT.glob("*.wind.json")):
                exp[f.name] = {"file": str(f.relative_to(ROOT)), "sha256": sha256(f)}
            (BUILD / "export_report.json").write_text(json.dumps(
                {"pipeline": "Scripts/pipeline/export_fbx.py kind=static", "files": exp,
                 "expected_warnings": "the foliage files carry no UCX_/SOCKET_ children by design (study 4.2)"},
                indent=1), encoding="utf-8")
    out_blend = Path(a.out_blend) if a.out_blend else BLEND
    out_blend.parent.mkdir(parents=True, exist_ok=True)
    if not a.fast:
        try:
            bpy.ops.file.pack_all()
        except Exception as exc:  # noqa: BLE001
            print("pack_all:", exc)
    bpy.ops.wm.save_as_mainfile(filepath=str(out_blend), compress=True)
    rep_path = BUILD / ("build_report_fast.json" if a.fast else "build_report.json")
    rep_path.write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    print("saved", out_blend, flush=True)


if __name__ == "__main__":
    main()
