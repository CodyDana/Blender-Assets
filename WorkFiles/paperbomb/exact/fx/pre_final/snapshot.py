"""Snapshot the built paper bomb as a regression baseline (plain Python, no Blender).

    py WorkFiles/paperbomb/regression/snapshot.py --name post_paper_bomb [--force]

Modelled on WorkFiles/shuriken/regression/snapshot_pack.py, which is frozen; this is the
prop line's own copy, so the fan and the smoke bomb inherit it.

WHAT IT COPIES, AND WHY EACH PIECE IS IN THE SET
------------------------------------------------
    PaperBomb.blend          the built scene, so a later build can be diffed against it
    export/                  the exact shipped bytes: FBX, sockets sidecar, README
    textures/                the four maps
    renders/                 the gallery set
    scripts/                 Scripts/props as it stood, minus __pycache__: a hash change
                             in the FBX is only actionable if you can see the source
                             that produced it
    paperbomb_report.json    every number the build measured
    PAPERBOMB_REPORT.md      the prose
    SHA256SUMS.txt           every file above EXCEPT the renders

The renders are deliberately outside the hash set.  Cycles is not bit-reproducible -
denoising and tile scheduling move the last bits - so hashing them would make the
comparison fail on every run for no reason.  They are copied so a human can look at them
and compare, and ``compare.py`` measures them statistically instead.

Refuses to overwrite an existing snapshot unless ``--force`` is given.
"""
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
MESH = "SM_PaperBomb"
TEXTURES = ("BC", "ORM", "N", "M")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_tree(src: Path, dst: Path, skip=("__pycache__",)) -> list:
    out = []
    for item in sorted(src.rglob("*")):
        if any(part in skip for part in item.parts):
            continue
        if item.is_dir():
            continue
        target = dst / item.relative_to(src)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)
        out.append(target)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--name", required=True)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    dest = HERE / args.name
    if dest.exists() and not args.force:
        print(f"refusing to overwrite {dest} - pass --force if you mean it")
        return 2
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    hashed: list = []
    unhashed: list = []

    blend = PROJECT / "Assets" / "PaperBomb.blend"
    shutil.copy2(blend, dest / blend.name)
    hashed.append(dest / blend.name)

    exports = PROJECT / "Exports" / "PaperBomb"
    (dest / "export").mkdir()
    for name in (f"{MESH}.fbx", f"{MESH}.sockets.json", "README.txt"):
        src = exports / name
        if src.is_file():
            shutil.copy2(src, dest / "export" / name)
            hashed.append(dest / "export" / name)
    (dest / "textures").mkdir()
    for suffix in TEXTURES:
        src = exports / "Textures" / f"T_PaperBomb_{suffix}.png"
        shutil.copy2(src, dest / "textures" / src.name)
        hashed.append(dest / "textures" / src.name)

    (dest / "renders").mkdir()
    for src in sorted((PROJECT / "Renders" / "PaperBomb").glob("*.png")):
        shutil.copy2(src, dest / "renders" / src.name)
        unhashed.append(dest / "renders" / src.name)

    hashed += copy_tree(PROJECT / "Scripts" / "props", dest / "scripts")

    work = PROJECT / "WorkFiles" / "paperbomb"
    for name in ("paperbomb_report.json", "PAPERBOMB_REPORT.md", "full_build.log"):
        src = work / name
        if src.is_file():
            shutil.copy2(src, dest / name)
            if name != "full_build.log":
                hashed.append(dest / name)

    lines = [f"{sha256(p)}  {p.relative_to(dest).as_posix()}" for p in sorted(hashed)]
    (dest / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf8")

    report = json.loads((work / "paperbomb_report.json").read_text(encoding="utf8"))
    manifest = {
        "name": args.name,
        "mesh": MESH,
        "lod_triangles": report.get("lod_triangles"),
        "lod_screen_sizes": report.get("lod_screen_sizes"),
        "bounds_radius_mm": report.get("bounds_radius_mm"),
        "size_cm": report.get("size_cm"),
        "fbx_sha256": (report.get("export") or {}).get("sha256"),
        "texture_sha256": (report.get("textures") or {}).get("sha256"),
        "gates": report.get("gates"),
        "files_hashed": len(hashed),
        "files_copied_unhashed": [p.name for p in unhashed],
        "note": ("renders are copied but NOT hashed: Cycles is not bit-reproducible, so "
                 "compare.py measures them statistically instead"),
    }
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf8")
    print(f"snapshot {dest}  {len(hashed)} files hashed, {len(unhashed)} renders copied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
