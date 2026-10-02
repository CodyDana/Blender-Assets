"""LANDSCAPE ROUND (world stage): FILE COPY of the owned scenery the plan chose into DojoLab (never Migrate, never a
write into the source). Each package keeps its /Game/<Pack>/ path, so its references resolve unchanged.

Dependency closure: every seed .uasset/.umap is scanned for package names ('/Game/...' strings in its name table); each
one that exists in the same source Content folder is added (with its .uexp / .ubulk / .uptnl companions), recursively.
Packages outside /Game (/Engine, /Script, plugin mounts such as /Water or /ProceduralVegetationEditor) are listed, not
copied. A file that already exists in DojoLab with the same size and sha256 is skipped; a different existing file is
NOT overwritten (reported), so a re-run is idempotent and never clobbers.

Run: py -3 -B copy_owned.py [--dry]      Out: WorkFiles/dojo/build/landscape/world/json/copy_owned.json
"""
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

VAULT = Path(r"C:\ProgramData\Epic\EpicGamesLauncher\VaultCache")
SCEN = Path(r"C:\Users\Cody\Documents\Unreal Projects\Scenery_Tutorial\Content")
DST = Path(r"C:\Users\Cody\Documents\Unreal Projects\DojoLab\Content")
OUT = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\landscape\world\json\copy_owned.json")
FISH = VAULT / "NordicFi1d739256ce1cV1" / "data" / "Content"
MEGA = VAULT / "Megaplanb3dc3e6c5a59V1" / "data" / "Content"
NIAG = VAULT / "NiagaraExamplesPack" / "data" / "Content"

# (source Content root, seed globs relative to it, why)
SEEDS = [
    (FISH, ["Fishermans_Cabin/Meshes/Foliage/Tree/*.uasset"], "FZ1-FZ4 conifer forest (firs + billboard impostor)"),
    (FISH, ["Fishermans_Cabin/Meshes/Foliage/Bush/*.uasset"], "interim rounded shrubs (forecourt, stair sides, banks)"),
    (FISH, ["Fishermans_Cabin/Meshes/Foliage/Grass/*.uasset"], "grass / moss-bank scatter"),
    (FISH, ["Fishermans_Cabin/Meshes/Rocks/*.uasset"], "the only owned boulders (BF1-BF3, C1 stand-ins)"),
    (FISH, ["Fishermans_Cabin/Meshes/Small_Rocks/*.uasset"], "waterline / path-edge pebbles"),
    (FISH, ["Fishermans_Cabin/Meshes/Mountains/*.uasset"], "peaks option A (SM_Mountain_01 + MI_Mountain / MF_Snow)"),
    (FISH, ["Fishermans_Cabin/Textures/Tiling_Textures/Ground_Grass/*.uasset",
            "Fishermans_Cabin/Textures/Tiling_Textures/Ground_Dirt/*.uasset",
            "Fishermans_Cabin/Textures/Tiling_Textures/Ground_Dirt_Cracked/*.uasset",
            "Fishermans_Cabin/Textures/Tiling_Textures/Rock/*.uasset",
            "Fishermans_Cabin/Textures/Tiling_Textures/Fog_Cards/*.uasset"], "landscape layers (grass, dirt, rock slope) + fog cards"),
    (SCEN, ["Megascans/Surfaces/MossyRockyGround/*.uasset", "Megascans/Surfaces/Mossy_Rocky_Ground_vcrkeax/*.uasset",
            "Megascans/Surfaces/MossyGrass/*.uasset", "Megascans/Surfaces/ForestGround/*.uasset",
            "Megascans/Surfaces/MossyCreekStones/*.uasset", "Megascans/Surfaces/BeachCliff/*.uasset",
            "Megascans/Surfaces/Snow/*.uasset"], "landscape layers (moss, forest floor, river bed, cliff, snow)"),
    (SCEN, ["Landscape/Textures/T_MacroVariation.uasset", "Landscape/Textures/T_NoiseMask_RGB.uasset",
            "Landscape/Patches/T_Land_Mountain01.uasset", "Landscape/Patches/T_Land_Mountain02.uasset",
            "Landscape/Patches/T_Land_Erosion00.uasset", "Landscape/Patches/T_Land_Erosion01.uasset"],
     "macro variation + the heightmap patch stamps"),
    (MEGA, ["Megaplant_Library/Tree_Japanese_Cypress/Tree_Japanese_Cypress_01/*.uasset"],
     "5 Megaplants Japanese Cypress behind the hall (Route B)"),
    # NOT copied: NiagaraExamples FX_Fog. Its packages reference the plugin mount /NiagaraExamples/..., not /Game, so a
    # Content copy would not resolve; the low mist uses the engine's Local Fog Volume (the FX stage decides the rest).
]
COMPANIONS = (".uasset", ".umap", ".uexp", ".ubulk", ".uptnl")
PKG_RE = re.compile(rb"/Game/[A-Za-z0-9_\-/\.]+")
OTHER_RE = re.compile(rb"/(?:Engine|Water|ProceduralVegetationEditor|PVE|Niagara|NiagaraFluids|DynamicWind)[A-Za-z0-9_\-]*/[A-Za-z0-9_\-/\.]+")


def pkg_files(root, rel_noext):
    return [root / (rel_noext + ext) for ext in COMPANIONS if (root / (rel_noext + ext)).exists()]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def closure(root, seeds):
    todo = list(seeds)
    seen, missing, external = set(), set(), set()
    while todo:
        rel = todo.pop()
        if rel in seen:
            continue
        seen.add(rel)
        main = next((f for f in pkg_files(root, rel) if f.suffix in (".uasset", ".umap")), None)
        if main is None:
            missing.add(rel)
            continue
        data = main.read_bytes()
        for m in PKG_RE.findall(data):
            s = m.decode("ascii", "ignore").split(".")[0].rstrip("/")
            r = s[len("/Game/"):]
            if not r or r in seen:
                continue
            if pkg_files(root, r):
                todo.append(r)
            else:
                missing.add(r)
        for m in OTHER_RE.findall(data):
            external.add(m.decode("ascii", "ignore").split(".")[0])
    return seen, missing, external


def main():
    dry = "--dry" in sys.argv
    rep = {"dry": dry, "groups": [], "copied": 0, "skipped_same": 0, "conflicts": [], "bytes": 0}
    for root, globs, why in SEEDS:
        seeds = []
        for g in globs:
            for p in sorted(root.glob(g)):
                seeds.append(str(p.relative_to(root).with_suffix("")).replace("\\", "/"))
        pk, missing, external = closure(root, seeds)
        files = [f for r in sorted(pk) for f in pkg_files(root, r)]
        size = sum(f.stat().st_size for f in files)
        g = {"source_root": str(root), "why": why, "seeds": len(seeds), "packages": len(pk), "files": len(files),
             "MB": round(size / 1e6, 1), "unresolved_game_refs": sorted(missing)[:40],
             "external_refs": sorted(external)[:60], "package_list": sorted(pk)}
        rep["groups"].append(g)
        for f in files:
            rel = f.relative_to(root)
            d = DST / rel
            if d.exists():
                if d.stat().st_size == f.stat().st_size and sha(d) == sha(f):
                    rep["skipped_same"] += 1
                else:
                    rep["conflicts"].append(str(rel))
                continue
            rep["bytes"] += f.stat().st_size
            if not dry:
                d.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, d)
            rep["copied"] += 1
    rep["MB_copied"] = round(rep["bytes"] / 1e6, 1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rep, indent=1), encoding="utf-8")
    for g in rep["groups"]:
        print(f"{g['why'][:60]:60s} seeds {g['seeds']:3d} pkgs {g['packages']:4d} files {g['files']:4d} {g['MB']:8.1f} MB"
              f" unresolved {len(g['unresolved_game_refs'])} ext {len(g['external_refs'])}")
    print("COPY_OWNED", "dry" if dry else "done", "copied", rep["copied"], "skipped_same", rep["skipped_same"],
          "conflicts", len(rep["conflicts"]), "MB", rep["MB_copied"])


main()
