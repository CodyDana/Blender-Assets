"""Independent verifier, Unreal side (pythonscript commandlet, -nullrhi, FRESH process). READ-ONLY: saves nothing.

Written by the verifier; does not import the builder's ak_* modules. Dumps raw facts to JSON; all comparisons are
done afterwards in plain Python (vf_compare.py) so the engine side only reads.
Out: WorkFiles/armory/build/unreal/verify/vf_unreal.json
"""
import json
import os
import traceback

import unreal

OUT = r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory\build\unreal\verify\vf_unreal.json"
EXPORTS = r"C:\Users\Cody\Desktop\Blender_Projects\Exports\ArmoryKit"
LEVEL = "/Game/Armory/Maps/L_Armory"
EAL = unreal.EditorAssetLibrary
rep = {"engine": str(unreal.SystemLibrary.get_engine_version())}


def v3(v):
    return [float(v.x), float(v.y), float(v.z)]


def mat_info(mi):
    if mi is None:
        return None
    d = {"name": mi.get_name(), "path": mi.get_path_name(), "class": mi.get_class().get_name()}
    chain, cur = [], mi
    for _ in range(10):
        if isinstance(cur, unreal.MaterialInstance):
            p = cur.get_editor_property("parent")
            if p is None:
                chain.append(None)
                break
            chain.append(p.get_path_name())
            cur = p
        else:
            break
    d["parent_chain"] = chain
    try:
        base = mi.get_base_material()
        d["base"] = base.get_path_name() if base else None
    except Exception as e:  # noqa: BLE001
        d["base"] = f"err {e}"
    return d


def step(name, fn):
    try:
        rep[name] = fn()
    except Exception:  # noqa: BLE001
        rep[name] = {"error": traceback.format_exc()[-2500:]}


def meshes():
    stems = sorted(os.path.splitext(f)[0] for f in os.listdir(EXPORTS) if f.lower().endswith(".fbx"))
    all_assets = EAL.list_assets("/Game", recursive=True, include_folder=False)
    by_name = {}
    for p in all_assets:
        nm = p.rsplit("/", 1)[-1].split(".")[0]
        by_name.setdefault(nm, []).append(p)
    out = {"fbx_stems": stems, "n_game_assets": len(all_assets), "meshes": {}}
    for s in stems:
        e = {"asset_paths": by_name.get(s, [])}
        sm = None
        for p in e["asset_paths"]:
            a = unreal.load_asset(p.split(".")[0])
            if isinstance(a, unreal.StaticMesh):
                sm, e["path"] = a, a.get_path_name()
                break
        if sm is None:
            e["static_mesh"] = False
            out["meshes"][s] = e
            continue
        e["static_mesh"] = True
        bs = sm.get_editor_property("body_setup")
        if bs is None:
            e["body_setup"] = None
        else:
            agg = bs.get_editor_property("agg_geom")
            e["convex"] = len(agg.get_editor_property("convex_elems"))
            e["box"] = len(agg.get_editor_property("box_elems"))
            e["sphere"] = len(agg.get_editor_property("sphere_elems"))
            e["sphyl"] = len(agg.get_editor_property("sphyl_elems"))
            e["collision_trace"] = str(bs.get_editor_property("collision_trace_flag"))
            try:
                e["convex_vert_counts"] = [len(c.get_editor_property("vertex_data")) for c in agg.get_editor_property("convex_elems")]
            except Exception:  # noqa: BLE001
                e["convex_vert_counts"] = None
        e["slots"] = []
        for sl in sm.get_editor_property("static_materials"):
            e["slots"].append({"slot": str(sl.get_editor_property("material_slot_name")),
                               "imported": str(sl.get_editor_property("imported_material_slot_name")),
                               "material": mat_info(sl.get_editor_property("material_interface"))})
        bb = sm.get_bounding_box()
        e["local_bbox_cm"] = v3(bb.min) + v3(bb.max)
        try:
            e["tris_lod0"] = int(sm.get_num_triangles(0))
        except Exception:  # noqa: BLE001
            e["tris_lod0"] = None
        out["meshes"][s] = e
    return out


def level():
    exists = EAL.does_asset_exist(LEVEL)
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    loaded = bool(les.load_level(LEVEL))
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    actors = eas.get_all_level_actors()
    out = {"asset_exists": bool(exists), "loaded": loaded, "world": world.get_path_name() if world else None,
           "n_actors": len(actors), "actors": []}
    for a in actors:
        d = {"label": a.get_actor_label(), "name": a.get_name(), "class": a.get_class().get_name(),
             "loc": v3(a.get_actor_location()), "rot": [float(a.get_actor_rotation().roll), float(a.get_actor_rotation().pitch),
                                                        float(a.get_actor_rotation().yaw)],
             "scale": v3(a.get_actor_scale3d()), "hidden": bool(a.get_editor_property("hidden"))}
        o, ext = a.get_actor_bounds(False)
        d["bounds"] = [o.x - ext.x, o.y - ext.y, o.z - ext.z, o.x + ext.x, o.y + ext.y, o.z + ext.z]
        smcs = a.get_components_by_class(unreal.StaticMeshComponent)
        d["smc"] = []
        for c in smcs:
            m = c.get_editor_property("static_mesh")
            d["smc"].append({"mesh": m.get_path_name() if m else None, "visible": bool(c.get_editor_property("visible")),
                             "mats": [(mi.get_path_name() if mi else None) for mi in c.get_materials()],
                             "overrides": [(mi.get_path_name() if mi else None) for mi in c.get_editor_property("override_materials")]})
        lcs = a.get_components_by_class(unreal.LightComponent)
        d["lights"] = []
        for c in lcs:
            ld = {"class": c.get_class().get_name(), "intensity": float(c.get_editor_property("intensity")),
                  "cast_shadows": bool(c.get_editor_property("cast_shadows")),
                  "visible": bool(c.get_editor_property("visible")),
                  "mobility": str(c.get_editor_property("mobility"))}
            try:
                ld["units"] = str(c.get_editor_property("intensity_units"))
            except Exception:  # noqa: BLE001
                pass
            try:
                ld["attenuation_radius"] = float(c.get_editor_property("attenuation_radius"))
            except Exception:  # noqa: BLE001
                pass
            d["lights"].append(ld)
        sky = a.get_components_by_class(unreal.SkyLightComponent)
        if sky:
            c = sky[0]
            d["skylight"] = {"real_time_capture": bool(c.get_editor_property("real_time_capture")),
                             "intensity": float(c.get_editor_property("intensity")),
                             "source_type": str(c.get_editor_property("source_type"))}
        fog = a.get_components_by_class(unreal.ExponentialHeightFogComponent)
        if fog:
            c = fog[0]
            d["fog"] = {"volumetric": bool(c.get_editor_property("enable_volumetric_fog")),
                        "density": float(c.get_editor_property("fog_density")),
                        "visible": bool(c.get_editor_property("visible"))}
        if isinstance(a, unreal.PostProcessVolume):
            s = a.get_editor_property("settings")
            d["ppv"] = {"unbound": bool(a.get_editor_property("unbound")), "enabled": bool(a.get_editor_property("enabled")),
                        "exposure_method": str(s.get_editor_property("auto_exposure_method")),
                        "override_method": bool(s.get_editor_property("override_auto_exposure_method")),
                        "bias": float(s.get_editor_property("auto_exposure_bias"))}
        out["actors"].append(d)
    return out


def settings():
    out = {}
    for cv in ("r.DynamicGlobalIlluminationMethod", "r.ReflectionMethod", "r.Shadow.Virtual.Enable", "r.Substrate",
               "r.RayTracing", "r.GenerateMeshDistanceFields", "r.AllowStaticLighting"):
        try:
            out[cv] = unreal.SystemLibrary.get_console_variable_int_value(cv)
        except Exception as e:  # noqa: BLE001
            out[cv] = f"err {e}"
    try:
        gms = unreal.get_default_object(unreal.GameMapsSettings)
        out["game_default_map"] = str(gms.get_editor_property("game_default_map"))
        out["editor_startup_map"] = str(gms.get_editor_property("editor_startup_map"))
    except Exception as e:  # noqa: BLE001
        out["game_maps_err"] = str(e)
    return out


step("meshes", meshes)
step("settings", settings)
step("level", level)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(rep, f, indent=1, default=str)
unreal.log("VF_UNREAL_DONE")
