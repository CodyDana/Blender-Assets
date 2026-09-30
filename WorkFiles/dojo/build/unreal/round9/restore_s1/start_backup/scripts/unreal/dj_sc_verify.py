"""DojoLab SHOWCASE verify (pythonscript commandlet, -nullrhi, a FRESH process, read-only): re-check what was SAVED.

Gates (counts come from layout_showcase.json / showcase/blender_bounds.json, never constants):
 1 meshes      one static mesh per layout piece; convex hulls == Blender UCX, no other simple collision; Nanite as the
               layout says; LOD count == the FBX's LodGroup; LOD0 triangles == Blender (non-Nanite meshes); every slot
               holds the instance named like the slot, parented to its recipe's master (grey-box: M_DGB_FlatMaster);
               every Nanite mesh's fallback at full detail (fallback_target RELATIVE_ERROR + relative error 0, or
               PERCENT_TRIANGLES + 100 %) with LOD0 triangles == Blender (the AUTO default decimated it)
 2 textures    one texture per layout texture; BC sRGB TC_Default, ORM / M linear TC_Masks, N TC_Normalmap no flip;
               power-of-two sizes
 3 level       L_Dojo loads; one mesh actor per instance with the right mesh and scale, nothing else managed; no replaced
               grey-box stand-in left; location == layout; world box == Blender within 1 cm for EVERY actor (non-Nanite:
               render bounds; Nanite: the full-detail fallback geometry through the actor transform, since UE's Nanite
               render bounds are the whole DAG's conservative box, reported as information); collision per class
               (NoCollision classes disabled); the
               1v1 boundary hidden + Pawn-only; the gate leaves at their OPEN yaw
 4 traversal   one LevelBlock_Traversable per marker, hidden, Traversable-only, four ledges on the box top edges; every
               climb route's marker present; no TRV_ actor in the level that the layout does not list
 5 gameplay    GM_Dojo / SandboxCharacter_CMC / KillZ / P1-P2 as the grey-box stage (unchanged)
 6 environment sun direction = layout sun, SkyAtmosphere, real-time SkyLight, fog, unbound PPV with manual exposure,
               one point light per layout lamp light, the showcase cameras; the round-2 sunset look as saved: sun
               kelvin = layout, sky luminance factor / sky-light intensity / neutral grade = dj_sc_common, lamps at
               candela x LAMP_SCALE
 7 gasp_trace  in-engine: GASP's forward trace (capsule r 30 / half height 60, Traversable channel, 75 cm along the
               facing from the capsule centre at feet + 86 + 1.9 cm hover) from every climb-route stance must hit the
               route's OWN marker first (round 2: the plinth stance started inside TRV_Landing_PavilionPad)
Result: WorkFiles/dojo/build/unreal/showcase/verify.json
"""
import sys
import time
import traceback
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unreal  # noqa: E402
import dj_common as C  # noqa: E402
import dj_sc_common as S  # noqa: E402
import dj_sc_nanite as N  # noqa: E402

EAL = unreal.EditorAssetLibrary
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
AR = unreal.AssetRegistryHelpers.get_asset_registry()
CH = unreal.CollisionChannel
TOL = 1.0
L = S.load()
BL = S.bounds()


def resp(comp, ch):
    return str(comp.get_collision_response_to_channel(ch)).split(".")[-1].split(":")[0].replace("ECR_", "").lower()


def sm_subsystem():
    try:
        s = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    except Exception:  # noqa: BLE001
        s = None
    return s or unreal.new_object(unreal.StaticMeshEditorSubsystem)


def gate_meshes():
    sms = sm_subsystem()
    out, ok = {}, True
    for piece, p in sorted(L["pieces"].items()):
        b = BL["pieces"][piece]
        m = unreal.load_asset(S.mesh_path(L, piece))
        if not isinstance(m, unreal.StaticMesh):
            out[piece] = {"error": "missing"}
            ok = False
            continue
        agg = m.get_editor_property("body_setup").get_editor_property("agg_geom")
        nanite = bool(m.get_editor_property("nanite_settings").get_editor_property("enabled"))
        e = {"convex": len(agg.get_editor_property("convex_elems")), "ucx_blender": b["n_ucx"],
             "other_simple": sum(len(agg.get_editor_property(k)) for k in ("box_elems", "sphere_elems", "sphyl_elems")),
             "nanite": nanite, "nanite_wanted": bool(p.get("nanite", False)), "lods": int(m.get_num_lods()),
             "lods_blender": b["lods"], "tris_lod0": int(m.get_num_triangles(0)), "tris_blender": b["tris"], "slots": {}}
        if nanite:
            ns = m.get_editor_property("nanite_settings")
            tgt = str(ns.get_editor_property("fallback_target")).split(".")[-1].split(":")[0].strip("<> ")
            rel = float(ns.get_editor_property("fallback_relative_error"))
            pct = float(ns.get_editor_property("fallback_percent_triangles"))
            e["nanite_fallback"] = {"target": tgt, "relative_error": rel, "percent_triangles": pct}
            e["fallback_full"] = (((tgt == "RELATIVE_ERROR" and rel == 0.0) or (tgt == "PERCENT_TRIANGLES" and pct >= 1.0))
                                  and e["tris_lod0"] == e["tris_blender"])
        if e["lods"] > 1:
            try:
                e["lod_screen_sizes"] = [round(float(v), 3) for v in sms.get_lod_screen_sizes(m)]
            except Exception as exc:  # noqa: BLE001
                e["lod_screen_sizes"] = f"unreadable: {exc}"
        for s in m.get_editor_property("static_materials"):
            mi = s.get_editor_property("material_interface")
            parent = mi.get_editor_property("parent").get_name() if isinstance(mi, unreal.MaterialInstanceConstant) else None
            e["slots"][str(s.get_editor_property("material_slot_name"))] = [mi.get_name() if mi else None, parent]
        want_parent = {k: ("M_DGB_FlatMaster" if k.startswith("M_DGB_") else L["materials"][k]["master"]) for k in e["slots"]}
        e["tris_ok"] = nanite or e["tris_lod0"] == e["tris_blender"]
        e["ok"] = (e["convex"] == e["ucx_blender"] and e["other_simple"] == 0 and e["nanite"] == e["nanite_wanted"]
                   and e["lods"] == e["lods_blender"] and e["tris_ok"] and sorted(e["slots"]) == sorted(b["slots"])
                   and all(v[0] == k and v[1] == want_parent[k] for k, v in e["slots"].items())
                   and (e["lods"] == 1 or e.get("lod_screen_sizes") == [1.0, 0.5, 0.25])
                   and (not nanite or e["fallback_full"]))
        ok &= e["ok"]
        out[piece] = e
    bad = {k: v for k, v in out.items() if not v.get("ok")}
    return {"n": len(out), "n_layout": len(L["pieces"]), "n_nanite": sum(1 for v in out.values() if v.get("nanite")),
            "n_nanite_fallback_full": sum(1 for v in out.values() if v.get("fallback_full")),
            "failures": bad, "meshes": out, "passed": ok and len(out) == len(L["pieces"])}


def gate_textures():
    want = {"BC": (True, "TC_DEFAULT"), "ORM": (False, "TC_MASKS"), "M": (False, "TC_MASKS"), "N": (False, "TC_NORMALMAP")}
    out, bad = {}, []
    for name, t in sorted(L["textures"].items()):
        tex = unreal.load_asset(S.tex_path(L, name))
        if tex is None:
            bad.append(name)
            out[name] = "missing"
            continue
        srgb, comp = bool(tex.get_editor_property("srgb")), str(tex.get_editor_property("compression_settings")).split(".")[-1]
        comp = comp.split(":")[0]
        w, h = int(tex.blueprint_get_size_x()), int(tex.blueprint_get_size_y())
        pot = w > 0 and h > 0 and (w & (w - 1)) == 0 and (h & (h - 1)) == 0
        flip = bool(tex.get_editor_property("flip_green_channel"))
        ok = (srgb, comp) == want[t["kind"]] and pot and not flip
        out[name] = {"srgb": srgb, "compression": comp, "size": [w, h], "ok": ok}
        if not ok:
            bad.append(name)
    return {"n": len(out), "n_layout": len(L["textures"]), "bad": bad, "textures": out,
            "passed": not bad and len(out) == len(L["textures"])}


def gate_level():
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    loaded = les.load_level(C.LEVEL)
    actors = EAS.get_all_level_actors()
    by_label = {a.get_actor_label(): a for a in actors}
    res = {"loaded": bool(loaded), "n_actors": len(actors), "classes": dict(Counter(a.get_class().get_name() for a in actors))}
    classes = L["collision_classes"]
    missing, wrong, bad_col, bad_scale, rows, worst, worst_nan = [], [], [], [], {}, 0.0, 0.0
    fbox, infl = {}, {}
    per_class, per_kit = Counter(), Counter()
    for n, inst in enumerate(L["instances"]):
        lab = S.label(inst, n)
        a = by_label.get(lab)
        if a is None:
            missing.append(lab)
            continue
        smc = a.static_mesh_component
        sm = smc.get_editor_property("static_mesh")
        if sm is None or sm.get_name() != inst["piece"]:
            wrong.append(lab)
        sc = a.get_actor_scale3d()
        if max(abs(sc.x - inst["scale"][0]), abs(sc.y - inst["scale"][1]), abs(sc.z - inst["scale"][2])) > 1e-4:
            bad_scale.append(lab)
        cls = inst["collision_class"]
        per_class[cls] += 1
        per_kit[inst["kit"]] += 1
        want = classes[cls]
        got = {"pawn": resp(smc, CH.ECC_PAWN), "camera": resp(smc, CH.ECC_CAMERA), "visibility": resp(smc, CH.ECC_VISIBILITY)}
        enabled = str(smc.get_collision_enabled()).split(".")[-1].split(":")[0]
        hidden = bool(a.get_editor_property("hidden"))
        if (any(got[k] != want[k] for k in got) or hidden != bool(want.get("hidden_in_game", False))
                or (want.get("no_collision") and "NO_COLLISION" not in enabled.upper())
                or (not want.get("no_collision") and "NO_COLLISION" in enabled.upper())):
            bad_col.append({"label": lab, "class": cls, "got": got, "enabled": enabled, "hidden": hidden})
        o, e = a.get_actor_bounds(False)
        u = [o.x - e.x, o.y - e.y, o.z - e.z, o.x + e.x, o.y + e.y, o.z + e.z]
        b = BL["instances"][str(n)]
        wmin, wmax = C.bbox_bl_to_ue(b["min"], b["max"])
        w = wmin + wmax
        if not L["pieces"][inst["piece"]]["nanite"] and "min_all_lods" in b:   # UE render bounds = every LOD's union
            wmin, wmax = C.bbox_bl_to_ue(b["min_all_lods"], b["max_all_lods"])
            w = wmin + wmax
        if L["pieces"][inst["piece"]]["nanite"]:   # the rendered geometry (dj_sc_nanite), not the Nanite DAG box
            if inst["piece"] not in fbox:
                fbox[inst["piece"]] = N.fallback_box(sm)
            err = max(abs(p - q) for p, q in zip(N.world_box(a, fbox[inst["piece"]]), w))
            worst_nan = max(worst_nan, err)
            infl[inst["piece"]] = max(infl.get(inst["piece"], 0.0), round(max(abs(p - q) for p, q in zip(u, w)), 3))
        else:
            err = max(abs(p - q) for p, q in zip(u, w))
            worst = max(worst, err)
        rows[n] = err
        loc = C.loc_cm(inst["loc"])
        al = a.get_actor_location()
        if max(abs(al.x - loc[0]), abs(al.y - loc[1]), abs(al.z - loc[2])) > 0.01:
            wrong.append(lab + " (location)")
    # round 3 fix f1: the painted sky dome (tag DJ_SkyDome, look_r3.ENV sky_dome) is lighting, not a layout instance
    dome = [a for a in actors if unreal.Name("DJ_SkyDome") in list(a.tags)]
    res["sky_dome_actors"] = len(dome)
    mesh_actors = [a for a in actors if a.get_class().get_name() == "StaticMeshActor" and a not in dome]
    stand_ins = sorted({a.static_mesh_component.get_editor_property("static_mesh").get_name() for a in mesh_actors
                        if a.static_mesh_component.get_editor_property("static_mesh") is not None
                        and a.static_mesh_component.get_editor_property("static_mesh").get_name() in L["replaced_greybox"]})
    leaves = {}
    for it in L["kit1"]["gate_leaf_placements"]["open"]:
        a = next((x for x in mesh_actors if x.static_mesh_component.get_editor_property("static_mesh") is not None
                  and x.static_mesh_component.get_editor_property("static_mesh").get_name() == it["piece"]), None)
        yaw = a.get_actor_rotation().yaw if a else None
        leaves[it["piece"]] = {"yaw": None if yaw is None else round(yaw, 3), "want": C.yaw_deg(it["rot_z"]),
                               "open": yaw is not None and abs(((yaw - C.yaw_deg(it["rot_z"])) + 180) % 360 - 180) < 0.01}
    res.update({"missing": missing, "wrong_mesh": wrong, "bad_scale": bad_scale, "collision_errors": bad_col,
                "per_class": dict(per_class), "per_kit": dict(per_kit), "n_mesh_actors": len(mesh_actors),
                "n_instances": len(L["instances"]), "bounds_max_err_cm": round(worst, 4),
                "bounds_max_err_cm_nanite_geometry": round(worst_nan, 4),
                "nanite_culling_bounds_inflation_cm_by_piece": dict(sorted(infl.items())),
                "n_nanite_actors": sum(1 for i in L["instances"] if L["pieces"][i["piece"]]["nanite"]),
                "bounds_failures": {k: round(v, 3) for k, v in rows.items() if v > TOL},
                "greybox_stand_ins_left": stand_ins, "gate_leaves": leaves})
    res["passed"] = (bool(loaded) and not missing and not wrong and not bad_scale and not bad_col
                     and not res["bounds_failures"] and len(mesh_actors) == len(L["instances"]) and not stand_ins
                     and all(v["open"] for v in leaves.values()))
    return res, actors


def gate_traversal(actors):
    by_label = {a.get_actor_label(): a for a in actors}
    rows, bad = {}, []
    for m in L["traversal_markers"]:
        a = by_label.get("TRV_" + m["name"])
        if a is None or a.get_class().get_name() != "LevelBlock_Traversable_C":
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
        cols = [{"traversable": resp(c, CH.ECC_TRAVERSABLE), "pawn": resp(c, CH.ECC_PAWN), "visibility": resp(c, CH.ECC_VISIBILITY),
                 "camera": resp(c, CH.ECC_CAMERA)} for c in a.get_components_by_class(unreal.StaticMeshComponent)]
        hidden = bool(a.get_editor_property("hidden"))
        ok = (len(splines) == 4 and err <= TOL and hidden and cols
              and all(c == {"traversable": "block", "pawn": "ignore", "visibility": "ignore", "camera": "ignore"} for c in cols))
        rows[m["name"]] = {"ledge_err_cm": round(err, 3), "n_ledges": len(splines), "hidden": hidden, "route": m["route"],
                           "box": m["box"], "ok": ok}
        if not ok:
            bad.append(("marker", m["name"]))
    need = sorted({r["marker"] for r in L["climb_routes"] if r.get("marker")})
    miss = [n for n in need if n not in rows]
    names = {"TRV_" + m["name"] for m in L["traversal_markers"]}
    extra = sorted(lab for lab in by_label if lab.startswith("TRV_") and lab not in names)
    return {"markers": rows, "n_markers": len(rows), "n_layout": len(L["traversal_markers"]), "route_markers_needed": need,
            "route_markers_missing": miss, "bad": bad, "trv_actors_not_in_layout": extra,
            "passed": not bad and not miss and not extra and len(rows) == len(L["traversal_markers"])}


def gate_gasp_trace(actors):
    """GASP's step 2.1 in the engine: SystemLibrary.capsule_trace_single on the Traversable trace type from each
    climb-route stance; the first blocking hit must be the route's own marker (TRV_<marker>)."""
    tq = next(getattr(unreal.TraceTypeQuery, n) for n in dir(unreal.TraceTypeQuery) if n.upper() == "ECC_TRAVERSABLE")
    ctx = actors[0]
    rows, bad = {}, []
    for i, r in enumerate(L["climb_routes"]):
        if not r.get("marker") or not r.get("stance") or not r.get("face"):
            continue
        x, y = r["stance"]
        z = float(r.get("floor_z", 0.0)) * 100.0 + 86.0 + 1.9
        fx, fy = r["face"]
        a0 = unreal.Vector(x * 100.0, -y * 100.0, z)
        a1 = unreal.Vector(x * 100.0 + fx * 75.0, -y * 100.0 - fy * 75.0, z)
        h = unreal.SystemLibrary.capsule_trace_single(ctx, a0, a1, 30.0, 60.0, tq, False, [],
                                                      unreal.DrawDebugTrace.NONE, True)
        hit = None
        if h is not None:
            t = h.to_tuple()
            act = t[9] if len(t) > 9 else None
            hit = {"actor": act.get_actor_label() if act else None, "start_penetrating": bool(t[1]),
                   "time": round(float(t[2]), 4), "impact": [round(t[5].x, 1), round(t[5].y, 1), round(t[5].z, 1)]}
        ok = bool(hit and hit["actor"] == "TRV_" + r["marker"])
        key = f"{i:02d} {r['route']} {r['step']}"
        rows[key] = {"marker": r["marker"], "hit": hit, "ok": ok}
        if not ok:
            bad.append(key)
    return {"routes": rows, "n": len(rows), "bad": bad, "passed": bool(rows) and not bad}


def deps(pkg, seen):
    opts = unreal.AssetRegistryDependencyOptions(include_soft_package_references=False, include_hard_package_references=True)
    for d in AR.get_dependencies(pkg, opts) or []:
        d = str(d)
        if d.startswith("/Game") and d not in seen:
            seen.add(d)
            deps(d, seen)
    return seen


def gate_gameplay(actors):
    ini = (C.PROJECT_DIR / "Config" / "DefaultEngine.ini").read_text(encoding="utf-8")
    gm_cls = EAL.load_blueprint_class(C.DOJO_GAME_MODE)
    pawn = unreal.get_default_object(gm_cls).get_editor_property("default_pawn_class")
    ws = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_world_settings()
    override = ws.get_editor_property("default_game_mode")
    res = {"project_game_mode": f"GlobalDefaultGameMode={C.DOJO_GAME_MODE}.GM_Dojo_C" in ini,
           "project_default_map": f"GameDefaultMap={C.LEVEL}.L_Dojo" in ini,
           "default_pawn": pawn.get_path_name() if pawn else None,
           "world_game_mode": override.get_path_name() if override else None,
           "kill_z": float(ws.get_editor_property("kill_z"))}
    seen = set()
    for pkg in (C.DOJO_GAME_MODE, C.GASP_CHARACTER, C.LEVEL):
        deps(pkg, seen)
    res["n_dependencies"] = len(seen)
    res["missing_dependencies"] = sorted(p for p in seen if not EAL.does_asset_exist(p))
    starts = [a for a in actors if isinstance(a, unreal.PlayerStart)]
    res["player_starts"] = {}
    for ps in L["player_starts"]:
        a = next((s for s in starts if s.get_actor_label() == ps["name"]), None)
        if a is None:
            continue
        loc, f = a.get_actor_location(), a.get_actor_forward_vector()
        x, y, _ = C.loc_cm(ps["loc"])
        res["player_starts"][ps["tag"]] = {"loc": [round(loc.x, 1), round(loc.y, 1), round(loc.z, 1)],
                                           "forward": [round(f.x, 3), round(f.y, 3)],
                                           "at_spawn": abs(loc.x - x) < 1 and abs(loc.y - y) < 1}
    p1, p2 = res["player_starts"].get("P1"), res["player_starts"].get("P2")
    res["facing_each_other"] = bool(p1 and p2 and p1["forward"][0] > 0.99 and p2["forward"][0] < -0.99)
    res["passed"] = (res["project_game_mode"] and res["project_default_map"] and bool(pawn)
                     and pawn.get_path_name().endswith("SandboxCharacter_CMC.SandboxCharacter_CMC_C")
                     and bool(override) and override.get_name() == "GM_Dojo_C" and res["kill_z"] == -1000.0
                     and not res["missing_dependencies"] and len(starts) == 2 and res["facing_each_other"]
                     and all(v["at_spawn"] for v in res["player_starts"].values()))
    return res


def gate_environment_uds(actors):
    """Round 8: Ultra Dynamic Sky owns sun / sky / sky light / fog / clouds. Exactly one UDS actor with the ENV variables
    as saved, NO standalone DirectionalLight / SkyAtmosphere / SkyLight / ExponentialHeightFog / VolumetricCloud / sky
    dome, its Sun component on the layout sun, UDS exposure off and our unbound manual PPV above UDS's priority, one point
    light per layout light at candela x LAMP_SCALE (the exposure-recalibrated scale), the showcase cameras."""
    import math
    U = S.UDS
    env = {"lights": 0, "cameras": [], "uds_actors": 0, "conflicting_actors": []}
    for a in actors:
        cls = a.get_class().get_name()
        if cls in ("DirectionalLight", "SkyAtmosphere", "SkyLight", "ExponentialHeightFog", "VolumetricCloud") or \
                unreal.Name("DJ_SkyDome") in list(a.tags):
            env["conflicting_actors"].append(f"{cls}:{a.get_actor_label()}")
        elif cls == "Ultra_Dynamic_Sky_C":
            env["uds_actors"] += 1
            bad = []
            got = {}
            for k, v in U["props"].items():
                g = a.get_editor_property(k)
                got[k] = str(g)[:60]
                ok = _same(g, v)   # enums ({"enum": ...}), bools and numbers
                if not ok:
                    bad.append(k)
            env["uds_props"] = got
            env["uds_prop_mismatch"] = bad
            sun = next(c for c in a.get_components_by_class(unreal.DirectionalLightComponent) if c.get_name() == "Sun")
            f = sun.get_forward_vector()
            exp = C.dir_bl_to_ue(L["sun"]["travel_dir"])
            env["sun_ok"] = max(abs(f.x - exp[0]), abs(f.y - exp[1]), abs(f.z - exp[2])) < 3e-3
            env["sun_elev_deg"] = round(math.degrees(math.asin(-f.z)), 3)
            env["sun_az_from_x_blender_deg"] = round(math.degrees(math.atan2(f.y, -f.x)), 3)
            env["sun_component"] = {k: round(float(sun.get_editor_property(k)), 4) for k in
                                    ("intensity", "light_source_angle", "contact_shadow_length")}
            env["sun_component_mismatch"] = [k for k, v in U.get("sun", {}).items()
                                             if not _same(sun.get_editor_property(k), v)]
            env["uds_post_process"] = []
            for c in a.get_components_by_class(unreal.PostProcessComponent):
                s_ = c.get_editor_property("settings")
                env["uds_post_process"].append({"name": c.get_name(), "priority": float(c.get_editor_property("priority")),
                                                "overrides_exposure_method": bool(s_.get_editor_property(
                                                    "override_auto_exposure_method")),
                                                "overrides_bias": bool(s_.get_editor_property("override_auto_exposure_bias"))})
        elif cls == "PostProcessVolume":
            s = a.get_editor_property("settings")
            env["ppv_unbound"] = bool(a.get_editor_property("unbound"))
            env["ppv_priority"] = float(a.get_editor_property("priority"))
            env["exposure_manual"] = "MANUAL" in str(s.get_editor_property("auto_exposure_method")).upper()
            env["exposure_bias"] = round(float(s.get_editor_property("auto_exposure_bias")), 3)
            env["grade"] = {}
            for k in ("color_gain", "color_saturation"):
                v_ = s.get_editor_property(k)
                env["grade"][k] = ([round(v_.x, 4), round(v_.y, 4), round(v_.z, 4), round(v_.w, 4)]
                                   if s.get_editor_property("override_" + k) else None)
        elif cls == "PointLight":
            env["lights"] += 1
            pl = a.get_editor_property("point_light_component")
            li = next((x for x in L["lights"] if x["name"] == a.get_actor_label()), None)
            if li is None or abs(float(pl.get_editor_property("intensity")) - li["candela"] * S.LAMP_SCALE) > \
                    max(0.05, 1e-3 * li["candela"] * S.LAMP_SCALE):
                env.setdefault("lamp_errors", []).append(a.get_actor_label())
        elif cls == "CineCameraActor":
            env["cameras"].append(a.get_actor_label())
    uds_pp_prio = max([p["priority"] for p in env.get("uds_post_process", [])] or [0.0])
    env["passed"] = bool(env["uds_actors"] == 1 and not env["conflicting_actors"] and env.get("sun_ok")
                         and not env.get("uds_prop_mismatch") and not env.get("sun_component_mismatch")
                         and env.get("ppv_unbound") and env.get("exposure_manual")
                         and abs(env.get("exposure_bias", 1e9) - float(S.EXPOSURE["bias_ev"])) < 1e-3
                         and env.get("ppv_priority", 0.0) > uds_pp_prio
                         and env["lights"] == len(L["lights"]) and not env.get("lamp_errors")
                         and not any(x["name"].startswith("Light_Fill_") for x in L["lights"])
                         and sorted(env["cameras"]) == sorted(c["name"] for c in L["cameras"])
                         and env.get("grade", {}).get("color_gain") in (None, [1.0, 1.0, 1.0, 1.0])
                         and env.get("grade", {}).get("color_saturation") in (None, [1.0, 1.0, 1.0, 1.0]))
    return env


def gate_environment(actors):
    if S.UDS:
        return gate_environment_uds(actors)
    env = {"lights": 0, "cameras": []}
    for a in actors:
        cls = a.get_class().get_name()
        if cls == "DirectionalLight":
            f = a.get_actor_forward_vector()
            exp = C.dir_bl_to_ue(L["sun"]["travel_dir"])
            c = a.get_editor_property("directional_light_component")
            env["sun_ok"] = max(abs(f.x - exp[0]), abs(f.y - exp[1]), abs(f.z - exp[2])) < 1e-3
            env["sun_lux"] = float(c.get_editor_property("intensity"))
            env["sun_atmosphere"] = bool(c.get_editor_property("atmosphere_sun_light"))
            env["sun_kelvin"] = (float(c.get_editor_property("temperature")) if c.get_editor_property("use_temperature")
                                 else None)
        elif cls == "SkyAtmosphere":
            env["sky_atmosphere"] = True
            f_ = a.get_component_by_class(unreal.SkyAtmosphereComponent).get_editor_property("sky_luminance_factor")
            env["sky_luminance_factor"] = [round(f_.r, 4), round(f_.g, 4), round(f_.b, 4)]
        elif cls == "SkyLight":
            slc = a.get_editor_property("light_component")
            env["skylight_rtc"] = bool(slc.get_editor_property("real_time_capture"))
            env["skylight_intensity"] = round(float(slc.get_editor_property("intensity")), 4)
        elif cls == "StaticMeshActor" and unreal.Name("DJ_SkyDome") in list(a.tags):   # round 3 fix f1
            m = a.static_mesh_component.get_material(0)
            env["sky_dome"] = {"material": m.get_path_name() if m else None,
                               "scale": round(a.get_actor_scale3d().x, 3)}
        elif cls == "VolumetricCloud":   # round 3 fix f1
            vc = a.get_component_by_class(unreal.VolumetricCloudComponent)
            m = vc.get_editor_property("material")
            env["clouds"] = {"material": m.get_path_name() if m else None,
                             "bottom_km": round(float(vc.get_editor_property("layer_bottom_altitude")), 3)}
        elif cls == "ExponentialHeightFog":
            env["fog"] = True
        elif cls == "PostProcessVolume":
            s = a.get_editor_property("settings")
            env["ppv_unbound"] = bool(a.get_editor_property("unbound"))
            env["exposure_manual"] = str(s.get_editor_property("auto_exposure_method")).endswith("MANUAL") or \
                "MANUAL" in str(s.get_editor_property("auto_exposure_method")).upper()
            env["exposure_bias"] = round(float(s.get_editor_property("auto_exposure_bias")), 3)
            env["grade"] = {}
            for k in ("color_gain", "color_saturation"):
                v_ = s.get_editor_property(k)
                env["grade"][k] = ([round(v_.x, 4), round(v_.y, 4), round(v_.z, 4), round(v_.w, 4)]
                                   if s.get_editor_property("override_" + k) else None)
        elif cls == "PointLight":
            env["lights"] += 1
            pl = a.get_editor_property("point_light_component")
            li = next((x for x in L["lights"] if x["name"] == a.get_actor_label()), None)
            if li is None or abs(float(pl.get_editor_property("intensity")) - li["candela"] * S.LAMP_SCALE) > 0.05:
                env.setdefault("lamp_errors", []).append(a.get_actor_label())
        elif cls == "CineCameraActor":
            env["cameras"].append(a.get_actor_label())
    env["passed"] = bool(env.get("sun_ok") and env.get("sun_atmosphere") and env.get("sky_atmosphere")
                         and env.get("skylight_rtc") and env.get("fog") and env.get("ppv_unbound") and env.get("exposure_manual")
                         and env["lights"] == len(L["lights"])
                         and sorted(env["cameras"]) == sorted(c["name"] for c in L["cameras"])
                         and env.get("sun_kelvin") == float(L["sun"]["kelvin"])
                         and env.get("sky_luminance_factor") == [round(x, 4) for x in S.SKY_FACTOR]
                         and env.get("skylight_intensity") == round(S.SKYLIGHT_INTENSITY, 4)
                         and env.get("grade", {}).get("color_gain") in (None, [1.0, 1.0, 1.0, 1.0])
                         and env.get("grade", {}).get("color_saturation") in (None, [1.0, 1.0, 1.0, 1.0])
                         and not env.get("lamp_errors")
                         and (bool(env.get("clouds")) == bool(S.CLOUDS))
                         and (bool(env.get("sky_dome")) == bool(S.SKY_DOME)))
    return env


def _same(got, want):
    """round 5: a read-back component value against its look_r3.ENV value (numbers, bools, colours, enums)."""
    if isinstance(want, dict) and "enum" in want:
        return want["enum"].split(".")[1] in str(got)
    if isinstance(want, bool):
        return bool(got) == want
    if isinstance(want, (int, float)):
        return abs(float(got) - float(want)) <= 1e-3 * max(1.0, abs(float(want)))
    if isinstance(want, (list, tuple)):
        vals = [got.r, got.g, got.b] if hasattr(got, "r") else [got.x, got.y, got.z]
        return all(abs(a - b) <= 1e-3 for a, b in zip(vals, want))
    return str(got) == str(want)


def gate_env_extras(actors):
    """round 5: the extra sun / sky atmosphere / sky light / fog / post values (look_r3.ENV) as saved."""
    by = {a.get_actor_label(): a for a in actors}
    if S.UDS:   # round 8: only our PPV's extra values remain ours (UDS owns sun / sky atmosphere / sky light / fog)
        comps = {"pp_extra": (by["PostProcess_Dojo"].get_editor_property("settings"), dict(S.PP_EXTRA, **{
            k: v for k, v in S.GRADE.items() if not isinstance(v, tuple)}))}
    else:
        comps = {}
    comps = comps or {"sun_extra": (by["Sun_Sunset"].get_editor_property("directional_light_component"), S.SUN_EXTRA),
             "sky_atmosphere": (by["SkyAtmosphere"].get_component_by_class(unreal.SkyAtmosphereComponent), S.SKY_ATMOSPHERE),
             "skylight_extra": (by["SkyLight"].get_editor_property("light_component"), S.SKYLIGHT_EXTRA),
             "fog": (by["ExponentialHeightFog"].get_editor_property("component"), S.FOG),
             "pp_extra": (by["PostProcess_Dojo"].get_editor_property("settings"), S.PP_EXTRA)}
    out, bad = {}, []
    for sec, (obj, kv) in comps.items():
        out[sec] = {}
        for k, v in kv.items():
            try:
                g = obj.get_editor_property(k)
                ok = _same(g, v)
                if sec == "pp_extra":
                    ok = ok and bool(obj.get_editor_property("override_" + k))
            except Exception as exc:  # noqa: BLE001
                g, ok = f"error {str(exc)[:80]}", False
            out[sec][k] = {"want": v, "got": str(g)[:60], "ok": ok}
            if not ok:
                bad.append(f"{sec}.{k}")
    out["mismatch"] = bad
    out["passed"] = not bad
    return out


def gate_decals(actors):
    """round 5 gate 8: one DecalActor per layout decal (DKD_<id>), its instance (parent M_DKD_Decal_Master), location,
    rotation, DecalSize (half extents) and the flip scale as decals.json; nothing extra."""
    want = {d["id"]: d for d in L.get("decals", [])}
    got = {a.get_actor_label()[4:]: a for a in actors
           if a.get_class().get_name() == "DecalActor" and a.get_actor_label().startswith("DKD_")}
    missing, bad, worst = sorted(set(want) - set(got)), [], 0.0
    for k, d in want.items():
        a = got.get(k)
        if a is None:
            continue
        u = d["ue"]
        dc = a.get_editor_property("decal")
        m = dc.get_decal_material()
        par = m.get_editor_property("parent") if m else None
        loc = a.get_actor_location()
        e = max(abs(loc.x - u["location_cm"][0]), abs(loc.y - u["location_cm"][1]), abs(loc.z - u["location_cm"][2]))
        sz = dc.get_editor_property("decal_size")
        es = max(abs(sz.x - u["decal_size_cm"][0]), abs(sz.y - u["decal_size_cm"][1]), abs(sz.z - u["decal_size_cm"][2]))
        sc = a.get_actor_scale3d()
        want_r = unreal.Rotator()
        want_r.pitch, want_r.yaw, want_r.roll = u["rotation_deg"]["pitch"], u["rotation_deg"]["yaw"], u["rotation_deg"]["roll"]
        # compare the axes, not the rotator numbers (pitch +-90 decals on floors / roofs have many equal rotators)
        got_r = a.get_actor_rotation()
        er = 0.0
        for fn in (unreal.MathLibrary.get_forward_vector, unreal.MathLibrary.get_up_vector):
            g_, w_ = fn(got_r), fn(want_r)
            er = max(er, max(abs(g_.x - w_.x), abs(g_.y - w_.y), abs(g_.z - w_.z)))
        worst = max(worst, e)
        if (m is None or m.get_name() != d["material"] or par is None or par.get_name() != "M_DKD_Decal_Master"
                or e > 0.01 or es > 0.01 or er > 1e-4
                or max(abs(sc.x - u["scale"][0]), abs(sc.y - u["scale"][1]), abs(sc.z - u["scale"][2])) > 1e-4):
            bad.append({"id": k, "material": m.get_name() if m else None, "loc_err_cm": round(e, 4),
                        "size_err_cm": round(es, 4), "axis_err": round(er, 6)})
    extra = sorted(set(got) - set(want))
    return {"n_layout": len(want), "n_actors": len(got), "missing": missing, "bad": bad, "extra": extra,
            "max_loc_err_cm": round(worst, 5), "passed": not missing and not bad and not extra}


def main():
    t0 = time.time()
    rep = {"engine": unreal.SystemLibrary.get_engine_version()}
    try:
        rep["1_meshes"] = gate_meshes()
        rep["2_textures"] = gate_textures()
        rep["3_level"], actors = gate_level()
        rep["4_traversal"] = gate_traversal(actors)
        rep["5_gameplay"] = gate_gameplay(actors)
        rep["6_environment"] = gate_environment(actors)
        rep["7_gasp_trace"] = gate_gasp_trace(actors)
        rep["6_environment"]["extras"] = gate_env_extras(actors)   # round 5
        rep["6_environment"]["passed"] = rep["6_environment"]["passed"] and rep["6_environment"]["extras"]["passed"]
        rep["8_decals"] = gate_decals(actors)                     # round 5
        rep["gates"] = {k: bool(rep[k]["passed"]) for k in ("1_meshes", "2_textures", "3_level", "4_traversal",
                                                           "5_gameplay", "6_environment", "7_gasp_trace", "8_decals")}
        rep["passed"] = all(rep["gates"].values())
    except Exception:  # noqa: BLE001
        rep["error"] = traceback.format_exc()[-3000:]
        rep["passed"] = False
    rep["sec"] = round(time.time() - t0, 1)
    S.write_json(S.SC_OUT / "verify.json", rep)
    unreal.log(f"DJ_STEP_DONE sc_verify passed={rep['passed']} gates={rep.get('gates')}")


main()
