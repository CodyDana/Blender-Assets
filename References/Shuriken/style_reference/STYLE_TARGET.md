# Shuriken pack style target (measured from the downloaded reference, 2026-09-18)

> **CURRENT RECIPE = restyle pass 2 (2026-09-18, library 3.7.0).** The table further down is the pass-1 target and is kept for history only. What shipped, judged through the pack's own rig against `WorkFiles/shuriken/style_reference/ref_rig_scaled100_{persp,top}.png`:
>
> - **Knife grind** on every cutting edge: 35° per side, 0.15 mm land, tip radius 0.075 mm; hub scallops keep a 0.45 mm chamfer plus wall, the hole a 0.3 mm deburr. Grind widths 2.04 / 1.68 / 1.25 mm on the 3.0 / 2.5 / 1.9 mm plates.
> - **Two-finish grind:** a 0.7 mm polished band at the edge (the thin bright line, measured 0.58 mm visible, same as the reference), satin grimy steel over the rest of the facet so thick plates don't read as a chrome frame.
> - **Face:** coat linear ~0.10, metallic 1.0, roughness 0.34; soft low-contrast smears spread over the face; the halo round the hole is a shallow dish in the normal map, not paint; fine, mostly dark, clustered micro-scratches; near-invisible pits; at most two tiny rust specks; narrow nicks along the grind line; tips polished over the last 2.5 mm.
> - **Mass gate** runs on the un-ground plate (outline proportions); ground mass is reported and drives the physics override.
> - The authoritative, commented recipe is the docstring of `Scripts/shuriken/shuriken_lib/material.py`. Comparison sheet: `Renders/Shuriken/style_comparison.png`. Backup: `Backups/Shuriken_restyle_pass2_2026-09-18/`.
> - Known, accepted difference: our sourced plates are 2–2.4× thicker than the reference relative to span, so the ground bevel is wider than the reference's. The material keeps the bright part as thin as the reference's.

The user brought in a free third-party shuriken asset (`shuriken.zip` from Downloads, SHA-256
c962a187…559d, extracted here) and asked for the whole pack to follow its look: **a sharp shuriken
with wear and tear**. This file records what that look is, in numbers, so every form can be built
to it. The reference's geometry and textures are for study only and are **not** reused in the pack
(licence unknown; the pack ships only our own generated meshes and baked maps).

## What the reference is
- One six-point star, 197 mm tip to tip, 2.48 mm thick, round centre hole about 24 mm, triangular
  straight-edged points off a round hub, semicircular scallop notches. Low-poly 3,408 triangles,
  high-poly 54,528 (a smooth round-over, no sculpted chips). Four 4K maps: BaseColor, Metallic,
  Roughness, Normal (tangent, OpenGL-style +Y). UV coverage 24 %, two plate islands plus wall
  strips, about 61 px/cm at 4K.
- Outline is perfectly 6-fold symmetric; the "chipped" look is entirely texture, not silhouette.
- Renders: `WorkFiles/shuriken/style_reference/ref2_lp_{hero,top,close}.png` (our rig, their maps),
  `ref2_hp_close_clay.png` (their high-poly, clay). Numbers: `styleref_textures.json`,
  `styleref_report2.json`.

## The recipe (measured inside the UV mask; stored sRGB values unless noted)
| Trait | Reference | Our pack today | Target for the pack |
|---|---|---|---|
| Coat colour, plate interior | stored p50 0.346 = **linear 0.097**; neutral, blue−red +0.02 | linear 0.035 | linear **0.09–0.11**, neutral, faintly cool |
| Plate value spread | p05 0.33 → p95 0.61 (worn areas bright) | narrow | same spread, from wear not noise |
| Island border vs interior | border mean 0.438 vs interior 0.345 (+27 %) | tips only | all ground edges bright |
| Metallic | 1.0 everywhere (97 %); 3 % pale non-metal specks | 0.9 | **1.0**; 0.2 % pale specks |
| Roughness, plate | p05 0.29 / p50 **0.32** / p95 0.39 | 0.55 | coat 0.32 ± 0.05, bare steel 0.22–0.28 |
| Roughness, walls | to 0.48 | – | walls +0.05 |
| Scratches | 1.1 % of area, thin bright dashes +0.16; walls 3 %, plate 0.8 %; random directions, dashed | radial grind | 1 % plate, 3 % walls; short dashes 3–15 mm, random angle |
| Dark pits | 0.3 %, −0.15 | – | 0.3 % |
| Rust | a few tiny warm specks | none | 1–3 specks per piece |
| Coat mottle | low-frequency lighter smudges ±0.03 | – | ±0.03 |
| Normal map | flat plates; only the edge round-over on walls (p95 6.4°) | tip facet | edge chamfer everywhere |
| Edge geometry | **full-length ground chamfer on every outer edge**, both faces, ≈ 1 mm on a 2.5 mm plate | 0.9 mm only on the last 15 mm of each tip | chamfer all outer edges, width ≈ 40 % of plate thickness (0.8 mm on 1.9–2.0 mm plates, 1.0 mm on 2.5 mm, 1.2 mm on 3.0 mm), single flat facet with a tiny round; keep the tip taper |
| Wear boundary | irregular, torn edge between coat and bare metal, eating 1–3 mm into the face | smoothstep by radius | noise-broken boundary; 100 % bare on chamfers; tips bare over the last 15 mm |

## What we keep from our own pack
- Our outlines (modern line), sourced sizes and thicknesses, mass gates, LODs, sockets, UCX, the
  bake pipeline and the shared gallery rig. Only the edge treatment and the surface recipe change.
- Study 5 caution still applies: the coat must stay clearly darker than the bare metal so the star
  does not read as flat grey. Contrast, not brightness, is the point.

## Gallery consequence
Hero object mean luminance will rise from about 0.19 (stored) toward 0.30, and the top view from
0.18 toward 0.28. Re-measure and record the new band; the pack-consistency gate compares forms
against each other, not against the old band.
