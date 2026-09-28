import bpy, numpy as np, json, bmesh
from mathutils import Vector
P = 'C:/Users/Cody/Desktop/Blender_Projects/Exports/BlackHat/'
side = json.load(open(P+'SM_BlackHat.sockets.json'))
def load(p):
    i = bpy.data.images.load(p); i.colorspace_settings.name = 'Non-Color'
    a = np.array(i.pixels[:], dtype=np.float32).reshape(i.size[1], i.size[0], i.channels); bpy.data.images.remove(i); return a
def s2l(s): return np.where(s <= 0.04045, s/12.92, ((s+0.055)/1.055)**2.4)
out = {}
for part, mname in (('Straw','M_BlackHat_Straw'), ('Cloth','M_BlackHat_Cloth')):
    tint = np.array(side['materials'][mname]['tint_default_linear'])
    bc = load(P+f'Textures/T_BlackHat_{part}_BC.png'); de = load(P+f'Textures/T_BlackHat_{part}_Detail.png')
    orm = load(P+f'Textures/T_BlackHat_{part}_ORM.png'); n = load(P+f'Textures/T_BlackHat_{part}_N.png')
    d8 = np.round(de[..., 0]*255).astype(int)
    bcl = s2l(bc[..., :3]); dl = s2l(de[..., 0])[..., None]*tint
    r = {'detail_min_max_8bit': [int(d8.min()), int(d8.max())], 'detail_distinct': int(len(np.unique(d8))),
         'detail_p1_p99': [float(np.percentile(d8, 1)), float(np.percentile(d8, 99))],
         'detail_rgb_equal': bool(np.allclose(de[..., 0], de[..., 1]) and np.allclose(de[..., 0], de[..., 2]))}
    # mip parity in linear
    a, b = bcl.astype(np.float64), dl.astype(np.float64); par = []
    for lvl in range(0, 12):
        m = np.abs(a - b).max(); rel = np.abs(a-b).mean()/max(a.mean(), 1e-6)
        par.append([lvl, round(float(m), 5), round(float(rel)*100, 3)])
        if a.shape[0] == 1: break
        a = a.reshape(a.shape[0]//2, 2, a.shape[1]//2, 2, 3).mean((1, 3)); b = b.reshape(b.shape[0]//2, 2, b.shape[1]//2, 2, 3).mean((1, 3))
    r['bc_vs_detail_x_tint_lin_maxabs_meanrel_pct_by_mip'] = par
    r['bc_lin_max'] = float(bcl.max()); r['bc_lin_mean'] = float(bcl.mean())
    r['orm_R_G_B_A_mean'] = [float(orm[..., c].mean()) for c in range(4)]
    r['orm_A_min_max'] = [float(orm[..., 3].min()), float(orm[..., 3].max())]
    r['orm_B_max'] = float(orm[..., 2].max())
    nn = n[..., :3]*2-1; r['N_mean'] = nn.reshape(-1, 3).mean(0).round(4).tolist()
    r['N_len_p1_p99'] = np.percentile(np.linalg.norm(nn, axis=2), [1, 99]).round(3).tolist()
    out[part] = r
# geometry: hull containment + socket + lods
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=P+'SM_BlackHat.fbx')
ob = bpy.data.objects
def verts(o): return np.array([o.matrix_world @ v.co for v in o.data.vertices])
V = verts(ob['SM_BlackHat_LOD0'])
hulls = [ob['UCX_SM_BlackHat_LOD0_00'], ob['UCX_SM_BlackHat_LOD0_01']]
def planes(o):
    bm = bmesh.new(); bm.from_mesh(o.data); bm.transform(o.matrix_world); pl = []
    for f in bm.faces: pl.append((np.array(f.normal), float(np.array(f.normal) @ np.array(f.calc_center_median()))))
    c = np.array([v.co for v in bm.verts]).mean(0); bm.free(); return pl, c
inside_any = np.zeros(len(V), bool); worst = []
for h in hulls:
    pl, c = planes(h)
    d = np.max(np.stack([V @ nrm - off for nrm, off in pl], 1), 1)   # >0 outside
    inside_any |= d <= 1e-5
    # hull convexity: vertices of hull all inside own planes
    hv = verts(h); worst.append(float(np.max(np.stack([hv @ nrm - off for nrm, off in pl], 1))))
out['hull_lod0_vertices_outside_both'] = int((~inside_any).sum())
out['hull_self_convex_max_mm'] = [w*1000 for w in worst]
out['hull_volumes_bbox'] = [[verts(h).min(0).round(4).tolist(), verts(h).max(0).round(4).tolist()] for h in hulls]
# inner apex estimate: max z of lowest skin? report vertex z stats near axis
ax = V[np.hypot(V[:, 0], V[:, 1]) < 0.02]
out['near_axis_z_min_max_mm'] = [float(ax[:, 2].min()*1000), float(ax[:, 2].max()*1000)] if len(ax) else None
out['lod0_bbox_mm'] = [(V.min(0)*1000).round(2).tolist(), (V.max(0)*1000).round(2).tolist()]
out['bounds_radius_from_origin_mm'] = float(np.linalg.norm(V, axis=1).max()*1000)
bbc = (V.min(0)+V.max(0))/2; out['bounds_radius_bbox_centre_mm'] = float(np.linalg.norm(V-bbc, axis=1).max()*1000)
out['bbox_half_diag_mm'] = float(np.linalg.norm(V.max(0)-V.min(0))/2*1000)
# does the hull block the head seat? socket position inside hull 0?
s = np.array(side['sockets'][0]['location_cm'])/100
pl, c = planes(hulls[0]); out['socket_inside_hull0'] = bool(max(s @ nrm - off for nrm, off in pl) <= 0)
print('ENG ' + json.dumps(out))
# blend: head empty
bpy.ops.wm.open_mainfile(filepath='C:/Users/Cody/Desktop/Blender_Projects/Assets/BlackHat.blend')
print('BLEND ' + json.dumps([(o.name, o.type, o.parent.name if o.parent else None, [round(x, 5) for x in o.matrix_world.translation], [round(x, 4) for x in o.matrix_world.to_euler()]) for o in bpy.data.objects if o.type == 'EMPTY' or 'SOCKET' in o.name]))
