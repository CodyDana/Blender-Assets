import sys, time, numpy as np
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
from props_lib import smokebomb_wind as W
dummy = W.PassSpec("P", ("x",), (0.3, -0.9, 0.2), (0, 0, 1), -97, 97, (0,) * 4, (0.1,) * 4)
for n, w in [(20, 0.18), (24, 0.18), (28, 0.18), (24, 0.2)]:
    t0 = time.time()
    ax = W.core_axes(n, [0.2, 0.9, 0.3], dummy.n)
    CP, CW = W.core_path(ax, w)
    wd = W.assemble([dummy], [], tail_deg=10, core=(CP, CW))
    cv = W.coverage(wd, 128)
    st = wd.edge_strain(); core = wd.pass_idx == 0
    steps = np.degrees(np.arccos(np.clip(np.einsum("ij,ij->i", ax[1:], ax[:-1]), -1, 1)))
    print(n, w, "cover min", cv["min"], "mean %.2f p05 %.1f" % (cv["mean"], cv["p05"]), "voids", cv["void_cells"],
          "core strain max %.1f%% p90 %.1f%%" % (100 * st[core].max(), 100 * np.percentile(st[core], 90)),
          "axis steps %.0f..%.0f" % (steps.min(), steps.max()), "len", round(float(wd.s[-1]), 1), "%.1fs" % (time.time() - t0))
