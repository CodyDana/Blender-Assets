"""AR-01 G5 at LOD2 and LOD3 (penetration depth in pixels at the LOD's switch-in distance):

    blender -b Assets/Guns/AR01.blend --factory-startup --python Scripts/guns/rifle/rifle_g5_lods.py -- [--out json]

Shim (gunlib 0.2.0): gunlib.drivers.g5_lods with the AR-01 config (rifle_gun.CFG).
Writes scratch/game/g5_lods.json.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rifle_common  # noqa: E402
from rifle_gun import CFG  # noqa: E402
from gunlib.drivers import g5_lods  # noqa: E402

CFG.scratch = rifle_common.SCRATCH          # honours a redirected rifle_common.SCRATCH (parts/*_run.py)
g5_lods.main(CFG)
