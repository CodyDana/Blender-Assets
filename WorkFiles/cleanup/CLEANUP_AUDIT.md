# Blender_Projects cleanup audit (read-only)

Date: 2026-09-28, just after midnight. Nothing was deleted, moved or edited. The only files written are this report and `cleanup_audit.json` in the same folder.

## 1. The short version

The project folder holds **115.7 GB** (107.7 GiB, the "108 GB" Windows shows) in 53,632 files. Each file is counted once, in the most specific group that fits it.

| Group | Size | What it means |
|---|---|---|
| **A. Safe to delete** | **78.7 GB** | Scratch from finished jobs that can be regenerated. None of it is the only copy of anything final, and no other chat is using it. |
| **B. Keep** | **12.3 GB** | Scripts, references, final .blend files, final exports, renders, reports, verified backups, locks, and work other chats are doing right now. |
| **C. Ask the user** | **24.7 GB** | Older backups, failed experiments you might still want, CharacterLab, JinMuWon, and things that belong to other chats or to Codex. |

**Where the space goes:** the smoke bomb scratch alone is **61 GB**. It holds about 330 `.pkl` simulation dumps of 200-630 MB each, plus float arrays. The smoke bomb was accepted on 09-25 and has a verified backup. Group A items A01-A10 cover it.

**Drive C:** 1,999 GB total, **1,028 GB free**. The Recycle Bin on C: can hold up to about **95 GiB** (97,394 MB). It is **empty** right now, and "delete immediately" is off.

## 2. Recycle Bin caveat (please read before deleting)

- **No single A item is too big for this drive's Recycle Bin.** The largest is 15.1 GB, and the bin limit is about 95 GiB. Even all of group A at once (about 73 GiB) fits, as long as the bin stays empty.
- **The Recycle Bin frees no space until you empty it.** Moving 78 GB to the bin leaves the drive exactly as full as before.
- The items marked **LARGE** below (A01-A06, A09, A11) are several GB each and together take up most of the bin. Delete them one at a time. Check that nothing complains for a day, then empty the bin.
- Deleting from a terminal (`rm`, `Remove-Item`, `del`), or from an agent, **skips the Recycle Bin**. Those deletions are permanent. Do the deleting yourself, in File Explorer.
- Folders with thousands of small files (A09 has 3,348 and A16 has 1,562) can take several minutes to recycle. That is normal.
- **Before deleting A16** (the Unreal check folders), close every Unreal editor.

## 3. Group A - safe to delete (78.7 GB)

These are sorted by size. "Newest" is the newest file inside, which shows that nothing has touched these since the job finished. Every path is under `C:\Users\Cody\Desktop\Blender_Projects\`.

| # | Folder / files | Size | Newest | Why it can go | Bin |
|---|---|---|---|---|---|
| A01 | `WorkFiles\smokebomb\rewind\build2` | 15.09 GB | 09-25 05:09 | Smoke bomb attempt-2 round-2 dev builds (.pkl ball caches, iteration renders). The smoke bomb was accepted on 09-25. The shipped files are in Assets/Exports and in `Backups\SmokeBomb_2026-09-21`. | LARGE |
| A02 | `WorkFiles\smokebomb\rewind\wind` | 12.64 GB | 09-22 11:39 | Winding design scratch: 40+ `wd_out\*.pkl` dumps of 200-630 MB each. The final winding is frozen in `Scripts\props\props_lib\smokebomb_wind_fit.py`. (If you want the generator scripts, keep `wind\wd_tools\*.py`, a few hundred KB.) | LARGE |
| A03 | `WorkFiles\smokebomb\rewind\build4` | 6.97 GB | 09-25 18:47 | Round-3 dev builds (.pkl ball variants). Finished job. | LARGE |
| A04 | `WorkFiles\smokebomb\rewind\build5` | 6.57 GB | 09-25 22:46 | Round-4/final dev builds. The shipped result is live and in the backup. | LARGE |
| A05 | `WorkFiles\smokebomb\final_pass` | 5.84 GB | 09-25 22:46 | Final-pass parameter sweeps (g_* variants). (Keep `final_pass\tools\*.py` if you want them.) | LARGE |
| A06 | `WorkFiles\smokebomb\rewind\tape` | 4.29 GB | 09-22 10:20 | Tape/cloth design scratch. | LARGE |
| A07 | `WorkFiles\smokebomb\rewind\` build3, measure_r1/r2/r2b/r3, judge_cloth_rw4, blind_r1/r2/r2_prev_build_0526/r3 | 2.53 GB | 09-25 21:05 | Attempt-2 measure, judge and dev folders. | |
| A08 | `WorkFiles\smokebomb\rewind\build` | 1.35 GB | 09-25 22:45 | Build output folder (`rewind\build\ship`). `build_smoke_bomb.py` recreates it on the next build. | |
| A09 | `WorkFiles\smokebomb\` build_r2, build_dev, build_r3, build_r4, build, adversary_r1/r2/r3, judge_cloth_r3, blind_judge | 6.00 GB | 09-21 19:51 | Smoke bomb **attempt 1**, which failed and was replaced by attempt 2. Its end state is kept in `round3_2026-09-21` (see C14). | LARGE |
| A10 | `WorkFiles\smokebomb\UnrealCheck*`, `UnrealVerify*` (8 folders) | 0.04 GB | 09-25 22:45 | Unreal check logs. Re-runnable. | |
| A11 | `WorkFiles\blackhat\build_dev` | 6.41 GB | 09-26 02:08 | Black hat dev builds look1-8, tex2048/4096, b3-b14. Each holds 121-486 MB `.npz` texture caches. The black hat is CLOSED, and `Backups\BlackHat_2026-09-25` matches the live files. | LARGE |
| A12 | `WorkFiles\blackhat\surface_pass` | 1.06 GB | 09-26 03:07 | Surface-pass iteration renders d01-d32. | |
| A13 | `WorkFiles\flashbang\r2\dev`, `dev2`, `dev3`, `dev4` | 1.50 GB | 09-27 22:49 | Flashbang round-2 dev builds (3 x 419 MB `bakes_lod0.npz`). Round 2 finished and shipped at 23:29. **Keep** `r2\r1_state`, `r2\compare`, `r2\look*` and `r2\tools`, because the flashbang scripts read or cite them. | |
| A14 | `Backups\Materials_2026-09-26\WorkFiles_materials\look_verify` | 1.49 GB | 09-26 06:54 | Exact copy (same 754 names and sizes) of A15. | |
| A15 | `WorkFiles\materials\look_verify` | 1.49 GB | 09-26 06:54 | Materials look-verify captures from 09-26 (float .npy/.exr). The materials have been rebuilt and re-verified several times since. To keep one copy as evidence, delete only A14. | |
| A16 | Inside `WorkFiles\shuriken\UnrealShuriken\Content\`: `PropsCheck`, `SwordCheck`, `IVSnowFlower`, `ShurikenCheck3/4/6/7/8/9`, `ShurikenVerifyIndep`, `KunaiPlainVerify12`, `SpikeVerify10`, `HookedCrossVerify11`, `FanCheck`, `FanIndepVerify`, `PBVerify2/4/6/R2`, `PBExact_0926`; plus `UnrealShuriken\Saved\Crashes` | 3.02 GB | 09-27 23:20 | One import-check folder per verification run: 19 smoke bomb, 12 paper bomb, 8 black hat, 9 flashbang and 10 Snow Flower runs, plus the old shuriken checks. Nothing references them, and every check can be re-run. **Close Unreal first. Do NOT touch `Content\NinjaPack`** (the shared pack materials) or the project files. Old reports that say "verified in /Game/ShurikenCheck9/..." will then point at nothing, which is fine. | |
| A17 | `Exports\SnowFlower_DesignRevision3.zip`, `SnowFlower_ReferenceRevision.zip`, `SnowFlower_Package.zip` | 0.50 GB | 09-19 | Old rev-3 zips. **SHA-256 identical** copies sit in `Backups\SnowFlower_rev3_pre_review_2026-09-26\Exports\`. If you also delete that backup (C08), these become the only copies, so decide the two together. | |
| A18 | `WorkFiles\pipeline_test\UnrealTest`, `UnrealTest_Interchange`, `UnrealReview`, `UnrealCheck`; `WorkFiles\shuriken\UnrealTest` | 0.40 GB | 09-17 | Unreal test projects from the 09-17 pipeline test (imports of the old JinMuWon). `test_pipeline.py` recreates them. | |
| A19 | `WorkFiles\kunai\blade_section\build`, `review_r1`, `review_r2`, `fix_r1` | 0.74 GB | 09-27 01:22 | Kunai blade-section prototypes and review renders. The kunai is DONE, with backup `Shuriken_after_kunai_blade_section_2026-09-26`. Keep `options\` (the sheet you picked from) and `final\`. `build_kunai_plain.py` cites `build\hero_yaw_probe_summary.json` as evidence, so keep that one JSON if you like. | |
| A20 | `.npy` / `.npz` files inside `WorkFiles\paperbomb\exact` (only those, 53 files) | 0.47 GB | 09-26 23:36 | Float caches from the finished paper bomb trace. The traced shapes live in `Scripts\props\props_lib`, and the PNGs/JSON in `exact\` stay. | |
| A21 | `.blend1` of finished assets: `Assets\` SmokeBomb, BlackHat, Fan, Flashbang, Shuriken, PaperBomb, SummoningJutsu, Kamish_Daggers, Ea_Sword; plus `.blend1` in `WorkFiles\flashbang`, `fan`, `pipeline_test`, `smokebomb` | 0.14 GB | 09-27 20:58 | A `.blend1` is Blender's automatic "previous save". The real `.blend` next to each one is newer and has a verified backup. | |
| A22 | Every `__pycache__` / `*.pyc` (2,304 files) | 0.06 GB | - | Python caches, recreated automatically. | |
| A23 | Loose files in the `WorkFiles` root: `kd_*` (August dagger analysis), `blender_mcp_*` (09-13 MCP test), `mcp_autostart.log`, `nail_*.log`, `skin_*.log` | 0.05 GB | 09-24 | Old scratch and logs. | |

**Checked before listing:** I searched `Scripts\` for any code that *reads* from these folders. The build scripts that read from WorkFiles use these paths, which are all in B and must stay:

- `shuriken\photo_study\synthesis\photo_matched_outlines_mm.json`
- `flashbang\metrology\fb_ref_srgb.npy`
- `flashbang\r2\r1_state`
- `SnowFlower\v4\sword_build\maps_report.json`, `sheath_build\maps_report.json` and `sheath_build\fit\`
- the two Snow Flower high-poly blends
- `MetaHuman\player_*\rig\bones.json` and `player_base\faces\*.json`
- `paperbomb\paused_2026-09-21\SHA256SUMS_exports.txt`
- every `regression\...\SHA256SUMS.txt`

Everything in A is referenced only in comments, as evidence.

## 4. Group B - keep (12.3 GB)

- **Scripts** (`Scripts\`, 10 MB without caches). This is the source of truth; every asset can be rebuilt from it.
- **References** (209 MB) and the root docs (`ASSET_GUIDELINES.md`, `FAB_ASSET_STUDY.md`, `CHARACTER_PIPELINE_REVIEW.md`).
- **Final source blends** in `Assets\` (Shuriken, PaperBomb, SmokeBomb, BlackHat, Fan, Flashbang, SnowFlower, SnowFlowerHeels, Dojo, Armory, and the small August ones).
- **Final exports** in `Exports\` (per-item FBX, textures, sidecars and READMEs, plus DojoKit and ArmoryKit) and **renders** in `Renders\`.
- **Verified baselines** in `Backups\`:
  - `PaperBomb_2026-09-26`
  - `SnowFlower_v4_pre_lookmatch_2026-09-27`. This is the **only copy** of the last verified Snow Flower set; 97% of its bytes exist nowhere else.
  - `Flashbang_r1_final_2026-09-27`. The only copy of flashbang round 1.
  - `Shuriken_after_kunai_blade_section_2026-09-26`
  - `SmokeBomb_2026-09-21`
  - `BlackHat_2026-09-25`
  - `Fan_2026-09-26`
  - `Materials_2026-09-26` (minus the duplicate in A14)
  - `SnowFlowerHeels_r1_2026-09-27` (the heels decision is still open)
- **WorkFiles reports, specs, regression baselines, metrology, locks and final folders.** Two Snow Flower high-poly bake sources also stay: `WorkFiles\SnowFlower\v4\SnowFlower_HighPoly_v4.blend` and `SnowFlower_Sheath_HighPoly.blend`.
- **The ShurikenValidation Unreal project** (`WorkFiles\shuriken\UnrealShuriken`, 276 MB after A16), including `Content\NinjaPack`, which every chat builds its materials into.
- **In use right now by other chats. Do not touch:**
  - `WorkFiles\dojo` (last write 23:47), `Exports\DojoKit`, `Assets\Dojo`
  - `WorkFiles\armory` (23:44), `Exports\ArmoryKit`, `Assets\Armory`
  - `WorkFiles\Characters\2B_private` (23:46, private)
  - `WorkFiles\MetaHuman\hiyuki_private` (private)
  - `WorkFiles\world`

**About the locks:** all 15 lock files in `WorkFiles\locks` name process IDs that are no longer running. Agents run short Python processes, so a lock's pid being dead does **not** mean the asset is free. I judged activity from file times instead. Keep the lock files.

## 5. Group C - questions for you (24.7 GB)

| # | Item | Size | Question |
|---|---|---|---|
| C01 | `Exports\CharacterLab` (Unreal project: MH_PlayerFemale/Default/Base, MH_Hiyuki_Private, HeelsCheck) | 1.73 GB | Keep the project. Clear its ~550 MB of caches (DerivedDataCache 267 MB, Intermediate 142 MB, Saved\Autosaves 110 MB, Saved\Crashes 31 MB) only when every Unreal editor is closed and the character/Hiyuki chats are idle. OK? |
| C02 | `WorkFiles\JinMuWon` | 5.22 GB | Is JinMuWon still needed now that you use MetaHumans? This folder holds 8 extra full copies of the 80-130 MB character blends (`customization\*\backups`, `body_review\commit_backups`, `checklist_round2\...\commit_backups`), plus the MPFB2 add-on source and a 280 MB MakeHuman `system_assets.zip`, both re-downloadable. |
| C03 | JinMuWon blends and exports: `Assets\JinMuWon*.blend(+1)`, `Assets\JinMuWon_v2\`, `Exports\JinMuWon\`, `Exports\JinMuWon_v2\` (two UnrealDemo projects), `Renders\JinMuWon*` | 2.23 GB | Keep, archive or delete? At minimum, the `.blend1` files (~470 MB) and `JinMuWon_v2\UnrealDemo\Intermediate` (125 MB) could go. |
| C04 | `Backups\JinMuWon_v2_skin_nails_2026-09-25`, `Backups\BeforeMetaHuman_20260924T185019Z` | 0.77 GB | Every file in both is byte-identical to a live file (SHA-256 checked for the big blends). Delete, or keep while JinMuWon is kept? |
| C05 | `WorkFiles\MetaHuman\player_default`, `player_female`, `player_base`, `preset_thumbnails` | 3.53 GB | Mostly diagnose/capture PNGs (2.1 GB) from the character chat. The capture folders could go, but scripts read `player_*\rig\bones.json`, `*_recipe.json` and `player_base\faces\*.json`, so those must stay. Ask the character chat? |
| C06 | `WorkFiles\SnowFlower\v4\lookmatch`, `trace_pilot` | 1.18 GB | Both Snow Flower passes FAILED the blind test. They depend on your open Snow Flower decision (restore the verified set / more views / outside sculpt). Delete once you decide? |
| C07 | Snow Flower bake caches `sword_build\bake\*.npy`, `sheath_build\bake\*.npy` | 2.47 GB | 10 x 201 MB. Regenerable by re-baking, but `sfv4_lm_gates.py` reads them. Delete with C06? |
| C08 | `Backups\SnowFlower_rev3_pre_review_2026-09-26`, `Backups\SnowFlower_v4_2026-09-26`, `WorkFiles\SnowFlower\Revision1/2` | 1.27 GB | Rev-3 is the older AI-made version, replaced by v4. SnowFlower_v4_2026-09-26 is the first v4 state. Still wanted? (See A17 about the zips.) |
| C09 | Eight older shuriken step backups (`Shuriken_pre_restyle` ... `Shuriken_after_kunai_plain`, 09-17 to 09-19), plus the loose four-point files | 0.55 GB | The current baseline is `Shuriken_after_kunai_blade_section`. Keep the history? |
| C10 | Paper bomb history before the remake: 4 backups `PaperBomb_2026-09-19/20_*`, plus `WorkFiles\paperbomb\claudeR2`, `claudeR3`, `claudeR3_shipped_backup`, `paused_2026-09-20` | 0.37 GB | The paper bomb is finished. Keep the history? (Keep `paused_2026-09-21` in any case; two build scripts read its SHA256SUMS file.) |
| C11 | Old loose August backups: SummoningJutsu, Kamish_Daggers, Ea_Sword, Ninja, `Untitled.blend`, blender_mcp_setup, Docs_before_* | 0.04 GB | Tiny. Keep or delete? |
| C12 | Black cloak (own chat, active 09-27): `WorkFiles\BlackCloak_Review` (incl. the 924 MB CloakReview Unreal project with 366 MB of DDC/Intermediate cache), `BlackCloak_MH_v2`, `BlackCloak_MH`, `BlackCloak`, `garment_pipeline`, `Assets\BlackCloak.blend(+1)`, `Assets\Garments`, `Exports\BlackCloak` + `BlackCloak_Package.zip`, `Exports\Garments`, `Backups\BlackCloak_*` | 3.30 GB | Owned by the black cloak chat. Ask it first. `Exports\BlackCloak_Package.zip` is identical to the copy in `Backups\BlackCloak_original_2026-09-26`. |
| C13 | Black nunchucks (made by **Codex**): `Assets\BlackNunchucks.blend(+1)`, `Exports\BlackNunchucks` + a 250 MB package zip, `WorkFiles\BlackNunchucks` (135 MB qa_deps), `Backups\BlackNunchucks_PreRecolor` | 0.95 GB | Not ours. Keep it, or ask Codex? |
| C14 | Failed smoke bomb snapshots: `smokebomb\round3_2026-09-21`, `rewind\paused_2026-09-25`, `rewind\wip_modules_2026-09-21` | 0.12 GB | Only history of the failed states. Keep or delete? |
| C15 | `WorkFiles\shuriken\photo_study` | 0.77 GB | Mostly .npy caches from the 09-18 photo study. `synthesis\` and `PHOTO_MEASUREMENT.md` **must stay** (the hooked-cross build reads them). OK to delete the rest (`juji`, `manji`, `happo`, `roppo`, `senban`, ~0.75 GB)? |
| C16 | `UnrealShuriken\Content\SFMatTrial` | 0.07 GB | A Snow Flower material trial. Still wanted? |
| C17 | Snow Flower `.blend1` files (`Assets\SnowFlower`, `WorkFiles\SnowFlower\v4`) | 0.11 GB | Delete after the Snow Flower decision? |

**Also to decide:**

- **Stray folder `C:\WorkFiles`** (outside the project; 66 PNGs, 46 MB). It holds:
  - `armory\build\renders\fix1` and `look2` (15 MB, 09-27 01:17-02:24)
  - `dojo\build\ground` and `dojo\build\props\training` renders (29 MB, 09-27 18:19-18:55)
  - `fan\UnrealCheck\dev1\ue_fold_sheet.png` (2.6 MB, 09-26)

  Scripts wrote to a relative `WorkFiles` path while the current folder was `C:\`. The armory and dojo chats (both active) and the finished fan job made it, so it is not ours to judge. Tell those chats, then move it into the project or delete it. The armory/dojo scripts that did this may do it again.
- **Private content** (see section 7): 2B from Sketchfab/DAZ, and Hiyuki reference images of a game character. Do you want these in the GitHub repo at all?

## 6. Duplicates found (SHA-256, files over 50 MB)

These were compared by size first, then hashed. The smoke bomb/black hat/flashbang scratch was not hashed because it is all in A anyway.

- `Exports\SnowFlower_DesignRevision3.zip`, `SnowFlower_ReferenceRevision.zip`, `SnowFlower_Package.zip` = copies in `Backups\SnowFlower_rev3_pre_review_2026-09-26\Exports\` (A17).
- `Exports\BlackCloak_Package.zip` = `Backups\BlackCloak_original_2026-09-26\Exports\BlackCloak_Package.zip` (C12).
- JinMuWon: `JinMuWon_v2.blend`, `JinMuWon_Human.blend` and `JinMuWon_Human_Review.blend` each exist 2-3 times across Assets, the two JinMuWon backups and the customization/commit backups. `WorkFiles\MetaHuman\player_base\src_Human_copy.blend` is identical to `Assets\JinMuWon_v2\JinMuWon_Human.blend` (C02-C05).
- `WorkFiles\SnowFlower\v4\lookmatch\r1_snapshot_interrupted\*HighPoly*.blend` = the live high-poly blends (C06).
- The two Snow Flower v4 backups share the same high-poly blends (C08 vs B).
- `MH_PlayerDefault\...\T_Body_SRMF_VT.uasset` exists in both CharacterLab and CloakReview (copied content).
- Backup contents compared by name and size against live files:
  - `Materials_2026-09-26`, `JinMuWon_v2_skin_nails`, `BeforeMetaHuman`, `BlackCloak_original`, `SmokeBomb_2026-09-21`, `BlackHat_2026-09-25`, `Fan_2026-09-26`, `PaperBomb_2026-09-26`, `Shuriken_after_kunai_blade_section`: about 100% also live. They are safety copies, not the only copy.
  - `SnowFlower_v4_pre_lookmatch` (2.5% live), `Flashbang_r1_final` (43%), `SnowFlowerHeels_r1` (30%), `BlackNunchucks_PreRecolor` (0%): these hold unique content.

## 7. GitHub repo estimate (after deleting group A)

Sizes are before git compression; PNG/blend barely compress.

| Part | Normal git | Git LFS |
|---|---|---|
| Scripts (no `__pycache__`) | 0.01 GB | |
| References (images + docs) | 0.21 GB | |
| Root docs, READMEs, sidecars in Exports | 0.01 GB | |
| WorkFiles reports/specs/tools (`.md`, `.py`, `.txt`, `.svg`, `.json` under 2 MB) | 0.19 GB | |
| Assets `.blend` (no `.blend1`), excluding JinMuWon | | 0.35 GB |
| Exports (FBX, textures, READMEs), excluding CharacterLab/JinMuWon and Unreal caches | | 1.64 GB (1.31 GB without the two package zips) |
| Renders (excluding JinMuWon) | | 0.76 GB |
| Textures folder | | 0.10 GB |
| Snow Flower high-poly bake sources (WorkFiles) | | 0.21 GB |
| **Core total** | **~0.42 GB** | **~3.1 GB** (~2.7 GB without zips) |
| + CharacterLab Content (no caches) | | +1.18 GB, making ~4.2 GB |
| + JinMuWon (blends, exports, UnrealDemo content, renders) | | +1.63 GB, making ~4.7 GB |
| + both | | ~5.9 GB |

Not in the repo:

- `Backups\`: 4.4 GB after A. Git history becomes your backup from the first commit on. The two unique baselines, `SnowFlower_v4_pre_lookmatch` (0.34 GB) and `Flashbang_r1_final` (0.04 GB), can be committed once under an `archive/` folder (+0.38 GB LFS) or copied to an external drive.
- The rest of the WorkFiles scratch.
- Private content (~1.1 GB).

**LFS warnings:**

- Free LFS storage counts **every version** you push. Re-committing a 130 MB character blend 10 times uses 1.3 GB.
- Starting at ~3 GB leaves ~7 GB of headroom. Commit big blends when they reach a milestone, not after every small change.
- LFS downloads also have a monthly allowance; check GitHub's billing page.
- Seven files are over 100 MB (the JinMuWon blends and uassets, MH_PlayerDefault/Female, and the BlackNunchucks zip). They can only go in through LFS, never plain git.

**Private / licensed content:** consider excluding it even from a private repo.

- `References\Characters\2B_kimono_private` and `WorkFiles\Characters\2B_private` come from a Sketchfab/DAZ model. Its license may not allow re-uploading.
- The Hiyuki reference images are of a commercial game character, and `MH_Hiyuki_Private` is marked DO NOT SHIP.
- MetaHuman assets fall under Epic's license. They are fine in a private repo tied to your UE project, but must never be public.

### Proposed `.gitignore` (text only; not created in the project)

```gitignore
# --- Blender / Python ---
*.blend1
*.blend2
__pycache__/
*.pyc

# --- Unreal caches (every project) ---
**/DerivedDataCache/
**/Intermediate/
**/Saved/
**/Binaries/
.vs/
*.sln

# --- Local only ---
Backups/
*.log
*.dmp
*.bak

# --- WorkFiles: keep text (reports, specs, tools, small json), drop heavy scratch ---
WorkFiles/**/*.npy
WorkFiles/**/*.npz
WorkFiles/**/*.pkl
WorkFiles/**/*.exr
WorkFiles/**/*.png
WorkFiles/**/*.jpg
WorkFiles/**/*.blend
WorkFiles/**/*.fbx
WorkFiles/**/*.obj
WorkFiles/**/*.glb
WorkFiles/**/*.uasset
WorkFiles/**/*.umap
WorkFiles/**/*.zip
WorkFiles/shuriken/UnrealShuriken/
WorkFiles/BlackCloak_Review/unreal/
# build inputs that must stay
!WorkFiles/SnowFlower/v4/SnowFlower_HighPoly_v4.blend
!WorkFiles/SnowFlower/v4/SnowFlower_Sheath_HighPoly.blend
!WorkFiles/flashbang/metrology/fb_ref_srgb.npy

# --- Package zips (rebuildable deliverables) ---
Exports/*.zip

# --- Private / licensed: never upload ---
WorkFiles/Characters/2B_private/
References/Characters/2B_kimono_private/
WorkFiles/MetaHuman/hiyuki_private/
References/Characters/Hiyuki_private/
Exports/CharacterLab/Unreal/Content/Characters/MetaHumans/MH_Hiyuki_Private*
```

(Add `Exports/CharacterLab/` and/or `*JinMuWon*` lines if you decide to leave those out.)

### Proposed `.gitattributes` (text only; not created in the project)

```gitattributes
# Big binaries go to Git LFS
*.blend   filter=lfs diff=lfs merge=lfs -text
*.fbx     filter=lfs diff=lfs merge=lfs -text
*.glb     filter=lfs diff=lfs merge=lfs -text
*.obj     filter=lfs diff=lfs merge=lfs -text
*.png     filter=lfs diff=lfs merge=lfs -text
*.jpg     filter=lfs diff=lfs merge=lfs -text
*.jpeg    filter=lfs diff=lfs merge=lfs -text
*.tga     filter=lfs diff=lfs merge=lfs -text
*.exr     filter=lfs diff=lfs merge=lfs -text
*.psd     filter=lfs diff=lfs merge=lfs -text
*.webp    filter=lfs diff=lfs merge=lfs -text
*.uasset  filter=lfs diff=lfs merge=lfs -text
*.umap    filter=lfs diff=lfs merge=lfs -text
*.mp4     filter=lfs diff=lfs merge=lfs -text
*.ttf     filter=lfs diff=lfs merge=lfs -text
*.otf     filter=lfs diff=lfs merge=lfs -text
*.npy     filter=lfs diff=lfs merge=lfs -text
*.dna     filter=lfs diff=lfs merge=lfs -text
*.zip     filter=lfs diff=lfs merge=lfs -text

# References stay in normal git (small images, you asked for plain git here)
References/** !filter !diff !merge !text

# Text files: consistent line endings
*.py    text eol=lf
*.md    text
*.json  text
*.sh    text eol=lf
*.ps1   text eol=crlf
*.uproject text
```

## 8. Suggested order

1. Delete A01-A12 (the smoke bomb and black hat scratch, ~74 GB) in Explorer, one folder at a time.
2. With Unreal closed, delete A16 inside ShurikenValidation. Leave NinjaPack alone.
3. Delete the rest of A (A13-A15, A17-A23).
4. Wait a day, then empty the Recycle Bin. That frees about 79 GB.
5. Answer the C questions. The biggest are JinMuWon (C02-C04, 8.2 GB), MetaHuman captures (C05, 3.5 GB), Snow Flower (C06-C08, 4.9 GB) and the black cloak (C12, 3.3 GB, ask that chat).
6. Then set up the repo with the files in section 7.

## 9. How this was measured

- One read-only pass listed every file with its size and time.
- Sizes were totalled per folder, per file type, and per rule. Each file sits in the most specific rule that matches it.
- Same-size files over 50 MB were SHA-256 hashed, except the A scratch.
- Backups were compared with live files by name and size.
- `Scripts\` was searched for code that reads WorkFiles paths.
- Lock pids were checked with the process list.
- The Recycle Bin limit was read from the registry, and its current contents from the shell.

Full per-item numbers (files, newest time, text size inside) are in `cleanup_audit.json`.
