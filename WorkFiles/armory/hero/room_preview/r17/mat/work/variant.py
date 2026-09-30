"""variant.py NAME key=val ... : tex_entrance.sisal_rib with overrides into r17/mat/Textures (trial sets only)."""
import sys, json
from pathlib import Path
sys.path.insert(0, r"C:\Users\Cody\Desktop\Blender_Projects\Scripts\armory\hero")
sys.path.insert(0, r"C:\Users\Cody\Desktop\Blender_Projects\Scripts\armory")
import tex_entrance as TE
TE.MT.OUT = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory\hero\room_preview\r17\mat\Textures")
kw = {}
for a in sys.argv[2:]:
    k, v = a.split("=")
    kw[k] = v if v.startswith("#") else float(v) if "." in v else int(v)
print(json.dumps(TE.sisal_rib(name=sys.argv[1], **kw)))
