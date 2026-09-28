"""Walk-in check (fresh commandlet, -nullrhi, read-only): can the player enter the armory as Manny?

Gates:
 1 game mode   the project default game mode is BP_ThirdPersonGameMode and its default pawn is BP_ThirdPersonCharacter;
               the character's skeletal mesh (SKM_Manny*) and anim class load.
 2 references  every package the character and game mode depend on (recursively, /Game only) exists on disk.
 3 level       L_Armory loads, has exactly one PlayerStart, at layout.json "player_start" (exterior stage: the courtyard path)
               facing the entrance, and
               the level's WorldSettings do not override the game mode.
 4 walk        capsule sweeps (the character's own capsule size) along the walking route are not blocked: from outside
               the door through it to the entry mat, then down the west and east aisles to the steps.
Result: WorkFiles/armory/build/unreal/character.json
"""
import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unreal  # noqa: E402
import ak_common as C  # noqa: E402

EAL = unreal.EditorAssetLibrary
AR = unreal.AssetRegistryHelpers.get_asset_registry()
GM = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonGameMode"
CH = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"


def V(t):
    return unreal.Vector(float(t[0]), float(t[1]), float(t[2]))


def bl(x, y, z):
    """Blender metres -> Unreal cm (x*100, -y*100, z*100)."""
    return (x * 100.0, -y * 100.0, z * 100.0)


def deps(pkg, seen):
    opts = unreal.AssetRegistryDependencyOptions(include_soft_package_references=False,
                                                 include_hard_package_references=True)
    for d in AR.get_dependencies(pkg, opts) or []:
        d = str(d)
        if d.startswith("/Game") and d not in seen:
            seen.add(d)
            deps(d, seen)
    return seen


def main():
    t0 = time.time()
    rep = {"engine": unreal.SystemLibrary.get_engine_version(), "gates": {}}
    try:
        # 1 game mode and character
        gm_cls = unreal.EditorAssetLibrary.load_blueprint_class(GM)
        ch_cls = unreal.EditorAssetLibrary.load_blueprint_class(CH)
        gm = unreal.get_default_object(gm_cls)
        pawn = gm.get_editor_property("default_pawn_class")
        ch = unreal.get_default_object(ch_cls)
        mesh_comp = ch.get_editor_property("mesh")
        skm = mesh_comp.get_editor_property("skeletal_mesh_asset") if mesh_comp else None
        anim = mesh_comp.get_editor_property("anim_class") if mesh_comp else None
        cap = ch.get_editor_property("capsule_component")
        radius = float(cap.get_editor_property("capsule_radius")) if cap else 42.0
        half = float(cap.get_editor_property("capsule_half_height")) if cap else 96.0
        ini = (C.PROJECT_DIR / "Config" / "DefaultEngine.ini").read_text(encoding="utf-8")
        g1 = {"project_default_game_mode": "GlobalDefaultGameMode=/Game/ThirdPerson/Blueprints/BP_ThirdPersonGameMode" in ini,
              "default_pawn": pawn.get_name() if pawn else None,
              "skeletal_mesh": skm.get_path_name() if skm else None,
              "anim_class": anim.get_name() if anim else None,
              "capsule_radius_cm": radius, "capsule_half_height_cm": half}
        g1["passed"] = bool(g1["project_default_game_mode"] and pawn and "ThirdPersonCharacter" in pawn.get_name()
                            and skm and "Manny" in skm.get_name() and anim)   # the user asked for Manny
        rep["gates"]["1_game_mode"] = g1
        # 2 references
        seen = set()
        for pkg in (GM, CH):
            deps(pkg, seen)
        missing = sorted(p for p in seen if not EAL.does_asset_exist(p))
        rep["gates"]["2_references"] = {"n_dependencies": len(seen), "missing": missing, "passed": not missing}
        # 3 level
        les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        loaded = les.load_level(C.LEVEL)
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
        starts = [a for a in actors if isinstance(a, unreal.PlayerStart)]
        ws = world.get_world_settings()
        override = ws.get_editor_property("default_game_mode") if ws else None
        g3 = {"loaded": bool(loaded), "player_starts": len(starts), "game_mode_override": override.get_name() if override else None}
        if starts:
            loc, rot = starts[0].get_actor_location(), starts[0].get_actor_rotation()
            g3["start_cm"] = [round(loc.x, 1), round(loc.y, 1), round(loc.z, 1)]
            g3["start_yaw"] = round(rot.yaw, 1)
            # exterior stage: at layout.json "player_start" (the courtyard path), facing +Blender Y = UE -Y (yaw -90)
            want, _yaw = C.player_start(C.load_layout())
            g3["inside_past_door"] = abs(loc.x - want[0]) < 1.0 and abs(loc.y - want[1]) < 1.0
            g3["faces_into_room"] = abs(((rot.yaw + 90.0) + 180.0) % 360.0 - 180.0) < 20.0
        g3["passed"] = bool(loaded and len(starts) == 1 and not override and g3.get("inside_past_door")
                            and g3.get("faces_into_room"))
        rep["gates"]["3_level"] = g3
        # 4 walk: capsule sweeps at standing height (capsule centre = floor + half height + 2 cm)
        zc = half + 2.0
        routes = {   # exterior stage: the 12 x 16 m hall and the courtyard (walk_check.py is authoritative)
            "courtyard_start_through_entrance_to_mat": [(6.0, -10.4), (6.0, -1.9), (6.0, 1.2)],
            "mat_to_west_aisle_to_steps": [(6.0, 1.2), (3.0, 1.5), (3.0, 12.3)],
            "mat_to_east_aisle_to_steps": [(6.0, 1.2), (9.0, 1.5), (9.0, 12.3)],
            "centre_gap_case1_case2": [(3.0, 5.7), (9.0, 5.7)],
            "CONTROL_must_hit_case1": [(6.0, 1.2), (6.0, 3.6)],   # straight into case 1: proves the sweeps collide
        }
        g4 = {"routes": {}}
        for name, pts in routes.items():
            legs = []
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                a, b = V(bl(x0, y0, 0)), V(bl(x1, y1, 0))
                a.z = b.z = zc
                hit = unreal.SystemLibrary.capsule_trace_single(world, a, b, radius, half - 2.0,
                                                                unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [],
                                                                unreal.DrawDebugTrace.NONE, True)
                blocked = None
                if hit is not None:
                    t = hit.to_tuple()
                    if t[0]:   # blocking hit
                        actor = t[9] if len(t) > 9 else None
                        blocked = {"at_cm": [round(v, 1) for v in (t[4].x, t[4].y, t[4].z)],
                                   "actor": actor.get_actor_label() if actor else None}
                legs.append({"from_bl_m": [x0, y0], "to_bl_m": [x1, y1], "blocked": blocked})
            g4["routes"][name] = {"legs": legs, "clear": all(l["blocked"] is None for l in legs)}
        g4["control_blocked"] = not g4["routes"]["CONTROL_must_hit_case1"]["clear"]
        g4["passed"] = g4["control_blocked"] and all(r["clear"] for k, r in g4["routes"].items() if not k.startswith("CONTROL"))
        rep["gates"]["4_walk"] = g4
        # gate 4 is informational: capsule traces do not collide in a -nullrhi commandlet (the control sweep into case 1
        # passes through). The authoritative walk check is Scripts/armory/walk_check.py against the same UCX hulls.
        rep["gates"]["4_walk"]["informational_only"] = True
        rep["passed"] = all(g["passed"] for k, g in rep["gates"].items() if k != "4_walk")
    except Exception:  # noqa: BLE001
        rep["error"] = traceback.format_exc()[-3000:]
        rep["passed"] = False
    rep["sec"] = round(time.time() - t0, 1)
    C.write_json(C.OUT / "character.json", rep)
    unreal.log(f"AK_STEP_DONE character passed={rep['passed']}")


main()
