import json, sys
from mk import shot
from cand import *
OUT = sys.argv[1]
R3 = {"M_DJ_RoofTile": {"s": {"ValueMult": 1.75}, "v": {"Tint": [0.87, 0.96, 1.2], "MeanColour": [0.046, 0.05, 0.066]}}}
def F(bias=1.5, roof=R3):
    return dict(bias=bias, pp=PP, mat={**roof, **SH, **TIMB, **SAND}, emis=EMIS, lamps=LAMPS)
h1 = dict(SKY, **{"Lighting Brightness (Dawn/Dusk)": 1.0, "Sky Light Intensity": 3.6})
L = [shot("h1_lb10_b150", uds=h1, **F()), shot("h2_b140", **F(1.4)), shot("h3_b160", **F(1.6)),
     shot("h4_roof", cam="CU_HallUpperRoof", **F()), shot("h5_east", cam="CAM_EastYard", **F()),
     shot("h6_ver", cam="CAM_HallVeranda", **F()), shot("h7_drum", cam="CAM_Drum", **F())]
json.dump(dict(CFG, out_dir=OUT, report=OUT + "/game_capture.json", shots=L), open(OUT + "/cfg.json", "w"), indent=1)
print(len(L), "shots")
