"""AR-01 measure stage (gates L3 features and L4 dimensions) on the built geometry, frame M (mm):

    blender -b Assets/Guns/AR01.blend --factory-startup --python Scripts/guns/rifle/rifle_measure.py -- [--out json]

Shim (gunlib 0.2.0): gunlib.drivers.measure with the AR-01 config (rifle_gun.CFG).
The rifle's feature scans are rifle_gun_measure.features (L3 tolerance: 2 sheet px = 2 / 0.8225 = 2.43 mm).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rifle_common  # noqa: E402
from rifle_gun import CFG  # noqa: E402
from gunlib.drivers import measure  # noqa: E402

CFG.scratch = rifle_common.SCRATCH          # honours a redirected rifle_common.SCRATCH (parts/*_run.py)
measure.main(CFG)
