import json
from mk import shot
G = {"film_grain_intensity": 0.06}
L = []
L.append(shot("b0_base"))
L.append(shot("b1_a3_s20_sun5_b10", bias=1.0, pp=G, uds={"Sun Source Angle Scale": 3.0, "Sky Light Intensity": 2.0, "Sun Light Intensity": 5.0}))
L.append(shot("b2_a3_s20_sun4_b11", bias=1.1, pp=G, uds={"Sun Source Angle Scale": 3.0, "Sky Light Intensity": 2.0, "Sun Light Intensity": 4.0}))
L.append(shot("b3_a3_s24_sun5_b08", bias=0.8, pp=G, uds={"Sun Source Angle Scale": 3.0, "Sky Light Intensity": 2.4, "Sun Light Intensity": 5.0}))
L.append(shot("b4_a3_s17_sun4_b12", bias=1.2, pp=G, uds={"Sun Source Angle Scale": 3.0, "Sky Light Intensity": 1.7, "Sun Light Intensity": 4.0}))
L.append(shot("b5_b2_fogR", bias=1.1, pp=G, uds={"Sun Source Angle Scale": 3.0, "Sky Light Intensity": 2.0, "Sun Light Intensity": 4.0,
                                               "All Fog Colors Multiplier": [6.5, 1.7, 0.6]}))
L.append(shot("b6_b5_cloudwarm", bias=1.1, pp=G, uds={"Cloud Light Color (Dawn/Dusk)": [1.0, 0.55, 0.3],
              "Rayleigh Scattering Color (Dawn/Dusk)": [0.5, 0.36, 0.58], "Cloud Wisps Tint (Dawn/Dusk)": [1.0, 0.5, 0.35]}))
L.append(shot("b6e_b5_cloudwarm", cam="CAM_Establishing", bias=1.1, pp=G))
L.append(shot("b7_b6_grain12", bias=1.1, pp={"film_grain_intensity": 0.12}))
L.append(shot("b7e_b6_grain12", cam="CAM_Establishing", bias=1.1, pp={"film_grain_intensity": 0.12}))
open("shots_b.txt", "w").write(json.dumps(L, indent=0))
