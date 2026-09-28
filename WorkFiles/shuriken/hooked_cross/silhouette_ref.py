"""Plan-silhouette reference set for the hooked-cross build (restyle_pass2/silhouette_check.py input).

The five frozen forms keep the references the spike build used (spike/silhouette_ref/*.npz, copied unchanged: the
stars and the senban against their restyle-pass-1 meshes, the six-point against its own un-ground outline, the spike
against its square-arris bar), so the check proves none of their outlines moved.  The hooked cross has no earlier
mesh; each LOD's reference is the SAME LOD authored UN-GROUND (grind=False, chamfer=False: square edges all round,
the same columns and the same fillets): the knife grind and the small chamfers are finishes on the edge section,
so every LOD's plan silhouette must equal its un-ground outline.

HEADLESS:
    blender -b --factory-startup --python silhouette_ref.py -- <out_dir>
"""
import json
import shutil
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
sys.path.insert(0, str(PROJ / "Scripts" / "shuriken"))

import bpy  # noqa: E402,F401
from shuriken_lib.outline_plate import build_outline_bmesh  # noqa: E402
from shuriken_lib.pack import load_form_module  # noqa: E402

out = Path(sys.argv[sys.argv.index("--") + 1])
out.mkdir(parents=True, exist_ok=True)
src = PROJ / "WorkFiles" / "shuriken" / "spike" / "silhouette_ref"
info = {"frozen_copied_from": str(src), "frozen_copied": [], "hooked_cross_unground": {}}
for f in sorted(src.glob("*.npz")):
    shutil.copy2(f, out / f.name)
    info["frozen_copied"].append(f.name)

form = load_form_module(PROJ / "Scripts" / "shuriken" / "build_hooked_cross.py")
o = form.geometry.o
for level, lod in enumerate(form.spec.lods):
    bm, stats, _runs, _plan = build_outline_bmesh(o, replace(lod, grind=False, chamfer=False))
    try:
        bm.verts.ensure_lookup_table()
        co = np.array([v.co[:] for v in bm.verts], dtype=np.float64)
        tris = []
        for face in bm.faces:
            idx = [v.index for v in face.verts]
            for k in range(1, len(idx) - 1):
                tris.append((idx[0], idx[k], idx[k + 1]))
    finally:
        bm.free()
    name = f"{form.spec.mesh_name}_LOD{level}"
    np.savez(out / f"{name}.npz", co=co, tri=np.array(tris, dtype=np.int64))
    info["hooked_cross_unground"][name] = {"verts": int(len(co)), "tris": len(tris)}
(out / "silhouette_ref_info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
print("SILHOUETTE_REF " + json.dumps(info))
