import sys, json, numpy as np
sys.path.insert(0, ".")
import wd_build as B
from props_lib import smokebomb_wind as W
rec = json.load(open(B.OUT + "/b0_design.json"))
passes = [W.PassSpec(name=p["name"], shows=tuple(p["shows"]), n=tuple(p["n"]), e1=tuple(p["e1"]), phi_a=p["phi_a"], phi_b=p["phi_b"],
                     beta=tuple(p["beta"]), width=tuple(p["width"]), gather=tuple(p["gather"]), role=p["role"]) for p in rec["passes"]]
wd = W.assemble(passes, [], tail_deg=70)
st = wd.edge_strain(); kg = wd.geodesic_curvature()
names = wd.names
for k in np.argsort(-st)[:1]:
    pass
# per pass: max strain on arc and on connector
for i, nm in enumerate(names):
    m = wd.pass_idx == i
    a = m & ~np.isnan(wd.phi); c = m & np.isnan(wd.phi)
    ia = np.argmax(np.where(a, st, -1)); ic = np.argmax(np.where(c, st, -1))
    print(f"{nm:7s} arc max {100*st[ia]:7.1f}% at phi {wd.phi[ia]:7.1f} (z {wd.c[ia,2]:+.2f})   conn max {100*st[ic]:7.1f}% at tail {wd.tail[ic]:6.1f} (z {wd.c[ic,2]:+.2f})  conn p90 {100*np.percentile(st[c],90) if c.any() else 0:5.1f}%")
