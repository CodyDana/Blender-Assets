"""DojoLab ninja: NO JUTSU VOICE-OVERS (owner rule 2026-10-02: "remove the voice overs for the jutsu completely").

Library used by dj_ninja_novoice.py (the one-off removal, voices_paper stage) and by dj_ninja_setup.py step_novoice (so
a re-sync from DemoGame_1 re-applies it). Runs inside an Unreal pythonscript commandlet on DojoLab.

Where a jutsu voice can be wired (measured in the voices_paper stage, 2026-10-02):
  - UNinjaJutsu::StartVoice (+ StartVoiceVolume) on the jutsu data assets (/Game/Ninja/Jutsu/DA_Jutsu_*): the ONLY place.
    UNinjaJutsuComponent::BeginJutsu spawns it with UGameplayStatics::SpawnSoundAttached only when StartVoice is set
    (NinjaJutsuComponent.cpp ~238); the C++ hard-codes no sound path, so the C++ stays byte-identical.
  - Nothing else references /Game/Ninja/Audio/Voice (asset registry referencers, hard + soft, and a byte scan of every
    .uasset / .umap under Content): no montage / sequence sound notify, no Blueprint, no level.
What it does (idempotent): StartVoice = None on every NinjaJutsu asset under /Game (and every jutsu in BP_NinjaGasp's
NinjaJutsu list), saved only when it changed; the voice packages are deleted only when nothing references them; any
ObjectRedirector left under /Game/Ninja is fixed up; the non-voice SFX are left alone.
"""
import os
from pathlib import Path

import unreal

EAL = unreal.EditorAssetLibrary
AR = unreal.AssetRegistryHelpers.get_asset_registry()
AT = unreal.AssetToolsHelpers.get_asset_tools()
VOICE_DIR = "/Game/Ninja/Audio/Voice"
VOICE_PACKAGES = ["/Game/Ninja/Audio/Voice/SFX_Voice_GreatFireball", "/Game/Ninja/Audio/Voice/SFX_Voice_KageBunshin"]
KEEP_SFX = ["/Game/Ninja/Audio/SFX_HandSeal", "/Game/Ninja/Audio/SFX_JutsuRelease", "/Game/Ninja/Audio/SFX_Chidori",
            "/Game/Ninja/Audio/SFX_FireballLaunch", "/Game/Ninja/Audio/SFX_FireballImpact"]
CONTENT = Path(r"C:\Users\Cody\Documents\Unreal Projects\DojoLab\Content")
BP_NINJA = "/Game/Ninja/Blueprints/BP_NinjaGasp"


def _opts(hard=True, soft=True):
    return unreal.AssetRegistryDependencyOptions(include_soft_package_references=soft,
                                                 include_hard_package_references=hard,
                                                 include_searchable_names=False, include_soft_management_references=False,
                                                 include_hard_management_references=False)


def referencers(pkg):
    return sorted({str(r) for r in (AR.get_referencers(pkg, _opts()) or [])} - {pkg})


def jutsu_assets():
    """every NinjaJutsu data asset under /Game (by the loaded class name: the saved registry tags may still name the
    old /Script/DemoGame_1 path) + the jutsu list of BP_NinjaGasp's NinjaJutsu component"""
    out = {}
    for ad in AR.get_assets_by_path("/Game/Ninja", recursive=True):
        cls = str(ad.asset_class_path.asset_name)
        if cls in ("NinjaJutsu",) or str(ad.asset_name).startswith("DA_Jutsu_"):
            a = ad.get_asset()
            if a is not None and a.get_class().get_name() == "NinjaJutsu":
                out[a.get_path_name()] = a
    bp = unreal.load_asset(BP_NINJA)
    if bp is not None:
        sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        lib = unreal.SubobjectDataBlueprintFunctionLibrary
        for h in sub.k2_gather_subobject_data_for_blueprint(bp):
            o = lib.get_object(lib.get_data(h))
            if o is not None and o.get_class().get_name() == "NinjaJutsuComponent":
                for j in o.get_editor_property("jutsus"):
                    if j is not None:
                        out[j.get_path_name()] = j
    return out


def jutsu_audio(j):
    rec = {}
    for k in ("start_voice", "start_voice_volume", "complete_sound", "play_complete_sound"):
        try:
            v = j.get_editor_property(k)
            rec[k] = v.get_path_name() if hasattr(v, "get_path_name") else (None if v is None else v)
        except Exception as exc:  # noqa: BLE001
            rec[k] = "ERR " + str(exc)[:80]
    return rec


def byte_scan(tokens=(b"SFX_Voice", b"Audio/Voice")):
    hits = []
    for p in CONTENT.rglob("*"):
        if p.suffix.lower() not in (".uasset", ".umap") or not p.is_file():
            continue
        try:
            b = p.read_bytes()
        except OSError:
            continue
        if any(t in b for t in tokens):
            hits.append(str(p.relative_to(CONTENT)).replace("\\", "/"))
    return sorted(hits)


def redirectors(root="/Game"):
    out = []
    for ad in AR.get_assets_by_path(root, recursive=True):
        if str(ad.asset_class_path.asset_name) == "ObjectRedirector":
            out.append(str(ad.package_name))
    return sorted(out)


def remove_voices(rep, delete=True):
    """clear StartVoice everywhere, delete the voice packages (only with no referencer left), fix redirectors.
    Fills rep; returns True when no voice is wired and no voice package is left (or delete=False and none wired)."""
    AR.search_all_assets(True)
    AR.wait_for_completion()
    rep["voice_packages_before"] = {p: EAL.does_asset_exist(p) for p in VOICE_PACKAGES}
    rep["voice_referencers_before"] = {p: referencers(p) for p in VOICE_PACKAGES}
    rep["byte_scan_before"] = byte_scan()
    js = jutsu_assets()
    rep["jutsu_before"] = {k: jutsu_audio(v) for k, v in sorted(js.items())}
    cleared, saved = [], []
    for path, j in sorted(js.items()):
        if j.get_editor_property("start_voice") is not None:
            j.set_editor_property("start_voice", None)
            cleared.append(path)
            pkg = path.split(".")[0]
            if EAL.save_asset(pkg, only_if_is_dirty=False):
                saved.append(pkg)
    rep["jutsu_cleared"] = cleared
    rep["jutsu_saved"] = saved
    rep["jutsu_after"] = {k: jutsu_audio(v) for k, v in sorted(js.items())}
    AR.search_all_assets(True)
    AR.wait_for_completion()
    try:   # the saved packages' new dependency lists
        AR.scan_modified_asset_files([str(CONTENT / (pkg[len("/Game/"):] + ".uasset")) for pkg in saved])
    except Exception as exc:  # noqa: BLE001
        rep.setdefault("notes", []).append("scan_modified_asset_files: " + str(exc)[:160])
    refs = {p: referencers(p) for p in VOICE_PACKAGES}
    rep["voice_referencers_after_clear"] = refs
    live_refs = sorted({r for v in refs.values() for r in v if not r.startswith(VOICE_DIR)})
    rep["deleted"] = []
    if delete and not live_refs:
        for p in VOICE_PACKAGES:
            if EAL.does_asset_exist(p):
                if EAL.delete_asset(p):
                    rep["deleted"].append(p)
        if EAL.does_directory_exist(VOICE_DIR):
            rep["dir_deleted"] = bool(EAL.delete_directory(VOICE_DIR))
    elif live_refs:
        rep["delete_refused_referencers"] = live_refs
    disk_dir = CONTENT / "Ninja" / "Audio" / "Voice"
    if disk_dir.is_dir() and not any(disk_dir.iterdir()):
        os.rmdir(disk_dir)   # the empty folder, if the editor left it
    rep["voice_dir_on_disk"] = disk_dir.exists()
    rep["voice_packages_after"] = {p: EAL.does_asset_exist(p) for p in VOICE_PACKAGES}
    AR.search_all_assets(True)
    AR.wait_for_completion()
    red = redirectors("/Game/Ninja")
    rep["redirectors_ninja_before_fix"] = red
    if red:
        objs = [unreal.load_asset(r) for r in red]
        AT.fix_up_referencers([o for o in objs if o is not None])
        for r in red:
            if EAL.does_asset_exist(r):
                EAL.delete_asset(r)
    rep["redirectors_game_after"] = redirectors("/Game")
    rep["keep_sfx"] = {p: {"exists": EAL.does_asset_exist(p), "referencers": referencers(p)} for p in KEEP_SFX}
    rep["byte_scan_after"] = byte_scan()
    wired = [k for k, v in rep["jutsu_after"].items() if v.get("start_voice")]
    rep["voice_wired_after"] = wired
    ok = not wired and not rep["byte_scan_after"] and all(v["exists"] for v in rep["keep_sfx"].values())
    if delete:
        ok = ok and not any(rep["voice_packages_after"].values()) and not rep["voice_dir_on_disk"] \
            and not [r for r in rep["redirectors_game_after"] if r.startswith("/Game/Ninja")]
    rep["passed"] = bool(ok)
    return rep["passed"]
