# Ninja character port: provenance (DemoGame_1 -> DojoLab)

Written 2026-10-02 by `tools/write_provenance.py` from the survey (`survey/closure.json`), the copy logs
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
| Project | `C:\Users\Cody\Documents\Unreal Projects\DemoGame_1` (READ ONLY: plain file reads and `git --no-optional-locks` only; never opened in an editor) |
| Branch / HEAD at the port | `metahuman-player` / **`7ea694afab7420f552879ce0f0a917901fbd07d7`** (Catwalk: judging rounds 4-6 applied, final build r7) |
| Working tree | dirty (11 entries, none under `Source/`); `Source/` is identical to HEAD |
| Male-era commit (LFS blobs) | **`43fd6ce242b48c282e089e802d6f0c113f821c21`** (BlackCloak re-fitted to the MetaHuman player, worn with Chaos Cloth) |
| `/Game/Ninja/Blueprints/BP_NinjaGasp` | LFS oid `017e4018029f60d3c8099a0f23df67b7d97538432f79ea68f0d42b49aa15542b` (working-tree file `6477bbe5...` NOT used: it adds the private catwalk walk tier) |
| `/Game/Ninja/Blueprints/BP_NinjaVisual` | LFS oid `5ea028e27eda24a366efd898d40ebb09b08ff23d0b12bd5d6fdd823a3d5a2f95` (working-tree file `df019968...` NOT used: it hard-imports the private BP_MH_PlayerFemale) |
| Everything else | the working tree at the port (sha256 of every file below; each matched the survey's hash at copy time) |
| Never copied | MH_PlayerFemale, Hiyuki, 2B, the catwalk / Mocap folders, anything `_Private` (`closure.json` `private_blocked` = 0; the copy tool refuses such paths) |

## 2. What was copied

- C++: **29 files** byte-identical into `Source/DojoLab/` (15 classes). Every copied file is still identical
  in DojoLab: **29 / 29**. (The survey's
  "31 files" was a miscount: 15 classes = 14 .h/.cpp pairs + `NinjaJutsu.h` = 29 files.)
- Content: **510 packages** (473 core + 37 feature-only, 955,262,255 bytes), all
  `.uasset`, at their DemoGame_1 `/Game` paths (no path collided, so nothing was remapped and no redirector was made).
  504 are byte-identical to the source; 4 were changed afterwards on purpose (sections 3 and 5b) and 2
  were deleted on purpose (the jutsu voice-overs, section 5b). No `.wav` / `.png` import
  source was copied. No DojoLab file was overwritten (every destination was asserted absent first).
- Kept as they were in DojoLab (not copied): the 38 identical GASP packages and the 13 packages that differ (D1: DojoLab's
  MetaHumans/Common hair / lash materials, skeletons and control rigs, GASP's `SK_Mannequin`, `IMC_Sandbox`).

## 3. Every change made

### 3.1 Copied files changed after the copy

| File | Change |
|---|---|
| `Content/Ninja/Blueprints/BP_NinjaGasp.uasset` | B4: SCS components NinjaAirJump, NinjaLockOn, NinjaStance, NinjaFreeLook, NinjaCombat removed (dj_ninja_setup.py), compiled, saved. PLAY-TEST FIX T1 (2026-10-02): CDO jump_max_count 2 -> 1 = SandboxCharacter_CMC's (dj_ninja_fixjump.py; also applied by dj_ninja_setup.py from now on); before the fix sha256 0bfbdc23eb88859480a884361b51be679ea0bcff09a6e081cdde4c6330a4c259, backup test/backup_before_fixjump/ |
| `Content/Ninja/Input/IMC_NinjaGasp.uasset` | B5: trimmed from 24 rows to the 8 jutsu rows (dj_ninja_setup.py), saved |
| `Content/Ninja/Jutsu/DA_Jutsu_ShadowClone.uasset` | NO VOICE (owner rule 2026-10-02): StartVoice SFX_Voice_KageBunshin -> None (dj_ninja_novoice.py), saved; section 5b |
| `Content/Ninja/Jutsu/DA_Jutsu_GreatFireball.uasset` | NO VOICE (owner rule 2026-10-02): StartVoice SFX_Voice_GreatFireball -> None (dj_ninja_novoice.py), saved; section 5b |

No copied C++ file was edited.

### 3.2 DojoLab files changed (start backup in `start_backup/`, `SHA256SUMS.txt`)

| File | sha256 before (backup) | sha256 now | Change |
|---|---|---|---|
| `DojoLab.uproject` | bd6bd165fe59bb609ee85f7014af1e9ea361ee6b02895b2cc3345d5484432471 | a5e92151359d2b24f253ea8519528643e88dcea87547bc1801f850c20dc47dfb | "Modules": [{"Name": "DojoLab", "Type": "Runtime", "LoadingPhase": "Default"}] added; plugins unchanged |
| `Config/DefaultEngine.ini` | d91d7e8e7a9f2778e378bb0df3a228d3169e6ec77e5aa6323b8b760b02e5200d | 83c8689991e1e1a4df8968869347f8ca04013fe83731a1ee59fdac8b971cfc88 | [CoreRedirects] +PackageRedirects=(OldName="/Script/DemoGame_1",NewName="/Script/DojoLab") appended; GlobalDefaultGameMode GM_Dojo -> GM_DojoNinja. Nothing else (GASP's DDCvars, collision channels, PoseSearch, r.SkinCache.DefaultBehavior=0 unchanged) |
| `Content/Dojo/Maps/L_Dojo.umap` | 44992f94e4d9eae8b497847948a871b4aeb94e3047620ca7565282ad55fcf8f5 | 0be14fb5c7112d3fded56aedaa8e0ac6d2736f98f7b948dda37d94ea64031316 | World Settings GameMode override GM_Dojo -> GM_DojoNinja (resaved by the commandlet; PlayerStarts P1 (1450, -1050, 95) yaw 0 and P2 (2950, -1050, 95) yaw 180 unchanged) |

`Content/Dojo/Blueprints/GM_Dojo.uasset` is unchanged (sha256 `ad9def160235886235f2a0fe10f612a1595ddb498ff198c99499ccf026c8adb3`; still DefaultPawnClass
SandboxCharacter_CMC: the reference route).

### 3.3 New DojoLab files

| File | sha256 | What |
|---|---|---|
| `Source/DojoLab.Target.cs` | 153e440a71cc97eb1090d58d4850eb89d15e8a43f9cc4874960d8d21419ea640 | game target (BuildSettingsVersion.V7, Unreal5_8, ExtraModuleNames DojoLab) |
| `Source/DojoLabEditor.Target.cs` | 820dc6d163b6d590750a645eb60ee810474a3b1e79a520b0098574f2696e8fa0 | editor target (same settings) |
| `Source/DojoLab/DojoLab.Build.cs` | aaa6bbca5805c28fcf545a70a53aa2a1d079910469419590fa29749cb8e523c6 | module rules: Core, CoreUObject, Engine, InputCore, EnhancedInput, Niagara; private AIModule; PublicDefinitions DEMOGAME_1_API=DOJOLAB_API |
| `Source/DojoLab/DojoLab.h` | 874f31945643e1cc6a4fda18bfe4cc3497b6e57cc57cce989fe140877c28d0f9 | module header (CoreMinimal) |
| `Source/DojoLab/DojoLab.cpp` | 1923bfb34a9ac128f4b2cc6248a61beba3223456306ee5e843dda04df201768c | IMPLEMENT_PRIMARY_GAME_MODULE(FDefaultGameModuleImpl, DojoLab, "DojoLab") |
| `Source/DojoLab/DojoNinjaCameraSubsystem.h` | 7f5c013acaf41bf399029b564743551eb160456fa844946e0e57dd39d1548201 | per-pawn camera switch (D3), new code |
| `Source/DojoLab/DojoNinjaCameraSubsystem.cpp` | a8a56a52cc294666c6fa374d02ffecb21de03147b1eaf0abc90122deb8430485 | per-pawn camera switch (D3), new code |
| `Content/Dojo/Blueprints/GM_DojoNinja.uasset` | a8f930c13101382ada2456f076a88980ba4ea71555b6f29b16374ff8f77441c5 | new game mode: Blueprint child of GM_Dojo, DefaultPawnClass BP_NinjaGasp_C |
| `Binaries/Win64/UnrealEditor-DojoLab.dll` | 18065c7253ebd9d9226e5e5a87ef029f8b39de17e0d5a519227800e43f37303b | built module (Build.bat DojoLabEditor Win64 Development) |

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
  folder; redirectors under /Game/Ninja afterwards: 0 (the
  90 elsewhere under /Game are GASP / sample-content redirectors that predate the port, untouched). Kept (non-voice SFX): SFX_HandSeal, SFX_JutsuRelease,
  SFX_Chidori, SFX_FireballLaunch, SFX_FireballImpact, and the component's clone-dispel sound.
- `BP_NinjaGasp.uasset` sha256 now **480ec9558a74dae424b5f6420e8f881cf37915fb27fd5d5813222c45f4918927** (not re-saved: it references the DA_Jutsu assets, not the voices).

| Jutsu asset | StartVoice before | StartVoice now | sha256 now |
|---|---|---|---|
| `/Game/Ninja/Jutsu/DA_Jutsu_Chidori.DA_Jutsu_Chidori` | - | None | 2a6bfce61dfd534908c84f2f78ecb3ca70d4425d39d39ac1d7968dc81931c7ee |
| `/Game/Ninja/Jutsu/DA_Jutsu_GreatFireball.DA_Jutsu_GreatFireball` | /Game/Ninja/Audio/Voice/SFX_Voice_GreatFireball.SFX_Voice_GreatFireball | None | 318bb1c7f842390bcbf83cc4afad965ae2ccfdd2ba093e9a4725d621bfbe3a3a |
| `/Game/Ninja/Jutsu/DA_Jutsu_ShadowClone.DA_Jutsu_ShadowClone` | /Game/Ninja/Audio/Voice/SFX_Voice_KageBunshin.SFX_Voice_KageBunshin | None | 22d1736b8edeb28c93adbb9eea05c776b00b42d7b4b202e5e21ef7afc4163a95 |
| `/Game/Ninja/Jutsu/DA_Jutsu_Summoning.DA_Jutsu_Summoning` | - | None | befbc7a629396846b57420942131ac164f7f06b7d8a96f2cd222a84b18b69d20 |

Headless check (fresh process, `run_ninja_port.sh check`, gates A-G): {'A_modules': True, 'B_packages': True, 'C_deps': True, 'D_character': True, 'E_gamemode': True, 'F_input': True, 'G_no_voice': True}.

-game re-test by the real keys (F / Two / Three / Four), with the audio device on (`-Sound`, output muted), every
AudioComponent in the world recorded at 10 Hz ("seen" includes finished components still alive from the cast before;
the positive control before the removal, `voices_paper/jutsu_before/`, listed both voice components and 9 `voice ...
(playing)` log lines with the same harness; after: none and 0):

| cast | completed | seals | audio components seen | voice components |
|---|---|---|---|---|
| stand ShadowClone | yes | 3 | SFX_Chidori, SFX_HandSeal, SFX_JutsuRelease | none |
| walk ShadowClone | yes | 3 | MSS_FoleySound_Walk, MSS_FoleySound_WalkBackwards, SFX_Chidori, SFX_FireballLaunch, SFX_HandSeal, SFX_JutsuRelease | none |
| run ShadowClone | yes | 3 | MSS_FoleySound_RunStrafe, MSS_FoleySound_Run_Soft, MSS_FoleySound_Scuff, MSS_FoleySound_Walk, MSS_FoleySound_WalkBackwards, SFX_Chidori, SFX_HandSeal, SFX_JutsuRelease | none |
| stand GreatFireball | yes | 6 | SFX_Chidori, SFX_FireballLaunch, SFX_HandSeal, SFX_JutsuRelease | none |
| walk GreatFireball | yes | 6 | MSS_FoleySound_Walk, MSS_FoleySound_WalkBackwards, SFX_Chidori, SFX_FireballLaunch, SFX_HandSeal, SFX_JutsuRelease | none |
| run GreatFireball | yes | 6 | MSS_FoleySound_RunStrafe, MSS_FoleySound_Run_Soft, MSS_FoleySound_Scuff, MSS_FoleySound_Walk, MSS_FoleySound_WalkBackwards, SFX_Chidori, SFX_FireballLaunch, SFX_HandSeal, SFX_JutsuRelease | none |
| stand Summoning | yes | 5 | SFX_Chidori, SFX_FireballLaunch, SFX_HandSeal, SFX_JutsuRelease | none |
| walk Summoning | yes | 5 | MSS_FoleySound_Walk, MSS_FoleySound_WalkBackwards, SFX_Chidori, SFX_FireballLaunch, SFX_HandSeal, SFX_JutsuRelease | none |
| run Summoning | yes | 5 | MSS_FoleySound_RunStrafe, MSS_FoleySound_Run_Soft, MSS_FoleySound_Scuff, MSS_FoleySound_Walk, MSS_FoleySound_WalkBackwards, SFX_Chidori, SFX_FireballLaunch, SFX_HandSeal, SFX_JutsuRelease | none |
| stand Chidori | yes | 3 | SFX_Chidori, SFX_FireballLaunch, SFX_HandSeal, SFX_JutsuRelease | none |
| walk Chidori | yes | 3 | MSS_FoleySound_Walk, MSS_FoleySound_WalkBackwards, SFX_Chidori, SFX_HandSeal | none |
| run Chidori | yes | 3 | MSS_FoleySound_RunStrafe, MSS_FoleySound_Run_Soft, MSS_FoleySound_Scuff, MSS_FoleySound_Walk, MSS_FoleySound_WalkBackwards, SFX_Chidori, SFX_FireballLaunch, SFX_HandSeal, SFX_JutsuRelease | none |

## 6. C++ files (DemoGame_1 -> DojoLab, byte-identical)

| DojoLab file | Source | sha256 | bytes | role | now |
|---|---|---|---|---|---|
| `Source/DojoLab/NinjaAirJumpComponent.cpp` | `Source/DemoGame_1/NinjaAirJumpComponent.cpp` | db87ac2a9575ab77c24c9f68aabf72d9012b03d8d38c5952b0b150bf7f6b8ba8 | 5681 | copy_load_clean_only | identical |
| `Source/DojoLab/NinjaAirJumpComponent.h` | `Source/DemoGame_1/NinjaAirJumpComponent.h` | c7aaff9fce83b5eb17836064ba015abd7a89ba72b04369fad817ed968f2335a9 | 5429 | copy_load_clean_only | identical |
| `Source/DojoLab/NinjaCombatComponent.cpp` | `Source/DemoGame_1/NinjaCombatComponent.cpp` | c874236d64ba926b3c7855deb651b7e81d41ac6a553200512143a5446b9cd02e | 23738 | copy_compile_only | identical |
| `Source/DojoLab/NinjaCombatComponent.h` | `Source/DemoGame_1/NinjaCombatComponent.h` | 8a5612a96d6610013dc7065695eb263e26ecd73ff81113dd3a4a6bc8e31ff8ff | 18706 | copy_compile_only | identical |
| `Source/DojoLab/NinjaFireball.cpp` | `Source/DemoGame_1/NinjaFireball.cpp` | 8cf403f12c13760ae48696818b598508b43d2b1ac502f2f2add7c7896dac0a33 | 5741 | copy | identical |
| `Source/DojoLab/NinjaFireball.h` | `Source/DemoGame_1/NinjaFireball.h` | 55afa3a022e58d1cd605cb8d52a4cac5b2122662b77a4dc301740284d1518baf | 4170 | copy | identical |
| `Source/DojoLab/NinjaFreeLookComponent.cpp` | `Source/DemoGame_1/NinjaFreeLookComponent.cpp` | 46726e013015036fbda6fbe4001877c6193cb89da6d6fda5e58513d9bebafb47 | 5520 | copy_load_clean_only | identical |
| `Source/DojoLab/NinjaFreeLookComponent.h` | `Source/DemoGame_1/NinjaFreeLookComponent.h` | 58822ca579dc7b61b5a6b506f85117cf1104de1650161e2f5f7d7215583cbf4b | 3598 | copy_load_clean_only | identical |
| `Source/DojoLab/NinjaGroundSeal.cpp` | `Source/DemoGame_1/NinjaGroundSeal.cpp` | 2c14fb083caf6629e3b207ef1a4853b50d53b420bd9ac7c34ca4246d10f0324c | 1920 | copy | identical |
| `Source/DojoLab/NinjaGroundSeal.h` | `Source/DemoGame_1/NinjaGroundSeal.h` | df1d14df4fe0b13d94ebe221277f8f5491d6c0e486e2abdbfc4d6a98e92b918c | 2502 | copy | identical |
| `Source/DojoLab/NinjaHandEffect.cpp` | `Source/DemoGame_1/NinjaHandEffect.cpp` | 6adeb9b3d66e8bfe0eb0d37ad13047f3e996bf6a7fad99367d74f1b8191ecdfe | 2099 | copy | identical |
| `Source/DojoLab/NinjaHandEffect.h` | `Source/DemoGame_1/NinjaHandEffect.h` | 695f696c21b50d21f220e8fa3ecccd62577e57778b5e45c1846392cb75038bd2 | 2690 | copy | identical |
| `Source/DojoLab/NinjaJutsu.h` | `Source/DemoGame_1/NinjaJutsu.h` | 44d184eaad5f04d71088ab7669936f72361110f7e796f17b6fbbd6b174c559be | 5968 | copy | identical |
| `Source/DojoLab/NinjaJutsuComponent.cpp` | `Source/DemoGame_1/NinjaJutsuComponent.cpp` | bf18b1744e61f30b51d99cb12925a06a108c6e41ec0c4595d5966125926f954f | 34448 | copy | identical |
| `Source/DojoLab/NinjaJutsuComponent.h` | `Source/DemoGame_1/NinjaJutsuComponent.h` | 702ba6286fd32ab9f955208b41a1c02821f2e506c35169dfaeaa1c42195c87c3 | 13131 | copy | identical |
| `Source/DojoLab/NinjaLockOnCameraModifier.cpp` | `Source/DemoGame_1/NinjaLockOnCameraModifier.cpp` | 789bbc825857d0f3388dfae5a1790f49e07ff7af97f228a2f88106aa054b51a5 | 1842 | copy_compile_only | identical |
| `Source/DojoLab/NinjaLockOnCameraModifier.h` | `Source/DemoGame_1/NinjaLockOnCameraModifier.h` | 8d3bd9329185f36d96768529b2588dea94b78a1c5fa0a1dfcd55e14fec1569fe | 1189 | copy_compile_only | identical |
| `Source/DojoLab/NinjaLockOnComponent.cpp` | `Source/DemoGame_1/NinjaLockOnComponent.cpp` | 4dd2e125a286ceecfc16ed5067d7f47febfe10f6bdb14c8135214e75190e1744 | 12528 | copy_compile_only | identical |
| `Source/DojoLab/NinjaLockOnComponent.h` | `Source/DemoGame_1/NinjaLockOnComponent.h` | 55cb628de5cf7e696785611cebfd54744a1f07003e2aaa2b0b9c5f3e67ee1dad | 5993 | copy_compile_only | identical |
| `Source/DojoLab/NinjaRunStyleComponent.cpp` | `Source/DemoGame_1/NinjaRunStyleComponent.cpp` | e8a5650cfff09523057797f194ddd4b500e6b5c7a65b905b473b2125f45e29b2 | 10326 | copy | identical |
| `Source/DojoLab/NinjaRunStyleComponent.h` | `Source/DemoGame_1/NinjaRunStyleComponent.h` | 12895fc623e7e56c01e1d810ee9fcae036aed46baaba757e26ed46acda0ecc68 | 9458 | copy | identical |
| `Source/DojoLab/NinjaStanceComponent.cpp` | `Source/DemoGame_1/NinjaStanceComponent.cpp` | e73672078645ef4c810b2c471902e5b2dcbdb648454d3c1641757c0f78ffc57b | 23663 | copy_compile_only | identical |
| `Source/DojoLab/NinjaStanceComponent.h` | `Source/DemoGame_1/NinjaStanceComponent.h` | dc4d25fe56d376e21310d485a115b7799358287c5d4c8f3278a4a47e35c8fef7 | 14189 | copy_compile_only | identical |
| `Source/DojoLab/NinjaTurnComponent.cpp` | `Source/DemoGame_1/NinjaTurnComponent.cpp` | 6a11fd5c272582b526716bfd851847788d85b752b643ec0258fd41799c763c6c | 6631 | copy | identical |
| `Source/DojoLab/NinjaTurnComponent.h` | `Source/DemoGame_1/NinjaTurnComponent.h` | 0d3a4c7aa7211a8352ab3db2778d1a3d3edb6536b2885da0a3b16a07618c1fa4 | 5122 | copy | identical |
| `Source/DojoLab/NinjaVisual.cpp` | `Source/DemoGame_1/NinjaVisual.cpp` | f14cd3c4b59ac4dcf7146b80f1f03d868529e5d2971f996e040ebf475e310118 | 4497 | copy | identical |
| `Source/DojoLab/NinjaVisual.h` | `Source/DemoGame_1/NinjaVisual.h` | 30949dd55e8f2dc9a9c2338c5e741a8bb0f3f0b1ef1bad61afd4b4a9428ea62b | 2958 | copy | identical |
| `Source/DojoLab/NinjaVisualBodyComponent.cpp` | `Source/DemoGame_1/NinjaVisualBodyComponent.cpp` | d94bcb1c7afac4ea8330c3fb888245009a4ba7cfad36e287ee301709b9ea49d3 | 8493 | copy | identical |
| `Source/DojoLab/NinjaVisualBodyComponent.h` | `Source/DemoGame_1/NinjaVisualBodyComponent.h` | 1c09beec65ecdb2c209d697281f739a6dbe9af1144a70811e6713d53a1665098 | 6014 | copy | identical |

Not copied:

| Source | sha256 | action | why |
|---|---|---|---|
| `Source/DemoGame_1/DemoGame_1.Build.cs` | 31e26972a1cbb93a04847a9fcc76f4171b5302a1a48a8c288d385980bbe179ae | replace | replaced by Source/DojoLab/DojoLab.Build.cs (runtime deps only) |
| `Source/DemoGame_1/DemoGame_1.cpp` | 415600693436d91b016f83fb9ab134671a9c5bae267f6a36d9e018217ac33421 | replace | module boilerplate: replaced by new Source/DojoLab/DojoLab.h/.cpp |
| `Source/DemoGame_1/DemoGame_1.h` | 4694b655856b269fc41b195971214f8e629857c7e5d6f34002a066cd4af3037c | replace | module boilerplate: replaced by new Source/DojoLab/DojoLab.h/.cpp |
| `Source/DemoGame_1/NinjaBlueprintTool.cpp` | 19d01c9b1da173adac2f0043b4c0b6c03e469f6f53cedba9a6ddd1ba4949d491 | skip | editor tool ninja.bp.reliable (BP_NinjaGasp already carries the reliable flag) |
| `Source/DemoGame_1/NinjaClothTool.cpp` | 4d9fac1ddfb815e3e1d38de8231db62866287e1b264229e4192d0d08a81c9a46 | skip | editor tool ninja.cloth.create (cloth data is baked into SKM_BlackCloak_MH) |
| `Source/DemoGame_1/NinjaDebugInput.cpp` | 1ff4994048a66e80f7c938391904936d2f487e7d7a4509695e7928d847c6a6c3 | skip | dev tool ninja.press / ninja.worlds |
| `Source/DemoGame_1/NinjaDebugWorld.h` | 3f74b62326d02265cfa057f2eb1b5db7f37e6413f2bfff8e81af45ded9a09f4b | skip | dev tool header used only by NinjaDebugInput.cpp |
| `Source/DemoGame_1/NinjaLandscapeTool.cpp` | 1c22721dd6584f8b64d91343588fae8c5970bc37f698a944e55aed1746743f4a | skip | editor tool ninja.landscape.create (DemoGame_1 scenery) |
| `Source/DemoGame_1.Target.cs` | 5af485e5b0ff961bb71042ade7210366e4f59eb7296e51974d720a32fe20118b | replace | new DojoLab targets (same BuildSettingsVersion.V7 / Unreal5_8) |
| `Source/DemoGame_1Editor.Target.cs` | 54657430675c3a7348ec9f9610c67975bfddd4d2aa7fcbf5871a1a9e35065e86 | replace | new DojoLab targets (same BuildSettingsVersion.V7 / Unreal5_8) |

## 7. Content packages (510)

| Package | class | from | sha256 (copied) | bytes | DojoLab now |
|---|---|---|---|---|---|
| `/Game/BareNinja_AnimSet/Animation/UE5/attack03` | feature_only | working tree | 832e46f5a2a88e331599ecd02e176f523c1e5ffeca67b9049a5563074578a3af | 231754 | identical |
| `/Game/BareNinja_AnimSet/Animation/UE5/attack04` | feature_only | working tree | c04224fe283fa9cd1ce622969edaa080fcdb96fbe64c20f71a177f13aac26185 | 170863 | identical |
| `/Game/BareNinja_AnimSet/Animation/UE5/attack_daggerthrow02` | feature_only | working tree | 77bfe2f2eb0aca232374e633b91aa9f4e198f7277f08d8bc39da6d140fdb322e | 206637 | identical |
| `/Game/BareNinja_AnimSet/Animation/UE5/avoid_left` | feature_only | working tree | 6bf0a5b6af52e0ef70162ac51ee45575ee7074f6029318271e4c185dff0d8e11 | 238747 | identical |
| `/Game/BareNinja_AnimSet/Animation/UE5/avoid_right` | feature_only | working tree | 4a782c779b81784d9dac8a65f75a8d55f13cf0a63f654e38567ec45f837791f1 | 238393 | identical |
| `/Game/BareNinja_AnimSet/Animation/UE5/combo01_1` | feature_only | working tree | 1d048c8e9435e895c273795c9cff27bec6e79132a1daac5b65b76b8265e696ed | 181482 | identical |
| `/Game/BareNinja_AnimSet/Animation/UE5/combo01_2` | feature_only | working tree | 157c28ea74d10ab505a32649c69065cea6cd1e18594ff3c53913e73f8336f51b | 178379 | identical |
| `/Game/BareNinja_AnimSet/Animation/UE5/combo01_3` | feature_only | working tree | 4168d6a89ecbe59cdfc6e8422573a06002573b6031755d268f6b108c25098545 | 181903 | identical |
| `/Game/BareNinja_AnimSet/Animation/UE5/combo01_4` | feature_only | working tree | 1529f35f37b40254b08a4837f92637b191ee6a9c6fdd3c1fb223e453f1c44389 | 338000 | identical |
| `/Game/BareNinja_AnimSet/Animation/UE5/dash_back` | feature_only | working tree | bb84d74b22b2dcd36174e78de0fb6be79e25148a9b18953afbc63cba63fbfd44 | 124094 | identical |
| `/Game/BareNinja_AnimSet/Animation/UE5/dash_front` | feature_only | working tree | 3d8aaf820361f38e0281d1b594f24a71be680a6653eb9a98d3e36b4a14e9f625 | 124854 | identical |
| `/Game/BareNinja_AnimSet/Animation/UE5/defense02` | feature_only | working tree | 3b7b5e687f60134747d41e4c9a70eb00f023a475a1bae8f6230daf73663120c0 | 256571 | identical |
| `/Game/BareNinja_AnimSet/Animation/UE5/hit_back` | feature_only | working tree | e03fbbe6d3f3a7682306b48a2bac7a47fc39d60fc4d4f95259425a60bd7b78ed | 96677 | identical |
| `/Game/BareNinja_AnimSet/Animation/UE5/hit_front` | feature_only | working tree | cd1d50a74fbada9cfb509d406af45c85945c0f618fe630cfd3562a14d14107f3 | 96704 | identical |
| `/Game/BareNinja_AnimSet/Animation/UE5/hit_left` | feature_only | working tree | 9ea7c4b5d635e67bce90c35858cace51a927ba86a18e5a3c5800e3d4d4c281a5 | 96302 | identical |
| `/Game/BareNinja_AnimSet/Animation/UE5/hit_right` | feature_only | working tree | 6964c584d17d1be9dadc20a25dc64d378e1d0f1f541da58db683a09f1250ef4e | 96398 | identical |
| `/Game/BareNinja_AnimSet/Animation/UE5/teleport_start` | feature_only | working tree | f308f95dc7bb8275367210f3fdcba4b168b233d71ecbd1ac601de1f142f0d202 | 149853 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Materials/Functions/CA_Mannequin` | core | working tree | 0741facba1fcde49b7b022736aa5233621993dee8046212f84263e7aeecff9af | 4858 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Materials/Functions/ChromaticCurve` | core | working tree | 72dede2d74c08909525be0d68f6f1a45a4688be69a34b4d8ea02a511fb58c5bd | 6329 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Materials/Functions/MF_Diffraction` | core | working tree | b6ad8f5bd8144e9b668a2d6b26ec002b4288f4d5ac30843fa509c00a5ef9f93d | 32252 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Materials/Functions/MF_logo3layers` | core | working tree | 8ded4652d7bcc31ce7b708ff6f62ba24621c1766408a4aa9eab98c303657eb20 | 56649 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Materials/Functions/ML_BaseColorFallOff` | core | working tree | c11ba5cddb10edec811ec70c0d4d52c56a42618418826ec2b25b1a396b496402 | 13460 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Materials/Instances/Manny/MI_Manny_01` | core | working tree | 13011e104051b0fa23055792c48496d7e8b01e0c044cefd0faac2d0cb8bfaf34 | 21981 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Materials/Instances/Manny/MI_Manny_02` | core | working tree | ac69c0ded2dadc5d79f57917d144786a1539bae0c535782e38d46b2db30de3e2 | 25290 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Materials/Instances/Quinn/MI_Quinn_01` | core | working tree | 97acd52be7fba8ea54fc2c8b57eb595647313154284a21bff2f495a4f254879f | 20058 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Materials/Instances/Quinn/MI_Quinn_02` | core | working tree | 4dbdb02d9f5172363125f1bef59c766ba7839d7d307ff93c4757bdcd3f80cfa7 | 25667 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Materials/M_Mannequin` | core | working tree | 8c7ac7ab924756de6e0ce8f8e194165e79507774c80541d5556b0bc56c54c8bf | 83700 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Meshes/SKM_Manny` | core | working tree | e533ec98fa34e9df3cd10e2cd550e6ea7e5ab762f02f2c9f4242c419413396e9 | 34534882 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Meshes/SKM_Manny_Simple` | core | working tree | a5be2dbe2a158e57425323320878bf30ad1d26d0a75bbf5e2e393f7a3d903468 | 18527352 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Meshes/SKM_Quinn` | core | working tree | 229e5136431375ec88134b19c2225e9f4f4638e17f35eebd676bdd50de9b1e47 | 36495860 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Meshes/SK_Mannequin` | core | working tree | 610a163059ca9cea5a4b88eca6a5fa5f623d4e4374c76361b2a2a1425a49f0d8 | 188670 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/ABP_Manny_PostProcess` | core | working tree | 1fcadb1a10dcf9910d063bafa9dfa1eeb47be2b21d5666bcaad80e7418be9a70 | 464257 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/ABP_Quinn_PostProcess` | core | working tree | fff74c065593f1d8e9eaaed75ab8fd64af3dbf2653686cdf55c4e2972bd93926 | 464055 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/CR_Mannequin_Body` | core | working tree | 6636c088ff380f7b6d4048d55fe0d4d67892a6bb7b07d370ccc967c0de4c332e | 11312233 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/CR_Mannequin_Procedural` | core | working tree | 0eba7479f9dbe837ed14cdea7b5e4ce4b893d78339fcc86e8fb834423bd8edbb | 2166248 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/PA_Mannequin` | core | working tree | f270644a0db5e2123324b372df0c4808c1366eb28dc3987a33e7e703dfe638cb | 64289 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Manny/Manny_calf_l_anim` | core | working tree | 91c348fc3d2f6fee479e332db03832a85e80f7fc56f861e17a03f42c3006b823 | 141521 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Manny/Manny_calf_l_pose` | core | working tree | dcf7ceeb554af5bd11830b93a5d91cc7dcab0504056933ed35add344508585f3 | 207522 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Manny/Manny_calf_r_anim` | core | working tree | ca7efad2ad9586bd08309084d68a905271cb69556e126d2082e537c7e3852fd4 | 141531 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Manny/Manny_calf_r_pose` | core | working tree | fe2d2fb75bc08abb35a9abcfbbc2d6e8d2dccdea251bc7d7792d75c73a24041e | 207522 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Manny/Manny_clavicle_l_anim` | core | working tree | 4a0d804f21e9389409697c30097ba8dbee2d38b5352c336de0e3f47edb8fc706 | 141553 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Manny/Manny_clavicle_l_pose` | core | working tree | 2b77d7cdacd9fc3a12cef665a51c00ab8780497e90886aab8c1439f45e4b94a6 | 205824 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Manny/Manny_clavicle_r_anim` | core | working tree | adb7e4f331e124bda471ec40fe528797584a9578d3b2448acfb2b76dbf23dcab | 141555 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Manny/Manny_clavicle_r_pose` | core | working tree | 0e5d21be48994e8e4759493d9fe8c79997f1e109e69c4066834445608d1ca915 | 206426 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Manny/Manny_foot_l_anim` | core | working tree | c47df4fa190aaba187a935c49ca9b448351a6fc8aa4f7ff9292e4535701adf73 | 129529 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Manny/Manny_foot_l_pose` | core | working tree | bd83d308cf44807483593fd5e40f75db5003b2e2a49f58c001c8ea779c2db9f6 | 132268 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Manny/Manny_foot_r_anim` | core | working tree | b3a6c4f4e0e0bb9719a5821ed2f292a8af667b891784eab151751f706f0e75c6 | 129531 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Manny/Manny_foot_r_pose` | core | working tree | e5bf1d3fbfba88f7dbe09441813e1c842c38129c617d708db2233861b1d42a4f | 132268 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Manny/Manny_hand_l_anim` | core | working tree | 15a8a04745a8ca8ac9641ffa23bde27d9ca2aa5fef0bf76b05b5fc8e3a05b74c | 135529 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Manny/Manny_hand_l_pose` | core | working tree | bfcfce224339be910374ca202012ffd16604316c36720a70af4556f09888ae30 | 169298 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Manny/Manny_hand_r_anim` | core | working tree | 1fd695cbbd49ae1e9f3e0381c6bb05d4bef838110a7b572345d8d0e803ac323f | 135531 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Manny/Manny_hand_r_pose` | core | working tree | bfa8a59908089f3e36c882b5040928ccc0c6aa2154edd2ed372cc2b907f0bada | 169298 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Manny/Manny_lowerarm_l_anim` | core | working tree | 75578712a25d814c590283ffbf7c71186f188ad7b417a7578623643a87b9dd4e | 166016 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Manny/Manny_lowerarm_l_pose` | core | working tree | 38b7b97a5367d6ce718f376d62e408020286a3f37bffa13c5eb3989e963f9030 | 361736 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Manny/Manny_lowerarm_r_anim` | core | working tree | 1bd28f4ec0c145cc912c9c5d99b8ce12c705c3cbc9125b1fa9a3b9f474614424 | 165555 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Manny/Manny_lowerarm_r_pose` | core | working tree | 1cc54710e07e114300f3eab83c78ea4295a01ca1033f8cca89b3ba8201d4e36c | 361736 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Manny/Manny_thigh_l_anim` | core | working tree | eb15961b7c1aac295106e5641c81237beccb94b7c6ba6783122f347ab01e5c50 | 195537 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Manny/Manny_thigh_l_pose` | core | working tree | 6e330ce96492d6f4c5e36c5a65cb91e44713720fc6ad43a62e584b031801ced6 | 558064 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Manny/Manny_thigh_r_anim` | core | working tree | 44aa18bbfbabc650abd291692f08b5847ee3cab72642091f59d36f57c147b5f0 | 195539 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Manny/Manny_thigh_r_pose` | core | working tree | 174df22ea4f5c05fcc7c8a7e060be11d04bf96151686dbd56f041e031b82c08c | 558064 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Manny/Manny_upperarm_l_anim` | core | working tree | 2ba6cd8599bfa14fa4d8120677febfb23149f7897fce31a5a563b030555488ac | 207555 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Manny/Manny_upperarm_l_pose` | core | working tree | 4ba93f82a886ed7f9eb6cfb8e51b6ef9120b05ca4a66dc5ce7aed9fd0b50d117 | 641725 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Manny/Manny_upperarm_r_anim` | core | working tree | 7778e6273f74288c69894e38308ba1b96d7ff887e9eae8467e6d98eeb439c1b4 | 207557 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Manny/Manny_upperarm_r_pose` | core | working tree | 567b8df57fe0a2bee2b643ab1a7faf500a805d8f077598d0bba61b3906acfb71 | 630287 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Quinn/Quinn_calf_l_anim` | core | working tree | e39265b82cfbc63c8d9fc8afa57b9bc67662d60f5bacc5083c932da2cf205600 | 190099 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Quinn/Quinn_calf_l_pose` | core | working tree | 5f52eed98a03839cf96d0414d34910af28cd4c24a142f4c7502500f465096727 | 245349 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Quinn/Quinn_calf_r_anim` | core | working tree | e57ff4935dc37da69f04fd94af59a4ee507682980fa2ac9a34c80577a88aeb72 | 190176 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Quinn/Quinn_calf_r_pose` | core | working tree | c675155f53eef735bf7cafdcfa519d3055878c6a095c884bc29f4be37847173f | 245430 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Quinn/Quinn_clavicle_l_anim` | core | working tree | 74a4e93a0c7e84eb9d0c4f3d137c87f36f13b5feec921d962c422e6cfbf6ee9b | 184140 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Quinn/Quinn_clavicle_l_pose` | core | working tree | 12947cd63ab85bf8c015cf5e47b214f55b1ca02540a07e7dfe68153a346e525e | 206097 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Quinn/Quinn_clavicle_r_anim` | core | working tree | b873df4d9ca99e97ca773b49d82dfdc8d6e54be9fce8a1b66ad3202f18b6ba15 | 183803 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Quinn/Quinn_clavicle_r_pose` | core | working tree | 44ab2ed45f80b5a6dbd61e77f2f685974fe1fdb78e704719a210f7bd0a3e2b2c | 206141 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Quinn/Quinn_foot_l_anim` | core | working tree | 1abff5d6c1a500aa05c5352125158997f707e7c05e6365ae502c4e544a242246 | 171777 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Quinn/Quinn_foot_l_pose` | core | working tree | 02b31a369177f5dc93afd4caaafcb7ae1ae3b98102059add1527e84df81e9387 | 132284 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Quinn/Quinn_foot_r_anim` | core | working tree | 2de68c28da2dcc4a66e0a9857b79a0e7669f648084354c0adcf550edfcb93804 | 171779 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Quinn/Quinn_foot_r_pose` | core | working tree | dc9937e9604afd13acbf58e0ad2d870a52ba0763022b708ff007deb7d7d73462 | 132284 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Quinn/Quinn_hand_l_anim` | core | working tree | 1148ca2f2e94c1733444318c7033a88eb237dc9e2f30f6ab6dc4af6e39837c42 | 177777 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Quinn/Quinn_hand_l_pose` | core | working tree | f24cdb522cb85dd00e92a85af45c7641bfbc0c7c07862318e27956a5cfff69d6 | 169314 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Quinn/Quinn_hand_r_anim` | core | working tree | f3a0d31ab54778e3d3a60e1d3b904569faafd6b5644f080d8e7ab9bcbe181a68 | 158677 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Quinn/Quinn_hand_r_pose` | core | working tree | f950b810dfa6f343b7d6cfc25565cbb46ce160ddd870f4cd41e84986fd400477 | 169314 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Quinn/Quinn_lowerarm_l_anim` | core | working tree | c0604bddd392679621d0b55c56d4eb8a83b32df1e67ba559eacb2ea76bd6fa9b | 194700 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Quinn/Quinn_lowerarm_l_pose` | core | working tree | c83711fb5ac0bf9be9eeb7a12e1c8cfc6d8d326b8553892c6fcdb3807dfa6cf0 | 399690 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Quinn/Quinn_lowerarm_r_anim` | core | working tree | f6036745c0e22338fd1f29e218469405ad4aa1e534a7841414f5d2739b9b2803 | 194702 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Quinn/Quinn_lowerarm_r_pose` | core | working tree | 92d38777c14a90986d46af7e0a4aa5e460052d3ab356b1dd8116273438ca2f16 | 399690 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Quinn/Quinn_thigh_l_anim` | core | working tree | 234e6ed25d68badfa9bd2a0b71abd2b2be7c4e0ee8af427abcd03a97bea258ad | 218683 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Quinn/Quinn_thigh_l_pose` | core | working tree | 601086bb797d7a77c5428238ecd2049fc271b4ab890648396a273ce5359caa10 | 557779 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Quinn/Quinn_thigh_r_anim` | core | working tree | b75f2f6b099a5957ec4a8c4a3f2e5cf0b3ed26049568f8ef23ed5ad8581c4984 | 218685 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Quinn/Quinn_thigh_r_pose` | core | working tree | a8148a1ae69c8c57d3ae52d2f092d70d3212cfeff67b2b89f68fbb60d2ae0496 | 557779 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Quinn/Quinn_upperarm_l_anim` | core | working tree | a8fa443309409243be4eff8ecb42d71957a10857e022fef2fcbb24aca6d508af | 206701 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Quinn/Quinn_upperarm_l_pose` | core | working tree | e3498a181f00ecf5902840e309097151dc529925a6647d707e94fb217e2cf54b | 485601 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Quinn/Quinn_upperarm_r_anim` | core | working tree | d823765e62e40428e41fb4591c4cea28e615ff6f55cf80d1d95d0c00f966d029 | 206703 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Rigs/Poses/Quinn/Quinn_upperarm_r_pose` | core | working tree | 56825f52ebbec2dd8453057622dc9238d45633f1d56541f2bbda5402e6db6b4b | 488611 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Textures/Manny/T_Manny_01_ASAOPMASK_MSK` | core | working tree | 92feff65263cf98df9f13b43565f2b0d3494ef224fd0505b52b6ac12b91926cc | 3608443 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Textures/Manny/T_Manny_01_BN` | core | working tree | ef38593d5516f8ee656af7d7402062199d60cb4cae836079ab65e8c066666d4b | 18511069 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Textures/Manny/T_Manny_01_CCRCCPlastic_MSK` | core | working tree | 35a6d5275b0cd9d4f5f1e08c7ed71dbdcb3cf7527cca60827b67060b49705978 | 10267742 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Textures/Manny/T_Manny_01_D` | core | working tree | b0ed7063f0d47da6a289dcb002516699f5bccdd6f23fdc751fa62cb49c95ad8e | 5736709 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Textures/Manny/T_Manny_01_MSR_MSK` | core | working tree | 977e8116d78fdc44bc4e87a30b7196278a555d4e23dbc9ebac9976b22ef8951f | 11035057 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Textures/Manny/T_Manny_01_N` | core | working tree | 747d7be85eaec5061fa197c89299df979ef9f461734187644ead2cecfa73020b | 7198275 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Textures/Manny/T_Manny_01_Tan` | core | working tree | 7f03b2a51a54c77d6a0a46f066dc733cbbc6bc4a62247ac93267d2659e2bcd69 | 1356812 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Textures/Manny/T_Manny_02_ASAOPMASK_MSK` | core | working tree | 4d50c8cf88385cbc27a57c5867f86b0ec32d39fdba0ce2d3e676192cbc40ec28 | 8336156 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Textures/Manny/T_Manny_02_BN` | core | working tree | 73e4e9e0a4212862dcc56615de85e3c6da5aa242563634f42f6ba7e7c41554d8 | 21135761 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Textures/Manny/T_Manny_02_CCRCCPlastic_MSK` | core | working tree | 9e2e459f310abb5e7b8abc603db5c2af6e9e8e8d3931d1e46c38a39be27795c0 | 13137450 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Textures/Manny/T_Manny_02_D` | core | working tree | 0b917adde34269d96a02cf4ddefb01835ab2569420573113728e9b349c678dbc | 9028731 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Textures/Manny/T_Manny_02_MSR_MSK` | core | working tree | 72ba80d62aeb8aa0af9a4106cf8099672bbfe1895f12cab6676c69740d7efd9c | 13673324 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Textures/Manny/T_Manny_02_N` | core | working tree | 0e767ea4be75c2d06dc4ff0a4c653341803c830db051b4388fa1ca3a347a3a7e | 7269360 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Textures/Manny/T_Manny_02_Tan` | core | working tree | 4ff187c144dd7d4d35d58a8fe71c35c2e30bbd28875e4403f7ac39cf785fa7a8 | 2151500 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Textures/Quinn/T_Quinn_01ID_BN` | core | working tree | be65d5170a17152a0f7e64a45e10e9f329d34383add527fb88269dff78b1c865 | 16108622 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Textures/Quinn/T_Quinn_01ID_D` | core | working tree | 700fc30b9afbbce2991381712b8530af33ac2d765e4002f15ae626a1366b45e9 | 4711179 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Textures/Quinn/T_Quinn_01ID_MSR_MSK` | core | working tree | 9dd32e46a1ad023412a72555c2facf077c7c038d195098f01f0ce8407958e3b5 | 11656164 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Textures/Quinn/T_Quinn_01ID_N` | core | working tree | 87140bf1c993d02c4b0b373afd0993762f5ad0a46a939eb4b0d949d2fd41b71a | 5217699 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Textures/Quinn/T_Quinn_01ID_Tan` | core | working tree | ab41404907d27c7b6deae82febe570e9c513fd6d230ac13041fa9d2a65ff8e54 | 1104650 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Textures/Quinn/T_Quinn_01_ASAOMASK_MSK` | core | working tree | d9b7cfca19be130e33df212753b2cadc74a6966299c24e38b2a33b03744e3cab | 5834857 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Textures/Quinn/T_Quinn_01_CCRCCPlastic_MSK` | core | working tree | 8a4e7b0a51815897b4a95c5abd8094690fce4166f0ba8a55b62ee050aa407c13 | 12399949 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Textures/Quinn/T_Quinn_02ID_BN` | core | working tree | 5159b78695b075ff5ee40711f95ca9cbd70722d175f47cdbdff6b66e4a55b544 | 19706906 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Textures/Quinn/T_Quinn_02ID_D` | core | working tree | 14c2b2c3746ead0893ed811d5773f3596e543eff3629a4e3bcb9c59d57876f4a | 6732547 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Textures/Quinn/T_Quinn_02ID_MSR_MSK` | core | working tree | ec378d6fd4abb1ed68ce0347904bf0c88994479ea7d96721f0cccdfae20b2884 | 13169794 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Textures/Quinn/T_Quinn_02ID_N` | core | working tree | 715188e1c844c7e4c117b04949f95b7be03e2741b83577a3ddf3047dd52dac34 | 5217699 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Textures/Quinn/T_Quinn_02ID_Tan` | core | working tree | 6bcddc436d9ba272dabce8fa18b8a4fe64e4260bbf4803948aee19c9d6d4f34d | 1758517 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Textures/Quinn/T_Quinn_02_ASAOMASK_MSK` | core | working tree | 715dc82506b3424e9e96991cf21d94f6c60bc074c55dbb4bf458d1daf4df0912 | 6901996 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Textures/Quinn/T_Quinn_02_CCRCCPlastic_MSK` | core | working tree | cd748dc1beb63e0fd154c171dbeec2b157582124d88aa589722842b66bcb9e01 | 13427881 | identical |
| `/Game/BareNinja_AnimSet/demo/Characters/Mannequins/Textures/Shared/T_UE_Logo_M` | core | working tree | 61d1f0f9d25eae6d02b4f7268bed14f690378e977eb33e02e6fe3a7c60b6a886 | 69983 | identical |
| `/Game/Characters/Mannequins/Materials/M_Mannequin` | core | working tree | d7ffe412d906380bd5bd4462f464b2a1fe48fdb79b9077f29bd0f958a782035c | 59292 | identical |
| `/Game/Characters/Mannequins/Materials/Manny/MI_Manny_01_New` | core | working tree | 9f1e4ed382304d020b750c81505140fc1de4d339b0909430adb5380a6bb89b65 | 17963 | identical |
| `/Game/Characters/Mannequins/Materials/Manny/MI_Manny_02_New` | core | working tree | 26389db06f0b7928b487494bef3320d6b0e6bccd58193bccedd67c2c89132a46 | 18706 | identical |
| `/Game/Characters/Mannequins/Materials/Quinn/MI_Quinn_01` | core | working tree | 62a3050ef24b823f9fe84ac5d9c477099494982d35dafcc3d8078f32b0d4a865 | 11184 | identical |
| `/Game/Characters/Mannequins/Materials/Quinn/MI_Quinn_02` | core | working tree | 6aec77489fdfab0e1ea299de60fbd4f332face4495bbbd20b97fb0308bb9c5b4 | 10718 | identical |
| `/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple` | core | working tree | be9f011191ee1887b97cd13bce09886a6066c2fd62c619991070ec142184e1bf | 15825101 | identical |
| `/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple` | core | working tree | 1ef45d92507a76d74a5e06737f94cad40eb7d5f5769dfbb63f7f74e784a178c6 | 16252577 | identical |
| `/Game/Characters/Mannequins/Meshes/SK_Mannequin` | core | working tree | 22029d47455f24471195b26a0e04a1e1389f27d6a924e88c9f46a0f600c9a530 | 191198 | identical |
| `/Game/Characters/Mannequins/Rigs/CR_Mannequin_Body` | core | working tree | 57f84458a160c35b77f0442d2af41054e41e021ebbb496c2c76dea76d1d89580 | 17057558 | identical |
| `/Game/Characters/Mannequins/Rigs/PA_Mannequin` | core | working tree | c0ceaf003947088ff076555b81a46e5ccb11149c94025eb2a9e74263fbaa0d67 | 301538 | identical |
| `/Game/Characters/Mannequins/Textures/Manny/T_Manny_01_BN` | core | working tree | 2f623209571ecbd8185b5b463786be033c3284190b4fc7b249e8d1d2ed995fd8 | 1422785 | identical |
| `/Game/Characters/Mannequins/Textures/Manny/T_Manny_01_D` | core | working tree | 6ae0f4f9908c30ecc9aedf1ebb442e4983e526a7832ec791542064c7853f9999 | 699555 | identical |
| `/Game/Characters/Mannequins/Textures/Manny/T_Manny_01_MRA` | core | working tree | 3e42e888aed8aefff68da7d7dda4f177c5647b19473e4e913f61375c1319abd8 | 712594 | identical |
| `/Game/Characters/Mannequins/Textures/Manny/T_Manny_02_BN` | core | working tree | c9575d21c9e2872b3358c0efb9e202535ce2efce94c338b9d3bd04cb9831e353 | 20999487 | identical |
| `/Game/Characters/Mannequins/Textures/Manny/T_Manny_02_D` | core | working tree | 474728713232c6833f55c041548f555bc62c5c49e74082a5d16e68a5ce488cfe | 1036712 | identical |
| `/Game/Characters/Mannequins/Textures/Manny/T_Manny_02_MRA` | core | working tree | 6697972eaf2dfe201923dba6a302f024b0ef4c4e46b4ecf578178717098e8277 | 1059559 | identical |
| `/Game/Characters/Mannequins/Textures/Quinn/T_Quinn_01_D` | core | working tree | 04e5ed207b7df0d2ad1bbc668916bcf170545fc2a72875e49ec99c6e2667002f | 674768 | identical |
| `/Game/Characters/Mannequins/Textures/Quinn/T_Quinn_01_MRA` | core | working tree | 0988d4d9f25597224910e1043591cb2a089a8607a4fe4a63cbc68f3eb2ab473e | 791597 | identical |
| `/Game/Characters/Mannequins/Textures/Quinn/T_Quinn_01_N` | core | working tree | 10fbe9ac3e18e0a890d19756d3470ca372a1aeaffefbe9a22d6b0e6182293551 | 1263741 | identical |
| `/Game/Characters/Mannequins/Textures/Quinn/T_Quinn_02_D` | core | working tree | f0ccb2f465894c6f9ff4dd142351ed33186c5f861283a75f3e08d1531a253c49 | 943331 | identical |
| `/Game/Characters/Mannequins/Textures/Quinn/T_Quinn_02_MRA` | core | working tree | 9f7e495cbe0430aed7084b5508f87186f98346eb04f003734c9b378891da7887 | 974099 | identical |
| `/Game/Characters/Mannequins/Textures/Quinn/T_Quinn_02_N` | core | working tree | 0bc26466e9fdc954cc276bb6ac1350e22c3dabbe1b54b6bf78ed5ae2e339d9fc | 1524635 | identical |
| `/Game/Characters/Mannequins/Textures/Shared/T_UE_Logo_M` | core | working tree | 34e6fa3414c04a86b7a5287e5569ea9d6e53c319d6e7dbfc8b09dab5b70611a6 | 59927 | identical |
| `/Game/MetaHumans/Common/Animation/ABP_Clothing_PostProcess` | core | working tree | 66667430c5d21e3751c884de521b75c5ff8ac8ed70eb78c606102720464d5a07 | 199649 | identical |
| `/Game/MetaHumans/Common/Animation/ABP_MH_LiveLink` | core | working tree | 0b9cef34cce0a65fdf215625944c3d68857c3f7c9b6d1b5b519c4252b0d9a287 | 344736 | identical |
| `/Game/MetaHumans/Common/Animation/CR_PlaceHolder` | core | working tree | 6b8b26061d2c212238fe9b4ee0652a0e931d907a7e9e9e7c3cc9b009ee2cdbc9 | 23430 | identical |
| `/Game/MetaHumans/Common/Body/ABP_Body_PostProcess` | core | working tree | e9a926a75bb53e3b7385e77be61131295971f7c9f83a620504c8a7001b5d94b5 | 131075 | identical |
| `/Game/MetaHumans/Common/Body/IdentityTemplate/Body_LODSettings_High` | core | working tree | 0c8f23d6b77010d4926b46fa6a054f9aa81804f48510a394d9b2e514a33ebb35 | 57191 | identical |
| `/Game/MetaHumans/Common/Controls/CRSL_MetaHuman_Gizmo` | core | working tree | 19b63e857a3ceccbb3f101f116418f88aa16e66ea8ee6945e0d3c33aa563b229 | 4577 | identical |
| `/Game/MetaHumans/Common/Controls/SM_MetaHuman_Faceboard_2x` | core | working tree | d78430259ef69abcaadf89d158a1d3de4ac0a7df957f40c38750b15148996705 | 535217 | identical |
| `/Game/MetaHumans/Common/Controls/SM_MetaHuman_Faceboard_Convergence` | core | working tree | b5af5d64eb2ba1435258b097783ea157ad1ae028e51b01478bebfa3d47731d05 | 194595 | identical |
| `/Game/MetaHumans/Common/Controls/SM_MetaHuman_Faceboard_FollowGrp` | core | working tree | e1176ffb5b1f31da03ce2a102416e34843143a7718e219d54666ca61121a0af1 | 79037 | identical |
| `/Game/MetaHumans/Common/Face/ABP_Face` | core | working tree | 7312f5473af9a17567705b6e366c23095c00b9213032d27e2ad114b5db90318c | 30650 | identical |
| `/Game/MetaHumans/Common/Face/ABP_Face_PostProcess` | core | working tree | 690fd8fefd579fbad4cc9515df9b8f307467a75a3edfba90ec467d809a421b43 | 204133 | identical |
| `/Game/MetaHumans/Common/Face/ARKit/AS_MetaHuman_ARKit_Mapping` | core | working tree | 7a295f5198aed54103c5a71176f2d4ad12cdc91477e58913fe8259327ec7d9e8 | 5328449 | identical |
| `/Game/MetaHumans/Common/Face/ARKit/PA_MetaHuman_ARKit_Mapping` | core | working tree | 37c2f21b41e20e3902bf3ae5e0ec37f0828c01a97b72609885d64378e0e0da4d | 929498 | identical |
| `/Game/MetaHumans/Common/Face/CR_MetaHuman_HeadMovement_IK_Proc` | core | working tree | a7f6abf7b8f56e73fc0e7d95a1ddcbb591507b56d093e39ad38d71c617d450a8 | 1270368 | identical |
| `/Game/MetaHumans/Common/Face/Face_LODSettings` | core | working tree | a978f489fa4cc174c2fdf519c045b5eaa45171ff8c9274039adf7cc8f2e4b924 | 150175 | identical |
| `/Game/MetaHumans/Common/Face/Face_LODSettings_High` | core | working tree | 78c6d92a921ebff3f8f8b66d8100f51478bf7d1e6a620a8a9a25a02d523f12cf | 96946 | identical |
| `/Game/MetaHumans/Common/Face/PHYS_Face` | core | working tree | 62c1f892f76d5cc3d2246dcda53bfb2f7bde1481e0c9a76625d0211ca444dd85 | 12730 | identical |
| `/Game/MetaHumans/Common/Face/SKM_Face` | core | working tree | 57fce4bc10d8811fa8c79dd7626e5aa54f82ed5f5ff37891adce0c4114d7954d | 18542596 | identical |
| `/Game/MetaHumans/Common/Face/SKM_Face_DNA` | core | working tree | b46f2209810f4feba95b2b045de832dbb289b17005d68c5e497226f51e79e2f7 | 11048667 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Common/Material_Functions/MF_UDIMs` | core | working tree | eb30d61e8f20b273475fd15cf3e3783ddcfde6a1b0412716777f1ae59be95efe | 13133 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Common/Material_Functions/MF_UHM_QualitySwitch_MaterialAttributes` | core | working tree | 153fef8f78f1a34fb1098eb39b29a5613c14f69ea60224a2679d210eab16ca1d | 14073 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Common/Material_Functions/MF_UHM_QualitySwitch_Scalar` | core | working tree | 6fae216c85221bcb85a3be31bf7f8a3615863f6629239ebcc547c87dda65ed19 | 13895 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Common/Material_Functions/MF_UHM_QualitySwitch_Vector3` | core | working tree | 50a8cac2421ae9513a3b4908457886c7b42fdf7ab8c5e75685f5bb62c4a54ee1 | 13559 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Common/Material_Functions/MF_blendNormals` | core | working tree | 919cd9a260b7c43835f96380d27837779aa73ab192230da1944b028688e3bd7f | 16417 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Common/Material_Functions/MF_color_LinearTosRGB` | core | working tree | 2d33321fe55338724e79c6ffbc930661eaa057d3799330d28ac2bd35c53b6778 | 15903 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Common/Material_Functions/MF_color_sRGBToLinear` | core | working tree | 4243f87d552df1c3aa1eb6706151479b88b54adb5c74344434df44364b45526e | 15903 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Common/Material_Functions/MF_normalRotator` | core | working tree | 5506ae71de5adfbb0b80fa9c9d7fb398932a88f978b4273fa770e8d3b046dd49 | 19007 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Common/Material_Functions/MF_normalStrength` | core | working tree | 59e7d9a7c474caadf8900bea550e005fde0b0e2ea9e146be72ae87e43c886947 | 9510 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Common/Material_Functions/MF_ruler` | core | working tree | e1fc6fb687d9c2a63a0ceeacf32aa3cf28295b7ac6f1bb8abeffda7317b90478 | 11004 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Common/Textures/Placeholders/T_Flat_Black_M` | core | working tree | 5db9cac08bdc8a73ca471a06e2cc5cb82eb40581a8e477011cb9dbaab85752d6 | 7888 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Common/Textures/Placeholders/T_Flat_Black_M_VT` | core | working tree | 51781404a5fa51130418b279520de0455143da99866e430d89089030c0c70107 | 8446 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Common/Textures/Placeholders/T_Flat_Grey_C` | core | working tree | fecf4d81a28f1877568a22b5e3b41b2066ba8570ff36017937e266997512c3c2 | 7695 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Common/Textures/Placeholders/T_Flat_Grey_C_VT` | core | working tree | 89774a390d2a0a0aadcf37b35f83c40d9a4dba3c228e603df7b6db6f4de5748a | 8171 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Common/Textures/Placeholders/T_Flat_Grey_HDR_C` | core | working tree | 1a06043cdb7b0d97f6f4a664934c35a57e3383439109349db38e3e022414c990 | 8034 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Common/Textures/Placeholders/T_Flat_Grey_linear` | core | working tree | 1424dc4efecead0d6d33d8555a098a0ae1a752b0370d2e8d71043b334d2e200f | 7912 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Common/Textures/Placeholders/T_Flat_N` | core | working tree | bce0f946d557f288d7f4db6c5df29b5fa86cde9aa310cbc8d3a06d43d5c077e8 | 7943 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Common/Textures/Placeholders/T_Flat_N_VT` | core | working tree | a7d7092fb895c4c4a98c1613469bfc78bd2a68c88c293cdb7fa94165110972ff | 8454 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Common/Textures/Placeholders/T_Flat_White_C` | core | working tree | 3593e36299d2be782b091d145a74a9b40eb6989c216e3fc8dc004f6cbe812ea9 | 7716 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Common/Textures/Placeholders/T_Flat_White_C_VT` | core | working tree | 194965b8cb85af42f3ca1aafa9b6c8c5de67c5a32dfee937b38ed1d64de961d2 | 8208 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Common/Textures/T_MH_BentNormal_AO` | core | working tree | a3d11ba1a4f406a88d045bcbc9b0acc91d3b7b8608af744f6742157a02237a8a | 898387 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Common/Textures/T_MicroDetail001_N` | core | working tree | 21b6123b9ba9b253b235d4e4a74e0ab59074b70b10061fda048c5bee7ffebd01 | 1432616 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Common/Textures/T_TilingNoise_001` | core | working tree | 769f06cc767757c4680123e0ad0b5f9bd9fd8d288fc937f04683fe087b880437 | 99166 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Eye/Material_Functions/MF_circularMask` | core | working tree | a9ffeab42d6406650ded08573b064324a317373a1f7fc67d024f00a5c1cef381 | 14851 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Eye/Material_Functions/MF_customIris` | core | working tree | ac96dcdb4b6d2a8064cf29edfd58c732115cff74cfa0b078ce8e94eb43930de6 | 56763 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Eye/Material_Functions/MF_pupilScale` | core | working tree | 0afb180a02bc365d08921bab00f096b50d30e7b203c8b2319b3c3c2743515093 | 32639 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Eye/Material_Functions/MF_refractedUVs` | core | working tree | 2ab945e46504f1fdea8f34959ffe41959165dffb7bcf9914e9439d1b102fa3a9 | 46494 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Eye/Materials/Baked/MI_EyeL_Baked` | core | working tree | b4fb95f7c465a8f90c3d46a132400337fe37a30c4336d4304f1ce265fcf02434 | 6295 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Eye/Materials/MI_eye_eyeball_unified_MH_preset_left` | core | working tree | 3246b3f0be5a1edf8340f274a324f62222c4a36d0e44b9cf45a93572c010aee1 | 37225 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Eye/Materials/MI_eye_lacrimal_fluid_unified` | core | working tree | cc23f1229b17b1d9f03d7033dd7ea1fcc376aa7b859d41badaa65da1d3e03f97 | 8616 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Eye/Materials/MI_eye_occlusion_unified` | core | working tree | 398fa2bc0dc626f9edd3c93bdd5603aba85829215426bca96aac268adef0a765 | 19141 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Eye/Materials/M_eye_eyeball_unified` | core | working tree | 9690c994eb9e7312cca88e7a0a182d7a234c92b998b0b2b735b5941eafa4b207 | 399648 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Eye/Materials/M_eye_lacrimal_fluid_unified` | core | working tree | 7455618277a444caaea5457ffb5893a1d5b406c1583145d109dd5b729c7b68d3 | 26990 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Eye/Materials/M_eye_occlusion_unified` | core | working tree | 18010e8c1de1156e388370e1ed04a7fad3e85f06ac70efd8dfafde39655c2ee8 | 101689 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Eye/Materials/SSP_eye_unified` | core | working tree | 77c1eb1aae000b1595ac13f500e8c5a9c21f73683205e6b64810c9f428146a5f | 3195 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Eye/Textures/Iris/T_Iris_H_M` | core | working tree | 8d52a62c12e73464bf9347fb0689955ac9f994781dbf174d8c28a3c4d4917d5b | 1587154 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Eye/Textures/Iris/T_Iris_I_M` | core | working tree | f433d337cea9564290b47024d6c54ca6f8d8fc4bfbc2991379d67da63c5ecdf8 | 1418680 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Eye/Textures/Iris/T_iris_H_N` | core | working tree | c9731844e65a2197d84119889e4ddbbf6977f6ac45a803fa90edec44e8f7290a | 6011675 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Eye/Textures/Iris/T_iris_I_N` | core | working tree | c4dc594a923a254de2572e6023cf8d79666d36295e4e3fee38dec91aabde77d5 | 5572583 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Eye/Textures/Iris/feather_N` | core | working tree | 186a32860d37ae709d35b1c7e8aa6336d9ebeabf1049e65d885c202d5ea427d0 | 2069229 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Eye/Textures/T_Base_Tile_DetailNormal` | core | working tree | 531fe2d96b67bee548300dc46a9ce8a650db1b1f6c766f43f9ad42070fd0ef0d | 143434 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Eye/Textures/T_EV_DustPanner_01` | core | working tree | 1b8b2e5d72a2e844018e120d87b76856e06ab7324cf15deeb7e30e8cd47e8294 | 53575 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Eye/Textures/T_EyeMidPlaneDisplacement` | core | working tree | e26785eca9bf681337788ae05263d2404ab0a93a10e5e0ef5e21bf8bd8aa9845 | 1106635 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Eye/Textures/T_EyeSclera_D` | core | working tree | 2157d1257b58ae6352a0bd96d886120ed69e7b6aa336a43eebc4cfec1eddf198 | 3869446 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Eye/Textures/T_EyeSclera_N` | core | working tree | d89124dfee2933b08e520cccc36c3cf7f571b894bb04a01424a50ed45a0c8d02 | 15222474 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Eye/Textures/T_Eye_N` | core | working tree | 7b42266b4197ac45deb1537cb23499f1bef83c3b831c94d51c067084b23d9b69 | 209856 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Eye/Textures/T_Iris001_01_D` | core | working tree | 511a27292a2978f6ce37afafb14bb7b5d75f47fea1f13c01ff6e86e42c9eadc6 | 1403400 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Eye/Textures/T_Shared_Eye_AO` | core | working tree | 2e95c07be98bc93c6e19d9f67ccd7e9b5df30532e4059aba198d0ec7680e0b71 | 95503 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Eye/Textures/T_Veins_D` | core | working tree | 9a7d32b9cb8b6c4cf677d1ffa4424044a5b51e1fe0937eb41d7bbcddcc57855d | 5354107 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Eye/Textures/T_alice_sun_painted` | core | working tree | ba254baab2c768d26af8baf8144e8b0c051af619dbf150201924c939598454d0 | 228461 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Eye/Textures/T_iris_color_picker` | core | working tree | 60cfbafb96225a26913adbf75d671037f333fdd1199fc2c4b1fdf77ef0e95910 | 90653 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Eye/Textures/T_lacrimal_N` | core | working tree | 7aadb14752421feb19c42e6d33bc04068d6430015901366312e27a01401e51da | 1432610 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Material_Functions/MF_Skin_ScalableNormals` | core | working tree | 3b86bee821179df733a9c689c2cc5b8f7cb3dd8329e1c440ea21f83325382358 | 192876 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Material_Functions/MF_Skin_ScalableNormals_Regions` | core | working tree | ed1ad296db8256721ff982f01f9571e7188bd07c140eddff56f3a6ea1ec83640 | 30055 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Material_Functions/MF_skin_animated` | core | working tree | 7fe4b6fa6b05bf5f77ca474770221b9f5265a6cf411eabb9ce996b95b012bfea | 102637 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Material_Functions/MF_skin_bakedInputs` | core | working tree | 124df67ee4f47dbc9dbe4ca4f5ef18e299d2281e3131e5bc8dae6e96763a51d3 | 45592 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Material_Functions/MF_skin_bentNormalsAO` | core | working tree | 076563413f80edb92d6bd2e851e736d6306e935b4868d537e4a71785a6869282 | 23621 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Material_Functions/MF_skin_fakeAO` | core | working tree | c50774c674289c78deb02d2c0ba7fc82df364d90a31c9589085ce21b6f94820e | 28529 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Material_Functions/MF_skin_fuzzApply` | core | working tree | 4251072c3384d519f2ce23bc671139c809beb1e6020dec6d292a3d4e73fae2ea | 31677 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Material_Functions/MF_skin_globalAdjustmentsPostBake` | core | working tree | 963f90f5280ef514894773904237d71528c7b9ed59d3e9422ea302c8758a4ec2 | 51118 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Material_Functions/MF_skin_microSkinDetails` | core | working tree | 308cd0229ad39e267b2e2a94427358d7fe9ce8256a93e4e8e8860f85b5010435 | 54742 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Material_Functions/MF_skin_mipmapAdjustments` | core | working tree | 2266dfec820e17f19eefe40ce2095aa30b58996dcbd6c43bfc04ea93c97677dd | 43148 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Material_Functions/MF_skin_scalability` | core | working tree | 3d9584588e285e195479fa146d75e0d055443083340d620f32248d05c2183d73 | 56924 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Material_Functions/MF_skin_scatterAnisotropyPT` | core | working tree | 6f60dbd94b5cfd4a7d3ae10ee6ff9963a65d330f06c41926b6d97ef1087449cb | 10789 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Material_Functions/MF_skin_utils` | core | working tree | fe20d8403b30018adc3312e359fab02030d7e3eef2edd0c8407e28e105e18fe6 | 18641 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Material_Functions/Skin_Animated/MF_AnimatedMaps` | core | working tree | c60e20e877ca83ba1d17856ddad8f041c048364ecab85ff16a2d3874d60c4c75 | 20819 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Material_Functions/Skin_Animated/MF_HeadMask_01A` | core | working tree | 68eab9b322853e1575d78dec60b9c4f5978bce105496def616f4222afb626ad5 | 36325 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Material_Functions/Skin_Animated/MF_HeadMask_02A` | core | working tree | e7cd9db978a3d5ce67c37194e9df3525ec2410cddf897d22e11487d05f7d2c7d | 24263 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Material_Functions/Skin_Animated/MF_HeadMask_03A` | core | working tree | adb46c5503616068cb7c618498667b59a419b5292807bdb898503adb8961301e | 25261 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Material_Functions/Skin_Animated/MF_HeadMask_TexArraySample` | core | working tree | dc7a51f159c4c5fb9e7750efb39feca71275b25c46851803504c49b1568bb08e | 13236 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Materials/Baked/MI_Head_Baked_LOD0_VT` | core | working tree | f85889bf1851d639f1e0914bdf037f6bd0b4b18c3a6684809f591e5426e6545b | 17295 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Materials/M_skin_unified_baked` | core | working tree | 03da0aa2177714cf05f6390b84ecdaf1f0318f344cce515070d9715cf513568e | 82191 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Materials/SSP_skin_unified` | core | working tree | 333509cbf26bd9c54727ae71197f900eaa44ae8e82b30fb7d8426ecaa9f07395 | 3359 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Textures/Scalable_Normals/T_Pores_FlowMap` | core | working tree | 8d4763e8a39f26d6c0d2a813ffdb9f6bf21fde9366f1d10b87fda460f3935207 | 604439 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Textures/Scalable_Normals/T_Pores_Horizontal_Normal3C` | core | working tree | 80a3f626698d0f6267c993a3c860df86a3f5352c96fa0369cd2409e67bb59045 | 395822 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Textures/Scalable_Normals/T_Pores_Neutral_Normal3C` | core | working tree | 31ce31c47b18a50a00699cf301f85edc080a2071553c7f4e98388b8cb04dea45 | 768284 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Textures/Scalable_Normals/T_Pores_Nose_Normal3C` | core | working tree | 79a2e1d3ee92fbc2a12fd8bc0f9a9a9fd90b3fc4420b925930c7c3af70808531 | 877758 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Textures/Scalable_Normals/T_Pores_PoreMask` | core | working tree | a2e403bf3ad30d262264c588834c2bb4bf93d8304f30fdaedce922a8c8c00535 | 98666 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Textures/Scalable_Normals/T_Pores_RegionMask` | core | working tree | b0f2cc4441c24c23d615981be30da76e97058dee3d93ebffc1da784ad89145a6 | 31433 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Textures/Scalable_Normals/T_Pores_Vertical_Normal3C` | core | working tree | 027ead7eada933c9767525ef924832b5a74ad90b502e141739918809ea85eae2 | 655404 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Textures/Skin_Animated/T_head_wm13_msk_01` | core | working tree | 2a235d1de27a6c301d63ab71fc4ccf0d6ebc0d839a854bb2aa243934182a8947 | 59902 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Textures/Skin_Animated/T_head_wm1_msk_01` | core | working tree | 7d556e02db0179e093b0c2f0ff8338804a41de847855e7f385efb2fae2c25d1e | 159931 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Textures/Skin_Animated/T_head_wm1_msk_02` | core | working tree | 812e53f1b8fadef500254615e7f1e726716331b860a40cd3c64b2ad3edac090e | 249605 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Textures/Skin_Animated/T_head_wm1_msk_03` | core | working tree | 611522842783d71e28d26d2ddc4baa338a27c1e10c6198c1cfad1971c5cfd693 | 538591 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Textures/Skin_Animated/T_head_wm1_msk_04a` | core | working tree | c426646ecdd170f1c744c480280c926fc04927c0dc5a8610674d4479f6c26069 | 198301 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Textures/Skin_Animated/T_head_wm2_msk_01` | core | working tree | 3c49e2c147b119b9a6bfb647252734c7c7a278dc0fdd3cd7fe956f6d8d4ea19a | 210276 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Textures/Skin_Animated/T_head_wm2_msk_02` | core | working tree | d69ffe9541aa0d849ec84b59ef5b7610bd001b36c7ed4f54c67470e07c8f2a80 | 401775 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Textures/Skin_Animated/T_head_wm2_msk_03a` | core | working tree | 5a66b12c02e78a5af7fae1244216c1b3bb6fb2f4c4c3275b37e131413c808d2c | 321863 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Textures/Skin_Animated/T_head_wm3_msk_01` | core | working tree | 8ddafd5036640ad0209c633175b620e96745dff6bd4a947a0bdc6cd2d1ee6b8a | 152343 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Textures/Skin_Animated/T_head_wm3_msk_02` | core | working tree | 5c70f8f2efaa4fe86d5c7760ec7219a2590fbeba650584cba917d512f82bc4a5 | 306692 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Textures/Skin_Animated/T_head_wm_msk_Array` | core | working tree | ab10fe8ea7a4e53ea542e9b0edecc103339992fbc6ccbf393c1879c0c077f5a6 | 2504212 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Textures/T_SkinMicro3_N` | core | working tree | 52192c32c290b904f8680dd0814514c7a935c5e90f427da97d8adc9e42dac1d9 | 2184262 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Skin/Textures/T_skinMicro3_CAV` | core | working tree | c33ce2751d013730c5e79c9ab51d9388270e472d9fe8edfe3ab3aee3ff8458ea | 1721820 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Teeth/Materials/MI_teeth_unified` | core | working tree | 1b7bd2f17ea2f6131ff5904dd07dddf84919f27d30ac2599b4d68aee39bf36a6 | 10203 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Teeth/Materials/MI_teeth_unified_MH_preset` | core | working tree | 0e11f32bd74087225978b8141be5ce5aeae0174e2a95cec1f344913a882340ee | 22016 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Teeth/Materials/M_teeth_unified` | core | working tree | 0473e6edd15f85bfc2f45b301abff59e2d0ddc6826381a330019ab58b3baa942 | 216960 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Teeth/Materials/SSP_teeth_unified` | core | working tree | ef04d1b688a6834467ee9afbe9ad1d79a15c8fdaed9f90c05b206023c921d094 | 3402 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Teeth/Textures/T_Teeth_BaseColor` | core | working tree | 766e974e7a46519bd8a0b2688e41ba6caf882e6b47980793f4c8aa43dfcc5a1f | 4448086 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Teeth/Textures/T_Teeth_DetailNormal` | core | working tree | 34c3bc322cc8ea92ef0ab51856896641f7232662c196da4fdecf6f466ba5669b | 6101839 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Teeth/Textures/T_Teeth_Masks_001` | core | working tree | a07cc8b297773d870c7146b3c551020a8fba3628baef8a32326b1c9cb5ef9da2 | 2230628 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Teeth/Textures/T_Teeth_Masks_002` | core | working tree | 3cdcff8aa3ba836999e9d988e549dca5b9a3291b57face12f040f4602d380711 | 384192 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Teeth/Textures/T_Teeth_Normal` | core | working tree | 67bb03f0deebe0bcac6627d447b70e57d70e5bce5293733ccc518df44d29f19b | 2994467 | identical |
| `/Game/MetaHumans/Common/Lookdev_UHM/Teeth/Textures/T_Teeth_SharpNormal` | core | working tree | ee56e042b2023694d95c6b874cab4232561443f10ccb6e2975e2e35c318828a0 | 2494681 | identical |
| `/Game/MetaHumans/Common/Materials/MF_GrayNormal` | core | working tree | 36f9df81661f4a4159917a7cf7251e273f2888ecd190600c0c0dbd16a19c926c | 12003 | identical |
| `/Game/MetaHumans/Common/Materials/MI_Eyelashes_HigherLODs` | core | working tree | 6271d8cb37b697d8a88ddff70fff8c4520583b5717d32bc1b68b2414f9da4819 | 9511 | identical |
| `/Game/MetaHumans/Common/Materials/MI_Eyelashes_LowerLODs` | core | working tree | 5eff67d59f983ba52ee28937131b11765bb414c653168022fdaac633f2c01f90 | 9428 | identical |
| `/Game/MetaHumans/Common/Materials/M_GrayTexture_Eyes` | core | working tree | dd71ab6de447e62e6ce9ff0d3a359a7b8e4efabd7e0aaa4b978c61add1d9ebf8 | 11643 | identical |
| `/Game/MetaHumans/Common/Materials/M_GrayTexture_Head` | core | working tree | 481705d3c2fa21b52de633878b7ab18b89b19b0b87e20b45252a2219039b2fd7 | 13967 | identical |
| `/Game/MetaHumans/Common/Materials/M_GrayTexture_Teeth` | core | working tree | 746c580e8a8e871b47c88e91f3a5a7b9fb81ea59170951218453138d355936fc | 17388 | identical |
| `/Game/MetaHumans/Common/Materials/M_Hide` | core | working tree | 2a88b3476c5dcd8050ab71e349646a6ba2d0454458ef495b87b669a0fe87d633 | 8594 | identical |
| `/Game/MetaHumans/Common/Optional/BodyTextures/T_Skin_Microtiling_M` | core | working tree | 1c6ffe9a853afc415d8f5fc305b04937b2ac359d74f67489c1b25374136ad09b | 755010 | identical |
| `/Game/MetaHumans/Common/Optional/Grooms/GroomAssets/Eyebrows/Eyebrows_M_SlightArch/Eyebrows_M_SlightArch_CardsAtlas_Attribute` | core | working tree | b1c82af7f616e929f5dc6fd4bcf468b86b7b43c6b19800bf6ee4f3520d21494d | 3142488 | identical |
| `/Game/MetaHumans/Common/Optional/Grooms/GroomAssets/Eyebrows/Eyebrows_M_SlightArch/Eyebrows_M_SlightArch_CardsAtlas_Tangent` | core | working tree | cfebf32dbb2d1409ea3e7d5a7b0f609b8d4634ae4061f146fb90b2bea99ac700 | 101427 | identical |
| `/Game/MetaHumans/Common/Optional/Grooms/GroomAssets/Hair/Hair_S_BrushCut/Hair_S_BrushCut_ColorXYDepthGroupID` | core | working tree | 16ba676bdc36059f8133074ed10af82cd3c3c19fe872dbc9d912d676a748f4f1 | 412774 | identical |
| `/Game/MetaHumans/Common/Optional/Grooms/GroomAssets/Hair/Hair_S_BrushCut/Hair_S_BrushCut_Helmet_LOD5` | core | working tree | cbf552c53117c7ec7862b2d0840b444ad7d4a965c1920d43b2b0786b34422d1d | 128366 | identical |
| `/Game/MetaHumans/Common/Optional/Grooms/GroomAssets/Hair/Hair_S_BrushCut/Hair_S_BrushCut_RooUVSeedCoverage` | core | working tree | a0a1750fb69e79959ab9bce186c5cbbcfaa91a59c9f8166325c87243ec755819 | 5593849 | identical |
| `/Game/MetaHumans/Common/Optional/Grooms/GroomAssets/Hair/Hair_S_BrushCut/Hair_S_BrushCut_TangentCoordU` | core | working tree | 79a1f489b51c7934041018991c487a22b5ec45d55d19d8f59887cba66627d2d8 | 466878 | identical |
| `/Game/MetaHumans/Common/Optional/Grooms/HighlightsTextures/HighlightsMask_dense` | core | working tree | c039eefe64f7c04733fb7b78d5a2f0011e49ad7088652a61acabaa930e468330 | 383384 | identical |
| `/Game/MetaHumans/Common/Textures/Eyelashes/T_Eyelashes_S_Fine_Coverage` | core | working tree | 47fb56e888e4810cb3215917610afcb41ce62beab0d823107a75b0f6f9c02e56 | 291966 | identical |
| `/Game/MetaHumans/Common/Textures/Eyelashes/T_Eyelashes_S_Sparse_Coverage` | core | working tree | b97404f57b3dd3c56941b9efd3b3356ffbc45ec2428e7bc1771d009078e0018e | 431589 | identical |
| `/Game/MetaHumans/Common/Textures/T_Gray_Eyes_D` | core | working tree | b11ac1014c18828b3d2504e60da80f845a890de822de16c9db66118c2655432a | 24089 | identical |
| `/Game/MetaHumans/Common/Textures/T_Gray_Head_D` | core | working tree | 0d39a3e536545e4eaea5a261fe4708c3e0c21a823c8b532cf23ebc561274c93a | 1528355 | identical |
| `/Game/MetaHumans/Common/Textures/T_Gray_N` | core | working tree | 522a31b9227c0ae055f1a1cc4374e37132e07b265dba4dad25395b775d379539 | 19292 | identical |
| `/Game/MetaHumans/Common/Textures/T_Gray_Teeth_D` | core | working tree | 94186808f15613c21ce30c6c27db3770f2b4c1d0a686274666e786e6bc898f08 | 624126 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/BP_MH_PlayerDefault` | core | working tree | 4c09d057d94bfad102f11a4378c376ce06f6442826e58c79e132c6e77ab13277 | 204039 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Body/Baked/T_Body_BC_VT` | core | working tree | 6861ea13445edbc6ce1a5ac0024845ef9c7d13830be95db7bce5c2cab17633b7 | 6602557 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Body/Baked/T_Body_N_VT` | core | working tree | f165735b9253d15ad42f6b936275d02b8481a01ace599c83c7ed9ca41383538c | 37593182 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Body/Baked/T_Body_SRMF_VT` | core | working tree | 5af64c1919cddc43d5b742decbaf99b2cf16073ea683976876142fc36f925757 | 59103175 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Body/Baked/T_Body_Scatter_VT` | core | working tree | 5d5b6f3eaed55f97d22d1332c9f8d7e8f0ce9978e4c9014a3ba4d5743fa77367 | 63202 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Body/Materials/MI_Body_Baked_VT` | core | working tree | f372b28c47d6d0c7360f6498905b535b9a6d225dda74fa30d3f0aa61e702385c | 9350 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Body/PHYS_MH_PlayerDefault` | core | working tree | 80180f930faf829bdc913a0c47aecd71fe684d16ee821b58a1a96ac17927c0ab | 220190 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Body/SKM_MH_PlayerDefault_BodyMesh` | core | working tree | 59d6bf16c4e56cbc8ad9b411899e10372c7ff5600092a4d21dca4b2ee53ed9bc | 11709147 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Body/SKM_MH_PlayerDefault_BodyMesh_DNA` | core | working tree | 17a6403812df4b5dfbe2db3a3cc2471defad2c00c777369831a6d6e249d2ffaa | 4613099 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Baked/T_BakedNormal_LOD3` | core | working tree | 1786f2e283ffc847f15b63c60d96680f1443b95b58268eeb3357bb5c6f6c80ea | 89047 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Baked/T_BakedNormal_LOD5` | core | working tree | 9156233508b71fe5a14a85a779fe62dc985d0230961cf5a7b84fbdcfdd8ae9c4 | 101389 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Baked/T_EyeIrisL_BC` | core | working tree | e5a606da2d73d02933dc5b6e336c9ff1947996287eaa0f3e4a44417b2695e2cf | 1504334 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Baked/T_EyeIrisL_N` | core | working tree | d557c7d9c0f77d72387b6272e717666445b0845a073693d88aeb1ed15e120b2d | 2690776 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Baked/T_EyeIrisR_BC` | core | working tree | 2921eb989d8897e2a484ac727aaa5c1b094c1da8b7ec30880301594d551e1af8 | 1504334 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Baked/T_EyeIrisR_N` | core | working tree | 11f7dbb40b7d06afbef276542a7d72e42f677677f4d116064371f2699b2aaec0 | 2690776 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Baked/T_EyeScleraL_BC` | core | working tree | 994ffdeede835ba173f8ee5186728a6a2fecec2aa60e2c8de27020c41df40c00 | 2068618 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Baked/T_EyeScleraL_N` | core | working tree | 37cf65060f49612def272cf97094558e5149577ae7fbf8a6f756de46bb26946c | 2192515 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Baked/T_EyeScleraR_BC` | core | working tree | b3d78277813562c904acead4f99b8873fa95b2811c492c0e7c4be76382d19509 | 2067943 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Baked/T_EyeScleraR_N` | core | working tree | 481d2968e3bfbe52d970b090c3f6ce8ea5fffb1fc058d6c3b7a533a9f59965df | 2192515 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Baked/T_Head_LOD1_BC_VT` | core | working tree | ab0e1edc33b090950d8a8e8930829859402ee74811f9cc3332b50514ea144c43 | 3990369 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Baked/T_Head_LOD1_N_VT` | core | working tree | 21b53acf9157599a3527fa6e90ddd24002f87e2d775366272ef148f2907ae086 | 17180320 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Baked/T_Head_LOD1_SRMF_VT` | core | working tree | a1ac3a18b79b51da953e416df1061d1528aae51b896f606459b74dbdd8c7c959 | 28861704 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Baked/T_Head_LOD1_Scatter_VT` | core | working tree | be9638e8fda588391ad888ce6a20d778f564e0a357f46b69c3336fface2f0e42 | 101957 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Baked/T_Head_LOD3_BC_VT` | core | working tree | 3ec79ef605c5529154961b2727c6e6b7c3e544458c14017aaf1e2308852bf00b | 4283382 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Baked/T_Head_LOD3_N_VT` | core | working tree | 5c75de323ec3d1c4814e90f8108e36435937360038dde2b7c47557b71db26f3a | 6380797 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Baked/T_Head_LOD3_SRMF_VT` | core | working tree | 128b02d5869d87421b36a707cbf8d1064e742f4b315c5f309b4e470176f33b18 | 6861257 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Baked/T_Head_LOD3_Scatter_VT` | core | working tree | 836c9590a9e0f0e5ad335db6a999c4eaba610c74456debc6a73cc869498b6c48 | 152679 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Baked/T_Head_LOD5to7_BC_VT` | core | working tree | 095b471e071467f5de0020596bdf177bc9d239523028995b761a320edaf5059a | 1507857 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Baked/T_Head_LOD5to7_N_VT` | core | working tree | 124ac904fc529ae83de1a829354cf559d45f58efe36dee32e31874ca45ed2a55 | 1963388 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Baked/T_Head_LOD5to7_SRMF` | core | working tree | bd35696d91d81d7e6625a59c02b48cece16538adce9600e81338cb747b076193 | 2091815 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Baked/T_Head_LOD5to7_Scatter_VT` | core | working tree | 993eb0438a1f8a7ce23c8ec74f2ac6fae5f6c0d9ed4b5405587692b90b517933 | 47961 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Baked/T_Teeth_BC` | core | working tree | 7eba522ac26c08261b2a64bd1084b8d46b9e91b0dad80d3711aa0a8afec291ad | 990207 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Baked/T_Teeth_N` | core | working tree | 00e14b32bbf1a27f557b57615b9cc26d7c236103370a650b87492d5b0b151eb8 | 6115069 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Baked/T_Teeth_SRM` | core | working tree | 4d808fd1402fd6b56af9c3bea70f2213cc37e1c0eb7ec38b0acdc3a559e32489 | 687658 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Baked/T_Teeth_Scatter` | core | working tree | 2129e46144c6e6a72056865aa41c4b2eef74e2533ce5efca1d8f0776ee1da29f | 5627 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Materials/MI_EyeL_Baked` | core | working tree | 5a875deb29c9c1711850f8158b63760927bf01b017b8b4fcf10fa0b5b749e2dd | 11919 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Materials/MI_EyeR_Baked` | core | working tree | da002b122d1d720d3b439b6cb849e41dec5ea8381adb61350484f8bbc50e4358 | 12712 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Materials/MI_Face_EyeShell` | core | working tree | daf90e145fc1e8ab83a934f103a0382add107d20cb9d80e5d657eb6b4f984686 | 4853 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Materials/MI_Face_Eyelashes` | core | working tree | 8f7ae44cfdb431045afc49649e88b01b19d75006f29f30bd2befb1f48c3c1d29 | 6995 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Materials/MI_Face_EyelashesHiLODs` | core | working tree | 50e30d9dd6afe7882a6f54f2bb00f19e9c9059ac6f385589d1e8402b339d473b | 7473 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Materials/MI_Face_LacrimalFluid` | core | working tree | 31af4972b6f2edf1d2d9d3ccaaccd21ddec18568dd48965e3ba5c8469ff842e7 | 4907 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Materials/MI_Face_Skin_Baked_LOD1_VT` | core | working tree | 329edde1e265d82e61ae47ce5bf818600e4f029a55bea5cb4ed379a362c4938e | 9408 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Materials/MI_Face_Skin_Baked_LOD3_VT` | core | working tree | 4fa74a240fbf48addded9002f35ea4256c149fac6b117702f694d056b39be99b | 9879 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Materials/MI_Face_Skin_Baked_LOD5to7_VT` | core | working tree | e3c659d4ac433d4af705144f019502241957050538da2e2210573c7cfd6fd855 | 13045 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Materials/MI_Teeth_Baked` | core | working tree | 5b715d42c38c2a8d9524613de8b2303970b9c998235fd765f7a0d246c13fe2e3 | 6088 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/SKM_MH_PlayerDefault_FaceMesh` | core | working tree | ae486f1cb0d0c69088a43e66308e0e1e4904964a17446a0f05452a7478055829 | 6495023 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/SKM_MH_PlayerDefault_FaceMesh_DNA` | core | working tree | a23a2227807274fd1b3e35325af4ff1aab1c4c068a33c6766a0d7165b6332a44 | 5474983 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Textures/T_Face_Basecolor_Animated_CM1` | core | working tree | 8ee8f835b68df79191b68ba650ec723e43f593f085b11204fd9659c0cc447852 | 151152 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Textures/T_Face_Basecolor_Animated_CM2` | core | working tree | d1a80fd7e693074ffaf7319c28e681b87316e9dbca57d9b4ef75ad45f3b13dc4 | 142400 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Textures/T_Face_Basecolor_Animated_CM3` | core | working tree | 0926bd832dfb378b5636e2dd53d02e32f353c5b132781a89c53a1b3d823d7dad | 69080 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Textures/T_Face_Normal_Animated_WM1` | core | working tree | e08baa3d35d776d4b7d55baae5d9f5fe054ffad2f7e5ae61f5605e53ae704733 | 555027 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Textures/T_Face_Normal_Animated_WM2` | core | working tree | e91743c0e74a2760ef894d34ceff1746638d20f96332375b3f674b1e6d9a7a37 | 496792 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Face/Textures/T_Face_Normal_Animated_WM3` | core | working tree | 79e187bfbdec89d6066a28b3dad60bbae32cebd2c4d7e7e81665d2e57df4173f | 238195 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Grooms/Eyebrows_M_SlightArch` | core | working tree | 48fe32c1fa74447664bba0670fd35ffb9624a909017ead5ebe24e9438d59555b | 143462 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Grooms/Eyebrows_M_SlightArch_Binding` | core | working tree | 639c72e87812a79f25dc4b986222018ae9d2049c4b0dd7525a44f4e30e7785ff | 5950 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Grooms/Eyebrows_M_SlightArch_CardsMesh_Group0_LOD1` | core | working tree | a1c01d4735c0fc24f747e3ea7c0cf5c9f905dbf7bf6640100bb6cad98e5b71ee | 194950 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Grooms/Eyebrows_M_SlightArch_CardsMesh_Group0_LOD3` | core | working tree | 0d122b98489cb8ae84cf6a71be901627253f068b1a8c8df75e869ba9db6ed235 | 105488 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Grooms/Eyelashes_S_Fine` | core | working tree | 140c939c9241dacb012a73659d6da8014bda2c274c28894eb7a21cdebdefe7c6 | 131382 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Grooms/Eyelashes_S_Fine_Binding` | core | working tree | f1b9f62edbb70477792a9afa50079779770145e3ef59035c332e2654926e2025 | 5958 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Grooms/GroomAsset_0` | core | working tree | 1d335236658e221424b4b07e84d0281952ac67f39afdecec6f9f890693980d9e | 13729979 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Grooms/Hair_S_BrushCut` | core | working tree | 356b030ac5ef3f682bbf2590b07a54e981e50dbe88208a51e44c4138aecdf7cd | 6153 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Grooms/Hair_S_BrushCut_CardsMesh_Group0_LOD1` | core | working tree | 0d661d28cebfeb6f7bd54df7bbcc0eebf7c973f556e316d85164fbd8060e44fd | 1314629 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Grooms/Hair_S_BrushCut_CardsMesh_Group0_LOD3` | core | working tree | 73f8cc201f064d29bab3126086bbdc1c4a211f8eaa569636ad4ecf1090512212 | 594737 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Grooms/Hair_S_BrushCut_Helmet_LOD5` | core | working tree | eeb585be8990cb170634689989cd8c659c437b0cb5a366ed42c8c550445d9123 | 128309 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Grooms/Hair_S_BrushCut_Helmet_LOD7` | core | working tree | e1631621ce081f7d1ffb54079f4560c0a08476c498e7662f9ccfa72c1fff8f35 | 81979 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Grooms/MI_WI_Eyebrows_M_SlightArch_Facial_Hair` | core | working tree | 72d0a49e38abf9d1f875ef5070b8f83cfaf4aa799a3b49617ff1b6eeb3a59e9b | 7467 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Grooms/MI_WI_Eyebrows_M_SlightArch_Hair` | core | working tree | 1addecfe9d17438ed09c6912d8d5da625408475a0f4c1015436f22ce1a507ee3 | 9816 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Grooms/MI_WI_Eyelashes_S_Fine_Hair` | core | working tree | 0014a7d0d58308ff0ecc1b11d818b99410eed9c33396bb31a430bbd90cb865e9 | 8874 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Grooms/MI_WI_Hair_S_BrushCut_Hair` | core | working tree | 3ee9266d62dab9ef6df493380d2293040539deee00a6d7eb81a329b40ac73253 | 9521 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Grooms/MI_WI_Hair_S_BrushCut_Hair_Cards` | core | working tree | d2798d19702d39959c2dc5e66ab5e80aba4939263c8c6a750a856aa134a4f9aa | 9581 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Grooms/MI_WI_Hair_S_BrushCut_Hair_Helmet` | core | working tree | a8c6d7c9cc3ac37c3f60ee6f772032f27691787f1147ea081219ff7129c53098 | 9591 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Grooms/Textures/Hair_S_BrushCut_CardsAtlas_Attribute` | core | working tree | d643a99976b7f9beb5e44f5e505405b91e9b1bf2fb9e862798a280452a3a7d55 | 4127069 | identical |
| `/Game/MetaHumans/MH_PlayerDefault/Grooms/Textures/Hair_S_BrushCut_CardsAtlas_Tangent` | core | working tree | 4ca4f105b5c9f95df93f1a4ebf14d445a987546dc48d768057bf1e5534640092 | 5014701 | identical |
| `/Game/NiagaraExamples/EffectTypes/NET_Environment_Looping` | core | working tree | 5bf0deceebd7e1c84facee31eb9104a9c54a160e69a014a95da7b3153eb6c6a3 | 11773 | identical |
| `/Game/NiagaraExamples/EffectTypes/NET_Gameplay_Burst` | core | working tree | a27e1e3835546bdb44a621386c1a8911ea3d1de5330ea4b7c4e55214ebe0be61 | 11397 | identical |
| `/Game/NiagaraExamples/EffectTypes/NET_Gameplay_Looping` | core | working tree | eeb835b0e7bf89d5a850b468dac202c0a765f53d3a13b1cbd48743a55a4c10ad | 11764 | identical |
| `/Game/NiagaraExamples/FX_Explosions/CameraShake/CS_Explosion_01` | core | working tree | 6c922d474ade125c7b5732e48a1089b6f4629ee73972c0ec9270ffbba386e631 | 6573 | identical |
| `/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Debris` | core | working tree | fbc450a992505b86a40e7e3bb34a3b039751de3770411b16bb308c27e2afb33c | 424466 | identical |
| `/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Explosion` | core | working tree | e61e8e9e69910e3aef857b90704e17bf3a15a07d19dcdfe9445e937029ab1370 | 491252 | identical |
| `/Game/NiagaraExamples/FX_Explosions/Emitters/NE_GroundDust` | core | working tree | 0478cac45a67bfa38748b040234b1000beea6e585dac3a5a415deea347ca2c96 | 403017 | identical |
| `/Game/NiagaraExamples/FX_Explosions/Emitters/NE_PostProcess` | core | working tree | 3dbe10714f429530308185ed5c2704c144094d119b41f9841a7a4b1fb5e0e23b | 153987 | identical |
| `/Game/NiagaraExamples/FX_Explosions/Emitters/NE_SparkDebris` | core | working tree | 30f27fa54926d19d103a69343965edfccc0192083a10013b8399ea3fcfc516d3 | 308150 | identical |
| `/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small` | core | working tree | 33e8e20325006312aeac692497fad70043ef545f46d95e9d13a8a19f874d04a9 | 5719777 | identical |
| `/Game/NiagaraExamples/FX_Misc/NS_Fire` | core | working tree | 3bb5faa88f7e305cb202b78d3d81a3b886dac3e940873ecbd3617b1b02f48ba1 | 3471503 | identical |
| `/Game/NiagaraExamples/FX_Ribbons/Emitters/NE_Arc` | core | working tree | f6d5de48017e778cd32e60b69d37b54a56a684a41f0150108ec68b487331828a | 825544 | identical |
| `/Game/NiagaraExamples/MPC_NiagaraExamples` | core | working tree | 4455ec7e8c3c9c908062751b51c1e55728456c356c82f6ac35714f0cee2d5c5c | 1881 | identical |
| `/Game/NiagaraExamples/Materials/MI_ExplosionFlare` | core | working tree | 9c14ccbd0303d6e0b105b08403c7f11e7f2678fa79f2679c483a6b282126ba6d | 8517 | identical |
| `/Game/NiagaraExamples/Materials/MI_ExplosionRoil_8x8` | core | working tree | 0c5451df141bc0eafcf14880ec147a2e09fdbbedd3784e0c035bcd636f0e2a01 | 19638 | identical |
| `/Game/NiagaraExamples/Materials/MI_Explosion_Decal` | core | working tree | b31bc2f644d48b868566cc28fe13acaf7689d3e3e87f87d35ee967a4eae5af2e | 9029 | identical |
| `/Game/NiagaraExamples/Materials/MI_Explosion_Decal_Frame0` | core | working tree | 0235fd3be0e92dba150a96d3b52017fc36e4a067acf950ee35f646fa42d6f935 | 7284 | identical |
| `/Game/NiagaraExamples/Materials/MI_Flames` | core | working tree | fd8fc97e784cb6e62bf0f8be0406321ed9710874037e451dd6b3a0c93e6d85a4 | 8471 | identical |
| `/Game/NiagaraExamples/Materials/MI_Flare` | core | working tree | 560420f1c537c9156fb5f25b04285c4be2fdb3cc1563c12f1ee006a75b1f950d | 5843 | identical |
| `/Game/NiagaraExamples/Materials/MI_Flare_TeslaCoil` | core | working tree | 95d9d857027b806accab21426a42dd2efc384941358fe7cd8179624aa87a061b | 8458 | identical |
| `/Game/NiagaraExamples/Materials/MI_Pebbles` | core | working tree | 3ee2dc94980961cde3aaa1b97a5cb1b69d2deab422a26500d77b6819927e67bd | 6811 | identical |
| `/Game/NiagaraExamples/Materials/MI_SimpleDebris` | core | working tree | 814792bcf2213db177d48726beb58134d6bfda4c36e31aa1024907b219fd3996 | 7118 | identical |
| `/Game/NiagaraExamples/Materials/MI_SmokePuffLight_8x8` | core | working tree | 87c078b20a9c3a4aee0eb1178184b81847219348e0b1bb9729b18b75092cf0cc | 15786 | identical |
| `/Game/NiagaraExamples/Materials/MI_SmokePuffLight_8x8_Emissive_Tesla` | core | working tree | 52730236e8b97c318439606b15e48887cfd548c94e484dd6c81c73c7376e0daa | 16226 | identical |
| `/Game/NiagaraExamples/Materials/MI_Sparks` | core | working tree | 5cc57b2939ba9194b0629e4cdbcde292f4be2bdb28cbe71f5168e2facc77d730 | 7340 | identical |
| `/Game/NiagaraExamples/Materials/MasterMaterials/M_Decal_Glow` | core | working tree | 421cd3a3ffd3acc490b14c32d7967cd4e5acdab3990c2d53fc7000a49e3075a4 | 32273 | identical |
| `/Game/NiagaraExamples/Materials/MasterMaterials/M_Decal_SubUV` | core | working tree | ef0e05a24f716ae50d702627ecf1c39bff5b628073d7d9afc92a245dfaa77a51 | 26191 | identical |
| `/Game/NiagaraExamples/Materials/MasterMaterials/M_Flames` | core | working tree | e0e33afc2fc91b1d3ddaf5c58745c4c336d548d2973c5058c92b40df1d35b8d0 | 41316 | identical |
| `/Game/NiagaraExamples/Materials/MasterMaterials/M_Flare` | core | working tree | d408f0015857f14710fc515c9f20c9720b4496db2134b751635c1c826f371d29 | 26040 | identical |
| `/Game/NiagaraExamples/Materials/MasterMaterials/M_Pebbles` | core | working tree | d3ba41c8c4cbc8d15bea2c1e15b60058e343ba434151aad71744a71d2fe3ca1d | 26090 | identical |
| `/Game/NiagaraExamples/Materials/MasterMaterials/M_Quixel_Simple` | core | working tree | 621bcff6d6c37d080f4fe2eefb62c27780428e3f10e98b26ead4fcaa1ca82ee4 | 22770 | identical |
| `/Game/NiagaraExamples/Materials/MasterMaterials/M_Ribbon_Arc` | core | working tree | 8979e08df8938cb118a558f9c1dee727bdfc1d3115c909af83904c3d6ded35ad | 73245 | identical |
| `/Game/NiagaraExamples/Materials/MasterMaterials/M_SimpleDebris` | core | working tree | 46f6aec4854e2eeefa3e7ff6218d30eeeb7ac2633d0300d337c536cc05f0ef1f | 26304 | identical |
| `/Game/NiagaraExamples/Materials/MasterMaterials/M_SmokeAndFire_Sprites` | core | working tree | 532de65742544bdaae368408a46bb059b0c2f033650366947527ce50ead1179d | 152885 | identical |
| `/Game/NiagaraExamples/Materials/MasterMaterials/M_Sparks` | core | working tree | 7a0d34d9cbc2026c9335bb80b8763fdf45f39df17ecf56e239e8ecf0a1f0bff3 | 31237 | identical |
| `/Game/NiagaraExamples/Materials/MaterialFunctions/MF_DecalNormalFade` | core | working tree | d50e44824f627a9a7f2461d660b49b21e938d82122daf9b304b13fea0c921c1c | 15377 | identical |
| `/Game/NiagaraExamples/Materials/MaterialFunctions/MF_ExposureCompensation` | core | working tree | 3fa969c1e9761e99a70cb62e0f9b28db575eb71831b0ad6a3deb49b5c5d5e10c | 13944 | identical |
| `/Game/NiagaraExamples/Materials/MaterialFunctions/MF_FastSphereNormal` | core | working tree | d2d5e63b4f8e9e202e8b9da8b02201c1ab291cb94e4887f76aadf5fc2540a275 | 18404 | identical |
| `/Game/NiagaraExamples/Materials/MaterialFunctions/MF_MotionStretchSpark` | core | working tree | 6de768b97ce291f56355caad0877e9e47287f74ec66ed460b73d55ca6eb600ff | 25154 | identical |
| `/Game/NiagaraExamples/NPC_NiagaraExamples` | core | working tree | 9f92fe2ee4370885b5ecd918849480fa49da358c7778124cd438fd926dded0e0 | 4477 | identical |
| `/Game/NiagaraExamples/StaticMesh/Concrete_Rubble_uc1iccejw/MI_Concrete_Rubble_uc1iccejw_1K` | core | working tree | a4a1efe4b7f63b459fccaee3af0853a84b4774ae928c6547eb4aff3d668d5368 | 13361 | identical |
| `/Game/NiagaraExamples/StaticMesh/Concrete_Rubble_uc1iccejw/T_ConcreteRubble_uc1iccejw_1K_DpR` | core | working tree | dca3df7d82fd97e6d9bcfdcba185656f330420ebb3f2b6f9930ad35ad1fc9355 | 458054 | identical |
| `/Game/NiagaraExamples/StaticMesh/Concrete_Rubble_uc1iccejw/T_Concrete_Rubble_uc1iccejw_1K_D` | core | working tree | 63a6a12aa5b010b170dcf170b61a4f15670ebd73bba8594a314877e85e34f5a8 | 1195197 | identical |
| `/Game/NiagaraExamples/StaticMesh/Concrete_Rubble_uc1iccejw/T_Concrete_Rubble_uc1iccejw_1K_N` | core | working tree | 8f2953be8469c35ed3f416be7a509027f7fcb4fcb375a5d092fd7f9e32904153 | 1146480 | identical |
| `/Game/NiagaraExamples/StaticMesh/Concrete_Rubble_uc1jagbjw/MI_Concrete_Rubble_uc1jagbjw_1K` | core | working tree | 673daa211c17f907948690750b7686a5e44dc09dbbb15727fcb27af0af071522 | 12584 | identical |
| `/Game/NiagaraExamples/StaticMesh/Concrete_Rubble_uc1jagbjw/T_ConcreteRubble_uc1jagbjw_1K_DpR` | core | working tree | b7ab843ec8e193de0ce28188273cd25dc5b9af1bef9ed4f3c9e4ea9c2cbef587 | 452889 | identical |
| `/Game/NiagaraExamples/StaticMesh/Concrete_Rubble_uc1jagbjw/T_Concrete_Rubble_uc1jagbjw_1K_D` | core | working tree | 0759e7e856bef5546a4f59402c875e0c66bafdc089d9188fbff8f2c534783e60 | 1150815 | identical |
| `/Game/NiagaraExamples/StaticMesh/Concrete_Rubble_uc1jagbjw/T_Concrete_Rubble_uc1jagbjw_1K_N` | core | working tree | d7e2e27efb79426d3df8d4d04a3b99a522d81e54a1c40085bdaf523ced6a0a2c | 1164110 | identical |
| `/Game/NiagaraExamples/StaticMesh/Concrete_Rubble_uc1jagnjw/MI_Concrete_Rubble_uc1jagnjw_1K` | core | working tree | 71e75c7f729d2dadfe5f8121369cb9cf8b770f3646c5b7cd6c318eca78c33126 | 13033 | identical |
| `/Game/NiagaraExamples/StaticMesh/Concrete_Rubble_uc1jagnjw/T_ConcreteRubble_uc1jagnjw_1K_DpR` | core | working tree | 5544621370d47448af33eadc2a620f424099b72ef2d76c320171a3880c5ddf25 | 433113 | identical |
| `/Game/NiagaraExamples/StaticMesh/Concrete_Rubble_uc1jagnjw/T_Concrete_Rubble_uc1jagnjw_1K_D` | core | working tree | 0343d86d9963c95cb9191b5dcc82e18c478c41dfa9b55776af14df89d054dedb | 1183636 | identical |
| `/Game/NiagaraExamples/StaticMesh/Concrete_Rubble_uc1jagnjw/T_Concrete_Rubble_uc1jagnjw_1K_N` | core | working tree | 44f0e1e5881ffa0feccbc8543e0ab8842be5402f71e4f0e385f01154092c2dbf | 1086965 | identical |
| `/Game/NiagaraExamples/StaticMesh/Rock_shopk/MI_Rock_shopk_2K` | core | working tree | ba0ebdafceb64dc4072464b4858c231f2b40b36f87053ef17b053fa4ae4917ae | 13453 | identical |
| `/Game/NiagaraExamples/StaticMesh/Rock_shopk/T_Rock_shopk_2K_D` | core | working tree | 380ccec5ed41908b5e5bed9edbab9abafb82657e18238a5bbf1fd9588f554921 | 1279522 | identical |
| `/Game/NiagaraExamples/StaticMesh/Rock_shopk/T_Rock_shopk_2K_DpR` | core | working tree | 4a02d499cad663218fc2d6688d8497333eb1e3ffb15e7d1e688dbb7b21338465 | 547638 | identical |
| `/Game/NiagaraExamples/StaticMesh/Rock_shopk/T_Rock_shopk_2K_N` | core | working tree | b9d86321659925f1e6748262b4fd4f1931eb2a7ef480d79a3549ebd78c92ca22 | 1069019 | identical |
| `/Game/NiagaraExamples/StaticMesh/SM_Disk` | core | working tree | f0ee7a3e44b01ed66b55941a753feba63360a213aa2d402795456e69c418e0dc | 14952 | identical |
| `/Game/NiagaraExamples/StaticMesh/S_Concrete_Rubble_uc1iccejw` | core | working tree | d64de173ffcaccc34f4d49b035ffd83ae472e4803faa7793023fe0aa0ab000d0 | 36372 | identical |
| `/Game/NiagaraExamples/StaticMesh/S_Concrete_Rubble_uc1jagbjw` | core | working tree | 6143b05d800ef60d60baa0a9bcfc5e8a8e6cd5a83b182f07e76182ab1e3b0354 | 36866 | identical |
| `/Game/NiagaraExamples/StaticMesh/S_Concrete_Rubble_uc1jagnjw` | core | working tree | 7381d85706aaf5afcd6d1a179d8c1a838f7b2446290e7ea34ab63c01be21f5e8 | 26443 | identical |
| `/Game/NiagaraExamples/StaticMesh/S_Rock_shopk` | core | working tree | b1fdfc81081e53ffbbfddff3064e013092614b39fe2f66393a644cfc9627c7b2 | 31254 | identical |
| `/Game/NiagaraExamples/Textures/ColorCurves/Atlas_FXColorCurves` | core | working tree | 9660ff6c17cf7c33ef3bee84dd8893b1c113d31b50412173c0c826efc60ad77b | 6924 | identical |
| `/Game/NiagaraExamples/Textures/ColorCurves/EmissiveColorCurve` | core | working tree | bb7369e6f444e0a957ce001a6e13b530b0e326aed37f419acbd9951e27ae7ecb | 5560 | identical |
| `/Game/NiagaraExamples/Textures/Decals/ExplosionDecalMasks` | core | working tree | a0841bf2a02f23c4bf5d6f8b58e6beeace78d8fc8985c414b546889d271a085e | 2103938 | identical |
| `/Game/NiagaraExamples/Textures/Flares/LensFlare_01` | core | working tree | b547599267d6219958828ebbf0127115653615061540f8e0c9ad840ff021f59f | 129501 | identical |
| `/Game/NiagaraExamples/Textures/Noise/T_Hermite2Noise_CenteredTiling` | core | working tree | e2d8d43b7a8da528ee154d7ab5ec7a8ee440610a734b275e0746f2dc4b354722 | 3812552 | identical |
| `/Game/NiagaraExamples/Textures/Noise/T_HermiteNoise_CenteredTiling` | core | working tree | 96a11f81e751ad276f4982a00d67c1f707b4da82897765a3916f8f20b5e291f6 | 3184261 | identical |
| `/Game/NiagaraExamples/Textures/Sprites/T_ExplosionRoil_EOO_Loop` | core | working tree | ee97ef90f775452373cf035eecb6cc276bd10f69c5fda12747ae61665f2c2c6d | 4944463 | identical |
| `/Game/NiagaraExamples/Textures/Sprites/T_ExplosionRoil_Normals_Loop` | core | working tree | b70b2d998933164bed0efd1475114e3fa476f5f1241723a32e14220480610c3a | 8276631 | identical |
| `/Game/NiagaraExamples/Textures/Sprites/T_SmokePuffLight_EOO_Loop` | core | working tree | 12ce65c60986b47a7d79fa8bfd2da0a9703106a58769a449e9a492247284042c | 4154715 | identical |
| `/Game/NiagaraExamples/Textures/Sprites/T_SmokePuffLight_Normals_Loop` | core | working tree | eed655ffe5e1a672b7f64102e0f8f8a761ee441de3f0d2b4fd29cad5391f950f | 7740249 | identical |
| `/Game/NiagaraExamples/Textures/Utils/BaseEOO` | core | working tree | fa39a4ecd97f8f4e32cae78ebc33af12eae1f7bb1b97c71cea26b262ddd9bbf1 | 10181 | identical |
| `/Game/NiagaraExamples/Textures/Utils/BaseNormal` | core | working tree | 0a57c86bffcbe36da2007b71223d0ec582c50b8ca87fdaad0b23a828dfb30a4c | 10724 | identical |
| `/Game/NiagaraExamples/Textures/Utils/CutoutMask` | core | working tree | 8b8917b6ef26999f863240c46b03c7d884550b9f4fe269dc28f7e28ef1858540 | 11185 | identical |
| `/Game/NiagaraExamples/Textures/Utils/CutoutMask_8x8` | core | working tree | d229bc4606bafec09f16336873ce07249a122339c3bf5944182d1bb95e2a6987 | 24514 | identical |
| `/Game/Ninja/Animation/ABP_NinjaVisual` | core | working tree | 8064a49c04296462ce71a2efedbdc2cae75b396722e9802d8fe29d42d75ec3f7 | 399897 | identical |
| `/Game/Ninja/Animation/Combat/A_Throw01_WaistDraw` | feature_only | working tree | 650b6ae62a3ae6e3b13aff397e82a75f6107073d83b217c3e41f4e12ad5713f4 | 689842 | identical |
| `/Game/Ninja/Animation/Combat/A_Throw02_RisingDraw` | feature_only | working tree | 64ab4de6e80f1be1781d143231df47ce31fb7578fc77e8c52ba19293e67c8756 | 611117 | identical |
| `/Game/Ninja/Animation/Combat/A_Throw02_RisingDraw_Idle` | feature_only | working tree | ef08456460f81770cad4cce9b8a010ee3c3b619fa6e5e066f302813b50a42458 | 608693 | identical |
| `/Game/Ninja/Animation/HandSeals/A_Seal_Bird` | core | working tree | 701ed0f0c54a9e7cb3d94596772edfaab205d4ff7ec99696bdbe02e02288d6db | 94341 | identical |
| `/Game/Ninja/Animation/HandSeals/A_Seal_Boar` | core | working tree | b268a4c571cb48c0bd5d7794bc07e56d10a0afdc7df93e9f15a02da2bf9d7713 | 93475 | identical |
| `/Game/Ninja/Animation/HandSeals/A_Seal_Dog` | core | working tree | 12639365cc66226473ec3318ed4166f16d1d1d536c3000490fb3d9b2dd9c6a91 | 94261 | identical |
| `/Game/Ninja/Animation/HandSeals/A_Seal_Hare` | core | working tree | 842aacef63acec64e9c8eaede2c07788d1bf9e265e66701fa32049d5991289c6 | 93505 | identical |
| `/Game/Ninja/Animation/HandSeals/A_Seal_Horse` | core | working tree | b25c7263277f709f948a76b506d35fe91b6fd1007134df48f40a3cfc4ef1a0c6 | 93519 | identical |
| `/Game/Ninja/Animation/HandSeals/A_Seal_Monkey` | core | working tree | 2b01faafb535456c373ef3326625ed3f66f265a289114abf558a6dee9812e1ae | 94326 | identical |
| `/Game/Ninja/Animation/HandSeals/A_Seal_Ox` | core | working tree | e93f2aef6693dbafc9f0fc4ad37f3e95fbcb12aeb5aa40cab60fd4b1fe94ef6b | 93397 | identical |
| `/Game/Ninja/Animation/HandSeals/A_Seal_Ram` | core | working tree | 2a0f1dc5a324db2066268b27b90dcc1bb57dce696254685ee67cc7a231cf10c7 | 93374 | identical |
| `/Game/Ninja/Animation/HandSeals/A_Seal_Snake` | core | working tree | 0f350be998ddf16fba8f4f9831c393db0aea4d62c65e7663393c2e194ce345f3 | 93365 | identical |
| `/Game/Ninja/Animation/HandSeals/A_Seal_Tiger` | core | working tree | cd90b80cc03fe3130ce56e7c33b161007e5e65dfdcce8a81f8c5ea713534bdcd | 93355 | identical |
| `/Game/Ninja/Animation/Jutsu/A_Chidori_Charge` | core | working tree | 35d0c31cf33d5973938e06d387d02b9f4ecc4774027f56b25d31c8058656c574 | 93446 | identical |
| `/Game/Ninja/Animation/Jutsu/A_Summon_PalmSlam` | core | working tree | e79c5b8a5acab3956afad819fb90e983b8cb8e15e201a5a002a02f570d621b9d | 136316 | identical |
| `/Game/Ninja/Animation/Jutsu/A_Summon_ThumbBite` | core | working tree | 84d4fcd2e416130622bc138d8ef5b32b3953f8df9cda19df5d0c8f86c8d555ad | 94266 | identical |
| `/Game/Ninja/Animation/Loco/AN_FootPlant` | feature_only | working tree | 27569e7236151734c01d522a9f34605cc1b11f85e3bbf2fdbe9db3ed840b6a40 | 3815 | identical |
| `/Game/Ninja/Animation/Loco/A_Loco_Evade_Bwd_Start` | feature_only | working tree | b45fc646b6ec2deb0c6b14d0f817fe2db25df5b325d96c93a03bdaf3ba029166 | 266560 | identical |
| `/Game/Ninja/Animation/Loco/A_Loco_Evade_Fwd_Start` | feature_only | working tree | d7c3d6763b56f884f89b1bd30b324b1dfa4ec736744f1bffe26f576d01b234c7 | 372391 | identical |
| `/Game/Ninja/Animation/Loco/A_NinjaRun_InPlace` | core | working tree | 2897155d50203b8dd5846c2c9475dff942a5d3c066d6d3fba2aea928f0a0cd6d | 252242 | identical |
| `/Game/Ninja/Animation/Loco/A_NinjaSprint_InPlace` | core | working tree | ab6369d6071b98f5d0eae4f2a2021cf8e6d01fa4e49aa86d8cef8dba88e8274e | 249549 | identical |
| `/Game/Ninja/Animation/Stance/A_Prone_Enter` | feature_only | working tree | bc98a6ae4b86766421cdcd7e74ab10e9fdda8ff7159f613911d838c7bf60da86 | 168606 | identical |
| `/Game/Ninja/Animation/Stance/A_Prone_Exit` | feature_only | working tree | 88a2aad0b2d3d291c5622179440829a8327b3517618d59cfeeb2898ad1d688e5 | 168645 | identical |
| `/Game/Ninja/Animation/Stance/A_Prone_Idle` | feature_only | working tree | eac38e3ecf0babb7d281928ae0899282a4cec40209287cab12539fc1927d8648 | 133552 | identical |
| `/Game/Ninja/Audio/SFX_Chidori` | core | working tree | 67ed64765c7d56d6ed335011509999f4bc0a3624b4f23ad069172f4be6904610 | 520866 | identical |
| `/Game/Ninja/Audio/SFX_FireballImpact` | core | working tree | 69194aba9dd2b0c664aad3c3ee08c09d54eeff80b4dda44ce4c6e5768364e32c | 120402 | identical |
| `/Game/Ninja/Audio/SFX_FireballLaunch` | core | working tree | 4cf816419f97eafaa69663dfa0fd175f5ddb3d53ea7bd4549fa5deef7f563b0e | 150938 | identical |
| `/Game/Ninja/Audio/SFX_HandSeal` | core | working tree | e32e5fe489800a3aed8f574b17649df997336954f73f1ca5cc163f34bc3a5d0c | 30699 | identical |
| `/Game/Ninja/Audio/SFX_JutsuRelease` | core | working tree | fb74624bebab1db55c3f2a89a7c8b5aac311d55d8a86eaddf9687512a5468815 | 76072 | identical |
| `/Game/Ninja/Audio/Voice/SFX_Voice_GreatFireball` | core | working tree | 471e64cb279b3643c49a110f4cf8d34c3e27ba5e971a363854a64fc60939ebcc | 182860 | REMOVED (owner rule 2026-10-02: no jutsu voice-overs; 5b) |
| `/Game/Ninja/Audio/Voice/SFX_Voice_KageBunshin` | core | working tree | f091d6ef1d1368aef16d80d11f914bedc4d1acdab53f48534a353d90fe02b949 | 139841 | REMOVED (owner rule 2026-10-02: no jutsu voice-overs; 5b) |
| `/Game/Ninja/Blueprints/BP_NinjaGasp` | core | 43fd6ce LFS | 017e4018029f60d3c8099a0f23df67b7d97538432f79ea68f0d42b49aa15542b | 1329521 | modified: 480ec9558a74dae424b5f6420e8f881cf37915fb27fd5d5813222c45f4918927 |
| `/Game/Ninja/Blueprints/BP_NinjaVisual` | core | 43fd6ce LFS | 5ea028e27eda24a366efd898d40ebb09b08ff23d0b12bd5d6fdd823a3d5a2f95 | 58969 | identical |
| `/Game/Ninja/Character/ABP_MH_NinjaBody` | core | working tree | 27c6272533f897c43fef67594fa7dfd98f1dafa0f9d5079a708f6c542c45a5a0 | 45932 | identical |
| `/Game/Ninja/Character/Retarget/IK_MH_PlayerDefault` | core | working tree | 903c4b0a8a37c702632d92807e57f7a7e3ff3ba04b12ff84595438f40ab156ea | 280527 | identical |
| `/Game/Ninja/Character/Retarget/RTG_Manny_to_MH` | core | working tree | 61e05fe7a79f7db311c34955cf83fde3e5e4534692f419c9cbc930bc167d7830 | 32047 | identical |
| `/Game/Ninja/Cloak/ABP_Cloak` | core | working tree | 368702a286fa9ee20391f76527d0c8c0ed6b454dcb7e389afeeeb6d3d880a675 | 38910 | identical |
| `/Game/Ninja/Cloak/MI_BlackCloak_Leather` | core | working tree | 3e0006613f383cf31271d10e2fb353f3272d5e63586ce3fa826212ef1be0ac77 | 7961 | identical |
| `/Game/Ninja/Cloak/MI_BlackCloak_Steel` | core | working tree | 2df1bfdcd0a3b29ee304bfdf3f3f870b96b635e9e88fcd01620019110475c4e3 | 8211 | identical |
| `/Game/Ninja/Cloak/M_BlackCloak` | core | working tree | a6c389470789d28b2f1c96b44c18978ae26a24b15441f392965ca1f720d15b83 | 12535 | identical |
| `/Game/Ninja/Cloak/M_BlackCloakSolid` | core | working tree | e48e0b22feeb834f0fe7e00bb095665da98eb82b5be65a2ca4cbe7a4e3d6a51b | 10695 | identical |
| `/Game/Ninja/Cloak/SKM_BlackCloak` | core | working tree | 3c61ef6b91ccadf6411d422e1cd5d9e5a7c22f2ea2c345cbab84c2d51df708ad | 7159091 | identical |
| `/Game/Ninja/Cloak/SKM_BlackCloak_MH` | core | working tree | a59aa8408014c5b3e265af1245b4633b66d105fcbe4089432da3e793f66167c9 | 7215937 | identical |
| `/Game/Ninja/Cloak/Textures/T_BlackCloak_BaseColor` | core | working tree | fba4496e0c6d6cd82dd18140c471ca81494e5a7480e090b5055baed8047b9ea4 | 3885824 | identical |
| `/Game/Ninja/Cloak/Textures/T_BlackCloak_Normal_OpenGL` | core | working tree | c1f3c078a41aea9a36a3ebc95d9f12328ef98ef88ddb964b60673fb537bb832e | 2405862 | identical |
| `/Game/Ninja/Cloak/Textures/T_BlackCloak_Roughness` | core | working tree | 2bc46dd1ec633c8613df85fd14d06ccded0488d3bc51fc50e7bdb7e52e26f344 | 635472 | identical |
| `/Game/Ninja/FX/MI_CloneSmoke` | core | working tree | 7159279bb82b3973ec93af55b56d8f11e251b36ecd1ffce1497014b88d08e25c | 14386 | identical |
| `/Game/Ninja/FX/NS_ChidoriArcs` | core | working tree | ae239f2a2e17becbc17cc000f5d45612f9140e3da969bd6d0abd3f2ddcbc2f84 | 6128817 | identical |
| `/Game/Ninja/FX/NS_CloneSmoke` | core | working tree | 4a8c4a50d1d697233fa6c1a47063f492429d937f7dfc0bb94cbfccebb7b0d6ce | 3945738 | identical |
| `/Game/Ninja/FX/Summoning/M_SummoningSeal` | core | working tree | 5dffcc33a29ee8258342fd393e6cac283928de6adcbe1bc57b1975ad8005cea3 | 21099 | identical |
| `/Game/Ninja/FX/Summoning/T_SummoningJutsu_D` | core | working tree | 88101fd0202266d033f9fde062af91aa54efc8bcf6703b2ef2191d2632b1e5c0 | 4982204 | identical |
| `/Game/Ninja/Input/IA_Attack_Heavy` | feature_only | working tree | 492ce6ae6f814a397cc90fc9074513699310b3c3f03dd88675faf19318c04a5b | 1288 | identical |
| `/Game/Ninja/Input/IA_Attack_Light` | feature_only | working tree | 9061f7c8b6391724d22d385bf95c56aaf5c95a6579601f464f227767f53a8a85 | 1302 | identical |
| `/Game/Ninja/Input/IA_Block` | feature_only | working tree | 4bec19c2c787adab82b8453a2b407f19e91f852a40c8cfc31163ad0c5d142f72 | 1246 | identical |
| `/Game/Ninja/Input/IA_Dodge` | feature_only | working tree | f8cf655e57d8dc5fa23ec385ec6c0ebb655b86273d9a6ccbd8b764275dfd1395 | 1280 | identical |
| `/Game/Ninja/Input/IA_FreeLook` | feature_only | working tree | 2d086b817c7a59dcb8937e7b8a2e568717b6901b902727ee9a6dbcebd3a33e1d | 1306 | identical |
| `/Game/Ninja/Input/IA_Jutsu` | core | working tree | 024a7cbbb5d8ec1b41d22f82c0f2e3eb8b3ad4a38a80072f32013f1ffc37fce2 | 1155 | identical |
| `/Game/Ninja/Input/IA_Jutsu_Chidori` | core | working tree | 599fc398be55222074297d18f8afb25158196e7408fb2d3a524c7f9df8945794 | 1195 | identical |
| `/Game/Ninja/Input/IA_Jutsu_GreatFireball` | core | working tree | 0b424407164b3df3fd04fc04bcc5d97b77c67a75d80979b047409c1039c3b37f | 1225 | identical |
| `/Game/Ninja/Input/IA_Jutsu_Summoning` | core | working tree | 8c535ead6607c552f7304a967015115608c9a6a9a3bc262ad2c92cec09e3952e | 1205 | identical |
| `/Game/Ninja/Input/IA_Kunai` | feature_only | working tree | e30c4d71a21ddfc58f4b6f2edce73a51adc035cc17489b30893ad40bda4a7927 | 1265 | identical |
| `/Game/Ninja/Input/IA_KunaiAerial` | feature_only | working tree | fa0720afc61d753960277909d158267055c1d00915761ea049c4a97395ec8ee4 | 1293 | identical |
| `/Game/Ninja/Input/IA_LockOn` | feature_only | working tree | 898eb6082dbd5ae797cfa2a4a181b1e9ffed06840c874238519df8a097e6b114 | 1160 | identical |
| `/Game/Ninja/Input/IA_NinjaCrouch` | feature_only | working tree | 87a40252d81f2cadf92f94102969302134c0c19a538e945920c0f31b84a0442f | 1185 | identical |
| `/Game/Ninja/Input/IA_NinjaProne` | feature_only | working tree | e56b7e2964af9f7829515ecf3d76ac5b19d2b589b99d2c9bca0eb76e0f401284 | 1180 | identical |
| `/Game/Ninja/Input/IA_Shunshin` | feature_only | working tree | 3cc9f7751835d990f25fb8b57548690b744b75bb0f07ca3ead32b55d09edc376 | 1277 | identical |
| `/Game/Ninja/Input/IMC_NinjaGasp` | core | working tree | 8112f715eca2047e819d0c0eec952a00869ba72fd046ad64479b08f9cbb6ad19 | 11821 | modified: 685b68aae901d9119dd7ae3ab6957d89012eb89690ce9ba05c251b6a720b02bc |
| `/Game/Ninja/Jutsu/BP_ChidoriLightning` | core | working tree | 848a7cb7ce73ab3c6286c0a4a6c360f0716067827bcdb6c318b22ac05f087f19 | 28018 | identical |
| `/Game/Ninja/Jutsu/BP_GreatFireball` | core | working tree | 5607778029773ac4f3c3bd363fca5622ab37c67f169dbcdbbe8cd215514150b9 | 32478 | identical |
| `/Game/Ninja/Jutsu/BP_SummoningSeal` | core | working tree | bc5a9a7cbe50d6dca61c53eb2eebc6942603dacd993834b7b34db40ecce5e9bf | 24497 | identical |
| `/Game/Ninja/Jutsu/DA_Jutsu_Chidori` | core | working tree | 2a6bfce61dfd534908c84f2f78ecb3ca70d4425d39d39ac1d7968dc81931c7ee | 3200 | identical |
| `/Game/Ninja/Jutsu/DA_Jutsu_GreatFireball` | core | working tree | 06ab26ae7a1fd43c7fe754b549dae43afb03c996ac8e333ecda3902b5633e9c7 | 3621 | modified: 318bb1c7f842390bcbf83cc4afad965ae2ccfdd2ba093e9a4725d621bfbe3a3a |
| `/Game/Ninja/Jutsu/DA_Jutsu_ShadowClone` | core | working tree | 1208c9217328ba6b0083c07342e05df8fa2316f1a1866af98c232fb5e589f7cc | 2865 | modified: 22d1736b8edeb28c93adbb9eea05c776b00b42d7b4b202e5e21ef7afc4163a95 |
| `/Game/Ninja/Jutsu/DA_Jutsu_Summoning` | core | working tree | befbc7a629396846b57420942131ac164f7f06b7d8a96f2cd222a84b18b69d20 | 3836 | identical |
