"""AR-01 stage 5 gates on the EXPORTED bytes, in a fresh Blender process (nothing from the build scene):

    blender -b --factory-startup --python Scripts/guns/rifle/rifle_rig_verify.py -- [--out json]

Shim (gunlib 0.2.0): gunlib.drivers.rig_verify with the AR-01 config (rifle_gun.CFG).
Writes WorkFiles/guns/rifle/gates/rig_export.json.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rifle_common  # noqa: E402
from rifle_gun import CFG  # noqa: E402
from gunlib.drivers import rig_verify  # noqa: E402

CFG.scratch = rifle_common.SCRATCH          # honours a redirected rifle_common.SCRATCH (parts/*_run.py)
rig_verify.main(CFG)
