"""Byte checks for the finalise step (plain Python):
 1. every file of regression/post_blade_section (113 + extras) == its live source;
 2. the six frozen forms' 66 live files == WorkFiles/kunai/blade_section/prep/frozen_six_sha256.json;
 3. the six forms' files in post_blade_section == the same files in pre_blade_section (the frozen six did not move).
    py -3 byte_checks.py <out.json>"""
import hashlib, json, sys
from pathlib import Path
P = Path(r"C:\Users\Cody\Desktop\Blender_Projects"); R = P / "WorkFiles/shuriken/regression"
NEW, PRE = R / "post_blade_section", R / "pre_blade_section"
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
MESH = {"four_point": "SM_Shuriken_FourPoint", "eight_point": "SM_Shuriken_EightPoint", "square_plate": "SM_Shuriken_SquarePlate",
        "six_point": "SM_Shuriken_SixPoint", "spike": "SM_Shuriken_Spike", "hooked_cross": "SM_Shuriken_HookedCross", "kunai_plain": "SM_Kunai_Plain"}
def live_of(rel):
    parts = rel.split("/")
    if rel == "Shuriken.blend": return P / "Assets/Shuriken.blend"
    if parts[0] == "export": return P / "Exports/Shuriken" / parts[1]
    if parts[0] == "textures": return P / "Exports/Shuriken/Textures" / parts[1]
    if parts[0] == "renders": return P / "Renders/Shuriken" / parts[1]
    if parts[0] == "scripts": return P / "Scripts/shuriken" / "/".join(parts[1:])
    if parts[0] == "extras":
        if parts[1] == "MATERIALS_README.md": return P / "Exports/Shuriken/MATERIALS_README.md"
        if parts[1] == "Recolour": return P / "Exports/Shuriken/Textures/Recolour" / parts[2]
        if parts[1] == "renders": return P / "Renders/Shuriken" / parts[2]
    if rel.endswith("_report.json"): return P / "WorkFiles/shuriken" / rel
    return None
res = {"snapshot_vs_live": {}, "mismatches": []}
files = [f for f in NEW.rglob("*") if f.is_file() and f.name not in ("SHA256SUMS.txt", "MANIFEST.json", "SHA256SUMS_extras.txt")]
for f in sorted(files):
    rel = f.relative_to(NEW).as_posix(); src = live_of(rel)
    ok = src is not None and src.exists() and sha(src) == sha(f)
    if not ok: res["mismatches"].append(rel)
res["snapshot_vs_live"] = {"files": len(files), "identical": len(files) - len(res["mismatches"])}
# SHA256SUMS.txt self-consistency
bad = []
for line in (NEW / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
    h, rel = line.split(" *", 1)
    if sha(NEW / rel) != h: bad.append(rel)
res["sha256sums_txt_lines_bad"] = bad
prep = json.loads((P / "WorkFiles/kunai/blade_section/prep/frozen_six_sha256.json").read_text(encoding="utf-8"))
items = {k: v for form in prep["forms"].values() for k, v in form.items()}
tot = 0; badp = []
for k, v in items.items():
    pth = Path(k) if Path(k).is_absolute() else P / k
    h = v if isinstance(v, str) else v.get("sha256")
    tot += 1
    if sha(pth) != h: badp.append(k)
res["frozen_six_vs_prep_list"] = {"files": tot, "identical": tot - len(badp), "bad": badp}
six = [f for f in MESH if f != "kunai_plain"]; cmp_ = {"files": 0, "identical": 0, "bad": []}
for f in sorted(files):
    rel = f.relative_to(NEW).as_posix()
    if rel.startswith(("scripts/", "extras/")) or rel in ("Shuriken.blend", "pack_report.json"): continue
    form = next((x for x in six if rel.startswith((f"renders/{x}_", f"{x}_report")) or MESH[x][3:] in rel), None)
    if not form: continue
    cmp_["files"] += 1
    if (PRE / rel).exists() and sha(PRE / rel) == sha(f): cmp_["identical"] += 1
    else: cmp_["bad"].append(rel)
res["six_in_post_vs_pre_blade_section"] = cmp_
Path(sys.argv[1]).write_text(json.dumps(res, indent=2), encoding="utf-8")
print(json.dumps({k: v for k, v in res.items()}))
