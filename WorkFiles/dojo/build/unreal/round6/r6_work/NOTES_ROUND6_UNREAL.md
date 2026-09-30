
## 2026-09-30 - ROUND 6: DOJOLAB IMPORT + FIXES (the 1v1 rear seal, the far background, gravel, shade, drum bulb, slate tiles, decals sync)

User: "yes start first round. keep emblem for now". The emblem plaques are untouched (gate street side + both hall side
gables); no vegetation (trees stay grey-box). Headless Blender only (no MCP), no DojoLab editor open at any step (the
runners' guard), one Unreal process at a time and none left running. DemoGame_1*, the GASP sample and ArmoryLab were not
touched. Nothing committed. Lock DojoKit refreshed and still held (claude).
- **Folders:** `unreal/round6/r6_work/`:
  - `start_backup/`: every showcase and Unreal script, layout_showcase.json, decals.json, L_Dojo.umap and
    DojoShowcase.blend as they were;
  - `it1`, `it2`: the iterations;
  - `probe_a..c`: the probes;
  - `measure_r6.py`, `make_sheet_r6.py`;
  - `checks/run_checks_r6.sh`;
  - `checks/ue/`: the in-engine alley checks.

  `unreal/round6/r6/` holds:
  - the FINAL 42 stills and `SHOWCASE_SHEET_R6.png`;
  - `measure_r6.json`;
  - `json/`: import, materials, level, verify, perf, capture;
  - `json/checks/`: every Blender check and the UE alley checks.

### Commands
```
blender -b --factory-startup --python Scripts/dojo/showcase/compose_showcase.py      (253 pieces, 1110 instances, 86 decals)
bash WorkFiles/dojo/build/unreal/round6/r6_work/checks/run_checks_r6.sh
DJ_CAPTURE_DIR=<abs>/unreal/round6/r6 bash Scripts/dojo/unreal/run_showcase_unreal.sh prep import materials level verify perf capture
bash WorkFiles/dojo/build/unreal/round6/r6_work/checks/ue/run_r6_ue.sh r6_ue_alley_replay.py r6_ue_alley_flood.py r6_ue_pocket_probe.py r6_ue_pocket_probe2.py
py -3 WorkFiles/dojo/build/unreal/round6/r6_work/measure_r6.py <abs>/unreal/round6/r6
py -3 WorkFiles/dojo/build/unreal/round6/r6_work/make_sheet_r6.py <abs>/unreal/round6/r6
```

### 1. The outside kit in DojoLab (from the outside track's round-6 Blender stage)
- **Import:**
  - 251 meshes: the 45 outside FBX (incl. SM_DKX_PocketFence_W/E and the nine SM_DKX_1v1_* blockers), the new far town,
    and the four ridged rings with their custom normals (FBX normal import ON);
  - 137 textures (T_DKX_FarFacade_BC / ORM / N new); 0 errors.
- **Materials:**
  - new instances M_DKX_FarFacade and M_DKX_FarKawara (on M_DJ_Lib_Opaque) and M_DKX_Blocker1v1 (on M_DJ_Flat_Master);
  - the retired M_DKX_FarRoofA/B and FarWallPlaster/Wood are deleted from DojoLab. look_r3 RETIRED_MESHES now takes any
    package path; the level step reports them 'absent' afterwards.
- **The 1v1 group can be found for the BR:**
  - every instance in folder Boundary_1v1 sits in Outliner folder `Dojo/Boundary_1v1` and carries the actor tag
    `Dojo/Boundary_1v1` (new in dj_sc_level);
  - 14 actors carry it: the 2 alley fences, the 2 pocket fences, the 9 invisible blockers, and the grey-box ring
    SM_DGB_Boundary_1v1 (its folder is the same, and it is 1v1-only too);
  - the blockers are class 'boundary' (Pawn block, Camera / Visibility ignore, hidden in game, no shadow); perf counts
    10 hidden mesh actors.
- **The ridge rings:** no crest strokes in any capture (CU_R6_RidgesNorth, and CU_R5_FarBackground zoomed in).
  - No Specular change was needed on them. M_DJ_EmissiveFlat_Master's new Specular input defaults to 0.5, so nothing
    changed.
  - The far kawara flashed white at grazing angles in it1: M_DKX_FarKawara now has Specular 0.15 and RoughMult 1.6.

### 2. Look fixes (look_r3.py ROUND 6; measured, see `r6_work/probe_a..c`)
- **Masters (dj_sc_materials):** M_DJ_Lib_Opaque gets `Specular` (default 0.5) and `MetallicMult` (default 1).
  M_DJ_EmissiveFlat_Master gets `Specular` (default 0.5). The defaults leave every other instance as it was.
- **Gravel** (M_DKG_Gravel / Coarse): the r5 Saturation 0.5 had taken the warm gravel map grey.
  - Now: Saturation 1.0, Tint (1.1, 0.95, 0.77), ValueMult 0.84 / 1.05.
  - CAM_Overview yards: (156-163, 133-138, 115-123), R/B 1.31-1.39, s 0.24-0.28.
  - r5 f1 was (153, 146, 150) R/B 1.02 s 0.05. Ref 1: (148, 120, 109) R/B 1.36. Ref 2: R/B 1.31-1.48, s 0.23-0.32.
- **Shade:** the crush was the missing bounce, not the grain. In probe_a / probe_c, the timber flatten / AO moved the
  worst cells only 1-2 points.
  - GI settings in the PPV: Lumen diffuse colour boost 3.0 + skylight leaking 0.1 (probe_c C3).
  - The timbers (library timbers, gate, training and stand variants): AOStrength 0.15 + FlattenToMean 0.4 toward their
    own mean.
  - **Downpipes + gutters:** the library Iron is metal (ORM metallic 0.85), so it mirrored the dark eaves.
    - They get their own M_DJS_DownpipeMetal: the Iron maps, MetallicMult 0.15, VM 2.4, flatten 0.5 to a mid grey,
      RoughMult 1.35.
    - It is on SM_DKH/DKO/DKC_Downpipe, SM_DKO_Gutter_S/N/F and the roofs' own gutter (Iron) slot.
    - Left pipe (8, 6, 6) -> (80, 68, 66); mid pipe (94, 77, 71).
  - Results:
    - corridor soffit cell: 32.8 % in r5, now under 10 %;
    - gate emblem frame: 17.9 % near-black in r5, now under 10 % in every cell;
    - pavilion ceiling: (15, 3, 1) in r5, (51, 25, 13) in it1, now (93, 48, 26).
  - **Near-black over all 42 stills (4 x 4 cells, max channel < 12):** 2 stills keep one cell over 10 %. Both are
    geometric true shade:
    - CU_Lantern 13.2 %: the void under the veranda deck;
    - CU_Taiko 11.1 %: the creases between the shaded wall-cap tile rolls.

    For comparison: 12 stills in r5 (up to 34.7 %) and 12 in it1.
- **Drum bulb:** Light_Fill_PavilionCeiling is removed; 4 fill lights are left (the alleys and corridors).
  - Blown px on the drum: CU_Taiko 0, CAM_Drum 0, CU_R4_PavilionTaiko 0 (r5: 342 / 212 / 61).
  - The ceiling is lit by the GI above.
- **Sunlit tiles:** Specular and value barely move them (probe_a V4-V6: +-0.03). The tile instance's Saturation 0.3
  was washing every tint out.
  - Now: Saturation 1.0, flatten target (0.05, 0.056, 0.064) (albedo R/B about 0.78 linear), Tint
    (0.92, 0.975, 1.05), Specular 0.3, AOStrength 0.3.
  - Sunlit R/B (the brightest 30 % of each box):

    | Tile | r5 f1 (verify) | r6 |
    |---|---|---|
    | Gate onigawara | 1.24-1.31 | 1.11 |
    | Gate noshi | 1.30-1.42 | 1.12 |
    | Gate cap rolls | 1.23-1.25 | 1.10 |
    | Pavilion E face (tight box) | 1.31 | 1.13 |
    | E wall cap (tight box) | 1.44 | 1.19 |

  - The price: the shaded hall roofs read R/B 0.74-0.80 in CAM_Ref2Match / EstablishingRef2 (r5 0.83-0.93, ref 2 0.88),
    a cooler dark slate. The low sun is warm, so a tile that stays slate in it has to sit slightly cool in shade.
- **Sunlit timber** saturation is still <= 0.65: pavilion E post 0.57 (brightest 30 %: 0.49), W post 0.47, eave beam
  0.34.
- **Decals:** decals.json now lists the 86 decals the level places.
  - The 15 roof / wall-cap lichen moved to `dropped`, with the reason (the round 5 f1 judge drop).
  - build_dressing.py applies the same drop, so a rebuild stays in sync.
  - Unreal decal gate: 86 / 86, location error 0.0.

### 3. Checks (final level, fresh processes)
- **Unreal verify: 8 / 8 gates**, including 7_gasp_trace 23 / 23 and 8_decals 86 / 86.
  - 253 / 253 meshes (97 Nanite, every fallback full), 137 textures.
  - 1110 / 1110 actors, bounds max error 0.0014 cm.
  - 24 markers (ledge error 0.0), 14 point lights.
- **Perf:**
  - 8.47 M placed triangles, 2.0 M unique;
  - 219 unique meshes;
  - draw estimate 370 per pass;
  - 138 textures, about 395 MB at full mips.
- **In-engine alley seal** (`r6_work/checks/ue/`):
  - `ue_alley_replay.json` replays the outside track's 32 CONTROL + 10 POSITIVE paths as Pawn capsule sweeps (r 30,
    hh 86):
    - with the grey-box ring IGNORED, 32 / 32 CONTROLs are blocked, so the round-6 set seals on its own;
    - with everything in, 32 / 32 CONTROLs are blocked;
    - 10 / 10 POSITIVEs are clear in every mode;
    - in BR mode (the tagged group ignored), 30 / 30 of the CONTROLs the Blender check found open are open;
    - the two lower-roof-north-end CONTROLs start inside the upper roof's eave hull at full height, so they were
      replayed with the verifier's hh 62.5 capsule.
  - `ue_alley_flood.json` (the verify_r5 flood, ring ignored): 0 alley cells reached on either side (W max Y 33.6,
    E 33.7).
  - `ue_pocket_probe*.json` (the verify_r5 slot sweeps): 0 clear. In r5 the slot paths walked clear.
- **Blender** (`r6/json/checks/`, GASP capsule r 0.30, 1.72 m):
  - walk: 47 routes, PASS at r 0.30 and at r 0.35. The 6 new CONTROL_alley_pocket_* routes are blocked by
    SM_DKX_PocketFence_* and SM_DKX_1v1_PocketSide_*.
  - climb: PASS, identical field by field to verify_r5's climb_check.json:

    | Obstacle | Height (cm) |
    |---|---|
    | Wall | 198.1 / 193.7 |
    | Pier | 123.1 |
    | Cistern | 122.3 |
    | Eave pad | 172.9 |
    | AC | 197.4 |
    | Shed crate -> band | 123.1 -> 122.9 |
    | Pavilion crate -> pad | 122.3 -> 197.9 |
    | Vending | 173.1 |
    | Plinth | 98.1 |
    | Veranda | 48.1 |
    | Hurdle | 111.8 |

  - Roof walks: gate, hall, outbuildings, corridors, shed and pavilion are all identical to verify_r5.
  - Clearance: 46 clashes (r5: 46). Ground holes: 135 clusters (r5: 136).

### Captures (unreal/round6/r6/, 42 stills + SHOWCASE_SHEET_R6.png)
The round-5 set (36, incl. CAM_Ref2Match), plus:
- CU_R6_AlleyPocketW and _E: the corridor ends from the courtyard side, through to the pocket and alley fences;
- CU_R6_AlleyAbove: the sealed strip from above and behind;
- CU_R6_PocketAboveW;
- CU_R6_TownEdgeE: the road ends at the edge-row house fronts;
- CU_R6_RidgesNorth: the jagged rings and the impostor town.

The far view, skyline and overview are CU_R5_FarBackground, CU_R5_Skyline and CAM_Overview.

### Open
- The shaded roofs are cooler than ref 2 (R/B 0.74-0.80 against 0.88). This is the trade-off for sunlit tiles <= 1.2.
- Two near-black cells over 10 % remain, both geometric true shade:
  - the void under the veranda deck (CU_Lantern 13.2 %);
  - the wall-cap tile creases (CU_Taiko 11.1 %).
- The pavilion ceiling is lit by GI only: (93, 48, 26), still a saturated red-brown.
- Lumen diffuse colour boost 3.0 lifts every bounce. The sunlit plaster and timber stayed within the limits (post s
  0.57), but the judges should look at the overall warmth.
- CU_R6_AlleyPocketE and _W read alike (the two ends are mirror-built).
- Still open from earlier rounds:
  - vegetation is pending;
  - the player's bReceivesDecals is the user's call;
  - the DojoKit lock is still held.

### Scripts changed (not committed)
- **Showcase:** `Scripts/dojo/showcase/look_r3.py` (ROUND 6 section).
- **Unreal:**
  - `dj_sc_materials.py`: Lib_Opaque Specular + MetallicMult, EmissiveFlat Specular;
  - `dj_sc_level.py`: the `Dojo/Boundary_1v1` actor tag.
- **Dressing:** `Scripts/dojo/dressing/build_dressing.py` (the decals.json drop sync).
- **Data:** `WorkFiles/dojo/build/dressing/decals.json`: 86 placements + `dropped`. The r5 copy is in
  `r6_work/start_backup/layouts/decals_r5.json`.
