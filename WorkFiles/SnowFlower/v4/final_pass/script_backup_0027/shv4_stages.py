"""Snow Flower sheath build stages (geo, bake, maps, game, export); entry point build_sheath.py."""
from __future__ import annotations

import json
import math
import time
from pathlib import Path

import bpy
import numpy as np

import build_sheath as BS
import shv4_parts as P
import shv4_spec as S
import sfv4_bake as BK
import sfv4_png as PNG
import sfv4_uvpack as UP
from sfv4_mesh import MB

log = BS.log
WORK, BAKE_DIR, WORK_BLEND = BS.WORK, BS.BAKE_DIR, BS.WORK_BLEND

PARTS = ("body", "throat", "band", "chape", "stem", "bloom")
#: cage extrusion (mm) per bake group: above the tallest high detail that the low does not model
#: final pass: body 4.6 -> 6.2 mm - the two teardrop pods stand 5.4 mm proud, so the old cage started INSIDE them and
#: baked their back faces as the black "eye" the reviews saw
#: and bloom 2.6 -> 4.8 mm: a proxy rim sinks below its flower centre while the high petals stand ~0.1 r above it, so the
#: old cage started rays UNDER the petal rims of the larger blossoms (throat r 20.6 mm: 0.1 r + sink 2.0 = 4.1 mm) and
#: baked their undersides - the black crescents / halos
CAGE_MM = {"body": 6.2, "throat": 4.4, "band": 2.4, "chape": 4.2, "stem": 1.2, "bloom": 4.8}
#: high groups each low part may hit.  Final pass: the blossom proxies also see the surface they sit on, so rays in the
#: gaps between petals land on the lacquer / fitting instead of missing or grazing a petal wall (the black crescents and
#: halos on every blossom rim in the craft review)
HIGH_FOR = {"body": ("body", "vine", "bloomv"), "throat": ("throat",), "band": ("band",), "chape": ("chape",),
            "stem": ("vine",), "bloom": ("bloomv", "bloomf", "body", "vine", "throat", "band", "chape")}

HIDDEN = ("throat_in", "band_in", "chape_cav", "core_bot", "chape_top", "cav0", "cav1", "cav2", "cav3")


def island_scale(name):
    if name.endswith("_under"):
        return 0.1
    if name in HIDDEN or name.startswith("body0_") or name.startswith("body2_"):
        return 0.06
    if name == "cav_mouth":
        return 0.35
    if name == "core_top":
        return 0.5
    return 1.0


def new_collection(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c


def build_low(level):
    out = {}
    mb = MB(f"body_L{level}")
    P.build_core(mb, level)
    out["body"] = mb
    for name, fn in (("throat", P.build_throat), ("band", P.build_band), ("chape", P.build_chape)):
        mb = MB(f"{name}_L{level}")
        fn(mb, level)
        out[name] = mb
    if level in (0, 1):
        mb = MB(f"stem_L{level}")
        P.build_stem(mb, level)
        out["stem"] = mb
    mb = MB(f"bloom_L{level}")
    P.build_blooms(mb, level)
    out["bloom"] = mb
    for k, m in out.items():
        # every low face is lacquer (slot 0) on the body and silver (slot 1) elsewhere
        m.fmat = [P.LACQ if k == "body" else P.SILV for _ in m.fmat]
    return {k: v for k, v in out.items() if v.faces}


def build_high():
    import sfv4_rev3 as R3
    import shv4_relief as RL
    out = {}
    sink = R3.Sink("body")
    P.build_core(sink.mb(P.H_LACQ), "high", uvmode="pattern")
    out["body"] = sink.mbs
    sink = R3.Sink("vine")
    RL.vine_high(sink)
    out["vine"] = sink.mbs
    sink = R3.Sink("bloomv")
    RL.blossoms_high(sink, ("vine",))
    out["bloomv"] = sink.mbs
    sink = R3.Sink("bloomf")
    RL.blossoms_high(sink, ("fitting",))
    out["bloomf"] = sink.mbs
    for name, fn, rl in (("throat", P.build_throat, RL.throat_high), ("band", P.build_band, RL.band_high),
                         ("chape", P.build_chape, RL.chape_high)):
        sink = R3.Sink(name)
        fn(sink.mb(R3.SILVER), "high", high=True)
        rl(sink)
        out[name] = sink.mbs
    return out


# ====================================================================== stage geo

def stage_geo():
    import shv4_look as LOOK
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    t0 = time.time()
    lows = {lv: build_low(lv) for lv in (0, 1, 2)}
    tri = {lv: {p: m.tri_count() for p, m in d.items()} for lv, d in lows.items()}
    log("low tris", {lv: sum(v.values()) for lv, v in tri.items()}, tri)
    isl = {}
    for lv, d in lows.items():
        for part, mb in d.items():
            for k, pts in mb.islands().items():
                isl[k] = np.vstack([isl[k], pts]) if k in isl else pts
    UP.island_scale = island_scale
    atlas = UP.pack(isl, S.ATLAS, S.PAD_PX // 2, 0.0)
    lm = UP.pack(isl, 1024, 3, 0.0, scaled=False)
    WORK.mkdir(parents=True, exist_ok=True)
    UP.save(atlas, WORK / "atlas.json")
    UP.save(lm, WORK / "atlas_lightmap.json")
    log(f"atlas {atlas.density * 10:.1f} px/cm cover {UP.coverage_fraction(atlas):.2f}; islands {len(isl)}")

    lac = bpy.data.materials.new(BS.SLOT_LACQUER)
    sil = bpy.data.materials.new(BS.SLOT_SILVER)
    for lv, d in lows.items():
        col = new_collection(f"LOD{lv}_parts")
        for part, mb in d.items():
            ob = mb.to_object(f"SH4_L{lv}_{part}", col, materials=[lac, sil], uv_transform=atlas.transform,
                              uv1_transform=lm.transform)
            ob["sh4_part"] = part
            ob["sh4_level"] = lv
    col = new_collection("BAKE_LOW")
    import bmesh
    for part, mb in lows[0].items():
        bm_ = bpy.data.materials.new(f"BAKE_{part}")
        bm_.use_nodes = True
        n = bm_.node_tree.nodes.new("ShaderNodeTexImage")
        n.name = "bake_target"
        ob = mb.to_object(f"SH4_BAKE_{part}", col, materials=[bm_, bm_], uv_transform=atlas.transform)
        b = bmesh.new()
        b.from_mesh(ob.data)
        bmesh.ops.triangulate(b, faces=b.faces[:], quad_method="BEAUTY", ngon_method="BEAUTY")
        b.to_mesh(ob.data)
        b.free()
        ob["sh4_part"] = part
        ob.visible_diffuse = ob.visible_glossy = ob.visible_shadow = ob.visible_transmission = False
    # ---- lacquer pattern + high
    bc, rough, meta = LOOK.paint_lacquer()
    np.save(WORK / "lacquer_bc.npy", bc.astype(np.float32))
    img_bc = bpy.data.images.new("SH4_LACQUER_BC", meta["W"], meta["H"], float_buffer=True, is_data=True)
    img_bc.pixels.foreach_set(np.concatenate([bc, np.ones(bc.shape[:2] + (1,))], -1).astype(np.float32).ravel())
    img_bc.pack()
    img_r = bpy.data.images.new("SH4_LACQUER_ROUGH", meta["W"], meta["H"], float_buffer=True, is_data=True)
    img_r.pixels.foreach_set(np.stack([rough] * 3 + [np.ones_like(rough)], -1).astype(np.float32).ravel())
    img_r.pack()
    hmats = LOOK.make_high_materials(img_bc, img_r)
    high = build_high()
    col = new_collection("HIGH")
    ht = 0
    for group, d in high.items():
        for mkey, mb in d.items():
            if not mb.faces:
                continue
            ht += mb.tri_count()
            ob = mb.to_object(f"SH4_H_{group}_{mkey}", col, materials=hmats, recalc=True, smooth_angle=50.0)
            ob.data.polygons.foreach_set("material_index", mb.fmat)
            ob["sh4_group"] = group
    log("high tris", ht, f"{time.time() - t0:.1f}s", "vein fraction", round(meta["vein_fraction"], 3))
    json.dump({"low_tris": tri, "high_tris": ht, "atlas_px_per_cm": atlas.density * 10,
               "atlas_cover": UP.coverage_fraction(atlas), "lacquer_meta": {k: v for k, v in meta.items()}},
              open(WORK / "geo_report.json", "w"), indent=1, default=float)
    bpy.ops.wm.save_as_mainfile(filepath=str(WORK_BLEND))
    log("saved", WORK_BLEND)


# ====================================================================== stage bake

def stage_bake(channels):
    import sfv4_look as LK
    bpy.ops.wm.open_mainfile(filepath=str(WORK_BLEND))
    dev = BK.setup_cycles()
    log("device", dev)
    sc = bpy.context.scene
    if sc.world is None:
        sc.world = bpy.data.worlds.new("bake_world")
    sc.world.light_settings.distance = 0.012
    hmats = [m for m in bpy.data.materials if m.name.startswith("SH4H_")]
    lows = list(bpy.data.collections["BAKE_LOW"].objects)
    highs = list(bpy.data.collections["HIGH"].objects)
    for c in bpy.data.collections:
        if c.name.startswith("LOD"):
            for o in c.objects:
                o.hide_render = True
    BAKE_DIR.mkdir(parents=True, exist_ok=True)
    size = S.ATLAS
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
        acc = np.zeros((size, size, 3), np.float32)
        cov = np.zeros((size, size), bool)
        for low in lows:
            part = low["sh4_part"]
            hs = [h for h in highs if h["sh4_group"] in HIGH_FOR[part]]
            for o in lows:
                o.hide_render = o is not low
            px = BK.bake_part(low, hs, btype, size, CAGE_MM[part], samples)
            tris = BK.uv_triangles_px(low, size, 0.0)
            m = BK.rasterize(tris, size, dilate=1)
            acc[m] = px[..., :3][m]
            cov |= m
            if ch == "NORMAL":
                np.save(BAKE_DIR / f"cov_{part}.npy", m)
        np.save(BAKE_DIR / f"sheath_{ch}.npy", acc)
        np.save(BAKE_DIR / "sheath_cov.npy", cov)
        log(f"channel {ch} done {time.time() - t:.1f}s")


# ====================================================================== stage maps

def lin2srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def stage_maps():
    BS.TEX_DIR.mkdir(parents=True, exist_ok=True)
    cov = np.load(BAKE_DIR / "sheath_cov.npy")
    ld = lambda ch: np.load(BAKE_DIR / f"sheath_{ch}.npy")
    nrm = BK.edge_extend(ld("NORMAL"), cov)
    nrm[..., 1] = 1.0 - nrm[..., 1]                         # OpenGL -> DirectX
    ao = BK.edge_extend(ld("AO"), cov)[..., 0]
    bc = BK.edge_extend(ld("BC"), cov)
    rough = BK.edge_extend(ld("ROUGH"), cov)[..., 0]
    metal = BK.edge_extend(ld("METAL"), cov)[..., 0]
    flip = lambda a: a[::-1]
    stem = BS.TEX_STEM
    PNG.write_png(BS.TEX_DIR / f"{stem}_BC.png", flip(lin2srgb(bc)))
    PNG.write_png(BS.TEX_DIR / f"{stem}_ORM.png", flip(np.stack([ao, rough, metal], -1)))
    PNG.write_png(BS.TEX_DIR / f"{stem}_N.png", flip(np.clip(nrm, 0, 1)))
    # lacquer Detail (tint-ready, the sword wrap's convention): full-range normalised luminance over the lacquer texels.
    # Final pass: (1) normalised over the DIELECTRIC lacquer texels only (metallic < 0.5): the baked silver twigs, buds and
    # second stem on the body islands were setting a_hi at 0.77 and left the marble ~12 % of the range; those texels keep
    # their baked colour and metal through the pack master's 'Metal From ORM' switch.  (2) shipped at
    # S.LACQUER_DETAIL_MAP (2048, coverage-weighted 2x2 box): the 4096 sRGB G8 built as an 85 MiB BGRA8 in Unreal.
    lac = np.load(BAKE_DIR / "cov_body.npy")
    lum = bc @ np.array([0.2126, 0.7152, 0.0722])
    diel = lac & cov & (metal < 0.5)
    lo, hi = np.percentile(lum[diel], [0.1, 99.9])
    d = np.clip((lum - lo) / max(hi - lo, 1e-6), 0, 1)
    fdn = d.shape[0] // S.LACQUER_DETAIL_MAP
    w = (lac & cov).astype(np.float64)
    num = (d * w).reshape(S.LACQUER_DETAIL_MAP, fdn, S.LACQUER_DETAIL_MAP, fdn).sum(axis=(1, 3))
    den = w.reshape(S.LACQUER_DETAIL_MAP, fdn, S.LACQUER_DETAIL_MAP, fdn).sum(axis=(1, 3))
    cov_d = den > 0
    d = np.where(cov_d, num / np.maximum(den, 1e-12), 0.0)
    d = BK.edge_extend(d[..., None].repeat(3, -1), cov_d)[..., 0]
    d, d_fill, _ = BK.detail_fill(d, cov_d)
    np.save(WORK / "lacquer_detail_cov_2048.npy", cov_d)
    PNG.write_png(BS.TEX_DIR / f"{stem}_Lacquer_Detail.png", flip(lin2srgb(d)))
    silver = cov & ~lac
    info = {"size": int(cov.shape[0]), "coverage": float(cov.mean()),
            "bc_mean_linear_lacquer": [float(v) for v in bc[lac & cov].mean(axis=0)],
            "bc_mean_linear_silver": [float(v) for v in bc[silver].mean(axis=0)],
            "ao_mean": float(ao[cov].mean()), "rough_mean_lacquer": float(rough[lac & cov].mean()),
            "rough_mean_silver": float(rough[silver].mean()), "metal_mean_lacquer": float(metal[lac & cov].mean()),
            "metal_mean_silver": float(metal[silver].mean()),
            "lacquer_detail_a_lo": float(lo), "lacquer_detail_a_hi": float(hi),
            "lacquer_detail_size": int(S.LACQUER_DETAIL_MAP), "lacquer_detail_background_fill_linear": d_fill, "lacquer_detail_range_texels": "dielectric lacquer (metal < 0.5)",
            "lacquer_metal_texel_fraction": float((lac & cov & (metal >= 0.5)).sum() / max((lac & cov).sum(), 1)),
            "lacquer_default_tint_linear": [float(v) for v in bc[lac & cov].mean(axis=0)],
            "lacquer_dielectric_tint_linear": [float(v) for v in bc[diel].mean(axis=0)],
            "detail_encoding": "sRGB-encoded linear d = (albedo_luminance - a_lo)/(a_hi - a_lo), lacquer texels"}
    for p in sorted(BS.TEX_DIR.glob(f"{stem}_*.png")):
        info.setdefault("sha256", {})[p.name] = BS.sha256(p)
    json.dump(info, open(WORK / "maps_report.json", "w"), indent=1)
    log("maps", json.dumps({k: v for k, v in info.items() if k != "sha256"})[:1200])


# ====================================================================== stage game

def _grow_hull_to_contain(h, pts, margin=0.0002):
    import bmesh
    from mathutils import Vector
    me = h.data
    c = np.array([v.co[:] for v in me.vertices]).mean(axis=0)
    for _ in range(40):
        b = bmesh.new()
        b.from_mesh(me)
        b.faces.ensure_lookup_table()
        planes = [(np.array(f.normal[:]), float(np.dot(np.array(f.normal[:]), np.array(f.verts[0].co[:])))) for f in b.faces]
        b.free()
        worst = max(float((pts @ n - d).max()) for n, d in planes)
        if worst <= 1e-7:
            return
        size = np.linalg.norm(np.array([v.co[:] for v in me.vertices]) - c, axis=1).mean()
        k = 1.0 + (worst + margin) / max(size, 1e-6)
        for v in me.vertices:
            v.co = Vector(c + (np.array(v.co[:]) - c) * k)
    raise RuntimeError(f"{h.name}: hull could not be grown to contain its vertices")


def _clip_hull_at_mouth(h, z_cut):
    """Intersect the hull with the half-space z >= z_cut (the sheath lies entirely below the mouth plane in +Z)."""
    import bmesh
    b = bmesh.new()
    b.from_mesh(h.data)
    bmesh.ops.bisect_plane(b, geom=b.verts[:] + b.edges[:] + b.faces[:], plane_co=(0.0, 0.0, z_cut),
                           plane_no=(0.0, 0.0, 1.0), clear_inner=True)
    pts = [v.co.copy() for v in b.verts]
    b.free()
    b = bmesh.new()
    for p in pts:
        b.verts.new(p)
    bmesh.ops.convex_hull(b, input=b.verts[:])
    for v in list(b.verts):
        if not v.link_faces:
            b.verts.remove(v)
    b.to_mesh(h.data)
    b.free()


def stage_game():
    import bmesh
    import sfv4_look as LK
    from pipeline.helpers import apply_modifier, _hull_only, make_lod_group, make_socket
    bpy.ops.wm.open_mainfile(filepath=str(WORK_BLEND))
    BS.guard_paths(BS.HIGH_BLEND, BS.GAME_BLEND)
    high_objs = set(bpy.data.collections["HIGH"].objects)
    bpy.data.libraries.write(str(BS.HIGH_BLEND), {bpy.data.collections["HIGH"]} | high_objs, fake_user=True)
    log("high-poly saved", BS.HIGH_BLEND)
    for o in list(bpy.data.collections["HIGH"].objects) + list(bpy.data.collections["BAKE_LOW"].objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for cname in ("HIGH", "BAKE_LOW"):
        bpy.data.collections.remove(bpy.data.collections[cname])
    for nm in (BS.SLOT_LACQUER, BS.SLOT_SILVER):
        old = bpy.data.materials.get(nm)
        if old is not None:
            bpy.data.materials.remove(old)
    T = BS.TEX_DIR
    st = BS.TEX_STEM
    lac = LK.make_game_material(BS.SLOT_LACQUER, T / f"{st}_BC.png", T / f"{st}_ORM.png", T / f"{st}_N.png")
    sil = LK.make_game_material(BS.SLOT_SILVER, T / f"{st}_BC.png", T / f"{st}_ORM.png", T / f"{st}_N.png")
    gcol = new_collection(BS.NAME)
    lods = []
    for lv in (0, 1, 2):
        col = bpy.data.collections[f"LOD{lv}_parts"]
        parts = list(col.objects)
        for o in parts:
            o.data.materials[0] = lac
            o.data.materials[1] = sil
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        for o in parts:
            o.select_set(True)
        bpy.context.view_layer.objects.active = parts[0]
        bpy.ops.object.join()
        ob = parts[0]
        ob.name = BS.NAME if lv == 0 else f"{BS.NAME}_LOD{lv}"
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
    lod0 = lods[0]
    # ---- collision: three convex hulls (throat + upper body, body, chape), overlapping
    V = np.array([v.co[:] for v in lod0.data.vertices]) * 1000.0
    zz = V[:, 2]
    groups = [("throat_upper", zz <= float(S.zr(470.0))),
              ("body", (zz >= float(S.zr(440.0))) & (zz <= float(S.zr(1275.0)))),
              ("chape", zz >= float(S.zr(1255.0)))]
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
        bmesh.ops.convex_hull(bm, input=bm.verts[:])
        for v in list(bm.verts):
            if not v.link_faces:
                bm.verts.remove(v)
        me = bpy.data.meshes.new(f"UCX_{BS.NAME}_{i:02d}")
        bm.to_mesh(me)
        bm.free()
        h = bpy.data.objects.new(f"UCX_{BS.NAME}_{i:02d}", me)
        gcol.objects.link(h)
        h.parent = lod0
        for _ in range(20):
            if len(me.vertices) <= 24:
                break
            mod = h.modifiers.new("dec", "DECIMATE")
            mod.decimate_type = "COLLAPSE"
            mod.ratio = max(0.1, 44.0 / max(len(me.polygons), 1))
            apply_modifier(h, mod)
            b2 = bmesh.new()
            b2.from_mesh(h.data)
            _hull_only(b2)
            b2.to_mesh(h.data)
            b2.free()
            me = h.data
        _grow_hull_to_contain(h, pts)
        if gname == "throat_upper":
            # final pass: growing the decimated hull about its centroid pushed it ~16 mm past the mouth, into the
            # sheathed guard's hull; cut it at the mouth plane (nothing of the sheath is above it) and re-hull
            _clip_hull_at_mouth(h, float(S.Z_MOUTH) / 1000.0 - 0.0002)
            _grow_hull_to_contain(h, pts)
        me = h.data
        me.materials.clear()
        h.hide_render = True
        h.display_type = "WIRE"
        hull_info.append({"name": h.name, "group": gname, "vertices": len(h.data.vertices),
                          "z_min_mm": round(min(v.co.z for v in h.data.vertices) * 1000.0, 3)})
    # ---- sockets (Empties; the pipeline bakes the UE orientation correction)
    fit = json.loads((P.FIT_DIR / "fit.json").read_text(encoding="utf-8"))
    band_back = float(-P.front_y(P.band_ring(S.ROW_BAND), 0.0))
    socks = {}
    for sname, rec in fit["sockets"].items():
        loc = np.array(rec["location_mm"]) / 1000.0
        make_socket(lod0, sname, tuple(loc), tuple(rec["rotation_euler_rad"]))
        socks[sname] = {"location_mm": rec["location_mm"], "rotation_deg": [math.degrees(a) for a in rec["rotation_euler_rad"]]}
    make_socket(lod0, "BeltMount", (0.0, band_back / 1000.0, 0.0), (0.0, 0.0, 0.0))
    socks["BeltMount"] = {"location_mm": [0.0, band_back, 0.0], "rotation_deg": [0.0, 0.0, 0.0]}
    make_lod_group(BS.NAME, lods)
    bpy.context.scene["sh4_lod_screen_sizes"] = list(S.LOD_SCREEN_SIZES)
    bpy.context.scene["sh4_axis"] = ("+Z toward the chape point, +X sword spine side, -Y front (vine face); origin = mid "
                                     "band centre on the sheath axis")
    bpy.ops.wm.save_as_mainfile(filepath=str(BS.GAME_BLEND))
    info = {"lod_objects": [o.name for o in lods],
            "lod_triangles": [sum(len(p.vertices) - 2 for p in o.data.polygons) for o in lods],
            "hulls": hull_info, "sockets": socks, "game_blend": str(BS.GAME_BLEND), "high_blend": str(BS.HIGH_BLEND)}
    json.dump(info, open(WORK / "game_report.json", "w"), indent=1)
    log("game", json.dumps(info))


# ====================================================================== stage export

def stage_export():
    from pipeline.export_fbx import export_fbx
    from pipeline.qa_check import qa_check
    bpy.ops.wm.open_mainfile(filepath=str(BS.GAME_BLEND))
    BS.EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    fbx = BS.EXPORT_DIR / f"{BS.NAME}.fbx"
    BS.guard_paths(fbx)
    grp = bpy.data.objects[f"{BS.NAME}_LodGroup"]
    res = export_fbx(str(fbx), [grp], kind="static", lod_screen_sizes=list(S.LOD_SCREEN_SIZES))
    log("export", json.dumps({k: res[k] for k in ("objects", "warnings", "sidecar", "lod_screen_sizes")}))
    objs = [f"{BS.NAME}_LOD0", f"{BS.NAME}_LOD1", f"{BS.NAME}_LOD2"]
    geo = json.load(open(WORK / "geo_report.json"))
    qa = qa_check(objs, budget_tris=S.BUDGET_TRIS, texel_density=S.QA_TEXEL_TARGET, tolerance=0.25, require_uv1=True)
    fails = [c for c in qa["checks"] if not c["passed"]]
    json.dump({"export": res, "qa": qa, "fbx_sha256": BS.sha256(fbx),
               "sidecar_sha256": BS.sha256(res["sidecar"]) if res.get("sidecar") else None},
              open(WORK / "export_report.json", "w"), indent=1, default=str)
    lod0 = bpy.data.objects[f"{BS.NAME}_LOD0"]
    V = np.array([v.co[:] for v in lod0.data.vertices]) * 1000.0
    hulls = sorted(c.name for c in lod0.children if c.name.startswith("UCX_"))
    socks = sorted(c.name for c in lod0.children if c.name.startswith("SOCKET_"))
    fit = json.loads((P.FIT_DIR / "fit.json").read_text(encoding="utf-8"))
    rep = {"asset": BS.NAME, "fbx": str(fbx), "sidecar": res.get("sidecar"),
           "lod_triangles": [qa["triangles"][o] for o in objs], "lod_screen_sizes": list(S.LOD_SCREEN_SIZES),
           "bbox_min_mm": V.min(axis=0).round(3).tolist(), "bbox_max_mm": V.max(axis=0).round(3).tolist(),
           "size_mm": (V.max(axis=0) - V.min(axis=0)).round(3).tolist(),
           "bounds_radius_mm": float(np.linalg.norm(V - 0.5 * (V.max(axis=0) + V.min(axis=0)), axis=1).max()),
           "collision": {"hulls": hulls, "hull_vertices": {h: len(bpy.data.objects[h].data.vertices) for h in hulls}},
           "sockets": socks, "material_slots": [m.name for m in lod0.data.materials],
           "export": {"sha256": {"fbx": BS.sha256(fbx), "sidecar": BS.sha256(res["sidecar"]) if res.get("sidecar") else None}},
           "textures": json.load(open(WORK / "maps_report.json")),
           "qa": {"passed": qa["passed"], "checks": len(qa["checks"]), "fails": fails},
           "frame": "mm, +Z toward the chape point, +X sword spine side, -Y front; origin = mid band centre on the axis",
           "atlas_px_per_cm": geo["atlas_px_per_cm"], "fit": {k: fit[k] for k in (
               "phi_deg", "t_mm", "lateral_margin_beyond_wall_and_clearance_mm", "hilt_offset_at_mouth_mm",
               "guard_gap_mm", "z_tip", "tip_row", "clearance_mm", "cavity", "sockets")}}
    # where the sword's own sockets must land in the sheath's space (Unreal cm) when it hangs on the Holster socket:
    # the in-engine gate compares Unreal's socket composition with this
    Mf = np.array(fit["matrix_S_from_W"])
    sw_side = json.loads((BS.EXPORT_DIR / "SM_SnowFlower.sockets.json").read_text(encoding="utf-8"))
    exp = {}
    for r in sw_side["sockets"]:
        cm = r["location_cm"]
        pw = np.array([cm[0] * 10.0, -cm[1] * 10.0, cm[2] * 10.0, 1.0])
        ps = Mf @ pw
        exp[r["socket"]] = [round(ps[0] / 10.0, 4), round(-ps[1] / 10.0, 4), round(ps[2] / 10.0, 4)]
    rep["holster_expected_ue_cm"] = exp
    json.dump(rep, open(S.ROOT / "WorkFiles" / "SnowFlower" / "v4" / "sheath_report.json", "w"), indent=1)
    log("qa passed", qa["passed"], "checks", len(qa["checks"]), "fails", json.dumps(fails)[:3000])
