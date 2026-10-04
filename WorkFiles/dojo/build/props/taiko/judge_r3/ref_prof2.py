from PIL import Image
import numpy as np
S='C:/Users/Cody/AppData/Local/Temp/claude/C--Users-Cody-Desktop-Blender-Projects--claude-worktrees-cardshop-build-integration-5227b4/24ade915-2f01-4a92-a0c7-405f2d922327/scratchpad/ref.png'
im=np.asarray(Image.open(S).convert('L')).astype(float)
def runs(row,x0,x1,th=120):
    d=row[x0:x1]<th
    out=[];s=None
    for i,v in enumerate(d):
        if v and s is None: s=i
        if not v and s is not None: out.append((x0+s,x0+i-1)); s=None
    return [r for r in out if r[1]-r[0]>4]
for y in range(200,250,2):
    # use min over 3 rows to suppress highlights? highlights are bright; use local band min
    row=im[y]
    r=runs(row,380,650)
    print(y, [(a,b,b-a+1) for a,b in r])
