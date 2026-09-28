"""Plan-silhouette reference set for the six-point build (restyle_pass2/silhouette_check.py input).

The frozen forms keep their restyle-pass-1 meshes (restyle_pass2/pass1_meshes/*.npz, copied unchanged): the
silhouette check proves their outline did not move.  The six-point has no pass-1 mesh, so its reference is
the UN-GROUND plate authored by the same generator at each LOD's own counts (bevel_segments 0, exactly what
measure.unbevelled_plate_area_mm2 authors for the mass gate): the knife grind is a finish on the edge
section, so the finished mesh's plan silhouette must equal the un-ground outline's.

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
from shuriken_lib.geometry import build_star_bmesh  # noqa: E402
from shuriken_lib.pack import load_form_module  # noqa: E402

out = Path(sys.argv[sys.argv.index("--") + 1])
out.mkdir(parents=True, exist_ok=True)
pass1 = PROJ / "WorkFiles" / "shuriken" / "restyle_pass2" / "pass1_meshes"
info = {"frozen_pass1_copied": [], "six_point_unground": {}}
for f in sorted(pass1.glob("*.npz")):
    shutil.copy2(f, out / f.name)
    info["frozen_pass1_copied"].append(f.name)

form = load_form_module(PROJ / "Scripts" / "shuriken" / "build_six_point.py")
spec = form.spec
o = spec.outline()
for level, lod in enumerate(spec.lods):
    plain = replace(lod, bevel_segments=0, tip_intervals=0, pyramid_tip=False,
                    taper_intervals=max(1, lod.taper_intervals))
    bm, stats = build_star_bmesh(o, plain, plain.taper_intervals)
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
    name = f"{spec.mesh_name}_LOD{level}"
    np.savez(out / f"{name}.npz", co=co, tri=np.array(tris, dtype=np.int64))
    info["six_point_unground"][name] = {"verts": int(len(co)), "tris": len(tris), "triangles_stat": stats["triangles"]}
(out / "silhouette_ref_info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
print("SILHOUETTE_REF " + json.dumps(info))
