import sys, json, os
D = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/reference_metrology"
segs = json.load(open(os.path.join(D, "sb_s8_segments_V.json")))
json.dump({"edges": {s['id'][1:]: {"pts": s['pts']} for s in segs}}, open(os.path.join(D, "sb_autoV.json"), "w"))
print(len(segs))
