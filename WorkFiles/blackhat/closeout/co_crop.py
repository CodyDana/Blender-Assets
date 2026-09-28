"""Close-out: old-vs-new (or ref-vs-new) crops.  blender -b --factory-startup --python co_crop.py -- A.png B.png OUT.png scale x0,y0,x1,y1 ..."""
import sys
from pathlib import Path
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
from props_lib import blackhat_look as LK
a = sys.argv[sys.argv.index("--") + 1:]
boxes = [tuple(int(v) for v in b.split(",")) for b in a[4:]]
LK.crops_sheet(a[0], Path(a[1]), Path(a[2]), boxes, scale=int(a[3]))
