"""gen.py NAME [fn=sisal_cord] key=val ... : a trial set into work2/tex (test only)"""
import sys, json
from pathlib import Path
sys.path.insert(0, r"C:\Users\Cody\Desktop\Blender_Projects\Scripts\armory\hero")
sys.path.insert(0, r"C:\Users\Cody\Desktop\Blender_Projects\Scripts\armory")
import tex_entrance as TE
TE.MT.OUT = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory\hero\room_preview\r18\mat\work2\tex")
fn = TE.sisal_cord
kw = {}
for a in sys.argv[2:]:
    k, v = a.split("=")
    if k == "fn":
        fn = getattr(TE, v); continue
    kw[k] = v if v.startswith("#") else float(v) if "." in v else int(v)
print(json.dumps(fn(name=sys.argv[1], **kw)))
