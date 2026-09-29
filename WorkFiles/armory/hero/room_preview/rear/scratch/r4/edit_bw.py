p = r'C:\Users\Cody\Desktop\Blender_Projects\Scripts\armory\hero\hero_backwall.py'
s = open(p, encoding='utf-8').read()


def rep(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, (old[:70], s.count(old))
    s = s.replace(old, new)


rep('''HEAVY_Y = 13.67         # layout: HEAVY_Y = LAND_Y + 0.17 (rear dais; was 13.62)''',
    '''HEAVY_Y = 13.35         # layout: HEAVY_Y = LAND_Y - 0.15 (rear dais b4: on the hall floor, back face on the plinth face)''')
rep('''BEAM_Y0, BEAM_Y1 = 13.54, 13.862         # 2 cm behind the heavy posts' front; 1.3 cm in front of the cross beam''',
    '''BEAM_Y0, BEAM_Y1 = 13.22, 13.862         # 2 cm behind the heavy posts' front (b4: 13.20); 1.3 cm in front of the cross beam''')
rep('''    F = LAND_Z - 0.60                                                                  # rear dais: the foot on the landing
    b.prism(octagon(0, 0, hw, hw, 0.012), "z", 0.0, 0.603 + F, LQ, grain="z")         # newel base (in the landing)
    b.cbox(-0.145, 0.145, -0.145, 0.145, 0.598 + F, 0.822 + F, BR, 0.005)              # the solid brass foot block''',
    '''    F = -0.60                                         # rear dais b4 (judge delta 2): the foot on the hall floor
    b.cbox(-0.148, 0.148, -0.148, 0.148, 0.0, 0.822 + F, BR, 0.005)                    # the solid brass foot block''')
rep('''    b = Build(G, "SM_AK_Platform_Edge_2x1")
    b.box(0, 2, 0.03, DECK_D, 0, LAND_Z, LQ)                                              # carcass (in the landing)
    riser(b, 2.0, -0.02, LAND_Z + 0.001, DECK_Z, "deck", 0.10)                            # the upper riser
    b.box(0, 2, 0.10, DECK_D, LAND_Z + 0.001, DECK_Z - 0.03, LQ)                          # body under the deck panels
    deck_boards(b, 0.10, DECK_D)
    return b.done([(0, 2, -0.02, DECK_D, 0, DECK_Z)])''',
    '''    b = Build(G, "SM_AK_Platform_Edge_22")
    W = 2.2                                           # b4: the centre bay only (X 3.80-8.20, two modules)
    b.box(0, W, 0.03, DECK_D, 0, LAND_Z, LQ)                                              # carcass (in the landing)
    # b4 (judge delta 3): no LED line: the landing and the deck read as one platform strip in front of the hero table
    riser(b, W, -0.02, LAND_Z + 0.001, DECK_Z, "landing", 0.10)                           # the upper riser (unlit)
    b.box(0, W, 0.10, DECK_D, LAND_Z + 0.001, DECK_Z - 0.03, LQ)                          # body under the deck panels
    deck_boards(b, 0.10, DECK_D, x1=W)
    return b.done([(0, W, -0.02, DECK_D, 0, DECK_Z)])''')

i0 = s.index('def landing(G):')
i1 = s.index('def steps(G):')
side = '''def side_plinth(G):
    """b4 (blind judge delta 1: reference 2 and back_wall.png show solid panelled plinth faces either side of the
    flight, nothing stepped there): the side zones (X 0-3.80 / 8.20-12) are one plinth from the landing front (y 0 =
    LAND_Y 13.50) back to Y 15.20, up to the deck (+0.90), 1.9 x 1.70 m modules. The old platform-edge front (black
    lacquer - the polished top ends in a thick nosing; under it a small shadow reveal, a plain fascia band, a fine groove
    line, then the face frame round two recessed fields, each ringed by a raised bolection moulding) re-proportioned to
    0.90 m (the fields 30 cm taller), a polished brass edge line along the nosing's front instead of the LED band."""
    b = Build(G, "SM_AK_Platform_Side_19")
    W, D, dz = 1.9, 1.70, DECK_Z - 0.60
    NOSE, REVEAL, FASCIA, GROOVE, TOP = (EDGE_NOSE + dz, EDGE_REVEAL + dz, EDGE_FASCIA + dz, EDGE_GROOVE + dz,
                                         EDGE_TOP + dz)
    b.box(0, W, 0.03, D, 0, DECK_Z - 0.03, LQ)                                            # carcass (black lacquer)
    deck_boards(b, 0.006, D, z1=DECK_Z, w=0.85, x1=W)                                     # polished deck top
    nose = [(-0.017, NOSE), (0.0062, NOSE), (0.0062, DECK_Z), (-0.014, DECK_Z), (-0.020, DECK_Z - 0.006),
            (-0.020, NOSE + 0.003)]
    b.prism(nose, "x", 0.0, W, LQ, grain="x", mat_fn=top_is(DECK, LQ), grow=False)       # nosing board
    b.box(0.0005, W - 0.0005, -0.0215, -0.0165, NOSE + 0.008, NOSE + 0.020, BR, grain="x")   # brass edge line
    b.box(0, W, 0.024, 0.03, REVEAL - 0.004, NOSE + 0.001, LQ, grain="x")                 # shadow reveal (2.8 cm deep)
    b.box(0, W, -0.004, 0.03, FASCIA, REVEAL, LQ, grain="x")                              # plain fascia band
    b.box(0, W, 0.014, 0.03, GROOVE - 0.004, FASCIA + 0.002, LQ, grain="x")              # groove line (1.8 cm deep)
    b.box(0, W, -0.0036, 0.028, TOP, GROOVE, LQ, grain="x")                               # top rail
    b.box(0, W, -0.004, 0.03, EDGE_RAIL[0], EDGE_RAIL[1], LQ, grain="x")                  # bottom rail
    b.box(0, W, 0.012, 0.03, 0.0, EDGE_RAIL[0], LQ, grain="x")                            # recessed toe plinth
    b.box(0, W, 0.020, 0.03, EDGE_RAIL[1] - 0.003, TOP + 0.003, LQ, grain="x")            # recessed fields (2.4 cm)
    posts = [(0.001, 0.02), (W / 2 - 0.02, W / 2 + 0.02), (W - 0.02, W - 0.001)]
    for x0, x1 in posts:
        b.box(x0, x1, -0.0030, 0.028, EDGE_RAIL[1] - 0.005, TOP + 0.005, LQ, grain="z")
    for i in range(len(posts) - 1):                                                       # raised bolection mouldings
        b.ring(posts[i][1], posts[i + 1][0], EDGE_RAIL[1], TOP, 0.036, 0.024, -0.0130, LQ, "xz", c=0.012)
    return b.done([(0, W, -0.02, D, 0, DECK_Z)])


'''
s = s[:i0] + side + s[i1:]

i0 = s.index('def stair_cheek(G):')
i1 = s.index('def paper_bay(')
newel = '''def stair_newel(G):
    """b4 (blind judge delta 7: reference 2 / back_wall.png flank the flight with square newel posts; the b3 cheek blocks
    with LED lines along their caps read as sloping stringers): X 3.45-3.80 / 8.20-8.55 from the stair foot (y 0 =
    STAIR_Y0 12.30). A square 0.35 m newel at the foot, 1.00 m tall, in the heavy posts' finish: plain gloss black lacquer,
    a solid polished brass shoe (10 cm) and a brass cap block (6 cm) with a dark line under it; behind it a plain black
    lacquer side wall to the plinth face (Y 13.50) at the landing's +0.75 with a thin brass top edge. No LED."""
    b = Build(G, "SM_AK_StairNewel")
    W, ND, NH, L, H = G["CHEEK_W"], G["NEWEL_D"], G["NEWEL_H"], G["LAND_Y"] - G["STAIR_Y0"], LAND_Z
    b.cbox(0.0, W, 0.0, ND, 0.0, 0.10, BR, 0.004)                                         # the brass shoe
    b.cbox(0.004, W - 0.004, 0.004, ND - 0.004, 0.098, NH - 0.072, LQ, 0.004, grain="z")  # the newel shaft
    b.cbox(0.010, W - 0.010, 0.010, ND - 0.010, NH - 0.074, NH - 0.058, LQ, 0.002)        # dark line under the cap
    b.cbox(0.0, W, 0.0, ND, NH - 0.060, NH, BR, 0.005)                                    # the brass cap block
    b.cbox(0.012, W - 0.012, ND - 0.002, L - 0.001, 0.0, H - 0.012, LQ, 0.003, grain="y")  # the side wall
    b.cbox(0.008, W - 0.008, ND - 0.002, L - 0.001, H - 0.013, H, BR, 0.002, grain="y")   # its brass top edge
    return b.done([(-0.005, W + 0.005, -0.005, ND + 0.005, 0, NH), (0.005, W - 0.005, ND, L, 0, H)])


'''
s = s[:i0] + newel + s[i1:]
rep('''    return [steps(G), platform_edge(G), platform_top(G), landing(G), stair_cheek(G), painting_panel(G),''',
    '''    return [steps(G), platform_edge(G), platform_top(G), side_plinth(G), stair_newel(G), painting_panel(G),''')
open(p, 'w', encoding='utf-8').write(s)
print("ok")
