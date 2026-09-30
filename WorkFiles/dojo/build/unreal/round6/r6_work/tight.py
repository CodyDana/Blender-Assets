import json, glob, sys, os
for v in sys.argv[1:]:
    t = json.load(open(v))["tiles"]
    n = os.path.basename(os.path.dirname(v))[:18].ljust(18)
    print(n, "pavE", t["CU_R4_PavilionTaiko:pav_E_tight"]["lit30"], "capE", t["CU_R4_PavilionTaiko:wallcapE_tight"]["lit30"])
