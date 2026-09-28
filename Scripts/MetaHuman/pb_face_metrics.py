"""pb_face_metrics.py -- numbers for the face candidates (needs numpy; Blender's bundled python works:
    "C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" Scripts/MetaHuman/pb_face_metrics.py <build_report.json>

* body: max per-vertex distance between each candidate's Body dump and the unmodified reference Body dump (same
  editor run) and the builder's A-pose dump (player_base/mesh_dump/mh_apose_Body.obj); bone deltas; constraints.
* face: per-vertex displacement of each candidate's Face dump vs the unmodified conformed face (same topology),
  restricted to the front of the face (vertices with y > head-centre y and z within the face band), in mm;
  landmark displacement (the 79 landmarks of MH_PlayerBase).
Writes <report>_metrics.json next to the report.
"""
import json
import sys
from pathlib import Path

import numpy as np

rp = Path(sys.argv[1])
rep = json.loads(rp.read_text(encoding="utf-8"))
b = rep["build"]
DUMPS = rp.parent / "mesh_dump"
BUILDER_BODY = Path(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/MetaHuman/player_base/mesh_dump/mh_apose_Body.obj")


def load_obj(p):
    v = []
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("v "):
                v.append([float(x) for x in line.split()[1:4]])
    return np.array(v)


out = {"units": "cm unless noted"}
ref_body = load_obj(DUMPS / "ref_Body.obj")
ref_face = load_obj(DUMPS / "ref_Face.obj")
builder_body = load_obj(BUILDER_BODY) if BUILDER_BODY.is_file() else None
out["ref_vs_builder_body_max_cm"] = (float(np.abs(ref_body - builder_body).max())
                                     if builder_body is not None and builder_body.shape == ref_body.shape else None)
ref_lm = np.array(b["reference"]["landmarks"])
ref_bones = b["reference"]["measure"]["bones"]
ref_con = b["reference"]["measure"]["constraints"]
# front-of-face mask on the unmodified face
zc = 173.6
mask = (ref_face[:, 1] > 2.0) & (ref_face[:, 2] > zc - 14.0) & (ref_face[:, 2] < zc + 8.0)
out["face_front_vertex_count"] = int(mask.sum())
for name, c in b["candidates"].items():
    tag = name.replace("MH_PlayerBase_", "")
    m = {}
    body = load_obj(DUMPS / f"{tag}_Body.obj")
    m["body_max_vertex_delta_vs_ref_cm"] = float(np.abs(body - ref_body).max()) if body.shape == ref_body.shape else "shape mismatch"
    bones = c["measure"]["bones"]
    m["bone_max_delta_cm"] = max(float(np.abs(np.array(bones[k]) - np.array(ref_bones[k])).max()) for k in ref_bones)
    con = c["measure"]["constraints"]
    m["constraint_max_delta"] = max(abs(con[k] - ref_con[k]) for k in ref_con)
    m["height"] = con.get("Height")
    face = load_obj(DUMPS / f"{tag}_Face.obj")
    if face.shape == ref_face.shape:
        dv = np.linalg.norm(face - ref_face, axis=1)
        m["face_front_disp_mm_mean"] = round(float(dv[mask].mean() * 10), 2)
        m["face_front_disp_mm_p90"] = round(float(np.percentile(dv[mask], 90) * 10), 2)
        m["face_front_disp_mm_max"] = round(float(dv[mask].max() * 10), 2)
        m["whole_face_mesh_disp_mm_mean"] = round(float(dv.mean() * 10), 2)
    lm = np.array(c["measure"]["landmarks"])
    if lm.shape == ref_lm.shape:
        dl = np.linalg.norm(lm - ref_lm, axis=1)
        m["landmark_disp_mm_mean"] = round(float(dl.mean() * 10), 2)
        m["landmark_disp_mm_max"] = round(float(dl.max() * 10), 2)
        # proportions: face width/height from landmark bbox
        m["landmark_bbox_cm"] = [round(float(x), 2) for x in (lm.max(0) - lm.min(0))]
    out[name] = m
out["ref_landmark_bbox_cm"] = [round(float(x), 2) for x in (ref_lm.max(0) - ref_lm.min(0))]
dst = rp.with_name(rp.stem + "_metrics.json")
dst.write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps(out, indent=1))
