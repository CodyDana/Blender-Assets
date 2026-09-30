"""ROUND 5 (2026-09-29): EMBLEM PLAQUES + the WEATHERING / MOSS DECAL PLAN (the dressing track, SM_DKD_* / T_DKD_*).

1. EMBLEM. The user's own emblem (the armory's, Exports/ArmoryKit/Textures/T_AK_Emblem*.png; copied byte for byte as
   T_DKD_Emblem_{M,BC,N,ORM}.png, pixels unchanged) as a period crest plaque: a black-lacquered round timber board with
   the emblem RAISED on it (real relief geometry traced from the emblem mask, crisp small bevels), gilt as the armory
   made it (T_DKD_Emblem_BC: gold on black; ORM metal 1 on the emblem, glossy black lacquer around it).
     SM_DKD_EmblemPlaque_Hall  0.90 m board: on the hall's UPPER GABLES (the hip-and-gable's tsuma triangles, where a
                               house crest sits), centred on the king post over the collar beam, west AND east gable (the
                               compound is mirror-symmetric for P1 / P2). The hall has no front-facing gable: its upper
                               roof's gables face west and east (hall sheet, layout_hall.json 'gable_face_x').
     SM_DKD_EmblemPlaque_Gate  0.46 m board: on the gate's STREET face (the approach road, the house's public face), hung
                               on the centre peg of the front eave beam at X 22 (the only face above the opening that is
                               not behind the eave beam or under the rafters: measured, dressing/BUILD_NOTES.md).
   No banners or cloth (no reference shows any), no text.
2. DECALS. decals.json: the six decal materials (T_DKD_Decal_*, made by make_decal_textures.py) and EVERY placement
   measured here by ray casts against the composed compound (Assets/Dojo/DojoShowcase.blend, read-only), in the grey-box
   frame (metres, X east, Y north, Z up) with the Unreal transform computed ((x, -y, z) * 100; decal local +X = the
   projection direction into the surface, +Z = the texture's up; DecalSize = half extents). The Blender review renders
   show them as ray-projected preview meshes (collection DecalPreview, never exported).

Run: blender -b --factory-startup --python Scripts/dojo/dressing/build_dressing.py -- [--no-export] [--no-preview]
Out: Assets/Dojo/DojoDressing.blend (Kit = the showcase kit + the plaques, Assembly = the showcase instances + ours,
     DecalPreview), Exports/DojoKit/Dressing/{SM_DKD_*.fbx, Textures/T_DKD_Emblem_*},
     WorkFiles/dojo/build/dressing/{layout_dressing.json, layout_dressing_checks.json, decals.json, qa_report.json,
     export_report.json, dressing_report.json, clearance.json}
"""
import hashlib
import json
import math
import random
import shutil
import sys
import time
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for _p in (HERE, ROOT / "Scripts", ROOT / "Scripts" / "dojo", ROOT / "Scripts" / "dojo" / "roof"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import dkd_common as C  # noqa: E402
from pipeline.export_fbx import export_fbx  # noqa: E402
from pipeline.lock import assert_owner  # noqa: E402
from pipeline.qa_check import qa_check  # noqa: E402
import kit_mesh as KM  # noqa: E402

ARGS = C.args()
T0 = time.time()
MAT_PLAQUE = "M_DKD_EmblemPlaque"
EMBLEM_FILES = {"T_AK_Emblem.png": "T_DKD_Emblem_M.png", "T_AK_Emblem_BC.png": "T_DKD_Emblem_BC.png",
                "T_AK_Emblem_N.png": "T_DKD_Emblem_N.png", "T_AK_Emblem_ORM.png": "T_DKD_Emblem_ORM.png"}
# plaque designs: board diameter = the emblem image's full width (the emblem ring's outer edge is at 0.911 of the
# radius, so a black lacquer border shows round it)
PLAQUES = {
    # round 5 fix f1 (both judges: the hall plaque ran up under the bargeboard with the tie-beam block poking out under
    # it): 0.90 -> 0.64 m, clear of both (top +8.25 under the bargeboard's +8.4 there, bottom +7.61 over the block's
    # +7.453)
    "SM_DKD_EmblemPlaque_Hall": dict(D=0.64, T=0.040, relief=0.009, bevel=0.002, chamfer=0.008,
                                     note="0.64 m crest plaque for the hall's upper gables (west + east)"),
    "SM_DKD_EmblemPlaque_Gate": dict(D=0.46, T=0.035, relief=0.008, bevel=0.0018, chamfer=0.007,
                                     note="0.46 m crest plaque for the gate's street face (hung on the eave beam's "
                                          "centre peg)"),
}
# placements (grey-box frame). Plaque local frame: the disc centre on its BACK plane is the pivot, the face looks
# along local -Y, the emblem's top along +Z. rot_z -90 faces -X (west), +90 faces +X (east), 0 faces -Y (street).
# Measured fits (probe of DojoShowcase.blend, BUILD_NOTES ROUND 5): the west gable's plaster face is X 14.600, its king
# post face 14.550, collar beam face 14.555 (z 7.842-7.992), the block on the tie beam 14.510 at z 7.233-7.453 (under
# the plaque); apex of the plaster +8.729, gable foot +6.943; east mirrored about X 22. The gate's street eave beams:
# upper y -1.890 (z 3.20-3.36), lower y -1.840 (z 3.06-3.20) with 11 x 10 cm pegs every 0.4 m reaching y -1.940
# (z 3.10-3.20), one at X 22.0; above the beams the gate roof's rafters (X 21.73-21.82 / 22.18-22.27 either side of
# X 22) and its soffit boards come down to about +3.22 in the plaque's plane (y -1.95..-1.99): the plaque's top stays
# under that (clearance.json: min gap 5 mm, no intersection). Relief measured: hall 9.5 mm, gate 6.2 mm (the curve's
# bevel eats part of the design value).
PLACE = [
    ("SM_DKD_EmblemPlaque_Hall", (14.545, 29.0, 7.93), -90.0, "hall upper gable, west: on the king post over the "
                                                                "collar beam, 5 mm off the king post face"),
    ("SM_DKD_EmblemPlaque_Hall", (29.455, 29.0, 7.93), 90.0, "hall upper gable, east (mirror about X 22)"),
    ("SM_DKD_EmblemPlaque_Gate", (22.0, -1.945, 2.975), 0.0, "gate street face: hung on the eave beam's centre peg "
                                                              "(X 22), under the eave's soffit boards (their underside "
                                                              "is about +3.22 in the plaque's plane) and between the two "
                                                              "rafters flanking X 22: top +3.205, bottom +2.745"),
]


# ------------------------------------------------------------------------------------------------ emblem tracing
def load_mask(path, res=512):
    """The emblem mask as a float array (rows = image rows from the TOP), full res and averaged down to res."""
    im = bpy.data.images.load(str(path), check_existing=False)
    w, h = im.size
    px = np.empty(w * h * 4, np.float32)
    im.pixels.foreach_get(px)
    bpy.data.images.remove(im)
    full = px.reshape(h, w, 4)[::-1, :, 0].astype(np.float64)       # bpy rows go bottom-up: flip to top-down
    k = w // res
    small = full.reshape(res, k, res, k).mean(axis=(1, 3))
    return full, small


def march(f):
    """Marching squares on f (> 0 inside), rows top-down. Returns closed loops of (col, row) float points."""
    H, W = f.shape
    F = np.full((H + 2, W + 2), -0.5)
    F[1:-1, 1:-1] = f
    H, W = F.shape
    tl, tr, br, bl = F[:-1, :-1] > 0, F[:-1, 1:] > 0, F[1:, 1:] > 0, F[1:, :-1] > 0
    case = tl * 1 + tr * 2 + br * 4 + bl * 8
    ii, jj = np.nonzero((case > 0) & (case < 15))

    def pt(edge):
        kind, i, j = edge
        if kind == "h":                                  # between (i, j) and (i, j + 1)
            a, b = F[i, j], F[i, j + 1]
            t = a / (a - b)
            return (j + t, i)
        a, b = F[i, j], F[i + 1, j]                     # between (i, j) and (i + 1, j)
        t = a / (a - b)
        return (j, i + t)
    adj = {}

    def seg(a, b):
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    for i, j in zip(ii.tolist(), jj.tolist()):
        c = int(case[i, j])
        T_, R_, B_, L_ = ("h", i, j), ("v", i, j + 1), ("h", i + 1, j), ("v", i, j)
        centre = (F[i, j] + F[i, j + 1] + F[i + 1, j + 1] + F[i + 1, j]) / 4 > 0
        table = {1: [(L_, T_)], 2: [(T_, R_)], 3: [(L_, R_)], 4: [(R_, B_)], 6: [(T_, B_)], 7: [(L_, B_)],
                 8: [(B_, L_)], 9: [(T_, B_)], 11: [(R_, B_)], 12: [(L_, R_)], 13: [(T_, R_)], 14: [(L_, T_)],
                 5: [(T_, R_), (B_, L_)] if centre else [(L_, T_), (R_, B_)],
                 10: [(L_, T_), (R_, B_)] if centre else [(T_, R_), (B_, L_)]}
        for a, b in table[c]:
            seg(a, b)
    loops, used = [], set()
    for start in list(adj):
        if start in used:
            continue
        loop, prev, cur = [start], None, start
        used.add(start)
        while True:
            nxt = [n for n in adj[cur] if n != prev and n not in used]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            used.add(cur)
            loop.append(cur)
        if len(loop) > 8:
            loops.append(np.array([pt(e) for e in loop]) - 1.0)   # remove the pad
    return loops


def rdp(p, eps):
    if len(p) < 3:
        return p
    a, b = p[0], p[-1]
    ab = b - a
    n = np.hypot(*ab)
    d = (np.abs(ab[0] * (p[:, 1] - a[1]) - ab[1] * (p[:, 0] - a[0])) / n) if n > 1e-12 else np.hypot(*(p - a).T)
    k = int(np.argmax(d))
    if d[k] > eps:
        return np.vstack([rdp(p[:k + 1], eps)[:-1], rdp(p[k:], eps)])
    return np.vstack([a, b])


def simplify_loop(loop, eps):
    k = len(loop) // 2
    a = rdp(np.vstack([loop[:k + 1]]), eps)
    b = rdp(np.vstack([loop[k:], loop[:1]]), eps)
    return np.vstack([a[:-1], b[:-1]])


def trace_emblem():
    full, small = load_mask(C.ARMORY_TEX / "T_AK_Emblem.png", 512)
    loops = march(small - 0.5)
    res = small.shape[0]
    out = []
    for lp in loops:
        s = simplify_loop(lp, 0.35)
        uv = np.column_stack([(s[:, 0] + 0.5) / res, 1.0 - (s[:, 1] + 0.5) / res])   # (u, v), v up
        area = 0.5 * np.sum(uv[:, 0] * np.roll(uv[:, 1], -1) - np.roll(uv[:, 0], -1) * uv[:, 1])
        out.append({"uv": uv, "area": float(area), "n_raw": len(lp), "n": len(s)})
    return full, out


# ------------------------------------------------------------------------------------------------ materials
def plaque_material():
    m = bpy.data.materials.get(MAT_PLAQUE)
    if m:
        return m
    m = bpy.data.materials.new(MAT_PLAQUE)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")

    def img(name, noncolor):
        n = nt.nodes.new("ShaderNodeTexImage")
        im = bpy.data.images.load(str(C.TEX_DIR / name), check_existing=True)
        if noncolor:
            im.colorspace_settings.name = "Non-Color"
        n.image = im
        return n
    bc, orm, nrm = img("T_DKD_Emblem_BC.png", False), img("T_DKD_Emblem_ORM.png", True), img("T_DKD_Emblem_N.png", True)
    nt.links.new(bc.outputs["Color"], bsdf.inputs["Base Color"])
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(orm.outputs["Color"], sep.inputs["Color"])
    rm = nt.nodes.new("ShaderNodeMath")
    rm.operation = "MULTIPLY"
    rm.use_clamp = True
    rm.inputs[1].default_value = PLAQUE_ROUGH_MULT
    nt.links.new(sep.outputs[1], rm.inputs[0])
    nt.links.new(rm.outputs[0], bsdf.inputs["Roughness"])
    nt.links.new(sep.outputs[2], bsdf.inputs["Metallic"])
    sn = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(nrm.outputs["Color"], sn.inputs["Color"])
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    nt.links.new(sn.outputs[1], inv.inputs[1])                  # DirectX -> OpenGL green for Blender
    cb = nt.nodes.new("ShaderNodeCombineColor")
    nt.links.new(sn.outputs[0], cb.inputs[0])
    nt.links.new(inv.outputs[0], cb.inputs[1])
    nt.links.new(sn.outputs[2], cb.inputs[2])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(cb.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def back_material():
    """round 5 f1: the plaque's back cap, the shared library's dark timber (slot name = the library recipe)."""
    m = bpy.data.materials.get("M_DJ_TimberDark")
    if m is None:
        m = bpy.data.materials.new("M_DJ_TimberDark")
        m.use_nodes = True
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Base Color"].default_value = (0.09, 0.06, 0.04, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.8
    return m


PLAQUE_ROUGH_MULT = 2.0   # r1: x2 on the armory's ORM (gilt 0.30 -> 0.60, lacquer 0.20 -> 0.40): at 0.3 the gilt mirrored
                          # the dark eave / gable surroundings and read black in shade (r0 renders); weathered exterior
PLAQUE_RECIPE = {
    MAT_PLAQUE: {"master": "M_DJ_Lib_Opaque", "kit": "dressing", "ue_dir": f"{C.UE_DIR}/Materials",
                 "textures": {"BC": "T_DKD_Emblem_BC", "ORM": "T_DKD_Emblem_ORM", "N": "T_DKD_Emblem_N"},
                 "scalars": {"RoughMult": PLAQUE_ROUGH_MULT, "NormalStrength": 1.0}, "vectors": {"Tint": [1.0, 1.0, 1.0],
                                                                                   "TileM": [1.0, 1.0, 0.0, 0.0]},
                 "switches": {"UseWear": False},
                 "note": "the user's armory emblem (T_AK_Emblem_* copied byte for byte): gilt emblem (metal 1, rough "
                         "0.30 x RoughMult 2 = 0.60) on black lacquer (0.20 x 2 = 0.40: weathered, not mirror); UV0 0-1 across the board face, the relief's "
                         "walls pulled onto the gilt texels, the board's edge / back on black corner texels"},
}


# ------------------------------------------------------------------------------------------------ plaque mesh
def relief_mesh(loops, D, relief, bevel, name):
    """The emblem as raised relief: a 2D filled curve of the traced loops, extruded, small round bevel; returns a
    mesh in plaque-local coordinates with the relief base at y = 0 rising toward -y (caller offsets it)."""
    cu = bpy.data.curves.new(name + "_crv", "CURVE")
    cu.dimensions = "2D"
    cu.fill_mode = "FRONT"
    cu.resolution_u = 1
    cu.extrude = max(relief / 2 - bevel, 0.0005)
    cu.bevel_depth = bevel
    cu.bevel_resolution = 1
    cu.offset = 0.0
    for lp in loops:
        uv = lp["uv"]
        sp = cu.splines.new("POLY")
        sp.points.add(len(uv) - 1)
        for k, (u, v) in enumerate(uv):
            sp.points[k].co = ((u - 0.5) * D, (v - 0.5) * D, 0.0, 1.0)
        sp.use_cyclic_u = True
    ob = bpy.data.objects.new(name + "_crvobj", cu)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)
    bm = bmesh.new()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    zmin = min(v.co.z for v in bm.verts)
    zmax = max(v.co.z for v in bm.verts)
    back = [f for f in bm.faces if f.normal.z < -0.99]                 # nothing faces the board
    if back:
        bmesh.ops.delete(bm, geom=back, context="FACES")
    for v in bm.verts:                                                 # curve (x, y, z) -> plaque (x, -(z - zmin), y)
        x, y, z = v.co
        v.co = Vector((x, -(z - zmin), y))       # a proper rotation (det +1): the curve's normals stay outward
    return bm, zmax - zmin


def board_bm(bm, D, T, ch, segs=128):
    """The round board: back plane y = 0, face y = -T, a 45 deg chamfer ch on the front edge; face ngon, sides, back."""
    R = D / 2
    rings = []
    for (r, y) in ((R - ch, -T), (R, -T + ch), (R, 0.0)):
        rings.append([bm.verts.new((r * math.cos(2 * math.pi * k / segs), y, r * math.sin(2 * math.pi * k / segs)))
                      for k in range(segs)])
    face = bm.faces.new(list(reversed(rings[0])))
    face.normal_update()
    if face.normal.y > 0:
        face.normal_flip()
    side = []
    for a, b in ((rings[0], rings[1]), (rings[1], rings[2])):
        for k in range(segs):
            k2 = (k + 1) % segs
            side.append(bm.faces.new((a[k], a[k2], b[k2], b[k])))
    backf = bm.faces.new(rings[2])
    bmesh.ops.recalc_face_normals(bm, faces=[face] + side + [backf])
    return face, side, backf


def build_plaque(name, spec, loops, mask_full, coll_):
    D, T, relief, bevel, ch = spec["D"], spec["T"], spec["relief"], spec["bevel"], spec["chamfer"]
    rbm, rh = relief_mesh(loops, D, relief, bevel, name)
    for v in rbm.verts:
        v.co.y -= (T - 0.001)                                       # 1 mm into the board face
    me_r = bpy.data.meshes.new(name + "_relief")
    rbm.to_mesh(me_r)
    rbm.free()
    bm = bmesh.new()
    bm.from_mesh(me_r)
    bpy.data.meshes.remove(me_r)
    for lay in list(bm.loops.layers.uv.values()):                   # the curve's own UV layer (r0 bug: it stayed
        bm.loops.layers.uv.remove(lay)                              # channel 0 and ours became 'UVMap.001')
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)        # the curve's bevel rings share points
    ng = [f for f in bm.faces if len(f.verts) > 4]
    if ng:
        bmesh.ops.triangulate(bm, faces=ng)
    relief_faces = set(bm.faces)
    face, side, backf = board_bm(bm, D, T, ch)
    uvl = bm.loops.layers.uv.new("UVMap")
    Hm, Wm = mask_full.shape

    def planar(co):
        return (co.x / D + 0.5, co.z / D + 0.5)
    inside = mask_full > 0.99

    def nudge(u, v, rad=6):
        """Pull a relief UV onto a gilt texel (the traced edge sits on the anti-aliased boundary)."""
        cx, cy = int(round(u * (Wm - 1))), int(round((1 - v) * (Hm - 1)))
        if 0 <= cy < Hm and 0 <= cx < Wm and inside[cy, cx]:
            return u, v
        y0, y1, x0, x1 = max(0, cy - rad), min(Hm, cy + rad + 1), max(0, cx - rad), min(Wm, cx + rad + 1)
        win = inside[y0:y1, x0:x1]
        if not win.any():
            return u, v
        yy, xx = np.nonzero(win)
        k = int(np.argmin((yy + y0 - cy) ** 2 + (xx + x0 - cx) ** 2))
        return (xx[k] + x0) / (Wm - 1), 1 - (yy[k] + y0) / (Hm - 1)
    cache = {}
    for f in relief_faces:
        for lp in f.loops:
            key = lp.vert.index
            if key not in cache:
                cache[key] = nudge(*planar(lp.vert.co))
            lp[uvl].uv = cache[key]
    for lp in face.loops:
        lp[uvl].uv = planar(lp.vert.co)
    segs = len(side) // 2
    for i, f in enumerate(side):                                    # edge + chamfer: a strip in the black corner
        for lp in f.loops:
            a = (math.atan2(lp.vert.co.z, lp.vert.co.x) % (2 * math.pi)) / (2 * math.pi)
            lp[uvl].uv = (0.004 + 0.05 * a, 0.004 + 0.02 * (-lp.vert.co.y / T))
    for lp in backf.loops:                                           # round 5 f1: the back is a TIMBER cap (library
        lp[uvl].uv = (lp.vert.co.x * 2.0, lp.vert.co.z * 2.0)       # TimberDark, tile units): the gate plaque's back
    backf.material_index = 1                                         # read as a black disc from the courtyard
    bmesh.ops.triangulate(bm, faces=[face, backf], quad_method="BEAUTY", ngon_method="BEAUTY")
    bm.normal_update()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = False
    me.materials.append(plaque_material())
    me.materials.append(back_material())
    obj = bpy.data.objects.new(name, me)
    coll_.objects.link(obj)
    # UCX: the board + relief as one convex hull (a 24-gon prism)
    hb = bmesh.new()
    front = -(T + rh)
    for k in range(24):
        a = 2 * math.pi * k / 24
        for y in (0.0, front):
            hb.verts.new((D / 2 * math.cos(a), y, D / 2 * math.sin(a)))
    bmesh.ops.convex_hull(hb, input=list(hb.verts))
    for v in [v for v in hb.verts if not v.link_faces]:
        hb.verts.remove(v)
    hm = bpy.data.meshes.new(f"UCX_{name}_00")
    hb.to_mesh(hm)
    hb.free()
    h = bpy.data.objects.new(f"UCX_{name}_00", hm)
    coll_.objects.link(h)
    h.parent = obj
    h.hide_render = True
    h.display_type = "WIRE"
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    return obj, {"tris": tris, "relief_front_y": round(front, 4), "board_diameter": D, "board_t": T,
                 "relief_m": round(rh, 4), "relief_faces": len(relief_faces)}


# ------------------------------------------------------------------------------------------------ ray casting
class Caster:
    """scene.ray_cast over the Assembly instances only (Kit pieces, UCX, boundary, plaques and previews hidden)."""

    def __init__(self):
        self.sc = bpy.context.scene
        self.hidden = []
        for o in list(bpy.context.view_layer.objects):
            keep = ("__" in o.name and o.type == "MESH" and not C.piece_of(o).startswith("SM_DGB_Boundary")
                    and not C.piece_of(o).startswith("SM_DKD_"))
            if not keep:
                o.hide_set(True)
                self.hidden.append(o)
        self.dg = bpy.context.evaluated_depsgraph_get()

    IGNORE = ("SM_DKG_Tuft", "SM_DKG_Pebbles", "SM_DKP_Modern_Wire")    # no-collision dressing the rays pass through
    NOT_GROUND = IGNORE + ("SM_DKP_", "SM_DKS_Rack")                    # props standing on the ground

    def cast(self, origin, direction, dist=50.0, ignore=IGNORE):
        o, d = Vector(origin), Vector(direction).normalized()
        left = dist
        for _ in range(12):
            hit, loc, nrm, idx, ob, mat = self.sc.ray_cast(self.dg, o, d, distance=left)
            if not hit:
                return None
            if C.piece_of(ob).startswith(ignore):
                step = (Vector(loc) - o).length + 0.002
                o = Vector(loc) + d * 0.002
                left -= step
                if left <= 0:
                    return None
                continue
            return {"p": Vector(loc), "n": Vector(nrm).normalized(), "piece": C.piece_of(ob), "obj": ob.name}
        return None

    def restore(self):
        for o in self.hidden:
            o.hide_set(False)


def axis_snap(n, tol_deg=6.0):
    """Snap a nearly axis-aligned normal onto the axis (the rubble / plaster relief tilts the hit normal)."""
    for ax in (Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))):
        for s in (1, -1):
            if n.dot(ax * s) > math.cos(math.radians(tol_deg)):
                return ax * s
    return n


# ------------------------------------------------------------------------------------------------ decal plan
DECAL_MATS = {
    "MossFoot":   {"nominal_m": [4.0, 1.0], "opacity": 1.0, "rough_mult": 1.0, "normal_strength": 1.0,
                   "use": "moss cushions + damp at a wall foot / the rubble footing (texture bottom row at the ground)"},
    "RainStreak": {"nominal_m": [2.0, 1.0], "opacity": 0.9, "rough_mult": 1.0, "normal_strength": 0.5,
                   "use": "runoff streaks hanging from a drip line: under the wall caps and eaves (top row at the drip)"},
    "Grime":      {"nominal_m": [1.0, 1.0], "opacity": 0.85, "rough_mult": 1.0, "normal_strength": 0.7,
                   "use": "splash-back grime at post bases (bottom row at the post foot) and door thresholds (bottom "
                          "row at the door, projected down)"},
    "Lichen":     {"nominal_m": [1.0, 1.0], "opacity": 0.8, "rough_mult": 1.0, "normal_strength": 1.0,
                   "use": "crustose lichen on roof tiles, wall caps and the stone lanterns"},
    "WaterStain": {"nominal_m": [1.0, 1.0], "opacity": 0.9, "rough_mult": 1.0, "normal_strength": 0.6,
                   "use": "the ground stain under a downpipe shoe (bottom row at the shoe, up = the outflow)"},
    "WornPath":   {"nominal_m": [1.5, 1.5], "opacity": 0.8, "rough_mult": 1.0, "normal_strength": 1.0,
                   "use": "trodden gravel where feet leave the paving (hall stair, gate)"},
}


class Plan:
    def __init__(self, caster):
        self.c = caster
        self.items = []
        self.skipped = []
        self.rng = random.Random(5901)

    def add(self, mat, p, n, up, w, h, depth, source, extra=None):
        n = Vector(n).normalized()
        up = Vector(up)
        up = (up - n * up.dot(n)).normalized()
        right = up.cross(n)                    # looking at the surface (against n): +right is to the viewer's right
        k = sum(1 for i in self.items if i["material"] == f"M_DKD_Decal_{mat}") + 1
        it = {"id": f"{mat}_{k:02d}", "material": f"M_DKD_Decal_{mat}",
              "centre": [round(v, 4) for v in p], "normal": [round(v, 4) for v in n], "up": [round(v, 4) for v in up],
              "right": [round(v, 4) for v in right], "size_m": [round(w, 3), round(h, 3)], "depth_m": round(depth, 3),
              "flip_u": bool(self.rng.random() < 0.5), "source": source}
        x_ue, z_ue = C.ue_dir(-n), C.ue_dir(up)
        roll, pitch, yaw = C.ue_rotator_from_axes(x_ue, z_ue)
        it["ue"] = {"location_cm": C.ue_loc_cm(p), "rotation_deg": {"roll": roll, "pitch": pitch, "yaw": yaw},
                    "decal_size_cm": [round(depth * 50, 2), round(w * 50, 2), round(h * 50, 2)],
                    "scale": [1.0, -1.0 if it["flip_u"] else 1.0, 1.0]}
        if extra:
            it.update(extra)
        self.items.append(it)
        return it

    def skip(self, mat, why, **kw):
        self.skipped.append({"material": mat, "why": why, **kw})

    # -- walls: a horizontal ray finds the face; the ground or the drip above sets the height
    def wall(self, mat, origin, direction, w, h, anchor, expect, probe_z, depth=0.4, max_up=2.6, note=""):
        o = Vector((origin[0], origin[1], probe_z))
        r = self.c.cast(o, direction, 30.0)
        if r is None or not r["piece"].startswith(expect):
            self.skip(mat, "face not found / wrong piece", origin=list(origin), hit=r and r["piece"])
            return None
        n = -Vector(direction).normalized()          # the perimeter / building walls are axis-aligned planes: the
        p = r["p"]                                   # rubble pillows' own tilts must not tilt the decal
        if anchor == "ground":
            g = self.c.cast(p + n * 0.35 + Vector((0, 0, 1.0)), (0, 0, -1), 4.0, ignore=Caster.NOT_GROUND)
            gz = g["p"].z if g else 0.0
            cz = gz + 0.02 + h / 2
            src = f"{note}face {r['piece']} at {tuple(round(v, 3) for v in p)}, ground {round(gz, 3)} ({g and g['piece']})"
        else:                                                 # 'under': hang from the drip line above the face
            u = self.c.cast(p + n * 0.03, (0, 0, 1), max_up)
            if u is None:
                self.skip(mat, "no drip line above", origin=list(origin), face=r["piece"])
                return None
            cz = u["p"].z - 0.015 - h / 2
            src = f"{note}face {r['piece']} at {tuple(round(v, 3) for v in p)}, drip {round(u['p'].z, 3)} ({u['piece']})"
        c = Vector((p.x, p.y, cz))
        return self.add(mat, c, n, (0, 0, 1), w, h, depth, src)

    def floor(self, mat, xy, up, w, h, z_from=2.0, depth=0.4, expect=None, note=""):
        r = self.c.cast((xy[0], xy[1], z_from), (0, 0, -1), z_from + 3.0)
        if r is None or (expect and not r["piece"].startswith(expect)):
            self.skip(mat, "floor not found / wrong piece", xy=list(xy), hit=r and r["piece"])
            return None
        return self.add(mat, r["p"], axis_snap(r["n"], 3.0), up, w, h, depth,
                        f"{note}floor {r['piece']} at z {round(r['p'].z, 3)}")

    def roof(self, mat, xy, w, h, expect, z_from=20.0, depth=0.5, note=""):
        r = self.c.cast((xy[0], xy[1], z_from), (0, 0, -1), z_from + 2.0)
        if r is None or not r["piece"].startswith(expect):
            self.skip(mat, "roof not found / wrong piece", xy=list(xy), hit=r and r["piece"])
            return None
        n = r["n"]
        up = Vector((0, 0, 1)) - n * n.z                      # uphill (texture top up the slope)
        if up.length < 1e-3:
            up = Vector((0, 1, 0))
        return self.add(mat, r["p"], n, up, w, h, depth, f"{note}surface {r['piece']} at "
                        f"{tuple(round(v, 3) for v in r['p'])}, slope {round(math.degrees(math.acos(max(-1, min(1, n.z)))), 1)} deg")


def loose_parts(obj):
    """World-space bounding boxes of the loose parts of an instance's mesh."""
    me = obj.data
    M = obj.matrix_world
    n = len(me.vertices)
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for e in me.edges:
        a, b = find(e.vertices[0]), find(e.vertices[1])
        if a != b:
            parent[a] = b
    co = np.array([M @ v.co for v in me.vertices])
    roots = np.array([find(i) for i in range(n)])
    out = []
    for r in np.unique(roots):
        pts = co[roots == r]
        out.append(np.concatenate([pts.min(0), pts.max(0)]))
    return out


def find_posts(piece, min_h=1.6, max_w=0.45, max_bottom=1.2, min_w=0.10):
    posts = []
    for o in C.instances_of(piece):
        for bb in loose_parts(o):
            dx, dy, dz = bb[3] - bb[0], bb[4] - bb[1], bb[5] - bb[2]
            if (dz >= min_h and max(dx, dy) <= max_w and min(dx, dy) >= min_w and max(dx, dy) <= 2.2 * min(dx, dy)
                    and bb[2] <= max_bottom):
                posts.append({"piece": piece, "x": float((bb[0] + bb[3]) / 2), "y": float((bb[1] + bb[4]) / 2),
                              "w": float(dx), "d": float(dy), "z0": float(bb[2]), "z1": float(bb[5])})
    # de-duplicate nested parts (a post and its own sleeve): keep the widest at each spot
    posts.sort(key=lambda p: -p["w"] * p["d"])
    keep = []
    for p in posts:
        if all(math.hypot(p["x"] - q["x"], p["y"] - q["y"]) > 0.15 for q in keep):
            keep.append(p)
    return keep


def plan_decals(caster):
    P = Plan(caster)
    # ---------------- 1. MOSS + DAMP at the wall foot (the rubble footing), shaded / damp stretches only
    moss_in = [((10.0, 1.2), (0, -1, 0), 4.0), ((15.8, 1.2), (0, -1, 0), 3.2), ((28.2, 1.2), (0, -1, 0), 3.2),
               ((34.0, 1.2), (0, -1, 0), 4.0),                                # south wall, courtyard face (faces N)
               ((1.2, 8.5), (-1, 0, 0), 4.0), ((1.2, 19.0), (-1, 0, 0), 3.6), ((1.2, 24.8), (-1, 0, 0), 3.6),
               ((42.8, 8.5), (1, 0, 0), 4.0), ((42.8, 19.0), (1, 0, 0), 3.6), ((42.8, 24.8), (1, 0, 0), 3.6)]
    for (x, y), d, w in moss_in:
        P.wall("MossFoot", (x, y), d, w, 0.85, "ground", "SM_DK_WallFooting", 0.25, depth=0.40,
               note="courtyard wall foot; ")
    for x in (3.5, 12.0, 32.0, 40.5):                                          # the street face (reference 1)
        P.wall("MossFoot", (x, -3.0), (0, 1, 0), 4.0, 0.85, "ground", "SM_DK_WallFooting", 0.25, depth=0.40,
               note="street wall foot; ")
    # ---------------- 2. RAIN STREAKS under the wall caps (plaster body) and under the outbuilding eaves
    streak_in = [((12.0, 1.2), (0, -1, 0), 2.4), ((31.5, 1.2), (0, -1, 0), 2.0), ((1.2, 12.0), (-1, 0, 0), 2.4),
                 ((1.2, 21.8), (-1, 0, 0), 2.0), ((42.8, 12.6), (1, 0, 0), 2.4), ((42.8, 22.2), (1, 0, 0), 2.0)]
    for (x, y), d, w in streak_in:
        P.wall("RainStreak", (x, y), d, w, 1.05, "under", "SM_DK_WallBody", 1.1, depth=0.30, max_up=1.2,
               note="under the wall cap, courtyard face; ")
    for x, w in ((5.5, 2.4), (15.0, 2.0), (29.5, 2.2), (38.0, 2.4)):
        P.wall("RainStreak", (x, -3.0), (0, 1, 0), w, 1.05, "under", "SM_DK_WallBody", 1.1, depth=0.30, max_up=1.2,
               note="under the wall cap, street face; ")
    for x in (0.9, 6.7):                                                        # storehouse / residence gable fronts
        P.wall("RainStreak", (x, 24.0), (0, 1, 0), 1.2, 1.5, "under", "SM_DKO_", 2.0, depth=0.30, max_up=2.4,
               note="under the storehouse eave corner; ")
    for x in (37.3, 43.1):
        P.wall("RainStreak", (x, 24.0), (0, 1, 0), 1.2, 1.5, "under", "SM_DKO_", 2.0, depth=0.30, max_up=2.4,
               note="under the residence eave corner; ")
    # ---------------- 3. GRIME at post bases (posts measured from the frames' loose parts) and door thresholds
    posts = {}
    for piece in ("SM_DK_Gate_Frame", "SM_DKH_VerandaFrame", "SM_DKH_Frame", "SM_DKC_PostFrame", "SM_DKV_Frame",
                  "SM_DKS_Post"):
        posts[piece] = find_posts(piece, max_bottom=1.7 if piece == "SM_DKV_Frame" else 1.2,
                                  min_w=0.18 if piece == "SM_DK_Gate_Frame" else 0.10)
    chosen = []
    for p in posts["SM_DK_Gate_Frame"]:
        chosen.append((p, Vector((0, -1 if p["y"] < 0.2 else 1, 0)), "gate post"))
    front = [p for p in posts["SM_DKH_VerandaFrame"] + posts["SM_DKH_Frame"] if p["y"] < 23.0]
    for p in front:
        chosen.append((p, Vector((0, -1, 0)), "hall veranda front post"))
    for p in posts["SM_DKC_PostFrame"]:
        chosen.append((p, Vector((0, -1, 0)), "corridor post (open courtyard side)"))
    for p in posts["SM_DKV_Frame"]:
        chosen.append((p, Vector((-1, 0, 0)) if p["x"] < 41 else Vector((0, 1, 0)), "pavilion post"))
    for p in posts["SM_DKS_Post"]:
        chosen.append((p, Vector((0, 1, 0)), "shed post"))
    for p, n, what in chosen:
        half = (p["d"] if abs(n.y) > 0.5 else p["w"]) / 2
        base = Vector((p["x"], p["y"], p["z0"]))
        c = base + n * half + Vector((0, 0, 0.30 - 0.04))
        w = (p["w"] if abs(n.y) > 0.5 else p["d"]) + 0.16
        P.add("Grime", c, n, (0, 0, 1), w, 0.60, (p["d"] if abs(n.y) > 0.5 else p["w"]) + 0.12,
              f"{what} ({p['piece']}) {round(p['w'], 3)} x {round(p['d'], 3)} m, foot +{round(p['z0'], 3)}",
              {"post_centre": [round(p["x"], 3), round(p["y"], 3)]})
    P.floor("Grime", (22.0, -1.20), (0, -1, 0), 3.4, 0.9, z_from=1.0, note="gate threshold, street side; ")
    P.floor("Grime", (22.0, -0.05), (0, 1, 0), 3.4, 0.8, z_from=1.0, note="gate threshold, courtyard side; ")
    P.floor("Grime", (22.0, 23.55), (0, -1, 0), 6.0, 0.9, z_from=2.0, expect="SM_DKH_", note="hall main doors, "
            "on the veranda boards; ")
    for piece in ("SM_DKO_Door_Steel", "SM_DKO_Door_Wood"):
        for o in C.instances_of(piece):
            bb = C.world_bbox(o)
            cx, cy = (bb[0] + bb[3]) / 2, (bb[1] + bb[4]) / 2
            if bb[3] - bb[0] < bb[4] - bb[1]:                                   # thin in X
                out = Vector((1 if cx < 22 else -1, 0, 0))
                w = bb[4] - bb[1]
            else:
                out = Vector((0, -1 if cy > 18 else 1, 0))
                w = bb[3] - bb[0]
            xy = Vector((cx, cy, 0)) + out * 0.55
            P.floor("Grime", (xy.x, xy.y), out, w + 0.4, 0.9, z_from=1.2, note=f"{piece} threshold; ")
    # ---------------- 4. LICHEN on roof tiles, wall caps and the stone lanterns (sparse)
    for xy in ((12.3, 22.3), (18.4, 22.4), (25.8, 22.2), (31.8, 22.5)):
        P.roof("Lichen", xy, 1.4, 1.1, "SM_DKH_RoofLower", note="hall lower roof; ")
    for xy in ((20.4, -1.7), (23.7, 1.6)):
        P.roof("Lichen", xy, 1.2, 1.0, "SM_DK_Gate_Roof", note="gate roof; ")
    for xy in ((-0.5, 9.4), (44.5, 12.8), (6.8, -0.5), (35.5, -0.5), (-0.5, 23.0), (44.5, 20.5)):
        P.roof("Lichen", xy, 1.0, 0.8, "SM_DK_WallCap", note="wall cap; ")
    for xy in ((3.2, 29.5), (40.8, 29.5)):
        P.roof("Lichen", xy, 1.4, 1.1, "SM_DKO_Roof", note="outbuilding roof; ")
    P.roof("Lichen", (39.6, 2.2), 1.2, 1.0, "SM_DKV_Roof", note="pavilion roof; ")
    for (lx, ly) in ((19.0, 19.75), (25.0, 19.75)):
        P.roof("Lichen", (lx + 0.12, ly - 0.10), 0.55, 0.55, "SM_DKP_Stone_LanternTall", z_from=4.0, depth=0.30,
               note="lantern cap; ")
        P.roof("Lichen", (lx + 0.28, ly - 0.30), 0.60, 0.60, "SM_DKP_Stone_LanternTall", z_from=1.2, depth=0.30,
               note="lantern base; ")
    # ---------------- 5. WATER STAINS under the downpipe shoes (the shoe measured from each instance's lowest verts)
    for piece in ("SM_DKH_Downpipe", "SM_DKO_Downpipe", "SM_DKC_Downpipe"):
        for o in C.instances_of(piece):
            M = o.matrix_world
            co = np.array([M @ v.co for v in o.data.vertices])
            zmin = co[:, 2].min()
            low = co[co[:, 2] < zmin + 0.06]
            shaft = co[(co[:, 2] > zmin + 0.6) & (co[:, 2] < zmin + 1.6)]
            outlet = low.mean(0)
            axis = shaft.mean(0) if len(shaft) else outlet
            d = Vector((outlet[0] - axis[0], outlet[1] - axis[1], 0))
            if d.length < 0.02:
                d = Vector((0, -1, 0))
            d.normalize()
            tip = low[np.argmax((low[:, :2] - axis[:2]) @ np.array([d.x, d.y]))]
            c = Vector((tip[0], tip[1], 0)) + d * 0.42
            it = P.floor("WaterStain", (c.x, c.y), d, 0.95, 1.0, z_from=max(0.8, float(zmin) + 0.5),
                         note=f"{piece} shoe outlet {tuple(round(float(v), 3) for v in tip)}, outflow "
                              f"{tuple(round(v, 3) for v in d)}; ")
    # ---------------- 6. WORN PATHS in the gravel (hall stair flanks, along the hall front, the gate apron sides)
    for x in (20.45, 23.55):
        P.floor("WornPath", (x, 20.25), (0, 1, 0), 1.3, 1.7, expect="SM_DKG_", note="beside the hall stair; ")
    for x in (16.2, 27.8):
        P.floor("WornPath", (x, 20.65), (0, 1, 0), 4.5, 0.95, expect="SM_DKG_", note="along the hall front "
                "(stair to the veranda ends); ")
    for x in (16.9, 27.1):
        P.floor("WornPath", (x, 1.0), (0, 1, 0), 1.7, 1.4, expect="SM_DKG_", note="beside the gate apron; ")
    P.floor("WornPath", (22.0, -3.3), (0, -1, 0), 4.6, 1.6, z_from=1.0, note="street, in front of the gate apron "
            "(lands on whatever the outside track's ground is); ")
    return P, posts


# ------------------------------------------------------------------------------------------------ decal previews
def decal_material(name):
    key = f"PREVIEW_{name}"
    m = bpy.data.materials.get(key)
    if m:
        return m
    m = bpy.data.materials.new(key)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    spec = DECAL_MATS[name]

    def img(sfx, noncolor):
        n = nt.nodes.new("ShaderNodeTexImage")
        im = bpy.data.images.load(str(C.TEX_DIR / f"T_DKD_Decal_{name}_{sfx}.png"), check_existing=True)
        if noncolor:
            im.colorspace_settings.name = "Non-Color"
        n.image = im
        n.extension = "CLIP"
        return n
    bc, orm, nrm, msk = img("BC", False), img("ORM", True), img("N", True), img("M", True)
    nt.links.new(bc.outputs["Color"], bsdf.inputs["Base Color"])
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(orm.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
    op = nt.nodes.new("ShaderNodeMath")
    op.operation = "MULTIPLY"
    op.use_clamp = True
    nt.links.new(msk.outputs["Color"], op.inputs[0])
    op.inputs[1].default_value = spec["opacity"]
    nt.links.new(op.outputs[0], bsdf.inputs["Alpha"])
    sn = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(nrm.outputs["Color"], sn.inputs["Color"])
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    nt.links.new(sn.outputs[1], inv.inputs[1])
    cb = nt.nodes.new("ShaderNodeCombineColor")
    nt.links.new(sn.outputs[0], cb.inputs[0])
    nt.links.new(inv.outputs[0], cb.inputs[1])
    nt.links.new(sn.outputs[2], cb.inputs[2])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.inputs["Strength"].default_value = spec["normal_strength"]
    nt.links.new(cb.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def build_previews(plan, caster, coll_):
    """Each decal as a grid projected along -normal onto whatever the ray hits inside its box (the decal's own
    projection rule), lifted 4 mm, UV = the decal's texture space."""
    n_obj = 0
    built = []
    for it in plan.items:
        c, n, up, right = (Vector(it[k]) for k in ("centre", "normal", "up", "right"))
        w, h = it["size_m"]
        dep = it["depth_m"]
        nu = max(2, int(math.ceil(w / 0.05)))
        nv = max(2, int(math.ceil(h / 0.05)))
        flip = it["flip_u"]
        verts, uvs, ok = [], [], []
        for j in range(nv + 1):
            for i in range(nu + 1):
                s, t = i / nu, j / nv
                q = c + right * (s - 0.5) * w + up * (t - 0.5) * h
                r = caster.cast(q + n * (dep / 2), -n, dep)
                if r is None:
                    verts.append(q)
                    ok.append(False)
                else:
                    verts.append(r["p"] + r["n"] * 0.004)
                    ok.append(True)
                uvs.append((1 - s if flip else s, t))
        faces = []
        for j in range(nv):
            for i in range(nu):
                a = j * (nu + 1) + i
                quad = (a, a + 1, a + nu + 2, a + nu + 1)
                if all(ok[k] for k in quad):
                    faces.append(quad)
        it["preview_faces"] = len(faces)
        if faces:
            built.append((it, verts, faces, uvs))
    for it, verts, faces, uvs in built:
        me = bpy.data.meshes.new("DP_" + it["id"])
        me.from_pydata([tuple(v) for v in verts], [], faces)
        uvl = me.uv_layers.new(name="UVMap")
        for poly in me.polygons:
            for li in poly.loop_indices:
                uvl.data[li].uv = uvs[me.loops[li].vertex_index]
        me.materials.append(decal_material(it["material"].replace("M_DKD_Decal_", "")))
        o = bpy.data.objects.new("DP_" + it["id"], me)
        coll_.objects.link(o)
        o.visible_shadow = False
        n_obj += 1
    return n_obj


# ------------------------------------------------------------------------------------------------ checks
def clearance(objs, inst_objs):
    """Min distance from every plaque instance's vertices to the other meshes (BVH of each neighbour whose bbox is
    within 0.6 m), and whether any plaque triangle intersects a neighbour."""
    res = {}
    for o in inst_objs:
        me = o.data
        M = o.matrix_world
        pv = [M @ v.co for v in me.vertices]
        pb = BVHTree.FromPolygons(pv, [tuple(p.vertices) for p in me.polygons])
        bb = C.world_bbox(o)
        best = (9.0, None)
        hits = []
        for other in C.assembly():
            if other is o or C.piece_of(other).startswith(("SM_DKD_", "SM_DGB_Boundary")) or other.type != "MESH":
                continue
            ob = C.world_bbox(other)
            if any(ob[i] > bb[i + 3] + 0.6 or ob[i + 3] < bb[i] - 0.6 for i in range(3)):
                continue
            Mo = other.matrix_world
            ov = [Mo @ v.co for v in other.data.vertices]
            tb = BVHTree.FromPolygons(ov, [tuple(p.vertices) for p in other.data.polygons])
            for v in pv:
                f = tb.find_nearest(v)
                if f[0] is not None and f[3] < best[0]:
                    best = (f[3], C.piece_of(other))
            ov_pairs = pb.overlap(tb)
            if ov_pairs:
                cs = [sum((pv[k] for k in me.polygons[i].vertices), Vector()) / len(me.polygons[i].vertices)
                      for i, _ in ov_pairs]
                hits.append((C.piece_of(other), len(ov_pairs),
                             [round(min(c[i] for c in cs), 3) for i in range(3)] +
                             [round(max(c[i] for c in cs), 3) for i in range(3)]))
        res[o.name] = {"min_gap_m": round(best[0], 4), "nearest": best[1], "intersects": hits}
    return res


# ------------------------------------------------------------------------------------------------ main
def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    assert_owner(C.LOCK, "claude")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    kit = C.coll("Kit")
    asm = C.coll("Assembly")
    C.DW.mkdir(parents=True, exist_ok=True)
    C.TEX_DIR.mkdir(parents=True, exist_ok=True)
    n_ctx = C.load_showcase(kit, asm)
    print("context instances", n_ctx, flush=True)

    # ---- emblem textures: byte copies (pixels unchanged), verified by sha256
    tex = {}
    for src, dst in EMBLEM_FILES.items():
        shutil.copyfile(C.ARMORY_TEX / src, C.TEX_DIR / dst)
        a, b = sha(C.ARMORY_TEX / src), sha(C.TEX_DIR / dst)
        tex[dst] = {"from": f"Exports/ArmoryKit/Textures/{src}", "sha256": b, "identical": a == b}
    assert all(v["identical"] for v in tex.values())

    # ---- plaques
    mask_full, loops = trace_emblem()
    print("emblem loops", [(lp["n_raw"], lp["n"], round(lp["area"], 4)) for lp in loops], flush=True)
    objs, stats = {}, {}
    for name, spec in PLAQUES.items():
        o, st = build_plaque(name, spec, loops, mask_full, kit)
        objs[name], stats[name] = o, st
        print("BUILT", name, st, flush=True)
    inst, inst_objs = [], []
    for k, (piece, loc, rz, note) in enumerate(PLACE):
        o = bpy.data.objects.new(f"{piece}__d{k:03d}", objs[piece].data)
        o.matrix_world = Matrix.Translation(loc) @ Matrix.Rotation(math.radians(rz), 4, "Z")
        asm.objects.link(o)
        inst_objs.append(o)
        bb = C.world_bbox(o)
        inst.append({"piece": piece, "loc": list(loc), "rot_xyz_deg": [0.0, 0.0, rz], "rot_z": rz,
                     "scale": [1.0, 1.0, 1.0], "folder": "Dressing/Emblem", "collision_class": "thin",
                     "kit": "dressing", "source": "dressing/layout_dressing.json", "note": note,
                     "bbox_min_max": [round(v, 4) for v in bb]})
    bpy.context.view_layer.update()
    clr = clearance(objs, inst_objs)
    C.write_json(C.DW / "clearance.json", clr)
    print("CLEARANCE", json.dumps(clr), flush=True)

    # ---- decal plan (ray casts against the compound)
    caster = Caster()
    plan, posts = plan_decals(caster)
    print("DECALS", len(plan.items), "skipped", len(plan.skipped), flush=True)
    for s in plan.skipped:
        print("  SKIP", s, flush=True)
    prev = C.coll("DecalPreview")
    n_prev = 0 if "--no-preview" in ARGS else build_previews(plan, caster, prev)
    caster.restore()
    prev.hide_viewport = True
    kit.hide_render = True
    kit.hide_viewport = True

    # ---- QA + export (plaques: Nanite single LOD above 2k tris; texel density not applicable: unique crest texture)
    qa, exp = {}, {}
    kit.hide_viewport = False
    for name, o in objs.items():
        KM.add_uv1(o)
        r = qa_check([o], require_uv1=True, texel_density=None, overlap_method="sat")
        fails = [c for c in r["checks"] if not c["passed"]]
        waive = {"uv_no_overlap", "uv0_tile_range"}    # the relief sits over the board face in UV0 by design
        hard = [c for c in fails if c["name"] not in waive]
        qa[name] = {"hard_fails": hard, "waived": sorted({c["name"] for c in fails if c["name"] in waive}),
                    "tris": r["triangles"].get(name)}
        print("QA", name, len(hard), sorted({c["name"] for c in fails}), flush=True)
        for c in hard:
            print("  FAIL", c["name"], str(c["detail"])[:200], flush=True)
    hard_total = sum(len(v["hard_fails"]) for v in qa.values())
    C.write_json(C.DW / "qa_report.json", qa)
    nanite = {n: stats[n]["tris"] >= 2000 for n in objs}
    clr_bad = [k for k, v in clr.items() if v["intersects"] or v["min_gap_m"] < 0.001]
    if clr_bad:
        print("CLEARANCE FAIL", clr_bad, flush=True)
    if not hard_total and not clr_bad and "--no-export" not in ARGS:
        C.EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        for name, o in objs.items():
            r = export_fbx(str(C.EXPORT_DIR / f"{name}.fbx"), [o], kind="static", sidecar=False)
            exp[name] = {"lods": 1, "nanite": nanite[name], "tris": stats[name]["tris"], "warnings": r["warnings"]}
        C.write_json(C.DW / "export_report.json", exp)
    kit.hide_viewport = True

    # ---- layouts
    textures = {Path(f).stem: {"png": str(C.TEX_DIR / f), "ue_dir": f"{C.UE_DIR}/Textures",
                               "kind": Path(f).stem.rsplit("_", 1)[1]} for f in sorted(p.name for p in C.TEX_DIR.glob("T_DKD_*.png"))}
    pieces = {n: {"kit": "dressing", "class": "thin", "folder": "Dressing/Emblem", "note": PLAQUES[n]["note"],
                  "nanite": nanite[n], "fbx": str(C.EXPORT_DIR / f"{n}.fbx"), "sidecar": None,
                  "ue_dir": f"{C.UE_DIR}/Meshes", "slots": [MAT_PLAQUE, "M_DJ_TimberDark"], "tris": stats[n]["tris"],
                  "lod_tris": [stats[n]["tris"]], "lods": 1, "n_ucx": 1, "vcol": [],
                  "design": {k: v for k, v in PLAQUES[n].items() if k != "note"}, "measured": stats[n]}
              for n in objs}
    LX = {"date": "2026-09-29", "stage": "round 5: emblem plaques + weathering decals (dressing track)",
          "units": "m, grey-box world frame (X east, Y north, Z up; Unreal (x*100, -y*100, z*100), yaw = -rot_z)",
          "pieces": pieces, "instances": inst, "materials": PLAQUE_RECIPE,
          "textures": {k: v for k, v in textures.items() if k.startswith("T_DKD_Emblem_") and not k.endswith("_M")},
          "emblem_textures": tex, "emblem_trace": [{"n_raw": lp["n_raw"], "n": lp["n"], "area_uv": round(lp["area"], 5)}
                                                     for lp in loops],
          "decals": "dressing/decals.json", "clearance": clr,
          "collision": "each plaque one convex hull (class thin: Pawn block, Camera + Visibility ignore); every plaque "
                       "is out of reach of the walk routes (hall gables +7.45..+8.35 under the verge; gate +2.84..+3.36 "
                       "over the street apron, over R5's 2.5 m)"}
    C.write_json(C.DW / "layout_dressing.json", LX)
    decals = {
        "date": "2026-09-29", "units": LX["units"],
        "convention": {
            "centre": "a point ON the receiving surface (ray-cast); the decal box is centred there",
            "normal": "the surface's outward normal; the decal projects along -normal",
            "up / right": "the texture's up (image top) and right on the surface; right = up x normal",
            "size_m": "[width along right, height along up]", "depth_m": "box depth along the normal (centred)",
            "flip_u": "mirror the texture across (variation); in Unreal: actor scale Y = -1",
            "ue.rotation_deg": "UE rotator for local +X = -normal (projection), local +Z = up",
            "ue.decal_size_cm": "UDecalComponent.DecalSize = HALF extents (depth, width, height) / 2 in cm",
            "verify": "texture orientation in Unreal (which of the decal's local Y / Z is the image's U / V) is not "
                      "measured here: check one wall decal (MossFoot_01: the moss must sit at the wall FOOT) in the "
                      "first capture and flip up / right globally if needed"},
        "master": {"name": "M_DKD_Decal_Master", "domain": "DeferredDecal",
                   "blend": "Translucent (DBuffer: colour, normal, roughness)",
                   "graph": {"BaseColor": "BC.rgb * Tint", "Normal": "lerp((0,0,1), N (DirectX, TC_Normalmap), "
                             "NormalStrength)", "Roughness": "ORM.g * RoughMult", "Metallic": 0, "Specular": 0.5,
                             "Opacity": "saturate(M.r * Opacity) * DecalLifetimeOpacity"},
                   "note": "one master, one instance per decal type; DBuffer decals render on Nanite and non-Nanite "
                           "meshes (r.DBuffer 1, the UE 5.8 default); set bReceivesDecals false on the player "
                           "character's meshes so a player walking through a wall-foot box is not stained"},
        "materials": {f"M_DKD_Decal_{k}": {"parent": "M_DKD_Decal_Master", "ue_dir": f"{C.UE_DIR}/Materials",
                                           "textures": {s: f"T_DKD_Decal_{k}_{s}" for s in ("BC", "N", "ORM", "M")},
                                           "scalars": {"Opacity": v["opacity"], "RoughMult": v["rough_mult"],
                                                       "NormalStrength": v["normal_strength"]},
                                           "vectors": {"Tint": [1.0, 1.0, 1.0]}, "nominal_size_m": v["nominal_m"],
                                           "use": v["use"],
                                           "count": sum(1 for i in plan.items if i["material"] == f"M_DKD_Decal_{k}")}
                      for k, v in DECAL_MATS.items()},
        "textures": {k: v for k, v in textures.items() if k.startswith("T_DKD_Decal_")},
        "placements": plan.items, "skipped": plan.skipped,
        "posts_measured": {k: [[round(q["x"], 3), round(q["y"], 3), round(q["w"], 3), round(q["d"], 3),
                                round(q["z0"], 3)] for q in v] for k, v in posts.items()},
        "counts": {"placements": len(plan.items), "skipped": len(plan.skipped), "preview_objects": n_prev},
    }
    # ROUND 6 (2026-09-30) decals.json <-> level sync: the lichen on the tiled roofs and wall caps were dropped in round
    # 5 fix f1 (judges: white scribbles at distance; the gate-roof box printed black splatter on the soffit), so the
    # file lists only what the level places (86); the dropped ones are kept under "dropped" for the record
    _drop = ("gate roof;", "hall lower roof;", "outbuilding roof;", "pavilion roof;", "wall cap;")
    _gone = [q for q in decals["placements"]
             if q["material"] == "M_DKD_Decal_Lichen" and q.get("source", "").startswith(_drop)]
    if _gone:
        decals["placements"] = [q for q in decals["placements"] if q not in _gone]
        decals["dropped"] = {"reason": "round 5 fix f1 judge drop (round5.DROP_DECALS); synced to the level in round 6",
                             "placements": _gone}
        decals["counts"]["placements"] = len(decals["placements"])
        decals["counts"]["dropped"] = len(_gone)
        decals["materials"]["M_DKD_Decal_Lichen"]["count"] = sum(
            1 for q in decals["placements"] if q["material"] == "M_DKD_Decal_Lichen")
    C.write_json(C.DW / "decals.json", decals)
    # checks layout: the showcase layout + our pieces / instances (walk_check / climb_check / roof walks read it)
    L = json.loads(C.SHOWCASE_LAYOUT.read_text(encoding="utf-8"))
    L["pieces"].update(pieces)
    L["instances"] = L["instances"] + inst
    L["stage"] = "round 5 dressing checks: the showcase + SM_DKD_* emblem plaques"
    C.write_json(C.DW / "layout_dressing_checks.json", L)
    rep = {"pieces": stats, "qa_hard_fails": hard_total, "exported": sorted(exp), "decals": decals["counts"],
           "decals_by_material": {k: v["count"] for k, v in decals["materials"].items()},
           "clearance": clr, "sec": round(time.time() - T0, 1)}
    C.write_json(C.DW / "dressing_report.json", rep)
    C.BLEND.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(C.BLEND))
    print("DONE", json.dumps(rep), flush=True)


if __name__ == "__main__":
    main()
