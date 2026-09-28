"""pd_r2_compare.py -- offline geometry proof for the round-2 MH_PlayerDefault (numpy; no Unreal). Copy of
pd_pd_compare.py (round 1) reading the round-2 dumps (mesh_dump/R2_*.obj) and pd_r2_verify_<attempt>.json, plus the
exact head-skin deltas of the jaw-ramus fix vs FaceC and vs the round-1 MH_PlayerDefault.

Run with Blender's bundled Python:
  "C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" Scripts/MetaHuman/pd_r2_compare.py [attempt]

Inputs (GeometryScript CPU dumps, UE world cm, Z up, faces +Y), all from the pd_player_default.py verify session
(fresh editor, one MetaHuman actor at a time):
  mesh_dump/PD_Body.obj, PD_Face.obj            saved MH_PlayerDefault
  mesh_dump/FaceC_Body.obj, FaceC_Face.obj      scratch duplicate of MH_PlayerBase_FaceC (never saved)
  mesh_dump/PlayerBase_Body.obj                 scratch duplicate of MH_PlayerBase (never saved)
plus the earlier build-session dumps of MH_PlayerBase / FaceC (player_base/faces/mesh_dump/ref_Body.obj, FaceC_*.obj)
and the verify report pd_verify_<attempt>.json (bones, constraints, state comparisons).
Writes WorkFiles/MetaHuman/player_default/body_compare.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pd_geodiag_lib import boundary_loops, load_obj, vertex_normals  # noqa: E402

ROOT = Path(r"C:/Users/Cody/Desktop/Blender_Projects")
OUT = ROOT / "WorkFiles/MetaHuman/player_default"
MD = OUT / "mesh_dump"
OLD = ROOT / "WorkFiles/MetaHuman/player_base/faces/mesh_dump"
ATTEMPT = sys.argv[1] if len(sys.argv) > 1 else "1"
NH = 24049   # head skin = first component of the Face mesh (MetaHuman LOD0 topology)


def cmp_mesh(a, b):
    Va, Fa = a
    Vb, Fb = b
    res = {"verts": [len(Va), len(Vb)], "tris": [len(Fa), len(Fb)]}
    if len(Va) != len(Vb):
        res["note"] = "vertex count differs"
        return res
    res["same_triangles"] = bool(len(Fa) == len(Fb) and np.array_equal(Fa, Fb))
    d = np.linalg.norm(Va - Vb, axis=1)
    res["vertex_dist_cm_max"] = float(d.max())
    res["vertex_dist_cm_mean"] = float(d.mean())
    res["verts_moved_gt_0.001cm"] = int((d > 1e-3).sum())
    return res


def seam(face, body):
    Vf, Ff = face
    Vb, Fb = body
    fh = Ff[np.all(Ff < NH, axis=1)]
    lf, nbf, nmf = boundary_loops(fh)
    lb, nbb, nmb = boundary_loops(Fb)
    neck_f = max(lf, key=len)
    neck_b = max(lb, key=len)
    d = np.linalg.norm(Vf[neck_f][:, None] - Vb[neck_b][None], axis=2)
    nnd = d.min(1)
    nf = -vertex_normals(Vf[:NH], fh)[neck_f]
    nb = -vertex_normals(Vb, Fb)[np.array(neck_b)[d.argmin(1)]]
    ang = np.degrees(np.arccos(np.clip((nf * nb).sum(1), -1, 1)))
    return {"head_boundary_loops": len(lf), "body_boundary_loops": len(lb), "body_boundary_edges": nbb,
            "body_nonmanifold_edges": nmb, "seam_verts": len(neck_f), "seam_gap_cm_max": float(nnd.max()),
            "seam_gap_cm_mean": float(nnd.mean()), "seam_normal_mismatch_deg_max": float(ang.max()),
            "seam_gap_ok_lt_0.01cm": bool(nnd.max() < 0.01)}


def main():
    M = {k: load_obj(p) for k, p in {
        "PD_Body": MD / "R2_PD_Body.obj", "PD_Face": MD / "R2_PD_Face.obj",
        "FaceC_Body": MD / "R2_FaceC_Body.obj", "FaceC_Face": MD / "R2_FaceC_Face.obj",
        "PB_Body": MD / "R2_PlayerBase_Body.obj",
        "r1_PD_Face": MD / "PD_Face.obj", "r1_PD_Body": MD / "PD_Body.obj",
        "old_ref_Body": OLD / "ref_Body.obj", "old_FaceC_Body": OLD / "FaceC_Body.obj",
        "old_FaceC_Face": OLD / "FaceC_Face.obj"}.items()}
    rep = {"script": "Scripts/MetaHuman/pd_r2_compare.py", "units": "cm, UE world, A-pose preview actor at origin"}
    rep["body_PD_vs_PlayerBase_same_session"] = cmp_mesh(M["PD_Body"], M["PB_Body"])
    rep["body_PD_vs_FaceC_same_session"] = cmp_mesh(M["PD_Body"], M["FaceC_Body"])
    rep["body_PD_vs_PlayerBase_faces_build_session"] = cmp_mesh(M["PD_Body"], M["old_ref_Body"])
    rep["body_PD_vs_FaceC_faces_build_session"] = cmp_mesh(M["PD_Body"], M["old_FaceC_Body"])
    hs = lambda k: (M[k][0][:NH], M[k][1][np.all(M[k][1] < NH, axis=1)])  # noqa: E731
    rep["head_skin_PD_vs_FaceC_same_session"] = cmp_mesh(hs("PD_Face"), hs("FaceC_Face"))
    rep["head_skin_PD_vs_FaceC_faces_build_session"] = cmp_mesh(hs("PD_Face"), hs("old_FaceC_Face"))
    rep["face_mesh_all_sections_PD_vs_FaceC"] = {"verts": [len(M["PD_Face"][0]), len(M["FaceC_Face"][0])],
                                                 "tris": [len(M["PD_Face"][1]), len(M["FaceC_Face"][1])]}
    if len(M["PD_Face"][0]) == len(M["FaceC_Face"][0]):
        d = np.linalg.norm(M["PD_Face"][0] - M["FaceC_Face"][0], axis=1)
        moved = np.nonzero(d > 1e-3)[0]
        rep["face_mesh_all_sections_PD_vs_FaceC"].update(
            {"vertex_dist_cm_max": float(d.max()), "verts_moved_gt_0.001cm": int(len(moved)),
             "moved_index_range": [int(moved.min()), int(moved.max())] if len(moved) else None,
             "moved_bbox_min": M["PD_Face"][0][moved].min(0).round(2).tolist() if len(moved) else None,
             "moved_bbox_max": M["PD_Face"][0][moved].max(0).round(2).tolist() if len(moved) else None})
    # exact head-skin deltas of the jaw-ramus fix (round-2 PD vs FaceC, same session)
    Vp, Vf = M["PD_Face"][0][:NH], M["FaceC_Face"][0][:NH]
    d = np.linalg.norm(Vp - Vf, axis=1)
    ax = np.abs(Vf[:, 0])
    jaw_box = (ax > 2.0) & (Vf[:, 2] > 155.0) & (Vf[:, 2] < 171.0) & (Vf[:, 1] > -5.0) & (Vf[:, 1] < 10.0)
    rep["jaw_fix_head_skin_delta_vs_FaceC"] = {
        "max_cm": float(d.max()), "max_at_FaceC_xyz": Vf[int(d.argmax())].round(2).tolist(),
        "mean_cm": float(d.mean()), "verts_moved_gt_0.5mm": int((d > 0.05).sum()), "verts_moved_gt_1mm": int((d > 0.1).sum()),
        "verts_moved_gt_2mm": int((d > 0.2).sum()),
        "max_outside_lower_jaw_box_cm": float(d[~jaw_box].max()),
        "lower_jaw_box": "|x|>2, 155<z<171, -5<y<10 (UE cm)",
        "p99_cm": float(np.percentile(d, 99)),
        "lateral_x_change_at_max_cm": float((np.abs(Vp[:, 0]) - np.abs(Vf[:, 0]))[int(d.argmax())])}
    rep["head_skin_PD_r2_vs_PD_r1"] = cmp_mesh(hs("PD_Face"), hs("r1_PD_Face"))
    rep["body_PD_r2_vs_PD_r1"] = cmp_mesh(M["PD_Body"], M["r1_PD_Body"])
    rep["neck_seam_PD"] = seam(M["PD_Face"], M["PD_Body"])
    rep["neck_seam_FaceC_same_session"] = seam(M["FaceC_Face"], M["FaceC_Body"])

    vr = json.loads((OUT / f"pd_r2_verify_{ATTEMPT}.json").read_text(encoding="utf-8"))["verify"]
    b_pd, b_pb, b_fc = vr["bones"], vr["playerbase_bones"], vr["facec_bones"]
    common = sorted(set(b_pd) & set(b_pb))
    dd = {k: float(np.abs(np.array(b_pd[k]) - np.array(b_pb[k])).max()) for k in common}
    rep["bones_PD_vs_PlayerBase"] = {"n_pd": len(b_pd), "n_pb": len(b_pb), "n_common": len(common),
                                     "max_abs_cm": max(dd.values()) if dd else None,
                                     "worst": sorted(dd.items(), key=lambda kv: -kv[1])[:3]}
    common2 = sorted(set(b_pd) & set(b_fc))
    rep["bones_PD_vs_FaceC"] = {"n_common": len(common2),
                                "max_abs_cm": max(float(np.abs(np.array(b_pd[k]) - np.array(b_fc[k])).max())
                                                  for k in common2) if common2 else None}
    c_pd = {k: v["value"] for k, v in vr["constraints"].items()}
    c_pb = {k: v["value"] for k, v in vr["playerbase_constraints"].items()}
    rep["constraints_PD_vs_PlayerBase"] = {"n": len(c_pd), "same_keys": sorted(c_pd) == sorted(c_pb),
                                           "max_abs": max(abs(c_pd[k] - c_pb[k]) for k in c_pd),
                                           "active_flags_equal": all(vr["constraints"][k]["active"] ==
                                                                     vr["playerbase_constraints"][k]["active"] for k in c_pd)}
    rep["compare_body_state_PD_vs_PlayerBase"] = vr.get("compare_body_state_pd_vs_playerbase")
    rep["compare_body_state_PD_vs_FaceC"] = vr.get("compare_body_state_pd_vs_facec")
    rep["compare_face_state_PD_vs_FaceC"] = vr.get("compare_face_state_pd_vs_facec")
    rep["face_coeffs_maxdiff_vs_r2_build"] = vr.get("coeffs_maxdiff_vs_build_final")
    rep["face_coeffs_maxdiff_vs_facec"] = vr.get("coeffs_maxdiff_vs_facec")
    rep["face_regions_changed_vs_facec"] = vr.get("regions_changed_vs_facec")
    rep["landmark_deltas_vs_facec"] = vr.get("landmark_deltas_vs_facec")
    rep["constraints_vs_playerbase_maxdiff"] = vr.get("constraints_vs_playerbase_maxdiff")
    (OUT / "body_compare_r2.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
