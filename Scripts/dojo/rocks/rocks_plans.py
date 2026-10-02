"""Pilot rock plans (spec): every number is read off the owner's sheet (References/Dojo/dojo_rocks_ref.png) by
Scripts/dojo/rocks/rocks_ref.py -> WorkFiles/dojo/build/rocks/ref_measure.json, or is a study 4.9 parameter.

Frame: x = length (the sheet's main view looks along +y from -y), y = depth (+y away from the viewer), z up,
ground z = 0 (the sheet's contact line); the mesh continues below grade as a buried skirt (study 3.10).

Depth is the one dimension the sheet does not draw consistently (its smaller views are drawn at other scales and
from other angles; RiverRound's end views say depth ~ height, its oblique plan view says ~0.66 x height). Rule
used: the end (side) view is the depth authority, scaled by the main view's height; the plan view is a soft check
(its outline shape is used, stretched to that depth). Where the two disagree by more than 10 % the depth is the
geometric mean and the disagreement is recorded (BUILD_NOTES).
"""
from __future__ import annotations

PLANS = {
    "RiverRound": dict(
        prefix="SM_DKR_Rock_BoulderRiver01", kind="river", seed=7101,
        sheet="row 2, boulder 2 (sheet x 334-506): the rounded loaf",
        size=dict(L=2.077, H=1.359, D=1.27),       # D: end views 1.33 / 1.36, plan 0.90 -> 1.27 (end views lead)
        views=dict(front=("RiverRound", "front"), side=("RiverRound", "side"), top=("RiverRound", "top")),
        bury=0.16, base_cut=0.10,
        # broad old joint faces (normal, depth under the support): the front and back faces, the left end, the top
        joints=[((0.0, -1.0, 0.0), 0.02), ((-0.55, -0.8, 0.25), 0.04), ((0.5, -0.8, 0.35), 0.035),
                ((0.0, 1.0, 0.0), 0.02), ((-1.0, 0.0, 0.0), 0.03), ((0.15, 0.0, 1.0), 0.025),
                ((0.9, -0.35, 0.35), 0.04)],
        r_big=0.165,                               # 13 % of the 1.27 short axis (study: river 15-30 %, sheet 10-12 %)
        flakes=dict(count=40, R=(0.15, 0.40), depth=(0.003, 0.008), lean=1.8, jitter=6.0),
        cracks=[dict(face="front", pts=[(-0.62, 1.20), (-0.70, 0.75), (-0.80, 0.15)], depth=0.16, w=0.020),
                dict(face="left", pts=[(0.05, 1.05), (-0.02, 0.55), (0.06, 0.10)], depth=0.12, w=0.016)],
        lip_r=0.034, voxel1=0.010, voxel2=0.005,
        noise=[(0.008, 1.3), (0.0035, 3.0), (0.0018, 9.0), (0.0008, 26.0)],
        wet=dict(h=0.36, soft=0.10),               # the sheet's dark lower band: bottom ~30 % (value p50 0.20 vs 0.43)
        moss=dict(top=0.62, amount=1.0), mid_voxel=0.0140, map=2048,
    ),
    "RiverLong": dict(
        prefix="SM_DKR_Rock_BoulderRiver02", kind="river", seed=7202,
        sheet="row 2, boulder 3 (sheet x 612-898): the long low one, two lobes fused at a vertical crack",
        size=dict(L=3.361, H=1.183, D=1.28),       # D: end view 1.18, plan 1.38 (17 % apart) -> geometric mean
        views=dict(front=("RiverLong", "front"), side=("RiverLong", "side"), top=("RiverLong", "top")),
        bury=0.16, base_cut=0.10,
        joints=[((0.0, -1.0, 0.0), 0.02), ((0.35, -0.9, 0.3), 0.03), ((-0.4, -0.85, 0.25), 0.03),
                ((0.0, 1.0, 0.0), 0.02), ((0.0, 0.0, 1.0), 0.02),
                ((-1.0, 0.0, 0.25), 0.04), ((1.0, 0.1, 0.2), 0.04)],
        r_big=0.17,
        flakes=dict(count=55, R=(0.15, 0.42), depth=(0.003, 0.008), lean=1.8, jitter=6.0),
        cracks=[dict(face="front", pts=[(-0.08, 1.12), (-0.11, 0.70), (-0.10, 0.12)], depth=0.20, w=0.024),
                dict(face="front", pts=[(-1.45, 0.38), (-0.85, 0.36), (-0.20, 0.40)], depth=0.06, w=0.010,
                     wander=0.016),
                dict(face="front", pts=[(-1.13, 0.80), (-1.15, 0.45), (-1.12, 0.12)], depth=0.08, w=0.011,
                     wander=0.014),
                dict(face="back", pts=[(-0.05, 1.10), (-0.02, 0.60), (-0.06, 0.12)], depth=0.18, w=0.022)],
        lip_r=0.034, voxel1=0.010, voxel2=0.0055,
        noise=[(0.008, 1.3), (0.0035, 3.0), (0.0018, 9.0), (0.0008, 26.0)],
        wet=dict(h=0.34, soft=0.10),
        moss=dict(top=0.60, amount=1.0), mid_voxel=0.0150, map=2048,
    ),
    "CliffChunk": dict(
        prefix="SM_DKR_Rock_Cliff01", kind="cliff", seed=7401,
        sheet="row 4, chunk 1 (sheet x 58-266): blocky jointed granite, stepped ledges, vertical cracks",
        size=dict(L=2.794, H=3.076, D=1.74),       # D from the side view (aspect 0.563) at the main height
        views=dict(front=("CliffChunk", "front"), side=("CliffChunk", "side"), top=("CliffChunk", "top")),
        bury=0.25, base_cut=0.10,
        # joint sets: tiers (sheeting joints, z), per tier the vertical joints (x) and one depth joint (y)
        blocks=dict(
            # columns (the vertical joint family A, x) read off the main view, one depth joint (family B, y);
            # each column draws its own bed joints (family C) in these height bands: bed joints never run across
            x_splits=[-0.92, -0.38, 0.18, 0.70], y_splits=[0.04], jit=5.0, dip_deg=4.0, min_block=0.45,
            beds=[(0.95, 1.55), (1.85, 2.45)],
            # recess (m) by the block's level in its column: the foot stands proud, upper blocks step back
            recess_by_level=[(0.0, 0.02, 0.06, 0.12), (0.06, 0.10, 0.16, 0.22), (0.12, 0.18, 0.24, 0.30)],
            open_r=0.028, chip_p=0.30, crack_p=0.8, bed_crack_p=0.6, crack_depth=(0.12, 0.25),
            crack_w=(0.012, 0.024), facets=(2, 4), facet_tilt=(16.0, 40.0), facet_depth=(0.05, 0.16)),
        flakes=dict(count=45, R=(0.12, 0.30), depth=(0.008, 0.025), lean=0.7, jitter=10.0),
        cracks=[dict(face="front", pts=[(0.30, 1.15), (0.27, 0.62), (0.31, 0.10)], depth=0.18, w=0.018),
                dict(face="front", pts=[(-0.20, 2.10), (-0.23, 1.70), (-0.20, 1.30)], depth=0.15, w=0.016),
                dict(face="front", pts=[(0.95, 3.00), (0.90, 2.55), (0.93, 2.25)], depth=0.15, w=0.016),
                dict(face="left", pts=[(-0.30, 2.80), (-0.33, 1.90), (-0.30, 1.30)], depth=0.15, w=0.018)],
        lip_r=0.008, voxel1=0.010, voxel2=0.0062,
        noise=[(0.0025, 4.0), (0.0012, 12.0), (0.0006, 30.0)],
        wet=None, moss=dict(top=0.0, amount=1.0, ledges=True), mid_voxel=0.0165, map=4096,
    ),
}
