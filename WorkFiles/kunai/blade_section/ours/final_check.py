"""Task 4 check: the final (validated) procedure on our render in the photo pose (roll 5, same world as the gallery
render; uniform steel + a round probe torus, since our shipped ring is a flat forged ring and cannot be a probe), plus
the whole validation set with the final settings (log residual, PSF-footprint forward fit).  Also the measurers'
kernel-matcap method on the same render (the bias that explains measurer A)."""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import section_procedure as SP
import run_validate2 as V
from run_validate import FV, x_of_fvis, analytic
HERE = Path(__file__).parent

def go(name, k, scale, method='v3'):
    png = HERE / 'validate' / f'{name}.png'; meta = json.loads(open(str(png) + '.json').read())
    lum0, al0 = SP.load_lum(png); lum, al = V.resize(lum0, scale), V.resize(al0, scale)
    blade = SP.blade_from_meta(meta, scale=scale, visible_x=x_of_fvis(1.0)); pr = meta['probe']
    c = np.array(pr['centre_px']) * scale; cl = [[p[0] * scale, p[1] * scale] for p in pr['centreline_px']]
    tube = pr['tube_r_px'] * scale; sig = 0.35 * max(scale, 0.5)
    fn, box = SP.ring_d_centreline(c, cl, tube)
    if method == 'v3':
        mc = SP.ParamMatcap(lum, fn, SP.probe_pixels(fn, box, 1 - (0.5 + 2 * sig) / tube), sig_psf=sig, log=True)
    else:
        m = SP.Matcap(SP.probe_samples_centreline(lum, c, cl, tube), 0.12); mc = lambda n2, at=None: m(n2)
    rows = []
    for f in FV:
        x = x_of_fvis(f); s = blade.s_of_x(x)
        q, *_ = SP.ridge_offset(lum, blade, s, alpha=al)
        qt = (blade.ridge(s) - 0.5 * (blade.top(s) + blade.bot(s))) / (0.5 * (blade.top(s) - blade.bot(s)))
        r = SP.run2(lum, blade, mc, [s], lambda _s: q, alpha=al, gain1=False)[0]
        an = analytic(x, k)
        rows.append({'frac_vis': f, 'x_mm': round(x, 2), 'analytic_face_slope': round(an['face_slope'], 4),
                     'analytic_ridge_ratio': round(an['ridge_ratio'], 4), 'recovered_face_slope': r['ratio_r'],
                     'band10': r['ratio_band10'], 'q_meas': round(q, 4), 'q_true': round(qt, 4),
                     'roll_est': round(r['ratio_roll'], 2), 'L_srgb': [round(r['L_top_srgb'], 1), round(r['L_bot_srgb'], 1)]})
    return rows

out = {}
cases = [('v9_z1_roll5', 1.0), ('v1_z1', 1.0), ('v7_z1_roll6', 1.0), ('v4_z1_probe035', 1.0), ('v3_z2', 2.0),
         ('v6_z2_roll6', 2.0), ('v2_z35', 3.5), ('v8_z35_roll0', 3.5), ('v5_z35_probe035', 3.5)]
for name, k in cases:
    for scale in (0.7, 1.0):
        rows = go(name, k, scale)
        rat = [r['recovered_face_slope'] / r['analytic_face_slope'] for r in rows]
        front = rat[2:]
        out[f'{name}@{scale}'] = {'rows': rows, 'median_ratio_front': float(np.median(front)),
                                  'median_ratio_all': float(np.median(rat)), 'min': float(min(rat)), 'max': float(max(rat))}
        print('%-18s s%.1f  median rec/true front %.2f all %.2f [%.2f-%.2f]' % (name, scale, np.median(front), np.median(rat), min(rat), max(rat)), flush=True)
kr = go('v9_z1_roll5', 1.0, 0.7, method='kernel')
out['v9_z1_roll5@0.7_KERNEL_0.12_as_measurer_A'] = {'rows': kr, 'median_ratio_front': float(np.median([r['recovered_face_slope'] / r['analytic_face_slope'] for r in kr[2:]]))}
print('kernel method on v9:', out['v9_z1_roll5@0.7_KERNEL_0.12_as_measurer_A']['median_ratio_front'])
for r in out['v9_z1_roll5@0.7']['rows']: print(r)
(HERE / 'validate' / 'final_check.json').write_text(json.dumps(out, indent=1))
