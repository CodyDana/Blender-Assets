# SK_Fan: build report (folding fan / sensu, skeletal prop), final pass (round 3)

**Date:** 2026-09-26. **Build:** `Scripts/props/build_fan.py`, from scratch, no arguments (Blender 5.2.0 LTS, headless,
`--factory-startup`, 228 s with the fold cache `cda0c70b3b254fad`; `WorkFiles/fan/run_fold_optimisation.py` rebuilds
the cache in about 12 min). It rebuilt `Assets/Fan.blend`, `Exports/Fan/` and `Renders/Fan/`. Logs:
`WorkFiles/fan/final_build.log`, `final_verify.log`. Report: `WorkFiles/fan/fan_report.json`. The round-2 report is kept
as `WorkFiles/fan/round3/FAN_REPORT_round2.md`.

Scope, as the user asked: the SHAPE and the MECHANISM of fan2 (fan1 as a cross-check), with no surface design. The leaf
and ribs are plain black, the ribs are solid (no piercing; that is design, for a later stage).

## Status

| Check | Result |
|---|---|
| Build gates (`fan_report.json` `gates`) | **26 of 26 pass**, including the new see-through gates G5, G5b and G5c |
| Blender re-import of the shipped FBX (`Scripts/props/verify_fan.py`) | **V1-V6 pass**: every key and half key of every clip, stretch 0.00013 mm, crack 0.0836 mm, 0 intersections |
| Unreal 5.8.3, standalone (`/Game/FanCheck/Final_0926r3b`, pass 1 import, pass 2 fresh process with a real RHI) | **U1-U11 pass** (U10 and U11 are new: the mesh's own bounds extension holds the leaf without the physics asset; Loop flags and bone compression are as the sidecar says) |
| Unreal 5.8.3, the PACK's assets (`/Game/NinjaPack/Meshes/Fan`, with MI_Fan_*) | **U1-U11 pass**; renders show the real instances (`WorkFiles/fan/UnrealCheck/final_r3_pack/ue_pack_fold_sheet.png`) |
| Materials build (`Scripts/unreal/materials/run_build.sh`, runs `fan1`, `fan2`, `fan3`) | `fan2` and `fan3` verify **passed** (functions, masters, instances, meshes, textures, dependencies, accounting); their dumps and node layouts are **byte-identical** (idempotent) |
| Existing items' materials | `dump_fan3.json` against the materials job's final `dump_f2.json`: **no change and no removal**; 28 additions (8 fan instances, 2 fan meshes, 15 fan textures, and the new `used_with_skeletal_mesh` key on the 3 masters: True on Fabric and Steel, False on PaperInk) |
| Existing items' exports | `WorkFiles/materials/survey/check_exports_frozen.sh`: **63 of 63 identical**, no new files beyond the materials job's own 18 |
| Frozen scopes (`WorkFiles/fan/regression/fan_regression.py`) | 232 of 232 frozen files identical (other items' blends, exports, renders, the shuriken scripts, the other props' builders and libraries, the whole pipeline incl. `skeletal_prop.py`), nothing added; materials code: only the 7 allowed files changed, 2 files added |
| Pipeline | **not touched** this round (`Scripts/pipeline/` identical), so its tests were not re-run; they passed in round 1 on these exact bytes |
| Processes | No Unreal or Blender process of this pass is left running; the other session's `UnrealEditor.exe` windows were not touched; no lock was claimed or released |

## 1. Blind-test history

| Round | Judge picked the copy | What it keyed on | What changed next |
|---|---|---|---|
| 1 | 15 of 16 pairs | pleat shading anti-phase with fan2, zigzag edge, flat facets, bright inner-edge dots, cone tassel | round 2: fold alternation flipped and fitted to fan2's notches, sinusoid edge, thread tassel |
| 2 | 16 of 16 (all confident) | cold neutral colour cast, rounded "tube" pleats, bright dashes at the leaf's inner edge, dull rivet, clean tassel, flat rib zone, no micro-texture | round 3 (this pass, below). No round-3 blind test was run (maintainer pass) |

## 2. What this pass changed, issue by issue

### Blocker and majors

| # | Issue (from) | What was done | Measured |
|---|---|---|---|
| B1 | Light dashed arc along the leaf's inner edge, every opening, every LOD (craft; Unreal major; measurer) | **Leaf-zone prongs.** Every stick but the rear guard now carries a thin plate (0.2 mm) on its own bone that runs on 5.9 mm past its rib tip, over the silk's inner margin; the prongs shingle like the ribs. The silk runs on under the band (its own edge 0.4060 L); the **visible leaf edge is the band's edge, 0.437 L** (RS 7: 0.431 L +- 0.012 L) and the rib tips (the band's inner step) sit at 0.4054 L (RS 4 shoulder row 0.415 - 0.431 +- 0.01 L). Each prong is weighted to its own stick along its - edge and to the next stick along its + edge (blended by angle between), so it shortens with its gap as the fan closes and the closed fan stays compact; it also laps 1 mm inward over its own rib tip (so no ray slips down the step to the next rib) | New **G5** proof (`props_lib/fan_seethrough.py`, rays from 13 view directions through an annulus round the inner edge, every LOD, 6 openings): front and back **0** (round 2: up to 2,253 samples), rim-oblique 45 deg **0** at every opening (round 2: up to 14,682), LOD0 total **762 vs 122,596**. fan2's reference camera through the whole inner band: **0 of 350,656 rays** at every LOD (the round-2 reference render had 94 px). Unreal, the round-2 reviewer's own cameras and frames: the inner-edge rows are gone; all that is left are single-pixel specks along fold lines (the 0.08 mm crack, 253 px in 20 shots against round 2's 2,208) |
| M1 | Ribs stop short of the leaf; leaf held only by its face bones (craft) | The prong band IS the ribs running on over the silk's inner margin, glued there. Ribs running on BEHIND the silk to 0.9 L were measured impossible with rigid pleats (below, gap 3) | the probe of gap 12 shows face 24 swinging through the vertical under its leaf line at 26 deg open (`round3/` notes in section 3) |
| M2 | ACL default cracks the fold; the compression requirement is only in WorkFiles (Unreal) | The sidecar's `import` block now says `"bone_compression": "/Engine/Animation/DefaultRecorderBoneCompression"` with the reason and the ACL alternative; the pack import and both Unreal checks read it from there; the buyer README says re-compressing with the project default cracks the leaf | U11 pass (all three clips) |
| M3 | Pack masters lack Used with Skeletal Mesh; pack material path unverified on the skeletal mesh (Unreal) | Integrated (section 6): the flag on M_Fabric_Master and M_Steel_Master, MI_Fan_Leaf / _Ribs / _Tassel / _Rivet, the fan imported by the pack build | pack build verify passes; pass 2 on the pack's fan renders the real instances; the existing items' dump is unchanged |
| M4 | Pleats read as rounded tubes, ribs as smooth plastic, no micro-texture (craft; measurer) | Leaf faces are now **flat facets** with crisp folds (the normal turns toward the ridge only in the first 20 % of each face beside its mountain); the invented "cockling" relief was removed and the silk weave's relief doubled; the sticks got a lacquered bamboo long grain (vascular-bundle streaks in albedo, gloss and relief) on top of the per-stick tone | leaf p10/50/90 0.0059 / 0.0158 / 0.0284 (fan2 0.0076 / 0.0156 / 0.0287); see `Renders/Fan/fan_crops_3x.png`, `fan_raking.png` |
| M5 | Closed state: pages overhang the guards, guards 1.57 deg apart (craft major; Unreal minor) | **Accepted, not changed** (decision D14). The pages are 11.4 mm wide at the tip (the leaf's development: 25 pleats over fan2's measured opening) and fan2's guard is 9.1 mm there (RS 5, measured), so no pleat arrangement fits inside it; bringing the guards to 0 deg needs equal leaf-line offsets, which moves the pleat pattern off fan2's measured notches (round 2's fit). Measured now: closed 210.2 x 16.4 x 15.5 mm (round 2: 17.2 mm wide), pages overhang the front guard by 2.66 mm at the tip, nothing intersects, the prongs no longer add width | `fan_report.json` `closed_bundle`, `Renders/Fan/fan_closed_stack.png` |

### Minors

| Issue | Done |
|---|---|
| Tassel's cord_01 capsule starts inside the fan's handle box; tassel overlaps the rivet (Unreal) | The capsule now starts 8 mm below the eyelet (the box reaches 6.0 mm). The rivet overlap is the cord threaded through the eyelet, as fan2: recorded in the tassel sidecar (`rivet_overlap`) and the README, with the collision-filtering advice for component physics |
| Bounds depend on the physics asset (Unreal) | The sidecar carries `import.bounds_extension_cm` (posed LOD0 at 41 openings + 1 mm, minus the bind box: +X 0.195, +Y 0.10, +Z 0.15, -X 0.10, -Y 0.106, -Z 0.824 cm); both imports set it; U10: the mesh's own bounds hold every posed leaf corner with 1.0 mm to spare, no physics asset needed. The envelope box stays in PHYS_Fan |
| PHYS_Fan not reproducible from Exports; body on 'pivot' carries nothing (Unreal) | The proxies ship in `Exports/Fan/Physics/`; the sidecar says how to rebuild; the pack build makes `PHYS_Fan` / `PHYS_Fan_Tassel` from them. **The sticks are now children of `pivot`** (leaf faces stay children of their sticks), so the one body on `pivot` carries the whole fan; the sidecar's role text says so and that the open leaf has no collision |
| Texture import defaults (Unreal) | The pack importer sets the kinds (BC DXT1 sRGB, ORM DXT5 / DXT1 linear, N BC5, Detail16 G16); the three 8-bit `*_Detail.png` are listed as not imported, as for every item. `recolour_maps.json` carries each Detail16's Unreal import flags |
| Loop flag (Unreal) | Sidecar per clip: OpenClose loop on (one full open-hold-close, loop-safe), Openness off (drive by time), OpenPose on (static). Both imports set it; U11 |
| Rivet dull (craft; measurer) | Base colour 0.80 / 0.78 / 0.74 (polished nickel-silver, was 0.62), roughness 0.05 - 0.09. In the Unreal pack renders it reads as the brightest point; under the reference view's near-black studio it still reads grey (lighting, gap 5) |
| Tassel reads as smooth flutes (craft; measurer) | Not changed (gap 6) |
| Animation feel motorised (craft, optional) | Not changed: A_Fan_Openness can be driven by any curve in game; no second clip was added (gap 7) |
| Colour less blue than fan2 (measurer) | Not changed: the tints ARE RS 9's blue-black; the render's chroma is washed by the specular sheen (leaf render chroma 0.301 / 0.332 / 0.367 vs fan2 0.264 / 0.329 / 0.407). A buyer can pick any colour (gap 8) |

## 3. Mechanism and fold proof (final bytes)

Frame: rivet at the origin, rivet axis +Z (front), stick_00 (the held front guard) along +X, opening counter-clockwise.
Openness s: 0 closed (1.57 deg), 1 open (163.2 deg).

- **Numpy mechanism, 87 openings (G1-G3):** worst crack **0.0833 mm**, **0 intersections** of any class (leaf/leaf
  non-neighbours, leaf/sticks including the prongs, stick/stick, rivet); minimum dihedrals 3.59 / 3.78 deg; 0
  neighbouring-face crossings at bind (G2b); the closed leaf stays within the stack faces (G3b).
- **Half keys** (Unreal-style local slerp between keys): OpenClose 0.0823 mm, Openness 0.0829 mm, 0 hits.
- **From the exported FBX** (Blender importer, 121 + 157 + 3 evaluations): stretch 0.00013 mm, crack 0.0836 mm, 0
  intersections (V3-V5).
- **Unreal, engine poses** (every key and half key): crack 0.0083 cm; runtime (compressed, component) 0.0083 cm; opening
  error 2.6e-5 deg.
- **See-through (G5, new):** section 2, B1. `fan_report.json` `seethrough` has every LOD, opening and view, with and
  without the prongs.
- **Why nothing can run BEHIND the silk** (the craft's "ribs to 0.9 L"): a leaf face hinges on its leaf line and, as
  the fan closes, swings down through the vertical UNDER that line to lie as a page on the other side (probe: face 24
  at s = 0.15 has its valley under its own leaf line). So a rib under a leaf line would be cut by its own face. The
  prong lies on the + side of its leaf line, where the face only ever falls away (0.37 mm below at 0.9 mm when open,
  steeper as it closes), and over the next leaf line, 0.375 mm lower; blending it onto the next stick keeps both of its
  edges fixed relative to those two lines at every opening.
- **Bind optimisation** (the mid-fold offsets, re-run because the silk's inner radius moved): worst crack 0.0962 ->
  0.0685 mm at the optimiser's samples.
- **Sheets:** `Renders/Fan/fan_fold_sheet.png` (0, 15, 30, 60, 90, 120, 150, 163.2 deg, front and above, from the
  re-imported FBX), `fan_closed_stack.png`, `fan_unreal_fold_sheet.png` (Unreal captures).

## 4. Rig, animation, LODs, sockets, physics

- **Bones:** `pivot`, `stick_00`..`stick_25` (children of `pivot`), `leaf_00`..`leaf_49` (each a child of the stick it
  hinges on) = 77 in Blender, **78 in Unreal** with `root`. Every leaf face is rigid (one influence); only the prong
  vertices carry two influences (their stick and the next), so no vertex has more than 2.
- **Clips (60 fps):** `A_Fan_OpenClose` 1.3 s (0.5 s eased open, 0.3 s hold, 0.5 s close; loop on), `A_Fan_Openness`
  1.0 s linear in angle (drive by time; loop off), `A_Fan_OpenPose` (static; loop on). Compression: DefaultRecorder.
- **LODs:** SK_Fan 5572 / 2720 / 1320 triangles at screen sizes 1.0 / 0.413 / 0.1446 (bands 3000-6000, 1500-3000,
  500-1500), every fold and every prong kept, no bones removed. SK_Fan_Tassel 1384 / 384 / 76.
- **Size:** open 372.9 x 210.1 x 16.3 mm, closed 210.2 x 16.4 x 15.5 mm; L 190 mm; mass 22 g (tassel 3 g).
- **Sockets:** `Grip` (stick_00, 40 mm above the butt; an ESTIMATE, set it against your hand rig), `Pivot`, `Tassel`
  (back eyelet), `Tip` (stick_12 at the leaf edge). Unreal: 0.0 cm / 0.0 deg against the sidecar.
- **Physics:** PHYS_Fan one body on `pivot` (handle box 21.2 x 1.4 x 1.65 cm colliding, 22 g; bounds envelope box, no
  collision, no mass). PHYS_Fan_Tassel: kinematic anchor + 5 capsules, 5 constraints.
- **Tassel:** a separate skeletal mesh with a 6-bone chain (not rigid, because it must hang under gravity whatever the fan
  does, and not part of SK_Fan, so leaving it off leaves nothing), attached at the `Tassel` socket.

## 5. How to use it in Unreal (plain English)

1. Use the pack's `/Game/NinjaPack/Meshes/Fan/SK_Fan` (everything is set up there), or import from `Exports/Fan`
   following `Exports/Fan/README.md` - keep the **DefaultRecorderBoneCompression** on the three clips, or the leaf will
   crack.
2. Attach the fan to the hand at its `Grip` socket and adjust that socket to your hand.
3. For a flourish, play `A_Fan_OpenClose` once as a montage. To control how open it is from gameplay, put
   `A_Fan_Openness` in a Sequence Evaluator and set its time to the openness (0 closed, 1.0 fully open). To keep it open,
   loop `A_Fan_OpenPose`.
4. For the tassel, attach `SK_Fan_Tassel` to the `Tassel` socket and give it an AnimDynamics chain (tassel_root ->
   skirt_02) so it hangs and swings.
5. Physics: make PHYS_Fan's body kinematic while held, simulate when dropped (drop it closed: the open leaf has no
   collision).
6. Colours: open `MI_Fan_Leaf`, `MI_Fan_Ribs` or `MI_Fan_Tassel` (duplicate first for a variant) and change **Colour**
   in **01 Colour**. Colour = the part's average colour. The rivet (`MI_Fan_Rivet`) is metal and not tintable.

## 6. Materials integration (`Scripts/unreal/materials/`)

- **Spec (additions):** items `Fan` (SK_Fan: slots M_Fan_Leaf -> MI_Fan_Leaf, M_Fan_Sticks -> MI_Fan_Ribs, M_Fan_Rivet ->
  MI_Fan_Rivet) and `Fan_Tassel` (M_Fan_Tassel -> MI_Fan_Tassel), `kind: skeletal`, folder `/Game/NinjaPack/Meshes/Fan`;
  8 instances (each with its `_Base`, the pack's chain); `recolour_maps` / `recolour_constants` for Fan; the three 8-bit
  Detail PNGs not imported; `changes_v3_fan` explains all of it. Specular Strength 0.5 (leaf, tassel), 0.6 (ribs), as
  the build's look.
- **Usage flag (decision D15):** `used_with_skeletal_mesh` on M_Fabric_Master and M_Steel_Master. It only adds the
  skeletal shader permutation; the dump proves no graph, parameter, default or instance of an existing item changed.
  Without it a cooked game renders the fan with the default material. To revert: remove the two settings keys and the
  two Fan items.
- **Code:** `np_skeletal.py` (NEW: skeletal import with LODs, LOD sizes, bounds extension, sockets, physics from the
  proxies, clips with compression and Loop; assignment by slot name; sockets without bone names). `np_meshes.py`,
  `np_verify.py`, `np_spec.py`, `np_render.py` dispatch to it only for `kind: skeletal`; `np_masters.py` / `np_dump.py`
  know the new flag. `maps/derive_constants_fan.py` (NEW) imports `derive_constants.fabric_part` unchanged (the other
  items' constants record that file's hash) and writes `Exports/Fan/Textures/Recolour/recolour_constants.json`: all
  three parts pass its gates (the default equals the baked contract at mip 0 and every mip, guards inactive, mip drift
  within 2 %). Lightest Colour 0.6 on all three.
- **Runs:** `fan1` (verify failed only on the socket list, which listed bones: fixed), `fan2`, `fan3` pass; dumps
  identical. Not run for the fan: the pack's `render` mode (its UV-probe indices would shift and overwrite the materials
  job's probe captures); the fan's look in Unreal is from pass 2 on the pack's assets instead.

## 7. Decisions (change any of these)

D1-D13 as round 2 (`round3/FAN_REPORT_round2.md` section 1), except D12 (compression) now lives in the sidecar. New:

| # | Decision | Why |
|---|---|---|
| D14 | Closed state accepted as is (2.66 mm page overhang at the tip, guards 1.57 deg apart) | fan2's pleat width (11.4 mm) exceeds its guard (9.1 mm); equal leaf offsets would move the pleats off fan2's notches |
| D15 | `Used with Skeletal Mesh` set on the two pack masters | required for any skeletal item on the pack's masters; changes no existing look (dump) |
| D16 | Visible leaf edge 0.437 L (not 0.431 L) and a 5.9 mm band | the widest band both RS tolerances allow; 4 mm left a dotted row in the Unreal reviewer's rim view (208 px at 122.8 deg) |
| D17 | Prongs blend onto the next stick (2 influences) | a rigid prong stood ~9 mm proud of the closed stack (measured: closed width 20.0 mm vs 16.4 mm blended) |
| D18 | The sticks' material part is called **Ribs** (MI_Fan_Ribs); the FBX slot stays `M_Fan_Sticks` and the maps `T_Fan_Sticks_*` | the brief's instance name; renaming the slot would only churn files |

## 8. Honest gaps

1. **Low oblique see-through remains.** From about 25 - 30 deg across a partly open fan toward the pivot, a few slits
   still show under the band (LOD0 samples: 243 at 82.4 deg and 519 at 36 deg at 30 deg elevation; 0 at 45 deg and
   steeper, 0 front/back). In Unreal's rim camera the rows are gone. Closing it completely needs deforming silk (morph
   targets or more bones per face), because nothing rigid may sit under a leaf line.
2. **Single-pixel specks along fold lines** in coverage renders: the rigid faces meet within 0.08 mm, not exactly.
3. **No ribs behind the silk** (back view shows plain silk): impossible with rigid pleats (section 3).
4. **The bare rib zone still reads flatter than fan2** (p10/50/90 0.0080 / 0.0101 / 0.0107 vs 0.0048 / 0.0118 /
   0.0252): fan2's bare zone is pierced openwork, kept out by the brief. The bamboo grain helps close up only.
5. **Rivet** reads grey under the reference view's near-black studio; bright under normal lighting.
6. **Tassel** skirt reads as smooth locks, not loose threads; knot clean.
7. **Animation** is mechanically even (no flick timing); a stylised clip is the user's call.
8. **Colour** renders more neutral than fan2 through the specular sheen; the parameter is RS 9's blue-black.
9. **Closed state** (D14).
10. **Grip socket** is an estimate; mobile rendering untested; no gravity simulation run in a commandlet (the chain and
    its constraints are verified).
11. **Visible leaf edge** is 1.1 mm (2 px in fan2's frame) outside fan2's measured 0.431 L, inside its tolerance (D16).

## 9. Files

- **Build:** `Scripts/props/build_fan.py`, `Scripts/props/props_lib/fan_*.py` (new: `fan_seethrough.py`),
  `Scripts/props/verify_fan.py`. Pipeline unchanged.
- **Unreal checks:** `WorkFiles/fan/UnrealCheck/` (`fan_ue_pass1_import.py`, `fan_ue_pass2_verify.py`,
  `fan_ue_sheet.py`, `run_ue.sh`); results `final_r3/` (standalone) and `final_r3_pack/` (pack assets).
- **Round-3 evidence:** `WorkFiles/fan/round3/` (see-through sweeps `st_*.json`, `ue_holes_r3.json` + masks, derive log,
  materials-run logs, the fold optimisation log, the pre-pass materials code and the round-2 report).
- **Materials:** `Scripts/unreal/materials/` (above); build outputs `WorkFiles/materials/build/*_fan{1,2,3}.json`,
  `dump_fan{2,3}.json`.
- **Outputs:** `Assets/Fan.blend`, `Exports/Fan/` (+ `README.md`, `Physics/`), `Renders/Fan/`.
- **Regression:** `WorkFiles/fan/regression/` (`fan_regression.py`; `pre_final_pass/`, `post_fan/` with
  `compare_vs_pre_final_pass.json`). **Backup:** `Backups/Fan_2026-09-26/`.
- **Reference docs:** `References/Fan/REFERENCE_SPEC.md` (new row: inner edge, round 3), `FAN_STUDY.md`.
