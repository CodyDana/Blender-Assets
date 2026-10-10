"""AR-01 stage 4 view gates (plain Python): LOD-pop and the S2 sight picture at every LOD, on the twin's
per-LOD triangles (scratch/game/lod<k>_tris.npz, frame M, mm):

    py -3 -B Scripts/guns/rifle/rifle_viewgates.py [--outdir dir] [--outr dir] [--sizes-out json]

Shim (gunlib 0.2.0): gunlib.drivers.viewgates with the AR-01 config (rifle_gun.CFG).
Writes scratch/game/viewgates.json and gates/game_lod_sizes.json.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rifle_common  # noqa: E402
from rifle_gun import CFG  # noqa: E402
from gunlib.drivers import viewgates  # noqa: E402

CFG.scratch = rifle_common.SCRATCH          # honours a redirected rifle_common.SCRATCH (parts/*_run.py)

if __name__ == "__main__":
    viewgates.main(CFG)
