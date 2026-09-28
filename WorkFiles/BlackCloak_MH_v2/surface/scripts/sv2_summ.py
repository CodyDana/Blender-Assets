import json, sys
for t in sys.argv[sys.argv.index("--") + 1:]:
    tag, mode = t.split(":")
    d = json.load(open("C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_MH_v2/surface/logs/%s_%s.json" % (tag, mode)))
    x = d.get("swatch_1x") or d.get("drape_1x")
    a = x.get("patches_agg") or x.get("flat_patches_agg")
    keys = ('mean_mean', 'hp_rel_mean', 'lin_amp_5_10mm_mean', 'lin_amp_10_20mm_mean', 'lin_amp_20_45mm_mean', 'orient_v_over_h_mean',
            'orient_axes_over_diag_mean', 'struct_aniso_mean', 'spec_p2_3', 'spec_p3_5', 'spec_p5_10', 'spec_p10_16', 'spec_aniso_vfreq_over_hfreq')
    print("SUM", tag, mode, "median", round(x["median_lum_srgb"], 2), x.get("p10_p90_lum_srgb", ""), {k.replace('_mean', ''): round(a[k], 4) for k in keys if k in a})
