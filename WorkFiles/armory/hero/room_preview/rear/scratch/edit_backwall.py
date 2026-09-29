from pathlib import Path
p = Path(r'C:\Users\Cody\Desktop\Blender_Projects\Scripts\armory\hero\hero_backwall.py')
s = p.read_text(encoding='utf-8')


def rep(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, (old[:70], s.count(old))
    s = s.replace(old, new)


rep('''ENABLED stays False: the user reviews images of every piece before anything goes into the armory.
"""''', '''Rear dais (2026-09-28, the user: "the reference seems to have more depth ... more steps"; build_armory_kit STAIR_* /
LAND_* / DECK_*): armory3_reference2.png's dais is 6 risers of 0.15 m: a lower flight of 5 (Y 12.30-13.50, 0.30 m
going, X 3.80-8.20 in two 2.2 m modules SM_AK_Steps_22; LED lines under the four tread nosings, the 5th riser unlit
with the emblem), a landing at +0.75 across the full width (Y 13.50-14.40: the centre in the stair module, the side zones
SM_AK_Platform_Landing_19, the old platform-edge cabinet front re-proportioned to 0.75 m under a nosing with an LED
line), and one riser (LED line under its nosing) to the deck at +0.90 (Y 14.40-16.00: SM_AK_Platform_Edge_2x1 front
row, SM_AK_Platform_2x1 inner row, 2 x 0.80 m). NEW scripted piece SM_AK_StairCheek: the lacquer cheek blocks either
side of the flight (0.35 m, to the landing, brass cap edge, LED line under the cap). Everything on the deck rises 0.30 m:
the painting bay (PAINT_Z 1.80, the panel 2.15 m to the header beam's underside +3.95, the paper +0.99-3.64, the
picture's ground +1.36 over the hero table's +1.42 top: the same sheet, shifted), the screens (3.10 m, top +4.00), the
LED posts' cove, the heavy posts' foot on the landing (Y 13.67). The newel (SM_AK_LanternPedestal) is now the rear
lanterns' open stand, built in hero_lantern_vase.

ENABLED stays False: the user reviews images of every piece before anything goes into the armory.
"""''')
rep('''DECK_Z, PAINT_Z, PAINT_H_ = 0.60, 1.50, 2.30        # build_armory_kit PAINT_Z / PAINT_H (asserted in painting_panel)''',
    '''DECK_Z, PAINT_Z, PAINT_H_ = 0.90, 1.80, 2.15        # build_armory_kit DECK_Z / PAINT_Z / PAINT_H (asserted in painting_panel)
LAND_Z = 0.75                                        # build_armory_kit LAND_Z (asserted in steps)''')
rep('''PAPER_Z1 = 3.34                                      # world''',
    '''PAPER_Z1 = 3.64                                      # world (rear dais: 3.34 + 0.30)''')
rep('''IMG_Z0 = 1.06                                        # world height of the painting picture's bottom edge''',
    '''IMG_Z0 = 1.36                                        # world height of the painting picture's bottom edge (dais: +0.30)''')
rep('''HEAVY_Y = 13.62         # layout: PLAT_Y + 0.17''', '''HEAVY_Y = 13.67         # layout: HEAVY_Y = LAND_Y + 0.17 (rear dais; was 13.62)''')
rep('''BEAM_Y0, BEAM_Y1 = 13.49, 13.862''', '''BEAM_Y0, BEAM_Y1 = 13.54, 13.862''')
rep('''    b = Build(G, "SM_AK_Post_Heavy_480")
    hw = HEAVY_HW
    b.prism(octagon(0, 0, hw, hw, 0.012), "z", 0.0, 0.603, LQ, grain="z")             # newel base (in the platform)
    b.cbox(-0.145, 0.145, -0.145, 0.145, 0.598, 0.822, BR, 0.005)                      # the solid brass foot block
    b.cbox(-0.137, 0.137, -0.137, 0.137, 0.818, 0.832, LQ, 0.003)                      # dark line over it
    b.prism(octagon(0, 0, 0.14, 0.14, 0.007), "z", 0.830, SQ_Z0 - 0.045, LQ, grain="z")    # the tall shaft''',
    '''    b = Build(G, "SM_AK_Post_Heavy_480")
    hw = HEAVY_HW
    assert abs(G["HEAVY_Y"] - HEAVY_Y) < 1e-6 and abs(G["LAND_Z"] - LAND_Z) < 1e-6, "hero_backwall: HEAVY_Y / LAND_Z"
    F = LAND_Z - 0.60                                                                  # rear dais: the foot on the landing
    b.prism(octagon(0, 0, hw, hw, 0.012), "z", 0.0, 0.603 + F, LQ, grain="z")         # newel base (in the landing)
    b.cbox(-0.145, 0.145, -0.145, 0.145, 0.598 + F, 0.822 + F, BR, 0.005)              # the solid brass foot block
    b.cbox(-0.137, 0.137, -0.137, 0.137, 0.818 + F, 0.832 + F, LQ, 0.003)              # dark line over it
    b.prism(octagon(0, 0, 0.14, 0.14, 0.007), "z", 0.830 + F, SQ_Z0 - 0.045, LQ, grain="z")    # the tall shaft''')
rep('''    b.box(-CH, CH, -0.1, YB, 0.003, 0.598, T, grain="z")                                 # channel filled in the platform
    b.box(-CH, CH, -0.1, YB, LED_TOP, top - 0.003, T, grain="z")                         # and over the strip
    b.box(-CH + 0.0005, CH - 0.0005, YB - 0.0026, YB, 0.598, LED_TOP, LPOST)             # the amber strip
    for s in (-1, 1):                                                                     # the washes on the walls
        xa, xb = sorted((s * (CH - 0.0012), s * CH))
        b.box(xa, xb, -0.097, YB - 0.0005, 0.600, LED_TOP - 0.002, LWASH)''',
    '''    b.box(-CH, CH, -0.1, YB, 0.003, DECK_Z - 0.002, T, grain="z")                        # channel filled in the deck
    b.box(-CH, CH, -0.1, YB, LED_TOP, top - 0.003, T, grain="z")                         # and over the strip
    b.box(-CH + 0.0005, CH - 0.0005, YB - 0.0026, YB, DECK_Z - 0.002, LED_TOP, LPOST)    # the amber strip
    for s in (-1, 1):                                                                     # the washes on the walls
        xa, xb = sorted((s * (CH - 0.0012), s * CH))
        b.box(xa, xb, -0.097, YB - 0.0005, DECK_Z, LED_TOP - 0.002, LWASH)''')
i0 = s.index('NEWEL_H, NEWEL_W = 0.85, 0.23')
i1 = s.index('def deck_boards(')
s = s[:i0] + '''# rear dais (2026-09-28): SM_AK_LanternPedestal (the slim newel, final r1 / r2) is now the rear lanterns' open stand,
# built with the lantern's members in hero_lantern_vase.py


''' + s[i1:]
i0 = s.index('def deck_boards(')
i1 = s.index('def paper_bay(')
s = s[:i0] + Path(r'C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory\hero\room_preview\rear\scratch\dais_block.py').read_text(encoding='utf-8') + s[i1:]
rep('''    b = Build(G, "SM_AK_RearScreen")
    H, ST, RB, RT, BEAD = 3.4, 0.075, 0.075, 0.075, 0.012''', '''    b = Build(G, "SM_AK_RearScreen")
    H, ST, RB, RT, BEAD = G["SCREEN_H"], 0.075, 0.075, 0.075, 0.012   # rear dais: 3.10 m on the +0.90 deck (was 3.4)''')
rep('''    return [steps(G), platform_edge(G), platform_top(G), painting_panel(G), painting_base(G), rear_screen(G),
            post_led(G), post_heavy(G), lantern_pedestal(G), downlight(G), downlight_box(G), canopy(G), top_beam(G)]''',
    '''    return [steps(G), platform_edge(G), platform_top(G), landing(G), stair_cheek(G), painting_panel(G),
            painting_base(G), rear_screen(G), post_led(G), post_heavy(G), downlight(G), downlight_box(G), canopy(G),
            top_beam(G)]''')
p.write_text(s, encoding='utf-8')
print("ok")
