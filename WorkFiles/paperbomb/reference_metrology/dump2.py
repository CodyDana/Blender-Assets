# -*- coding: utf-8 -*-
import json, io
d=json.load(io.open(r'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/reference_metrology/layout.json',encoding='utf-8'))
for s in ('V1','V2','OURS'):
    b=d[s]['diamonds']['beads_on_rules']
    print('==',s,'beads on rules: %d =='%len(b))
    for it in b:
        print('   %-6s at %6.1fmm along  len=%4.2fmm  maxW=%4.2fmm (%.1fx rule)'%(
            it['on_rule'],it['pos_along_rule']['mm'],it['length_along_rule']['mm'],it['max_width']['mm'],it['width_over_rule_med']))
print()
for s in ('V1','V2','OURS'):
    print('==',s,'flourishes ==')
    for c,v in d[s]['corner_flourishes'].items():
        bb=v['bbox']
        print('  %s box %5.2fx%5.2fmm at (%5.2f,%6.2f)  ink=%5.1fmm2 parts=%d  strokeW med=%.2f p90=%.2f  runH=%5.2f runV=%5.2f outboardX=%5.2f outboardY=%5.2f reachMax=%5.2f'%(
          c,bb['w']['mm'],bb['h']['mm'],bb['x0']['mm'],bb['y0']['mm'],v['ink_mm2'],v['n_parts'],
          v['stroke_w_med_h']['mm'],v['stroke_w_p90_h']['mm'],v['run_along_horiz_rule']['mm'],v['run_along_vert_rule']['mm'],
          v['outboard_of_side_rule']['mm'],v['outboard_of_horiz_rule']['mm'],v['reach_from_rule_corner_max']['mm']))
print()
print('-- OURS clear space --')
for k2,v in d['OURS']['clear_space'].items():
    print('    %-52s %s'%(k2, ('%.3f'%v) if isinstance(v,float) else '%.2f mm'%v['mm']))
print()
print('-- key ratios --')
for s in ('V1','V2','OURS'):
    cs=d[s]['clear_space']
    print(s, 'bao/ringD w=%.3f diag=%.3f  bao-ring dx=%.2f dy=%.2f'%(
      cs.get('bao_width_over_ring_outer_diameter',0),cs.get('bao_bbox_diag_over_ring_outer_diameter',0),
      cs['bao_centroid_minus_ring_centre_x']['mm'],cs['bao_centroid_minus_ring_centre_y']['mm']))
