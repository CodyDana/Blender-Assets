"""Round 3: see-through samples around the leaf's inner edge, with and without the leaf-zone prongs, over openings.

    blender -b --factory-startup --python WorkFiles/fan/round3/seethrough_compare.py -- [--lods 0,1,2] [--out name.json]
Also runs the numpy fold proof (cracks + every intersection class) on the prong build at the same samples."""
import json, sys, time
from pathlib import Path
P = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(P / "Scripts")); sys.path.insert(0, str(P / "Scripts" / "props"))
import numpy as np
from props_lib import fan_fold as FF, fan_geom as G, fan_seethrough as ST
from props_lib.fan_spec import FAN as _FAN
import dataclasses

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FAN = dataclasses.replace(_FAN, prong_reach_mm=float(argv[argv.index("--reach") + 1]), leaf_in_L=float(argv[argv.index("--vis") + 1]) - float(argv[argv.index("--reach") + 1]) / 190.0) if "--reach" in argv else _FAN
lods = [int(x) for x in (argv[argv.index("--lods") + 1] if "--lods" in argv else "0").split(",")]
out_name = argv[argv.index("--out") + 1] if "--out" in argv else "seethrough_compare.json"
views = argv[argv.index("--views") + 1].split(",") if "--views" in argv else list(ST.VIEWS)
openings = [float(x) for x in (argv[argv.index("--openings") + 1] if "--openings" in argv else "163.2,122.8,82.4,36,15,5").split(",")]
c = json.loads((P / "WorkFiles/fan/fold_bind_cache.json").read_text())
pass
fs = FF.FoldSolver(FAN, np.array(c["offsets"]))
res = {"openings": openings, "lods": {}}
atl = None
t0 = time.time()
for lod in range(max(lods) + 1):
    mb, info, atl = G.build_lod(FAN, lod, fs.tpl, atl)
    if lod not in lods:
        continue
    P0, T, B = mb.arrays()
    prong = np.array([k.startswith("prong") for k in mb.TK])
    rows = {}
    for op in openings:
        s = FAN.s_for_opening(op)
        Ts = {f"stick_{i:02d}": M for i, M in enumerate(fs.sticks_T(s))}
        for j, M in enumerate(fs.face_T(s)):
            Ts[f"leaf_{j:02d}"] = M
        Ts["pivot"] = np.eye(4)
        Q = np.empty_like(P0)
        for bi, bn in enumerate(mb.bone_names):
            m = B == bi
            if m.any():
                Q[m] = FF.apply(Ts[bn], P0[m])
        with_p = ST.count(Q, T, FAN, s, views=views)
        without = ST.count(Q, T[~prong], FAN, s, views=views)
        rows[str(op)] = {"with_prongs": with_p, "without_prongs": without}
        print(f"LOD{lod} {op:6.1f} deg  with {with_p['total']:6d}  without {without['total']:6d}  "
              + " ".join(f"{v}:{with_p[v]}/{without[v]}" for v in views), flush=True)
    res["lods"][f"LOD{lod}"] = {"triangles": info["triangles"], "prong_triangles": int(prong.sum()), "rows": rows}
res["seconds"] = round(time.time() - t0, 1)
(P / "WorkFiles/fan/round3" / out_name).write_text(json.dumps(res, indent=1))
print("done", res["seconds"])
