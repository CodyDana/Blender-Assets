"""ROUND 5 OUTSIDE track (2026-09-29): shared helpers for Scripts/dojo/outside/build_outside.py (SM_DKX_*).

Reuses, read-only (never forked):
  Scripts/dojo/roof/kit_mesh.py      Piece container, chamfered-box primitives, stone_uv, add_uv1, fix_lod
  Scripts/dojo/materials             the shared dojo material library (M_DJ_*)
  Exports/DojoKit/Ground/Textures    the ground kit's soil set + macro map (T_DKG_Soil_*, T_DKG_Macro_M)
New here (this track's own, Exports/DojoKit/Outside/Textures): T_DKX_Cobble_{BC,N,ORM} (ox_tex.py).

Material instances this track adds (recipes in layout_outside.json 'materials', on the showcase's EXISTING masters in
Scripts/dojo/unreal/dj_sc_materials.py; no new master):
  M_DKX_RoadCobble   M_DJ_GroundXY_Master  T_DKX_Cobble on world XY / 4 m (+ macro)   the approach road
  M_DKX_VergeSoil    M_DJ_GroundXY_Master  the ground kit's soil set, darker, moister  wall-foot verges, outside ground
  M_DKX_LaneEarth    M_DJ_GroundXY_Master  the soil set, desaturated and lifted       side lanes, the lower lane
  M_DKX_Water        M_DJ_Flat_Master      dark, glossy                               the canal below the terrace
  M_DKX_MountainNear M_DJ_Flat_Master      blue-grey, rough                           near ridge ring (height fog tints it)
  M_DKX_MountainFar  M_DJ_Flat_Master      paler blue-grey                            far ridge ring
  M_DKX_FarGround    M_DJ_Flat_Master      dark olive grey                            the plain between the town and the ridges
The Blender previews below follow the Unreal masters' maths (GroundXY: BC x Tint x macro tint, Saturation about the
pixel's luminance, x ValueMult). The mountain previews add an aerial-perspective mix by camera distance that stands in
for DojoLab's ExponentialHeightFog (Blender renders only; the Unreal material is the flat colour).
"""
import json
import math
import sys
import time
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[3]
for _p in (ROOT / "Scripts", ROOT / "Scripts" / "dojo", ROOT / "Scripts" / "dojo" / "roof",
           ROOT / "Scripts" / "dojo" / "materials"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from pipeline.export_fbx import export_fbx  # noqa: E402
from pipeline.qa_check import qa_check  # noqa: E402
from pipeline.helpers import decimate_lods, make_lod_group  # noqa: E402
import dojo_materials as djm  # noqa: E402
import kit_mesh as KM  # noqa: E402

WORK = ROOT / "WorkFiles" / "dojo" / "build"
OXW = WORK / "outside"
TEX_OUT = ROOT / "Exports" / "DojoKit" / "Outside" / "Textures"
GROUND_TEX = ROOT / "Exports" / "DojoKit" / "Ground" / "Textures"
SHOWCASE_BLEND = ROOT / "Assets" / "Dojo" / "DojoShowcase.blend"
SHOWCASE_LAYOUT = WORK / "showcase" / "layout_showcase.json"
UE_ROOT = "/Game/DojoKit/Outside"

ROAD, VERGE, LANE = "M_DKX_RoadCobble", "M_DKX_VergeSoil", "M_DKX_LaneEarth"
WATER, MNEAR, MFAR, FARG = "M_DKX_Water", "M_DKX_MountainNear", "M_DKX_MountainFar", "M_DKX_FarGround"
KAWARA = "M_DKX_Kawara"
PLE = "M_DJ_PlasterEarth"
GROUND_XY = (ROAD, VERGE, LANE)          # UV0 = world XY / 4 m (the master samples world XY / 400 cm itself)
FLAT = (WATER, MNEAR, MFAR, FARG)        # flat colour masters: UV0 = world XY / 4 m (only for the pipeline's UV gate)


def _lin(s):
    return round((s / 255.0) / 12.92 if s / 255.0 <= 0.04045 else ((s / 255.0 + 0.055) / 1.055) ** 2.4, 5)


def lin3(rgb):
    return [_lin(c) for c in rgb]


_MAT_DIR = UE_ROOT + "/Materials"
_GX_TEX = {"Macro Map": "T_DKG_Macro_M"}
RECIPES = {
    ROAD: {"master": "M_DJ_GroundXY_Master", "kit": "outside", "ue_dir": _MAT_DIR,
           "textures": {"Base Colour Map": "T_DKX_Cobble_BC", "ORM Map": "T_DKX_Cobble_ORM",
                        "Normal Map": "T_DKX_Cobble_N", **_GX_TEX},
           "scalars": {"Macro Tint": 0.10, "Macro Rough": 0.05, "Macro Dirt": 0.06, "Tile cm": 400.0,
                       "Saturation": 1.0, "ValueMult": 1.0}, "vectors": {"Tint": [1.0, 1.0, 1.0]}, "switches": {},
           "note": "the approach road: rounded granite cobbles with dark sandy joints (dojo1_reference1's grey stony road); "
                   "T_DKX_Cobble (ox_tex.py) on world XY / 4 m"},
    VERGE: {"master": "M_DJ_GroundXY_Master", "kit": "outside", "ue_dir": _MAT_DIR,
            "textures": {"Base Colour Map": "T_DKG_Soil_BC", "ORM Map": "T_DKG_Soil_ORM", "Normal Map": "T_DKG_Soil_N",
                         **_GX_TEX},
            "scalars": {"Macro Tint": 0.14, "Macro Rough": 0.05, "Macro Dirt": 0.05, "Tile cm": 400.0,
                        "Saturation": 0.85, "ValueMult": 0.80}, "vectors": {"Tint": [0.98, 1.0, 0.97]}, "switches": {},
            "note": "wall-foot verges and the outside ground: the ground kit's soil, darker (dojo1_reference1's dark "
                    "verge strip and outside ground, sRGB (46-61, 40-54, 26-54) at dusk); grass comes with the vegetation pass"},
    LANE: {"master": "M_DJ_GroundXY_Master", "kit": "outside", "ue_dir": _MAT_DIR,
           "textures": {"Base Colour Map": "T_DKG_Soil_BC", "ORM Map": "T_DKG_Soil_ORM", "Normal Map": "T_DKG_Soil_N",
                        **_GX_TEX},
           "scalars": {"Macro Tint": 0.10, "Macro Rough": 0.05, "Macro Dirt": 0.0, "Tile cm": 400.0,
                       "Saturation": 0.55, "ValueMult": 1.25}, "vectors": {"Tint": [1.0, 1.0, 1.04]}, "switches": {},
           "note": "packed-earth lanes (the side lanes and the lower lane): the ground kit's soil, desaturated and "
                   "lifted (the shed's packed-earth recipe values, as this track's own instance)"},
    WATER: {"master": "M_DJ_Flat_Master", "kit": "outside", "ue_dir": _MAT_DIR, "textures": {},
            "scalars": {"Roughness": 0.06, "Metallic": 0.0, "Specular": 0.5},
            "vectors": {"Base Colour": lin3((26, 30, 30))}, "switches": {},
            "note": "the canal under the terrace wall (dojo1_reference1: dark water): dark, glossy; Lumen reflects the sky"},
    MNEAR: {"master": "M_DJ_Flat_Master", "kit": "outside", "ue_dir": _MAT_DIR, "textures": {},
            "scalars": {"Roughness": 1.0, "Metallic": 0.0, "Specular": 0.2},
            "vectors": {"Base Colour": lin3((46, 52, 60))}, "switches": {},
            "note": "near ridge ring (0.9-1.3 km): a dark blue-grey forested ridge; the level's ExponentialHeightFog "
                    "(density 0.02, falloff 0.12) lays the haze on it, as dojo1_reference2's horizon"},
    MFAR: {"master": "M_DJ_Flat_Master", "kit": "outside", "ue_dir": _MAT_DIR, "textures": {},
           "scalars": {"Roughness": 1.0, "Metallic": 0.0, "Specular": 0.2},
           "vectors": {"Base Colour": lin3((70, 76, 90))}, "switches": {},
           "note": "far ridge ring (1.6-2.2 km, inside the 2.4 km cloud dome): paler blue-grey"},
    KAWARA: {"master": "M_DJ_Lib_Opaque", "kit": "outside", "ue_dir": _MAT_DIR,
             "textures": {"BC": "T_DKX_Kawara_BC", "ORM": "T_DKX_Kawara_ORM", "N": "T_DKX_Kawara_N",
                          "WearMask": "T_DJ_WearMask_M"},
             "scalars": {"RoughMult": 1.0, "NormalStrength": 1.0}, "vectors": {"Tint": [1.0, 1.0, 1.0],
                                                                              "TileM": [4.0, 4.0, 0.0, 0.0]},
             "switches": {"UseWear": False},
             "note": "the town roofs' tile field: the shared library's RoofTile maps with kawara courses every 0.2667 m "
                     "(ox_tex.kawara), on geometry rolls at the same pitch (UVs aligned by the builder); the ridges and "
                     "hip rolls keep M_DJ_RoofTile"},
    FARG: {"master": "M_DJ_Flat_Master", "kit": "outside", "ue_dir": _MAT_DIR, "textures": {},
           "scalars": {"Roughness": 1.0, "Metallic": 0.0, "Specular": 0.3},
           "vectors": {"Base Colour": lin3((50, 52, 42))}, "switches": {},
           "note": "the plain between the town and the ridges (stand-in until the vegetation pass): dark olive grey"},
}
# preview-only haze colours (Blender): (horizon colour sRGB, distance scale m)
HAZE = {MNEAR: ((104, 108, 128), 2600.0), MFAR: ((122, 124, 144), 2200.0), FARG: ((104, 108, 128), 3000.0)}
TEXTURES = {f"T_DKX_{s_}_{k}": {"png": str(TEX_OUT / f"T_DKX_{s_}_{k}.png"), "ue_dir": UE_ROOT + "/Textures",
                                 "kind": k} for s_ in ("Cobble", "Kawara") for k in ("BC", "N", "ORM")}
TEXTURES_REUSED = {"T_DKG_Soil_BC": "ground", "T_DKG_Soil_ORM": "ground", "T_DKG_Soil_N": "ground",
                   "T_DKG_Macro_M": "ground", "T_DJ_WearMask_M": "library"}


# ------------------------------------------------------------------------------------------------ Blender previews
def _img_node(nt, path, noncolor):
    n = nt.nodes.new("ShaderNodeTexImage")
    im = bpy.data.images.load(str(path), check_existing=True)
    if noncolor:
        im.colorspace_settings.name = "Non-Color"
    n.image = im
    return n


def _dx_normal(nt, nrm_node, strength=1.0):
    sn = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(nrm_node.outputs["Color"], sn.inputs["Color"])
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    nt.links.new(sn.outputs[1], inv.inputs[1])
    cb = nt.nodes.new("ShaderNodeCombineColor")
    nt.links.new(sn.outputs[0], cb.inputs[0])
    nt.links.new(inv.outputs[0], cb.inputs[1])
    nt.links.new(sn.outputs[2], cb.inputs[2])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.inputs["Strength"].default_value = strength
    nt.links.new(cb.outputs["Color"], nm.inputs["Color"])
    return nm


def ground_xy_material(name):
    """Blender preview of an M_DJ_GroundXY_Master instance: textures on UV0 (world XY / 4 m, baked), the macro map on
    UV0 / 8 (world XY / 32 m), BC x Tint x (1 + MacroTint (M.r - .5) 2), Saturation about luminance, x ValueMult."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    r = RECIPES[name]
    tx = r["textures"]

    def path(t):
        return (TEX_OUT if t.startswith("T_DKX_") else GROUND_TEX) / f"{t}.png"
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bc = _img_node(nt, path(tx["Base Colour Map"]), False)
    orm = _img_node(nt, path(tx["ORM Map"]), True)
    nrm = _img_node(nt, path(tx["Normal Map"]), True)
    uvn = nt.nodes.new("ShaderNodeUVMap")
    uvn.uv_map = "UVMap"
    for n in (bc, orm, nrm):
        nt.links.new(uvn.outputs["UV"], n.inputs["Vector"])
    mac = _img_node(nt, GROUND_TEX / "T_DKG_Macro_M.png", True)
    sc8 = nt.nodes.new("ShaderNodeVectorMath")
    sc8.operation = "SCALE"
    sc8.inputs["Scale"].default_value = 1.0 / 8.0
    nt.links.new(uvn.outputs["UV"], sc8.inputs[0])
    nt.links.new(sc8.outputs[0], mac.inputs["Vector"])
    msep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(mac.outputs["Color"], msep.inputs["Color"])
    k = nt.nodes.new("ShaderNodeMath")          # 1 + tint * (m.r - .5) * 2 = (1 - tint) + 2 tint m.r
    k.operation = "MULTIPLY_ADD"
    tint_k = r["scalars"]["Macro Tint"]
    k.inputs[1].default_value = 2.0 * tint_k
    k.inputs[2].default_value = 1.0 - tint_k
    nt.links.new(msep.outputs[0], k.inputs[0])
    tint = nt.nodes.new("ShaderNodeVectorMath")
    tint.operation = "MULTIPLY"
    tint.inputs[1].default_value = r["vectors"]["Tint"]
    nt.links.new(bc.outputs["Color"], tint.inputs[0])
    sk = nt.nodes.new("ShaderNodeVectorMath")
    sk.operation = "SCALE"
    nt.links.new(tint.outputs[0], sk.inputs[0])
    nt.links.new(k.outputs[0], sk.inputs["Scale"])
    hs = nt.nodes.new("ShaderNodeHueSaturation")
    hs.inputs["Saturation"].default_value = r["scalars"]["Saturation"]
    hs.inputs["Value"].default_value = r["scalars"]["ValueMult"]
    nt.links.new(sk.outputs[0], hs.inputs["Color"])
    nt.links.new(hs.outputs["Color"], bsdf.inputs["Base Color"])
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(orm.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
    nm = _dx_normal(nt, nrm)
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    mat["recipe"] = json.dumps(r)
    return mat


def flat_material(name):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    r = RECIPES[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    base = list(r["vectors"]["Base Colour"]) + [1.0]
    bsdf.inputs["Roughness"].default_value = r["scalars"]["Roughness"]
    bsdf.inputs["Metallic"].default_value = r["scalars"]["Metallic"]
    try:
        bsdf.inputs["Specular IOR Level"].default_value = r["scalars"]["Specular"]
    except KeyError:
        pass
    if name in HAZE:
        # preview-only aerial perspective: mix toward the horizon colour by 1 - exp(-d / scale), and let the far
        # silhouettes self-light a little (the fog's inscatter), as DojoLab's height fog does
        hz, scale = HAZE[name]
        cam = nt.nodes.new("ShaderNodeCameraData")
        dv = nt.nodes.new("ShaderNodeMath")
        dv.operation = "DIVIDE"
        dv.inputs[1].default_value = -scale
        nt.links.new(cam.outputs["View Distance"], dv.inputs[0])
        ex = nt.nodes.new("ShaderNodeMath")
        ex.operation = "EXPONENT"
        nt.links.new(dv.outputs[0], ex.inputs[0])
        one = nt.nodes.new("ShaderNodeMath")
        one.operation = "SUBTRACT"
        one.inputs[0].default_value = 1.0
        nt.links.new(ex.outputs[0], one.inputs[1])
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.inputs["A"].default_value = base
        mix.inputs["B"].default_value = lin3(hz) + [1.0]
        nt.links.new(one.outputs[0], mix.inputs["Factor"])
        nt.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
        em = nt.nodes.new("ShaderNodeVectorMath")
        em.operation = "SCALE"
        nt.links.new(mix.outputs["Result"], em.inputs[0])
        nt.links.new(one.outputs[0], em.inputs["Scale"])
        nt.links.new(em.outputs[0], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = 0.35
    else:
        bsdf.inputs["Base Color"].default_value = base
    mat["recipe"] = json.dumps(r)
    return mat


def kawara_material():
    """Blender preview of M_DKX_Kawara (M_DJ_Lib_Opaque, UV0 in tile units, no wear)."""
    if KAWARA in bpy.data.materials:
        return bpy.data.materials[KAWARA]
    mat = bpy.data.materials.new(KAWARA)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bc = _img_node(nt, TEX_OUT / "T_DKX_Kawara_BC.png", False)
    orm = _img_node(nt, TEX_OUT / "T_DKX_Kawara_ORM.png", True)
    nrm = _img_node(nt, TEX_OUT / "T_DKX_Kawara_N.png", True)
    uvn = nt.nodes.new("ShaderNodeUVMap")
    uvn.uv_map = "UVMap"
    for n in (bc, orm, nrm):
        nt.links.new(uvn.outputs["UV"], n.inputs["Vector"])
    nt.links.new(bc.outputs["Color"], bsdf.inputs["Base Color"])
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(orm.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
    nt.links.new(sep.outputs[2], bsdf.inputs["Metallic"])
    nm = _dx_normal(nt, nrm)
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    mat["recipe"] = json.dumps(RECIPES[KAWARA])
    return mat


def material(name):
    if name == KAWARA:
        return kawara_material()
    if name in djm.MATERIALS:
        return djm.make_material(name)
    if name in GROUND_XY:
        return ground_xy_material(name)
    if name in FLAT:
        return flat_material(name)
    raise KeyError(name)


# ------------------------------------------------------------------------------------------------ Geo -> mesh
def geo_to_object(piece, coll):
    """kit_mesh.geo_to_object + this track's materials (world XY / 4 m UV0 for the ground and flat sets) + the Geo's
    smooth flags + PlasterEarth box UVs. Returns (object, bad face count)."""
    g = piece.g
    P = Vector((0, 0, 0)) if piece.local else piece.pivot
    W = getattr(piece, "world_origin", None)     # the instance's world origin for world-XY UVs (None: the pivot)
    WO = Vector(W) if W is not None else piece.pivot
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    vs = [bm.verts.new(p - P) for p in g.v]
    mats, bad = [], 0
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
        face.smooth = bool(g.fsm[fi]) if fi < len(g.fsm) else False
        if m in GROUND_XY or m in FLAT:
            for loop in face.loops:
                co = loop.vert.co + (WO if piece.local else P)
                loop[uvl].uv = (co.x / 4.0, co.y / 4.0)
            continue
        if all(i in g.vuv for i in f):
            for loop, vi in zip(face.loops, f):
                loop[uvl].uv = g.vuv[vi]
            continue
        fr = g.fr[fi]
        face.normal_update()
        n = face.normal
        axes = list(fr) if fr is not None else [Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))]
        ni = max(range(3), key=lambda i: abs(n.dot(axes[i])))
        inplane = [i for i in range(3) if i != ni]
        U, Vv = axes[inplane[0]], axes[inplane[1]]
        for loop in face.loops:
            co = loop.vert.co + P
            loop[uvl].uv = (co.dot(U) / 4.0, co.dot(Vv) / 4.0)
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
    mesh = bpy.data.meshes.new(piece.name)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(material(m))
    extra_slots = {}
    for face_m, end_m in ((KM.TD, KM.TDE), (KM.TA, KM.TAE)):
        if face_m in mats:
            mesh.materials.append(djm.make_material(end_m))
            extra_slots[face_m] = len(mesh.materials) - 1
    obj = bpy.data.objects.new(piece.name, mesh)
    coll.objects.link(obj)
    by_mat = {}
    for poly in mesh.polygons:
        by_mat.setdefault(mats[poly.material_index], []).append(poly.index)
    for m, faces in by_mat.items():
        if m == KM.TD:
            djm.grain_uv(obj, "TimberDark", end_set="TimberDarkEnd", faces=faces, end_material_index=extra_slots[KM.TD])
        elif m == KM.TA:
            djm.grain_uv(obj, "TimberAged", end_set="TimberAgedEnd", faces=faces, end_material_index=extra_slots[KM.TA])
        elif m == KM.IR:
            djm.grain_uv(obj, "Iron", faces=faces, round_mode=False)
        elif m == KM.PL:
            djm.box_uv(obj, "PlasterCream", faces=faces, space="OBJECT")
        elif m == PLE:
            djm.box_uv(obj, "PlasterEarth", faces=faces, space="OBJECT")
        elif m == KM.GR:
            KM.stone_uv(obj, faces, "Granite")
        elif m == KM.GRR and not getattr(piece, "rubble_box", False):
            KM.stone_uv(obj, faces, "GraniteRubble")
        elif m == KM.GRR:
            djm.box_uv(obj, "GraniteRubble", faces=faces, space="OBJECT")
        elif m == KM.GL:
            djm.unit_uv(obj, faces=faces)
    for i, pts in enumerate(piece.hulls):
        hb = bmesh.new()
        hv = [hb.verts.new(Vector(p) - P) for p in pts]
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
    obj["nanite"] = piece.nanite
    obj["kit"] = "outside"
    return obj, bad


def tris_of(o):
    return sum(len(pl.vertices) - 2 for pl in o.data.polygons)


# ------------------------------------------------------------------------------------------------ QA + export
WAIVE = {"uv0_tile_range", "uv_no_overlap"}      # tiling UVs in tile units (every dojo kit's practice since kit 1)


def qa_and_export(P, objs, kit, export_dir, work_dir, quick=False, no_export=False, extra_waive=None):
    """UV1, pipeline qa_check (texel 5.12 px/cm +-25 %), then export through Scripts/pipeline: Nanite pieces and pieces
    under 400 tris as one LOD, the rest LOD0-2 (decimate 0.5 / 0.25, cleaned, clamped inside LOD0). Returns (qa, exp)."""
    sc = bpy.context.scene
    qa, exp = {}, {}
    if quick:
        return qa, exp
    for p in P:
        KM.add_uv1(objs[p.name])
    kit.hide_viewport = False
    for p in P:
        o = objs[p.name]
        r = qa_check([o], require_uv1=True, texel_density=5.12, tolerance=0.25,
                     overlap_method="operator" if tris_of(o) > 40000 else "sat")
        w = set(WAIVE) | set((extra_waive or {}).get(p.name, ()))
        fails = [c for c in r["checks"] if not c["passed"]]
        hard = [c for c in fails if c["name"] not in w]
        tex = next((c["detail"] for c in r["checks"] if c["name"] == "texel_density"), "")
        ucx = sum(1 for c in o.children if c.name.startswith("UCX_"))
        qa[p.name] = {"hard_fails": hard, "waived": sorted({c["name"] for c in fails if c["name"] in w}),
                      "tris": r["triangles"].get(p.name), "texel_qa": tex, "ucx": ucx}
        if ucx == 0:
            qa[p.name]["hard_fails"].append({"name": "ucx_present", "detail": "no UCX hull"})
        print("QA", p.name, len(qa[p.name]["hard_fails"]), sorted({c["name"] for c in fails}), flush=True)
        for c in qa[p.name]["hard_fails"]:
            print("  FAIL", p.name, c["name"], str(c["detail"])[:240], flush=True)
    hard_total = sum(len(v["hard_fails"]) for v in qa.values())
    (work_dir / "qa_report.json").write_text(json.dumps(qa, indent=1, default=str), encoding="utf-8")
    print(f"QA: {len(P)} pieces, hard fails {hard_total}", flush=True)
    if no_export or hard_total:
        kit.hide_viewport = True
        return qa, exp
    export_dir.mkdir(parents=True, exist_ok=True)
    for p in P:
        o = objs[p.name]
        tris = qa[p.name]["tris"]
        if p.nanite or tris < 400:
            r = export_fbx(str(export_dir / f"{p.name}.fbx"), [o], kind="static", sidecar=False)
            exp[p.name] = {"lods": 1, "lod_tris": [tris], "nanite": p.nanite, "warnings": r["warnings"]}
            continue
        tmpc = bpy.data.collections.new("TmpLOD")
        sc.collection.children.link(tmpc)
        c0 = o.copy()
        c0.data = o.data.copy()
        c0.name = f"{p.name}_LOD0"
        tmpc.objects.link(c0)
        for h in o.children:
            hc = h.copy()
            hc.data = h.data.copy()
            hc.name = h.name.replace(f"UCX_{p.name}_", f"UCX_{p.name}_LOD0_")
            tmpc.objects.link(hc)
            hc.parent = c0
        lods = decimate_lods(c0, (0.5, 0.25))
        for lo in lods:
            KM.fix_lod(lo, clamp_to=c0)
        grp = make_lod_group(p.name, [c0] + lods)
        lq = qa_check([c0] + lods, require_uv1=True, require_ucx=False)
        lod_hard = [c for c in lq["checks"] if not c["passed"] and c["name"] not in WAIVE | {"texel_density"}]
        r = export_fbx(str(export_dir / f"{p.name}.fbx"), [grp], kind="static", sidecar=True)
        exp[p.name] = {"lods": 3, "lod_tris": [lq["triangles"].get(x.name) for x in [c0] + lods],
                       "lod_qa_fails": [(c["name"], c["object"], str(c["detail"])[:120]) for c in lod_hard],
                       "screen_sizes": r.get("lod_screen_sizes"), "warnings": r["warnings"]}
        for ob in list(tmpc.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.collections.remove(tmpc)
    kit.hide_viewport = True
    (work_dir / "export_report.json").write_text(json.dumps(exp, indent=1, default=str), encoding="utf-8")
    print(f"exported {len(exp)} FBX to {export_dir}", flush=True)
    return qa, exp


# ------------------------------------------------------------------------------------------------ layout / checks
def place(piece, loc, rot, note=""):
    d = {"piece": piece, "loc": [round(v, 4) for v in loc], "rot_z": float(rot)}
    if note:
        d["note"] = note
    return d


def link_instances(inst, pieces, objs, asm, kit_name, tag):
    for n, it in enumerate(inst):
        p = pieces[it["piece"]]
        it.update({"folder": p.folder, "collision_class": p.cls, "kit": kit_name})
        o = bpy.data.objects.new(f"{it['piece']}__{tag}{n:04d}", objs[it["piece"]].data)
        o.matrix_world = Matrix.Translation(it["loc"]) @ Matrix.Rotation(math.radians(it["rot_z"]), 4, "Z")
        asm.objects.link(o)
        pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
        it["bbox_min_max"] = [round(min(q[i] for q in pts), 4) for i in range(3)] + \
                             [round(max(q[i] for q in pts), 4) for i in range(3)]
    return inst


def base_of(name):
    b = name.split("__")[0].split(".")[0]
    if b.startswith("UCX_"):
        b = b[4:].rsplit("_", 1)[0]
        if b.endswith("_LOD0"):
            b = b[:-5]
    return b


def compose_checks(kit, asm, replaced, LX, kit_name, prefix, out_path, stage, extra_walk=None, extra_climb=None,
                   moves=None, extra_instances=None, drop_instances=()):
    """Load the showcase compound (read-only) around the kit: its Kit pieces + UCX and its Assembly instances minus the
    replaced grey-box pieces (and any earlier copy of this kit); the modern kit's moved instances (moves: showcase
    instance index -> new transform) and extra modern instances (extra_instances, linked from the showcase's own kit
    meshes); write the checks layout (layout_showcase.json with the swap) to out_path."""
    if not SHOWCASE_BLEND.exists():
        print("no showcase blend; checks skipped")
        return None

    def dropped(name):
        b = base_of(name)
        if "__" in name and b in drop_instances:
            return True
        return b in replaced or b.startswith(prefix)

    with bpy.data.libraries.load(str(SHOWCASE_BLEND), link=False) as (src, dst):
        dst.objects = [n for n in src.objects if not dropped(n)]
    keep = 0
    for o in dst.objects:
        if o is None:
            continue
        if "__" in o.name:
            asm.objects.link(o)
            keep += 1
        elif o.type in ("MESH", "EMPTY"):
            kit.objects.link(o)
    L = json.loads(SHOWCASE_LAYOUT.read_text(encoding="utf-8"))
    L["pieces"] = {k: v for k, v in L["pieces"].items() if k not in replaced and not k.startswith(prefix)}
    for k, v in LX["pieces"].items():
        L["pieces"][k] = {"class": v["class"], "kit": kit_name, "nanite": v["nanite"], "ucx": v["ucx"]}
    # the modern kit's instances this track moves (the road): re-place the showcase's own objects and layout rows
    moved = 0
    by_label = {o.name: o for o in asm.objects}
    for idx, new in (moves or {}).items():
        row = L["instances"][idx]
        label = f"{row['piece']}__{idx:04d}"
        o = by_label.get(label)
        row["loc"] = list(new["loc"])
        row["rot_z"] = new["rot_z"]
        row["rot_xyz_deg"] = [0.0, 0.0, new["rot_z"]]
        if "scale" in new:
            row["scale"] = list(new["scale"])
        if o is not None:
            sc_ = new.get("scale", [1, 1, 1])
            o.matrix_world = (Matrix.Translation(new["loc"]) @ Matrix.Rotation(math.radians(new["rot_z"]), 4, "Z")
                              @ Matrix.Diagonal(Vector(list(sc_) + [1.0])))
            moved += 1
    extra_rows = []
    for n, e in enumerate(extra_instances or []):
        src = kit.objects.get(e["piece"]) or bpy.data.objects.get(e["piece"])
        if src is None:
            continue
        o = bpy.data.objects.new(f"{e['piece']}__x{n:04d}", src.data)
        sc_ = e.get("scale", [1, 1, 1])
        o.matrix_world = (Matrix.Translation(e["loc"]) @ Matrix.Rotation(math.radians(e["rot_z"]), 4, "Z")
                          @ Matrix.Diagonal(Vector(list(sc_) + [1.0])))
        asm.objects.link(o)
        extra_rows.append(e)
    L["instances"] = [i for i in L["instances"] if i["piece"] not in replaced and not i["piece"].startswith(prefix)] \
        + extra_rows + LX["instances"]
    L["stage"] = stage
    L[kit_name] = LX["numbers"]
    for k, (z, pts, leaves) in (extra_walk or {}).items():
        L["walk_routes"][k] = {"floor_z": z, "points": [list(q) for q in pts]}
        if leaves:
            L["walk_routes"][k]["leaves"] = "open"
    L["climb_routes"] = L["climb_routes"] + list(extra_climb or [])
    out_path.write_text(json.dumps(L, indent=1), encoding="utf-8")
    print("context: assembly instances kept", keep, "moved", moved, "extra", len(extra_rows), out_path.name, "written",
          flush=True)
    return L


def save_blend(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    print("saved", path, flush=True)


def new_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    kit = bpy.data.collections.new("Kit")
    sc.collection.children.link(kit)
    asm = bpy.data.collections.new("Assembly")
    sc.collection.children.link(asm)
    return sc, kit, asm


def timer():
    t0 = time.time()
    return lambda: round(time.time() - t0, 1)
