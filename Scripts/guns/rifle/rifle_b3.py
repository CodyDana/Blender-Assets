"""AR-01 gate B3 (motion clearance, rest + extremes + sweep) and G5 static contacts, on Assets/Guns/AR01.blend:

    blender -b Assets/Guns/AR01.blend --factory-startup --python Scripts/guns/rifle/rifle_b3.py -- [--quick]
            [--suffix _LOD1] [--collection AR01_LOD1] [--out json]

Shim (gunlib 0.2.0): gunlib.drivers.b3 with the AR-01 config (rifle_gun.CFG).
Writes WorkFiles/guns/rifle/scratch/b3_result.json (the gates stage file is assembled by rifle_gates.py).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rifle_common  # noqa: E402
from rifle_gun import CFG  # noqa: E402
from gunlib.drivers import b3  # noqa: E402

CFG.scratch = rifle_common.SCRATCH          # honours a redirected rifle_common.SCRATCH (parts/*_run.py)
b3.main(CFG)
