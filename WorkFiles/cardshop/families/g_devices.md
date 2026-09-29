# Family g_devices: POS devices and money (built 2026-09-29, cloud)

Module: `Scripts/cardshop/csk_lib/fam_g_devices.py`, 14 item keys prefixed `g_devices_`. It covers spec rows G2 to
G10 (CARDSHOP_KIT_SPEC.md 3.G). I opened sheet 26 (`csk_pos_devices.png`), cropped and zoomed each panel with
Pillow, and compared each render side by side with its crop (`*_vs_sheet.png`).

**Build:** one build of all 14 keys ends `CSK_BUILD PASSED`. The house `qa_check` passes on every LOD. The kit checks
pass 28/28:
- `contain_fit` 13/13: the tray's 5 `Bill_NN` and 8 `Coin_NN` sockets, checked against the built note stack and coin;
- `csk_hashes` 14/14;
- `deny_scan` 1/1.

## Meshes

| Key | Mesh | LOD tris | Budget | qa | Sockets (+ `Seat`) | Hulls |
|---|---|---|---|---|---|---|
| g_devices_cash_drawer | SM_CSK_CashDrawer | 124 (LOD0 only) | 800 | PASS | `Tray` | 5 |
| g_devices_cash_drawer_tray | SM_CSK_CashDrawer_Tray | 636 / 336 / 44 | **700** (spec 400) | PASS | `Bill_01..05`, `Coin_01..08`, `Grip` | 1 |
| g_devices_bills | SM_CSK_Bills_Stack | 60 (LOD0 only) | 100 | PASS | `Grip`, `Stack` | 1 |
| g_devices_coin | SM_CSK_Coin | 116 (LOD0 only) | 120 | PASS | `Grip`, `Stack` | 1 |
| g_devices_terminal | SM_CSK_Terminal_Card | 496 / 164 / 48 | 800 | PASS | `CardSlot`, `Tap`, `Grip` | 1 |
| g_devices_printer | SM_CSK_Printer_Receipt | 408 / 124 / 48 | 450 | PASS | `PaperOut`, `Lid` | 1 |
| g_devices_printer_lid | SM_CSK_Printer_Receipt_Lid (added) | 196 / 68 / 48 | 250 | PASS | none | 1 |
| g_devices_pos | SM_CSK_POS_Screen | 418 / 204 / 48 | 800 | PASS | `Screen` | 2 |
| g_devices_scanner | SM_CSK_Scanner | 586 / 266 / 144 | 600 | PASS | `Grip`, `Beam` | 1 |
| g_devices_cradle | SM_CSK_Scanner_Cradle | 288 / 144 / 56 | **300** (spec 200) | PASS | `Scanner` | 1 |
| g_devices_price_gun | SM_CSK_PriceGun | 768 / 358 / 172 | 1200 | PASS | `Grip`, `LabelOut` | 1 |
| g_devices_phone | SM_CSK_Phone | 276 / 76 / 20 | 300 | PASS | `Grip`, `Screen` | 1 |
| g_devices_laptop | SM_CSK_Laptop | 1148 / 320 / 64 | **1200** (spec 500) | PASS | `Lid`, `Grip` | 1 |
| g_devices_laptop_lid | SM_CSK_Laptop_Lid | 180 / 52 / 20 | 300 | PASS | `Screen` | 1 |

The printer's spec budget of 700 is split between its two meshes: 450 for the body and 250 for the lid.

**Render bounds (mm):**

| Mesh | Render bounds | What sets it |
|---|---|---|
| Drawer | 409 × 417 × 112 exactly | |
| Tray | 395 × 412 × 96 | The lock stands 3.5 proud of the front |
| Note stack | 149.7 × 69.5 × 10 | |
| Coin | 23.7 × 23.9 × 2 | A 15-sided disc |
| Terminal | 81 × 168 × 56 exactly | |
| Printer | 152 × 179 × 113.5 | 118 with the lid closed |
| POS screen | 360 × 200 × 290 | |
| Scanner | 70 × 160 × 95 exactly | |
| Cradle | 104 × 94 × 100 | |
| Price gun | 45 × 211 × 126 | The label strip hangs 18 in front of the 190 body |
| Phone | 72.6 × 150 × 8 | The two keys stand 0.6 proud of the 72 edge |
| Laptop | 320 × 220 × 16 closed | |

**Socket conventions:**
- Every device's front faces −Y, except the drawer.
- The spec row slides the drawer's tray toward +Y (the staff), and the counter's `Drawer` socket has no rotation, so
  the drawer's lock face is at +Y.
- Directional sockets (`CardSlot`, `Tap`, `PaperOut`, `Screen`, `Beam`, `LabelOut`) point their local +Z out of the
  device. This is the G1 pack's `CardsOut` convention.
- The long handhelds (terminal, scanner, labeller) run their long axis along Y. The spec's "168 × 81 × 56" and
  similar sizes are read as sizes, not as axes: sheet 26 draws 81 across the terminal's front.
- **Moving parts.** Each moving part's pivot is on its axis, and `data.parts` wires it to its socket:

  | Part | Motion | Socket | Range | `open_rot_deg` |
  |---|---|---|---|---|
  | Tray | Slide along +Y | `Tray` | 0-385 mm | |
  | Printer lid | Hinge about X | `Lid` | −105° to 0° | −105 (sheet 26 pose) |
  | Laptop lid | Hinge about X | `Lid` | −130° to 0° | −110 |

  The laptop's hinge axis runs along the rear edge at the lid's mid-thickness. The lid's rear edge is a full round
  about that axis, so the lid clears the base at every angle.
- The tray's `Bill_NN` and `Coin_NN` sockets live on the tray mesh, so money moves with the tray. Notes are turned
  90° to run front to back.
- The cradle's `Scanner` socket parks the scanner nose-down in its cup, grip toward the cradle's front. It uses
  rotation (90, 0, 180), and the nose lands on the cup floor.
- **New placement classes.** `CLASSES` adds `Bill` (150 × 70 × 10) and `Coin` (24 × 24 × 2), for the tray's
  contain test.

## What was built (sheet 26)

- **G2 drawer:** a black steel sleeve with R2.5 rounded edges (2 segments), open at the front, with a folded frame
  round the opening.
- **G2 tray:** the front panel with a round chrome lock and keyhole, the steel bin, and the black insert. The insert
  has real cut pockets:
  - 5 note slots at the back, each with a chrome wire U-clip on a barrel at the back wall;
  - 2 × 4 coin cups in front.
- **G3 terminal:**
  - A wedge body: low at the keypad, with a steeper rear deck, a vertical back, and an undercut arch under the rear
    with a foot. It has R5 edges (3 segments).
  - The colour screen is recessed in the rear deck.
  - 3 soft keys, a 3 × 4 numeric block, and red / yellow / green function keys at the front. The keys are frustum
    caps.
  - The card slot is cut across the front face.
- **G4 printer:**
  - A body with R4 edges and a parting-line groove.
  - A recessed panel low on the front.
  - The front ledge carries a dark tear bar and a square feed key.
  - The paper bay holds an 80 mm roll with a board core.
  - **Lid:** a clamshell shell made of separate convex blocks, so it passes the `_Lid` winding check. It has a rubber
    platen roller along its front edge, and round hinge bosses with pins.
- **G5 POS screen:**
  - A 360 × 230 display with rounded corners and edges, leaning back 12°.
  - A thin bezel, a 1 mm screen recess, and a camera dot.
  - A short, wide neck with a mount block into the display's back.
  - A 200 × 200 base with a rounded top edge and a chamfered foot.
- **G6 scanner:**
  - A lofted head that flares into a nose bezel, with a recessed window in its own emissive slot.
  - A pistol grip raked about 42°, lofted in horizontal sections, so it sits cleanly in the foot.
  - A flat pill-shaped foot.
  - A blue-grey finger trigger.
- **G6 cradle:**
  - A tapered block on a plinth band, with a rounded top edge.
  - A deep saddle dips between two ears, with a cup for the scanner's nose.
- **G7 price labeller:**
  - A body with the print head proud at the front: a window with the red selector, and the label exit below it.
  - The label roll sits between two round-topped cover plates, with a blue spool flange on the far side.
  - A fixed handle is raked back. A lower lever ends in a hook down to the counter.
  - The label strip hangs to the counter.
  - Screw bosses on the sides.
- **G8 money:**
  - The note stack is 5 plain note bundles offset by up to 0.9 mm. Its top and bottom are print tiles (UV0 front /
    back) for the Signs atlas's generic money cell.
  - The coin is a plain disc with a rounded rim.
  - No currency design.
- **G9 phone:**
  - Rounded corners and edges.
  - A flush screen with a thin bezel and a hole-punch camera.
  - Two keys on the right edge, at the positions the sheet shows.
- **G10 laptop:**
  - An aluminium base with rounded corners and edges.
  - A recessed keyboard well with 78 keycaps (a 15-unit layout, and an up/down half-key pair).
  - A touchpad recess, the opening notch, and 3 ports on the left side.
  - **Lid:** a full-round edge, the screen flush in a black bezel, and a camera dot.
- **Screens:** every screen (G3, G5, G9, G10) has its own `M_CSK_Screen` slot and a 0-1 UV0 island, upright as seen
  in use. The laptop's screen reads upright when the lid is open.

**LODs:**
- LOD1 drops bevels, key detail and small parts.
- LOD2 keeps the silhouette and the screen face.
- The laptop's LOD1 keycaps are flat quads.

## Deviations (logged in the module)

1. **Drawer: coin cups.** The sheet draws 2 rows × 5 coin cups. The sheet's own call-out, the log, the spec (E\*) and
   the lead all say 8 cups, so I built 2 × 4.
2. **Drawer: travel.** The travel is **385** (spec 280 E). The sheet draws the tray out until the clip barrels sit
   under the housing's front edge, with every slot in view. The picture wins over E.
3. **Printer: size and lid.**
   - I built it 152 wide × 179 deep. The spec says 179 × 152, but that is E and the sheet's call-outs are the other
     way round.
   - The lid is a **separate hinged part**, `SM_CSK_Printer_Receipt_Lid` (spec: parts none). The sheet draws the lid
     open over the roll, and a separate lid lets the printer also stand closed on the counter.
   - The budget of 700 is split 450 + 250.
4. **Budget raises:**
   - **Tray** 400 → **700**: 13 real pockets, 5 wire clips on barrels and the lock.
   - **Cradle** 200 → **300**: the saddle and cup are real cuts, and the ears have a rounded top edge.
   - **Laptop base** 500 → **1200**: the sheet draws a full keyboard, and the 78 real keycaps alone are 780 tris.
5. **Drawer front at +Y.** The spec's tray direction and the counter socket put the drawer's front at +Y. Every other
   device has its front at −Y.
6. **Render bounds over the spec sizes:**
   - The price gun's label strip adds 18 mm in front of its 190 body.
   - The phone's keys stand 0.6 mm proud of its 72 mm edge.

## New material slot names

The lead needs to add these MIs:

| Slot | What it is | Used on |
|---|---|---|
| `M_CSK_Screen` | Named by the spec | G3, G5, G9, G10 |
| `M_CSK_ScanWindow` | The scanner's emissive beam window (red) | G6 scanner |
| `M_CSK_AccentRed` | The terminal's cancel key, the labeller's selector | G3, G7 |
| `M_CSK_AccentYellow` | The terminal's clear key | G3 |
| `M_CSK_AccentGreen` | The terminal's enter key | G3 |
| `M_CSK_AccentBlue` | The labeller's spool flange; the scanner's trigger (the sheet's trigger is a greyer blue) | G6 scanner, G7 |
| `M_CSK_Paper` | White paper | The receipt roll, the label roll, the label strip |
| `M_CSK_Money` | A print slot: the Signs atlas's generic money cell, no currency design | G8 notes |
| `M_CSK_Coin` | Metal; gold / silver / copper MIs | G8 coin |
| `M_CSK_Aluminium` | The laptop's grey anodised shell | G10 |

**Existing slots reused:**
- `M_CSK_SteelBlack`: the drawer.
- `M_CSK_Plastic`: black device plastic.
- `M_CSK_Metal`: chrome hardware (the lock, the clips, the hinge pins), as in a_cases.
- `M_CSK_Rubber`: the terminal's keys, the platen roller.
- `M_CSK_Board`: the receipt roll's core.
- `M_CSK_SteelDark`: the tear bar.

## Not built

Nothing. All of G2 to G10 are built.

## Open questions for the user

1. **Drawer coin cups.** The sheet draws 10 cups (2 × 5); the call-out and the spec say 8. I built 8 (2 × 4). Do you
   want 10 to match the picture?
2. **Scanner in the cradle.** The sheet shows the cradle beside the scanner, not in use. I made the pose E: the
   scanner is parked nose-down in the cup, with its grip and foot toward the cradle's front. Is that the pose you
   want, or should the cradle hold it another way?
3. **Printer lid.** Is a separate hinged lid OK? The spec says parts: none. The alternative is one mesh, with the
   lid either open as on the sheet or closed.
4. **Key colours.** The key colours use 4 small accent slots, so the terminal has 6 material sections. Would you
   rather have one `M_CSK_Keys` slot with a small palette texture, which would mean fewer draws?
5. **Label print.** The label strip's red label borders are print. They are not modelled, and the strip is plain
   `M_CSK_Paper`. Should they get a print tile?

## Renders (`WorkFiles/cardshop/families/g_devices/`)

Rendered with `csk_shot.py` through a scratch palette wrapper, so black plastic reads black. The shot tool itself
is unedited.

**Side by side with the sheet crop:**
- `drawer_vs_sheet.png`
- `terminal_vs_sheet.png`
- `printer_vs_sheet.png`
- `pos_vs_sheet.png`
- `scanner_vs_sheet.png`
- `price_gun_vs_sheet.png`
- `phone_vs_sheet.png`
- `laptop_vs_sheet.png`

**Single views:**
- **Drawer:** `drawer_34.png` (open, with notes and coins on their sockets), `drawer_closed_34.png`.
- **Terminal:** `terminal_34.png`.
- **Printer:** `printer_34.png` (lid open, the sheet pose), `printer_closed_34.png`.
- **POS screen:** `pos_34.png`.
- **Scanner:** `scanner_34.png`, `scanner_in_cradle_34.png` (on the `Scanner` socket).
- **Price gun:** `price_gun_34.png`.
- **Phone:** `phone_top.png` (front and side).
- **Laptop:** `laptop_open_34.png`, `laptop_closed_34.png`.
- **Money:** `money_34.png`.
- **All devices:** `overview_34.png`.
