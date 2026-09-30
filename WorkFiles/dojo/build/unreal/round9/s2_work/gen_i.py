import json, sys
from mk2 import shot
from cand import CFG
OUT = sys.argv[1]
L = [shot("i0_built"),
     shot("i1_hl10", pp={"local_exposure_highlight_contrast_scale": 1.0}),
     shot("i2_lb07", bias=1.75, pp={"local_exposure_highlight_contrast_scale": 0.7}, uds={"Lighting Brightness (Dawn/Dusk)": 0.7}),
     shot("i3_both", bias=1.75, pp={"local_exposure_highlight_contrast_scale": 1.0}),
     shot("i4_both_fog30", bias=1.75, pp={"local_exposure_highlight_contrast_scale": 1.0}, uds={"Fog": 3.0}),
     shot("i5_east", cam="CAM_EastYard", bias=1.75, pp={"local_exposure_highlight_contrast_scale": 1.0}),
     shot("i6_ver", cam="CAM_HallVeranda", bias=1.75, pp={"local_exposure_highlight_contrast_scale": 1.0}),
     shot("i7_skyl", cam="CU_R5_Skyline", bias=1.75, pp={"local_exposure_highlight_contrast_scale": 1.0})]
json.dump(dict(CFG, out_dir=OUT, report=OUT + "/game_capture.json", shots=L), open(OUT + "/cfg.json", "w"), indent=1)
print(len(L), "shots")
