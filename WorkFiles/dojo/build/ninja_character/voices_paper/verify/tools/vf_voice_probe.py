"""INDEPENDENT VERIFIER (voices_paper stage, 2026-10-02): read-only probe of DojoLab for jutsu voices + the paper MIs.
Pythonscript commandlet, -nullrhi. Saves NOTHING (no save_asset / save_package / delete call anywhere in this file).
Output: verify/probe.json
"""
import json
import time
import traceback
from pathlib import Path

import unreal

OUT = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\ninja_character\voices_paper\verify\probe.json")
CONTENT = Path(r"C:\Users\Cody\Documents\Unreal Projects\DojoLab\Content")
AR = unreal.AssetRegistryHelpers.get_asset_registry()
EAL = unreal.EditorAssetLibrary
VOICE_DIR = "/Game/Ninja/Audio/Voice"
VOICE_PKGS = ["/Game/Ninja/Audio/Voice/SFX_Voice_GreatFireball", "/Game/Ninja/Audio/Voice/SFX_Voice_KageBunshin"]
KEEP = ["/Game/Ninja/Audio/SFX_HandSeal", "/Game/Ninja/Audio/SFX_JutsuRelease", "/Game/Ninja/Audio/SFX_Chidori",
        "/Game/Ninja/Audio/SFX_FireballLaunch", "/Game/Ninja/Audio/SFX_FireballImpact"]
SOUND_CLASSES = {"SoundWave", "SoundCue", "MetaSoundSource", "SoundWaveProcedural", "SoundAttenuation", "SoundClass",
                 "SoundMix", "SoundSourceBus", "SoundSubmix", "DialogueWave", "DialogueVoice", "SoundNodeWavePlayer"}
R = {"t0": time.strftime("%Y-%m-%d %H:%M:%S"), "engine": unreal.SystemLibrary.get_engine_version()}


def opts():
    return unreal.AssetRegistryDependencyOptions(include_soft_package_references=True,
                                                 include_hard_package_references=True,
                                                 include_searchable_names=False,
                                                 include_soft_management_references=True,
                                                 include_hard_management_references=True)


def pathname(v):
    if v is None:
        return None
    return v.get_path_name() if hasattr(v, "get_path_name") else str(v)


ok = {}
try:
    AR.search_all_assets(True)
    AR.wait_for_completion()
    allg = AR.get_assets_by_path("/Game", recursive=True)
    R["n_assets_game"] = len(allg)
    # 1. every sound-type asset in /Game, and anything whose name or path says voice
    snd, voiceish = [], []
    for ad in allg:
        cls = str(ad.asset_class_path.asset_name)
        pkg = str(ad.package_name)
        name = str(ad.asset_name)
        if cls in SOUND_CLASSES or cls.startswith("Sound") or "MetaSound" in cls:
            snd.append([pkg, cls])
        low = (pkg + name).lower()
        if "voice" in low or "kagebunshin" in low or "kage_bunshin" in low:
            voiceish.append([pkg, cls])
    R["sound_assets_ninja"] = sorted(x for x in snd if x[0].startswith("/Game/Ninja"))
    R["sound_assets_total"] = len(snd)
    R["voiceish_assets_game"] = sorted(voiceish)
    R["voice_dir_exists_ar"] = bool(EAL.does_directory_exist(VOICE_DIR))
    R["voice_dir_has_assets"] = bool(EAL.does_directory_have_assets(VOICE_DIR, True)) if R["voice_dir_exists_ar"] else False
    R["voice_dir_on_disk"] = (CONTENT / "Ninja" / "Audio" / "Voice").exists()
    R["voice_pkgs_exist"] = {p: bool(EAL.does_asset_exist(p)) for p in VOICE_PKGS}
    R["voice_pkgs_referencers"] = {p: sorted(str(x) for x in (AR.get_referencers(p, opts()) or [])) for p in VOICE_PKGS}
    # 2. dependency sweep: every package in /Game whose dependencies name anything under /Game/Ninja/Audio/Voice
    pk = sorted({str(ad.package_name) for ad in allg})
    hits = []
    for p in pk:
        try:
            deps = AR.get_dependencies(p, opts()) or []
        except Exception:  # noqa: BLE001
            continue
        if any(str(d).startswith(VOICE_DIR) for d in deps):
            hits.append(p)
    R["packages_swept"] = len(pk)
    R["packages_depending_on_voice_dir"] = hits
    # 3. every NinjaJutsu (by loaded class) under /Game + BP_NinjaGasp's NinjaJutsu component list
    jutsu = {}
    for ad in allg:
        cls = str(ad.asset_class_path.asset_name)
        if cls == "NinjaJutsu" or str(ad.asset_name).startswith("DA_Jutsu"):
            a = ad.get_asset()
            if a is not None and a.get_class().get_name() == "NinjaJutsu":
                rec = {}
                for k in ("start_voice", "start_voice_volume", "complete_sound", "play_complete_sound"):
                    try:
                        v = a.get_editor_property(k)
                        rec[k] = v if isinstance(v, (bool, float, int)) else pathname(v)
                    except Exception as exc:  # noqa: BLE001
                        rec[k] = "ERR " + str(exc)[:80]
                jutsu[a.get_path_name()] = rec
    R["jutsu_assets"] = jutsu
    bp = unreal.load_asset("/Game/Ninja/Blueprints/BP_NinjaGasp")
    comp = {}
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    for h in sub.k2_gather_subobject_data_for_blueprint(bp):
        o = lib.get_object(lib.get_data(h))
        if o is not None and o.get_class().get_name() == "NinjaJutsuComponent":
            js = []
            for j in o.get_editor_property("jutsus"):
                js.append({"jutsu": pathname(j), "start_voice": pathname(j.get_editor_property("start_voice")) if j else None})
            comp = {"jutsus": js}
            for k in ("seal_sound", "jutsu_complete_sound", "clone_dispel_sound"):
                try:
                    comp[k] = pathname(o.get_editor_property(k))
                except Exception as exc:  # noqa: BLE001
                    comp[k] = "ERR " + str(exc)[:80]
    R["bp_ninja_jutsu_component"] = comp
    # 4. kept SFX and who uses them
    R["keep_sfx"] = {p: {"exists": bool(EAL.does_asset_exist(p)),
                         "referencers": sorted(str(x) for x in (AR.get_referencers(p, opts()) or []))} for p in KEEP}
    # 5. redirectors under /Game/Ninja
    R["redirectors_ninja"] = sorted(str(ad.package_name) for ad in allg if str(ad.asset_class_path.asset_name) == "ObjectRedirector"
                                    and str(ad.package_name).startswith("/Game/Ninja"))
    # 6. the window paper MIs (DojoLab children) and their parents
    MEL = unreal.MaterialEditingLibrary
    paper = {}
    for n in ("MI_DJA_AK_HWinPaperW", "MI_DJA_AK_HWinPaperE", "MI_DJA_AK_Shoji"):
        mi = unreal.load_asset(f"/Game/ArmoryHall/Materials/{n}")
        if mi is None:
            paper[n] = None
            continue
        par = mi.get_editor_property("parent")
        rec = {"parent": pathname(par)}
        for tag, m in (("child", mi), ("parent", par)):
            try:
                rec[tag + "_scalars"] = {str(k): round(MEL.get_material_instance_scalar_parameter_value(m, k), 5)
                                         for k in MEL.get_scalar_parameter_names(m)}
                vv = {}
                for k in MEL.get_vector_parameter_names(m):
                    c = MEL.get_material_instance_vector_parameter_value(m, k)
                    vv[str(k)] = [round(c.r, 4), round(c.g, 4), round(c.b, 4)]
                rec[tag + "_vectors"] = vv
            except Exception as exc:  # noqa: BLE001
                rec[tag + "_err"] = str(exc)[:160]
        try:
            rec["child_overrides_scalar"] = [str(p.parameter_info.name) for p in mi.get_editor_property("scalar_parameter_values")]
            rec["child_overrides_vector"] = [str(p.parameter_info.name) for p in mi.get_editor_property("vector_parameter_values")]
        except Exception as exc:  # noqa: BLE001
            rec["override_err"] = str(exc)[:160]
        paper[n] = rec
    R["paper_mi"] = paper
    ok["no_voice_assets"] = not R["voiceish_assets_game"] and not any(R["voice_pkgs_exist"].values())
    ok["voice_dir_gone"] = not R["voice_dir_exists_ar"] and not R["voice_dir_on_disk"]
    ok["no_package_refs_voice"] = not R["packages_depending_on_voice_dir"] and not any(R["voice_pkgs_referencers"].values())
    ok["every_start_voice_empty"] = bool(jutsu) and all(v.get("start_voice") is None for v in jutsu.values()) and \
        bool(comp.get("jutsus")) and all(j["start_voice"] is None for j in comp["jutsus"])
    ok["keep_sfx_exist_and_used"] = all(v["exists"] and v["referencers"] for v in R["keep_sfx"].values())
    ok["no_ninja_redirectors"] = not R["redirectors_ninja"]
except Exception:  # noqa: BLE001
    R["error"] = traceback.format_exc()[-3000:]
R["ok"] = ok
R["passed"] = bool(ok) and all(ok.values()) and "error" not in R
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(R, indent=1, default=str), encoding="utf-8")
unreal.log(f"VF_PROBE_DONE passed={R['passed']} ok={ok}")
