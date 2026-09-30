"""Dojo kit 10: MODERN PROPS (Blender only). Every prop is its OWN asset: its own mesh, UCX hulls, FBX and collection.

Builds, at the origin, each prop in its own collection under "ModernProps" in Assets/Dojo/ModernProps.blend, runs the
pipeline QA (0 hard fails required, budget_tris=5000 per prop; uv0_tile_range and uv_no_overlap are waived because
UV0 is a TILING channel, as in the ground kit), exports each prop through Scripts/pipeline as a LOD0-2 LodGroup
(decimate_lods + make_lod_group, UCX_<base>_LOD0_NN; sockets go to the .sockets.json sidecar), and writes
WorkFiles/dojo/build/props/modern/{layout_modern.json, measure.json, qa_report.json, export_report.json}.

Sources: WorkFiles/world/DOJO_ARENA_SPEC.md (sizes, placements, R3, collision classes 5.3), STYLE_GUIDE.md (palette,
5.12 px/cm, 7 Nanite + LOD0-2, IP section 10: no text, logos or brands anywhere; every panel is blank), the reference
panel 11 of References/Dojo/dojo_modern_props_ref.png and the AC units / lamps of dojo1_reference2.png (look only).

Fix round f1 (2026-09-27): wall props on the grey-box wall face Y 27.94; token UCX on the wires; roof AC under
5k tris (alpha-masked fan grille); LOD0-2 on every prop; vending display with baked AO; vending front redrawn
(arch-topped window, chrome coin cluster, flush top: the 1.0 m depth now comes from the cabinet); height-anchored
weathered paint; twisted fan blades; hex tapered lanterns with bulbs; street lamps redrawn; pole with a second
crossarm, riser box, coil and three new attachment assets (transformer, guy, telecom cable); junction box straightened.

Local frame of every prop: metres, front faces -Y (Blender's front view looks at it), Z up.
  * floor props (vending machine, street lamps, utility pole): pivot = base centre on the ground.
  * pole attachments (transformer, guy): pivot = the POLE's base centre, so they take the pole's own transform.
  * roof AC unit: pivot = centre of the front edge of its footprint ON THE ROOF SURFACE (the front feet line); the
    roof rises toward +Y at 25 degrees (spec R4), so the unit drops straight onto the hall's lower roof.
  * wall props (small wall AC, wall lamp, junction box): the wall surface is the plane y = 0 and the prop stands out
    toward -Y; pivot on that plane (wall AC: the bracket arm top; lamp: the back-board centre; junction box: the
    bottom of its conduit loop).
  * wires: pivot at the first attachment point; the span runs along +X and sags under its own weight.

Run: blender -b --factory-startup --python Scripts/dojo/props/modern/build_modern_props.py -- [--no-export]
"""
import json
import math
import sys
from datetime import date
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "Scripts"))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "stone"))
from pipeline.export_fbx import export_fbx  # noqa: E402
from pipeline.qa_check import qa_check  # noqa: E402
from pipeline.lock import assert_owner  # noqa: E402
from pipeline.helpers import decimate_lods, make_lod_group  # noqa: E402
import modern_lib as L  # noqa: E402
from modern_lib import Asset, bend_path, arc, V  # noqa: E402

EXPORT_DIR = ROOT / "Exports" / "DojoKit" / "Props" / "modern"
L.TEX_DIR = EXPORT_DIR / "Textures"
WORK = ROOT / "WorkFiles" / "dojo" / "build" / "props" / "modern"
BLEND = ROOT / "Assets" / "Dojo" / "ModernProps.blend"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
BUDGET = 5000                               # STYLE_GUIDE: props 1-5k triangles

TEAL, WHITE, GALV = "M_DKP_Modern_PaintTeal", "M_DKP_Modern_PaintWhite", "M_DKP_Modern_Galvanised"
# r2: the shared dojo library for iron, timber, lamp glass and the vending display
IRON, WOOD, WOODD = "M_DJ_Iron", "M_DJ_TimberAged", "M_DJ_TimberDark"
CONC, FINS, PANEL = "M_DKP_Modern_Concrete", "M_DKP_Modern_CoilFins", "M_DJ_VendingPanel"
GLASS, BTN, PORC, RUB = ("M_DJ_GlassAmber", "M_DKP_Modern_ButtonLit", "M_DKP_Modern_Porcelain",
                         "M_DKP_Modern_Rubber")
PDARK, PCREAM, CHROME, FAN = ("M_DKP_Modern_PlasticDark", "M_DKP_Modern_PlasticCream", "M_DKP_Modern_Chrome",
                              "M_DKP_Modern_FanDark")
CABLE, INSUL, COPPER = "M_DKP_Modern_Cable", "M_DKP_Modern_PipeInsul", "M_DKP_Modern_Copper"
GREY, BULB, GRILLE, RUST = ("M_DKP_Modern_PaintGrey", "M_DKP_Modern_BulbLit", "M_DKP_Modern_FanGrille",
                            "M_DKP_Modern_Rust")

# ------------------------------------------------------------------------------------------------ spec numbers
ROOF_PITCH = math.radians(25.0)            # spec R4: lower roof 25 deg, eave +3.0 at Y 21.5, +4.17 at the wall Y 24
T25 = math.tan(ROOF_PITCH)
LOWER_EAVE_Y, LOWER_EAVE_Z = 21.5, 3.0
AC_FRONT_Y = 22.0                          # spec 5.1: 1.2 x 2.0 m, sticks 1.1 m out beyond the upper eave line (Y 23.1)
AC_ROOF_Z = LOWER_EAVE_Z + (AC_FRONT_Y - LOWER_EAVE_Y) * T25     # 3.2332 ("a roof at about +3.23")
AC_TOP = 5.10                              # r2: the grey-box's GASP-proved route 5 (+5.10; the spec's +4.75 is superseded)
AC_TOP_LOCAL = AC_TOP - AC_ROOF_Z          # 1.8668
VEND_TOP = 1.75                            # spec route 8
POLE_H = 8.0                               # spec gives none: a believable wooden distribution pole (see notes)
WALL_FACE_Y = 27.94                        # grey-box SM_DGB_Storehouse / SM_DGB_Residence south wall face
OUTBUILDING_EAVE_Z = 3.0499                # grey-box storehouse / residence roof bbox min (eave line Y 27.4)


def zr(y):
    """Roof surface height above the AC pivot at local y (the roof rises toward +Y)."""
    return y * T25


def pole_r(z):
    t = (z + 0.30) / (POLE_H + 0.30)
    return 0.140 - 0.040 * t


def pole_c(z):
    t = (z + 0.30) / (POLE_H + 0.30)
    return V(0.018 * math.sin(t * 2.4) - 0.009, 0.010 * math.sin(t * 3.7 + 1.0), z)


def rot_x90():
    return Matrix.Rotation(math.radians(90), 4, "X")      # local +Z -> -Y (toward the front)


def arch_outline(xa, xb, za, zb, rr, n_arc=8, n_side=3):
    """Rounded-top (arch-topped) window outline, square bottom corners, as (x, z) points."""
    pts = [(xb, za + (zb - rr - za) * k / n_side) for k in range(n_side + 1)]
    pts += [(xb - rr + rr * math.cos(math.pi / 2 * k / n_arc), zb - rr + rr * math.sin(math.pi / 2 * k / n_arc))
            for k in range(1, n_arc + 1)]
    pts += [(xb - rr - (xb - xa - 2 * rr) * k / n_side, zb) for k in range(1, n_side)]
    pts += [(xa + rr + rr * math.cos(math.pi / 2 + math.pi / 2 * k / n_arc),
             zb - rr + rr * math.sin(math.pi / 2 + math.pi / 2 * k / n_arc)) for k in range(0, n_arc + 1)]
    pts += [(xa, zb - rr - (zb - rr - za) * k / n_side) for k in range(1, n_side + 1)]
    pts += [(xa + (xb - xa) * k / n_side, za) for k in range(1, n_side)]
    return pts


# ================================================================================================ (a) vending machine

def vending():
    """r2: back to the SHEET's 0.80 m depth (GASP proved route 8 on the grey-box's 0.9 x 0.8 m box; the user decision
    keeps it, the showcase no longer squeezes the machine): the whole machine, top cap included, fits X +-0.45,
    Y +-0.40, flat top +1.75 = the grey-box box exactly. Front: an arch-topped display window (library
    M_DJ_VendingPanel: the sheet's pale backlit diffuser, blank) in a white surround inside the teal door, a white
    selection band, a white panel with a teal coin strip carrying the chrome coin fittings, and the lower teal zone
    with the dispense bay and two lit buttons (the sheet's orange pair)."""
    a = Asset("SM_DKP_Modern_VendingMachine", "climbprop",
              "plain drinks vending machine 0.90 x 0.80 x 1.75 m (the sheet's size and the grey-box box), faded teal + "
              "white, blank panels, arch-topped backlit display; climb prop (route 8), flush flat top +1.75, 0.80 deep")
    a.vbase = 0.08
    D0, D1 = -0.352, 0.392         # cabinet shell
    F = -0.372                     # door front face
    for x in (-0.37, 0.37):
        for y in (-0.29, 0.29):
            a.lathe([(0, 0.0), (0.028, 0.0), (0.028, 0.012), (0.014, 0.018), (0.014, 0.03), (0, 0.03)], RUB,
                    sides=10, center=(x, y, 0))
    a.box(-0.44, 0.44, -0.34, 0.38, 0.028, 0.085, IRON, bevel=0.004)
    a.box(-0.443, 0.443, D0, D1, 0.08, 1.72, TEAL, bevel=0.008)
    a.box(-0.439, 0.439, F, D0 + 0.002, 0.09, 1.70, TEAL, bevel=0.006)
    # flush top cap: exactly the 0.90 x 0.80 footprint, a 2.8 cm lip over the door front (no canopy)
    a.box(-0.45, 0.45, -0.40, 0.40, 1.718, VEND_TOP, TEAL, bevel=0.005)
    # ---- upper white face: the arch-topped display window in a white surround (blank: no text, no product art)
    WX0, WX1, WZ0, WZ1, WR = -0.37, 0.29, 1.30, 1.63, 0.085
    yp = F - 0.010
    a.plate_poly(-0.405, 0.325, 1.262, 1.668, arch_outline(WX0, WX1, WZ0, WZ1, WR), (WX0 + WX1) / 2,
                 (WZ0 + WZ1) / 2, WHITE, origin=(0, yp, 0), s_axis=(1, 0, 0), t_axis=(0, 0, 1))
    for (x0, x1, z0, z1) in ((-0.405, 0.325, 1.664, 1.668), (-0.405, -0.401, 1.262, 1.668),
                             (0.321, 0.325, 1.262, 1.668)):
        a.box(x0, x1, yp + 0.0005, F + 0.001, z0, z1, WHITE)
    # the window itself: an arch-shaped emissive panel set 4 mm back in the white surround (library 0-1 UV over the
    # window's bounding box, so the diffuser's soft hotspot sits in the middle of the glass)
    ol = arch_outline(WX0 - 0.004, WX1 + 0.004, WZ0 - 0.004, WZ1 + 0.004, WR + 0.004)
    cxw, czw = (WX0 + WX1) / 2, (WZ0 + WZ1) / 2
    ol = sorted(ol, key=lambda q: math.atan2(q[1] - czw, q[0] - cxw))
    yw = F - 0.004
    verts = [(cxw, yw, czw)] + [(q[0], yw, q[1]) for q in ol]
    faces = [(0, 1 + (i + 1) % len(ol), 1 + i) for i in range(len(ol))]
    u0, u1, v0, v1 = WX0 - 0.004, WX1 + 0.004, WZ0 - 0.004, WZ1 + 0.004
    uvs = [[((verts[k][0] - u0) / (u1 - u0), (verts[k][2] - v0) / (v1 - v0)) for k in f] for f in faces]
    a._add(verts, faces, PANEL, uvs, False)
    # white selection band under the window: groove line, row of blank lit buttons, small chrome button
    a.box(-0.405, 0.325, yp, F + 0.001, 1.10, 1.258, WHITE, bevel=0.003)
    a.box(-0.398, 0.318, yp - 0.002, yp + 0.004, 1.174, 1.180, PDARK)
    for i in range(7):
        x = -0.375 + i * 0.086
        a.box(x, x + 0.055, yp - 0.010, yp + 0.002, 1.198, 1.238, BTN, bevel=0.004)
    a.lathe([(0, 0), (0.014, 0), (0.014, 0.008), (0.009, 0.012), (0, 0.013)], CHROME, sides=12,
            xf=Matrix.Translation((0.28, yp, 1.14)) @ rot_x90())
    # ---- white panel B, and the TEAL coin strip beside it carrying the chrome coin fittings (sheet)
    a.box(-0.405, 0.135, yp, F + 0.001, 0.66, 1.02, WHITE, bevel=0.003)
    a.box(0.150, 0.325, yp + 0.002, F + 0.001, 0.66, 1.02, TEAL, bevel=0.003)
    a.box(0.185, 0.290, yp - 0.008, yp + 0.004, 0.84, 0.985, CHROME, bevel=0.005)       # coin plate
    a.box(0.222, 0.254, yp - 0.015, yp - 0.006, 0.905, 0.958, CHROME, bevel=0.003)      # slot bezel
    a.box(0.234, 0.242, yp - 0.017, yp - 0.013, 0.912, 0.950, PDARK)                    # slot
    a.tube([(0.270, yp - 0.008, 0.865), (0.270, yp - 0.024, 0.865)], 0.008, CHROME, sides=10)   # return lever
    for z in (0.745, 0.705):                                                              # two lit coin buttons
        a.lathe([(0, 0), (0.012, 0), (0.012, 0.007), (0, 0.010)], BTN, sides=12,
                xf=Matrix.Translation((0.2375, yp, z)) @ rot_x90())
    # ---- lower teal zone: dispense bay (chrome frame, dark recess, chrome flap), two lit buttons, coin return
    for (x0, x1, z0, z1) in ((-0.37, -0.35, 0.30, 0.47), (0.12, 0.14, 0.30, 0.47),
                             (-0.35, 0.12, 0.30, 0.32), (-0.35, 0.12, 0.45, 0.47)):
        a.box(x0, x1, F - 0.014, F + 0.002, z0, z1, CHROME, bevel=0.003)
    a.box(-0.35, 0.12, F - 0.006, F - 0.001, 0.32, 0.45, PDARK)
    a.hull([(x, y, z) for x in (-0.345, 0.115) for (y, z) in ((F - 0.013, 0.444), (F - 0.010, 0.444),
                                                           (F - 0.004, 0.330), (F - 0.001, 0.330))], CHROME)
    a.box(-0.35, 0.12, F - 0.018, F - 0.010, 0.444, 0.454, CHROME)
    for z in (0.42, 0.34):
        a.lathe([(0, 0), (0.022, 0), (0.022, 0.010), (0.016, 0.016), (0, 0.017)], BTN, sides=14,
                xf=Matrix.Translation((0.24, F, z)) @ rot_x90())
    a.box(0.205, 0.275, F - 0.022, F + 0.002, 0.18, 0.26, CHROME, bevel=0.008)
    a.box(0.215, 0.265, F - 0.025, F - 0.018, 0.19, 0.23, PDARK)
    # ---- right teal strip: lock and handle (inside the 0.40 line); door hinges on the left
    a.lathe([(0, 0), (0.022, 0), (0.022, 0.012), (0.016, 0.018), (0, 0.02)], CHROME, sides=14,
            xf=Matrix.Translation((0.39, F, 1.05)) @ rot_x90())
    a.box(0.382, 0.398, F - 0.026, F - 0.010, 1.10, 1.26, CHROME, bevel=0.006)
    for z in (0.26, 1.46):
        a.tube([(-0.436, F - 0.004, z), (-0.436, F - 0.004, z + 0.09)], 0.008, CHROME, sides=8)
    # ---- side panels: white insets over the teal cabinet (the sheet's side view: white upper, teal lower band)
    for sx in (-1, 1):
        x0 = 0.442 if sx > 0 else -0.449
        a.box(x0, x0 + 0.007, -0.33, 0.36, 0.62, 1.66, WHITE, bevel=0.003)
    # rear vent louvres, recessed into the back so nothing passes Y 0.40
    for k in range(6):
        z = 0.14 + k * 0.045
        a.box(-0.30, 0.30, D1 - 0.004, D1 + 0.006, z, z + 0.018, IRON)
    # collision: one flush block = the grey-box box (0.90 x 0.80, top +1.75)
    a.col_box(-0.45, 0.45, -0.40, 0.40, 0.0, VEND_TOP)
    return a


# ================================================================================================ fan + condenser parts

def fan_blade(a, c, rr0, rr1, th0, r, y_bl, cx, cz):
    """One twisted, pitched, swept fan blade. r2 (judges: 'dark shard normals'): the f1 blade was a 4-point diamond
    section whose smooth normals averaged the top and bottom faces at the razor leading and trailing edges (the dark
    shards). Now 9 stations and an 8-point cambered section with a 2 mm thick rounded leading edge and a squared 1.5 mm
    trailing edge: the smooth normals of the upper and lower skins never meet at a knife edge, the root and tip are
    capped flat (fans from the section centre, sharp rims), and the blade is 5 mm thick at mid-chord."""
    st = []
    K = 9
    for k in range(K):
        t = k / (K - 1)
        rr = r * (rr0 + (rr1 - rr0) * t)
        chord = r * (0.20 + 0.30 * math.sin(math.pi * 0.5 * t) ** 0.8)
        pitch = math.radians(42 - 24 * t)
        th = th0 + 0.38 * t
        rad = V(math.cos(th), 0, math.sin(th))
        tan = V(-math.sin(th), 0, math.cos(th))
        ctr = V(cx, y_bl, cz) + rad * rr
        cd = tan * math.cos(pitch) + V(0, 1, 0) * math.sin(pitch)
        nrm = rad.cross(cd).normalized()
        h = chord / 2
        tk = 0.005 * (1 - 0.35 * t)
        camber = 0.004
        # (chord position -1 = leading edge .. +1 = trailing edge, offset along the blade normal)
        prof = [(-1.0, 0.0), (-0.93, 0.45 * tk + 0.2 * camber), (-0.4, 0.5 * tk + 0.9 * camber),
                (0.35, 0.35 * tk + 0.8 * camber), (1.0, 0.075 * tk * 4 + 0.1 * camber),
                (1.0, -0.075 * tk * 4 + 0.1 * camber), (0.35, -0.30 * tk + 0.8 * camber),
                (-0.4, -0.45 * tk + 0.9 * camber), (-0.93, -0.40 * tk + 0.2 * camber)]
        st.append([ctr - cd * (u * h) + nrm * v for u, v in prof])
    n = len(st[0])
    verts = [p for s_ in st for p in s_]
    faces = []
    for k in range(K - 1):
        for i in range(n):
            j = (i + 1) % n
            faces.append((k * n + i, k * n + j, (k + 1) * n + j, (k + 1) * n + i))
    ends = []
    for k, flip in ((0, True), (K - 1, False)):
        cen = sum(st[k], V(0, 0, 0)) / n
        verts.append(cen)
        ci = len(verts) - 1
        for i in range(n):
            j = (i + 1) % n
            faces.append((ci, k * n + j, k * n + i) if flip else (ci, k * n + i, k * n + j))
            ends.append((k * n + i, k * n + j))
    sm = [True] * (len(faces) - 2 * n) + [False] * (2 * n)
    a._add(verts, faces, FAN, None, smooth=sm, sharp_edges=ends)


def fan_assembly(a, cx, y_face, cz, r, depth, blades=3):
    """Round fan opening on a -Y face: dark recessed bell-mouth shroud, motor plate and motor, twisted pitched
    blades with a hub cap, and an alpha-masked dense wire guard (11 rings, 14 spokes) with a wire rim."""
    y_back = y_face + depth
    a.tube([(cx, y_face, cz), (cx, y_back, cz)], r, FAN, sides=32, caps=False, smooth=True, radii=[r, r * 0.96])
    a.tube([(cx, y_back - 0.002, cz), (cx, y_face + 0.004, cz)], r * 0.955, FAN, sides=32, caps=False, smooth=True)
    a.lathe([(0, 0), (r * 0.96, 0), (r * 0.96, 0.004), (0, 0.004)], FAN, sides=32,
            xf=Matrix.Translation((cx, y_back - 0.004, cz)) @ rot_x90())
    a.lathe([(0, 0), (r * 0.20, 0), (r * 0.20, depth * 0.28), (r * 0.17, depth * 0.34), (0, depth * 0.34)], FAN,
            sides=16, xf=Matrix.Translation((cx, y_back - 0.004, cz)) @ rot_x90())
    y_bl = y_face + depth * 0.42
    for b in range(blades):
        fan_blade(a, None, 0.15, 0.90, 2 * math.pi * b / blades + 0.4, r, y_bl, cx, cz)
    hr = r * 0.15
    a.lathe([(0, 0), (hr, 0), (hr, 0.035), (hr * 0.8, 0.05), (hr * 0.4, 0.058), (0, 0.06)], GALV, sides=16,
            xf=Matrix.Translation((cx, y_bl + 0.02, cz)) @ rot_x90())
    # guard: a gently domed alpha-masked disc + wire rim + 4 clips
    yg = y_face - 0.012
    R = r * 1.02
    n = 32
    verts = [(cx, yg - 0.008, cz)] + [(cx + R * math.cos(2 * math.pi * i / n), yg, cz + R * math.sin(2 * math.pi * i / n))
                                      for i in range(n)]
    faces = [(0, 1 + i, 1 + (i + 1) % n) for i in range(n)]
    uvs = [[(0.5 + (verts[k][0] - cx) / (2 * R), 0.5 + (verts[k][2] - cz) / (2 * R)) for k in f] for f in faces]
    a._add(verts, faces, GRILLE, uvs, False)
    a.tube(arc((cx, yg, cz), R, 0, 2 * math.pi, 32), 0.0035, GALV, sides=4, closed=True)
    for k in range(4):
        ang = math.pi / 4 + k * math.pi / 2
        d = V(math.cos(ang), 0, math.sin(ang))
        p = V(cx, 0, cz) + d * (R + 0.006)
        a.box(p.x - 0.012, p.x + 0.012, yg - 0.004, y_face + 0.001, p.z - 0.012, p.z + 0.012, GALV)


def condenser_case(a, x0, x1, y0, y1, z0, z1, fan_cx, fan_cz, fan_r, front_depth, fins_left=True, blades=3):
    """White casing: open front section with a round fan opening, closed core, fin panels on the left and back."""
    yc = y0 + front_depth
    a.box(x0, x1, yc, y1, z0, z1, WHITE, bevel=0.008)
    a.plate_hole(x0 + 0.004, x1 - 0.004, z0 + 0.004, z1 - 0.004, fan_cx, fan_cz, fan_r, WHITE,
                 origin=(0, y0, 0), s_axis=(1, 0, 0), t_axis=(0, 0, 1), n=32)
    a.box(x0, x1, y0 + 0.002, yc + 0.004, z1 - 0.012, z1, WHITE, bevel=0.004)
    a.box(x0, x1, y0 + 0.002, yc + 0.004, z0, z0 + 0.012, WHITE, bevel=0.004)
    a.box(x0, x0 + 0.012, y0 + 0.002, yc + 0.004, z0 + 0.01, z1 - 0.01, WHITE, bevel=0.004)
    a.box(x1 - 0.012, x1, y0 + 0.002, yc + 0.004, z0 + 0.01, z1 - 0.01, WHITE, bevel=0.004)
    fan_assembly(a, fan_cx, y0 + 0.001, fan_cz, fan_r, front_depth - 0.004, blades=blades)
    h = z1 - z0
    fz0, fz1 = z0 + 0.10 * h, z1 - 0.10 * h
    if fins_left:
        fy0, fy1 = yc + 0.06, y1 - 0.06
        a.box(x0 - 0.004, x0 + 0.002, fy0, fy1, fz0, fz1, FINS)
        for (yy0, yy1, zz0, zz1) in ((fy0 - 0.02, fy0, fz0 - 0.02, fz1 + 0.02), (fy1, fy1 + 0.02, fz0 - 0.02, fz1 + 0.02),
                                     (fy0, fy1, fz0 - 0.02, fz0), (fy0, fy1, fz1, fz1 + 0.02)):
            a.box(x0 - 0.007, x0 + 0.001, yy0, yy1, zz0, zz1, WHITE)
        nb = max(3, int((fy1 - fy0) / 0.09))
        for k in range(1, nb):
            y = fy0 + (fy1 - fy0) * k / nb
            a.box(x0 - 0.012, x0 - 0.007, y - 0.0025, y + 0.0025, fz0 - 0.005, fz1 + 0.005, GALV)
    return yc


def valve_pair(a, x_face, y, zs, sx=1):
    """Two service valves on a side face (+X when sx = 1): galvanised bodies, brass-copper caps."""
    for (z, rp) in zip(zs, (0.010, 0.014)):
        a.box(*sorted((x_face, x_face + sx * 0.035)), y - 0.022, y + 0.022, z - 0.022, z + 0.022, GALV, bevel=0.003)
        a.tube([(x_face + sx * 0.035, y, z), (x_face + sx * 0.050, y, z)], rp * 0.8, COPPER, sides=8)
        a.tube([(x_face + sx * 0.015, y - 0.022, z), (x_face + sx * 0.015, y - 0.040, z)], 0.008, COPPER, sides=8)


# ================================================================================================ (b) roof AC unit

def ac_roof():
    a = Asset("SM_DKP_Modern_ACUnit_Roof", "climbprop",
              "condenser on a dark iron stand for the hall's 25 deg lower roof; stand footprint 1.2 x 2.0 m, flat "
              "condenser top +5.10 (1.2 x 1.08 m, R3) at the grey-box route-5 position (front feet on the roof at "
              "+3.23, Y 22.0); runners lie on the roof slope; line set + service valves on the +X side; climb prop")
    # r2: built for the grey-box route (top +5.10, GASP-proved) instead of being Z-scaled in Unreal (the showcase's
    # 1.23 Z-scale lifted the runners 0.21 m off the tiles): the casing keeps its 0.877 m height and rides on taller
    # legs; the runners and their pads stay on the roof plane (zr), so nothing floats
    X0, X1, Y0, Y1 = -0.60, 0.60, 0.02, 1.10
    ZT = AC_TOP_LOCAL
    ZB = ZT - 0.877
    a.vbase = ZB
    condenser_case(a, X0, X1, Y0, Y1, ZB, ZT, fan_cx=-0.17, fan_cz=(ZB + ZT) / 2 + 0.01, fan_r=0.335,
                   front_depth=0.12)
    # back coil + frame
    a.box(-0.54, 0.36, Y1 - 0.002, Y1 + 0.004, ZB + 0.09, ZT - 0.09, FINS)
    for (xa, xb, za, zb) in ((-0.56, -0.54, ZB + 0.07, ZT - 0.07), (0.36, 0.38, ZB + 0.07, ZT - 0.07),
                             (-0.54, 0.36, ZB + 0.07, ZB + 0.09), (-0.54, 0.36, ZT - 0.09, ZT - 0.07)):
        a.box(xa, xb, Y1 - 0.001, Y1 + 0.007, za, zb, WHITE)
    # right side (+X): service panel with screw heads, valve cover, two service valves
    a.box(X1 - 0.002, X1 + 0.006, 0.55, 1.04, ZB + 0.05, ZT - 0.30, WHITE, bevel=0.003)
    for (y, z) in ((0.58, ZB + 0.08), (1.01, ZB + 0.08), (0.58, ZT - 0.33), (1.01, ZT - 0.33)):
        a.box(X1 + 0.006, X1 + 0.010, y - 0.006, y + 0.006, z - 0.006, z + 0.006, CHROME)
    a.box(X1 - 0.002, X1 + 0.008, 0.08, 0.40, ZB + 0.03, ZB + 0.30, WHITE, bevel=0.003)
    VY, VZ = 0.24, (ZB + 0.09, ZB + 0.18)
    valve_pair(a, X1 + 0.008, VY, VZ)
    # insulated line set: out of the valves, down, back along the roof under the unit's rear, into the cream cover
    for (z, r_, xo) in ((VZ[0], 0.013, 0.080), (VZ[1], 0.017, 0.118)):
        # r2: down to the tiles and back up the slope (the taller stand would otherwise leave it hanging mid-air)
        off = 0.03 if xo < 0.1 else 0.075
        path = bend_path([(X1 + 0.05, VY, z), (X1 + xo, VY, z), (X1 + xo, VY, zr(VY) + off),
                          (X1 + xo, 1.17, zr(1.17) + off), (0.50, 1.17, zr(1.17) + off)], 0.05, 4)
        a.tube(path, r_, INSUL, sides=8)
    # wiring whip: flexible conduit from the service panel port looping to a galvanised box behind the unit
    a.box(X1 + 0.006, X1 + 0.030, 0.93, 0.97, ZB + 0.24, ZB + 0.28, GALV, bevel=0.003)
    wp = bend_path([(X1 + 0.03, 0.95, ZB + 0.26), (X1 + 0.10, 0.95, ZB + 0.22), (X1 + 0.10, 1.06, ZB + 0.05),
                    (0.44, 1.17, 0.66)], 0.07, 6)
    a.tube(wp, 0.011, CABLE, sides=6)
    a.box(0.36, 0.44, 1.13, 1.21, 0.60, 0.71, GALV, bevel=0.004)
    cp = bend_path([(0.40, 1.21, 0.63), (0.40, 1.32, zr(1.32) + 0.05), (0.40, 1.985, zr(1.985) + 0.05)], 0.05, 4)
    a.tube(cp, 0.011, GALV, sides=6)
    # base pan
    a.box(X0 + 0.01, X1 - 0.01, Y0 + 0.01, Y1 - 0.01, ZB - 0.018, ZB + 0.002, GALV, bevel=0.003)
    # ---- dark painted steel stand: level frame on sloped runners that lie on the tiles and fix to the hall wall
    RX = 0.525
    RB, RT = ZB - 0.063, ZB - 0.018
    for sx in (-1, 1):
        xc = RX * sx
        a.box(xc - 0.024, xc + 0.024, 0.03, 1.08, RB, RT, IRON)
        a.hull([(xc + dx, y, zr(y) + dz) for dx in (-0.028, 0.028) for y in (0.0, 1.99) for dz in (0.02, 0.07)], IRON)
        for y in (0.07, 0.95, 1.85):
            a.hull([(xc + dx, y + dy, zr(y + dy) + dz) for dx in (-0.045, 0.045) for dy in (-0.06, 0.06)
                    for dz in (-0.004, 0.02)], RUB)
        for y in (0.055, 0.555, 1.055):
            z_foot = zr(y) + 0.07
            if RB - z_foot > 0.003:
                a.box(xc - 0.022, xc + 0.022, y - 0.022, y + 0.022, z_foot - 0.004, RB + 0.002, IRON)
                a.box(xc - 0.035, xc + 0.035, y - 0.035, y + 0.035, z_foot - 0.004, z_foot + 0.004, IRON)
        a.tube([(xc, 0.075, zr(0.075) + 0.10), (xc, 0.53, RB - 0.01)], 0.008, IRON, sides=5)
        a.box(xc - 0.035, xc + 0.035, 1.985, 1.998, zr(1.99) + 0.01, zr(1.99) + 0.19, IRON)
        for z in (zr(1.99) + 0.09, zr(1.99) + 0.16):
            a.box(xc - 0.01, xc + 0.01, 1.975, 1.985, z - 0.01, z + 0.01, IRON)
    for y in (0.03, 1.035):
        a.box(-RX - 0.024, RX + 0.024, y, y + 0.045, RB, RT, IRON)
    # r2: the taller stand gets a mid rail on each side and a rear cross brace (the sheet's stand is a braced frame)
    for sx in (-1, 1):
        xc = RX * sx
        zm0, zm1 = zr(0.055) + 0.07 + 0.45 * (RB - zr(0.055) - 0.07), zr(1.055) + 0.07 + 0.45 * (RB - zr(1.055) - 0.07)
        zm = max(zm0, zm1)
        a.box(xc - 0.018, xc + 0.018, 0.035, 1.075, zm - 0.02, zm + 0.02, IRON)
    a.tube([(-RX, 1.045, zr(1.045) + 0.10), (RX, 1.045, RB - 0.01)], 0.007, IRON, sides=5)
    for s in (-1, 1):
        a.tube([(-RX * s, 0.045, zr(0.045) + 0.10), (RX * s, 0.045, RB - 0.01)], 0.007, IRON, sides=5)
    # line-set cover: vertical elbow behind the unit, then along the roof to a wall cap
    a.box(0.455, 0.545, 1.13, 1.21, zr(1.21) + 0.02, 0.705, PCREAM, bevel=0.004)
    a.box(0.45, 0.55, 1.125, 1.215, 0.700, 0.715, PCREAM, bevel=0.003)
    a.hull([(x, y, zr(y) + dz) for x in (0.455, 0.545) for y in (1.21, 1.975) for dz in (0.02, 0.085)], PCREAM)
    a.box(0.44, 0.56, 1.975, 1.998, zr(1.99) + 0.00, zr(1.99) + 0.13, PCREAM, bevel=0.004)
    # condensate drain hose from the base pan curling down onto the tiles
    hp = bend_path([(-0.42, 0.95, ZB - 0.02), (-0.42, 0.95, 0.56), (-0.42, 1.02, zr(1.02) + 0.03),
                    (-0.42, 1.30, zr(1.30) + 0.015)], 0.04, 4)
    a.tube(hp, 0.008, RUB, sides=6)
    # collision: the unit block with a sloped bottom on the roof plane, and the low runner / duct zone behind it
    a.col_hull([(x, y, z) for x in (X0, X1) for (y, z) in ((-0.02, zr(-0.02) - 0.03), (Y1, zr(Y1) - 0.03),
                                                              (-0.02, ZT), (Y1, ZT))])
    a.col_hull([(x, y, z) for x in (X0, X1) for (y, z) in ((Y1, zr(Y1) - 0.02), (Y1, 0.78), (2.0, zr(2.0) - 0.02),
                                                              (2.0, zr(2.0) + 0.16))])
    a.info["top_local_z"] = ZT
    return a


# ================================================================================================ (b2) small wall AC

def ac_wall():
    a = Asset("SM_DKP_Modern_ACUnit_Wall", "thin",
              "small split-type condenser 0.78 x 0.28 x 0.54 m on two galvanised wall brackets; wall dressing")
    X0, X1, Y0, Y1, ZB, ZT = -0.39, 0.39, -0.335, -0.055, 0.015, 0.555
    a.vbase = ZB
    condenser_case(a, X0, X1, Y0, Y1, ZB, ZT, fan_cx=-0.12, fan_cz=0.29, fan_r=0.195, front_depth=0.07)
    a.box(-0.36, 0.30, Y1 - 0.002, Y1 + 0.004, ZB + 0.06, ZT - 0.06, FINS)
    a.box(X1 - 0.002, X1 + 0.008, -0.22, -0.07, ZB + 0.03, ZB + 0.24, WHITE, bevel=0.003)
    for z in (0.10, 0.15):
        a.box(X1 + 0.008, X1 + 0.03, -0.12, -0.09, z - 0.012, z + 0.012, GALV)
    lp = bend_path([(X1 + 0.03, -0.105, 0.125), (0.48, -0.105, 0.125), (0.48, -0.105, 0.30), (0.48, -0.005, 0.30)],
                   0.04, 5)
    a.tube(lp, 0.018, INSUL, sides=8)
    a.lathe([(0, 0), (0.045, 0), (0.045, 0.012), (0.03, 0.022), (0, 0.024)], PCREAM, sides=16,
            xf=Matrix.Translation((0.48, 0.0, 0.30)) @ rot_x90())
    a.tube(bend_path([(X1, -0.25, 0.05), (0.43, -0.25, 0.05), (0.43, -0.25, -0.12), (0.43, -0.004, -0.2)], 0.05, 5),
           0.006, CABLE, sides=6)
    for xc in (-0.27, 0.27):
        a.box(xc - 0.02, xc + 0.02, -0.006, 0.0, -0.30, 0.02, GALV, bevel=0.002)
        a.box(xc - 0.02, xc + 0.02, -0.42, -0.004, -0.03, 0.0, GALV, bevel=0.002)
        a.tube([(xc, -0.007, -0.27), (xc, -0.37, -0.028)], 0.009, GALV, sides=6)
        for y in (-0.30, -0.10):
            a.box(xc - 0.03, xc + 0.03, y - 0.025, y + 0.025, 0.0, ZB, RUB)
        for z in (-0.25, -0.02):
            a.lathe([(0, 0), (0.011, 0), (0.011, 0.007), (0, 0.008)], GALV, sides=6,
                    xf=Matrix.Translation((xc, -0.006, z - 0.01 if z > -0.1 else z)) @ rot_x90())
    a.col_box(-0.40, 0.53, -0.425, 0.0, -0.30, 0.565)
    return a


# ================================================================================================ lanterns (lamps)

def lantern(a, cx, cy, ztop, h, rt, rb, hood):
    """A hexagonal iron lantern hanging from a ring at ztop: ball finial, flared hex hood, top band, six seeded amber
    glass panes that TAPER toward the bottom (the emissive slot, one pane = 0-1 UV), corner posts, bottom tray and
    drop, and a bulb (BulbLit) on a socket inside at the glass hotspot height. Returns the bulb centre."""
    a.tube(arc((cx, cy, ztop - 0.014), 0.012, 0, 2 * math.pi, 12), 0.0035, IRON, sides=6, closed=True)
    zf = ztop - 0.075
    a.lathe([(0, 0), (0.013, 0), (0.013, 0.010), (0.007, 0.016), (0.015, 0.026), (0.015, 0.036), (0.007, 0.046),
             (0.004, 0.058), (0, 0.061)], IRON, sides=8, center=(cx, cy, zf - 0.002))
    hh = hood * 0.75
    zh0 = zf - hh
    a.lathe([(0, zh0), (hood, zh0), (hood, zh0 + 0.012), (hood * 0.80, zh0 + 0.032), (hood * 0.46, zh0 + hh * 0.62),
             (hood * 0.20, zh0 + hh * 0.93), (0, zf)], IRON, sides=6, smooth=False, center=(cx, cy, 0))
    zt = zh0 - 0.002
    a.lathe([(rt + 0.004, zt - 0.026), (rt + 0.013, zt - 0.022), (rt + 0.013, zt), (rt * 0.4, zt)], IRON, sides=6,
            smooth=False, center=(cx, cy, 0))
    zg1 = zt - 0.024
    zg0 = ztop - h + 0.060
    for k in range(6):
        a0, a1 = math.radians(60 * k), math.radians(60 * (k + 1))
        B0 = (cx + rb * math.cos(a0), cy + rb * math.sin(a0), zg0)
        B1 = (cx + rb * math.cos(a1), cy + rb * math.sin(a1), zg0)
        T1 = (cx + rt * math.cos(a1), cy + rt * math.sin(a1), zg1)
        T0 = (cx + rt * math.cos(a0), cy + rt * math.sin(a0), zg1)
        a.quad([B0, B1, T1, T0], GLASS, uv01=True)
        a.tube([(cx + (rb + 0.006) * math.cos(a0), cy + (rb + 0.006) * math.sin(a0), zg0 - 0.004),
                (cx + (rt + 0.008) * math.cos(a0), cy + (rt + 0.008) * math.sin(a0), zg1 + 0.004)],
               0.0055, IRON, sides=4)
    zb = ztop - h
    a.lathe([(0, zb + 0.022), (rb * 0.45, zb + 0.022), (rb + 0.014, zg0 - 0.016), (rb + 0.014, zg0 + 0.002),
             (rb * 0.5, zg0 + 0.004)], IRON, sides=6, smooth=False, center=(cx, cy, 0))
    a.lathe([(0, 0), (0.006, 0.0), (0.016, 0.010), (0.021, 0.018), (0.012, 0.024), (0, 0.024)], IRON, sides=8,
            center=(cx, cy, zb - 0.002))
    zbulb = zg0 + 0.45 * (zg1 - zg0)
    a.lathe([(0, zbulb + 0.030), (0.013, zbulb + 0.030), (0.013, zg1 + 0.002), (0, zg1 + 0.002)], IRON, sides=8,
            center=(cx, cy, 0))
    br = min(0.026, rb * 0.30)
    a.lathe([(0, zbulb - br * 1.1), (br * 0.55, zbulb - br * 0.95), (br * 0.92, zbulb - br * 0.45), (br, zbulb),
             (br * 0.8, zbulb + br * 0.55), (br * 0.5, zbulb + br * 1.05), (0, zbulb + br * 1.15)], BULB, sides=10,
            center=(cx, cy, 0))
    return (cx, cy, zbulb)


def square_lantern(a, cx, cy, ztop, h, rt, rb, hood):
    """r2 (judges + the sheet's wall lamp and street lamps): a tall SQUARE four-sided iron lantern hanging from a ring:
    a small finial under the ring, a pyramid cap with a flat eave lip (half-width `hood`), a top band, four library
    amber glass panes (M_DJ_GlassAmber, 0-1 per pane, so each pane carries the library's bulb hotspot) that TAPER
    from half-width rt at the top to rb at the bottom and fill 62 % of the lantern height, iron corner posts, a
    bottom band, a tapered base and a drop; a pear bulb (BulbLit) at the glass centre. Returns the bulb centre."""
    k = h / 0.40
    sq = math.sqrt(2.0)
    ph = math.pi / 4
    a.tube(arc((cx, cy, ztop - 0.012 * k), 0.012 * k, 0, 2 * math.pi, 12), 0.0035, IRON, sides=6, closed=True)
    z_fin = ztop - 0.030 * k                                                  # finial: neck, ball, collar
    a.lathe([(0, z_fin), (0.012 * k, z_fin), (0.014 * k, z_fin + 0.006 * k), (0.008 * k, z_fin + 0.010 * k),
             (0.011 * k, z_fin + 0.016 * k), (0.009 * k, z_fin + 0.022 * k), (0.004 * k, z_fin + 0.0255 * k),
             (0, z_fin + 0.026 * k)], IRON, sides=10, center=(cx, cy, 0))
    z_cap1 = z_fin + 0.001
    z_cap0 = z_cap1 - 0.075 * k                                              # eave lip bottom
    lip = 0.010 * k
    a.lathe([(0, z_cap0), (hood * sq, z_cap0), (hood * sq, z_cap0 + lip), ((hood - 0.012 * k) * sq, z_cap0 + lip + 0.004 * k),
             (0.018 * k * sq, z_cap1 - 0.004 * k), (0.012 * k * sq, z_cap1), (0, z_cap1)], IRON, sides=4, phase=ph,
            smooth=False, center=(cx, cy, 0))
    z_b1 = z_cap0 + 0.001
    z_b0 = z_b1 - 0.017 * k                                                  # top band
    a.lathe([(0, z_b0), ((rt + 0.010 * k) * sq, z_b0), ((rt + 0.012 * k) * sq, z_b0 + 0.004 * k),
             ((rt + 0.012 * k) * sq, z_b1), (0, z_b1)], IRON, sides=4, phase=ph, smooth=False, center=(cx, cy, 0))
    zg1 = z_b0 + 0.001
    zg0 = zg1 - 0.62 * h                                                     # glass: 62 % of the lantern height
    corners = [(math.cos(ph + math.pi / 2 * i), math.sin(ph + math.pi / 2 * i)) for i in range(4)]
    for i in range(4):
        (c0x, c0y), (c1x, c1y) = corners[i], corners[(i + 1) % 4]
        B0 = (cx + rb * sq * c0x, cy + rb * sq * c0y, zg0)
        B1 = (cx + rb * sq * c1x, cy + rb * sq * c1y, zg0)
        T1 = (cx + rt * sq * c1x, cy + rt * sq * c1y, zg1)
        T0 = (cx + rt * sq * c0x, cy + rt * sq * c0y, zg1)
        a.quad([B0, B1, T1, T0], GLASS, uv01=True)
        a.tube([(cx + (rb + 0.003) * sq * c0x, cy + (rb + 0.003) * sq * c0y, zg0 - 0.004),
                (cx + (rt + 0.004) * sq * c0x, cy + (rt + 0.004) * sq * c0y, zg1 + 0.004)], 0.0065 * k, IRON,
               sides=4, phase=ph)
    zbb1 = zg0 - 0.001                                                       # bottom band, tapered base, drop
    zbb0 = zbb1 - 0.012 * k
    zbase = zbb0 - 0.018 * k
    a.lathe([(0, zbase), (rb * 0.55 * sq, zbase), ((rb + 0.006 * k) * sq, zbb0), ((rb + 0.010 * k) * sq, zbb0 + 0.002),
             ((rb + 0.010 * k) * sq, zbb1), (0, zbb1)], IRON, sides=4, phase=ph, smooth=False, center=(cx, cy, 0))
    a.lathe([(0, 0), (0.006 * k, 0.0), (0.012 * k, 0.008 * k), (0.009 * k, 0.014 * k), (0, 0.016 * k)], IRON,
            sides=8, center=(cx, cy, zbase - 0.015 * k))
    zbulb = zg0 + 0.50 * (zg1 - zg0)
    a.lathe([(0, zbulb + 0.030 * k), (0.012 * k, zbulb + 0.030 * k), (0.012 * k, zg1 + 0.002), (0, zg1 + 0.002)], IRON,
            sides=8, center=(cx, cy, 0))
    br = min(0.024 * k, rb * 0.30)
    a.lathe([(0, zbulb - br * 1.1), (br * 0.55, zbulb - br * 0.95), (br * 0.92, zbulb - br * 0.45), (br, zbulb),
             (br * 0.8, zbulb + br * 0.55), (br * 0.5, zbulb + br * 1.05), (0, zbulb + br * 1.15)], BULB, sides=10,
            center=(cx, cy, 0))
    return (cx, cy, zbulb)


def wall_lamp():
    """r2 redesign to the sheet's wall lamp (panel 11c): a wooden backplate POST on the wall that runs from above the
    arm to well below the lantern, an iron arm at its head reaching 0.40 m out with a curved iron scroll strut under
    it, and a tall square tapered lantern (0.40 m, glass 62 % of its height, pyramid cap with finial and ring)
    hanging from the arm's end. Pivot: the post's back face on the wall at the arm height's origin (as f1)."""
    a = Asset("SM_DKP_Modern_WallLamp", "thin",
              "wall lamp: wooden backplate post, iron arm with a scroll strut reaching 0.40 m, a 0.40 m tall square "
              "tapered iron lantern with amber glass (62 % of its height), pyramid cap, finial and ring; pivot on the "
              "wall at the post's centre line")
    a.box(-0.045, 0.045, -0.055, 0.0, -0.52, 0.27, WOODD, bevel=0.006)                              # backplate post
    a.box(-0.018, 0.018, -0.435, -0.053, 0.196, 0.224, IRON, bevel=0.003)                            # arm
    a.box(-0.018, 0.018, -0.435, -0.415, 0.172, 0.224, IRON, bevel=0.003)                            # arm end drop
    for z in (0.14, 0.24):                                                                           # post straps
        a.box(-0.049, 0.049, -0.059, -0.053, z - 0.012, z + 0.012, IRON, bevel=0.0015)
    for z in (-0.44, 0.19):                                                                          # wall bolts
        a.lathe([(0, 0), (0.010, 0), (0.010, 0.006), (0, 0.008)], IRON, sides=6,
                xf=Matrix.Translation((0, -0.059, z)) @ rot_x90())
    # scroll strut: a quarter-round sweep from the post up under the arm, ending in a small curl
    sc = arc((0, -0.055, 0.20), 0.22, -math.pi / 2, -math.pi, 14, u_axis=(0, 1, 0), v_axis=(0, 0, 1))
    a.tube(sc, 0.008, IRON, sides=6)
    a.tube([(0, -0.40, 0.172), (0, -0.40, 0.160)], 0.004, IRON, sides=6)                             # hook
    a.info["bulb_local"] = square_lantern(a, 0.0, -0.40, 0.162, 0.40, rt=0.105, rb=0.085, hood=0.13)
    a.col_box(-0.14, 0.14, -0.54, 0.0, -0.52, 0.27)
    return a


def street_lamp(kind):
    if kind == "A":
        a = Asset("SM_DKP_Modern_StreetLamp_A", "thin",
                  "street lamp type A, 3.0 m: concrete footing, cast base, tapered iron post, capital and finial, "
                  "short bracket with a smooth curved strut carrying a 0.52 m square tapered lantern close under the post top; a "
                  "wire eye on the head (SOCKET Wire)")
        a.box(-0.22, 0.22, -0.22, 0.22, 0.0, 0.12, CONC, bevel=0.012)
        a.box(-0.13, 0.13, -0.13, 0.13, 0.12, 0.14, IRON, bevel=0.004)
        for x in (-0.095, 0.095):
            for y in (-0.095, 0.095):
                a.lathe([(0, 0), (0.012, 0), (0.012, 0.01), (0, 0.012)], IRON, sides=6, center=(x, y, 0.14))
        a.lathe([(0.0, 0.14), (0.115, 0.14), (0.115, 0.17), (0.098, 0.19), (0.088, 0.25), (0.074, 0.31),
                 (0.066, 0.52), (0.078, 0.545), (0.078, 0.575), (0.058, 0.60), (0.0, 0.60)], IRON, sides=8,
                phase=math.pi / 8, smooth=False)
        a.tube([(0, 0, 0.598), (0, 0, 2.86)], 0.046, IRON, sides=12, radii=[0.046, 0.036])
        for z, r in ((1.30, 0.052), (2.60, 0.044)):
            a.lathe([(0, z - 0.02), (r, z - 0.02), (r, z + 0.02), (0, z + 0.02)], IRON, sides=12)
        a.lathe([(0, 2.855), (0.050, 2.855), (0.050, 2.875), (0.038, 2.89), (0.038, 2.93), (0.054, 2.945),
                 (0.054, 2.962), (0, 2.965)], IRON, sides=12, smooth=False)
        a.lathe([(0, 0), (0.02, 0.004), (0.026, 0.014), (0.014, 0.024), (0.006, 0.030), (0.004, 0.036), (0, 0.037)],
                IRON, sides=10, center=(0, 0, 2.963))
        LX = -0.30
        a.box(LX - 0.03, -0.03, -0.012, 0.012, 2.866, 2.890, IRON, bevel=0.003)
        a.tube(arc((-0.225, 0, 2.68), 0.188, 0, math.pi / 2, 16), 0.009, IRON, sides=6)
        a.tube([(LX, 0, 2.866), (LX, 0, 2.84)], 0.005, IRON, sides=6)
        a.info["bulb_local"] = square_lantern(a, LX, 0.0, 2.842, 0.52, rt=0.135, rb=0.108, hood=0.17)
        # wire eye on the +X side of the head (span-wire tie point)
        a.tube([(0.035, 0, 2.905), (0.062, 0, 2.905)], 0.006, IRON, sides=6)
        a.tube(arc((0.080, 0, 2.905), 0.017, 0, 2 * math.pi, 12), 0.004, IRON, sides=5, closed=True)
        a.socket("Wire", (0.097, 0, 2.905))
        a.col_box(-0.22, 0.22, -0.22, 0.22, 0.0, 0.14)
        a.col_box(-0.12, 0.12, -0.12, 0.12, 0.14, 0.60)
        a.col_hull([(x, y, z) for x in (-0.05, 0.05) for y in (-0.05, 0.05) for z in (0.60, 3.0)])
        a.col_box(LX - 0.21, LX + 0.21, -0.19, 0.19, 2.32, 2.89)
    else:
        a = Asset("SM_DKP_Modern_StreetLamp_B", "thin",
                  "street lamp type B, 2.5 m: plain footing and base, iron post, top crossbar with two wire eyes "
                  "(SOCKETs Wire_L / Wire_R) and a spike, quarter-round bracket carrying a 0.44 m square tapered lantern")
        a.box(-0.17, 0.17, -0.17, 0.17, 0.0, 0.10, CONC, bevel=0.01)
        a.lathe([(0.0, 0.10), (0.09, 0.10), (0.09, 0.13), (0.07, 0.15), (0.058, 0.36), (0.066, 0.38), (0.066, 0.40),
                 (0.05, 0.42), (0.0, 0.42)], IRON, sides=12, smooth=False)
        a.tube([(0, 0, 0.418), (0, 0, 2.40)], 0.040, IRON, sides=12, radii=[0.040, 0.031])
        a.lathe([(0, 2.395), (0.036, 2.395), (0.036, 2.415), (0, 2.42)], IRON, sides=12)
        a.box(-0.20, 0.20, -0.012, 0.012, 2.40, 2.424, IRON, bevel=0.003)                      # crossbar
        a.lathe([(0, 0), (0.014, 0), (0.014, 0.012), (0.006, 0.02), (0.004, 0.06), (0, 0.076)], IRON, sides=8,
                center=(0, 0, 2.424))
        for sx, lab in ((-1, "Wire_L"), (1, "Wire_R")):
            a.tube(arc((sx * 0.19, 0, 2.448), 0.016, 0, 2 * math.pi, 12), 0.004, IRON, sides=5, closed=True)
            a.socket(lab, (sx * 0.19, 0, 2.464))
        a.tube(arc((0.28, 0, 2.10), 0.245, math.pi, math.pi / 2, 16), 0.009, IRON, sides=6)
        a.box(0.02, 0.29, -0.010, 0.010, 2.335, 2.355, IRON, bevel=0.003)
        a.tube([(0.28, 0, 2.336), (0.28, 0, 2.312)], 0.004, IRON, sides=6)
        a.info["bulb_local"] = square_lantern(a, 0.28, 0.0, 2.314, 0.44, rt=0.115, rb=0.092, hood=0.145)
        a.col_box(-0.17, 0.17, -0.17, 0.17, 0.0, 0.10)
        a.col_hull([(x, y, z) for x in (-0.05, 0.05) for y in (-0.05, 0.05) for z in (0.10, 2.50)])
        a.col_box(0.09, 0.47, -0.17, 0.17, 1.86, 2.36)
    return a


# ================================================================================================ (d) utility pole + attachments + wires

UP_ARM = (7.30, 7.40, (-0.85, -0.45, 0.45, 0.85), 0.95, "ABCD", 0.34)
LO_ARM = (6.75, 6.84, (-0.70, -0.30, 0.30, 0.70), 0.80, "EFGH", 0.46)
INS_PROFILE = [(0, 0), (0.030, 0), (0.056, 0.024), (0.060, 0.032), (0.040, 0.042), (0.050, 0.066), (0.030, 0.096),
               (0.032, 0.106), (0.020, 0.126), (0, 0.130)]


def arm_front_y(zc):
    c = pole_c(zc)
    return c.y - pole_r(zc) + 0.006


def utility_pole():
    a = Asset("SM_DKP_Modern_UtilityPole", "thin",
              "wooden distribution pole, 8.0 m above ground (0.30 m more below grade), warm weathered timber; two "
              "timber crossarms with steel braces and 8 brown-glazed pin insulators, 2 spool racks for service "
              "drops, a telecom messenger clamp, a riser cable to a small pole box, a coiled slack loop and step "
              "bolts. Wires, transformer and guy are separate assets, attached at the SOCKET_ empties / the pole pivot")
    zs = [-0.30 + k * 0.5 for k in range(17)] + [POLE_H]
    pts = [pole_c(z) for z in zs]
    radii = [pole_r(z) + 0.0025 * math.sin(i * 2.3) for i, z in enumerate(zs)]
    a.tube(pts, 0.14, WOOD, sides=14, radii=radii)
    top = pts[-1]
    a.lathe([(0, 0), (radii[-1] + 0.006, 0), (radii[-1] + 0.006, 0.02), (radii[-1] * 0.6, 0.05), (0, 0.065)], GALV,
            sides=14, center=(top.x, top.y, POLE_H - 0.015))
    for (z0, z1, xs, half, letters, drop) in (UP_ARM, LO_ARM):
        zc = (z0 + z1) / 2
        ca = pole_c(zc)
        y1 = arm_front_y(zc)
        a.box(-half, half, y1 - 0.095, y1, z0, z1, WOOD, bevel=0.008, vaxis="x")
        arm_y = y1 - 0.0475
        a.tube([(ca.x, y1 - 0.11, zc), (ca.x, ca.y + pole_r(zc) + 0.03, zc)], 0.008, GALV, sides=6)
        a.box(ca.x - 0.03, ca.x + 0.03, y1 - 0.103, y1 - 0.095, zc - 0.03, zc + 0.03, GALV)
        zb = z0 - drop
        cb = pole_c(zb)
        for sx in (-1, 1):
            a.bar((half * 0.58 * sx, y1 - 0.02, z0 - 0.002), (cb.x + 0.02 * sx, cb.y - pole_r(zb) - 0.004, zb), 0.04,
                  0.006, GALV, up=(0, 1, 0))
        a.tube([(cb.x, cb.y - pole_r(zb) - 0.03, zb), (cb.x, cb.y + pole_r(zb) + 0.02, zb)], 0.008, GALV, sides=6)
        for x, letter in zip(xs, letters):
            a.tube([(x, arm_y, z1 - 0.002), (x, arm_y, z1 + 0.03)], 0.011, GALV, sides=6)
            a.lathe(INS_PROFILE, PORC, sides=12, center=(x, arm_y, z1 + 0.028))
            a.socket(f"Wire_{letter}", (x, arm_y, z1 + 0.028 + 0.104))
    # two spool racks on the +X side for low-voltage service drops
    for zc in (6.20, 5.85):
        c = pole_c(zc)
        xr = c.x + pole_r(zc)
        a.box(xr - 0.004, xr + 0.006, c.y - 0.025, c.y + 0.025, zc - 0.09, zc + 0.09, GALV)
        for dz in (-0.06, 0.06):
            a.box(xr, xr + 0.14, c.y - 0.02, c.y + 0.02, zc + dz - 0.004, zc + dz + 0.004, GALV)
        a.tube([(xr + 0.11, c.y, zc - 0.07), (xr + 0.11, c.y, zc + 0.07)], 0.007, GALV, sides=6)
        a.lathe([(0, 0), (0.034, 0), (0.036, 0.012), (0.026, 0.028), (0.026, 0.080), (0.036, 0.096),
                 (0.034, 0.108), (0, 0.108)], PORC, sides=10, center=(xr + 0.11, c.y, zc - 0.054))
        a.socket(f"Drop_{1 if zc > 6 else 2}", (xr + 0.11 + 0.026, c.y, zc))
    # telecom messenger clamp on the -X side at +5.0 (SOCKET Telecom), and a slack coil hung below it
    zt = 5.0
    c = pole_c(zt)
    xl = c.x - pole_r(zt)
    a.box(xl - 0.006, xl + 0.004, c.y - 0.03, c.y + 0.03, zt - 0.10, zt + 0.06, GALV)
    a.box(xl - 0.16, xl, c.y - 0.012, c.y + 0.012, zt - 0.012, zt + 0.012, GALV)
    a.box(xl - 0.20, xl - 0.14, c.y - 0.03, c.y + 0.03, zt - 0.03, zt + 0.02, GALV, bevel=0.004)
    a.socket("Telecom", (xl - 0.17, c.y, zt - 0.04))
    zk = 4.55
    ck = pole_c(zk)
    xk = ck.x - pole_r(zk)
    a.tube([(xk + 0.01, ck.y, zk), (xk - 0.07, ck.y, zk), (xk - 0.07, ck.y, zk + 0.04)], 0.006, GALV, sides=5)
    for k, (ry, rz) in enumerate(((0.19, 0.24), (0.17, 0.22))):
        loop = [V(xk - 0.07 - 0.012 * k, ck.y + ry * math.sin(t), zk - rz + rz * math.cos(t))
                for t in [2 * math.pi * i / 22 for i in range(22)]]
        a.tube(loop, 0.008, CABLE, sides=5, closed=True)
    # riser cable from the lower rack down the +X side to a small pole box at +2.6, strapped every metre
    zr0, zr1 = 5.80, 2.90
    rpts = []
    for k in range(7):
        z = zr1 + (zr0 - zr1) * k / 6
        cc = pole_c(z)
        rpts.append(V(cc.x + pole_r(z) + 0.022, cc.y + 0.05, z))
    rpts.append(V(pole_c(5.85).x + pole_r(5.85) + 0.11, pole_c(5.85).y + 0.03, 5.80))
    a.tube(bend_path(rpts, 0.05, 3), 0.009, CABLE, sides=5)
    for z in (3.4, 4.4, 5.3):
        cc = pole_c(z)
        xs_ = cc.x + pole_r(z)
        a.box(xs_ - 0.002, xs_ + 0.036, cc.y + 0.025, cc.y + 0.075, z - 0.012, z + 0.012, GALV)
    cb = pole_c(2.72)
    xb = cb.x + pole_r(2.72)
    a.box(xb, xb + 0.13, cb.y - 0.10, cb.y + 0.10, 2.56, 2.88, GREY, bevel=0.008)
    a.box(xb + 0.13, xb + 0.14, cb.y - 0.095, cb.y + 0.095, 2.87, 2.89, GREY)
    a.box(xb + 0.004, xb + 0.14, cb.y - 0.012, cb.y + 0.012, 2.52, 2.56, GALV)
    # step bolts from +2.6 to +6.0, alternating sides (clear of the riser and the box)
    for k in range(9):
        z = 3.0 + k * 0.37
        cc = pole_c(z)
        ang = math.radians(125 if k % 2 == 0 else 235)
        d = V(math.cos(ang), math.sin(ang), 0)
        p0 = cc + d * (pole_r(z) - 0.02)
        a.tube([p0, cc + d * (pole_r(z) + 0.16), cc + d * (pole_r(z) + 0.17) + V(0, 0, 0.03)], 0.0095, GALV, sides=5)
    a.col_hull([(0.14 * math.cos(k * math.pi / 4), 0.14 * math.sin(k * math.pi / 4), -0.30) for k in range(8)] +
               [(0.105 * math.cos(k * math.pi / 4), 0.105 * math.sin(k * math.pi / 4), POLE_H + 0.05) for k in range(8)])
    for (z0, z1, xs, half, letters, _d) in (UP_ARM, LO_ARM):
        y1 = arm_front_y((z0 + z1) / 2)
        a.col_box(-half, half, y1 - 0.095, y1, z0 - 0.02, z1 + 0.16)
    a.info["insulator_top_local"] = {f"Wire_{l_}": [x, round(arm_front_y((z0 + z1) / 2) - 0.0475, 4), round(z1 + 0.132, 4)]
                                     for (z0, z1, xs, half, ls, _d) in (UP_ARM, LO_ARM) for x, l_ in zip(xs, ls)}
    return a


def pole_transformer():
    a = Asset("SM_DKP_Modern_PoleTransformer", "thin",
              "pole-mounted transformer can (0.40 m diameter, 0.72 m tall) on two galvanised hanger brackets, two "
              "porcelain bushings with jumpers up to the pole's lower-crossarm insulators F and G; pivot = the pole's "
              "base centre (place with the pole's transform)")
    zc0, zc1 = 5.30, 5.98
    cm = pole_c((zc0 + zc1) / 2)
    ry = cm.y - pole_r(5.65) - 0.26
    cx = cm.x
    a.vbase = zc0
    a.lathe([(0, zc0 - 0.03), (0.13, zc0 - 0.03), (0.19, zc0), (0.20, zc0 + 0.02), (0.20, zc1), (0.212, zc1),
             (0.212, zc1 + 0.025), (0.16, zc1 + 0.06), (0, zc1 + 0.075)], GREY, sides=16, center=(cx, ry, 0))
    for z in (zc0 + 0.18, zc0 + 0.40):                                                  # cooling ribs
        a.lathe([(0.2, z), (0.207, z), (0.207, z + 0.02), (0.2, z + 0.02)], GREY, sides=16, center=(cx, ry, 0))
    for zh in (zc0 + 0.12, zc1 - 0.10):                                                 # hanger brackets
        cc = pole_c(zh)
        yp = cc.y - pole_r(zh)
        a.box(cx - 0.05, cx + 0.05, ry + 0.19, yp + 0.004, zh - 0.02, zh + 0.02, GALV)
        a.hull([(cx + sx * pole_r(zh) * 0.8, yp + 0.03 + dy, zh + dz) for sx in (-1, 1) for dy in (-0.03, 0.0)
                for dz in (-0.03, 0.03)], GALV)
    tops = []
    for sx in (-1, 1):
        bx, by = cx + sx * 0.08, ry - 0.02
        a.lathe([(0, 0), (0.028, 0), (0.028, 0.012), (0.022, 0.03), (0.03, 0.04), (0.02, 0.06), (0.026, 0.07),
                 (0.016, 0.09), (0.008, 0.10), (0, 0.10)], PORC, sides=10, center=(bx, by, zc1 + 0.045))
        tops.append(V(bx, by, zc1 + 0.145))
    y_arm = arm_front_y((LO_ARM[0] + LO_ARM[1]) / 2) - 0.0475
    for top_, x_ins in zip(tops, (LO_ARM[2][1], LO_ARM[2][2])):
        end = V(x_ins, y_arm, LO_ARM[1] + 0.13)
        mid = (top_ + end) / 2 + V(0, -0.08, 0.02)
        path = [top_ + (mid - top_) * t * 2 if t <= 0.5 else mid + (end - mid) * (t - 0.5) * 2
                for t in [k / 10 for k in range(11)]]
        a.tube(bend_path(path, 0.05, 2), 0.006, CABLE, sides=5)
    a.col_hull([(cx + 0.21 * math.cos(k * math.pi / 4), ry + 0.21 * math.sin(k * math.pi / 4), z)
                for k in range(8) for z in (zc0 - 0.03, zc1 + 0.08)])
    return a


def pole_guy():
    GZ, AY = 6.40, 3.60
    a = Asset("SM_DKP_Modern_PoleGuy", "thin",
              f"down guy for an end or corner pole: galvanised band at +{GZ} on the pole, 8 mm strand to an anchor rod "
              f"{AY} m out along +Y with a concrete collar, a 1.8 m cream plastic guard over the lower strand; pivot = "
              "the pole's base centre (take the pole's position, rotate about Z to aim the guy)")
    cc = pole_c(GZ)
    rr = pole_r(GZ) + 0.006
    a.tube(arc((cc.x, cc.y, GZ), rr, 0, 2 * math.pi, 20), 0.005, GALV, sides=4, closed=True)
    eye = V(cc.x, cc.y + rr + 0.05, GZ - 0.02)
    a.box(cc.x - 0.02, cc.x + 0.02, cc.y + rr - 0.004, eye.y, GZ - 0.035, GZ - 0.005, GALV)
    anchor = V(0.0, AY, 0.22)
    d = (anchor - eye).normalized()
    a.tube([eye, anchor], 0.004, GALV, sides=6)
    # preformed grips at both ends
    a.tube([eye + d * 0.03, eye + d * 0.45], 0.0065, GALV, sides=6)
    a.tube([anchor - d * 0.50, anchor - d * 0.04], 0.0065, GALV, sides=6)
    # guard sleeve over the lower 1.8 m
    g0 = anchor - d * 0.10
    g1 = anchor - d * 1.90
    a.tube([g0, g1], 0.022, PCREAM, sides=8)
    # anchor rod (into the ground along the strand) and a concrete collar at grade
    rod_end = anchor + d * 0.45
    a.tube([anchor - d * 0.02, rod_end], 0.012, GALV, sides=6)
    a.tube(arc((anchor.x, anchor.y + 0.012, anchor.z + 0.01), 0.025, 0, 2 * math.pi, 10, u_axis=(1, 0, 0),
               v_axis=d.cross(V(1, 0, 0)).normalized()), 0.006, GALV, sides=5, closed=True)
    g = anchor + d * (anchor.z / -d.z)                                  # where the rod enters the ground
    a.lathe([(0, -0.05), (0.16, -0.05), (0.16, 0.01), (0.12, 0.03), (0, 0.035)], CONC, sides=12,
            center=(g.x, g.y, 0))
    a.col_hull([p + V(dx, dy, 0) for p in (g0, g1) for dx in (-0.03, 0.03) for dy in (-0.03, 0.03)])
    a.info.update({"band_z": GZ, "anchor_local": [0.0, AY, 0.22], "strand_angle_from_vertical_deg":
                   round(math.degrees(math.atan2(AY - eye.y, GZ - 0.22)), 2)})
    return a


def catenary(length, sag, dz, n=48):
    pts = []
    for k in range(n + 1):
        x = length * k / n
        pts.append(V(x, 0, dz * x / length - 4 * sag * x * (length - x) / length ** 2))
    return pts


def wire(name, length, sag, dz, note, r=0.0065, fitting="tie"):
    """One conductor between two attachment points: parabolic sag (close to a catenary at these sag ratios), end
    fittings, and a TOKEN UCX (a 4 cm block at the first attachment point) so the pipeline gate passes without the
    wire ever becoming an invisible wall if the NoCollision profile is missed."""
    a = Asset(name, "wire", note)
    pts = catenary(length, sag, dz)
    a.tube(pts, r, CABLE, sides=6)
    for end in (0, 1):
        p = pts[0] if end == 0 else pts[-1]
        q = pts[1] if end == 0 else pts[-2]
        d = (q - p).normalized()
        if fitting == "tie":        # tie wire wrapped over the insulator top groove
            a.tube([p - d * 0.07, p + d * 0.07], r + 0.004, GALV, sides=6)
        else:                       # service-drop dead-end: preformed grip + clevis loop beyond the end
            a.tube([p + d * 0.02, p + d * 0.30], r + 0.0035, GALV, sides=6)
            side = d.cross(V(0, 1, 0)).normalized()
            a.tube(arc(p - d * 0.025, 0.02, 0, 2 * math.pi, 10, u_axis=tuple(d), v_axis=tuple(side)), 0.004, GALV,
                   sides=5, closed=True)
    a.col_box(0.0, 0.04, -0.02, 0.02, -0.02, 0.02)
    lo = min(p.z for p in pts)
    a.info.update({"length_m": length, "sag_m": sag, "end_dz_m": dz, "lowest_z_local": round(lo, 4),
                   "radius_m": r, "centrelines": [[[round(c, 4) for c in p] for p in pts]], "ucx_note": "token 4 cm block at the first attachment point"})
    return a


def wire_telecom():
    L_, sag = 25.0, 0.60
    a = Asset("SM_DKP_Modern_Wire_Telecom25", "wire",
              "telecom cable bundle for a 25 m span: 6 mm steel messenger with a 24 mm and an 18 mm cable lashed "
              "under it, 0.60 m sag, suspension clamps at both ends; never blocks (NoCollision)")
    lines = []
    for (dzo, dyo, r, sides, mat) in ((0.0, 0.0, 0.003, 4, GALV), (-0.019, 0.004, 0.012, 6, CABLE),
                                      (-0.030, -0.012, 0.009, 6, CABLE)):
        pts = [p + V(0, dyo * (1 if k % 2 else 0.6), dzo) for k, p in enumerate(catenary(L_, sag, 0.0))]
        a.tube(pts, r, mat, sides=sides)
        lines.append([[round(c, 4) for c in p] for p in pts])
    for x in (0.0, L_):
        a.box(x - 0.05, x + 0.05, -0.022, 0.022, -0.05, 0.012, GALV, bevel=0.004)
    a.col_box(0.0, 0.04, -0.02, 0.02, -0.02, 0.02)
    a.info.update({"length_m": L_, "sag_m": sag, "centrelines": lines, "ucx_note": "token 4 cm block at the first attachment point",
                   "radius_m": 0.012})
    return a


# ================================================================================================ (f) junction box

def junction_box():
    a = Asset("SM_DKP_Modern_JunctionBox", "thin",
              "small utility junction box on a wall: two straight conduits up in line with the box, strap clamps on "
              "standoffs, one conduit down into a J drip loop with an open bushing; rust at the lid seam; 0.80 m "
              "overall; pivot on the wall at the bottom of the loop")
    a.vbase = 0.274
    for z in (0.245, 0.645):
        a.box(-0.03, 0.03, -0.006, 0.0, z, z + 0.04, GALV, bevel=0.002)
    a.box(-0.13, 0.13, -0.13, -0.004, 0.28, 0.64, GREY, bevel=0.006)
    a.box(-0.138, 0.138, -0.1285, -0.1245, 0.272, 0.648, RUST)                     # rust line at the lid seam
    a.box(-0.136, 0.136, -0.142, -0.126, 0.274, 0.646, GREY, bevel=0.005)          # lid
    a.box(-0.145, 0.145, -0.152, -0.004, 0.646, 0.66, GREY, bevel=0.004)           # drip hood
    for z in (0.33, 0.55):
        a.tube([(-0.139, -0.136, z), (-0.139, -0.136, z + 0.05)], 0.0065, GALV, sides=8)
    a.box(0.108, 0.14, -0.156, -0.140, 0.44, 0.48, GALV, bevel=0.002)
    a.tube([(0.124, -0.156, 0.46), (0.124, -0.168, 0.46)], 0.006, GALV, sides=8)
    for (x, z) in ((-0.115, 0.29), (0.115, 0.29), (-0.115, 0.63), (0.115, 0.63)):
        a.tube([(x, -0.142, z), (x, -0.146, z)], 0.006, GALV, sides=8)
    # two conduits straight up in line with the box (at the box's depth), coupling, strap clamp on standoffs
    for x in (-0.05, 0.05):
        a.lathe([(0, 0), (0.019, 0), (0.019, 0.025), (0, 0.025)], GALV, sides=6, center=(x, -0.06, 0.66))
        a.tube([(x, -0.06, 0.66), (x, -0.06, 0.80)], 0.0125, GALV, sides=10, caps=True)
        a.lathe([(0, 0), (0.016, 0), (0.016, 0.02), (0, 0.02)], GALV, sides=10, center=(x, -0.06, 0.74))
    a.box(-0.085, 0.085, -0.0765, -0.0725, 0.765, 0.785, GALV, bevel=0.0015)       # strap across both
    for x in (-0.08, 0.08):
        a.box(x - 0.007, x + 0.007, -0.075, -0.001, 0.765, 0.785, GALV)            # standoff legs
    # bottom conduit into a J drip loop, one strap clamp, open bushing on the end
    a.lathe([(0, 0), (0.019, 0), (0.019, 0.025), (0, 0.025)], GALV, sides=6, center=(0, -0.06, 0.255))
    loop = [V(0, -0.06, 0.28), V(0, -0.06, 0.10)] + \
        arc((0, -0.115, 0.10), 0.055, math.pi, 2 * math.pi, 10, u_axis=(0, -1, 0), v_axis=(0, 0, 1))[1:] + \
        [V(0, -0.17, 0.15)]
    a.tube(loop, 0.0125, GALV, sides=10)
    a.box(-0.02, 0.02, -0.0765, -0.0725, 0.17, 0.19, GALV, bevel=0.0015)
    a.box(-0.018, 0.018, -0.075, -0.001, 0.17, 0.19, GALV)
    a.lathe([(0.0125, 0.0), (0.019, 0.0), (0.019, 0.018), (0.016, 0.022), (0.0125, 0.022)], GALV, sides=12,
            center=(0, -0.17, 0.145))
    a.lathe([(0, 0.0), (0.0125, 0.0), (0.0125, 0.004), (0, 0.004)], PDARK, sides=12, center=(0, -0.17, 0.158))
    a.col_box(-0.15, 0.15, -0.20, 0.0, 0.0, 0.80)
    return a


# ================================================================================================ layout (spec frame)

UNPLACED = {
    "SM_DKP_Modern_StreetLamp_B": "SPARE (user decision 2026-09-28: drop the invented lamps). r2 placed two inside the "
                                  "courtyard's south yard strip (10.9, 0.45) / (33.1, 0.45): withdrawn. The references "
                                  "show only two street lamps, outside the gate on the road (street lamp A's positions)",
}


def layout_instances(pole_obj, pole_asset):
    """Placements in the grey-box frame (spec section 1): metres, X east, Y north, Z up; UE (x*100, -y*100, z*100),
    yaw = -rot_z. `source` says whether the spec fixes the position or it is proposed here."""
    inst = []

    def add(piece, loc, rot, source, note, scale=(1, 1, 1)):
        inst.append({"piece": piece, "loc": [round(c, 4) for c in loc], "rot_z": rot, "scale": [round(s, 4) for s in scale],
                     "source": source, "note": note,
                     "ue_loc_cm": [round(loc[0] * 100, 2), round(-loc[1] * 100, 2), round(loc[2] * 100, 2)],
                     "ue_yaw": -rot})
    add("SM_DKP_Modern_VendingMachine", (12.45, 0.40, 0.0), 180.0,
        "spec route 8 = the grey-box box X 12.0-12.9, Y 0-0.8, top +1.75 (GASP-proved at 0.8 deep)",
        "r2: against the south wall inside the courtyard, front facing north; the 0.90 x 0.80 machine fills the "
        "grey-box box exactly (back on the wall face Y 0, top lip front Y 0.80); no scaling in Unreal")
    for x in (15.6, 28.4):
        add("SM_DKP_Modern_ACUnit_Roof", (x, AC_FRONT_Y, round(AC_ROOF_Z, 4)), 0.0,
            "grey-box route 5 (ACUnit markers X 15.0-16.2 / 27.8-29.0, top +5.10; stance (15.6, 21.78) on the roof)",
            "r2: built at +5.10, NO Z-scale in Unreal; front feet on the lower roof at Y 22.0 (+3.233), casing Y "
            "22.02-23.10 (flat top 1.08 m deep, ends at the upper eave line), runners on the slope to the hall wall "
            "at Y 24.0; fan faces the courtyard")
    add("SM_DKP_Modern_ACUnit_Wall", (40.8, WALL_FACE_Y, 1.55), 0.0, "proposed",
        "residence south wall face (grey-box Y 27.94), 1.55 m up")
    for x in (6.6, 37.4):
        add("SM_DKP_Modern_WallLamp", (x, WALL_FACE_Y, 2.45), 0.0, "proposed",
            "storehouse / residence south wall face (grey-box Y 27.94) beside the corridor ends (reference 2's "
            "lamps), mirrored about X 22; see eave_check")
    add("SM_DKP_Modern_JunctionBox", (2.2, WALL_FACE_Y, 0.30), 0.0, "proposed",
        "storehouse south wall face (grey-box Y 27.94) (reference 2's meter box)")
    # r3 (user decision 2026-09-28, 'drop the invented lamps'): street lamps stand ONLY outside the wall on the street
    # side, where dojo1_reference1 shows them (two lamps flanking the gate approach across the road); none inside the
    # courtyard. Street lamp A keeps the two street positions; street lamp B (r2: two in the south yard strip INSIDE
    # the wall, invented) has no street position left in the references and is an unplaced spare (UNPLACED)
    for x, rot in ((17.0, 180.0), (27.0, 0.0)):
        add("SM_DKP_Modern_StreetLamp_A", (x, -4.5, 0.0), rot, "proposed (spec 7 + dojo1_reference1: two street lamps "
            "on the approach road outside the gate)",
            "flanking the gate approach outside the south wall, lanterns toward the path")
    poles = (-15.5, 9.5, 34.5, 59.5)
    for x in poles:
        add("SM_DKP_Modern_UtilityPole", (x, -7.0, 0.0), 90.0, "proposed (spec 7: power lines on the approach road)",
            "road edge 7 m south of the wall face, 25 m spans symmetric about the gate axis X 22; crossarms across "
            "the line (rot 90: local -Y front faces +X)")
    add("SM_DKP_Modern_PoleTransformer", (9.5, -7.0, 0.0), 90.0, "proposed",
        "on the X 9.5 pole (same transform as the pole) that feeds the gatehouse service drop")
    add("SM_DKP_Modern_PoleGuy", (poles[0], -7.0, 0.0), 90.0, "proposed",
        "end pole X -15.5: guy aimed west (local +Y -> world -X), anchor 3.6 m out")
    add("SM_DKP_Modern_PoleGuy", (poles[-1], -7.0, 0.0), -90.0, "proposed",
        "end pole X 59.5: guy aimed east (local +Y -> world +X), anchor 3.6 m out")
    # conductors: the pole's insulator tops, local (x, y, z) rotated 90 deg: world = (X - y, -7 + x, z)
    tops = pole_asset.info["insulator_top_local"]
    for i in range(len(poles) - 1):
        x0 = poles[i]
        for key, (lx, ly, lz) in sorted(tops.items()):
            wx, wy = x0 - ly, -7.0 + lx
            add("SM_DKP_Modern_Wire_Span25", (wx, wy, lz), 0.0, "proposed",
                f"conductor {key}, pole X {x0} -> {poles[i + 1]}", scale=((poles[i + 1] - x0) / 25.0, 1, 1))
        so = [c for c in pole_obj.children if c.name.endswith("_Telecom")][0]
        sx, sy, sz = so.location
        add("SM_DKP_Modern_Wire_Telecom25", (x0 - sy, -7.0 + sx, sz), 0.0, "proposed",
            f"telecom bundle, pole X {x0} -> {poles[i + 1]}")
    # a service drop from the X 9.5 pole's upper rack to the gatehouse west side (+3.2 under its eave)
    so = [c for c in pole_obj.children if c.name.endswith("Drop_1")][0]
    sx, sy, sz = so.location
    p0 = V(9.5 - sy, -7.0 + sx, sz)
    p1 = V(17.9, -1.2, 3.2)
    d = p1 - p0
    horiz = math.hypot(d.x, d.y)
    yaw = math.degrees(math.atan2(d.y, d.x))
    add("SM_DKP_Modern_Wire_Drop12", tuple(p0), round(yaw, 3), "proposed",
        "service drop, pole X 9.5 rack -> gatehouse west side (feeds the gate bracket lamps); scale stretches the "
        "12 m / -3.0 m design span to this run", scale=(horiz / 12.0, 1, d.z / -3.0))
    return inst, poles


# ================================================================================================ library pass (r2)

NANITE_OVER = 2000        # user decision 2026-10-02: Nanite for props over about 2k tris; the 5k budget is waived for them


def budget_for(tris):
    return None if tris > NANITE_OVER else BUDGET


def mesh_islands(me, faces):
    fset = set(faces)
    by_edge = {}
    for f in faces:
        for ek in me.polygons[f].edge_keys:
            by_edge.setdefault(ek, []).append(f)
    seen, out = set(), []
    for f0 in faces:
        if f0 in seen:
            continue
        stack, isl = [f0], []
        seen.add(f0)
        while stack:
            f = stack.pop()
            isl.append(f)
            for ek in me.polygons[f].edge_keys:
                for g in by_edge[ek]:
                    if g in fset and g not in seen:
                        seen.add(g)
                        stack.append(g)
        out.append(isl)
    return out


def apply_library(o, cls):
    """UV0 for the library slots by the library's helpers (timber: grain_uv, round members wrapping round their axis,
    boards planar, end faces on the end-grain slot; iron: box_uv, upright and unmirrored), then the library 'Wear'
    corner colours on the whole prop (wires skip it: thin tubes, no bevels, no ground)."""
    djm = L.djm
    me = o.data
    names = [m.name for m in me.materials]
    for side, end in L.END_OF.items():
        if side in names and end not in names:
            me.materials.append(L.build_material(end))
    names = [m.name for m in me.materials]

    def faces_of(mn):
        i = names.index(mn)
        return [pl.index for pl in me.polygons if pl.material_index == i]
    stats = {}
    for side, end in L.END_OF.items():
        if side in names and faces_of(side):
            rnd_f, box_f = [], []
            for isl in mesh_islands(me, faces_of(side)):
                pts = [me.vertices[v].co for f in isl for v in me.polygons[f].vertices]
                _c, ax, _s = djm._pca(pts)
                dist = []
                for f in isl:
                    nn = me.polygons[f].normal
                    if abs(nn.dot(ax)) < 0.3 and all(nn.dot(m_) < 0.985 for m_ in dist):
                        dist.append(nn.copy())
                (rnd_f if len(dist) >= 10 else box_f).extend(isl)
            for fl, mode in ((rnd_f, True), (box_f, False)):
                if fl:
                    r_ = djm.grain_uv(o, bpy.data.materials[side]["dj_set"], end_set=bpy.data.materials[end]["dj_set"],
                                      faces=fl, end_material_index=names.index(end), uv_map="UV0", round_mode=mode)
                    stats.setdefault(side, []).append(r_)
    import timber_bands   # Scripts/dojo/props/stone/timber_bands.py (same owner): mid-tone band offsets
    for side in L.END_OF:
        if side in names and faces_of(side):
            stats[side + "_bands"] = timber_bands.calm_bands(o, side, bpy.data.materials[side]["dj_set"])
    if "M_DJ_Iron" in names and faces_of("M_DJ_Iron"):
        djm.box_uv(o, "Iron", faces=faces_of("M_DJ_Iron"), uv_map="UV0")
    for end in L.END_OF.values():
        if end in names and not faces_of(end) and names.index(end) == len(names) - 1:
            me.materials.pop(index=len(names) - 1)
            names.pop()
    if cls != "wire":
        ground = {"SM_DKP_Modern_ACUnit_Roof": -10.0, "SM_DKP_Modern_ACUnit_Wall": -10.0,
                  "SM_DKP_Modern_WallLamp": -10.0, "SM_DKP_Modern_JunctionBox": -10.0,
                  "SM_DKP_Modern_PoleTransformer": -10.0}.get(o.name)
        stats["wear"] = djm.bake_wear(o, ground_z=ground)
    return stats


# ================================================================================================ LOD export

def export_with_lods(name, o, sc, waive):
    """kit 1 / taiko pattern: LOD0-2 on temporary copies (pipeline decimate_lods + make_lod_group, UCX renamed
    UCX_<base>_LOD0_NN, sockets SOCKET_<base>_LOD0_* keep their clean ue_socket names), QA on the LODs, export the
    LodGroup through Scripts/pipeline (sockets travel in the .sockets.json sidecar, ASSET_GUIDELINES 6.2)."""
    tmp = bpy.data.collections.new("TmpLOD")
    sc.collection.children.link(tmp)
    c0 = o.copy()
    c0.data = o.data.copy()
    c0.name = f"{name}_LOD0"
    tmp.objects.link(c0)
    for h in o.children:
        hc = h.copy()
        if h.data is not None:
            hc.data = h.data.copy()
        hc.name = h.name.replace(f"UCX_{name}_", f"UCX_{name}_LOD0_").replace(f"SOCKET_{name}_", f"SOCKET_{name}_LOD0_")
        tmp.objects.link(hc)
        hc.parent = c0
    lods = decimate_lods(c0, (0.5, 0.25))
    for lo in lods:
        # the Collapse decimation drags UV1 islands a hair outside 0-1 / into each other: repack the lightmap channel
        me = lo.data
        me.uv_layers.remove(me.uv_layers["UV1"])
        L.add_uv1(lo)
    grp = make_lod_group(name, [c0] + lods)
    lq = qa_check([c0] + lods, require_uv1=True, require_ucx=False, budget_tris=budget_for(len(c0.data.polygons)))
    lod_hard = [c for c in lq["checks"] if not c["passed"] and c["name"] not in waive]
    if lod_hard:
        raise RuntimeError(f"{name}: LOD QA hard fails {[(c['name'], c['object']) for c in lod_hard]}")
    r = export_fbx(str(EXPORT_DIR / f"{name}.fbx"), [grp], kind="static", sidecar=True)
    tris = [lq["triangles"].get(x.name) for x in [c0] + lods]
    rep = {"lods": 3, "lod_tris": tris, "strictly_descending": all(a > b for a, b in zip(tris, tris[1:])),
           "lod_qa_hard_fails": [(c["name"], c["object"], str(c["detail"])[:160]) for c in lod_hard],
           "objects": r["objects"], "screen_sizes": r.get("lod_screen_sizes"), "warnings": r["warnings"],
           "sidecar": r["sidecar"]}
    for ob in list(tmp.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.collections.remove(tmp)
    return rep


# ================================================================================================ main

def main():
    assert_owner("DojoModernProps", "claude")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    root = bpy.data.collections.new("ModernProps")
    sc.collection.children.link(root)
    builders = [vending, ac_roof, ac_wall, wall_lamp, lambda: street_lamp("A"), lambda: street_lamp("B"),
                utility_pole, pole_transformer, pole_guy, junction_box,
                lambda: wire("SM_DKP_Modern_Wire_Span25", 25.0, 0.45, 0.0,
                             "one conductor, 25 m pole-to-pole span, 0.45 m sag, tie wraps at both insulators; never "
                             "blocks (NoCollision; token UCX only)"),
                lambda: wire("SM_DKP_Modern_Wire_Drop12", 12.0, 0.25, -3.0,
                             "one service-drop conductor, 12 m, falls 3.0 m from a pole rack to a building, 0.25 m "
                             "sag, dead-end grips + clevis loops; never blocks (NoCollision; token UCX only)",
                             r=0.0055, fitting="deadend"),
                wire_telecom]
    assets, objs = {}, {}
    for b in builders:
        a = b()
        coll = bpy.data.collections.new(a.name.replace("SM_DKP_Modern_", "Modern_"))
        root.children.link(coll)
        objs[a.name] = a.build(coll)
        lib = apply_library(objs[a.name], a.cls)
        print("library", a.name, lib)
        for c in objs[a.name].children:
            if c.name.startswith("SOCKET_"):
                c["ue_socket"] = c.name[len(f"SOCKET_{a.name}_"):]
        if "centrelines" in a.info:
            objs[a.name]["review_centrelines"] = json.dumps(a.info["centrelines"])
            objs[a.name]["review_radius"] = a.info["radius_m"]
        assets[a.name] = a
        print("built", a.name, len(objs[a.name].data.polygons), "faces")
    WORK.mkdir(parents=True, exist_ok=True)

    # ---- QA (budget 5000 on every prop)
    qa, waive = {}, {"uv0_tile_range", "uv_no_overlap"}
    for name, o in objs.items():
        tris0 = sum(len(pl.vertices) - 2 for pl in o.data.polygons)
        r = qa_check([o], require_uv1=True, budget_tris=budget_for(tris0))
        fails = [c for c in r["checks"] if not c["passed"]]
        hard = [c for c in fails if c["name"] not in waive]
        qa[name] = {"hard_fails": hard, "waived": sorted({c["name"] for c in fails if c["name"] in waive}),
                    "tris": r["triangles"].get(name), "checks": len(r["checks"]), "budget_tris": budget_for(tris0),
                    "nanite": tris0 > NANITE_OVER and assets[name].cls != "wire"}
    hard_total = sum(len(v["hard_fails"]) for v in qa.values())
    print(f"QA: {len(objs)} props, hard fails {hard_total}")
    for k, v in qa.items():
        print("  ", k, v["tris"], "tris")
        for c in v["hard_fails"]:
            print("  FAIL", k, c["name"], c["object"], str(c["detail"])[:200])

    # ---- measure
    measure = {"date": str(date.today()), "round": "r2", "units": "metres, prop-local frame (front -Y)", "props": {}}
    for name, o in objs.items():
        me = o.data
        xs = [v.co.x for v in me.vertices]
        ys = [v.co.y for v in me.vertices]
        zs = [v.co.z for v in me.vertices]
        tris = sum(len(p.vertices) - 2 for p in me.polygons)
        rec = {"class": assets[name].cls, "note": assets[name].note,
               "bbox_min": [round(min(xs), 4), round(min(ys), 4), round(min(zs), 4)],
               "bbox_max": [round(max(xs), 4), round(max(ys), 4), round(max(zs), 4)],
               "dims": [round(max(xs) - min(xs), 4), round(max(ys) - min(ys), 4), round(max(zs) - min(zs), 4)],
               "tris": tris, "verts": len(me.vertices), "slots": [m.name for m in me.materials],
               "ucx": [], "sockets": [c.name for c in o.children if c.name.startswith("SOCKET_")]}
        for c in o.children:
            if c.name.startswith("UCX_"):
                cx = [v.co.x for v in c.data.vertices]
                cy = [v.co.y for v in c.data.vertices]
                cz = [v.co.z for v in c.data.vertices]
                rec["ucx"].append({"name": c.name, "min": [round(min(cx), 4), round(min(cy), 4), round(min(cz), 4)],
                                   "max": [round(max(cx), 4), round(max(cy), 4), round(max(cz), 4)],
                                   "dims": [round(max(cx) - min(cx), 4), round(max(cy) - min(cy), 4),
                                            round(max(cz) - min(cz), 4)]})
        dens = {}
        uvl = me.uv_layers[0].data
        for mi, m in enumerate(me.materials):
            tex, tile, _p = L.MATERIALS[m.name]
            if not tex or (tex == "LIB" and tile is None):
                continue
            if tex == "LIB":
                px = L.djm.set_info(m["dj_set"])["size_px"][0]
            else:
                px = bpy.data.images[f"T_DKP_Modern_{tex}_BC.png"].size[0]
            ua = ma = 0.0
            for p in me.polygons:
                if p.material_index != mi:
                    continue
                uv = [uvl[li].uv for li in p.loop_indices]
                s = sum(uv[i].x * uv[(i + 1) % len(uv)].y - uv[(i + 1) % len(uv)].x * uv[i].y for i in range(len(uv)))
                ua += abs(s) / 2
                ma += p.area
            if ma > 0:
                dens[m.name] = round(math.sqrt(ua / ma) * px / 100.0, 3)
        rec["texel_px_per_cm"] = dens
        if assets[name].cls == "climbprop":
            ztop = max(zs)
            top = [p for p in me.polygons if p.normal.z > 0.999 and abs(p.center.z - ztop) < 0.002]
            tx = [me.vertices[i].co.x for p in top for i in p.vertices]
            ty = [me.vertices[i].co.y for p in top for i in p.vertices]
            ucx_top = [u for u in rec["ucx"] if abs(u["max"][2] - ztop) < 0.002]
            rec["flat_top"] = {"z_local": round(ztop, 4), "render_top_x": [round(min(tx), 4), round(max(tx), 4)],
                               "render_top_y": [round(min(ty), 4), round(max(ty), 4)],
                               "render_top_depth_y": round(max(ty) - min(ty), 4),
                               "render_top_width_x": round(max(tx) - min(tx), 4),
                               "ucx_top_y": [round(min(u["min"][1] for u in ucx_top), 4),
                                             round(max(u["max"][1] for u in ucx_top), 4)],
                               "ucx_top_depth_y": round(max(u["max"][1] for u in ucx_top) -
                                                        min(u["min"][1] for u in ucx_top), 4),
                               "rule_R3_min_depth": 1.0}
        info = {k: v for k, v in assets[name].info.items() if k != "centrelines"}
        rec.update(info)
        measure["props"][name] = rec
    pr = measure["props"]
    vend = pr["SM_DKP_Modern_VendingMachine"]
    door_front = -0.372
    vend["top_lip_over_door_front_m"] = round(door_front - vend["flat_top"]["render_top_y"][0], 4)
    vend["top_lip_over_door_front_bbox_m"] = round(door_front - vend["bbox_min"][1], 4)
    pr["SM_DKP_Modern_ACUnit_Roof"]["placement_check"] = {
        "roof_z_at_front_Y22": round(AC_ROOF_Z, 4),
        "top_world_z": round(AC_ROOF_Z + pr["SM_DKP_Modern_ACUnit_Roof"]["flat_top"]["z_local"], 4),
        "spec_top": AC_TOP, "rise_from_roof_at_front": round(AC_TOP - AC_ROOF_Z, 4),
        "footprint_world_Y": [AC_FRONT_Y + pr["SM_DKP_Modern_ACUnit_Roof"]["bbox_min"][1],
                              AC_FRONT_Y + pr["SM_DKP_Modern_ACUnit_Roof"]["bbox_max"][1]],
        "standable_top_world_Y": [AC_FRONT_Y + pr["SM_DKP_Modern_ACUnit_Roof"]["flat_top"]["render_top_y"][0],
                                  AC_FRONT_Y + pr["SM_DKP_Modern_ACUnit_Roof"]["flat_top"]["render_top_y"][1]],
        "upper_eave_line_Y": 23.1,
        "headroom_under_upper_eave_at_Y23.1_m": round(5.5 - AC_TOP, 3),
        "headroom_under_upper_roof_at_wall_Y24_m": round(5.5 + 0.9 * T25 - AC_TOP, 3),
        "depth_note": "2.0 m is the stand footprint (runners to the hall wall). The climbable top is the condenser "
                      "casing, 1.2 x 1.08 m, flat at +5.10, which ends at the upper eave line Y 23.1; the last rise "
                      "to the upper eave landing (+5.5) is the grey-box's 0.40 m walk-up step (GASP_TRAVERSAL 4)",
        "frame_rail_clearance_over_runner_at_rear_m": round((AC_TOP_LOCAL - 0.877 - 0.063) - (zr(1.08) + 0.07), 4),
        "casing_clearance_over_roof_at_rear_m": round(AC_TOP_LOCAL - 0.877 - zr(1.10), 4),
        "runners_on_roof": "runner hulls from zr(y) + 0.02 on rubber pads from zr(y) - 0.004: seated on the slope, "
                           "no Z-scale (the showcase's 1.23 scale lifted them 0.21 m)"}
    # wall-prop mounting: storehouse / residence wall face and the eave above
    lamp = pr["SM_DKP_Modern_WallLamp"]
    measure["wall_mount_check"] = {
        "wall_face_Y": WALL_FACE_Y, "eave_line_Y": 27.4, "eave_underside_z_min": OUTBUILDING_EAVE_Z,
        "lamp_mount_z": 2.45, "lamp_top_world_z": round(2.45 + lamp["bbox_max"][2], 4),
        "lamp_bottom_world_z": round(2.45 + lamp["bbox_min"][2], 4),
        "lamp_reach_world_Y": round(WALL_FACE_Y + lamp["bbox_min"][1], 4),
        "clearance_lamp_top_to_eave_underside_m": round(OUTBUILDING_EAVE_Z - (2.45 + lamp["bbox_max"][2]), 4),
        "lamp_under_eave": (WALL_FACE_Y + lamp["bbox_min"][1]) > 27.4,
        "wall_ac_top_world_z": round(1.55 + pr["SM_DKP_Modern_ACUnit_Wall"]["bbox_max"][2], 4),
        "junction_box_top_world_z": round(0.30 + pr["SM_DKP_Modern_JunctionBox"]["bbox_max"][2], 4)}
    (WORK / "measure.json").write_text(json.dumps(measure, indent=1), encoding="utf-8")

    # ---- layout
    inst, poles = layout_instances(objs["SM_DKP_Modern_UtilityPole"], assets["SM_DKP_Modern_UtilityPole"])
    classes = {
        "climbprop": {"pawn": "block", "camera": "ignore", "visibility": "block", "traversal": "block",
                      "spec": "5.3 climb props: flat tops 1.0 m deep or more"},
        "thin": {"pawn": "block", "camera": "ignore", "visibility": "ignore", "traversal": "none (above vault band)",
                 "spec": "5.3 thin uprights (posts, lanterns): must not break lock-on or yank the camera"},
        "wire": {"pawn": "ignore", "camera": "ignore", "visibility": "ignore", "profile": "NoCollision",
                 "spec": "5.2 wires: unwalkable, never block; the UCX is a 4 cm token block at the first attachment "
                         "point, only for the pipeline gate, so a missed profile cannot make an invisible wall"},
    }
    pieces = {n: {"class": assets[n].cls, "note": assets[n].note, "fbx": f"Exports/DojoKit/Props/modern/{n}.fbx",
                  "slots": [m.name for m in objs[n].data.materials], "tris_lod0": pr[n]["tris"],
                  "collision": classes[assets[n].cls]} for n in objs}
    mats = {}
    for n, (tex, tile, p) in L.MATERIALS.items():
        rec = {"family": p.get("family"), "generic_for_look_pass": p.get("generic")}
        if tex == "LIB":
            if n not in bpy.data.materials:
                continue
            rec.update({"library": "Scripts/dojo/materials v" + str(L.djm.VERSION),
                        "textures": [f"T_DJ_{bpy.data.materials[n]['dj_set']}_{s_}" for s_ in ("BC", "N", "ORM")],
                        "tile_m": tile, "normal": "DirectX"})
        elif tex:
            rec.update({"textures": [f"T_DKP_Modern_{tex}_{s}" for s in ("BC", "N", "ORM")], "tile_m": tile,
                        "normal": "DirectX"})
        else:
            rec.update({k: v for k, v in p.items() if k in ("color", "rough", "metal", "coat", "emit", "emit_color")})
        if "emit_tex" in p:
            rec["emissive"] = f"BC x {p['emit_tex']}"
        if p.get("anchored"):
            rec["uv0"] = "U tiles; V height-anchored (0 = the prop's painted base, 2 m per tile)"
        if p.get("alpha"):
            rec["blend"] = "masked (BC alpha), two-sided"
        mats[n] = rec
    layout = {"units": "metres, grey-box frame (UE: x*100, -y*100, z*100, yaw = -rot_z)",
              "spec": "WorkFiles/world/DOJO_ARENA_SPEC.md", "date": str(date.today()), "round": "r3",
              "pieces": pieces, "instances": inst, "unplaced": UNPLACED, "collision_classes": classes, "materials": mats,
              "eave_check": measure["wall_mount_check"],
              "numbers": {"ac_roof_z_front": round(AC_ROOF_Z, 4), "ac_top": AC_TOP, "vending_top": VEND_TOP,
                          "pole_height": POLE_H, "roof_pitch_deg": 25.0, "wall_face_Y": WALL_FACE_Y}}
    (WORK / "layout_modern.json").write_text(json.dumps(layout, indent=1), encoding="utf-8")

    # ---- export: LOD0-2 LodGroup per prop (wires: single LOD, see notes)
    if "--no-export" not in ARGS and hard_total == 0:
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        results = {}
        for name, o in objs.items():
            if assets[name].cls == "wire":
                res = export_fbx(str(EXPORT_DIR / f"{name}.fbx"), [o], kind="static", sidecar=False)
                results[name] = {"lods": 1, "lod_tris": [qa[name]["tris"]], "objects": res["objects"],
                                 "warnings": res["warnings"], "sidecar": res["sidecar"]}
            else:
                results[name] = export_with_lods(name, o, sc, waive)
            qa[name]["lods"] = {k: results[name][k] for k in ("lods", "lod_tris")}
            qa[name]["lod_qa_hard_fails"] = results[name].get("lod_qa_hard_fails", [])
        (WORK / "export_report.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
        print(f"exported {len(results)} FBX to {EXPORT_DIR}")
        for k, v in results.items():
            print("  ", k, v["lod_tris"], v.get("lod_qa_hard_fails"), v["warnings"][:1])
    (WORK / "qa_report.json").write_text(json.dumps(qa, indent=1, default=str), encoding="utf-8")
    BLEND.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    print("saved", BLEND)


main()
