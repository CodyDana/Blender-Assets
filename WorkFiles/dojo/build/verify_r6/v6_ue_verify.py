"""VERIFY r6 (independent verifier), Unreal side. pythonscript commandlet, -nullrhi, a FRESH process, READ-ONLY: nothing
is saved; the only file written is WorkFiles/dojo/build/verify_r6/ue_verify.json.

Truth sources: layout_showcase.json (instances, markers, routes) and verify_r6/fbx_audit.json (this verifier's own
re-import of every exported FBX: UCX counts, LODs, triangles, slots, local vertex boxes). The expected world boxes are
computed here from the audit boxes and the layout matrices (not from the builder's blender_bounds.json).
"""
import json
import math
import time
import traceback
from collections import Counter
from pathlib import Path

import unreal

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
VD = ROOT / "WorkFiles" / "dojo" / "build" / "verify_r6"
L = json.loads((ROOT / "WorkFiles/dojo/build/showcase/layout_showcase.json").read_text(encoding="utf-8"))
A = json.loads((VD / "fbx_audit.json").read_text(encoding="utf-8"))["pieces"]
PROJ = Path(r"C:\Users\Cody\Documents\Unreal Projects\DojoLab")
LEVEL = "/Game/Dojo/Maps/L_Dojo"
GM = "/Game/Dojo/Blueprints/GM_Dojo"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
CH = unreal.CollisionChannel
V = unreal.Vector
TOL_CM = 1.0
ENGINE_DEFAULT_NAMES = {"WorldGridMaterial", "DefaultMaterial", "DefaultLitMaterial", "DefaultDeferredDecalMaterial"}


# ------------------------------------------------------------------ maths (Blender frame -> UE), independent of dj_*
def rot_bl(r):
    rx, ry, rz = (math.radians(a) for a in r)
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    return [[cz * cy, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx],
            [sz * cy, sz * sy * sx + cz * cx, sz * sy * cx - cz * sx],
            [-sy, cy * sx, cy * cx]]


def expected_box_ue(inst, local_box):
    """local_box [[min],[max]] (m, Blender local) -> world UE AABB [x0,y0,z0,x1,y1,z1] cm."""
    R = rot_bl(inst["rot_xyz_deg"])
    s, t = inst["scale"], inst["loc"]
    pts = []
    for x in (local_box[0][0], local_box[1][0]):
        for y in (local_box[0][1], local_box[1][1]):
            for z in (local_box[0][2], local_box[1][2]):
                v = (x * s[0], y * s[1], z * s[2])
                w = [t[i] + sum(R[i][j] * v[j] for j in range(3)) for i in range(3)]
                pts.append((w[0] * 100, -w[1] * 100, w[2] * 100))
    return [min(p[k] for p in pts) for k in range(3)] + [max(p[k] for p in pts) for k in range(3)]


def ue_rot_cols(inst):
    R = rot_bl(inst["rot_xyz_deg"])
    S = (1, -1, 1)
    U = [[S[i] * R[i][j] * S[j] for j in range(3)] for i in range(3)]
    return [(U[0][j], U[1][j], U[2][j]) for j in range(3)]


def enum_name(e):
    return str(e).split(".")[-1].split(":")[0].strip("<> ").replace("ECR_", "").lower()


def resp(comp, ch):
    return enum_name(comp.get_collision_response_to_channel(ch))


def hit_info(h):
    if h is None:
        return None
    t = h.to_tuple()
    if not t[0] and not t[1]:
        return None
    act = t[9]
    return {"blocking": bool(t[0]), "start_pen": bool(t[1]), "time": round(float(t[2]), 4),
            "impact": [round(t[5].x, 2), round(t[5].y, 2), round(t[5].z, 2)],
            "actor": act.get_actor_label() if act else None}


# ------------------------------------------------------------------ 1 project / gameplay
def check_gameplay():
    ini = (PROJ / "Config" / "DefaultEngine.ini").read_text(encoding="utf-8")
    lines = [l.strip() for l in ini.splitlines() if l.strip().startswith(("GameDefaultMap", "EditorStartupMap",
                                                                          "GlobalDefaultGameMode", "ServerDefaultMap"))]
    gm_cls = unreal.EditorAssetLibrary.load_blueprint_class(GM)
    pawn = unreal.get_default_object(gm_cls).get_editor_property("default_pawn_class") if gm_cls else None
    parent = None
    try:
        parent = unreal.EditorAssetLibrary.load_asset(GM).get_editor_property("parent_class").get_path_name()
    except Exception:  # noqa: BLE001
        pass
    ws = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_world_settings()
    ov = ws.get_editor_property("default_game_mode")
    res = {"ini_lines": lines, "gm_parent": parent, "default_pawn": pawn.get_path_name() if pawn else None,
           "world_gamemode_override": ov.get_path_name() if ov else None}
    res["default_map_ok"] = any(l.replace(" ", "") == f"GameDefaultMap={LEVEL}.L_Dojo" for l in lines)
    res["editor_startup_map"] = next((l for l in lines if l.startswith("EditorStartupMap")), None)
    res["global_gm_ok"] = any(l.replace(" ", "") == f"GlobalDefaultGameMode={GM}.GM_Dojo_C" for l in lines)
    res["pawn_ok"] = bool(pawn) and pawn.get_path_name().endswith("/Game/Blueprints/SandboxCharacter_CMC.SandboxCharacter_CMC_C")
    res["editor_map_ok"] = any(l.replace(" ", "") == f"EditorStartupMap={LEVEL}.L_Dojo" for l in lines)
    res["passed"] = res["default_map_ok"] and res["editor_map_ok"] and res["pawn_ok"] and (res["global_gm_ok"] or (ov and ov.get_name() == "GM_Dojo_C"))
    return res


# ------------------------------------------------------------------ 2 meshes + materials
def mat_root(mi):
    chain = []
    m = mi
    while isinstance(m, unreal.MaterialInstance):
        chain.append(m.get_path_name())
        m = m.get_editor_property("parent")
    chain.append(m.get_path_name() if m else None)
    return chain


def bad_material(m):
    if m is None:
        return "None"
    chain = mat_root(m)
    if any(c is None or c.startswith("/Engine/") for c in chain):
        return "engine: " + " <- ".join(str(c) for c in chain)
    if any(c.split(".")[-1] in ENGINE_DEFAULT_NAMES for c in chain if c):
        return "default-named: " + " <- ".join(chain)
    return None


def check_meshes():
    out, fails = {}, {}
    for piece, p in sorted(L["pieces"].items()):
        a = A[piece]
        m = unreal.load_asset(f"{p['ue_dir']}/{piece}")
        if not isinstance(m, unreal.StaticMesh):
            fails[piece] = "missing in UE"
            continue
        agg = m.get_editor_property("body_setup").get_editor_property("agg_geom")
        ns = m.get_editor_property("nanite_settings")
        nan = bool(ns.get_editor_property("enabled"))
        e = {"convex": len(agg.get_editor_property("convex_elems")), "ucx_fbx": a["n_ucx"],
             "other_simple": sum(len(agg.get_editor_property(k)) for k in ("box_elems", "sphere_elems", "sphyl_elems")),
             "nanite": nan, "nanite_layout": bool(p.get("nanite")), "lods": int(m.get_num_lods()), "lods_fbx": a["lods"],
             "tris0": int(m.get_num_triangles(0)), "tris0_fbx": a["tris"][0], "slots": {}, "bad_slots": {}}
        if nan:
            e["fallback"] = [enum_name(ns.get_editor_property("fallback_target")),
                             float(ns.get_editor_property("fallback_relative_error")),
                             float(ns.get_editor_property("fallback_percent_triangles"))]
        for s in m.get_editor_property("static_materials"):
            nm = str(s.get_editor_property("material_slot_name"))
            mi = s.get_editor_property("material_interface")
            e["slots"][nm] = mi.get_path_name() if mi else None
            b = bad_material(mi)
            if b:
                e["bad_slots"][nm] = b
        why = []
        if e["convex"] != e["ucx_fbx"]:
            why.append("convex != FBX UCX")
        if e["ucx_fbx"] == 0:
            why.append("NO UCX in the FBX")
        if e["other_simple"]:
            why.append("extra simple shapes")
        if e["nanite"] != e["nanite_layout"]:
            why.append("nanite flag != layout")
        if e["lods"] != e["lods_fbx"]:
            why.append("LOD count != FBX")
        if e["tris0"] != e["tris0_fbx"]:
            why.append("LOD0/fallback tris != FBX")
        if sorted(e["slots"]) != sorted(a["slots"]):
            why.append("slot names != FBX")
        if e["bad_slots"]:
            why.append("engine-default/missing material")
        if nan and not ((e["fallback"][0] == "relative_error" and e["fallback"][1] == 0.0)
                        or (e["fallback"][0] == "percent_triangles" and e["fallback"][2] >= 1.0)):
            why.append("nanite fallback not full")
        e["fail"] = why
        if why:
            fails[piece] = why
        out[piece] = e
    # props over ~2k tris must be Nanite (user decision 2026-10-02)
    prop_kits = ("taiko", "training", "stone", "modern", "yard")
    heavy_not_nanite = sorted(k for k, p in L["pieces"].items() if p["kit"] in prop_kits and A[k]["tris"][0] > 2000
                              and not out.get(k, {}).get("nanite") and p["class"] != "nocollision")
    return {"n_layout": len(L["pieces"]), "n_found": len(out), "n_nanite": sum(1 for v in out.values() if v["nanite"]),
            "n_convex_total": sum(v["convex"] for v in out.values()), "fails": fails,
            "props_over_2k_not_nanite": heavy_not_nanite, "meshes": out,
            "passed": not fails and len(out) == len(L["pieces"]) and not heavy_not_nanite}


# ------------------------------------------------------------------ 3 level
def vbox_ue_local(mesh):
    lo, hi = [1e18] * 3, [-1e18] * 3
    for s in range(mesh.get_num_sections(0)):
        verts = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(mesh, 0, s)[0]
        for v in verts:
            for k, c in enumerate((v.x, v.y, v.z)):
                lo[k] = min(lo[k], c)
                hi[k] = max(hi[k], c)
    return lo, hi


def world_of(actor, box):
    lo, hi = box
    t = actor.get_actor_transform()
    pts = [t.transform_location(V(x, y, z)) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
    return [min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts),
            max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)]


def check_level():
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    loaded = bool(les.load_level(LEVEL))
    actors = EAS.get_all_level_actors()
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    labels = Counter(a.get_actor_label() for a in actors)
    by_label = {a.get_actor_label(): a for a in actors}
    sma = [a for a in actors if isinstance(a, unreal.StaticMeshActor)]
    res = {"loaded": loaded, "world": world.get_path_name() if world else None, "n_actors": len(actors),
           "classes": dict(Counter(a.get_class().get_name() for a in actors)), "n_static_mesh_actors": len(sma)}
    miss, dup, wrong_mesh, loc_err, rot_err, scale_err, col_err, bounds_fail = [], [], [], [], [], [], [], {}
    worst = {"nonnanite_render": 0.0, "nanite_fallback_geom": 0.0, "nanite_render_bounds": 0.0}
    nan_render = {}
    fb_cache = {}
    want_labels = set()
    for n, inst in enumerate(L["instances"]):
        lab = f"{inst['piece']}__{n:04d}"
        want_labels.add(lab)
        if labels.get(lab, 0) == 0:
            miss.append(lab)
            continue
        if labels[lab] > 1:
            dup.append(lab)
        a = by_label[lab]
        smc = a.static_mesh_component
        sm = smc.get_editor_property("static_mesh")
        if sm is None or sm.get_name() != inst["piece"]:
            wrong_mesh.append(lab)
            continue
        al = a.get_actor_location()
        w = (inst["loc"][0] * 100, -inst["loc"][1] * 100, inst["loc"][2] * 100)
        d = max(abs(al.x - w[0]), abs(al.y - w[1]), abs(al.z - w[2]))
        if d > 0.01:
            loc_err.append([lab, round(d, 4)])
        t = a.get_actor_transform()
        cols = ue_rot_cols(inst)
        rd = 0.0
        for j, ax in enumerate((V(1, 0, 0), V(0, 1, 0), V(0, 0, 1))):
            g = t.transform_direction(ax)
            rd = max(rd, abs(g.x - cols[j][0]), abs(g.y - cols[j][1]), abs(g.z - cols[j][2]))
        if rd > 1e-4:
            rot_err.append([lab, round(rd, 6)])
        sc = a.get_actor_scale3d()
        if max(abs(sc.x - inst["scale"][0]), abs(sc.y - inst["scale"][1]), abs(sc.z - inst["scale"][2])) > 1e-5:
            scale_err.append(lab)
        want = L["collision_classes"][inst["collision_class"]]
        got = {"pawn": resp(smc, CH.ECC_PAWN), "camera": resp(smc, CH.ECC_CAMERA), "visibility": resp(smc, CH.ECC_VISIBILITY)}
        enabled = enum_name(smc.get_collision_enabled())
        if want.get("no_collision"):
            if "no_collision" not in enabled:
                col_err.append([lab, enabled])
        elif any(got[k] != want[k] for k in got) or "no_collision" in enabled:
            col_err.append([lab, inst["collision_class"], got, enabled])
        o, e = a.get_actor_bounds(False)
        u = [o.x - e.x, o.y - e.y, o.z - e.z, o.x + e.x, o.y + e.y, o.z + e.z]
        au = A[inst["piece"]]
        if L["pieces"][inst["piece"]].get("nanite"):
            if inst["piece"] not in fb_cache:
                fb_cache[inst["piece"]] = vbox_ue_local(sm)
            exp = expected_box_ue(inst, au["lod0_vbox"])
            err = max(abs(p - q) for p, q in zip(world_of(a, fb_cache[inst["piece"]]), exp))
            worst["nanite_fallback_geom"] = max(worst["nanite_fallback_geom"], err)
            infl = max(abs(p - q) for p, q in zip(u, exp))
            worst["nanite_render_bounds"] = max(worst["nanite_render_bounds"], infl)
            nan_render[inst["piece"]] = max(nan_render.get(inst["piece"], 0.0), round(infl, 3))
        else:
            exp = expected_box_ue(inst, au["all_lod_vbox"])
            err = max(abs(p - q) for p, q in zip(u, exp))
            worst["nonnanite_render"] = max(worst["nonnanite_render"], err)
        if err > TOL_CM:
            bounds_fail[lab] = round(err, 3)
    piece_names = set(L["pieces"])
    extra = sorted(a.get_actor_label() for a in sma if a.get_actor_label() not in want_labels
                   and a.static_mesh_component.get_editor_property("static_mesh") is not None
                   and a.static_mesh_component.get_editor_property("static_mesh").get_name() in piece_names)
    other_sma = sorted(a.get_actor_label() for a in sma if a.get_actor_label() not in want_labels)
    per_piece_ok = Counter(i["piece"] for i in L["instances"]) == Counter(
        a.static_mesh_component.get_editor_property("static_mesh").get_name() for a in sma
        if a.get_actor_label() in want_labels and a.static_mesh_component.get_editor_property("static_mesh"))
    # engine-default materials on any component in the level
    eng = []
    for a in actors:
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            for k, m in enumerate(c.get_materials()):
                b = bad_material(m)
                if b:
                    eng.append([a.get_actor_label(), c.get_name(), k, b, bool(a.get_editor_property("hidden"))])
    res.update({"missing": miss, "duplicate_labels": dup, "wrong_mesh": wrong_mesh, "location_err": loc_err,
                "rotation_err": rot_err, "scale_err": scale_err, "collision_err": col_err,
                "bounds_fail_over_1cm": bounds_fail, "worst_cm": {k: round(v, 4) for k, v in worst.items()},
                "nanite_render_bounds_inflation_cm": dict(sorted(nan_render.items())),
                "extra_actors_of_layout_meshes": extra, "static_mesh_actors_not_in_layout": other_sma,
                "per_piece_counts_match": per_piece_ok, "engine_default_materials": eng,
                "n_instances": len(L["instances"])})
    visible_eng = [x for x in eng if not x[4]]
    res["passed"] = (loaded and not miss and not dup and not wrong_mesh and not loc_err and not rot_err and not scale_err
                     and not col_err and not bounds_fail and not extra and per_piece_ok and not visible_eng)
    return res, actors


# ------------------------------------------------------------------ 4 traversal
def trv_ignore(actors):
    # r6: the surface probes also ignore the tagged 1v1-only group (the north wall top blocker sits on Wall_N's top)
    return [a for a in actors if a.get_actor_label().startswith("TRV_") or "Boundary" in a.get_actor_label()
            or "Dojo/Boundary_1v1" in [str(t) for t in a.get_editor_property("tags")]]


def check_traversal(actors):
    by_label = {a.get_actor_label(): a for a in actors}
    ign = trv_ignore(actors)
    ctx = actors[0]
    rows, bad = {}, []
    for m in L["traversal_markers"]:
        a = by_label.get("TRV_" + m["name"])
        x0, x1, y0, y1, z0, z1 = m["box"]
        r = {"box": m["box"], "route": m["route"]}
        if a is None or a.get_class().get_name() != "LevelBlock_Traversable_C":
            r["error"] = "missing / wrong class"
            rows[m["name"]] = r
            bad.append(m["name"])
            continue
        # ledges: the four splines on the box top edges, normals outward
        want = {"Ledge_1": ((x0, y1), (x1, y1), (0, -1)), "Ledge_2": ((x0, y0), (x1, y0), (0, 1)),
                "Ledge_3": ((x0, y1), (x0, y0), (-1, 0)), "Ledge_4": ((x1, y1), (x1, y0), (1, 0))}
        err = 0.0
        sps = a.get_components_by_class(unreal.SplineComponent)
        for sp in sps:
            w = want.get(sp.get_name())
            if w is None:
                err = 1e9
                continue
            p0 = sp.get_location_at_spline_point(0, unreal.SplineCoordinateSpace.WORLD)
            p1 = sp.get_location_at_spline_point(1, unreal.SplineCoordinateSpace.WORLD)
            up = sp.get_up_vector_at_spline_point(0, unreal.SplineCoordinateSpace.WORLD)
            e0 = (w[0][0] * 100, -w[0][1] * 100)
            e1 = (w[1][0] * 100, -w[1][1] * 100)
            err = max(err, abs(p0.x - e0[0]), abs(p0.y - e0[1]), abs(p1.x - e1[0]), abs(p1.y - e1[1]),
                      abs(p0.z - z1 * 100), abs(p1.z - z1 * 100), 100 * abs(up.x - w[2][0]), 100 * abs(up.y - w[2][1]))   # normals in the UE frame
        cols = [{"trav": resp(c, CH.ECC_TRAVERSABLE) if hasattr(CH, "ECC_TRAVERSABLE") else None,
                 "pawn": resp(c, CH.ECC_PAWN), "vis": resp(c, CH.ECC_VISIBILITY), "cam": resp(c, CH.ECC_CAMERA)}
                for c in a.get_components_by_class(unreal.StaticMeshComponent)]
        # the climb surface under the marker's top: Pawn-profile line traces straight down at the centre and 4 points
        # inset 15 cm from each ledge; the surface top must sit within 3 cm of the marker top
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        pts = [(cx, cy), (x0 + 0.15, cy), (x1 - 0.15, cy), (cx, y0 + 0.15), (cx, y1 - 0.15)]
        if m["name"] == "Hall_Veranda":   # r6: a U-shaped deck round the hall body (the r5 centre probes hit the hall);
            # probe the deck itself: both side strips and the front strip, 15 cm and 50 cm in from the ledges
            pts = [(x0 + 0.15, cy), (x1 - 0.15, cy), (cx, y0 + 0.15), (x0 + 0.5, y0 + 0.5), (x1 - 0.5, y0 + 0.5),
                   (x0 + 0.5, y1 - 0.5), (x1 - 0.5, y1 - 0.5)]
        surf = []
        for (px, py) in pts:
            h = unreal.SystemLibrary.line_trace_single_by_profile(ctx, V(px * 100, -py * 100, z1 * 100 + 60),
                                                                   V(px * 100, -py * 100, z1 * 100 - 150), "Pawn", False,
                                                                   ign, unreal.DrawDebugTrace.NONE, True)
            hi = hit_info(h)
            surf.append({"at": [round(px, 3), round(py, 3)], "hit_z_m": round(hi["impact"][2] / 100, 4) if hi else None,
                         "actor": hi["actor"] if hi else None,
                         "d_top_cm": round(hi["impact"][2] - z1 * 100, 2) if hi else None})
        on = [s for s in surf if s["d_top_cm"] is not None and abs(s["d_top_cm"]) <= 3.0]
        r.update({"ledge_err_cm": round(err, 3), "n_ledges": len(sps), "hidden": bool(a.get_editor_property("hidden")),
                  "collision": cols, "surface": surf, "surface_hits_within_3cm": f"{len(on)}/{len(surf)}"})
        ok = (len(sps) == 4 and err <= TOL_CM and r["hidden"] and cols
              and all(c["pawn"] == "ignore" and c["vis"] == "ignore" and c["cam"] == "ignore" and c["trav"] in ("block", None)
                      for c in cols)
              and len(on) >= max(3, len(pts) - 2))
        r["ok"] = ok
        rows[m["name"]] = r
        if not ok:
            bad.append(m["name"])
    need = sorted({r["marker"] for r in L["climb_routes"] if r.get("marker")})
    miss = [n for n in need if n not in rows]
    names = {"TRV_" + m["name"] for m in L["traversal_markers"]}
    extra = sorted(a.get_actor_label() for a in actors if a.get_actor_label().startswith("TRV_") and a.get_actor_label() not in names)
    extra_cls = sorted(a.get_actor_label() for a in actors if a.get_class().get_name() == "LevelBlock_Traversable_C"
                       and a.get_actor_label() not in names)
    # hall landings: every placed SM_DKH_EaveLanding's top face must lie inside one marker's top rectangle at its height
    hall = []
    for n, inst in enumerate(L["instances"]):
        if inst["piece"] != "SM_DKH_EaveLanding":
            continue
        a = next((x for x in actors if x.get_actor_label() == f"{inst['piece']}__{n:04d}"), None)
        o, e = a.get_actor_bounds(False)
        top = [(o.x - e.x) / 100, (o.x + e.x) / 100, -(o.y + e.y) / 100, -(o.y - e.y) / 100]
        cover = []
        for m in L["traversal_markers"]:
            bx = m["box"]
            ox = min(bx[1], top[1]) - max(bx[0], top[0])
            oy = min(bx[3], top[3]) - max(bx[2], top[2])
            if ox > 0.3 and oy > 0.3:
                cover.append({"marker": m["name"], "marker_top": bx[5], "overlap_m": [round(ox, 3), round(oy, 3)],
                              "marker_ok": rows.get(m["name"], {}).get("ok")})
        hall.append({"instance": n, "render_box_xy_m": [round(v, 3) for v in top], "markers": cover,
                     "ok": any(c["marker_ok"] and abs(c["marker_top"] - 3.0) < 0.02 for c in cover)})
    return {"n_markers_layout": len(L["traversal_markers"]), "markers": rows, "bad": bad, "route_markers_needed": need,
            "route_markers_missing": miss, "trv_not_in_layout": extra, "traversable_blocks_not_in_layout": extra_cls,
            "hall_eave_landings": hall,
            "passed": not bad and not miss and not extra and not extra_cls and hall and all(h["ok"] for h in hall)}


# ------------------------------------------------------------------ 5 GASP forward trace + in-engine walk sweeps
def check_gasp(actors):
    tq = next(getattr(unreal.TraceTypeQuery, n) for n in dir(unreal.TraceTypeQuery) if n.upper() == "ECC_TRAVERSABLE")
    ctx = actors[0]
    rows, bad = {}, []
    for i, r in enumerate(L["climb_routes"]):
        if not r.get("marker") or not r.get("stance") or not r.get("face"):
            continue
        x, y = r["stance"]
        z = float(r.get("floor_z", 0.0)) * 100 + 86 + 1.9
        fx, fy = r["face"]
        h = unreal.SystemLibrary.capsule_trace_single(ctx, V(x * 100, -y * 100, z), V(x * 100 + fx * 75, -y * 100 - fy * 75, z),
                                                      30.0, 60.0, tq, False, [], unreal.DrawDebugTrace.NONE, True)
        hi = hit_info(h)
        ok = bool(hi and hi["actor"] == "TRV_" + r["marker"] and not hi["start_pen"])
        rows[f"{i:02d} {r['route']} {r['step']}"] = {"marker": r["marker"], "hit": hi, "ok": ok}
        if not ok:
            bad.append(f"{i:02d}")
    return {"routes": rows, "bad": bad, "passed": bool(rows) and not bad}


def check_walk(actors):
    """Pawn-profile capsule sweeps along every walk route, in the engine. Capsule r 30; its body band floor+47 .. +172
    (centre floor+109.5, half height 62.5); the floor follows a Pawn-profile line trace down at each 5 cm sample
    (step-ups <= 45 cm). 'leaves: open' routes are the BR passage: the hidden 1v1 ring is ignored there (as walk_check)."""
    ctx = actors[0]
    trv = [a for a in actors if a.get_actor_label().startswith("TRV_")]
    bnd = [a for a in actors if "Boundary" in a.get_actor_label()]
    out = {}
    for name, rt in L["walk_routes"].items():
        ign = trv + (bnd if rt.get("leaves") == "open" else [])
        floor = rt["floor_z"] * 100
        pts = rt["points"]
        block, n_samp, prev = None, 0, None
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            n = max(2, int(math.hypot(x1 - x0, y1 - y0) / 0.05))
            for k in range(n + 1):
                x, y = (x0 + (x1 - x0) * k / n) * 100, -(y0 + (y1 - y0) * k / n) * 100
                h = unreal.SystemLibrary.line_trace_single_by_profile(ctx, V(x, y, floor + 47), V(x, y, floor - 120), "Pawn",
                                                                       False, ign, unreal.DrawDebugTrace.NONE, True)
                hi = hit_info(h)
                if hi and not hi["start_pen"]:
                    floor = hi["impact"][2]
                c = V(x, y, floor + 109.5)
                if prev is not None:
                    s = unreal.SystemLibrary.capsule_trace_single_by_profile(ctx, prev, c, 30.0, 62.5, "Pawn", False, ign,
                                                                             unreal.DrawDebugTrace.NONE, True)
                    si = hit_info(s)
                    if si:
                        block = {"at_m": [round(x / 100, 2), round(-y / 100, 2)], "floor_m": round(floor / 100, 3), **si}
                        break
                prev = c
                n_samp += 1
            if block:
                break
        out[name] = {"clear": block is None, "block": block, "samples": n_samp, "end_floor_m": round(floor / 100, 3)}
    ctl = {k: v for k, v in out.items() if k.startswith("CONTROL")}
    rts = {k: v for k, v in out.items() if not k.startswith("CONTROL")}
    return {"routes": out, "controls_blocked": all(not v["clear"] for v in ctl.values()),
            "routes_clear": all(v["clear"] for v in rts.values()),
            "passed": all(not v["clear"] for v in ctl.values()) and all(v["clear"] for v in rts.values())}


# ------------------------------------------------------------------ 6 environment readback (for the colour diagnosis)
def check_env(actors):
    env = {}
    for a in actors:
        cls = a.get_class().get_name()
        if cls == "DirectionalLight":
            c = a.get_editor_property("directional_light_component")
            env["sun"] = {"lux": float(c.get_editor_property("intensity")), "use_temp": bool(c.get_editor_property("use_temperature")),
                          "kelvin": float(c.get_editor_property("temperature")),
                          "color": str(c.get_editor_property("light_color")), "pitch": a.get_actor_rotation().pitch}
        elif cls == "SkyLight":
            c = a.get_editor_property("light_component")
            env["skylight"] = {"intensity": float(c.get_editor_property("intensity")), "rtc": bool(c.get_editor_property("real_time_capture"))}
        elif cls == "SkyAtmosphere":
            f = a.get_component_by_class(unreal.SkyAtmosphereComponent).get_editor_property("sky_luminance_factor")
            env["sky_luminance_factor"] = [f.r, f.g, f.b]
        elif cls == "PostProcessVolume":
            s = a.get_editor_property("settings")
            ov = {}
            for nm in dir(s):
                if nm.startswith("override_"):
                    try:
                        if s.get_editor_property(nm):
                            ov[nm[9:]] = str(s.get_editor_property(nm[9:]))
                    except Exception:  # noqa: BLE001
                        pass
            env.setdefault("ppv", []).append({"label": a.get_actor_label(), "unbound": bool(a.get_editor_property("unbound")),
                                              "overrides": ov})
        elif cls == "PointLight":
            env["point_lights"] = env.get("point_lights", 0) + 1
    return env



# ================================================================== round-5 gates (independent)
DEC_SRC = json.loads((ROOT / "WorkFiles/dojo/build/dressing/decals.json").read_text(encoding="utf-8"))
COMPOUND = (-1.0, 45.0, -1.0, 37.0)     # outer wall line incl. the wall thickness (Blender m): x0, x1, y0, y1


def bl_of(v):
    return [round(v.x / 100, 3), round(-v.y / 100, 3), round(v.z / 100, 3)]


def inside_compound(x, y):
    return COMPOUND[0] < x < COMPOUND[1] and COMPOUND[2] < y < COMPOUND[3]




def textures_of(m):
    """[(param or 'root', texture path)] for a material / instance chain: every MI's texture overrides (nearest first)
    plus the root Material's used textures (its defaults)."""
    out, seen, x = [], set(), m
    while isinstance(x, unreal.MaterialInstance):
        for tp in x.get_editor_property("texture_parameter_values"):
            nm = str(tp.get_editor_property("parameter_info").get_editor_property("name"))
            v = tp.get_editor_property("parameter_value")
            if nm not in seen:
                seen.add(nm)
                out.append([nm, v.get_path_name() if v else None])
        x = x.get_editor_property("parent")
    if x is not None:
        try:
            out += [["root", t.get_path_name()] for t in unreal.MaterialEditingLibrary.get_used_textures(x)]
        except Exception as ex:  # noqa: BLE001
            out.append(["root", f"err {ex}"])
    return out

# ------------------------------------------------------------------ 8 lamps / lights: street lamps only outside
def check_lamps(actors):
    rows, lights, bad = [], [], []
    for a in actors:
        cls = a.get_class().get_name()
        if isinstance(a, unreal.StaticMeshActor):
            sm = a.static_mesh_component.get_editor_property("static_mesh")
            nm = sm.get_name() if sm else ""
            if any(k in nm.lower() for k in ("lamp", "lantern", "light", "pole", "utility", "transformer")):
                o, e = a.get_actor_bounds(False)
                box = [round((o.x - e.x) / 100, 3), round(-(o.y + e.y) / 100, 3), round((o.x + e.x) / 100, 3), round(-(o.y - e.y) / 100, 3)]
                l = bl_of(a.get_actor_location())
                box_in = (inside_compound(box[0], box[1]) or inside_compound(box[2], box[3])
                          or inside_compound(box[0], box[3]) or inside_compound(box[2], box[1]))
                r = {"label": a.get_actor_label(), "mesh": nm, "loc_bl_m": l, "xy_box_bl_m": box,
                     "loc_inside_compound": inside_compound(l[0], l[1]), "box_touches_compound": box_in,
                     "hidden": bool(a.get_editor_property("hidden"))}
                why = []
                if "StreetLamp" in nm and (r["loc_inside_compound"] or box_in):
                    why.append("street lamp inside the compound")
                if "LanternShort" in nm:
                    why.append("short lantern placed")
                if ("Lantern" in nm or "StreetLamp" in nm) and 16.0 <= l[0] <= 28.0 and -3.0 <= l[1] <= 8.0:
                    why.append("lantern / street lamp at the gate")
                r["fail"] = why
                if why:
                    bad.append(r["label"])
                rows.append(r)
        if "Light" in cls and cls not in ("DirectionalLight", "SkyLight"):
            lights.append({"label": a.get_actor_label(), "class": cls, "loc_bl_m": bl_of(a.get_actor_location()),
                           "hidden": bool(a.get_editor_property("hidden"))})
    orphan = []
    for li in lights:
        near = [r for r in rows if max(abs(li["loc_bl_m"][0] - r["loc_bl_m"][0]), abs(li["loc_bl_m"][1] - r["loc_bl_m"][1])) <= 1.0]
        li["on_mesh"] = near[0]["label"] if near else None
        li["street_lamp_light_inside"] = ("StreetLamp" in li["label"]) and inside_compound(li["loc_bl_m"][0], li["loc_bl_m"][1])
        if not near and not li["label"].startswith("Light_Fill_"):
            orphan.append(li["label"])
    lay_lights = {l["name"]: l for l in L["lights"]}
    got = {li["label"]: li for li in lights}
    miss = sorted(set(lay_lights) - set(got))
    extra = sorted(set(got) - set(lay_lights))
    loc_err = {}
    for k, l in lay_lights.items():
        if k in got:
            d = max(abs(got[k]["loc_bl_m"][i] - l["loc"][i]) for i in range(3))
            if d > 0.002:
                loc_err[k] = round(d, 4)
    lay = Counter(i["piece"] for i in L["instances"])
    street = [r for r in rows if "StreetLamp" in r["mesh"]]
    res = {"lamp_like_actors": rows, "street_lamps": street, "lights": lights, "n_lights": len(lights),
           "orphan_lights": orphan, "bad": bad, "layout_lights_missing": miss, "lights_not_in_layout": extra,
           "light_loc_err_m": loc_err,
           "street_lamp_lights_inside": [li["label"] for li in lights if li["street_lamp_light_inside"]],
           "layout_counts": {k: lay.get(k, 0) for k in L["pieces"] if any(s in k for s in ("Lamp", "Lantern", "Pole", "Utility"))}}
    res["passed"] = bool(not bad and not orphan and not miss and not extra and not loc_err and street
                         and not res["street_lamp_lights_inside"]
                         and res["layout_counts"].get("SM_DKP_Stone_LanternShort", 0) == 0)
    return res


# ------------------------------------------------------------------ 9 project assets: retired meshes gone
def check_assets():
    ar = unreal.EditorAssetLibrary
    retired = {k: ar.does_asset_exist(v) for k, v in L.get("retired_meshes", {}).items()}
    lst = [p for p in ar.list_assets("/Game/DojoKit", recursive=True, include_folder=False) if "/SM_" in p]
    names = sorted({p.split("/")[-1].split(".")[0] for p in lst})
    return {"retired_still_present": [k for k, v in retired.items() if v], "n_sm_assets": len(names),
            "sm_assets_not_in_layout": [n for n in names if n not in L["pieces"]], "passed": not any(retired.values())}


# ------------------------------------------------------------------ 10 grey-box left: only SM_DGB_Tree + the hidden 1v1 boundary
def check_greybox(actors):
    rows, bad = [], []
    for a in actors:
        if not isinstance(a, unreal.StaticMeshActor):
            continue
        sm = a.static_mesh_component.get_editor_property("static_mesh")
        nm = sm.get_name() if sm else ""
        pth = sm.get_path_name() if sm else ""
        if nm.startswith("SM_DGB_") or "/Greybox/" in pth:
            smc = a.static_mesh_component
            o, e = a.get_actor_bounds(False)
            hid = bool(a.get_editor_property("hidden"))
            r = {"label": a.get_actor_label(), "mesh": nm, "path": pth, "hidden_in_game": hid,
                 "comp_visible": bool(smc.get_editor_property("visible")),
                 "pawn": resp(smc, CH.ECC_PAWN), "collision": enum_name(smc.get_collision_enabled()),
                 "box_bl_m": [round((o.x - e.x) / 100, 2), round(-(o.y + e.y) / 100, 2), round((o.z - e.z) / 100, 2),
                              round((o.x + e.x) / 100, 2), round(-(o.y - e.y) / 100, 2), round((o.z + e.z) / 100, 2)]}
            r["allowed"] = nm == "SM_DGB_Tree" or (nm == "SM_DGB_Boundary_1v1" and hid)
            rows.append(r)
            if not r["allowed"]:
                bad.append(r)
    bnd = [r for r in rows if r["mesh"] == "SM_DGB_Boundary_1v1"]
    return {"greybox_actors": rows, "not_allowed": bad, "counts": dict(Counter(r["mesh"] for r in rows)),
            "boundary": bnd,
            "passed": bool(not bad and len(bnd) >= 1 and all(b["hidden_in_game"] and b["pawn"] == "block" for b in bnd))}


# ------------------------------------------------------------------ 13 closed rear alley without the hidden ring
def sweep(actors, rt, ign):
    ctx = actors[0]
    floor = rt["floor_z"] * 100
    pts = rt["points"]
    prev = None
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = max(2, int(math.hypot(x1 - x0, y1 - y0) / 0.05))
        for k in range(n + 1):
            x, y = (x0 + (x1 - x0) * k / n) * 100, -(y0 + (y1 - y0) * k / n) * 100
            hi = hit_info(unreal.SystemLibrary.line_trace_single_by_profile(ctx, V(x, y, floor + 47), V(x, y, floor - 120), "Pawn",
                                                                            False, ign, unreal.DrawDebugTrace.NONE, True))
            if hi and not hi["start_pen"]:
                floor = hi["impact"][2]
            c = V(x, y, floor + 109.5)
            if prev is not None:
                si = hit_info(unreal.SystemLibrary.capsule_trace_single_by_profile(ctx, prev, c, 30.0, 62.5, "Pawn", False, ign,
                                                                                     unreal.DrawDebugTrace.NONE, True))
                if si:
                    return {"at_m": [round(x / 100, 2), round(-y / 100, 2)], **si}
            prev = c
    return None


def check_alley(actors):
    """The alley-fence CONTROLs swept with the hidden 1v1 ring IGNORED too: the rear alley must be closed by the fence
    kit's own collision. Plus the 1v1 ring CONTROL swept normally (it must hit the Boundary)."""
    trv = [a for a in actors if a.get_actor_label().startswith("TRV_")]
    bnd = [a for a in actors if "Boundary" in a.get_actor_label()]
    out = {}
    for name, rt in L["walk_routes"].items():
        if "alley" in name.lower():
            b = sweep(actors, rt, trv + bnd)
            out[name] = {"blocked_without_boundary": b is not None, "block": b}
    ring = {k: sweep(actors, rt, trv) for k, rt in L["walk_routes"].items() if k.startswith("CONTROL_1v1")}
    ring_ok = bool(ring) and all(v is not None and v.get("actor") and "Boundary" in v["actor"] for v in ring.values())
    return {"alley_routes": out, "ring_controls": ring, "ring_blocked_by_boundary": ring_ok,
            "passed": bool(out) and all(v["blocked_without_boundary"] for v in out.values()) and ring_ok}


# ------------------------------------------------------------------ 14 decals (vs the dressing track's decals.json)
def check_decals(actors):
    got = {a.get_actor_label()[4:]: a for a in actors
           if a.get_class().get_name() == "DecalActor" and a.get_actor_label().startswith("DKD_")}
    other_decals = [a.get_actor_label() for a in actors if a.get_class().get_name() == "DecalActor"
                    and not a.get_actor_label().startswith("DKD_")]
    src = {p["id"]: p for p in DEC_SRC["placements"]}
    lay = {d["id"]: d for d in L.get("decals", [])}
    rows, bad, worst = {}, [], {"loc_cm": 0.0, "axis": 0.0, "size_cm": 0.0}
    mats = {}
    for k, p in src.items():
        a = got.get(k)
        r = {"material_src": p["material"], "in_layout": k in lay, "source": p.get("source", "")[:80]}
        if a is None:
            r["present"] = False
            rows[k] = r
            continue
        r["present"] = True
        dc = a.get_editor_property("decal")
        m = dc.get_decal_material()
        chain = mat_root(m) if m else [None]
        r["material"] = m.get_name() if m else None
        r["chain"] = chain
        mats[r["material"]] = chain
        c, nrm, right = p["centre"], p["normal"], p["right"]
        loc = a.get_actor_location()
        el = max(abs(loc.x - c[0] * 100), abs(loc.y + c[1] * 100), abs(loc.z - c[2] * 100))
        rot = a.get_actor_rotation()
        fwd = unreal.MathLibrary.get_forward_vector(rot)
        up = unreal.MathLibrary.get_up_vector(rot)
        want_x = (-nrm[0], nrm[1], -nrm[2])          # local +X = -normal (UE frame: y flips)
        ea = max(abs(fwd.x - want_x[0]), abs(fwd.y - want_x[1]), abs(fwd.z - want_x[2]))
        dot_right = up.x * right[0] - up.y * right[1] + up.z * right[2]
        sz = dc.get_editor_property("decal_size")
        exp_sz = (p["depth_m"] * 50, p["size_m"][1] * 50, p["size_m"][0] * 50)
        es = max(abs(sz.x - exp_sz[0]), abs(sz.y - exp_sz[1]), abs(sz.z - exp_sz[2]))
        r.update({"loc_err_cm": round(el, 4), "x_axis_err": round(ea, 6), "z_dot_right": round(dot_right, 5),
                  "size_cm": [round(sz.x, 3), round(sz.y, 3), round(sz.z, 3)], "size_err_cm": round(es, 4),
                  "hidden": bool(a.get_editor_property("hidden"))})
        worst["loc_cm"] = max(worst["loc_cm"], el)
        worst["axis"] = max(worst["axis"], ea)
        worst["size_cm"] = max(worst["size_cm"], es)
        why = []
        if r["material"] != p["material"]:
            why.append("material != decals.json")
        if chain[-1] is None or not chain[-1].endswith("M_DKD_Decal_Master") or any(x and x.startswith("/Engine/") for x in chain):
            why.append("material chain not M_DKD_Decal_Master")
        if el > 1.0 or ea > 1e-3 or abs(abs(dot_right) - 1) > 1e-3 or es > 0.5 or r["hidden"]:
            why.append("frame")
        r["fail"] = why
        if why:
            bad.append(k)
        rows[k] = r
    absent = sorted(k for k, r in rows.items() if not r["present"])
    absent_in_layout = sorted(k for k in absent if rows[k]["in_layout"])
    extra = sorted(set(got) - set(src))
    mat_tex = {}
    for nm, chain in mats.items():
        mat_tex[nm] = [t for _p, t in textures_of(unreal.load_asset(chain[0])) if t]
    eng_tex = {k: [t for t in v if t.startswith("/Engine/")] for k, v in mat_tex.items()}
    return {"n_decals_json": len(src), "n_layout": len(lay), "n_actors": len(got), "other_decal_actors": other_decals,
            "absent_from_level": absent, "absent_but_in_layout": absent_in_layout,
            "absent_sources": {k: rows[k]["source"] for k in absent}, "extra": extra, "bad": bad,
            "worst": {k: round(v, 5) for k, v in worst.items()}, "material_textures": mat_tex,
            "engine_textures": {k: v for k, v in eng_tex.items() if v}, "decals": rows,
            "passed_layout": bool(not absent_in_layout and not bad and not extra and not any(eng_tex.values())),
            "passed_every_decals_json": bool(not absent and not bad and not extra)}


# ------------------------------------------------------------------ 15 emblem: textures exported, crest scan
def export_tex(tex, name):
    d = VD / "emblem_export"
    d.mkdir(exist_ok=True)
    fn = d / f"{name}.png"
    t = unreal.AssetExportTask()
    t.set_editor_property("object", tex)
    t.set_editor_property("filename", str(fn))
    t.set_editor_property("automated", True)
    t.set_editor_property("prompt", False)
    t.set_editor_property("replace_identical", True)
    ok = unreal.Exporter.run_asset_export_task(t)
    return {"ok": bool(ok), "file": str(fn), "exists": fn.exists()}


CREST_WORDS = ("emblem", "crest", "kamon", "logo", "sigil", "insignia", "badge", "symbol", "mon_", "_mon", "clan", "seal")


def check_emblem(actors):
    use, mat_of = {}, {}
    for a in actors:
        mats = []
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            mats += [m for m in c.get_materials() if m]
        if a.get_class().get_name() == "DecalActor":
            m = a.get_editor_property("decal").get_decal_material()
            if m:
                mats.append(m)
        for m in mats:
            p = m.get_path_name()
            if p not in mat_of:
                mat_of[p] = [t for _p, t in textures_of(m) if t]
            for t in mat_of[p]:
                use.setdefault(t, set()).add(a.get_actor_label())
    crest_tex_in_level = {t: sorted(v)[:40] for t, v in use.items()
                          if any(w in t.split("/")[-1].lower() for w in CREST_WORDS)}
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    crest_assets = []
    for ad in ar.get_assets_by_path("/Game", recursive=True):
        try:
            cls = str(ad.asset_class_path.asset_name)
        except Exception:  # noqa: BLE001
            cls = str(ad.asset_class)
        nm = str(ad.asset_name)
        if any(w in nm.lower() for w in CREST_WORDS):
            crest_assets.append([str(ad.package_name), cls])
    plaques, exported = {}, {}
    for a in actors:
        if not isinstance(a, unreal.StaticMeshActor):
            continue
        sm = a.static_mesh_component.get_editor_property("static_mesh")
        if sm is None or "Emblem" not in sm.get_name():
            continue
        mats = a.static_mesh_component.get_materials()
        pl = {"mesh": sm.get_name(), "loc_bl_m": bl_of(a.get_actor_location()),
              "materials": [m.get_path_name() if m else None for m in mats],
              "chains": [mat_root(m) if m else None for m in mats],
              "textures": [mat_of.get(m.get_path_name(), []) if m else [] for m in mats],
              "texture_params": [textures_of(m) if m else [] for m in mats]}
        plaques[a.get_actor_label()] = pl
        for tl in pl["textures"]:
            for t in tl:
                if t in exported or t.startswith("err"):
                    continue
                tex = unreal.load_asset(t)
                info = {"class": tex.get_class().get_name(), "srgb": bool(tex.get_editor_property("srgb")),
                        "size": [int(tex.blueprint_get_size_x()), int(tex.blueprint_get_size_y())]}
                try:
                    info["import_source"] = tex.get_editor_property("asset_import_data").get_first_filename()
                except Exception as ex:  # noqa: BLE001
                    info["import_source"] = f"err {ex}"
                if "emblem" in t.split("/")[-1].lower():
                    info["export"] = export_tex(tex, t.split(".")[-1])
                exported[t] = info
    return {"plaques": plaques, "plaque_textures": exported,
            "emblem_textures_used_by": {t: sorted(v) for t, v in use.items() if "emblem" in t.lower()},
            "crest_like_textures_in_level": crest_tex_in_level, "crest_like_assets_in_project": crest_assets,
            "n_level_textures": len(use), "level_textures": sorted(use)}


# ------------------------------------------------------------------ 16 the 1v1-only group: separable (r6)
def check_group(actors):
    """Every 1v1-only piece (layout_outside.json onev1_only: 4 visible fences + 9 invisible blockers) and the grey-box
    ring carry the actor tag and the Outliner folder 'Dojo/Boundary_1v1'; nothing else does; the invisible ones are
    hidden in game, Pawn block, Camera / Visibility ignore, no shadow; the fences are visible and Pawn block."""
    LO = json.loads((ROOT / "WorkFiles/dojo/build/outside/layout_outside.json").read_text(encoding="utf-8"))["onev1_only"]
    tag = LO["ue_tag"]
    want_vis = {v["piece"] for v in LO["visible"]}
    want_inv = {v["piece"] for v in LO["invisible"]} | {"SM_DGB_Boundary_1v1"}
    want_inst = {f"{i['piece']}__{n:04d}" for n, i in enumerate(L["instances"]) if i["piece"] in want_vis | want_inv}
    rows, bad = {}, []
    tagged = set()
    for a in actors:
        tags = [str(t) for t in a.get_editor_property("tags")]
        lab = a.get_actor_label()
        folder = str(a.get_folder_path())
        if tag in tags or lab in want_inst:
            smc = a.get_component_by_class(unreal.StaticMeshComponent)
            sm = smc.get_editor_property("static_mesh") if smc else None
            nm = sm.get_name() if sm else None
            r = {"tagged": tag in tags, "folder": folder, "mesh": nm, "hidden_in_game": bool(a.get_editor_property("hidden")),
                 "pawn": resp(smc, CH.ECC_PAWN) if smc else None, "camera": resp(smc, CH.ECC_CAMERA) if smc else None,
                 "visibility": resp(smc, CH.ECC_VISIBILITY) if smc else None,
                 "cast_shadow": bool(smc.get_editor_property("cast_shadow")) if smc else None}
            why = []
            if tag in tags:
                tagged.add(lab)
            if lab not in want_inst:
                why.append("tagged but not a 1v1-only piece")
            if tag not in tags:
                why.append("not tagged")
            if folder != tag:
                why.append("folder")
            if nm in want_inv and not (r["hidden_in_game"] and r["pawn"] == "block" and r["camera"] == "ignore"
                                       and r["visibility"] == "ignore" and (not r["cast_shadow"] or nm == "SM_DGB_Boundary_1v1")):
                why.append("invisible blocker setup")
            if nm in want_vis and (r["hidden_in_game"] or r["pawn"] != "block"):
                why.append("visible fence setup")
            r["fail"] = why
            if why:
                bad.append(lab)
            rows[lab] = r
    return {"tag": tag, "n_expected": len(want_inst), "n_tagged": len(tagged), "expected": sorted(want_inst),
            "missing": sorted(want_inst - tagged), "actors": rows, "bad": bad,
            "passed": bool(want_inst) and tagged == want_inst and not bad}


def main():
    t0 = time.time()
    rep = {"engine": unreal.SystemLibrary.get_engine_version(), "verifier": "independent r6"}
    try:
        rep["1_meshes"] = check_meshes()
        rep["3_level"], actors = check_level()
        rep["0_gameplay"] = check_gameplay()
        rep["4_traversal"] = check_traversal(actors)
        rep["5_gasp_trace"] = check_gasp(actors)
        rep["6_walk_in_engine"] = check_walk(actors)
        rep["7_env"] = check_env(actors)
        rep["8_lamps"] = check_lamps(actors)
        rep["9_assets"] = check_assets()
        rep["10_greybox"] = check_greybox(actors)
        rep["13_alley_ring"] = check_alley(actors)
        rep["14_decals"] = check_decals(actors)
        rep["15_emblem"] = check_emblem(actors)
        rep["16_group_1v1"] = check_group(actors)
        rep["gates"] = {k: bool(rep[k]["passed"]) for k in ("0_gameplay", "1_meshes", "3_level", "4_traversal",
                                                           "5_gasp_trace", "6_walk_in_engine", "8_lamps", "9_assets",
                                                           "10_greybox", "13_alley_ring", "16_group_1v1")}
        rep["gates"]["14_decals_layout"] = bool(rep["14_decals"]["passed_layout"])
        rep["gates"]["14_decals_every_json"] = bool(rep["14_decals"]["passed_every_decals_json"])
    except Exception:  # noqa: BLE001
        rep["error"] = traceback.format_exc()[-4000:]
    rep["sec"] = round(time.time() - t0, 1)
    (VD / "ue_verify.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
    unreal.log(f"V6_VERIFY_DONE gates={rep.get('gates')} error={'error' in rep}")


main()
