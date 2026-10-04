# judge r6: lower collar row profile in the front centre, photo vs ours (same camera)
from PIL import Image
import numpy as np
T = 'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/props/taiko/'
a = np.asarray(Image.open(T + 't6/silhouette_overlay.png').convert('RGB')).astype(float)
for nm, x0 in (('photo', 0), ('ours', 1038)):
    sub = a[780:1010, x0 + 440:x0 + 600]
    lum = sub.mean(2); mx, mn = sub.max(2), sub.min(2)
    sat = ((mx - mn) / np.maximum(mx, 1)).mean(1); dark = (lum < 60).mean(1)
    print(nm, ' '.join('%d:%.0f/%.2f/%.2f' % (780 + i, lum[i:i+5].mean(), sat[i:i+5].mean(), dark[i:i+5].mean()) for i in range(0, 230, 5)))
