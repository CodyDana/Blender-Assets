def deck_boards(b, y0, y1, n_from=0.0, z0=None, z1=None, w=0.80, x1=2.0):
    """The deck floor: pale greige polished deck panels (x1 / 2 x w m), a 0.8 mm joint chamfer in the finish at every
    panel edge (faint panel joints; only the vertical panel ends show the timber). z1 = the top (default DECK_Z)."""
    z1 = DECK_Z if z1 is None else z1
    z0 = z1 - 0.03 if z0 is None else z0
    edges = [y0] + [n_from + k * w for k in range(1, 5) if y0 < n_from + k * w < y1] + [y1]
    xs = [0.0, x1 / 2, x1]
    for ya, yb in zip(edges, edges[1:]):
        for xa, xb in zip(xs, xs[1:]):
            b.cbox(xa, xb, ya, yb, z0, z1, LQ, 0.0012, grain="x", mat_fn=top_is(DECK, LQ, 0.5))


DECK_D = 0.80   # rear dais: the deck modules are 2 x 0.80 m (two rows, Y 14.40-16.00)


def platform_top(G):
    """The inner 2 x 0.80 m deck module (+0.90): black lacquer body under two polished deck panels (only the top shows)."""
    assert abs(G["DECK_Z"] - DECK_Z) < 1e-6, "hero_backwall: DECK_Z changed"
    b = Build(G, "SM_AK_Platform_2x1")
    b.box(0, 2, 0, DECK_D, 0, DECK_Z - 0.03, LQ)          # final r1: black lacquer sides (were striped timber)
    deck_boards(b, 0.0, DECK_D)
    return b.done([(0, 2, 0, DECK_D, 0, DECK_Z)])


EDGE_NOSE = 0.568     # underside of the 3.2 cm nosing (clear over the riser emblem SM_AK_EmblemDisc_12, top +0.566)
EDGE_REVEAL = 0.553   # a 1.5 cm shadow reveal under the nosing (recessed 1.6 cm)
EDGE_FASCIA = 0.440   # the plain deck-edge fascia band +0.44 to +0.553, over a fine groove line
EDGE_GROOVE = 0.432
EDGE_TOP = 0.405      # top of the fields (the face frame's top rail runs to the groove)
EDGE_RAIL = (0.045, 0.075)   # the bottom rail over the recessed toe
# (these are the old +0.60 platform edge's rows; landing() lifts every row above the bottom rail by LAND_Z - 0.60)


def riser(b, W, yn, z_lo, zt, lit, depth_to):
    """One stair riser and its tread board across local x 0-W (back_wall.png's steps, r4 / final r1 / r2): a near-black
    lacquer riser block from z_lo to under the nose, a 4 cm tread board with a rounded-off nose at yn (its top in the
    polished deck finish for the landing and the deck, else lacquer), and - when lit - ONE crisp 2 cm amber line tucked
    under the nose (1.25 cm behind it) with a warm wash fading down the riser face below it (final r2)."""
    zb = zt - 0.04
    yr = yn + 0.025                                                                       # riser face
    b.box(0, W, yr, depth_to, z_lo, zb, LQ, grain="x")                                    # riser block
    nose = [(yn + 0.003, zb), (depth_to, zb), (depth_to, zt), (yn + 0.006, zt), (yn, zt - 0.006), (yn, zb + 0.003)]
    kw = {"mat_fn": top_is(DECK, LQ)} if lit in ("deck", "landing") else {}
    b.prism(nose, "x", 0.0, W, LQ, grain="x", **kw)                                       # tread board
    if lit in (True, "deck"):
        b.box(0.0005, W - 0.0005, yn + 0.0125, yr + 0.002, zb - 0.0215, zb - 0.0015, LINE)   # the line under the nose
        w0, w1 = z_lo + 0.006, zb - 0.0215
        b.box(0.001, W - 0.001, yr - 0.0008, yr + 0.001, w0, w1, SWASH, grow=False,
              unique=(lambda n: n[1] < -0.9,
                      lambda p, w1=w1, w0=w0: (min(max((w1 - p[2]) / (0.45 * (w1 - w0)), 0.0), 0.99), 0.5)))


def platform_edge(G):
    """The deck's front 2 x 0.80 m module (faces -Y at y 0 = DECK_Y 14.40): its upper riser over the landing (+0.75 to
    +0.90, reference 2's 6th riser with its own LED line) in the steps' section - a near-black riser under a 4 cm
    nosing whose top is the polished deck, one crisp amber line under the nose with the warm wash down the riser - over
    a lacquer carcass hidden in the landing (y >= 0.03 below +0.75), and the deck panels behind it."""
    b = Build(G, "SM_AK_Platform_Edge_2x1")
    b.box(0, 2, 0.03, DECK_D, 0, LAND_Z, LQ)                                              # carcass (in the landing)
    riser(b, 2.0, -0.02, LAND_Z + 0.001, DECK_Z, "deck", 0.10)                            # the upper riser
    b.box(0, 2, 0.10, DECK_D, LAND_Z + 0.001, DECK_Z - 0.03, LQ)                          # body under the deck panels
    deck_boards(b, 0.10, DECK_D)
    return b.done([(0, 2, -0.02, DECK_D, 0, DECK_Z)])


def landing(G):
    """The landing's side zones (1.9 m modules, faces -Y at y 0 = LAND_Y 13.50, +0.75, 0.90 m deep to the deck riser).
    The old platform-edge front (back_wall.png: black lacquer - the polished top ends in a thick nosing; under it a
    small shadow reveal, a plain fascia band, a fine groove line, then the face frame round two recessed fields, each
    ringed by a raised bolection moulding in the same black lacquer) re-proportioned to 0.75 m (the fields 15 cm
    taller), with an LED line under the nosing (reference 2's side zones: a dark door cabinet with a lit top edge)."""
    b = Build(G, "SM_AK_Platform_Landing_19")
    W, D, dz = 1.9, 0.90, LAND_Z - 0.60
    NOSE, REVEAL, FASCIA, GROOVE, TOP = (EDGE_NOSE + dz, EDGE_REVEAL + dz, EDGE_FASCIA + dz, EDGE_GROOVE + dz,
                                         EDGE_TOP + dz)
    b.box(0, W, 0.03, D, 0, LAND_Z - 0.03, LQ)                                            # carcass (black lacquer)
    deck_boards(b, 0.006, D, z1=LAND_Z, w=0.90, x1=W)                                     # polished landing top
    nose = [(-0.017, NOSE), (0.0062, NOSE), (0.0062, LAND_Z), (-0.014, LAND_Z), (-0.020, LAND_Z - 0.006),
            (-0.020, NOSE + 0.003)]
    b.prism(nose, "x", 0.0, W, LQ, grain="x", mat_fn=top_is(DECK, LQ), grow=False)       # nosing board
    b.box(0, W, 0.024, 0.03, REVEAL - 0.004, NOSE + 0.001, LQ, grain="x")                 # shadow reveal (2.8 cm deep)
    b.box(0.0005, W - 0.0005, -0.004, 0.012, REVEAL + 0.0005, NOSE - 0.0005, LINE)        # the LED line under the nose
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
    return b.done([(0, W, -0.02, D, 0, LAND_Z)])


def steps(G):
    """The lower flight, 2.2 m module (two side by side, X 3.80-8.20; local y 0 = the stair foot, STAIR_Y0 12.30), with
    the centre landing behind it: 5 risers of 0.15 m and 0.30 m going (reference 2: 5 risers of ~15 px, lines under the
    nosings at y 317 / 332 / 347 / 362), ONE crisp amber line under each of the four tread nosings with the warm wash down
    the riser (r4 / final r2); the 5th riser (+0.60 to +0.75, at LAND_Y) unlit: it carries the emblem; its tread board is
    the landing's nosing, the landing (+0.75) in the polished deck finish back to the deck riser (y 2.10 = DECK_Y)."""
    assert abs(G["LAND_Z"] - LAND_Z) < 1e-6 and abs(G["DECK_Z"] - DECK_Z) < 1e-6, "hero_backwall: LAND_Z / DECK_Z"
    b = Build(G, "SM_AK_Steps_22")
    W, LD = 2.2, G["DECK_Y"] - G["STAIR_Y0"]
    cols = []
    for k in range(5):
        top = k == 4
        riser(b, W, -0.02 + 0.30 * k, 0.15 * k, 0.15 * (k + 1), "landing" if top else True,
              LD if top else 0.30 * (k + 1) + 0.005)
        cols.append((0, W, -0.02 + 0.30 * k, LD, 0.15 * k, 0.15 * (k + 1)))
    return b.done(cols)


def stair_cheek(G):
    """NEW scripted piece (rear dais): the lacquer cheek block either side of the lower flight (reference 2: dark blocks
    about 27 px wide just inside the heavy posts, X 3.45-3.80 / 8.20-8.55), from the stair foot to the landing front,
    up to the landing's +0.75: a near-black lacquer block under a 3 cm cap slab that overhangs 1 cm, a polished brass
    edge line round the cap's front and sides, and an amber LED line tucked under the cap on the front and both sides."""
    b = Build(G, "SM_AK_StairCheek")
    W, L, H = G["CHEEK_W"], G["LAND_Y"] - G["STAIR_Y0"], LAND_Z
    b.cbox(0.0, W, 0.0, L, 0.0, H - 0.03, LQ, 0.004, grain="y")                           # the block
    b.cbox(-0.01, W + 0.01, -0.01, L, H - 0.03, H, LQ, 0.003, grain="y")                  # the cap slab
    b.box(-0.0125, W + 0.0125, -0.0125, L - 0.002, H - 0.022, H - 0.012, BR)              # brass edge line
    b.box(0.001, W - 0.001, -0.004, 0.0005, H - 0.047, H - 0.034, LINE)                   # LED under the cap: front
    for x0, x1 in ((-0.004, 0.0005), (W - 0.0005, W + 0.004)):                            # and both sides
        b.box(x0, x1, 0.001, L - 0.003, H - 0.047, H - 0.034, LINE)
    return b.done([(-0.01, W + 0.01, -0.01, L, 0, H)])


