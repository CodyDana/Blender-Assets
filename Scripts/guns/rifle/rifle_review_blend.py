"""AR-01 review blend (headless Blender): the built rifle plus every detail module's review-only objects (the bake
sources whose detail reaches the game as a normal map, e.g. the grip's modelled checker field), so ROUGH LOOK review
renders show what the textured asset will show. Nothing here is exported; Assets/Guns/AR01.blend is not modified.

    blender -b Assets/Guns/AR01.blend --factory-startup --python Scripts/guns/rifle/rifle_review_blend.py -- --out <blend>
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rifle_common import GRIP, SCRATCH  # noqa: E402

import bpy  # noqa: E402

from gunlib import bl  # noqa: E402
import parts as PM  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else SCRATCH / "AR01_review.blend"
coll = bl.collection("AR01_ReviewBakeSource")
n = 0
for m in PM.MODULES:
    mod = PM.load(m)
    for name, fn in getattr(mod, "REVIEW_EXTRAS", ()):
        if bpy.data.objects.get(name):
            bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
        ob = fn(coll, GRIP, name)
        n += 1
        print("[review_blend] added", name, len(ob.data.polygons), "faces")
bpy.ops.wm.save_as_mainfile(filepath=str(out.resolve()), copy=True)
print("[review_blend] DONE", n, out)
