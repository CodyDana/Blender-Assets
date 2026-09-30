# Round 5, round-4 fixes track: build notes

## 2026-09-29 - ROUND 5 (final look pass, no vegetation): the round-4 open asset fixes

User: "start with everything else and leave the vegetation for later". This track fixed the round-4 open items on the
Blender assets and re-exported them through `Scripts/pipeline`. It worked headless only, with no MCP. It did not touch
Unreal or DojoLab: the combined import is the next step. Nothing was committed.

**Locks** (all `claude`, refreshed): DojoShed, DojoKit (kit 1), DojoHall, and DojoTrainingProps, which was claimed
new because no lock file existed. The dressing and outside tracks work in their own folders; none of their files was
touched.

**Start state:** `start_backup/` holds:
- the scripts, layouts, blends and exports of every kit touched;
- the library's `dojo_materials.py` and `dojo_tex_gen.py`.

### Commands
```
blender -b --factory-startup --python Scripts/dojo/shed/build_shed.py                       # QA 5, 0 hard fails
blender -b --factory-startup --python Scripts/dojo/build_kit1.py                           # QA 28, 0 hard fails (19 min)
"<blender python>" Scripts/dojo/materials/dojo_tex_gen.py --only ShojiPaper                 # the new named variant
blender -b --factory-startup --python Scripts/dojo/hall/build_hall.py                      # QA 21, 0 hard fails
blender -b --factory-startup --python Scripts/dojo/props/training/build_training_props.py  # QA 7, 0 hard fails
blender -b --factory-startup --python WorkFiles/dojo/build/round5/fixes/compose_r5_checks.py -- --no-export
bash WorkFiles/dojo/build/round5/fixes/checks/run_checks_r5.sh                              # every walk / climb / roof walk
blender -b --factory-startup --python WorkFiles/dojo/build/round5/fixes/checks/fbx_audit_r5.py
blender -b --factory-startup Assets/Dojo/DojoShowcase.blend --python WorkFiles/dojo/build/round5/fixes/r5_render.py -- --cams <list> --samples 64 --tag after [--light studio] [--src PREFIX=<backup blend>]
py -3 WorkFiles/dojo/build/round5/fixes/sbs.py <out> <img> <img> ...
```

**The track's own tools:**
- `compose_r5_checks.py` runs the showcase compose unchanged, with its output redirected to `checks/`. The live
  `DojoShowcase.blend` and `showcase/layout_showcase.json` belong to the Unreal step and were not written.
- `r5_runcheck.py` runs the existing check scripts on that blend. It pins their `ROOT = parents[2]` expression and
  applies path swaps.
- `r5_render.py` makes read-only Cycles renders (denoised) of the live showcase. Each piece gets its kit blend's
  textured mesh; `--src` points a prefix at the backup blends to make the "before" renders. It uses the UE capture
  cameras plus this track's `FX_*` close-ups.

### 1. Training shed (`Scripts/dojo/shed/build_shed.py`)
**Measured first.** The board wall already ran the full bay (X 0.28-5.72), and still does.

The round-4 "1/3 of the width" reading came from the corner:
- The shed is in the SW corner. Its roof's west side is open onto the WEST perimeter wall.
- In CU_R4_ShedVending the back edge projects to 960-1343 px and the west side to 1343-1751 px.
- So about 45 % of the roof's width in that view is the west wall's plaster seen under the roof, not a short board
  wall. `renders/*/FX_ShedFront*` show the board wall filling the bay.

Changes, all against dojo_training_shed_ref:

| Item | Before | After | Source |
|---|---|---|---|
| Wall piers | 0.14 m frame posts | 0.20 m timber piers at both ends of the board wall, floor to the head beam, proud of the boards | the sheet's front / 3/4 / side views |
| Shelf | 4 tiers, 3.7 m (X 1.08-4.78) | 4 tiers, **4.2 m (X 0.90-5.10)**, filling the bay between the two framed end panels | The sheet's 3/4 view puts the rack at 78 % of the board wall (front view: 67 %). The shelf heights were already the sheet's, measured on its 1.8 m figure (0.28 / 0.68 / 1.06 / 1.47 against ours 0.30 / 0.68 / 1.06 / 1.46), so they are unchanged. Three uprights, the middle one 26 % from the west end |
| End panels | stiles at 0.95 / 5.05 | stiles at 0.80-0.88 / 5.12-5.20, low rail between pier and stile | the sheet's narrow framed end panels |
| Corrugation | 120 mm pitch, 30 mm deep | **150 mm, 42 mm**, 1.05 m cover per sheet | about 37 ribs over the sheet's 6 m eave; the eave edge now reads as a row of dark arches (`FX_ShedEaveEdge`) |
| Purlins | steel C, 75 mm | **timber (TimberAged) 65 x 63 mm**, square to the sheet | the sheet's timber purlin frame; 63 mm keeps the sheet-to-rafter stack at exactly 0.1074 m |
| Rear braces | 70 mm angles from the frame posts | **80 x 9 mm steel angles** from each pier's inner face (at about 2/3 height) to its end rafter at Y 1.30, with a bolted foot plate | the sheet's 3/4 view |
| Front knee braces | 60 mm | 70 mm | - |

Other results:
- **Collision:** identical except the rack's own box (`checks/json/fbx_audit_r5.json`: every other shed UCX has a
  vertex delta of 0.0 mm). The front beam is +2.165 and the head beam is unchanged, because the purlin depth was
  traded for the deeper sheet.
- **Tris (FBX audit):** roof 17,144 -> 13,800 (Nanite; the wider pitch has fewer ribs), back wall 1,676 -> 1,764, rack 1,496 (unchanged).
- **Texel:**
  - The roof now mixes the galvanised set (1024 px / 2 m) with the timber purlins (2048 px / 4 m).
  - The pipeline's `texel_density` check grades a whole mesh at its largest texture, so the roof is waived on that
    one check.
  - Each slot is measured on its own texture instead: galvanised 4.78 px/cm, timber 5.12, iron 5.12. The build
    stops if any slot is off by more than 25 %. The numbers are in `shed_pavilion/shed/shed_report.json`.
- **Not changed (spec):**
  - The roof's pitch: 0.5 m of fall over 4.25 m + a level 0.75 m band, set by spec 4.5 and route 7. It will always
    read flatter than the sheet's.
  - The corner placement.
  - In low sun the bay stands in the shed's own shade (the lighting pass).

### 2. Residence ridge "renders tan": the slot is correct. The tan comes from the sun, not the asset (no change)
- **One mesh on both buildings.** SM_DKO_Roof_Ridge is used on both outbuildings (rot 90), with one slot,
  M_DJ_RoofTile: layout_outbuildings, and UE verify r4 "slots match". The UE storehouse ridge (same mesh) reads
  charcoal.
- **Same texture sampling.** A UV probe (`probe_ridge_uv.py`) shows the ridge and the slope sample the same
  T_DJ_RoofTile_BC mean.
- **Not the sheen.** A Blender test (`--exp ridge_rough` / `ridge_nometal`) with roughness x 2.5 or metal 0 moved
  the sunlit ridge face by at most 10 levels:
  - base render (113, 91, 78);
  - no metal (119, 96, 83);
  - rougher (103, 84, 74);
  - the slope stays (29, 31, 44).
- **The cause.** The residence ridge's west noshi face is the only ridge face in the compound that stands square to
  the 12 deg WNW sun (n.l 0.92 against 0.58 on the slope). A dark albedo in full low sun reads mid-tan, the same as
  the pavilion's sunlit tiles, R/B 1.84 in r4.
- **Where the fix belongs.** This is the look pass's "low-sun warmth" item (sun colour, or a tile look value), not
  an asset bug.

### 3. Kit 1's route-2 step pier against the outbuilding verge (`Scripts/dojo/build_kit1.py`)
- **The clash.** The pier's +X end is world Y 27.4, exactly the outbuilding's front verge face. Its gable verge
  overhung that end by 0.12-0.16 m at +3.0-3.49, into the verge tiles and bargeboard. This was clearance r4 clash 2:
  1012 / 1048 face pairs.
- **The fix.** `step_pier(..., close_hi=True)`: the cap now stops 2.5 cm short of the end face, with the kit's own
  closed end (tile end plate + the ridge's round end tile, as the gate join against its post). The wall-end (-X)
  gable is unchanged.
- **Measured (piece local):**

  | Height band | Max +X, before | Max +X, after |
  |---|---|---|
  | above +3.0 | 1.163 | 0.975 |
  | +2.6-3.0 | 1.121 | 1.000 |

  Footing and plaster are unchanged. Clearance: 46 contacts (r4 f1: 48); both pier-roof clashes are gone.
- **Route 2 unchanged:** pier 123.1 cm mantle, then a 0.233 m step onto the far slope; ob_roof_walk route2 W/E PASS.

### 4. Hall shoji (`Scripts/dojo/hall/build_hall.py`, new library variant `M_DJ_ShojiPaper`)
- **Density:** measured on the hall sheet's front elevation as 7 cells across x 9 up per sliding panel, with muntins
  about 30 % of the pitch. So the door and lattice bays go from 6 x 11 with 20 mm bars to **7 x 9 with 36 mm bars**.
  The lattice bay's low strip and the clerestory frieze keep their counts.
- **Paper:**
  - One quad per CELL (bar centre to bar centre), unit UV, on the new named library variant M_DJ_ShojiPaper:
    `dojo_tex_gen.shoji_paper`, 256 px, with `MATERIALS` and README entries.
  - Colours: core #F2B25E, mid #E0913F, rim #8E5222. Core hue 34.6 deg, rim 28.1 deg; brightness falls to 55 % at
    the bars, so only the cell cores are bright.
  - Emissive 0.75 (UE 75 after K_LUX).
  - GlassAmber is untouched (lanterns, lamps, windows).
- **Sheet targets:** bright cells p95 (220-234, 152-168, 88-98), hue 27-29; ref 2 hue 33-34.
- **Blender, FX_ShojiWide, bright-cell median:**

  | | sRGB | Hue | Sat | Luminance p95 |
  |---|---|---|---|---|
  | Before | (254, 215, 183) | 27 | 0.28 | 235: the per-panel hotspot blown pale |
  | After | (216, 164, 111) | 30.3 | 0.49 | 176 |

- **UE.** The UE instance gets its first values from compose (EmissiveIntensity 75, tint 1). The look pass should
  judge and tune it on the captures, not reuse GlassAmber's look values (tint and Saturation 0.6 are what made that
  one salmon).
- **Collision:** unchanged, 0.0 mm. **Tris:** Bay_Lattice 3,528 -> 3,748, Bay_Door 2,820 -> 2,980, ClereFrieze 1,448.

### 5. Wall plaster seams every 4 m (`build_kit1.py`)
- **The cause.** Round 3's V-grooves sat on every module end plus each module's middle. The instanced 4 m modules
  therefore drew a regular 2 m panel grid on every wall; the sheet shows at most one faint hairline per elevation.
- **The fix.** `PANEL_SEAMS = False`. The modules now butt flush. The plaster is world-aligned (UE triplanar, Blender
  world box), so there is no texture seam either. The irregular crack ribbons stay.
- **Tris:** WallBody 4 m 648 -> 520 (and the 1 / 2 m variants); GateJoin 20,550 -> 20,470; StepPier 63,037 -> 59,741.
- **Collision:** unchanged.

### 6. Wooden dummy "round log body" (`Scripts/dojo/props/training/build_training_props.py`)
- **Size already right.** Measured on the sheet (1.8 m figure = 166.7 px/m), the body is 0.33-0.35 m across (ours
  0.32 + grow) and 1.82 m tall (ours 1.90).
- **The defect was the texture wrap.**
  - The body's 1.0 m circumference is under 0.35 of the 4 m timber tile, so `v_map` gave it a MIRRORED ramp (V 0 ->
    0.13 -> 0).
  - The two mirror lines ran down its front and back. They flip the tangent-space normal map, which drew the hard
    vertical crease that made it read as a square plank post in UE (CU_Training r4).
  - Now `v_linear=True`: the grain wraps once at true scale, with one seam at the back (+Y), and 64 sides.
- **Same fix** on the long-arm dummy's body.
- **Tris (LOD0, FBX audit):** wooden dummy 15,420 -> 16,028; long-arm 10,844 -> 11,452.
- **Checks:** collision unchanged; clearance at r 0.35 PASS.

### 7. Other clear asset bugs
- The eight retired `SM_DKG_PaverCourse_2x0p42_A..H.fbx` were still in the live `Exports/DojoKit/Ground/` (verifier
  r4 note). They were moved to `retired_fbx/Ground/`. They are not placed, are in RETIRED_MESHES, and the ground
  build no longer calls their builder.
- The shed roof walk had no CONTROL of its own (verifier r4 note). The check run adds
  `CONTROL_1v1_west_edge_over_the_wall_top_into_the_boundary`: blocked at X -0.72 by the 1v1 ring.

### Checks (this track's composed scene `checks/DojoShowcase_r5.blend`; GASP capsule r 0.30, 1.72 m, step 0.45) - ALL PASS
- **Compose:** 208 pieces, 796 instances, 0 warnings, 63 materials (+ShojiPaper), 101 textures.
- **QA:** shed 5, kit 1 28, hall 21, training 7, with 0 hard fails and a UCX on every SM_.
- **FBX audit** (fresh process, exact bytes, old vs new, 61 FBX): no unexpected collision change. Only the rack's
  UCX moved (the fix).
- **walk_check:** 20 routes clear, 11 / 11 CONTROLs blocked; also at r 0.35.
- **climb_check (hover 0.019):** every route, with the numbers unchanged:

  | Obstacle | Height (cm) |
  |---|---|
  | Wall | 198.1 / 193.7 |
  | Pier | 123.1 (+0.233 step) |
  | Cistern | 122.3 |
  | Eave pad | 172.9 |
  | AC | 197.4 + 0.40 |
  | Shed crate -> band | 123.1 -> 122.9 |
  | Pavilion crate -> pad | 122.3 -> 197.9 |
  | Vending | 173.1 + 0.25 |
  | Plinth | 98.1 |
  | Veranda | 48.1 |
  | Hurdle | 111.8 |

  Route 3: -0.109 / -0.513.
- **Roof walks:**
  - gate 3 / 3;
  - hall 16 paths;
  - outbuildings 15;
  - corridors 12;
  - shed 6 (the new CONTROL included);
  - pavilion 6.

  All PASS.
- **Clearance:** 46 contacts, all intended (grade contacts, valley laps). The pier clashes are gone.
- **Ground holes:** identical to r4 f1 (only the closed interiors and the gate-post slits).

### Renders (Cycles, denoised, 48-64 spp, UE capture cameras + close-ups; `renders/before|after[_studio]/`)
Before / after sheets are in `sbs/`:
- **Shed:** CU_R4_ShedVending, CAM_VendingShed, FX_ShedFront, FX_Shed34, FX_ShedEaveEdge, FX_ShedUnder,
  shed_front_vs_ref.
- **Pier:** FX_PierStore, FX_PierRes, FX_PierStoreTop.
- **Hall:** FX_ShojiWide, CAM_HallVeranda, CAM_Establishing, hall_shoji_vs_ref.
- **Wall:** FX_WallSeamsS, FX_WallSeamsW, CU_WallFooting.
- **Dummy:** dummy_after, dummy_body_zoom, CU_Training.
- **Ridge:** FX_ResidenceRidge.

### Open / for the Unreal step
- **Re-import:**
  - Shed: Roof, BackWall, Rack.
  - Kit 1: StepPier, WallBody x9, GateJoin. The gate pieces re-exported with 0.1 mm float jitter only.
  - Hall: all 21 re-exported; Bay_Lattice / Door / ClereFrieze changed.
  - Training: WoodenDummy, LongArmDummy. The others re-exported with the same tris.
- **New library material:** M_DJ_ShojiPaper + T_DJ_ShojiPaper_{BC,N,ORM}. Compose picks it up automatically.
- **Residence ridge:** low-sun warmth on sun-facing tile, for the lighting pass.
- **Shed interior:** shade in low sun (the lighting pass). The corner means the west wall shows under the roof from
  the courtyard.
- **For other tracks:** they match kit meshes by name and bounds for their renders. The changed pieces' bounds moved
  (rack, pier, shoji bays), so re-read them from the kit blends.

### Scripts changed (not committed)
- `Scripts/dojo/shed/build_shed.py`
- `Scripts/dojo/build_kit1.py`
- `Scripts/dojo/hall/build_hall.py`
- `Scripts/dojo/props/training/build_training_props.py`
- `Scripts/dojo/materials/dojo_materials.py`, `dojo_tex_gen.py` and `README.md` (the named variant only)
- `WorkFiles/dojo/build/round5/fixes/*.py` and `checks/*` (new)
