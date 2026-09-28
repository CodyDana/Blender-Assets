"""Build the hero_lantern_vase pieces (no render), print HERO_* stats and audit the FITTED spray parts for clipping:
blossom/bud vs blossom/bud (must be 0) and blossom/bud vs branch triangles away from the attachment.
blender -b --factory-startup --python stats.py"""
import os, sys
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
os.environ["ARMORY_HERO_ONLY"] = "hero_lantern_vase"
ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
sys.path.insert(0, str(ROOT / "Scripts" / "armory"))
bpy.ops.wm.read_factory_settings(use_empty=True)
import build_armory_kit as K
for n in K.MATERIALS:
    K.build_material(n)
M = next(m for m in K.HERO.MODULES if m.__name__ == "hero_lantern_vase")
CAP = []; PRE = []
_fit0 = M._fit
def _fit(parts, *a, **k):
    out = _fit0(parts, *a, **k)
    CAP.append(out[0]); PRE.append(parts)
    return out
M._fit = _fit
ps = [p for m in K.HERO.MODULES for p in m.pieces(K.HERO.G)]

def audit(parts, label):
    items = []
    for verts, faces, uvs, mats, sm in parts:
        vv = [Vector(v) for v in verts]
        kind = "flower" if isinstance(mats, list) else ("bud" if mats == M.BUD else "tube")
        lo = Vector([min(v[i] for v in vv) for i in range(3)]); hi = Vector([max(v[i] for v in vv) for i in range(3)])
        c = vv[0] if kind == "flower" else (vv[0] + vv[1]) / 2 if kind == "bud" else None
        R = max((v - c).length for v in vv) if c is not None else 0
        cents = [sum((vv[i] for i in f), Vector()) / len(f) for f in faces]
        items.append((kind, lo, hi, BVHTree.FromPolygons(vv, [tuple(f) for f in faces]), c, R, cents))
    ff = ft = 0
    worst = []
    for i, (k1, lo1, hi1, b1, c1, R1, _) in enumerate(items):
        if k1 == "tube":
            continue
        for j, (k2, lo2, hi2, b2, c2, R2, cents2) in enumerate(items):
            if j == i or any(lo1[a] > hi2[a] or hi1[a] < lo2[a] for a in range(3)):
                continue
            pairs = b1.overlap(b2)
            if not pairs:
                continue
            if k2 == "tube":
                d = min((cents2[q] - c1).length for _p, q in pairs)
                dmax = max((cents2[q] - c1).length for _p, q in pairs)
                lim = (0.75 * R1 + 0.03) if k1 == "flower" else (3.5 * R1 + 0.02)
                if dmax > lim:
                    ft += 1
                    worst.append((k1, round(R1, 4), round(dmax, 4), tuple(round(x, 3) for x in c1)))
            elif j > i:
                ff += 1
                worst.append((k1, k2, tuple(round(x, 3) for x in c1)))
    print("AUDIT", label, "bloom/bud-vs-bloom/bud", ff, "bloom/bud-vs-branch(away from attach)", ft, worst[:8])

exec(open(__file__.replace("clip_audit_stats.py", "clip_audit2.py")).read())
for parts, label in zip(PRE, ("S_prefit", "L_prefit")):
    audit_face(parts, label, 5 if label.startswith("S") else 4)
for parts, label in zip(CAP, ("S", "L")):
    audit_face(parts, label, 5 if label.startswith("S") else 4)
    audit(parts, label)
print("STATS_DONE")
