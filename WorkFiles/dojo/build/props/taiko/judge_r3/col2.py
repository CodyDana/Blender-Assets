from PIL import Image
import numpy as np
im=np.asarray(Image.open('../t3/drum_front_standing_photo.png').convert('RGB')).astype(int)
for y in range(110,260,2):
    print(y, im[y,505:520].mean(0).astype(int), im[y,480:490].mean(0).astype(int))
# horizontal runs at upper row
def runs(row,x0,x1,th=80):
    d=row[x0:x1]<th; out=[];s=None
    for i,v in enumerate(d):
        if v and s is None: s=i
        if not v and s is not None: out.append((x0+s,x0+i-1)); s=None
    return [(a,b,b-a+1) for a,b in out if b-a>3]
L=np.asarray(Image.open('../t3/drum_front_standing_photo.png').convert('L')).astype(float)
for y in range(155,210,2): print(y, runs(L[y],420,620))
