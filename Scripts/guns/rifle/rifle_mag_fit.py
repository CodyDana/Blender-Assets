"""AR-01 stage 6 fit verification (M1-M8) on the SHIPPED bytes of both meshes, in a fresh Blender process:

    blender -b --factory-startup --python Scripts/guns/rifle/rifle_mag_fit.py -- [--out json] [--geom npz]

Shim (gunlib 0.2.0): gunlib.drivers.mag_fit with the AR-01 config (rifle_gun.CFG).
The rock-path gates are rifle_gun_magfit.stage6_gates. Writes WorkFiles/guns/rifle/gates/mag.json and
scratch/mag/fit_geom.npz (rifle_mag_sheets.py draws from it).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rifle_common  # noqa: E402
from rifle_gun import CFG  # noqa: E402
from gunlib.drivers import mag_fit  # noqa: E402

CFG.scratch = rifle_common.SCRATCH          # honours a redirected rifle_common.SCRATCH (parts/*_run.py)
mag_fit.main(CFG)
