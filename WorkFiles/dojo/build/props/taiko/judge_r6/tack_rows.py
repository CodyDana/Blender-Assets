# judge r6: row centres from each tack's own dark-disc centroid (columns between tacks split the rows), same camera
from PIL import Image
import numpy as np
from scipy import ndimage as ndi
T = 'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/props/taiko/'
a = np.asarray(Image.open(T + 't6/silhouette_overlay.png').convert('RGB')).astype(float)
for nm, x0 in (('photo', 0), ('ours', 1038)):
    sub = a[228:296, x0 + 400:x0 + 640]
    lum = sub.mean(2)
    m = lum < 110  # tack incl. highlights mostly
    m = ndi.binary_fill_holes(m)
    dist = ndi.distance_transform_edt(m)
    pk = (dist == ndi.maximum_filter(dist, size=15)) & (dist > 8)
    lab, n = ndi.label(pk)
    c = np.array(ndi.center_of_mass(pk, lab, range(1, n + 1)))
    r = np.array([dist[int(round(y)), int(round(x))] for y, x in c])
    ys = c[:, 0] + 228
    order = np.argsort(c[:, 1])
    print(nm, 'n', n, 'y', np.round(ys[order], 1).tolist())
    print('   inscribed radius', np.round(r[order], 1).tolist())
    med = np.median(ys)
    up, lo = ys[ys < med - 3], ys[ys > med + 3]
    print('   upper row y %.1f  lower row y %.1f  dy %.1f  (n %d/%d)' % (up.mean(), lo.mean(), lo.mean() - up.mean(), len(up), len(lo)))
