"""Walk-in clearance for a Manny-sized capsule, measured against the kit's UCX collision hulls (the same hulls Unreal
imports: hull counts verified equal by ak_verify). Unreal's capsule traces do not collide in a -nullrhi commandlet (the
control sweep into case 1 passed straight through), so the geometric check runs here instead.

Capsule: radius 0.35 m, blocking band z 0.20-1.80 m (anything lower is a step the character walks up: max 0.45 m on the
character movement component; our steps are 0.15 m). A route point is clear when no hull whose z range overlaps the band
comes within the radius horizontally. Every hull is an axis-aligned box after the instance rotations (multiples of 90 deg).
A control route straight into case 1 must be blocked, or the check is invalid.

Genkan (2026-09-28): the entry is a SUNKEN vestibule (build_armory_kit GENKAN: floor -0.12, X 3.52-8.48 (entryfix; was 2.17-9.83), Y 0-2.35 (entryfix r2; was 2.56), the
doorway X 4-8 back to Y -0.30) behind a
low sill (+0.04) with the black step beam (Y 2.35-2.51 since entryfix r2, flush with the hall floor) at its far edge, so the floor now also
steps DOWN: under the capsule centre the floor is the highest hull top within STEP of the current floor (it was only ever
raised). Every route reports its largest single step up and down (max_step_up_m / max_step_down_m, 5 cm probes); the
entry's steps must stay <= ENTRY_STEP_MAX (0.18 m), checked on the ENTRY_ROUTES and required for "passed".

Run: blender -b --factory-startup Assets/Armory/ArmoryKit.blend --python Scripts/armory/walk_check.py
Result: WorkFiles/armory/build/walk_check.json
"""
import json
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(bpy.data.filepath).resolve().parents[2]
OUT = ROOT / "WorkFiles" / "armory" / "build" / "walk_check.json"
if Path(bpy.data.filepath).name != "ArmoryKit.blend":   # a test copy (build_armory_kit --preview-dir): report beside it
    OUT = Path(bpy.data.filepath).resolve().parent / "walk_check.json"
R, Z0, Z1 = 0.35, 0.20, 1.80
# building stage (2026-09-27): routes for the hall (layout.json "cases"), the 4 m entrance and the platform
# r20 (2026-09-28, the user: "lengthen the room to 20m"): the 12 x 20 m hall. The flight's foot Y 15.50 (was 12.30), the
# side cabinets' front 16.76, the deck lip 17.60, the hero table 18.90-19.80, the rear alcoves / corner showcases' fronts
# Y 19.40 / 19.395, the heavy posts Y 16.38-16.68, the deck lanterns Y 18.89-19.31; cases 2 / 3 at Y 8.80 / 13.60
# r20 rear round (2026-09-28): the lower flight's going 0.28 (risers at Y 15.50 / 15.78 / 16.06 / 16.34 / 16.62), the
# +0.75 landing Y 16.62-17.60 (X 3.80-8.20); the wings are one +0.90 plinth from Y 16.43 (WING_Y, X 0-3.80 / 8.20-12,
# no terraces); the cheeks X 3.45-3.80 / 8.20-8.55, Y 15.50-16.43, +0.75 (no longer steppable: 0.75 > 0.45); the
# stair-foot lanterns on their floor stands X 3.075-3.42 / 8.58-8.925, Y 15.53-15.87; the rear alcoves X 1.50-3.30 /
# 8.70-10.50; the corner niche blocks X 0.34-1.50 / 10.50-11.66, front Y 19.40
# r20 fix round (2026-09-29, blind judge 7/10): ONE even flight of six 0.15 m risers, going 0.35, from the foot Y 15.85
# (nose 15.83) to the deck lip 17.60 (treads +0.15 / +0.30 / +0.45 / +0.60 / +0.75 from Y 16.18 / 16.53 / 16.88 / 17.23 /
# 17.58 - 0.35); the stair-foot lanterns Y 15.88-16.22; the cheeks Y 15.85-16.43; centre cases 1 / 2 / 3 at Y 4.00 / 8.70
# / 13.40 (case 3 Y 12.90-13.90); the side rows west 5 / 4 / G1 / G3 at Y 4.10 / 7.27 / 10.53 / 13.80, east 8 / 7 / 6 / G2
# at 4.00 / 7.15 / 10.45 / 13.80 (the last backs at Y 14.55); the display bays 3.85 m (front X 0.294, unchanged); the
# parked door leaves X 2.44-4.14 / 7.86-9.56
ENTRY_STEP_MAX = 0.18   # genkan: the largest single step allowed on the entry routes (sill down, beam up)
ROUTES = {
    # genkan (2026-09-28): over the low sill (Y -0.435 to -0.30, +0.04) down onto the sunken genkan floor (-0.12, X
    # 2.17-9.83, Y 0-2.56, the doorway X 4-8 back to the sill) and the rush mat lying on it (X 4.75-7.25, Y 0.18-2.56,
    # +2.2 cm; its board surround +3 cm)
    "outside_through_entrance_to_mat": [(6.0, -2.0), (6.0, 0.45)],
    # up the black step beam (Y 2.56-2.72, flush with the hall floor: one 12 cm step) onto the hall, toward case 1's
    # west corner (plinth X 5.1-6.9 from Y 3.05; entryfix: the entry lanterns are the andon SM_AK_Lantern on the genkan
    # floor at X 3.53-3.99 / 8.01-8.47, Y 2.093-2.553, against the bar; the genkan is X 3.52-8.48, the bar X 3.46-8.54;
    # entryfix r2: the lanterns stand 0.32 m in front of the bar, Y 1.57-2.03, and the bar is Y 2.35-2.51)
    "mat_up_the_step_beam_to_case1": [(6.0, 0.45), (6.0, 2.2), (4.45, 2.9)],
    # straight up the beam on the axis to just in front of case 1 (its plinth front Y 3.05)
    "genkan_axis_up_the_beam": [(6.0, 1.2), (6.0, 2.65)],
    # between the mat's surround (r4: X 4.60-7.40) and the west lantern (entryfix: X 3.53-3.99), up the bar beside it
    "genkan_up_the_beam_beside_west_lantern": [(4.45, 0.6), (4.45, 2.9)],
    "genkan_up_the_beam_beside_east_lantern": [(7.55, 0.6), (7.55, 2.9)],
    # layout 2: the vestibule posts are gone (the jamb posts stand on the south wall line at the frame's outer ends, r3:
    # plinths X 1.57-2.15 / 9.85-10.43, Y 0-0.84). Genkan: across the genkan floor in front of the entry lanterns
    # (entryfix: their fronts at Y 2.093) and up over the pit's side return onto the hall floor (one 12 cm step), then
    # up the aisle
    # entryfix r2: in front of the lanterns (their fronts now at Y 1.57), so Y 1.65 -> 1.1
    # rear dais (2026-09-28): the flight's foot is Y 12.30 (X 3.80-8.20, cheek blocks X 3.45-3.80 / 8.20-8.55 from
    # Y 12.30), the stair-foot lanterns on their stands X 2.95-3.41 / 8.59-9.05, Y 12.62-13.08: up the aisle to Y 11.92,
    # in front of the cheek block (its cap from Y 12.29) to the flight and up its five 0.15 m risers onto the landing (+0.75)
    # r20: the aisles run on to Y 15.12 (0.38 m in front of the flight's foot and the cheek lanterns, Y 15.525)
    # r20 b3: the side rows moved in to X 2.50 / 9.50 (plinths X 1.95-3.05 / 8.95-10.05, the front pair from Y 3.40 /
    # 3.30), so the aisles run up the middle of the gap to the centre column (X 5.10 / 6.90): X 4.05 / 7.95, entered
    # on a slant in front of case 5 / 8 after passing outboard of the entry lanterns
    # r20 round 3: the front pair 5 / 8 is the smaller SF case further in (X 2.65-3.45 / 8.55-9.35, Y 3.50-4.70 /
    # 3.40-4.60): the aisles at X 4.05 / 7.95 keep 0.60 m to them, the slant in front of them 0.53 m; the parked door
    # leaves are X 2.40-4.10 / 7.90-9.60 (Y 0.14-0.19); the wall walks pass the wide display bays (front X 0.294)
    # r20 fix round: to 0.38 m before the flight's nose (15.83), then up it onto the +0.75 tread (Y 17.42)
    # r16 stairs+cases round: the front pair 5 / 8 moved forward (X 2.5-3.3 / 8.7-9.5, Y 3.0-4.2): the slant onto the
    # aisle runs in front of them (0.6 m clear of their inner front corner, 0.45 m of the entry lantern's back corner);
    # the flight is four 0.15 m risers (foot 15.85, lip 16.90) to the +0.60 deck, so Y 17.42 is on the deck
    # r17 cases round: the side rows step toward the aisle as they go back (build_armory_kit CASE_TABLE): west 5 / 4 /
    # G1 / G3 plinths X 2.30-3.10 / 2.325-3.175 / 2.45-3.55 / 3.405-4.255 at Y 3.15-4.35 / 6.75-7.75 / 11.05-12.45 /
    # 13.90-14.90; east 8 / 7 / 6 / G2 X 8.90-9.70 / 8.59-9.69 / 8.485-9.335 / 7.745-8.595 at Y 3.15-4.35 / 6.75-8.15 /
    # 11.85-12.85 / 13.90-14.90. The aisle runs X 4.05 / 7.95 to Y 12.6, then jogs in to X 4.70 / 7.30 past the back
    # case (G3 / G2, 0.445 m clear) beside case 3 (X 5.2-6.8, 0.50 m clear) to the flight
    # r17 fix round (build_armory_kit CASE_TABLE: each row stacks as reference 2's): west 5 / G1 / 4 / G3 plinths X
    # 2.30-3.10 / 3.05-4.15 / 1.15-2.00 / 1.15-2.00 at Y 3.15-4.35 / 4.85-6.25 / 7.60-8.60 / 12.40-13.40, east 8 / 7 /
    # 6 / G2 X 8.90-9.70 / 7.85-8.95 / 10.00-10.85 / 10.00-10.85 at the same Y. The aisles run straight at X 4.62 / 7.38
    # (0.47 m clear of the S cases G1 / 7, 0.48 m of cases 1 / 2, 0.58 m of case 3) from the step beam to the flight
    # r18 cases round (build_armory_kit CASE_TABLE: each row one diagonal on screen): west 5 / 4 / G3 / G1 plinths X
    # 2.30-3.10 / 1.13-1.98 / 1.15-2.00 / 2.05-2.95 at Y 3.15-4.35 / 7.85-8.85 / 11.95-12.95 / 13.70-14.90, east 8 / 6 /
    # G2 / 7 X 8.90-9.70 / 10.02-10.87 / 10.00-10.85 / 9.05-9.95 at the same Y. The aisles are X 3.10-5.10 / 6.90-8.90:
    # the routes run up their middles, X 4.10 / 7.90 (1.00 m clear of the front pair, 1.00 m of cases 1 / 2, 1.10 m of
    # case 3, 1.15 m of the S cases at the rear)
    "mat_to_west_aisle_to_steps": [(6.0, 1.2), (4.8, 1.1), (3.0, 1.1), (3.0, 2.3), (4.10, 2.75), (4.10, 15.45),
                                   (4.3, 15.45), (4.3, 17.42)],
    # r19 (reference order, build_armory_kit CASE_TABLE): west 5 / 4 / G1 / G3 plinths X 2.40-3.40 / 2.70-3.60 /
    # 2.87-3.67 / 2.46-3.36 at Y 2.91-3.71 / 4.645-5.395 / 6.58-7.58 / 9.465-10.215; east 8 / 7 / 6 / G2 X 8.66-9.46 /
    # 8.76-9.76 / 8.58-9.38 / 8.52-9.42 at Y 2.80-3.80 / 4.70-5.50 / 6.925-7.675 / 9.525-10.275. The aisles keep X 4.10 /
    # 7.90 (0.43 / 0.62 m clear of the rows, 1.00 m of cases 1 / 2); the east entry slant bends at (8.5, 2.4) between
    # the entry lantern (back corner (8.47, 2.03), 0.37 m) and case 8 (front inner corner (8.66, 2.80), 0.43 m)
    # r19 b: case 8 is the compact SF at (8.80, 3.13) (plinth X 8.47-9.13 from Y 2.78; hull corner (8.457, 2.767)): the
    # slant bends at (8.60, 2.38) (0.37 m off the entry lantern's back corner (8.47, 2.03), 0.40 m off case 8) and runs
    # level in front of case 8 (Y 2.38-2.45, 0.36 m clear of its front corner) onto the aisle
    "mat_to_east_aisle_to_steps": [(6.0, 1.2), (7.2, 1.1), (9.0, 1.1), (9.0, 2.3), (8.60, 2.38), (7.90, 2.45),
                                   (7.90, 15.45), (7.7, 15.45), (7.7, 17.42)],   # r19 a: ... (8.5, 2.4), (7.90, 2.75) ...
    # r20 rear round: to 0.38 m before the wing plinth's face (Y 16.43; was the b7 cabinet front 16.76)
    "west_wall_walk_along_niches": [(3.0, 1.5), (0.75, 1.5), (0.75, 16.05)],       # behind the west side cases
    "east_wall_walk_along_niches": [(9.0, 1.5), (11.25, 1.5), (11.25, 16.05)],     # behind the east side cases
    # r20 b3: case 1 Y 3.35-4.65, case 2 8.20-9.40, case 3 13.10-14.10; the side cases' inner faces X 3.05 / 8.95
    # r20 fix round: case 1 Y 3.35-4.65, case 2 8.10-9.30, case 3 12.90-13.90, the flight's nose 15.83; the side cases'
    # inner faces X 3.05 / 8.95 (0.40 m from the route ends)
    # r16 stairs+cases round: the side rows staggered as reference 2 (west 5 / 4 / G1 / G3 at Y 3.0-4.2 / 5.0-6.5 /
    # 7.35-8.75 / 10.6-12.1, inner faces X 3.3 / 3.55; east 8 / 7 / 6 / G2 at 3.0-4.2 / 5.05-6.45 / 7.3-8.8 / 10.6-12.1,
    # inner faces X 8.7 / 8.45): the centre gaps run wall walk to wall walk through the 0.80 m gaps between the side
    # cases (Y 6.9: 0.40 m clear of 4 / 6; Y 9.7: 0.40 m behind case 2) and in front of the flight
    # r16 fix round: the rows step out to the walls (tall 4 / 6 / G3 / G2 at X 1.60 / 10.40, 1.0 x 0.85 m: faces
    # X 1.175 / 10.825, Y 5.25-6.25 / 7.55-8.55 / 10.85-11.85; S G1 / 7 at X 2.10 / 9.90, Y 7.35-8.75 / 5.05-6.45): the
    # wall walks (X 0.75 / 11.25) keep 0.075 m, the cross walks 0.30-0.65 m
    # r17 cases round: the cross walks at Y 5.55 (1.20 m behind the front pair, 1.20 m before case 4 / 7, 0.90 m
    # behind case 1), 10.0 (0.70 m behind case 2, 1.05 m before G1) and 15.3 (0.40 m behind G3 / G2, 0.55 m before
    # the flight's foot 15.85); the wall walks (X 0.75 / 11.25) are now 1.2 m clear of every side case
    # r17 fix round: the first cross walk moves behind the S cases (Y 6.25), in front of the talls 4 / 6 (7.60) and
    # case 2 (8.10): Y 6.95
    # r19: the cross walks behind the cloak / boots cases (backs 5.395 / 5.50) and before the scroll / hat cases (fronts
    # 6.58 / 6.925): Y 6.05; behind the rear talls (backs 10.215 / 10.275), before case 3 (12.90): Y 11.1
    "centre_gap_case1_case2": [(0.75, 6.05), (11.25, 6.05)],   # r18: Y 6.95
    "centre_gap_case2_case3": [(0.75, 11.1), (11.25, 11.1)],   # r18: Y 10.0 (now inside the rear talls)
    "centre_gap_case3_to_flight": [(0.75, 15.3), (11.25, 15.3)],
    # r20 round 3 (NEW): between case 5 / 8 and case 1 (X 3.45-5.10 / 6.90-8.55), from the wall walk to the centre gap
    # r16: through the 0.80 m gap between the front case and the second case (5 / 4, 8 / 7) onto the aisle
    # r17 cases round: the gap behind the front pair is Y 4.35-6.75 (was 4.2-5.0)
    # r17 fix round: behind the front case (Y 4.35), round the outer side of the S case (X 3.05 / 8.95) and on to the
    # aisle behind it, then down the aisle to the step beam
    # r18 cases round: nothing stands behind the front case now: straight across behind it (its back Y 4.35) to the aisle
    # r19: through the 0.935 / 0.90 m gap between the front case and the cloak / boots case behind it
    "west_wall_behind_case5_to_aisle": [(0.75, 4.18), (4.10, 4.18), (4.10, 2.9)],     # r18: Y 5.55
    "east_wall_behind_case8_to_aisle": [(11.25, 4.25), (7.90, 4.25), (7.90, 2.9)],    # r18: Y 5.55
    # r17 (NEW): into the rows' own gaps from the aisle to the wall walk: behind case 4 / 7 and behind G1 / 6
    # r17 fix round: behind the wall talls 4 / 6 (to Y 8.60), in front of the back talls G3 / G2 (from 12.40) and
    # behind them (to 13.40)
    # r18 cases round: behind the talls 4 / 6 (backs Y 8.85), in front of the back talls G3 / G2 (fronts 11.95), and
    # through the 0.75 m gap between G3 / G2 (backs 12.95) and the S cases G1 / 7 (fronts 13.70); behind the S cases
    # (backs 14.90) the cross walk at Y 15.3 passes
    # r19: between the scroll / hat case (backs 7.58 / 7.675) and the rear tall (fronts 9.465 / 9.525)
    # r19 b: the rear slot is a PAIR of talls (build_armory_kit CASE_TABLE): west G4 X 2.61-3.51, Y 7.985-8.735 and G3
    # X 2.71-3.61, Y 9.755-10.505; east G5 X 8.39-9.29, Y 8.075-8.825 and G2 X 8.37-9.27, Y 9.715-10.465; 0.40 m of
    # floor (no route) between the scroll / hat case and the near tall. The r19 a routes at Y 8.52 / 8.60 now cross the
    # near talls: they move into the gap between the pair (1.02 / 0.89 m wide), Y 9.25 / 9.27
    "west_aisle_between_G4_and_G3_to_wall": [(4.10, 9.25), (0.75, 9.25)],     # r19 a: between G1 and G3, Y 8.52
    "east_aisle_between_G5_and_G2_to_wall": [(7.90, 9.27), (11.25, 9.27)],    # r19 a: between case 6 and G2, Y 8.60
    # r18 final fix (build_armory_kit CASE_TABLE / CASES: talls 0.90 x 0.75, S 1.0 x 0.8): west 4 / G3 / G1 plinths X
    # 1.13-1.88 / 1.60-2.35 / 2.13-2.93 at Y 7.85-8.75 / 10.50-11.40 / 13.93-14.93, the front SF 5 Y 3.25-4.25; east
    # mirrored. Behind case 4 (Y 9.6, 0.85 / 0.90 m clear), behind the back tall G3 / G2 (Y 12.1) and between it and the
    # S case (Y 13.3, 0.63 m clear of the S front); "before G3" (Y 11.4) is now inside G3's footprint, replaced by
    # "behind G3". The cross walk at Y 15.3 passes 0.37 m behind the S cases (backs 14.93)
    "west_aisle_behind_G3_to_wall": [(4.10, 12.1), (0.75, 12.1)],
    "east_aisle_behind_G2_to_wall": [(7.90, 12.1), (11.25, 12.1)],
    # r19: nothing stands behind the rear talls any more; the r18 routes between G3 / G2 and the S cases (Y 13.3) now
    # cross open floor before case 3's flank
    "west_aisle_rear_floor_to_wall": [(4.10, 13.3), (0.75, 13.3)],
    "east_aisle_rear_floor_to_wall": [(7.90, 13.3), (11.25, 13.3)],
    # rear dais: case 3's back is Y 11.8 (X 5.2-6.8); up the flight on a slant onto the landing, the hero table front
    # at Y 14.55 on the +0.90 deck
    "aisle_up_the_steps_to_hero_table": [(9.0, 15.45), (7.7, 15.45), (6.0, 17.42), (6.0, 18.45)],   # r20 fix round
    # building r5: from the top of the steps across the platform to the rear alcoves (between the heavy platform-front
    # posts, the hero table and the platform lanterns)
    # f1: the rear alcoves moved outboard (X 1.2-3.0 / 9.0-10.8), the platform lanterns to (3.55 / 8.45, 15.10)
    # rear dais: up the flight to the landing (+0.75), across onto the side plinth (b4: +0.90 from Y 13.50, one 0.15 m
    # step at X 3.80 / 8.20) to the alcove front (Y 15.40); the deck lanterns stand at X 3.27-3.73 / 8.27-8.73,
    # Y 14.87-15.33
    # r20: along the +0.75 row (Y 17.40-17.45) and back to 0.45 m before the alcove fronts (Y 19.40)
    "platform_to_west_rear_alcove": [(6.0, 15.45), (6.0, 17.15), (4.3, 17.40), (2.4, 17.45), (2.4, 18.95)],
    "platform_to_east_rear_alcove": [(6.0, 15.45), (6.0, 17.15), (7.7, 17.40), (9.6, 17.45), (9.6, 18.95)],
    # rear dais: on to the corner showcases (b4: X 0.39-1.19 / 10.81-11.61, front Y 15.395), clear of the sill ledge
    # (X 0-0.335 / 11.665-12, underside +2.55: head height on the +0.90 deck)
    # r20 rear round: the rear alcoves 0.30 m inboard (X 1.50-3.30 / 8.70-10.50, centres 2.40 / 9.60); the corner
    # NICHES (blocks X 0.34-1.50 / 10.50-11.66, face Y 19.40, niche openings X 0.95-1.40 / 10.60-11.05)
    "platform_to_west_corner_niche": [(6.0, 15.45), (6.0, 17.15), (4.3, 17.40), (2.4, 17.45), (1.175, 18.95)],
    "platform_to_east_corner_niche": [(6.0, 15.45), (6.0, 17.15), (7.7, 17.40), (9.6, 17.45), (10.825, 18.95)],
    # rear dais: up the flight on the axis and the deck riser to the hero table's front (Y 14.55)
    # b4: the table is Y 14.90-15.80 now: on up the plain deck riser onto the deck in front of it
    "axis_up_the_flight_to_hero_table_front": [(6.0, 15.45), (6.0, 18.50)],       # r20: table front 18.887
    # b4: the side plinths are +0.90 from the landing front (Y 13.50): from the landing across onto the west / east
    # plinth (one 0.15 m step at X 3.80 / 8.20), past the newel side walls (to Y 13.50) and the heavy posts (Y 13.18-13.48)
    # b7: the side zones are terraced in the flight's rows (cabinet +0.60 from Y 13.56, tread +0.75 from 13.98, deck
    # +0.90 from 14.40): along the +0.60 row (Y 13.85: 0.37 m behind the heavy posts' back faces, Y 13.48) across the
    # full width of the room
    # r20: the +0.60 row at Y 17.05 (0.37 m behind the heavy posts' back faces, Y 16.68)
    # r20 rear round: the wings are one +0.90 plinth (no terraces): from the +0.75 landing up one 0.15 m step onto
    # the west / east wing deck at X 3.80 / 8.20, 0.37 m behind the heavy posts' back faces (Y 16.68)
    # r20 fix round: from the +0.75 tread (Y 17.25-17.60) up one 0.15 m step onto the wing deck
    # r16: the flight's top tread is the +0.60 deck itself (from Y 16.90): level across onto the wings
    "landing_onto_west_wing_deck": [(5.0, 17.42), (0.8, 17.42)],
    "landing_onto_east_wing_deck": [(7.0, 17.42), (11.2, 17.42)],
    # r20 rear round (NEW): past the stair-foot lanterns on their stands (X 3.12-3.42 / 8.58-8.88, Y 15.55-15.85) along
    # the wing plinth's face to the wall walk (0.38 m clear of the face, Y 16.05)
    "aisle_past_west_foot_lantern_to_wall": [(4.10, 15.45), (2.5, 15.45), (2.5, 16.05), (0.75, 16.05)],
    "aisle_past_east_foot_lantern_to_wall": [(7.90, 15.45), (9.5, 15.45), (9.5, 16.05), (11.25, 16.05)],
    # r20 (NEW): the 1.30 m deck strip in front of the hero table (front 18.887), the deck lanterns (18.893) and the
    # plum vases, across the deck from the west to the east rear alcove
    "deck_strip_in_front_of_hero_table": [(6.0, 15.45), (6.0, 18.45), (2.4, 18.45), (9.6, 18.45)],
    # layout 2 (entrance.png's composition): from the mat along the inside of the south wall across the genkan floor,
    # past the parked leaves (X 2.25-3.95 / 8.05-9.75, genkan: standing on its floor, room face Y 0.19 + hardware) and the inner jamb bands (X 2.11-2.25 / 9.75-9.89, to Y 0.215) up to the deep jamb
    # posts at the frame's outer ends (plinths X 1.57-2.15 / 9.85-10.43, Y 0-0.84; the sconces on their room faces hang
    # above the band); entryfix: up over the pit's side return (X 3.46-3.52 / 8.48-8.54) onto the hall floor, which
    # runs on outboard of the genkan to the posts
    "inside_along_west_parked_leaf_to_jamb_post": [(6.0, 0.6), (2.6, 0.6), (2.6, 1.9)],
    "inside_along_east_parked_leaf_to_jamb_post": [(6.0, 0.6), (9.4, 0.6), (9.4, 1.9)],
    # genkan: from the vestibule's west / east end up over the side return (one 12 cm step) onto the hall floor beside
    # the post plinth (to Y 0.86) and on to the wall walk behind the side cases (entryfix: the genkan ends at X 3.52 /
    # 8.48, so the start moved in from X 3.0 / 9.0, beside the mat surround)
    # entryfix r2: in front of the lanterns (fronts Y 1.57) and past the post plinth (to Y 0.84) on a slant
    "genkan_west_end_up_the_return_to_wall_walk": [(4.2, 1.1), (3.0, 1.15), (1.1, 1.4), (0.75, 2.0)],
    "genkan_east_end_up_the_return_to_wall_walk": [(7.8, 1.1), (9.0, 1.15), (10.9, 1.4), (11.25, 2.0)],
    "CONTROL_must_hit_case1": [(6.0, 1.2), (6.0, 3.6)],   # r20 b3: case 1's plinth front is Y 3.35 (the capsule reaches 3.95)
    # exterior stage (2026-09-27): the player starts in the courtyard (layout.json "player_start", on the path inside the
    # gate) and walks the stepping stones and the ishidatami over the landing and the threshold into the hall
    "courtyard_start_along_path_through_entrance": [(6.0, -10.4), (6.1, -7.5), (6.0, -4.9), (6.0, -1.9), (6.0, -0.4),
                                                    (6.0, 1.2)],
    "outside_through_gate_to_start": [(6.0, -16.0), (6.0, -13.0), (6.0, -10.4)],   # gate clear X 4.81-7.19
    "courtyard_round_west_to_tsukubai_front": [(6.0, -10.4), (4.7, -8.8), (4.7, -6.4)],
    "courtyard_round_east_past_lantern": [(6.0, -4.0), (9.6, -4.4), (9.6, -8.6), (6.2, -9.0)],
    "CONTROL_must_hit_stone_lantern": [(6.0, -7.3), (8.35, -7.3)],
}

# exterior stage: the SM_AKX_ garden pieces live in KitExterior / AssemblyExterior
KIT_COLLS, ASM_COLLS = ("Kit", "KitExterior"), ("Assembly", "AssemblyExterior")
kit = {o.name: o for c in KIT_COLLS if c in bpy.data.collections for o in bpy.data.collections[c].objects
       if o.type == "MESH" and not o.name.startswith("UCX_")}
hulls = []   # (xmin, xmax, ymin, ymax, zmin, zmax, instance name)
for inst in [o for c in ASM_COLLS if c in bpy.data.collections for o in bpy.data.collections[c].objects]:
    piece = inst.name.split("__")[0]
    src = kit.get(piece)
    if src is None:
        continue
    for h in src.children:
        if not h.name.startswith("UCX_"):
            continue
        pts = [inst.matrix_world @ (h.matrix_local @ Vector(c)) for c in h.bound_box]
        xs, ys, zs = [p.x for p in pts], [p.y for p in pts], [p.z for p in pts]
        hulls.append((min(xs), max(xs), min(ys), max(ys), min(zs), max(zs), inst.name))


STEP = 0.45   # CharacterMovement MaxStepHeight (cm 45)
ENTRY_ROUTES = ("outside_through_entrance_to_mat", "mat_up_the_step_beam_to_case1", "genkan_axis_up_the_beam",
                "genkan_up_the_beam_beside_west_lantern", "genkan_up_the_beam_beside_east_lantern",
                "mat_to_west_aisle_to_steps", "mat_to_east_aisle_to_steps", "inside_along_west_parked_leaf_to_jamb_post",
                "inside_along_east_parked_leaf_to_jamb_post", "genkan_west_end_up_the_return_to_wall_walk",
                "genkan_east_end_up_the_return_to_wall_walk", "courtyard_start_along_path_through_entrance")


def probe(x, y, floor):
    """-> (blocking hull or None, new floor). Hulls within the radius whose top is within STEP of the current floor are
    stepped onto; anything taller that reaches into the body blocks. Genkan: the new floor is the highest top of the
    hulls directly under the capsule centre (within STEP of the current floor), so it can also step down (a sunken
    floor); with no hull under the centre it stays where it was."""
    under_tops = []
    near = []
    for (x0, x1, y0, y1, z0, z1, name) in hulls:
        dx = max(x0 - x, 0.0, x - x1)
        dy = max(y0 - y, 0.0, y - y1)
        if (dx * dx + dy * dy) ** 0.5 < R:
            near.append((z0, z1, name, dx == 0.0 and dy == 0.0))
    for z0, z1, name, under in near:
        if z1 <= floor + STEP:
            if under:
                under_tops.append(z1)
        elif z0 < floor + Z1:
            return name, floor
    return None, (max(under_tops) if under_tops else floor)


res = {"capsule": {"radius_m": R, "band_z_m": [Z0, Z1]}, "n_hulls": len(hulls), "routes": {}}
for name, pts in ROUTES.items():
    hits = []
    floor = None
    up = down = 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = max(2, int(((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5 / 0.05))
        for i in range(n + 1):
            t = i / n
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            if floor is None:   # the start: the highest ground-level top (<= +0.7) under the first point
                floor = max([h[5] for h in hulls if h[0] <= x <= h[1] and h[2] <= y <= h[3] and h[5] <= 0.7] or [0.0])
            b, nf = probe(x, y, floor)
            up, down = max(up, nf - floor), max(down, floor - nf)
            floor = nf
            if b:
                hits.append({"at_m": [round(x, 2), round(y, 2)], "hull_of": b, "floor_m": round(floor, 3)})
                break
        if hits:
            break
    res["routes"][name] = {"points": pts, "clear": not hits, "first_block": hits[0] if hits else None,
                          "end_floor_m": round(floor, 3), "max_step_up_m": round(up, 3),
                          "max_step_down_m": round(down, 3)}
res["control_blocked"] = all(not r["clear"] for k, r in res["routes"].items() if k.startswith("CONTROL"))
res["entry_step_max_m"] = ENTRY_STEP_MAX
res["entry_steps_ok"] = all(max(res["routes"][k]["max_step_up_m"], res["routes"][k]["max_step_down_m"]) <= ENTRY_STEP_MAX
                            for k in ENTRY_ROUTES)
res["passed"] = res["control_blocked"] and res["entry_steps_ok"] and \
    all(r["clear"] for k, r in res["routes"].items() if not k.startswith("CONTROL"))
OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
print("WALK", json.dumps({k: (v["clear"], v["first_block"], v["max_step_up_m"], v["max_step_down_m"])
                          for k, v in res["routes"].items()}), "entry_steps_ok", res["entry_steps_ok"], "passed",
      res["passed"])
