"""Finalise step 6: the final list of every LIVE file the blade-section rework changed, old -> new SHA-256.
Old hashes come from the pre-rework copies: regression/pre_blade_section (+ extras/), script_backups/
(full_tree_shuriken_3_10_1, *.before_blade_section.*), UnrealCheck6/*.before_blade_section.py.  Also re-checks that the
six frozen forms' 66 files still match prep/frozen_six_sha256.json and that files the rework must NOT touch are unchanged.
Writes final_change_list.json and final_change_list.md (the table appended to LIVE_CHANGES.md).
    py -3 final_change_list.py"""
import hashlib, json
from pathlib import Path

P = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
PRE = P / "WorkFiles/shuriken/regression/pre_blade_section"
SB = P / "WorkFiles/kunai/blade_section/script_backups"
HERE = P / "WorkFiles/kunai/blade_section/finalise"


def sha(p):
    p = Path(p)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


rows = []   # (live rel path, old source path or None, note)


def add(rel, old, note=""):
    rows.append((rel, old, note))


add("Assets/Shuriken.blend", PRE / "Shuriken.blend", "rebuilt by build_pack.py (stage2, promoted); the six forms inside are content-identical (compare_frozen)")
add("Exports/Shuriken/SM_Kunai_Plain.fbx", PRE / "export/SM_Kunai_Plain.fbx", "Unreal-verified (KunaiBladeC2, C3)")
add("Exports/Shuriken/SM_Kunai_Plain.sockets.json", PRE / "export/SM_Kunai_Plain.sockets.json", "")
for n in ("Plain_BC", "Plain_ORM", "Plain_N", "Wrap_BC", "Wrap_ORM", "Wrap_N", "Wrap_Natural_BC", "Lettering"):
    add(f"Exports/Shuriken/Textures/T_Kunai_{n}.png", PRE / f"textures/T_Kunai_{n}.png", "")
for n in ("T_Kunai_Wrap_Detail16.png", "recolour_maps.json", "recolour_constants.json"):
    add(f"Exports/Shuriken/Textures/Recolour/{n}", PRE / f"extras/Recolour/{n}", "materials step (make_kunai_wrap_detail.py + derive_constants.py --only Shuriken)")
add("Exports/Shuriken/MATERIALS_README.md", PRE / "extras/MATERIALS_README.md", "must be unchanged")
for shot in ("persp", "top", "wire", "lods", "lodgrind"):
    add(f"Renders/Shuriken/kunai_plain_{shot}.png", PRE / f"renders/kunai_plain_{shot}.png", "persp = the new 3/4 hero (yaw 35)" if shot == "persp" else "")
for n in ("kunai_plain_3q.png", "kunai_plain_neck_closeup.png", "kunai_plain_grip_closeup.png", "modern_line_sheet.png", "style_comparison.png"):
    add(f"Renders/Shuriken/{n}", PRE / f"extras/renders/{n}", "byte copy of kunai_plain_persp.png" if n == "kunai_plain_3q.png" else "")
add("WorkFiles/shuriken/kunai_plain_report.json", PRE / "kunai_plain_report.json", "engine_check verified (KunaiBladeC3 evidence); blade_section block")
add("WorkFiles/shuriken/pack_report.json", PRE / "pack_report.json", "kunai result + pack_consistency (knife coat rule); engine_checks_verified true")
add("WorkFiles/kunai/KUNAI_PLAIN_REPORT.md", SB / "KUNAI_PLAIN_REPORT.before_blade_section.md", "section 14")
add("References/Kunai/KUNAI_STUDY.md", SB / "KUNAI_STUDY.before_blade_section.md", "section 4 rows, sources, mass table, open question 2")
add("References/Kunai/LETTERING_HOWTO.md", P / "Backups/Shuriken_after_kunai_plain_2026-09-19/References/Kunai/LETTERING_HOWTO.md", "must be unchanged (band did not move)")
add("WorkFiles/materials/MATERIALS_REPORT.md", SB / "MATERIALS_REPORT.before_blade_section.md", "header note + section A8")
add("WorkFiles/kunai/plain_calc/kunai_plain_mass_check.py", SB / "WorkFiles/kunai/plain_calc/kunai_plain_mass_check.before_blade_section.py", "re-run with the 3.11 section")
add("WorkFiles/kunai/plain_calc/kunai_plain_mass_check.json", SB / "WorkFiles/kunai/plain_calc/kunai_plain_mass_check.before_blade_section.json", "154.06 g target; old figures kept in *_3_10_1_section.json")
add("Scripts/unreal/materials/maps/make_kunai_wrap_detail.py", SB / "make_kunai_wrap_detail.before_blade_section.py", "BLEND_SHA_BASELINE only")
lib_old = SB / "full_tree_shuriken_3_10_1"
live_sc = P / "Scripts/shuriken"
for f in sorted(live_sc.glob("*.py")) + sorted((live_sc / "shuriken_lib").glob("*.py")):
    rel = f.relative_to(live_sc).as_posix()
    add("Scripts/shuriken/" + rel, lib_old / rel, "")
uc = P / "WorkFiles/shuriken/UnrealCheck6"
for f in sorted(uc.glob("*.before_blade_section.py")):
    live = f.with_name(f.name.replace(".before_blade_section", ""))
    add(live.relative_to(P).as_posix(), f, "UnrealCheck6 harness (UC6_OUT / UC6_ATTACH_WRITE; defaults unchanged)")

out, changed, unchanged, must_not = [], 0, 0, []
for rel, old, note in rows:
    o, n = sha(old) if old else None, sha(P / rel)
    status = "new" if o is None else ("changed" if o != n else "unchanged")
    out.append({"file": rel, "old_sha256": o, "new_sha256": n, "status": status, "old_source": str(old) if old else None, "note": note})
    if "must be unchanged" in note and status != "unchanged":
        must_not.append(rel)
prep = json.loads((P / "WorkFiles/kunai/blade_section/prep/frozen_six_sha256.json").read_text(encoding="utf-8"))
six = {k: v["sha256"] for form in prep["forms"].values() for k, v in form.items()}
six_bad = [k for k, h in six.items() if sha(P / k) != h]
res = {"files": out, "changed": [r["file"] for r in out if r["status"] == "changed"],
       "unchanged_listed": [r["file"] for r in out if r["status"] == "unchanged"],
       "must_not_change_but_did": must_not,
       "frozen_six": {"files": len(six), "identical": len(six) - len(six_bad), "bad": six_bad}}
(HERE / "final_change_list.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
md = ["| Live file | Old SHA-256 (pre-rework) | New SHA-256 (shipped) | Note |", "|---|---|---|---|"]
for r in out:
    if r["status"] != "changed":
        continue
    md.append(f"| `{r['file']}` | `{r['old_sha256']}` | `{r['new_sha256']}` | {r['note']} |")
(HERE / "final_change_list.md").write_text("\n".join(md) + "\n", encoding="utf-8")
print(json.dumps({"changed": len(res["changed"]), "unchanged_listed": res["unchanged_listed"], "must_not": must_not,
                  "frozen_six": res["frozen_six"]}))
