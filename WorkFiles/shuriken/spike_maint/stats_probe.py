"""Run shuriken_lib.render.image_stats (bar=True) on existing renders + masks and print the 3.8.1 figures.

    blender -b --factory-startup --python stats_probe.py -- <renders_dir> <diag_dir> <form> [<form> ...]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\Cody\Desktop\Blender_Projects\Scripts\shuriken")
from shuriken_lib.render import image_stats  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
renders, diag, forms = Path(argv[0]), Path(argv[1]), argv[2:]
out = {}
for form in forms:
    for shot in ("persp", "top"):
        st = image_stats(renders / f"{form}_{shot}.png", diag / f"{form}_{shot}_mask.png", 4, bar=True)
        keep = {k: st.get(k) for k in ("object_luminance", "coat_luminance", "bar_wall_luminance", "bar_wall_dots",
                                       "coat_dots", "backdrop_points", "wall_luminance")}
        out[f"{form}_{shot}"] = keep
print("STATS_PROBE " + json.dumps(out))
