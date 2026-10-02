"""Pilot 2 rock materials (bpy). Two node trees:

1. COMPOSITE (the bake source, on the dense mesh; also rendered directly on the surface test patch): the scanned macro
   layer (Poly Haven CC0, regraded to grey granite by Scripts/stone/scan_surface.py, box-projected in object space at
   its own tile size) x the rock tint, then the weathering layers driven by per-vertex fields from
   Scripts/stone/stone_weather2.py:
     Mk  (point colour) R moss, G lichen zone, B wet, A stain (signed: >0.5 tan iron staining, <0.5 grime)
     Mk2 (point colour) R cavity (crevice / joint), G olive (algae, low in the wet zone), B arris (convex, bleached)
   - stain: the sheet's tan only as staining (owner's call), grime as the dark weathering mottles;
   - lichen: lobed rosettes made per pixel (3-D Voronoi cells; each rosette's radius varies with a noise of the
     direction from its centre -> 5-9 rounded lobes), pale grey-green with a darker heart, gated by the zone field;
   - wet: albedo darkened with an olive tint low down, roughness to ~0.2 (glossy);
   - moss: mossy_rock albedo (box-projected) where Mk.R.
   ``mode`` picks what the tree emits for baking: "BC" (linear albedo), "MASK" (R moss, G lichen, B wet) or "ROUGH",
   or "PREVIEW" (a full Principled surface with the grain detail on top: the test patch).
2. SHIPPED (MI_DKR_<Rock>, the Unreal MI plan on M_ST_RockUnique): unique BC x the tiling grain detail
   (T_DKR_GraniteGrain_BC / its mean, strength GrainAmount, faded under moss), unique N (DirectX -> flipped for
   Blender) with the grain as a fine bump on top, ORM roughness.
"""
from __future__ import annotations

from pathlib import Path

import bpy

import rocks_material as rm1      # pilot 1 helpers (G node builder, moss / grass materials)

ROOT = Path(__file__).resolve().parents[3]
TEXW = ROOT / "WorkFiles" / "dojo" / "build" / "rocks" / "work2" / "tex"
TEXS = ROOT / "Exports" / "DojoKit" / "Rocks" / "Textures"

GRAIN_TILE_M = 0.45                    # T_DKR_GraniteGrain_*: 2048 px = 0.45 m (pilot 2 fix 1; was 0.75)
LICHEN_TILE_M = 0.5                    # T_DKR_LichenDetail_*: 1024 px = 0.5 m (scan_surface.lichen_layer)
GRAIN_MEAN_LIN = (0.3211, 0.2937, 0.2845)        # scan_surface.json grain.tile.mean_linear_rgb

# per-kind composite parameters (linear colours)
KIND = {
    "river": dict(macro="river", tile_m=1.6, tint=(1.0, 0.90, 0.80), stain=(0.62, 0.47, 0.28), stain_amt=0.85,
                  crust=0.85, crust_t=0.53, spots=0.85, spots_t=0.58, crust_scale=17.0, spots_scale=30.0,
                  grime=(0.30, 0.295, 0.285), grime_amt=0.7, cav=0.72, arris=0.24, wet_dark=0.26,
                  olive=(0.30, 0.31, 0.16), wet_rough=0.07, wet_rough_flat=0.22, base_rough=0.78, grain=0.7,
                  bake_lichen=False, lichen_scale=14.0,
                  lichen_r=(0.012, 0.026), lichen_density=0.8, moss_tile_m=0.9),
    "cliff": dict(macro="cliff", tile_m=1.4, tint=(1.0, 0.90, 0.80), stain=(0.62, 0.47, 0.28), stain_amt=0.85,
                  crust=0.75, crust_t=0.54, spots=0.85, spots_t=0.58, crust_scale=18.0, spots_scale=32.0,
                  grime=(0.30, 0.295, 0.285), grime_amt=0.7, cav=0.78, arris=0.24, wet_dark=0.55,
                  olive=(0.35, 0.34, 0.20), wet_rough=0.35, wet_rough_flat=0.45, base_rough=0.84, grain=1.0,
                  bake_lichen=False, lichen_scale=14.0,
                  lichen_r=(0.012, 0.027), lichen_density=0.85, moss_tile_m=0.9),
}
LICHEN_COL = (0.50, 0.52, 0.36)        # pale grey-green rosette (linear)
MOSS_TINT = (1.25, 1.18, 0.50)          # toward the sheet's bright yellow-green moss
MOSS_SHELL_TINT = (0.34, 0.40, 0.13)    # pilot 2 fix 1: the shell is the dark cushion interior under the shoots


def _img(path, data):
    return rm1._img(Path(path), data)


def _sock(node, name, kind, out=False):
    return rm1._socket(node, name, kind, out)


def _new_mat(name):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    return mat


def madd(g, a, b, c):
    m = g.node("ShaderNodeMath", operation="MULTIPLY_ADD")
    for sock, v in zip(m.inputs, (a, b, c)):
        if isinstance(v, bpy.types.NodeSocket):
            g.link(v, sock)
        else:
            sock.default_value = v
    return m.outputs[0]


def _vec_scale(g, vec, s):
    m = g.node("ShaderNodeVectorMath", operation="SCALE")
    g.link(vec, m.inputs[0])
    _sock(m, "Scale", "VALUE").default_value = s
    return m.outputs[0]


def _box_tex(g, img, vec, blend=0.3):
    t = g.tex(img, vec)
    t.projection = "BOX"
    t.projection_blend = blend
    return t


def _lichen(g, P):
    """Lobed rosettes from the per-vertex seed fields (stone_weather2.lichen_fields): Lc = offset to the nearest
    seed (m), Lp = (radius m, lobe random, phase random, present). Returns (cover 0-1, shade 0-1)."""
    lc = g.node("ShaderNodeAttribute", attribute_name="Lc", attribute_type="GEOMETRY")
    lp = g.node("ShaderNodeAttribute", attribute_name="Lp", attribute_type="GEOMETRY")
    sp = g.node("ShaderNodeSeparateColor")
    g.link(lp.outputs["Color"], sp.inputs["Color"])
    d = lc.outputs["Vector"]
    ln = g.node("ShaderNodeVectorMath", operation="LENGTH")
    g.link(d, ln.inputs[0])
    dist = ln.outputs["Value"]
    nrm = g.node("ShaderNodeVectorMath", operation="NORMALIZE")
    g.link(d, nrm.inputs[0])
    # petal lobes: polar angle of the offset in the surface's tangent frame, r(theta) = R (0.62 + 0.32
    # |cos(k theta / 2 + phase)|^0.7), k = 5-8 lobes per rosette, a little noise on the rim
    geo = g.node("ShaderNodeNewGeometry")
    tr = g.node("ShaderNodeVectorTransform", vector_type="NORMAL", convert_from="WORLD", convert_to="OBJECT")
    g.link(geo.outputs["Normal"], tr.inputs["Vector"])
    t = g.node("ShaderNodeVectorMath", operation="CROSS_PRODUCT")
    g.link(tr.outputs["Vector"], t.inputs[0])
    t.inputs[1].default_value = (0.31, 0.42, 0.85)
    tn = g.node("ShaderNodeVectorMath", operation="NORMALIZE")
    g.link(t.outputs[0], tn.inputs[0])
    bt = g.node("ShaderNodeVectorMath", operation="CROSS_PRODUCT")
    g.link(tr.outputs["Vector"], bt.inputs[0])
    g.link(tn.outputs[0], bt.inputs[1])
    du = g.node("ShaderNodeVectorMath", operation="DOT_PRODUCT")
    g.link(d, du.inputs[0])
    g.link(tn.outputs[0], du.inputs[1])
    dv = g.node("ShaderNodeVectorMath", operation="DOT_PRODUCT")
    g.link(d, dv.inputs[0])
    g.link(bt.outputs[0], dv.inputs[1])
    theta = g.mathf("ARCTAN2", dv.outputs["Value"], du.outputs["Value"])
    k = g.mathf("FLOOR", madd(g, sp.outputs[1], 4.0, 5.0))
    ph = g.mathf("MULTIPLY", sp.outputs[2], 6.283)
    cosv = g.mathf("COSINE", g.mathf("ADD", g.mathf("MULTIPLY", g.mathf("MULTIPLY", theta, k), 0.5), ph))
    petal = g.mathf("POWER", g.mathf("ABSOLUTE", cosv), 0.7)
    rimn = g.node("ShaderNodeTexNoise")
    rimn.inputs["Scale"].default_value = 3.0
    g.link(nrm.outputs[0], rimn.inputs["Vector"])
    lobf = madd(g, petal, 0.32, 0.56)
    lobf = madd(g, rimn.outputs["Fac"], 0.12, lobf)
    rad = g.mathf("MULTIPLY", sp.outputs[0], lobf)
    edge = g.node("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP")
    g.link(dist, edge.inputs["Value"])
    g.link(g.mathf("SUBTRACT", rad, 0.0012), edge.inputs["From Min"])
    g.link(rad, edge.inputs["From Max"])
    edge.inputs["To Min"].default_value = 1.0
    edge.inputs["To Max"].default_value = 0.0
    cover = g.mathf("MULTIPLY", edge.outputs["Result"], lp.outputs["Alpha"])
    rel = g.mathf("DIVIDE", dist, g.mathf("MAXIMUM", rad, 1e-4))
    heart = g.node("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP")
    g.link(rel, heart.inputs["Value"])
    heart.inputs["From Min"].default_value = 0.12
    heart.inputs["From Max"].default_value = 0.45
    heart.inputs["To Min"].default_value = 1.0
    heart.inputs["To Max"].default_value = 0.0
    crease = g.node("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP")
    g.link(petal, crease.inputs["Value"])
    crease.inputs["From Min"].default_value = 0.0
    crease.inputs["From Max"].default_value = 0.30
    crease.inputs["To Min"].default_value = 1.0
    crease.inputs["To Max"].default_value = 0.0
    inner = g.node("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP")
    g.link(rel, inner.inputs["Value"])
    inner.inputs["From Min"].default_value = 0.25
    inner.inputs["From Max"].default_value = 0.45
    crease_v = g.mathf("MULTIPLY", crease.outputs["Result"], inner.outputs["Result"])
    rim = g.node("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP")
    g.link(rel, rim.inputs["Value"])
    rim.inputs["From Min"].default_value = 0.80
    rim.inputs["From Max"].default_value = 1.0
    shade = g.mathf("MAXIMUM", g.mathf("MAXIMUM", heart.outputs["Result"], g.mathf("MULTIPLY", crease_v, 0.8)),
                    g.mathf("MULTIPLY", rim.outputs["Result"], 0.35))
    return cover, shade


def composite_material(name, kind, mode="BC", grain=True, P=None):
    """The bake-source tree (see module doc). ``mode``: BC | MASK | ROUGH | PREVIEW."""
    P = dict(KIND[kind], **(P or {}))
    mat = _new_mat(name)
    g = rm1.G(mat)
    out = g.node("ShaderNodeOutputMaterial")
    tc = g.node("ShaderNodeTexCoord")
    pos = tc.outputs["Object"]
    mk = g.node("ShaderNodeAttribute", attribute_name="Mk", attribute_type="GEOMETRY")
    mk2 = g.node("ShaderNodeAttribute", attribute_name="Mk2", attribute_type="GEOMETRY")
    s1 = g.node("ShaderNodeSeparateColor")
    g.link(mk.outputs["Color"], s1.inputs["Color"])
    s2 = g.node("ShaderNodeSeparateColor")
    g.link(mk2.outputs["Color"], s2.inputs["Color"])
    moss, lzone, wet = s1.outputs[0], s1.outputs[1], s1.outputs[2]
    stain = mk.outputs["Alpha"]
    cav, olive, arris = s2.outputs[0], s2.outputs[1], s2.outputs[2]
    macro = _box_tex(g, _img(TEXW / f"Macro_{P['macro']}_BC.png", False), _vec_scale(g, pos, 1.0 / P["tile_m"]))
    base = g.mix(1.0, macro.outputs["Color"], P["tint"], "MULTIPLY")
    t2 = g.mathf("MULTIPLY", stain, 2.0)
    tanf = g.mathf("MAXIMUM", g.mathf("SUBTRACT", t2, 1.0), 0.0)
    grimef = g.mathf("MAXIMUM", g.mathf("SUBTRACT", 1.0, t2), 0.0)
    # >0.5: pale beige weathering crust with the sheet's tan (a mix toward a pale colour, modulated by the macro)
    pale = g.mix(1.0, P["stain"], g.mix(0.5, (1.0, 1.0, 1.0), g.mix(1.0, macro.outputs["Color"], (2.0, 2.0, 2.0),
                                                                      "MULTIPLY")), "MULTIPLY")
    base = g.mix(g.mathf("MULTIPLY", tanf, P["stain_amt"]), base, pale)
    base = g.mix(g.mathf("MULTIPLY", grimef, P["grime_amt"]), base, g.mix(1.0, base, P["grime"], "MULTIPLY"))
    # bleached convex arrises, dark crevices
    base = g.mix(g.mathf("MULTIPLY", arris, P["arris"]), base, (0.62, 0.61, 0.58))
    cavc = g.mix(g.mathf("MULTIPLY", cav, P["cav"]), (1.0, 1.0, 1.0), (0.05, 0.05, 0.05))
    base = g.mix(1.0, base, cavc, "MULTIPLY")
    # crustose lichen / weathering crust (the sheet's crisp pale patches) and dark spots, per pixel with sharp
    # edges, on the dry, moss-free surface
    dryx = g.mathf("MULTIPLY", g.mathf("SUBTRACT", 1.0, g.mathf("MINIMUM", g.mathf("MULTIPLY", wet, 1.6), 1.0)),
                   g.mathf("SUBTRACT", 1.0, moss))
    cn = g.node("ShaderNodeTexNoise")
    cn.inputs["Scale"].default_value = P["crust_scale"]
    cn.inputs["Detail"].default_value = 7.0
    cn.inputs["Roughness"].default_value = 0.62
    g.link(pos, cn.inputs["Vector"])
    ce = g.node("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP")
    g.link(cn.outputs["Fac"], ce.inputs["Value"])
    ce.inputs["From Min"].default_value = P["crust_t"]
    ce.inputs["From Max"].default_value = P["crust_t"] + 0.025
    crust = g.mathf("MULTIPLY", g.mathf("MULTIPLY", ce.outputs["Result"], dryx), P["crust"])
    base = g.mix(crust, base, g.mix(0.35, (0.58, 0.57, 0.52), macro.outputs["Color"]))
    sn = g.node("ShaderNodeTexNoise")
    sn.inputs["Scale"].default_value = P["spots_scale"]
    sn.inputs["Detail"].default_value = 5.0
    sn.inputs["Roughness"].default_value = 0.6
    g.link(pos, sn.inputs["Vector"])
    se = g.node("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP")
    g.link(sn.outputs["Fac"], se.inputs["Value"])
    se.inputs["From Min"].default_value = P["spots_t"]
    se.inputs["From Max"].default_value = P["spots_t"] + 0.03
    spots = g.mathf("MULTIPLY", g.mathf("MULTIPLY", se.outputs["Result"], g.mathf("SUBTRACT", 1.0, moss)),
                    P["spots"])
    base = g.mix(spots, base, g.mix(1.0, base, (0.18, 0.18, 0.18), "MULTIPLY"))
    # lichen rosettes
    if P.get("bake_lichen", True):
        lcov, lheart = _lichen(g, P)
        lcol = g.mix(g.mathf("MULTIPLY", lheart, 0.45), LICHEN_COL, (0.30, 0.31, 0.26))
        lnz = g.node("ShaderNodeTexNoise")
        lnz.inputs["Scale"].default_value = 320.0
        lnz.inputs["Detail"].default_value = 4.0
        g.link(pos, lnz.inputs["Vector"])
        lcol = g.mix(g.mathf("MULTIPLY", g.mathf("SUBTRACT", lnz.outputs["Fac"], 0.35), 1.2), lcol,
                     (0.24, 0.25, 0.18))
        base = g.mix(lcov, base, lcol)
    else:
        # pilot 2 fix 1: the rosettes live in the tiling lichen detail (shipped material); the bake carries only
        # the zone (M.G) and a faint pale crust under it
        lcov = lzone
        base = g.mix(g.mathf("MULTIPLY", lzone, 0.12), base, (0.55, 0.56, 0.50))
    # wet: darker, olive low down
    wetc = g.mix(wet, (1.0, 1.0, 1.0), (P["wet_dark"],) * 3)
    base = g.mix(1.0, base, wetc, "MULTIPLY")
    base = g.mix(g.mathf("MULTIPLY", olive, 0.85), base, g.mix(1.0, base, P["olive"], "MULTIPLY"))
    # moss
    mt = _box_tex(g, _img(TEXS / "T_DKR_MossDetail_BC.png", False), _vec_scale(g, pos, 1.0 / P["moss_tile_m"]))
    mossc = g.mix(1.0, mt.outputs["Color"], MOSS_TINT, "MULTIPLY")
    base = g.mix(moss, base, mossc)
    # roughness
    wr = g.node("ShaderNodeMix", data_type="FLOAT")
    g.link(cav, wr.inputs[0])
    _sock(wr, "A", "VALUE").default_value = P.get("wet_rough_flat", P["wet_rough"])
    _sock(wr, "B", "VALUE").default_value = P["wet_rough"]
    r = g.node("ShaderNodeMix", data_type="FLOAT")
    g.link(wet, r.inputs[0])
    _sock(r, "A", "VALUE").default_value = P["base_rough"]
    g.link(_sock(wr, "Result", "VALUE", out=True), _sock(r, "B", "VALUE"))
    rough = _sock(r, "Result", "VALUE", out=True)
    rough = g.mathf("MAXIMUM", rough, g.mathf("MULTIPLY", moss, 0.9))
    # fresh faces: closer to the neutral grey of the crystal grain (no weathering tint)
    fresh = mk2.outputs["Alpha"]
    gray = g.node("ShaderNodeRGBToBW")
    g.link(base, gray.inputs["Color"])
    base = g.mix(g.mathf("MULTIPLY", fresh, 0.6), base, gray.outputs["Val"])
    if mode in ("BC", "MASK", "ROUGH", "FRESH"):
        em = g.node("ShaderNodeEmission")
        if mode == "FRESH":
            g.link(madd(g, fresh, 0.7, 0.3), em.inputs["Color"])
        elif mode == "BC":
            g.link(base, em.inputs["Color"])
        elif mode == "MASK":
            cm = g.node("ShaderNodeCombineColor")
            g.link(moss, cm.inputs[0])
            g.link(lcov, cm.inputs[1])
            g.link(wet, cm.inputs[2])
            g.link(cm.outputs[0], em.inputs["Color"])
        else:
            g.link(rough, em.inputs["Color"])
        g.link(em.outputs[0], out.inputs["Surface"])
        return mat
    # PREVIEW: the shipped material's maths on the unbaked layers (surface test patch)
    bsdf = g.node("ShaderNodeBsdfPrincipled")
    col = base
    nrm = None
    if grain:
        col, nrm = _grain(g, pos, col, g.mathf("MAXIMUM", moss, lcov), 1.0 / GRAIN_TILE_M, box=True)
    g.link(col, bsdf.inputs["Base Color"])
    g.link(rough, bsdf.inputs["Roughness"])
    if nrm is not None:
        g.link(nrm, bsdf.inputs["Normal"])
    g.link(bsdf.outputs[0], out.inputs["Surface"])
    return mat


GRAIN = dict(amount=1.0, contrast=1.35, bump=0.3, bump_dist=0.0015)


def _grain(g, vec, col, moss, scale, box=False, normal=None, amount=1.0):
    """col x lerp(1, grain / grain_mean, amount x (1 - moss)); bump from the grain height on ``normal``."""
    v = _vec_scale(g, vec, scale)
    tg = _box_tex(g, _img(TEXS / "T_DKR_GraniteGrain_BC.png", False), v) if box else \
        g.tex(_img(TEXS / "T_DKR_GraniteGrain_BC.png", False), v)
    ratio = g.mix(1.0, tg.outputs["Color"], tuple(1.0 / c for c in GRAIN_MEAN_LIN), "MULTIPLY")
    ratio.node.clamp_result = False
    if GRAIN["contrast"] != 1.0:
        pw = g.node("ShaderNodeVectorMath", operation="POWER")
        g.link(ratio, pw.inputs[0])
        pw.inputs[1].default_value = (GRAIN["contrast"],) * 3
        ratio = pw.outputs[0]
    amt = g.mathf("MULTIPLY", g.mathf("SUBTRACT", 1.0, moss), GRAIN["amount"] * amount)
    f = g.mix(amt, (1.0, 1.0, 1.0), ratio)
    f.node.clamp_result = False
    col = g.mix(1.0, col, f, "MULTIPLY")
    col.node.clamp_result = False
    th = _box_tex(g, _img(TEXW / "T_DKR_GraniteGrain_H.png", True), v) if box else \
        g.tex(_img(TEXW / "T_DKR_GraniteGrain_H.png", True), v)
    hsum = th.outputs["Color"]
    bump = g.node("ShaderNodeBump")
    bump.inputs["Strength"].default_value = GRAIN["bump"]
    bump.inputs["Distance"].default_value = GRAIN["bump_dist"]
    g.link(hsum, bump.inputs["Height"])
    if normal is not None:
        g.link(normal, bump.inputs["Normal"])
    return col, bump.outputs["Normal"]


LICHEN = dict(density=1.0, bias=-0.08, bump=0.35, bump_dist=0.0012, rough=0.86)


def _lichen_detail(g, uv, col, nrm, rough, zone, moss, scale, P):
    """Pilot 2 fix 1: crisp foliose rosettes from the tiling T_DKR_LichenDetail_* (20 px/cm), shown per rosette
    where the baked lichen zone (M.G) allows: show = cover x (id < zone x density + bias) x (1 - moss)."""
    v = _vec_scale(g, uv, scale)
    tl = g.tex(_img(TEXS / "T_DKR_LichenDetail_BC.png", False), v)
    th = g.tex(_img(TEXS / "T_DKR_LichenDetail_HID.png", True), v)
    sh = g.node("ShaderNodeSeparateColor")
    g.link(th.outputs["Color"], sh.inputs["Color"])
    thr = madd(g, zone, P["density"], P["bias"])
    gate = g.mathf("LESS_THAN", sh.outputs[1], thr)
    show = g.mathf("MULTIPLY", g.mathf("MULTIPLY", tl.outputs["Alpha"], gate), g.mathf("SUBTRACT", 1.0, moss))
    col = g.mix(show, col, tl.outputs["Color"])
    bump = g.node("ShaderNodeBump")
    bump.inputs["Strength"].default_value = P["bump"]
    bump.inputs["Distance"].default_value = P["bump_dist"]
    g.link(g.mathf("MULTIPLY", sh.outputs[0], show), bump.inputs["Height"])
    g.link(nrm, bump.inputs["Normal"])
    rm = g.node("ShaderNodeMix", data_type="FLOAT")
    g.link(show, rm.inputs[0])
    g.link(rough, _sock(rm, "A", "VALUE"))
    _sock(rm, "B", "VALUE").default_value = P["rough"]
    return col, bump.outputs["Normal"], _sock(rm, "Result", "VALUE", out=True)


def rock_material(name, maps, m_per_uv, grain_amount=1.0, lichen=None):
    """MI_DKR_<Rock>: maps = dict BC, N, ORM, M (paths)."""
    mat = _new_mat(name)
    g = rm1.G(mat)
    out = g.node("ShaderNodeOutputMaterial")
    bsdf = g.node("ShaderNodeBsdfPrincipled")
    uv = g.node("ShaderNodeUVMap", uv_map="UVMap")
    tBC = g.tex(_img(maps["BC"], False), uv.outputs["UV"])
    tN = g.tex(_img(maps["N"], True), uv.outputs["UV"])
    tORM = g.tex(_img(maps["ORM"], True), uv.outputs["UV"])
    tM = g.tex(_img(maps["M"], True), uv.outputs["UV"])
    sep = g.node("ShaderNodeSeparateColor")
    g.link(tN.outputs["Color"], sep.inputs["Color"])
    comb = g.node("ShaderNodeCombineColor")
    g.link(sep.outputs[0], comb.inputs[0])
    g.link(g.mathf("SUBTRACT", 1.0, sep.outputs[1]), comb.inputs[1])
    g.link(sep.outputs[2], comb.inputs[2])
    nm = g.node("ShaderNodeNormalMap", uv_map="UVMap")
    g.link(comb.outputs[0], nm.inputs["Color"])
    sORM = g.node("ShaderNodeSeparateColor")
    g.link(tORM.outputs["Color"], sORM.inputs["Color"])
    sM = g.node("ShaderNodeSeparateColor")
    g.link(tM.outputs["Color"], sM.inputs["Color"])
    # grain weight = (1 - moss) x M.A (fresh 1 .. weathered 0.3), pilot 2 fix 1
    gmask = g.mathf("SUBTRACT", 1.0, g.mathf("MULTIPLY", g.mathf("SUBTRACT", 1.0, sM.outputs[0]),
                                              tM.outputs["Alpha"]))
    col, nrm = _grain(g, uv.outputs["UV"], tBC.outputs["Color"], gmask,
                      m_per_uv / GRAIN_TILE_M, amount=grain_amount,
                      normal=nm.outputs["Normal"])
    rough = sORM.outputs[1]
    if lichen:
        col, nrm, rough = _lichen_detail(g, uv.outputs["UV"], col, nrm, rough, sM.outputs[1], sM.outputs[0],
                                         m_per_uv / LICHEN_TILE_M, lichen)
    g.link(col, bsdf.inputs["Base Color"])
    g.link(rough, bsdf.inputs["Roughness"])
    g.link(nrm, bsdf.inputs["Normal"])
    g.link(bsdf.outputs[0], out.inputs["Surface"])
    mat["unreal_plan"] = ("MI of M_ST_RockUnique: BaseColor = BC x lerp(1, GrainBC/GrainMean, GrainAmount x (1-M.R)); "
                          "lichen detail: show = LichenBC.A x (LichenHID.G < M.G x Density + Bias) x (1-M.R), "
                          "BaseColor = lerp(BaseColor, LichenBC.rgb, show), Normal += LichenN x show, Roughness -> "
                          "0.86; Normal = BlendAngleCorrected(N, GrainN); Roughness = ORM.G; AO = ORM.R; M = R moss, "
                          "G lichen zone, B wet (for the master's wetness / snow overrides)")
    mat["grain"] = str(dict(GRAIN, amount_mi=grain_amount))
    mat["lichen"] = str(lichen)
    return mat


def moss_strand_material(name="MI_DKR_MossStrand"):
    """Pilot 2 fix 1: moss shoots (stone_moss.moss_cushions): Col.R base -> tip (dark olive interior -> yellow-green
    tips, the sheet's moss panel), Col.G per-shoot variation, Col.B = 1 on sporophyte stalks (red-brown)."""
    mat = bpy.data.materials.get(name)
    if mat is not None:
        return mat
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    g = rm1.G(mat)
    out = g.node("ShaderNodeOutputMaterial")
    bsdf = g.node("ShaderNodeBsdfPrincipled")
    at = g.node("ShaderNodeAttribute", attribute_name="Col", attribute_type="GEOMETRY")
    sep = g.node("ShaderNodeSeparateColor")
    g.link(at.outputs["Color"], sep.inputs["Color"])
    ramp = g.node("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position = 0.0
    cr.elements[0].color = (0.035, 0.045, 0.012, 1)
    cr.elements[1].position = 1.0
    cr.elements[1].color = (0.56, 0.62, 0.10, 1)
    e = cr.elements.new(0.55)
    e.color = (0.20, 0.30, 0.04, 1)
    g.link(sep.outputs[0], ramp.inputs["Fac"])
    var = g.mix(g.mathf("MULTIPLY", sep.outputs[1], 0.35), ramp.outputs["Color"], (0.30, 0.26, 0.06))
    spo = g.mix(sep.outputs[2], var, (0.22, 0.09, 0.04))
    g.link(spo, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.7
    for k in ("Subsurface Weight",):
        if k in bsdf.inputs:
            bsdf.inputs[k].default_value = 0.0
    g.link(bsdf.outputs[0], out.inputs["Surface"])
    mat["unreal_plan"] = "MI of a two-sided opaque foliage master; VertexColor.R base->tip, G variation, B sporophyte"
    return mat


def moss_material(maps=None, name="MI_DKR_RockMoss"):
    """Moss cushion shells: pilot 1's recipe on the pilot 2 moss detail, tinted toward the sheet's bright
    yellow-green moss (pilot 1's read dark olive)."""
    old = rm1.PARAMS["MossTint"]
    rm1.PARAMS["MossTint"] = MOSS_SHELL_TINT
    try:
        m = bpy.data.materials.get(name)
        if m is not None and m.get("pilot") == "2f1b":
            return m                               # shared by every rock in the file: never remove it
        if m is not None:
            m.name = name + "_pilot1_old"
        m = rm1.moss_material({"MOSS": TEXS / "T_DKR_MossDetail_BC.png"}, name=name)
        m["pilot"] = "2f1b"
        return m
        return rm1.moss_material({"MOSS": TEXS / "T_DKR_MossDetail_BC.png"}, name=name)
    finally:
        rm1.PARAMS["MossTint"] = old


def grass_material(name="MI_DKR_GrassTuft"):
    return rm1.grass_material(name)
