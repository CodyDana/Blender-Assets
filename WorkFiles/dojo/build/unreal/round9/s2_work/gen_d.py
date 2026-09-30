import json, sys
from mk import shot
OUT = sys.argv[1]
SKY = {"Cloud Coverage": 3.2, "Macro Variation": 0.5, "Contrast": 0.45, "High Frequency Noise Amount": 0.5,
       "Volumetric Cloud Ambient Light (Dawn/Dusk)": [0.65, 0.6, 0.72], "Cloud Dark Color (Dawn/Dusk)": [0.09, 0.085, 0.11],
       "Cloud Light Color (Dawn/Dusk)": [1.0, 0.55, 0.3], "Rayleigh Scattering Color (Dawn/Dusk)": [0.3, 0.4, 1.0],
       "All Fog Colors Multiplier": [18.0, 2.6, 1.2], "Base Height Fog Falloff": 0.5, "Fog": 2.0,
       "Layer Height Scale": 1.0, "Volumetric Clouds Scale": 1.2, "Cloud Wisps Opacity (Clear)": 0.5,
       "Lighting Brightness (Dawn/Dusk)": 1.6, "Sky Light Color Multiplier (Dawn/Dusk)": [0.8, 1.0, 1.15],
       "Sky Light Intensity": 3.2}
B = 1.2 + 0.5  # it4 bias + log2(2.4 / 1.6) (the lighting brightness drop)
PP = {"film_toe": 0.7, "local_exposure_shadow_contrast_scale": 0.7, "local_exposure_highlight_contrast_scale": 0.7}
TIMB = {k: {"s": {"Saturation": 0.26}} for k in ("M_DJ_TimberDark", "M_DJ_TimberDarkEnd", "M_DJ_TimberAged", "M_DJ_TimberAgedEnd")}
SAND = {"M_DKG_SandRaked": {"s": {"RakeWarp": 0.004, "RakeWarpU": 0.002, "NormalVar": 0.1, "UV Scale": 0.72, "ValueMult": 1.0}},
        "M_DKG_SandEdge": {"s": {"ValueMult": 1.0}}}
R1 = {"M_DJ_RoofTile": {"s": {"ValueMult": 1.75}, "v": {"Tint": [0.85, 0.97, 1.3], "MeanColour": [0.045, 0.05, 0.072]}}}
R2 = {"M_DJ_RoofTile": {"s": {"ValueMult": 1.7}, "v": {"Tint": [0.8, 0.93, 1.25], "MeanColour": [0.042, 0.047, 0.068]}}}
SH = {"M_DJ_ShojiPaper": {"s": {"Saturation": 0.9}}, "M_DJS_ShojiClere": {"s": {"Saturation": 0.9}}}
EMIS = {"M_DJ_ShojiPaper": 0.78, "M_DJS_ShojiClere": 0.78}
LAMPS = {"Light_DKP_Stone_LanternTall": {"mult": 0.5, "radius_cm": 700.0}, "Light_DKP_Modern_WallLamp": {"mult": 0.75, "radius_cm": 800.0}}
def full(roof, **kw):
    return dict(bias=B, pp=PP, mat={**roof, **SH, **TIMB, **SAND}, emis=EMIS, lamps=LAMPS, **kw)
L = [shot("d1_r1", uds=SKY, **full(R1)), shot("d2_r2", **full(R2)),
     shot("d3_roof_r1", cam="CU_HallUpperRoof", **full(R1)), shot("d4_roof_r2", cam="CU_HallUpperRoof", **full(R2)),
     shot("d5_ver", cam="CAM_HallVeranda", **full(R1)), shot("d6_east", cam="CAM_EastYard", **full(R1)),
     shot("d7_drum", cam="CAM_Drum", **full(R1)), shot("d8_gate", cam="CAM_GateFromStreet", **full(R1)),
     shot("d9_over", cam="CAM_Overview", **full(R1)), shot("d10_estab", cam="CAM_Establishing", **full(R1))]
cfg = {"out_dir": OUT, "report": OUT + "/game_capture.json", "warm_s": 40, "warm_per_cam_s": 4, "settle_s": 14,
       "shot_timeout_s": 90, "hide_pawn": True, "warm_pass": False,
       "cvars": ["scalability 3", "r.ScreenPercentage 100", "r.HighResScreenshotDelay 8", "t.MaxFPS 60"], "shots": L}
json.dump(cfg, open(OUT + "/cfg.json", "w"), indent=1)
print(len(L), "shots")
