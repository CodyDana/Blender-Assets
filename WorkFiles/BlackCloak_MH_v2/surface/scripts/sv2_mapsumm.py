import json, sys
for d_ in sys.argv[sys.argv.index("--") + 1:]:
    d = json.load(open(d_ + "/T_BlackCloakV2_maps.json"))
    print("MAPS", d_[-7:], "PB", d["albedo_bands_at_photo_scale_2p64mm"], "MIP", [(m["mip"], m["bc_lum_std_over_mean"], m["n_mean_tilt_deg"]) for m in d["mips"]],
          "contract", d["detail16"]["contract_pass"], d["detail16"]["contract_model_vs_BC_levels"]["max"], "GH1", d["detail16"]["G_H1_pass"], "N", d["normal_sign_test"]["pass"],
          "stats", {k: d["stats"][k] for k in ("bc_median_lum_srgb8", "bc_median_rgb_srgb8", "bc_p1_p99_lum_srgb8", "n_std", "rough_mean", "rough_p1_p99", "normal_tilt_mean_deg")})
