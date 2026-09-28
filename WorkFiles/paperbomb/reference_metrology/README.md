# Paper-bomb reference metrology

## Authority

The reference of record is **`References/PaperBomb/paperbomb_guide_v2_real_glyphs.png`**
(300 × 653, real kanji), byte-identical to the `Downloads/paperbomb.png` the user named
(sha256 `670acbd782c9a43bb0b2838851ec6bec7aaae144f18aaeb5e8cf45ca7ef01099`). It is called **RG**.

`References/PaperBomb/paperbomb_guide.png` (1024 × 1536, **HR**) is supporting material only:
sub-pixel character — stroke-edge roughness, kasure hole shape, paper-fibre size, brush-tip
behaviour — and **never** a position, size, weight, colour or shape.

RG samples the card at **3.917 px/mm**: one pixel is **0.2553 mm** and nothing finer than a
**0.51 mm** cell is resolvable. Every row in the spec carries its own tolerance and an `HR?` flag.

## Current instrument — use these

| File | What it does |
|---|---|
| `rg_lib.py` | loader (stored sRGB via `pngread`), morphology, connected components, robust line fits, debug PNG writer |
| `rg_s1_silhouette.py` → `rg_s1_silhouette.json` | tag edge, aspect, the four chamfers, edge straightness, **and the tear / nick / dog-ear test** |
| `rg_s2_elements.py` → `rg_s2_elements.json` | classification, first-cut rules and corners, full ink-cluster inventory |
| `rg_s3_geometry.py` → `rg_s3_geometry.json` | rule insets and frame, continuity and thinning, corner ornaments, named zones |
| `rg_s3b_ring_glyph.py` → `rg_s3b_ring_glyph.json` | ring ellipse, stroke, coverage, striation; hero glyph and every clearance |
| `rg_s4_ink.py` → `rg_s4_ink.json` | paper colour, edge ageing, the six reds, black core, halo, seals, the leaf-pair probe |
| `rg_s5_detail.py` → `rg_s5_detail.json` | columns, flame, seals, corrected colour rows, **HR sub-pixel character** |
| `rg_s6_columns.py` → `rg_s6_columns.json` | columns split at their necks (the glyphs touch), flame run ladder and heart scan |
| `rg_s7_fix.py` → `rg_s7_fix.json` | ink-aware grain and mottle, the centreline chain by class, the top rule's dark section |
| `rg_s8_seals.py` → `rg_s8_seals.json` | the two seals isolated on their own components |
| `rg_s9_consolidate.py` → **`reference_spec_realglyph.json`** | the machine-readable twin of `References/PaperBomb/REFERENCE_SPEC.md`, plus the labelled overlay |

Run any of them with:

```
"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python rg_sN_*.py
```

(The system Python has no numpy; Blender's has numpy 2.3.4.)

## Two traps this instrument had to fix

1. **The percentile trap.** Red ink reaches warmth (R−B) 0.80 while the paper sits at 0.25, so a
   "half-maximum between p1 and p99" threshold lands *above the paper* and the tag mask collapses
   onto the ink. The paper level must be measured as the paper level.
2. **The red-only rule trap.** Part of the top border rule is drawn in dark, desaturated ink.
   Measuring rule continuity on the **red** mask alone reports a 20 mm hole that no photograph
   shows. Continuity and width are measured on **ink = red ∪ black**.

## Superseded — do NOT take reference numbers from these

The following were written with the **old** high-resolution guide as the authority (the previous
spec said "V1 for every proportion, stroke, ornament and colour"). They remain for provenance
only. Anything in them that this pass did not re-confirm is **not** a reference value:

`LAYOUT_NOTES.md`, `INK_NOTES.md`, `TYPE_NOTES.md`, `reference_spec.json`, `layout.json`,
`ink_colour.json`, `typography.json`, `typography_raw.json`, `lfl_report.json`, and every
`measure*.py` / `stage*.py` / `probe*.py` / `pb*.py` / `tagmeas.py` / `summarise.py` /
`lfl*.py` script beside them.

`lib_metro.py`, `lib_tag.py` and `pngread.py` are still sound as *libraries* — `rg_lib.py` builds
on the same ideas and `pngread.py` is imported directly — but `lib_tag.CARD_H_MM = 156.0` is now
wrong (the card is **162.29 mm**), so do not use `lib_tag` for a new measurement without fixing it.

## The line that does not move

Everything here MEASURES the guides and emits numbers. Nothing here writes artwork a build could
consume, and nothing under `Scripts/` imports any of it. `paperbomb_art.py` refuses to open the
guides (`FORBIDDEN_INPUT_FRAGMENTS`, `GuideAccess`, `no_guide_access`) — keep that gate passing.
Debug rasters live in `debug/`, are named `DEBUG_NEVER_SHIP_RG_*`, and must never be traced,
sampled, thresholded or vectorised. This is what keeps the asset clear of Fab's CreatedWithAI
disclosure.
