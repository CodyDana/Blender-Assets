import json
from mk import shot
PP = {"film_grain_intensity": 0.1, "film_toe": 0.66, "local_exposure_shadow_contrast_scale": 1.0, "film_slope": 0.84}
BASE = {"Sun Source Angle Scale": 3.0, "Sky Light Intensity": 2.8, "Sun Light Intensity": 4.0,
        "Fog": 1.3, "Cloud Coverage": 3.2, "Cloud Light Color (Dawn/Dusk)": [1.0, 0.55, 0.3],
        "Volumetric Cloud Ambient Light (Dawn/Dusk)": [0.45, 0.42, 0.55],
        "Sun Light Color": [0.94, 0.94, 1.0], "Sky Light Color Multiplier (Dawn/Dusk)": [0.58, 1.3, 1.5],
        "Rayleigh Scattering Color (Dawn/Dusk)": [0.45, 0.47, 0.75], "Saturation": 1.0, "Contrast": 0.4,
        "All Fog Colors Multiplier": [9.0, 2.0, 1.0], "Lighting Brightness (Dawn/Dusk)": 2.8}
MAT = {"M_DJ_RoofTile": {"s": {"ValueMult": 2.0}, "v": {"Tint": [0.9, 1.2, 1.75], "MeanColour": [0.048, 0.058, 0.085]}},
       "M_DJ_ShojiPaper": {"s_mul": {"EmissiveIntensity": 0.82}, "v": {"EmissiveTint": [1.0, 0.55, 0.34]}},
       "M_DJ_ShojiPaper@SM_DKH_Bay_ClereFrieze": {"s_mul": {"EmissiveIntensity": 0.82 * 0.65}},
       "M_DJ_GlassAmber": {"s_mul": {"EmissiveIntensity": 1.4}, "v": {"EmissiveTint": [1.0, 0.4, 0.12]}},
       "M_DJ_PlasterCream": {"s": {"Saturation": 0.08, "ValueMult": 1.9}, "v": {"Tint": [1.0, 0.95, 1.08]}},
       "M_DKG_Gravel": {"s": {"Saturation": 0.35, "ValueMult": 1.4}, "v": {"Tint": [0.97, 0.94, 0.98]}},
       "M_DKG_GravelCoarse": {"s": {"Saturation": 0.35, "ValueMult": 1.55}, "v": {"Tint": [0.97, 0.94, 0.98]}},
       "M_DKG_SandRaked": {"v": {"Tint": [1.0, 0.9, 0.88]}}, "M_DKG_SandEdge": {"v": {"Tint": [1.0, 0.9, 0.88]}},
       "M_DJ_TimberDark": {"s": {"Saturation": 0.4}}, "M_DJ_TimberDarkEnd": {"s": {"Saturation": 0.4}},
       "M_DJ_TimberAged": {"s": {"Saturation": 0.4}}, "M_DJ_TimberAgedEnd": {"s": {"Saturation": 0.4}}}
LAMPS = {"Light_DKP_Stone_LanternTall": {"mult": 2.0, "radius_cm": 1200.0}, "Light_DKP_Modern_WallLamp": {"mult": 2.0, "radius_cm": 1000.0}}
L = []
L.append(shot("g1", bias=1.05, pp=PP, uds=BASE, mat=MAT, lamps=LAMPS))
BASE.update({"Contrast": 0.6, "Cloud Coverage": 3.6, "High Frequency Noise Amount": 0.5, "Base Height Fog Falloff": 0.2,
             "Fog": 1.6, "All Fog Colors Multiplier": [12.0, 2.6, 1.1], "Rayleigh Scattering Color (Dawn/Dusk)": [0.4, 0.45, 0.9],
             "Lighting Brightness (Dawn/Dusk)": 2.4, "Volumetric Cloud Ambient Light (Dawn/Dusk)": [0.5, 0.5, 0.75],
             "Cloud Dark Color (Dawn/Dusk)": [0.08, 0.08, 0.14], "Sky Light Color Multiplier (Dawn/Dusk)": [0.62, 1.25, 1.4]})
L = []
L.append(shot("i1", bias=1.27, pp=PP, uds=BASE, mat=MAT, lamps=LAMPS))
L.append(shot("i1e", cam="CAM_Establishing", bias=1.27, pp=PP, mat=MAT, lamps=LAMPS))
L.append(shot("i2_fog20_mult14", bias=1.27, pp=PP, uds={"Fog": 2.0, "All Fog Colors Multiplier": [14.0, 2.8, 1.1]}, mat=MAT, lamps=LAMPS))
L.append(shot("i2e", cam="CAM_Establishing", bias=1.27, pp=PP, mat=MAT, lamps=LAMPS))
L.append(shot("i3_i2_fall012", bias=1.27, pp=PP, uds={"Base Height Fog Falloff": 0.12}, mat=MAT, lamps=LAMPS))
L.append(shot("i3p", cam="CAM_PlayerEyeSand", bias=1.27, pp=PP, mat=MAT, lamps=LAMPS))
open("shots_i.txt", "w").write(json.dumps(L, indent=0))
