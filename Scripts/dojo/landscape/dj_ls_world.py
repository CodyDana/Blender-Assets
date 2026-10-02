"""LANDSCAPE ROUND (world stage), Unreal step 3 (pythonscript commandlet WITH a real RHI: -AllowCommandletRendering, so
the landscape edit layers merge on the GPU and its Nanite mesh builds): the world around the compound, from
world/json/world_layout.json (make_world_layout.py), into /Game/Dojo/Maps/L_Dojo.

Re-run safe: destroys exactly the actors tagged DJ_Landscape (never DJ_Managed: the compound / showcase level step owns
those), then builds, in order:
  1 the valley mask texture (T_DJL_ValleyMask, linear masks) -> MI_DJL_Valley
  2 LS_Valley and LS_Far: ALandscapeProxy::Import through our editor helper (DojoLandscapeTools, installed in DojoLab
    only while this step runs), Nanite on, edit layers merged, collision rebuilt, Nanite built
  3 every actor of the layout: StaticMeshActors (stone kit, pines, owned rocks, far mountain meshes, CherrySlots,
    1v1 boundary B1-B8), SkeletalMeshActors (the Megaplants cypress), collision per class, WPO disable distance and
    Rigid shadow invalidation on the pine foliage
  4 ISM groups (the fir forest, billboards, grass, bushes, pebbles): one actor per mesh with an
    InstancedStaticMeshComponent, each instance's bottom placed from the mesh's own box (bury as the layout says)
  5 the river: one WaterBodyRiver (spline = the layout's points; width / depth / velocity per point; turquoise MI;
    affects_landscape off: the channel is carved in the heightmap) + a WaterZone
  6 lantern point lights (2550 K, relative to the courtyard stone lanterns' candela), the low Local Fog Volume over the
    rapids, FX anchors for the FX stage
Result: world/json/ls_world.json
"""
import json
import math
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
sys.path.insert(0, str(ROOT / "Scripts/dojo/unreal"))
import unreal  # noqa: E402
import dj_sc_common as S  # noqa: E402

W = ROOT / "WorkFiles/dojo/build/landscape/world"
LAY = json.loads((W / "json/world_layout.json").read_text(encoding="utf-8"))
EAL = unreal.EditorAssetLibrary
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
MEL = unreal.MaterialEditingLibrary
TAG = "DJ_Landscape"
REP = {"engine": unreal.SystemLibrary.get_engine_version(), "errors": [], "notes": [], "counts": {}}
CH = unreal.CollisionChannel
RT = unreal.CollisionResponseType
_MESH = {}
_BB = {}


def V(x, y, z):
    return unreal.Vector(float(x), float(y), float(z))


def cm(p):
    return V(p[0] * 100.0, -p[1] * 100.0, p[2] * 100.0)


def rot(yaw=0.0, pitch=0.0, roll=0.0):
    r = unreal.Rotator()
    r.pitch, r.yaw, r.roll = float(pitch), float(yaw), float(roll)
    return r


def setp(o, k, v):
    try:
        o.set_editor_property(k, v)
        return True
    except Exception as exc:  # noqa: BLE001
        REP.setdefault("setp_failed", []).append(f"{type(o).__name__}.{k}: {str(exc)[:120]}")
        return False


def tag(a, label, folder, extra=()):
    a.set_actor_label(label)
    a.set_folder_path("Dojo/" + folder)
    a.tags = [unreal.Name(TAG)] + [unreal.Name(t) for t in extra]
    return a


def mesh(path):
    if path not in _MESH:
        m = unreal.load_asset(path)
        if isinstance(m, unreal.FoliageType_InstancedStaticMesh):
            m = m.get_editor_property("mesh")
        _MESH[path] = m
        if isinstance(m, unreal.StaticMesh):
            b = m.get_bounding_box()
            _BB[path] = (b.min, b.max)
    return _MESH[path]


def collide(comp, kind):
    if kind in ("none", "nocollision"):
        comp.set_collision_profile_name("NoCollision")
        comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        return
    comp.set_collision_profile_name("BlockAll")
    comp.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
    if kind == "thin":        # rails, lanterns: the courtyard's thin-upright class
        comp.set_collision_response_to_channel(CH.ECC_CAMERA, RT.ECR_IGNORE)
        comp.set_collision_response_to_channel(CH.ECC_VISIBILITY, RT.ECR_IGNORE)
    elif kind == "lowblock":  # pine base mounds: walkable, the camera passes
        comp.set_collision_response_to_channel(CH.ECC_CAMERA, RT.ECR_IGNORE)
    elif kind == "boundary":  # 1v1 terrace edge: Pawn only
        comp.set_collision_response_to_all_channels(RT.ECR_IGNORE)
        comp.set_collision_response_to_channel(CH.ECC_PAWN, RT.ECR_BLOCK)


def clear():
    n = 0
    for a in EAS.get_all_level_actors():
        if unreal.Name(TAG) in list(a.tags):
            EAS.destroy_actor(a)
            n += 1
    REP["removed_previous"] = n


# ---------------------------------------------------------------------------------------------------- 1 mask
def mask_texture():
    src = LAY["mask"]["file"]
    task = unreal.AssetImportTask()
    for k, v in (("filename", src), ("destination_path", "/Game/DojoLandscape/Textures"),
                 ("destination_name", "T_DJL_ValleyMask"), ("automated", True), ("replace_existing", True), ("save", False)):
        task.set_editor_property(k, v)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    t = unreal.load_asset("/Game/DojoLandscape/Textures/T_DJL_ValleyMask")
    setp(t, "srgb", False)
    setp(t, "compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
    EAL.save_loaded_asset(t, False)
    mi = unreal.load_asset("/Game/DojoLandscape/Materials/MI_DJL_Valley")
    MEL.set_material_instance_texture_parameter_value(mi, "ValleyMask", t)
    MEL.update_material_instance(mi)
    EAL.save_loaded_asset(mi, False)
    REP["mask"] = {"texture": t.get_path_name(), "size": [t.blueprint_get_size_x(), t.blueprint_get_size_y()]}


# ---------------------------------------------------------------------------------------------------- 2 landscapes
def landscapes():
    lib = unreal.DojoLandscapeToolsLibrary
    # the landscape Nanite build finishes inside UpdateNaniteRepresentation only when the multithreaded build is off
    # (Landscape.cpp: otherwise it is left in flight, and a commandlet never ticks it to completion)
    unreal.SystemLibrary.execute_console_command(None, "landscape.Nanite.MultithreadBuild 0")
    out = {}
    for L in LAY["landscapes"]:
        mat = unreal.load_asset(L["material"])
        loc = unreal.Vector(*L["location_cm"])
        sc = unreal.Vector(*L["scale"])
        res = lib.create_landscape_from_raw16(L["raw"], L["n"], L["n"], L["sections"], L["quads"], loc, sc, mat, L["label"])
        land, report = (res if isinstance(res, tuple) else (res, ""))
        if land is None:
            raise RuntimeError(f"{L['label']}: {report}")
        setp(land, "enable_nanite", True)
        tag(land, L["label"], "Landscape/Terrain", ("DJL_landscape",))
        fin = lib.finalize_landscape(land, True)
        comps = land.get_components_by_class(unreal.LandscapeComponent)
        o, e = land.get_actor_bounds(False)
        out[L["label"]] = {"create": report, "finalize": fin, "components": len(comps),
                           "bounds_cm": [[round(o.x - e.x), round(o.y - e.y), round(o.z - e.z)],
                                         [round(o.x + e.x), round(o.y + e.y), round(o.z + e.z)]],
                           "nanite": bool(land.get_editor_property("enable_nanite"))}
    REP["landscapes"] = out


# ---------------------------------------------------------------------------------------------------- 3 actors
def place_actor(r):
    if r.get("skeletal"):
        sk = unreal.load_asset(r["mesh"])
        if sk is None:
            raise RuntimeError(f"missing {r['mesh']}")
        a = EAS.spawn_actor_from_class(unreal.SkeletalMeshActor, cm(r["loc"]), rot(-r["rot_z"]))
        c = a.skeletal_mesh_component
        if not setp(c, "skinned_asset", sk):
            c.set_skeletal_mesh_asset(sk)
        a.set_actor_scale3d(V(*r["scale"]))
        c.set_collision_profile_name("NoCollision")
        return tag(a, r["label"], r["folder"], ("DJL_" + r["group"],))
    m = mesh(r["mesh"])
    if m is None:
        raise RuntimeError(f"missing {r['mesh']}")
    loc = list(r["loc"])
    scale = list(r["scale"])
    pitch, roll = r.get("pitch", 0.0), r.get("roll", 0.0)
    if r.get("size_m"):     # owned rocks: scale to the target size, sink `bury` of the height into the ground
        bmin, bmax = _BB[r["mesh"]]
        ext = max(bmax.x - bmin.x, bmax.y - bmin.y) / 100.0
        s = r["size_m"] / ext
        h = (bmax.z - bmin.z) / 100.0 * s
        scale = [s, s, s * 0.85]
        loc[2] = loc[2] - r["bury"] * h * 0.85 - bmin.z / 100.0 * s * 0.85
        if r.get("top_z") is not None:     # fix round: the rapids boulders are set by their TOP over the water
            loc[2] = r["top_z"] - bmax.z / 100.0 * s * 0.85
    a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, cm(loc), rot(-r["rot_z"], pitch, roll))
    a.set_actor_scale3d(V(*scale))
    c = a.static_mesh_component
    c.set_static_mesh(m)
    c.set_mobility(unreal.ComponentMobility.STATIC)
    if r.get("material"):
        mi = unreal.load_asset(r["material"])
        for i in range(len(m.get_editor_property("static_materials"))):
            c.set_material(i, mi)
    collide(c, r["collision"])
    if not r.get("shadow", True):
        setp(c, "cast_shadow", False)
    if r.get("wpo_disable_cm"):
        setp(c, "world_position_offset_disable_distance", int(r["wpo_disable_cm"]))
    if r.get("shadow_invalidation") == "Rigid":
        setp(c, "shadow_cache_invalidation_behavior", unreal.ShadowCacheInvalidationBehavior.RIGID)
    if r.get("hidden"):
        a.set_actor_hidden_in_game(True)
    return tag(a, r["label"], r["folder"], ["DJL_" + r["group"]] + list(r.get("tags", [])))


def actors():
    n = {}
    for r in LAY["actors"]:
        try:
            place_actor(r)
            n[r["group"]] = n.get(r["group"], 0) + 1
        except Exception:  # noqa: BLE001
            REP["errors"].append(f"actor {r['label']}")
            REP.setdefault("tracebacks", {})[r["label"]] = traceback.format_exc()[-800:]
    REP["counts"]["actors"] = n
    # CS01 / CS02: the hidden grey-box trees keep their trunk hulls (the showcase level step hid them)
    trees = [a for a in EAS.get_all_level_actors() if a.get_actor_label().startswith("SM_DGB_Tree__")]
    REP["cs01_cs02_trunk_hulls"] = [{"label": t.get_actor_label(), "hidden_in_game": bool(t.get_editor_property("hidden")),
                                     "collision": str(t.static_mesh_component.get_collision_enabled())} for t in trees]


# ---------------------------------------------------------------------------------------------------- 4 ISM
def ism_actor(g):
    path = g.get("mesh") or g.get("foliage_type")
    m = mesh(path)
    if m is None:
        raise RuntimeError(f"missing {path}")
    a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, V(0, 0, 0), rot())
    a.static_mesh_component.set_mobility(unreal.ComponentMobility.STATIC)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    root = sds.k2_gather_subobject_data_for_instance(a)[0]
    params = unreal.AddNewSubobjectParams(parent_handle=root, new_class=unreal.InstancedStaticMeshComponent,
                                          blueprint_context=None)
    handle, fail = sds.add_new_subobject(params)
    ism = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle))
    ism.set_static_mesh(m)
    ism.set_mobility(unreal.ComponentMobility.STATIC)
    if g.get("material"):
        mi = unreal.load_asset(g["material"])
        for i in range(len(m.get_editor_property("static_materials"))):
            ism.set_material(i, mi)
    for i, sm in enumerate(m.get_editor_property("static_materials")):
        cur = sm.get_editor_property("material_interface")
        new = (g.get("material_swaps") or {}).get(cur.get_name() if cur else "")
        if new:
            ism.set_material(i, unreal.load_asset(new))
    bmin, _ = _BB[path]
    ts = []
    for x, y, z, yaw, s, _k in g["rows"]:
        zc = z * 100.0 - g.get("bury_m", 0.0) * 100.0 * s - (0.0 if g.get("pivot_ground") else bmin.z * s)
        t = unreal.Transform(V(x * 100.0, -y * 100.0, zc), rot(-yaw), V(s, s, s))
        ts.append(t)
    ism.add_instances(ts, False, True)
    collide(ism, g["collision"])
    setp(ism, "cast_shadow", bool(g.get("shadow", True)))
    if g.get("wpo_disable_cm"):
        setp(ism, "world_position_offset_disable_distance", int(g["wpo_disable_cm"]))
    if g.get("shadow_invalidation") == "Rigid":
        # hall + armory round (shadow pass, the landscape verify's carry-over): the wind WPO no longer invalidates the
        # virtual shadow map cache every frame (ShadowDepths 11.6 ms at CAM_RiverRapids, almost all of it the firs)
        setp(ism, "shadow_cache_invalidation_behavior", unreal.ShadowCacheInvalidationBehavior.RIGID)
    if g.get("cull_cm"):
        try:
            ism.set_cull_distances(0, int(g["cull_cm"]))
        except Exception as exc:  # noqa: BLE001
            REP["notes"].append(f"cull {g['name']}: {str(exc)[:80]}")
    tag(a, g["name"], g["folder"], ("DJL_" + g["group"], "DJL_ISM"))
    return int(ism.get_instance_count())


def isms():
    n = {}
    for g in LAY["ism"]:
        try:
            n[g["name"]] = ism_actor(g)
        except Exception:  # noqa: BLE001
            REP["errors"].append(f"ism {g['name']}")
            REP.setdefault("tracebacks", {})[g["name"]] = traceback.format_exc()[-1200:]
    REP["counts"]["ism"] = n


# ---------------------------------------------------------------------------------------------------- 5 water
def water():
    Wd = LAY["water"]
    z = Wd["zone"]
    zone = EAS.spawn_actor_from_class(unreal.WaterZone, cm(z["centre"]), rot())
    setp(zone, "zone_extent", unreal.Vector2D(z["extent_m"][0] * 100.0, z["extent_m"][1] * 100.0))
    # fix round: the stepped rapids' pours are 1-2 m long; the water info texture must resolve them (default 512 over
    # 1.6 km = 3.1 m per texel)
    if z.get("rt_resolution"):
        ok = setp(zone, "render_target_resolution", unreal.IntPoint(z["rt_resolution"], z["rt_resolution"]))
        try:
            rr = zone.get_editor_property("render_target_resolution")
            REP["water_rt_resolution"] = [rr.x, rr.y, ok]
        except Exception as exc:  # noqa: BLE001
            REP["water_rt_resolution"] = f"ERR {str(exc)[:100]}"
    tag(zone, z["label"], "Landscape/Water")
    pts = Wd["points"]
    p0 = pts[0]
    river = EAS.spawn_actor_from_class(unreal.WaterBodyRiver, cm([p0["xy"][0], p0["xy"][1], p0["water_z"]]), rot())
    sp = river.get_water_spline()
    sp.clear_spline_points(False)
    for p in pts:
        sp.add_spline_point(cm([p["xy"][0], p["xy"][1], p["water_z"]]), unreal.SplineCoordinateSpace.WORLD, False)
    sp.update_spline()
    comp = river.get_water_body_component()
    setp(comp, "affects_landscape", False)
    for i, p in enumerate(pts):
        comp.set_river_width_at_spline_input_key(float(i), p["width_m"] * 100.0)
        comp.set_river_depth_at_spline_input_key(float(i), p["depth_m"] * 100.0)
        comp.set_water_velocity_at_spline_input_key(float(i), p["velocity_cm_s"])
    mi = unreal.load_asset(Wd["material"])
    try:
        comp.set_water_material(mi)
    except Exception:  # noqa: BLE001
        setp(comp, "water_material", mi)
    try:
        comp.on_water_body_changed(True)
    except Exception:  # noqa: BLE001
        try:
            river.on_water_body_changed(True, False)
        except Exception as exc:  # noqa: BLE001
            REP["notes"].append(f"on_water_body_changed: {str(exc)[:100]}")
    tag(river, Wd["label"], "Landscape/Water")
    n = sp.get_number_of_spline_points()
    REP["water"] = {"points": n, "length_m": round(sp.get_spline_length() / 100.0, 1),
                    "width_m_at": {str(i): round(comp.get_river_width_at_spline_input_key(float(i)) / 100.0, 2)
                                   for i in (0, n // 3, 2 * n // 3, n - 1)},
                    "velocity_at": {str(i): round(comp.get_water_velocity_at_spline_input_key(float(i)), 1)
                                    for i in (0, n // 2, n - 1)},
                    "material": (comp.get_water_material().get_path_name() if comp.get_water_material() else None)}


# ---------------------------------------------------------------------------------------------------- 6 lights, fog, fx
def lights_fog_fx():
    base = next((li for li in S.load()["lights"] if "LanternTall" in li["name"]), None)
    cd0 = (base["candela"] if base else 600.0) * S.LAMP_SCALE
    out = []
    for li in LAY["lights"]:
        a = EAS.spawn_actor_from_class(unreal.PointLight, cm(li["loc"]), rot())
        c = a.get_editor_property("point_light_component")
        for k, v in (("mobility", unreal.ComponentMobility.MOVABLE), ("intensity_units", unreal.LightUnits.CANDELAS),
                     ("intensity", cd0 * li["candela_rel_lantern_tall"]), ("use_temperature", True),
                     ("temperature", li["kelvin"]), ("attenuation_radius", li["radius_m"] * 100.0),
                     ("source_radius", 3.0), ("cast_shadows", li["shadows"])):
            setp(c, k, v)
        tag(a, li["name"], "Landscape/StairPath/Lights", ("DJL_lamp",))
        out.append({"name": li["name"], "cd": round(cd0 * li["candela_rel_lantern_tall"], 3)})
    REP["lights"] = out
    f = LAY["fog"]
    try:
        a = EAS.spawn_actor_from_class(unreal.LocalFogVolume, cm(f["centre"]), rot(-f["yaw"]))
        base_ext = 500.0     # a Local Fog Volume is a unit sphere of radius 500 cm at scale 1 (its actor bounds are the sprite)
        a.set_actor_scale3d(V(f["size_m"][0] * 50.0 / base_ext, f["size_m"][1] * 50.0 / base_ext, f["size_m"][2] * 50.0 / base_ext))
        comp = a.get_component_by_class(unreal.LocalFogVolumeComponent)
        # a thin, low mist (the first build at 0.35 / 0.8 hid the rapids in a white wall): extinction per metre
        # fix round (delta 6): half the world stage's extinction (the mist read as a steam plume)
        for k, v in (("radial_fog_extinction", 0.015), ("height_fog_extinction", 0.04), ("height_fog_falloff", 1200.0),
                     ("height_fog_offset", 0.0), ("fog_albedo", unreal.LinearColor(0.85, 0.9, 0.95, 1.0))):
            setp(comp, k, v)
        tag(a, f["label"], "Landscape/Water", ("DJL_fog",))
        o2, e2 = a.get_actor_bounds(False)
        REP["fog"] = {"base_extent_cm": round(base_ext, 1), "extent_cm": [round(e2.x), round(e2.y), round(e2.z)]}
    except Exception:  # noqa: BLE001
        REP["errors"].append("fog")
        REP.setdefault("tracebacks", {})["fog"] = traceback.format_exc()[-800:]
    cube = unreal.load_asset("/Engine/BasicShapes/Cube")
    for an in LAY["fx_anchors"]:
        a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, cm(an["loc"]), rot())
        a.set_actor_scale3d(V(0.2, 0.2, 0.2))
        a.static_mesh_component.set_static_mesh(cube)
        collide(a.static_mesh_component, "none")
        setp(a.static_mesh_component, "cast_shadow", False)
        a.set_actor_hidden_in_game(True)
        tag(a, an["label"], "Landscape/FXAnchors", ("FXAnchor", an["kind"]))
    REP["fx_anchors"] = len(LAY["fx_anchors"])


def save():
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    ok = bool(les.save_current_level())
    try:
        ok = ok and bool(EAL.save_directory("/Game/DojoLandscape", only_if_is_dirty=True, recursive=True))
    except Exception:  # noqa: BLE001
        pass
    return ok


def main():
    t0 = time.time()
    try:
        les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        REP["loaded"] = bool(les.load_level("/Game/Dojo/Maps/L_Dojo"))
        clear()
        # the water goes in BEFORE the landscapes: WaterEditor's OnLevelActorAdded hook, when a water body appears in a
        # world that already holds a landscape, adds a water brush + edit layer through LandscapeEditor UI code, which
        # asserts without Slate in a commandlet (run 1 crashed there); with no landscape yet it only logs, and the body
        # is then set to affects_landscape = False (our channel is carved in the heightmap)
        for name, fn in (("mask", mask_texture), ("water", water), ("landscapes", landscapes), ("actors", actors),
                         ("ism", isms), ("lights_fog_fx", lights_fog_fx)):
            t1 = time.time()
            try:
                fn()
            except Exception:  # noqa: BLE001
                REP["errors"].append(name)
                REP.setdefault("tracebacks", {})[name] = traceback.format_exc()[-2500:]
            REP.setdefault("sec_by_step", {})[name] = round(time.time() - t1, 1)
            unreal.log(f"DJ_LS_WORLD step {name} done {REP['sec_by_step'][name]} s errors={len(REP['errors'])}")
        REP["n_landscape_actors"] = sum(1 for a in EAS.get_all_level_actors() if unreal.Name(TAG) in list(a.tags))
        REP["n_actors_total"] = len(EAS.get_all_level_actors())
        REP["saved"] = save()
    except Exception:  # noqa: BLE001
        REP["errors"].append("main")
        REP.setdefault("tracebacks", {})["main"] = traceback.format_exc()[-2500:]
    REP["passed"] = not REP["errors"] and REP.get("saved", False)
    REP["sec"] = round(time.time() - t0, 1)
    (W / "json/ls_world.json").write_text(json.dumps(REP, indent=1, default=str), encoding="utf-8")
    unreal.log(f"DJ_STEP_DONE ls_world passed={REP['passed']} errors={REP['errors'][:6]} actors={REP.get('n_landscape_actors')}")


main()
