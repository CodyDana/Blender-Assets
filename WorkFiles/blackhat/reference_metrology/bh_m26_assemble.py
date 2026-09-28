"""Stage 26: assemble reference_spec.json (machine twin of References/BlackHat/REFERENCE_SPEC.md).
Run with Blender's Python (json only):  blender -b --factory-startup --python bh_m26_assemble.py"""
import json, os
D = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/blackhat/reference_metrology"


def L(n):
    return json.load(open(os.path.join(D, n)))


cam = L('bh_s07_joint.json'); misc = L('bh_s23_misc.json'); pitch = L('bh_s24_ribpitch.json')
col = L('bh_s20_colour_light.json'); lash = L('bh_s15_lashings.json')
c = cam['2.6']; b = misc['2.6']['blender']


def row(value, tol, status='MEASURED', how='', unit=''):
    return dict(value=value, tolerance=tol, status=status, unit=unit, how=how)


spec = {
    'meta': dict(
        reference='References/BlackHat/blackhat_guide.png',
        sha256='8244fd615b6c1575c57eba5a077a18c44da52a234a44b08997f7a2b94d7ec356',
        size_px=[670, 599],
        units=('R = outer radius of the rim (outside of the rolled rim tube); D = 2R. theta = azimuth about the hat axis, '
               '0 = rim point nearest the reference camera, + toward image right. rho = horizontal radius / R on the cone '
               'surface z = H(1-rho). z = 0 is the rim outline plane (bottom of the rim tube, +/-0.02 R).'),
        instrument='Blender 5.2 headless Python + NumPy 2; scripts bh_m00..bh_m26 in this folder; stage outputs bh_s*.json',
        status_labels='MEASURED (read off the pixels), INFERRED (geometric consequence of measured rows), DESIGNED (proposal for what the reference cannot show)',
        designed_scale_note='The photo has no scale. DESIGNED default D = 600 mm (R = 300 mm); every length is given in R.',
        debug_dir='WorkFiles/blackhat/reference_metrology/debug (DEBUG, NEVER SHIP)',
        build_input_policy='The build must never read, sample, project or trace the reference pixels or the debug images; this spec is numbers and words.'),
    'camera': {
        'projection': row('perspective', 'must be perspective; orthographic fails the crown-cap check (cap arc rms 1.66 px vs 0.61 px)',
                          how='joint fit of silhouette + crown-cap edge arc over a camera-distance ladder (bh_m07)'),
        'distance_to_rim_centre_R': row(2.6, [2.2, 3.0], how='minimum of the crown-cap arc residual; band-ring level test agrees (d ~ 2.5)'),
        'elevation_deg': row(round(c['e_deg'], 2), 0.5, how='line of sight to the rim centre, above the rim plane (range 16.5-17.4 over the distance range)'),
        'focal_mm_on_36mm_sensor_670px_wide': row(round(b['focal_mm_sensor36_fitH670'], 1), [35.1, 50.3], how='f_px * 36 / 670; tied to the distance row'),
        'f_px': row(round(c['f'], 1), [652.6, 936.7]),
        'hfov_deg': row(round(b['hfov_deg'], 1), [39.4, 54.3], status='INFERRED'),
        'rim_centre_image_px': row([round(c['u0'], 2), round(c['v0'], 2)], 2.0, how='image of the rim centre = camera aim point'),
        'blender_shift_xy': row([round(b['shift_x'], 4), round(b['shift_y'], 4)], 0.005, status='INFERRED',
                                how='render 670 x 599, sensor fit HORIZONTAL, 36 mm, camera aimed at the rim centre'),
        'roll_deg': row(0.51, 0.15, unit='deg', how='image content rotated 0.51 deg CLOCKWISE (right rim tip 5.5 px lower than the left); generator angles 25.47 / 26.53 deg below horizontal'),
        'camera_position_R_camera_frame': row([0.0, -2.486, 0.761], 'scales with the distance row', status='INFERRED',
                                              how='camera on azimuth theta = 0 (-Y), looking at the rim centre'),
        'designed_world_orientation': row('hat +Z up, +X forward; knot on the wearer LEFT (+Y). Reference camera azimuth psi = +29 deg from +X toward +Y, at (2.174, 1.205, 0.761) R',
                                          'psi +/-5 deg', status='DESIGNED', how='knot measured at theta = +61 deg from the camera-facing point; psi = 90 - 61'),
        'frame_extent_px': row({'x': [1, 664], 'crown_top_y': 142.5, 'rim_bottom_y_at_centre': 433.5, 'lowest_tail_tip_y': 533, 'left_tip_y': 328, 'right_tip_y': 333.5}, 2),
        'silhouette_generator_lines': row({'left': 'y = 299.06 - 0.47641 x', 'right': 'y = -26.848 + 0.49928 x', 'virtual_apex_px': [334.03, 139.93]}, '1 px', how='bh_m02; rms 0.69 / 0.73 px'),
    },
    'lighting': {
        'backdrop': row('pure white cut-out, 0.992-0.997 stored everywhere; NO cast shadow and no contact shadow on the backdrop', 'must stay absent',
                        how='every backdrop pixel more than 8 px from the hat is >= 0.992 (bh_m01)'),
        'softness': row('large soft sources; no hard shadow edge anywhere; darkness only in crevices (rim groove 0.011-0.06 stored, black line under the cap lip)', 'qualitative'),
        'straw_brightness_vs_theta_lin_p50': row({'theta 0..16 (front)': 0.017, 'theta -28..-24': 0.054, 'theta -52..-44 (left, worn + sheen)': 0.074,
                                                  'theta -76..-64': 0.035, 'theta 72..76 (right)': 0.041},
                                                 '+/-20% each after matching exposure on the front bay',
                                                 how='unrolled cone, rho 0.55-0.93, rib columns excluded (bh_m20)'),
        'straw_profile_full': row(col['straw_theta_profile'], '+/-20%', how='(theta, p30, p50, p90) linear luminance'),
        'pattern': row('camera-facing bays darkest; both sides 2-4x brighter; left ~1.3x brighter than right. Not Lambertian from one light (1-light fit R2 0.11, 2-light 0.23): grazing sheen on the straw plus lights behind both sides',
                       'qualitative', status='INFERRED'),
        'rim_tube_lin_p50': row({'front theta 0..15': 0.012, 'theta -50': 0.049, 'theta +55..60': 0.030}, '+/-25%'),
        'specular': row('straw: soft sheen, streaky glints along strands on the lit left bays (p90 0.16 lin); cloth: matte (p90/p50 1.4)', 'qualitative', status='INFERRED'),
        'proposed_rig': row('soft key area light upper-left-behind (theta -110, elev 35); soft kicker right-behind (theta +115, elev 25, 0.6x key); weak front fill 0.2x; straw roughness ~0.5 with sheen',
                            'tune to the brightness rows', status='DESIGNED'),
    },
    'cone': {
        'H_over_R': row(round(c['H'], 3), 0.015, how='virtual apex height above the rim outline plane'),
        'D_over_H': row(round(2 / c['H'], 2), 0.13, status='INFERRED'),
        'slope_from_horizontal_deg': row(26.0, 0.8, status='INFERRED'),
        'apex_full_angle_deg': row(128.0, 1.6, status='INFERRED'),
        'profile': row('straight generators (silhouette rms 0.7 px, quadratic term negligible); no sag or flare near the rim', '<= 0.005 R deviation from straight'),
        'crown_cap_radius_over_R': row(round(c['rc'], 4), 0.008, how='cap lower-edge arc (top of its black shadow line) fitted as a circle on the cone (bh_m07)'),
        'crown_cap_profile': row('low conical lid, slope ~20 deg (flatter than the 26 deg cone); top 0.005 R below the virtual apex; lip thickness / overhang ~0.008 R casting a black 1.5-2 px line; faint radial ribs on the lid meet at a point, no finial',
                                 'slope +/-5 deg; lip 0.004-0.012 R', status='INFERRED'),
    },
    'ribs': {
        'primary_count': row(13, 'exactly 13', status='INFERRED',
                             how='7 visible ribs span 167 deg, mean pitch 27.84 deg (N = 12.93); forced N=13 rms 2.16 deg vs N=12 rms 4.82 deg at the best camera; N=12 becomes the better even-pitch fit only for d >= 2.9 R and matches 30 deg exactly at d = 3.5 R, where the cap residual is 21% worse (bh_m24)'),
        'visible_azimuths_at_rim_deg': row(pitch['2.6']['ribs'], {'-82 and +85': 4, 'others': 2}, how='rib meets the rim, unrolled cone (bh_m16), d = 2.6 camera'),
        'visible_gaps_deg': row([27.5, 31.0, 31.1, 22.4, 28.0, 27.0], 2, how='keep them; do not regularise the visible arc'),
        'far_side_azimuths_deg': row([112.7, 140.3, 167.9, 195.4, 223.0, 250.6], 3, status='DESIGNED', how='6 more ribs evenly filling +85 -> +278 deg (pitch 27.6)'),
        'diameter_over_R': row(0.011, 0.003, how='dark flank to dark flank 0.9 deg at rho 0.78; bright core 0.5 deg'),
        'relief': row('round rod lying ON the skin with a dark shadow flank each side (~0.3 deg each)', 'relief 0.6-1.0 x diameter', status='INFERRED'),
        'construction': row('twisted cord / split-cane rod; rope twist clearly visible on the theta = +7.6 rib (pitch ~1.6 x diameter); runs from under the cap lip to under the rim binding cord', 'qualitative'),
        'fine_radial_seams': row('thin 1 px dark radial seams in the weave at irregular 3-8 deg spacing; texture only, no relief', 'texture', how='theta spectrum peaks 3.8-7.7 deg'),
    },
    'weave': {
        'strand_direction': row('circumferential flat strands (parallel to the rim); radial fine seams break them into brick-like runs', 'qualitative'),
        'strand_width_over_R': row(0.006, 0.002, how='~2 px at the front, slant scale 328 px/R'),
        'strand_width_over_D': row(0.003, 0.001, status='INFERRED'),
        'course_period_over_R_slant': row(0.031, 0.008, how='autocorrelation along rho peaks at 0.0275 rho'),
        'weave_meets_rib': row('strands run continuously UNDER each rib; no gap or break at the rib; shadow flanks either side', 'qualitative'),
        'weave_at_edges': row('disappears under the cap lip at the top and under the binding cord / rim tube at the bottom', 'qualitative'),
    },
    'rim': {
        'tube_diameter_over_R': row(0.044, 0.006, how='front: bottom outline 433.5 px to the dark groove 412 px = 21.5 px at 484.6 px/R'),
        'binding_cord_diameter_over_R': row(0.005, 0.002, how='thin light cord on the inner-top edge of the tube, above the groove'),
        'groove': row('dark crevice between binding cord and tube, stored 0.011-0.06', 'must read black'),
        'lashing_count': row(26, 'exactly 2 per rib bay', status='INFERRED', how='a lashing at every primary rib end plus one inside every bay, in all 5 measurable bays'),
        'lashing_visible_azimuths_deg': row({'at_ribs': [-53.7, -22.1, 7.65, 30.0, 58.35], 'in_bays': [-67.0, -32.5, -9.0, 17.1, 42.75]},
                                            {'|theta| < 45': 1.5, 'sides': 4}, how='theta-rectified rim face (bh_m15); +30.0 is hidden under tail A, inferred from its rib'),
        'lashing_detections_raw': row(lash, 'n/a', how='all peaks incl. tail edges (27.65, 35.2) and weak tip detections'),
        'bay_lashing_fraction_of_bay': row([0.55, 0.68, 0.46, 0.42, 0.45], 0.08, how='(lashing - previous rib) / bay width'),
        'lashing_width_over_R': row(0.038, 0.005, how='2.0-2.4 deg at R'),
        'wraps_per_lashing': row(3, 'exactly 3', how='3x-8x crops'),
        'wrap_cord_diameter_over_R': row(0.012, 0.003, status='INFERRED'),
        'lashing_extent': row('wraps cover the tube and the binding cord and reach ~0.015 R onto the skin edge', 0.005),
    },
    'band': {
        'ring_centre_rho': row(0.365, 0.015, how='back-projected band line at theta -80..0; horizontal within +/-0.01 rho'),
        'ring_height_z_over_H': row(0.635, 0.02, status='INFERRED'),
        'gap_below_cap_edge_R_slant': row(0.29, 0.03, status='INFERRED'),
        'width_over_R': row({'theta < -20 (twisted, cord-like)': 0.010, 'theta 0': 0.04, 'theta +30 (fanned toward knot)': 0.11},
                            {'cord': 0.003, 'theta 0': 0.01, 'theta 30': 0.02}),
        'flat_cloth_width_over_R': row(0.10, 0.02, status='INFERRED', how='fanned width near the knot and the tail widths'),
        'wrap': row('one turn round the cone lying on it and passing OVER the ribs; progressively twisted into a narrow roll away from the knot; its lower edge dips to rho 0.51 just before the knot', 'qualitative'),
        'knot_theta_deg': row(61, 5, how='back-projected knot centre image (462, 222); 57-64 over the distance range'),
        'knot_rho': row(0.43, 0.04),
        'knot_size_over_R': row([0.08, 0.09], 0.02, how='28 x 35 px at ~370 px/R'),
        'knot_shape': row('compact gathered knot (square-knot bulk) on the band lower edge; the band fans into 3-4 fold lines entering it', 'qualitative'),
    },
    'tails': {
        'count': row(2, 'exactly 2'),
        'leave_knot_at': row({'theta': 64, 'rho': 0.51}, {'theta': 5, 'rho': 0.04}),
        'cross_rim_theta_deg': row({'A': 31, 'B': 40}, 4),
        'order': row('A (inner, nearer the camera-facing side) lies over B near the knot', 'qualitative'),
        'width_over_R': row({'A': [0.062, 0.075], 'B': [0.084, 0.091]}, 0.01, how='below-rim widths 28-34 px (A), 36-39 px (B) at 452 / 430 px/R'),
        'length_knot_to_tip_over_R': row({'A': 0.99, 'B': 0.96}, 0.10, status='INFERRED', how='on-cone path + straight fall'),
        'length_over_D': row(0.49, 0.05, status='INFERRED'),
        'hang_below_rim_over_R': row({'A': 0.30, 'B': 0.32}, 0.04),
        'hang_direction': row('falls 12-18 deg off vertical, outward (image right, away from the cone)', 5, status='INFERRED'),
        'tip_image_px': row({'A': [592, 533], 'B': [643, 520]}, 4),
        'twist_drape': row('A is turned ~60-90 deg (edge toward the camera, 17 px wide) for ~0.15 R after the knot, then lies flat on the cone and over the rim; B stays face-on and stands slightly off the cone near the rim (dark air gap)', 'qualitative'),
        'torn_end': row('each end is a long tapering diagonal tear finishing in a point on the OUTER (image-right) edge: A tear 0.18 R long; B 0.25 R long with one deep notch splitting off a narrow sliver; ragged teeth 0.007-0.02 R',
                        {'tear length': 0.04, 'teeth': 0.005}),
        'cloth_thickness_over_R': row(0.004, '0.003-0.005 (not resolvable, <= 1.5 px)', status='DESIGNED'),
    },
    'colour': {
        'straw_albedo_lin_lum': row(0.042, 0.015, status='INFERRED', how='unworn straw mean 0.035 lin over the visible arc / mean irradiance ~0.8 (sides lit near full, front ~0.4)'),
        'straw_albedo_srgb': row([0.233, 0.225, 0.224], 0.03, status='INFERRED', how='albedo lum x chroma (0.350, 0.327, 0.323); #3B3939'),
        'straw_chroma_hue_sat': row({'chroma': [0.350, 0.327, 0.323], 'hue_deg': 9, 'sat': 0.04}, {'r': 0.008, 'hue_deg': 8, 'sat': 0.02}),
        'rim_and_lashing_albedo_srgb': row([0.241, 0.223, 0.213], 0.03, status='INFERRED', how='warmer: chroma (0.375, 0.324, 0.300), hue 18-21 deg, sat 0.10-0.13; #3D3936'),
        'cloth_albedo_lin_lum': row(0.030, 0.010, status='INFERRED', how='tails 0.012-0.017 and band 0.010-0.032 lin in dimmer / vertical positions; ~0.72x straw'),
        'cloth_albedo_srgb': row([0.195, 0.188, 0.189], 0.03, status='INFERRED', how='chroma (0.348, 0.324, 0.328), neutral, sat 0.04; #323030'),
        'wear_fleck_srgb_observed': row([0.373, 0.362, 0.358], 0.04, how='pixels > 1.8x the local p30; neutral light grey; lin lum p50 0.082, p90 0.20'),
        'wear_fleck_albedo_lin_lum': row(0.10, [0.08, 0.20], status='INFERRED'),
        'default_tints_for_sidecar': row({'straw_lin': [0.0443, 0.0414, 0.0410], 'cloth_lin': [0.0316, 0.0294, 0.0297], 'rim_lin': [0.0473, 0.0409, 0.0378]},
                                         '+/-25%', status='INFERRED', how='albedo lum x chroma / (chroma . Rec709 luma)'),
        'region_stats': row(col, 'n/a', how='observed (lighting included), bh_m20'),
    },
    'wear': {
        'coverage_visible_straw': row(0.15, 0.04, how='fraction of pixels > 1.8x the local p30 (bh_m21)'),
        'zones': row({'left theta -62..-25, rho .45-.97': 0.20, 'front theta -5..16': 0.07, 'streaks theta -18..-5, rho .70-.82': 0.12, 'right theta 72..95': 0.18}, 0.05),
        'fleck_shape': row('short streaks ALONG the circumferential strands, 0.5-3 deg long, 0.003-0.006 R tall; lighter strand tops, not holes', 'qualitative'),
        'dark_smudge': row('one broad darker smudge at theta -45..-35, rho 0.55-0.90, ~15% darker than its surround', 0.1),
        'rim_wear': row('light scuffs on the front face of the rim tube (image x 280-330 and 360-380); rim p90/p50 = 2.4', 'qualitative'),
        'not_present': row('no holes, no tears in the straw, no broken ribs, no missing lashings, no chin cord, no lining, no decals, no colour', 'must stay absent'),
    },
    'cannot_see_DESIGNED': {
        'underside': row('plain inside of the woven skin (same circumferential strands), skin 0.006 R thick; ribs only on the outside; rim tube round all the way under; lashings wrap fully round the tube; NO headband ring, lining or chin cord (the reference never shows the underside)',
                         'n/a', status='DESIGNED'),
        'far_side': row('6 more primary ribs at 27.6 deg pitch; a lashing at every rib + one per bay (26 total); band continues round the back as the narrow twisted roll at rho 0.365; wear flecks ~10% coverage; no new damage',
                        'n/a', status='DESIGNED'),
        'head_socket': row('Empty on the axis at the inner crown seat: a 57 cm head (sphere r = 9.07 cm) inscribed in the inner cone (half-angle 64 deg) has its centre 1.113 r below the inner apex, so the skull top sits 0.113 r = 1.03 cm below the inner apex; +Z up out of the crown, +X forward',
                           'n/a', status='DESIGNED'),
        'real_size': row('D = 600 mm, H = 146 mm, rib 3.3 mm, rim tube 13 mm, lashing cord 3.6 mm, band cloth 30 mm, tails ~295 mm', 'n/a', status='DESIGNED'),
    },
    'acceptance_checks': [
        'Render the SHIPPED asset from the camera rows (670 x 599) and run bh_m01/bh_m02 on it: generator lines within 1 px of the rows, tips within 2 px, rim bottom within 2 px.',
        'Crown-cap arc (bh_m07 trace) within 1 px of the reference trace; cap edge ends x 298 / 370 within 2 px.',
        'Unroll with bh_m16 using the SAME camera: ribs at the listed azimuths, lashings (bh_m15) at the listed azimuths, 3 wraps each.',
        'Band ring at rho 0.365, knot at theta 61, tails crossing the rim at 31 / 40 and tips within 6 px of (592, 533) / (643, 520).',
        'Colour/brightness rows via bh_m20 on the render after matching exposure on the front bay.',
        'LOOK: side-by-side with the reference; if it looks different it fails even when every number passes.',
    ],
}
json.dump(spec, open(os.path.join(D, 'reference_spec.json'), 'w'), indent=1)
print('BHSPEC ok', len(json.dumps(spec)))
