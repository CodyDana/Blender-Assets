"""Render the mist / spray flipbooks and the haze sprite in Cycles and pack them (headless Blender 5.2).

    blender -b --factory-startup --python Scripts/dojo/fx/render_flipbooks.py -- \
        --only puff,wisp,spray,haze [--cell 512] [--grid 8] [--samples 192] [--frames 0,63] [--preview]

Each flipbook is a life cycle (birth -> dissipation) of 64 frames on an 8 x 8 grid (row-major from the top left, the
Unreal SubUV / Niagara convention). Colour-neutral: the volume / water is white and lit ONLY by six white suns, one
per axis, each in its own Cycles light group, so ONE render per frame gives the six directional lighting passes and
the alpha (film transparent):

  T_DKF_<Name>_SixWayP  RGBA linear: R = lit from +X (right), G = lit from +Z (top), B = lit from +Y (back, i.e. from
                        behind the sprite toward the camera), A = opacity
  T_DKF_<Name>_SixWayN  RGBA linear: R = lit from -X (left), G = lit from -Z (bottom), B = lit from -Y (front, the
                        camera side), A = opacity again (so either map alone is usable)

Camera: orthographic, looking along +Y (sprite space: +X right, +Z up, +Y away from the viewer). The lighting
values are normalised per flipbook by one factor (the 99.8th percentile of all six passes -> 1.0). A plain
single-texture use is SixWayP.G (top-lit) as luminance with SixWayP.A as opacity.

Frame renders go to WorkFiles/dojo/build/fx/src_textures/<name>/ (EXR, not shipped).
"""
from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fx_bl as B  # noqa: E402
import fx_common as fx  # noqa: E402

LIGHTS = {  # name: direction the light COMES FROM (unit vector from the sprite toward the light)
    "PX": (1, 0, 0), "PZ": (0, 0, 1), "PY": (0, 1, 0),
    "NX": (-1, 0, 0), "NZ": (0, 0, -1), "NY": (0, -1, 0),
}


def args():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--only", default="puff,wisp,spray,haze")
    p.add_argument("--cell", type=int, default=512)
    p.add_argument("--grid", type=int, default=8)
    p.add_argument("--samples", type=int, default=192)
    p.add_argument("--frames", default=None, help="first,last frame to render (default all)")
    p.add_argument("--preview", action="store_true", help="skip the packing, only render the listed frames")
    return p.parse_args(a)


# --------------------------------------------------------------------------- scene

def base_scene(cell, samples, res=None):
    sc = B.reset_scene()
    B.cycles(sc, samples=samples, res=res or (cell, cell), transparent=True, denoise=False, view="Standard")
    sc.cycles.volume_step_rate = 0.5
    sc.cycles.volume_max_steps = 1024
    sc.cycles.max_bounces = 8
    sc.cycles.volume_bounces = 12
    sc.cycles.transparent_max_bounces = 16
    sc.cycles.use_adaptive_sampling = False
    sc.render.image_settings.media_type = "MULTI_LAYER_IMAGE"
    sc.render.image_settings.file_format = "OPEN_EXR_MULTILAYER"
    sc.render.image_settings.color_depth = "16"
    sc.render.image_settings.color_mode = "RGBA"
    w = bpy.data.worlds.new("Black")
    sc.world = w
    w.use_nodes = True
    next(n for n in w.node_tree.nodes if n.type == "BACKGROUND").inputs["Strength"].default_value = 0.0
    vl = sc.view_layers[0]
    for name, d in LIGHTS.items():
        vl.lightgroups.add(name=name)
        ld = bpy.data.lights.new(name, "SUN")
        ld.energy = 3.0
        ld.angle = math.radians(10)
        ob = bpy.data.objects.new(name, ld)
        sc.collection.objects.link(ob)
        ob.rotation_euler = Vector(d).to_track_quat("Z", "Y").to_euler()
        ob.lightgroup = name
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 2.0
    cam.location = (0, -5, 0)
    cam.rotation_euler = (math.pi / 2, 0, 0)
    return sc


def volume_cube(name, size=(1, 1, 1)):
    me = bpy.data.meshes.new(name)
    sx, sy, sz = size
    v = [(x * sx, y * sy, z * sz) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
    f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    me.from_pydata(v, [], f)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


class Params:
    """Value nodes in the density graph, set per frame."""

    def __init__(self, tree):
        self.tree = tree
        self.nodes = {}

    def value(self, name, default, loc):
        n = B.node(self.tree, "ShaderNodeValue", loc)
        n.label = name
        n.outputs[0].default_value = default
        self.nodes[name] = n
        return n.outputs[0]

    def set(self, **kw):
        for k, v in kw.items():
            self.nodes[k].outputs[0].default_value = float(v)


def mist_material(kind):
    """Principled Volume, density = eroded warped fBm inside a growing ellipsoid envelope."""
    mat = bpy.data.materials.new("M_" + kind)
    mat.use_nodes = True
    t = mat.node_tree
    t.nodes.clear()
    P = Params(t)
    tc = B.node(t, "ShaderNodeTexCoord", (-2000, 0))
    # drift offset
    ox, oz = P.value("ox", 0, (-2000, -300)), P.value("oz", 0, (-2000, -380))
    off = B.node(t, "ShaderNodeCombineXYZ", (-1800, -300))
    B.link(t, ox, off.inputs[0]); B.link(t, oz, off.inputs[2])
    p0 = B.node(t, "ShaderNodeVectorMath", (-1700, 0), operation="SUBTRACT")
    B.link(t, B.out(tc, "Object"), p0.inputs[0]); B.link(t, off.outputs[0], p0.inputs[1])
    p = B.node(t, "ShaderNodeVectorRotate", (-1600, 0), rotation_type="Y_AXIS")
    B.link(t, p0.outputs[0], B.inp(p, "Vector"))
    B.link(t, P.value("tilt", 0.0, (-1800, -120)), B.inp(p, "Angle"))
    # envelope: |p / radii| with radii from values; a flattened bottom for the puff
    rx, ry, rz = P.value("rx", 0.6, (-2000, -500)), P.value("ry", 0.5, (-2000, -580)), P.value("rz", 0.5, (-2000, -660))
    rad = B.node(t, "ShaderNodeCombineXYZ", (-1800, -560))
    B.link(t, rx, rad.inputs[0]); B.link(t, ry, rad.inputs[1]); B.link(t, rz, rad.inputs[2])
    q = B.node(t, "ShaderNodeVectorMath", (-1400, -400), operation="DIVIDE")
    B.link(t, p.outputs[0], q.inputs[0]); B.link(t, rad.outputs[0], q.inputs[1])
    # warp the envelope with low-frequency noise so the silhouette is lumpy, not an ellipsoid
    wlow = B.node(t, "ShaderNodeTexNoise", (-1400, -700), noise_dimensions="4D")
    B.link(t, p.outputs[0], B.inp(wlow, "Vector"))
    wW = P.value("W", 0, (-2000, -800))
    B.link(t, wW, B.inp(wlow, "W"))
    B.inp(wlow, "Scale").default_value = 1.6
    B.inp(wlow, "Detail").default_value = 2.0
    ln = B.node(t, "ShaderNodeVectorMath", (-1200, -400), operation="LENGTH")
    B.link(t, q.outputs[0], ln.inputs[0])
    lw = B.node(t, "ShaderNodeMath", (-1000, -450), operation="MULTIPLY_ADD")
    B.link(t, B.out(wlow, "Factor"), lw.inputs[0])
    lump = P.value("lump", 0.6, (-1200, -600))
    B.link(t, lump, lw.inputs[1])
    B.link(t, B.out(ln, "Value"), lw.inputs[2])
    lw2 = B.node(t, "ShaderNodeMath", (-850, -450), operation="SUBTRACT")
    B.link(t, lw.outputs[0], lw2.inputs[0])
    half = B.node(t, "ShaderNodeMath", (-1000, -600), operation="MULTIPLY")
    B.link(t, lump, half.inputs[0]); half.inputs[1].default_value = 0.5
    B.link(t, half.outputs[0], lw2.inputs[1])
    env = B.node(t, "ShaderNodeMapRange", (-650, -450))
    B.link(t, lw2.outputs[0], B.inp(env, "Value"))
    B.inp(env, "From Min").default_value = 1.0
    B.inp(env, "From Max").default_value = 0.35
    env.interpolation_type = "SMOOTHSTEP"
    # detail: anisotropic (streaky) domain-warped fBm
    sx, sy, sz = P.value("sx", 1, (-2000, 200)), P.value("sy", 1, (-2000, 120)), P.value("sz", 1, (-2000, 40))
    sv = B.node(t, "ShaderNodeCombineXYZ", (-1800, 150))
    B.link(t, sx, sv.inputs[0]); B.link(t, sy, sv.inputs[1]); B.link(t, sz, sv.inputs[2])
    ps = B.node(t, "ShaderNodeVectorMath", (-1400, 150), operation="MULTIPLY")
    B.link(t, p.outputs[0], ps.inputs[0]); B.link(t, sv.outputs[0], ps.inputs[1])
    warp = B.node(t, "ShaderNodeTexNoise", (-1200, 350), noise_dimensions="4D")
    B.link(t, ps.outputs[0], B.inp(warp, "Vector")); B.link(t, wW, B.inp(warp, "W"))
    B.inp(warp, "Scale").default_value = 1.2
    B.inp(warp, "Detail").default_value = 3.0
    wc = B.node(t, "ShaderNodeVectorMath", (-1000, 350), operation="SUBTRACT")
    B.link(t, B.out(warp, "Color"), wc.inputs[0]); wc.inputs[1].default_value = (0.5, 0.5, 0.5)
    wamt = P.value("warp", 0.8, (-1200, 500))
    ws = B.node(t, "ShaderNodeVectorMath", (-850, 350), operation="SCALE")
    B.link(t, wc.outputs[0], ws.inputs[0]); B.link(t, wamt, B.inp(ws, "Scale"))
    pw = B.node(t, "ShaderNodeVectorMath", (-700, 200), operation="ADD")
    B.link(t, ps.outputs[0], pw.inputs[0]); B.link(t, ws.outputs[0], pw.inputs[1])
    det = B.node(t, "ShaderNodeTexNoise", (-500, 200), noise_dimensions="4D")
    B.link(t, pw.outputs[0], B.inp(det, "Vector")); B.link(t, wW, B.inp(det, "W"))
    dscale = P.value("dscale", 2.2, (-700, 400))
    B.link(t, dscale, B.inp(det, "Scale"))
    dd_ = P.value("detail", 6.0, (-700, 480))
    B.link(t, dd_, B.inp(det, "Detail"))
    rr_ = P.value("rough", 0.58, (-700, 560))
    B.link(t, rr_, B.inp(det, "Roughness"))
    # erosion: (noise - thr) * gain, clamped, times envelope and life
    thr = P.value("thr", 0.45, (-500, 400))
    er0 = B.node(t, "ShaderNodeMath", (-400, 200), operation="SUBTRACT")
    B.link(t, B.out(det, "Factor"), er0.inputs[0]); B.link(t, thr, er0.inputs[1])
    # core boost: the inside of the envelope erodes last (dense core, billowy / feathered rim)
    e2 = B.node(t, "ShaderNodeMath", (-450, 50), operation="POWER")
    B.link(t, B.out(env, "Result"), e2.inputs[0]); e2.inputs[1].default_value = 2.0
    cb = P.value("core", 0.10, (-600, 50))
    er = B.node(t, "ShaderNodeMath", (-300, 200), operation="MULTIPLY_ADD")
    B.link(t, e2.outputs[0], er.inputs[0]); B.link(t, cb, er.inputs[1]); B.link(t, er0.outputs[0], er.inputs[2])
    # soften: the erosion edge is feathered by env (thin at the rim)
    gain = P.value("gain", 6.0, (-300, 400))
    g = B.node(t, "ShaderNodeMath", (-150, 200), operation="MULTIPLY", use_clamp=False)
    B.link(t, er.outputs[0], g.inputs[0]); B.link(t, gain, g.inputs[1])
    ge = B.node(t, "ShaderNodeMath", (0, 200), operation="MULTIPLY")
    B.link(t, g.outputs[0], ge.inputs[0]); B.link(t, B.out(env, "Result"), ge.inputs[1])
    cl = B.node(t, "ShaderNodeMath", (150, 200), operation="MAXIMUM")
    B.link(t, ge.outputs[0], cl.inputs[0]); cl.inputs[1].default_value = 0.0
    # add a soft floor of thin haze inside the envelope (feathered, never a hard edge)
    base = P.value("base", 0.08, (0, 400))
    hz = B.node(t, "ShaderNodeMath", (150, 380), operation="MULTIPLY")
    B.link(t, B.out(env, "Result"), hz.inputs[0]); B.link(t, base, hz.inputs[1])
    hz2 = B.node(t, "ShaderNodeMath", (300, 300), operation="MULTIPLY")
    B.link(t, hz.outputs[0], hz2.inputs[0]); B.link(t, B.out(det, "Factor"), hz2.inputs[1])
    dsum = B.node(t, "ShaderNodeMath", (450, 250), operation="ADD")
    B.link(t, cl.outputs[0], dsum.inputs[0]); B.link(t, hz2.outputs[0], dsum.inputs[1])
    life = P.value("life", 1.0, (450, 450))
    dl = B.node(t, "ShaderNodeMath", (600, 250), operation="MULTIPLY")
    B.link(t, dsum.outputs[0], dl.inputs[0]); B.link(t, life, dl.inputs[1])
    dens = P.value("density", 8.0, (600, 450))
    dd = B.node(t, "ShaderNodeMath", (750, 250), operation="MULTIPLY")
    B.link(t, dl.outputs[0], dd.inputs[0]); B.link(t, dens, dd.inputs[1])
    pv = B.node(t, "ShaderNodeVolumePrincipled", (950, 200))
    B.inp(pv, "Color").default_value = (1, 1, 1, 1)
    B.inp(pv, "Anisotropy").default_value = 0.25
    B.link(t, dd.outputs[0], B.inp(pv, "Density"))
    mo = B.node(t, "ShaderNodeOutputMaterial", (1150, 200))
    B.link(t, B.out(pv, "Volume"), B.inp(mo, "Volume"))
    return mat, P


# --------------------------------------------------------------------------- recipes (per-frame parameters)

def smooth(e0, e1, x):
    tt = min(max((x - e0) / (e1 - e0), 0.0), 1.0)
    return tt * tt * (3 - 2 * tt)


def puff_params(t):
    """Billowing puff (cut-out 1): cauliflower top, dense core, grows, rises, erodes away."""
    return dict(W=0.4 + 1.1 * t, ox=0.02 * t, oz=-0.25 + 0.30 * t,
                rx=0.62 + 0.30 * smooth(0, 1, t ** 0.7), ry=0.45 + 0.25 * t, rz=0.34 + 0.18 * smooth(0, 1, t ** 0.7),
                core=0.05, lump=1.4, sx=1.0, sy=1.0, sz=1.15, warp=0.9, dscale=3.0 - 0.6 * t, detail=6.0, rough=0.66,
                thr=0.47 + 0.08 * smooth(0.25, 1.0, t), gain=18.0, base=0.03,
                life=smooth(0.0, 0.10, t) * (1 - smooth(0.62, 1.0, t)), density=3.5)


def wisp_params(t):
    """Streaky drifting wisp (cut-outs 2-3): stretched along a rising diagonal, thins as it drifts."""
    return dict(W=0.2 + 0.9 * t, ox=-0.12 + 0.30 * t, oz=-0.10 + 0.20 * t,
                rx=0.72 + 0.22 * t, ry=0.40, rz=0.24 + 0.10 * t, core=0.0, tilt=0.38,
                lump=1.7, sx=0.33, sy=1.2, sz=1.5, warp=1.4, dscale=2.4, detail=7.0, rough=0.62,
                thr=0.46 + 0.08 * smooth(0.3, 1.0, t), gain=8.0, base=0.16,
                life=smooth(0.0, 0.12, t) * (1 - smooth(0.55, 1.0, t)), density=14.0)


def haze_params():
    """Low mist bank (cut-out 4): wide, flat, soft top, dense along the water."""
    return dict(W=0.3, ox=0.0, oz=-0.04, rx=0.84, ry=0.5, rz=0.36, lump=0.8, sx=0.6, sy=1.2, sz=1.5, warp=1.0,
                dscale=2.0, detail=6.0, rough=0.6, thr=0.44, gain=3.5, base=0.25, life=1.0, density=6.0, core=0.1)


# --------------------------------------------------------------------------- spray

def spray_setup(sc, seed=5, n_drops=4200, n_foam=16000):
    """Droplets (points, streak chains) + frothy core volume; returns an update(t) function."""
    rng = np.random.default_rng(seed)
    n = n_drops
    # launch: a crown from a base line, more vertical in the middle; sizes lognormal; some big blobs
    x0 = rng.normal(0, 0.16, n)
    z0 = np.full(n, -0.86) + rng.uniform(0, 0.08, n)
    y0 = rng.normal(0, 0.10, n)
    ang = rng.normal(0, 0.42, n) + 0.9 * np.clip(x0, -0.3, 0.3)
    spd = rng.lognormal(np.log(1.85), 0.35, n)
    vx = spd * np.sin(ang)
    vz = spd * np.cos(ang) * rng.uniform(0.75, 1.0, n)
    vy = rng.normal(0, 0.3, n)
    t_launch = rng.uniform(0.0, 0.35, n) ** 1.5
    radius = np.clip(rng.lognormal(np.log(0.006), 0.55, n), 0.0018, 0.03)
    # aerated white water: many small, slow drops packed into the crown / base mound (reads as foam sheets)
    m = n_foam
    fx0 = rng.normal(0, 0.14, m)
    fz0 = np.full(m, -0.88) + rng.uniform(0, 0.05, m)
    fy0 = rng.normal(0, 0.12, m)
    fang = rng.normal(0, 0.30, m) + 1.1 * np.clip(fx0, -0.35, 0.35) + 0.25
    fsp = rng.lognormal(np.log(1.25), 0.40, m)
    x0 = np.concatenate([x0, fx0]); z0 = np.concatenate([z0, fz0]); y0 = np.concatenate([y0, fy0])
    vx = np.concatenate([vx, fsp * np.sin(fang)]); vz = np.concatenate([vz, fsp * np.cos(fang)])
    vy = np.concatenate([vy, rng.normal(0, 0.2, m)])
    t_launch = np.concatenate([t_launch, rng.uniform(0.0, 0.45, m) ** 1.3])
    radius = np.concatenate([radius, np.clip(rng.lognormal(np.log(0.0045), 0.35, m), 0.0025, 0.012)])
    g = -3.4  # sprite units / s^2 (1 unit = half the cell), lifetime 1 s -> tuned to the cell
    mat = bpy.data.materials.new("M_Water")
    mat.use_nodes = True
    bs = next(nd for nd in mat.node_tree.nodes if nd.type == "BSDF_PRINCIPLED")
    bs.inputs["Base Color"].default_value = (0.95, 0.96, 0.97, 1)
    bs.inputs["Roughness"].default_value = 0.18
    bs.inputs["Specular IOR Level"].default_value = 0.6
    me = bpy.data.meshes.new("Drops")
    ob = bpy.data.objects.new("Drops", me)
    sc.collection.objects.link(ob)
    gn = bpy.data.node_groups.new("DropsGN", "GeometryNodeTree")
    gn.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    gn.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    gi = gn.nodes.new("NodeGroupInput")
    go = gn.nodes.new("NodeGroupOutput")
    m2p = gn.nodes.new("GeometryNodeMeshToPoints")
    na = gn.nodes.new("GeometryNodeInputNamedAttribute")
    na.data_type = "FLOAT"
    na.inputs["Name"].default_value = "prad"
    sm = gn.nodes.new("GeometryNodeSetMaterial")
    sm.inputs["Material"].default_value = mat
    gn.links.new(gi.outputs[0], m2p.inputs["Mesh"])
    gn.links.new(na.outputs["Attribute"], m2p.inputs["Radius"])
    gn.links.new(m2p.outputs[0], sm.inputs["Geometry"])
    gn.links.new(sm.outputs[0], go.inputs[0])
    mod = ob.modifiers.new("GN", "NODES")
    mod.node_group = gn
    # soft spray mist around the base (the sheet's white-water haze, feathered edges)
    mmat, mist_fp = mist_material("SprayMist")
    mc = volume_cube("SprayMist")
    mc.data.materials.append(mmat)
    sheet_rng_seed = seed + 17
    # froth core: a volume cube whose envelope is a rising / collapsing column

    def update(t):
        T = t * 1.0
        age = T - t_launch
        alive = age > 0
        a = np.clip(age, 0, None)
        px = x0 + vx * a
        pz = z0 + vz * a + 0.5 * g * a * a
        py = y0 + vy * a
        vzt = vz + g * a
        # drops die when they fall back under the base, and thin out with age (break-up + evaporation)
        keep = alive & (pz > -0.92) & (np.abs(px) < 0.98) & (pz < 0.98)
        rad = radius * np.clip(1.0 - 0.35 * a, 0.3, 1.0)
        verts, rads = [], []
        idx = np.nonzero(keep)[0]
        for i in idx:
            # streak chain: 1-5 points back along the velocity (reads as a sheet / ligament when fast)
            sp = math.hypot(vx[i], vzt[i])
            k = int(min(4, 1 + sp * 2.0)) if radius[i] < 0.012 else 1
            for j in range(k):
                dt = j * 0.0045
                verts.append((px[i] - vx[i] * dt, py[i] - vy[i] * dt, pz[i] - vzt[i] * dt))
                rads.append(rad[i] * (1 - 0.12 * j))
        # water SHEETS (the sheet's crown / column): continuous walls sampled densely with small overlapping
        # points so they read as connected white water, not beads. Crown wall early, a central column jet in
        # the middle of the life, both collapsing into the droplets above.
        sv, sr = sheet_points(T, sheet_rng_seed)
        verts.extend(sv)
        rads.extend(sr)
        mist_fp.set(W=0.4 + 1.2 * T, ox=0.0, oz=-0.80 + 0.25 * smooth(0, 0.6, T), rx=0.35 + 0.35 * T, ry=0.3,
                    rz=0.14 + 0.30 * smooth(0.05, 0.6, T), core=0.1, tilt=0.0, lump=1.0, sx=1.2, sy=1.2, sz=1.0,
                    warp=1.0, dscale=2.6, detail=6.0, rough=0.6, thr=0.47 + 0.08 * smooth(0.4, 1, T), gain=5.0,
                    base=0.15, life=smooth(0.02, 0.2, T) * (1 - smooth(0.6, 1.0, T)), density=6.0)
        me.clear_geometry()
        me.from_pydata(verts, [], [])
        attr = me.attributes.new("prad", "FLOAT", "POINT")
        attr.data.foreach_set("value", np.array(rads, dtype=np.float32))
        me.update()
        return len(verts)

    return update


def sheet_points(T, seed):
    """Crown wall + central column jet as dense point sheets at normalised time T (0..1)."""
    rng = np.random.default_rng(seed)
    base = -0.86
    pts, rad = [], []
    # crown: wall of angle theta, rising then collapsing, radius grows, rim height varies per angle (fingers)
    grow = smooth(0.0, 0.22, T) * (1 - smooth(0.30, 0.62, T))
    if grow > 0.01:
        nth = 220
        th = np.linspace(0, 2 * np.pi, nth, endpoint=False) + rng.uniform(0, 0.03, nth)
        hmax = 0.42 * grow * (0.55 + 0.45 * np.abs(np.sin(3 * th + 1.1) * np.cos(5 * th + 0.3)))             * (1 + 0.35 * np.cos(th - 0.6))  # higher on one side (the sheet's leaning crown)
        r0 = 0.10 + 0.30 * smooth(0.0, 0.6, T)
        for k in range(nth):
            ns = max(2, int(hmax[k] / 0.008))
            s_ = np.linspace(0, hmax[k], ns) + rng.uniform(0, 0.006, ns)
            r = r0 + 0.35 * s_ + rng.normal(0, 0.006, ns)
            x = r * np.cos(th[k]) * 1.25
            y = r * np.sin(th[k]) * 0.8
            z = base + s_ + 0.04 * np.sin(8 * th[k]) * s_
            thin = 1 - 0.6 * (s_ / max(hmax[k], 1e-3))
            for i in range(ns):
                if rng.random() < 0.12 * (s_[i] / max(hmax[k], 1e-3)):
                    continue  # holes near the rim: the sheet tears
                pts.append((x[i], y[i], z[i]))
                rad.append(0.0075 * thin[i] + 0.002)
    # column jet: a tall ragged cone in the middle of the life
    jet = smooth(0.18, 0.40, T) * (1 - smooth(0.50, 0.85, T))
    if jet > 0.01:
        h = 0.95 * jet
        m = int(5000 * jet)
        s_ = rng.uniform(0, 1, m) ** 0.8 * h
        w = 0.05 + 0.22 * (s_ / max(h, 1e-3)) + 0.1 * (1 - s_ / max(h, 1e-3))
        a = rng.uniform(0, 2 * np.pi, m)
        rr = w * np.sqrt(rng.uniform(0, 1, m))
        for i in range(m):
            pts.append((rr[i] * np.cos(a[i]) + 0.05, rr[i] * np.sin(a[i]) * 0.6, base + s_[i]))
            rad.append(float(rng.uniform(0.004, 0.009)))
    return pts, rad


# --------------------------------------------------------------------------- render + pack

def read_exr(path):
    import OpenImageIO as oiio
    inp = oiio.ImageInput.open(str(path))
    layers = {}
    k = 0
    while inp.seek_subimage(k, 0):
        spec = inp.spec()
        arr = np.array(inp.read_image(k, 0, 0, spec.nchannels, oiio.FLOAT)).reshape(spec.height, spec.width,
                                                                                    spec.nchannels)
        for ci, cn in enumerate(spec.channelnames):
            layers[cn.split(".", 1)[1] if "." in cn else cn] = arr[..., ci]
        k += 1
    inp.close()
    return layers


def blur3(a):
    """3x3 binomial blur: removes the residual path-tracing grain of the (undenoised) light-group passes."""
    k = np.array([1, 2, 1], np.float32) / 4
    a = sum(np.roll(a, d, axis=0) * w for d, w in zip((-1, 0, 1), k))
    return sum(np.roll(a, d, axis=1) * w for d, w in zip((-1, 0, 1), k))


def frame_passes(layers):
    alpha = layers["Combined.A"]
    lg = {}
    for name in LIGHTS:
        key = [k for k in layers if k.startswith(f"Combined_{name}.") and k.endswith(".R")]
        base = key[0][:-2]
        lg[name] = blur3((layers[base + ".R"] + layers[base + ".G"] + layers[base + ".B"]) / 3.0)
    return alpha, lg


def render_sequence(sc, name, n_frames, setter, a, extra=None):
    src = fx.SRC_TEX / name
    src.mkdir(parents=True, exist_ok=True)
    f0, f1 = (0, n_frames - 1)
    if a.frames:
        f0, f1 = (int(v) for v in a.frames.split(","))
    stats = []
    for f in range(f0, f1 + 1):
        t = f / (n_frames - 1)
        info = setter(t)
        sc.render.filepath = str(src / f"{name}_{f:03d}.exr")
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        stats.append({"frame": f, "sec": round(time.time() - t0, 2), "info": info})
        if a.preview:
            alpha, lg = frame_passes(read_exr(src / f"{name}_{f:03d}.exr"))
            am = np.maximum(alpha, 1e-3)
            raw = (0.55 * lg["PZ"] + 0.35 * lg["NY"] + 0.25 * lg["PY"]) / am
            ref = float(np.percentile(raw[alpha > 0.05], 99)) if (alpha > 0.05).any() else 1.0
            lum = np.clip(raw / ref, 0, 1) * alpha
            print(f"ALPHA {name} {f} max {alpha.max():.3f} mean {alpha.mean():.4f} p90in {np.percentile(alpha[alpha>0.01],90) if (alpha>0.01).any() else 0:.3f}")
            rgb = np.stack([lum * 1.0, lum * 0.8, lum * 0.66], -1)  # warm tint only for viewing
            fx.save_png(np.clip(rgb, 0, 1), fx.WORK / f"renders/flipbooks/preview/{name}_{f:03d}.png")
        print(f"FRAME {name} {f} {stats[-1]['sec']}s {info}")
    return stats


UNPRE_FLOOR = 0.5  # un-premultiply the lighting only down to this alpha: thinner edges keep their (dim) radiance


def pack(name, n_frames, grid, cell, extra_meta=None):
    """Pack 64 frame EXRs into the SixWayP / SixWayN atlases.

    The light-group passes are coverage-weighted radiance. They are divided by max(alpha, UNPRE_FLOOR) so the dense
    parts carry a per-pixel shading value while the thin feathered edges stay dim (a scattering medium's thin edge
    scatters little light; un-premultiplying it fully made white halos). One normalisation factor per flipbook: the
    99.5th percentile of the six passes where alpha > UNPRE_FLOOR -> 1.0.
    """
    src = fx.SRC_TEX / name
    size = grid * cell
    P = np.zeros((size, size, 4), np.float32)
    N = np.zeros((size, size, 4), np.float32)
    frames = []
    for f in range(n_frames):
        alpha, lg = frame_passes(read_exr(src / f"{name}_{f:03d}.exr"))
        am = np.maximum(alpha, UNPRE_FLOOR)
        frames.append((alpha, {k: v / am for k, v in lg.items()}))
    vals = np.concatenate([np.concatenate([lg[k][a > UNPRE_FLOOR] for k in LIGHTS]) for a, lg in frames])
    norm = float(np.percentile(vals, 99.5)) if len(vals) else 1.0
    cover = []
    for f, (alpha, lg) in enumerate(frames):
        r, c = divmod(f, grid)
        ys, xs = slice(r * cell, (r + 1) * cell), slice(c * cell, (c + 1) * cell)
        P[ys, xs, :3] = np.clip(np.stack([lg["PX"], lg["PZ"], lg["PY"]], -1) / norm, 0, 1)
        N[ys, xs, :3] = np.clip(np.stack([lg["NX"], lg["NZ"], lg["NY"]], -1) / norm, 0, 1)
        P[ys, xs, 3] = np.clip(alpha, 0, 1)
        N[ys, xs, 3] = np.clip(alpha, 0, 1)
        cover.append(round(float(alpha.mean()), 4))
    # EXR/OIIO rows are top-down; PNG rows top-down: flipbook frame 0 is the top-left cell
    fx.save_png(P, fx.TEX / f"T_DKF_{name}_SixWayP.png")
    fx.save_png(N, fx.TEX / f"T_DKF_{name}_SixWayN.png")
    prev = np.clip(0.55 * P[..., 1:2] + 0.35 * N[..., 2:3] + 0.25 * P[..., 2:3], 0, 1)
    fx.save_png(np.repeat(prev, 3, -1) * P[..., 3:4], fx.WORK / f"renders/flipbooks/{name}_preview_neutral.png")
    return {"norm_factor": norm, "unpremultiply_floor": UNPRE_FLOOR, "coverage_per_frame": cover, "size": size,
            "grid": grid, "cell": cell, **(extra_meta or {})}


def pack_haze(res=(2048, 1024)):
    """T_DKF_Haze_M: R opacity, G top-lit, B back-lit (same floored un-premultiply as the flipbooks)."""
    alpha, lg = frame_passes(read_exr(fx.SRC_TEX / "Haze" / "Haze.exr"))
    am = np.maximum(alpha, UNPRE_FLOOR)
    g = {k: v / am for k, v in lg.items()}
    vals = np.concatenate([g[k][alpha > UNPRE_FLOOR] for k in LIGHTS])
    norm = float(np.percentile(vals, 99.5))
    M = np.stack([np.clip(alpha, 0, 1), np.clip(g["PZ"] / norm, 0, 1), np.clip(g["PY"] / norm, 0, 1)], -1)
    fx.save_png(M, fx.TEX / "T_DKF_Haze_M.png")
    return {"size": list(res), "norm_factor": norm, "unpremultiply_floor": UNPRE_FLOOR,
            "coverage": round(float(alpha.mean()), 4)}


def main():
    a = args()
    only = a.only.split(",")
    n_frames = a.grid * a.grid
    meta = {}
    for name in only:
        if name in ("puff", "wisp"):
            sc = base_scene(a.cell, a.samples)
            cube = volume_cube("Vol")
            mat, P = mist_material(name)
            cube.data.materials.append(mat)
            fn = puff_params if name == "puff" else wisp_params
            label = "MistPuff" if name == "puff" else "MistWisp"

            def setter(t, P=P, fn=fn):
                P.set(**fn(t))
                return None

            stats = render_sequence(sc, label, n_frames, setter, a)
            if not a.preview:
                meta[label] = pack(label, n_frames, a.grid, a.cell, {"render_sec": sum(s["sec"] for s in stats)})
        elif name == "spray":
            sc = base_scene(a.cell, a.samples)
            upd = spray_setup(sc)
            stats = render_sequence(sc, "SprayBurst", n_frames, upd, a)
            if not a.preview:
                meta["SprayBurst"] = pack("SprayBurst", n_frames, a.grid, a.cell,
                                          {"render_sec": sum(s["sec"] for s in stats)})
        elif name == "haze":
            res = (2 * a.cell * 2, a.cell * 2)  # 2048 x 1024 at cell 512
            sc = base_scene(a.cell, a.samples, res=res)
            sc.camera.data.ortho_scale = 2.0
            cube = volume_cube("Vol", size=(1.0, 0.6, 0.5))
            mat, P = mist_material("haze")
            cube.data.materials.append(mat)
            P.set(**haze_params())
            src = fx.SRC_TEX / "Haze"
            src.mkdir(parents=True, exist_ok=True)
            sc.render.filepath = str(src / "Haze.exr")
            bpy.ops.render.render(write_still=True)
            meta["Haze"] = pack_haze(res)
    if meta:
        path = fx.WORK / "json/flipbooks.json"
        old = fx.load_json(path) if path.exists() else {}
        old.update(meta)
        fx.write_json(path, old)
    print("DONE", list(meta))


if __name__ == "__main__":
    main()
