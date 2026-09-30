import json, sys
from mk import shot
OUT = sys.argv[1]
IT4 = {"Cloud Coverage": 3.6, "Contrast": 0.6, "High Frequency Noise Amount": 0.5,
       "Volumetric Cloud Ambient Light (Dawn/Dusk)": [0.65, 0.6, 0.72], "Cloud Dark Color (Dawn/Dusk)": [0.09, 0.085, 0.11],
       "Cloud Light Color (Dawn/Dusk)": [1.0, 0.55, 0.3], "Rayleigh Scattering Color (Dawn/Dusk)": [0.4, 0.45, 0.9],
       "All Fog Colors Multiplier": [14.0, 2.8, 1.1], "Base Height Fog Falloff": 0.2, "Fog": 2.0,
       "Layer Height Scale": 0.35, "Volumetric Clouds Scale": 2.5, "Cloud Wisps Opacity (Clear)": 1.0,
       "Lighting Brightness (Dawn/Dusk)": 2.4, "Sky Light Color Multiplier (Dawn/Dusk)": [0.62, 1.25, 1.4], "Macro Variation": 0.16}
COM = dict(IT4, **{"Base Height Fog Falloff": 0.5, "Cloud Wisps Opacity (Clear)": 0.5, "Contrast": 0.45, "Cloud Coverage": 2.8,
                   "Layer Height Scale": 1.0, "Volumetric Clouds Scale": 1.2, "Lighting Brightness (Dawn/Dusk)": 2.0})
c1 = dict(COM, **{"Rayleigh Scattering Color (Dawn/Dusk)": [0.22, 0.4, 1.0]})
c2 = dict(COM, **{"Rayleigh Scattering Color (Dawn/Dusk)": [0.3, 0.4, 1.0]})
c3 = dict(c2, **{"Cloud Coverage": 3.2, "Macro Variation": 0.5})
c4 = dict(c2, **{"Sky Light Color Multiplier (Dawn/Dusk)": [0.75, 1.05, 1.2]})
B = 1.46
PP = {"film_toe": 0.72, "local_exposure_shadow_contrast_scale": 0.85, "local_exposure_highlight_contrast_scale": 0.7}
MAT = {"M_DJ_RoofTile": {"s": {"ValueMult": 1.6}, "v": {"Tint": [0.76, 0.9, 1.22], "MeanColour": [0.041, 0.044, 0.063]}},
       "M_DJ_ShojiPaper": {"s": {"Saturation": 0.9}}, "M_DJS_ShojiClere": {"s": {"Saturation": 0.9}},
       "M_DKG_SandRaked": {"s": {"RakeWarp": 0.004, "RakeWarpU": 0.002, "NormalVar": 0.1}},
       **{k: {"s": {"Saturation": 0.26}} for k in ("M_DJ_TimberDark", "M_DJ_TimberDarkEnd", "M_DJ_TimberAged", "M_DJ_TimberAgedEnd")}}
EMIS = {"M_DJ_ShojiPaper": 0.78, "M_DJS_ShojiClere": 0.78}
LAMPS = {"Light_DKP_Stone_LanternTall": {"mult": 0.5, "radius_cm": 700.0}, "Light_DKP_Modern_WallLamp": {"mult": 0.75, "radius_cm": 800.0}}
FULL = dict(bias=B, pp=PP, mat=MAT, emis=EMIS, lamps=LAMPS)
L = [shot("c1_ray22", bias=B, uds=c1), shot("c2_ray30", bias=B, uds=c2), shot("c3_cov32", bias=B, uds=c3),
     shot("c4_skl", bias=B, uds=c4), shot("c5_full", uds=c2, **FULL),
     shot("c6_east", cam="CAM_EastYard", **FULL), shot("c7_ver", cam="CAM_HallVeranda", **FULL),
     shot("c8_roof", cam="CU_HallUpperRoof", **FULL), shot("c9_estab", cam="CAM_Establishing", **FULL),
     shot("c10_skyl", cam="CU_R5_Skyline", **FULL)]
cfg = {"out_dir": OUT, "report": OUT + "/game_capture.json", "warm_s": 40, "warm_per_cam_s": 4, "settle_s": 14,
       "shot_timeout_s": 90, "hide_pawn": True, "warm_pass": False,
       "cvars": ["scalability 3", "r.ScreenPercentage 100", "r.HighResScreenshotDelay 8", "t.MaxFPS 60"], "shots": L}
json.dump(cfg, open(OUT + "/cfg.json", "w"), indent=1)
print(len(L), "shots")
