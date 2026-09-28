"""Male fitting-body landmarks for BlackCloak_MH_v2 (rest/bind pose = the FitBody's A-pose). Opens the FitBody READ ONLY
(never saves). World: Z up, metres, front = -Y, the character's RIGHT = -X (viewer-left in a front view).
Usage: blender -b References/Characters/MH_PlayerDefault/MH_PlayerDefault_FitBody.blend --factory-startup --python v2m_body_landmarks.py -- <out.json>"""
import bpy, sys, json, math
import numpy as np
from mathutils import Vector
OUT = sys.argv[sys.argv.index("--") + 1]
dg = bpy.context.evaluated_depsgraph_get()


def verts(name):
    o = bpy.data.objects[name]; e = o.evaluated_get(dg); me = e.to_mesh()
    a = np.array([(o.matrix_world @ v.co)[:] for v in me.vertices]); e.to_mesh_clear(); return a


B = verts("FIT_MH_PlayerDefault_Body"); Hd = verts("FIT_MH_PlayerDefault_Head"); HP = verts("FIT_MH_PlayerDefault_HeadParts")
HX = verts("FIT_MH_PlayerDefault_HairProxy")
arm = bpy.data.objects["root"]


def bone(n, tail=False):
    b = arm.data.bones[n]; return list(arm.matrix_world @ (b.tail_local if tail else b.head_local))


R = {"frame": "Blender world, metres, Z up, front=-Y, character right=-X", "pose": "FitBody rest (A-pose), unposed"}
R["floor_z"] = float(B[:, 2].min()); R["head_top_z_skin"] = float(Hd[:, 2].max()); R["hair_proxy_top_z"] = float(HX[:, 2].max())
R["stature_m"] = R["head_top_z_skin"] - R["floor_z"]
mid = Hd[np.abs(Hd[:, 0]) < 0.004]
prof = []
for z in np.arange(1.45, 1.90, 0.0025):
    s = mid[np.abs(mid[:, 2] - z) < 0.00125]
    if len(s): prof.append((float(z), float(s[:, 1].min())))
prof = np.array(prof)
m = (prof[:, 0] > 1.65) & (prof[:, 0] < 1.80); i = int(np.argmin(np.where(m, prof[:, 1], 9))); nose = prof[i]
R["nose_tip"] = [0.0, float(nose[1]), float(nose[0])]
m2 = (prof[:, 0] < nose[0]) & (prof[:, 0] > nose[0] - 0.03); j = int(np.argmax(np.where(m2, prof[:, 1], -9)))
R["subnasale"] = [0.0, float(prof[j, 1]), float(prof[j, 0])]
m3 = (prof[:, 0] < prof[j, 0]) & (prof[:, 0] > prof[j, 0] - 0.025); k = int(np.argmin(np.where(m3, prof[:, 1], 9)))
R["upper_lip"] = [0.0, float(prof[k, 1]), float(prof[k, 0])]
m4 = (prof[:, 0] < prof[k, 0]) & (prof[:, 0] > prof[k, 0] - 0.02); l = int(np.argmax(np.where(m4, prof[:, 1], -9)))
R["stomion_mouth_line"] = [0.0, float(prof[l, 1]), float(prof[l, 0])]
m5 = (prof[:, 0] < prof[l, 0] - 0.01) & (prof[:, 0] > prof[l, 0] - 0.06); c = int(np.argmin(np.where(m5, prof[:, 1], 9)))
R["chin_point"] = [0.0, float(prof[c, 1]), float(prof[c, 0])]
R["midline_profile_z_y_every_1cm"] = [[round(z, 3), round(y, 4)] for z, y in prof[::4]]
for side, sg in (("l", 1), ("r", -1)):
    s = HP[(HP[:, 0] * sg > 0.015) & (HP[:, 0] * sg < 0.06) & (HP[:, 2] > nose[0])]
    med = np.median(s, 0); s2 = s[np.linalg.norm(s - med, axis=1) < 0.02]
    R["eye_%s_centre" % side] = [float(v) for v in s2.mean(0)]
    R["eye_%s_front" % side] = [float(v) for v in s2[np.argmin(s2[:, 1])]]
R["ipd_m"] = abs(R["eye_l_centre"][0] - R["eye_r_centre"][0])
R["eye_line_z"] = 0.5 * (R["eye_l_centre"][2] + R["eye_r_centre"][2])


def xext(P, z, dz=0.004):
    s = P[np.abs(P[:, 2] - z) < dz]
    return [float(s[:, 0].min()), float(s[:, 0].max())] if len(s) else None


R["head_x_extent_at_eye_line"] = xext(Hd, R["eye_line_z"]); R["head_x_extent_at_nose_tip"] = xext(Hd, nose[0])
R["head_x_extent_at_mouth"] = xext(Hd, R["stomion_mouth_line"][2])
R["hairproxy_x_extent_at_eye_line"] = xext(HX, R["eye_line_z"])
R["head_y_extent_at_mouth"] = [float(Hd[np.abs(Hd[:, 2] - R["stomion_mouth_line"][2]) < 0.004][:, 1].min()), float(Hd[np.abs(Hd[:, 2] - R["stomion_mouth_line"][2]) < 0.004][:, 1].max())]
P = np.concatenate([B, Hd])
for nb in ("neck_01", "neck_02"):
    z = bone(nb)[2]; s = P[(np.abs(P[:, 2] - z) < 0.004) & (np.hypot(P[:, 0], P[:, 1] - 0.02) < 0.12)]
    cc = s[:, :2].mean(0); r = np.linalg.norm(s[:, :2] - cc, axis=1)
    R[nb + "_ring"] = {"z": z, "centre_xy": [float(cc[0]), float(cc[1])], "r_p50": float(np.median(r)), "r_p90": float(np.percentile(r, 90)),
                       "x_extent": [float(s[:, 0].min()), float(s[:, 0].max())], "y_extent": [float(s[:, 1].min()), float(s[:, 1].max())]}
for side, sg in (("l", 1), ("r", -1)):
    ua = bone("upperarm_" + side)
    s = B[(np.abs(B[:, 0] - ua[0]) < 0.02) & (np.abs(B[:, 1] - ua[1]) < 0.05)]
    R["shoulder_top_%s" % side] = [float(ua[0]), float(ua[1]), float(s[:, 2].max())]
    s2 = B[(B[:, 2] > 1.40) & (B[:, 2] < 1.52) & (B[:, 0] * sg > 0)]
    R["deltoid_lateral_%s" % side] = [float(v) for v in s2[np.argmax(s2[:, 0] * sg)]]
    R["shoulder_line_%s_z_at_x" % side] = {str(x): float(B[(np.abs(B[:, 0] - sg * x) < 0.006) & (B[:, 2] > 1.35)][:, 2].max()) for x in (0.06, 0.08, 0.10, 0.12, 0.14, 0.16, 0.18, 0.20, 0.22)}
R["biacromial_m"] = abs(R["shoulder_top_l"][0] - R["shoulder_top_r"][0])
R["bideltoid_m"] = abs(R["deltoid_lateral_l"][0] - R["deltoid_lateral_r"][0])
for zz in (1.30, 1.35, 1.40, 1.45, 1.50):
    s = B[(np.abs(B[:, 2] - zz) < 0.005) & (np.abs(B[:, 0]) < 0.17)]
    R["torso_y_extent_at_z%.2f" % zz] = [float(s[:, 1].min()), float(s[:, 1].max())]
for xx in (-0.15, -0.12, -0.09):
    R["front_surface_y_at_x%.2f" % xx] = {("%.2f" % zz): float(B[(np.abs(B[:, 0] - xx) < 0.008) & (np.abs(B[:, 2] - zz) < 0.008)][:, 1].min()) for zz in (1.38, 1.42, 1.46, 1.50)}
for side in ("l", "r"):
    a = Vector(bone("upperarm_" + side)); b = Vector(bone("lowerarm_" + side)); d = b - a
    R["upperarm_%s_angle_from_vertical_deg" % side] = math.degrees(math.acos(-d.z / d.length))
R["bones"] = {n: bone(n) for n in ("pelvis", "spine_03", "spine_05", "neck_01", "neck_02", "head", "clavicle_l", "clavicle_r", "upperarm_l", "upperarm_r",
                                   "lowerarm_l", "lowerarm_r", "hand_l", "hand_r", "thigh_l", "thigh_r", "calf_l", "calf_r", "foot_l", "foot_r")}
for zz in (0.1, 0.3, 0.6, 0.9, 1.0):
    s = B[np.abs(B[:, 2] - zz) < 0.005]; s = s[np.abs(s[:, 0]) < 0.3]
    R["body_x_extent_at_z%.1f" % zz] = [float(s[:, 0].min()), float(s[:, 0].max())]
R["body_x_extent_all"] = [float(B[:, 0].min()), float(B[:, 0].max())]
json.dump(R, open(OUT, "w"), indent=1)
print("LANDMARKS", json.dumps({k: R[k] for k in ("stature_m", "eye_line_z", "ipd_m", "nose_tip", "subnasale", "upper_lip", "stomion_mouth_line", "chin_point",
                                               "biacromial_m", "bideltoid_m", "shoulder_top_r", "floor_z", "upperarm_r_angle_from_vertical_deg")}))
