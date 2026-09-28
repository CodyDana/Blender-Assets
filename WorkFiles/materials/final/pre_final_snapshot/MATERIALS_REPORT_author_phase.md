# Ninja pack materials: build and verification report

**Date:** 2026-09-26. **Role:** material author, workflow `pack-materials-recolour`.
**Project:** `WorkFiles/shuriken/UnrealShuriken/ShurikenValidation.uproject` (UE 5.8.3), content root `/Game/NinjaPack/`.
**Pack name:** `NinjaPack` is a working name. No asset name contains it, so the final pack name is the user's call and needs only a folder rename.

## 1. Result in one screen

| Check | Result |
|---|---|
| Masters, functions, instances built from code | 3 masters, 5 material functions, 12 instances plus 1 preset (`Presets/MI_Kunai_Plain_Wrap_Undyed`) |
| Everything compiles (fresh process, real D3D12 RHI) | Yes: 0 "Failed to compile" lines in the verify log. PS instructions: steel 165, fabric 199 (wrap 215), paper 257. Samplers 4-5 |
| Instances: right parent and defaults | 13 of 13; every value the spec sets reads back equal |
| Every slot bound, no WorldGridMaterial | 10 meshes, 12 slots, all 3 LODs of each (36 sections) resolve to a `/Game/NinjaPack/MaterialInstances` asset. Sockets equal their sidecars |
| Texture flags | 45 of 45 match their kind in a fresh process, including the hat ORM composite (`CTM_NORMAL_ROUGHNESS_TO_GREEN`, power 1). The Detail16 maps build as G16 (2.67 bytes per texel with mips) |
| Default = today's look (Unreal base-colour capture) | All 5 recolourable parts pass. Capture vs the graph twin: p99.9 1 level, mean 0.08-0.13. Capture vs the shipped BC: max 1-3 levels, except the paper (max 7, on 0.1 % of texels at ink edges; section 4.2) |
| Recolour holds (white, saturated red, near black) | 0 clipped texels, max gap 1 level, detail kept 34-40 % (white) to 100 % (near black), Spearman 0.983-0.999. One metric miss: the wrap at near black, Spearman 0.956 (section 4.3) |
| Idempotent build | Two full clean + build + assign + verify runs (`r2`, `r3`) give **byte-identical** dumps: graphs, parameters, texture flags and slots, and also node layout |
| Frozen exports | `check_exports_frozen.sh` exits 0: 63 of 63 identical, and the only new files are the 10 `Recolour/` files the map phase made. `Assets/Shuriken.blend` is still `f712b421...` |
| Offscreen renders | 30 lit frames (10 meshes x 3 views) plus a contact sheet, 17 base-colour captures, 5 recolour stress sheets |

## 2. What was built

### 2.1 Code: `Scripts/unreal/materials/`

| File | Job |
|---|---|
| `material_spec.json` | The build's source of truth, copied from `WorkFiles/materials/material_spec.json` and updated (section 5). It covers every item, slot, texture, texture kind, master parameter (name, group, sort order, range, tooltip) and default. `GENERATOR` values are resolved from each item's `Exports/<Group>/Textures/Recolour/recolour_maps.json`, and generator values win over the spec |
| `np_spec.py` | Pure Python: resolves the spec plus the recolour JSONs into slots, instances, textures and meshes. It fails on unresolved or unknown values and requires every PNG in the four export folders to be imported or explicitly skipped |
| `np_graph.py` | A checked expression-graph builder over `MaterialEditingLibrary`. Every connection is verified |
| `np_functions.py` | `MF_TintDetail`, `MF_AlbedoRollOff`, `MF_NormalStrength`, `MF_LetteringBand`, `MF_InkDerive` |
| `np_masters.py` | `M_Steel_Master`, `M_Fabric_Master` (material attributes; shading model from expression), `M_PaperInk_Master` |
| `np_textures.py` | Texture import and flags. It **reuses** the props and shuriken importers' own `INTENT` tables for BC/ORM/N/M/Lettering: it loads them in a harmless verify-on-an-empty-folder mode, and their report goes to `WorkFiles/materials/build/logs/`, never to `Exports/`. The build asserts the spec agrees with them. It also applies the black hat's ORM composite step, as `bhu_tex_composite.py` does, and verifies flags |
| `np_meshes.py` | Legacy FBX import with the line's measured settings, then `pipeline.ue_import_sockets.apply_sidecar` unchanged (the only save). Slot assignment runs in a later process |
| `np_build.py` | Build and clean. It refuses to run over existing graphs (section 3) |
| `np_dump.py`, `np_verify.py` | Canonical dump (graph walk from the roots, so it does not depend on names or GUIDs) and fresh-process gates |
| `np_render.py` | Offscreen renders: UV-plane base-colour captures (with UV probes), lit beauty frames, sheen calibration, texture memory |
| `build_pack_materials.py` | Entry point, one mode per Unreal process |
| `run_build.sh` | Runs the modes in order, one commandlet at a time. It waits while any `UnrealEditor-Cmd` runs and stops on any failure, `passed=False`, or compile failure |
| `verify/analyse_captures.py`, `verify/make_frames.py`, `verify/sheen_blender_reference.py`, `verify/sheen_compare.py` | Headless Blender analysis of the Unreal captures, frame finishing, and the sheen calibration |
| `maps/` | The map generators from the previous phase (unchanged) |

To rebuild from nothing, run `bash Scripts/unreal/materials/run_build.sh <tag>`. The default steps are `import_meshes import_textures clean build assign verify`, taking about 1.5 minutes in total. Renders are a separate step: `NP_RENDER_PARTS=uv,beauty,sheen bash run_build.sh <tag> render`, then the two Blender scripts in `verify/`.

### 2.2 Assets under `/Game/NinjaPack/`

- `Materials/`: `M_Steel_Master`, `M_Fabric_Master`, `M_PaperInk_Master`.
- `Materials/Functions/`: the five MFs. They are exposed to the library and each has a description of its math.
- `MaterialInstances/`:
  - `MI_Shuriken_{FourPoint,EightPoint,SquarePlate,SixPoint,Spike,HookedCross}_Steel`
  - `MI_Kunai_Plain_Steel`, `MI_Kunai_Plain_Wrap`
  - `MI_SmokeBomb_Cloth`
  - `MI_BlackHat_Straw`, `MI_BlackHat_Cloth`
  - `MI_PaperBomb_Tag`
  - `Presets/MI_Kunai_Plain_Wrap_Undyed`: the baked undyed wrap BC, as a child of the wrap instance.
- `Textures/{Shuriken,SmokeBomb,BlackHat,PaperBomb}/`: 45 textures.
  - Not imported: the three shipped sRGB `*_Detail.png`. They are superseded by the lossless 16-bit `Recolour/*_Detail16` copies; the sRGB G8 builds as BGRA8, about 85 MiB for the smoke bomb.
  - `T_PaperBomb_M` is imported but not wired (README section 4).
- `Meshes/`: the 10 static meshes, with sockets and LOD screen sizes from their sidecars.

### 2.3 What the buyer sees

Each recolourable part has one colour at the top of its instance: **`01 Colour` > `Colour`** for the fabric parts, and **`01 Colours` > `Paper Colour` / `Black Ink Colour` / `Red Ink Colour`** for the paper bomb. Its default is the shipped look, and it means "the average colour this part reads as".

Parameter groups:

- `02 Detail`: Detail Strength, 0..1.5.
- `03 Surface`: Roughness Adjust ±0.25, Specular Strength, Normal Strength 0..2, and Baked AO In Colour on the paper.
- `04 Sheen`: an optional Cloth sheen.
- `05 Lettering`: the kunai band.
- `08 Advanced (set by build, do not edit)`: the generator constants.
- `09 Textures`: the maps and the switches `Use Baked Colour Map` and `Specular From ORM Alpha`.

The steel has `Steel Tint` (white = as shipped), `Roughness Adjust` and `Normal Strength`. Every parameter has a tooltip taken from the spec, or a fallback in `np_masters.DESC_FALLBACK`.

## 3. Finding: never rebuild a material graph in place (UE 5.8.3)

The first idempotency design reused existing assets. For graphs it called `delete_all_material_expressions(_in_function)`, rebuilt, and saved.

- In the authoring process this compiled.
- A **fresh process then failed to compile every material that calls the rebuilt functions**: "Missing function input 'Colour' / 'DetailScale'", "If input A must be a primitive type". The calls lose some of the re-created function inputs. See `build/logs/render_r1.log` (14 failures).

Therefore:

- `build` now refuses to run while any authored asset exists.
- `clean` (its own process) deletes `Materials/` and `MaterialInstances/` and checks both disk and registry.
- `build` creates everything from nothing, and `assign` re-binds the slots.

The two runs `r2` and `r3` of that sequence gave byte-identical dumps (`build/dump_r2.json` and `build/dump_r3.json`, plus the `dump_layout_*` files) and 0 compile failures in their fresh verify processes.

## 4. Verification

### 4.1 Fresh-process verify (`build/verify_r3.json`, real RHI, `-AllowCommandletRendering -RenderOffscreen`)

- `-nullrhi` does not compile shaders: `get_statistics` returns 0 instructions there. So verify runs on the real RHI.
- The gates for functions, masters, instances, meshes, textures and PNG accounting all pass.
- Masters expose exactly the spec's parameters, with no missing, extra or unreachable nodes.
- Shading models:
  - Steel and paper: Default Lit.
  - Fabric: From Material Expression with material attributes.
- Texture memory (`build/render_r2b.json`) is 242.6 MiB for the whole line. It includes:
  - smoke-bomb Detail16: 42.7 MiB (G16);
  - hat Detail16: 10.7 MiB each;
  - paper PaperDetail and InkWeights: 21.4 MiB each (uncompressed BGRA8).

### 4.2 Default = the Blender look: Unreal base-colour captures (`ue_renders/uv_capture_analysis.json`)

**Method.** The engine Plane is scaled to one world unit per texel and captured orthographically at each texture's resolution (1024, 2048 or 4096) with `SCS_BASE_COLOR`. That capture is the GBuffer's 8-bit sRGB base colour, so its stored levels are exact. The comparison is against:

- the **twin**: the same graph evaluated in float64 on the same PNGs;
- the shipped **BC** PNG.

**Measurement fix.** The Plane's UVs do not land exactly on texel centres. Each pixel samples up to ±0.012 / ±0.023 / ±0.047 texel off-centre at 1024 / 2048 / 4096. A bilinear fetch then bleeds a few percent of the neighbour into high-contrast texels.

- This happens with a bare texture sample too (tested with a transient material, and in a 4×4-tiled capture), so it is capture geometry, not material math.
- Each capture therefore has a **UV probe**: a transient, never-saved material that writes the magnified sub-texel sample offset. The twin samples the maps at exactly those positions, before the non-linear graph math.
- Without the probe the smoke bomb read max 44 levels; with it, max 3.

| Part (default instance) | vs twin: max / p99.9 / mean (levels) | vs shipped BC: max / p99.9 / mean | dE00 vs BC mean / p99 |
|---|---|---|---|
| Kunai wrap | 1 / 1 / 0.08 | 2 / 1 / 0.11 (184 texels at 2) | 0.14 / 1.15 |
| Smoke bomb cloth (4096) | 3 / 1 / 0.13 | 3 / 1 / 0.37 | 0.32 / 1.17 |
| Hat straw | 1 / 1 / 0.10 | 2 / 1 / 0.24 | 0.25 / 1.14 |
| Hat cloth | 1 / 1 / 0.10 | 1 / 1 / 0.18 | 0.17 / 1.12 |
| Paper tag (Baked AO In Colour 0) | 7 / 1 / 0.08 | 7 / 2 / 0.09 | 0.15 / 0.81 |
| Paper tag as shipped (AO 1) | 7 / 3 / 0.29 vs twin × ORM.R | — | the ORM is DXT1 (TC_Masks), so AO block error shows |
| Steel (6 forms, BC path) | — | 20-40 / 8-10 / 0.48-0.65 | This is BC1 (DXT1) compression of the shipped BC, which the steel has always had: reported, not gated |

Notes on the table:

- **Twin vs BC at the texel level** (from the generators): 0 levels for the smoke bomb and hat, at most 2 for the wrap, at most 1 for the paper.
- **The gate** (MATERIAL_PLAN V2: capture vs twin, p99.9 ≤ 1 and mean ≤ 0.3) passes for all five parts. Saved as `ue_renders/basecolour/uv_*_default.png` (lossless stored levels).
- **The paper's residual max** sits on 0.1 % of texels at ink edges next to 0.9 paper, where 0.001 texel of residual sample-position error is worth several dark levels.

### 4.3 Recolour stress in Unreal (runtime MaterialInstanceDynamic, no asset written)

Colours tested were white 0.8, saturated red (0.8, 0.02, 0.02) and near black 0.01, on every fabric part, and each paper colour alone.

- **Capture vs twin:** p99.9 ≤ 1 everywhere except smoke-bomb white/red (p99.9 1, max 11 on 1383 texels). The gate is p99.9 ≤ 2; the GPU's pow/exp round differently from float64 by a fraction of a level.
- **V3 metrics on the Unreal 8-bit captures:**

  | Metric | White / red | Near black |
  |---|---|---|
  | Clipped texels | 0 | 0 |
  | Max banding gap | 1 level, occupancy ≥ 1.0 of the span | 1 level |
  | Log-contrast kept | 34-40 % | 100 % |
  | Spearman vs default capture | 0.983-0.999 | 0.993-0.998 |

  Mean albedo for white 0.8: wrap 0.798, smoke 0.759, straw 0.767, cloth 0.773.
- **One metric miss:** the kunai wrap at near black has Spearman 0.956 (gate 0.98). Its detail is intact (log-contrast ratio 1.004, max gap 1), but the wrap's narrow detail range collapses into a handful of 8-bit levels at 0.01, and the ties lower the rank correlation. This comes from the 8-bit output, not from the recolour.
- **Paper:** each colour recolours, and the derived dry and pool colours stay in [0, 1]. Pooled red stays dark for any red colour, by design (plan section 3.3). Black-ink white reads flat inside solid strokes, as the map phase recorded.
- Sheets: `ue_renders/basecolour/stress_sheet_<part>.png`.

### 4.4 Lit look

- **Frames:**
  - `ue_renders/frames/<mesh>_{threequarter,top,low}.png` (1024², 2x supersampled) and the contact sheet `ue_renders/ninjapack_default_instances.png`.
  - Rig: key, fill and rim directional lights at **one light level for every item**, so the dark cloth reads dark and the paper light. A SkyAtmosphere with a real-time-capture SkyLight, and a neutral grey floor.
  - Every mesh renders with its default instances. The hat, smoke bomb and kunai grip read black or dark, and the paper tag as printed paper.
  - The steel reflects little (black sky above the floor), so it reads as near-black silhouettes with edge highlights. This is a lighting-rig limitation of the check, not a material issue.
- **Commandlet rendering gotchas** (all fixed in `np_render.py`):
  - `Editor.AsyncStaticMeshCompilation=0` is needed, or nothing renders.
  - `unreal.Rotator`'s positional order is (roll, pitch, yaw).
  - The 10 cm default near plane clips these small props.

### 4.5 Kunai wrap sheen: calibrated, and the default changed (`ue_renders/sheen_calibration/sheen_compare.json`)

The survey mapped Blender's sheen (weight 0.35, tint 0.62/0.60/0.56, roughness 0.35) onto Unreal's Cloth model as Fuzz (0.62, 0.60, 0.56) with Cloth 0.35. That was measured instead of guessed:

- **Setup:** Blender (Cycles, Principled) and Unreal each lit the same flat-coloured sphere with one key and one rim light. For every Fuzz/Cloth candidate, the sheen-on / sheen-off luminance ratio per N·V bin was compared with Blender's. The no-sheen baselines agree within 1 % in shape.
- **Errors** (RMS log-ratio):

  | Candidate | Error |
  |---|---|
  | Survey mapping | 0.477 (reads light grey) |
  | Best Cloth pair: Fuzz = tint × 0.35 = (0.217, 0.21, 0.196), Cloth 0.35 | 0.259 |
  | Plain Default Lit | **0.206** |

- **Why:** Unreal's Cloth lobe *replaces* the GGX specular, so it dims the grazing rim (rim ratio 0.84) that Blender's additive sheen brightens (1.35).
- **Decision:** `MI_Kunai_Plain_Wrap` ships with **Cloth Sheen OFF**, the measured closer match. The calibrated pair is the default for a buyer who switches it on.
- This changes the survey spec's `Cloth Sheen: true`. It is recorded in the build spec with the numbers.

## 5. Changes against the survey spec (all in `Scripts/unreal/materials/material_spec.json`)

- **Paper maps:**
  - `T_PaperBomb_PaperDetail` is kind `PaperDetail_sRGB`: sRGB ON, `TC_EditorIcon` (BGRA8). Its sampler is Color.
  - `T_PaperBomb_InkWeights` is `InkWeights_linear`: `TC_VectorDisplacementmap` (BGRA8 linear).
  - This follows the map generator's finding that linear 8-bit RGB fails G-P1. BC7 was not used.
- **Kunai wrap:** Cloth Sheen false, and Sheen Colour (0.217, 0.21, 0.196) on the wrap and as the master default (section 4.5).
- **Build settings:** added `build.recolour_maps`, `build.master_default_textures` and `build.not_imported`, plus `unwired_texture_kinds` for the paper's `_M`.
- **Generator values win:** two spec numbers differed from the generator and the generator was used:
  - smoke-bomb Colour: 0.045583 → 0.045583837;
  - Detail Scale: 13.838558 → 13.838304, recomputed from the written Detail16.

## 6. Re-pointing the paused paper bomb

When its exact-match pass changes the maps:

1. Run `blender -b --factory-startup --python Scripts/unreal/materials/maps/make_paperbomb_recolour_maps.py` (G-P0 fails loudly if the art stops matching the BC).
2. Run `bash Scripts/unreal/materials/run_build.sh <tag>`.

Asset names do not change. If the palette or `_composite` changes, the MF_InkDerive constants come through `recolour_maps.json` automatically.

## 7. Open points and the user's calls

1. **Pack name:** `/Game/NinjaPack` is a working name.
2. **Steel BC compression:** the steel BC is DXT1 (TC_Default), with up to 40 levels of block error on rust specks and edges. It has always shipped this way. BC7 would cost 2x memory for better fidelity; that is the user's call.
3. **Wrap sheen:** the measured choice is Default Lit. If the user prefers the Cloth "dusty" read, the switch is one checkbox and the calibrated pair is preset.
4. **Smoke-bomb Detail16:** 42.7 MiB at 4096 (G16). Setting Maximum Texture Size to 2048 in a game build is the user's call; its report found 2048 loses sparkle.
5. **Substrate:** untested; the project has it off.
6. **Lettering band:** the band graph compiles and is on for the wrap, but the shipped mask is blank, so it was not visually exercised.
7. **Buyer review (V7):** the parameter names, groups, tooltips and ranges are in `build/dump_r3.json`. An independent read-through was not run.

## 8. Evidence index (`WorkFiles/materials/`)

- `build/`:
  - one JSON per mode and run: `import_*_r3`, `clean_r3`, `build_r3`, `assign_r3`, `verify_r3`, `render_r2*`;
  - `dump_r2.json` / `dump_r3.json` and the `dump_layout_*` files (identical);
  - `logs/`, `compile_failures_*.txt`, `frozen_check_final.txt`;
  - API probes `probe_api*.json`.
  - Earlier runs are kept for the record: `r1`, `r1b` (the in-place rebuild that failed), and the `t*` render tests.
- `ue_renders/`:
  - `frames/` and `ninjapack_default_instances.png`;
  - `basecolour/` and `uv_capture_analysis.json`;
  - `sheen_calibration/`;
  - `captures/capture_jobs.json`. The EXRs were deleted after analysis, since they are fully represented by the PNGs and the JSON.
- No Unreal or Blender process of this phase is left running. The other session's `UnrealEditor.exe` (DemoGame_1) was never touched. No lock was claimed or released.
