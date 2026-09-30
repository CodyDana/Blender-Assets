# Dojo shared material library: build notes

## 2026-09-28 - Stage: shared dojo material library v1.0.0 (Blender only)

**Why:** the blind judges on kits 1, 2, 8, 9 and 10 found the shapes mostly right. The materials were the common
gap:
- timber too orange, clean or grey, with pale bevel stripes and light end grain;
- granite smeared, with mirrored UVs, reading as concrete;
- iron metallic at 0.89-0.90;
- glass flat and peach.

This stage builds one library that every kit uses from now on. It does not rebuild any shipped kit, and it does not
touch DojoLab or Unreal. There are no locks to take: every file below is new.

### Files
| Path | What |
|---|---|
| `Scripts/dojo/materials/dojo_tex_gen.py` | numpy generators, 14 sets + WearMask |
| `Scripts/dojo/materials/dojo_materials.py` | Blender API: `make_material`, `grain_uv`, `box_uv`, `round_uv`, `rope_uv`, `unit_uv`, `bake_wear`, `texel_density` |
| `Scripts/dojo/materials/README.md` | per-material table, Unreal recipe (3 masters, wear maths, instance params), measured numbers |
| `Scripts/dojo/materials/ref_crops.py`, `render_swatches.py`, `compose_swatches.py` | measuring, rendering and the sheet |
| `Exports/DojoKit/Materials/Textures/T_DJ_*_{BC,N,ORM}.png` + `T_DJ_WearMask_M.png` | 43 PNG, 173 MB |
| `WorkFiles/dojo/build/materials/` | `SWATCH_SHEET_r1..r4.png`, `numbers_r*.json`, `ref_medians.json`, `refcrops/`, `renders/r1..r4/`, `textures_report.json` |

### Commands
```
py -3 Scripts/dojo/materials/ref_crops.py
"C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" Scripts/dojo/materials/dojo_tex_gen.py
blender -b --factory-startup --python Scripts/dojo/materials/render_swatches.py -- --round r4 --samples 128
py -3 Scripts/dojo/materials/compose_swatches.py --round r4
```

### Method
- **Reference crops:** 27 crops from 8 sheets (the task's six, plus the gatehouse for the aged timber and the hall
  front for plaster and steps). Their medians are in `ref_medians.json`.
- **Studio rig:** the one `render_training.py` calibrated against the sheets (grey world 0.78 x 0.55,
  key/fill/top discs, AgX Medium High Contrast, -0.8 EV). Sunset: 3000 K sun at 11 degrees, a warm-to-blue sky.
- **Shapes:** each material gets shape A and shape B, made with the library's own UV helpers and `bake_wear`, i.e.
  exactly what a kit build script would call.

### Rounds (studio dE76 against the reference crop medians)
| Material | r1 | r2 | r3 | r4 |
|---|---|---|---|---|
| TimberDark | 6.2 | 3.9 | 7.4 | 3.7 |
| TimberAged | 8.1 | 6.1 | 10.7 | 6.2 |
| Granite | 9.3 | 4.0 | 4.8 | 3.0 |
| GraniteRubble | 11.5 | 3.6 | 3.3 | 3.4 |
| Iron | 3.6 | 3.6 | 3.6 | 3.6 |
| Rope | 6.8 | 2.6 | 2.6 | 2.6 |
| PlasterCream | 11.4 | 3.4 | 3.4 | 3.4 |
| PlasterEarth | 14.8 | 5.0 | 3.4 | 3.4 |
| RoofTile | 3.1 | 3.1 | 3.1 | 3.1 |
| Lacquer | 8.1 | 6.6 | 5.9 | 5.9 |
| GlassAmber (glow) | - | 25.8 | 15.1 | 21.3 |
| VendingPanel | 24.0 | 15.5 | 6.6 | 6.6 |

- **r1 → r2:**
  - Granite and rubble were 21-31 % too light and read as terrazzo. Changes: sparser grains, relief from chipped
    facets, and the rubble's dark joint bleed removed (the cavity shading had read the joints).
  - The plasters were re-measured.
  - Glass: pinned to amber hue.
  - Vending: saturated cyan.
  - The sphere swatches switched to the triplanar path.
- **r2 → r3:** every render's p10-p90 luminance spread was 0.5-0.7 x the sheets'. Added a median-preserving
  contrast step to timber, granite, rubble and lacquer, stronger normal maps, and dark stone rims.
- **r3 → r4:**
  - Timber warmer and lighter. The black repeating bands were weakened.
  - Softer granite chips (r3 read as crazy paving).
  - Less blue in the amber, emission 9 → 5.
- **Final correction pass (r4, same looks):**
  - The rope strand index was not periodic across U: s = 3v + 4u became 3v + 12u, and the seam rank went from 1.0
    to 0.937.
  - The swatch cylinder builder mirrored geometry (inside-out normals).
  - `texel_density` now measures each face against its own slot's set.
  - The swatch renderer assigned the slots after `grain_uv`: `mesh.materials.clear()` resets face material
    indices, so r1-r3 showed side-grain material on the end faces. Fixed, and documented in `grain_uv`.

### Final numbers (r4)
- **Studio dE76:** 2.6-6.6 on every opaque material, luminance 0.92-1.07 x.
  - Timber end/face luminance: 0.78 (dark end grain, the rule).
  - Iron metallic: 87.6 % of texels >= 0.95, 12.4 % = 0, 0.0 % partial.
- **Texel density** (area-weighted, measured on the swatch meshes):
  - timber faces and ends 4.8-5.7 px/cm;
  - box-UV stone and plaster 5.12;
  - lacquer 10.2 (hero);
  - glass-frame timber 5.4-5.5.
- **Edge wear:** G covers 5-14 % of the surface area (bevel faces only; broad faces 0).
- **Seams:** every tiling set's wrap step ranks below the 99th percentile of interior steps (the highest is Granite
  at 0.988).
- **Kit 1 reuse:**
  - PlasterEarth reuses kit 1's generator and parameters. Only the base colour is re-measured: kit 1's #A48B6D
    rendered x0.77 dark on this rig.
  - RoofTile is byte-identical to kit 1's T_DK_RoofTile (md5 checked).
  - Before the re-measure, PlasterEarth was byte-identical as well.

### Open points
- **GlassAmber:** the glowing pixels are hue 23 against the sheets' 37 (still too orange under AgX). Set the final
  hue and intensity in the Unreal look pass, after the sun, sky and post re-grade.
- **Timber:** the 4 m tone band repeats in V on surfaces wider than 4 m across the grain. Per-member offsets hide it
  on normal members.
- **Kits not moved over yet:** nothing already shipped uses the library yet. Kits 1, 2, 8, 9 and 10 each still have
  their own texture sets. Moving them over is their own rebuild (`make_material`, UV helpers, `bake_wear`, then
  export and Unreal instances per the README).
- **Moss and lichen** on stone beyond the rubble joints is not included (kit 1's MossMask layers over it).

## 2026-09-28 - ROUND 3: library v1.1.0, the Unreal look pass

**Why:** in DojoLab (round 2) the final judge and the verifier found the library materials giving the copy away:
timber orange-red (veranda deck s 0.85, posts 0.90, gate ceiling pure red, against the sheets' (80, 59, 46) s 0.43),
granite speckle reading as terrazzo / dalmatian, wall-cap and gate tiles red-shifted (R/B 1.28-1.88), cream plaster
red in shade (s 0.96), lacquer blotchy and wet. Texture NAMES are unchanged, so every kit picks the new pixels up on
re-import. Ground side and the full command list: `WorkFiles/dojo/build/ground/BUILD_NOTES_GROUND.md` (ROUND 3).
Outputs: `WorkFiles/dojo/build/round3/ground_materials/` (Unreal hand-off `unreal_recipe_r3.json`).

**Method.** The r2 UE captures against the Blender renders of the same views give an empirical chroma gain: UE log(R/B)
= 1.7-2.9 x the Blender render's for timber (low sun plus Lumen bounce between warm timber and plaster compounds the
chroma). New helpers in `dojo_tex_gen.py`: `grade_median` (per-channel LINEAR gain putting the texture's median on a
target), `chroma` (per-pixel chroma about luminance), `flatten_low` (pulls member-scale luminance to the median),
`hp_std_rel` (speckle contrast metric), `_nail_holes`.

| Set | r2 median (s) | r3 median (s) | What changed |
|---|---|---|---|
| TimberDark | (84, 57, 38) 0.55 | (74, 62, 54) 0.27 | chroma x 0.62 then graded to #4A3E36; across-grain band 0.06 -> 0.02, dark streaks 0.28 -> 0.12, latewood lines 0.55 -> 0.32 (no zebra); member-scale tone flattened (15 cm, k 0.8): no more black or orange members by grain_uv offset; silvering 0.05 -> 0.16; 70 nail holes per tile with iron-stain halos; checks kept |
| TimberAged | (103, 71, 47) 0.54 | (87, 73, 61) 0.30 | the same, graded to #57493D |
| Timber ends | - | face x 0.78 luminance | graded from the face target, chroma x 0.56 |
| Granite | (112, 105, 98) 0.13 | (115, 111, 106) 0.08 | NEW v2 generator: fine crystal grain, sparse low-contrast mica / feldspar, bush-hammered pits (4-10 mm), chisel strokes, soft 7 cm chips, fine crevices, cavity darkening at two scales, sun-bleached (lighter, greyer) highs, crustose lichen on 4.4 % of the face; speckle metric 0.283 -> 0.162, normal strength 8 -> 12. GraniteRubble keeps the r2 fields, unchanged |
| RoofTile | (73, 74, 77) R/B 0.95 | (64, 67, 74) R/B 0.865 | no longer kit 1's verbatim set: neutral charcoal with a blue-black glaze, roughness about 0.42 (glaze, so the rolls catch a highlight from their own curvature), the ibushi bloom kept, bronze wear (#6B5B48) instead of pale grey patches |
| PlasterCream | (185, 144, 108) 0.42 | (192, 169, 140) 0.27 | dark-stain tint (R +5 %, B -12 %) cut to (1 %, 3 %); graded to #C0A98C (cream, not peach) |
| PlasterEarth | (194, 165, 130) 0.33 | (192, 170, 144) 0.25 | tint (2 %, 5 %); graded to #C0AA90 |
| Lacquer | (110, 52, 40) 0.64 | (102, 69, 63) 0.38 | mottle 0.10 -> 0.035, craquelure 0.75 -> 0.45, contrast step 0.5 -> 0.25, satin roughness (base 0.30 -> 0.46), graded to #66453F |

**Swatches** (`SWATCH_SHEET_r5.png`, `r6` = final; studio dE76 against the sheets' crop medians):
TimberDark 7.0 (lum x1.12), TimberAged 10.0, Granite **2.8**, PlasterCream 13.5, PlasterEarth 5.9, RoofTile **1.4**,
Lacquer 4.0. The timber and cream-plaster distances rose ON PURPOSE: their albedos are greyer than the sheets so they
land on the sheets' look under UE's chroma gain (predicted veranda timber s 0.53-0.61 in UE; the target is 0.45-0.6).

**Unreal targets and caveats** (`unreal_recipe_r3.json`):
- Wall-cap / gate tiles: the r2 red shift behaved additively in log R/B (+0.68 wall cap, +0.30 gate), so the bluer
  glaze buys only about 0.09: expect wall cap ~1.7, gate ~1.17 unless the lighting is addressed too (bounce off warm
  plaster, the 2400 K gate lamps).
- Plaster in veranda shade: if it still reads s > 0.6 after the greyer timber, the cause is Lumen bounce between warm
  surfaces plus the lamps: a lighting step, not the albedo.
- Bleached timber TOPS need a world-normal-Z term in the Unreal master (a tiling map cannot know which face is up);
  not added (dj_sc_materials.py is not this track's file).
