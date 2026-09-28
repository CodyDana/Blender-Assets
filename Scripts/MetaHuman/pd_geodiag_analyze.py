"""pd_geodiag_analyze.py -- offline geometry diagnosis of the MetaHuman dumps (jaw line, ear patch, shoulders, neck seam).

Run with Blender's Python (numpy):
  "C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" Scripts/MetaHuman/pd_geodiag_analyze.py
Writes WorkFiles/MetaHuman/player_default/geodiag/geodiag_report.json and per-vertex arrays (npz) for the renders.
No Unreal, no .blend files.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pd_geodiag_lib import (DUMPS, OUT, apply, boundary_loops, components, dihedral, edge_table, face_normals,  # noqa: E402
                            kabsch, load_obj, self_intersections, vertex_normals)

NH = 24049            # head skin = first component of the Face mesh (MetaHuman LOD0 topology)
OUT.mkdir(parents=True, exist_ok=True)
REPORT: dict = {"script": "Scripts/MetaHuman/pd_geodiag_analyze.py", "coords": "UE world cm, Z up, faces +Y, "
                "character left = +X (bones *_l at +X). UE front camera looks -Y => image-left = -X = character RIGHT."}

M = {k: load_obj(p) for k, p in DUMPS.items()}
F_all = M["kelvin_Face"][1]
FH = F_all[np.all(F_all < NH, axis=1)]
heads = {k: M[k][0][:NH].copy() for k in ("kelvin_Face", "ref_Face", "FaceC_Face")}
# outward normals: the dump winding is clockwise in a right-handed reading (UE is left-handed) -> negate
def vnorm(V, F):
    return -vertex_normals(V, F)


def fnorm(V, F):
    n, a = face_normals(V, F)
    return -n, a


# ---------------------------------------------------------------- 0. neck seam (face vs body)
seam = {}
for fk, bk in (("kelvin_Face", "kelvin_Body"), ("ref_Face", "ref_Body"), ("FaceC_Face", "FaceC_Body")):
    Vf, Ff = M[fk]
    Vb, Fb = M[bk]
    lf, nbf, nmf = boundary_loops(Ff[np.all(Ff < NH, axis=1)])
    lb, nbb, nmb = boundary_loops(Fb)
    neck_f = max(lf, key=len)
    neck_b = max(lb, key=len)
    d = np.linalg.norm(Vf[neck_f][:, None] - Vb[neck_b][None], axis=2)
    nnd = d.min(1)
    # normal continuity across the seam: compare vertex normals of head and body at the matched seam vertices
    nf = vnorm(Vf[:NH], Ff[np.all(Ff < NH, axis=1)])[neck_f]
    nb = vnorm(Vb, Fb)[np.array(neck_b)[d.argmin(1)]]
    ang = np.degrees(np.arccos(np.clip((nf * nb).sum(1), -1, 1)))
    seam[fk] = {"head_boundary_loops": len(lf), "head_boundary_edges": nbf, "head_nonmanifold_edges": nmf,
                "body_boundary_loops": len(lb), "body_boundary_edges": nbb, "body_nonmanifold_edges": nmb,
                "seam_verts": len(neck_f), "seam_gap_cm_max": round(float(nnd.max()), 5),
                "seam_gap_cm_mean": round(float(nnd.mean()), 5),
                "seam_normal_mismatch_deg_max": round(float(ang.max()), 2),
                "seam_normal_mismatch_deg_mean": round(float(ang.mean()), 2),
                "seam_z_range": [round(float(Vf[neck_f][:, 2].min()), 2), round(float(Vf[neck_f][:, 2].max()), 2)]}
REPORT["neck_seam"] = seam

# ---------------------------------------------------------------- alignment Kelvin -> FaceC (similarity, whole head)
R, t, s = kabsch(heads["kelvin_Face"], heads["FaceC_Face"], scale=True)
heads["kelvinAl"] = apply(R, t, s, heads["kelvin_Face"])
REPORT["kelvin_to_FaceC_similarity"] = {"scale": round(float(s), 4), "t": np.round(t, 3).tolist(),
                                        "rms_cm": round(float(np.sqrt(((heads["kelvinAl"] - heads["FaceC_Face"]) ** 2)
                                                                     .sum(1).mean())), 3)}

# ---------------------------------------------------------------- regions (indices from FaceC geometry)
C = heads["FaceC_Face"]
nC = vnorm(C, FH)
ear_R = np.nonzero((C[:, 0] < -7.3) & (C[:, 2] > 166.5) & (C[:, 2] < 181.5) & (C[:, 1] > -5.5) & (C[:, 1] < 3.5))[0]
ear_L = np.nonzero((C[:, 0] > 7.3) & (C[:, 2] > 166.5) & (C[:, 2] < 181.5) & (C[:, 1] > -5.5) & (C[:, 1] < 3.5))[0]
# under-jaw: surface below the mouth whose outward normal points down; neck band just below it
under = np.nonzero((C[:, 2] > 156.0) & (C[:, 2] < 168.0) & (nC[:, 2] < -0.35) & (C[:, 1] > -3.0))[0]
jz = C[under, 2]
band = np.nonzero((C[:, 2] > 152.0) & (C[:, 2] < 168.0) & (C[:, 1] > -4.0) & (np.abs(C[:, 0]) < 9.0) &
                  (C[:, 1] < 13.0))[0]
REGIONS = {"ear_R_imageLeft": ear_R, "ear_L_imageRight": ear_L, "under_jaw": under, "jaw_neck_band": band}
np.savez(OUT / "geodiag_regions.npz", **{k: v for k, v in REGIONS.items()})


def region_faces(idx):
    m = np.zeros(NH, bool)
    m[idx] = True
    return np.nonzero(m[FH].all(1))[0]


def tri_stats(V, Vref, fsel):
    """per-triangle stretch vs reference (after similarity) + minimum angle."""
    P = V[FH[fsel]]
    Q = Vref[FH[fsel]]
    out = {}
    e = [P[:, 1] - P[:, 0], P[:, 2] - P[:, 0], P[:, 2] - P[:, 1]]
    L = np.stack([np.linalg.norm(x, axis=1) for x in e], 1)
    # angles
    def ang(a, b):
        return np.degrees(np.arccos(np.clip((a * b).sum(1) / np.maximum(np.linalg.norm(a, axis=1) *
                                                                         np.linalg.norm(b, axis=1), 1e-12), -1, 1)))
    a0 = ang(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
    a1 = ang(P[:, 0] - P[:, 1], P[:, 2] - P[:, 1])
    a2 = 180 - a0 - a1
    minang = np.minimum(np.minimum(a0, a1), a2)
    Lr = np.stack([np.linalg.norm(Q[:, 1] - Q[:, 0], axis=1), np.linalg.norm(Q[:, 2] - Q[:, 0], axis=1),
                   np.linalg.norm(Q[:, 2] - Q[:, 1], axis=1)], 1)
    ratio = L / np.maximum(Lr, 1e-9)
    aniso = ratio.max(1) / np.maximum(ratio.min(1), 1e-9)
    out["min_angle_deg_min"] = round(float(minang.min()), 2)
    out["tris_min_angle_below_5deg"] = int((minang < 5).sum())
    out["edge_len_ratio_vs_kelvin_min_max"] = [round(float(ratio.min()), 3), round(float(ratio.max()), 3)]
    out["tris_anisotropic_stretch_gt_2"] = int((aniso > 2).sum())
    out["tris_anisotropic_stretch_gt_3"] = int((aniso > 3).sum())
    return out, minang, aniso


e_all, f0_all, f1_all, _ = dihedral(C, FH)
fnK, _ = fnorm(heads["kelvinAl"], FH)
reg_out = {}
for rname, idx in REGIONS.items():
    fsel = region_faces(idx)
    rr = {"verts": int(len(idx)), "tris": int(len(fsel)),
          "bbox_FaceC": [np.round(C[idx].min(0), 2).tolist(), np.round(C[idx].max(0), 2).tolist()]}
    for k in ("kelvinAl", "ref_Face", "FaceC_Face"):
        V = heads[k]
        e, f0, f1, ang = dihedral(V, FH)
        inreg = np.isin(e[:, 0], idx) & np.isin(e[:, 1], idx)
        a = ang[inreg]
        fn, _ = fnorm(V, FH)
        cosK = (fn[fsel] * fnK[fsel]).sum(1)
        ts, _, _ = tri_stats(V, heads["kelvinAl"], fsel)
        rr[k] = {"dihedral_max": round(float(a.max()), 1), "dihedral_p99": round(float(np.percentile(a, 99)), 1),
                 "edges_gt30": int((a > 30).sum()), "edges_gt45": int((a > 45).sum()), "edges_gt60": int((a > 60).sum()),
                 "edges_gt90": int((a > 90).sum()),
                 "tri_normal_dev_vs_kelvin_gt45": int((cosK < np.cos(np.radians(45))).sum()),
                 "tri_normal_dev_vs_kelvin_gt90_flipped": int((cosK < 0).sum()),
                 "tri_normal_dev_vs_kelvin_max_deg": round(float(np.degrees(np.arccos(np.clip(cosK.min(), -1, 1)))), 1),
                 **ts}
        if k != "kelvinAl":
            hits = self_intersections(V, FH, fsel, cell=0.5)
            rr[k]["self_intersections_in_region"] = len(hits)
            if hits:
                cc = V[FH[np.array(hits)[:, 0]]].mean(1)
                rr[k]["self_intersection_sample_centroids"] = np.round(cc[:8], 2).tolist()
        else:
            hits = self_intersections(V, FH, fsel, cell=0.5)
            rr[k]["self_intersections_in_region"] = len(hits)
    reg_out[rname] = rr
REPORT["regions"] = reg_out

# ---------------------------------------------------------------- jaw crease: curvature across the jaw/neck junction
def cot_mean_curv(V, F):
    """|mean curvature| per vertex (cotan Laplacian / mixed area, simple barycentric area)."""
    nv = len(V)
    L = np.zeros((nv, 3))
    A = np.zeros(nv)
    for i, j, k in ((0, 1, 2), (1, 2, 0), (2, 0, 1)):
        vi, vj, vk = V[F[:, i]], V[F[:, j]], V[F[:, k]]
        a, b = vj - vi, vk - vi
        cr = np.linalg.norm(np.cross(a, b), axis=1)
        cot = (a * b).sum(1) / np.maximum(cr, 1e-12)   # cot of the angle at vertex i (opposite edge j-k)
        np.add.at(L, F[:, j], 0.5 * cot[:, None] * (vk - vj))
        np.add.at(L, F[:, k], 0.5 * cot[:, None] * (vj - vk))
        np.add.at(A, F[:, i], cr / 6.0)
    Hn = L / np.maximum(A, 1e-12)[:, None] / 2.0     # = -H * n_out (|.| = mean curvature, 1/cm)
    return Hn, A


curv = {}
for k in ("kelvinAl", "ref_Face", "FaceC_Face"):
    V = heads[k]
    Hn, A = cot_mean_curv(V, FH)
    n = vnorm(V, FH)
    Hs = (Hn * n).sum(1)          # signed; sign convention checked below on the skull top (convex)
    curv[k] = Hs
top = int(np.argmax(C[:, 2]))
sgn = np.sign(np.median(curv["FaceC_Face"][np.nonzero(C[:, 2] > C[:, 2].max() - 2)[0]]))
for k in curv:
    curv[k] = curv[k] * sgn   # now convex (skull top) > 0, concave crease < 0
np.savez(OUT / "geodiag_curv.npz", **curv)
jc = {}
for k, Hs in curv.items():
    b = Hs[band]
    order = np.argsort(b)[:25]
    jc[k] = {"band_min_signed_mean_curv_1_per_cm": round(float(b.min()), 3),
             "band_p1": round(float(np.percentile(b, 1)), 3),
             "band_verts_concave_below_-0.5": int((b < -0.5).sum()),
             "band_verts_concave_below_-1.0": int((b < -1.0).sum()),
             "most_concave_sample_xyz_FaceC_space": np.round(C[band[order[:6]]], 2).tolist()}
REPORT["jaw_neck_crease_curvature"] = jc

# ---------------------------------------------------------------- source-mesh crease for comparison (different topology)
Vs, Fs = M["source"]
ns = -vertex_normals(Vs, Fs)
# orientation sanity for the source: nose tip normal should point +Y
ntip = int(np.argmax(Vs[:, 1] * (Vs[:, 2] > 150)))
if ns[ntip, 1] < 0:
    ns = -ns
REPORT["source_outward_normal_flip_applied"] = bool(ns[ntip, 1] < 0)

# ---------------------------------------------------------------- body: holes / hidden faces near the straps
bodies = {}
for bk in ("kelvin_Body", "ref_Body", "FaceC_Body", "mh_apose_Body"):
    Vb, Fb = M[bk]
    loops, nbb, nmb = boundary_loops(Fb)
    uniq, cnt, _ = edge_table(Fb)
    roots = components(len(Vb), Fb)
    fn, area = face_normals(Vb, Fb)
    bodies[bk] = {"verts": int(len(Vb)), "tris": int(len(Fb)), "boundary_loops": len(loops),
                  "boundary_loop_sizes": sorted([len(L) for L in loops], reverse=True),
                  "boundary_loop_centers": [np.round(Vb[L].mean(0), 2).tolist() for L in loops],
                  "nonmanifold_edges": nmb, "components": int(len(np.unique(roots))),
                  "zero_area_tris": int((area < 1e-8).sum())}
# shoulder-top self-intersection + stretch vs Kelvin body (same topology)
Vb = M["FaceC_Body"][0]
Fb = M["FaceC_Body"][1]
Vk = M["kelvin_Body"][0]
Rb, tb, sb = kabsch(Vk, Vb, scale=True)
VkA = apply(Rb, tb, sb, Vk)
sh = np.nonzero((Vb[:, 2] > 138) & (np.abs(Vb[:, 0]) > 6) & (np.abs(Vb[:, 0]) < 24) & (Vb[:, 1] > -12))[0]
msk = np.zeros(len(Vb), bool)
msk[sh] = True
fsh = np.nonzero(msk[Fb].all(1))[0]
fnb, _ = face_normals(Vb, Fb)
fnk, _ = face_normals(VkA, Fb)
cosb = (fnb[fsh] * fnk[fsh]).sum(1)
e, f0, f1, angb = dihedral(Vb, Fb)
inreg = msk[e[:, 0]] & msk[e[:, 1]]
ek, _, _, angk = dihedral(VkA, Fb)
hits_b = self_intersections(Vb, Fb, fsh, cell=0.8)
bodies["shoulder_tops_FaceC_vs_Kelvin"] = {
    "region": "body verts z>138, 6<|x|<24", "verts": int(len(sh)), "tris": int(len(fsh)),
    "dihedral_max_FaceC": round(float(angb[inreg].max()), 1), "dihedral_max_Kelvin": round(float(angk[inreg].max()), 1),
    "edges_gt30_FaceC": int((angb[inreg] > 30).sum()), "edges_gt30_Kelvin": int((angk[inreg] > 30).sum()),
    "tri_normal_dev_vs_kelvin_gt45": int((cosb < np.cos(np.radians(45))).sum()),
    "tri_normal_dev_vs_kelvin_gt90": int((cosb < 0).sum()),
    "self_intersections": len(hits_b)}
REPORT["body"] = bodies

(OUT / "geodiag_report.json").write_text(json.dumps(REPORT, indent=1), encoding="utf-8")
print(json.dumps(REPORT, indent=1))
