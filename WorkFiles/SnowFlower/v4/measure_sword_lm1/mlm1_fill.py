import numpy as np
def fill_rows(m, maxgap=14):
    m = m.copy()
    for y in range(m.shape[0]):
        c = np.where(m[y])[0]
        if len(c) < 2: continue
        d = np.diff(c); idx = np.where((d > 1) & (d <= maxgap))[0]
        for i in idx: m[y, c[i]:c[i+1]] = True
    return m
