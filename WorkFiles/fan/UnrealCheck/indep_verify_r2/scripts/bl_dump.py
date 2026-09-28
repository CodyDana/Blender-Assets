"""Independent reference dump from Assets/Fan.blend (read only, never saved): hierarchy, rest pose, per-LOD tri
counts + section materials, probe points per bone, coincident (crack) vertex pairs per LOD, posed probe points per
action frame, posed AABB per Openness frame. All output in UE component space (cm, y flipped)."""
import bpy, json, sys, math
import numpy as np
from mathutils import Matrix, Vector
OUT = sys.argv[sys.argv.index("--")+1]
sc = bpy.context.scene
arm = bpy.data.objects["root"]
tarm = bpy.data.objects["root_tassel"]
def ue(v):  # blender armature mm -> UE cm
    return [v[0]*100.0, -v[1]*100.0, v[2]*100.0]
res = {"blend_fps": sc.render.fps}
def hier(a):
    out = {}
    for b in a.data.bones:
        out[b.name] = {"parent": b.parent.name if b.parent else None, "head_ue": ue(b.head_local), "tail_ue": ue(b.tail_local),
                       "children": [c.name for c in b.children]}
    return out
res["bones"] = hier(arm); res["bone_order"] = [b.name for b in arm.data.bones]
res["tassel_bones"] = hier(tarm)
res["arm_matrix_world"] = [list(r) for r in arm.matrix_world]
dg = bpy.context.evaluated_depsgraph_get()
# ---------------------------------------------------------------- meshes
lods = {}
bone_verts = {}
for name in ["SK_Fan", "SK_Fan_LOD1", "SK_Fan_LOD2", "SK_Fan_Tassel", "SK_Fan_Tassel_LOD1", "SK_Fan_Tassel_LOD2"]:
    o = bpy.data.objects[name]
    me = o.data
    me.calc_loop_triangles()
    a = o.parent
    M = a.matrix_world.inverted() @ o.matrix_world
    co = np.array([tuple(M @ v.co) for v in me.vertices])
    gnames = [g.name for g in o.vertex_groups]
    dom = []; ninf = []
    for v in me.vertices:
        ws = [(g.weight, gnames[g.group]) for g in v.groups if g.weight > 0]
        ninf.append(len(ws))
        dom.append(max(ws)[1] if ws else None)
    per_mat = {}
    for t in me.loop_triangles:
        mn = me.materials[t.material_index].name if me.materials[t.material_index] else None
        per_mat[mn] = per_mat.get(mn, 0) + 1
    lo = co.min(0); hi = co.max(0)
    lods[name] = {"verts": len(me.vertices), "tris": len(me.loop_triangles), "tris_per_material": per_mat,
                  "materials": [m.name for m in me.materials], "max_influences": max(ninf), "unweighted": ninf.count(0),
                  "bounds_ue_min": ue([lo[0], hi[1], lo[2]]), "bounds_ue_max": ue([hi[0], lo[1], hi[2]])}
    if name.startswith("SK_Fan") and "Tassel" not in name:
        # coincident vertices on different bones = fold-line copies (the crack pairs)
        D2 = ((co[:, None, :] - co[None, :, :]) ** 2).sum(-1)
        ii, jj = np.nonzero(D2 < (5e-6) ** 2)
        seen = set(); pairs = []
        for i, j in zip(ii.tolist(), jj.tolist()):
            if i < j and dom[i] != dom[j]:
                k = tuple(sorted((dom[i], dom[j]))) + (tuple(np.round(co[i] * 1e5).astype(int)),)
                if k in seen:
                    continue
                seen.add(k)
                pairs.append([dom[i], dom[j], ue(co[i]), ue(co[j])])
        lods[name]["crack_pairs"] = pairs
        if name == "SK_Fan":
            for i, p in enumerate(co):
                bone_verts.setdefault(dom[i], []).append(p)
            res["lod0_leaf_verts"] = {}
            lv = {}
            for i, p in enumerate(co):
                if dom[i] and dom[i].startswith("leaf_"):
                    lv.setdefault(dom[i], []).append(ue(p))
            res["lod0_leaf_verts"] = lv
res["lods"] = lods
# probe points: 4 spread vertices per bone (bind, UE cm)
probes = {}
for b, pts in bone_verts.items():
    P = np.array(pts)
    i0 = int(np.argmax(np.linalg.norm(P, axis=1)))
    sel = [i0]
    for _ in range(3):
        d = np.min(np.stack([np.linalg.norm(P - P[s], axis=1) for s in sel]), axis=0)
        sel.append(int(np.argmax(d)))
    probes[b] = [ue(P[s]) for s in sel]
res["probes"] = probes
# ---------------------------------------------------------------- posed probes per action frame
rest = {b.name: b.matrix_local.copy() for b in arm.data.bones}
if arm.animation_data is None:
    arm.animation_data_create()
anims = {}
for act in bpy.data.actions:
    arm.animation_data.action = act
    try:
        arm.animation_data.action_slot = act.slots[0]
    except Exception:
        pass
    f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
    frames = {}
    aabb = {}
    for f in range(f0, f1 + 1):
        sc.frame_set(f)
        dg.update()
        pp = {}
        for pb in arm.pose.bones:
            D = pb.matrix @ rest[pb.name].inverted()
            pp[pb.name] = [ue(D @ Vector([v[0]*0.01, -v[1]*0.01, v[2]*0.01])) for v in probes.get(pb.name, [])]
        s00 = arm.pose.bones["stick_00"].matrix; s25 = arm.pose.bones["stick_25"].matrix
        # opening: angle between the two guards' axes (bone Y axis) projected on the XY plane
        def ang(m):
            y = m.to_3x3() @ Vector((0, 1, 0)) if False else m.to_3x3().col[1]
            return math.degrees(math.atan2(y[1], y[0]))
        op = abs((ang(s25) - ang(s00) + 180) % 360 - 180)
        frames[f] = {"probes": pp, "opening_deg": op}
        if act.name == "A_Fan_Openness":
            o = bpy.data.objects["SK_Fan"].evaluated_get(dg)
            me = o.to_mesh()
            M = arm.matrix_world.inverted() @ o.matrix_world
            co = np.array([tuple(M @ v.co) for v in me.vertices])
            o.to_mesh_clear()
            lo = co.min(0); hi = co.max(0)
            aabb[f] = {"min": ue([lo[0], hi[1], lo[2]]), "max": ue([hi[0], lo[1], hi[2]])}
    anims[act.name] = {"frame_range": [f0, f1], "frames": frames, "aabb": aabb}
res["anims"] = anims
# ---------------------------------------------------------------- texture stats
tex = {}
import glob, os
for p in sorted(glob.glob(r"C:/Users/Cody/Desktop/Blender_Projects/Exports/Fan/Textures/**/*.png", recursive=True)):
    im = bpy.data.images.load(p, check_existing=False)
    im.colorspace_settings.name = "Non-Color"
    w, h = im.size
    px = np.empty(w*h*4, dtype=np.float32); im.pixels.foreach_get(px); px = px.reshape(-1, 4)
    tex[os.path.basename(p)] = {"size": [w, h], "channels": im.channels, "depth": im.depth,
                                "min": px.min(0).round(4).tolist(), "max": px.max(0).round(4).tolist(), "mean": px.mean(0).round(4).tolist()}
    bpy.data.images.remove(im)
res["textures"] = tex
json.dump(res, open(OUT, "w"))
print("DUMP_DONE", len(res["bones"]), {k: v["tris"] for k, v in lods.items()}, {k: len(v.get("crack_pairs", [])) for k, v in lods.items()})
