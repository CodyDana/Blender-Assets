"""Round 2: patch props_lib/flashbang_spec.py (one-shot, asserts every anchor)."""
p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/flashbang_spec.py"
s = open(p, encoding="utf-8").read()


def rep(a, b, n=1):
    global s
    assert s.count(a) == n, (a[:80], s.count(a))
    s = s.replace(a, b)


rep('''    inner_shell: bool = True  # the tube's hole walls and inner surface (LOD2 drops them; the holes stay open)
''', '''    inner_shell: bool = True  # the tube's hole walls and inner surface (LOD2 drops them; the holes stay open)
    grooves: bool = False     # ROUND 2: the ring lines as real V-grooves (else normal / colour only)
    can_shoulder: bool = False  # ROUND 2: each brass can's seam step + rounded shoulder as geometry
    head_detail: int = 2      # ROUND 2: 2 every fuze part, 1 no coil / pads, 0 the silhouette parts only
''')
rep('''    wall_mm: float = dmm(0.04)                              # 1.76 outer tube wall (spec 3: 0.03-0.05 D)''',
    '''    wall_mm: float = dmm(0.05)                              # ROUND 2: 2.2 (was 1.76) - the reference's thick cut
                                                            # wall (spec 3: 0.03-0.05 D, the top of the range)''')
rep('''    ring_line_w: float = dmm(0.015)
''', '''    ring_line_w: float = dmm(0.015)
    groove_w: float = 0.35                                  # ROUND 2: V-groove half width (0.7 mm wide) ...
    groove_d: float = 0.40                                  # ... and depth (craft: 0.6-0.8 wide, 0.4 deep)
''')
rep('''    can_r: float = 5.7
    can_c: float = 11.3
    can_arc_deg: float = 220.0
''', '''    can_r: float = 6.0                                      # ROUND 2: 12 mm wide = 78 % of the hole (ref ~70-80 %)
    can_c: float = 11.0                                     # front of the can at r 17.0
    can_arc_deg: float = 200.0
    can_step: float = 0.45                                  # ROUND 2: the seam step (the lower tube's top edge) ...
    can_flare: float = 1.2                                  # ... and the upper part's rounded shoulder above it
''')
rep('''    plate_z1: float = dmm(3.732)                            # 164.21 top cover plate top
    plate_x: Tuple[float, float] = (-14.6, 12.8)            # FINALISE: overhang 4.0 mm = 0.09 D (craft: <= 0.07-0.1 D)
    plate_y: float = dmm(0.48) / 2.0 + 0.25                 # FINALISE: covers the housing top (no hidden +Z face)
    panel_proud: float = 1.0                                # FINALISE: the raised front panel on the -X face (v2)
    panel_y: float = 6.2                                    # its half width
    panel_slot: float = 0.7                                 # half width of its vertical slot
    panel_z: Tuple[float, float] = (141.5, 161.53)
    arm_curl_r: float = 2.1
    arm_curl_len: float = 11.0
    arm_pin_r: float = 0.85
    arm_pin_len: float = 13.6
    knuckle_r: float = dmm(0.137) / 2.0                     # 3.01
    knuckle_len: float = 15.2                               # FINALISE: fills the lever curl between its flanges (cheeks)
    knuckle_c: Tuple[float, float, float] = (18.0, -2.62, 160.64)  # top of the lever curl = overall top 165.9
    block_x: Tuple[float, float] = (10.2, 17.6)             # CHOICE: the hinge bracket carrying knuckle and pin
    block_y: Tuple[float, float] = (-8.3, 6.3)
    block_z: Tuple[float, float] = (151.3, 160.0)
    pin_boss_r: float = dmm(0.095) / 2.0                    # 2.09
    pin_boss_len: float = dmm(0.17)                         # 7.48
    pin_c: Tuple[float, float] = (15.4, dmm(3.514))         # (x, z) of the pin axis; z 154.6 (spec 2)
    pin_r: float = 1.0
    pin_head_r: float = 2.3                                 # FINALISE: the ring passes through the pin's head
    pin_head_len: float = 4.2                               # (the separate split-ring eyelet is gone)
    small_boss_r: float = dmm(0.057) / 2.0                  # 1.25 (v1 x185 y63 -> X +6.9, Z ~158.4)
    small_boss_c: Tuple[float, float] = (6.9, 158.4)
''', '''    plate_z1: float = 164.1                                 # top cover plate top (2.57 mm plate)
    #: ROUND 2 fuze head (the blind tells: "a plain box with a flat cap").  Every part below is real geometry,
    #: placed by projecting it through the reference row camera (WorkFiles/flashbang/r2/tools/r2proj.py) so each view's
    #: head silhouette extents land near the reference's (r2_extents.py), and by eye against the close-ups.
    plate_x: Tuple[float, float] = (-11.3, 12.9)            # small overhang on every side (0.7 / 1.0 mm)
    plate_y: float = 11.6
    housing_corner_c: Tuple[float, float, float, float] = (0.6, 0.6, 0.6, 2.6)   # vertical edges (-X-Y, +X-Y,
                                                            # +X+Y, -X+Y): the -X+Y corner cut back (v1's narrow left)
    # the striker on the -X face (v2: a raised plate topped by a hinge knuckle across the face)
    striker_proud: float = 1.6
    striker_y: float = 6.8                                  # half width
    striker_z: Tuple[float, float] = (142.0, 160.6)
    striker_knuckle_r: float = 2.9
    striker_knuckle_c: Tuple[float, float] = (-11.86, 163.0)   # (x, z): its top = 165.9 = 3.77 D (the overall height)
    # the side lug on the +Y face (v2's left flank with two pin ends; v1 / v3's top-left lug and roll): a flag-shaped
    # plate standing off the housing on a spacer, its top edge rolled, two cross pins with square washers
    lug_y: Tuple[float, float] = (12.8, 16.3)
    lug_standoff: Tuple[float, float, float, float] = (0.5, 6.0, 143.0, 161.0)   # x0, x1, z0, z1 (y 10.3 .. lug)
    lug_poly_xz: Tuple[Tuple[float, float], ...] = ((-1.0, 141.5), (7.0, 141.5), (7.0, 162.4), (-10.0, 162.4),
                                                    (-10.8, 161.6), (-10.8, 156.3), (-10.0, 155.5), (-1.0, 155.5))
    lug_roll_r: float = 1.6                                 # the rolled top edge (a tube along X)
    lug_pins: Tuple[Tuple[float, float], ...] = ((-10.8, 159.0), (-1.0, 149.0))   # (x of the face, z)
    knuckle_r: float = dmm(0.137) / 2.0                     # 3.01
    knuckle_len: float = 15.2                               # FINALISE: fills the lever curl between its flanges (cheeks)
    knuckle_c: Tuple[float, float, float] = (18.0, -2.62, 161.5)   # ROUND 2: +0.86 so the curl top = 165.9 = 3.77 D
    block_x: Tuple[float, float] = (10.2, 17.6)             # CHOICE: the hinge bracket carrying knuckle and pin
    block_y: Tuple[float, float] = (-8.3, 6.3)
    block_z: Tuple[float, float] = (151.3, 160.0)
    pin_boss_r: float = 2.2
    pin_boss_y1: float = -14.5                              # ROUND 2: the boss's outer end (the pin shaft shows beyond)
    #: ROUND 2: the pin eye and the ring's top point, fitted with the ring's pose to the four views' ring extents
    #: (r2_ring_search.py: mean |ours - ref| of the ring-side extents 16.5 -> 7.4 mm over H 2.70-3.75 D)
    pin_c: Tuple[float, float] = (15.4, 156.5)              # (x, z) of the pin axis
    pin_eye_c_y: float = -21.5
    pin_r: float = 1.0
    pin_head_r: float = 2.4                                 # the ring passes through the pin's head
    pin_head_len: float = 2.6
    small_boss_r: float = 1.35                              # the screw head on the -Y face (v1 / v3 / p1)
    small_boss_c: Tuple[float, float] = (5.2, 158.2)
    coil_c: Tuple[float, float] = (-5.6, 158.0)             # ROUND 2: the small coil end on the -Y face (v3)
    post_c: Tuple[float, float] = (12.2, -9.0)              # ROUND 2: the spring post and its ball (v1 / v4)
    post_z: Tuple[float, float] = (152.0, 159.3)
    post_r: float = 0.9
    ball_r: float = 1.3
    ball_z: float = 160.0
''')
rep('''    ring_tilt_deg: float = 30.0                             # FINALISE: hangs 30 deg off the sleeve (v2 / v4 overhang)
    ring_yaw_deg: float = -10.0                             # CHOICE: v4 sees the ring ~72 deg from face-on''',
    '''    ring_tilt_deg: float = 10.0                             # ROUND 2: fitted (r2_ring_search.py), was 30
    ring_yaw_deg: float = 10.0                              # ROUND 2: the wire through the eye runs 10 deg off +X''')
rep('''        #  FINALISE: cell_v 2 (the cylinder needs no vertical splits), hole 24/16/12, inner 1x1, cap 3/2/1 per flat,
        #  tube = segments per brass can, ring 32x8 / 20x6 / 12x4 on one centreline, lever curl 10/5/3
        #          cell_u web_u cell_v hole  in_u in_v rev coll pl  cap/flat notch tube ring  sm eye  curl chamf band
        LodQuality(12, 6, 2, 24, 1, 1, 72, 32, 28, 3, True, 8, 32, 8, 12, 8, 4, 10, True, (5200, 6000), 2, True),
        LodQuality(8, 4, 1, 18, 1, 1, 48, 20, 16, 2, True, 8, 24, 8, 8, 6, 3, 5, True, (2500, 4000), 1, True),
        LodQuality(4, 2, 1, 16, 1, 1, 24, 16, 10, 1, False, 6, 24, 8, 6, 4, 3, 3, False, (800, 1700), 0, False),''',
    '''        #  ROUND 2: the revolve 72 -> 48 at LOD0 (7.5 deg: a 0.05 mm sagitta) and cap 3 -> 2 per flat pay for the
        #  V-grooves, the can shoulders and the fuze mechanism; LOD1 back near the plan's ~2,600-3,000
        #          cell_u web_u cell_v hole  in_u in_v rev coll pl  cap/flat notch tube ring  sm eye  curl chamf band
        LodQuality(8, 4, 2, 24, 1, 1, 48, 28, 24, 2, True, 6, 32, 8, 12, 8, 4, 10, True, (5200, 6000), 2, True,
                   True, True, 2),
        LodQuality(4, 2, 1, 16, 1, 1, 24, 20, 16, 1, True, 6, 24, 6, 8, 6, 3, 5, True, (2400, 3300), 1, True,
                   False, False, 1),
        LodQuality(2, 1, 1, 12, 1, 1, 12, 12, 8, 1, False, 4, 16, 4, 6, 4, 3, 3, False, (800, 1700), 0, False,
                   False, False, 0),''')
rep('''    def pin_eye_y(self) -> float:
        """The pin head's centre (the ring passes through it) = the Pin socket."""
        return round(self.block_y[0] - self.pin_boss_len - self.pin_head_len / 2.0, 3)''',
    '''    def pin_eye_y(self) -> float:
        """The pin head's centre (the ring passes through it) = the Pin socket."""
        return round(self.pin_eye_c_y, 3)''')
open(p, "w", encoding="utf-8").write(s)
print("spec patched")
