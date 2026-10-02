"""Pilot 2 rock plans (owner-approved METHOD CHANGE after pilot 1 failed 3/10). Sizes, figure scale and traced
outlines are pilot 1's measurements of the owner's sheet (WorkFiles/dojo/build/rocks/ref_measure.json); the forms
are new: river boulders are corestones (Scripts/stone/rock_corestone.py) clamped by the traced visual hull, the cliff
chunk is a true fracture of a sheared mass (Scripts/stone/rock_fracture.py).

Frame: x = length (the sheet's main view looks along +y), y = depth, z up, ground z = 0; the mesh continues below
grade as a buried skirt (study 3.10).

Silhouette reads used here (sheet masks, pilot/refcrops/mask_*.npy, width per row top -> bottom and top profile):
- RiverRound front: widest (0.98 W) at ~0.22 H above grade, width 0.60 / 0.76 / 0.85 / 0.92 at 7/8, 6/8, 5/8, 4/8
  of H, which an ellipse with its equator at 0.22-0.25 H fits within 0.03; crown at ~40 % of the length.
- RiverLong front: two lobes; the left 45 % stands 0.72-0.85 H, the right peaks at 0.98-0.99 H at 60-80 % of the
  length; the vertical crack at ~46 % of the length (x ~ -0.13 m).
"""
from __future__ import annotations

PLANS = {
    "RiverRound": dict(
        prefix="SM_DKR_Rock_BoulderRiver01", kind="river", seed=7111,
        sheet="row 2, boulder 2 (sheet x 334-506): the rounded dome",
        size=dict(L=2.077, H=1.359, D=1.27),
        views=dict(front=("RiverRound", "front"), side=("RiverRound", "side"), top=("RiverRound", "top")),
        bury=0.20, base_cut=0.10, clamp=0.035,
        lobes=[dict(centre=(0.0, 0.0), a=1.06, b=0.655, ze=0.31, c_up=1.08, c_dn=0.55, p_xy=2.05, p_z=2.3,
                    crown=(-0.08, -0.03), under=0.16, lumps=[(0.030, 1.5), (0.016, 3.2)])],
        joints=[((0.0, -1.0, 0.12), 0.09), ((0.0, 1.0, 0.08), 0.08), ((-1.0, 0.05, 0.25), 0.08),
                ((-0.55, -0.35, 0.76), 0.06), ((0.72, -0.25, 0.62), 0.06), ((0.95, 0.15, 0.1), 0.05)],
        facets=dict(count=16, depth=(0.03, 0.08)),
        facets2=dict(count=40, depth=(0.012, 0.035), r=0.04),
        r_open=0.18,                                  # 16 % of the 1.27 short axis (study: river 15-30 %)
        cracks=[dict(face="front", pts=[(-0.52, 1.10), (-0.60, 0.80), (-0.66, 0.42)], depth=0.06, w=0.010,
                     wander=0.010),
                dict(face="front", pts=[(0.30, 0.85), (0.40, 0.62), (0.43, 0.42)], depth=0.04, w=0.007,
                     wander=0.012)],
        lip_r=0.02, voxel1=0.010, voxel2=0.005,
        meso=[(0.035, 2.0), (0.016, 4.5), (0.006, 11.0)],
        wet=dict(h=0.42, warp=0.20, soft=0.24, splash=0.55),
        moss=dict(z_lo=0.66, z_hi=0.82, brk_lo=0.50, brk_hi=0.62, crevice=0.3), mid_voxel=0.0135, map=2048,
    ),
    "RiverLong": dict(
        prefix="SM_DKR_Rock_BoulderRiver02", kind="river", seed=7212,
        sheet="row 2, boulder 3 (sheet x 612-898): the long low one, two lobes fused at a vertical crack",
        size=dict(L=3.361, H=1.183, D=1.28),
        views=dict(front=("RiverLong", "front"), side=("RiverLong", "side"), top=("RiverLong", "top")),
        bury=0.20, base_cut=0.10, clamp=0.035,
        lobes=[dict(centre=(0.0, 0.0), a=1.72, b=0.655, ze=0.30, c_up=0.90, c_dn=0.52, p_xy=2.25, p_z=2.0,
                    crown=(0.42, -0.03), under=0.16, tilt_deg=0.0, lumps=[(0.030, 1.5), (0.016, 3.2)])],
        fuse_r=0.10,
        joints=[((0.0, -1.0, 0.10), 0.08), ((0.0, 1.0, 0.06), 0.07), ((-1.0, 0.0, 0.3), 0.08),
                ((1.0, 0.08, 0.25), 0.07), ((0.15, -0.3, 0.95), 0.05), ((-0.45, -0.45, 0.75), 0.05)],
        facets=dict(count=24, depth=(0.03, 0.08)),
        facets2=dict(count=56, depth=(0.012, 0.035), r=0.04),
        r_open=0.18,
        cracks=[dict(face="front", pts=[(-0.13, 1.02), (-0.16, 0.62), (-0.12, 0.14)], depth=0.12, w=0.014,
                     wander=0.010),
                dict(face="back", pts=[(-0.10, 0.98), (-0.08, 0.55), (-0.11, 0.14)], depth=0.10, w=0.012,
                     wander=0.010),
                dict(face="top", pts=[(-0.13, -0.50), (-0.15, 0.0), (-0.12, 0.50)], depth=0.10, w=0.012,
                     wander=0.010),
                dict(face="front", pts=[(-1.35, 0.45), (-1.0, 0.40), (-0.55, 0.44)], depth=0.03, w=0.006,
                     wander=0.006)],
        lip_r=0.02, voxel1=0.010, voxel2=0.0055,
        meso=[(0.035, 2.0), (0.016, 4.5), (0.006, 11.0)],
        wet=dict(h=0.44, warp=0.20, soft=0.24, splash=0.55),
        moss=dict(z_lo=0.60, z_hi=0.76, brk_lo=0.44, brk_hi=0.56, crevice=0.4), mid_voxel=0.0145, map=2048,
    ),
    "CliffChunk": dict(
        prefix="SM_DKR_Rock_Cliff01", kind="cliff", seed=7411,
        sheet="row 4, chunk 1 (sheet x 58-266): angular multi-direction fracture, stepped ledges",
        size=dict(L=2.794, H=3.076, D=1.74),
        views=dict(front=("CliffChunk", "front"), side=("CliffChunk", "side"), top=("CliffChunk", "top")),
        bury=0.25, base_cut=0.10,
        fracture=dict(yaw_deg=8.0, lean_deg=5.0, lean_dir_deg=35.0, col_w=0.56, row_d=0.85, levels=(2, 4),
                      jit=0.12, zstretch=1.8, tilt=8.0, neigh=3.5, recess=(-0.10, 0.30), recess_jit=0.26,
                      gap=0.012, joint_depth=(0.14, 0.26), facets=(2, 3), facet_tilt=(15.0, 38.0),
                      facet_depth=(0.05, 0.20), open_r=0.015, recess_step=0.04),
        chips=dict(count=120, size=(0.025, 0.07)), rubble=dict(count=9, size=(0.15, 0.36)),
        flakes=dict(count=40, R=(0.08, 0.22), depth=(0.006, 0.02), lean=0.7, jitter=10.0),
        lip_r=0.006, voxel1=0.012, voxel2=0.0062,
        meso=[(0.0025, 4.0), (0.0012, 12.0)],
        wet=None, damp_h=0.35,
        moss=dict(z_lo=None, ledges=True, nz_lo=0.45, nz_hi=0.8, brk_lo=0.36, brk_hi=0.50, crevice=0.7),
        mid_voxel=0.019, map=4096, uv="smart",
    ),
}


# ----------------------------------------------------------------------------------------------- pilot 2 fix 1
# Judge round on pilot 2 (4/10): forms. River rocks -> faceted water-worn blocks (rock_corestone.broad_facet_cuts +
# one big opening; joints split the mass into stepped lobes with rounded lips, no slots). Cliff -> joint-set
# fracture (rock_fracture.jointset_cells: beds every 0.4-1.2 m + two vertical sets, cuboid blocks, crisp 2.2 cm
# arrises, benches). Facet azimuths: 0 = the sheet's main view (-y), +90 = the +x end, 180 = back; elevation up.
# The designs follow the sheet crops (looked at, 2026-10-01): RiverRound has a broad dark plane on its left
# front, two front planes meeting at a soft ridge under a diagonal joint, a crowned top; RiverLong is three lobes
# (left ~17 %, middle to ~42 %, the tall right dome), the joints near-vertical and curving, the lobes stepping up
# to the right.
_RR_FACETS = [(-20, 12, 0.13), (25, 16, 0.11), (0, 46, 0.11), (-72, 8, 0.17), (-52, 44, 0.12), (80, 10, 0.12),
              (62, 50, 0.10), (-15, 78, 0.05), (40, 70, 0.05), (180, 14, 0.12), (150, 44, 0.10), (-145, 40, 0.11),
              (118, 16, 0.10), (-115, 18, 0.10), (0, -35, 0.07), (90, -30, 0.06), (-90, -30, 0.06),
              (180, -35, 0.07)]
_RL_FACETS = [(-12, 14, 0.12), (14, 20, 0.12), (2, 50, 0.12), (-25, 80, 0.06), (30, 74, 0.06), (-86, 14, 0.17),
              (86, 20, 0.15), (-70, 48, 0.13), (74, 50, 0.12), (180, 18, 0.12), (168, 50, 0.11), (-150, 30, 0.12),
              (140, 30, 0.12), (40, 12, 0.10), (-45, 10, 0.10), (0, -35, 0.07), (180, -35, 0.07), (90, -30, 0.06),
              (-90, -30, 0.06)]

PLANS["RiverRound"].update(
    method="faceted", clamp=0.012, r_open=0.13, lip_open=0.030, core=0.045, joint_gap=0.004, joint_close=0.008,
    lobes=[dict(centre=(0.0, 0.0), a=1.10, b=0.69, ze=0.31, c_up=1.12, c_dn=0.55, p_xy=2.5, p_z=2.5,
                crown=(-0.08, -0.03), under=0.16, lumps=[(0.014, 1.5), (0.008, 3.2)])],
    facets_broad=_RR_FACETS,
    split=[dict(p0=(0.02, 0.0, 0.85), n=(0.83, 0.10, -0.55), amp=0.04, freq=1.3, meander=(0.03, 0.8),
                zone=((-0.05, -0.55, 0.95), 0.62))],
    lobe_steps=[0.02, 0.0],
    facets2=dict(count=18, depth=(0.010, 0.026), r=0.035),
    cracks=[], meso=[(0.010, 2.0), (0.006, 5.0), (0.003, 12.0)],
    wet=dict(h=0.30, warp=0.12, soft=0.10, splash=0.0, waterline=0.6),
)
PLANS["RiverLong"].update(
    method="faceted", clamp=0.012, r_open=0.15, lip_open=0.045, core=0.08, joint_gap=0.008, joint_close=0.010,
    lobes=[dict(centre=(0.0, 0.0), a=1.76, b=0.69, ze=0.30, c_up=0.95, c_dn=0.52, p_xy=2.6, p_z=2.3,
                crown=(0.42, -0.03), under=0.16, tilt_deg=0.0, lumps=[(0.014, 1.5), (0.008, 3.2)])],
    facets_broad=_RL_FACETS,
    split=[dict(p0=(-1.10, 0.0, 0.5), n=(1.0, 0.25, 0.12), amp=0.035, freq=1.2, meander=(0.025, 0.6)),
           dict(p0=(-0.25, 0.0, 0.5), n=(1.0, -0.22, -0.28), amp=0.04, freq=1.0, meander=(0.03, 0.5))],
    lobe_steps=[0.04, 0.022, 0.0],
    facets2=dict(count=26, depth=(0.010, 0.026), r=0.035),
    cracks=[], meso=[(0.010, 2.0), (0.006, 5.0), (0.003, 12.0)],
    wet=dict(h=0.32, warp=0.12, soft=0.10, splash=0.0, waterline=0.6),
)
PLANS["CliffChunk"].update(
    method="jointset",
    jointset=dict(columns=True, yaw_deg=6.0, first_bed=(0.30, 0.95), bed_h=(0.40, 1.20), bed_tilt=9.0,
                  u_sp=(0.40, 0.85), v_sp=(0.45, 0.95), vjit=7.0, recess=(-0.14, 0.55), recess_jit=0.46,
                  col_jit=0.36, bench_base=0.08, bench_rise=0.75, recess_step=0.03, gap=0.004,
                  joint_depth=(0.05, 0.12), face_tilt=(14.0, 32.0), face_cut=(0.08, 0.24), chamfer_p=0.5,
                  chamfer_depth=(0.08, 0.24), side_chamfer_p=0.5, tilted_top_p=0.35, top_drop=(0.05, 0.30),
                  facets=(2, 3), facet_tilt=(15.0, 35.0), facet_depth=(0.08, 0.22),
                  open_r=0.02),
    chips=dict(count=70, size=(0.02, 0.06)), rubble=dict(count=8, size=(0.14, 0.34)),
    flakes=dict(count=0, R=(0.08, 0.2), depth=(0.006, 0.018), lean=0.7, jitter=10.0),   # round 3: square pockets
    lip_r=0.005,
)

# moss as a crest band with satellites (delta 7; the sheet's row 2 crest moss, checked)
PLANS["RiverRound"]["moss"] = dict(PLANS["RiverRound"]["moss"], ridge=0.22)
PLANS["RiverLong"]["moss"] = dict(PLANS["RiverLong"]["moss"], ridge=0.16)
# the box-direction charts stretched the grain on RiverRound's left face (pilot2_f1 test render): planar islands
# tried: smart project 40 deg (bake-margin bleed on its many island borders at 2K) and 26-direction charts (seam
# slits); kept: pilot 2's 6-direction charts
PLANS["RiverRound"].pop("uv", None)
PLANS["RiverLong"].pop("uv", None)
PLANS["RiverLong"]["moss"] = dict(PLANS["RiverLong"]["moss"], ridge=0.22)
