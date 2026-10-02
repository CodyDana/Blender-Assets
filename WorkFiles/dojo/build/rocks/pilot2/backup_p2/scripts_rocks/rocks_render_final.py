"""Final pilot renders (study 6.4), called from rocks_render.py (modes sheet / close / river). Cycles, denoised,
headless. The shipped objects come from Assets/Dojo/DojoRocks.blend with their preview materials (= the Unreal MI
plan).

sheet   per rock: the sheet's row layout pieces -- main view (perspective, ~8 deg up), top and side views -- on the
        sheet's light-grey studio (film transparent + shadow catcher, composited on sRGB 186 grey later), the 1.8 m
        figure beside the main view; plus an alpha pass for the silhouette measure.
close   five close-ups framed like the sheet's: granite grain, a fracture edge, moss on rock, the wet-to-dry line at
        water, lichen. Spots are found by reading the baked mask map at ray hits (not picked by eye).
river   a small sunset riverbank test: the three rocks in a stand-in stream bed with stand-in cobbles (not shipped),
        the dojo's low western sun (~9 deg).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

import bpy
from mathutils import Vector

import rocks_render as R
from rocks_plans import PLANS

OUT = R.PILOT


def load_rocks(names):
    want = [PLANS[n]["prefix"] for n in names]
    objs = R.append_from_blend(want)
    return {n: objs[PLANS[n]["prefix"]] for n in names}


def holdout_below(z=-0.003):
    ob = R.holdout_ground()
    ob.location.z = z - 5.0
    for a in ("visible_shadow", "visible_diffuse", "visible_glossy", "visible_transmission",
              "visible_volume_scatter"):
        setattr(ob, a, False)
    return ob


def place_only(objs, keep):
    for n, ob in objs.items():
        vis = n == keep
        ob.hide_render = not vis
        for c in ob.children:
            c.hide_render = True


def persp_cam(target, dist, azim, elev, lens):
    a, e = math.radians(azim), math.radians(elev)
    d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    loc = Vector(target) + d * dist
    return R.camera("CamP", tuple(loc), tuple(target), lens=lens)


def fit_dist(extent_w, extent_h, lens, res, margin=1.18):
    sw = 36.0
    fov_w = 2 * math.atan(sw / (2 * lens))
    fov_h = 2 * math.atan(sw * res[1] / res[0] / (2 * lens))
    return max(extent_w * margin / (2 * math.tan(fov_w / 2)), extent_h * margin / (2 * math.tan(fov_h / 2)))


# ----------------------------------------------------------------------------------------------- sheet
def mode_sheet(rocks, src):
    out = OUT / "sheet"
    meta = {}
    for r in rocks:
        sc = R.reset()
        R.studio(key=260.0)
        objs = load_rocks([r])
        ob = objs[r]
        holdout_below()
        lo, hi = R.bbox_of(ob)
        L, D, H = hi[0] - lo[0], hi[1] - lo[1], hi[2]
        sc.cycles.samples = 192
        # main view with the figure (the sheet puts the figure left of the rock, in its plane)
        fig = R.figure(lo[0] - 0.75, 0.0)
        res = (1600, 1000)
        sc.render.resolution_x, sc.render.resolution_y = res
        lens = 85.0
        w = (hi[0] - (lo[0] - 1.05))
        cx = (hi[0] + lo[0] - 1.05) / 2
        dist = fit_dist(w, max(H, 1.85), lens, res, 1.12)
        persp_cam((cx, 0.0, max(H, 1.8) * 0.47), dist, 0.0, 8.0, lens)
        R.render(out / f"{r}_main.png", res=res)
        # main view without the figure (the measured silhouette / value regions)
        fig.hide_render = True
        dist2 = fit_dist(L, H, lens, (1400, 1000), 1.12)
        persp_cam(((lo[0] + hi[0]) / 2, 0.0, H * 0.45), dist2, 0.0, 8.0, lens)
        R.render(out / f"{r}_mainonly.png", res=(1400, 1000))
        # top (oblique, as the sheet's smaller views) and side (end) views
        persp_cam(((lo[0] + hi[0]) / 2, 0.0, H * 0.3), fit_dist(L, D + H * 0.6, lens, (1200, 900), 1.15),
                  0.0, 50.0, lens)
        R.render(out / f"{r}_top.png", res=(1200, 900))
        persp_cam((0.0, (lo[1] + hi[1]) / 2, H * 0.45), fit_dist(D, H, lens, (900, 1000), 1.15), 90.0, 8.0, lens)
        R.render(out / f"{r}_side.png", res=(900, 1000))
        meta[r] = {"bbox": [list(map(float, lo)), list(map(float, hi))], "lens": lens, "elev_main": 8.0}
    (out / "sheet_meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")


# ----------------------------------------------------------------------------------------------- close-ups
def _mask_sampler(ob):
    """Sample the object's baked mask map (M) at a face + barycentric point -> (moss, lichen, wet, stain)."""
    mat = ob.data.materials[0]
    img = next(n.image for n in mat.node_tree.nodes if n.type == "TEX_IMAGE" and n.image
               and n.image.name.endswith("_M.png"))
    w, h = img.size
    px = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)
    uvl = ob.data.uv_layers["UVMap"].data
    me = ob.data

    def sample(face_index, p):
        poly = me.polygons[face_index]
        vs = [me.vertices[i].co for i in poly.vertices]
        uvs = [uvl[li].uv for li in poly.loop_indices]
        # barycentric on the triangle
        a, b, c = vs[0], vs[1], vs[2]
        v0, v1, v2 = b - a, c - a, p - a
        d00, d01, d11 = v0.dot(v0), v0.dot(v1), v1.dot(v1)
        d20, d21 = v2.dot(v0), v2.dot(v1)
        den = max(d00 * d11 - d01 * d01, 1e-12)
        v = (d11 * d20 - d01 * d21) / den
        wv = (d00 * d21 - d01 * d20) / den
        u = 1 - v - wv
        uv = uvs[0] * u + uvs[1] * v + uvs[2] * wv
        x = min(max(int(uv[0] * w), 0), w - 1)
        y = min(max(int(uv[1] * h), 0), h - 1)
        return px[y, x]
    return sample


def find_spot(ob, score, rng, n=2500, zmin=0.1):
    """Random surface hits from outside, scored by score(mask, normal, point); returns the best (point, normal)."""
    me = ob.data
    sample = _mask_sampler(ob)
    deps = bpy.context.evaluated_depsgraph_get()
    lo, hi = R.bbox_of(ob)
    best, bp = -1e9, None
    for _ in range(n):
        d = Vector(rng.normal(0, 1, 3))
        d.normalize()
        tgt = Vector((rng.uniform(lo[0], hi[0]), rng.uniform(lo[1], hi[1]), rng.uniform(max(lo[2], zmin), hi[2])))
        o = tgt - d * 8.0
        hit, loc, nrm, fi, hob, _ = bpy.context.scene.ray_cast(deps, o, d)
        if not hit or hob is None or hob.name != ob.name or loc.z < zmin:
            continue
        if me.polygons[fi].material_index != 0:
            continue
        m = sample(fi, loc)
        s = score(m, nrm, loc)
        if s > best:
            best, bp = s, (loc.copy(), nrm.copy())
    return bp


def close_cam(p, n, width, tilt=0.0, up_bias=0.25, res=(1000, 1400)):
    n = Vector(n).normalized()
    d = (n + Vector((0, 0, up_bias))).normalized()
    if tilt:
        side = n.cross(Vector((0, 0, 1)))
        if side.length > 1e-6:
            side.normalize()
            d = (d + side * math.tan(math.radians(tilt))).normalized()
    lens = 100.0
    dist = width / (36.0 * res[0] / max(res) / lens) if res[0] < res[1] else width / (36.0 / lens)
    dist = width * lens / 36.0 * (max(res) / res[0])
    loc = Vector(p) + d * dist
    return R.camera("CamC", tuple(loc), tuple(p), lens=lens)


def mode_close(rocks, src):
    out = OUT / "close"
    rng = np.random.default_rng(31)
    sc = R.reset()
    names = list(PLANS)
    objs = load_rocks(names)
    # the sheet's close-ups: soft daylight from the upper left
    R.world_colour((0.62, 0.64, 0.68), 0.9)
    R.sun("Key", 48.0, 300.0, 3.2, (1.0, 0.97, 0.92), angle_deg=6.0)
    sc.cycles.samples = 256
    res = (1000, 1400)
    meta = {}
    shots = [
        # (name, rock, score fn, field width m, tilt deg, up bias)
        ("grain", "CliffChunk", lambda m, n, p: -3 * m[0] - 2 * m[1] - m[3] + (1 - abs(n.z)) * 1.5
         - abs(p.z - 1.0) * 0.3, 0.13, 0.0, 0.0),
        ("fracture", "CliffChunk", lambda m, n, p: (0.3 < n.z < 0.8) * 1.0 + m[0] * 0.6 - m[2]
         - abs(p.z - 1.3) * 0.3, 0.42, 35.0, 0.35),
        ("moss", "RiverLong", lambda m, n, p: m[0] * 2 + n.z, 0.40, 0.0, 0.6),
        ("lichen", "CliffChunk", lambda m, n, p: m[1] * 3 - m[0] * 2 + (1 - abs(n.z)), 0.20, 0.0, 0.1),
    ]
    for name, r, score, width, tilt, ub in shots:
        place_only(objs, r)
        spot = find_spot(objs[r], score, rng)
        if spot is None:
            continue
        p, n = spot
        close_cam(p, n, width, tilt, ub, res)
        R.render(out / f"close_{name}.png", res=res)
        meta[name] = {"rock": r, "point": list(p), "normal": list(n), "width_m": width}
    # wet-to-dry line: RiverRound at a water plane set just under its baked wet line
    r = "RiverRound"
    place_only(objs, r)
    ob = objs[r]
    lo, hi = R.bbox_of(ob)
    zw = PLANS[r]["wet"]["h"] * hi[2] - 0.16
    water = water_plane(zw, 6.0)
    deps = bpy.context.evaluated_depsgraph_get()
    o = Vector((0.15, -6.0, zw + 0.16))
    hit, loc, nrm, fi, hob, _ = sc.ray_cast(deps, o, Vector((0, 1, 0)))
    if hit:
        cam = close_cam(loc, nrm, 0.5, 15.0, -0.05, res)
        R.render(out / "close_wetline.png", res=res)
        meta["wetline"] = {"rock": r, "point": list(loc), "water_z": zw, "width_m": 0.5}
    bpy.data.objects.remove(water)
    (out / "close_meta.json").write_text(json.dumps(meta, indent=1, default=float), encoding="utf-8")


def water_plane(z, size, colour=(0.25, 0.55, 0.52)):
    me = bpy.data.meshes.new("Water")
    s = size
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    ob = bpy.data.objects.new("Water", me)
    bpy.context.scene.collection.objects.link(ob)
    ob.location.z = z
    m = bpy.data.materials.new("StandInWater")
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*colour, 1)
    b.inputs["Roughness"].default_value = 0.04
    b.inputs["IOR"].default_value = 1.33
    b.inputs["Transmission Weight"].default_value = 0.92
    nt = m.node_tree
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 9.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.08
    nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    vol = nt.nodes.new("ShaderNodeVolumeAbsorption")
    vol.inputs["Color"].default_value = (0.35, 0.75, 0.70, 1)
    vol.inputs["Density"].default_value = 1.6
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    nt.links.new(vol.outputs[0], out.inputs["Volume"])
    me.materials.append(m)
    # give the plane thickness so the absorption volume is closed
    sol = ob.modifiers.new("solid", "SOLIDIFY")
    sol.thickness = 1.5
    sol.offset = -1.0
    return ob


# ----------------------------------------------------------------------------------------------- riverbank
def _granite_like(name, v):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 60.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (v * 0.55, v * 0.53, v * 0.50, 1)
    ramp.color_ramp.elements[1].color = (v * 1.1, v * 1.07, v * 1.02, 1)
    nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.6
    return m


def stand_in_cobbles(n, region, zfun, rng, mat):
    """Stand-in cobbles (NOT shipped; the cobble set is a later stage): flattened noisy spheres."""
    obs = []
    for i in range(n):
        x = rng.uniform(*region[0])
        y = rng.uniform(*region[1])
        r = float(np.exp(rng.uniform(np.log(0.05), np.log(0.22))))
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=r, location=(x, y, zfun(x, y) + r * 0.25))
        ob = bpy.context.active_object
        ob.scale = (rng.uniform(0.9, 1.4), rng.uniform(0.8, 1.2), rng.uniform(0.45, 0.75))
        ob.rotation_euler = (0, 0, rng.uniform(0, 6.28))
        d = ob.modifiers.new("d", "DISPLACE")
        tx = bpy.data.textures.new(f"cn{i}", "CLOUDS")
        tx.noise_scale = 0.6
        d.texture = tx
        d.strength = r * 0.25
        ob.data.materials.append(mat)
        for p in ob.data.polygons:
            p.use_smooth = True
        obs.append(ob)
    return obs


def mode_river(rocks, src):
    sc = R.reset()
    objs = load_rocks(list(PLANS))
    rng = np.random.default_rng(77)
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "AgX"
    sc.cycles.samples = 384
    # sunset sky: warm horizon, dusky zenith (the dojo's sunset: sun ~9 deg from the west)
    w = sc.world
    nt = w.node_tree
    bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (1.0, 0.55, 0.28, 1)
    ramp.color_ramp.elements[1].position = 0.45
    ramp.color_ramp.elements[1].color = (0.30, 0.34, 0.55, 1)
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.55
    R.sun("Sunset", 9.0, 270.0, 4.5, (1.0, 0.58, 0.32), angle_deg=1.2)
    # stand-in stream bed: a bank mesh (soil / gravel), a stream channel, water
    def zf(x, y):
        return 0.10 + 0.05 * math.sin(0.7 * x) + (0.0 if y < 1.2 else 0.25 * (y - 1.2)) - \
            (0.30 if -1.6 < y < 1.0 else 0.0) * (1.0 - min(1.0, abs(y + 0.3) / 1.3) ** 3)
    n = 120
    xs = np.linspace(-9, 9, n)
    ys = np.linspace(-7, 9, n)
    Vg = [(x, y, zf(x, y)) for y in ys for x in xs]
    Fg = [(j * n + i, j * n + i + 1, (j + 1) * n + i + 1, (j + 1) * n + i) for j in range(n - 1) for i in range(n - 1)]
    me = bpy.data.meshes.new("StandInBank")
    me.from_pydata(Vg, [], Fg)
    for p in me.polygons:
        p.use_smooth = True
    bank = bpy.data.objects.new("StandInBank", me)
    sc.collection.objects.link(bank)
    soil = _granite_like("StandInGravel", 0.16)
    soil.node_tree.nodes["Noise Texture"].inputs["Scale"].default_value = 140.0
    me.materials.append(soil)
    water = water_plane(0.02, 9.0)
    water.scale = (1.0, 0.19, 1.0)
    water.location.y = -0.3
    # rocks: the river boulders in the stream (sunk 15-30 %, study 3.10), the cliff chunk on the far bank
    rr, rl, cc = objs["RiverRound"], objs["RiverLong"], objs["CliffChunk"]
    rr.location = (-0.9, -0.6, -0.22)
    rr.rotation_euler = (0, 0, math.radians(-18))
    rl.location = (2.0, 0.2, -0.20)
    rl.rotation_euler = (0, 0, math.radians(8))
    cc.location = (-1.2, 3.4, 0.05)
    cc.rotation_euler = (0, 0, math.radians(12))
    for ob in (rr, rl, cc):
        ob.hide_render = False
        for c in ob.children:
            c.hide_render = True
    cob = _granite_like("StandInCobble", 0.30)
    stand_in_cobbles(70, ((-5, 5), (-1.9, 1.1)), zf, rng, cob)
    stand_in_cobbles(40, ((-5, 5), (1.0, 2.6)), zf, rng, cob)
    sc.render.resolution_x, sc.render.resolution_y = 1800, 1000
    persp_cam((0.2, 0.9, 0.7), 8.6, 20.0, 14.0, 35.0)
    R.render(OUT / "river" / "riverbank_sunset.png", res=(1800, 1000))
    persp_cam((-0.6, 0.2, 0.5), 5.0, -35.0, 10.0, 50.0)
    R.render(OUT / "river" / "riverbank_sunset_close.png", res=(1800, 1000))
