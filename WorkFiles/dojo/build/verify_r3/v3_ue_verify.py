"""VERIFY r3 (independent verifier), Unreal side. pythonscript commandlet, -nullrhi, a FRESH process, READ-ONLY: nothing
is saved; the only file written is WorkFiles/dojo/build/verify_r3/ue_verify.json.

Truth sources: layout_showcase.json (instances, markers, routes) and verify_r3/fbx_audit.json (this verifier's own
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
VD = ROOT / "WorkFiles" / "dojo" / "build" / "verify_r3"
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
    res["passed"] = res["default_map_ok"] and res["pawn_ok"] and (res["global_gm_ok"] or (ov and ov.get_name() == "GM_Dojo_C"))
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
    prop_kits = ("taiko", "training", "stone", "modern")
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
    return [a for a in actors if a.get_actor_label().startswith("TRV_") or "Boundary" in a.get_actor_label()]


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
              and len(on) >= 3)
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


# ------------------------------------------------------------------ 8 lamps (user 2026-09-28: drop the invented lamps)
def check_lamps(actors):
    """Courtyard interior = Blender X 0..44, Y 0..36 (spec). No street lamp (A or B) anywhere with its location inside
    the compound's outer wall line (X -1..45, Y -1..37); no short lantern placed anywhere; no lantern of any kind in the
    gate zone (X 16..28, Y -1..8). Also lists every light actor and every lantern / lamp mesh actor with its position."""
    rows, lights, bad = [], [], []
    for a in actors:
        cls = a.get_class().get_name()
        l = a.get_actor_location()
        bx, by, bz = l.x / 100, -l.y / 100, l.z / 100
        if isinstance(a, unreal.StaticMeshActor):
            sm = a.static_mesh_component.get_editor_property("static_mesh")
            nm = sm.get_name() if sm else ""
            if any(k in nm for k in ("Lamp", "Lantern", "lamp", "lantern")):
                # use the world bounds too (a lamp standing on the wall line)
                o, e = a.get_actor_bounds(False)
                box = [round((o.x - e.x) / 100, 3), round(-(o.y + e.y) / 100, 3), round((o.x + e.x) / 100, 3), round(-(o.y - e.y) / 100, 3)]
                inside = -1.0 < bx < 45.0 and -1.0 < by < 37.0
                r = {"label": a.get_actor_label(), "mesh": nm, "loc_bl_m": [round(bx, 3), round(by, 3), round(bz, 3)],
                     "xy_box_bl_m": box, "inside_compound": inside, "hidden": bool(a.get_editor_property("hidden"))}
                why = []
                if "StreetLamp" in nm and inside:
                    why.append("street lamp inside the compound")
                if "LanternShort" in nm:
                    why.append("short lantern placed")
                if "Lantern" in nm and 16.0 <= bx <= 28.0 and -1.0 <= by <= 8.0:
                    why.append("lantern at the gate")
                r["fail"] = why
                if why:
                    bad.append(r["label"])
                rows.append(r)
        if "Light" in cls and cls not in ("DirectionalLight", "SkyLight"):
            lights.append({"label": a.get_actor_label(), "class": cls, "loc_bl_m": [round(bx, 3), round(by, 3), round(bz, 3)]})
    # every light must sit on a placed lamp/lantern mesh (within 1 m), i.e. no orphan light left where a lamp was dropped
    orphan = []
    for li in lights:
        near = [r for r in rows if max(abs(li["loc_bl_m"][0] - r["loc_bl_m"][0]), abs(li["loc_bl_m"][1] - r["loc_bl_m"][1])) <= 1.0]
        li["on_mesh"] = near[0]["label"] if near else None
        if not near:
            orphan.append(li["label"])
    lay = Counter(i["piece"] for i in L["instances"])
    res = {"lamp_actors": rows, "lights": lights, "n_lights": len(lights), "orphan_lights": orphan, "bad": bad,
           "layout_counts": {k: lay.get(k, 0) for k in L["pieces"] if "Lamp" in k or "Lantern" in k}}
    res["passed"] = not bad and not orphan and res["layout_counts"].get("SM_DKP_Stone_LanternShort", 0) == 0
    return res


# ------------------------------------------------------------------ 9 project assets: retired meshes gone, spares present
def check_assets():
    ar = unreal.EditorAssetLibrary
    retired = {k: ar.does_asset_exist(v) for k, v in L.get("retired_meshes", {}).items()}
    lst = [p for p in ar.list_assets("/Game/DojoKit", recursive=True, include_folder=False) if "/SM_" in p]
    names = sorted({p.split("/")[-1].split(".")[0] for p in lst})
    not_in_layout = [n for n in names if n not in L["pieces"]]
    return {"retired_still_present": [k for k, v in retired.items() if v], "n_sm_assets": len(names),
            "sm_assets_not_in_layout": not_in_layout, "passed": not any(retired.values())}


def main():
    t0 = time.time()
    rep = {"engine": unreal.SystemLibrary.get_engine_version(), "verifier": "independent r3"}
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
        rep["gates"] = {k: bool(rep[k]["passed"]) for k in ("0_gameplay", "1_meshes", "3_level", "4_traversal",
                                                           "5_gasp_trace", "6_walk_in_engine", "8_lamps")}
    except Exception:  # noqa: BLE001
        rep["error"] = traceback.format_exc()[-4000:]
    rep["sec"] = round(time.time() - t0, 1)
    (VD / "ue_verify.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
    unreal.log(f"V3_VERIFY_DONE gates={rep.get('gates')} error={'error' in rep}")


main()
