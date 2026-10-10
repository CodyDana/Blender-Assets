"""Generic driver runner: ``--gun <config.py> --driver <name> [driver args]`` (inside Blender after ``--``, or plain
Python for b4 / viewgates)."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))            # Scripts/guns
sys.path.insert(0, str(HERE.parents[2]))            # Scripts

from gunlib import gunconf  # noqa: E402


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    gun = argv[argv.index("--gun") + 1]
    drv = argv[argv.index("--driver") + 1]
    rest = [a for i, a in enumerate(argv) if a not in ("--gun", "--driver") and
            (i == 0 or argv[i - 1] not in ("--gun", "--driver"))]
    cfg = gunconf.load(gun)
    importlib.import_module(f"gunlib.drivers.{drv}").main(cfg, rest)


main()
