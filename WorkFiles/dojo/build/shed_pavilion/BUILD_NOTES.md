# Training shed (SW) + drum pavilion structure (SE): build notes

Track of the round-4 workflow `dojo-round4-buildings` (step 2). Locks `DojoShed` (claude, `Assets/Dojo/DojoShed.blend`) and
`DojoPavilion` (claude, `Assets/Dojo/DojoPavilion.blend`), both still held for the fix round. Blender only: nothing in
DojoLab or Unreal was touched; the combined import is step 3.

## 2026-09-29 - ROUND 4: training shed (SM_DKS_*) + drum pavilion structure (SM_DKV_*)

**References (look):** `References/Dojo/dojo_training_shed_ref.png`, `dojo_drum_pavilion_ref.png` (AI-generated, measured
only; crops in `refcrops/`). **Spec (size, wins):** `DOJO_ARENA_SPEC.md` 4.5. **Gameplay:** the grey-box's numbers
(`build_dojo_greybox.py`, `layout.json`, `showcase/layout_showcase.json`), unchanged.
**Shared code, used read-only:** `Scripts/dojo/roof/roof_kit.py` 1.3.0 (RoofSlope, tile_field, plan_clip, rafters,
sarking, eave_trim, hip_roll with disc ends, sag_warp, slab), `roof/kit_mesh.py`, the material library
(`Scripts/dojo/materials`, M_DJ_*), the modern kit's `modern_lib.build_material` (galvanised, concrete), the ground kit's
soil set. Nothing shared was edited.

### Commands (headless, --factory-startup)
```
blender -b --factory-startup --python Scripts/dojo/shed/build_shed.py            [-- --quick] [--no-export] [--no-context]
blender -b --factory-startup --python Scripts/dojo/pavilion/build_pavilion.py    [-- --quick] [--no-export] [--no-context]
# checks (each kit's blend holds the showcase compound with the kit swapped in, as the hall's did)
blender -b --factory-startup Assets/Dojo/DojoShed.blend --python Scripts/dojo/walk_check.py  -- --layout shed_pavilion/layout_shed_checks.json --out shed_pavilion/checks/walk_check_shed.json
blender -b --factory-startup Assets/Dojo/DojoShed.blend --python Scripts/dojo/climb_check.py -- --layout shed_pavilion/layout_shed_checks.json --out shed_pavilion/checks/climb_check_shed.json --hover 0.019
blender -b --factory-startup Assets/Dojo/DojoShed.blend --python Scripts/dojo/roof_walk_check.py -- --layout shed_pavilion/layout_shed_checks.json --out shed_pavilion/checks/roof_walk_check_kit1_shed.json
blender -b --factory-startup Assets/Dojo/DojoShed.blend --python Scripts/dojo/shed/sp_roof_walk.py -- --asset shed
(the same four with DojoPavilion.blend / layout_pavilion_checks.json / --asset pavilion)
blender -b --factory-startup --python Scripts/dojo/shed/sp_verify_fbx.py        # fresh process, the exported FBX bytes
blender -b --factory-startup Assets/Dojo/DojoShed.blend --python Scripts/dojo/shed/render_sp.py -- --asset shed --what sheet|close|context --samples 96 --tag r0
blender -b --factory-startup --python Scripts/armory/side_by_side.py -- <ref crop> <render> <out>
```

### Files
- `Scripts/dojo/shed/`: `sp_common.py` (shared by both builders: kit_mesh's Geo -> mesh plus the non-library materials,
  the hall's QA + export loop, the showcase context loader), `build_shed.py`, `render_sp.py`, `sp_roof_walk.py`,
  `sp_verify_fbx.py`. `Scripts/dojo/pavilion/build_pavilion.py`.
- `Exports/DojoKit/Shed/` SM_DKS_Roof, _Post, _BackWall, _Floor, _Rack (+ sidecars for the LOD pieces);
  `Exports/DojoKit/Pavilion/` SM_DKV_Plinth, _Frame, _RoofQuarter, _Finial, _EavePad.
- `WorkFiles/dojo/build/shed_pavilion/`: `layout_shed.json`, `layout_pavilion.json` (pieces, fbx, classes, pivots,
  instances, `replaces_greybox`, numbers; the shed's also holds the two new material recipes), `layout_*_checks.json`,
  `shed/` + `pavilion/` (qa_report, export_report, *_report), `checks/`, `refcrops/`, `renders/r0/`.

### Pieces
| Piece | Class | Tris | Ship | UCX | Notes |
|---|---|---|---|---|---|
| SM_DKS_Roof | roof | 25,816 | Nanite | 2 | 8 lapped corrugated sheets (76 mm pitch, 18 mm deep, 1.2 mm thick, per-sheet UV offsets), top roll flashing with end caps, side angle trims, 6 C purlins, 3 channel rafters, front I-beam, knee braces |
| SM_DKS_Post (x2) | thin | 576 | LOD0-2 | 2 | 0.114 m pipe on a 0.45 x 0.45 x 0.30 m concrete footing, base plate + nuts, sleeve collars, cap plate |
| SM_DKS_BackWall | building | 1,676 | LOD0-2 | 1 | dark vertical boards (backed: no daylight at the joints) in a timber frame at Y 0.30-0.47 (clear of the wall cap's overhang to Y 0.24), head beam carrying the rafters, end-panel stiles + rails, rear knee braces |
| SM_DKS_Floor | ground | 44 | 1 LOD | 1 | 2 cm packed-earth pad |
| SM_DKS_Rack | thin | 1,496 | LOD0-2 | 1 | its own asset: empty 4-shelf rack 3.4 x 0.45 x 1.5 m, three uprights (the middle one 26 % from the west end: the sheet's front view seen from the courtyard), shelves +0.30 / 0.68 / 1.06 / 1.46 |
| SM_DKV_Plinth | ground | 3,268 | Nanite | 4 | 3 rough-faced ashlar courses (corner bond, the bottom one bedded 5 cm), flush flag paving, the north stair |
| SM_DKV_Frame | thin | 3,428 | Nanite | 8 | pedestals, 0.32 m posts, bearing blocks, boat bracket arms, eave beams (keta) crossing at the corners, outer eave purlin ring (degeta) on cantilever + diagonal corner arms, tie beams (nuki) with projecting ends, struts, knee braces, ceiling ties + king post |
| SM_DKV_RoofQuarter (x4) | roof | 21,988 | Nanite | 1 | one face + its hip, instanced at 0/90/180/270 about (41, 3): tiles (10 courses of 0.284 m, eave discs), sarking, 17 parallel rafters, hip rafter, fascia, 3-course hip roll ending in a round end tile, 8 cm corner upsweep |
| SM_DKV_Finial | roof | 992 | LOD0-2 | 1 | square tile cap with a cornice over the hip ends, iron neck, plain iron ball r 0.15 (top +5.09), UVs in a rust-free window of T_DJ_Iron |
| SM_DKV_EavePad | landing | 704 | LOD0-2 | 1 | route 7's landing: flat deck (boards along the eave), fascia, side boards, two joists strapped onto the rafter tails |

Unique tris: shed 29,608 (30,184 placed, 6 instances); pavilion 30,380 (96,344 placed, 8 instances).

### Numbers (measured, layout_*.json)
- **Shed:** roof crest (= collision) +3.0 at Y 0 falling 6.71 deg to +2.5 at Y 4.25, then LEVEL +2.5 to the eave at Y 5.0
  (route 7's band, the sheets cranked over the purlin at Y 4.25). Front beam 2.165-2.305, posts at X 0.42 / 5.58, Y 4.85;
  head beam 2.591-2.751. Nothing west of X 0 or south of Y 0 (the wall-top runs pass clear).
- **Pavilion:** plinth X 39-43, Y 1-5, +1.0; roof 38.4-43.6 x 0.4-5.6, eave +3.25, apex +4.5, 25.68 deg; posts (39.55 /
  42.45, 1.55 / 4.45), pedestal top +1.36; keta 3.241-3.481; degeta 2.956-3.136; bracket arms 2.756-2.896; nuki
  2.745-2.875 (1.745 m over the plinth); stair X 40-42, treads +0.75 (Y 5.0-5.4), +0.50 (5.4-5.8), +0.25 (5.8-6.2).
  Taiko (separate, layout_taiko.json) clear of every pavilion mesh (world-space BVH test: only the stand's feet touch the
  paving at +1.0).
- **Collision = the grey-box's, exactly:** max vertex delta **0.0 mm** on the shed's two roof slabs, the pavilion's four
  roof slabs, the pad and the plinth box (`checks/hull_compare_greybox.json`).

### Checks (GASP capsule r 0.30, 1.72 m, step 0.45)
- **QA:** 10/10 pieces, **0 hard fails** (waived as every dojo kit: uv0_tile_range, uv_no_overlap: tiling UVs in tile
  units). Texel 4.9-6.1 px/cm. LOD sets 0 fails.
- **FBX, fresh process** (`checks/fbx_verify.json`): 10/10 match (tris, UCX count and names, LOD count, slots, bounds
  0.0 mm).
- **walk_check:** shed 16/16 routes clear + 6/6 controls blocked; pavilion 17/17 + 6/6; both also PASS at r 0.35. New
  routes: into the shed under the front beam along the rack; up the north stair onto the plinth; the drummer's stance
  across the north drum head; controls: into the rack, the plinth's north face beside the stair.
- **climb_check (hover 0.019):** every route works, every number identical to the round-3 showcase: route 7 shed crate
  123.1 cm -> band 122.9 cm, depth 94.6 (Mantle 1 m); pavilion crate 122.3 -> pad 197.9 cm, depth 85.9 (Mantle 2.5 m);
  plinth 98.1 cm, depth 134 (Mantle 1 m).
- **roof walk** (`sp_roof_walk.py`, new): shed 5/5 (band both ways, band up the lean-to to the back, across, back down,
  off the west edge onto the wall top); pavilion 5/5 + the finial control (pad onto the west face to the finial, round
  both hips, up the south face; slope 25.7 deg). `roof_walk_check.py` (kit 1 gate paths) still PASS.

### Decisions / deviations (flagged)
1. **Pavilion stair on the NORTH face.** The sheet's front (drum body side-on) is the courtyard side (west), but the
   west face carries route 7's crate (X 36.35-37.35, centred on Y 3) and the plinth-mantle stance (38.64, 3.0). North
   is the drum-head side, towards the east yard. The sheet's "side steps" are the front stair seen in profile (its top
   view has one stair): one stair built.
2. **Stair treads 0.40 m** (4 risers of 0.25): at 0.35 m the walk check's 0.35 m-radius margin run blocked.
3. **Route-7 pad** = the hall's EaveLanding language (a flat eave deck on joists strapped to the rafter tails); the
   collision is the grey-box pad exactly.
4. **Shed front band** = the same corrugated sheets cranked level for the front 0.75 m (a two-pitch lean-to).
5. **Shed sides open** (the sheet): the grey-box's steel east wall is dropped; no route used it.
6. **Two new material INSTANCES** (no new textures; recipes in `layout_shed.json` "materials"; the combined import must
   create them): `M_DKS_GalvWeathered` = M_DJ_Lib_Opaque + T_DKP_Modern_Galvanised_*, Tint (0.44, 0.45, 0.49), RoughMult
   1.5, UseWear (the modern galvanised is new bright spangle; the sheet's roof is dull weathered grey);
   `M_DKS_PackedEarth` = M_DJ_GroundXY_Master + T_DKG_Soil_*, Saturation 0.55, ValueMult 1.35 (the sheet's pale floor).
   Concrete footings use M_DKP_Modern_Concrete as is.
7. **Headroom (R5 2.5 m) cannot hold** under the spec's own eaves: shed front beam +2.165 (eave +2.5); pavilion 1.745 m
   under the tie beams over the +1.0 plinth (eave +3.25). The 1.72 m capsule clears both.
8. **Pyramid roof:** roof_kit has no hogyo builder; the roof is composed from the kit's parts in `build_pavilion.py`
   (no roof_kit edit). A `pyramid()` builder in the kit would let later pavilions reuse it.

### Renders (Cycles, denoised, 96 spp, grey studio; `renders/r0/`)
- Sheets: `shed_front_N`, `shed_side_E`, `shed_top`, `shed_34`; `pavilion_front_W` (the sheet's front: from the
  courtyard), `pavilion_side_N`, `pavilion_top` (stair at the bottom, as the sheet), `pavilion_34`; 1.8 m silhouette.
- Side-by-side (reference | ours): `sbs_shed_front_N`, `sbs_shed_side_E`, `sbs_shed_top`, `sbs_shed_34`,
  `sbs_pavilion_front_W`, `sbs_pavilion_side_N`, `sbs_pavilion_top`.
- Close-ups: shed post + footing, front band over the crate, underside + rack, top flashing; pavilion SW eave corner,
  bracket underside, finial + hips, route-7 pad over the crate, north stair.
- Context (studio light, in the compound): `shed_context_from_yard`, `pavilion_context_from_yard`.

### Open (for the judges / fix round)
- Proportions follow the spec, so both read squatter than the sheets: the shed roof is 0.5 m of fall over 5 m (the
  sheet's is steep and visible from the front); the pavilion stands on a 1.0 m plinth (sheet about 0.6 m).
- Shed roof: no rust streaks (the sheet has rust along the ribs); the galvanised set's dark macro patches read as
  stains; tune `M_DKS_GalvWeathered` in the Unreal look pass.
- Pavilion roof quarter mixes roof_kit's TimberDark (rafters, fascia, sarking) with the frame's TimberAged.
- The shed band's west ledge could be a 0.5 m mantle from the west wall top (spec: "reached from the wall"), but no
  traversal marker is there in the grey-box; not added.
- Unreal: nothing imported yet (step 3); the grey-box pieces to retire are listed in each layout's `replaces_greybox`.


## 2026-09-29 - ROUND 4 FIX f1
Full notes: `WorkFiles/dojo/build/BUILD_NOTES.md` (ROUND 4 FIX f1). Shed: corrugation 120 mm / 30 mm, heavier knee
braces, rack 3.7 m, M_DKS_GalvWeathered tint 0.60 (the board wall was already full width: the judges' close-up looked
along it edge-on; the camera is re-framed). Pavilion: slimmer hip rolls and smaller hip end tiles; the knee braces
stay (the sheet shows them). QA 5 + 5, 0 hard fails; collision unchanged; roof walks PASS.
