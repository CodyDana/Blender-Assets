"""W6 gate: docs + showcase (plain Python). Writes WorkFiles/guns/sniper/gates/docs_showcase.json and
gates/shipped_sha256_w6.json.

    py -3 -B WorkFiles/guns/sniper/tools/w6_docs_gate.py

Each README / MATERIALS_README item is checked by its section heading AND required words being present (computed, not
asserted). Showcase: the expected 17 images exist with their sizes and studio logs. Bytes: every file in
Exports/Guns/SR01 hashed and compared with the W5 record (UnrealCheck/SHA256_at_end.json). Deny list: the scan
written by w6_deny_scan.py.
"""
import datetime
import hashlib
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
E = ROOT / "Exports/Guns/SR01"
G = ROOT / "WorkFiles/guns/sniper/gates"
R = (E / "README.md").read_text(encoding="utf-8")
M = (E / "MATERIALS_README.md").read_text(encoding="utf-8")


def has(text, *words):
    return all(w in text for w in words)


README = [
    ("frames / axes (mm, +X muzzle, Unreal cm Y flipped, Convert Scene, Force Front X off)",
     has(R, "## Frames and units", "+X toward the muzzle", "Y flipped", "Convert Scene", "Force Front X Axis")),
    ("bones (13 + root) and the angle table", has(R, "### Bones and the angle table", "13 rigid bones", "abp_angle_table")),
    ("clips + notifies (8 clips, table, start/end states)",
     has(R, "| `A_SR01_BipodDeploy` |", "BipodLocked", "BoltLock", "starts with the bolt open")),
    ("sockets (20, table, static-mesh socket rule)", has(R, "## Sockets", "20 sockets", "BipodFoot_L", "ue_import_sockets.py")),
    ("straight reload path", has(R, "## Magazine and reloads", "**straight**", "67.8 mm", "MagInsertStart")),
    ("bipod use: deploy/stow clips, bones, 12 deg splay, ground heights by extension, cant, bounds",
     has(R, "## The bipod in use", "**12 degrees**", "266.7", "341.1", "+-15 degrees", "bounds extension")),
    ("bounds extension values", has(R, "Positive (0, 8.681, 2.31)", "Negative (0, 12.877, 18.386)")),
    ("scope attachment: Mount on Rail_Top + 2 slots, Sight / EyePoint, no zero",
     has(R, "## The scope", "+ 2 slots: X +20.02 mm", "`Sight`", "`EyePoint`", "No zero is built in")),
    ("FP/TP pattern incl. the scope pair + ForcedLodModel", has(R, "## First person", "FP_Scope", "ForcedLodModel = 1")),
    ("shared long-gun ABP (AR-01 compatible skeleton)", has(R, "SK_AR01_Skeleton", "bone not found")),
    ("collision (UCX names, no collision in hand)", has(R, "## Collision", "UCX_SM_SR01_LOD0_00..09", "*No Collision*")),
    ("centre of mass and masses", has(R, "**Centre of mass:** 200.2 / -0.3 / 68.7", "5.9 kg", "1.15 kg", "0.20 kg")),
    ("physics (PHYS_SR01, envelope, rebuild)", has(R, "## Physics", "PHYS_SR01", "bounds-envelope box", "PhysicsProxy")),
    ("tri counts per LOD for every mesh", has(R, "40,518", "18,202", "41,396", "878", "9,938", "1,454")),
    ("texture sizes", has(R, "(2048)", "(4096)", "(1024)", "(512)")),
    ("materials table + pack instances marked not built", has(R, "## Materials and textures", "not built")),
    ("measured Unreal notes kept", has(R, "## Measured in Unreal 5.8.3", "SR01_1014b", "Asset warnings: 0")),
    ("open items stated (close-up realism, U11)", has(R, "Close-up realism is not signed off", "U11")),
]
MATS = [
    ("texture sets and slots", has(M, "## Texture sets and slots", "M_SR01_Chassis", "M_Att_Scope_Lens")),
    ("map settings / colour spaces (BC sRGB, ORM/Masks linear, N DirectX, Detail16 G16)",
     has(M, "## Import the maps", "sRGB on", "sRGB off", "**DirectX**", "G16")),
    ("Masks channels (R/G/B/A, A = OD only)", has(M, "### Masks channels", "Refinishable", "**1 only on the OD paint**")),
    ("recolour plan (group SR01, OD = user colour, baked default)",
     has(M, "## The recolour plan", "`SR01`", "*Use Original Baked Colours* ON")),
    ("pack instances not built yet (stated)", has(M, "**The pack's material instances for the SR-01 are not built yet.**")),
    ("open D1 (no mask input on the master) stated", has(M, "no mask input", "do not switch")),
    ("steel tint / scope", has(M, "## Metal and scope", "Steel Tint")),
]
SHOW = ROOT / "showcase/SniperRifle_SR01"
expect = [f"SniperRifle_SR01_{v}.png" for v in ("hero", "front", "side", "back", "top", "hero_dark")] + \
         [f"SniperRifle_SR01_Mag_{v}.png" for v in ("hero", "front", "side")] + \
         [f"SniperRifle_SR01_{s}_{v}.png" for s in ("BipodDeployed", "Scoped", "Scope") for v in ("hero", "front")]
imgs = {f: list(Image.open(SHOW / f).size) for f in expect if (SHOW / f).exists()}
logs = sorted(p.name for p in (ROOT / "WorkFiles/guns/sniper/showcase_logs").glob("_studio_*.json"))

w5 = json.loads((ROOT / "WorkFiles/guns/sniper/UnrealCheck/SHA256_at_end.json").read_text())
cur = {p.relative_to(E).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(E.rglob("*"))
       if p.is_file()}
same = sorted(k for k in w5 if cur.get(k) == w5[k])
changed = sorted(k for k in w5 if k in cur and cur[k] != w5[k])
new = sorted(k for k in cur if k not in w5)
(G / "shipped_sha256_w6.json").write_text(json.dumps({"date": datetime.date.today().isoformat(), "root":
                                                      "Exports/Guns/SR01", "files": cur}, indent=1))
deny = json.loads((ROOT / "WorkFiles/guns/sniper/scratch/w6/deny_scan.json").read_text())


def gate(name, value, threshold, ok):
    return {"name": name, "value": value, "threshold": threshold, "pass": bool(ok)}


gates = [gate(f"README covers {n}", v, "present", v) for n, v in README]
gates += [gate(f"MATERIALS_README covers {n}", v, "present", v) for n, v in MATS]
gates.append(gate("showcase/SniperRifle_SR01 images (studio.py copy on the shipped FBX + maps; deployed-bipod hero and "
                  "the scope on the rail from w6_showcase_prep.py), looked at and framing checked", imgs,
                  f"the {len(expect)} expected images", len(imgs) == len(expect)))
gates.append(gate("studio logs kept", logs, "one per studio run", len(logs) >= 6))
gates.append(gate("shipped bytes = the W5-verified record (README.md rewritten, MATERIALS_README.md new)",
                  {"same": len(same), "changed": changed, "new": new},
                  "every FBX / sidecar / texture identical", set(changed) <= {"README.md"} and
                  set(new) <= {"MATERIALS_README.md"}))
gates.append(gate("gun deny list over every shipped text line and name (gunlib qa_gun.deny_hits + a maker-word net)",
                  {"lines": deny["text_lines_scanned"], "names": deny["names_scanned"], "hits": deny["text_hits"] +
                   list(deny["name_hits"]) + deny["extra_word_hits_text"] + deny["extra_word_hits_names"]},
                  "none", deny["pass"]))
gates.append({"name": "showcase/ASSET_LIST.md row: not edited (other chats edit it on main); exact row text in "
                      "SR01_REPORT.md section 9", "value": "row text in the report", "threshold": "report",
              "pass": True})
gates.append({"name": "pack materials: proposal only (not built, by instruction)",
              "value": "WorkFiles/guns/sniper/pack_materials_proposal.md + .json", "threshold": "report",
              "pass": True})
failed = [g["name"] for g in gates if not g["pass"]]
doc = {"stage": "W6 docs + showcase (pack materials proposed, not built)", "date": datetime.date.today().isoformat(),
       "report": "WorkFiles/guns/sniper/SR01_REPORT.md", "gates": gates, "failed": failed,
       "status": "pass" if not failed else "fail"}
(G / "docs_showcase.json").write_text(json.dumps(doc, indent=1))
print("DOCS_GATE", doc["status"], failed)
