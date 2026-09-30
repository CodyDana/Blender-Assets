"""DojoLab (pythonscript commandlet, -nullrhi, READ-ONLY: nothing is saved): what GASP can vault / mantle / hurdle, and how
the geometry must be marked. Reads the GASP assets COPIED into DojoLab (the sample project itself is never opened).

Dumps to WorkFiles/dojo/build/unreal/gasp_inspect.json (+ gasp_t3d/*.t3d text exports):
 - GM_Sandbox CDO (default pawn, controller) and the DefaultLevel world-settings override
 - SandboxCharacter_CMC CDO: capsule, CharacterMovement (step height, walkable angle, jump, gravity, speeds), components
 - LevelBlock_Traversable: its components (Blueprint SCS), collision profile, variables; and spawned test instances at
   several scales in a transient level, reading back the ledge spline points the construction script leaves
 - the traversal Chooser tables CHT_TraversalMontages_CMC / _Mover: every column and row (ranges of obstacle height,
   depth, back-ledge height, speed ...) through a T3D text export and the Python-visible properties
 - the LevelBlock_Traversable instances in GASP's own DefaultLevel (their sizes = the heights Epic tests with)
"""
import json
import os
import re
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unreal  # noqa: E402
import dj_common as C  # noqa: E402

EAL = unreal.EditorAssetLibrary
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
T3D = C.OUT / "gasp_t3d"
REP = {"engine": unreal.SystemLibrary.get_engine_version(), "errors": []}


def err(where):
    REP["errors"].append(f"{where}: {traceback.format_exc()[-1200:]}")


def gp(obj, k, default=None):
    try:
        return obj.get_editor_property(k)
    except Exception:  # noqa: BLE001
        return default


def s(v):
    try:
        if isinstance(v, unreal.Vector):
            return [round(v.x, 3), round(v.y, 3), round(v.z, 3)]
        if isinstance(v, unreal.Object):
            return v.get_path_name()
        if isinstance(v, (int, float, str, bool)) or v is None:
            return v
        return str(v)
    except Exception:  # noqa: BLE001
        return repr(v)


def export_t3d(obj, name):
    """Text export of an object (and its subobjects) through the engine's T3D / copy exporters."""
    T3D.mkdir(parents=True, exist_ok=True)
    out = T3D / f"{name}.t3d"
    for ext in ("t3d", "copy"):
        try:
            task = unreal.AssetExportTask()
            task.set_editor_property("object", obj)
            task.set_editor_property("filename", str(out))
            task.set_editor_property("automated", True)
            task.set_editor_property("prompt", False)
            task.set_editor_property("replace_identical", True)
            task.set_editor_property("write_empty_files", False)
            task.set_editor_property("selected", False)
            ok = unreal.Exporter.run_asset_export_task(task)
            if ok and out.exists() and out.stat().st_size > 0:
                return str(out)
        except Exception:  # noqa: BLE001
            pass
    return None


def props_of(obj, names):
    return {k: s(gp(obj, k)) for k in names}


def game_mode():
    out = {}
    try:
        cls = EAL.load_blueprint_class(C.GASP_GAME_MODE)
        cdo = unreal.get_default_object(cls)
        out = props_of(cdo, ["default_pawn_class", "player_controller_class", "hud_class", "game_state_class",
                             "player_state_class", "spectator_class"])
        out["parent"] = s(unreal.BlueprintEditorLibrary.get_blueprint_asset(cls) if hasattr(unreal, "BlueprintEditorLibrary") else None)
    except Exception:  # noqa: BLE001
        err("game_mode")
    try:
        les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        les.load_level("/Game/Levels/DefaultLevel")
        w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        ws = w.get_world_settings()
        out["DefaultLevel_world_settings_game_mode"] = s(gp(ws, "default_game_mode"))
        actors = EAS.get_all_level_actors()
        blocks = []
        classes = {}
        for a in actors:
            cn = a.get_class().get_name()
            classes[cn] = classes.get(cn, 0) + 1
            if "Traversable" in cn:
                o, e = a.get_actor_bounds(False)
                sc = a.get_actor_scale3d()
                blocks.append({"label": a.get_actor_label(), "class": cn,
                               "size_cm": [round(2 * e.x, 1), round(2 * e.y, 1), round(2 * e.z, 1)],
                               "bottom_z": round(o.z - e.z, 1), "top_z": round(o.z + e.z, 1),
                               "scale": s(sc), "yaw": round(a.get_actor_rotation().yaw, 2)})
        out["DefaultLevel_actor_classes"] = classes
        out["DefaultLevel_traversable_blocks"] = blocks
        heights = sorted({round(b["size_cm"][2], 1) for b in blocks})
        out["DefaultLevel_traversable_heights_cm"] = heights
    except Exception:  # noqa: BLE001
        err("default_level")
    return out


def character():
    out = {}
    try:
        cls = EAL.load_blueprint_class(C.GASP_CHARACTER)
        cdo = unreal.get_default_object(cls)
        cap = gp(cdo, "capsule_component")
        out["capsule"] = props_of(cap, ["capsule_radius", "capsule_half_height"]) if cap else None
        if cap:
            out["capsule"]["collision_profile"] = s(cap.get_collision_profile_name())
        cmc = gp(cdo, "character_movement")
        if cmc:
            out["movement"] = props_of(cmc, [
                "max_step_height", "walkable_floor_angle", "walkable_floor_z", "jump_z_velocity", "gravity_scale",
                "max_walk_speed", "max_walk_speed_crouched", "max_acceleration", "air_control", "ledge_check_threshold",
                "perch_radius_threshold", "perch_additional_height", "can_walk_off_ledges", "nav_agent_props"])
        out["jump_max_count"] = s(gp(cdo, "jump_max_count"))
        out["jump_max_hold_time"] = s(gp(cdo, "jump_max_hold_time"))
        comps = []
        try:
            sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
            bp = unreal.load_asset(C.GASP_CHARACTER)
            handles = sds.k2_gather_subobject_data_for_blueprint(bp)
            for h in handles:
                d = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(h)
                o = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(d)
                comps.append({"name": str(unreal.SubobjectDataBlueprintFunctionLibrary.get_variable_name(d)),
                              "class": o.get_class().get_name() if o else None})
        except Exception:  # noqa: BLE001
            err("character_components")
        out["components"] = comps
        export_t3d(unreal.load_asset(C.GASP_CHARACTER), "SandboxCharacter_CMC")
    except Exception:  # noqa: BLE001
        err("character")
    return out


def responses(comp):
    """Collision responses of a primitive to every channel the enum exposes (the Traversable channel is game trace 1)."""
    out = {"collision_enabled": s(comp.get_collision_enabled()), "object_type": s(comp.get_collision_object_type())}
    for name in dir(unreal.CollisionChannel):
        if name.startswith("ECC_"):
            try:
                out[name] = str(comp.get_collision_response_to_channel(getattr(unreal.CollisionChannel, name))).split(".")[-1]
            except Exception:  # noqa: BLE001
                pass
    return out


def spline_points(sp):
    pts = []
    for i in range(sp.get_number_of_spline_points()):
        p = sp.get_location_at_spline_point(i, unreal.SplineCoordinateSpace.WORLD)
        up = sp.get_up_vector_at_spline_point(i, unreal.SplineCoordinateSpace.WORLD)
        pts.append({"loc": [round(p.x, 2), round(p.y, 2), round(p.z, 2)],
                    "up_normal": [round(up.x, 3), round(up.y, 3), round(up.z, 3)]})
    return pts


def traversable_block():
    out = {}
    try:
        bp = unreal.load_asset(C.TRAVERSABLE_BLOCK)
        cls = EAL.load_blueprint_class(C.TRAVERSABLE_BLOCK)
        cdo = unreal.get_default_object(cls)
        out["parent_class"] = s(gp(bp, "parent_class"))
        out["cdo_vars"] = props_of(cdo, ["min_ledge_width", "MinLedgeWidth", "opposite_ledges", "OppositeLedges",
                                         "ledges", "Ledges"])
        comps = []
        sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        for h in sds.k2_gather_subobject_data_for_blueprint(bp):
            d = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(h)
            o = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(d)
            e = {"name": str(unreal.SubobjectDataBlueprintFunctionLibrary.get_variable_name(d)),
                 "class": o.get_class().get_name() if o else None}
            if isinstance(o, unreal.StaticMeshComponent):
                e["mesh"] = s(gp(o, "static_mesh"))
                e["collision_profile"] = s(o.get_collision_profile_name())
                e["relative_scale"] = s(gp(o, "relative_scale3d"))
                e["relative_location"] = s(gp(o, "relative_location"))
            if isinstance(o, unreal.SplineComponent):
                try:
                    e["n_points"] = o.get_number_of_spline_points()
                    e["points_local"] = [s(o.get_location_at_spline_point(i, unreal.SplineCoordinateSpace.LOCAL))
                                         for i in range(o.get_number_of_spline_points())]
                except Exception:  # noqa: BLE001
                    pass
                e["tags"] = [str(t) for t in (gp(o, "component_tags") or [])]
            comps.append(e)
        out["components"] = comps
        out["t3d"] = export_t3d(bp, "LevelBlock_Traversable")
        # spawn test instances: which spline points does the construction script leave at a given actor scale?
        tests = []
        for sc in ((1, 1, 1), (2, 1, 1), (1, 3, 1), (1, 1, 2), (4, 1, 2.5)):
            a = EAS.spawn_actor_from_class(cls, unreal.Vector(0, 0, 0), unreal.Rotator())
            a.set_actor_scale3d(unreal.Vector(*sc))
            try:
                a.rerun_construction_scripts()
            except Exception:  # noqa: BLE001
                pass
            o, ext = a.get_actor_bounds(False)
            t = {"scale": sc, "bounds_min": s(o - ext), "bounds_max": s(o + ext), "splines": {}}
            for sp in a.get_components_by_class(unreal.SplineComponent):
                t["splines"][sp.get_name()] = spline_points(sp)
            for sm in a.get_components_by_class(unreal.StaticMeshComponent):
                t.setdefault("meshes", []).append({"name": sm.get_name(), "mesh": s(gp(sm, "static_mesh")),
                                                   "profile": s(sm.get_collision_profile_name()),
                                                   "responses": responses(sm)})
            tests.append(t)
            EAS.destroy_actor(a)
        out["spawn_tests"] = tests
    except Exception:  # noqa: BLE001
        err("traversable_block")
    return out


def chooser(path, name):
    out = {"path": path}
    try:
        ch = unreal.load_asset(path)
        out["class"] = ch.get_class().get_name()
        out["t3d"] = export_t3d(ch, name)
        names = [n for n in dir(ch) if not n.startswith("_")]
        out["py_attrs"] = [n for n in names if re.search(r"(?i)column|row|result|struct|param|context|output", n)]
        for k in ("column_structs", "columns_structs", "result_structs", "results_structs", "disabled_rows",
                  "context_data", "output_object_type", "result_type", "fallback_result"):
            v = gp(ch, k, "<n/a>")
            if v != "<n/a>":
                try:
                    out.setdefault("props", {})[k] = [str(x) for x in v] if hasattr(v, "__iter__") and not isinstance(v, str) else str(v)
                except Exception:  # noqa: BLE001
                    out.setdefault("props", {})[k] = str(v)
    except Exception:  # noqa: BLE001
        err(f"chooser {name}")
    return out


def assets_named(pattern):
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    hits = []
    for a in ar.get_assets_by_path("/Game", recursive=True):
        n = str(a.asset_name)
        if re.search(pattern, n):
            hits.append({"path": str(a.package_name), "class": str(a.asset_class_path.asset_name)})
    return hits


def main():
    t0 = time.time()
    try:
        REP["traversal_assets"] = assets_named(r"(?i)travers|mantle|vault|hurdle")
        REP["game_mode"] = game_mode()
        REP["character"] = character()
        REP["traversable_block"] = traversable_block()
        REP["choosers"] = {n: chooser(p, n) for n, p in (
            ("CHT_TraversalMontages_CMC", "/Game/Characters/UEFN_Mannequin/Animations/Traversal/CHT_TraversalMontages_CMC"),
            ("CHT_TraversalMontages_Mover", "/Game/Characters/UEFN_Mannequin/Animations/Traversal/CHT_TraversalMontages_Mover"))}
        for p, n in (("/Game/Blueprints/AC_TraversalLogic", "AC_TraversalLogic"),
                     ("/Game/Blueprints/Data/S_TraversalCheckInputs", "S_TraversalCheckInputs"),
                     ("/Game/Blueprints/Data/E_TraversalActionType", "E_TraversalActionType"),
                     ("/Game/Blueprints/GM_Sandbox", "GM_Sandbox"),
                     ("/Game/Levels/LevelPrototyping/LevelBlock", "LevelBlock"),
                     ("/Game/Blueprints/Data/E_MovementMode", "E_MovementMode"),
                     ("/Game/Blueprints/Data/S_CharacterPropertiesForTraversal", "S_CharacterPropertiesForTraversal")):
            a = unreal.load_asset(p)
            REP.setdefault("t3d", {})[n] = export_t3d(a, n) if a else "missing"
    except Exception:  # noqa: BLE001
        err("main")
    REP["passed"] = not REP["errors"]
    REP["sec"] = round(time.time() - t0, 1)
    C.write_json(C.OUT / "gasp_inspect.json", REP)
    unreal.log(f"DJ_STEP_DONE gasp passed={REP['passed']} errors={len(REP['errors'])}")


main()
