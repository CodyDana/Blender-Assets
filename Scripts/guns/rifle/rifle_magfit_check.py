"""AR-01 magazine fit at the FORM stage (R51 loop-back): the stage-6 M-gates' geometry on the built LOD0 parts:

    blender -b <AR01.blend | scratch/AR01_form_partial.blend> --factory-startup --python Scripts/guns/rifle/rifle_magfit_check.py -- [--out json]

Shim (gunlib 0.2.0): gunlib.drivers.magfit_check with the AR-01 config (rifle_gun.CFG).
The rock-path gates (F1-F8) are rifle_gun_magfit.form_gates. Writes WorkFiles/guns/rifle/gates/form_magfit.json (default).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rifle_common  # noqa: E402
from rifle_gun import CFG  # noqa: E402
from gunlib.drivers import magfit_check  # noqa: E402

CFG.scratch = rifle_common.SCRATCH          # honours a redirected rifle_common.SCRATCH (parts/*_run.py)
magfit_check.main(CFG)
