CASES = {  # type: (width along local X, depth along local Y, plinth height, glass height)
    # building r2, fitted to reference 2 through the C1 camera (BUILD_NOTES): the front case is a low plinth under tall
    # glass (plinth top +0.50, glass top +1.45), the kasa case a low base under tall glass; the hero is a low two-tier
    # lacquer TABLE (no glass: G = 0)
    # r20 b3 (blind judge 7/10, delta 4: case 1 read too big from the entrance, hiding case 2 and the axis): the front
    # case's glass 0.95 -> 0.70 (glass top +1.20)
    "L": (1.8, 1.3, 0.50, 0.70), "LN": (1.6, 1.0, 0.45, 0.75), "M": (1.8, 1.2, 0.70, 0.55),
    # r16 fix round (blind judge delta 1: from C1 the tall cases read as oversized wire boxes, reference 2's hat and
    # back tall cases about half as wide): the Tall footprint 1.5 x 1.1 -> 1.0 x 0.85 m (the 1.70 m glass kept: user
    # decision), still room for a mannequin or a standing item
    # r17 fix round (blind judge 7/10 on r17/final, delta a3: the side low cases' glass was about half the plinth
    # height, where reference 2's kunai / scroll / boots / shuriken cases show glass about as tall as it is wide): the
    # S case a lower plinth under taller glass, 0.90 + 0.45 -> 0.55 + 0.70 (top +1.35 -> +1.25: the back tall behind
    # it then stands wholly above it in C1; b1 at 0.80 hid the tall's plinth foot); the front SF pair keeps its 0.90
    # plinth (the shuriken tray in case 8 sits on it unchanged) under 0.45 -> 0.65 m glass (top +1.55)
    # r18 cases round (r17 judge: the side rows zig-zag; one diagonal wanted): the S case is now the LAST case of each
    # row, inboard of the back tall at the rear, where the C1 room between that tall (x <= 348 / >= 1100) and the
    # stair-foot lantern (x 489 / 959) takes at most 0.9 m of depth: 1.4 x 1.1 -> 1.2 x 0.9 m (heights kept; its
    # glass 0.70 still about as tall as it is deep)
    # r18 final fix (the r18 combined judge 8/10, deltas 1-2: the rows still not one even inward diagonal, and from C1
    # only ~20 px of floor between neighbouring cases, "any camera or FOV change would bring the overlap back"). Solved
    # on the C1 projection with the cases' real silhouettes (WorkFiles/armory/hero/room_preview/r18/final/work/
    # solve_row*.py, local2.py): with the 1.0 x 0.85 talls NO placement gives even 20 px between every pair (the
    # front tall must stand wholly above the low front case, the back tall wholly beside it and left of the lit corner
    # niche); the talls' footprint 1.0 x 0.85 -> 0.90 x 0.75 m (the 1.70 m glass kept: user decision; still room for a
    # mannequin) and the S case 1.2 x 0.9 -> 1.0 x 0.8 m open 30-35 px between every pair
    # r19 (USER DECISION 2026-09-30 "copy the reference order"): the S case is reference 2's medium glass case (the
    # kunai, scroll and boots cases): measured through C1 their plinths are ~0.55 m with the glass top at ~+1.10-1.17,
    # so the glass 0.70 -> 0.60 (top +1.25 -> +1.15)
    "S": (1.0, 0.8, 0.55, 0.60), "Tall": (0.9, 0.75, 0.50, 1.70), "Hero": (2.4, 0.9, 0.52, 0.0),   # r18: "S" (1.0, 0.8, 0.55, 0.70); r18 cases round: "S" (1.2, 0.9, ...), "Tall" (1.0, 0.85, ...)
    # r19 (NEW): reference 2's hat case (east, third from the entry) is neither low nor the 2.2 m tall: through C1 its
    # plinth reads ~0.60 m and its glass ~0.95 m (top ~+1.55) over a near-square footprint; room for the straw hat on a
    # stand with the attire under it
    "MT": (0.8, 0.75, 0.60, 0.95),
    # r20 round 3 (blind judge 7/10, delta 2: the front side cases were cut by both C1 frame edges; reference 2's kunai
    # and shuriken cases are small and sit fully inside it): the front pair's own smaller footprint, 1.20 x 0.80 m (the
    # same plinth and glass heights as "S"; the shuriken tray, 0.54 x 0.44 m with its card, still fits case 8)
    # r18 cases round (r17 judge: from C1 the front SF's +1.55 top rail landed on the plinth of the tall case behind it,
    # the two read as one stacked object; reference 2's front kunai case is LOW, its top ~+1.0-1.1 through the C1 fit):
    # 0.90 + 0.65 -> 0.40 + 0.50 (top +0.90, glass taller than the plinth). Through C1 its top edge falls to y 557, 16 px
    # under the cloak tall's foot (y 540); a +1.00 top would need that tall 0.7 m further back, into the niche's x band.
    # The tray follows the plinth (armory_items.tray_instance: deck +0.404, card top +0.63, 0.27 m under the glass top)
    # r18 final fix: 1.2 -> 1.0 m wide (along world Y; the centre and the tray unchanged: the 0.54 m tray still fits)
    # and the glass 0.50 -> 0.45 (top +0.85; the tray card top +0.63): through C1 its top edge drops from y 557 to 572,
    # 33 px above the tall behind it
    "SF": (1.0, 0.8, 0.40, 0.45),   # r18 cases round: (1.2, 0.8, 0.40, 0.50)
}


# ---- building stage: mesh generators (welded parts for Piece.mesh; outward winding checked by hand, see notes)

