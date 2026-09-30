import json, sys
from mk import shot
OUT = sys.argv[1]
IT4 = {"Cloud Coverage": 3.6, "Contrast": 0.6, "High Frequency Noise Amount": 0.5,
       "Volumetric Cloud Ambient Light (Dawn/Dusk)": [0.65, 0.6, 0.72], "Cloud Dark Color (Dawn/Dusk)": [0.09, 0.085, 0.11],
       "Cloud Light Color (Dawn/Dusk)": [1.0, 0.55, 0.3], "Rayleigh Scattering Color (Dawn/Dusk)": [0.4, 0.45, 0.9],
       "All Fog Colors Multiplier": [14.0, 2.8, 1.1], "Base Height Fog Falloff": 0.2, "Fog": 2.0,
       "Layer Height Scale": 0.35, "Volumetric Clouds Scale": 2.5, "Cloud Wisps Opacity (Clear)": 1.0}
RD = ["Overall Intensity", "Macro Variation", "Base Height Fog Falloff", "Contrast", "Layer Height Scale",
      "Volumetric Clouds Scale", "Cloud Density", "Fog", "Sky Light Intensity", "Sun Disk Intensity", "Cloud Wisps Opacity (Clear)"]
def u(**kw):
    d = dict(IT4); d.update({k.replace("_", " "): v for k, v in kw.items()}); return d
b0 = dict(IT4, **{"Cloud Coverage": 2.2, "All Fog Colors Multiplier": [5.0, 1.6, 0.75]})
b1 = dict(IT4, **{"Cloud Coverage": 2.2, "Base Height Fog Falloff": 0.5})
b2 = dict(IT4, **{"Cloud Coverage": 2.2, "All Fog Colors Multiplier": [20.0, 3.5, 1.2], "Base Height Fog Falloff": 0.8})
b3 = dict(b1, **{"Rayleigh Scattering Color (Dawn/Dusk)": [0.3, 0.5, 1.3]})
b4 = dict(b3, **{"Layer Height Scale": 1.0, "Volumetric Clouds Scale": 1.2})
b5 = dict(b3, **{"Cloud Wisps Opacity (Clear)": 0.4})
b6 = dict(b3, **{"Contrast": 0.3, "Volumetric Cloud Ambient Light (Dawn/Dusk)": [0.62, 0.64, 0.85]})
b7 = dict(b3, **{"Overall Intensity": 1.3})
L = [shot("b0_fog_r8", uds=b0, read=RD), shot("b1_fall05", uds=b1), shot("b2_fall08_red", uds=b2), shot("b3_ray", uds=b3),
     shot("b4_cumulus", uds=b4), shot("b5_wisps04", uds=b5), shot("b6_contr03", uds=b6), shot("b7_overall13", uds=b7, read=RD),
     shot("b8_estab_b3", cam="CAM_Establishing", uds=b3)]
cfg = {"out_dir": OUT, "report": OUT + "/game_capture.json", "warm_s": 40, "warm_per_cam_s": 4, "settle_s": 14,
       "shot_timeout_s": 90, "hide_pawn": True, "warm_pass": False,
       "cvars": ["scalability 3", "r.ScreenPercentage 100", "r.HighResScreenshotDelay 8", "t.MaxFPS 60"], "shots": L}
json.dump(cfg, open(OUT + "/cfg.json", "w"), indent=1)
print(len(L), "shots")
