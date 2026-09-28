"""Finalise patch 1: flashbang_spec.py numbers (applied once)."""
from pathlib import Path

p = Path(r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/flashbang_spec.py")
s = p.read_text(encoding="utf-8")
rep = [
    ('"""props_lib.flashbang_spec - SM_Flashbang\'s build-to numbers, in one place (round 1).',
     '"""props_lib.flashbang_spec - SM_Flashbang\'s build-to numbers, in one place (round 1 + finalise 2026-09-27).'),
    ('''    end_annulus_r: Tuple[float, float] = (19.30, dmm(0.94) / 2.0)
    end_lip_r: Tuple[float, float] = (17.30, 19.30)         # 0.045 D radial
    end_groove_r: Tuple[float, float] = (16.00, 17.30)      # 0.03 D
    end_disc_r: float = 16.00
    end_z_lip: float = 0.0
    end_z_annulus: float = 0.5
    end_z_groove: float = 1.2
    end_z_disc: float = 0.35
    notch_deg: Tuple[float, ...] = (-10.0, 62.0, 134.0, 206.0, 278.0)   # 5 notches, 72 deg pitch (p3: -10 ... )
    notch_w_mm: float = dmm(0.05)                           # 2.2
    disc_step_depth: float = 1.0                            # the matching step on the disc edge (p3)''',
     '''    #: FINALISE (craft review): p3 reads as a WIDE flat contact rim (r 15.2 .. foot) around a recessed central disc,
    #: a narrow groove between them, and 5 blocky notches where the rim juts IN toward the centre (the disc outline
    #: steps in); the side views' foot cut-outs are the same 5 notches cut out through the outer bottom edge.
    #: Radial bands (r0, r1, z normal, z in a notch) from the centre out; z = height ABOVE the contact plane.
    end_bands: Tuple[Tuple[float, float, float, float], ...] = (
        (0.0, 12.6, 1.1, 1.1),        # central disc, 1.1 mm recessed
        (12.6, 13.8, 1.1, 1.9),       # notch: the groove steps in
        (13.8, 15.2, 1.1, 0.0),       # notch: the rim tab (the disc outline steps in at each notch)
        (15.2, 16.4, 1.9, 0.0),       # the groove (normal) / rim tab (notch)
        (16.4, 18.4, 0.0, 0.0),       # the flat contact rim
        (18.4, dmm(0.94) / 2.0, 0.0, 2.0),   # outer rim; in a notch cut out 2.0 mm up through the foot edge
    )
    notch_foot_z: float = 2.0                               # the foot cut-out height (side views v1 / v3)
    notch_deg: Tuple[float, ...] = (-10.0, 62.0, 134.0, 206.0, 278.0)   # 5 notches, 72 deg pitch (p3: -10 ... )
    notch_w_mm: float = 5.0                                 # FINALISE: 4-5 mm blocky notches (was 2.2)'''),
    ('''    plate_x: Tuple[float, float] = (-19.0, 12.8)            # CHOICE: the arm overhang 0.07-0.25 D (8.4 mm here)
    plate_y: float = 9.4''',
     '''    plate_x: Tuple[float, float] = (-14.6, 12.8)            # FINALISE: overhang 4.0 mm = 0.09 D (craft: <= 0.07-0.1 D)
    plate_y: float = dmm(0.48) / 2.0 + 0.25                 # FINALISE: covers the housing top (no hidden +Z face)
    panel_proud: float = 1.0                                # FINALISE: the raised front panel on the -X face (v2)
    panel_y: float = 6.2                                    # its half width
    panel_slot: float = 0.7                                 # half width of its vertical slot
    panel_z: Tuple[float, float] = (141.5, 161.53)'''),
    ('''    knuckle_len: float = dmm(0.331)                         # 14.56''',
     '''    knuckle_len: float = 17.6                               # FINALISE: spans the lever's top width (no open curl end)'''),
    ('''    knuckle_c: Tuple[float, float, float] = (18.0, -1.0, 160.64)  # top of the lever curl = overall top 165.9''',
     '''    knuckle_c: Tuple[float, float, float] = (18.0, -2.62, 160.64)  # top of the lever curl = overall top 165.9'''),
    ('''    eye_major: float = 1.75
    eye_minor: float = 0.55''',
     '''    pin_head_r: float = 2.3                                 # FINALISE: the ring passes through the pin's head
    pin_head_len: float = 4.2                               # (the separate split-ring eyelet is gone)'''),
    ('''    lever_t: float = 2.2                                    # 0.05 D plate (spec 6: plate or flange, not resolvable)''',
     '''    lever_t: float = 1.3                                    # FINALISE: sheet thickness of a CHANNEL section
    lever_flange: float = 3.3                               # flange depth (edge-on the lever reads ~0.08 D deep, v1)'''),
    ('''    lever_joggle_z: Tuple[float, float] = (141.2, 137.6)    # the short outward step (v4 y 138-143)''',
     '''    lever_joggle_z: Tuple[float, float] = (146.0, 137.0)    # FINALISE: one smooth diagonal step (was an S-crank)'''),
    ('''    ring_wire_d: float = dmm(0.04)                          # 1.76 (p1 close-up: one round wire)
    ring_tilt_deg: float = 15.0                             # CHOICE: hangs outward so it clears the sleeve (v2 edge-on)''',
     '''    ring_wire_d: float = 2.4                                # FINALISE: thicker dark wire (craft 2.2-2.5 mm)
    ring_tilt_deg: float = 30.0                             # FINALISE: hangs 30 deg off the sleeve (v2 / v4 overhang)'''),
    ('''    tube_seam_z: Tuple[float, ...] = (dmm(0.859) + 0.3, dmm(1.521) + 0.3, dmm(2.158) + 0.3)  # 0-3 px above centre''',
     '''    tube_seam_z: Tuple[float, ...] = (dmm(0.859) + 0.3, dmm(1.521) + 0.3, dmm(2.158) + 0.3)  # 0-3 px above centre
    #: FINALISE (craft + blind review: "a smooth brass egg"): through each hole the reference shows a vertical brass
    #: CYLINDER narrower than the hole with dark gaps both sides.  One brass can per hole column (radius can_r, axis
    #: at radius can_c), dark radial dividers between the columns (they also close the see-through at the limbs).
    can_r: float = 5.7
    can_c: float = 11.3
    can_arc_deg: float = 220.0'''),
    ("    tube_segs: int            # inner brass tube",
     "    tube_segs: int            # FINALISE: segments of each brass can's visible arc"),
    ('''    def pin_eye_y(self) -> float:
        return round(self.block_y[0] - self.pin_boss_len - 1.17, 3)''',
     '''    def pin_eye_y(self) -> float:
        """The pin head's centre (the ring passes through it) = the Pin socket."""
        return round(self.block_y[0] - self.pin_boss_len - self.pin_head_len / 2.0, 3)'''),
]
for a, b in rep:
    assert a in s, a[:70]
    s = s.replace(a, b)
i0 = s.index("    lods: Tuple[LodQuality, ...] = (")
i1 = s.index("    sockets: Tuple[SocketDef")
s = s[:i0] + '''    lods: Tuple[LodQuality, ...] = (
        #  FINALISE: cell_v 2 (the cylinder needs no vertical splits), hole 24/16/12, inner 1x1, cap 3/2/1 per flat,
        #  tube = segments per brass can, ring 32x8 / 20x6 / 12x4 on one centreline, lever curl 10/5/3
        #          cell_u web_u cell_v hole  in_u in_v rev coll pl  cap/flat notch tube ring  sm eye  curl chamf band
        LodQuality(12, 6, 2, 24, 1, 1, 72, 32, 28, 3, True, 8, 32, 8, 12, 8, 4, 10, True, (5200, 6000), 2, True),
        LodQuality(8, 4, 1, 16, 1, 1, 48, 24, 16, 2, True, 6, 20, 6, 8, 6, 3, 5, True, (2500, 3500), 2, True),
        LodQuality(4, 2, 1, 12, 1, 1, 24, 16, 10, 1, False, 4, 12, 4, 6, 4, 3, 3, False, (800, 1400), 0, False),
    )
''' + s[i1:]
p.write_text(s, encoding="utf-8")
print("spec patched")
