# Ninja pack materials: build and verification report

**Date:** 2026-09-26. **Roles:** material author, then maintainer final pass (workflow `pack-materials-recolour`).
**Project:** `WorkFiles/shuriken/UnrealShuriken/ShurikenValidation.uproject` (UE 5.8.3), content root `/Game/NinjaPack/`.
**Pack name:** `NinjaPack` is a working name. No asset name contains it, so the final pack name is the user's call and needs only a folder rename.

This report has two parts. **Part A** is the final state after the maintainer pass: what ships, how each item
tested, what the three reviews found and what was done about each finding, and the honest list of gaps. **Part B**
is the material author's record, kept unchanged; where it disagrees with Part A (instance count, folder layout,
`clean`, group names, lettering on the wrap), Part A holds.

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

# Part B: author phase record (unchanged)

