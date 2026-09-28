"""pf_female.py -- female player variant MH_PlayerFemale (UE 5.8.3, MetaHumanCharacter). Runs INSIDE UnrealEditor on
Exports/CharacterLab/Unreal/CharacterLab.uproject; launch with Scripts/MetaHuman/pf_run.ps1 -Mode <mode>.

Modes (PF_MODE):
  explore1  saves NOTHING. Reads Epic's young female presets (coefficients, landmarks, body constraints, skin/eyes/
            makeup/groom settings), renders each preset's face shape on one scratch actor (duplicate of Aera, under
            /Game/PlayerFemale/Scratch, never saved), renders round-1 coefficient blends, sweeps the skin tone
            (u/v -> body bias read back) and a set of low-mark face textures.
  explore2+ see the job functions below (all scratch-only until 'build').
Shared helpers: pf_common.py. Never signs in; never calls request_auto_rigging / request_texture_sources /
build_meta_human.
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
from pf_common import step, warn, check, warmup, shoot, switch  # noqa: E402

FEMALE_PRESETS = ["Aera", "Tuya", "Etta", "Lani", "Vivian", "Jelena", "Celeste", "Sunita"]
BASE_PRESET = "Aera"
LOW_MARK_TEXTURES = [58, 64, 33, 7, 35, 45, 147, 49, 36]   # TS-1.3 wrinkles Low / stubble None / marks Low, fairest
PRESET_DATA = C.OUT / "pf_preset_data.json"


def read_presets(names) -> dict:
    """Coefficients, landmarks and settings of Epic presets (scratch duplicates, opened for edit, never spawned)."""
    out = {}
    for p in names:
        dup = C.scratch_dup(f"{C.PRESET_SRC}/{p}", f"PRE_{p}")
        C.open_edit(dup)
        row = {"coeffs": C.coeffs(dup), "landmarks": C.landmarks(dup), "eval": C.eval_settings(dup),
               "constraints": C.constraints(dup), "settings": C.character_settings(dup),
               "skin": C.skin_readback(dup),
               "internal_collection": C.collection_inventory(dup.get_editor_property("internal_collection"))}
        try:
            col = C.mhs().get_preview_collection(dup)
            sel = C.selections(col)
            row["groom_params"] = {s: C.instance_params(col, k[1]) for s, k in sel.items()
                                   if s in ("Hair", "Eyebrows", "Eyelashes")}
        except Exception as exc:  # noqa: BLE001
            row["groom_params"] = "ERR " + repr(exc)[:200]
        C.close_edit(dup)
        out[p] = row
        step(f"preset {p} read", n=len(row["coeffs"]), height=row["constraints"].get("Height", {}).get("value"))
        yield
    return out


def mix(D: dict, weights: dict, regions: dict | None = None, base: str = BASE_PRESET) -> list:
    """base + sum w_i * (preset_i - base) per region (pb_face_build.blend)."""
    return C.PFB.blend(D[base]["coeffs"], {k: v["coeffs"] for k, v in D.items()}, weights, 1, regions=regions)


def explore1_variants(D: dict) -> list:
    return [
        {"name": "M3", "desc": "Aera/Tuya/Etta equal thirds", "coeffs": mix(D, {"Tuya": 1 / 3, "Etta": 1 / 3})},
        {"name": "M4", "desc": "Aera/Tuya/Etta/Lani quarters",
         "coeffs": mix(D, {"Tuya": .25, "Etta": .25, "Lani": .25})},
        {"name": "AT", "desc": "Aera .5 Tuya .35 Etta .15", "coeffs": mix(D, {"Tuya": .35, "Etta": .15})},
        {"name": "M3V", "desc": "Aera .3 Tuya .3 Etta .25 Vivian .15",
         "coeffs": mix(D, {"Tuya": .3, "Etta": .25, "Vivian": .15})},
        {"name": "M3J", "desc": "Aera .3 Tuya .3 Etta .25 Jelena .15",
         "coeffs": mix(D, {"Tuya": .3, "Etta": .25, "Jelena": .15})},
        {"name": "M3C", "desc": "Aera .3 Tuya .3 Etta .25 Celeste .15",
         "coeffs": mix(D, {"Tuya": .3, "Etta": .25, "Celeste": .15})},
    ]


def explore1_job(scene: C.Scene):
    res = C.REPORT.setdefault("explore1", {})
    # ---- explore actor FIRST (grooms only render for the first MetaHuman spawned in a session) ----
    ex = C.scratch_dup(f"{C.PRESET_SRC}/{BASE_PRESET}", "PF_X1")
    C.open_edit(ex)
    res["base_settings"] = C.character_settings(ex)
    res["base_skin"] = C.skin_readback(ex)
    res["base_constraints"] = C.constraints(ex)
    res["base_internal_collection"] = C.collection_inventory(ex.get_editor_property("internal_collection"))
    lm0 = C.landmarks(ex)
    fc = C.face_center_from_landmarks(lm0)
    height = res["base_constraints"].get("Height", {}).get("value", 168.0)
    res["face_center"] = fc
    res["height"] = height
    V = C.views(fc, height)
    actor = C.spawn(ex)
    scene.show_only(actor, [actor])
    yield from warmup(300, 15.0)
    res["grooms"] = C.groom_state(actor)
    for vn in ("Face_Front", "Face_TQ_L", "Face_Profile_L", "Body_Front", "Body_Side", "Eyes"):
        yield from shoot(scene, f"aera_asis_{vn}.png", V[vn])

    # ---- preset data ----
    D = yield from read_presets(FEMALE_PRESETS)
    PRESET_DATA.write_text(json.dumps(D, indent=1, default=str), encoding="utf-8")
    lay = C.PFB.layout(D[BASE_PRESET]["coeffs"])
    ok = all(C.PFB.layout(D[p]["coeffs"]) == lay for p in D)
    check("preset_layouts_equal", ok, n_regions=len(lay))
    check("dup_equals_preset", C.coeffs(ex) == D[BASE_PRESET]["coeffs"])

    # ---- a neutral light skin (freckles off) so shape comparisons are not dominated by texture ----
    res["skin_for_shapes"] = C.commit_skin(ex, face_texture_index=36)
    yield from warmup(90, 4.0)

    # ---- preset shapes on the one actor ----
    for p in FEMALE_PRESETS:
        C.set_coeffs(ex, D[p]["coeffs"])
        yield from warmup(60, 2.5)
        for vn in ("Face_Front", "Face_TQ_L"):
            yield from shoot(scene, f"p_{p}_{vn}.png", V[vn])
    # ---- round-1 blends ----
    res["variants"] = {}
    for v in explore1_variants(D):
        C.set_coeffs(ex, v["coeffs"])
        yield from warmup(60, 2.5)
        res["variants"][v["name"]] = {"desc": v["desc"], "landmarks": C.landmarks(ex)}
        for vn in ("Face_Front", "Face_TQ_L", "Face_Profile_L"):
            yield from shoot(scene, f"v_{v['name']}_{vn}.png", V[vn])

    # ---- skin tone: body bias read-back over a u/v grid, then captures ----
    C.set_coeffs(ex, explore1_variants(D)[0]["coeffs"])
    grid = {}
    for u in (0.0, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0):
        for v in (0.0, 0.25, 0.5, 0.75, 1.0):
            rb = C.commit_skin(ex, u=u, v=v, face_texture_index=36)
            grid[f"{u:.2f},{v:.2f}"] = {"bias": rb.get("body_bias"), "gain": rb.get("body_gain"),
                                        "srgb": rb.get("tone_srgb_from_bias")}
            yield
    res["skin_grid"] = grid
    step("skin grid read", n=len(grid))
    for u, v in ((0.0, 0.5), (1.0, 0.5), (0.5, 0.0), (0.5, 1.0), (0.1, 0.3), (0.1, 0.5), (0.1, 0.7),
                 (0.2, 0.3), (0.2, 0.5), (0.2, 0.7)):
        C.commit_skin(ex, u=u, v=v, face_texture_index=36)
        yield from warmup(90, 4.0)
        yield from shoot(scene, f"s_u{u:.2f}_v{v:.2f}_Face_Front.png", V["Face_Front"])
    # ---- face textures (low marks) at a fair tone ----
    for idx in LOW_MARK_TEXTURES:
        C.commit_skin(ex, u=0.1, v=0.5, face_texture_index=idx)
        yield from warmup(90, 4.0)
        yield from shoot(scene, f"t_{idx:03d}_Face_Close.png", V["Face_Close"])
    res["final_grooms"] = C.groom_state(actor)
    C.release_actor(scene, actor, ex)
    step("explore1 done (nothing saved)")


# ================================================================================================================
# explore2: per-region blends (Etta / Tuya / a refining preset on Aera), fair skin, hair swap test
# ================================================================================================================
EYES_UP = {"idx": [51, 44, 52, 36, 20, 35], "d": [0.0, 0.0, 0.06]}          # upper lids a touch higher (brighter eyes)
LOWER_LID_DOWN = {"idx": [53, 37], "d": [0.0, 0.0, -0.03]}
OUTER_CANTHUS_UP = {"idx": [22, 18], "d": [0.0, 0.0, 0.06]}                  # slight almond lift
JAW_SOFT = {"idx": [63, 43], "d_per": [[0.15, 0.0, 0.0], [-0.15, 0.0, 0.0]]}  # lower jaw sides a little inward
CHIN_SMALL = {"idx": [8, 82], "d": [0.0, -0.05, 0.08]}


def region_recipe(refiner: str = "Celeste", scale_aera: float = 1.0, etta_boost: float = 0.0) -> dict:
    r = refiner
    return {"blend": {"Etta": .35 + etta_boost, "Tuya": .2, r: .15},
            "regions": {"eyes": {"Etta": .35 + etta_boost, r: .25, "Tuya": .1},
                        "brows": {"Etta": .35 + etta_boost, "Tuya": .2, r: .15},
                        "nose": {"Etta": .3 + etta_boost, r: .3, "Tuya": .2},
                        "mouth": {"Etta": .5 + etta_boost / 2, r: .2, "Tuya": .1},
                        "chin": {"Tuya": .4, "Etta": .35 + etta_boost / 2},
                        "jaw": {"Tuya": .4, "Etta": .35 + etta_boost / 2, r: .1},
                        "cheeks": {"Tuya": .35, "Etta": .35 + etta_boost / 2},
                        "cheekbones": {"Etta": .35 + etta_boost / 2, "Tuya": .25, r: .1}}}


def explore2_variants(D: dict) -> list:
    out = []
    for name, rc, moves in (("R1", region_recipe("Celeste"), []),
                            ("R2", region_recipe("Sunita"), []),
                            ("R3", region_recipe("Vivian"), []),
                            ("R4", region_recipe("Celeste", etta_boost=0.15), []),
                            ("R1m", region_recipe("Celeste"), [EYES_UP, LOWER_LID_DOWN, OUTER_CANTHUS_UP, JAW_SOFT]),
                            ("R4m", region_recipe("Celeste", etta_boost=0.15),
                             [EYES_UP, LOWER_LID_DOWN, OUTER_CANTHUS_UP, JAW_SOFT, CHIN_SMALL])):
        out.append({"name": name, "recipe": rc, "moves": moves,
                    "coeffs": mix(D, rc["blend"], rc["regions"])})
    return out


def load_preset_data() -> dict:
    return json.loads(PRESET_DATA.read_text(encoding="utf-8"))


def apply_face(ch, v) -> list:
    """coefficients, then one translate_face_landmarks call per move stage (moves, moves2, moves3 if present)."""
    C.set_coeffs(ch, v["coeffs"])
    flat = C.translate_landmarks(ch, v["moves"]) if v.get("moves") else []
    for k in ("moves2", "moves3"):
        if v.get(k):
            flat = flat + [[k]] + C.translate_landmarks(ch, v[k])
    return flat


HAIR_TRIES = ["WI_Hair_S_Updo", "WI_Hair_L_Straight", "WI_Hair_S_LowPonytail"]
GROOM_COLOUR = {"Hair": {"Melanin": 0.9, "Redness": 0.1}, "Eyebrows": {"Melanin": 0.9, "Redness": 0.1},
                "Eyelashes": {"Melanin": 0.9}}


def set_groom_colours(ch, params=GROOM_COLOUR) -> dict:
    col = C.mhs().get_preview_collection(ch)
    sel = C.selections(col)
    done = {}
    for slot, want in params.items():
        if slot in sel:
            for n, val in want.items():
                done[f"{slot}.{n}"] = C.set_groom_param(col, sel[slot][1], n, val)
    C.mhs().on_edit_preview_collection(ch)
    return done


def wait_hair(scene, ch, fc, max_seconds=180.0):
    """Wait until the crown above the forehead renders dark (hair) in a Face_Front-style probe."""
    V = C.views(fc, 170.0)
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


def explore2_job(scene: C.Scene):
    res = C.REPORT.setdefault("explore2", {})
    D = load_preset_data()
    ex = C.scratch_dup(f"{C.PRESET_SRC}/{BASE_PRESET}", "PF_X2")
    C.open_edit(ex)
    fc = C.face_center_from_landmarks(D[BASE_PRESET]["landmarks"])
    V = C.views(fc, 170.0)
    res["face_center"] = fc
    res["skin_default"] = C.commit_skin(ex, u=0.0, v=0.65, face_texture_index=33)
    actor = C.spawn(ex)
    scene.show_only(actor, [actor])
    yield from warmup(300, 15.0)
    res["grooms"] = C.groom_state(actor)
    res["variants"] = {}
    variants = explore2_variants(D)
    for v in variants:
        flat = apply_face(ex, v)
        yield from warmup(60, 2.5)
        res["variants"][v["name"]] = {"recipe": v["recipe"], "moves": flat, "landmarks": C.landmarks(ex),
                                      "coeffs": C.coeffs(ex)}
        for vn in ("Face_Front", "Face_TQ_L", "Face_TQ_R", "Face_Profile_L"):
            yield from shoot(scene, f"v_{v['name']}_{vn}.png", V[vn])
    # ---- skin on R4m ----
    apply_face(ex, variants[-1])
    for u, vv, tex in ((0.0, 0.5, 33), (0.0, 0.8, 33), (0.04, 0.7, 33), (0.0, 0.65, 49), (0.0, 1.0, 33)):
        res.setdefault("skin", {})[f"{u}_{vv}_{tex}"] = C.commit_skin(ex, u=u, v=vv, face_texture_index=tex)
        yield from warmup(90, 4.0)
        yield from shoot(scene, f"s_u{u:.2f}_v{vv:.2f}_t{tex}_Face_Front.png", V["Face_Front"])
    C.commit_skin(ex, u=0.0, v=0.65, face_texture_index=33)
    yield from warmup(60, 3.0)
    # ---- hair swap test on the same actor ----
    res["hair"] = {}
    for wi in HAIR_TRIES:
        try:
            key = C.set_preview_slot(ex, "Hair", f"{C.GROOM_ROOT}/Hair/{wi}")
            C.mhs().assemble_for_preview(ex)
            yield from warmup(120, 6.0)
            res["hair"][wi] = {"key": key, "colours": set_groom_colours(ex)}
            C.mhs().assemble_for_preview(ex)
            probes = yield from wait_hair(scene, ex, fc)
            res["hair"][wi]["probes"] = probes
            res["hair"][wi]["grooms"] = C.groom_state(actor)
            step(f"hair {wi}", probes=probes[-3:])
            for vn in ("Face_Front", "Face_TQ_L", "Hair_Back34_L", "Hair_Side_L"):
                yield from shoot(scene, f"h_{wi}_{vn}.png", V[vn])
        except Exception:  # noqa: BLE001
            warn(f"hair {wi}: " + traceback.format_exc()[-600:])
    C.release_actor(scene, actor, ex)
    step("explore2 done (nothing saved)")


# ================================================================================================================
# explore3: refined recipes + landmark moves, brows/lashes, hair (internal collection first), makeup, skin, body
# ================================================================================================================
def inward(pair, a, dz=0.0, dy=0.0):
    """(character-right -X, character-left +X) landmark pair moved a cm towards the midline."""
    return {"idx": list(pair), "d_per": [[a, dy, dz], [-a, dy, dz]]}


M2 = [{"idx": [51, 44, 52, 36, 20, 35], "d": [0.0, 0.0, 0.08]},        # upper lids up: brighter, less hooded
      {"idx": [53, 37], "d": [0.0, 0.0, -0.04]},                         # lower lids down a little
      inward((22, 18), -0.03, dz=0.05),                                   # outer canthi slightly out + up (almond)
      inward((1, 28), 0.35), inward((2, 29), 0.25), inward((63, 43), 0.2),  # narrower lower face / jaw
      inward((66, 23), 0.15),                                             # outer cheekbones slightly in
      inward((67, 45), 0.1),                                              # narrower alae (refined nose)
      {"idx": [64], "d": [0.0, -0.04, 0.02]},                            # smaller, slightly lifted tip
      inward((3, 30), 0.1), {"idx": [8, 62], "d": [0.0, 0.0, 0.08]}]      # small chin
M2_STRONG_JAW = M2 + [inward((1, 28), 0.2), inward((68, 46), 0.15)]


def recipe3(refiners: dict) -> dict:
    """Etta/Tuya core with a refining mix; less Aera in the cheeks than round 2 (narrower mid-face)."""
    def with_ref(core: dict, scale: float) -> dict:
        d = dict(core)
        for k, w in refiners.items():
            d[k] = d.get(k, 0.0) + w * scale
        return d
    return {"blend": with_ref({"Etta": .35, "Tuya": .2}, 1.0),
            "regions": {"eyes": with_ref({"Etta": .35, "Tuya": .1}, 1.6),
                        "brows": with_ref({"Etta": .35, "Tuya": .2}, 1.0),
                        "nose": with_ref({"Etta": .3, "Tuya": .2}, 2.0),
                        "mouth": with_ref({"Etta": .5, "Tuya": .1}, 1.3),
                        "chin": with_ref({"Tuya": .4, "Etta": .35}, 0.7),
                        "jaw": with_ref({"Tuya": .45, "Etta": .35}, 0.7),
                        "cheeks": with_ref({"Tuya": .45, "Etta": .4}, 0.5),
                        "cheekbones": with_ref({"Etta": .4, "Tuya": .35}, 0.7)}}


def explore3_variants(D: dict) -> list:
    out = []
    for name, refs, moves in (("F1", {"Vivian": .15}, M2),
                              ("F2", {"Sunita": .15}, M2),
                              ("F3", {"Vivian": .07, "Sunita": .06, "Celeste": .04}, M2),
                              ("F3j", {"Vivian": .07, "Sunita": .06, "Celeste": .04}, M2_STRONG_JAW)):
        rc = recipe3(refs)
        out.append({"name": name, "recipe": rc, "moves": moves, "coeffs": mix(D, rc["blend"], rc["regions"])})
    return out


BROWS_WI = "WI_Eyebrows_M_Natural"
FIRST_HAIR = "WI_Hair_S_Updo"
MORE_HAIR = ["WI_Hair_S_UpdoBuns", "WI_Hair_L_Straight"]
LASHES = {"type": "LONG_SLIGHT_CURL", "melanin": 0.9}


def commit_lashes(ch, type_name="LONG_SLIGHT_CURL", melanin=0.9) -> None:
    hm = ch.get_editor_property("head_model_settings")
    el = hm.get_editor_property("eyelashes")
    el.set_editor_property("type", getattr(ue.MetaHumanCharacterEyelashesType, type_name))
    el.set_editor_property("enable_grooms", True)
    el.set_editor_property("melanin", float(melanin))
    hm.set_editor_property("eyelashes", el)
    C.mhs().commit_head_model_settings(ch, hm)


def makeup(kind: str):
    m = ue.MetaHumanCharacterMakeupSettings()
    if kind == "none":
        return m
    lips = ue.MetaHumanCharacterLipsMakeupProperties()
    lips.type = ue.MetaHumanCharacterLipsMakeupType.NATURAL
    lips.color = ue.LinearColor(0.45, 0.12, 0.13, 1.0)       # soft rose
    lips.opacity = 0.25 if kind == "subtle" else 0.4
    lips.roughness = 0.35
    lips.metalness = 0.0
    eyes = ue.MetaHumanCharacterEyeMakeupProperties()
    eyes.type = ue.MetaHumanCharacterEyeMakeupType.THIN_LINER
    eyes.primary_color = ue.LinearColor(0.02, 0.012, 0.01, 1.0)
    eyes.secondary_color = ue.LinearColor(0.0, 0.0, 0.0, 1.0)
    eyes.opacity = 0.35 if kind == "subtle" else 0.55
    eyes.roughness = 0.75
    eyes.metalness = 0.0
    m.lips = lips
    m.eyes = eyes
    if kind == "blush":
        b = ue.MetaHumanCharacterBlushMakeupProperties()
        b.type = ue.MetaHumanCharacterBlushMakeupType.APPLE
        b.color = ue.LinearColor(0.5, 0.12, 0.12, 1.0)
        b.intensity = 0.15
        b.roughness = 0.6
        m.blush = b
    return m


LIP_ACCENT_SOFT = {"lips": {"saturation": 0.35, "redness": 0.45}}


def explore3_job(scene: C.Scene):
    res = C.REPORT.setdefault("explore3", {})
    D = load_preset_data()
    ex = C.scratch_dup(f"{C.PRESET_SRC}/{BASE_PRESET}", "PF_X3")
    res["hair_first"] = C.set_internal_slot(ex, "Hair", f"{C.GROOM_ROOT}/Hair/{FIRST_HAIR}")
    res["brows"] = C.set_internal_slot(ex, "Eyebrows", f"{C.GROOM_ROOT}/Eyebrows/{BROWS_WI}")
    C.open_edit(ex)
    fc = C.face_center_from_landmarks(D[BASE_PRESET]["landmarks"])
    V = C.views(fc, 170.0)
    variants = explore3_variants(D)
    apply_face(ex, variants[2])
    C.mhs().commit_face_state(ex)
    res["skin_default"] = C.commit_skin(ex, u=0.0, v=0.75, face_texture_index=33)
    commit_lashes(ex)
    C.mhs().commit_makeup_settings(ex, makeup("none"))
    actor = C.spawn(ex)
    scene.show_only(actor, [actor])
    yield from warmup(300, 15.0)
    res["colours"] = set_groom_colours(ex, {"Hair": {"Melanin": 0.9, "Redness": 0.1},
                                            "Eyebrows": {"Melanin": 0.95, "Redness": 0.1},
                                            "Eyelashes": {"Melanin": 0.95}})
    C.mhs().assemble_for_preview(ex)
    yield from warmup(120, 6.0)
    probes = yield from wait_hair(scene, ex, fc, 300.0)
    res["hair_probe_first"] = probes
    res["grooms"] = C.groom_state(actor)
    col = C.mhs().get_preview_collection(ex)
    res["groom_params"] = {s: C.instance_params(col, k[1]) for s, k in C.selections(col).items()
                           if s in ("Hair", "Eyebrows", "Eyelashes")}
    res["variants"] = {}
    for v in variants:
        flat = apply_face(ex, v)
        yield from warmup(60, 2.5)
        res["variants"][v["name"]] = {"recipe": v["recipe"], "moves": flat, "landmarks": C.landmarks(ex),
                                      "coeffs": C.coeffs(ex)}
        for vn in ("Face_Front", "Face_TQ_L", "Face_TQ_R", "Face_Profile_L"):
            yield from shoot(scene, f"v_{v['name']}_{vn}.png", V[vn])
    apply_face(ex, variants[2])
    yield from warmup(60, 2.5)
    for vn in ("Hair_Back34_L", "Hair_Side_L", "Hair_Back", "Eyes"):
        yield from shoot(scene, f"h_{FIRST_HAIR}_{vn}.png", V[vn])
    # ---- makeup + lip accent ----
    for kind in ("none", "subtle", "subtle_accent", "blush"):
        if kind == "subtle_accent":
            C.commit_skin(ex, u=0.0, v=0.75, face_texture_index=33, accents=LIP_ACCENT_SOFT)
            C.mhs().commit_makeup_settings(ex, makeup("subtle"))
        else:
            C.mhs().commit_makeup_settings(ex, makeup(kind))
        yield from warmup(90, 4.0)
        yield from shoot(scene, f"m_{kind}_Face_Close.png", V["Face_Close"])
        yield from shoot(scene, f"m_{kind}_Face_Front.png", V["Face_Front"])
    # ---- skin tone final choice ----
    C.mhs().commit_makeup_settings(ex, makeup("subtle"))
    for u, vv in ((0.0, 0.65), (0.0, 0.85), (0.03, 0.8), (0.0, 0.75)):
        res.setdefault("skin", {})[f"{u}_{vv}"] = C.commit_skin(ex, u=u, v=vv, face_texture_index=33,
                                                                accents=LIP_ACCENT_SOFT)
        yield from warmup(90, 4.0)
        yield from shoot(scene, f"s_u{u:.2f}_v{vv:.2f}_Face_Front.png", V["Face_Front"])
        yield from shoot(scene, f"s_u{u:.2f}_v{vv:.2f}_Body_Front.png", V["Body_Front"])
    # ---- more hairstyles (swap on the same actor; binding may take minutes) ----
    for wi in MORE_HAIR:
        try:
            key = C.set_preview_slot(ex, "Hair", f"{C.GROOM_ROOT}/Hair/{wi}")
            set_groom_colours(ex, {"Hair": {"Melanin": 0.9, "Redness": 0.1}})
            C.mhs().assemble_for_preview(ex)
            yield from warmup(120, 6.0)
            probes = yield from wait_hair(scene, ex, fc, 360.0)
            res.setdefault("hair_more", {})[wi] = {"key": key, "probes": probes, "grooms": C.groom_state(actor)}
            step(f"hair {wi}", probes=probes[-3:])
            for vn in ("Face_Front", "Face_TQ_L", "Hair_Back34_L", "Hair_Side_L", "Hair_Back"):
                yield from shoot(scene, f"h_{wi}_{vn}.png", V[vn])
        except Exception:  # noqa: BLE001
            warn(f"hair {wi}: " + traceback.format_exc()[-600:])
    # ---- body: preset body vs 168 cm lean-athletic constraint sets (outfit cleared) ----
    try:
        col = C.mhs().get_preview_collection(ex)
        col.get_editor_property("default_instance").set_single_slot_selection("Outfits", ue.MetaHumanPaletteItemKey())
        C.mhs().on_edit_preview_collection(ex)
        C.mhs().assemble_for_preview(ex)
        yield from warmup(120, 6.0)
    except Exception:  # noqa: BLE001
        warn("outfit clear: " + traceback.format_exc()[-400:])
    res["body"] = {"preset": C.constraints(ex)}
    for vn in ("Body_Front", "Body_Side"):
        yield from shoot(scene, f"b_preset_{vn}.png", V[vn])
    for label, want in (("B1", {"Height": 168.0}),
                        ("B2", {"Height": 168.0, "Fat": -0.9, "Muscularity": -0.2}),
                        ("B3", {"Height": 168.0, "Fat": -0.9, "Muscularity": 0.2})):
        cons = C.mhs().get_body_constraints(ex, False)
        for c in cons:
            n = str(c.name)
            if n in want:
                c.set_editor_property("is_active", True)
                c.set_editor_property("target_measurement", float(want[n]))
            else:
                c.set_editor_property("is_active", False)
        C.mhs().set_body_constraints(ex, cons)
        C.mhs().commit_body_state(ex)
        yield from warmup(150, 8.0)
        res["body"][label] = {"want": want, "got": C.constraints(ex), "landmarks": C.landmarks(ex)}
        fc2 = C.face_center_from_landmarks(C.landmarks(ex))
        V2 = C.views(fc2, 168.0)
        for vn in ("Body_Front", "Body_Side", "Body_Back", "Face_Front"):
            yield from shoot(scene, f"b_{label}_{vn}.png", V2[vn])
    C.release_actor(scene, actor, ex)
    step("explore3 done (nothing saved)")


# ================================================================================================================
# explore4: chosen face F3j with the final identity candidates, hair S_Updo + L_Straight, textures, body constraints
# ================================================================================================================
SKIN_ACCENTS = {"lips": {"saturation": 0.35, "redness": 0.45}, "under_eye": {"redness": 0.35, "saturation": 0.4}}


def set_body(ch, want: dict) -> dict:
    """Epic's example pattern: modify the struct objects in a Python list, pass the list back, commit."""
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


def explore4_job(scene: C.Scene):
    res = C.REPORT.setdefault("explore4", {})
    D = load_preset_data()
    face = next(v for v in explore3_variants(D) if v["name"] == "F3j")
    ex = C.scratch_dup(f"{C.PRESET_SRC}/{BASE_PRESET}", "PF_X4")
    res["hair_first"] = C.set_internal_slot(ex, "Hair", f"{C.GROOM_ROOT}/Hair/WI_Hair_S_Updo")
    res["brows"] = C.set_internal_slot(ex, "Eyebrows", f"{C.GROOM_ROOT}/Eyebrows/{BROWS_WI}")
    clear_internal_outfit(ex)
    C.open_edit(ex)
    fc = C.face_center_from_landmarks(D[BASE_PRESET]["landmarks"])
    V = C.views(fc, 170.0)
    apply_face(ex, face)
    C.mhs().commit_face_state(ex)
    res["skin"] = C.commit_skin(ex, u=0.0, v=0.8, face_texture_index=33, accents=SKIN_ACCENTS)
    commit_lashes(ex)
    C.mhs().commit_makeup_settings(ex, makeup("subtle"))
    actor = C.spawn(ex)
    scene.show_only(actor, [actor])
    yield from warmup(300, 15.0)
    res["colours"] = set_groom_colours(ex, {"Hair": {"Melanin": 0.95, "Redness": 0.05},
                                            "Eyebrows": {"Melanin": 0.95, "Redness": 0.1},
                                            "Eyelashes": {"Melanin": 0.95}})
    C.mhs().assemble_for_preview(ex)
    yield from warmup(120, 6.0)
    res["hair_probe_first"] = yield from wait_hair(scene, ex, fc, 900.0)
    res["grooms"] = C.groom_state(actor)
    col = C.mhs().get_preview_collection(ex)
    res["groom_params"] = {s: C.instance_params(col, k[1]) for s, k in C.selections(col).items()
                           if s in ("Hair", "Eyebrows", "Eyelashes")}
    res["preview_collection"] = C.collection_inventory(col)
    for vn in ("Face_Front", "Face_TQ_L", "Face_TQ_R", "Face_Profile_L", "Face_Close", "Eyes", "Hair_Back34_L",
               "Hair_Back", "Hair_Side_L", "Hair_Top"):
        yield from shoot(scene, f"f_Updo_{vn}.png", V[vn])
    for tex in (64, 49):
        C.commit_skin(ex, u=0.0, v=0.8, face_texture_index=tex, accents=SKIN_ACCENTS)
        yield from warmup(90, 4.0)
        for vn in ("Face_Front", "Face_Close"):
            yield from shoot(scene, f"t_{tex}_{vn}.png", V[vn])
    C.commit_skin(ex, u=0.0, v=0.8, face_texture_index=33, accents=SKIN_ACCENTS)
    yield from warmup(90, 4.0)
    yield from shoot(scene, "b_preset_Body_Front.png", V["Body_Front"])
    yield from shoot(scene, "b_preset_Body_Side.png", V["Body_Side"])
    res["body"] = {"preset": C.constraints(ex)}
    for label, want in (("B2", {"Height": 168.0, "Fat": -0.9, "Muscularity": -0.2}),
                        ("B3", {"Height": 168.0, "Fat": -0.9, "Muscularity": 0.2})):
        res["body"][label] = {"want": want, "got": set_body(ex, want)}
        yield from warmup(150, 8.0)
        lm = C.landmarks(ex)
        res["body"][label]["landmarks"] = lm
        V2 = C.views(C.face_center_from_landmarks(lm), 168.0)
        step(f"body {label}", got=res["body"][label]["got"])
        for vn in ("Body_Front", "Body_Side", "Body_Back", "Face_Front"):
            yield from shoot(scene, f"b_{label}_{vn}.png", V2[vn])
    try:
        key = C.set_preview_slot(ex, "Hair", f"{C.GROOM_ROOT}/Hair/WI_Hair_L_Straight")
        set_groom_colours(ex, {"Hair": {"Melanin": 0.95, "Redness": 0.05}})
        C.mhs().assemble_for_preview(ex)
        yield from warmup(120, 6.0)
        lm = C.landmarks(ex)
        fc2 = C.face_center_from_landmarks(lm)
        probes = yield from wait_hair(scene, ex, fc2, 600.0)
        res["hair_straight"] = {"key": key, "probes": probes, "grooms": C.groom_state(actor)}
        V2 = C.views(fc2, 168.0)
        for vn in ("Face_Front", "Face_TQ_L", "Hair_Back34_L", "Hair_Back", "Hair_Side_L", "Body_Front"):
            yield from shoot(scene, f"h_Straight_{vn}.png", V2[vn])
    except Exception:  # noqa: BLE001
        warn("straight hair: " + traceback.format_exc()[-600:])
    C.release_actor(scene, actor, ex)
    step("explore4 done (nothing saved)")


# ================================================================================================================
# BUILD + VERIFY: MH_PlayerFemale (and optional face alternates) from the choices made in explore1-4
# ================================================================================================================
FINAL = {
    "source_preset": BASE_PRESET,
    "face_variant": "F3jEJ3",
    "hair": "WI_Hair_S_Updo",
    "brows": BROWS_WI,
    "lashes": LASHES,
    "skin": {"u": 0.0, "v": 0.8, "face_texture_index": 49, "accents": SKIN_ACCENTS, "freckles": "NONE",
             "show_top_underwear": True},
    "makeup": "subtle",
    "body": {"Height": 168.0, "Fat": -0.9, "Muscularity": 0.2},
    "groom_params": {"Hair": {"Melanin": 0.95, "Redness": 0.05}, "Eyebrows": {"Melanin": 0.95, "Redness": 0.1},
                     "Eyelashes": {"Melanin": 0.95}},
    "eyes": "kept from the Aera preset (IRIS007, dark brown)",
    "peachfuzz": "kept from the Aera preset (WI_Peachfuzz_M_Thin)",
}
ALTS = {"MH_PlayerFemale_AltA": "F1", "MH_PlayerFemale_AltB": "R4m"}
BUILD_ALTS = os.environ.get("PF_ALTS", "0") == "1"
RECIPE_PATH = C.OUT / "player_female_recipe.json"


EYES_MORE_OPEN = [{"idx": [51, 44, 52, 36, 20, 35], "d": [0.0, 0.0, 0.04]}, {"idx": [53, 37], "d": [0.0, 0.0, -0.02]}]


def all_face_variants(D: dict) -> dict:
    out = {v["name"]: v for v in explore2_variants(D)}
    out.update({v["name"]: v for v in explore3_variants(D)})
    f = dict(out["F3j"])
    f["name"] = "F3jE"
    f["moves"] = list(f["moves"]) + EYES_MORE_OPEN      # F3j + eyes a touch more open (explore4 read slightly small)
    out["F3jE"] = f
    g = dict(f)
    g["name"] = "F3jEJ3"
    g["moves2"] = J3                                     # explore5: narrower jaw + slightly shorter chin, 2nd pass
    out["F3jEJ3"] = g
    return out


def identity_readback(ch) -> dict:
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
    acc = ch.get_editor_property("skin_settings").get_editor_property("accents")
    return {"skin": C.skin_readback(ch), "iris": iris,
            "accents": {r: C.struct_dict(acc.get_editor_property(r)) for r in ("lips", "under_eye")},
            "eyelashes": {"type": C.enum_s(el.get_editor_property("type")),
                          "enable_grooms": bool(el.get_editor_property("enable_grooms")),
                          "melanin": round(float(el.get_editor_property("melanin")), 4)},
            "makeup": C.struct_dict(mk),
            "internal_selections": {k: v[0] for k, v in C.selections(ch.get_editor_property("internal_collection")).items()}}


def identity_ok(rb: dict) -> dict:
    s = rb["skin"]
    sel = rb["internal_selections"]
    return {"u": abs(s["u"] - FINAL["skin"]["u"]) < 1e-3, "v": abs(s["v"] - FINAL["skin"]["v"]) < 1e-3,
            "face_texture_index": s["face_texture_index"] == FINAL["skin"]["face_texture_index"],
            "freckles_none": s["freckles_mask"] == "NONE", "top_underwear": s["show_top_underwear"] is True,
            "lashes": rb["eyelashes"]["type"] == FINAL["lashes"]["type"],
            "lash_melanin": abs(rb["eyelashes"]["melanin"] - FINAL["lashes"]["melanin"]) < 1e-3,
            "lips_makeup": rb["makeup"]["lips"]["type"] == FINAL.get("check_lips", "NATURAL"),
            "eye_makeup": rb["makeup"]["eyes"]["type"] == "THIN_LINER",
            "blush": rb["makeup"]["blush"]["type"] == FINAL.get("check_blush", "NONE"),
            "foundation_off": rb["makeup"]["foundation"]["apply_foundation"] is False,
            "hair": str(sel.get("Hair", "")).startswith(FINAL["hair"]),
            "brows": str(sel.get("Eyebrows", "")).startswith(FINAL["brows"]),
            "outfit_empty": sel.get("Outfits") in (None, "", "None")}


def make_character(path: str, D: dict, face: dict, res: dict):
    """Duplicate the Aera preset to `path` and apply the FINAL identity with the given face variant (unsaved)."""
    if ue.EditorAssetLibrary.does_asset_exist(path):
        step(f"deleting earlier {path} (made by this script)")
        if not ue.EditorAssetLibrary.delete_asset(path):
            raise RuntimeError(f"could not delete old {path}")
    ch = ue.EditorAssetLibrary.duplicate_asset(f"{C.PRESET_SRC}/{FINAL['source_preset']}", path)
    if not isinstance(ch, ue.MetaHumanCharacter):
        raise RuntimeError(f"duplicate_asset -> {ch}")
    res["hair"] = C.set_internal_slot(ch, "Hair", f"{C.GROOM_ROOT}/Hair/{FINAL['hair']}")
    res["brows"] = C.set_internal_slot(ch, "Eyebrows", f"{C.GROOM_ROOT}/Eyebrows/{FINAL['brows']}")
    clear_internal_outfit(ch)
    C.open_edit(ch)
    res["coeffs_at_open_equal_preset"] = C.coeffs(ch) == D[FINAL["source_preset"]]["coeffs"]
    # body FIRST (the face follows the body; explore4 set it after the face and the live preview showed a neck gap)
    res["body_got"] = set_body(ch, FINAL["body"])
    res["face_moves_applied"] = apply_face(ch, face)
    res["coeffs_after_face"] = C.coeffs(ch)
    C.mhs().commit_face_state(ch)
    sk = FINAL["skin"]
    res["skin_readback"] = C.commit_skin(ch, u=sk["u"], v=sk["v"], face_texture_index=sk["face_texture_index"],
                                         accents=sk["accents"], show_top_underwear=sk["show_top_underwear"])
    commit_lashes(ch, FINAL["lashes"]["type"], FINAL["lashes"]["melanin"])
    mk = FINAL["makeup"]
    C.mhs().commit_makeup_settings(ch, makeup2(**mk) if isinstance(mk, dict) else makeup(mk))
    if "sclera_custom_tint" in FINAL:
        res["sclera"] = commit_sclera(ch, FINAL["sclera_custom_tint"])
    return ch


def save(ch, path: str) -> None:
    p = ch.get_path_name()
    if not p.startswith(path + "."):
        raise RuntimeError(f"refusing to save {p}")
    if not ue.EditorAssetLibrary.save_loaded_asset(ch, only_if_is_dirty=False):
        raise RuntimeError(f"save failed: {p}")
    step(f"SAVED {path}")


def build_job(scene: C.Scene):
    D = load_preset_data()
    faces = final_faces(D)
    res = C.REPORT.setdefault("build", {"final": FINAL})
    ch = make_character(C.PF_PATH, D, faces[FINAL["face_variant"]], res)
    step("MH_PlayerFemale made (unsaved)", body=res["body_got"])
    actor = C.spawn(ch)
    scene.show_only(actor, [actor])
    yield from warmup(300, 15.0)
    res["groom_params_set"] = set_groom_colours(ch, FINAL["groom_params"])
    C.mhs().assemble_for_preview(ch)
    yield from warmup(120, 6.0)
    lm = C.landmarks(ch)
    fc = C.face_center_from_landmarks(lm)
    res["hair_probe"] = yield from wait_hair(scene, ch, fc, 1200.0)
    col = C.mhs().get_preview_collection(ch)
    res["groom_params"] = {s: C.instance_params(col, k[1]) for s, k in C.selections(col).items()
                           if s in ("Hair", "Eyebrows", "Eyelashes")}
    res["grooms"] = C.groom_state(actor)
    res["coeffs_final"] = C.coeffs(ch)
    res["landmarks_final"] = lm
    res["face_center"] = fc
    res["constraints"] = C.constraints(ch)
    res["eval_settings"] = C.eval_settings(ch)
    res["identity"] = identity_readback(ch)
    oks = identity_ok(res["identity"])
    check("build_identity", all(oks.values()), detail=oks)
    C.write_report()
    save(ch, C.PF_PATH)
    res["saved"] = True
    V = C.views(fc, res["constraints"]["Height"]["value"])
    for vn in ("Face_Front", "Face_TQ_L", "Body_Front", "Hair_Back34_L"):
        yield from shoot(scene, f"build_{vn}.png", V[vn])
    C.release_actor(scene, actor, ch)
    yield from warmup(30, 1.0)
    if BUILD_ALTS:
        C.assert_locks(extra=list(ALTS))
        for name, fv in ALTS.items():
            ares = res.setdefault("alts", {}).setdefault(name, {"face_variant": fv})
            a = make_character(f"{C.CHAR_DIR}/{name}", D, faces[fv], ares)
            set_groom_colours(a, FINAL["groom_params"])
            ares["coeffs_final"] = C.coeffs(a)
            ares["identity"] = identity_readback(a)
            save(a, f"{C.CHAR_DIR}/{name}")
            C.close_edit(a)
            yield
    write_recipe(D, faces, res)
    step("build done")


def write_recipe(D: dict, faces: dict, res: dict) -> None:
    fv = faces[FINAL["face_variant"]]
    recipe = {
        "asset": C.PF_PATH, "built_utc": C._now(),
        "build_script": "Scripts/MetaHuman/pf_female.py (PF_MODE=build) via Scripts/MetaHuman/pf_run.ps1 -Mode build",
        "reproduce": [
            f"duplicate {C.PRESET_SRC}/{FINAL['source_preset']} -> {C.PF_PATH}",
            f"internal collection: Hair={FINAL['hair']}, Eyebrows={FINAL['brows']}, Outfits cleared (other slots as the preset)",
            "open for edit; set_body_constraints(only the body constraints below active) + commit_body_state; "
            "then set_face_model_coefficients(blend below, base = the Aera preset's coefficients); "
            "translate_face_landmarks(landmark_moves below), then one more call per extra stage "
            "(landmark_moves2, landmark_moves3; each stage is its own call, in that order); commit_face_state",
            "eyes: the preset's eyes_settings with sclera.use_custom_tint = sclera_custom_tint (both eyes); "
            "commit_eyes_settings",
            "commit_skin_settings (skin below); commit_head_model_settings (eyelashes); commit_makeup_settings",
            "spawn + groom instance parameters on the preview collection; save"],
        "face": {"variant": FINAL["face_variant"],
                 "blend_formula": "per face-model region: out = Aera + sum w_i * (preset_i - Aera) "
                                  "(Scripts/MetaHuman/pb_face_build.py blend, blend_start 1; region groups REGION_GROUPS)",
                 "blend": fv["recipe"]["blend"], "regions": fv["recipe"]["regions"],
                 "implicit_aera_weight_overall": round(1.0 - sum(fv["recipe"]["blend"].values()), 4),
                 "landmark_moves_cm_requested": fv["moves"],
                 "landmark_moves2_cm_requested_second_call": fv.get("moves2"),
                 "landmark_moves3_cm_requested_third_call": fv.get("moves3"),
                 "coeffs_final": res["coeffs_final"], "landmarks_final": res["landmarks_final"]},
        "body": {"constraints_set": FINAL["body"], "constraints_readback": res["constraints"]},
        "identity": {k: FINAL.get(k) for k in ("skin", "makeup", "lashes", "hair", "brows", "groom_params", "eyes",
                                               "sclera_custom_tint", "peachfuzz")},
        "version": FINAL.get("version", 1),
        "previous_version_recipe": "player_female_recipe_v1.json (v1 asset backup: MH_PlayerFemale_v1.uasset.bak)",
        "makeup_detail": C.struct_dict(makeup2(**FINAL["makeup"]) if isinstance(FINAL["makeup"], dict)
                                       else makeup(FINAL["makeup"])),
        "readback_at_build": res["identity"],
        "groom_params_at_build": res["groom_params"],
        "alts": {k: {"face_variant": v, "recipe": faces[v]["recipe"], "moves": faces[v]["moves"]}
                 for k, v in ALTS.items()} if BUILD_ALTS else None,
        "runner_ups_not_saved": {v: {k: faces[v].get(k) for k in ("recipe", "moves", "moves2", "moves3")}
                                 for v in (("K5", "K7") if FINAL.get("version") == 2 else ("F1", "F2", "R4m"))},
        "exploration": "explore1-7 (pf_explore*_1.json, explore*_captures/; 6-7 = beauty pass): presets, blends, skin u/v grid, "
                       "face textures, makeup, hair, body",
        "not_called": ["request_auto_rigging", "request_texture_sources", "build_meta_human"]}
    RECIPE_PATH.write_text(json.dumps(recipe, indent=1, default=str), encoding="utf-8")
    step("recipe written", path=str(RECIPE_PATH))


def verify_job(scene: C.Scene):
    """Fresh session: reload the SAVED MH_PlayerFemale, check identity/coefficients vs the build, capture the set."""
    build = json.loads((C.OUT / f"pf_build_{os.environ.get('PF_BUILD_ATTEMPT', '1')}.json")
                       .read_text(encoding="utf-8"))["build"]
    res = C.REPORT.setdefault("verify", {})
    pf = ue.load_asset(C.PF_PATH)
    if not isinstance(pf, ue.MetaHumanCharacter):
        raise RuntimeError(f"{C.PF_PATH} did not load as a MetaHumanCharacter")
    res["disk_identity"] = identity_readback(pf)
    oks = identity_ok(res["disk_identity"])
    check("disk_identity", all(oks.values()), detail=oks)
    C.open_edit(pf)
    c = C.coeffs(pf)
    res["coeffs_maxdiff_vs_build"] = max(abs(a - b) for a, b in zip(c, build["coeffs_final"]))
    check("face_coeffs_equal_build", res["coeffs_maxdiff_vs_build"] < 1e-5, maxdiff=res["coeffs_maxdiff_vs_build"])
    res["constraints"] = C.constraints(pf)
    dh = abs(res["constraints"]["Height"]["value"] - build["constraints"]["Height"]["value"])
    check("height_equal_build", dh < 1e-2, height=res["constraints"]["Height"]["value"])
    res["can_build_meta_human"] = bool(C.mhs().can_build_meta_human(pf, False))
    actor = C.spawn(pf)
    scene.show_only(actor, [actor])
    yield from warmup(300, 15.0)
    lm = C.landmarks(pf)
    fc = C.face_center_from_landmarks(lm)
    res["hair_probe"] = yield from wait_hair(scene, pf, fc, 900.0)
    check("hair_drawn", res["hair_probe"][-1] < 70, probes=res["hair_probe"][-4:])
    col = C.mhs().get_preview_collection(pf)
    res["groom_params"] = {s: C.instance_params(col, k[1]) for s, k in C.selections(col).items()
                           if s in ("Hair", "Eyebrows", "Eyelashes")}
    gp_ok = all(abs(res["groom_params"].get(s, {}).get(n, -1) - v) < 1e-3
                for s, want in FINAL["groom_params"].items() for n, v in want.items())
    check("groom_params_persisted", gp_ok, params=res["groom_params"])
    res["grooms"] = C.groom_state(actor)
    V = C.views(fc, res["constraints"]["Height"]["value"])
    for vn in ("Face_Front", "Face_TQ_L", "Face_TQ_R", "Face_Profile_L", "Face_Profile_R", "Face_Close", "Eyes",
               "Body_Front", "Body_Side", "Body_Back", "Body_TQ", "Hair_Back34_L", "Hair_Back34_R", "Hair_Back",
               "Hair_Side_L", "Hair_Top", "Hair_Front_High"):
        yield from shoot(scene, f"pf_{vn}.png", V[vn])
    yield from switch(scene, "studio")
    for vn in ("Face_Front", "Face_TQ_L", "Body_Front"):
        yield from shoot(scene, f"pf_{vn}_studio.png", V[vn])
    yield from switch(scene, "ambient")
    C.release_actor(scene, actor, pf)
    step("verify done (nothing saved)")


J1 = [inward((1, 28), 0.2), inward((2, 29), 0.15), inward((68, 46), 0.1), inward((63, 43), 0.1)]
J2 = J1 + [inward((66, 23), 0.1), inward((11, 17), 0.1), inward((3, 30), 0.05)]
J3 = J2 + [{"idx": [8, 62], "d": [0.0, 0.0, 0.1]}, {"idx": [3, 30], "d": [0.0, 0.0, 0.05]}]


def explore5_job(scene: C.Scene):
    """Scratch duplicate of the SAVED MH_PlayerFemale (never saved): extra lower-face narrowing on top of the build."""
    res = C.REPORT.setdefault("explore5", {})
    ex = C.scratch_dup(C.PF_PATH, "PF_X5")
    C.open_edit(ex)
    c0 = C.coeffs(ex)
    lm0 = C.landmarks(ex)
    fc = C.face_center_from_landmarks(lm0)
    V = C.views(fc, 168.0)
    actor = C.spawn(ex)
    scene.show_only(actor, [actor])
    yield from warmup(300, 15.0)
    res["hair_probe"] = yield from wait_hair(scene, ex, fc, 240.0)
    res["variants"] = {}
    for name, moves in (("C0", []), ("J1", J1), ("J2", J2), ("J3", J3)):
        C.set_coeffs(ex, c0)
        flat = C.translate_landmarks(ex, moves) if moves else []
        yield from warmup(60, 2.5)
        res["variants"][name] = {"moves": flat, "coeffs": C.coeffs(ex), "landmarks": C.landmarks(ex)}
        for vn in ("Face_Front", "Face_TQ_L", "Face_Profile_L", "Face_Low"):
            yield from shoot(scene, f"j_{name}_{vn}.png", V[vn])
    C.set_coeffs(ex, c0)
    C.release_actor(scene, actor, ex)
    step("explore5 done (nothing saved)")


# ================================================================================================================
# BEAUTY PASS (Cody, via coordinator): hourglass body + K-pop-idol-aesthetic ADULT face, glass skin, gradient lip
# ================================================================================================================
BODIES = {
    "BA": {"Height": 168.0, "Chest": 92.0, "Underbust": 72.0, "Waist": 61.0, "Hip": 95.0},
    "BB": {"Height": 168.0, "Chest": 95.0, "Underbust": 72.0, "Waist": 60.5, "Hip": 97.0},
    "BC": {"Height": 168.0, "Chest": 94.0, "Waist": 61.0, "Hip": 96.0, "Muscularity": 0.2},
}
EYES_BIGGER = [{"idx": [51, 44, 52, 36, 20, 35], "d": [0.0, 0.0, 0.05]}, {"idx": [53, 37], "d": [0.0, 0.0, -0.03]},
               inward((22, 18), -0.04)]
VLINE = [inward((1, 28), 0.2), inward((2, 29), 0.2), inward((63, 43), 0.15), inward((68, 46), 0.1),
         inward((11, 17), 0.12), inward((66, 23), 0.08), inward((3, 30), 0.08), {"idx": [8, 62], "d": [0.0, 0.05, -0.05]}]
VLINE_STRONG = VLINE + [inward((1, 28), 0.1), inward((2, 29), 0.1), inward((63, 43), 0.08), inward((11, 17), 0.06)]
NOSE_SLIM = [inward((67, 45), 0.06), {"idx": [64], "d": [0.0, -0.03, 0.0]}, inward((70, 74), 0.03)]
BROW_STRAIGHT = [{"idx": [10, 26], "d": [0.0, 0.0, -0.08]}, {"idx": [77, 24], "d": [0.0, 0.0, 0.03]}]


def kpop_variants(D: dict) -> dict:
    base = all_face_variants(D)["F3jEJ3"]
    out = {}
    for name, m3 in (("K1", VLINE + EYES_BIGGER + NOSE_SLIM),
                     ("K2", VLINE_STRONG + EYES_BIGGER + NOSE_SLIM),
                     ("K4", VLINE + EYES_BIGGER + NOSE_SLIM + BROW_STRAIGHT)):
        v = dict(base)
        v["name"] = name
        v["moves3"] = m3
        out[name] = v
    rc = recipe3({"Vivian": .07, "Sunita": .06, "Celeste": .04})
    rc["regions"]["cheeks"] = {"Tuya": .25, "Etta": .3, "Celeste": .15, "Vivian": .15}
    rc["regions"]["jaw"] = {"Tuya": .35, "Etta": .35, "Celeste": .1, "Vivian": .1}
    v = dict(base)
    v.update({"name": "K3", "recipe": rc, "coeffs": mix(D, rc["blend"], rc["regions"]),
              "moves3": VLINE + EYES_BIGGER + NOSE_SLIM})
    out["K3"] = v
    return out


def makeup2(lip_type="NATURAL", lip_opacity=0.35, lip_rough=0.8, blush=0.12, liner=0.35,
            lip_color=(0.5, 0.1, 0.15)):
    m = ue.MetaHumanCharacterMakeupSettings()
    lips = ue.MetaHumanCharacterLipsMakeupProperties()
    lips.type = getattr(ue.MetaHumanCharacterLipsMakeupType, lip_type)
    lips.color = ue.LinearColor(*lip_color, 1.0)
    lips.opacity = lip_opacity
    lips.roughness = lip_rough
    lips.metalness = 0.0
    eyes = ue.MetaHumanCharacterEyeMakeupProperties()
    eyes.type = ue.MetaHumanCharacterEyeMakeupType.THIN_LINER
    eyes.primary_color = ue.LinearColor(0.02, 0.012, 0.01, 1.0)
    eyes.secondary_color = ue.LinearColor(0.0, 0.0, 0.0, 1.0)
    eyes.opacity = liner
    eyes.roughness = 0.75
    eyes.metalness = 0.0
    m.lips = lips
    m.eyes = eyes
    if blush > 0:
        b = ue.MetaHumanCharacterBlushMakeupProperties()
        b.type = ue.MetaHumanCharacterBlushMakeupType.APPLE
        b.color = ue.LinearColor(0.6, 0.15, 0.2, 1.0)
        b.intensity = blush
        b.roughness = 0.6
        m.blush = b
    return m


GLASS_ACCENTS = {"lips": {"saturation": 0.35, "redness": 0.45},
                 "under_eye": {"redness": 0.2, "saturation": 0.3, "lightness": 0.6}}


def body_then_face(ch, body: dict, face: dict) -> dict:
    got = set_body(ch, body)
    apply_face(ch, face)
    C.mhs().commit_face_state(ch)
    return got


def extra_views(fc, height):
    V = C.views(fc, height)
    V["Torso_TQ"] = (C.orbit((0.0, 0.0, height * 0.74), 110.0, 35, 5), (0.0, 0.0, height * 0.74), 30.0)
    V["Torso_Front"] = (C.orbit((0.0, 0.0, height * 0.74), 110.0, 0, 5), (0.0, 0.0, height * 0.74), 30.0)
    return V


def explore6_job(scene: C.Scene):
    res = C.REPORT.setdefault("explore6", {})
    D = load_preset_data()
    K = kpop_variants(D)
    ex = C.scratch_dup(f"{C.PRESET_SRC}/{BASE_PRESET}", "PF_X6")
    res["hair"] = C.set_internal_slot(ex, "Hair", f"{C.GROOM_ROOT}/Hair/WI_Hair_L_Straight")
    res["brows"] = C.set_internal_slot(ex, "Eyebrows", f"{C.GROOM_ROOT}/Eyebrows/WI_Eyebrows_M_FlatThick")
    clear_internal_outfit(ex)
    C.open_edit(ex)
    res["v1_body"] = {k: v["value"] for k, v in C.constraints(ex).items()}
    res["body_got"] = {"BB": body_then_face(ex, BODIES["BB"], K["K1"])}
    sk = FINAL["skin"]
    C.commit_skin(ex, u=sk["u"], v=sk["v"], face_texture_index=sk["face_texture_index"], accents=GLASS_ACCENTS)
    commit_lashes(ex)
    C.mhs().commit_makeup_settings(ex, makeup2())
    actor = C.spawn(ex)
    scene.show_only(actor, [actor])
    yield from warmup(300, 15.0)
    set_groom_colours(ex, FINAL["groom_params"])
    C.mhs().assemble_for_preview(ex)
    yield from warmup(120, 6.0)
    fc = C.face_center_from_landmarks(C.landmarks(ex))
    res["hair_probe"] = yield from wait_hair(scene, ex, fc, 900.0)
    res["grooms"] = C.groom_state(actor)
    # ---- bodies (body first, then the face re-applied) ----
    res["bodies"] = {}
    for bn in ("BA", "BB", "BC"):
        got = body_then_face(ex, BODIES[bn], K["K1"])
        yield from warmup(150, 8.0)
        cons = C.constraints(ex)
        res["bodies"][bn] = {"want": BODIES[bn], "got": got,
                             "all": {k: v["value"] for k, v in cons.items()}}
        step(f"body {bn}", **{k: cons[k]["value"] for k in ("Height", "Chest", "Underbust", "Waist", "Hip", "Fat")})
        fc = C.face_center_from_landmarks(C.landmarks(ex))
        V = extra_views(fc, 168.0)
        for vn in ("Body_Front", "Body_Side", "Body_Back", "Torso_TQ", "Torso_Front", "Face_Front"):
            yield from shoot(scene, f"b_{bn}_{vn}.png", V[vn])
    body_then_face(ex, BODIES["BB"], K["K1"])
    yield from warmup(120, 6.0)
    # ---- faces ----
    res["faces"] = {}
    for kn in ("K1", "K2", "K3", "K4"):
        apply_face(ex, K[kn])
        yield from warmup(60, 2.5)
        lm = C.landmarks(ex)
        res["faces"][kn] = {"coeffs": C.coeffs(ex), "landmarks": lm}
        V = extra_views(C.face_center_from_landmarks(lm), 168.0)
        for vn in ("Face_Front", "Face_TQ_L", "Face_Profile_L", "Face_Close"):
            yield from shoot(scene, f"k_{kn}_{vn}.png", V[vn])
    apply_face(ex, K["K1"])
    yield from warmup(60, 2.5)
    V = extra_views(C.face_center_from_landmarks(C.landmarks(ex)), 168.0)
    # ---- lips / blush / skin glow ----
    for label, mk, rough in (("L1", makeup2(), 1.06),
                             ("L2", makeup2(lip_type="CUPID"), 1.06),
                             ("L3", makeup2(lip_type="HOLLYWOOD", lip_opacity=0.25), 1.06),
                             ("L4", makeup2(lip_opacity=0.45, lip_rough=0.65, blush=0.2), 0.98)):
        C.mhs().commit_makeup_settings(ex, mk)
        C.commit_skin(ex, u=sk["u"], v=sk["v"], face_texture_index=sk["face_texture_index"], accents=GLASS_ACCENTS,
                      roughness=rough)
        yield from warmup(90, 4.0)
        for vn in ("Face_Front", "Face_Close"):
            yield from shoot(scene, f"m_{label}_{vn}.png", V[vn])
    C.mhs().commit_makeup_settings(ex, makeup2())
    C.commit_skin(ex, u=sk["u"], v=sk["v"], face_texture_index=sk["face_texture_index"], accents=GLASS_ACCENTS)
    yield from warmup(60, 3.0)
    for vn in ("Hair_Back34_L", "Hair_Back", "Hair_Side_L", "Face_TQ_R", "Eyes"):
        yield from shoot(scene, f"h_Straight_{vn}.png", V[vn])
    # ---- brow swap (preview collection; binding refit) ----
    try:
        C.set_preview_slot(ex, "Eyebrows", f"{C.GROOM_ROOT}/Eyebrows/WI_Eyebrows_M_Full")
        set_groom_colours(ex, {"Eyebrows": FINAL["groom_params"]["Eyebrows"]})
        C.mhs().assemble_for_preview(ex)
        yield from warmup(600, 60.0)
        res["brow_full_grooms"] = C.groom_state(actor)
        for vn in ("Face_Front", "Face_Close"):
            yield from shoot(scene, f"w_Full_{vn}.png", V[vn])
    except Exception:  # noqa: BLE001
        warn("brow swap: " + traceback.format_exc()[-500:])
    C.release_actor(scene, actor, ex)
    step("explore6 done (nothing saved)")


BODIES["BD"] = {"Height": 168.0, "Chest": 93.5, "Underbust": 72.0, "Waist": 60.5, "Hip": 96.5}
VLINE_XS = VLINE_STRONG + [inward((1, 28), 0.15), inward((2, 29), 0.15), inward((63, 43), 0.1), inward((11, 17), 0.08),
                           inward((66, 23), 0.07), inward((3, 30), 0.04), {"idx": [8, 62], "d": [0.0, 0.05, -0.03]}]
EYES_MORE = EYES_BIGGER + [{"idx": [51, 44, 52, 36, 20, 35], "d": [0.0, 0.0, 0.03]}]


def kpop_variants2(D: dict) -> dict:
    base = all_face_variants(D)["F3jEJ3"]
    rc = recipe3({"Vivian": .07, "Sunita": .06, "Celeste": .04})
    rc["regions"]["cheeks"] = {"Tuya": .2, "Etta": .3, "Celeste": .2, "Vivian": .15}
    rc["regions"]["jaw"] = {"Tuya": .25, "Etta": .3, "Celeste": .2, "Vivian": .15}
    rc["regions"]["chin"] = {"Tuya": .3, "Etta": .3, "Celeste": .15, "Vivian": .1}
    slim = mix(D, rc["blend"], rc["regions"])
    out = {}
    for name, coeffs, recipe, m3 in (("K5", base["coeffs"], base["recipe"], VLINE_XS + EYES_MORE + NOSE_SLIM),
                                     ("K6", slim, rc, VLINE_XS + EYES_MORE + NOSE_SLIM),
                                     ("K7", slim, rc, VLINE_XS + EYES_MORE + NOSE_SLIM + BROW_STRAIGHT)):
        v = dict(base)
        v.update({"name": name, "coeffs": coeffs, "recipe": recipe, "moves3": m3})
        out[name] = v
    return out


def commit_sclera(ch, custom_tint: bool) -> dict:
    eyes = ch.get_editor_property("eyes_settings")
    for side in ("eye_left", "eye_right"):
        e = eyes.get_editor_property(side)
        sc = e.get_editor_property("sclera")
        sc.set_editor_property("use_custom_tint", bool(custom_tint))
        e.set_editor_property("sclera", sc)
        eyes.set_editor_property(side, e)
    C.mhs().commit_eyes_settings(ch, eyes)
    return C.struct_dict(ch.get_editor_property("eyes_settings").get_editor_property("eye_left").get_editor_property("sclera"))


def explore7_job(scene: C.Scene):
    res = C.REPORT.setdefault("explore7", {})
    D = load_preset_data()
    K = kpop_variants2(D)
    ex = C.scratch_dup(f"{C.PRESET_SRC}/{BASE_PRESET}", "PF_X7")
    res["hair"] = C.set_internal_slot(ex, "Hair", f"{C.GROOM_ROOT}/Hair/WI_Hair_L_Straight")
    res["brows"] = C.set_internal_slot(ex, "Eyebrows", f"{C.GROOM_ROOT}/Eyebrows/WI_Eyebrows_M_Full")
    clear_internal_outfit(ex)
    C.open_edit(ex)
    body_then_face(ex, BODIES["BB"], K["K6"])
    sk = FINAL["skin"]
    C.commit_skin(ex, u=sk["u"], v=sk["v"], face_texture_index=sk["face_texture_index"], accents=GLASS_ACCENTS)
    commit_lashes(ex)
    C.mhs().commit_makeup_settings(ex, makeup2(blush=0.3))
    actor = C.spawn(ex)
    scene.show_only(actor, [actor])
    yield from warmup(300, 15.0)
    res["groom_colours"] = set_groom_colours(ex, FINAL["groom_params"])
    C.mhs().assemble_for_preview(ex)
    yield from warmup(120, 6.0)
    fc = C.face_center_from_landmarks(C.landmarks(ex))
    res["hair_probe"] = yield from wait_hair(scene, ex, fc, 900.0)
    col = C.mhs().get_preview_collection(ex)
    res["groom_params"] = {s: C.instance_params(col, k[1]) for s, k in C.selections(col).items()
                           if s in ("Hair", "Eyebrows", "Eyelashes")}
    res["faces"] = {}
    for kn in ("K5", "K6", "K7"):
        apply_face(ex, K[kn])
        yield from warmup(60, 2.5)
        lm = C.landmarks(ex)
        res["faces"][kn] = {"coeffs": C.coeffs(ex), "landmarks": lm}
        V = extra_views(C.face_center_from_landmarks(lm), 168.0)
        for vn in ("Face_Front", "Face_TQ_L", "Face_TQ_R", "Face_Profile_L", "Face_Close"):
            yield from shoot(scene, f"k_{kn}_{vn}.png", V[vn])
    apply_face(ex, K["K6"])
    yield from warmup(60, 2.5)
    V = extra_views(C.face_center_from_landmarks(C.landmarks(ex)), 168.0)
    # ---- eyes: sclera tint off (clearer whites); lower-lid rim with texture 64 ----
    res["sclera_off"] = commit_sclera(ex, False)
    yield from warmup(90, 4.0)
    for vn in ("Eyes", "Face_Close"):
        yield from shoot(scene, f"e_scleraoff_{vn}.png", V[vn])
    C.commit_skin(ex, u=sk["u"], v=sk["v"], face_texture_index=64, accents=GLASS_ACCENTS)
    yield from warmup(90, 4.0)
    for vn in ("Eyes", "Face_Close", "Face_Front"):
        yield from shoot(scene, f"e_t64_{vn}.png", V[vn])
    C.commit_skin(ex, u=sk["u"], v=sk["v"], face_texture_index=sk["face_texture_index"], accents=GLASS_ACCENTS)
    # ---- gradient lip candidates (matte) ----
    for label, mk in (("G1", makeup2(lip_type="CUPID", lip_opacity=0.6, lip_color=(0.55, 0.06, 0.12), blush=0.3)),
                      ("G2", makeup2(lip_type="CUPID", lip_opacity=0.8, lip_color=(0.5, 0.05, 0.1), blush=0.3)),
                      ("G3", makeup2(lip_type="NATURAL", lip_opacity=0.55, lip_color=(0.55, 0.06, 0.12), blush=0.3))):
        C.mhs().commit_makeup_settings(ex, mk)
        yield from warmup(90, 4.0)
        for vn in ("Face_Front", "Face_Close"):
            yield from shoot(scene, f"m_{label}_{vn}.png", V[vn])
    # ---- body BD (compromise) ----
    body_then_face(ex, BODIES["BD"], K["K6"])
    yield from warmup(150, 8.0)
    cons = C.constraints(ex)
    res["body_BD"] = {k: v["value"] for k, v in cons.items()}
    V = extra_views(C.face_center_from_landmarks(C.landmarks(ex)), 168.0)
    for vn in ("Body_Front", "Body_Side", "Torso_TQ", "Torso_Front"):
        yield from shoot(scene, f"b_BD_{vn}.png", V[vn])
    # ---- brow alternative (swap; hair may drop out while the grooms rebuild -- close-ups only) ----
    try:
        C.set_preview_slot(ex, "Eyebrows", f"{C.GROOM_ROOT}/Eyebrows/WI_Eyebrows_S_FlatThin")
        set_groom_colours(ex, {"Eyebrows": FINAL["groom_params"]["Eyebrows"]})
        C.mhs().assemble_for_preview(ex)
        yield from warmup(600, 60.0)
        set_groom_colours(ex, {"Eyebrows": FINAL["groom_params"]["Eyebrows"]})
        yield from warmup(120, 6.0)
        yield from shoot(scene, "w_FlatThin_Face_Close.png", V["Face_Close"])
    except Exception:  # noqa: BLE001
        warn("brow swap: " + traceback.format_exc()[-500:])
    C.release_actor(scene, actor, ex)
    step("explore7 done (nothing saved)")


def final_faces(D: dict) -> dict:
    out = all_face_variants(D)
    out.update(kpop_variants2(D))
    return out


# ---- v2 (beauty pass, chosen from explore6/7): overrides the v1 FINAL above ----
FINAL.update({
    "version": 2,
    "face_variant": "K6",
    "hair": "WI_Hair_L_Straight",
    "brows": "WI_Eyebrows_L_Shaded",    # build 3 used S_FlatThin: too faint at normal distance
    "groom_params": {"Hair": {"Melanin": 0.95, "Redness": 0.05},
                     "Eyebrows": {"Melanin": 0.95, "Redness": 0.1, "Lightness": 0.4},
                     "Eyelashes": {"Melanin": 0.95}},
    "skin": {"u": 0.0, "v": 0.8, "face_texture_index": 49, "accents": GLASS_ACCENTS, "freckles": "NONE",
             "show_top_underwear": True},
    "makeup": {"lip_type": "CUPID", "lip_opacity": 0.38, "lip_rough": 0.8, "lip_color": (0.45, 0.07, 0.12),
               "blush": 0.15, "liner": 0.35},
    "check_lips": "CUPID", "check_blush": "APPLE",
    "sclera_custom_tint": False,
    "body": BODIES["BD"],
})


def main() -> None:
    C.OUT.mkdir(parents=True, exist_ok=True)
    with open(C.STEP_LOG, "a", encoding="utf-8") as fh:
        fh.write(f"\n===== pf_female.py mode={C.MODE} attempt={C.ATTEMPT} {C._now()} =====\n")
    C.assert_locks()
    if not C.REPORT["engine"].startswith("5.8"):
        raise RuntimeError(f"expected UE 5.8.x, got {C.REPORT['engine']}")
    C.REPORT["sha_start"] = C.protected_hashes()
    scene = C.Scene()
    step("scene ready")
    jobs = {"explore1": explore1_job, "explore2": explore2_job, "explore3": explore3_job, "explore4": explore4_job, "build": build_job, "verify": verify_job, "explore5": explore5_job, "explore6": explore6_job, "explore7": explore7_job}
    if C.MODE not in jobs:
        raise ValueError(f"unknown PF_MODE {C.MODE}")
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
