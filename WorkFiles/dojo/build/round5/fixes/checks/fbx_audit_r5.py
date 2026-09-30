"""ROUND 5 fixes track: audit the EXACT exported FBX bytes in a fresh Blender process, old (start_backup/exports) vs
new (Exports/DojoKit/...), per FBX: every UCX_* hull (names and world vertex sets, 0.1 mm), the LOD0 render mesh (tris,
material slots, bounds), the LOD count; plus sidecar presence. Collision must be identical except where this round
changed a piece's size on purpose (listed in EXPECTED).
Run: blender -b --factory-startup --python WorkFiles/dojo/build/round5/fixes/checks/fbx_audit_r5.py
Out: WorkFiles/dojo/build/round5/fixes/checks/json/fbx_audit_r5.json
"""
import json
from pathlib import Path

import bpy

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
FIX = ROOT / "WorkFiles" / "dojo" / "build" / "round5" / "fixes"
OLD = FIX / "start_backup" / "exports"
NEW = ROOT / "Exports" / "DojoKit"
KITS = {"Shed": "Shed", "Kit1": "Kit1", "Hall": "Hall", "training": "Props/training"}
EXPECTED = {"UCX_SM_DKS_Rack_00": "rack widened 3.7 -> 4.2 m (the fix)",
            "UCX_SM_DKS_Rack_LOD0_00": "rack widened 3.7 -> 4.2 m (the fix)"}


def load(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    hulls, meshes = {}, {}
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        M = o.matrix_world
        pts = [M @ v.co for v in o.data.vertices]
        if o.name.startswith("UCX_"):
            hulls[o.name] = sorted(tuple(round(c, 4) for c in p) for p in pts)
        else:
            meshes[o.name] = {"tris": sum(len(p.vertices) - 2 for p in o.data.polygons),
                              "slots": [m.name if m else None for m in o.data.materials],
                              "bbox": [[round(min(p[i] for p in pts), 4) for i in range(3)],
                                       [round(max(p[i] for p in pts), 4) for i in range(3)]]}
    return hulls, meshes


def max_delta(a, b):
    if len(a) != len(b):
        return None
    return max((max(abs(x - y) for x, y in zip(p, q)) for p, q in zip(a, b)), default=0.0)


out, bad = {}, []
for kit, rel in KITS.items():
    for f in sorted((NEW / rel).glob("*.fbx")):
        o = OLD / kit / f.name
        if not o.exists():
            out[f.name] = {"new_file": True}
            continue
        ho, mo = load(o)
        hn, mn = load(f)
        hd = {}
        for k in sorted(set(ho) | set(hn)):
            d = max_delta(ho[k], hn[k]) if k in ho and k in hn else None
            hd[k] = d
            if (d is None or d > 1e-4) and k not in EXPECTED:
                bad.append(f"{f.name}:{k}")
        lod0 = {k: v for k, v in mn.items() if not k.endswith(("_LOD1", "_LOD2"))}
        lod0o = {k: v for k, v in mo.items() if not k.endswith(("_LOD1", "_LOD2"))}
        out[f.name] = {"ucx_count": [len(ho), len(hn)], "ucx_max_delta_m": hd, "lods": [len(mo), len(mn)],
                       "render": {k: {"old": lod0o.get(k), "new": v} for k, v in lod0.items()},
                       "changed_render": any(lod0o.get(k) != v for k, v in lod0.items()),
                       "sidecar": (f.with_suffix("").with_suffix(".sockets.json")).exists()
                       if False else (f.parent / (f.stem + ".sockets.json")).exists()}
res = {"files": len(out), "collision_unexpected_changes": bad, "passed": not bad,
       "expected_changes": EXPECTED, "audit": out}
(FIX / "checks" / "json").mkdir(parents=True, exist_ok=True)
(FIX / "checks" / "json" / "fbx_audit_r5.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print("FBXAUDIT files", len(out), "unexpected collision changes", bad, "changed render",
      sorted(k for k, v in out.items() if v.get("changed_render")))
