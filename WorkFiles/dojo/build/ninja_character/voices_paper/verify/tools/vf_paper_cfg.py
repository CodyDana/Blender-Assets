"""INDEPENDENT VERIFIER: -game capture config for dj_game_capture.py (window paper, the level AS SAVED).
Views: 3 level cameras + 4 of the change stage's runtime views (V1 V2 V3 V6, same eye / target, for comparison) + 3 NEW
views of the verifier's own (N1 N2 N3: closer and longer looks at the upper windows). Per view: base (no runtime material
change), paperoff (window paper emission x0), shojioff (ONLY the transom shoji MI_DJA_AK_Shoji x0 = the neighbouring lit
paper), neighoff (all other lit paper x0: transom shoji, lantern washi, facade shoji), base2 (repeat: noise mask).
Hall-local metres (x east, y north, z up) -> UE cm via world = hall_local + (22, 24, 0.5), UE = (x, -y, z) x 100."""
import json
import math
from pathlib import Path

HL = (22.0, 24.0, 0.5)
OUT = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\ninja_character\voices_paper\verify\paper")


def ue(p):
    return [round((p[0] + HL[0]) * 100, 1), round(-(p[1] + HL[1]) * 100, 1), round((p[2] + HL[2]) * 100, 1)]


def rot(eye, at):
    dx, dy, dz = at[0] - eye[0], at[1] - eye[1], at[2] - eye[2]
    return [round(math.degrees(math.atan2(dz, math.hypot(dx, dy))), 3), round(math.degrees(math.atan2(dy, dx)), 3)]


POSES = [   # (name, borrowed CineCamera, eye, target, hfov)
    ("V1_EastAisle_to_W", "CU_Lantern", (3.6, 4.5, 1.65), (-6.2, 9.5, 3.3), 78),
    ("V2_WestAisle_to_E", "CU_Taiko", (-3.6, 13.5, 1.65), (6.2, 9.0, 3.3), 78),
    ("V3_Platform_S", "CU_Training", (0.0, 18.6, 2.45), (0.0, 6.0, 3.0), 90),
    ("V6_CourtyardCentreLow", "CU_WallFooting", (0.0, -2.4, 1.2), (0.0, 10.0, 3.1), 84),
    ("N1_Mid_to_W_close", "CU_R4_PavilionTaiko", (-1.5, 10.0, 1.65), (-6.2, 12.0, 3.4), 70),
    ("N2_Mid_to_E_close", "CU_R4_RidgeHall", (1.5, 6.0, 1.65), (6.2, 4.0, 3.4), 70),
    ("N3_North_to_SE_long", "CU_R5_Skyline", (-4.0, 19.0, 1.7), (6.2, 2.0, 3.0), 75),
]
LEVEL_CAMS = ["CAM_AK_CW_WestAisle", "CAM_AK_CX_FromPlatform", "CAM_DoorwayIn"]
PAPER = ["MI_DJA_AK_HWinPaperW", "MI_DJA_AK_HWinPaperE"]
NEIGH = {"MI_DJA_AK_Shoji": "Emissive Intensity", "MI_DJA_AK_HWashi": "Emissive Intensity",
         "M_DJ_ShojiPaper": "EmissiveIntensity"}


def sets():
    on = {p: {"s_mul": {"Emissive Intensity": 1.0}} for p in PAPER}
    on.update({n: {"s_mul": {k: 1.0}} for n, k in NEIGH.items()})
    paperoff = dict(on, **{p: {"s_mul": {"Emissive Intensity": 0.0}} for p in PAPER})
    shojioff = dict(on, **{"MI_DJA_AK_Shoji": {"s_mul": {"Emissive Intensity": 0.0}}})
    neighoff = dict(on, **{n: {"s_mul": {k: 0.0}} for n, k in NEIGH.items()})
    return [("base", None), ("paperoff", paperoff), ("shojioff", shojioff), ("neighoff", neighoff), ("base2", on)]


shots = []
for name, pose in [(c, None) for c in LEVEL_CAMS] + [(p[0], p[1:]) for p in POSES]:
    b = {"name": pose[0] if pose else name, "w": 1920, "h": 1080}
    if pose:
        b["pose"] = {"loc_cm": ue(pose[1]), "rot": rot(ue(pose[1]), ue(pose[2])), "fov": pose[3]}
    for tag, m in sets():
        s = dict(b, out=f"{name}__{tag}")
        if m:
            s["mat"] = m
        shots.append(s)
cfg = {"out_dir": str(OUT).replace("\\", "/"), "report": str(OUT / "game_capture.json").replace("\\", "/"), "shots": shots,
       "warm_s": 30, "warm_per_cam_s": 3, "settle_s": 8, "hide_pawn": True, "shot_timeout_s": 90, "warm_pass": True,
       "census_prefixes": ["SM_AK_Window_Paper", "ISM_SM_AK_Window_Paper", "SM_AK_Window_Lattice", "ISM_SM_AK_Window_Lattice"]}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "cfg.json").write_text(json.dumps(cfg, indent=1), encoding="utf-8")
print(len(shots), "shots")
