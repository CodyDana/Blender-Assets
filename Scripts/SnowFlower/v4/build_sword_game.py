"""Snow Flower v4 sword build (headless Blender 5.2).

    blender -b --factory-startup --python Scripts/SnowFlower/v4/build_sword_game.py -- --stage <stage>

Stages (each its own process, in order):
    geo     build high-poly + LOD0/1/2, pack the atlases, save the work blend
    bake    bake NORMAL / AO / BC / ROUGH / METAL per part into float arrays (--channels to limit)
    maps    compose the shipped PNGs (DirectX normals, ORM, sRGB BC, wrap Detail)
    game    join LODs, game materials, UCX hulls, sockets, LOD group -> Assets/SnowFlower/SnowFlower_Game_v4.blend
            (+ the v4 high-poly -> WorkFiles/SnowFlower/v4/SnowFlower_HighPoly_v4.blend)
    export  Scripts/pipeline/export_fbx.py + qa_check -> Exports/SnowFlower/v4/
Revision-3 files are never opened for writing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "Scripts"))

import bpy  # noqa: E402
import numpy as np  # noqa: E402

import sfv4_assemble as A  # noqa: E402
import sfv4_bake as BK  # noqa: E402
import sfv4_look as LK  # noqa: E402
import sfv4_png as PNG  # noqa: E402
import sfv4_spec as S  # noqa: E402
import sfv4_uvpack as UP  # noqa: E402
import sfv4_blade as BL  # noqa: E402

WORK = ROOT / "WorkFiles" / "SnowFlower" / "v4" / "sword_build"
BAKE_DIR = WORK / "bake"
WORK_BLEND = WORK / "SF4_work.blend"
HIGH_BLEND = ROOT / "WorkFiles" / "SnowFlower" / "v4" / "SnowFlower_HighPoly_v4.blend"
GAME_BLEND = ROOT / "Assets" / "SnowFlower" / "SnowFlower_Game_v4.blend"
EXPORT_DIR = ROOT / "Exports" / "SnowFlower" / "v4"
TEX_DIR = EXPORT_DIR / "Textures"
NAME = "SM_SnowFlower"
FORBIDDEN = [ROOT / "Assets" / "SnowFlower" / "SnowFlower_Master.blend",
             ROOT / "Assets" / "SnowFlower" / "SnowFlower_Game.blend"]
WRAP_PARTS = ("grip",)


def log(*a):
    print("[SF4]", *a, flush=True)


def guard_paths(*paths):
    for p in paths:
        for f in FORBIDDEN:
            if Path(p).resolve() == f.resolve():
                raise RuntimeError(f"refusing to write revision-3 file {f}")


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def new_collection(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c


# ====================================================================== stage geo

def stage_geo():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    t0 = time.time()
    lows = {lv: A.build_low(lv) for lv in (0, 1, 2)}
    log("low tris", {lv: sum(m.tri_count() for m in d.values()) for lv, d in lows.items()})
    # ---- atlases: union of island coordinates over the LODs
    steel_isl, wrap_isl = {}, {}
    for lv, d in lows.items():
        for part, mb in d.items():
            tgt = wrap_isl if part in WRAP_PARTS else steel_isl
            for k, pts in mb.islands().items():
                tgt[k] = np.vstack([tgt[k], pts]) if k in tgt else pts
    steel = UP.pack(steel_isl, S.STEEL_MAP, S.PAD_PX // 2, 0.0)
    wrap = UP.pack(wrap_isl, S.WRAP_MAP, S.PAD_PX // 2, 1.0)
    allisl = dict(steel_isl)
    allisl.update(wrap_isl)
    lm = UP.pack(allisl, 1024, 3, 0.0)
    WORK.mkdir(parents=True, exist_ok=True)
    UP.save(steel, WORK / "atlas_steel.json")
    UP.save(wrap, WORK / "atlas_wrap.json")
    UP.save(lm, WORK / "atlas_lightmap.json")
    log(f"steel atlas {steel.density * 10:.1f} px/cm cover {UP.coverage_fraction(steel):.2f}; "
        f"wrap {wrap.density * 10:.1f} px/cm cover {UP.coverage_fraction(wrap):.2f}; islands {len(steel_isl)}+{len(wrap_isl)}")

    def uvt(island, uv):
        return (wrap if island in wrap_isl else steel).transform(island, uv)

    def uv1(island, uv):
        return lm.transform(island, uv)

    def uvt_bake(island, uv):
        out = uvt(island, uv)
        if island in wrap_isl:
            out = out.copy()
            out[:, 0] -= 1.0     # bake images are 0..1; the shipped UV0 keeps the wrap in tile U 1..2
        return out

    slot_mats = [bpy.data.materials.new(n) for n in S.SLOT_NAMES]      # blade / fittings / grip (final pass)
    # ---- game-level part objects (UV0 atlas + UV1 lightmap)
    for lv, d in lows.items():
        col = new_collection(f"LOD{lv}_parts")
        for part, mb in d.items():
            ob = mb.to_object(f"SF4_L{lv}_{part}", col, materials=slot_mats, uv_transform=uvt,
                              uv1_transform=uv1)
            ob["sf4_part"] = part
            ob["sf4_level"] = lv
    # ---- bake-low (LOD0 parts) with a bake target material
    col = new_collection("BAKE_LOW")
    for part, mb in lows[0].items():
        size = S.WRAP_MAP if part in WRAP_PARTS else S.STEEL_MAP
        bm = bpy.data.materials.new(f"BAKE_{part}")
        bm.use_nodes = True
        n = bm.node_tree.nodes.new("ShaderNodeTexImage")
        n.name = "bake_target"
        ob = mb.to_object(f"SF4_BAKE_{part}", col, materials=[bm, bm, bm], uv_transform=uvt_bake)
        me = ob.data
        # triangulate so the baked tangent frame equals the exported (triangulated) one
        import bmesh
        b = bmesh.new()
        b.from_mesh(me)
        bmesh.ops.triangulate(b, faces=b.faces[:], quad_method="BEAUTY", ngon_method="BEAUTY")
        b.to_mesh(me)
        b.free()
        ob["sf4_part"] = part
        ob["sf4_atlas"] = "wrap" if part in WRAP_PARTS else "steel"
        ob.visible_diffuse = ob.visible_glossy = ob.visible_shadow = ob.visible_transmission = False
    # ---- high poly
    L = BL.relief_layout(-1)
    Lb = BL.relief_layout(1)
    bc, rough, meta = LK.paint_blade_pattern(L["samples"], Lb["samples"])
    np.save(WORK / "pattern_bc.npy", bc.astype(np.float32))
    np.save(WORK / "pattern_rough.npy", rough.astype(np.float32))
    img_bc = bpy.data.images.new("SF4_PATTERN_BC", meta["W"], meta["H"], float_buffer=True, is_data=True)
    img_bc.pixels.foreach_set(np.concatenate([bc, np.ones(bc.shape[:2] + (1,))], -1).astype(np.float32).ravel())
    img_bc.pack()
    img_r = bpy.data.images.new("SF4_PATTERN_ROUGH", meta["W"], meta["H"], float_buffer=True, is_data=True)
    img_r.pixels.foreach_set(np.stack([rough] * 3 + [np.ones_like(rough)], -1).astype(np.float32).ravel())
    img_r.pack()
    hmats = LK.make_high_materials(img_bc, img_r, metal_bump=(0.03, 0.12))
    high = A.build_high()
    col = new_collection("HIGH")
    ht = 0
    for part, d in high.items():
        for mkey, mb in d.items():
            if not mb.faces:
                continue
            ht += mb.tri_count()
            ob = mb.to_object(f"SF4_H_{part}_{mkey}", col, materials=hmats, recalc=True, smooth_angle=50.0)
            ob["sf4_part"] = part
    log("high tris", ht, f"{time.time() - t0:.1f}s")
    json.dump({"low_tris": {lv: {p: m.tri_count() for p, m in d.items()} for lv, d in lows.items()},
               "high_tris": ht, "steel_px_per_cm": steel.density * 10, "wrap_px_per_cm": wrap.density * 10,
               "steel_cover": UP.coverage_fraction(steel), "wrap_cover": UP.coverage_fraction(wrap)},
              open(WORK / "geo_report.json", "w"), indent=1)
    bpy.ops.wm.save_as_mainfile(filepath=str(WORK_BLEND))
    log("saved", WORK_BLEND)


# ====================================================================== stage bake

def stage_bake(channels, parts=None):
    """``parts`` (final pass 2026-09-27): re-bake only these bake groups into the EXISTING channel arrays (the other
    parts' texels are kept); None = every part from scratch."""
    bpy.ops.wm.open_mainfile(filepath=str(WORK_BLEND))
    dev = BK.setup_cycles()
    log("device", dev)
    sc = bpy.context.scene
    if sc.world is None:
        sc.world = bpy.data.worlds.new("bake_world")
    sc.world.light_settings.distance = 0.012
    hmats = [bpy.data.materials[f"SF4H_{n[0]}"] for n in LK.HIGH_MATERIALS]
    lows = [o for o in bpy.data.collections["BAKE_LOW"].objects]
    highs = list(bpy.data.collections["HIGH"].objects)
    # hide the game-level objects from every ray
    for c in bpy.data.collections:
        if c.name.startswith("LOD"):
            for o in c.objects:
                o.hide_render = True
    BAKE_DIR.mkdir(parents=True, exist_ok=True)
    for ch in channels:
        t = time.time()
        if ch in ("BC", "ROUGH", "METAL"):
            LK.set_bake_channel(hmats, ch)
            btype, samples = "EMIT", 4
        elif ch == "AO":
            LK.set_bake_channel(hmats, "SHADED")
            btype, samples = "AO", 48
        else:
            LK.set_bake_channel(hmats, "SHADED")
            btype, samples = "NORMAL", 8
        for atlas, size in (("steel", S.STEEL_MAP), ("wrap", S.WRAP_MAP)):
            acc = np.zeros((size, size, 3), np.float32)
            cov = np.zeros((size, size), bool)
            if parts:
                if not (BAKE_DIR / f"{atlas}_{ch}.npy").exists():
                    continue
                acc = np.load(BAKE_DIR / f"{atlas}_{ch}.npy")
                cov = np.load(BAKE_DIR / f"{atlas}_cov.npy")
            for low in lows:
                if low["sf4_atlas"] != atlas:
                    continue
                part = low["sf4_part"]
                if parts and part not in parts:
                    continue
                if ch == "METAL" and atlas == "wrap":
                    continue
                hs = [h for h in highs if h["sf4_part"] in A.HIGH_FOR[part]]
                for o in lows:
                    o.hide_render = o is not low
                px = BK.bake_part(low, hs, btype, size, A.CAGE_MM[part], samples)
                tris = BK.uv_triangles_px(low, size, 0.0)
                m = BK.rasterize(tris, size, dilate=1)
                acc[m] = px[..., :3][m]
                cov |= m
            if cov.any():
                np.save(BAKE_DIR / f"{atlas}_{ch}.npy", acc)
                np.save(BAKE_DIR / f"{atlas}_cov.npy", cov)
        log(f"channel {ch} done {time.time() - t:.1f}s")


# ====================================================================== stage maps

def lin2srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def stage_maps():
    TEX_DIR.mkdir(parents=True, exist_ok=True)
    report = {}
    for atlas, stem in (("steel", "T_SnowFlower_Steel"), ("wrap", "T_SnowFlower_Wrap")):
        cov = np.load(BAKE_DIR / f"{atlas}_cov.npy")
        ld = lambda ch: np.load(BAKE_DIR / f"{atlas}_{ch}.npy")
        nrm = BK.edge_extend(ld("NORMAL"), cov)
        nrm[..., 1] = 1.0 - nrm[..., 1]                     # OpenGL -> DirectX
        ao = BK.edge_extend(ld("AO"), cov)[..., 0]
        bc = BK.edge_extend(ld("BC"), cov)
        rough = BK.edge_extend(ld("ROUGH"), cov)[..., 0]
        metal = BK.edge_extend(ld("METAL"), cov)[..., 0] if atlas == "steel" else np.zeros_like(ao)
        if atlas == "steel":
            # look-match R1: ANTIQUED silver - the sheet's fittings are bright on the raised faces and dark in every
            # recess; bake a mild cavity darkening into the metal albedo (Unreal's AO only touches indirect light)
            bc = bc * (0.72 + 0.28 * np.clip(ao, 0, 1))[..., None]
        # rows: Blender pixel row 0 is the bottom (v=0); PNG row 0 is the top
        flip = lambda a: a[::-1]
        PNG.write_png(TEX_DIR / f"{stem}_BC.png", flip(lin2srgb(bc)))
        PNG.write_png(TEX_DIR / f"{stem}_ORM.png", flip(np.stack([ao, rough, metal], -1)))
        PNG.write_png(TEX_DIR / f"{stem}_N.png", flip(np.clip(nrm, 0, 1)))
        info = {"size": int(cov.shape[0]), "coverage": float(cov.mean()),
                "bc_mean_linear": [float(v) for v in bc[cov].mean(axis=0)],
                "ao_mean": float(ao[cov].mean()), "rough_mean": float(rough[cov].mean()),
                "metal_mean": float(metal[cov].mean())}
        if atlas == "wrap":
            lum = bc @ np.array([0.2126, 0.7152, 0.0722])
            lo, hi = np.percentile(lum[cov], [0.1, 99.9])
            d = np.clip((lum - lo) / max(hi - lo, 1e-6), 0, 1)
            # final pass: the Detail ships at S.WRAP_DETAIL_MAP (1024): a coverage-weighted 2x2 box of the linear d,
            # then the same pull-push padding (a 2048 G16 Detail16 in Unreal would cost 4x the wrap BC)
            f = d.shape[0] // S.WRAP_DETAIL_MAP
            w = cov.astype(np.float64)
            num = (d * w).reshape(S.WRAP_DETAIL_MAP, f, S.WRAP_DETAIL_MAP, f).sum(axis=(1, 3))
            den = w.reshape(S.WRAP_DETAIL_MAP, f, S.WRAP_DETAIL_MAP, f).sum(axis=(1, 3))
            cov_d = den > 0
            d_small = np.where(cov_d, num / np.maximum(den, 1e-12), 0.0)
            d_small = BK.edge_extend(d_small[..., None].repeat(3, -1), cov_d)[..., 0]
            d_small, d_fill, _ = BK.detail_fill(d_small, cov_d)
            PNG.write_png(TEX_DIR / f"{stem}_Detail.png", flip(lin2srgb(d_small)))
            info["detail_background_fill_linear"] = d_fill
            np.save(WORK / "wrap_detail_cov_1024.npy", cov_d)
            tint = bc[cov].mean(axis=0)
            info.update({"detail_a_lo": float(lo), "detail_a_hi": float(hi), "default_tint_linear": [float(v) for v in tint],
                         "detail_size": int(S.WRAP_DETAIL_MAP),
                         "detail_encoding": "sRGB-encoded linear d = (albedo_luminance - a_lo)/(a_hi - a_lo), "
                                            "coverage-weighted 2x2 box to 1024"})
        report[atlas] = info
    for p in sorted(TEX_DIR.glob("*.png")):
        report.setdefault("sha256", {})[p.name] = sha256(p)
    json.dump(report, open(WORK / "maps_report.json", "w"), indent=1)
    log("maps", json.dumps({k: v for k, v in report.items() if k != "sha256"}, indent=0)[:1500])


# ====================================================================== stage game

def stage_game():
    from pipeline.helpers import make_lod_group, make_socket
    import bmesh
    bpy.ops.wm.open_mainfile(filepath=str(WORK_BLEND))
    # ---- save the v4 high-poly (bake source) as its own file
    high_objs = set(bpy.data.collections["HIGH"].objects)
    bpy.data.libraries.write(str(HIGH_BLEND), {bpy.data.collections["HIGH"]} | high_objs, fake_user=True)
    log("high-poly saved", HIGH_BLEND)
    for o in list(bpy.data.collections["HIGH"].objects) + list(bpy.data.collections["BAKE_LOW"].objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for cname in ("HIGH", "BAKE_LOW"):
        bpy.data.collections.remove(bpy.data.collections[cname])
    # ---- game materials (image textures only; Blender preview of the shipped maps)
    for nm in S.SLOT_NAMES:
        old = bpy.data.materials.get(nm)
        if old is not None:
            bpy.data.materials.remove(old)
    game_mats = [LK.make_game_material(nm, TEX_DIR / f"{S.SLOT_TEX[nm]}_BC.png", TEX_DIR / f"{S.SLOT_TEX[nm]}_ORM.png",
                                       TEX_DIR / f"{S.SLOT_TEX[nm]}_N.png") for nm in S.SLOT_NAMES]
    gcol = new_collection("SM_SnowFlower")
    lods = []
    for lv in (0, 1, 2):
        col = bpy.data.collections[f"LOD{lv}_parts"]
        parts = list(col.objects)
        for o in parts:
            # replace the slot materials in place (materials.clear() would reset the face indices)
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
        # triangulate (the shipped topology == the baked tangent frame)
        b = bmesh.new()
        b.from_mesh(ob.data)
        bmesh.ops.triangulate(b, faces=b.faces[:], quad_method="BEAUTY", ngon_method="BEAUTY")
        b.to_mesh(ob.data)
        b.free()
        # drop unused material slots? keep both on every LOD (identical section layout in Unreal)
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        gcol.objects.link(ob)
        bpy.data.collections.remove(col)
        lods.append(ob)
    lod0 = lods[0]
    # ---- collision: four convex hulls around the LOD0 vertices, overlapping so their union holds it
    V = np.array([v.co[:] for v in lod0.data.vertices]) * 1000.0
    zz = V[:, 2]
    rr = np.hypot(V[:, 0], V[:, 1])
    # final pass: five hulls.  The old grip+pommel hull took every vertex below z 64, which included the guard wings
    # (z 60-64), so it was as wide as the guard (+-59 mm); the grip hull now stops under the guard (z <= 50) and the
    # pommel has its own.
    groups = [
        ("blade", (zz > 110.0) & (zz <= 830.0)),
        ("tip", (zz > 800.0)),
        ("guard", (zz > 40.0) & (zz <= 132.0)),
        ("grip", (zz > -186.0) & (zz <= 50.0)),
        ("pommel", (zz <= -180.0)),
    ]
    # every vertex must be in at least one group
    covered = np.zeros(len(V), bool)
    for _, g in groups:
        covered |= g
    if not covered.all():
        raise RuntimeError(f"{(~covered).sum()} LOD0 vertices outside every hull group")
    hull_info = []
    for i, (gname, sel) in enumerate(groups):
        pts = V[sel] / 1000.0
        bm = bmesh.new()
        for p in pts:
            bm.verts.new(p)
        res = bmesh.ops.convex_hull(bm, input=bm.verts[:])
        for v in list(bm.verts):
            if not v.link_faces:
                bm.verts.remove(v)
        # simplify to <= 32 verts: iterative decimate + re-hull via the pipeline helper
        me = bpy.data.meshes.new(f"UCX_{NAME}_{i:02d}")
        bm.to_mesh(me)
        bm.free()
        h = bpy.data.objects.new(f"UCX_{NAME}_{i:02d}", me)
        gcol.objects.link(h)
        h.parent = lod0
        from pipeline.helpers import apply_modifier, _hull_only
        for _ in range(20):
            if len(me.vertices) <= 32:
                break
            mod = h.modifiers.new("dec", "DECIMATE")
            mod.decimate_type = "COLLAPSE"
            mod.ratio = max(0.1, 60.0 / max(len(me.polygons), 1))
            apply_modifier(h, mod)
            b2 = bmesh.new()
            b2.from_mesh(h.data)
            _hull_only(b2)
            b2.to_mesh(h.data)
            b2.free()
            me = h.data
        # the decimated hull may cut the mesh: push it out until it holds its vertex group
        _grow_hull_to_contain(h, pts)
        me.materials.clear()
        h.hide_render = True
        h.display_type = "WIRE"
        h["ue_collision"] = "UCX"
        hull_info.append({"name": h.name, "group": gname, "vertices": len(h.data.vertices)})
    # ---- sockets (Empties, UE correction baked by the pipeline helper)
    socks = {}
    for sname, (x, y, z) in S.socket_positions().items():
        s = make_socket(lod0, sname, (x / 1000.0, y / 1000.0, z / 1000.0))
        socks[sname] = [x, y, z]
    # ---- LOD group (renames the mesh to _LOD0 together with its UCX/SOCKET children)
    grp = make_lod_group(NAME, lods)
    bpy.context.scene["sf4_lod_screen_sizes"] = list(S.LOD_SCREEN_SIZES)
    bpy.context.scene["sf4_axis"] = "+Z blade, +X spine, -Y front; origin = Grip socket"
    guard_paths(GAME_BLEND)
    bpy.ops.wm.save_as_mainfile(filepath=str(GAME_BLEND))
    info = {"lod_objects": [o.name for o in lods],
            "lod_triangles": [sum(len(p.vertices) - 2 for p in o.data.polygons) for o in lods],
            "hulls": hull_info, "sockets_mm": socks, "game_blend": str(GAME_BLEND),
            "high_blend": str(HIGH_BLEND)}
    json.dump(info, open(WORK / "game_report.json", "w"), indent=1)
    log("game", json.dumps(info))


def _grow_hull_to_contain(h, pts, margin=0.0002):
    """Scale the hull's vertices out from its centroid until every point in ``pts`` is inside."""
    import bmesh
    from mathutils import Vector
    me = h.data
    c = np.array([v.co[:] for v in me.vertices]).mean(axis=0)
    for _ in range(30):
        b = bmesh.new()
        b.from_mesh(me)
        b.faces.ensure_lookup_table()
        planes = [(np.array(f.normal[:]), float(np.dot(np.array(f.normal[:]), np.array(f.verts[0].co[:])))) for f in b.faces]
        b.free()
        worst = 0.0
        for n, d in planes:
            worst = max(worst, float((pts @ n - d).max()))
        if worst <= 1e-7:
            return
        # grow by the worst excursion relative to the hull size
        size = np.linalg.norm(np.array([v.co[:] for v in me.vertices]) - c, axis=1).mean()
        k = 1.0 + (worst + margin) / max(size, 1e-6)
        for v in me.vertices:
            v.co = Vector(c + (np.array(v.co[:]) - c) * k)
    raise RuntimeError(f"{h.name}: hull could not be grown to contain its vertices")


# ====================================================================== stage export

def stage_export():
    from pipeline.export_fbx import export_fbx
    from pipeline.qa_check import qa_check
    bpy.ops.wm.open_mainfile(filepath=str(GAME_BLEND))
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    fbx = EXPORT_DIR / f"{NAME}.fbx"
    grp = bpy.data.objects[f"{NAME}_LodGroup"]
    res = export_fbx(str(fbx), [grp], kind="static", lod_screen_sizes=list(S.LOD_SCREEN_SIZES))
    log("export", json.dumps({k: res[k] for k in ("objects", "warnings", "sidecar", "lod_screen_sizes")}))
    objs = [f"{NAME}_LOD0", f"{NAME}_LOD1", f"{NAME}_LOD2"]
    texel = json.load(open(WORK / "geo_report.json"))["steel_px_per_cm"]
    qa = qa_check(objs, budget_tris=45000, texel_density=None, require_uv1=True)
    # texel density measured on the steel atlas only (the wrap uses its own 2048 map)
    json.dump({"export": res, "qa": qa, "fbx_sha256": sha256(fbx),
               "sidecar_sha256": sha256(res["sidecar"]) if res.get("sidecar") else None},
              open(WORK / "export_report.json", "w"), indent=1, default=str)
    # ---- the build's own record (the Unreal gates read their expectations from here)
    lod0 = bpy.data.objects[f"{NAME}_LOD0"]
    V = np.array([v.co[:] for v in lod0.data.vertices]) * 1000.0
    hulls = sorted(c.name for c in lod0.children if c.name.startswith("UCX_"))
    socks = sorted(c.name for c in lod0.children if c.name.startswith("SOCKET_"))
    rep = {"asset": NAME, "fbx": str(fbx), "sidecar": res.get("sidecar"),
           "lod_triangles": [qa["triangles"][o] for o in objs],
           "lod_screen_sizes": list(S.LOD_SCREEN_SIZES),
           "bbox_min_mm": V.min(axis=0).round(3).tolist(), "bbox_max_mm": V.max(axis=0).round(3).tolist(),
           "size_mm": (V.max(axis=0) - V.min(axis=0)).round(3).tolist(),
           "bounds_radius_mm": float(np.linalg.norm(V - 0.5 * (V.max(axis=0) + V.min(axis=0)), axis=1).max()),
           "collision": {"hulls": hulls, "hull_vertices": {h: len(bpy.data.objects[h].data.vertices) for h in hulls}},
           "sockets": socks, "sockets_mm": {k: list(v) for k, v in S.socket_positions().items()},
           "material_slots": [m.name for m in lod0.data.materials],
           "export": {"sha256": {"fbx": sha256(fbx), "sidecar": sha256(res["sidecar"]) if res.get("sidecar") else None}},
           "textures": json.load(open(WORK / "maps_report.json")),
           "qa": {"passed": qa["passed"], "checks": len(qa["checks"])},
           "frame": "mm, +Z blade, +X spine, -Y front; origin = Grip socket",
           "steel_px_per_cm": texel, "wrap_px_per_cm": json.load(open(WORK / "geo_report.json"))["wrap_px_per_cm"]}
    json.dump(rep, open(ROOT / "WorkFiles" / "SnowFlower" / "v4" / "sword_report.json", "w"), indent=1)
    fails = [c for c in qa["checks"] if not c["passed"]]
    log("qa passed", qa["passed"], "checks", len(qa["checks"]), "fails", json.dumps(fails)[:3000])


# ====================================================================== main

def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True)
    ap.add_argument("--channels", default="NORMAL,AO,BC,ROUGH,METAL")
    ap.add_argument("--parts", default="")
    a = ap.parse_args(argv)
    t = time.time()
    if a.stage == "geo":
        stage_geo()
    elif a.stage == "bake":
        stage_bake([c.strip() for c in a.channels.split(",") if c.strip()],
                   [c.strip() for c in a.parts.split(",") if c.strip()] or None)
    elif a.stage == "maps":
        stage_maps()
    elif a.stage == "game":
        stage_game()
    elif a.stage == "export":
        stage_export()
    else:
        raise SystemExit(f"unknown stage {a.stage}")
    log(f"stage {a.stage} finished in {time.time() - t:.1f}s")


if __name__ == "__main__":
    main()
