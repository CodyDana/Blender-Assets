"""Stone kit (tracks 8 terrace wall + 9 stair path): SHARED helpers. Track-neutral; add to it, never break it.

The stone kit extends the dojo's own stonework, so it IMPORTS (never forks) the pieces that already carry that language:
  - Scripts/dojo/kit1_geo.py            Geo, pillow_face, rough_block, hewn_box, primitives (plain import)
  - Scripts/dojo/build_kit1.py          footing construction, M_DK_FootingStone / M_DK_JointEarth recipes, moss_alpha,
                                        UV1 packing, LOD fix (load_builder(): the module without its trailing main())
  - Scripts/dojo/props/stone/build_stone_props.py   the courtyard stone lantern (load_builder() as well)
  - Scripts/dojo/materials/             the shared material library (dojo_materials / dojo_tex_gen)

What is here:
  load_builder(path, name)   import a dojo build script whose last line is `main()` without running main
  Piece                      kit piece container (Geo + UCX hull point lists + catalog fields)
  tile_of(mat)               a material's tile size (m) from the library set it samples
  granite_moss_variant(...)  a library Granite variant with moss lerped in by the 'Wear' alpha (the kit-1
                             M_DK_FootingStone recipe with its own tint / flatten / moss numbers)
  build_mesh(piece, coll, K1, moss=...)   Geo -> mesh: UV0 in library tile units (explicit per-vertex UVs, box
                             projection with a per-part offset for stone and iron, grain_uv for timber with its end-grain
                             slot, unit_uv for panes), UV1 lightmap (kit 1's checked packer), 'Wear' corner colours
                             (bake_wear), optional moss alpha, UCX_ children from the hull point lists
  qa_piece / export_piece    the pipeline gate: qa_check (0 hard fails, UV0 tiling overlaps waived as kit 1) and
                             export_fbx; Nanite pieces ship LOD0 only, light pieces LOD0-2 (pipeline decimate_lods)
  merge_catalog(track, data) atomic, file-locked read-modify-write of WorkFiles/dojo/build/stonekit/kit_catalog.json
                             (each track owns tracks[<track>] and its own pieces; nothing else is touched)
  file_lock(path)            a tiny O_EXCL lock for the shared files (catalog, DojoStoneKit.blend)
"""
import contextlib
import json
import math
import os
import random
import sys
import time
import types
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector, noise

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "Scripts"
DOJO = SCRIPTS / "dojo"
for _p in (SCRIPTS, DOJO, DOJO / "materials"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from pipeline.export_fbx import export_fbx  # noqa: E402
from pipeline.helpers import decimate_lods, make_lod_group  # noqa: E402
from pipeline.qa_check import qa_check  # noqa: E402
import dojo_materials as djm  # noqa: E402
import dojo_tex_gen as djt  # noqa: E402
import kit1_geo as G  # noqa: E402

EXPORT_DIR = ROOT / "Exports" / "DojoKit" / "StoneKit"
WORK = ROOT / "WorkFiles" / "dojo" / "build" / "stonekit"
BLEND = ROOT / "Assets" / "Dojo" / "DojoStoneKit.blend"
CATALOG = WORK / "kit_catalog.json"
KIT1_BUILDER = DOJO / "build_kit1.py"
STONE_PROPS_BUILDER = DOJO / "props" / "stone" / "build_stone_props.py"
WAIVE = {"uv0_tile_range", "uv_no_overlap"}     # UV0 is in library tile units (tiles overlap by design; kit 1 waives)


# ------------------------------------------------------------------------------------------------ import, don't fork
def load_builder(path, name):
    """Import a dojo build script whose LAST line is a bare `main()` call, without running main. The module keeps its
    own __file__ (its paths resolve as in its own run) and is registered in sys.modules under `name`."""
    path = Path(path)
    if name in sys.modules:
        return sys.modules[name]
    src = path.read_text(encoding="utf-8").rstrip().splitlines()
    if not src or src[-1].strip() != "main()":
        raise RuntimeError(f"{path.name}: the last line is not a bare main() call; cannot import it safely")
    mod = types.ModuleType(name)
    mod.__file__ = str(path)
    sys.modules[name] = mod
    exec(compile("\n".join(src[:-1]) + "\n", str(path), "exec"), mod.__dict__)
    return mod


def clamp01(x):
    return max(0.0, min(1.0, x))


# ------------------------------------------------------------------------------------------------ piece container
class Piece:
    """One kit piece: its Geo (kit1_geo), convex UCX hulls (point lists, piece space), and catalog fields."""

    def __init__(self, name, cls, note, track):
        self.name, self.cls, self.note, self.track = name, cls, note, track
        self.g = G.Geo()
        self.hulls = []
        self.hull_kinds = []
        self.nanite = False
        self.ground_z = None        # bake_wear ground level (None = the piece's lowest point)
        self.moss = None            # {material: callable(obj, slot) -> faces} moss passes after bake_wear
        self.snaps = {}             # name -> {"loc": [x, y, z], "facing": [x, y, z], "note": str}
        self.extra = {}
        self.part = None            # an already-built Blender object (pieces built by another builder, e.g. a Part)

    def hull_box(self, x0, x1, y0, y1, z0, z1, kind="block"):
        self.hulls.append([(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)])
        self.hull_kinds.append(kind)
        return self

    def hull_pts(self, pts, kind="block"):
        self.hulls.append([tuple(p) for p in pts])
        self.hull_kinds.append(kind)
        return self

    def snap(self, name, loc, facing, note=""):
        self.snaps[name] = {"loc": [round(float(v), 4) for v in loc], "facing": [round(float(v), 4) for v in facing],
                            "note": note}
        return self


# ------------------------------------------------------------------------------------------------ materials
KIT_TILES = {"M_DK_FootingStone": 4.0, "M_DK_JointEarth": 4.0, "M_DK_TimberPale": 4.0}


def tile_of(m):
    mat = bpy.data.materials.get(m)
    if mat is not None and mat.get("dj_set"):
        tm = djt.SETS[mat["dj_set"]]["tile_m"]
        return (tm[0] if tm else None)
    if m in KIT_TILES:
        return KIT_TILES[m]
    if mat is not None and mat.get("sk_tile"):
        return float(mat["sk_tile"])
    return 4.0


VARIANT_NORMAL = {"M_DKT_StepGranite": 0.55}    # a variant's normal strength is part of its recipe (keyed by name,
                                                 # so every track's call builds the same material)

# f2 (the owner's reading of the reference, 2026-09-30): ONE kit-wide granite family in MID-GREY (f1's pale grey-beige
# was wrong, r0's kit-1 FootingStone tint read brown at sunset): the tints neutralise the warm library Granite BC mean
# to a neutral grey (linear ~0.14 on the wall, sRGB ~105: between kit 1's footing (0.097 / 0.085 / 0.075) and f1's
# 0.25), so the terrace sits with the dojo footing without retinting kit 1. Tone variation per stone, light weathered
# tops, darker undersides and moss in the bed joints / on top edges come from the 'Wear' corner colours (stone_tone +
# the tracks' moss passes): every recipe stays an M_DJ_Lib_Opaque instance (Tint, FlattenToMean, MeanColour, moss lerp
# on VertexColor.A, normal strength) in Unreal.
TEX_MEAN = (0.177, 0.155, 0.134)                 # the T_DJ_Granite BC mean (linear, measured)
KIT_MOSS = (0.125, 0.135, 0.036)                 # kit 1's FS_MOSS (the sheet's yellow-olive moss)


def _grey_tint(target, cool=0.0):
    """Per-channel tint that maps the warm Granite BC mean onto a neutral grey `target` (linear), `cool` bluer."""
    return tuple(round(target * (1.0 + (cool if i == 2 else 0.0)) / m, 4) for i, m in enumerate(TEX_MEAN))


KIT1_RATIO = (1.0, 0.876, 0.773)                 # kit 1's M_DK_FootingStone mean (0.097 / 0.085 / 0.075): its warm-grey hue
STONE_RATIO = (1.0, 0.86, 0.74)                  # f2r2: kit 1's footing hue (the owner: tone sits with the dojo footing;
                                                 # MID-GREY, not beige or brown). A warmer (1, 0.82, 0.66) met the
                                                 # reference's daylight saturation but read tan-brown at sunset; the
                                                 # owner's reading outranks SG11's saturation (see BUILD_NOTES f2r2)


def _stone_tint(lum, ratio=STONE_RATIO):
    """f2r2: per-channel tint mapping the Granite BC mean onto a warm MID-GREY with kit 1's footing hue (channel
    ratio KIT1_RATIO) at Rec.709 luminance `lum` (linear). f2's cool-neutral grey (+10 % blue) rendered pink-lilac
    (hue 23 deg, sat 0.27 measured by Scripts/stone/stone_measure.py) against the reference's 30.5 deg / 0.18."""
    y = 0.2126 * ratio[0] + 0.7152 * ratio[1] + 0.0722 * ratio[2]
    return tuple(round(lum * r / y / m, 4) for r, m in zip(ratio, TEX_MEAN))


KIT_MATS = {
    # wall face stones, sangi-zumi, curbs, cheeks, flight / landing sides, the footing course: MID-GREY granite with
    # kit 1's footing hue (the owner: tone sits with the dojo's own footing; kit 1 itself is not retinted)
    "M_DKT_WallGranite": dict(tint=_stone_tint(0.130), flat=0.64, normal=0.28),
    # the coping / cap course: a little darker (the reference's squarer top stones)
    "M_DKT_CopeGranite": dict(tint=_stone_tint(0.108), flat=0.60, normal=0.30),
    # treads, landing flags, kerb tops: LIGHTER walked tops, calm (low normal)
    "M_DKT_StepGranite": dict(tint=_stone_tint(0.185), flat=0.70, normal=0.15),
    # risers and step ends: darker and rougher
    "M_DKT_StepRiser": dict(tint=_stone_tint(0.085), flat=0.66, normal=0.30),
    # the joint core behind the stones: dark earth, flattened hard (no pale pebble specks: kit 1's JointEarth is not used)
    "M_DKT_JointDark": dict(tint=(0.034, 0.032, 0.030), flat=0.90, normal=0.30),
    # f3: moss cushions in the bed joints and on the cap tops (geometry, the owner's "moss in the bed joints and on
    # top edges"; the reference's joint moss is bright yellow-green, hue ~60-75 deg): the same master, the Wear.A lerp
    # driven to ~1 so the moss colour carries it, the granite under it flattened almost away
    "M_DKT_MossPad": dict(tint=(0.05, 0.05, 0.05), flat=0.95, normal=0.45, moss=(0.120, 0.140, 0.036)),
}
BOX_UV_MATS = set(KIT_MATS)                      # box-projected per face (no planar stretch on the stone flanks)

# f2: the timber / lantern variants of library materials (tinted library sets, renamed; Unreal: MI of the library
# master with Tint): darker weathered timber (rails, lantern body), a charcoal hood (the library RoofTile set darkened:
# no rust), warmer amber panes (deeper tint, lower emission so AgX / UE tonemapping keeps the amber instead of peach)
LIB_VARIANTS = {
    "M_DKT_TimberWeathered": ("M_DJ_TimberDark", dict(tint=(0.38, 0.355, 0.34))),       # f3: darker (was 0.48)
    "M_DKT_TimberWeatheredEnd": ("M_DJ_TimberDarkEnd", dict(tint=(0.38, 0.355, 0.34))),
    "M_DKT_HoodCharcoal": ("M_DJ_RoofTile", dict(tint=(0.40, 0.41, 0.45))),
    "M_DKT_GlassAmberWarm": ("M_DJ_GlassAmber", dict(tint=(0.80, 1.0, 0.26), emission_strength=1.15)),
}


def lib_variant(name):
    """A renamed, tinted library material (LIB_VARIANTS); the library original is rebuilt clean under its own name."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    base, ov = LIB_VARIANTS[name]
    had = base in bpy.data.materials
    m = djm.make_material(base, rebuild=True, **ov)
    m.name = name
    djm.make_material(base, rebuild=had)
    m["sk_variant"] = f"library {base} with {ov}"
    return m


def lib_variants():
    for n in LIB_VARIANTS:
        lib_variant(n)
    return list(LIB_VARIANTS)


def kit_material(name):
    """One of the kit's granite recipes (KIT_MATS) through granite_moss_variant (same numbers from every track)."""
    r = KIT_MATS[name]
    VARIANT_NORMAL[name] = r["normal"]
    return granite_moss_variant(name, r["tint"], r["flat"], TEX_MEAN, r.get("moss", KIT_MOSS), normal_strength=r["normal"])


def kit_materials():
    for n in KIT_MATS:
        kit_material(n)
    return list(KIT_MATS)


def granite_moss_variant(name, tint, flat, mean, moss, normal_strength=None):
    """A library Granite variant: BC x tint, lerped `flat` towards the tinted set mean, moss colour lerped in by the
    'Wear' ALPHA before the library wear maths (the kit-1 M_DK_FootingStone recipe, build_kit1.lib_materials), and a
    normal strength (None: VARIANT_NORMAL[name] or 1.0; Unreal: the master's FlattenNormal = 1 - strength). Unreal: an
    M_DJ_Lib_Opaque instance with Tint + FlattenToMean + MeanColour and a moss lerp on VertexColor.A."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    if normal_strength is None:
        normal_strength = VARIANT_NORMAL.get(name, 1.0)
    had = "M_DJ_Granite" in bpy.data.materials
    m = djm.make_material("M_DJ_Granite", rebuild=True, tint=tint, normal_strength=normal_strength)
    m.name = name
    djm.make_material("M_DJ_Granite", rebuild=had)      # a clean library Granite under its own name again
    nt = m.node_tree
    grp = next(n for n in nt.nodes if n.type == "GROUP")
    lk = grp.inputs["Color"].links[0]
    src0 = lk.from_socket
    nt.links.remove(lk)
    fl = nt.nodes.new("ShaderNodeMix")
    fl.data_type = "RGBA"
    fl.inputs["Factor"].default_value = flat
    nt.links.new(src0, fl.inputs["A"])
    fl.inputs["B"].default_value = tuple(a * b for a, b in zip(mean, tint)) + (1.0,)
    attr = next(n for n in nt.nodes if n.type == "ATTRIBUTE" and n.attribute_name == "Wear")
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(attr.outputs["Alpha"], mix.inputs["Factor"])
    nt.links.new(fl.outputs["Result"], mix.inputs["A"])
    mix.inputs["B"].default_value = tuple(moss) + (1.0,)
    nt.links.new(mix.outputs["Result"], grp.inputs["Color"])
    m["dj_set"] = "Granite"
    m["sk_variant"] = "library Granite x tint %s, lerp %.2f to its mean, moss by Wear.A -> %s, normal %.2f" % (
        tint, flat, moss, normal_strength)
    m.diffuse_color = tuple(0.18 * t for t in tint) + (1.0,)
    return m


# ------------------------------------------------------------------------------------------------ mesh build
def _part_offset(pid, salt=0):
    r = random.Random(pid * 7919 + salt * 104729 + 17)
    return r.uniform(0.0, 1.0), r.uniform(0.0, 1.0)


def _box_uv(co, n, tile):
    """The library's box projection (dojo_materials.box_uv): every face upright and unmirrored seen from outside."""
    ax = max(range(3), key=lambda k: abs(n[k]))
    s = 1.0 if n[ax] >= 0 else -1.0
    if ax == 0:
        u, v = s * co.y, co.z
    elif ax == 1:
        u, v = -s * co.x, co.z
    else:
        u, v = co.x, s * co.y
    return u / tile, v / tile


TIMBER_END = {"M_DJ_TimberDark": "M_DJ_TimberDarkEnd", "M_DJ_TimberAged": "M_DJ_TimberAgedEnd",
              "M_DKT_TimberWeathered": "M_DKT_TimberWeatheredEnd"}
UNIT_UV = {"M_DJ_GlassAmber", "M_DJ_ShojiPaper", "M_DKT_GlassAmberWarm"}


def build_mesh(piece, coll, K1):
    """Geo -> mesh object with library UVs, UV1, 'Wear' and UCX children (see the module docstring)."""
    g = piece.g
    mats, face_mat, face_smooth, face_pid = [], [], [], []
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UV0")
    vs = [bm.verts.new(p) for p in g.v]
    bad = 0
    for fi, f in enumerate(g.f):
        try:
            face = bm.faces.new([vs[i] for i in f])
        except ValueError:
            bad += 1
            continue
        m = g.fm[fi]
        if m not in mats:
            mats.append(m)
        face.material_index = mats.index(m)
        face_mat.append(m)
        face_smooth.append(g.fsm[fi] if fi < len(g.fsm) else False)
        face_pid.append(g.fp[fi] if fi < len(g.fp) else 0)
        face.normal_update()
        if m not in BOX_UV_MATS and all(i in g.vuv for i in f):
            for loop, vidx in zip(face.loops, f):
                loop[uvl].uv = g.vuv[vidx]
            continue
        tile = tile_of(m) or 1.0
        pid = g.fp[fi] if fi < len(g.fp) else 0
        ou, ov = _part_offset(pid, sum(map(ord, m)) % 97)
        for loop in face.loops:
            u, v = _box_uv(loop.vert.co, face.normal, tile)
            loop[uvl].uv = (u + ou, v + ov)
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
    mesh = bpy.data.meshes.new(piece.name)
    bm.to_mesh(mesh)
    bm.free()
    for side, end in TIMBER_END.items():
        if side in mats and end not in mats:
            mats.append(end)
    for m in mats:
        mesh.materials.append(bpy.data.materials[m])
    if any(face_smooth):
        mesh.polygons.foreach_set("use_smooth", face_smooth)
    obj = bpy.data.objects.new(piece.name, mesh)
    coll.objects.link(obj)
    for side, end in TIMBER_END.items():
        wood = [i for i, m in enumerate(face_mat) if m == side]
        if wood:
            djm.grain_uv(obj, bpy.data.materials[side]["dj_set"], end_set=bpy.data.materials[end]["dj_set"],
                         faces=wood, end_material_index=mats.index(end), seed=len(piece.name), uv_map="UV0")
    panes = [i for i, m in enumerate(face_mat) if m in UNIT_UV]
    if panes:
        djm.unit_uv(obj, faces=panes, uv_map="UV0")
    for side, end in TIMBER_END.items():          # drop an end-grain slot nothing uses (keeps the FBX slots honest)
        if end in mats and not any(p.material_index == mats.index(end) for p in mesh.polygons):
            idx = mats.index(end)
            if idx == len(mats) - 1:
                mesh.materials.pop(index=idx)
                mats.pop(idx)
    K1.add_uv1(obj)
    wear = djm.bake_wear(obj, ground_z=piece.ground_z)
    obj["wear_bevel_faces"] = wear["bevel_faces"]
    if piece.moss:
        for m, fn in piece.moss.items():
            if m in mats:
                obj[f"moss_faces_{m}"] = fn(obj, mats.index(m))
    tone_mats = [m for m in mats if m in KIT_MATS and m not in ("M_DKT_JointDark", "M_DKT_MossPad")]
    if tone_mats and getattr(piece, "tone", True):
        obj["tone_faces"] = stone_tone(obj, [mats.index(m) for m in tone_mats], face_pid, len(piece.name),
                                       dark_max=getattr(piece, "tone_dark", 0.30))
    add_hulls(obj, piece, coll)
    obj["nanite"] = piece.nanite
    return obj, bad


def add_hulls(obj, piece, coll):
    for i, pts in enumerate(piece.hulls):
        hb = bmesh.new()
        hv = [hb.verts.new(Vector(p)) for p in pts]
        bmesh.ops.convex_hull(hb, input=hv)
        for v in [v for v in hb.verts if not v.link_faces]:
            hb.verts.remove(v)
        hm = bpy.data.meshes.new(f"UCX_{piece.name}_{i:02d}")
        hb.to_mesh(hm)
        hb.free()
        h = bpy.data.objects.new(f"UCX_{piece.name}_{i:02d}", hm)
        coll.objects.link(h)
        h.parent = obj
        h.hide_render = True
        h.display_type = "WIRE"


# ------------------------------------------------------------------------------------------------ QA + export
def qa_piece(obj, texel=5.12, require_uv1=True):
    r = qa_check([obj], require_uv1=require_uv1, texel_density=texel, tolerance=0.25)
    fails = [c for c in r["checks"] if not c["passed"]]
    hard = [c for c in fails if c["name"] not in WAIVE]
    tex = next((c["detail"] for c in r["checks"] if c["name"] == "texel_density"), "")
    return {"hard_fails": [{"name": c["name"], "object": c["object"], "detail": str(c["detail"])[:300]} for c in hard],
            "waived": sorted({c["name"] for c in fails if c["name"] in WAIVE}),
            "tris": r["triangles"].get(obj.name), "texel": tex,
            "texel_library_per_slot": djm.texel_density(obj, uv_map="UV0")}


def export_piece(obj, K1, lods, out_dir=EXPORT_DIR):
    """Export through Scripts/pipeline. lods=False: LOD0 only (Nanite pieces); True: LOD0-2 on temporary copies
    (decimate 0.5 / 0.25, kit 1's LOD fix, UCX renamed UCX_<base>_LOD0_NN), screen sizes in the sidecar."""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = str(out_dir / f"{obj.name}.fbx")
    if not lods:
        r = export_fbx(path, [obj], kind="static", sidecar=False)
        return {"lods": 1, "lod_tris": [sum(len(p.vertices) - 2 for p in obj.data.polygons)],
                "warnings": r["warnings"], "objects": r["objects"], "path": path}
    sc = bpy.context.scene
    tmpc = bpy.data.collections.new("TmpLOD")
    sc.collection.children.link(tmpc)
    name = obj.name
    c0 = obj.copy()
    c0.data = obj.data.copy()
    c0.name = f"{name}_LOD0"
    tmpc.objects.link(c0)
    for h in obj.children:
        hc = h.copy()
        hc.data = h.data.copy()
        hc.name = h.name.replace(f"UCX_{name}_", f"UCX_{name}_LOD0_")
        tmpc.objects.link(hc)
        hc.parent = c0
    lods_ = decimate_lods(c0, (0.5, 0.25))
    for lo in lods_:
        K1.fix_lod(lo)
    grp = make_lod_group(name, [c0] + lods_)
    lq = qa_check([c0] + lods_, require_uv1=True, require_ucx=False)
    lod_hard = [c for c in lq["checks"] if not c["passed"] and c["name"] not in WAIVE]
    r = export_fbx(path, [grp], kind="static", sidecar=True)
    tris = [lq["triangles"].get(x.name) for x in [c0] + lods_]
    rep = {"lods": 3, "lod_tris": tris, "strictly_descending": all(a > b for a, b in zip(tris, tris[1:])),
           "lod_qa_hard_fails": [(c["name"], c["object"], str(c["detail"])[:160]) for c in lod_hard],
           "ucx_names": sorted(ch.name for ch in c0.children), "screen_sizes": r.get("lod_screen_sizes"),
           "warnings": r["warnings"], "sidecar": r.get("sidecar"), "path": path}
    for ob in list(tmpc.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.collections.remove(tmpc)
    return rep


# ------------------------------------------------------------------------------------------------ shared files
@contextlib.contextmanager
def file_lock(target, timeout=600.0):
    """Serialise writers of one shared file (the catalog, the stone-kit blend): an O_EXCL '<file>.lock' next to it.
    A lock older than 30 minutes is treated as stale (a crashed writer)."""
    lk = Path(str(target) + ".lock")
    lk.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    while True:
        try:
            fd = os.open(str(lk), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"{os.getpid()} {time.strftime('%Y-%m-%dT%H:%M:%S')}".encode())
            os.close(fd)
            break
        except FileExistsError:
            try:
                if time.time() - lk.stat().st_mtime > 1800:
                    lk.unlink()
                    continue
            except FileNotFoundError:
                continue
            if time.time() - t0 > timeout:
                raise TimeoutError(f"{lk} held for more than {timeout} s")
            time.sleep(0.5)
    try:
        yield
    finally:
        try:
            lk.unlink()
        except FileNotFoundError:
            pass


def merge_catalog(track, data, piece_prefix):
    """kit_catalog.json: replace tracks[track] with `data['track']` and every piece whose name starts with
    `piece_prefix` with `data['pieces']`; other tracks' entries are kept byte-for-byte (as parsed)."""
    WORK.mkdir(parents=True, exist_ok=True)
    with file_lock(CATALOG):
        cat = {}
        if CATALOG.exists():
            try:
                cat = json.loads(CATALOG.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                bak = CATALOG.with_suffix(".corrupt.json")
                CATALOG.replace(bak)
                cat = {}
        cat.setdefault("kit", "Dojo stone kit (SM_DKT_*): terrace retaining wall (8) + stair path (9)")
        cat.setdefault("units", "metres, +Z up, Blender = Unreal x 100 (cm); Unreal Y = -Blender Y (FBX axis "
                                "conversion by Scripts/pipeline)")
        cat.setdefault("tracks", {})
        cat.setdefault("pieces", {})
        cat["tracks"][track] = data["track"]
        cat["pieces"] = {k: v for k, v in cat["pieces"].items() if not k.startswith(piece_prefix)}
        cat["pieces"].update(data["pieces"])
        cat["pieces"] = dict(sorted(cat["pieces"].items()))
        cat["updated"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        tmp = CATALOG.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps(cat, indent=1), encoding="utf-8")
        os.replace(tmp, CATALOG)
    return CATALOG


def mesh_stats(obj):
    vs = [v.co for v in obj.data.vertices]
    lo = [min(v[i] for v in vs) for i in range(3)]
    hi = [max(v[i] for v in vs) for i in range(3)]
    hulls = []
    for ch in sorted(obj.children, key=lambda c: c.name):
        hv = [v.co for v in ch.data.vertices]
        hulls.append({"name": ch.name, "min": [round(min(v[i] for v in hv), 4) for i in range(3)],
                      "max": [round(max(v[i] for v in hv), 4) for i in range(3)]})
    return {"bbox_min": [round(x, 4) for x in lo], "bbox_max": [round(x, 4) for x in hi],
            "size_m": [round(hi[i] - lo[i], 4) for i in range(3)],
            "tris": sum(len(p.vertices) - 2 for p in obj.data.polygons), "ucx": hulls,
            "slots": [m.name for m in obj.data.materials]}


def moss_noise(co, sc=5.5, off=(3.1, 7.7, 1.3)):
    return noise.noise(co * sc + Vector(off)) * 0.5 + 0.5


def hull_slope(x0, x1, prof):
    """A convex hull from a YZ profile [(y, z), ...] extruded over x0..x1."""
    return [(x, y, z) for x in (x0, x1) for (y, z) in prof]


def rot_z(v, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return Vector((c * v[0] - s * v[1], s * v[0] + c * v[1], v[2]))


# ------------------------------------------------------------------------------------------------ f1: stone language
def stone_tone(obj, slots, face_pid, seed=0, dark_max=0.30, under=0.30, top_g=0.88):
    """Per-stone macro variation on the 'Wear' corner colours (after bake_wear and the moss pass), read by the library
    wear maths in Blender and Unreal alike: every stone (a Geo part) gets its own grime offset in R (0 .. dark_max:
    up to ~12 % darker), downward-facing faces +`under` R (darker undersides), upward faces (normal z > 0.45) edge
    wear G >= top_g (light, weathered tops through the wear mask, patchy). Returns the number of faces touched."""
    me = obj.data
    ca = me.color_attributes["Wear"]
    slots = set(slots)
    cache = {}
    n_f = 0
    for poly in me.polygons:
        if poly.material_index not in slots:
            continue
        pid = face_pid[poly.index] if poly.index < len(face_pid) else 0
        if pid not in cache:
            r = random.Random(pid * 7919 + seed * 104729 + 3)
            cache[pid] = dark_max * (r.random() ** 1.4)
        dk = cache[pid]
        nz = poly.normal.z
        add = dk + (under * clamp01((-nz - 0.30) / 0.4))
        gmin = top_g * clamp01((nz - 0.45) / 0.30)
        n_f += 1
        for li in poly.loop_indices:
            c = ca.data[li].color
            ca.data[li].color = (clamp01(c[0] + add), max(c[1], gmin), c[2], c[3])
    me.update()
    return n_f


class PlaneFace:
    """A flat laying face with the build_wall Face interface: P(a, z) = O + t a + up z, frame -> (t, n, up)."""

    def __init__(self, O, t, n):
        self.O = Vector(O)
        self.t = Vector(t).normalized()
        self.n = Vector(n).normalized()
        self.up = self.n.cross(self.t).normalized()
        self.o = self.n

    def P(self, a, z):
        return self.O + self.t * a + self.up * z

    def frame(self, a, z):
        return self.t, self.n, self.up


def _smooth01(x):
    x = clamp01(x)
    return x * x * (3 - 2 * x)


def _hull2(pts):
    """Convex hull (CCW) of 2D points (monotone chain)."""
    P_ = sorted(set((round(p[0], 6), round(p[1], 6)) for p in pts))
    if len(P_) < 3:
        return P_

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in P_:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 1e-12:
            lo.pop()
        lo.append(p)
    for p in reversed(P_):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 1e-12:
            hi.pop()
        hi.append(p)
    return lo[:-1] + hi[:-1]


def _widths(total, first, last, wmean, rng):
    if total <= 0.0:
        return []
    ws_f = [rng.uniform(*first)] if first else []
    ws_l = [rng.uniform(*last)] if last else []
    if sum(ws_f) + sum(ws_l) > total - 0.22:
        return [total]
    rest = total - sum(ws_f) - sum(ws_l)
    m_ = max(1, int(round(rest / wmean)))
    raw = [rng.uniform(0.62, 1.38) for _ in range(m_)]
    k = rest / sum(raw)
    return ws_f + [w * k for w in raw] + ws_l


def lay_courses(g, F, courses, s_top, s_bot, lohi, pins, seed, stone_fn, clip=None, force_first=None,
                force_last=None, wmean=lambda s: 0.44, amp=(0.030, 0.062), joint_half=(0.0035, 0.0055), knock=0.22):
    """f1 (judge delta 1): irregular POLYGON stones in rough courses (the reference ishigaki: 5-7 sided stones with
    diagonal and rhomboid joints, nested course to course, tight joints). courses: depths s (down = +, z = -s) of the
    course boundaries; the band s_top .. s_bot is laid. lohi(k, sa, sb) -> ((lo_top, lo_bot), (hi_top, hi_bot)): the
    course's end lines. Every course boundary is a zig-zag through the joints of the two courses it separates: it rises
    `amp` under each joint of the course above and drops `amp` over each joint of the course below, so every stone is
    convex (its top bulges up between its own corners, its bottom bulges down) and the neighbours share the boundary
    exactly (joints 2 x joint_half wide). pins: a values where the boundaries stay straight (module ends interlock with
    the neighbour on the global course table). clip: half planes (ka, kz, c): keep ka a + kz z <= c. stone_fn(g, F,
    poly_az, rng, seed) -> 0/1 builds one stone. Returns the number of stones."""
    rng = random.Random(seed)
    ks = [k for k in range(len(courses) - 1) if courses[k] < s_bot - 0.02 and courses[k + 1] > s_top + 0.02]
    if not ks:
        return 0

    def sab(k):
        return max(courses[k], s_top), min(courses[k + 1], s_bot)

    J = {}
    for k in ks:
        sa, sb = sab(k)
        (lo_t, lo_b), (hi_t, hi_b) = lohi(k, sa, sb)
        if hi_t - lo_t < 0.08 and hi_b - lo_b < 0.08:
            continue
        total = ((hi_t + hi_b) - (lo_t + lo_b)) / 2
        first = force_first.get(k % 2) if force_first else None
        last = force_last.get(k % 2) if force_last else None
        ws = _widths(total, first, last, wmean(sa), rng)
        lines = [[lo_t, lo_b, "end"]]
        a = 0.0
        for w in ws[:-1]:
            a += w
            f = a / total
            j = rng.uniform(-0.045, 0.045)
            lines.append([lo_t + (hi_t - lo_t) * f + j, lo_b + (hi_b - lo_b) * f - j, "joint"])
        lines.append([hi_t, hi_b, "end"])
        # stagger: a joint closer than 0.12 to a joint of the course above slides away (stays between its neighbours)
        if k - 1 in J:
            above = [ln[1] for ln in J[k - 1] if ln[2] == "joint"]
            for i in range(1, len(lines) - 1):
                for ab in above:
                    dlt = lines[i][0] - ab
                    if abs(dlt) < 0.12:
                        sh = (0.13 - abs(dlt)) * (1 if dlt >= 0 else -1)
                        lo_ok = lines[i - 1][0] + 0.20
                        hi_ok = lines[i + 1][0] - 0.20
                        if lo_ok < hi_ok:
                            nt = min(max(lines[i][0] + sh, lo_ok), hi_ok)
                            lines[i][1] += nt - lines[i][0]
                            lines[i][0] = nt
        J[k] = lines

    def fade(a):
        return min([_smooth01((abs(a - p) - 0.12) / 0.40) for p in pins] + [1.0])

    B = {}
    for k in ks + [ks[-1] + 1]:
        s0 = courses[k] if k < len(courses) else s_bot
        if s0 <= s_top + 1e-6 or s0 >= s_bot - 1e-6:
            B[k] = (min(max(s0, s_top), s_bot), [])
            continue
        pts = []
        for ln in J.get(k - 1, []):
            if ln[2] == "joint":
                pts.append([ln[1], -rng.uniform(*amp) * fade(ln[1])])
        for ln in J.get(k, []):
            if ln[2] == "joint":
                pts.append([ln[0], rng.uniform(*amp) * fade(ln[0])])
        pts.sort()
        for i in range(len(pts) - 1):                 # opposite kinks too close: both neutral
            if pts[i + 1][0] - pts[i][0] < 0.09 and pts[i][1] * pts[i + 1][1] < 0:
                pts[i][1] = pts[i + 1][1] = 0.0
        B[k] = (s0, pts)

    def s_of(k, a):
        s0, pts = B[k]
        if not pts:
            return s0
        if a <= pts[0][0]:
            f0 = fade(pts[0][0])
            return s0 + (pts[0][1] * fade(a) / f0 if f0 > 1e-3 else 0.0)
        if a >= pts[-1][0]:
            f1 = fade(pts[-1][0])
            return s0 + (pts[-1][1] * fade(a) / f1 if f1 > 1e-3 else 0.0)
        for i in range(len(pts) - 1):
            if pts[i][0] <= a <= pts[i + 1][0]:
                f = (a - pts[i][0]) / max(pts[i + 1][0] - pts[i][0], 1e-9)
                return s0 + pts[i][1] + (pts[i + 1][1] - pts[i][1]) * f
        return s0

    def inner(k, a0, a1):
        s0, pts = B[k]
        return [p[0] for p in pts if a0 + 0.02 < p[0] < a1 - 0.02]

    n = 0
    for k in ks:
        if k not in J:
            continue
        lines = J[k]
        for (lt, lb, _), (rt, rb, _) in zip(lines, lines[1:]):
            if min(rt - lt, rb - lb) < 0.07:
                continue
            poly = [(lb, -s_of(k + 1, lb))]
            poly += [(a, -s_of(k + 1, a)) for a in inner(k + 1, lb, rb)]
            poly += [(rb, -s_of(k + 1, rb)), (rt, -s_of(k, rt))]
            poly += [(a, -s_of(k, a)) for a in reversed(inner(k, lt, rt))]
            poly += [(lt, -s_of(k, lt))]
            poly = _hull2(poly)
            if len(poly) < 3:
                continue
            if rng.random() < knock:                 # a small corner knocked off now and then
                ci = rng.randrange(len(poly))
                m_ = len(poly)
                pc, pa, pb = Vector(poly[ci]), Vector(poly[ci - 1]), Vector(poly[(ci + 1) % m_])
                c = rng.uniform(0.02, 0.05)
                ca_, cb_ = min(c, 0.4 * (pa - pc).length), min(c, 0.4 * (pb - pc).length)
                if ca_ > 0.005 and cb_ > 0.005:
                    poly = poly[:ci] + [tuple(pc + (pa - pc).normalized() * ca_),
                                        tuple(pc + (pb - pc).normalized() * cb_)] + poly[ci + 1:]
            poly = G.clean_poly(poly)
            if len(poly) < 3:
                continue
            ins = G.inset_convex(poly, rng.uniform(*joint_half))
            if ins is None:
                continue
            if clip:
                for (ka, kz, c_) in clip:
                    ins = G.convex_clip(ins, ka, kz, c_)
                    if len(ins) < 3:
                        break
                if len(ins) < 3:
                    continue
                ins = G.clean_poly(ins)
                if len(ins) < 3:
                    continue
            n += stone_fn(g, F, ins, rng, seed * 7919 + n * 31 + k)
    return n


def min_width(poly):
    """The narrowest caliper width of a convex 2D polygon (min over edges of the farthest vertex from that edge)."""
    best = 1e9
    m = len(poly)
    for i in range(m):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % m]
        L = math.hypot(x1 - x0, y1 - y0)
        if L < 1e-9:
            continue
        far = max(abs((x1 - x0) * (y0 - q[1]) - (x0 - q[0]) * (y1 - y0)) / L for q in poly)
        best = min(best, far)
    return best


def dressed_stone(g, F, poly_az, rng, seed, mat, depth=0.22, proud=0.0, step=0.030, tilt=0.035, scale=1.0):
    """f1 (judge delta 1): a dressed face stone on face F from a convex outline [(a, z)]: kit1_geo.pillow_face with the
    judge's numbers: a FLAT crown (bulge <= 1.4 cm, crown exponent 3.5-5), a small crisp arris (8-13 mm quarter round),
    only small corner rounding (Chaikin keep 0.10-0.16), calm relief (2.5 / 0.8 mm), and a small random tilt of the
    whole face (+-2 deg) so neighbours catch the light differently. Built on the face's tangent plane at the centroid."""
    ac = sum(p[0] for p in poly_az) / len(poly_az)
    zc = sum(p[1] for p in poly_az) / len(poly_az)
    P0 = F.P(ac, zc)
    t, n, up = F.frame(ac, zc)
    poly = []
    for (a, z) in poly_az:
        q = F.P(a, z) - P0
        poly.append((q.dot(t), q.dot(up)))
    if abs(G.poly_area(poly)) < 0.0025:
        return 0
    w = max(p[0] for p in poly) - min(p[0] for p in poly)
    h = max(p[1] for p in poly) - min(p[1] for p in poly)
    s_ = min(w, h)
    if s_ < 0.05:
        return 0
    if min_width(poly) < 0.06:                  # a clipped sliver or wedge (its narrowest caliper width < 6 cm): skip
        return 0
    v0 = len(g.v)
    r = G.pillow_face(g, poly, P0, t, n, depth, 0.010 * scale + rng.uniform(0.0, 0.008) * scale + proud,
                      min(0.014, max(0.005, 0.030 * s_)) * scale, seed, mat,
                      edge=rng.uniform(0.008, 0.013), rough=0.0025 * scale, fine=0.0008 * scale,
                      step=step, rounds=2, keep=rng.uniform(0.10, 0.16), crown=rng.uniform(3.5, 5.0),
                      wobble=0.002, peak_off=0.20, uv_off=(rng.uniform(0, 1), rng.uniform(0, 1)))
    if r is None:
        return 0
    if tilt:
        from mathutils import Matrix
        M = Matrix.Rotation(rng.uniform(-tilt, tilt), 3, t) @ Matrix.Rotation(rng.uniform(-tilt, tilt), 3, up)
        for i in range(v0, len(g.v)):
            g.v[i] = P0 + M @ (g.v[i] - P0)
    return 1


def rigid_warp(g, fn, v_from=0):
    """Move every Geo part (one add() call: one stone) rigidly by fn(its centroid), so a curved batter / flare never
    shears a stone (judge delta 9); parts are found from g.fp over the faces added after vertex v_from."""
    parts = {}
    for fi, f in enumerate(g.f):
        if f[0] < v_from:
            continue
        parts.setdefault(g.fp[fi], set()).update(f)
    for pid, vs in parts.items():
        c = sum((g.v[i] for i in vs), Vector()) / len(vs)
        d_ = fn(c)
        for i in vs:
            g.v[i] = g.v[i] + d_
    return g


# ------------------------------------------------------------------------------------------------ f2: rounded stones
# The owner's reading (2026-09-30): the reference ishigaki is ROUNDED pillow-faced granite like round 0 (not f1's flat
# many-sided polygons), with more varied sizes and aspect (some upright ovals taller than wide, some long), dark deep
# joints of about 2-4 cm. lay_rounded is round 0's course layer (build_wall.lay_face_r0: rounded quads in rough courses
# with wandering boundaries, some tall stones through two courses, a corner knocked off now and then) made track-neutral,
# without the packing chips, with a mixed width distribution; pillow_stone is round 0's body stone.
class Boundary:
    """A course boundary s(a): the course depth s0, wandering +-amp between the pins (piece ends, corners)."""

    def __init__(self, s0, a_lo, a_hi, pins, rng, amp):
        self.s0, self.pins = s0, pins
        self.cp = []
        a = a_lo - 0.6
        while a < a_hi + 0.6:
            self.cp.append((a, rng.uniform(-amp, amp)))
            a += rng.uniform(0.55, 0.85)
        self.cp.append((a, rng.uniform(-amp, amp)))

    def __call__(self, a):
        cp = self.cp
        w = 0.0
        for i in range(len(cp) - 1):
            if cp[i][0] <= a <= cp[i + 1][0]:
                f = (a - cp[i][0]) / (cp[i + 1][0] - cp[i][0])
                w = cp[i][1] + (cp[i + 1][1] - cp[i][1]) * f
                break
        tp = min([_smooth01((abs(a - p) - 0.15) / 0.45) for p in self.pins] + [1.0])
        return self.s0 + w * tp


def mixed_widths(total, first, last, ch, rng, mix=(0.24, 0.58)):
    """Stone widths summing to `total` for a course of height ch: about 24 % upright stones (0.62-0.85 ch: taller than
    wide), 58 % ordinary (1.0-1.45 ch), 18 % long (1.7-2.3 ch); optional forced first / last widths (corner stones)."""
    if total <= 0.0:
        return []
    ws_f = [rng.uniform(*first)] if first else []
    ws_l = [rng.uniform(*last)] if last else []
    if sum(ws_f) + sum(ws_l) > total - 0.22:
        return [total]
    rest = total - sum(ws_f) - sum(ws_l)
    raw = []
    while sum(raw) < rest - 0.5 * ch:
        r = rng.random()
        if r < mix[0]:
            w = ch * rng.uniform(0.62, 0.85)
        elif r < mix[0] + mix[1]:
            w = ch * rng.uniform(1.0, 1.45)
        else:
            w = ch * rng.uniform(1.7, 2.3)
        raw.append(max(0.20, w))
    if not raw:
        raw = [rest]
    k = rest / sum(raw)
    return ws_f + [w * k for w in raw] + ws_l


def _cut_corner(poly, i, c):
    m = len(poly)
    p, pa, pb = Vector(poly[i]), Vector(poly[i - 1]), Vector(poly[(i + 1) % m])
    ea, eb = (pa - p), (pb - p)
    ca, cb = min(c, 0.45 * ea.length), min(c, 0.45 * eb.length)
    q1, q2 = p + ea.normalized() * ca, p + eb.normalized() * cb
    return poly[:i] + [tuple(q1), tuple(q2)] + poly[i + 1:]


def lay_rounded(g, F, courses, s_top, s_bot, lohi, pins, seed, stone_fn, clip=None, force_first=None,
                force_last=None, amp=0.045, tall_p=0.22, joint=(0.004, 0.0065), knock=0.35):
    """f2: lay rounded face stones on face F (P(a, z), frame) between depths s_top .. s_bot (z = -s) in the course
    table `courses`. lohi(k, sa, sb) -> ((lo_top, lo_bot), (hi_top, hi_bot)): the course's end lines. pins: a values
    where the boundaries stay exactly on the table (module ends interlock). clip: half planes (ka, kz, c): keep
    ka a + kz z <= c. joint: the half joint inset per stone (0.4-0.65 cm: 0.8-1.3 cm between rims, 2-4 cm of visible
    dark joint once the pillow shoulders and rounded corners fall away). stone_fn(g, F, poly_az, rng, seed) -> 0/1. Returns the count."""
    rng = random.Random(seed)
    ks = [k for k in range(len(courses) - 1) if courses[k] < s_bot - 0.02 and courses[k + 1] > s_top + 0.02]
    if not ks:
        return 0

    def sab(k):
        return max(courses[k], s_top), min(courses[k + 1], s_bot)
    bounds = {}
    for k in ks + [ks[-1] + 1]:
        s0 = courses[k] if k < len(courses) else s_bot
        if s0 <= s_top + 1e-6 or s0 >= s_bot - 1e-6:
            s0 = min(max(s0, s_top), s_bot)
            bounds[k] = (lambda a, s0=s0: s0)
        else:
            bounds[k] = Boundary(s0, -12.0, 12.0, pins, rng, amp)
    talls = {}                                  # upright stones through two courses (pairs (0,1), (2,3), ...)
    for k in ks[:-1]:
        if k % 2 or k + 1 not in ks or courses[k + 2] > s_bot + 0.05:
            continue
        (lo1, _), (hi1, _) = lohi(k, *sab(k))
        (lo2, _), (hi2, _) = lohi(k + 1, *sab(k + 1))
        lo, hi = max(lo1, lo2) + 0.40, min(hi1, hi2) - 0.40
        a = lo + rng.uniform(0.0, 0.9)
        lst = []
        ch2 = courses[k + 2] - courses[k]
        while a + 0.30 < hi:
            if any(abs(a - p) < 0.5 for p in pins):
                a += 0.35
                continue
            if rng.random() < tall_p:
                w = ch2 * rng.uniform(0.48, 0.66)      # an upright oval: clearly taller than wide
                if a + w > hi:
                    break
                jl, jr = rng.uniform(-0.02, 0.02), rng.uniform(-0.02, 0.02)
                lst.append(((a + jl, a - jl), (a + w + jr, a + w - jr)))
                a += w + rng.uniform(1.0, 2.0)
            else:
                a += rng.uniform(0.6, 1.2)
        if lst:
            talls[k] = lst

    def clipped(poly):
        if not clip:
            return poly
        for (ka, kz, c_) in clip:
            poly = G.convex_clip(poly, ka, kz, c_)
            if len(poly) < 3:
                return None
        poly = G.clean_poly(poly)
        return poly if len(poly) >= 3 else None

    def one(quad, sd):
        poly = list(quad)
        if rng.random() < knock:
            poly = _cut_corner(poly, rng.randrange(len(poly)), rng.uniform(0.025, 0.06))
        poly = G.clean_poly(poly)
        if len(poly) < 3:
            return 0
        inner = G.inset_convex(poly, rng.uniform(*joint))
        if inner is None:
            return 0
        inner = clipped(inner)
        if inner is None:
            return 0
        return stone_fn(g, F, inner, rng, sd)

    n = 0
    for k in ks:
        sa, sb = sab(k)
        s_up, s_dn = bounds[k], bounds[k + 1]
        (lo_t, lo_b), (hi_t, hi_b) = lohi(k, sa, sb)
        if hi_t - lo_t < 0.08 and hi_b - lo_b < 0.08:
            continue
        blocks = sorted(list(talls.get(k, [])) + list(talls.get(k - 1, [])), key=lambda b: b[0][0])
        segs, left, lkind = [], (lo_t, lo_b), "end"
        for (bl, br) in blocks:
            segs.append((left, bl, lkind, "tall"))
            left, lkind = br, "tall"
        segs.append((left, (hi_t, hi_b), lkind, "end"))
        ch = max(0.12, sb - sa)
        for si, (L, R_, lk, rk) in enumerate(segs):
            if min(R_[0] - L[0], R_[1] - L[1]) < 0.06:
                continue
            first = force_first.get(k % 2) if (force_first and si == 0 and lk == "end") else None
            last = force_last.get(k % 2) if (force_last and si == len(segs) - 1 and rk == "end") else None
            total = (R_[0] + R_[1]) / 2 - (L[0] + L[1]) / 2
            ws = mixed_widths(total, first, last, ch, rng)
            lines = [(L[0], L[1])]
            a = 0.0
            for w in ws[:-1]:
                a += w
                f = a / total
                j = rng.uniform(-0.035, 0.035)
                lines.append((L[0] + (R_[0] - L[0]) * f + j, L[1] + (R_[1] - L[1]) * f - j))
            lines.append((R_[0], R_[1]))
            for (lt, lb), (rt, rb) in zip(lines, lines[1:]):
                if min(rt - lt, rb - lb) < 0.07:
                    continue
                quad = [(lb, -s_dn(lb)), (rb, -s_dn(rb)), (rt, -s_up(rt)), (lt, -s_up(lt))]
                n += one(quad, seed * 7919 + n * 31 + k)
    for k, lst in talls.items():
        for (bl, br) in lst:
            s_up, s_dn = bounds[k], bounds[k + 2]
            quad = [(bl[1], -s_dn(bl[1])), (br[1], -s_dn(br[1])), (br[0], -s_up(br[0])), (bl[0], -s_up(bl[0]))]
            n += one(quad, seed * 131 + n)
    return n


def pillow_stone(g, F, poly_az, rng, seed, mat, depth=0.24, scale=1.0, rough=(0.0040, 0.0058)):
    """f2: round 0's body stone (build_wall.face_stone_r0): a rounded pillow on face F's tangent plane at the outline's
    centroid (kit1_geo.pillow_face): rounded corners (Chaikin keep 0.14-0.24), a full crown (bulge 1.5-4 cm, crown
    exponent 2-3), a soft 18-28 mm shoulder, granular relief a little calmer than r0 (4-6 mm)."""
    ac = sum(p[0] for p in poly_az) / len(poly_az)
    zc = sum(p[1] for p in poly_az) / len(poly_az)
    P0 = F.P(ac, zc)
    t, n, up = F.frame(ac, zc)
    poly = []
    for (a, z) in poly_az:
        q = F.P(a, z) - P0
        poly.append((q.dot(t), q.dot(up)))
    if abs(G.poly_area(poly)) < 0.0025:
        return 0
    w = max(p[0] for p in poly) - min(p[0] for p in poly)
    h = max(p[1] for p in poly) - min(p[1] for p in poly)
    s_ = min(w, h)
    if s_ < 0.05:
        return 0
    step = min(0.032, max(0.021, 0.018 + 0.022 * s_))
    r = G.pillow_face(g, poly, P0, t, n, depth, (0.018 + rng.uniform(0.0, 0.018)) * scale,
                      min(0.040, max(0.015, 0.07 * s_ + rng.uniform(-0.004, 0.006))) * scale, seed, mat,
                      edge=rng.uniform(0.014, 0.022) * min(1.0, scale * 1.2), rough=rng.uniform(*rough) * scale,
                      fine=0.0018 * scale, step=step, rounds=2, keep=rng.uniform(0.14, 0.24), crown=rng.uniform(2.0, 3.0),
                      wobble=0.004, peak_off=0.12, uv_off=(rng.uniform(0, 1), rng.uniform(0, 1)))
    return int(r is not None)


def fold_into_kit():
    """f2: fold the '<name>.001' datablocks an appended track collection brings into Assets/Dojo/DojoStoneKit.blend.
    The stone kit's OWN recipes (KIT_MATS, LIB_VARIANTS) take the NEW copy (the old one is remapped onto it and
    removed: before f2 the old definitions won, so a retuned recipe never reached the kit blend); library materials,
    images and node groups fold onto the originals as before (identical library data)."""
    own = set(KIT_MATS) | set(LIB_VARIANTS)
    n = 0
    for coll_ in (bpy.data.materials, bpy.data.images, bpy.data.node_groups):
        for d_ in list(coll_):
            base, _, suf = d_.name.rpartition(".")
            if not (base and suf.isdigit() and len(suf) == 3 and base in coll_):
                continue
            if coll_ is bpy.data.materials and base in own:
                old = coll_[base]
                old.user_remap(d_)
                coll_.remove(old)
                d_.name = base
            else:
                d_.user_remap(coll_[base])
                coll_.remove(d_)
            n += 1
    return n


def drop_collection_for_append(name):
    """f2: remove a track collection from the open kit blend COMPLETELY before re-appending it: its objects, their
    meshes, the kit's own materials (KIT_MATS / LIB_VARIANTS) and every orphan. Blender re-uses datablocks it
    appended earlier from the same source file (weak library references), so leaving the old meshes / materials as
    orphans let a re-append pick the stale ones up (the f2-dev kit blend kept f1-era recipes)."""
    old = bpy.data.collections.get(name)
    meshes = set()
    if old is not None:
        for o in list(old.all_objects):
            if o.type == "MESH":
                meshes.add(o.data)
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(old)
    for me in meshes:
        if me.users == 0:
            bpy.data.meshes.remove(me)
    for m in set(KIT_MATS) | set(LIB_VARIANTS):
        mat = bpy.data.materials.get(m)
        if mat is not None and mat.users == 0:
            bpy.data.materials.remove(mat)
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)


# ------------------------------------------------------------------------------------------------ f2 round 2: study
# STONE_BUILDING_STUDY.md (2026-09-30) 4.4 / 4.5 / 8.2, applied to the owner's reading: the layout comes from the
# shared, track-neutral Scripts/stone/stone_layout.py (measured h/w mixture of the traced terrace: upright share ~0.70,
# leaning joints, broken courses, per-corner cuts), the stones from pillow_stone_v2 (per-corner radius through the
# layout's corner cuts, asymmetric crown with its peak toward the top edge, crown height 6-14 % of the short side with a
# CV >= 0.3, a small per-stone tilt so neighbours catch the light differently). LAYOUT_LOG collects every stone's 2D
# outline (face coordinates a, z) with its crown and corner cuts for the flat layout gates (stone_measure.layout_shapes).
if str(SCRIPTS / "stone") not in sys.path:
    sys.path.insert(0, str(SCRIPTS / "stone"))
import stone_layout as SL  # noqa: E402

LAYOUT_LOG = {"piece": None, "zones": {}}
_LAST = {}


def layout_reset(piece):
    LAYOUT_LOG["piece"] = piece
    LAYOUT_LOG["zones"] = {}


def layout_add(zone, poly, crown=None, corner_r=None, kind=None, z_top=None, z_bot=None):
    z = LAYOUT_LOG["zones"].setdefault(zone, {"stones": [], "z_top": z_top, "z_bot": z_bot})
    if z_top is not None:
        z["z_top"], z["z_bot"] = z_top, z_bot
    z["stones"].append({"poly": [tuple(p) for p in poly], "crown": crown, "corner_r": corner_r, "kind": kind})


def pillow_stone_v2(g, F, poly_az, rng, seed, mat, depth=0.24, scale=1.0, crown_k=(0.06, 0.26), tilt=(0.055, 0.035),
                    proud=(0.016, 0.032), rough=(0.0030, 0.0046), keep=(0.14, 0.22)):
    """f2r2: a rounded pillow stone (kit1_geo.pillow_face) from an outline that already carries per-corner cuts:
    Chaikin 2 rounds (keep 0.13-0.20) turn the cut corners into egg / lens outlines of varying radius; the crown rises
    crown_k x the short side (clamped 1.2-4.8 cm) with a rounded profile (exponent 2.0-2.8: below 2 the apex turns into a pyramid crease) and its peak 15-30 % off
    centre toward the top edge (the lit crown / shaded lower rim of the reference); the stone is then tilted rigidly by
    up to tilt[0] rad about the face's along axis and tilt[1] about its up axis. _LAST['crown'] holds the crown."""
    ac = sum(p[0] for p in poly_az) / len(poly_az)
    zc = sum(p[1] for p in poly_az) / len(poly_az)
    P0 = F.P(ac, zc)
    t, n, up = F.frame(ac, zc)
    poly = []
    for (a, z) in poly_az:
        q = F.P(a, z) - P0
        poly.append((q.dot(t), q.dot(up)))
    if abs(G.poly_area(poly)) < 0.0020:
        return 0
    w = max(p[0] for p in poly) - min(p[0] for p in poly)
    h = max(p[1] for p in poly) - min(p[1] for p in poly)
    s_ = min(w, h)
    if s_ < 0.05 or min_width(poly) < 0.05:
        return 0
    step = min(0.030, max(0.019, 0.016 + 0.022 * s_))
    bulge = max(0.015, min(0.060, rng.uniform(*crown_k) * s_)) * scale
    v0 = len(g.v)
    kp = rng.uniform(*keep)
    # (the rng draw order is unchanged from f2r2: proud, edge, rough, keep, crown, peak, uv)
    r = G.pillow_face(g, poly, P0, t, n, depth, rng.uniform(*proud) * scale, bulge, seed, mat,
                      edge=rng.uniform(0.012, 0.020) * min(1.0, scale * 1.2), rough=rng.uniform(*rough) * scale,
                      fine=0.0012 * scale, step=step, rounds=2, keep=kp, crown=rng.uniform(2.0, 2.8),
                      wobble=0.004, peak_off=rng.uniform(0.15, 0.30), uv_off=(rng.uniform(0, 1), rng.uniform(0, 1)))
    if r is None:
        return 0
    if tilt and (tilt[0] or tilt[1]):
        from mathutils import Matrix
        M = Matrix.Rotation(rng.uniform(-tilt[0], tilt[0]), 3, t) @ Matrix.Rotation(rng.uniform(-tilt[1], tilt[1]), 3, up)
        for i in range(v0, len(g.v)):
            g.v[i] = P0 + M @ (g.v[i] - P0)
    _LAST["crown"] = round(bulge, 4)
    _LAST["keep"] = kp
    return 1


# ------------------------------------------------------------------------------------------------ f3: fitted + moss
# STONE KIT f3 (2026-09-30; STONE_BUILDING_STUDY 4.5, the judge-steer-checked deltas): the terrace stones FIT their
# neighbours (Scripts/stone/stone_layout.coursed_fitted: Y-junctions, shared outlines), 1.1-1.5 cm between the rims
# (f2: 1.6-2.2 cm plus a dark triangle at every T-junction), a gentler corner rounding (Chaikin keep 0.12-0.18); moss
# CUSHIONS in the bed joints (moss_pad, M_DKT_MossPad) where the owner reads "moss and dirt in the bed joints".
MOSS_MAT = "M_DKT_MossPad"


def _resample_line(pts, step):
    out = [pts[0]]
    for p, q in zip(pts, pts[1:]):
        L = math.hypot(q[0] - p[0], q[1] - p[1])
        k = max(1, int(math.ceil(L / step)))
        for j in range(1, k + 1):
            out.append((p[0] + (q[0] - p[0]) * j / k, p[1] + (q[1] - p[1]) * j / k))
    return out


def moss_pad(g, F, line_az, rng, seed, width=(0.032, 0.052), thick=(0.012, 0.022), front=(0.016, 0.028),
             step=0.016, mat=MOSS_MAT):
    """A lumpy moss cushion lying in a joint of face F along the polyline line_az [(a, z)] (the joint centre): an
    8-sided tube whose half-width `width` spills a little over both stone rims and whose front bulges `front` +
    `thick` out of the face plane (below the stones' crowns), tapering to points at both ends, radius noised in two
    octaves. Smooth-shaded; the Wear alpha is set by the track's moss pass for `mat`."""
    pts = _resample_line(line_az, step)
    if len(pts) < 3:
        return 0
    L = sum(math.hypot(q[0] - p[0], q[1] - p[1]) for p, q in zip(pts, pts[1:]))
    if L < 0.06:
        return 0
    off = Vector((seed * 0.37, seed * 0.19, seed * 0.53))
    rw, rt, fr = rng.uniform(*width), rng.uniform(*thick), rng.uniform(*front)
    NS = 8
    rings = []
    acc = 0.0
    for i, (a, z) in enumerate(pts):
        if i:
            acc += math.hypot(a - pts[i - 1][0], z - pts[i - 1][1])
        if i == 0 or i == len(pts) - 1:       # the end points are the caps' apexes (no collapsed rings)
            continue
        u = acc / L
        taper = math.sin(math.pi * min(1.0, max(0.0, u))) ** 0.55
        pa, pb = pts[max(0, i - 1)], pts[min(len(pts) - 1, i + 1)]
        ta = (pb[0] - pa[0], pb[1] - pa[1])
        tl = math.hypot(*ta) or 1.0
        side = (-ta[1] / tl, ta[0] / tl)                  # in-plane normal to the joint line
        P0 = F.P(a, z)
        t_, n_, up_ = F.frame(a, z)
        sv = t_ * side[0] + up_ * side[1]
        C = P0 + n_ * fr
        ring = []
        for k in range(NS):
            ang = 2 * math.pi * k / NS
            q = C + sv * (math.cos(ang) * rw) + n_ * (math.sin(ang) * rt)
            # f3: clumps along the joint (a low-frequency swell) + lumps + fine knobs: a cushion, not a smooth tube
            clump = 0.75 + 0.45 * (noise.noise(P0 * 9.0 + off * 0.3) * 0.5 + 0.5)
            lump = 1.0 + 0.40 * noise.noise(q * 34.0 + off) + 0.22 * noise.noise(q * 95.0 + off * 1.7)
            ring.append(C + (q - C) * (taper * clump * max(0.25, lump)))
        rings.append(ring)
    a0, z0 = pts[0]
    a1, z1 = pts[-1]
    n0 = F.frame(a0, z0)[1]
    n1 = F.frame(a1, z1)[1]
    verts = [F.P(a0, z0) + n0 * fr]
    for ring in rings:
        verts.extend(ring)
    verts.append(F.P(a1, z1) + n1 * fr)
    nr = len(rings)
    faces = []
    for k in range(NS):
        faces.append((0, 1 + (k + 1) % NS, 1 + k))
    for i in range(nr - 1):
        b0, b1 = 1 + i * NS, 1 + (i + 1) * NS
        for k in range(NS):
            k2 = (k + 1) % NS
            faces.append((b0 + k, b0 + k2, b1 + k2, b1 + k))
    last = len(verts) - 1
    bl = 1 + (nr - 1) * NS
    for k in range(NS):
        faces.append((bl + k, bl + (k + 1) % NS, last))
    # orient outward: a face on the middle ring must point away from the ring's centre
    mi = nr // 2
    ctr = sum(rings[mi], Vector()) / NS
    f_ = faces[NS + mi * NS]
    a_, b_, c_ = verts[f_[0]], verts[f_[1]], verts[f_[2]]
    if (b_ - a_).cross(c_ - a_).dot(((a_ + b_ + c_) / 3) - ctr) < 0:
        faces = [tuple(reversed(f)) for f in faces]
    g.add(verts, faces, mat, F.frame(*pts[len(pts) // 2]), smooth=set(range(len(faces))))
    return 1


def _upper_chain(poly):
    """The polygon's upward-facing edges (outward normal z > 0.45) as one chain of points, left to right."""
    if G.poly_area(poly) < 0:
        poly = list(reversed(poly))
    n = len(poly)
    up = []
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        ex, ez = q[0] - p[0], q[1] - p[1]
        L = math.hypot(ex, ez)
        if L < 1e-6:
            continue
        if -ex / L > 0.45:                    # CCW: the outward normal is (ez, -ex) / L
            up.append(i)
    if not up:
        return None
    idx = set(up)
    start = next((i for i in up if (i - 1) % n not in idx), up[0])
    chain = [poly[start]]
    i = start
    while i in idx:
        chain.append(poly[(i + 1) % n])
        i = (i + 1) % n
        if i == start:
            break
    return list(reversed(chain))


def _cut_line(ch, u0, u1):
    out, acc = [], 0.0
    for p, q in zip(ch, ch[1:]):
        L = math.hypot(q[0] - p[0], q[1] - p[1])
        if L < 1e-9:
            continue
        for u in (u0, u1):
            if acc <= u <= acc + L:
                f = (u - acc) / L
                out.append(((p[0] + (q[0] - p[0]) * f, p[1] + (q[1] - p[1]) * f), u))
        if u0 < acc + L < u1:
            out.append((q, acc + L))
        acc += L
    out.sort(key=lambda x: x[1])
    return [p for p, _ in out]


def lay_measured(g, F, courses, s_top, s_bot, lohi, pins, seed, stone_fn, clip=None, force_first=None,
                 force_last=None, joint=(0.0065, 0.0085), zone="body", method="fitted", pad_p=None, **kw):
    """f3: lay rounded face stones on face F between depths s_top .. s_bot. method "fitted" (default):
    Scripts/stone/stone_layout.coursed_fitted (fitted outlines, Y-junctions); "coursed": f2r2's coursed_rounded. Each
    outline (convex hull) is inset by its own half joint (0.55-0.75 cm: 1.1-1.5 cm between rims; with the shoulders
    about 2-3 cm of visible dark joint), clipped, and built by stone_fn(g, F, poly_az, rng, seed) -> 0/1. pad_p(a, z)
    -> probability: a moss cushion (moss_pad) along part of the stone's upper joint (the bed joint above it). Every
    built stone goes to LAYOUT_LOG[zone] as its ROUNDED outline (what the eye sees). Returns the count."""
    rng = random.Random(seed * 31 + 7)
    if method == "fitted":
        stones = SL.coursed_fitted(courses, s_top, s_bot, lohi, pins, seed, force_first=force_first,
                                   force_last=force_last, **kw)
    else:
        stones = SL.coursed_rounded(courses, s_top, s_bot, lohi, pins, seed, force_first=force_first,
                                    force_last=force_last, **kw)
    prng = random.Random(seed * 131 + 5)
    n = 0

    def inside(a, z):
        return all(ka * a + kz * z <= c_ + 1e-9 for (ka, kz, c_) in (clip or ()))
    for i, st in enumerate(stones):
        raw = SL.convex_hull(st["poly"]) if method == "fitted" else st["poly"]
        poly = G.clean_poly(raw, min_edge=0.006)
        if len(poly) < 3:
            continue
        inner = G.inset_convex(poly, rng.uniform(*joint))
        if inner is None or len(inner) < 3:
            continue
        if clip:
            for (ka, kz, c_) in clip:
                inner = G.convex_clip(inner, ka, kz, c_)
                if len(inner) < 3:
                    break
            if len(inner) < 3:
                continue
            inner = G.clean_poly(inner, min_edge=0.006)
            if len(inner) < 3:
                continue
        _LAST.clear()
        ok = stone_fn(g, F, inner, rng, seed * 7919 + i * 31 + st["course"])
        if not ok:
            continue
        n += 1
        kp = _LAST.get("keep")
        shown = G.chaikin(inner, 2, kp) if kp else inner
        if st.get("cuts"):
            cr = [round(c, 4) for c in st["cuts"]]
        else:                                  # fitted: the Chaikin rounding per corner ~ keep x the shorter edge
            m = len(inner)
            cr = [round(1.2 * (kp or 0.15) * min(math.hypot(inner[j][0] - inner[j - 1][0], inner[j][1] - inner[j - 1][1]),
                                                   math.hypot(inner[(j + 1) % m][0] - inner[j][0],
                                                              inner[(j + 1) % m][1] - inner[j][1])), 4)
                  for j in range(m)]
        layout_add(zone, shown, _LAST.get("crown"), cr, st["kind"], z_top=-s_top, z_bot=-s_bot)
        if pad_p is not None:
            ch = _upper_chain(poly)
            if ch and len(ch) >= 2:
                ac = sum(p[0] for p in ch) / len(ch)
                zc = sum(p[1] for p in ch) / len(ch)
                if prng.random() < pad_p(ac, zc):
                    Lc = sum(math.hypot(q[0] - p[0], q[1] - p[1]) for p, q in zip(ch, ch[1:]))
                    frac = prng.uniform(0.40, 0.95)
                    u0 = prng.uniform(0.0, 1.0 - frac) * Lc
                    pts = [p for p in _cut_line(ch, u0, u0 + frac * Lc) if inside(*p)]
                    if len(pts) >= 2:
                        moss_pad(g, F, pts, prng, seed * 17 + i)
    return n


def write_layout(path):
    """The stone_layout/1 JSON of the last piece (Scripts/stone/stone_measure.py shapes <file>)."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(SL.layout_json(LAYOUT_LOG["piece"], LAYOUT_LOG["zones"]), indent=1),
                          encoding="utf-8")
    return path
