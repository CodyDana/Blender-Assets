# VERIFIER: would dj_armory_sync's FILE stage copy anything now? (ArmoryLab source sha vs the DojoLab copy; read-only)
import hashlib, json
from pathlib import Path
F = json.loads(Path(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/unreal/armory_sync/files.json").read_text())
A = Path(r"C:/Users/Cody/Documents/Unreal Projects/ArmoryLab/Content"); D = Path(r"C:/Users/Cody/Documents/Unreal Projects/DojoLab/Content")
sh = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
would, drift = [], []
for pkg, h in F["sha"].items():
    rel = pkg[len("/Game/"):] + ".uasset"
    a, d = A / rel, D / rel
    ha = sh(a) if a.exists() else None
    hd = sh(d) if d.exists() else None
    if ha != hd: would.append(pkg)
    if ha != h: drift.append(pkg)
out = {"packages": len(F["sha"]), "would_copy": would, "armorylab_changed_since_sync": drift, "files_json_date": F.get("date")}
Path("json/files_stage_check.json").write_text(json.dumps(out, indent=1))
print(out["packages"], len(would), len(drift), F.get("date"))
