"""Finalise step 5: Backups/Shuriken_after_kunai_blade_section_2026-09-26/, laid out like
Backups/Shuriken_after_kunai_plain_2026-09-19/ (blend, Exports/Shuriken + Textures, References/Kunai, Renders/Shuriken,
reports/, Scripts/shuriken), plus what this rework touched that the Sep 19 backup had no slot for: Exports/Shuriken/
MATERIALS_README.md and Textures/Recolour/, Scripts/unreal/materials/maps/make_kunai_wrap_detail.py,
WorkFiles/materials/MATERIALS_REPORT.md and the 3.11.1 material no-op proof.  Read-only on every source; refuses to
overwrite.  Writes BACKUP_SHA256SUMS.txt and verifies every copy against its source.
    py -3 make_backup.py"""
import hashlib, json, shutil, sys
from pathlib import Path

P = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
DEST = P / "Backups" / "Shuriken_after_kunai_blade_section_2026-09-26"
if DEST.exists():
    print("ERROR: exists", DEST); sys.exit(2)
pairs = []   # (source, relative destination)
pairs.append((P / "Assets/Shuriken.blend", "Shuriken.blend"))
ex = P / "Exports/Shuriken"
for f in sorted(ex.glob("*")):
    if f.is_file():
        pairs.append((f, f"Exports/Shuriken/{f.name}"))
for f in sorted((ex / "Textures").glob("*.png")):
    pairs.append((f, f"Exports/Shuriken/Textures/{f.name}"))
for f in sorted((ex / "Textures/Recolour").rglob("*")):
    if f.is_file():
        pairs.append((f, "Exports/Shuriken/Textures/Recolour/" + f.relative_to(ex / "Textures/Recolour").as_posix()))
for name in ("KUNAI_STUDY.md", "LETTERING_HOWTO.md", "sources.md"):
    pairs.append((P / "References/Kunai" / name, f"References/Kunai/{name}"))
for f in sorted((P / "Renders/Shuriken").glob("*.png")):
    pairs.append((f, f"Renders/Shuriken/{f.name}"))
ws = P / "WorkFiles/shuriken"
for form in ("four_point", "eight_point", "square_plate", "six_point", "spike", "hooked_cross", "kunai_plain"):
    pairs.append((ws / f"{form}_report.json", f"reports/{form}_report.json"))
pairs.append((ws / "pack_report.json", "reports/pack_report.json"))
pairs.append((P / "WorkFiles/kunai/KUNAI_PLAIN_REPORT.md", "reports/KUNAI_PLAIN_REPORT.md"))
pairs.append((P / "WorkFiles/kunai/blade_section/fix_r1/material_noop_check_3_11_1.json", "reports/material_noop_check_3_11_1.json"))
pairs.append((P / "WorkFiles/materials/MATERIALS_REPORT.md", "reports/MATERIALS_REPORT.md"))
sc = P / "Scripts/shuriken"
for f in sorted(sc.glob("*.py")) + sorted((sc / "shuriken_lib").glob("*.py")):
    pairs.append((f, "Scripts/shuriken/" + f.relative_to(sc).as_posix()))
pairs.append((P / "Scripts/unreal/materials/maps/make_kunai_wrap_detail.py", "Scripts/unreal/materials/maps/make_kunai_wrap_detail.py"))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


lines, bad = [], []
for src, rel in pairs:
    tgt = DEST / rel
    tgt.parent.mkdir(parents=True, exist_ok=True)
    h0 = sha(src)
    shutil.copy2(src, tgt)
    h1, h2 = sha(tgt), sha(src)
    if not (h0 == h1 == h2):
        bad.append(rel)
    lines.append(f"{h1} *{rel}")
(DEST / "BACKUP_SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
# re-verify the manifest from disk
bad2 = [ln.split(" *", 1)[1] for ln in lines if sha(DEST / ln.split(" *", 1)[1]) != ln.split(" *", 1)[0]]
summary = {"dest": str(DEST), "files": len(pairs), "bytes": sum((DEST / r).stat().st_size for _, r in pairs),
           "copy_mismatch": bad, "manifest_reverify_bad": bad2, "verified": not bad and not bad2}
(DEST / "BACKUP_MANIFEST.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary))
