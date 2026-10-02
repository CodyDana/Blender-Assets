"""ArmoryLab step 4 (pythonscript commandlet, -nullrhi, a FRESH process): re-check what was SAVED, not what a building
process reported (house rule: in-process reads can pass while nothing persisted).

Gates (all must pass; every count comes from the exports on disk or from layout.json / materials.json, not constants):
 1 meshes      one static mesh per layout.json piece (hero round; Blender kit = layout = Unreal folder, no stale mesh); per mesh the convex hull count equals the Blender UCX count and
               there is no other simple collision; LOD0 triangles equal Blender's; every material slot holds the instance
               named like the slot
 2 textures    one texture per map a layout.json material uses (hero round: T_AK_H* included), with the intended flags (BC sRGB TC_Default, ORM linear TC_Masks,
               N linear TC_Normalmap no flip)
 3 materials   hero round: every layout.json material (M_AK_H* included) checked against ak_common.material_spec from
               layout.json: its instance on the expected master with its scalars, vectors and maps; masters exist; no
               extra instance in the folder
 4 level       L_Armory loads; one mesh actor per layout.json instance labelled <piece>__<nnn> with the right mesh; bounds
               of EVERY mesh actor equal the Blender Assembly bounds converted within 1 cm (entrance piece and an
               east-wall piece named); the room kit (SM_AK_) is on lighting channels 0 + 1 and the exterior (SM_AKX_) on
               0 only; every layout.json cast_shadow False instance casts no shadow
 5 lights      the directional lights of the preset (ak_common.directional_specs, env AK_PRESET, default night) and
               no others: golden = the layout.json suns (the real sun drives the atmosphere and is on channel 0; the f2
               window fill is on channel 1 only, does not drive the atmosphere and does not scatter); night = the moon
               alone (atmosphere light, channel 0, no scattering, priority 1) with direction, lux, disc; + every local
               light by role with the ak_common candela and the preset's colour temperature, shadows as
               ak_common.light_shadows (<= 12), sky light real-time capture at the preset's intensity, SkyAtmosphere,
               height fog as the preset (golden volumetric at the haze density, night none), unbound PPV with manual
               exposure at the preset's bias, the PlayerStart at layout.json "player_start"
               facing the entrance, one camera actor per layout.json camera (shift-lens sensor offset = shift_y x 36 mm)
 6 items       every layout.json item on display (pack asset, placement, +1 scale, sockets)
 7 hero        hero round: every layout.json hero piece is a mesh with all slots assigned, placed as often as layout.json
               places it (per hero module). The suns' forward shading priority (sun 1, window fill 0) is checked in gate 5.
 8 view        (2026-10-01) the V first-person toggle is wired: IA_ToggleView, IMC_ArmoryView mapping exactly V to it, and
               ONE ArmoryViewToggleComponent on BP_ThirdPersonCharacter with both assigned (the runtime proof that V
               switches the view is the fptest step). Gate 1 also checks Nanite per mesh (ak_nanite.want_nanite: on for
               opaque meshes, off for the translucent case glass pieces).
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
import ak_nanite as N  # noqa: E402

EAL = unreal.EditorAssetLibrary
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
TOL = 1.0
TEX_WANT = {"BC": ("True", "TC_DEFAULT", None), "ORM": ("False", "TC_MASKS", None), "N": ("False", "TC_NORMALMAP", "False")}


def gate_meshes(bl):
    out, ok = {}, True
    mats = C.blender_materials()
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
        e["nanite_want"] = str(N.want_nanite(p["slots"], mats))   # VSM overflow fix: opaque meshes Nanite, case glass not
        e["ok"] = (e["convex"] == e["ucx_blender"] and e["other_simple"] == 0 and sorted(slots) == sorted(p["slots"])
                   and e["nanite"] == e["nanite_want"]
                   and all(k == v for k, v in slots.items())
                   and (e["tris_lod0"] is None or e["tris_lod0"] == p["tris"]))
        ok &= e["ok"]
        out[name] = e
    # hero round: the Blender kit, layout.json "pieces" and the Unreal mesh folder are the same set (no stale mesh such as
    # the pre-hero SM_AK_Entrance_6 left in /Game/ArmoryKit/Meshes)
    lay = set(C.layout_pieces())
    ue = {p.split(".")[0].rsplit("/", 1)[-1] for p in EAL.list_assets(C.MESH_DEST, recursive=False, include_folder=False)}
    sets = {"blender_not_layout": sorted(set(bl["pieces"]) - lay), "layout_not_blender": sorted(lay - set(bl["pieces"])),
            "unreal_not_layout": sorted(ue - lay), "layout_not_unreal": sorted(lay - ue)}
    nan = [k for k, v in out.items() if v.get("nanite") == "True"]
    return {"meshes": out, "n": len(out), "sets": sets, "n_nanite": len(nan), "non_nanite": sorted(set(out) - set(nan)),
            "passed": ok and len(out) == C.n_meshes() and not any(sets.values())}


def gate_textures():
    out, ok = {}, True
    for png in C.engine_textures():   # hero round: every map a layout.json material uses (T_AK_* / T_AK_H* / T_AKX_*)
        t = unreal.load_asset(f"{C.TEX_DEST}/{png.stem}") if EAL.does_asset_exist(f"{C.TEX_DEST}/{png.stem}") else None
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
    """Hero round: every layout.json material (M_AK_H* included) against ak_common.material_spec computed HERE from
    layout.json (not from what the materials step reported): the instance exists on its expected master, with its
    scalars, vector colours and texture maps; every master it needs exists; no extra instance is left in the folder."""
    MEL = unreal.MaterialEditingLibrary
    out, ok = {}, True
    want = C.blender_materials()
    masters = set()
    for name, (tex, p) in sorted(want.items()):
        master, scal, vec, texs, _notes = C.material_spec(tex, p)
        masters.add(master)
        mi = unreal.load_asset(f"{C.MAT_DEST}/{name}") if EAL.does_asset_exist(f"{C.MAT_DEST}/{name}") else None
        e = {"exists": isinstance(mi, unreal.MaterialInstanceConstant), "master_want": master}
        if e["exists"]:
            parent = mi.get_editor_property("parent")
            e["parent"] = parent.get_name() if parent else None
            e["scalars"] = {k: round(float(MEL.get_material_instance_scalar_parameter_value(mi, k)), 4) for k in scal}
            e["vectors"] = {}
            for k in vec:
                c = MEL.get_material_instance_vector_parameter_value(mi, k)
                e["vectors"][k] = [round(c.r, 5), round(c.g, 5), round(c.b, 5)]
            e["textures"] = {}
            for k in texs:
                t = MEL.get_material_instance_texture_parameter_value(mi, k)
                e["textures"][k] = t.get_name() if t else None
            e["ok"] = (e["parent"] == master
                       and all(abs(e["scalars"][k] - float(v)) < 1e-3 * max(1.0, abs(float(v))) for k, v in scal.items())
                       and all(max(abs(a_ - float(b_)) for a_, b_ in zip(e["vectors"][k], v)) < 1e-4
                               for k, v in vec.items())
                       and all(e["textures"][k] == v for k, v in texs.items()))
        ok &= bool(e.get("ok"))
        out[name] = e
    for m in sorted(masters):
        a = unreal.load_asset(f"{C.MAT_DEST}/{m}") if EAL.does_asset_exist(f"{C.MAT_DEST}/{m}") else None
        out[m] = {"exists": isinstance(a, unreal.Material), "ok": isinstance(a, unreal.Material)}
        ok &= out[m]["exists"]
    extra = []
    for path in EAL.list_assets(C.MAT_DEST, recursive=False, include_folder=False):
        n = path.split(".")[0].rsplit("/", 1)[-1]
        if n not in want and not n.endswith("_Master"):
            extra.append(n)
    n_hero = sum(1 for n in want if n.startswith("M_AK_H"))
    bad = sorted(k for k, v in out.items() if not v.get("ok"))
    return {"materials": out, "n_instances": len(want), "n_hero_instances": n_hero, "masters": sorted(masters),
            "extra_instances": extra, "failures": bad, "passed": ok and not extra}


def gate_hero(layout, actors):
    """Hero round: every layout.json hero piece (hero_pieces: piece -> module) is a mesh in Unreal whose every slot holds
    its M_AK_* instance, placed as many times as layout.json places it; per-module counts are reported."""
    by_piece = Counter()
    for a in actors:
        lab = a.get_actor_label()
        if "__" in lab and a.get_class().get_name() == "StaticMeshActor":
            by_piece[lab.rsplit("__", 1)[0]] += 1
    want_n = Counter(i["piece"] for i in layout["instances"])
    rows, ok, per_module = {}, True, Counter()
    for piece, module in sorted(layout.get("hero_pieces", {}).items()):
        per_module[module] += 1
        m = unreal.load_asset(f"{C.MESH_DEST}/{piece}") if EAL.does_asset_exist(f"{C.MESH_DEST}/{piece}") else None
        e = {"module": module, "mesh": isinstance(m, unreal.StaticMesh), "placed": by_piece.get(piece, 0),
             "placed_want": want_n.get(piece, 0)}
        if e["mesh"]:
            slots = [(str(s.get_editor_property("material_slot_name")), s.get_editor_property("material_interface"))
                     for s in m.get_editor_property("static_materials")]
            e["unassigned"] = [n for n, mi in slots if mi is None or mi.get_name() != n]
            e["hero_materials"] = sorted(n for n, _mi in slots if n.startswith("M_AK_H"))
        e["ok"] = bool(e["mesh"] and not e.get("unassigned") and e["placed"] == e["placed_want"])
        ok &= e["ok"]
        rows[piece] = e
    return {"pieces": rows, "n": len(rows), "per_module": dict(per_module),
            "failures": sorted(k for k, v in rows.items() if not v["ok"]),
            "passed": ok and len(rows) == len(layout.get("hero_pieces", {})) and len(rows) > 0}


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
        umin, umax, basis, _render = N.actor_box(a)   # Nanite: the placed LOD0 source box (ak_nanite)
        u = umin + umax
        b = bl["instances"][str(n)]
        wmin, wmax = C.bbox_bl_to_ue(b["min"], b["max"])
        err = max(abs(p - q) for p, q in zip(u, wmin + wmax))
        worst = max(worst, err)
        rows[n] = {"label": lab, "err_cm": round(err, 4), "basis": basis, "ue": [round(v, 3) for v in u],
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
    # night + genkan (2026-09-28): the directional lights are ak_common.directional_specs of the active preset (golden:
    # the layout sun + window fill; night: the moon ALONE, the golden suns absent), and the level holds exactly those
    specs = C.directional_specs(layout)
    dirs = [a for a in actors if a.get_class().get_name() == "DirectionalLight"]
    res["directional_labels"] = sorted(a.get_actor_label() for a in dirs)
    if sorted(res["directional_labels"]) != sorted(S["name"] for S in specs):
        bad.append(("directional_set", res["directional_labels"], [S["name"] for S in specs]))
    for S in specs:
        a = by_label.get(S["name"])
        if a is None:
            bad.append(("missing", S["name"]))
            continue
        comp = a.get_component_by_class(unreal.LightComponent)
        f = a.get_actor_forward_vector()
        exp = C.dir_bl_to_ue(S["travel_dir"])
        ch = comp.get_editor_property("lighting_channels")
        interior = S["interior"]
        r = {"lux": float(comp.get_editor_property("intensity")),
             "forward": [round(f.x, 4), round(f.y, 4), round(f.z, 4)],
             "atmosphere_sun_light": bool(comp.get_editor_property("atmosphere_sun_light")),
             "channels": [bool(ch.get_editor_property("channel0")), bool(ch.get_editor_property("channel1"))],
             "volumetric_scattering": float(comp.get_editor_property("volumetric_scattering_intensity")),
             "source_angle": float(comp.get_editor_property("light_source_angle")), "interior_only": interior,
             "forward_shading_priority": int(comp.get_editor_property("forward_shading_priority"))}
        res.setdefault("suns", {})[S["name"]] = r
        if max(abs(p - q) for p, q in zip(r["forward"], exp)) > 1e-3:
            bad.append(("sun_direction", S["name"], r["forward"]))
        if abs(r["lux"] - S["lux"]) > 1e-2:
            bad.append(("sun_lux", S["name"], r["lux"]))
        if abs(r["source_angle"] - S["angle_deg"]) > 1e-3:
            bad.append(("sun_angle", S["name"], r["source_angle"]))
        if r["atmosphere_sun_light"] != S["atmosphere"] or r["channels"] != ([False, True] if interior else [True, False]):
            bad.append(("sun_channels_or_atmosphere", S["name"], r))
        if abs(r["volumetric_scattering"] - S["scatter"]) > 1e-4:   # the fill (and night's moon) never scatter
            bad.append(("sun_scatter", S["name"], r["volumetric_scattering"]))
        if r["forward_shading_priority"] != S["priority"]:   # hero round: the real sun wins (1 vs 0); night: moon 1
            bad.append(("forward_shading_priority", S["name"], r["forward_shading_priority"]))
    for L in layout["lights"]:
        if L["type"] == "sun":
            continue
        a = by_label.get(L["name"])
        if a is None:
            bad.append(("missing", L["name"]))
            continue
        comp = a.get_component_by_class(unreal.LightComponent)
        got_roles[L["role"]] += 1
        # night + genkan: the colour temperature of the preset (night downlights 3500 K), as the 8-bit sRGB colour
        # set_light_color(linear, sRGB=True) stores
        lcol = comp.get_editor_property("light_color")
        want_c = [round(255.0 * (12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055))
                  for c in C.kelvin_rgb(C.light_kelvin(L))]
        got_c = [int(lcol.r), int(lcol.g), int(lcol.b)]
        if max(abs(p - q) for p, q in zip(got_c, want_c)) > 2:
            bad.append(("colour", L["name"], got_c, want_c))
        if L["type"] == "rect":   # glow round: the night under-glow's Unreal-only barn doors (and the hero table's)
            door = float(comp.get_editor_property("barn_door_length"))
            if abs(door - C.light_barn_door_cm(L)) > 1e-3 or (door > 0.0 and
                                                               abs(float(comp.get_editor_property("barn_door_angle"))) > 1e-3):
                bad.append(("barn_door", L["name"], door, C.light_barn_door_cm(L)))
        cd = float(comp.get_editor_property("intensity"))
        if abs(cd - C.light_candela(L)) > 1e-2 * max(1.0, C.light_candela(L)):
            bad.append(("intensity", L["name"], cd))
        if bool(comp.get_editor_property("cast_shadows")):
            shadowed.append(L["name"])
        if bool(comp.get_editor_property("cast_shadows")) != C.light_shadows(L):
            bad.append(("shadows", L["name"]))
        # performance (2026-10-02): attenuation radius per role, case lights on lighting channel 1 only
        if abs(float(comp.get_editor_property("attenuation_radius")) - C.light_atten_cm(L)) > 0.5:
            bad.append(("attenuation_radius", L["name"], float(comp.get_editor_property("attenuation_radius"))))
        lch = comp.get_editor_property("lighting_channels")
        if (bool(lch.get_editor_property("channel0")), bool(lch.get_editor_property("channel1"))) != C.light_channels(L):
            bad.append(("lighting_channels", L["name"]))
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
            env["skylight_intensity"] = float(c.get_editor_property("intensity"))
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
    # the preset's environment: golden has volumetric fog at the Blender haze density; night has none (no shafts);
    # the sky light intensity and the manual exposure bias are the preset's
    fog_want = C.FOG_DENSITY_PER_M > 0.0
    env["preset"] = C.PRESET
    env["fog_ok"] = (env.get("fog_volumetric") == fog_want
                     and abs(env.get("fog_density", -1.0) - C.FOG_DENSITY_PER_M * 10.0) < 1e-6)
    env["skylight_ok"] = abs(env.get("skylight_intensity", -1.0) - C.SKYLIGHT_INTENSITY) < 1e-4
    env["ppv_bias_ok"] = abs(env.get("ppv_bias", 99.0) - C.EXPOSURE_BIAS) < 1e-3
    res["environment"] = env
    res["bad"] = bad
    res["passed"] = (not bad and dict(want_roles) == dict(got_roles) and len(shadowed) <= C.MAX_SHADOWED_LOCAL
                     and env.get("skylight_real_time_capture") and env["fog_ok"] and env["skylight_ok"]
                     and env["ppv_bias_ok"] and env.get("sky_atmosphere")
                     and env.get("ppv_unbound") and "MANUAL" in env.get("ppv_manual", "").upper()
                     and env.get("player_start", {}).get("inside_door") and env.get("player_start", {}).get("faces_into_room")
                     and len(env.get("cameras", [])) == len(layout["cameras"]))
    return res


def gate_view():
    """The V first-person toggle (ak_firstperson.py) as saved: assets, the V mapping, the component on the character."""
    IA, IMC, CH = "/Game/ArmoryLab/Input/IA_ToggleView", "/Game/ArmoryLab/Input/IMC_ArmoryView",         "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
    res = {"module_loaded": hasattr(unreal, "ArmoryViewToggleComponent")}
    imc = unreal.load_asset(IMC) if EAL.does_asset_exist(IMC) else None
    res["ia"] = EAL.does_asset_exist(IA)
    maps = []
    if isinstance(imc, unreal.InputMappingContext):
        for mp in imc.get_editor_property("default_key_mappings").get_editor_property("mappings"):
            act = mp.get_editor_property("action")
            maps.append([act.get_path_name().split(".")[0] if act else None,
                         str(mp.get_editor_property("key").get_editor_property("key_name"))])
    res["imc_mappings"] = maps
    comps = []
    if res["module_loaded"]:
        sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        lib = unreal.SubobjectDataBlueprintFunctionLibrary
        for h in sds.k2_gather_subobject_data_for_blueprint(unreal.load_asset(CH)):
            o = lib.get_associated_object(lib.get_data(h))
            if isinstance(o, unreal.ArmoryViewToggleComponent):
                a, c = o.get_editor_property("toggle_view_action"), o.get_editor_property("toggle_view_context")
                comps.append([a.get_path_name().split(".")[0] if a else None, c.get_path_name().split(".")[0] if c else None])
    res["components"] = comps
    res["passed"] = bool(res["module_loaded"] and res["ia"] and maps == [[IA, "V"]] and comps == [[IA, IMC]])
    return res


def main():
    t0 = time.time()
    rep = {"engine": unreal.SystemLibrary.get_engine_version(), "preset": C.PRESET}
    try:
        layout = C.load_layout()
        bl = json.loads(C.BLENDER_BOUNDS.read_text(encoding="utf-8"))
        rep["1_meshes"] = gate_meshes(bl)
        rep["2_textures"] = gate_textures()
        rep["3_materials"] = gate_materials()
        rep["4_level"], actors = gate_level(layout, bl)
        rep["5_lights"] = gate_lights(layout, actors)
        rep["6_items"] = gate_items(layout, actors)
        rep["7_hero"] = gate_hero(layout, actors)
        rep["8_view"] = gate_view()
        rep["gates"] = {k: rep[k]["passed"] for k in ("1_meshes", "2_textures", "3_materials", "4_level", "5_lights",
                                                        "6_items", "7_hero", "8_view")}
        rep["passed"] = all(rep["gates"].values())
    except Exception:  # noqa: BLE001
        rep["error"] = traceback.format_exc()[-3000:]
        rep["passed"] = False
    rep["sec"] = round(time.time() - t0, 1)
    C.write_json(C.OUT / "verify.json", rep)
    unreal.log(f"AK_STEP_DONE verify passed={rep['passed']} gates={rep.get('gates')}")


main()
