"""Katana game assembly + export (called from build_katana.py stages game / export).

game:   one mesh per LOD (parts joined, triangulated = the baked tangent frame), the 3 slot materials as image-texture
        previews of the shipped maps, 6 UCX hulls (KATANA_BUILD_PLAN.md 7.1: habaki + blade 0-25 %, 25-50 %,
        50-80 %, 80 %-tip, seppa + tsuba, tsuka), sockets as Empties (spec positions; BladeTip pitched along the tip
        tangent; CenterOfMass from part volumes x densities), LOD group -> Assets/Katana/Katana.blend
export: Scripts/pipeline export_fbx (LodGroup, sidecar with sockets + LOD screen sizes) + qa_check
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
import bmesh
import numpy as np
from mathutils import Vector

import katana_spec as K

NAME = K.NAME


def log(*a):
    print("[KAT]", *a, flush=True)


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ====================================================================== materials
def make_game_material(name, stem, tex_dir):
    m = bpy.data.materials.new(name)
    if m.node_tree is None or not any(n.type == "BSDF_PRINCIPLED" for n in m.node_tree.nodes):
        m.use_nodes = True
    nt = m.node_tree
    bs = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UV0"

    def img(suffix, cs):
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(str(tex_dir / f"{stem}_{suffix}.png"), check_existing=True)
        t.image.colorspace_settings.name = cs
        nt.links.new(uv.outputs["UV"], t.inputs["Vector"])
        return t
    tbc, torm, tn = img("BC", "sRGB"), img("ORM", "Non-Color"), img("N", "Non-Color")
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(torm.outputs["Color"], sep.inputs["Color"])
    nt.links.new(tbc.outputs["Color"], bs.inputs["Base Color"])
    nt.links.new(sep.outputs["Green"], bs.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], bs.inputs["Metallic"])
    nsep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(tn.outputs["Color"], nsep.inputs["Color"])
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    nt.links.new(nsep.outputs["Green"], inv.inputs[1])
    ncomb = nt.nodes.new("ShaderNodeCombineColor")
    nt.links.new(nsep.outputs["Red"], ncomb.inputs["Red"])
    nt.links.new(inv.outputs[0], ncomb.inputs["Green"])
    nt.links.new(nsep.outputs["Blue"], ncomb.inputs["Blue"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.uv_map = "UV0"
    nt.links.new(ncomb.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bs.inputs["Normal"])
    # AO preview (Unreal applies AO to indirect light only): a gentle multiply on the base colour
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 1.0
    aoc = nt.nodes.new("ShaderNodeMapRange")
    aoc.inputs["To Min"].default_value = 0.55
    nt.links.new(sep.outputs["Red"], aoc.inputs["Value"])
    a_in = next(s_ for s_ in mix.inputs if s_.name == "A" and s_.type == "RGBA")
    b_in = next(s_ for s_ in mix.inputs if s_.name == "B" and s_.type == "RGBA")
    r_out = next(s_ for s_ in mix.outputs if s_.name == "Result" and s_.type == "RGBA")
    nt.links.new(tbc.outputs["Color"], a_in)
    nt.links.new(aoc.outputs["Result"], b_in)
    nt.links.new(r_out, bs.inputs["Base Color"])
    return m


# ====================================================================== mass properties
def mass_properties(parts0):
    """Point of balance from part volumes x densities (g/cm3: steel/iron 7.85, brass 8.5, ho wood 0.45, ray skin
    1.1, cotton/silk ito 0.7). The nakago (tang) is not modelled (it is inside the tsuka); a typical one is added as a
    virtual steel volume (z 58 -> -160, 29 -> 21 mm wide, 6.5 -> 5.0 thick) so the balance is physical."""
    items = []
    # blade: section areas along the arc
    st = np.linspace(0, K.S_TIP - 0.5, 400)
    for s0, s1 in zip(st[:-1], st[1:]):
        s = 0.5 * (s0 + s1)
        sec, _ = K.blade_section_uv(s, 0)
        pts = [(u, y) for u, y, V in sec] + [(sec[j][0], -sec[j][1]) for j in range(len(sec) - 2, 0, -1)]
        pts = np.array(pts)
        area = 0.5 * abs(np.dot(pts[:, 0], np.roll(pts[:, 1], -1)) - np.dot(pts[:, 1], np.roll(pts[:, 0], -1)))
        uc = float(pts[:, 0].mean())
        x, y, z = K.blade_xyz(s, uc, 0.0)
        items.append(("blade", area * (s1 - s0), 7.85, (x, 0.0, z)))
    for z0 in np.linspace(-160, 58, 60)[:-1]:
        dz = 218 / 59
        t = (58 - z0) / 218
        items.append(("nakago (virtual)", (29 - 8 * t) * (6.5 - 1.5 * t) * 0.85 * dz, 7.85, (0.0, 0.0, z0 + dz / 2)))
    hb = K.SP["habaki"]
    items.append(("habaki", (34.4 * 11.0 * 0.86 - 31 * 6.5 * 0.6) * 28, 8.5, (0.25, 0.0, 72.0)))
    se = K.SP["seppa"]["outline"]
    a_se = math.pi * se["depth_x"] / 2 * se["width_y"] / 2 * 1.08 - 31 * 6.5
    items.append(("seppa x2", 2 * a_se * 1.5, 8.5, (0.0, 0.0, 54.0)))
    items.append(("tsuba", (math.pi * 38 ** 2 - 31 * 6.5) * 5.0, 7.85, (0.0, 0.0, 54.0)))
    items.append(("fuchi", (2 * (38 + 26.7) * 1.1 * 13 * 0.8 + 38 * 26.7 * 0.8 * 1.0), 7.85, (0.0, 0.0, 44.0)))
    items.append(("kashira", 2 * (35 + 24.6) * 1.1 * 11 * 1.2 + 35 * 24.6 * 0.8 * 1.5, 7.85, (1.1, 0.0, -210.0)))
    wood = 0.0
    for z in np.linspace(-204, 37, 50):
        cx, a, b = K.core_axes(z)
        wood += math.pi * a * b * 1.06 * (241 / 50)
    items.append(("tsuka wood (ho)", wood - 23 * 5.5 * 0.85 * 197, 0.45, (0.4, 0.0, -83.0)))
    items.append(("same", 2 * (33 + 22) * 1.1 * 241 * 1.0, 1.1, (0.4, 0.0, -83.0)))
    items.append(("ito", 2 * 950 * 9.0 * 1.3, 0.7, (0.4, 0.0, -83.0)))
    items.append(("menuki x2", 2 * 30 * 10 * 3.2 * 0.45, 8.5, (0.0, 0.0, -83.5)))
    m_tot = 0.0
    c = np.zeros(3)
    rows = {}
    for name, vol, rho, pos in items:
        m = vol * rho / 1000.0       # g
        m_tot += m
        c += m * np.array(pos)
        rows[name] = rows.get(name, 0.0) + m
    c /= m_tot
    return {"mass_g": round(m_tot, 1), "com_mm": [round(float(v), 2) for v in c],
            "parts_g": {k: round(v, 1) for k, v in rows.items()},
            "balance_from_tsuba_mm": round(float(c[2]) - 56.8, 1)}


# ====================================================================== hulls
def _hull_from_points(name, pts_m, parent, coll, max_verts=32):
    from pipeline.helpers import apply_modifier, _hull_only
    bm = bmesh.new()
    for p in pts_m:
        bm.verts.new(p)
    bmesh.ops.convex_hull(bm, input=bm.verts[:])
    for v in list(bm.verts):
        if not v.link_faces:
            bm.verts.remove(v)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    h = bpy.data.objects.new(name, me)
    coll.objects.link(h)
    h.parent = parent
    for _ in range(25):
        if len(h.data.vertices) <= max_verts:
            break
        mod = h.modifiers.new("dec", "DECIMATE")
        mod.decimate_type = "COLLAPSE"
        mod.ratio = max(0.1, (max_verts * 1.6) / max(len(h.data.polygons), 1))
        apply_modifier(h, mod)
        b2 = bmesh.new()
        b2.from_mesh(h.data)
        _hull_only(b2)
        b2.to_mesh(h.data)
        b2.free()
    _grow_hull_to_contain(h, np.asarray(pts_m))
    h.data.materials.clear()
    h.hide_render = True
    h.display_type = "WIRE"
    return h


def _planes(me):
    b = bmesh.new()
    b.from_mesh(me)
    b.faces.ensure_lookup_table()
    pl = [(np.array(f.normal[:]), float(np.dot(np.array(f.normal[:]), np.array(f.verts[0].co[:])))) for f in b.faces]
    b.free()
    return pl


def _grow_hull_to_contain(h, pts, margin=0.00015):
    """Push each hull vertex outward along the worst plane violations: scale about the centroid per axis until
    every point is inside (the Snow Flower method, applied per axis so thin blade hulls stay thin)."""
    me = h.data
    for _ in range(60):
        pl = _planes(me)
        worst = 0.0
        for n, d in pl:
            worst = max(worst, float((pts @ n - d).max()))
        if worst <= 0.0:
            return
        V = np.array([v.co[:] for v in me.vertices])
        c = V.mean(axis=0)
        ext = np.maximum(np.abs(V - c).max(axis=0), 1e-5)
        k = 1.0 + (worst + margin) / ext
        for v in me.vertices:
            v.co = Vector(c + (np.array(v.co[:]) - c) * k)
    raise RuntimeError(f"{h.name}: hull could not be grown to contain its vertices")


def blade_s_of(x, z):
    a = np.arctan2(z - K.CZ, K.CX - x)
    return a * K.R


# ====================================================================== game
def make_game(WORK, TEX_DIR, GAME_BLEND):
    from pipeline.helpers import make_lod_group, make_socket
    for o in list(bpy.data.collections["BAKE_LOW"].objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(bpy.data.collections["BAKE_LOW"])
    for nm in K.SLOT_NAMES:
        old = bpy.data.materials.get(nm)
        if old is not None:
            old.name = old.name + "_placeholder"
    game_mats = [make_game_material(nm, K.SLOT_TEX[nm], TEX_DIR) for nm in K.SLOT_NAMES]
    gcol = bpy.data.collections.new(NAME)
    bpy.context.scene.collection.children.link(gcol)
    lods = []
    part_info = {}
    for lv in (0, 1, 2):
        col = bpy.data.collections[f"LOD{lv}_parts"]
        parts = list(col.objects)
        if lv == 0:
            for o in parts:
                part_info[o["kat_part"]] = np.array([v.co[:] for v in o.data.vertices]) * 1000.0
        for o in parts:
            for k, gm in enumerate(game_mats):
                o.data.materials[k] = gm
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        for o in parts:
            o.select_set(True)
        bpy.context.view_layer.objects.active = parts[0]
        bpy.ops.object.join()
        ob = parts[0]
        ob.name = NAME if lv == 0 else f"{NAME}_LOD{lv}"
        ob.data.name = ob.name
        for k in list(ob.keys()):
            del ob[k]
        b = bmesh.new()
        b.from_mesh(ob.data)
        bmesh.ops.triangulate(b, faces=b.faces[:], quad_method="BEAUTY", ngon_method="BEAUTY")
        b.to_mesh(ob.data)
        b.free()
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        gcol.objects.link(ob)
        bpy.data.collections.remove(col)
        lods.append(ob)
    for m in list(bpy.data.materials):
        if m.name.endswith("_placeholder") and m.users == 0:
            bpy.data.materials.remove(m)
    lod0 = lods[0]
    # ---- collision (plan 7.1): 6 hulls
    Bv = part_info["blade"]
    sB = blade_s_of(Bv[:, 0], Bv[:, 2])
    S = K.S_TIP
    cuts = [0.0, 0.25 * S, 0.50 * S, 0.80 * S, S + 1]
    groups = []
    for i in range(4):
        sel = Bv[(sB >= cuts[i] - 2.0) & (sB <= cuts[i + 1] + 2.0)]
        if i == 0:
            sel = np.vstack([sel, part_info["habaki"]])
        groups.append((f"blade_{i}", sel))
    groups.append(("tsuba_seppa", np.vstack([part_info["tsuba"], part_info["seppa_blade"], part_info["seppa_tsuka"]])))
    tsuka = np.vstack([part_info[p] for p in ("fuchi", "kashira", "core", "cords", "menuki", "mekugi", "band", "eyelets")])
    groups.append(("tsuka", tsuka))
    allv = np.vstack(list(part_info.values()))
    hull_info = []
    hulls = []
    for i, (gname, pts) in enumerate(groups):
        h = _hull_from_points(f"UCX_{NAME}_{i:02d}", pts / 1000.0, lod0, gcol)
        h["ue_collision"] = "UCX"
        hulls.append(h)
        hull_info.append({"name": h.name, "group": gname, "vertices": len(h.data.vertices)})
    # every LOD0 vertex inside at least one hull
    inside_any = np.zeros(len(allv), bool)
    for h in hulls:
        pl = _planes(h.data)
        ok = np.ones(len(allv), bool)
        for n, d in pl:
            ok &= (allv / 1000.0) @ n - d <= 1e-7
        inside_any |= ok
    log("hulls", hull_info, "LOD0 vertices outside every hull:", int((~inside_any).sum()))
    # ---- sockets
    mp = mass_properties(part_info)
    socks = dict(K.socket_positions())
    socks["CenterOfMass"] = tuple(mp["com_mm"])
    rec = {}
    for sname, (x, y, z) in socks.items():
        rot = (0.0, math.radians(K.TIP_PITCH_DEG), 0.0) if sname == "BladeTip" else (0.0, 0.0, 0.0)
        make_socket(lod0, sname, (x / 1000.0, y / 1000.0, z / 1000.0), rotation_euler=rot)
        rec[sname] = {"mm": [x, y, z], "rotation_deg": [math.degrees(r) for r in rot]}
    grp = make_lod_group(NAME, lods)
    bpy.context.scene["kat_lod_screen_sizes"] = list(K.LOD_SCREEN_SIZES)
    bpy.context.scene["kat_axis"] = "+Z blade (tsuka axis), +X mune, -Y omote; origin = Grip socket; mm/1000"
    GAME_BLEND.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(GAME_BLEND))
    info = {"lod_objects": [o.name for o in lods],
            "lod_triangles": [len(o.data.polygons) for o in lods],
            "hulls": hull_info, "lod0_vertices_outside_hulls": int((~inside_any).sum()),
            "sockets": rec, "mass": mp, "game_blend": str(GAME_BLEND)}
    json.dump(info, open(WORK / "game_report.json", "w"), indent=1)
    log("game", json.dumps(info)[:2500])


# ====================================================================== export
def export(WORK, EXPORT_DIR):
    from pipeline.export_fbx import export_fbx
    from pipeline.qa_check import qa_check
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    fbx = EXPORT_DIR / f"{NAME}.fbx"
    grp = bpy.data.objects[f"{NAME}_LodGroup"]
    res = export_fbx(str(fbx), [grp], kind="static", lod_screen_sizes=list(K.LOD_SCREEN_SIZES))
    log("export", json.dumps({k: res.get(k) for k in ("objects", "warnings", "sidecar", "lod_screen_sizes")}, default=str))
    objs = [f"{NAME}_LOD0", f"{NAME}_LOD1", f"{NAME}_LOD2"]
    qa = qa_check(objs, budget_tris=25000, texel_density=None, require_uv1=True)
    fails = [c for c in qa["checks"] if not c["passed"]]
    lod0 = bpy.data.objects[f"{NAME}_LOD0"]
    V = np.array([v.co[:] for v in lod0.data.vertices]) * 1000.0
    hulls = sorted(c.name for c in lod0.children if c.name.startswith("UCX_"))
    socks = sorted(c.name for c in lod0.children if c.name.startswith("SOCKET_"))
    geo = json.load(open(WORK / "geo_report.json"))
    game = json.load(open(WORK / "game_report.json"))
    tex = sorted((EXPORT_DIR / "Textures").glob("*.png"))
    rep = {"asset": NAME, "fbx": str(fbx), "sidecar": res.get("sidecar"),
           "lod_triangles": [qa["triangles"][o] for o in objs], "lod_screen_sizes": list(K.LOD_SCREEN_SIZES),
           "bbox_min_mm": V.min(axis=0).round(3).tolist(), "bbox_max_mm": V.max(axis=0).round(3).tolist(),
           "collision": {"hulls": hulls, "hull_vertices": {h: len(bpy.data.objects[h].data.vertices) for h in hulls},
                         "lod0_vertices_outside_hulls": game["lod0_vertices_outside_hulls"]},
           "sockets": socks, "sockets_mm": game["sockets"], "mass": game["mass"],
           "material_slots": [m.name for m in lod0.data.materials],
           "texel_px_per_cm": {"steel_atlas_base": geo["steel_px_per_cm"], "grip_atlas_base": geo["grip_px_per_cm"]},
           "sha256": {"fbx": sha256(fbx), "sidecar": sha256(res["sidecar"]) if res.get("sidecar") else None,
                      **{p.name: sha256(p) for p in tex}},
           "qa": {"passed": qa["passed"], "checks": len(qa["checks"]), "fails": fails},
           "frame": "mm, +Z blade along the tsuka axis, +X mune, -Y omote; origin = Grip socket"}
    json.dump(rep, open(WORK.parent / "katana_report.json", "w"), indent=1, default=str)
    json.dump(qa, open(WORK / "qa_katana.json", "w"), indent=1, default=str)
    log("qa passed", qa["passed"], "checks", len(qa["checks"]), "fails", json.dumps(fails)[:3000])
