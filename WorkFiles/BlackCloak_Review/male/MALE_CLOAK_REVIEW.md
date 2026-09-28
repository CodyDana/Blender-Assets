# Black cloak on the male player: review against your reference

Date: 2026-09-27. Read-only review. Nothing was rebuilt or changed in DemoGame_1 or in any protected folder.

- **Under review:** `/Game/Ninja/Cloak/SKM_BlackCloak_MH`, the cloak MH_PlayerDefault wears in game. Source FBX sha fb8d35a2.
- **Reference:** `References/BlackCloak/blackcloak.png`, your photo.
- **Contact sheet:** `WorkFiles/BlackCloak_Review/male/MALE_CLOAK_contact_sheet.png`. It has three parts:
  - Row 1: the reference, our cloak, and our cloak on the male.
  - Rows 2-3: six blind pairs. Each side is labelled REF or OURS after judging, found by matching pixels against the reference.
  - Row 4: in-game PIE shots. PIE (Play-In-Editor) means the game running inside the editor.
- **Machine summary:** `male_review_summary.json`.

Glossary for terms used below:
- **IoU:** how much two silhouettes overlap. 1.0 means identical.
- **SKM:** the skeletal mesh asset in Unreal.
- **Chaos Cloth:** Unreal's cloth simulation.
- **Sim section:** the part of the cloak that is simulated as cloth.
- **AnimDrive / MaxDistance:** cloth settings. AnimDrive pulls the cloth back toward its modelled shape. MaxDistance caps how far each vertex may move away from that shape.
- **Slub:** the irregular, thick-and-thin yarn look of the linen/wool in your photo.

## Short answer

- **It does not match your reference, and it cannot be patched into an exact match.** A blind judge picked our copy in 20 of 20 pairs (18 of them with confidence). A pass would be 13 or fewer.
- **The rough outline is close.** Silhouette IoU is 0.920 raw and 0.941 after best alignment. This holds only in the still bind pose, before the cloth moves.
- **Almost everything that gives your cloak its character is wrong or missing:**
  - hem
  - collar wraps
  - clasp
  - layered front
  - fray and rolled edges
  - fabric grain
  - tone
- **Worn in game it is worse:**
  - It covers his face to just under the eyes.
  - His thighs and white underwear show through the front.
  - His hands come out through the wings.
  - The cloth collapses into a narrow column at idle and flies like a flat board or loose ribbons in motion.
- **Recommendation: option D, in two stages.** Nothing starts until you say go.
  - Stage 1: cheap surface fixes (tone, grain, clasp). About 5-7 h.
  - Stage 2: re-make the wool as flat pattern pieces sewn and draped on the male in Blender 5.2. About 30-40 h.
  - Stage 2 is the only path that can reach "exact".

## Were the captures good?

Both captures worked.

**Unreal (engine).** A byte-exact copy of the game assets, in a scratch project with the game's renderer settings.
- Straight-on 100 mm camera, studio lit, rest pose.
- Also a Simulate-In-Editor cloth run (cloth left to settle).
- Folder: `male/unreal/`.

**Blender (Cycles).** The same FBX, re-bound to the male's skeleton and matched to within 5e-7 m.
- The game's material graph was reproduced.
- The view transform was Standard, calibrated so that a white card reads 0.90.
- Folder: `male/blender/`.

**Limits to keep in mind:**
- **The two captures disagree on brightness** by about 1.8x in linear light on the same asset (UE mean 0.00476 vs Blender 0.00873).
  - The UE capture had GI (bounce light) off, so the white room added no bounce.
  - Only the Blender capture is calibrated to white, so tone targets come from Blender.
- **The Blender camera fit settled on a yaw of -18 degrees.** That shifted clasp and wing positions by up to 28 px. Several position claims made from it were wrong (see the appendix). Positions are judged from the straight-on UE capture.
- **Nobody has measured the actual in-game idle** (arms down, cloth settled). The only settled-cloth number (IoU 0.797) comes from the A-pose with the arms outside the cloak. The game idle in `final/a02_idle_front_after_3s.png` and `b01_front.png` is an even narrower column, so expect it to score below 0.80.

## 1. How the male's version compares with the reference

### Blind test

- **Result:** 20 of 20 correct, 18 of them confident. Pass mark: 13 or fewer.
- **Our side used the best case:** the UE rest-pose capture, aligned to the reference (IoU 0.94) and exposure-matched so both garment medians sit at 31.2 sRGB.
- **Fairness:** a fairness check found only small staging tells, a grey floor line and a crisper render. **None of the judge's tells were about staging.**
- **Files:** pairs are in `male/blind/`; the parameters are in `male/blind_tools/blind_params.json`.

The judge's recurring tells, most telling first:
1. The hem breaks into square-cut vertical strips with gaps and blunt stub ends. The reference has one continuous, flared, staggered hem that pools.
2. The collar is a cone of evenly stacked horizontal rings with a clean top rim. The reference has crossing diagonal wrap folds and a visible dark interior.
3. The clasp is a thin silver wire ring with a diagonal pin. The reference has a thick, flat, dark oval ring with a strap and fabric gathered into it.
4. There is no fray and no loose threads. Our edges are knife-thin and clean, with stair-step notches where panels meet.
5. The surface shows a repeating wavy, directional ripple. The reference has irregular slubby linen/wool speckle.
6. The shading is flat and grey-lit, with hard black wedges between layers. The mantle reads as one rigid sheet with a square corner.
7. The sides of the silhouette are blocky and the hem is fragmented.

Four of these seven are geometry: hem, collar, card edges and blocky outline. Surface work cannot remove them.

### Key numbers

| Measure | Reference | Ours (UE rest) | Ours (Blender) | Notes |
|---|---|---|---|---|
| Silhouette IoU | 1 | 0.920 raw / 0.941 aligned | 0.912 | The original source sculpt scored 0.934 in the 2026-09-26 review. The male fit is the same shape, warped. |
| Silhouette IoU, cloth settled | 1 | 0.797 raw / 0.813 aligned | - | A-pose settle. The real game idle is narrower. |
| Hem band IoU (best alignment) | 1 | 0.727 | 0.694 | Worst band |
| Collar band IoU | 1 | 0.84-0.90 | 0.85 | |
| Hem jumps of 8 px or more | 4 | 12 | 7 | |
| Hem range (px) | 34 | 76 | 55 | |
| Collar wrap edges | 8 at 8.6 px spacing | 4 at 11 px | 3 at 16.8 px | |
| Clasp band thickness (px) | about 4, flat and dark | 2.5, round and bright | 3.4 | |
| Folds gathered around the clasp (r = 18/26/34 px) | 23/21/24 | 12/14/21 | 9/7/12 | |
| Long diagonal mantle edge, mean error | - | 3.2 px | 18.9 px (yaw) | Our best element |
| Garment brightness p50 (sRGB) | 31 | 15.5 (under-lit) | 23.7 (calibrated) | About 1.5x linear too dark |
| Fabric grain anisotropy (1 = no direction) | 1.5-3.0 | 2.1-6.3 | 2.2-33 | Ours is directional streaks, not slub |

### Element by element

These grades apply the verifier's corrections. The earlier gap table reported 5 close / 5 poor. That miscounted its own rows (they held 4 close and 6 poor), and it graded the clasp position "poor" from an alignment artefact. The recount below is 0 exact, 5 close, 7 partial, 5 poor, 2 missing, 2 invented, over 21 elements.

| Element | Grade | What we see (evidence) |
|---|---|---|
| Overall silhouette (rest pose) | close | IoU 0.920 raw, 0.941 aligned. The misses are the collar top, the two lower hem-flare corners and a centre-bottom slit (`verify/vf_overlay_ref_red_UE_blue.png`). |
| Height / width | close | h/w 1.629 vs 1.664, within 2%. Mantle width at y=150: 272 vs 270 px. |
| Clasp position | close | The ring centre is at about (113, 90) vs the reference's (116, 90) at best alignment. The strap and gather above it are missing (see below). |
| Long diagonal mantle edge | close | Mean error 3.2 px, max 8.5, slope 41.6 vs 42.5 degrees. Edge strength is 0.74 vs 0.94. |
| Viewer-right wing corner | close | Extreme point at (409, 380) vs (402, 385). |
| Collar height / top opening | partial | Widths at top+5/15/40/70: 98/100/129/225 vs 91/100/118/203 px, so 9-11% too wide below the top. Only a 3-4 px sliver of the dark interior shows, vs about 20 px. |
| Fabric gathered into the clasp | partial | About half the radial folds (12/14/21 vs 23/21/24). The pleats radiate from a point below the ring instead of being drawn through it. |
| Two short overlap edges | partial | The count is right (2), but they are 3-6x weaker (strength 0.30/0.23 vs 0.85/0.93). They are thin shelves with no shadow line. |
| Viewer-left wing | partial | The corner position is right (2, 330 vs 10, 329). It is one flat panel instead of 3-4 cascading pointed drops (layer edges 0/2/1 vs 2/7/4). |
| Front panels | partial | 3-4 edges per row vs 7-10 in the reference (`gap/logs/gap_measurements.json`). |
| Inner opening | partial | Dark, but it is a slit between strips. On the male, legs and underwear show where the reference has a closed dark cavity. |
| Colour / value | partial | p50 is 23.7 vs 31 sRGB in the calibrated capture, with flat contrast. The albedo texture median is 25/255, about 1% reflectance. |
| Collar wrap folds | poor | 3-4 stacked horizontal rings vs 8 sagging wraps with a crossing diagonal (`gap/out/crop_collar.png`). |
| Clasp ring | poor | A thin round polished torus, 5.8 x 1.3 x 6.0 cm. The reference ring is flat, dark and wider than tall (about 6.8 x 6.0 cm). |
| Hem | poor | Square-cut strips with slits. 12 jumps vs 4. No flare at either lower corner: at x=30/385 the reference reaches y 629/628, ours stops at 401/405. It hangs 1-11 cm off the floor, with no pooling. |
| Rolled edges | poor | Single-sheet cuts. `build_cloak_mh.py:86` strips the source's SOLIDIFY. |
| Fabric grain | poor | Directional wormy streaks from an untiled 1 mm weave (repeat 66-87 cm) vs isotropic slub at 1-4 cm. Tiling the existing weave makes it flatter, not better. |
| Strap tab on the clasp | missing | The only leather piece (3.1 x 1.0 x 6.0 cm) sits inside the ring (`blender/logs/clasp_probe.json`). |
| Fray and loose threads | missing | Clean polygon cuts everywhere (`blender/compare/e_closeup_wing_viewer_left.png`, `e_closeup_hem.png`). |
| Clasp pin bar | invented | A diagonal pin crosses the ring. The reference ring is filled with fabric. |
| Shoulder horn / notch | invented | A white notch between the collar and the viewer-right mantle (62 background px vs 6). |

## 2. Quality as worn in game

- **Face coverage.** The cowl front reaches 173.8 cm on a 186.1 cm male, 1.3 cm under his eyes and 3.5 cm above his nose tip (`final/b05_close.png`).
  - An exact copy scaled to him would also reach about eye level (collar top about 178.8 cm).
  - The reference cowl is soft and would slump under a real chin. Ours is a rigid skinned tube.
  - So this is partly a design decision, not only a defect.
- **Front opening.** His thighs and white underwear show through the central slit, at rest and in every PIE pose (`b01_front.png`, `a17_seals_b.png`, `a15_flip_land.png`).
  - The UE body capture has 2,315 skin px in the hem band.
  - Blender counts 4,318 leg px in the reference view.
- **Arms and hands.** 69 cloak vertices sit more than 1 mm inside the arms at rest (45 more than 1 cm, deepest 4.39 cm). With the arms down, 27 are still inside.
  - Hands exit through the wings (`b01`, `a02`, `b03`).
  - The cloak is weighted to 6 spine and head bones only (spine_03 up to head), so it never follows the arms.
  - There is an open slot down his left side (`blender/renders/d_side_l_body_down_game.png`).
- **Cloth behaviour (blocker).** `make_cloth_mh.py:22-49` sets MaxDistance 120 cm, full pin only above 136 cm, AnimDrive 0 and self-collision off.
  - At idle the wings collapse into a narrow column.
  - In run and sprint the cape stands off as a flat board (`a05`, `a09`).
  - In the flip the square hem strips whip like ribbons (`a13`-`a15`).
  - Prone opens a hole with skin showing (`a25`).
  - Settled silhouette IoU falls to 0.797.
  - Earlier tuning already tried a global AnimDrive of 0.3 and MaxDistance 30. Both gave a "rigid board" (`make_cloth_mh.py:22-24`, `:45`). Global knobs will not fix it.
- **Mesh quality of the sim section.**
  - 1,731 of its 5,991 triangles (29%) are slivers with an angle under 5 degrees.
  - There are 707 self-intersecting face pairs in the sim section (1,002 across all wool, 2,432 between pieces in the fit).
  - That is why self-collision has to stay off.
- **Fabric at game distance.** At game distance it reads as a flat black shape.
  - The albedo is about 1%.
  - The weave averages out to nothing.
  - Up close, the untiled weave shows as stretched, wormy crepe.
- **Length.** 177.2 cm on a 186.1 cm male is fine. The hem shape is the problem, not the length.
- **Performance note.** There is only one LOD (level of detail) at 28,378 tris for a character usually seen at a distance.

## 3. Can it reach an exact match, and how?

**Repairing this mesh cannot reach an exact match.** The ChatGPT/Codex generator built every wool piece as a formula, not as cloth:
- Each piece is a perfect quad grid.
- The nine front pieces are traced outlines with made-up depth. That makes them pure height fields: 0.000 fold-over, where real draped cloth measures 0.35.
- The collar is lofted between horizontal rings.
- The hem strips are the straight-cut ends of separate panels.
- The file itself says: "Not an exact reconstruction."

Patching that structure is the pattern that did not converge on the smoke bomb.

**Options:**

| Option | Reaches | Cost | Risk |
|---|---|---|---|
| A. Surface only: tone, grain texture, new clasp | Colour and clasp near exact, grain close. Hem, collar, layers, fray, legs showing and cloth collapse unchanged. The judge would still win. | 5-7 h | Low technical risk, but it cannot meet "exact" |
| B. Geometry repair on the current fit | Perhaps IoU 0.93-0.95, a continuous but straight hem, a more diagonal collar. Still relief cards, still no self-collision. | 14-24 h | High: this is the smoke-bomb pattern, and most of the work is lost if C follows |
| C. Re-drape from flat pattern pieces on the male in Blender 5.2 cloth | Every element becomes reachable: flared pooling hem, wrapped cowl, real layers, closed dark lining, rolled edges, fray, a stable in-game drape | 30-40 h | Medium: multi-layer sewing is fiddly, and there is only one front photo |
| **D. A now, then C (recommended)** | Stage 1 lands in about a day. Stage 2 goes to exact. | 35-45 h total | Low, then medium |

**Why C/D is feasible here.** A pilot on this machine draped a 10,421-vertex circle-cut cape over the male in 36 s:
- self-collision on
- 0 vertices inside the body
- a continuous flared hem down to 3 cm off the floor
- 0.35 fold-over

Files: `male/path/renders/path_pilot_drape_*.png` and `path_pilot_drape_report.json`.

Marvelous Designer and CLO are not installed, so the tool is Blender cloth.

**Proposed acceptance targets (untested):**
- silhouette IoU at least 0.96
- every band at least 0.93
- hem jumps of 4 or fewer
- 7-9 collar wrap edges
- blind judge at 13/20 or fewer
- measured at the actual in-game idle, not only the rest pose

Write each target as a local relation, not as a centimetre move. For example: "the ring sits 15-20 px below the shoulder line, with a strap above it", or a collar-width ratio. Absolute centimetre moves proved to depend on the alignment.

**Keep the old version safe:**
- Ship the result as `SKM_BlackCloak_MH_v2` next to the current mesh, with a toggle.
- Build it on a new recipe. Do not change `Assets/BlackCloak.blend` (bd42c71e): its garment regression is bit-exact and pinned to it.

## 4. Ranked fix list toward an exact match on the male

Every item ships through DemoGame_1 (a new SKM, cloth data or material), so every one touches the character track. Costs are estimates.

| # | Fix | Severity | Why | Cost | Character track |
|---|---|---|---|---|---|
| 1 | Rebuild the in-game cloth. Clean uniform sim mesh (1.5-2.5 cm edges, layers not intersecting). Per-vertex AnimDrive and MaxDistance masks. Skin the wings and shoulders to the clavicle and upper-arm bones. Turn self-collision on. Accept at the measured game idle. | blocker | Idle collapses to a column. Board and ribbons in motion. Settled IoU 0.797. Global knob changes already failed (G01, VF-M1, M4, M5, G15). | 8-12 h after the re-drape (needs #2-#4 geometry) | yes: new cloth data, SKM_v2, DemoGame_1 scripts |
| 2 | Continuous circle-cut hem that flares at both lower corners and pools 2-4 cm onto the floor. No strip cuts. | major | Blind tell #1. Hem band IoU 0.73. 12 jumps vs 4 (G02, BM-01, U3, M6). | Part of the re-drape, about 8 h | yes |
| 3 | Cowl re-draped as a bias band with about 8 sagging wraps, one crossing diagonal, an open rolled top and a dark interior. Height per your decision. | major | Blind tell #2. 3-4 rings vs 8 wraps. It also sets face coverage (G03, U4, BM-02, G04). | 6-8 h | yes |
| 4 | Closed front: 3-4 layered front leaves plus a dark lining panel. | major | Legs and underwear show. Front edges 3-4 vs 7-10 (G05, BM-06, G12, U8). | 4-6 h in the re-drape | yes. Trousers on the player would be a separate character-track item. |
| 5 | Tone: base colour median about 31-38/255 sRGB (0.015-0.02 linear), slightly warm, plus a sheen/fuzz lobe. Check it in a game-lit PIE shot. | major | About 1.5x too dark in linear. It reads as a flat black shape in game (G07, BM-05, U1 adjusted, M3). | about 1 h (stage 1) | yes: texture/material in DemoGame_1 |
| 6 | Fabric: a new isotropic slub/heather texture (1-4 cm mottling plus fine noise, no directional weave) with a UV or world-scale parameter in M_BlackCloak. Use true-scale UVs on the re-drape. | major | Blind tell #5. Directional streaks vs slub (G06, BM-04, U2 adjusted). | 3-4 h (stage 1) | yes |
| 7 | Clasp: a thick flat dark oval ring (band about 1.1 cm, roughness 0.55 or more), a strap tab rising 15-20 px above it to the shoulder line, no pin, fabric gathered through the ring. Keep the ring where it is. | major | Blind tell #3 (G08, U5, BM-03, BM-15). | 3-4 h (stage 1). The gather is finished in the re-drape. | yes: FBX rebuild of the skinned slots |
| 8 | Edge finish: 4-8 mm rolled edges on every layer, plus alpha fray cards and a few loose threads on the hem and wing tips. | major | Blind tells #4 and #6 (G09, BM-07, BM-08, U6). | 4-6 h | yes |
| 9 | Viewer-left wing as 3-4 staggered pointed drops. | major | Layer edges 0/2/1 vs 2/7/4 (G10, BM-10). | 2-3 h in the re-drape | yes |
| 10 | Arm clearance and hand exits: arm openings under the wing layers, 1 cm or more clearance, close the left side slot, arm capsules in the cloth collision. | major | 69 verts inside the arms at rest, hands through the wings (G11, BM-11, U9, BM-12). | 2-4 h | yes |
| 11 | Smooth the viewer-right shoulder into the collar (remove the horn/notch). | minor | An invented shape (G13, BM-09). | Free in the re-drape | yes |
| 12 | Add 2-3 LODs, with cloth off or a proxy at distance. | info | Performance, not look (M7). | 1-2 h after the rebuild | yes |

## 5. Decisions you need to make

1. **Go / no-go and which path.**
   - D is recommended: Stage 1 at about 5-7 h, then Stage 2 at about 30-40 h.
   - A alone will not look like your photo.
   - Nothing starts until you say go.
2. **Does "exact" include covering his face to eye level?** An exact copy does reach eye level on this 186 cm male. The alternatives:
   - Lower the cowl front 6-10 cm to the chin or mouth.
   - Let it slump softly under the chin.
3. **The back.** Your photo has no back view, so the back will be a design interpretation. Is that OK, or do you have a back reference?
4. **Under-layer.** Is the lining panel enough, or should the player also get trousers (a character-track item)?
5. **Stage 2 budget.** About 12-16 workflow agent runs over 4-5 rounds. It warrants ultracode if your usage cap allows. Otherwise plan it as normal workflow rounds that stop early when a round clearly fails.
6. **Confirm the safety rails:**
   - Build as a new recipe and `SKM_BlackCloak_MH_v2` behind a toggle.
   - Leave `Assets/BlackCloak.blend` and its bit-exact regression frozen.
7. **Confirm the acceptance bar:**
   - IoU at least 0.96, bands at least 0.93, blind 13/20 or fewer.
   - Measured on the male at the game idle, as well as in the product-shot view.

## Appendix A: refuted or corrected claims (dropped from the findings)

- **BM-14.** Claim: "the drape is turned 12-20 degrees". Refuted: the straight-on UE capture reaches IoU 0.941 at yaw 0. The -18 degrees came from the Blender fit method, which had no scale or shift freedom plus a floor constraint.
- **G14.** Claim: "mantle 3 cm too wide per side". Refuted: the width at y=150 is 270 (reference) vs 272 (UE), within 1% at best alignment. The +8% came from forcing scale 1.0.
- **BM-02, partly.** Claim: "collar taller, clipped at the top". Refuted: at best alignment the UE collar is slightly shorter than the reference. "Lower it 4-6 cm" is a design choice, not a matching fix.
- **BM-03, G08, BM-13, partly.** Claims: "clasp 7.6 cm too far inboard", "14 px too high", "folds 8 cm inboard". Refuted: these are camera yaw and scale artefacts. The ring is within 3-4 px of the reference. What really differs is the missing strap and gather above it.
- **BM-09, partly.** Claim: "upper silhouette wider". Refuted: shoulder-band IoU is 0.969. The horn/notch is real (minor).
- **BM-10, partly.** Claim: "lower-left flare". Refuted: it appears only in the yawed Blender view. UE has x=39 vs the reference's 41 at y=550.
- **BM-01, numbers only.** The reference hem is scalloped (lowest y 627-656, std 10.6 px), not level (std 1.2). The background inside the outline is 1.5-1.8x the reference's, not 25x. The finding stands, downgraded from blocker to major. The blocker is the in-game cloth (G01).
- **U1 fix value.** Albedo 0.03-0.045 linear was derived from the under-lit UE capture and would overshoot 2-3x. Use 0.015-0.02.
- **U2, partly.** Claim: "grain invisible at full-frame distance". Overstated: the amplitude is similar, but the grain is directional and quantised. A thread-scale weave tiled at 5-10 cm would average out. Slub at 1-4 cm is what is needed.
- **U7 fix.** A global AnimDrive of 0.1-0.3 was already tried and rejected (`make_cloth_mh.py:45`). Only per-vertex masks plus arm skinning will work.
- **G06, numbers only.** The reference anisotropy is 1.5-3.0, not 0.99. The UE "hp_rel 0.108" is inflated by 8-bit steps near black. The conclusion holds.

## Appendix B: severity changes applied

- BM-01: blocker to major.
- BM-09 and BM-13: major to minor.
- U11: to info.
- Clasp position: poor to close in the table.
- U8 stays minor, as the rest-pose part of the major G05.
- Added from the verifier:
  - VF-M1: game-idle silhouette not measured (major).
  - VF-M2: positions depend on the alignment (major, method).
  - VF-M3: tone target inflated (major).
  - VF-M4: 29% sliver triangles (minor).
  - VF-M5: cloth tuning history (minor).
  - VF-M6: missing lower-corner flare (minor).
  - VF-M7: single LOD (info).

## Sources

- **Reference:** `References/BlackCloak/blackcloak.png`
- **UE capture:** `male/unreal/shots/`, `male/unreal/compare/mu_compare.json`, `unreal_review_sheet.png`
- **Blender capture:** `male/blender/renders/`, `male/blender/compare/measurements_male.json`, `male/blender/logs/clearance_by_region.json`, `clasp_probe.json`
- **Gap measurements:** `male/gap/logs/gap_measurements.json`, `gap_measurements2.json`, `male/gap/out/crop_*.png`
- **Verification:** `male/verify/vf_measure.json`, `vf_scene.json`, `vf_crop_*.png`, `vf_overlay_*.png`
- **Path study:** `male/path/logs/path_geom_fit.json`, `male/path/renders/path_pilot_drape_report.json`
- **Blind test:** `male/blind/pair_01..20.png`, `male/blind_tools/blind_params.json`
- **Contact sheet:** `male/report_tools/make_contact_sheet.py`, `contact_sheet_log.json`
- **In game:** `DemoGame_1/Saved/Claude/Shots/metahuman_cloak/final/` (b01, b05, a02, a05, a09, a13-a15, a17, a25)
- **Build scripts (read only):** `DemoGame_1/Tools/Claude/Blender/build_cloak_mh.py`, `Tools/Claude/Cloak/make_cloth_mh.py`
