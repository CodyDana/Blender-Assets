"""ArmoryLab step 4 (pythonscript commandlet, -nullrhi, a FRESH process): re-check what was SAVED, not what a building
process reported (house rule: in-process reads can pass while nothing persisted).

Gates (all must pass; every count comes from the exports on disk or from layout.json / materials.json, not constants):
 1 meshes      one static mesh per exported SM_AK*.fbx; per mesh the convex hull count equals the Blender UCX count and
               there is no other simple collision; LOD0 triangles equal Blender's; every material slot holds the instance
               named like the slot
 2 textures    one texture per exported BC / N / ORM map, with the intended flags (BC sRGB TC_Default, ORM linear TC_Masks,
               N linear TC_Normalmap no flip)
 3 materials   every master materials.json built exists; every instance exists on its expected parent with its scalars
 4 level       L_Armory loads; one mesh actor per layout.json instance labelled <piece>__<nnn> with the right mesh; bounds
               of EVERY mesh actor equal the Blender Assembly bounds converted within 1 cm (entrance piece and an
               east-wall piece named); the room kit (SM_AK_) is on lighting channels 0 + 1 and the exterior (SM_AKX_) on
               0 only; every layout.json cast_shadow False instance casts no shadow
 5 lights      the layout.json suns (the real sun drives the atmosphere and is on channel 0; the f2 window fill is on
               channel 1 only, does not drive the atmosphere and does not scatter) + every local light by role with the
               ak_common candela, shadows as ak_common.light_shadows (<= 12), sky light real-time capture, SkyAtmosphere,
               volumetric height fog, unbound PPV with manual exposure, the PlayerStart at layout.json "player_start"
               facing the entrance, one camera actor per layout.json camera (shift-lens sensor offset = shift_y x 36 mm)
Result: WorkFiles/armory/build/unreal/verify.json
"""
import json
import sys
import time
import traceback
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unreal  # noqa: E402
import ak_common as C  # noqa: E402

EAL = unreal.EditorAssetLibrary
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
TOL = 1.0
TEX_WANT = {"BC": ("True", "TC_DEFAULT", None), "ORM": ("False", "TC_MASKS", None), "N": ("False", "TC_NORMALMAP", "False")}


def gate_meshes(bl):
    out, ok = {}, True
    for name, p in sorted(bl["pieces"].items()):
        m = unreal.load_asset(f"{C.MESH_DEST}/{name}")
        e = {}
        if not isinstance(m, unreal.StaticMesh):
            out[name] = {"error": "missing"}
            ok = False
            continue
        agg = m.get_editor_property("body_setup").get_editor_property("agg_geom")
        e["convex"] = len(agg.get_editor_property("convex_elems"))
        e["other_simple"] = sum(len(agg.get_editor_property(k)) for k in ("box_elems", "sphere_elems", "sphyl_elems"))
        e["ucx_blender"] = len(p["ucx"])
        slots = {}
        for s in m.get_editor_property("static_materials"):
            mi = s.get_editor_property("material_interface")
            slots[str(s.get_editor_property("material_slot_name"))] = mi.get_name() if mi else None
        e["slots"] = slots
        e["slots_blender"] = p["slots"]
        e["tris_lod0"] = int(m.get_num_triangles(0)) if hasattr(m, "get_num_triangles") else None
        e["tris_blender"] = p["tris"]
        e["nanite"] = str(m.get_editor_property("nanite_settings").get_editor_property("enabled"))
        e["ok"] = (e["convex"] == e["ucx_blender"] and e["other_simple"] == 0 and sorted(slots) == sorted(p["slots"])
                   and all(k == v for k, v in slots.items())
                   and (e["tris_lod0"] is None or e["tris_lod0"] == p["tris"]))
        ok &= e["ok"]
        out[name] = e
    return {"meshes": out, "n": len(out), "passed": ok and len(out) == C.n_meshes()}


def gate_textures():
    out, ok = {}, True
    for png in C.engine_textures():
        t = unreal.load_asset(f"{C.TEX_DEST}/{png.stem}")
        kind = png.stem.rsplit("_", 1)[1]
        if t is None:
            out[png.stem] = {"error": "missing"}
            ok = False
            continue
        srgb, comp, flip = TEX_WANT[kind]
        e = {"srgb": str(t.get_editor_property("srgb")), "compression": str(t.get_editor_property("compression_settings")),
             "flip_green": str(t.get_editor_property("flip_green_channel")), "mips": str(t.get_editor_property("mip_gen_settings"))}
        e["ok"] = (e["srgb"] == srgb and comp in e["compression"] and (flip is None or e["flip_green"] == flip)
                   and "NO_MIPMAPS" not in e["mips"].upper())
        ok &= e["ok"]
        out[png.stem] = e
    return {"textures": out, "n": len(out), "passed": ok and len(out) == C.n_textures()}


def gate_materials():
    want = json.loads((C.OUT / "materials.json").read_text(encoding="utf-8"))["instances"]
    out, ok = {}, True
    masters = json.loads((C.OUT / "materials.json").read_text(encoding="utf-8"))["masters"]
    for m in masters:
        a = unreal.load_asset(f"{C.MAT_DEST}/{m}")
        out[m] = {"exists": isinstance(a, unreal.Material)}
        ok &= out[m]["exists"]
    for name, w in want.items():
        mi = unreal.load_asset(f"{C.MAT_DEST}/{name}")
        e = {"exists": isinstance(mi, unreal.MaterialInstanceConstant)}
        if e["exists"]:
            parent = mi.get_editor_property("parent")
            e["parent"] = parent.get_name() if parent else None
            e["scalars"] = {k: round(float(unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(mi, k)), 4)
                            for k in w.get("scalars", {})}
            e["ok"] = e["parent"] == w.get("master") and all(abs(e["scalars"][k] - float(v)) < 1e-3
                                                             for k, v in w.get("scalars", {}).items())
        ok &= bool(e.get("ok"))
        out[name] = e
    return {"materials": out, "passed": ok}


def gate_level(layout, bl):
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    loaded = les.load_level(C.LEVEL) if les else unreal.EditorLoadingAndSavingUtils.load_map(C.LEVEL)
    actors = EAS.get_all_level_actors()
    res = {"loaded": bool(loaded), "n_actors": len(actors),
           "classes": dict(Counter(a.get_class().get_name() for a in actors))}
    by_label = {a.get_actor_label(): a for a in actors}
    rows, worst, missing, wrong_mesh, bad_channels, bad_shadow = {}, 0.0, [], [], [], []
    for n, inst in enumerate(layout["instances"]):
        lab = f"{inst['piece']}__{n:03d}"
        a = by_label.get(lab)
        if a is None:
            missing.append(lab)
            continue
        sm = a.static_mesh_component.get_editor_property("static_mesh")
        if sm is None or sm.get_name() != inst["piece"]:
            wrong_mesh.append(lab)
        smc = a.static_mesh_component
        ch = smc.get_editor_property("lighting_channels")
        want_ch = (True, C.is_interior_piece(inst["piece"]))
        if (bool(ch.get_editor_property("channel0")), bool(ch.get_editor_property("channel1"))) != want_ch:
            bad_channels.append(lab)
        if inst.get("cast_shadow") is False and bool(smc.get_editor_property("cast_shadow")):
            bad_shadow.append(lab)
        o, e = a.get_actor_bounds(False)
        u = [o.x - e.x, o.y - e.y, o.z - e.z, o.x + e.x, o.y + e.y, o.z + e.z]
        b = bl["instances"][str(n)]
        wmin, wmax = C.bbox_bl_to_ue(b["min"], b["max"])
        err = max(abs(p - q) for p, q in zip(u, wmin + wmax))
        worst = max(worst, err)
        rows[n] = {"label": lab, "err_cm": round(err, 4), "ue": [round(v, 3) for v in u],
                   "blender_converted": [round(v, 3) for v in wmin + wmax]}
    door = next(n for n, i in enumerate(layout["instances"]) if i["piece"].startswith("SM_AK_Entrance_"))
    east = next(n for n, i in enumerate(layout["instances"])
                if i["piece"] == "SM_AK_WallLower_2" and float(i["rot_z"]) == 90.0)
    res["bounds_gate"] = {"tolerance_cm": TOL, "n_checked": len(rows), "max_err_cm_all": round(worst, 4),
                          "door_piece": rows.get(door), "east_wall_piece": rows.get(east),
                          "failures": [r for r in rows.values() if r["err_cm"] > TOL]}
    res["missing"], res["wrong_mesh"] = missing, wrong_mesh
    res["lighting_channel_errors"], res["cast_shadow_errors"] = bad_channels, bad_shadow
    res["n_interior_meshes"] = sum(1 for i in layout["instances"] if C.is_interior_piece(i["piece"]))
    res["n_no_shadow_meshes"] = sum(1 for i in layout["instances"] if i.get("cast_shadow") is False)
    res["passed"] = (bool(loaded) and not missing and not wrong_mesh and len(rows) == len(layout["instances"])
                     and not res["bounds_gate"]["failures"] and not bad_channels and not bad_shadow)
    return res, actors


def gate_items(layout, actors):
    """Every layout.json item: its actor exists, uses its pack asset, sits within 0.1 cm and 0.1 deg of the Blender
    placement converted, has scale exactly +1 on every axis (never mirrored), and the asset still has its sockets."""
    by_label = {a.get_actor_label(): a for a in actors}
    rows, ok = {}, True
    for it in layout.get("items", []):
        a = by_label.get(f"ITEM_{it['name']}")
        e = {}
        if a is None:
            rows[it["name"]] = {"missing": True}
            ok = False
            continue
        sm = a.static_mesh_component.get_editor_property("static_mesh")
        want = C.loc_cm(it["loc"])
        loc, rt, sc = a.get_actor_location(), a.get_actor_rotation(), a.get_actor_scale3d()
        e["asset_ok"] = sm is not None and sm.get_path_name().split(".")[0] == it["ue_asset"]
        e["loc_err_cm"] = round(max(abs(loc.x - want[0]), abs(loc.y - want[1]), abs(loc.z - want[2])), 4)
        dyaw = (rt.yaw - C.yaw_deg(it["rot_z"]) + 180.0) % 360.0 - 180.0
        e["yaw_err_deg"] = round(abs(dyaw), 4)
        e["tilt_deg"] = round(max(abs(rt.pitch), abs(rt.roll)), 4)
        e["scale"] = [round(sc.x, 4), round(sc.y, 4), round(sc.z, 4)]
        # StaticMesh.sockets is protected from Python in 5.8: look the pack's sockets up by name instead
        e["sockets"] = [n for n in ("Grip", "Trail") if sm is not None and sm.find_socket(n) is not None]
        e["ok"] = bool(e["asset_ok"] and e["loc_err_cm"] < 0.1 and e["yaw_err_deg"] < 0.1 and e["tilt_deg"] < 0.1
                       and e["scale"] == [1.0, 1.0, 1.0] and e["sockets"])
        ok &= e["ok"]
        rows[it["name"]] = e
    return {"items": rows, "n": len(rows), "passed": ok and len(rows) == len(layout.get("items", []))}


def gate_lights(layout, actors):
    res = {}
    want_roles = Counter(L["role"] for L in layout["lights"] if L["type"] != "sun")
    by_label = {a.get_actor_label(): a for a in actors}
    got_roles, shadowed, bad = Counter(), [], []
    for L in layout["lights"]:
        a = by_label.get(L["name"])
        if a is None:
            bad.append(("missing", L["name"]))
            continue
        comp = a.get_component_by_class(unreal.LightComponent)
        if L["type"] == "sun":
            f = a.get_actor_forward_vector()
            exp = C.dir_bl_to_ue(L["travel_dir"])
            ch = comp.get_editor_property("lighting_channels")
            interior = L.get("link") == "interior"
            r = {"lux": float(comp.get_editor_property("intensity")),
                 "forward": [round(f.x, 4), round(f.y, 4), round(f.z, 4)],
                 "atmosphere_sun_light": bool(comp.get_editor_property("atmosphere_sun_light")),
                 "channels": [bool(ch.get_editor_property("channel0")), bool(ch.get_editor_property("channel1"))],
                 "volumetric_scattering": float(comp.get_editor_property("volumetric_scattering_intensity")),
                 "source_angle": float(comp.get_editor_property("light_source_angle")), "interior_only": interior}
            res.setdefault("suns", {})[L["name"]] = r
            if max(abs(p - q) for p, q in zip(r["forward"], exp)) > 1e-3:
                bad.append(("sun_direction", L["name"], r["forward"]))
            if abs(r["lux"] - C.sun_lux(L)) > 1e-2:
                bad.append(("sun_lux", L["name"], r["lux"]))
            if r["atmosphere_sun_light"] == interior or r["channels"] != ([False, True] if interior else [True, False]):
                bad.append(("sun_channels_or_atmosphere", L["name"], r))
            if interior and r["volumetric_scattering"] != 0.0:
                bad.append(("fill_scatters", L["name"]))
            continue
        got_roles[L["role"]] += 1
        cd = float(comp.get_editor_property("intensity"))
        if abs(cd - C.light_candela(L)) > 1e-2 * max(1.0, C.light_candela(L)):
            bad.append(("intensity", L["name"], cd))
        if bool(comp.get_editor_property("cast_shadows")):
            shadowed.append(L["name"])
        if bool(comp.get_editor_property("cast_shadows")) != C.light_shadows(L):
            bad.append(("shadows", L["name"]))
        if float(comp.get_editor_property("volumetric_scattering_intensity")) != 0.0:
            bad.append(("scatter", L["name"]))
    res["roles_want"], res["roles_got"] = dict(want_roles), dict(got_roles)
    res["shadowed_local"] = shadowed
    env = {}
    for a in actors:
        cls = a.get_class().get_name()
        if cls == "SkyLight":
            c = a.get_editor_property("light_component")
            env["skylight_real_time_capture"] = bool(c.get_editor_property("real_time_capture"))
        elif cls == "ExponentialHeightFog":
            c = a.get_editor_property("component")
            env["fog_volumetric"] = bool(c.get_editor_property("enable_volumetric_fog"))
            env["fog_density"] = float(c.get_editor_property("fog_density"))
        elif cls == "SkyAtmosphere":
            env["sky_atmosphere"] = True
        elif cls == "PostProcessVolume":
            s = a.get_editor_property("settings")
            env["ppv_unbound"] = bool(a.get_editor_property("unbound"))
            env["ppv_manual"] = str(s.get_editor_property("auto_exposure_method"))
            env["ppv_bias"] = float(s.get_editor_property("auto_exposure_bias"))
        elif cls == "PlayerStart":
            loc, f = a.get_actor_location(), a.get_actor_forward_vector()
            want, _yaw = C.player_start(C.load_layout())   # exterior stage: in the courtyard, facing the entrance
            env["player_start"] = {"loc": [loc.x, loc.y, loc.z], "forward": [round(f.x, 3), round(f.y, 3), round(f.z, 3)],
                                   "inside_door": abs(loc.x - want[0]) < 1.0 and abs(loc.y - want[1]) < 1.0,
                                   "faces_into_room": f.y < -0.99}
        elif cls in ("CameraActor", "CineCameraActor"):
            env.setdefault("cameras", []).append(a.get_actor_label())
    cams = {c["name"]: c for c in layout["cameras"]}
    for lab in env.get("cameras", []):
        c = cams.get(lab.replace("CAM_", "", 1))
        a = by_label[lab]
        if c is None:
            bad.append(("camera_not_in_layout", lab))
            continue
        if a.get_class().get_name() == "CineCameraActor":
            fb = a.get_cine_camera_component().get_editor_property("filmback")
            off = float(fb.get_editor_property("sensor_vertical_offset"))
            if abs(off - float(c.get("shift_y", 0.0)) * 36.0) > 1e-3:
                bad.append(("camera_shift", lab, off))
    res["environment"] = env
    res["bad"] = bad
    res["passed"] = (not bad and dict(want_roles) == dict(got_roles) and len(shadowed) <= C.MAX_SHADOWED_LOCAL
                     and env.get("skylight_real_time_capture") and env.get("fog_volumetric") and env.get("sky_atmosphere")
                     and env.get("ppv_unbound") and "MANUAL" in env.get("ppv_manual", "").upper()
                     and env.get("player_start", {}).get("inside_door") and env.get("player_start", {}).get("faces_into_room")
                     and len(env.get("cameras", [])) == len(layout["cameras"]))
    return res


def main():
    t0 = time.time()
    rep = {"engine": unreal.SystemLibrary.get_engine_version()}
    try:
        layout = C.load_layout()
        bl = json.loads(C.BLENDER_BOUNDS.read_text(encoding="utf-8"))
        rep["1_meshes"] = gate_meshes(bl)
        rep["2_textures"] = gate_textures()
        rep["3_materials"] = gate_materials()
        rep["4_level"], actors = gate_level(layout, bl)
        rep["5_lights"] = gate_lights(layout, actors)
        rep["6_items"] = gate_items(layout, actors)
        rep["gates"] = {k: rep[k]["passed"] for k in ("1_meshes", "2_textures", "3_materials", "4_level", "5_lights",
                                                        "6_items")}
        rep["passed"] = all(rep["gates"].values())
    except Exception:  # noqa: BLE001
        rep["error"] = traceback.format_exc()[-3000:]
        rep["passed"] = False
    rep["sec"] = round(time.time() - t0, 1)
    C.write_json(C.OUT / "verify.json", rep)
    unreal.log(f"AK_STEP_DONE verify passed={rep['passed']} gates={rep.get('gates')}")


main()
