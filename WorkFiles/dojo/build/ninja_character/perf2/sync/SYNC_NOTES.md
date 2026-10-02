# perf2 / SYNC: DojoLab synced to armory_hall revision 5 (2026-10-02)

Revision 5 (armory chat, owner asked): entry mat removed (SM_AK_EntryMat retired, id AKI_0335 retired), upper side
windows backlit by SM_AK_Window_Paper_35_W/_E x10 (AKI_0618..0627, M_AK_HWinPaperW/E, T_AK_HWinPaper_BC), the
ArmoryLab per-level light values (atten_cm / channels, which DojoLab does not read), every other ArmoryKit FBX
re-exported with the same geometry. Machine-readable numbers: `RESULTS.json`.

## Steps (SYNC.md 3.1 + 3.3)
1. `check_sync.py --side dojo` at the start: **exit 2** (synced rev 3, needs 5; DojoLab copies of T_AK_HWinPaper_BC,
   M_AK_HWinPaperE/W and the 7 M_AK_* masters behind). `check_sync_start.txt`.
2. Backup before any write: `start_backup/` (L_Dojo.umap 3cd28a0e..., Content/ArmoryKit, ArmoryHall, NinjaPack,
   armory_sync jsons, manifest.json, showcase verify.json, BUILD_NOTES.md, the DojoNinjaPort lock; SHA256SUMS.txt,
   316 files).
3. C++ module current: `Build.bat DojoLabEditor Win64 Development` -> "Target is up to date", 0 actions;
   UnrealEditor-DojoLab.dll sha256 18065c72... unchanged, BuildId 55116800 = the engine's. `logs/ubt_build.log`.
4. `Scripts/dojo/unreal/run_armory_sync.sh` (no edit needed for the C++ module; the commandlet loaded the DojoLab
   module from DojoLabEditor.target):
   - files: 198 packages in the closure, 10 copied (the 7 masters, M_AK_HWinPaperE/W, T_AK_HWinPaper_BC), 188
     unchanged, 0 missing, 0 drift vs the manifest.
   - Unreal (115 s): 65 / 65 SM_AK_* re-imported (every FBX sha changed with the re-export; 0 drift vs the manifest),
     incl. the 2 new window-paper meshes (Nanite, 1 UCX hull each); **470 / 470 instances placed** (461 - entry mat + 10
     window paper), bounds max 0.070 cm, transform error 0.0 cm, 0 gate failures, 0 envelope violations, 0 lights
     outside, 114 design + 10 backer + 1 level light, 12 shadowed <= budget 14, 83 / 83 shell ids, 22 / 22 shell faces on
     channel 1, 6 / 6 parked-leaf paper, 10 / 10 backer paper. L_Dojo actors tagged DJ_ArmoryHall 593 -> 602
     (destroyed and re-placed, the plan changed). New DojoLab-only children (the existing emissive rule, no new look
     value): MI_DJA_AK_HWinPaperW (38.5 -> 2.615), MI_DJA_AK_HWinPaperE (30.66 -> 2.082). 0 errors; warnings = FBX
     tangent notices, GetSectionFromStaticMesh (fallback-box measurement), LevelBlock construction script (all known).
5. `check_sync.py --side dojo`: **exit 0** (PASS, synced; rev 5 needs 5).
6. Record (SYNC.md 3.3): `lock.py claim ArmoryHall` -> `bump_manifest.py --record-sync DojoLab` -> `release`. Manifest
   diff against the backup: exactly `last_synced.DojoLab` 4 -> 5. check_sync again exit 0.
7. `run_showcase_unreal.sh verify` (fresh commandlet, 36 s): **9 / 9 gates PASS** incl. 5_gameplay (GM_DojoNinja ->
   BP_NinjaGasp, GM_Dojo -> SandboxCharacter_CMC) and 9_armory_hall (602 actors, 0 instances wrong / missing, 0 items
   / lights missing, PPV bounded, sync rev 5 = manifest rev 5). Level 2,556 -> 2,565 actors (+9 = +10 paper - 1 mat).
   Copy in `sc_verify/`; the canonical `WorkFiles/dojo/build/unreal/showcase/verify.json` is this run's.
8. Interior walk routes, by the pawn itself in -game (`run_ninja_playtest.ps1`, suite routes, 40 routes: every ARM_*,
   HALL_*, interior CONTROL and the centre-door route): **ninja 40 / 40 as expected (31 / 31 reached, 9 / 9 blocked)**,
   SandboxCharacter_CMC 40 / 40, 0 differences; 0 errors / ensures in both logs. The centre-door route now ends with the
   feet at 0.522 m (0.603 before: the pawn stood on the 8 cm entry mat, now removed). End points equal to the play-test
   stage within 3 cm, except ARM_deck_strip (the walker fix changed it) and CONTROL_dais_through_the_north_wall (held,
   stopped 21 cm further along the blocking wall). Max deviation 0.43 m on both pawns: the
   play-test stage's walker fix (waypoint-order projection, switching segments 0.45 m before a vertex) measures corner
   cuts against the current segment; GASP before the fix 0.16, after 0.43 on the same routes; not a level change.

## Not changed / open
- No look value changed; no Blender, shared file (apart from the record line), ArmoryLab, DemoGame_1 or GASP file
  touched. Nothing committed or pushed.
- The window paper casts shadows in L_Dojo (dj_armory_look.NO_SHADOW_PIECES is empty); the armory chat's change line
  says "no shadow" for ArmoryLab. Not changed here (no look changes in this run); owner / look stage to decide.
- SM_AK_EntryMat.uasset stays in DojoLab/Content/ArmoryKit/Meshes, unreferenced by L_Dojo (a retired name is never
  reused; delete only if the owner wants).
- Lock DojoNinjaPort NOT released: the port still has open items (16.7 ms p95 target / ninja perf levers, D1 hair
  colour, R4) and this perf2 round continues.
