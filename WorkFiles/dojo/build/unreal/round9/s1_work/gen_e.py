import json
from mk import shot
PP = {"film_grain_intensity": 0.1, "film_toe": 0.62, "local_exposure_shadow_contrast_scale": 1.0, "film_slope": 0.88}
BASE = {"Sun Source Angle Scale": 3.0, "Sky Light Intensity": 2.2, "Sun Light Intensity": 4.0,
        "Fog": 1.8, "Cloud Coverage": 3.2, "Cloud Light Color (Dawn/Dusk)": [1.0, 0.55, 0.3],
        "Sun Light Color": [0.94, 0.94, 1.0], "Sky Light Color Multiplier (Dawn/Dusk)": [0.58, 1.3, 1.5],
        "Rayleigh Scattering Color (Dawn/Dusk)": [0.42, 0.42, 0.62], "Saturation": 1.0, "Contrast": 0.4,
        "All Fog Colors Multiplier": [6.5, 1.75, 0.85], "Lighting Brightness (Dawn/Dusk)": 3.2}
MAT = {"M_DJ_RoofTile": {"s": {"ValueMult": 2.0}, "v": {"Tint": [0.96, 1.15, 1.9], "MeanColour": [0.05, 0.055, 0.095]}},
       "M_DJ_ShojiPaper": {"s_mul": {"EmissiveIntensity": 0.82}, "v": {"EmissiveTint": [1.0, 0.53, 0.26]}},
       "M_DJ_ShojiPaper@SM_DKH_Bay_ClereFrieze": {"s_mul": {"EmissiveIntensity": 0.82 * 0.65}},
       "M_DJ_GlassAmber": {"s_mul": {"EmissiveIntensity": 1.4}, "v": {"EmissiveTint": [1.0, 0.48, 0.13]}},
       "M_DJ_PlasterCream": {"v": {"Tint": [1.0, 0.92, 1.02]}},
       "M_DKG_Gravel": {"v": {"Tint": [1.0, 0.9, 0.9]}}, "M_DKG_GravelCoarse": {"v": {"Tint": [1.0, 0.9, 0.9]}},
       "M_DKG_SandRaked": {"v": {"Tint": [1.0, 0.9, 0.82]}}, "M_DKG_SandEdge": {"v": {"Tint": [1.0, 0.9, 0.82]}}}
LAMPS = {"Light_DKP_Stone_LanternTall": {"mult": 2.0, "radius_cm": 1200.0}, "Light_DKP_Modern_WallLamp": {"mult": 2.0, "radius_cm": 1000.0}}
L = []
L.append(shot("e1_lb32", bias=1.1, pp=PP, uds=BASE, mat=MAT, lamps=LAMPS))
L.append(shot("e2_slope084_toe066", bias=1.1, pp=dict(PP, film_slope=0.84, film_toe=0.66), mat=MAT, lamps=LAMPS))
L.append(shot("e2e", cam="CAM_Establishing", bias=1.1, pp=dict(PP, film_slope=0.84, film_toe=0.66), mat=MAT, lamps=LAMPS))
L.append(shot("e2p", cam="CAM_PlayerEyeSand", bias=1.1, pp=dict(PP, film_slope=0.84, film_toe=0.66), mat=MAT, lamps=LAMPS))
L.append(shot("e3_sky25_b10", bias=1.0, pp=dict(PP, film_slope=0.84, film_toe=0.66), uds={"Sky Light Intensity": 2.5}, mat=MAT, lamps=LAMPS))
L.append(shot("e4_lb28_b12", bias=1.2, pp=dict(PP, film_slope=0.84, film_toe=0.66), uds={"Sky Light Intensity": 2.5, "Lighting Brightness (Dawn/Dusk)": 2.8}, mat=MAT, lamps=LAMPS))
L.append(shot("e4e", cam="CAM_Establishing", bias=1.2, pp=dict(PP, film_slope=0.84, film_toe=0.66), mat=MAT, lamps=LAMPS))
open("shots_e.txt", "w").write(json.dumps(L, indent=0))
