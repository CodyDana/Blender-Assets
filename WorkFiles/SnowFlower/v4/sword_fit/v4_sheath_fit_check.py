"""Static lateral fit of the FINAL v4 blade (analytic outline, equals the shipped LOD0 to <0.2 mm) in a
straight sheath of the reference outline (References/SnowFlower/SnowFlower_sheath_reference.png, widths from
sheath_spec.json section 2/5), for the sheath builder. Pure numpy."""
import json, sys
import numpy as np
sys.path.insert(0, r'C:/Users/Cody/Desktop/Blender_Projects/Scripts/SnowFlower/v4')
import sfv4_spec as S

def sheath_w_px(row):
    if row < 169: return THROAT_PX     # throat fitting (rows 31-167): its interior is designed (spec row 9)
    if row <= 322: return 97.0 if row < 287 else 96.0
    if row <= 1250: return 96 + (72 - 96) * (row - 322) / (1250 - 322)
    if row <= 1292: return 72.0
    if row <= 1387: return 72 + (84 - 72) * min(1, (row - 1292) / 40)
    u = (row - 1387) / (1496 - 1387); return 84 * np.sqrt(max(0, 1 - u * u))

THROAT_PX = float(sys.argv[1]) if len(sys.argv) > 1 else 97.0
z = np.linspace(S.Z_PENDANT_TIP, S.Z_TIP, 1200)
sp, ed = S.spine_x(z), S.edge_x(z)
out = {}
for k in (0.687, 0.70, 0.72):
    for wall, clr in ((2.5, 1.0), (2.0, 0.75)):
        rows = 31 + (z - S.Z_PENDANT_TIP) / k + 1.0 / k
        hw = np.array([sheath_w_px(r) * k / 2 for r in rows]) - wall - clr
        best = (-1e9, 0)
        for c in np.linspace(-20, 20, 801):
            m = np.min(hw - np.maximum(np.abs(sp - c), np.abs(ed - c)))
            if m > best[0]: best = (m, c)
        m, c = best
        marg = hw - np.maximum(np.abs(sp - c), np.abs(ed - c)); i = int(np.argmin(marg))
        out[f"k{k}_wall{wall}_clr{clr}"] = {"best_margin_mm": round(float(m), 2), "cavity_axis_x_mm": round(float(c), 2),
            "limit_at_z_mm": round(float(z[i]), 1), "sheath_length_mm": round(1466 * k, 1),
            "tip_rests_ref_row": round(float(rows[-1]), 0)}
json.dump(out, open(r'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/sword_fit/v4_sheath_fit_check_throat%d.json' % int(THROAT_PX), 'w'), indent=1)
for k, v in out.items(): print(k, v)
