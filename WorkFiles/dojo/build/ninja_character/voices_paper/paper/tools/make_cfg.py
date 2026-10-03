"""voices_paper stage, B (window paper at sunset): -game capture configs for dj_game_capture.py.
Views: level cameras + runtime poses (probe_pose; a borrowed CineCamera is moved, nothing saved), given in the hall frame
(hall-local metres, x east / y north / z up from the hall floor; Blender world = +(22, 24, 0.5); UE cm = (x, -y, z) x 100).
Per view: base, paper OFF (paper emission x0: the paper mask by difference), neighbours OFF (the other lit paper: the
armory shoji MI_DJA_AK_Shoji, the lantern washi MI_DJA_AK_HWashi, the hall's facade shoji M_DJ_ShojiPaper), then
candidates (paper emission x k, optional day tint). Usage: make_cfg.py <stage> <out_dir> [variants json]"""
import json
import math
import sys
from pathlib import Path

HL = (22.0, 24.0, 0.5)


def ue(p):
    x, y, z = p[0] + HL[0], p[1] + HL[1], p[2] + HL[2]
    return [round(x * 100, 1), round(-y * 100, 1), round(z * 100, 1)]


def rot(eye, at):
    """eye / at already in UE cm (explore run 1 negated y twice: mirrored yaw)"""
    dx, dy, dz = at[0] - eye[0], at[1] - eye[1], at[2] - eye[2]
    return [round(math.degrees(math.atan2(dz, math.hypot(dx, dy))), 3), round(math.degrees(math.atan2(dy, dx)), 3)]


# (name, borrowed camera, eye hall-local, look-at hall-local, hfov)
POSES = [
    ("V1_EastAisle_to_W", "CU_Lantern", (3.6, 4.5, 1.65), (-6.2, 9.5, 3.3), 78),
    ("V2_WestAisle_to_E", "CU_Taiko", (-3.6, 13.5, 1.65), (6.2, 9.0, 3.3), 78),
    ("V3_Platform_S", "CU_Training", (0.0, 18.6, 2.45), (0.0, 6.0, 3.0), 90),
    ("V4_CourtyardDoor", "CU_SandEye", (2.2, -4.0, 1.7), (-6.2, 6.0, 3.6), 70),
    ("V6_CourtyardCentreLow", "CU_WallFooting", (0.0, -2.4, 1.2), (0.0, 10.0, 3.1), 84),
    ("V5_CourtyardSteps", "CU_GateFront", (-1.5, -2.6, 1.6), (6.2, 5.0, 3.6), 70),
]
LEVEL_CAMS = ["CAM_AK_CW_WestAisle", "CAM_AK_CX_FromPlatform", "CAM_DoorwayIn"]
PAPER = ["MI_DJA_AK_HWinPaperW", "MI_DJA_AK_HWinPaperE"]
NEIGH = {"MI_DJA_AK_Shoji": "Emissive Intensity", "MI_DJA_AK_HWashi": "Emissive Intensity",
         "M_DJ_ShojiPaper": "EmissiveIntensity"}
NIGHT_TINT = [0.30, 0.45, 1.0]   # the copied ArmoryLab MIs' Emissive Tint (ak_common NIGHT_EMIT, render_armory)


def mat(paper_k=1.0, tint=None, neigh_k=1.0):
    m = {p: {"s_mul": {"Emissive Intensity": paper_k}, "v": {"Emissive Tint": tint or NIGHT_TINT}} for p in PAPER}
    for n, prm in NEIGH.items():
        m[n] = {"s_mul": {prm: neigh_k}}
    return m

def final_sets():
    """after the change: the base is the level as saved (no runtime material change at all); the masks switch only
    the emission off (no tint written)"""
    off = {p: {"s_mul": {"Emissive Intensity": 0.0}} for p in PAPER}
    noff = {n: {"s_mul": {prm: 0.0}} for n, prm in NEIGH.items()}
    on = {p: {"s_mul": {"Emissive Intensity": 1.0}} for p in PAPER}   # = the saved MI value (no tint written)
    on.update({n: {"s_mul": {prm: 1.0}} for n, prm in NEIGH.items()})
    return [("base", on), ("paperoff", dict(on, **off)), ("neighoff", dict(on, **noff)), ("base2", on)]


def main():
    stage, out_dir = sys.argv[1], Path(sys.argv[2])
    variants = json.loads(sys.argv[3]) if len(sys.argv) > 3 else []   # [[tag, paper_k, tint or null], ...]
    views = [(c, None) for c in LEVEL_CAMS] + [(n, (cam, e, a, f)) for n, cam, e, a, f in POSES]
    shots = []
    for name, pose in views:
        cam = pose[0] if pose else name
        base = {"name": cam, "w": 1920, "h": 1080}
        if pose:
            base["pose"] = {"loc_cm": ue(pose[1]), "rot": rot(ue(pose[1]), ue(pose[2])), "fov": pose[3]}
        if stage == "final":
            sets = final_sets()
        else:
            sets = [("base", mat()), ("paperoff", mat(0.0)), ("neighoff", mat(neigh_k=0.0))]
            sets += [(t, mat(k, tint)) for t, k, tint in variants] + [("base2", mat())]
        for tag, m in sets:
            sh = dict(base, out=f"{name}__{tag}")
            if m:
                sh["mat"] = m
            shots.append(sh)
    cfg = {"out_dir": str(out_dir).replace("\\", "/"), "report": str(out_dir / "game_capture.json").replace("\\", "/"),
           "shots": shots, "warm_s": 30, "warm_per_cam_s": 4, "settle_s": 8, "hide_pawn": True, "shot_timeout_s": 90,
           "warm_pass": True, "stage": stage,
           "census_prefixes": ["SM_AK_Window_Paper", "ISM_SM_AK_Window_Paper", "SM_AK_Window_Lattice",
                               "ISM_SM_AK_Window_Lattice"]}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cfg.json").write_text(json.dumps(cfg, indent=1), encoding="utf-8")
    print(len(shots), "shots ->", out_dir / "cfg.json")


main()
