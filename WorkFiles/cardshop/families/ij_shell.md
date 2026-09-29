# Family ij_shell: signage, shell, entry door, lights (built 2026-09-29, cloud)

Module: `Scripts/cardshop/csk_lib/fam_ij_shell.py`, 22 item keys prefixed `ij_shell_`. Spec rows: CARDSHOP_KIT_SPEC.md
3.I I1-I5 and 3.J J1-J3. J4 (the scale figure) is dropped by the user. I opened sheets 30-34 on disk, measured them
off zoomed crops, and rendered every item against them.

**Build:** one build of all 22 keys ends `CSK_BUILD PASSED`. The house `qa_check` passes on every LOD. The kit checks
pass 23/23: `.csk.json` hashes 22/22 and the deny scan. The warnings are the house LodGroup socket drop only: those
sockets are in the `.sockets.json` sidecar.

## Meshes

| Key (`ij_shell_…`) | Mesh | LOD tris | Budget | qa | Sockets (+ `Seat`) | Hulls |
|---|---|---|---|---|---|---|
| sign_openclosed | SM_CSK_Sign_OpenClosed | 220 / 104 / 52 | 300 | PASS | Mount, Plate | 1 |
| sign_openclosed_plate | SM_CSK_Sign_OpenClosed_Plate | 132 (LOD0 only) | **150** (spec 60) | PASS | Face | 1 |
| pricetag_shelf | SM_CSK_PriceTag_Shelf | 68 | 80 | PASS | Mount, Face, Text | 1 |
| pricetag_tent | SM_CSK_PriceTag_Tent | 44 | 80 | PASS | Mount, Face, Text | 1 |
| pricetag_hook | SM_CSK_PriceTag_Hook | 84 | **90** (spec 80) | PASS | Mount, Face, Text | 1 |
| poster_a2 / poster_a1 | SM_CSK_Poster_A2 / _A1 | 92 each | 200 | PASS | Mount | 1 |
| sign_storefront | SM_CSK_Sign_Storefront | 292 / 116 / 84 | 400 | PASS | Mount, Face | 3 |
| sign_hanging | SM_CSK_Sign_Hanging | 140 (LOD0 only) | **150** (spec 100) | PASS | Mount_L, Mount_R | 1 |
| wall | SM_CSK_Shell_Wall_2000 | 32 | 600 | PASS | Snap_L, Snap_R | 1 |
| wall_window | SM_CSK_Shell_Wall_Window_2000 | 384 / 120 / 108 | 600 | PASS | Snap_L, Snap_R | 4 |
| wall_window_glass | SM_CSK_Shell_Wall_Window_2000_Glass (new) | 48 | 100 | PASS | none | 4 |
| wall_door | SM_CSK_Shell_Wall_Door_2000 | 60 | 600 | PASS | Snap_L, Snap_R, Mount_DoorFrame | 3 |
| floor | SM_CSK_Shell_Floor_2000 | 44 | 600 | PASS | Snap_L, Snap_R | 1 |
| ceiling | SM_CSK_Shell_Ceiling_2000 | 236 / 76 / 44 | 600 | PASS | Snap_L, Snap_R | 1 |
| door_entry | SM_CSK_Door_Entry (the leaf) | 360 / 172 / 64 | 800 | PASS | Handle, Sign | 1 |
| door_entry_frame | SM_CSK_Door_Entry_Frame | 384 / 184 / 64 | 400 | PASS | Door, Bell | 3 |
| light_panel600 | SM_CSK_Light_Panel600 | 140 | 200 | PASS | Mount, Light | 1 |
| light_track2000 | SM_CSK_Light_Track2000 | 272 / 80 / 12 | 300 | PASS | Mount, Head_01..06 | 1 |
| light_trackhead | SM_CSK_Light_TrackHead | 72 | **150** (split) | PASS | Mount, Tilt | 1 |
| light_trackhead_spot | SM_CSK_Light_TrackHead_Spot (new) | 200 / 120 / 68 | **250** (split) | PASS | Light | 1 |
| light_pendant | SM_CSK_Light_Pendant | 556 / 272 / 124 | 600 | PASS | Mount, Light | 2 |

**Moving parts** (`.csk.json` `parts`, with `open_ue` / `closed_ue`):

| Part | Socket | Hinge | Range | Pose |
|---|---|---|---|---|
| Plate | `Plate` (on the sign) | Z, 180° flip | 0-180° | Open/closed faces swap |
| Door leaf | `Door` (on the frame) | Z | 0-100° | Opens outward, toward +Y (the street); display pose 90° |
| Spot | `Tilt` (on the track head) | X | 0-80° | 0 = aimed level at -Y; the display pose is the sheet's 45° |

**Frames:**
- Wall-hung items (posters, the storefront sign, the window sign's suction cup): `Seat` is on the wall or glass plane,
  and the item stands out toward -Y.
- Ceiling items: `Seat` and `Mount` are the ceiling contact, and the item hangs below.
- Shell modules: end-corner pivot. The shop face is at y 0, the outside face at y 150. The floor's top and the
  ceiling grid's underside are at z 0.
- The door frame uses the wall's frame. Its pivot is the shop-face bottom centre, which lands on the wall's
  `Mount_DoorFrame` and fills the 1000 × 2200 opening exactly.
- The leaf's `Sign` socket takes the I1 sign's `Seat` on the shop side of the glass.
- `Light` sockets aim their +X along the beam.

## Construction (all real geometry)

- **I1 sign** (sheet 30):
  - A 300 × 150 × 5 plate with R6 corners and two Ø9 cord holes. The print is OPEN on the front and CLOSED on the
    back.
  - A clear suction cup (Ø70, measured) with a pull tab, and a round-topped J hook.
  - A black cord runs from the hook to a knot over each hole, then down both faces of the plate into the hole.
- **I2 price tags** (sheet 30):
  - **Shelf clip:** an extruded clip profile with a flange over the shelf top, a tongue down the shelf face, a front
    panel 13 off the face and a J curl holding the white insert.
  - **Tent:** a clear A-frame (faces leaning 20°) with a folded white insert.
  - **Hook plate:** a clear rounded plate, the insert inside it, and a round clip barrel on its left edge.
- **I3 posters** (sheet 31): four mitred black bars, 20 face and 16 deep, with a rounded outer edge. Each stops short
  of the mitre plane, so the mitre shows as a 0.35 line. The poster sits 3 below the face.
- **I4 storefront sign** (sheet 31): a black box with a 12 bezel over a diffuser recessed 8 (print + emissive). There
  are two wall plates outboard of the ends, each with two square arms into the box end and two bolt heads.
- **I5 hanging sign** (sheet 30): a thin aluminium frame round a two-sided printed panel. Two steel cables have ceiling
  cups and grippers.
- **J1 shell** (sheet 32):
  - **Walls:** a plaster slab with black end bands; a 150 black skirting, 10 proud, on the shop face.
  - **Window:** a 1600 × 2400 black frame on a 300 sill. The mullion stands 35% across and the transom 25% down;
    both views of the sheet agree. The 4 panes are in the `_Glass` mesh.
  - **Door:** a 1000 × 2200 opening starting 600 from the left end (both views), with black-lined reveals.
  - **Floor:** a 20 mm slab with a 1.5 chamfer (the "fine join").
  - **Ceiling:** one closed solid. A 2 × 2 grid of tiles sits in 3 mm recesses in a 24 mm T-grid, with half bars on
    the edges.
- **J2 door** (sheet 33):
  - **Frame:** 47 jambs and an 89 header (the printed 1000 / 900 and 2200 / 2100 fix these). It has a 15 stop, a
    stainless threshold plate, the hinges' frame leaves, and a bell on a round backplate centred on the header's
    street face.
  - **Leaf:** 80 / 80 / 100 stiles and rails, a glazing bead, a 10 glass pane, a 760 stainless pull bar on two posts,
    and 3 knuckles on the hinge axis.
- **J3 lights** (sheet 34):
  - **Panel:** an aluminium edge frame round a diffuser (`M_CSK_LED`).
  - **Track:** a channel with a bottom slot, lips, a white conductor strip and end caps.
  - **Track head:** a round adapter and a stem. The spot is a Ø70 × 150 body with a bezel and a recessed reflector
    cone plus lens (`M_CSK_LED`), and a knuckle barrel 50 from the rear.
  - **Pendant:** the dome profile was measured row by row off the sheet, as one closed thin shell (1.2 wall) with a
    lit inside. It hangs on a collar, a 1000 cord and a Ø100 canopy.

## Deviations from the spec, and why

1. **I1 slots are PVC + Cord.** The spec says "chain + suction hook, Metal"; sheet 30 draws a black cord on a clear
   cup, and the picture wins.
2. **The I1 plate budget is 60 → 150,** for the R6 corners and two cord holes. The I5 budget is 100 → 150, for two
   suspenders with cups and grippers. The I2 hook budget is 80 → 90, because a 6-sided barrel read as a hex nut.
3. **I2 shelf clip is 76 × 30 × 48 overall.** Sheet 30's clip hooks over the shelf edge, with a 47 front panel
   holding a 32 insert. The spec's 76 × 32 × 2 is taken as the insert. `Mount` is the shelf's front top edge. The
   small grey spacer in the side view is not modelled, because it is hidden from the front.
4. **I5 is 600 × 145** (spec 600 × 200 E). Sheet 30's panel reads 4.15 : 1.
5. **I3 frames:** the A2 / A1 call-outs are drawn to the frame's outer edge, so the visible poster is 380 × 554 and
   554 × 801.
6. **I4:** the box stands 12 off the wall (the plate thickness); the pictures read close to the wall. The arms are
   100 long (sheet 84-115). The footprint with brackets is 2199 wide.
7. **J1 Window glass is a new mesh,** `SM_CSK_Shell_Wall_Window_2000_Glass`, per the fixed-pane rule (4.5).
8. **J1 Wall_Door gets a new `Mount_DoorFrame` socket.** Sheet 32's black band round the door opening is the J2
   frame itself: 1000 × 150 × 2200 fills the opening exactly. The bare wall has black reveals only.
9. **J1 skirting is on the shop face only,** because the sheet never shows an outside face. The window frame depth
   (70, centred) and pane thickness (10) are E.
10. **J2 jambs are 47,** where the picture reads 85. Printed call-outs win. The bell is scaled to the header, as the
    sheet's bell is as tall as the header. The I1 sign sits a little lower than drawn, so its cup is on glass, not
    on the top rail.
11. **The J2 hinge side follows the front view and the notes:** hinges on the right seen from the pull (street)
    side. The sheet's top and 3/4 views draw the other hand.
12. **J3 track rail is 20 wide × 35 tall.** The section inset and the 35 call-out say so; the spec's 35 × 20 is E and
    the picture wins. The rail has no `Light` socket, because the heads carry the light.
13. **J3 TrackHead is split** into `SM_CSK_Light_TrackHead` (adapter + stem, budget 150) and
    `SM_CSK_Light_TrackHead_Spot` (the tilting body, budget 250). That is the spec's 400 split in two, because the
    spec says the head pivots on its tilt axis and moving parts ship separately. The round adapter lets the head pan
    by its attach rotation. Tilt is capped at 80°, because past that the rear cap meets the adapter.
14. **J3 pendant:** the drawing's cord is shorter than its "1000 mm" label; the printed 1000 is used. It has one slot,
    `M_CSK_PowderBlack`: black by default, white as an MI tint.
15. **LOD ratios:**
    - The window wall's LOD2 (108) is only a little under its LOD1 (120); every part left is visible at 20 m.
    - The sign hanger's LOD2 is 24% of LOD0, a little over the guide's 5-20%.

## New material slots (the lead adds the MIs)

| Slot | Used for |
|---|---|
| `M_CSK_Sign` | Signs atlas print: I1 plate (2 faces), I5 panel (2 faces) |
| `M_CSK_Poster` | Signs atlas print: I3 posters |
| `M_CSK_SignLit` | I4 diffuser: print + emissive (lit / unlit) |
| `M_CSK_PriceTag` | I2 inserts (spec name, `Price` digits 4.4) |
| `M_CSK_PowderBlack` | Black powder-coated aluminium: poster frames, lightbox + brackets, window frame, door lining, door frame + leaf, track, heads, pendant (tint for white) |
| `M_CSK_Cord` | I1 cord, pendant cord |
| `M_CSK_Plaster` | Walls |
| `M_CSK_FloorVinyl` | Floor (the existing `M_CSK_Vinyl` is the chair's black vinyl) |
| `M_CSK_CeilingTile` | Ceiling tiles |

Reused: `M_CSK_PVC`, `M_CSK_Acrylic`, `M_CSK_Chrome`, `M_CSK_Frame` (T-grid, panel edge, I5 frame), `M_CSK_Base`
(skirting), `M_CSK_Glass`, `M_CSK_LED`, `M_CSK_PlasticWhite` (track conductor strip).

## Not built

- **J4 `SM_CSK_ScaleFigure`:** dropped by the user (the UE mannequin is used).
- **UV2 metre tiling on the shell** (spec 4.1). `mesh.py` writes UV0 and UV1 only. The plaster, vinyl and tile
  materials need either UV2 support added to csk_lib, or world-aligned tiling in the material. That is a lead
  decision; I did not edit shared files.

## Open questions for the user

1. **Ceiling grid vs the 600 LED panel.** Sheet 32's notes give 2 × 2 tiles per 2000 module (976 cells), so the 600
   panel cannot drop into a cell; it now mounts on a tile face. The room shot looks nearer 3 × 3. Keep 2 × 2, or
   change the grid?
2. **Door hand.** The sheet's views disagree. I built hinges on the right seen from the street, per the front view
   and the notes. Should there be a mirrored left-hand leaf and frame?
3. **Skirting on the walls' outside face too** (for partition use)? Right now it is on the shop face only.
4. **The hanging sign's cable drop** is fixed at the sheet's 100. Is a longer-drop variant wanted?
5. **I5 at 600 × 145** (the picture's proportions) rather than the spec's 600 × 200: OK?

## Renders (`WorkFiles/cardshop/families/ij_shell/`)

- **Sign and price tags:** `i1_sign_front.png`, `i1_sign_34.png`, `i2_shelf_side.png`, `i2_shelf_34.png`,
  `i2_tent_34.png`, `i2_hook_34.png`.
- **Posters and signs:** `i3_posters_front.png`, `i3_poster_corner.png`, `i4_storefront_34.png`,
  `i5_hanging_34.png`.
- **Shell and door:** `j1_shell_corner.png` (an L corner with floor, walls, window glass, the door frame and an open
  leaf), `j1_walls_front.png`, `j1_ceiling_under.png`, `j2_door_back.png`, `j2_door_open34.png` (with the I1 sign on
  the leaf).
- **Lights:** `j3_track_34.png`, `j3_head_right.png`, `j3_pendant_front.png`, `j3_pendant_under.png`,
  `j3_panel_34.png`.
- **Reference | render side by side:** `sbs_i1_sign.png`, `sbs_i2_shelf.png`, `sbs_i2_tent_hook.png`,
  `sbs_i3_posters.png`, `sbs_i4_storefront.png`, `sbs_i5_hanging.png`, `sbs_j1_walls.png`, `sbs_j2_door.png`,
  `sbs_j3_head.png`.

The shot tool guesses materials from slot names, so the cord, the vinyl and the tiles render mid-grey. It is a shape
check.
