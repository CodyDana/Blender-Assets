# ArmoryKit lean build: notes

Deviations from `WorkFiles/armory/ARMORY_PLAN.md` (v2) and the decisions behind them, one dated section per stage.

## 2026-09-27: Look pass (match `reference/armory3_reference2.png`, empty gallery)

**Scope.** Room and casework only. No items and no dressing were added (no vases, banners, labels or emblems).
The brass emblem plates stay blank. Positions and footprints are unchanged except the lattice fix below.
Everything was run headless (`blender -b --factory-startup`), with no GUI, no MCP and no Unreal.

### What the reference shows, and what was wrong in the first render (`renders/C1_EntryReveal_golden.png`)
- **Walls.** The reference is dominated by near-black timber: posts, rails, wainscot, upper framing and window
  surrounds. Cream appears only as lit niche backs and as dim upper panels. The first render had cream plaster on
  every wall body, on the upper walls and in the ceiling coffers.
- **Upper walls.** The reference has a continuous clerestory of lattice windows plus a row of small square grilles
  under the ceiling. The first render had 4 small windows per side in a plaster wall.
- **Light.** The reference has golden-hour shafts with lattice patches on the floor, plinth under-glow, LED lines on
  the steps, lit niches and bright lanterns, all warm and contrasty. The first render was flat and bright, with no
  shafts.

### Geometry changes (`Scripts/armory/build_armory_kit.py`)
| Piece | Change | Tris LOD0 before -> after |
|---|---|---|
| `SM_AK_WallLower_1/_2`, `SM_AK_WallLower_Door_2`, `SM_AK_Corner_5` | Wall body material plaster -> **timber** | unchanged |
| `SM_AK_WallUpper_2` / `_1` | Timber body. **Blind shoji panels** fill each bay (2 per 2 m piece, at X 0.12-0.88 and 1.12-1.88, clear of the 1 m posts). Their height, sill and lattice rails (+3.50 to +4.40, rails at +3.83 and +4.09) match the real windows. Above them sits a **ranma transom**: a square grid of 20 mm bars over a subdued plaster back, +4.52 to +4.70. A sill ledge is added under the panels | 36 -> 552 / 36 -> 300 |
| `SM_AK_WallUpper_Window_2` | Timber body. Transom added above the window | 168 -> 372 |
| `SM_AK_Ceiling_Coffer_2x2` | Coffer face uses `M_AK_PlasterShade` (plaster set x 0.30, so a dark coffer). A second inner timber ring makes a stepped coffer | 188 -> 236 |
| `SM_AK_Case_*_Plinth` (all 6) | Body inset 15 mm under a full-footprint lacquer cap. **Brass top edge** (12 mm) where the glass sits. The gold band and emblem plate move onto the inset face. The footprint is unchanged; the brass lip adds 3 mm per side | 156 -> 204 (Tall 144 -> 192) |
| `SM_AK_Window_Lattice` placement (layout) | **Bug fix.** The lattice was placed 15 cm inside the room, floating in front of the opening (world X 0.15 / 7.85). It now sits in the wall at mid-depth (X -0.15 / 8.15), which is where the old code comment said it was | unchanged |

- Kit total: 5,120 LOD0 triangles for the 35 pieces. It is still far under the plan's environment budget.
- **Plan deviation (ceiling).** Plan section 4 lists "ceiling coffers" under Cream panel (lit). The reference and this
  stage's brief both show a dark ceiling, so the coffers use `M_AK_PlasterShade` (tinted plaster).
- **Plan deviation (upper walls).** The plan has plain upper walls with 2 windows per side. The blind shoji and the
  transoms add the reference's clerestory character without changing the window count, size or position. The real
  windows stay 150 x 90 at sill +350.

### Materials
| Material | Change | Unreal rebuild |
|---|---|---|
| `M_AK_PlasterShade` (new) | Plaster texture set x flat tint 0.30 (max albedo 0.24) | MI of the plaster master with a tint scalar |
| `M_AK_Shoji` (new) | Flat `#CCBC9C` (0.80 sRGB max, inside the plaster cap), emissive 0.55 warm `#FFD39A` | Flat params + emissive |
| `M_AK_LED` | Emission 8 -> 30 | Emissive |
| `M_AK_Paper` (lanterns) | Emission 4 -> 3.5, warmer emission colour `#FFB866` (was white-hot) | Emissive |
| Emissive materials | Roughness 0.8 | flat |
| `M_AK_Glass` | Principled glass unchanged. In Blender only, a Light Path "Is Shadow Ray" mix to Transparent, so the panes behave like Unreal's thin translucent glass for shadows. Cycles' refractive glass blocks every shadow ray, which left the decks unlit by the sun | Glass master as planned. The mix is a Cycles review nuance |
| `T_AK_Plank_*` | Base `#3B2B20` -> **`#4A3526`**. Roughness mean 0.406 -> **0.286** (satin, so the floor mirrors the glow as in the reference). Still 2048 px, seamless (periodic FFT noise) | texture set |

- Plaster albedo: `T_AK_Plaster_BC` is unchanged and still clamped at 0.80 (mean sRGB 0.800 / 0.789 / 0.686 in
  `textures_report.json`).
- `make_armory_textures.py` was rerun in full, so `textures_report.json` lists all 6 sets.

### Light table (`layout.json`, built by `lights()`)
- **Sun.** Elevation 32 deg, travelling +X and 20 deg toward +Y: it enters the **west** windows, camera-left from
  C1 as in the reference. `travel_dir` is (0.797, 0.290, -0.530) and `rot_deg` is (58, 0, -70). Both are now
  written into `layout.json` with the elevation and heading.
  - **Chosen by measurement, not by eye.** The window openings were ray-cast against the built room (cases
    included) for elevations 24-45 deg and headings from -30 to +30 deg.
  - At 32 / -20: 45 of 72 window samples land on open floor, steps or platform, and 18 hit case glass. Of the lit
    floor samples, 30 are directly visible from C1 and 27 from CX. The patches fall at X 4.6-6.2, Y 6.7-10.9: the
    east aisle, the right half of the steps and the platform edge.
  - The first version (28 deg, heading 40 deg toward the door) put most of the patch in the shadow of cases 1 and 2.
- **Plan deviation (sun elevation).** The plan says about 20-25 deg. With sills at +3.50 in an 8 m room, a sun that
  low throws the patches onto the far wall or into the cases. 32 deg is the lowest elevation that lands clear
  patches on the aisles and the platform.
- **Sun colour.** 3800 K, as in the plan (was 3900 K).
- **New lights:**
  - `UnderGlow_01..09`: one downward rect per plinth in the toe recess, W x D, 2700 K, no shadows. These are the
    plan's under-glow rects.
  - `RackLight_W/E`: one wash per corner-rack niche.
- **Colour temperatures:**
  - Case 3600 -> 4000 K, panel 2900 -> 3200 K, lantern 2400 -> 2700 K (the plan's 2700 K practicals), down
    3200 -> 3500 K.
  - These temper the orange cast. The final C1 golden still measures mean saturation 0.61, against 0.46 for the
    reference.

### Review renders (`Scripts/armory/render_armory.py`)
- **Powers (Blender W)** are case 16, panel 4, rack 7, lantern 12, down 50 (x 0.6 in golden), wash 35 and glow 4 per
  metre of perimeter. Golden runs case and panel lights at 0.85.
- **Sun and sky.** Golden: sun 100 W/m2. The floor albedo is about 0.05 linear, so a weaker sun left the patches
  invisible (measured by ray-casting the patch floor points: they were lit, just too dark). Gallery has no sun, per
  the plan (sky fill only). The golden sky behind the lattice is warm (1.0, 0.66, 0.38) at strength 2.2; the gallery
  sky is the old blue at 0.35.
- **Shafts: haze confined to the shafts.** A room-sized volume holds density 0.014 /m only inside the prisms the sun
  sweeps through the two window openings and the door (computed in the shader from `travel_dir`), anisotropy 0.35.
  - Only the sun scatters. The other ~60 practicals and the sky have volume scatter off (Unreal equivalent: Volumetric
    Scattering Intensity 0 on those lights).
  - The haze is seen by camera and through-glass rays only.
  - These three choices were each measured on crops. A uniform haze left the floor blotchy at 96 samples, and
    anisotropy 0.55 produced firefly sparkle. Setting the haze object's ray visibility flags had no measurable effect.
- **Tone.** AgX, Medium High Contrast, exposure +0.4 (both presets), a mild compositor bloom (Blender 5.2 Glare
  sockets API) and direct-light clamp 25.
  - Matched to the LOOK reference on C1 golden, as display-value luminance:

    | Measure | Reference | Final render | Before |
    |---|---|---|---|
    | Mean | 0.328 | 0.362 | 0.452 |
    | p50 | 0.282 | 0.283 | 0.422 |
    | p90 | 0.740 | 0.758 | 0.845 |
    | Share below 0.2 | 37.9 % | 35.7 % | 23.1 % |
    | Cream pixels (L > 0.6, saturation < 0.35) | 7.8 % | 21.1 % | 28.3 % |

  - The remaining cream excess is the empty pale decks and lit niche backs. The contrast rule keeps them pale, and
    items will cover them.
- **Blender flags.** Renders now run with `--factory-startup`. Without it, the user's add-ons load in the headless
  process, including the BlenderMCP add-on, which printed "BlenderMCP addon registered".
- **New CLI flags:** `--look`, `--exposure`, `--fog`, `--aniso`, `--clamp-direct`, `--no-fog`, `--uniform-fog`,
  `--no-bloom`, `--no-emis-sampling`, `--lantern-haze` and `--sun-no-scatter`. The last few are diagnostics.

### Results
- `build_armory_kit.py`: QA 35 pieces, **0 hard fails**. **35 of 35 FBX** exported through `Scripts/pipeline`
  (`export_report.json`: 0 warnings). Every SM_ keeps its `UCX_<node>_00`.
- Final renders are in `renders/look1/`, all at 1600x900 and 96 samples:
  - Golden: `C1_EntryReveal`, `C3_Case3`, `C5_CloakCase`, `C10_Hero`, `CW_WestAisle`, `CX_FromPlatform`.
  - Gallery: `C1_EntryReveal`, plus `C10_Hero_gallery` as an extra (the plan's preset for C10 is Gallery).
- About 20 s per golden frame and 15 s per gallery frame on OPTIX.
- Render rounds on the final camera set: 3 (plus single-camera diagnostics).

### Open issues
- **C10 grain (golden only).** A shaft crosses in front of the hero case glass, and 96 samples leave visible haze
  grain in that region.
  - The raw render shows the in-scatter variance directly.
  - With the glass hidden it denoises clean. It persists with density 0.008, a sun angle of 0.2 deg, DISTANCE
    sampling, step rate 2, camera-only haze, and haze excluded inside the vitrines.
  - It is a Cycles sampling limit, not a scene defect. `C10_Hero_gallery.png` is clean. The plan's C10 preset is
    Gallery anyway.
- **Door exterior in CX.** The open door shows a blown-out sunlit exterior. `SM_AK_Door_Leaf` (plan 7.1 #6) is not
  in the lean kit.
- **Unreal glass.** The FBX material for `M_AK_Glass` now sits behind a Mix shader. Unreal rebuilds its materials
  from `material_spec`, so nothing is lost, but the FBX's embedded glass parameters are generic.

## 2026-09-27: Build stage (recorded retroactively in fix round 1)

The build stage wrote no section. The independent measurer (`measure_r1.json`) listed these deviations from plan 3.2.
They are recorded here. Items marked *fixed in fix1* were moved back to the plan in the next section.

| Deviation in the scene after the build stage | Status |
|---|---|
| East cases 6, 7 and 8 at X 6.45-7.55 (plan: 6.30-7.40, 6.40-7.50, 6.60-7.60) | **Accepted override**, kept. The plan's 3.2 now has an as-built note |
| Result of that: east mid-row aisles of 154.2 cm (3<->6) and 164.2 cm (2<->6), over the plan's 130-150 | Kept. They are wider, not narrower, so there is no boom or camera risk |
| West cases mirrored from the east override to X 0.446-1.554 (case 4 centre 1.00, case 5 centre 1.00) | *Fixed in fix1* (cases 4 and 5 back on plan) |
| South window pair at Y 4.25-5.75 (plan 5.25-6.75) | *Fixed in fix1* |
| Door and window 3.1 cm timber linings: clear openings 143.9 x 196.9 (door) and 143.9 x 83.9 (windows) | *Fixed in fix1* (clear openings are now 150 x 200 and 150 x 90) |
| 2 extra lanterns on the platform at (0.6, 10.7) and (7.4, 10.7), on top of the plan's 4 | Kept (6 lanterns, as plan 7.3 "x6") |
| Wall panels 9 end at Y 8.93 (8 bays, Y 1-9), not the plan's Y 9.50 | Kept. The next 1 m bay would run into the steps' lantern at (1.7 / 6.3, 9.9) |
| Case 6 is 150 long and case 8 is 140 long: the section 5 families, not the section 3.2 extents (140 and 130). Their centres are on the plan | Kept. The plan's two tables disagree, and the build follows the family table |

## 2026-09-27: Fix round 1 (measurer r1 + blind judge 5.5/10)

Headless only (`blender -b --factory-startup`), no GUI, no MCP, no Unreal. Scripts changed: `build_armory_kit.py`,
`render_armory.py` and `make_armory_textures.py` (all changes are marked `fix1` in the code). All numbers below were
measured by ray casts or bounding boxes in the rebuilt `ArmoryKit.blend` (scratch script `measure_fix1.py`).

### Layout fixes (measurer r1)
| Finding | Fix | Measured after |
|---|---|---|
| South windows 100 cm south of the plan | Upper-wall run on both long walls is now, along Y: `WallUpper_1` 0-1, `WallUpper_2` 1-3 and 3-5, `WallUpper_Window_2` 5-7, `WallUpper_1` 7-8, `WallUpper_Window_2` 8-10, `WallUpper_2` 10-12 (`UPPER_RUN`). The post at Y 6 is now a `Post_340` (top +3.40, under the sill), and the post at Y 5 is a `Post_480`. Lattices moved with the openings | Clear openings, both walls: **Y 5.251-6.749 and 8.251-9.749**, Z 3.501-4.399. Lattices at Y 5.249-6.751 and 8.249-9.751. `Post_340` at Y 6 and Y 9 on both walls |
| Case 5 at X 1.00 (15 cm off) | Case 5 centre X 1.15, with its `CaseLight_05` and `UnderGlow_05` (they are derived from the case table) | Plinth **X 0.596-1.704**, Y 5.996-7.404. Aisles 5<->3 **139.2 cm**, 5<->2 **149.2 cm**, clearance to the panel front 34.5 cm |
| Case 4 at X 1.00 (on the 5 cm limit) | Back on plan, centre X 0.95 | Plinth **X 0.396-1.504**, Y 2.196-3.704. Aisle 4<->1 **149.2 cm**, clearance to the panel front 14.6 cm |
| Door clear 143.9 x 196.9 | Rough opening widened to X 0.219-1.781 (piece-local), head 2.031, so the 3.1 cm lining leaves the plan's clear opening. The casing trim moved out with it. Threshold and entry mat unchanged (150) | Clear **X 3.251-4.749 (149.8 cm)** at z 0.5, 1.0 and 1.9; head **+1.999**. The 0.2 cm short is the kit's per-box overlap growth |
| Window clear 143.9 x 83.9 (recorded, not a finding) | Same treatment: rough opening X 0.219-1.781, sill 0.969, head 1.931. `SM_AK_Window_Lattice` is now 150 x 90 (plan 7.1 #4), rails at +3.83 and +4.09, level with the blind panels | Clear **149.8 x 89.8** at sill +3.50 |

- All west-side aisles are now inside 130-150 cm. The minimum walking clearance is 139.2 cm (5<->3).
- The east cases are unchanged (accepted override; see the build-stage section).
- `ARMORY_PLAN.md` v2 3.2 already carries these door, window and case 4/5 numbers. I added an as-built note under
  its table (clear openings, east override, section 5 lengths, dark decks). `ARMORY_LAYOUT` is drawn from the plan
  table, and no plan number moved, so `armory_layout.py` was not rerun.
- `layout.json` now carries `openings` (clear window Y/Z, door X/Z). `render_armory.py` reads the shaft prisms
  from it instead of a hard-coded copy.

### Sun, rerun ray study (the windows moved)
- The window openings were ray-cast against the rebuilt room (cases included), for elevations 24-46 deg and
  headings -40 to +40 deg. That is 72 samples per window.
- **Chosen: elevation 32 deg, heading 0 deg** (travel straight +X, `travel_dir` (0.848, 0, -0.530)). The look pass
  used -20 deg.
- Results at the chosen angle:
  - 42 and 46 of the 72 samples per window land on open floor or plinth tops, the best balance of any candidate.
  - Of those floor points, 75 are visible from C1 and 68 from CX (the best combined score).
  - The patches fall at X 4.7-6.6, Y 5.3-6.7 and 8.3-9.7, in the east aisle with an edge on case 6.
- With heading 0 the sun no longer enters the door, so there is no door shaft.
- Sun angle 0.8 -> **0.15 deg**. At a ~7 m throw, 0.8 deg blurred the 25 mm lattice bars (10 cm penumbra) into
  one soft blob. At 0.15 deg the penumbra is ~2 cm, and the 12 x 3 lattice grid reads on the floor (C1, CX).
- There are still 2 lattice patches, not the judge's 3-5. The plan fixes 2 windows per side, and one sun can only use
  one side's pair.

### Look fixes (blind judge, room/casework/lighting only)
| Judge delta | Done | Where |
|---|---|---|
| 1. Dark decks | Case decks are `M_AK_Felt` (`#221D1A`, rough 0.95) with an 8 mm brass edge just inside the glass. The tall-case backdrop is felt with a 10 mm brass frame (was cream plaster) | `SM_AK_Case_*_Plinth`, `SM_AK_Case_Tall_Glass` |
| 2. Niches as dark bays | `SM_AK_WallPanel_Lit` has a walnut back board (`M_AK_BackBoard`, `#4E3A2A`). It is lit by a grazing wash (the `PanelLight` rects are now aimed down the board, 30 W) and by two soft LED lines in the back corners (`M_AK_LEDSoft`, emit 4). It has a black lacquer counter at +0.90 with a brass nosing, a closed lacquer cabinet front below, and a dark 13-bar lattice grille over dim shoji paper at the top. `SM_AK_CornerRack` (the two tall panels flanking the painting) gets the same back board, corner LEDs and grille | kit pieces |
| 3. Harder sun, lattice patches, fewer god rays | Sun 0.15 deg, re-aimed by ray study (above). Haze density 0.014 -> **0.006** | render |
| 4. Less sepia haze, deeper blacks | The haze now fades out below +2.7 m (none under +1.2); low haze lit by the sun in front of the case glass put speckle on the dark decks (C3 stands inside the south shaft). Only camera rays see the haze now (a cleanup; on its own it did not remove the speckle). Case light 4000 -> 4300 K, downlights 3500 -> 4000 K. The pale decks and panels that lifted the blacks are gone | render, `lights()` |
| 5. Lower-feeling ceiling, exterior | Blind shoji emission 0.55 -> **0.06**, and the paper is darker (`#6A5F4E`), so only the 4 real windows glow. Camera and glossy rays now see an exterior through the windows and the door: a tree line of green foliage under a warm sky (`exterior()` in the world shader). Diffuse rays keep the flat sky, so the room fill is unchanged. The ceiling height and coffers are unchanged (plan 3.1 datums; C1 is the plan camera) | render, `M_AK_Shoji` |
| 6. Glass grain | OIDN with albedo and normal guides, prefilter Accurate, quality High. Indirect clamp 6 -> 3, caustics off, glossy blur 1.0. The speckle on the decks was the haze, not the glass. Measured on a C3 deck crop (mean absolute high-pass, 48 samples): 0.0015 with no haze, 0.0020 with the haze at full height (camera rays only), 0.0016 with the height fade. **C10 golden is now clean**, which closes the look pass's open issue | render |
| 7. Floor | `T_AK_Plank_*` tile 4 m -> **2 m**, the floor piece's size. At 4 m every 2 x 2 piece showed the same quarter with a seam, which read as parquet squares. Boards are 12.5 cm wide (were 20), 2 m long with staggered butt joints. Base `#4A3526` -> `#3F3129` (saturation 0.49 -> 0.35). Grain contrast 0.16 -> 0.07 and board tint 0.07 -> 0.045: the per-board grain shift made a blocky checker. Still satin (roughness 0.285) | textures |
| 8. Hero alcove | `SM_AK_PaintingPanel` has a 12 mm brass fillet inside the frame and an 8 mm LED halo around the outer edge (a glowing gold border). The black tiered stand is an inner mount (`DSP_Kake_Hero`, P4), so it is out of scope | kit piece |
| 9. Entry framing | **Not done.** C1 is the plan's camera (inside the door, +230). The door posts, the threshold beam and the entry lanterns at (0.9 / 7.1, 0.6) are outside its frustum. The reference is shot from outside the door | - |
| 10. Plinths | Brass inlay frame (6 mm) on the front face marks the front panel, with the blank emblem plate at its centre. The heights stay on the plan's section 5 table | `SM_AK_Case_*_Plinth` (not Tall) |

- Out of scope by design: items, vases, banners, crests and text. The emblem plates stay blank.
- **Plan deviation (contrast rule, section 4).** The plan puts items on pale linen decks and cream backdrops. This
  round follows the look reference and the review: decks and backdrops are dark felt with gold trim.
  - It is a material swap (an MI in Unreal). G0-1 still measures every item against its case interior.
  - If a near-black item fails 3:1, that case goes back to linen or gets a red cloth insert.
- New materials: `M_AK_Felt` (MI of `M_Fabric_Master`), `M_AK_BackBoard` (MI of `M_AK_Wood_Master`) and
  `M_AK_LEDSoft` (emissive MI). `M_AK_Linen` is no longer used by any piece.

### Tone (C1 golden, display-value luminance; stats script as in the look pass)
| Measure | Reference | fix1 | look1 |
|---|---|---|---|
| Mean | 0.328 | 0.258 | 0.362 |
| p10 | 0.061 | 0.073 | 0.068 |
| p50 | 0.282 | 0.202 | 0.283 |
| p90 | 0.740 | 0.556 | 0.758 |
| Share below 0.2 | 37.9 % | 49.5 % | 35.7 % |
| Cream pixels | 7.8 % | **5.9 %** | 21.1 % |
| Mean saturation | 0.458 | 0.704 | 0.607 |

- Exposure is +0.8 in both presets (was +0.4). The dark decks and niches took most of the old mid-tones away.
  Panel wash 4 -> 30 W, rack 7 -> 20 W, downlights 50 -> 80 W.
- The frame is now darker in the mid-tones than the reference (p50 0.20 vs 0.28), and the cream excess is gone.
- Saturation is **higher** than before (0.70 vs 0.46). The near-black warm timber dominates the frame, and its
  (max - min) / max is high. That is still open (see below).

### Results
- `build_armory_kit.py`: QA 35 pieces, **0 hard fails**. **35 of 35 FBX** exported through `Scripts/pipeline`
  with 0 warnings. Every SM_ keeps its `UCX_<node>_00`.
- Kit total: 6,320 LOD0 triangles (was 5,120).
  - WallPanel_Lit 96 -> 348, CornerRack 96 -> 384, PaintingPanel 60 -> 156.
  - Plinths 204 -> 300 (Tall 192 -> 240), Tall glass 216 -> 252.
- `make_armory_textures.py` was rerun in full (`textures_report.json` lists all 6 sets).
- Renders in `renders/fix1/`, 1600x900, 96 samples:
  - Golden: `C1_EntryReveal`, `C3_Case3`, `C5_CloakCase`, `C10_Hero`, `CW_WestAisle`, `CX_FromPlatform`.
  - Gallery: `C1_EntryReveal`.
- Render rounds: 4 low-res rounds and 2 final rounds.

### Open issues
- **Warm cast.** Mean saturation is 0.70 against the reference's 0.46. The next lever is a less saturated timber
  (plan `#221A15`) or cooler fill. I did not change the plan's timber colour this round.
- **Only 2 sun patches** (the plan's 2 windows per side). A third would need a window change in the plan.
- **Mid-tones below the reference** (p50 0.20 vs 0.28). Items in the cases will add light-coloured mid-tones.
  Otherwise, raise the case and panel light power at G0.
- **Door leaf.** `SM_AK_Door_Leaf` is still not in the lean kit. The open door now shows the green exterior instead
  of a blown-out white, and the case glass reflects it as a dim green panel (C3, C10).
- **Entry framing (judge delta 9)** needs a camera outside the door, which differs from the plan's C1.

## 2026-09-27: Unreal assembly (new project ArmoryLab, level `/Game/Armory/Maps/L_Armory`)

**Scope.** A new UE 5.8 project, the 35 kit pieces and 18 textures imported, the kit materials, the empty room assembled
from `layout.json` with the golden-hour light table, then offscreen stills. No items, no proxies, and the emblem plates
stay blank. DemoGame_1 was only read (its render settings). No unreal-mcp, no Blender GUI or MCP, and no other session's
process, project or lock was touched. The other session's `UnrealEditor.exe` (pid 16028) was left alone. Twice a
step waited for another session's `UnrealEditor-Cmd` to finish, and only one Unreal process of ours ran at a time.

### Where things are
- Project: `C:\Users\Cody\Documents\Unreal Projects\ArmoryLab\ArmoryLab.uproject`. EngineAssociation 5.8, Blueprint-only
  (no Modules), plugins PythonScriptPlugin and EditorScriptingUtilities.
- `Config/DefaultEngine.ini` is written by `make_project.py`:
  - DemoGame_1's `RendererSettings` section, copied whole: AllowStaticLighting False, VSM, mesh distance fields,
    Lumen GI + reflections, ray tracing, Substrate, local-exposure defaults.
  - DX12 with the SM6 shader formats, and HardwareTargeting.
  - `[ConsoleVariables] Interchange.FeatureFlags.Import.FBX=0`.
  - GameDefaultMap and EditorStartupMap set to `L_Armory`.
- Content: `/Game/ArmoryKit/{Meshes, Textures, Materials}`, `/Game/Armory/Maps/L_Armory`. 62 MB.
- Scripts: `Scripts/armory/unreal/`.

| Script | Role |
|---|---|
| `ak_common.py` | Paths, the Blender to UE conversions and the photometric constants |
| `make_project.py` | Writes the project files. Plain Python |
| `blender_bounds.py` | Blender `-b`. The world AABB of every Assembly instance, plus slot names, tris and UCX per piece |
| `ak_import.py` | Commandlet. Meshes and textures |
| `ak_materials.py` | Commandlet. Masters, instances and slot assignment |
| `ak_level.py` | Commandlet. The level, the bounds gate and the save |
| `ak_verify.py` | Commandlet in a fresh process. Every gate again, on the saved assets |
| `ak_capture.py` + `run_capture.ps1` | Offscreen editor. The stills |
| `ak_image_stats.py` | System Python (Pillow). Tone, sweep and convergence stats |
| `blender_units_probe.py`, `blender_tone_ladder.py` | Blender-side calibrations |
| `run_armory_unreal.sh` | The runner |

- Results and logs are in `WorkFiles/armory/build/unreal/`:
  - `{make_project, import, materials, level, verify, capture, capture_stats}.json`
  - `blender_bounds.json`, `blender_units_probe.json`, `tone_ladder_blender.json`
  - `logs/`, including `timings.txt`
  - `captures/`

### Commands (all idempotent)
- Everything: `bash Scripts/armory/unreal/run_armory_unreal.sh`. The steps are project, bounds, import, materials,
  level, verify and capture.
- Any subset: `run_armory_unreal.sh level verify capture`.
- Capture options (environment variables):

  | Variable | Effect |
  |---|---|
  | `AK_CAMS` | Which cameras to capture |
  | `AK_FRAMES` | Captures per view (default 96) |
  | `AK_WARM` / `AK_WARM_SEC` | Warm-up: 600 ticks and at least 20 s |
  | `AK_SWEEP=1`, `AK_SWEEP_OFFSETS` | Exposure sweep on C1 |
  | `AK_LADDER=1` | Tone ladder and light-unit rig |
  | `AK_DIAG` | Show-flag diagnostics |

- `AK_EXPOSURE_BIAS` overrides the level's exposure. `AK_FORCE_IMPORT=1` re-imports unchanged sources.
- Then `py -3 Scripts/armory/unreal/ak_image_stats.py`.
- How re-runs stay idempotent:
  - The import skips any asset whose source sha256 matches `import_manifest.json`.
  - The masters are rebuilt from an empty graph, and the instances are cleared and re-set.
  - The level loads if it exists and destroys only actors tagged `AK_Managed` (263 of them), then respawns.
  - The capture clears only its own `captures/` output.
- Final full run, 2026-09-27 02:08:06 to 02:09:23 (77 s total):

  | Step | Time |
  |---|---|
  | project | 0 s |
  | bounds | 2 s |
  | import | 6 s (unchanged sources skipped; the first real import took 7 s) |
  | materials | 8 s |
  | level | 7 s |
  | verify | 6 s |
  | capture | 44 s: 32 s in-engine, 2,237 ticks, 96 captures per view |

- The commandlets use the SnowFlower v4 flags: `-run=pythonscript -unattended -nop4 -nosplash -nullrhi -nosound`.
  Each is preceded by a wait loop on `tasklist | grep -i UnrealEditor-Cmd`.
- About 10 capture rounds and 8 level rounds ran during the stage, as diagnostics and tuning (01:42-02:09). Only the
  final run's outputs are on disk.

### Results (fresh-process verify, `verify.json`: all 5 gates pass)
1. **Meshes: 35 of 35.**
   - Every mesh's convex hull count equals its Blender UCX count: Steps 3, Door 3, Window 4, all others 1.
   - No other simple collision, and no auto collision.
   - LOD0 triangles equal Blender's for every piece.
   - Every material slot holds the instance of the same name.
2. **Textures: 18 of 18.** BC sRGB TC_Default; ORM linear TC_Masks; N linear TC_Normalmap with no green flip (the maps
   are DirectX). All 2048, with mips.
3. **Materials: 5 masters + 17 instances**, each instance on its expected parent with the Blender values read back.
4. **Level: 191 of 191 instances**, labelled `<piece>__<nnn>` like the Blender Assembly objects.
   - **Bounds gate: max error 0.0001 cm over all 191 actors**, against the 1 cm tolerance. Conversion:
     (x*100, -y*100, z*100), yaw -rot_z.
   - Door piece `SM_AK_WallLower_Door_2__057`: UE [299.944, -3.057, -0.057] to [500.056, 30.057, 252.056], identical to
     the converted Blender bounds.
   - East-wall piece `SM_AK_WallLower_2__072`: [797.969, -200.031, -0.030] to [830.030, 0.031, 252.031], error 0.0001 cm.
5. **Lights and environment.**
   - Sun: 10,000 lux, pitch -32.0, yaw 0. Its forward (0.848, 0, -0.530) equals the Blender travel_dir converted.
   - 59 local lights, per role:

     | Type | Count |
     |---|---|
     | Rect | 37: case 9, glow 9, panel 16, rack 2, wash 1 |
     | Spot (down) | 16 |
     | Point (lantern) | 6 |

   - Shadow casting: only the 9 case lights (limit 12).
   - SkyAtmosphere; SkyLight with real-time capture.
   - ExponentialHeightFog with volumetric fog.
   - Unbound PPV: manual exposure, bias -3.34.
   - PlayerStart at (400, -90, 95) cm, facing -Y in UE (+Y in Blender, into the room). It stands on the entry mat.
   - 7 review CameraActors.
- **Outliner folders:**
  - `Architecture/{Floor, Ceiling, Walls/South|North|East|West, Posts, Windows, Entry, Platform}`
  - `Casework/{Cases, WallPanels, CornerRacks, Painting, Lanterns}`
  - `Lights/{Sun, CaseLights, UnderGlow, WallPanels, CornerRacks, Lanterns, Downlights, PaintingWash, Sky, PostProcess}`
  - `Cameras`, `Gameplay`
- **Stills:** `unreal/captures/C1_EntryReveal.png`, `C10_Hero.png` and `CW_WestAisle.png`, at 1600x900.
  - FOV is horizontal, from a 36 mm sensor: 73.74, 48.46 and 73.74 deg.
  - Checkpoints are in `captures/sequence/`; diagnostics, sweep, ladder and light-unit frames are in `captures/diag/`.

### Photometric conversion (measured, not assumed)
- **Cycles probe** (`blender_units_probe.json`):
  - A white Lambertian plane under a sun of strength 1 has radiance 0.3183 (= 1/pi).
  - A 1 W point light at 1 m gives 0.0251 (irradiance ~1/(4 pi)).
  - A 1 W 10 cm area light at 1 m gives 0.0997 (on-axis intensity P/pi).
  - Emission strength 1 gives radiance 1.
- **One factor K = 100 lux per Blender W/m2** keeps every Blender ratio:

  | Blender | Unreal |
  |---|---|
  | Sun | lux = K*S (10,000 lux) |
  | Point / spot | cd = K*P/(4 pi) |
  | Rect | cd = K*P/pi |
  | Emission strength s | emissive = K*s*colour |

  - Light colours are the same Tanner Helland kelvin fit as `render_armory.py`, set as linear colour.
  - The golden preset scales apply: case 0.85, panel 0.85, down 0.6.
- **Unreal rect lights deliver 2x their candela.** `RectLightSceneProxy.cpp` divides the colour by
  `0.5 * SourceWidth * SourceHeight`.
  - Measured in a closed black box: a 0.18 grey quad 2 m under a 1000 cd point light reads 1.035x the expected
    14.3 nits.
  - The same quad under a 10 x 10 cm rect light of 1000 cd reads **2.04-2.07x**.
  - So every rect light is set to half the Blender-equivalent candela (`RECT_CANDELA_SCALE = 0.5`).
  - Examples: CaseLight_01 216 cd, UnderGlow_01 433 cd, Down_11 382 cd, Lantern 95 cd.
- **Exposure.**
  - Analytic parity would be 2^bias = 2^0.8/K, which gives -5.84.
  - **Tuned to -3.34.** That is the bias whose C1 capture matches the Blender golden C1 (renders/fix1) in both mean and
    median display luminance. Sweep, error in mean + p50: -3.84: 0.126; -3.59: 0.066; **-3.34: 0.006**; -3.09: 0.069.
  - Why +2.5 EV, from the tone ladders (13 emissive quads of known radiance through each engine's own exposure and
    tonemapper): for the same scene radiance at -3.34, Unreal shows mid-tones 1.2 EV brighter than AgX Medium High
    Contrast +0.8 (0.5 EV at display 0.2, 1.7 EV at 0.75), and crushes the darks.
  - So about 1.3 EV of the gap is the tone curve and exposure constant.
  - The other ~1.2 EV is less mid-tone radiance in the Lumen room than in the Cycles path-traced room. This is after
    the sun, point, spot and rect units were each verified.
  - Blender's own bounces are worth only +0.035 mean display on C1 (48 samples, diffuse and glossy bounces 0 vs
    default), so the balance of the remainder is not pinned down.

### Tone vs the Blender golden renders (display luminance, `capture_stats.json`)
| View | Engine | Mean | p10 | p50 | p90 | < 0.2 | Cream | Saturation |
|---|---|---|---|---|---|---|---|---|
| C1 | Unreal | 0.271 | 0.023 | 0.212 | 0.631 | 48.1 % | 5.9 % | 0.80 |
| C1 | Blender | 0.258 | 0.073 | 0.202 | 0.556 | 49.5 % | 5.9 % | 0.70 |
| C10 | Unreal | 0.240 | 0.044 | 0.105 | 0.767 | 68.3 % | 9.7 % | 0.81 |
| C10 | Blender | 0.221 | 0.053 | 0.165 | 0.555 | 61.6 % | 0.9 % | 0.76 |
| CW | Unreal | 0.236 | 0.020 | 0.150 | 0.583 | 57.1 % | 4.9 % | 0.82 |
| CW | Blender | 0.244 | 0.054 | 0.189 | 0.533 | 51.8 % | 5.2 % | 0.72 |

### How representative the captures are
- **Lumen is ON in the captures, and it had to be switched on.** UE 5.8 `SceneCaptureRendering.cpp` sets the GI and
  reflection method of every scene capture to None by default. The first capture round (01:49) was therefore
  unoccluded sky-light fill with no Lumen. It is superseded.
- `ak_capture.py` now overrides the capture's post-process settings:
  - Lumen GI and reflections, surface cache 1.0, front-layer translucency reflections.
  - It does not override exposure, so the level's PPV sets it.
- Proof, as diagnostic frames of C1:

  | Frame | Mean display | Change vs final |
  |---|---|---|
  | Final | 0.271 | - |
  | Lumen GI off | 0.476 (the unoccluded fallback) | 61 levels |
  | Lumen reflections off | 0.308 | 12.8 levels |
  | Volumetric fog off | 0.242 | 7.2 levels (the shafts are real) |

- **Engine frames, not one shot.** The capture runs in a full offscreen editor (see D4), so the engine ticks:
  - shaders compile, distance fields build and the real-time sky light recaptures;
  - Lumen, TSR and volumetric-fog history accumulate over 96 captures per view;
  - all of it after at least 20 s / 600 ticks of warm-up with the level loaded.
- **Convergence**, as the mean absolute change between checkpoints (8-bit levels):

  | Interval | C1 | C10 | CW |
  |---|---|---|---|
  | 1 -> 4 | 5.0 | 6.1 | 5.6 |
  | 16 -> 32 | 1.2 | 0.9 | 1.1 |
  | 64 -> 96 | 0.58 | 0.50 | 0.58 |
  | Frame 1 vs final | 8.5 | 8.5 | 8.9 |

  - The last 32 frames still move 4-5 % of pixels by more than 4 levels. That is temporal noise (fog, Lumen, TSR
    jitter), not drift.
  - A single capture would NOT have been representative.
- **Limits.**
  - These are SceneCapture2D stills in the editor world, not PIE or a packaged game. There is no motion, and no frame
    time was measured (G0-5 not run).
  - Scene-capture defaults can differ from the main view in minor show flags.
  - Ray tracing is enabled on the RHI (log: "Ray tracing is enabled"). Which Lumen tracing path (HW or SW) the capture
    used was not verified.

### Deviations from the plan / brief, and decisions
- **D1 Materials.**
  - What the plan says: section 4 puts new masters in `material_spec.json` (the np builder) and makes brass an MI of
    `M_Steel_Master`.
  - The brief forbids touching the pack system, and ArmoryLab has no pack. So `ak_materials.py` builds its own
    masters in `/Game/ArmoryKit/Materials`.
  - Masters:
    - `M_AK_Textured_Master`: BC x Tint, ORM, N, UV Scale.
    - `M_AK_Flat_Master`: clear-coat shading via MakeMaterialAttributes. `MP_CustomData0/1` are hidden from Python.
      Only the lacquer uses it.
    - `M_AK_FlatNoCoat_Master`: default lit; brass, felt, linen, back board.
    - `M_AK_Emissive_Master`.
    - `M_AK_Glass_Master`.
  - The plan's Wood/Plaster split and the decal master are not built.
  - `M_AK_Plaster` and `M_AK_Linen` exist but no slot uses them (the look pass and fix1 moved those surfaces to
    timber and felt).
  - Instance names equal the Blender material names (`M_AK_Timber` etc.), per the brief, not `MI_`.
- **D2 Glass.**
  - It is a translucent master, not the plan's Substrate thin-translucent model:
    - Surface ForwardShading lighting;
    - base colour 0.012, roughness 0.02, specular 0.5;
    - opacity 0.08 face-on, rising to 0.45 at grazing (Fresnel, exponent 5).
  - With Lumen front-layer reflections on (PPV), the panes reflect the room. Without them they reflected the sky and
    read frosted blue.
- **D3 Import.**
  - Generate Lightmap UVs is OFF: AllowStaticLighting is False, so the FBX's own UV1 is kept.
  - Nanite is OFF: the largest piece is 552 triangles, under the plan's ~2k threshold.
  - Import normals and MikkTSpace. `SM_AK_EntryMat` and `SM_AK_PaintingPanel` log a harmless "degenerate tangent"
    warning: their hidden faces sample one texel.
- **D4 Capture process.**
  - The capture is a SEPARATE process, as the brief asks, but it is a full offscreen editor:
    `UnrealEditor-Cmd -RenderOffscreen -dx12 -ExecutePythonScript`, driven by a Slate post-tick callback (the
    BlackCloak review pattern). It is not `-run=pythonscript`.
  - A pythonscript commandlet never ticks the engine, so Lumen and the sky capture could not accumulate.
  - The same one-Unreal-at-a-time guard applies, and it kills only its own pid on a 30 min timeout.
- **D5 Spawning.** `spawn_actor_from_object` spawns nothing in a commandlet ("No actor was spawned"). Meshes are spawned
  as StaticMeshActor plus `set_static_mesh`.
- **D6 Lights.**
  - The table is followed as written.
  - Specular is hidden (`specular_scale 0`) on the case, glow, panel and rack lights, mirroring Blender's
    `visible_glossy False`.
  - Volumetric scattering is 0 on every local light and on the sky light (Blender: only the sun scatters).
  - Attenuation radius 20 m (Blender lights have no cutoff).
  - Spot inner cone = outer cone x (1 - blend 0.5). Rect barn doors off.
  - Rect sizes: downward lights put Blender size_x on UE source_height; aimed lights put it on source_width.
  - Sun source angle 0.15 deg, atmosphere sun light on.
- **D7 Fog.**
  - ExponentialHeightFog: FogDensity 0.06 (= 0.006 /m, the Blender haze; UE uses density/1000 per cm), falloff 0.001.
  - Volumetric fog: anisotropy 0.35, albedo (1, 0.93, 0.85).
  - Inscattering and directional inscattering are black, sky-atmosphere contribution 0.
  - Volumetric fog distance and fog cutoff 30 m, so the exterior is not fogged.
  - Blender confined the haze to the sun prisms and faded it out below +2.7 m. Unreal's haze is uniform, so the shafts
    reach the floor.
- **D8 Sky.**
  - SkyAtmosphere and a real-time-capture SkyLight (intensity 1) replace Blender's flat warm world and tree-line
    exterior. The door and windows show a physical 32-degree sky, not foliage.
  - Sky lighting off changes C1 by only -0.009 mean.
- **D9 Post process.** Vignette 0 (the Blender renders have none); Lumen front-layer translucency reflections on.
  Local exposure keeps DemoGame_1's 0.8 / 0.8 project defaults.
- **D10 Extras.** Seven CameraActors (`CAM_<name>`, horizontal FOV) so the review views can be piloted. The captures
  use them, so the saved camera transforms are what gets verified. No GameMode was set: PIE uses the engine default
  pawn from the PlayerStart (lean build, no character).

### Open issues
- **Tone curve.**
  - Unreal's filmic toe crushes the darks: p10 0.02-0.04 vs Blender 0.05-0.07.
  - It keeps more saturation: 0.80-0.82 vs 0.70-0.76.
  - Mean and p50 are matched on C1 only; CW is 0.2 EV darker.
- **C10 hero deck reads pale.**
  - The felt deck under the case light is display ~0.55 vs 0.23 in Blender, the painting is brighter, and cream is
    9.7 % vs 0.9 %.
  - The deck radiance itself now matches Blender (after the rect fix). The room-matched exposure sits about 1.2 EV
    above radiance parity, so directly lit decks come out hot.
  - The plan's "manual exposure per camera" cannot fix this alone: C10's p50 is low while its p90 is high.
  - Revisit when items sit on the decks. Options: lower case light power in Unreal only, or more room fill.
- **C10 glass.**
  - The top pane seen from below at a ~3 deg grazing angle reads as a white band (the Fresnel edge opacity).
  - The brass emblem plate reads dark (0.12 vs 0.72): in Unreal it reflects the dark room.
  - Candidates: tune Edge Opacity and the brass roughness at the G0-10 glass gate.
- **Unexplained ~1.2 EV** of mid-tone radiance between the Lumen room and the Cycles room. Emissive-as-light (lantern
  paper, LED strips) is the main suspect: Cycles samples these as light sources, while Lumen only picks them up
  through the surface cache.
- **Not done here.** The door leaf (not in the kit), a character or GameMode, the Gallery preset, performance (G0-5),
  and the 10 m width variant.

## 2026-09-27: Independent Unreal verification (verifier, not the builder)

Everything below was measured in a **fresh** process, using the verifier's own scripts in
`WorkFiles/armory/build/unreal/verify/`. None of the builder's `ak_*` modules or its `blender_bounds.json` were reused.
- `vf_unreal_dump.py`: pythonscript commandlet, `-nullrhi`, read-only. It started at 02:15 only after `tasklist` showed
  no UnrealEditor-Cmd running, and it exited 0 with no `Error:` lines. It ends by writing `vf_unreal.json`.
- `vf_blender_side.py`: headless Blender, bounds taken from the evaluated meshes of the Assembly collection. It ends
  by writing `vf_blender.json`.
- `vf_compare.py` compares the two dumps and writes `vf_report.json`.
- `vf_image_stats.py`, `vf_blackmask.py` and `vf_c10_band.py` measure the captures. They write `vf_images.json`,
  `vf_mask_*.png` and `vf_c10.json`.
- The project was not modified: `L_Armory.umap` still has its 02:08:29 timestamp after the run.

| Gate | Result | Numbers |
|---|---|---|
| Meshes | PASS | All 35 FBX have a StaticMesh. Convex hulls total 42, equal to the 42 Blender UCX (32 pieces with 1, 2 with 3, 1 with 4). No box, sphere or capsule collision. All 89 expected slots are present by name with no extra slots. Every material is a MIC under `/Game/ArmoryKit/Materials` (15 distinct), with a `/Game` master and nothing from `/Engine`. |
| Level | PASS | L_Armory loads. 263 actors, of which 191 are StaticMeshActors. That equals the 191 layout.json instances and the 191 Blender Assembly objects. No null or engine mesh, no engine or null material, no overrides, no hidden actors, and every label matches its mesh. |
| Bounds | PASS | All 191 instances compared. The largest error is 0.00011 cm, against a 1 cm tolerance. Rotations checked: 0 (97), 180 (14), -90 (41) and 90 (39). The reported sample covers 10 different pieces, including rot 90, -90 and 180, and each has an error of at most 0.00004 cm. Evaluated and raw mesh bounds are identical. |
| Lights | PASS | 1 directional light (10,000 lux, shadows), 37 rect, 16 spot and 6 point. Total 60, which equals the layout. 9 local lights cast shadows (the CaseLights), within the limit of 12. There is a SkyLight with real-time capture, one SkyAtmosphere, and height fog with volumetric fog on. The PPV is unbound, with manual exposure and a bias of -3.34. |
| Config | PASS | Every RendererSettings key matches DemoGame_1. DX12 is set, with SM6. `GameDefaultMap=/Game/Armory/Maps/L_Armory.L_Armory`. The cvars in the fresh process confirm GI=1 (Lumen), Reflections=1, VSM=1 and Substrate=1. Nothing in `Saved/Config` overrides these. |
| Captures | **FAIL** | See below. |

**Captures** (the builder's PNGs, written 02:09, after the level was saved at 02:08:29; compared with fix1 golden):
- **C1 and CW read as the same room.** The same pieces sit in the same places, and every material is assigned: no
  checker or default grey anywhere. Nothing is missing. Block luminance correlation is 0.87 for C1 and 0.80 for CW.
- **Crushed shadows (tone).** Pixels below 0.02 luminance cover 8.2 % of C1 in Unreal vs 0.8 % in Blender, and 9.8 %
  vs 2.4 % in CW. They cluster on the shaded lacquer plinth faces and the upper walls and corners, so those surfaces
  go black.
- **C10 hero (the fail).**
  - The top glass pane is a full-width band about 24 px tall at display 0.85-0.93, vs 0.19 in Blender. It is an
    obvious blown-out surface.
  - The felt deck is 0.45 vs 0.21 in Blender.
  - The brass emblem plate is RGB (0.15, 0.02, 0.00) vs (0.71, 0.37, 0.00), so it reads dark red, not brass. The C1
    foreground plates show the same thing.
  - The glass loses the room reflection that the Blender shot is built on.
- **Capture limits.**
  - These are the builder's captures, not re-rendered by the verifier.
  - Only three stills, at a single tuned exposure bias.
  - Whether Lumen took the hardware or the software path is unverified. `r.RayTracing=1` alone does not prove it.
- **Verdict: not passed.** All five structural gates pass. The look gate fails on C10: a blown-out glass band, a
  hot deck and a mis-reading brass plate. The builder disclosed all of these, but disclosure does not clear the gate.

## 2026-09-27: look pass 2 (main chat, after the workflow; user: "close to the reference image besides the items")

Driven by the r2 blind judge (6/10) and a side-by-side with armory3_reference2. Blender build + Unreal scripts.

- **Windows (plan deviation, follows the LOOK reference):** every 2 m upper bay of both long walls is now a 150 x 100
  lattice window (sill +2.65, head +3.65, shoji grid 5 x 4), with a dim lattice screen above and the transom under the
  ceiling. Was: two 150 x 90 windows per side at +3.50 plus blind screens. Odd posts stop at +2.60 (`SM_AK_Post_260`,
  replaces `Post_340`).
- **Exterior:** `SM_AK_Ext_Backdrop` (16 x 7 m emissive card, `T_AK_Backdrop_BC`, sunlit trees, casts no shadow) outside
  the west, east and south walls, in both engines.
- **Sun:** 30 deg elevation, heading 25 deg toward the door, through the west windows. Haze 0.006 -> 0.003.
- **Floor:** long 14 cm walnut boards on a 4 m tile, four UV-offset floor variants `SM_AK_Floor_Plank_2x2_A-D` in a
  2 x 2 checker (replaces the single 2 m piece; no neighbouring pieces repeat).
- **Cases:** decks oxblood cloth `#4A1715` (user decision: dark mood, near-black items still separate by hue); the tall
  cases' backdrop is the golden backlit panel (the oxblood full-height panel read as a door). Glass: thin low-reflection
  glass (0.3 x Fresnel) in Blender, Edge Opacity 0.45 -> 0.16 in Unreal; frames thinner (8 mm) in new `M_AK_Bronze`.
- **Niches / rack backs:** `M_AK_BackBoard` is now a warm golden backlit panel (emissive 0.45).
- **Cameras:** C1 just inside the door at +2.65, 18 mm (the reference's elevated entry view); C10 pulled back to frame the
  painting over the hero case. Entry lanterns moved to flank the mat (X 2.9 / 5.1, Y 1.15).
- **Grade:** exposure golden +0.8 -> +0.2, gallery +0.5; case lights 16 -> 40 W (Unreal `POWER_W` matched).
- **Unreal scripts:** material table now read from layout.json `materials`; new `M_AK_EmissiveTex_Master`; mesh and texture
  counts come from the exports on disk; the import deletes our own stale meshes; backdrop cast shadow off.
- Result: 39 pieces, QA 0 hard fails, 39 FBX, 19 textures. Renders: `renders/look2/` and `renders/look2/compare/`.
- **Still different from the reference:** it is empty (items, vases, banners, crests out of scope), and the reference's
  entry view stands further back behind a wide open front; our 150 x 200 door keeps the camera just inside.
- **Unreal rerun (02:35-02:44):**
  - The whole pipeline passes: import 39 meshes and 19 textures; materials 6 masters and 19 instances; level with 200
    meshes (bounds gate max error 0.0003 cm) and 59 local lights. The fresh-process verify passes all 5 gates.
  - Fix: a reimport kept the OLD slot names (Brass on the glass frames). `ak_import.py` now deletes a changed mesh and
    imports it fresh.
  - Unreal-only tuning in `ak_common.py`:
    - exposure follows the Blender change: `EXPOSURE_BIAS` -3.34 -> -3.94;
    - case lights x0.6;
    - a felt colour override `#3A1B19` in `ak_materials.UE_OVERRIDES`, because Unreal's tonemapper kept the oxblood
      orange-red where AgX rolls it off.
  - Stills are in `unreal/captures/`.

## 2026-09-27: Building stage (12 x 16 m room, big entrance, the user's emblem, reference-2 dressing)

Workflow building stage, resumed after a computer restart. The interrupted agent's edits were the starting point (textures,
build script for the 12 x 16 m room, render and walk scripts); this pass verified them, iterated five review rounds
(`renders/stage_building/r1`-`r5`) against `reference/armory3_reference2.png`, and finished the notes, drawing, plan,
exports and final renders. Display cases stay EMPTY: no items, stands, mannequins or placeholders.

**The emblem is the USER'S OWN ORIGINAL DESIGN** (user decision 2026-09-27), recreated from the plinth-front medallion
and the banner crests of their LOOK reference: gold ring 0.87-1.0 R, five separate egg petals 0.17-0.74 R (one pointing
up), a small heart-shaped centre (`make_armory_textures.emblem_field`). Textures: `T_AK_Emblem` (2048 mask),
`T_AK_Emblem_N` (relief), `T_AK_Emblem_BC/ORM` (gold on lacquer), and in gold on `T_AK_Banner_BC`.

### What was built / changed
- **Room** 12.0 x 16.0 m, same heights. Pieces extended by repetition; new pieces only where needed
  (`SM_AK_Ceiling_Beam_4`, `SM_AK_Entrance_6`, `SM_AK_Threshold_4`, `SM_AK_DoorLeaf`, `SM_AK_EntryStep_4`).
  52 pieces, 355 instances, 90 lights (sun + 89), QA 0 hard fails, 52 FBX exported. Largest piece 1076 tris
  (`SM_AK_RearAlcove`). Removed, with their stale FBX deleted: `Ceiling_Beam_8`, `CornerRack`, `Threshold_2`,
  `WallLower_Door_2`, `Case_Hero_Glass`.
- **Entrance** 4.0 x 3.0 m clear, centred (X 4-8): heavy 30 x 54 cm posts with iron straps, 40 cm lintel, lit ranma,
  8 cm threshold beam, sliding lattice leaves parked open on the inner face, woven runner, two floor lanterns
  flanking it, a 7 cm step beam at Y 2.56.
- **Layout** (ARMORY_PLAN section 3, `ARMORY_LAYOUT.txt/.svg`): centre row 1/2/3 at Y 3.70 / 7.60 / 11.30; side
  cases at X 1.75 / 10.25 (aisles 2.8 m); **three EMPTY growth slots G1-G3** use the extra length.
- **r2, case proportions fitted to reference 2** through the fitted C1 camera: case 1 (L) 1.8 x 1.3, plinth 0.50,
  glass 0.95 (was 2.0 x 1.4, 0.75 + 0.45); case 3 (LN) 1.6 x 1.0, 0.45 + 0.75; case 2 (M) 1.8 wide. The tall cases lost
  their backlit backdrop (it read as a bright door; the reference tall case is clear glass on all sides).
- **r2, hero**: reference 2 shows a low two-tier black lacquer TABLE (no glass) with the emblem on its front, so
  `SM_AK_Case_Hero_Plinth` is now that table (2.4 x 0.9, top +0.52 on the platform) and the hero glass is gone.
- **r2, painting** 2.4 x 2.3 m (was 1.8 tall; the reference panel is nearly square), Z 1.5-3.8; its header beam
  moved up to 3.95-4.35. Windows 150 x 120 (head +3.85, was +3.65). Banners moved to X 1.65 / 10.35, Y 15.55.
- **r3, sun** 22 deg up, heading 20 deg (was 32 / 25): the lattice patches now stream from the west windows across
  the centre-right floor, as in the reference. The three south bays of the west wall (Y 0-6) got a closed, lit shoji
  pane (`SM_AK_Window_ShojiPane`, `M_AK_ShojiLit`): at this sun they threw patches onto the entry mat and lanterns, which
  the reference keeps in shade. None of those three windows is in the C1 frame.
- **r3, plum sprays** redrawn from a zoom of the reference vases: an ikebana bundle of near-straight stems in a narrow V,
  red blossoms along the upper two thirds, two white stems leaning out (was a dense bushy canopy). Sill vases 0.30 -> 0.40 m.
- **r4**: lantern paper hotter and yellower (emit 1.6 -> 3.2, #FFB260; albedo held at 0.80); runner darker (#6F5F45);
  rear-alcove lattice denser and heavier (32 x 12 bars of 26 mm) under a dimmer gold glow (1.1); heavy 30 cm posts at
  the platform front behind the pedestal lanterns (`SM_AK_Post_Heavy_480`, replaces the thin LED posts there);
  golden-preset case lights 0.85 -> 0.6.
- **r5**: platform lanterns moved to (4.0 / 8.0, 15.15): at (4.35 / 7.65, 13.85) they sealed the platform off (walk
  check: the gap to the hero table was 0.36 m, under the 0.70 m capsule). Ceiling lattice panels moved over the platform
  (X 4-8, Y 14-16). layout.json now carries each instance's world bbox and the case dimensions; `armory_layout.py`
  draws from it (the 8 x 12 table is kept as `armory_layout_v2_8x12.py`).

### Reference inventory (R1-R10)
- [x] R1 entry: dark posts and lintel, threshold and step beams, woven runner, two square paper floor lanterns.
  NOT in the C1 frame: the reference door posts at the frame edges (see open issues).
- [x] R2 walnut planks along the axis, satin; lattice sun patches from the left windows across the floor.
- [x] R3 lattice windows on both long walls, deep sill ledge, black vases with plum sprays (4 per wall), tea caddies,
  ranma band above, posts between bays.
- [x] R4 continuous lit niche band (golden backlit panels, black lacquer counter, brass rails), empty.
- [x] R5 thin-framed clear vitrines, black lacquer plinths with gold top line, louvred bands, the emblem medallion front
  and back, LED under-glow.
- [x] R6 platform (+0.60) with 4 LED-nosed risers, hero table with emblem, painting with glowing border, plum vases
  flanking it, lanterns on pedestals and on the platform, rear alcoves (golden panel, EMPTY upright rack, tansu with
  emblem, ornamental lattice above). The emblem on the platform front centre is NOT built (the platform front is
  cabinet doors).
- [x] R7 two tall black banners with the gold crest and small lower motifs, grazed by narrow spots.
- [x] R8 dark coffered ceiling, LED-edged 4 m beams, round downlights, two ornamental lattice panels.
- [x] R9 tall dark posts along the walls and at the platform front; LED edge lines on the painting-bay posts.
- [~] R10 golden-hour grade: see the measured gap below.

### Cameras (layout.json)
- C1_EntryReveal (6.0, -0.65, +2.90) looking at (6.0, 6.53, 0), 24 mm: a least-squares fit of camera Y, Z, pitch
  and lens to 14 reference landmarks (case fronts, lanterns, painting) with Z capped at 2.90 (under the 3.0 m lintel).
  RMS 31.9 px on 1448 x 1086 (38.8 px for the best fit before the case refit; a lens-shift variant gained only 3 px).
  The reference door posts at the frame edges cannot be fitted with this camera: posts beside a camera in a 3 m
  opening fall outside a pitched 24 mm frame (checked numerically for posts at X 2.9-3.55, Y 0.3-2.8).
- C2, C3, C5, C10, CW, CX re-aimed for the new room. CG_Garden does not exist yet (exterior stage); not rendered.

### Walk check
`walk_check.py`: 11 routes clear (entrance, entry step, both aisles, both wall walks, both centre gaps, steps to the
hero table, platform to each rear alcove); CONTROL blocked at (6.0, 2.75) by case 1 glass. passed = True.

### Measured C1 vs reference (1448 x 1086, display values)
| | mean | p10 | p50 | p90 | saturation | blue/red |
|---|---|---|---|---|---|---|
| reference 2 | 0.328 | 0.061 | 0.282 | 0.740 | 0.45 | 0.58 |
| C1 r1 (start) | 0.302 | 0.107 | 0.211 | 0.620 | 0.73 | 0.36 |
| C1 final | 0.313 | 0.123 | 0.234 | 0.645 | 0.70 | 0.38 |

### Renders
`renders/stage_building/`: golden 1600 x 900 at 96 samples (C1, C3, C5, C10, CW, CX), C1 gallery,
`ref_aspect/C1_EntryReveal_golden.png` (1448 x 1086) and `reference_vs_C1.png`. Rounds r1-r5 are kept for history.

### Open issues
- Grade: C1 is still more saturated (0.70 vs 0.45) and warmer (blue/red 0.38 vs 0.58), with lifted blacks (p10 0.12
  vs 0.06), than the reference. The next look pass should cool the practicals and sky and deepen the toe.
- The oxblood decks (user decision #4A1715) read pink-mauve where the case lights or the sun hit them; the reference
  decks read near black.
- The reference door posts at the C1 frame edges cannot be reproduced with the 4 x 3 m opening (see Cameras).
- `M_AK_Plum` (alpha) and `M_AK_Banner` need Masked / two-sided materials in Unreal; `M_AK_ShojiLit` is a new emissive
  instance. Unreal has NOT been re-run for this stage (import, materials, level, verify).
- The sun enters through the west windows only; the east windows get no sun.


## 2026-09-27: Exterior stage (courtyard garden, the hall's outside, layered scenery)

Workflow exterior stage, started fresh after the computer restart (the building stage had finished at 07:00; nothing of
this stage existed yet). The room interior is untouched except where the exterior meets it (the entrance approach, the
outer wall faces, the roof over the ceiling, what the windows and the door look out on). The display cases stay EMPTY.

### What was built
- **New scripts:** `Scripts/armory/build_armory_exterior.py` (all `SM_AKX_` pieces and their placement; imported by
  `build_armory_kit.py`, which calls `EXT.setup(globals())` so the module uses the kit's `Piece` / `lathe` / `card`), and
  `Scripts/armory/make_exterior_textures.py` (14 `T_AKX_` sets, numpy, procedural, original).
- **Blender collections** `KitExterior` / `AssemblyExterior`; same QA, pipeline export and layout.json as the room.
  Result: **90 pieces (50 room + 40 exterior), QA 0 hard fails, 90 FBX exported**, 488 instances (137 exterior).
- **Removed:** `SM_AK_Ext_Ground`, `SM_AK_Ext_Backdrop` (stale FBX deleted), materials `M_AK_Backdrop`, `M_AK_Ground`.
- **Courtyard** X -4..16, Y -13..-0.3 (20 x 12.7 m), ground Z 0: raked gravel (`T_AKX_Gravel`: 8 mm Worley chips over
  ridges 6.25 cm apart running across the axis, tile 2 m), concentric raked rings (`SM_AKX_RakeRing_A/B`, an annulus whose
  V runs outward so the same gravel ridges follow the mound outline), two moss mounds, three rocks (one used twice), ten
  clipped shrubs, a Kasuga-style stone lantern (`SM_AKX_StoneLantern`, 2.0 m, dim paper core, upturned roof corners), a
  stone basin with water surface and bamboo spout (`SM_AKX_Tsukubai`), a cut-granite landing at the entrance, an
  ishidatami strip, 11 stepping stones to the gate.
- **Trees** (alpha-masked cards, collision on the trunk only; tris): black pines `Pine_A` 1097 (cloud-pruned pads on
  near-horizontal branches) and `Pine_B` 740; maples `MapleGreen_A` 1663, `MapleRed_A` 1258, `MapleRed_B` 598. Leaf
  materials: two-sided, a little translucency, and an edge-on fade (Blender Layer Weight; Unreal |N.V| x 3) so thin cards
  do not streak. All 40 exterior pieces together: 11,560 tris.
- **Enclosure:** south wall with a roofed gate on the axis (2.38 m clear), side walls to Y +3, plaster on a stone base,
  timber cap, tiled coping (top +2.05), piers.
- **The hall outside:** hipped tile roof (`SM_AKX_Roof`): eaves 1.0 m, 26 deg, eave top +4.70, ridge +8.26; its
  underside clears the wall top (+5.00) at the outer face. Computed: the eave line's shadow lands at +4.09 on the side
  walls (sun 22 deg up, heading 20 deg: 0.430 m drop per metre), above the window heads (+3.85), so the sun still enters
  the west windows as before. Stone foundation band (+0.46), timber posts every 2 m, base rail, rails and jambs round
  each window, plaster band under the eaves (`SM_AKX_Facade_*`).
- **Scenery** (all emissive, **cast no shadow** in both engines via the layout.json instance flag `cast_shadow: false`):
  tree-line cards 24 x 14 m on X -10, X 22 and Y 26, 48 x 20 m on X -30, X 42 and Y 46, plus two far cards SW and SE on
  Y -48 (the gate opens south onto the meadow, hills and mountains); a 360 deg hills ring (r 170 m, 10-34 m) and a
  mountains ring (r 720 m, 70-250 m) whose painted light follows the sun (lit warm opposite it, backlit hazy toward it).
  The windows now show near trees, gaps to the far layer, and the sky: depth and parallax instead of one flat card.
- **Sky (review renders):** `render_armory.py` world = sky only (the old procedural tree line is behind
  `--legacy-exterior`): orange horizon, gold, cream, blue zenith, sun glow, faint cloud streaks; camera sky strength 4.5.
  Probe: world Generated = the unit view direction (z 0.854 at 60 deg up). Camera clip end 3000 m.
- **PlayerStart** moved to the courtyard path at (6.0, -10.4), facing the entrance (layout.json `player_start`,
  rot_z 90). **CG_Garden** camera (2.9, -12.3, +1.8) looking at (6.9, -1.0, 2.3), 20 mm, with its own review exposure
  (layout.json camera `exposure_ev`: golden -2.8, gallery -1.0; the room presets are +0.8).
- **Grade:** golden exposure +0.6 -> +0.8. The emissive south backdrop that used to light the entry through the door is
  gone. Measured on C1 1600 x 900 (one stats script for all rows, display values): building stage mean 0.299 / p10 0.119
  / p50 0.217 / p90 0.648; at +0.6 now 0.273 / 0.086 / 0.190 / 0.635; at +0.8 (final) 0.294 / 0.102 / 0.212 / 0.661.
  Reference 2: 0.323 / 0.060 / 0.282 / 0.711. C1 at 1448 x 1086: 0.274 / 0.088 / 0.200 / 0.614 (building stage 0.295 /
  0.110 / 0.216 / 0.626): the taller frame holds more of the entry floor, which lost the backdrop fill.
- **Layout drawing:** `armory_layout.py` also writes `ARMORY_SITE.txt` / `.svg` (the courtyard from layout.json);
  exterior cameras are drawn there, not on the room plan. ARMORY_PLAN.md section 3.4 added, 3.3 walk routes updated.

### Walk check
`walk_check.py` reads both assembly collections (569 hulls): 15 routes clear, including
`courtyard_start_along_path_through_entrance` (6.0, -10.4) -> stones -> ishidatami -> landing -> threshold -> mat,
`outside_through_gate_to_start`, round the basin and round the lantern; **both controls blocked** (case 1 glass at
(6.0, 2.75); the stone lantern at (7.58, -7.3)). passed = True.

### Unreal (ArmoryLab; no editor had it open; one commandlet at a time)
- Script changes: meshes `SM_AK*.fbx`; textures = BC / N / ORM maps only (`ak_common.engine_textures`; the generator
  mask `T_AK_Emblem` has no import intent and made the first import fail); `tex_stem` for `AKX_` sets; new masters
  `M_AK_TexturedMasked_Master` (two-sided, masked, edge fade) and `M_AK_EmissiveTexMasked_Master`; `Base Colour Scale`
  on the emissive-picture masters (0 = unlit scenery); `M_AK_Plum` / `M_AK_Banner` now use the masked two-sided master
  (closes that open issue); PlayerStart from layout.json in ak_level / ak_verify / ak_character; per-instance
  `cast_shadow`; the bounds gate's door piece is `SM_AK_Entrance_6`; the banner light role was missing from `POWER_W`
  and the light folders (the building stage never ran Unreal).
- `blender_bounds.py` now takes the rotated LOCAL box corners (Unreal's actor bounds are the local box rotated; the
  first level run failed at 77 cm on the stepping stones, rocks and mounds, which are yawed off 90 deg).
- Run 07:42-07:43: import 90 meshes / 62 textures, materials 8 masters / 43 instances / 90 meshes, level 488 meshes
  (bounds gate max 0.0041 cm) and 89 local lights, verify all 5 gates, character (PlayerStart at (600, 1040, 95) cm,
  yaw -90, faces the entrance), walk: all passed. The capture step was NOT run: the Unreal look of the garden is unverified.

### Renders (`renders/stage_exterior/`)
Golden 1600 x 900 at 96 samples: C1, C3, C5, C10, CW, CX, CG_Garden; C1 gallery; `ref_aspect/C1_EntryReveal_golden.png`
(1448 x 1086); `reference_vs_C1.png`. Test rounds `r1`-`r6` kept for history.

### Open issues
- The exterior tree lines are flat emissive cards; from the courtyard the far layer's conifers read a little pale and
  flat, and every tree line looks the same from both sides (its light is painted in).
- Bright red maple leaves in direct sun tone-map toward pink in AgX (CG_Garden).
- The case glass now reflects the sunlit courtyard through the entrance (C5 shows the garden in the tall case glass):
  physically right, but brighter than the old green backdrop reflection.
- C1 mid-tones stay under the reference (p50 0.212 vs 0.282); the saturation and warmth gaps from the building stage remain.
- No world-boundary blocking: the player can walk out of the gate onto the 400 x 400 m field.
- Unreal: not captured; the masked foliage, the emissive scenery strengths (emit x K) and SkyAtmosphere against the
  Blender sky are untested visually and may need Unreal-only tweaks.

## 2026-09-27: Fix round f1 (measurer r1 + blind judge 6.5/10)

Workflow fix round, started after a computer restart (nothing of this round existed yet; the exterior stage had finished
at 07:44). Headless Blender only; the ArmoryKit lock was taken over from the finished exterior stage. Display cases stay
EMPTY (no items, stands, mannequins or placeholders). **The emblem is the USER'S OWN ORIGINAL DESIGN** (unchanged, from
their LOOK reference); it is now also on the top riser at the platform front centre.

### Measurer fixes (all seven)
- **Platform-bay niches** are a new 1.90 m piece `SM_AK_WallPanel_Lit_190` at +0.60-+2.50 (bbox top +2.501; the sill
  ledge underside is +2.549), so the ledge, the Y 14.25-15.75 windows and sill vase __314 are free. Plan 3.1 / 3.2 state it.
- **Platform lanterns vs big vases**: lanterns (3.55 / 8.45, 15.10), vases X 4.20 / 7.80. Bboxes: lantern X 3.288-3.812,
  vase 3.881-4.519 (7 cm apart); a BVH clash check finds no crossing.
- **Sill sprays**: cards at +/-25 deg off the wall line (was 15 / 95). Computed reach toward the wall 0.31 x sin 25 =
  0.131 m from the vase axis at 0.17 m: the cards stop 3.9 cm in front of the wall face (vase body 1.8 cm). No clash
  with `WallUpper_Window_2`.
- **Platform front emblem (R6)**: `SM_AK_EmblemDisc_12`, the user's emblem as an 11.6 cm gold medallion on the top
  riser at (6.0, 13.43), +0.45-+0.566 (the whole visible riser between the top tread and the platform lip). The hero
  table's base emblem also grew 17 -> 20 cm (reference 2's is about 24 cm).
- **Pine_B**: turned 90 deg and moved to (9.5, -10.16). Canopy bbox Y -12.55..-8.65: 9 cm inside the courtyard wall face
  (-12.64) and 8 cm short of the red maple's crown (-8.57); only its roots touch the gravel.
- **ARMORY_PLAN 3.3**: the stale S1-S3 fragment is deleted.
- **Tall-case plinths**: 0.20 -> 0.50 m (glass 2.00 -> 1.70, top still +2.20), so they carry the louvred bands and a
  25 cm emblem front and back like the other plinths.

### Judge blockers and deltas (room, casework, dressing, light; nothing that asked for items was done)
- **C1 camera (new fit)**: reference 2's verticals are vertical, so its establishing view is a LEVEL shift-lens camera.
  Least-squares fit of Y, Z, lens and shift to 15 landmarks (step beam ends, both entry lanterns, case 1 plinth and glass,
  painting corners): (6.0, -1.51, +3.42), 24.5 mm, shift_y -0.303: RMS 16.3 px on 1448 x 1086, against 39.0 px for the
  old pitched camera on the same landmarks. layout.json cameras carry an optional `shift_y`; render_armory.py applies it.
  It stands over the landing 1.5 m outside the entrance, so the **entrance is now 3.65 m tall** (computed: the lintel must
  be >= +3.61 to clear the frame top). Lintel +3.65-+4.05, ranma +4.10-+4.62, door leaves 3.65 m, the exterior facade
  rail moved onto the lintel top (`SM_AKX_Facade_Entrance_6`; it would have hung 20 cm into the opening).
- **Door posts at the frame edges (R1, delta 10)**: two heavy 30 cm posts (`SM_AK_Post_Heavy_480`, full height) at
  (4.0, 1.02) / (8.0, 1.02), a vestibule 1 m inside the entrance on the jamb lines. Through the fitted camera their inner
  faces project to x -41..45 px and 1403..1489 px of 1448, full height, as reference 2's posts. The entry step beam is
  30 cm deep x 9 cm with black lacquer faces.
- **Decks (blocker 1)**: every case deck and the hero table top is black lacquer `M_AK_DeckLacquer` (#0E0C0B, rough
  0.25) with the thin brass edge. **This supersedes the look2 user decision #4A1715 (oxblood)**; it is one material
  entry if the user wants the oxblood back. No cream boards were added (optional in the judge list).
- **Niches (blocker 2)**: a dark recess, not a lightbox: `M_AK_BackBoard` #6B5238, no emission; no grille band, no LED
  edge lines, the two long brass rails became four short pegs; a small lens under the head 20 cm off the back and a
  review spot there pointing straight down (120 deg, 40 W): the light grazes the board, hot under the head and falling
  off (E ~ d / r^3: 17x dimmer 0.5 m down than 0.1 m down). Rear alcoves: the LED strip across the lip is gone (two
  lenses), same dark board; the gold lattice glow above them 1.1 -> 0.8.
- **Grade (blocker 3, delta 4)**: AgX Very High Contrast (was Medium High) at +2.4 EV golden and gallery (the niches no
  longer glow and the decks are black); bloom threshold 1.2 -> 2.0, strength 0.35 -> 0.2; the sky fill cooler
  (0.90, 0.86, 0.80); case lights 5000 -> 5500 K, downlights 4600 -> 5000 K, niche spots 3600 K; golden downlights
  x1.3, case x0.8. M_AK_LED 30 -> 12 (the step nosings mirrored as stacks of hot lines in every case glass); the glass
  reflection 0.3 -> 0.18 x Fresnel.
- **Sun (blocker 4, delta 3)**: 30 deg up, heading 40 deg, 3500 K, 0.5 deg disc. Computed from the window (sill +2.65,
  head +4.10): each patch lands 4.6-7.1 m along the ray, X 3.5-5.5 (the left aisle and the centre row's west edge),
  3-4.6 m nearer the entrance than its window, 2.5 m long: diagonal beams from the LEFT windows toward the lower right in
  C1. All west windows are open again (`SM_AK_Window_ShojiPane` and `M_AK_ShojiLit` removed, stale FBX deleted).
  Physically one sun through +2.65-+4.10 windows cannot light the whole floor width as reference 2 does.
- **Windows (delta 5)**: 150 x 145 (head +3.85 -> +4.10; the exterior facade frames follow); the near tree line is warmer
  (`make_exterior_textures.treeline`: 30-40 % toward #D6B46A) and brighter (emit 7 -> 10).
- **Banners (delta 6)**: the fitted camera puts reference 2's banners (x 355-392 / 1056-1093, y 25-172 px, 0.55 m wide)
  at X 0.78 / 11.22, Y 13.13, cloth +2.41-+4.60. Built there, hung from the ceiling (cords 30 -> 15 cm), facing the
  entrance, with a thin gold edge line on the cloth (the crest alone read as a wall medallion) and a 60 W grazing spot.
- **Ceiling (delta 7)**: `SM_AK_Ceiling_Rib_2` ribs along the axis on X 2/4/6/8/10 (plain timber: with LED lines the
  ceiling read as an office grid), dark timber coffer boards (the plaster-shade boards read olive), a round downlight can
  in every coffer (the review spot moved under its lens, CEIL - 0.145).
- **Lanterns (delta 8)**: heavy corner posts with finials, base frame, projecting open top frame with cross bars, one low
  rail, amber paper (#5E4F3C albedo, emission 0.4 x #FFA838; was 3.2 x #FFB260 on #CCAE80).
- **Floor (delta 9)**: `T_AK_Plank` long boards with one butt joint per 4 m, the blotchy low-frequency tint much weaker,
  base #322823 (darker, less saturated).
- **Sill vases (delta 11)**: 0.40 -> 0.46 m, spray 0.62 m wide, denser plum texture (13 stems, larger blossoms; the big
  vases use it too), and a narrow 3400 K spot on each (role `sill`, 14 W).
- **Under-glow (delta 12)**: the plinth strips are `M_AK_LEDGlow` (emission 4, was the 30-strength LED), the UnderGlow
  area lights 4 -> 8 W per metre of perimeter at 3300 K.
- **Painting (delta 13)**: a fuller ink pine (seven long branches almost to the edges, overlapping needle clouds along
  each, clouds over the branch ends), gold frame.
- North-wall upper panels are the dark `M_AK_ScreenPanel` (reference 2's upper rear wall is dark); the north-wall corner
  niches are gone; the rear alcoves moved outboard to X 1.2-3.0 / 9.0-10.8 (the fitted camera measures reference 2's
  rack alcoves at X ~1.0-2.3).

### Build
92 pieces (added `WallPanel_Lit_190`, `Ceiling_Rib_2`, `EmblemDisc_12`; removed `Window_ShojiPane`), 523 instances,
96 lights; QA 0 hard fails; 92 FBX exported, no stale FBX. layout.json `materials` now lists only materials some piece
uses (40). Textures: plank, painting, plum, banner, runner changed (`make_armory_textures.py`, full run), near tree line
(`make_exterior_textures.py treeline`). Drawing and plan section 3 regenerated / updated.

### Walk check
`walk_check.py`, 604 hulls: 16 routes clear, including the new `entry_mat_between_the_vestibule_posts` and the aisle
routes that pass between each vestibule post and its floor lantern; both controls blocked. passed = True.

### Measured C1 (1448 x 1086, display values, the same stats as earlier stages)
| | mean | p10 | p50 | p90 | saturation | blue/red |
|---|---|---|---|---|---|---|
| reference 2 | 0.323 | 0.060 | 0.282 | 0.711 | 0.45 | 0.58 |
| exterior stage | 0.274 | 0.088 | 0.200 | 0.614 | about 0.70 | about 0.38 |
| f1 final | 0.272 | 0.052 | 0.191 | 0.681 | 0.62 | 0.49 |

### Renders (`renders/stage_f1/`)
Golden 1600 x 900 at 96 samples: C1, C3, C5, C10, CW, CX, CG_Garden; C1 gallery; `ref_aspect/C1_EntryReveal_golden.png`
(1448 x 1086); `reference_vs_C1.png` (side_by_side.py). Test rounds are in the session scratchpad only.

### Open issues
- Mid-tones still under the reference (p50 0.19 vs 0.28), still warmer and more saturated (0.62 vs 0.45). The reference's
  mids come largely from its lit items, bright near-camera niches and a floor lit across its whole width.
- The 12 m room is wider than reference 2's: its front side cases sit at about X 2.7-3.5 through the fitted camera, ours
  at X 1.2-2.3 (user decision: 2.8 m aisles), so the near side walls and side cases fall outside the C1 frame.
- Sun patches cover X 3.5-5.5 only (one sun, windows +2.65-+4.10); reference 2 lights the whole floor width.
- The deck colour change overrides the user's oxblood decision (#4A1715): a user call.
- C1 now uses a lens shift and stands outside the building at +3.42 m: an Unreal CineCamera needs a filmback sensor
  offset (or a crop) to match; not done.
- Unreal NOT re-run for f1: new materials `M_AK_DeckLacquer`, `M_AK_LEDGlow`; `M_AK_BackBoard` / `M_AK_Paper` params
  changed (and `ak_materials.py` has its own BackBoard / Felt table entries); `UE_OVERRIDES` still holds the M_AK_Felt
  override (Felt is no longer in layout.json); M_AK_ShojiLit and M_AK_PlasterMid dropped out; new meshes (rib, emblem
  disc, 1.90 m niche), the taller entrance and windows.
- The tall case glass still mirrors the sunlit courtyard in C5 (reduced, 0.18 x Fresnel).
- The lanterns' paper is a flat emission (no hot centre); the reference's glow falls off from the middle.
- The brighter, warmer near tree line makes CG_Garden's background trees paler.

## 2026-09-27: Fix round f2 (blind judge 6.8/10; no measurer fixes)

Workflow fix round, started fresh after a computer restart (f1 had finished; nothing of f2 existed). Headless Blender
only; the ArmoryKit lock was claimed for this round. Display cases stay EMPTY (no items, stands, mannequins or
placeholders). **The emblem is the USER'S OWN ORIGINAL DESIGN** (unchanged, from their LOOK reference). Test renders
live in the session scratchpad only; finals in `renders/stage_f2/`.

### Judge blockers
- **Sun (blocker 1, delta 1).** Reference 2, zoomed on both halves of its floor: EVERY lattice patch streams from the
  LEFT (west) windows toward the lower right, on the left AND the right half of the floor. None comes from the right
  windows. One sun through the +2.65 to +4.10 windows lights a band about 3 m wide. So two directional lights now share
  the heading. The analytic study (scratch `sunpatch.py`: a floor point is lit if its ray back to the sun passes the
  opening at both the inner and the outer wall face) gives:
  - the sun, 18 deg up, heading 35 deg, 2800 K: patches X 6.70-10.00, 16.5 % of the hall floor (X 1.2-10.8,
    Y 2.6-12.7), about 4.5 m long along the ray. The eave soffit edge (+4.52, 1.0 m out) shades the outer wall face
    down to +4.12, 2.3 cm above the clear window head (+4.10).
  - `Sun_WindowFill`, 30 deg up, heading 37 deg, 0.85 x: patches X 3.70-5.35 (11.1 %). It is interior-only: layout.json
    `"link": "interior"`; Blender uses light and shadow linking to the Assembly collection; Unreal needs a second
    directional light on its own lighting channel. It does not scatter in the haze.
  - f1's sun (30/40) lit 10.1 %, X 3.55-5.10. In C1 at 1448 x 1086, the floor band x 150-1300, y 430-880 has 15.8 %
    of its pixels above 0.6. f1 had 10.4 % and reference 2 has 15.8 %. Patches climb onto the case decks (C3).
  - Sun 3500 -> 2800 K and 100 -> 60 W/m2. The bigger patches had read salmon-white: measured (232, 193, 176) against
    reference 2's peach-gold (249, 199, 153). Final: (207, 158, 131).
- **Floor (blocker 2, delta 3).** The "brick pattern" was a bug. `pnoise`'s `stretch_u` multiplies the U frequency, so
  0.012 made the grain run ACROSS the boards. The grain now runs along them (`stretch_u` 80 / 50 / 100). Other changes:
  - 20 boards per 4 m = 20 cm wide (were 14.3 cm), 4 m long with one staggered butt joint
  - board tint 0.045 -> 0.08
  - base #352A29 (a dark walnut; reference 2's shaded floor measures mauve-brown, saturation 0.14-0.18)
  - roughness 0.22 -> 0.16

### Judge deltas (room, casework, dressing, light; nothing that asked for items was done)
- **Grade (2):** golden stays AgX Very High Contrast at +2.4 EV. Haze 0.0015 -> 0.0008. The fill sun does not scatter
  (its shafts veiled the west aisle). The warmer, weaker sun keeps the patches golden, below AgX's white shoulder.
- **Windows (4):** 9 muntins and 3 rails (panes 14.2 x 34.3 cm; were 11 muntins and 1 rail). The near tree line is
  veiled toward peach-gold (#E2A866 at 0.40-0.52, was #D6B46A at 0.30-0.40). Measured window glow in C1 (237-243,
  185-189, 162-166) against reference 2's (226-246, 195-233, 158-210).
- **Painting (5):** warm beige paper #A88C66 (was #CCBE9F) and near-black ink #15120F. The needle clouds are 15 % larger
  and fully opaque. The wash is 35 -> 6 W. The hero table's downlight has a 50 deg spread (layout.json `spread_deg`;
  Unreal: barn doors), because its wide lobe was washing the paper white. C1 paper: 0.93 -> 0.79 display value.
  Reference 2's is 0.48-0.56.
- **Ceiling (6):**
  - a 12 mm warm LED line round the inner lower edge of every coffer ring
  - larger downlight cans (18 cm trim, 14 cm body, 16 cm deep), with the spot under the lens at 40 deg / blend 0.3,
    so pools read on the floor (gallery C1)
  - lattice panels also on the centre line X 4-8 at Y 8-10 and 12-14 (six in all; `LATTICE_COFFERS`)
- **Sill vases (7):** one per bay, 8 per wall (were 4). `T_AK_Plum` is now a square 2048 card with a wide, round bush:
  22 stems fanning +/-40 deg, 2-4 blossoming twigs each, and three white stems. The sill spray is three 0.88 m cards at
  0 / +/-16 deg (0.72 m over the 0.46 m vase: 1.6x the height, 1.9x the width).
  - Computed wall clearance: 0.44 x sin 16 = 0.121 m from the vase axis at 0.17 m. The cards stop 4.9 cm off the wall
    and 2.4 cm off the window casing; at 20 deg they would have touched the casing by 0.55 cm.
  - The big vases carry two 0.90 m cards at 60 / 120 deg, clear of the platform lanterns (card X 3.975-4.425 against
    the lantern's 3.288-3.812).
  - The caddies moved to (0.20, 5.40), (11.80, 8.60), (0.20, 13.40) and (11.80, 0.60), 11 cm clear of the sprays.
- **Rear alcoves (8):** new `M_AK_AlcoveLit` back panel: cream #A88C62 with a low emission of 0.18 x #FFB45C. Two warm
  spots (role `alcove`, 12 W, 75 deg, 3200 K) sit at the lenses under the head, aimed low on the panel. The rack wash
  is 20 W.
- **Entry (9):**
  - The step beam is a thin matte timber sill: 18 cm deep x 6 cm (was 30 x 9 cm with black lacquer).
  - New `SM_AK_Post_Jamb_480`: 45 x 30 cm, full height, black iron straps with studs. It is placed at (3.995 / 8.005,
    1.02); inner faces X 4.22 / 7.78. Through C1 the inner face spans x 0-70 px (was 0-44 px).
  - The lantern cap is the plain open frame (no cross bars, no finials; the posts stop at +0.645).
  - The panes use a new glow picture `T_AK_LanternPaper` on a unique UV per pane: a hot cream core just above the
    middle, falling to a deep amber rim. The material is `M_AK_LanternPaper`, unlit emit_image, 0.40. A flat emission
    tone-maps to one cream tone at +2.4 EV.
- **Glass (10):** the reflection factor went 0.18 -> 0.02 x Fresnel (museum anti-reflective glass: 0.1 % face-on, up to
  2 % at grazing). A k = 0 / 0.04 test on C5 proved the image in the tall glass is a reflection of the sunlit courtyard
  through the entrance. At 0.02 it is fainter but still visible.
- **Wall bays (11):** `SM_AK_WallPanel_Lit` now stands on the floor: a black lacquer dado cabinet (door panel, brass
  split line, toe kick) up to +0.85, a projecting 29.4 cm lacquer counter with a brass nosing (+0.85-+0.90), then the
  cream back board (#A68D69, not emissive) up to +2.35 under the head. The platform bay has a 0.40 m dado (counter
  +1.00). The pegs stay at +1.35 / +1.70. The panel spots are 40 -> 22 W and 3600 -> 3100 K (the cream clipped to white).
- **Exterior:** `make_exterior_textures.SUN_AZ` still held 22 / 20 from the building stage. It now follows the kit sun
  (18 / 35), and the hills and mountain rings were regenerated.

### Build
- 93 pieces (added `SM_AK_Post_Jamb_480`), 531 instances, 105 lights (2 suns). QA 0 hard fails; 93 FBX exported, none
  stale, no export warnings.
- New materials `M_AK_AlcoveLit` and `M_AK_LanternPaper` (texture `T_AK_LanternPaper` BC/N/ORM, 512).
  `M_AK_Paper` (#3E3328, 0.5 x #FFB24A) now only serves the stone lantern.
- Textures regenerated: all of `make_armory_textures.py`; `treeline`, `hills` and `mountains` from
  `make_exterior_textures.py`.
- A BVH surface check of the changed pieces finds only contacts: pieces standing on the floor or ledge, and the wall bays
  against their posts and wall base. The dado embeds the wall's 1.2 cm base board.

### Walk check
`walk_check.py`: 17 routes clear. The new `entry_mat_between_the_vestibule_posts_east` joins the west route, moved to
X 4.62 (the jamb's inner face is 4.22, and the capsule is r 0.35). Both controls are blocked. passed = True.

### Measured C1, 1448 x 1086 (display values, same stats as earlier stages)
| | mean | p10 | p50 | p90 | saturation | blue/red |
|---|---|---|---|---|---|---|
| reference 2 | 0.323 | 0.060 | 0.282 | 0.711 | 0.45 | 0.58 |
| f1 final | 0.272 | 0.052 | 0.191 | 0.681 | 0.62 | 0.49 |
| f2 final | 0.290 | 0.058 | 0.197 | 0.685 | 0.64 | 0.47 |

### Renders (`renders/stage_f2/`)
- golden 1600 x 900 at 96 samples: C1, C3, C5, C10, CW, CX and CG_Garden
- C1 gallery
- `ref_aspect/C1_EntryReveal_golden.png` (1448 x 1086)
- `reference_vs_C1.png` (side_by_side.py)

### Open issues
- **C1 mid-tones and colour.** The mid-tones are still under the reference (p50 0.197 vs 0.282). C1 is more saturated
  (0.64 vs 0.45) and warmer (blue/red 0.47 vs 0.58). Reference 2's shaded floor is a desaturated mauve-brown; ours is
  orange-brown under the warm glow lights.
- **Two suns.** The two-sun set-up is a deliberate cheat for reference 2's floor-wide patches. In Unreal it needs a
  second directional light restricted by lighting channel. It must not drive the SkyAtmosphere, and the interior meshes
  must be on both channels.
- **Unreal not re-run in f2** (nor in f1). Pending there:
  - the fill sun
  - new materials `M_AK_AlcoveLit` and `M_AK_LanternPaper` (an unlit emissive picture)
  - `M_AK_BackBoard` and `M_AK_Paper` parameter changes; `ak_materials.py` keeps its own table
  - the alcove spot role and the hero light's `spread_deg`
  - the new jamb post, the wall-bay and lantern meshes, and the square plum texture
  - everything listed under f1
- **Glass.** The tall case glass still faintly mirrors the sunlit courtyard in C5, even at 2 % grazing reflectance.
- **Painting.** The paper reads warmer and brighter than reference 2's (0.79 vs about 0.5).
- **Drawing.** In the ASCII plan the sill vases (`v`) overprint most wall-bay characters (`9`). They share the wall band
  at different heights, and the SVG shows both.
- **User call.** The deck colour (black lacquer against the user's oxblood #4A1715) still needs a decision.

## 2026-09-27: Unreal rebuild (ArmoryLab from the final f2 Blender build)

Workflow Unreal stage. It started fresh after a computer restart: no Unreal script had changed since 07:43 and nothing of
this stage existed. The Blender build was not touched. Display cases stay EMPTY (no items, stands, mannequins or
placeholders). **The emblem is the USER'S OWN ORIGINAL DESIGN** (unchanged). It reaches Unreal as `T_AK_Emblem_BC/N/ORM`
on `M_AK_Emblem`, and in gold on `T_AK_Banner_BC`.

Guards:
- At 17:05 no `UnrealEditor.exe` was running (Get-CimInstance). The runner now checks this itself before every Unreal
  step (see below).
- One Unreal process at a time. No unreal-mcp or Blender MCP was used, and no GUI was opened.
- The ArmoryKit lock was claimed at 17:05 and released at the end. The Blender steps (bounds, walk) only read the blend.
- No other session's process, project or lock was touched.

### Script changes (`Scripts/armory/unreal/`)
- **`run_armory_unreal.sh`**
  - `editor_guard`: before each Unreal step it asks PowerShell (Get-CimInstance Win32_Process) whether an
    `UnrealEditor.exe` has ArmoryLab on its command line. If one does, the run stops with exit 3 and writes nothing.
  - The default steps are now `project bounds import materials level verify manny character walk capture stats`.
  - The capture step now runs `ak_crop.py` afterwards. The new `stats` step runs `ak_image_stats.py`.
- **`ak_common.py`**
  - The golden-preset light table is now **read from `render_armory.py`** (ast literal_eval of POWER, PRESET_SCALE,
    SUN, FOG, SUN_ANGLE_DEG, EXPOSURE, LOOK, SKY, BLOOM). The hand-copied POWER_W had gone stale (fix1 powers, and no
    alcove or sill role).
  - `light_watts` now includes each light's `power_scale`. `sun_lux` = K x 60 W/m2 x power_scale: 6000 lux for the sun,
    5100 lux for the window fill.
  - Unreal-only tables: `UE_ROLE_SCALE`, `UE_SPEC_OFF_ROLES`, `UE_SHADOW_OFF_ROLES`, `UE_PP` and `UE_SKY` (values below).
  - `is_interior_piece`, `camera_exposure_offset`, `light_shadows`. The haze is FOG golden 0.0008/m (Unreal
    FogDensity 0.008). The sun disc is 0.5 deg.
- **`ak_materials.py`**
  - The stale fallback copy of the Blender table is gone. layout.json `materials` is required, and it drives all
    42 instances.
  - `M_AK_Felt` is out of `UE_OVERRIDES` (the felt no longer exists).
  - New `M_AK_Foliage_Master`: masked, two-sided, Two Sided Foliage shading, subsurface = BC x Translucency. It serves the
    pine pads and maples (the Blender `translucent` weight).
  - The plum sprays and banner stay on the masked two-sided `M_AK_TexturedMasked_Master`. The lantern paper and the far
    scenery use the emissive-picture masters (Base Colour Scale 0 = unlit).
  - Glass follows f2's 0.02 x Fresnel: Opacity 0.02, Edge 0.06, Specular 0.1 (was 0.05 / 0.16 / 0.35).
  - It deletes our own stale instances once every slot is re-assigned: M_AK_Backdrop, Felt, Ground, Linen, Plaster,
    PlasterMid and ShojiLit.
- **`ak_import.py`** also deletes our own stale textures. There were none; `SM_AK_Window_ShojiPane` was deleted as a
  stale mesh.
- **`ak_level.py`**
  - **Two directional lights.** `Sun_GoldenHour` drives the atmosphere, scatters in the fog and sits on channel 0.
    `Sun_WindowFill` (`link: interior`) is on **lighting channel 1 only**: no atmosphere, no fog scattering, no
    volumetric shadow.
  - Every `SM_AK_` room-kit actor is on channels 0 + 1 (394 actors); the `SM_AKX_` exterior is on 0. So the fill lights,
    and is shadowed by, the room only, as Blender's light and shadow linking to Assembly does. Lumen's scene lighting
    honours the channel mask in 5.8 (`LumenSceneDirectLighting.cpp`).
  - New roles: `alcove` and `sill` spots (folders `Lights/RearAlcoves`, `Lights/SillVases`). Panel lights are now spots.
    Each spot uses its own `blend`.
  - `spread_deg` (the hero light, 50 deg) becomes straight barn doors, L = (short side / 2) / tan(spread / 2) = 57.9 cm.
    Flared doors at half the spread did not block rays leaving past the near edge: the first capture washed the
    painting's lower half.
  - **CineCameraActors** for all 8 layout cameras: 36 x 20.25 mm filmback, the Blender lens, focus disabled.
    - C1's shift_y -0.303 becomes `SensorVerticalOffset` = shift_y x 36 = -10.908 mm. The sign is checked in
      `CameraStackTypes.cpp`: a negative offset moves the view down.
    - CG_Garden carries its own exposure: PPV bias + (-2.8 - 2.4) EV in the camera's post-process settings.
  - The PlayerStart comes from layout.json `player_start`: the courtyard at (600, 1040, 95) cm, yaw -90, facing the
    entrance.
  - The PPV takes `UE_PP`, and the SkyAtmosphere takes `UE_SKY`.
- **`ak_verify.py`**
  - Every count comes from the exports or from layout.json / materials.json. Masters come from materials.json.
  - New checks:
    - each actor's lighting channels: interior pieces on 0 + 1, exterior on 0 only
    - every `cast_shadow: false` instance (16) casts no shadow
    - per sun: lux, direction, channels, atmosphere flag and fill scattering
    - the shift-lens sensor offset
    - camera actors: CameraActor or CineCameraActor
- **`ak_capture.py`**
  - By default it captures every layout.json camera, plus `C1_EntryReveal_ref_aspect` at 1448 x 1086.
  - The FOV comes from the Blender lens.
  - A shift-lens view is captured level into a tall target of the same horizontal FOV. C1 is 1600 x 1870, rows 970-1870;
    the ref-aspect frame is 1448 x 1964, rows 878-1964. `ak_crop.py` (new, system Python) crops it afterwards, and the
    raw frames are kept in `captures/raw/`.
  - Per-camera exposure offset (the garden).
  - Sweep frames 8 -> 48 (`AK_SWEEP_FRAMES`). At 8 frames the sweep's C1 was 0.03 darker than the 96-frame final.
  - `run_capture.ps1` takes extra cvars from `AK_CVARS`.
- **`ak_image_stats.py`**
  - It compares against `renders/stage_f2` (was fix1), and C1 at the reference aspect also against reference 2.
  - It adds the blue/red ratio.
  - Tall raw frames (sequence, diag, sweep) are cropped like the final.
- **`ak_compare_sheet.py`** (new): Blender | Unreal sheets, and reference | Blender | Unreal for C1, written to
  `unreal/compare/`.
- **`ak_manny.py`** now prints `AK_STEP_DONE manny passed=`: the runner's grep had been failing the step.
  **`ak_character.py`**: docstring only (its PlayerStart gate already followed layout.json).

### Unreal-only tuning (measured; rounds on C1 plus all 8 views)
- **Exposure bias -1.80** (was -3.94).
  - The C1-only sweep optimum is -2.24: mean 0.275 / p50 0.209 against Blender's 0.295 / 0.202. But that leaves C3, CW
    and CX 0.07-0.11 darker than their Blender renders.
  - At -1.74, the per-view errors (Unreal - Blender) have medians of +0.007 (mean) and -0.001 (p50). Over the measured
    slope of about 0.12 mean per EV, that gives -1.80. The derivation is in `ak_common.EXPOSURE_BIAS`.
- **`UE_ROLE_SCALE` lantern 0.2 and `UE_SPEC_OFF_ROLES` lantern.** In Blender the opaque paper panes hide the lantern
  point light except through the open top. In Unreal the lanterns cast no shadow, which gave hot floor pools and
  highlights round every lantern.
- **`UE_SHADOW_OFF_ROLES` alcove.** It keeps the plan's budget of at most 12 shadowed local lights, so the 12 case
  lights keep theirs. Blender shadows 16.
- **`UE_PP`**: bloom 0.3 (Unreal's default is 0.675), colour saturation 0.85. Unreal's filmic curve kept the 2800 K
  sunlit gravel at (0.70, 0.47, 0.18), against AgX's (0.63, 0.51, 0.37).
- **`UE_SKY` sky_luminance_factor (5.0, 3.5, 3.0).** The physical sky for a 6000 lux sun read dim teal: CG sky display
  (0.38, 0.44, 0.43) against Blender's cream (0.81, 0.77, 0.72). The factor is the linearised per-channel ratio.
- **Tried and dropped:**
  - `film_toe` 0.3: C1 p10 went only 0.016 -> 0.039, and every mid-tone got darker.
  - SMRT 16 rays x 16 samples with texel dither 0: identical sun patches.

### Final full run (17:18:18-17:20:21, 123 s, all steps exit 0)
| Step | Time and result |
|---|---|
| project | 0 s |
| bounds | 2 s |
| import | 8 s. 93 meshes and 65 textures, unchanged sources skipped. The first real import, at 17:05, took 41 s |
| materials | 9 s. 9 masters, 42 instances, 93 meshes, no unmatched slot |
| level | 8 s. 531 mesh actors. Bounds gate max 0.0051 cm over all 531 (tolerance 1 cm). 2 suns + 103 local lights, 12 shadowed. No failed property set |
| verify | 8 s, fresh process: **all 5 gates pass**. 649 actors: 531 StaticMesh, 2 DirectionalLight, 27 Rect, 70 Spot, 6 Point, 8 CineCamera, sky, fog, PPV, PlayerStart. No channel or cast-shadow errors |
| manny | 8 s. SKM_Manny_Simple, saved |
| character | 8 s. Game mode and Manny OK, 47 dependencies, none missing. One PlayerStart at (600, 1040, 95) cm, yaw -90, facing the entrance. No world-settings override |
| walk | 2 s. `walk_check.py`: 17 of 17 routes clear, both controls blocked, passed |
| capture | 60 s. 9 frames, 96 captures each after 2394 warm-up ticks (21 s). Crop OK |
| stats | 9 s |

Lights per role:

| Role | Count |
|---|---|
| panel | 26 |
| down | 22 |
| sill | 16 |
| case | 12 |
| glow | 12 |
| lantern | 6 |
| alcove | 4 |
| rack | 2 |
| banner | 2 |
| wash | 1 |

Lumen is in the captures:
- Lumen GI off changes C1 by 73 levels (mean display 0.60 against 0.33).
- Lumen reflections off: 9.4 levels.
- Volumetric fog off: 3.9 levels.

Convergence, 64 -> 96 frames: C1 2.6 levels (19 % of pixels move more than 4 levels), C10 0.7, CG 0.6. This is
temporal noise in the scene capture (Lumen / TSR); a single frame would not be representative.

### Unreal vs Blender golden (stage_f2), display values (`capture_stats.json`)
| View | Unreal mean / p10 / p50 / p90 | Blender mean / p10 / p50 / p90 | Saturation U / B | Blue/red U / B |
|---|---|---|---|---|
| C1 | 0.327 / 0.032 / 0.283 / 0.779 | 0.295 / 0.072 / 0.202 / 0.690 | 0.64 / 0.65 | 0.51 / 0.45 |
| C1 1448 x 1086 | 0.319 / 0.022 / 0.267 / 0.762 | 0.300 / 0.062 / 0.202 / 0.696 | 0.64 / 0.65 | 0.52 / 0.47 |
| C3 | 0.280 / 0.033 / 0.209 / 0.642 | 0.329 / 0.074 / 0.269 / 0.708 | 0.69 / 0.74 | 0.44 / 0.36 |
| C5 | 0.284 / 0.007 / 0.117 / 0.828 | 0.282 / 0.012 / 0.145 / 0.732 | 0.67 / 0.69 | 0.55 / 0.49 |
| C10 | 0.240 / 0.020 / 0.141 / 0.710 | 0.173 / 0.011 / 0.069 / 0.526 | 0.80 / 0.86 | 0.35 / 0.26 |
| CW | 0.238 / 0.002 / 0.095 / 0.717 | 0.260 / 0.025 / 0.166 / 0.700 | 0.70 / 0.74 | 0.50 / 0.42 |
| CX | 0.305 / 0.003 / 0.196 / 0.839 | 0.321 / 0.021 / 0.206 / 0.875 | 0.61 / 0.66 | 0.59 / 0.55 |
| CG_Garden | 0.347 / 0.000 / 0.207 / 0.795 | 0.318 / 0.004 / 0.167 / 0.771 | 0.46 / 0.45 | 0.66 / 0.66 |

- Reference 2 at 1448 x 1086: 0.328 / 0.061 / 0.282 / 0.740, saturation 0.46, blue/red 0.58. The Unreal C1 is closer
  to it in mean and mid-tones than the Blender C1 is (0.319 / 0.267 against 0.300 / 0.202), and it is less warm.
- This table uses `ak_image_stats.py` (Rec.709 on the 8-bit values). Its Blender C1 at 1448 x 1086 reads 0.300 / 0.202,
  where the f2 notes give 0.290 / 0.197 with their own script.
- Captures: `unreal/captures/*.png`; raw tall C1 frames in `captures/raw/`.
- Sheets: `unreal/compare/<cam>_blender_vs_unreal.png` and `reference_blender_unreal_C1.png`.

### Open issues
- **Crushed darks.** Unreal's p10 is 0.00-0.03 against Blender's 0.01-0.07. The filmic toe crushes shaded lacquer and
  the timber corners; film_toe did not fix it.
- **Per-view balance.**
  - C10 is brighter than Blender (+0.07 mean). The walls beside the painting and the floor read lighter, and the
    painting paper is still bright.
  - C3 and CW are darker (-0.05 / -0.02 mean, p50 -0.06 / -0.07).
  - Blender's hero table top reads as a bright reflection of the painting; Unreal's is a dull grey lacquer.
- **Floor.** The Unreal floor is lighter and pinker (glossy Lumen reflections of the windows); Blender's is a darker
  walnut.
- **Sun patches** are crisper in Unreal and carry a fine dappled edge: the sill plum sprays' masked shadows. SMRT
  settings do not change it. Blender's patches are softer.
- **Case glass** is almost invisible in Unreal (only the frames read). The f2 open issue, the garden mirrored in the
  C5 tall glass, does not occur in Unreal. The LED-nosing reflections Blender shows in the C3 glass are absent too.
- **Lanterns** read yellower than Blender's peach-cream (filmic hue shift of the emissive paper).
- **Shadow budget.** The alcove spots lost their shadows (budget 12). MegaLights was not evaluated.
- **Garden.** The shaded hall facade is darker than Blender's (no uniform world fill). The far tree-line cards show hard
  mask edges.
- **Still open from earlier stages:** the painting paper brightness; the deck colour (a user call: black lacquer against
  the user's oxblood #4A1715); the 12 m width that crops the side walls out of C1; the ASCII drawing overprint. No
  performance measurement (G0-5) was made.

## 2026-09-27 (evening): look pass 3, main chat. The building is finished (scripted); the exterior is left as built.

The user decided: "just finish the dojo armory via script. dont worry about the outside then". The faithful workflow
(wf_06d6cc6d-8bb) was stopped after its Unreal stage passed; the blind judge had scored 6.5 -> 6.8 -> 6.5. This pass
was measured with `Scripts/armory/region_stats.py` (region colours: reference 2 vs render, same C1 framing).

- **Pink floor, root cause:** the plank base `#352A29` has G = B, so it read mauve-pink under warm light. It is now
  golden walnut `#3B2E24` (reference 2's shaded floor measures sRGB 0.48 / 0.36 / 0.27, i.e. B < G < R).
- **White balance:** every light ran 3100-3800 K, so the frame read over-saturated orange.
  `KELVIN_SHIFT = 900` is applied in `lights()` and travels to Unreal via layout.json.
- **Sun:** 60 -> 90 W/m2. The f2 salmon patches came from the pink floor.
- **Haze:** fog 0.0008 -> 0.0004.
- **Rear alcoves:** rack lights 20 -> 9 W, `M_AK_AlcoveLit` emission 0.18 -> 0.09.
- **Niches:** panel lights 22 -> 14 W, `M_AK_BackBoard` `#A68D69` -> `#7C6446`.
- **Painting:** paler parchment `#C2B397`, ink `#221E1A`.
- **Result, whole-frame C1 mean (sRGB):**

  | Source | R | G | B | Brightness |
  |---|---|---|---|---|
  | Reference | 0.42 | 0.31 | 0.24 | L 0.33 |
  | Blender | 0.42 | 0.31 | 0.21 | L 0.32 |
  | Unreal | 0.40 | 0.28 | 0.20 | L 0.30 |

- **Unreal-only overrides** (`ak_materials.UE_OVERRIDES`): plank tint 0.62, painting tint 0.70. Without them the
  Unreal floor read light oak.
- **Final state:** 93 pieces, QA 0 hard fails, 93 FBX. Unreal: import, materials, level (531 meshes, 103 lights),
  verify (5/5), manny, character and walk (17/17, controls blocked) all pass, and the captures are done.
- Renders: `renders/look3/`. Unreal stills: `unreal/captures/`.
- **Left as is:** the exterior garden, and hero-quality modelling of individual pieces (a possible later phase).
  Items are added one by one later, each with its own stand.

## 2026-09-27: Item 1, the shuriken tray (user: "Just have one tray displaying all of them neatly")

**Tray:** module `Scripts/armory/armory_items.py`, imported by `build_armory_kit.py`.
- Piece `SM_AK_DSP_ShurikenTray`: kiri tray 54.1 x 36.8 cm, six compartments of 16.5 cm (3 x 2), 8 mm dividers,
  1.5 cm walls, a linen lining, and a 6 cm riser. One UCX.
- Placement: on case 8's deck (+0.904), front row toward the aisle.

**Layout:**

| Row | Left | Middle | Right |
|---|---|---|---|
| Back | FourPoint | EightPoint | SixPoint |
| Front | SquarePlate | HookedCross | Spike |

- Every disc lies flat, face +Z up, turned so its Grip arm points straight back. The yaw comes from each sidecar's
  Grip socket: four-point / square / hooked cross 45°, eight-point 67.5°, six-point 60°.
- The spike runs along the tray, point to the viewer's right.
- Scale is +1 everywhere; the HookedCross is rotated only, never mirrored.

**Lighting and materials:**
- The first render blew out: a pale tray sat 42 cm under a case light tuned for a black deck.
- Measured: the ceiling downlights, not the case light, dominate the deck illumination.
- Fix: case 8's light × 0.12 (`ITEMS.CASE_LIGHT`); kiri `#7E6A52`; lining `M_AK_TrayLining` `#4E473D`. The dark
  steel reads crisp and the ground edges catch light.

**Data and Blender preview:**
- `layout.json` gains an `"items"` list: name, form, case, FBX, Unreal asset, Blender loc and rot_z.
- The Blender preview imports each item's real FBX LOD0 with its baked maps into the `Items` collection. Import frames
  are identity with true sizes; the items are not exported with the kit and not in the walk check.

**Unreal:**
- `make_project.py` syncs the pack's imported `/Game/NinjaPack` (172 files, sockets recreated, pack materials) from
  the ShurikenValidation project into ArmoryLab. The pack is the source of truth, so files are overwritten.
- `ak_level.place_items` spawns `ITEM_<name>` actors in `Items/Case_8`.
- New verify gate `6_items` checks the asset, location < 0.1 cm, yaw < 0.1°, no tilt, scale exactly +1, and the
  Grip/Trail sockets present (looked up by name: `StaticMesh.sockets` is protected in 5.8).
- Result: all 6 gates pass, 0.0 cm / 0.0° errors. Manny, character, walk and capture pass.
- Camera `C4_ShurikenTray` added. Stills: `renders/items/` (Blender) and `unreal/captures/C4_ShurikenTray.png`.

### Item 1, revision 2 (user: "The tray should look like the reference image. it's a flat black slate-looking tray")

**Target:** the enlarged crop of reference 2's shuriken board (case 1, right-hand board): one flat matte near-black
slab, no walls or compartments, a small gold plate on the front edge, the items laid straight on it.

**Board:** `SM_AK_DSP_ShurikenTray` is now a 54.1 x 36.8 x 2.5 cm slab.
- Material: new tiling set `T_AK_Slate`, `#1D1D1F` honed, roughness 0.88. At roughness 0.62 it read as brushed metal.
- A blank brass plate (7 x 1.3 cm) sits on the front edge. Same two rows, same yaw rule, same Unreal gate.

**Why the lit card (measured, not guessed):**
- The pack steel is metallic 1.0. From the aisle, a flat star mirrors the back of the case, so under a top light
  alone the steel read black while the matte slab went grey-white. A no-sun render proved the sun was not the cause.
- Fix: a warm lit reflection card (`M_AK_ReflectCard`, emission 0.22) standing 6 cm behind the slab, 20 cm tall.
  The star faces reflect it toward a viewer in the aisle (the reflections land at +8 to +17 cm for the 27° view),
  the same idea as reference 2's lit case interiors.
- Case 8's top light is now x0.08, so the slate stays near-black.

**Result:** dark slate with the shuriken lit warm bronze-gold, in Blender and Unreal. The full pipeline passes,
including `6_items`.

## 2026-09-28: Hero pieces switched on (user: "follow the armory reference for both and switch them on")

**Before state:** `WorkFiles/armory/build/pre_hero_live/`: layout.json, qa_report.json, walk_check.json, export_report.json,
items_report.json, the pre-hero `ArmoryKit_pre_hero.blend`, an md5 manifest of Exports/ArmoryKit, and the newest live
renders (from `hero/room_preview/calib/final_r2/live`, 1600x900, plus C1 at 1448x1086 in `renders/ref_aspect`).

**Switch:** `ENABLED = True` in all nine modules of `Scripts/armory/hero/`: hero_backwall, hero_banner_coffer,
hero_cases, hero_ceiling_lattice, hero_entrance, hero_lantern_vase, hero_rear_alcove, hero_shared, hero_walls. Nothing
else in them changed (their comments still say "ENABLED stays False").

**Live build** (with export, no --preview-dir): HERO lists 48 pieces, the same set and the same modules as the last test
copy (`room_preview/newel_lanterns_build`, b3). Log: `WorkFiles/armory/build/hero_live_logs/build_live.txt`; HERO json:
`hero_live_logs/hero_report.json`.

| Module | Pieces |
|---|---|
| hero_backwall (13) | Steps_2, Platform_Edge_2x1, Platform_2x1, PaintingPanel, RearScreen, Post_LED_480, Post_Heavy_480, LanternPedestal; new H_PaintingBase, H_Downlight, H_DownlightBox, H_Canopy, H_TopBeam |
| hero_cases (11) | Case_Hero_Plinth; Case_S/M/L/LN/Tall Plinth and Glass |
| hero_entrance (8) | Entrance_12, DoorLeaf, DoorLeaf_R, Post_Jamb_480, Threshold_4, EntryStep_4, EntryMat; new H_WallSconce |
| hero_banner_coffer (4) | Banner, Ceiling_Coffer_2x2; new H_Ceiling_Downlight, H_Ceiling_Joint |
| hero_lantern_vase (4) | Lantern, Vase_Plum_S, Vase_Plum_L; new H_NewelLantern |
| hero_walls (4) | Window_Lattice (reference-2 windows), WallPanel_Lit, WallPanel_Lit_190, SillLedge_2 |
| hero_shared (2) | Ceiling_Beam_4, Ceiling_Rib_2 (+ the kit material overrides) |
| hero_ceiling_lattice (1) | Ceiling_Lattice_2x2 |
| hero_rear_alcove (1) | RearAlcove |

- New pieces (9 FBX in Exports/ArmoryKit): SM_AK_H_Canopy, H_Ceiling_Downlight, H_Ceiling_Joint, H_Downlight,
  H_DownlightBox, H_NewelLantern, H_PaintingBase, H_TopBeam, H_WallSconce.
- QA: 104 pieces, hard fails 0. 104 FBX exported through Scripts/pipeline. Instances 520 -> 583; layout tris
  28,510 -> 88,411; openings and cameras unchanged.
- Lights: 105 before and after. The two floor-lantern points at the stair foot (Lantern_3.3_13.0 / 8.7_13.0) are
  replaced by NewelLantern_3.3_13.25 / 8.7_13.25 (+1.01, radius 0.05, power x0.5), identical to the test copy.
- Textures: every image the live blend's materials use exists in Exports/ArmoryKit/Textures, is power of two, BC sRGB
  and ORM/N non-colour (check: `hero_live_logs/texture_check.json`). 24 T_AK_H* sets are in use: AlcoveGrille,
  AlcovePanel, AlcoveReturn, BannerSatin, EntBrushed, EntCoirR, EntTimberE, Halo, KickGlow, Lacquer, LatticeBoss,
  LatticeGlow, LatticeSlot, LatticeTimber, Medallion, NicheWashiRoom, NicheWashiRoom190, PaintingTall, Plank, Screen,
  Tassel, Timber, WallOak, WashiRoom. Full BC/ORM/N for the lit surfaces; BC only (emissive/unlit) for AlcoveGrille,
  AlcovePanel, Halo, KickGlow, LatticeGlow, LatticeSlot, NicheWashiRoom(190), PaintingTall, WashiRoom.
- Walk check (live blend): all 17 routes clear, both controls blocked (case 1 plinth, stone lantern). passed True.

**Renders** (render_armory golden, 96 samples, 1600x900; C1 also 1448x1086): `renders/hero_live/`, sheets
`renders/hero_live/compare/` (C1_ref_before_after = reference | before | after; <cam>_before_after for all eight).
Live vs the last test copy (mean abs difference, 0-1): C1 0.0005, CX 0.0001, C10 0.0000 (newel b3), C1 ref-aspect
0.0007 (b3) / 0.0013 (win_2), CW 0.0022 (win_2): the live room is the calibrated test copy. Against final_r2 the
differences are the window and newel-lantern stages (C1 L0.319 -> 0.383, CX 0.287 -> 0.358, CW 0.214 -> 0.274).

**Colour, C1 at the reference framing** (region_stats; `renders/hero_live/compare/C1_region_stats.txt`):

| Region | Reference | Before (pre-hero live) | final_r2 test | After (hero live) |
|---|---|---|---|---|
| whole | L0.33 | L0.34 | L0.31 | L0.38 |
| side_window | L0.79 c49% | L0.72 c47% | L0.68 c30% | L0.82 c63% |
| left_window | L0.72 | L0.39 | L0.10 | L0.28 |
| left_upper_wall | L0.19 | L0.46 | L0.21 | L0.47 |
| floor_front | L0.53 | L0.44 | L0.44 | L0.55 |
| floor_sunpatch_centre | L0.54 | L0.38 | L0.45 | L0.52 |
| floor_hi10 | L0.93 c99% | L0.88 | L0.88 | L0.96 c100% |
| case_glass_edge | L0.90 c91% | L0.87 | L0.89 | L0.95 c100% |
| lantern_paper | L0.72 | L0.83 | L0.74 | L0.74 |
| painting_centre | L0.39 | L0.51 | L0.41 | L0.42 |
| rear_lattice | L0.18 | L0.44 | L0.21 | L0.26 |
| niche_back | L0.47 | L0.29 | L0.40 | L0.44 |
| front_plinth | L0.08 | L0.35 | L0.28 | L0.29 |

Open: the left upper wall (L0.47 against 0.19) came back with the window stage's bigger openings; the whole frame is
0.05 over the reference; the left window is still dark (L0.28 against 0.72).

**Decisions carried in:** the windows and the newel lanterns follow armory3_reference2.png (windows: slim 2.8 cm dark
oak frame, 1.41 x 1.36 m clear field, 13 dark bars, one rail at 44 %; newel lanterns: lit 0.28 m lantern on each
stair-foot newel, X 3.30 / 8.70, Y 13.25); the heavy posts and newels stay at the layout's X (r2's move reverted);
fixed user decisions: tall case glass 1.70 m, hero table 52 cm, entrance posts at the frame ends with the doors between
them, large vases fanned toward the entrance, slim newels at the stair foot, the user's emblem on every medallion.

**Not done here:** the ArmoryLab Unreal project was not rebuilt from these exports. `Exports/ArmoryKit/SM_AK_Entrance_6.fbx`
(2026-09-27) is a stale orphan that no build writes any more.

## Unreal: hero pieces (2026-09-28)

The ArmoryLab level `/Game/Armory/Maps/L_Armory` was rebuilt from the live hero build: 104 pieces, 583 instances, 48 hero
pieces from 9 modules. No ArmoryLab editor was open. The runner waited on its own while another chat's DojoLab
commandlet finished, and it ran one Unreal process at a time. No MCP was used. The `ArmoryKit` lock was held for the
whole stage and then released. The pre-hero Unreal results, final captures and scripts are saved in
`unreal/pre_hero/`.

### Script changes (`Scripts/armory/unreal/`)
- **`ak_common.py`**
  - `layout_pieces()`, `layout_textures()`, `texture_kinds()`: the kit is now defined by layout.json. It covers every
    piece in `pieces` and every map a layout material uses. An emissive picture (`emit_image`) uses BC only; every
    other set uses BC, ORM and N.
  - `n_meshes`, `n_textures` and `engine_textures` now follow layout.json. The export folder also holds the stale
    `SM_AK_Entrance_6.fbx` and 77 maps of retired or BC-only sets, so a folder glob gives the wrong kit.
  - `material_spec()` / `blender_materials()`: the per-material Unreal spec (master, scalars, vectors, maps) moved here
    from `ak_materials`, so `ak_verify` can check every instance against layout.json itself. New handling:
    - glass `refl` scales Specular and Edge Opacity by refl / 0.02. `M_AK_HCaseGlass` at 0.035 gets 0.175 / 0.105.
    - glass `tint` is reported in a note unless it is white. The only tint used is `#FFFFFF`.
    - opaque `two_sided` goes to the new `M_AK_TexturedTwoSided_Master` (`M_AK_HBannerSatin`).
    - `tint`, `emit_image`, `unlit`, `alpha`, `coat` and `rough` behave as before, for every M_AK_H* name.
  - `UE_OVERRIDES` and `GLASS` moved here from `ak_materials`. The overrides were re-derived, as listed below.
  - `EXPOSURE_BIAS` -1.80 -> -1.58, explained below.
  - `AK_ROLE_SCALE` (diagnostics only) switches a light role off for a test level. If it is set, verify fails the
    intensities by design.
- **`ak_import.py`** imports every layout.json piece and map. A piece or map that the layout needs but the exports lack
  fails the step. It deleted our stale `SM_AK_Entrance_6` mesh and 24 retired textures (Plank, Timber, Painting, Plum,
  Banner, Mat, Ground, Backdrop, and the unused LanternPaper N/ORM).
- **`ak_materials.py`**
  - It is generic over layout.json `materials`: 123 instances, 92 of them M_AK_H*, on 10 masters.
  - The masters' default textures are taken from the first layout material on each master. The fixed T_AK_Timber,
    T_AK_Plum and T_AKX_Hills defaults are gone from the kit.
  - It fails if a map an instance needs is missing.
  - It deleted 13 stale instances, including M_AK_Painting, M_AK_Plum, M_AK_Banner and M_AK_Glass.
- **`ak_level.py`**
  - It reads back `forward_shading_priority` on both suns. The level passes only if the property set succeeded and the
    readback is 1 on the sun and 0 on the window fill.
  - A light role without a folder name goes to `Lights/<role>` instead of raising an error.
- **`ak_verify.py`**
  - Gate 1: the Blender kit, layout.json and the Unreal mesh folder are the same set, with no stale mesh.
  - Gate 2: textures come from layout.json.
  - Gate 3: every layout material is checked against `material_spec`: parent, scalars, vector colours and maps, plus
    the masters. No extra instance may remain.
  - Gate 5: each sun's `forward_shading_priority`.
  - New gate 7_hero: every `hero_pieces` entry is a mesh with every slot on its instance, placed as often as layout.json
    places it. Counts are reported per module.
- **`ak_image_stats.py` / `ak_compare_sheet.py`** now compare against `renders/hero_live` (was stage_f2).

### Final run (14:00-14:04, all steps exit 0)
| Step | Result |
|---|---|
| import | 104 meshes, 96 textures, no errors |
| materials | 10 masters, 123 instances, 104 meshes, no unmatched slot |
| level | 583 mesh actors; bounds gate max 0.0023 cm; 2 suns + 103 local lights, 12 shadowed; setp_failed empty |
| verify (fresh process) | 1_meshes, 2_textures, 3_materials, 4_level, 5_lights, 6_items, 7_hero: all pass. 708 actors: 589 StaticMesh (583 kit + 6 items), 2 Directional, 27 Rect, 70 Spot, 6 Point, 9 CineCamera, sky, fog, PPV, PlayerStart |
| manny / character | pass: SKM_Manny_Simple, 47 dependencies with none missing, PlayerStart facing the entrance |
| walk | 17 of 17 routes clear, both controls blocked, passed |
| capture | 10 frames (9 cameras + C1 at 1448 x 1086) in `unreal/captures/` |

- 7_hero per module: backwall 13, cases 11, entrance 8, banner_coffer 4, lantern_vase 4, walls 4, shared 2,
  ceiling_lattice 1, rear_alcove 1.
- **Forward shading:** in `level.json` the suns read `Sun_GoldenHour` forward_shading_priority 1 and `Sun_WindowFill` 0,
  `setp_failed` is `[]`, and verify.json confirms the same. The 5.8 property name `forward_shading_priority` is correct.
  None of the logs contains "Multiple directional lights".

### Unreal-only tuning (C1 region colours against the hero_live Blender C1; `unreal/region_stats_hero_final.txt`)
- **`M_AK_Plank` tint 0.86.** At Blender tint 1.8 the HPlank floor read light grey oak: floor_shade L0.58 against 0.36.
  At bias -1.80, 1.0 matched; 0.86 = 1.0 / 1.165 for the new bias. look3's 0.62 was tuned for the retired T_AK_Plank.
- **`M_AK_HPaintingTall` emission 0.043** (Blender 0.1). The paper read 0.57 against 0.42. This replaces look3's
  painting tint 0.70, whose material is gone.
- **`M_AK_HWashi` emission 0.146** (Blender 0.28). The lantern paper read 0.83 against 0.74.
- **`M_AK_HDeck` colour `#432D11`** (Blender `#6E5A48`).
  - The platform deck read pale cream in every view: C1 (0.74, 0.59, 0.45) against (0.51, 0.31, 0.12), and C10
    (0.68, 0.57, 0.46) against (0.50, 0.31, 0.14).
  - Diagnostic captures ruled out other causes: the result did not change with the painting wash off, the lanterns off,
    the downlights off, the deck's coat off, or Lumen reflections off (`unreal/tuning/`). The fix is the per-channel
    linear ratio.
- **Exposure bias -1.58** (was -1.80). At -1.80 the room views' mean errors had a median of -0.027: C1 -0.027,
  C3 +0.019, C4 -0.027, C5 -0.041, C10 +0.029, CW -0.042, CX -0.066.

**Final C1 (1448 x 1086), display sRGB:**

| Region | Blender | Unreal |
|---|---|---|
| whole | (0.47, 0.36, 0.27) L0.38 | (0.42, 0.34, 0.26) L0.35 |
| floor_shadow_left | L0.39 | L0.38 |
| floor_front | L0.55 | L0.54 |
| floor_lo50 | L0.30 | L0.31 |
| floor_shade | L0.36 | L0.42 |
| floor_sunpatch_centre | L0.52 | L0.45 |
| painting_centre | L0.42 | L0.42 |
| lantern_paper | L0.74 | L0.77 |
| platform_deck | (0.51, 0.31, 0.12) L0.34 | (0.55, 0.30, 0.09) L0.34 |
| case_deck_front | L0.26 | L0.33 |
| niche_back | L0.44 | L0.53 |
| rear_alcove_left | L0.36 | L0.43 |
| front_plinth | L0.29 | L0.15 |
| left_upper_wall | L0.47 | L0.24 |
| side_window | L0.82 | L0.61 |
| rear_lattice | L0.26 | L0.10 |

**Per view** (whole-frame mean, Unreal - Blender):

| View | Difference |
|---|---|
| C1 | -0.020 |
| C3 | +0.035 |
| C4 | -0.010 |
| C5 | -0.029 |
| C10 | +0.041 |
| CW | -0.032 |
| CX | -0.058 |
| CG_Garden | +0.091 (own offset; exterior left as is) |

Unreal p10 stays at 0.00-0.02 against Blender's 0.01-0.06 (the filmic toe, as before).

### Open issues
- **Already there before the hero pieces**, per the pre-hero look3-vs-Unreal region stats
  (`unreal/tuning/region_prehero_look3_vs_unreal.txt`):
  - the left upper wall, west windows and rear lattice read darker in Unreal (Lumen bounce and the window washi
    against Cycles);
  - the front plinth lacquer reflects less of the floor.
  These are not material-override fixes.
- **Sun patch against shade.** Unreal's sunlit boards read 0.45 against 0.52 while its shaded floor reads 0.42 against
  0.36. One tint cannot match both.
- **Tangent warnings.** The first import warned about degenerate tangent bases (MikkTSpace) on several meshes, including
  WallPanel_Lit, WallPanel_Lit_190, Steps_2, RearScreen, PaintingPanel, Lantern, H_PaintingBase, H_NewelLantern and
  H_Canopy. They are harmless in the captures.
- **Stale export.** `Exports/ArmoryKit/SM_AK_Entrance_6.fbx` is still on disk, unused. It is no longer imported, and its
  Unreal mesh was deleted.
- **Nanite** stays off. The largest hero pieces are 4-7k tris.

## 2026-09-28: Night lighting + genkan entry (live)

User: "reduce the brightness significantly in ours. make it nighttime for us. also the front entrance is not
matching... please fix the front entrance." The two test-copy rounds (night preset in `render_armory.py`, genkan
deltas 1-4 and 6 in the kit) were made live under the ArmoryKit lock.

**Live build with export** (`build_armory_kit.py`, no flags): QA 107 pieces, hard fails 0; 107 FBX exported to
`Exports/ArmoryKit`; `ArmoryKit.blend` saved with 577 instances. HERO lists all 49 hero-mapped meshes (9 groups),
including the new/changed entry pieces `SM_AK_Lantern_Entry`, `SM_AK_EntryMat`, `SM_AK_StepBeam` (hero_entrance /
hero_lantern_vase). Re-exported entry FBX: SM_AK_EntryMat, SM_AK_StepBeam, SM_AK_Lantern_Entry, SM_AK_GenkanFloor,
SM_AK_Entrance_12; texture sets `T_AK_HEntSisal_*` and `T_AK_HEntTimberG_*` are in `Exports/ArmoryKit/Textures`.

**Walk check (live blend):** passed; 705 hulls; every route clear; both controls blocked (case 1, stone lantern);
largest entry step 0.16 m down (limit 0.18), up 0.12 m.

**Renders** (Cycles, 96 samples; night is now the default preset):
- `renders/night_live/`: C1, CX, C10, C3, C5, CW, C4, CG at 1600 x 900; `night_live/ref_aspect/` C1 at 1448 x 1086.
- `renders/golden_live/`: golden C1 at 1448 x 1086 (entry comparison).
- `renders/night_live/compare/`: `C1_ref_vs_golden_live.png` (entry check), `C1_ref_vs_night_live.png`,
  `<cam>_hero_live_vs_night_live.png` for all eight views, `C1_region_stats.txt` (reference | golden_live | night).

Whole-frame mean display luminance, night_live / hero_live golden:

| View | Golden | Night | Ratio |
|---|---|---|---|
| C1 | 0.383 | 0.134 | 0.35 |
| CX | 0.358 | 0.094 | 0.26 |
| C10 | 0.210 | 0.132 | 0.63 |
| C3 | 0.291 | 0.178 | 0.61 |
| C5 | 0.288 | 0.107 | 0.37 |
| CW | 0.274 | 0.103 | 0.38 |
| C4 | 0.227 | 0.135 | 0.60 |
| CG | 0.347 | 0.119 | 0.34 |

C1 at 1448 x 1086: reference 0.328, hero_live golden 0.376, golden_live 0.357, night 0.129. C1 regions (reference /
golden_live / night): lantern paper L0.72 / 0.72 / 0.49, floor front 0.53 / 0.55 / 0.14, front plinth 0.08 / 0.20 /
0.01, side window 0.79 / 0.82 / 0.02.

**Open (seen in the live renders):**
- Entry vs reference (golden C1): the step beam still runs the full frame width past both lanterns, and its lighter
  weathered top reads grey-brown rather than the reference's black bar; the parked-door jambs at the frame edges
  (delta 5) are still not in view; the sunken genkan floor is the same tone as the hall floor.
- Close views (C10, C3, C4) only fall to about 0.6x golden: the painting and LED lines dominate them.
- CX night: the courtyard seen through the open entrance reads comparatively bright (pale ground, a green panel at the
  gate) against the dark hall.
- The display cases render empty in C1 / CX (as in hero_live).
- Unreal not rebuilt: `ak_common` still derives the golden values; the ArmoryLab night stage is a separate step.

## Unreal: night + genkan (2026-09-28)

The ArmoryLab level `/Game/Armory/Maps/L_Armory` was rebuilt from the live night + genkan build (107 pieces, 577
instances). NIGHT is now the level's default lighting. No ArmoryLab editor was open and no other Unreal process ran. The
`ArmoryKit` lock was held for the whole stage and then released. No MCP was used. The golden hero-round results
(captures, level/verify/capture/materials json, scripts) are saved in `unreal/golden_hero/`.

### Preset switch
`ak_common.PRESET` comes from the environment variable `AK_PRESET`: `night` (default) or `golden`. Every Unreal step is
its own process, so set it for the whole run: `AK_PRESET=golden bash Scripts/armory/unreal/run_armory_unreal.sh`
rebuilds the golden-hour level exactly as the hero round (bias -1.58, 9000 + 7650 lux suns, volumetric fog, the golden
UE_OVERRIDES, saturation 0.85). Run materials, level, verify, capture and stats with the same preset: the scenery-card
dimming and the night overrides live in the material instances. The golden path was checked offline (constants and
specs identical to the hero round), not re-run in Unreal.

### Script changes (`Scripts/armory/unreal/`)
- **`ak_common.py`**
  - Reads `MOON`, `PRESET_KELVIN`, `NIGHT_EMIT`, `NIGHT_SKY_CAM` and `CAM_EXPOSURE` from `render_armory.py` too.
  - `ROLE_SCALE` (was `GOLDEN_SCALE`), `SUN_W_M2`, `BLENDER_EXPOSURE_EV`, `FOG_DENSITY_PER_M`, `SKY_FILL` follow the preset.
  - `light_kelvin()`: `PRESET_KELVIN` (night downlights 3500 K instead of layout.json's 5900 K).
  - `directional_specs()`: golden = the two layout suns as before; night = ONE light, `Moon`: 300 lux (3.0 W/m2 x K),
    7500 K, 38 deg up, heading 35 deg (Unreal forward (0.6455, 0.4520, -0.6157)), disc 0.5 deg, SkyAtmosphere light,
    channel 0, volumetric scattering 0, no volumetric shadow, forward shading priority 1. Sun_GoldenHour and
    Sun_WindowFill are not spawned.
  - `camera_exposure_offset()`: `CAM_EXPOSURE[preset]` first (night CG_Garden +0.3 vs +1.1 = -0.8 EV).
  - `blender_materials()`: night scales the far-scenery cards' emission by `NIGHT_EMIT` (x0.012) and adds `emit_tint`
    (0.30, 0.45, 1.0); `material_spec()` gives every emissive picture an `Emissive Tint` vector (white by default).
  - Per preset: `EXPOSURE_BIAS_BY_PRESET` (golden -1.58, night -2.68), `UE_ROLE_SCALE_BY_PRESET`, `UE_SKY_BY_PRESET`,
    `SKYLIGHT_INTENSITY` (golden 1.0, night 0.25), night `UE_PP`, and `UE_OVERRIDES_NIGHT` merged over `UE_OVERRIDES`
    (night only). Values and reasons below.
- **`ak_materials.py`**: the emissive-picture masters multiply the emission by a new `Emissive Tint` parameter.
- **`ak_level.py`**: directional lights from `directional_specs`; local-light colour from `light_kelvin`; sky light at
  `SKYLIGHT_INTENSITY`; height fog density from the preset and volumetric fog only when the preset has haze (night: off,
  no shafts; the fog actor stays). The level passes only if the level holds exactly the preset's directional lights
  (night: 1) with their priorities read back.
- **`ak_verify.py`** gate 5: the directional set must equal `directional_specs` (night: `Moon` only), each with direction,
  lux, disc, atmosphere flag, channels, scattering and priority; every local light's colour matches the preset's
  temperature (8-bit sRGB within 2); fog matches the preset (night: density 0, volumetric off); sky light intensity and
  PPV bias are the preset's.
- **`ak_capture.py`**, **`ak_image_stats.py`**, **`ak_compare_sheet.py`**, **`run_armory_unreal.sh`**: preset-aware; the
  Blender baseline is `renders/night_live` (`<cam>_night.png`) for night and `renders/hero_live` for golden; the stats
  key is now `blender`; the runner exports `AK_PRESET` (default night) and stamps it in `logs/timings.txt`.

### Final run (16:15-16:18, all steps exit 0)
| Step | Result |
|---|---|
| import | 107 meshes, 99 textures |
| materials | 10 masters, 125 instances, 107 meshes |
| level | 577 mesh actors; bounds gate max 0.0032 cm; 1 directional (Moon, priority 1) + 103 local lights, 12 shadowed; setp_failed empty |
| verify (fresh process) | 1_meshes, 2_textures, 3_materials, 4_level, 5_lights, 6_items, 7_hero: all pass; directional set `['Moon']`; fog off; PPV bias -2.68 |
| manny / character | pass (SKM_Manny_Simple; PlayerStart in the courtyard facing the entrance) |
| walk | passed: every route clear, both controls blocked (case 1, stone lantern) |
| capture | 10 frames in `unreal/captures/`; night C1: `unreal/captures/C1_EntryReveal.png` and `C1_EntryReveal_ref_aspect.png` |
| stats | `unreal/capture_stats.json` (against night_live); sheets in `unreal/compare/` |

No log contains "Multiple directional lights".

### Unreal-only night tuning (C1 at 1448 x 1086 against the Blender night C1; `unreal/tuning/night/t2..t11`)
First pass (straight conversion, bias -2.88): every room view within 0.035 of Blender's whole-frame mean, but white
clipped pools in front of every plinth (L 0.63 against 0.26), cream-white LED lines, hot niches and case decks, a
dark-red platform deck, a crushed floor, and a bright DAYTIME blue sky over bright gravel in CG_Garden (+0.14).
- **glow x0.25** (role scale): the under-glow rects are Lambertian in Unreal; Blender narrows them to a 160 deg spread.
- **panel x0.6** plus `M_AK_HNicheWashi`/`190` emit 0.02 -> 0.012 and `M_AK_HNicheSide` 0.035 -> 0.015: niche_back
  L 0.38 -> 0.30 (Blender 0.26).
- **PP: saturation 1.0, film_toe 0.4.** The golden 0.85 was for the 2800 K sun. The toe lift raised the floor
  (floor_lo50 0.068 -> 0.10, Blender 0.11).
- **`M_AK_HAmberHot` 22 -> 6, `M_AK_HKickGlow` 3.15 -> 1.2, `M_AK_HLedStrip` 1.2 -> 0.6:** the LED lines were
  cream-white in Unreal's shoulder.
- **`M_AK_HWashi` 0.11**, **`M_AK_HAlcovePanel` 0.6**, **`M_AK_HDeck` #534337** (the golden #432D11 read dark red at
  night), **`M_AK_HDeckSuede` #060504 rough 0.8** (a cool sheen from the 6400 K case lights), **`M_AKX_Gravel` tint 0.6**.
- **Sky:** `sky_luminance_factor` (0.06, 0.11, 0.10), sky light 0.25. CG_Garden sky display (0.008, 0.057, 0.124)
  against Blender (0.011, 0.050, 0.105).
- **Exposure bias -2.68.**

**Final C1 (1448 x 1086), display sRGB** (`unreal/region_stats_night_final.txt`: reference | Blender night | Unreal night):

| Region | Blender night | Unreal night |
|---|---|---|
| whole | (0.19, 0.12, 0.06) L0.13 | (0.18, 0.12, 0.07) L0.13 |
| floor_front | L0.14 | L0.14 |
| floor_shade | L0.10 | L0.10 |
| floor_lo50 | L0.11 | L0.10 |
| floor_sunpatch_centre (moon) | L0.14 | L0.12 |
| floor_shadow_left | L0.18 | L0.16 |
| lantern_paper | L0.49 | L0.50 |
| painting_centre | L0.20 | L0.22 |
| platform_deck | (0.40, 0.25, 0.12) L0.27 | (0.42, 0.25, 0.14) L0.28 |
| case_deck_front | L0.08 | L0.07 |
| niche_back | L0.26 | L0.30 |
| rear_alcove_left | L0.30 | L0.32 |
| side_window | L0.02 | L0.07 |
| rear_lattice | L0.12 | L0.06 |
| glow pool before the front plinth | (0.40, 0.24, 0.09) L0.26 | (0.40, 0.25, 0.16) L0.28 |
| plinth kick line | (0.64, 0.33, 0.03) L0.37 | (0.66, 0.42, 0.24) L0.46 |

**Per view** (whole-frame mean display luminance, Unreal / Blender night):

| View | Unreal | Blender | Difference |
|---|---|---|---|
| C1 | 0.127 | 0.134 | -0.007 |
| C1 1448 x 1086 | 0.129 | 0.129 | 0.000 |
| C3 | 0.174 | 0.178 | -0.004 |
| C4 | 0.148 | 0.135 | +0.013 |
| C5 | 0.120 | 0.107 | +0.013 |
| C10 | 0.141 | 0.132 | +0.009 |
| CW | 0.102 | 0.103 | -0.001 |
| CX | 0.104 | 0.094 | +0.010 |
| CG_Garden | 0.143 | 0.119 | +0.024 |

C2_Case1 has no Blender night render (not in night_live).

### Open issues
- **Kick lines and pools.** The plinth kick lines and the glow pools stay paler than Blender's amber. This is Unreal's
  filmic shoulder against AgX; a tonemapper difference that no material fix removes.
- **Pre-existing darkness.** The rear lattice (L 0.06 against 0.12) and the left upper wall stay darker, as in golden
  (Lumen against Cycles).
- **CG_Garden.** The moonlit gravel is still warmer, L about 0.36 against 0.32. The foreground maple glows red with
  translucency, and the pine/tree-line cards read somewhat brighter than Blender's.
- **Unreal p50** runs lower than Blender's in most views: 0.07 against 0.09 on C1. It is the toe; p90 is higher.
- **The entry.** Unreal reproduces the live genkan as built. The step beam still runs past both lanterns with a
  grey-brown top; that fix is a separate Blender task.
- **The Unreal golden preset** was not re-captured this stage. `AK_PRESET=golden` rebuilds it.

## 2026-09-28: Entry fix round 2 made live (night_live2)

The entryfix round 2 test-copy result (b5: the 40 mm C1 camera fitted together with the entry layout; test copy
`WorkFiles/armory/hero/room_preview/entryfix`, blind judge 7.2/10) was built live under the ArmoryKit lock (claimed
17:17, released at the end). The script edits were already live in `Scripts/armory/`. No MCP was used and Unreal was
not run.

**Textures.** The first live build stopped: `T_AK_HEntRushK_*` (the mat) and `T_AK_HEntTimberL_*` (the bar's lacquered
timber) existed only in the test copy's `Textures/`. They were written into `Exports/ArmoryKit/Textures` with
`tex_entrance.py HEntRushK HEntTimberL`, and the files are byte-identical (md5) to the test copy's sets.

**Live build with export** (`build_armory_kit.py`, no flags): QA 106 pieces, hard fails 0; 106 FBX exported;
`ArmoryKit.blend` saved with 577 instances; the C1_EntryReveal camera in layout.json is now 40 mm at (6.0, -4.18, 3.39),
level, shift_y -0.315. The entry lanterns are `SM_AK_Lantern` pieces now, so `SM_AK_Lantern_Entry` is gone from the kit.
Build log: `renders/night_live2/build_log.txt`.

**Orphaned FBX.** `SM_AK_Lantern_Entry`, `SM_AK_EntryStep_4` and `SM_AK_Entrance_6` are not in the live layout.json
(which `ak_import` reads), so they went from `Exports/ArmoryKit` to the Windows Recycle Bin (recoverable; the last two
are also in git). Old snapshot / test-copy layouts still name them (`layout_pre_entrance.json`,
`pre_hero_live/layout.json`, `hero/room_preview/layout.json`, `genkan/layout*.json`, `newel_lanterns_build/layout.json`);
those are history only. `Exports/ArmoryKit` now holds exactly the 106 layout pieces.

**Walk check (live blend):** passed; every route clear; both controls blocked (case 1 at (6.0, 2.75), stone lantern at
(7.58, -7.3)); entry_steps_ok, largest steps 0.12 m up (bar, beside the lanterns) and 0.16 m down (sill). Log:
`renders/night_live2/walk_log.txt`.

**Renders** (Cycles 96 samples, night preset): `renders/night_live2/` C1, CX, C10, C3, C5, CW, C4, CG at 1600 x 900;
`night_live2/ref_aspect/` C1 at 1448 x 1086. Comparison sheets in `night_live2/compare/`:
`C1_ref_vs_night_live_vs_night_live2.png` (1448 x 1086 panels), `..._1600x900.png`, and `C1_region_stats.txt`
(reference | night_live | night_live2; the region boxes are fixed pixels, so after the camera change the C1 regions no
longer land on the same content and only "whole" is comparable).

Whole-frame mean display luminance, night_live -> night_live2: C1 0.13 -> 0.15, CX 0.09 -> 0.09, C10 0.13 -> 0.15,
C3 0.18 -> 0.20, C5 0.11 -> 0.11, CW 0.10 -> 0.11, C4 0.14 -> 0.14, CG 0.12 -> 0.12.

**Open (from the round 2 judge, 7.2/10; not addressed in this build):**
- Blockers: the entry mat reads as a 2x2 tatami split (a seam near the bottom of C1, fully visible in CE_EntryDown),
  where the reference shows one continuous woven mat with a black border; the lantern top (an overhanging lid, post
  stubs, bright gap strips) against the reference's flush, open top with a centre cross-rail.
- Deltas: the lantern faces lack the thin inner frame and extra mullion; the bar's near-black band is about 32 px against
  18 px; the right framing board shows lighter orange grain in close views; the lantern footprint is about 15% wider (cap
  overhang); possibly a second frame behind each lantern against the side wall (low confidence).
- Unreal was not rebuilt: ArmoryLab still holds the previous night + genkan build. A rebuild is
  `bash Scripts/armory/unreal/run_armory_unreal.sh` (night default); `ak_import` deletes stale assets not in layout.json.

## Unreal: night rebuild from night_live2 + brighter under-glow (2026-09-28)

User: "please make the lights below the showcase boxes glow brighter". Blender already carries the raise (M_AK_HAmber
8.5, M_AK_HAmberHot 22, night glow role x3.0), but the previous Unreal night stage had dimmed it again (glow lights x0.25,
HAmberHot 6, HKickGlow 1.2) because the 4200 K pools clipped cream-white. ArmoryLab `/Game/Armory/Maps/L_Armory` was
rebuilt at night from the live entry-fix round 2 build (106 pieces, 577 instances; b5 C1 camera) with a brighter,
saturated amber under-glow. The `ArmoryKit` lock was held for the stage (claimed 17:23) and then released. No MCP was
used. No ArmoryLab editor was open. One other session's UnrealEditor-Cmd was running at the start, and the runner
waited for it to finish without touching it.

**Why Unreal read cream.** In Cycles the amber streak on the floor in front of every plinth comes from the hot emissive
strips (HAmberHot, the HKickGlow picture) lighting the glossy floor and reflecting in it. The 4200 K glow rect only adds
a soft warm-white spill. In Unreal the emissives light nothing, so the rect alone made a wide cream pool.

**Script changes (`Scripts/armory/unreal/`)**
- `ak_common.py` (night only; golden unchanged, checked offline):
  - `UE_ROLE_SCALE` night glow 0.25 -> 1.0.
  - New `UE_ROLE_KELVIN` {glow: 2000 K}: the rect carries the strips' amber. `light_kelvin()` applies it after
    PRESET_KELVIN.
  - New `UE_ROLE_BARN_DOOR_CM` {glow: 2.0}: straight barn doors, since the rect hangs 7.5 cm over the floor. They keep
    the light in a band beside the plinth.
  - New `light_barn_door_cm(L)`: also derives the hero table's spread doors as before.
  - `UE_OVERRIDES_NIGHT`: M_AK_HAmberHot 6 -> 12; M_AK_HKickGlow 1.2 -> 2.0 with `emit_tint` (1.0, 0.8, 0.6), so its
    white-hot core stays amber in the filmic shoulder.
- `ak_level.py`: rect barn doors come from `light_barn_door_cm`. `level.json` lights list `barn_door_cm`.
- `ak_verify.py` gate 5 also checks every rect light's barn-door length and angle.
- `ak_image_stats.py`, `ak_compare_sheet.py`, `run_armory_unreal.sh`: the night Blender baseline is now
  `renders/night_live2`.
- `Scripts/armory/region_stats.py`: new glow regions for the b5 C1 framing: `glow_kick_front`, `glow_kick_front_hi10`,
  `glow_pool_front`, `glow_pool_front_wide`, `glow_kick_mid`, `glow_pool_mid`, `glow_east_plinths_hi10`.

**Tuning** (C1 at 1448 x 1086, one capture per try; `unreal/tuning/glow/`):

| Try | Result |
|---|---|
| g1 | Before (current settings, new build) |
| g2: 2000 K, doors 6 cm, x0.5 | Doors cut the pool to a line (pool L 0.22) |
| g3: 3 cm, x1.0, KickGlow 2, AmberHot 12 | Pool 0.56 |
| g4: 2 cm, KickGlow tint | Pool 0.61, mid pool 0.45. Chosen |
| g5: 1800 K, x0.8 | Pool 0.55, too orange, B 0.02 |
| g6: 1900 K, x0.9 | Mid pool 0.43, under Blender's 0.46 |

**Final run (17:41-17:43, all steps exit 0)**

| Step | Result |
|---|---|
| import | 106 meshes, 99 textures |
| materials | 10 masters, 124 instances |
| level | 577 actors; bounds gate max 0.0047 cm; 1 directional (Moon) + 103 local lights; setp_failed empty |
| verify (fresh process) | Gates 1-7 all pass, including the barn doors |
| manny / character | Pass |
| walk | Every route clear; both controls blocked (case 1, stone lantern); entry_steps_ok |
| capture | 10 frames |
| stats / compare | Done |

No "Multiple directional lights" in any log.

**Glow, C1 1448 x 1086, display sRGB** (`unreal/region_stats_glow_final.txt`; reference | Blender night_live2 | Unreal
before | Unreal after):

| Region | Blender | Unreal before | Unreal after |
|---|---|---|---|
| glow_kick_front (plinth LED line + kick band) | (0.65,0.37,0.07) L0.41 | (0.58,0.30,0.05) L0.34 | (0.72,0.37,0.05) L0.42 |
| glow_kick_front_hi10 | (0.94,0.65,0.40) L0.70 | (0.87,0.71,0.33) L0.71 | (0.99,0.89,0.35) L0.87 |
| glow_pool_front (floor in front of the front plinth) | (0.74,0.47,0.19) L0.51 | (0.56,0.40,0.28) L0.43 | (0.86,0.58,0.11) L0.61 |
| glow_pool_front_wide | L0.37 | L0.32 | (0.64,0.40,0.10) L0.43 |
| glow_kick_mid | L0.42 | L0.38 | L0.45 |
| glow_pool_mid | (0.65,0.43,0.19) L0.46 | (0.46,0.31,0.21) L0.33 | (0.67,0.42,0.10) L0.45 |
| glow_east_plinths_hi10 | L0.60 | L0.53 | (0.89,0.64,0.19) L0.66 |

- **Saturation** (mean HSV S), pool front: Blender 0.76, before 0.54, after 0.89.
- **White clipping** (all channels >= 0.9): 0 % in every glow region. The c% in region_stats is the red channel
  alone, which is expected for saturated amber.
- **Whole-frame mean** (Unreal after / Blender): C1 ref aspect 0.147 / 0.155, C1 0.141 / 0.153, C3 0.179 / 0.196,
  C4 0.148 / 0.136, C5 0.126 / 0.110, C10 0.147 / 0.153, CW 0.106 / 0.108, CX 0.107 / 0.092, CG 0.143 / 0.121.
- **Hot amber pixels** (max > 0.5, saturation > 0.6), before -> after: C10 10.1 -> 12.0 %, C3 8.6 -> 9.5 %,
  CW 2.4 -> 3.7 %, CX 2.2 -> 3.6 %. White share is unchanged in every view.
- **Sheets:** `unreal/compare/C1_glow_blender_before_after.png` (crop), `reference_blender_unreal_C1.png`, and
  `<cam>_blender_vs_unreal.png`.

**Open**
- The hottest rows beside the shoe read yellow-amber (0.99, 0.89, 0.35) where Blender's read orange-cream. Unreal's
  pool is a little tighter than Blender's soft halo. The glow also lights the lowest part of the plinth sides (the rects
  cast no shadows, as in Blender).
- Not addressed here: the case-top LED strip (M_AK_HLedStrip 0.6) stays dimmer than Blender (hi10 L 0.68 against
  0.81), and the pre-existing darker lantern paper in the new C1 framing (L 0.35 against 0.47).

## 2026-09-28: Rear dais made live (night_live4) + Unreal night rebuild

User: "review the back part of the armory. The reference seems to have more depth to it.. like more steps and also a
showcase on both left and right corners. Also the lanterns used in the reference in the back part look like the ones in
the front." The rear dais round 3 test-copy result (b9, `WorkFiles/armory/hero/room_preview/rear/b9`; blind judge
6.5/10, no blockers) was built live under the ArmoryKit lock (claimed 21:28, released 21:32, before Unreal). The script
edits were already live in `Scripts/armory/`. No MCP was used.

**What b9 changes (live now):** one continuous 6-riser flight (0.15 m risers, 0.42 m going, Y 12.30 to the deck lip at
Y 14.40, +0.90) with LED lines under every nose except the emblem riser; the low black-lacquer stair cheeks
(`SM_AK_StairCheek`) whose front ends are the newels; all four rear lanterns are the developed `SM_AK_Lantern` design,
uniformly scaled (`SM_AK_Lantern_M` x0.90 on the deck, `SM_AK_Lantern_S` x0.65 on the cheeks; same mesh design, not a
redesign); terraced, panelled side zones (`SM_AK_Platform_Side_19`); the recessed corner showcases
(`SM_AK_H_CornerShowcase`, empty, backlit `T_AK_HShowcasePanel`); the tall painting sheet regenerated for the new paper
(`T_AK_HPaintingTall`).

**Textures.** `T_AK_HPaintingTall_*` (`tex_backwall.py tall`) and `T_AK_HShowcasePanel_*`
(`tex_rear_alcove.py HShowcasePanel`) were written into `Exports/ArmoryKit/Textures` by their own scripts; all six files
are byte-identical (md5) to the test copy's `rear/Textures` sets.

**Live build with export** (`build_armory_kit.py`, no flags): QA 108 pieces, hard fails 0; 108 FBX exported;
`ArmoryKit.blend` saved with 571 instances (was 577); 106 lights, 125 materials, 50 hero-mapped meshes. New FBX:
SM_AK_Steps_22, SM_AK_Platform_Edge_22, SM_AK_Platform_Side_19, SM_AK_StairCheek, SM_AK_Lantern_M, SM_AK_Lantern_S,
SM_AK_H_CornerShowcase. Build log: `renders/night_live4/build_log.txt`.

**Orphaned FBX** (not in the live layout.json) went to the Windows Recycle Bin (all five are also in git history):
SM_AK_H_NewelLantern, SM_AK_LanternPedestal, SM_AK_Platform_Edge_2x1, SM_AK_Steps_2, SM_AK_WallPanel_Lit_190.
`Exports/ArmoryKit` holds exactly the 108 layout pieces.

**Walk check (live blend):** passed; every route clear, including the new rear routes (up the flight to the hero table,
onto both side terraces, to both rear alcoves and both corner showcases); both controls blocked (case 1 at (6.0, 2.75),
stone lantern at (7.58, -7.3)); entry_steps_ok. Largest step up on the rear routes 0.15 m. Log:
`renders/night_live4/walk_log.txt`.

**Renders** (Cycles 96 samples, night): `renders/night_live4/` C1, CX, C10, C3, CW, CG at 1600 x 900;
`night_live4/ref_aspect/` C1 at 1448 x 1086. Sheets in `night_live4/compare/`:
`C1_ref_vs_night_live2_vs_night_live4.png` (1448 x 1086 panels), `..._1600x900.png`, and
`<cam>_night_live2_vs_night_live4.png` for CX, C10, C3, CW, CG.

Whole-frame mean display luminance, night_live2 -> night_live4: C1 0.153 -> 0.162 (ref aspect 0.155 -> 0.160),
CX 0.092 -> 0.093, C10 0.153 -> 0.178, C3 0.196 -> 0.229 (the lit flight fills the view), CW 0.108 -> 0.114,
CG 0.121 -> 0.121.

### Unreal night rebuild (21:33-21:37, all steps exit 0)
No ArmoryLab editor was open and no other Unreal process ran. The Blender night baseline for `ak_image_stats.py` /
`ak_compare_sheet.py` is now `renders/night_live4`; views it lacks (C4, C5) fall back to `night_live2` (`bl_file()`).

| Step | Result |
|---|---|
| import | 108 meshes, 105 textures; stale deleted: the 5 orphaned meshes above, the unused `T_AK_HEntRushK_*` / `T_AK_HEntTimberL_*` (replaced by the new mat's sets in the previous build) and `T_AK_HNicheWashiRoom190_BC` |
| materials | 10 masters, 125 instances, 108 meshes |
| level | 571 actors; bounds gate max 0.0047 cm; 104 lights; setp_failed empty |
| verify (fresh process) | Gates 1-7 all pass |
| manny / character | Pass |
| walk | passed; every route clear; both controls blocked; entry_steps_ok |
| capture | 10 frames (`unreal/captures/`) |
| stats / compare | `unreal/capture_stats.json`, `unreal/compare/reference_blender_unreal_C1.png`, `<cam>_blender_vs_unreal.png` |

Whole-frame mean (Unreal / Blender night_live4): C1 ref aspect 0.155 / 0.160, C1 0.153 / 0.162, C10 0.191 / 0.178,
C3 0.232 / 0.229, CW 0.119 / 0.114, CX 0.110 / 0.093, CG 0.144 / 0.121 (C4 0.149 / 0.136 and C5 0.127 / 0.110 against
night_live2). C1 ref aspect, rear band (x 300-1148, y 0-330): L 0.164 / 0.151; the flight (x 560-890, y 220-330)
L 0.206 / 0.207; painting box L 0.27 / 0.20 (Unreal's painting and rear screens read brighter and browner).

**Open (b9 judge, 6.5/10; not addressed in this build):**
- The rear bay reads about 1.25x too large / too close from the entrance (flanking posts ~500 px apart in C1 against
  ~365 px; painting ~175 x 157 px against ~145 x 115). Push the back wall north or narrow the centre bay.
- The wing fronts carry full-width glowing tread bands (bleachers, very visible in C3); the reference has plain dark
  panelled plinth fronts on the wings and the stepped flight only between the flanking posts.
- The deck strip in front of the hero table is thin; the reference sets the table, vases and lanterns further back.
- The painting is near square (~1.1:1) inside a projecting portal with a lit lintel; the reference is landscape
  (~1.26:1) in a recessed bay under the coffered ceiling.
- The corner showcases read as freestanding tall vitrines; the reference has shallow lit wall niches.
- The stair-foot lanterns sit on lower pedestals than the reference's post-style ones, slightly further out.
