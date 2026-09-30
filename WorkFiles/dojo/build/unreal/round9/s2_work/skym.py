"""Round 9 s2 sky metrics on CAM_Ref2Match (1920x1440, rows 0..280 = above the far ridges) vs ref 2 rows 0..100:
median, clear-gap colour (the bluest 30 % by R-B), lit-cloud colour (the reddest 20 %), luma p10/p90, unique colours,
zero-gradient share. usage: py -3 skym.py <png> [...]"""
import sys, numpy as np
from PIL import Image
def m(a):
    px = a.reshape(-1, 3).astype(float); rb = px[:, 0] - px[:, 2]; lu = px @ [.2126, .7152, .0722]
    g = np.median(px[rb < np.percentile(rb, 30)], 0).astype(int); c = np.median(px[rb > np.percentile(rb, 80)], 0).astype(int)
    r = a.astype(np.int32)
    zg = ((np.abs(np.diff(r, axis=1)).sum(2) == 0).mean() + (np.abs(np.diff(r, axis=0)).sum(2) == 0).mean()) / 2 * 100
    u = len(np.unique(a.reshape(-1, 3), axis=0))
    return f"med {np.median(px,0).astype(int)} gaps {g} clouds {c} luma p10 {np.percentile(lu,10):.0f} p90 {np.percentile(lu,90):.0f} uniq {u} zg {zg:.1f}%"
ref = np.asarray(Image.open(r"C:/Users/Cody/Desktop/Blender_Projects/References/Dojo/dojo1_reference2.png").convert("RGB"))
print(f"{'ref2':14s}", m(ref[0:100, 40:1400]))
for p in sys.argv[1:]:
    a = np.asarray(Image.open(p).convert("RGB"))
    print(f"{p.split('/')[-1][:-4][:14]:14s}", m(a[0:280]))
