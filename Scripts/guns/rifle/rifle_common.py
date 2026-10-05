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

# part pairs that touch at a butt / fixed joint besides each part's own joint parent (B3 / G5 gap checks; the LOD stage
# checks the same pairs at LOD1)
CONTACT_PAIRS = [("pistol_grip", "trigger_guard"), ("pistol_grip", "receiver"), ("trigger_guard", "receiver"),
                 ("buttstock", "rear_trunnion"), ("buttstock", "butt_plate"), ("rear_sight_block", "receiver"),
                 ("rear_sight_block", "dust_cover"), ("upper_handguard", "lower_handguard"),
                 ("gas_tube_rear_cap", "rear_sight_block"), ("muzzle_brake", "front_sight_block"),
                 ("butt_screws", "butt_plate"), ("rivets", "receiver"), ("magazine", "receiver"),
                 ("magazine", "mag_catch"), ("selector", "receiver"), ("selector", "rivets"),
                 ("bolt_carrier", "receiver_rails"), ("bolt_carrier", "dust_cover"), ("bolt_carrier", "receiver"),
                 ("trigger", "receiver"), ("trigger", "trigger_guard"), ("mag_catch", "trigger_guard"),
                 ("rear_sight_leaf", "rear_sight_block"), ("rear_sight_slider", "rear_sight_leaf"),
                 ("sling_swivel_loop", "sling_swivel_base"), ("gas_piston", "gas_tube")]
