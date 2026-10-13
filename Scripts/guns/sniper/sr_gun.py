"""SR01 config for the gun-agnostic gunlib drivers (gunlib.gunconf), W3: paths under scratch/w3, the spec's sockets in
gunlib's record shape (sr_common.gun_socket_rows), the rig-verify and magazine-fit hooks. Used by sr_rig_verify.py (a
sniper-side port of gunlib.drivers.rig_verify: the gun has no Sight socket, B4 / S2 read the scope's A4) and
sr_magfit.py."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from sr_common import CODE, SPEC_PATH, WORK, GRIP, gun_socket_rows  # noqa: E402

import numpy as np  # noqa: E402

from gunlib.gunconf import GunConfig  # noqa: E402

CFG = GunConfig(CODE, WORK, SPEC_PATH, log_tag=CODE)
CFG.scratch = WORK / "scratch" / "w3"
_ROWS = gun_socket_rows()
CFG.gun_sockets = lambda: _ROWS
CFG.socket = lambda name: {r["socket"]: r for r in _ROWS}[name]


def _clips(rep):
    import sr_clips as CL
    clips = CL.all_clips()
    by_id = {id(fr): name for name, (fr, _n, _f) in clips.items()}

    def rest_rule(frames):
        return CL.rest_as_declared(frames, by_id.get(id(frames)))
    return clips, CL.basis_from, rest_rule


CFG.rig_verify = {
    "stage": "W3 rig + export (SK_SR01 set, SM_SR01)", "noun": "rifle", "clips": _clips, "clip_table_name": "sr_clips",
    "bore_z_B": 0.0 - float(GRIP[2]), "ucx_count": 10,
    "b3_coverage_text": "bolt rotate -60..0 then slide 0..88, trigger 0..6, safety -12..0, release -4.5..0, riser "
                        "-12.9..12, cant -15..15, legs 0..90, ext 0..76: the ranges B3 / F1-F9 swept with 0 "
                        "intersections (gates/form.json, LOD0)",
    "bounds_note": "LOD0-3 posed vs LOD0's bind box at every frame of every clip and at the extreme poses (bipod "
                   "deployed / ext 76 / cant +-15, bolt open / back, riser range); U5 re-checks in engine",
    "qa_budget_text": "pass (budget 55,000 = 50,000 gun + 5,000 merged mag; UV1 present; UCX keyed to the node; texel = "
                      "measured aggregate +-25 %)",
    "game_gates": WORK / "scratch" / "w3" / "rig" / "s2_substitute.json"}

CFG.mag_fit = {"noun": "rifle", "stage": "W3 magazine (SM_SR01_Mag build + fit on the shipped bytes)",
               "well_box_M": {"X": (413.8, 503.6), "Y": (-13.55, 13.55), "Z": (-75.0, -19.7)}}
