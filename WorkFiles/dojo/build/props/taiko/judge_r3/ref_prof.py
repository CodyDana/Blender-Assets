from PIL import Image
import numpy as np
from scipy import ndimage as nd
S='C:/Users/Cody/AppData/Local/Temp/claude/C--Users-Cody-Desktop-Blender-Projects--claude-worktrees-cardshop-build-integration-5227b4/24ade915-2f01-4a92-a0c7-405f2d922327/scratchpad/ref.png'
im=np.asarray(Image.open(S).convert('L')).astype(float)
sub=im[150:280,400:640]
dark=(sub<90)
print('dark per y:', [(150+i,int(v)) for i,v in enumerate(dark.sum(1)) if v>0])
# fill highlights: closing
m=nd.binary_closing(im<110,iterations=2)
m=nd.binary_fill_holes(m)
lab,n=nd.label(m[180:265,300:740])
for i,sl in enumerate(nd.find_objects(lab)):
    h=sl[0].stop-sl[0].start; w=sl[1].stop-sl[1].start
    cy=(sl[0].start+sl[0].stop)/2+180; cx=(sl[1].start+sl[1].stop)/2+300
    area=(lab[sl]==i+1).sum()
    if area>80: print('blob cx %.1f cy %.1f w %d h %d area %d'%(cx,cy,w,h,area))
