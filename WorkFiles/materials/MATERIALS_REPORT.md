# Ninja pack materials: build and verification report

**Date:** 2026-09-26. **Roles:** material author, then maintainer final pass (workflow `pack-materials-recolour`).
**Project:** `WorkFiles/shuriken/UnrealShuriken/ShurikenValidation.uproject` (UE 5.8.3), content root `/Game/NinjaPack/`.
**Pack name:** `NinjaPack` is a working name. No asset name contains it, so the final pack name is the user's call and needs only a folder rename.

This report has two parts. **Part A** is the final state after the maintainer pass: what ships, how each item
tested, what the three reviews found and what was done about each finding, and the honest list of gaps. **Part B**
is the material author's record, kept unchanged; where it disagrees with Part A (instance count, folder layout,
`clean`, group names, lettering on the wrap), Part A holds.
**Update 2026-09-27:** section A8 records the rebuild for the kunai blade-section rework (shuriken_lib 3.11.1). Where
A8 gives a newer kunai figure, A8 wins.

# Part A: final state (maintainer pass)

## A1. Result in one screen

| Check | Result |
|---|---|
| Built from code, deterministic | 3 masters, 5 material functions, 25 instances: 12 `MI_<Item>_<Part>_Base`, 12 buyer-facing `MI_<Item>_<Part>` and 1 preset. Two full clean + build + assign + verify runs (`f1`, `f2`) give **byte-identical** dumps and node layouts |
| Compiles, fresh process, real D3D12 RHI | 0 "Failed to compile" in verify and render. PS instructions: steel 165, fabric 227, paper 260; 4-5 samplers |
| Read-back | 25 of 25 instances: right parent, every effective value equal to the spec, and the overridden set exactly what that link must override (Base: everything; buyer MI: only its colour(s)) |
| Slots, sockets, textures | 10 meshes, 12 slots, all LOD sections on the buyer MIs, no WorldGridMaterial; sockets equal their sidecars; 52 of 52 textures carry their flags |
| No dependency drag | Every mesh's transitive dependencies hold only its own item's textures plus the 8x8 `Textures/Default` maps (verify gate `dependencies`) |
| **Default = today's look** | The final build's default base-colour captures are **bit-identical** to the author build's (11 of 12 captures identical; the smoke bomb differs by 1 level on 2 of 16.8 M texels). Capture vs twin p99.9 1 level; vs the shipped BC max 1-3 levels (paper 7 on 0.1 % of ink-edge texels) |
| **Recolour holds** (Unreal captures: default + 9 colours per fabric part incl. `FFFFFF FF0000 0000FF F2E8D5 000000`, 17 paper jobs) | 57 of 57 captures pass: highlight plateau ≤ 14 % (was 100 % for white/red/blue), gap 1 level, detail kept 47-56 % (white) to 100 % (dark), mean colour at a distance within 0.6 % (was up to +25 % on the smoke bomb) |
| Renderer setups | Substrate: base colour identical to deferred, lit within 1.6 %. Forward shading: lit within 0.2 %. Mobile untested |
| Frozen exports | `check_exports_frozen.sh` exits 0: 63 of 63 identical; the only new files are 18 (10 Recolour maps/JSON of the map phase, 4 `recolour_constants.json`, 4 `MATERIALS_README.md`). `Assets/Shuriken.blend` still `f712b421...` |

## A2. Per item

"Default match" = Unreal base-colour capture of the shipped buyer MI vs the shipped BC (8-bit stored levels, UV-probe
corrected; `ue_renders/uv_capture_analysis.json`). "Recolour" = the final Unreal stress
(`final/recolour/ue/fs_ue_results.json`) plus the float64 twin on the full maps with mips 2/4/6
(`final/recolour/fs_twin_results.json`).

| Item | Master(s) | Buyer instances (each with a `_Base`) | Recolourable parts (parameter) | Default match | Recolour test |
|---|---|---|---|---|---|
| Shuriken four-point, eight-point, square plate, six-point, spike, hooked cross | `M_Steel_Master` | `MI_Shuriken_<Form>_Steel` | None (optional `Steel Tint`, a multiplier, clamped) | The BC map itself: only its own DXT1 block error (max 21-40, p99.9 8-10 levels), unchanged from the author build | Not recolourable; Steel Tint white = identity (verified) |
| Kunai (plain) | `M_Steel_Master` + `M_Fabric_Master` | `MI_Kunai_Plain_Steel`, `MI_Kunai_Plain_Wrap`; preset `Presets/MI_Kunai_Plain_Wrap_Undyed` | Grip wrap (`Colour`, shipped `#373532`, Lightest `#CBCBCB`) | Wrap: max 2, p99.9 1, mean 0.11 levels; dE00 mean 0.14 | PASS 10/10 (UE). White → `#CBCBCB`: plateau 5.8 % / highlights 13.9 %, detail 56 %, mip-4 mean ×1.0003. Black → `#191919`, detail 100 % |
| Smoke bomb | `M_Fabric_Master` | `MI_SmokeBomb_Cloth` | Cloth (`Colour`, shipped `#3F3A37`, Lightest `#C5C5C5`) | max 3, p99.9 1, mean 0.37 levels; dE00 mean 0.32 | PASS 10/10. White → `#C5C5C5`: plateau 2.2 % / 4.9 %, detail 47 %, mip-4 ×1.003 (was ×1.147); deep red B01010 mip-4 ×1.005 (was ×1.246) |
| Black hat | `M_Fabric_Master` | `MI_BlackHat_Straw`, `MI_BlackHat_Cloth` | Straw (`Colour`, `#3F3C3B`), cloth band (`Colour`, `#383737`); Lightest `#CBCBCB` each | Straw max 2, p99.9 1; cloth max 1, p99.9 1 | PASS 10/10 each. White: straw plateau 4.2 % / 10.9 %, detail 48 %; cloth 2.7 % / 6.7 %, 51 %; mip-4 within 0.1 % |
| Paper bomb (paused art; re-point in A6) | `M_PaperInk_Master` | `MI_PaperBomb_Tag` | Paper (`Paper Colour`, `#F3E3C3`), black ink (`Black Ink Colour`, `#0F0F0E`), red ink (`Red Ink Colour`, `#D5180B`) | AO off: max 7 (0.1 % ink-edge texels), p99.9 2; dE00 mean 0.15 | PASS 17/17. White paper → `#F4F4F4` cap: paper plateau 10.8 % (was 49.6 %), 0.66 % of paper texels at the art's 0.962 ceiling (was 52 %). Neutral red ink pools neutral (C\*ab 0.0, was 8.5). Black paper → `#191919`: detail kept, 33 % plateau (8-bit limit, documented) |

Swatch sheets (one per recolourable part; Unreal captures, mip 0 and mip 4 as the GPU shades it vs the true filtered
result): `final/recolour/swatch_UE_{Kunai_Wrap,SmokeBomb_Cloth,BlackHat_Straw,BlackHat_Cloth,PaperBomb_Paper,PaperBomb_BlackInk,PaperBomb_RedInk}.png`.
Twin sheets with the full metrics: `final/recolour/swatch_<part>.png`. One-page default-look comparison:
`final/default_look_comparison.png` (Blender gallery graph | Blender linear-filtered | Unreal, matched lights).

## A3. Review findings and what was done

### Blocker

**Light colours flattened every highlight (recolour review).** Any pick with a channel near full intensity made the
headroom ≤ 0, so every highlight texel took one value. **Fixed** in `MF_TintDetail`: the pick is scaled (hue kept)
down to a per-part **Lightest Colour** = min(0.6, 0.9 / HighlightRatio^0.2), so the highlight exponent never drops
below 0.2. Lightest is `#CBCBCB` (wrap, straw, hat cloth) and `#C5C5C5` (smoke bomb); it is a buyer slider in
`01 Colour` (0.3-0.9, 0.9 = no cap) with a tooltip, so a buyer who wants a brighter result can trade highlight detail
for it. The verifier's own proposal (Cmin 0.35) was tested and rejected: it maps white to `#A7A7A7` on the smoke bomb
(dE00 21 from the pick); the chosen cap costs dE00 11-13 for pure white and keeps plateaus at 2-14 %. The top 15 % of
the smoke bomb's white threads sit in the roll-off knee (0.85-0.95), spread evenly over 12 levels, 0 texels at the
0.949 clip gate. `V3` now includes `FFFFFF`, `FF0000`, `0000FF`, `F2E8D5`, `000000` and a plateau metric.

### Major

| Finding | Action |
|---|---|
| Recolours got lighter at a distance (Jensen gap; smoke bomb +15-25 % at mip 4) | **Fixed.** `MF_TintDetail` multiplies by K = exp(-A(lod)·(1-C_hi)^P): the material computes the detail map's mip level from UV derivatives (anisotropy-aware, clamped 0-8), A(lod) is piecewise linear from 8 per-part increments fitted on the Unreal mip chain (`maps/derive_constants.py`). K = 1 at the default and at dark colours (C = 1), so the default stays exact at every mip. Measured in Unreal at mip 4: all parts within 0.6 % (smoke bomb ×1.003-1.005). Two log-normal alternatives were tried first and only halved the drift; a second log-detail texture would have cost +67 MiB |
| Pure black gave a flat 0 | **Fixed** (fabric Colour and Paper Colour): colour + max(0.01 - max3, 0), hue kept. `000000` → `#191919` with 100 % of the detail. Not applied to the inks (the default black ink, 0.0048, is below the floor) |
| Full-intensity paper clipped half the grain | **Fixed**: Paper Colour is scaled to ≤ **Paper Colour Limit** = 0.962 / p99.9 paper weight = 0.904 (`#F4F4F4`). The verifier's other suggestion (a soft knee instead of the art's hard 0.962 min) was **not** applied: the shipped default reaches 0.957 in the paper's red channel, so any knee below 0.962 would change the default |
| No buyer README | **Done**: `Exports/{Shuriken,SmokeBomb,BlackHat,PaperBomb}/MATERIALS_README.md` (new files): where things are, change a colour in 3 steps, variants (duplicate first), what the colour means and the Hex sRGB field, light/black/distance behaviour, reset and `Use Original Baked Colours`, what to leave alone, supported setups, kunai sheen and lettering, smoke-bomb tone note, paper ink behaviours. Tooltips no longer point to files that do not ship |
| Reset-to-default gave the smoke bomb's values | **Fixed**: master → `MaterialInstances/Base/MI_<Item>_<Part>_Base` (all textures and matched settings) → `MI_<Item>_<Part>` (on the mesh; overrides only its colour). Reset or untick restores that part's shipped value. Master defaults are now neutral |
| Masters dragged other items' textures (42.7 MiB) | **Fixed**: masters reference only seven 8x8 textures in `/Game/NinjaPack/Textures/Default` (`Scripts/unreal/materials/default_textures/`, generated); the verify gate walks every mesh's dependencies |
| Substrate / forward / mobile untested and undocumented | **Tested** Substrate and forward in throwaway project copies (deleted afterwards; `final/compat/`): all 12 buyer MIs compile, base colour identical under Substrate, lit captures within 1.6 % (Substrate) and 0.2 % (forward) for default, white and red on every recolourable part. **Float Precision Mode Full** on the fabric and paper masters, **Used With Instanced Static Meshes** on all three. Mobile is not tested and is stated as such in every README |
| Smoke bomb 13-17 % lighter than the Cycles gallery (look review) | **No material change** (user's call, as the verifier said): the gallery is darkened by Cycles filtering 8-bit sRGB before decoding; Unreal shows the maps' true albedo. The README tells buyers and gives the -7 % Colour tweak if the gallery tone is wanted. The item's sidecar is frozen, so the note lives in the README and this report |
| Kunai wrap loses the preview's grazing sheen glints | **Kept** Default Lit (measured closer) and stated plainly in the kunai README. A calibrated view-dependent sheen term was not added (user's call) |

### Minor

| Finding | Action |
|---|---|
| Red pool greenish for neutral picks | **Fixed**: pool gain chroma fades with the red ink's saturation (`Red Ink Pool Default Saturation`); default exact, neutral picks pool neutral |
| Constants over the whole map incl. background fill | **Fixed**: `recolour_constants.json` recomputes Colour/Bias/Scale/Mean/HighlightRatio/moments over covered texels (Colour' × n' = Colour × n); the default capture is unchanged |
| Tooltips / group names | **Fixed**: buyer language; one scheme 01 Colour, 02 Detail, 03 Surface, 04 Sheen, 05 Lettering, 08 Advanced (matched to ... - do not change), 09 Textures; `Use Baked Colour Map` → `Use Original Baked Colours` in 01 Colour; Steel Tint clamped (saturate) |
| Lettering on over a blank mask | **Fixed**: the wrap ships `Use Lettering` off (227 PS instructions instead of +16). The lettering group still shows on other fabric MIs (static switch off; the README says it does nothing there) |
| Build hygiene | **Fixed**: `clean` deletes only spec-authored assets and refuses (deleting nothing) if the folders hold anything else; `run_build.sh` runs `maps_check` (sha256 chain maps → recolour_maps.json → recolour_constants.json, plus derive script and twin hashes) before any Unreal step and derives its paths from its own location; the survey spec copy is marked `_SUPERSEDED`; scripts and spec snapshotted (A6). Not done: git (the project is not a repository; not asked), and `np_textures` still borrows the two importers' `INTENT` tables (documented coupling, working) |
| Absolute source paths in AssetImportData | **Not changed** (user's call): importing from a neutral staging path before Fab packaging, or clearing the source data, is a packaging step |
| Kunai textures under `Textures/Shuriken/`, no overview map | **Not changed**: the kunai ships in the shuriken pack's export folder, and the folder follows the export group; an overview map is outside the materials job |
| Detail16 combing on smoke bomb / straw (8-bit sources) | No action (as recommended): Unreal captures show max gap 1 level |
| Near-black paper grain collapses to ~10 levels | Documented (8-bit GBuffer); black paper lifts to `#191919` |

## A4. Verification method (final pass)

- `maps/derive_constants.py` (Blender headless) gates: v2 twin at the default equals the v1 contract to 1e-9 at mip 0
  and every mip; every guard inactive at the default; fitted mip correction within 2 % on the map mean.
- `maps/np_twin.py`: the one float64 twin of the v2 graphs, used by the derive step, `verify/analyse_captures.py`
  and the stress tests.
- Build `f1` and `f2` (clean + build + assign + verify), identical dumps; `render` `f2` (UV captures with UV probes,
  30 lit frames, texture memory 242.7 MiB total: the default textures add nothing measurable).
- Final stress, Unreal (`final/recolour/fs_ue_capture.py`): 57 temporary child MICs of the shipped buyer MIs in
  `/Game/_Scratch_FinalRecolour` (never saved, deleted, absent from registry and disk), captured at mip 0 and 1/16
  resolution; analysis per pixel against the twin (fabric p99.9 ≤ 2 levels, paper ≤ 3 at texel centres).
- Final stress, twin (`final/recolour/fs_twin_stress.py`): same colours as the recolour verifier, full maps, mips 2/4/6;
  all fabric and paper parts pass (gates in the script docstring).

## A5. Rebuild, re-point, snapshot

- Rebuild: `bash Scripts/unreal/materials/run_build.sh <tag>` (maps_check, import_meshes, import_textures, clean,
  build, assign, verify; about 1.5 min), then `run_build.sh <tag> render` and the `verify/` Blender scripts.
- If a Recolour map changes (for example the **paper bomb** after its paused exact-match pass): run
  `maps/make_paperbomb_recolour_maps.py`, then `maps/derive_constants.py`, then `run_build.sh`. `maps_check` refuses to
  build while the chain is stale. Asset names do not change.
- Snapshot of the scripts and spec: `WorkFiles/materials/regression/post_materials/` (with `SHA256SUMS.txt`); backup of
  `Scripts/unreal/materials` and `WorkFiles/materials`: `Backups/Materials_2026-09-26/`.

## A6. Honest gaps

1. **Pure white is not white.** By design the lightest fabric colour is `#CBCBCB` (`#C5C5C5` on the smoke bomb), dE00
   11-13 from `FFFFFF`; the paper tops out at `#F4F4F4`. A buyer can raise Lightest Colour and accept flatter
   highlights. On the smoke bomb the highlight detail of a white pick is 13 % of the default's log-contrast (the whole
   part keeps 47 %), and its brightest 15 % of threads sit in the soft roll-off.
2. **Near black on the kunai wrap** (`#191919`/`#1A1A1A`): 29 % / 24 % of highlight texels share one 8-bit level and
   Spearman vs default is 0.956-0.992. The wrap's narrow detail spans only a handful of GBuffer levels that dark (the
   shipped default itself has a 16.7 % highlight plateau). Inherent to the 8-bit base colour, not the graph.
3. **Mip compensation is a fit**: map means within 0.6 % in Unreal at mip 4 and within 1.5 % in the twin at every mip;
   per-texel differences remain at a distance (smoke bomb white mip-4 texel dE00 mean ~3); Detail Strength other than
   1 uses the same fit approximately; a streamed-out mip or a texture LOD bias makes the computed level differ.
4. **Kunai wrap sheen**: the preview's grazing glints are not reproduced (Default Lit ships); user's call.
5. **Smoke bomb tone vs the Cycles gallery**: Unreal is ~7.7 % lighter in base colour than the gallery renders (the
   gallery's filtering artefact); user's call, documented.
6. **Not tested**: mobile (ES3.1), Cloth Sheen on under Substrate or forward, Nanite; the lit-scene check still uses
   direct lights only (no captured sky light in a commandlet) and few contact shadows.
7. **Steel BC** stays DXT1 as shipped (block error up to 40 levels on specks); BC7 at 2x memory is the user's call.
8. **Paper inks** are flat inside solid strokes; a white or light ink reads as a flat shape there (by design).
9. **Shipping hygiene left to the user**: absolute source paths in the imported assets, the final pack name, no
   overview map, no version control.
10. Paper stress captures are compared at texel centres (no UV probe): p99.9 up to 3 levels on edges; the probe-
    corrected paper default check holds p99.9 ≤ 2.

## A7. Evidence index (final pass, `WorkFiles/materials/`)

- `final/constants/`, `Exports/*/Textures/Recolour/recolour_constants.json`: derived constants and their gates.
- `build/*_f1.json`, `build/*_f2.json`, `dump_f1.json` = `dump_f2.json`, `verify_f2.json`, `render_f2.json`, logs.
- `ue_renders/uv_capture_analysis.json`, `ue_renders/basecolour/`, `ue_renders/frames/`, `ninjapack_default_instances.png`.
- `final/default_captures_before_after.json`, `final/default_look_comparison.png`.
- `final/recolour/`: twin and Unreal stress scripts, results JSON, swatch sheets.
- `final/compat/`: Substrate / forward runs, `compat_results.json`, `compat_sheet.png` (project copies deleted).
- `final/exp/`: the design experiments (mean cap, mip strategies).
- `final/pre_final_snapshot/`: the author build's scripts, spec, dump and report before this pass.
- `final/frozen_check_final.txt`: the frozen-exports proof.
- No Unreal or Blender process of this pass is left running; the other session's `UnrealEditor.exe` windows and
  another agent's processes were not touched; no lock was claimed or released.

## A8. Update 2026-09-27: the kunai blade-section rework (shuriken_lib 3.11.1)

The kunai was rebuilt with a new blade cross-section (option C: a 7 mm diamond, 0.3 mm un-ground edge, 0.15 mm knife
land; `WorkFiles/kunai/KUNAI_PLAIN_REPORT.md` section 14). This replaced `Assets/Shuriken.blend`
(`f712b421...` -> `abb558fef12a...`), the kunai FBX (`a2d464722c30...`; the sidecar did not change, `bf6990550357...`) and all
of its maps. The kunai's Recolour files were bound to the old blend and wrap BC, so they were regenerated and the pack
rebuilt. Every live write is logged in `WorkFiles/kunai/blade_section/LIVE_CHANGES.md`, and the evidence is in
`WorkFiles/kunai/blade_section/materials/`.

**Section-dependent inputs.** There are none. `MI_Kunai_Plain_Steel` overrides nothing: the polished edge band and the
rest of the steel finish come from the baked `T_Kunai_Plain_{BC,ORM,N}`, which were re-imported. The wrap's
`Lettering Band UV` is (1.1328125, 0.61898509, 1.8359375, 0.73617259), and the kunai's independent Unreal check (gate 13)
confirmed that rectangle is unchanged. So no spec value or graph was edited.

**Recolour chain.**
- `maps/make_kunai_wrap_detail.py`: the only change is `BLEND_SHA_BASELINE`, from `f712b421` to `abb558fe`. The
  generator refuses any other blend. The backup is
  `WorkFiles/kunai/blade_section/script_backups/make_kunai_wrap_detail.before_blade_section.py`. It ran on the new blend,
  read-only (the sha was the same before and after), and all gates passed:
  - G-K1: islands max 1 level, mean 0.0005;
  - G-K2: dE00 mean 0.309, p99 0.985;
  - H = 3.46;
  - white gap 1.
- `maps/derive_constants.py -- --only Shuriken`: PASS. The other items' constants were not written.
- The new wrap BC differs from the old one on 171 texels, 3 of them by more than 1 level (up to 21, at the neck edge).
  So the constants moved only at bake-noise level:
  - `Colour` is identical to 6 decimals, and the default is still `#373532`;
  - `Lightest Colour` is still 0.6 (`#CBCBCB`);
  - `Detail Highlight Ratio` went from 2.647944 to 2.648017;
  - `Detail16` differs by more than 1 % on 3 texels.
- Files now: `T_Kunai_Wrap_Detail16.png` `a69e7f0826ea...`, `recolour_maps.json` `900f982095d3...`,
  `recolour_constants.json` `5ec770810bdd...`. The previous files are in `.../materials/pre/`. The comparison is
  `recolour_old_vs_new.json`.

**Rebuild: `run_build.sh kblade_0927`.** This ran every default step: maps_check, import_meshes, import_textures, clean,
build, assign and verify.
- The materials lock was held as `kunai-blade-chat`, and preflight passed.
- `UE_CMD` pointed at `WorkFiles/kunai/blade_section/materials/ue_cmd_guarded.sh`. Before every launch it runs the
  machine's one-Unreal-at-a-time guard (`WorkFiles/shuriken/UnrealCheck6/wait_unreal_free.ps1`), which also catches an
  `UnrealEditor.exe` with `-run=` or `-nullrhi`. `materials/guard.log` shows every launch was FREE.
- All steps exited 0 with `passed=True` and 0 compile failures.
- Verify ran in a fresh process on the real RHI, and every gate passed: functions, masters, 43 instances, 14 meshes,
  textures, dependencies and accounting.
  - Kunai PS instructions: steel 165, wrap 227, Undyed preset 163.
  - The kunai mesh depends only on its own 8 maps plus the Default textures.
- **The six forms' MIs are unchanged, and only the kunai wrap moved.** The dump was compared with the previous build's
  (`dump_sf_final_0927.json`; see `WorkFiles/kunai/blade_section/materials/dump_compare_vs_sf_final_0927.json`).
  - Changed: only `MI_Kunai_Plain_Wrap`, its `_Base` and the `_Undyed` preset, and only in the 8 derived constants.
  - Identical:
    - all 5 functions, all 3 masters and the node layout;
    - the other 40 instances, including all six `MI_Shuriken_*_Steel` and their Bases, and `MI_Kunai_Plain_Steel`;
    - all 14 meshes' slots and sections;
    - all 78 textures' flags.
  - Import: the kunai FBX `a2d464722c30...` and sidecar `bf6990550357...`. `T_Kunai_Wrap_Detail16` is the only texture
    whose source hash changed since that build, and all 78 imported hashes equal the files on disk.
- The six frozen shuriken forms still match `prep/frozen_six_sha256.json` on all 66 files
  (`materials/frozen_six_after_materials.json`). `Exports/Shuriken/MATERIALS_README.md` was not changed, because its
  kunai text is still true.

**Look re-verified as in A4, for the kunai only.**
- **UV-plane base-colour captures.** Run: `run_build.sh kblade_0927 render` with `NP_RENDER_ONLY` set to the kunai's 5
  captures and `SM_Kunai_Plain`, followed by `verify/analyse_captures.py` and `verify/make_frames.py`.
  - Wrap default vs the twin: max 1, p99.9 1, mean 0.079 levels (was 0.079).
  - Wrap default vs the shipped BC: max 2, p99.9 1, mean 0.109; dE00 mean 0.14, p99 1.15. The gate passes.
  - White and red stress captures vs the twin: max 1. Their V3 figures are identical to before.
  - Near-black (0.01) keeps the known Spearman miss, 0.956 (A6.2; unchanged).
  - Steel BC (DXT1, reported, not gated): inside the UV islands p99.9 is 8 (was 11) and the mean is 1.42 (was 1.44).
    The whole-map mean rose from 0.65 to 1.19. That comes only from the new background fill (94, 91, 96), which DXT1
    stores one level off, on texels no mesh shows.
  - The pack's `uv_capture_analysis.json`, `captures/capture_jobs.json` and contact sheet keep the other parts' f2
    entries, with the kunai's replaced; each file has an `updates` note. The kunai-only outputs are in
    `.../materials/ue_renders_kunai_only/`.
- **Lit frames.** `frames/SM_Kunai_Plain_*` show the new section. With a 0.15 mm land the near edge has no bright
  bevel; the old 1.5 mm edge had one. At 8x the edge is a plain anti-aliased silhouette, with no glints or periodic
  sparkle from the polished band, so nothing needed fixing in the material (`.../materials/frame_blade_*.png`).
- **Recolour stress in Unreal** (copies of `final/recolour/fs_ue_*` limited to the kunai wrap, in
  `.../materials/recolour/`). Scratch path: `/Game/_Scratch_KunaiBladeRecolour`, never saved, deleted, and absent from
  the registry and the disk afterwards.
  - PASS 10/10.
  - Every figure equals the 2026-09-26 run to within 0.001. For example, white gives `#CBCBCB`, plateau 5.8 % /
    highlights 13.9 %, detail 56 %, mip-4 ×1.0003.
- **Twin stress** (`fs_twin_stress.py --only Kunai` on this build's dump): PASS 10/10. The default equals the shipped BC
  within 2 levels.
- Unreal launches: 9, all guarded and all FREE. No Unreal or Blender process of this step is left running, and the GUI
  editors were not touched.

# Part B: author phase record (unchanged)

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

## Snow Flower heels join the pack (2026-09-27, heels-chat, tag heels_0927)

Additions only. The item `SnowFlowerHeels` is a skeletal garment for MH_PlayerFemale. np_skeletal imports it from `Exports/SnowFlowerHeels/SK_SnowFlowerHeels.skeletal.json` into `/Game/NinjaPack/Meshes/SnowFlowerHeels`, with its own skeleton copy in this project.

It adds 6 instances:
- `MI_SnowFlowerHeels_Leather` / `_Insole` on M_Fabric_Master (recolourable)
- `MI_SnowFlowerHeels_Metal` on M_Steel_Master
- each with a `_Base`

The recolour maps come from `maps/make_snowflowerheels_recolour_maps.py`, and the constants from `maps/derive_constants_snowflowerheels.py`. Every gate passes.

The run was preflight, maps_check, import_meshes, import_textures, clean, build, assign, verify. All passed, every verify gate is true and there were 0 compile failures. The 43 other instances and all masters and functions are identical to kblade_0927 (`WorkFiles/SnowFlowerHeels/final/materials/instances_unchanged_check.json`). The lock was released. Details are in `WorkFiles/SnowFlowerHeels/HEELS_REPORT.md` section 3.
