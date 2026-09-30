import json, sys
from mk import shot
OUT = sys.argv[1]
exec(open("gen_d.py").read().split("L = [")[0].split("OUT = sys.argv[1]")[1])   # SKY, PP, TIMB, SAND, R1, R2, SH, EMIS, LAMPS
SKY = dict(SKY, **{"Lighting Brightness (Dawn/Dusk)": 1.2, "All Fog Colors Multiplier": [16.0, 4.0, 1.2], "Fog": 2.3,
                   "Sky Light Color Multiplier (Dawn/Dusk)": [0.7, 1.28, 1.25], "Sky Light Intensity": 4.0})
PP = dict(PP, local_exposure_shadow_contrast_scale=0.65)
F = dict(bias=1.6, pp=PP, mat={**R1, **SH, **TIMB, **SAND}, emis=EMIS, lamps=LAMPS)
cams = ["CAM_Ref2Match", "CAM_Establishing", "CAM_PlayerEyeSand", "CAM_Overview", "CAM_GateFromStreet", "CAM_HallVeranda",
        "CU_HallUpperRoof", "CU_R5_Skyline", "CAM_EastYard", "CAM_Drum", "CU_R4_StorehouseFront", "CAM_EstablishingRef2"]
L = [shot(c, cam=c, uds=SKY if i == 0 else None, **F) for i, c in enumerate(cams)]
for s in L:
    s.pop("out")
cfg = {"out_dir": OUT, "report": OUT + "/game_capture.json", "warm_s": 40, "warm_per_cam_s": 4, "settle_s": 14,
       "shot_timeout_s": 90, "hide_pawn": True, "warm_pass": False,
       "cvars": ["scalability 3", "r.ScreenPercentage 100", "r.HighResScreenshotDelay 8", "t.MaxFPS 60"], "shots": L}
json.dump(cfg, open(OUT + "/cfg.json", "w"), indent=1)
print(len(L), "shots")
