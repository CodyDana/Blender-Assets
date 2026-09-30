import json, sys
from mk import shot
OUT = sys.argv[1]
exec(open("gen_d.py").read().split("L = [")[0].split("OUT = sys.argv[1]")[1])   # SKY, PP, TIMB, SAND, R1, R2, SH, EMIS, LAMPS
SKY = dict(SKY, **{"Lighting Brightness (Dawn/Dusk)": 1.2, "All Fog Colors Multiplier": [16.0, 4.0, 1.2]})
B = 1.2 + 1.0   # log2(2.4 / 1.2)
R0 = {"M_DJ_RoofTile": {"s": {"ValueMult": 1.7}, "v": {"Tint": [0.9, 0.97, 1.12], "MeanColour": [0.046, 0.05, 0.062]}}}
def full(roof, **kw):
    return dict(bias=B, pp=PP, mat={**roof, **SH, **TIMB, **SAND}, emis=EMIS, lamps=LAMPS, **kw)
s1 = dict(SKY, **{"Sky Light Color Multiplier (Dawn/Dusk)": [0.7, 1.3, 1.25]})
s2 = dict(SKY, **{"Sky Light Color Multiplier (Dawn/Dusk)": [0.66, 1.4, 1.3]})
s3 = dict(s1, **{"Sun Light Color": [0.9, 1.0, 1.05]})
L = [shot("e1_skl1_r1", uds=s1, **full(R1)), shot("e1b_skl1_r0", **full(R0)), shot("e2_skl2_r0", uds=s2, **full(R0)),
     shot("e3_sun_r0", uds=s3, **full(R0)),
     shot("e4_roof_s3r0", cam="CU_HallUpperRoof", **full(R0)), shot("e5_roof_s3r1", cam="CU_HallUpperRoof", **full(R1)),
     shot("e6_roof_s1r0", cam="CU_HallUpperRoof", uds=s1, **full(R0)),
     shot("e7_skyl_s1r0", cam="CU_R5_Skyline", **full(R0)), shot("e8_east_s1r0", cam="CAM_EastYard", **full(R0))]
cfg = {"out_dir": OUT, "report": OUT + "/game_capture.json", "warm_s": 40, "warm_per_cam_s": 4, "settle_s": 14,
       "shot_timeout_s": 90, "hide_pawn": True, "warm_pass": False,
       "cvars": ["scalability 3", "r.ScreenPercentage 100", "r.HighResScreenshotDelay 8", "t.MaxFPS 60"], "shots": L}
json.dump(cfg, open(OUT + "/cfg.json", "w"), indent=1)
print(len(L), "shots")
