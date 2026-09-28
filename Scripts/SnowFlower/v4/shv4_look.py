"""Snow Flower sheath look: the painted marble lacquer (numpy, from the spec's measured tones and vein statistics),
the high-poly bake materials (same node contract as sfv4_look so its set_bake_channel works) and the game materials.

Lacquer (spec section 7): cool blue-grey black, display median 0.178 (sRGB), soft cloudy mottling 10-27 mm, thin
light-grey veins ~1 mm wide on ~7 % of the surface running mostly lengthwise with diagonal branches, glossy
(roughness 0.15-0.25).  Etched twigs: faint flat grey lines along the chamfers (albedo only).  The albedo values
below are DESIGNED so the studio render of the baked maps reproduces those display tones (calibrated, see report).
"""
from __future__ import annotations

import math

import numpy as np

import shv4_spec as S
from sfv4_look import fbm, smoothstep

# pattern domain (mm): u = arclength from the face centre (front -45..45, back 55..145), v = z
PAT_U = (-48.0, 148.0)
PAT_V = (S.Z_MOUTH - 4.0, float(S.zr(1300.0)) + 4.0)   # look-match: the core now runs to row 1296
PAT_PPMM = 4.0

#: lacquer albedo (linear) - DESIGNED, calibrated against the reference's display tones (SHEATH_REPORT section 4)
LACQ_DARK = np.array([0.0030, 0.0038, 0.0060])
LACQ_MID = np.array([0.0150, 0.0184, 0.0268])
LACQ_VEIN = np.array([0.130, 0.138, 0.160])
LACQ_ETCH = np.array([0.060, 0.063, 0.070])


def paint_lacquer(seed=7717):
    rng = np.random.default_rng(seed)
    W = int((PAT_U[1] - PAT_U[0]) * PAT_PPMM)
    H = int((PAT_V[1] - PAT_V[0]) * PAT_PPMM)
    u = PAT_U[0] + (np.arange(W) + 0.5) / PAT_PPMM
    z = PAT_V[0] + (np.arange(H) + 0.5) / PAT_PPMM
    UU, ZZ = np.meshgrid(u, z)
    # clouds: 10-27 mm, stretched along the sheath (autocorrelation ~11 px along vs ~4 px across)
    cloud = fbm((H, W), (H / (PAT_PPMM * 24.0), W / (PAT_PPMM * 11.0)), 5, rng)
    cloud2 = fbm((H, W), (H / (PAT_PPMM * 60.0), W / (PAT_PPMM * 30.0)), 3, rng)
    # veins: level crossings of a lengthwise-stretched field (thin lines, mostly along z) + diagonal branches
    f1 = fbm((H, W), (H / (PAT_PPMM * 40.0), W / (PAT_PPMM * 7.0)), 5, rng)
    f2 = fbm((H, W), (H / (PAT_PPMM * 18.0), W / (PAT_PPMM * 14.0)), 4, rng)
    warp = fbm((H, W), (H / (PAT_PPMM * 30.0), W / (PAT_PPMM * 20.0)), 3, rng)
    g1 = f1 + 0.22 * (warp - 0.5)
    v1 = np.exp(-((g1 - 0.5) / 0.0085) ** 2)
    v2 = np.exp(-((f2 - 0.47) / 0.0065) ** 2) * smoothstep(0.55, 0.70, cloud2)
    vein = np.clip(0.45 * v1 + 0.30 * v2, 0, 1)     # look-match: softer, fewer line veins (the reference has wisps)
    vein *= 0.55 + 0.45 * smoothstep(0.35, 0.75, fbm((H, W), (H / (PAT_PPMM * 50.0), W / (PAT_PPMM * 25.0)), 2, rng))
    m = smoothstep(0.32, 0.74, 0.7 * cloud + 0.3 * cloud2)   # look-match: ~3x the marble contrast
    base = LACQ_DARK[None, None, :] * (1 - m[..., None]) + LACQ_MID[None, None, :] * m[..., None]
    # a faint lighter haze inside the clouds (the reference's soft grey mottling)
    haze = smoothstep(0.60, 0.90, cloud) * 0.85
    base = base * (1 - haze[..., None]) + (LACQ_VEIN * 0.45)[None, None, :] * haze[..., None]
    bc = base * (1 - vein[..., None]) + LACQ_VEIN[None, None, :] * vein[..., None]
    rough = 0.19 + 0.05 * (cloud - 0.5) + 0.05 * vein
    # ---- etched twigs along the chamfers (flat, albedo only)
    etch = np.zeros((H, W))
    for (r0, r1, sideflag) in S.ETCHED:
        for face_off in (0.0,):
            rngt = np.random.default_rng(int(r0 * 7 + (sideflag + 2) * 13))
            # chamfer band of the front island: |u| 17..31 mm; image-left (+X) = u < 0
            sgn = -1.0 if sideflag > 0 else 1.0
            for tw in range(3):
                z0 = float(S.zr(r0 + (r1 - r0) * rngt.uniform(0, 0.5)))
                zlen = float((r1 - r0) * S.K * rngt.uniform(0.5, 0.9))
                u0 = sgn * rngt.uniform(19.0, 28.0) + face_off
                pts = [(u0, z0)]
                ang = rngt.uniform(-0.35, 0.35)
                while pts[-1][1] - z0 < zlen:
                    ang += rngt.uniform(-0.25, 0.25)
                    ang = float(np.clip(ang, -0.6, 0.6))
                    uu, zz = pts[-1]
                    pts.append((float(np.clip(uu + 2.0 * math.sin(ang), sgn * 16.5 if sgn > 0 else -33.0,
                                               33.0 if sgn > 0 else -16.5)), zz + 2.0 * math.cos(ang)))
                    if rngt.random() < 0.22:
                        a2 = ang + rngt.choice([-1, 1]) * rngt.uniform(0.5, 0.9)
                        bu, bz = pts[-1]
                        br = [(bu, bz)]
                        for _ in range(int(rngt.integers(2, 5))):
                            br.append((br[-1][0] + 1.6 * math.sin(a2), br[-1][1] + 1.6 * math.cos(a2)))
                        _stroke(etch, br, 0.35, PAT_PPMM)
                _stroke(etch, pts, 0.45, PAT_PPMM)
    bc = bc * (1 - etch[..., None]) + LACQ_ETCH[None, None, :] * etch[..., None]
    meta = {"W": W, "H": H, "ppmm": PAT_PPMM, "u_range": PAT_U, "v_range": PAT_V,
            "vein_fraction": float((vein > 0.35).mean())}
    return np.clip(bc, 0, 1), np.clip(rough, 0.05, 0.9), meta


def _stroke(img, pts, width_mm, ppmm):
    H, W = img.shape
    for (u0, z0), (u1, z1) in zip(pts[:-1], pts[1:]):
        n = int(max(abs(u1 - u0), abs(z1 - z0)) * ppmm * 2) + 2
        for t in np.linspace(0, 1, n):
            u = u0 + (u1 - u0) * t
            z = z0 + (z1 - z0) * t
            cx = (u - PAT_U[0]) * ppmm
            cy = (z - PAT_V[0]) * ppmm
            r = width_mm * ppmm
            x0, x1 = int(max(cx - r - 1, 0)), int(min(cx + r + 2, W))
            y0, y1 = int(max(cy - r - 1, 0)), int(min(cy + r + 2, H))
            if x1 <= x0 or y1 <= y0:
                continue
            X, Y = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
            d = np.hypot(X - cx, Y - cy)
            img[y0:y1, x0:x1] = np.maximum(img[y0:y1, x0:x1], np.clip(1.0 - (d - r * 0.5) / (r * 0.8), 0, 1) * 0.8)


# high material slots (indices = shv4_parts.H_*): name, base colour (linear), roughness, metallic, noise amp, scale
HIGH_MATERIALS = [
    ("Lacquer", None, None, 0.0, 0.0, 0.0),
    ("Silver", (0.62, 0.62, 0.635), 0.14, 1.0, 0.06, 0.9),      # look-match: polished (was 0.60 / 0.27 satin); tone-matched
    ("Inlay", (0.38, 0.395, 0.43), 0.09, 0.0, 0.05, 1.3),     # pearl-white petals, buds, pods (dielectric)
    ("Recess", (0.030, 0.031, 0.036), 0.46, 1.0, 0.20, 0.8),
    ("Inset", (0.014, 0.017, 0.026), 0.22, 0.0, 0.25, 0.35),
    ("Branch", (0.62, 0.62, 0.635), 0.16, 1.0, 0.12, 1.1),
    ("Cavity", (0.010, 0.010, 0.012), 0.65, 0.0, 0.10, 0.5),
    ("Antique", (0.44, 0.44, 0.45), 0.30, 1.0, 0.22, 1.5),
]


def make_high_materials(pattern_bc_img, pattern_rough_img):
    import bpy
    import sfv4_look as LK
    saved = LK.HIGH_MATERIALS
    LK.HIGH_MATERIALS = [("Blade",) + m[1:] if m[0] == "Lacquer" else m for m in HIGH_MATERIALS]
    saved_u, saved_v = LK.PATTERN_U, LK.PATTERN_V
    LK.PATTERN_U, LK.PATTERN_V = PAT_U, PAT_V
    try:
        mats = LK.make_high_materials(pattern_bc_img, pattern_rough_img)
    finally:
        LK.HIGH_MATERIALS = saved
        LK.PATTERN_U, LK.PATTERN_V = saved_u, saved_v
    for m, spec in zip(mats, HIGH_MATERIALS):
        m.name = f"SH4H_{spec[0]}"
    # bark / hammered texture on the vine: a lengthwise-stretched noise bump (captured by the normal bake)
    m = mats[5]
    nt = m.node_tree
    bs = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    if not bs.inputs["Normal"].links:
        tc = nt.nodes.new("ShaderNodeTexCoord")
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (2600.0, 2600.0, 700.0)
        nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = 1.0
        nz.inputs["Detail"].default_value = 6.0
        nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.45
        bump.inputs["Distance"].default_value = 0.0002
        nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bs.inputs["Normal"])
    return mats
