import json, sys
from cand import CFG
OUT = sys.argv[1]
cams = [("CAM_Ref2Match", 1440), ("CAM_Establishing", 1440), ("CAM_PlayerEyeSand", 1080), ("CAM_Overview", 1080),
        ("CAM_GateFromStreet", 1080), ("CAM_HallVeranda", 1080), ("CU_HallUpperRoof", 1080), ("CU_R5_Skyline", 1080),
        ("CAM_EastYard", 1080), ("CAM_Drum", 1080), ("CU_R4_StorehouseFront", 1080), ("CAM_EstablishingRef2", 1440)]
L = [{"name": c, "w": 1920, "h": h} for c, h in cams]
json.dump(dict(CFG, out_dir=OUT, report=OUT + "/json/game_capture.json", shots=L), open(sys.argv[2], "w"), indent=1)
