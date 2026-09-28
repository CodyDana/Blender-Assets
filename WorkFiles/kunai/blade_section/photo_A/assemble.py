"""Combine geometry (measure_raw.json), ring pose (ring_fit.json) and shading fit (shading_fit.json) into the
final per-station numbers + annotated overlay. Writes photo_A_measurement.json and photo_A_overlay.png."""
from PIL import Image, ImageDraw, ImageFont
import numpy as np, json, math

IMG = 'C:/Users/Cody/Desktop/Blender_Projects/References/Kunai/kunai_reference2.jpg'
M = json.load(open('measure_raw.json')); R = json.load(open('ring_fit.json')); SF = json.load(open('shading_fit.json'))
ri, ro = R['inner'], R['outer']

E_EDGE_MM = 0.25          # assumed photo edge half-thickness (unresolvable: < 1 px ~ 0.5 mm)
W_WIDEST_MM = 18.0        # photo blade scaled so its widest half-width = ours (36 mm blade)

T = np.array(M['top_corner']); B = np.array(M['bot_corner']); J = np.array(M['rj_front'])
Sh = np.array(M['shoulder_top']); Shb = np.array(M['shoulder_bot'])
adir = np.array([math.cos(math.radians(M['axis_angle_deg'])), math.sin(math.radians(M['axis_angle_deg']))])
cdir = np.array([math.cos(math.radians(M['cross_angle_deg'])), math.sin(math.radians(M['cross_angle_deg']))])
w_px = np.linalg.norm(B - T) / 2

g_lo = SF['face_on_fit']['base_gain'][0]; g_hi = SF['face_on_fit']['base_nogain'][0]
per = {round(p['frac'], 2): p for p in SF['per_station_top_face']}


def dist_to_line(p, a, b):
    d = (b - a) / np.linalg.norm(b - a); v = p - a; return abs(v[0] * d[1] - v[1] * d[0])


stations = []
for st in M['stations']:
    fr = round(st['frac'], 2)
    hw_rel = st['width_rel_widest']
    w_mm = W_WIDEST_MM * hw_rel
    if st['section'] == 'front':
        p = per[fr]
        lo, hi = p['r_gain'], p['r_nogain']
        fs = (lo + hi) / 2
        unc = f"shading-model: {lo:.2f} (blade albedo free) to {hi:.2f} (same albedo as ring); full sensitivity grid p10-p90 " \
              f"{SF['face_on_fit']['r_p10']:.2f}-{SF['face_on_fit']['r_p90']:.2f}. Ridge-line geometry cannot resolve it (blade seen ~face-on)."
    else:
        # rear facet = plane through rear edge line (z=0) and J (z = r*w_px); slope across at this station
        P = np.array(st['ridge'])     # ridge crossing on this chord (~ on the axis)
        zfrac = dist_to_line(P, T, Sh) / dist_to_line(J, T, Sh)
        hw = st['half_width_px']
        fs_of = lambda r: r * w_px * zfrac / hw
        lo, hi = fs_of(g_lo), fs_of(g_hi); fs = (lo + hi) / 2
        unc = f"rear-facet planar model only ({lo:.2f}-{hi:.2f}); rear ridge line is blurry (fit rms 1.9 px); treat as indicative"
    rr = fs + E_EDGE_MM / w_mm
    stations.append(dict(frac_from_shoulder=fr, our_blade_mm_from_shoulder=round(st['our_mm'], 1), section=st['section'],
                         face_slope=round(fs, 3), face_slope_low=round(lo, 3), face_slope_high=round(hi, 3),
                         face_angle_deg=round(math.degrees(math.atan(fs)), 1),
                         ridge_ratio=round(rr, 3), ridge_ratio_assumes=f"edge half-thickness {E_EDGE_MM} mm, half-width {w_mm:.1f} mm (photo width profile scaled to 36 mm widest)",
                         photo_half_width_px=round(st['half_width_px'], 2), photo_width_rel_widest=round(hw_rel, 3),
                         ridge_offset_px=round(st['ridge_offset_px'], 2), ridge_offset_frac=round(st['offset_frac'], 3),
                         ridge_ratio_if_ring_pose=round(st['ridge_ratio'], 3), uncertainty=unc))

front = [s for s in stations if s['section'] == 'front']
summary_fs = float(np.median([s['face_slope'] for s in front])); summary_rr = float(np.median([s['ridge_ratio'] for s in front]))

# ours, same metric, for context (spec numbers, pre-grind)
def ours(x):
    w = 8 + (18 - 8) * x / 35 if x <= 35 else 18 * (140 - x) / 105
    h = 2.5 if x <= 35 else 2.5 - (2.5 - 0.8) * (x - 35) / 100
    return dict(x_mm=round(x, 1), half_width=round(w, 2), ridge_half=round(h, 3), face_slope=round((h - 0.75) / w, 3), ridge_ratio=round(h / w, 3))
our_ctx = [ours(s['our_blade_mm_from_shoulder']) for s in stations]

result = dict(
    measurer='photo_A', image=IMG, image_size=[500, 333],
    headline=f"face_slope ~{summary_fs:.2f} (face angle ~{math.degrees(math.atan(summary_fs)):.0f} deg), ridge_ratio ~{summary_rr:.2f}, roughly constant along the front of the blade (planar facets). Range 0.26-0.44; wider 0.2-0.65.",
    method=[
        'Ring: ellipse fits to inner and outer silhouettes (radial threshold crossings, algebraic conic fit, 15% trimmed). cos(theta)=(b_o+b_i)/(a_o+a_i) is independent of tube shape.',
        'Blade: sub-pixel threshold crossings along columns/rows for 6 lines (front/rear top edge, front/rear bottom edge, front/rear ridge = lit/dark boundary); robust TLS line fits.',
        'Corners = edge-line intersections; crease/cross direction = corner-to-corner line; axis = crease midpoint -> tip (edge intersection). Stations cut along the cross direction.',
        'Geometric route: ridge offset from the chord midpoint / half-chord = ridge_ratio * tan(roll). Measured offset ~0.01 of the half-width at every front station: the ridge is on the midline, so the blade is seen ~face-on and this route cannot give the height.',
        'Ring pose (theta 24.8 deg roll about the blade axis) would force ridge_ratio ~0.03 and predicts facet luminances 163/149 or 23/23 vs observed 144/39: rejected. The ring is most likely ~10% oval along the kunai axis (forged loop), or twisted.',
        'Shading route: the ring tube (round cross-section) is used as a light probe/matcap (luminance vs view-space normal). Planar facets through the edge lines and a ridge of height r*w at the widest crease; r fitted to the 4 facet luminances. Sensitivity grid over kernel width, tube cut, facet set, blade albedo gain, roll +-5 deg, pitch +-15 deg.'],
    pose=dict(
        blade_plane='near face-on to the camera: roll about the blade axis ~2 deg (+-4), from ridge offset ~0.01 with face slope ~0.35; pitch (axis toward/away from camera) not constrained, assumed small (tested +-15 deg)',
        in_plane_rotation_deg=round(M['axis_angle_deg'], 2), in_plane_note='blade axis rises to the right at ~23.8 deg in the image; cross direction (corner-to-corner) at 65.7 deg; measured axis/cross skew 0.5 deg',
        ring_ellipse=dict(outer_a=round(ro['a'], 2), outer_b=round(ro['b'], 2), inner_a=round(ri['a'], 2), inner_b=round(ri['b'], 2),
                          aspect_outer=round(ro['aspect'], 3), aspect_inner=round(ri['aspect'], 3), major_axis_deg=round(ro['major_angle_deg'] - 180, 1),
                          theta_if_circular_coplanar_deg=round(M['theta_deg'], 1), theta_bootstrap_68=[round(v, 1) for v in M['bootstrap']['theta_p16_p84']],
                          tube_r_over_R=round((ro['a'] - ri['a']) / (ro['a'] + ri['a']), 3),
                          verdict='not used for pose: coplanar-circle reading contradicts the blade (see method)'),
        focal='long lens assumed (shallow DOF, compressed background) -> orthographic; perspective between ring and blade is along the kunai axis (pitch), which does not change the ridge-offset measurement',
        how_derived='ring ellipse (rejected), ridge-offset symmetry (roll ~0), facet shading vs ring matcap (face slope)'),
    photo_blade_proportions=dict(
        widest_chord_px=round(M['widest_chord_px'], 1), shoulder_chord_px=round(M['shoulder_chord_px'], 1),
        shoulder_to_widest_px=round(M['L_crease_px'], 1), shoulder_to_bark_px=round(M['L_visible_px'], 1), shoulder_to_extrapolated_tip_px=round(M['L_tip_px'], 1),
        width_over_length=round(M['widest_chord_px'] / M['L_tip_px'], 3), widest_at_frac_of_full=round(M['L_crease_px'] / M['L_tip_px'], 3),
        widest_at_frac_of_visible=round(M['crease_frac_of_visible'], 3), shoulder_over_widest=round(M['shoulder_chord_px'] / M['widest_chord_px'], 3),
        visible_over_full=round(M['L_visible_px'] / M['L_tip_px'], 3),
        ours=dict(width_over_length=round(36 / 140, 3), widest_at=0.25, shoulder_over_widest=round(16 / 36, 3)),
        note='if the axis is pitched toward the camera the photo length is foreshortened, so width/length is an upper bound'),
    geometry=dict(top_corner=M['top_corner'], bottom_corner=M['bot_corner'], ridge_junction=M['rj_front'], tip_extrapolated=M['tip'],
                  shoulder_axis=M['shoulder_axis'], bark_entry_axis=M['entry'], crease_ridge_frac_from_top=round(M['crease_ridge_frac_from_top'], 3),
                  ridge_line_misses_tip_px=round(M['ridge_front_miss_tip_px'], 2), lines=M['lines']),
    facet_luminance_observed=SF['ring_pose_hypothesis']['observed_facet_L'],
    ring_pose_hypothesis=SF['ring_pose_hypothesis'],
    shading_fit=dict(base_albedo_free=SF['face_on_fit']['base_gain'], base_same_albedo=SF['face_on_fit']['base_nogain'],
                     grid_median=SF['face_on_fit']['r_median'], grid_p10=SF['face_on_fit']['r_p10'], grid_p90=SF['face_on_fit']['r_p90'],
                     per_station_top_face=SF['per_station_top_face']),
    stations=stations, summary_face_slope=round(summary_fs, 3), summary_ridge_ratio=round(summary_rr, 3),
    ours_same_stations_spec_pre_grind=our_ctx,
    caveats=['500x333 JPEG with sharpening halos; edges located to ~0.2 px rms but the ridge HEIGHT is not visible geometrically in this pose',
             'shading answer assumes ring and blade share finish and see the same distant lighting; ring tube is only ~11 px wide so the probe is blurred (biases same-albedo fit high)',
             'blade albedo vs ring is the main degeneracy: 0.26-0.31 if the blade is ~1.3x brighter, 0.40-0.47 if identical',
             'photo edge thickness unresolvable; ridge_ratio adds an assumed 0.25 mm edge half-thickness',
             'the photo kunai is a different design (broader blade, narrower shoulder); use ratios, not mm'])
json.dump(result, open('photo_A_measurement.json', 'w'), indent=1, default=float)
print(json.dumps(dict(stations=[{k: s[k] for k in ('frac_from_shoulder', 'our_blade_mm_from_shoulder', 'face_slope', 'face_slope_low', 'face_slope_high', 'ridge_ratio', 'face_angle_deg')} for s in stations],
                      summary=(summary_fs, summary_rr), ours=our_ctx), indent=0))

# ---------------- overlay ----------------
S = 3
base = Image.open(IMG).convert('RGB')
big = base.resize((500 * S, 333 * S), Image.LANCZOS)
panel_h = 420
canvas = Image.new('RGB', (500 * S, 333 * S + panel_h), (18, 18, 22)); canvas.paste(big, (0, 0))
d = ImageDraw.Draw(canvas)
def font(sz):
    for f in ('C:/Windows/Fonts/consola.ttf', 'C:/Windows/Fonts/arial.ttf'):
        try:
            return ImageFont.truetype(f, sz)
        except Exception:
            pass
    return ImageFont.load_default()
F14, F18, F22 = font(15), font(19), font(23)
tp = lambda p: ((p[0] + 0.5) * S, (p[1] + 0.5) * S)
def line_seg(ln, t0, t1, col, w=2):
    c = np.array(ln['c']); dd = np.array(ln['d']); d.line([tp(c + dd * t0), tp(c + dd * t1)], fill=col, width=w)
Ln = M['lines']
def tparam(ln, p):
    return float((np.array(p) - np.array(ln['c'])) @ np.array(ln['d']))
tip = np.array(M['tip']); ent = np.array(M['entry'])
# edges (red/orange), ridge (green), crease (cyan), axis (white dashed)
line_seg(Ln['top_front'], tparam(Ln['top_front'], T), tparam(Ln['top_front'], tip), (255, 60, 60))
line_seg(Ln['bot_front'], tparam(Ln['bot_front'], B), tparam(Ln['bot_front'], tip), (255, 60, 60))
line_seg(Ln['top_rear'], tparam(Ln['top_rear'], Sh), tparam(Ln['top_rear'], T), (255, 150, 40))
line_seg(Ln['bot_rear'], tparam(Ln['bot_rear'], Shb), tparam(Ln['bot_rear'], B), (255, 150, 40))
line_seg(Ln['ridge_front'], tparam(Ln['ridge_front'], J), tparam(Ln['ridge_front'], tip), (60, 255, 90))
d.line([tp(T), tp(B)], fill=(0, 220, 255), width=2)
sa = np.array(M['shoulder_axis'])
for k in range(0, 60):
    a = sa + (tip - sa) * k / 60; b = sa + (tip - sa) * (k + 0.5) / 60; d.line([tp(a), tp(b)], fill=(255, 255, 255), width=1)
d.line([tp(Sh), tp(Shb)], fill=(255, 255, 0), width=2)
# stations
for s, st in zip(stations, M['stations']):
    a, b, r = np.array(st['top']), np.array(st['bot']), np.array(st['ridge'])
    d.line([tp(a), tp(b)], fill=(255, 0, 255), width=2)
    x, y = tp(r); d.ellipse([x - 4, y - 4, x + 4, y + 4], outline=(255, 255, 255), width=2)
    bx, by = tp(b)
    d.text((bx - 18, by + 8), f"{s['frac_from_shoulder']:.2f}\n{s['our_blade_mm_from_shoulder']:.0f}mm\nfs {s['face_slope']:.2f}", fill=(255, 230, 255), font=F14)
# ring ellipses
for f, col in ((ri, (60, 255, 90)), (ro, (255, 0, 255))):
    th = math.radians(f['major_angle_deg'])
    pts = [tp((f['cx'] + f['a'] * math.cos(t) * math.cos(th) - f['b'] * math.sin(t) * math.sin(th),
               f['cy'] + f['a'] * math.cos(t) * math.sin(th) + f['b'] * math.sin(t) * math.cos(th))) for t in np.linspace(0, 2 * math.pi, 180)]
    d.line(pts + [pts[0]], fill=col, width=2)
th = math.radians(ro['major_angle_deg']); c0 = np.array([ro['cx'], ro['cy']])
d.line([tp(c0 - ro['a'] * np.array([math.cos(th), math.sin(th)])), tp(c0 + ro['a'] * np.array([math.cos(th), math.sin(th)]))], fill=(255, 255, 255), width=1)
d.text(tp((60, 272)), f"ring: outer {ro['a']:.1f}x{ro['b']:.1f}px  inner {ri['a']:.1f}x{ri['b']:.1f}px\naspect-> theta {M['theta_deg']:.1f} deg IF circular+coplanar\n(rejected: contradicts blade, see panel)", fill=(255, 255, 255), font=F14)
# legend / panel
y0 = 333 * S + 10
txt = [
    ("photo_A  -  kunai_reference2.jpg blade section (ratios only; photo is a shape reference, not traced)", F22, (255, 255, 255)),
    ("red = front edges, orange = rear (shoulder) edges, green = ridge (lit/dark boundary), cyan = widest crease (corner to corner),", F18, (220, 220, 220)),
    ("white dashed = axis (crease midpoint -> extrapolated tip), yellow = shoulder, magenta = station chords (frac of visible blade / our mm / face slope)", F18, (220, 220, 220)),
    (f"Ridge sits on the chord midpoint at every station (offset {min(s['ridge_offset_frac'] for s in stations if s['section']=='front'):+.3f}..{max(s['ridge_offset_frac'] for s in stations if s['section']=='front'):+.3f} of half-width) -> blade seen ~face-on; height NOT visible geometrically.", F18, (255, 220, 120)),
    (f"Ring-pose reading (roll {M['theta_deg']:.1f} deg) would need ridge_ratio ~0.03 and predicts facet L 163/149 or 23/23 vs observed 144/39 -> rejected", F18, (255, 220, 120)),
    ("   (the ring is most likely ~10% oval along the kunai axis, or twisted on the tang).", F18, (255, 220, 120)),
    (f"Shading fit (ring tube as light probe, planar facets): face_slope {g_lo:.2f} (blade albedo free) .. {g_hi:.2f} (same albedo); grid p10-p90 {SF['face_on_fit']['r_p10']:.2f}-{SF['face_on_fit']['r_p90']:.2f}", F18, (140, 255, 160)),
    (f"SUMMARY face_slope ~{summary_fs:.2f} (face angle ~{math.degrees(math.atan(summary_fs)):.0f} deg), ridge_ratio ~{summary_rr:.2f}, ~constant along the front.", F22, (140, 255, 160)),
    ("Ours (spec, pre-grind) at 39 mm: face_slope 0.10, ridge_ratio 0.14.   Confidence: low-medium.", F22, (140, 255, 160)),
]
for t, f, col in txt:
    d.text((14, y0), t, fill=col, font=f); y0 += f.size + 16
canvas.save('photo_A_overlay.png')
# zoomed blade crop of the overlay for readability
canvas.crop((230 * S, 90 * S, 440 * S, 205 * S)).save('photo_A_overlay_blade_zoom.png')
print('overlay written')
