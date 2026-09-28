"""BlackCloak_MH_v2 stage 2: shared constants and helpers for the drape / assemble / render scripts (Blender 5.2).

Frame: the locked fitting body's world (metres, Z up, faces -Y, his RIGHT is -X).
Azimuth phi (degrees) is measured around the neck axis: 0 = front (-Y), +90 = his left (+X), -90 = his right (-X).
Pattern space: flat 2-D metres, polar (r, alpha) about the circle-cut centre; alpha (radians) increases CCW.
The mantle is one circle cut; pattern angle alpha maps to body azimuth phi(alpha) = PHI_EDGE - alpha / K_CONE
(K_CONE = 330/360: a 330-degree cut rolls into a 23.6-degree cone, so the start shape is the flat pattern rolled).
"""
import math
import os
import sys

ROOT = "C:/Users/Cody/Desktop/Blender_Projects"
SCRIPTS = ROOT + "/Scripts"
HERE = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

WORK_BLEND = ROOT + "/Assets/Garments/BlackCloak_MH_v2.blend"
WORK_DIR = ROOT + "/WorkFiles/BlackCloak_MH_v2/build"
EXPORT_DIR = ROOT + "/Exports/Garments/BlackCloak_MH_v2"
EXPORT_FBX = EXPORT_DIR + "/SK_BlackCloak_MH_v2.fbx"
TEX_DIR = EXPORT_DIR + "/Textures"
RENDER_DIR = ROOT + "/Renders/BlackCloak_MH_v2"
CLASP_BLEND = ROOT + "/WorkFiles/BlackCloak_MH_v2/surface/BlackCloakV2_Clasp.blend"
CLASP_OBJECT = "BlackCloakV2_Clasp"

# The drape / look pose (TARGET_SPEC 5; identical to v2m_common.ARMS_DOWN_V2): garment_qa pose ops.
ARMS_DOWN_V2 = [
    ("aim", "upperarm_l", "lowerarm_l", (0.16, 0.02, -1.0)), ("aim", "upperarm_r", "lowerarm_r", (-0.16, 0.02, -1.0)),
    ("aim", "lowerarm_l", "hand_l", (0.10, -0.22, -1.0)), ("aim", "lowerarm_r", "hand_r", (-0.10, -0.22, -1.0)),
]

# ---------------------------------------------------------------- UVs and materials
TILE_M = 0.45                 # one tile of the stage-1 slub maps
S_UV = 5.85                   # metres of pattern per UV0 unit (13 tiles exactly, so a +1 UV island shift keeps the slub phase)
UV_SCALE = S_UV / TILE_M      # 13.0: material UV scale for UV0
UV0 = "UVMap"
UV1 = "UV1_Fray"
FRAY_CARD_M = 0.056           # the fray strip texture covers 5.6 cm in V; V = 1 is the cloth side (row 0)
FRAY_EDGE_V = 1.0 - 0.004 / FRAY_CARD_M   # the geometric cut edge sits 4 mm into the opaque band
FRAY_BODY_V = 0.97            # every non-fringe vertex: opaque cloth
MAT_WOOL = "M_BlackCloakV2_Wool"
MAT_CLASP = "M_BlackCloakV2_Clasp"

# ---------------------------------------------------------------- pattern (mantle)
K_CONE = 0.62                 # r1: 330/360 flared into a stiff bell under the gate's cloth settings
PHI_EDGE = -58.0              # his right-front: the right panel's open edge at the neck
PHI_WRAP_START = 75.0         # his left-front: where the neck seam ends and the wrap's free top edge begins
PHI_CLASP = -64.0             # the wrap's front corner (gathered under the button)
CLASP_TARGET = (-0.185, 1.48)  # x, z of the button centre (TARGET_SPEC 3)
CLASP_DIAM = 0.056
SEAM_OFFSET = 0.004           # mantle neck edge sits this far outside the funnel wall
GATHER_LEN = 0.24             # length of the wrap top edge gathered into the button footprint
GATHER_RING_R = 0.024         # radius of the gather rosette under the button
GATHER_ARC_DEG = (45.0, -105.0)
WRAP_TOP_RISE = 0.34          # the wrap top edge spirals out by this much (pattern r) from the neck to the corner


PHI_YOKE_START = 55.0         # the skinned yoke covers the wrap from here across to the button


def smoothstep(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def interp_table(table, x, periodic=None):
    """Piecewise-linear table [(x, y), ...] (sorted), optional period for wrap-around (degrees)."""
    if periodic:
        x = (x - table[0][0]) % periodic + table[0][0]
        pts = list(table) + [(table[0][0] + periodic, table[0][1])]
    else:
        pts = table
        if x <= pts[0][0]:
            return pts[0][1]
        if x >= pts[-1][0]:
            return pts[-1][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            t = (x - x0) / max(x1 - x0, 1e-12)
            t = t * t * (3 - 2 * t)          # smooth between knots
            return y0 + (y1 - y0) * t
    return pts[-1][1]


def wrap180(a):
    return (a + 180.0) % 360.0 - 180.0


def fabric_length_from_top(phi):
    """Target fabric length from the top edge (neck seam / wrap top edge) to the hem, by body azimuth (metres)."""
    t = [(-180, 1.65), (-110, 1.71), (-85, 1.71), (-64, 1.66), (-52, 1.61), (-40, 1.60), (-15, 1.74), (0, 1.84),
         (35, 1.82), (65, 1.75), (90, 1.70), (140, 1.66)]
    return interp_table(t, wrap180(phi), periodic=360.0)
