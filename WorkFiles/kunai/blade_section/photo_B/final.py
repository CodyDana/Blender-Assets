import numpy as np, json, math
from PIL import Image, ImageDraw, ImageFont
SRC = 'C:/Users/Cody/Desktop/Blender_Projects/References/Kunai/kunai_reference2.jpg'
Ls = json.load(open('blade_lines.json')); rf = json.load(open('ring_fit.json')); fac = json.load(open('facets.json'))
joint = json.load(open('joint.json')); probe = json.load(open('ring_probe.json'))['curve']
Tt, Tb, tip, R, Rc, M = np.load('keypts.npy')
s_sh, s_tip, s_vis = fac['s_shoulder'], fac['s_tip'], fac['s_visible_end']
AX = -22.76
axd = np.array([math.cos(math.radians(AX)), math.sin(math.radians(AX))]); v = np.array([axd[1], -axd[0]])


def line(k): return np.array(Ls[k]['c']), np.array(Ls[k]['d'])


def hit(P, dv, k):
    c, d = line(k); t = np.linalg.solve(np.column_stack([dv, -d]), c - P); return t[0]


def ours(x):
    h = 8 + 10 * x / 35 if x <= 35 else 18 * (1 - (x - 35) / 105) * (1 + 0.25 * (x - 35) / 105)
    t = 5.0 if x <= 35 else max(1.6, 5 + (1.6 - 5) * (x - 35) / 100)
    return h, t / 2


def ours_mm(s): return (s - s_sh) / (0 - s_sh) * 35.0 if s < 0 else 35.0 + s / s_tip * 105.0


rows = fac['rows']


def near(s, key, win=4.6): return float(np.mean([r[key] for r in rows if abs(r['s'] - s) <= win]))


KA = joint['kept_alpha']  # min, p25, med, p75, max (geometry-filtered)
a_c = 10.1; roll_c = 4.9  # k=1.1 med/med solution
tn = lambda a: math.tan(math.radians(a))
stations = []
for fv, label in ((0.10, 'rear'), (None, 'widest'), (0.40, 'front'), (0.60, 'front'), (0.80, 'front'), (0.93, 'front-near-bark')):
    s = 0.0 if fv is None else s_sh + fv * (s_vis - s_sh)
    fvv = (s - s_sh) / (s_vis - s_sh); x = ours_mm(s); w_o, hr_o = ours(x)
    front = s >= 0 and label != 'rear'
    hw = near(s, 'halfw', 3.1 if fv is None else 4.6)
    off = float(np.mean([r['off'] for r in rows if abs(r['s'] - s) <= (6.1 if fv is None else 4.6)]))
    if front:
        fs = tn(a_c); iqr = [tn(KA[1]), tn(KA[3])]; rng = [tn(KA[0]), tn(KA[4])]; ang = a_c
        unc = ('front facet is planar (brightness flat 132-151 along it), so one slope; shading-derived; IQR/range from '
               'probe-curve quartiles x blade/ring albedo 1.0-1.25, filtered by the ridge-offset geometry')
        if label == 'front-near-bark':
            unc += '; near the bark the lower facet darkens (L~20): shadow or occlusion, least reliable station'
    else:
        hw_w = joint['widest_halfw']; fs_a = tn(a_c) * hw_w / hw; fs_b = 0.30
        fs = 0.5 * (fs_a + fs_b); iqr = [min(fs_a, 0.23), 0.34]; rng = [tn(KA[0]) * hw_w / hw, 0.38]; ang = math.degrees(math.atan(fs))
        unc = ('rear facet: blend of (a) constant ridge height carried back from the widest station, slope %.2f, and (b) '
               'per-station shading inversion ~0.30 (rear upper facet L~165, brighter = steeper), which sits on the '
               'saturating part of the probe curve' % fs_a)
    e_w = 0.75 / w_o
    stations.append(dict(
        label=label, frac_from_shoulder=round(fvv, 3), frac_from_shoulder_to_extrapolated_tip=round((s - s_sh) / (s_tip - s_sh), 3),
        ours_mm_from_shoulder=round(x, 1), photo_axial_px_from_widest=round(s, 1), photo_halfwidth_px=round(hw, 2),
        photo_halfwidth_over_max=round(hw / joint['widest_halfw'], 3),
        ridge_offset_px_toward_top_edge=round(off, 2), ridge_offset_over_halfwidth=round(off / hw, 4),
        facet_L_upper=round(near(s, 'Lup'), 1), facet_L_lower=round(near(s, 'Llo'), 1),
        face_angle_deg=round(ang, 1), face_slope=round(fs, 3), face_slope_IQR=[round(iqr[0], 3), round(iqr[1], 3)],
        face_slope_range=[round(rng[0], 3), round(rng[1], 3)],
        edge_half_over_halfwidth_assumed=round(e_w, 4), ridge_ratio=round(fs + e_w, 3), ridge_ratio_if_sharp_edge=round(fs, 3),
        ours_face_slope=round((hr_o - 0.75) / w_o, 3), ours_ridge_ratio=round(hr_o / w_o, 3),
        photo_over_ours_face_slope=round(fs / ((hr_o - 0.75) / w_o), 2),
        coplanar_ring_hypothesis_ridge_ratio=round((off / hw) / math.tan(math.radians(22.9)), 3), uncertainty=unc))
for st in stations:
    print(st['label'], st['frac_from_shoulder'], st['ours_mm_from_shoulder'], st['face_slope'], st['face_slope_IQR'],
          st['face_slope_range'], st['ridge_ratio'], 'ours', st['ours_face_slope'], st['ours_ridge_ratio'], 'x', st['photo_over_ours_face_slope'],
          'H1', st['coplanar_ring_hypothesis_ridge_ratio'], 'hw', st['photo_halfwidth_over_max'])
fi, fo = rf['45']['inner'], rf['45']['outer']
result = dict(
    image=SRC, image_size=[500, 333],
    ring=dict(inner=fi, outer=fo, centreline_minor_over_major=(fi['semi_minor'] + fo['semi_minor']) / (fi['semi_major'] + fo['semi_major']),
              roll_if_circle_deg=22.9, minor_axis_dir_deg=[fi['minor_dir_deg'], fo['minor_dir_deg']], threshold_variants=rf),
    axes=dict(grip_axis_deg=-20.8, grip_top_edge_deg=Ls['grip_top']['ang'], front_edge_bisector_deg=-23.21, chord_perp_deg=67.24 - 90,
              axis_used_deg=AX, ridge_front_deg=Ls['ridge_front']['ang'], ridge_rear_deg=Ls['ridge_rear']['ang']),
    keypoints=dict(Ttop=Tt.tolist(), Tbot=Tb.tolist(), tip_extrapolated=tip.tolist(), R_crease_x_ridge=Rc.tolist(), M_chord_mid=M.tolist(),
                   shoulder_top=fac['shoulder_top'], shoulder_bot=fac['shoulder_bot'], visible_end=[403.0, 110.3]),
    blade_proportions=dict(
        axial_shoulder_to_widest_px=-s_sh, axial_widest_to_tip_px=s_tip, axial_widest_to_visible_end_px=s_vis,
        widest_frac_of_shoulder_to_tip=-s_sh / (s_tip - s_sh), shoulder_halfwidth_over_max=near(s_sh + 2, 'halfw', 1.6) / joint['widest_halfw'],
        width_over_length_shoulder_to_tip=2 * joint['widest_halfw'] / (s_tip - s_sh), visible_frac_of_shoulder_to_tip=(s_vis - s_sh) / (s_tip - s_sh),
        ours=dict(widest_frac=0.25, shoulder_over_max=8 / 18, width_over_length=36 / 140)),
    line_fits={k: {kk: vv for kk, vv in dd.items() if kk != 'pts'} for k, dd in Ls.items()},
    probe_curve_up_tilt_deg_vs_L_med_q25_q75_n=probe,
    joint_solution=dict(front_face_angle_deg=a_c, roll_deg=roll_c, kept_alpha_min_p25_med_p75_max=KA, kept_roll_min_med_max=joint['kept_roll'],
                        widest_ridge_offset_measured_px=joint['widest_off'], combos=joint['combos']),
    hypothesis_tests=dict(
        H1_ring_circle_coplanar_plus='roll +22.9 deg; ridge on the edge midline (offset 0.15 +-1 px at the widest) forces ridge_ratio ~0.00-0.05; '
                                     'REJECTED: both facets would then tilt ~21 deg up and read bright (probe L~150) but the lower facet reads L~39',
        H1_ring_circle_coplanar_minus='roll -22.9 deg: the upper facet reading bright needs a face angle >= 34 deg => ridge offset ~ -9 px toward the '
                                      'lower edge; REJECTED (measured +0.15 px)',
        H2_blade_near_face_on='roll ~+5 deg (-4..+10); ring oval (~0.92) or twisted relative to the blade; ACCEPTED; section depth then comes from '
                              'shading (ring used as a light probe), not from the ridge position, which is degenerate near face-on'),
    stations=stations,
    summary=dict(face_slope_front=round(tn(a_c), 3), face_slope_front_IQR=[round(tn(KA[1]), 3), round(tn(KA[3]), 3)],
                 face_slope_front_range=[round(tn(KA[0]), 3), round(tn(KA[4]), 3)],
                 ridge_ratio_widest=stations[1]['ridge_ratio'], ours_face_slope_widest=0.097, ours_ridge_ratio_widest=0.139))
json.dump(result, open('photo_B_measurements.json', 'w'), indent=1)

# ---------------------------------------------------------------- overlay
S = 3
im = Image.open(SRC).convert('RGB').resize((500 * S, 333 * S), Image.LANCZOS)
W = 500 * S + 600
canvas = Image.new('RGB', (W, 333 * S), (24, 24, 28)); canvas.paste(im, (0, 0))
d = ImageDraw.Draw(canvas)
try:
    F = ImageFont.truetype('arial.ttf', 15); FS = ImageFont.truetype('consola.ttf', 13); FB = ImageFont.truetype('arialbd.ttf', 16)
except Exception:
    F = FS = FB = ImageFont.load_default()
P = lambda p: (p[0] * S, p[1] * S)


def seg(a, b, col, w=2): d.line([P(a), P(b)], fill=col, width=w)


def ell(f, col, w=2, dash=False):
    c = np.array(f['center']); A = f['semi_major']; B = f['semi_minor']; md = math.radians(f['minor_dir_deg'])
    um = np.array([math.cos(md), math.sin(md)]); uM = np.array([-um[1], um[0]]); pts = []
    for t in np.linspace(0, 2 * math.pi, 181): pts.append(P(c + A * math.cos(t) * uM + B * math.sin(t) * um))
    if dash:
        for i in range(0, 180, 4): d.line(pts[i:i + 3], fill=col, width=w)
    else:
        d.line(pts, fill=col, width=w)


ell(fi, (0, 230, 255)); ell(fo, (0, 230, 255))
cl = dict(center=((np.array(fi['center']) + np.array(fo['center'])) / 2).tolist(), semi_major=(fi['semi_major'] + fo['semi_major']) / 2,
          semi_minor=(fi['semi_minor'] + fo['semi_minor']) / 2, minor_dir_deg=(fi['minor_dir_deg'] + fo['minor_dir_deg']) / 2)
ell(cl, (255, 230, 0), 1, True)
c = np.array(cl['center']); md = math.radians(cl['minor_dir_deg']); um = np.array([math.cos(md), math.sin(md)])
seg(c - cl['semi_minor'] * um, c + cl['semi_minor'] * um, (255, 230, 0), 1)
seg(c, tip, (255, 0, 255), 1)
G = (60, 255, 60); RD = (255, 60, 60)
seg(np.array(fac['shoulder_top']), Tt, G); seg(Tt, tip, G); seg(np.array(fac['shoulder_bot']), Tb, G); seg(Tb, tip, G)
seg(Rc, tip, RD)
cr, dr = line('ridge_rear'); seg(Rc, Rc - 42 * dr, RD)
for k in ('grip_top', 'grip_bot'):
    cc, dd = line(k); seg(cc - 50 * dd, cc + 50 * dd, (160, 160, 255), 1)
seg(Tt, Rc, (255, 160, 0), 2); seg(Rc, Tb, (255, 160, 0), 1)
for p, name in ((Tt, 'Ttop'), (Tb, 'Tbot'), (Rc, 'R'), (tip, 'tip (extrap.)')):
    q = P(p); d.ellipse([q[0] - 4, q[1] - 4, q[0] + 4, q[1] + 4], outline=(255, 255, 255), width=2)
    d.text((q[0] + 6, q[1] - 18), name, fill=(255, 255, 255), font=F, stroke_width=2, stroke_fill=(0, 0, 0))
for st in stations:
    s = st['photo_axial_px_from_widest']; Pp = M + s * axd; fr = s >= 0 and st['label'] != 'rear'
    tt = hit(Pp, v, 'top_front' if fr else 'top_rear'); tb = hit(Pp, v, 'bot_front' if fr else 'bot_rear')
    a = Pp + tt * v; b = Pp + tb * v; seg(a, b, (255, 255, 255), 1)
    q = P(b); lab = '%.2f\nfs %.2f' % (st['frac_from_shoulder'], st['face_slope'])
    d.multiline_text((q[0] - 14, q[1] + 6), lab, fill=(255, 255, 255), font=F, stroke_width=2, stroke_fill=(0, 0, 0))
x0 = 500 * S + 16; y = 14


def T(t, f=F, col=(235, 235, 235)):
    global y; d.text((x0, y), t, fill=col, font=f); y += f.size + 5


T('Photo measurer B - blade section (kunai_reference2)', FB, (255, 230, 120))
T('green edges | red ridge | orange widest-station crease', F)
T('cyan ring fits | yellow ring centreline + minor axis', F)
T('magenta blade axis | white = stations (frac, face_slope)', F)
y += 6
T('POSE', FB)
T('axis -22.8 deg in image; no pitch (ring major axis and', F)
T('  the widest chord are both square to the blade axis)', F)
T('ring centreline b/a 0.921 = 22.9 deg roll IF circular+coplanar', F)
T('ridge sits on the edge midline everywhere (|off| <= 0.9 px)', F)
T('shading (ring used as light probe) rejects that 22.9 deg:', F)
T('  blade near face-on, roll ~+5 deg (-4..+10)', F)
T('  => ring oval/twisted; depth comes from shading', F)
y += 6
T('RESULT  (face_slope = tan of face angle)', FB)
T('station frac  ours_mm  photo fs [IQR]        ours fs', FS)
for st in stations:
    T('%-7s %.2f  %5.1f    %.2f [%.2f-%.2f]    %.3f' % (st['label'][:7], st['frac_from_shoulder'], st['ours_mm_from_shoulder'], st['face_slope'],
                                                     st['face_slope_IQR'][0], st['face_slope_IQR'][1], st['ours_face_slope']), FS)
T('front ~%.2f (full range %.2f-%.2f) = ~2x ours (0.08-0.10)' % (tn(a_c), tn(KA[0]), tn(KA[4])), F, (255, 230, 120))
T('ridge_ratio at widest %.2f (1.5 mm edge on our widths) vs ours 0.14' % stations[1]['ridge_ratio'], F, (255, 230, 120))
y += 8
T('RING PROBE: luminance vs normal up-tilt (deg)', FB)
px0, py0, pw, ph = x0 + 34, y + 4, 520, 190
d.rectangle([px0, py0, px0 + pw, py0 + ph], outline=(120, 120, 120))
X = lambda u: px0 + (u + 50) / 100 * pw; Y = lambda L: py0 + ph - (L / 255) * ph
for u in (-40, -20, 0, 20, 40):
    d.line([(X(u), py0), (X(u), py0 + ph)], fill=(60, 60, 60)); d.text((X(u) - 8, py0 + ph + 3), str(u), fill=(200, 200, 200), font=FS)
for L in (50, 100, 150, 200): d.text((px0 - 30, Y(L) - 7), str(L), fill=(200, 200, 200), font=FS)
d.line([(X(r[0]), Y(r[2])) for r in probe], fill=(0, 110, 130), width=1)
d.line([(X(r[0]), Y(r[3])) for r in probe], fill=(0, 110, 130), width=1)
d.line([(X(r[0]), Y(r[1])) for r in probe], fill=(0, 230, 255), width=2)
for Lv, col, nm in ((145.9, (230, 230, 230), 'upper front facet 146'), (38.7, (160, 160, 160), 'lower front facet 39'),
                    (165, (255, 200, 120), 'upper rear facet 165')):
    d.line([(px0, Y(Lv)), (px0 + pw, Y(Lv))], fill=col, width=1); d.text((px0 + 4, Y(Lv) - 15), nm, fill=col, font=FS)
canvas.save('photo_B_overlay.png')
print('saved', canvas.size)
