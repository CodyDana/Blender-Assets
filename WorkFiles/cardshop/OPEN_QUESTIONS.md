# Card Shop Kit: open questions after the family build (collected 2026-09-29)

All 66 questions the 12 family builders left (65, plus a_cases 7 from the local sheet check): 63 for the user, 3 for
the lead. Each family's report (`WorkFiles/cardshop/families/<family>.md`) has the context. **Rec** is the local lead
session's recommendation; the decision is the user's. Where the rec is "as built", nothing changes unless you say
otherwise.

## Decisions that change shapes against the pictures (look at these first)

| # | Family | Question | Rec |
|---|---|---|---|
| 1 | a_cases 4 | **A2 bay:** keep the spec's 184 bay (a fixed ~250 oak panel under it at the rear), or the picture's taller bay with doors down to the bottom track? | Picture: the rear view is the sheet's clearest feature, and "to the T" is the bar |
| 2 | a_cases 7 | **A5 proportions:** sheet 18's oak band is as tall as the glass zone. Keep kick 20 / oak 50 / glass 230, go to the picture's proportions at 300 (glass ~140), or keep 230 glass and grow to ~490 tall? | Picture's proportions at ~490 tall: keeps slabs on stands fitting |
| 3 | a_cases 3 | **A4:** posts to the floor (main view) or standing on the base (detail)? Front standards or clips? | Posts to the floor, as A1 and the main view |
| 4 | b_pack 1 | **B3 collector box:** keep 89 deep (fails a blind test against sheet 10's shallow tray), or ~155 deep to match the layout (changes `BoxC` and shelf grids)? | 155: the picture can't be matched at 89 |
| 5 | a_display 1 | **A14 lid:** glass hood (closed views, built) or flat sheet (open view)? | Hood, as built |
| 6 | a_display 4 | **A16 3-tier riser:** 3 steps × 2 slots (built) or the picture's 2 rows × 3, ~300 wide? | Picture |
| 7 | a_display 8 | **Wall unit cabinet:** 900 (the call-out, built) or ~690 (the picture's proportions)? | 900: a printed number beats a proportion |
| 8 | b_pack 2 | **Wrapper crimps:** whole (sheet 4) or torn like the Open state? | Torn: the state chain needs it |
| 9 | b_pack 4 | **L box:** 2 packs across (the numbers) although sheet 5 draws many narrow packs? | As built |
| 10 | b_ship 3 | **Blister bubble:** pack-sized (built) or the sheet's taller 174 flange with gaps? | Picture |
| 11 | c_retail 3 | **Deck-box pack:** keep the picture's hang tab (Deck H becomes 141)? | Keep the tab |
| 12 | c_retail 6 | **Magnetic holder:** magnets 6 from the top edge (well ~92 tall), as the picture? | Picture |
| 13 | de_storage 1 | **E1 finger cut:** U (built) or the open views' 11-deep half-moon? | No view: both are in the sheet |
| 14 | de_storage 2 | **E1 ends:** M inner length (16 hidden back end) or thin walls everywhere (cavity 13 longer)? | M inner length |
| 15 | e_play 2 | **Binder spine:** 57 (picture) or 51 (spec)? | 57, and the wrapped binder follows |
| 16 | fg_counter 1 | **Folded chair:** 901 tall (a real frame) against the sheet's 800? | 901 |
| 17 | fg_counter 2 | **Counter devices:** is the E layout OK (the sheet's two views disagree)? | Yes |
| 18 | g_devices 1 | **Drawer coin cups:** 8 (call-out, built) or 10 (drawn)? | 8 |
| 19 | h_backroom 4 | **Workbench lower shelf:** oak (notes, built) or chipboard (reads so in the picture)? | Chipboard |
| 20 | ij_shell 1 | **Ceiling grid:** 2 × 2 tiles per module (notes, built) or 3 × 3 (the room shot), so the 600 panel drops in? | 3 × 3 |
| 21 | ij_shell 2 | **Door hand:** add a mirrored left-hand leaf and frame? | Yes, cheap |
| 22 | ij_shell 5 | **I5 panel:** 600 × 145 (picture) instead of 600 × 200 (spec)? | Picture |
| 23 | e_play 1 | **Binder page 293.7 vs cover 292.1** (both measured): grow the cover to ~296, or trim the page? | Grow the cover |

## Parts, states and extra meshes

| # | Family | Question | Rec |
|---|---|---|---|
| 24 | a_cases 1 | A6 stays: a separate stay part, or the front on its hinge only? (sheet 18 draws folding stays) | Stay part |
| 25 | a_cases 2 | A5 / A6 locks: model a cylinder lock, or leave the `Lock` sockets? | Model it (A1 has one) |
| 26 | a_cases 5 | A3 light pole: which back corner (built back-right)? | As built |
| 27 | a_cases 6 | Keep `SM_CSK_Showcase_Half_BayDoor_{L}` as its own mesh (+2)? | Yes: the doors must slide |
| 28 | a_display 2 | A14: add the curved lid stay as a part? | Yes |
| 29 | a_display 3 | A14 lock at the back top corner (sheet), the front, or none? | As the sheet |
| 30 | a_display 5 | A16 risers and stands: solid clear blocks (built) or 3 mm hollow sheet? | Solid (looks the same, cheaper) |
| 31 | a_display 6 | Wall unit: hinged door parts + interior shelf, or fixed doors? | Fixed for v1 |
| 32 | a_display 7 | Wall unit: add `Snap_L` / `Snap_R`? | Yes |
| 33 | a_shelving 3 | A10 end cap: 610 (sheet) or 852 (closes a Double run)? 610-wide shelves? | 610 + a 610 shelf |
| 34 | b_pack 5 | Tuck box film: in the mesh, or a separate unsealed mesh? | In the mesh |
| 35 | b_ship 1 | Carton: grow to inner 490 so 6 sealed boxes fit (6 × 80.8 > 484)? | Yes |
| 36 | b_ship 2 | Ship flat: one (M) or S, M and L? | Three |
| 37 | de_storage 3 | E2: is the M footprint the lid's (built) or the base's? | No view |
| 38 | e_play 3 | Binder: open-flat (built) or a standing binder whose cover opens? | As built |
| 39 | e_play 4 | Tilted page rest (2.45°) OK? | Yes |
| 40 | fg_counter 4 | Modesty-panel grommet: blind cup (built) or a through hole? | As built |
| 41 | g_devices 2 | Scanner parked nose-down in the cradle: that pose? | Yes |
| 42 | g_devices 3 | Printer lid as a separate hinged part (the spec says no parts)? | Yes |
| 43 | h_backroom 1 | Bin flap: now allowed as a 3 mm curved shell (see L1 below), rebuild it? | Rebuild as a shell |
| 44 | h_backroom 3 | Hand truck: `Nose_M` / `Nose_L` sockets, or one `Nose` with per-class offsets? | As built |
| 45 | ij_shell 3 | Skirting on the walls' outside face too? | No |
| 46 | ij_shell 4 | Hanging sign: a longer-drop variant? | Not for v1 |

## Budgets, sockets, hulls

| # | Family | Question | Rec |
|---|---|---|---|
| 47 | a_shelving 4 | Wire rack: 14,000 with grooved posts, or ~6,300 without grooves? | 14,000 |
| 48 | a_shelving 5 | Gondola Double: grooves as `rails` data, or > 40 sockets? | Rails |
| 49 | a_shelving 6 | Corner L shelves and box tier back panel have no collision: raise the hull limits? | Yes, +1 each |
| 50 | b_pack 3 | Pack states budgets 1950 / 1750 / 850 (spec E 250 / 200 / 40)? | Yes |
| 51 | e_play 5 | Binder body 1800, rolled mat 1200, d6 800, token 200 with LODs? | Yes |
| 52 | h_backroom 2 | Warehouse rack: 20,000 for 468 keyhole pockets, ~13k front only, or 1,500 with a mask? | ~13k front only |

## Classes, grids, placement

| # | Family | Question | Rec |
|---|---|---|---|
| 53 | b_ship 4 | Class codes `BoxShipS/M/L` for racks and the hand truck? | Yes |
| 54 | c_retail 1 | Fixture grids accept `CardSmall`? | Yes |
| 55 | c_retail 2 | Top-loader pack: 33 proxy block, or a 52-deep bag? | 52 |
| 56 | c_retail 4 | Hang pose: B8 hangs upright, the blister lies on its back. One convention? | Upright for hanging items |
| 57 | de_storage 4 | Add the `BoxGrade` class for D4? | Yes |
| 58 | fg_counter 5 | Mat and deck layout: check against the playmat zones (E5 exists now) | Lead to check |

## Materials and print

| # | Family | Question | Rec |
|---|---|---|---|
| 59 | c_retail 5 | Dice pips: print in the Boxes cell, or E6's `M_CSK_Resin` pip mask? | Resin mask (E6 exists) |
| 60 | e_play 6 | Pip ink by UV rule (pips in tile (0, 0), the rest in U −1)? | Yes |
| 61 | fg_counter 3 | Paper bag default: shop-logo cell or plain kraft? | Plain kraft (the sheet) |
| 62 | g_devices 4 | Terminal keys: 4 accent slots (6 sections) or one `M_CSK_Keys` palette slot? | One palette slot |
| 63 | g_devices 5 | Label strip: a print tile for the red label borders? | Yes |

## For the lead (shared code), not the user

| # | From | Item | Status |
|---|---|---|---|
| L1 | h_backroom 1, a_cases | The `_Lid` winding test forced convex parts | **Done:** `mesh.check_outward_rays` (per-shell ray parity) now runs on every `_Glass` / `_Lid` / `_Door` / `_BayDoor` part, concave shells included (35 parts, all pass; negative-tested) |
| L2 | a_shelving 1 | Round parts under 13 sides shade faceted (`mesh.mark_sharp` marks every edge over 30°) | Open: add a per-region "smooth" option in `mesh.py` |
| L3 | a_shelving 2 | Tilted levels (A13): `fit.grid_slots` / `slots.write_csk_json` ignore the Level socket's rotation, so `slots_ue` are axis-aligned | Open: rotate grid offsets and slot rotations by the level socket |
| L4 | b_pack 6 | Sheet 5's S box window reads 128 / 87 / 64 against geom's 126 / 100 / 70 | Open: a G1 change, so it needs the user's OK |
| L5 | handoff | Blender 5.2's exact boolean appends an empty material slot per cutter | **Done:** `mesh._apply_boolean` drops the added slots |
