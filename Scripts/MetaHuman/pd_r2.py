"""pd_r2.py -- round 2 of the MH_PlayerDefault cleanup (UE 5.8.3, MetaHumanCharacter). Runs INSIDE UnrealEditor on
Exports/CharacterLab/Unreal/CharacterLab.uproject; launch with Scripts/MetaHuman/pd_r2_run.ps1 (one editor at a time,
RAM preflight, SHA-256 of the protected assets before/after, waits for exit).

PD_MODE=explore  saves NOTHING. Scratch duplicate of MH_PlayerBase_FaceC (bald, /Game/PlayerDefault/Scratch, never
                 saved): tries jaw variants that soften the steep posterior-ramus step behind FaceC's residual jaw
                 line, captures each with the pb_conform studio rig + the ambient rig (same cameras), dumps the face
                 mesh of each variant. Then a scratch duplicate of the saved MH_PlayerDefault tests groom colour
                 (Redness/Melanin) from behind.
Shared helpers: pd_r2_common.py. Never signs in; never calls request_auto_rigging / request_texture_sources /
build_meta_human.
"""
from __future__ import annotations

import copy
import json
import math
import os
import sys
import traceback
from pathlib import Path

sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/MetaHuman")
import unreal as ue  # noqa: E402

import pd_r2_common as C  # noqa: E402
from pd_r2_common import step, warn, check, warmup, shoot, switch  # noqa: E402

GONION = (1, 28)          # landmark 1 = character right jaw angle (-X), 28 = left (+X)
JAWCHEEK = (2, 29)        # lower cheek / jaw line in front of the angle


def inward(idx_pair, amount, dz=0.0, dy=0.0):
    """Symmetric move of a (-X, +X) landmark pair towards the midline by `amount` cm (+ optional dz/dy)."""
    return {"idx": list(idx_pair), "d_per": [[amount, dy, dz], [-amount, dy, dz]]}


def recipe_with(rc: dict, **group_weights) -> dict:
    r = copy.deepcopy(rc)
    for g, w in group_weights.items():
        r["regions"][g] = w
    return r


def explore_variants(D: dict) -> list:
    rc = D["facec_recipe"]
    fcm = rc["landmark_moves"]
    lay = C.PFB.layout(D["base"])

    def blend(r):
        return C.PFB.blend(D["base"], D["presets"], r.get("blend", {}), D["blend_start"], regions=r.get("regions"))

    jt = list(D["facec_coeffs"])
    for reg in (20, 21):                      # jaw-side regions: lateral translation back to MH_PlayerBase's
        i0, _n = lay[reg]
        jt[i0 + 5] = D["base"][i0 + 5]
    return [
        {"name": "C0", "desc": "FaceC exactly (control)", "coeffs": D["facec_coeffs"], "moves": []},
        {"name": "R0", "desc": "MH_PlayerBase face (unmodified conform)", "coeffs": D["base"], "moves": []},
        {"name": "L3", "desc": "FaceC + jaw angles (lm 1/28) 3 mm inward", "coeffs": D["facec_coeffs"],
         "moves": [inward(GONION, 0.3)]},
        {"name": "L6", "desc": "FaceC + jaw angles 6 mm inward", "coeffs": D["facec_coeffs"],
         "moves": [inward(GONION, 0.6)]},
        {"name": "L6b", "desc": "FaceC + jaw angles 6 mm + lm 2/29 3 mm inward", "coeffs": D["facec_coeffs"],
         "moves": [inward(GONION, 0.6), inward(JAWCHEEK, 0.3)]},
        {"name": "L9", "desc": "FaceC + jaw angles 9 mm inward (FaceC widened them 8.5 mm)",
         "coeffs": D["facec_coeffs"], "moves": [inward(GONION, 0.9)]},
        {"name": "J45", "desc": "jaw group Kelvin .25 / Jorge .20 (FaceC .40/.35) + FaceC eyelid moves",
         "coeffs": blend(recipe_with(rc, jaw={"Kelvin": 0.25, "Jorge": 0.2})), "moves": fcm},
        {"name": "J20", "desc": "jaw group Kelvin .10 / Jorge .10 (= FaceC neck) + FaceC eyelid moves",
         "coeffs": blend(recipe_with(rc, jaw={"Kelvin": 0.1, "Jorge": 0.1})), "moves": fcm},
        {"name": "JT", "desc": "FaceC with jaw-side regions 20/21 lateral translation = MH_PlayerBase", "coeffs": jt,
         "moves": []},
        {"name": "N40", "desc": "neck group Kelvin .20 / Jorge .20 (FaceC .10/.10) + FaceC eyelid moves",
         "coeffs": blend(recipe_with(rc, neck={"Kelvin": 0.2, "Jorge": 0.2})), "moves": fcm},
        {"name": "E75", "desc": "ears group = jaw weights Kelvin .40 / Jorge .35 (FaceC default .35/.15) + moves",
         "coeffs": blend(recipe_with(rc, ears={"Kelvin": 0.4, "Jorge": 0.35})), "moves": fcm},
    ]


def apply_variant(ch, v) -> dict:
    C.set_coeffs(ch, v["coeffs"])
    flat = C.translate_landmarks(ch, v["moves"]) if v["moves"] else []
    return {"moves_flat": flat, "coeffs": C.coeffs(ch), "landmarks": C.landmarks(ch)}


def explore_job(scene: C.Scene):
    D = C.offline_coeff_data()
    res = C.REPORT.setdefault("explore", {"variants": {}})
    # offline blend reproduces FaceC's pre-move coefficients exactly
    rc = D["facec_recipe"]
    ab = C.PFB.blend(D["base"], D["presets"], rc["blend"], D["blend_start"], regions=rc["regions"])
    res["offline_blend_vs_facec_after_blend_maxdiff"] = C.max_abs_diff(ab, D["facec_after_blend"])
    check("offline_blend_reproduces_facec", res["offline_blend_vs_facec_after_blend_maxdiff"] == 0.0,
          maxdiff=res["offline_blend_vs_facec_after_blend_maxdiff"])

    ex = C.scratch_dup(C.FACEC_PATH, "PD_R2_Explore")
    C.open_edit(ex)
    c0 = C.coeffs(ex)
    res["dup_vs_facec_build_maxdiff"] = C.max_abs_diff(c0, D["facec_coeffs"])
    res["eval"] = C.eval_settings(ex)
    # determinism: after-blend + FaceC's landmark moves == FaceC's saved coefficients?
    C.set_coeffs(ex, ab)
    C.translate_landmarks(ex, rc["landmark_moves"])
    res["rebuild_facec_vs_saved_maxdiff"] = C.max_abs_diff(C.coeffs(ex), D["facec_coeffs"])
    check("facec_rebuild_deterministic", res["rebuild_facec_vs_saved_maxdiff"] < 1e-4,
          maxdiff=res["rebuild_facec_vs_saved_maxdiff"])
    C.set_coeffs(ex, D["facec_coeffs"])
    actor = C.spawn(ex)
    scene.show_only(actor, [actor])
    yield from warmup(240, 12.0)

    variants = explore_variants(D)
    views = C.all_views()
    passes = [("ambient", ["Face_ThreeQuarter", "JawClose", "JawRamus", "JawLow", "Face_Front"]),
              ("studio", ["Face_ThreeQuarter", "JawClose", "JawRamus", "Face_Front", "Face_Profile"])]
    for pi, (variant, names) in enumerate(passes):
        yield from switch(scene, variant)
        for v in variants:
            info = apply_variant(ex, v)
            yield from warmup(60, 2.5)
            if pi == 0:
                row = {"desc": v["desc"], "moves": info["moves_flat"],
                       "coeff_maxdiff_vs_facec": C.max_abs_diff(info["coeffs"], D["facec_coeffs"]),
                       "coeff_l2_vs_facec": sum((a - b) ** 2 for a, b in zip(info["coeffs"], D["facec_coeffs"])) ** 0.5,
                       "landmarks": info["landmarks"], "coeffs": info["coeffs"]}
                try:
                    row["dump_Face"] = C.dump_mesh(C.find_component(actor, "Face"), f"R2X_{v['name']}_Face")
                except Exception as exc:  # noqa: BLE001
                    row["dump_Face"] = "ERR " + repr(exc)[:200]
                res["variants"][v["name"]] = row
                step(f"variant {v['name']} applied", l2=round(row["coeff_l2_vs_facec"], 4))
            for vn in names:
                yield from shoot(scene, f"x_{v['name']}_{vn}_{variant}.png", views[vn])
    C.set_coeffs(ex, D["facec_coeffs"])
    C.release_actor(scene, actor, ex)
    yield from warmup(30, 1.0)

    # (the groom-colour test moved to hair_test(): grooms render only for the first MetaHuman of a session)
    step("explore done (nothing saved)")


def hair_test(scene: C.Scene, prefix: str = "h"):
    """Groom colour from behind on a scratch duplicate of the saved MH_PlayerDefault. Must run FIRST in a session
    (explore 1: grooms bound but did not render when another MetaHuman had been spawned earlier)."""
    views = C.all_views()
    # ---------------- groom colour from behind: scratch duplicate of the saved MH_PlayerDefault ----------------
    hres = C.REPORT.setdefault("hair", {})
    ht = C.scratch_dup(C.PD_PATH, "PD_R2_HairTest")
    C.open_edit(ht)
    ha = C.spawn(ht)
    scene.show_only(ha, [ha])
    yield from switch(scene, "studio")
    yield from warmup(300, 15.0)
    col = C.mhs().get_preview_collection(ht)
    sel = C.selections(col)
    hres["params_before"] = {s: C.instance_params(col, k[1]) for s, k in sel.items() if s in ("Hair", "Eyebrows", "Eyelashes")}
    hres["grooms"] = C.groom_state(ha)
    hair_sets = [("H25", 0.9, 0.25), ("H10", 0.9, 0.10), ("H05", 0.95, 0.05)]
    hviews = ["Body_Back", "Shoulders_Back", "Head_Back34", "Head_Back_Far", "Face_Front", "Head_Top"]
    for label, mel, red in hair_sets:
        col = C.mhs().get_preview_collection(ht)
        sel = C.selections(col)
        for slot in ("Hair", "Eyebrows"):
            if slot in sel:
                C.set_groom_param(col, sel[slot][1], "Melanin", mel)
                C.set_groom_param(col, sel[slot][1], "Redness", red)
        C.mhs().on_edit_preview_collection(ht)
        C.mhs().assemble_for_preview(ht)
        yield from warmup(150, 8.0)
        col = C.mhs().get_preview_collection(ht)
        sel = C.selections(col)
        hres[label] = {"set": {"Melanin": mel, "Redness": red},
                       "read": {s: C.instance_params(col, k[1]) for s, k in sel.items() if s in ("Hair", "Eyebrows")},
                       "grooms": C.groom_state(ha)}
        step(f"hair set {label}", mel=mel, red=red)
        yield from switch(scene, "studio")
        for vn in hviews:
            yield from shoot(scene, f"{prefix}_{label}_{vn}_studio.png", views[vn])
        yield from switch(scene, "ambient")
        for vn in ("Head_Back_Far", "Body_Back", "Face_Front"):
            yield from shoot(scene, f"{prefix}_{label}_{vn}_ambient.png", views[vn])
    C.release_actor(scene, ha, ht)


NECKBACK = (68, 46)       # neck just behind/below the jaw angle (-X, +X)
LOBE = (55, 21)           # skin below the ear lobe at the top of the ramus (-X, +X)


def outward(idx_pair, amount, dz=0.0, dy=0.0):
    return {"idx": list(idx_pair), "d_per": [[-amount, dy, dz], [amount, dy, dz]]}


def explore2_variants(D: dict) -> list:
    rc = D["facec_recipe"]
    fcm = rc["landmark_moves"]
    fc = D["facec_coeffs"]
    j20 = C.PFB.blend(D["base"], D["presets"], rc["blend"], D["blend_start"],
                      regions=recipe_with(rc, jaw={"Kelvin": 0.1, "Jorge": 0.1})["regions"])
    return [
        {"name": "C0", "desc": "FaceC exactly (control)", "coeffs": fc, "moves": []},
        {"name": "N3", "desc": "FaceC + neck behind jaw angle (lm 46/68) 3 mm outward", "coeffs": fc,
         "moves": [outward(NECKBACK, 0.3)]},
        {"name": "N6", "desc": "FaceC + lm 46/68 6 mm outward", "coeffs": fc, "moves": [outward(NECKBACK, 0.6)]},
        {"name": "U3", "desc": "FaceC + below-lobe ramus top (lm 21/55) 3 mm outward", "coeffs": fc,
         "moves": [outward(LOBE, 0.3)]},
        {"name": "L6N4", "desc": "FaceC + jaw angles 6 mm in + lm 46/68 4 mm out", "coeffs": fc,
         "moves": [inward(GONION, 0.6), outward(NECKBACK, 0.4)]},
        {"name": "L9N4", "desc": "FaceC + jaw angles 9 mm in + lm 46/68 4 mm out", "coeffs": fc,
         "moves": [inward(GONION, 0.9), outward(NECKBACK, 0.4)]},
        {"name": "L6N4U2", "desc": "FaceC + jaw angles 6 mm in + 46/68 4 mm out + 21/55 2 mm out", "coeffs": fc,
         "moves": [inward(GONION, 0.6), outward(NECKBACK, 0.4), outward(LOBE, 0.2)]},
        {"name": "L6up", "desc": "FaceC + jaw angles 6 mm in and 3 mm up", "coeffs": fc,
         "moves": [inward(GONION, 0.6, dz=0.3)]},
        {"name": "L6back", "desc": "FaceC + jaw angles 6 mm in and 3 mm back", "coeffs": fc,
         "moves": [inward(GONION, 0.6, dy=-0.3)]},
        {"name": "J20L6N4", "desc": "jaw group .1/.1 + FaceC eyelid moves + jaw angles 6 mm in + 46/68 4 mm out",
         "coeffs": j20, "moves": list(fcm) + [inward(GONION, 0.6), outward(NECKBACK, 0.4)]},
    ]


def explore3_variants(D: dict) -> list:
    fc = D["facec_coeffs"]
    return [
        {"name": "C0", "desc": "FaceC exactly (control)", "coeffs": fc, "moves": []},
        {"name": "L9N4", "desc": "FaceC + jaw angles 9 mm in (request) + lm 46/68 4 mm out (request)", "coeffs": fc,
         "moves": [inward(GONION, 0.9), outward(NECKBACK, 0.4)]},
        {"name": "L9N8", "desc": "FaceC + jaw angles 9 mm in + lm 46/68 8 mm out (requests)", "coeffs": fc,
         "moves": [inward(GONION, 0.9), outward(NECKBACK, 0.8)]},
        {"name": "L12N4", "desc": "FaceC + jaw angles 12 mm in + lm 46/68 4 mm out (requests)", "coeffs": fc,
         "moves": [inward(GONION, 1.2), outward(NECKBACK, 0.4)]},
        {"name": "L12N8", "desc": "FaceC + jaw angles 12 mm in + lm 46/68 8 mm out (requests)", "coeffs": fc,
         "moves": [inward(GONION, 1.2), outward(NECKBACK, 0.8)]},
    ]


def explore3_job(scene: C.Scene):
    """Refinement of the landmark-only jaw-ramus fix + the looks needed to judge it (nothing saved)."""
    D = C.offline_coeff_data()
    res = C.REPORT.setdefault("explore3", {"variants": {}})
    views = C.all_views()
    ex = C.scratch_dup(C.FACEC_PATH, "PD_R2_Explore3")
    C.open_edit(ex)
    res["dup_vs_facec_build_maxdiff"] = C.max_abs_diff(C.coeffs(ex), D["facec_coeffs"])
    actor = C.spawn(ex)
    scene.show_only(actor, [actor])
    yield from warmup(240, 12.0)
    variants = explore3_variants(D)
    passes = [("ambient", ["Face_ThreeQuarter", "JawClose", "JawRamus", "Face_Front", "JawLow"]),
              ("studio", ["Face_ThreeQuarter", "JawClose", "JawRamus", "Face_Front", "Face_Profile", "JawLow"]),
              ("eval", ["Face_ThreeQuarter", "JawClose"]),
              ("bounce", ["Face_ThreeQuarter", "JawClose"]),
              ("headlight", ["Face_ThreeQuarter", "JawClose", "Face_Front"])]
    for pi, (variant, names) in enumerate(passes):
        yield from switch(scene, variant)
        for v in variants:
            info = apply_variant(ex, v)
            yield from warmup(60, 2.5)
            if pi == 0:
                res["variants"][v["name"]] = {
                    "desc": v["desc"], "moves": info["moves_flat"],
                    "coeff_maxdiff_vs_facec": C.max_abs_diff(info["coeffs"], D["facec_coeffs"]),
                    "coeff_l2_vs_facec": sum((a - b) ** 2 for a, b in zip(info["coeffs"], D["facec_coeffs"])) ** 0.5,
                    "landmarks": info["landmarks"], "coeffs": info["coeffs"]}
                step(f"variant {v['name']} applied", l2=round(res["variants"][v["name"]]["coeff_l2_vs_facec"], 4))
            for vn in names:
                yield from shoot(scene, f"x3_{v['name']}_{vn}_{variant}.png", views[vn])
    # geometry of each variant: commit on the scratch duplicate (never saved) so the CPU mesh copy reflects it
    for v in variants:
        apply_variant(ex, v)
        C.mhs().commit_face_state(ex)
        yield from warmup(30, 1.0)
        try:
            res["variants"][v["name"]]["dump_Face"] = C.dump_mesh(C.find_component(actor, "Face"), f"R2X3_{v['name']}_Face")
        except Exception as exc:  # noqa: BLE001
            res["variants"][v["name"]]["dump_Face"] = "ERR " + repr(exc)[:200]
    C.set_coeffs(ex, D["facec_coeffs"])
    C.release_actor(scene, actor, ex)
    step("explore3 done (nothing saved)")


def explore2_job(scene: C.Scene):
    D = C.offline_coeff_data()
    res = C.REPORT.setdefault("explore2", {"variants": {}})
    views = C.all_views()
    yield from hair_test(scene, "h2")
    yield from warmup(30, 1.0)
    # ---- Epic preset Kelvin as the reference jaw (grooms hidden), moved so its face centre = our camera target ----
    try:
        kel = C.scratch_dup(f"{C.PRESET_SRC}/Kelvin", "PD_R2_Kelvin")
        C.open_edit(kel)
        ka = C.spawn(kel)
        kc = json.loads(C.FACE_PROBE_REPORT.read_text(encoding="utf-8"))["probe"]["kelvin_face_center"]
        off = [C.FACE_CENTER[i] - kc[i] for i in range(3)]
        ka.set_actor_location(ue.Vector(*off), False, False)
        for comp in ka.get_components_by_class(ue.GroomComponent):
            comp.set_visibility(False, False)
        scene.show_only(ka, [ka])
        res["kelvin_offset"] = off
        yield from warmup(240, 12.0)
        for variant, names in (("ambient", ["Face_ThreeQuarter", "JawClose", "JawRamus", "Face_Front"]),
                               ("studio", ["Face_ThreeQuarter", "JawClose", "Face_Front"])):
            yield from switch(scene, variant)
            for vn in names:
                yield from shoot(scene, f"k_Kelvin_{vn}_{variant}.png", views[vn])
        C.release_actor(scene, ka, kel)
        yield from warmup(30, 1.0)
    except Exception as exc:  # noqa: BLE001
        warn("kelvin reference failed: " + traceback.format_exc()[-500:])

    ex = C.scratch_dup(C.FACEC_PATH, "PD_R2_Explore2")
    C.open_edit(ex)
    res["dup_vs_facec_build_maxdiff"] = C.max_abs_diff(C.coeffs(ex), D["facec_coeffs"])
    actor = C.spawn(ex)
    scene.show_only(actor, [actor])
    yield from warmup(240, 12.0)
    variants = explore2_variants(D)
    passes = [("ambient", ["Face_ThreeQuarter", "JawClose", "JawRamus", "Face_Front"]),
              ("studio", ["Face_ThreeQuarter", "JawClose", "Face_Front", "Face_Profile"]),
              ("headlight", ["Face_ThreeQuarter", "JawClose"])]
    for pi, (variant, names) in enumerate(passes):
        yield from switch(scene, variant)
        for v in variants:
            info = apply_variant(ex, v)
            yield from warmup(60, 2.5)
            if pi == 0:
                res["variants"][v["name"]] = {
                    "desc": v["desc"], "moves": info["moves_flat"],
                    "coeff_maxdiff_vs_facec": C.max_abs_diff(info["coeffs"], D["facec_coeffs"]),
                    "coeff_l2_vs_facec": sum((a - b) ** 2 for a, b in zip(info["coeffs"], D["facec_coeffs"])) ** 0.5,
                    "landmarks": info["landmarks"], "coeffs": info["coeffs"]}
                step(f"variant {v['name']} applied", l2=round(res["variants"][v["name"]]["coeff_l2_vs_facec"], 4))
            for vn in names:
                yield from shoot(scene, f"x2_{v['name']}_{vn}_{variant}.png", views[vn])
    C.set_coeffs(ex, D["facec_coeffs"])
    C.release_actor(scene, actor, ex)
    step("explore2 done (nothing saved)")


# ================================================================================================================
# BUILD + VERIFY (round 2): MH_PlayerDefault = FaceC + jaw-ramus fix + identity
# ================================================================================================================
HAIR_WI = f"{C.GROOM_ROOT}/Hair/WI_Hair_S_BrushCut"
BROWS_WI = f"{C.GROOM_ROOT}/Eyebrows/WI_Eyebrows_M_SlightArch"
LASHES_WI = f"{C.GROOM_ROOT}/Eyelashes/WI_Eyelashes_S_Fine"
EYES_PRESET = f"{C.PRESET_SRC}/Kelvin"
FACE_TEXTURE_INDEX = 36
LASH_CARD_MELANIN = 0.9
# groom colour: Melanin 0.9 as round 1; Redness 0.25 (wardrobe default) -> 0.10 on hair + brows so the short BrushCut
# does not read copper/auburn from behind (round-1 verifier; Redness = pheomelanin share)
GROOM_PARAMS = {"Hair": {"Melanin": 0.9, "Redness": 0.1}, "Eyebrows": {"Melanin": 0.9, "Redness": 0.1},
                "Eyelashes": {"Melanin": 0.9}}
EMPTY_SLOTS = ("Beard", "Mustache", "Peachfuzz", "Outfits", "Top Garment", "Bottom Garment")
# jaw-ramus fix chosen from explore 1-3 (WorkFiles/MetaHuman/player_default/pd_r2_explore*_1.json, r2_explore*_captures):
# variant L9N8 = FaceC + jaw-angle landmarks 1/28 requested 9 mm towards the midline (the solver moves them 4.4 mm)
# + neck-behind-the-jaw-angle landmarks 46/68 requested 8 mm outwards (moved 2.1 mm). Nothing else in the recipe changes.
JAW_FIX = {"name": "L9N8",
           "moves": [inward(GONION, 0.9), outward(NECKBACK, 0.8)],
           "why": "FaceC widened the jaw angles 8.5 mm/side over the conform while the neck behind them stayed, so the "
                  "posterior ramus turns away from the key light over a short distance and renders as a crisp line from "
                  "the ear to the jaw angle. L9N8 halves the widening and fills the neck 2 mm: ramus-line depth "
                  "(JawClose, ambient rig) 22.6 -> 16.2, below Epic's Kelvin preset (19.1) in the same rig/camera."}
BUILD_REPORT_FOR_VERIFY = C.OUT / "pd_r2_build_{attempt}.json"


def identity_readback(ch) -> dict:
    s = ch.get_editor_property("skin_settings")
    sp = s.get_editor_property("skin")
    fr = s.get_editor_property("freckles")
    eyes = ch.get_editor_property("eyes_settings")
    el = ch.get_editor_property("head_model_settings").get_editor_property("eyelashes")
    mk = ch.get_editor_property("makeup_settings")
    iris = {}
    for side in ("eye_left", "eye_right"):
        ir = eyes.get_editor_property(side).get_editor_property("iris")
        iris[side] = {"pattern": C.enum_s(ir.get_editor_property("pattern")),
                      "primary_u": round(float(ir.get_editor_property("primary_color_u")), 4),
                      "primary_v": round(float(ir.get_editor_property("primary_color_v")), 4),
                      "secondary_u": round(float(ir.get_editor_property("secondary_color_u")), 4),
                      "secondary_v": round(float(ir.get_editor_property("secondary_color_v")), 4)}
    return {"face_texture_index": int(sp.get_editor_property("face_texture_index")),
            "body_texture_index": int(sp.get_editor_property("body_texture_index")),
            "u": round(float(sp.get_editor_property("u")), 4), "v": round(float(sp.get_editor_property("v")), 4),
            "roughness": round(float(sp.get_editor_property("roughness")), 4),
            "show_top_underwear": bool(sp.get_editor_property("show_top_underwear")),
            "freckles_mask": C.enum_s(fr.get_editor_property("mask")),
            "iris": iris,
            "eyelashes_type": C.enum_s(el.get_editor_property("type")),
            "eyelashes_enable_grooms": bool(el.get_editor_property("enable_grooms")),
            "eyelashes_card_melanin": round(float(el.get_editor_property("melanin")), 4),
            "makeup_types": {k: C.enum_s(mk.get_editor_property(k).get_editor_property("type"))
                             for k in ("blush", "eyes", "lips")},
            "foundation": bool(mk.get_editor_property("foundation").get_editor_property("apply_foundation"))}


def identity_ok(r: dict, sel: dict) -> dict:
    want_sel = {"Hair": "WI_Hair_S_BrushCut", "Eyebrows": "WI_Eyebrows_M_SlightArch", "Eyelashes": "WI_Eyelashes_S_Fine"}
    res = {
        "face_texture_index": r["face_texture_index"] == FACE_TEXTURE_INDEX,
        "tone_neutral": abs(r["u"] - 0.5) < 1e-3 and abs(r["v"] - 0.5) < 1e-3,
        "freckles_none": r["freckles_mask"] == "NONE",
        "underwear_top_on": r["show_top_underwear"] is True,
        "iris_both_IRIS006": all(r["iris"][s]["pattern"] == "IRIS006" for s in ("eye_left", "eye_right")),
        "iris_both_dark": all(abs(r["iris"][s]["primary_v"] - 0.0755) < 2e-3 for s in ("eye_left", "eye_right")),
        "eyelashes_short_fine": r["eyelashes_type"] == "SHORT_FINE",
        "eyelash_card_melanin": abs(r["eyelashes_card_melanin"] - LASH_CARD_MELANIN) < 1e-3,
        "makeup_none": all(v == "NONE" for v in r["makeup_types"].values()) and not r["foundation"],
    }
    for slot, want in want_sel.items():
        got = sel.get(slot, ("", None))
        got = got[0] if isinstance(got, tuple) else got
        res[f"slot_{slot}"] = str(got).startswith(want)
    for slot in EMPTY_SLOTS:
        got = sel.get(slot)
        got = got[0] if isinstance(got, tuple) else got
        res[f"slot_{slot}_empty"] = (got is None) or got in ("", "None", "none")
    return res


def groom_params_ok(params: dict) -> dict:
    out = {}
    for slot, want in GROOM_PARAMS.items():
        for name, value in want.items():
            v = params.get(slot, {}).get(name) if isinstance(params, dict) else None
            out[f"{slot}.{name}"] = isinstance(v, float) and abs(v - value) < 1e-3
    return out


def region_changes(a, b, lay) -> dict:
    """Which face-model regions differ between two coefficient vectors (max abs diff per region)."""
    out = {}
    for r, (i0, n) in enumerate(lay):
        d = max(abs(a[i] - b[i]) for i in range(i0, i0 + 9 + n))
        if d > 1e-6:
            out[str(r)] = round(d, 5)
    return out


def apply_jaw_fix(ch, D) -> dict:
    """FaceC coefficients (the duplicate already carries them) + the round-2 jaw-ramus landmark moves."""
    c_before = C.coeffs(ch)
    lm_before = C.landmarks(ch)
    flat = C.translate_landmarks(ch, JAW_FIX["moves"]) if JAW_FIX["moves"] else []
    c_after = C.coeffs(ch)
    return {"moves_flat": flat, "coeffs_before": c_before, "coeffs_after": c_after, "landmarks_before": lm_before,
            "landmarks_after": C.landmarks(ch),
            "coeff_maxdiff_vs_facec": C.max_abs_diff(c_after, D["facec_coeffs"]),
            "regions_changed_vs_facec": region_changes(c_after, D["facec_coeffs"], C.PFB.layout(D["base"]))}


RECIPE_PATH = C.OUT / "player_default_recipe.json"


def write_recipe(D, res, fix, rb, sel_int) -> None:
    old = None
    if RECIPE_PATH.exists():
        old = json.loads(RECIPE_PATH.read_text(encoding="utf-8"))
        (C.OUT / "player_default_recipe_round1.json").write_text(json.dumps(old, indent=1), encoding="utf-8")
    recipe = {
        "asset": C.PD_PATH, "built_utc": C._now(), "round": 2,
        "build_script": "Scripts/MetaHuman/pd_r2.py (PD_MODE=build) via Scripts/MetaHuman/pd_r2_run.ps1 -Mode build",
        "reproduce": ["duplicate /Game/Characters/MetaHumans/MH_PlayerBase_FaceC -> MH_PlayerDefault",
                      "add WI_Hair_S_BrushCut + WI_Eyebrows_M_SlightArch to the INTERNAL collection before opening",
                      "open for edit; translate_face_landmarks(jaw_fix.moves); commit_face_state",
                      "skin / eyes / makeup / head-model eyelashes as below; groom instance parameters as below; save"],
        "face": {"base_recipe_file": str(C.FACE_RECIPES), "base_recipe_candidate": "MH_PlayerBase_FaceC",
                 "base_recipe": D["facec_recipe"], "base_coeffs_source": str(C.FACE_BUILD_REPORT),
                 "jaw_fix": JAW_FIX, "jaw_fix_moves_applied": fix["moves_flat"],
                 "coeffs_final": res["coeffs_final"],
                 "coeff_maxdiff_vs_facec": fix["coeff_maxdiff_vs_facec"],
                 "regions_changed_vs_facec": fix["regions_changed_vs_facec"],
                 "landmarks_final": res["landmarks_final"],
                 "revert": "set JAW_FIX moves to [] in pd_r2.py and rebuild = the round-1 face (FaceC exactly)"},
        "identity": {
            "skin": {"face_texture_index": FACE_TEXTURE_INDEX, "u": 0.5, "v": 0.5, "show_top_underwear": True,
                     "body_texture_index": "kept (0)", "roughness": "kept (1.06)", "accents": "kept (all 0.5)",
                     "freckles_mask": "NONE", "enable_texture_overrides": False},
            "eyes": {"from_preset": "Kelvin", "iris_pattern": "IRIS006", "primary_color_uv": [0.9003, 0.0755],
                     "secondary_color_uv": [0.9753, 0.0964], "why": "natural dark brown"},
            "eyelashes_head_model": {"type": "SHORT_FINE", "enable_grooms": True, "melanin": LASH_CARD_MELANIN},
            "grooms": {"Hair": "WI_Hair_S_BrushCut", "Eyebrows": "WI_Eyebrows_M_SlightArch",
                       "Eyelashes": "WI_Eyelashes_S_Fine (auto from head-model eyelashes)",
                       "Beard": None, "Mustache": None, "Peachfuzz": None, "Outfits": None,
                       "instance_parameters": GROOM_PARAMS},
            "makeup": "none (MetaHumanCharacterMakeupSettings() defaults)",
            "outfit": "none; the tank top + briefs are the skin material's painted underwear"},
        "readback_at_build": rb,
        "collection_selections_at_build": {k: v[0] for k, v in sel_int.items()},
        "groom_instance_params_at_build": res.get("groom_params"),
        "round1_recipe": "player_default_recipe_round1.json" if old else None,
        "not_called": ["request_auto_rigging", "request_texture_sources", "build_meta_human"]}
    RECIPE_PATH.write_text(json.dumps(recipe, indent=1, default=str), encoding="utf-8")
    step("recipe written", path=str(RECIPE_PATH))


def build_job(scene: C.Scene):
    D = C.offline_coeff_data()
    res = C.REPORT.setdefault("build", {"jaw_fix": JAW_FIX, "groom_params": GROOM_PARAMS})
    C.assert_clean(C.PD_PATH)
    if ue.EditorAssetLibrary.does_asset_exist(C.PD_PATH):
        step(f"deleting the round-1 {C.PD_PATH} (made by pd_player_default.py; locked by claude)")
        if not ue.EditorAssetLibrary.delete_asset(C.PD_PATH):
            raise RuntimeError(f"could not delete old {C.PD_PATH}")
    ch = ue.EditorAssetLibrary.duplicate_asset(C.FACEC_PATH, C.PD_PATH)
    if not isinstance(ch, ue.MetaHumanCharacter):
        raise RuntimeError(f"duplicate_asset({C.FACEC_PATH}, {C.PD_PATH}) -> {ch}")
    step("MH_PlayerDefault duplicated from FaceC")
    res["internal_collection_at_duplicate"] = C.collection_inventory(ch.get_editor_property("internal_collection"))
    res["grooms_added"] = {"Hair": C.add_to_internal(ch, "Hair", HAIR_WI),
                           "Eyebrows": C.add_to_internal(ch, "Eyebrows", BROWS_WI)}
    step("hair + brows added to the internal collection", **res["grooms_added"])
    C.open_edit(ch)
    c0 = C.coeffs(ch)
    res["coeffs_at_open_vs_facec_build_maxdiff"] = C.max_abs_diff(c0, D["facec_coeffs"])
    check("build_dup_coeffs_equal_facec", res["coeffs_at_open_vs_facec_build_maxdiff"] == 0.0,
          maxdiff=res["coeffs_at_open_vs_facec_build_maxdiff"])
    res["eval_settings_at_open"] = C.eval_settings(ch)
    yield

    # ---- face: jaw-ramus fix on top of the FaceC recipe, then commit ----
    fix = apply_jaw_fix(ch, D)
    C.mhs().commit_face_state(ch)
    fix["coeffs_after_commit_maxdiff_vs_after_moves"] = C.max_abs_diff(C.coeffs(ch), fix["coeffs_after"])
    res["jaw_fix_result"] = fix
    step("jaw fix applied + face committed", maxdiff_vs_facec=fix["coeff_maxdiff_vs_facec"],
         regions=fix["regions_changed_vs_facec"], commit_roundtrip=fix["coeffs_after_commit_maxdiff_vs_after_moves"])
    yield from warmup(30, 1.0)

    # ---- skin: texture variant 36, neutral tone, no freckles, painted top underwear kept on ----
    s = ch.get_editor_property("skin_settings")
    sp = s.get_editor_property("skin")
    sp.set_editor_property("face_texture_index", FACE_TEXTURE_INDEX)
    sp.set_editor_property("u", 0.5)
    sp.set_editor_property("v", 0.5)
    sp.set_editor_property("show_top_underwear", True)
    s.set_editor_property("skin", sp)
    fr = s.get_editor_property("freckles")
    fr.set_editor_property("mask", ue.MetaHumanCharacterFrecklesMask.NONE)
    s.set_editor_property("freckles", fr)
    s.set_editor_property("enable_texture_overrides", False)
    C.mhs().commit_skin_settings(ch, s)
    step("skin committed")
    yield from warmup(30, 1.0)
    eyes = ue.load_asset(EYES_PRESET).get_editor_property("eyes_settings")
    C.mhs().commit_eyes_settings(ch, eyes)
    step("eyes committed (Kelvin preset eyes_settings)")
    yield from warmup(60, 2.5)
    C.mhs().commit_makeup_settings(ch, ue.MetaHumanCharacterMakeupSettings())
    step("makeup committed (defaults = none)")
    yield
    hm = ch.get_editor_property("head_model_settings")
    el = hm.get_editor_property("eyelashes")
    el.set_editor_property("type", ue.MetaHumanCharacterEyelashesType.SHORT_FINE)
    el.set_editor_property("enable_grooms", True)
    el.set_editor_property("melanin", LASH_CARD_MELANIN)
    hm.set_editor_property("eyelashes", el)
    C.mhs().commit_head_model_settings(ch, hm)
    step("head model eyelashes committed (SHORT_FINE)")
    yield from warmup(30, 1.0)
    col = C.mhs().get_preview_collection(ch)
    sel = C.selections(col)
    if not sel.get("Eyelashes", ("", None))[0].startswith("WI_Eyelashes_S_Fine"):
        warn(f"eyelash groom not auto-selected ({sel.get('Eyelashes')}); selecting WI_Eyelashes_S_Fine explicitly")
        key = col.try_add_item_from_wardrobe_item("Eyelashes", ue.load_asset(LASHES_WI))
        col.get_editor_property("default_instance").set_single_slot_selection("Eyelashes", key)
    for slot in EMPTY_SLOTS:
        got = sel.get(slot)
        if got is not None and got[0] not in ("", "None"):
            warn(f"slot {slot} had {got[0]}: clearing")
            col.get_editor_property("default_instance").set_single_slot_selection(slot, ue.MetaHumanPaletteItemKey())
    C.mhs().on_edit_preview_collection(ch)
    actor = C.spawn(ch)
    scene.show_only(actor, [actor])
    yield from warmup(240, 12.0)
    col = C.mhs().get_preview_collection(ch)
    sel_prev = C.selections(col)
    res["groom_params_before_set"] = {slot: C.instance_params(col, k[1]) for slot, k in sel_prev.items()
                                      if slot in GROOM_PARAMS}
    res["groom_params_set"] = {f"{slot}.{n}": C.set_groom_param(col, sel_prev[slot][1], n, v)
                               for slot, want in GROOM_PARAMS.items() if slot in sel_prev for n, v in want.items()}
    C.mhs().on_edit_preview_collection(ch)
    C.mhs().assemble_for_preview(ch)
    step("groom parameters set", **res["groom_params_set"])
    yield from warmup(150, 8.0)
    col = C.mhs().get_preview_collection(ch)
    sel_prev = C.selections(col)
    sel_int = C.selections(ch.get_editor_property("internal_collection"))
    res["preview_collection"] = C.collection_inventory(col)
    res["internal_collection"] = C.collection_inventory(ch.get_editor_property("internal_collection"))
    res["groom_params"] = {slot: C.instance_params(col, k[1]) for slot, k in sel_prev.items() if slot in GROOM_PARAMS}
    res["grooms"] = C.groom_state(actor)
    res["eye_mids"] = C.eye_mid_params(actor)
    rb = identity_readback(ch)
    res["identity_readback"] = rb
    c1 = C.coeffs(ch)
    res["coeffs_final"] = c1
    res["coeffs_final_vs_fix_maxdiff"] = C.max_abs_diff(c1, fix["coeffs_after"])
    res["landmarks_final"] = C.landmarks(ch)
    res["constraints_after"] = C.constraints(ch)
    res["eval_settings"] = C.eval_settings(ch)
    res["settings_before_save"] = C.character_settings(ch)
    oks = identity_ok(rb, sel_int)
    check("build_identity", all(oks.values()), detail=oks)
    gp = groom_params_ok(res["groom_params"])
    check("build_groom_params_preview", all(gp.values()), detail=gp)
    check("build_face_coeffs_equal_fix", res["coeffs_final_vs_fix_maxdiff"] == 0.0,
          maxdiff=res["coeffs_final_vs_fix_maxdiff"])
    same_c = max(abs(res["constraints_after"][k]["value"] - float(v)) for k, v in D["facec_constraints"].items()) < 2e-3
    check("build_constraints_equal_facec", same_c)
    check("build_eval_settings_equal_facec", res["eval_settings"] == D["facec_eval"], got=res["eval_settings"])
    C.write_report()

    path = ch.get_path_name()
    if not path.startswith(C.PD_PATH + "."):
        raise RuntimeError(f"refusing to save {path}")
    if not ue.EditorAssetLibrary.save_loaded_asset(ch, only_if_is_dirty=False):
        raise RuntimeError(f"save failed: {path}")
    res["saved"] = True
    step("MH_PlayerDefault SAVED")
    write_recipe(D, res, fix, rb, sel_int)
    views = C.all_views()
    for vn in ("Face_Front", "Face_ThreeQuarter", "JawClose", "Body_Front", "Head_Back34"):
        yield from shoot(scene, f"build_{vn}.png", views[vn])
    C.release_actor(scene, actor, ch)
    step("build done")


STUDIO_VIEWS = ["Face_Front", "Face_ThreeQuarter", "Face_Profile", "Body_Front", "Body_Side", "Body_Back",
                "Hand_xneg_Front", "Hand_xneg_Outer", "Hand_xpos_Front", "Hand_xpos_Outer",
                "JawClose", "JawLow", "JawRamus", "EarR", "EarRSide", "Shoulders_Front", "Shoulders_High",
                "ShoulderL_TQ", "ShoulderR_TQ", "Shoulders_Back", "Eyes", "Head_Back34", "Head_Top", "Head_Back_Far"]
VARIANT_VIEWS = [("bounce", ["Face_Front", "Face_ThreeQuarter", "JawClose", "JawLow"]),
                 ("rimshadow", ["Face_Front", "EarR"]),
                 ("rimspec0", ["Face_Front", "EarR"]),
                 ("norim", ["Face_Front", "EarR"]),
                 ("eval", ["Face_Front", "Face_ThreeQuarter", "Face_Profile", "JawClose", "EarR", "Shoulders_Front",
                           "Body_Front", "Head_Back34"]),
                 ("ambient", ["Face_Front", "Face_ThreeQuarter", "Face_Profile", "JawClose", "JawLow", "JawRamus",
                              "EarR", "Body_Front", "Body_Back", "Head_Back_Far"]),
                 ("headlight", ["Face_ThreeQuarter", "JawClose", "JawRamus"]),
                 ("base", ["Face_Front", "Face_ThreeQuarter", "JawClose", "EarR", "EarRSide", "Shoulders_Front",
                           "Shoulders_High", "ShoulderL_TQ", "ShoulderR_TQ", "Shoulders_Back"])]


def shoot_set(scene: C.Scene, prefix: str):
    views = C.all_views()
    yield from switch(scene, "studio")
    for vn in STUDIO_VIEWS:
        yield from shoot(scene, f"{prefix}{vn}.png", views[vn])
    for variant, names in VARIANT_VIEWS:
        yield from switch(scene, variant)
        for vn in names:
            yield from shoot(scene, f"{prefix}{vn}_{variant}.png", views[vn])
    yield from switch(scene, "studio")


def hair_visible(scene: C.Scene) -> dict:
    """Capture the Face_Front view (studio) and sample the crown: the BrushCut renders near-black there, the bald
    scalp renders as lit skin. Round-2 verify 1 showed the saved asset can come up with the hair groom bound but not
    drawn ('Waiting for groom bindings to be ready 0/1 (Hair_S_BrushCut)')."""
    loc, look, fov = C.all_views()["Face_Front"]
    scene.aim(loc, look, fov)
    scene.apply_hidden()
    scene.capture.capture_scene()
    lum = []
    for x in range(420, 581, 40):            # crown of the Face_Front shot (round-1 captures: hair median luma 58,
        for y in range(310, 391, 20):        # bald FaceC 142, bald round-2 verify-1 130)
            c = ue.RenderingLibrary.read_render_target_pixel(scene.world, scene.rt, x, y)
            lum.append(0.299 * c.r + 0.587 * c.g + 0.114 * c.b)
    lum.sort()
    med = lum[len(lum) // 2]
    return {"crown_luma_median": round(med, 1), "hair": med < 95.0}


def wait_for_hair(scene: C.Scene, ch, max_seconds: float = 300.0):
    """Wait (re-assembling the preview every 30 s) until the hair groom is drawn; records the evidence."""
    t0 = C.time.monotonic()
    probes = []
    n = 0
    while True:
        yield from C.settle()
        pr = hair_visible(scene)
        pr["t_s"] = round(C.time.monotonic() - t0, 1)
        probes.append(pr)
        if pr["hair"] or C.time.monotonic() - t0 > max_seconds:
            break
        n += 1
        if n % 6 == 0:
            C.mhs().assemble_for_preview(ch)
            pr["reassembled"] = True
        yield from warmup(60, 4.0)
    C.REPORT.setdefault("hair_wait", []).append(probes)
    check("hair_drawn_before_captures", probes[-1]["hair"], probes=probes[-4:], n=len(probes))


def hairlook_job(scene: C.Scene):
    """Saves nothing. The saved MH_PlayerDefault from behind with the rim light on / specular-free / off, to isolate
    why the short hair reads copper and patchy from behind in the studio rig (round-1 verifier note)."""
    pd = ue.load_asset(C.PD_PATH)
    C.open_edit(pd)
    actor = C.spawn(pd)
    scene.show_only(actor, [actor])
    yield from warmup(300, 15.0)
    yield from wait_for_hair(scene, pd)
    C.REPORT["hairlook"] = {"groom_params": {s: C.instance_params(C.mhs().get_preview_collection(pd), k[1])
                                             for s, k in C.selections(C.mhs().get_preview_collection(pd)).items()
                                             if s in ("Hair", "Eyebrows")}}
    views = C.all_views()
    for variant in ("studio", "rimspec0", "norim", "ambient"):
        yield from switch(scene, variant)
        for vn in ("Body_Back", "Shoulders_Back", "Head_Back34", "Head_Back_Far"):
            yield from shoot(scene, f"hl_{vn}_{variant}.png", views[vn])
    C.release_actor(scene, actor, pd)
    step("hairlook done (nothing saved)")


def verify_job(scene: C.Scene):
    D = C.offline_coeff_data()
    build = json.loads(Path(str(BUILD_REPORT_FOR_VERIFY).format(attempt=os.environ.get("PD_BUILD_ATTEMPT", "1")))
                       .read_text(encoding="utf-8"))["build"]
    res = C.REPORT.setdefault("verify", {"build_report": str(BUILD_REPORT_FOR_VERIFY)})
    lay = C.PFB.layout(D["base"])
    # ---------------- A) MH_PlayerDefault as saved (FIRST MetaHuman of the session: grooms render) ----------------
    pd = ue.load_asset(C.PD_PATH)
    if not isinstance(pd, ue.MetaHumanCharacter):
        raise RuntimeError(f"{C.PD_PATH} did not load as a MetaHumanCharacter")
    res["disk_settings"] = C.character_settings(pd)
    res["disk_internal_collection"] = C.collection_inventory(pd.get_editor_property("internal_collection"))
    rb = identity_readback(pd)
    res["disk_identity"] = rb
    oks = identity_ok(rb, C.selections(pd.get_editor_property("internal_collection")))
    check("disk_identity", all(oks.values()), detail=oks)
    C.open_edit(pd)
    c = C.coeffs(pd)
    res["coeffs"] = c
    res["coeffs_maxdiff_vs_build_final"] = C.max_abs_diff(c, build["coeffs_final"])
    check("face_coeffs_equal_build", res["coeffs_maxdiff_vs_build_final"] == 0.0,
          maxdiff=res["coeffs_maxdiff_vs_build_final"])
    res["coeffs_maxdiff_vs_facec"] = C.max_abs_diff(c, D["facec_coeffs"])
    res["regions_changed_vs_facec"] = region_changes(c, D["facec_coeffs"], lay)
    res["eval_settings"] = C.eval_settings(pd)
    check("face_eval_settings_equal_facec", res["eval_settings"] == D["facec_eval"], got=res["eval_settings"])
    lm = C.landmarks(pd)
    res["landmarks"] = lm
    res["landmark_deltas_vs_facec"] = {str(i): [round(a - b, 4) for a, b in zip(p, q)]
                                       for i, (p, q) in enumerate(zip(lm, D["facec_landmarks"]))
                                       if max(abs(a - b) for a, b in zip(p, q)) > 1e-3}
    res["constraints"] = C.constraints(pd)
    dcon = max(abs(res["constraints"][k]["value"] - float(v)) for k, v in D["ref_constraints"].items())
    res["constraints_maxdiff_vs_playerbase_build_ref"] = dcon
    check("body_constraints_equal_playerbase", dcon < 2e-3, maxdiff=dcon)
    res["can_build_meta_human"] = bool(C.mhs().can_build_meta_human(pd, False))
    C.write_report()
    actor = C.spawn(pd)
    scene.show_only(actor, [actor])
    yield from warmup(300, 15.0)
    yield from wait_for_hair(scene, pd)
    col = C.mhs().get_preview_collection(pd)
    sel = C.selections(col)
    res["preview_collection"] = C.collection_inventory(col)
    res["groom_params"] = {slot: C.instance_params(col, k[1]) for slot, k in sel.items() if slot in GROOM_PARAMS}
    res["grooms"] = C.groom_state(actor)
    res["eye_mids"] = C.eye_mid_params(actor)
    gp = groom_params_ok(res["groom_params"])
    check("groom_params_persisted", all(gp.values()), detail=gp)
    vis = {r["name"]: r["visible"] for r in res["grooms"] if r["groom"]}
    check("grooms_bound_and_visible", len(vis) >= 3 and all(vis.values()), grooms=vis)
    em = res["eye_mids"]
    check("eye_materials_match", len(em) == 2 and len({json.dumps(v, sort_keys=True) for v in em.values()}) == 1, eye_mids=em)
    res["bones"] = C.bone_positions(actor)
    res["dump_Body"] = C.dump_mesh(C.find_component(actor, "Body"), "R2_PD_Body")
    res["dump_Face"] = C.dump_mesh(C.find_component(actor, "Face"), "R2_PD_Face")
    C.write_report()
    yield from shoot_set(scene, "after_")
    yield from C.shoot_ortho(scene, "after_")
    C.release_actor(scene, actor, None)   # keep PD open for the state comparisons below
    yield from warmup(30, 1.0)

    # ---------------- B) FaceC (scratch duplicate, never saved) = BEFORE ----------------
    fc = C.scratch_dup(C.FACEC_PATH, "PD_R2_Before_FaceC")
    C.open_edit(fc)
    res["facec_dup_coeffs_maxdiff_vs_build"] = C.max_abs_diff(C.coeffs(fc), D["facec_coeffs"])
    for tol in (0.0, 1e-3, 0.1):
        res.setdefault("compare_face_state_pd_vs_facec", {})[str(tol)] = bool(C.mhs().compare_face_state(pd, fc, tol))
        res.setdefault("compare_body_state_pd_vs_facec", {})[str(tol)] = bool(C.mhs().compare_body_state(pd, fc, tol))
    step("state comparisons vs FaceC", face=res["compare_face_state_pd_vs_facec"], body=res["compare_body_state_pd_vs_facec"])
    fa = C.spawn(fc)
    scene.show_only(fa, [fa])
    yield from warmup(240, 12.0)
    res["facec_bones"] = C.bone_positions(fa)
    res["facec_dump_Body"] = C.dump_mesh(C.find_component(fa, "Body"), "R2_FaceC_Body")
    res["facec_dump_Face"] = C.dump_mesh(C.find_component(fa, "Face"), "R2_FaceC_Face")
    yield from shoot_set(scene, "before_")
    yield from C.shoot_ortho(scene, "before_")
    C.release_actor(scene, fa, fc)
    yield from warmup(30, 1.0)

    # ---------------- C) MH_PlayerBase (scratch duplicate, never saved): body reference ----------------
    pb = C.scratch_dup(C.BASE_PATH, "PD_R2_Ref_PlayerBase")
    C.open_edit(pb)
    for tol in (0.0, 1e-5, 1e-3):
        res.setdefault("compare_body_state_pd_vs_playerbase", {})[str(tol)] = bool(C.mhs().compare_body_state(pd, pb, tol))
    check("compare_body_state_pd_vs_playerbase_tol0", res["compare_body_state_pd_vs_playerbase"]["0.0"],
          detail=res["compare_body_state_pd_vs_playerbase"])
    res["playerbase_constraints"] = C.constraints(pb)
    cd = {k: (res["constraints"][k]["value"], v["value"], res["constraints"][k]["active"] == v["active"])
          for k, v in res["playerbase_constraints"].items()}
    res["constraints_vs_playerbase_maxdiff"] = max(abs(a - b) for a, b, _ in cd.values())
    check("constraints_equal_playerbase", res["constraints_vs_playerbase_maxdiff"] == 0.0 and all(x for _, _, x in cd.values()),
          n=len(cd), maxdiff=res["constraints_vs_playerbase_maxdiff"])
    pa = C.spawn(pb)
    scene.show_only(pa, [pa])
    yield from warmup(150, 8.0)
    res["playerbase_bones"] = C.bone_positions(pa)
    res["playerbase_dump_Body"] = C.dump_mesh(C.find_component(pa, "Body"), "R2_PlayerBase_Body")
    bd = [max(abs(a - b) for a, b in zip(res["bones"][k], res["playerbase_bones"][k]))
          for k in res["bones"] if k in res["playerbase_bones"]]
    res["bones_compared"] = len(bd)
    res["bones_maxdiff_vs_playerbase_cm"] = max(bd) if bd else None
    check("bones_equal_playerbase", bool(bd) and len(bd) == len(res["bones"]) and max(bd) < 1e-3,
          n=len(bd), maxdiff=res["bones_maxdiff_vs_playerbase_cm"])
    yield from shoot(scene, "ref_PlayerBase_Body_Front.png", C.all_views()["Body_Front"])
    C.release_actor(scene, pa, pb)
    C.close_edit(pd)
    step("verify done (nothing saved)")


def main() -> None:
    with open(C.STEP_LOG, "a", encoding="utf-8") as fh:
        fh.write(f"\n===== pd_r2.py mode={C.MODE} attempt={C.ATTEMPT} {C._now()} =====\n")
    C.assert_locks()
    if not C.REPORT["engine"].startswith("5.8"):
        raise RuntimeError(f"expected UE 5.8.x, got {C.REPORT['engine']}")
    C.REPORT["sha_start"] = C.protected_hashes()
    scene = C.Scene()
    step("scene ready")
    jobs = {"explore": explore_job, "explore2": explore2_job, "explore3": explore3_job, "build": build_job,
            "verify": verify_job, "hairlook": hairlook_job}
    if C.MODE not in jobs:
        raise ValueError(f"unknown PD_MODE {C.MODE}")
    C.Runner(scene, jobs[C.MODE](scene)).start()


try:
    main()
except Exception:  # noqa: BLE001
    C.REPORT["error"] = traceback.format_exc()
    try:
        step("ERROR in main", error=C.REPORT["error"])
    except Exception:  # noqa: BLE001
        pass
    ue.log_error(C.REPORT["error"])
    for _ch in list(C.EDITED):
        try:
            C.close_edit(_ch)
        except Exception:  # noqa: BLE001
            pass
    C.REPORT["status"] = "failed"
    C.write_report()
    ue.SystemLibrary.quit_editor()
