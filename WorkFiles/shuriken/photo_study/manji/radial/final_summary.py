import json, os, sys, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
P = C.OUT + "/"
R1 = json.load(open(P+'measure_raw.json')); R2 = json.load(open(P+'measure2.json')); R3 = json.load(open(P+'measure3.json')); QA = json.load(open(P+'qa_symmetry.json'))
S = R3['summary_ratios']; SPAN = R1['SPAN_px']
def m(v): return sum(v)/len(v)
print('centre', [round(x,2) for x in R1['centroid_xy_px']], 'span', round(SPAN,2), 'tips r', [round(x,1) for x in R1['tips_radius_px']])
print('area', R1['area_px'], 'perimeter', round(R1['perimeter_px'],1), 'aniso', round(R1['second_moment_anisotropy'],5))
print('fft', R1['fft_dominant_harmonic'], R1['fft_top5_harmonics'], round(R1['fft_amp_ratio_k4_over_next'],2))
axes = [a['axis_deg'] for a in R1['arms']]; tips = R1['tips_angle_deg']
off = [(tips[i]-axes[i])%360 for i in range(4)]
print('axes', [round(x,2) for x in axes], 'tip offset', [round(x,2) for x in off], 'mean', round(m(off),2), 'sd', round(st.stdev(off),3))
hs = QA['hookside']; tr = QA['trailing']
lit_hs=[v['dist'] for v in hs['values'] if v['lighting']=='lit']; lit_tr=[v['dist'] for v in tr['values'] if v['lighting']=='lit']
all_hs=[v['dist'] for v in hs['values']]; all_tr=[v['dist'] for v in tr['values']]
print('corridor width lit %.2f (%.4f span) all %.2f (%.4f span)' % (m(lit_hs)+m(lit_tr), (m(lit_hs)+m(lit_tr))/SPAN, m(all_hs)+m(all_tr), (m(all_hs)+m(all_tr))/SPAN))
print('central square side', [round(v,1) for v in R1['junction_vertex_adjacent_dist_px']], 'ratio %.4f sd %.4f' % (m(R1['junction_vertex_adjacent_dist_px'])/SPAN, st.stdev(R1['junction_vertex_adjacent_dist_px'])/SPAN))
print('junction vertex radius', [round(v,1) for v in R1['junction_vertex_radius_px']])
for k in ['arm_width_at_root_ratio','arm_width_at_hookroot_ratio','arm_width_taper_total_deg','hook_len_beyond_arm_ratio','hook_len_from_centreline_ratio','hook_len_from_trailing_edge_ratio','hook_root_width_ratio','hook_root_u_ratio','arm_outer_end_u_ratio','tip_u_ratio','tip_v_ratio','hook_inner_edge_angle_to_arm_axis_deg','tip_angle_deg_window20_300','tip_angle_deg_window15_150','tip_angle_deg_window10_80','tip_chord_angle_deg','tip_width_3px_back','tip_width_10px_back','outer_edge_arc_radius_ratio','junction_radius_ratio','corner_angle_junction_deg','corner_angle_hookroot_deg','corner_angle_armend_deg','tip_angle_spacing_deg','tip_radius_px']:
    v = S[k]; print('%-40s %9.4f +- %.4f  [%.4f, %.4f] n=%d' % (k, v['mean'], v['sd'], v['min'], v['max'], v['n']))
print('bbox', [round(x,4) for x in S['bbox_in_arm_frame_ratio']], 'across', [round(x,4) for x in S['across_arms_centreline_ratio']], 'area %.4f perim %.3f' % (S['area_ratio_span2'], S['perimeter_ratio']))
cr = json.load(open(P+'corner_radius.json'))
d = {}
for c in cr: d.setdefault(c['kind'], []).append(round(c['radius_px'],1))
print('curvature radii', d)
c2 = json.load(open(P+'corner_radius2.json'))
d2 = {}
for c in c2['corners']: d2.setdefault(c['kind'], []).append(round(c['r_D25'],1))
print('sagitta radii (D25, x1.85 calib)', {k:[round(x*1.85,1) for x in v] for k,v in d2.items()})
b = R3['bevel_bands']
for q in (1,2):
    stt = b['q%d_outer'%q]['stations']
    print('bevel q%d outer len %.0f' % (q, b['q%d_outer'%q]['edge_len']), [(round(s['s_frac'],2), s['band_width_px'], round(s['thickness_px'])) for s in stt[:14]])
print('holes', R1['enclosed_background_components_px'], 'bright interior spots', R1['interior_bright_spots_count'], R1['interior_bright_spots_largest_px'], 'interior lum', [round(x,3) for x in R1['interior_lum_p01_p50_p99']])
print('hand', [(round(hh['arm_axis_deg'],2), round(hh['tip_v_on_ccw_side'],1), hh['hookside_edge_on_ccw_side']) for hh in R1['handedness_per_arm']])
print('asym', [(round(a['tip_deg'],1), round(a['r_cw_minus3']), round(a['r_ccw_plus3'])) for a in R1['r_theta_asymmetry_at_tips']])
seg5 = json.load(open(P+'seg5.json')); print('seg5', {k:v for k,v in seg5.items() if k!='column_scan' and k!='row_scan'}, seg5['column_scan'], seg5['row_scan'])
