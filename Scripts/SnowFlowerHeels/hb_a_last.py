"""Stage A: the last (the shoe's inner form) around her POSED right foot, the insole surface and the sole outline.

    blender -b WorkFiles/SnowFlowerHeels/foot_posed.blend --factory-startup --python Scripts/SnowFlowerHeels/hb_a_last.py

foot_posed.blend is only read (never saved). Output: WorkFiles/SnowFlowerHeels/r1/cache/last_r.npz
  grid (origin, shape; 1 mm voxels, local frame), f_last (float16 SDF, negative inside), f_foot (float16),
  zins (insole top per (u, v) column), outline (sole outline polygon, local mm), last_v / last_q (quad mesh),
  foot_v / foot_t (the posed foot skin, local mm).
"""
import sys
import time
from pathlib import Path

import bmesh
import bpy
import numpy as np
import openvdb as vdb

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hb_common as C  # noqa: E402

T0 = time.time()


def log(*a):
    print(f"[A {time.time() - T0:6.1f}s]", *a, flush=True)


def foot_mesh_local():
    obj = bpy.data.objects["HEEL_FootPosed_R"]
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.transform(obj.matrix_world)
    edges = [e for e in bm.edges if e.is_boundary]
    bmesh.ops.holes_fill(bm, edges=edges, sides=0)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    v = np.array([tuple(x.co) for x in bm.verts])
    t = np.array([[x.index for x in f.verts] for f in bm.faces], dtype=np.uint32)
    bm.free()
    return C.world_to_local(v, "r"), t


def main():
    C.CACHE.mkdir(parents=True, exist_ok=True)
    fv, ft = foot_mesh_local()
    log("foot", fv.shape, ft.shape, fv.min(0).round(1), fv.max(0).round(1))
    lo = np.array([-45, -72, -4])
    shape = np.array([312, 154, 304])          # u -45..266, v -72..81, w -4..299
    xf = vdb.createLinearTransform(voxelSize=1.0)
    g = vdb.FloatGrid.createLevelSetFromPolygons(fv.astype(np.float32), triangles=ft, transform=xf,
                                                 exBandWidth=40.0, inBandWidth=40.0)
    f_foot = np.zeros(tuple(shape), dtype=np.float32)
    g.copyToArray(f_foot, ijk=tuple(int(x) for x in lo))
    log("foot sdf", f_foot.min(), f_foot.max())
    U = lo[0] + np.arange(shape[0])
    V = lo[1] + np.arange(shape[1])
    W = lo[2] + np.arange(shape[2])

    # ---- insole: lowest skin per column
    inside = f_foot < 0
    has = inside.any(axis=2)
    kfirst = np.argmax(inside, axis=2)
    D = np.full(has.shape, np.nan)
    ii, jj = np.nonzero(has)
    k = kfirst[ii, jj]
    f1 = f_foot[ii, jj, k].astype(float)
    f0 = f_foot[ii, jj, np.maximum(k - 1, 0)].astype(float)
    frac = np.where(f0 - f1 > 1e-6, f0 / (f0 - f1), 1.0)
    D[ii, jj] = W[np.maximum(k - 1, 0)] + frac
    Dm = np.where(has, D, np.inf)
    z0 = Dm.min(axis=1)                         # lower envelope along u
    valid = np.isfinite(z0)
    ufoot = U[valid]
    log("foot bottom u range", ufoot.min(), ufoot.max())
    gap = C.D["insole_gap"]
    z0v = np.interp(U, U[valid], z0[valid] - gap)
    # extend behind the heel with the heel slope, and forward to the toe tip with a straight toe spring
    u_tip, v_tip, w_tip = C.D["toe_tip"]
    ins_tip = w_tip - 0.8
    u_toe_end = ufoot.max()
    j0 = np.searchsorted(U, u_toe_end - 12)
    zt0 = z0v[j0]
    fwd = U > U[j0]
    z0v[fwd] = zt0 + (U[fwd] - U[j0]) / (u_tip - U[j0]) * (ins_tip - zt0)
    back = U < ufoot.min() + 3
    jb = np.searchsorted(U, ufoot.min() + 3)
    slope = (z0v[jb + 8] - z0v[jb]) / 8.0
    z0v[back] = z0v[jb] + (U[back] - U[jb]) * slope
    # smooth along u, keep under the envelope
    env = np.interp(U, U[valid], z0[valid] - gap)
    env[fwd] = np.minimum(env[fwd], z0v[fwd])
    env[back] = z0v[back]
    z = z0v.copy()
    for _ in range(60):
        zs = np.convolve(np.pad(z, 6, mode="edge"), np.ones(13) / 13.0, mode="valid")
        z = np.minimum(zs, env)
    z0s = z
    # 2D: slight cup across v, then clamp under the actual skin columns
    Vg, Ug = np.meshgrid(V, U)
    zins = z0s[:, None] + 0.0 * Vg
    center_v = 8.0
    zins = zins + 0.0006 * (Vg - center_v) ** 2          # ~1 mm up at 40 mm from the centre
    Dcl = np.where(has, D - gap, np.inf)
    for _ in range(40):
        zins = np.minimum(C.blur2(zins, 1.5), Dcl)
    log("zins at u=0,60,130,200", [round(float(zins[np.searchsorted(U, uu), np.searchsorted(V, 8)]), 2) for uu in (0, 60, 130, 200)])

    # ---- sole outline: plan hull of the foot's lower part + margin, pulled to the toe tip
    Z3 = W[None, None, :]
    low = inside & (Z3 < (zins[:, :, None] + 22.0))
    colmask = low.any(axis=2)
    pts = np.stack([Ug[colmask], Vg[colmask]], 1).astype(float)
    hull = C.convex_hull2(pts)
    # offset the convex hull by the margin (vertex normals)
    m = C.D["outline_margin"] + 0.5
    hull = C.resample_polyline(hull, step=2.0, closed=True)
    n = len(hull)
    tang = np.roll(hull, -1, 0) - np.roll(hull, 1, 0)
    nrm = np.stack([tang[:, 1], -tang[:, 0]], 1)
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    cen = hull.mean(0)
    if ((hull - cen) * nrm).sum() < 0:
        nrm = -nrm
    hull = hull + nrm * m
    # toe: convex hull with the tip, then round everything except the tip
    tip = np.array([u_tip, v_tip])
    poly = C.convex_hull2(np.vstack([hull, tip[None]]))
    poly = C.resample_polyline(poly, step=1.5, closed=True)
    # gentle convexity on the toe flanks: push points between the ball and the tip outward by a bulge
    ball_u = 150.0
    s = np.clip((poly[:, 0] - ball_u) / (u_tip - ball_u), 0, 1)
    bulge = 2.2 * np.sin(np.pi * s) ** 1.2
    sidev = np.sign(poly[:, 1] - (v_tip + (poly[:, 0] - u_tip) * 0.0))
    poly[:, 1] += bulge * sidev * (s > 0) * (s < 1)
    # light smoothing except within 6 mm of the tip
    far = np.linalg.norm(poly - tip, axis=1) > 6.0
    for _ in range(3):
        sm = (np.roll(poly, 1, 0) + np.roll(poly, -1, 0) + poly) / 3.0
        poly[far] = sm[far]
    outline = poly
    log("outline", len(outline), outline[:, 0].min(), outline[:, 0].max(), outline[:, 1].min(), outline[:, 1].max())

    # 2D signed distance to the outline on the (u, v) grid
    d_out = C.poly_sdf2(np.stack([Ug.ravel(), Vg.ravel()], 1).astype(float), outline).reshape(Ug.shape)

    # ---- compose the last SDF
    log("compose")
    cb, cm = C.D["clear_blur"], C.D["clear_min"]
    fb = C.blur3(f_foot - cb, C.D["blur_sigma"])
    # toe box: outline prism under an elliptic dome, only in front of the ball
    ctr_u = np.interp(U, *zip(*[(0.0, 5.0), (120.0, 8.0), (u_tip, v_tip)]))
    # dome height above the insole along the axis: from the foot's toe top down to the tip
    H = np.interp(U, [120.0, 150.0, 185.0, 215.0, u_tip - 2.0, u_tip], [34.0, 32.0, 26.0, 17.0, 3.0, 0.3])
    # half width per u from the outline's distance field (inside extent)
    inside2 = d_out < 0
    vmin = np.where(inside2, Vg, np.inf).min(1)
    vmax = np.where(inside2, Vg, -np.inf).max(1)
    okrow = np.isfinite(vmin) & np.isfinite(vmax)
    vmin = np.where(okrow, vmin, v_tip)
    vmax = np.where(okrow, vmax, v_tip)
    hw = np.maximum((vmax - vmin) / 2.0, 0.5)
    vc = (vmax + vmin) / 2.0
    rel = np.clip(np.abs(Vg - vc[:, None]) / hw[:, None], 0, 1)
    top = zins + H[:, None] * np.sqrt(np.maximum(1 - rel ** 2.4, 0.0)) ** 0.8
    f_top = Z3 - top[:, :, None]
    f_side = d_out[:, :, None] + 0 * Z3
    f_toe = C.smax(f_side, f_top, 4.0)
    f_toe = C.smax(f_toe, (118.0 - U)[:, None, None] + 0 * Z3, 6.0)
    last = C.smin(fb, f_toe, 6.0)
    # low prism wall along the sole outline (real lasts are vertical at the feather edge)
    wall_h = np.interp(U, [-40, 40, 100, 160, u_tip], [11.0, 9.0, 8.0, 9.0, 3.0])
    f_prism = C.smax(f_side, Z3 - (zins + wall_h[:, None])[:, :, None], 2.5)
    f_prism = C.smax(f_prism, (-40.0 + 0 * U)[:, None, None] + 0 * Z3, 1.0)
    last = C.smin(last, f_prism, 4.0)
    # tall counter: the heel's own section (at w 112) carried straight up behind the ankle, so the counter stands
    # off the Achilles like the reference's armoured back (and clears the calf when the ankle flexes)
    k112 = int(112 - lo[2])
    sec = f_foot[:, :, k112].astype(np.float32) - 3.5
    bulge = 8.0 * np.exp(-0.5 * ((W - 170.0) / 50.0) ** 2)            # the medallion bulge (reference counter stands well off)
    f_counter = sec[:, :, None] - bulge[None, None, :]
    f_counter = C.smax(f_counter, (U[:, None, None] - 38.0) + 0 * Z3, 5.0)
    f_counter = C.smax(f_counter, (95.0 - Z3) + 0 * U[:, None, None], 6.0)
    last = C.smin(last, f_counter, 8.0)
    last = np.minimum(last, f_foot - cm)                                 # never closer than clear_min
    last = C.smax(last, zins[:, :, None] - Z3, 0.8)                      # cut by the insole
    last = np.maximum(last, Z3 - 296.0)                                  # open top (never meshed that high anyway)
    last = np.maximum(last, (U[:, None, None] - (u_tip + 0.4)) + 0 * Z3)
    last = last.astype(np.float32)
    log("last sdf done", float(last.min()), float(last.max()))

    g2 = vdb.FloatGrid()
    g2.transform = xf
    g2.background = 40.0
    g2.copyFromArray(last, ijk=tuple(int(x) for x in lo), tolerance=0.0)
    pts_q, tris_q, quads_q = g2.convertToPolygons(isovalue=0.0, adaptivity=0.0)
    log("last mesh", pts_q.shape, tris_q.shape, quads_q.shape)

    np.savez_compressed(C.CACHE / "last_r.npz", lo=lo, shape=shape, f_last=last.astype(np.float16),
                        f_foot=f_foot.astype(np.float16), zins=zins.astype(np.float32), U=U, V=V, W=W,
                        outline=outline, last_v=pts_q, last_t=tris_q, last_q=quads_q, foot_v=fv, foot_t=ft,
                        d_out=d_out.astype(np.float32), has=has, D=np.nan_to_num(D, nan=-1.0).astype(np.float32))
    log("saved", C.CACHE / "last_r.npz")


main()
