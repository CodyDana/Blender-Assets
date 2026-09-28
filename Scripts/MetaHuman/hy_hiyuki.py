"""hy_hiyuki.py -- PRIVATE / DO NOT SHIP capability test: how close can a MetaHuman get to Hiyuki (Wuthering Waves)?
Runs INSIDE UnrealEditor on Exports/CharacterLab/Unreal/CharacterLab.uproject; launch with
Scripts/MetaHuman/hy_run.ps1 -Mode <mode>.

Target asset: /Game/Characters/MetaHumans/MH_Hiyuki_Private (a separate duplicate of the Aera preset). MH_PlayerFemale
and MH_PlayerDefault are NEVER opened for edit or saved; the female's face is reused only as coefficient NUMBERS read
from WorkFiles/MetaHuman/player_female/player_female_recipe.json.

Modes (HY_MODE):
  explore1  saves NOTHING. Scratch duplicate under /Game/HiyukiPrivate/Scratch: female v2 face as the base, then
            graded landmark sculpts towards her proportions (H1/H2/H3), iris tint, hair/brow/lash colour, makeup.
  explore2  saves NOTHING. Hairstyle candidates on the chosen face.
  build     makes + saves MH_Hiyuki_Private from FINAL.
  verify    fresh session: reload the saved asset, check identity, capture the comparison set.
Reuses pf_common (scene, cameras, MetaHuman helpers) with its output globals redirected here.
Never signs in; never calls request_auto_rigging / request_texture_sources / build_meta_human.
"""
from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/MetaHuman")
import unreal as ue  # noqa: E402

import pf_common as C  # noqa: E402

# ---- redirect pf_common's outputs to the private folder (module globals are read at call time) ----
MODE = os.environ.get("HY_MODE", "explore1").strip().lower()
ATTEMPT = os.environ.get("HY_ATTEMPT", "1").strip()
C.MODE, C.ATTEMPT = MODE, ATTEMPT
C.OUT = C.ROOT / "WorkFiles/MetaHuman/hiyuki_private"
C.CAPTURES = C.OUT / f"{MODE}_captures"
C.REPORT_PATH = C.OUT / f"hy_{MODE}_{ATTEMPT}.json"
C.STEP_LOG = C.OUT / "hiyuki_private.log"
C.PF_NAME = "MH_Hiyuki_Private"
C.PF_PATH = f"{C.CHAR_DIR}/{C.PF_NAME}"
C.SCRATCH = "/Game/HiyukiPrivate/Scratch"
C.PROTECTED = C.PROTECTED + ["MH_PlayerFemale"]
C.REPORT.update({"script": "Scripts/MetaHuman/hy_hiyuki.py", "mode": MODE, "attempt": ATTEMPT,
                 "private": "PRIVATE / DO NOT SHIP"})

from pf_common import step, warn, check, warmup, shoot  # noqa: E402

FEMALE_RECIPE = C.ROOT / "WorkFiles/MetaHuman/player_female/player_female_recipe.json"
BASE_PRESET = "Aera"
BODY = {"Height": 168.0, "Chest": 93.5, "Underbust": 72.0, "Waist": 60.5, "Hip": 96.5}   # female v2 body (BD)
GLASS_ACCENTS = {"lips": {"saturation": 0.35, "redness": 0.45},
                 "under_eye": {"redness": 0.2, "saturation": 0.3, "lightness": 0.6}}
FIRST_HAIR = "WI_Hair_L_StraightBangs"
FIRST_BROWS = "WI_Eyebrows_M_Thin"


# ------------------------------------------------------------------------------------------------------------------
# landmark sculpt towards her proportions (UE cm: x lateral, -X = character's right; y forward; z up)
# ------------------------------------------------------------------------------------------------------------------
R_EYE = [22, 51, 44, 52, 33, 53]      # outer canthus, upper lid outer->inner, inner canthus, lower lid
L_EYE = [18, 35, 20, 36, 19, 37]
R_BROW, L_BROW = [78, 10, 77], [25, 26, 24]
UPPER_LIDS = ([51, 44, 52], [35, 20, 36])
LOWER_LIDS = ([53], [37])
MOUTH_ALL = [5, 47, 31, 49, 34, 50, 9, 16, 4, 48, 32]


def pair(r, l, dx_out=0.0, dy=0.0, dz=0.0):
    """right/left landmark lists moved dx_out OUTWARD (negative = inward), same dy/dz."""
    return [(i, (-dx_out, dy, dz)) for i in r] + [(i, (dx_out, dy, dz)) for i in l]


def mid(idx, dy=0.0, dz=0.0):
    return [(i, (0.0, dy, dz)) for i in idx]


def hy_moves(s: float) -> list:
    """(idx, (dx,dy,dz)) list; s = strength. Targets from the reference measurement (IPD-normalised):
    eyes wider apart + more open, brows higher, nose shorter/smaller, mouth higher + much narrower,
    chin much shorter, V-line jaw."""
    m = []
    m += pair(R_EYE, L_EYE, dx_out=0.25 * s)                                    # wider-set eyes
    m += pair(R_BROW, L_BROW, dx_out=0.18 * s)
    m += pair(*UPPER_LIDS, dz=0.10 * s) + pair(*LOWER_LIDS, dz=-0.06 * s)        # bigger opening
    m += pair([22], [18], dx_out=0.05 * s)
    m += pair([10], [26], dz=0.20 * s) + pair([77], [24], dz=0.12 * s) + pair([78], [25], dz=0.15 * s)
    m += mid([64], dy=-0.12 * s, dz=0.20 * s) + mid([65], dz=0.20 * s)          # shorter, smaller nose
    m += pair([67], [45], dx_out=-0.12 * s, dz=0.20 * s) + pair([70], [74], dx_out=-0.06 * s)
    m += mid([5, 47, 31, 49, 34, 50, 9, 16, 4], dz=0.35 * s)                     # mouth up ...
    m += pair([48], [32], dx_out=-0.35 * s, dz=0.35 * s)                         # ... and much narrower
    m += pair([49], [34], dx_out=-0.12 * s) + pair([47], [31], dx_out=-0.10 * s) + pair([9], [16], dx_out=-0.10 * s)
    m += pair([11], [17], dx_out=-0.05 * s, dz=0.20 * s)
    m += mid([62, 8], dz=0.60 * s)                                               # much shorter chin
    m += pair([3], [30], dx_out=-0.20 * s, dz=0.45 * s)                          # V-line
    m += pair([63], [43], dx_out=-0.30 * s, dz=0.30 * s)
    m += pair([1], [28], dx_out=-0.30 * s, dz=0.15 * s)
    m += pair([2], [29], dx_out=-0.15 * s)
    m += pair([68], [46], dx_out=-0.20 * s, dz=0.30 * s)
    return m


def merged(moves) -> list:
    """sum duplicate indices -> one translate_face_landmarks stage in pf_common's 'd_per' format."""
    acc = {}
    for i, d in moves:
        a = acc.setdefault(i, [0.0, 0.0, 0.0])
        for k in range(3):
            a[k] += d[k]
    idx = sorted(acc)
    return [{"idx": idx, "d_per": [acc[i] for i in idx]}]


def extra_moves(s: float) -> list:
    """explore1 follow-up: eyes still read small, lips too full/wide -> bigger opening, thinner + narrower lips"""
    m = []
    m += pair(*UPPER_LIDS, dz=0.08 * s) + pair(*LOWER_LIDS, dz=-0.05 * s) + pair([22], [18], dx_out=0.04 * s)
    m += mid([5], dz=-0.10 * s) + pair([47], [31], dz=-0.08 * s)                  # thinner upper lip
    m += mid([4], dz=0.12 * s) + pair([9], [16], dz=0.10 * s)                      # thinner lower lip
    m += pair([48], [32], dx_out=-0.15 * s) + pair([49], [34], dx_out=-0.06 * s)   # narrower
    return m


def idol_moves(s: float) -> list:
    """v2 (user 2026-09-27: 'attractive idol ... eyes way too far apart, nose too big', 'maybe a kpop idol'):
    an ORIGINAL K-pop-idol-style face on the female v2 base -- eyes slightly closer + more open, small slim nose,
    straighter brows, slimmer lips, soft V-line. No Hiyuki spacing/lower-face distortion."""
    m = []
    m += pair(R_EYE, L_EYE, dx_out=-0.06 * s) + pair(R_BROW, L_BROW, dx_out=-0.04 * s)   # eyes a touch closer
    m += pair(*UPPER_LIDS, dz=0.06 * s) + pair(*LOWER_LIDS, dz=-0.03 * s) + pair([22], [18], dx_out=0.02 * s)
    m += pair([67], [45], dx_out=-0.10 * s, dz=0.05 * s) + pair([70], [74], dx_out=-0.06 * s)  # small slim nose
    m += pair([57], [40], dx_out=-0.05 * s) + mid([64], dy=-0.10 * s, dz=0.05 * s) + mid([65], dz=0.05 * s)
    m += pair([48], [32], dx_out=-0.08 * s) + mid([5], dz=-0.04 * s) + mid([4], dz=0.05 * s)   # slimmer lips
    m += pair([1], [28], dx_out=-0.10 * s) + pair([63], [43], dx_out=-0.08 * s)             # soft V-line
    m += pair([3], [30], dx_out=-0.05 * s) + mid([62, 8], dz=0.10 * s)
    m += pair([10], [26], dz=-0.05 * s) + pair([77], [24], dz=0.02 * s)                     # straighter brows
    return m


# name -> list of stages (each stage = one translate_face_landmarks call); a float = hy_moves(s), ("x", s) = extra
VARIANTS = {"H0": [], "H1": [1.0], "H2": [1.6], "H3": [1.6, 1.6], "H4": [2.5, 2.5],
            "H3x": [1.6, 1.6, ("x", 1.5)], "H3xx": [1.6, 1.6, ("x", 1.5), ("x", 1.5)],
            "H4x": [2.5, 2.5, ("x", 1.5)],
            "K1": [("i", 1.0)], "K2": [("i", 1.6)], "K3": [("i", 1.6), ("i", 1.6)], "K4": [("i", 2.4), ("i", 2.4)]}


def ratios(lm) -> dict:
    """the IPD-normalised proportions used in the feasibility table"""
    P = lambda i: lm[i]  # noqa: E731
    ipd = abs((P(22)[0] + P(33)[0]) / 2 - (P(18)[0] + P(19)[0]) / 2)
    eyez = (P(22)[2] + P(33)[2] + P(18)[2] + P(19)[2]) / 4
    ew = abs(P(18)[0] - P(19)[0])
    return {"ipd_cm": round(ipd, 3), "eyechin_ipd": round((eyez - P(8)[2]) / ipd, 3), "ew_ipd": round(ew / ipd, 3),
            "open_w": round((P(44)[2] - P(53)[2]) / ew, 3), "icd_ew": round(abs(P(19)[0] - P(33)[0]) / ew, 3),
            "mouth_ipd": round(abs(P(32)[0] - P(48)[0]) / ipd, 3),
            "mouthchin_ipd": round((P(50)[2] - P(8)[2]) / ipd, 3),
            "eyenose_ipd": round((eyez - P(64)[2]) / ipd, 3),
            "jaw_ipd": round(abs(P(1)[0] - P(28)[0]) / ipd, 3),
            "brow_eye_ipd": round((P(10)[2] - eyez) / ipd, 3)}


def apply_variant(ch, base_coeffs, stages) -> list:
    C.set_coeffs(ch, base_coeffs)
    flat = []
    for k, s in enumerate(stages):
        flat.append([f"stage{k}", s])
        if isinstance(s, (tuple, list)):
            moves = idol_moves(s[1]) if s[0] == "i" else extra_moves(s[1])
        else:
            moves = hy_moves(s)
        C.translate_landmarks(ch, merged(moves))
    return flat


# ------------------------------------------------------------------------------------------------------------------
# identity pieces
# ------------------------------------------------------------------------------------------------------------------
def commit_lashes(ch, type_name="LONG_SLIGHT_CURL", melanin=0.9) -> None:
    hm = ch.get_editor_property("head_model_settings")
    el = hm.get_editor_property("eyelashes")
    el.set_editor_property("type", getattr(ue.MetaHumanCharacterEyelashesType, type_name))
    el.set_editor_property("enable_grooms", True)
    el.set_editor_property("melanin", float(melanin))
    hm.set_editor_property("eyelashes", el)
    C.mhs().commit_head_model_settings(ch, hm)


def makeup(lip_type="NATURAL", lip_opacity=0.3, lip_rough=0.7, lip_color=(0.55, 0.12, 0.16),
           blush_type="APPLE", blush=0.3, blush_color=(0.7, 0.12, 0.15), liner=0.45,
           eye_type="THIN_LINER", eye_primary=(0.02, 0.012, 0.01)):
    m = ue.MetaHumanCharacterMakeupSettings()
    lips = ue.MetaHumanCharacterLipsMakeupProperties()
    lips.type = getattr(ue.MetaHumanCharacterLipsMakeupType, lip_type)
    lips.color = ue.LinearColor(*lip_color, 1.0)
    lips.opacity = lip_opacity
    lips.roughness = lip_rough
    lips.metalness = 0.0
    eyes = ue.MetaHumanCharacterEyeMakeupProperties()
    eyes.type = getattr(ue.MetaHumanCharacterEyeMakeupType, eye_type)
    eyes.primary_color = ue.LinearColor(*eye_primary, 1.0)
    eyes.secondary_color = ue.LinearColor(0.0, 0.0, 0.0, 1.0)
    eyes.opacity = liner
    eyes.roughness = 0.75
    eyes.metalness = 0.0
    m.lips = lips
    m.eyes = eyes
    if blush > 0:
        b = ue.MetaHumanCharacterBlushMakeupProperties()
        b.type = getattr(ue.MetaHumanCharacterBlushMakeupType, blush_type)
        b.color = ue.LinearColor(*blush_color, 1.0)
        b.intensity = blush
        b.roughness = 0.6
        m.blush = b
    return m


def commit_iris(ch, tint=None, saturation=None, cornea_size=None, limbal=None, sclera_custom_tint=False,
                primary_uv=None) -> dict:
    eyes = ch.get_editor_property("eyes_settings")
    for side in ("eye_left", "eye_right"):
        e = eyes.get_editor_property(side)
        ir = e.get_editor_property("iris")
        if tint is not None:
            ir.set_editor_property("global_tint", ue.LinearColor(*tint, 1.0))
        if saturation is not None:
            ir.set_editor_property("global_saturation", float(saturation))
        if limbal is not None:
            ir.set_editor_property("limbal_ring_color", ue.LinearColor(*limbal, 1.0))
        if primary_uv is not None:
            ir.set_editor_property("primary_color_u", float(primary_uv[0]))
            ir.set_editor_property("primary_color_v", float(primary_uv[1]))
            ir.set_editor_property("secondary_color_u", float(primary_uv[0]))
            ir.set_editor_property("secondary_color_v", float(primary_uv[1]))
        e.set_editor_property("iris", ir)
        if cornea_size is not None:
            co = e.get_editor_property("cornea")
            co.set_editor_property("size", float(cornea_size))
            e.set_editor_property("cornea", co)
        sc = e.get_editor_property("sclera")
        sc.set_editor_property("use_custom_tint", bool(sclera_custom_tint))
        e.set_editor_property("sclera", sc)
        eyes.set_editor_property(side, e)
    C.mhs().commit_eyes_settings(ch, eyes)
    return C.struct_dict(ch.get_editor_property("eyes_settings").get_editor_property("eye_left"))


def set_groom_colours(ch, params: dict) -> dict:
    col = C.mhs().get_preview_collection(ch)
    sel = C.selections(col)
    done = {}
    for slot, want in params.items():
        if slot in sel:
            for n, val in want.items():
                done[f"{slot}.{n}"] = C.set_groom_param(col, sel[slot][1], n, val)
    C.mhs().on_edit_preview_collection(ch)
    return done


def groom_params(ch) -> dict:
    col = C.mhs().get_preview_collection(ch)
    return {s: C.instance_params(col, k[1]) for s, k in C.selections(col).items()
            if s in ("Hair", "Eyebrows", "Eyelashes")}


def enum_names(cls) -> list:
    out = []
    for n in dir(cls):
        if n.isupper() and not n.startswith("_"):
            out.append(n)
    return out


def set_body(ch, want: dict) -> dict:
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


def clear_internal_outfit(ch) -> None:
    ic = ch.get_editor_property("internal_collection")
    ic.get_editor_property("default_instance").set_single_slot_selection("Outfits", ue.MetaHumanPaletteItemKey())


def wait_hair(scene, ch, fc, max_seconds=600.0):
    """crown above the forehead renders dark while the hair still has its default (dark) colour"""
    V = C.views(fc, 168.0)
    t0 = C.time.monotonic()
    probes = []
    n = 0
    while True:
        loc, look, fov = V["Hair_Front_High"]
        scene.aim(loc, look, fov)
        yield from C.settle()
        scene.capture.capture_scene()
        lum = C.region_luma(scene, 450, 550, 360, 420)
        probes.append(round(lum, 1))
        if lum < 70 or C.time.monotonic() - t0 > max_seconds:
            break
        n += 1
        if n % 6 == 0:
            C.mhs().assemble_for_preview(ch)
        yield from warmup(60, 4.0)
    return probes


FEMALE = json.loads(FEMALE_RECIPE.read_text(encoding="utf-8"))
BASE_COEFFS = FEMALE["face"]["coeffs_final"]
DARK = {"Hair": {"Melanin": 0.9, "Redness": 0.05}, "Eyebrows": {"Melanin": 0.9}, "Eyelashes": {"Melanin": 0.9}}
SILVER = {"Hair": {"Melanin": 0.0, "Redness": 0.0, "Whiteness": 1.0},
          "Eyebrows": {"Melanin": 0.0, "Redness": 0.0, "Whiteness": 1.0},
          "Eyelashes": {"Melanin": 0.25}}
HAIR_COLOURS = {
    "C1": SILVER,
    "C2": {"Hair": {"Melanin": 0.05, "Redness": 0.0, "Whiteness": 0.85, "Lightness": 1.0}},
    "C3": {"Hair": {"Melanin": 0.0, "Redness": 0.0, "Whiteness": 0.7}},
}
IRIS = {"I1": {"tint": (1.0, 0.12, 0.14), "saturation": 2.0},
        "I2": {"tint": (1.0, 0.05, 0.08), "saturation": 2.0, "cornea_size": 0.19},
        "I3": {"tint": (1.0, 0.18, 0.22), "saturation": 1.6, "cornea_size": 0.20, "limbal": (0.35, 0.05, 0.06)}}
MAKEUP = {"M1": {},
          "M2": {"blush": 0.45, "blush_color": (0.75, 0.1, 0.14), "lip_opacity": 0.4},
          "M3": {"blush": 0.35, "liner": 0.6, "lip_type": "CUPID", "lip_opacity": 0.35}}


# ================================================================================================================
def explore1_job(scene: C.Scene):
    res = C.REPORT.setdefault("explore1", {})
    res["enums"] = {n: enum_names(getattr(ue, n)) for n in (
        "MetaHumanCharacterEyelashesType", "MetaHumanCharacterEyeMakeupType", "MetaHumanCharacterBlushMakeupType",
        "MetaHumanCharacterLipsMakeupType")}
    ex = C.scratch_dup(f"{C.PRESET_SRC}/{BASE_PRESET}", "HY_X1")
    res["hair"] = C.set_internal_slot(ex, "Hair", f"{C.GROOM_ROOT}/Hair/{FIRST_HAIR}")
    res["brows"] = C.set_internal_slot(ex, "Eyebrows", f"{C.GROOM_ROOT}/Eyebrows/{FIRST_BROWS}")
    clear_internal_outfit(ex)
    C.open_edit(ex)
    res["body_got"] = set_body(ex, BODY)
    C.set_coeffs(ex, BASE_COEFFS)
    C.mhs().commit_face_state(ex)
    lm0 = C.landmarks(ex)
    dl = max(max(abs(a - b) for a, b in zip(p, q)) for p, q in zip(lm0, FEMALE["face"]["landmarks_final"]))
    res["base_landmark_maxdiff_vs_female_cm"] = round(dl, 4)
    res["skin"] = C.commit_skin(ex, u=0.0, v=0.8, face_texture_index=49, accents=GLASS_ACCENTS)
    commit_lashes(ex, "LONG_SLIGHT_CURL", 0.9)
    C.mhs().commit_makeup_settings(ex, makeup())
    actor = C.spawn(ex)
    scene.show_only(actor, [actor])
    yield from warmup(300, 15.0)
    set_groom_colours(ex, DARK)
    C.mhs().assemble_for_preview(ex)
    yield from warmup(120, 6.0)
    fc = C.face_center_from_landmarks(lm0)
    res["hair_probe"] = yield from wait_hair(scene, ex, fc, 900.0)
    res["groom_params_default"] = groom_params(ex)
    res["silver_set"] = set_groom_colours(ex, SILVER)
    res["iris_I1"] = commit_iris(ex, **IRIS["I1"])
    yield from warmup(120, 6.0)
    res["groom_params_silver"] = groom_params(ex)
    res["grooms"] = C.groom_state(actor)
    # ---- face variants ----
    res["variants"] = {}
    for name, stages in VARIANTS.items():
        flat = apply_variant(ex, BASE_COEFFS, stages)
        yield from warmup(60, 2.5)
        lm = C.landmarks(ex)
        res["variants"][name] = {"stages": flat, "ratios": ratios(lm), "landmarks": lm, "coeffs": C.coeffs(ex)}
        step(f"variant {name}", **ratios(lm))
        V = C.views(C.face_center_from_landmarks(lm), 168.0)
        for vn in ("Face_Front", "Face_TQ_L", "Face_TQ_R", "Face_Profile_L", "Face_Close"):
            yield from shoot(scene, f"v_{name}_{vn}.png", V[vn])
    # ---- on H3: iris, hair colour, makeup ----
    apply_variant(ex, BASE_COEFFS, VARIANTS["H3"])
    yield from warmup(60, 2.5)
    V = C.views(C.face_center_from_landmarks(C.landmarks(ex)), 168.0)
    res["iris"] = {}
    for name, kw in IRIS.items():
        res["iris"][name] = commit_iris(ex, **kw)
        yield from warmup(90, 4.0)
        for vn in ("Eyes", "Face_Close"):
            yield from shoot(scene, f"i_{name}_{vn}.png", V[vn])
    commit_iris(ex, **IRIS["I1"], cornea_size=0.1742)
    res["hair_colour"] = {}
    for name, params in HAIR_COLOURS.items():
        res["hair_colour"][name] = set_groom_colours(ex, params)
        yield from warmup(90, 4.0)
        for vn in ("Face_Front", "Hair_Back34_L"):
            yield from shoot(scene, f"c_{name}_{vn}.png", V[vn])
    set_groom_colours(ex, SILVER)
    res["makeup"] = {}
    for name, kw in MAKEUP.items():
        C.mhs().commit_makeup_settings(ex, makeup(**kw))
        res["makeup"][name] = kw
        yield from warmup(90, 4.0)
        for vn in ("Face_Front", "Face_Close"):
            yield from shoot(scene, f"m_{name}_{vn}.png", V[vn])
    for label, (ltype, mel) in {"L1": ("LONG_SLIGHT_CURL", 0.25), "L2": ("LONG_SLIGHT_CURL", 0.6)}.items():
        commit_lashes(ex, ltype, mel)
        yield from warmup(90, 4.0)
        yield from shoot(scene, f"l_{label}_Eyes.png", V["Eyes"])
    C.release_actor(scene, actor, ex)
    step("explore1 done (nothing saved)")


# ================================================================================================================
# explore2: hairstyle candidates on the chosen face (each swap re-fits the groom, ~5-10 min)
# ================================================================================================================
IRIS2 = {"E1": {"tint": (1.3, 0.12, 0.15), "saturation": 2.0, "cornea_size": 0.19, "primary_uv": (0.9, 0.56)},
         "E2": {"tint": (1.3, 0.12, 0.15), "saturation": 2.0, "cornea_size": 0.19, "primary_uv": (0.712, 0.68)},
         "E3": {"tint": (1.5, 0.10, 0.14), "saturation": 2.0, "cornea_size": 0.19, "primary_uv": (0.5, 0.95)},
         "E4": {"tint": (1.5, 0.10, 0.14), "saturation": 2.0, "cornea_size": 0.19, "primary_uv": (0.9, 0.95),
                "limbal": (0.3, 0.03, 0.05)}}
MAKEUP2 = {"N1": {"blush_type": "HIGH_CURVE", "blush": 0.25, "blush_color": (0.8, 0.15, 0.2), "lip_opacity": 0.45,
                  "lip_color": (0.6, 0.1, 0.15), "liner": 0.5},
           "N2": {"blush_type": "LOW_SWEEP", "blush": 0.25, "blush_color": (0.8, 0.15, 0.2), "lip_opacity": 0.45,
                  "lip_color": (0.6, 0.1, 0.15), "liner": 0.5},
           "N3": {"blush_type": "ANGLED", "blush": 0.2, "blush_color": (0.8, 0.15, 0.2), "lip_opacity": 0.45,
                  "lip_color": (0.6, 0.1, 0.15), "liner": 0.5, "eye_type": "FULL_THIN_LINER"}}
BROWS2 = {"B1": {"Eyebrows": {"Melanin": 0.15, "Redness": 0.0, "Whiteness": 0.6}},
          "B2": {"Eyebrows": {"Melanin": 0.3, "Redness": 0.0, "Whiteness": 0.5}}}
FINAL = {   # picks from explore2 (2026-09-27): face H3xx, iris E4, blush N1 (0.3), brows B2, hair L_StraightBangs
    "face_variant": os.environ.get("HY_FACE", "H3xx"),
    "hair": FIRST_HAIR,
    "brows": FIRST_BROWS,
    "lashes": {"type": "LONG_SLIGHT_CURL", "melanin": 0.25},
    "skin": {"u": 0.0, "v": 0.8, "face_texture_index": 49, "accents": GLASS_ACCENTS},
    "iris": IRIS2["E4"],
    "makeup": dict(MAKEUP2["N1"], blush=0.3),
    "groom_params": {"Hair": SILVER["Hair"], "Eyebrows": BROWS2["B2"]["Eyebrows"], "Eyelashes": SILVER["Eyelashes"]},
    "body": BODY,
}
HAIR_TRIES = [h for h in os.environ.get("HY_HAIRS", "WI_Hair_L_StraightBangs,WI_Hair_S_Updo,WI_Hair_S_LowPonytail,"
                                                    "WI_Hair_M_SideSweptFringe")
              .split(",") if h]


def face_coeffs_for(ch, name: str) -> list:
    apply_variant(ch, BASE_COEFFS, VARIANTS[name])
    return C.coeffs(ch)


def dress(ch, final: dict, res: dict) -> None:
    """everything except hair colour (set after the groom is fitted) on a character open for edit"""
    res["body_got"] = set_body(ch, final["body"])
    if final["face_variant"] == "K4S4":        # v2 idol face: K4 coefficients x region scales S4 (explore3/4)
        C.set_coeffs(ch, scaled(idol_base(), SCALES["S4"]))
        res["face_moves"] = ["K4 coeffs from hy_explore3_1.json", SCALES["S4"]]
    else:
        res["face_moves"] = apply_variant(ch, BASE_COEFFS, VARIANTS[final["face_variant"]])
    C.mhs().commit_face_state(ch)
    sk = final["skin"]
    res["skin"] = C.commit_skin(ch, u=sk["u"], v=sk["v"], face_texture_index=sk["face_texture_index"],
                                accents=sk["accents"])
    commit_lashes(ch, final["lashes"]["type"], final["lashes"]["melanin"])
    C.mhs().commit_makeup_settings(ch, makeup(**final["makeup"]))
    res["eyes"] = commit_iris(ch, **final["iris"])


def explore2_job(scene: C.Scene):
    res = C.REPORT.setdefault("explore2", {"final": FINAL, "hairs": HAIR_TRIES})
    ex = C.scratch_dup(f"{C.PRESET_SRC}/{BASE_PRESET}", "HY_X2")
    res["hair_first"] = C.set_internal_slot(ex, "Hair", f"{C.GROOM_ROOT}/Hair/{HAIR_TRIES[0]}")
    res["brows"] = C.set_internal_slot(ex, "Eyebrows", f"{C.GROOM_ROOT}/Eyebrows/{FINAL['brows']}")
    clear_internal_outfit(ex)
    C.open_edit(ex)
    dress(ex, FINAL, res)
    lm = C.landmarks(ex)
    fc = C.face_center_from_landmarks(lm)
    V = C.views(fc, 168.0)
    actor = C.spawn(ex)
    scene.show_only(actor, [actor])
    yield from warmup(300, 15.0)
    # ---- first hair fitted: face follow-ups, iris, makeup, brow colour (fast; no re-fit) ----
    set_groom_colours(ex, DARK)
    C.mhs().assemble_for_preview(ex)
    yield from warmup(120, 6.0)
    first_probes = yield from wait_hair(scene, ex, fc, 900.0)
    set_groom_colours(ex, FINAL["groom_params"])
    yield from warmup(120, 6.0)
    res["faces"] = {}
    for name in ("H3", "H3x", "H3xx", "H4x"):
        apply_variant(ex, BASE_COEFFS, VARIANTS[name])
        yield from warmup(60, 2.5)
        lmv = C.landmarks(ex)
        res["faces"][name] = {"ratios": ratios(lmv), "coeffs": C.coeffs(ex)}
        step(f"face {name}", **ratios(lmv))
        Vv = C.views(C.face_center_from_landmarks(lmv), 168.0)
        for vn in ("Face_Front", "Face_TQ_L", "Face_Profile_L", "Face_Close"):
            yield from shoot(scene, f"f_{name}_{vn}.png", Vv[vn])
    apply_variant(ex, BASE_COEFFS, VARIANTS[FINAL["face_variant"]])
    yield from warmup(60, 2.5)
    res["iris"] = {}
    for name, kw in IRIS2.items():
        res["iris"][name] = commit_iris(ex, **kw)
        yield from warmup(90, 4.0)
        for vn in ("Eyes", "Face_Close"):
            yield from shoot(scene, f"e_{name}_{vn}.png", V[vn])
    commit_iris(ex, **FINAL["iris"])
    for name, kw in MAKEUP2.items():
        C.mhs().commit_makeup_settings(ex, makeup(**kw))
        yield from warmup(90, 4.0)
        for vn in ("Face_Front", "Face_Close"):
            yield from shoot(scene, f"n_{name}_{vn}.png", V[vn])
    C.mhs().commit_makeup_settings(ex, makeup(**FINAL["makeup"]))
    for name, gp in BROWS2.items():
        set_groom_colours(ex, gp)
        yield from warmup(90, 4.0)
        yield from shoot(scene, f"b_{name}_Face_Close.png", V["Face_Close"])
    set_groom_colours(ex, FINAL["groom_params"])
    res["hair"] = {HAIR_TRIES[0]: {"probes": first_probes}}
    for k, wi in enumerate(HAIR_TRIES):
        try:
            probes = res["hair"].get(wi, {}).get("probes")
            if k > 0:
                C.set_preview_slot(ex, "Hair", f"{C.GROOM_ROOT}/Hair/{wi}")
                set_groom_colours(ex, {"Hair": DARK["Hair"]})
                C.mhs().assemble_for_preview(ex)
                yield from warmup(120, 6.0)
                probes = yield from wait_hair(scene, ex, fc, 900.0)
            set_groom_colours(ex, FINAL["groom_params"])
            yield from warmup(120, 6.0)
            res["hair"][wi] = {"probes": probes, "grooms": C.groom_state(actor), "params": groom_params(ex)}
            step(f"hair {wi}", probes=probes[-3:])
            for vn in ("Face_Front", "Face_TQ_L", "Face_TQ_R", "Face_Profile_L", "Hair_Back34_L", "Hair_Back",
                       "Hair_Front_High"):
                yield from shoot(scene, f"h_{wi}_{vn}.png", V[vn])
        except Exception:  # noqa: BLE001
            warn(f"hair {wi}: " + traceback.format_exc()[-600:])
    C.release_actor(scene, actor, ex)
    step("explore2 done (nothing saved)")


# ================================================================================================================
# explore3 (v2, idol look): face variants K1-K4 vs the female v2 base, lip/blush, red vs brown eyes
# ================================================================================================================
BROWN_IRIS = {"tint": (0.6823, 0.6823, 0.6823), "saturation": 1.8, "cornea_size": 0.18, "primary_uv": (0.8716, 0.0859),
              "limbal": (0.8115, 0.8115, 0.8115)}
IDOL_MAKEUP = {"P1": {"lip_type": "CUPID", "lip_opacity": 0.45, "lip_color": (0.62, 0.12, 0.14), "lip_rough": 0.75,
                      "blush_type": "APPLE", "blush": 0.2, "blush_color": (0.8, 0.2, 0.22), "liner": 0.4},
               "P2": {"lip_type": "CUPID", "lip_opacity": 0.55, "lip_color": (0.55, 0.05, 0.12), "lip_rough": 0.7,
                      "blush_type": "HIGH_CURVE", "blush": 0.22, "blush_color": (0.8, 0.18, 0.22), "liner": 0.45}}
IDOL_LASHES = {"Eyelashes": {"Melanin": 0.55, "Redness": 0.0}}


def explore3_job(scene: C.Scene):
    res = C.REPORT.setdefault("explore3", {})
    final = dict(FINAL, face_variant="K2", makeup=IDOL_MAKEUP["P1"])
    ex = C.scratch_dup(f"{C.PRESET_SRC}/{BASE_PRESET}", "HY_X3")
    C.set_internal_slot(ex, "Hair", f"{C.GROOM_ROOT}/Hair/{final['hair']}")
    C.set_internal_slot(ex, "Eyebrows", f"{C.GROOM_ROOT}/Eyebrows/{final['brows']}")
    clear_internal_outfit(ex)
    C.open_edit(ex)
    dress(ex, final, res)
    lm = C.landmarks(ex)
    fc = C.face_center_from_landmarks(lm)
    V = C.views(fc, 168.0)
    actor = C.spawn(ex)
    scene.show_only(actor, [actor])
    yield from warmup(300, 15.0)
    set_groom_colours(ex, DARK)
    C.mhs().assemble_for_preview(ex)
    yield from warmup(120, 6.0)
    res["hair_probe"] = yield from wait_hair(scene, ex, fc, 900.0)
    set_groom_colours(ex, final["groom_params"])
    set_groom_colours(ex, IDOL_LASHES)
    yield from warmup(120, 6.0)
    res["faces"] = {}
    for name in ("H0", "H3xx", "K1", "K2", "K3", "K4"):
        apply_variant(ex, BASE_COEFFS, VARIANTS[name])
        yield from warmup(60, 2.5)
        lmv = C.landmarks(ex)
        res["faces"][name] = {"ratios": ratios(lmv), "coeffs": C.coeffs(ex)}
        step(f"face {name}", **ratios(lmv))
        Vv = C.views(C.face_center_from_landmarks(lmv), 168.0)
        for vn in ("Face_Front", "Face_TQ_L", "Face_Profile_L", "Face_Close"):
            yield from shoot(scene, f"k_{name}_{vn}.png", Vv[vn])
    apply_variant(ex, BASE_COEFFS, VARIANTS["K3"])
    yield from warmup(60, 2.5)
    V = C.views(C.face_center_from_landmarks(C.landmarks(ex)), 168.0)
    for name, kw in IDOL_MAKEUP.items():
        C.mhs().commit_makeup_settings(ex, makeup(**kw))
        yield from warmup(90, 4.0)
        for vn in ("Face_Front", "Face_Close"):
            yield from shoot(scene, f"p_{name}_{vn}.png", V[vn])
    commit_iris(ex, **BROWN_IRIS)
    yield from warmup(90, 4.0)
    for vn in ("Face_Front", "Face_Close", "Face_TQ_L"):
        yield from shoot(scene, f"brown_{vn}.png", V[vn])
    C.release_actor(scene, actor, ex)
    step("explore3 done (nothing saved)")


# ================================================================================================================
# explore4 (v2, idol): per-region SCALE on top of K4 -- landmark moves barely narrowed the nose, the region scale
# (face-model coefficient [scale, quat, t, n, PCA] per region, pb_face_build.layout) shrinks it directly
# ================================================================================================================
REGION_IDX = {"eyes": [7, 8], "nose": [13], "mouth": [16], "chin": [17]}
SCALES = {"S0": {}, "S1": {"nose": 0.90}, "S2": {"nose": 0.85, "mouth": 0.93},
          "S3": {"nose": 0.85, "mouth": 0.93, "eyes": 1.04},
          "S4": {"nose": 0.80, "mouth": 0.90, "eyes": 1.06, "chin": 0.95}}


def scaled(coeffs, scales: dict) -> list:
    out = list(coeffs)
    lay = C.PFB.layout(out)
    for group, f in scales.items():
        for r in REGION_IDX[group]:
            out[lay[r][0]] *= float(f)
    return out


def idol_base() -> list:
    rep = json.loads((C.OUT / "hy_explore3_1.json").read_text(encoding="utf-8"))
    return rep["explore3"]["faces"]["K4"]["coeffs"]


def explore4_job(scene: C.Scene):
    res = C.REPORT.setdefault("explore4", {"scales": SCALES})
    k4 = idol_base()
    ex = C.scratch_dup(f"{C.PRESET_SRC}/{BASE_PRESET}", "HY_X4")
    clear_internal_outfit(ex)
    C.open_edit(ex)
    res["body_got"] = set_body(ex, BODY)
    C.set_coeffs(ex, k4)
    C.mhs().commit_face_state(ex)
    sk = FINAL["skin"]
    C.commit_skin(ex, u=sk["u"], v=sk["v"], face_texture_index=sk["face_texture_index"], accents=sk["accents"])
    commit_lashes(ex, "LONG_SLIGHT_CURL", 0.55)
    C.mhs().commit_makeup_settings(ex, makeup(**IDOL_MAKEUP["P1"]))
    commit_iris(ex, **FINAL["iris"])
    actor = C.spawn(ex)
    scene.show_only(actor, [actor])
    yield from warmup(300, 15.0)
    lay = C.PFB.layout(k4)
    res["region_scales_k4"] = {g: [k4[lay[r][0]] for r in idx] for g, idx in REGION_IDX.items()}
    res["faces"] = {}
    for name, sc in SCALES.items():
        C.set_coeffs(ex, scaled(k4, sc))
        yield from warmup(60, 2.5)
        lmv = C.landmarks(ex)
        res["faces"][name] = {"ratios": ratios(lmv), "coeffs": C.coeffs(ex)}
        step(f"face {name}", **ratios(lmv))
        Vv = C.views(C.face_center_from_landmarks(lmv), 168.0)
        for vn in ("Face_Front", "Face_TQ_L", "Face_Profile_L", "Face_Close"):
            yield from shoot(scene, f"s_{name}_{vn}.png", Vv[vn])
    C.release_actor(scene, actor, ex)
    step("explore4 done (nothing saved)")


# ================================================================================================================
# build + verify: the saved private asset
# ================================================================================================================
RECIPE_PATH = C.OUT / "hiyuki_private_recipe.json"


def identity_readback(ch) -> dict:
    eyes = ch.get_editor_property("eyes_settings").get_editor_property("eye_left")
    el = ch.get_editor_property("head_model_settings").get_editor_property("eyelashes")
    return {"skin": C.skin_readback(ch), "iris": C.struct_dict(eyes.get_editor_property("iris")),
            "cornea": C.struct_dict(eyes.get_editor_property("cornea")),
            "eyelashes": {"type": C.enum_s(el.get_editor_property("type")),
                          "melanin": round(float(el.get_editor_property("melanin")), 4)},
            "makeup": C.struct_dict(ch.get_editor_property("makeup_settings")),
            "internal_selections": {k: v[0] for k, v in
                                    C.selections(ch.get_editor_property("internal_collection")).items()}}


def build_job(scene: C.Scene):
    res = C.REPORT.setdefault("build", {"final": FINAL})
    path = C.PF_PATH
    if ue.EditorAssetLibrary.does_asset_exist(path):
        step(f"deleting earlier {path} (made by this script)")
        if not ue.EditorAssetLibrary.delete_asset(path):
            raise RuntimeError(f"could not delete old {path}")
    ch = ue.EditorAssetLibrary.duplicate_asset(f"{C.PRESET_SRC}/{BASE_PRESET}", path)
    if not isinstance(ch, ue.MetaHumanCharacter):
        raise RuntimeError(f"duplicate_asset -> {ch}")
    res["hair"] = C.set_internal_slot(ch, "Hair", f"{C.GROOM_ROOT}/Hair/{FINAL['hair']}")
    res["brows"] = C.set_internal_slot(ch, "Eyebrows", f"{C.GROOM_ROOT}/Eyebrows/{FINAL['brows']}")
    clear_internal_outfit(ch)
    C.open_edit(ch)
    dress(ch, FINAL, res)
    actor = C.spawn(ch)
    scene.show_only(actor, [actor])
    yield from warmup(300, 15.0)
    lm = C.landmarks(ch)
    fc = C.face_center_from_landmarks(lm)
    set_groom_colours(ch, DARK)
    C.mhs().assemble_for_preview(ch)
    yield from warmup(120, 6.0)
    res["hair_probe"] = yield from wait_hair(scene, ch, fc, 1200.0)
    res["groom_params_set"] = set_groom_colours(ch, FINAL["groom_params"])
    yield from warmup(120, 6.0)
    res["groom_params"] = groom_params(ch)
    res["coeffs_final"] = C.coeffs(ch)
    res["landmarks_final"] = lm
    res["ratios"] = ratios(lm)
    res["constraints"] = C.constraints(ch)
    res["identity"] = identity_readback(ch)
    C.write_report()
    p = ch.get_path_name()
    if not p.startswith(path + "."):
        raise RuntimeError(f"refusing to save {p}")
    if not ue.EditorAssetLibrary.save_loaded_asset(ch, only_if_is_dirty=False):
        raise RuntimeError(f"save failed: {p}")
    step(f"SAVED {path}")
    V = C.views(fc, 168.0)
    for vn in ("Face_Front", "Face_TQ_L", "Hair_Back34_L"):
        yield from shoot(scene, f"build_{vn}.png", V[vn])
    C.release_actor(scene, actor, ch)
    RECIPE_PATH.write_text(json.dumps({
        "PRIVATE": "PRIVATE / DO NOT SHIP - never copy into DemoGame_1, the game build, Fab exports or anything public",
        "asset": path, "built_utc": C._now(), "script": "Scripts/MetaHuman/hy_hiyuki.py HY_MODE=build via hy_run.ps1",
        "final": FINAL, "face_base": "MH_PlayerFemale v2 face coefficients (numbers from player_female_recipe.json)",
        "landmark_stages": VARIANTS.get(FINAL["face_variant"], res.get("face_moves")),
        "k4_stages": VARIANTS["K4"], "idol_moves_per_unit": merged(idol_moves(1.0)), "region_scales": SCALES["S4"],
        "readback": res["identity"], "groom_params": res["groom_params"], "ratios": res["ratios"],
        "coeffs_final": res["coeffs_final"], "landmarks_final": lm}, indent=1, default=str), encoding="utf-8")
    step("build done")


def verify_job(scene: C.Scene):
    build = json.loads((C.OUT / f"hy_build_{os.environ.get('HY_BUILD_ATTEMPT', '1')}.json")
                       .read_text(encoding="utf-8"))["build"]
    res = C.REPORT.setdefault("verify", {})
    ch = ue.load_asset(C.PF_PATH)
    if not isinstance(ch, ue.MetaHumanCharacter):
        raise RuntimeError(f"{C.PF_PATH} did not load as a MetaHumanCharacter")
    res["disk_identity"] = identity_readback(ch)
    C.open_edit(ch)
    c = C.coeffs(ch)
    res["coeffs_maxdiff_vs_build"] = max(abs(a - b) for a, b in zip(c, build["coeffs_final"]))
    check("face_coeffs_equal_build", res["coeffs_maxdiff_vs_build"] < 1e-5, maxdiff=res["coeffs_maxdiff_vs_build"])
    actor = C.spawn(ch)
    scene.show_only(actor, [actor])
    yield from warmup(300, 15.0)
    lm = C.landmarks(ch)
    fc = C.face_center_from_landmarks(lm)
    V = C.views(fc, 168.0)
    V["Bust_Front"] = (C.orbit((fc[0], fc[1], fc[2] - 14.0), 170.0, 0, 3), (fc[0], fc[1], fc[2] - 14.0), 30.0)
    V["Face_TQ_L_High"] = (C.orbit(fc, 58.0, 30, 14), fc, 30.0)       # her ref3/ref4: head tipped down, 3/4
    V["Face_TQ_R_High"] = (C.orbit(fc, 58.0, -30, 14), fc, 30.0)
    t0 = C.time.monotonic()      # white hair: wait for the groom by time, then check the crown is not skin-coloured
    yield from warmup(600, 90.0)
    res["groom_params"] = groom_params(ch)
    gp_ok = all(abs(res["groom_params"].get(s, {}).get(n, -1) - v) < 1e-3
                for s, want in FINAL["groom_params"].items() for n, v in want.items())
    check("groom_params_persisted", gp_ok, params=res["groom_params"])
    res["grooms"] = C.groom_state(actor)
    res["groom_wait_s"] = round(C.time.monotonic() - t0, 1)
    for vn in ("Face_Front", "Face_TQ_L", "Face_TQ_R", "Face_Profile_L", "Face_Profile_R", "Face_Close", "Eyes",
               "Hair_Back34_L", "Hair_Back", "Hair_Front_High", "Body_Front", "Bust_Front", "Face_TQ_L_High",
               "Face_TQ_R_High"):
        yield from shoot(scene, f"hy_{vn}.png", V[vn])
    C.release_actor(scene, actor, ch)
    step("verify done (nothing saved)")


# ---- v2 (user 2026-09-27: "attractive idol ... eyes way too far apart, nose too big", "maybe a kpop idol. just pick
# one"): original K-pop-idol-style face; v1 (Hiyuki likeness H3xx) backed up in WorkFiles/.../hiyuki_private/v1 ----
FINAL.update({
    "version": 2,
    "face_variant": "K4S4",
    "makeup": IDOL_MAKEUP["P1"],
    "lashes": {"type": "LONG_SLIGHT_CURL", "melanin": 0.55},
    "groom_params": {"Hair": SILVER["Hair"], "Eyebrows": BROWS2["B2"]["Eyebrows"],
                     "Eyelashes": {"Melanin": 0.55, "Redness": 0.0}},
})


# ================================================================================================================
def main() -> None:
    C.OUT.mkdir(parents=True, exist_ok=True)
    with open(C.STEP_LOG, "a", encoding="utf-8") as fh:
        fh.write(f"\n===== hy_hiyuki.py mode={MODE} attempt={ATTEMPT} {C._now()} (PRIVATE / DO NOT SHIP) =====\n")
    C.assert_locks()
    if not C.REPORT["engine"].startswith("5.8"):
        raise RuntimeError(f"expected UE 5.8.x, got {C.REPORT['engine']}")
    C.REPORT["sha_start"] = C.protected_hashes()
    scene = C.Scene()
    step("scene ready")
    jobs = {"explore1": explore1_job, "explore2": explore2_job, "explore3": explore3_job, "explore4": explore4_job, "build": build_job, "verify": verify_job}
    if MODE not in jobs:
        raise ValueError(f"unknown HY_MODE {MODE}")
    C.Runner(scene, jobs[MODE](scene)).start()


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
