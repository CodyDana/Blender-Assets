"""Scratch: one-line-per-region summary of measure_r5 outputs across probe variant folders."""
import json, glob, sys, os
ROWS=[("CU_R5_AlleyFence","fence_boards"),("CAM_Drum","pavilion_ceiling"),("CAM_Drum","drum_top"),("CU_R4_CorridorOpen","lattice_rail"),("CU_GateFront","gate_ceiling"),("CAM_HallVeranda","veranda_soffit"),("CAM_EstablishingRef2","veranda_band"),
 ("CAM_Drum","post_sunlit"),("CU_R4_PavilionTaiko","post_sunlit"),("CU_R4_PavilionTaiko","tiles_sunlit"),("CU_R4_RidgeGate","noshi"),("CU_R4_RidgeGate","tiles"),("CAM_EstablishingRef2","hall_upper_roof"),("CU_R4_PavilionTaiko","wall_plaster_sun"),("CU_R4_ResidenceFront","plaster"),("CU_R4_StorehouseFront","gable_plaster"),("CAM_EstablishingRef2","sand_lit"),("CAM_HallVeranda","shoji_glow")]
for f in sorted(glob.glob(sys.argv[1]+"/*/regions_r5_x.json")):
    d=json.load(open(f)); print("==",os.path.basename(os.path.dirname(f)), {c[:14]:d["cams"][c]["image"]["near_black_frac"] for c in ("CU_R5_AlleyFence","CAM_Drum","CU_R4_CorridorOpen") if c in d["cams"]})
    for c,k in ROWS:
        r=d["cams"].get(c,{}).get(k)
        if r: print(f"   {c[:16]:16s} {k:17s} {str(r['median_srgb']):16s} h{r['hue_deg']:5.1f} s{r['sat']:.2f} R/B{r['r_over_b']:.2f} nb{r['near_black_frac']:.2f}")
