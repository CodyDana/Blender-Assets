"""Kit 6, taiko set (SEPARATE from the pavilion): drum, stand and one drumstick mesh (placed twice), in Taiko.blend.

Reference: References/Dojo/dojo_drum_pavilion_ref.png (drum close-up panels, bottom right). Sizes: the prompt's
"about 1.2 m across" wins over the sheet; the sheet's proportions are measured (BUILD_NOTES.md, stage BUILD).

Pieces (each its own collection, mesh, UCX and FBX with LOD0-2; real-world metres):
  SM_DKP_Taiko_Drum   pivot at the drum centre; drum axis along local X; ring handles on +-Y
  SM_DKP_Taiko_Stand  pivot at the base centre on the ground; the drum axis runs along local X
  SM_DKP_Taiko_Stick  pivot at the grip end on the stick axis; the stick runs along local +X

Fix round f1 (2026-09-27): LOD0-2 on every piece (pipeline decimate_lods + make_lod_group, UCX_<base>_LOD0_NN);
tacks cut to 30 triangles each (110 per head, jittered, 12 % bigger, zig-zag +-16 mm); lathe UV seam moved to the
underside (-Z) and the wrap made a whole number of tiles; hide collar with its own strip texture, an irregular
torn and lifted edge and folds; rounded lip; rings hang flat against the bulge (1.3x thicker); stand darker with
end-grain faces, heavier sills, kusabi wedge blocks without top pegs, iron L-straps wrapping the rail ends with
round rivets; UCX covers the saddle shoulders; thicker flat-ended sticks leaning at the front-right end, solved
against the real meshes (BVH) with the feet grounded to 0.5 mm.

Writes: Assets/Dojo/Taiko.blend (collections Taiko_Drum, Taiko_Stand, Taiko_Stick, Taiko_Layout),
Exports/DojoKit/Props/taiko/SM_DKP_Taiko_*.fbx (through Scripts/pipeline), and in
WorkFiles/dojo/build/props/taiko/: layout_taiko.json, measure.json, qa_report.json, export_report.json.

Run: blender -b --factory-startup --python Scripts/dojo/props/taiko/build_taiko.py -- [--no-export]
"""
import json
import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "Scripts"))
sys.path.insert(0, str(HERE))
from pipeline.export_fbx import export_fbx  # noqa: E402
from pipeline.qa_check import qa_check  # noqa: E402
from pipeline.lock import assert_owner  # noqa: E402
from pipeline.helpers import decimate_lods, make_lod_group  # noqa: E402
import taiko_uv as UVL  # noqa: E402
sys.path.insert(0, str(ROOT / "Scripts" / "dojo" / "materials"))
import dojo_materials as djm  # noqa: E402  (the shared dojo material library, r2)

EXPORT_DIR = ROOT / "Exports" / "DojoKit" / "Props" / "taiko"
TEX = EXPORT_DIR / "Textures"
WORK = ROOT / "WorkFiles" / "dojo" / "build" / "props" / "taiko"
BLEND = ROOT / "Assets" / "Dojo" / "Taiko.blend"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

# --------------------------------------------------------------------------- dimensions (metres)
# Sheet (front elevation, 112.8 px/m from the 1.8 m silhouette): drum 1.04 m tall, 1.34-1.45 m long, bottom 0.57 m
# above the plinth. Prompt: "about 1.2 m across" -> scale the sheet by 1.2 / 1.04 = 1.154.
R_BELLY = 0.600          # 1.20 m across the belly (prompt)
R_BODY_END = 0.548       # body radius at |x| = 0.70 (sheet: ends about 0.92 of the belly)
X_BODY = 0.70
X_COLLAR = UVL.X_COLLAR  # mean x of the torn collar edge
COLLAR_T = 0.0045        # hide thickness over the body
LIP_XC, LIP_RC, LIP_RHO = 0.758, 0.528, 0.019   # rolled lip: circle centre (x, r) and radius in the profile plane
X_FACE = 0.771           # the flat head face (recessed about 6 mm inside the lip's crown at x = 0.777)
R_FACE = 0.505           # the flat face's edge radius (then the lip rolls out to its crown)
N_TACKS = 128            # per head (r2: 110 -> 128, the judges: denser, nearly touching, doubled in places)
X_TACK, TACK_ZZ = 0.676, 0.0155  # zig-zag centre and half-offset along the axis
TACK_R, TACK_H = 0.0213, 0.0162  # dome base radius / height (f1: +12 %)
DRUM_Z = 1.25            # drum centre above the stand base
SIDES = 144              # r2: 96 -> 144 columns, so the torn collar edge can tear in narrow notches
RING_R, RING_T = 0.074, 0.0124   # ring handle: centre-line radius and tube radius (f1: tube 1.3x)

POST_X, POST_Y, POST_W = 0.56, 0.48, 0.18      # post centres (+-), section (f1: 0.16 -> 0.18, heavier)
SILL_W, SILL_H, SILL_Y = 0.22, 0.18, 0.72      # foot sills along Y (f1: 0.18 x 0.15 -> 0.22 x 0.18)
RAIL_W, RAIL_X = 0.13, 0.76                    # long rails along X, protruding past the posts
RAIL_LO, RAIL_HI = (0.19, 0.34), (0.47, 0.62)
CRADLE_X0, CRADLE_X1 = 0.46, 0.58
CRADLE_BOTTOM, CRADLE_FLAT_Y = 0.52, 0.40
CRADLE_Y = 0.69                                # outer end of the cradle beam's wedge block
SADDLE_GAP = 0.003
RAIL_IRON_T = 0.006                            # r2: rail-end iron wrap thickness

STICK_L, STICK_R_GRIP, STICK_R_TIP = UVL.STICK_L, 0.040, 0.046   # r3: 13 % taper toward the grip (judge: 10-15 %)
STICK_EDGE = 0.008       # (f1/r2 flat-end round-over; r3 ends are domes, see STICK_DOME)
STICK_DOME = (0.62, 2.4)  # r3: dome height / end radius, superellipse exponent (a full round dome, soft shoulder)
RAIL_Y_OUT = (POST_W - RAIL_W) / 2   # r3: rails lap flush on the posts' outer faces (the sheet's joint close-up)
PLATE_T = 0.004                      # r3: flat iron strap plate thickness

# --------------------------------------------------------------------------- materials

# r2 (2026-09-28): the shared dojo library for timber, end grain and iron (M_DJ_*, UVs in library tile units);
# the three taiko-only surfaces (lacquer, hide, collar) are built on the library's own node graph (make_material:
# the DJ_Wear_v1 vertex-colour weathering, the same Unreal recipe M_DJ_Lib_Opaque) with the taiko's own maps.
LAC, HIDE, COLLAR, TIM, TIMEND, STK, IRN = (
    "M_DKP_Taiko_Lacquer", "M_DKP_Taiko_Hide", "M_DKP_Taiko_HideCollar", "M_DJ_TimberDark",
    "M_DJ_TimberDarkEnd", "M_DJ_TimberAged", "M_DJ_Iron")
# name: (texture set, params)
MATERIALS = {
    LAC: ("Lacquer", {"kind": "UNIQUE hero lacquer on the library graph (M_DJ_Lib_Opaque, UseWear on, TileM 2,2)",
                      "finish": "satin (roughness ~0.5), no clear coat"}),
    HIDE: ("Hide", {"kind": "UNIQUE on the library graph (UseWear on)"}),
    COLLAR: ("Collar", {"kind": "UNIQUE strip on the library graph (UseWear on)"}),
    TIM: ("LIBRARY TimberDark", {"kind": "shared library: MI_DJ_TimberDark"}),
    TIMEND: ("LIBRARY TimberDarkEnd", {"kind": "shared library: MI_DJ_TimberDarkEnd"}),
    IRN: ("LIBRARY Iron", {"kind": "shared library: MI_DJ_Iron"}),
}
TILE = {TIM: djm.set_info("TimberDark")["tile_m"][0], TIMEND: djm.set_info("TimberDarkEnd")["tile_m"][0],
        IRN: djm.set_info("Iron")["tile_m"][0], STK: djm.set_info("TimberAged")["tile_m"][0]}
OWN = {LAC: "Lacquer", HIDE: "Hide", COLLAR: "Collar"}


def build_material(name):
    if name.startswith("M_DJ_"):
        return djm.make_material(name, uv_map="UV0")
    # a taiko-only surface on the library graph: register it with the library's 2 m Lacquer tile (the wear mask
    # scale), build the library node tree, then point its three maps at the taiko's own set
    djm.MATERIALS[name] = dict(set="Lacquer", kind="opaque", wear=True, normal_strength=1.0)
    mat = djm.make_material(name, rebuild=True, uv_map="UV0")
    for n in mat.node_tree.nodes:
        if n.type == "TEX_IMAGE" and n.image and n.image.name.startswith("T_DJ_Lacquer_"):
            sfx = n.image.name.split("_")[-1].split(".")[0]
            img = bpy.data.images.load(str(TEX / f"T_DKP_Taiko_{OWN[name]}_{sfx}.png"), check_existing=True)
            img.colorspace_settings.name = "sRGB" if sfx == "BC" else "Non-Color"
            n.image = img
    mat["dj_set"] = "Lacquer"          # wear-mask tile only; the maps are T_DKP_Taiko_<set>
    mat["taiko_set"] = OWN[name]
    return mat


def build_material_f1(name):
    """f1 material builder (retired in r2, kept for the record)."""
    tex, _p = MATERIALS[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")

    def img(suffix, noncolor):
        node = nt.nodes.new("ShaderNodeTexImage")
        image = bpy.data.images.load(str(TEX / f"T_DKP_Taiko_{tex}_{suffix}.png"), check_existing=True)
        if noncolor:
            image.colorspace_settings.name = "Non-Color"
        node.image = image
        return node
    bc, orm, nrm = img("BC", False), img("ORM", True), img("N", True)
    nt.links.new(bc.outputs["Color"], bsdf.inputs["Base Color"])
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(orm.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
    nt.links.new(sep.outputs[2], bsdf.inputs["Metallic"])
    # the maps are DirectX (UE); flip green back to OpenGL for Blender's review renders
    sep_n = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(nrm.outputs["Color"], sep_n.inputs["Color"])
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    nt.links.new(sep_n.outputs[1], inv.inputs[1])
    comb = nt.nodes.new("ShaderNodeCombineColor")
    nt.links.new(sep_n.outputs[0], comb.inputs[0])
    nt.links.new(inv.outputs[0], comb.inputs[1])
    nt.links.new(sep_n.outputs[2], comb.inputs[2])
    nmap = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(comb.outputs["Color"], nmap.inputs["Color"])
    nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


# --------------------------------------------------------------------------- geometry builder

class Part:
    """Collects closed sub-meshes (verts, faces, per-face loop UVs, per-face materials, smooth flags) for one SM_."""

    def __init__(self, name):
        self.name = name
        self.chunks = []
        self.ucx = []

    def add(self, verts, faces, uvs, mats, smooth=False, M=None):
        if isinstance(mats, str):
            mats = [mats] * len(faces)
        if M is not None:
            verts = [tuple(M @ Vector(v)) for v in verts]
        self.chunks.append((verts, faces, uvs, mats, smooth))
        return self

    def hull(self, points):
        self.ucx.append(points)
        return self

    def build(self, coll):
        mats = []
        bm = bmesh.new()
        uvl = bm.loops.layers.uv.new("UV0")
        for verts, faces, uvs, fmats, smooth in self.chunks:
            vs = [bm.verts.new(v) for v in verts]
            for f_idx, fu, m in zip(faces, uvs, fmats):
                if m not in mats:
                    mats.append(m)
                f = bm.faces.new([vs[i] for i in f_idx])
                f.material_index = mats.index(m)
                f.smooth = smooth
                for loop, uv in zip(f.loops, fu):
                    loop[uvl].uv = uv
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        mesh = bpy.data.meshes.new(self.name)
        bm.to_mesh(mesh)
        bm.free()
        for m in mats:
            mesh.materials.append(bpy.data.materials[m])
        obj = bpy.data.objects.new(self.name, mesh)
        coll.objects.link(obj)
        add_uv1(obj)
        for i, pts in enumerate(self.ucx):
            hm = bpy.data.meshes.new(f"UCX_{self.name}_{i:02d}")
            hb = bmesh.new()
            hv = [hb.verts.new(p) for p in pts]
            bmesh.ops.convex_hull(hb, input=hv)
            loose = [v for v in hb.verts if not v.link_faces]
            if loose:
                bmesh.ops.delete(hb, geom=loose, context="VERTS")
            bmesh.ops.recalc_face_normals(hb, faces=hb.faces[:])
            hb.to_mesh(hm)
            hb.free()
            h = bpy.data.objects.new(hm.name, hm)
            coll.objects.link(h)
            h.parent = obj
            h.hide_render = True
            h.display_type = "WIRE"
        return obj


def add_uv1(obj):
    """UV1 lightmap channel (Fab rule): Blender's lightmap pack, never overlapping, inside 0-1."""
    me = obj.data
    me.uv_layers.new(name="UV1")
    me.uv_layers.active_index = 1
    with bpy.context.temp_override(active_object=obj, object=obj, selected_objects=[obj],
                                   selected_editable_objects=[obj]):
        bpy.ops.uv.lightmap_pack(PREF_CONTEXT="ALL_FACES", PREF_PACK_IN_ONE=False, PREF_NEW_UVLAYER=False,
                                 PREF_BOX_DIV=12, PREF_MARGIN_DIV=0.3)
    me.uv_layers.active_index = 0


_JIT = [0]


def cbox(x0, x1, y0, y1, z0, z1, mat, grain="x", c=0.008, uvoff=(0.0, 0.0), end_mat=None, rough=0.0, seed=0):
    """A chamfered box (worn timber edge) as (verts, faces, uvs, mats). Planar tiling UV per face: U along the grain
    axis when it lies in the face plane, else along the face's longer side. end_mat: the material of the two faces
    across the grain (end grain, f1), mapped with its own tile. rough: per-corner random offset (m), which keeps each
    corner's three chamfer vertices together, for the rough kusabi wedges. A tiny unique growth per box keeps abutting
    boxes from sharing coincident vertices (the armory rule)."""
    _JIT[0] += 1
    g = 0.0002 + (_JIT[0] % 211) * 3e-6
    x0, x1, y0, y1, z0, z1 = x0 - g, x1 + g, y0 - g, y1 + g, z0 - g, z1 + g
    lo, hi = (x0, y0, z0), (x1, y1, z1)
    c = min(c, (x1 - x0) / 3, (y1 - y0) / 3, (z1 - z0) / 3)
    rng = random.Random(seed or _JIT[0])
    verts, idx = [], {}
    for sx in (0, 1):
        for sy in (0, 1):
            for sz in (0, 1):
                p = [hi[0] if sx else lo[0], hi[1] if sy else lo[1], hi[2] if sz else lo[2]]
                off = [rng.uniform(-rough, rough) for _ in range(3)]
                inset = [(-c if s else c) for s in (sx, sy, sz)]
                for ax in range(3):
                    q = [p[o] + off[o] for o in range(3)]
                    for o in range(3):
                        if o != ax:
                            q[o] += inset[o]
                    idx[(sx, sy, sz, ax)] = len(verts)
                    verts.append(tuple(q))
    faces, fax = [], []
    for ax in range(3):   # main faces
        o1, o2 = [a for a in range(3) if a != ax]
        for s in (0, 1):
            ring = []
            for a, b in ((0, 0), (1, 0), (1, 1), (0, 1)):
                k = [0, 0, 0]
                k[ax], k[o1], k[o2] = s, a, b
                ring.append(idx[(k[0], k[1], k[2], ax)])
            faces.append(tuple(ring))
            fax.append(ax)
    for ax in range(3):   # edge chamfers along axis ax
        o1, o2 = [a for a in range(3) if a != ax]
        for a in (0, 1):
            for b in (0, 1):
                k0 = [0, 0, 0]
                k0[o1], k0[o2] = a, b
                k1 = list(k0)
                k1[ax] = 1
                faces.append((idx[(*k0, o1)], idx[(*k1, o1)], idx[(*k1, o2)], idx[(*k0, o2)]))
                fax.append(-1)
    for sx in (0, 1):     # corner triangles
        for sy in (0, 1):
            for sz in (0, 1):
                faces.append((idx[(sx, sy, sz, 0)], idx[(sx, sy, sz, 1)], idx[(sx, sy, sz, 2)]))
                fax.append(-1)
    gi = "xyz".index(grain)
    ext = [x1 - x0, y1 - y0, z1 - z0]
    uvs, mats = [], []
    for f, a in zip(faces, fax):
        pts = [Vector(verts[i]) for i in f]
        n = (pts[1] - pts[0]).cross(pts[2] - pts[0])
        nax = max(range(3), key=lambda q: abs(n[q]))
        plane = [q for q in range(3) if q != nax]
        is_end = end_mat is not None and a == gi
        m = end_mat if is_end else mat
        tile = TILE[m]
        ua = gi if gi in plane else max(plane, key=lambda q: ext[q])
        va = [q for q in plane if q != ua][0]
        off = (uvoff[0] * 1.7 % 1.0, uvoff[1] * 2.3 % 1.0) if is_end else uvoff
        uvs.append(wrap_uv([(p[ua] / tile + off[0], p[va] / tile + off[1]) for p in pts]))
        mats.append(m)
    return verts, faces, uvs, mats


def pbox(x0, x1, y0, y1, z0, z1, mat=None, uvoff=(0.0, 0.0)):
    """A plain 6-quad box (iron straps: no chamfer, 12 triangles)."""
    mat = mat or IRN
    _JIT[0] += 1
    g = 0.0001 + (_JIT[0] % 97) * 2e-6
    x0, x1, y0, y1, z0, z1 = x0 - g, x1 + g, y0 - g, y1 + g, z0 - g, z1 + g
    verts = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    tile = TILE[mat]
    uvs = []
    for f in faces:
        pts = [Vector(verts[i]) for i in f]
        n = (pts[1] - pts[0]).cross(pts[2] - pts[0])
        nax = max(range(3), key=lambda q: abs(n[q]))
        a, b = [q for q in range(3) if q != nax]
        uvs.append(wrap_uv([(p[a] / tile + uvoff[0], p[b] / tile + uvoff[1]) for p in pts]))
    return verts, faces, uvs, [mat] * len(faces)


def wrap_uv(face_uv):
    """Shift one face's UVs by whole tiles so its minimum lies in 0..1 (tiling texture: the look is unchanged)."""
    du = math.floor(min(u for u, _v in face_uv))
    dv = math.floor(min(v for _u, v in face_uv))
    return [(u - du, v - dv) for u, v in face_uv]


def lathe(rings, sides, phase, seg_mat, uv_fn, ragged=None):
    """Surface of revolution about X. rings = [(x, r)], r == 0 gives a pole. ragged(k, i) -> (dx, dr) for ring k at
    column i. The angle of column i is 2 pi i / sides + phase, so column 0 (the UV seam) sits at `phase`.
    uv_fn(seg, k, col, pos) -> (u, v) for the corner of segment seg on ring k at the unwrapped column col (0..sides)
    and vertex position pos."""
    verts, vid = [], []
    for k, (x, r) in enumerate(rings):
        if r == 0:
            verts.append((x, 0.0, 0.0))
            vid.append([len(verts) - 1] * sides)
            continue
        row = []
        for i in range(sides):
            th = 2 * math.pi * i / sides + phase
            dx, dr = ragged(k, i) if ragged else (0.0, 0.0)
            verts.append((x + dx, (r + dr) * math.cos(th), (r + dr) * math.sin(th)))
            row.append(len(verts) - 1)
        vid.append(row)
    faces, uvs, mats = [], [], []
    for k in range(len(rings) - 1):
        a, b = vid[k], vid[k + 1]
        for i in range(sides):
            j = (i + 1) % sides
            corners = [(k, a[i], i), (k, a[j], i + 1), (k + 1, b[j], i + 1), (k + 1, b[i], i)]
            if rings[k][1] == 0:
                corners = [corners[0], corners[2], corners[3]]
            elif rings[k + 1][1] == 0:
                corners = [corners[0], corners[1], corners[3]]
            faces.append(tuple(c[1] for c in corners))
            uvs.append([uv_fn(k, kk, col, verts[vi]) for kk, vi, col in corners])
            mats.append(seg_mat[k])
    return verts, faces, uvs, mats


def lathe_z(profile, sides, mat, tile=2.0, uoff=(0.37, 0.61)):
    """Small surface of revolution about local Z (tacks, rivets, the boss). profile = [(r, z), ...]; open at the
    bottom when the last ring is not a pole (it sits sunk into the surface below)."""
    verts, rings = [], []
    for (r, z) in profile:
        if r == 0:
            verts.append((0.0, 0.0, z))
            rings.append([len(verts) - 1] * sides)
        else:
            rings.append([len(verts) + i for i in range(sides)])
            for i in range(sides):
                a = 2 * math.pi * (i + 0.5) / sides
                verts.append((r * math.cos(a), r * math.sin(a), z))
    faces, uvs = [], []
    for k in range(len(profile) - 1):
        a, b = rings[k], rings[k + 1]
        for i in range(sides):
            j = (i + 1) % sides
            pu = lambda vi: (verts[vi][0] / tile + uoff[0], verts[vi][1] / tile + uoff[1] + verts[vi][2] / tile)  # noqa
            if profile[k][0] == 0:
                faces.append((a[i], b[j], b[i]))
            elif profile[k + 1][0] == 0:
                faces.append((a[i], a[j], b[i]))
            else:
                faces.append((a[i], a[j], b[j], b[i]))
            uvs.append([pu(v) for v in faces[-1]])
    return verts, faces, uvs, [mat] * len(faces)


def torus(R, r, nu, nv, mat, tile=2.0):
    """Torus about local Z (ring in the XY plane). UV: U along the ring, V around the tube."""
    verts = []
    for i in range(nu):
        a = 2 * math.pi * i / nu
        for j in range(nv):
            b = 2 * math.pi * j / nv
            rr = R + r * math.cos(b)
            verts.append((rr * math.cos(a), rr * math.sin(a), r * math.sin(b)))
    faces, uvs = [], []
    for i in range(nu):
        for j in range(nv):
            i2, j2 = (i + 1) % nu, (j + 1) % nv
            faces.append((i * nv + j, i2 * nv + j, i2 * nv + j2, i * nv + j2))
            uvs.append([(R * 2 * math.pi * ii / nu / tile, r * 2 * math.pi * jj / nv / tile)
                        for ii, jj in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))])
    return verts, faces, uvs, [mat] * len(faces)


def frame(origin, t, d, n):
    """Matrix with local X = t, Y = d, Z = n at origin (all unit, orthogonal)."""
    M = Matrix.Identity(4)
    for row in range(3):
        M[row][0], M[row][1], M[row][2], M[row][3] = t[row], d[row], n[row], origin[row]
    return M


# Round domed heads (f1: the joint close-up's round-headed nails and rivets; 6 sides, 18 triangles, open base)
def dome(r, h, sides=6):
    return lathe_z([(0.0, h), (0.70 * r, 0.72 * h), (r, -0.0015)], sides, IRN)


# --------------------------------------------------------------------------- the drum

def body_r(x):
    return R_BELLY - (R_BELLY - R_BODY_END) * (x / X_BODY) ** 2


def harmonics(seed, kmin, kmax, amp, power=0.8):
    """A random periodic function of the angle: sum of harmonics kmin..kmax with 1/k^power amplitudes, scaled to
    peak `amp` over the SIDES columns. Returns a list of SIDES values."""
    rng = random.Random(seed)
    terms = [(k, rng.uniform(0, 2 * math.pi), rng.uniform(0.5, 1.0) / k ** power) for k in range(kmin, kmax + 1)]
    vals = [sum(a * math.sin(k * 2 * math.pi * i / SIDES + ph) for k, ph, a in terms) for i in range(SIDES)]
    m = max(abs(v) for v in vals)
    return [amp * v / m for v in vals]


# per head (s = +1 / -1): torn edge offset along the axis, lap-edge lift, collar folds
RAG = {}
for _s in (1, -1):
    _rng = random.Random(77 + _s)
    base = harmonics(100 + _s, 2, 60, 0.012)
    jit = [_rng.uniform(-0.003, 0.003) for _ in range(SIDES)]
    # r2 (judges: torn, irregular): 9 torn-back notches (V tears 2-4 columns wide, 8-14 mm deep) and 4 small
    # proud tabs per head
    for _ in range(9):
        c0 = _rng.randrange(SIDES)
        depth = _rng.uniform(0.008, 0.014)
        half = _rng.choice((1, 1, 2))
        for d_ in range(-half, half + 1):
            jit[(c0 + d_) % SIDES] += depth * (1.0 - abs(d_) / (half + 1))
    for _ in range(4):
        c0 = _rng.randrange(SIDES)
        jit[c0 % SIDES] -= _rng.uniform(0.004, 0.007)
    lift_h = harmonics(200 + _s, 3, 40, 0.0020)
    RAG[_s] = {"dx": [b + j for b, j in zip(base, jit)],
               # r2 (judges: "slightly lifted"): the lap edge stands 1.5-5.5 mm proud, curling up in places
               "lift": [0.0035 + v + (0.0015 if j > 0.006 else 0.0) for v, j in zip(lift_h, jit)],
               "fold": harmonics(300 + _s, 9, 44, 1.0, 0.5),
               "fold_edge": harmonics(400 + _s, 14, 70, 1.0, 0.3)}   # r2: small folds radiating from the edge


def drum():
    p = Part("SM_DKP_Taiko_Drum")
    phase = -math.pi / 2          # f1: UV seam at the underside (-Z), hidden by the cradle
    # ---- profile: (x, r, kind) from the -X pole to the +X pole
    lip_a = [0, 45, 90, 130]
    head = [(X_COLLAR, None, "rag_lo"), (X_COLLAR, None, "rag_hi"), (X_COLLAR + 0.010, "c", "edge_in"),
            (0.658, "c", "fold1"), (0.698, "c", "fold2"), (0.738, "c", "fold3")]
    for a in lip_a:
        ar = math.radians(a)
        head.append((LIP_XC + LIP_RHO * math.sin(ar), LIP_RC + LIP_RHO * math.cos(ar), f"lip{a}"))
    head += [(X_FACE, R_FACE, "face"), (X_FACE + 0.0012, 0.28, "face"), (X_FACE + 0.0020, 0.0, "face")]
    body_x = [0.0, 0.15, 0.30, 0.42, 0.51, 0.575]
    prof = []
    for x, r, kd in reversed(head):
        prof.append((-x, r, kd, -1))
    for x in reversed(body_x[1:]):
        prof.append((-x, body_r(x), "body", -1))
    for x in body_x:
        prof.append((x, body_r(x), "body", 1))
    for x, r, kd in head:
        prof.append((x, r, kd, 1))
    P = []
    for x, r, kd, s in prof:
        if r is None or r == "c":
            r = body_r(abs(x)) + (0 if kd == "rag_lo" else COLLAR_T)
        P.append((x, r, kd, s))
    kinds = [q[2] for q in P]
    # lip arc length from lip0 per side (for the lip strip U)
    arc = {}
    for s in (1, -1):
        acc, prev = 0.0, None
        for k, (x, r, kd, ss) in (list(enumerate(P)) if s > 0 else list(enumerate(P))[::-1]):
            if ss != s or not (kd.startswith("lip") or kd == "face"):
                continue
            if prev is not None:
                acc += math.hypot(x - prev[0], r - prev[1])
            arc[k] = acc
            prev = (x, r)
            if kd == "face" and r == R_FACE:
                break

    def seg_material(k):
        a, b = kinds[k], kinds[k + 1]
        if a == "body" and b == "body":
            return LAC
        if {a, b} <= {"body", "rag_lo"} and "rag_lo" in (a, b):
            return LAC
        hide_k = lambda q: q.startswith("lip") or q == "face"  # noqa: E731
        if hide_k(a) and hide_k(b):
            return HIDE
        return COLLAR   # includes the short run from the last fold ring onto the lip's first ring
    seg_mat = [seg_material(k) for k in range(len(P) - 1)]
    rings = [(x, r) for x, r, _k, _s in P]

    def ragged(k, i):
        x, r, kd, s = P[k]
        R = RAG[s]
        if kd in ("rag_lo", "rag_hi"):
            xe = X_COLLAR + R["dx"][i]
            lift = R["lift"][i]
            r_here = body_r(xe) + (0.6 * lift if kd == "rag_lo" else COLLAR_T + lift)
            return s * (xe - X_COLLAR), r_here - r
        if kd == "edge_in":     # r2: a ring 10 mm inside the torn edge, following it, half lifted, with small folds
            xe = X_COLLAR + R["dx"][i] + 0.010
            r_here = body_r(xe) + COLLAR_T + 0.45 * R["lift"][i] + 0.0018 * R["fold_edge"][i]
            return s * (xe - (X_COLLAR + 0.010)), r_here - r
        if kd.startswith("fold"):
            amp = {"fold1": 0.0016, "fold2": 0.0007, "fold3": 0.0009}[kd]
            return 0.0, amp * R["fold"][i]
        return 0.0, 0.0

    def uv_fn(seg, k, col, pos):
        m = seg_mat[seg]
        x = pos[0]
        s = 1 if x > 0 else -1
        if m == LAC:
            return (x / UVL.LAC_TILE + UVL.LAC_U0, UVL.LAC_WRAPS * col / SIDES)
        if m == COLLAR:
            i = col % SIDES
            xe = X_COLLAR + RAG[s]["dx"][i]
            if kinds[k] == "rag_lo":
                u = 0.0
            else:
                u = UVL.COLLAR_U_EDGE + (abs(x) - xe) / UVL.COLLAR_TILE_U
            return (u, UVL.COLLAR_WRAPS * col / SIDES)
        # hide: the flat face as a planar disc per head, the lip roll as a U strip
        if kinds[seg] == "face" and kinds[seg + 1] == "face":
            cu, cv = UVL.HEAD_CENTRE[s]
            return (s * pos[1] / UVL.HIDE_TILE + cu, pos[2] / UVL.HIDE_TILE + cv)
        return (UVL.LIP_U0[s] + arc.get(k, 0.0) / UVL.HIDE_TILE, UVL.HIDE_WRAPS * col / SIDES)

    v, f, uv, m = lathe(rings, SIDES, phase, seg_mat, uv_fn, ragged)
    p.add(v, f, uv, m, smooth=True)

    # ---- tacks: a jittered zig-zag of iron domes on each collar (f1: 30 triangles each, 110 per head, +12 %)
    tack_meta = []
    for s in (-1, 1):
        rng = random.Random(500 + s)
        for i in range(N_TACKS):
            th = 2 * math.pi * (i + 0.5 * (s > 0) + rng.uniform(-0.14, 0.14)) / N_TACKS
            xx = X_TACK + (TACK_ZZ if i % 2 else -TACK_ZZ) + rng.uniform(-0.003, 0.003)
            sc = rng.uniform(0.90, 1.05)
            r0 = body_r(xx) + COLLAR_T
            n = Vector((0.0, math.cos(th), math.sin(th)))
            t = Vector((1.0, 0.0, 0.0))
            tilt = Matrix.Rotation(rng.uniform(-0.07, 0.07), 4, "X") @ Matrix.Rotation(rng.uniform(-0.07, 0.07), 4, "Y")
            M = frame(Vector((s * xx, 0, 0)) + n * r0, t, n.cross(t), n) @ Matrix.Rotation(rng.uniform(0, 6.3), 4, "Z") \
                @ tilt
            tv, tf, tu, tm = lathe_z([(0.0, TACK_H * sc), (0.72 * TACK_R * sc, 0.72 * TACK_H * sc),
                                      (TACK_R * sc, -0.0025)], 10, IRN, uoff=((0.37 + 0.013 * i) % 1.0, 0.61 + 0.29 * s))
            p.add(tv, tf, tu, tm, smooth=True, M=M)
            tack_meta.append((s, xx, th, TACK_R * sc))

    # ---- ring handles (f1): the ring hangs under gravity in a vertical plane against the belly; its top threads the
    # staple, so the plate sits phi above the equator where the staple centre meets the ring plane
    y_plane = R_BELLY + RING_T + 0.0015
    phi = math.acos(y_plane / (R_BELLY + 0.021))
    ring_info = {}
    for s in (-1, 1):
        n = Vector((0.0, s * math.cos(phi), math.sin(phi)))
        t = Vector((1.0, 0.0, 0.0))
        d = Vector((0.0, s * math.sin(phi), -math.cos(phi)))
        P0 = n * R_BELLY
        M = frame(P0 + n * 0.001, t, d, n) @ Matrix.Rotation(math.radians(45), 4, "Z")
        hw = 0.095 / math.sqrt(2)
        pv, pf, pu, pm = cbox(-hw, hw, -hw, hw, -0.003, 0.004, IRN, grain="x", c=0.0025)
        p.add(pv, pf, pu, pm, M=M)
        rv, rf, ru, rm = dome(0.0072, 0.0065)
        for a, b in ((0.064, 0), (-0.064, 0), (0, 0.064), (0, -0.064)):
            p.add(rv, rf, ru, rm, smooth=True, M=frame(P0 + n * 0.0035 + t * a + d * b, t, d, n))
        bv, bf, bu, bm = lathe_z([(0.0, 0.010), (0.009, 0.0085), (0.014, 0.004), (0.014, -0.001)], 8, IRN)
        p.add(bv, bf, bu, bm, smooth=True, M=frame(P0 + n * 0.003, t, d, n))
        sv, sf, su, sm_ = torus(0.021, 0.0048, 12, 6, IRN)
        p.add(sv, sf, su, sm_, smooth=True, M=frame(P0 + n * 0.021, d, n, t))
        top = P0 + n * 0.021
        centre = Vector((0.0, s * y_plane, top.z - RING_R))
        gv, gf, gu, gm = torus(RING_R, RING_T, 28, 8, IRN)
        p.add(gv, gf, gu, gm, smooth=True, M=frame(centre, Vector((1, 0, 0)), Vector((0, 0, 1)), Vector((0, s, 0))))
        ring_info[s] = {"phi_deg": round(math.degrees(phi), 2), "ring_plane_y": round(s * y_plane, 4),
                        "ring_centre_z": round(centre.z, 4)}
    # collision: one convex 16-gon prism around the barrel and handles (blocking prop, unwalkable)
    rc = 0.66 / math.cos(math.pi / 16)
    pts = []
    x_end = LIP_XC + LIP_RHO + 0.004
    for x in (-x_end, x_end):
        for i in range(16):
            a = 2 * math.pi * (i + 0.5) / 16
            pts.append((x, rc * math.cos(a), rc * math.sin(a)))
    p.hull(pts)
    p.meta = {"tacks": tack_meta, "rings": ring_info}
    return p


# --------------------------------------------------------------------------- the stand

def cradle_profile(yend):
    """Saddle top of a cradle crossbeam in (y, z): flat outer shoulders, and a polyline arc whose chords stay just
    outside the drum (vertices on Rs / cos(half step), so each chord's midpoint sits at radius Rs)."""
    Rs = body_r(CRADLE_X0) + SADDLE_GAP
    a_max = math.asin(CRADLE_FLAT_Y / Rs)
    nseg = 10
    step = 2 * a_max / nseg
    Rv = Rs / math.cos(step / 2)
    pts = [(-yend, DRUM_Z - math.sqrt(Rs * Rs - CRADLE_FLAT_Y ** 2))]
    for i in range(nseg + 1):
        a = -a_max + i * step
        rr = Rs if i in (0, nseg) else Rv
        pts.append((rr * math.sin(a), DRUM_Z - rr * math.cos(a)))
    pts.append((yend, pts[0][1]))
    return pts, Rs


def extrude_heightfield(xa, xb, prof, zb, mat):
    """Closed solid between x = xa..xb whose Y-Z section is the area under the polyline prof (y ascending) down to
    zb. Built as vertical strips so every face is a convex quad (no n-gons)."""
    verts, faces = [], []
    for x in (xa, xb):
        for (y, z) in prof:
            verts.append((x, y, z))
        for (y, z) in prof:
            verts.append((x, y, zb))
    n = len(prof)
    T0, B0, T1, B1 = 0, n, 2 * n, 3 * n
    for i in range(n - 1):
        faces.append((T0 + i, T0 + i + 1, B0 + i + 1, B0 + i))
        faces.append((T1 + i, B1 + i, B1 + i + 1, T1 + i + 1))
        faces.append((T0 + i, T1 + i, T1 + i + 1, T0 + i + 1))
        faces.append((B0 + i, B0 + i + 1, B1 + i + 1, B1 + i))
    faces.append((T0, B0, B1, T1))
    faces.append((T0 + n - 1, T1 + n - 1, B1 + n - 1, B0 + n - 1))
    tile = TILE[mat]
    uvs = []
    for f in faces:
        pts = [Vector(verts[i]) for i in f]
        nrm = (pts[1] - pts[0]).cross(pts[2] - pts[0])
        if abs(nrm.x) > max(abs(nrm.y), abs(nrm.z)):
            uvs.append([(q.y / tile + 0.21, q.z / tile) for q in pts])
        elif abs(nrm.y) > abs(nrm.z):
            uvs.append([(q.z / tile, q.x / tile + 0.33) for q in pts])
        else:
            uvs.append([(q.y / tile + 0.21, q.x / tile + 0.33) for q in pts])
    return verts, faces, uvs, [mat] * len(faces)


def post_top():
    """Post top 4 mm under the drum surface above the post's inner top corner (the highest drum-bottom point over the
    post's top face)."""
    xin, yin = POST_X - POST_W / 2, POST_Y - POST_W / 2
    r = body_r(xin)
    return DRUM_Z - math.sqrt(r * r - yin * yin) - 0.004


def stand():
    p = Part("SM_DKP_Taiko_Stand")
    hw = POST_W / 2
    PT = post_top()
    E = dict(end_mat=TIMEND)
    for sx in (-1, 1):
        xc = sx * POST_X
        # foot sill along Y (f1: heavier) with chunky raised stop blocks at both ends
        p.add(*cbox(xc - SILL_W / 2, xc + SILL_W / 2, -SILL_Y, SILL_Y, 0.0, SILL_H, TIM, grain="y", c=0.016,
                    uvoff=(0.1 * sx, 0.37), **E))
        for sy in (-1, 1):
            y0, y1 = sorted((sy * (SILL_Y - 0.145), sy * (SILL_Y - 0.004)))
            p.add(*cbox(xc - 0.125, xc + 0.125, y0, y1, SILL_H - 0.02, SILL_H + 0.11, TIM, grain="x", c=0.016,
                        uvoff=(0.23 * sy, 0.1 * sx), rough=0.003, **E))
        # cradle crossbeam (along Y) with the saddle; its ends run through the posts
        xa, xb = sorted((sx * CRADLE_X0, sx * CRADLE_X1))
        prof, Rs = cradle_profile(POST_Y + hw - 0.01)
        p.add(*extrude_heightfield(xa, xb, prof, CRADLE_BOTTOM, TIM))
        # f1: chunky kusabi wedge blocks outside the posts (taller than the beam, rough, no peg on top)
        for sy in (-1, 1):
            y0, y1 = sorted((sy * (POST_Y + hw - 0.004), sy * CRADLE_Y))
            wv, wf, wu, wm = cbox(xa - 0.008, xb + 0.008, y0, y1, CRADLE_BOTTOM - 0.025, CRADLE_BOTTOM + 0.195, TIM,
                                  grain="z", c=0.018, uvoff=(0.41, 0.17 * sy), rough=0.006, seed=900 + 10 * sx + sy, **E)
            xm, zb_, zt_ = 0.5 * (xa + xb), CRADLE_BOTTOM - 0.025, CRADLE_BOTTOM + 0.195
            wv = [(xm + (v[0] - xm) * (0.80 + 0.20 * (v[2] - zb_) / (zt_ - zb_)), v[1], v[2]) for v in wv]  # wedge taper
            p.add(wv, wf, wu, wm)
        for sy in (-1, 1):
            yc = sy * POST_Y
            p.add(*cbox(xc - hw, xc + hw, yc - hw, yc + hw, SILL_H - 0.03, PT, TIM, grain="z", c=0.014,
                        uvoff=(0.19 * sx + 0.05 * sy, 0.63), **E))
    # long rails (along X) at two levels on both sides, running out past the posts. r3: each rail laps flush on the
    # posts' outer faces (the sheet's joint close-up: the beam passes the post's outer face and a flat iron strap
    # plate is nailed flush across the joint). The r2 6 mm U-wrap round the rail end read as a black cube (judge r2
    # blocker 2) and is gone: the rail's end grain shows, as on the sheet.
    rivets = []
    for sy in (-1, 1):
        for (z0, z1), off, flush in ((RAIL_LO, 0.29, False), (RAIL_HI, 0.71, True)):
            # the lower rail stays centred through the post (its outer face must clear the sill's stop block,
            # which stands 3 cm outside it); its plate covers only the protruding end
            yc = sy * (POST_Y + (RAIL_Y_OUT if flush else 0.0))
            yo = yc + sy * RAIL_W / 2      # the rail's outer face (flush with the post's for the upper rail)
            p.add(*cbox(-RAIL_X, RAIL_X, yc - RAIL_W / 2, yc + RAIL_W / 2, z0, z1, TIM, grain="x", c=0.012,
                        uvoff=(0.0, off + 0.13 * sy), **E))
            for sx in (-1, 1):
                # a 4 mm flat strap plate: upper rail from just outside the cradle wedge block (x 0.585) across the
                # post's outer corner to 12 mm short of the rail tip; lower rail from the post's face to the tip
                x_in = 0.585 if flush else POST_X + hw + 0.003
                xa_, xb_ = sorted((sx * x_in, sx * (RAIL_X - 0.012)))
                ya_, yb_ = sorted((yo - sy * 0.0008, yo + sy * PLATE_T))
                p.add(*pbox(xa_, xb_, ya_, yb_, z0 + 0.012, z1 - 0.012))
                yn = yo + sy * PLATE_T
                zm, dz = 0.5 * (z0 + z1), 0.5 * (z1 - z0) - 0.030
                nrm = Vector((0, sy, 0))
                xe = RAIL_X - 0.032
                if flush:
                    rivets += [((sx * 0.607, yn, zm + dz), nrm, "small"), ((sx * 0.607, yn, zm - dz), nrm, "small"),
                               ((sx * 0.672, yn, zm - 0.004), nrm, "big")]
                else:
                    rivets += [((sx * (x_in + 0.022), yn, zm + 0.012), nrm, "big")]
                rivets += [((sx * xe, yn, zm + dz), nrm, "small"), ((sx * xe, yn, zm - dz), nrm, "small")]
    for k, (o, n, kind) in enumerate(rivets):
        big = kind == "big"
        rv, rf, ru, rm = dome(0.0120 if big else 0.0065, 0.0075 if big else 0.0045, 8 if big else 6)
        t = Vector((0, 0, 1)) if abs(n.z) < 0.5 else Vector((1, 0, 0))
        d = n.cross(t)
        p.add(rv, rf, ru, rm, smooth=True, M=frame(Vector(o), t, d, n))

    # ---- collision (blocking prop, unwalkable). f1: the saddle shoulders and wedge blocks are covered
    def box_pts(x0, x1, y0, y1, z0, z1):
        return [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    for sx in (-1, 1):
        xc = sx * POST_X
        p.hull(box_pts(xc - SILL_W / 2 - 0.01, xc + SILL_W / 2 + 0.01, -SILL_Y - 0.01, SILL_Y + 0.01, 0.0, SILL_H))
        for sy in (-1, 1):
            y0, y1 = sorted((sy * (SILL_Y - 0.145), sy * (SILL_Y + 0.004)))
            p.hull(box_pts(xc - 0.14, xc + 0.14, y0 - 0.005, y1 + 0.005, SILL_H - 0.025, SILL_H + 0.12))
        xa, xb = sorted((sx * CRADLE_X0, sx * CRADLE_X1))
        prof, _Rs = cradle_profile(POST_Y + hw - 0.01)
        cpts = [(x, y, z + 0.002) for y, z in prof if abs(y) <= 0.18 for x in (xa, xb)]
        p.hull(cpts + [(x, y, CRADLE_BOTTOM) for _x, y, _z in cpts for x in (xa, xb)])   # f1: follows the arc
        for sy in (-1, 1):
            pts = []
            for y, z in prof:
                if sy * y >= 0.17:
                    pts += [(x, y, z + 0.002) for x in (xa, xb)] + [(x, y, CRADLE_BOTTOM) for x in (xa, xb)]
            y_out = sy * (CRADLE_Y + 0.008)
            pts += [(x, y_out, z) for x in (xa - 0.012, xb + 0.012)
                    for z in (CRADLE_BOTTOM - 0.03, CRADLE_BOTTOM + 0.202)]
            pts += [(x, sy * (POST_Y + hw - 0.004), z) for x in (xa - 0.012, xb + 0.012)
                    for z in (CRADLE_BOTTOM - 0.03, CRADLE_BOTTOM + 0.202)]
            p.hull(pts)
        for sy in (-1, 1):
            yc = sy * POST_Y
            xo = sx * (POST_X + hw + 0.013)
            x0, x1 = sorted((xc - sx * hw, xo))
            p.hull(box_pts(x0, x1, yc - hw, yc + hw, SILL_H - 0.03, PT))
    for sy in (-1, 1):
        for (z0, z1) in (RAIL_LO, RAIL_HI):
            yc = sy * (POST_Y + (RAIL_Y_OUT if (z0, z1) == RAIL_HI else 0.0))   # r3: upper rails lap flush
            p.hull(box_pts(-RAIL_X - 0.004, RAIL_X + 0.004, yc - RAIL_W / 2 - 0.004, yc + RAIL_W / 2 + 0.014,
                           z0 - 0.004, z1 + 0.004) if sy > 0 else
                   box_pts(-RAIL_X - 0.004, RAIL_X + 0.004, yc - RAIL_W / 2 - 0.014, yc + RAIL_W / 2 + 0.004,
                           z0 - 0.004, z1 + 0.004))
    return p


# --------------------------------------------------------------------------- the stick

def stick_r(x):
    """r3: a slight taper toward the grip (x = 0), 13 %."""
    return STICK_R_GRIP + (STICK_R_TIP - STICK_R_GRIP) * max(0.0, min(1.0, x / STICK_L))


def stick_profile():
    """r3 (round-2 judge blocker 1 / delta 1: 'a lathe-turned stick, fully domed ends, no flat caps'): the turned
    profile (x, r) pole to pole. Each end is a superellipse dome (height STICK_DOME[0] x the end radius, exponent
    STICK_DOME[1]): round in silhouette with a soft shoulder, as the sheet's close-up. Returns the rings and the
    arc length of each ring from the grip pole (the UV's V)."""
    k, n = STICK_DOME
    h0, h1 = k * stick_r(0.0), k * stick_r(STICK_L)
    rings = []
    for deg in (0, 14, 26, 38, 50, 62, 74, 90):          # grip dome, pole -> shoulder
        ph = math.radians(deg)
        rings.append((h0 * (1 - math.cos(ph) ** (2 / n)), stick_r(0.0) * math.sin(ph) ** (2 / n)))
    body = [h0 + (STICK_L - h0 - h1) * t for t in (0.08, 0.2, 0.35, 0.5, 0.65, 0.8, 0.92)]
    for x in body:
        rings.append((x, stick_r(x)))
    for deg in (90, 74, 62, 50, 38, 26, 14, 0):          # strike dome, shoulder -> pole
        ph = math.radians(deg)
        rings.append((STICK_L - h1 * (1 - math.cos(ph) ** (2 / n)), stick_r(STICK_L) * math.sin(ph) ** (2 / n)))
    rings[0] = (0.0, 0.0)
    rings[-1] = (STICK_L, 0.0)
    arc = [0.0]
    for a, b in zip(rings[:-1], rings[1:]):
        arc.append(arc[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    return rings, arc


def stick():
    """r3: the bachi as a turned stick on the HIDE atlas's wood patch (taiko_uv.BACHI_*): U = one whole wrap round
    the stick over the periodic patch (no seam step), V = arc length along the profile from the grip pole, so the
    domes continue the side grain into the pole and carry the patch's end-grain tone (no radial pinwheel)."""
    p = Part("SM_DKP_Taiko_Stick")
    rings, arc = stick_profile()
    sides = 20

    def uv_fn(seg, k, col, pos):
        return (UVL.BACHI_U0 + UVL.BACHI_UW * col / sides, UVL.BACHI_V0 + arc[k] / UVL.HIDE_TILE)
    v, f, uv, m = lathe(rings, sides, -math.pi / 2, [HIDE] * (len(rings) - 1), uv_fn)
    p.add(v, f, uv, m, smooth=True)
    p.meta = {"arc_len_m": round(arc[-1], 4), "sides": sides, "rings": len(rings),
              "dome_heights_m": [round(STICK_DOME[0] * stick_r(0.0), 4), round(STICK_DOME[0] * stick_r(STICK_L), 4)]}
    rc = (STICK_R_TIP + 0.002) / math.cos(math.pi / 8)
    pts = []
    for x in (-0.001, STICK_L + 0.001):
        for i in range(8):
            a = 2 * math.pi * (i + 0.5) / 8
            pts.append((x, rc * math.cos(a), rc * math.sin(a)))
    p.hull(pts)
    return p


def stick_f1_r2():
    """(f1/r2 flat-ended stick on M_DJ_TimberAged, retired in r3)"""
    return None


# --------------------------------------------------------------------------- stick lean solver (f1)

def mesh_world(obj, M):
    me = obj.data
    return [M @ v.co for v in me.vertices], [tuple(pl.vertices) for pl in me.polygons]


def surface_samples(verts, polys, step, near_bvh, margin=0.02):
    """Stick side: points on the mesh surface (a barycentric grid `step` apart, which includes the vertices and
    edges) on the triangles that lie within `margin` of the obstacle (near_bvh), so the sampling stays local."""
    out = []
    for pl in polys:
        for a in range(1, len(pl) - 1):
            tri = (verts[pl[0]], verts[pl[a]], verts[pl[a + 1]])
            ln = max((tri[1] - tri[0]).length, (tri[2] - tri[1]).length, (tri[0] - tri[2]).length)
            c = (tri[0] + tri[1] + tri[2]) / 3
            if near_bvh.find_nearest(c, ln + margin)[0] is None:
                continue
            n = max(1, int(math.ceil(ln / step)))
            for i in range(n + 1):
                for j in range(n + 1 - i):
                    u, w = i / n, j / n
                    out.append(tri[0] * (1 - u - w) + tri[1] * u + tri[2] * w)
    return out


def edge_samples(verts, edges, step, lo, hi):
    """Obstacle side: vertices and edge points `step` apart, clipped to the box lo..hi around the stick. With the
    stick's surface grid this covers the vertex-face, face-vertex and edge-edge contact cases."""
    out = [v for v in verts if all(lo[i] <= v[i] <= hi[i] for i in range(3))]
    for a, b in edges:
        p0, p1 = verts[a], verts[b]
        d = p1 - p0
        t0, t1 = 0.0, 1.0
        for i in range(3):
            if abs(d[i]) < 1e-12:
                if p0[i] < lo[i] or p0[i] > hi[i]:
                    t0, t1 = 1.0, 0.0
                    break
                continue
            ta, tb = (lo[i] - p0[i]) / d[i], (hi[i] - p0[i]) / d[i]
            t0, t1 = max(t0, min(ta, tb)), min(t1, max(ta, tb))
        if t1 <= t0:
            continue
        n = max(1, int(math.ceil((t1 - t0) * d.length / step)))
        out += [p0 + d * (t0 + (t1 - t0) * k / n) for k in range(n + 1)]
    return out


def min_gap(stick_obj, M, obstacles, step=0.003):
    """Minimum surface distance between the stick placed at M and the obstacle meshes (two-way sampled)."""
    sv, sp = mesh_world(stick_obj, M)
    s_bvh = BVHTree.FromPolygons(sv, sp)
    lo = Vector([min(v[i] for v in sv) - 0.01 for i in range(3)])
    hi = Vector([max(v[i] for v in sv) + 0.01 for i in range(3)])
    best = (1e9, None)
    for name, (ov, oe, o_bvh) in obstacles.items():
        for q in surface_samples(sv, sp, step, o_bvh):
            hit = o_bvh.find_nearest(q, 0.05)
            if hit[0] is not None and hit[3] < best[0]:
                best = (hit[3], name)
        for q in edge_samples(ov, oe, step, lo, hi):
            hit = s_bvh.find_nearest(q, 0.05)
            if hit[0] is not None and hit[3] < best[0]:
                best = (hit[3], name)
    return best


def stick_poses(stick_obj, stand_obj, drum_obj):
    """f1 (blind judge + measurer): both sticks stand on the plinth at the front-right (+X, -Y) end of the stand and
    lean 15 and 18.5 degrees toward -X onto the upper front rail's end (its folded iron strap), as in the sheet's
    front view. The tilt is fixed; the stick slides along X until the sampled mesh gap to the stand or drum is
    0.5 mm; the feet are set 0.5 mm above the plinth (the lowest vertex of a polyhedron is its lowest point)."""
    obstacles = {}
    for name, obj, M in (("stand", stand_obj, Matrix.Identity(4)), ("drum", drum_obj,
                                                                    Matrix.Translation((0, 0, DRUM_Z)))):
        v, pl = mesh_world(obj, M)
        obstacles[name] = (v, [tuple(e.vertices) for e in obj.data.edges], BVHTree.FromPolygons(v, pl))
    target = 0.0005
    poses = []
    placed = []
    # r2 (judges: "sticks lean at the far end by the post"): both sticks stand beside the +X/-Y post, just outboard
    # of the sill's stop block, and lean BACK onto the iron wrap of the upper front rail's end (the sheet's 3/4 view:
    # two sticks side by side against the far post). Each stick keeps its tilt and lean azimuth and slides along the
    # lean direction s (horizontal) from well outside until the sampled mesh gap is 0.5 mm.
    #   (foot x at the start, foot y at the start, slide direction s, tilt from vertical, roll)
    specs = ((0.745, -1.10, (0.0, 1.0), 11.0, 0.6),
             (1.350, -0.50, (-1.0, 0.15), 14.0, 2.3))   # the second leans in on the rail end's iron plate
    for k, (x0, y0, sdir, tilt, roll) in enumerate(specs):
        sv_ = Vector((sdir[0], sdir[1], 0.0)).normalized()
        a = math.radians(tilt)
        D = Vector((-sv_.x * math.sin(a), -sv_.y * math.sin(a), -math.cos(a)))   # grip (top) -> strike end (foot)
        q = Vector((1, 0, 0)).rotation_difference(D)
        R = q.to_matrix().to_4x4() @ Matrix.Rotation(roll, 4, "X")
        zmin = min((R @ v.co).z for v in stick_obj.data.vertices)
        foot_local = min(stick_obj.data.vertices, key=lambda v: (R @ v.co).z).co
        fl = R @ foot_local

        def pose(t, x0=x0, y0=y0, sv_=sv_, R=R, zmin=zmin, fl=fl):
            # t = distance slid along s; the lowest vertex (the foot) sits at (x0, y0) + s t
            return Matrix.Translation((x0 + sv_.x * t - fl.x, y0 + sv_.y * t - fl.y, target - zmin)) @ R
        obs = dict(obstacles)
        for j, Mo in enumerate(placed):
            v, pl = mesh_world(stick_obj, Mo)
            obs[f"stick{j}"] = (v, [tuple(e.vertices) for e in stick_obj.data.edges], BVHTree.FromPolygons(v, pl))
        # march in from outside, then bisect on t for a 0.5 mm gap (t grows toward the stand)
        t_far = 0.0
        g_far = min(0.2, min_gap(stick_obj, pose(t_far), obs, 0.004)[0])
        t_near = t_far
        while True:
            t_try = t_near + max(0.0015, min(0.05, g_far * 0.5))
            g = min(0.2, min_gap(stick_obj, pose(t_try), obs, 0.004)[0])
            if g < target:
                t_near = t_try
                break
            t_far, g_far, t_near = t_try, g, t_try
            if t_try > 1.2:
                raise RuntimeError("stick %d never touched the stand" % k)
        lo_x, hi_x = t_near, t_far      # lo: touching, hi: clear
        for _ in range(16):
            mid = 0.5 * (lo_x + hi_x)
            g = min_gap(stick_obj, pose(mid), obs, 0.001)[0]
            if g > target:
                hi_x = mid
            else:
                lo_x = mid
        M = pose(hi_x)
        gap, who = min_gap(stick_obj, M, obs, 0.001)
        foot = min((M @ v.co).z for v in stick_obj.data.vertices)
        tip = M @ Vector((STICK_L, 0, 0))
        top = M @ Vector((0, 0, 0))
        placed.append(M)
        fw = M @ foot_local
        print(f"stick {k}: gap {gap:.5f} with {who}, foot {foot:.5f}, foot xy {fw.x:.4f} {fw.y:.4f}")
        poses.append((M, {"tilt_from_vertical_deg": tilt, "lean_toward_xy": [round(sv_.x, 3), round(sv_.y, 3)],
                          "roll_rad": roll, "contact_gap_m": round(gap, 5), "contact_with": who,
                          "foot_gap_above_plinth_m": round(foot, 5),
                          "foot_xy_stand_local": [round(fw.x, 4), round(fw.y, 4)],
                          "top_end_centre_stand_local": [round(c, 4) for c in top],
                          "strike_end_centre_stand_local": [round(c, 4) for c in tip],
                          "solver": "BVH: stick surface grid + obstacle vertices/edges, 1 mm samples; bisection "
                                    "on the slide distance"}))
    return poses


def _old_stick_loop_f1():
    """f1 stick loop (retired in r2)."""
    for k, (y, tilt, yaw, roll) in enumerate(()):
        pass


# --------------------------------------------------------------------------- layout

# Spec (DOJO_ARENA_SPEC 4.5, grey-box SM_DGB_Pavilion): pavilion plinth X 39-43, Y 1-5, top +1.0; the drum stands at
# the plinth centre (41, 3), drum axis north-south (local X -> world +Y, rot_z 90): the sheet's front view faces the
# courtyard on the west.
PAV_CENTRE = (41.0, 3.0)
PLINTH_TOP = 1.0
ROT_Z = 90.0


def export_with_lods(name, o, sc, waive):
    """kit 1's pattern: LOD0-2 on temporary copies (pipeline decimate_lods + make_lod_group, UCX renamed
    UCX_<base>_LOD0_NN), QA on the LODs, export the LodGroup through Scripts/pipeline."""
    tmp = bpy.data.collections.new("TmpLOD")
    sc.collection.children.link(tmp)
    c0 = o.copy()
    c0.data = o.data.copy()
    c0.name = f"{name}_LOD0"
    tmp.objects.link(c0)
    for h in o.children:
        hc = h.copy()
        hc.data = h.data.copy()
        hc.name = h.name.replace(f"UCX_{name}_", f"UCX_{name}_LOD0_")
        tmp.objects.link(hc)
        hc.parent = c0
    lods = decimate_lods(c0, (0.5, 0.25))
    cleaned = {}
    for lo in lods:   # Collapse can leave wire edges / loose verts where a tiny rivet collapses: drop them
        bm = bmesh.new()
        bm.from_mesh(lo.data)
        wire = [e for e in bm.edges if not e.link_faces]
        bmesh.ops.delete(bm, geom=wire, context="EDGES")
        loose = [v for v in bm.verts if not v.link_edges]
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
        bm.to_mesh(lo.data)
        bm.free()
        cleaned[lo.name] = {"wire_edges_removed": len(wire), "loose_verts_removed": len(loose)}
    grp = make_lod_group(name, [c0] + lods)
    lq = qa_check([c0] + lods, require_uv1=True, require_ucx=False)
    lod_hard = [c for c in lq["checks"] if not c["passed"] and c["name"] not in waive]
    r = export_fbx(str(EXPORT_DIR / f"{name}.fbx"), [grp], kind="static", sidecar=True)
    tris = [lq["triangles"].get(x.name) for x in [c0] + lods]
    rep = {"lods": 3, "lod_tris": tris, "strictly_descending": all(a > b for a, b in zip(tris, tris[1:])),
           "lod_qa_hard_fails": [(c["name"], c["object"], str(c["detail"])[:160]) for c in lod_hard],
           "lod_cleanup": cleaned, "objects": r["objects"], "screen_sizes": r.get("lod_screen_sizes"), "warnings": r["warnings"]}
    for ob in list(tmp.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.collections.remove(tmp)
    return rep


def main():
    assert_owner("DojoTaiko", "claude")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    for name in MATERIALS:
        build_material(name)
    parts = {"SM_DKP_Taiko_Drum": ("Taiko_Drum", drum()), "SM_DKP_Taiko_Stand": ("Taiko_Stand", stand()),
             "SM_DKP_Taiko_Stick": ("Taiko_Stick", stick())}
    objs = {}
    for name, (cname, part) in parts.items():
        coll = bpy.data.collections.new(cname)
        sc.collection.children.link(coll)
        objs[name] = part.build(coll)
    drum_meta = parts["SM_DKP_Taiko_Drum"][1].meta
    # r2: the stand's timber takes the library's grain_uv (U along each member's long axis, V round the member from
    # its centre, a random per-member offset, end faces planar with TimberDarkEnd): t1's per-face planar V put the
    # two faces of one member on different tone bands of the 4 m tile (a light face next to a dark one)
    st = objs["SM_DKP_Taiko_Stand"]
    mi = {m.name: i for i, m in enumerate(st.data.materials)}
    wood = [pl.index for pl in st.data.polygons if pl.material_index in (mi[TIM], mi[TIMEND])]
    for i in wood:
        st.data.polygons[i].material_index = mi[TIM]
    gstats = djm.grain_uv(st, "TimberDark", end_set="TimberDarkEnd", faces=wood, end_material_index=mi[TIMEND],
                          seed=11, uv_map="UV0")
    print("GRAIN", gstats)
    TIMBER_BAND = {"stand": pin_band_v(st, {TIM}, 0.27, 0.51, seed=5),
                   "stick": "r3: the stick is on the hide atlas's own wood patch (no library band)"}
    print("BAND", TIMBER_BAND)
    # r2: the library's weathering corner colour 'Wear' (R grime / occlusion, G edge wear on narrow convex bevels,
    # B ground dirt), read by every library-graph material here and by M_DJ_Lib_Opaque in Unreal
    wear = {}
    for name, o in objs.items():
        gz = {"SM_DKP_Taiko_Drum": -DRUM_Z, "SM_DKP_Taiko_Stand": 0.0, "SM_DKP_Taiko_Stick": -10.0}[name]
        wear[name] = djm.bake_wear(o, ao_rays=16, ao_dist=0.12, ground_z=gz)
        wear[name + "_regrime"] = regrime(o, dist=0.12, ground_z=(0.0 if name.endswith("Stand") else None))
        o.data.color_attributes.active_color_name = "Wear"
    wear["drum_bulge"] = drum_wear_bulge(objs["SM_DKP_Taiko_Drum"])
    wear["stick_edges"] = stick_wear_ends(objs["SM_DKP_Taiko_Stick"])
    print("WEAR", wear)

    # ---- layout (assembled at the pavilion's drum position, grey-box frame) as linked instances
    lay = bpy.data.collections.new("Taiko_Layout")
    sc.collection.children.link(lay)
    base = Matrix.Translation((PAV_CENTRE[0], PAV_CENTRE[1], PLINTH_TOP)) @ Matrix.Rotation(math.radians(ROT_Z), 4, "Z")
    local = {"SM_DKP_Taiko_Stand": [(Matrix.Identity(4), {})],
             "SM_DKP_Taiko_Drum": [(Matrix.Translation((0, 0, DRUM_Z)), {})],
             "SM_DKP_Taiko_Stick": stick_poses(objs["SM_DKP_Taiko_Stick"], objs["SM_DKP_Taiko_Stand"],
                                               objs["SM_DKP_Taiko_Drum"])}
    instances = []
    for piece, lst in local.items():
        for k, (ML, info) in enumerate(lst):
            o = bpy.data.objects.new(f"{piece}__{k:02d}", objs[piece].data)
            o.matrix_world = base @ ML
            lay.objects.link(o)
            loc, rot, _s = o.matrix_world.decompose()
            eul = rot.to_euler("XYZ")
            pts = [o.matrix_world @ v.co for v in o.data.vertices]
            instances.append({
                "piece": piece, "name": o.name,
                "loc": [round(c, 4) for c in loc], "rot_xyz_deg": [round(math.degrees(a), 3) for a in eul],
                "stand_local_matrix": [[round(c, 6) for c in row] for row in ML],
                "bbox_min_max": [round(min(q[i] for q in pts), 4) for i in range(3)] +
                                [round(max(q[i] for q in pts), 4) for i in range(3)],
                "unreal_loc_cm": [round(loc.x * 100, 2), round(-loc.y * 100, 2), round(loc.z * 100, 2)],
                **({"pose": info} if info else {})})

    meas = measure(objs, instances, drum_meta)
    WORK.mkdir(parents=True, exist_ok=True)

    coll_classes = {
        "SM_DKP_Taiko_Drum": {"class": "blocking prop, unwalkable (spec 5.2: 'the drum and its stand')",
                               "pawn": "block", "camera": "ignore", "visibility": "block", "gasp_traversal": "none",
                               "can_character_step_up_on": "No", "walkable_slope_override": "Unwalkable",
                               "ucx": "one convex 16-gon prism around barrel + handles"},
        "SM_DKP_Taiko_Stand": {"class": "blocking prop, unwalkable (thin-upright rules: camera and sight ignore)",
                                "pawn": "block", "camera": "ignore", "visibility": "ignore", "gasp_traversal": "none",
                                "can_character_step_up_on": "No", "walkable_slope_override": "Unwalkable",
                                "ucx": "20 hulls: 2 sills, 4 stop blocks, 2 x 3 cradle (centre + 2 shoulders with "
                                       "the wedge blocks), 4 posts (with the strap legs), 4 rails (with the straps)"},
        "SM_DKP_Taiko_Stick": {"class": "small dressing (lean-on prop)", "pawn": "ignore", "camera": "ignore",
                                "visibility": "ignore", "gasp_traversal": "none",
                                "ucx": "one convex 8-gon prism (kept for physics / a later pickup)"},
    }
    data = {"units": "metres, grey-box frame (DOJO_ARENA_SPEC section 1); UE: (x*100, -y*100, z*100), yaw = -rot_z",
            "source_spec": "WorkFiles/world/DOJO_ARENA_SPEC.md 4.5 (drum pavilion plinth X 39-43, Y 1-5, top +1.0)",
            "anchor": {"pavilion_plinth_centre": list(PAV_CENTRE), "plinth_top_z": PLINTH_TOP, "rot_z_deg": ROT_Z,
                       "note": "drum axis north-south; ring-handle side faces the courtyard (west). The pavilion "
                               "itself is not in this run. Sticks lean at the stand's +X/-Y corner (world north-"
                               "west corner)."},
            "pieces": {n: {"fbx": f"Exports/DojoKit/Props/taiko/{n}.fbx", "pivot": pv, "lods": 3,
                           "materials": [m.name for m in objs[n].data.materials], "collision": coll_classes[n]}
                       for n, pv in (("SM_DKP_Taiko_Drum", "drum centre (on the axis, mid-length)"),
                                     ("SM_DKP_Taiko_Stand", "base centre on the ground"),
                                     ("SM_DKP_Taiko_Stick", "grip end, on the stick axis; stick along +X"))},
            "instances": instances,
            "materials": {k: {"texture_set": (f"T_DKP_Taiko_{v[0]}" if k in OWN else
                                              f"T_DJ_{v[0].split()[-1]} (Exports/DojoKit/Materials/Textures)"),
                              "params": v[1]} for k, v in MATERIALS.items()},
            "tris": {k: sum(len(pl.vertices) - 2 for pl in o.data.polygons) for k, o in objs.items()}}
    (WORK / "layout_taiko.json").write_text(json.dumps(data, indent=1), encoding="utf-8")

    # ---- QA (pipeline gates; tiling materials waive UV0 overlap by design, as the armory kit does)
    qa = {}
    waive = {"uv_no_overlap"}
    for name, o in objs.items():
        r = qa_check([o], require_uv1=True)
        fails = [c for c in r["checks"] if not c["passed"]]
        hard = [c for c in fails if c["name"] not in waive]
        qa[name] = {"hard_fails": hard, "waived": [c["name"] for c in fails if c["name"] in waive],
                    "tris": r["triangles"].get(name), "checks_run": len(r["checks"]),
                    "texel": [c["detail"] for c in r["checks"] if c["name"] == "texel_density"]}
    hard_total = sum(len(v["hard_fails"]) for v in qa.values())
    print(f"QA: {len(objs)} pieces, hard fails {hard_total}")
    for k, v in qa.items():
        print("  ", k, "tris", v["tris"], "waived", v["waived"])
        for c in v["hard_fails"]:
            print("  FAIL", k, c["name"], str(c["detail"])[:200])

    if "--no-export" not in ARGS and hard_total == 0:
        lay.hide_viewport = True
        results = {}
        for name, o in objs.items():
            results[name] = export_with_lods(name, o, sc, waive)
            print("  export", name, results[name]["lod_tris"], results[name]["lod_qa_hard_fails"])
        (WORK / "export_report.json").write_text(json.dumps(results, indent=1, default=str), encoding="utf-8")
        lay.hide_viewport = False
        for name, rr in results.items():
            qa[name]["lods"] = {"lod_tris": rr["lod_tris"], "strictly_descending": rr["strictly_descending"],
                                "lod_qa_hard_fails": rr["lod_qa_hard_fails"]}
        meas["summary"]["lod_tris"] = {k: v["lod_tris"] for k, v in results.items()}
        print(f"exported {len(results)} FBX to {EXPORT_DIR}")
    (WORK / "qa_report.json").write_text(json.dumps(qa, indent=1, default=str), encoding="utf-8")
    (WORK / "measure.json").write_text(json.dumps(meas, indent=1), encoding="utf-8")
    BLEND.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    print("saved", BLEND)
    print("MEASURE", json.dumps(meas["summary"]))


def pin_band_v(obj, mat_names, lo, hi, seed=0, uv="UV0"):
    """r2: pin every timber member (a connected island of faces using one of mat_names) into the V range lo..hi of
    the library tile. The library timber sets carry a strong large-scale tone band ACROSS V (TimberDark row means:
    v 0.03-0.2 near black, 12-15; v 0.27-0.51 mid, 43-67; v 0.52-0.97 light, 95-124), so the library's random
    per-member offsets make one member black and its neighbour orange (the judges' 'one member differs' look). The
    reference timber is one even dark brown, so every member of these props samples the same band; U offsets stay
    random. Shifts are rigid (whole-island), so texel density and continuity are unchanged."""
    import bmesh as _bm
    import random as _rnd
    rng = _rnd.Random(seed)
    me = obj.data
    idx = {i for i, m in enumerate(me.materials) if m and m.name in mat_names}
    bm = _bm.new()
    bm.from_mesh(me)
    lay = bm.loops.layers.uv[uv]
    faces = [f for f in bm.faces if f.material_index in idx]
    fset = set(faces)
    seen, n_isl, spans = set(), 0, []
    for f0 in faces:
        if f0.index in seen:
            continue
        stack, isl = [f0], []
        seen.add(f0.index)
        while stack:
            c = stack.pop()
            isl.append(c)
            for e in c.edges:
                for g in e.link_faces:
                    if g in fset and g.index not in seen:
                        seen.add(g.index)
                        stack.append(g)
        vs = [l[lay].uv.y for f in isl for l in f.loops]
        v0, v1 = min(vs), max(vs)
        span = v1 - v0
        spans.append(round(span, 4))
        c_ = rng.uniform(lo + span / 2, hi - span / 2) if span < hi - lo else 0.5 * (lo + hi)
        d = c_ - 0.5 * (v0 + v1)
        for f in isl:
            for l in f.loops:
                l[lay].uv.y += d
        n_isl += 1
    bm.to_mesh(me)
    bm.free()
    me.update()
    return {"islands": n_isl, "band_v": [lo, hi], "max_span": max(spans) if spans else 0,
            "over_band": sum(1 for s in spans if s > hi - lo)}


def regrime(obj, rays=16, dist=0.15, inset=0.30, ground_z=None, attr="Wear"):
    """r2: re-sample the library Wear R (grime / occlusion) per face CORNER at a point 30 % in from the corner toward
    the face centre, instead of at the vertex. These props are built from interpenetrating members (a rail runs
    through a post, a brace dies into a block), so a vertex buried inside a neighbouring member is fully occluded and
    the library's per-vertex value darkened the whole face toward it (measured: stand R mean 0.61). The formula is the
    library's (cosine hemisphere, hits / rays x 1.4, clamped); an optional ground plane at ground_z occludes too. G and
    B stay exactly as bake_wear wrote them."""
    import math as _m
    import random as _r
    from mathutils import Vector as _V
    from mathutils.bvhtree import BVHTree as _B
    me = obj.data
    Mw = obj.matrix_world
    verts = [Mw @ v.co for v in me.vertices]
    polys = [tuple(p.vertices) for p in me.polygons]
    if ground_z is not None:
        n0 = len(verts)
        verts += [_V((-20, -20, ground_z)), _V((20, -20, ground_z)), _V((20, 20, ground_z)), _V((-20, 20, ground_z))]
        polys.append((n0, n0 + 1, n0 + 2, n0 + 3))
    bvh = _B.FromPolygons(verts, polys, epsilon=0.0)
    rnd = _r.Random(7)
    dirs = []
    for i in range(rays):
        u1, u2 = (i + rnd.random()) / rays, rnd.random()
        rr = _m.sqrt(u1)
        th = 2 * _m.pi * u2
        dirs.append(_V((rr * _m.cos(th), rr * _m.sin(th), _m.sqrt(max(0.0, 1 - u1)))))
    ca = me.color_attributes[attr]
    R3 = Mw.to_3x3()
    tot, n = 0.0, 0
    for p in me.polygons:
        nrm = (R3 @ p.normal).normalized()
        if nrm.length < 0.5:
            continue
        cen = Mw @ p.center
        rot = nrm.to_track_quat("Z", "Y").to_matrix()
        for li in p.loop_indices:
            v = verts[me.loops[li].vertex_index]
            q = v + (cen - v) * inset + nrm * 1e-3
            hit = 0
            for d in dirs:
                if bvh.ray_cast(q, rot @ d, dist)[0] is not None:
                    hit += 1
            r = min(1.0, hit / rays * 1.4)
            c = ca.data[li].color
            ca.data[li].color = (r, c[1], c[2], 1.0)
            tot += r
            n += 1
    me.update()
    return {"corners": n, "R_mean": round(tot / max(n, 1), 3)}


def stick_wear_ends(o):
    """r3: a smooth, oiled turned stick has no pale worn arrises (the sheet's close-up): Wear G = 0 everywhere; the
    grime (R) and the ground dirt (B) stay."""
    me = o.data
    ca = me.color_attributes["Wear"]
    for p in me.polygons:
        for li in p.loop_indices:
            c = ca.data[li].color
            ca.data[li].color = (min(c[0], 0.5), 0.0, c[2], 1.0)
    return {"faces_with_edge_wear": 0, "faces": len(me.polygons), "grime_capped": 0.5}


def drum_wear_bulge(o):
    """r2 (judges: 'worn highlights on the bulge'): the lacquer's Wear G across the belly, patchy (3D noise), so the
    library wear maths lifts it by up to +17 % in broken patches; the hide face keeps G = 0 (only grime there)."""
    from mathutils.noise import noise as pn
    me = o.data
    ca = me.color_attributes["Wear"]
    idx = {m.name: i for i, m in enumerate(me.materials)}
    lac, hid = idx.get(LAC), idx.get(HIDE)
    n_lac = n_worn = 0
    for poly in me.polygons:
        if poly.material_index not in (lac, hid):
            continue
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            c = ca.data[li].color
            if poly.material_index == hid:
                ca.data[li].color = (c[0], 0.0, c[2], 1.0)
                continue
            band = math.exp(-(co.x / 0.34) ** 2)
            nz = 0.5 + 0.5 * pn(Vector((co.x * 5.0, co.y * 5.0, co.z * 5.0)))
            nz2 = 0.5 + 0.5 * pn(Vector((co.x * 17.0 + 3.1, co.y * 17.0, co.z * 17.0)))
            g = max(c[1], min(1.0, band * (0.35 + 1.1 * nz) * (0.7 + 0.5 * nz2)))
            ca.data[li].color = (c[0], g, c[2], 1.0)
            n_lac += 1
            n_worn += g > 0.5
    return {"lacquer_corners": n_lac, "corners_G_over_0.5": n_worn}


def measure(objs, instances, drum_meta):
    out = {"pieces": {}}
    for name, o in objs.items():
        me = o.data
        co = [v.co for v in me.vertices]
        by_mat = {}
        for pl in me.polygons:
            by_mat.setdefault(me.materials[pl.material_index].name, set()).update(pl.vertices)
        mm = {}
        for mname, vids in by_mat.items():
            pts = [co[i] for i in vids]
            mm[mname] = {"bbox_min": [round(min(p[i] for p in pts), 4) for i in range(3)],
                         "bbox_max": [round(max(p[i] for p in pts), 4) for i in range(3)]}
        out["pieces"][name] = {
            "bbox_min": [round(min(p[i] for p in co), 4) for i in range(3)],
            "bbox_max": [round(max(p[i] for p in co), 4) for i in range(3)],
            "dims": [round(max(p[i] for p in co) - min(p[i] for p in co), 4) for i in range(3)],
            "verts": len(me.vertices), "tris": sum(len(pl.vertices) - 2 for pl in me.polygons),
            "materials": mm, "ucx_hulls": len([c for c in o.children if c.name.startswith("UCX_")])}
    d = objs["SM_DKP_Taiko_Drum"].data
    mat_v = {}
    for pl in d.polygons:
        mat_v.setdefault(d.materials[pl.material_index].name, set()).update(pl.vertices)
    rr = lambda i: math.hypot(d.vertices[i].co.y, d.vertices[i].co.z)  # noqa: E731
    belly = max(rr(i) for i in mat_v[LAC])
    face_flat = [i for i in mat_v[HIDE] if abs(abs(d.vertices[i].co.x) - X_FACE) < 0.0006 and rr(i) < R_FACE + 0.002]
    face_r = max(rr(i) for i in face_flat)
    lip_r = max(rr(i) for i in mat_v[HIDE])
    collar_x = [abs(d.vertices[i].co.x) for i in mat_v[COLLAR] if rr(i) < body_r(abs(d.vertices[i].co.x)) + 0.004
                and abs(d.vertices[i].co.x) < 0.64]
    s = objs["SM_DKP_Taiko_Stand"].data
    sad = []
    for v in s.vertices:
        if CRADLE_X0 - 0.01 < abs(v.co.x) < CRADLE_X1 + 0.01 and abs(v.co.y) < CRADLE_FLAT_Y + 1e-3 and v.co.z > 0.6:
            sad.append(math.hypot(v.co.y, v.co.z - DRUM_Z) - body_r(abs(v.co.x)))
    xin, yin = POST_X - POST_W / 2, POST_Y - POST_W / 2
    r_at = body_r(xin)
    post_clear = (DRUM_Z - math.sqrt(r_at * r_at - yin * yin)) - post_top()
    # ring handle clearance to the barrel (min over ring vertices of radius - body radius at their x)
    ring_gap = []
    for i in mat_v[IRN]:
        co = d.vertices[i].co
        if abs(co.x) < 0.1 and abs(co.y) > 0.55 and co.z < -0.0:
            ring_gap.append(math.hypot(co.y, co.z) - body_r(abs(co.x)))
    drum_inst = next(i for i in instances if i["piece"] == "SM_DKP_Taiko_Drum")
    stand_inst = next(i for i in instances if i["piece"] == "SM_DKP_Taiko_Stand")
    stk = out["pieces"]["SM_DKP_Taiko_Stick"]
    sv = objs["SM_DKP_Taiko_Stick"].data.vertices
    stick_d = [2 * max(math.hypot(v.co.y, v.co.z) for v in sv if abs(v.co.x - xx) < 0.03) for xx in (0.0, STICK_L)]
    tk = drum_meta["tacks"]
    out["summary"] = {
        "drum_belly_diameter_m": round(2 * belly, 4),
        "drum_head_flat_face_diameter_m": round(2 * face_r, 4),
        "drum_lip_outer_diameter_m": round(2 * lip_r, 4),
        "drum_length_m": out["pieces"]["SM_DKP_Taiko_Drum"]["dims"][0],
        "drum_length_over_belly": round(out["pieces"]["SM_DKP_Taiko_Drum"]["dims"][0] / (2 * belly), 3),
        "collar_torn_edge_x_range_m": [round(min(collar_x), 4), round(max(collar_x), 4)] if collar_x else None,
        "tacks_total": len(tk), "tacks_per_head": N_TACKS,
        "tack_dome_diameter_range_m": [round(2 * min(t[3] for t in tk), 4), round(2 * max(t[3] for t in tk), 4)],
        "tack_tris_each": 30,
        "ring_handles": drum_meta["rings"],
        "ring_outer_diameter_m": round(2 * (RING_R + RING_T), 4), "ring_tube_diameter_m": round(2 * RING_T, 4),
        "ring_min_gap_to_barrel_m": round(min(ring_gap), 4) if ring_gap else None,
        "drum_centre_above_stand_base_m": DRUM_Z,
        "drum_bottom_above_stand_base_m": round(DRUM_Z - belly, 4),
        "drum_top_world_z": drum_inst["bbox_min_max"][5],
        "drum_top_above_plinth_m": round(drum_inst["bbox_min_max"][5] - PLINTH_TOP, 4),
        "pavilion_eave_z_spec": 3.25, "clearance_drum_top_to_eave_m": round(3.25 - drum_inst["bbox_min_max"][5], 4),
        "stand_footprint_xy_m": out["pieces"]["SM_DKP_Taiko_Stand"]["dims"][:2],
        "stand_height_m": out["pieces"]["SM_DKP_Taiko_Stand"]["dims"][2],
        "stand_world_bbox": stand_inst["bbox_min_max"],
        "saddle_gap_min_max_m": [round(min(sad), 4), round(max(sad), 4)] if sad else None,
        "post_top_below_drum_surface_m": round(post_clear, 4),
        "stick_length_m": stk["dims"][0], "stick_diameter_grip_strike_m": [round(x, 4) for x in stick_d],
        "stick_length_over_diameter": [round(STICK_L / x, 2) for x in stick_d],
        "stick_poses": [i["pose"] for i in instances if i["piece"] == "SM_DKP_Taiko_Stick"],
        "tris": {k: v["tris"] for k, v in out["pieces"].items()},
    }
    return out


main()
