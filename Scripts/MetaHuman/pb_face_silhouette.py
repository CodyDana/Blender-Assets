"""pb_face_silhouette.py -- run the builder's silhouette measurements (pb_silhouette_measure.py, same 0.2 cm/px
orthographic base-colour renders) on the face-candidate captures: ref_ (unmodified conform) and FaceA/B/C.

    py -3 Scripts/MetaHuman/pb_face_silhouette.py
Writes WorkFiles/MetaHuman/player_base/faces/face_silhouette_measure.json.
"""
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
src = (HERE / "pb_silhouette_measure.py").read_text(encoding="utf-8")
ns = {"__name__": "pb_silhouette_measure_lib"}
exec(compile(src.split("res = {\"cm_per_px\"")[0], "pb_silhouette_measure.py", "exec"), ns)  # functions only

CAP = Path(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/MetaHuman/player_base/faces/captures")
out = {"cm_per_px": ns["S"], "source": "builder's pb_silhouette_measure.py functions, faces/captures/*_Ortho_*.png"}
for prefix in ("ref", "FaceA", "FaceB", "FaceC"):
    for view in ("Front", "Side"):
        p = CAP / f"{prefix}_Ortho_{view}.png"
        if p.is_file():
            m = ns["load_mask"](str(p))
            out.setdefault(prefix, {})[view.lower()] = ns["front_measures"](m) if view == "Front" else ns["side_measures"](m)
dst = CAP.parent / "face_silhouette_measure.json"
dst.write_text(json.dumps(out, indent=1), encoding="utf-8")
keys_f = ["height", "crotch_height", "hip_breadth", "waist_breadth", "neck_breadth", "head_breadth_incl_ears",
          "shoulder_breadth_above_armpit", "chest_breadth_at_armpit"]
keys_s = ["head_height_top_to_chin", "head_depth_incl_nose", "nose_tip_y", "menton_z"]
print("measure".ljust(30) + "".join(p.ljust(10) for p in ("ref", "FaceA", "FaceB", "FaceC")))
for k in keys_f:
    print(k.ljust(30) + "".join(str(out.get(p, {}).get("front", {}).get(k)).ljust(10) for p in ("ref", "FaceA", "FaceB", "FaceC")))
for k in keys_s:
    print(k.ljust(30) + "".join(str(out.get(p, {}).get("side", {}).get(k)).ljust(10) for p in ("ref", "FaceA", "FaceB", "FaceC")))
