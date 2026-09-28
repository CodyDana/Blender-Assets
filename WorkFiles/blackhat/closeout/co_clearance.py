"""Close-out: clearance of the tails, lashings and ribs above the skin-to-tube fillet (read-only on the blend)."""
import sys, json
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
import bpy, numpy as np
from props_lib import blackhat_geom as G
from props_lib.blackhat_spec import BLACK_HAT
hat = G.Hat(BLACK_HAT)
out = {"fillet": {"rho_mm": hat.fil_rho, "p0_rz": hat.fil_p0.tolist(), "p1_rz": hat.fil_p1.tolist(),
                  "tube_angle_deg": float(np.degrees(np.arctan2(hat.fil_p1[1] - hat.zc, hat.fil_p1[0] - hat.Rc)))}}
for lod in range(3):
    mb = G.build_lod(BLACK_HAT, lod, None, tails=None) if False else None
ob = {o.name: o for o in bpy.data.objects}
for name in ("SM_BlackHat_LOD0", "SM_BlackHat_LOD1", "SM_BlackHat_LOD2"):
    me = ob[name].data
    P = np.array([v.co[:] for v in me.vertices]) * (1000.0 if max(ob[name].dimensions) < 5 else 1.0)
    mw = np.array(ob[name].matrix_world)
    slot = np.zeros(len(P), int)
    for p in me.polygons:
        for vi in p.vertices:
            slot[vi] = max(slot[vi], p.material_index)
    r = np.hypot(P[:, 0], P[:, 1]); z = P[:, 2]
    band = (r > hat.fil_p0[0]) & (r < hat.fil_p1[0])
    dz = z - hat.fillet_z(r)
    cl = band & (slot == 1)
    out[name] = {"scale_guess": float(np.abs(P).max()), "cloth_verts_over_fillet": int(cl.sum()),
                 "cloth_min_dz_mm": float(dz[cl].min()) if cl.any() else None,
                 "straw_verts_below_fillet_by_0.2mm": int(((dz < -0.2) & band & (slot == 0)).sum())}
print("CLEAR " + json.dumps(out))
