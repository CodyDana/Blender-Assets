# PRIVATE / DO NOT SHIP -- independent checker for 2B step A. Read-only on the .blend (never saves).
# Usage: blender -b 2B_private_base.blend -P b2_check_numbers.py -- <out_json>
import bpy, bmesh, sys, os, json, struct, hashlib, math
from mathutils import Vector

GLB = "C:/Users/Cody/Desktop/Blender_Projects/References/Characters/2B_kimono_private/source/28.glb"
EXPECT_SHA = "8d8143d12c8cf7f0d147fd29a3a5175b10f2b3ffd8fd850b3bde457207057135"
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/Characters/2B_private/checks/check_numbers.json"
R = {}

# ---- (5) source hash
h = hashlib.sha256()
with open(GLB, "rb") as f:
    for ch in iter(lambda: f.read(1 << 20), b""):
        h.update(ch)
R["sha256"] = h.hexdigest()
R["sha_ok"] = R["sha256"] == EXPECT_SHA

# ---- (3) GLB tris from accessors
with open(GLB, "rb") as f:
    data = f.read()
magic, ver, length = struct.unpack_from("<III", data, 0)
clen, ctype = struct.unpack_from("<II", data, 12)
gj = json.loads(data[20:20 + clen].decode("utf8"))
glb_mats = [m.get("name", "") for m in gj.get("materials", [])]
glb_tris = 0
glb_per_mat = {}
prim_modes = set()
for mesh in gj["meshes"]:
    for p in mesh["primitives"]:
        mode = p.get("mode", 4)
        prim_modes.add(mode)
        if "indices" in p:
            n = gj["accessors"][p["indices"]]["count"]
        else:
            n = gj["accessors"][p["attributes"]["POSITION"]]["count"]
        t = n // 3
        glb_tris += t
        mn = glb_mats[p["material"]] if "material" in p else None
        glb_per_mat[mn] = glb_per_mat.get(mn, 0) + t
R["glb"] = {"n_meshes": len(gj["meshes"]), "n_prims": sum(len(m["primitives"]) for m in gj["meshes"]),
            "n_materials": len(glb_mats), "modes": sorted(prim_modes), "tris": glb_tris,
            "dup_mat_names": sorted({m for m in glb_mats if glb_mats.count(m) > 1})}

# ---- scene inventory
def coll_of(o):
    return [c.name for c in o.users_collection]

test_names = set()
for c in bpy.data.collections:
    if "test" in c.name.lower():
        for o in c.all_objects:
            test_names.add(o.name)
objs = [o for o in bpy.data.objects if o.name not in test_names]
R["collections"] = {c.name: {"objs": len(c.all_objects), "hide_render": c.hide_render,
                             "children": [x.name for x in c.children]} for c in bpy.data.collections}
R["non_test_objects"] = {o.name: {"type": o.type, "colls": coll_of(o)} for o in objs}
R["test_objects_count"] = len(test_names)
R["scenes"] = [s.name for s in bpy.data.scenes]

meshes = {o.name: o for o in objs if o.type == "MESH"}
per = {}
tot_tris = 0
mat_users = {}
ident_bad = []
for n, o in sorted(meshes.items()):
    me = o.data
    me.calc_loop_triangles()
    t = len(me.loop_triangles)
    tot_tris += t
    mats = [s.material.name if s.material else None for s in o.material_slots]
    used_idx = sorted({p.material_index for p in me.polygons})
    used = [mats[i] if i < len(mats) else None for i in used_idx]
    for m in used:
        mat_users.setdefault(m, []).append(n)
    props = {k: (str(o[k]) if not isinstance(o[k], (int, float, str)) else o[k]) for k in o.keys()}
    mw = o.matrix_world
    ident = all(abs(mw[i][j] - (1.0 if i == j else 0.0)) < 1e-6 for i in range(4) for j in range(4))
    if not ident:
        ident_bad.append(n)
    ngon = sum(1 for p in me.polygons if len(p.vertices) != 3)
    per[n] = {"tris": t, "polys": len(me.polygons), "non_tri_polys": ngon, "verts": len(me.vertices),
              "mats_slots": mats, "mats_used": used, "props": props, "colls": coll_of(o),
              "modifiers": [m.type for m in o.modifiers], "hide_render": o.hide_render,
              "glb_tris_for_mat": sum(glb_per_mat.get(m, 0) for m in used)}
R["objects"] = per
R["total_tris_blend"] = tot_tris
R["tris_match"] = tot_tris == glb_tris
R["non_identity_transforms"] = ident_bad
R["per_obj_tri_mismatch"] = {n: (v["tris"], v["glb_tris_for_mat"]) for n, v in per.items() if v["tris"] != v["glb_tris_for_mat"]}

# ---- (2) materials
missing = [m for m in glb_mats if m not in mat_users]
multi = {m: u for m, u in mat_users.items() if len(u) != 1}
extra = [m for m in mat_users if m not in glb_mats]
def expected_layer(objname):
    return {"BODY": "Body", "HAIR": "Hair", "CLO": "Clothing"}.get(objname.split("_")[0])
coll_bad = {n: v["colls"] for n, v in per.items() if expected_layer(n) not in v["colls"]}
prop_bad = {}
for n, v in per.items():
    sm = None
    for k, val in v["props"].items():
        if "src" in k.lower() and "mat" in k.lower():
            sm = val
    if sm is None or (sm not in v["mats_used"] and str(sm) != str(v["mats_used"])):
        prop_bad[n] = {"prop": sm, "used": v["mats_used"]}
R["materials"] = {"glb_count": len(glb_mats), "missing_in_blend": missing, "used_by_not_one_object": multi,
                  "extra_non_glb": extra, "object_collection_bad": coll_bad, "src_prop_bad": prop_bad}

# ---- (4) images
imgs = {}
for n, o in meshes.items():
    for s in o.material_slots:
        m = s.material
        if not m or not m.node_tree:
            continue
        for nd in m.node_tree.nodes:
            if nd.type == "TEX_IMAGE" and nd.image:
                imgs.setdefault(nd.image.name, set()).add(m.name)
img_rep = {}
for iname, users in imgs.items():
    im = bpy.data.images[iname]
    fp = bpy.path.abspath(im.filepath) if im.filepath else ""
    try:
        sz = tuple(im.size)
        _ = im.pixels[0] if sz[0] else None
    except Exception as e:
        sz = ("ERR", str(e))
    img_rep[iname] = {"packed": im.packed_file is not None, "filepath": im.filepath,
                      "file_exists": bool(fp) and os.path.exists(fp), "size": list(sz) if isinstance(sz, tuple) else sz,
                      "has_data": im.has_data, "source": im.source, "users": sorted(users)}
R["images"] = img_rep
R["images_bad"] = [k for k, v in img_rep.items() if not (v["has_data"] and v["size"] and v["size"][0] > 0)]
R["mats_without_images"] = sorted(m.name for m in bpy.data.materials if m.users and m.node_tree and
                                  not any(nd.type == "TEX_IMAGE" for nd in m.node_tree.nodes))

# ---- (1) height / orientation
def wverts(names):
    out = []
    for nm in names:
        o = meshes.get(nm)
        if o:
            mw = o.matrix_world
            out += [mw @ v.co for v in o.data.vertices]
    return out
SKIN = ["BODY_" + s for s in ["Body", "Face", "Lips", "Head", "Ears", "Legs", "Arms", "Fingernails", "Toenails", "EyeSocket"]]
sk = wverts(SKIN)
zmax = max(v.z for v in sk); zmin = min(v.z for v in sk)
top_obj = max(SKIN, key=lambda n: max((v.co.z for v in meshes[n].data.vertices), default=-9))
low_obj = min(SKIN, key=lambda n: min((v.co.z for v in meshes[n].data.vertices), default=9))
body_all = wverts([n for n in meshes if n.startswith("BODY_")])
clo = wverts([n for n in meshes if n.startswith("CLO_")])
hair = wverts([n for n in meshes if n.startswith("HAIR_")])
def bb(vs):
    return [[min(v[i] for v in vs) for i in range(3)], [max(v[i] for v in vs) for i in range(3)]]
def cen(vs):
    return list(sum(vs, Vector()) / len(vs))
face = wverts(["BODY_Face"]); head = wverts(["BODY_Head"]); torso = wverts(["BODY_Body"])
cor = wverts(["BODY_Cornea"])
corL = [v for v in cor if v.x > 0]; corR = [v for v in cor if v.x < 0]
# nose tip: most -Y Face vertex
nose = min(face, key=lambda v: v.y)
R["geom"] = {"skin_zmax": zmax, "skin_zmin": zmin, "skin_height_cm": (zmax - zmin) * 100,
             "top_obj": top_obj, "low_obj": low_obj, "all_body_bb": bb(body_all), "skin_bb": bb(sk),
             "clothing_bb": bb(clo), "clothing_zmin": min(v.z for v in clo), "hair_bb": bb(hair),
             "overall_zmin": min(min(v.z for v in clo), zmin, min(v.z for v in hair)),
             "face_centroid": cen(face), "head_centroid": cen(head), "torso_centroid": cen(torso),
             "torso_bb": bb(torso), "nose_tip": list(nose), "corneaL_c": cen(corL), "corneaR_c": cen(corR),
             "skin_bb_center_xy": [(bb(sk)[0][i] + bb(sk)[1][i]) / 2 for i in range(2)]}
tb = bb(torso)
R["geom"]["torso_bb_center_xy"] = [(tb[0][i] + tb[1][i]) / 2 for i in range(2)]
# torso PCA facing on horizontal plane (shoulder axis)
upper = [v for v in torso if 1.20 < v.z < 1.45]
if upper:
    c = sum(upper, Vector()) / len(upper)
    sxx = sum((v.x - c.x) ** 2 for v in upper); syy = sum((v.y - c.y) ** 2 for v in upper)
    sxy = sum((v.x - c.x) * (v.y - c.y) for v in upper)
    ang = 0.5 * math.atan2(2 * sxy, sxx - syy)
    R["geom"]["upper_torso_major_axis_deg_from_X"] = math.degrees(ang)
    R["geom"]["upper_torso_centroid"] = list(c)

# ---- (6) boundaries
def loops_of(bm):
    bnd = [e for e in bm.edges if e.is_boundary]
    seen = set(); comps = []
    adj = {}
    for e in bnd:
        for v in e.verts:
            adj.setdefault(v.index, []).append(e)
    for e in bnd:
        if e.index in seen:
            continue
        stack = [e]; comp = []
        seen.add(e.index)
        while stack:
            x = stack.pop(); comp.append(x)
            for v in x.verts:
                for y in adj[v.index]:
                    if y.index not in seen:
                        seen.add(y.index); stack.append(y)
        comps.append(comp)
    out = []
    for comp in comps:
        vs = {v for e in comp for v in e.verts}
        c = sum((v.co for v in vs), Vector()) / len(vs)
        per_len = sum(e.calc_length() for e in comp)
        out.append({"edges": len(comp), "centroid": [round(c.x, 4), round(c.y, 4), round(c.z, 4)],
                    "perimeter_m": round(per_len, 4)})
    nm = sum(1 for e in bm.edges if not e.is_manifold and not e.is_boundary)
    return out, len(bnd), nm

eyeC = [Vector(R["geom"]["corneaL_c"]), Vector(R["geom"]["corneaR_c"])]
mouth = wverts(["BODY_Mouth", "BODY_Teeth"])
mbb = bb(mouth)
def classify(c):
    c = Vector(c)
    if min((c - e).length for e in eyeC) < 0.03:
        return "eye"
    if all(mbb[0][i] - 0.01 <= c[i] <= mbb[1][i] + 0.01 for i in range(3)):
        return "mouth"
    return "OTHER"

bnd = {}
for n in sorted(meshes):
    if not n.startswith("BODY_"):
        continue
    bm = bmesh.new(); bm.from_mesh(meshes[n].data)
    bm.transform(meshes[n].matrix_world)
    lp, ne, nm = loops_of(bm)
    for l in lp:
        l["class"] = classify(l["centroid"])
    bnd[n] = {"loops": len(lp), "boundary_edges": ne, "nonmanifold_nonboundary": nm, "list": lp}
    bm.free()
R["boundaries_per_object"] = {n: {k: v[k] for k in ("loops", "boundary_edges", "nonmanifold_nonboundary")} for n, v in bnd.items()}
R["boundary_loops_detail"] = {n: v["list"] for n, v in bnd.items()}

# welded shell
SHELL = SKIN + ["BODY_Mouth"]
def shell_check(names, dist):
    bm = bmesh.new()
    for n in names:
        me = meshes[n].data.copy()
        me.transform(meshes[n].matrix_world)
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    nv0 = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)
    bm.edges.ensure_lookup_table(); bm.verts.index_update(); bm.edges.index_update()
    lp, ne, nm = loops_of(bm)
    for l in lp:
        l["class"] = classify(l["centroid"])
    r = {"verts_before": nv0, "verts_after": len(bm.verts), "faces": len(bm.faces), "loops": len(lp),
         "boundary_edges": ne, "nonmanifold_nonboundary": nm, "list": lp}
    bm.free()
    return r
R["shell_weld_1e-9"] = shell_check(SHELL, 1e-9)
R["shell_weld_1e-6"] = shell_check(SHELL, 1e-6)
R["skin_no_mouth_weld_1e-9"] = shell_check(SKIN, 1e-9)
R["non_eye_mouth_loops"] = {}
for key in ("shell_weld_1e-9",):
    R["non_eye_mouth_loops"][key] = [l for l in R[key]["list"] if l["class"] == "OTHER"]
for n, v in bnd.items():
    oth = [l for l in v["list"] if l["class"] == "OTHER"]
    if oth:
        R["non_eye_mouth_loops"][n] = oth

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w") as f:
    json.dump(R, f, indent=1, default=str)
print("CHECK_DONE", OUT)
