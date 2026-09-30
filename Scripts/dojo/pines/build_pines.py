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
from mathutils.bvhtree import BVHTree

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
import rock_v3  # noqa: E402

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


def mound_moss_material():
    """v2f: the mound's moss = M_DKN_Moss x a cushion factor from VertexColor.R (gaps 0.42 x, cushion tops 1.25 x
    and a touch yellower)."""
    name = "MI_DKN_MoundMoss"
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = moss_material().copy()
    m.name = name
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    src = bsdf.inputs["Base Color"].links[0].from_socket
    vc = nt.nodes.new("ShaderNodeVertexColor")
    vc.layer_name = "Color"
    sv = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(vc.outputs["Color"], sv.inputs["Color"])
    ramp = nt.nodes.new("ShaderNodeMapRange")
    ramp.inputs["To Min"].default_value = 0.30
    ramp.inputs["To Max"].default_value = 1.35
    nt.links.new(sv.outputs["Red"], ramp.inputs["Value"])
    comb = nt.nodes.new("ShaderNodeCombineColor")
    mulg = nt.nodes.new("ShaderNodeMath")
    mulg.operation = "MULTIPLY"
    mulg.inputs[1].default_value = 1.06
    nt.links.new(ramp.outputs["Result"], mulg.inputs[0])
    nt.links.new(ramp.outputs["Result"], comb.inputs[0])
    nt.links.new(mulg.outputs["Value"], comb.inputs[1])
    nt.links.new(ramp.outputs["Result"], comb.inputs[2])
    out = _mix(nt, src, comb.outputs["Color"], 1.0, 200, 500, "MULTIPLY")
    nt.links.new(out, bsdf.inputs["Base Color"])
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
    tinted = _mix(nt, src, (1.08, 1.10, 0.78, 1.0), 1.0, -200, 600, "MULTIPLY")   # v2f: l16 fern skirt read pale straw; the sheet's skirt is green
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


# ----------------------------------------------------------------------------- hull / UV helpers (mound stones)

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


# ----------------------------------------------------------------------------- rock-stone helpers (the mound's stones)

# (the v2 lobe rock is gone: the rock stage builds the D rock with rock_v3.py; the mound's small stones keep this)
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


# ----------------------------------------------------------------------------- v3 rock (stone study method)

# v2f: measured on the P4F / P4Q rock bodies: stone median (111,101,84) / (91,85,72), hue 38-41, luma p25-p75
# 60-69 .. 120-150; the v2 rock stage rendered (106,97,72) hue 44, p25-p75 75-109: a touch too yellow and too
# narrow a value spread (SG10). Less yellow tint, more contrast about the median, a stronger baked normal.
ROCK_TINT = (0.68, 0.67, 0.665)          # final-1 measured (101,93,71) hue 44 sat 0.27, p75 L 110: greyer, lighter
LICHEN_ORANGE = (0.36, 0.16, 0.035, 1.0)  # sRGB ~ (162, 111, 52): the sheet's ochre specks
LICHEN_GREY = (0.34, 0.32, 0.18, 1.0)     # sRGB ~ (158, 153, 118): yellow-grey crust
LICHEN_PALE = (0.40, 0.38, 0.30, 1.0)     # pale grey-yellow crust
SOIL = (0.075, 0.058, 0.042, 1.0)
ROCK_CONTRAST = 0.60          # l15: 0.9 made the granite grain a terrazzo speckle; relief carries the spread
ROCK_PIVOT = 0.10
ROCK_SAT = 0.60
ROCK_GRIME_DARK = 0.62


def rock_v3_materials(vname, S, paths):
    """MI_DKN_<V>_Rock: the shared library granite (M_DJ_Granite: BC + ORM + the 'Wear' layer, tiled on UV0 at its
    4 m tile via the rock's metres-per-UV S) under the rock's unique maps: T_DKN_<V>_Rock_N (DirectX, the baked meso
    relief and cracks: the library's own 3.5 / 9 cm facet normal is NOT used, study rule 10), _ORM (baked AO for
    Unreal; Cycles shades its own), _M (R moss, G lichen, B dirt). Grain micro-relief = a 0.1 bump from the granite
    albedo. MI_DKN_<V>_RockMoss: the pines' moss set on the cushions, tiled on UV0 at 2 m."""
    mat = djm.make_material("M_DJ_Granite", rebuild=True, tint=ROCK_TINT)
    mat.name = f"MI_DKN_{vname}_Rock"
    nt = mat.node_tree
    N, L = nt.nodes, nt.links
    bsdf = next(n for n in N if n.type == "BSDF_PRINCIPLED")
    uvn = next(n for n in N if n.type == "UVMAP")
    uvn.uv_map = "UVMap"
    mp = N.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (S / 4.0, S / 4.0, 1.0)
    for lk in list(uvn.outputs["UV"].links):
        L.new(mp.outputs["Vector"], lk.to_socket)
    L.new(uvn.outputs["UV"], mp.inputs["Vector"])
    raw = N.new("ShaderNodeUVMap")
    raw.uv_map = "UVMap"

    def utex(path, nc):
        t = N.new("ShaderNodeTexImage")
        t.image = load_img(path, nc)
        t.interpolation = "Linear"
        L.new(raw.outputs["UV"], t.inputs["Vector"])
        return t
    tn, torm, tm = utex(paths["N"], True), utex(paths["ORM"], True), utex(paths["M"], True)
    sepm = N.new("ShaderNodeSeparateColor")
    L.new(tm.outputs["Color"], sepm.inputs["Color"])
    col = bsdf.inputs["Base Color"].links[0].from_socket
    rough = bsdf.inputs["Roughness"].links[0].from_socket
    # value spread (stone study SG10 / S2: t5 measured p90/p50 1.4 and local std 0.055 against the sheet's 3.3 and
    # 0.11): more grain contrast and a weathering mottle that darkens (the 'Wear' R grime, baked per vertex)
    # contrast about the granite's own linear median (Blender's Bright/Contrast pivots on 0.5: t6 went black)
    v1 = N.new("ShaderNodeVectorMath")
    v1.operation = "SUBTRACT"
    L.new(col, v1.inputs[0])
    v1.inputs[1].default_value = (ROCK_PIVOT,) * 3
    v2 = N.new("ShaderNodeVectorMath")
    v2.operation = "MULTIPLY_ADD"
    L.new(v1.outputs[0], v2.inputs[0])
    v2.inputs[1].default_value = (1.0 + ROCK_CONTRAST,) * 3
    v2.inputs[2].default_value = (ROCK_PIVOT,) * 3
    v3 = N.new("ShaderNodeVectorMath")
    v3.operation = "MAXIMUM"
    L.new(v2.outputs[0], v3.inputs[0])
    v3.inputs[1].default_value = (0.004, 0.004, 0.004)
    hs = N.new("ShaderNodeHueSaturation")
    hs.inputs["Saturation"].default_value = ROCK_SAT
    L.new(v3.outputs[0], hs.inputs["Color"])
    wa = N.new("ShaderNodeAttribute")
    wa.attribute_type = "GEOMETRY"
    wa.attribute_name = "Wear"
    wsep = N.new("ShaderNodeSeparateColor")
    L.new(wa.outputs["Color"], wsep.inputs["Color"])
    dk = N.new("ShaderNodeMath")
    dk.operation = "MULTIPLY_ADD"
    dk.inputs[1].default_value = -ROCK_GRIME_DARK
    dk.inputs[2].default_value = 1.0
    L.new(wsep.outputs["Red"], dk.inputs[0])
    col = _mix(nt, hs.outputs["Color"], dk.outputs["Value"], 1.0, 250, 400, "MULTIPLY")
    # lichen: three crust colours picked by a 20 cm noise (UV0 x S = metres)
    nz = N.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 3.0 * S
    L.new(raw.outputs["UV"], nz.inputs["Vector"])
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.50
    ramp.color_ramp.elements[0].color = LICHEN_ORANGE
    ramp.color_ramp.elements[1].position = 0.66
    ramp.color_ramp.elements[1].color = LICHEN_GREY
    e = ramp.color_ramp.elements.new(0.80)
    e.color = LICHEN_PALE
    L.new(nz.outputs["Fac"], ramp.inputs["Fac"])
    lich = N.new("ShaderNodeMath")
    lich.operation = "MULTIPLY"
    lich.inputs[1].default_value = 1.0
    L.new(sepm.outputs["Green"], lich.inputs[0])
    col = _mix(nt, col, ramp.outputs["Color"], lich.outputs["Value"], 300, 400, "MIX")
    dirt = N.new("ShaderNodeMath")
    dirt.operation = "MULTIPLY"
    dirt.inputs[1].default_value = 0.55
    L.new(sepm.outputs["Blue"], dirt.inputs[0])
    col = _mix(nt, col, SOIL, dirt.outputs["Value"], 400, 400, "MIX")
    # flat moss in the crevices and on top (the moss set's colour, tiled at 2 m)
    mm = N.new("ShaderNodeMapping")
    mm.inputs["Scale"].default_value = (S / 2.0, S / 2.0, 1.0)
    L.new(raw.outputs["UV"], mm.inputs["Vector"])
    mbc = N.new("ShaderNodeTexImage")
    mbc.image = load_img(TEX / "T_DKN_Moss_BC.png", False)
    L.new(mm.outputs["Vector"], mbc.inputs["Vector"])
    # v2f: the sheet's rock moss (91,95,56) / (82,89,48) is paler and less saturated than the mound moss set
    mcol = _mix(nt, mbc.outputs["Color"], (1.10, 1.12, 1.45, 1.0), 1.0, 450, 250, "MULTIPLY")
    col = _mix(nt, col, mcol, sepm.outputs["Red"], 500, 400, "MIX")
    L.new(col, bsdf.inputs["Base Color"])
    rm = N.new("ShaderNodeMix")
    rm.data_type = "FLOAT"
    L.new(sepm.outputs["Red"], rm.inputs["Factor"])
    L.new(rough, rm.inputs["A"])
    rm.inputs["B"].default_value = 0.95
    L.new(rm.outputs["Result"], bsdf.inputs["Roughness"])
    # normal: the unique baked map, plus the grain as a small bump from the granite albedo
    nrm = _dx_to_gl_normal(nt, tn.outputs["Color"], 2.2, 200, -500)
    bw = N.new("ShaderNodeRGBToBW")
    L.new(col, bw.inputs["Color"])
    bump = N.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.10
    bump.inputs["Distance"].default_value = 0.002
    L.new(bw.outputs["Val"], bump.inputs["Height"])
    L.new(nrm, bump.inputs["Normal"])
    L.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    for n in list(N):
        if n.type == "NORMAL_MAP" and not n.outputs["Normal"].links:
            N.remove(n)
    mat["dkn_rock_v3_S_m_per_uv0"] = float(S)
    moss = moss_material().copy()
    moss.name = f"MI_DKN_{vname}_RockMoss"
    for n in moss.node_tree.nodes:
        if n.type == "MAPPING":
            n.inputs["Scale"].default_value = (S / 2.0, S / 2.0, 1.0)
    return mat, moss


def rs_unit(v):
    v = np.asarray(v, float)
    return v / max(float(np.linalg.norm(v)), 1e-12)


def grow_rock_roots_v3(rock_obj, extra, spec, rng):
    """v3 roots (owner: 8-12 tapering roots that hug the rock faces, shrink-wrapped and partly sunk in the moss, and
    dive into the cracks down to the ground). Each root leaves the flared base over the rock top, is snapped to the
    BARE rock surface every 2.5 cm (its centre 0.25 r above it: 3/4 sunk into rock and moss cushions), slides down
    the fall line, is drawn into the nearest lower cleft or crack and then follows it down, keeps clear of the roots
    already laid, and runs 6-12 cm into the soil at the foot. About half of them fork once (pipe rule at the fork)."""
    Vb, Fb = extra["bare_V"], extra["bare_F"]
    bvh = BVHTree.FromPolygons([tuple(map(float, v)) for v in Vb], [tuple(map(int, f)) for f in Fb])
    att = np.asarray(extra["attract"], float)
    base = np.asarray(spec["trunk"]["pts"][0], float)
    base_r = float(spec["trunk"]["min_r"][0])
    down = np.array([0.0, 0.0, -1.0])
    # azimuths (deg; 270 = front, 180 = left): D1's front panel shows the roots gathered down the LEFT flank and
    # one down the front cleft; the side and 3/4 panels show more round the back-left; D2 likewise
    # v2f (judge delta 2, P4F/P4Q: 8-12 thin roots of varied thickness from a small flare over the top and down
    # 2-3 faces, some lifted off the stone, a tangle of 15-25 visible strands with the forks): 13 primaries
    # l15 close-up: P4F's roots drape the LEFT flank and the front-left shoulder; most azimuths there
    az_by = {"PineD1": [120, 138, 152, 166, 180, 194, 208, 222, 240, 262, 300, 340, 40],
             "PineD2": [130, 148, 165, 180, 196, 212, 230, 250, 275, 305, 340, 30, 90]}
    az = np.deg2rad(np.asarray(az_by.get(spec["variant"], az_by["PineD1"]), float) + rng.normal(0, 6))
    laid = []

    def clearance(p, r):
        push = np.zeros(3)
        for P, R in laid:
            d = P - p
            dist = np.linalg.norm(d, axis=1)
            j = int(np.argmin(dist))
            need = R[j] + r + 0.006
            if 1e-6 < dist[j] < need:
                push -= d[j] / dist[j] * (need - dist[j])
        return push

    roots = []

    def walk(p0, d0, r0, max_len, parent=None, forks=True, top_run=0.0, lift=0.0, lift_s0=0.0):
        pts = [np.asarray(p0, float)]
        radii = [r0]
        d = rs_unit(d0)
        s = 0.0
        step = 0.025
        wob = rng.normal(0, 1, 3)
        in_crack = False
        while s < max_len:
            t = s / max_len
            r = max(0.006, r0 * (1.0 - 0.72 * t))
            p = pts[-1] + d * step
            p = p + clearance(p, r) * 0.8
            hit = bvh.find_nearest(tuple(map(float, p)))
            if hit[0] is None:
                break
            loc, nrm = np.array(hit[0]), np.array(hit[1])
            if loc[2] < 0.02:                            # at the foot: the tip dives under the moss apron
                pts.append(loc - nrm * 0.5 * r + np.array([0.0, 0.0, -0.04]))
                radii.append(r)
                break
            lift_now = lift > 0 and (lift_s0 < s < lift_s0 + lift) and not in_crack
            # v2f: 0.25 r -> 0.55 r above the stone (the thinner roots vanished into the rock and cushions)
            p = loc + nrm * ((1.25 * r + 0.006) if lift_now else (0.85 * r if not in_crack else 0.35 * r))
            g = down - nrm * float(nrm @ down)
            gl = np.linalg.norm(g)
            g = g / gl if gl > 1e-6 else np.zeros(3)
            wob = 0.8 * wob + 0.2 * rng.normal(0, 1, 3)
            # over the top first (the root plate spreads before the roots turn down: t2 roots slid straight
            # down the front face as parallel ropes), then the fall line
            gw = 0.04 if s < top_run else 0.20 + 0.45 * min(1.0, 2 * t)
            dn = 0.70 * d + gw * g + 0.06 * wob
            dv = att - p
            dist = np.linalg.norm(dv, axis=1)
            ok = (dist < 0.22) & (dv[:, 2] < 0.01)
            if ok.any():
                j = int(np.argmin(np.where(ok, dist, 9.0)))
                # l15: strong crack attraction pulled every root into a straight vertical line down a crack
                dn = dn + (0.25 if dist[j] > 0.03 else 0.12) * dv[j] / max(dist[j], 1e-6)
                in_crack = dist[j] < 0.03
            else:
                in_crack = False
            dn = dn - nrm * float(nrm @ dn)
            d = rs_unit(dn)
            pts.append(p)
            radii.append(r)
            s += step
        P = np.array(pts)
        if len(P) < 5:
            return
        R = np.array(radii)
        idx = len(roots)
        laid.append((P, R))
        roots.append({"pts": P[1:].tolist(), "profile": R.tolist(), "exact": True,
                      **({"parent_root": parent} if parent is not None else {})})
        L_ = float(np.linalg.norm(np.diff(P, axis=0), axis=1).sum())
        if forks and L_ > 0.4 and rng.uniform() < 0.75:
            k = int(len(P) * rng.uniform(0.25, 0.5))
            dd = P[min(k + 1, len(P) - 1)] - P[k]
            ang = np.deg2rad(rng.choice([-1, 1]) * rng.uniform(28, 45))
            c, s_ = np.cos(ang), np.sin(ang)
            dd = np.array([c * dd[0] - s_ * dd[1], s_ * dd[0] + c * dd[1], dd[2]])
            pr_ = np.asarray(roots[idx]["profile"], float)
            pr_[k:] *= 0.86                              # the parent thins past the fork (pipe rule, n ~ 2.5)
            roots[idx]["profile"] = pr_.tolist()
            laid[-1] = (P, pr_)
            walk(P[k], dd, float(R[k]) * 0.60, L_ * (1 - k / len(P)) * 0.8, idx, forks=L_ > 0.9)

    for a in az:
        # v2f: varied, thinner (base_r is now the slim 0.13-0.15 m trunk: 1.6-3.6 cm root radii); every third
        # root is lifted 1-2.5 cm off the stone over a 10-25 cm stretch (the sheet's roots bridge hollows)
        r0 = base_r * rng.uniform(0.20, 0.38)
        dirv = np.array([np.cos(a), np.sin(a), -0.12])
        p0 = base + np.array([np.cos(a), np.sin(a), 0.0]) * base_r * 0.75 + np.array([0.0, 0.0, 0.25 * base_r])
        lift = rng.uniform(0.10, 0.25) if rng.uniform() < 0.35 else 0.0
        walk(p0, dirv, r0, 2.4, top_run=rng.uniform(0.20, 0.45), lift=lift, lift_s0=rng.uniform(0.15, 0.5))
    return roots


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
    xmax = 0.0
    for i in sorted(range(len(parts)), key=lambda i: -sizes[i][1]):
        w, h = sizes[i] * scale
        if x + w > 0.98 and x > 0.0:
            x, y, row_h = 0.0, y + row_h + 0.01, 0.0
        place[i] = (x + 0.01, y + 0.01)
        x += w + 0.01
        xmax = max(xmax, x + 0.01)
        row_h = max(row_h, h)
    ymax = y + row_h + 0.02
    # v2 s17: a chart wider than the tile (the mound surface) overflowed U (qa uv1_inside_0_1); fit both axes
    k = min(1.0, 0.98 / ymax, 0.98 / max(xmax, 1e-6))
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
        md = {"rx": float(np.ptp(foot[:, 0])) / 2 + 0.32, "ry": float(np.ptp(foot[:, 1])) / 2 + 0.32,
              "cx": float(c[0]), "cy": float(c[1]), "h": 0.10}
    else:
        md = dict(spec["mound"])
        md["ry"] = max(md["ry"], 0.55 * md["rx"])
    rx, ry, cx, cy, h = md["rx"], md["ry"], md["cx"], md["cy"], md["h"]
    nr, ns = (44, 160) if rock_obj is None else (26, 96)      # v2f: fine enough for 2.5 cm moss cushions
    seed = int(rng.integers(1 << 20))
    tree = rock_obj is None
    # v2 s9: the sheet's mound is a low mossy HILL: conical-ish flanks from a rounded crown at the trunk down to the
    # ground, cushions of moss 2-6 cm proud, the edge running under the ground (no lip); s8 had a flat disc with a
    # vertical soil edge. Moss hummocks = gaussian bumps on the crown and flanks.
    # v2f (judge delta 7, checked on P1F/P2F/P3F): the sheet's mounds are LOW DISCS: a thin flat-topped moss bed
    # about 0.4-0.6 of the sheet's band height with a small rise at the trunk, lumpy from moss clumps, stones and
    # ferns rather than from the ground shape, and a pale gravel/soil rim. v2's cone + 2.5-7.5 cm hummocks read as a
    # thick olive hump (A1: a tall hump on the right).
    n_hum = 150 if tree else 18
    hum_a = rng.uniform(0, 2 * np.pi, n_hum)
    hum_r = np.sqrt(rng.uniform(0.0, 0.88, n_hum))
    hum_c = np.stack([cx + rx * hum_r * np.cos(hum_a), cy + ry * hum_r * np.sin(hum_a)], 1)
    # l7 mound lab: a thin flat bed let the nebari roots exit under the rim and read as a flat plate; the sheet's
    # mound (P1F crop) rises ~0.2 m at the trunk and is LUMPY with small moss cushions: many 2.5-6 cm cushions
    hum_s = (rng.uniform(0.025, 0.06, n_hum) if tree else rng.uniform(0.035, 0.10, n_hum))
    hum_h = (rng.uniform(0.012, 0.034, n_hum) if tree else rng.uniform(0.015, 0.045, n_hum))

    def base_z(px, py):
        px = np.asarray(px, float)
        py = np.asarray(py, float)
        rr = np.sqrt(((px - cx) / rx) ** 2 + ((py - cy) / ry) ** 2)
        if tree:
            # flat bed (0.45 h) with a soft shoulder to the rim + a trunk rise (0.35 h within ~0.3 of the radius)
            q = np.clip(rr, 0, 1)
            z = 0.72 * h * np.clip(1 - q ** 2.2, 0, 1) ** 1.1 + 0.22 * h * np.exp(-(q / 0.3) ** 2)
        else:
            z = h * np.clip(1 - rr * rr, 0, 1) ** 1.2
        return z, rr

    def bump_at(px, py):
        bump = np.zeros(np.shape(px), dtype=float)
        for (hx, hy), sg, hh in zip(hum_c, hum_s, hum_h):
            bump = bump + hh * np.exp(-(((px - hx) ** 2 + (py - hy) ** 2) / (2 * sg * sg)))
        return bump

    def surf_z(px, py):
        px = np.asarray(px, float)
        py = np.asarray(py, float)
        z, rr = base_z(px, py)
        bump = bump_at(px, py)
        fine = col.value_noise2(px * 18.0, py * 18.0, seed + 3, 1.0) - 0.5
        edge = np.clip((rr - 0.86) / 0.14, 0, 1)
        return z + (bump + 0.010 * fine) * (1 - edge) - 0.015 * edge ** 1.5

    V = [np.array([cx, cy, float(surf_z(np.array([cx]), np.array([cy]))[0])])]
    ring_idx = []
    th = np.linspace(0, 2 * np.pi, ns, endpoint=False)
    wob = 1.0 + 0.05 * np.sin(3 * th + seed % 7) + 0.035 * np.sin(5 * th + seed % 11) + 0.02 * np.sin(9 * th + seed % 5)
    for i in range(1, nr + 1):
        r = (i / nr) ** 0.9
        x = cx + rx * r * wob * np.cos(th)
        y = cy + ry * r * wob * np.sin(th)
        z = surf_z(x, y)
        ring_idx.append(list(range(len(V), len(V) + ns)))
        V.extend(np.stack([x, y, z], 1))
    bot = len(V)
    V.append(np.array([cx, cy, -0.08]))
    V = np.array(V)

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
    # ---- stones: (A-C) one grey boulder by the trunk's front flank (all three sheet mounds show one), 3 medium
    # stones half sunk in the moss, 10 pebbles near the rim; (D) stones round the rock's foot
    stones = []
    specs_st = []
    if tree:
        bs = float(np.clip(0.22 * rx / 0.9, 0.14, 0.28))     # v2f: the sheet's mound boulder is ~0.3-0.5 m
        a0 = -np.pi / 2 + rng.uniform(0.25, 0.6)
        specs_st.append((a0, rng.uniform(0.18, 0.28), (bs, bs * 0.8, bs * 0.66), 0.10, 4))
        # v2f: more half-sunk rocks through the moss (the sheet's mounds show 3-6 rocks of 5-20 cm, a gravel rim)
        for _ in range(5):
            sz = rng.uniform(0.05, 0.11)
            specs_st.append((rng.uniform(0, 2 * np.pi), rng.uniform(0.30, 0.8),
                             (sz, sz * rng.uniform(0.7, 0.95), sz * rng.uniform(0.5, 0.7)), 0.35, 3))
        for _ in range(22):
            ps = rng.uniform(0.02, 0.045)
            specs_st.append((rng.uniform(0, 2 * np.pi), rng.uniform(0.78, 0.95), (ps, ps * 0.8, ps * 0.55), 0.3, 2))
    else:
        # rock stage: small same-rock debris half sunk in the moss (t2: 6-20 cm stones read as a ring of boulders)
        for _ in range(7):
            sz = rng.uniform(0.035, 0.10)
            specs_st.append((rng.uniform(0, 2 * np.pi), rng.uniform(0.80, 0.95),
                             (sz, sz * rng.uniform(0.7, 1.0), sz * rng.uniform(0.45, 0.7)), 0.45, 3))
    n_st = len(specs_st)
    for (a, rr, rad, sink, chips) in specs_st:
        px, py = cx + rx * rr * np.cos(a), cy + ry * rr * np.sin(a)
        pz = float(base_z(np.array([px]), np.array([py]))[0][0])
        P = _lobe_points((px, py, pz), rad, rng, level=2, bump=0.1, n_chips=chips)
        P[:, 2] -= sink * rad[2] * 2
        stones.append(convex_hull_mesh(P))
    st_uv, _, _ = mass_uvs(stones)
    # ---- tufts (s9): the sheet's base shows a small round leafy shrub by the trunk, low fern sprays and short
    # grass sprigs among the moss; s8's 12-22 cm lawn blades read as meadow grass
    kinds = [fol.make_clump(np.random.default_rng(seed + 1), n_blades=22, height=(0.035, 0.08), width=0.004,
                            spread=0.05),
             fol.make_clump(np.random.default_rng(seed + 2), n_blades=16, height=(0.06, 0.12), width=0.016,
                            spread=0.05),           # fern-like: few broad arching fronds
             fol.make_clump(np.random.default_rng(seed + 3), n_blades=90, height=(0.10, 0.24), width=0.013,
                            spread=0.09)]
    kinds += rosmod.library(0.75)[:3]          # s10: the leafy shrub = a ball of small needle rosettes
    # s11: moss cushions: many tiny dense clumps (1.5-3.5 cm) give the sheet's lumpy, bright-tipped moss texture
    # v2f: denser moss cushions (40 blades, 2-4.5 cm), set on the cushion tops of the ground shape
    kinds.append(fol.make_clump(np.random.default_rng(seed + 4), n_blades=18, height=(0.012, 0.028), width=0.010,
                                spread=0.03))             # (final-2: 40 blades x 520 clumps = 104k tris on C's mound)            # final-1: 2-9 cm tufts read as a lawn; 1-3 cm cushions
    # v2f: real fern sprays (index 7, 8): the sheet's mounds and the rock foot carry ferns, not only grass
    kinds.append(fol.make_fern(np.random.default_rng(seed + 5), n_fronds=7, length=(0.12, 0.22)))
    kinds.append(fol.make_fern(np.random.default_rng(seed + 6), n_fronds=9, length=(0.18, 0.30), pairs=13))
    tips = []
    if tree:
        n_t = int(np.clip(round(14 * rx * ry), 12, 30))
        for k in range(n_t):
            a = rng.uniform(0, 2 * np.pi)
            rr = np.sqrt(rng.uniform(0.04, 0.75))
            px, py = cx + rx * rr * np.cos(a), cy + ry * rr * np.sin(a)
            pz = float(surf_z(np.array([px]), np.array([py]))[0]) - 0.01
            # final-1 model sheet: the ferns read as grass at tree distance; bigger fern sprays, fewer grass tufts
            vk = int(rng.choice([7, 7, 8, 8, 1]))           # final-1: the grass tufts read as a lawn
            tips.append({"p": np.array([px, py, pz]), "d": np.array([0, 0, 1.0]), "pad": 0,
                         "variant": vk, "scale": rng.uniform(1.4, 2.0) if vk >= 7 else rng.uniform(0.8, 1.2)})
        n_moss = int(np.clip(300 * rx * ry, 100, 360))
        for k in range(n_moss):
            if k < len(hum_c):
                px, py = hum_c[k] + rng.normal(0, 0.3 * hum_s[k], 2)
            else:
                a = rng.uniform(0, 2 * np.pi)
                rr = np.sqrt(rng.uniform(0.0, 0.8))
                px, py = cx + rx * rr * np.cos(a), cy + ry * rr * np.sin(a)
            pz = float(surf_z(np.array([px]), np.array([py]))[0]) - 0.004
            tips.append({"p": np.array([px, py, pz]), "d": np.array([0, 0, 1.0]), "pad": 0, "variant": 6,
                         "scale": rng.uniform(0.8, 1.4)})
        # one shrub on the trunk's right-front, beside the boulder (P1F, P2F, P3F all show it)
        a = -np.pi / 2 + rng.uniform(0.7, 1.0)
        px, py = cx + rx * 0.22 * np.cos(a), cy + ry * 0.22 * np.sin(a)
        pz = float(surf_z(np.array([px]), np.array([py]))[0]) - 0.02
        sh = float(np.clip(rx / 0.9, 0.8, 1.3))
        for k in range(11):
            u = rng.normal(0, 1, 3)
            u[2] = abs(u[2]) + 0.4
            u /= np.linalg.norm(u)
            q = np.array([px, py, pz + 0.08 * sh]) + u * 0.09 * sh
            tips.append({"p": q, "d": u, "pad": 0, "variant": 3 + k % 3, "scale": 0.8 * sh})
    else:
        n_t = 72
        for k in range(n_t):
            a = rng.uniform(0, 2 * np.pi)
            rr = rng.uniform(0.74, 0.95)
            px, py = cx + rx * rr * np.cos(a), cy + ry * rr * np.sin(a)
            pz = float(surf_z(np.array([px]), np.array([py]))[0]) - 0.01
            # v2f (judge delta 1, P4F/P4Q bottom edge): a skirt of ferns and small shrubs round the rock's foot
            vk = int(rng.choice([0, 7, 7, 8, 8, 8, 3, 4]))
            tips.append({"p": np.array([px, py, pz]), "d": np.array([0, 0, 1.0]), "pad": 0,
                         "variant": vk, "scale": rng.uniform(1.6, 2.3) if vk >= 7 else rng.uniform(0.9, 1.3)})
        # rock stage: the sheet's rock foot sits in moss cushions (P4F/P4S/P4Q), not on bare soil
        for k in range(170):
            a = rng.uniform(0, 2 * np.pi)
            rr = rng.uniform(0.70, 0.92)
            px, py = cx + rx * rr * np.cos(a), cy + ry * rr * np.sin(a)
            pz = float(surf_z(np.array([px]), np.array([py]))[0]) - 0.004
            tips.append({"p": np.array([px, py, pz]), "d": np.array([0, 0, 1.0]), "pad": 0, "variant": 6,
                         "scale": rng.uniform(0.7, 1.3)})
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
    # v2f: vertex colour R = moss cushion (0 in the gaps between cushions .. 1 on a cushion top), so the moss reads
    # LUMPY with dark gaps and bright yellow-green tops like the sheet's mounds (l7/l8 lab: a flat blotchy felt).
    # Unreal: the mound MI lerps the moss colour by VertexColor.R. Stones and tufts carry 1 (neutral).
    bm_ = bump_at(V[:, 0], V[:, 1])
    cz = np.clip(bm_ / max(float(np.percentile(bm_[:bot], 90)), 1e-4), 0, 1) ** 0.8
    cz = np.clip(0.15 + 0.85 * cz + 0.25 * (col.value_noise2(V[:, 0] * 25, V[:, 1] * 25, seed + 12, 1.0) - 0.5), 0, 1)
    vcol = np.ones((len(allV), 4), np.float32)
    vcol[:len(V), 0] = cz
    obj = meshio.make_mesh(name, allV, faces, {"UVMap": uv0, "UV1": uv1}, colour=vcol, smooth=True, collection=coll)
    me = obj.data
    for m_ in (mound_moss_material(), soil_material(), rock_material(), groundcover_material()):
        me.materials.append(m_)

    def soil_mask(fc):
        rr = np.sqrt(((fc[:, 0] - cx) / rx) ** 2 + ((fc[:, 1] - cy) / ry) ** 2)
        nz = col.value_noise2(fc[:, 0] * 3, fc[:, 1] * 3, seed + 9, 1.0)
        # s9: a ragged soil and gravel band at the foot, bare patches on the lower flank (the sheet: brown soil and
        # grit show between the moss cushions toward the edge)
        nz2 = col.value_noise2(fc[:, 0] * 7, fc[:, 1] * 7, seed + 10, 1.0)
        if not tree:                     # rock stage: the D apron is moss to the rim, a ragged soil edge only
            return rr > 0.90 + 0.06 * nz2
        return (rr > 0.90 + 0.05 * nz2) | ((nz < 0.22) & (rr > 0.65))       # v2f: thinner rim band
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
    rock_extra = None
    if "rock" in spec:
        # v3 (stone study 4.9 / 8.3): SDF lobes, unique UVs and bakes; the tree was moved onto it in make_spec
        rock_obj, rock_info, rock_extra = rock_v3.build_rock_v3(vname, coll, TEX, BUILD / "tex", rock_v3_materials,
                                                                ao_samples=max(32, a.samples))
        rock_obj["uv0_tile_extent"] = 1.0
        z_before = float(spec["trunk"]["pts"][0][2])
        seat_trunk_on_rock(rock_obj, spec)
        rock_info["trunk_base_z_spec"] = z_before
        rock_info["rock_surface_under_base"] = spec["trunk"].get("rock_surface_z")
        spec["roots"] = grow_rock_roots_v3(rock_obj, rock_extra, spec, rng)
        rock_info["roots_primary"] = sum(1 for r_ in spec["roots"] if "parent_root" not in r_)
        rock_info["roots_forks"] = sum(1 for r_ in spec["roots"] if "parent_root" in r_)
    sk = treegen.build_skeleton_separated(spec, rng)        # v2f: limbs kept apart (fork close-up)
    # v2: the spec profile already carries the sheet's girth and root swell; the tube flare only adds the
    # nebari foot (short decay), buttress lobes and a twist (C: massive and twisted)
    params = tubes.TubeParams(tile_m=TILE_M, plate_spacing=0.030 if pine == 3 else 0.022,
                              ring_len=0.030 if pine == 3 else 0.022, plate_min_r=0.05,
                              flare_amp=0.12 if pine == 4 else 0.22, flare_len=0.35 if pine == 4 else 0.6,
                              buttress=0.10 if pine == 4 else 0.16, twist=1.3 if pine in (3, 4) else 0.5,
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
    # s13: pine C (4.5 m, pads to 1.8 m wide) uses 6 % longer needles (7.5-11.9 cm with the instance scale, G9)
    tufts = rosmod.library(float(spec.get("rosette_pad", {}).get("ros_scale", 1.0)))
    n_b = len(tufts)
    # v2f: pad-top sites (kind 0) get the star units, rim / flank / under-rim sites the upright brushes
    ns = rosmod.N_STAR
    # l11 pad-side: an even row of same-size rim brushes read as a comb; half the rim sites take a star, and every
    # rosette gets an extra 1.0-1.04 size (final-1: 3 of 4 rim sites take a star, the brushes read as grass) (x the 0.88-1.12 instance scale; needles stay 7-12 cm, G9)
    tips = [dict(t, variant=int(rng.integers(ns)) if (int(t.get("kind", 0)) == 0 or rng.random() < 0.75)
                 else int(rng.integers(ns, n_b)), scale=float(rng.uniform(1.0, 1.04)))
            for t in sk["tips"]]
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
        # v3: one hull per lobe (the lobes are convex before the union: study 4.9.2 step 9); no traversal marker
        for k, Vl in enumerate(rock_extra["lobe_V"]):
            ucx_from_points(rock_obj, Vl, k)
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
    info["needle_len_cm"] = [round(100 * 0.88 * min(lens), 2), round(100 * 1.12 * 1.04 * max(lens), 2)]   # x instance scale 0.88-1.12 x v2f extra 1.0-1.04
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
