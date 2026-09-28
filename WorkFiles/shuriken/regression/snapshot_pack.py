"""Snapshot the built pack as a regression baseline (plain Python, no Blender):

    py WorkFiles/shuriken/regression/snapshot_pack.py --name post_restyle_snapshot [--forms four_point,eight_point,square_plate]

Latest: post_kunai_plain (2026-09-19, library 3.10.0, all seven forms, after the plain kunai build; the kunai's second
slot maps, T_Kunai_Wrap_* and the blank T_Kunai_Lettering, are copied too).
Before: post_hooked_cross (2026-09-19, library 3.9.1, all six forms, after the hooked-cross MAINTENANCE pass; the 3.9.0
build's snapshot of the same name was moved to post_hooked_cross_build_3_9_0).
Before: post_hooked_cross_build_3_9_0 (2026-09-18, library 3.9.0, all six forms, after the hooked-cross build).
Before: post_spike_maint (2026-09-18, library 3.8.1, all five forms, after the spike maintenance pass).

Layout (the one compare_frozen.py reads): Shuriken.blend, export/<mesh>.fbx + .sockets.json,
textures/T_*.png, renders/*.png, scripts/ (Scripts/shuriken as built), <form>_report.json,
pack_report.json, SHA256SUMS.txt (every file except the renders, which the rig re-renders).
Refuses to overwrite an existing snapshot unless --force is given.
"""
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
MESH = {"four_point": "SM_Shuriken_FourPoint", "eight_point": "SM_Shuriken_EightPoint",
        "square_plate": "SM_Shuriken_SquarePlate", "six_point": "SM_Shuriken_SixPoint",
        "spike": "SM_Shuriken_Spike", "hooked_cross": "SM_Shuriken_HookedCross", "kunai_plain": "SM_Kunai_Plain"}
# 3.10: a form's maps beyond T_<form>_BC / _ORM / _N (the kunai's second material slot and its lettering mask)
EXTRA_TEXTURES = {"kunai_plain": ["T_Kunai_Wrap_BC", "T_Kunai_Wrap_ORM", "T_Kunai_Wrap_N", "T_Kunai_Wrap_Natural_BC",
                                  "T_Kunai_Lettering"]}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--name", required=True)
    parser.add_argument("--forms", default=",".join(MESH))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    forms = [f for f in args.forms.split(",") if f]
    dest = HERE / args.name
    if dest.exists():
        if not args.force:
            print(f"ERROR: {dest} exists (use --force to replace)")
            return 2
        shutil.rmtree(dest)
    copied = []

    def copy(src: Path, rel: str):
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        copied.append(rel)

    copy(PROJECT / "Assets" / "Shuriken.blend", "Shuriken.blend")
    for form in forms:
        mesh = MESH[form]
        for name in (f"{mesh}.fbx", f"{mesh}.sockets.json"):
            copy(PROJECT / "Exports" / "Shuriken" / name, f"export/{name}")
        for suffix in ("BC", "ORM", "N"):
            name = f"T_{mesh[len('SM_'):]}_{suffix}.png"
            copy(PROJECT / "Exports" / "Shuriken" / "Textures" / name, f"textures/{name}")
        for stem in EXTRA_TEXTURES.get(form, []):
            copy(PROJECT / "Exports" / "Shuriken" / "Textures" / f"{stem}.png", f"textures/{stem}.png")
        for shot in ("persp", "top", "wire", "lods", "lodgrind"):
            src = PROJECT / "Renders" / "Shuriken" / f"{form}_{shot}.png"
            if shot == "lodgrind" and not src.exists():
                continue                              # library < 3.7 renders no LOD grind close-up
            copy(src, f"renders/{form}_{shot}.png")
        copy(PROJECT / "WorkFiles" / "shuriken" / f"{form}_report.json", f"{form}_report.json")
    copy(PROJECT / "WorkFiles" / "shuriken" / "pack_report.json", "pack_report.json")
    scripts = PROJECT / "Scripts" / "shuriken"
    for path in sorted(scripts.glob("*.py")) + sorted((scripts / "shuriken_lib").glob("*.py")):
        copy(path, "scripts/" + str(path.relative_to(scripts)).replace("\\", "/"))
    sums = [f"{sha256(dest / rel)} *{rel}" for rel in copied if not rel.startswith("renders/")]
    (dest / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")
    manifest = {"snapshot": args.name, "forms": forms, "files": len(copied),
                "library_version": json.loads((dest / "pack_report.json").read_text(encoding="utf-8")).get("library_version")}
    (dest / "MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"SNAPSHOT {dest} files={len(copied)} sums={len(sums)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
