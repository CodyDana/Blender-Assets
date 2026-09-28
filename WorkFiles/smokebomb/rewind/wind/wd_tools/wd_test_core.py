import sys, time, numpy as np
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
from props_lib import smokebomb_wind as W
for n, w in [(12, 0.16), (16, 0.16), (20, 0.16), (16, 0.2)]:
    t0 = time.time()
    core = W.core_passes(n, [0.2, 0.9, 0.3], [0.3, -0.9, 0.2], width_frac_d=w)
    wd = W.assemble(core, [], tail_deg=10)
    cv = W.coverage(wd, 128)
    st = wd.edge_strain(); conn = np.isnan(wd.phi)
    print(n, w, "cover min", cv["min"], "mean %.2f p05 %.1f" % (cv["mean"], cv["p05"]), "voids", cv["void_cells"], "conn strain max %.1f%% p90 %.1f%%" % (100*st[conn].max(), 100*np.percentile(st[conn], 90)), "len", round(float(wd.s[-1]),1), "%.1fs" % (time.time()-t0))
