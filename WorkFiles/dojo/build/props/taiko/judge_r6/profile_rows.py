# judge r6: row profiles in the front centre (photo panel A vs ours panel B of t6/silhouette_overlay.png, same camera)
from PIL import Image
import numpy as np
T = 'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/props/taiko/'
a = np.asarray(Image.open(T + 't6/silhouette_overlay.png').convert('RGB')).astype(float)
for nm, x0 in (('photo', 0), ('ours', 1038)):
    sub = a[150:420, x0 + 420:x0 + 620]
    lum = sub.mean(2)
    dark = (lum < 60).mean(1)
    # saturation (gold) per row
    mx, mn = sub.max(2), sub.min(2)
    sat = ((mx - mn) / np.maximum(mx, 1)).mean(1)
    rows = []
    print(nm)
    for i in range(0, 270, 5):
        print('  y%4d dark %.2f sat %.2f lum %.0f' % (150 + i, dark[i:i+5].mean(), sat[i:i+5].mean(), lum[i:i+5].mean()))
    # tack pitch by autocorrelation of darkness along a row band
    for yb in (int(np.argmax(dark[:120])),):
        pass
