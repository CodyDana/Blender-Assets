"""Round 4 (2026-09-29): shared helpers for the TRAINING SHED (Scripts/dojo/shed/build_shed.py, SM_DKS_*) and the DRUM
PAVILION (Scripts/dojo/pavilion/build_pavilion.py, SM_DKV_*) builders. Same track, same owner (locks DojoShed and
DojoPavilion).

It reuses, read-only:
  - Scripts/dojo/roof/kit_mesh.py      the kit Piece container and primitives (cbox, member, cobox, stone_uv, add_uv1,
                                       fix_lod)
  - Scripts/dojo/materials             the shared dojo material library (M_DJ_*; never forked)
  - Scripts/dojo/props/modern/modern_lib.build_material
                                       the modern kit's galvanised steel and concrete (M_DKP_Modern_Galvanised /
                                       _Concrete, textures T_DKP_Modern_*): the library has no galvanised or concrete
                                       set, and these two are already imported into DojoLab
  - the ground kit's soil set          M_DKG_Soil (T_DKG_Soil_*, world XY / 4 m, as the ground kit maps it)
geo_to_object() is kit_mesh.geo_to_object plus those three non-library materials (their UV0: explicit per-vertex UVs
from the Geo when given, else box projection in metres / tile with world Z on V, as the modern kit maps them) and the
Geo's smooth-shading flags. qa_and_export() is the hall builder's QA + export loop (pipeline qa_check + export_fbx,
LOD0-2 for pieces under 2k tris, Nanite single LOD above). compose_checks() loads the showcase compound around a kit
the way the hall did, so walk_check / climb_check / roof_walk_check run unchanged on the kit's blend.
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
           ROOT / "Scripts" / "dojo" / "materials", ROOT / "Scripts" / "dojo" / "props" / "modern"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from pipeline.export_fbx import export_fbx  # noqa: E402
from pipeline.qa_check import qa_check  # noqa: E402
from pipeline.helpers import decimate_lods, make_lod_group  # noqa: E402
import dojo_materials as djm  # noqa: E402
import kit_mesh as KM  # noqa: E402
import modern_lib as ML  # noqa: E402

ML.TEX_DIR = ROOT / "Exports" / "DojoKit" / "Props" / "modern" / "Textures"
GROUND_TEX = ROOT / "Exports" / "DojoKit" / "Ground" / "Textures"
WORK = ROOT / "WorkFiles" / "dojo" / "build"
SPW = WORK / "shed_pavilion"
SHOWCASE_BLEND = ROOT / "Assets" / "Dojo" / "DojoShowcase.blend"
SHOWCASE_LAYOUT = WORK / "showcase" / "layout_showcase.json"

GALV = "M_DKP_Modern_Galvanised"
CONC = "M_DKP_Modern_Concrete"
SOIL = "M_DKG_Soil"
# two new INSTANCES (no new textures; the Unreal recipes are in layout_shed.json 'materials'): the sheet's weathered
# galvanised roof (the modern kit's galvanised set under the library opaque master: darker, duller, library wear) and
# the sheet's pale packed earth (the ground kit's soil set, desaturated and lifted)
GALVW = "M_DKS_GalvWeathered"
EARTH = "M_DKS_PackedEarth"
EXTRA = {GALV: 2.0, CONC: 2.0, SOIL: 4.0, GALVW: 2.0, EARTH: 4.0}      # tile metres
WORLD_XY = (SOIL, EARTH)
RECIPES = {
    GALVW: {"master": "M_DJ_Lib_Opaque", "kit": "shed", "ue_dir": "/Game/DojoKit/Shed/Materials",
            "textures": {"BC": "T_DKP_Modern_Galvanised_BC", "ORM": "T_DKP_Modern_Galvanised_ORM",
                         "N": "T_DKP_Modern_Galvanised_N", "WearMask": "T_DJ_WearMask_M"},
            "scalars": {"RoughMult": 1.5, "NormalStrength": 1.0}, "vectors": {"Tint": [0.60, 0.61, 0.65],
                                                                             "TileM": [2.0, 2.0, 0.0, 0.0]},
            "switches": {"UseWear": True},
            "note": "the shed sheet's weathered galvanised steel: the modern kit's galvanised set x a darker blue-grey "
                    "tint, duller (roughness x 1.5), library wear (grime / dirt from the 'Wear' vertex colours)"},
    EARTH: {"master": "M_DJ_GroundXY_Master", "kit": "shed", "ue_dir": "/Game/DojoKit/Shed/Materials",
            "textures": {"Base Colour Map": "T_DKG_Soil_BC", "ORM Map": "T_DKG_Soil_ORM", "Normal Map": "T_DKG_Soil_N",
                         "Macro Map": "T_DKG_Macro_M"},
            "scalars": {"Macro Tint": 0.10, "Macro Rough": 0.05, "Macro Dirt": 0.0, "Tile cm": 400.0,
                        "Saturation": 0.55, "ValueMult": 1.35}, "vectors": {"Tint": [1.0, 1.0, 1.04]},
            "switches": {},
            "note": "the shed sheet's pale packed earth: the ground kit's soil, desaturated and lifted towards the "
                    "sheet's floor (sRGB about 133 / 116 / 103)"},
}


# ------------------------------------------------------------------------------------------------ materials
def soil_material():
    """The ground kit's M_DKG_Soil for the Blender review renders: T_DKG_Soil BC / ORM / N (DirectX, green flipped
    back) on UV0 (world XY / 4 m: the ground kit's world-aligned mapping, baked into UV0)."""
    if SOIL in bpy.data.materials:
        return bpy.data.materials[SOIL]
    mat = bpy.data.materials.new(SOIL)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")

    def img(suffix, noncolor):
        n = nt.nodes.new("ShaderNodeTexImage")
        im = bpy.data.images.load(str(GROUND_TEX / f"T_DKG_Soil_{suffix}.png"), check_existing=True)
        if noncolor:
            im.colorspace_settings.name = "Non-Color"
        n.image = im
        return n
    bc, orm, nrm = img("BC", False), img("ORM", True), img("N", True)
    nt.links.new(bc.outputs["Color"], bsdf.inputs["Base Color"])
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(orm.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
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
    nt.links.new(cb.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    mat["family"] = "ground kit M_DKG_Soil (world-aligned XY / 4 m in Unreal)"
    return mat


def galv_weathered():
    """Blender preview of M_DKS_GalvWeathered (RECIPES): the modern galvanised material x tint, roughness x 1.5, and
    the 'Wear' grime (R) darkening as in the library wear maths."""
    if GALVW in bpy.data.materials:
        return bpy.data.materials[GALVW]
    src = ML.build_material(GALV)
    mat = src.copy()
    mat.name = GALVW
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    lk = bsdf.inputs["Base Color"].links[0]
    col = lk.from_socket
    nt.links.remove(lk)
    rc = RECIPES[GALVW]
    tint = nt.nodes.new("ShaderNodeVectorMath")
    tint.operation = "MULTIPLY"
    nt.links.new(col, tint.inputs[0])
    tint.inputs[1].default_value = rc["vectors"]["Tint"]
    att = nt.nodes.new("ShaderNodeAttribute")
    att.attribute_name = "Wear"
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(att.outputs["Color"], sep.inputs["Color"])
    grime = nt.nodes.new("ShaderNodeMath")
    grime.operation = "MULTIPLY_ADD"
    nt.links.new(sep.outputs[0], grime.inputs[0])
    grime.inputs[1].default_value = -0.40
    grime.inputs[2].default_value = 1.0
    sc_ = nt.nodes.new("ShaderNodeVectorMath")
    sc_.operation = "SCALE"
    nt.links.new(tint.outputs[0], sc_.inputs[0])
    nt.links.new(grime.outputs[0], sc_.inputs["Scale"])
    nt.links.new(sc_.outputs[0], bsdf.inputs["Base Color"])
    rl = bsdf.inputs["Roughness"].links
    if rl:
        r_src = rl[0].from_socket
        nt.links.remove(rl[0])
        m = nt.nodes.new("ShaderNodeMath")
        m.operation = "MULTIPLY"
        m.use_clamp = True
        nt.links.new(r_src, m.inputs[0])
        m.inputs[1].default_value = rc["scalars"]["RoughMult"]
        nt.links.new(m.outputs[0], bsdf.inputs["Roughness"])
    return mat


def packed_earth():
    """Blender preview of M_DKS_PackedEarth (RECIPES): the soil material, saturation 0.55, value x 1.35."""
    if EARTH in bpy.data.materials:
        return bpy.data.materials[EARTH]
    mat = soil_material().copy()
    mat.name = EARTH
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    lk = bsdf.inputs["Base Color"].links[0]
    col = lk.from_socket
    nt.links.remove(lk)
    hs = nt.nodes.new("ShaderNodeHueSaturation")
    hs.inputs["Saturation"].default_value = RECIPES[EARTH]["scalars"]["Saturation"]
    hs.inputs["Value"].default_value = RECIPES[EARTH]["scalars"]["ValueMult"]
    nt.links.new(col, hs.inputs["Color"])
    nt.links.new(hs.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


def material(name):
    if name in djm.MATERIALS:
        return djm.make_material(name)
    if name == SOIL:
        return soil_material()
    if name == GALVW:
        return galv_weathered()
    if name == EARTH:
        return packed_earth()
    if name in (GALV, CONC):
        return ML.build_material(name)
    raise KeyError(name)


# ------------------------------------------------------------------------------------------------ Geo -> mesh
def geo_to_object(piece, coll):
    """kit_mesh.geo_to_object + the non-library materials (EXTRA) + smooth flags. Returns (object, bad face count)."""
    g = piece.g
    P = Vector((0, 0, 0)) if piece.local else piece.pivot
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
        fr = g.fr[fi]
        face.normal_update()
        n = face.normal
        if m in EXTRA:
            tile = EXTRA[m]
            if all(i in g.vuv for i in f):
                for loop, vi in zip(face.loops, f):
                    loop[uvl].uv = g.vuv[vi]
                continue
            if m in WORLD_XY:
                for loop in face.loops:
                    co = loop.vert.co + P
                    loop[uvl].uv = (co.x / tile, co.y / tile)
                continue
            ax = max(range(3), key=lambda i: abs(n[i]))
            for loop in face.loops:
                co = loop.vert.co + P
                if ax == 2:
                    u, v = co.x, co.y * (1 if n.z > 0 else -1)
                elif ax == 0:
                    u, v = (co.y if n.x > 0 else -co.y), co.z
                else:
                    u, v = (-co.x if n.y > 0 else co.x), co.z
                loop[uvl].uv = (u / tile, v / tile)
            continue
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
        elif m == KM.GR:
            KM.stone_uv(obj, faces, "Granite")
        elif m == KM.GRR:
            KM.stone_uv(obj, faces, "GraniteRubble")
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
    obj["kit"] = getattr(piece, "kit", "")
    return obj, bad


def tris_of(o):
    return sum(len(pl.vertices) - 2 for pl in o.data.polygons)


# ------------------------------------------------------------------------------------------------ QA + export
WAIVE = {"uv0_tile_range", "uv_no_overlap"}      # tiling UVs in tile units (the kits' practice since kit 1)


def qa_and_export(P, objs, kit, export_dir, work_dir, quick=False, no_export=False, extra_waive=None):
    """UV1, pipeline qa_check (texel 5.12 px/cm +-25 %), then export: Nanite pieces and pieces under 400 tris as one
    LOD, the rest LOD0-2 (decimate 0.5 / 0.25, cleaned, clamped inside LOD0) with a socket sidecar. Returns (qa, exp)."""
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
        qa[p.name] = {"hard_fails": hard, "waived": sorted({c["name"] for c in fails if c["name"] in w}),
                      "tris": r["triangles"].get(p.name), "texel_qa": tex}
        print("QA", p.name, len(hard), sorted({c["name"] for c in fails}), flush=True)
        for c in hard:
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
def place(piece, loc, rot):
    return {"piece": piece, "loc": [round(v, 4) for v in loc], "rot_z": float(rot)}


def link_instances(inst, pieces, objs, asm, kit_name, tag):
    for n, it in enumerate(inst):
        p = pieces[it["piece"]]
        it.update({"folder": p.folder, "collision_class": p.cls, "kit": kit_name})
        o = bpy.data.objects.new(f"{it['piece']}__{tag}{n:03d}", objs[it["piece"]].data)
        o.matrix_world = Matrix.Translation(it["loc"]) @ Matrix.Rotation(math.radians(it["rot_z"]), 4, "Z")
        asm.objects.link(o)
        pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
        it["bbox_min_max"] = [round(min(q[i] for q in pts), 4) for i in range(3)] + \
                             [round(max(q[i] for q in pts), 4) for i in range(3)]
    return inst


def compose_checks(kit, asm, replaced, LX, kit_name, prefix, out_path, stage, extra_walk=None):
    """Load the showcase compound (read-only) around the kit: its Kit pieces + UCX and its Assembly instances minus the
    replaced grey-box pieces (and any earlier copy of this kit); write the checks layout (layout_showcase.json with the
    swap) to out_path."""
    if not SHOWCASE_BLEND.exists():
        print("no showcase blend; checks skipped")
        return

    def base_of(name):
        b = name.split("__")[0].split(".")[0]
        if b.startswith("UCX_"):
            b = b[4:].rsplit("_", 1)[0]
            if b.endswith("_LOD0"):
                b = b[:-5]
        return b

    def dropped(name):
        b = base_of(name)
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
    L["instances"] = [i for i in L["instances"] if i["piece"] not in replaced and not i["piece"].startswith(prefix)] \
        + LX["instances"]
    L["stage"] = stage
    L[kit_name] = LX["numbers"]
    for k, (z, pts) in (extra_walk or {}).items():      # round 4: this kit's own ground routes (walk_check.py reads them)
        L["walk_routes"][k] = {"floor_z": z, "points": [list(q) for q in pts]}
    out_path.write_text(json.dumps(L, indent=1), encoding="utf-8")
    print("context: assembly instances kept", keep, out_path.name, "written", flush=True)


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
