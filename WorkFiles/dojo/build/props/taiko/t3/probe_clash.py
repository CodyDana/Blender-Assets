"""t3: probe the drum (at DRUM_Z) against the stand in Taiko.blend: drum vertices inside stand wood, per part."""
import bpy, math
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
DRUM_Z = 1.25
d = bpy.data.objects["SM_DKP_Taiko_Drum"]; s = bpy.data.objects["SM_DKP_Taiko_Stand"]
dm, sm = d.data, s.data
DP = [Vector((v.co.x, v.co.y, v.co.z + DRUM_Z)) for v in dm.vertices]
wood = [list(p.vertices) for p in sm.polygons if not sm.materials[p.material_index].name.startswith("M_DKP_Taiko_Hide")]
SP = [v.co.copy() for v in sm.vertices]
wb = BVHTree.FromPolygons(SP, wood)
db = BVHTree.FromPolygons(DP, [list(p.vertices) for p in dm.polygons])
print("overlap pairs drum-wood", len(db.overlap(wb)))
vm = {}
for p in dm.polygons:
    for v in p.vertices: vm[v] = dm.materials[p.material_index].name
inside = {}
for i, p in enumerate(DP):
    # ray parity along +Z
    n = 0; o = p.copy()
    for _ in range(50):
        hit = wb.ray_cast(o, Vector((0, 0, 1)), 5.0)
        if hit[0] is None: break
        n += 1; o = hit[0] + Vector((0, 0, 1e-5))
    if n % 2:
        inside.setdefault(vm.get(i), []).append(p)
for k, v in inside.items():
    print("INSIDE", k, len(v), "x", round(min(abs(q.x) for q in v), 3), round(max(abs(q.x) for q in v), 3),
          "y", round(min(abs(q.y) for q in v), 3), round(max(abs(q.y) for q in v), 3), "z", round(min(q.z for q in v), 3), round(max(q.z for q in v), 3))
print("post-region drum min z for |x|>0.47,|y|>0.39:", min((q.z for q in DP if abs(q.x) > 0.47 and 0.39 < abs(q.y) < 0.57 and abs(q.x) < 0.65), default=None))
col = [i for i, m in vm.items() if m == "M_DKP_Taiko_HideCollar"]
lo = sorted(col, key=lambda i: DP[i].z)[:5]
for i in lo:
    q = DP[i]; print("lowest collar", tuple(round(c, 4) for c in q), "r", round(math.hypot(q.y, q.z - DRUM_Z), 4))
pp = [q for q in (DP[i] for i in col) if 0.39 < abs(q.y) < 0.57]
print("collar verts in post y band", len(pp), "min z", round(min(q.z for q in pp), 4) if pp else None)
print("stand bbox", [round(min(v[i] for v in SP), 3) for i in range(3)], [round(max(v[i] for v in SP), 3) for i in range(3)])
posts = [v for v in SP if v.z > 0.7 and abs(v.y) > 0.38]
print("stand verts z>0.7 |y|>0.38: x", round(min(abs(v.x) for v in posts),3), round(max(abs(v.x) for v in posts),3), "zmax", round(max(v.z for v in posts),4))
