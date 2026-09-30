CAMERAS = [  # name, location (m), look-at (m), lens mm
    # f1: reference 2's verticals are vertical, so its establishing view is a LEVEL camera with a lens shift. Least-squares
    # fit of Y, Z, lens and shift to 15 landmarks (step beam ends, both lanterns, case 1 plinth and glass, painting
    # corners): (6.0, -1.51, +3.42), 24.5 mm, shift_y -0.303, RMS 16.3 px on 1448 x 1086 (the pitched 24 mm camera
    # at (6.0, -0.65, +2.90) scored 39.0 px on the same landmarks). It stands over the landing, 1.5 m outside the
    # entrance; the 3.65 m lintel clears the top of its frame. The 5th element is the look-at, the 6th the lens shift
    # entryfix (2026-09-28, the user: the entry lanterns read "like a long rectangle"): the 24.5 mm lens 1.5 m out put
    # the lanterns 45 deg below the axis at the frame corners, so the andon showed its top at 0.49x its front face
    # (reference 2: ~0.31x). Refit (WorkFiles/armory/hero/room_preview/entryfix/c1fit3.py: 11 landmarks, the case glass
    # tops left out as a design difference; the lintel must clear the frame top): 35 mm, 3.05 m out, shift -0.316:
    # lantern top 0.37x the front (rendered ~0.31x to the cap's front edge), RMS 23.9 px on those landmarks
    # entryfix r2 (blind judge 6/10): refit jointly with the entry layout (c1fit4.py, RMS 12.5 px on 19 landmark
    # values): 40 mm, 4.18 m out, shift -0.315; the lanterns' top shows 0.33x their front (35 mm: 0.37x)
    ("C1_EntryReveal", (6.0, -4.18, 3.39), (6.0, 20.0, 3.39), 40.0, -0.315),
    ("C2_Case1", (6.0, 1.50, 2.20), (6.0, 4.00, 0.8), 35),            # r20 b3: follows case 1 (Y 4.00)
    # r17 cases round: re-aimed on the tray in case 8 at (9.30, 3.75) (r16 still aimed at the r20 X 8.95 / Y 4.0), 1.2 m
    # out in the aisle at the same Y, looking down onto the tray (deck +0.904)
    # r17 fix round: the SF glass is 0.20 m taller (top +1.55), so the camera rises 1.62 -> 1.78 to keep looking down
    # over the near top rail into the tray
    # r18 cases round: the SF case is low (plinth +0.40, glass top +0.90; the tray deck +0.404), so the camera leans in
    # over it (0.20 m off the case's aisle face, +1.85) and looks steeply down through the top glass onto the tray: the
    # sight line to the tray's front edge (X 9.11, +0.43) clears the near top rail (X 8.96, +0.90) by 5 cm (from 0.45 m
    # off at +1.75 the rail crossed the front row)
    # r18 final fix (the r18 combined judge, delta 6: "the blank white backboard in C4 is blown out and dominates the top
    # third of the frame"; the tray and its reflection card stay as they are): 0.10 m further over the case (0.10 m off
    # its aisle face), the aim 5 cm nearer and a 65 mm lens, so the slab fills the frame (y ~100-767 of 900, x ~260-1340)
    # and the card stands wholly above its top edge (projected: its foot at y < 0); the near rail (+0.85) is ~0.4 m
    # under the sight line to the tray's front edge
    # r19 (reference order): case 8 moves with its tray from (9.30, 3.75) to (9.06, 3.30); the camera keeps the same
    # place relative to it (0.10 m off its aisle face, X 8.66)
    ("C4_ShurikenTray", (8.56, 3.30, 1.85), (9.04, 3.30, 0.43), 65),  # item 1: looking down into case 8   # r18 final: (8.80, 3.75, 1.85) -> (9.28, 3.75, 0.43); r18: (8.70, 3.75, 1.85) -> (9.33, 3.75, 0.43), 50
    # r20 (12 x 20): C3 / C5 follow cases 3 / 4, C10 / CX the back wall (+4.0), CW's aim the flight (+3.2)
    ("C3_Case3", (6.0, 11.30, 1.50), (6.0, 13.40, 0.95), 28),        # r20 fix round: follows case 3 (Y 13.40)
    # r17 cases round: case 4 at (2.75, 7.25); from the aisle behind it (1.85 m in, 1.35 m back), clear of case 2 (X 5.1)
    # r17 fix round (judge delta b: the camera cut off the glass top and the plinth foot): case 4 at (1.575, 8.10);
    # from beside case 2's front corner in the aisle, 3.6 m off (was 2.3 m), so the whole 2.2 m case stands in the frame
    # r18 cases round: case 4 at (1.555, 8.35); the same 3.6 m view from the aisle in front of case 2 (X 4.90, 0.20 m
    # outboard of its west face), the whole 2.2 m case in frame (26 mm: at 28 mm the plinth foot sat 7 px off the frame)
    # r18 final fix: case 4 at (1.505, 8.30)
    # r19 (reference order): the cloak case 4 is second from the entry at (3.15, 5.02); from the aisle mouth (0.40 m
    # outboard of case 1's west face, Y 2.45), 3.1 m off, the whole 2.2 m case in frame (projected y ~70-855 of 900),
    # the scroll case and the rear tall beside it on the right, the low kunai case in the near left corner, case 1 out
    # of frame (a first try from X 5.55 caught its glass in the lower right)
    ("C5_CloakCase", (4.70, 2.45, 1.80), (3.10, 5.05, 1.10), 21),   # r18: (4.90, 7.05, 1.60) -> (1.505, 8.30, 1.10), 26
    ("C10_Hero", (6.0, 14.90, 2.30), (6.0, 19.90, 1.85), 26),
    # r17 fix round: the west aisle is X 4.62 (was 4.05). r18 cases round (r17 judge: G1's glass filled the foreground;
    # from Y 2.9 case 1's west face and case 5 also flank the frame): G1 has moved to the rear, the aisle is X 3.10-5.10,
    # and the camera stands in its middle just past the front pair (backs Y 4.35 / 4.65), so the near frame is floor
    # r19 (reference order): the west aisle is X 3.67-5.10 past the scroll case; the camera stands in it between the
    # cloak case (back Y 5.40) and the scroll case (front 6.58), looking down the aisle to the flight: the rear tall G3
    # wholly in frame on the left (its plinth and emblem), case 2 / 3 on the right, the aisle floor clear
    ("CW_WestAisle", (4.60, 6.00, 1.70), (4.2, 16.2, 0.9), 24),   # r18: (4.10, 5.10, 1.60) -> (3.6, 16.2, 1.2), 24
    ("CX_FromPlatform", (6.0, 19.4, 2.4), (6.0, 1.0, 0.8), 24),
    EXT.CAMERA,   # exterior stage: CG_Garden, the courtyard and the entrance
]


# --------------------------------------------------------------------------- main

def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    for name in MATERIALS:
        build_material(name)
