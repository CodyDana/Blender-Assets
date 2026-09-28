import json
d = json.load(open(r"C:/Users/Cody/Desktop/Blender_Projects/Exports/Garments/BlackCloak_MH_v2/Textures/T_BlackCloakV2_maps.json"))
x = d["detail16"]
print("D16", {k: x[k] for k in ("Colour_linear", "Bias", "Scale", "DetailMean", "DetailHighlightRatio", "H_default", "G_H1_pass", "contract_pass")}, x["contract_model_vs_BC_levels"])
print("STRESS", {k: v["pass"] for k, v in x["recolour_stress_subsample7"].items()})
print("NS", d["normal_sign_test"])
print("SEAM", d["tiling_seam"])
print("FRAY", d["fray"]["alpha_coverage_by_mip"], d["fray"]["fringe_threads"])
print("FILES", {k: (v["sha256"][:12], v["bytes"]) for k, v in d["files"].items()})
