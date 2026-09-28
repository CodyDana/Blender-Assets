import sys, json, os
D = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/reference_metrology"
tr = json.load(open(os.path.join(D, "sb_autoV.json")))['edges']
ids = sys.argv[sys.argv.index('--') + 1:]
for i in ids:
    e = tr[i]['pts']
    print(i, " ".join(f"({p[0]:.0f},{p[1]:.0f})" for p in e))
