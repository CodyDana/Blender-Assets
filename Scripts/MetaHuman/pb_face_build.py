"""pb_face_build.py -- build mode of pb_face_design.py (imported by it; not run on its own).

Recipe file (PB_FACE_RECIPES, json):
{
  "blend_start": 10,                       # coefficient index where preset blending starts (see probe notes)
  "candidates": {
    "MH_PlayerBase_FaceA": {"blend": {"Kelvin": 0.35, "Bo": 0.25}, "note": "..."},
    ...
  }
}
For every candidate: out = base + sum_i w_i * (preset_i - base) on coefficient indices >= blend_start; indices below
blend_start (the global header of the face model) are kept from MH_PlayerBase. Only the FACE state is changed
(set_face_model_coefficients + commit_face_state); the body state is never touched.

Each candidate is a fresh duplicate of /Game/Characters/MetaHumans/MH_PlayerBase (MH_PlayerBase itself is only read).
A candidate asset left by an earlier run of THIS script is deleted and re-made (names are lock-checked first).
"""
from __future__ import annotations

import json
import time
import traceback
from pathlib import Path

import unreal as ue

ORTHO_RES = 1200
ORTHO_WIDTH = 240.0
ORTHO_CAM_Z = 95.0


def layout(c):
    """Face-model coefficient layout found by the probe (UE 5.8.3):
    [num_regions=22] + per region [scale, qx, qy, qz, qw, tx, ty, tz (head-local cm, DNA space), n, n PCA values].
    Returns a list of (region_start_index, n)."""
    regions = int(round(c[0]))
    i = 1
    out = []
    for _ in range(regions):
        n = int(round(c[i + 8]))
        out.append((i, n))
        i += 9 + n
    if i != len(c):
        raise ValueError(f"unexpected coefficient layout: parsed {i} of {len(c)}")
    return out


# Region groups of the 22-region face model, named from each region's head-local rigid translation (DNA space:
# x lateral, y up, z forward; see faces/face_probe_report_1.json). Left/right regions come in mirrored pairs.
REGION_GROUPS = {
    "cranium": [0, 3],        # (0,155.1,2.9) top/forehead-crown, (0,149.3,-3.6) back of skull
    "forehead": [4],          # (0,154.3,7.4)
    "temples": [1, 2],        # (+-5.6,151.1,3.9)
    "brows": [5, 6],          # (+-3.0,151.0,8.8) brow ridge / upper lids
    "eyes": [7, 8],           # (+-3.2,149.4,9.0)
    "cheekbones": [9, 10],    # (+-4.6,147.4,7.7)
    "ears": [11, 12],         # (+-7.2,147.1,0.7) side of head / ears
    "nose": [13],             # (0,145.9,10.4)
    "cheeks": [14, 15],       # (+-4.2,143.1,7.4)
    "mouth": [16],            # (0,142.5,9.2)
    "chin": [17],             # (0,139.8,9.3)
    "jaw": [18, 20, 21],      # (0,138.3,6.2) under-chin, (+-4.0,140.4,5.4) jaw sides
    "neck": [19],             # (0,136.4,0.2) neck; identical translation for every preset (anchor to the body)
}


def blend(base, presets: dict, weights: dict, start: int = 1, regions: dict | None = None):
    """out = base + sum_i w_i * (preset_i - base) on every rigid + PCA value (the region count entries are equal
    for every character and stay untouched); region quaternions are re-normalised afterwards.
    `regions` = {group: {preset: weight}} overrides `weights` for the regions of that group (the MetaHuman Creator
    Blend tool's per-region blending, done on the coefficients)."""
    n = len(base)
    lay = layout(base)
    region_w = [dict(weights) for _ in lay]
    for group, gw in (regions or {}).items():
        for r in REGION_GROUPS[group]:
            region_w[r] = dict(gw)
    names = {p for w in region_w for p in w}
    for name in names:
        c = presets[name]
        if len(c) != n or layout(c) != lay:
            raise ValueError(f"coefficient layout mismatch for {name}")
    out = list(base)
    for r, (i0, cnt) in enumerate(lay):
        idx = list(range(max(i0, start), i0 + 8)) + list(range(i0 + 9, i0 + 9 + cnt))  # skip the count entry
        for name, w in region_w[r].items():
            c = presets[name]
            for i in idx:
                out[i] += float(w) * (c[i] - base[i])
        if not any(region_w[r].values()):
            continue
        q = out[i0 + 1:i0 + 5]
        norm = sum(x * x for x in q) ** 0.5
        if norm > 0:
            out[i0 + 1:i0 + 5] = [x / norm for x in q]
    return out


def apply_landmark_moves(M, ch, moves) -> list:
    """Parametric sculpt (the MetaHuman Creator 'Move' tool): each move = {"idx": [landmark indices],
    "d": [dx, dy, dz] cm, UE axes: x lateral, y forward, z up}. Applied with translate_face_landmarks after the
    coefficient blend. Landmark indices are MH_PlayerBase's 79 face landmarks (see faces/face_probe_report_1.json)."""
    if not moves:
        return []
    idx = ue.Array(int)
    deltas = ue.Array(ue.Vector)
    flat = []
    for mv in moves:
        for i in mv["idx"]:
            idx.append(int(i))
            deltas.append(ue.Vector(float(mv["d"][0]), float(mv["d"][1]), float(mv["d"][2])))
            flat.append([int(i)] + [float(x) for x in mv["d"]])
    M.mhs().translate_face_landmarks(ch, idx, deltas)
    return flat


def preset_share(weights: dict, regions: dict | None, n_regions: int = 22) -> dict:
    """Total preset influence per region and averaged over the 22 regions (PCA-size weighted is not used)."""
    region_w = [sum(weights.values())] * n_regions
    for group, gw in (regions or {}).items():
        for r in REGION_GROUPS[group]:
            region_w[r] = sum(gw.values())
    return {"per_region": [round(x, 3) for x in region_w], "mean": round(sum(region_w) / n_regions, 3)}


def explore_job(scene, M):
    """Scratch-only preview: every variant is applied to an in-memory duplicate of MH_PlayerBase (never saved)
    and captured with the builder's face cameras."""
    variants = json.loads(Path(M.RECIPES).read_text(encoding="utf-8"))["variants"]
    need = sorted({p for v in variants for p in list(v.get("blend", {})) +
                   [q for g in v.get("regions", {}).values() for q in g]})
    preset_c = {}
    for p in need:
        dup = M.scratch_dup(f"{M.PRESET_SRC}/{p}", f"{M.SCRATCH}/PRE_{p}")
        M.open_edit(dup)
        preset_c[p] = M.coeffs(dup)
        M.close_edit(dup)
        yield
    probe = M.scratch_dup(M.BASE_PATH, f"{M.SCRATCH}/PB_FaceExplore")
    M.open_edit(probe)
    base_c = M.coeffs(probe)
    res = M.REPORT.setdefault("explore", {})
    actor = M.spawn(probe)
    scene.show_only(actor, [actor])
    yield from M.warmup()
    for v in variants:
        label = v["label"]
        M.assert_clean(label)
        M.set_coeffs(probe, blend(base_c, preset_c, v.get("blend", {}), regions=v.get("regions")))
        lm_blend = M.landmarks(probe)
        moves = apply_landmark_moves(M, probe, v.get("landmark_moves"))
        res[label] = {"blend": v.get("blend", {}), "regions": v.get("regions"), "landmark_moves": moves,
                      "landmarks_after_blend": lm_blend, "landmarks": M.landmarks(probe),
                      "share": preset_share(v.get("blend", {}), v.get("regions"))}
        yield from M.warmup(90, 4.0)
        yield from M.take(scene, M.face_shots(f"x_{label}_", M.PB_FACE_CENTER, tuple(v.get("views", ("Front", "ThreeQuarter")))))
    M.set_coeffs(probe, base_c)
    M.step("explore done")


def ortho_setup(scene):
    rt = ue.RenderingLibrary.create_render_target2d(scene.world, ORTHO_RES, ORTHO_RES,
                                                    ue.TextureRenderTargetFormat.RTF_RGBA8)
    return rt


def take_ortho(scene, M, rt, prefix):
    cap = scene.capture
    shots = [(prefix + "Ortho_Front.png", (0.0, 600.0, ORTHO_CAM_Z), (0.0, 0.0, ORTHO_CAM_Z)),
             (prefix + "Ortho_Side.png", (600.0, 0.0, ORTHO_CAM_Z), (0.0, 0.0, ORTHO_CAM_Z))]
    cap.set_editor_property("projection_type", ue.CameraProjectionMode.ORTHOGRAPHIC)
    cap.set_editor_property("ortho_width", ORTHO_WIDTH)
    cap.set_editor_property("capture_source", ue.SceneCaptureSource.SCS_BASE_COLOR)
    cap.set_editor_property("texture_target", rt)
    saved_hidden = list(scene.hidden)
    scene.hidden = saved_hidden + [scene.backdrop]
    try:
        for name, loc, look in shots:
            scene.aim(loc, look, 30.0)
            scene.apply_hidden()
            yield from M.settle()
            cap.capture_scene()
            M.CAPTURES.mkdir(parents=True, exist_ok=True)
            ue.RenderingLibrary.export_render_target(scene.world, rt, str(M.CAPTURES), name)
            M.REPORT["captures"].append(str(M.CAPTURES / name))
            M.step("captured " + name)
    finally:
        cap.set_editor_property("projection_type", ue.CameraProjectionMode.PERSPECTIVE)
        cap.set_editor_property("capture_source", ue.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        cap.set_editor_property("texture_target", scene.rt)
        scene.hidden = saved_hidden
        scene.apply_hidden()


def verify_job(scene, M):
    """Fresh-session check of the SAVED candidates: reload each asset, compare its face coefficients with the ones
    the build run committed, read body constraints / eval settings, capture face front + body front. Saves nothing."""
    build = json.loads(Path(M.RECIPES).read_text(encoding="utf-8"))["build"]
    names = list(build["candidates"])
    M.assert_locks(extra=names)
    res = M.REPORT.setdefault("verify", {})
    chars = {}
    for name in names:
        path = f"{M.CHAR_DIR}/{name}"
        ch = ue.load_asset(path)
        if not isinstance(ch, ue.MetaHumanCharacter):
            raise RuntimeError(f"{path} did not load as a MetaHumanCharacter")
        M.open_edit(ch)
        c = M.coeffs(ch)
        want = build["candidates"][name]["coeffs"]
        res[name] = {"loaded": True, "coeff_len": len(c),
                     "coeff_max_diff_vs_build": max(abs(a - b) for a, b in zip(c, want)) if len(c) == len(want) else "len mismatch",
                     "constraints": M.constraints(ch), "eval": M.eval_settings(ch),
                     "constraints_match_build": M.constraints(ch) == build["candidates"][name]["constraints"],
                     "can_build_meta_human": bool(M.mhs().can_build_meta_human(ch, False))}
        chars[name] = ch
        M.step(f"verify {name}", diff=res[name]["coeff_max_diff_vs_build"], height=res[name]["constraints"].get("Height"))
        yield
    actors = {n: M.spawn(ch) for n, ch in chars.items()}
    for name in names:
        prefix = "verify_" + name.replace("MH_PlayerBase_", "") + "_"
        scene.show_only(actors[name], list(actors.values()))
        yield from M.warmup()
        yield from M.take(scene, M.face_shots(prefix, M.PB_FACE_CENTER, ("Front",)) + M.body_front(prefix))
    M.step("verify done (nothing saved)")


def build_job(scene, M):
    mhs = M.mhs()
    recipes = json.loads(Path(M.RECIPES).read_text(encoding="utf-8"))
    start = int(recipes.get("blend_start", 1))
    cands = recipes["candidates"]
    names = list(cands)
    M.assert_locks(extra=names)
    for name in names:
        M.assert_clean(name)
        if not name.startswith("MH_PlayerBase_Face"):
            raise ValueError(f"candidate name {name} must start with MH_PlayerBase_Face")
    out = M.REPORT.setdefault("build", {"recipes": recipes, "candidates": {}})

    # 1) preset coefficients (in-memory duplicates, never saved)
    need = sorted({p for r in cands.values() for p in list(r.get("blend", {})) +
                   [q for g in r.get("regions", {}).values() for q in g]})
    preset_c = {}
    for p in need:
        dup = M.scratch_dup(f"{M.PRESET_SRC}/{p}", f"{M.SCRATCH}/PRE_{p}")
        M.open_edit(dup)
        preset_c[p] = M.coeffs(dup)
        M.close_edit(dup)
        M.step(f"preset {p} coefficients read ({len(preset_c[p])})")
        yield

    # 2) unmodified reference: scratch duplicate of MH_PlayerBase (never saved)
    ref = M.scratch_dup(M.BASE_PATH, f"{M.SCRATCH}/PB_FaceRef")
    M.open_edit(ref)
    base_c = M.coeffs(ref)
    out["reference"] = {"coeffs_len": len(base_c), "eval": M.eval_settings(ref), "constraints": M.constraints(ref),
                        "landmarks": M.landmarks(ref)}

    # 3) candidates
    chars = {}
    for name in names:
        rc = cands[name]
        path = f"{M.CHAR_DIR}/{name}"
        if ue.EditorAssetLibrary.does_asset_exist(path):
            M.step(f"deleting earlier {path} (made by this script)")
            if not ue.EditorAssetLibrary.delete_asset(path):
                raise RuntimeError(f"could not delete old {path}")
        ch = ue.EditorAssetLibrary.duplicate_asset(M.BASE_PATH, path)
        if not isinstance(ch, ue.MetaHumanCharacter):
            raise RuntimeError(f"duplicate_asset({M.BASE_PATH}, {path}) -> {ch}")
        M.open_edit(ch)
        c0 = M.coeffs(ch)
        d0 = max(abs(a - b) for a, b in zip(c0, base_c))
        new_c = blend(c0, preset_c, rc.get("blend", {}), start, regions=rc.get("regions"))
        M.set_coeffs(ch, new_c)
        got = M.coeffs(ch)
        moves = apply_landmark_moves(M, ch, rc.get("landmark_moves"))
        final_c = M.coeffs(ch)
        mhs.commit_face_state(ch)
        M.save_asset(ch)
        info = {"asset": path, "recipe": rc, "blend_start": start, "dup_vs_base_max_coeff_diff": d0,
                "set_roundtrip_max_diff": max(abs(a - b) for a, b in zip(got, new_c)),
                "coeff_l2_change": sum((a - b) ** 2 for a, b in zip(new_c, c0)) ** 0.5,
                "coeffs_after_blend": new_c, "landmark_moves": moves, "coeffs": final_c,
                "share": preset_share(rc.get("blend", {}), rc.get("regions")),
                "eval": M.eval_settings(ch), "constraints": M.constraints(ch),
                "landmarks": M.landmarks(ch), "saved": True}
        out["candidates"][name] = info
        chars[name] = ch
        M.step(f"{name} built + saved", l2=round(info["coeff_l2_change"], 3), eval=info["eval"])
        yield

    # 4) captures + measurements with the builder's cameras
    rt_ortho = ortho_setup(scene)
    subjects = [("ref", ref)] + [(n, chars[n]) for n in names]
    actors = {}
    for label, ch in subjects:
        actors[label] = M.spawn(ch)
    all_actors = list(actors.values())
    for label, ch in subjects:
        actor = actors[label]
        prefix = "ref_" if label == "ref" else label.replace("MH_PlayerBase_", "") + "_"
        scene.show_only(actor, all_actors)
        yield from M.warmup()
        shots = M.face_shots(prefix, M.PB_FACE_CENTER, ("Front", "ThreeQuarter", "Profile")) + M.body_front(prefix)
        yield from M.take(scene, shots)
        yield from take_ortho(scene, M, rt_ortho, prefix)
        meas = {"bones": M.bone_positions(actor)}
        try:
            body = M.find_component(actor, "Body")
            meas["body_dump"] = M.dump_component(body, prefix + "Body")
        except Exception as exc:  # noqa: BLE001
            M.warn(f"{label}: body dump failed: {exc!r}")
        try:
            face = M.find_component(actor, "Face")
            meas["face_dump"] = M.dump_component(face, prefix + "Face")
        except Exception as exc:  # noqa: BLE001
            M.warn(f"{label}: face dump failed: {exc!r}")
        meas["constraints"] = M.constraints(ch)
        meas["landmarks"] = M.landmarks(ch)
        target = out["reference"] if label == "ref" else out["candidates"][label]
        target["measure"] = meas
        M.write_report()
    # 5) final save of the candidates (captures do not change them) and release
    for name in names:
        M.save_asset(chars[name])
    M.step("build done")
