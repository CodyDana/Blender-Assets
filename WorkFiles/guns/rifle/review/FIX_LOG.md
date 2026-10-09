# AR-01 stage 7 "apply fixes": fix log

Source of the findings: `review/REVIEW_RESULTS_paused_2026-10-07.json` (craft review L6: 8 major / 6 minor / 2 notes;
tech review: 1 major / 8 minor / 4 notes; two realism judges on review/realism; one blind judge, 12/12 picked).
Every finding below was checked against the exported bytes and the generators before it was fixed or rejected. Fixes
are in the generators only; every output was rebuilt (run_rifle.sh -> run_game.sh -> run_rig_mag.sh) and every
stage-2..6 gate re-run. Numbers come from `gates/form.json`, `uv_bake_paint.json`, `game.json`, `rig_export.json`,
`mag.json`, `review_export.json` and the summary in `gates/review_fixes.json`.

## 0. The paused run's partial fixes (START STATE)

| Partial fix (571dfb7a) | Verdict | What was done |
|---|---|---|
| `gunlib/edgemask.py` + `bake.dump_tris`: edge masks from the true dihedral edges, not the bevel-node bake | Kept, finished | Measured as 3D distance, it printed the FAR side of thin walls (the liner channel's outline on the upper handguard, rails behind the 1 mm receiver sheet). Added same-side weighting (edge face normals vs the texel normal) and a cache version |
| `rifle_paint.py`: chips only on true sharp edges, cluster field, zone-only scratches in mixed directions, brake soot, rail-strip-only carrier polish, sparse along-grain dents, groove-only checkering tone, rigid handguard grain | Kept, finished | Added the magazine's own wear zones, a carbon colour for chips on the brake lip (the partial code left 122 light dielectric texels there), and the wear audit |
| `paint.scratch_patches`, `flow_coords(rigid)` | Kept | as written |
| `rifle_surface.py`: bluing rough 0.45-0.55, cover / charging-handle zones | Kept, tuned | charging-handle zone r 12 / w 0.6; button zone r 12 / w 0.6 (a light halo round the button hole in first person) |
| `rifle_uv.py`: visibility retry at the face corners | WITHDRAWN | It re-classed ~600 mostly interior faces and fragmented their islands (1601 -> 1846): Metal fill 0.649, Mag 0.636, under the 0.70 / 0.65 gates. The wedge it targeted came from the bake margin (finding 2) |
| `export_review_job.py` | Kept, extended | see finding 7 and the clip pose fix |

## 1. Craft review (L6)

| # | Finding | Verdict | Fix / reason | Evidence |
|---|---|---|---|---|
| M1 | Wear as fake triangles and dashed seam lines (mag, magwell, guard, brake collar) | REAL, fixed | Three causes. (a) The bevel-node edge bake followed interpolated normals over long CDT slivers: replaced by the geometric same-side edge field. (b) **The bakes' 16 px margin**: Blender writes each object's bake with its own margin, so a part's extension overwrote the border texels of neighbouring islands (Furniture: 62,485 valid texels carried another part's position, e.g. the upper handguard strip at X 594-595 held the stock seat at X 248): every pass now bakes with margin 0 and the texel-size estimate is island-aware. (c) The magazine's chips now only inside its real wear zones (feed lips, lugs, spines at the well, floor plate) | wear audit: 0 bare clusters on panel interiors (Metal, Mag); largest bare blob 3.19 mm2 Metal / 3.25 mm2 Mag (gate <= 8); `review/set/mag_34_2x.png`, `mag_left_2x.png`, `receiver_right_3x.png` |
| M2 | Bright wedge on the receiver's right wall at the magwell | REAL, fixed | The bake-margin overwrite (M1 b) gave wall texels a neighbour part's position / normal, so they painted as a lit sliver. Margin 0 | `review/set/receiver_right_3x.png`, `reload_magrockstart_right_3x.png`: no wedge |
| M3 | Receiver an empty shell at full bolt travel; no bolt head, no chamber | REAL, fixed (geometry) | The real pattern's rotating bolt (r 7.6, case-head recess, firing-pin hole, extractor claw high on the right) rides in the carrier; the carrier's full section ends at X 397.5 (only its upper body runs forward); the bolt head runs in a bore (r 8.0) through the trunnion's rear to the breech; the trunnion stands up to Z 8.0 over the barrel's rear end (X 434-452); the rails end at 433.98; the gas piston rides with the carrier (bone bolt). The review's bolt frames are now posed with the selector at Auto (the clips) and lit by the L5 rig plus a weak port fill | B3 bolt sweep 0 intersecting steps (min 0.25 mm), G5 0; `review/set/bolt_rear_right_3x.png`, `bolt_rear_34_above.png`. Residual: the open receiver interior is dark under the physical rig (black lacquer, light only through the port) |
| M4 | Fire / Charge / Reload clips with the selector on SAFE | REAL, fixed | Every clip except A_AR01_Selector holds the selector at Auto (16 deg) start to end (loop-equal); the game layers the real fire mode per bone (README). The review job now poses from the clip armature's absolute bone matrices (Blender's importer takes an animation FBX's node defaults as rest, which hid a held selector) | rig_export clips read back <= 5e-05 mm / 1e-05 deg; `review/set/bolt_rear_right_3x.png` lever down |
| M5 | Magazine catch a melted chrome lump | REAL, fixed (geometry) | One flat stamped paddle (+-5.0 on the traced outline) on the tongue, crisp 0.3 bevels, flat-shaded (sharp at 30 deg), satin bluing 0.45-0.55; the T-section rib + wings removed | B3 mag_release 0 steps (min 0.102 mm), MAGFIT F5 0, M3 rear lug to catch 0.20 mm; `review/set/receiver_right_3x.png` |
| M6 | Upper handguard: vertical line and liner trapezoid printed on the wood | REAL, fixed | Trapezoid: far-side edges through the thin wall (edgemask same-side). Line at X 595: the bake margin overwrite (M1 b), measured at texel (913, 1724): margin 16 gave X 248.1 (stock), margin 0 gives X 594.3 | `review/set/lod_strip.png` LOD0 handguard; `review/realism/hero_34.png` |
| M7 | Set / realism renders lit by the near 'rough' rig | REAL, fixed | `review/set` and `review/realism` are lit by the L5 physical rig (scratch/game/l5.json, k 1.34) centred on each shot; the blind pairs keep their panel-matched rigs (same numbering and key) | `gates/review_export.json`; `review/realism/contact.png` |
| M8 | Faceted rivet heads (G3) | REAL, fixed | 8 -> 24 segments (15 deg), smooth-shaded crown; one profile ring fewer (4n triangles) to stay under the 50k ceiling. G3's 7.5 deg is a barrel-size rule: on a 2.55 mm head 24 segments leave a 0.022 mm chord error (0.19 px at the 3x review scale) | B8 rifle LOD0 49,474 (ceiling 50,000) |
| m1 | Small parts polished to chrome (knob 79 % bare, selector flash, carrier smear) | REAL, fixed | bluing rough 0.45-0.55, bare only on true edges, carrier polish only on the rail strip, knob zone narrowed | charging knob bare fraction 0.0001 (gate <= 0.25) |
| m2 | Brushed-aluminium hairlines over the receiver / front sight | REAL, fixed | scuffs only inside handling / sling zones, 6 mm, direction per patch, half contrast | `review/set/receiver_right_3x.png`, `brake_front_sight_right_3x.png` |
| m3 | Hammered pock dents on the wood | REAL, fixed | sparse dings stretched along the grain, mineral streaks, pores, end grain | `review/set/lod_strip.png`, `review/realism/hero_34.png` |
| m4 | Front sight window a near-rectangle | REAL, fixed (geometry) | rear edge exactly parallel to the tower's rake (3.57 mm over 9.6), tighter corner rounds | `review/set/brake_front_sight_right_3x.png`; L2 per-part 21/21 |
| m5 | Brake interior as grey as its outside | REAL, fixed | soot deepening into the chamber, carbon on the slant lip (dielectric) | `review/set/brake_front_sight_34_3x.png` |
| m6 | LOD2 stock faceted, LOD3 checkering black triangles | PARTLY fixed | LOD1-3 wooden parts take LOD0's shading normals (DataTransfer, custom normals): the LOD2 stock now shades smooth in clay. Remaining: LOD2 / LOD3 sample the LOD0 atlas through island-snapped UVs, so the coarse stock shows grain blocks and the LOD3 grip a coarse checker; both only from 6.8 m / 20.3 m, where LOD-pop measures max 1.80 / 1.41 px | `game.json` LOD-pop; scratch diag `stock2_clay.png` |
| n1 | Gas tube latch lever a through slot | REAL, fixed | a 0.7 mm floored recess in the 1.6 mm link | form gates pass |
| n2 | Passing items | - | none | - |

## 2. Tech review

| # | Finding | Verdict | Fix / reason | Evidence |
|---|---|---|---|---|
| T1 (major) | Bare steel as whole flat triangles on the Mag set; the chip gate measured the rifle only | REAL, fixed | as craft M1; new gates on every set: bare clusters on panel interiors, largest bare blob per set, wood grey chips, knob bare fraction (`rifle_paint.wear_audit`, `rifle_stage34_gates`). The magazine's AO / edge passes now bake on the magazine ALONE (seated, its top baked the receiver's shadow: AO 0.04-0.25 on visible faces, dark triangles once removed) | `uv_bake_paint.json` stage-7 rows |
| T2 | Magwell wedge | REAL, fixed | craft M2 | as M2 |
| T3 | Twin SM_AR01 LOD1-3 magazine not the shipped one | REAL, fixed | `rifle_maglod.py`: one recipe for SM_AR01_Mag and the twin (LOD0 parts collapse-decimated, joined, UV overlaps separated); new gate | `mag.json` "Twin magazine = SM_AR01_Mag at every LOD": 6666/1998/648/248 both, 0.0 mm; twin LOD1 24,460 (44.4 %), LOD2 9,098 (16.5 %) |
| T4 | LOD3 floor not enforced; LOD0 above target | RULED | R52 in the spec: the blockout LOD3 (~1,100) is accepted (LOD-pop max 1.41 px); LOD0 49,474 is reported against the 30-45k target and the 50k ceiling | `rifle_spec.json` R52 |
| T5 | Grip checkering: LOD0 modelled cuts? | OPEN for the user | The user's wording ("real modelled cuts baked to a crisp normal on lower LODs") can mean cut geometry on LOD0; that costs ~3-6k triangles against a 50k ceiling at 49.5k. Default kept (normal map from the modelled field on every LOD), recorded in R52 | - |
| T6 | Clip node defaults = a clip pose | PARTLY fixed | The scene is parked before the clips while they are written, so the defaults are each clip's START pose (bind pose for every bone except a selector held at Auto) instead of frame 1's (bolt 2.03 mm, trigger 12 deg...). Blender's FBX exporter writes the first baked frame as the default; changing that needs the shared pipeline exporter, left untouched. Unreal plays the absolute curves (unaffected); README tells Blender users to read absolute matrices; the review job does | raw FBX: `bolt` Lcl Translation = rest head, `selector` Lcl Rotation Y 16 |
| T7 | ShellEject at frame 2 | REAL, fixed | frame 3 (the rear stop) | sidecar notifies |
| T8 | Magazine 27.5-29.0 mm at ribs / floor plate vs R32 26.0 | RULED | the ribs are pressed OUT as on real steel magazines; 26.0 is the body; 29.0 the floor plate; the ribbed part never enters the well (M2 / M3 unaffected). R52 | `rifle_spec.json` R52 |
| T9 | No README / MATERIALS_README in Exports | REAL, fixed | written: import settings, colour spaces, texture groups, LOD sizes, socket recreation, FP/TP components with ForcedLodModel, selector layering, physics mass, notifies | `Exports/Guns/AR01/README.md`, `MATERIALS_README.md` |
| N1 | FBX embeds the absolute source path | NOTE, not changed | pipeline-wide (`Scripts/pipeline/export_fbx.py`, also katana / fan); for the pipeline owner before Fab | - |
| N2 | LOD1-3 point-mapped / flipped UV on hidden faces | NOTE, not changed | hidden faces only; the port-visible bolt / carrier / trunnion faces are LOD0 / LOD1 with real UVs; no new gate this round | - |
| N3 | Spec / plan texture sizes drift | FIXED | R52 + `textures.sets_shipped_2026_10_08` (Metal 4096, Furniture 2048, Mag 1024, Detail16 1024) | `rifle_spec.json` |
| N4 | LOD2 2.8 mm wider on the left | NOT changed | LOD-pop passes (max 1.80 px); the generator's coarse radius; left for the LOD pass | - |

## 3. Realism judges (review/realism, 2 judges x 4 views: 5 fake calls)

| Tell | Verdict | Fix / reason |
|---|---|---|
| Pale, chalky, clay-like dust cover in FP / ADS | Mostly the lighting rig (fixed: L5 physical rig); the cover's base colour stays where L5 measures the sheet (cover 89 vs receiver 63 sRGB, delta -0.025 luma) | A glossier cover (0.30-0.42) was tried and read lighter at the ADS grazing angle: not adopted |
| Lumpy / blotchy cover, dark speckle, white specks along the rear edge | REAL, fixed | dust / wipe slabs and oil blotches removed from the crown, edge-only wear, the button halo narrowed |
| Orange, saturated wood | REJECTED | the sheet's walnut IS saturated (L5: stock sat 0.61 R/B 2.57, grip 0.51 / 2.04, handguards 0.59 / 2.47 and 0.53 / 2.12); under the near rig it read orange, under the L5 rig it reads walnut-red |
| Wallpaper / swirly procedural grain; plastic sheen | Partly fixed | form-following grain, irregular ring widths, mineral streaks, pores, sheen wander along the grain |
| Upper handguard painted line and blotch | REAL, fixed | craft M6 |
| Checkering a dark decal patch | REAL, fixed | only the grooves darken |
| Generator-style white streaks on the magazine | REAL, fixed | magazine wear zones; craft M1 |
| ADS: no front post in the notch (judge A) | REJECTED | B4: post centred (lateral 0.0, vertical 0.0127 mm); textured ADS check: post visible 158 px, tip 0.5 px from the projection, Weber -0.34; judge B and the craft review saw it |
| Charging knob a glossy blob | REAL, fixed | m1 |
| Butt plate rim a noisy light band | NOT changed | the sheet's butt plate is scratched steel by design (c7); the rim is that plate's edge |

Target "at most 1 single-judge fake call over the 4 views" is for the next review; not self-judged here.

## 4. Blind test (12/12 picked, reported, not blocking)

Design tells checked against the main views and the real pattern:
- Selector "a short wide paddle" (pairs 01, 04, 05): REJECTED. The close-up c1 and the real stamped lever are a broad
  plate (it closes the cover's slot); only the 1.3 mm/px side view reads it as a thin line: a sheet self-contradiction.
- Upper handguard "extra seam", "angular stepped vent": the seam was the bake-margin line (fixed, M6); the vents are
  the sheet's two lower-edge gaps (kept).
- Checkering "dark inset panel": fixed (grooves only).
- Mag "white chip", "speckled edges" (pairs 08, 09, 12): fixed (M1).
- Dust cover "plain box, no ribs" (01, 03, 05, 06): REJECTED, R50 (the sheet draws a smooth cover).
- True-left "selector and S stamping" (02): REJECTED, the RIGHT panel is a mirror of the left (self-contradiction).
- Stock-side plate, screw slots, buttplate rim (02, 11), brake framing (07), floor plate height (08, 09): the sheet's
  close-ups contradict the main views or each other (R36); main views + real pattern kept.
- Render tells (soft studio light, procedural wood, flat metal): AI-photo vs render differences, not design.
