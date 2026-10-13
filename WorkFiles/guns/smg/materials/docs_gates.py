"""Write WorkFiles/guns/smg/gates/docs_showcase.json (W6 docs + showcase): the README / MATERIALS_README cover what the
plan's W6 row lists (frames, sockets, straight reload path, stock states and bounds, FP pattern, collision in hand, CoM,
colour, measured Unreal notes), the showcase folder holds the studio renders + the Unreal pack frame, and the shipped
docs name no real product or maker.

    py -3 -B WorkFiles/guns/smg/materials/docs_gates.py
"""
import json
import re
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
E = ROOT / "Exports/Guns/SMG01"
SC = ROOT / "showcase/CompactSMG_SM01"
readme = (E / "README.md").read_text(encoding="utf-8")
mats = (E / "MATERIALS_README.md").read_text(encoding="utf-8")

checks = {
    "README covers frames/axes (Convert Scene, Force Front X off, Unreal rotators / cm)":
        all(k in readme for k in ("Convert Scene", "Force Front X Axis", "Unreal rotators")),
    "README covers bones (11 + root)": "11 bones" in readme and all(b in readme for b in ("`stock`", "`sight_front`")),
    "README covers sockets (21, Shoulder / SlingRear follow the fold)": "21 sockets" in readme and "follow the fold" in readme,
    "README covers clips + notifies (8 clips, table)": all(f"A_SMG01_{c}" in readme for c in (
        "Fire", "Charge", "Reload", "ReloadEmpty", "Selector", "StockFold", "StockUnfold", "SightFlip")) and "StockLocked" in readme,
    "README covers the straight reload path": "straight" in readme and "MagInsertStart" in readme and "no rock" in readme,
    "README covers stock states and bounds": "Stock states" in readme and "24.752" in readme and "bounds-envelope" in readme,
    "README covers FP/TP + ForcedLodModel + FP_Mag/TP_Mag": all(k in readme for k in ("FP_Weapon", "TP_Weapon", "FP_Mag", "TP_Mag", "ForcedLodModel = 1")),
    "README covers the shared long-gun ABP": "abp_angle_table" in readme and "Compatible Skeletons" in readme,
    "README covers collision (UCX names, no collision in hand)": "UCX_SM_SMG01_LOD0_00..07" in readme and "No Collision" in readme,
    "README covers centre of mass (extended + folded)": "47.5 / 0.7 / 83.1" in readme and "100.0 / -10.0 / 83.1" in readme,
    "README covers colour controls": "Use Original Baked Colours" in readme and "Steel Tint" in readme,
    "README covers measured Unreal notes": "Unreal import notes (UE 5.8.3, measured)" in readme and "smg01_1013b" in readme,
    "MATERIALS_README covers slots/instances": all(k in mats for k in ("MI_SMG01_Metal", "MI_SMG01_Furniture", "MI_SMG01_Mag", "_Base")),
    "MATERIALS_README covers map settings (BC7 polymer)": "BC7" in mats and "Grayscale" in mats,
    "MATERIALS_README covers recolour steps (both instances, one Colour)": "Change the polymer colour" in mats and "same **Colour** on both" in mats,
    "MATERIALS_README covers steel tint": "Steel Tint" in mats,
    "MATERIALS_README covers measured": "smg01_1013b" in mats and "p99.9 2 / 2" in mats,
}
NAMES = re.compile(r"\b(B&T|Brugger|APC9?|UMP|MP5|MP7|Heckler|Koch|HK\b|Glock|SIG\b|Sauer|Colt|Magpul|Kriss|Vector|"
                   r"Uzi|Beretta|Kalashnikov|AK-?\d|CZ\b|Scorpion|Thompson)", re.I)
hits = sorted(set(m.group(0) for t in (readme, mats) for m in NAMES.finditer(t)))
imgs = sorted(SC.glob("*.png"))
sizes = {p.name: Image.open(p).size for p in imgs}
expect = [f"CompactSMG_SM01_{v}.png" for v in ("hero", "front", "side", "back", "top", "hero_dark", "Mag_hero",
                                                 "Mag_front", "Mag_side", "Scene_UE_threequarter")]
gates = [{"name": k, "value": v, "threshold": "present", "pass": bool(v)} for k, v in checks.items()]
gates += [
    {"name": "showcase/CompactSMG_SM01 images (studio.py on the shipped FBX + maps, + 1 Unreal pack frame), looked at",
     "value": sizes, "threshold": "the 10 expected images", "pass": sorted(expect) == sorted(sizes)},
    {"name": "showcase/ASSET_LIST.md row: not edited here (orchestrator rule: another chat has edits there); row text "
             "handed to the main chat in the stage summary", "value": "row text in the W6 summary", "threshold": "report",
     "pass": True},
    {"name": "no real product or maker names in the shipped docs", "value": hits, "threshold": "none", "pass": not hits},
]
doc = {"stage": "W6 docs + showcase", "date": "2026-10-13", "report": "WorkFiles/guns/smg/SMG_REPORT.md",
       "gates": gates, "failed": [g["name"] for g in gates if not g["pass"]]}
doc["status"] = "pass" if not doc["failed"] else "fail"
(ROOT / "WorkFiles/guns/smg/gates/docs_showcase.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
print(doc["status"], doc["failed"])
