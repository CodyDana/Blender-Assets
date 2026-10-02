"""Re-pack the flipbook atlases from the rendered EXRs (no re-render). blender -b --factory-startup --python repack.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fx_common as fx  # noqa: E402
import render_flipbooks as RF  # noqa: E402

path = fx.WORK / "json/flipbooks.json"
meta = fx.load_json(path) if path.exists() else {}
for name in ("MistPuff", "MistWisp", "SprayBurst"):
    keep = {k: v for k, v in meta.get(name, {}).items() if k in ("method", "render_sec")}
    meta[name] = RF.pack(name, 64, 8, 512, keep)
    print("PACKED", name, meta[name]["norm_factor"])
meta["Haze"] = RF.pack_haze()
print("PACKED Haze")
fx.write_json(path, meta)
