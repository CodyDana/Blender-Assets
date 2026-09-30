import json, sys
from mk import shot
OUT = sys.argv[1]
exec(open("gen_d.py").read().split("L = [")[0].split("OUT = sys.argv[1]")[1])   # SKY, PP, TIMB, SAND, R1, R2, SH, EMIS, LAMPS
SKY = dict(SKY, **{"Lighting Brightness (Dawn/Dusk)": 1.2, "All Fog Colors Multiplier": [24.0, 4.5, 1.0],
                   "Sky Light Color Multiplier (Dawn/Dusk)": [0.72, 1.18, 1.22]})
def full(roof=R1, bias=1.6, sand=None, **kw):
    return dict(bias=bias, pp=PP, mat={**roof, **SH, **TIMB, **(sand or SAND)}, emis=EMIS, lamps=LAMPS, **kw)
SAND2 = {"M_DKG_SandRaked": dict(SAND["M_DKG_SandRaked"], s=dict(SAND["M_DKG_SandRaked"]["s"], NormalFadeStart=2500.0,
                                                                   NormalFadeEnd=6000.0, NormalFarStrength=0.85)),
         "M_DKG_SandEdge": SAND["M_DKG_SandEdge"]}
L = [shot("f1_b160", uds=SKY, **full()), shot("f2_b175", **full(bias=1.75)),
     shot("f3_fog26", uds=dict(SKY, Fog=2.6), **full()), shot("f4_sandfar", uds=SKY, **full(sand=SAND2)),
     shot("f5_east", cam="CAM_EastYard", **full()), shot("f6_ver", cam="CAM_HallVeranda", **full()),
     shot("f7_roof", cam="CU_HallUpperRoof", **full()), shot("f8_drum", cam="CAM_Drum", **full()),
     shot("f9_eye", cam="CAM_PlayerEyeSand", **full()), shot("f10_estab", cam="CAM_Establishing", **full())]
cfg = {"out_dir": OUT, "report": OUT + "/game_capture.json", "warm_s": 40, "warm_per_cam_s": 4, "settle_s": 14,
       "shot_timeout_s": 90, "hide_pawn": True, "warm_pass": False,
       "cvars": ["scalability 3", "r.ScreenPercentage 100", "r.HighResScreenshotDelay 8", "t.MaxFPS 60"], "shots": L}
json.dump(cfg, open(OUT + "/cfg.json", "w"), indent=1)
print(len(L), "shots")
