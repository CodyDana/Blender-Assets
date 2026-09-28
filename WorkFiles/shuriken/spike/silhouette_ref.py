"""Plan-silhouette reference set for the spike build (restyle_pass2/silhouette_check.py input).

The frozen forms keep the references the six-point build used (six_point/silhouette_ref/*.npz, copied
unchanged: the stars and the senban against their restyle-pass-1 meshes, the six-point against its own
un-ground outline), so the check proves none of their outlines moved.  The spike has no earlier mesh; its
reference is the SAME bar authored with square arrises (arris_segments 0, the tip flat kept) at every
LOD's name: the arris round is a finish on the section, so every LOD's plan silhouette must equal it.
(The sharp un-ground outline differs from it only by the tip flat: 0.075 mm either side of the axis at
the point, which build_spike's mass check accounts for.)

HEADLESS:
    blender -b --factory-startup --python silhouette_ref.py -- <out_dir>
"""
import json
import shutil
import sys
from pathlib import Path

import numpy as np

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
sys.path.insert(0, str(PROJ / "Scripts" / "shuriken"))

import bpy  # noqa: E402,F401
from shuriken_lib.bar import build_bar_bmesh  # noqa: E402
from shuriken_lib.bar_spec import BarLodSpec  # noqa: E402
from shuriken_lib.pack import load_form_module  # noqa: E402

out = Path(sys.argv[sys.argv.index("--") + 1])
out.mkdir(parents=True, exist_ok=True)
src = PROJ / "WorkFiles" / "shuriken" / "six_point" / "silhouette_ref"
info = {"frozen_copied_from": str(src), "frozen_copied": [], "spike_square_arris": {}}
for f in sorted(src.glob("*.npz")):
    shutil.copy2(f, out / f.name)
    info["frozen_copied"].append(f.name)

form = load_form_module(PROJ / "Scripts" / "shuriken" / "build_spike.py")
o = form.geometry.o
bm, stats = build_bar_bmesh(o, BarLodSpec(arris_segments=0))
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
for level in range(len(form.spec.lods)):
    name = f"{form.spec.mesh_name}_LOD{level}"
    np.savez(out / f"{name}.npz", co=co, tri=np.array(tris, dtype=np.int64))
    info["spike_square_arris"][name] = {"verts": int(len(co)), "tris": len(tris)}
(out / "silhouette_ref_info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
print("SILHOUETTE_REF " + json.dumps(info))
