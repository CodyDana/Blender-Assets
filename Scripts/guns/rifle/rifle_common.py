"""AR-01 rifle: paths and the spec (plain Python; safe inside Blender)."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]                                 # Scripts/guns/rifle -> repo root
sys.path.insert(0, str(ROOT / "Scripts" / "guns"))
sys.path.insert(0, str(ROOT / "Scripts"))

from gunlib.spec import GunSpec  # noqa: E402

WORK = ROOT / "WorkFiles" / "guns" / "rifle"
SPEC_PATH = WORK / "rifle_spec.json"
TRACE = WORK / "trace"
GATES = WORK / "gates"
SCRATCH = WORK / "scratch"
REVIEW = WORK / "review"
SHEET = ROOT / "References" / "Guns" / "Rifle" / "rifle_sheetAB.webp"
BLEND = ROOT / "Assets" / "Guns" / "AR01.blend"
BLOCKOUT_BLEND = SCRATCH / "AR01_blockout.blend"
RENDERS = ROOT / "Renders" / "Guns" / "AR01"
for p in (GATES, SCRATCH, REVIEW, RENDERS, BLEND.parent):
    p.mkdir(parents=True, exist_ok=True)

SPEC = GunSpec(SPEC_PATH)
GRIP = SPEC.grip_M                                     # frame B origin in M (mm)
