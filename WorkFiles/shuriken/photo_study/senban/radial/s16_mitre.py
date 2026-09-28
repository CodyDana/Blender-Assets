"""Mitre test at the two top corners: the boundary between the dark top facet and the lighter side bevel
is a steel-steel line that must run into the true tip. Fit it and measure its distance from the
'inner' (primary) and 'outer' apex candidates."""
import sys, json, math
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/senban/radial")
import numpy as np
from common import *
R = json.load(open(OUT + "senban_final.json"))
rgb = load_rgb().astype(np.float64)
L = rgb.mean(-1)
Ls = L.copy()
# light 3x3 box smoothing
Ls = sum(np.roll(np.roll(L, dy, 0), dx, 1) for dy in (-1, 0, 1) for dx in (-1, 0, 1)) / 9
inner = R["per_side_primary_top_edge_inner"]["apex_corners_px"]
outer = R["per_side_alt_top_edge_outer"]["apex_corners_px"]
out = {}
for cname, side_dir in (("corner_2", +1), ("corner_3", -1)):     # TL: scan +x from left edge ; TR: scan -x
    ai = np.array(inner[cname]); ao = np.array(outer[cname])
    pts = []
    for y in range(int(ai[1]) + 4, int(ai[1]) + 30):
        x0 = int(ai[0]) - 6 if side_dir > 0 else int(ai[0]) + 6
        xs = np.arange(x0, x0 + side_dir * 60, side_dir)
        prof = Ls[y, xs]
        # first position (from the side edge inward) where L drops below 0.16 after having been > 0.3
        seen = np.nonzero(prof > 0.3)[0]
        if len(seen) == 0: continue
        k0 = seen[0]
        drop = np.nonzero(prof[k0:] < 0.16)[0]
        if len(drop) == 0: continue
        k = k0 + drop[0]
        # subpixel: linear interp at 0.16 crossing
        a, b = prof[k - 1], prof[k]
        f = (a - 0.16) / (a - b) if a != b else 0
        pts.append((xs[k - 1] + side_dir * f, y))
    pts = np.array(pts, float)
    (mx, my), (ux, uy), rms = fit_line(pts[:, 0], pts[:, 1])
    nrm = np.array([-uy, ux])
    di = abs((ai[0] - mx) * nrm[0] + (ai[1] - my) * nrm[1])
    do = abs((ao[0] - mx) * nrm[0] + (ao[1] - my) * nrm[1])
    ang = math.degrees(math.atan2(uy, ux))
    out[cname] = {"n_pts": len(pts), "mitre_line_rms_px": round(rms, 2), "mitre_heading_deg": round(ang, 2),
                  "dist_to_inner_apex_px": round(di, 2), "dist_to_outer_apex_px": round(do, 2),
                  "inner_apex": ai.tolist(), "outer_apex": ao.tolist(),
                  "pts_first_last": [pts[0].round(1).tolist(), pts[-1].round(1).tolist()]}
json.dump(out, open(OUT + "senban_mitre_test.json", "w"), indent=1)
print(json.dumps(out, indent=1))
