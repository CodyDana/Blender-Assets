"""W1b: SM_Att_Scope_LongRange form (SR01_BUILD_PLAN 5; CRAFT_STUDY RP15): a 34 mm long-range scope with its two
rings, built in the gun's frame M (mm) at its mounted pose so the A-gates run against the gun; the attachment's own
frame is M - Mount (Mount = the rear ring's recoil lug on the rail-top plane, Rail_Top + 2 slots).

Profile stations from the traced GR scope ring (scratch/w1 prof.py, about the scope axis Z 57.6): eyecup, eyepiece,
power ring + throw lever, 34 mm tube, turret saddle with elevation (top), windage (right), side focus (left), the
objective bell to 62 mm. Knurl / scallops are geometry. Lenses are their own slot (opaque glossy, Q6), recessed
6 mm (objective) / 4 mm (ocular).
"""
from __future__ import annotations

import math

import numpy as np

from gunlib import geo2d as G
from gunlib import mesh as MS
from gunlib.parts import hardware as HW
from gunlib.parts.sights_flip import revolve_loop
from sr_common import D
from sniper_parts import Part, xcyl, ycyl, joint

SA = D["scope_attachment"]
AXZ = 57.6                                   # scope axis Z (A4)
MOUNT = np.array(SA["mount_M"], float)       # (416.15, 0, 30.0)
RINGS_X = [float(x) for x in SA["ring_X"]]   # slots 2 and 12
SLOT_B, SLOT_L = "M_Att_Scope_Body", "M_Att_Scope_Lens"
R_TUBE = 17.0
X0, X1 = 271.1, 690.5


def body():
    # (x, r) outer stations; the ocular / objective faces recessed for the lenses
    prof = [(X0 + 4.0, 19.0), (X0 + 0.6, 21.0), (X0, 22.0), (X0 + 0.4, 23.0), (X0 + 2.0, 23.6), (X0 + 9.5, 23.6),
            (X0 + 11.0, 22.6),                                                     # rubber eyecup ring (part of body)
            (284.0, 21.6), (350.0, 21.6), (351.0, 22.3), (374.0, 22.3), (375.0, 21.6),   # eyepiece + power ring
            (378.0, 20.8), (386.0, R_TUBE), (553.0, R_TUBE), (560.0, 17.6), (632.0, 30.4), (636.0, 31.05),
            (689.3, 31.05), (X1, 30.0), (X1, 27.4), (X1 - 6.0, 27.4), (X1 - 6.0, 0.0)]
    xs = X0 + 4.0
    loop = [(x - X0, r) for x, r in prof[:-1]] + [(X1 - 6.0 - X0, 15.5), (4.0, 15.5)]
    # (W4 review C13) 64 sides (5.6 deg; G3 <= 7.5): at 36 the eyepiece and bell rims read polygonal in the FP / ADS views
    m = revolve_loop(loop, (X0, 0, AXZ), (1, 0, 0), 64)
    # power-ring scallops (8) and the throw lever on the right
    cut = []
    for i in range(8):
        a = 2 * math.pi * i / 8
        c = np.array([0.0, 22.3 * math.cos(a), AXZ + 22.3 * math.sin(a)])
        cut.append(MS.cylinder(c + [355.0, 0, 0], c + [371.0, 0, 0], 1.6, 6))
    lever = MS.box(358.0, 368.0, -27.5, -21.6, AXZ - 2.0, AXZ + 2.0)
    # saddle: a turret housing around the tube between X 443.2 and 482.7 (Z 34.5..75.5 drawn)
    saddle = MS.prism(G.rounded_rect(443.2, 482.7, -20.0, 20.0, 4.0, 4), AXZ - 19.0, AXZ + 18.0, "XY")
    sad_r = MS.revolve([(0.0, 0.0), (0.0, 20.5), (39.5, 20.5), (39.5, 0.0)], (443.2, 0, AXZ), (1, 0, 0), 32)
    return Part("scope_body", m, [("U", [lever, saddle, sad_r]), ("D", cut)], bone="-", cls="M-round", slot=SLOT_B,
                recipe=[(0.5, 1, 30.0)], spec_id="scope_body")


def turret(axis, centre, base_r, cap_r, h_base, h_cap, n_knurl=32, name="turret", dot=True):
    """A drum turret on the saddle (local +Z = the axis): base collar, a knurled skirt as a toothed prism (real
    straight knurl as geometry, n_knurl teeth 0.6 deep), a top cap with a raised zero dot."""
    th = np.linspace(0, 2 * math.pi, 2 * n_knurl, endpoint=False)
    rr = np.where(np.arange(2 * n_knurl) % 2 == 0, cap_r, cap_r - 0.6)
    star = np.c_[rr * np.cos(th), rr * np.sin(th)]
    m = MS.revolve([(0.0, 0.0), (0.0, base_r), (h_base + 0.3, base_r), (h_base + 0.3, 0.0)], (0, 0, 0), (0, 0, 1), 24)
    skirt = MS.prism(star, h_base, h_base + h_cap - 2.0, "XY")
    cap = MS.revolve([(0.0, 0.0), (0.0, cap_r + 0.02), (1.2, cap_r + 0.02), (2.2, cap_r - 1.2), (2.2, 0.0)],
                     (0, 0, h_base + h_cap - 2.2), (0, 0, 1), 24)
    dot = MS.cylinder((cap_r * 0.55, 0, h_base + h_cap - 0.2), (cap_r * 0.55, 0, h_base + h_cap + 0.4), 0.8, 8)
    place = lambda q: HW.place(q, centre, axis)
    return Part(name, place(m), [("U", [place(skirt), place(cap)] + ([place(dot)] if dot else []))], bone="-", slot=SLOT_B,
                recipe=[(0.25, 1, 50.0)], spec_id="scope_body")


def turrets():
    return [turret((0, 0, 1), (462.0, 0, AXZ + 18.02), 13.0, 16.0, 6.0, 18.0, 24, "scope_turret_elev", dot=False),
            turret((0, -1, 0), (462.0, -20.52, AXZ), 11.0, 13.5, 4.0, 10.0, 20, "scope_turret_wind"),
            turret((0, 1, 0), (466.0, 20.52, AXZ), 12.0, 13.0, 3.0, 9.0, 20, "scope_focus")]


def ring(x, width, k):
    """34 mm two-piece ring: clamp base on the rail with the recoil lug in slot k, the cap with 2 screws per side,
    the cross-bolt nut on the left."""
    hw = width / 2.0
    ro = R_TUBE + 3.7
    ring_m = MS.revolve([(0.0, 0.0), (0.0, ro), (width, ro), (width, 0.0)], (x - hw, 0, AXZ), (1, 0, 0), 32)
    base = MS.prism(np.array([(-15.0, 30.02), (15.0, 30.02), (12.5, AXZ - 6.0), (-12.5, AXZ - 6.0)]), x - hw, x + hw, "YZ")
    # rail clamp jaws hugging the 1913 dovetail sides down to Z 24.0 (outside the rail's V at +-10.6 + 0.3)
    jaws = [MS.box(x - hw, x + hw, 10.9, 15.0, 24.0, 30.5), MS.box(x - hw, x + hw, -15.0, -10.9, 24.0, 30.5)]
    lug = MS.box(x - 2.5, x + 2.5, -7.0, 7.0, 27.15, 30.5)                # recoil lug into the slot (5.24 wide)
    nut = HW.place(MS.revolve([(0.0, 0.0), (0.0, 4.2), (3.0, 4.2), (3.0, 0.0)], (0, 0, 0), (0, 0, 1), 6),
                   (x, 15.02, 27.2), (0, 1, 0))
    bolt_head = HW.place(HW.socket_cap(4.0, 0.01, 16), (x, -15.02, 27.2), (0, -1, 0))
    ears = [MS.box(x - hw, x + hw, 19.0, 25.0, AXZ - 3.0, AXZ + 3.0), MS.box(x - hw, x + hw, -25.0, -19.0, AXZ - 3.0, AXZ + 3.0)]
    # the cap / base split line is a W2 normal-map detail (a 0.8 slot grazing the tube bore made UD1 slivers)
    cut = [xcyl(x - hw - 1, x + hw + 1, R_TUBE + 0.15, z=AXZ, nseg=36)]
    pr = Part(f"scope_ring_{k}", ring_m, [("U", [base] + jaws + ears + [lug, nut, bolt_head]), ("D", cut)], bone="-",
              slot=SLOT_B, recipe=[(0.4, 1, 30.0)], jnt=joint("butt", note="recoil lug in rail slot %d" % k),
              spec_id="scope_rings")
    heads = MS.Mesh()
    for sg in (1, -1):
        for dx in (-hw * 0.5, hw * 0.5):
            heads.extend(MS.cylinder((x + dx, sg * 22.0, AXZ + 3.02), (x + dx, sg * 22.0, AXZ + 4.8), 1.9, 10))
    return [pr, Part(f"scope_ring_{k}_screws", heads, bone="-", slot=SLOT_B, recipe=[], spec_id="scope_rings")]


def lenses():
    m = MS.revolve([(0.0, 0.0), (0.0, 27.3), (1.2, 27.3), (1.6, 0.0)], (X1 - 6.0 + 0.02, 0, AXZ), (1, 0, 0), 48)
    m2 = MS.revolve([(0.0, 0.0), (0.4, 18.4), (1.4, 18.4), (1.4, 0.0)], (X0 + 4.0 - 0.02, 0, AXZ), (-1, 0, 0), 40)
    return [Part("scope_lens_objective", m, bone="-", cls="none", slot=SLOT_L, recipe=[], spec_id="scope_lens"),
            Part("scope_lens_ocular", m2, bone="-", cls="none", slot=SLOT_L, recipe=[], spec_id="scope_lens")]


def all_parts():
    out = [body()] + turrets()
    out += ring(RINGS_X[0], 23.5, 2) + ring(RINGS_X[1], 21.6, 12)
    out += lenses()
    return out
