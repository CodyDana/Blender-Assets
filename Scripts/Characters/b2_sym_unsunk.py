"""b2_sym_unsunk.py - PRIVATE / DO NOT SHIP. Recover the skin's "garment sink" displacement of the verified rig.

  blender -b WorkFiles/Characters/2B_private/rig_work/c1_stage3a_heat.blend -P Scripts/Characters/b2_sym_unsunk.py

b2_rig_apose.py pushed the skin 2-3 mm under the (then asymmetric) bandeau / underwear. Before the skin is
mirror-averaged that dent has to come out, or every place covered on one side only would keep a half-depth dent on
both sides. This script re-runs b2_rig_apose.py IN MEMORY (its source is read and exec'd with a few exact string
patches; the file itself is not edited) on the read-only stage-3a blend, with every write disabled:
  * no save_as_mainfile, no rig_work json writes (patched to no-ops)
  * the skin coordinates right before and right after the sink loop, and the final 168 cm scale, are captured
It writes only checks_sym/c1_sink_capture.npz: pre, post (metres, before the 168 cm scale), k (scale), and the final
coordinates the re-run produced, so the build can check they equal the verified rig's skin exactly.
"""
import os, sys, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from b2_sym_lib import CHECKS, log  # noqa

APOSE = os.path.join(HERE, "b2_rig_apose.py")
OUTF = CHECKS + "/c1_sink_capture.npz"
_CAP = {}

src = open(APOSE, encoding="utf-8").read()
PATCHES = [
    ('    sunk = 0\n    under_top_side = []\n',
     '    _CAP["pre"] = np.array([list(v.co) for v in me.vertices])\n    sunk = 0\n    under_top_side = []\n'),
    ('    report["skin_verts_sunk_under_garments"] = sunk\n',
     '    report["skin_verts_sunk_under_garments"] = sunk\n    _CAP["post"] = np.array([list(v.co) for v in me.vertices])\n'),
    ('    report["uniform_scale_to_168cm"] = {"height_before_m": round(top, 4), "scale": round(k, 5)}\n',
     '    report["uniform_scale_to_168cm"] = {"height_before_m": round(top, 4), "scale": round(k, 5)}\n    _CAP["k"] = k\n'),
    ('    save_json(WORK + "/c1_apose_report.json", report)\n', '    _CAP["report"] = report\n'),
    ('    save_json(WORK + "/c1_apose_skeleton.json", {n: list(hA[n]) for n in order})\n', ''),
    ('    bpy.ops.wm.save_as_mainfile(filepath=RIG_BLEND, compress=True)\n',
     '    _CAP["final"] = np.array([list(v.co) for v in me.vertices])\n'),
]
for old, new in PATCHES:
    assert src.count(old) == 1, ("patch anchor not found exactly once", old)
    src = src.replace(old, new)
assert "save_as_mainfile" not in src and "save_json(" not in src.replace("def save_json(", "")
g = {"__name__": "__main__", "__file__": APOSE, "_CAP": _CAP}
exec(compile(src, APOSE, "exec"), g)
os.makedirs(CHECKS, exist_ok=True)
np.savez_compressed(OUTF, pre=_CAP["pre"], post=_CAP["post"], k=np.array(_CAP["k"]), final=_CAP["final"])
sunk = np.linalg.norm(_CAP["post"] - _CAP["pre"], axis=1)
log("captured", OUTF, "sunk verts", int((sunk > 1e-7).sum()), "max mm", round(float(sunk.max()) * 1000, 3), "k", _CAP["k"])
