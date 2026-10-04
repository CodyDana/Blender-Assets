# judge r6: tack pitch (horizontal autocorrelation) and row centres in the front centre, photo vs ours, same camera
from PIL import Image
import numpy as np
T = 'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/props/taiko/'
a = np.asarray(Image.open(T + 't6/silhouette_overlay.png').convert('RGB')).astype(float)
for nm, x0 in (('photo', 0), ('ours', 1038)):
    lum = a[225:300, x0 + 400:x0 + 640].mean(2)
    d = (lum < 70).astype(float)
    prof = d.mean(1)
    print(nm, 'dark rows', ' '.join('%d:%.2f' % (225 + i, p) for i, p in enumerate(prof) if p > 0.05))
    for lo, hi in ((0, 75),):
        pass
    # per row band autocorrelation
    for yy in range(240, 290, 4):
        r = d[yy - 225:yy - 225 + 3].mean(0); r = r - r.mean()
        ac = np.correlate(r, r, 'full')[len(r) - 1:]
        lag = 12 + int(np.argmax(ac[12:60]))
        print('  y%d pitch %d (ac %.2f)' % (yy, lag, ac[lag] / max(ac[0], 1e-9)))
    # tack width along the row: mean dark run length at the row centre
    for yy in (250, 275, 280):
        r = d[yy - 225] > 0.5
        runs = []; c = 0
        for v in r:
            if v: c += 1
            elif c: runs.append(c); c = 0
        print('  y%d dark runs median %s' % (yy, np.median(runs) if runs else None), runs[:12])
