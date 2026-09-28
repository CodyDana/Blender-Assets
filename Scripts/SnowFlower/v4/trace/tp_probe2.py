import json, numpy as np
T = json.load(open(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot/work/trace.json"))
for e in T["elements"]:
    if e["name"] in ("lat_L", "lat_R", "t1_L", "t1_R"):
        for k in ("region", "silver", "dark"):
            print(e["name"], k, [(round(l["area"], 1), len(l["pts"]), np.round(np.array(l["pts"]).min(0), 1).tolist(), np.round(np.array(l["pts"]).max(0), 1).tolist()) for l in e[k]])
