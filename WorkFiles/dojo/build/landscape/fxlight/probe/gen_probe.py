"""FX + LIGHTING stage probes: -game runtime overrides (UDS variables, PPV fields, MIDs, lamps) on the built level,
nothing saved. usage: py -3 gen_probe.py <name>  -> probe/<name>/cfg.json"""
import json, sys
from pathlib import Path
P = Path(__file__).parent
name = sys.argv[1]
D = P / name
D.mkdir(exist_ok=True)
CAMS = {"CAM_Ref2Match": (1920, 1440), "CAM_LandscapeRef": (1280, 1920), "CAM_Drum": (1920, 1080),
        "CU_HallUpperRoof": (1920, 1080), "CAM_RiverRapids": (1920, 1080), "CAM_HallVeranda": (1920, 1080),
        "CAM_PlayerEyeSand": (1920, 1080), "CAM_FromGateOut": (1920, 1080), "CAM_TerraceWall": (1920, 1080),
        "CAM_StairPath": (1920, 1080), "CU_Lantern": (1920, 1080), "CAM_Overview": (1920, 1080), "CAM_EastYard": (1920, 1080), "CU_SandEye": (1920, 1080), "CU_Training": (1920, 1080)}
SETS = json.loads((P / "sets.json").read_text())
shots = []
for set_name in SETS["order"][name]:
    s = SETS["sets"][set_name]
    for cam in s["cams"]:
        w, h = CAMS[cam]
        sh = {"name": cam, "w": w, "h": h, "out": f"{set_name}__{cam}"}
        for k in ("uds", "pp", "mat", "lamps", "cmds"):
            if s.get(k):
                sh[k] = s[k]
        shots.append(sh)
cfg = {"out_dir": str(D).replace("\\", "/"), "report": str(D / "game_capture.json").replace("\\", "/"),
       "warm_s": 75, "warm_per_cam_s": 6, "settle_s": 12, "shot_timeout_s": 120, "hide_pawn": True, "warm_pass": True,
       "cvars": ["scalability 3", "r.ScreenPercentage 100", "r.HighResScreenshotDelay 8", "t.MaxFPS 60"], "shots": shots}
(D / "cfg.json").write_text(json.dumps(cfg, indent=1))
print(len(shots), "shots ->", D / "cfg.json")
