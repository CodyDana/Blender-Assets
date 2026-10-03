# Senbon throwing needles: final report

**Date:** 2026-10-03. **Library:** props_lib senbon **1.1.0** (`Scripts/props/build_senbon.py` +
`Scripts/props/props_lib/senbon_*.py`). **Workflow:** Study + Game/tech plan -> Build -> Verify (Unreal + craft) ->
Finalise (this pass). **Status:** finished; Unreal 5.8.3 verified on the exact shipped bytes; joined the pack's
colour system; showcase added.

| | |
|---|---|
| Meshes | `SM_Senbon_Needle` (130 mm, double-pointed), `SM_Senbon_Heavy` (170 mm, three-facet point, cotton-wrapped tail) |
| Exports | `Exports/Senbon/` (2 FBX, 2 sidecars, 9 maps + Recolour/, `README.md`, `MATERIALS_README.md`) |
| Source | `Assets/Senbon.blend` (rebuilt by the build script; images packed) |
| Renders | `Renders/Senbon/` (hero, turntables, close-ups, family with kunai and spike, wire, LOD strips, LOD points, distance strip, hand scale) + `WorkFiles/senbon/SENBON_DESIGN_COMPARE.png` |
| Showcase | `showcase/Senbon/` (17 images) + one row in `showcase/ASSET_LIST.md` |
| Design reference | `WorkFiles/senbon/SENBON_STUDY.md`, `senbon_spec.json`, `SENBON_DESIGN_SHEET.png` (no user reference: the sheet is the reference) |
| Tech plan | `WorkFiles/senbon/SENBON_BUILD_PLAN.md` |

## 1. The study in short

Real needle-type throwing weapons (hari-gata) were round bo-shuriken, 15-25 cm and 5-6 mm in surviving school patterns;
the only truly thin needles on record are hair needles with no published measurements. The design (the pack's own,
generic historical form, no marks) is two meshes:

- **SM_Senbon_Needle:** 130 mm, round, double-pointed, a parabolic swell from Ø 2.3 mm at the shoulders (x ±50) to
  Ø 2.8 mm at the middle, two 15 mm cones. Blackened steel, bright ground cones. 4.61 g, balanced at the centre.
- **SM_Senbon_Heavy:** 170 mm, single point, Ø 2.8 mm tail tapering up to Ø 4.5 mm behind a 22 mm three-facet point
  (ridges from s 159). A 45 mm cotton thread wrap (Ø 4.2) between two Ø 4.6 bindings, recolourable (default `#373532`,
  the kunai grip). 11.93 g, balance 93.70 mm from the butt (8.7 mm ahead of the middle, so it flies point-first).
- Both are clearly unlike the pack's 6 mm square spike (37 g). Not built: a bundle, a holder or case, tassels, marks.

## 2. Final numbers (measured on the shipped bytes)

| | SM_Senbon_Needle | SM_Senbon_Heavy |
|---|---|---|
| Triangles LOD0/1/2 (Blender = Unreal) | **312** / 80 / 36 | 618 / 198 / 78 |
| Sides per LOD | 12 / 8 / 6 | 12 / 9 / 6 |
| LOD screen sizes | 1.0 / 0.13 / **0.029** | 1.0 / 0.17 / 0.0595 |
| Switch distances (1080p, 90 deg) | 0.89 m / **3.99 m** | 0.89 m / 2.54 m |
| LOD deviation p99 at the switch | 0.11 / 0.06 px | 0.14 / 0.17 px |
| Smallest triangle | 2.48 mm² | 0.026 mm² |
| Silhouette vs design (LOD0) | 0.002 mm | 0.004 mm |
| Mass (sidecar) | 4.608 g (design 4.615) | 11.927 g (design 11.926), COM 93.697 mm (93.695) |
| Collision | 1 hull, 18 verts, contains every LOD, ratio 1.27 | 1 hull, 17 verts, contains every LOD, ratio 1.57, centroid -1.23 cm |
| Maps | 2048 x 256 BC/ORM/N, 14 px/mm | 2048 x 256 steel (12 px/mm) + **1024 x 1024** wrap (**18 px/mm**) + Detail16 |
| Material instances | `MI_Senbon_Needle_Steel` | `MI_Senbon_Heavy_Steel`, `MI_Senbon_Heavy_Wrap` |

Sockets (cm from the pivot, +X to the point): needle Grip 0, Tip +6.5, Trail -6.5, Throw 0, Embed +5.0; heavy Grip
-6.370, Tip +7.630, Trail -9.370, Throw 0, Embed +6.130. Unreal reads them back at scale 1 with zero error.

Build gates: **32 of 32** pass (the builder's 30 plus the new `21_*_min_triangle_area_ge_0.01mm2` on both meshes).
`qa_check` 72/72 and 84/84.

## 3. What this finalise pass changed, issue by issue

| Issue (from) | Severity | What was done | Result |
|---|---|---|---|
| Needle LOD0 imports 336 of 360 triangles: Unreal's Remove Degenerates deleted the r 0.05 mm tip-flat fans, leaving a 0.1 mm hole at each tip (unreal) | major | Every needle LOD now ends in **one sharp apex** (the heavy point's construction): `senbon_geom.needle_profile`. The hull closes to an apex point at each tip (18 verts). New build gate: no triangle under 0.01 mm² | LOD0 312 tris in Blender **and** in Unreal; 0 boundary edges after Unreal's own FBX round trip; silhouette dev 0.047 -> 0.002 mm; mass 4.608 g (-0.16 % vs design) |
| Needle breaks up at the LOD2 switch (2.54 m): 9 % of the shaft in the worst raw frame (unreal) | major | Needle LOD2 screen size 0.0455 -> **0.029** (`senbon_spec.NEEDLE_LOD2_SCREEN_SIZE`): LOD2 starts at 3.99 m; LOD1 (80 tris) covers 0.89-3.99 m. No fattening | Unreal at 2.63 m now picks LOD1: worst-frame continuity 0.09 -> **0.23**, mean 0.86, 8-jitter mean 1.0. The extra loss the LOD added is gone; what remains is the needle's own sub-pixel width (2.8 mm < 1 px beyond ~2.5 m). Measured numbers stated in the README |
| Wrap reads as ribbed rubber, not cotton (craft) | major | `senbon_paint.paint_wrap` rewritten: per-stretch height (±0.02 mm) and shade (±8 %) continuous along the thread; 2-ply twist (grooves at 37 deg, 0.5 mm along the thread) in N and BC; relief 0.10 -> 0.06 mm; fibre halo on the crests (roughness toward 0.95, +4 % value); fibre/fuzz noise. Every pattern is continuous across theta = 0 (the builder's twist and fibre terms jumped at azimuth +Y) | Macro side by side (`WorkFiles/senbon/fin/look/cmp_builder_vs_dev1.png`): the turns now show ply twist and vary; reads as twisted cord. Normal tilt p99 31 -> 22.5 deg |
| Wrap Cloth Sheen proposed ON (unreal) | minor | OFF, as `MI_Kunai_Plain_Wrap` (`recolour_maps.json` switches and the spec entry) | Same cotton as the kunai grip |
| Heavy facets go dark under some HDRIs (craft) | minor | `_ground_facet`: same base colour (0.42, pack value); finer grind streaks (period ~0.25 mm), contrast mostly in roughness (mean 0.27, ±0.035), relief 0.004 mm | Measured facet/coat luminance ratio (`WorkFiles/senbon/fin/look/hdri/*.json`): courtyard 0.89 -> 0.96, studio 0.32 -> 0.34, interior 3.0 -> 4.5, sunset 3.6 -> 3.6. **Not fixed under studio/courtyard light**: a planar polished flat reflects one direction; making it read bright everywhere would need roughness ~0.4+, which kills the polish. Documented in the README |
| Facet grind lines read wavy (craft) | minor | Same `_ground_facet` change (low frequency halved, density up, no component above Nyquist) | Finer, straighter grind in the close-ups |
| LOD label clipped (craft) | minor | Gallery LOD strip camera lowered, frame 4 % wider | Labels whole in `senbon_lods_*.png` |
| Hand-scale render crude (craft) | minor | Left out of the showcase; the family shot (with kunai and spike) is the scale image | Kept in `Renders/Senbon/` as a work image only |
| Distance strip has no spike control (craft) | minor | No change: the strip already shows needle, heavy and spike (top to bottom); the real control is the Unreal pass C2 | See section 4 |
| ORM README flags (unreal) | minor | README now lists Compression No Alpha ON | |
| Wrap set could not join the pack (found in this pass) | blocker for the pack | The pack's derive step and the fabric master's single `Detail Map Size` require a **square** Detail16; the builder's wrap was 1024 x 256. The wrap set is now **1024 x 1024 at the spec's 18 px/mm** (was 16), island's lower edge on the middle row so every mip down to 4 x 4 has covered texels | Derive gates all PASS; also closes the builder's "16 vs 18 px/mm" gap. Cost: wrap textures ~5.7 MiB in Unreal (all ten senbon textures 8.3 MiB) |
| TSR flicker not measurable in a commandlet (unreal) | minor | Not measured; stated in README and here | User's PC, PIE: needle at 2.5 m and 4 m with the spike beside it |
| Lit look on verifier materials (unreal) | minor | The pack build rendered beauty frames on the real MIs: `WorkFiles/senbon/fin/ue_pack_frames/` | Reads as the pack's blackened steel; wrap dark cotton |
| Pack daylight trait, "pen" read, naming (craft) | minor | No change (pack-level / user calls); listed in section 7 | |

## 4. Unreal 5.8.3 verification (finalise run, `WorkFiles/senbon/UnrealVerify_fin/`)

The verifier's scripts (copied, paths repointed; distances 3.9 / 4.1 / 5.0 m added for the new switch), content path
`/Game/PropsCheck/Senbon_Fin_1003c` (left in place: the next run needs a new path). Five fresh commandlet processes, one
at a time, on the exact bytes hashed in `SHA256_at_start.txt` (identical after every pass and at the end):

- **A import / B read-back:** LODs 312/80/36 and 618/198/78 = Blender truth; screen sizes 1/0.13/0.029 and
  1/0.17/0.0595 exact; 1 convex hull each; 5 sockets each at scale 1 = sidecar; 10 textures with the README flags,
  power of two, full mips (12 at 2048, 11 at 1024; the wrap set is now 1024 x 1024).
- **B2 Unreal FBX round trip** (analysed in Blender): triangle counts equal; **0 boundary edges** on both LOD0s (the
  builder's needle had 24); hulls convex (max 8e-9 cm off their own hull), equal to the shipped ones within
  3.2e-7 cm; every LOD vertex inside its hull.
- **C1 lit + mips:** last-mip probes uniform and equal to the source means on all 10 textures.
- **C2 distance visibility** (1920 x 1080, 90 deg, raw single frames, 8 jitters; mask material):

| Mesh, horizontal | 2.45 m | 2.63 m | 3.9 m | 5.0 m |
|---|---|---|---|---|
| Needle worst / mean frame continuity (LOD picked) | 0.58 / 0.92 (LOD1) | **0.23 / 0.86 (LOD1)** (was 0.09 on LOD2) | 0.00 / 0.58 | 0.00 / 0.45 |
| Needle 8-jitter mean | 1.0 | 1.0 | 0.97 | 0.96 |
| Heavy worst / mean | 1.0 / 1.0 | 1.0 / 1.0 | 0.54 / 0.92 | 0.00 / 0.76 |
| Spike (control) worst / mean | 1.0 / 1.0 | 1.0 / 1.0 | 0.94 / 0.99 | 0.85 / 0.97 |

Diagonal (20 deg) needle: worst ≥ 0.90 to 2.63 m, 0.59 at 3.9 m. Beyond ~3.9 m even LOD0 drops out of some single
frames: the needle is 0.7 px wide there. That is the design's thinness, not a LOD artefact, and the plan's answer
(trail + glint VFX, TSR, no fattening) stands. TSR itself is not measured.

## 5. Pack colours

- Materials lock `senbon-wf`; `Scripts/unreal/materials/material_spec.json` gains items `Senbon_Needle` and
  `Senbon_Heavy` (6 instances: `MI_Senbon_Needle_Steel`, `MI_Senbon_Heavy_Steel` on `M_Steel_Master`,
  `MI_Senbon_Heavy_Wrap` on `M_Fabric_Master`, each with `_Base`), build entries for group `Senbon`, and
  `changes_v7_senbon`. Proof of additions only: the spec with the senbon entries removed is byte-identical to the
  pre-senbon copy (`WorkFiles/senbon/fin/material_spec_before_senbon.json`).
- New `Scripts/unreal/materials/maps/derive_constants_senbon.py` (copy of the flashbang's). Gates: default equals the v1
  contract at mip 0 and every mip, guards inactive, mip-mean drift within 2 % for six test colours: **all PASS**.
  Shipped Colour `#373532`, Lightest `#CBCBCB`.
- One code change: `np_render.py` skips the senbon STEEL UV captures as it already skipped the spike's (2048 x 256 is
  not square; `verify/analyse_captures.py` needs square maps; steel captures are report-only). Recorded in
  `changes_v7_senbon`.
- `NP_OWNER=senbon-wf bash Scripts/unreal/materials/run_build.sh senbon_1003b maps_check import_meshes import_textures
  clean build assign verify render`: preflight OK, maps_check OK, every step `passed=True`, **0 compile failures, 0
  errors**; verify gates functions, masters, instances, meshes, textures, dependencies, accounting all **true**.
- **Every other entry unchanged:** pack dump `bhnoslit_1002` (the last build before this) vs `senbon_1003`: 53 -> 59
  instances, 19 -> 21 meshes, 93 -> 103 textures, 3 masters and 5 functions; added only the senbon's, removed none,
  **changed none** (`WorkFiles/senbon/fin/materials_dump_compare_bhnoslit_1002_vs_senbon_1003.json`). The second run's
  dump (`senbon_1003b`) is byte-identical to the first.
- UV captures (senbon-only analysis, `WorkFiles/senbon/fin/uv_capture_analysis_senbon_only.json`): wrap default vs twin
  max 1 level, **default-equals-BC gate PASS**; white, red, black vs twin max 1 level; v3 recolour gates pass for white
  and red; **black fails v3 on Spearman 0.971 < 0.98**, the same near-black 8-bit trait as the kunai grip (0.956,
  pack gap A6.2). PS instructions: steel 165, wrap 227.
- The pack's full `analyse_captures.py` run still stops on a **pre-existing** fan problem
  (`uv_MI_Fan_Rivet_default`, a 1024 map captured at 2048), so the shared `uv_capture_analysis.json` was not rewritten
  (still 2026-10-02). Not the senbon's; not touched.
- The lock was released (run_build's exit trap) and is free (`np_lock.py status` = null).
- **Not applied:** the build plan's proposed "Used with Niagara Mesh Particles" flag on `M_Steel_Master` (and
  `M_Fabric_Master`). It is a change to shared masters and was flagged as needing approval; the README tells buyers.

## 6. Frozen items and housekeeping

- `check_exports_frozen.sh` output byte-identical at the start and end of this pass
  (`WorkFiles/senbon/fin/regression/check_exports_frozen_fin_{start,end}.txt`); its standing DIFF lines belong to other
  chats and were there before the build.
- 202 hashed files under `Exports/{Shuriken,SmokeBomb,BlackHat,PaperBomb,Fan,Flashbang}`, `Scripts/shuriken` and
  `Scripts/unreal/materials`: identical except exactly this pass's three materials changes
  (`material_spec.json`, `np_render.py`, new `maps/derive_constants_senbon.py`)
  (`fin_{start,end}_SHA256SUMS.txt`). The build's own frozen gate (the builder's 202-file baseline) passes. No
  `__pycache__` written under `Scripts/shuriken` or `Scripts/unreal/materials`.
- No Blender or UnrealEditor-Cmd started by this pass is running. The Senbon asset lock is released.
- Before/after copies: `WorkFiles/senbon/fin/code_before/`, `exports_before_fin/`, `senbon_report_builder.json`;
  `np_render_before_senbon.py`.

## 7. Honest known gaps and the user's calls

1. **Thin at a distance:** the needle drops below 1 px at ~2.5 m at 1080p and single frames break up from ~2.6 m;
   readability in flight depends on the planned Trail ribbon and Tip glint (not built: VFX are outside this asset).
2. **TSR flicker not measured** (commandlet captures keep no TSR history). Check in PIE on the user's PC.
3. **Heavy facets under studio light** read darker than the black body (facet/coat ratio 0.34; courtyard 0.96). Physics
   of a polished flat; changing it would change the pack's polish look.
4. **Niagara usage flag** not set on the shared masters (user approval needed).
5. **Wrap look** is now cord-like at macro, but **no blind test** was run; the wrap at 3:1 is the remaining judgement.
6. **Wrap texture memory:** square 1024 set (pack contract) leaves ~75 % fill; 5.7 MiB of the 8.3 MiB.
7. **Mass vs mesh volume:** mass and pivot use the as-built round profile; the 12-gon mesh is ~4.5 % less volume.
8. **Heavy hull** ratio 1.57 (tapered tail inside an octagonal prism); buyers set COM offset +1.23 cm (README).
9. **Departures from the plan:** heavy LOD1 9 sides (three equal facets), heavy LOD2 keeps the three facets, needle
   LOD2 screen size 0.029 (this pass), wrap 1024 x 1024 (this pass), facet roughness 0.27 vs the spec's 0.22.
10. **Pack-level, not senbon:** blackened coat reads light/tan in sunlight (shared steel values); black wrap pick fails
    v3 Spearman like the kunai grip; the fan rivet capture stops the full capture analyser.
11. **User decisions still open (from the study/plan):** the needle's Grip at its middle (plan rule says 40 mm from a
    butt it does not have), a bright polished preset (possible with Steel Tint / Roughness Adjust, no new maps), the
    Fab listing name (suggested "Throwing Needles (hari-gata)": "senbon" is strongly tied to one anime franchise), a
    needle case or holder, and the heavy's 6 mm bare butt stub (the craft review found a slight "pen refill" read; the
    study owner could shorten it to ~3 mm).

## 8. Rebuild

```
"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python Scripts/props/build_senbon.py
"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python Scripts/unreal/materials/maps/derive_constants_senbon.py
py -3 -B Scripts/unreal/materials/np_lock.py claim <owner>
NP_OWNER=<owner> bash Scripts/unreal/materials/run_build.sh <tag>
```

The build takes about 100 s (meshes, textures, AO bake, export, renders, compare, gates). Re-run the derive step after
every build that rewrites the wrap's Recolour maps; `maps_check` refuses a stale chain.
