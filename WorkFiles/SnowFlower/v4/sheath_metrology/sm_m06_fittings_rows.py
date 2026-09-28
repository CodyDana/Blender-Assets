# sm_m06: per-row silhouette widths through the fittings (throat, mid band, chape)
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from sm_lib import *
s01 = json.load(open(os.path.join(HERE, "sm_s01.json")))
prof = np.array(s01["profile"])
for ya, yb in [(31, 180), (270, 340), (1250, 1497)]:
    print("rows", ya, yb)
    for r in prof[(prof[:, 0] >= ya) & (prof[:, 0] <= yb)][::2]:
        print("  y %4d l %4d r %4d w %4d c %6.1f" % tuple(r[:5]))
