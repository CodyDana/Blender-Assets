"""ArmoryLab post-shell step (pythonscript commandlet, -nullrhi): the performance settings on the HALL VARIANT of L_Armory.

Order, every ArmoryLab sync (SYNC.md 3.2 + BUILD_NOTES "ArmoryLab performance (hall variant)"):
  1 bash Scripts/armory/unreal/run_armory_unreal.sh [... level ...]          (our own steps, the standalone armory)
  2 the shell tool, WorkFiles/shared/armory_hall/tools/ue_armorylab_shell.py  (the hall variant; the last SHARED step)
  3 bash Scripts/armory/unreal/run_armory_unreal.sh hallperf                  (this script)
  4 py -3 -B WorkFiles/shared/armory_hall/tools/check_sync.py --side armory   (exit 0)
It never touches a shell actor's mesh, transform, material, collision or tags, nor the shell's lights, nor any shared
file. It writes neither level.json nor anything under armory_hall_sync/, so check_sync's hall-variant check (shell.json
gates + level.json not newer than shell.json) is unaffected. Idempotent: a level already right is not re-saved.

What it does (ak_common "performance (2026-10-02)"):
  a our local lights (every light in level.json local_lights, found by label): attenuation radius = light_atten_cm(role)
    and lighting channels = light_channels(role). ak_level.py already builds them so; this brings a level saved before
    the change (or touched by anything else) to the same state without a level rebuild.
  b the hall variant's floor tiles (actors tagged AH_Shell whose mesh is a room-kit SM_AK_ piece: AKI_9001..9008,
    placed by the shell tool on channel 0 only) go on lighting channels 0 + 1, like every other room-kit piece
    (ak_level.py place_meshes), so the channel-1 case lights still reach them.
Gates: every level.json light found and read back; tiles found = interior_layout.json's substitution tiles.
Result: WorkFiles/armory/build/unreal/hallperf.json, log line 'AK_STEP_DONE hallperf passed=...'.
"""
import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unreal  # noqa: E402
import ak_common as C  # noqa: E402

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
SHARED = C.ROOT / "WorkFiles" / "shared" / "armory_hall"
REP = {"level": C.LEVEL, "notes": [], "errors": []}


def channels_of(comp):
    ch = comp.get_editor_property("lighting_channels")
    return bool(ch.get_editor_property("channel0")), bool(ch.get_editor_property("channel1"))


def set_channels(comp, c0, c1):
    ch = unreal.LightingChannels()
    ch.set_editor_property("channel0", bool(c0))
    ch.set_editor_property("channel1", bool(c1))
    ch.set_editor_property("channel2", False)
    comp.set_editor_property("lighting_channels", ch)


def main():
    t0 = time.time()
    lv = json.loads((C.OUT / "level.json").read_text(encoding="utf-8"))
    want = {x["name"]: x["role"] for x in lv["local_lights"]}
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    REP["open_ok"] = bool(les.load_level(C.LEVEL))
    actors = EAS.get_all_level_actors()
    by_label = {a.get_actor_label(): a for a in actors}
    changed, lights, missing = 0, {}, []
    for name, role in want.items():
        a = by_label.get(name)
        comp = a.get_component_by_class(unreal.LocalLightComponent) if a else None
        if comp is None:
            missing.append(name)
            continue
        L = {"name": name, "role": role}
        r_want, ch_want = C.light_atten_cm(L), C.light_channels(L)
        r_got, ch_got = float(comp.get_editor_property("attenuation_radius")), channels_of(comp)
        if abs(r_got - r_want) > 0.5:
            comp.set_editor_property("attenuation_radius", r_want)
            changed += 1
        if ch_got != ch_want:
            set_channels(comp, *ch_want)
            changed += 1
        lights[name] = {"role": role, "atten_cm": float(comp.get_editor_property("attenuation_radius")),
                        "channels": list(channels_of(comp)), "was": {"atten_cm": r_got, "channels": list(ch_got)}}
    bad = [n for n, v in lights.items() if abs(v["atten_cm"] - C.light_atten_cm(v)) > 0.5
           or tuple(v["channels"]) != C.light_channels(v)]
    tiles = []
    for a in actors:
        if unreal.Name("AH_Shell") not in list(a.tags) or not isinstance(a, unreal.StaticMeshActor):
            continue
        smc = a.static_mesh_component
        m = smc.static_mesh
        if m is None or not C.is_interior_piece(m.get_name()):
            continue
        if channels_of(smc) != (True, True):
            set_channels(smc, True, True)
            changed += 1
        tiles.append({"label": a.get_actor_label(), "channels": list(channels_of(smc))})
    I = json.loads((SHARED / "interior_layout.json").read_text(encoding="utf-8"))
    n_tiles_want = sum(1 for it in I["instances"] if it.get("src_armory", {}).get("layout_index") is None)
    hall_variant = any(unreal.Name("AH_Shell") in list(a.tags) for a in actors)
    REP.update({"hall_variant": hall_variant, "lights_found": len(lights), "lights_want": len(want),
                "lights_missing": missing, "lights_bad": bad, "tiles": tiles, "tiles_want": n_tiles_want if hall_variant else 0,
                "changed_properties": changed,
                "by_role": {r: {"atten_cm": C.light_atten_cm({"role": r}), "channels": list(C.light_channels({"role": r})),
                                "n": sum(1 for v in want.values() if v == r)} for r in sorted(set(want.values()))}})
    REP["saved"] = bool(les.save_current_level()) if changed else "unchanged"
    REP["passed"] = (REP["open_ok"] and not missing and not bad and REP["saved"] in (True, "unchanged")
                     and len(tiles) == REP["tiles_want"] and all(t["channels"] == [True, True] for t in tiles))
    REP["sec"] = round(time.time() - t0, 1)


try:
    main()
except Exception:  # noqa: BLE001
    REP["errors"].append(traceback.format_exc()[-3000:])
    REP["passed"] = False
C.write_json(C.OUT / "hallperf.json", REP)
unreal.log(f"AK_STEP_DONE hallperf passed={REP.get('passed')} lights={REP.get('lights_found')}/{REP.get('lights_want')} "
           f"tiles={len(REP.get('tiles', []))} changed={REP.get('changed_properties')} saved={REP.get('saved')}")
