# Kit 10: modern props. Build notes

## Stage: BUILD (2026-09-27)

Blender only (headless, `--factory-startup`). No Unreal in this run. Lock `DojoModernProps` was claimed for the run and released at the end.

### Files
- **Scripts:** `Scripts/dojo/props/modern/`
  - `make_modern_textures.py`: numpy textures.
  - `modern_lib.py`: geometry builder and materials.
  - `build_modern_props.py`: build, QA, export, layout and measure.
  - `render_modern.py`: Cycles views, close-ups and the line-up.
  - `compose_sheets.py`: the model sheets and the reference crops.
- **Blend:** `Assets/Dojo/ModernProps.blend`. There is one collection per prop, under `ModernProps`.
- **Exports:** `Exports/DojoKit/Props/modern/SM_DKP_Modern_*.fbx` (10 files).
  - The pole also has `SM_DKP_Modern_UtilityPole.sockets.json`.
  - Textures are in `Textures/T_DKP_Modern_<Set>_{BC,N,ORM}.png` (9 sets, 27 PNGs). The normals are DirectX.
- **Data:** `layout_modern.json` (28 instances), `measure.json`, `qa_report.json`, `export_report.json`, `textures_report.json`.
- **Renders:** `renders/r0/`.

### Assets (every prop is its own mesh, UCX, FBX and collection)

| Asset | Size (m) | Tris | UCX | Class |
|---|---|---|---|---|
| SM_DKP_Modern_VendingMachine | 0.92 x 1.03 (0.80 body + 0.21 hood) x 1.75 | 1966 | 2 | climb prop |
| SM_DKP_Modern_ACUnit_Roof | 1.22 x 2.00 x 1.52 (top +4.75 when placed) | 6204 | 2 | climb prop |
| SM_DKP_Modern_ACUnit_Wall | 0.78 x 0.28 x 0.54 casing, on brackets | 4112 | 1 | thin / wall dressing |
| SM_DKP_Modern_WallLamp | 0.40 m reach, 0.40 m lantern | 1496 | 1 | thin |
| SM_DKP_Modern_StreetLamp_A | 3.00 tall | 2292 | 4 | thin |
| SM_DKP_Modern_StreetLamp_B | 2.50 tall | 1384 | 3 | thin |
| SM_DKP_Modern_UtilityPole | 8.00 above grade (+0.30 below), crossarm 1.90 | 3844 | 2 | thin |
| SM_DKP_Modern_JunctionBox | 0.29 x 0.19 x 0.80 | 1556 | 1 | thin |
| SM_DKP_Modern_Wire_Span25 | 25 m span, 0.45 m sag | 588 | 1 | wire (NoCollision) |
| SM_DKP_Modern_Wire_Drop12 | 12 m, falls 3.0 m, 0.25 m sag | 588 | 1 | wire (NoCollision) |

Pivots:
- **Floor props:** the base centre on the ground.
- **Roof AC:** the centre of the front edge of the footprint, on the roof surface.
- **Wall props:** on the wall plane (y = 0). For the lamp it is the back-plate centre; for the wall AC it is the bracket arm top; for the junction box it is the loop bottom (the loop's lowest point is +0.03).
- **Wires:** the first attachment point. The span runs along +X.

### Gates
- `qa_check` found **0 hard fails** across 10 props (509 checks). `require_uv1` was on.
- `uv0_tile_range` and `uv_no_overlap` are waived, as in the ground kit, because UV0 is a tiling channel.
- UV1 is a lightmap pack: it is non-overlapping and stays inside 0-1. Both of those were checked.
- The exports went through `pipeline.export_fbx` with no warnings.

### Spec rules and deviations (all measured; see measure.json)
- **Vending machine, R3 (a flat top at least 1.0 m deep):**
  - The sheet's body is 0.80 m deep. It keeps that body and adds a sheet-steel rain hood that projects 0.21 m over the front.
  - The flat top at +1.75 is therefore 1.008 m deep as rendered and 1.018 m deep in collision.
  - The collision is 2 hulls: the body block, plus a slab for the hood.
  - For comparison, the grey-box's 0.8 m box already mantled in GASP (depth 80 cm).
  - If the hood's 0.2 m overhang confuses GASP's ledge trace, the fallback is one full 0.92 x 1.02 x 1.75 box.
  - Placement: (12.45, 0.42), rot 180. The back is 2 cm off the wall face and the hood front sits at Y 1.038.
- **Roof AC, spec 5.1:**
  - The prop is built to the spec's gameplay size, as asked: a 1.2 x 2.0 m footprint and a flat top at +4.75.
  - With the front feet on the lower roof at Y 22.0 (+3.2332, measured) the top is at 4.750.
  - The standable flat top is 1.2 x 1.066 m (render) or 1.12 m (UCX), and runs from Y 22.02 to 23.10. It stays entirely outside the upper eave line (Y 23.1), so R3 holds.
  - The rear 0.9 m, under the eave where the headroom is 0.75 m, holds only the runners, the duct and the conduit. They lie on the tiles and fix to the hall wall at Y 24.0.
  - The casing clears the roof by 0.127 m at its rear edge. The frame rail clears the runner by 3.4 mm at the rear leg.
  - **Conflict:** the grey-box (kit 0) moved its AC to a 1.2 x 1.0 m unit with its top at +5.10, a GASP-measured deviation. This asset follows the spec as the task asked. Kit 0 or the user must choose. A +5.10 variant only needs taller front legs, one parameter (`AC_TOP`).
- **Utility pole height:**
  - The spec gives no height, and the sheet's "4.0 m" is not a believable pole.
  - The build uses 8.0 m above grade, with 0.30 m buried and the crossarm at +7.30 to 7.40.
  - The wire attachment points are SOCKET_ empties: Wire_A-D at the insulator tops (+7.532), and Drop_1 and Drop_2 at the spool racks.
- **Collision classes (spec 5.3):**
  - Climb props block pawn and visibility and ignore the camera.
  - Thin uprights (lamps, pole, junction box, wall AC) block the pawn only.
  - Wires carry a UCX only to pass the pipeline gate. The layout sets them to NoCollision.
- **IP (style guide section 10):** there is no text, logo, brand, number or crest anywhere. Every panel is blank, and the vending display is a plain backlit diffuser.

### Materials
- **Generic (for the look pass to unify):** Galvanised, IronDark, PoleWood, Concrete, PaintGrey, LampGlass, Porcelain, Rubber, Cable, Chrome, Copper, PlasticCream.
- **Unique:** PaintTeal (vending), PaintWhite (AC casings, vending panels), CoilFins, VendPanel, ButtonLit, FanDark, PlasticDark, PipeInsul.
- **Emissive slots:** LampGlass (warm amber, emission 2.6), VendPanel (the BC doubles as the emissive colour, x0.8) and ButtonLit.
- **Texel density (measured):**
  - 5.03-5.40 px/cm on the 1024 px / 2 m tiling sets.
  - CoilFins is 20.48 px/cm (512 px over 0.25 m, which gives 2.5 mm fins).
  - VendPanel is 8.4 px/cm (unique).

### Layout (grey-box frame; UE (x*100, -y*100, z*100), yaw = -rot_z)

**From the spec:**
- Vending machine at (12.45, 0.42, 0), rot 180.
- Roof AC units at (15.6 / 28.4, 22.0, 3.2332).

**Proposed:**
- **Wall AC:** residence at (40.8, 27.4, 1.55).
- **Wall lamps:** storehouse and residence at X 6.6 / 37.4, +2.45.
- **Junction box:** storehouse at (2.2, 27.4, 0.30).
- **Street lamps:** A outside the gate at X 17 / 27, Y -4.5; B in the south yard strip at X 10.9 / 33.1.
- **Poles and wires:**
  - Poles at X -15.5 / 9.5 / 34.5 / 59.5, Y -7.0, rot 90: 25 m spans, symmetric about X 22.
  - 12 span conductors.
  - 1 service drop to the gatehouse, scaled from the 12 m design span.

### Renders (Cycles, OIDN, 48-96 samples, RTX 4070 SUPER) and review rounds
- **Sheets, close-ups, line-up and side-by-sides:** 10 sheets, 11 close-ups, 2 sunset line-ups and 10 side-by-sides, all in `renders/r0/`.
- **Round 1:**
  - The silhouettes were missing because of a stale world matrix.
  - The studio light was too hot: paint washed out and the pole looked pale.
  - Round 1 found the teal too pale. It was deepened to `#2C6F75`, closer to the sheet's machine.
- **Round 2:**
  - The pole timber was darkened.
  - The insulators were darkened to a brown glaze.
  - A grey painted box was used for the junction box, as on the sheet.
  - The glass was made amber.
  - The pole's buried butt was hidden behind a holdout.
  - The line-up got a gradient sky and a warmer sun.
- **Round 3:**
  - The roof-AC stand became dark painted steel, like the sheet's dark stand.
  - The side-view figure now stands on the roof.
  - The wall-prop 3/4 views are framed on the prop.
  - The vending display emission went down to 0.8.

### Open issues
- **AC top height:** the spec's +4.75 against the grey-box's measured +5.10 (see above).
- **Vending hood and GASP:** the hood's GASP behaviour is untested because there is no Unreal in this run.
- **LODs:** none are exported. The style guide says props ship LOD0-2 or use Nanite. These props are all under 6.3k tris.
- **Wire sheets:** a 13 mm wire is under one pixel at sheet scale, so the wire model sheets are near-empty. The wires read in the line-ups.
- **Vending display:** it reads as a warm white diffuser, where the sheet's display window is teal-tinted.
- **Sheet differences:** the sheet's pole shows several crossarms and many wires; this build has one crossarm and 2 racks. Wall lamps hang at the arm's end.


## Stage: FIX ROUND f1 (2026-09-27)

Blender only (headless, `--factory-startup`), no Unreal. Lock `DojoModernProps` claimed for the stage and released at the end. The r0 scripts were edited in place, so the r0 renders stay in `renders/r0/` for comparison. The f1 renders are in `renders/f1/`.

### Measurer fixes
- **F1 (wall props on the wall):** the wall AC, both wall lamps and the junction box now sit at Y 27.94, the grey-box `SM_DGB_Storehouse` / `SM_DGB_Residence` south wall face (from `layout_greybox.json`).
  - Placements: WallLamp (6.6 / 37.4, 27.94, 2.45), ACUnit_Wall (40.8, 27.94, 1.55), JunctionBox (2.2, 27.94, 0.30).
  - **Eave check** (in `measure.json` `wall_mount_check` and `layout_modern.json` `eave_check`):
    - The lamp top is at +2.75. The eave underside is at +3.05 (grey-box roof bbox min at Y 27.4), which leaves **0.30 m** of clearance, so the 2.45 m mount holds.
    - The lantern bottom is at +2.11.
    - The lantern reaches Y 27.29, 0.11 m past the eave line. It stays below the eave, so nothing collides.
    - The wall AC top is at +2.105 and the junction box top at +1.10.
- **F2 (wire UCX):** every wire (Span25, Drop12 and the new Telecom25) now carries a **token 4 cm block** at its first attachment point (UCX 0.04 x 0.04 x 0.04 m, measured), so a wire can never become an invisible wall. The class stays NoCollision.
- **F3 (tri budget):** `qa_check` now runs with `budget_tris=5000` on every prop and every LOD.
  - The roof AC dropped from 6204 to **3460** tris: the modelled guard rings (about 2.8k) became an alpha-masked grille disc.
  - Every prop is under 5000. The largest is the pole at 3954.
- **F4 (LODs):** every non-wire prop now ships LOD0-2 as a LodGroup (`decimate_lods` 0.5/0.25 + `make_lod_group`; UCX renamed `UCX_<base>_LOD0_NN`).
  - LOD1/2 get a repacked UV1: Collapse had pushed UV1 slightly outside 0-1. LOD QA is 0 hard fails and the build refuses to export otherwise.
  - Sockets travel in the `.sockets.json` sidecar, with clean `ue_socket` names (Wire_A..H, Drop_1/2, Telecom; the lamp wire eyes) and `lod_screen_sizes` 1.0/0.5/0.25.
  - **Nanite statement (STYLE_GUIDE 7):** enable Nanite on the opaque pieces over 2k tris (pole 3954, roof AC 3460, wall AC 2232, vending 2014). Keep LOD0-2 as the fallback.
  - Two slots need care: the FanGrille is masked, and the LampGlass is translucent if the glass instance is used. Keep either on the fallback path if Nanite shows problems with them.
  - **Wires:** single LOD (636 / 836 / 1656 tris, thin 6-sided tubes that Collapse would break), no Nanite.
- **F5 (VendPanel):** the display texture was rebuilt and is no longer flat.
  - It is a teal-tinted window with two shelves of plain, blank dummy cans, 0.66 x 0.33 m, 512x256.
  - **ORM.R is real AO** baked from the display's own height field (cans, shelf lips, recess edge): mean 0.845, min 0.15. The N map carries the same relief.
  - Emission is BC x 0.7.
- **F6 (AC top height):** a decision, not changed here. The build stays at the spec's +4.75 (`AC_TOP`, one constant).

### Judge blockers
- **Wire sheets:** the wire model sheets now draw the conductor 8x thicker from its stored centreline, as a labelled review-only preview.
  - The r0 sheets were also blank for a second reason: the below-grade holdout box hid everything under z 0, which is where a sagging wire hangs.
  - New real-thickness close-ups: `wire_span_end_insulator` (tie wrap on the insulator top), `wire_drop_deadend` (preformed dead-end grip + clevis loop at the spool rack) and `wire_midspan_telecom` (messenger + 2 cables).
- **Roof AC depth:** confirmed that 2.0 m is the **stand footprint**, not the top.
  - The climbable top is the condenser casing: 1.192 x 1.066 m in the render, 1.12 m in the UCX, flat at +4.75. It runs from Y 22.03 to 23.09, ending at the upper eave line.
  - The rear 0.9 m lies under the upper eave. The headroom there is 0.75 m at Y 23.1 and 1.17 m at the wall, so a 1.8 m capsule cannot stand there whether or not the top continues.
  - The top is therefore not extended, and R3 holds with 1.07 / 1.12 m.
- **Pole height:** the spec gives no height, so the pole stays at **8.0 m** (the sheet's 4.0 m is not a believable distribution pole). This is recorded as a user decision.

### Look deltas
- **Lanterns (all three):** new hexagonal lantern.
  - Six seeded amber glass panes that taper toward the bottom. `LampGlass` is now a unique 256x512 texture set: a bubble normal, soot at the top, and a warm falloff from a hotspot at the bulb height. BC doubles as the emissive colour, x2.2, with 0.45 transmission in Blender.
  - A visible pear bulb (`BulbLit`, emission 14, warm) on a socket inside.
  - A flared hex hood with a ball finial, and a hex bottom tray and drop.
  - Review renders add point lights at the bulbs as stand-ins for the in-game light components. They are never exported.
- **WallLamp:** a dark timber back-board and arm with iron straps, L-plates and a straight iron strut. The faceted scroll is gone.
  - The lantern is now 0.33 m across the glass corners (was 0.25). The hood is 0.40 m across the corners.
  - Reach is 0.48 m to the lantern axis. It could not be the sheet's 0.40 because the larger hood needs clearance from the strut.
- **StreetLamp_A:** a capital and finial on the post top. The lantern hangs close under the post top from a 0.30 m bracket with a smooth 16-segment quarter-round strut. A wire eye on the head (SOCKET Wire). No scroll.
- **StreetLamp_B:** a top crossbar with two wire eyes (SOCKETs Wire_L / Wire_R) and a spike, plus a smooth quarter-round bracket.
- **VendingMachine:** front redrawn to the sheet.
  - An arch-topped (rounded top corners, r 0.085 m) display window in a white surround, then a white band with a groove line, 7 blank lit buttons and a small chrome button.
  - A white panel with a **chrome** coin cluster (slot bezel, return lever, 2 lit buttons).
  - A lower teal zone with a chrome-framed dispense bay and chrome flap, a lit round button and a chrome coin-return cup. The lock and handle are on the right teal strip.
  - **No canopy:** the flush top cap overhangs the door front by **1.5 cm** (render top) / 2 cm (bbox).
  - **The R3 depth now comes from the cabinet:** the body is 1.00 m deep, where the sheet shows 0.80 (spec wins). The flat top is 1.016 m deep in the render and 1.026 m in the UCX.
  - One flush collision box. Layout: centre Y 0.526, back 2 cm off the wall.
- **Weathering (pack-wide):** PaintTeal, PaintWhite and PaintGrey are now **height-anchored**.
  - U tiles seamlessly. V runs 0 to 2 m above each prop's painted base; the builder offsets V per asset with `Asset.vbase`, and top faces use the clean mid band.
  - That allows base grime and splash, more sun fade higher up, 72 rust runs bleeding down from fastener/seam spots, more chips, and peeled patches showing primer and rust.
  - The textures report seam scores along V around 5-9, which is expected; the U columns are seamless (0.8-1.2).
- **Fans (both AC units):**
  - 3 twisted, pitched and swept blades (5 stations, 42 to 18 deg pitch) with a hub cap.
  - A darker recessed shroud.
  - A dense alpha grille, `T_DKP_Modern_FanGrille` (11 rings, 14 spokes, RGBA, masked, two-sided), plus a wire rim and 4 clips.
- **Roof AC:**
  - The service valves (galvanised bodies, copper caps) and the insulated line set are on the **+X side**, visible from the front and courtyard. They run down and back under the rear of the unit into the cream line-set cover.
  - A flexible wiring whip loops from the service port to a galvanised box, with the conduit continuing up the slope.
- **UtilityPole:**
  - Warmer and darker weathered timber: orange-brown, sun-silvered patches, 22 drying checks.
  - A **second, lower crossarm** at +6.75 with 4 more insulators (Wire_E..H), so 8 conductors.
  - A telecom messenger clamp (SOCKET Telecom) and a hanging slack coil.
  - A riser cable strapped down the +X side to a small grey pole box at +2.6.
  - 9 step bolts.
- **New separate assets** (per the user's one-asset-per-prop rule; pivot = the pole's base centre, so they take the pole's own transform):
  - `SM_DKP_Modern_PoleTransformer`: 0.40 m can, hanger brackets, 2 bushings with jumpers to lower-crossarm insulators F/G. 1044 tris.
  - `SM_DKP_Modern_PoleGuy`: a band at +6.4, a strand to an anchor 3.6 m out (29.1 deg from vertical), preformed grips, a 1.8 m cream guard, and an anchor rod with a concrete collar. 472 tris; the UCX is the guard only.
  - `SM_DKP_Modern_Wire_Telecom25`: messenger + 24 mm + 18 mm cables, 0.60 m sag, suspension clamps. 1656 tris; token UCX.
- **JunctionBox:**
  - The top conduits run straight up in line with the box, with a strap clamp on standoffs.
  - A strap clamp on the bottom conduit.
  - A rust line at the lid seam (new flat material `M_DKP_Modern_Rust`).
  - The J-loop now ends in an open bushing with a dark mouth instead of a ball.

### Layout (46 instances)
- **Changed:** the wall props at Y 27.94, and the vending centre at Y 0.526.
- **New:** 8 conductors per span (A..H) plus 1 telecom per span, the transformer on the X 9.5 pole, and guys on the end poles (X -15.5 aimed west, X 59.5 aimed east).

### Gates and numbers
- QA 0 hard fails (767 checks), `budget_tris=5000`, `require_uv1`. The waivers are unchanged (UV0 tiling channel).
- LOD0/1/2 tris:

| Asset | LOD0 | LOD1 | LOD2 |
|---|---|---|---|
| VendingMachine | 2014 | 1006 | 502 |
| ACUnit_Roof | 3460 | 1730 | 865 |
| ACUnit_Wall | 2232 | 1116 | 557 |
| WallLamp | 982 | 490 | 244 |
| StreetLamp_A | 1830 | 914 | 456 |
| StreetLamp_B | 1626 | 812 | 406 |
| UtilityPole | 3954 | 1976 | 988 |
| PoleTransformer | 1044 | 522 | 260 |
| PoleGuy | 472 | 236 | 118 |
| JunctionBox | 1260 | 630 | 314 |

- **Texel density:**
  - 5.03-5.45 px/cm on the tiling sets.
  - CoilFins 20.48; FanGrille 7.5 (roof) / 12.9 (wall).
  - VendPanel 10.7; LampGlass 14.7-19.9 (unique maps).
- **Materials:**
  - Generic, for the look pass: Galvanised, IronDark, PoleWood, Concrete, PaintGrey, LampGlass, BulbLit, Porcelain, Rubber, Cable, Chrome, Copper, PlasticCream, Rust.
  - Unique: PaintTeal, PaintWhite, CoilFins, VendPanel, FanGrille, ButtonLit, FanDark, PlasticDark, PipeInsul.
  - Emissive slots: LampGlass, BulbLit, VendPanel, ButtonLit.

### Renders (Cycles, OIDN; 48 spp for the views, 64 for the close-ups, 96 for the line-up)
- `renders/f1/`: 13 sheets, 13 side-by-sides, 20 close-ups and 3 sunset line-ups (`lineup_sunset`, `_left`, `_right`).
- The views, close-ups and line-up ran as 5 parallel Blender processes on the GPU.

### Open issues
- **F6:** the AC top (+4.75 spec vs +5.10 grey-box) is for the user or kit 0 to choose. A rebuild only needs `AC_TOP`.
- **Pole height:** 8.0 m is unconfirmed by the user.
- **Vending depth:** 1.0 m (sheet 0.8) is untested in GASP. The grey-box box is 0.8 m deep.
- **Glass in Unreal:** choose an opaque emissive instance (the hotspot is in the map) or translucent glass.
- **Masked materials:** the grille needs a masked, two-sided instance.
- **Studio render look:** in the studio renders the PaintGrey transformer can reads close to off-white, and the pole timber reads lighter than in the sunset light.
- **Insulators:** the glossy coat on the insulators gives a white rim at grazing angles in the close-ups.


## Stage: ROUND 2, library material + shape pass (2026-09-28, group B, Blender only)

Lock `DojoModernProps` (claude) for the stage; no Unreal, no DojoLab writes. Renders: `renders/r2/` (13 sheets, 13
side-by-sides, 30 close-ups, 3 sunset line-ups). f1 scripts backed up in the session scratchpad before editing.

### Library applied (Scripts/dojo/materials v1.0.0) where it covers the material
| Was | Now | UV0 |
|---|---|---|
| M_DKP_Modern_IronDark (every stand, lamp post, lantern, bracket, vending base) | M_DJ_Iron (bare 0.95-1.0 metal, rust 0) | `box_uv` |
| M_DKP_Modern_PoleWood (pole, crossarms) | M_DJ_TimberAged + End | `grain_uv` (the pole wraps round its axis, crossarms planar) |
| wall-lamp back-board | M_DJ_TimberDark + End | `grain_uv` |
| M_DKP_Modern_LampGlass (wall lamp, street lamps A / B) | M_DJ_GlassAmber (0-1 per pane: the library's bulb hotspot) | explicit 0-1 per pane |
| M_DKP_Modern_VendPanel | M_DJ_VendingPanel (blank backlit diffuser) on the arch-shaped window, 0-1 over the window box | explicit |
Paint (teal / white / grey), galvanised, concrete, coil fins, fan grille, chrome, copper, rubber, plastics, porcelain,
cable, bulb and button emissives stay kit-own: the library has no such sets. `bake_wear` on every non-wire prop;
`timber_bands.calm_bands` (Scripts/dojo/props/stone/timber_bands.py) keeps each timber member on the library tile's
mid-tone rows.

### Shape fixes
| Item | Done | Measured |
|---|---|---|
| Vending depth | back to the SHEET's 0.80 m: the whole machine fits X +-0.45 x Y +-0.40, flush flat top +1.75 = the grey-box box (GASP route 8); layout (12.45, 0.40) rot 180, back on the wall face, no Unreal scaling | bbox 0.900 x 0.806 x 1.750 (6 mm of chrome fittings past the top lip); UCX 0.90 x 0.80 x 1.75; top 0.79 m (render) / 0.80 (UCX) deep |
| Vending display | library VendingPanel on an arch-shaped emissive window set in the white surround inside the teal door; a teal coin strip carrying the chrome coin plate, slot, return lever and two lit buttons; two lit buttons by the dispense bay (the sheet's orange pair) | - |
| Vending glow colour | NOT made 2700-3000 K: the sheet's window is a pale cyan backlit panel and the library's measured VendingPanel matches it (hue 188.8 vs 188.4 deg, dE 6.6). Warm would invent a colour the sheet does not show; kept dim (library strength 1.6 / MI 160) | flagged for the user |
| Roof AC | rebuilt at **+5.10** (AC_TOP): casing 1.20 x 1.08 x 0.877 unchanged, now on taller legs (casing bottom 0.99 above the front feet), side mid rails and a rear cross brace; runners and their rubber pads stay on the 25 deg roof plane (no Z-scale); the line set now drops to the tiles and runs up the slope | top world +5.100, flat top Y 22.026-23.092 (1.066 m render / 1.12 UCX), casing clears the roof 0.48 m at its rear, headroom under the upper eave 0.40 (the grey-box's walk-up step) |
| Fan blades (both ACs) | 9 stations, 8-point cambered section, 2 mm rounded leading edge, squared trailing edge, flat sharp-rimmed root / tip caps: no knife edges for smooth normals to average | `closeup_acroof_fan_front`, `_fan_blades_oblique`: clean |
| Wall lamp | redesigned to the sheet: wooden backplate post (0.79 m, runs 0.28 m below the lantern), iron arm reaching 0.40 m with a quarter-round strut, a 0.40 m square lantern tapering 0.21 -> 0.17 m, glass 62 % of its height, pyramid cap with finial and ring | eave clearance 0.33 m at the 2.45 mount |
| Street lamps A / B | the same square tapered lantern (the sheet's street lamps are four-sided), library glass, bulbs at the glass centre | - |
| Wires | new close-range review renders: `wire_span_close` (crossarms and the eight conductors at the insulators), `wire_span_along`, `wire_sag_midspan`, `wire_drop_close` (+ f1's three) | - |
| Utility pole | 8.0 m kept (user decision) | - |

### QA / export / Nanite
- `qa_check(require_uv1=True)`: **0 hard fails on all 13**, LOD QA 0; waivers unchanged. Budget 5000 up to 2000 tris,
  waived above (Nanite: VendingMachine 2168, ACUnit_Roof 3882, ACUnit_Wall 2610, UtilityPole 3954). Others: WallLamp
  1084, StreetLamp_A 1744, StreetLamp_B 1540, PoleTransformer 1044, PoleGuy 472, JunctionBox 1260, wires 636 / 836 / 1656.
- 13 FBX re-exported (LOD0-2 LodGroups; wires single LOD); sockets in the sidecars as before.
- Texel density: library iron 4.9-5.1, timber 5.1, paints 5.0-5.4 px/cm.

### Open
- Vending glow colour (above): the user decides warm vs the sheet's cyan; a warm variant needs a tint parameter on
  M_DJ_Lib_Emissive (library owner).
- GlassAmber reads peach under AgX (library README: set the hue in the Unreal look pass).
- The showcase must re-import (AC without its Z-scale, vending without its 0.78 squeeze) and build the library instances.


## Stage: ROUND 3 LOOK PASS (2026-09-28, props track, Blender only)

Lock `DojoModernProps` (claude) for the stage. No Unreal, no DojoLab write, no commit. The material library was not
edited.

### Layout: drop the invented lamps (user decision 2026-09-28)
- Street lamps stand ONLY outside the wall on the street side, where `dojo1_reference1` shows them: two lamps flanking
  the gate approach across the road.
- **Street lamp A** keeps those two street positions: (17.0, -4.5) and (27.0, -4.5).
- **Street lamp B** is withdrawn from the courtyard. In r2 it stood at (10.9, 0.45) / (33.1, 0.45) in the south yard
  strip INSIDE the wall. No street position is left for it in the references, so it is an unplaced spare
  (`layout_modern.json` `unplaced`, round "r3").
- Wall lamps stay only on the outbuilding walls (6.6 / 37.4 at Y 27.94), where the references show them. No wall lamp
  moved.
- No short lanterns inside the gate (stone layout).

### Vending machine
Kept as r2 (user decision: sheet 11 wins over ref 1): the sheet's teal / white design and the cyan-white
`M_DJ_VendingPanel` display. No geometry change.

### Build
- `build_modern_props.py -- --no-export`: QA 0 hard fails on all 13.
- No geometry changed, so the r2 FBX in `Exports/DojoKit/Props/modern/` stay as they are (not re-exported).
- `layout_modern.json` rewritten: 2 StreetLamp_A instances, 0 StreetLamp_B, and the rest unchanged.

### Open
Judge B's modern deltas were not in this round's list:
- AC cabinet stand;
- street-lamp bronze finish, stepped plinth and finials;
- wall-lamp finial, scroll and eave flare;
- vending mid white panel width and side-panel depth.
