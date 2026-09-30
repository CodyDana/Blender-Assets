import json, glob, sys
for v in sorted(glob.glob(sys.argv[1] + "/*/m.json")):
    m = json.load(open(v))
    c = {k: (x["frame_nb"], x["max_cell_nb"]) for k, x in m["cells"].items()}
    t = m["tiles"]
    def rb(k, w="lit30"): return t[k][w]["R/B"] if k in t else float("nan")
    print(v.split("\\")[-2] if "\\" in v else v.split("/")[-2], " ".join(f"{k.split('_',1)[1][:10]}:{b:.2f}" for k, (a, b) in c.items()))
    g = m["gravel"]
    print("   tiles lit30: pav %.2f capE %.2f oni %.2f noshi %.2f cap %.2f | shade ref2Up %.2f ridgeLower %.2f estUp %.2f" % (
        rb("CU_R4_PavilionTaiko:pav_roof_E_face_sunlit"), rb("CU_R4_PavilionTaiko:wallcap_E_sunlit"),
        rb("CU_R4_RidgeGate:onigawara_lit_face"), rb("CU_R4_RidgeGate:noshi_stack"), rb("CU_R4_RidgeGate:cap_rolls"),
        rb("CAM_Ref2Match:hall_upper_roof", "all"), rb("CU_R4_RidgeHall:hall_roof_tiles_lower_right", "all"), rb("CAM_EstablishingRef2:hall_upper_roof", "all")),
        "noshi rgb", t.get("CU_R4_RidgeGate:noshi_stack", {}).get("lit30", {}).get("rgb"),
        "ceiling", m["timber"].get("CU_R4_PavilionTaiko:ceiling_under_roof", {}).get("all", {}).get("rgb"),
        "postE", m["timber"].get("CU_R4_PavilionTaiko:post_E_sunlit", {}).get("lit30"),
        "gravel", [x["all"]["rgb"] for x in g.values()], "hot", m["hotspot"])
