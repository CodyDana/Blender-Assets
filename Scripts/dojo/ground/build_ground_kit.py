"""Dojo kit 2: THE GROUND (WorkFiles/dojo/DOJO_QUEUE.md "Kit 2 breakdown", WorkFiles/world/DOJO_ARENA_SPEC.md).

Builds every ground piece at the origin (collection "Kit", UCX_ collision children, UV0 world-scale tiling, UV1
lightmap), assembles the compound's ground from one computed layout (collection "Assembly", linked copies), writes
WorkFiles/dojo/build/ground/layout_ground.json (the armory layout.json schema: pieces, instances, lights, materials,
cameras, tris, plus the ground zones), runs the pipeline QA, exports each piece through Scripts/pipeline to
Exports/DojoKit/Ground/SM_DKG_*.fbx and saves Assets/Dojo/DojoGround.blend.

Frame (spec section 1): metres, origin = inside south-west corner of the compound at courtyard level, X east (0-44),
Y north (0-36), Z up. Unreal: (x*100, -y*100, z*100), yaw = -rot_z.

Collision (spec 5.3 class "Ground, floors"): every walkable piece has UCX hulls at its visible walk surface
(f1: no more floating or sinking). Sand, gravel and the beds' flat part at Z 0; slabs +0.020; the edging boards +0.008
(visible top 6-10 mm); the gate kerb band +0.10 and the bed kerbs +0.05 (boxes); the sloped kerb End pieces are the
convex hull of the block; the bed mounds a flat box + the convex hull of the dome. Rake grooves, gravel and soil relief
live in the normal maps only. Grass, moss and pebble dressing has no collision (spec 5.3).

Run: blender -b --factory-startup --python Scripts/dojo/ground/build_ground_kit.py -- [--no-export]
"""
import json
import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Scripts"))
from pipeline.export_fbx import export_fbx  # noqa: E402
from pipeline.qa_check import qa_check  # noqa: E402
sys.path.insert(0, str(ROOT / "Scripts" / "dojo" / "materials"))
import dojo_materials as djm  # noqa: E402  (r2: the shared dojo material library)

TEX = ROOT / "Exports" / "DojoKit" / "Ground" / "Textures"
EXPORT_DIR = ROOT / "Exports" / "DojoKit" / "Ground"
WORK = ROOT / "WorkFiles" / "dojo" / "build" / "ground"
BLEND = ROOT / "Assets" / "Dojo" / "DojoGround.blend"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

TILE = 4.0            # every tiling set covers 4.0 m at 2048 px = 5.12 px/cm (STYLE_GUIDE 6)
MACRO_TILE = 32.0     # macro variation mask period (world XY)
RAKE_P = TILE / 42    # r3: mean 0.0952 m, irregular lines (make_ground_textures.py; r0-r2: 22 lines, 0.1818 m)

# --------------------------------------------------------------------------- materials
# coords: "uv0" samples the maps on UV0; "world_xy" samples them on world X/Y / tile (Unreal: WorldPosition.xy /
# 400 cm), so gravel and soil panels of any size and position join with no seam. Both: macro mask on world XY / 32 m.
MATERIALS = {
    # r3 (UE judge: moire at eye level): the rake normal fades with view distance in Unreal (M_DJ_Ground_Master:
    # N = lerp(N, (0, 0, 1), (1 - far_strength) * saturate((PixelDepth - start_cm) / (end_cm - start_cm)))); Blender
    # renders are unaffected (Cycles supersamples). 'normal_fade' is read by the Unreal step, see BUILD_NOTES r3
    "M_DKG_SandRaked": {"texture": "SandRaked", "tile": [4.0, 4.0], "coords": "uv0",
                        "macro": {"tint": 0.06, "rough": 0.04, "dirt": 0.04},
                        "normal_fade": {"start_cm": 1200.0, "end_cm": 3500.0, "far_strength": 0.35}},
    "M_DKG_SandEdge": {"texture": "SandEdge", "tile": [4.0, 0.5], "coords": "uv0",
                       "macro": {"tint": 0.06, "rough": 0.04, "dirt": 0.04},
                       "normal_fade": {"start_cm": 1200.0, "end_cm": 3500.0, "far_strength": 0.35}},
    # r2 (the kit 2 judge's top deltas + the kit-1 round 2 junction list): the path slabs AND the kerbs take the
    # SHARED LIBRARY granite (Scripts/dojo/materials: T_DJ_Granite_*, the M_DJ_Lib_Opaque recipe) through this
    # ground instance: a cooler grey-mauve tint (reference 2's slabs, 147/127/127) and a per-slab tone and hue
    # (Unreal: PerInstanceRandom), the library's 'Wear' weathering (bake_wear). The old ground sets (T_DKG_Granite,
    # T_DKG_GraniteHewn) are no longer used.
    # r3 (Unreal: the r2 tint (1.66, 1.92, 2.60) rendered the path pale lilac, (166, 162, 185)): the new library
    # granite v2 (median (115, 111, 106)) x a warm-grey tint -> albedo median about (137, 129, 118); the per-paver tone
    # is now in the 'Wear' R channel (each paver of a course mesh gets its own grime offset), so the per-ACTOR tone /
    # hue (one course = one actor, which would stripe the path by course) is off: instance_tint 0, hue_var neutral
    "M_DKG_Granite": {"library": "M_DJ_Granite", "tint_lin": [1.45, 1.38, 1.25], "instance_tint": 0.0,
                      "hue_var": {"warm": [1.0, 1.0, 1.0], "cool": [1.0, 1.0, 1.0]}, "tile": [4.0, 4.0],
                      "coords": "uv0"},
    "M_DKG_Gravel": {"texture": "Gravel", "tile": [4.0, 4.0], "coords": "world_xy",
                     "macro": {"tint": 0.10, "rough": 0.05, "dirt": 0.08}},
    # f1 (judge delta 4): the gate strip's darker, coarser pebble gravel
    "M_DKG_GravelCoarse": {"texture": "GravelCoarse", "tile": [4.0, 4.0], "coords": "world_xy",
                           "macro": {"tint": 0.08, "rough": 0.04, "dirt": 0.06}},
    "M_DKG_Soil": {"texture": "Soil", "tile": [4.0, 4.0], "coords": "world_xy",
                   "macro": {"tint": 0.10, "rough": 0.05, "dirt": 0.0}},
    "M_DKG_EdgeTimber": {"texture": "EdgeTimber", "tile": [4.0, 4.0], "coords": "uv0",
                         "macro": {"tint": 0.05, "rough": 0.03, "dirt": 0.0}},
    # f1 (judge delta 10): the soil beds are mounded islands whose soil feathers into the gravel: gravel and soil
    # (both world-aligned) lerped by the 'Blend' vertex colour (R = soil), height-blended by the gravel's
    # luminance so pebbles poke through the soil edge. Unreal: VertexColor.R, same world-aligned sampling.
    "M_DKG_BedBlend": {"blend": ["Gravel", "Soil"], "tile": [4.0, 4.0], "coords": "world_xy",
                       "macro": {"tint": 0.10, "rough": 0.05, "dirt": 0.05}, "blend_contrast": 0.35},
    # f1 (judge delta 9): grass / moss tufts and stray pebbles (spec 5.3 "grass, moss, gravel dressing": no
    # collision); base colour = the 'Col' vertex colour, no textures
    "M_DKG_Dressing": {"vertex_colour": "Col", "roughness": 0.78},
}


def tex_path(name, suffix):
    return TEX / f"T_DKG_{name}_{suffix}.png"


def build_library_instance(name, spec):
    """r2: a ground instance of a library material: the library material's nodes (djm.make_material), copied under the
    ground's slot name, its base colour multiplied by a linear tint and a per-instance tone / hue (Blender: Object
    Info Random; Unreal: PerInstanceRandom on M_DJ_Lib_Opaque's Tint)."""
    src = djm.make_material(spec["library"])
    mat = src.copy()
    mat.name = name
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    lk = bsdf.inputs["Base Color"].links[0]
    col = lk.from_socket
    nt.links.remove(lk)
    oi = nt.nodes.new("ShaderNodeObjectInfo")
    r2 = nt.nodes.new("ShaderNodeMath")
    r2.operation = "MULTIPLY"
    nt.links.new(oi.outputs["Random"], r2.inputs[0])
    r2.inputs[1].default_value = 17.31
    fr = nt.nodes.new("ShaderNodeMath")
    fr.operation = "FRACT"
    nt.links.new(r2.outputs[0], fr.inputs[0])
    hue = nt.nodes.new("ShaderNodeMix")
    hue.data_type = "RGBA"
    nt.links.new(fr.outputs[0], hue.inputs["Factor"])
    hue.inputs["A"].default_value = tuple(spec["hue_var"]["warm"]) + (1.0,)
    hue.inputs["B"].default_value = tuple(spec["hue_var"]["cool"]) + (1.0,)
    tone = nt.nodes.new("ShaderNodeMapRange")
    nt.links.new(oi.outputs["Random"], tone.inputs["Value"])
    tone.inputs["To Min"].default_value = 1.0 - spec["instance_tint"]
    tone.inputs["To Max"].default_value = 1.0 + spec["instance_tint"]
    m1 = nt.nodes.new("ShaderNodeVectorMath")
    m1.operation = "MULTIPLY"
    nt.links.new(col, m1.inputs[0])
    nt.links.new(hue.outputs["Result"], m1.inputs[1])
    m2 = nt.nodes.new("ShaderNodeVectorMath")
    m2.operation = "MULTIPLY"
    nt.links.new(m1.outputs[0], m2.inputs[0])
    m2.inputs[1].default_value = tuple(spec["tint_lin"])
    m3 = nt.nodes.new("ShaderNodeVectorMath")
    m3.operation = "SCALE"
    nt.links.new(m2.outputs[0], m3.inputs[0])
    nt.links.new(tone.outputs["Result"], m3.inputs["Scale"])
    nt.links.new(m3.outputs[0], bsdf.inputs["Base Color"])
    mat["dj_library"] = djm.VERSION
    mat["dj_set"] = src.get("dj_set")
    return mat


def build_material(name):
    spec = MATERIALS[name]
    if "library" in spec:
        return build_library_instance(name, spec)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    L = nt.links.new

    if "vertex_colour" in spec:   # dressing: vertex colour only
        vc = nt.nodes.new("ShaderNodeVertexColor")
        vc.layer_name = spec["vertex_colour"]
        L(vc.outputs["Color"], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = spec["roughness"]
        return mat

    def img(path, noncolor):
        n = nt.nodes.new("ShaderNodeTexImage")
        im = bpy.data.images.load(str(path), check_existing=True)
        if noncolor:
            im.colorspace_settings.name = "Non-Color"
        n.image = im
        n.interpolation = "Linear"
        return n

    def math_node(op, a, b=None):
        m = nt.nodes.new("ShaderNodeMath")
        m.operation = op
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                m.inputs[i].default_value = v
            else:
                L(v, m.inputs[i])
        return m.outputs[0]

    def mix(fac, a, b, dtype="RGBA"):
        m = nt.nodes.new("ShaderNodeMix")
        m.data_type = dtype
        L(fac, m.inputs["Factor"])
        for sock, v in (("A", a), ("B", b)):
            if isinstance(v, (tuple, list)):
                m.inputs[sock].default_value = tuple(v) + ((1.0,) if dtype == "RGBA" and len(v) == 3 else ())
            else:
                L(v, m.inputs[sock])
        return m.outputs["Result"]

    geo = nt.nodes.new("ShaderNodeNewGeometry")
    if spec["coords"] == "world_xy":
        vec = nt.nodes.new("ShaderNodeVectorMath")
        vec.operation = "MULTIPLY"
        L(geo.outputs["Position"], vec.inputs[0])
        vec.inputs[1].default_value = (1.0 / spec["tile"][0], 1.0 / spec["tile"][1], 0.0)
        coord = vec.outputs[0]
    else:
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "UV0"
        coord = uvn.outputs["UV"]

    def tex_set(tset):
        bc, orm, nrm = img(tex_path(tset, "BC"), False), img(tex_path(tset, "ORM"), True), img(tex_path(tset, "N"), True)
        for n in (bc, orm, nrm):
            L(coord, n.inputs["Vector"])
        return bc.outputs["Color"], orm.outputs["Color"], nrm.outputs["Color"]

    if "blend" in spec:   # two world-aligned sets lerped by the 'Blend' vertex colour, height-blended
        (bc_a, orm_a, n_a), (bc_b, orm_b, n_b) = tex_set(spec["blend"][0]), tex_set(spec["blend"][1])
        vc = nt.nodes.new("ShaderNodeVertexColor")
        vc.layer_name = "Blend"
        vs = nt.nodes.new("ShaderNodeSeparateColor")
        L(vc.outputs["Color"], vs.inputs["Color"])
        lum = nt.nodes.new("ShaderNodeRGBToBW")
        L(bc_a, lum.inputs["Color"])
        # fac = smoothstep(0.4, 0.6, Blend + k (0.5 - gravel luminance)): bright pebbles stay on top longest
        raw = math_node("ADD", vs.outputs[0], math_node("MULTIPLY", math_node("SUBTRACT", 0.5, lum.outputs[0]),
                                                         spec["blend_contrast"]))
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.interpolation_type = "SMOOTHSTEP"
        mr.inputs["From Min"].default_value = 0.40
        mr.inputs["From Max"].default_value = 0.60
        L(raw, mr.inputs["Value"])
        fac = mr.outputs["Result"]
        bc_out, orm_out, n_out = mix(fac, bc_a, bc_b), mix(fac, orm_a, orm_b), mix(fac, n_a, n_b)
    else:
        bc_out, orm_out, n_out = tex_set(spec["texture"])
    # macro variation on world XY / 32 m
    mv = nt.nodes.new("ShaderNodeVectorMath")
    mv.operation = "MULTIPLY"
    L(geo.outputs["Position"], mv.inputs[0])
    mv.inputs[1].default_value = (1.0 / MACRO_TILE, 1.0 / MACRO_TILE, 0.0)
    macro = img(TEX / "T_DKG_Macro_M.png", True)
    L(mv.outputs[0], macro.inputs["Vector"])
    msep = nt.nodes.new("ShaderNodeSeparateColor")
    L(macro.outputs["Color"], msep.inputs["Color"])
    mc = spec["macro"]
    # albedo gain = (1 + tint * (R - 0.5) * 2) * (1 - dirt * max(B - 0.5, 0) * 2)
    gain = math_node("ADD", math_node("MULTIPLY", math_node("SUBTRACT", msep.outputs[0], 0.5), 2 * mc["tint"]), 1.0)
    dirt = math_node("SUBTRACT", 1.0, math_node("MULTIPLY", math_node("MAXIMUM", math_node("SUBTRACT", msep.outputs[2], 0.5), 0.0), 2 * mc["dirt"]))
    gain = math_node("MULTIPLY", gain, dirt)
    wear_r = None
    if "wear_dark" in spec:   # granite: edge darkening from the "Wear" vertex colour (1 = clean face, 0 = edge)
        vc = nt.nodes.new("ShaderNodeVertexColor")
        vc.layer_name = "Wear"
        vsep = nt.nodes.new("ShaderNodeSeparateColor")
        L(vc.outputs["Color"], vsep.inputs["Color"])
        wear_r = vsep.outputs[0]
        wear = math_node("ADD", spec["wear_dark"], math_node("MULTIPLY", wear_r, 1.0 - spec["wear_dark"]))
        gain = math_node("MULTIPLY", gain, wear)
    oi = nt.nodes.new("ShaderNodeObjectInfo")
    if "instance_tint" in spec:   # per-instance tone: gain * (1 + k * (random - 0.5) * 2), Unreal PerInstanceRandom
        gain = math_node("MULTIPLY", gain, math_node("ADD", 1.0, math_node(
            "MULTIPLY", math_node("SUBTRACT", oi.outputs["Random"], 0.5), 2 * spec["instance_tint"])))
    col = bc_out
    if "hue_var" in spec:         # per-instance hue: lerp(warm, cool, frac(random * 17.31))
        r2 = math_node("FRACT", math_node("MULTIPLY", oi.outputs["Random"], 17.31))
        hue = mix(r2, spec["hue_var"]["warm"], spec["hue_var"]["cool"])
        hm = nt.nodes.new("ShaderNodeVectorMath")
        hm.operation = "MULTIPLY"
        L(col, hm.inputs[0])
        L(hue, hm.inputs[1])
        col = hm.outputs[0]
    mul = nt.nodes.new("ShaderNodeVectorMath")
    mul.operation = "SCALE"
    L(col, mul.inputs[0])
    L(gain, mul.inputs["Scale"])
    L(mul.outputs[0], bsdf.inputs["Base Color"])
    osep = nt.nodes.new("ShaderNodeSeparateColor")
    L(orm_out, osep.inputs["Color"])
    rough = math_node("ADD", osep.outputs[1], math_node("MULTIPLY", math_node("SUBTRACT", msep.outputs[1], 0.5), 2 * mc["rough"]))
    if "crown_gloss" in spec and wear_r is not None:
        rough = math_node("SUBTRACT", rough, math_node("MULTIPLY", wear_r, spec["crown_gloss"]))
    L(math_node("MINIMUM", math_node("MAXIMUM", rough, 0.02), 1.0), bsdf.inputs["Roughness"])
    L(osep.outputs[2], bsdf.inputs["Metallic"])
    # the N maps are DirectX (Unreal): flip green back to OpenGL for Blender
    nsep = nt.nodes.new("ShaderNodeSeparateColor")
    L(n_out, nsep.inputs["Color"])
    comb = nt.nodes.new("ShaderNodeCombineColor")
    L(nsep.outputs[0], comb.inputs[0])
    L(math_node("SUBTRACT", 1.0, nsep.outputs[1]), comb.inputs[1])
    L(nsep.outputs[2], comb.inputs[2])
    nmap = nt.nodes.new("ShaderNodeNormalMap")
    nmap.uv_map = "UV0"
    L(comb.outputs["Color"], nmap.inputs["Color"])
    L(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    # AO is left to the renderer in Blender (Unreal reads ORM.r as material AO)
    return mat


# --------------------------------------------------------------------------- geometry

class Piece:
    """One kit mesh: welded parts (bmesh), UV0 per loop, an optional loop colour layer ('Wear' on stone, 'Blend' on the
    beds, 'Col' on dressing), UCX hulls: boxes (colbox) or convex hulls of point sets (colhull)."""

    def __init__(self, name, family, wear=False, colour=None, collision=True):
        self.name, self.family = name, family
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UV0")
        layer = "Wear" if wear else colour
        self.col = self.bm.loops.layers.float_color.new(layer) if layer else None
        self.mats, self.ucx = [], []
        self.vmap = {}
        self.meta = {}
        self.collision = collision      # False: spec 5.3 "grass, moss, gravel dressing" (no collision)

    def part(self):
        self.vmap = {}      # a new weld scope: parts never share vertices
        return self

    def v(self, co):
        key = tuple(round(c, 6) for c in co)
        if key not in self.vmap:
            self.vmap[key] = self.bm.verts.new(co)
        return self.vmap[key]

    def face(self, cos, mat, uvs, wear=None):
        f = self.bm.faces.new([self.v(c) for c in cos])
        if mat not in self.mats:
            self.mats.append(mat)
        f.material_index = self.mats.index(mat)
        for i, loop in enumerate(f.loops):
            loop[self.uv].uv = uvs[i]
            if self.col is not None:
                w = 1.0 if wear is None else wear[i]
                loop[self.col] = tuple(w) if isinstance(w, (tuple, list)) else (w, w, w, 1.0)
        return f

    def colbox(self, x0, x1, y0, y1, z0, z1):
        self.ucx.append(("box", (x0, x1, y0, y1, z0, z1)))
        return self

    def colhull(self, pts):
        self.ucx.append(("hull", [tuple(p) for p in pts]))
        return self

    def build(self, coll):
        bm = self.bm
        if getattr(self, "recalc", False):
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bm.normal_update()
        mesh = bpy.data.meshes.new(self.name)
        bm.to_mesh(mesh)
        bm.free()
        for m in self.mats:
            mesh.materials.append(bpy.data.materials[m])
        obj = bpy.data.objects.new(self.name, mesh)
        coll.objects.link(obj)
        add_uv1(obj)
        for i, (kind, data) in enumerate(self.ucx):
            hull = bpy.data.meshes.new(f"UCX_{self.name}_{i:02d}")
            hb = bmesh.new()
            if kind == "box":
                x0, x1, y0, y1, z0, z1 = data
                bmesh.ops.create_cube(hb, size=1.0)
                for vert in hb.verts:
                    vert.co.x = x0 + (vert.co.x + 0.5) * (x1 - x0)
                    vert.co.y = y0 + (vert.co.y + 0.5) * (y1 - y0)
                    vert.co.z = z0 + (vert.co.z + 0.5) * (z1 - z0)
            else:
                vs = [hb.verts.new(p) for p in data]
                res = bmesh.ops.convex_hull(hb, input=vs)
                loose = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
                if loose:
                    bmesh.ops.delete(hb, geom=loose, context="VERTS")
                bmesh.ops.recalc_face_normals(hb, faces=hb.faces[:])
            hb.to_mesh(hull)
            hb.free()
            h = bpy.data.objects.new(f"UCX_{self.name}_{i:02d}", hull)
            coll.objects.link(h)
            h.parent = obj
            h.hide_render = True
            h.display_type = "WIRE"
        return obj


def add_uv1(obj):
    """UV1 lightmap channel (Fab rule): Blender's lightmap pack, which never overlaps and stays in 0-1."""
    me = obj.data
    me.uv_layers.new(name="UV1")
    me.uv_layers.active_index = 1
    with bpy.context.temp_override(active_object=obj, object=obj, selected_objects=[obj],
                                   selected_editable_objects=[obj]):
        bpy.ops.uv.lightmap_pack(PREF_CONTEXT="ALL_FACES", PREF_PACK_IN_ONE=False, PREF_NEW_UVLAYER=False,
                                 PREF_BOX_DIV=12, PREF_MARGIN_DIV=0.2)
    me.uv_layers.active_index = 0


def quad(p, x0, x1, y0, y1, z, mat, uvfn):
    cos = [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)]
    p.face(cos, mat, [uvfn(c[0], c[1]) for c in cos])


def stone_block(p, x0, x1, y0, y1, zb, zt, mat, ch=0.010, inset=0.05, cc=0.012, uvoff=(0.0, 0.0), zt_x1=None,
                wear_base=0.45):
    """A granite block. f1 (judge deltas 5 and 7): worn, rounded arrises: the plan corners are cut by cc and the top
    arris is a two-step round of radius ch; an inset top ring carries the 'Wear' vertex colour (dark arris, clean
    crown). zt_x1: top height at the +X end (a sloped end piece; the top stays planar, so the block is convex and the
    convex hull of its vertices is the block itself). Bottom face omitted (never seen). Returns the vertex list."""
    p.part()
    zt1 = zt if zt_x1 is None else zt_x1

    def ztop(x):
        return zt + (zt1 - zt) * (x - x0) / (x1 - x0)

    def octo(d):
        a0, a1, b0, b1, c = x0 + d, x1 - d, y0 + d, y1 - d, cc
        return [(a0 + c, b0), (a1 - c, b0), (a1, b0 + c), (a1, b1 - c), (a1 - c, b1), (a0 + c, b1), (a0, b1 - c),
                (a0, b0 + c)]

    # rings: (inset, depth below the top or None for the bottom, wear)
    spec = [(0.0, None, wear_base), (0.0, ch, 0.12), (0.30 * ch, 0.30 * ch, 0.0), (ch, 0.0, 0.3),
            (ch + inset, 0.0, 1.0)]
    rings = []
    for d, dz, w in spec:
        rings.append(([(x, y, zb if dz is None else ztop(x) - dz) for x, y in octo(d)], w))
    uo, vo = uvoff

    def uv_top(c):
        return (c[0] / TILE + uo, c[1] / TILE + vo)

    def uv_side(c, k):
        along = c[1] + vo if k in (2, 6) else c[0] + uo
        return (along / TILE, c[2] / TILE)

    for r in range(len(rings) - 1):
        (ra, wa), (rb, wb) = rings[r], rings[r + 1]
        for k in range(8):
            j = (k + 1) % 8
            q = [ra[k], ra[j], rb[j], rb[k]]
            uvs = [uv_side(c, k) for c in q] if r < 2 else [uv_top(c) for c in q]
            p.face(q, mat, uvs, [wa, wa, wb, wb])
    top = rings[-1][0]
    for idx in ((7, 0, 5, 6), (0, 1, 4, 5), (1, 2, 3, 4)):
        q = [top[i] for i in idx]
        p.face(q, mat, [uv_top(c) for c in q], [1.0] * 4)
    return [c for ring, _ in rings for c in ring]


def board(p, s0, s1, t0, t1, along_x, zb, ztops, mat, step=0.25):
    """f1 (judge delta 8, measurer): a timber edging board with a slightly irregular top. Stations every `step` along
    the board, each with its own top height ztops(s). along_x: the board runs along X (s = x, t = y), else along Y
    (s = y, t = x). Faces are wound outward in both cases (recalculated after build)."""
    p.part()
    n = max(1, int(round((s1 - s0) / step)))
    ss = [s0 + (s1 - s0) * i / n for i in range(n + 1)]

    def P(s, t, z):
        return (s, t, z) if along_x else (t, s, z)

    zs = [ztops(s) for s in ss]
    for i in range(n):
        a, b = ss[i], ss[i + 1]
        za, zb_ = zs[i], zs[i + 1]
        top = [P(a, t0, za), P(b, t0, zb_), P(b, t1, zb_), P(a, t1, za)]
        p.face(top, mat, [(s / TILE, t / TILE) for s, t in ((a, t0), (b, t0), (b, t1), (a, t1))])
        for t in (t0, t1):
            q = [P(a, t, zb), P(b, t, zb), P(b, t, zb_), P(a, t, za)]
            p.face(q, mat, [(a / TILE, zb / TILE), (b / TILE, zb / TILE), (b / TILE, zb_ / TILE), (a / TILE, za / TILE)])
    for s, z in ((ss[0], zs[0]), (ss[-1], zs[-1])):
        q = [P(s, t0, zb), P(s, t1, zb), P(s, t1, z), P(s, t0, z)]
        p.face(q, mat, [(t0 / TILE, zb / TILE), (t1 / TILE, zb / TILE), (t1 / TILE, z / TILE), (t0 / TILE, z / TILE)])


# --------------------------------------------------------------------------- zones (DOJO_ARENA_SPEC section 4)

FIELD_W = (8.0, 21.0, 2.0, 19.0)          # fight floor west half (the spec's 28 x 17 m at X 8-36, Y 2-19)
FIELD_E = (23.0, 36.0, 2.0, 19.0)
PATH = (21.0, 23.0, 0.5, 21.5)            # flush stone path X 21-23 (spec 4.2), gate kerb band to the hall steps
GATE_BAND = (18.0, 26.0, 0.0, 0.5)        # granite kerb band inside the gate (under the gatehouse roof X 18-26)
EDGE_W = 0.10                             # edging board width
STRIP = 0.50                              # sand edge strip width (the SandEdge texture's 0.5 m)
# f1 (judge delta 7): the gate band is a heavy threshold: 10 cm proud (the gate leaves' sill height in the grey-box,
# +0.0997), a 20 mm rounded arris, rough-hewn; the bed kerbs keep +0.05. A 10 cm step is far under the 0.45 m step-up.
KERB = {"Kerb25": {"w": 0.25, "zt": 0.05, "zb": -0.15, "ch": 0.012, "cc": 0.010},
        "Kerb50": {"w": 0.50, "zt": 0.10, "zb": -0.20, "ch": 0.020, "cc": 0.015}}
KERB_END_FREE = 0.012                     # the sloped end's arris height at its free end (the top there is + ch)
JOINT = 0.005                             # half of the 10 mm joint between kerb blocks (f1: 6 -> 10 mm, mortar below)
SLAB_JOINT = 0.004                        # half of the 8 mm joint between path slabs (f1 judge delta 5: 5-8 mm)
SLAB_CH = 0.012                           # r2 (judge: chamfer): the slabs' rounded arris 8 -> 12 mm
# r3 (the UE judge: 'two columns of big pale lilac slabs with one centre seam'): the path is rebuilt as warm-grey
# rectangular pavers 0.40-0.60 m long (across the path) in courses 0.42 m deep, running bond (every joint at least
# 0.12 m from the joints of the course before), 10 mm joints over the dark joint fill (+0.004), 10 mm rounded arris
PAVER_D = 0.42                            # course depth along the path (50 courses over the 21.0 m path)
PAVER_LENS = (0.40, 0.45, 0.50, 0.55, 0.60)
PAVER_JOINT = 0.005                       # half of the 10 mm joint
PAVER_CH = 0.010
PAVER_MIN_OFFSET = 0.12                   # running bond: joint-to-joint offset between consecutive courses
PAVER_VARIANTS = "ABCDEFGH"
# r3 f1 (both Unreal judges: 'the references use two staggered columns of large, near-square granite slabs'; the r3
# 4-5 small pavers per course in running bond is a design difference): the path is re-laid as TWO slabs across, each
# 1.0 m wide (the spec's 2.0 m path) and 0.6-0.9 m long, the two columns' joints staggered (every joint at least
# SLAB2_MIN_OFFSET from the other column's; about half a slab), straight outer edges. Path / field width 2 / 13 = 0.154
# equals reference 2's 0.155 (measured at the hall end of the path), so the path keeps its width.
SLAB2_W = 1.0
SLAB2_LENS = (0.6, 0.7, 0.8, 0.9)
SLAB2_VARIANTS = "ABC"
SLAB2_MIN_OFFSET = 0.25
SLAB2_TONE = 0.40                         # per-slab 'Wear' R offset 0..0.40 (0-16 % darker), one per piece variant
PAVER_TONE = 0.40                         # per-paver 'Wear' R offset 0..0.40 (x 0.40 in the wear maths: 0-16 % darker)
JF = "M_DJ_GraniteRubble"                 # r2: the dark joint fill under the slab and kerb joints (the library rubble)
SLAB_TOP = 0.020                          # f1 (judge delta 6): slabs 2 cm proud of the sand and gravel (r0: 12 mm)
BOARD_TOP = (0.006, 0.010)                # f1 (measurer): edging board top 6-10 mm proud, irregular (r0: 25 mm)
BOARD_HULL_TOP = 0.008                    # its hull top: within 2 mm of the visible top everywhere
GATE_STRIP = (7.75, 36.25, 0.0, 2.0)      # f1 (judge delta 4): the coarse pebble strip between the gate and the sand

# no gravel under these (building floors / plinths sit there; the kit-1/3/5/6 pieces cover them)
EXCLUDE = {
    "hall_and_veranda": (11.0, 33.0, 22.0, 34.0),            # spec 4.4 (X 11-33, Y 22-34); step band sits on gravel
    "corridor_W": (7.5, 10.5, 29.5, 32.5), "corridor_E": (33.5, 36.5, 29.5, 32.5),   # spec 4.5, floor +0.5
    "storehouse": (0.0, 7.5, 27.5, 36.0), "residence": (36.5, 44.0, 27.5, 36.0),      # spec 4.5 (edges 7.6 / 27.4 / 36.4: 0.1 m under the walls)
    "drum_plinth": (39.0, 43.0, 1.0, 5.0),                   # spec 4.5, plinth +1.0
}
# f1 (judge delta 10): soil beds are mounded planting islands with organic outlines that feather into the gravel
# (reference 2), not kerbed rectangular trays. Each bed is one mesh over its grid-aligned rect (gravel stops at the
# rect; at the rect edge the bed material is 100 % the same world-aligned gravel, so the join is invisible).
# name: (rect, outline centre, semi-axes, superellipse exponent, peak height, wall sides). East = mirror of west.
BEDS_W = {
    "Tree_W": ((1.25, 5.75, 13.75, 18.25), (3.5, 16.0), (1.85, 1.85), 2.0, 0.08, ""),   # round the tree (3.5, 16)
    "WallFoot8_W": ((0.0, 1.25, 5.5, 13.5), (0.0, 9.5), (1.05, 3.4), 2.6, 0.05, "W"),  # shed to the side wicket
    "WallFoot12_W": ((0.0, 1.25, 15.5, 27.5), (0.0, 21.5), (1.05, 5.1), 2.6, 0.05, "W"),  # wicket to storehouse
    # reference 2's near-left bed between the shed (X 0-6) and the sand; Y 0-2.5 keeps the grey-box climb crate at
    # (36.35-37.35, 2.5-3.5) off the mirrored east bed
    "Gate_W": ((6.0, 7.75, 0.0, 2.5), (6.875, 0.0), (0.75, 2.1), 2.4, 0.05, "S"),
}


def mirror_rect(r):
    x0, x1, y0, y1 = r
    return (44.0 - x1, 44.0 - x0, y0, y1)


BEDS = dict(BEDS_W)
for k, (r, c, ax, e, hgt, walls) in BEDS_W.items():
    BEDS[k.replace("_W", "_E")] = (mirror_rect(r), (44.0 - c[0], c[1]), ax, e, hgt,
                                   walls.replace("W", "E"))

GRID = 0.25


def fmt(v):
    return (f"{v:g}").replace(".", "p")


def region_grid(include, exclude):
    nx, ny = int(round(44 / GRID)), int(round(36 / GRID))
    g = [[False] * nx for _ in range(ny)]

    def cells(r):
        x0, x1, y0, y1 = (int(round(c / GRID)) for c in r)
        assert all(abs(c / GRID - round(c / GRID)) < 1e-9 for c in r), r
        return x0, x1, y0, y1

    for r in include:
        x0, x1, y0, y1 = cells(r)
        for j in range(y0, y1):
            for i in range(x0, x1):
                g[j][i] = True
    for r in exclude:
        x0, x1, y0, y1 = cells(r)
        for j in range(max(0, y0), min(ny, y1)):
            for i in range(max(0, x0), min(nx, x1)):
                g[j][i] = False
    return g


PANEL_SIZES = [4.0, 2.0, 1.0, 0.5, 0.25]


def greedy_tiles(g):
    """Cover the True cells with axis-aligned panels from PANEL_SIZES x PANEL_SIZES (largest area first, squarer first).
    Returns (x0, y0, w, d) in metres. No rotation (the world-aligned normal maps stay aligned)."""
    ny, nx = len(g), len(g[0])
    sizes = sorted({(w, d) for w in PANEL_SIZES for d in PANEL_SIZES},
                   key=lambda s: (-s[0] * s[1], abs(math.log(s[0] / s[1]))))
    out = []
    for j in range(ny):
        for i in range(nx):
            if not g[j][i]:
                continue
            for w, d in sizes:
                wn, dn = int(round(w / GRID)), int(round(d / GRID))
                if i + wn > nx or j + dn > ny:
                    continue
                if all(g[jj][ii] for jj in range(j, j + dn) for ii in range(i, i + wn)):
                    for jj in range(j, j + dn):
                        for ii in range(i, i + wn):
                            g[jj][ii] = False
                    out.append((i * GRID, j * GRID, w, d))
                    break
    return out


def fill_run(length, sizes=(2.0, 1.0, 0.5, 0.25)):
    out, rest = [], round(length, 6)
    for s in sizes:
        while rest >= s - 1e-9:
            out.append(s)
            rest = round(rest - s, 6)
    assert rest < 1e-6, (length, rest)
    return out


def slab_sequences(total=21.0, seed=7):
    """Two columns of slab lengths (0.6-1.2 m) summing to the path length, with every joint of one column at least
    0.2 m from every joint of the other (staggered, as reference 2)."""
    rng = random.Random(seed)
    lens = [0.6, 0.8, 1.0, 1.2]
    for _ in range(20000):
        cols = []
        for c in range(2):
            seq, s = [], 0.0
            if c == 1:
                first = rng.choice([0.6, 1.2])
                seq, s = [first], first
            while total - s > 1.2 + 1e-9:
                x = rng.choice(lens)
                seq.append(x)
                s = round(s + x, 6)
            rest = round(total - s, 6)
            if rest not in lens:
                break
            seq.append(rest)
            cols.append(seq)
        if len(cols) < 2:
            continue
        j = [[round(sum(c[:k]), 6) for k in range(1, len(c))] for c in cols]
        if all(abs(a - b) >= 0.2 - 1e-9 for a in j[0] for b in j[1]):
            return cols
    raise RuntimeError("no staggered slab sequence found")


# --------------------------------------------------------------------------- the kit

S, SE, GR, GH, GV, GC, SO, TB, BB, DR = ("M_DKG_SandRaked", "M_DKG_SandEdge", "M_DKG_Granite", "M_DKG_Granite",
                                         "M_DKG_Gravel", "M_DKG_GravelCoarse", "M_DKG_Soil", "M_DKG_EdgeTimber",
                                         "M_DKG_BedBlend", "M_DKG_Dressing")
SLAB_LENGTHS = [0.6, 0.8, 1.0, 1.2]
SLAB_UVOFF = {"A": (0.0, 0.0), "B": (0.37, 0.61)}
KERB50_RUN = [1.5, 2.0, 1.0, 1.5, 1.0]    # f1 (judge delta 7): varied block lengths across the 7 m between the ends
PATH_BERM = ([0.0, 0.42, 0.46, 0.485, 0.5], [0.0, 0.0, 0.004, 0.008, 0.010])     # f1 (judge delta 6), from x_in1
BOARD_BERM = ([0.0, 0.015, 0.04, 0.08, 0.5], [0.007, 0.006, 0.003, 0.0, 0.0])    # from the board face


def lin_hex(h):
    c = [int(h[i:i + 2], 16) / 255.0 for i in (1, 3, 5)]
    return tuple(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c)


def sand_field_piece():
    """One fight-floor half, 13 x 17 m (local origin = the field's SW corner). Rake lines run along local X (east-west,
    as reference 2). Main raked panel X 0.6-12.5, edge strips 0.5 m wide on both X sides (the ridges run into the
    board at X 0.1 and the path at X 13 and end in round caps). Y 0.1-16.9 inside the boards.
    UV: v = (y - 8.5) / 4, so a crest sits on the field's centre line and the E half (this piece turned 180 deg) has
    the same phase; f1: u = (x - 12.5) / 4, so the raked tile's line wobble (0 at u = 0 mod 1) is 0 where the ridges
    meet the path strip (and 1.5 mm at the board strip, u = -2.975). The strips carry U = +-(y - 8.5) / 4, V 0 at the
    field, 1 at the edge. f1 (judge delta 6): each strip's last few cm rise into a berm, +10 mm against the path slabs
    and +7 mm against the board, the sand heaped against the edge (visual only; the hull stays flat at 0)."""
    p = Piece("SM_DKG_SandField_13x17", "sand")
    yc = 8.5
    x_in0, x_in1 = EDGE_W + STRIP, 13.0 - STRIP
    y0, y1 = EDGE_W, 17.0 - EDGE_W
    quad(p, x_in0, x_in1, y0, y1, 0.0, S, lambda x, y: ((x - x_in1) / TILE, (y - yc) / TILE))
    ds, zs = PATH_BERM
    for i in range(len(ds) - 1):   # path side, x_in1 -> 13.0
        xa, xb, za, zb = x_in1 + ds[i], x_in1 + ds[i + 1], zs[i], zs[i + 1]
        cos = [(xa, y0, za), (xb, y0, zb), (xb, y1, zb), (xa, y1, za)]
        p.face(cos, SE, [(-(c[1] - yc) / TILE, (c[0] - x_in1) / STRIP) for c in cos])
    ds, zs = BOARD_BERM
    for i in range(len(ds) - 1):   # board side, EDGE_W -> x_in0
        xa, xb, za, zb = EDGE_W + ds[i], EDGE_W + ds[i + 1], zs[i], zs[i + 1]
        cos = [(xa, y0, za), (xb, y0, zb), (xb, y1, zb), (xa, y1, za)]
        p.face(cos, SE, [((c[1] - yc) / TILE, (x_in0 - c[0]) / STRIP) for c in cos])
    p.colbox(0.0, 13.0, 0.0, 17.0, -0.20, 0.0)
    p.meta = {"size_m": [13.0, 17.0], "raked_m": [round(x_in1 - x_in0, 3), round(y1 - y0, 3)],
              "rake_lines_across_field": round((y1 - y0) / RAKE_P, 1),
              "berm_top_m": {"path_side": PATH_BERM[1][-1], "board_side": BOARD_BERM[1][0]}}
    return p


def board_heights(name):
    rng = random.Random(name)
    cache = {}

    def f(s):
        k = round(s, 4)
        if k not in cache:
            cache[k] = round(rng.uniform(*BOARD_TOP), 4)
        return cache[k]
    return f


def edging_pieces():
    """f1: bleached timber boards, 0.10 m wide, the top 6-10 mm proud and irregular (every 0.25 m), hull top +0.008
    (measurer: r0's +0.025 top over a flat hull at 0 sank feet 2.5 cm)."""
    out = []
    zb = -0.10
    for L in (2.0, 1.0):
        name = f"SM_DKG_SandEdging_Straight_{fmt(L)}"
        p = Piece(name, "edging")
        p.recalc = True
        board(p, 0.0, L, 0.0, EDGE_W, True, zb, board_heights(name), TB)
        p.colbox(0.0, L, 0.0, EDGE_W, -0.20, BOARD_HULL_TOP)
        out.append(p)
    name = "SM_DKG_SandEdging_Corner"   # an L with 1 m legs along local +X and +Y
    p = Piece(name, "edging")
    p.recalc = True
    w = EDGE_W
    f = board_heights(name)
    board(p, 0.0, 1.0, 0.0, w, True, zb, f, TB)
    board(p, w + 0.001, 1.0, 0.0, w, False, zb, lambda s: f(s + 7.0), TB)   # 1 mm off leg X (no shared verts)
    p.colbox(0.0, 1.0, 0.0, w, -0.20, BOARD_HULL_TOP)
    p.colbox(0.0, w, w, 1.0, -0.20, BOARD_HULL_TOP)
    out.append(p)
    for q in out:
        q.meta = {"top_m": list(BOARD_TOP), "hull_top_m": BOARD_HULL_TOP}
    return out


# r3: the eight course patterns (metres, west to east). Interior pavers 0.40-0.60 m; the edge pavers may be cut
# (0.20-0.60 m, as real running bond cuts its courses at the path edges). Chosen by a random search over all 515
# such compositions of 2.0 m (3-5 pavers, 5 cm steps) for the set whose (pattern, flipped) courses have the most
# running-bond neighbours (every one has at least 5 of the 16): a strict 4-paver 0.40-0.60 set only alternates two
# patterns (the first r3 build repeated one pattern every other course).
PAVER_PATTERNS = {"A": [0.5, 0.45, 0.5, 0.55], "B": [0.35, 0.45, 0.5, 0.4, 0.3], "C": [0.5, 0.5, 0.4, 0.6],
                  "D": [0.35, 0.4, 0.55, 0.5, 0.2], "E": [0.2, 0.6, 0.5, 0.4, 0.3], "F": [0.2, 0.55, 0.55, 0.4, 0.3],
                  "G": [0.2, 0.5, 0.55, 0.45, 0.3], "H": [0.5, 0.55, 0.45, 0.5]}
assert all(abs(sum(v) - 2.0) < 1e-9 for v in PAVER_PATTERNS.values())


def paver_joints(var, flip):
    js = [round(sum(PAVER_PATTERNS[var][:k]), 4) for k in range(1, len(PAVER_PATTERNS[var]))]
    return sorted(round(2.0 - j, 4) for j in js) if flip else js


def paver_sequence(n=50, seed=12):
    """r3: n courses of (variant, flipped) in running bond: every interior joint of a course at least
    PAVER_MIN_OFFSET from every interior joint of the course before, and no variant within the last three courses
    (random walk with restarts)."""
    rng = random.Random(seed)
    for _ in range(5000):
        seq = []
        for _k in range(n):
            recent = {v for v, _f in seq[-3:]}
            prev = seq[-1] if seq else None
            opts = [(v, f) for v in PAVER_VARIANTS for f in (False, True) if v not in recent and
                    (prev is None or all(abs(a - b) >= PAVER_MIN_OFFSET - 1e-9
                                         for a in paver_joints(v, f) for b in paver_joints(*prev)))]
            if not opts:
                break
            seq.append(rng.choice(opts))
        if len(seq) == n:
            return seq
    raise RuntimeError("no running-bond paver sequence found")


def slab2_name(L, var):
    return f"SM_DKG_Slab_100x{int(round(L * 100))}_{var}"


def slab2_columns(total=21.0, seed=21):
    """r3 f1: two columns of slab lengths from SLAB2_LENS summing to the path length; every interior joint of the east
    column at least SLAB2_MIN_OFFSET from every interior joint of the west one (depth-first search for the east column
    over a random west column); the east column starts with a short slab, so the stagger is about half a slab."""
    rng = random.Random(seed)
    lens = sorted(SLAB2_LENS)

    def dfs(acc, seq, wj):
        if abs(acc - total) < 1e-9:
            return seq
        opts = list(lens)
        rng.shuffle(opts)
        for L in opts:
            y = round(acc + L, 6)
            if y > total + 1e-9:
                continue
            if abs(y - total) > 1e-9 and any(abs(y - j) < SLAB2_MIN_OFFSET - 1e-9 for j in wj):
                continue
            r = dfs(y, seq + [L], wj)
            if r:
                return r
        return None

    import sys as _sys
    _sys.setrecursionlimit(10000)
    for _ in range(2000):
        w, acc = [], 0.0
        while total - acc > max(lens) + 1e-9:
            x = rng.choice(lens)
            w.append(x)
            acc = round(acc + x, 6)
        rest = round(total - acc, 6)
        if not any(abs(rest - L) < 1e-9 for L in lens):
            continue
        w.append(rest)
        wj = [round(sum(w[:k]), 6) for k in range(1, len(w))]
        if 0.6 in [round(abs(j - 0.6), 6) for j in wj] or any(abs(0.6 - j) < SLAB2_MIN_OFFSET for j in wj):
            continue
        e = dfs(0.6, [0.6], wj)
        if e:
            return [w, e]
    raise RuntimeError("no staggered two-column slab layout found")


def slab_pieces():
    """r3 f1: the path slabs SM_DKG_Slab_100x<60-90>_<A-C>: one granite slab each (1.0 m across the path, 8 mm joints,
    12 mm rounded arris, its own UV offset); variant = UV offset + per-slab tone (slab_tone). One flat UCX at the slab
    top (+0.020). The dark joint fill under the joints is the path bed (unchanged)."""
    out = []
    for L in SLAB2_LENS:
        for var in SLAB2_VARIANTS:
            p = Piece(slab2_name(L, var), "slab", wear=True)
            rng = random.Random("slab2" + slab2_name(L, var))
            stone_block(p, SLAB_JOINT, SLAB2_W - SLAB_JOINT, SLAB_JOINT, L - SLAB_JOINT, -0.05, SLAB_TOP, GR,
                        ch=SLAB_CH, inset=0.05, cc=0.012, uvoff=(rng.uniform(0, 1), rng.uniform(0, 1)))
            p.colbox(0.0, SLAB2_W, 0.0, L, -0.10, SLAB_TOP)
            p.meta = {"size_m": [SLAB2_W, L], "top_z": SLAB_TOP, "joint_m": 2 * SLAB_JOINT, "arris_round_m": SLAB_CH,
                      "variant": var, "per_slab_tone": f"Wear R + U(0, {SLAB2_TONE})"}
            out.append(p)
    p = Piece("SM_DKG_PathBed_2x3", "path_bed")   # the joint fill under the slabs (r2: dark, the library rubble)
    quad(p, 0.0, 2.0, 0.0, 3.0, 0.004, JF, lambda x, y: (x / TILE, y / TILE))
    p.colbox(0.0, 2.0, 0.0, 3.0, -0.12, 0.004)
    out.append(p)
    return out


def slab_tone(obj):
    """r3 f1: after bake_wear, one random grime offset on the 'Wear' R channel for the whole slab (variants differ
    slab by slab); the bleached arris (G) is cleared, as on the r3 pavers (pale joints at the low sun)."""
    me = obj.data
    ca = me.color_attributes["Wear"]
    t = random.Random(obj.name).uniform(0.0, SLAB2_TONE)
    for c_ in ca.data:
        c = list(c_.color)
        c[0] = min(1.0, c[0] + t)
        c[1] = 0.0
        c_.color = c
    me.update()
    return round(t, 3)


def paver_course_pieces_r3():
    """(r3, retired by f1) the path's paver courses (SM_DKG_PaverCourse_2x0p42_<A-H>): four pavers each, every paver a granite
    block with a 10 mm rounded arris and its own UV offset; one flat UCX at the paver top (+0.020). The dark joint
    fill under the joints is the path bed (unchanged)."""
    out = []
    for var, lens in PAVER_PATTERNS.items():
        p = Piece(f"SM_DKG_PaverCourse_2x0p42_{var}", "paver", wear=True)
        rng = random.Random("paver" + var)
        x = 0.0
        assert len(lens) <= 5
        for L in lens:
            stone_block(p, x + PAVER_JOINT, x + L - PAVER_JOINT, PAVER_JOINT, PAVER_D - PAVER_JOINT, -0.05, SLAB_TOP,
                        GR, ch=PAVER_CH, inset=0.04, cc=0.010, uvoff=(rng.uniform(0, 1), rng.uniform(0, 1)))
            x = round(x + L, 6)
        p.colbox(0.0, 2.0, 0.0, PAVER_D, -0.10, SLAB_TOP)
        p.meta = {"size_m": [2.0, PAVER_D], "pavers_m": lens, "top_z": SLAB_TOP, "joint_m": 2 * PAVER_JOINT,
                  "arris_round_m": PAVER_CH, "per_paver_tone": f"Wear R + U(0, {PAVER_TONE})"}
        out.append(p)
    p = Piece("SM_DKG_PathBed_2x3", "path_bed")   # the joint fill under the pavers (r2: dark, the library rubble)
    quad(p, 0.0, 2.0, 0.0, 3.0, 0.004, JF, lambda x, y: (x / TILE, y / TILE))
    p.colbox(0.0, 2.0, 0.0, 3.0, -0.12, 0.004)
    out.append(p)
    return out


def paver_tone(obj):
    """r3: after bake_wear: each paver (its own x range in the course) gets a random offset on the 'Wear' R (grime)
    channel, so pavers differ one by one in Blender (DJ_Wear_v1) and in Unreal (M_DJ_Lib_Opaque wear maths); the edge
    wear G is cleared (test render t1: bleached arrises read the joints as pale lines and flashed at the low sun)."""
    me = obj.data
    ca = me.color_attributes["Wear"]
    rng = random.Random(obj.name)
    lens = PAVER_PATTERNS[obj.name.rsplit("_", 1)[1]]
    edges = [0.0]
    for L in lens:
        edges.append(edges[-1] + L)
    tones = [rng.uniform(0.0, PAVER_TONE) for _ in lens]
    for poly in me.polygons:
        cx = poly.center.x
        k = max(0, min(len(lens) - 1, next((i for i in range(len(lens)) if cx < edges[i + 1]), len(lens) - 1)))
        for li in poly.loop_indices:
            c = list(ca.data[li].color)
            c[0] = min(1.0, c[0] + tones[k])
            c[1] = 0.0   # no bleached arris on the pavers: the test render's pale bevels read the joints LIGHT
            ca.data[li].color = c
    me.update()
    return [round(t, 3) for t in tones]


def kerb_pieces():
    out = []
    for fam, k in KERB.items():
        w, zt, zb, ch, cc = k["w"], k["zt"], k["zb"], k["ch"], k["cc"]
        ins = min(0.05, w / 2 - ch - cc - 0.02)
        straights = (2.0, 1.0, 0.5, 0.25) if fam == "Kerb25" else (2.0, 1.5, 1.0)
        for L in straights:
            p = Piece(f"SM_DKG_{fam}_Straight_{fmt(L)}", "kerb", wear=True)
            stone_block(p, JOINT, L - JOINT, 0.0, w, zb, zt, GH, ch=ch, inset=ins, cc=cc, uvoff=(0.11 * L, 0.23))
            p.colbox(0.0, L, 0.0, w, zb, zt)
            out.append(p)
        p = Piece(f"SM_DKG_{fam}_Corner", "kerb", wear=True)
        stone_block(p, JOINT, w - JOINT, JOINT, w - JOINT, zb, zt, GH, ch=ch, inset=min(ins, w / 2 - ch - cc - 0.03),
                    cc=cc, uvoff=(0.5, 0.1))
        p.colbox(0.0, w, 0.0, w, zb, zt)
        out.append(p)
        # 0.5 m, the top sloping down to KERB_END_FREE + ch at local +X; f1 (measurer): the hull is the convex hull of
        # the block itself (it slopes with the top), not a flat box at zt that floated 5 cm over the free end
        p = Piece(f"SM_DKG_{fam}_End", "kerb", wear=True)
        verts = stone_block(p, JOINT, 0.5, 0.0, w, zb, zt, GH, ch=ch, inset=ins, cc=cc, uvoff=(0.3, 0.7),
                            zt_x1=KERB_END_FREE + ch)
        p.colhull(verts)
        p.meta = {"top_m": [zt, KERB_END_FREE + ch], "arris_at_free_end_m": KERB_END_FREE,
                  "hull": "convex hull of the block (sloped)"}
        out.append(p)
    # dark joint fill under the gate band's straights (visible in the 10 mm joints)
    p = Piece("SM_DKG_KerbMortar_7x0p5", "kerb_mortar")
    quad(p, 0.0, 7.0, 0.0, 0.5, 0.06, JF, lambda x, y: (x / TILE, y / TILE))
    p.colbox(0.0, 7.0, 0.0, 0.5, -0.20, 0.06)
    out.append(p)
    return out


def panel_piece(mat_key, w, d):
    fam = {"Gravel": GV, "GravelCoarse": GC, "Soil": SO}[mat_key]
    p = Piece(f"SM_DKG_{mat_key}_{fmt(w)}x{fmt(d)}", mat_key.lower())
    quad(p, 0.0, w, 0.0, d, 0.0, fam, lambda x, y: (x / TILE, y / TILE))
    p.colbox(0.0, w, 0.0, d, -0.20, 0.0)
    return p


def upper_hull_z(pts, query):
    """z of the upper surface of the convex hull of pts at each (x, y) in query (None outside its footprint): the
    minimum over the hull's upward-facing planes (exact for a convex solid)."""
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in pts]
    bmesh.ops.convex_hull(bm, input=vs)
    bm.normal_update()
    planes = []
    for f in bm.faces:
        n = f.normal
        if n.z > 1e-6:
            c = f.calc_center_median()
            planes.append((n.x, n.y, n.z, n.dot(c)))
    xs = [v.co.x for v in bm.verts]
    ys = [v.co.y for v in bm.verts]
    bm.free()
    out = []
    for x, y in query:
        zs = [(d - a * x - b * y) / c for a, b, c, d in planes]
        out.append(min(zs) if zs else None)
    return out, (min(xs), max(xs), min(ys), max(ys))


def bed_piece(name, rect, centre, axes, expo, peak, walls, step=0.125):
    """f1 (judge delta 10): a mounded planting island. One grid mesh over the bed's rect (local origin = the rect's
    SW corner): height = peak (1 - q^2) inside a wobbly superellipse outline (q = its normalised radius; a concave
    dome), 0 outside; 'Blend' vertex colour R = soil weight, 1 inside q 0.78, feathered with noise to 0 by q 1.10,
    so the soil blends into the gravel (height-blended in the material). At every rect border that is not against a
    wall the height and the soil weight are 0: the bed's gravel meets the world-aligned gravel panels invisibly.
    Collision (spec 5.3 "ground, floors"): a flat box at 0 over the rect + the convex hull of the dome (sampled every
    0.25 m); the hull-to-surface gap is measured and stored in meta."""
    x0, x1, y0, y1 = rect
    cx, cy = centre
    ax, ay = axes
    p = Piece(f"SM_DKG_Bed_{name}", "bed", colour="Blend")
    p.part()
    rng = random.Random(name)
    harm = [(k, rng.uniform(0.015, 0.035), rng.uniform(0, 2 * math.pi)) for k in (2, 3, 4, 5)]
    waves = [(rng.uniform(1.5, 4.0), rng.uniform(0, 2 * math.pi), rng.uniform(0, 2 * math.pi)) for _ in range(5)]

    def qn(x, y):
        dx, dy = (x - cx) / ax, (y - cy) / ay
        r = (abs(dx) ** expo + abs(dy) ** expo) ** (1.0 / expo)
        th = math.atan2(dy, dx)
        return r / (1.0 + sum(a * math.sin(k * th + ph) for k, a, ph in harm))

    def noise(x, y):
        return sum(math.sin(f * (x * math.cos(t) + y * math.sin(t)) + ph) for f, t, ph in waves) / len(waves)

    nx, ny = int(round((x1 - x0) / step)), int(round((y1 - y0) / step))
    H, Bl = {}, {}
    for j in range(ny + 1):
        for i in range(nx + 1):
            x, y = x0 + i * step, y0 + j * step
            q = qn(x, y)
            H[i, j] = round(peak * max(0.0, 1.0 - q * q), 5)
            b = 1.0 - min(1.0, max(0.0, (q + 0.07 * noise(x, y) - 0.78) / 0.32))
            Bl[i, j] = b * b * (3 - 2 * b)
    # the non-wall borders must be flat pure gravel
    for (i, j), h in H.items():
        edge = {"W": i == 0, "E": i == nx, "S": j == 0, "N": j == ny}
        if any(v and side not in walls for side, v in edge.items()):
            assert h == 0.0 and Bl[i, j] < 0.02, (name, i, j, h, Bl[i, j])
    for j in range(ny):
        for i in range(nx):
            ids = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
            cos = [(a * step, b * step, H[a, b]) for a, b in ids]
            p.face(cos, BB, [(c[0] / TILE, c[1] / TILE) for c in cos],
                   [(Bl[k], Bl[k], Bl[k], 1.0) for k in ids])
    w, d = x1 - x0, y1 - y0
    p.colbox(0.0, w, 0.0, d, -0.20, 0.0)
    dome = [(i * step, j * step, H[i, j]) for (i, j) in H if i % 2 == 0 and j % 2 == 0 and H[i, j] > 0]
    dome += [(x, y, 0.0) for x, y, _ in dome]
    # rim points on the outline itself (h = 0) so the hull footprint reaches the rim
    dome += [(i * step, j * step, 0.0) for (i, j) in H if H[i, j] == 0 and any(
        H.get((i + a, j + b), 0) > 0 for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))) and i % 2 == 0 and j % 2 == 0]
    p.colhull(dome)
    zq, _ = upper_hull_z(dome, [(i * step, j * step) for (i, j) in H])
    # the collision surface is the higher of the flat box (0) and the dome hull (its plane envelope extrapolates
    # below 0 outside the footprint, so max() also handles the outside)
    gaps = [max(0.0, zh if zh is not None else 0.0) - H[k] for zh, k in zip(zq, H)]
    p.meta = {"rect": list(rect), "peak_m": peak, "outline_centre": list(centre), "semi_axes_m": list(axes),
              "hull_float_max_m": round(max(gaps), 4), "hull_sink_max_m": round(-min(gaps), 4),
              "soil_area_m2_blend_gt_0p5": round(sum(1 for v in Bl.values() if v > 0.5) * step * step, 2)}
    return p


def tuft_piece(name, blades, hmin, hmax, spread, seed, cols):
    """f1 (judge delta 9): a grass / moss tuft for joints and edges: thin triangular blades from a small base, leaning
    out, vertex-coloured root to tip. Spec 5.3: grass and moss dressing has no collision (no UCX)."""
    p = Piece(name, "dressing", colour="Col", collision=False)
    rng = random.Random(seed)
    root, tip, dry = (lin_hex(c) for c in cols)
    for b in range(blades):
        p.part()
        a = rng.uniform(0, 2 * math.pi)
        r0 = rng.uniform(0, spread)
        bx, by = r0 * math.cos(a), r0 * math.sin(a)
        h = rng.uniform(hmin, hmax)
        lean = rng.uniform(0.15, 0.55) * h
        wdt = rng.uniform(0.003, 0.006)
        px, py = -math.sin(a) * wdt, math.cos(a) * wdt
        tx, ty = bx + lean * math.cos(a), by + lean * math.sin(a)
        t = tip if rng.random() > 0.25 else dry
        cos = [(bx - px, by - py, -0.004), (bx + px, by + py, -0.004), (tx, ty, h)]
        c = [root + (1.0,), root + (1.0,), t + (1.0,)]
        p.face(cos, DR, [(0.0, 0.0), (1.0, 0.0), (0.5, 1.0)], c)
    p.colbox(-0.01, 0.01, -0.01, 0.01, -0.004, 0.0)   # r3: trivial UCX (house rule); NoCollision in Unreal
    p.meta = {"blades": blades, "height_m": [hmin, hmax], "collision": "none (spec 5.3 dressing)",
              "ucx": "trivial 2 x 2 x 0.4 cm box at the root (house rule: UCX on every SM_); NoCollision in Unreal"}
    return p


def pebble_piece(name, count, seed):
    """f1 (judge delta 9): a small scatter of stray pebbles (1-2.5 cm, low octahedra) for slab edges and the gravel's
    edge on the sand. No collision (spec 5.3 gravel dressing)."""
    p = Piece(name, "dressing", colour="Col", collision=False)
    rng = random.Random(seed)
    tones = [lin_hex(c) for c in ("#8A837B", "#6F6861", "#9E968B", "#7A6C60", "#5D5853")]
    for _ in range(count):
        p.part()
        cx, cy = rng.uniform(-0.15, 0.15), rng.uniform(-0.10, 0.10)
        a, b = rng.uniform(0.005, 0.012), rng.uniform(0.004, 0.010)
        hz = rng.uniform(0.004, 0.009)
        rot = rng.uniform(0, math.pi)
        cr, sr = math.cos(rot), math.sin(rot)

        def P(u, v, z):
            return (cx + u * cr - v * sr, cy + u * sr + v * cr, z)
        ring = [P(a, 0, 0.3 * hz), P(0, b, 0.3 * hz), P(-a, 0, 0.3 * hz), P(0, -b, 0.3 * hz)]
        top, bot = P(0, 0, hz), P(0, 0, -0.002)
        t = tones[rng.randrange(len(tones))]
        ct = [t + (1.0,)] * 3
        for k in range(4):
            j = (k + 1) % 4
            p.face([ring[k], ring[j], top], DR, [(0, 0), (1, 0), (0.5, 1)], ct)
            p.face([ring[j], ring[k], bot], DR, [(0, 0), (1, 0), (0.5, 1)], [tuple(0.6 * c for c in t) + (1.0,)] * 3)
    p.colbox(-0.01, 0.01, -0.01, 0.01, -0.002, 0.0)   # r3: trivial UCX (house rule); NoCollision in Unreal
    p.meta = {"pebbles": count, "collision": "none (spec 5.3 dressing)",
              "ucx": "trivial 2 x 2 x 0.2 cm box at the centre (house rule: UCX on every SM_); NoCollision in Unreal"}
    return p


def dressing_pieces():
    return [tuft_piece("SM_DKG_Tuft_Grass", 14, 0.045, 0.11, 0.03, 91, ("#3A4222", "#7E8744", "#A3965F")),
            tuft_piece("SM_DKG_Tuft_Moss", 10, 0.015, 0.035, 0.04, 92, ("#353D1F", "#5F6B33", "#7A7A45")),
            pebble_piece("SM_DKG_Pebbles_Stray", 9, 93)]


# --------------------------------------------------------------------------- layout

def rot_about_centre(loc, rz):
    """The E fight-floor half is the W half turned 180 deg about the floor centre (22, 10.5)."""
    return (44.0 - loc[0], 21.0 - loc[1], loc[2]), (rz + 180.0) % 360.0


def layout():
    I = []

    def add(piece, x, y, z=0.0, r=0.0):
        r = ((r + 180.0) % 360.0) - 180.0
        I.append((piece, (round(x, 4), round(y, 4), round(z, 4)), round(r, 3)))

    # fight floor: W half + its edging, and the same turned 180 deg for the E half
    west = [("SM_DKG_SandField_13x17", (8.0, 2.0, 0.0), 0.0),
            ("SM_DKG_SandEdging_Corner", (8.0, 2.0, 0.0), 0.0),       # SW corner
            ("SM_DKG_SandEdging_Corner", (8.0, 19.0, 0.0), -90.0)]    # NW corner
    for x in range(9, 21, 2):
        west.append(("SM_DKG_SandEdging_Straight_2", (float(x), 2.0, 0.0), 0.0))            # south board
        west.append(("SM_DKG_SandEdging_Straight_2", (float(x + 2), 19.0, 0.0), 180.0))     # north board
    y = 3.0
    for L in fill_run(15.0, (2.0, 1.0)):                                                      # west board Y 3-18
        west.append((f"SM_DKG_SandEdging_Straight_{fmt(L)}", (8.0 + EDGE_W, y, 0.0), 90.0))
        y += L
    for piece, loc, r in west:
        add(piece, *loc, r)
        l2, r2 = rot_about_centre(loc, r)
        add(piece, *l2, r2)
    # path: bed + two staggered slab columns
    for k in range(7):
        add("SM_DKG_PathBed_2x3", PATH[0], PATH[2] + 3.0 * k, 0.0)
    # r3 f1: two staggered slab columns (X 21-22 and 22-23), variants cycled so no two neighbours share one
    cols = slab2_columns(round(PATH[3] - PATH[2], 6))
    slab_joints = []
    vrng = random.Random(33)
    prev = {}
    for c, seq in enumerate(cols):
        y = PATH[2]
        x = PATH[0] + c * SLAB2_W
        for k, L in enumerate(seq):
            opts = [v for v in SLAB2_VARIANTS if v != prev.get((c, k - 1)) and v != prev.get((1 - c, k))]
            var = vrng.choice(opts)
            prev[(c, k)] = var
            add(slab2_name(L, var), x, round(y, 6), 0.0, 0.0)
            y = round(y + L, 6)
            slab_joints.append((x, y))
        assert abs(y - PATH[3]) < 1e-6, (c, y)
    # gate kerb band (Kerb50) X 18-26, Y 0-0.5: sloped end pieces at both free ends, varied lengths between
    gx0, gx1, gy0, gy1 = GATE_BAND
    add("SM_DKG_Kerb50_End", gx0 + 0.5, gy1, 0.0, 180.0)
    x = gx0 + 0.5
    kerb_joints = [x]
    for L in KERB50_RUN:
        add(f"SM_DKG_Kerb50_Straight_{fmt(L)}", x, gy0, 0.0, 0.0)
        x += L
        kerb_joints.append(x)
    assert abs(x - (gx1 - 0.5)) < 1e-9, x
    add("SM_DKG_Kerb50_End", gx1 - 0.5, gy0, 0.0, 0.0)
    add("SM_DKG_KerbMortar_7x0p5", gx0 + 0.5, gy0, 0.0, 0.0)
    # soil beds: one mounded piece per bed at its rect's SW corner (never rotated: world-aligned textures)
    for bname, (rect, *_rest) in BEDS.items():
        add(f"SM_DKG_Bed_{bname}", rect[0], rect[2])
    bed_rects = [b[0] for b in BEDS.values()]
    # surround gravel: the whole compound minus the fight floor, path, gate band (f1, measurer: r0 ran gravel under
    # the band, 3.99 m2 of hidden overdraw), the coarse gate strip, beds and building floors
    gexcl = [FIELD_W, FIELD_E, PATH, GATE_BAND, GATE_STRIP] + list(EXCLUDE.values()) + bed_rects
    gravel = greedy_tiles(region_grid([(0.0, 44.0, 0.0, 36.0)], gexcl))
    for (x, y, w, d) in gravel:
        add(f"SM_DKG_Gravel_{fmt(w)}x{fmt(d)}", x, y)
    coarse = greedy_tiles(region_grid([GATE_STRIP], [GATE_BAND, PATH, FIELD_W, FIELD_E] + bed_rects))
    for (x, y, w, d) in coarse:
        add(f"SM_DKG_GravelCoarse_{fmt(w)}x{fmt(d)}", x, y)
    # dressing (f1, judge delta 9): sparse tufts in the path, slab and kerb joints, on the gate strip and at the tree
    # beds' rims; stray pebbles on the slab edges near the gate and along the strip's edge on the sand
    drng = random.Random(2027)
    tufts = []
    for _ in range(10):   # path edge joints (between the berm and the slabs)
        tufts.append((drng.choice((PATH[0] - 0.004, PATH[1] + 0.004)), drng.uniform(1.0, 20.5), 0.004))
    for (x0, yj) in drng.sample([j for j in slab_joints if j[1] < PATH[3] - 1.0], 6):   # r3 f1: slab joints
        tufts.append((x0 + drng.uniform(0.15, 0.85), yj, 0.004))
    for xj in drng.sample(kerb_joints, 4):   # the band's north foot at its joints, and moss in the joints
        tufts.append((xj, gy1 + 0.01, 0.0))
    for _ in range(8):   # the coarse gate strip
        tufts.append((drng.choice((drng.uniform(8.2, 20.8), drng.uniform(23.2, 35.8))), drng.uniform(0.6, 1.9), 0.0))
    for cx in (3.5, 40.5):   # tree bed rims
        for k in range(4):
            a = drng.uniform(0, 2 * math.pi)
            tufts.append((cx + 1.85 * math.cos(a), 16.0 + 1.85 * math.sin(a), 0.0))
    for i, (x, y, z) in enumerate(tufts):
        add("SM_DKG_Tuft_Moss" if i % 3 == 2 else "SM_DKG_Tuft_Grass", x, y, z, drng.uniform(0, 360))
    for xj in kerb_joints[1:-1]:
        add("SM_DKG_Tuft_Moss", xj, gy1 - 0.12, 0.06, drng.uniform(0, 360))
    pebbles = []
    for _ in range(8):   # slab edges near the gate
        pebbles.append((drng.choice((PATH[0] + 0.12, PATH[1] - 0.12, 22.0)), drng.uniform(0.7, 4.0), SLAB_TOP))
    for _ in range(6):   # stray gravel from the strip on the sand's south strip
        pebbles.append((drng.choice((drng.uniform(9.0, 20.5), drng.uniform(23.5, 35.0))), 2.25, 0.0))
    for x, y, z in pebbles:
        add("SM_DKG_Pebbles_Stray", x, y, z, drng.uniform(0, 360))
    zones = {
        "fight_floor_x0_x1_y0_y1": [8.0, 36.0, 2.0, 19.0], "fight_floor_m": [28.0, 17.0],
        "sand_field_W": list(FIELD_W), "sand_field_E": list(FIELD_E), "path": list(PATH),
        "path_width_m": PATH[1] - PATH[0], "path_length_m": PATH[3] - PATH[2],
        "gate_kerb_band": list(GATE_BAND), "gate_strip_coarse_gravel": list(GATE_STRIP),
        "beds": {k: {"rect": list(v[0]), "outline_centre": list(v[1]), "semi_axes_m": list(v[2]),
                     "superellipse_exp": v[3], "peak_m": v[4], "wall_sides": v[5]} for k, v in BEDS.items()},
        "gravel_excluded": {k: list(v) for k, v in EXCLUDE.items()},
        "areas_m2": {"sand_raked_incl_boards": 2 * 13.0 * 17.0,
                     "path": (PATH[1] - PATH[0]) * (PATH[3] - PATH[2]),
                     "gravel_surround": round(sum(w * d for _, _, w, d in gravel), 3),
                     "gravel_coarse_strip": round(sum(w * d for _, _, w, d in coarse), 3),
                     "bed_rects": round(sum((r[1] - r[0]) * (r[3] - r[2]) for r in bed_rects), 3),
                     "gate_band": (GATE_BAND[1] - GATE_BAND[0]) * (GATE_BAND[3] - GATE_BAND[2])},
        "gravel_panels": len(gravel), "gravel_coarse_panels": len(coarse),
        "dressing": {"tufts": len(tufts) + len(kerb_joints) - 2, "pebble_scatters": len(pebbles)},
        "kerb50_run_m": KERB50_RUN,
        "path_slabs_f1": {"width_m": SLAB2_W, "columns_m": cols, "min_joint_offset_m": SLAB2_MIN_OFFSET,
                          "count": sum(len(c) for c in cols)},
    }
    # the ground must tile the compound with no overlap and no hole (panels, fields, path, band, beds, buildings)
    cover = region_grid([], [])
    for rects in ([(x, x + w, y, y + d) for x, y, w, d in gravel + coarse],
                  [FIELD_W, FIELD_E, PATH, GATE_BAND], bed_rects, list(EXCLUDE.values())):
        for (a, b, c, e) in rects:
            for j in range(int(round(c / GRID)), int(round(e / GRID))):
                for i in range(int(round(a / GRID)), int(round(b / GRID))):
                    if 0 <= i < len(cover[0]) and 0 <= j < len(cover):
                        cover[j][i] = cover[j][i] + 1 if cover[j][i] else 1
    cells = [v for row in cover for v in row]
    zones["coverage_check_0p25_cells"] = {"holes": sum(1 for v in cells if not v),
                                          "overlaps": sum(1 for v in cells if v and v > 1)}
    return I, gravel, coarse, zones


# --------------------------------------------------------------------------- lights and cameras

SUN_ELEV_DEG, SUN_HEADING_DEG = 22.0, 45.0  # warm low sun from the west-north-west (reference 2's shadows fall to the
# lower right, toward +X and -Y); heading = degrees from +X toward -Y of the TRAVEL direction (armory convention).
# r0 tests: at 12 and 18 deg, heading 25, the grey-box west tree's canopy shadow (+4.0 to +7.5) crossed both fields.
# 22 deg, heading 45 (from the north-west): computed, the canopy shadow falls 9.9-18.6 m along the ray from (3.5, 16),
# i.e. X 10.5-16.6, Y 9.0-2.8, on the WEST field's near half, as in reference 2; the east tree's shadow leaves the
# compound; the 2 m wall's shadow reaches 5.0 m (3.5 m in X) and stays in the yards


def lights():
    el, az = math.radians(SUN_ELEV_DEG), math.radians(SUN_HEADING_DEG)
    d = (math.cos(el) * math.cos(az), -math.cos(el) * math.sin(az), -math.sin(el))
    from mathutils import Vector
    rot = Vector(d).to_track_quat("-Z", "Y").to_euler()
    return [{"type": "sun", "name": "Sun_Sunset", "rot_deg": [round(math.degrees(a), 3) for a in rot], "kelvin": 2700,
             "elev_deg": SUN_ELEV_DEG, "heading_deg_from_x_toward_minus_y": SUN_HEADING_DEG,
             "travel_dir": [round(c, 4) for c in d]}]


# C_Establish: fitted to dojo1_reference2 (BUILD_NOTES_GROUND.md, stage 1): the sand fields' outline and their
# near/far scale ratio (2.25) give a LEVEL camera 13.6 m south of the near sand edge and 9.7 m up, 24.6 mm lens,
# horizon at image row 180 of 1086 (shift_y -0.2507). The same fit measures the rake spacing (0.18 m) consistently
# at every depth. At spec size that eye sits over the gatehouse roof, so the render hides the gatehouse and the south
# wall from the camera (they still cast shadows); the reference frames the view with gate posts instead.
CAMERAS = [
    {"name": "C_Establish", "loc": [22.0, -11.6, 9.7], "look_at": [22.0, 30.0, 9.7], "lens_mm": 24.6,
     "shift_y": -0.2507, "res": [1448, 1086], "hide_from_camera": ["gatehouse", "south_wall"]},
    # C_Overview: like dojo1_reference1: the field's near/far widths (809 / 735 px) and depth/width foreshortening
    # (0.58) give a long lens 140 m out at 36 deg down
    {"name": "C_Overview", "loc": [22.0, -99.3, 82.3], "look_at": [22.0, 14.0, 0.0], "lens_mm": 94.0,
     "res": [1448, 1086]},
    # C_PlayerEye: 1.7 m eye in the west field, looking east along the rake lines toward the path
    {"name": "C_PlayerEye", "loc": [12.5, 6.6, 1.7], "look_at": [30.0, 8.2, 0.55], "lens_mm": 30.0,
     "res": [1600, 900]},
    # r3: the Unreal judge's framings (layout_showcase.json cameras), for like-for-like Blender checks
    {"name": "CAM_EstablishingRef2", "loc": [22.0, 2.9, 3.1], "look_at": [22.0, 24.0, 0.3], "hfov_deg": 74.0,
     "res": [1448, 1086]},
    {"name": "CAM_PlayerEyeSand", "loc": [16.5, 4.5, 1.65], "look_at": [21.5, 26.0, 2.4], "hfov_deg": 70.0,
     "res": [1920, 1080]},
]


# --------------------------------------------------------------------------- main

def mat_json(v):
    """The material's Unreal recipe for layout_ground.json."""
    if "vertex_colour" in v:
        return dict(v, unreal="BaseColor = VertexColor (the 'Col' layer, linear); no textures; two-sided")
    if "library" in v:
        st = "Granite"
        return dict(v, texture_files={st: {x: f"../Materials/Textures/T_DJ_{st}_{x}.png" for x in ("BC", "N", "ORM")}},
                    unreal=("MI of M_DJ_Lib_Opaque (Scripts/dojo/materials/README.md) with the library Granite maps, "
                            "UseWear on (VertexColor 'Wear'), BaseColor x tint_lin x lerp(warm, cool, "
                            "frac(PerInstanceRandom * 17.31)) x (1 +- instance_tint)"))
    sets = v.get("blend") or [v["texture"]]
    return dict(v, texture_files={t: {s: f"Textures/T_DKG_{t}_{s}.png" for s in ("BC", "N", "ORM")} for t in sets},
                macro_file="Textures/T_DKG_Macro_M.png", macro_tile_m=MACRO_TILE,
                normal="DirectX", orm="R AO, G roughness, B metal",
                unreal=("lerp(" + sets[0] + ", " + sets[1] + ", smoothstep(0.4, 0.6, VertexColor.R + k (0.5 - "
                        "luminance(" + sets[0] + " BC))))") if "blend" in v else None)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    for name in MATERIALS:
        build_material(name)
    djm.make_material(JF)
    kit_coll = bpy.data.collections.new("Kit")
    sc.collection.children.link(kit_coll)
    asm = bpy.data.collections.new("Assembly")
    sc.collection.children.link(asm)

    inst, gravel, coarse, zones = layout()
    pieces = [sand_field_piece()] + edging_pieces() + slab_pieces() + kerb_pieces()
    for key, tiles in (("Gravel", gravel), ("GravelCoarse", coarse)):
        for w, d in sorted({(w, d) for _, _, w, d in tiles}, key=lambda s: (-s[0] * s[1], s)):
            pieces.append(panel_piece(key, w, d))
    pieces += [bed_piece(k, *v) for k, v in BEDS.items()]
    pieces += dressing_pieces()
    meta = {p.name: dict(p.meta, family=p.family, collision=p.collision) for p in pieces}
    objs = {p.name: p.build(kit_coll) for p in pieces}
    for p in pieces:        # r2: the library's weathering on the granite (R grime, G edge wear on the arrises, no dirt)
        if p.family in ("slab", "kerb", "paver"):
            djm.bake_wear(objs[p.name], ground_z=-1.0)
        if p.family == "paver":   # r3: per-paver tone on the Wear R channel
            meta[p.name]["paver_tone_wear_r"] = paver_tone(objs[p.name])
        if p.name.startswith("SM_DKG_Slab_"):   # r3 f1: per-slab tone
            meta[p.name]["slab_tone_wear_r"] = slab_tone(objs[p.name])
    kit_coll.hide_render = True
    kit_coll.hide_viewport = True
    missing = {p for p, _, _ in inst} - set(objs)
    assert not missing, missing

    bboxes = []
    for n, (piece, loc, rz) in enumerate(inst):
        o = bpy.data.objects.new(f"{piece}__{n:04d}", objs[piece].data)
        o.matrix_world = Matrix.Translation(loc) @ Matrix.Rotation(math.radians(rz), 4, "Z")
        asm.objects.link(o)
        pts = [o.matrix_world @ v.co for v in o.data.vertices]
        bboxes.append([round(min(q[i] for q in pts), 4) for i in range(3)] +
                      [round(max(q[i] for q in pts), 4) for i in range(3)])

    tris = {k: sum(len(p.vertices) - 2 for p in o.data.polygons) for k, o in objs.items()}
    count = {}
    for p, _, _ in inst:
        count[p] = count.get(p, 0) + 1
    used_mats = {m.name for o in objs.values() for m in o.data.materials if m}
    WORK.mkdir(parents=True, exist_ok=True)
    data = {"units": "metres, Blender frame (UE: x*100, -y*100, z*100, yaw = -rot_z)",
            "frame": "origin = inside SW corner of the compound at courtyard level; X east 0-44, Y north 0-36 "
                     "(DOJO_ARENA_SPEC section 1, the same frame as the grey-box layout.json)",
            "kit": "dojo kit 2, ground", "date": "2026-09-27", "round": "r3 (2026-09-28)",
            "pieces": sorted(objs),
            "instances": [{"piece": p, "loc": list(l), "rot_z": r, "bbox_min_max": b}
                          for (p, l, r), b in zip(inst, bboxes)],
            "lights": lights(),
            "materials": {k: mat_json(v) for k, v in MATERIALS.items() if k in used_mats},
            "materials_library": {JF: {"library": JF, "use": "the joint fill under the slab and kerb joints",
                                       "textures": "../Materials/Textures/T_DJ_GraniteRubble_{BC,N,ORM}.png"}},
            "cameras": CAMERAS,
            "zones": zones,
            "collision": {"rule": "f1: every hull sits at the visible walk surface: sand, gravel, beds' flat part "
                                  "at 0 (the sand berms rise 7-10 mm over the last 8 cm, visual only); slabs +0.020 "
                                  "(2 cm proud); boards +0.008 (visible top 6-10 mm); gate band +0.10 and bed kerbs "
                                  "+0.05 as boxes; kerb End pieces = convex hull of the sloped block; bed mounds = "
                                  "flat box + convex hull of the dome (gaps in piece_meta). Every step is under the "
                                  "0.45 m step-up. Rake grooves, gravel and soil relief are normal-map only.",
                          "class": "Ground, floors (spec 5.3): block Pawn, Camera, Visibility, traversal",
                          "dressing": "SM_DKG_Tuft_* and SM_DKG_Pebbles_*: no collision (spec 5.3 grass, moss, "
                                      "gravel dressing); r3: each carries a trivial UCX (house rule) and stays "
                                      "NoCollision in Unreal (piece_meta collision False -> class nocollision)"},
            "texel_density_px_per_cm": 5.12, "tile_m": TILE, "rake_spacing_m": round(RAKE_P, 4),
            "piece_meta": meta, "instance_counts": count,
            "tris": tris,
            "tris_assembled_total": sum(tris[p] * c for p, c in count.items())}
    (WORK / "layout_ground.json").write_text(json.dumps(data, indent=1), encoding="utf-8")

    qa, waive = {}, {"uv0_tile_range", "uv_no_overlap"}
    for name, o in objs.items():
        r = qa_check([o], require_uv1=True, require_ucx=True)   # r3: every SM_ has a UCX (dressing: trivial)
        fails = [c for c in r["checks"] if not c["passed"]]
        hard = [c for c in fails if c["name"] not in waive]
        qa[name] = {"hard_fails": hard, "waived": [c["name"] for c in fails if c["name"] in waive],
                    "tris": r["triangles"].get(name),
                    "texel": next((c["detail"] for c in r["checks"] if c["name"] == "texel_density"), None)}
    (WORK / "qa_report.json").write_text(json.dumps(qa, indent=1, default=str), encoding="utf-8")
    hard_total = sum(len(v["hard_fails"]) for v in qa.values())
    print(f"QA: {len(objs)} pieces, {len(inst)} instances, hard fails {hard_total}")
    for k, v in qa.items():
        for c in v["hard_fails"]:
            print("  FAIL", k, c["name"], str(c["detail"])[:200])

    if "--no-export" not in ARGS and hard_total == 0:
        kit_coll.hide_viewport = False
        results = {}
        for name, o in objs.items():
            res = export_fbx(str(EXPORT_DIR / f"{name}.fbx"), [o], kind="static", sidecar=False)
            results[name] = {"objects": res["objects"], "warnings": res["warnings"]}
        (WORK / "export_report.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
        kit_coll.hide_viewport = True
        print(f"exported {len(results)} FBX to {EXPORT_DIR}")
    BLEND.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    print("saved", BLEND, "pieces", len(objs), "instances", len(inst), "zones", json.dumps(zones["areas_m2"]))


main()
