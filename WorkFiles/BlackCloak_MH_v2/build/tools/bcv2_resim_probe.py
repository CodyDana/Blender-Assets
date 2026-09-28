"""Posed re-simulation of the SHIPPED cloth section (a Blender stand-in for Chaos, used before any Unreal run).

blender -b --factory-startup --python v2m_posed_resim.py -- [--fbx <fbx>] --out <dir> [--poses idle,long_stride,arms_forward,deep_crouch,arms_up]
      [--frames 120] [--quality 6] [--mass 0.5] [--bending 1.5]

For each pose: the fitting body starts in ARMS_DOWN_V2 (the drape pose, where the bind shape is valid), holds it for
frames 1-15, blends to the target pose over frames 15-45 (garment_qa POSES; 'idle' = ARMS_DOWN_V2 held; 'apose' = the
rest A-pose = the photo's product-form support, see TARGET_SPEC 6.2) and holds it to
the last frame. The garment's skinned part follows its spine weights (Armature modifier); the *_Sim section is split off
and gets Blender cloth AFTER its Armature modifier with the PinMask red channel as the pin group (pin stiffness 1, so
red = follows the skinned pose, 0 = free), self-collision ON, colliding with the posed body + head (all regions,
arms included) and a floor at z = 0. At the last frame it reports: sim vertices inside the skin deeper than 5 mm (all
regions), skinned vertices inside by region, self-intersecting face pairs in the sim section, lowest hem z, the settled
drop of the sim section vs its bind shape (mean / p95 displacement), and writes Workbench front + side PNGs and a
photo-camera alpha PNG (<pose>_photo_alpha.png, 417x674 x2) for v2m_silhouette_score-style IoU (idle = the in-game
idle stand-in: the review's settled IoU 0.797 problem)."""
import sys, os, json, math, argparse, time
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_MH_v2/spec/scripts")
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from v2m_common import *

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser(); ap.add_argument("--fbx", default=DEFAULT_FBX); ap.add_argument("--out", required=True)
ap.add_argument("--poses", default="idle,apose,long_stride,arms_forward,deep_crouch,arms_up"); ap.add_argument("--frames", type=int, default=120)
ap.add_argument("--quality", type=int, default=6); ap.add_argument("--floor-thick", type=float, default=-1); ap.add_argument("--mass", type=float, default=0.5); ap.add_argument("--bending", type=float, default=1.5)
A = ap.parse_args(argv)
os.chdir(ROOT); A.fbx = os.path.abspath(A.fbx); A.out = os.path.abspath(A.out); os.makedirs(A.out, exist_ok=True)
from pipeline import garment_qa as gq


def keyframe_pose(arm, frame):
    for pb in arm.pose.bones:
        pb.keyframe_insert("location", frame=frame); pb.keyframe_insert("rotation_quaternion", frame=frame)


def run_pose(pose_name):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    t0 = time.time()
    fit = fitbody(); drop_haircards(); arm = fit["armature"]
    meshes = import_garment(A.fbx, arm)
    sc = bpy.context.scene; sc.frame_start = 1; sc.frame_end = A.frames; sc.render.fps = 30
    for pb in arm.pose.bones: pb.rotation_mode = "QUATERNION"
    apply_pose(arm, ARMS_DOWN_V2); keyframe_pose(arm, 1); keyframe_pose(arm, 15)
    # idle = ARMS_DOWN_V2 held (settle test); apose = back to the rest A-pose (the PRODUCT-FORM drape: the photo's
    # ghost mannequin holds its arms out under the cloak, so the photo outline is scored on this drape)
    ops = ARMS_DOWN_V2 if pose_name == "idle" else ([] if pose_name == "apose" else gq.POSES[pose_name])
    apply_pose(arm, ops); keyframe_pose(arm, 45); keyframe_pose(arm, A.frames)
    sc.frame_set(1)
    bind_lo, bind_hi = bbox_of(meshes)   # photo framing from the BIND shape (same framing as the rest photo render)
    # split the *_Sim faces off every garment mesh into one cloth object
    simobjs = []; skinned = []
    for o in meshes:
        sidx = [i for i, m in enumerate(o.data.materials) if m and m.name.endswith("_Sim")]
        if not sidx: skinned.append(o); continue
        bpy.context.view_layer.objects.active = o
        for ob in bpy.context.selected_objects: ob.select_set(False)
        o.select_set(True)
        bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="DESELECT")
        bpy.ops.object.mode_set(mode="OBJECT")
        for p in o.data.polygons: p.select = p.material_index in sidx
        bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.separate(type="SELECTED"); bpy.ops.object.mode_set(mode="OBJECT")
        new = [ob for ob in bpy.context.selected_objects if ob is not o]
        simobjs += new; skinned.append(o)
    assert len(simobjs) == 1, [s.name for s in simobjs]
    so = simobjs[0]; me = so.data
    # PinMask red -> vertex group
    ca = me.color_attributes.get("PinMask"); pin = so.vertex_groups.new(name="V2M_PIN")
    red = np.zeros(len(me.vertices))
    if ca is not None:
        for p in me.polygons:
            for li in p.loop_indices:
                vi = me.loops[li].vertex_index
                c = ca.data[li].color[0] if ca.domain == "CORNER" else ca.data[vi].color[0]
                red[vi] = max(red[vi], c)
    for i, r in enumerate(red):
        if r > 0: pin.add([i], float(r), "REPLACE")
    bind_co = np.array([so.matrix_world @ v.co for v in me.vertices])
    cm = so.modifiers.new("Cloth", "CLOTH"); s = cm.settings
    s.quality = A.quality; s.mass = A.mass; s.air_damping = 1.0
    s.tension_stiffness = 40; s.compression_stiffness = 40; s.shear_stiffness = 20; s.bending_stiffness = A.bending
    s.vertex_group_mass = "V2M_PIN"; s.pin_stiffness = 1.0
    c = cm.collision_settings; c.distance_min = 0.006; c.collision_quality = 3; c.use_self_collision = True; c.self_distance_min = 0.004
    cm.point_cache.frame_start = 1; cm.point_cache.frame_end = A.frames
    for key in ("body", "head"):
        ob = fit[key]; col = ob.modifiers.new("Collision", "COLLISION"); ob.collision.thickness_outer = 0.006; ob.collision.cloth_friction = 5.0
    fme = bpy.data.meshes.new("V2M_Floor"); bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=4); bm.to_mesh(fme); bm.free()
    floor = bpy.data.objects.new("V2M_Floor", fme); sc.collection.objects.link(floor); floor.modifiers.new("Collision", "COLLISION")
    if A.floor_thick >= 0: floor.collision.thickness_outer = A.floor_thick
    per = []
    for f in range(1, A.frames + 1):
        ts = time.time(); sc.frame_set(f); per.append(time.time() - ts)
    # ---- measure
    co, polys = evaluated_coords(so)
    skin = [fit["body"], fit["head"]]
    colr = gq.Collider(skin, [gq.dominant_regions(o) for o in skin])
    d, found, reg = colr.signed(co, 0.25)
    inside = found & (d < -0.005)
    rec = {"pose": pose_name, "sim_verts": len(co), "sim_inside_gt5mm": int(inside.sum()), "sim_inside_by_region": {r: int((inside & (reg == r)).sum()) for r in set(reg[inside])},
           "sim_deepest_cm": float(max(0.0, -d[found].min()) * 100) if found.any() else None}
    sk = {}
    for o in skinned:
        c2, _ = evaluated_coords(o); d2, f2, r2 = colr.signed(c2, 0.25); ins2 = f2 & (d2 < -0.005)
        for r in set(r2[ins2]): sk[r] = sk.get(r, 0) + int((ins2 & (r2 == r)).sum())
    rec["skinned_inside_gt5mm_by_region"] = sk
    disp = np.linalg.norm(co - bind_co, axis=1)
    rec["sim_displacement_vs_bind_cm_mean_p95"] = [float(disp.mean() * 100), float(np.percentile(disp, 95) * 100)]
    rec["sim_zmin"] = float(co[:, 2].min())
    zb_ = bind_co[:, 2]
    rec["disp_by_bind_z"] = {"%.1f" % z0: [float(disp[(zb_ >= z0) & (zb_ < z0 + 0.3)].mean() * 100) if ((zb_ >= z0) & (zb_ < z0 + 0.3)).any() else None, int(((zb_ >= z0) & (zb_ < z0 + 0.3)).sum())] for z0 in (0.0, 0.3, 0.6, 0.9, 1.2, 1.5)}
    rec["disp_z_component_mean_cm"] = float((co[:, 2] - bind_co[:, 2]).mean() * 100)
    jm = bpy.data.meshes.new("V2M_simres"); jm.from_pydata(co.tolist(), [], polys)
    bmr = bmesh.new(); bmr.from_mesh(jm); bmr.faces.ensure_lookup_table()
    tr = BVHTree.FromBMesh(bmr); fv = [set(v.index for v in f.verts) for f in bmr.faces]
    rec["sim_self_intersections"] = int(sum(1 for i, j in tr.overlap(tr) if i < j and not (fv[i] & fv[j])))
    rec["sec_per_frame_mean_max"] = [float(np.mean(per)), float(np.max(per))]
    # ---- pictures: Workbench front / side with body, photo-camera garment alpha
    res_ob = bpy.data.objects.new("V2M_SimResult", jm); sc.collection.objects.link(res_ob)
    so.hide_render = True; floor.hide_render = True
    sc.render.engine = "BLENDER_WORKBENCH"; sh = sc.display.shading; sh.light = "STUDIO"; sh.color_type = "OBJECT"; sh.show_cavity = True
    for o in [res_ob] + skinned: o.color = (0.12, 0.12, 0.13, 1)
    for key in ("body", "head"): fit[key].color = (0.8, 0.66, 0.58, 1)
    arm.hide_render = True
    if fit.get("head_parts"): fit["head_parts"].hide_render = True
    fit["hair_proxy"].hide_render = True
    sc.render.film_transparent = False
    for view in ("front", "side_r", "back"):
        cam, _ = make_camera(view)
        sc.render.filepath = os.path.join(A.out, "%s_%s.png" % (pose_name, view)); bpy.ops.render.render(write_still=True)
    # photo alpha (garment only, black), framing from the BIND garment bbox so it matches the rest photo render
    for key in ("body", "head"): fit[key].hide_render = True
    tgt = Vector(((bind_lo[0] + bind_hi[0]) / 2, (bind_lo[1] + bind_hi[1]) / 2, (bind_lo[2] + bind_hi[2]) / 2))
    span = (bind_hi[2] - bind_lo[2]) * 1.08
    cam, crec = make_camera("photo", None, {"res": (REF_W * 2, REF_H * 2), "frame": "fixed", "target": tuple(tgt), "span_m": span})
    sc.render.film_transparent = True; sh.light = "FLAT"; sh.show_cavity = False
    for o in [res_ob] + skinned: o.color = (0, 0, 0, 1)
    sc.render.filepath = os.path.join(A.out, "%s_photo_alpha.png" % pose_name); bpy.ops.render.render(write_still=True)
    rec["photo_camera"] = crec; rec["seconds"] = time.time() - t0
    lm = {"floor_origin": [0.0, 0.0, 0.0], "shoulder_line_clothed_r": [-0.18, 0.0, 1.56], "shoulder_line_clothed_l": [0.18, 0.0, 1.56]}
    json.dump({"args": {"mult": 2}, "camera": crec, "landmarks_3d": lm, "landmarks_px": dict(zip(lm.keys(), project(cam, lm.values()))),
               "note": "posed re-sim photo alpha; score with v2m_silhouette_score.py <dir> %s_photo" % pose_name},
              open(os.path.join(A.out, "%s_photo.json" % pose_name), "w"), indent=1, default=float)
    return rec


out = {"fbx": A.fbx, "settings": vars(A), "poses": {}}
for pn in A.poses.split(","):
    try:
        out["poses"][pn] = run_pose(pn)
    except Exception as e:
        import traceback; out["poses"][pn] = {"error": repr(e), "trace": traceback.format_exc()}
    json.dump(out, open(os.path.join(A.out, "posed_resim.json"), "w"), indent=1, default=float)
    log("RESIM", pn, json.dumps({k: v for k, v in out["poses"][pn].items() if k not in ("photo_camera", "trace")}, default=float)[:900])
