"""Stage F: game build of the Snow Flower heels from the source blend.

    blender -b Assets/SnowFlowerHeels/SnowFlowerHeels.blend --factory-startup --python Scripts/SnowFlowerHeels/hb_f_build.py -- [--stage bake|export|all]

1. join the posed GAME shoe (right), three final slots (Leather / Insole / Metal), unique UVs per slot
2. bake BC / ORM / N (DirectX) from the posed HIGH shoe (Cycles, selected to active); insole BC = the painted print
3. mirror to the left shoe (UVs +1 in U, so UV0 never overlaps)
4. skin in the HEEL POSE from her posed skin (foot / ball / calf only), unpose both shoes to the bind pose
5. LOD1 / LOD2 by collapse decimation; join the pair per LOD: SK_SnowFlowerHeels(_LOD1/_LOD2)
6. garment_qa (fitted, MH_PlayerFemale, unique UVs) + posed-foot clearance, export_fbx(kind="garment") per LOD,
   sidecar SK_SnowFlowerHeels.garment.json, textures to Exports/SnowFlowerHeels/Textures
The source blend is never overwritten; the result is saved as Assets/SnowFlowerHeels/SnowFlowerHeels_Build.blend.
"""
import json
import math
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


# ------------------------------------------------------------------------------------------------ UVs

def uv_unwrap(ob):
    """Unique UVs per slot: split by material, smart-project + pack each part alone, join back."""
    ins = json.loads((C.R1 / "tex" / "insole_uv.json").read_text())
    pieces = []
    for si, slot in enumerate(SLOTS):
        c = ob.copy()
        c.data = ob.data.copy()
        c.name = f"UVPART_{slot}"
        bpy.context.scene.collection.objects.link(c)
        bm = bmesh.new()
        bm.from_mesh(c.data)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index != si], context="FACES")
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
        bm.to_mesh(c.data)
        bm.free()
        if not c.data.uv_layers:
            c.data.uv_layers.new(name="UVMap")
        ctx_obj(c)
        if slot == "Insole":
            me = c.data
            co = np.array([tuple(c.matrix_world @ v.co) for v in me.vertices])
            loc = C.world_to_local(co, "r")
            uv = np.column_stack([(loc[:, 0] - ins["U0"]) / ins["US"], (loc[:, 1] - ins["V0"]) / ins["VS"]])
            li = np.array([l.vertex_index for l in me.loops])
            me.uv_layers[0].data.foreach_set("uv", uv[li].ravel())
        else:
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.uv.smart_project(angle_limit=math.radians(38), island_margin=0.003, area_weight=0.0,
                                     correct_aspect=True, scale_to_bounds=False)
            bpy.ops.uv.select_all(action="SELECT")
            bpy.ops.uv.pack_islands(rotate=True, margin=0.003)
            bpy.ops.object.mode_set(mode="OBJECT")
            for rnd, ang in enumerate((20, 10, 5, 2)):
                bad = overlap_faces(c)
                if not bad:
                    break
                log("uv re-unwrap", slot, "round", rnd, len(bad), "faces")
                for p_ in c.data.polygons:
                    p_.select = p_.index in bad
                bpy.ops.object.mode_set(mode="EDIT")
                bpy.ops.uv.smart_project(angle_limit=math.radians(ang), island_margin=0.003, area_weight=0.0,
                                         correct_aspect=True, scale_to_bounds=False)
                bpy.ops.mesh.select_all(action="SELECT")
                bpy.ops.uv.select_all(action="SELECT")
                bpy.ops.uv.pack_islands(rotate=True, margin=0.003)
                bpy.ops.object.mode_set(mode="OBJECT")
        uv = np.zeros(len(c.data.loops) * 2)
        c.data.uv_layers[0].data.foreach_get("uv", uv)
        uv = uv.reshape(-1, 2)
        area = 0.0
        for p in c.data.polygons:
            q = uv[p.loop_start:p.loop_start + p.loop_total]
            area += 0.5 * abs(np.sum(q[:, 0] * np.roll(q[:, 1], -1) - np.roll(q[:, 0], -1) * q[:, 1]))
        log("uv", slot, "faces", len(c.data.polygons), "uv area", round(area, 3), "range", uv.min(0).round(3), uv.max(0).round(3))
        pieces.append(c)
    name = ob.name
    mats = list(ob.data.materials)
    bpy.data.objects.remove(ob, do_unlink=True)
    new = join_objects(pieces, name)
    col = bpy.data.collections["HEELS_GAME_POSED"]
    for cc in list(new.users_collection):
        cc.objects.unlink(new)
    col.objects.link(new)
    return new


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
    """mode 'bc': emission = base colour (a DIFFUSE colour bake returns black for metals); 'metal': emission = the
    metallic value; None: off."""
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
        if mode == "metal":
            v = b.inputs["Metallic"].default_value
            b.inputs["Emission Color"].default_value = (v, v, v, 1)
        else:
            src = b.inputs["Base Color"]
            if src.links:
                nt.links.new(src.links[0].from_socket, b.inputs["Emission Color"])
            else:
                b.inputs["Emission Color"].default_value = src.default_value


def bake_all(game, highs):
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
    bk.cage_extrusion = 0.0012
    bk.max_ray_distance = 0.008
    bk.margin = 12
    bk.target = "IMAGE_TEXTURES"
    images = {}
    for kind in ("BC", "N", "AO", "R", "M"):
        for slot in SLOTS:
            w, h = TEX_SIZE[slot]
            im = bpy.data.images.new(f"bake_{slot}_{kind}", w, h, alpha=False, float_buffer=True)
            im.colorspace_settings.name = "Non-Color"
            images[(slot, kind)] = im
    # bake with the UVs of the right shoe in 0-1 (no tile offsets yet)
    for slot in SLOTS:
        m = final_material(slot)
        nt = m.node_tree
        for n in list(nt.nodes):
            if n.type == "TEX_IMAGE":
                nt.nodes.remove(n)
        node = nt.nodes.new("ShaderNodeTexImage")
        node.name = "BAKE"
        nt.nodes.active = node
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for h in highs:
        h.hide_render = False
        h.hide_set(False)
        h.select_set(True)
    game.hide_render = False
    game.select_set(True)
    bpy.context.view_layer.objects.active = game
    # the low-poly and her body must not occlude the high-poly's AO: take them out of every ray type
    for attr in ("visible_diffuse", "visible_glossy", "visible_shadow", "visible_transmission", "visible_volume_scatter"):
        setattr(game, attr, False)
    lock = gq.load_base_lock("MH_PlayerFemale")
    for role in ("body", "head", "hair_proxy", "head_parts", "hair_cards"):
        nm = lock["objects"].get(role)
        if nm and bpy.data.objects.get(nm):
            bpy.data.objects[nm].hide_render = True
    for o in bpy.data.objects:
        if o.type == "MESH" and o not in highs and o is not game:
            o.hide_render = True

    def bake(kind, btype, **kw):
        for slot in SLOTS:
            final_material(slot).node_tree.nodes["BAKE"].image = images[(slot, kind)]
        log("bake", kind)
        bpy.ops.object.bake(type=btype, **kw)

    sc.cycles.samples = 16
    set_emission("bc")
    bake("BC", "EMIT")
    set_emission("metal")
    bake("M", "EMIT")
    set_emission(None)
    bake("R", "ROUGHNESS")
    bake("N", "NORMAL", normal_space="TANGENT")
    sc.cycles.samples = 96
    bake("AO", "AO")
    for attr in ("visible_diffuse", "visible_glossy", "visible_shadow", "visible_transmission", "visible_volume_scatter"):
        setattr(game, attr, True)
    return images


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


def write_textures(images):
    TEXDIR.mkdir(parents=True, exist_ok=True)
    out = {}
    for slot in SLOTS:
        bc = px(images[(slot, "BC")])[..., :3]
        ao = px(images[(slot, "AO")])[..., 0]
        r = px(images[(slot, "R")])[..., 0]
        m = px(images[(slot, "M")])[..., 0]
        n = px(images[(slot, "N")])[..., :3].copy()
        if slot == "Insole":
            import metro_png as P
            pr = P.read(str(C.R1 / "tex" / "insole_print.png")).astype(np.float32) / 255.0
            pr = pr[::-1, :, :3]                                   # PNG top row = V 1
            bc = np.where(pr <= 0.04045, pr / 12.92, ((pr + 0.055) / 1.055) ** 2.4)
            r = np.full_like(r, 0.62)
        if slot == "Metal":
            # antiqued silver: darken recesses in the colour too (the reference's dark recesses)
            k = np.clip((ao - 0.25) / 0.75, 0, 1) ** 0.8
            bc = bc * (0.35 + 0.65 * k)[..., None] * np.where(m > 0.5, 1.0, 1.0)[..., None]
        n[..., 1] = 1.0 - n[..., 1]                                 # OpenGL -> DirectX green
        orm = np.stack([ao, r, m], -1)
        base = f"T_SnowFlowerHeels_{slot}"
        save_png(lin2srgb(bc), TEXDIR / f"{base}_BC.png", True)
        save_png(orm, TEXDIR / f"{base}_ORM.png", False)
        save_png(n, TEXDIR / f"{base}_N.png", False)
        out[slot] = {k: str(TEXDIR / f"{base}_{k}.png") for k in ("BC", "ORM", "N")}
        log("textures", slot, "BC mean", lin2srgb(bc).mean().round(3), "metal frac", float((m > 0.5).mean()))
    return out


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

def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    stage = argv[argv.index("--stage") + 1] if "--stage" in argv else "all"
    assert_owner("SnowFlowerHeels", "claude")
    sc = bpy.context.scene
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
    game_r = join_objects([o for o in col_game.objects if o.name.startswith("GAME_R_")], "GAME_R_posed")
    for o in [o for o in col_game.objects if o.name.startswith("GAME_L_")]:
        bpy.data.objects.remove(o, do_unlink=True)
    parts = remap_slots(game_r)
    REPORT["lod0_tris_per_shoe"] = gh.tris(game_r)
    log("game right", len(game_r.data.vertices), "verts", gh.tris(game_r), "tris")
    bm = bmesh.new()
    bm.from_mesh(game_r.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="BEAUTY", ngon_method="BEAUTY")
    bm.to_mesh(game_r.data)
    bm.free()
    game_r = uv_unwrap(game_r)
    log("LOD0 right overlaps after unwrap", len(overlap_faces(game_r)))
    if "--skip-bake" in argv:
        tex = {slot: {k: str(TEXDIR / f"T_SnowFlowerHeels_{slot}_{k}.png") for k in ("BC", "ORM", "N")} for slot in SLOTS}
    else:
        hp_setup()
        images = bake_all(game_r, highs_r)
        tex = write_textures(images)
    game_materials(tex)
    REPORT["textures"] = tex
    if stage == "bake":
        bpy.ops.wm.save_as_mainfile(filepath=str(C.ASSET_BLEND.with_name("SnowFlowerHeels_Build.blend")))
        return
    # ---- left shoe = mirror
    game_l = game_r.copy()
    game_l.data = game_r.data.copy()
    game_l.name = "GAME_L_posed"
    col_game.objects.link(game_l)
    game_l.data.transform(Matrix.Diagonal((-1, 1, 1, 1)))
    game_l.data.flip_normals()
    offset_uvs(game_r, 0.0)
    offset_uvs(game_l, 1.0)
    # ---- skin in the heel pose, then unpose
    feet, params = load_pose()
    apply_heel_pose(arm, feet, params)
    bpy.context.view_layer.update()
    per_side = {}
    for side, ob in (("r", game_r), ("l", game_l)):
        w = skin_weights(ob, side, arm, body, zs)
        w = smooth_weights(ob, w, 2)
        pts = np.array([tuple(ob.matrix_world @ v.co) for v in ob.data.vertices])
        rest = unpose_points(pts, w, arm)
        per_side[side] = (w, pts, rest)
        used = sorted({b for x in w for b in x})
        log("skin", side, used, "max infl", max(len(x) for x in w))
    clear_heel_pose(arm)
    for side, ob in (("r", game_r), ("l", game_l)):
        w, pts, rest = per_side[side]
        ob.data.vertices.foreach_set("co", rest.astype(np.float32).ravel())
        ob.data.update()
        apply_weights(ob, w)
    # ---- LODs per side
    lods = {0: [game_r, game_l]}
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
            if (a_[uvl].uv - b_.link_loop_next[uvl].uv).length > 1e-6 or                     (a_.link_loop_next[uvl].uv - b_[uvl].uv).length > 1e-6:
                border.update(v.index for v in e.verts)
        bmk.free()
        return border

    for li, ratio in ((1, 0.5), (2, 0.25)):
        lods[li] = []
        for ob in (game_r, game_l):
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
                # last resort: collapse the few still-folded triangles to a single UV point (they then sample one
                # texel; zero-area UV triangles are ignored by the overlap test) - recorded in the report
                me = c.data
                uvd = me.uv_layers[0].data
                for fi in best[2]:
                    poly = me.polygons[fi]
                    cen = sum((Vector(uvd[l].uv) for l in poly.loop_indices), Vector((0.0, 0.0))) / poly.loop_total
                    for l in poly.loop_indices:
                        uvd[l].uv = cen
                REPORT.setdefault("lod_uv_collapsed_faces", {})[c.name] = len(best[2])
                log("LOD", c.name, "collapsed UVs of", len(best[2]), "faces; overlaps now", len(overlap_faces(c)))
            lods[li].append(c)
    gcol = bpy.data.collections[gh.GARMENT_COLLECTION]
    finals = []
    for li in (0, 1, 2):
        name = NAME if li == 0 else f"{NAME}_LOD{li}"
        pair = [o for o in lods[li]]
        for o in pair:
            gh.move_to(o, gcol)
        ob = join_objects(pair, name)
        # merge nothing: the two shoes are disjoint; clean any degenerate faces the decimation left
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
        gh.bind(ob, arm)
        for p in ob.data.polygons:
            p.use_smooth = True
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
            json.dumps(res["metrics"].get("intersection", {}))[:400])
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
                          "min_clearance_mm_on_near_verts": round(float(np.percentile(d[d < 0.01] * 1000, 1)) if (d < 0.01).any() else 99.0, 2)}
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
                             "warnings": res["warnings"], "triangles": gh.tris(ob)})
            log("exported", path.name)
        REPORT["exported"] = exported
        sidecar = {
            "fbx": f"{NAME}.fbx", "lods": [e["fbx"] for e in exported], "fbx_sha256": exported[0]["sha256"],
            "garment_type": "fitted (shoes: foot/ball; the strap and tall back also calf_twist_01/02)", "base": "MH_PlayerFemale",
            "skeleton": lock["unreal"]["skeleton"], "skeleton_hash": lock["skeleton_hash"],
            "physics_asset": lock["unreal"]["physics_asset"], "socket_bone": None, "cloth_section": None,
            "material_slots": [m.name for m in finals[0].data.materials], "triangles": [e["triangles"] for e in exported],
            "lod_screen_sizes": [1.0, 0.5, 0.25],
            "bind_pose": "REST pose of metahuman_base_skel; the shoes are modelled on her foot in the heel pose and unposed "
                         "- they sit correctly only with the heel-pose correction (WorkFiles/SnowFlowerHeels/HEEL_POSE.md)",
            "built": datetime.now().astimezone().isoformat(timespec="seconds"),
        }
        (C.EXPORT_DIR / f"{NAME}.garment.json").write_text(json.dumps(sidecar, indent=1), encoding="utf-8")
    REPORT["finished"] = datetime.now().astimezone().isoformat(timespec="seconds")
    (C.R1 / "build_report.json").write_text(json.dumps(REPORT, indent=1, default=str), encoding="utf-8")
    bpy.ops.wm.save_as_mainfile(filepath=str(C.ASSET_BLEND.with_name("SnowFlowerHeels_Build.blend")))
    log("BUILD_DONE gates_passed", passed)


try:
    main()
except Exception:  # noqa: BLE001
    import traceback
    traceback.print_exc()
    print("BUILD_ERROR")
    sys.exit(1)
