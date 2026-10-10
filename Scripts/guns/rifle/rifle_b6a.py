"""AR-01 gate B6a: the parts joined as the static twin would be, qa_check topology + degenerate checks; plus the
tokenised gun deny list on every object name.

    blender -b Assets/Guns/AR01.blend --factory-startup --python Scripts/guns/rifle/rifle_b6a.py -- [--out json]

Shim (gunlib 0.2.0): gunlib.drivers.b6a with the AR-01 config (rifle_gun.CFG).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rifle_common  # noqa: E402
from rifle_gun import CFG  # noqa: E402
from gunlib.drivers import b6a  # noqa: E402

CFG.scratch = rifle_common.SCRATCH          # honours a redirected rifle_common.SCRATCH (parts/*_run.py)
b6a.main(CFG)
