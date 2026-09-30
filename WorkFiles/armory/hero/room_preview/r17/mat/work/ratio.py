import sys, numpy as np
from PIL import Image
for p in sys.argv[1:]:
    L = np.asarray(Image.open(p).convert('L')).astype(float)
    rs = []
    for y in range(965, 1045, 6):
        for x in range(600, 880, 40):
            s = L[y:y+6, x:x+40]
            rs.append(np.percentile(s, 90) / max(np.percentile(s, 10), 1))
    print(p.split('/')[-3], 'nub:gap p90/p10', round(float(np.median(rs)), 2))
