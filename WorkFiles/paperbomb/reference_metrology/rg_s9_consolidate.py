# -*- coding: utf-8 -*-
"""STAGE 9 - consolidate every real-glyph measurement into ONE machine-readable
twin of the spec, and draw the labelled debug overlay. METROLOGY ONLY.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rg_lib as R  # noqa: E402


def L(name):
    return json.load(open(os.path.join(HERE, name), encoding="utf-8"))


S1 = L("rg_s1_silhouette.json")
S2 = L("rg_s2_elements.json")
S3 = L("rg_s3_geometry.json")
S3B = L("rg_s3b_ring_glyph.json")
S4 = L("rg_s4_ink.json")
S5 = L("rg_s5_detail.json")
S6 = L("rg_s6_columns.json")
S7 = L("rg_s7_fix.json")
S8 = L("rg_s8_seals.json")

PPMM = S1['ppmm']
CARD_W = 70.0
CARD_H = S1['card_h_mm_from_aspect']

spec = dict(
    authority=dict(
        reference_of_record="References/PaperBomb/paperbomb_guide_v2_real_glyphs.png",
        sha256_matches="Downloads/paperbomb.png (the file the user named)",
        size_px=[S1['image']['width'], S1['image']['height']],
        supporting_only="References/PaperBomb/paperbomb_guide.png (1024x1536) - SUB-PIXEL "
                        "CHARACTER ONLY, never a position, size, weight, colour or shape",
        tag_px=S1['tag_px'], ppmm=PPMM,
        px_mm=round(1.0 / PPMM, 4),
        nyquist_cell_mm=round(2.0 / PPMM, 4),
        card_w_mm=CARD_W, card_h_mm=CARD_H,
        aspect=S1['aspect'], aspect_sweep=S1['aspect_sweep'],
        tag_edge_rule="half-maximum of the PAPER-to-BACKGROUND warmth (R-B) step; the paper "
                      "level, NOT a high percentile, which lands on the red ink",
        never_traced="every number here is a position, size, fraction, angle, count, density or "
                     "colour value; no pixel of either guide is copied into anything that ships",
    ),
    silhouette=dict(
        virtual_corners_px=S1['virtual_corners'],
        octagon_vertices_px=S1['octagon_vertices_px'],
        sides=S1['sides'],
        chamfers=S1['chamfers'],
        outline_deviation=S1['outline_deviation'],
        outline_deviation_regions=S1['outline_deviation_regions'],
        damage_test=S1['damage_test'],
        verdict="CLEAN OCTAGON. No tear, no nick, no folded corner anywhere: every one of "
                "%d boundary samples lies within %.2f px (%.3f mm) of the fitted octagon, and "
                "zero samples on any side lie more than 1.5 px (0.38 mm) inboard of it."
                % (S1['outline_deviation']['n_points'],
                   max(abs(S1['outline_deviation']['min_px']), S1['outline_deviation']['max_px']),
                   max(abs(S1['outline_deviation']['min_mm']), S1['outline_deviation']['max_mm'])),
    ),
    rules=dict(insets=S3['rules'], frame=S3['rule_frame'],
               continuity=S3['rule_continuity'], ink_colour=S7['rule_ink_colour']),
    corner_ornaments=S3['corner_ornaments'],
    ring=S3B['ring'],
    centre_glyph=S3B['centre_glyph'],
    hero_clearance_mm=S3B['hero_clearance_mm'],
    hero_to_sho_mm=S4['hero_to_sho_mm'],
    columns=S6['columns'],
    flame_emblem=S5['flame_emblem'],
    flame_run_ladder=S6['flame_run_ladder'],
    flame_heart=S6['flame_heart'],
    flame_heart_vertical_scan=S6['flame_heart_vertical_scan'],
    flame_enclosed_voids=S6['flame_enclosed_voids'],
    seals=dict(big=S8['seal_big'], small=S8['seal_small'],
               big_alt=S5['seal_big'], small_alt=S5['seal_small']),
    centreline_chain=S7['centreline_chain'],
    bottom_rule_gap_each_side_of_diamond_mm=S7.get('bottom_rule_gap_each_side_of_diamond_mm'),
    leaf_pair_probe=S4['leaf_pair_probe'],
    paper=S4['paper'],
    edge_ageing=S5['edge_ageing'],
    grain=S7['grain'],
    mottle=S7['mottle'],
    reds=S4['reds'],
    red_spread=S4['red_spread'],
    red_weight=S5['red_weight'],
    black_ink=S4['black_ink'],
    ink_halo=S5['ink_halo'],
    coverage=S2['coverage'],
    HR_subpixel_character=S5['HR_subpixel_character'],
)

out = os.path.join(HERE, "reference_spec_realglyph.json")
with open(out, "w", encoding="utf-8") as fh:
    json.dump(spec, fh, indent=1, ensure_ascii=False)
print("wrote", out, os.path.getsize(out), "bytes")

# ------------------------------------------------------------------ overlay
a, _ = R.read_stored(R.RG)
H, W = a.shape[:2]
vis = a.copy()
P = np.array(S1['octagon_vertices_px'], float)


def line(p1, p2, col):
    n = int(max(abs(p2[0] - p1[0]), abs(p2[1] - p1[1])) * 2) + 2
    for t in np.linspace(0, 1, n):
        x = int(round(p1[0] + t * (p2[0] - p1[0])))
        y = int(round(p1[1] + t * (p2[1] - p1[1])))
        if 0 <= x < W and 0 <= y < H:
            vis[y, x] = col


for i in range(len(P)):
    line(P[i], P[(i + 1) % len(P)], [0, 0.85, 0])

XL = S1['sides']['L']['b']; XR = S1['sides']['R']['b']
YT = S1['sides']['T']['b']; YB = S1['sides']['B']['b']
WPX = XR - XL; HPX = YB - YT
fl = XL + S3['rules']['L']['inset_px']; fr = XR - 1 - S3['rules']['R']['inset_px']
ft = YT + S3['rules']['T']['inset_px']; fb = YB - 1 - S3['rules']['B']['inset_px']
for p1, p2 in (((fl, ft), (fr, ft)), ((fr, ft), (fr, fb)),
               ((fr, fb), (fl, fb)), ((fl, fb), (fl, ft))):
    line(p1, p2, [0, 0.4, 1])


def rect_mm(x0, x1, y0, y1, col):
    X0 = XL + x0 / CARD_W * WPX; X1 = XL + x1 / CARD_W * WPX
    Y0 = YT + y0 / CARD_H * HPX; Y1 = YT + y1 / CARD_H * HPX
    line((X0, Y0), (X1, Y0), col); line((X1, Y0), (X1, Y1), col)
    line((X1, Y1), (X0, Y1), col); line((X0, Y1), (X0, Y0), col)


g = S3B['centre_glyph']
rect_mm(g['x0_mm'], g['x1_mm'], g['y0_mm'], g['y1_mm'], [1, 0, 1])
f_ = S5['flame_emblem']
rect_mm(f_['x0_mm'], f_['x1_mm'], f_['y0_mm'], f_['y1_mm'], [1, 0.5, 0])
for nm, c in S6['columns'].items():
    w = c['whole']
    rect_mm(w['x0_mm'], w['x1_mm'], w['y0_mm'], w['y1_mm'], [0, 0.8, 0.8])
for k in ('big', 'small'):
    s = S8['seal_' + k]
    b = s['outer_box_mm']
    rect_mm(b[0], b[1], b[2], b[3], [0.6, 0, 1])
# ring mid ellipse
cx = XL + S3B['ring']['centre_f'][0] * WPX
cy = YT + S3B['ring']['centre_f'][1] * HPX
Aax = S3B['ring']['mid_axis_w_mm'] / 2 / CARD_W * WPX
Bax = S3B['ring']['mid_axis_h_mm'] / 2 / CARD_H * HPX
for t in np.linspace(0, 2 * np.pi, 900):
    x = int(round(cx + Aax * np.cos(t))); y = int(round(cy + Bax * np.sin(t)))
    if 0 <= x < W and 0 <= y < H:
        vis[y, x] = [1, 1, 0]
R.save_debug(vis, "s9_overlay_LABELLED", scale=3)
print("overlay written")
