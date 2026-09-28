"""Estimate the photo's blur (Gaussian sigma, px) from edge profiles across the blade's straight front edges and the
ring's outer silhouette: fit an erf step to linear luminance profiles."""
import json, math, sys
import numpy as np
sys.path.insert(0, '.')
import section_procedure as SP
lum, _ = SP.load_lum(SP.PHOTO_PATH)
M = json.load(open(SP.BS + '/photo_A/measure_raw.json'))
def erf(x): 
    return np.vectorize(math.erf)(x)
def fit_edge(prof, us):
    best=None
    for sig in np.arange(0.3, 3.01, 0.05):
        for u0 in np.arange(-1.5, 1.51, 0.05):
            m = 0.5*(1+erf((us-u0)/(sig*math.sqrt(2))))
            A = np.column_stack([m, np.ones_like(m)]); c, res, *_ = np.linalg.lstsq(A, prof, rcond=None)
            e = float(((A@c-prof)**2).sum())
            if best is None or e<best[0]: best=(e, sig, u0, c)
    return best
out = {}
for line in ('top_front', 'bot_front'):
    L = M['lines'][line]; c0 = np.array(L['c']); d = np.array(L['d']); n = np.array([-d[1], d[0]])
    sigs=[]
    for t in np.arange(-40, 50, 6):
        P = c0 + t*d
        us = np.arange(-4, 4.01, 0.25)
        prof = np.array([np.mean([SP.bilin(lum, *(P + u*n + k*d)) for k in (-1, 0, 1)]) for u in us])
        e, sig, u0, cc = fit_edge(prof, us)
        if abs(cc[0]) > 0.02: sigs.append(sig)
    out[line] = [float(np.median(sigs)), float(np.percentile(sigs, 25)), float(np.percentile(sigs, 75)), len(sigs)]
print(json.dumps(out))
json.dump(out, open('photo_psf.json', 'w'), indent=1)
