"""Saya game assembly + export (called from build_saya.py stages game / export).

game:   one mesh per LOD (parts joined, triangulated = the baked tangent frame), moved into the SAYA FRAME (sword frame
        - (0, 0, 138.3): origin = BeltMount), the 2 slot materials as image-texture previews of the shipped maps,
        5 UCX hulls (KATANA_BUILD_PLAN.md 7.1: the body in four chords along the arc, koiguchi in 00 and kojiri in 03,
        and the kurikata), sockets as Empties (spec positions: BeltMount, Holster, Mouth, DrawPivot; zero rotation),
        LOD group -> Assets/Katana/Saya.blend
export: Scripts/pipeline export_fbx (LodGroup, sidecar with sockets + LOD screen sizes) + qa_check
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import bpy
import bmesh
import numpy as np
from mathutils import Matrix

import saya_spec as S
from katana_game import make_game_material, _planes

NAME = S.NAME


def log(*a):
    print("[SAYA]", *a, flush=True)


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _dirs18(frame):
    """18 outward plane normals (cube faces + the 12 edge diagonals) in a local frame (3 orthonormal columns)."""
    import itertools
    d = [np.array(v, float) for v in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))]
    for i, j in ((0, 1), (0, 2), (1, 2)):
        for a, b in itertools.product((1, -1), (1, -1)):
            v = np.zeros(3)
            v[i], v[j] = a, b
            d.append(v / np.linalg.norm(v))
    F = np.asarray(frame, float)
    return np.array([F @ v for v in d])


def _outer_hull(name, pts_m, frame, parent, coll, margin=0.0002):
    """Collision hull that CONTAINS every point by construction: the intersection of 18 half-spaces at the points'
    support (+ margin) in a frame aligned with the part (<= 32 vertices). Vertices by brute-force plane triples."""
    import itertools
    N = _dirs18(frame)
    h = (pts_m @ N.T).max(axis=0) + margin
    V = []
    for i, j, k in itertools.combinations(range(len(N)), 3):
        A = N[[i, j, k]]
        if abs(np.linalg.det(A)) < 1e-9:
            continue
        x = np.linalg.solve(A, h[[i, j, k]])
        if (N @ x - h <= 1e-9).all():
            V.append(x)
    V = np.unique(np.round(np.array(V), 9), axis=0)
    bm = bmesh.new()
    for p in V:
        bm.verts.new(p)
    bmesh.ops.convex_hull(bm, input=bm.verts[:])
    for v in list(bm.verts):
        if not v.link_faces:
            bm.verts.remove(v)
    bmesh.ops.dissolve_limit(bm, angle_limit=0.0005, verts=bm.verts[:], edges=bm.edges[:])
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    ob.parent = parent
    ob.hide_render = True
    ob.display_type = "WIRE"
    return ob


def make_game(WORK, TEX_DIR, GAME_BLEND):
    from pipeline.helpers import make_lod_group, make_socket
    for o in list(bpy.data.collections["BAKE_LOW"].objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(bpy.data.collections["BAKE_LOW"])
    for nm in S.SLOT_NAMES:
        old = bpy.data.materials.get(nm)
        if old is not None:
            old.name = old.name + "_placeholder"
    game_mats = [make_game_material(nm, S.TEX_STEM, TEX_DIR) for nm in S.SLOT_NAMES]
    gcol = bpy.data.collections.new(NAME)
    bpy.context.scene.collection.children.link(gcol)
    shift = Matrix.Translation((0.0, 0.0, -S.Z_OFF / 1000.0))
    lods, part_info = [], {}
    for lv in (0, 1, 2):
        col = bpy.data.collections[f"LOD{lv}_parts"]
        parts = list(col.objects)
        for o in parts:
            o.data.transform(shift)
            if lv == 0:
                part_info[o["saya_part"]] = np.array([v.co[:] for v in o.data.vertices]) * 1000.0
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
    # ---- collision: the body in four chords along the arc (+-2 mm overlap), the kurikata
    Bv = part_info["body"]
    Bs = Bv.copy()
    Bs[:, 2] += S.Z_OFF
    sB, _, _ = S.xyz_to_arc(Bs)
    cuts = [S.S_MO - 1.0, 180.0, 360.0, 540.0, S.S_EN + 1.0]
    groups = []
    for i in range(4):
        groups.append((f"body_{i}", Bv[(sB >= cuts[i] - 2.0) & (sB <= cuts[i + 1] + 2.0)]))
    groups.append(("kurikata", part_info["kurikata"]))
    allv = np.vstack(list(part_info.values()))
    hull_info, hulls = [], []
    for i, (gname, pts) in enumerate(groups):
        if gname == "kurikata":
            sk = S.KURI["s_centre"]
            frame = np.c_[S.tangent(sk), S.radial(sk), [0.0, 1.0, 0.0]]
        else:
            sm = 0.5 * (max(cuts[i], S.S_MO) + min(cuts[i + 1], S.S_EN))
            frame = np.c_[S.radial(sm), [0.0, 1.0, 0.0], S.tangent(sm)]
        h = _outer_hull(f"UCX_{NAME}_{i:02d}", pts / 1000.0, frame, lod0, gcol)
        h["ue_collision"] = "UCX"
        hulls.append(h)
        hull_info.append({"name": h.name, "group": gname, "vertices": len(h.data.vertices)})
    inside_any = np.zeros(len(allv), bool)
    for h in hulls:
        ok = np.ones(len(allv), bool)
        for n, d in _planes(h.data):
            ok &= (allv / 1000.0) @ n - d <= 1e-7
        inside_any |= ok
    log("hulls", hull_info, "LOD0 vertices outside every hull:", int((~inside_any).sum()))
    # ---- sockets (saya frame, zero rotation)
    rec = {}
    for sname, (x, y, z) in S.sockets_saya_mm().items():
        make_socket(lod0, sname, (x / 1000.0, y / 1000.0, z / 1000.0), rotation_euler=(0.0, 0.0, 0.0))
        rec[sname] = {"mm": [x, y, z], "rotation_deg": [0.0, 0.0, 0.0]}
    make_lod_group(NAME, lods)
    bpy.context.scene["saya_lod_screen_sizes"] = list(S.LOD_SCREEN_SIZES)
    bpy.context.scene["saya_axis"] = ("saya frame = the seated katana's frame - (0, 0, 138.3 mm): origin BeltMount, "
                                      "+Z toward the kojiri along the mouth's tangent, +X mune, -Y omote; mm/1000")
    GAME_BLEND.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(GAME_BLEND))
    info = {"lod_objects": [o.name for o in lods], "lod_triangles": [len(o.data.polygons) for o in lods],
            "hulls": hull_info, "lod0_vertices_outside_hulls": int((~inside_any).sum()), "sockets": rec,
            "game_blend": str(GAME_BLEND)}
    json.dump(info, open(WORK / "game_report.json", "w"), indent=1)
    log("game", json.dumps(info)[:2000])


def export(WORK, EXPORT_DIR):
    from pipeline.export_fbx import export_fbx
    from pipeline.qa_check import qa_check
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    fbx = EXPORT_DIR / f"{NAME}.fbx"
    grp = bpy.data.objects[f"{NAME}_LodGroup"]
    res = export_fbx(str(fbx), [grp], kind="static", lod_screen_sizes=list(S.LOD_SCREEN_SIZES))
    log("export", json.dumps({k: res.get(k) for k in ("objects", "warnings", "sidecar", "lod_screen_sizes")}, default=str))
    objs = [f"{NAME}_LOD0", f"{NAME}_LOD1", f"{NAME}_LOD2"]
    qa = qa_check(objs, budget_tris=12000, texel_density=None, require_uv1=True)
    fails = [c for c in qa["checks"] if not c["passed"]]
    lod0 = bpy.data.objects[f"{NAME}_LOD0"]
    V = np.array([v.co[:] for v in lod0.data.vertices]) * 1000.0
    hulls = sorted(c.name for c in lod0.children if c.name.startswith("UCX_"))
    socks = sorted(c.name for c in lod0.children if c.name.startswith("SOCKET_"))
    geo = json.load(open(WORK / "geo_report.json"))
    game = json.load(open(WORK / "game_report.json"))
    tex = sorted((EXPORT_DIR / "Textures").glob(f"{S.TEX_STEM}_*.png"))
    rep = {"asset": NAME, "fbx": str(fbx), "sidecar": res.get("sidecar"),
           "lod_triangles": [qa["triangles"][o] for o in objs], "lod_screen_sizes": list(S.LOD_SCREEN_SIZES),
           "bbox_min_mm": V.min(axis=0).round(3).tolist(), "bbox_max_mm": V.max(axis=0).round(3).tolist(),
           "collision": {"hulls": hulls, "hull_vertices": {h: len(bpy.data.objects[h].data.vertices) for h in hulls},
                         "lod0_vertices_outside_hulls": game["lod0_vertices_outside_hulls"]},
           "sockets": socks, "sockets_mm": game["sockets"],
           "material_slots": [m.name for m in lod0.data.materials],
           "texel_px_per_cm": {"saya_atlas_base": geo["px_per_cm"]},
           "sha256": {"fbx": sha256(fbx), "sidecar": sha256(res["sidecar"]) if res.get("sidecar") else None,
                      **{p.name: sha256(p) for p in tex}},
           "katana_fbx_sha256": sha256(S.KATANA_FBX),
           "qa": {"passed": qa["passed"], "checks": len(qa["checks"]), "fails": fails},
           "frame": "mm, saya frame = the seated katana's frame - (0, 0, 138.3); origin BeltMount; +X mune, -Y omote"}
    json.dump(rep, open(WORK.parent / "saya_report.json", "w"), indent=1, default=str)
    json.dump(qa, open(WORK / "qa_saya.json", "w"), indent=1, default=str)
    log("qa passed", qa["passed"], "checks", len(qa["checks"]), "fails", json.dumps(fails)[:3000])
