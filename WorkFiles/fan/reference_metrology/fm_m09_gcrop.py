"""Stage 9: gamma-boosted image-space crops."""
import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/reference_metrology")
from fm_lib import *
import json
for i, x0, y0, x1, y1, sc, gain, gam, name in json.loads(sys.argv[sys.argv.index('--')+1]):
    a = load(i)[y0:y1, x0:x1]
    a = np.clip(a*gain, 0, 1)**gam
    save_png(a, name, sc)
print("done")
