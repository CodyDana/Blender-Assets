"""SMG01 B4b: the sight picture at the cheek-weld eye point (90 mm behind the aperture, plan 14.2 B4b: reported),
the B4 driver with the eye relief changed (plain Python).

    py -3 -B Scripts/guns/smg/smg_b4b.py [--npz WorkFiles/guns/smg/scratch/form_tris.npz]
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from gunlib import gunconf  # noqa: E402
from gunlib.drivers import b4  # noqa: E402

cfg = gunconf.load(HERE / "smg_gun.py")
argv = sys.argv[1:]
npz = argv[argv.index("--npz") + 1] if "--npz" in argv else str(cfg.scratch / "form_tris.npz")
cfg.b4 = dict(cfg.b4, relief=90.0, img=cfg.review / "b4" / "b4b_cheek_weld.png")
b4.main(cfg, ["--npz", npz, "--out", str(cfg.scratch / "b4b_result.json"),
              "--img", str(cfg.review / "b4" / "b4b_cheek_weld.png")])
