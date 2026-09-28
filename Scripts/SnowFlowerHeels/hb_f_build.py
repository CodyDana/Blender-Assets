"""Stage F: game build of the Snow Flower heels from the source blend (round 1 + finalise 2026-09-27).

    blender -b Assets/SnowFlowerHeels/SnowFlowerHeels.blend --factory-startup --python Scripts/SnowFlowerHeels/hb_f_build.py -- [--stage bake|export|all]

1. join the posed GAME shoe (right), three final slots (Leather / Insole / Metal), unique UVs per slot
2. bake BC / ORM / N (DirectX) from the posed HIGH shoe (Cycles, selected to active); insole BC = the painted print
3. mirror to the left shoe (UVs +1 in U, so UV0 never overlaps)
4. skin in the HEEL POSE from her posed skin (foot / ball / calf only), unpose both shoes to the bind pose
5. LOD1 / LOD2 by collapse decimation; join the pair per LOD: SK_SnowFlowerHeels(_LOD1/_LOD2)
6. garment_qa (fitted, MH_PlayerFemale, unique UVs) + posed-foot clearance, export_fbx(kind="garment") per LOD,
   sidecar SK_SnowFlowerHeels.garment.json, textures to Exports/SnowFlowerHeels/Textures
The source blend is never overwritten; the result is saved as Assets/SnowFlowerHeels/SnowFlowerHeels_Build.blend.

Finalise 2026-09-27 (after the Unreal and craft reviews of round 1):
* UVs unwrapped per piece (SLIM for the upper's leather and lining, smart project 55 deg elsewhere), one texel density
* per-piece bake: each game piece bakes only from its own high counterpart (face attribute ``piece``), 1.5 mm cage,
  4 mm rays, margin 0 in a rasterised mask, then a 16 px dilation; AO self-only fallback when a piece's AO median < 0.15
* satin leather / antiqued silver post-process of the ORM (roughness from the baked relief, bright glossy bevels)
* skinning: rigid on foot_/ball_ except the strap ring and buckle (HB_SKIN=rigid|ramp|r1, default rigid)
* LODs built on the right shoe and mirrored (identical topology), <= 2 influences after decimation
* exported with export_fbx(kind="garment"), which writes centimetres since pipeline 1.2.0
Report: WorkFiles/SnowFlowerHeels/final/build_report.json.
"""
import json
import math
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import hb_common as C  # noqa: E402
from pipeline import garment_helpers as gh  # noqa: E402
from pipeline import garment_qa as gq  # noqa: E402
from pipeline.export_fbx import export_fbx  # noqa: E402
from pipeline.lock import assert_owner  # noqa: E402
from SnowFlowerHeels.heel_pose import apply_heel_pose, clear_heel_pose, load_pose, unpose_points  # noqa: E402

T0 = time.time()
NAME = "SK_SnowFlowerHeels"
SLOTS = ["Leather", "Insole", "Metal"]
TILE = {"Leather": (0.0, 0.0), "Insole": (0.0, 1.0), "Metal": (0.0, -1.0)}
TEX_SIZE = {"Leather": (2048, 2048), "Insole": (2048, 1024), "Metal": (2048, 2048)}
TEXDIR = C.EXPORT_DIR / "Textures"
REPORT = {}
FINAL = C.WORK / "final"
MAX_INFL = 4


def log(*a):
    print(f"[F {time.time() - T0:7.1f}s]", *a, flush=True)


def ctx_obj(ob):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    ob.hide_set(False)
    ob.hide_select = False
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


def join_objects(objs, name):
    if len(objs) == 1:
        objs[0].name = name
        objs[0].data.name = name
        return objs[0]
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.hide_select = False
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    with bpy.context.temp_override(active_object=objs[0], selected_editable_objects=objs, selected_objects=objs):
        bpy.ops.object.join()
    ob = objs[0]
    ob.name = name
    ob.data.name = name
    return ob


def final_material(slot):
    name = f"M_SnowFlowerHeels_{slot}"
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
    return m


def remap_slots(ob):
    """HP_* part materials -> the three final slots (per-face)."""
    mesh = ob.data
    old = [m for m in mesh.materials]
    idx = np.zeros(len(mesh.polygons), dtype=np.int32)
    mesh.polygons.foreach_get("material_index", idx)
    code = np.array([SLOTS.index(m["final_slot"]) for m in old])
    part = np.array([m.name[3:] for m in old])
    # keep the part name per face as an attribute (for the report / debugging)
    newidx = code[idx]
    mesh.materials.clear()
    for s in SLOTS:
        mesh.materials.append(final_material(s))
    mesh.polygons.foreach_set("material_index", newidx)
    mesh.update()
    return part[idx]



BODY_PARTS = ["upper", "sole", "stiletto", "toplift", "strap", "insole"]
STRAP_ORNAMENTS = {"hex_frame", "dia_left", "dia_right", "tongue", "stud", "buckle_blossom"}
PIECE_META = {}


def tag_pieces(objs, side="R", store=True):
    """Face attribute ``piece`` on the posed GAME_*/HIGH_* parts: one id per (body part, material) and per ornament
    shell (``orn_id`` written by stage D). Game and high parts get the same ids, so every game piece bakes from its own
    high counterpart only (round 1 baked everything against everything: leather rays hit the ornaments and the lining)."""
    for ob in objs:
        part = ob.name.split("_", 2)[2]
        me = ob.data
        n = len(me.polygons)
        mi = np.zeros(n, dtype=np.int32)
        me.polygons.foreach_get("material_index", mi)
        if part == "ornaments":
            oid = np.zeros(n, dtype=np.int32)
            me.attributes["orn_id"].data.foreach_get("value", oid)
            pid = 1000 + oid
            names = json.loads(ob["orn_names"])
            if store:
                for k in np.unique(oid):
                    PIECE_META[int(1000 + k)] = {"part": "ornament", "name": names[int(k)]}
        else:
            base = (BODY_PARTS.index(part) + 1) * 10
            pid = base + mi
            if store:
                for k in np.unique(mi):
                    PIECE_META[int(base + k)] = {"part": part, "name": f"{part}:{me.materials[int(k)].name[3:]}"}
        a = me.attributes.get("piece") or me.attributes.new("piece", "INT", "FACE")
        a.data.foreach_set("value", pid.astype(np.int32))


def face_ints(ob, name):
    me = ob.data
    a = np.zeros(len(me.polygons), dtype=np.int32)
    me.attributes[name].data.foreach_get("value", a)
    return a


def subset_copy(ob, keep_mask, name, collection=None):
    """A copy of ``ob`` holding only the faces in ``keep_mask`` (attributes, UVs and corner normals carried)."""
    c = ob.copy()
    c.data = ob.data.copy()
    c.name = name
    (collection or bpy.context.scene.collection).objects.link(c)
    bm = bmesh.new()
    bm.from_mesh(c.data)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if not keep_mask[f.index]], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(c.data)
    bm.free()
    return c


def uv_stretch_ok(ob):
    """Area distortion of an unwrap: per-face (UV area / 3D area) relative to the median, p95/p5 <= 4 passes."""
    me = ob.data
    uv = np.zeros(len(me.loops) * 2)
    me.uv_layers[0].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    r = []
    for p in me.polygons:
        q = uv[p.loop_start:p.loop_start + p.loop_total]
        a2 = 0.5 * abs(np.sum(q[:, 0] * np.roll(q[:, 1], -1) - np.roll(q[:, 0], -1) * q[:, 1]))
        if p.area > 1e-10:
            r.append(a2 / p.area)
    r = np.array(r)
    r = r[r > 0]
    if len(r) < 3:
        return False, 0.0
    ratio = float(np.percentile(r, 95) / max(np.percentile(r, 5), 1e-12))
    return ratio <= 4.0, ratio


def unwrap_piece(c, method):
    ctx_obj(c)
    if not c.data.uv_layers:
        c.data.uv_layers.new(name="UVMap")
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    if method == "slim":
        bpy.ops.uv.unwrap(method="MINIMUM_STRETCH", fill_holes=True, correct_aspect=True, margin=0.002, no_flip=True,
                          iterations=30)
    else:
        bpy.ops.uv.smart_project(angle_limit=math.radians(method), island_margin=0.003, area_weight=0.0,
                                 correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def uv_unwrap(ob):
    """Unique UVs per slot, unwrapped PER PIECE (finalise 2026-09-27; round 1 smart-projected each whole slot at 38 deg
    and re-unwrapped overlaps until the sheets were hundreds of fragments):
    * the upper's leather and lining: one minimum-stretch (SLIM) unwrap each, no seams needed (each is a disc); falls
      back to smart project 55 deg if the unwrap folds or stretches (area p95/p5 > 4)
    * every other piece (sole, stiletto, top-lift, strap, each ornament shell): smart project 55 deg
    * the insole keeps its planar print mapping
    then per slot: islands averaged to one texel density and packed with an 8-px margin at 2048."""
    ins = json.loads((C.R1 / "tex" / "insole_uv.json").read_text())
    piece = face_ints(ob, "piece")
    mi = np.zeros(len(ob.data.polygons), dtype=np.int32)
    ob.data.polygons.foreach_get("material_index", mi)
    methods = {}
    slots_out = []
    for si, slot in enumerate(SLOTS):
        subs = []
        for pid in sorted(np.unique(piece[mi == si]).tolist()):
            keep = (mi == si) & (piece == pid)
            c = subset_copy(ob, keep, f"UVP_{slot}_{pid}")
            meta = PIECE_META.get(pid, {})
            if slot == "Insole":
                me = c.data
                if not me.uv_layers:
                    me.uv_layers.new(name="UVMap")
                co = np.array([tuple(c.matrix_world @ v.co) for v in me.vertices])
                loc = C.world_to_local(co, "r")
                uv = np.column_stack([(loc[:, 0] - ins["U0"]) / ins["US"], (loc[:, 1] - ins["V0"]) / ins["VS"]])
                li = np.array([l.vertex_index for l in me.loops])
                me.uv_layers[0].data.foreach_set("uv", uv[li].ravel())
                methods[pid] = "planar"
            elif meta.get("part") == "upper":
                unwrap_piece(c, "slim")
                ok, ratio = uv_stretch_ok(c)
                bad = overlap_faces(c)
                if ok and len(bad) <= 0.02 * len(c.data.polygons):
                    # a few folded faces are re-unwrapped by the slot pass below
                    methods[pid] = f"slim (area p95/p5 {ratio:.2f}, {len(bad)} folded faces re-unwrapped)"
                else:
                    unwrap_piece(c, 55)
                    methods[pid] = f"smart55 (slim rejected: ratio {ratio:.2f}, {len(bad)} overlapping faces)"
            else:
                unwrap_piece(c, 55)
                methods[pid] = "smart55"
            subs.append(c)
        part = join_objects(subs, f"UVSLOT_{slot}")
        if slot != "Insole":
            ctx_obj(part)
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.uv.select_all(action="SELECT")
            bpy.ops.uv.average_islands_scale()
            bpy.ops.uv.pack_islands(rotate=True, margin=0.004)
            bpy.ops.object.mode_set(mode="OBJECT")
            for rnd, ang in enumerate((20, 10, 5, 2)):
                bad = overlap_faces(part)
                if not bad:
                    break
                log("uv re-unwrap", slot, "round", rnd, len(bad), "faces")
                # select ONLY the overlapping faces: vertex/edge flags left selected by the pack above would re-select
                # every face on entering edit mode (the round 1 bug that re-projected whole slots at 20 deg)
                for v_ in part.data.vertices:
                    v_.select = False
                for e_ in part.data.edges:
                    e_.select = False
                for p_ in part.data.polygons:
                    p_.select = p_.index in bad
                    if p_.select:
                        for vi in p_.vertices:
                            part.data.vertices[vi].select = True
                bpy.ops.object.mode_set(mode="EDIT")
                bpy.ops.uv.smart_project(angle_limit=math.radians(ang), island_margin=0.003, area_weight=0.0,
                                         correct_aspect=True, scale_to_bounds=False)
                bpy.ops.mesh.select_all(action="SELECT")
                bpy.ops.uv.select_all(action="SELECT")
                # smart project fills the unit square with the few re-projected faces: bring them back to the slot's
                # texel density before packing (else 2 mm^2 faces took 12 % of the leather sheet)
                bpy.ops.uv.average_islands_scale()
                bpy.ops.uv.pack_islands(rotate=True, margin=0.004)
                bpy.ops.object.mode_set(mode="OBJECT")
        islands = count_uv_islands(part)
        uv = np.zeros(len(part.data.loops) * 2)
        part.data.uv_layers[0].data.foreach_get("uv", uv)
        uv = uv.reshape(-1, 2)
        area = 0.0
        for p in part.data.polygons:
            q = uv[p.loop_start:p.loop_start + p.loop_total]
            area += 0.5 * abs(np.sum(q[:, 0] * np.roll(q[:, 1], -1) - np.roll(q[:, 0], -1) * q[:, 1]))
        REPORT.setdefault("uv", {})[slot] = {"faces": len(part.data.polygons), "islands": islands,
                                              "uv_coverage": round(area, 3)}
        log("uv", slot, "faces", len(part.data.polygons), "islands", islands, "coverage", round(area, 3))
        slots_out.append(part)
    REPORT.setdefault("uv", {})["methods"] = {str(k): v for k, v in methods.items()}
    name = ob.name
    bpy.data.objects.remove(ob, do_unlink=True)
    new = join_objects(slots_out, name)
    col = bpy.data.collections["HEELS_GAME_POSED"]
    for cc in list(new.users_collection):
        cc.objects.unlink(new)
    col.objects.link(new)
    return new


def count_uv_islands(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    uvl = bm.loops.layers.uv.active
    parent = list(range(len(bm.faces)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for e in bm.edges:
        lf = e.link_loops
        if len(lf) != 2:
            continue
        a, b = lf
        if (a[uvl].uv - b.link_loop_next[uvl].uv).length < 1e-6 and (a.link_loop_next[uvl].uv - b[uvl].uv).length < 1e-6:
            ra, rb = find(a.face.index), find(b.face.index)
            if ra != rb:
                parent[ra] = rb
    n = len({find(i) for i in range(len(bm.faces))})
    bm.free()
    return n


def overlap_faces(ob, eps=1e-7):
    """Polygon indices taking part in UV triangle overlaps (the qa_check SAT test, returning the pairs)."""
    import itertools
    from collections import defaultdict
    me = ob.data
    me.calc_loop_triangles()
    uv = np.zeros(len(me.loops) * 2)
    me.uv_layers[0].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    tris = np.array([[uv[l] for l in t.loops] for t in me.loop_triangles])
    poly = np.array([t.polygon_index for t in me.loop_triangles])
    ea, eb = tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]
    keep = np.nonzero(np.abs(ea[:, 0] * eb[:, 1] - ea[:, 1] * eb[:, 0]) > 1e-12)[0]
    tris, poly = tris[keep], poly[keep]
    mins, maxs = tris.min(1), tris.max(1)
    cell = max(float(np.median(maxs - mins)) * 2.0, 1e-4)
    buckets = defaultdict(list)
    lo = np.floor(mins / cell).astype(np.int64)
    hi = np.floor(maxs / cell).astype(np.int64)
    for i in range(len(tris)):
        for cx in range(lo[i, 0], hi[i, 0] + 1):
            for cy in range(lo[i, 1], hi[i, 1] + 1):
                buckets[(cx, cy)].append(i)
    pairs = set()
    for m in buckets.values():
        if len(m) > 1:
            pairs.update(itertools.combinations(m, 2))
    if not pairs:
        return set()
    pa = np.array(sorted(pairs))
    A, B = tris[pa[:, 0]], tris[pa[:, 1]]
    sep = np.any(maxs[pa[:, 0]] <= mins[pa[:, 1]] + eps, axis=1) | np.any(maxs[pa[:, 1]] <= mins[pa[:, 0]] + eps, axis=1)
    for T in (A, B):
        for k in range(3):
            e = T[:, (k + 1) % 3] - T[:, k]
            ax = np.stack([-e[:, 1], e[:, 0]], -1)
            ax /= np.maximum(np.linalg.norm(ax, axis=1, keepdims=True), 1e-18)
            pa_ = np.einsum("pij,pj->pi", A, ax)
            pb_ = np.einsum("pij,pj->pi", B, ax)
            sep |= (pa_.max(1) <= pb_.min(1) + eps) | (pb_.max(1) <= pa_.min(1) + eps)
    bad = pa[~sep]
    return set(poly[bad[:, 0]].tolist()) | set(poly[bad[:, 1]].tolist())


def fix_uv_folds(ob, iters=12):
    """Unfold flipped UV triangles (decimation/projection folds): per UV island, faces whose UV winding disagrees with
    the island's majority get their loop UVs relaxed toward their island neighbours. Moves UVs by a few texels."""
    from pipeline.qa_check import uv_overlap_sat
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.faces.ensure_lookup_table()
    uvl = bm.loops.layers.uv.active
    key = lambda lp: (round(lp[uvl].uv.x, 6), round(lp[uvl].uv.y, 6))  # noqa: E731
    # islands: faces connected across edges whose two loops match in UV on both sides
    parent = list(range(len(bm.faces)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for e in bm.edges:
        lf = e.link_loops
        if len(lf) != 2:
            continue
        a, b = lf
        if key(a) == key(b.link_loop_next) and key(a.link_loop_next) == key(b):
            ra, rb = find(a.face.index), find(b.face.index)
            if ra != rb:
                parent[ra] = rb
    isl = [find(i) for i in range(len(bm.faces))]

    def sarea(f):
        u = [lp[uvl].uv for lp in f.loops]
        return sum(u[i].x * u[(i + 1) % len(u)].y - u[(i + 1) % len(u)].x * u[i].y for i in range(len(u))) * 0.5
    fixed_total = 0
    for _ in range(iters):
        maj = {}
        for f in bm.faces:
            maj[isl[f.index]] = maj.get(isl[f.index], 0.0) + sarea(f)
        flipped = [f for f in bm.faces if sarea(f) * maj[isl[f.index]] <= 0]
        if not flipped:
            break
        fixed_total += len(flipped)
        for f in flipped:
            for lp in f.loops:
                # neighbours: loops of the same vertex in the same island with the same uv, their adjacent uvs
                acc = Vector((0.0, 0.0))
                n = 0
                k0 = key(lp)
                for l2 in lp.vert.link_loops:
                    if isl[l2.face.index] != isl[f.index] or key(l2) != k0:
                        continue
                    for nb in (l2.link_loop_next, l2.link_loop_prev):
                        acc += nb[uvl].uv
                        n += 1
                if n:
                    tgt = acc / n
                    for l2 in lp.vert.link_loops:
                        if isl[l2.face.index] == isl[f.index] and key(l2) == k0:
                            l2[uvl].uv = l2[uvl].uv * 0.5 + tgt * 0.5
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.calc_loop_triangles()
    me = ob.data
    uv = np.zeros(len(me.loops) * 2)
    me.uv_layers[0].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    tri = np.array([[uv[l] for l in t.loops] for t in me.loop_triangles])
    return fixed_total, uv_overlap_sat(tri)


def offset_uvs(ob, du_side=0.0):
    me = ob.data
    uv = np.zeros(len(me.loops) * 2)
    me.uv_layers[0].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    idx = np.zeros(len(me.polygons), dtype=np.int32)
    me.polygons.foreach_get("material_index", idx)
    lp = np.zeros(len(me.loops), dtype=np.int32)
    for p in me.polygons:
        lp[p.loop_start:p.loop_start + p.loop_total] = p.material_index
    for si, slot in enumerate(SLOTS):
        t = TILE[slot]
        uv[lp == si] += np.array([t[0] + du_side, t[1]])
    me.uv_layers[0].data.foreach_set("uv", uv.ravel())



# ------------------------------------------------------------------------------------------------ high-poly bake shading

def hp_setup():
    """Add the texture detail to the HP_* bake-source materials (floral emboss, grain, crackle, insole print)."""
    tex = C.R1 / "tex"
    floral = bpy.data.images.load(str(tex / "floral_emboss.png"))
    floral.colorspace_settings.name = "Non-Color"
    grain = bpy.data.images.load(str(tex / "grain.png"))
    grain.colorspace_settings.name = "Non-Color"
    printimg = bpy.data.images.load(str(tex / "insole_print.png"))
    for m in bpy.data.materials:
        if not m.name.startswith("HP_"):
            continue
        part = m.name[3:]
        nt = m.node_tree
        b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        tc = nt.nodes.new("ShaderNodeTexCoord")
        if part in ("leather", "strap", "binding", "lining", "crackle", "sole"):
            mp = nt.nodes.new("ShaderNodeMapping")
            mp.inputs["Scale"].default_value = (1 / 0.055, 1 / 0.055, 1 / 0.055)
            nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
            bump = nt.nodes.new("ShaderNodeBump")
            bump.inputs["Distance"].default_value = 0.00025
            height = None
            if part in ("leather", "strap", "binding", "lining"):
                gi = nt.nodes.new("ShaderNodeTexImage")
                gi.image = grain
                gi.projection = "BOX"
                gi.projection_blend = 0.3
                mg = nt.nodes.new("ShaderNodeMapping")
                mg.inputs["Scale"].default_value = (1 / 0.012,) * 3
                nt.links.new(tc.outputs["Object"], mg.inputs["Vector"])
                nt.links.new(mg.outputs["Vector"], gi.inputs["Vector"])
                height = gi.outputs["Color"]
                bump.inputs["Strength"].default_value = 0.35 if part != "lining" else 0.15
            if part == "leather":
                fi = nt.nodes.new("ShaderNodeTexImage")
                fi.image = floral
                fi.projection = "BOX"
                fi.projection_blend = 0.35
                nt.links.new(mp.outputs["Vector"], fi.inputs["Vector"])
                add = nt.nodes.new("ShaderNodeMath")
                add.operation = "MULTIPLY_ADD"
                add.inputs[1].default_value = 0.6
                nt.links.new(fi.outputs["Color"], add.inputs[0])
                nt.links.new(height, add.inputs[2])
                height = add.outputs[0]
                col = nt.nodes.new("ShaderNodeMix")
                col.data_type = "RGBA"
                col.inputs["A"].default_value = (0.0085, 0.008, 0.0078, 1)
                col.inputs["B"].default_value = (0.022, 0.021, 0.020, 1)
                nt.links.new(fi.outputs["Color"], col.inputs["Factor"])
                nt.links.new(next(o for o in col.outputs if o.type == "RGBA"), b.inputs["Base Color"])
            if part == "crackle":
                vo = nt.nodes.new("ShaderNodeTexVoronoi")
                vo.feature = "DISTANCE_TO_EDGE"
                vo.inputs["Scale"].default_value = 1 / 0.0025 * 0.055
                nt.links.new(mp.outputs["Vector"], vo.inputs["Vector"])
                height = vo.outputs["Distance"]
                bump.inputs["Strength"].default_value = 0.6
            if height is not None:
                nt.links.new(height, bump.inputs["Height"])
                nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
        if part == "insole":
            im = nt.nodes.new("ShaderNodeTexImage")
            im.image = printimg
            nt.links.new(tc.outputs["UV"], im.inputs["Vector"])
            nt.links.new(im.outputs["Color"], b.inputs["Base Color"])
    # planar UVs on the high insole objects (same mapping as the game insole)
    ins = json.loads((C.R1 / "tex" / "insole_uv.json").read_text())
    for ob in bpy.data.collections["HEELS_HIGH_POSED"].objects:
        if not ob.name.startswith("HIGH_R_insole"):
            continue
        me = ob.data
        lay = me.uv_layers.new(name="UVMap")
        co = np.array([tuple(v.co) for v in me.vertices])
        loc = C.world_to_local(co, "r")
        uv = np.column_stack([(loc[:, 0] - ins["U0"]) / ins["US"], (loc[:, 1] - ins["V0"]) / ins["VS"]])
        li = np.array([l.vertex_index for l in me.loops])
        lay.data.foreach_set("uv", uv[li].ravel())



def set_emission(mode):
    """mode 'bc': emission = base colour (a DIFFUSE colour bake returns black for metals); 'mr': emission =
    (metallic, roughness, 0) of the material; None: off."""
    for m in bpy.data.materials:
        if not m.name.startswith("HP_"):
            continue
        nt = m.node_tree
        b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        for l in list(b.inputs["Emission Color"].links):
            nt.links.remove(l)
        if mode is None:
            b.inputs["Emission Strength"].default_value = 0.0
            continue
        b.inputs["Emission Strength"].default_value = 1.0
        if mode == "mr":
            b.inputs["Emission Color"].default_value = (b.inputs["Metallic"].default_value,
                                                        b.inputs["Roughness"].default_value, 0.0, 1.0)
        else:
            src = b.inputs["Base Color"]
            if src.links:
                nt.links.new(src.links[0].from_socket, b.inputs["Emission Color"])
            else:
                b.inputs["Emission Color"].default_value = src.default_value


def raster_mask(uvtris, w, h):
    """Pixels whose centre lies inside any of the UV triangles (what a margin-0 Cycles bake writes)."""
    mask = np.zeros((h, w), dtype=bool)
    P = np.asarray(uvtris, dtype=np.float64) * np.array([w, h])
    for t in P:
        x0 = max(int(math.floor(t[:, 0].min() - 0.5)), 0)
        x1 = min(int(math.ceil(t[:, 0].max() - 0.5)), w - 1)
        y0 = max(int(math.floor(t[:, 1].min() - 0.5)), 0)
        y1 = min(int(math.ceil(t[:, 1].max() - 0.5)), h - 1)
        if x1 < x0 or y1 < y0:
            continue
        X, Y = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        (ax, ay), (bx, by), (cx, cy) = t
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-12:
            continue
        l1 = ((by - cy) * (X - cx) + (cx - bx) * (Y - cy)) / den
        l2 = ((cy - ay) * (X - cx) + (ax - cx) * (Y - cy)) / den
        l3 = 1.0 - l1 - l2
        e = -1e-7
        mask[y0:y1 + 1, x0:x1 + 1] |= (l1 >= e) & (l2 >= e) & (l3 >= e)
    return mask


def dilate(img, filled, iters=16):
    """Grow the baked islands outward (the bake margin), averaging the filled 8-neighbours."""
    img = img.copy()
    filled = filled.copy()
    for _ in range(iters):
        acc = np.zeros_like(img)
        cnt = np.zeros(filled.shape, dtype=np.float32)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                f = np.roll(np.roll(filled, dy, 0), dx, 1)
                acc += np.roll(np.roll(img, dy, 0), dx, 1) * f[..., None]
                cnt += f
        new = (~filled) & (cnt > 0)
        if not new.any():
            break
        img[new] = acc[new] / cnt[new][:, None]
        filled |= new
    return img, filled


def piece_distances(ob, piece):
    """{(a, b): min distance mm} for piece pairs closer than 6 mm (vertex -> other piece's surface, both ways)."""
    me = ob.data
    co = np.array([tuple(ob.matrix_world @ v.co) for v in me.vertices])
    pids = sorted(np.unique(piece).tolist())
    faces_of = {p: [tuple(me.polygons[i].vertices) for i in np.nonzero(piece == p)[0]] for p in pids}
    verts_of = {p: sorted({i for f in faces_of[p] for i in f}) for p in pids}
    trees = {p: BVHTree.FromPolygons([Vector(c) for c in co], faces_of[p]) for p in pids}
    lo = {p: co[verts_of[p]].min(0) for p in pids}
    hi = {p: co[verts_of[p]].max(0) for p in pids}
    near = {}
    for i, a in enumerate(pids):
        for b in pids[i + 1:]:
            if np.any(lo[a] - 0.006 > hi[b]) or np.any(lo[b] - 0.006 > hi[a]):
                continue
            d = min(min((trees[b].find_nearest(Vector(co[k]), 0.006)[3] or 1.0) for k in verts_of[a]),
                    min((trees[a].find_nearest(Vector(co[k]), 0.006)[3] or 1.0) for k in verts_of[b]))
            if d < 0.006:
                near[(a, b)] = d * 1000.0
    return pids, near


def bake_groups(pids, near, gap_mm):
    """Greedy colouring: pieces closer than ``gap_mm`` never bake together (so no ray can reach a neighbour's high)."""
    order = sorted(pids, key=lambda p: (p >= 1000, -sum(1 for k in near if p in k)))
    groups = []
    for p in order:
        for g in groups:
            if p < 1000 or any(q < 1000 for q in g):
                continue                        # the large body pieces bake alone
            if all(near.get((min(p, q), max(p, q)), 99.0) >= gap_mm for q in g):
                g.append(p)
                break
        else:
            groups.append([p])
    return groups


def bake_all(game, highs):
    """Per-piece selected-to-active bake (finalise 2026-09-27). Each game piece is baked only from its own high
    counterpart (same ``piece`` id), pieces closer than 6 mm never share a bake, the cage offset is 1.5 mm with a 4 mm
    ray limit, and every bake writes margin 0 inside a rasterised coverage mask; the islands are then dilated 16 px.
    AO rays still see every high part (the scene), so ornaments shade the leather around them."""
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        sc.cycles.device = "GPU"
    except Exception:  # noqa: BLE001
        pass
    bk = sc.render.bake
    bk.use_selected_to_active = True
    bk.use_cage = False
    bk.cage_extrusion = 0.0015
    bk.max_ray_distance = 0.004
    bk.margin = 0
    bk.target = "IMAGE_TEXTURES"
    lock = gq.load_base_lock("MH_PlayerFemale")
    for role in ("body", "head", "hair_proxy", "head_parts", "hair_cards"):
        nm = lock["objects"].get(role)
        if nm and bpy.data.objects.get(nm):
            bpy.data.objects[nm].hide_render = True
    for o in bpy.data.objects:
        if o.type == "MESH":
            o.hide_render = True
    # the high pieces
    hcol = bpy.data.collections.new("BAKE_HIGH")
    bpy.context.scene.collection.children.link(hcol)
    hp = {}
    for h in highs:
        pc = face_ints(h, "piece")
        for pid in np.unique(pc).tolist():
            c = subset_copy(h, pc == pid, f"BH_{pid}", hcol)
            c.hide_render = False
            hp.setdefault(pid, []).append(c)
    # the game shoe: corner normals kept so every piece bakes against the final shading normals
    me = game.data
    cn = np.array([tuple(l.vector) for l in me.corner_normals])
    a = me.attributes.new("bake_cn", "FLOAT_VECTOR", "CORNER")
    a.data.foreach_set("vector", cn.ravel())
    piece = face_ints(game, "piece")
    pids, near = piece_distances(game, piece)
    groups = bake_groups(pids, near, 6.0)
    missing = [p for p in pids if p not in hp]
    REPORT["bake"] = {"pieces": len(pids), "groups": len(groups), "pieces_without_high": missing,
                      "cage_extrusion_mm": 1.5, "max_ray_mm": 4.0, "gap_mm": 6.0}
    log("bake pieces", len(pids), "groups", len(groups), "missing highs", missing)
    mi = np.zeros(len(me.polygons), dtype=np.int32)
    me.polygons.foreach_get("material_index", mi)
    uv = np.zeros(len(me.loops) * 2)
    me.uv_layers[0].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    me.calc_loop_triangles()
    lt_poly = np.array([t.polygon_index for t in me.loop_triangles])
    lt_uv = np.array([[uv[l] for l in t.loops] for t in me.loop_triangles])
    KINDS = ("BC", "MR", "N", "AO")
    images, acc, cov = {}, {}, {}
    for kind in KINDS:
        for slot in SLOTS:
            w, h = TEX_SIZE[slot]
            im = bpy.data.images.new(f"bake_{slot}_{kind}", w, h, alpha=True, float_buffer=True)
            im.colorspace_settings.name = "Non-Color"
            images[(slot, kind)] = im
            acc[(slot, kind)] = np.zeros((h, w, 4), dtype=np.float32)
    for slot in SLOTS:
        w, h = TEX_SIZE[slot]
        cov[slot] = np.zeros((h, w), dtype=bool)
        m = final_material(slot)
        nt = m.node_tree
        for n in list(nt.nodes):
            if n.type == "TEX_IMAGE":
                nt.nodes.remove(n)
        node = nt.nodes.new("ShaderNodeTexImage")
        node.name = "BAKE"
        nt.nodes.active = node
    ao_fallback = []
    for gi, g in enumerate(groups):
        keep = np.isin(piece, g)
        low = subset_copy(game, keep, f"BAKE_LOW_{gi}")
        lme = low.data
        cnl = np.zeros(len(lme.loops) * 3)
        lme.attributes["bake_cn"].data.foreach_get("vector", cnl)
        lme.normals_split_custom_set(cnl.reshape(-1, 3).tolist())
        low.hide_render = False
        for attr in ("visible_diffuse", "visible_glossy", "visible_shadow", "visible_transmission",
                     "visible_volume_scatter"):
            setattr(low, attr, False)
        masks = {}
        for si, slot in enumerate(SLOTS):
            sel = keep[lt_poly] & (mi[lt_poly] == si)
            if sel.any():
                w, h = TEX_SIZE[slot]
                masks[slot] = raster_mask(lt_uv[sel], w, h)
        sel_highs = [c for p in g for c in hp.get(p, [])]
        if not sel_highs:
            bpy.data.objects.remove(low, do_unlink=True)
            continue

        def run(kind, btype, **kw):
            for slot in SLOTS:
                final_material(slot).node_tree.nodes["BAKE"].image = images[(slot, kind)]
            for o in bpy.context.view_layer.objects:
                o.select_set(False)
            for c in sel_highs:
                c.select_set(True)
            low.select_set(True)
            bpy.context.view_layer.objects.active = low
            bpy.ops.object.bake(type=btype, **kw)
            for slot, mk in masks.items():
                arr = px(images[(slot, kind)])
                acc[(slot, kind)][mk] = arr[mk]

        sc.cycles.samples = 16
        set_emission("bc")
        run("BC", "EMIT")
        set_emission("mr")
        run("MR", "EMIT")
        set_emission(None)
        run("N", "NORMAL", normal_space="TANGENT")
        sc.cycles.samples = 64
        run("AO", "AO")
        # AO sanity: rays that start inside other geometry (round 1: 66% of the insole baked AO = 0)
        for slot, mk in masks.items():
            med = float(np.median(acc[(slot, "AO")][mk][:, 0])) if mk.any() else 1.0
            if med < 0.15:
                others = [o for o in hcol.objects if o not in sel_highs]
                for o in others:
                    o.hide_render = True
                run("AO", "AO")
                for o in others:
                    o.hide_render = False
                med2 = float(np.median(acc[(slot, "AO")][mk][:, 0]))
                ao_fallback.append({"group": gi, "pieces": [PIECE_META.get(p, {}).get("name", p) for p in g],
                                    "slot": slot, "median_before": round(med, 3), "median_self_only": round(med2, 3)})
                break
        for slot, mk in masks.items():
            cov[slot] |= mk
        log("bake group", gi, "/", len(groups), [PIECE_META.get(p, {}).get("name", p) for p in g][:6])
        bpy.data.objects.remove(low, do_unlink=True)
    REPORT["bake"]["ao_self_only_fallback"] = ao_fallback
    for c in list(hcol.objects):
        bpy.data.objects.remove(c, do_unlink=True)
    bpy.data.collections.remove(hcol)
    out = {}
    for slot in SLOTS:
        for kind in KINDS:
            out[(slot, kind)] = (acc[(slot, kind)], cov[slot])
    return out


def texel_stats(slot, n, ao, cov):
    nz = n[..., 2] * 2.0 - 1.0
    ln = np.linalg.norm(n * 2.0 - 1.0, axis=-1)
    return {"island_texels": int(cov.sum()), "N_z_below_0.2_frac": round(float((nz[cov] < 0.2).mean()), 5),
            "N_len_off_frac": round(float((np.abs(ln[cov] - 1.0) > 0.1).mean()), 5),
            "AO_zero_frac": round(float((ao[cov] < 0.02).mean()), 5), "AO_median": round(float(np.median(ao[cov])), 3)}


def write_textures(baked):
    TEXDIR.mkdir(parents=True, exist_ok=True)
    out = {}
    stats = {}
    for slot in SLOTS:
        bc, cov = baked[(slot, "BC")]
        mr, _ = baked[(slot, "MR")]
        nn, _ = baked[(slot, "N")]
        ao_, _ = baked[(slot, "AO")]
        bc = bc[..., :3].copy()
        m = mr[..., 0].copy()
        r = mr[..., 1].copy()
        n = nn[..., :3].copy()
        ao = ao_[..., 0].copy()
        # renormalise the baked tangent normals (sub-sample averaging shortens them)
        v = n * 2.0 - 1.0
        v /= np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-6)
        n = v * 0.5 + 0.5
        stats[slot] = texel_stats(slot, n, ao, cov)
        if slot == "Insole":
            import metro_png as P
            pr = P.read(str(C.R1 / "tex" / "insole_print.png")).astype(np.float32) / 255.0
            pr = pr[::-1, :, :3]                                   # PNG top row = V 1
            bc = np.where(pr <= 0.04045, pr / 12.92, ((pr + 0.055) / 1.055) ** 2.4)
            lum = bc @ np.array([0.2126, 0.7152, 0.0722])
            r = np.clip(0.66 - 0.5 * lum, 0.5, 0.7)                 # the printed ink sits a little glossier
        tv = v[..., 0] + v[..., 1]                                  # tangent-space relief (grain, emboss, bevels)
        if slot == "Leather":
            # satin leather: roughness 0.6-0.76 varied by the baked grain relief
            s = float(np.std(tv[cov])) or 1.0
            leather = cov & (m < 0.5)
            r = np.where(leather, np.clip(r + 0.05 * np.clip(tv / s, -1.6, 1.6), 0.45, 0.8), r)
        if slot == "Metal":
            # antiqued silver: darker in the AO recesses, brighter and glossier on the bevels (curvature from N)
            edge = np.clip((1.0 - v[..., 2]) / 0.25, 0.0, 1.0)
            metal = m > 0.5
            k = np.clip((ao - 0.25) / 0.75, 0, 1) ** 0.8
            bc = np.where(metal[..., None], bc * (0.35 + 0.65 * k)[..., None] * (1.0 + 0.3 * edge)[..., None], bc)
            r = np.where(metal, r * (1.0 - 0.6 * edge), r)
        # the bake margin: grow every map 16 px out of the islands, neutral values beyond
        bc, _f = dilate(bc, cov)
        n, _f = dilate(n, cov)
        orm = np.stack([ao, r, m], -1)
        orm, f2 = dilate(orm, cov)
        bc[~f2] = 0.0
        n[~f2] = (0.5, 0.5, 1.0)
        orm[~f2] = (1.0, 0.5, 0.0)
        v = n * 2.0 - 1.0
        v /= np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-6)
        n = v * 0.5 + 0.5
        n[..., 1] = 1.0 - n[..., 1]                                 # OpenGL -> DirectX green
        base = f"T_SnowFlowerHeels_{slot}"
        save_png(lin2srgb(np.clip(bc, 0, 1)), TEXDIR / f"{base}_BC.png", True)
        save_png(np.clip(orm, 0, 1), TEXDIR / f"{base}_ORM.png", False)
        save_png(np.clip(n, 0, 1), TEXDIR / f"{base}_N.png", False)
        out[slot] = {k: str(TEXDIR / f"{base}_{k}.png") for k in ("BC", "ORM", "N")}
        log("textures", slot, stats[slot])
    REPORT["bake_texel_stats"] = stats
    return out


def px(im):
    a = np.empty(im.size[0] * im.size[1] * 4, dtype=np.float32)
    im.pixels.foreach_get(a)
    return a.reshape(im.size[1], im.size[0], 4)


def save_png(arr, path, srgb):
    h, w = arr.shape[:2]
    im = bpy.data.images.new(path.stem, w, h, alpha=False)
    im.colorspace_settings.name = "sRGB" if srgb else "Non-Color"
    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[..., :3] = arr[..., :3]
    im.pixels.foreach_set(rgba.ravel())
    im.filepath_raw = str(path)
    im.file_format = "PNG"
    im.save()
    return im


def lin2srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)



def game_materials(tex):
    """Final slot materials drive the baked maps (Blender preview/render of the game mesh; Unreal uses pack masters)."""
    for slot in SLOTS:
        m = final_material(slot)
        nt = m.node_tree
        for n in list(nt.nodes):
            if n.type in ("TEX_IMAGE", "NORMAL_MAP", "SEPARATE_COLOR"):
                nt.nodes.remove(n)
        b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        def img(k, cs):
            im = bpy.data.images.load(tex[slot][k], check_existing=True)
            im.colorspace_settings.name = cs
            node = nt.nodes.new("ShaderNodeTexImage")
            node.image = im
            node.extension = "REPEAT"
            return node
        bc = img("BC", "sRGB")
        orm = img("ORM", "Non-Color")
        nn = img("N", "Non-Color")
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(orm.outputs["Color"], sep.inputs["Color"])
        # DirectX normal: flip green back for Blender
        inv = nt.nodes.new("ShaderNodeSeparateColor")
        comb = nt.nodes.new("ShaderNodeCombineColor")
        mth = nt.nodes.new("ShaderNodeMath")
        mth.operation = "SUBTRACT"
        mth.inputs[0].default_value = 1.0
        nt.links.new(nn.outputs["Color"], inv.inputs["Color"])
        nt.links.new(inv.outputs["Green"], mth.inputs[1])
        nt.links.new(inv.outputs["Red"], comb.inputs["Red"])
        nt.links.new(mth.outputs[0], comb.inputs["Green"])
        nt.links.new(inv.outputs["Blue"], comb.inputs["Blue"])
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(comb.outputs["Color"], nm.inputs["Color"])
        nt.links.new(bc.outputs["Color"], b.inputs["Base Color"])
        nt.links.new(sep.outputs["Green"], b.inputs["Roughness"])
        nt.links.new(sep.outputs["Blue"], b.inputs["Metallic"])
        nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
        if slot == "Metal":
            b.inputs["Coat Weight"].default_value = 0.0


# ------------------------------------------------------------------------------------------------ skinning

def remap_bone(name, side):
    n = name.lower()
    if "toe" in n or n.startswith("ball"):
        return f"ball_{side}"
    if n.startswith("foot") or "ankle" in n or n.startswith("heel"):
        return f"foot_{side}"
    if n.startswith("calf"):
        return name if name != f"calf_{side}" else f"calf_twist_02_{side}"
    if n.startswith("thigh") or n.startswith("knee"):
        return f"calf_twist_01_{side}"
    return f"foot_{side}"


def skin_weights(game, side, arm, body, zs):
    """Per vertex {bone: w} from her POSED skin (nearest triangle, barycentric), remapped to foot/ball/calf."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    me = ev.to_mesh()
    verts = [body.matrix_world @ v.co for v in me.vertices]
    me.calc_loop_triangles()
    tris = [tuple(t.vertices) for t in me.loop_triangles]
    names = {g.index: g.name for g in body.vertex_groups}
    vw = [{names[g.group]: g.weight for g in v.groups if g.weight > 0} for v in body.data.vertices]
    ev.to_mesh_clear()
    # keep only this side's lower leg triangles
    sgn = 1.0 if side == "l" else -1.0
    keep = [t for t in tris if all(verts[i].x * sgn > 0.02 and verts[i].z < 0.42 for i in t)]
    tree = BVHTree.FromPolygons(verts, keep)
    out = []
    co = [game.matrix_world @ v.co for v in game.data.vertices]
    loc = C.world_to_local(np.array([tuple(p) for p in co]), side)
    for i, p in enumerate(co):
        hit, _n, idx, _d = tree.find_nearest(p)
        a, b_, c = keep[idx]
        bw = barycentric_transform(hit, verts[a], verts[b_], verts[c], Vector((1, 0, 0)), Vector((0, 1, 0)),
                                   Vector((0, 0, 1)))
        acc = {}
        for corner, fac in zip((a, b_, c), (max(bw.x, 0), max(bw.y, 0), max(bw.z, 0))):
            for bone, w in vw[corner].items():
                nb = remap_bone(bone, side)
                acc[nb] = acc.get(nb, 0.0) + w * fac
        u, v_, w_ = loc[i]
        if u < 40 and w_ < zs(u, v_) - 5.5:          # stiletto, top-lift and the fittings on them: rigid on the foot
            acc = {f"foot_{side}": 1.0}
        top = sorted(acc.items(), key=lambda kv: -kv[1])[:3]
        top = [(b, w) for b, w in top if w >= 0.02] or [(f"foot_{side}", 1.0)]
        tot = sum(w for _, w in top)
        out.append({b: w / tot for b, w in top})
    return out


def smooth_weights(ob, weights, iters=3):
    """Average weights over mesh neighbours (keeps rigid parts' single bone) - removes speckle from the nearest-skin
    lookup on the ornaments."""
    n = len(weights)
    nb = [[] for _ in range(n)]
    for e in ob.data.edges:
        a, b = e.vertices
        nb[a].append(b)
        nb[b].append(a)
    cur = weights
    for _ in range(iters):
        new = []
        for i in range(n):
            if len(cur[i]) == 1 and list(cur[i].values())[0] == 1.0 and next(iter(cur[i])).startswith("foot"):
                new.append(cur[i])
                continue
            acc = dict(cur[i])
            for j in nb[i]:
                for k, w in cur[j].items():
                    acc[k] = acc.get(k, 0.0) + w * 0.5
            top = sorted(acc.items(), key=lambda kv: -kv[1])[:3]
            tot = sum(w for _, w in top)
            new.append({k: w / tot for k, w in top if w / tot >= 0.02})
            t2 = sum(new[-1].values())
            new[-1] = {k: w / t2 for k, w in new[-1].items()}
        cur = new
    return cur


def apply_weights(ob, weights):
    for g in list(ob.vertex_groups):
        ob.vertex_groups.remove(g)
    groups = {}
    for i, w in enumerate(weights):
        for b, x in w.items():
            g = groups.get(b) or ob.vertex_groups.new(name=b)
            groups[b] = g
            g.add([i], x, "REPLACE")


# ------------------------------------------------------------------------------------------------ main

def strap_vertices(ob):
    """Vertices of the ankle strap ring and the buckle hardware sitting on it."""
    piece = face_ints(ob, "piece")
    strap_ids = {p for p, m in PIECE_META.items() if m.get("part") == "strap" or m.get("name") in STRAP_ORNAMENTS}
    mask = np.zeros(len(ob.data.vertices), dtype=bool)
    for p in ob.data.polygons:
        if int(piece[p.index]) in strap_ids:
            for v in p.vertices:
                mask[v] = True
    return mask


def smooth_weights_spatial(ob, weights, side, zs, sigma_mm):
    """Gaussian blur of the skin weights in the POSED shoe's 3D space (sigma ``sigma_mm``), across pieces: every ornament
    then carries the weights of the leather under it and the counter bends as one smooth shell, instead of the round 1
    patchwork of nearest-skin lookups that crumpled it (edges +28 mm in the Unreal walk). The stiletto, top-lift and their
    fittings stay rigid on foot_; at most 4 influences are kept."""
    from mathutils.kdtree import KDTree
    co = np.array([tuple(ob.matrix_world @ v.co) for v in ob.data.vertices])
    loc = C.world_to_local(co, side)
    rigid = (loc[:, 0] < 40) & (loc[:, 2] < zs(loc[:, 0], loc[:, 1]) - 5.5)
    bones = sorted({b for w in weights for b in w})
    W = np.array([[w.get(b, 0.0) for b in bones] for w in weights])
    kd = KDTree(len(co))
    for i, p in enumerate(co):
        kd.insert(p, i)
    kd.balance()
    r = 3.0 * sigma_mm / 1000.0
    out = W.copy()
    for i in range(len(co)):
        if rigid[i]:
            continue
        hits = kd.find_range(co[i], r)
        idx = np.array([h[1] for h in hits])
        d = np.array([h[2] for h in hits]) * 1000.0
        g = np.exp(-0.5 * (d / sigma_mm) ** 2)
        out[i] = (g[:, None] * W[idx]).sum(0) / g.sum()
    res = []
    for i in range(len(co)):
        order = np.argsort(-out[i])[:4]
        wv = {bones[k]: float(out[i, k]) for k in order if out[i, k] >= 0.02}
        tot = sum(wv.values()) or 1.0
        res.append({b: x / tot for b, x in wv.items()})
    return res, {"variant": "smooth", "sigma_mm": sigma_mm, "rigid_vertices": int(rigid.sum()), "max_influences": 4}


def adjust_weights(ob, weights, side, arm, variant):
    """Skinning of everything that is not the strap (finalise 2026-09-27, Unreal walk test of round 1: the calf_twist /
    foot blend crumpled the tall back, edges stretched up to 28 mm).
    * "rigid": the whole shoe except the strap ring and buckle is rigid on foot_ (toes stay on ball_), the strap keeps
      her calf_twist weights - a shoe does not bend at the ankle
    * "ramp": calf weight faded in from 60 mm to 140 mm above the ankle joint (a boot-shaft blend)
    * "r1": round 1 as shipped"""
    if variant == "r1":
        return weights, {}
    strap = strap_vertices(ob)
    ankle = arm.matrix_world @ arm.pose.bones[f"foot_{side}"].head
    out = []
    moved = 0
    for i, w in enumerate(weights):
        if strap[i]:
            out.append(w)
            continue
        calf = sum(x for b, x in w.items() if b.startswith("calf"))
        if calf <= 0:
            out.append(w)
            continue
        if variant == "rigid":
            keep = 0.0
        else:
            h = ((ob.matrix_world @ ob.data.vertices[i].co).z - ankle.z) * 1000.0
            t = min(max((h - 60.0) / 80.0, 0.0), 1.0)
            keep = t * t * (3 - 2 * t)
        nw = {b: x for b, x in w.items() if not b.startswith("calf")}
        for b, x in w.items():
            if b.startswith("calf") and keep > 0:
                nw[b] = x * keep
        nw[f"foot_{side}"] = nw.get(f"foot_{side}", 0.0) + calf * (1.0 - keep)
        tot = sum(nw.values())
        nw = {b: x / tot for b, x in nw.items() if x / tot >= 0.02}
        tot = sum(nw.values())
        out.append({b: x / tot for b, x in nw.items()})
        moved += 1
    return out, {"variant": variant, "strap_vertices": int(strap.sum()), "reweighted_vertices": moved}


def limit_influences(ob, n=2):
    """Keep the ``n`` largest weights per vertex, renormalised (decimation interpolates groups)."""
    names = {g.index: g.name for g in ob.vertex_groups}
    rows = []
    worst = 0
    for v in ob.data.vertices:
        ws = sorted(((g.weight, names[g.group]) for g in v.groups if g.weight > 0), reverse=True)
        worst = max(worst, len(ws))
        ws = ws[:n] or [(1.0, "foot_r")]
        tot = sum(w for w, _ in ws)
        rows.append({b: w / tot for w, b in ws})
    apply_weights(ob, rows)
    return worst


def cleanup_mesh(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_area() < 1e-11], context="FACES")
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-6)
    for _ in range(3):
        bad = [e for e in bm.edges if len(e.link_faces) > 2]
        if not bad:
            break
        doomed = set()
        for e in bad:
            fl = sorted(e.link_faces, key=lambda f: f.calc_area())
            doomed.update(fl[:len(fl) - 2])
        bmesh.ops.delete(bm, geom=list(doomed), context="FACES")
    bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context="EDGES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(ob.data)
    bm.free()
    gh.triangulate_ngons(ob)


def mirror_left(ob, name, collection):
    """The left shoe = the exact mirror of the right one: same topology, X mirrored, winding flipped, bone groups
    renamed _r -> _l, UVs shifted +1 in U (so UV0 never overlaps)."""
    c = ob.copy()
    c.data = ob.data.copy()
    c.name = name
    collection.objects.link(c)
    c.data.transform(Matrix.Diagonal((-1, 1, 1, 1)))
    c.data.flip_normals()
    for g in c.vertex_groups:
        if g.name.endswith("_r"):
            g.name = g.name[:-2] + "_l"
    me = c.data
    uv = np.zeros(len(me.loops) * 2)
    me.uv_layers[0].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    uv[:, 0] += 1.0
    me.uv_layers[0].data.foreach_set("uv", uv.ravel())
    return c


def decimate_lod(ob, li, ratio, col_game):
    def uv_border(me):
        bmk = bmesh.new()
        bmk.from_mesh(me)
        uvl = bmk.loops.layers.uv.active
        border = set()
        for e in bmk.edges:
            lf = e.link_loops
            if len(lf) != 2:
                border.update(v.index for v in e.verts)
                continue
            a_, b_ = lf
            if (a_[uvl].uv - b_.link_loop_next[uvl].uv).length > 1e-6 or \
                    (a_.link_loop_next[uvl].uv - b_[uvl].uv).length > 1e-6:
                border.update(v.index for v in e.verts)
        bmk.free()
        return border
    protect = uv_border(ob.data)
    src_co = np.array([tuple(v.co) for v in ob.data.vertices])
    best = None
    jit = [0.0, 0.0, 0.0, 0.01, -0.01, 0.02, -0.02]
    for attempt in range(len(jit)):
        c = ob.copy()
        c.data = ob.data.copy()
        c.name = ob.name.replace("posed", f"LOD{li}") + f"_try{attempt}"
        col_game.objects.link(c)
        ctx_obj(c)
        grp = c.vertex_groups.new(name="_lodkeep")
        grp.add(list(range(len(c.data.vertices))), 0.0, "REPLACE")
        grp.add(sorted(protect), 1.0, "REPLACE")
        mod = c.modifiers.new("dec", "DECIMATE")
        mod.decimate_type = "COLLAPSE"
        mod.ratio = ratio + jit[attempt] * (1.0 if li == 2 else 0.5)
        mod.use_collapse_triangulate = True
        mod.delimit = {"UV", "MATERIAL", "SEAM"}
        mod.vertex_group = "_lodkeep"
        mod.vertex_group_factor = 1.0
        with bpy.context.temp_override(object=c, active_object=c):
            bpy.ops.object.modifier_apply(modifier=mod.name)
        c.vertex_groups.remove(c.vertex_groups["_lodkeep"])
        cleanup_mesh(c)
        bad = overlap_faces(c)
        log("LOD overlaps", c.name, len(bad), gh.tris(c))
        key = (len(bad), abs(gh.tris(c) - ratio * gh.tris(ob)))
        if best is None or key < best[0]:
            if best is not None:
                bpy.data.objects.remove(best[1], do_unlink=True)
            best = (key, c, bad)
        else:
            bpy.data.objects.remove(c, do_unlink=True)
        if not bad:
            break
        for fi in best[2]:
            for vi in best[1].data.polygons[fi].vertices:
                p_ = np.array(best[1].data.vertices[vi].co)
                d = np.linalg.norm(src_co - p_, axis=1)
                protect.update(np.nonzero(d < 0.004)[0].tolist())
    c = best[1]
    c.name = ob.name.replace("posed", f"LOD{li}")
    if best[2]:
        me = c.data
        uvd = me.uv_layers[0].data
        for fi in best[2]:
            poly = me.polygons[fi]
            cen = sum((Vector(uvd[l].uv) for l in poly.loop_indices), Vector((0.0, 0.0))) / poly.loop_total
            for l in poly.loop_indices:
                uvd[l].uv = cen
        REPORT.setdefault("lod_uv_collapsed_faces_per_shoe", {})[f"LOD{li}"] = len(best[2])
        log("LOD", c.name, "collapsed UVs of", len(best[2]), "faces; overlaps now", len(overlap_faces(c)))
    return c


# ------------------------------------------------------------------------------------------------ main

def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    stage = argv[argv.index("--stage") + 1] if "--stage" in argv else "all"
    variant = os.environ.get("HB_SKIN", "smooth10")
    assert_owner("SnowFlowerHeels", "claude")
    FINAL.mkdir(parents=True, exist_ok=True)
    REPORT["skin_variant"] = variant
    lock = gq.load_base_lock("MH_PlayerFemale")
    arm = bpy.data.objects[lock["armature_object"]]
    body = bpy.data.objects[lock["objects"]["body"]]
    zl = np.load(C.CACHE / "last_r.npz")
    import hb_geo as G
    zs = G.zins_sampler(zl)
    col_game = bpy.data.collections["HEELS_GAME_POSED"]
    col_high = bpy.data.collections["HEELS_HIGH_POSED"]
    highs_r = [o for o in col_high.objects if o.name.startswith("HIGH_R_")]
    for o in col_high.objects:
        if o.name.startswith("HIGH_L_"):
            o.hide_render = True
    games = [o for o in col_game.objects if o.name.startswith("GAME_R_")]
    gn = json.loads(bpy.data.objects["GAME_R_ornaments"]["orn_names"])
    hn = json.loads(bpy.data.objects["HIGH_R_ornaments"]["orn_names"])
    if gn != hn:
        raise RuntimeError(f"game / high ornament lists differ: {len(gn)} vs {len(hn)}")
    tag_pieces(games)
    tag_pieces(highs_r, store=False)
    REPORT["pieces"] = {str(k): v for k, v in sorted(PIECE_META.items())}
    game_r = join_objects(games, "GAME_R_posed")
    for o in [o for o in col_game.objects if o.name.startswith("GAME_L_")]:
        bpy.data.objects.remove(o, do_unlink=True)
    remap_slots(game_r)
    bm = bmesh.new()
    bm.from_mesh(game_r.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="BEAUTY", ngon_method="BEAUTY")
    bm.to_mesh(game_r.data)
    bm.free()
    # hard edges above 60 deg (plate walls, bevels, sole edges): the smooth-everywhere round 1 normals forced the
    # normal map to bend every shading normal back by up to 90 deg
    game_r.data.set_sharp_from_angle(angle=math.radians(60.0))
    REPORT["lod0_tris_per_shoe"] = gh.tris(game_r)
    log("game right", len(game_r.data.vertices), "verts", gh.tris(game_r), "tris")
    game_r = uv_unwrap(game_r)
    if "--skip-bake" in argv:
        tex = {slot: {k: str(TEXDIR / f"T_SnowFlowerHeels_{slot}_{k}.png") for k in ("BC", "ORM", "N")} for slot in SLOTS}
    else:
        hp_setup()
        baked = bake_all(game_r, highs_r)
        tex = write_textures(baked)
    game_materials(tex)
    REPORT["textures"] = tex
    if stage == "bake":
        bpy.ops.wm.save_as_mainfile(filepath=str(C.ASSET_BLEND.with_name("SnowFlowerHeels_Build.blend")))
        return
    offset_uvs(game_r, 0.0)
    # ---- skin the right shoe in the heel pose, then unpose (the left shoe is its mirror)
    feet, params = load_pose()
    apply_heel_pose(arm, feet, params)
    bpy.context.view_layer.update()
    w = skin_weights(game_r, "r", arm, body, zs)
    w = smooth_weights(game_r, w, 2)
    if variant.startswith("smooth"):
        w, info = smooth_weights_spatial(game_r, w, "r", zs, float(variant[6:] or 10.0))
    else:
        w, info = adjust_weights(game_r, w, "r", arm, variant)
    REPORT["skin"] = info
    pts = np.array([tuple(game_r.matrix_world @ v.co) for v in game_r.data.vertices])
    rest = unpose_points(pts, w, arm)
    log("skin", sorted({b for x in w for b in x}), "max infl", max(len(x) for x in w), info)
    clear_heel_pose(arm)
    game_r.data.vertices.foreach_set("co", rest.astype(np.float32).ravel())
    game_r.data.update()
    apply_weights(game_r, w)
    cleanup_mesh(game_r)
    # ---- LODs of the right shoe, then mirror each LOD
    lods_r = {0: game_r, 1: decimate_lod(game_r, 1, 0.5, col_game), 2: decimate_lod(game_r, 2, 0.25, col_game)}
    gcol = bpy.data.collections[gh.GARMENT_COLLECTION]
    finals = []
    REPORT["max_influences_before_limit"] = {}
    for li in (0, 1, 2):
        right = lods_r[li]
        REPORT["max_influences_before_limit"][f"LOD{li}"] = limit_influences(right, MAX_INFL)
        REPORT[f"lod{li}_tris_per_shoe"] = gh.tris(right)
        for p in right.data.polygons:
            p.use_smooth = True
        right.data.set_sharp_from_angle(angle=math.radians(60.0))
        left = mirror_left(right, right.name.replace("_R_", "_L_"), col_game)
        name = NAME if li == 0 else f"{NAME}_LOD{li}"
        for o in (right, left):
            gh.move_to(o, gcol)
        ob = join_objects([right, left], name)
        gh.bind(ob, arm)
        finals.append(ob)
        REPORT[f"lod{li}_tris"] = gh.tris(ob)
        log("LOD", li, name, gh.tris(ob), "tris")
    bpy.context.view_layer.update()
    # ---- gates
    qa = {}
    for ob in finals:
        res = gq.qa_garment([ob], "fitted", base="MH_PlayerFemale", unique_uvs=True)
        qa[ob.name] = res
        log("QA", ob.name, "passed" if res["passed"] else f"FAILED {res['failed']}",
            json.dumps(res["metrics"].get("intersection", {}))[:300])
    REPORT["qa"] = {k: {"passed": v["passed"], "failed": v["failed"], "metrics": v["metrics"],
                        "failed_detail": [c for c in v["checks"] if not c["passed"]],
                        "checks": [(c["name"], c["passed"]) for c in v["checks"]]} for k, v in qa.items()}
    for k, v in REPORT["qa"].items():
        for c in v["failed_detail"]:
            log("  FAIL", k, c["name"], c["object"], c["detail"][:300])
    # ---- posed clearance (the gates test the REST pose; the shoe is worn in the heel pose)
    apply_heel_pose(arm, feet, params)
    bpy.context.view_layer.update()
    col = gq.Collider([body, bpy.data.objects[lock["objects"]["head"]]])
    posed = {}
    for ob in finals:
        coords, _ = gq.evaluated_world(ob)
        dist, found, _r = col.signed(coords, max_distance=0.3)
        d = dist[found]
        posed[ob.name] = {"vertices": int(len(coords)), "inside_any": int((d < 0).sum()),
                          "inside_gt_1mm": int((d < -0.001).sum()), "deepest_mm": round(float(-min(d.min(), 0) * 1000), 2),
                          "min_clearance_mm_on_near_verts": round(float(np.percentile(d[d < 0.01] * 1000, 1)) if (d < 0.01).any() else 99.0, 2),
                          "floor_min_z_mm": round(float(coords[:, 2].min() * 1000), 3)}
        log("POSED", ob.name, posed[ob.name])
    clear_heel_pose(arm)
    REPORT["posed_clearance"] = posed
    passed = all(v["passed"] for v in qa.values())
    REPORT["gates_passed"] = passed
    C.EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    if passed and stage in ("all", "export"):
        exported = []
        for ob in finals:
            path = C.EXPORT_DIR / f"{ob.name}.fbx"
            res = export_fbx(path, [ob], kind="garment")
            data = path.read_bytes()
            limb = data.count(b"LimbNode")
            if limb < len(arm.data.bones) or b"Cluster" not in data:
                raise RuntimeError(f"{path.name}: skeleton/skin missing ({limb} LimbNode)")
            exported.append({"fbx": path.name, "sha256": gq.file_sha256(path), "objects": res["objects"],
                             "units": res["units"], "warnings": res["warnings"], "triangles": gh.tris(ob)})
            log("exported", path.name, res["units"])
        REPORT["exported"] = exported
        old = {}
        sc_path = C.EXPORT_DIR / f"{NAME}.garment.json"
        if sc_path.exists():
            old = json.loads(sc_path.read_text(encoding="utf-8"))
        sidecar = {
            "fbx": f"{NAME}.fbx", "lods": [e["fbx"] for e in exported], "fbx_sha256": exported[0]["sha256"],
            "units": "cm (pipeline 1.2.0; the round 1 metre files were drawn 100x small as Leader Pose followers)",
            "garment_type": "fitted (foot_/ball_ with calf_twist_01/02 on the tall back and strap; weights blurred in "
                            "3D so the shell bends as one piece; stiletto and top-lift rigid on foot_)"
            if variant.startswith("smooth") else f"fitted (skin variant {variant})",
            "base": "MH_PlayerFemale",
            "skeleton": lock["unreal"]["skeleton"], "skeleton_hash": lock["skeleton_hash"],
            "physics_asset": lock["unreal"]["physics_asset"], "socket_bone": None, "cloth_section": None,
            "material_slots": [m.name for m in finals[0].data.materials], "triangles": [e["triangles"] for e in exported],
            "lod_screen_sizes": [1.0, 0.5, 0.25], "max_influences": MAX_INFL,
            "bind_pose": "REST pose of metahuman_base_skel; the shoes are modelled on her foot in the heel pose and unposed "
                         "- they sit correctly only with the heel-pose correction CR_HeelPose (HEEL_POSE.md)",
            "heel_tip_floor_in_foot_l_ue_cm": old.get("heel_tip_floor_in_foot_l_ue_cm", [-15.4536, 3.1602, -1.3427]),
            "built": datetime.now().astimezone().isoformat(timespec="seconds"),
        }
        sc_path.write_text(json.dumps(sidecar, indent=1), encoding="utf-8")
    REPORT["finished"] = datetime.now().astimezone().isoformat(timespec="seconds")
    (FINAL / "build_report.json").write_text(json.dumps(REPORT, indent=1, default=str), encoding="utf-8")
    bpy.ops.wm.save_as_mainfile(filepath=str(C.ASSET_BLEND.with_name("SnowFlowerHeels_Build.blend")))
    log("BUILD_DONE gates_passed", passed)


try:
    main()
except Exception:  # noqa: BLE001
    import traceback
    traceback.print_exc()
    print("BUILD_ERROR")
    sys.exit(1)
