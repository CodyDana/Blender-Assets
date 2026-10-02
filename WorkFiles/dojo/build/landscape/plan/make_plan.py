"""Dojo LANDSCAPE ROUND - plan stage generator (read-only for everything outside this folder).

Writes, next to this script:
  landscape_plan.json   - the layout plan in the LEVEL FRAME (layout_showcase.json frame: metres, x east, y north,
                          z up; Unreal = (x*100, -y*100, z*100) cm, UE yaw = -rot_z)
  landscape_plan_topdown.png - top-down plan image (near field + far field)
  ref_camera_check.png  - the reference beside a wire projection of the plan through CAM_LandscapeRef
Run: py -3 -B make_plan.py
"""
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = 'C:/Users/Cody/Desktop/Blender_Projects'
REF = REPO + '/References/Dojo/dojo_landscape_ref.png'
SHOWCASE = REPO + '/WorkFiles/dojo/build/showcase/layout_showcase.json'

# ----------------------------------------------------------------------------------------------------------------------
# 0. Existing level (read from layout_showcase.json, never written)
# ----------------------------------------------------------------------------------------------------------------------
show = json.load(open(SHOWCASE, encoding='utf-8'))


def ue(p):
    """level frame metres -> Unreal cm"""
    x, y = p[0], p[1]
    z = p[2] if len(p) > 2 else 0.0
    return [round(x * 100, 1), round(-y * 100, 1), round(z * 100, 1)]


COMPOUND = {'x': [-1.0, 45.0], 'y': [-1.0, 37.0], 'courtyard_z': 0.0, 'wall_top_z': 2.0,
            'gate_centre': [22.0, -1.0, 0.0], 'gate_paving_south_edge_y': -3.0,
            'hall': {'x': [10.95, 33.05], 'y': [21.5, 33.85], 'upper_ridge_z': 8.3},
            'note': 'unchanged: every gameplay number, collision, GASP marker and the 1v1 alley closure stay'}

# ----------------------------------------------------------------------------------------------------------------------
# 1. Terrace, forecourt and the ishigaki wall runs
# ----------------------------------------------------------------------------------------------------------------------
TERRACE = {
    'upper_terrace': {'z': 0.0, 'poly': [[-7.0, -3.0], [49.0, -3.0], [49.0, 44.0], [-7.0, 44.0]],
                      'strips': {'south_verge': 'y -1.0..-3.0 (x -7..49), the band in front of the south wall',
                                 'west_strip': 'x -7.0..-1.0 (y -3..44)',
                                 'east_strip': 'x 45.0..49.0 (y -3..44)',
                                 'north_strip': 'y 37.0..44.0 (x -7..49); the hillside rises north of y 44 (no wall)'},
                      'surface': 'landscape at z 0.00 (grass/moss layers) outside the compound; under the compound '
                                 'the landscape sits at z -0.30, hidden below the kit ground meshes'},
    'forecourt': {'z': -0.5, 'poly': [[12.0, -3.0], [34.0, -3.0], [34.0, -7.6], [12.0, -7.6]],
                  'north_edge': 'a 0.5 m dressed step course (SM_DKT_WallFoot_2m/4m, tops at z 0) along y -3.0 '
                                'except the gate stair x 20.2..23.8',
                  'surface': 'granite flags (SM_DKT_Stair_Landing_W180 / LandingSB_W180 tiled) or landscape '
                             'gravel-dirt layer; decide by the ref crop (ref: pale compacted path)'},
}
WALLS = [
    {'id': 'WR1_SW_verge', 'from': [4.0, -3.0], 'to': [12.0, -3.0], 'faces': '-y (south)', 'top_z': 0.0,
     'module_H': 'H2', 'foot_z': -2.0, 'length_m': 8.0,
     'modules': '2 x SM_DKT_Wall_4m_H2; EndL_H2 at x 4 buried into the west rock knoll (its top is +0.5..+2.5, so '
                'the verge meets rock west of x 4); at x 12 it becomes the north cheek of flight F1'},
    {'id': 'WR2_forecourt_front', 'from': [12.0, -7.6], 'to': [34.0, -7.6], 'faces': '-y (south)', 'top_z': -0.5,
     'module_H': 'H4', 'foot_z': -4.5, 'length_m': 22.0,
     'modules': '5 x Wall_4m_H4 + 1 x Wall_2m_H4; EndL_H4 at x 12 (stair F1/L1 side); CornerOut_H4 at (34,-7.6); '
                'the west half is buried ~1 m by the rock bank (foot visible from x ~24 east, boulders at the foot)'},
    {'id': 'WR3_forecourt_east', 'from': [34.0, -7.6], 'to': [34.0, -3.0], 'faces': '+x (east)', 'top_z': -0.5,
     'module_H': 'H4', 'foot_z': -4.5, 'length_m': 4.6,
     'modules': '1 x Wall_4m_H4 (+0.6 m taken by the corner); CornerIn at (34,-3.0) against WR4; the 0.5 m top step '
                'at (34,-3.0) closed with WallCoping_CornerIn + a WallFoot return'},
    {'id': 'WR4_SE_terrace', 'from': [34.0, -3.0], 'to': [49.0, -3.0], 'faces': '-y (south)', 'top_z': 0.0,
     'module_H': 'H6', 'foot_z': -6.0, 'length_m': 15.0,
     'modules': '3 x Wall_4m_H6 + 1 x Wall_2m_H6 + CornerOut_H6 at (49,-3.0); straight batter (the study default); '
                'the compound SE corner stands on it, the rapids and foot boulders below'},
    {'id': 'WR5_east_terrace', 'from': [49.0, -3.0], 'to': [49.0, 44.0], 'faces': '+x (east)', 'top_z': 0.0,
     'module_H': 'H6 (y -3..9) / H4 (y 9..29) / H3 (y 29..44)', 'foot_z': '-6.0 / -4.0 / -3.0', 'length_m': 47.0,
     'modules': '3 x Wall_4m_H6, 5 x Wall_4m_H4, 3 x Wall_4m_H3 + 1 x Wall_2m_H3, EndR_H3 at y 44 into the hill; the '
                'foot steps are hidden by the bank (bank crest 1-1.5 m above the water, rising upstream)'},
]

# ----------------------------------------------------------------------------------------------------------------------
# 2. Stair path (river bank -> gate).  Kit grid: riser 1/6 m, tread 1/3 m (1:2, 26.57 deg), W 1.8 m.
#    Flights are given as bottom/top points on the flight centre line; the build stage derives loc/rot from
#    kit_catalog.json how_to_chain (pieces are built walking UP along +Y).
# ----------------------------------------------------------------------------------------------------------------------
STAIR = [
    # gate stair: two W180 R050 flights side by side under the gate paving edge
    {'id': 'G1', 'piece': 'SM_DKT_Stair_Flight_W180_R050', 'bottom': [21.1, -4.0, -0.5], 'top': [21.1, -3.0, 0.0],
     'up': '+y', 'note': 'gate stair west half (3 risers)'},
    {'id': 'G2', 'piece': 'SM_DKT_Stair_Flight_W180_R050', 'bottom': [22.9, -4.0, -0.5], 'top': [22.9, -3.0, 0.0],
     'up': '+y', 'note': 'gate stair east half; outer cheeks SM_DKT_Stair_Cheek_R050 at x 20.0 / 24.0'},
    {'id': 'F1', 'piece': 'SM_DKT_Stair_Flight_W180_R100', 'bottom': [10.0, -6.5, -1.5], 'top': [12.0, -6.5, -0.5],
     'up': '+x', 'note': 'leaves the forecourt west end going down west (ref: first steps beside the forecourt wall)'},
    {'id': 'L1', 'piece': 'SM_DKT_Stair_LandingL_W180', 'centre': [9.1, -6.5, -1.5],
     'note': 'turn: arrive from the south (P1a), leave east (F1); timber lantern at its NW corner'},
    {'id': 'P1a', 'piece': 'SM_DKT_Stair_LandingSB_W180 (rot 90: 4.0 m level path section)', 'from': [9.1, -7.4, -1.5],
     'to': [9.1, -11.4, -1.5], 'note': 'cliff-foot path; the cliff face (C1) rises on the west, the bank drops east'},
    {'id': 'F2', 'piece': 'SM_DKT_Stair_Flight_W180_R050', 'bottom': [9.1, -12.4, -2.0], 'top': [9.1, -11.4, -1.5],
     'up': '+y'},
    {'id': 'L2', 'piece': 'SM_DKT_Stair_Landing_W180', 'centre': [9.1, -13.3, -2.0],
     'note': 'timber lantern on the river (east) side'},
    {'id': 'P1b', 'piece': 'SM_DKT_Stair_LandingSB_W180 x2 (rot 90: 8.0 m level path)', 'from': [9.1, -14.2, -2.0],
     'to': [9.1, -22.2, -2.0], 'note': 'paved path under the cliff (ref: the paved stretch between the lantern landing '
                                       'and the long flight); Rail_Flat on the east (drop) side'},
    {'id': 'L3', 'piece': 'SM_DKT_Stair_Landing_W180', 'centre': [9.1, -23.1, -2.0],
     'note': 'lantern landing at the head of the long flight (ref); stone lantern east'},
    {'id': 'F3', 'piece': 'SM_DKT_Stair_Flight_W180_R200', 'bottom': [9.1, -28.0, -4.0], 'top': [9.1, -24.0, -2.0],
     'up': '+y', 'note': 'the long flight (12 risers); Rail_Slope_R200 on the east (river) side; cliff face west'},
    {'id': 'L4', 'piece': 'SM_DKT_Stair_LandingL_W180', 'centre': [9.1, -28.9, -4.0],
     'note': 'turn: arrive from the west (P2), leave north (F3)'},
    {'id': 'P2', 'piece': 'SM_DKT_Stair_LandingSB_W180 (rot 0: 4.0 m level path along x)', 'centre': [6.2, -28.9, -4.0],
     'note': 'short paved traverse west; Rail_Flat_L180 x2 on the south side'},
    {'id': 'L5', 'piece': 'SM_DKT_Stair_LandingL_W180', 'centre': [3.3, -28.9, -4.0],
     'note': 'turn: arrive from the south (F4), leave east (P2)'},
    {'id': 'F4', 'piece': 'SM_DKT_Stair_Flight_W180_R200', 'bottom': [3.3, -33.8, -6.0], 'top': [3.3, -29.8, -4.0],
     'up': '+y', 'note': 'the foreground flight of the reference: rail on the river side, the tall cliff face west'},
    {'id': 'L6', 'piece': 'SM_DKT_Stair_Landing_W180', 'centre': [3.3, -34.7, -6.0],
     'note': 'timber lantern (east)'},
    {'id': 'F5', 'piece': 'SM_DKT_Stair_Flight_W180_R100', 'bottom': [3.3, -37.6, -7.0], 'top': [3.3, -35.6, -6.0],
     'up': '+y', 'note': 'rail east'},
    {'id': 'L7', 'piece': 'SM_DKT_Stair_Landing_W180 + Stair_Kerb_L180 on the open sides', 'centre': [3.3, -38.5, -7.0],
     'note': 'river landing, ~0.6 m over the water and ~10 m from it; stone lantern; the BR approach continues SW as '
             'a landscape dirt trail along the bank (P_lower_bank)'},
]
STAIR_TOTALS = {
    'rise_m': 7.0, 'risers': 42, 'riser_m': 0.1667, 'tread_m': 0.3333, 'pitch_deg': 26.57, 'width_m': 1.8,
    'flights': '7 + 2 side by side at the gate', 'landings_turns': 7, 'lanterns': 6, 'rails_m': 'about 34 m (P1b east 8 m, F3 east 4 m, P2 south 4 m, F4 both 8 m, F5 east 2 m, the forecourt '
                                         'stair head 3.6 m, posts at ends and corners)',
    'gasp': 'riser 0.167 < MaxStepHeight 0.45; 26.6 deg < walkable 44.77; width 1.8 > capsule 0.60; rails post '
            'tops 0.86 (vaultable, not a route blocker); P2 flags level; every landing >= 1.8 x 1.8',
}
LANTERNS = [
    {'piece': 'SM_DKT_Stair_Lantern_Timber', 'loc': [19.2, -4.6, -0.5], 'note': 'left of the gate stair (ref)'},
    {'piece': 'SM_DKT_Stair_Lantern_Timber', 'loc': [8.3, -5.6, -1.5], 'note': 'L1 NW corner'},
    {'piece': 'SM_DKT_Stair_Lantern_Timber', 'loc': [10.2, -12.6, -2.0], 'note': 'L2 river side'},
    {'piece': 'SM_DKT_Stair_Lantern_Stone', 'loc': [10.2, -22.4, -2.0], 'note': 'L3 (ref: lantern at the head of the '
                                                                             'long flight)'},
    {'piece': 'SM_DKT_Stair_Lantern_Timber', 'loc': [4.4, -34.0, -6.0], 'note': 'L6 river side'},
    {'piece': 'SM_DKT_Stair_Lantern_Stone', 'loc': [4.4, -39.2, -7.0], 'note': 'L7 river landing'},
]
LANTERN_RULE = 'one lantern per landing or turn, about every 2.5-3.5 m of rise (ref: 4 visible between the river and ' \
               'the gate); timber on the upper path, stone lower down; lights: the Stair_Lantern sockets, 2400-2700 K'

# ----------------------------------------------------------------------------------------------------------------------
# 3. River (Water plugin WaterBodyRiver spline, downstream order)
# ----------------------------------------------------------------------------------------------------------------------
RIVER = [
    # id, x, y, water z, width, zone
    ('R0', 300.0, 470.0, -1.0, 26.0, 'far upstream valley (visual)'),
    ('R1', 160.0, 230.0, -2.4, 22.0, 'upstream run'),
    ('R2', 88.0, 95.0, -3.6, 18.0, 'run'),
    ('R3', 66.0, 42.0, -4.3, 15.0, 'run beside the NE of the compound'),
    ('R4', 62.0, 14.0, -4.8, 14.0, 'riffle, first white water'),
    ('R5', 57.0, -12.0, -5.3, 15.0, 'RAPIDS (SE corner, foot boulders)'),
    ('R6', 37.0, -17.0, -6.2, 16.0, 'RAPIDS under the forecourt wall'),
    ('R7', 26.0, -30.0, -7.2, 16.0, 'RAPIDS end, tail-out beside the long flight'),
    ('R8', 17.0, -45.0, -7.9, 18.0, 'run past the river landing'),
    ('R9', 4.0, -64.0, -8.3, 19.0, 'pool under the reference camera'),
    ('R10', -30.0, -115.0, -9.0, 24.0, 'exits south-west (visual)'),
    ('R11', -100.0, -230.0, -9.8, 28.0, 'far downstream (visual)'),
]
RIVER_NOTES = {
    'body': 'one WaterBodyRiver (Water plugin, owner-approved) with Water_Material_River retuned turquoise-grey '
            '(ref: turquoise water, white foam); spline points = R0..R11, per-point width/depth/velocity',
    'depth_m': 'run 1.2, rapids 0.6-0.8 (boulders break the surface), pool 2.0',
    'velocity_cm_s': 'run 80-120, rapids 250-350, pool 40',
    'rapids': {'from': 'R4', 'to': 'R7', 'length_m': 61, 'drop_m': 2.4, 'grade_pct': 3.9,
               'white_water': 'foam in the water material (engine T_WaterFlow_01/03_Foam_Tiled 2K) driven by '
                              'velocity + boulder distance field; our river-mist Niagara (this round) at 3 points '
                              '+ spray bursts at 6 emergent boulders; NiagaraExamples BP_FogBankVolume (sparse volume '
                              'texture) or a Local Fog Volume as the low mist along R4..R8'},
    'banks': 'bank crest 0.6-1.5 m above the water; boulder shelves at the wall feet; river bed = MossyCreekStones',
}

# ----------------------------------------------------------------------------------------------------------------------
# 4. Zones (bank, slope, cliff, forest, ground cover)
# ----------------------------------------------------------------------------------------------------------------------
ZONES = [
    {'id': 'BF1_foot_boulders', 'kind': 'boulder field', 'poly': [[24, -7.6], [49, -3.0], [58, -6], [44, -12], [26, -12]],
     'content': '3 huge foot boulders 2-3 m against WR2 east half / WR4 + 6-8 river boulders 0.5-1.5 m + cobbles',
     'source': 'GAP (sourced rounded granite); interim Fishermans SM_Rocks_01..04 if the form check passes'},
    {'id': 'BF2_rapids_channel', 'kind': 'in-channel boulders', 'along': 'R4..R7', 'content':
        '14-18 boulders 0.5-1.5 m, 30-40 % emergent, elongated along the flow, sunk 15-35 %',
     'source': 'GAP (4-6 unique river boulders)'},
    {'id': 'BF3_west_bank', 'kind': 'mossy rock bank', 'poly': [[10.5, -8], [26, -10], [30, -24], [20, -44], [12, -40], [11, -24]],
     'content': 'the steep mossy bank between the stair and the rapids: 6-10 boulders 1-2.5 m, moss cushions, '
                'shrubs, PineD2 + CS08', 'source': 'boulders GAP; moss/grass/bush owned'},
    {'id': 'C1_west_cliff', 'kind': 'rocky cliff', 'poly': [[-14, -3], [4, -3], [7.9, -7], [7.9, -28], [1.7, -29.5],
                                                                [1.7, -37.5], [-6, -44], [-16, -40]],
     'content': "jointed granite outcrop (the reference's left cliff): east-facing face along the path at x ~7.9 "
                '(P1a-F3, 3.5-4.5 m tall) and x ~1.7 (F4-F5, ~5 m); top +2.5 at (-2,-12), +1.5 at (0,-24), -1.0 at '
                '(-2,-36); moss on ledges; PineD1 + CS09/CS10 on top',
     'source': 'GAP (3-4 jointed cliff chunks 2-8 m); landscape slope under them'},
    {'id': 'E1_far_bank', 'kind': 'bank + slope', 'poly': [[70, 45], [69, 15], [65, -20], [45, -27], [33, -38],
                                                          [27, -52], [45, -75], [100, -70], [92, 20], [100, 95],
                                                          [80, 60]],
     'content': 'boulder-edged far bank rising 3-20 m; cherry slot row CS13-CS18; bushes; firs behind (FZ3)'},
    {'id': 'P_lower_bank', 'kind': 'path bank', 'poly': [[1.7, -37], [12, -38], [13, -50], [-2, -60], [-8, -48]],
     'content': 'dirt-and-moss bank below L7, the BR dirt trail SW, cobbles at the water line'},
]
FORESTS = [
    {'id': 'FZ1_north_hill', 'poly': [[-40, 46], [95, 46], [130, 210], [-70, 210]],
     'species': 'Fishermans SM_Fir_Tree_01..08 (10.3-16.0 m; weights: 01-05 60 %, 06-08 40 % toward the back) + 5 '
                'Megaplants Japanese Cypress (Route B) as the front row at y 47-52 behind the hall',
     'density': '1 per 60 m2 at the edge -> 1 per 35 m2 beyond y 70; min spacing 5 m; keep-out 3 m from y 44',
     'placement': 'PCG Surface Sampler -> Self Pruning -> Static Mesh Spawner (ISM, Nanite, Voxelize); WPO off > 60 m'},
    {'id': 'FZ2_west_ridge', 'poly': [[-170, -80], [-16, -80], [-16, -2], [-14, 44], [-40, 46], [-170, 130]],
     'species': 'Fir 01..08', 'density': '1 per 50 m2; keep-out 4 m from the cliff top edge and the camera wedge'},
    {'id': 'FZ3_east_valley', 'poly': [[92, -80], [260, -70], [330, 320], [140, 270], [104, 95], [88, 20]],
     'species': 'Fir 01..08', 'density': '1 per 45 m2, thinning to 1 per 90 m2 near the far-bank cherries'},
    {'id': 'FZ4_mid_ridges', 'poly': 'landscape LS_Far, 0.5-2.5 km N/NE',
     'species': 'SMF_Fir_Tree_Billboard (Fishermans impostor) at 1 per 150 m2 + a forest-canopy landscape layer',
     'density': 'impostors to ~2.5 km; material only beyond'},
]
PINES = [
    # id, variant, loc, yaw, scale, note
    ('P01', 'PineA1', [26.0, -4.6, -0.5], 200, 1.10, 'forecourt, right of the gate stair (ref: small pine there)'),
    ('P02', 'PineC1', [10.8, -2.1, 0.0], 135, 1.00, 'verge at the stair head; long limb reaching SE over F1'),
    ('P03', 'PineD1', [6.2, -17.5, 1.8], 70, 1.15, 'on the west cliff edge above P1b (cliff pine on its boulder)'),
    ('P04', 'PineD2', [13.8, -30.5, -4.8], 250, 1.20, 'on the river-bank boulder east of L4 / the F3 foot'),
    ('P05', 'PineB1', [-4.5, 9.0, 0.0], 30, 1.20, 'west strip, over the SW wall'),
    ('P06', 'PineC2', [47.0, 3.0, 0.0], 290, 1.00, 'east strip, leaning out over WR5 toward the river'),
    ('P07', 'PineB2', [47.0, 24.0, 0.0], 160, 1.15, 'east strip'),
    ('P08', 'PineA2', [-3.5, 33.0, 0.0], 10, 1.25, 'west strip'),
    ('P09_opt', 'PineA1', [0.62, 21.0, 0.0], 90, 1.00, 'OPTIONAL inside W wall bed (gated: walk + climb re-run)'),
    ('P10_opt', 'PineA2', [43.38, 21.0, 0.0], 270, 1.00, 'OPTIONAL inside E wall bed (gated)'),
]
CHERRY = [
    # id, loc, height_m, canopy_m, collision, note
    ('CS01', [3.5, 16.0, 0.0], 7.0, 6.4, 'keep the grey-box trunk hull (0.5 m, hidden)', 'courtyard W (existing slot)'),
    ('CS02', [40.5, 16.0, 0.0], 7.0, 6.4, 'keep the grey-box trunk hull (0.5 m, hidden)', 'courtyard E (existing slot)'),
    ('CS03', [-4.0, 1.5, 0.0], 8.0, 8.0, 'none', 'west strip SW corner (ref: big cherry left of the compound)'),
    ('CS04', [-4.0, 22.0, 0.0], 7.0, 7.0, 'none', 'west strip'),
    ('CS05', [-3.5, 41.0, 0.0], 7.0, 7.0, 'none', 'NW corner'),
    ('CS06', [47.2, 13.0, 0.0], 7.0, 6.0, 'none', 'east strip (ref: cherries right of the compound)'),
    ('CS07', [47.0, 40.0, 0.0], 7.0, 6.0, 'none', 'NE corner'),
    ('CS08', [13.0, -23.0, -3.2], 5.0, 5.0, 'none', 'bank east of F3 (ref: pink cherry right of the long flight)'),
    ('CS09', [-6.0, -9.0, 1.0], 8.0, 8.0, 'none', 'west cliff top (ref: upper-left cherry leaning over the stair)'),
    ('CS10', [-1.5, -31.0, -0.5], 6.0, 6.0, 'none', 'cliff top west of F4 (ref: pink along the lower left)'),
    ('CS11', [28.0, -43.5, -6.5], 10.0, 11.0, 'none', 'HERO cherry on the east bank at the right edge of CAM_LandscapeRef (ref: the big framing cherry; ours sits lower in the frame, see the plan)'),
    ('CS12', [5.0, -47.0, -7.2], 4.0, 4.0, 'none', 'low cherry on the west bank by the pool (ref: bottom centre)'),
    ('CS13', [41.0, -31.0, -5.5], 7.0, 7.0, 'none', 'far bank of the rapids'),
    ('CS14', [62.0, -22.0, -4.5], 7.0, 7.0, 'none', 'far bank'),
    ('CS15', [74.0, 2.0, -3.5], 7.0, 7.0, 'none', 'far bank row (ref: cherries receding upstream)'),
    ('CS16', [78.0, 30.0, -3.0], 7.0, 7.0, 'none', 'far bank row'),
    ('CS17', [92.0, 62.0, -2.5], 7.0, 7.0, 'none', 'far bank row'),
    ('CS18', [108.0, 95.0, -2.0], 7.0, 7.0, 'none', 'far bank row'),
    ('CS19', [40.0, 42.0, 0.5], 7.0, 6.0, 'none', 'behind the residence (ref: cherries among the back buildings)'),
    ('CS20', [12.0, 42.0, 0.5], 7.0, 6.0, 'none', 'behind the storehouse'),
]
CHERRY_SLOT_SPEC = {
    'actor': 'an empty Actor (or a hidden SM_DGB_Tree scaled to the slot) named CherrySlot_<id>, folder '
             'Dojo/CherrySlots, tags [CherrySlot, <id>], bHiddenInGame, no collision unless listed',
    'record': 'height_m, canopy_m, ground z snapped to the landscape at build, yaw free',
    'keep_clear': 'no other tree, pine or forest instance within 0.5 x canopy of a slot; slots >= 1.0 m from any path '
                  'edge; CS01/CS02 keep today\'s trunk collision so every walk/climb route is unchanged',
    'fx': 'the petal Niagara (this round) is placed per slot but spawned inactive (tag CherrySlotFX), plus one '
          'courtyard layer, all off until the cherries land; one showcase variant capture with them on',
}

# ----------------------------------------------------------------------------------------------------------------------
# 5. Boundary (1v1): the existing ring stays; a second, separable line on the terrace edge
# ----------------------------------------------------------------------------------------------------------------------
BOUNDARY = {
    'keep': 'SM_DGB_Boundary_1v1 (the ring on the wall outer face, 11 UCX) + the 13 alley/pocket/roof blockers in '
            'Dojo/Boundary_1v1: unchanged, still the 1v1 closure',
    'new_group': {'folder': 'Dojo/Boundary_1v1', 'tags': ['Boundary_1v1', 'TerraceEdge'],
                  'collision': 'Pawn block only; Camera/Visibility ignore (spec 5.3 class "1v1 boundary")',
                  'height_m': 6.0, 'thickness_m': 0.5,
                  'lines': [
                      {'id': 'B1_forecourt_front', 'from': [11.4, -7.35], 'to': [34.25, -7.35], 'z0': -0.5},
                      {'id': 'B2_forecourt_east', 'from': [34.25, -7.35], 'to': [34.25, -3.0], 'z0': -0.5},
                      {'id': 'B3_stair_head', 'from': [12.2, -5.4], 'to': [12.2, -7.6], 'z0': -0.5,
                       'note': 'closes the stair F1 head in the 1v1 (the stair is outside the 1v1 bounds)'},
                      {'id': 'B4_SE_edge', 'from': [34.25, -2.75], 'to': [48.75, -2.75], 'z0': 0.0},
                      {'id': 'B5_east_edge', 'from': [48.75, -2.75], 'to': [48.75, 44.0], 'z0': 0.0},
                      {'id': 'B6_north_edge', 'from': [-7.0, 44.0], 'to': [49.0, 44.0], 'z0': 0.0,
                       'note': 'the hillside; follows the ground (+0..+1)'},
                      {'id': 'B7_west_edge', 'from': [-7.0, -3.0], 'to': [-7.0, 44.0], 'z0': 0.0},
                      {'id': 'B8_SW_verge', 'from': [-7.0, -2.75], 'to': [12.2, -2.75], 'z0': 0.0},
                  ]},
    'world_edge': 'PROPOSAL (not 1v1): Dojo/Boundary_World, kept in every mode: blockers at the playable landscape '
                  'edge and the far river bank, so the BR cannot walk into the backdrop; owner call',
    'checks': ['CONTROL_1v1_gate_to_forecourt (blocked by the ring, as today)',
               'CONTROL_1v1_terrace_edge_* for B1-B8 with the ring disabled in a test copy (proves the second line)',
               'BR_stair_path_river_landing_to_gate + reverse (Boundary_1v1 dropped): walkable end to end',
               'existing 47 walk routes, 32/32 alley CONTROLs, climb routes, GASP trace 23/23: unchanged'],
}

# ----------------------------------------------------------------------------------------------------------------------
# 6. Reference camera (fitted to the compound landmarks; see camfit notes) and far layout from it
# ----------------------------------------------------------------------------------------------------------------------
CAM = {'name': 'CAM_LandscapeRef', 'loc': [4.8, -61.6, 12.9], 'yaw_deg_from_north': 24.2, 'pitch_deg': -3.7,
       'hfov_deg': 60.0, 'out_wh': [1024, 1536],
       'fit': 'weighted least squares on 10 reference landmarks (gate threshold/ridge, SW/SE wall corners, hall '
              'ridge/step, the lantern landing, the long-flight foot, the foreground flight, the rapids) with the '
              "horizon held near the reference's y ~710-760 and hfov >= 50: weighted rms 54 px on 1024 x 1536. The "
              'AI reference has no single perspective (its hall sits ~110 px higher than any camera that fits the '
              'wall allows), so this is a compromise; the build stage re-measures it on the first capture'}
W, H = CAM['out_wh']


def cam_basis(c=CAM):
    y, p = math.radians(c['yaw_deg_from_north']), math.radians(c['pitch_deg'])
    f = np.array([math.sin(y) * math.cos(p), math.cos(y) * math.cos(p), math.sin(p)])
    r = np.array([math.cos(y), -math.sin(y), 0.0])
    u = np.cross(r, f)
    k = (W / 2) / math.tan(math.radians(c['hfov_deg']) / 2)
    return f, r, u, k


def project(P, c=CAM):
    f, r, u, k = cam_basis(c)
    d = np.asarray(P, float) - np.array(c['loc'])
    df = d @ f
    return (W / 2 + (d @ r) / df * k, H / 2 - (d @ u) / df * k, df)


def ray_point(px, py, horiz_dist, c=CAM):
    """point on the camera ray through pixel (px, py) at a horizontal distance from the camera"""
    f, r, u, k = cam_basis(c)
    d = f + r * ((px - W / 2) / k) + u * ((H / 2 - py) / k)
    s = horiz_dist / math.hypot(d[0], d[1])
    p = np.array(c['loc']) + d * s
    return [round(float(v), 1) for v in p]


# reference pixels (read off dojo_landscape_ref.png crops, 1024 x 1536)
REF_PX = {'peakA_summit': (350, 457), 'peakB_summit': (567, 493), 'peakA_base_L': (160, 640), 'peakA_base_R': (473, 560),
          'peakB_base_L': (470, 545), 'peakB_base_R': (660, 560), 'ridgeM1_crest_mid': (380, 530),
          'ridgeM2_crest_right': (760, 640), 'far_valley_haze': (900, 700)}
PEAK_A_DIST, PEAK_B_DIST = 7500.0, 8300.0
PEAKS = []
for pid, dist, key in (('PeakA_left_large', PEAK_A_DIST, 'peakA'), ('PeakB_right_small', PEAK_B_DIST, 'peakB')):
    top = ray_point(*REF_PX[key + '_summit'], dist)
    bl = ray_point(*REF_PX[key + '_base_L'], dist)
    br = ray_point(*REF_PX[key + '_base_R'], dist)
    width_vis = round(math.dist(bl[:2], br[:2]), 0)
    PEAKS.append({'id': pid, 'summit': top, 'horizontal_dist_m': dist,
                  'azimuth_deg_from_north': round(math.degrees(math.atan2(top[0] - CAM['loc'][0],
                                                                          top[1] - CAM['loc'][1])), 1),
                  'visible_upper_width_m': width_vis, 'base_width_m': round(width_vis * 1.9, -2),
                  'snowline_z': round(top[2] * 0.55, -1),
                  'note': 'summit from the reference pixel through CAM_LandscapeRef; the lower flanks hidden by '
                          'ridge M1/M2 as in the reference'})
RIDGES = [
    {'id': 'M1_dark_forested_ridge', 'crest_from': ray_point(200, 600, 1300), 'crest_mid': ray_point(*REF_PX['ridgeM1_crest_mid'], 1250),
     'crest_to': ray_point(520, 600, 1350), 'look': 'dark blue-green conifer ridge in front of peak A (ref)'},
    {'id': 'M2_valley_ridges_right', 'crest_near': ray_point(*REF_PX['ridgeM2_crest_right'], 900),
     'crest_far': ray_point(*REF_PX['far_valley_haze'], 2600),
     'look': 'receding hazier ridges along the river valley to the NE (ref right side)'},
    {'id': 'F_far_ridges', 'crest_mid': ray_point(620, 600, 4200), 'look': 'hazy blue far ridges between the peaks'},
    {'id': 'N_near_hill', 'crest': [22.0, 200.0, 45.0], 'look': 'the forested hill directly behind the hall (FZ1)'},
]

# ----------------------------------------------------------------------------------------------------------------------
# 7. Landscape actors
# ----------------------------------------------------------------------------------------------------------------------
LANDSCAPES = {
    'LS_Valley': {'centre': [22.0, 18.0], 'size_m': 1008, 'verts': '2017 x 2017', 'spacing_m': 0.5,
                  'components': '16 x 16 of 126 quads (2 x 2 sections of 63)', 'nanite': True,
                  'z_range_m': [-12.0, 120.0],
                  'spot_heights': {
                      'under_compound': -0.30, 'terrace_strips': 0.0, 'forecourt': -0.5,
                      'SW_verge_wall_foot': -2.0, 'forecourt_wall_foot': -4.5, 'SE_wall_foot': -6.0,
                      'east_wall_foot': '-6.0 (y -3..9) / -4.0 (y 9..29) / -3.0 (y 29..44)',
                      'west_cliff_top': '+1.5 at (-8,-5), +0.5 at (-8,-20), -3.0 at (-6,-40)',
                      'river_bed': 'water z - depth', 'far_bank': '+2 at x 70, +5 at x 85, +20 at x 130',
                      'north_hill': '0 at y 44, +6 at y 60, +20 at y 100, +45 at y 200, +90 at y 400',
                      'west_ridge': '+4 at x -30, +18 at x -80, +40 at x -200'},
                  'sculpt': 'Landscape edit layers: base by script from these spot heights + river channel carve; '
                            'detail with Landscape Patches using the OWNED Scenery_Tutorial stamps '
                            '(T_Land_Mountain01/02, T_Land_Erosion00/01, BP_Landscape_Patch)'},
    'LS_Far': {'centre': [0.0, 3000.0], 'size_m': 8064, 'verts': '1009 x 1009', 'spacing_m': 8.0, 'nanite': True,
               'hole_or_below': 'sits 30 m below LS_Valley where they overlap (or a visibility hole)',
               'carries': 'ridges M1/M2/F + (option B) the two snow peaks as patch stamps',
               'material': 'far landscape material: forest canopy, rock, snow by height + slope (snow-peak material '
                           'we make) + T_MacroVariation'},
    'peaks_option_A': 'Fishermans SM_Mountain_01 (303 x 303 x 47 m, 2.16 M Nanite tris, MI_Mountain with MF_Snow) '
                      'scaled to each peak (xy ~12-13, z ~15-19) - only if a staging look check passes',
    'peaks_option_B': 'LS_Far sculpted with T_Land_Mountain01/02 patch stamps + our snow-peak material',
}
LAYERS = [
    ('Grass', 'Fishermans T_Grass_D 4K / N 2K / ORD 2K', 'terrace strips, gentle banks'),
    ('MossyGrass', 'Scenery_Tutorial T_MossyGrass_01 (1K)', 'moss patches, bank crests'),
    ('MossyRock', 'Scenery_Tutorial T_Mossy_Rocky_Ground_vcrkeax (registry 1K; named 4K)', 'banks, cliff ledges, stair sides'),
    ('ForestFloor', 'Scenery_Tutorial T_ForestGround (1K)', 'under FZ1-FZ3'),
    ('RockSlope', 'Fishermans T_Rocks_D/N/R/DP 4K tiling', 'auto on slopes > 35 deg (MF_SlopeBlend)'),
    ('Dirt', 'Fishermans T_Ground_Dirt 4K / Dirt_Cracked 4K', 'bank path P2, the BR trail, river margins'),
    ('RiverBed', 'Scenery_Tutorial T_MossyCreekStones (1K)', 'under the water'),
    ('Snow', 'Scenery_Tutorial T_snow_02 (1K) + our snow-peak material', 'LS_Far above the snowline'),
]

# ----------------------------------------------------------------------------------------------------------------------
# 8. Removal list, supporting cameras
# ----------------------------------------------------------------------------------------------------------------------
REMOVE = ['Outside/Street (237 instances: road, kerbs, gutter, verges, canal, terrace-edge strips, SM_DKX_Road_Gate)',
          'Outside/Town (42)', 'Outside/Ground (4)', 'Outside/Far (6: ridge rings + impostor town)',
          'Props/Modern instances outside the compound walls (street lamps, poles, wires, junction box)',
          'Trees/SM_DGB_Tree x2 visuals (CS01/CS02 keep their trunk hulls hidden)',
          'the 22 old tree_slots (replaced by the pine list, CherrySlots and forest zones)']
KEEP = ['every compound piece, prop, decal, light and GASP marker', 'Outside alley/pocket fences + Boundary_1v1 group',
        'UDS dusk (1730 lock, sun 9.08 deg from the west) and the round-9 restore_s1 look values']
CAMERAS_EXTRA = [
    {'name': 'CAM_LandscapeRef', **{k: v for k, v in CAM.items() if k != 'name'}},
    {'name': 'CAM_StairClimb', 'loc': [3.3, -39.3, -5.4], 'look_at': [12.0, -4.0, 1.0], 'hfov_deg': 60.0,
     'out_wh': [1920, 1080], 'note': 'player eye at the river landing looking up the path to the gate'},
    {'name': 'CAM_Rapids', 'loc': [10.2, -23.1, -0.4], 'look_at': [45.0, -10.0, -5.5], 'hfov_deg': 62.0,
     'out_wh': [1920, 1080], 'note': 'from L3 over the rapids, the foot boulders and WR4'},
    {'name': 'CAM_PeaksOverHall', 'loc': [22.0, -6.5, 1.2], 'look_at': [260.0, 7400.0, 700.0], 'hfov_deg': 50.0,
     'out_wh': [1920, 1080], 'note': 'forecourt eye level: gate, hall roofs and the two peaks'},
]

# ----------------------------------------------------------------------------------------------------------------------
# projection check table
# ----------------------------------------------------------------------------------------------------------------------
CHECK_PTS = {
    'gate threshold (22,-1,0)': ([22, -1, 0], (367, 927)),
    'gate ridge': ([22, 0, 4.4], (367, 827)),
    'SW wall corner cap': ([-1, -1, 2.5], (45, 862)),
    'SE wall corner cap': ([45, -1, 2.5], (645, 830)),
    'hall ridge centre': ([22, 28.5, 8.3], (270, 645)),
    'hall front step': ([22, 21.5, 0.5], (320, 800)),
    'L3 lantern landing': ([9.1, -23.1, -2.0], (240, 1100)),
    'F3 foot (long flight)': ([9.1, -28.0, -4.0], (200, 1245)),
    'F4/F5 foreground flight': ([3.3, -36.6, -6.5], (80, 1420)),
    'rapids R6-R7': ([31, -22, -6.6], (700, 1060)),
    'river exit bottom (R8)': ([16.5, -44.0, -7.9], (620, 1536)),
    'CS11 hero cherry trunk': ([28.0, -43.5, -6.5], (1000, 1300)),
}


def check_table():
    rows = []
    for name, (P, ref) in CHECK_PTS.items():
        x, y, df = project(P)
        rows.append({'point': name, 'world': P, 'proj_px': [int(round(x)), int(round(y))], 'ref_px': list(ref),
                     'd_px': int(round(math.hypot(x - ref[0], y - ref[1]))), 'in_front': bool(df > 0)})
    return rows


# ----------------------------------------------------------------------------------------------------------------------
# drawing
# ----------------------------------------------------------------------------------------------------------------------
def font(sz, bold=False):
    try:
        return ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf' if bold else 'C:/Windows/Fonts/arial.ttf', sz)
    except OSError:
        return ImageFont.load_default()


def draw_topdown(path):
    # near field: x -75..125, y -95..95  (200 x 190 m) at 9 px/m
    S = 9.0
    X0, X1, Y0, Y1 = -75.0, 125.0, -95.0, 95.0
    NW, NH = int((X1 - X0) * S), int((Y1 - Y0) * S)
    FW = 760
    img = Image.new('RGB', (NW + FW + 60, NH + 160), (246, 244, 238))
    near = Image.new('RGB', (NW, NH), (246, 244, 238))
    d = ImageDraw.Draw(near, 'RGBA')

    def P(x, y):
        return ((x - X0) * S, (Y1 - y) * S)

    def poly(pts, fill, outline=None, w=1):
        d.polygon([P(*p[:2]) for p in pts], fill=fill, outline=outline)
        if outline and w > 1:
            d.line([P(*p[:2]) for p in pts] + [P(*pts[0][:2])], fill=outline, width=w)

    f12, f14, f16, f22 = font(12), font(14), font(16, True), font(22, True)
    dt = ImageDraw.Draw(img, 'RGBA')
    dt.text((15, 12), 'Dojo LANDSCAPE ROUND - top-down plan (level frame: metres, x east, y north; UE = x*100, -y*100)',
           fill=(20, 20, 20), font=f22)
    dt.text((15, 44), 'Near field (1 grid = 10 m).  Keep: compound + UDS dusk.  New: terrace + ishigaki, stair path, '
                     'river + rapids, boulders, pines, CherrySlots (hidden), forest zones, 1v1 terrace-edge blockers.',
           fill=(40, 40, 40), font=f14)
    dt.text((15, 66), 'Sun: 9.08 deg from the west (UDS 1730 lock) - arrow at left.  Heights in metres relative to the '
                     'courtyard (z 0).', fill=(40, 40, 40), font=f14)
    # grid
    for gx in range(int(X0), int(X1) + 1, 10):
        d.line([P(gx, Y0), P(gx, Y1)], fill=(0, 0, 0, 22 if gx % 50 else 60), width=1)
        if gx % 50 == 0:
            d.text(P(gx + 0.5, Y0 + 3), str(gx), fill=(90, 90, 90), font=f12)
    for gy in range(int(Y0), int(Y1) + 1, 10):
        d.line([P(X0, gy), P(X1, gy)], fill=(0, 0, 0, 22 if gy % 50 else 60), width=1)
        if gy % 50 == 0:
            d.text(P(X0 + 0.5, gy + 1.5), str(gy), fill=(90, 90, 90), font=f12)
    # forests
    for fz in FORESTS:
        if isinstance(fz['poly'], list):
            poly(fz['poly'], (60, 110, 70, 60), (40, 90, 50, 160))
            cx = sum(p[0] for p in fz['poly']) / len(fz['poly'])
            cy = sum(p[1] for p in fz['poly']) / len(fz['poly'])
            cx, cy = min(max(cx, X0 + 12), X1 - 25), min(max(cy, Y0 + 5), Y1 - 5)
            d.text(P(cx - 10, cy), fz['id'], fill=(30, 70, 35), font=f14)
    # zones
    zc = {'boulder field': (150, 150, 150, 110), 'mossy rock bank': (120, 140, 90, 110), 'rocky cliff': (110, 105, 100, 150),
          'bank + slope': (150, 170, 120, 90), 'path bank': (190, 170, 130, 110)}
    for z in ZONES:
        if 'poly' in z:
            poly(z['poly'], zc.get(z['kind'], (160, 160, 160, 90)), (80, 80, 80, 160))
            cx = sum(p[0] for p in z['poly']) / len(z['poly'])
            cy = sum(p[1] for p in z['poly']) / len(z['poly'])
            d.text(P(cx - 4, cy + 1), z['id'].split('_')[0], fill=(40, 40, 40), font=f12)
    # river
    pts = [(r[1], r[2]) for r in RIVER]
    widths = [r[4] for r in RIVER]
    left, right = [], []
    for i, (x, y) in enumerate(pts):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, len(pts) - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        n = math.hypot(dx, dy)
        nx, ny = -dy / n, dx / n
        left.append((x + nx * widths[i] / 2, y + ny * widths[i] / 2))
        right.append((x - nx * widths[i] / 2, y - ny * widths[i] / 2))
    d.polygon([P(*p) for p in left + right[::-1]], fill=(64, 196, 196, 200), outline=(20, 110, 120))
    # rapids band R4..R7
    ri = [r[0] for r in RIVER]
    a, b = ri.index('R4'), ri.index('R7')
    d.polygon([P(*p) for p in left[a:b + 1] + right[a:b + 1][::-1]], fill=(255, 255, 255, 120))
    for r in RIVER:
        if X0 < r[1] < X1 and Y0 < r[2] < Y1:
            d.ellipse([P(r[1] - 0.8, r[2] + 0.8), P(r[1] + 0.8, r[2] - 0.8)], fill=(10, 80, 90))
            d.text(P(r[1] + 1.5, r[2] + 1.5), f'{r[0]} {r[3]:+.1f}', fill=(10, 70, 80), font=f12)
    d.text(P(40, -24), 'RAPIDS R4-R7', fill=(10, 60, 70), font=f16)
    # terrace + forecourt
    poly(TERRACE['upper_terrace']['poly'], (214, 200, 160, 150), (120, 100, 60), 2)
    poly(TERRACE['forecourt']['poly'], (200, 185, 150, 200), (120, 100, 60), 2)
    # compound
    poly([[-1, -1], [45, -1], [45, 37], [-1, 37]], (236, 226, 196, 255), (90, 60, 40), 3)
    hx, hy = COMPOUND['hall']['x'], COMPOUND['hall']['y']
    poly([[hx[0], hy[0]], [hx[1], hy[0]], [hx[1], hy[1]], [hx[0], hy[1]]], (120, 110, 110, 200), (60, 50, 50))
    d.text(P(17, 29), 'HALL', fill=(255, 255, 255), font=f16)
    d.text(P(8, 10), 'COMPOUND (1v1 arena, z 0)', fill=(90, 60, 40), font=f16)
    d.rectangle([P(18.8, 1.93), P(25.2, -1.93)], fill=(90, 60, 40))
    d.text(P(26, 0.5), 'gate', fill=(90, 60, 40), font=f12)
    # walls
    for w in WALLS:
        d.line([P(*w['from']), P(*w['to'])], fill=(70, 70, 75), width=6)
        mx, my = (w['from'][0] + w['to'][0]) / 2, (w['from'][1] + w['to'][1]) / 2
        lab = w['id'].split('_')[0] + ' ' + w['module_H'].split(' ')[0]
        off = (1.5, -1.8) if w['faces'].startswith('-y') else (1.2, 0)
        d.text(P(mx + off[0], my + off[1]), lab, fill=(40, 40, 45), font=f12)
    # boundary
    for ln in BOUNDARY['new_group']['lines']:
        d.line([P(*ln['from']), P(*ln['to'])], fill=(220, 30, 30, 220), width=2)
    # stair
    for s in STAIR:
        if 'bottom' in s:
            a, b = s['bottom'], s['top']
            d.line([P(a[0], a[1]), P(b[0], b[1])], fill=(245, 245, 245), width=int(1.8 * S))
            d.line([P(a[0], a[1]), P(b[0], b[1])], fill=(40, 40, 40), width=1)
            # riser ticks
            n = int(round((b[2] - a[2]) / (1 / 6)))
            for i in range(n + 1):
                t = i / max(n, 1)
                cx, cy = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
                ux, uy = (b[0] - a[0]), (b[1] - a[1])
                L = math.hypot(ux, uy)
                px_, py_ = -uy / L * 0.9, ux / L * 0.9
                d.line([P(cx - px_, cy - py_), P(cx + px_, cy + py_)], fill=(120, 120, 120), width=1)
            d.text(P(max(a[0], b[0]) + 1.1, (a[1] + b[1]) / 2 + 0.6), f"{s['id']} {b[2]:+.1f}/{a[2]:+.1f}",
                   fill=(20, 20, 20), font=f12)
        elif 'centre' in s:
            c = s['centre']
            half = 0.9
            if 'SB' in s['piece']:
                d.rectangle([P(c[0] - 2.0, c[1] + half), P(c[0] + 2.0, c[1] - half)], fill=(235, 235, 235),
                            outline=(60, 60, 60))
            else:
                d.rectangle([P(c[0] - half, c[1] + half), P(c[0] + half, c[1] - half)], fill=(235, 235, 235),
                            outline=(60, 60, 60))
            d.text(P(c[0] - 4.2, c[1] + 0.7), s['id'], fill=(20, 20, 20), font=f12)
        else:
            a, b = s['from'], s['to']
            d.line([P(a[0], a[1]), P(b[0], b[1])], fill=(235, 235, 235), width=int(1.8 * S))
            d.text(P(a[0] - 5.5, (a[1] + b[1]) / 2), s['id'], fill=(20, 20, 20), font=f12)
    for ln in LANTERNS:
        x, y = ln['loc'][:2]
        d.ellipse([P(x - 0.45, y + 0.45), P(x + 0.45, y - 0.45)], fill=(255, 170, 30), outline=(120, 60, 0))
    # boulders (hero)
    for bx, by, r in HERO_BOULDERS:
        d.ellipse([P(bx - r, by + r), P(bx + r, by - r)], fill=(135, 135, 140, 230), outline=(60, 60, 60))
    # pines
    for pid, var, loc, yaw, sc, note in PINES:
        x, y = loc[:2]
        rad = {'A': 1.2, 'B': 1.7, 'C': 2.3, 'D': 1.6}[var[4]] * sc
        opt = pid.endswith('opt')
        d.ellipse([P(x - rad, y + rad), P(x + rad, y - rad)], fill=(20, 90, 50, 120 if opt else 220),
                  outline=(10, 50, 25))
        d.text(P(x + rad + 0.3, y + 0.8), f'{pid.split("_")[0]} {var[4:]}', fill=(10, 60, 30), font=f12)
    # cherry slots
    for cid, loc, h, can, col, note in CHERRY:
        x, y = loc[:2]
        if X0 < x < X1 and Y0 < y < Y1:
            r = can / 2
            d.ellipse([P(x - r, y + r), P(x + r, y - r)], outline=(230, 90, 160), width=2)
            d.line([P(x - 0.6, y), P(x + 0.6, y)], fill=(200, 50, 130), width=2)
            d.line([P(x, y - 0.6), P(x, y + 0.6)], fill=(200, 50, 130), width=2)
            d.text(P(x + 0.8, y - 0.4), cid, fill=(180, 40, 120), font=f12)
    # camera
    cx, cy = CAM['loc'][:2]
    yaw = math.radians(CAM['yaw_deg_from_north'])
    hf = math.radians(CAM['hfov_deg'] / 2)
    L = 160
    for s_ in (-1, 1):
        ex, ey = cx + L * math.sin(yaw + s_ * hf), cy + L * math.cos(yaw + s_ * hf)
        d.line([P(cx, cy), P(ex, ey)], fill=(40, 40, 200, 200), width=2)
    d.ellipse([P(cx - 1.2, cy + 1.2), P(cx + 1.2, cy - 1.2)], fill=(40, 40, 200))
    d.text(P(cx - 30, cy - 2), 'CAM_LandscapeRef z +11.2', fill=(40, 40, 200), font=f14)
    for c in CAMERAS_EXTRA[1:]:
        x, y = c['loc'][:2]
        if X0 < x < X1 and Y0 < y < Y1:
            lx, ly = c['look_at'][:2]
            dd = math.hypot(lx - x, ly - y)
            d.line([P(x, y), P(x + (lx - x) / dd * 12, y + (ly - y) / dd * 12)], fill=(90, 90, 220), width=2)
            d.ellipse([P(x - 0.7, y + 0.7), P(x + 0.7, y - 0.7)], fill=(90, 90, 220))
    # sun arrow (from the west, slightly south)
    sx, sy = X0 + 6, 70
    d.line([P(sx, sy), P(sx + 14, sy + 1.8)], fill=(230, 120, 20), width=4)
    d.polygon([P(sx + 14, sy + 1.8), P(sx + 11, sy + 3.5), P(sx + 11.4, sy - 0.2)], fill=(230, 120, 20))
    d.text(P(sx, sy + 4.5), 'SUN 9 deg (W)', fill=(200, 100, 10), font=f14)
    # north arrow
    nx_, ny_ = X1 - 8, 82
    d.line([P(nx_, ny_ - 8), P(nx_, ny_)], fill=(0, 0, 0), width=3)
    d.polygon([P(nx_, ny_ + 1), P(nx_ - 1.5, ny_ - 2.5), P(nx_ + 1.5, ny_ - 2.5)], fill=(0, 0, 0))
    d.text(P(nx_ - 1, ny_ + 5), 'N', fill=(0, 0, 0), font=f16)
    img.paste(near, (15, 110))
    ImageDraw.Draw(img).rectangle([15, 110, 15 + NW, 110 + NH], outline=(60, 60, 60), width=2)
    d = ImageDraw.Draw(img, 'RGBA')
    # legend
    lx, ly = 15, NH + 128
    items = [((236, 226, 196), 'compound'), ((214, 200, 160), 'terrace z 0'), ((200, 185, 150), 'forecourt z -0.5'),
             ((70, 70, 75), 'ishigaki wall run'), ((245, 245, 245), 'stair path (flight/landing)'),
             ((255, 170, 30), 'lantern'), ((64, 196, 196), 'river (white = rapids)'), ((135, 135, 140), 'hero boulder'),
             ((20, 90, 50), 'niwaki pine SM_DKN'), ((230, 90, 160), 'CherrySlot (hidden)'),
             ((220, 30, 30), '1v1 terrace-edge blocker'), ((60, 110, 70), 'conifer forest zone'),
             ((40, 40, 200), 'camera')]
    x = lx
    for col, lab in items:
        d.rectangle([x, ly, x + 16, ly + 16], fill=col, outline=(40, 40, 40))
        d.text((x + 20, ly), lab, fill=(20, 20, 20), font=f12)
        x += 28 + int(d.textlength(lab, font=f12))
    # ---------------- far field panel ----------------
    ox, oy = NW + 45, 110
    FS = FW / 12000.0  # 12 km wide
    FX0, FY1 = -3500.0, 9500.0

    def Q(x, y):
        return (ox + (x - FX0) * FS, oy + (FY1 - y) * FS)

    d.rectangle([ox, oy, ox + FW - 10, oy + 12000 * FS], fill=(236, 240, 244), outline=(80, 80, 80))
    d.text((ox + 6, oy + 6), 'Far field (1 grid = 1 km)', fill=(20, 20, 20), font=f16)
    for gx in range(-3000, 8501, 1000):
        d.line([Q(gx, FY1), Q(gx, FY1 - 12000)], fill=(0, 0, 0, 25))
    for gy in range(-2000, 9501, 1000):
        d.line([Q(FX0, gy), Q(FX0 + 12000, gy)], fill=(0, 0, 0, 25))
    # LS_Valley and LS_Far squares
    v = LANDSCAPES['LS_Valley']
    h = v['size_m'] / 2
    d.rectangle([Q(v['centre'][0] - h, v['centre'][1] + h), Q(v['centre'][0] + h, v['centre'][1] - h)],
                outline=(120, 90, 40), width=2)
    fl = LANDSCAPES['LS_Far']
    h = fl['size_m'] / 2
    d.rectangle([Q(fl['centre'][0] - h, fl['centre'][1] + h), Q(fl['centre'][0] + h, fl['centre'][1] - h)],
                outline=(90, 90, 160), width=2)
    d.text(Q(fl['centre'][0] - h + 60, fl['centre'][1] - h + 420), 'LS_Far 8 km (8 m)', fill=(90, 90, 160), font=f12)
    d.text(Q(v['centre'][0] + 600, v['centre'][1] - 300), 'LS_Valley 1 km (0.5 m)', fill=(120, 90, 40), font=f12)
    # river far
    d.line([Q(r[1], r[2]) for r in RIVER], fill=(40, 160, 170), width=3)
    # ridges
    m1 = RIDGES[0]
    d.line([Q(*m1['crest_from'][:2]), Q(*m1['crest_mid'][:2]), Q(*m1['crest_to'][:2])], fill=(30, 80, 50), width=4)
    d.text(Q(m1['crest_to'][0] + 80, m1['crest_to'][1]), 'M1 ridge', fill=(30, 80, 50), font=f12)
    m2 = RIDGES[1]
    d.line([Q(*m2['crest_near'][:2]), Q(*m2['crest_far'][:2])], fill=(60, 100, 90), width=3)
    d.text(Q(m2['crest_far'][0] + 80, m2['crest_far'][1]), 'M2 valley ridges', fill=(60, 100, 90), font=f12)
    fr = RIDGES[2]
    d.ellipse([Q(fr['crest_mid'][0] - 700, fr['crest_mid'][1] + 150), Q(fr['crest_mid'][0] + 700, fr['crest_mid'][1] - 150)],
              outline=(120, 130, 170), width=2)
    d.text(Q(fr['crest_mid'][0] + 750, fr['crest_mid'][1]), 'F far ridges', fill=(120, 130, 170), font=f12)
    for pk in PEAKS:
        x, y, z = pk['summit']
        r = pk['base_width_m'] / 2
        d.ellipse([Q(x - r, y + r * 0.8), Q(x + r, y - r * 0.8)], fill=(255, 255, 255, 200), outline=(90, 110, 150), width=2)
        d.ellipse([Q(x - 60, y + 60), Q(x + 60, y - 60)], fill=(60, 80, 120))
        d.text(Q(x + r + 60, y + 200), f"{pk['id'].split('_')[0]} +{z:.0f} m", fill=(40, 60, 110), font=f14)
        d.text(Q(x + r + 60, y - 150), f"{pk['horizontal_dist_m'] / 1000:.1f} km az {pk['azimuth_deg_from_north']}",
               fill=(40, 60, 110), font=f12)
    # camera far
    cx, cy = CAM['loc'][:2]
    for s_ in (-1, 1):
        ex, ey = cx + 9500 * math.sin(yaw + s_ * hf), cy + 9500 * math.cos(yaw + s_ * hf)
        d.line([Q(cx, cy), Q(ex, ey)], fill=(40, 40, 200, 150), width=1)
    d.rectangle([Q(-1, 37), Q(45, -1)], fill=(90, 60, 40))
    d.text(Q(cx + 150, cy - 200), 'dojo + CAM_LandscapeRef', fill=(40, 40, 200), font=f12)
    img.save(path)


HERO_BOULDERS = [  # x, y, plan radius - placement targets for the sourced foot / bank / river boulders
    (29.0, -9.4, 1.4), (35.5, -9.0, 1.2), (42.0, -6.0, 1.5), (47.5, -5.0, 1.3), (52.0, -3.8, 1.1),   # foot
    (13.5, -37.0, 1.3), (15.0, -26.0, 1.2), (12.5, -18.0, 1.0), (18.0, -31.0, 1.0),                    # west bank
    (40.0, -14.5, 0.8), (33.0, -19.0, 0.7), (45.5, -12.0, 0.7), (28.0, -25.0, 0.8), (51.0, -9.0, 0.6),  # rapids
    (31.0, -29.0, 0.6), (36.0, -22.0, 0.5), (58.0, -2.0, 0.7), (24.0, -34.0, 0.7), (60.0, 6.0, 0.6),
    (17.0, -46.0, 0.8), (21.0, -41.0, 0.6),
]


def draw_ref_check(path, rows):
    ref = Image.open(REF).convert('RGB')
    wire = Image.new('RGB', (W, H), (235, 238, 242))
    d = ImageDraw.Draw(wire, 'RGBA')

    def pp(P):
        x, y, df = project(P)
        return (x, y) if df > 1 else None

    def line3(pts, col, w=2):
        q = [pp(p) for p in pts]
        for a, b in zip(q, q[1:]):
            if a and b:
                d.line([a, b], fill=col, width=w)

    # horizon
    f, r, u, k = cam_basis()
    hy = H / 2 + math.tan(math.radians(CAM['pitch_deg'])) * k
    d.line([(0, hy), (W, hy)], fill=(150, 150, 190), width=1)
    # peaks as triangles
    for pk in PEAKS:
        x, y, z = pk['summit']
        bw = pk['base_width_m'] / 2
        yaw = math.radians(pk['azimuth_deg_from_north'])
        rx, ry = math.cos(yaw), -math.sin(yaw)
        a = pp([x - rx * bw, y - ry * bw, 150])
        b = pp([x, y, z])
        c = pp([x + rx * bw, y + ry * bw, 150])
        s1 = pp([x - rx * bw * 0.45, y - ry * bw * 0.45, pk['snowline_z']])
        s2 = pp([x + rx * bw * 0.45, y + ry * bw * 0.45, pk['snowline_z']])
        if a and b and c:
            d.polygon([a, b, c], fill=(150, 160, 185))
            d.polygon([s1, b, s2], fill=(250, 250, 252))
    # ridges M1
    m1 = RIDGES[0]
    q = [pp(m1['crest_from']), pp(m1['crest_mid']), pp(m1['crest_to'])]
    if all(q):
        d.polygon(q + [(q[2][0], hy + 8), (q[0][0], hy + 8)], fill=(70, 100, 95))
    # terrain plate: river
    line3([[rr[1], rr[2], rr[3]] for rr in RIVER], (40, 170, 180), 10)
    # compound outline (wall caps)
    line3([[-1, -1, 2.5], [45, -1, 2.5], [45, 37, 2.5], [-1, 37, 2.5], [-1, -1, 2.5]], (120, 80, 50), 3)
    line3([[-1, -1, 0], [45, -1, 0]], (120, 80, 50), 1)
    hx, hy_ = COMPOUND['hall']['x'], COMPOUND['hall']['y']
    line3([[hx[0], hy_[0], 3], [hx[1], hy_[0], 3], [hx[1], hy_[1], 3], [hx[0], hy_[1], 3], [hx[0], hy_[0], 3]],
          (80, 70, 70), 2)
    line3([[hx[0] + 3, 28.5, 8.3], [hx[1] - 3, 28.5, 8.3]], (80, 70, 70), 3)
    line3([[18.8, -1.5, 4.4], [25.2, -1.5, 4.4]], (90, 60, 40), 4)
    for w_ in WALLS:
        a, b = w_['from'], w_['to']
        fz = w_['foot_z'] if isinstance(w_['foot_z'], float) else -4.0
        line3([[a[0], a[1], w_['top_z']], [b[0], b[1], w_['top_z']]], (70, 70, 75), 3)
        line3([[a[0], a[1], fz], [b[0], b[1], fz]], (70, 70, 75), 1)
    for s in STAIR:
        if 'bottom' in s:
            line3([s['bottom'], s['top']], (250, 250, 250), 7)
            line3([s['bottom'], s['top']], (30, 30, 30), 1)
        elif 'centre' in s:
            c = s['centre']
            line3([[c[0] - 0.9, c[1], c[2]], [c[0] + 0.9, c[1], c[2]]], (250, 250, 250), 6)
        else:
            line3([s['from'], s['to']], (230, 225, 210), 7)
    for bx, by, rr in HERO_BOULDERS:
        q = pp([bx, by, -5.5])
        if q:
            rad = max(3, rr * 900 / max(1.0, math.dist([bx, by], CAM['loc'][:2])))
            d.ellipse([q[0] - rad, q[1] - rad * 0.7, q[0] + rad, q[1] + rad * 0.7], fill=(140, 140, 145))
    for cid, loc, h, can, col, note in CHERRY:
        base = pp(loc)
        top = pp([loc[0], loc[1], loc[2] + h * 0.7])
        if base and top:
            rad = abs(base[1] - top[1]) * can / h * 0.6
            d.ellipse([top[0] - rad, top[1] - rad * 0.8, top[0] + rad, top[1] + rad * 0.8], outline=(230, 90, 160),
                      width=2)
    for row in rows:
        x, y = row['proj_px']
        rx_, ry_ = row['ref_px']
        d.ellipse([x - 5, y - 5, x + 5, y + 5], outline=(0, 0, 200), width=2)
    out = Image.new('RGB', (W * 2 + 20, H + 60), (255, 255, 255))
    rr = ref.copy()
    dr = ImageDraw.Draw(rr)
    for row in rows:
        x, y = row['ref_px']
        dr.ellipse([x - 6, y - 6, x + 6, y + 6], outline=(255, 0, 0), width=3)
    out.paste(rr, (0, 60))
    out.paste(wire, (W + 20, 60))
    do = ImageDraw.Draw(out)
    do.text((10, 10), 'Reference (red = check points)', fill=(0, 0, 0), font=font(26, True))
    do.text((W + 30, 10), 'Plan through CAM_LandscapeRef (blue = same points)', fill=(0, 0, 0), font=font(26, True))
    out.save(path)


def main():
    rows = check_table()
    plan = {
        'title': 'Dojo LANDSCAPE ROUND - layout plan (plan stage)',
        'date': '2026-09-30',
        'frame': 'level frame of layout_showcase.json: metres, x east, y north, z up (courtyard z 0); Unreal cm = '
                 '(x*100, -y*100, z*100), UE yaw = -rot_z; azimuths here are degrees from north (+y) toward east (+x)',
        'reference': 'References/Dojo/dojo_landscape_ref.png (look reference; daytime) - the sunset stays (UDS 1730 '
                     'lock, sun 9.08 deg from the west, round-9 restore_s1 look)',
        'compound': COMPOUND, 'terrace': TERRACE, 'walls': WALLS,
        'stair_path': {'segments': STAIR, 'totals': STAIR_TOTALS, 'lanterns': LANTERNS, 'lantern_rule': LANTERN_RULE},
        'river': {'spline': [{'id': r[0], 'xy': [r[1], r[2]], 'water_z': r[3], 'width_m': r[4], 'zone': r[5]}
                             for r in RIVER], **RIVER_NOTES},
        'hero_boulders': [{'xy': [b[0], b[1]], 'plan_radius_m': b[2]} for b in HERO_BOULDERS],
        'zones': ZONES, 'forests': FORESTS,
        'pines': [{'id': p[0], 'variant': p[1], 'meshes': [f'SM_DKN_{p[1]}_Trunk', f'SM_DKN_{p[1]}_Foliage'] +
                   ([f'SM_DKN_{p[1]}_Rock'] if p[1].startswith('PineD') else []) +
                   [f'SM_DKN_BaseMound_{p[1][4]}'], 'loc': p[2], 'yaw_deg': p[3], 'scale': p[4], 'note': p[5],
                   'ue_cm': ue(p[2])} for p in PINES],
        'cherry_slots': {'spec': CHERRY_SLOT_SPEC,
                         'slots': [{'id': c[0], 'loc': c[1], 'height_m': c[2], 'canopy_m': c[3], 'collision': c[4],
                                    'note': c[5], 'ue_cm': ue(c[1])} for c in CHERRY]},
        'boundary': BOUNDARY,
        'far': {'peaks': PEAKS, 'ridges': RIDGES},
        'landscapes': LANDSCAPES, 'landscape_layers': [{'layer': a, 'source': b, 'where': c} for a, b, c in LAYERS],
        'cameras': CAMERAS_EXTRA + [{'name': 'CAM_LandscapeRef_ue', 'loc_cm': ue(CAM['loc']),
                                     'ue_rotation': {'yaw': round(CAM['yaw_deg_from_north'] - 90.0, 1),
                                                     'pitch': CAM['pitch_deg'], 'roll': 0.0},
                                     'note': 'UE yaw: 0 = +X (east), -90 = UE -Y = level north; UE yaw = azimuth_from_north - 90'}],
        'ref_camera_check': rows,
        'remove': REMOVE, 'keep': KEEP,
    }
    with open(os.path.join(HERE, 'landscape_plan.json'), 'w', encoding='utf-8') as fh:
        json.dump(plan, fh, indent=1)
    draw_topdown(os.path.join(HERE, 'landscape_plan_topdown.png'))
    draw_ref_check(os.path.join(HERE, 'ref_camera_check.png'), rows)
    for r in rows:
        print(r)
    for p in PEAKS:
        print(p)
    for rd in RIDGES:
        print(rd)
    print('CAM ue', ue(CAM['loc']))


if __name__ == '__main__':
    main()
