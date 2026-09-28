"""pd_r2_sheets.py -- round-2 before/after sheets + pixel metrics for MH_PlayerDefault (plain Python + Pillow).

Reuses pd_pd_sheets.py (round 1: same crops, same metric definitions) on the round-2 verify captures
(captures/before_* = scratch duplicate of MH_PlayerBase_FaceC, captures/after_* = the saved MH_PlayerDefault, same
session, same pb_conform studio rig + cameras, one MetaHuman in the world at a time) and adds:
  before_after_jawramus.png   posterior jaw ramus: studio / ambient / headlight (geometry-only) / base colour
  jaw_line_vs_kelvin.png      the same JawClose camera on Epic's Kelvin preset (explore2), FaceC and PlayerDefault
  hair_back_r1_vs_r2.png      the hair from behind at 115 / 250 / 380 cm: round 1 (Redness 0.25) vs round 2
Writes image_metrics_r2.json.
usage: py Scripts/MetaHuman/pd_r2_sheets.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pd_pd_sheets as S  # noqa: E402

OUT = S.OUT
CAP = S.CAP
R1 = CAP / "round1"
X2 = OUT / "r2_explore2_captures"


def main():
    sheets = []
    sheets.append(S.sheet("before_after_face.png",
                          [("Face_Front", "Face_Front.png"), ("Face_ThreeQuarter", "Face_ThreeQuarter.png"),
                           ("Face_Profile", "Face_Profile.png")],
                          (170, 180, 870, 1200), 0.62, "Face, studio rig (pb_conform key/fill/rim + sky, same cameras)"))
    sheets.append(S.sheet("before_after_body.png",
                          [("Body_Front", "Body_Front.png"), ("Body_Side", "Body_Side.png"), ("Body_Back", "Body_Back.png")],
                          (250, 60, 750, 1150), 0.7, "Body, studio rig (body geometry identical to MH_PlayerBase)"))
    sheets.append(S.sheet("before_after_hands.png",
                          [("Hand_xneg_Front", "Hand_xneg_Front.png"), ("Hand_xneg_Outer", "Hand_xneg_Outer.png"),
                           ("Hand_xpos_Front", "Hand_xpos_Front.png"), ("Hand_xpos_Outer", "Hand_xpos_Outer.png")],
                          (150, 150, 850, 1050), 0.45, "Hands, studio rig"))
    sheets.append(S.sheet("before_after_jaw.png",
                          [("JawClose studio", "JawClose.png"), ("JawClose +bounce", "JawClose_bounce.png"),
                           ("JawClose eval rig", "JawClose_eval.png"), ("JawClose ambient", "JawClose_ambient.png"),
                           ("JawClose headlight", "JawClose_headlight.png"), ("JawClose base colour", "JawClose_base.png"),
                           ("JawLow studio", "JawLow.png"), ("JawLow ambient", "JawLow_ambient.png")],
                          None, 0.32, "Jaw: studio vs +bounce vs eval vs ambient vs headlight (geometry-only shading) vs base colour"))
    sheets.append(S.sheet("before_after_jawramus.png",
                          [("JawClose studio", "JawClose.png"), ("JawClose ambient", "JawClose_ambient.png"),
                           ("JawClose headlight", "JawClose_headlight.png"), ("JawRamus studio", "JawRamus.png"),
                           ("JawRamus ambient", "JawRamus_ambient.png"), ("JawRamus headlight", "JawRamus_headlight.png"),
                           ("3/4 ambient", "Face_ThreeQuarter_ambient.png"), ("3/4 headlight", "Face_ThreeQuarter_headlight.png")],
                          {"JawClose.png": (560, 150, 960, 650), "JawClose_ambient.png": (560, 150, 960, 650),
                           "JawClose_headlight.png": (560, 150, 960, 650), "Face_ThreeQuarter_ambient.png": (520, 580, 920, 1080),
                           "Face_ThreeQuarter_headlight.png": (520, 580, 920, 1080), "*": (400, 250, 800, 750)}, 0.62,
                          "Posterior jaw ramus (the residual line of defect 1), same cameras"))
    sheets.append(S.sheet("before_after_ear.png",
                          [("EarR studio", "EarR.png"), ("EarR rim spec 0", "EarR_rimspec0.png"),
                           ("EarR no rim", "EarR_norim.png"), ("EarR rim shadow", "EarR_rimshadow.png"),
                           ("EarR eval rig", "EarR_eval.png"), ("EarR ambient", "EarR_ambient.png"),
                           ("EarR base colour", "EarR_base.png"), ("EarRSide studio", "EarRSide.png")],
                          (0, 150, 700, 1100), 0.4,
                          "Image-left ear (character's right): studio rig vs rim-light specular off / rim off / rim shadow vs base colour"))
    sheets.append(S.sheet("before_after_shoulders.png",
                          [("Shoulders_Front", "Shoulders_Front.png"), ("Shoulders_High", "Shoulders_High.png"),
                           ("ShoulderL_TQ", "ShoulderL_TQ.png"), ("ShoulderR_TQ", "ShoulderR_TQ.png"),
                           ("Shoulders_Back", "Shoulders_Back.png"), ("Shoulders_Front base", "Shoulders_Front_base.png"),
                           ("ShoulderL_TQ base", "ShoulderL_TQ_base.png")],
                          None, 0.33, "Shoulder tops, fresh session, one MetaHuman actor in the world (base = albedo on black)"))
    sheets.append(S.sheet("before_after_eyes_hair.png",
                          [("Eyes", "Eyes.png"), ("Head_Back34", "Head_Back34.png"), ("Head_Top", "Head_Top.png"),
                           ("Head_Back_Far", "Head_Back_Far.png")],
                          {"Eyes.png": (0, 380, 1000, 820), "Head_Back_Far.png": (350, 450, 650, 750),
                           "*": (150, 150, 850, 1050)}, 0.55, "Identity: eyes, hair (back 3/4, top, 250 cm behind)"))
    sheets.append(S.sheet("before_after_eval_rig.png",
                          [("Face_Front eval", "Face_Front_eval.png"), ("Face_ThreeQuarter eval", "Face_ThreeQuarter_eval.png"),
                           ("Face_Profile eval", "Face_Profile_eval.png"), ("Head_Back34 eval", "Head_Back34_eval.png"),
                           ("Body_Front eval", "Body_Front_eval.png")],
                          {"Body_Front_eval.png": (250, 60, 750, 1150), "Head_Back34_eval.png": (150, 150, 850, 1050),
                           "*": (170, 180, 870, 1200)}, 0.5,
                          "Evaluation rig = studio + weak unshadowed up-light + rim light casting shadows at 0.3 specular"))
    sheets.append(S.sheet("before_after_ambient.png",
                          [("Face_Front ambient", "Face_Front_ambient.png"),
                           ("Face_ThreeQuarter ambient", "Face_ThreeQuarter_ambient.png"),
                           ("Face_Profile ambient", "Face_Profile_ambient.png"), ("EarR ambient", "EarR_ambient.png"),
                           ("Body_Front ambient", "Body_Front_ambient.png"), ("Body_Back ambient", "Body_Back_ambient.png")],
                          {"Body_Front_ambient.png": (250, 60, 750, 1150), "Body_Back_ambient.png": (250, 60, 750, 1150),
                           "EarR_ambient.png": (0, 150, 700, 1100), "*": (170, 180, 870, 1200)}, 0.5,
                          "Ambient rig = studio key/fill/rim UNCHANGED + the same sky light capturing the grey backdrop"))
    sheets.append(S.strip("jaw_line_vs_kelvin.png",
                          "Posterior ramus, JawClose camera: Epic preset Kelvin (explore2, aligned to our face centre) vs FaceC vs PlayerDefault",
                          [("Kelvin studio", X2 / "k_Kelvin_JawClose_studio.png"), ("BEFORE FaceC studio", CAP / "before_JawClose.png"),
                           ("AFTER PD studio", CAP / "after_JawClose.png"),
                           ("Kelvin ambient", X2 / "k_Kelvin_JawClose_ambient.png"),
                           ("BEFORE FaceC ambient", CAP / "before_JawClose_ambient.png"),
                           ("AFTER PD ambient", CAP / "after_JawClose_ambient.png")],
                          (560, 150, 960, 650), 0.62))
    sheets.append(S.strip("hair_back_r1_vs_r2.png",
                          "Hair from behind: round 1 PlayerDefault (Redness 0.25) vs round 2 (see player_default_recipe.json)",
                          [("round1 Shoulders_Back", R1 / "after_Shoulders_Back.png"), ("round2 Shoulders_Back", CAP / "after_Shoulders_Back.png"),
                           ("round1 Body_Back", R1 / "after_Body_Back.png"), ("round2 Body_Back", CAP / "after_Body_Back.png"),
                           ("round1 Head_Back34", R1 / "after_Head_Back34.png"), ("round2 Head_Back34", CAP / "after_Head_Back34.png")],
                          (300, 60, 700, 460), 0.6))
    sheets.append(S.strip("face_r1_vs_r2.png",
                          "Face: round 1 PlayerDefault (FaceC geometry) vs round 2 (jaw-ramus fix), studio rig",
                          [("round1 Front", R1 / "after_Face_Front.png"), ("round2 Front", CAP / "after_Face_Front.png"),
                           ("round1 3/4", R1 / "after_Face_ThreeQuarter.png"), ("round2 3/4", CAP / "after_Face_ThreeQuarter.png"),
                           ("round1 Profile", R1 / "after_Face_Profile.png"), ("round2 Profile", CAP / "after_Face_Profile.png")],
                          (170, 180, 870, 1200), 0.4))

    m = {"thresholds": {"near_black_maxRGB_lt": 16, "glint_minRGB_ge": 150}}
    for who in ("before", "after"):
        mm = {}
        for v in ("JawClose.png", "JawClose_bounce.png", "JawClose_eval.png", "Face_ThreeQuarter.png",
                  "Face_ThreeQuarter_bounce.png", "Face_ThreeQuarter_eval.png", "Face_Front.png", "Face_Front_bounce.png",
                  "Face_Front_eval.png", "JawLow.png", "JawLow_bounce.png", "JawClose_ambient.png", "JawLow_ambient.png",
                  "Face_ThreeQuarter_ambient.png", "Face_Front_ambient.png"):
            box = (150, 700, 900, 1000) if v.startswith("Face_") else None
            mm["near_black_" + v] = S.near_black_frac(f"{who}_{v}", box=box)
        for v in ("EarR.png", "EarR_rimspec0.png", "EarR_norim.png", "EarR_rimshadow.png", "EarR_eval.png",
                  "EarR_ambient.png", "EarR_base.png"):
            mm["glint_px_ear_" + v] = S.white_count(f"{who}_{v}", thr=150, box=(330, 380, 530, 880))
        for v in ("Face_Front.png", "Face_Front_rimspec0.png", "Face_Front_norim.png", "Face_Front_rimshadow.png",
                  "Face_Front_eval.png", "Face_Front_ambient.png"):
            mm["glint_px_imageLeftEar_" + v] = S.white_count(f"{who}_{v}", thr=150, box=(240, 560, 320, 760))
        for v, box in S.SHOULDER_BOXES.items():
            mm["seethrough_holes_px_" + v] = S.enclosed_background(f"{who}_{v}", box)
        m[who] = mm
    for tag, z in (("front", "Front"), ("side", "Side")):
        a = S.mask_ortho(f"after_Ortho_{z}.png", 148.0)
        b = S.mask_ortho(f"before_Ortho_{z}.png", 148.0)
        m[f"ortho_{tag}_below_z148_silhouette"] = {"after_px": len(a), "before_px": len(b), "xor_px": len(a ^ b),
                                                  "iou": round(len(a & b) / max(1, len(a | b)), 6)}
    m["sheets"] = sheets
    (OUT / "image_metrics_r2.json").write_text(json.dumps(m, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in m.items() if k != "sheets"}, indent=1))


if __name__ == "__main__":
    main()
