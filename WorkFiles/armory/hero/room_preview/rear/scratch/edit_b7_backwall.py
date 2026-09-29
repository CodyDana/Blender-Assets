p = r'C:\Users\Cody\Desktop\Blender_Projects\Scripts\armory\hero\hero_backwall.py'
s = open(p, encoding='utf-8').read()


def rep(old, new):
    global s
    assert s.count(old) == 1, old[:60]
    s = s.replace(old, new)


rep('''PAINT_SW, HALO_W, PAINT_RAIL = 0.10, 0.06, 0.03     # pilaster width, halo width, rail height
PAPER_W = 2.4 - 2 * (PAINT_SW + HALO_W)              # 2.08 m''', '''# rear dais b7 (blind judge delta 7: the paper read portrait, ~170 x 190 px in C1, and the bay's painting larger than
# reference 2's, which is about square over the table): 20 cm pilasters (was 10 cm), so the paper is 1.88 m wide
PAINT_SW, HALO_W, PAINT_RAIL = 0.20, 0.06, 0.03     # pilaster width, halo width, rail height
PAPER_W = 2.4 - 2 * (PAINT_SW + HALO_W)              # 1.88 m (was 2.08)''')
rep('''PAPER_Z1 = 3.64                                      # world (rear dais: 3.34 + 0.30)
IMG_Z0 = 1.36                                        # world height of the painting picture's bottom edge (dais: +0.30)''', '''# b7 (judge delta 7): the paper ends at +3.30 (was 3.64): 1.88 m over the table top (+1.42) by 1.88 m wide, square as
# reference 2; the picture (1.88 / PAINT_ASPECT = 2.15 m tall) starts at +1.30, just under the table top (reference 2
# hides its foot behind the table), and its top 7 % (plain paper over the crown) is cut
PAPER_Z1 = 3.30                                      # world (b6: 3.64)
IMG_Z0 = 1.30                                        # world height of the painting picture's bottom edge (b6: 1.36)''')
rep('''HEAVY_Y = 13.33         # layout: HEAVY_Y = LAND_Y - 0.17 (rear dais b4: on the hall floor, back face on the plinth nosing)''',
    '''HEAVY_Y = 13.33         # layout HEAVY_Y (rear dais b4: on the hall floor, Y 13.18-13.48)''')
rep('''    # b4 (judge delta 3): no LED line: the landing and the deck read as one platform strip in front of the hero table
    riser(b, W, -0.02, LAND_Z + 0.001, DECK_Z, "landing", 0.10)                           # the upper riser (unlit)''',
    '''    # b7 (judge delta 3): the flight's 6th riser, lit like the others, its nose the deck's polished edge
    riser(b, W, -0.02, LAND_Z + 0.001, DECK_Z, "deck", 0.10)                              # the 6th riser (lit)''')
rep('''def riser(b, W, yn, z_lo, zt, lit, depth_to, nose_h=0.04):''', '''def riser(b, W, yn, z_lo, zt, lit, depth_to, nose_h=0.04, wash=True):''')
rep('''        w0, w1 = z_lo + 0.006, zb - 0.0215
        b.box(''', '''        w0, w1 = z_lo + 0.006, zb - 0.0215
        if not wash:                                                                      # b7: the cabinets' lit ledge
            return
        b.box(''')

SIDE = '''def side_plinth(G):
    """b7 (blind judge deltas 4 / 6: the b4-b6 plinth faces read as flat black voids; reference 2's side zones are a
    terraced, panelled base under the rack alcoves): the side zones (X 0-3.80 / 8.20-12; y 0 = LAND_Y 13.56 back to
    Y 15.20, 1.9 m modules) are terraced in the flight's own rows. At the front a black lacquer door cabinet to +0.60 (the
    4th riser's line): two doors per module, each a recessed field inside a raised face frame with small polished brass
    corner brackets, under the steps' nose with its lit ledge (the amber line under the nose, no wash on the doors);
    then a plain recessed riser (+0.60 to +0.75, unlit as the flight's 5th) to a tread at +0.75 (y GOING), and the lit
    deck riser at y 2 x GOING (DECK_Y 14.40) to the polished deck."""
    b = Build(G, "SM_AK_Platform_Side_19")
    W, D, GO, CZ = 1.9, 1.64, G["GOING"], G["CAB_Z"]
    b.box(0, W, 0.03, D, 0, CZ - 0.04, LQ)                                                # cabinet carcass
    riser(b, W, -0.02, 0.0, CZ, True, GO + 0.005, wash=False)                             # cabinet face + lit ledge
    yr = 0.005                                                                            # the cabinet's face
    FR = 0.012                                                                            # face frame proud of it
    zt = CZ - 0.04 - 0.0215 - 0.02                                                        # under the lit ledge
    for x0 in (0.0, W / 2):                                                               # two doors per module
        x1 = x0 + W / 2
        for a0, a1, z0, z1, g in ((x0 + 0.004, x0 + 0.06, 0.0, zt, "z"), (x1 - 0.06, x1 - 0.004, 0.0, zt, "z"),
                                  (x0 + 0.06, x1 - 0.06, 0.0, 0.09, "x"), (x0 + 0.06, x1 - 0.06, zt - 0.07, zt, "x")):
            b.cbox(a0, a1, yr - FR, yr + 0.002, z0, z1, LQ, 0.003, grain=g)
        fx0, fx1, fz0, fz1 = x0 + 0.06, x1 - 0.06, 0.09, zt - 0.07                         # the recessed field
        for cx, sx in ((fx0, 1), (fx1, -1)):                                              # brass corner brackets
            for cz, sz in ((fz0, 1), (fz1, -1)):
                xa, xb = sorted((cx + sx * 0.012, cx + sx * 0.075))
                za, zb_ = sorted((cz + sz * 0.012, cz + sz * 0.018))
                b.box(xa, xb, yr - 0.004, yr + 0.001, za, zb_, BR, grain="x")
                xa, xb = sorted((cx + sx * 0.012, cx + sx * 0.018))
                za, zb_ = sorted((cz + sz * 0.018, cz + sz * 0.075))
                b.box(xa, xb, yr - 0.004, yr + 0.001, za, zb_, BR, grain="z")
    b.box(0, W, GO + 0.03, D, CZ - 0.041, LAND_Z - 0.04, LQ)                              # body under the tread
    riser(b, W, GO - 0.02, CZ - 0.001, LAND_Z, False, 2 * GO + 0.005)                    # recessed riser, tread +0.75
    b.box(0, W, 2 * GO + 0.03, D, LAND_Z - 0.041, DECK_Z - 0.03, LQ)                      # body under the deck
    riser(b, W, 2 * GO - 0.02, LAND_Z - 0.001, DECK_Z, "deck", 2 * GO + 0.10)             # the lit deck riser
    deck_boards(b, 2 * GO + 0.10, D, x1=W)
    return b.done([(0, W, -0.02, D, 0, CZ), (0, W, GO - 0.02, D, CZ, LAND_Z), (0, W, 2 * GO - 0.02, D, LAND_Z, DECK_Z)])


'''
a = s.index("def side_plinth(G):")
e = s.index("def steps(G):")
s = s[:a] + SIDE + s[e:]

STEPS = '''def steps(G):
    """The flight, 2.2 m module (two side by side, X 3.80-8.20; local y 0 = the stair foot, STAIR_Y0 12.30): b7 (blind
    judge delta 3: b4-b6 read as four steps up to a dark landing pad) the first five of six uniform risers of 0.15 m with
    a 0.42 m going (GOING) up to the deck riser (SM_AK_Platform_Edge_22 at y 2.10 = DECK_Y), ONE crisp amber line under
    each nose with the warm wash down the riser (r4 / final r2), except the 5th riser (+0.60 to +0.75), unlit: it
    carries the emblem (reference 2's unlit 5th riser). Every tread is the lacquer tread board."""
    assert abs(G["LAND_Z"] - LAND_Z) < 1e-6 and abs(G["DECK_Z"] - DECK_Z) < 1e-6, "hero_backwall: LAND_Z / DECK_Z"
    b = Build(G, "SM_AK_Steps_22")
    W, LD, GO = 2.2, G["DECK_Y"] - G["STAIR_Y0"], G["GOING"]
    cols = []
    for k in range(5):
        top = k == 4
        riser(b, W, -0.02 + GO * k, 0.15 * k, 0.15 * (k + 1), not top, LD if top else GO * (k + 1) + 0.005,
              nose_h=0.032 if top else 0.04)   # b3: the emblem (to +0.716) clears the 5th nose
        cols.append((0, W, -0.02 + GO * k, LD, 0.15 * k, 0.15 * (k + 1)))
    return b.done(cols)


def stair_cheek(G):
    """b7 (blind judge deltas 1 / 8: the b4-b6 1.00 m newel block beside a lantern on its own stand, and a big raw brass
    top on the side wall; reference 2: the lantern sits on a short post at each end of the flight, thin gold trim lines
    only): X 3.45-3.80 / 8.20-8.55 from the stair foot (y 0 = STAIR_Y0) to the side cabinet's face (LAND_Y), a low black
    lacquer cheek to +0.45 (the 3rd tread's height). Its front end (0.35 m square) is the newel the stair-foot lantern
    SM_AK_Lantern_S stands on: a polished brass shoe (6 cm) and a thin brass cap line under a lacquer top plate, a 1.2 cm
    shadow reveal behind it; the wall behind with a thin brass line on both top arrises."""
    b = Build(G, "SM_AK_StairCheek")
    W, H, L = G["CHEEK_W"], G["CHEEK_H"], G["LAND_Y"] - G["STAIR_Y0"]
    b.cbox(-0.004, W + 0.004, -0.004, W + 0.004, 0.0, 0.06, BR, 0.003)                  # brass shoe
    b.cbox(0.0, W, 0.0, W, 0.058, H - 0.021, LQ, 0.004, grain="z")                        # the newel
    b.cbox(-0.003, W + 0.003, -0.003, W + 0.003, H - 0.022, H - 0.010, BR, 0.002)        # brass cap line
    b.cbox(-0.002, W + 0.002, -0.002, W + 0.002, H - 0.011, H, LQ, 0.003)                # top plate
    b.box(0.012, W - 0.012, W + 0.002, W + 0.014, 0.0, H - 0.03, LQ, grain="z")          # shadow reveal
    b.cbox(0.0, W, W + 0.013, L, 0.0, H - 0.004, LQ, 0.004, grain="y")                    # the side wall
    for x0, x1 in ((-0.002, 0.004), (W - 0.004, W + 0.002)):                              # thin brass top lines
        b.box(x0, x1, W + 0.02, L - 0.004, H - 0.016, H - 0.009, BR, grain="y")
    return b.done([(0.0, W, 0.0, L, 0.0, H)])


'''
a = s.index("def steps(G):")
e = s.index("def paper_bay(")
s = s[:a] + STEPS + s[e:]
open(p, 'w', encoding='utf-8').write(s)
print("ok")
