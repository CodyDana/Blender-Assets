"""verify_engineering: sim-section quality of the MH FBX + texture checks (read-only)."""
import bpy, bmesh, json, sys, math
import numpy as np
out = sys.argv[sys.argv.index('--') + 1]
R = {}
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=r'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/garment_pipeline/BlackCloak/export/SK_BlackCloak_MH.fbx')
o = [x for x in bpy.context.scene.objects if x.type == 'MESH'][0]
me = o.data
simi = [i for i, m in enumerate(me.materials) if m.name.endswith('_Sim')][0]
bm = bmesh.new(); bm.from_mesh(me); bm.transform(o.matrix_world)
faces = [f for f in bm.faces if f.material_index == simi]
edges = set(); angs = []
for f in faces:
    for e in f.edges: edges.add(e)
    vs = [v.co for v in f.verts]
    for i in range(3):
        a, b, c = vs[i], vs[(i + 1) % 3], vs[(i + 2) % 3]
        u, w = b - a, c - a
        if u.length > 0 and w.length > 0: angs.append(math.degrees(u.angle(w)))
mins = [min(angs[i:i + 3]) for i in range(0, len(angs), 3)]
el = sorted(e.calc_length() * 100 for e in edges)
R['sim'] = {'tris': len(faces), 'verts': len({v for f in faces for v in f.verts}), 'edge_cm_median': round(el[len(el) // 2], 2), 'edge_cm_p95': round(el[int(.95 * len(el))], 2), 'edge_cm_max': round(el[-1], 2),
            'min_angle_median': round(sorted(mins)[len(mins) // 2], 2), 'tris_min_angle_lt10': sum(1 for m in mins if m < 10), 'tris_min_angle_lt5': sum(1 for m in mins if m < 5)}
# PinMask on sim
ca = me.color_attributes.get('PinMask')
if ca:
    red = [0] * len(me.vertices)
    if ca.domain == 'POINT':
        for i, d in enumerate(ca.data): red[i] = d.color[0]
    else:
        for li, l in enumerate(me.loops): red[l.vertex_index] = max(red[l.vertex_index], ca.data[li].color[0])
    simv = {v.index for f in faces for v in f.verts}
    R['pinmask'] = {'domain': ca.domain, 'red_gt_0.5_all': sum(1 for r in red if r > .5), 'red_gt_0.5_sim': sum(1 for i in simv if red[i] > .5)}
# textures
T = r'C:/Users/Cody/Desktop/Blender_Projects/Exports/BlackCloak/Textures/'
def load(n):
    im = bpy.data.images.load(T + n); im.colorspace_settings.name = 'Non-Color'
    a = np.array(im.pixels[:], dtype=np.float32).reshape(im.size[1], im.size[0], im.channels)
    return im, a
imdx, dx = load('T_BlackCloak_Normal_DirectX.png'); imgl, gl = load('T_BlackCloak_Normal_OpenGL.png')
rim, ro = load('T_BlackCloak_Roughness.png'); bim, bc = load('T_BlackCloak_BaseColor.png')
R['tex'] = {'size': list(imdx.size), 'channels': [imdx.channels, imgl.channels, rim.channels, bim.channels],
            'dx_g_plus_gl_g_minus1_maxabs': float(np.abs(dx[..., 1] + gl[..., 1] - 1).max()),
            'dx_r_eq_gl_r_maxabs': float(np.abs(dx[..., 0] - gl[..., 0]).max()),
            'rough_min_max': [float(ro[..., 0].min()), float(ro[..., 0].max())],
            'bc_srgb255_min_max': [round(float(bc[..., 0].min()) * 255), round(float(bc[..., 0].max()) * 255)],
            'normal_xy_absmax': [float(np.abs(gl[..., 0] * 2 - 1).max()), float(np.abs(gl[..., 1] * 2 - 1).max())]}
# sign check: green of OpenGL should correlate positively with d(height)/dy... use BaseColor as height proxy
h = bc[..., 0]; dy = np.roll(h, -1, 0) - np.roll(h, 1, 0)  # rows increase upward in Blender pixel order
g = gl[..., 1] * 2 - 1
R['tex']['corr_gl_green_vs_minus_dHdy_bottomup'] = float(np.corrcoef(g.ravel(), -dy.ravel())[0, 1])
json.dump(R, open(out, 'w'), indent=1)
print('VE_ST_DONE')
