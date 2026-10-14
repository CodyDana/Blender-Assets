"""SR01 debug aid (W1 follow-up UD1): build the named parts (no save) and print where the Unreal-drop / micro
triangles sit, clustered to 1 mm, with the pre-repair counts. Usage: blender -b --factory-startup --python
sr_ud_probe.py -- --only chassis,bolt_handle,magazine"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import numpy as np  # noqa: E402
from gunlib import bl, ud  # noqa: E402
from gunlib.ud import _tri_metrics  # noqa: E402
import sniper_parts as SP  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
only = argv[argv.index("--only") + 1].split(",")
out = {}
coll = bl.collection(SP.PARTS_COLL)
for n in only:
    p = SP.PARTS[n]()
    if "--weld" in argv:
        p.weld_mm = float(argv[argv.index("--weld") + 1])
    ob, rep = p.build(coll)
    V, T = bl.tris_np(ob)
    area, L, height, drop, corner = _tri_metrics(V, T)
    bad = np.nonzero(drop | (area < ud.MIN_AREA_MM2) | (height < ud.MIN_HEIGHT_MM))[0]
    c = np.round(V[T[bad]].mean(1), 0)
    keys, cnt = np.unique(c, axis=0, return_counts=True)
    order = np.argsort(-cnt)[:25]
    out[n] = {"mfe": rep.get("multi_face_edges"), "be": rep.get("boundary_edges"), "ud": rep.get("ud"), "pre": rep.get("ud_pre_repair"), "tris": rep.get("triangles"),
              "clusters": [[keys[i].tolist(), int(cnt[i])] for i in order]}
    if "--tris" in argv:
        out[n]["bad"] = [[np.round(V[T[i]] - np.array(SP.GRIP), 2).tolist(), round(float(area[i]), 5)] for i in np.nonzero(drop)[0][:40]]
    print("UDPROBE", n, json.dumps(out[n]))
Path(HERE.parents[2] / "WorkFiles/guns/sniper/scratch/w1/ud_probe.json").write_text(json.dumps(out, indent=1))
