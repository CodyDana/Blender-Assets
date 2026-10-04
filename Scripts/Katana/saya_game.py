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
import math
from pathlib import Path

import bpy
import bmesh
import numpy as np
from mathutils import Matrix

import saya_spec as S
from katana_game import make_game_material, _planes, mesh_vt, dense_samples

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


def analytic_skin_normals(me, cos_min=math.cos(math.radians(35.0)), tol=0.004):
    """Finaliser fix 2026-10-03 (craft review: lengthwise shading facets from the 48-sided section showed as stripes in
    the gloss lacquer). Every corner whose vertex lies on the analytic outer surface (superellipse section, concentric
    with the blade arc) and whose face normal is within 35 deg of the analytic normal gets the analytic normal as its
    custom normal; every other corner (rounds, groove walls, mouth face, kojiri cap, cavity, kurikata) keeps the
    normal Blender computed, so sharp edges stay sharp. Returns the count of corners set analytically."""
    nv = len(me.vertices)
    V = np.empty(nv * 3)
    me.vertices.foreach_get("co", V)
    V = V.reshape(-1, 3) * 1000.0
    V[:, 2] += S.Z_OFF                                  # saya frame -> sword frame
    s, rho, y = S.xyz_to_arc(V)
    sc = np.clip(s, S.S_MO, S.S_EN)
    t = (sc - S.S_MO) / (S.S_EN - S.S_MO)
    D = S.SY["depth_x"]["mouth"] + (S.SY["depth_x"]["kojiri_end"] - S.SY["depth_x"]["mouth"]) * t
    W = S.SY["width_y"]["mouth"] + (S.SY["width_y"]["kojiri_end"] - S.SY["width_y"]["mouth"]) * t
    a, b = D / 2, W / 2
    xr = (rho - (S.RHO_MUNE + a)) / a
    yr = y / b
    n = S.SE_N
    F = (np.abs(xr) ** n + np.abs(yr) ** n) ** (1.0 / n)
    on = (np.abs(F - 1.0) * np.minimum(a, b) < tol) & (s >= S.S_MO - 1e-6) & (s <= S.S_EN + 1e-6)
    gx = np.sign(xr) * np.abs(xr) ** (n - 1) / a
    gy = np.sign(yr) * np.abs(yr) ** (n - 1) / b
    gl = np.maximum(np.hypot(gx, gy), 1e-12)
    gx, gy = gx / gl, gy / gl
    ang = s / S.R
    radial = np.stack([-np.cos(ang), np.zeros_like(ang), np.sin(ang)], 1)
    N3 = gx[:, None] * radial + gy[:, None] * np.array([0.0, 1.0, 0.0])[None, :]
    nl = len(me.loops)
    lv = np.empty(nl, int)
    me.loops.foreach_get("vertex_index", lv)
    cn = np.empty(nl * 3)
    me.corner_normals.foreach_get("vector", cn)
    cn = cn.reshape(-1, 3)
    fn = np.empty(len(me.polygons) * 3)
    me.polygons.foreach_get("normal", fn)
    fn = fn.reshape(-1, 3)
    ls = np.empty(len(me.polygons), int)
    me.polygons.foreach_get("loop_start", ls)
    lt = np.empty(len(me.polygons), int)
    me.polygons.foreach_get("loop_total", lt)
    lpoly = np.repeat(np.arange(len(me.polygons)), lt)
    use = on[lv] & (np.sum(fn[lpoly] * N3[lv], axis=1) > cos_min)
    out = cn.copy()
    out[use] = N3[lv[use]]
    me.normals_split_custom_set([tuple(v) for v in out])
    me.update()
    return int(use.sum()), int(nl)


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
    part_mesh = {0: {}, 1: {}, 2: {}}
    for lv in (0, 1, 2):
        col = bpy.data.collections[f"LOD{lv}_parts"]
        parts = list(col.objects)
        for o in parts:
            o.data.transform(shift)
            part_mesh[lv][o["saya_part"]] = mesh_vt(o)
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
        n_an, n_lp = analytic_skin_normals(ob.data)
        log(f"LOD{lv}: analytic skin normals on {n_an} of {n_lp} corners")
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        gcol.objects.link(ob)
        bpy.data.collections.remove(col)
        lods.append(ob)
    for m in list(bpy.data.materials):
        if m.name.endswith("_placeholder") and m.users == 0:
            bpy.data.materials.remove(m)
    lod0 = lods[0]
    # ---- collision: the body in four chords along the arc, the kurikata. Finaliser fix 2026-10-03: the chords were
    # built from LOD0 VERTICES with a +-2 mm overlap, but the body's rings are 40 mm apart, so neighbouring hulls left
    # 17-30 mm gaps (12.5 % of the surface outside every hull). Each chord now takes DENSE SURFACE SAMPLES (<= 1 mm on
    # LOD0, <= 2 mm on LOD1/2) of the body within its arc range +- 3 mm; a finer, independent sampling gates the union.
    def samples(part, step0=1.0, step12=2.0):
        out = []
        for lv in (0, 1, 2):
            if part in part_mesh[lv]:
                V, T = part_mesh[lv][part]
                out.append(dense_samples(V, T, step0 if lv == 0 else step12))
        return np.vstack(out)
    Bd = samples("body")
    Bs = Bd.copy()
    Bs[:, 2] += S.Z_OFF
    sB, _, _ = S.xyz_to_arc(Bs)
    cuts = [S.S_MO - 1.0, 180.0, 360.0, 540.0, S.S_EN + 1.0]
    OVL = 3.0
    groups = []
    for i in range(4):
        lo = -1e9 if i == 0 else cuts[i] - OVL
        hi = 1e9 if i == 3 else cuts[i + 1] + OVL
        groups.append((f"body_{i}", Bd[(sB >= lo) & (sB <= hi)]))
    groups.append(("kurikata", samples("kurikata")))
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
        hv = np.array([v.co[:] for v in h.data.vertices]) * 1000.0
        hs = hv.copy()
        hs[:, 2] += S.Z_OFF
        sh_, _, _ = S.xyz_to_arc(hs)
        hull_info.append({"name": h.name, "group": gname, "vertices": len(h.data.vertices), "points": int(len(pts)),
                          "s_range_mm": [round(float(sh_.min()), 2), round(float(sh_.max()), 2)]})
    rng = np.random.default_rng(13)
    gate = [dense_samples(V, T, 0.5, rng) for (V, T) in part_mesh[0].values()]
    gate += [V for lv in (0, 1, 2) for (V, T) in part_mesh[lv].values()]
    allv = np.vstack(gate)
    inside_any = np.zeros(len(allv), bool)
    for h in hulls:
        d = np.max(np.stack([(allv / 1000.0) @ n - dd for n, dd in _planes(h.data)], 1), axis=1)
        inside_any |= d <= 1e-7
    n_out = int((~inside_any).sum())
    log("hulls", hull_info, f"gate: {len(allv)} surface samples + LOD vertices, outside every hull: {n_out}")
    if n_out:
        raise RuntimeError(f"collision gate: {n_out} surface samples outside every hull")
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
            "hulls": hull_info, "lod0_vertices_outside_hulls": n_out,
            "collision_gate": {"samples": int(len(allv)), "outside": n_out, "method": "LOD0 surface jittered <= 0.5 mm "
                               "+ all LOD vertices vs the union of the 5 hulls (plane test, 1e-4 mm)"}, "sockets": rec,
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
