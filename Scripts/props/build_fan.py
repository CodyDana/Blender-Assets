#!/usr/bin/env python
"""Build SK_Fan (the folding fan, sensu) from scratch: fold mechanism, sticks, pleated leaf, rivet, the
separate tassel, skeleton and skin, animations, LODs, tint-ready maps, physics and socket data, skeletal FBX
export with its sidecar, QA, the fold proof and the renders.

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python Scripts/props/build_fan.py -- [--quick] [--dev-dir DIR] [--no-render]

``--quick`` / ``--no-render`` only with ``--dev-dir``.  The shipped build is the one without flags.

HOW IT IS MADE (the way a folding fan is made)
    props_lib.fan_spec      REFERENCE_SPEC / FAN_STUDY numbers, each with its status
    props_lib.fan_fold      the mechanism: sticks turn about the rivet; 50 rigid leaf faces hinged on the
                            sticks' leaf lines and on each other; the fold solved per openness; the instruments
    props_lib.fan_geom      26 stacked sticks, the leaf (front + back layer per face), the glued flaps, the eyelet
    props_lib.fan_tassel    SK_Fan_Tassel: cord, bead knot, neck binding, round skirt; a 6-bone chain
    props_lib.fan_paint     maps painted from each part's own coordinates; the pack's tint-ready finish
    props_lib.fan_look      armature, skin, materials from the baked maps, AO bake, actions
    props_lib.fan_refview   REFERENCE_SPEC 1's fan2 camera and the fidelity instruments
    props_lib.fan_gallery   the pack gallery, the line sheet, the fold sheet
    pipeline.skeletal_prop  (NEW) skeletal QA, the multi-file export, the skeletal sidecar

WHAT IT READS: numbers only.  fan2.png is opened only after every map is written, for the side-by-side, the
crops and the fidelity metrics.

WHAT IT NEVER TOUCHES: the shuriken pack, the smoke bomb, the black hat, the paper bomb, the materials build,
Scripts/pipeline's existing modules.  Their hashes are checked at the start and at the end.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "Scripts"))
sys.path.insert(0, str(PROJECT / "Scripts" / "props"))

import bpy                                                        # noqa: E402
import numpy as np                                                # noqa: E402

from pipeline import skeletal_prop as SKP                         # noqa: E402
from props_lib import fan_fold as FF                              # noqa: E402
from props_lib import fan_geom as G                               # noqa: E402
from props_lib import fan_look as LK                              # noqa: E402
from props_lib import fan_paint as FP                             # noqa: E402
from props_lib import fan_refview as RV                           # noqa: E402
from props_lib import fan_seethrough as ST                        # noqa: E402
from props_lib import fan_tassel as TS                            # noqa: E402
from props_lib.fan_spec import D2R, FAN, assert_clean, build_to, deny_hits  # noqa: E402

LIB_VERSION = "1.0.0"
ASSETS = PROJECT / "Assets"
EXPORTS = PROJECT / "Exports" / "Fan"
TEXTURES = EXPORTS / "Textures"
RECOLOUR = TEXTURES / "Recolour"
RENDERS = PROJECT / "Renders" / "Fan"
WORK = PROJECT / "WorkFiles" / "fan"
BUILD_WORK = WORK / "build"
REFERENCE = PROJECT / "References" / "Fan" / "fan2.png"
REFERENCE_SHA_PREFIX = "45432662"
FOLD_CACHE = PROJECT / "WorkFiles" / "fan" / "fold_bind_cache.json"

#: specular scale per part (Specular = scale x ORM.A); rivet is metal
SPEC_SCALE = {"leaf": 0.5, "sticks": 0.6, "tassel": 0.5}
ROUGH_RANGE = {"leaf": (0.50, 0.75), "sticks": (0.20, 0.45), "tassel": (0.45, 0.75), "rivet": (0.05, 0.35)}
PART_SLOT = {"leaf": 0, "sticks": 1, "rivet": 2}
FPS_OPENCLOSE = 60
FPS_OPENNESS = 60

T0 = time.time()
spec_caption = {}


def log(*parts):
    print(f"[fan {time.time() - T0:7.1f}s]", *parts, flush=True)


def sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# =========================================================================== frozen assets
FROZEN_GLOBS = [
    ("shuriken_blend", "Assets/Shuriken.blend"),
    ("smokebomb_blend", "Assets/SmokeBomb.blend"),
    ("blackhat_blend", "Assets/BlackHat.blend"),
    ("paperbomb_blend", "Assets/PaperBomb.blend"),
]
FROZEN_DIRS = ["Exports/Shuriken", "Exports/SmokeBomb", "Exports/BlackHat", "Exports/PaperBomb",
               "Scripts/shuriken", "Scripts/unreal/materials", "Renders/Shuriken", "Renders/SmokeBomb",
               "Renders/BlackHat", "Renders/PaperBomb"]
FROZEN_PIPELINE = ["Scripts/pipeline/__init__.py", "Scripts/pipeline/export_fbx.py", "Scripts/pipeline/qa_check.py",
                   "Scripts/pipeline/helpers.py", "Scripts/pipeline/textures.py", "Scripts/pipeline/lock.py",
                   "Scripts/pipeline/ue_import_sockets.py", "Scripts/pipeline/garment_qa.py",
                   "Scripts/pipeline/garment_helpers.py", "Scripts/pipeline/test_pipeline.py",
                   "Scripts/pipeline/test_qa_negative.py", "Scripts/pipeline/test_garment.py"]
FROZEN_PROPS = ["Scripts/props/build_black_hat.py", "Scripts/props/build_smoke_bomb.py",
                "Scripts/props/build_paper_bomb.py"]


def frozen_hashes() -> dict:
    out = {}
    for key, rel in FROZEN_GLOBS:
        p = PROJECT / rel
        out[rel] = sha256(p) if p.is_file() else None
    for rel in FROZEN_PIPELINE + FROZEN_PROPS:
        p = PROJECT / rel
        out[rel] = sha256(p) if p.is_file() else None
    for d in FROZEN_DIRS:
        base = PROJECT / d
        if not base.exists():
            continue
        h = hashlib.sha256()
        n = 0
        for p in sorted(base.rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts:
                h.update(str(p.relative_to(PROJECT)).encode())
                h.update(sha256(p).encode())
                n += 1
        out[d] = {"files": n, "tree_sha256": h.hexdigest()}
    for p in sorted((PROJECT / "Scripts" / "props" / "props_lib").glob("*.py")):
        if not p.name.startswith("fan_"):
            out[str(p.relative_to(PROJECT)).replace("\\", "/")] = sha256(p)
    return out


# =========================================================================== fold
def stage_fold(spec, report, quick=False):
    key = FF.bind_cache_key(spec)
    cache = json.loads(FOLD_CACHE.read_text()) if FOLD_CACHE.is_file() else {}
    if cache.get("key") == key:
        off = np.array(cache["offsets"])
        rep = cache["report"]
        log(f"  bind offsets from the cache ({key}): worst crack {rep['worst_after_mm']:.5f} mm")
    else:
        log("  optimising the bind geometry (deterministic Nelder-Mead, ~12 min)")
        off, rep = FF.optimise_bind(spec, iters=120, log=log)
        FOLD_CACHE.parent.mkdir(parents=True, exist_ok=True)
        FOLD_CACHE.write_text(json.dumps({"key": key, "offsets": np.asarray(off).tolist(), "report": rep}, indent=1))
    fs = FF.FoldSolver(spec, off)
    report["fold"] = {"bind_optimisation": rep, "key": key, "page_tilt_closed_deg": round(fs.page_tilt_deg(0.0), 4),
                      "leaf_z_pitch_mm": round(spec.leaf_z_pitch, 5), "stick_pitch_deg": spec.stick_pitch_deg,
                      "leaf_pitch_deg": spec.leaf_pitch_deg, "face_angle_deg": spec.face_angle_deg,
                      "gamma_open_deg": spec.gamma_deg}
    return fs


def openness_samples():
    """0.05 deg .. open, dense near closed (the pleats lie down in the last few degrees)."""
    s = sorted(set([0.0] + [float(x) for x in np.geomspace(1e-4, 0.1, 40)] + [float(x) for x in np.linspace(0.1, 1.0, 46)]))
    return s


def posed_vertices(spec, fs, mb, s) -> np.ndarray:
    """LOD0's vertices (mm, armature space) with the mechanism at openness s."""
    Ts = {f"stick_{i:02d}": M for i, M in enumerate(fs.sticks_T(s))}
    for j, M in enumerate(fs.face_T(s)):
        Ts[f"leaf_{j:02d}"] = M
    Ts["pivot"] = np.eye(4)
    return G.skin(mb, Ts, FF.apply)


def fold_proof_numpy(spec, fs, mb, samples) -> dict:
    """G1-G3 on the numpy LOD0 at every sample: cracks, triangle intersections (leaf/leaf non-adjacent,
    leaf/sticks, stick/stick, leaf/rivet, sticks/rivet), leaf never inside a guard, dihedral angles."""
    P, T, B = mb.arrays()
    names = mb.bone_names
    TP = np.array(mb.TP)
    TG = np.array(mb.TG)
    is_leaf = np.isin(TP, ["leaf", "flaps"])
    is_stick = TP == "sticks"
    is_rivet = TP == "rivet"
    lfi = np.array([int(g.split("_")[1]) if g.startswith("leaf_") else (-1 if g == "flap_front" else
                   (2 * (spec.n_sticks - 1)) if g == "flap_rear" else -99) for g in TG])
    sidx = np.array([int(g.split("_")[1]) if g.startswith("stick_") else -1 for g in TG])
    rows = []
    worst = {"crack_mm": 0.0, "hits": 0, "min_mid_dihedral_deg": 180.0, "min_rib_dihedral_deg": 180.0,
             "adjacent_crossings_at_bind": None, "adjacent_crossings_max": 0}
    L_idx, S_idx, R_idx = np.nonzero(is_leaf)[0], np.nonzero(is_stick)[0], np.nonzero(is_rivet)[0]
    flap_owner = {-1: 0, 2 * (spec.n_sticks - 1): spec.n_sticks - 1}
    for s in samples:
        Ts = {f"stick_{i:02d}": M for i, M in enumerate(fs.sticks_T(s))}
        faces = fs.face_T(s)
        for j, M in enumerate(faces):
            Ts[f"leaf_{j:02d}"] = M
        Ts["pivot"] = np.eye(4)
        Q = G.skin(mb, Ts, FF.apply)
        tri = Q[T]
        c = fs.cracks(s, faces)
        n_ll, ex_ll = FF.count_intersections(tri[L_idx], tri[L_idx], same=True,
                                             exclude=lambda a, b: np.abs(lfi[L_idx][a] - lfi[L_idx][b]) <= 1)
        # STRICT: neighbouring faces too (they share a fold line): at bind they must not cross at all; posed, a
        # crossing can only be the fold's own crack (two rigid copies of one fold line), so its depth is measured
        adj = adjacent_crossings(tri[L_idx], lfi[L_idx])

        def ls_ex(a, b):
            # a glued flap touches its own guard by design
            la = lfi[L_idx][a]
            own = np.array([flap_owner.get(int(v), -5) for v in la])
            return own == sidx[S_idx][b]
        n_ls, ex_ls = FF.count_intersections(tri[L_idx], tri[S_idx], exclude=ls_ex)
        n_ss, ex_ss = FF.count_intersections(tri[S_idx], tri[S_idx], same=True,
                                             exclude=lambda a, b: sidx[S_idx][a] == sidx[S_idx][b])
        n_lr, _ = FF.count_intersections(tri[L_idx], tri[R_idx])
        n_sr, _ = FF.count_intersections(tri[S_idx], tri[R_idx])
        zl = tri[L_idx][:, :, 2]
        z_front_guard_top = spec.stick_z(0)[1]
        z_rear_guard_bot = spec.stick_z(spec.n_sticks - 1)[0]
        # dihedrals of gap 0 (all gaps are the same)
        tpl = fs.tpl
        a_rib = FF.apply(faces[0], tpl.rib_pts[0])
        a_mid = FF.apply(faces[0], tpl.mid_pts[0])
        b_rib = FF.apply(faces[1], tpl.rib_pts[1])
        c_mid = FF.apply(faces[2], tpl.mid_pts[1])
        d_mid = FF.dihedral_deg(a_mid[0], a_mid[1], a_rib[0], b_rib[0])
        d_val = FF.dihedral_deg(b_rib[0], b_rib[1], FF.apply(faces[1], tpl.mid_pts[0])[0], c_mid[0])
        hits = n_ll + n_ls + n_ss + n_lr + n_sr
        row = {"s": round(s, 6), "opening_deg": round(spec.opening_at(s), 4), "crack_mm": round(c["worst_mm"], 5),
               "rib_fold_mm": round(c["rib_fold_mm"], 5), "mid_fold_mm": round(c["mid_fold_mm"], 5),
               "leaf_off_rib_mm": round(c["leaf_off_rib_mm"], 5),
               "hits": {"leaf_leaf": n_ll, "leaf_sticks": n_ls, "stick_stick": n_ss, "leaf_rivet": n_lr, "sticks_rivet": n_sr},
               "leaf_z_mm": [round(float(zl.min()), 3), round(float(zl.max()), 3)],
               "leaf_beyond_stack_faces_mm": round(max(0.0, float(zl.max()) - z_front_guard_top,
                                                       z_rear_guard_bot - float(zl.min())), 3),
               "dihedral_mid_deg": round(float(d_mid), 3), "dihedral_rib_deg": round(float(d_val), 3),
               "adjacent_crossings": adj["pairs"]}
        if hits:
            row["examples"] = {"leaf_leaf": ex_ll[:3], "leaf_sticks": ex_ls[:3], "stick_stick": ex_ss[:3]}
        rows.append(row)
        worst["crack_mm"] = max(worst["crack_mm"], c["worst_mm"])
        worst["hits"] += hits
        worst["min_mid_dihedral_deg"] = min(worst["min_mid_dihedral_deg"], float(d_mid))
        worst["min_rib_dihedral_deg"] = min(worst["min_rib_dihedral_deg"], float(d_val))
        worst["adjacent_crossings_max"] = max(worst["adjacent_crossings_max"], adj["pairs"])
        if abs(s - 1.0) < 1e-12:
            worst["adjacent_crossings_at_bind"] = adj["pairs"]
    closed = rows[0]
    return {"samples": len(rows), "rows": rows, "worst": {k: (round(v, 5) if isinstance(v, float) else v)
                                                         for k, v in worst.items()},
            "closed": {"leaf_z_mm": closed["leaf_z_mm"], "leaf_beyond_stack_faces_mm": closed["leaf_beyond_stack_faces_mm"]}}


SEETHROUGH_OPENINGS = (163.2, 122.8, 82.4, 36.0, 15.0, 5.0)
SEETHROUGH_VIEWS = ("front", "back", "rim_oblique_30", "rim_oblique_45", "rim_oblique_60", "rear_oblique_30",
                    "rear_oblique_45", "pivot_oblique_45", "side_oblique_45_plus", "side_oblique_45_minus")


def seethrough_proof(spec, fs, meshes) -> dict:
    """Round 3 (G5): daylight through the fan round the leaf's inner edge (props_lib.fan_seethrough) on every LOD at
    SEETHROUGH_OPENINGS, with the leaf-zone prongs and, for comparison on LOD0, without them (round 2's construction)."""
    out = {"openings": list(SEETHROUGH_OPENINGS), "views": list(SEETHROUGH_VIEWS), "lods": {}}
    for lod, mb in enumerate(meshes):
        P, T, B = mb.arrays()
        prong = np.array([k.startswith("prong") for k in mb.TK])
        rows = {}
        for op in SEETHROUGH_OPENINGS:
            s = spec.s_for_opening(op)
            Q = posed_vertices(spec, fs, mb, s)
            row = {"with_prongs": ST.count(Q, T, spec, s, views=SEETHROUGH_VIEWS)}
            if lod == 0:
                row["without_prongs_round2"] = ST.count(Q, T[~prong], spec, s, views=SEETHROUGH_VIEWS)
            rows[f"{op:g}"] = row
        out["lods"][f"LOD{lod}"] = rows
        out.setdefault("reference_camera", {})[f"LOD{lod}"] = ST.count_reference(posed_vertices(spec, fs, mb, 1.0), T, spec)
    w = out["lods"]["LOD0"]
    out["front_back_all_lods_all_openings"] = int(sum(r["with_prongs"][v] for L in out["lods"].values() for r in L.values()
                                                      for v in ("front", "back")))
    out["rim45_LOD0_by_opening"] = {k: r["with_prongs"]["rim_oblique_45"] for k, r in w.items()}
    out["rim30_LOD0_by_opening"] = {k: r["with_prongs"]["rim_oblique_30"] for k, r in w.items()}
    out["total_LOD0_with_vs_without"] = [int(sum(r["with_prongs"]["total"] for r in w.values())),
                                         int(sum(r["without_prongs_round2"]["total"] for r in w.values()))]
    return out


def adjacent_crossings(tri: np.ndarray, face: np.ndarray) -> dict:
    """Crossing triangle pairs between NEIGHBOURING leaf faces (faces j and j+1 share a fold line; the G2 count leaves
    them out).  At bind there must be none (round 1 had 75: its back layers were offset at the folds); posed, the two
    rigid copies of a fold line are up to the crack apart, so two faces meeting at a small dihedral cross along
    their shared fold by that much - the crack, gated at 0.1 mm, seen another way."""
    n, _ = FF.count_intersections(tri, tri, same=True, exclude=lambda a, b: np.abs(face[a] - face[b]) != 1)
    return {"pairs": int(n)}


def closed_bundle(spec, fs, mb) -> dict:
    """The closed fan's leaf bundle: width at the tip and at the leaf base beside the guards."""
    P, T, B = mb.arrays()
    faces = fs.face_T(0.0)
    tpl = fs.tpl
    pts = []
    for j, M in enumerate(faces):
        pts.append(FF.apply(M, np.vstack([tpl.rib_pts[j // 2 + (j % 2)], tpl.mid_pts[j // 2]])))
    pts = np.vstack(pts)
    lam0 = spec.leaf_line_deg(0, 0.0) * D2R
    u = np.array([math.cos(lam0), math.sin(lam0)])
    n = np.array([-u[1], u[0]])
    lat = pts[:, :2] @ n
    rad = pts[:, :2] @ u
    tip = rad > spec.r_out - 5
    base = rad < spec.r_in + 5
    return {"lateral_extent_tip_mm": [round(float(lat[tip].min()), 3), round(float(lat[tip].max()), 3)],
            "lateral_extent_base_mm": [round(float(lat[base].min()), 3), round(float(lat[base].max()), 3)],
            "z_extent_mm": [round(float(pts[:, 2].min()), 3), round(float(pts[:, 2].max()), 3)],
            "front_guard_lateral_at_tip_mm": [round(-spec.L * math.sin(spec.leaf_off_front_deg * D2R) - 0.5 * spec.guard_width_mm(spec.L), 3),
                                              round(-spec.L * math.sin(spec.leaf_off_front_deg * D2R) + 0.5 * spec.guard_width_mm(spec.L), 3)],
            "note": "lateral 0 = the common leaf line at the closed pose; +lateral = toward the side the fan opens. "
                    "Round 2: the pages lie on the -lateral side (the valleys fall behind the leaf lines), beside "
                    "the front guard's outer edge"}


# =========================================================================== geometry
def stage_geometry(spec, fs, report):
    fan, infos, atl = [], [], None
    for lod in range(3):
        mb, info, atl = G.build_lod(spec, lod, fs.tpl, atl)
        fan.append(mb)
        infos.append(info)
        log(f"  SK_Fan LOD{lod}: {info['triangles']} triangles {info['parts']}")
    tas, tinfo = [], []
    for lod in range(3):
        mb, info = TS.build_tassel(spec, lod)
        ppmm = TS.tassel_uvs(mb, spec.tassel_texture_size)
        info["ppmm"] = round(ppmm, 3)
        tas.append(mb)
        tinfo.append(info)
        log(f"  SK_Fan_Tassel LOD{lod}: {info['triangles']} triangles")
    report["geometry"] = {"fan": infos, "tassel": tinfo, "stick_atlas_ppmm": round(atl["ppmm"], 4)}
    return fan, tas


# =========================================================================== textures
def _tris_for(mb, slot, layer_ok=("front", "flap_front", "")):
    idx = [t for t in range(len(mb.T)) if mb.TS[t] == slot and mb.TLAY[t] in layer_ok]
    return idx


def paint_channels(mb, slot, size, painter, base_lum, extra=None):
    idx = _tris_for(mb, slot, ("front", "")) if slot == 0 else _tris_for(mb, slot, ("front", "", "back"))
    uvt = np.array([mb.TUV[t] for t in idx])
    loc = np.array([mb.TL[t] for t in idx])
    kind_code = {"leaf": 0, "top": 0, "bottom": 1, "wall": 2, "hole": 3, "recess": 4, "0": 0, "1": 1, "2": 2, "3": 3, "": 0,
                 "prong_top": 5, "prong_bottom": 6, "prong_wall": 2}
    kind = np.array([[kind_code.get(mb.TK[t], 0)] * 3 for t in idx], np.float64)[..., None]
    grp = np.array([[_group_num(mb.TG[t])] * 3 for t in idx], np.float64)[..., None]
    owner, att = FP.rasterise(uvt, {"loc": loc, "kind": kind, "grp": grp}, size, np.arange(len(idx)))
    wr = owner >= 0
    L = att["loc"][wr]
    K = np.rint(att["kind"][wr][:, 0]).astype(int)
    S = np.rint(att["grp"][wr][:, 0]).astype(int)
    f, rough, spec_m, hgt = painter(L, K, S)
    H = W = size
    ch = {"written": wr, "alb": np.zeros((H, W)), "rough": np.zeros((H, W)), "spec": np.zeros((H, W)),
          "hgt": np.zeros((H, W)), "ao": np.ones((H, W))}
    ch["alb"][wr] = base_lum * f
    ch["rough"][wr] = rough
    ch["spec"][wr] = spec_m
    ch["hgt"][wr] = hgt
    own = owner.copy()
    own = FP.dilate(own, {k: ch[k] for k in ("alb", "rough", "spec", "hgt")}, iters=24)
    ch["own"] = own
    return ch


def _group_num(g):
    try:
        return int(g.split("_")[-1])
    except ValueError:
        return {"flap_front": 0, "flap_rear": 25, "cord": 0, "knot": 1, "neck": 2, "skirt": 3}.get(g, 0)


def stage_textures(spec, fan, tas, report, quick=False):
    TEXTURES.mkdir(parents=True, exist_ok=True)
    RECOLOUR.mkdir(parents=True, exist_ok=True)
    stems = spec.texture_stems
    lum = lambda c: float(np.asarray(c) @ FP.LUMA)
    grain = 25 * spec.face_angle_deg          # the flat leaf's centre line
    atl = report["geometry"]
    chs = {
        "leaf": paint_channels(fan[0], 0, spec.texture_size, lambda L, K, S: FP.paint_leaf(L, grain), lum(spec.leaf_colour_linear)),
        "sticks": paint_channels(fan[0], 1, spec.texture_size,
                                 lambda L, K, S: FP.paint_stick(L, K, S, half_width=lambda x: 0.5 * np.array([spec.rib_width_mm(v) for v in x]),
                                                                rounded=(K <= 1) & (S > 0) & (S < spec.n_sticks - 1), edge_band_mm=1.6, edge_drop_mm=0.22),
                                 lum(spec.sticks_colour_linear)),
        "rivet": paint_channels(fan[0], 2, spec.rivet_texture_size, lambda L, K, S: FP.paint_rivet(L, K), lum(spec.rivet_colour_linear)),
        "tassel": paint_channels(tas[0], 0, spec.tassel_texture_size, lambda L, K, S: FP.paint_tassel(L, K), lum(spec.tassel.colour_linear)),
    }
    chs["leaf"]["px_per_mm"] = report["geometry"]["fan"][0]["leaf_ppmm"]
    chs["sticks"]["px_per_mm"] = report["geometry"]["stick_atlas_ppmm"]
    chs["rivet"]["px_per_mm"] = 20.0
    chs["tassel"]["px_per_mm"] = report["geometry"]["tassel"][0]["ppmm"]
    chroma = {"leaf": spec.leaf_colour_linear, "sticks": spec.sticks_colour_linear, "rivet": spec.rivet_colour_linear,
              "tassel": spec.tassel.colour_linear}
    maps, paths = _finish_all(chs, chroma, stems)
    report["_chs"] = chs
    return chs, maps, paths, chroma


def _finish_all(chs, chroma, stems):
    maps, paths = {}, {}
    for k, ch in chs.items():
        m = FP.finish(ch, chroma[k], rough_range=ROUGH_RANGE[k], metal=(k == "rivet"))
        maps[k] = m
        keys = ("BC", "ORM", "N") if k == "rivet" else ("BC", "ORM", "N", "Detail")
        paths[k] = {kk: LK.write_png(TEXTURES / f"{stems[k]}_{kk}.png", m[kk]) for kk in keys}
    return maps, paths


def make_materials(spec, maps, paths, pack=True):
    mats = {}
    names = spec.materials
    for k in ("leaf", "sticks", "tassel"):
        m = maps[k]
        mats[k] = LK.make_material(names[k], paths[k], m["tint_linear"], m["detail_bias"], m["detail_scale"],
                                   SPEC_SCALE[k], metal=False, pack=pack)
    mats["rivet"] = LK.make_material(names["rivet"], paths["rivet"], metal=True, pack=pack)
    return mats


def stage_ao(spec, fan, tas, chs, maps, paths, chroma, report, quick=False):
    """AO in the open (bind) pose on LOD0 with the leaf's FRONT layer only (the back layer shares its UVs)."""
    tmp_mats = make_materials(spec, maps, paths, pack=False)
    front = fan[0].subset([t for t in range(len(fan[0].T)) if fan[0].TLAY[t] != "back"])
    ob = LK.mesh_object(front, "__AO_Fan", [tmp_mats["leaf"], tmp_mats["sticks"], tmp_mats["rivet"]])
    if bpy.context.scene.world is None:
        bpy.context.scene.world = bpy.data.worlds.new("__ao_world")
    aos = LK.bake_ao(ob, {0: spec.texture_size, 1: spec.texture_size, 2: spec.rivet_texture_size},
                     samples=32 if quick else 256, distance_m=0.004)
    me = ob.data
    bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.meshes.remove(me)
    tob = LK.mesh_object(tas[0], "__AO_Tassel", [tmp_mats["tassel"]])
    taos = LK.bake_ao(tob, {0: spec.tassel_texture_size}, samples=32 if quick else 256, distance_m=0.004)
    me = tob.data
    bpy.data.objects.remove(tob, do_unlink=True)
    bpy.data.meshes.remove(me)
    for m in tmp_mats.values():
        for n in m.node_tree.nodes:
            if n.type == "TEX_IMAGE" and n.image is not None:
                bpy.data.images.remove(n.image)
        bpy.data.materials.remove(m)
    rep = {}
    for k, a in (("leaf", aos[0]), ("sticks", aos[1]), ("rivet", aos[2]), ("tassel", taos[0])):
        reached = a > 1e-6
        fill = float(a[reached].mean()) if reached.any() else 1.0
        a = np.where(reached, a, fill)
        # a soft AO: ORM.R is Unreal's indirect occlusion; the pose changes, so keep it gentle (0.35 .. 1)
        a = 1.0 - 0.65 * (1.0 - np.clip(a, 0, 1))
        chs[k]["ao"] = a
        rep[k] = {"reached_fraction": round(float(reached.mean()), 4), "mean": round(float(a.mean()), 4),
                  "p01": round(float(np.percentile(a, 1)), 4)}
    maps, paths = _finish_all(chs, chroma, FAN.texture_stems)
    report["ao_bake"] = rep
    return maps, paths


def stage_recolour(spec, maps, paths, report):
    """Detail16 (lossless 16-bit linear copy of each part's Detail) + recolour_maps.json in the pack's schema."""
    stems = spec.texture_stems
    out = {"schema": "ninjapack.recolour_maps/1", "item": "Fan", "generated": time.strftime("%Y-%m-%d"),
           "generator": {"script": "Scripts/props/build_fan.py", "script_sha256": sha256(__file__),
                         "module": "Scripts/props/props_lib/fan_paint.py",
                         "module_sha256": sha256(PROJECT / "Scripts/props/props_lib/fan_paint.py"),
                         "version": LIB_VERSION, "blender": bpy.app.version_string},
           "sidecar": {"file": "Exports/Fan/SK_Fan.skeletal.json"}, "maps": {}, "parts": {}}
    part_names = PART_NAMES
    rc = _recolour_common()
    for k in ("leaf", "sticks", "tassel"):
        m = maps[k]
        d16 = FP.detail16(m["Detail"])
        p16 = LK.write_png(RECOLOUR / f"{stems[k]}_Detail16.png", d16, bits=16)
        dec = d16.astype(np.float64) / 65535.0
        back8 = np.rint(FP.srgb_encode(dec) * 255.0).astype(np.uint8)
        lossless = bool((back8 == m["Detail"]).all())
        name = f"{stems[k]}_Detail16"
        out["maps"][name] = {"file": f"Exports/Fan/Textures/Recolour/{name}.png", "sha256": sha256(p16),
                             "size": list(d16.shape), "format": "PNG, 16-bit greyscale (colour type 0), no colour chunks, row 0 = top",
                             "encoding": "LINEAR: value / 65535 = the linear detail d (sRGB-decoded shipped Detail)",
                             "unreal_import": {"srgb": False, "compression": "TC_GRAYSCALE", "expected_pc_format": "G16",
                                               "sampler": "SAMPLERTYPE_LINEAR_GRAYSCALE", "mips": "TMGS_FROM_TEXTURE_GROUP",
                                               "address": "Wrap"},
                             "source": {"file": f"Exports/Fan/Textures/{stems[k]}_Detail.png", "sha256": sha256(paths[k]["Detail"]),
                                        "stored_levels": int(len(np.unique(m["Detail"])))},
                             "recipe": "d16 = round(65535 * sRGBdecode(Detail8 / 255)); lossless (one code per 8-bit level)",
                             "gates": {"lossless_back_to_8bit": lossless}}
        pn = part_names[k]
        # round 3: the pack's v1 fields (recolour_common.fabric_constants over EVERY texel of the Detail16, exactly as the
        # pack's make_detail16.py does for the other items), so derive_constants_fan.py can derive the v2 constants
        n = m["detail_bias"] + m["detail_scale"] * dec
        kc = rc.fabric_constants(n)
        out["parts"][pn] = {"slot_material": spec.materials[k], "instance": f"MI_Fan_{pn}", "master": "M_Fabric_Master",
                            "detail_map": name,
                            "base_colour_map_reference": {"file": f"Exports/Fan/Textures/{stems[k]}_BC.png",
                                                          "sha256": sha256(paths[k]["BC"])},
                            "params": {"Colour": [*[round(float(x), 6) for x in m["tint_linear"]], 1.0],
                                       "Detail Bias": m["detail_bias"], "Detail Scale": m["detail_scale"],
                                       "Detail Mean": kc["mean"], "Detail Highlight Ratio": kc["highlight_ratio"],
                                       "Detail Moments Low": kc["moments_low"], "Detail Moments High": kc["moments_high"],
                                       "Dark Detail Follow": rc.DARK_FOLLOW, "Albedo Ceiling": rc.ALBEDO_CEILING},
                            "n_range": [kc["n_min"], kc["n_max"]], "fraction_n_le_1": kc["fraction_n_le_1"],
                            "moment_samples": {"c": list(rc.MOMENT_POINTS), "low": kc["moment_samples_low"],
                                               "high": kc["moment_samples_high"]},
                            "param_notes": {"Colour": "linear RGBA; the part's MEAN colour (the buyer's one colour); "
                                                      "default = REFERENCE_SPEC 9's reference colour"},
                            "derivation": "BaseColor = saturate(Tint x (DetailBias + DetailScale x Detail)), Tint = the "
                                          "part's MEAN colour over its written texels. The v1 fields (Detail Mean, "
                                          "Highlight Ratio, Moments) are recolour_common.fabric_constants over every texel "
                                          "of the Detail16; recolour_constants.json (v2: covered texels, Lightest Colour, "
                                          "mip compensation) is written by "
                                          "Scripts/unreal/materials/maps/derive_constants_fan.py"}
    out["pass"] = all(v["gates"]["lossless_back_to_8bit"] for v in out["maps"].values())
    path = RECOLOUR / "recolour_maps.json"
    path.write_text(json.dumps(out, indent=1), encoding="utf-8")
    report["recolour"] = {"file": str(path.relative_to(PROJECT)), "parts": list(out["parts"]),
                          "lossless": {k: v["gates"]["lossless_back_to_8bit"] for k, v in out["maps"].items()}}


PART_NAMES = {"leaf": "Leaf", "sticks": "Ribs", "tassel": "Tassel"}   # round 3: the buyer's part names (MI_Fan_<part>)


def _recolour_common():
    """The pack's recolour helpers (Scripts/unreal/materials/maps/recolour_common.py), read-only: no bytecode is written
    into the materials folder."""
    import importlib.util
    old = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        path = PROJECT / "Scripts" / "unreal" / "materials" / "maps" / "recolour_common.py"
        sp = importlib.util.spec_from_file_location("np_recolour_common_ro", str(path))
        mod = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(mod)
        return mod
    finally:
        sys.dont_write_bytecode = old


def texture_report(spec, maps, paths, report):
    tex = {"maps": {k: {kk: str(Path(v).relative_to(PROJECT)) for kk, v in p.items()} for k, p in paths.items()},
           "sha256": {k: {kk: sha256(v) for kk, v in p.items()} for k, p in paths.items()},
           "sizes": {k: {kk: int(maps[k][kk].shape[0]) for kk in p} for k, p in paths.items()},
           "tint_linear": {k: [round(float(x), 6) for x in maps[k]["tint_linear"]] for k in maps},
           "detail_bias": {k: maps[k].get("detail_bias") for k in maps},
           "detail_scale": {k: maps[k].get("detail_scale") for k in maps},
           "recolour": {k: maps[k].get("recolour") for k in maps if "recolour" in maps[k]},
           "roughness_stats": {k: maps[k]["roughness_stats"] for k in maps},
           "albedo_stats": {k: {kk: round(v, 6) for kk, v in maps[k]["albedo_stats"].items()} for k in maps},
           "mip_parity": {k: FP.mip_parity(maps[k]) for k in maps if "Detail" in maps[k]},
           "colour_chunks": {k: {kk: [c for c in LK.png_chunks(v) if c in ("sRGB", "gAMA", "cHRM", "iCCP")]
                                 for kk, v in p.items()} for k, p in paths.items()},
           "spec_scale": SPEC_SCALE, "roughness_range": {k: list(v) for k, v in ROUGH_RANGE.items()}}
    tex["power_of_two"] = all((s & (s - 1)) == 0 for d in tex["sizes"].values() for s in d.values())
    ref = {"leaf": spec.leaf_colour_linear, "sticks": spec.sticks_colour_linear, "tassel": spec.tassel.colour_linear}
    tex["tint_vs_reference_colour"] = {k: {"tint": tex["tint_linear"][k], "reference_rs9": list(ref[k]),
                                           "max_abs_diff": round(float(np.abs(np.array(tex["tint_linear"][k]) - np.array(ref[k])).max()), 6)}
                                       for k in ref}
    report["textures"] = tex


# =========================================================================== blender objects
def bone_list(spec, fs):
    n = spec.n_sticks
    bones = [("pivot", (0, 0, 0), (0, 12.0, 0), "", (0, 0, 1))]
    for i in range(n):
        z0, z1 = spec.stick_z(i)
        zc = 0.5 * (z0 + z1)
        a = spec.stick_axis_deg(i, 1.0) * D2R
        # round 3: the sticks are children of 'pivot' (the rivet; it never moves), so the fan's one physics body, which
        # Unreal's builder puts on 'pivot', carries every stick and leaf face when the component is simulated
        bones.append((f"stick_{i:02d}", (0, 0, zc), (spec.L * math.cos(a), spec.L * math.sin(a), zc), "pivot", (0, 0, 1)))
    tpl = fs.tpl
    for j in range(2 * (n - 1)):
        k = j // 2 + (j % 2)                     # the leaf line this face hinges on
        z = tpl.z[k]
        a = tpl.lam_deg[k] * D2R
        # a face bone is the CHILD of the stick it hinges on: its local motion is then one rotation about a
        # line fixed in the stick (the hinge), which Unreal's per-bone slerp between keys reproduces exactly;
        # as a top-level bone its motion would be the hinge turn composed with the stick's turn about Z, and a
        # single slerp of that composition misses by up to ~1.9 mm between keys (measured)
        bones.append((f"leaf_{j:02d}", (0, 0, z), (spec.L * math.cos(a), spec.L * math.sin(a), z), f"stick_{k:02d}",
                      (0, 0, 1)))
    return bones


def stage_objects(spec, fs, fan, tas, mats, report):
    arm = LK.make_armature("root", bone_list(spec, fs))
    slots = [mats["leaf"], mats["sticks"], mats["rivet"]]
    objs = []
    for i, mb in enumerate(fan):
        name = spec.mesh_name if i == 0 else f"{spec.mesh_name}_LOD{i}"
        assert_clean(name)
        objs.append(LK.mesh_object(mb, name, slots, arm, weights=mb.W))
    tarm = LK.make_armature("root_tassel", [(n, h, t, p, (0, 1, 0)) for n, h, t, p in TS.bone_table(spec)])
    tobjs = []
    for i, mb in enumerate(tas):
        name = spec.tassel_name if i == 0 else f"{spec.tassel_name}_LOD{i}"
        tobjs.append(LK.mesh_object(mb, name, [mats["tassel"]], tarm, weights=mb.W))
    report["skeleton"] = {"bones": [b.name for b in arm.data.bones], "bone_count": len(arm.data.bones) + 1,
                          "root": "the armature object 'root' (Unreal's root bone)",
                          "tassel_bones": [b.name for b in tarm.data.bones]}
    return arm, objs, tarm, tobjs


def fan_pose_T(spec, fs, s):
    Tb = {f"stick_{i:02d}": M for i, M in enumerate(fs.sticks_T(s))}
    for j, M in enumerate(fs.face_T(s)):
        Tb[f"leaf_{j:02d}"] = M
    Tb["pivot"] = np.eye(4)
    return Tb


def ease(u):
    return u * u * (3 - 2 * u)


def stage_actions(spec, fs, arm, report):
    acts = {}
    # A_Fan_OpenClose: closed -> open (0.5 s, eased) -> hold 0.3 s -> closed (0.5 s), 30 fps, keys every frame
    n_move, n_hold = int(round(0.5 * FPS_OPENCLOSE)), int(round(0.3 * FPS_OPENCLOSE))
    svals = [ease(f / n_move) for f in range(n_move + 1)] + [1.0] * n_hold + \
            [ease(1 - f / n_move) for f in range(1, n_move + 1)]
    frames = [(f, fan_pose_T(spec, fs, s)) for f, s in enumerate(svals)]
    acts["A_Fan_OpenClose"] = (LK.key_action(arm, "A_Fan_OpenClose", frames), svals, FPS_OPENCLOSE)
    # A_Fan_Openness: linear in the opening angle, closed (frame 0) to open (last frame), 1 s at 60 fps
    n = FPS_OPENNESS
    svals2 = [f / n for f in range(n + 1)]
    frames = [(f, fan_pose_T(spec, fs, s)) for f, s in enumerate(svals2)]
    acts["A_Fan_Openness"] = (LK.key_action(arm, "A_Fan_Openness", frames), svals2, FPS_OPENNESS)
    # A_Fan_OpenPose: the bind (open) pose, two frames
    frames = [(0, fan_pose_T(spec, fs, 1.0)), (1, fan_pose_T(spec, fs, 1.0))]
    acts["A_Fan_OpenPose"] = (LK.key_action(arm, "A_Fan_OpenPose", frames), [1.0, 1.0], FPS_OPENCLOSE)
    arm.animation_data.action = None
    LK.pose(arm, {})
    report["animations"] = {k: {"frames": len(v[1]), "fps": v[2], "seconds": round((len(v[1]) - 1) / v[2], 4),
                                "openness_per_frame": [round(x, 6) for x in v[1]],
                                "opening_deg_per_frame": [round(spec.opening_at(x), 4) for x in v[1]]}
                            for k, v in acts.items()}
    return acts


def half_key_proof(spec, fs, mb, acts) -> dict:
    """Unreal plays a key-per-frame sequence by interpolating each bone between keys (quaternion slerp, linear
    translation).  Pose every bone that way at every HALF-key of every sequence and measure the cracks and
    the intersections, exactly as the fold proof does on the keys."""
    from mathutils import Quaternion
    P, T, B = mb.arrays()
    names = mb.bone_names
    TP = np.array(mb.TP)
    TG = np.array(mb.TG)
    is_leaf = np.isin(TP, ["leaf", "flaps"])
    L_idx = np.nonzero(is_leaf)[0]
    S_idx = np.nonzero(TP == "sticks")[0]
    lfi = np.array([int(g.split("_")[1]) if g.startswith("leaf_") else (-1 if g == "flap_front" else 50) for g in TG])
    sidx = np.array([int(g.split("_")[1]) if g.startswith("stick_") else -1 for g in TG])
    flap_owner = {-1: 0, 50: spec.n_sticks - 1}
    tpl = fs.tpl
    out = {}

    from mathutils import Matrix as _Mx

    def interp(Ma, Mb, u):
        qa = _Mx(Ma[:3, :3].tolist()).to_quaternion()
        qb = _Mx(Mb[:3, :3].tolist()).to_quaternion()
        if qa.dot(qb) < 0:
            qb.negate()
        q = qa.slerp(qb, u)
        M = np.eye(4)
        M[:3, :3] = np.array(q.to_matrix())
        M[:3, 3] = (1 - u) * Ma[:3, 3] + u * Mb[:3, 3]
        return M

    for name, (act, svals, fps) in acts.items():
        worst_crack, hits, rows = 0.0, 0, []
        for f in range(len(svals) - 1):
            Ta, Tb = fan_pose_T(spec, fs, svals[f]), fan_pose_T(spec, fs, svals[f + 1])
            # bones interpolate about their own rest pose: T_bone = M_rest^-1 -> basis; interpolating the
            # armature-space T of a bone whose head is fixed is the same slerp; T maps bind -> posed about the
            # armature origin, so convert to the bone's head frame first
            Tm = {}
            # as Unreal: each bone's LOCAL transform (relative to its parent) is interpolated, then composed
            for bn in Ta:
                if bn.startswith("leaf_"):
                    continue
                head = _bone_head(spec, fs, bn)
                H = np.eye(4)
                H[:3, 3] = head
                Hi = np.linalg.inv(H)
                Tm[bn] = H @ interp(Hi @ Ta[bn] @ H, Hi @ Tb[bn] @ H, 0.5) @ Hi
            for bn in Ta:
                if not bn.startswith("leaf_"):
                    continue
                j = int(bn.split("_")[1])
                par = f"stick_{j // 2 + (j % 2):02d}"
                head = _bone_head(spec, fs, bn)
                H = np.eye(4)
                H[:3, 3] = head
                Hi = np.linalg.inv(H)
                ra = np.linalg.inv(Ta[par]) @ Ta[bn]
                rb = np.linalg.inv(Tb[par]) @ Tb[bn]
                Tm[bn] = Tm[par] @ H @ interp(Hi @ ra @ H, Hi @ rb @ H, 0.5) @ Hi
            faces = [Tm[f"leaf_{j:02d}"] for j in range(50)]
            c = fs.cracks(0.5 * (svals[f] + svals[f + 1]), faces)
            # the line_T used by cracks() is exact at the interpolated openness; the sticks' own slerp about
            # Z is exact too, so this measures only the faces' interpolation
            Q = G.skin(mb, Tm, FF.apply)
            tri = Q[T]
            n_ll, _ = FF.count_intersections(tri[L_idx], tri[L_idx], same=True,
                                             exclude=lambda a, b: np.abs(lfi[L_idx][a] - lfi[L_idx][b]) <= 1)
            n_ls, _ = FF.count_intersections(tri[L_idx], tri[S_idx],
                                             exclude=lambda a, b: np.array([flap_owner.get(int(v), -5) for v in lfi[L_idx][a]]) == sidx[S_idx][b])
            worst_crack = max(worst_crack, c["worst_mm"])
            hits += n_ll + n_ls
            rows.append({"between_frames": [f, f + 1], "crack_mm": round(c["worst_mm"], 5), "hits": n_ll + n_ls})
        out[name] = {"half_keys": len(rows), "worst_crack_mm": round(worst_crack, 5), "intersections": hits,
                     "worst_rows": sorted(rows, key=lambda r: -r["crack_mm"])[:5]}
    return out


def _bone_head(spec, fs, bn):
    if bn == "pivot":
        return np.zeros(3)
    kind, idx = bn.split("_")
    i = int(idx)
    if kind == "stick":
        z0, z1 = spec.stick_z(i)
        return np.array([0.0, 0.0, 0.5 * (z0 + z1)])
    k = i // 2 + (i % 2)
    return np.array([0.0, 0.0, fs.tpl.z[k]])


# =========================================================================== sockets / physics
def sockets_and_bodies(spec, fs, fan_mb):
    zt = 0.5 * spec.stack_mm
    z00 = 0.5 * sum(spec.stick_z(0))
    grip_x = -spec.butt_mm + 40.0
    rx = lambda deg: np.array([[1, 0, 0], [0, math.cos(deg * D2R), -math.sin(deg * D2R)], [0, math.sin(deg * D2R), math.cos(deg * D2R)]])
    a12 = spec.stick_axis_deg(12, 1.0) * D2R
    Rz12 = np.array([[math.cos(a12), -math.sin(a12), 0], [math.sin(a12), math.cos(a12), 0], [0, 0, 1.0]])
    sockets = [
        {"name": "Grip", "bone": "stick_00", "location_mm": [grip_x, 0.0, z00], "matrix": np.eye(3).tolist(),
         "use": "hand attach: on the held (front) guard 40 mm above the butt, +X along the guard, +Z out of the front "
                "(ESTIMATE, FS 5.9)"},
        {"name": "Pivot", "bone": "pivot", "location_mm": [0.0, 0.0, 0.0], "matrix": np.eye(3).tolist(),
         "use": "the rivet axis (+Z): spin and aim reference"},
        {"name": "Tassel", "bone": "pivot", "location_mm": [0.0, 0.0, -zt - spec.rivet_proud], "matrix": rx(-90.0).tolist(),
         "use": "SK_Fan_Tassel attaches here (the back eyelet); the tassel's -Z (its hang) points along the fan's -Y "
                "(down when the open fan is held upright); simulate it to hang under gravity"},
        {"name": "Tip", "bone": "stick_12", "location_mm": [spec.L * math.cos(a12), spec.L * math.sin(a12),
                                                            0.5 * sum(spec.stick_z(12))], "matrix": Rz12.tolist(),
         "use": "the leaf edge at mid-fan: trails, gusts"},
    ]
    for s in sockets:
        s["unreal_component"] = SKP.ue_component_transform(np.array(s["matrix"]), s["location_mm"])

    head = 2 * spec.rivet_proud + spec.stack_mm + 1.0
    handle_c = np.array([0.5 * (spec.L - spec.butt_mm), 1.0, 0.0])
    handle_size = np.array([spec.L + spec.butt_mm + 2.0, 14.0, head])
    # the bounds envelope: the AABB of LOD0 posed at every sampled openness (the pleats leave the stack plane
    # part-way open, so the bind pose alone is not enough) and the handle box
    lo = handle_c - 0.5 * handle_size
    hi = handle_c + 0.5 * handle_size
    for s_ in np.linspace(0.0, 1.0, 41):
        Q = posed_vertices(spec, fs, fan_mb, float(s_))
        lo, hi = np.minimum(lo, Q.min(0)), np.maximum(hi, Q.max(0))
    lo, hi = lo - 1.0, hi + 1.0
    # round 3: the mesh's OWN bounds extension (Unreal positive/negative_bounds_extension, cm, Unreal axes), so the
    # bounds hold the folding leaf even if a buyer regenerates or swaps the physics asset: bind AABB of LOD0 vs the
    # posed envelope above (the leaf swings up to ~16 mm behind the rivet plane while it opens and closes)
    Pb, _, _ = fan_mb.arrays()
    blo, bhi = Pb.min(0), Pb.max(0)
    ext_pos_mm = np.maximum(hi - bhi, 0.0)
    ext_neg_mm = np.maximum(blo - lo, 0.0)
    # Unreal axes: x = x, y = -y (FBX Forward -Y), z = z; so +y and -y swap
    bounds_ext = {"positive_cm": [round(float(ext_pos_mm[0]) * 0.1, 3), round(float(ext_neg_mm[1]) * 0.1, 3),
                                  round(float(ext_pos_mm[2]) * 0.1, 3)],
                  "negative_cm": [round(float(ext_neg_mm[0]) * 0.1, 3), round(float(ext_pos_mm[1]) * 0.1, 3),
                                  round(float(ext_neg_mm[2]) * 0.1, 3)],
                  "why": "posed LOD0 at 41 openings (plus 1 mm) minus the bind AABB, per axis: set on the mesh as "
                         "Positive/Negative Bounds Extension so its bounds never depend on the physics asset"}
    elements = [
        {"shape": "box", "centre_mm": handle_c.tolist(), "matrix": np.eye(3).tolist(), "size_mm": handle_size.tolist(),
         "collision": True, "contribute_to_mass": True,
         "role": "the closed fan's handle / head: the one colliding shape"},
        {"shape": "box", "centre_mm": (0.5 * (lo + hi)).tolist(), "matrix": np.eye(3).tolist(), "size_mm": (hi - lo).tolist(),
         "collision": False, "contribute_to_mass": False,
         "role": "bounds envelope (no collision, no mass): the open fan's extent, so the mesh bounds hold the leaf "
                 "at every openness"},
    ]
    for e in elements:
        e["unreal_component"] = SKP.ue_component_transform(np.array(e["matrix"]), e["centre_mm"])
        e["size_cm"] = [round(v * 0.1, 4) for v in e["size_mm"]]
    bodies = [{"bone": "pivot", "unreal_bone_any_of": ["pivot"], "physics_type": "Default",
               "consider_for_bounds": True, "mass_kg": spec.mass_g / 1000.0, "elements": elements,
               "role": "ONE rigid body for a held prop, on 'pivot' (the rivet; round 3: every stick is a child of "
                       "'pivot', and every leaf face a child of its stick, so the body carries the whole fan when the "
                       "component simulates). The game makes it Kinematic while held and simulates it when dropped. Only "
                       "the handle box collides: the OPEN leaf has no collision (drop the fan closed, or add bodies)"}]
    return sockets, bodies, bounds_ext


def tassel_bodies(spec):
    """tassel_root: a small Kinematic anchor (it follows the Tassel socket); below it one capsule per chain bone,
    simulated, the builder's constraints joining each to its parent."""
    out = [{"bone": "tassel_root", "physics_type": "Kinematic", "consider_for_bounds": True, "mass_kg": 0.001,
            "elements": [{"shape": "sphere", "centre_mm": [0.0, 0.0, 0.0], "radius_mm": 1.5, "collision": False,
                          "contribute_to_mass": True}],
            "role": "anchor at the fan's eyelet"}]
    for name, h, t, p in TS.bone_table(spec):
        if name == "tassel_root":
            continue
        r = 0.5 * (spec.tassel.cord_d_L * spec.L) + 0.5 if name.startswith("cord") else (
            4.5 if name == "knot" else 6.0)
        top, bot = h[2], t[2]
        if name == "cord_01":
            # round 3: attached at the Tassel socket, the fan's handle box reaches 6.0 mm down the tassel's axis (Unreal
            # measured cord_01's cap inside it): the capsule's top cap now starts TASSEL_CLEAR_MM below the eyelet
            top = min(top, -TASSEL_CLEAR_MM)
        length = abs(bot - top)
        e = {"shape": "capsule", "centre_mm": [0.0, 0.0, 0.5 * (top + bot)], "matrix": np.eye(3).tolist(),
             "radius_mm": round(r, 3), "length_mm": round(max(0.1, length - 2 * r), 3), "axis": "Z",
             "collision": True, "contribute_to_mass": True}
        out.append({"bone": name, "physics_type": "Default", "consider_for_bounds": True,
                    "mass_kg": round(spec.tassel_mass_g / 1000.0 / 5, 6), "elements": [e]})
    for b in out:
        for e in b["elements"]:
            e["unreal_component"] = SKP.ue_component_transform(np.eye(3), e["centre_mm"])
    return out


BONE_COMPRESSION = "/Engine/Animation/DefaultRecorderBoneCompression"
#: round 3: intended playback per clip (the sidecar and the pack import set the AnimSequence Loop flag from this)
ANIM_PLAYBACK = {
    "A_Fan_OpenClose": {"loop": True, "playback": "a full flick open, 0.3 s hold, close (1.3 s). Loop-safe (its first and "
                                                   "last poses are identical); play it once as a montage for a gesture"},
    "A_Fan_Openness": {"loop": False, "playback": "NOT for playing: closed (0 s) to fully open (1.0 s), linear in the "
                                                   "opening angle; drive it by explicit time (Sequence Evaluator, "
                                                   "time = openness 0..1) for gameplay-controlled opening"},
    "A_Fan_OpenPose": {"loop": True, "playback": "the static open pose (two identical frames); loop or hold it"},
}
PROXY_BOX_MM = 250.0
#: the fan's handle box reaches 6.0 mm (0.60 cm) along the tassel's hang from the Tassel socket; 2 mm margin
TASSEL_CLEAR_MM = 8.0


def export_physics_proxy(arm, bone_names, bodies, material, name) -> dict:
    """<name>.fbx: the armature with one 250 mm cube per physics body, weighted to that body's bone.

    Unreal's physics-asset builder (FBX import, Create Physics Asset) makes one body per bone that carries
    vertices and merges a bone whose vertices span less than its 20 cm Min Bone Size into its parent; the 250 mm
    cubes make it build exactly one body on each body bone (and the constraints between them).  The Unreal
    import script then replaces each body's shapes with the build's elements and sets its type, bounds flag,
    collision and mass, and assigns the asset to the real mesh.  A build artefact in WorkFiles, not a shipped
    mesh (MEASURED UE 5.8.3: with a proxy sized like the real handle the one body came out on 'root')."""
    mb = G.FanMesh(list(bone_names))
    h = 0.5 * PROXY_BOX_MM
    for bd in bodies:
        c = np.array(bd["elements"][0]["centre_mm"], np.float64)
        corners = np.array([[sx * h, sy * h, sz * h] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]) + c
        for q in [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]:
            P = corners[list(q)]
            n = np.cross(P[1] - P[0], P[2] - P[0])
            n /= np.linalg.norm(n)
            if n @ (P.mean(0) - c) < 0:
                n = -n
            for tri in ((0, 1, 2), (0, 2, 3)):
                mb.tri([P[k] for k in tri], [(0.1, 0.1), (0.9, 0.1), (0.9, 0.9)], [n] * 3, bd["bone"], 0, "proxy",
                       bd["bone"])
    ob = LK.mesh_object(mb, name, [material], arm)
    out = EXPORTS / "Physics"                     # round 3: shipped (was WorkFiles), so PHYS_* rebuild from Exports alone
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{name}.fbx"
    try:
        SKP.export_skeletal_set(str(out), arm, [ob], name, frame_rate=FPS_OPENCLOSE)
    finally:
        me = ob.data
        bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.meshes.remove(me)
    return {"fbx": str(path), "file": f"Physics/{name}.fbx", "sha256": sha256(path), "bodies": [bd["bone"] for bd in bodies]}


# =========================================================================== QA
def stage_qa(spec, arm, objs, tarm, tobjs, report):
    # every stick is a closed solid; so is the eyelet (per LOD)
    closed = {o.name: _closed_groups(o) for o in objs}
    # round 3: 2 influences on the prong vertices only (stick i and stick i+1), 1 everywhere else
    res = SKP.qa_skeletal(objs, arm, max_influences=2, bone_budget=128, closed_groups=closed, max_slots=3)
    # the tassel's armature carries the name 'root' in its own files: check it under that name
    arm.name = "root_fan"
    tarm.name = "root"
    try:
        tres = SKP.qa_skeletal(tobjs, tarm, max_influences=2, bone_budget=16, max_slots=1)
    finally:
        tarm.name = "root_tassel"
        arm.name = "root"
    report["qa"] = {"fan": _summ(res), "tassel": _summ(tres)}
    for r, nm in ((res, "fan"), (tres, "tassel")):
        bad = [c for c in r["checks"] if not c["passed"]]
        for c in bad:
            log(f"  QA FAIL ({nm}) {c['name']} on {c['object']}: {c['detail']}")
        log(f"qa_skeletal {nm}: {'PASS' if r['passed'] else 'FAIL'} ({len(r['checks']) - len(bad)}/{len(r['checks'])})")


def _closed_groups(obj):
    """Face sets that must each be a closed solid: every stick (its plate, spacer and leaf-zone prong; a prong's
    vertices also carry the next stick, so a face belongs to the LOWEST stick its vertices use), the eyelet."""
    me = obj.data
    names = {g.index: g.name for g in obj.vertex_groups}
    vgs = {v.index: [names[g.group] for g in v.groups if g.weight > 0] for v in me.vertices}
    groups = {}
    for p in me.polygons:
        bones = sorted({b for vi in p.vertices for b in vgs.get(vi, [])})
        sticks = [b for b in bones if b.startswith("stick_")]
        if sticks and p.material_index == PART_SLOT["sticks"]:
            groups.setdefault(sticks[0], []).append(p.index)
        elif bones == ["pivot"]:
            groups.setdefault("eyelet", []).append(p.index)
    return groups


def _summ(r):
    return {"passed": r["passed"], "n_checks": len(r["checks"]),
            "failed": [{"name": c["name"], "object": c["object"], "detail": c["detail"]} for c in r["checks"] if not c["passed"]],
            "checks": r["checks"]}


# =========================================================================== export
def stage_export(spec, arm, objs, tarm, tobjs, acts, maps, report, lod_sizes, sockets, bodies):
    EXPORTS.mkdir(parents=True, exist_ok=True)
    written = SKP.export_skeletal_set(str(EXPORTS), arm, objs, spec.mesh_name,
                                      actions=[acts[k][0] for k in ("A_Fan_OpenClose", "A_Fan_Openness", "A_Fan_OpenPose")],
                                      frame_rate=FPS_OPENCLOSE, fps_by_action={k: v[2] for k, v in acts.items()})
    arm.animation_data.action = None
    LK.pose(arm, {})
    # the tassel: its armature carries the name 'root' in its own files
    arm.name = "root_fan"
    tarm.name = "root"
    try:
        twritten = SKP.export_skeletal_set(str(EXPORTS), tarm, tobjs, spec.tassel_name, actions=[])
    finally:
        tarm.name = "root_tassel"
        arm.name = "root"
    tex = report.get("textures") or {}
    mats = {}
    for k, slot in (("leaf", 0), ("sticks", 1), ("rivet", 2)):
        stem = spec.texture_stems[k]
        m = maps[k]
        mats[spec.materials[k]] = {
            "slot": slot, "part": k, "master": "M_Steel_Master" if k == "rivet" else "M_Fabric_Master",
            "textures": {kk: f"{stem}_{kk}" for kk in (("BC", "ORM", "N") if k == "rivet" else ("BC", "ORM", "N", "Detail"))},
            "tint_default_linear": None if k == "rivet" else [round(float(x), 6) for x in m["tint_linear"]],
            "tint_is": None if k == "rivet" else "the part's MEAN colour: edit Colour to recolour",
            "detail_bias_default": m.get("detail_bias"), "detail_scale_default": m.get("detail_scale"),
            "specular_scale": SPEC_SCALE.get(k), "metal": k == "rivet"}
    payload = {
        "asset": spec.mesh_name, "skeleton": spec.skeleton_name,
        "bones": report["skeleton"]["bones"], "root_bone": "root",
        "lod_files": [Path(w["fbx"]).name for w in written["meshes"]],
        "lod_screen_sizes": lod_sizes,
        "lod_note": "import LOD1/LOD2 with SkeletalMeshEditorSubsystem.import_lod (same skeleton, same root); every "
                    "fold is kept at every LOD, so NO Bones to Remove",
        "animations": [{"file": Path(a["fbx"]).name, "frames": a["frames"], "fps": a["fps"],
                        **ANIM_PLAYBACK[Path(a["fbx"]).stem]} for a in written["animations"]],
        "import": {"use_t0_as_ref_pose": False, "update_skeleton_reference_pose": False, "import_morph_targets": False,
                   "create_physics_asset": False, "normals": "import normals", "convert_scene": True,
                   "force_front_x_axis": False, "custom_sample_rate": "the file's rate (60 fps)",
                   "bone_compression": BONE_COMPRESSION,
                   "bone_compression_why": "REQUIRED on all three A_Fan_* clips. Unreal's project default (ACL) moves "
                                           "the leaf's face bones by up to 0.64 mm and opens the pleat folds by up to "
                                           "1.1 mm (visible cracks and see-through dots along every fold); "
                                           "DefaultRecorderBoneCompression keeps them within 0.08 mm (MEASURED, UE "
                                           "5.8.3). Re-compressing the clips with the project default will crack the "
                                           "leaf. Alternative: a custom ACL setting with an error threshold of "
                                           "0.001 cm and a virtual-vertex distance of at least 20 cm",
                   "bounds_extension_cm": report["bounds_extension"],
                   "loop_flags": {k: v["loop"] for k, v in ANIM_PLAYBACK.items()}},
        "physics_proxies": {"SK_Fan": report["physics_proxy"]["file"], "SK_Fan_Tassel": report["tassel_physics_proxy"]["file"],
                            "how": "import each proxy FBX onto the real mesh's skeleton with Create Physics Asset ON: "
                                   "the builder makes exactly the listed bodies (one 250 mm cube per body bone); then "
                                   "rewrite each body from physics_bodies (shapes, collision, mass, type), rename it "
                                   "PHYS_Fan / PHYS_Fan_Tassel, assign it to the real mesh and delete the proxy mesh "
                                   "(Scripts/unreal/materials/np_skeletal.py does exactly this)"},
        "sockets": sockets, "physics_bodies": bodies,
        "materials": mats,
        "materials_note": "Pack instances (Scripts/unreal/materials): MI_Fan_Leaf and MI_Fan_Ribs on M_Fabric_Master, "
                          "BaseColor = saturate(Colour x (DetailBias + DetailScale x Detail16)), Colour = the part's "
                          "MEAN colour (default = the reference colour); MI_Fan_Rivet on M_Steel_Master, not tintable. "
                          "The slot 'M_Fan_Sticks' holds all 26 sticks (both guards and the 24 ribs): its instance is "
                          "MI_Fan_Ribs. Both masters carry 'Used with Skeletal Mesh'.",
        "bounds_note": "the mesh's own Positive/Negative Bounds Extension (import.bounds_extension_cm) holds the "
                       "folding leaf; the physics body's second box (no collision, no mass) is the same envelope",
        "physics_note": "Unreal's builder cannot be told which bodies to make and the body list is not exposed to "
                        "Python: PHYS_Fan is built from Physics/SK_Fan_PhysicsProxy.fbx (one body, on 'pivot') and "
                        "that body is rewritten from these elements (physics_proxies.how)",
        "mass_kg": spec.mass_g / 1000.0,
        "fold_check": fold_check_data(spec, report["_fs"]),
        "bones_rest": {b.name: {"head_cm": SKP.ue_component_transform(np.eye(3), [v * 1000.0 for v in b.head_local])["location_cm"],
                                "parent": b.parent.name if b.parent else "root"} for b in arm.data.bones},
    }
    sc = SKP.write_skeletal_sidecar(str(EXPORTS / f"{spec.mesh_name}.fbx"), payload)
    tpay = {"asset": spec.tassel_name, "skeleton": f"{spec.tassel_name}_Skeleton", "bones": list(TS.BONES),
            "physics_proxy": report["tassel_physics_proxy"]["file"],
            "root_bone": "root", "lod_files": [Path(w["fbx"]).name for w in twritten["meshes"]],
            "lod_screen_sizes": report.get("tassel_lod_screen_sizes"),
            "attach": {"to": spec.mesh_name, "socket": "Tassel"},
            "physics_bodies": tassel_bodies(spec),
            "simulation": "AnimDynamics chain (Bound Bone tassel_root, Chain End skirt_02) or a Rigid Body node on "
                          "this physics asset; it must hang under gravity. Either runs in the tassel's own anim graph and "
                          "never collides with the fan. If you simulate the tassel as COMPONENT physics instead, make it "
                          "ignore its parent fan (Ignore Component/Actor when moving, or a collision channel the fan's "
                          "body ignores); cord_01's capsule starts 8 mm below the eyelet, clear of the fan's handle box",
            "rivet_overlap": "the first 3 mm of the cord pass through the fan's back eyelet head: that is the cord threaded "
                             "through the eyelet (as fan2), intended",
            "materials": {spec.materials["tassel"]: {"slot": 0, "master": "M_Fabric_Master",
                                                     "textures": {kk: f"{spec.texture_stems['tassel']}_{kk}" for kk in ("BC", "ORM", "N", "Detail")},
                                                     "tint_default_linear": [round(float(x), 6) for x in maps["tassel"]["tint_linear"]],
                                                     "detail_bias_default": maps["tassel"]["detail_bias"],
                                                     "detail_scale_default": maps["tassel"]["detail_scale"],
                                                     "specular_scale": SPEC_SCALE["tassel"]}},
            "mass_kg": spec.tassel_mass_g / 1000.0}
    tsc = SKP.write_skeletal_sidecar(str(EXPORTS / f"{spec.tassel_name}.fbx"), tpay)
    files = [w["fbx"] for w in written["meshes"]] + [a["fbx"] for a in written["animations"]] + \
            [w["fbx"] for w in twritten["meshes"]] + [sc, tsc] +             [report["physics_proxy"]["fbx"], report["tassel_physics_proxy"]["fbx"]]
    report["export"] = {"files": {Path(f).name: {"sha256": sha256(f), "bytes": Path(f).stat().st_size} for f in files},
                        "written": written, "tassel": twritten, "sidecar": str(Path(sc).relative_to(PROJECT)),
                        "tassel_sidecar": str(Path(tsc).relative_to(PROJECT))}
    log(f"exported {len(files)} files")


def fold_check_data(spec, fs) -> dict:
    """What the Unreal verifier needs to measure the fold from the engine's own bone poses: every leaf face bone's
    four fold corners at bind (Unreal component space, cm) and which corners are copies of one vertex."""
    t = fs.tpl
    n = spec.n_sticks
    ue = lambda p: SKP.ue_component_transform(np.eye(3), p)["location_cm"]
    faces = {}
    for j in range(2 * (n - 1)):
        i = j // 2
        if j % 2 == 0:
            corners = [t.rib_pts[i, 0], t.rib_pts[i, 1], t.mid_pts[i, 0], t.mid_pts[i, 1]]
        else:
            corners = [t.mid_pts[i, 0], t.mid_pts[i, 1], t.rib_pts[i + 1, 0], t.rib_pts[i + 1, 1]]
        faces[f"leaf_{j:02d}"] = [ue(c) for c in corners]
    pairs = []
    for i in range(n - 1):
        pairs += [[f"leaf_{2 * i:02d}", 2, f"leaf_{2 * i + 1:02d}", 0], [f"leaf_{2 * i:02d}", 3, f"leaf_{2 * i + 1:02d}", 1]]
    for k in range(1, n - 1):
        pairs += [[f"leaf_{2 * k - 1:02d}", 2, f"leaf_{2 * k:02d}", 0], [f"leaf_{2 * k - 1:02d}", 3, f"leaf_{2 * k:02d}", 1]]
    return {"faces": faces, "pairs": pairs, "gate_cm": 0.01,
            "note": "corners: [inner, outer] of the face's first fold line then of its second; a pair is one leaf vertex "
                    "carried by two face bones (the crack between its copies)"}


# =========================================================================== measure
def stage_measure(spec, fs, arm, objs, tobjs, report):
    lods = {}
    for i, o in enumerate(objs):
        me = o.data
        co = np.array([v.co[:] for v in me.vertices]) * 1000.0
        band = spec.lod_bands[i]
        ntri = len(me.polygons)
        lods[f"LOD{i}"] = {"object": o.name, "triangles": ntri, "vertices": len(me.vertices), "band": list(band),
                           "in_band": bool(band[0] <= ntri <= band[1]),
                           "bounds_mm": {"min": np.round(co.min(0), 3).tolist(), "max": np.round(co.max(0), 3).tolist()}}
    co = np.array([v.co[:] for v in objs[0].data.vertices]) * 1000.0
    c = 0.5 * (co.min(0) + co.max(0))
    radius = float(np.linalg.norm(co - c, axis=1).max())
    report["lods"] = lods
    report["lod_triangles"] = [lods[f"LOD{i}"]["triangles"] for i in range(3)]
    report["bounds_radius_mm"] = round(radius, 3)
    report["lod_screen_sizes"] = spec.lod_screen_sizes(radius)
    report["switch_distances_m"] = spec.switch_distances_m(radius)
    tl = {}
    for i, o in enumerate(tobjs):
        band = spec.tassel_lod_bands[i]
        n = len(o.data.polygons)
        tl[f"LOD{i}"] = {"object": o.name, "triangles": n, "band": list(band), "in_band": bool(band[0] <= n <= band[1])}
    tco = np.array([v.co[:] for v in tobjs[0].data.vertices]) * 1000.0
    tr = float(np.linalg.norm(tco - 0.5 * (tco.min(0) + tco.max(0)), axis=1).max())
    report["tassel_lods"] = tl
    report["tassel_lod_screen_sizes"] = spec.lod_screen_sizes(tr)
    report["size_open_mm"] = np.round(co.max(0) - co.min(0), 2).tolist()
    spec_caption["open_mm"] = float(co.max(0)[0] - co.min(0)[0])
    # UV0 overlaps per texture (the leaf's back layer shares the front's UVs by design: front layers only)
    from pipeline.qa_check import uv_overlap_sat
    mb0 = report["_fan_mb"]
    ov = {}
    for part, slot in (("leaf", 0), ("sticks", 1), ("rivet", 2)):
        idx = [t for t in range(len(mb0.T)) if mb0.TS[t] == slot and mb0.TLAY[t] != "back"]
        ov[part] = int(uv_overlap_sat(np.array([mb0.TUV[t] for t in idx])))
    ov["tassel"] = int(uv_overlap_sat(np.array(report["_tas_mb"].TUV)))
    P0, T0, _ = mb0.arrays()
    a3 = 0.5 * np.linalg.norm(np.cross(P0[T0[:, 1]] - P0[T0[:, 0]], P0[T0[:, 2]] - P0[T0[:, 0]]), axis=1)
    report["uv_overlaps"] = ov
    report["min_triangle_area_mm2_lod0"] = round(float(a3.min()), 6)
    # the closed fan, from the numpy mechanism (the shipped skin is verified again in verify_fan.py)
    Tb = fan_pose_T(spec, fs, 0.0)
    P, T, B = fs_mesh_positions(spec, fs, report["_fan_mb"], Tb)
    report["size_closed_mm"] = np.round(P.max(0) - P.min(0), 2).tolist()
    # leaf and stick geometry facts
    report["measured"] = {
        "opening_guard_axes_deg": spec.opening_at(1.0), "stick_pitch_deg": round(spec.stick_pitch_deg, 4),
        "leaf_pitch_deg": round(spec.leaf_pitch_deg, 4), "leaf_radii_mm": [round(spec.r_in, 3), round(spec.r_out, 3)],
        "leaf_visible_inner_mm": round(spec.r_in + spec.prong_reach_mm, 3),
        "leaf_visible_inner_L": round((spec.r_in + spec.prong_reach_mm) / spec.L, 5),
        "rib_tip_mm": round(spec.r_in - spec.rib_end_gap_mm, 3),
        "rib_tip_L": round((spec.r_in - spec.rib_end_gap_mm) / spec.L, 5),
        "closed_length_mm": round(spec.L + spec.butt_mm, 3), "stack_mm": round(spec.stack_mm, 3),
        "pleat_depth_open_mm": _pleat_depth(fs), "scallop_p2p_mm": _scallop(fs, spec),
        "rib_width_at_leaf_mm": round(spec.rib_width_mm(spec.r_in), 3), "guard_width_mm": {
            f"{x:.2f}L": round(spec.guard_width_mm(x * spec.L), 3) for x in (0.23, 0.525, 0.76, 0.93)}}


def fs_mesh_positions(spec, fs, mb, Tb):
    P, T, B = mb.arrays()
    return G.skin(mb, Tb, FF.apply), T, B


def _pleat_depth(fs):
    t = fs.tpl
    i = 12
    mid = t.mid_pts[i]
    rz = 0.5 * (t.rib_pts[i][:, 2] + t.rib_pts[i + 1][:, 2])
    return {"at_leaf_edge_mm": round(float(mid[1, 2] - rz[1]), 3), "at_leaf_base_mm": round(float(mid[0, 2] - rz[0]), 3)}


def _scallop(fs, spec):
    """the leaf edge's in-plane scallop, peak to trough (round 2: fan_geom's, not the fold template's)"""
    return round(spec.scallop_L * spec.L, 3)


# =========================================================================== gates
def collect_gates(report) -> dict:
    g = {}
    fp = report.get("fold_proof") or {}
    g["G1_leaf_cracks_under_0.1mm_all_angles"] = bool(fp) and fp["worst"]["crack_mm"] <= 0.1
    g["G2_no_intersections_all_angles"] = bool(fp) and fp["worst"]["hits"] == 0
    g["G2b_neighbouring_faces_never_cross_at_bind"] = bool(fp) and fp["worst"]["adjacent_crossings_at_bind"] == 0
    hk = report.get("half_keys") or {}
    g["G1b_half_keys_cracks_under_0.1mm_no_hits"] = bool(hk) and all(v["worst_crack_mm"] <= 0.1 and v["intersections"] == 0
                                                                       for v in hk.values())
    g["G3_leaf_never_under_front_guard"] = bool(fp) and all(r["hits"]["leaf_sticks"] == 0 for r in fp["rows"])
    g["G3b_closed_leaf_within_stack"] = bool(fp) and fp["closed"]["leaf_beyond_stack_faces_mm"] <= 0.05
    st = report.get("seethrough") or {}
    # round 3: no daylight straight through (front or back) at any LOD or opening, and none from the rim at 45 deg when
    # open 120 deg or more; the remaining oblique counts are reported (FAN_REPORT: known gap)
    g["G5_no_seethrough_front_back_any_lod_any_opening"] = bool(st) and st["front_back_all_lods_all_openings"] == 0
    g["G5c_no_seethrough_reference_camera_band_all_lods"] = bool(st) and all(
        v["see_through_rays"] == 0 for v in (st.get("reference_camera") or {"x": {"see_through_rays": 1}}).values())
    g["G5b_no_seethrough_rim45_open_120_plus"] = bool(st) and all(v == 0 for k, v in st["rim45_LOD0_by_opening"].items()
                                                                     if float(k) >= 120.0)
    qa = report.get("qa") or {}
    g["G4_qa_skeletal_fan"] = bool((qa.get("fan") or {}).get("passed"))
    g["G4_qa_skeletal_tassel"] = bool((qa.get("tassel") or {}).get("passed"))
    lods = report.get("lods") or {}
    g["lod_triangles_in_band"] = bool(lods) and all(v["in_band"] for v in lods.values())
    tr = report.get("lod_triangles", [0, 0, 0])
    g["lod_triangles_descend"] = tr[0] > tr[1] > tr[2]
    tl = report.get("tassel_lods") or {}
    g["tassel_lods_in_band"] = bool(tl) and all(v["in_band"] for v in tl.values())
    tex = report.get("textures") or {}
    g["maps_power_of_two_no_colour_chunks"] = bool(tex.get("power_of_two")) and not any(
        c for d in (tex.get("colour_chunks") or {}).values() for c in d.values())
    ok = bool(tex.get("recolour"))
    for k, rc in (tex.get("recolour") or {}).items():
        mm = rc["detail_min_max_code"]
        ok = ok and rc["detail_levels_used"] >= 64 and mm[0] == 0 and mm[1] == 255 and \
            abs(rc["mean_of_bias_plus_scale_x_detail"] - 1.0) <= 0.002 and rc["max_abs_err_linear"] <= 0.0035
    g["recolour_detail_full_range_tint_is_mean"] = ok
    g["mip_parity_within_1pct_or_half_level"] = bool(tex) and all(
        v["max_abs_pct"] <= 1.0 or v.get("max_level_diff", 9) <= 0.5 for v in tex["mip_parity"].values())
    g["tint_equals_reference_colour"] = bool(tex) and all(v["max_abs_diff"] <= 0.0015 for v in tex["tint_vs_reference_colour"].values())
    rec = report.get("recolour") or {}
    g["detail16_lossless"] = bool(rec) and all(rec["lossless"].values())
    g["uv0_no_overlaps"] = bool(report.get("uv_overlaps")) and not any(report["uv_overlaps"].values())
    g["min_triangle_area_ge_0.001mm2"] = report.get("min_triangle_area_mm2_lod0", 0) >= 0.001
    g["frozen_assets_unchanged"] = bool((report.get("frozen") or {}).get("unchanged"))
    names = [report.get("asset"), *(report.get("skeleton") or {}).get("bones", [])]
    g["no_franchise_string"] = not deny_hits(*[n for n in names if n])
    rv = report.get("rivet_projection") or {}
    g["reference_camera_rivet_within_1.5px"] = bool(rv) and rv["error_px"] <= 1.5
    fid = report.get("fidelity") or {}
    if fid:
        g["F_mask_iou_ge_0.95"] = fid["mask_iou"] >= 0.95
        # RS 7: the outer radius is 1.000 L +- 0.01 L = +- 3.4 px in fan2's frame
        g["F_boundary_mean_le_2.5px"] = max(fid["boundary_px"]["mean_ref_to_render"], fid["boundary_px"]["mean_render_to_ref"]) <= 2.5
    g["_all"] = all(v for k, v in g.items() if not k.startswith("_"))
    return g


# =========================================================================== main
def parse_args(argv):
    p = argparse.ArgumentParser()
    p.add_argument("--quick", action="store_true")
    p.add_argument("--no-render", action="store_true")
    p.add_argument("--dev-dir", default=None)
    p.add_argument("--report-name", default="fan_report.json")
    return p.parse_args(argv)


def main(argv=None):
    global ASSETS, EXPORTS, TEXTURES, RECOLOUR, RENDERS, WORK, BUILD_WORK
    argv = argv if argv is not None else (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    args = parse_args(argv)
    if args.dev_dir:
        dev = Path(args.dev_dir) if Path(args.dev_dir).is_absolute() else PROJECT / args.dev_dir
        ASSETS, EXPORTS, RENDERS, WORK = dev / "Assets", dev / "Exports" / "Fan", dev / "Renders" / "Fan", dev
        TEXTURES, BUILD_WORK = EXPORTS / "Textures", dev / "build"
        RECOLOUR = TEXTURES / "Recolour"
    elif args.quick or args.no_render:
        raise SystemExit("--quick / --no-render are DEV flags: use them with --dev-dir")
    spec = FAN
    for d in (ASSETS, EXPORTS, TEXTURES, RECOLOUR, RENDERS, WORK, BUILD_WORK):
        d.mkdir(parents=True, exist_ok=True)
    report = {"asset": spec.mesh_name, "library": f"props_lib fan {LIB_VERSION}", "built": time.strftime("%Y-%m-%dT%H:%M:%S"),
              "blender": bpy.app.version_string, "build_script": str(Path(__file__).relative_to(PROJECT)),
              "quick": bool(args.quick), "build_to": build_to(spec), "frozen": {"before": frozen_hashes()}}
    LK.reset_scene()
    log("fold (props_lib.fan_fold)")
    fs = stage_fold(spec, report, args.quick)
    log("geometry (props_lib.fan_geom, fan_tassel)")
    fan, tas = stage_geometry(spec, fs, report)
    report["_fan_mb"] = fan[0]
    report["_tas_mb"] = tas[0]
    report["_fs"] = fs
    log("fold proof on the numpy mechanism (G1 - G3)")
    report["fold_proof"] = fold_proof_numpy(spec, fs, fan[0], openness_samples())
    report["closed_bundle"] = closed_bundle(spec, fs, fan[0])
    log("see-through proof round the leaf's inner edge (G5)")
    report["seethrough"] = seethrough_proof(spec, fs, fan)
    log(f"  front/back holes (all LODs, all openings): {report['seethrough']['front_back_all_lods_all_openings']}; "
        f"rim 45: {report['seethrough']['rim45_LOD0_by_opening']}; LOD0 total with/without prongs "
        f"{report['seethrough']['total_LOD0_with_vs_without']}")
    w = report["fold_proof"]["worst"]
    log(f"  worst crack {w['crack_mm']} mm, intersections {w['hits']}, min dihedrals {w['min_mid_dihedral_deg']:.2f} / "
        f"{w['min_rib_dihedral_deg']:.2f} deg")
    log("maps (props_lib.fan_paint)")
    chs, maps, paths, chroma = stage_textures(spec, fan, tas, report, args.quick)
    log("AO bake (Cycles, LOD0 open, leaf front layer)")
    maps, paths = stage_ao(spec, fan, tas, chs, maps, paths, chroma, report, args.quick)
    texture_report(spec, maps, paths, report)
    stage_recolour(spec, maps, paths, report)
    mats = make_materials(spec, maps, paths, pack=True)
    log("objects, skeleton, skin")
    arm, objs, tarm, tobjs = stage_objects(spec, fs, fan, tas, mats, report)
    log("actions")
    acts = stage_actions(spec, fs, arm, report)
    log("half-key proof (Unreal-style interpolation between keys)")
    report["half_keys"] = half_key_proof(spec, fs, fan[0], acts)
    log("  " + ", ".join(f"{k}: crack {v['worst_crack_mm']} hits {v['intersections']}" for k, v in report["half_keys"].items()))
    stage_measure(spec, fs, arm, objs, tobjs, report)
    sockets, bodies, bounds_ext = sockets_and_bodies(spec, fs, report["_fan_mb"])
    report["sockets"] = sockets
    report["physics_bodies"] = bodies
    report["bounds_extension"] = bounds_ext
    stage_qa(spec, arm, objs, tarm, tobjs, report)
    blend = ASSETS / "Fan.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    report["blend"] = str(blend.relative_to(PROJECT)) if blend.is_relative_to(PROJECT) else str(blend)
    report["blend_sha256"] = sha256(blend)
    log(f"saved {blend}")
    report["physics_proxy"] = export_physics_proxy(arm, [b.name for b in arm.data.bones], bodies, mats["leaf"],
                                                   "SK_Fan_PhysicsProxy")
    arm.name = "root_fan"
    tarm.name = "root"
    try:
        report["tassel_physics_proxy"] = export_physics_proxy(tarm, [b.name for b in tarm.data.bones],
                                                              tassel_bodies(spec), mats["tassel"],
                                                              "SK_Fan_Tassel_PhysicsProxy")
    finally:
        tarm.name = "root_tassel"
        arm.name = "root"
    stage_export(spec, arm, objs, tarm, tobjs, acts, maps, report, report["lod_screen_sizes"], sockets, bodies)
    report["rivet_projection"] = RV.rivet_check(spec)
    if not args.no_render:
        from props_lib import fan_gallery as GAL
        GAL.stage_render(spec, fs, arm, objs, tarm, tobjs, report, RENDERS, BUILD_WORK, REFERENCE, quick=args.quick,
                         log=log)
    report.pop("_fan_mb", None)
    report.pop("_tas_mb", None)
    report.pop("_fs", None)
    report.pop("_chs", None)
    report["frozen"]["after"] = frozen_hashes()
    report["frozen"]["unchanged"] = report["frozen"]["after"] == report["frozen"]["before"]
    report["gates"] = collect_gates(report)
    bad = [k for k, v in report["gates"].items() if not v and not k.startswith("_")]
    log("gates: " + ("ALL PASS" if not bad else "FAILING " + ", ".join(bad)))
    out = WORK / args.report_name
    out.write_text(json.dumps(report, indent=1, default=_json_default), encoding="utf-8")
    log(f"report -> {out}")
    return 0


def _json_default(o):
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    return str(o)


if __name__ == "__main__":
    sys.exit(main())
