"""Shared dojo material library: the Blender material builder + UV / weathering helpers every dojo kit uses.

Textures come from dojo_tex_gen.py (numpy generators, same folder): Exports/DojoKit/Materials/Textures/T_DJ_*.
The Unreal recipe for every material is in README.md next to this file.

Usage from any headless build script (blender -b --factory-startup --python build_x.py):

    import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/dojo/materials")
    import dojo_materials as djm
    face, end = djm.make_material("M_DJ_TimberDark"), djm.make_material("M_DJ_TimberDarkEnd")
    obj.data.materials.append(face); obj.data.materials.append(end)
    djm.grain_uv(obj, "TimberDark", end_set="TimberDarkEnd", end_material_index=1)   # grain along each member
    djm.bake_wear(obj)                                                                # 'Wear' corner colours
    stone = djm.make_material("M_DJ_Granite"); djm.box_uv(obj2, "Granite")          # no mirrored faces

    # regenerate textures (numpy, no bpy needed):  python dojo_tex_gen.py [--only Granite,Iron]

Public API
    MATERIALS                       name -> spec (set, shading kind, defaults); list_materials()
    make_material(name, **overrides) -> bpy.types.Material  (idempotent: reuses an existing material of that name
                                     unless rebuild=True). Overrides: tint (linear RGB mult), rough_mult,
                                     normal_strength, projection ('UV' | 'BOX' Blender-only preview), box_blend,
                                     emission_strength, wear (bool), uv_map (name), tex_dir
    set_info(set_name)              size / tile metres / texel density of a texture set
    grain_uv(obj, set_name, end_set=None, faces=None, end_material_index=None, end_cos=0.72, seed=None,
             round_mode='auto', uv_map='UVMap')   timber: U along each loose part's long axis (PCA), end faces
                                     planar with the end-grain tile; per-part random offsets so members differ
    box_uv(obj, set_name, faces=None, space='OBJECT', seed=None, uv_map='UVMap')
                                     box projection with every face's texture upright and NOT mirrored
    round_uv(obj, set_name, faces=None, seed=None, uv_map='UVMap')   cylinders / barrels / posts: U along the
                                     axis, V = arc length round it (the seam faces local -B)
    rope_uv(obj, diameter, mode='straight'|'ring', lays_per_tile=4, lay_ratio=3.2, faces=None, uv_map='UVMap')
    unit_uv(obj, faces=None, uv_map='UVMap')   0-1 over each face (glass panes, vending display)
    bake_wear(obj, ao_rays=16, ao_dist=0.15, bevel_max=0.03, ground_z=None, dirt_h=0.45, attr='Wear')
                                     corner colour attribute: R grime/occlusion, G edge wear (ONLY on narrow
                                     convex bevel faces, never on the broad faces), B ground dirt
    texel_density(obj, set_name, uv_map='UVMap') -> dict   px/cm percentiles over the mesh (area weighted)

Weathering maths (identical in Unreal, see README):
    m  = WearMask(UV * tile_m)                       breakup, 1 m tile
    bc = bc * (1 - 0.40 * R)                         grime / occlusion
    e  = saturate((G * (0.35 + m) - 0.55) * 2.5)     broken edge wear (~40 % of a bevel face at most)
    bc = lerp(bc, desat(bc, 0.35) * 1.30, 0.55 * e)  <= +17 % lift: no pale band
    bc = lerp(bc, DUST, 0.45 * B * m)                ground dirt; rough += 0.06 * e + 0.08 * B
"""
import math
import os
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import dojo_tex_gen as tg  # noqa: E402  (numpy only)

ROOT = HERE.parents[2]
TEX_DIR = ROOT / "Exports" / "DojoKit" / "Materials" / "Textures"
VERSION = tg.LIB_VERSION
DUST_SRGB = (0.46, 0.41, 0.35)

# name -> (texture set, shading kind, defaults)
MATERIALS = {
    "M_DJ_TimberDark":     dict(set="TimberDark", kind="opaque", wear=True, normal_strength=1.0),
    "M_DJ_TimberDarkEnd":  dict(set="TimberDarkEnd", kind="opaque", wear=True, normal_strength=1.0),
    "M_DJ_TimberAged":     dict(set="TimberAged", kind="opaque", wear=True, normal_strength=1.0),
    "M_DJ_TimberAgedEnd":  dict(set="TimberAgedEnd", kind="opaque", wear=True, normal_strength=1.0),
    "M_DJ_Granite":        dict(set="Granite", kind="opaque", wear=True, normal_strength=1.0),
    "M_DJ_GraniteRubble":  dict(set="GraniteRubble", kind="opaque", wear=True, normal_strength=1.0),
    "M_DJ_Iron":           dict(set="Iron", kind="opaque", wear=False, normal_strength=1.0),
    "M_DJ_Rope":           dict(set="Rope", kind="opaque", wear=False, normal_strength=1.0),
    "M_DJ_PlasterCream":   dict(set="PlasterCream", kind="opaque", wear=True, normal_strength=1.0),
    "M_DJ_PlasterEarth":   dict(set="PlasterEarth", kind="opaque", wear=True, normal_strength=1.0),
    "M_DJ_RoofTile":       dict(set="RoofTile", kind="opaque", wear=False, normal_strength=1.0),
    "M_DJ_Lacquer":        dict(set="Lacquer", kind="opaque", wear=True, normal_strength=1.0),
    "M_DJ_GlassAmber":     dict(set="GlassAmber", kind="emissive", wear=False, normal_strength=0.5,
                                emission_strength=5.0, base_mult=0.25, rough_mult=1.0),
    "M_DJ_VendingPanel":   dict(set="VendingPanel", kind="emissive", wear=False, normal_strength=0.3,
                                emission_strength=1.6, base_mult=0.25, rough_mult=1.0),
    # r5 named variant (round-4 fixes track): the hall's lit shoji paper, unit UV per lattice CELL (unit_uv on each
    # cell quad), honey amber with bright cell cores; GlassAmber stays as it is for lanterns, lamps and windows
    "M_DJ_ShojiPaper":     dict(set="ShojiPaper", kind="emissive", wear=False, normal_strength=0.3,
                                emission_strength=0.75, base_mult=0.25, rough_mult=1.0),
}


def list_materials():
    return sorted(MATERIALS)


def set_info(set_name):
    s = tg.SETS[set_name]
    w, h = s["size"]
    tm = s["tile_m"]
    return {"set": set_name, "size_px": (w, h), "tile_m": tm,
            "px_per_cm": (w / (tm[0] * 100.0) if tm else None)}


def _tile(set_name):
    tm = tg.SETS[set_name]["tile_m"]
    return tm if tm else (1.0, 1.0)


# ------------------------------------------------------------------------------------------------ materials
def _img(path, non_color):
    img = bpy.data.images.load(str(path), check_existing=True)
    img.colorspace_settings.name = "Non-Color" if non_color else "sRGB"
    return img


def _wear_group():
    """Node group DJ_Wear: (Color, Rough, Wear RGB, Mask) -> (Color, Rough). The README's maths."""
    name = "DJ_Wear_v1"
    if name in bpy.data.node_groups:
        return bpy.data.node_groups[name]
    g = bpy.data.node_groups.new(name, "ShaderNodeTree")
    it = g.interface
    it.new_socket("Color", in_out="INPUT", socket_type="NodeSocketColor")
    it.new_socket("Rough", in_out="INPUT", socket_type="NodeSocketFloat")
    it.new_socket("Wear", in_out="INPUT", socket_type="NodeSocketColor")
    it.new_socket("Mask", in_out="INPUT", socket_type="NodeSocketFloat")
    it.new_socket("Color", in_out="OUTPUT", socket_type="NodeSocketColor")
    it.new_socket("Rough", in_out="OUTPUT", socket_type="NodeSocketFloat")
    N, L = g.nodes, g.links
    gi = N.new("NodeGroupInput")
    go = N.new("NodeGroupOutput")
    sep = N.new("ShaderNodeSeparateColor")
    L.new(gi.outputs["Wear"], sep.inputs["Color"])

    def math(op, a, b=None, clamp=False, v1=None, v2=None):
        m = N.new("ShaderNodeMath")
        m.operation = op
        m.use_clamp = clamp
        if a is not None:
            L.new(a, m.inputs[0])
        else:
            m.inputs[0].default_value = v1
        if b is not None:
            L.new(b, m.inputs[1])
        elif v2 is not None:
            m.inputs[1].default_value = v2
        return m.outputs[0]

    def mix(a, b, fac, blend="MIX"):
        m = N.new("ShaderNodeMix")
        m.data_type = "RGBA"
        m.blend_type = blend
        L.new(fac, m.inputs["Factor"])
        L.new(a, m.inputs["A"])
        if isinstance(b, tuple):
            m.inputs["B"].default_value = b
        else:
            L.new(b, m.inputs["B"])
        return m.outputs["Result"]

    R, G, B = sep.outputs[0], sep.outputs[1], sep.outputs[2]
    # grime: bc *= 1 - 0.4 R
    kR = math("MULTIPLY", R, v2=-0.40)
    kR = math("ADD", kR, v2=1.0)
    c1m = N.new("ShaderNodeMix")
    c1m.data_type = "RGBA"
    c1m.blend_type = "MULTIPLY"
    c1m.inputs["Factor"].default_value = 1.0
    L.new(gi.outputs["Color"], c1m.inputs["A"])
    cmb = N.new("ShaderNodeCombineColor")
    for i in range(3):
        L.new(kR, cmb.inputs[i])
    L.new(cmb.outputs[0], c1m.inputs["B"])
    c1 = c1m.outputs["Result"]
    # edge: e = sat((G * (0.35 + m) - 0.55) * 2.5)
    m035 = math("ADD", gi.outputs["Mask"], v2=0.35)
    e = math("MULTIPLY", G, m035)
    e = math("SUBTRACT", e, v2=0.55)
    e = math("MULTIPLY", e, v2=2.5, clamp=True)
    # worn colour = desat(c1, 0.35) * 1.30
    hsv = N.new("ShaderNodeHueSaturation")
    hsv.inputs["Saturation"].default_value = 0.65
    hsv.inputs["Value"].default_value = 1.30
    L.new(c1, hsv.inputs["Color"])
    e55 = math("MULTIPLY", e, v2=0.55)
    c2 = mix(c1, hsv.outputs["Color"], e55)
    # dirt: lerp(c2, DUST, 0.45 B m)
    bm_ = math("MULTIPLY", B, gi.outputs["Mask"])
    bm_ = math("MULTIPLY", bm_, v2=0.45)
    dust = tuple(_lin(c) for c in DUST_SRGB) + (1.0,)
    c3 = mix(c2, dust, bm_)
    L.new(c3, go.inputs["Color"])
    r = math("MULTIPLY", e, v2=0.06)
    r = math("ADD", r, gi.outputs["Rough"])
    rb = math("MULTIPLY", B, v2=0.08)
    r = math("ADD", r, rb, clamp=True)
    L.new(r, go.inputs["Rough"])
    return g


def _lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def make_material(name, rebuild=False, **ov):
    """Build (or reuse) one library material. name must be a key of MATERIALS."""
    if name not in MATERIALS:
        raise KeyError(f"{name}: not in the dojo library ({', '.join(list_materials())})")
    if name in bpy.data.materials and not rebuild:
        return bpy.data.materials[name]
    spec = dict(MATERIALS[name])
    spec.update(ov)
    set_name = spec["set"]
    tex_dir = Path(spec.get("tex_dir", TEX_DIR))
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    N, L = nt.nodes, nt.links
    for n in list(N):
        N.remove(n)
    out = N.new("ShaderNodeOutputMaterial")
    bsdf = N.new("ShaderNodeBsdfPrincipled")
    L.new(bsdf.outputs[0], out.inputs["Surface"])
    proj = spec.get("projection", "UV").upper()
    if proj == "BOX":
        tc = N.new("ShaderNodeTexCoord")
        mp = N.new("ShaderNodeMapping")
        tu, tv = _tile(set_name)
        mp.inputs["Scale"].default_value = (1.0 / tu, 1.0 / tu, 1.0 / tv)
        L.new(tc.outputs["Object"], mp.inputs["Vector"])
        vec = mp.outputs["Vector"]
    else:
        uvn = N.new("ShaderNodeUVMap")
        if spec.get("uv_map"):
            uvn.uv_map = spec["uv_map"]
        vec = uvn.outputs["UV"]

    def tex(suffix, non_color):
        t = N.new("ShaderNodeTexImage")
        t.image = _img(tex_dir / f"T_DJ_{set_name}_{suffix}.png", non_color)
        t.interpolation = "Linear"
        if proj == "BOX":
            t.projection = "BOX"
            t.projection_blend = spec.get("box_blend", 0.2)
        L.new(vec, t.inputs["Vector"])
        return t

    bc = tex("BC", False)
    nrm = tex("N", True)
    orm = tex("ORM", True)
    col = bc.outputs["Color"]
    if spec.get("tint"):
        tn = N.new("ShaderNodeMix")
        tn.data_type = "RGBA"
        tn.blend_type = "MULTIPLY"
        tn.inputs["Factor"].default_value = 1.0
        L.new(col, tn.inputs["A"])
        tn.inputs["B"].default_value = tuple(spec["tint"]) + (1.0,)
        col = tn.outputs["Result"]
    sep = N.new("ShaderNodeSeparateColor")
    L.new(orm.outputs["Color"], sep.inputs["Color"])
    rough = sep.outputs[1]
    rm = spec.get("rough_mult", 1.0)
    if rm != 1.0:
        m = N.new("ShaderNodeMath")
        m.operation = "MULTIPLY"
        m.use_clamp = True
        L.new(rough, m.inputs[0])
        m.inputs[1].default_value = rm
        rough = m.outputs[0]
    if spec.get("wear"):
        attr = N.new("ShaderNodeAttribute")
        attr.attribute_type = "GEOMETRY"
        attr.attribute_name = spec.get("wear_attr", "Wear")
        wm = N.new("ShaderNodeTexImage")
        wm.image = _img(tex_dir / "T_DJ_WearMask_M.png", True)
        tu, tv = _tile(set_name)
        mp2 = N.new("ShaderNodeMapping")
        mp2.inputs["Scale"].default_value = (tu, tv, 1.0)
        L.new(vec, mp2.inputs["Vector"])
        L.new(mp2.outputs["Vector"], wm.inputs["Vector"])
        if proj == "BOX":
            wm.projection = "BOX"
        grp = N.new("ShaderNodeGroup")
        grp.node_tree = _wear_group()
        L.new(col, grp.inputs["Color"])
        L.new(rough, grp.inputs["Rough"])
        L.new(attr.outputs["Color"], grp.inputs["Wear"])
        L.new(wm.outputs["Color"], grp.inputs["Mask"])
        col, rough = grp.outputs["Color"], grp.outputs["Rough"]
    L.new(rough, bsdf.inputs["Roughness"])
    L.new(sep.outputs[2], bsdf.inputs["Metallic"])
    # DirectX normal -> Blender (OpenGL): flip green
    ns = N.new("ShaderNodeSeparateColor")
    L.new(nrm.outputs["Color"], ns.inputs["Color"])
    inv = N.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    L.new(ns.outputs[1], inv.inputs[1])
    nc = N.new("ShaderNodeCombineColor")
    L.new(ns.outputs[0], nc.inputs[0])
    L.new(inv.outputs[0], nc.inputs[1])
    L.new(ns.outputs[2], nc.inputs[2])
    nm = N.new("ShaderNodeNormalMap")
    nm.inputs["Strength"].default_value = spec.get("normal_strength", 1.0)
    if proj != "BOX" and spec.get("uv_map"):
        nm.uv_map = spec["uv_map"]
    L.new(nc.outputs[0], nm.inputs["Color"])
    L.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    if spec["kind"] == "emissive":
        bm = N.new("ShaderNodeMix")
        bm.data_type = "RGBA"
        bm.blend_type = "MULTIPLY"
        bm.inputs["Factor"].default_value = 1.0
        L.new(col, bm.inputs["A"])
        k = spec.get("base_mult", 0.25)
        bm.inputs["B"].default_value = (k, k, k, 1.0)
        L.new(bm.outputs["Result"], bsdf.inputs["Base Color"])
        L.new(col, bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = spec.get("emission_strength", 10.0)
    else:
        L.new(col, bsdf.inputs["Base Color"])
    mat["dj_library"] = VERSION
    mat["dj_set"] = set_name
    return mat


# ------------------------------------------------------------------------------------------------ mesh helpers
def _bm(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()
    return bm


def _uv_layer(bm, obj, uv_map):
    me = obj.data
    if uv_map not in me.uv_layers:
        me.uv_layers.new(name=uv_map)
    # bmesh copy was made before the layer existed: fetch by name, create if missing
    lay = bm.loops.layers.uv.get(uv_map)
    if lay is None:
        lay = bm.loops.layers.uv.new(uv_map)
    return lay


def _metric(obj):
    """Object-space -> metric frame (rotation-free, scale applied): p_m = S @ p. Keeps world scale on members."""
    return obj.matrix_world.to_3x3()


def _parts(bm, faces):
    """Connected face islands within the face subset (edge-connected)."""
    fset = set(faces)
    seen, parts = set(), []
    for f in faces:
        if f.index in seen:
            continue
        stack, part = [f], []
        seen.add(f.index)
        while stack:
            c = stack.pop()
            part.append(c)
            for e in c.edges:
                for g in e.link_faces:
                    if g in fset and g.index not in seen:
                        seen.add(g.index)
                        stack.append(g)
        parts.append(part)
    return parts


def _pca(points):
    n = len(points)
    c = sum(points, Vector()) / n
    cov = Matrix(((0, 0, 0), (0, 0, 0), (0, 0, 0)))
    for p in points:
        d = p - c
        for i in range(3):
            for j in range(3):
                cov[i][j] += d[i] * d[j] / n
    # power iteration for the principal axis
    a = Vector((1, 0.3, 0.2)).normalized()
    for _ in range(60):
        a = (cov @ a)
        if a.length < 1e-12:
            a = Vector((1, 0, 0))
            break
        a.normalize()
    # smallest axis: power iteration on (trace*I - cov)
    tr = cov[0][0] + cov[1][1] + cov[2][2]
    inv = Matrix.Identity(3) * tr - cov
    b = a.orthogonal().normalized()
    for _ in range(60):
        b = inv @ b
        b = (b - a * b.dot(a))
        if b.length < 1e-12:
            b = a.orthogonal()
        b.normalize()
    return c, a, b


def _canon_axis(a):
    """Stable sign: the largest component positive (so neighbouring parallel members run the same way)."""
    i = max(range(3), key=lambda k: abs(a[k]))
    return a if a[i] >= 0 else -a


def _faces_sel(bm, faces):
    return [bm.faces[i] for i in faces] if faces is not None else list(bm.faces)


def _rng(obj, seed):
    return random.Random((seed if seed is not None else 0) * 1000003 + sum(map(ord, obj.name)))


def grain_uv(obj, set_name="TimberDark", end_set=None, faces=None, end_material_index=None, end_cos=0.72,
             seed=None, round_mode="auto", uv_map="UVMap"):
    """Timber UVs in tile units: each loose part's long axis (PCA) is U (the grain), side faces take V across the
    face, end faces (|n.axis| > end_cos) get a planar end-grain projection with end_set's tile and, if given,
    end_material_index. Round parts (auto: >= 10 distinct side normals) get V = arc length round the axis.
    Random per-part offsets make every member sample a different board of the tile.
    ORDER: append the material slots BEFORE calling this (mesh.materials.clear() resets every face's
    material_index to 0, which would put the face material back on the end faces)."""
    bm = _bm(obj)
    lay = _uv_layer(bm, obj, uv_map)
    S = _metric(obj)
    tu, tv = _tile(set_name)
    eu, ev = _tile(end_set or set_name)
    rng = _rng(obj, seed)
    stats = {"parts": 0, "end_faces": 0, "round_parts": 0}
    for part in _parts(bm, _faces_sel(bm, faces)):
        verts = {v for f in part for v in f.verts}
        pts = [S @ v.co for v in verts]
        c, a, _small = _pca(pts)
        a = _canon_axis(a)
        b = a.orthogonal().normalized()
        cc = a.cross(b).normalized()
        ou, ov = rng.uniform(0, 1), rng.uniform(0, 1)
        oeu, oev = rng.uniform(0, 1), rng.uniform(0, 1)
        side_normals = []
        for f in part:
            n = (S @ f.normal).normalized() if f.normal.length > 0 else Vector((0, 0, 1))
            if abs(n.dot(a)) <= end_cos:
                side_normals.append(n)
        distinct = []
        for n in side_normals:
            if all(n.dot(m) < 0.985 for m in distinct):
                distinct.append(n)
                if len(distinct) > 12:
                    break
        is_round = (round_mode is True) or (round_mode == "auto" and len(distinct) >= 10)
        stats["round_parts"] += int(is_round)
        radius = sum(((p - c) - a * (p - c).dot(a)).length for p in pts) / len(pts)
        for f in part:
            n = (S @ f.normal).normalized() if f.normal.length > 0 else Vector((0, 0, 1))
            if abs(n.dot(a)) > end_cos:
                stats["end_faces"] += 1
                s = 1.0 if n.dot(a) > 0 else -1.0
                for l in f.loops:
                    p = S @ l.vert.co - c
                    l[lay].uv = (s * p.dot(b) / eu + oeu, p.dot(cc) / ev + oev)
                if end_material_index is not None:
                    f.material_index = end_material_index
                continue
            if is_round:
                angs = []
                for l in f.loops:
                    p = S @ l.vert.co - c
                    angs.append(math.atan2(p.dot(cc), p.dot(b)))
                ref = angs[0]
                for i, l in enumerate(f.loops):
                    d = angs[i] - ref
                    if d > math.pi:
                        angs[i] -= 2 * math.pi
                    elif d < -math.pi:
                        angs[i] += 2 * math.pi
                    p = S @ l.vert.co - c
                    l[lay].uv = (p.dot(a) / tu + ou, angs[i] * radius / tv + ov)
            else:
                t = n.cross(a)
                t = t.normalized() if t.length > 1e-6 else b
                for l in f.loops:
                    p = S @ l.vert.co - c
                    l[lay].uv = (p.dot(a) / tu + ou, p.dot(t) / tv + ov)
        stats["parts"] += 1
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return stats


def box_uv(obj, set_name="Granite", faces=None, space="OBJECT", seed=None, uv_map="UVMap"):
    """Box projection in tile units, each face by its dominant axis, oriented so the texture reads upright and
    UNMIRRORED from outside (+X: (y, z), -X: (-y, z), +Y: (-x, z), -Y: (x, z), +Z: (x, y), -Z: (x, -y)).
    space='WORLD' keeps neighbouring pieces continuous; a per-object random offset breaks repeats otherwise."""
    bm = _bm(obj)
    lay = _uv_layer(bm, obj, uv_map)
    M = obj.matrix_world if space == "WORLD" else Matrix.LocRotScale(None, None, obj.matrix_world.to_scale())
    R = M.to_3x3()
    tu, tv = _tile(set_name)
    rng = _rng(obj, seed)
    ou, ov = (0.0, 0.0) if space == "WORLD" else (rng.uniform(0, 1), rng.uniform(0, 1))
    for f in _faces_sel(bm, faces):
        n = (R @ f.normal)
        ax = max(range(3), key=lambda k: abs(n[k]))
        s = 1.0 if n[ax] >= 0 else -1.0
        for l in f.loops:
            p = M @ l.vert.co
            if ax == 0:
                u, v = s * p.y, p.z
            elif ax == 1:
                u, v = -s * p.x, p.z
            else:
                u, v = p.x, s * p.y
            l[lay].uv = (u / tu + ou, v / tv + ov)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def round_uv(obj, set_name="Lacquer", faces=None, seed=None, uv_map="UVMap"):
    """Cylinders, barrels, round posts: U along the axis, V = arc length round it (one seam). Wrapper of
    grain_uv(round_mode=True) with the caps projected planar."""
    return grain_uv(obj, set_name, end_set=set_name, faces=faces, seed=seed, round_mode=True, uv_map=uv_map)


def rope_uv(obj, diameter, mode="straight", lays_per_tile=4, lay_ratio=3.2, faces=None, uv_map="UVMap"):
    """Rope: U = distance along the rope / (lays_per_tile * lay length), V = turns round the rope (0..1).
    mode 'straight': each loose part along its PCA axis; 'ring': a torus-like coil round its smallest PCA axis."""
    bm = _bm(obj)
    lay = _uv_layer(bm, obj, uv_map)
    S = _metric(obj)
    tile_u = lays_per_tile * lay_ratio * diameter
    for part in _parts(bm, _faces_sel(bm, faces)):
        pts = [S @ v.co for v in {v for f in part for v in f.verts}]
        c, a, k = _pca(pts)
        if mode == "ring":
            x = k.orthogonal().normalized()
            y = k.cross(x).normalized()
            R0 = sum(((q - c) - k * (q - c).dot(k)).length for q in pts) / len(pts)
            per_u = 2 * math.pi * R0 / tile_u
        else:
            b = a.orthogonal().normalized()
            cc = a.cross(b).normalized()
            per_u = None
        for f in part:
            uvs = []
            for l in f.loops:
                p = S @ l.vert.co - c
                if mode == "ring":
                    r = p - k * p.dot(k)
                    rn = r.normalized() if r.length > 1e-9 else x
                    phi = math.atan2(r.dot(y), r.dot(x))
                    q = p - rn * R0
                    th = math.atan2(q.dot(k), q.dot(rn))
                    uvs.append([phi * R0 / tile_u, th / (2 * math.pi)])
                else:
                    th = math.atan2(p.dot(cc), p.dot(b))
                    uvs.append([p.dot(a) / tile_u, th / (2 * math.pi)])
            for i in range(1, len(uvs)):             # unwrap every corner next to the face's first corner
                for j, per in ((1, 1.0), (0, per_u)):
                    if per is None:
                        continue
                    d = uvs[i][j] - uvs[0][j]
                    if d > per / 2:
                        uvs[i][j] -= per
                    elif d < -per / 2:
                        uvs[i][j] += per
            for l, uv in zip(f.loops, uvs):
                l[lay].uv = uv
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def unit_uv(obj, faces=None, uv_map="UVMap"):
    """0-1 over each face: U along the face's longest edge direction, V across (for panes and the vending display;
    the emissive hotspot is centred on each face)."""
    bm = _bm(obj)
    lay = _uv_layer(bm, obj, uv_map)
    S = _metric(obj)
    for f in _faces_sel(bm, faces):
        n = (S @ f.normal).normalized()
        ez = Vector((0, 0, 1))
        up = ez - n * ez.dot(n)
        if up.length < 1e-4:
            up = Vector((0, 1, 0)) - n * n.y
        up.normalize()
        rt = up.cross(n).normalized()
        ps = [S @ l.vert.co for l in f.loops]
        us = [p.dot(rt) for p in ps]
        vs = [p.dot(up) for p in ps]
        u0, u1, v0, v1 = min(us), max(us), min(vs), max(vs)
        for l, u, v in zip(f.loops, us, vs):
            l[lay].uv = ((u - u0) / max(u1 - u0, 1e-9), (v - v0) / max(v1 - v0, 1e-9))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def bake_wear(obj, ao_rays=16, ao_dist=0.15, bevel_max=0.03, edge_deg=20.0, ground_z=None, dirt_h=0.45,
              attr="Wear", seed=7):
    """Weathering corner colours (BYTE_COLOR, CORNER) read by the library materials and by Unreal:
      R = grime: ray-traced occlusion within ao_dist (hemisphere, ao_rays) + concave-edge corners
      G = edge wear: 1 ONLY on narrow convex bevel faces (face width <= bevel_max m with a convex edge > edge_deg),
          0 on every broad face, so no face turns pale as a whole (the judged 'pale bevel band' cause)
      B = ground dirt: 1 at ground_z (default: the object's lowest point) fading to 0 at ground_z + dirt_h."""
    me = obj.data
    bm = _bm(obj)
    Mw = obj.matrix_world
    wbm = bm.copy()
    wbm.transform(Mw)
    bvh = BVHTree.FromBMesh(wbm)
    wbm.free()
    R3 = Mw.to_3x3()
    zs = [(Mw @ v.co).z for v in bm.verts]
    gz = min(zs) if ground_z is None else ground_z
    rnd = random.Random(seed)
    dirs = []
    for i in range(ao_rays):                       # cosine-weighted hemisphere (z up), fixed set
        u1, u2 = (i + rnd.random()) / ao_rays, rnd.random()
        r = math.sqrt(u1)
        th = 2 * math.pi * u2
        dirs.append(Vector((r * math.cos(th), r * math.sin(th), math.sqrt(max(0.0, 1 - u1)))))
    occ = {}
    for v in bm.verts:
        n = (R3 @ v.normal).normalized() if v.normal.length > 0 else Vector((0, 0, 1))
        p = Mw @ v.co + n * 1e-3
        rot = n.to_track_quat("Z", "Y").to_matrix()
        hit = 0
        for d in dirs:
            h = bvh.ray_cast(p, rot @ d, ao_dist)
            if h[0] is not None:
                hit += 1
        concave = any(e.is_manifold and e.calc_face_angle_signed(0.0) < -math.radians(edge_deg)
                      for e in v.link_edges)
        occ[v.index] = min(1.0, hit / ao_rays * 1.4 + (0.35 if concave else 0.0))
    bevel_face = {}
    for f in bm.faces:
        convex = [e for e in f.edges if e.is_manifold and e.calc_face_angle_signed(0.0) > math.radians(edge_deg)]
        if not convex:
            bevel_face[f.index] = False
            continue
        # narrow = the face's width across its longest edge is small
        le = max(f.edges, key=lambda e: e.calc_length())
        d = (le.verts[1].co - le.verts[0].co)
        d = (R3 @ d).normalized() if d.length > 0 else Vector((1, 0, 0))
        ws = [(R3 @ v.co) for v in f.verts]
        n = (R3 @ f.normal).normalized()
        t = n.cross(d).normalized() if n.cross(d).length > 1e-9 else d.orthogonal()
        width = max(p.dot(t) for p in ws) - min(p.dot(t) for p in ws)
        bevel_face[f.index] = width <= bevel_max
    if attr in me.color_attributes:
        me.color_attributes.remove(me.color_attributes[attr])
    bm.to_mesh(me)
    bm.free()
    ca = me.color_attributes.new(attr, "BYTE_COLOR", "CORNER")
    stats = {"bevel_faces": sum(bevel_face.values()), "faces": len(me.polygons)}
    for poly in me.polygons:
        g = 1.0 if bevel_face.get(poly.index) else 0.0
        for li in poly.loop_indices:
            vi = me.loops[li].vertex_index
            z = (Mw @ me.vertices[vi].co).z
            b = max(0.0, min(1.0, 1.0 - (z - gz) / dirt_h))
            ca.data[li].color = (occ[vi], g, b * b, 1.0)
    me.update()
    return stats


def texel_density(obj, set_name=None, uv_map="UVMap"):
    """Area-weighted px/cm percentiles (p5, p50, p95) of UV map uv_map. set_name=None: each face is measured with
    the texture set of its own material slot (the library tags materials with 'dj_set'); faces whose set has no
    metric tile (unit-UV panes, rope) are skipped."""
    me = obj.data
    uvl = me.uv_layers[uv_map].data
    S = obj.matrix_world.to_3x3()
    rows = []
    for p in me.polygons:
        sn = set_name
        if sn is None:
            m = me.materials[p.material_index] if p.material_index < len(me.materials) else None
            sn = m.get("dj_set") if m else None
        if not sn or not tg.SETS[sn]["tile_m"]:
            continue
        w, h = tg.SETS[sn]["size"]
        if len(p.loop_indices) < 3:
            continue
        li = list(p.loop_indices)
        a3 = 0.0
        a2 = 0.0
        v0 = S @ me.vertices[me.loops[li[0]].vertex_index].co
        t0 = uvl[li[0]].uv
        for i in range(1, len(li) - 1):
            v1 = S @ me.vertices[me.loops[li[i]].vertex_index].co
            v2 = S @ me.vertices[me.loops[li[i + 1]].vertex_index].co
            a3 += (v1 - v0).cross(v2 - v0).length / 2
            t1, t2 = uvl[li[i]].uv, uvl[li[i + 1]].uv
            a2 += abs((t1.x - t0.x) * (t2.y - t0.y) - (t2.x - t0.x) * (t1.y - t0.y)) / 2
        if a3 > 1e-10:
            rows.append((math.sqrt(a2 * w * h / (a3 * 1e4)), a3))
    rows.sort()
    tot = sum(a for _, a in rows)

    def pct(q):
        acc = 0.0
        for d, a in rows:
            acc += a
            if acc >= q * tot:
                return round(d, 3)
        return round(rows[-1][0], 3) if rows else None

    if not rows:
        return None
    return {"p5": pct(0.05), "p50": pct(0.5), "p95": pct(0.95)}


if __name__ == "__main__":
    # smoke test: build every material in an empty file
    for n in list_materials():
        make_material(n)
    print("DJ materials:", len(bpy.data.materials), "library", VERSION, os.fspath(TEX_DIR))
