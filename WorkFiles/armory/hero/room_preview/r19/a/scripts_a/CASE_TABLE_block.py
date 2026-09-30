CASE_TABLE = [
    # r20 (12 x 20 m): case 1, the genkan and the front side cases (5, 8) stay (the C1 foreground is unchanged); case 2
    # 7.6 -> 8.80, case 3 11.3 -> 13.60; the side rows spread to end at Y 12.70 (0.635 L, the plan's side-display band):
    # west 4 6.6 -> 6.72, G1 9.1 -> 9.33, G3 11.6 -> 11.95; east 7 6.3 -> 6.60, 6 8.8 -> 9.25, G2 11.4 -> 11.95
    # r20 b3 (blind judge 7/10): (delta 5) the centre cases evenly spaced as the plan's (reference 1: 1 -> 2 -> 3 even,
    # case 1 at ~23 % of the hall): case 1 3.70 -> 4.00 (20 %; gaps 4.80 / 4.80). b3 tried 4.30 (and case 2 at 8.95):
    # through C1 its plinth foot rose to y 783 px against reference 2's 835 (4.00: 811, 3.70: 841); (deltas 2 / 3)
    # the side rows move in, X 1.75 / 10.25 -> 2.50 / 9.50 (the plan's side cases at ~2.65 m off the axis of its 8 m
    # hall, scaled to the 12 m hall; the gap to the centre column 2.05 m, the wall aisle along the niches 1.6 m), which
    # also brings the front pair (5, 8) into the C1 frame beside case 1, as reference 2's kunai and shuriken cases
    # r20 round 3 (blind judge delta 2): the front pair 5 / 8 is the smaller "SF" case, 0.55 m further inboard (X
    # 2.65-3.45 / 8.55-9.35): through C1 its front face spans x ~22-190 / ~1265-1435 of 1448 (reference 2's kunai case
    # ~30-195, shuriken case ~1285-1410); 1.65 m of floor stays between it and case 1 (X 5.10 / 6.90)
    # r20 fix round (blind judge 7/10): (delta 2) the centre row evenly spaced with clear floor before the flight: case 1
    # stays (the C1 foreground), cases 2 / 3 8.80 / 13.60 -> 8.70 / 13.40 (centres 4.70 m apart; the flight's foot moved
    # back to 15.85, so case 3's back (13.90) is 1.93 m clear of the bottom nose, was 1.38); (delta 8: the side cases
    # clustered in pairs with empty floor toward the rear) the side rows spread evenly from the front pair (5 / 8, fixed)
    # to 1.30 m before the stair-foot lanterns: equal 1.82 / 1.85 m gaps along each aisle, the last case's back at Y 14.55
    # r16 stairs+cases round (blind judge on night_20m: from C1 the east column 8 / 7 / 6 / G2 stacked into one another;
    # reference 2 staggers it: the shuriken case far front at the frame edge, the boots behind it and further in, the
    # hat's tall case further back; the kunai case likewise at the left edge). Reference 2's case feet measured through
    # the C1 camera (y = 87 + 5455 / (Y + 4.18) px on the floor; x = 724 + 1609 (X - 6) / (Y + 4.18)): shuriken front Y
    # ~3.0 (foot y 850), inner edge X ~8.5; boots front Y ~4.5, inner X ~8.46; hat front Y ~7.1, inner X ~8.5; the back
    # tall case front Y ~10.1, inner X ~8.45 (the left row mirrors it: kunai 3.0 / cloak 4.7 / scrolls 6.8 / tall 10.2,
    # inner X 3.55-3.8). The front pair 5 / 8 moves 0.6 m forward (front face Y 3.0) and 0.15 m outboard (X 2.5-3.3 /
    # 8.7-9.5: the outer half runs behind the C1 frame edge, the parked door leaf); X 1.6 / 10.4 would put them wholly
    # outside C1 (the frame edge at Y 3-4 is X ~2.3-2.8 / 9.2-9.7). The second case sits 0.8 m behind and further in
    # (inner faces X 3.55 / 8.45), the tall cases further back; 0.80 m walkable gaps between them (two cross-hall walks
    # at Y 6.9 / 9.7), the back pair's backs at Y 12.1
    ("1", "L", 6.0, 4.00, 0), ("2", "M", 6.0, 8.70, 0), ("3", "LN", 6.0, 13.40, 0),
    # r16 fix round (blind judge 7/10, point 6 / delta 1: in plan the side rows stood 2.1-2.5 m off the wall bays, a
    # wide floor lane between them; reference 2 / the plan (armory3_reference.png) stand the displays close in front of
    # the lit wall displays, staggered in X, and the tall frames crossed the low cases in front of them from C1): the
    # front pair 5 / 8 stays (the C1 frame edges); behind it the rows step OUT to the walls and alternate in X: the tall
    # cases (now 1.0 x 0.85 m) hug the wall walk (X 1.175-2.025 / 9.975-10.825: 0.88 m off the bays' front X 0.294,
    # the wall-walk capsule at X 0.75 / 11.25 keeps 0.075 m), the low S cases 0.5 m further in (X 1.55-2.65 / 9.35-10.45);
    # the same Y slots (the cross walks at Y 4.6 / 6.9 / 9.7 stay clear)
    # r17 cases round (after r16 the second / tall cases stood OUTBOARD of the front pair (X 1.6-2.1 against 2.90 /
    # 9.10), reversing reference 2's stagger: from C1 case 7's frame ran through case 8's top and the west front case
    # crossed the tall one behind it): every side case now reads on its own through C1. Solved on the C1 projection
    # (camera (6, -4.18, 3.39), 40 mm, shift -0.315 at 1448 x 1086: x = 724 + 1609 (X - 6) / (Y + 4.18), y = 87 +
    # 1609 (3.39 - Z) / (Y + 4.18); the door leaves mask x < 40 / > 1408): each row is a chain of image sectors from
    # the frame edge toward the aisle, a case's outer edge no further out than the one in front of it (world AND
    # image), no case box (plinth + glass) overlapping another in C1 (gaps 3-6 px on the built instances; WorkFiles/armory/hero/room_preview/r17/cases/c1_boxes.json).
    # The front pair runs 0.20 m further out than r16 (outer X 2.30 / 9.70, front face Y 3.15), cut by the C1 frame
    # edge beside the entry lanterns as reference 2's kunai / shuriken cases (visible to x 177 / from 1271; reference
    # ~195 / ~1285); X 1.6 would drop them out of C1 (its edge at Y 3.2 is X ~2.9). Behind them the rows step toward
    # the aisle: west 4 Tall Y 6.75-7.75, G1 S 11.05-12.45, G3 Tall 13.90-14.90 (inner X 4.255, 0.95 m from case 3);
    # east 7 S 6.75-8.15, 6 Tall 11.85-12.85, G2 Tall 13.90-14.90 (the 20 m hall's depth replaces the X spread that
    # the frames cannot take). Walk routes re-laid in walk_check.py (cross walks Y 5.55 / 10.0 / 15.3).
    # r17 fix round (blind judge 7/10 on r17/final): (a1) the r17 chain ended with the back talls G3 / G2 at C1 x
    # 493-577 / 871-955, right over the stair-foot lanterns (x 489-521 / 927-959) and the deck lanterns, which read as
    # lanterns displayed in the cases; reference 2's back talls stand further out, x ~0.21-0.30 / 0.70-0.77 of the frame,
    # the lanterns clear beside the steps. (a2) the r17 chain's C1 gaps were 3-7 px (read as one block). A pure
    # side-by-side chain of four cases cannot fit between the frame edge and the lanterns (x 40-480: the four need
    # ~520 px plus gaps; scratch solver), so each row now STACKS as reference 2 does, a case behind a LOW case standing
    # above it on screen: the front SF (5 / 8, unchanged: the C1 frame edge and the tray), the S (G1 / 7) behind it and
    # inboard (X 3.05-4.15 / 7.85-8.95, Y 4.85-6.25: 0.50 m of floor behind the front case; C1 x 198-439, 21 px
    # clear of it), and the two talls against the wall walk (X 1.15-2.00 / 10.00-10.85): the cloak Tall 4 / the Tall
    # 6 behind the front case (Y 7.60-8.60, C1 x 62-220: as reference 2's cloak behind its kunai case, its plinth seen
    # through the front case's glass) and the back tall G3 / G2 (Y 12.40-13.40): C1 x 253-358 (0.17-0.25; east 0.75-
    # 0.83), 127 px clear of the stair-foot lanterns, 33 px clear of the tall in front of it, 7 px clear of the corner
    # niche (build 1 put it at x 348-440, where the lit niche read inside its glass as the lanterns had), standing
    # wholly above the S on screen (its foot y 416, the S top 417). Plan gaps 0.50 / 1.71 / 3.80 m; from CX the two
    # talls of a row are 114 px apart (r17: one behind the other). The aisles move to X 4.62 / 7.38 (0.47 m clear of
    # the S cases, 0.48 m of cases 1 / 2); walk routes re-laid in walk_check.py (cross walks Y 6.95 / 10.0 / 15.3, the
    # rows' own gaps Y 9.6 / 11.4 / 14.3)
    # r18 cases round (r17 judge 7/10 on r17/final: (1) from C1 the front SF's top rail landed on the plinth of the tall
    # behind it, one stacked object; (2) the rows zig-zagged on screen (5 at the wall, G1 inward, 4 back out, G3 out)
    # where reference 2's side row is ONE diagonal stepping inward as it recedes; (3) G1's glass filled CW's
    # foreground). Solved on the C1 projection (work/solve*.py in WorkFiles/armory/hero/room_preview/r18/cases): each
    # row's four case boxes (plinth + glass, whole footprint) must step up AND inward on screen (foot y falling, both x
    # edges rising, west), 10+ px apart, the back ones clear of the lit corner niche (x 365-413, y 165-232), the rear
    # alcove, the stair-foot lantern (x 489-521, y 280-359) and the deck lantern (east mirrored: x' = 1448 - x). Two
    # rules fall out of the projection: a case behind a 2.2 m tall can never stand above it on screen (its foot would
    # have to be over y ~230), so it must stand wholly inboard of it; and the back tall must end left of the niche
    # (x <= 355), so it is pinned near X 1.15-2.0, Y ~12-13. So each row runs: the LOW front SF (5 / 8, unchanged in
    # plan, now +0.90: see CASES), the cloak / hat tall (4 / 6) at the wall walk 3.5 m behind it, standing wholly above
    # it on screen, the back tall (G3 / G2) further back beside it on screen, and the S (G1 / 7) last, inboard at the
    # rear, beside the back tall. C1 boxes (x0, x1, y0, y1; solver, whole footprints): 5 (40, 177, 557, 831), 4 (73,
    # 228, 234, 540), G3 (240, 348, 199, 425), G1 (369, 467, 267, 392); east mirrored. Gaps: 5-4 16 px (y), 4-G3 13
    # px (x), G3-G1 20 px (x); G3 17 px from the niche, G1 22 px from the stair-foot lantern. Reference 2's row (the
    # same measure): kunai (28, 195, 545, 855), cloak (130, 312, 325, 700), scrolls (258, 407, 400, 590), tall (287,
    # 450, 255, 470), overlapping by 90-150 px where ours keep clear; its scroll case is third (ours is last: third,
    # behind a tall, it would have to stand inboard of that tall and push the back tall into the niche). Plan: 5 X
    # 2.30-3.10, Y 3.15-4.35; 4 X 1.13-1.98, Y 7.85-8.85; G3 X 1.15-2.00, Y 11.95-12.95; G1 X 2.05-2.95, Y 13.70-14.90
    # (gaps 3.50 / 3.10 / 0.75 m); the aisles widen to X 3.10-5.10 / 6.90-8.90 (walk routes at X 4.10 / 7.90).
    # (The table keeps its old label order, so the CaseLight_NN numbering is unchanged.)
    # r18 final fix (the r18 combined judge 8/10, delta 1: "the rear tall case and the rear short case then jump inward
    # and sit almost side by side, with their bottoms 25 px apart"; delta 2: more margin): the smaller talls / S (see
    # CASES), the back tall G3 / G2 forward and inward to Y 10.50-11.40, X 1.60-2.35, the S G1 / 7 back to Y
    # 13.93-14.93 (0.37 m before the cross walk at Y 15.3), X 2.13-2.93. Through C1 (1448 x 1086) the inner
    # plinth edges (x @ foot y) run 5 (171, 821), 4 (211, 540), G3 (347, 459), G1 (466, 388): 4 -> G3 -> G1 one straight
    # line in two even steps ((136, -81), (119, -71); r18: (120, -115), (119, -33)); silhouette gaps 5-4 33, 4-G3 30,
    # G3-G1 33 px (r18: 18 / 13 / 20), G3 21 px from the lit niche, G1 23 px from the stair-foot lantern. The first step
    # (5 -> 4, 40 px inward) cannot open further without the cases overlapping: the front tall has to stand wholly above
    # the low front case, and the back tall wholly beside it and left of the niche. From CX the S / back-tall overlap
    # (-173 px) is gone; the back tall and the front tall overlap there by ~50 px instead (no layout clears both)
    # r19 (USER DECISION 2026-09-30 "copy the reference order"; reference 2's own on-screen overlap between neighbouring
    # cases, ~90-150 px, is ACCEPTED, no zero-overlap rule any more): each side row follows reference 2's order and C1
    # screen placement. West from the entry: 5 the LOW kunai case (S) beside the entry lantern, 4 the tall cloak case, G1
    # the scroll case (S), G3 a tall case near the stairs; east: 8 the shuriken case (SF, the tray, rot -90 kept), 7 the
    # boots case (S), 6 the hat case (MT), G2 a tall case near the stairs. Fitted per case on the C1 projection
    # (WorkFiles/armory/hero/room_preview/r19/a/work/solve.py: every plinth + glass corner, visible x 40-1408) to
    # reference 2's boxes measured on 2x crops (x0, x1, y0, y1 of 1448 x 1086): kunai (28, 195, 545, 855), cloak (130,
    # 313, 310, 700), scrolls (255, 407, 400, 590), W rear tall (287, 450, 255, 470), shuriken (1260, 1408, 625, 855),
    # boots (1180, 1410, 472, 715), hat (1078, 1210, 344, 575), E rear tall (1000, 1130, 255, 472). Ours (the fit):
    # 5 (-93, 194, 545, 856), 4 (122, 321, 287, 705), G1 (256, 405, 394, 594), G3 (307, 429, 220, 487); 8 (1260, 1522,
    # 600, 868), 7 (1183, 1405, 460, 701), 6 (1074, 1214, 337, 578), G2 (1004, 1125, 220, 485). The rear talls stand
    # ~35 px taller on screen than reference 2's (the 1.70 m glass is the user's) and the shuriken case keeps its
    # rotation for the tray. Plan: the rows run X 2.40-3.67 / 8.52-9.76 (about halfway from the wall displays, front X
    # 0.294, toward the centre column, X 5.10), gaps along each row 0.94 / 1.19 / 1.89 m (west) and 0.90 / 1.43 / 1.85 m
    # (east), the aisles to the centre cases 1.43 / 1.62 m; the rear talls' C1 boxes end at x 429 / 1004, clear of the
    # stair-foot lanterns (x 489-521 / 927-959). The table keeps its old label order (the CaseLight_NN numbering).
    ("5", "S", 2.90, 3.31, 0), ("G1", "S", 3.27, 7.08, 90), ("4", "Tall", 3.15, 5.02, 0),
    ("G3", "Tall", 2.91, 9.84, 0),
    ("8", "SF", 9.06, 3.30, -90), ("7", "S", 9.26, 5.10, 0), ("6", "MT", 8.98, 7.30, 0),
    ("G2", "Tall", 8.97, 9.90, 0),
    # r18 final fix: ("5", "SF", 2.70, 3.75, 90), ("G1", "S", 2.53, 14.43, 90), ("4", "Tall", 1.505, 8.30, 90),
    # ("G3", "Tall", 1.975, 10.95, 90), ("8", "SF", 9.30, 3.75, -90), ("7", "S", 9.47, 14.43, -90),
    # ("6", "Tall", 10.495, 8.30, -90), ("G2", "Tall", 10.025, 10.95, -90)
    # r18 cases round: ("G1", "S", 2.50, 14.30), ("4", "Tall", 1.555, 8.35), ("G3", "Tall", 1.575, 12.45) and east mirrored
    # rear dais (2026-09-28): the hero table on the +0.90 deck, 15 cm behind the deck edge (Y 14.55-15.45; was 14.85)
    # b4 (judge delta 3: from the entrance the table's base sat right on the top lit band; reference 2 shows a strip of
    # platform in front of it): 35 cm further back, Y 14.90-15.80 (10 cm in front of the painting base)
    # r20: 0.65 m in front of the back wall as before (Y 18.90-19.80; was 15.35 on the 16 m room): 1.30 m of deck in
    # front of it (b9 judge: "the deck strip in front of the table is thin", was 0.50 m)
    ("10", "Hero", 6.0, ROOM_L - 0.65, 0),
]
# genkan (2026-09-28): the entry pair stands on the sunken genkan floor just in front of the black step beam, either
# side of the mat. Entryfix (2026-09-28, the user: "lantern is fine... just keep it the same natural shape as you've
# developed"): the pair is the developed andon SM_AK_Lantern (hero_lantern_vase, 0.46 x 0.46 x 0.645, as the platform
# lanterns; the slim SM_AK_Lantern_Entry is gone), X 3.53-3.99 / 8.01-8.47 (the genkan's side edges 1 cm outboard, the
# bar's ends behind them), Y 2.093-2.553: the back 7 mm off the bar's face (Y 2.56).
# Entryfix r2 (blind judge 6/10: the mat showed ~100 px against the reference's 146, the front case crowded the bar):
# a joint fit of the C1 camera and the entry layout to reference 2 (entryfix/c1fit4.py: lantern silhouettes, bottoms and
# tops, the bar's back edge / arris / foot, case 1's plinth foot, the painting) puts reference 2's lanterns 0.32 m IN
# FRONT of the bar, on the genkan floor beside the mat (zoomed, their bottoms sit ~110 px below the bar's foot, their back
# feet ~60 px): Y 1.57-2.03 (centre 1.80), X unchanged; seen from C1 they still hide the bar's ends (the bar X 3.46-8.54
# is covered to X 3.91 / 8.09 behind them)
