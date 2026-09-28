"""table v2: the whorl (R family into the apex, on under the U fan to the top-right limb),
U0 kept to its own region, the V-gap wedge kept clear, stronger bottom keepouts."""
p = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/rewind/wind/wd_tools/wd_passes.py"
s = open(p, encoding="utf-8").read()


def rep(old, new):
    global s
    if old not in s:
        raise SystemExit("anchor not found: " + old[:100])
    s = s.replace(old, new)


# shared whorl geometry (image px): the V-gap wedge and the route on past the apex
rep('''def pass_table():
    E = edge_px''', '''#: REFERENCE_SPEC 4.5: the whorl V-gap, apex (690,252), ~90 px long up-left, ~20 px open
VGAP = np.array([(686, 248), (678, 240), (670, 232), (662, 224), (654, 216), (646, 208), (638, 200), (632, 194),
                 (676, 244), (668, 236), (660, 226), (650, 214), (642, 204), (682, 238), (672, 226), (662, 214),
                 (652, 202), (644, 194)], float)
#: DESIGNED: past the apex the R family runs on under the U fan and leaves over the top-right
#: limb (image angle ~70 deg), hidden all the way
R_ROUTE = np.array([(700, 248), (722, 236), (744, 222), (764, 208), (780, 197), (792, 189)], float)


def pass_table():
    E = edge_px''')

rep('''    T.append(PassFit("U0", ("U0",), (470, 470), (660, 270), [
        EdgeTerm(shift_toward(lin_up[(lin_up[:, 0] > 370)], (450, 250), 14), +1, 0.6, "hide", "LIN under R_in"),
        EdgeTerm(u0r, -1, 1.0, "own", "UA - V-gap"),
    ], width=0.15, width_w=0.1))''', '''    r2_region = probes_between(E("LC"), E("LA"), fr=(0.3, 0.5, 0.7))
    T.append(PassFit("U0", ("U0",), (470, 470), (660, 270), [
        EdgeTerm(shift_toward(lin_up[(lin_up[:, 0] > 370)], (450, 250), 10), +1, 0.6, "hide", "LIN under R_in"),
        EdgeTerm(u0r, -1, 1.0, "own", "UA - V-gap"),
        EdgeTerm(shift_toward(E("WTW", xr=(420, 540)), (480, 400), 3), +1, 0.8, "hide", "its foot under W's cord"),
        EdgeTerm(r2_region, +1, 1.0, "keepout", "R2's region"),
        EdgeTerm(VGAP, +1, 1.0, "keepout", "the whorl V-gap"),
    ], width=0.15, width_w=0.1))''')

rep('''    T.append(PassFit("Rin", ("R_in", "L5"), (600, 300), (258, 712), [
        EdgeTerm(lin, +1, 1.0, "own", "LIN"),
        EdgeTerm(shift_toward(lc[lc[:, 0] < 470], (300, 300), 22), -1, 0.5, "hide", "under R2"),
        EdgeTerm(radial(lin_lo, 1.02), -1, 0.3, "hide", "L5 outer edge at the limb"),
    ], width=0.09, width_w=0.1, knot_deg=6.0, smooth=0.3, max_strain=0.06))
    T.append(PassFit("R3", ("R3",), (620, 200), (240, 350), [
        EdgeTerm(shift_toward(la, (400, 300), 12), +1, 0.6, "hide", "LA under R2"),
        EdgeTerm(radial(la, 1.03), -1, 0.3, "hide", "beyond the limb"),
    ], width=0.10, width_w=0.1))
    T.append(PassFit("R2", ("R2",), (200, 520), (600, 250), [
        EdgeTerm(lc, -1, 1.0, "own", "LC"),
        EdgeTerm(la, +1, 1.0, "own", "LA"),
    ], width=0.17, width_w=0.05))''', '''    # the R family: all three run into the whorl apex and on (woven under the U fan) to the
    # top-right limb; travel toward the whorl, so +1 (left of travel) is the outer side
    rin_route = np.vstack([[(600, 296), (630, 282), (660, 268), (686, 256)], R_ROUTE + [0, 8]])
    T.append(PassFit("Rin", ("R_in", "L5"), (258, 712), (600, 300), [
        EdgeTerm(lin, -1, 1.0, "own", "LIN"),
        EdgeTerm(shift_toward(lc[lc[:, 0] < 470], (300, 300), 16), +1, 0.5, "hide", "under R2"),
        EdgeTerm(radial(lin_lo, 1.0), +1, 0.3, "hide", "L5 outer edge at the limb"),
        EdgeTerm(FL_resample(rin_route, 6.0), 0, 0.5, "own", "on under R2, into the apex and under the fan"),
        EdgeTerm(VGAP, +1, 1.0, "keepout", "the whorl V-gap"),
    ], width=0.09, width_w=0.15, knot_deg=6.0, smooth=0.3, max_strain=0.06))
    r3_route = np.vstack([[(640, 236), (668, 244)], R_ROUTE + [0, -6]])
    T.append(PassFit("R3", ("R3",), (240, 350), (640, 230), [
        EdgeTerm(shift_toward(la, (400, 300), 10), -1, 0.6, "hide", "LA under R2"),
        EdgeTerm(radial(la, 1.0), +1, 0.3, "hide", "beyond the limb"),
        EdgeTerm(FL_resample(r3_route, 6.0), 0, 0.4, "own", "into the apex and under the fan"),
        EdgeTerm(VGAP, +1, 1.0, "keepout", "the whorl V-gap"),
    ], width=0.10, width_w=0.15))
    r2_route = np.vstack([[(640, 262), (672, 256)], R_ROUTE])
    T.append(PassFit("R2", ("R2",), (200, 520), (600, 250), [
        EdgeTerm(lc, -1, 1.0, "own", "LC"),
        EdgeTerm(la, +1, 1.0, "own", "LA"),
        EdgeTerm(FL_resample(r2_route, 6.0), 0, 0.4, "own", "into the apex and under the fan"),
        EdgeTerm(VGAP, +1, 1.0, "keepout", "the whorl V-gap"),
    ], width=0.17, width_w=0.05))''')

rep('''TUCKS = [
    ("R2", (648, 238), "after", "@all:U0,U1,U2,U3,U4,U5,B,X,W,A"),
    ("R3", (640, 192), "before", "@all:U0,U1,U2,U3,U4,U5,B,X,W,A"),
    ("Rin", (598, 302), "before", "@all:U0,U1,U2,U3,U4,U5,B,X,W,A"),
    ("Rin", (262, 706), "after", "C"),
]''', '''TUCKS = [
    # the pinwheel: the R family dives under the U fan at the whorl apex
    ("R2", (672, 256), "after", "@all:U1,U2,U3,U4,U5"),
    ("R3", (668, 244), "after", "@all:U1,U2,U3,U4,U5"),
    ("Rin", (686, 256), "after", "@all:U1,U2,U3,U4,U5"),
    # the woven cycle: R_in's lower end (L5) threaded under C
    ("Rin", (262, 706), "before", "C"),
]''')

# bottom: D_a keeps out of the rim region harder, rimL probes further right
rep('''        EdgeTerm(rimL_region, +1, 1.0, "keepout", "rim (L3) region"),''', '''        EdgeTerm(rimL_region, +1, 3.0, "keepout", "rim (L3) region"),''')
rep('''    rimL_region = probes_between(E("D19", xr=(548, 700)), to_limb_px(E("D19", xr=(548, 700)), 0.99), fr=(0.2, 0.5, 0.8))''',
    '''    rimL_region = probes_between(E("D19", xr=(545, 700)), to_limb_px(E("D19", xr=(545, 700)), 0.99), fr=(0.1, 0.3, 0.5, 0.7, 0.9))''')
rep('''    P["rimL"] = probes_between(E("D19", xr=(548, 700)), to_limb_px(E("D19", xr=(548, 700)), 0.99), fr=(0.5,))''',
    '''    P["rimL"] = probes_between(E("D19", xr=(560, 700)), to_limb_px(E("D19", xr=(560, 700)), 0.99), fr=(0.5,))''')
# pins: the R family on top of what it covers at the upper left; U0 first among the U's
rep('''    ("W", "Rin"), ("A", "Rin"), ("U0", "Rin"),
]''', '''    ("W", "Rin"), ("A", "Rin"), ("U0", "Rin"),
    ("U0", "U1"), ("U0", "U2"), ("U0", "U3"), ("U0", "U4"), ("U0", "U5"),
    ("W", "R3"), ("A", "R3"),
]''')
open(p, "w", encoding="utf-8").write(s)
print("ok")
