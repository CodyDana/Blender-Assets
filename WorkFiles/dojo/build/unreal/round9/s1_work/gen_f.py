import json
from mk import shot
PP = {"film_grain_intensity": 0.1, "film_toe": 0.66, "local_exposure_shadow_contrast_scale": 1.0, "film_slope": 0.84}
BASE = {"Sun Source Angle Scale": 3.0, "Sky Light Intensity": 2.5, "Sun Light Intensity": 4.0,
        "Fog": 1.3, "Cloud Coverage": 3.2, "Cloud Light Color (Dawn/Dusk)": [1.0, 0.55, 0.3],
        "Sun Light Color": [0.94, 0.94, 1.0], "Sky Light Color Multiplier (Dawn/Dusk)": [0.58, 1.3, 1.5],
        "Rayleigh Scattering Color (Dawn/Dusk)": [0.45, 0.47, 0.75], "Saturation": 1.0, "Contrast": 0.4,
        "All Fog Colors Multiplier": [8.0, 2.1, 1.0], "Lighting Brightness (Dawn/Dusk)": 2.8}
MAT = {"M_DJ_RoofTile": {"s": {"ValueMult": 2.0}, "v": {"Tint": [1.12, 2.0, 2.4], "MeanColour": [0.058, 0.096, 0.119]}},
       "M_DJ_ShojiPaper": {"s_mul": {"EmissiveIntensity": 0.82}, "v": {"EmissiveTint": [1.0, 0.55, 0.34]}},
       "M_DJ_ShojiPaper@SM_DKH_Bay_ClereFrieze": {"s_mul": {"EmissiveIntensity": 0.82 * 0.65}},
       "M_DJ_GlassAmber": {"s_mul": {"EmissiveIntensity": 1.4}, "v": {"EmissiveTint": [1.0, 0.44, 0.13]}},
       "M_DJ_PlasterCream": {"s": {"Saturation": 0.12, "ValueMult": 1.9}, "v": {"Tint": [1.0, 0.92, 1.02]}},
       "M_DKG_Gravel": {"s": {"Saturation": 0.45, "ValueMult": 1.4}, "v": {"Tint": [1.0, 0.9, 0.9]}},
       "M_DKG_GravelCoarse": {"s": {"Saturation": 0.45, "ValueMult": 1.55}, "v": {"Tint": [1.0, 0.9, 0.9]}},
       "M_DKG_SandRaked": {"v": {"Tint": [1.0, 0.9, 0.82]}}, "M_DKG_SandEdge": {"v": {"Tint": [1.0, 0.9, 0.82]}},
       "M_DJ_TimberDark": {"s": {"Saturation": 0.45}}, "M_DJ_TimberDarkEnd": {"s": {"Saturation": 0.45}},
       "M_DJ_TimberAged": {"s": {"Saturation": 0.45}}, "M_DJ_TimberAgedEnd": {"s": {"Saturation": 0.45}}}
LAMPS = {"Light_DKP_Stone_LanternTall": {"mult": 2.0, "radius_cm": 1200.0}, "Light_DKP_Modern_WallLamp": {"mult": 2.0, "radius_cm": 1000.0}}
L = []
L.append(shot("f1", bias=1.2, pp=PP, uds=BASE, mat=MAT, lamps=LAMPS))
L.append(shot("f1e", cam="CAM_Establishing", bias=1.2, pp=PP, mat=MAT, lamps=LAMPS))
L.append(shot("f1p", cam="CAM_PlayerEyeSand", bias=1.2, pp=PP, mat=MAT, lamps=LAMPS))
L.append(shot("f1v", cam="CAM_HallVeranda", bias=1.2, pp=PP, mat=MAT, lamps=LAMPS))
L.append(shot("f2_sun34_b13", bias=1.3, pp=PP, uds={"Sun Light Intensity": 3.4}, mat=MAT, lamps=LAMPS))
L.append(shot("f3_f2_fog09", bias=1.3, pp=PP, uds={"Fog": 0.9, "All Fog Colors Multiplier": [10.0, 2.6, 1.2]}, mat=MAT, lamps=LAMPS))
L.append(shot("f3e", cam="CAM_Establishing", bias=1.3, pp=PP, mat=MAT, lamps=LAMPS))
open("shots_f.txt", "w").write(json.dumps(L, indent=0))
