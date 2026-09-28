"""BlackCloak v2 clasp: a solid round lacquered BUTTON/disc (Jin_Cloak intent: a glossy dark disc on the right shoulder;
not a ring, no strap, no pin).  Slightly domed face, a thin bevelled rim with a shallow groove inside it, a flat back.

Lathe of one profile, 32 segments, <= 800 tris, closed manifold, outward normals, UVs (face / back / rim strip),
its own material M_BlackCloakV2_Clasp from material_params.json, object property garment_hard = True (never decimated,
moved rigidly by a refit).  Origin = back centre; local +Z = the outward face normal; rest at the world origin so
stage 2 can place/parent it on the shoulder.  Saves a standalone .blend to append from.

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python build_clasp.py -- \
        --out WorkFiles/BlackCloak_MH_v2/surface/BlackCloakV2_Clasp.blend [--diameter 0.056]
"""
import sys, os, math, json, argparse
import bpy, bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bcv2_material as BM  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_MH_v2/surface/BlackCloakV2_Clasp.blend")
ap.add_argument("--diameter", type=float, default=0.056)
ap.add_argument("--segments", type=int, default=32)
A = ap.parse_args(argv)

R = A.diameter / 2.0
k = R / 0.028                       # profile authored for a 56 mm button, scaled uniformly
PROFILE = [  # (r, z) metres at 56 mm, back centre -> face centre
    (0.0, 0.0), (0.0235, 0.0), (0.0262, 0.0008), (0.0280, 0.0030), (0.0280, 0.0058), (0.0270, 0.0074),
    (0.0250, 0.0080), (0.0232, 0.0076), (0.0222, 0.0073), (0.0190, 0.0088), (0.0130, 0.0106), (0.0065, 0.0116),
    (0.0, 0.0119)]
PROFILE = [(r * k, z * k) for r, z in PROFILE]
SHARP_RINGS = {1}                   # back edge: flat back vs bevel
S = A.segments

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
bm = bmesh.new()
rings = []
for i, (r, z) in enumerate(PROFILE):
    if r == 0.0:
        rings.append([bm.verts.new((0, 0, z))])
    else:
        rings.append([bm.verts.new((r * math.cos(2 * math.pi * j / S), r * math.sin(2 * math.pi * j / S), z))
                      for j in range(S)])
bm.verts.ensure_lookup_table()
faces_by_span = []
for i in range(len(rings) - 1):
    a, b = rings[i], rings[i + 1]
    fs = []
    for j in range(S):
        jn = (j + 1) % S
        if len(a) == 1:
            f = bm.faces.new((a[0], b[jn], b[j]))
        elif len(b) == 1:
            f = bm.faces.new((a[j], a[jn], b[0]))
        else:
            f = bm.faces.new((a[j], a[jn], b[jn], b[j]))
        fs.append(f)
    faces_by_span.append(fs)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
# outward check: every face normal against the profile's analytic outward normal (dz, -dr) at that face's angle
inward = 0
for si, fs in enumerate(faces_by_span):
    (r0, z0), (r1, z1) = PROFILE[si], PROFILE[si + 1]
    nr, nz = (z1 - z0), -(r1 - r0)
    for f in fs:
        c = f.calc_center_median()
        th = math.atan2(c.y, c.x)
        if f.normal.dot(Vector((nr * math.cos(th), nr * math.sin(th), nz))) <= 0:
            inward += 1
# sharp edges: the ring(s) in SHARP_RINGS
for e in bm.edges:
    zs = {round(v.co.z, 7) for v in e.verts}
    rs = {round(math.hypot(v.co.x, v.co.y), 7) for v in e.verts}
    for ri in SHARP_RINGS:
        if zs == {round(PROFILE[ri][1], 7)} and rs == {round(PROFILE[ri][0], 7)}:
            e.smooth = False
# UVs: face (spans from ring 5 inward) planar in the left half; back fan planar top-right; side band strip bottom-right
uv = bm.loops.layers.uv.new("UVMap")
arc = [0.0]
for i in range(1, 6):
    arc.append(arc[-1] + math.dist(PROFILE[i - 1], PROFILE[i]))
for si, fs in enumerate(faces_by_span):
    for f in fs:
        angs = [math.atan2(l.vert.co.y, l.vert.co.x) % (2 * math.pi) for l in f.loops]
        if max(angs) - min(angs) > math.pi:            # seam at angle 0: unwrap to the far side
            angs = [a_ + 2 * math.pi if a_ < math.pi else a_ for a_ in angs]
        for l, ang in zip(f.loops, angs):
            x, y, z = l.vert.co
            if si == 0:                                  # back
                l[uv].uv = (0.75 + 0.23 * x / R, 0.75 + 0.23 * y / R)
            elif si >= 5:                                # face / dome / rim top
                l[uv].uv = (0.25 + 0.24 * x / R, 0.5 + 0.48 * y / R)
            else:                                        # bevel + side band
                ri = min(range(6), key=lambda q: abs(math.hypot(x, y) - PROFILE[q][0]) + abs(z - PROFILE[q][1]))
                l[uv].uv = (0.52 + 0.46 * ang / (2 * math.pi), 0.04 + 0.42 * arc[ri] / arc[-1])
me = bpy.data.meshes.new("BlackCloakV2_Clasp")
bm.to_mesh(me)
bm.free()
for p in me.polygons:
    p.use_smooth = True
ob = bpy.data.objects.new("BlackCloakV2_Clasp", me)
col = bpy.data.collections.new("BCV2_Clasp")
bpy.context.scene.collection.children.link(col)
col.objects.link(ob)
mat = BM.clasp_material(BM.load_params())
me.materials.append(mat)
ob["garment_hard"] = True
ob["bcv2_diameter_m"] = A.diameter
ob["bcv2_height_m"] = PROFILE[-1][1]
ob["bcv2_note"] = "origin = back centre, local +Z = outward; place on the right shoulder (viewer-left) of the mantle"
# checks
bm2 = bmesh.new()
bm2.from_mesh(me)
tris = sum(len(p.vertices) - 2 for p in me.polygons)
nonman = sum(1 for e in bm2.edges if not e.is_manifold)
bound = sum(1 for e in bm2.edges if e.is_boundary)
bm2.free()
uv_ok = all(0.0 <= d.uv[0] <= 1.0 and 0.0 <= d.uv[1] <= 1.0 for d in me.uv_layers[0].data)
rep = {"object": ob.name, "tris": tris, "verts": len(me.vertices), "segments": S, "diameter_m": A.diameter,
       "height_m": PROFILE[-1][1], "rim_bevel_m": [PROFILE[5][0] - PROFILE[8][0], PROFILE[6][1] - PROFILE[4][1]],
       "dome_rise_above_groove_m": PROFILE[-1][1] - PROFILE[8][1],
       "faces_pointing_inward": inward, "non_manifold_edges": nonman, "boundary_edges": bound,
       "uvs_in_0_1": uv_ok, "sharp_edges": sum(1 for e in me.edges if not e.use_edge_sharp is False),
       "material": mat.name, "garment_hard": True, "budget_tris": 800, "pass": bool(tris <= 800 and inward == 0 and nonman == 0 and bound == 0 and uv_ok)}
ob["bcv2_checks"] = json.dumps(rep)
os.makedirs(os.path.dirname(A.out), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=A.out)
json.dump(rep, open(os.path.splitext(A.out)[0] + ".json", "w"), indent=1)
print("CLASP", json.dumps(rep))
