"""W6: run gunlib's deny list (qa_gun.deny_hits, read-only import) over every shipped text and name of SR01.

    blender.exe -b --factory-startup --python w6_deny_scan.py -- <repo_root> <out_json>

Scans: every line of every text file in Exports/Guns/SR01 (README, MATERIALS_README, *.json sidecars, recolour JSON),
every file name in Exports/Guns/SR01 and showcase/SniperRifle_SR01, and every object, mesh, material, bone and empty
(socket) name inside every shipped FBX (imported headless). Also lists maker / product words the deny list may not
hold (EXTRA, a short safety net for the docs).
"""
import json
import re
import sys
from pathlib import Path

import bpy

a = sys.argv[sys.argv.index("--") + 1:]
ROOT, OUT = Path(a[0]), Path(a[1])
sys.path.insert(0, str(ROOT / "Scripts" / "guns"))
from gunlib import qa_gun  # noqa: E402

EXTRA = re.compile(r"\b(accuracy international|remington|barrett|sako|tikka|savage|ruger|mcmillan|magpul|harris|"
                   r"atlas|leupold|vortex|nightforce|schmidt|bender|zeiss|swarovski|cerakote|picatinny|mil-?std|"
                   r"glock|colt|beretta|h&k|heckler|steyr|fn |sig sauer|awm|aics|m24|m40|l96|trg)\b", re.I)
E = ROOT / "Exports" / "Guns" / "SR01"
S = ROOT / "showcase" / "SniperRifle_SR01"
hits, extra, n_lines, names = [], [], 0, set()
for f in sorted(E.rglob("*")):
    names.add(f.name)
    if f.suffix.lower() in (".md", ".json", ".txt"):
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            n_lines += 1
            h = qa_gun.deny_hits(line)
            if h:
                hits.append({"file": f.relative_to(ROOT).as_posix(), "line": i, "terms": h})
            for m in EXTRA.finditer(line):
                extra.append({"file": f.relative_to(ROOT).as_posix(), "line": i, "word": m.group(0)})
for f in sorted(S.glob("*")):
    names.add(f.name)
for fbx in sorted(E.rglob("*.fbx")):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(fbx))
    for o in bpy.data.objects:
        names.add(o.name)
        if o.type == "ARMATURE":
            names.update(b.name for b in o.data.bones)
    names.update(m.name for m in bpy.data.materials)
    names.update(m.name for m in bpy.data.meshes)
    names.update(ac.name for ac in bpy.data.actions)
name_hits = {n: qa_gun.deny_hits(n) for n in sorted(names) if qa_gun.deny_hits(n)}
name_extra = sorted(n for n in names if EXTRA.search(n.replace("_", " ")))
rep = {"deny_terms": len(qa_gun.GUN_DENY), "text_lines_scanned": n_lines, "names_scanned": len(names),
       "text_hits": hits, "name_hits": name_hits, "extra_word_hits_text": extra, "extra_word_hits_names": name_extra,
       "pass": not hits and not name_hits and not extra and not name_extra}
OUT.write_text(json.dumps(rep, indent=1))
print("DENY_SCAN", json.dumps({k: (len(v) if isinstance(v, (list, dict)) else v) for k, v in rep.items()}))
