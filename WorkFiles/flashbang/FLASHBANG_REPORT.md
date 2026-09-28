# SM_Flashbang: build report

## ROUND 2 FINALISE (2026-09-27, on the shipped round-2 bytes)

**Status: round 2 is shipped and verified in Unreal, but it is NOT a match yet.** The round-2 blind test was run on
these exact bytes, and the judge told ours from the reference in **16 of 16 pairs (11 confident)**. The finalise
pass changed no geometry and no texture. It verified the shipped files in Unreal, refreshed the pack materials for
the new maps, and wrote up the results.

### Blind results, both rounds

| Round | Pairs | Judge correct | Confident | Main design tells |
|---|---|---|---|---|
| 1 (built 1.0.0) | 16 | 16 of 16 | 15 | plain fuze box and flat plate; a thin shiny ring on an eyelet; a chrome sleeve band; white flecks on clean paint; a brass "egg" through the holes; a smooth strap lever; engraved (not cut) base notches; clean hole rims |
| 1 finalise (2.0.0) | - | not run | - | - |
| **2 (3.0.0, the shipped state)** | 16 | **16 of 16** | **11** (all 11 on design) | a camouflage-like mottled chip band around the sleeve shoulder; soft blotchy dark-grey paint wear instead of scratches and chips; clean pale brass with a crisp "+" seam in every hole (the reference's is dark, grimy and pitted); a flat dark lever with no diamond-plate hatch or bright edge wear; 2 hole columns where the reference shows 3 at the same angle; a faceted ring and a 12-flat faceted base cap with a flat speckled finish; a simpler, boxier top block |

Fewer confident calls than round 1 (11 against 15), but every pair was still called correctly.

### Round 2 still differs (honest list, from the blind maker's measurements and the judge)

1. **Ring lines**: the reference has two thin, faint engraved lines, flush with the surface. Ours are dark V-grooves
   with bright lips, plus a similar step under the sleeve, so the canister reads as three stacked barrels. This is
   the strongest tell.
2. **Brass tube**: the reference shows a darker, glossy cylinder in each hole, with a strong vertical highlight, dark
   sides and top, dark gaps at the window edges and one horizontal seam. Ours is a paler, evenly lit fill from edge
   to edge, and the painted vertical seam plus the ledge makes a "+" in every hole. (In Unreal's lit rig the brass
   reads darker and closer to the reference: `r2/fin2/fin2_swatch_default_holes_crop.png`.)
3. **Sleeve shoulder**: ours has a wide band of bright bare-metal speckle around the sleeve top and chamfer. The
   reference has only a thin bright worn edge there.
4. **Base cap**: ours is a visible 12-flat polygon, and the stepped foot recesses read as rectangular panels. The
   reference cap is round, with top and bottom chamfers and bright silver/bronze wear. Ours is darker and duller
   (cap p90 luminance 47-56 against 66-71).
5. **Cap end face**: the reference has a thin raised rim near the outer edge, cut by about 6 notches, with a bright
   worn lip. Ours sets the notched ring further in, with a wide plain band outside it, more and smaller notches and
   almost no edge wear.
6. **Paint**: ours is lighter and yellower, with grey-black blotches that read as camouflage. The reference is a
   deeper, more saturated olive with fine light scratches, small bright chips and a hammered texture. The medians
   match, but the reference has more spread (p90 100-114 against ours 93-97) and more chips and scratches.
7. **Steel** (fuze head, collar, lever): ours is much darker and flatter under the same light (head p50 20-32
   against 36-51, p90 37-53 against 73-141). The reference is antiqued, with bright worn arrises and a visible
   diamond hatch on the lever and housing.
8. **Pull ring pose**: in the reference v1/p1 the ring hangs face-on over the body. Ours hangs further out and higher
   (v1) and lower (v2), and in p1 it sits closer to the camera. No single yaw matches the ring in all four views.
9. **Lever stand-off**: in the reference v1 and v3 the lever's lower half stands clearly off the body, with a gap.
   Ours hugs the body.
10. **Hole pattern per view**: at the best-fit yaw the reference v2 shows three hole columns and ours shows two. Our
    holes are slightly taller for their width (15.0 x 18.0 mm, w/h 0.83, against about 14.4 x 16.7 mm, 0.87).
11. **Hole rims**: the reference has a continuous bright worn ring around each hole. Ours has it only in patches.
12. **Fuze head**: the reference's top has the lever's hooked top and several small pins and flags. Ours is boxier,
    and the -Y flag reads as a plain plate.
13. Minor: our top sits about 1-1.5 % higher relative to the body, and the reference cap is about 2 % wider relative
    to the body. The reference v2 may show a faint lengthwise seam (low confidence).

Measured by the blind maker on the shipped LOD0 and maps (its own registration): silhouette IoU v1 0.788, v2 0.915,
v3 0.872, v4 0.920 (the builder measured 0.80 / 0.92 / 0.86 / 0.91).

Things the reference does not show, which we added: the camouflage-like blotches, the speckled shoulder band, the
"+" seam, the 12-flat cap with rectangular recesses, and the raised-lip grooves. A round 3 should remove these first.

### Open choices you can still flip

- **Hole layout**: kept at **5 holes per row at 0/60/120/180/270 deg**, the only pattern that fits every reference
  view (it leaves one 90-degree blank web at the back). Six evenly spaced holes per row fit the front views only.
  Note that tell 10 (two hole columns where the reference shows three in v2) may push this choice.
- **Size**: kept at **165 mm** tall (D = 44 mm). D = 40 mm would give about 150 mm. It is one constant.

### Unreal 5.8.3 verification (exact shipped bytes)

`WorkFiles/flashbang/UnrealCheck_fin2/`, content path `/Game/PropsCheck/Flashbang_FIN2_0927a`. Every pass ran in its
own fresh commandlet, one at a time, with no other commandlet running.

- **Pass A (import)**: the four FBX, imported with the README's settings (legacy importer, Convert Scene ON, Convert
  Scene Unit ON, Force Front XAxis OFF, Import Mesh LODs ON, One Convex Hull per UCX, Import Normals + MikkTSpace,
  Generate Lightmap UVs ON), and each sidecar applied with `Scripts/pipeline/ue_import_sockets.py`. Then the three
  textures were imported, and their flags checked in a separate fresh process.
- **Pass B (read-back)**: a fresh process reloaded the saved assets. **34 of 34 gates pass.** The FBX sha256 equal
  the build report (36efe9ac / c8bbabbe / d6ca145c / 116fb823). The LOD triangles equal Blender's: 5,848 / 3,244 /
  1,912 (assembled), 4,900 / 2,520 / 1,276 (body), 584 / 440 / 432 (ring), 364 / 284 / 204 (lever). The screen
  sizes are applied (1.0 / 0.1755 / 0.0614 on the assembled mesh). The UCX hulls are 4 / 2 / 1 / 1 and the slots
  2 / 2 / 1 / 1. Nanite is off and the lightmap is on UV 1. The 5 sockets (Flash, Grip, LeverHinge, Pin, Throw) on
  the assembled and body meshes equal their sidecars at relative scale 1. The ring and lever, attached at Pin /
  LeverHinge with identity, land on the assembled vertices within 0.00002 mm, and +100 deg pitch swings the lever tip
  outward (x 0.80 to 11.86 cm).
- **Textures** (fresh process): BC sRGB / TC_Default, ORM linear / Masks, N linear / TC_Normalmap with Flip Green
  OFF. All are 2048 power-of-two with mips (3 of 3 match intent).
- **Logs**: 0 errors and 0 warnings in every pass. The only matching lines are the engine's optional profiler DLL
  probes (aqProf, VTune, PIX).
- **Pass C (offscreen render, real RHI)**: the pack's lit rig rendered the pack mesh with `MI_Flashbang_Paint`, with
  7 Colour overrides: `Renders/Flashbang/flashbang_recolour_swatches.png` (frames in `r2/fin2/ue_swatches/`). There
  were 0 errors and 0 compile failures. The 2 warnings are the engine noting that the `-dpcvars` values were already
  set, the same as round 1. The chips, scratches, hole walls, brass and steel keep their colour on every swatch.

### Pack materials (refreshed for the round-2 maps)

- **Recolour constants re-derived** (`Scripts/unreal/materials/maps/derive_constants_flashbang.py`, unchanged, run
  headless). Every derive gate passes: the default equals the v1 contract at mip 0 and at every mip, every guard is
  inactive at the default, and the mip-mean drift is within 2 %. The shipped default paint colour moves from
  `#494932` to **`#474730`** (linear 0.0625 / 0.0625 / 0.0297), because the round-2 paint averages slightly darker.
  Lightest Colour stays 0.6 (`#CBCBCB`). The round-1 file is kept as `r2/fin2/recolour_constants_r1_before.json`.
- **Pack build**: the materials lock was taken as `flashbang-chat`, then
  `NP_OWNER=flashbang-chat bash Scripts/unreal/materials/run_build.sh flashbang_r2_0927 maps_check import_meshes import_textures clean build assign verify render`
  (log `r2/fin2/materials_run_flashbang_r2_0927.log`). Preflight OK (fingerprint 77963ac6, the same code and spec as
  round 1: nothing under `Scripts/unreal/materials` was edited). maps_check OK. Every step reported `passed=True`
  with **0 compile failures and 0 errors**. The verify gates are all true (functions, masters, instances, meshes,
  textures, dependencies, accounting). The pack imported the exact round-2 FBX bytes.
- **Every other entry unchanged**: comparing the pack dump before (`flashbang_0927b`, the last pack run) and after:
  53 / 53 instances, 3 masters, 5 functions, 19 meshes, 93 textures, none added or removed, and no non-flashbang
  entry changed. Only `MI_Flashbang_Paint` and `MI_Flashbang_Paint_Base` changed, and only their scalar and vector
  values (the new constants). See `r2/fin2/materials_other_instances_unchanged_r2.json`.
- **UV-plane captures** against the look contract with Metal From ORM (`r2/fin2/uv_capture_analysis_flashbang_r2.json`).
  Paint texels, mean / p99 / p99.9 level difference: default 0.07 / 1 / 1, white 0.12 / 2 / 3, red 0.17 / 3 / 7,
  black 0.06 / 1 / 3. The kept metal texels are mean 2.3, p99 10, which is the BC1 block error (steel default vs BC
  is 2.1 / 10).
- Texture memory: BC 2.8 MB, ORM 2.8 MB, N 5.6 MB, Detail16 11.2 MB (G16).
- The lock was released after the swatch render.

### Frozen items and housekeeping

- The 157 hashed files under Exports/{Shuriken, SmokeBomb, BlackHat, PaperBomb, Fan} and `Scripts/unreal/materials`
  are identical at the start and end of this pass, and identical to the builder's end snapshot
  (`r2/fin2/fin2_{start,end}_frozen_SHA256SUMS.txt`).
- `frozen_check.py` and `check_exports_frozen.sh` give the same output at the start and end of this pass (kunai 40/40,
  paper bomb 3/3). Their standing DIFFs (the fan's 23 and check_exports_frozen's 15) were already there before round 2.
- No Blender or UnrealEditor-Cmd started by this pass is left running. The Flashbang asset lock is released.

---

## ROUND 2 (builder, 2026-09-27, props_lib flashbang 3.0.0)

The user asked for a second round after seeing round 1 ("yes run the second round"). This builder pass fixed the
brief's design tells and known gaps part by part (`WorkFiles/flashbang/r2_brief.json`). It was rebuilt from scratch
with `Scripts/props/build_flashbang.py` (no arguments), then exported through `Scripts/pipeline`, qa-checked,
rendered from the baked maps, and verified in Unreal 5.8.3. **No blind test has been run on round 2 yet.**
Round 1's final state is in `Backups/Flashbang_r1_final_2026-09-27/`, which was not touched.

**Results**

- 23 of 23 build gates pass.
- `qa_check` passes 88/88 (assembled), 84/84 (body), 71/71 (pull ring) and 71/71 (lever).
- Unreal 5.8.3 check on the exact exported bytes (`WorkFiles/flashbang/r2/UnrealCheck_r2`, content path
  `/Game/PropsCheck/Flashbang_R2_0927c`): 34/34 gates pass. Each pass ran in its own fresh commandlet, one at a time.
  The LOD triangle counts, the 5 sockets at scale 1, the screen sizes, the hulls and the texture flags all match.
- The frozen items are unchanged. The 157 hashed files are byte-identical at the start and end of this run.
  `frozen_check.py` gives the same result as at the start: kunai 40/40, paper bomb 3/3.
  `check_exports_frozen.sh` gives the same output as at the start (its 15 DIFFs were already there).

**Open choices the user can still flip**

- Hole layout: kept at **5 holes per row at 0/60/120/180/270 deg**, the only pattern consistent with every
  reference view. Six evenly spaced holes per row is still possible.
- Height: kept at **165 mm** (D = 44 mm). A D of 40 mm would give about 150 mm.

**Triangles** (LOD0 / LOD1 / LOD2)

| Mesh | Round 1 final | Round 2 |
|---|---|---|
| Assembled | 5,602 / 3,938 / 1,662 | **5,848 / 3,244 / 1,912** |
| Body | – | 4,900 / 2,520 / 1,276 |
| Pull ring | – | 584 / 440 / 432 |
| Lever | – | 364 / 284 / 204 |

**LOD pop**: at the switches (0.89 m and 2.54 m), the worst raw change is 3.4 % of the object's pixels. That is
1.6 % above the render-noise floor, and the gate allows 2 %.

**Overall height**: 165.9 mm, which is 3.770 D (round 1 final: 3.749 D).

### What changed (tell by tell)

| Brief item | Round 2 change | Now |
|---|---|---|
| Brass inner "egg" / "pill" | Round 1 had per-hole cans narrower than the hole; round 2 went back to **one concentric brass tube** 1.0 mm behind the wall (r 18.8). At 4x, the reference's brass fills every window edge to edge (`r2/look2/holes_dev2.png`). Each row has a geometric seam ledge (0.3 mm step, LOD0). There is a thin vertical dark seam at each window's centre, as the reference shows. Dark radial dividers keep the see-through at 0 px. The brass is glossier (roughness 0.32) and darker, with vertical streaks and no round blotches. | The brass fills the window with a cross-shaped seam, as in the reference views (`r2/compare/fb_r2_compare_p4.png`, `..._holes_rows.png`). It still reads a little too evenly lit and rounded next to the reference's bright ledge and strong vertical highlights. |
| Fuze head width / mechanism | Kept round 2's mechanism parts (striker plate and knuckle, +Y side lug with a rolled edge and two cross pins, screw head, coil, spring post and ball). **Added a -Y side flag**: a 1.4 mm plate in YZ with a turned end and a cross pin. It is where both v2 (top-right block) and v4 (top-left hook) put a part. | Head width at H 3.4 / 3.5 / 3.6 / 3.7 D against the reference: v1 +11 / +14 / +8 / -8 %; v2 -7 / -8 / +4 / +19 %; v3 -2 / -4 / 0 / -3 %; v4 -12 / -11 / +7 / 0 %. v3 is inside 5 % at every height; v4 H 3.7 and v2 H 3.6 are too. The misses at H 3.4-3.5 in v1, v2 and v4 are the pull ring's swing, and the four reference views cannot all be met by one rigid ring pose. |
| Paint value range and wear | Less large-scale mottle (the grey "camouflage" blotches), dark flecks of 0.4-1.5 mm scattered over the whole paint, more small chips in the field, darker rim grime, rougher paint (0.36) with a stronger hammered normal, and warmer studio strips. | Paint p10 / p50 / p90, ours vs reference: v1 (49 / 73 / 94) vs (45 / 69 / 108); v2 (49 / 77 / 106) vs (39 / 76 / 115); v3 (49 / 73 / 95) vs (38 / 74 / 116); v4 (43 / 67 / 106) vs (41 / 61 / 101). p50 is within 1-6 levels. p90 is 9-21 levels low in v1-v3 and 5 high in v4 (round 1: 15-29 low everywhere). p10 is still 2-11 high. |
| Steel "white hair" scratches | Scratch strokes halved (density 0.70 to 0.32, strength 0.55 to 0.30). Arrises are brighter and more continuous. The cap's top chamfer edge has a broken bronze line. There are more bronze specks on the cap. | The housing reads darker and cleaner, with crisper edges. The cap still has less bronze wear than the reference. |
| Lever | Darker base (0.058 to 0.046). Less light etching. The cross-hatch stamp's pitch wanders ±9 %, and the stamp is broken by noise into patches. | Less regular. It is still a little lighter and more mottled than the reference's lower lever. |
| Ring-line grooves | Kept as real V-grooves, shallower (0.52 mm wide, 0.22 mm deep), and painted with less darkening (0.55 to 0.30). | A thin line with a worn lip. |
| Base cap foot | The 5 mm through-cuts (nearly invisible) became **5 stepped foot recesses** (32 deg arcs, 2.2 mm taller chamfer band, with a wall at each end). That is how the reference's side views show them: a step in the dark lower band, with a level bottom edge. | The recesses read as steps in some views. The reference views disagree on where the recesses are. |
| LOD1 budget | Dropped LOD1's tube ledge and collar segments. The concentric tube is cheaper. | LOD1 went from 3,938 to **3,244**. The plan's figure was about 2,600. The ring was kept at 24x8 because 24x6 popped (6.4 %). |
| Close-up framings | p1 pulled back and raised, p2 re-framed to rows B-C plus the cap, p3 moved closer. | Closer to the reference panels. p2's roll and p3's pose are still approximate. |

### Round 2 known gaps (honest)

- No blind test has been run on round 2.
- The brass is structurally right but reads a little rounded and evenly lit. The reference's tube has a bright
  ledge highlight and strong vertical reflections.
- Paint p90 is still 9-21 levels low in v1-v3. The paint is smoother and slightly cooler than the reference's dense,
  warm, flecked finish, and the grime spots can read as medium-size blotches.
- Head width misses the 5 % target at H 3.4-3.5 D in v1, v2 and v4 (the ring pose), and at H 3.7 in v2 (+19 %:
  the new flag).
- The foot recess layout is a choice, because the reference views disagree.
- The pack materials were not touched. The shipped textures changed under the same names, but
  `Exports/Flashbang/Textures/Recolour/recolour_constants.json` and `Renders/Flashbang/flashbang_recolour_swatches.png`
  are still from round 1's pack build. The pack's material instances need the Finalise agent's `run_build.sh`
  pass (under the PackMaterials lock) to pick up the new maps and re-derive the constants.

Where to look:

- Part compares (reference | round 1 | round 2): `WorkFiles/flashbang/r2/compare/`.
- Iteration sheets: `WorkFiles/flashbang/r2/look2/`.
- Build log: `WorkFiles/flashbang/r2/final_build.log`.
- Build report: `WorkFiles/flashbang/flashbang_report.json`.

---

# Round 1 record: finalise pass

**Date:** 2026-09-27. **Library:** props_lib flashbang **2.0.0** (round 1 was 1.0.0). **Build:**
`Scripts/props/build_flashbang.py`, run from scratch with no arguments (Blender 5.2.0 LTS, headless,
`--factory-startup`, about 150 s). It rebuilt `Assets/Flashbang.blend`, `Exports/Flashbang/` and `Renders/Flashbang/`.
Round 1's scripts, exports, renders and report are kept in `WorkFiles/flashbang/fin/r1_backup/`.

## Status

- **Build gates: 23 of 23 pass** (round 1 had 19; new: no invalid normal texel, no background through the body at
  any LOD, LOD pop under 2 %, every gallery render shows the object). `qa_check` passes 88/88, 84/84, 71/71, 71/71.
- **Pack materials:** the flashbang joined the pack under the materials lock (owner `flashbang-chat`), built with
  `run_build.sh` (preflight automatic): preflight OK, maps_check OK, import_meshes / import_textures / clean / build /
  assign / verify / render all `passed=True`, **0 compile failures**. Verify gates all true (functions, masters,
  instances, meshes, textures, dependencies, accounting). Every other instance is unchanged (the resolved plan's 49
  existing instances have identical parents, params and textures; 4 added). The lock is released.
- **Unreal 5.8.3 re-check** on the exact final bytes, fresh process per pass: see section 4.
- **Frozen items unchanged:** 155 of 155 snapshot files identical (Exports/Shuriken, SmokeBomb, BlackHat, PaperBomb,
  Fan and Scripts/unreal/materials); the only differences under Scripts/unreal/materials are the flashbang's own
  additions (proved: `material_spec.json` with the flashbang entries removed hashes to the pre-flashbang snapshot) and
  one new file, `maps/derive_constants_flashbang.py`.
- **Fidelity:** closer than round 1 on every point the craft review raised, but **not indistinguishable** from the
  reference and **no blind test was run on this pass**. Section 6 lists what still differs.

## 1. Blind results per round

| Round | Pairs | Judge correct | Confident | Main tells |
|---|---|---|---|---|
| 1 (2026-09-27) | 16 | 16 of 16 | 15 | plain fuze box and flat plate; thin shiny ring on an eyelet; chrome sleeve band; white flecks on clean paint; brass "egg" through the holes; smooth strap lever; engraved (not cut) base notches; clean hole rims |
| Finalise | - | not run | - | this pass fixed the construction and surfacing tells listed above; a blind round is the next step |

## 2. What the finalise changed (review issue by issue)

| Issue (severity) | What was done | State |
|---|---|---|
| README import omitted Convert Scene Unit (major) | README step 1 lists the ASSET_GUIDELINES 6.5 settings (Convert Scene ON, Force Front XAxis OFF, Convert Scene Unit ON, Uniform Scale 1.0, Import Normals + MikkTSpace, Import Mesh LODs, One Convex Hull per UCX, Generate Lightmap UVs ON) | fixed |
| 8-bit Paint_Detail builds as BGRA8 21.9 MB (minor) | no longer shipped; it is the build-work source of the lossless `Recolour/T_Flashbang_Paint_Detail16.png` | fixed |
| MIs did not exist (minor) | `MI_Flashbang_Paint` / `_Steel` (+ `_Base`) built, assigned to all four meshes, verified, captured | fixed |
| UV1 / Generate Lightmap UVs OFF (minor) | import uses Generate Lightmap UVs ON (6.5, as the pack importer); the FBX still carries a clean UV1 | fixed |
| Fuze head narrow plain box (blocker) | raised front panel 1 mm proud with a vertical slot (-X face); top-plate overhang 8.4 -> 4.0 mm and covering the housing; hidden housing top removed; knuckle fills the lever curl; the pin head is a thick cylinder the ring passes through | partly (simpler than the reference's mechanism) |
| Lever open hook, S-crank, thin strap, smooth face (blocker) | channel section (1.3 mm sheet, 3.3 mm flanges) whose flanges wrap the knuckle as hinge cheeks; one straight diagonal joggle with 1.4 mm fillets; stamped +-35 deg cross-hatch on the web, broken arris wear | fixed (hatch more regular than the reference's) |
| Brass "egg", see-through limbs (blocker) | one brass CAN per hole column (r 5.7 mm) so each hole shows a vertical lit cylinder with dark gaps both sides; dark radial dividers and dark discs; brighter pitted brass with vertical scratches, lower-third grime, seam groove and a lighter shoulder band; see-through 0 px at LOD0/1/2 in all four views | fixed (shoulder is normal/colour detail, not geometry: triangle budget) |
| Hole walls chrome, faceted holes (blocker) | walls dark cut steel with grime; holes 24 / 18 / 16 points (was 20 / 10 / 8) | fixed |
| Clean paint with white flecks (major) | chips = dark oxidised core + thin warm bright edge, 1-3 mm blotches; grime blotches 3-15 mm (17 % of the paint) at rims, ring lines, base and step; lighter scuffs; hammered paint normal; thin bright scratches through the paint | partly (p10 and p50 match, p90 still low) |
| Chrome sleeve / cap chamfers (major) | sleeve chamfer keeps most of its paint; steel arrises bright only on the thin bevel and in noise-broken dashes | fixed |
| Ring thin, light, faceted, eyelet (major) | 2.4 mm dark antiqued wire, bright only on the outer arc; eyelet removed; hangs 30 deg off the sleeve; 32x8 / 24x8 / 24x8 segments on one centreline with perimeter-equivalent radii | fixed |
| Base end face engraved, no foot recess (major) | recessed disc, groove, wide contact rim with 5 blocky inward notches; the notches cut 2 mm up through the outer foot edge (the side views' cut-outs); darker cap with short scratch strokes and bronze specks | fixed |
| LOD pop at 0.889 / 2.538 m (major) | LOD1 keeps 18-point holes, 8-segment cans and the ring; LOD2 keeps the ring; a rendered gate was added | fixed: worst 0.67 % of object pixels change by > 20/255 (round 1: 5.1 % and 21 %) |
| Invalid normal block, lens scratch (minor) | hidden face removed; any inward baked normal is replaced (159 texels) and gated; scratches are straight strokes | fixed |
| Hole pattern 5-uneven vs 6-even (minor) | unchanged; a user decision (section 7) | open |
| Empty back render (minor) | the back view turns the object; coverage gate | fixed |
| Ring lines normal-only (minor) | kept as normal/colour detail (a real groove costs ~576 LOD0 triangles), shallower, lighter lip, chips along the line | partly |

## 3. Measurements (final build)

| | LOD0 | LOD1 | LOD2 |
|---|---|---|---|
| `SM_Flashbang` triangles | 5,602 | 3,938 | 1,662 |
| `SM_Flashbang_Body` | 4,622 | 3,214 | 1,146 |
| `SM_Flashbang_PullRing` | 584 | 440 | 432 |
| `SM_Flashbang_Lever` | 396 | 284 | 84 |
| Screen sizes (assembled) | 1.0 | 0.1768 | 0.0619 |

- LOD0 is under the 6,000 cap. LOD1 is 70 % of LOD0, above the plan's ~2,600: the holes, cans and ring are kept
  close to LOD0 so the 0.89 m switch does not pop (measured).
- Visible-surface deviation p99: LOD1 0.80 mm (limit 0.93), LOD2 1.9 mm (limit 2.65).
- LOD pop (90 deg hfov, 1080p, 3 turns, alpha-masked): 0.12-0.27 % at 0.889 m, 0.19-0.67 % at 2.54 m; render noise
  floor (same LOD, another seed) 0.35 % / 0.72 %.
- Height 164.97 mm = 3.749 D (spec 3.77 D, 0.6 % short: the thinner lever sheet lowers the curl top 0.45 mm).
- Atlas 2048, 8.43 px/mm, fill 0.816, 74 islands. Paint chipped 14.3 % (spec 14.3 %), near-edge bare 52.6 % (spec 57.7 %).
- Top-row silhouette IoU (our alpha vs the Study's traced outlines): v1 0.80, v2 0.89, v3 0.86, v4 0.90.
- Paint p10 / p50 / p90 (sRGB, ours vs reference, same camera and light): v1 43/66/83 vs 45/69/108; v2 38/69/92 vs
  41/76/115; v3 31/61/87 vs 40/74/116; v4 30/50/80 vs 39/61/101. The shadows and mid-tones match; the highlights are
  15-29 levels low.
- Head silhouette width at H 3.4 D (ours vs reference, D units): v1 1.24 vs 1.10 (ring hangs further out), v2 0.78 vs
  0.98, v3 1.24 vs 1.24, v4 0.88 vs 1.04.
- Collision: 4 / 2 / 1 / 1 hulls containing their meshes; hull centroid 7 mm above the weighted centre of mass (README:
  Center Of Mass Offset about (0, 0, -0.7) cm).
- Texture memory in Unreal: BC 2.7 MB, ORM 2.7 MB, N 5.4 MB, Detail16 10.7 MB (G16).

## 4. Unreal 5.8.3

**Pack build** (`/Game/NinjaPack`, run tags `flashbang_0927` and, on the final bytes, `flashbang_0927b`): see Status.
The UV-plane captures (one pixel per texel, SCS_BASE_COLOR) against the look contract with Metal From ORM
(`WorkFiles/flashbang/fin/uv_capture_analysis_flashbang.json`; the pack's `analyse_captures.py` has no Metal From ORM
branch, so it was not run on this item):

| Capture (MI_Flashbang_Paint) | Paint texels: mean / p99 / p99.9 levels vs contract | Kept (metal) texels vs contract |
|---|---|---|
| default | 0.10 / 1 / 2 | mean 2.1, p99 9 (the BC1 block error: the steel default vs BC is mean 1.8, p99 9) |
| white `FFFFFF` | 0.11 / 2 / 4 | unchanged (same figures as the default: Metal From ORM keeps them) |
| red `FF0000` | 0.18 / 4 / 13 | unchanged |
| black `000000` | 0.10 / 2 / 7 | unchanged |

- Default paint colour `#494932` (linear 0.0670 / 0.0670 / 0.0318), Lightest Colour 0.6 (`#CBCBCB`); constants
  derived by `maps/derive_constants_flashbang.py` (every derive gate PASS: default equals the v1 contract at every mip,
  guards inactive, mip-mean drift within 2 %).
- Texture memory: BC 2.7 MB, ORM 2.7 MB, N 5.4 MB, Detail16 10.7 MB (G16, as intended).
- Lit beauty frames with the pack instances: `WorkFiles/materials/ue_renders/frames_raw/SM_Flashbang*_{threequarter,top,low}.png`.
- Recolour swatches (Unreal, a MaterialInstanceDynamic of `MI_Flashbang_Paint` overriding only Colour, the pack's
  beauty rig): `Renders/Flashbang/flashbang_recolour_swatches.png` - default, `1C1C1C`, `B89B6A`, `22304A`, `8E2020`,
  `7A7D80`, `EDEDE8`; the chips, scratches, hole walls, brass and steel keep their colour on every swatch. The rig is
  brighter than the reference studio, so the swatches read lighter than their chips.

**Independent re-check** (`WorkFiles/flashbang/UnrealCheck_fin/`, content path `/Game/PropsCheck/Flashbang_FIN_0927a`,
four fresh `-nullrhi` processes, one at a time): **34 of 34 gates pass, 0 warning or error lines**, on the exact
final FBX bytes (sha256 prefixes 09472194 / d6c486ad / 297b8ad0 / 39814abc). Imported with the README's settings
(Convert Scene Unit ON, Generate Lightmap UVs ON). LOD triangles equal Blender's on all four meshes; hulls 4 / 2 / 1 / 1;
slots 2 / 2 / 1 / 1; the 5 sockets on the assembled and Body meshes equal the sidecars at scale 1; screen sizes
applied; Nanite off; the PullRing and Lever attached at Pin / LeverHinge with identity land on the assembled vertices
within 0.00002 mm; +100 deg pitch swings the lever tip outward (x 0.80 -> 11.77 cm); BC / ORM / N flags persisted
(3 of 3). Note: with Generate Lightmap UVs ON Unreal writes its own lightmap to UV index 2 and points the Light Map
Coordinate Index there; the harness (inherited from round 1) sets it to 1, the shipped UV1 - both are valid lightmaps.

## 5. Renders (from the shipped maps only)

`Renders/Flashbang/`: `flashbang_side_by_side.png` (reference | ours, all eight views), `flashbang_eight_views.png`,
`flashbang_reference_row.png`, `flashbang_closeup_p1..p4.png`, `flashbang_hero.png`, `flashbang_back.png`,
`flashbang_lods.png`, `flashbang_wire.png`, `flashbang_recolour_swatches.png` (Unreal, the pack instances, a Colour
override per swatch). Part compares: `WorkFiles/flashbang/r1/fb_r1_compare_*.png` (rewritten by this build).

## 6. Still differs (honest list)

- The fuze head is still simpler than the reference's: no side lug with its own curl, no spring, no striker detail;
  the head is narrower than the reference in v2 and v4 (0.78 / 0.88 D vs 0.98 / 1.04 D at H 3.4 D) and wider in v1.
- The paint highlights are 15-29 levels darker than the reference (p90), and the grime blotches read slightly
  camouflage-like at a distance; the reference's paint has more bright scuffing.
- The brass shoulder above the seam and the ring-line grooves are normal/colour detail, not geometry.
- The lever's stamped cross-hatch is more regular than the reference's.
- The reference's four views are not one rigid object (Study section 10); one assembly and per-view yaws were chosen
  (v1 -130, v2 170, v3 -110, v4 -25).
- LOD1 is 3,938 triangles (70 % of LOD0) to keep the switch clean.
- No blind test of this pass.

## 7. Decisions for you

1. **Hole pattern:** 5 holes per row at 0/60/120/180/270 deg (fits every reference view; leaves one 90 deg blank web
   at the back) or 6 evenly spaced (the natural manufactured pattern; fits the front views only).
2. **Scale:** D = 44 mm gives a 165 mm grenade (the reference is long); D = 40 mm would give 150 mm. One constant.

## 8. Where things are

Code: `Scripts/props/build_flashbang.py`, `Scripts/props/props_lib/flashbang_{spec,geom,blender,paint,look,gallery}.py`.
Finalise tools and evidence: `WorkFiles/flashbang/fin/` (patch scripts, head-width and capture analysis, swatches,
the materials run logs), Unreal harness `WorkFiles/flashbang/UnrealCheck_fin/`. Build report:
`WorkFiles/flashbang/flashbang_report.json`. Materials: `Scripts/unreal/materials/material_spec.json` (items
Flashbang, Flashbang_Body, Flashbang_PullRing, Flashbang_Lever; `changes_v6_flashbang`),
`Scripts/unreal/materials/maps/derive_constants_flashbang.py`.
