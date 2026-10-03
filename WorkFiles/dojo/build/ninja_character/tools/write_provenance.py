"""Writes ../PORT_PROVENANCE.md and ../build/provenance.json from the survey, the copy logs, the build reports and the
current file hashes (plain Python, no Unreal). Re-run after any re-sync.

    py -3 -B write_provenance.py
"""
import hashlib
import json
import subprocess
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
NC = HERE.parent
B = NC / "build"
DEMO = Path("C:/Users/Cody/Documents/Unreal Projects/DemoGame_1")
DOJO = Path("C:/Users/Cody/Documents/Unreal Projects/DojoLab")
BACKUP = NC / "start_backup"


def sha(p: Path):
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def git(*a):
    return subprocess.run(["git", "--no-optional-locks", "-C", str(DEMO), *a], capture_output=True, text=True).stdout.strip()


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8")) if Path(p).is_file() else {}


cl = load(NC / "survey" / "closure.json")
cpp_log = load(B / "copy_log_cpp.json")
con_log = load(B / "copy_log_content.json")
setup = load(B / "setup.json")
check = load(B / "check.json")
probe = load(B / "probe" / "probe_ninja.json")
probe_g = load(B / "probe" / "probe_gasp.json")
backup_sums = {}
if (BACKUP / "SHA256SUMS.txt").is_file():
    for ln in (BACKUP / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        h, _, f = ln.partition(" *")
        backup_sums[f.lstrip("./")] = h

MODIFIED_AFTER_COPY = {
    "Content/Ninja/Blueprints/BP_NinjaGasp.uasset": "B4: SCS components NinjaAirJump, NinjaLockOn, NinjaStance, NinjaFreeLook, "
                                                    "NinjaCombat removed (dj_ninja_setup.py), compiled, saved. PLAY-TEST FIX T1 (2026-10-02): CDO "
                                                    "jump_max_count 2 -> 1 = SandboxCharacter_CMC's (dj_ninja_fixjump.py; also "
                                                    "applied by dj_ninja_setup.py from now on); before the fix sha256 0bfbdc23eb88"
                                                    "859480a884361b51be679ea0bcff09a6e081cdde4c6330a4c259, backup "
                                                    "test/backup_before_fixjump/",
    "Content/Ninja/Input/IMC_NinjaGasp.uasset": "B5: trimmed from 24 rows to the 8 jutsu rows (dj_ninja_setup.py), saved",
    "Content/Ninja/Jutsu/DA_Jutsu_ShadowClone.uasset": "NO VOICE (owner rule 2026-10-02): StartVoice SFX_Voice_KageBunshin -> None "
                                                       "(dj_ninja_novoice.py), saved; section 5b",
    "Content/Ninja/Jutsu/DA_Jutsu_GreatFireball.uasset": "NO VOICE (owner rule 2026-10-02): StartVoice SFX_Voice_GreatFireball -> "
                                                         "None (dj_ninja_novoice.py), saved; section 5b",
}
# owner rule 2026-10-02: the jutsu voice-overs were deleted from DojoLab (never copy them again; section 5b)
REMOVED = {
    "Content/Ninja/Audio/Voice/SFX_Voice_GreatFireball.uasset": "REMOVED (owner rule 2026-10-02: no jutsu voice-overs; 5b)",
    "Content/Ninja/Audio/Voice/SFX_Voice_KageBunshin.uasset": "REMOVED (owner rule 2026-10-02: no jutsu voice-overs; 5b)",
}
VP = NC / "voices_paper"
novoice = load(VP / "novoice.json")
vcheck = load(VP / "check.json")
vjutsu = load(VP / "jutsu_after" / "report_ninja.json")
NEW_FILES = [
    ("Source/DojoLab.Target.cs", "game target (BuildSettingsVersion.V7, Unreal5_8, ExtraModuleNames DojoLab)"),
    ("Source/DojoLabEditor.Target.cs", "editor target (same settings)"),
    ("Source/DojoLab/DojoLab.Build.cs", "module rules: Core, CoreUObject, Engine, InputCore, EnhancedInput, Niagara; "
                                        "private AIModule; PublicDefinitions DEMOGAME_1_API=DOJOLAB_API"),
    ("Source/DojoLab/DojoLab.h", "module header (CoreMinimal)"),
    ("Source/DojoLab/DojoLab.cpp", "IMPLEMENT_PRIMARY_GAME_MODULE(FDefaultGameModuleImpl, DojoLab, \"DojoLab\")"),
    ("Source/DojoLab/DojoNinjaCameraSubsystem.h", "per-pawn camera switch (D3), new code"),
    ("Source/DojoLab/DojoNinjaCameraSubsystem.cpp", "per-pawn camera switch (D3), new code"),
    ("Content/Dojo/Blueprints/GM_DojoNinja.uasset", "new game mode: Blueprint child of GM_Dojo, DefaultPawnClass BP_NinjaGasp_C"),
    ("Binaries/Win64/UnrealEditor-DojoLab.dll", "built module (Build.bat DojoLabEditor Win64 Development)"),
]
CHANGED = [
    ("DojoLab.uproject", "\"Modules\": [{\"Name\": \"DojoLab\", \"Type\": \"Runtime\", \"LoadingPhase\": \"Default\"}] added; "
                         "plugins unchanged"),
    ("Config/DefaultEngine.ini", "[CoreRedirects] +PackageRedirects=(OldName=\"/Script/DemoGame_1\",NewName=\"/Script/DojoLab\") "
                                 "appended; GlobalDefaultGameMode GM_Dojo -> GM_DojoNinja. Nothing else (GASP's DDCvars, "
                                 "collision channels, PoseSearch, r.SkinCache.DefaultBehavior=0 unchanged)"),
    ("Content/Dojo/Maps/L_Dojo.umap", "World Settings GameMode override GM_Dojo -> GM_DojoNinja (resaved by the commandlet; "
                                      "PlayerStarts P1 (1450, -1050, 95) yaw 0 and P2 (2950, -1050, 95) yaw 180 unchanged)"),
]


def md_table(rows, head):
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def main():
    head = git("rev-parse", "HEAD")
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    dem = cl.get("demogame1", {})
    ov = cl.get("overrides", {})
    cpp_rows, cpp_json = [], []
    why = {c["file"]: (c["action"], c.get("why", "")) for c in cl.get("cpp", [])}
    for f in cpp_log.get("files", []):
        dst = DOJO / f["rel"]
        now = sha(dst)
        act, w = why.get(f["origin"], ("", ""))
        cpp_rows.append([f"`{f['rel']}`", f"`{f['origin']}`", f["sha256"], f["bytes"], act,
                         "identical" if now == f["sha256"] else f"CHANGED {now}"])
        cpp_json.append({**f, "dojo_sha256_now": now, "action": act, "why": w})
    skipped = [[f"`{c['file']}`", c["sha256"], c["action"], c.get("why", "")] for c in cl.get("cpp", [])
               if not c["action"].startswith("copy")]
    con_rows, con_json = [], []
    for f in sorted(con_log.get("files", []), key=lambda r: r["package"]):
        now = sha(DOJO / f["rel"])
        note = MODIFIED_AFTER_COPY.get(f["rel"]) or REMOVED.get(f["rel"])
        if f["rel"] in REMOVED and now is None:
            state = REMOVED[f["rel"]]
        else:
            state = "identical" if now == f["sha256"] else (f"modified: {now}" if note else f"DIFFERS: {now}")
        origin = "43fd6ce LFS" if f["origin"].startswith("lfs:") else "working tree"
        con_rows.append([f"`{f['package']}`", f["copy_class"], origin, f["sha256"], f["bytes"], state])
        con_json.append({**f, "dojo_sha256_now": now, "modified_after_copy": note})
    new_rows = [[f"`{p}`", sha(DOJO / p) or "-", w] for p, w in NEW_FILES]
    chg_rows = [[f"`{p}`", backup_sums.get(p, "-"), sha(DOJO / p), w] for p, w in CHANGED]
    n_core = sum(1 for f in con_log.get("files", []) if f["copy_class"] == "core")
    n_feat = sum(1 for f in con_log.get("files", []) if f["copy_class"] == "feature_only")
    by_folder = {}
    for f in con_log.get("files", []):
        parts = f["package"].split("/")
        k = "/".join(parts[:4]) if parts[2] in ("MetaHumans", "Ninja", "NiagaraExamples", "BareNinja_AnimSet") else "/".join(parts[:4])
        by_folder[k] = by_folder.get(k, 0) + 1
    unmod = sum(1 for r in con_json if r["dojo_sha256_now"] == r["sha256"])
    n_mod = sum(1 for r in con_json if r["dojo_sha256_now"] and r["dojo_sha256_now"] != r["sha256"])
    n_removed = sum(1 for r in con_json if r["rel"] in REMOVED and r["dojo_sha256_now"] is None)
    bp_sha = sha(DOJO / "Content/Ninja/Blueprints/BP_NinjaGasp.uasset")
    da_rows = [[f"`{k}`", (v.get("start_voice") or "-"), (novoice.get("jutsu_after", {}).get(k, {}).get("start_voice") or "None"),
                sha(DOJO / ("Content" + k.split(".")[0][len("/Game"):] + ".uasset")) or "-"]
               for k, v in sorted(novoice.get("jutsu_before", {}).items())]
    jr = (vjutsu.get("results") or {}).get("jutsu") or {}
    jt_rows = []
    for name in ("ShadowClone", "GreatFireball", "Summoning", "Chidori"):
        for mode in ("stand", "walk", "run"):
            r = jr.get(f"{mode}_{name}")
            if r:
                jt_rows.append([f"{mode} {name}", "yes" if r.get("completed") else "NO", r.get("n_seal_events"),
                                ", ".join(r.get("audio_components_seen") or []) or "-",
                                ", ".join(r.get("voice_components") or []) or "none"])
    gm_dojo_sha = sha(DOJO / "Content/Dojo/Blueprints/GM_Dojo.uasset")

    md = f"""# Ninja character port: provenance (DemoGame_1 -> DojoLab)

Written {date.today().isoformat()} by `tools/write_provenance.py` from the survey (`survey/closure.json`), the copy logs
(`build/copy_log_cpp.json`, `build/copy_log_content.json`), the build reports (`build/setup.json`, `build/check.json`,
`build/probe/*.json`) and the files on disk. Machine-readable twin: `build/provenance.json`.

PRIVATE LAB ONLY (R7): the jutsu carry Naruto technique names (Chidori, Kage Bunshin, Goukakyuu) and
`SFX_HandSeal`, `SFX_JutsuRelease` and `SFX_Chidori` are third-party anime audio. Nothing from this port may go into
anything sold or shared, and no DojoLab footage with these sounds or names may be published, until they are replaced
(DemoGame_1 has own-work fallbacks: `make_jutsu_sfx.py`, `SFX_ChidoriCharge`). **The two jutsu voice-overs
(`SFX_Voice_KageBunshin`, `SFX_Voice_GreatFireball`) were REMOVED from DojoLab on 2026-10-02 (owner rule: no jutsu voices
anywhere) and must never be copied or wired again (section 5b).**

## 1. Source

| | |
|---|---|
| Project | `{DEMO}` (READ ONLY: plain file reads and `git --no-optional-locks` only; never opened in an editor) |
| Branch / HEAD at the port | `{branch}` / **`{head}`** ({dem.get('head_subject', '')}) |
| Working tree | dirty ({len(dem.get('working_tree_dirty', []))} entries, none under `Source/`); `Source/` is identical to HEAD |
| Male-era commit (LFS blobs) | **`{dem.get('male_era_commit', '')}`** ({dem.get('male_era_subject', '')}) |
| `/Game/Ninja/Blueprints/BP_NinjaGasp` | LFS oid `{ov.get('/Game/Ninja/Blueprints/BP_NinjaGasp', {}).get('oid', '')}` (working-tree file `6477bbe5...` NOT used: it adds the private catwalk walk tier) |
| `/Game/Ninja/Blueprints/BP_NinjaVisual` | LFS oid `{ov.get('/Game/Ninja/Blueprints/BP_NinjaVisual', {}).get('oid', '')}` (working-tree file `df019968...` NOT used: it hard-imports the private BP_MH_PlayerFemale) |
| Everything else | the working tree at the port (sha256 of every file below; each matched the survey's hash at copy time) |
| Never copied | MH_PlayerFemale, Hiyuki, 2B, the catwalk / Mocap folders, anything `_Private` (`closure.json` `private_blocked` = {len(cl.get('summary', {}).get('private_blocked', []) or [])}; the copy tool refuses such paths) |

## 2. What was copied

- C++: **{len(cpp_rows)} files** byte-identical into `Source/DojoLab/` (15 classes). Every copied file is still identical
  in DojoLab: **{sum(1 for r in cpp_json if r['dojo_sha256_now'] == r['sha256'])} / {len(cpp_rows)}**. (The survey's
  "31 files" was a miscount: 15 classes = 14 .h/.cpp pairs + `NinjaJutsu.h` = 29 files.)
- Content: **{len(con_rows)} packages** ({n_core} core + {n_feat} feature-only, {con_log.get('counts', {}).get('bytes', 0):,} bytes), all
  `.uasset`, at their DemoGame_1 `/Game` paths (no path collided, so nothing was remapped and no redirector was made).
  {unmod} are byte-identical to the source; {n_mod} were changed afterwards on purpose (sections 3 and 5b) and {n_removed}
  were deleted on purpose (the jutsu voice-overs, section 5b). No `.wav` / `.png` import
  source was copied. No DojoLab file was overwritten (every destination was asserted absent first).
- Kept as they were in DojoLab (not copied): the 38 identical GASP packages and the 13 packages that differ (D1: DojoLab's
  MetaHumans/Common hair / lash materials, skeletons and control rigs, GASP's `SK_Mannequin`, `IMC_Sandbox`).

## 3. Every change made

### 3.1 Copied files changed after the copy

{md_table([[f"`{k}`", v] for k, v in MODIFIED_AFTER_COPY.items()], ["File", "Change"])}

No copied C++ file was edited.

### 3.2 DojoLab files changed (start backup in `start_backup/`, `SHA256SUMS.txt`)

{md_table(chg_rows, ["File", "sha256 before (backup)", "sha256 now", "Change"])}

`Content/Dojo/Blueprints/GM_Dojo.uasset` is unchanged (sha256 `{gm_dojo_sha}`; still DefaultPawnClass
SandboxCharacter_CMC: the reference route).

### 3.3 New DojoLab files

{md_table(new_rows, ["File", "sha256", "What"])}

How the copied sources build unchanged: the classes are declared `class DEMOGAME_1_API ...`; `DojoLab.Build.cs` adds
`PublicDefinitions.Add("DEMOGAME_1_API=DOJOLAB_API")`, so the token resolves to this module's export macro (UHT accepted
it; Build.bat: 22 actions, 0 warnings, 0 errors, 51 s). The copied assets name their classes `/Script/DemoGame_1.<Class>`;
the `[CoreRedirects]` package redirect maps all of them to `/Script/DojoLab` (measured: every class resolves through the
old path, `check.json` gate A).

The camera (D3): DemoGame_1 sets `DDCVar.NewGameplayCameraSystem.Enable=0` project-wide. DojoLab keeps GASP's 1 in the
ini; `UDojoNinjaCameraSubsystem` (a world subsystem, Game and PIE worlds) sets the cvar for each pawn the game spawns,
before it is possessed: 0 for a pawn with `UNinjaJutsuComponent` (BP_NinjaGasp and its clones), the original value back for
`/Game/Blueprints/SandboxCharacter_*`. `dojo.ninja.camera_switch 0` turns it off. The BP's own spring arm (375, socket
offset 0, lag 12, FOV 85) and `GameplayCamera` auto-activate off / `Camera(NotUsedByDefault)` auto-activate on came with
the 43fd6ce BP.

### 3.4 Scripts (Blender_Projects, this chat's pipeline)

- New: `Scripts/dojo/unreal/run_ninja_port.sh` (build / setup / ini / check), `dj_ninja_setup.py`, `dj_ninja_check.py`,
  `dj_ninja_game_probe.py` + `run_ninja_probe.ps1` (-game probe), `WorkFiles/dojo/build/ninja_character/tools/`
  (`port_copy.py`, `scan_log.py`, this generator).
- Play-test stage (2026-10-02), new: `Scripts/dojo/unreal/dj_ninja_playtest.py` (suites look / move / jutsu / routes),
  `dj_ninja_perf.py`, `run_ninja_playtest.ps1`, `dj_ninja_fixjump.py`; `run_ninja_port.sh` gained the `fixjump` step;
  `dj_ninja_setup.py` step_bp also applies T1. Tools: `tools/pt_media.py`, `pt_compare_demogame.py`, `pt_scan.py`,
  `pt_summary.py`.
- Changed: `Scripts/dojo/unreal/dj_verify.py` gate 4 and `dj_sc_verify.py` gate 5 accept GM_DojoNinja (GM_Dojo's child
  with BP_NinjaGasp) as the project default and the world override, and still require GM_Dojo -> SandboxCharacter_CMC.
  Originals in `start_backup/scripts/`.

## 4. Switching pawns

- Default: `L_Dojo` -> GM_DojoNinja -> BP_NinjaGasp (project default and the world override).
- GASP's reference pawn: `-game` URL `L_Dojo?game=/Game/Dojo/Blueprints/GM_Dojo.GM_Dojo_C` (a URL game beats the world
  override; measured: SandboxCharacter_CMC with GASP's own camera, `build/probe/probe_gasp.json`), or in the editor
  set L_Dojo's World Settings GameMode back to GM_Dojo. GASP's own `DDCvar.PawnClass <i>` indexes GM_Sandbox's
  PawnClasses (Mover, CMC) on either mode (GM_Sandbox's logic; not measured in this stage).
- The offline traversal checks (walk_check / climb_check) read the SandboxCharacter_CMC CDO, untouched; BP_NinjaGasp's
  capsule equals it (r 30 / half height 86, `check.json` gate D).

## 5. Re-syncing from DemoGame_1 later

1. Read `DemoGame_1/CLAUDE.md`; note `git rev-parse HEAD` and whether the player is still the female MetaHuman (then keep
   the 43fd6ce blobs for BP_NinjaGasp / BP_NinjaVisual, or pick a newer MALE commit:
   `git log -- Content/Ninja/Blueprints/BP_NinjaVisual.uasset`). Never copy a package whose imports name
   `BP_MH_PlayerFemale` or any private path.
2. C++: compare `Source/DemoGame_1/<file>` sha256 with section 6; copy changed files byte-identical; look for new includes
   or new component classes (a new class reached by `FindComponentByClass` must be copied too); rebuild with
   `run_ninja_port.sh build` (no editor on DojoLab; it waits for any UnrealEditor-Cmd).
3. Content: re-run `survey/tools/closure2.py <new.json>` (read-only, header based, same roots); copy new / changed `copy`
   packages over the earlier port copies after backing those up (`tools/port_copy.py` refuses to overwrite: move the old
   files to a backup folder first); never overwrite an `in_dojo_DIFFERENT` package without the owner's sign-off (D1).
4. `run_ninja_port.sh setup check` re-applies B4 / B5 / T1 (idempotent) and re-checks; then the -game probe
   (`run_ninja_probe.ps1`) and the play tests (`run_ninja_playtest.ps1`, suites look / move / jutsu / routes, and
   `dj_ninja_perf.py`), then `py -3 -B tools/write_provenance.py`.
5. Never resave a copied asset before the module is built and the CoreRedirect is in `DefaultEngine.ini`.
6. **No jutsu voices (owner rule 2026-10-02):** never copy `/Game/Ninja/Audio/Voice` (or any `SFX_Voice_*`) and never set
   a `StartVoice` (or `StartVoiceVolume` for one) on any jutsu. `closure2.py` marks them `VOICE_BLOCKED`, `port_copy.py`
   refuses them, and `run_ninja_port.sh setup` (step_novoice) clears any `StartVoice` a re-synced DA_Jutsu brings and
   deletes the folder if it reappears; `run_ninja_port.sh check` gate G fails on any voice. DojoLab's DA_Jutsu_ShadowClone
   / GreatFireball now differ from DemoGame_1's, so step 3 lists them as `in_dojo_DIFFERENT` (never overwritten without
   the owner's sign-off).

## 5a. Play-test stage (2026-10-02)

Results: `test/RESULTS.json` / `test/RESULTS.md` (all suites, both pawns, perf, log scans); BUILD_NOTES section
"2026-10-02 - NINJA CHARACTER: play tests".

Every change this stage made to DojoLab:

| What | Change | Why |
|---|---|---|
| `Content/Ninja/Blueprints/BP_NinjaGasp.uasset` | T1: CDO `jump_max_count` 2 -> 1 (the value read from GASP's `SandboxCharacter_CMC` CDO), compiled, saved (`run_ninja_port.sh fixjump`) | measured in -game: a second SpaceBar in the air rose to 243 cm (single jump 127.6 cm; SandboxCharacter_CMC 127.5 cm for both presses). DemoGame_1's double jump = this value (written by its `setup_ninja_gasp.py`) + the flip of `UNinjaAirJumpComponent`; the owner excluded it, the build removed only the component |

No C++ file, no other asset, no ini, no level and no plugin changed in this stage. Harness-only fixes (no DojoLab file):
the runner no longer passes `-dpcvars=au.MuteAudio=1` (a cheat cvar from a device profile raised an engine ensure in
ConfigUtilities.cpp in jutsu run 1; the probe mutes with the console command instead); the route walker advances in
waypoint order (a route that folds back on itself, ARM_deck_strip_in_front_of_hero_table, stalled both pawns).

Re-sync note: `dj_ninja_setup.py` step_bp now applies T1 too (idempotent), so section 5 step 4 keeps it.

## 5b. Jutsu voice-overs removed (voices_paper stage, 2026-10-02)

Owner rule (2026-10-02): "remove the voice overs for the jutsu completely". Report: `voices_paper/novoice.json`, check
`voices_paper/check.json`, -game re-test `voices_paper/jutsu_after/`; BUILD_NOTES section "2026-10-02 - NINJA CHARACTER:
jutsu voices removed + window paper at sunset".

- Where a voice was wired (measured): ONLY `UNinjaJutsu::StartVoice` on two data assets. The C++ spawns the sound only
  when that property is set and names no sound itself (`NinjaJutsuComponent.cpp` BeginJutsu), so **no C++ file was
  edited** (29 / 29 still byte-identical). BP_NinjaGasp's NinjaJutsu component only lists the four DA_Jutsu assets (no
  per-instance voice), no montage / sequence sound notify and no level or Blueprint referenced the voices (asset registry
  referencers, hard + soft, and a byte scan of every .uasset / .umap under Content).
- Removed: `/Game/Ninja/Audio/Voice/SFX_Voice_GreatFireball`, `/Game/Ninja/Audio/Voice/SFX_Voice_KageBunshin` and the
  folder; redirectors under /Game/Ninja afterwards: {len([r for r in novoice.get("redirectors_game_after", []) if r.startswith("/Game/Ninja")])} (the
  {len(novoice.get("redirectors_game_after", []) or [])} elsewhere under /Game are GASP / sample-content redirectors that predate the port, untouched). Kept (non-voice SFX): SFX_HandSeal, SFX_JutsuRelease,
  SFX_Chidori, SFX_FireballLaunch, SFX_FireballImpact, and the component's clone-dispel sound.
- `BP_NinjaGasp.uasset` sha256 now **{bp_sha}** (not re-saved: it references the DA_Jutsu assets, not the voices).

{md_table(da_rows, ["Jutsu asset", "StartVoice before", "StartVoice now", "sha256 now"])}

Headless check (fresh process, `run_ninja_port.sh check`, gates A-G): {vcheck.get("gates")}.

-game re-test by the real keys (F / Two / Three / Four), with the audio device on (`-Sound`, output muted), every
AudioComponent in the world recorded at 10 Hz ("seen" includes finished components still alive from the cast before;
the positive control before the removal, `voices_paper/jutsu_before/`, listed both voice components and 9 `voice ...
(playing)` log lines with the same harness; after: none and 0):

{md_table(jt_rows, ["cast", "completed", "seals", "audio components seen", "voice components"])}

## 6. C++ files (DemoGame_1 -> DojoLab, byte-identical)

{md_table(cpp_rows, ["DojoLab file", "Source", "sha256", "bytes", "role", "now"])}

Not copied:

{md_table(skipped, ["Source", "sha256", "action", "why"])}

## 7. Content packages ({len(con_rows)})

{md_table(con_rows, ["Package", "class", "from", "sha256 (copied)", "bytes", "DojoLab now"])}
"""
    (NC / "PORT_PROVENANCE.md").write_text(md, encoding="utf-8")
    pj = {"generated": date.today().isoformat(), "demogame1": {"branch": branch, "head": head, **dem},
          "overrides": ov, "cpp": cpp_json, "content": con_json,
          "new_files": [{"file": p, "sha256": sha(DOJO / p), "what": w} for p, w in NEW_FILES],
          "changed_files": [{"file": p, "sha256_before": backup_sums.get(p), "sha256_now": sha(DOJO / p), "what": w}
                            for p, w in CHANGED],
          "gm_dojo_sha256": gm_dojo_sha, "setup": setup, "check_gates": check.get("gates"),
          "probe_passed": probe.get("passed"), "probe_gasp_passed": probe_g.get("passed")}
    (B / "provenance.json").write_text(json.dumps(pj, indent=1), encoding="utf-8")
    print(f"PORT_PROVENANCE.md: {len(cpp_rows)} cpp, {len(con_rows)} packages, {unmod} unmodified")


main()
