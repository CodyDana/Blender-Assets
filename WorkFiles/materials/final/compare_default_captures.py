"""Default look unchanged by the final pass: the stored-level base-colour captures of every default instance, r2b (before)
vs f2 (after). Pure numpy + the PNG reader (Blender's bundled Python or blender -b)."""
import json, sys
from pathlib import Path
import numpy as np
P = Path("C:/Users/Cody/Desktop/Blender_Projects")
sys.path.insert(0, str(P / "Scripts/unreal/materials/maps")); sys.dont_write_bytecode = True
import recolour_common as rc
before = P / "WorkFiles/materials/final/pre_final_snapshot/ue_renders/basecolour"
after = P / "WorkFiles/materials/ue_renders/basecolour"
out = {}
for f in sorted(before.glob("uv_*default*.png")):
    g = after / f.name
    if not g.exists():
        out[f.name] = "missing after"; continue
    a, _, _ = rc.png_read(f); b, _, _ = rc.png_read(g)
    d = np.abs(a[..., :3].astype(int) - b[..., :3].astype(int)).max(-1)
    out[f.name] = {"identical": bool((d == 0).all()), "max": int(d.max()), "texels_diff": int((d > 0).sum()), "texels": int(d.size)}
    print(f.name, out[f.name])
(P / "WorkFiles/materials/final/default_captures_before_after.json").write_text(json.dumps(out, indent=1))
