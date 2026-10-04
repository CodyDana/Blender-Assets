import bpy, math, numpy as np
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath='C:/Users/Cody/Desktop/Blender_Projects/Exports/DojoKit/Props/taiko/SM_DKP_Taiko_Drum.fbx')
o = bpy.data.objects['SM_DKP_Taiko_Drum_LOD0']; me = o.data
V = np.array([tuple(o.matrix_world @ v.co) for v in me.vertices])
def part(ctr, ext):
    m = np.all(np.abs(V - np.array(ctr)) <= np.array(ext) / 2 + 1e-4, axis=1); return V[m]
ring = part((-0.0052, 0.7825, 0.0033), (0.1668, 0.0177, 0.1668))
c = ring.mean(0); q = ring - c
ang = np.degrees(np.arctan2(q[:, 2], q[:, 0])); r = np.hypot(q[:, 0], q[:, 2])
print('ring verts', len(ring), 'distinct major angles', len(np.unique(np.round(ang, 0))), 'distinct (r,y) per angle ~', len(ring) / max(1, len(np.unique(np.round(ang, 0)))))
boss = part((0.0093, 0.7858, 0.0778), (0.0685, 0.0424, 0.0683))
cb = boss.mean(0); qb = boss - cb
angb = np.degrees(np.arctan2(qb[:, 2], qb[:, 0]))
print('boss verts', len(boss), 'distinct angles', len(np.unique(np.round(angb, 0))))
sm = [p.use_smooth for p in me.polygons]
print('smooth faces frac', sum(sm) / len(sm))
