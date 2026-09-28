"""Stage 1: zoomed crops for visual inspection (contrast-stretched)."""
import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/reference_metrology")
from fm_lib import *
import json
crops = json.loads(sys.argv[sys.argv.index('--')+1])
for c in crops:
    i, x0, y0, x1, y1, sc, gain, name = c
    a = load(i)[y0:y1, x0:x1]
    if gain != 1:
        a = np.clip(a * gain, 0, 1)
    save_png(a, name, sc)
print("done")
