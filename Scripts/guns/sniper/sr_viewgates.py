"""SR01 W3 LOD-pop (plain Python; gunlib.drivers.viewgates.lod_pop on the twin's per-LOD triangle dumps):

    py -3 -B Scripts/guns/sniper/sr_viewgates.py

Both bipod poses (folded = the twin / bind pose, deployed = legs 90, ext 0) must pass every switch (mean contour
difference <= 1 px, max <= 3 px at 2560 x 1440, 90 deg, 4 headings); a failing switch moves farther (s x 0.9). The
distances are taken at the twin's engine sphere radius (game_report); sr_rig.py converts them to the SK's engine radius
(bind box + bounds extension). No S2: the gun has no iron sights (B4 is replaced by the scope's A4, gates/scope_form.json).
Writes gates/game_lod_sizes.json and scratch/w3/game/viewgates.json; strips in review/w3/game/.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from sr_common import WORK, GATES, CODE, D  # noqa: E402

from gunlib.drivers import viewgates as VG  # noqa: E402

OUT = WORK / "scratch" / "w3" / "game"


class _Cfg:
    viewgates = {"lod_npz": lambda k, st: OUT / f"lod{k}_{st}_tris.npz"}


def main():
    rep = json.loads((OUT / "game_report.json").read_text())
    r = float(rep["bounds_radius_m"]["twin_engine_sphere_radius"])
    sizes = [float(v) for v in D["lods"]["gun_screen_sizes_start"]]
    res = VG.lod_pop(_Cfg(), sizes, r, WORK / "review" / "w3" / "game", states=("folded", "deployed"))
    (OUT / "viewgates.json").write_text(json.dumps({"lod_pop": res}, indent=1))
    (GATES / "game_lod_sizes.json").write_text(json.dumps({f"SM_{CODE}": res["final_sizes"], "bounds_radius_m": r,
                                                           "states": ["folded", "deployed"]}, indent=1))
    print("[viewgates] DONE sizes", res["final_sizes"], "pass", all(s["pass"] for s in res["switches"]))


main()
