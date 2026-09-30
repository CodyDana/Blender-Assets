import json, sys
from mk import shot
OUT = sys.argv[1]
PP = {"film_toe": 0.62, "local_exposure_shadow_contrast_scale": 0.85, "local_exposure_highlight_contrast_scale": 0.7}
UDS = {"Cloud Coverage": 2.6, "Contrast": 0.3, "High Frequency Noise Amount": 0.35,
       "Volumetric Cloud Ambient Light (Dawn/Dusk)": [0.62, 0.64, 0.85], "Cloud Dark Color (Dawn/Dusk)": [0.1, 0.1, 0.14],
       "Cloud Light Color (Dawn/Dusk)": [1.0, 0.62, 0.4], "Rayleigh Scattering Color (Dawn/Dusk)": [0.42, 0.5, 1.0],
       "All Fog Colors Multiplier": [18.0, 3.6, 1.3], "Sky Light Intensity": 3.4}
MAT = {"M_DJ_RoofTile": {"s": {"ValueMult": 1.6}, "v": {"Tint": [0.85, 0.93, 1.12], "MeanColour": [0.05, 0.054, 0.068]}},
       "M_DJ_ShojiPaper": {"s": {"Saturation": 0.9}}, "M_DJS_ShojiClere": {"s": {"Saturation": 0.9}},
       "M_DKG_SandRaked": {"s": {"RakeWarp": 0.004, "RakeWarpU": 0.002, "NormalVar": 0.1}}}
EMIS = {"M_DJ_ShojiPaper": 0.78, "M_DJS_ShojiClere": 0.78}
LAMPS = {"Light_DKP_Stone_LanternTall": {"mult": 0.5, "radius_cm": 700.0}, "Light_DKP_Modern_WallLamp": {"mult": 0.75, "radius_cm": 800.0}}
C1 = dict(pp=PP, uds=UDS, mat=MAT, emis=EMIS, lamps=LAMPS)
L = [shot("a0_base")]
L.append(shot("a1_c1", **C1))
L.append(shot("a2_c1_east", cam="CAM_EastYard", **C1))
L.append(shot("a3_c1_ver", cam="CAM_HallVeranda", **C1))
L.append(shot("a4_c1_roof", cam="CU_HallUpperRoof", **C1))
L.append(shot("a5_c1_estab", cam="CAM_Establishing", **C1))
L.append(shot("a6_c1_skyl", cam="CU_R5_Skyline", **C1))
L.append(shot("a7_cov22", uds=dict(UDS, **{"Cloud Coverage": 2.2}), pp=PP, mat=MAT, emis=EMIS, lamps=LAMPS))
L.append(shot("a8_east_soft", cam="CAM_EastYard", uds=dict(UDS, **{"Cloud Coverage": 2.2, "Directional Inscattering Multiplier": 0.4, "Sun Disk Intensity": 0.5}),
              pp=dict(PP, film_shoulder=0.4), mat=MAT, emis=EMIS, lamps=LAMPS, read=["Directional Inscattering Multiplier", "Sun Disk Intensity", "Cloud Coverage"]))
cfg = {"out_dir": OUT, "report": OUT + "/game_capture.json", "warm_s": 40, "warm_per_cam_s": 4, "settle_s": 14,
       "shot_timeout_s": 90, "hide_pawn": True, "warm_pass": False,
       "cvars": ["scalability 3", "r.ScreenPercentage 100", "r.HighResScreenshotDelay 8", "t.MaxFPS 60"], "shots": L}
json.dump(cfg, open(OUT + "/cfg.json", "w"), indent=1)
print(len(L), "shots")
