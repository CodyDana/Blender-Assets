# Snow Flower sheath (SM_SnowFlower_Sheath): build report

**Date:** 2026-09-26. **Role:** sheath builder, acting as `claude`. The `SnowFlower` lock was not claimed, released or
forced. **Inputs:** `References/SnowFlower/SHEATH_REFERENCE_SPEC.md` and `WorkFiles/SnowFlower/v4/sheath_spec.json` (the
build reads numbers only, never the reference pixels), `SHEATH_STUDY.md`, and the **shipped** v4 sword
`Exports/SnowFlower/v4/SM_SnowFlower.fbx` (read-only).

## FINAL PASS (maintainer, 2026-09-27): the current state. It supersedes the numbers below where they differ.

The final pass fixed the fit blocker, the bake and engineering findings and the cheap invented-detail minors. It rebuilt the sheath cleanly against the rebuilt sword, re-verified it, and wired it into the pack materials. It started no new look-matching round.

### Result

| | Final value |
|---|---|
| LOD triangles | 11,424 / 5,600 / 3,292 |
| Size | 101.0 x 44.0 x 1006.5 mm. The throat is now 44 mm deep front to back at the mouth (DESIGNED, see below) |
| Material slots | 2: `M_SnowFlower_Sheath_Lacquer` and `M_SnowFlower_Sheath_Fittings` (renamed from `_Silver` to match the sword's `Fittings`) |
| Collision | 3 hulls. The throat hull is cut at the mouth plane (z_min -187.75 mm vs mouth -187.55); before, it reached 16.5 mm past the mouth |
| Sockets | Holster (0.15, 0, -29.78) cm pitch 0.65; Mouth (0.025, 0, -18.76) cm pitch 0.65, draw axis = its -Z; BeltMount (0, -1.34, 0) cm |
| Fit on the exported bytes, 9 LOD pairs | 0 intersections, 0 enclosure failures, straight draw 0 intersections at every 1 cm step. Minimum blade clearance 0.41 mm, minimum hilt clearance 1.42 mm, minimum wall 0.93 mm (LOD0/2, at the mouth) and 0.90 mm (LOD1) |
| Visible seat gap (new check) | Front: max 3.1 mm, mean 0.9 mm. Edge-on: p90 4.75 mm, max 7.9 mm at the collar's outermost column, which is the notch under the curled leaf (background, no steel). Before the fix: about 20 mm of bare blade front and back, and 27 mm edge-on |
| qa_check | 82 of 82 |
| FBX sha256 | `37c0e9219c7b5a61f3b0be7871f1cd4bb3032e11f51d4095a67da72f50db1ab2` |
| Unreal 5.8.3 | 22 of 22 gates on these bytes (`/Game/SwordCheck/SnowFlowerSheath_Final_0927a`), including the in-engine Holster composition: the sheathed sword's sockets match Blender within 0.0001 cm |
| Pack materials | `MI_SnowFlower_Sheath_Lacquer` on `M_Fabric_Master` (Metal From ORM on, recolourable) and `MI_SnowFlower_Sheath_Fittings` on `M_Steel_Master`, each with a `_Base` |

### What was fixed

- **Guard seat (blocker).** The sword now sinks until the guard's leaf body sits 0.4 mm above the collar.
  - The pendant leaves and the hub's bottom ring (the "plug") enter the mouth like a habaki. They are part of the swept cavity, and the core and throat under the collar are 9 mm deeper per side, hidden inside the throat fitting.
  - The seat tilt was re-solved to 0.65 degrees.
  - Two knots close the plug's end, with +0.4 mm clearance over the first 25 mm. The first rebuild measured 0.012 mm at the pendant tips; a denser-knot attempt cut the leaves, and both are recorded in `final_pass/logs`.
  - `shv4_verify.py` gained the visible-seat-gap check. Its gate is front max ≤ 5 mm, edge-on p90 ≤ 5 mm and max ≤ 10 mm. The side limit was revised after the first measurement, and the reason is recorded in the code.
- **Bake halos and black pod eyes.** The blossom cage went from 2.6 to 4.8 mm, and the blossom rays now also see the surface underneath. The body cage went from 4.6 to 6.2 mm (the pods stand 5.4 mm proud). The fitting blossom proxies now sink into their fittings. The dark halos, the throat blossom's dashes and the pod "eyes" are gone; see `final_pass/before` vs `after_final`.
- **Invented detail removed:**
  - the two sleeve bead lines across the throat's lower edge;
  - the row of dark-tipped spikes under the throat;
  - the bead seam across the chape top.
- **Texture memory.** The lacquer Detail now ships at 2048. The pack imports the lossless `Recolour/T_SnowFlower_Sheath_Lacquer_Detail16.png` (G16, about 11 MB with mips) instead of the 8-bit sRGB 4096 that built as 85 MiB BGRA8.
- **Recolour range.** The lacquer Detail is normalised over the **marble only**: dielectric texels with linear luminance below 0.3. The baked pearl buds, pods and petals on the body islands sit at 0.68-0.78, against the marble's ≤ 0.12, with nothing in between. They gave the Detail a heavy tail, and the pack's constants failed their knee, every-mip and mip-drift gates. They now pass.
  - `M_Fabric_Master`'s `Metal From ORM` switch keeps the baked colour where ORM.B is metallic **or** the baked luminance ramps 0.2 -> 0.4. That is the only master change. The switch is off on every other instance, and the pack dump shows every other instance, mesh, texture and function unchanged.
- **Holstered collision.** The throat hull is clipped at the mouth. The README says to set the sword to NoCollision or QueryOnly while sheathed, because the plug sits inside the mouth by design.

### Blind results (independent reviewers, before this pass)

The judge picked ours in **16 of 16** pairs, confident in all 16. Its tells:
- flat line-art plates instead of bevelled, layered cast plates on the throat, band and chape;
- flat blossoms with dark halos, where the halos are fixed in this pass;
- a thin, uniform vine with few twigs;
- matte, low-contrast shading;
- faint lacquer marble;
- invented spikes, seam and pod holes, which are fixed in this pass;
- a boxy, square-topped throat.

### What still differs from the reference (for the user to decide)

1. **Throat, band and chape.** They are baked outlines on flat solids, not modelled bevelled plates. Modelled LOD0 plates are estimated at +3-5k triangles and would be the next quality step. The flange-lobe frames still crumple at grazing angles. The collar top is flat and square and 73.7 mm wide, against the reference's domed, cupped 44 mm ring; the width is needed to pass the blade.
2. **Blossoms.** They are flatter and lighter grey than the reference's cupped pearl flowers. The sheath's pearl petals and the sword's silver blossoms do not share one finish.
3. **Vine.** It is thinner and more uniform than the reference's forked branch. It has two near-parallel strands into the chape. The feathered leaf below the throat and the filigree clusters are missing.
4. **Lacquer.** The median tone matches, but the marble contrast is about 3x lower (std 0.030 vs 0.089). It is less blue, with no facet ridge highlight.
5. **Metal.** Satin, where the reference is polished chrome.
6. **Band frieze.** A wavy line instead of leaf scroll.
7. **Designed parts.** The back face, the 44 mm throat depth, the cavity and the belt hardware are designed. The sheath has no modelled belt hanger; the `BeltMount` socket is where the rig's hanger attaches.

### Not tested

In-hand and draw animation, the character's hip socket, mobile and Substrate. There is no Unreal base-colour capture of the Snow Flower instances.


## 0. Result in one screen

| Check | Result |
|---|---|
| Tassel or cord | **None** |
| Game mesh | One LodGroup FBX with authored LODs (no Decimate): LOD0 **10,912**, LOD1 **4,924** (45 %), LOD2 **2,624** (24 %) triangles |
| Fit | The shipped sword on the `Holster` socket sits **fully inside a real cavity**. Checked on the exported bytes of both assets, for all 9 LOD pairings (sheath LOD0-2 x sword LOD0-2): 0 intersecting triangles; blade clearance **>= 0.568 mm**; hilt clearance >= 0.716 mm; every blade vertex enclosed; straight draw in 10 mm steps clean |
| Reference match (front view on the reference's own pixel grid) | Length 1465 vs 1467 px. Silhouette IoU **0.958**. Mean width error: body 0.05 px (0.04 mm), upper body 0.4 px, chape 0.5 px, band -0.6 px, throat -4.8 px. Collar +53 px, forced by the blade (section 3) |
| Detail | Cycles selected-to-active bake from a 260k-triangle high-poly: DirectX normal, AO in ORM.R, roughness, metallic, base colour, and a lacquer Detail map. One 4096 atlas at **89 px/cm** on visible surfaces |
| Material slots | 2, both tint-ready: `M_SnowFlower_Sheath_Lacquer` (Detail map) and `M_SnowFlower_Sheath_Silver` (Steel Tint on `M_Steel_Master`) |
| Collision | 3 hulls, `UCX_SM_SnowFlower_Sheath_LOD0_00..02` (throat + upper body, body, chape), 24 vertices each |
| Sockets | `Holster`, `Mouth` (the draw axis), `BeltMount`, all via the `.sockets.json` sidecar |
| Pipeline | `Scripts/pipeline/export_fbx.py --kind static`. `qa_check` **82 of 82 pass** (budget 16k, texel target 80 px/cm +-25 %, UV1 required) |
| Unreal 5.8.3 | **22 of 22 gates** on the exact bytes, one fresh commandlet at a time, 0 warning or error lines, none left running. This includes an in-engine gate: the sword's sockets carried through the sheath's `Holster` land where the Blender fit test put them (max difference 0.0001 cm) |
| Frozen items | Unchanged by this job. The paper bomb changed at 20:35-20:43, from another agent's work (section 9) |

FBX `e419f174bbfb98309b819df37fcc8faa812871e8dd0bf16d1e28826d2736a9bb`, sidecar `3eb2b652...3f87`.

## 1. Where things are

| What | Path |
|---|---|
| Game blend (LOD group, hulls, sockets) | `Assets/SnowFlower/SnowFlower_Sheath.blend` |
| High-poly (bake source) | `WorkFiles/SnowFlower/v4/SnowFlower_Sheath_HighPoly.blend` |
| Exports | `Exports/SnowFlower/v4/SM_SnowFlower_Sheath.fbx`, `.sockets.json`, `Textures/T_SnowFlower_Sheath_*` (4 PNGs), `README_Sheath.md` |
| Build scripts | `Scripts/SnowFlower/v4/build_sheath.py` (stages fit, geo, bake, maps, game, export), `run_sheath_all.sh` (everything). Modules `shv4_spec` (all numbers), `shv4_fit`, `shv4_parts`, `shv4_relief`, `shv4_look`, `shv4_stages`, `shv4_verify`, `shv4_render`, `shv4_compare`. The sword's `sfv4_*` modules are reused unchanged |
| Build records | `WorkFiles/SnowFlower/v4/sheath_build/` (`fit/`, `bake/`, logs, `fit_verify.json`, geo/maps/game/export reports), `sheath_report.json` |
| Unreal harness | `WorkFiles/SnowFlower/v4/UnrealCheck_Sheath/`. Run `run_unreal_checks.sh <new path>`. It is an adapted copy of the sword's harness, which is left unchanged |
| Renders | `Renders/SnowFlower/v4/SnowFlower_Sheath_*` (section 7) |

## 2. The fit: the conflict and how it was resolved

The reference sheath is straight and symmetric, and its body tapers 26 %. The shipped v4 blade is a dao: 53.5 mm
wide, with its spine sweeping 9.4 mm toward +X over the last 360 mm.

A coaxial straight sheath of the exact reference outline cannot hold it. On the shipped vertices of all three sword
LODs, the best margin is **-3.5 mm**, with 1.2 mm walls and 0.6 mm clearance (`fit/fit.json`, `no_tilt_best`).

The spec's fallbacks were to bow the sheath (visible), lengthen it, or hide the blade. This build does none of those.
It takes a fourth option: the sword is **seated with a 0.6 degree tilt** about Y, and the `Holster` socket carries that
rotation. The tip, which sweeps toward +X, swings back to the sheath axis. The outer outline stays **exactly the
reference**.

- **Search.** Tilts from -1.2 to 0 degrees in 0.05 steps, times lateral offsets. The rule is the smallest tilt that
  leaves 0.25 mm beyond wall + clearance, then the most centred guard. The pick is -0.60 degrees with t_x 1.0 mm. The
  guard sits **0.35 mm** off the sheath axis at the mouth, and the pommel is about 3.6 mm off the extended axis. Both
  are invisible.
- **Seat depth.** The lowest hilt vertex (the guard's pendant leaves) is 0.40 mm above the mouth plane. The blade tip
  then rests at reference **row 1357**, in the widest part of the chape and 138 mm above the point.
- **Cavity.** Every vertex of all three sword LODs below the mouth, **swept along the sword's own axis** out of the
  mouth, plus 0.6 mm clearance. It is a 16-sided support polygon per station, with knots lifted until every chord
  covers the dense support (`shv4_fit.py`). A straight draw is therefore clean by construction, and verified.
- **Stations.** LOD0 has 47 stations, LOD1 24 and LOD2 13. The minimum lateral wall is **1.49 / 1.49 / 1.33 mm**, at
  row ~1245 just above the chape.
- **Hidden widening.** Under the throat, the hidden lacquer core is widened by 1.5 mm per side (rows 31-60, fading to
  zero by row 140) so the mouth can pass the blade. The visible body keeps the reference width.

**Measured on the exported FBX bytes of both assets** (`shv4_verify.py --mode shipped`, `fit_verify.json`). The sword is
placed from the Holster socket as written in the exported sidecar, never from the build's own numbers.

| Check | Result (all 9 LOD pairings) |
|---|---|
| Intersecting triangles, sword vs sheath | **0** |
| Min clearance, blade vertex to sheath surface | 0.568 mm (LOD0 pairings) - 0.600 mm |
| Min clearance, hilt to sheath | 0.716 mm |
| Enclosure (rays +-X, +-Y from each blade vertex hit a cavity wall that faces them) | 0 failures |
| Straight draw, 95 steps of 10 mm | 0 intersections at any step (LOD0/0, 1/1, 2/2) |
| Holster matrix from the exported sidecar vs the fit | 0.0004 mm |

The X-ray section sheet (`SnowFlower_Sheath_fit_sections.png` / `.json`) cuts the shipped meshes at 7 stations. The
minimum blade-to-sheath clearance there is 0.51-0.83 mm.

## 3. Match to the reference (measured on renders of the SHIPPED asset)

The front view is orthographic on the reference's own pixel grid (0.687 mm/px, mouth at row 31, axis at x 505.5,
1024 x 1536). It is rendered from the exported FBX with the exported PNGs (`shv4_compare.py`,
`sheath_compare_metrics.json`).

| Zone | Mean width difference (ours - reference) | Note |
|---|---|---|
| Collar (rows 31-40) | +53 px (+36 mm) | **DESIGNED**, forced. The reference's 44 mm collar cannot pass a 53.5 mm blade: ours is 73.7 mm. Hidden under the 118 x 63 mm guard when sheathed |
| Throat (41-167) | -4.8 px (mean abs 5.8) | The tier maxima are hit exactly (112/117/147/115/102 px). The notches between the designed plate lobes are narrower than the reference's |
| Upper body (169-283) | +0.4 px | |
| Band (284-321) | -0.6 px (mean abs 4.2) | |
| Body (322-1249) | +0.05 px, max 2 px | |
| Chape (1250-1496) | +0.5 px, max 6 px | |

- **Overall.** Length 1465 vs 1467 px. IoU 0.958. The centre line is straight: drift 0.0 px (reference -1.5 px).
- **Tone** (display luminance, same pixels on both).
  - Lacquer p5/p50/p95: 0.125 / 0.172 / 0.253, against the reference's 0.097 / 0.194 / 0.307. The median is within the
    spec tolerance of +-0.03. Our mottling has less contrast than the reference.
  - Metal p50: 0.63 against 0.47. Our frames and petals render brighter.

**By eye** (`SnowFlower_Sheath_RefView_vs_Reference.png` and the four `Detail_*_vs_Reference.png`):

- **What matches:** the layout, the proportions, the faceted body, the vine path and its three blossom clusters, the
  band and the chape.
- **Throat:** the reference's plates are sculpted, cupped leaves stacked in real depth. Ours are thick bevelled silver
  frames with dark insets, **baked** onto a solid collar whose silhouette follows the plate outlines. They read
  correctly face-on but flatter at an angle. The frames on the flange lobes wobble in close-ups.
- **Blossoms:** ours are a little smaller and less cupped than the reference's pearl blossoms. The fitting blossoms'
  proxies show a thin dark rim at close range.
- **Lacquer veins:** more line-like than the reference's soft clouds.

## 4. What was built

**Body.** A faceted lacquer core in the spec's flattened octagon:

- front face 0.51 of the width, chamfers, narrow side faces;
- depth DESIGNED at 22 mm, thinning to 17 mm;
- one closed hollow shell (outer + swept cavity + mouth annulus) from the mouth to row 1266, where the chape takes over
  the cavity.

**Throat** (rows 31-167). A closed ring solid whose per-row front-view width is the union of the 8 DESIGNED plate
outlines placed on the spec's measured tips. On it, baked:

- thick silver frames with dark lacquer insets, stacked in 3 layers;
- beads at the collar and sleeve;
- thorn filigree;
- the 41 mm blossom, one petal up: a low-poly proxy plus the kept revision-3 flower construction in the bake.

**Mid band** (rows 284-317). Two rings, and a dark frieze with a running silver leaf scroll whose pointed ends reach
117 px. A 30 mm blossom sits on the front.

**Chape** (rows 1262-1496):

- the lancet frame through which the vine enters, the 37 mm blossom, upper, lateral, lower-lateral and central plates;
- the ogive with a silver outer lancet around a dark inner lancet;
- it carries the cavity's last 70 mm and closes to the point.

**Vine** (front face only). The measured stem path is on the core surface, 1.12 x the measured widths. It is LOD0/LOD1
geometry and baked into the body for LOD2. It carries:

- the second twining stem, twigs;
- 18 buds, 2 teardrop pods and 6 small leaves;
- the 11 measured blossoms, as proxies at LOD0 (the large ones at LOD1) and baked everywhere.

The etched twigs on the chamfers are albedo only. The back face is plain marbled lacquer, and the fittings continue
round it as plain plates. That back is **DESIGNED**, because the reference shows only the front.

**Materials in the bake:**

| Material | Values |
|---|---|
| Lacquer | numpy-painted marble, cool blue-grey black, lengthwise veins (2 % strong vein cover), roughness ~0.2, dielectric |
| Silver | metallic, base 0.60 |
| Pearl petals and buds | dielectric white 0.74, roughness 0.22 |
| Dark insets | dielectric |

## 5. Game engineering

| Item | Detail |
|---|---|
| LODs | LOD0: body + cavity 3,584, throat 1,904, band 648, chape 880, stem 2,496, blossoms 1,400. LOD1: 16-point body ring, coarser cavity and fittings, 4-sided stem, large blossoms only. LOD2: 10-point body, 14-point fittings, fitting blossoms only, vine baked. All LODs share one set of parametric UV islands (no transfer). Screen sizes 1.0 / 0.5 / 0.25, verified in Unreal |
| UVs | UV0: one 4096 atlas, 89 px/cm visible. Hidden interior islands (cavity, fitting inner walls, the core under the fittings) are packed at 6 %, so qa's aggregate is 64.7 px/cm against the documented 80 +-25 % target. UV1: a separate non-overlapping pack; Unreal regenerates its lightmap into channel 1 |
| Tint | The lacquer Detail is normalised luminance over the lacquer texels, in the same convention as the sword's wrap. The silver uses `M_Steel_Master`'s Steel Tint. **Not yet wired** into `Scripts/unreal/materials`: that is the Finalise phase |
| Collision | Convex hulls around the LOD0 vertices. The engine round trip shows every LOD0 vertex inside a hull (worst -0.0019 cm, inside). The hulls are solid, so make the sword NoCollision or query-only while sheathed |
| Sockets | See `Exports/SnowFlower/v4/README_Sheath.md`. Holster (0.10, 0, -31.66) cm with pitch 0.6; Mouth (-0.035, 0, -18.76) cm with pitch 0.6, **draw axis = its -Z**; BeltMount (0, -1.34, 0) cm at the band's back face. The pivot is the band centre on the axis |
| Mass | 0.7 kg for physics (study estimate) |

## 6. Unreal verification (UE 5.8.3, `/Game/SwordCheck/SnowFlowerSheath_0926a`)

The run went: Blender FBX count, then pass 1 (sheath **and** the shipped sword imported with their sidecars, one save
each), texture import (all 11 PNGs in the folder), ORM composite, texture verify, pass 2 (fresh reload + gates),
pass 3 (Unreal's own FBX export), Blender round trip, UV1 overlap, summary.

All **22 gates** pass:

- 3 LODs, with triangle counts equal in Blender, the FBX and Unreal;
- 3 hulls;
- 3 sockets at scale 1, outered to the asset;
- bounds 10.10 x 3.16 x 100.65 cm;
- screen sizes from the sidecar;
- lightmap index 1 on every LOD;
- slots Lacquer/Silver;
- Nanite off;
- texture flags persisted (N flip-green OFF, full mips, ORM composite);
- hulls contain LOD0;
- round-trip triangles and positions exact;
- zero UV1 overlap;
- the same bytes everywhere, and the sword bytes are the shipped v4 sword;
- **the Holster gate**: in-engine socket composition equals the Blender placement, 0.0001 cm.

`UnrealCheck_Sheath/verification_summary.json`.

## 7. Renders (`Renders/SnowFlower/v4/`, all from the exported FBX + exported PNGs)

| Group | Files |
|---|---|
| Reference view | `SnowFlower_Sheath_RefView_vs_Reference.png` (reference, ours, silhouette overlay), `_ref_front/_back/_side.png` |
| Fittings | `SnowFlower_Sheath_Detail_{Throat,Band,Chape,Vine}_vs_Reference.png` (reference crop 4x next to our 4x orthographic render), `_persp_{throat,band,chape}.png` |
| Fit | `_fit_front.png`, `_fit_side.png`, `_fit_hero.png` (sword sheathed via Holster), `_fit_cutaway_{full,mouth,tip,mouth_persp}.png` (front half removed), `_fit_sections.png/.json` (X-ray sections), `_fit_verify.json` |
| Gallery | `_hero.png`, `_back_hero.png`, `_wire.png`, `_lod_strip.png` |

## 8. What still differs, and open decisions

1. **The seat tilt of 0.6 degrees** is a design decision that keeps the reference outline exact. Alternatives:
   - a straight blade (sword `SWEEP_SCALE` 0) makes a coaxial fit possible;
   - widen the lower body by about 3.5 mm per side (visible);
   - bow the sheath.
2. **The collar** is 73.7 mm against the reference's 44 mm. This is forced by the blade and hidden when sheathed.
3. **Throat sculpt.** The plates are baked frames on a collar solid, not modelled cupped leaves. Modelled plates at
   LOD0 would be the next quality step, at an estimated +3-5k triangles.
4. The lacquer veins are more line-like than the reference's soft clouds. The metal renders brighter (p50 0.63 vs
   0.47); that is a lighting and albedo tuning question.
5. **Not in the reference, so DESIGNED:** the back face (plain lacquer with plain plates), the depth and section, the
   mouth interior and the cavity, and the belt hardware (socket only).
6. **Materials not wired into the pack system** yet: the Finalise phase.
7. **Not tested:** in-hand and draw animations, the character hip socket, mobile and Substrate.
8. **Overall length** follows the sword's 1256 mm, which is still unconfirmed against the character.

## 9. Integrity

- **Revision 3 and the v4 sword are unchanged:** 94 SnowFlower files were hashed at the start, and
  `sha256sum -c` passes at the end (`sheath_build/regression/snowflower_sha256_at_sheath_start.txt`).
- **Frozen exports.** `check_exports_frozen.sh` gave 61/63 at the start (paper bomb FBX and README already differed)
  and 57/63 at the end. The 4 further diffs are `Exports/PaperBomb/Textures/*.png`, together with the paper bomb FBX,
  `Assets/PaperBomb.blend` and its renders.
  - These changed at 20:35-20:43, together with `Scripts/props/build_paper_bomb.py` and two new paper-bomb library
    files: **another agent's paper-bomb pass**.
  - No sheath script references those paths.
  - Everything else in the fan regression is identical: 214 frozen, 1296 materials, 68 fan (`regression/`).
- **A slip, corrected.** A development preview with a relative output path wrote 4 PNGs to `C:\dev\`. They were moved
  into `sheath_build/dev/` and the folder removed. All later scripts use absolute paths.
- **Out of bounds.** No JinMuWon, MetaHuman or BlackCloak file was opened. No other process was touched. Unreal ran one
  commandlet at a time, and none is left running.

## 10. IP

The user states the Snow Flower design is **original**. Only the name was inspired by a manhwa, and the user
considers that name generic. Asset names are clean: the `qa_check` deny
list passes.
