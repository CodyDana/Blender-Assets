"""Round-2 (2026-09-28) fixes applied to the EXISTING WorkFiles/dojo/build/showcase/layout_showcase.json in place (plain
Python, no Blender), so the Unreal steps can run without re-composing the showcase; compose_showcase.py applies the same
rules on its next run. Idempotent (a re-run changes nothing and keeps the first run's record under "round2").
  1 markers: marker_policy.apply (pavilion-pad bottom +1.50; stale Wall_S_W2 / Wall_S_E1 removed)
  2 sun: SUN_KELVIN (5500 K at the light). UE's atmosphere sun already reddens a 13 deg sun (the colour probe: a white
    6500 K light reads as warm as Blender's sun colour (1.0, 0.63, 0.36)); 4300 K on top doubled the warmth (probe B4 /
    B0: lit grey card saturation 0.59) and was one source of the orange cast.
Run: py -3 Scripts/dojo/showcase/apply_round2.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import marker_policy  # noqa: E402

SUN_KELVIN = marker_policy.SUN_KELVIN
LAYOUT = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\showcase\layout_showcase.json")
L = json.loads(LAYOUT.read_text(encoding="utf-8"))
n0 = len(L["traversal_markers"])
_, rep = marker_policy.apply(L["traversal_markers"], L["climb_routes"])
r2 = L.setdefault("round2", {})
if rep["removed"] or rep["raised"]:
    r2["markers"] = rep
if L["sun"]["kelvin"] != SUN_KELVIN:
    r2["sun"] = {"old_kelvin": L["sun"]["kelvin"], "new_kelvin": SUN_KELVIN}
    L["sun"]["kelvin"] = SUN_KELVIN
    L["sun"]["note"] = marker_policy.SUN_NOTE
LAYOUT.write_text(json.dumps(L, indent=1), encoding="utf-8")
print("ROUND2 markers", n0, "->", len(L["traversal_markers"]), "sun", L["sun"]["kelvin"], json.dumps(r2)[:400])
