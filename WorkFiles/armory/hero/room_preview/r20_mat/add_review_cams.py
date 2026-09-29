"""Test copy only: add the r20_mat review cameras to this folder's layout.json (not the live layout)."""
import json, sys
from pathlib import Path
p = Path(__file__).resolve().parent / "layout.json"
d = json.loads(p.read_text(encoding="utf-8"))
extra = [
    {"name": "CE_EntryDown", "loc": [4.4, 4.9, 2.5], "look_at": [5.4, 1.7, -0.1], "lens_mm": 24},
    {"name": "CE_MatTop", "loc": [6.0, 0.35, 3.3], "look_at": [6.0, 1.85, -0.12], "lens_mm": 26},
    {"name": "CE_BarFromMat", "loc": [6.0, 0.3, 1.65], "look_at": [6.0, 2.9, 0.0], "lens_mm": 22},
]
names = {c["name"] for c in extra}
d["cameras"] = [c for c in d["cameras"] if c["name"] not in names] + extra
p.write_text(json.dumps(d, indent=1), encoding="utf-8")
print("cameras", [c["name"] for c in d["cameras"]])
