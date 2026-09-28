# Black Cloak review

Date: 2026-09-26. Read-only review. Nothing was rebuilt or changed.

- **What was reviewed:** the ChatGPT/Codex ("Astra") black cloak. That is Assets/BlackCloak.blend, Exports/BlackCloak/, Exports/BlackCloak_Package.zip, Renders/BlackCloak/ and WorkFiles/BlackCloak/.
- **How:** it was checked against your reference and this project's standards. The character chat's MetaHuman fit (WorkFiles/BlackCloak_MH/, and SKM_BlackCloak_MH in DemoGame_1) was read, not changed.
- **Backup:** the untouched original is in `Backups/BlackCloak_original_2026-09-26/`, with hashes in manifest.json. Assets/BlackCloak.blend still hashes to bd42c71e after the review.
- **Picture:** `BLACK_CLOAK_contact_sheet.png` in this folder. Top row: reference, shipped LOD0, MetaHuman fit. Below: 4 blind pairs.
- **Evidence:** every number below comes from a file in this folder: fidelity/, blind/, engineering/, materials/, character/, unreal/, verify_engineering/, verify_look/.

Every area produced a result: fidelity, engineering, materials, character and Unreal. None came back empty.

## The short answer

- **Look:** the outline is right, but the surface is not. The silhouette overlaps the reference at 93%. A blind judge still picked the copy in **20 of 20** pairs, and a pass needs 13 or fewer.
- **Game use:** the original files are **not usable** for your player. They sit on the wrong skeleton, are rigid, have no cloth setup and are 2.8x over the triangle budget.
- **The version to build on:** the character chat's MetaHuman rebuild of the same cloak (SK_BlackCloak_MH / SKM_BlackCloak_MH) *is* usable. It is on metahuman_base_skel, uses 28,378 triangles and passes every garment gate.
- **New blocker:** since today at 19:07 your player in DemoGame_1 is the **female** MetaHuman, and she does not wear the cloak. It is fitted only to the male body.
- **Colour:** yes, move it onto the pack material system. It is about 1 to 1.5 days of work, and it is not a straight port.
- **Recommendation:** **repair, don't rebuild.** Keep the MetaHuman garment-pipeline version as the base and fix it there. Retire the original exports.

---

## 1. How closely does it match the reference?

**Blind test: 20 of 20 picked correctly, all 20 with confidence. It fails** (a pass needs 13 or fewer). The 20 pairs are in `blind/`. Each pair crops the same reference pixels and scales both sides the same way.

**What matches (measured on the shipped LOD0, BlackCloak.fbx):**
- **Silhouette overlap (IoU)** is 0.934. IoU is the share of the two outlines that coincide. With a stricter mask that drops the floor shadow it is 0.947.
- **Height/width** is 1.683 against the reference's 1.661.
- **Clasp position** is within 2.6 px.
- **Right mantle corner** is within 2 px. The left wing corner is 10 px low.
- **Inner-opening centre** is off by (+2.7, +7.7) px.
- **The MetaHuman fit** hardly changes the look. It overlaps the original at 0.970 and the reference at 0.924.

**What does not match. These are the recurring tells the blind judge used:**
1. **No fabric texture.** The copy is flat near-black with smooth shading, where the reference is a slubby linen/wool weave in a lighter charcoal.
   - Fine-grain strength on flat patches: ours 1.0-4.4%, reference 5.4-15.6%.
   - The base-colour texture only uses sRGB levels 21-31: 11 levels, about 1% albedo.
   - Some of the "flat black mass" came from the dim review lighting. Under the creator's own lighting the fold contrast is close to the reference (std 9.7-11.1 against 11.95). Missing grain is the real defect; the darkness is partly staging.
2. **Hem.** The front panels end in square-cut, leg-like strips with white gaps between them. The reference has one continuous flared, rippled, staggered hem.
   - Background pixels enclosed in the lower hull: ours 6,693, reference 2,641.
   - The median hem is actually 9 px *above* the reference's; only the strip tips hang lower.
3. **No frayed edges.** Ours are razor-clean. The reference is ragged.
4. **No layer thickness.** The mantle edges are knife-cut slits with no rolled edge or shadow line. Edge contrast is 1.3-5.9 against 8.6-12.8.
5. **Collar.** Ours is a straight cone with 4 horizontal rings. The reference is a sagging cowl with 5-6 diagonal wrap folds. The brightness profile shows 6 peaks spaced 15-22 px, against 8 peaks spaced 8-12 px.
6. **Clasp.** Ours is a thin round ring with an invented diagonal pin. The reference has a thick flat oval band with a leather strap tab. There is also a white see-through slit beside it.
7. **Background leaks** through gaps between panels.
8. **No floor contact shadow.** This is staging, not an asset defect.
9. **Soft shading gradients** instead of distinct draped layers. A few edges look rubbery or waxy.

**Smaller shape differences:**
- The right shoulder has a flat shelf with a hard step.
- The diagonal mantle edge runs 8-16 px low over its middle.
- The left wing has one drape with a pinched spike, where the reference has two staggered frayed layers.

**Never compared to the reference:**
- **The in-game cloak.** It is a different, decimated mesh with a different material, and nobody has compared it (LOOK-M1). Its cloth part is where the hems are.
- **The back.** The reference is front-only, but the back is what your third-person camera sees. Only 4 of the 14 fabric pieces reach it. Revision_Back.png shows a flat slab with an invented rectangular yoke flap.

## 2. Is it game-ready in Unreal?

**The original exports (Exports/BlackCloak): no.**

| Check | Original export | MetaHuman build (character chat) |
|---|---|---|
| Skeleton | 152-bone JinMuWon rig. Shares 3 of 342 bone names with metahuman_base_skel (root, pelvis, head). 114 names contain a dot. | metahuman_base_skel, 342/342 names. Bound to the real skeleton within 0.00025 cm (garment_pipeline/ue_runs check). |
| Weights | Rigid: 1 influence per vertex on only 3 bones (spine01 30,726 verts, neck01 10,410, clavicle.R 1,200). | spine_03-05, neck_01/02, head; at most 2 influences. |
| Cloth readiness | No *_Sim section, no PinMask. Panels are closed 1.6 mm double shells. The pin CSV is indexed to the source cages, not to the FBX. | One *_Sim section: 5,991 tris / 3,420 verts, rigid on spine_03-05, PinMask active. |
| Triangles (cloak budget 30k, whole character 160k) | LOD0 84,612 / LOD1 47,088 / LOD2 25,646. Dressed player 206,504. The collar alone is 20,820. | 28,378; dressed player 150,270. |
| Fit on the MH body | 1,370 verts more than 1 mm inside the skin, deepest 6.2 cm. | 0 inside at rest and in 4 test poses (arms excluded by design). Closest gap is 0.25 cm, below the 1 cm rule at the cowl. |
| LODs | Separate files, no LOD group. | 1 LOD only (skeletal LODs are still an open item in the pipeline). |
| Pipeline gates | Skipped. The prefix check was dodged by renaming after export. qa_check fails 65/325 (skeletal) and 71/320 (static). garment_qa fails 13 gates. | Pipeline build passes all gates. The in-game one-off fails 2 core checks: 4 n-gons and the SKM_ prefix. |
| Scale / axes / topology | Correct: 172.1 cm tall, house FBX header, 0 non-manifold edges. | Correct: 177.2 cm tall. |

**Layers pass through each other.** In the exported LOD0, 7,894 triangle pairs intersect between pieces and 470 within pieces. You can see it as blotches on the upper back. The MetaHuman build still has about 1,121 self-intersecting pairs. That is why its cloth runs with self-collision off.

**Cloth mesh quality in the game build:**
- The cloth section was made by cutting the triangle count to 3.7%.
- As a result, 1,731 triangles have an angle under 5 degrees, and edges reach 92 cm.
- In game shots: the cape turns board-like when flipping, a hole shows calf skin when prone, and underwear shows through the front opening.

**UVs:**
- **UV0 is tiling.** It repeats the weave, but at uneven scale: density varies 2.9x between panels (128-371 px/cm). The README claims a uniform metre scale, which is wrong.
- **No unique UV set.** There is nowhere to bake AO or paint a tint mask.
- **The in-game mesh never got the weave tiling (VE-M1).** Its UV0 is about 1.18 UV/m, so the 12.8 cm weave repeat becomes a 43-125 cm repeat per panel. Every fabric judgement made on Exports renders is therefore not what the game draws.

**Textures:**
- **The DirectX normal is correct.** Green is exactly 255 minus the OpenGL map, and the thread-direction test scores 0.992 right against 0.113 wrong.
- **The maps break the pack convention:** _BaseColor / _Normal_DirectX / _Roughness instead of _BC / _ORM / _N, with no ORM, no AO and no Detail map. They are 8-bit RGB 2048 PNGs, power of two and seamless.
- **The weave is 1 mm detail at 160 px/cm,** 31x the house density. By the mip the game actually samples (mip 4-5), the colour varies only 2% and the normal is flat (0.04 degrees). In game it is one flat colour.
- **The game and the pipeline export both ship the OpenGL normal** and flip green on import. It renders correctly, but it breaks the "DirectX on disk" rule.

**Unreal check on the exact exported files.** It ran once, in a fresh UE 5.8.3 project, CloakReview. No other Unreal commandlet was running before either run.
- Scale is right, and the triangle counts are exact.
- The skeleton is the JinMuWon one: 152 bones, 3 names matching.
- With 5.8's default importer (Interchange), the static FBX arrives as **17 separate Nanite meshes**, and the LOD files become 34 more loose meshes. A Fab buyer would get 51 pieces.
- The FBX-embedded materials wire the **OpenGL** normal with the green flip off, so the lighting comes out inverted. Roughness is wired as Phong "shininess" and imports as sRGB colour.
- The standalone DirectX normal imports correctly with no manual step.
- The default import also creates a physics asset on every garment and recomputes normals.
- **Correction to the Unreal agent:** the MetaHuman FBXs *do* carry texture paths. The check missed them because it copied the FBXs without their Textures folder. The root cause is the house exporter (`Scripts/pipeline/export_fbx.py:111`, path_mode RELATIVE), which affects every asset.

## 3. Should the colour option move onto the pack material system?

**Yes.** Today there are three unrelated setups for one garment:
1. **M_Cloak_Recolor + MI_Cloak_Black/Crimson/Navy/Ivory.** These live only in a separate Unreal project, on the obsolete skeleton. Its 64 "passed" checks read parameters only; nothing was ever captured on screen.
2. **DemoGame_1's own M_BlackCloak** has **no colour control**, and its steel MI uses metallic 0.85, which the house rules forbid. So your player has no colour option today.
3. **The .blend materials,** with different values again.

**M_Cloak_Recolor's own faults:**
- Picking white pushes 2.7% of texels to albedo 1.0.
- The picked colour renders about 27% darker on average.
- Black goes to a flat 0.
- There are banding gaps of 6 levels.

**Migration outline:**
1. **Pack chat prerequisites.** These change no other item, and a dump comparison proves it.
   - (a) A two-sided override for MIs. M_Fabric_Master is two_sided false, and single-layer cloth needs two-sided.
   - (b) The "Used with Clothing" usage flag on M_Fabric_Master.
   - (c) A default colour at or above the pack's 0.01 black floor. The cloak's mean is 0.00997, so it would fail the default-exactness gate.
   - (d) A UV tiling parameter, or the UV0 rescale in the build (see VE-M1).
2. **New maps:** T_BlackCloak_Cloth_BC / _ORM / _N (DirectX) plus a full-range greyscale Detail map and a 16-bit Detail16.
   - Regenerate them at slub scale, 2-30 mm, repeating every 0.4-0.5 m, not at the 1 mm weave.
   - Target a mean albedo of about 0.015-0.025 linear. The final value is your look call, made from a matched Unreal capture.
   - Also try the pack's Cloth Sheen switch.
3. **Instances:**
   - MI_BlackCloak_Cloth_Base, with the buyer-facing MI_BlackCloak_Cloth overriding Colour only. It goes on both the cloth and cloth-sim slots.
   - MI_BlackCloak_Clasp_Base with MI_BlackCloak_Clasp on M_Steel_Master. This needs a clasp re-UV and a 512 atlas, because the current clasp UVs are degenerate.
4. **Slot names.** Keep today's four in the game build, so DemoGame only re-points materials. The Fab FBX merges steel and leather into one clasp slot.
5. **Re-verify:** the pack's V0-V3 checks and colour stress tests, plus a back-face and cloth-section render.
6. **DemoGame re-point.** The character chat does this, with your OK: migrate the pack masters in, then re-point the MIs and run a PIE test. PIE is Play In Editor.

**What breaks:**
- **Default look:** it changes on purpose.
- **Colour meaning:** "Colour" now means the average colour, not the brightest yarn, so the Crimson/Navy/Ivory presets need re-deriving.
- **Parameter names change** (CloakColor becomes Colour, and so on). Any Blueprint that sets "CloakColor" silently stops working.
- **Docs:** RECOLOR.md and the README need rewriting.

**Cost:**
- Pack side: 6-9 h.
- Clasp atlas and re-UV: 2-3 h.
- DemoGame re-point: 1-2 h.
- Total: about 1 to 1.5 working days. Then retire M_Cloak_Recolor and the DemoGame-local materials.

## 4. Ranked fix list

The ranking follows your goal: the player's cloak in your game first, a Fab listing second. "Char track" means it touches the character chat's work: DemoGame_1 SKM_BlackCloak_MH, WorkFiles/BlackCloak_MH or the garment regression. Every item marked yes needs your sign-off.

| # | Fix | Severity | Cost | Risk | Char track |
|---|---|---|---|---|---|
| 1 | **Decide which body wears the cloak** (male, female, both). For the female, build her fitting body, then refit, build, set up cloth and test. | Blocker | Decision now; 3-5 h per extra body | Medium: new fit, new cloth tuning | Yes |
| 2 | **Retire the original exports and withdraw BlackCloak_Package.zip.** The zip ships your reference photo (an IP risk), the full source .blend and an old-skeleton Unreal project: 52 files, about 97 MB. Mark BlackCloak_Skeletal*.fbx, M_Cloak_Recolor and export_refined_cloak.py as retired. | Major | 30-60 min | Low | No |
| 3 | **Take a lit Unreal capture of the in-game cloak** (front, 3/4, back; 3 m and 8 m; rest plus a settled cloth frame) before choosing any geometry work. Nobody has seen the real in-game look. | Major | 1-2 h | Low: read-only, in the review project | No (reads its FBX only) |
| 4 | **Fix the in-game weave scale:** a UV tiling parameter, or a UV0 rescale in build_garment. Unify the per-panel UV scale at the same time. | Major | 1-2 h (parameter) or 2-3 h (rebuild + reimport + cloth rebuild) | Low / medium | Yes |
| 5 | **Regenerate the fabric maps at slub scale**, with a slightly lighter albedo (about 0.015-0.025 linear), a Detail map, ORM and a DirectX _N. Judge them in the Unreal capture. | Major | 4-6 h + 2-3 h packing | Low | Yes (the textures the game uses) |
| 6 | **Move the colour option onto M_Fabric_Master / M_Steel_Master,** including the 3 pack prerequisites and the clasp re-UV/atlas. Retire M_Cloak_Recolor. | Major | About 1-1.5 days | Medium: parameter rename breaks any Blueprint using CloakColor | Yes (DemoGame re-point) |
| 7 | **Build a proper cloth sim mesh:** even 3-5 cm triangles, 3-6k tris, separate from the render mesh. This replaces the 3.7% collapse decimation. | Major | 4-8 h | Medium: cloth retune + PIE tests | Yes |
| 8 | **De-intersect the layers** (0.5-1 cm gaps, fixed stacking order), attach the two leaves pinned in mid-air, and fix the cowl clearance (1 cm) and the arm pass-through. | Major | 4-8 h | Medium: refit/build/cloth rerun | Yes |
| 9 | **Close the front opening:** a dark inner layer / under-robe, or body hiding. Today underwear and thigh show through. | Major | 4-10 h incl. retune | Medium | Yes |
| 10 | **Fidelity pass on the big tells:** one continuous flared, staggered hem with no gaps (lengthen most of it, trim only the longest tips), and a wrapped cowl with diagonal folds. | Major | 7-13 h | Medium: every geometry change reruns refit/build/cloth | Yes |
| 11 | **Design the back** (no reference exists): a continuous mantle, collar wraps that continue around, and no floating yoke. | Major | Decision + 3-5 h | Medium | Yes |
| 12 | **Smaller fidelity fixes:** clasp (thick oval band, strap tab, no pin, close the slit), shoulder shelf, mantle edge 8-16 px low, rolled layer edges, left-wing second layer, fray (alpha edge strip). | Minor | 5-8 h | Low-medium | Yes |
| 13 | **Switch the game to the pipeline build SK_BlackCloak_MH** (triangulated, correct prefix) at the next rebuild. | Minor | 1-2 h | Medium: reimport wipes the cloth data | Yes |
| 14 | **House exporter:** strip texture paths from FBX (export_fbx path_mode). Garment imports turn off physics-asset creation and normal recompute. | Minor | 1-1.5 h + tests | Low, but house-wide | Yes (the garment export uses it) |
| 15 | **Add skeletal LODs to build_garment** (about 28k, 14k, 7k; cloth only on LOD0). | Major for Fab, optional for the game | 2-4 h | Low | Yes |
| 16 | **Fab static version (only if you want one):** one FBX with a LOD group, UCX collision or a stated reason for none, a clean UV1, SM_ names and no embedded materials. | Minor | 3-5 h | Low | No |
| 17 | **Tooling and docs:** qa_check also checks the total triangle count; README claims corrected; the stale cloth table in Outfit_Pipeline.md updated (the live value is MaxDistance 120, not 30). | Minor | About 1.5 h | Low | Outfit_Pipeline.md only (your DemoGame repo) |

**Order of work.**
- **Items 1-3 first:** a decision, a cleanup and a look check.
- **Then 4-6:** the material track. These are safe texture and material work.
- **Then 7-12:** one combined geometry pass. Each geometry change forces a refit, build, reimport and cloth rebuild, so batch them.
- **Rough total** for items 1-12 on one body: about 6-9 working days.

## Repair or rebuild, and the source of truth

**Repair, on the MetaHuman garment-pipeline version.**
- **Why not rebuild:** the proportions are good (IoU 0.934) and the pipeline build already passes the skeleton, weight, budget and fit gates.
- **What repair means here:** the faults are the surface and the parts of the geometry the tells point at, meaning the hem, collar, layers, back and sim mesh. They are not the overall design.
- **Size:** the geometry pass is still substantial, about 3-5 days.

**Retire:**
- the original's skeletal and static exports;
- BlackCloak_Package.zip;
- export_refined_cloak.py;
- M_Cloak_Recolor and its MIs.

**Source of truth:**
- **Until geometry changes:** keep `Assets/BlackCloak.blend` frozen. Its hash bd42c71e is pinned in the regression recipe, and saving it breaks the regression.
- **For any geometry fix:** promote `WorkFiles/garment_pipeline/BlackCloak/BlackCloak_MH_garment.blend` into Assets/Garments/. Edit it on the locked fitting body and ship `build_garment` output (SK_BlackCloak_MH).
- **Then:** freeze Assets/BlackCloak.blend as history and re-baseline the regression.
- **Sign-off:** this needs your OK and the character chat's.

## Decisions you need to make

1. Which body is "my player" for this cloak: the male MH_PlayerDefault it is fitted to, the female MetaHuman that DemoGame_1 switched to today, or both?
2. The source of truth: promote the pipeline's MetaHuman work file (recommended), or keep the sculpt plus the refit recipe?
3. Should the game switch from the one-off SKM_BlackCloak_MH to the pipeline's SK_BlackCloak_MH (reimport + cloth rebuild)? Which FBX is canonical?
4. Move the colour option onto the pack material system (recommended)? This accepts the CloakColor-to-Colour parameter rename.
5. How dark should the cloth be, and should Cloth Sheen be on? This is a look call from a matched Unreal capture.
6. Is a dark inner layer / under-robe part of this asset, or will you hide the body?
7. What should the back look like? No reference exists.
8. How far should the fidelity rework go? It could be the big tells only (hem, collar, fabric), or also clasp, fray and edges.
9. Fab plan:
   - Skeletal only, or a separate static display version too?
   - Withdraw BlackCloak_Package.zip?
   - Is the reference product shot yours? It must never ship either way.
10. May the stray 13.8 MB recovery asset be deleted? It is in WorkFiles/BlackCloak/UnrealRecolor/Content/BlackCloakDependencyRecovery.

---

## Appendix A: finding index with final severities

Duplicates are merged in the text above. They are ENG-01 = CHR-02 = UE-1; ENG-02 = UE-3; ENG-03 = UE-2; ENG-05 ~ CHR-04; ENG-08 ~ MAT-9; UE-5 ~ VE-M3.

- **Blocker:** CHR-01 (female player not dressed); ENG-01 / UE-1 (wrong skeleton, for the original files); ENG-02 (rigid, no cloth).
- **Major:**
  - Engineering: ENG-03 and UE-2 (budget, downgraded from blocker because the game uses the 28k build); ENG-04 (MH fit, downgraded because it is already fixed in the MH build); ENG-05, ENG-06, ENG-07, ENG-08.
  - Materials: MAT-1 through MAT-5.
  - Character: CHR-03 through CHR-06, CHR-08, CHR-11 (upgraded).
  - Unreal: UE-3, UE-4, UE-5 (with correction), UE-6.
  - Fidelity: FID-1 (with correction), FID-2 (with correction), FID-3.
  - Verifier: VE-M1, VE-M2, LOOK-M1, LOOK-M2.
- **Minor:** ENG-09, ENG-10; MAT-6 through MAT-10 (MAT-7 downgraded); CHR-07, CHR-09, CHR-10; UE-7 through UE-10; FID-4, FID-5 (downgraded), FID-6, FID-7; VE-M3, VE-M5, LOOK-M3, LOOK-M4.
- **Info:** ENG-11 (downgraded), ENG-12; MAT-11; CHR-12, CHR-13; UE-11 to UE-13; FID-8, FID-9; VE-M4, LOOK-M5.

## Appendix B: refuted or corrected claims

No finding was refuted outright. These parts of findings were wrong and were dropped or corrected:

- **UE-5, "the MetaHuman FBXs carry no texture references":** false. Both carry 7 references to each of the 3 textures. The Unreal agent imported copies without their Textures folder.
- **FID-2, "the hem hangs 17.5 px below the reference; shorten it":** wrong. Only the strip tips hang low, and the median hem is 9 px *above* the reference. The fix is to close the gaps and make one continuous hem, not to shorten it.
- **FID-1, "reference cloth stdev 25.0; raise albedo to sRGB 40-55":** overstated. The reference mask included the floor shadow and hem gaps. The core cloth stdev is 11.95, so the real contrast gap is about 2.3x, not 4.7x. sRGB 40-55 would overshoot; aim for about 0.015-0.025 linear.
- **FID-5, "edge 17-22 px low":** it is 8 px at x=195 and about 16 px at x=283.
- **CHR-11, "keep slot names and just swap the MI, no reimport":** won't work on its own. The master samples UV0 with no tiling and is not two-sided, so the weave would stretch to 43-125 cm and back faces would be culled.
- **ENG-11, "MaxDistance 30 / collision thickness 0.5":** stale documentation. The live values are 120 cm and 2.5 cm (make_cloth_mh.py).
- **Engineering, "textures are RGBA":** they are 8-bit RGB.
- **ENG-09, "normal XY about ±0.037":** it reaches ±0.075, which is still weak.
- **CHR-02, "2 shared bone names":** it is 3 (root, pelvis, head).
- **ENG-05 / CHR-04, "2,325 intersecting pairs across 18 piece pairs in the source cages":** the verifier counts 4,129 across 20 piece pairs, because triangulating the quads doubles the count. The conclusion is unchanged.
- **Tells "no floor shadow" and part of "flat black mass":** these came from the review's staging (dim calibrated light, no floor catcher, low camera), not from the asset. The blind test would still fail on grain, hem, collar and clasp.
- **"Unreal check proves MH is on metahuman_base_skel":** this review's Unreal run compared bone names only. The real bind proof is `WorkFiles/garment_pipeline/ue_runs/garment_check_blackcloak_result.json` (0.00025 cm).
