import json
from mk import shot
PP = {"film_grain_intensity": 0.1, "film_toe": 0.62, "local_exposure_shadow_contrast_scale": 1.0}
L1 = {"Sun Source Angle Scale": 3.0, "Sky Light Intensity": 2.2, "Sun Light Intensity": 4.0,
      "All Fog Colors Multiplier": [6.5, 1.7, 0.6]}
S1 = {"Fog": 1.8, "All Fog Colors Multiplier": [7.0, 1.6, 0.8], "Rayleigh Scattering Color (Dawn/Dusk)": [0.5, 0.36, 0.6],
      "Saturation": 1.2, "Contrast": 0.25, "Cloud Coverage": 3.2, "Cloud Light Color (Dawn/Dusk)": [1.0, 0.55, 0.3]}
MAT = {"M_DJ_RoofTile": {"s": {"ValueMult": 2.0}, "v": {"Tint": [0.66, 0.86, 1.4], "MeanColour": [0.034, 0.04, 0.07]}},
       "M_DJ_ShojiPaper": {"s_mul": {"EmissiveIntensity": 0.82}, "v": {"EmissiveTint": [1.0, 0.56, 0.22]}},
       "M_DJ_ShojiPaper@SM_DKH_Bay_ClereFrieze": {"s_mul": {"EmissiveIntensity": 0.82 * 0.65}},
       "M_DJ_GlassAmber": {"s_mul": {"EmissiveIntensity": 1.4}, "v": {"EmissiveTint": [1.0, 0.55, 0.14]}}}
LAMPS = {"Light_DKP_Stone_LanternTall": {"mult": 2.0, "radius_cm": 1200.0}, "Light_DKP_Modern_WallLamp": {"mult": 2.0, "radius_cm": 1000.0}}
L = []
L.append(shot("c1_L1", bias=1.1, pp=PP, uds=L1))
L.append(shot("c2_L1_fogstart", bias=1.1, pp=PP, uds={"Min Fog Start Distance": 6000.0}))
L.append(shot("c3_c2_S1", bias=1.1, pp=PP, uds=S1))
L.append(shot("c3e_c2_S1", cam="CAM_Establishing", bias=1.1, pp=PP))
L.append(shot("c4_c3_mat", bias=1.1, pp=PP, mat=MAT))
L.append(shot("c5_c4_lamps", bias=1.1, pp=PP, mat=MAT, lamps=LAMPS))
L.append(shot("c5v_c4_lamps", cam="CAM_HallVeranda", bias=1.1, pp=PP, mat=MAT, lamps=LAMPS))
L.append(shot("c5p_c4_lamps", cam="CAM_PlayerEyeSand", bias=1.1, pp=PP, mat=MAT, lamps=LAMPS))
L.append(shot("c6_c5_sky26", bias=1.0, pp=PP, mat=MAT, lamps=LAMPS, uds={"Sky Light Intensity": 2.6}))
open("shots_c.txt", "w").write(json.dumps(L, indent=0))
