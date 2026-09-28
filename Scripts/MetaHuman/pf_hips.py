"""pf_hips.py -- widen MH_PlayerFemale's hips for the catwalk (Cody, 2026-09-26: "can you actually make her hips wider? i think
wide hips are needed for this type of cat walk"). Runs headless through pf_hips_run.ps1, on CharacterLab, one editor at a time.

Only the body's Hip measurement changes. Every other active body constraint keeps its saved value, and the face is put back
EXACTLY: its model coefficients are read before the body change and written again after it (the face follows the body, which is
why pf_female.py always sets the body first), then the face landmarks are compared against the originals.

  1. Scratch duplicate (never saved): Body_Front / Body_Back / Body_Side / Torso_TQ captures at each HIP_VARIANTS value.
  2. The real asset: Hip = PF_HIP (env, cm), face restored, checked, SAVED. Reports can_build_meta_human before and after, i.e.
     whether the body change needs the face re-rigged (that needs Cody's Epic sign-in: pd_rig_assemble.py, windowed editor).
PF_HIP_APPLY=0 renders the variants only and saves nothing.
"""
from __future__ import annotations

import os
import sys
import traceback

sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/MetaHuman")
import pf_common as C  # noqa: E402
import unreal as ue  # noqa: E402

HIP_VARIANTS = [96.5, 100.0, 103.0, 106.0]
HIP = float(os.environ.get("PF_HIP", "102"))
APPLY = os.environ.get("PF_HIP_APPLY", "1") == "1"
VIEWS = ("Body_Front", "Body_Back", "Body_Side", "Torso_TQ")


def active_body(ch) -> dict:
    return {k: v["value"] for k, v in C.constraints(ch).items() if v["active"]}


def set_body(ch, want: dict) -> dict:
    """Same pattern as pf_female.set_body: only the named constraints active, then commit."""
    cons = list(C.mhs().get_body_constraints(ch, False))
    for c in cons:
        n = str(c.name)
        if n in want:
            c.is_active = True
            c.target_measurement = float(want[n])
        else:
            c.is_active = False
    C.mhs().set_body_constraints(ch, cons)
    C.mhs().commit_body_state(ch)
    got = C.constraints(ch)
    return {k: got[k]["value"] for k in want}


def body_keep_face(ch, want: dict, face: list) -> dict:
    got = set_body(ch, want)
    C.set_coeffs(ch, face)
    C.mhs().commit_face_state(ch)
    return got


def lm_diff(a, b) -> float:
    return max(max(abs(p[i] - q[i]) for i in range(3)) for p, q in zip(a, b))


def views(fc, height):
    V = C.views(fc, height)
    mid = (0.0, 0.0, height * 0.52)
    V["Torso_TQ"] = (C.orbit(mid, 190.0, 35, 3), mid, 30.0)
    return V


def job(scene: C.Scene):
    res = C.REPORT.setdefault("hips", {"hip_variants": HIP_VARIANTS, "hip_chosen": HIP, "apply": APPLY})

    # ---- 1. variants on a scratch duplicate of the SAVED asset ----
    ex = C.scratch_dup(C.PF_PATH, "PF_HIPS")
    C.open_edit(ex)
    base = active_body(ex)
    res["saved_body"] = base
    face0 = C.coeffs(ex)
    lm0 = C.landmarks(ex)
    fc = C.face_center_from_landmarks(lm0)
    V = views(fc, base.get("Height", 168.0))
    actor = C.spawn(ex)
    scene.show_only(actor, [actor])
    yield from C.warmup(300, 15.0)
    res["variants"] = {}
    for hip in HIP_VARIANTS:
        want = dict(base)
        want["Hip"] = hip
        got = body_keep_face(ex, want, face0)
        yield from C.warmup(120, 5.0)
        d = lm_diff(C.landmarks(ex), lm0)
        cons = C.constraints(ex)
        res["variants"][str(hip)] = {"got": got, "all": {k: v["value"] for k, v in cons.items()}, "face_landmark_maxdiff_cm": d}
        C.step(f"hip {hip}", got=got, face_landmark_maxdiff_cm=round(d, 4))
        for vn in VIEWS:
            yield from C.shoot(scene, f"hip{hip:g}_{vn}.png", V[vn])
    C.release_actor(scene, actor, ex)
    yield from C.warmup(30, 1.0)

    if not APPLY:
        C.step("variants only (nothing saved)")
        return

    # ---- 2. the real asset ----
    pf = ue.load_asset(C.PF_PATH)
    if not isinstance(pf, ue.MetaHumanCharacter):
        raise RuntimeError(f"{C.PF_PATH} did not load as a MetaHumanCharacter")
    C.open_edit(pf)
    res["can_build_before"] = bool(C.mhs().can_build_meta_human(pf, False))
    before = active_body(pf)
    face_p = C.coeffs(pf)
    lm_p = C.landmarks(pf)
    want = dict(before)
    want["Hip"] = HIP
    res["applied_want"] = want
    res["applied_got"] = body_keep_face(pf, want, face_p)
    yield from C.warmup(60, 2.0)
    after = C.constraints(pf)
    res["applied_all"] = {k: v["value"] for k, v in after.items()}
    res["face_coeff_maxdiff"] = max(abs(a - b) for a, b in zip(C.coeffs(pf), face_p))
    res["face_landmark_maxdiff_cm"] = lm_diff(C.landmarks(pf), lm_p)
    C.check("face_coeffs_restored", res["face_coeff_maxdiff"] < 1e-5, maxdiff=res["face_coeff_maxdiff"])
    C.check("hip_applied", abs(res["applied_got"]["Hip"] - HIP) < 1.0, got=res["applied_got"]["Hip"])
    C.check("other_constraints_kept", all(abs(res["applied_all"][k] - v) < 1.0 for k, v in before.items() if k != "Hip"),
            before=before, after={k: res["applied_all"][k] for k in before})
    res["can_build_after"] = bool(C.mhs().can_build_meta_human(pf, False))
    C.step("can_build", before=res["can_build_before"], after=res["can_build_after"])
    if not ue.EditorAssetLibrary.save_loaded_asset(pf, only_if_is_dirty=False):
        raise RuntimeError("save failed")
    C.step(f"SAVED {C.PF_PATH} with Hip {HIP}")
    C.close_edit(pf)


def main() -> None:
    C.REPORT["script"] = "Scripts/MetaHuman/pf_hips.py"
    C.OUT.mkdir(parents=True, exist_ok=True)
    C.assert_locks()
    C.REPORT["sha_start"] = C.protected_hashes()
    scene = C.Scene()
    C.step("scene ready")
    C.Runner(scene, job(scene)).start()


try:
    main()
except Exception:  # noqa: BLE001
    C.REPORT["error"] = traceback.format_exc()
    C.step("ERROR in main", error=C.REPORT["error"])
    for _ch in list(C.EDITED):
        try:
            C.close_edit(_ch)
        except Exception:  # noqa: BLE001
            pass
    C.REPORT["status"] = "failed"
    C.write_report()
    ue.SystemLibrary.quit_editor()
