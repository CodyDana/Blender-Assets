# Dojo asset queue (this chat)

**Created:** 2026-09-27. **Order:** the build order. Each kit reuses the armory pipeline: Blender build script → UCX
collision → layout.json → Scripts/pipeline export → Unreal import into DojoLab → climb/walk check.
**Gate:** each kit starts only when the user says go, and a kit that needs a reference sheet waits for it.
Dimensions come from `WorkFiles/world/DOJO_ARENA_SPEC.md`; the sheets are for look (spec wins on heights).

| # | Kit | Main pieces | Ref sheet (prompt #) | Status |
|---|---|---|---|---|
| 0 | Grey-box + GASP climb check | whole compound in blocks, DojoLab project, traversal marking, climb ranges measured | overviews | DONE: DojoLab + L_Dojo grey-box playable with GASP's CMC character; climb routes 1-8 all work after spec changes (eave landings, AC top +5.10, hipped gate roof); verify PASS |
| 1 | Perimeter wall + gatehouse | wall footing/body/cap in 2.0/2.5/3.0 m, corner, end, gate posts, lintel, gate leaves, threshold, bracket lamps | 1, 2 (in) | DONE + IN DOJOLAB (2026-09-28). Judge 5 → 6 (f1) → 5.5 (f2). Open: free-standing rear post frames outside the gate roof (the judge's #1), placeholder wall-end surfaces, footing stone design (the sheet's rough polygonal rubble) |
| 2 | Ground (surfaces + meshes) | see the kit 2 breakdown below | overviews (no sheet) | BLENDER DONE (judge 5.5/10 twice, all measured checks pass). Open: sand grain/crest irregularity, edging + beds read weakly, path too warm. Unreal import waits for kit 1 |
| 3 | Hall structure | raised platform, veranda boards, posts and beams on 2 m bays, plaster and wood wall bays, sliding doors, lattice windows, steps | 3 (in) | BUILT + IN DOJOLAB (round 2): judge 5.5 before its fix round (not re-judged). Open: the upper roof's centre section/diagonal ridges vs the sheet, unfinished ridge caps, R5 headroom at the veranda edge |
| 4 | Roof system (shared by every building) | tile field, eave tiles + fascia + rafter ends, ridge, plain ridge ends, hip-and-gable corner, gable end, verge, gutter + downpipe | 4 (in) | BUILT (round 2): reusable API in Scripts/dojo/roof/ (roof_kit.py), used by the hall; tile glaze/wear is still in the look pass |
| 5 | Small buildings | storehouse (NW), residence (NE), two covered corridors | 5, 6 (in) | waits for kit 1's shared roof-tile system to pass its judge |
| 6 | Drum pavilion + taiko (SEPARATE assets) | pavilion: granite plinth, steps, posts on stone pedestals, pyramid roof. Taiko in its OWN file (Assets/Dojo/Taiko.blend, its own export): drum, stand and 2 sticks as separate meshes (user 2026-09-27: "the drum+drumsticks should be in a separate file for flexibility") | 7 (in) | TAIKO DONE in Blender (Taiko.blend; drum/stand/stick; judge 6.5 then 6.5; LOD0-2 shipped; drum 14.4k tris hero exception). Pavilion waits for kit 1's roof tiles |
| 7 | Training shed | steel lean-to roof, pipe posts, footings, board wall, storage rack | 8 (in) | waits (sits against the wall and uses kit 1 parts; goes with the small buildings) |
| 8 | Courtyard stone | tall + short stone lanterns, well with pulley and bucket, wooden cistern (climb prop) | 9 (in) | BLENDER DONE: 12 assets, judge 6.3 then 6.5. Open: lantern stone texture stretched/mirrored + cap too thin, crate skid floats, R8 lantern width, Well/Cistern over 5k tris, no LODs |
| 9 | Training props | makiwara, striking post, two dummies, empty weapon rack, bench, stool | 10 (in) | BLENDER DONE: 7 props, judge 6.0 then 6.5. Open: wood too orange/clean with pale bevel stripes, makiwara/post base lopsided, dummy base blocks read as rubber feet, makiwara 32k tris, bench/stool placements are proposals |
| 10 | Modern props | vending machine, AC units, wall lamps, utility pole + wires, street lamps, junction box | 11 (in: modern_props_ref + ref2) | BLENDER DONE: 10+ assets, judge 6.3 then 6.8. Open: vending front not glowing, roof-AC fan shading shards, wall lamp design, AC top +4.75 vs +5.10 (kit 0), pole height 8 m unconfirmed |
| 11 | Emblem + dressing | the user's armory emblem on the gate/hall, cloth pieces, weathering and moss decals | armory emblem | waiting |
| 12 | Outside / background | approach street, background building silhouettes, landscape mountains, pines and plants from packs | overviews | waiting |
| 13 | Look pass + final showcase | sunset lighting, material pass, full assembly in L_Dojo, GASP climb routes played, performance check | overviews | waiting |

## Reference sheets: ALL IN as of 2026-09-27 (prompts in `WorkFiles/world/DOJO_PIECE_PROMPTS.md`; files in `References/Dojo/`, logged in REFERENCE_LOG.md)

| Prompt | Sheet | File | Status |
|---|---|---|---|
| - | Overview (top-down, dusk) | dojo1_reference1.png | IN |
| - | Establishing view from the gate (sunset) | dojo1_reference2.png | IN |
| 1 | Perimeter wall | dojo_wall_ref.png | DONE + IN DOJOLAB (2026-09-28). Judge 5 → 6 (f1) → 5.5 (f2). Open: free-standing rear post frames outside the gate roof (the judge's #1), placeholder wall-end surfaces, footing stone design (the sheet's rough polygonal rubble) |
| 2 | Gatehouse | dojo_gatehouse_ref.png | IN |
| 3 | Hall front | dojo_hall_front_ref.png | BUILT + IN DOJOLAB (round 2): judge 5.5 before its fix round (not re-judged). Open: the upper roof's centre section/diagonal ridges vs the sheet, unfinished ridge caps, R5 headroom at the veranda edge |
| 4 | Roof details (+ bonus overview and mini elevations) | dojo_roof_details_ref.png | BUILT (round 2): reusable API in Scripts/dojo/roof/ (roof_kit.py), used by the hall; tile glaze/wear is still in the look pass |
| 5 | Storehouse + residence | dojo_outbuildings_ref.png | IN |
| 6 | Covered corridor | dojo_corridor_ref.png | IN |
| 7 | Drum pavilion + taiko | dojo_drum_pavilion_ref.png | IN |
| 8 | Training shed | dojo_training_shed_ref.png | IN |
| 9 | Stone lanterns, well, cistern | dojo_courtyard_stone_ref.png | IN |
| 10 | Training props | dojo_training_props_ref.png | IN |
| 11 | Modern props | dojo_modern_props_ref.png + dojo_modern_props_ref2.png | IN (summary boards of all pieces; panel 11 = modern props) |

**Bought / reused, not built:** vegetation (pines, shrubs, moss) from packs, mountains as Unreal landscape.

**Per kit, done means:** meshes + collision in Blender, renders beside the sheet, measured against the spec, a blind
judge for signature pieces (gate, hall, roof, drum), imported into DojoLab with the climb check passing.

## Kit 2 breakdown: ground (from dojo1_reference2, the view from the gate)

| Surface / piece | Look in the reference | Source |
|---|---|---|
| Raked sand fight floor | pale cream sand with straight parallel rake lines, in two fields either side of the path | OUR OWN: tiling sand texture, rake grooves in the normal/height map (straight and swirl variants) |
| Sand field edging | a thin timber or stone kerb around each sand field | modelled kerb pieces |
| Centre stone path | granite slabs two wide, staggered joints, about 1.2 m wide, gate to hall stair | modelled slab pieces; granite texture (our own procedural speckled granite) |
| Surround gravel | fine pale-grey gravel everywhere else (around the hall, buildings and edges) | tiling gravel texture (Poly Haven gravel_floor_02, CC0, approved and downloaded 2026-09-27) |
| Gate threshold / front strip | a granite kerb band with a gravel strip in front of the sand | modelled kerb + gravel |
| Garden edge beds | soil with rocks and shrubs along the side walls | soil texture; rocks later; plants from packs |
| Blends | gravel into sand, soil into gravel, moss at the wall foot | material masks + decals (look pass, kit 11) |

## Workflow plan (2026-09-27; the user wants more in parallel, CPU is fine)
- RUNNING, Blender only: `dojo-greybox-kit1` (kits 0-1; it owns DojoLab + Unreal), `dojo-kit2-ground` (kit 2), `dojo-props` (taiko + training props), `dojo-props-2` (courtyard stone + crates + modern props).
- NEXT once kit 1's tile/timber system is judged: A = hall + roof system (3+4) → B = small buildings + corridors + shed (5, 7) → C = drum pavilion. F = emblem, weathering, background, look pass (11-13) at the end.
- Unreal: every Blender-only kit goes into DojoLab in one combined import after kit 1's showcase (one commandlet at a time).

## Cross-kit material pass (proposed 2026-09-27, after kit 1's materials are judged)
The judges across kits 2, 8, 9 and 10 mostly flag MATERIALS, not shapes:
- timber too orange, clean or grey, with pale bevel stripes;
- granite smeared, with mirrored UVs;
- iron metallic at 0.89-0.90, where it should be 0.95-1.0;
- lamps and vending not glowing enough.
Plan: one shared dojo material library (dark weathered timber, rough granite, old iron, rope, emissive glass), built from kit 1's judged sets and applied to every prop kit, plus the listed shape fixes:
- lantern cap;
- crate skid;
- makiwara/post base symmetry;
- dummy leg and base;
- wall lamp design;
- vending glow;
- roof-AC fan normals.
Also decide Nanite vs LOD0-2 for every kit (taiko shipped LODs; stone, modern and training have none).

## User decisions (2026-10-02: "go with your defaults for the decisions")
- Veranda: a CONTINUOUS granite step band along the whole hall front (walk up anywhere). The sheet's wide central stair stays as the main stair within the band. For the hall kit (3).
- Utility pole: 8 m (a real pole), not the sheet's 4 m label.
- Tall stone lanterns: block the pawn, ignore Camera and Visibility (thin-upright responses), even though they are wider than R8's 0.4 m. Record as an accepted R8 exception.
- Short lanterns: flank the path just inside the gate (the stone layout's (20.6, 1.0) and (23.4, 1.0)).
- Gable-frame well: a spare variant (imported, not placed; for the BR village).
- Distance detail: Nanite for the props over about 2k tris; the taiko keeps its shipped LODs too. The 5k prop triangle budget is waived for Nanite pieces.

## Showcase result (2026-09-28, run wf_60472f1d-519)
- L_Dojo has 661 actors: kit 1 (156), ground (342), taiko, training, stone and modern props, 28 GASP markers, with the grey-box buildings still in.
- Checks: walk 15/15 routes clear and 8/8 controls blocked; every climb route works; verify 8/11 gates pass.
- Verify fails:
  1. Nanite bounds: set fallback_target to RELATIVE_ERROR 0 on the 38 Nanite meshes;
  2. a heavy ORANGE colour cast in the Unreal captures (roof tiles read orange, not charcoal): re-grade the sun, sky and post;
  3. the pavilion plinth traversal marker needs its bottom raised to about +1.50; plus 2 stale wall markers.
- Other open items:
  - the AC Z-scale lifts its runners (rebuild at +5.10);
  - the vending machine is squeezed to 0.78 depth for route 8;
  - the gate apron laps 0.4 m over the sand;
  - the short lanterns stand under the gate roof.

## Round 2 result (2026-09-28, run wf_75fbd230-e3e)
- Unreal polish:
  - the colour-cast cause was lighting/post (sun 4300 K, sky, grade), now neutral;
  - Nanite fallbacks full (the Nanite render bounds inflation is engine design);
  - markers fixed, plus an in-engine GASP trace gate.
- Shared material library: Scripts/dojo/materials + T_DJ_*.
- Judges:
  - gate 5 (pre-fix; its fix ran but wasn't re-judged);
  - props A 6.5, props B 6.5;
  - hall 5.5 (pre-fix; fix ran);
  - WHOLE COURTYARD in Unreal: 6.5.
- DojoLab: 760 actors, the hall replaces the grey-box hall; walk + climb all pass; verify 5/7.
- Verify fails:
  - timber orange-red in UE (sat 0.85-1.0 vs 0.55);
  - wall-cap and gate tiles red-shifted;
  - hall plaster red in shade;
  - the grey-box pavilion ceiling renders black;
  - dressing tufts/pebbles have 0 UCX (house rule).
- The final judge's top gaps, ALL MATERIAL/LOOK:
  - sand rake lines 3-4x too wide and too regular (moire), albedo chalk/lilac vs warm beige;
  - path = pale lilac big slabs, where the ref has smaller warm-grey staggered pavers;
  - gravel too cool;
  - timber too saturated;
  - granite speckle too coarse/contrasty (reads as terrazzo).
- Correction: the wall footing in the sheet is ROUNDED, roughly square pillow-faced rubble with moss under a course of dressed blocks. The r1 judge's "polygonal" steer was wrong; round 2 built polygonal shards.
- Invented (per the final judge): street lamps inside the courtyard; short lanterns inside the gate (a user decision from my default; can drop).

## Round 3 (look pass judged in Unreal), started 2026-09-28
- User: "yes run round 3, drop the invented lamps". Workflow `dojo-round3-look` (wf_2029cfc4-7f1).
- DECISION: no street lamps inside the courtyard (street side only, or unplaced) and no short lanterns at the gate (a spare). This supersedes the earlier "short lanterns flank the path" decision.
- Tracks:
  - ground + material library: sand, pavers, warm gravel, fine granite, timber/tile/plaster colour;
  - wall + gate: rounded pillow rubble footing under dressed blocks, wall end, gate details;
  - hall: upper-roof centre section, ridges and caps, measurer items;
  - props: taiko sticks and straps, makiwara rope, the layout without the invented lamps.
- Then the Unreal import + look tuning, two blind judges on the Unreal captures, one fix round, then verify + final judge.

## Round 3 result (2026-09-28/29, run wf_2029cfc4-7f1)
- Judges on the Unreal captures: whole 6 / detail 6.5 before the fix round; FINAL judge after the fix: 7.5 (round 2: 6.5). Verify 7/11.
- Done:
  - sunset sky with clouds (a painted dome: UE 5.8 volumetric clouds don't show in SceneCapture stills);
  - warm sand with irregular 9.5 cm rake bands and 4.8 cm fine grooves, moire down;
  - staggered granite pavers;
  - warm gravel;
  - fine granite;
  - greyer timber;
  - one shared tile material;
  - the footing rebuilt as rounded pillow rubble under dressed blocks (the judge: "closest piece to its sheet");
  - the hall upper roof reshaped;
  - taiko sticks/straps and makiwara rope rebuilt;
  - the invented lamps removed;
  - dressing gets a UCX.
- Verify fails:
  - timber still sat 0.7-0.8 in direct sun;
  - tiles red-shift in low sun (gate slope R/B 1.57, wall caps 1.2-2.2);
  - hall plaster under the veranda orange;
  - crushed blacks in shade (gate ceiling 64% near-black, veranda 20%).
- Final judge's top deltas:
  - the main ridges on the hall + gate are a plain box + one cap row (needs 3-4 stacked noshi courses + onigawara with a crest);
  - the gate roof reads tan in sun from the courtyard.
- USER CALL: the sheet's clerestory is a thin strip under the upper eave; ours is taller because route 5 needs the upper eave at +5.5 (AC +5.10 + 0.40 walk-up). Matching the sheet means redesigning route 5.
- Sky shows posterisation bands in the stills.

## Round 4 (the remaining buildings), started 2026-09-29
- User: "start step one. yes keep as is". DECISION: keep the hall's clerestory as is (route 5 wins over the sheet's thin strip).
- Workflow `dojo-round4-buildings` (wf_830c5cb6-e78):
  1. ridge/onigawara fix in the shared roof system, with the hall + gate re-exported;
  2. in parallel: storehouse + residence (SM_DKO_), corridors as bay modules (SM_DKC_), training shed (SM_DKS_) + drum pavilion (SM_DKV_);
  3. the combined DojoLab import replacing the grey-box buildings;
  4. two judges on the UE captures;
  5. one fix round;
  6. verify + final judge.
- Kits 5, 6 (pavilion) and 7 are covered here. The final look pass (11-13: low-sun colour, shade crush, weathering, emblem, background, trees) comes next.

## Round 4 result (2026-09-29, run wf_830c5cb6-e78)
- Every building is real in DojoLab.
- Roof system 1.3.0: noshi tile courses, cap rows, plain onigawara, hip-roll end discs. The hall + gate were re-exported with them.
- New kits: storehouse + residence (SM_DKO_), corridors (SM_DKC_, bay modules), training shed (SM_DKS_), drum pavilion (SM_DKV_; the taiko on its floor).
- The fix round rotated both outbuildings to GABLE-FRONT (door, canopy and vent on the gable facing the courtyard), as the references show. That deviates from the grey-box's "ridge along X": route 3's 1.22 m drop is now a walk, route 2 is a 0.233 m step; re-proved.
- Judges: whole 6.5 / buildings 6.4 before the fix; FINAL 7.5. Verify 8/10.
- Open:
  - grey-box alley fences x2 still visible (+ trees and outside ground);
  - the pavilion ceiling/drum top renders near-black in some cameras;
  - the west corridor is dark in shade (needs fill light);
  - the residence ridge reads tan (wrong slot?);
  - the shed back wall covers only 1/3 of the width;
  - the shed roof reads flat;
  - low-sun warmth on sunlit tiles/timber;
  - shoji glow salmon.
- NEXT: the final look pass (kits 11-13): lighting fill/shade crush, low-sun colour, weathering + moss decals, the user's armory emblem, the outside/background (street, mountains), trees/vegetation from packs, alley fences, plus the round-4 open items.

## Round 5 (final look pass, NO vegetation), started 2026-09-29
- User: "start with everything else and leave the vegetation for later". Trees stay grey-box stand-ins; the vegetation pack choice (Megaplants / Fishing Hut / other) is still open.
- Workflow `dojo-round5-look` (wf_b76623fd-a39):
  1. three Blender tracks in parallel:
     - emblem plaques (the user's armory emblem on the hall gable + gate) + weathering/moss decals;
     - outside: approach road with the street lamps/pole outside, rear alley fences, background houses + mountain ridge;
     - round-4 fixes: shed back wall/roof, residence ridge slot, pier-cap clip, shoji kumiko + amber glow, plaster seams, dummy body;
  2. Unreal: lighting pass (shade crush, low-sun colour, sky banding, haze), decals, performance report;
  3. two judges;
  4. fix;
  5. verify + final judge.

## Round 5 result (2026-09-29/30, run wf_b76623fd-a39)
- New:
  - emblem plaques: the user's armory emblem, byte-identical texture; on the gate's street-side eave beam, and on BOTH hall side gables because the hall has no front gable;
  - 86 weathering decals: moss, rain streaks, grime, water stains, worn paths (15 lichen dropped on purpose);
  - the approach road: cobbles, kerbs, gutter, with the street lamps + poles/wires outside;
  - a canal/lane per ref1;
  - rear alley fences;
  - outside ground;
  - 43 background houses;
  - a mountain ridge ring (far mesh, not a landscape);
  - round-4 fixes: shed, residence ridge, pier clip, shoji amber;
  - lighting: shade crush mostly fixed, low-sun tiles/timber closer, a new sunset sky texture, the sun behind-left of the hall.
- Judges: whole 6.5 / detail 6.5 before the fix; FINAL 7.5. Verify 12/17.
- Verify fails:
  1. **the 1v1 closed rear alley has a GAP**: the fences only close the veranda ends; the strip behind the hall + the pockets behind the corridors are open (predates round 5; the CONTROL routes never crossed it);
  2. 11 captures still over 10% near-black (corridor soffit 33%, downpipes);
  3. a fill light 5 cm above the drum top reads as a bulb (blown);
  4. sunlit gate ridge/pavilion tiles R/B 1.2-1.4, east wall caps 1.9;
  5. decals.json vs level mismatch (the 15 dropped lichen).
- Final judge's top gaps:
  - far background primitive (flat-shaded box town, smooth sine mountains with stroke lines);
  - courtyard gravel reads cold grey-white ("snow") from above.
- User calls:
  - the hall emblem on the side gables, or the front clerestory centre;
  - bReceivesDecals on the player character.
- Vegetation still pending the pack choice.

## Round 6 (fix round), started 2026-09-30
- User: "yes start first round. keep emblem for now". The emblem plaques stay as placed.
- Workflow `dojo-round6-fixes` (wf_8a9fabe7-2eb):
  1. close the 1v1 rear alley (visible fences/gates + a separable 1v1-only blocker group + new CONTROL routes);
  2. far town impostors + jagged hazy ridges (no stroke lines, no hard plain edge);
  3. Unreal:
     - warm gravel, shade detail (corridor soffit, downpipes);
     - remove the drum fill-light bulb;
     - sunlit tile R/B <= 1.2;
     - decals.json sync;
  4. judge + independent verify with its own alley capsule attempts;
  5. a fix pass if needed;
  6. final verify + judge.
- Vegetation after this, once the user picks a pack.

## Round 6 result (2026-09-30, run wf_8a9fabe7-2eb)
- ALLEY CLOSED + VERIFIED:
  - 2 visible pocket fences + 9 invisible 1v1-only blockers (folder/tag Dojo/Boundary_1v1, listed in layout_outside.json 'onev1_only'; the BR drops them);
  - in-engine replay 32/32 CONTROLs blocked, 10/10 POSITIVE clear; verify_r5 flood 0 alley cells;
  - walk 47 routes pass.
- Far background: impostor town (a facade atlas baked from our House_A..E), fractal ridge rings (the stroke-line cause was a Fresnel rim on smooth crests), a town edge closing the far plain.
- Other fixes: gravel warm, the drum fill bulb removed, sunlit tiles <= 1.2.
- Judge 7 before the fix pass, FINAL 6 after it. Verify 16/17 (only the gravel hue band, which was mis-set by me: the refs measure 13-18 deg).
- Lesson: my gates "no region >10% near-black" + "sunlit tile R/B <= 1.2" pushed the lighting flat. The final judge says the scene is a hazy flat afternoon vs ref2's dusk (ref2 has 12.8% of pixels under luma 40, ours 1.9%; our roofs read navy blue, R/B ~0.7 vs ref 0.92-0.95).
- NEXT proposal: judge contrast against the REFERENCE, not an anti-black rule. Neutral charcoal tiles (R/B ~0.93), exposure down, deeper eave shadows; the hills lower/softer behind the hall. Plus vegetation: much of ref2's dark mass is pines/shrubs.

## Round 7 (lighting pass vs the reference), started 2026-09-30
- User: "yes do the lighting pass". Workflow `dojo-round7-lighting` (wf_2a791d84-1cc):
  1. a ref-2 matched camera + a ref-vs-ours number table;
  2. tune: exposure, sun, GI, shadows, then tile/sand/gravel/plaster/glow instances, lower hazy hills;
  3. judge;
  4. an optional second iteration (restore t1 if t2 is worse);
  5. verify (functional gates + look numbers reported).
- No anti-black rule this time: the reference governs contrast.

## What is left besides vegetation (answer given 2026-09-30)
1. This lighting pass.
2. Vegetation (the pack choice is pending).
3. A real in-engine play test of the climb routes with the character. So far only GASP's logic has been replayed on the collision.
4. A GPU frame-time check in-game (so far only static numbers: 8.47 M tris placed, ~370 draws/pass, ~395 MB textures).
5. Polish backlog from the judges (props ~6.5-7: taiko lacquer, training wood, lantern granite; gate details).
6. Housekeeping:
   - delete unused round-1..5 assets in DojoLab;
   - release the dojo locks;
   - commit the untracked Assets/Dojo + Exports/DojoKit to git/LFS when the user wants;
   - the player's bReceivesDecals (default: off).
7. Later / the user's call:
   - move the dojo into the real game project (DemoGame_1 is read-only without permission);
   - the BR variant (drop the 1v1 blockers, open doors, the hall interior);
   - Fab packaging (README, AI-reference disclosure, CC0 gravel note);
   - an IP check of the plum-blossom emblem before selling.

## Round 8 (Ultra Dynamic Sky + cinematic preset), started 2026-09-30
- Research: WorkFiles/dojo/CINEMATIC_LOOK_RESEARCH.md. Gameplay + showcase presets. The flat look came from 5 shadow-lifting overrides (toe 0.28, local exposure shadow contrast 0.5, Lumen colour boost 3.0, skylight leaking 0.1, sun angle 0.3) + the fill lights.
- Workflow `dojo-round8-uds` (wf_378a2ded-32f):
  1. copy UDS from DemoGame_1 (read-only), remove the conflicting sky/sun/fog/dome/fill lights, lock the sunset, apply the gameplay preset, one exposure owner;
  2. -game HighResShot captures;
  3. judge vs ref2;
  4. a retune (restore if worse);
  5. verify incl. GPU frame time at 1080p/1440p.
- Needs the owner's OK (not enabled): the Movie Render Queue/Graph plugin (showcase/trailer stills), the DLSS plugin.
- User 2026-09-30:
  - MRQ is NOT needed ("i dont need to make a movie"); stills stay -game HighResShot.
  - No DLSS for now (TSR first).
  - The user added the needed plants + other assets to their Fab library. But the launcher VaultCache (C:/ProgramData/Epic/EpicGamesLauncher/VaultCache) only has Megaplants Ginkgo + Japanese Cypress (09-13) and FabLibrary/listings_v1.db was last written 09-20. The new items must be DOWNLOADED (Launcher > Library > Fab Library > Download) before we can copy them in.
- User 2026-09-30: "go with the best option for the cherry" = get the Unreal-format Megaplants Yoshino Cherry via the Epic Launcher after round 8 (confirm name/size before the download). "I'd like to incorporate the cherry to the dojo, i think it's colorful and nice." PLAN:
  - the two courtyard tree slots (W + E yards, the current SM_DGB_Tree stand-ins) become Yoshino cherries in blossom as the colourful accents framing the hall;
  - darker pines/cypress outside the walls give the reference's dark mass;
  - ginkgo at the rear/outside;
  - trunk collision only; canopies must not block wall-top runners or the climb routes (recheck P1_round_west_yard_past_tree etc.).

## Outside v2 (secluded mountain dojo), started 2026-09-30
- User: "Remove the surrounding city outside the dojo, have a wheatfield at the front / surrounding area and a mountainous landscape. The feel should be an exclusive dojo that is hard to get to."
- Workflow `dojo-outside-v2` (wf_767a7853-db8), BLENDER ONLY while round 8 (UDS) owns DojoLab:
  - town/road/canal removed (listed in 'removed_v1'; v1 backed up);
  - the dojo on a raised terrace, retaining terraces;
  - a single long path with steps + switchbacks through golden wheat;
  - rugged near ridges + hazy far ridges;
  - a sparse old power-pole line along the path (the modern touch; no street lamps outside);
  - our own wheat kit (SM_DKW_*, scatter -> layout_wheat.json);
  - tree slots marked.
- Kept exactly: the alley/pocket fences + the 1v1 blocker group.
- The Unreal import folds into the vegetation round (after round 8), together with the trees (cherries in the courtyard slots).

## Landscape pivot decisions (2026-09-30)
- Keep SUNSET (not the daytime of dojo_landscape_ref).
- We EXTEND OUR STONE KIT for the terrace retaining wall (ishigaki) + the stair path (steps, landings, handrails, path lanterns). Workflow `dojo-stonekit-ext` (wf_c210ec9b-e7a), Blender only, SM_DKT_*, kit_catalog.json.
- The user sources the rest (cherries UE-format, niwaki pines, slope forest, snow mountains, rocks/cliffs, river water, water FX, ground cover, falling petals, ambient sound). Integration by us after round 8.
- Staging rule for any other chat or packs: deliver to a separate staging location (not DojoLab while our workflows run), own locks/folders, UE-native assets with textures, then this chat integrates.
- User 2026-09-30: "go with your recommendation, enable the water plugin".
  - Scenery comes from owned content: Scenery_Tutorial firs/bushes/grass/rocks/mountain, Megaplants Ginkgo/Cypress + the UE-format Yoshino Cherry (launcher download, confirm first), Ultra Dynamic Sky.
  - The UE WATER PLUGIN is APPROVED for DojoLab: enable it in the landscape round, after round 8 releases DojoLab.
  - We make: the snow-peak material, falling-petal + river-mist Niagara FX.
  - JAPANESE PINES (niwaki black pine): the user asks ChatGPT for a reference sheet (prompt given; save as Downloads/dojo/dojo_japanese_pine_ref.png), then a custom build.
- 2026-09-30: the pine sheet is in (References/Dojo/dojo_japanese_pine_ref.png). User: "have you do the development of the tree". Workflow `dojo-niwaki-pines` (wf_07266c81-5a1), Blender only: 4 niwaki pines x 2 variants (SM_DKN_*), a generator in Scripts/dojo/pines/, wind-ready, trunk-only collision.
- RUNNING NOW: round 8 (UDS, DojoLab), the stone kit (Blender), the pines (Blender).
- AFTER round 8, the LANDSCAPE ROUND:
  - enable the Water plugin;
  - the cherry UE-format download (confirm with the user);
  - owned scenery + river + snow material + petals/mist FX;
  - place the stone kit + pines;
  - lighting;
  - checks.
- 2026-09-30: the tree study runs first (`tree-study-then-pines`, wf_ecce4489-dc6 → TREE_BUILDING_STUDY.md at the repo root), then the pines.
- The user agreed WE make the petal + mist FX assets. The user will bring ChatGPT reference sheets: Downloads/dojo/dojo_petals_ref.png and Downloads/dojo/dojo_mist_ref.png (prompts given in chat).
- FX plan:
  - snow = a height+slope material blend on the mountains;
  - petals = GPU Niagara per cherry canopy + a courtyard layer, wind from UDS, + fallen-petal scatter/decals;
  - river mist = Niagara mist at the rapids + spray bursts at boulders + a low Local Fog Volume + foam in the water material.
- 2026-09-30: the petal + mist sheets are IN (References/Dojo/dojo_petals_ref.png, dojo_mist_ref.png; logged). The FX assets are built in the landscape round: petal cards (flat/curled/folded + a browned variant) and the fallen-petal scatter; mist/spray flipbooks + Niagara + a Local Fog Volume.
- 2026-09-30: ROUND 8 DONE (UDS + gameplay preset), wf_378a2ded-32f. Judges 5 -> 5.5. The level uses UDS only (our sky, sun, fog and fill lights are gone, one exposure owner, time locked at 1730 = 9.1 deg sun from the west). Verify: all gates pass (253 meshes, walk/climb/roof walks, alley 32/32, GASP trace 23/23, DemoGame_1 untouched). GPU mean 8-14 ms (66-100 fps); p95 over 16.7 ms at 1440p@100. Open items:
  - the sun decision (9 deg west: lit sand, but a gate shadow on the yard and a pale sky; vs 5 deg: sunset sky but shaded sand);
  - sky banding/posterized clouds;
  - kawara read warm brown;
  - shoji glow too bright and yellow;
  - lantern pools weak;
  - the rake stripes are regular;
  - perf config not written (screen percentage 67-75% at 1440p, volumetric fog grid 16 px / Z 64).
  The town and grey-box trees go in the landscape round. Stills: WorkFiles/dojo/build/unreal/round8/s2/. Future judge stills: -game HighResShot via run_game_capture.ps1.
- 2026-09-30: STONE KIT EXTENSION DONE (wf_c210ec9b-e7a). 71 pieces SM_DKT_* (41 wall incl. corners, ends, stair openings, coping, foot; 30 stair incl. flights, landings, cheeks, rails, timber and stone lanterns). qa_check 0 hard fails, FBX re-import OK, walkable (risers ~0.167 m, ramp 26 deg). Not in Unreal yet. Judges 6 -> 5.5: the fix followed judge 1 into pale polygonal wall stones, long tread slabs and crazy-paving landings. Judge 2 and my own look say the reference is the other way (rounded mid-grey stones with moss in the joints, 3-5 short blocks per tread) - the same judge-flip as round 1's footing stones.
  Proposed fix round 2, from my reading of the reference:
  - restore the round-0 stone shapes and short tread blocks;
  - keep a mid-grey tone with moss/dirt in the joints;
  - a near-vertical terrace batter as the default (castle sweep optional);
  - flush rectangular landing flags plus a kerb piece;
  - squared rails on round posts;
  - a buried footing course instead of loose rubble;
  - fix the doubled lanterns.
  Waiting for the user's go.
- 2026-09-30: TREE STUDY DONE: TREE_BUILDING_STUDY.md at the repo root (1,559 lines, critic-revised), research notes in WorkFiles/studies/trees/, CLAUDE.md standards row updated. The study asks for shared-pipeline changes that were NOT made (qa_check uv0_overlap skip, _sss/_thk in DATA_SUFFIXES, make_ucx_hull_from_points); they need the pipeline owner's OK.
- 2026-09-30: PINES r0 + f1 DONE but not passing (wf_ecce4489-dc6). 8 trees SM_DKN_PineA1..D2 (trunk + foliage meshes, Pivot Painter 2 wind data), qa_check clean. Judges 3.5 -> 4.5; silhouette IoU 0.59-0.73 against 0.80.
  - Core miss: the pads are flat needle slabs, not domes of separate needle rosettes on zig-zag twigs.
  - Also: the D rock is a big faceted block (the reference has multi-lobed, lichened rock with 8-12 wrapping roots); needles too dark; no mossy base mound; bark too regular.
  - The judges flipped on trunk girth (too thick -> too thin); use the reference ratio instead.
  - Proposed v2 is a METHOD change (rosette-unit library + pads assembled as domes on ramified twigs; rebuilt rock; base mound as a separate mesh). Waiting for the user's go.
- 2026-09-30 USER DECISIONS: run all of step 1; the Megaplants settings are approved (the Procedural Vegetation Editor plugin + Nanite Foliage in DojoLab); HOLD the Yoshino Cherry (leave cherry slots marked in the landscape round); the sun stays ~9 deg from the west (my recommendation, taken with "yes do all of step 1"); commit a git checkpoint before the landscape round; then run step 3 (the landscape round).
- 2026-09-30: step 1 is running as one workflow, dojo-step1-parallel (wf_0b520999-fc8):
  - stone kit fix 2 (the owner's reference reading);
  - pines v2 (the rosette-pad method; heights from the sheet's figure: about 2.3/3.5/4.5/3.7 m);
  - DojoLab round 9 (look fixes + Megaplants settings + perf config);
  - paired before/after judges, keeping the better;
  - then a quiet-machine perf verify.
- 2026-09-30 ~09:35: USER: "for the stone and stone wall... rocks... do a study on the best ways to develop stone and stone walls and rocks before proceeding with that".
  - Stopped wf_0b520999-fc8 at 1h13m. Backups exist: Backups/DojoStoneKit_f1_2026-09-30, Backups/DojoPines_f1_2026-09-30, round9/s1_work/start_backup. An orphan DojoLab dj_sc_level.py commandlet was left to finish on its own.
  - Relaunched as dojo-step1b-stone-study (wf_d5f00786-6d9):
    - STONE_BUILDING_STUDY.md at the root (research x3, draft, critic, revise, CLAUDE.md row) -> then the stone kit rebuild f2/f3 per the study;
    - pines v2 trees continue now; the D-pine rock waits for the study;
    - DojoLab round 9 continues from its partial state;
    - verify at the end.
- 2026-09-30: STEP 1 DONE (wf_d5f00786-6d9).
  - STONE_BUILDING_STUDY.md at the root (2,028 lines, critic-revised; notes in WorkFiles/studies/stone/; CLAUDE.md row). The study notes the tracer/measurer tools (stone_trace.py, stone_measure.py) don't exist yet (~3-4 sessions) and gives a rock sourcing list.
  - Stone kit: best f3 5.8 (paired judges; f2 6 vs r0 5). Still coursed beds (SG5 fails), soft pillows, tan in Blender; next method step = power-diagram layout.
  - Pines: best v2f 5.6 (v2 5.5 vs f1 4.5). Rosette pads, mounds and the new D rock are in; the needles still read olive and brushed.
  - DojoLab round 9: 5.5 vs r8 4.5 (s2 retune worse, restored s1). Sunset sky with clouds, Megaplants PVE + Nanite Foliage on, perf config in: GPU 7-8 ms at 75% on 1440p; all gates pass. Caveat: Saved GameUserSettings sg.ResolutionQuality=100 overrides the curve on this PC.
- 2026-09-30: git checkpoint 5daa0d2 "Dojo checkpoint before the landscape round" on main (3,920 files, dojo paths only; ~2.3 GB LFS; not pushed).
- 2026-09-30: STEP 3 LANDSCAPE ROUND running (wf_efa3b002-0bd):
  - plan + owned-content inventory + gap list, in parallel with the FX assets in Blender;
  - DojoLab world (Water plugin, town removed, stone kit + pines imported, Landscape terrace/cliff/river, peaks with snow, conifers, CHERRY SLOTS, 1v1 terrace boundary);
  - FX (petals, mist, fog) + lighting rebalance;
  - judge, fix, keep the better;
  - verify.
- 2026-09-30 ~19:00: USER decided WE build the rocks (boulders, river boulders, cobbles, cliff chunks); supplied References/Dojo/dojo_rocks_ref.png (logged). The rock kit workflow is running (wf_42b8775c-9fd, Blender only, SM_DKR_*): pilot (2 river boulders + 1 cliff chunk) -> blind judge, stop gate 7/10, one method fix -> the full set only if it passes. After the landscape round: an in-engine side-by-side of our rocks vs the owned rocks, then swap them into the boulder zones BF1-BF3/C1.
- 2026-10-01: ROCK PILOT FAILED the gate: 3/10 (wf_42b8775c-9fd; no fix ran, below 4). Silhouettes matched (IoU 0.84-0.94) but: (1) the surface is painted speckle with no crystal-scale relief (local contrast 0.06 vs the sheet's 0.14); (2) RiverRound reads as a loaf/toaster (vertical sides, flat top); (3) the cliff is a grid of slabs that reads as masonry; (4) the wet band is a hard horizontal line. Proposed next: method change (corestone ellipsoids cut by joint planes; fracture-based cliff; real scanned CC0 granite surface maps) as a second pilot, or go back to sourcing. Waiting for the user. Landscape round: in its fix stage (judge ran at 22:14).
- 2026-10-01: USER: option A for the rocks. Downloaded 4 Poly Haven CC0 2K sets (tiger_rock, rock_surface, granite_tile_03, mossy_rock; 49 MB JPG; md5 OK; SOURCE.md each) into Assets/Dojo/SourceTextures/PolyHaven/. Rock pilot 2 running (wf_d8db8927-9b6): corestone river boulders, fractured cliff chunk, scanned surfaces; gate 7/10.
- 2026-10-01: USER DECISION: THE ARMORY GOES INSIDE THE MAIN HALL (option 1). Keep the hall front exactly as built. Extend the hall back about 11 m with a lower rear roof (temple rear-hall style) so the armory's 12 x 20 m interior (ceiling +4.8, door centred on its short south side) sits behind the hall's three centre door bays. Move the compound back wall, the rear alley 1v1 closure and the terrace back about 10 m. Read Exports/ArmoryKit + the armory chat's layout read-only (never edit armory files). Relight the armory from night to sunset through the open doors. Redo walk/climb/alley/GASP checks incl. the interior. Runs AFTER the landscape round. The user is briefing the armory chat (prompt given in chat): it will write WorkFiles/armory/ARMORY_HANDOFF_DOJO.md.
- Hall facts: walls X 13.0-31.0, Y 24.0-34.0 (18 x 10 m), 2 m bays, front P W P D D D P W P, head beam +2.67, wall plate +5.37, upper eave +5.5, ridge +8.7; compound back wall at y ~37.
- 2026-10-01: USER: after the hall extension, the armory must be "extended and in sync over there too": TWO-WAY SYNC between DojoLab (dojo hall) and ArmoryLab (armory chat). Any change the user makes in either chat must carry to the other.
  The hall-extension round must build the sync system:
  - shared source of truth: WorkFiles/shared/armory_hall/ with:
    - SYNC.md (the rules);
    - manifest.json (revision, date, chat, change log, FBX sha256 list);
    - interior_layout.json (every armory interior piece in HALL-LOCAL coordinates: origin = the hall's centre door threshold at finished floor level, +Y into the hall);
    - hall_shell_layout.json (the hall shell incl. the rear extension, SM_DKH_* + new SM_DKH_Rear*);
    - lights_design.json (case lights, downlights and lanterns travel with the interior; sky/sun/time-of-day stay per level: DojoLab sunset UDS, ArmoryLab its own);
    - interface.json (interior envelope: inside wall faces, floor level, ceiling, door openings, the bays the interior may touch).
  - ownership: the interior contents are the armory chat's, the shell is the dojo chat's; either chat may edit either side when the user asks, under the lock WorkFiles/locks/armoryhall.json (Scripts/pipeline/lock.py). After an edit: re-export via Scripts/pipeline, update the layout json, bump manifest revision + a dated change line.
  - each project gets a sync script that rebuilds placement from the shared jsons and re-imports changed FBX by sha (DojoLab: Scripts/dojo/unreal/; ArmoryLab: the armory chat's scripts).
  - each chat, at the start of any armory/hall work, compares the manifest revision with its last-synced revision (stored in its own notes) and syncs first.
  - git: commit the shared folder with the change.
  The prompt for the armory chat was given to the user in chat on 2026-10-01; the user sends it after the extension is done.
- 2026-10-01: LANDSCAPE ROUND DONE (wf_efa3b002-0bd).
  - Judge 5 -> fx+light 3.5 vs fix 5.5 (fix kept).
  - Matches the reference's layout: terrace + ishigaki wall, cliff stairs with lanterns, a river past the SE corner, forested slopes, peaks.
  - Weak:
    - the river reads calm with few in-stream boulders (our rocks pending);
    - bare grey cliff/valley faces;
    - small smooth snow cones vs the reference's broad massifs;
    - no cherries (on hold);
    - the wall stones read as rounded pebbles in engine.
  - Verify: all gameplay gates pass; 338 town instances removed; the 1v1 terrace boundary holds; the stair is walkable.
  - Perf OK at the main cameras (12-15 ms), but CAM_RiverRapids 22.7 ms and CAM_StairPath 19.1 ms (shadow depths from the firs).
- 2026-10-01: HALL + ARMORY round launched (wf_ac6d2186-d40):
  - survey (armory read-only from r20; the handoff file did not exist yet) + the sync design;
  - Blender rear extension;
  - DojoLab placement + relight + the sync script + carry-over fixes (stair lanterns, dead BR routes, shadow pass);
  - judge/fix;
  - verify.
  Rock pilot 2 (wf_d8db8927-9b6) is still running in parallel.
- 2026-10-01: ROCK PILOT 2 STOPPED at the gate: 4 -> 5/10 after its fix (pilot 1 was 3) (wf_d8db8927-9b6). Better: the granite grain is real, a soft wet zone, readable cliff blocks. Still CG tells: the river boulders read as smooth potato/soap blobs with slit cracks (no broad facet planes or lobes); the cliff has no horizontal bedding ledges or crisp jointed blocks; moss/lichen are flat decals. Agreed fallback = sourcing. Recommended: the user resumes the owned Electric Dreams Env download (23.9 of ~60 GB staged, idle since 2026-09-12; the likeliest owned granite rocks/cliffs). Our pilot rocks stay on disk as backups. Waiting for the user.
- 2026-10-01: HALL + ARMORY DONE (wf_ac6d2186-d40). Judge 7 -> v1 6.4 vs fix 7.2 (fix kept).
  - Hall extended 14 x 11 m back (posts X 15-29, Y 34-45), lower gable rear roof (ridge 0.76 m under the main ridge); invisible from the courtyard cameras (0.03% change outside the open doors).
  - Centre doors lifted out (1.76 m clear per bay).
  - Armory interior placed: 461 instances, 114 design lights, sunset relight with an interior PPV; matches the armory stills closely.
  - North wall/alley/terrace moved +11 m; cherry slots CS19/20 and the cypress row moved.
  - Verify: 88/88 walk routes incl. 26 interior, the GASP pawn walks in to the dais, alley + boundary floods 0 leaks, GPU under 16.7 ms everywhere (RiverRapids/StairPath fixed by the shadow pass).
  - Fails: CAM_Ref2Match backdrop above the roof changed (trees moved by the terrain move); SYNC.md missing the ArmoryLab shell + regeneration instructions.
  - Minor: the sync script re-saves on no-op; render-thread p95 17.9-19 ms; Lantern_5.
- 2026-10-01: follow-up running (wf_858bf0ab-926):
  - shared tools regen_interior.py / bump_manifest.py / check_sync.py;
  - shell_materials.json;
  - complete SYNC.md (ArmoryLab shows the extended hall);
  - the no-op sync;
  - backdrop restore, ISMs for render-thread cost, Lantern_5;
  - verify incl. a dry-run as the armory chat.
  The armory-chat prompt is sent only after this passes.
- 2026-10-01: SYNC FINISH DONE (wf_858bf0ab-926).
  - Shared tools (regen_interior / bump_manifest / check_sync / ue_armorylab_shell + an FBX reader), shell_materials.json, SYNC.md rev 3 (sections 0, 3, 11-14).
  - The sync script is a true no-op on rerun; the backdrop is restored (0.29% change above the roof, time-matched).
  - Frame time p95 now 11-15 ms everywhere: the big render-thread cost was Niagara in ray tracing (now off).
  - Stair L6 moved (min width 1.55 m); all gameplay gates pass.
  - ISMs need the armory chat to set used_with_instanced_static_meshes on its 7 masters (optional, small perf gain; the user's call).
  - Verify failed only the armory-side dry run: (1) the armory chat's own ak_verify order vs the hall-variant lifts; (2) the shell master sources not hashed. A small agent is fixing both -> rev 4. Then the user sends the armory prompt.
- 2026-10-01: SYNC rev 4 (SYNC.md 3.2 armory-side order: its own run_armory_unreal.sh first, then tools/ue_armorylab_shell.py last, then check_sync --side armory; section 15 shell-master snapshot + drift check; 3.4 per-project 'needs sync' revisions). check_sync dojo 0, armory 2 (expected). NOTE: the next DojoLab sc_verify needs run_armory_sync.sh first (records rev 4). The armory-chat prompt was given to the user.
- 2026-10-01: the ARMORY CHAT finished ArmoryLab first-time setup: synced at rev 4 (check_sync armory 0), shell placed 161/161, exterior hidden. It found that Unreal re-saves change .uasset sha (package GUID) and fixed ak_materials to save only on change. Our side checked: the manifest hashes only ArmoryLab's armory material/texture uassets and DojoLab's byte copies (dj_armory_sync copies files, saves only on change; 2nd-run md5 identical); the shell masters are tracked by a code snapshot, not uassets. check_sync dojo = PASS. Committed + pushed 763e0c0f (1,216 files; backup tars/start_backup excluded; no armory-chat or lock files).
- 2026-10-02: USER: bring the DemoGame_1 player into DojoLab, LOOK + MOVEMENT + the JUTSU (not the air-jump flips, lock-on, stance, free look unless the jutsu needs them). Running (wf_2e814453-cf6):
  - BP_NinjaGasp + BP_NinjaVisual + MH_PlayerDefault + CloakMH (Chaos cloth) + the centred camera;
  - UNinjaJutsuComponent ported unchanged into a new DojoLab C++ module, with PORT_PROVENANCE.md (DemoGame_1 commit, sha256, re-sync steps);
  - DemoGame_1 read-only; never MH_PlayerFemale/private.
  Separately (user's earlier question): ArmoryLab ran ~10 fps in PIE (309 frames/31 s, 50 un-precached PSO hitches); the user was given a profiling prompt for the armory chat.
- 2026-10-02: NINJA PORT BUILD DONE (build stage of wf_2e814453-cf6). DojoLab now plays BP_NinjaGasp (MetaHuman MH_PlayerDefault + CloakMH, centred camera, ninja run/sprint, the 4 jutsu on F/2/3/4) through the new GM_DojoNinja; GM_Dojo still gives SandboxCharacter_CMC (`?game=/Game/Dojo/Blueprints/GM_Dojo.GM_Dojo_C`).
  - New C++ module Source/DojoLab (29 DemoGame_1 files byte-identical + the camera switch); DojoLab is now a C++ project: build the DLL (run_ninja_port.sh build) before any commandlet or -game run.
  - 510 packages copied, 0 overwritten; headless check 6/6, -game probe: every jutsu fires, camera lateral 0 / 375 cm. Notes: BUILD_NOTES 'NINJA CHARACTER'; provenance: build/ninja_character/PORT_PROVENANCE.md.
  - Open: D1 hair/brow/lash colour vs DemoGame_1 shots, perf delta, dj_sc_verify run (after run_armory_sync.sh). PRIVATE LAB ONLY (anime audio + Naruto names).
- 2026-10-02: NINJA PORT PLAY TESTS DONE (play-test stage of wf_2e814453-cf6; BUILD_NOTES 'NINJA CHARACTER: play tests', results in build/ninja_character/test/RESULTS.json, OVERVIEW.jpg, videos per jutsu).
  - Look: MetaHuman + cloak, silhouette vs DemoGame_1's own shots IoU 0.78-0.89; Chaos cloth live every frame (frozen control detected), no explosion, no T-pose (<= 7.5 cm vs the host).
  - Movement: walk 200 / run 575 / sprint 1000, centred camera (lateral 0); all 15 traversal routes play the same GASP montages as SandboxCharacter_CMC.
  - Jutsu: all 4, standing / walking / running: every seal on UpperBody, completes, clone / fireball / seal decal / Chidori spawn and resolve, audio + FX fire, 0 errors / ensures.
  - Gameplay: 88/88 walk routes walked by the pawn (incl. 35 armory interior), 33/33 CONTROLs blocked, 0/12 1v1 escape attempts leaked; capsule = GASP's (r 30 / hh 86).
  - FIX T1: removed the leftover plain double jump (BP_NinjaGasp jump_max_count 2 -> 1 = GASP's); documented in PORT_PROVENANCE.md.
  - Open: 16.7 ms p95 missed at PlayerEyeSand / WestAisle by BOTH pawns (ninja 20.5 / 20.7, GASP 21.2 / 19.0); the ninja costs +1.9 / +3.3 ms mean in view. D1 hair colour not judged (lighting). PRIVATE LAB ONLY.
- 2026-10-02: NINJA PORT DONE (wf_2e814453-cf6).
  - BP_NinjaGasp is DojoLab's default pawn (GM_DojoNinja; GM_Dojo keeps SandboxCharacter_CMC). New C++ module DojoLab: 29 DemoGame_1 files byte-identical + DojoNinjaCameraSubsystem (a per-pawn camera cvar). 510 packages copied at DemoGame_1 paths; extra components removed; the IMC trimmed to the 8 jutsu rows. PORT_PROVENANCE.md (commits, sha256, re-sync steps).
  - Tests: the MetaHuman + cloak with live cloth; GASP movement + 15 traversals; all 4 jutsu (ShadowClone, GreatFireball, Summoning, Chidori) standing/walking/running; 88/88 walk routes, alley/boundary 0 leaks, same capsule.
  - Failed: frame time p95 17-21 ms for BOTH pawns (the machine was shared during the tests); dj_sc_verify gate 9 (the armory_hall sync is at rev 3 vs the armory chat's rev 5).
  - IP: the jutsu use Naruto names and third-party anime audio (private lab only, never publish).
  - Follow-up running (wf_66c8379f-e32): sync to rev 5 + gates, then an idle-machine perf profile with measured levers (no changes applied; the owner decides).
- 2026-10-02: ARMORY CHAT rev 5 note (relayed by the user):
  - Entry mat retired (SM_AK_EntryMat); 10 new backlit upper window papers SM_AK_Window_Paper_35_W/E (AKI_0618-0627; emissive M_AK_HWinPaperW/E); 4 mat materials unused; lights_design gets ArmoryLab-only atten/channels (not for DojoLab).
  - They ask us to: sync + record; check the window-paper emissive by eye at our sunset (lit shoji, not a light box) and tune per level in dj_armory_look.py.
  - ArmoryLab perf: 80-99 fps in -game; the user's 10 fps PIE was startup + GPU contention from ~15 Blender renders (VRAM 11.8/12 GB, a GPU timeout at 02:14). Their fix: case lights on lighting channel 1 only (the shell stays on 0), -52% shadow-depth draws.
  - Lever for DojoLab: 15 of the shell's 32 pieces (139 actors) are non-Nanite and get pulled into shadowed local lights' shadow maps -> make them Nanite or keep shadowed lights off the shell via channels.
  - Their ArmoryLab run overlapped our perf_ninja_1 (contaminated).
  - The shared rev-5 files are uncommitted (the owner decides).
  TODO after wf_66c8379f-e32: the window-paper look check/tune at sunset + test the channel/Nanite-shell lever.
- 2026-10-02 USER:
  - (1) commit the shared armory_hall rev-5 files with our sync (after wf_66c8379f-e32);
  - (2) REMOVE THE JUTSU VOICE-OVERS COMPLETELY, in general, not just in DojoLab. In DojoLab: clear every jutsu's StartVoice on the BP_NinjaGasp copy, delete /Game/Ninja/Audio/Voice/SFX_Voice_GreatFireball + SFX_Voice_KageBunshin, and update PORT_PROVENANCE re-sync steps to never bring voices back. DemoGame_1: the same in its own project (its chat, or us on the user's say-so). The SFX (seal, release, Chidori, fireball) are not voices; they stay unless the user says otherwise (they are also third-party anime audio).
