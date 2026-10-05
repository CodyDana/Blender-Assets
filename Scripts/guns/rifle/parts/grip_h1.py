"""Run the official H1 early gate (rifle_h1.py, unchanged) against the grip review blend instead of the shared asset
blend, writing its result to scratch/detail_grip/h1_result.json (headless Blender, the fit body as the main file):

    blender -b References/Characters/MH_PlayerDefault/MH_PlayerDefault_FitBody.blend --factory-startup
        --python Scripts/guns/rifle/parts/grip_h1.py
"""
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import rifle_common as RC  # noqa: E402

RC.BLEND = RC.SCRATCH / "detail_grip" / "AR01_grip.blend"
RC.SCRATCH = RC.SCRATCH / "detail_grip"
runpy.run_path(str(HERE.parent / "rifle_h1.py"), run_name="__main__")
