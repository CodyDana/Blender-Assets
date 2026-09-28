
## Exact reproduction (2026-09-26)

**This section supersedes everything below it where they disagree.** The sections that follow (F, E, D, C, B, A, 1-15)
are the history of earlier passes. They describe a procedural drawing typeset from a font. That drawing has been
replaced: the front of the card is now traced from the owner's reference.

**The brief.** The paper bomb is the owner's own design. The instruction was that it "must look exactly like my
reference image, every part precisely matching", traced directly from that image, which is the only source:
`References/PaperBomb/paperbomb_guide_v2_real_glyphs.png` (300 x 653 px, about 3.9 px/mm). The top-centre flame emblem
is the priority element. The text is fixed: 爆 in the centre, 火遁術 upper-left, 爆炎陣 upper-right, 焼尽 lower-right,
瞬業 lower-centre, and 火道 in the small seal. The silhouette is a clean octagon (70.0 x 162.29 mm, aspect 0.4313) with
no tears, nicks or folded corners. The mesh, LODs, collision and sockets were not changed in this pass.

**Result.** All 96 build gates pass, `qa_check` passes 74/74, and LOD0/1/2 have 1132/428/172 triangles. Two full
builds from seed 20260919 give byte-identical BC/ORM/N/M maps and sockets sidecar, and the same FBX content hash
(`d5db9968ed19b54ac46b52d07ceca9bb`). The shuriken pack is byte-identical (14 files). The recolour maps were
regenerated and pass every gate. In Unreal 5.8, `M_PaperInk_Master`, `MI_PaperBomb_Tag` and its Base instance were
rebuilt, and their fresh-process verify passed. That Unreal run also hit an error in another item's master; see
"Recolour maps and Unreal materials" below.

### Method

1. **Tracer** (`props_lib/paperbomb_trace.py`, `trace.py`, `paperbomb_finefit.py`).
   - The reference is unmixed into paper, red and black layers, and each element's contour is found at sub-pixel
     precision.
   - Each contour is fitted with splines and refined by analysis-by-synthesis. Every candidate shape is re-rendered
     through the source's own point spread (a pixel box plus a 0.4 px Gaussian) and compared with the observed
     layer.
   - The frame rules are traced as centrelines with widths. Sub-pixel paper lines inside solid red (the big seal's two
     sparkles, the slots of 道) are fitted as parametric knock-outs.
   - The result is `props_lib/paperbomb_traced.json`, in card millimetres, so it is independent of resolution. Every
     build re-traces it and requires the result to be byte-identical (gate 13b).
2. **Rasteriser** (`props_lib/paperbomb_tracedart.py`).
   - The shapes are filled with exact-area coverage at the texture grid (12.9 px/mm, with 2x supersampling), so edges
     are reconstructed crisply rather than upsampled.
   - Ink load, dry-brush residual, local red colour and stroke direction are sampled from the reference. A partial
     tone is laid as crisp bristle marks along the stroke with the same mean coverage.
   - Everything is composited in the reference's stored colour space by one function, `composite_traced`, with red
     behind black.
3. **Font decision.** The font detective tested 40 fonts already on the machine (`References/Fonts` plus the Windows
   fonts) against every column character (`WorkFiles/paperbomb/exact/fontid/fontid_result.json`). The best soft IoU
   per glyph was 0.62-0.68, which is inside the 0.55-0.69 band that separates different designs. The same-design
   control scored 0.81-0.87. The verdict was **no installed font matches**, so every column character, 爆 and 火道 is
   traced. No font file is used by the shipped art, so no font licence applies to it. The MasaFont notes in the older
   sections are history only.
4. **Paper decision.** The paper is derived from the reference with the ink removed:
   - Bare paper pixels are kept exactly.
   - Paper under and beside the ink is filled by multi-scale normalised convolution.
   - The result is resampled to the texture grid with a cubic B-spline.
   - Above the reference's Nyquist limit (2 cycles/mm), where the reference carries no information, a fine fibre band
     is added at stored-luma std 0.0045.

   Measured against the reference:
   - Paper median Lab is 90.91/0.80/20.15 against 90.91/0.81/20.12 (dE 0.02).
   - Per-pixel dE has a median of 0.18.
   - The low-frequency blotch (the std of 20 px block medians) is 0.0063 in the BC against 0.0065 in the reference.

   The pack's front render reads 0.0092 on the same measure. That extra comes from the shading of the curled card
   under the flat rig, not from the texture, so the texture's paper was left as it is.

### This final pass: what the blind judge found and what was done

- **Black ink in the front render was lifted and flat (major).** Ink roughness (ORM.G) was 0.72 for black and 0.68
  for red. Under the flat front rig, that sheen lifted the sumi to a stored luma of 0.065-0.071, against the
  reference's 0.045-0.050 once the paper was exposure-matched. I measured roughness values from 0.72 to 0.87 on the
  same frame and set both inks to **0.82**, `paperbomb_tracedart.INK_ROUGHNESS`. The black cores of the pack front now
  measure 0.045-0.049 (the reference is 0.045-0.050).

  The mottle inside the render's black (std 0.004-0.007, against the reference's 0.011-0.016) is flattened by the
  pack's shared view transform. Its toe is quadratic near black: with specular off, the same frame's black falls to
  0.009. Turning off denoising changed nothing. The texture and the scan shot (Standard view transform) carry the
  mottle, and the scan's black is dE 0.43 from the reference. The shared transform was not changed.
- **The BC's black-core mottle was about 20 % weak (minor).** The ink-load field was smoothed by a 0.8 px normalised
  convolution. Deep inside the black shapes, the reference's own unsmoothed ratio is now put back at a gain of 1.8
  (`CORE_DETAIL`); the extra over 1.0 makes up for the B-spline resampling. The boxed core std is now 0.0102-0.0112
  on the text and 0.0152 on the emblem, against the reference's 0.0109-0.0119 and 0.0164. That is within 5-14 % on
  every element (it was 19-22 % before).
- **The top-left knob's black sat on its flank (minor).** The pool wash was clipped to the traced red plus a 0.10 mm
  rim, which removed the black cap that runs just past the red. The rim is now 0.30 mm (`POOL_RIM_MM`). The knob's
  black-layer IoU against the reference is **0.929** (it was 0.786), with no grey on the paper beside the knob.
- **The big seal's top-left sparkle was short and dim (minor).** Its fit window was widened from 2.4 to 3.0 mm, so the
  long vertical ray is no longer cut at the window. The lower ray now reaches 17.9 px (it was 9.4 px), and the
  reproduction error in a common 3.4 mm window fell 5 %. The white specks and scratches in the seal field are **not**
  traced (see the gaps below). The bottom-right sparkle was already at its best fit, so it is unchanged.
- **The paper's low-frequency blotch (minor)** was left unchanged. The BC matches the reference (see above), and the
  excess is render shading.
- **The bottom-left claw's lower prong (optional)** was not changed. It was not distinguishable in the blind test.

### Per-element scores (the shipped BC photographed at the reference's grid; emblem first)

IoU and edge distance are measured on the half-level mask; the 4x IoU is on a 4x upsample. "Core dE" is the CIEDE2000
difference between the median core colours; the pixel dE is the median over pixels that are inked in both images.

| Element | Layer | IoU | IoU 4x | Mean edge (mm) | Core dE | Pixel dE |
|---|---|---|---|---|---|---|
| **Flame emblem** | black | **0.9907** | 0.9882 | **0.0118** | 0.37 | 0.72 |
| 爆 (centre) | black | 0.9884 | 0.9904 | 0.0203 | 0.34 | 0.62 |
| 火遁術 | black | 0.9768 | 0.9800 | 0.0146 | 0.36 | 0.92 |
| 爆炎陣 | black | 0.9809 | 0.9790 | 0.0149 | 0.31 | 0.99 |
| 焼尽 | black | 0.9763 | 0.9779 | 0.0214 | 0.38 | 0.86 |
| 瞬業 | black | 0.9817 | 0.9797 | 0.0159 | 0.29 | 0.95 |
| Big seal | red | 0.9797 | 0.9818 | 0.0177 | 0.21 | 0.65 |
| Small seal 火道 | red | 0.9622 | 0.9676 | 0.0142 | 0.50 | 0.90 |
| Ring | red | 0.9739 | 0.9764 | 0.0221 | 0.26 | 0.74 |
| Rules | red | 0.9649 | 0.9561 | 0.0170 | 0.78 | 1.34 |
| Chain | red / black | 0.9630 / 0.9412 | | 0.0157 / 0.0141 | 0.72 / 0.63 | |
| Top-left corner | red / black | 0.9881 / **0.9286** | | 0.0122 / 0.0217 | 0.43 / 1.98 | |
| Top-right corner | red | 0.9877 | 0.9755 | 0.0133 | 0.40 | 0.94 |
| Bottom-left corner | red | 0.9736 | 0.9612 | 0.0207 | 0.47 | 1.05 |
| Bottom-right corner | red | 0.9809 | 0.9658 | 0.0171 | 0.48 | 0.95 |
| Paper | | | | | 0.02 (median colour) | 0.18 |
| Whole card | | | | | dE mean 1.06, p90 2.56 | |

- These numbers come from `WorkFiles/paperbomb/exact/f4m/m3_scores.json`, the measurer's own code re-run on the final
  bytes.
- The build's own fidelity gate 13d scores the emblem at IoU 0.9904, edge 0.012 mm and dE 0.27, with 16 of 16
  elements in tolerance.
- The traced shapes' own overlap with the reference is 0.9978 for the emblem and 0.975 or better for every element.
- Compared with round 3, the 爆 IoU is 0.0017 lower (0.9901 before) and each column is 0.0006-0.0015 lower, because
  of the restored core mottle. The emblem is unchanged.
- Rules, black layer: IoU 0.81. This is the thresholded grey fade of the top rule's dry black run-out; it matches
  visually.

**Emblem at 4x and 8x** (`WorkFiles/paperbomb/exact/f4_emblem_zoom.png`): it is the same drawing as the reference. It
has the tall central tongue, curling side tongues, the two outer hooks, and a solid spiral heart that opens downward
into a pointed tail. The only difference is that the texture's edges are crisp where the source's pixels are soft.

**Blind side-by-side judge (round 3 bytes)**: at gallery and thumbnail size the judge's guesses were at chance on
every element. The tells it found at 4x are the ones fixed above; the render-mottle limit and the sparkle specks are
what remains.

### Gates retired, and what replaced them

**Retired as proxies for the old "our own drawing" rule:**

| Retired gate | Replaced by |
|---|---|
| `13_no_guide_image_opened` | `13_one_source_provenance` |
| `13b_art_module_contains_no_image_loads` | `13b_traced_shapes_from_the_source_and_reproducible` |
| `14_every_glyph_from_the_font` | `14_every_text_slot_traced` |

**Retired because the reference itself fails them like for like, or because they are resolution-dependent at the
texture grid.** Each one is covered by `13c`, `13d` and `29L`:

- `20_ring_is_one_lap`
- `29_ref_s05b_column_cell_max`
- `29_ref_s10_ring_kasure`
- `29_ref_s12_upper_column_axes`
- `29_ref_s19b_small_seal_glyph_em`
- `29_ref_s19d_small_seal_red_raster_box`
- `29_ref_s21_rule_weight`
- `29_ref_s22b_rule_rhythm`
- `29_ref_s25_edge_ageing`
- `29_ref_s26_paper_grain`

These are listed in `build_paper_bomb.RETIRED_GATES`, with a reason for each.

**Added:**

- `13c_traced_elements_overlap_reference`
- `13d_built_front_matches_reference_per_element` (IoU, edge distance and dE for each element on the built face)
- `29L_every_spec_row_like_for_like_with_reference`
- `30_silhouette_is_a_clean_octagon`, `30b_sides_and_bevels_are_straight`, `30c_outline_stays_inside_the_card_box`
- `31_card_aspect_matches_the_reference`
- `17c_front_scan_matches_reference_tone`
- The flame-emblem and seal-device rows `29_ref_s11b` to `s11g` and `s20b_seal_device_form`

The recolour generator's G-P4 check used to require the art modules to equal the paused snapshot. It now requires them
to be unchanged while the generator runs, and it records their hashes.

### Recolour maps and Unreal materials

**Recolour maps.** The generator `make_paperbomb_recolour_maps.py` now wraps `paperbomb_tracedart.composite_traced` in
memory.

- **Ink weights:**
  - Black weight = k x h.
  - Red weight = r x g_r x h.
  - Here g_r keeps a locally darker red from being over-claimed, and h keeps black over red from being over-claimed.
  - The traced face has no dry or pooled layer, so those weights are 0.
  - When rounding an ink weight up would exceed the texel's own colour, the weight is floored instead (15,761 red
    and 38,195 black texels).
  - The paper weight is the per-channel residual against the shipped BC.
- **New defaults:**
  - Paper Colour: linear (0.912, 0.752, 0.499), `#F5E1BB`.
  - Black Ink Colour: the traced art's own black, `#080907`.
  - Red Ink Colour: the median of the traced red cores, linear (0.589, 0.0087, 0.0035), `#CA170C`.
- **Gates:**
  - G-P0: the re-run equals the shipped BC byte for byte.
  - The capture re-composites to 0.0 exactly.
  - G-P1: the default recomposition is within 1 stored level everywhere (dE00 mean 0.26, max 0.84).
  - G-P2, G-P3 and G-P4 pass, and the recolour stress test passes.
- **Constants.** They come from the new `maps/derive_constants_paperbomb.py`. The shared `derive_constants.py` is
  unchanged, because the other items record its hash.
  - The traced paper's blue channel varies more than before (paper weight p99.9 1.209). With that, the base Paper
    Colour Limit rule (0.796) would have scaled the default down.
  - The limit is therefore raised to just above the default (0.912).
  - The v2 twin at the defaults now equals v1 exactly.
  - `maps_check` passes for the whole pack.
- `Exports/PaperBomb/MATERIALS_README.md` carries the new hex defaults. The main chat's
  `WorkFiles/materials/final/make_readmes.py` still has the old ones and would write them back if it is re-run.

**Pack materials** (tag `pb_f4`, `ShurikenValidation.uproject`, one commandlet at a time).

- **Steps run:** `maps_check`, `import_meshes`, `import_textures`, `clean`, `build`, `assign` and `verify`.
- **Other items' inputs.** Just before the run, none of them was newer than their last verified build (`fan3`,
  15:15).
- **What happened in the run:**
  1. At 23:41, one minute before `clean`, the main chat edited `np_masters.py` to add a "Metal From ORM" switch to
     the fabric master. That parameter is not yet in `material_spec.json`.
  2. `clean` deleted every authored material.
  3. `build` then rebuilt the five functions, `M_Steel_Master`, `M_PaperInk_Master` and all 33 instances, but
     `M_Fabric_Master` failed with `KeyError: 'Metal From ORM' is not in the spec`.
- **Paper bomb verify results (all pass):**
  - `M_PaperInk_Master` compiles (260 pixel instructions, 5 samplers).
  - `MI_PaperBomb_Tag` and `MI_PaperBomb_Tag_Base` have no mismatches.
  - SM_PaperBomb has 3 LODs, all slots on `MI_PaperBomb_Tag`, and the four sockets.
  - The textures and dependency gates pass.
- **Fabric items (black hat, fan, smoke bomb, kunai wrap):** they fail `verify` because their master is missing. Their
  materials will be restored by the main chat's next pack build, once its spec includes the new parameter. I did not
  touch any other item's spec entries or files.

### Provenance

| | |
|---|---|
| Source | `References/PaperBomb/paperbomb_guide_v2_real_glyphs.png` |
| Source SHA-256 | `670acbd782c9a43bb0b2838851ec6bec7aaae144f18aaeb5e8cf45ca7ef01099` |
| Method | Traced from the owner's design, on the owner's instruction |
| Traced shapes | `Scripts/props/props_lib/paperbomb_traced.json`, SHA-256 `e6b92cc75dffd3c85efcbacc26eaef5ac59f92ec96c091bc30e9391a20ca6e8f`, re-traced and reproduced byte for byte on every build |
| Per-element derivation | `paperbomb_tracedart.element_derivation()`, written into the build report under `art.provenance.elements` |
| Files the art step opened | The source and the traced JSON, and nothing else (`art.provenance.files_actually_opened`) |

### Known gaps

- **Render black mottle.** Under the pack front's shared view transform, the black-core mottle is 0.004-0.007 against
  the reference's 0.011-0.016. The black level itself now matches.
- **Seal field.** The reference's fine white specks and scratches in the big seal's red field and frame are not traced.
  The top-left sparkle's brightest pixels are still about 0.05 lower than the reference's, with 27 pixels above 0.45
  against the reference's 37.
- **Bottom-left claw.** Its lower prong is marginally thinner at 8x than in the reference.
- **Fabric master.** It is missing in the validation project until the main chat rebuilds (see above).

Files: build log and report `WorkFiles/paperbomb/exact/f4_detA*` / `f4_detB*` (B shipped), determinism
`exact/f4_determinism.txt`, measurements `exact/f4m/`, `exact/fx/`, side-by-side `exact/f4_side_by_side.png`,
backup `Backups/PaperBomb_2026-09-26/`.

---
