import json
from mk import shot
PP = {"film_grain_intensity": 0.1, "film_toe": 0.62, "local_exposure_shadow_contrast_scale": 1.0}
BASE = {"Sun Source Angle Scale": 3.0, "Sky Light Intensity": 2.2, "Sun Light Intensity": 4.0,
        "Fog": 1.8, "Cloud Coverage": 3.2, "Cloud Light Color (Dawn/Dusk)": [1.0, 0.55, 0.3],
        "Sun Light Color": [0.9, 0.96, 1.0], "Sky Light Color Multiplier (Dawn/Dusk)": [0.55, 1.35, 1.45],
        "Rayleigh Scattering Color (Dawn/Dusk)": [0.42, 0.42, 0.55], "Saturation": 1.0, "Contrast": 0.3,
        "All Fog Colors Multiplier": [6.0, 2.0, 0.8]}
MAT = {"M_DJ_RoofTile": {"s": {"ValueMult": 2.0}, "v": {"Tint": [0.8, 1.3, 1.7], "MeanColour": [0.042, 0.062, 0.085]}},
       "M_DJ_ShojiPaper": {"s_mul": {"EmissiveIntensity": 0.82}, "v": {"EmissiveTint": [1.0, 0.53, 0.26]}},
       "M_DJ_ShojiPaper@SM_DKH_Bay_ClereFrieze": {"s_mul": {"EmissiveIntensity": 0.82 * 0.65}},
       "M_DJ_GlassAmber": {"s_mul": {"EmissiveIntensity": 1.4}, "v": {"EmissiveTint": [1.0, 0.5, 0.14]}}}
LAMPS = {"Light_DKP_Stone_LanternTall": {"mult": 2.0, "radius_cm": 1200.0}, "Light_DKP_Modern_WallLamp": {"mult": 2.0, "radius_cm": 1000.0}}
L = []
L.append(shot("d1_neutral", bias=1.1, pp=PP, uds=BASE, mat=MAT, lamps=LAMPS))
L.append(shot("d1e_neutral", cam="CAM_Establishing", bias=1.1, pp=PP, mat=MAT, lamps=LAMPS))
L.append(shot("d1p_neutral", cam="CAM_PlayerEyeSand", bias=1.1, pp=PP, mat=MAT, lamps=LAMPS))
L.append(shot("d2_sun34_b12", bias=1.2, pp=PP, uds={"Sun Light Intensity": 3.4}, mat=MAT, lamps=LAMPS))
L.append(shot("d3_d1_slope084", bias=1.1, pp=dict(PP, film_slope=0.84), uds={"Sun Light Intensity": 4.0}, mat=MAT, lamps=LAMPS))
L.append(shot("d4_d1_contrast05", bias=1.1, pp=PP, uds={"Contrast": 0.5, "Cloud Coverage": 3.6}, mat=MAT, lamps=LAMPS))
L.append(shot("d4e_d1_contrast05", cam="CAM_Establishing", bias=1.1, pp=PP, mat=MAT, lamps=LAMPS))
open("shots_d.txt", "w").write(json.dumps(L, indent=0))
