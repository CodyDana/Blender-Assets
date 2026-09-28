"""Snow Flower v4 look: the high-poly bake materials (procedural), the painted blade pattern, and the
game materials used by every render (image textures only: BC / ORM / N)."""
from __future__ import annotations

import math

import numpy as np

import sfv4_spec as S

# linear base colour, roughness, metallic per high material slot (sfv4_rev3 indices)
HIGH_MATERIALS = [
    # name,        base colour (linear),   rough, metal, noise amp, noise scale (1/mm)
    ("Blade", None, None, 1.0, 0.0, 0.0),
    # look-match R1: polished (sheet: near-chrome silver with dark antiquing in the recesses), not satin
    ("Silver", (0.60, 0.60, 0.62), 0.20, 1.0, 0.04, 0.9),
    ("Inlay", (0.86, 0.86, 0.88), 0.28, 1.0, 0.03, 1.3),
    ("Recess", (0.016, 0.018, 0.024), 0.34, 1.0, 0.08, 0.8),
    ("BlackSteel", (0.034, 0.039, 0.050), 0.33, 1.0, 0.30, 0.25),
    ("BranchSteel", (0.66, 0.66, 0.68), 0.22, 1.0, 0.06, 1.1),
    ("Cord", (0.009, 0.009, 0.011), 0.72, 0.0, 0.30, 1.2),   # final pass: noise 2.5 -> 1.2 per mm (less shimmer)
    ("Core", (0.011, 0.011, 0.013), 0.70, 0.0, 0.10, 1.0),
    # look-match R1: the blade relief blossoms read PEARL-white on the sheet's blade crop (a half-metal white)
    ("Pearl", (0.86, 0.86, 0.88), 0.30, 0.45, 0.03, 1.3),
]

PATTERN_U = (-62.0, 62.0)          # mm (front u>0 = s*w, back u<0)
PATTERN_V = (S.Z_BLADE_ROOT - 4.0, S.Z_TIP + 4.0)
PATTERN_PPMM = 4.0


# ====================================================================== numpy noise

def value_noise(shape, cells, rng):
    """Smooth value noise: random lattice (cells) bicubic-ish upsampled to ``shape``."""
    h, w = shape
    ch, cw = max(2, int(cells[0])), max(2, int(cells[1]))
    g = rng.random((ch + 3, cw + 3))
    y = np.linspace(1, ch + 1, h)
    x = np.linspace(1, cw + 1, w)
    yi = np.floor(y).astype(int)
    xi = np.floor(x).astype(int)
    fy = y - yi
    fx = x - xi
    sy = fy * fy * (3 - 2 * fy)
    sx = fx * fx * (3 - 2 * fx)
    a = g[yi][:, xi]
    b = g[yi][:, xi + 1]
    c = g[yi + 1][:, xi]
    d = g[yi + 1][:, xi + 1]
    top = a + (b - a) * sx[None, :]
    bot = c + (d - c) * sx[None, :]
    return top + (bot - top) * sy[:, None]


def fbm(shape, cells, octaves, rng, gain=0.5):
    out = np.zeros(shape)
    amp = 1.0
    tot = 0.0
    for o in range(octaves):
        out += amp * value_noise(shape, (cells[0] * 2 ** o, cells[1] * 2 ** o), rng)
        tot += amp
        amp *= gain
    return out / tot


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


# ====================================================================== blade pattern

def paint_blade_pattern(ribbon_path_front, ribbon_path_back, seed=4417):
    """Paint base colour (linear RGB) and roughness over the blade's (u mm, z mm) domain.
    Returns (bc HxWx3, rough HxW, meta). Row 0 = PATTERN_V[0].

    LOOK-MATCH R1: colours matched to the sheet's front view sampled per region (spine band, channel, edge) in three
    height bands: the polished bands read BLUE-white and streaky (sheet std ~0.15), the channel blue-black in the upper
    blade lightening to a mottled blue-grey below, the edge bevel brightening toward the tip, and the bold wavy RIBBON
    (sfv4_blade.ribbon: bright edges, grey interior) from z ~330 to the tip.  ``ribbon_path_*`` are kept for the call
    signature (the old ribbon followed the relief trunk)."""
    import sfv4_blade as BL
    rng = np.random.default_rng(seed)
    W = int((PATTERN_U[1] - PATTERN_U[0]) * PATTERN_PPMM)
    H = int((PATTERN_V[1] - PATTERN_V[0]) * PATTERN_PPMM)
    u = PATTERN_U[0] + (np.arange(W) + 0.5) / PATTERN_PPMM
    z = PATTERN_V[0] + (np.arange(H) + 0.5) / PATTERN_PPMM
    UU, ZZ = np.meshgrid(u, z)
    w = S.width(ZZ)
    w = np.maximum(w, 0.5)
    s = np.abs(UU) / w
    t = S.blade_t(ZZ)
    cloud = fbm((H, W), (H / 90.0, W / 40.0), 5, rng)
    wisp = fbm((H, W), (H / 30.0, W / 18.0), 4, rng)
    streak = fbm((H, W), (H / 220.0, W / 1.6), 3, rng)          # lengthwise polish streaks
    speck = fbm((H, W), (H / 4.0, W / 4.0), 2, rng)
    ch0, ch1 = S.CHANNEL_S
    in_channel = smoothstep(ch0 - 0.006, ch0 + 0.012, s) * (1 - smoothstep(ch1 - 0.012, ch1 + 0.006, s))
    spine = 1 - smoothstep(0.010, 0.022, s)
    low = smoothstep(0.45, 0.75, t)                              # 0 upper blade .. 1 lower blade
    # polished steel: blue-white, streaky; the spine band darkens in the lower blade, the edge bevel brightens
    pol = 0.50 + 0.16 * (streak - 0.5) + 0.12 * (cloud - 0.5) + 0.04 * (speck - 0.5)
    tint = np.array([0.90, 0.96, 1.10])
    pol_rgb = pol[..., None] * tint
    spine_side = 1 - smoothstep(0.28, 0.40, s)
    edge_side = smoothstep(0.76, 0.84, s)
    pol_rgb *= (1 - 0.45 * low * spine_side)[..., None]
    pol_rgb *= (0.86 + 0.26 * low * edge_side)[..., None]
    pol_r = 0.22 + 0.07 * (streak - 0.5) + 0.05 * (speck - 0.5)
    # channel: blue-black with pale wisps, lightening to mottled blue-grey below
    m = cloud
    wi = smoothstep(0.64, 0.82, wisp) * 0.8
    base = np.stack([0.026 + 0.048 * m, 0.032 + 0.056 * m, 0.052 + 0.078 * m], -1)
    wis_c = np.array([0.15, 0.16, 0.20])
    ch_rgb = base * (1 - wi[..., None]) + wis_c * wi[..., None]
    lowc = np.stack([0.10 + 0.10 * m, 0.11 + 0.11 * m, 0.135 + 0.13 * m], -1)
    ch_rgb = ch_rgb * (1 - 0.7 * low[..., None]) + lowc * (0.7 * low[..., None])
    ch_r = 0.32 + 0.08 * (m - 0.5) - 0.08 * wi
    # the wavy ribbon (front: u > 0 is side -1)
    rib_in = np.zeros((H, W))
    rib_edge = np.zeros((H, W))
    for side in (-1, 1):
        s_c, hw, fade = BL.ribbon(z, side)
        onside = (UU > 0) if side < 0 else (UU < 0)
        d = np.abs(s - s_c[:, None]) / np.maximum(hw[:, None], 1e-4)
        inner = (1 - smoothstep(0.80, 1.05, d)) * fade[:, None]
        edge = np.exp(-((d - 0.86) / 0.13) ** 2) * fade[:, None]
        rib_in = np.maximum(rib_in, inner * onside)
        rib_edge = np.maximum(rib_edge, edge * onside)
    rib_c = np.array([0.42, 0.44, 0.50]) + 0.08 * (cloud[..., None] - 0.5)
    ch_rgb = ch_rgb * (1 - rib_in[..., None]) + rib_c * rib_in[..., None]
    ch_rgb = ch_rgb * (1 - rib_edge[..., None]) + np.array([0.66, 0.69, 0.76]) * rib_edge[..., None]
    ch_r = ch_r * (1 - rib_in) + 0.16 * rib_in
    # tip: the polish takes over the last 6 %
    tipmix = smoothstep(0.93, 0.99, t)
    in_ch = in_channel * (1 - tipmix)
    bc = pol_rgb * (1 - in_ch[..., None]) + ch_rgb * in_ch[..., None]
    rough = pol_r * (1 - in_ch) + ch_r * in_ch
    bc = bc * (1 - 0.18 * spine[..., None])
    rough = rough + 0.08 * spine
    bc = np.clip(bc, 0.0, 1.0)
    rough = np.clip(rough, 0.05, 0.9)
    meta = {"W": W, "H": H, "ppmm": PATTERN_PPMM, "u_range": PATTERN_U, "v_range": PATTERN_V}
    return bc, rough, meta


# ====================================================================== Blender materials

def _principled(nt):
    return next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")


def make_high_materials(pattern_bc_img=None, pattern_rough_img=None, metal_bump=None):
    """Create the 8 high-poly materials. Each carries three named nodes 'ch_bc' (RGB), 'ch_rough',
    'ch_metal' (values) feeding a Principled BSDF, plus an Emission node 'bake_emit' used by
    set_bake_channel()."""
    import bpy
    mats = []
    for idx, (name, bc, rough, metal, amp, scale) in enumerate(HIGH_MATERIALS):
        m = bpy.data.materials.new(f"SF4H_{name}")
        m.use_nodes = True
        nt = m.node_tree
        bs = _principled(nt)
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        if name == "Blade":
            uvn = nt.nodes.new("ShaderNodeUVMap")
            uvn.uv_map = "UV0"
            mp = nt.nodes.new("ShaderNodeMapping")
            # uv (m) * 1000 -> mm; image x = (u_mm - u0)/(u1-u0), y = (v_mm - v0)/(v1-v0)
            du = PATTERN_U[1] - PATTERN_U[0]
            dv = PATTERN_V[1] - PATTERN_V[0]
            mp.inputs["Scale"].default_value = (1000.0 / du, 1000.0 / dv, 1.0)
            mp.inputs["Location"].default_value = (-PATTERN_U[0] / du, -PATTERN_V[0] / dv, 0.0)
            nt.links.new(uvn.outputs["UV"], mp.inputs["Vector"])
            tb = nt.nodes.new("ShaderNodeTexImage")
            tb.image = pattern_bc_img
            tb.interpolation = "Linear"
            tb.extension = "EXTEND"
            nt.links.new(mp.outputs["Vector"], tb.inputs["Vector"])
            tr = nt.nodes.new("ShaderNodeTexImage")
            tr.image = pattern_rough_img
            tr.extension = "EXTEND"
            nt.links.new(mp.outputs["Vector"], tr.inputs["Vector"])
            c_bc = nt.nodes.new("ShaderNodeMixRGB")
            c_bc.inputs["Fac"].default_value = 0.0
            nt.links.new(tb.outputs["Color"], c_bc.inputs["Color1"])
            c_bc.name = "ch_bc"
            c_r = nt.nodes.new("ShaderNodeMath")
            c_r.operation = "ADD"
            c_r.inputs[1].default_value = 0.0
            nt.links.new(tr.outputs["Color"], c_r.inputs[0])
            c_r.name = "ch_rough"
            c_m = nt.nodes.new("ShaderNodeValue")
            c_m.outputs[0].default_value = metal
            c_m.name = "ch_metal"
            bc_sock, r_sock = c_bc.outputs["Color"], c_r.outputs[0]
        else:
            tc = nt.nodes.new("ShaderNodeTexCoord")
            nz = nt.nodes.new("ShaderNodeTexNoise")
            nz.inputs["Scale"].default_value = scale * 1000.0   # object space is metres
            nz.inputs["Detail"].default_value = 4.0
            nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
            fac = nt.nodes.new("ShaderNodeMapRange")
            fac.inputs["From Min"].default_value = 0.3
            fac.inputs["From Max"].default_value = 0.7
            fac.inputs["To Min"].default_value = 1.0 - amp
            fac.inputs["To Max"].default_value = 1.0 + amp
            nt.links.new(nz.outputs["Fac"], fac.inputs["Value"])
            c_bc = nt.nodes.new("ShaderNodeMixRGB")
            c_bc.blend_type = "MULTIPLY"
            c_bc.inputs["Fac"].default_value = 1.0
            c_bc.inputs["Color1"].default_value = (*bc, 1.0)
            nt.links.new(fac.outputs["Result"], c_bc.inputs["Color2"])
            c_bc.name = "ch_bc"
            c_r = nt.nodes.new("ShaderNodeMapRange")
            c_r.inputs["From Min"].default_value = 0.3
            c_r.inputs["From Max"].default_value = 0.7
            c_r.inputs["To Min"].default_value = rough - 0.04
            c_r.inputs["To Max"].default_value = rough + 0.04
            nt.links.new(nz.outputs["Fac"], c_r.inputs["Value"])
            c_r.name = "ch_rough"
            c_m = nt.nodes.new("ShaderNodeValue")
            c_m.outputs[0].default_value = metal
            c_m.name = "ch_metal"
            bc_sock, r_sock = c_bc.outputs["Color"], c_r.outputs["Result"]
            if name in ("Cord",):
                # twisted cord: diagonal strand striations + fibre noise (captured by the normal bake).  Final pass:
                # coarsened from 1.1 mm strands / 0.29 mm fibre (a ~11 px hatch at 102 px/cm that showed moire in
                # close-ups and would crawl in motion) to 2.2 mm strands / 0.67 mm fibre, softer bump
                wv = nt.nodes.new("ShaderNodeTexWave")
                wv.wave_type = "BANDS"
                wv.bands_direction = "DIAGONAL"
                wv.inputs["Scale"].default_value = 820.0     # look-match R1: finer braid (sheet: fine thread texture)
                wv.inputs["Distortion"].default_value = 1.5
                wv.inputs["Detail"].default_value = 2.0
                nt.links.new(tc.outputs["Object"], wv.inputs["Vector"])
                nz2 = nt.nodes.new("ShaderNodeTexNoise")
                nz2.inputs["Scale"].default_value = 1500.0
                nz2.inputs["Detail"].default_value = 2.0
                nt.links.new(tc.outputs["Object"], nz2.inputs["Vector"])
                addn = nt.nodes.new("ShaderNodeMath")
                addn.operation = "MULTIPLY_ADD"
                addn.inputs[1].default_value = 0.35
                nt.links.new(nz2.outputs["Fac"], addn.inputs[0])
                nt.links.new(wv.outputs["Fac"], addn.inputs[2])
                bump = nt.nodes.new("ShaderNodeBump")
                bump.inputs["Strength"].default_value = 0.28
                bump.inputs["Distance"].default_value = 0.00010
                nt.links.new(addn.outputs[0], bump.inputs["Height"])
                nt.links.new(bump.outputs["Normal"], bs.inputs["Normal"])
            elif name in ("BlackSteel", "Silver", "BranchSteel"):
                nz2 = nt.nodes.new("ShaderNodeTexNoise")
                nz2.inputs["Scale"].default_value = 2200.0
                nz2.inputs["Detail"].default_value = 2.0
                nt.links.new(tc.outputs["Object"], nz2.inputs["Vector"])
                bump = nt.nodes.new("ShaderNodeBump")
                # look-match R1: the sword passes metal_bump=(0.03, 0.12) (polished); the default keeps the old values for
                # other callers (the sheath builds its materials through this function)
                mb_ = metal_bump or (0.10, 0.3)
                bump.inputs["Strength"].default_value = mb_[0] if name != "BranchSteel" else mb_[1]
                bump.inputs["Distance"].default_value = 0.00003
                nt.links.new(nz2.outputs["Fac"], bump.inputs["Height"])
                nt.links.new(bump.outputs["Normal"], bs.inputs["Normal"])
        nt.links.new(bc_sock, bs.inputs["Base Color"])
        nt.links.new(r_sock, bs.inputs["Roughness"])
        nt.links.new(c_m.outputs[0], bs.inputs["Metallic"])
        em = nt.nodes.new("ShaderNodeEmission")
        em.name = "bake_emit"
        m["bc_socket"] = bc_sock.node.name
        mats.append(m)
    return mats


def set_bake_channel(mats, channel):
    """channel in ('SHADED', 'BC', 'ROUGH', 'METAL')."""
    for m in mats:
        nt = m.node_tree
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        bs = _principled(nt)
        em = nt.nodes["bake_emit"]
        for l in list(out.inputs["Surface"].links):
            nt.links.remove(l)
        for l in list(em.inputs["Color"].links):
            nt.links.remove(l)
        if channel == "SHADED":
            nt.links.new(bs.outputs[0], out.inputs["Surface"])
            continue
        node = nt.nodes["ch_bc" if channel == "BC" else "ch_rough" if channel == "ROUGH" else "ch_metal"]
        sock = node.outputs[0]
        nt.links.new(sock, em.inputs["Color"])
        em.inputs["Strength"].default_value = 1.0
        nt.links.new(em.outputs[0], out.inputs["Surface"])


def make_game_material(name, bc_path, orm_path, n_path, dx_normals=True):
    """Blender preview of the shipped material: BC (sRGB), ORM (linear; R AO, G rough, B metal),
    N (DirectX on disk -> green flipped back for Blender's OpenGL convention)."""
    import bpy
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bs = _principled(nt)
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UV0"
    tbc = nt.nodes.new("ShaderNodeTexImage")
    tbc.image = bpy.data.images.load(str(bc_path), check_existing=True)
    tbc.image.colorspace_settings.name = "sRGB"
    torm = nt.nodes.new("ShaderNodeTexImage")
    torm.image = bpy.data.images.load(str(orm_path), check_existing=True)
    torm.image.colorspace_settings.name = "Non-Color"
    tn = nt.nodes.new("ShaderNodeTexImage")
    tn.image = bpy.data.images.load(str(n_path), check_existing=True)
    tn.image.colorspace_settings.name = "Non-Color"
    for t in (tbc, torm, tn):
        nt.links.new(uv.outputs["UV"], t.inputs["Vector"])
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(torm.outputs["Color"], sep.inputs["Color"])
    # AO applied to base colour (preview of what Unreal's AO does to indirect light)
    mul = nt.nodes.new("ShaderNodeMixRGB")
    mul.blend_type = "MULTIPLY"
    mul.inputs["Fac"].default_value = 1.0
    nt.links.new(tbc.outputs["Color"], mul.inputs["Color1"])
    aoc = nt.nodes.new("ShaderNodeMapRange")
    aoc.inputs["To Min"].default_value = 0.35
    nt.links.new(sep.outputs["Red"], aoc.inputs["Value"])
    nt.links.new(aoc.outputs["Result"], mul.inputs["Color2"])
    nt.links.new(mul.outputs["Color"], bs.inputs["Base Color"])
    nt.links.new(sep.outputs["Green"], bs.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], bs.inputs["Metallic"])
    nsep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(tn.outputs["Color"], nsep.inputs["Color"])
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    nt.links.new(nsep.outputs["Green"], inv.inputs[1])
    ncomb = nt.nodes.new("ShaderNodeCombineColor")
    nt.links.new(nsep.outputs["Red"], ncomb.inputs["Red"])
    nt.links.new(inv.outputs[0] if dx_normals else nsep.outputs["Green"], ncomb.inputs["Green"])
    nt.links.new(nsep.outputs["Blue"], ncomb.inputs["Blue"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.uv_map = "UV0"
    nt.links.new(ncomb.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bs.inputs["Normal"])
    return m
