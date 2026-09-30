# verify_r9 build notes

## 2026-09-30 - INDEPENDENT VERIFIER, ROUND 9 - RESULT: PASS (gates 1-4); look reported with misses

House rules kept: headless Blender only, no MCP, one Unreal process at a time (none left running), read-only on DojoLab
(L_Dojo.umap md5 6598865e... before and after), outputs only in `verify_r9/`, nothing committed.

**Processes at the start (14:12):** no blender.exe, no UnrealEditor*.exe; only the two mcp-for-blender.exe servers
(not touched). The stopped run's dj_sc_level.py commandlet had already exited. Other chats: the stone-kit chat wrote
`build/stonekit/` up to 14:07; the armory chat wrote ArmoryLab 13:01-13:03. Neither was touched.

**What was verified:** the live level is the round-9 RESTORE of s1 (it4 look, 11:00), not the stopped run's it3 state.
The stills judged here are the ones named by the stage: `unreal/round9/s1_work/it3/`. The restored level's own stills
(`restore_s1/r9s1/`) differ from it3 by 0.9-2.0 mean |d| per camera, which is the repeat-capture noise floor.

**Reused:** the verify_r8 scripts (copied as `v9_*`), with these changes:
- the alley lattice shifted;
- the arc grid, headings and speeds changed;
- the perf configs set to the configured screen percentage;
- the CSV picked from the guard log;
- the look script extended to it3 and the restored level.

### 1. Functional gates: PASS
- **FBX audit:** 253 pieces, 0 errors, UCX valid on all; 0 pieces differ from verify_r8.
- **Blender:** walk, climb and all six roof walks PASS; clearance and ground holes show 0 leaf diffs against
  verify_r8 in 11 JSONs.
- **UE verify:** 14 / 14 gates.
  - Against verify_r8, the only differences are lighting values in 7_env.
  - Meshes, instances, transforms, collision, decals (86), TRV (24), GASP trace (23 / 23), in-engine walk (47), the
    alley ring and the 1v1 group (14) are identical.
- **Emblem:** pixel-identical; the JSON is byte-identical to r8.
- **Own alley attempts:**
  - flood: 0 target cells at r 30 and r 35;
  - mantles: 0 leaks out of 1,257;
  - BR mode opens all 9 targets.
- **Arcs:** the first pass logged 1,050 entries. They were my own artefact:
  - all of them came from 4 launch points at X 10.4, Y 34.5-35.4;
  - those points sit in the 7 cm seam between my own target boxes (pocket_W to X 10.38, the strip from X 10.45);
  - the seam is inside the sealed rear, and the flood never reaches it (northmost Y 33.63 at X 10-12).
- **Arcs rerun with the seam closed** (`v9_ue_alley_seam.py`): 0 / 793,260 at r 30 and 0 / 783,540 at r 35.

### 2. UDS: PASS
- One UDS actor and one of each active environment component.
- Exposure owner: the PPV PostProcess_Dojo only (manual, bias 1.2). UDS Apply Exposure is False.
- Time 1730, locked for 253 s in -game.
- Sun at 9.08 deg elevation, azimuth 187.29 deg from +X, so from the west.

### 3. Plugins, Nanite Foliage, other projects: PASS, with a documentation gap
- The ProceduralVegetationEditor (Megaplants) and DynamicWind plugins mount.
- `r.Nanite.Foliage` and `ProjectEnabled` are True.
- L_Dojo loads with 0 errors, and the warning set is the same as r8's.
- 0 writes after 08:00 in DemoGame_1, DemoGame_1_private2b and GameAnimationSample.
- **Documentation gap:** no BUILD_NOTES section records the 08:24 plugin enable or the 08:27 perf ini changes, and
  TREE_BUILDING_STUDY.md 5.1 still says DojoLab does not have PVE.

### 4. Performance: PASS
- `perf_summary.md` has the tables. The run used scalability 3, no vsync, `-game -dx12` offscreen.
- The configured screen percentage was checked from the TSR input size: 1920x1080 at both 1080p and 1440p (75 %).
- GPUTime p95 (target 16.7 ms):
  - 1080p: 7.33-7.92 ms;
  - 1440p configured: 7.88-8.48 ms;
  - 1440p at 100 %: 10.33-11.61 ms.
- FrameTime p95 is 12.55 ms or less everywhere.
- Top GPU costs: TSR 1.2-1.6 ms (2.3 at 100 %), shadow depths 0.68-0.77, shadow projection 0.41-0.68, Nanite 0.8-1.0.
- Volumetric fog fell from 1.0-1.6 ms in r8 to 0.24-0.40 ms, so the 16 / 64 grid is live.
- **Finding:** on this PC, `DojoLab/Saved/Config/WindowsEditor/GameUserSettings.ini` holds `sg.ResolutionQuality=100`.
  The -game startup reads r.ScreenPercentage 100 (manual), so the display-based curve only applies on a clean install
  or after the owner resets that user file. The captures run with 100 % as well.

### 5. Look (CAM_Ref2Match, matched framing, it3 = restored within noise)
| | ref 2 | r9 |
|---|---|---|
| under luma 40 | 13.7 % | 11.7 % |
| mean | 107.9 | 111.2 |
| p90 | 171 | 160 |
| top sky | (171, 147, 150) L152 | (146, 109, 105) L117 |
| horizon | (210, 157, 131) s0.38 | (193, 145, 121) s0.37 |
| sand near | (174, 140, 117) R/B 1.48 | (162, 122, 92) R/B 1.75 |
| sand near high-pass | 15.8 | 8.9 |
| sand far high-pass | 6.9 | 3.2 |
| veranda timber | (75, 49, 35) L53 | (52, 26, 14) L30 |
| lantern glow | s0.49 | s0.69 |
| roof, matched view | lit R/B 1.02 | lit R/B 1.00-1.06, a match |

- The roof in CU_HallUpperRoof reads sage: lit (138, 140, 128) with G >= R.
- Framing: our hall is 1.28x wider, the ridge sits 119 px lower, and there are no gate posts, no foreground step and
  no slab path.
- Grey-box SM_DGB_Tree cylinders show in CAM_EastYard, CAM_GateFromStreet and CAM_Overview.
- CAM_Drum has 27 % near-black pixels (300 / 1980 black tiles) and 63.5 % under luma 40.
