"""Plain-Python half of test_parts.py's sight check (PIL is not in Blender's Python): gunlib.drivers.b4 in the
aperture mode on the demo pair's triangle dump.

    py -3 -B Scripts/guns/gunlib/tests/b4_aperture_check.py <npz> <sight_line.json> <out.json> <img.png>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from gunlib.drivers import b4 as B4  # noqa: E402

npz, sl_path, out, img = sys.argv[1:5]
sl = json.loads(Path(sl_path).read_text())


class Cfg:
    b4 = {"kind": "aperture", "socket": "Sight", "rear": ["rear_sight_leaf"], "post": "front_sight_leaf",
          "ignore": ["front_sight_base", "rail", "rear_sight_base"], "tol_mm": 0.2}

    @staticmethod
    def socket(name):
        return {"socket": "Sight", "M_mm": [sl["aperture_x"], 0.0, sl["z"]],
                "unreal_rotation_deg": {"roll": 0.0, "pitch": 0.0, "yaw": 0.0}}

    @staticmethod
    def rel(p):
        return str(p)


B4.measure(Cfg, npz, out, img)
