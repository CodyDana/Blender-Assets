# -*- coding: utf-8 -*-
import json, io
P=r'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/reference_metrology/layout.json'
d=json.load(io.open(P,encoding='utf-8'))
keys=['flame_emblem','red_ring','centre_char_bao','col_upper_left_hi_ton_jutsu','col_upper_right_baku_en_jin','col_lower_right_shou_jin','col_lower_centre_shun_gou','seal_box_large_left','seal_box_small_right']
print('%-30s %-27s %-27s %-27s'%('element  fW/fH box','V1','V2','OURS'))
for kk in keys:
    row=[]
    for s in ('V1','V2','OURS'):
        e=d[s]['elements'].get(kk)
        row.append('--' if not e else 'x%.3f-%.3f y%.3f-%.3f'%(e['x0']['fW'],e['x1']['fW'],e['y0']['fH'],e['y1']['fH']))
    print('%-30s %-27s %-27s %-27s'%(kk,row[0],row[1],row[2]))
print()
print('%-30s %-27s %-27s %-27s'%('element  mm w x h @ centroid','V1','V2','OURS'))
for kk in keys:
    row=[]
    for s in ('V1','V2','OURS'):
        e=d[s]['elements'].get(kk)
        row.append('--' if not e else '%5.1fx%5.1f @%5.1f,%6.1f'%(e['w']['mm'],e['h']['mm'],e['centroid_x']['mm'],e['centroid_y']['mm']))
    print('%-30s %-27s %-27s %-27s'%(kk,row[0],row[1],row[2]))
print()
for s in ('V1','V2','OURS'):
    g=d[s]['elements'].get('red_ring',{}).get('geometry')
    if g: print(s,'RING c=(%.2f,%.2f)mm  R_out med=%.2f p10=%.2f p90=%.2f min=%.2f max=%.2f sd=%.2f  R_in=%.2f  thick med=%.2f p10=%.2f p90=%.2f max=%.2f  cov=%.2f ellip=%.1f%%@%.0fdeg fill=%.2f arcs=%s'%(
        g['centre_x']['mm'],g['centre_y']['mm'],g['outer_r_med']['mm'],g['outer_r_p10']['mm'],g['outer_r_p90']['mm'],
        g['outer_r_min']['mm'],g['outer_r_max']['mm'],g['outer_r_rms_raggedness']['mm'],g['inner_r_med']['mm'],
        g['thickness_med']['mm'],g['thickness_p10']['mm'],g['thickness_p90']['mm'],g['thickness_max']['mm'],
        g['angular_coverage'],g['ellipse_ellipticity_pct'],g['ellipse_major_axis_deg'],g['ink_fill_of_annulus'],
        d[s]['elements']['red_ring'].get('n_arcs')))
print()
for s in ('V1','V2','OURS'):
    print('--',s,'column parts (mm) --')
    for kk in keys[3:7]:
        e=d[s]['elements'].get(kk)
        if e and 'parts' in e:
            print('   %-30s'%kk, ' | '.join('%.1fx%.1f@%.1f,%.1f'%(p['bbox']['w']['mm'],p['bbox']['h']['mm'],p['bbox']['cx']['mm'],p['bbox']['cy']['mm']) for p in e['parts']))
print()
for s in ('V1','V2','OURS'):
    e=d[s]['elements']
    for kk in ('seal_box_large_left','seal_box_small_right'):
        if kk in e:
            print('%-5s %-22s %s knockout=%.2f strokeW med=%.2f p90=%.2f mm'%(s,kk,e[kk].get('style'),e[kk].get('knockout_frac_of_bbox',0),e[kk]['border_stroke_w_med']['mm'],e[kk]['border_stroke_w_p90']['mm']))
print()
for s in ('V1','V2','OURS'):
    print('==',s,'diamonds: %d (on centreline %d) =='%(d[s]['diamonds']['count'],d[s]['diamonds']['on_vertical_centreline']))
    for it in d[s]['diamonds']['items']:
        print('   %-5s at (%5.1f,%6.1f)mm  %4.2f x %4.2f mm  w/h=%.2f fill=%.2f onrule=%s centreline=%s'%(
            it['colour'],it['cx']['mm'],it['cy']['mm'],it['w']['mm'],it['h']['mm'],it['w_over_h'],it['fill'],it['on_rule'],it['on_centreline']))
print()
for s in ('V1','V2','OURS'):
    c=d[s]['composition']
    print('%-5s content bbox %.1f..%.1f x %.1f..%.1f mm | centroid (%.2f,%.2f) off (%+0.2f,%+0.2f) | bboxoff (%+0.2f,%+0.2f) | margins L%.2f R%.2f T%.2f B%.2f | balance LR %+0.1f%% TB %+0.1f%%'%(
      s,c['content_bbox']['x0']['mm'],c['content_bbox']['x1']['mm'],c['content_bbox']['y0']['mm'],c['content_bbox']['y1']['mm'],
      c['content_centroid_x']['mm'],c['content_centroid_y']['mm'],c['centroid_offset_from_tag_centre_x']['mm'],c['centroid_offset_from_tag_centre_y']['mm'],
      c['bbox_centre_offset_x']['mm'],c['bbox_centre_offset_y']['mm'],c['margin_left']['mm'],c['margin_right']['mm'],c['margin_top']['mm'],c['margin_bottom']['mm'],
      c['ink_balance_left_minus_right_pct'],c['ink_balance_top_minus_bottom_pct']))
print()
for s in ('V1','V2','OURS'):
    print('--',s,'clear space (mm) --')
    for k2,v in d[s]['clear_space'].items():
        print('    %-52s %s'%(k2, ('%.3f'%v) if isinstance(v,float) else '%.2f mm'%v['mm']))
