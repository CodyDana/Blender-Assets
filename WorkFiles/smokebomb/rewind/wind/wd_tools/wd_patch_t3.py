"""table v3: 3-D targets past the limb (the R family leaves over the top-right), coverage
probes for D_c and E up to A's edge, U0 above W's cord."""
import re

p = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/rewind/wind/wd_tools/wd_fitlib.py"
s = open(p, encoding="utf-8").read()


def rep(old, new):
    global s
    if old not in s:
        raise SystemExit("anchor: " + old[:100])
    s = s.replace(old, new)


# EdgeTerm: optional camera-frame points (for targets behind the limb)
rep('''    pts: np.ndarray
    side: int
    weight: float = 1.0
    kind: str = "own"
    label: str = ""
''', '''    pts: np.ndarray
    side: int
    weight: float = 1.0
    kind: str = "own"
    label: str = ""
    cam: Optional[np.ndarray] = None       # camera-frame unit points (overrides pts; may lie behind a limb)

    def P(self) -> np.ndarray:
        return np.asarray(self.cam, float) if self.cam is not None else px2cam(self.pts)
''')
s = s.replace("px2cam(t.pts) for t in pf.terms if len(t.pts) and t.kind not in", "t.P() for t in pf.terms if len(t.pts) and t.kind not in")
rep('''        if not len(t.pts) or t.kind in ("keepout", "inside"):
            continue
        P = px2cam(t.pts)''', '''        if not len(t.pts) or t.kind in ("keepout", "inside"):
            continue
        P = t.P()''')
rep('''    Ps = [px2cam(t.pts) for t in terms]''', '''    Ps = [t.P() for t in terms]''')
rep('''    for t in terms:
        if t.kind != "own":
            continue
        P = px2cam(t.pts)
        f = np.degrees(np.arctan2(P @ e2_, P @ e1_))''', '''    for t in terms:
        if t.kind != "own" or t.cam is not None:
            continue
        P = t.P()
        f = np.degrees(np.arctan2(P @ e2_, P @ e1_))''')
open(p, "w", encoding="utf-8").write(s)

p = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/rewind/wind/wd_tools/wd_passes.py"
s = open(p, encoding="utf-8").read()
rep('''def pass_table():
    E = edge_px''', '''def past_limb(route_px, degs=(4.0, 9.0, 14.0, 19.0)):
    """camera-frame points continuing a route straight on (a geodesic) past its last point,
    over the limb and onto the far side."""
    from wd_fitlib import px2cam
    import props_lib.smokebomb_wind as W
    P = px2cam(np.asarray(route_px, float)[-2:])
    p1 = W.normalize(P[1])
    t = P[1] - P[0]
    t = W.normalize(t - np.dot(t, p1) * p1)
    return np.array([np.cos(np.radians(d)) * p1 + np.sin(np.radians(d)) * t for d in degs])


def pass_table():
    E = edge_px''')
# the R family: add the past-limb targets
rep('''        EdgeTerm(FL_resample(rin_route, 6.0), 0, 0.5, "own", "on under R2, into the apex and under the fan"),''',
    '''        EdgeTerm(FL_resample(rin_route, 6.0), 0, 0.5, "own", "on under R2, into the apex and under the fan"),
        EdgeTerm(np.zeros((4, 2)), 0, 1.0, "own", "over the top-right limb", cam=past_limb(rin_route)),''')
rep('''        EdgeTerm(FL_resample(r3_route, 6.0), 0, 0.4, "own", "into the apex and under the fan"),''',
    '''        EdgeTerm(FL_resample(r3_route, 6.0), 0, 0.4, "own", "into the apex and under the fan"),
        EdgeTerm(np.zeros((4, 2)), 0, 1.0, "own", "over the top-right limb", cam=past_limb(r3_route)),''')
rep('''        EdgeTerm(FL_resample(r2_route, 6.0), 0, 0.4, "own", "into the apex and under the fan"),''',
    '''        EdgeTerm(FL_resample(r2_route, 6.0), 0, 0.4, "own", "into the apex and under the fan"),
        EdgeTerm(np.zeros((4, 2)), 0, 1.0, "own", "over the top-right limb", cam=past_limb(r2_route)),''')
# D_c and E reach up to A's lower edge; U0 covers just above W's cord
rep('''        EdgeTerm(e_region, +1, 1.0, "keepout", "E's region"),
    ], width=0.13, width_w=0.2))''', '''        EdgeTerm(e_region, +1, 1.0, "keepout", "E's region"),
        EdgeTerm(shift_toward(E("ALO", xr=(560, 690)), (600, 950), 7), 0, 1.0, "inside", "up to A's lower edge"),
    ], width=0.13, width_w=0.2))''')
rep('''        EdgeTerm(dc_region, +1, 1.0, "keepout", "D_c's region"),
    ], width=0.16, width_w=0.3))''', '''        EdgeTerm(dc_region, +1, 1.0, "keepout", "D_c's region"),
        EdgeTerm(shift_toward(E("ALO", xr=(700, 1020)), (850, 1000), 7), 0, 1.0, "inside", "up to A's lower edge"),
    ], width=0.16, width_w=0.3))''')
rep('''        EdgeTerm(shift_toward(E("WTW", xr=(390, 540)), (480, 400), 3), +1, 1.0, "hide", "its foot under W's cord"),''',
    '''        EdgeTerm(shift_toward(E("WTW", xr=(390, 540)), (480, 400), 3), +1, 1.0, "hide", "its foot under W's cord"),
        EdgeTerm(shift_toward(E("WTW", xr=(440, 495)), (480, 400), 9), 0, 2.0, "inside", "just above W's cord"),''')
open(p, "w", encoding="utf-8").write(s)
print("ok")
