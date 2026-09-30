"""Round 3 (2026-09-28): apply showcase/look_r3.py to the EXISTING WorkFiles/dojo/build/showcase/layout_showcase.json
in place (plain Python, no Blender), so a look iteration in Unreal needs no re-compose. compose_showcase.py applies the
same module on its next run. Idempotent (look_r3.apply_materials restores each recipe's own values first).
Run: py -3 Scripts/dojo/showcase/apply_look_r3.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import look_r3  # noqa: E402

LAYOUT = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\showcase\layout_showcase.json")
L = json.loads(LAYOUT.read_text(encoding="utf-8"))
done = look_r3.apply_materials(L["materials"])
look_r3.check_no_invented_lamps(L["instances"])
L.setdefault("round3", {})["look_r3"] = done
L["round3"]["lamp_tune"] = look_r3.apply_lights(L["lights"])
L["round3"]["sun_f1"] = look_r3.apply_sun(L["sun"])   # round 3 fix f1: ENV sun
# the round-3 close-up cameras (look_r3.CLOSEUPS) replace any earlier CU_* entries, so a re-frame needs no re-compose
L["cameras"] = [c for c in L["cameras"] if not c["name"].startswith("CU_")] + [
    {"name": c[0], "loc": list(c[1]), "look_at": list(c[2]), "hfov_deg": c[3], "out_wh": list(c[4]), "note": c[5]}
    for c in look_r3.CLOSEUPS]
LAYOUT.write_text(json.dumps(L, indent=1), encoding="utf-8")
print("LOOK_R3 slots", len(done), json.dumps(done)[:600])
