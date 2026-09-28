"""Photo: sensitivity of the RATIO estimate to the ridge offset q (roll), and the ring-coplanar hypothesis test."""
import json, math, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import section_procedure as SP
import measure_photo as MP
from run_validate import FV
out = {}
for lg in (True, False):
    mc, tube, dmax = MP.probe(0.3, 0.0, None, lg)
    tag = 'log' if lg else 'lin'
    res = []
    for f in FV:
        s = f * MP.M['L_visible_px']
        q_mine, hw, ur, mid = SP.ridge_offset(MP.lum, MP.blade, s)
        q_A = next((st['offset_frac'] for st in MP.M['stations'] if abs(st['frac'] - f) < 1e-6), None)
        row = {'frac': f, 'q_mine': q_mine, 'q_A_station': q_A}
        for name, q in (('q_mine', q_mine), ('q_0.01', 0.01), ('q_0.00', 0.0), ('q_0.05', 0.05)):
            r = SP.run2(MP.lum, MP.blade, mc, [s], lambda _s: q, gain1=False)[0]
            row[name + '_r'] = r['ratio_r']; row[name + '_roll'] = round(r['ratio_roll'], 2)
        # ring-coplanar hypothesis: roll 23-25 deg -> predicted facet luminances for the r that q implies
        mt, ct, mb, cb = SP.station_models(MP.blade, s)
        hyp = {}
        for roll in (23.0, 24.8):
            r_h = max(q_mine / math.tan(math.radians(roll)), 0.01)
            nt = SP.facet_normal(mt, r_h / ct, MP.blade, roll); nb = SP.facet_normal(mb, r_h / cb, MP.blade, roll)
            ut, ub = MP.blade.top(s), MP.blade.bot(s)
            Lt, _ = SP.facet_L(MP.lum, MP.blade, s, 'top'); Lb, _ = SP.facet_L(MP.lum, MP.blade, s, 'bot')
            hyp[f'roll{roll}'] = {'r_implied': round(r_h, 3), 'pred_ratio_top_bot': round(mc(nt[:2]) / mc(nb[:2]), 2),
                                  'obs_ratio_top_bot': round(Lt / Lb, 2)}
        row['ring_coplanar_hypothesis'] = hyp
        res.append(row)
        print(tag, row)
    out[tag] = res
Path('photo_q_sensitivity.json').write_text(json.dumps(out, indent=1))
