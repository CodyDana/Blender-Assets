"""AR-01 gate B4 'sight picture' (form realism round, plain Python: numpy + PIL), on scratch/form_tris.npz (frame M):

    py -3 -B Scripts/guns/rifle/rifle_b4.py [--npz scratch/form_tris.npz] [--out scratch/b4_result.json] [--img png]

Shim (gunlib 0.2.0): gunlib.drivers.b4 with the AR-01 config (rifle_gun.CFG).
zbuffer is re-exported for rifle_g5_visible.py.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rifle_common  # noqa: E402
from rifle_gun import CFG  # noqa: E402
from gunlib.drivers import b4  # noqa: E402
from gunlib.drivers.b4 import zbuffer  # noqa: E402,F401  (rifle_g5_visible uses rifle_b4.zbuffer)

CFG.scratch = rifle_common.SCRATCH          # honours a redirected rifle_common.SCRATCH (parts/*_run.py)

if __name__ == "__main__":
    b4.main(CFG)
