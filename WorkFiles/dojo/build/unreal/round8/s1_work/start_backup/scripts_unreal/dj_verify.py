"""DojoLab verify (pythonscript commandlet, -nullrhi, a FRESH process, read-only): re-check what was SAVED.

Gates (counts come from layout.json / blender_bounds.json / the exports on disk, never constants):
 1 meshes      one static mesh per exported SM_DGB_*.fbx; convex hulls == Blender UCX count, no other simple collision;
               LOD0 triangles == Blender; every slot holds the instance named like the slot (parent M_DGB_FlatMaster)
 2 level       L_Dojo loads; one mesh actor per layout.json instance with the right mesh; actor count; bounds of every mesh
               actor == the Blender Assembly bounds converted (1 cm); collision responses per class (Pawn / Camera /
               Visibility), the 1v1 boundary hidden in game and Pawn-only
 3 traversal   one LevelBlock_Traversable per layout.json marker, hidden in game, collision = Traversable only, its four
               ledge splines on the marker box's top edges with outward normals; every climb route's marker present
 4 gameplay    project default game mode GM_Dojo; its default pawn is GASP's SandboxCharacter_CMC; the level's world
               settings use GM_Dojo, KillZ -1000; PlayerStart P1 / P2 at the spec spawns facing each other; the pawn's
               hard /Game dependencies all exist
 5 environment sun direction = layout.json sun, SkyAtmosphere, SkyLight real-time capture, height fog, unbound PPV, cameras
Result: WorkFiles/dojo/build/unreal/verify.json
"""
import json
import sys
import time
import traceback
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unreal  # noqa: E402
import dj_common as C  # noqa: E402

EAL = unreal.EditorAssetLibrary
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
AR = unreal.AssetRegistryHelpers.get_asset_registry()
CH = unreal.CollisionChannel
TOL = 1.0


def resp(comp, ch):
    return str(comp.get_collision_response_to_channel(ch)).split(".")[-1].split(":")[0].replace("ECR_", "").lower()


def gate_meshes(bl):
    out, ok = {}, True
    for name, p in sorted(bl["pieces"].items()):
        m = unreal.load_asset(f"{C.MESH_DEST}/{name}")
        if not isinstance(m, unreal.StaticMesh):
            out[name] = {"error": "missing"}
            ok = False
            continue
        agg = m.get_editor_property("body_setup").get_editor_property("agg_geom")
        e = {"convex": len(agg.get_editor_property("convex_elems")), "ucx_blender": len(p["ucx"]),
             "other_simple": sum(len(agg.get_editor_property(k)) for k in ("box_elems", "sphere_elems", "sphyl_elems")),
             "tris_lod0": int(m.get_num_triangles(0)), "tris_blender": p["tris"], "slots": {}}
        for s in m.get_editor_property("static_materials"):
            mi = s.get_editor_property("material_interface")
            parent = mi.get_editor_property("parent").get_name() if isinstance(mi, unreal.MaterialInstanceConstant) else None
            e["slots"][str(s.get_editor_property("material_slot_name"))] = [mi.get_name() if mi else None, parent]
        e["ok"] = (e["convex"] == e["ucx_blender"] and e["other_simple"] == 0 and e["tris_lod0"] == e["tris_blender"]
                   and sorted(e["slots"]) == sorted(p["slots"])
                   and all(v[0] == k and v[1] == "M_DGB_FlatMaster" for k, v in e["slots"].items()))
        ok &= e["ok"]
        out[name] = e
    return {"meshes": out, "n": len(out), "n_exported": C.n_meshes(), "passed": ok and len(out) == C.n_meshes()}


def gate_level(layout, bl):
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    loaded = les.load_level(C.LEVEL)
    actors = EAS.get_all_level_actors()
    by_label = {a.get_actor_label(): a for a in actors}
    res = {"loaded": bool(loaded), "n_actors": len(actors), "classes": dict(Counter(a.get_class().get_name() for a in actors))}
    rows, worst, missing, wrong, bad_col = {}, 0.0, [], [], []
    classes = layout["collision_classes"]
    per_class = Counter()
    for n, inst in enumerate(layout["instances"]):
        lab = f"{inst['piece']}__{n:03d}"
        a = by_label.get(lab)
        if a is None:
            missing.append(lab)
            continue
        smc = a.static_mesh_component
        sm = smc.get_editor_property("static_mesh")
        if sm is None or sm.get_name() != inst["piece"]:
            wrong.append(lab)
        cls = inst["collision_class"]
        per_class[cls] += 1
        want = classes[cls]
        got = {"pawn": resp(smc, CH.ECC_PAWN), "camera": resp(smc, CH.ECC_CAMERA), "visibility": resp(smc, CH.ECC_VISIBILITY)}
        hidden = bool(a.get_editor_property("hidden"))
        if any(got[k] != want[k] for k in got) or hidden != bool(want.get("hidden_in_game", False)):
            bad_col.append({"label": lab, "class": cls, "got": got, "hidden": hidden})
        if cls == "boundary" and resp(smc, CH.ECC_WORLD_DYNAMIC) != "ignore":
            bad_col.append({"label": lab, "class": cls, "world_dynamic": resp(smc, CH.ECC_WORLD_DYNAMIC)})
        o, e = a.get_actor_bounds(False)
        u = [o.x - e.x, o.y - e.y, o.z - e.z, o.x + e.x, o.y + e.y, o.z + e.z]
        b = bl["instances"][str(n)]
        wmin, wmax = C.bbox_bl_to_ue(b["min"], b["max"])
        err = max(abs(p - q) for p, q in zip(u, wmin + wmax))
        worst = max(worst, err)
        rows[n] = err
    n_mesh_actors = sum(1 for a in actors if a.get_class().get_name() == "StaticMeshActor")
    res.update({"missing": missing, "wrong_mesh": wrong, "collision_errors": bad_col, "per_class": dict(per_class),
                "n_mesh_actors": n_mesh_actors, "n_instances": len(layout["instances"]),
                "bounds_max_err_cm": round(worst, 4), "bounds_failures": [k for k, v in rows.items() if v > TOL]})
    res["passed"] = (bool(loaded) and not missing and not wrong and not bad_col and not res["bounds_failures"]
                     and n_mesh_actors == len(layout["instances"]))
    return res, actors


def gate_traversal(layout, actors):
    cls_name = "LevelBlock_Traversable_C"
    by_label = {a.get_actor_label(): a for a in actors}
    rows, bad = {}, []
    for m in layout["traversal_markers"]:
        a = by_label.get("TRV_" + m["name"])
        if a is None or a.get_class().get_name() != cls_name:
            bad.append(("missing_or_wrong_class", m["name"]))
            continue
        x0, x1, y0, y1, z0, z1 = m["box"]
        want = {"Ledge_1": [x0 * 100, -y1 * 100, x1 * 100, -y1 * 100, (0, -1)],
                "Ledge_2": [x0 * 100, -y0 * 100, x1 * 100, -y0 * 100, (0, 1)],
                "Ledge_3": [x0 * 100, -y1 * 100, x0 * 100, -y0 * 100, (-1, 0)],
                "Ledge_4": [x1 * 100, -y1 * 100, x1 * 100, -y0 * 100, (1, 0)]}
        err = 0.0
        splines = a.get_components_by_class(unreal.SplineComponent)
        for sp in splines:
            w = want.get(sp.get_name())
            p0 = sp.get_location_at_spline_point(0, unreal.SplineCoordinateSpace.WORLD)
            p1 = sp.get_location_at_spline_point(1, unreal.SplineCoordinateSpace.WORLD)
            up = sp.get_up_vector_at_spline_point(0, unreal.SplineCoordinateSpace.WORLD)
            if w is None:
                err = 1e9
                continue
            err = max(err, abs(p0.x - w[0]), abs(p0.y - w[1]), abs(p1.x - w[2]), abs(p1.y - w[3]),
                      abs(p0.z - z1 * 100), abs(p1.z - z1 * 100), 100 * abs(up.x - w[4][0]), 100 * abs(up.y - w[4][1]))
        cols = []
        for comp in a.get_components_by_class(unreal.StaticMeshComponent):
            cols.append({"traversable": resp(comp, CH.ECC_TRAVERSABLE), "pawn": resp(comp, CH.ECC_PAWN),
                         "visibility": resp(comp, CH.ECC_VISIBILITY), "camera": resp(comp, CH.ECC_CAMERA)})
        hidden = bool(a.get_editor_property("hidden"))
        ok = (len(splines) == 4 and err <= TOL and hidden and cols
              and all(c == {"traversable": "block", "pawn": "ignore", "visibility": "ignore", "camera": "ignore"} for c in cols))
        rows[m["name"]] = {"ledge_err_cm": round(err, 3), "n_ledges": len(splines), "hidden": hidden, "collision": cols,
                           "route": m["route"], "ok": ok}
        if not ok:
            bad.append(("marker", m["name"]))
    need = sorted({r["marker"] for r in layout["climb_routes"] if r.get("marker")})
    missing_for_routes = [n for n in need if n not in rows]
    return {"markers": rows, "n_markers": len(rows), "n_layout": len(layout["traversal_markers"]),
            "route_markers_needed": need, "route_markers_missing": missing_for_routes, "bad": bad,
            "passed": not bad and not missing_for_routes and len(rows) == len(layout["traversal_markers"])}


def deps(pkg, seen):
    opts = unreal.AssetRegistryDependencyOptions(include_soft_package_references=False, include_hard_package_references=True)
    for d in AR.get_dependencies(pkg, opts) or []:
        d = str(d)
        if d.startswith("/Game") and d not in seen:
            seen.add(d)
            deps(d, seen)
    return seen


def gate_gameplay(layout, actors):
    ini = (C.PROJECT_DIR / "Config" / "DefaultEngine.ini").read_text(encoding="utf-8")
    gm_cls = EAL.load_blueprint_class(C.DOJO_GAME_MODE)
    cdo = unreal.get_default_object(gm_cls)
    pawn = cdo.get_editor_property("default_pawn_class")
    ws = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_world_settings()
    override = ws.get_editor_property("default_game_mode")
    res = {"project_game_mode": f"GlobalDefaultGameMode={C.DOJO_GAME_MODE}.GM_Dojo_C" in ini,
           "project_default_map": f"GameDefaultMap={C.LEVEL}.L_Dojo" in ini and f"EditorStartupMap={C.LEVEL}.L_Dojo" in ini,
           "gm_parent": unreal.get_default_object(gm_cls).get_class().get_super_class().get_name()
           if hasattr(unreal.get_default_object(gm_cls).get_class(), "get_super_class") else None,
           "default_pawn": pawn.get_path_name() if pawn else None,
           "world_game_mode": override.get_path_name() if override else None,
           "kill_z": float(ws.get_editor_property("kill_z"))}
    seen = set()
    for pkg in (C.DOJO_GAME_MODE, C.GASP_CHARACTER):
        deps(pkg, seen)
    res["n_dependencies"] = len(seen)
    res["missing_dependencies"] = sorted(p for p in seen if not EAL.does_asset_exist(p))
    starts = [a for a in actors if isinstance(a, unreal.PlayerStart)]
    res["player_starts"] = {}
    for ps in layout["player_starts"]:
        a = next((s for s in starts if s.get_actor_label() == ps["name"]), None)
        if a is None:
            continue
        loc, f = a.get_actor_location(), a.get_actor_forward_vector()
        x, y, _ = C.loc_cm(ps["loc"])
        res["player_starts"][ps["tag"]] = {"loc": [round(loc.x, 1), round(loc.y, 1), round(loc.z, 1)],
                                           "tag": str(a.get_editor_property("player_start_tag")),
                                           "forward": [round(f.x, 3), round(f.y, 3)],
                                           "at_spawn": abs(loc.x - x) < 1 and abs(loc.y - y) < 1}
    p1, p2 = res["player_starts"].get("P1"), res["player_starts"].get("P2")
    res["spawn_distance_m"] = round(abs(p1["loc"][0] - p2["loc"][0]) / 100.0, 3) if p1 and p2 else None
    res["facing_each_other"] = bool(p1 and p2 and p1["forward"][0] > 0.99 and p2["forward"][0] < -0.99)
    res["passed"] = (res["project_game_mode"] and res["project_default_map"] and bool(pawn)
                     and pawn.get_path_name().endswith("SandboxCharacter_CMC.SandboxCharacter_CMC_C")
                     and bool(override) and override.get_name() == "GM_Dojo_C" and res["kill_z"] == -1000.0
                     and not res["missing_dependencies"] and len(starts) == 2 and res["facing_each_other"]
                     and all(v["at_spawn"] and v["tag"] == k for k, v in res["player_starts"].items()))
    return res


def gate_environment(layout, actors):
    env = {}
    for a in actors:
        cls = a.get_class().get_name()
        if cls == "DirectionalLight":
            f = a.get_actor_forward_vector()
            exp = C.dir_bl_to_ue(layout["sun"]["travel_dir"])
            env["sun_ok"] = max(abs(f.x - exp[0]), abs(f.y - exp[1]), abs(f.z - exp[2])) < 1e-3
            env["sun_atmosphere"] = bool(a.get_editor_property("directional_light_component").get_editor_property("atmosphere_sun_light"))
        elif cls == "SkyAtmosphere":
            env["sky_atmosphere"] = True
        elif cls == "SkyLight":
            env["skylight_rtc"] = bool(a.get_editor_property("light_component").get_editor_property("real_time_capture"))
        elif cls == "ExponentialHeightFog":
            env["fog"] = True
        elif cls == "PostProcessVolume":
            env["ppv_unbound"] = bool(a.get_editor_property("unbound"))
        elif cls == "CineCameraActor":
            env.setdefault("cameras", []).append(a.get_actor_label())
    env["passed"] = (env.get("sun_ok") and env.get("sun_atmosphere") and env.get("sky_atmosphere") and env.get("skylight_rtc")
                     and env.get("fog") and env.get("ppv_unbound")
                     and sorted(env.get("cameras", [])) == sorted(c["name"] for c in layout["cameras"]))
    return env


def main():
    t0 = time.time()
    rep = {"engine": unreal.SystemLibrary.get_engine_version()}
    try:
        layout = C.load_layout()
        bl = json.loads(C.BLENDER_BOUNDS.read_text(encoding="utf-8"))
        rep["1_meshes"] = gate_meshes(bl)
        rep["2_level"], actors = gate_level(layout, bl)
        rep["3_traversal"] = gate_traversal(layout, actors)
        rep["4_gameplay"] = gate_gameplay(layout, actors)
        rep["5_environment"] = gate_environment(layout, actors)
        rep["gates"] = {k: bool(rep[k]["passed"]) for k in ("1_meshes", "2_level", "3_traversal", "4_gameplay", "5_environment")}
        rep["passed"] = all(rep["gates"].values())
    except Exception:  # noqa: BLE001
        rep["error"] = traceback.format_exc()[-3000:]
        rep["passed"] = False
    rep["sec"] = round(time.time() - t0, 1)
    C.write_json(C.OUT / "verify.json", rep)
    unreal.log(f"DJ_STEP_DONE verify passed={rep['passed']} gates={rep.get('gates')}")


main()
