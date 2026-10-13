# SMG01 W4 "apply fixes": fix log

Source of the findings: the W4 review of the renders from the exported W3 bytes (commit 1818f9a1): the craft review
(5 major, 6 minor, 2 notes), the tech review (PASS with 3 minor findings and 9 notes) and two realism judges on the
final-texture views (fp_35cm, ads_55deg, tp_3m, hero_34, hero_34_folded: every close view called fake by both, tp_3m
passed by both). Every finding was checked against the bytes, the generators and the sheet before it was fixed or
rejected. Fixes are in the generators only (no output edited by hand). Every output was then rebuilt from nothing with
`Scripts/guns/smg/run_all.sh` (run_smg.sh -> run_surface.sh -> AR-01 regression -> run_rig_mag.sh ->
smg_review_export.py -> smg_w4_fix_gates.py) and every stage gate re-run.

Numbers: `gates/form.json`, `uv_bake_paint.json`, `game.json`, `rig_export.json`, `mag.json`, `review_export.json`,
`gunlib_regression.json`, `review/diag/maps_vs_clay.json`, summarised in `gates/review_fixes.json` (one row per finding
with its evidence). Spec rulings for this round: **R44** (the first fix pass) and **R45** (the "flat clay" cause and
fix), in `tools/make_spec.py` / `smg_spec.json` `resolutions`.

The work ran in two sessions. The first fix pass (stopped mid-way at a user pause) made most of the generator fixes in
section 1. This resumed session checked that work, measured the cause of the realism judges' main finding (section 2),
fixed it, fixed two LOD1 regressions the first pass had introduced, and rebuilt everything.

## 1. Craft + tech review

| # | Finding | Verdict | Fix / reason | Evidence |
|---|---|---|---|---|
| C1 (major) | G3: vent and charging-channel ends polygonal | REAL, fixed | `parts/receiver.py stadium_xz`: 24 segments per semicircle (7.5 deg) on every moulded vent and the channel's lock notch; port corners 6 segments, magazine ladder recesses 5 (`gunlib.mag_box.ladder_cutters seg`, default unchanged for the AR-01). New gate **G3o** (`smg_facet_check.py`): the boundary loops of every opening on the moulded parts' side faces | G3o pass: max facet 4.0 deg at r >= 5, max sagitta 0.032 mm, 0 fails; B8 gun LOD0 48,238 tris (ceiling 50k), magazine 4,300 |
| C2 (major) | Charging knob a cratered, speckled blob | REAL, fixed | `smg_paint.py`: the knob's coat even (mottle x 0.25), the flat crown worn to a smooth satin (rough 0.45-0.55), a thin continuous bare rim just outside the crown edge | knob crown 3,409 texels, rim 245 bare texels; knob bare fraction 0.0065 |
| C3 (major) | Bare steel as 196 isolated specks (fireflies) | REAL, fixed | Bare steel as continuous 0.18-0.8 mm lines on the sharp convex crests (same-side edge distance x AO exposure x the bright-edge zones), <= 1.2 mm from the edge, clusters >= 14 texels; not on the rails' base flange or the device's slot edges; rubbed phosphate varied along the part (no per-tooth repeat) | 169 clusters, min 14 / median 50 texels, widest 0.78 mm, 0 bare texels off an edge, 0.70 % of the steel |
| C4 (major) | Polymer too clean, flat normal map, no whitening | REAL, fixed | Moulded texture in the normal map at the texel scale (0.6 mm grain over a 1.8 mm orange peel), roughness grain, albedo mottle at the craft table's +-4 levels, longer whitening bands, fore-aft scratches, a lighter glossier follower; plus this session's R45 pass (section 2) | Furniture BC std 4.25 levels (W3 2.3), Mag 3.88; normals tilted > 1 deg on 22.1 % / 23.4 % of texels (W3 2.3 %); polymer roughness std 0.085 -> 0.096, magazine 0.038 -> 0.059 |
| C5 (major) | G20: the steel lighter than the polymer | REAL, fixed | Phosphate base (40, 41, 42) (was 50-52), dry 0.62-0.76 / oiled 0.52-0.62 (spec R44; the CRAFT_STUDY table corrected); the L5 gate grades the sRGB-luma ratio receiver / (barrel + device) | ratio 1.49 (sheet 1.45; band 1.3-1.5); L5 colour pass on every region |
| m1 | Windage drum without knurl | REAL, fixed | Straight knurl, 0.55 mm pitch, 0.05 deep in Metal_N on the drum rim, crests rubbed lighter | 6,560 knurl texels |
| m2 | Port with the bolt back an empty box | PARTLY fixed | Fixed: the chamber mouth's 0.6 chamfer painted as the rounds' rubbed bright cone with a bare rim, bore soot deepening inward, port rear-edge soot 0.6. Rejected: the feed ramp and the magazine top: the bore centre (Z 1.87) is under the port's lower edge (Z 2.3) and the seated magazine's lips (Z ~ -13.6) are 16 mm under it, behind the wall and the bolt rails; no side or 3/4 view reaches them | chamber mouth 390 texels; F5 recess 81 of 91 rays |
| m3 | Trace noise (stock window, pad ribs) and the catch / V-panel junction | REAL, fixed | (a) Stock windows: DP 1.0 + true R 3 corners and R 25 blends at gentle bends. (b) The pad's rear face is the drawn face line through the tooth tips; grooves at one pitch / depth (3.2 / 1.2), open at the sides at LOD0. (c) The lower housing set in 0.8 under the upper's plan including its 45 deg fore-end step (its tongue stood 3.1 mm proud: the wedge face and black sliver) | L2 LEFT 0.981, RIGHT 0.955, TOP 0.932, per part 23 / 23; L3 24 / 24; G5 0 |
| m4 | Facets on the grip cover and the guard; LOD2 grip shading | Fixed at LOD0; LOD2 rejected | Guard master corners at 0.5 mm chords, the opening's R 6 corners 8 segments, the loop's offset corners rounded R 14, grip-cover stations 0.8 mm and bottom rim 4 segments. LOD2's grip shading only shows from ~9.5 m; LOD-pop passes on both stock states | G3o; LOD-pop (game.json) |
| m5 | Muzzle soot invisible, no crown carbon | REAL, fixed | Soot at the PBR floor (lin 0.013, sRGB 30) over the inner cage, bore, slot walls, a ring round the bore and a gradient out from each slot | L5 muzzle_device pass |
| m6 | Magazine top a flat rim, follower lost | PARTLY fixed | Fixed: lips rolled (R 1.2, 3 segments, 0.9 tip face; `gunlib.mag_box` optional `roll` / `tip`, off by default for the AR-01), the follower 1.0 under the lips' underside (was 8.0), lighter and glossier. Rejected: the stepped-up front top edge: the bolt rails stand 1.5 mm over the magazine's front top edge by design (R30) and M2's overtravel leaves no room | mag.json pass, form_magfit pass |
| m7 | Twin LOD sizes at the box half-diagonal | REAL, fixed | `gunlib.game.static_sphere_radius` (max \|v - box centre\|, Unreal's static-mesh rule, confirmed by the AR-01's engine numbers); the twin's and the magazine's sizes convert at it; U5 checks them against the engine | game_lod_sizes.json, SM_SMG01.sockets.json |
| m8 | Physics asset bounds vs the folded stock | DEFERRED to W5 | Needs the engine: plan 14.3 U7 now measures the component's runtime bounds of a dropped, simulating gun with the stock folded, with the fallback fixes written there | SMG_BUILD_PLAN 14.3 U7 |
| m9 | Sidecar texel classes state the bands, not the shipped densities | REAL, fixed | `SK_SMG01.skeletal.json` `gun.texel_classes_measured_px_per_cm` + `texel_class_rule` (R44 records W2's 1.25 x band-top ceiling) | sidecar |
| m10 | Metal Masks G = 0 | REAL, fixed | m_hand written on the phosphate (trigger / paddle faces, knob crown, selector thumb arcs, handling zones) | Masks G on 7.9 % of the phosphate |
| n1 | M4 definition | Recorded | R36's spring-catch M4 written into SMG_BUILD_PLAN 12.2 for W5 M9 and later guns | plan 12.2 |
| n2 | Budgets (LOD0 over the 25-40k target, LOD2 20 %, mag LOD2 / LOD3) | ACCEPTED, reported | Inside the 50k ceiling and the qa budget; LOD-pop and M1 pass, so none is visible | B8 |
| n3 | UD4 not reproducible from the shipped bytes | DEFERRED to W5 (U8) | The engine measures the lightmap; the shared texels are the projection charts' design | UD4 (build) pass |
| n4 | ShellEject with the stock folded | Recorded | The socket's use text (spec -> sidecar) states the throw cone meets the folded stock (B3b: 29 vertices; Q5 open) and that casings ignore the gun's own collision | sidecar sockets |
| n5 | W5 U2b needs the AR-01's abp_angle_table | DEFERRED to W5 | Harness data from `Scripts/guns/rifle/rifle_rig.py`; the AR-01 bytes stay as shipped | - |
| n6 | FBX NativeFilePath carries the absolute source path | DEFERRED to W6 / P | Pipeline-wide (AR-01 N1), fixed once before the Fab release | - |
| n7 | UCX_SM_SMG01_LOD0_02 not strictly convex (0.445 mm) | ACCEPTED | Unreal rebuilds the hull from the vertices; C1 0 outside | game.json C1 |
| n8 | Report wording | Fixed here | The W3 commit's LOD1 count is 23,344 (not 23,346); UD4 does not apply to the SK (no UV1); the fold's worst_excursion 248.8 mm is the 3D excursion, the per-axis growth 246.5 mm; the StockFold latch-bolt pass-through 0.458 mm at f3 stays accepted (a rigid rig cannot press the button) | - |

## 2. Realism judges: "one flat matte clay" (8 fake calls), measured

The orchestrator asked first whether the review renders show the final maps at all, or whether the paint is too
uniform. Both parts were checked:

- **The maps reach the renders.** The exported FBX carry `UV0` (SK) and `UV0` + `UV1` (twin, magazine);
  `gunlib.game.game_material` reads BC as sRGB, ORM and N as Non-Color, flips the DirectX green, and multiplies a gentle
  AO into the base colour. A BC-as-emission render shows the painted variation. Hookup, colour space and UVs are right.
- **But the paint was near-uniform at render scale, and the light gave it nothing to show.** New tool
  `smg_maps_vs_clay.py`: the seven 35 cm close-ups are rendered with the shipped maps and again with the same material
  with its maps unplugged and set to the maps' per-set medians (a constant clay of the same mean colour). With the first
  fix pass's maps the textured renders differed from that clay by only **1.8-3.5 sRGB levels (mean over the object;
  mean of the seven 2.8 under the review's grey-world light, 2.7 under a studio light; P90 4.8-4.9)**. W3's own maps
  were more uniform still (polymer BC std 2.3 levels). Under the review rigs' flat grey world, a dark rough surface has
  nothing to reflect, so roughness variation and edge sheen do not show either.

Fixes (spec R45):
- **Paint** (`smg_paint.py`, constants at the top): polymer roughness sheen fields at ~30 mm and ~8 mm
  (`SHEEN_BROAD` 0.25 / `SHEEN_MID` 0.22 x the fbm), recess dust on the polymer x 1.8, a settled dust film on up-facing
  faces (lighter, drier, wiped off in the handling zones), the phosphate's mottle x 1.8 and its own sheen field. Albedo
  mottle stays at the craft table's +-4 levels. Result on the shipped maps: **mean of the seven close-ups 3.28
  (grey-world rig) / 3.37 (studio rig), x 1.23 over the first pass; min P90 5.7** (`review/diag/maps_vs_clay.json`,
  reported). Polymer roughness std 0.085 -> 0.096; magazine 0.038 -> 0.059. A stronger setting (0.45 / 0.25: 3.88,
  x 1.42) was rendered and rejected by eye: at hero distance under the studio light the receiver read as camouflage
  clouds, which is a new fake tell, not realism. W2's gates all still pass (L5 colour on every region, G20 1.49).
- **Light for the realism views**: `gunlib/export_review_job.py` gains an optional `studio` rig: Blender's bundled
  `studio.exr` (CC0), made neutral (saturation 0), at strength 0.6 for light and reflections, plus the rough rig's
  softboxes at k 0.3; the camera still sees the flat grey 126 backdrop. `review/realism/<name>.png` (the judges' set)
  uses it; the same five views under the L5 calibration rig are kept in `review/realism/l5/`. The review set
  (`review/set/`) and the colour test stay on L5, so the colour calibration is unchanged. No AR-01 job uses the new
  rig (regression 14 / 14 equal).
- **Honest limit.** The surface is still a clean, lightly used polymer gun; the maps-vs-clay difference grew by a
  quarter, not by multiples, because the larger settings looked worse. Whether the close views now pass is for the
  realism judges on `review/realism/` (the studio set) to decide; the L5 versions are beside them for comparison.

| Tell | Verdict | Fix / reason |
|---|---|---|
| One flat matte material on every part: clay (8 calls) | REAL, fixed | Measured cause and fix above; plus C3-C5 (steel darker than the polymer, moulded texture, wear by cause) |
| No wear, edge rub, dust, grime (6) | REAL, fixed | C3, C4 (whitening, scratches), the R45 dust film and recess dust; the cavity grime and soot (m5) |
| Sparkle specks on the rail (2) | REAL, fixed | C3 (no cluster under 14 texels, none off an edge). The rail tooth crests still carry short bright lines by design (worn rail edges); judges to confirm |
| FP: the stock top "a thin curved sheet" (2) | Partly fixed | The cheek strut lies right under the 35 cm eye at a grazing angle; its matte top mirrored the grey world as one smooth light plane. It now carries the moulded texture, sheen variation, dust film and the parting line, under a light with structure. The geometry is the traced strut (26.7 mm, R 1.4 edges), unchanged |
| No markings (selector pictograms, serial, maker) (5) | REJECTED | The asset rule: generic, no markings (IP rule: no maker names); buyers add decals |
| Magazine "invented" ladder windows (1) | REJECTED | The sheet draws the ladder (two recessed channels crossed by flush ties: CRAFT 2.14, 4 ties on the LEFT trace) |
| Receiver panel lines, flat panels without draft (3) | Partly rejected | The seam is the sheet's drawn upper / lower split built as the real two-piece step (R43); side faces are formed by side actions (no draft; the openings' walls drafted 1 deg, CRAFT 2.1); the moulded texture and parting lines now read |
| Rear sight base a kitbash trapezoid / chevron inlay (2) | REJECTED | The generic rail-clamp BUIS base (RP15) as the sheet draws it |
| ADS: the front post a speck (2) | REJECTED | B4: the post tip centred in the 2.0 mm aperture at 0.25 m (lateral 0.0, vertical 0.0, post visible 0.99 mm): the true picture of a 1.85 mm post at 243 mm sight radius |
| Grip without stippling, thin guard, plain magwell (2) | Partly rejected | The stipple panels are built (W2 gate) and read at 35 cm, not at hero distance; the guard bar and the flare band are the sheet's and the real pattern's |
| Folded stock: pad grooves a greeble, hinge cap a placeholder, heavy arm (2) | Partly fixed | m3 (b): regular moulded ribs open at the sides; the hinge knuckle stack, axle and latch are built on the right (the view sees the left); the arm is the traced skeleton |
| Flat grey backdrop, even light (1) | REAL, fixed | The studio rig for the realism views (above). The first fix pass had rejected this to protect the colour test; the colour test keeps the L5 rig, so both hold |

The target "at most 1 single-judge fake call over the 4 views" is for the next judges' run, not self-judged here.

## 3. Blind test

Reported, not blocking: the 15 pairs were re-rendered from the new bytes (`review/blind/`, key
`review/blind_key.json`, same pair numbering and ours-B order).

## 4. Notes

- **Two LOD1 regressions from the first fix pass, found by W3's UD gates and fixed in the generators.** (1) The butt
  pad's grooves, cut open through the side rounds, left needle triangles against LOD1's 2-segment rounds: LOD1+ closes
  them inside the rounds again (1.2 mm at the ~2.6 m LOD1 switch is under 1 px). (2) The guard's 8-segment corner rounds
  put 0.3 mm chords on the guard's flat side faces at LOD1, and their triangulation left 2 needles 0.005-0.007 mm high
  (Unreal drops): LOD1+ uses the LOD count (4). LOD0 is unchanged by both, so W1 / W2 stand; W3 onward was rebuilt.
- **Order of the rebuild.** run_all.sh from nothing (W1 form 54 / 54 gates, W2, AR-01 regression) -> W3 failed UD at
  LOD1 (twice: the pad, then the guard) -> the two LOD1 fixes -> W3 from its first step (game, rig_export, mag pass) ->
  the R45 sheen set to its final 0.25 / 0.22 after the first full set of review renders showed the 0.45 clouds -> W2
  re-run from the paint step on the W2 blend (paint, recolour, Blender-side gates, L5, renders, gates: pass; W3 reads no
  texture, its FBX bytes are unchanged) -> the review renders and the fix record from the final bytes.
- **AR-01 regression process fixes** (`gunlib/tests/ar01_regression_compare.py`): a `test_parts` record without a final
  status (the process ended early once) is reported as incomplete instead of crashing the compare, and the byte check
  covers the AR-01's own blends only (`Assets/Guns` as a whole matched the SMG01 build's `SMG01.blend` and failed the
  row falsely). The regression now reads pass, 14 / 14 value groups equal.
- Triangles: the G3 rounds cost ~1,300 triangles on the gun; the four hidden rail-screw heads (36 -> 24 segments, 15
  deg, 0.02 mm chord) paid for most of them under the 50k ceiling. The barrel at the plan's 48 sides was tried and
  dropped (it pulled the barrel's texel density P5 under B9); the chamber chamfer 1.0 likewise (kept 0.6).
- The polymer base's blue 49 -> 48.5: with the moulded texture the trigger guard's shadowed L5 crop read 0.0535
  saturated (tolerance 0.05).
- gunlib changes (lock GunLib): `game.static_sphere_radius` (new), `parts/mag_box` (`roll`, `tip`, `ladder_cutters seg`,
  all optional with the old defaults), `export_review_job` (`studio` rig, optional), the regression compare fixes. The
  AR-01 regression was re-run on them (`gates/gunlib_regression.json`).
- The review renders, the realism set (studio + L5) and the blind pairs are rendered from the new exported bytes
  (sha256 in `gates/review_export.json`).

---

# W4b close-up realism pass, round 1 (spec R46)

Both realism judges failed all 12 close views of the R45 set (fp_35cm, ads_55deg, hero_34, hero_34_folded, studio + L5).
Each reason was checked against the renders, the maps and the real photos (`scratch/realref/craft`: the UMP-pattern
photos show an even black satin polymer, matte black steel parts, and wear only at edges and contact points). Diagnostic
looks (clay / clay + normal map / BC emission) separated geometry, normal map and albedo. Everything was rebuilt from the
paint step (the FBX bytes are unchanged; W3 reads no texture) and rendered from the exported bytes: `review/closeup_r1/`
(5 views x {realism rig, L5 rig} + 3 close-ups at ~21-24 cm + `before_after.png`). The numbers are in
`gates/closeup_r1.json` (K1-K7, all pass). `review/realism`, `review/set` and the blind pairs were re-rendered too.

## Measured causes and fixes

| Tell (judge calls) | Verdict | Cause (measured) | Fix | Evidence |
|---|---|---|---|---|
| Large, soft, cloudy grey / white blotches on the receiver and stock: noise / concrete (5) | REAL, fixed | R45's sheen fields (roughness +-0.12 at 30 / 8 mm) and albedo fields (+-22 % at 9 mm, +-25 % at 25 mm), plus a per-texel speckle (+-35 % at 0.6 mm, 2 px at 35 cm), spread evenly over every flat | Clouds cut to a trace: sheen 0.05 / 0.05, albedo 0.10 / 0.06, speckle 0.14. The variation now sits where real wear puts it: a handling rub on every exposed convex edge (0.2-0.7 mm, up to +35 % linear, rough -0.10), dust as a grey-beige deposit in the deep recesses and against inside corners (no fbm patches) | K1 band-pass std / mean on the hero receiver flats 0.027 -> 0.006 and 0.029 -> 0.009 (x 0.22 / x 0.30); polymer BC std 3.74 levels (G15 >= 3.0, now from edges and recesses) |
| Mid-grey clay, not black polymer; the top washed out (4) | REAL, fixed (realism rig) | R45's studio rig (studio.exr 0.6 + softboxes k 0.3) lit the receiver side to sRGB 80, 1.96 x the L5 calibration's exposure (the L5 rig is fitted to the sheet) | The realism rig is the bundled interior.exr (CC0) at 0.45 + softboxes k 0.12: window light with structure, exposure near the calibration. studio.exr 0.32 / k 0.16 and courtyard 0.35 were rendered and read flatter | K2 ratio 1.96 -> 1.17 (hero receiver 42.6 vs L5 36.6) |
| One material: steel sights, rail, device = the polymer (6) | REAL, fixed | Roughness overlapped: polymer 0.58-0.66, phosphate 0.62-0.76, both flat in the normal map | Polymer a satin 0.50-0.58 (hand 0.44) with its moulded grain at 12 / 20 um; phosphate a dead-flat crystalline charcoal 0.66-0.78 (oiled 0.56-0.66) with a +-4 um crystal grain in the normal map. Its base went from (40, 41, 42) to (45, 46, 47) so the L5 render keeps the sheet's receiver / steel ratio (at (40, 41, 42) / 0.70-0.82 G20 read 1.635); the base stays under the polymer's (46, 47, 48.5) | K5 roughness P50 0.795 vs 0.554 (split 0.24, was ~0.02); G20 1.537 (sheet 1.453, band <= 1.55); L5 colour pass on every region |
| ADS: a centre seam down the receiver rear face and the stock head (4) | REAL, fixed | Not UV: one island crosses Y 0 (checked per island). It was the painted mid-plane parting line (+0.02 mm, +12 %) on every face crossing Y 0, including the lower receiver's rear face and the stock head's top | The parting line only where a two-half tool parts on a strap or narrow face: grip / guard / magwell (lower receiver under Z -40), the grip cover, the magazine, the stock's struts (X < 218) | K3 centre-column contrast 3.77 -> 0.69 sRGB levels |
| White specks / fireflies on the rail teeth, the sight drum and the base edge (4) | REAL, fixed | Bare steel (metallic, sRGB 190) at rough 0.42-0.55 on 1-2 px dashes reflected the light's hot spots | Bare 0.50-0.62 (the AR-01's realism value); on the top rail (the player's view) bare only on the most-worn crests, the rest rubbed phosphate | K4 pixels >= 235: fp 8 -> 0, ads 72 -> 4; bare still edge lines (clusters >= 14 texels, 0 off an edge, 0.60 % of the steel) |
| No edge rub on the rail, sight ears, crown, mag lips, knob; no hand polish (3) | REAL, partly fixed | Polymer edges had whitening only in the zones (0.34 % of the polymer); the hand-polish clamp switched at half weight and drew a hard-edged lighter disc on the fore-end in the 24 cm close-up | The edge rub (above); the polish clamp blended (0.25-0.85). The steel's rubbed edges and bare crests are as in W4. The gun stays lightly used (spec wear_level 'moderate') | c1-c3 close-ups; Masks R / G |
| No markings: selector letters, serial, roll marks, witness numbers (3) | REJECTED | - | Asset rule: generic, no markings; buyers add decals. Pictograms on the selector were also rejected in W4 | - |
| The stock head nearest the camera: a flat slab with wavy, paper-like edges / blocky (5) | REAL, NOT fixed in r1 (geometry) | Clay renders show it is the geometry: the head's top follows the traced S-curve, and the r1 / r2 plan flare cuts meet that curve in wavy edges with R 1.0 rounds. The seam and the clouds on it are gone, but it still reads as a bent sheet at 35 cm | Round 2 candidate: the flare as moulded blends (outer rounds ~R 2.5-3 on the head, no straight plan cuts across the curved top). This needs the full chain from W1 (~2 h for W1 alone), so round 1 isolated the finish | `review/diag` clay look (scratch), closeup_r1 fp / ads |
| The receiver rear face a large flat block with crude stepped chamfers (2) | DEFERRED with the head (geometry) | The traced end block and its 45 deg top chamfers | Judge again on r1; r2 if it is still called | - |
| Ball charging knob a sphere primitive, oversized (4) | REJECTED | - | The sheet's knob (LEFT + TOP + 3/4: dia 16.8, protruding 19 mm; spec charging_handle authority). It is built with its flat 7.0 crown, a polished crown and a bright rim (CRAFT 2.3) | spec R-merge 'knob at rest where drawn' |
| Small round pin dots look arbitrary (1) | REJECTED | - | The sheet's drawn pins and rivets at their traced positions | trace |
| Hinge barrel a plain stack of cylinders with no pin detail (1) | REJECTED | - | The knuckle stack and the axle head (visible on top, round) are built per spec stock_hinge; the latch is on the left | - |
| Engraved panel lines = decal grooves; magazine ladder invented (2) | REJECTED (as in W4) | - | R43's real two-piece step; the sheet draws the ladder | - |

## Gates

- `gates/closeup_r1.json`: K1 clouds, K2 exposure, K3 seam, K4 glints, K5 material split, K6 every stage gate of the chain
  (form, form_magfit, uv_bake_paint, game, rig_export, mag, review_export, gunlib_regression: all pass), K7 set complete.
- W2 re-run from the paint step (paint, recolour pre-check, Blender-side gates, L5 refit k 1.2035, renders): pass. On the
  way the first R46 maps failed L5 (grip luma -0.059: the satin receiver lowered the fitted light) and G20 (1.635). The
  stipple went to 0.72-0.82 and pebbles x 1.24, the phosphate base to (45, 46, 47) and 0.66-0.78: grip -0.047, G20 1.537,
  both inside tolerance.
- gunlib was not changed in this round, so the AR-01 regression stands (gunlib_regression pass). The FBX bytes and W3's
  gates are unchanged; review_export.json carries the new texture hashes.

## Honest status

The finish-level tells (clouds, clay exposure, one material, seam, glints) are fixed and measured. The FP and ADS
foreground is still the geometry of the stock head and the receiver's end block. It reads cleaner now, but at 35 cm it
can still look like a bent sheet or a plain block, which is the likely remaining fake call. The realism verdict belongs
to the judges, on `review/closeup_r1/` (realism rig; the L5 versions are in `l5/`).

---

# W4b close-up realism pass, round 2 (spec R47)

Both realism judges failed every r1 close view (studio + L5, plus the three close-ups and before / after). Each reason
was checked against the r1 renders, clay / BC-emission / clay+normal looks of the exported bytes, the maps, the sheet's
3/4 view and the real photos (`scratch/realref/craft`). The fixes are in the generators; the chain was rebuilt from W1
(the shading change is a W1 change): W1 (blockout, form, magfit gates), W2, the AR-01 regression (gunlib changed), W3,
the W4 review renders and fix record, then `review/closeup_r2/` from the exported bytes (5 views x {product rig, L5 rig}
+ 3 close-ups at ~21-24 cm + `before_after.png` against r1 + `diag/clay_before_after.png`). Numbers:
`gates/closeup_r2.json` (K1-K8, all pass).

## First: do the review renders show the final maps?

Yes. The game material wiring is right (BC sRGB, ORM linear R AO / G rough / B metal, N DirectX green flipped back,
UV0); BC-emission looks show every painted feature. The denoiser was checked (1024 samples without it): it softened the
fine grain but was not the cause of "one flat clay". Three measured causes:

1. **The rig.** The r1 rig (interior HDRI 0.45 + four softboxes at k 0.12, 0.8-3.6 W) put nothing bright in the mirror
   direction of any flat. On a black dielectric the 4 % specular IS the look: with no reflection to carry, a 0.55 satin
   and a 0.80 phosphate both render as diffuse black-grey, which is "one material" and "clay". Brighter softboxes only
   gave brighter grey clay (66 on the receiver side, 1.8 x the L5 exposure); mirror-placed boxes gave sheen and a
   visible steel / polymer split.
2. **The wear was too faint to reach any render.** r1's edge rub was +6 sRGB levels, its specks and scratches +2-4: a
   multiplied albedo step from 0.028 to 0.04 linear is swamped by the coat's specular. The BC map had them; the lit
   image did not.
3. **The stock head's banding was geometry shading, not texture** (below).

## Measured causes and fixes

| Tell (judge calls) | Verdict | Cause (measured) | Fix | Evidence |
|---|---|---|---|---|
| Stock head in FP / ADS: a smooth slanted sheet, "bent ribbon", banded with soft smeared streaks, cloth-like (8) | REAL, fixed (shading); geometry kept | `smg_parts._flatten_planar` grew regions within 3 deg / 0.6 mm of a seed and set each to ONE plane normal: every gently curved prism surface (the stock's S-curved top strut and head, the strut bends, the grip strap and toe, the magwell flare, the pad top) was shaded as 3-6 deg flat bands with the gradients piled at their borders. Clay renders of the r1 bytes show the stripes; the maps are not involved | A region whose face-normal deviation follows a smooth field (linear fit on position, area-weighted R^2 >= 0.8, span >= 1.5 deg, carried by >= 3 faces) is CURVED: corner-angle weighted smooth normals, no sharp marks inside it; true flats (receiver flanks, stock sides, pad sides: R^2 0.01-0.4; the rear sight leaf's face with one 2.6 deg repair face: 0.72) still flatten. W1 onward rebuilt | K1: shading spread / geometric spread over the 22 curved LOD0 regions 0.27 -> 0.98 (`smg_curved_check.py`); `diag/clay_before_after.png` |
| One flat charcoal value with one roughness; steel (device, barrel, sights, rail, pins, trigger) = polymer (all) | REAL, fixed | Cause 1 (the rig); the maps' split (0.55 / 0.80) was right but nothing showed it | Product rig (`smg_review_export.STUDIO`): a long softbox in the mirror direction of the side face the camera sees, nudged up so its edge crosses the face as a sheen gradient; one in the top faces' mirror direction; two narrow strips behind-left / right for the edges; a weak key; interior HDRI 0.15 for ambient reflections; backdrop sRGB 150 (the sheet's reads 151); no denoiser, 1024 samples. The polymer a step glossier (0.47-0.55, hand 0.41; magazine 0.48-0.58) | K2 receiver side 43.7 vs L5 35.3 (1.24, <= 1.3: still black); K3 roughness P50 0.795 vs 0.526 (split 0.27), G20 1.543 |
| No wear, polish or edge rub on rail edges, sight ears, crown, magwell lip, mag feet, hinge, stock pad; razor-clean edges; CG-clean slabs (all) | REAL, fixed | Cause 2: r1's rub / scuffs / specks were multiplied steps of +2-6 levels | Wear MIXES toward a worn grey: polymer edge rub to sRGB 100 at the crest, 0.35-1.0 mm wide, polished (rough -0.22) so it also catches the strips; scuffs (a fore-aft and a set-down set) to 96 on the receiver, stock, magazine and grip-cover flats, the lower body favoured; the sheet's specks to 112; worn phosphate edges to 100 (rough -0.14). The spec's wear level stays 'moderate, as the sheet (white specks and edge scuffs)' | K6 polymer BC P99 - P50 13 -> 27 sRGB levels (magazine 37); c2 / c3 close-ups |
| No mould texture / roughness breakup; flats perfectly uniform (4) | REAL, fixed | r1's moulded grain (12 um at 0.6 mm) is sub-pixel at 35 cm; its 1.8 mm orange peel (20 um) read as cast concrete once a softbox grazed it | Peel to 5 um; a 0.25 mm spark grain (5 um, +-0.025 rough) carries the matte skin; handling smudges +-0.07 roughness at ~3 mm on the open faces (no low-frequency clouds: those were r1's "blotches") | c3 front face, c1 receiver top |
| Bright white hairline glints / slivers on random edges of the rear sight, its base, a rail tooth (4) | REAL, fixed | The sights' bare-steel dashes: 1-3 px metallic (sRGB 190) lines on the base corners, cheeks and drum | No bare steel on the sights or the selector; their edges rubbed phosphate, the drum's knurl crests rubbed | K5 0 bare texels there; K4 isolated hot pixels on fp / ads / c1: 0 / 3 / 0 (two on the hinge axle head's ring, one on the base edge) |
| Thin bright rim on the charging knob face; one bright white diagonal line on the selector (2) | REAL, fixed | The knob's bare rim (CRAFT 2.3) and the selector's bare lever edge; the selector disc also carried the phosphate mottle (a dark diagonal blot at 23 cm) | The knob rim a rubbed satin ring (x 1.9, rough 0.40); the selector bare-free, its mottle x 0.25 | c2, c3 |
| Vent walls and bore flat grey, no depth darkening (2) | REAL, fixed | r1's dust mixed 30 % toward sRGB 94 into every deep recess, walls included | Dust on floors only (up-facing, 12 %); recess walls darkened x (1 - 0.28 cav); the bore's soot as before | c3 vents |
| Butt pad ribs read as hard plastic, not rubber (2) | PARTLY | The rubber already differs (0.82-0.92 rough); at hero distance it reads by shape | Rubber rub at half the polymer's (scuffs grey, no polish); with the glossier satin round it the matte pad separates | hero_34_folded |
| Faint circular shading disc below the charging knob (1) | REJECTED | It is the knob's own soft shadow from the r1 key (BC-emission and clay looks show nothing there) | - | - |
| Receiver rear face a plain box: no sling point, latch button, texture (2) | PARTLY | The sheet draws no sling point or latch on the end block's rear face (the rear sling point is the stock's lower hole); inventing one breaks "invent nothing" | Finish only: rubbed edges and corners, scuffs, grain; under the product rig the face reads as black moulding | ads_55deg |
| Hinge cylinder's flat bright top cap like a primitive (1) | PARTLY | The knuckle's top and the axle head are the spec's (stock_hinge); r1 lit the cap's flat top directly | The rig no longer floods it; the cap carries the finish and a rubbed rim. Geometry unchanged | ads_55deg |
| Sight base and its rear ramp read as thin sheets laid on the receiver (1) | REJECTED (geometry) | The base's raised rear is the sheet's drawn shape, 2-7 mm thick; r1's flat light hid the step's shadow | Product rig (the step now shades) | c1 |
| No markings: roll marks, selector pictograms, serial, mag capacity, slot numbers (all) | REJECTED | - | Asset rule: generic, no markings; buyers add decals (as in r1 and W4) | - |
| Diagonal V grooves / panel lines beside the magwell look invented / decorative (2) | REJECTED (as in W4, r1) | The sheet's two-piece step (R43) | - | - |

## Gates

- `gates/closeup_r2.json`: K1 curved shading 0.27 -> 0.98; K2 exposure 1.24; K3 split 0.27 with G20 1.543; K4 isolated
  hot pixels 3 (<= 5); K5 sight / selector bare 0; K6 wear spread 13 -> 27 levels; K7 every stage gate of the chain
  (form, form_magfit, uv_bake_paint, game, rig_export, mag, review_export, gunlib_regression): pass; K8 16 images.
- W2 on the way: polymer 0.40-0.48 first failed L5 (grip luma -0.061, tolerance 0.05) and G20 (1.636); 0.46-0.54 with the
  stipple x 1.34 and the phosphate base (46, 47, 48) passed L5 but G20 read 1.552; 0.47-0.55 passes both (G20 1.543,
  L5 k 1.13, every region inside tolerance).
- W4 review export R3 (frames not cut) now measures each frame against its own backdrop (the realism rig's is 150); the
  W4 fix record's C2 accepts the knob's rubbed rim ring. gunlib changed (export_review_job: optional `extra_lights`,
  `mirror_n_M`, per-shot `denoise`; no AR-01 job uses them): the AR-01 regression re-ran and passes.
- W3's G5-visible measure at LOD3 (recorded beside the depth gate, not a gate) reads worst mean 1.805 px.

## Honest status

The finish-level tells of r1 (one value, no sheen, no wear, slivers, grey vent walls) and the stock head's banding are
fixed and measured. The stock head's curved top keeps the traced wave (slope 0.15 -> 0.5 at X 226-238 in the side view,
the sheet's own profile): with smooth shading it reads as a moulded curve, but a soft highlight still runs across it in
FP / ADS, and a judge may still read the head as a bent surface; reshaping it would leave the trace. The realism verdict
belongs to the judges, on `review/closeup_r2/` (product rig; the L5 versions in `l5/`).
