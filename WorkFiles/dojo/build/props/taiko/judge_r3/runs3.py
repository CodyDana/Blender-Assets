from PIL import Image
import numpy as np
def runs(row,x0,x1,th):
    d=row[x0:x1]<th; out=[];s=None
    for i,v in enumerate(d):
        if v and s is None: s=i
        if not v and s is not None: out.append((x0+s,x0+i-1)); s=None
    return [(a,b,b-a+1) for a,b in out if b-a>3]
for f in ['../t3/drum_front_standing_photo.png','../t3/drum_front_standing.png']:
    L=np.asarray(Image.open(f).convert('L')).astype(float)
    print(f)
    for y in (172,173,174,197,198): print(y, runs(L[y],420,620,120), runs(L[y],420,620,160))
    for x in (497,512,526,483):
        col=L[150:215,x]; print('col',x,[150+i for i,v in enumerate(col) if v<120][:1],[150+i for i,v in enumerate(col) if v<120][-1:])
