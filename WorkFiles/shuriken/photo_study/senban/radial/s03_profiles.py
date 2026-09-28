import sys
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/senban/radial")
import numpy as np
from common import *

rgb = load_rgb()
L = rgb.mean(-1)
chroma = rgb[..., 0] - rgb[..., 2]
def show(tag, pts):
    for (x, y) in pts:
        print(tag, "x=%d y=%d" % (x, y), rgb[y, x].round(3), "L=%.3f rb=%.3f" % (L[y, x], chroma[y, x]))

# hole interior grid
for y in range(370, 600, 20):
    print("HOLEROW y=%d" % y, " ".join("%.2f" % L[y, x] for x in range(380, 640, 10)))
# vertical profile across hole bottom at x=500 and x=430, 590
for x in (420, 500, 600):
    show("HBOT", [(x, y) for y in range(560, 612, 2)])
# vertical profile across hole top
show("HTOP", [(500, y) for y in range(345, 375, 1)])
# horizontal across hole left and right
show("HLEFT", [(x, 470) for x in range(375, 405, 1)])
show("HRIGHT", [(x, 470) for x in range(610, 640, 1)])
# right outer edge
show("RIGHT", [(x, 470) for x in range(850, 930, 2)])
# body samples
body = L[300:340, 250:300]
print("BODY L mean %.3f p5 %.3f p95 %.3f" % (body.mean(), np.percentile(body, 5), np.percentile(body, 95)))
