"""DojoLab SHOWCASE step (pythonscript commandlet, -nullrhi): the kit materials, built here and only here.

Masters in /Game/DojoKit/Materials/Masters, rebuilt from scratch every run so the graphs always equal this file. Each is
the Unreal side of the kits' own Blender materials (build_kit1.py build_material, build_ground_kit.py, the prop builders):
  M_DJ_K1_Master          kit 1 on UV0: BC x Tint, ORM, N (DirectX); grime = vertex G x world noise (Blender Noise on
                          position x (7, 7, 0.35), scale 2) x Grime -> multiply toward Grime Colour; moss = vertex R x
                          the world-projected moss mask (box, 1.3 / m) mapped 0.10-0.40 -> #56613A; crest = vertex R:
                          roughness x (1 - 0.38 Crest R), metallic + 0.30 Crest R (the round-tile sheen)
  M_DJ_K1World_Master     kit 1 plaster / earth core: BC and ORM world-aligned (triplanar |N|^6 blend, tile 4 m) as the
                          Blender material, so a wall of any height or length stays undistorted; grime as above
  Round 3 (2026-09-28, look pass): every library and ground master ends in G.look() (Saturation, ValueMult; the
  library masters also TopBleach); M_DJ_Ground_Master fades its normal with PixelDepth (NormalFade*). Values:
  Scripts/dojo/showcase/look_r3.py through layout_showcase.json.
  M_DJ_Ground_Master      kit 2 on UV0: macro variation (T_DKG_Macro_M on world XY / 32 m: albedo x (1 + tint (R-.5) 2)
                          (1 - dirt max(B-.5, 0) 2), roughness + rough (G-.5) 2); granite: 'Wear' vertex R edge dark
                          (wear_dark + R (1 - wear_dark)), crown gloss (roughness - k R), per-object tone and hue
                          (Blender Object Info Random -> a hash of the actor position: the kit's pieces are actors)
  M_DJ_GroundXY_Master    gravel / coarse gravel / soil sampled on world XY / 4 m (+ macro): panels join seamlessly
  M_DJ_BedBlend_Master    gravel -> soil by vertex R, height-blended by the gravel's luminance (smoothstep 0.4-0.6)
  M_DJ_Dressing_Master    tufts / pebbles: base colour = vertex colour, two-sided
  M_DJ_Prop_Master        props on UV0: BC x Tint (x AO when AO To Base), ORM, N; the training kit's 'Wear' vertex
                          colour (R grime, G edge wear -> bleached timber / bare iron, B ground dust) with its amounts
  M_DJ_PropMasked_Master  masked two-sided (the AC fan grille): opacity mask = BC alpha
  M_DJ_EmissiveTex_Master emissive = BC x Emissive Intensity (lantern panes, lamp glass, vending display); opaque
  M_DJ_Flat_Master        flat colour, roughness, metallic, specular
  M_DJ_EmissiveFlat_Master flat colour + Emissive Colour x Emissive Intensity (kit-1 lamp glow, bulbs, buttons)
Emissive = Blender strength x K_LUX (100, the armory's photometric factor), carried in layout_showcase.json.
Instances: one MaterialInstanceConstant per slot name in its kit's Materials folder, with the recipe from
layout_showcase.json; every imported kit mesh then gets, per slot, the instance named like the slot (the grey-box slots
of the drum-less pavilion take the existing M_DGB_* instances). Result: WorkFiles/dojo/build/unreal/showcase/materials.json
"""
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unreal  # noqa: E402
import dj_sc_common as S  # noqa: E402

EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
MP = unreal.MaterialProperty
ST = unreal.MaterialSamplerType
L = S.load()
# sampler defaults (any layout texture of the right kind; round 2: the shared library's maps)
DEF_TEX = {"BC": "T_DJ_TimberDark_BC", "ORM": "T_DJ_TimberDark_ORM", "N": "T_DJ_TimberDark_N", "M": "T_DJ_WearMask_M"}
DUST_LIN = tuple((c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4) for c in (0.46, 0.41, 0.35))


def lc(v):
    v = list(v) + [1.0] * (4 - len(v))
    return unreal.LinearColor(*[float(x) for x in v[:4]])


def get_or_create(path, cls, factory):
    if EAL.does_asset_exist(path):
        a = unreal.load_asset(path)
        if not isinstance(a, cls):
            raise TypeError(f"{path} exists as {type(a).__name__}, not {cls.__name__}: refusing to touch it")
        return a, False
    folder, name = path.rsplit("/", 1)
    a = AT.create_asset(name, folder, cls, factory)
    if a is None:
        raise RuntimeError(f"could not create {path}")
    return a, True


class G:
    def __init__(self, mat):
        self.m, self.n = mat, 0

    def node(self, cls, **props):
        self.n += 1
        e = MEL.create_material_expression(self.m, cls, -400 - 260 * (self.n // 10), 140 * (self.n % 10))
        for k, v in props.items():
            e.set_editor_property(k, v)
        return e

    def link(self, a, a_out, b, b_in):
        if not MEL.connect_material_expressions(a, a_out, b, b_in):
            raise RuntimeError(f"connect {a.get_name()}.{a_out!r} -> {b.get_name()}.{b_in!r} failed")

    def out(self, a, a_out, prop):
        if not MEL.connect_material_property(a, a_out, prop):
            raise RuntimeError(f"connect {a.get_name()}.{a_out!r} -> {prop} failed")

    # values -------------------------------------------------------------------------------------------------------
    def scalar(self, name, v, group="Surface"):
        return (self.node(unreal.MaterialExpressionScalarParameter, parameter_name=name, default_value=float(v), group=group), "")

    def vector(self, name, v, group="Surface"):
        return (self.node(unreal.MaterialExpressionVectorParameter, parameter_name=name, default_value=lc(v), group=group), "")

    def const(self, v):
        return (self.node(unreal.MaterialExpressionConstant, r=float(v)), "")

    def const3(self, v):
        return (self.node(unreal.MaterialExpressionConstant3Vector, constant=lc(v)), "")

    # maths (operands are (node, output) pairs) ----------------------------------------------------------------------
    def _bin(self, cls, a, b):
        e = self.node(cls)
        self.link(a[0], a[1], e, "A")
        self.link(b[0], b[1], e, "B")
        return (e, "")

    def mul(self, a, b):
        return self._bin(unreal.MaterialExpressionMultiply, a, b)

    def add(self, a, b):
        return self._bin(unreal.MaterialExpressionAdd, a, b)

    def sub(self, a, b):
        return self._bin(unreal.MaterialExpressionSubtract, a, b)

    def div(self, a, b):
        return self._bin(unreal.MaterialExpressionDivide, a, b)

    def mx(self, a, b):
        return self._bin(unreal.MaterialExpressionMax, a, b)

    def dot(self, a, b):
        return self._bin(unreal.MaterialExpressionDotProduct, a, b)

    def append(self, a, b):
        return self._bin(unreal.MaterialExpressionAppendVector, a, b)

    def lerp(self, a, b, t):
        e = self.node(unreal.MaterialExpressionLinearInterpolate)
        self.link(a[0], a[1], e, "A")
        self.link(b[0], b[1], e, "B")
        self.link(t[0], t[1], e, "Alpha")
        return (e, "")

    def un(self, cls, src, **props):
        e = self.node(cls, **props)
        self.link(src[0], src[1], e, "")
        return (e, "")

    def sat(self, a):
        return self.un(unreal.MaterialExpressionSaturate, a)

    def mask(self, a, chans):
        return self.un(unreal.MaterialExpressionComponentMask, a, r="R" in chans, g="G" in chans, b="B" in chans,
                       a="A" in chans)

    def pow(self, a, e):
        n = self.node(unreal.MaterialExpressionPower, const_exponent=float(e))
        self.link(a[0], a[1], n, "Base")
        return (n, "")

    def maprange(self, a, lo, hi):
        return self.sat(self.div(self.sub(a, self.const(lo)), self.const(hi - lo)))

    def smoothstep(self, a, lo, hi):
        x = self.maprange(a, lo, hi)
        return self.mul(self.mul(x, x), self.sub(self.const(3.0), self.mul(self.const(2.0), x)))

    # sources ------------------------------------------------------------------------------------------------------
    def tex(self, pname, kind, uv, group="Textures"):
        st = {"BC": ST.SAMPLERTYPE_COLOR, "ORM": ST.SAMPLERTYPE_MASKS, "M": ST.SAMPLERTYPE_MASKS,
              "N": ST.SAMPLERTYPE_NORMAL}[kind]
        t = self.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name=pname, sampler_type=st,
                      texture=unreal.load_asset(S.tex_path(L, DEF_TEX[kind])), group=group)
        if uv is not None:
            self.link(uv[0], uv[1], t, "UVs")
        return t

    def uv0(self, scale_param="UV Scale"):
        tc = (self.node(unreal.MaterialExpressionTextureCoordinate, coordinate_index=0), "")
        return self.mul(tc, self.scalar(scale_param, 1.0, "UV"))

    def wp(self):
        return (self.node(unreal.MaterialExpressionWorldPosition), "")

    def vc(self):
        return self.node(unreal.MaterialExpressionVertexColor)

    def world_xy(self, tile_cm):
        return self.div(self.mask(self.wp(), "RG"), tile_cm)

    def triplanar(self, pname, kind, tile_cm, out="RGB"):
        """Blender's three-axis world projection: X faces (y, z), Y faces (x, z), Z faces (x, y) / tile, weights |N|^6
        (Unreal V runs down and Y is mirrored, so the projected V axes are negated to keep the image upright)."""
        p = self.wp()
        X, Y, Z = self.mask(p, "R"), self.mask(p, "G"), self.mask(p, "B")
        neg = self.const(-1.0)
        uvs = [self.div(self.append(self.mul(Y, neg), self.mul(Z, neg)), tile_cm),
               self.div(self.append(X, self.mul(Z, neg)), tile_cm),
               self.div(self.append(X, Y), tile_cm)]
        nrm = (self.node(unreal.MaterialExpressionVertexNormalWS), "")
        w = self.pow(self.un(unreal.MaterialExpressionAbs, nrm), 6.0)
        ws = [self.mask(w, c) for c in ("R", "G", "B")]
        acc = None
        for uv, wi in zip(uvs, ws):
            s = (self.tex(pname, kind, uv), out)
            term = self.mul(s, wi)
            acc = term if acc is None else self.add(acc, term)
        return self.div(acc, self.add(self.add(ws[0], ws[1]), ws[2]))

    def macro(self, col, rough):
        """kit 2 macro variation, world XY / 32 m."""
        m = self.tex("Macro Map", "M", self.world_xy(self.const(3200.0)))
        half = self.const(0.5)
        two = self.const(2.0)
        tint = self.add(self.const(1.0), self.mul(self.mul(self.scalar("Macro Tint", 0.0, "Macro"),
                                                           self.sub((m, "R"), half)), two))
        dirt = self.sub(self.const(1.0), self.mul(self.mul(self.scalar("Macro Dirt", 0.0, "Macro"),
                                                           self.mx(self.sub((m, "B"), half), self.const(0.0))), two))
        col = self.mul(col, self.mul(tint, dirt))
        rough = self.add(rough, self.mul(self.mul(self.scalar("Macro Rough", 0.0, "Macro"), self.sub((m, "G"), half)), two))
        return col, rough

    def grime_k1(self, col, vc):
        """kit 1: vertex G x noise mask x Grime, multiplied toward Grime Colour (Blender MULTIPLY mix)."""
        pos = self.mul(self.wp(), self.const3((0.07, 0.07, 0.007)))
        nz = self.node(unreal.MaterialExpressionNoise, scale=1.0, levels=4, output_min=0.0, output_max=1.0,
                       quality=1, turbulence=False)
        names = []
        try:
            names = [str(x) for x in MEL.get_material_expression_input_names(nz)]
        except Exception:  # noqa: BLE001
            pass
        for pin in ["Position"] + names + [""]:
            if MEL.connect_material_expressions(pos[0], pos[1], nz, pin):
                break
        else:
            raise RuntimeError(f"noise position pin not found (inputs {names})")
        # the noise only modulates the vertex grime (x 0.75-1.0, half the Blender frequency across): Unreal's simplex noise has a wider spread than
        # Blender's fBm, and the full 0.35-0.65 map-range drew hard vertical stripes over the whole wall (capture r1)
        mask = self.lerp(self.const(0.75), self.const(1.0), self.maprange((nz, ""), 0.35, 0.65))
        fac = self.mul(self.mul((vc, "G"), mask), self.scalar("Grime", 0.0, "Weathering"))
        return self.lerp(col, self.mul(col, self.vector("Grime Colour", (0.40, 0.33, 0.25), "Weathering")), fac)


    # ---- round 2: the shared library's graph (Scripts/dojo/materials/README.md, Blender node group DJ_Wear_v1) ----
    def switch(self, name, a_true, a_false, default=False, group="Switches"):
        e = self.node(unreal.MaterialExpressionStaticSwitchParameter, parameter_name=name, default_value=bool(default),
                      group=group)
        self.link(a_true[0], a_true[1], e, "True")
        self.link(a_false[0], a_false[1], e, "False")
        return (e, "")

    def lib_wear(self, col, rough, vc, m):
        """README 'Wear maths' (== DJ_Wear_v1): R grime, G broken edge wear on narrow bevels, B ground dust."""
        c1 = self.mul(col, self.sub(self.const(1.0), self.mul((vc, "R"), self.const(0.40))))
        e = self.sat(self.mul(self.sub(self.mul((vc, "G"), self.add(self.const(0.35), m)), self.const(0.55)),
                              self.const(2.5)))
        lum = self.dot(c1, self.const3((0.2126, 0.7152, 0.0722)))
        worn = self.mul(self.lerp(lum, c1, self.const(0.65)), self.const(1.30))     # Blender HSV sat 0.65, value 1.30
        c2 = self.lerp(c1, worn, self.mul(e, self.const(0.55)))
        c3 = self.lerp(c2, self.const3(DUST_LIN), self.mul(self.mul((vc, "B"), m), self.const(0.45)))
        r = self.sat(self.add(self.add(rough, self.mul(e, self.const(0.06))), self.mul((vc, "B"), self.const(0.08))))
        return c3, r

    def actor_hash(self):
        """Blender's Object Info Random stand-in: a hash of the actor position (every kit piece is its own actor)."""
        return self.un(unreal.MaterialExpressionFrac, self.mul(self.un(unreal.MaterialExpressionSine, self.dot(
            (self.node(unreal.MaterialExpressionObjectPositionWS), ""), self.const3((0.129898, 0.78233, 0.37719))),
            period=1.0), self.const(43758.5453)))

    def instance_var(self, col):
        h = self.actor_hash()
        gain = self.add(self.const(1.0), self.mul(self.mul(self.scalar("InstanceTint", 0.0, "Variation"),
                                                           self.sub(h, self.const(0.5))), self.const(2.0)))
        hue = self.lerp(self.vector("HueWarm", (1, 1, 1), "Variation"), self.vector("HueCool", (1, 1, 1), "Variation"),
                        self.un(unreal.MaterialExpressionFrac, self.mul(h, self.const(17.31))))
        return self.mul(self.mul(col, gain), hue)

    def lib_colour(self, bc_rgb, vc):
        """BC x Tint, lerp to MeanColour by FlattenToMean (kit 1's footing stone), moss by VertexColor.A (UseMoss)."""
        col = self.mul(bc_rgb, self.vector("Tint", (1, 1, 1)))
        col = self.lerp(col, self.vector("MeanColour", (0.18, 0.18, 0.18), "Variation"),
                        self.scalar("FlattenToMean", 0.0, "Variation"))
        moss = self.lerp(col, self.vector("MossColour", (0.085, 0.095, 0.034), "Variation"), (vc, "A"))
        return self.switch("UseMoss", moss, col)

    def lib_finish(self, col, rough, vc, m):
        cw, rw = self.lib_wear(col, rough, vc, m)
        col = self.switch("UseWear", cw, col)
        rough = self.switch("UseWear", rw, rough)
        col = self.switch("UseInstanceVar", self.instance_var(col), col)
        return self.look(col, top=True), rough

    def look(self, col, top=False):
        """Round 3 (look pass in Unreal, showcase/look_r3.py): Saturation = lerp(luminance, colour) about the pixel's
        own luminance (1 = the texture as authored), x ValueMult; TopBleach: faces turned up (world normal Z) lerp
        toward TopBleachColour x their luminance x 1.25 (sun-bleached timber tops; a tiling map cannot know which face
        is up). Defaults leave the colour unchanged."""
        lum = self.dot(col, self.const3((0.2126, 0.7152, 0.0722)))
        col = self.mul(self.lerp(lum, col, self.scalar("Saturation", 1.0, "Look")), self.scalar("ValueMult", 1.0, "Look"))
        if top:
            nz = self.sat(self.mask((self.node(unreal.MaterialExpressionVertexNormalWS), ""), "B"))
            k = self.mul(self.smoothstep(nz, 0.55, 0.95), self.scalar("TopBleach", 0.0, "Look"))
            bleached = self.mul(self.mul(lum, self.const(1.25)), self.vector("TopBleachColour", (1.0, 0.97, 0.92), "Look"))
            col = self.lerp(col, bleached, k)
        return col

    def triplanar_normal_ws(self, pname, tile_cm):
        """World-space normal from a DirectX tangent map on the three world projections of triplanar() (same UVs):
        n = tx dP/du + ty dP/dv + tz sign(N.axis) axis per projection (the height-gradient reading, independent of
        the projection's handedness), blended by |N|^6 and normalised."""
        p = self.wp()
        X, Y, Z = self.mask(p, "R"), self.mask(p, "G"), self.mask(p, "B")
        neg = self.const(-1.0)
        uvs = [self.div(self.append(self.mul(Y, neg), self.mul(Z, neg)), tile_cm),
               self.div(self.append(X, self.mul(Z, neg)), tile_cm),
               self.div(self.append(X, Y), tile_cm)]
        nrm = (self.node(unreal.MaterialExpressionVertexNormalWS), "")
        w = self.pow(self.un(unreal.MaterialExpressionAbs, nrm), 6.0)
        ws = [self.mask(w, c) for c in ("R", "G", "B")]
        sg = [self.un(unreal.MaterialExpressionSign, self.mask(nrm, c)) for c in ("R", "G", "B")]
        acc = None
        for k, (uv, wi) in enumerate(zip(uvs, ws)):
            t = self.tex(pname, "N", uv)
            tx, ty, tz = (t, "R"), (t, "G"), (t, "B")
            tzs = self.mul(tz, sg[k])
            if k == 0:
                v = self.append(self.append(tzs, self.mul(tx, neg)), self.mul(ty, neg))
            elif k == 1:
                v = self.append(self.append(tx, tzs), self.mul(ty, neg))
            else:
                v = self.append(self.append(tx, ty), tzs)
            term = self.mul(v, wi)
            acc = term if acc is None else self.add(acc, term)
        return self.un(unreal.MaterialExpressionNormalize, acc)


def reset(mat, blend=unreal.BlendMode.BLEND_OPAQUE, two_sided=False):
    MEL.delete_all_material_expressions(mat)
    mat.set_editor_property("blend_mode", blend)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    mat.set_editor_property("two_sided", two_sided)
    mat.set_editor_property("use_material_attributes", False)
    for k in ("used_with_nanite", "used_with_static_lighting"):
        try:
            mat.set_editor_property(k, k == "used_with_nanite")
        except Exception:  # noqa: BLE001
            pass


def tint(g, col):
    return g.mul(col, g.vector("Tint", (1, 1, 1)))


def build_k1(mat):
    reset(mat)
    g = G(mat)
    uv = g.uv0()
    bc, orm, nm = g.tex("Base Colour Map", "BC", uv), g.tex("ORM Map", "ORM", uv), g.tex("Normal Map", "N", uv)
    vc = g.vc()
    col = g.grime_k1(tint(g, (bc, "RGB")), vc)
    moss = g.triplanar("Moss Mask", "M", g.const(100.0 / 1.3), out="R")
    mf = g.mul(g.maprange(g.mul((vc, "R"), moss), 0.10, 0.40), g.scalar("Moss", 0.0, "Weathering"))
    col = g.lerp(col, g.vector("Moss Colour", (0.0931, 0.1195, 0.0423), "Weathering"), mf)   # #56613A linear
    crest = g.mul((vc, "R"), g.scalar("Crest", 0.0, "Weathering"))
    g.out(col[0], col[1], MP.MP_BASE_COLOR)
    g.out(orm, "R", MP.MP_AMBIENT_OCCLUSION)
    r = g.mul((orm, "G"), g.sub(g.const(1.0), g.mul(crest, g.const(0.38))))
    g.out(r[0], r[1], MP.MP_ROUGHNESS)
    m = g.sat(g.add((orm, "B"), g.mul(crest, g.const(0.30))))
    g.out(m[0], m[1], MP.MP_METALLIC)
    g.out(nm, "RGB", MP.MP_NORMAL)


def build_k1_world(mat):
    reset(mat)
    g = G(mat)
    T = g.scalar("Tile cm", 400.0, "UV")
    col = g.triplanar("Base Colour Map", "BC", T)
    orm = g.triplanar("ORM Map", "ORM", T)
    col = g.grime_k1(tint(g, col), g.vc())
    g.out(col[0], col[1], MP.MP_BASE_COLOR)
    for ch, prop in (("R", MP.MP_AMBIENT_OCCLUSION), ("G", MP.MP_ROUGHNESS), ("B", MP.MP_METALLIC)):
        c = g.mask(orm, ch)
        g.out(c[0], c[1], prop)


def build_ground(mat):
    reset(mat)
    g = G(mat)
    uv = g.uv0()
    # round 9 (2026-09-30): the raked sand's regular stripes (static switch UseRakeVar, off = the graph as before, so the
    # other ground instances pay nothing): the UVs wobble by the macro noise on world XY / RakeWarpTile (RakeWarp in UV
    # units, the rake lines run along U), the albedo takes a fine macro-noise grain (GrainAmount on world XY / GrainTile)
    # and the rake normal fades on a low-frequency macro patch (NormalVar on world XY / NormalVarTile): uneven lines
    wm = g.tex("Macro Map", "M", g.world_xy(g.scalar("RakeWarpTile", 400.0, "Rake")))
    half = g.const(0.5)
    uv_w = g.add(uv, g.append(g.mul(g.sub((wm, "R"), half), g.scalar("RakeWarpU", 0.0, "Rake")),
                              g.mul(g.sub((wm, "G"), half), g.scalar("RakeWarp", 0.0, "Rake"))))
    uv = g.switch("UseRakeVar", uv_w, uv, group="Rake")
    bc, orm, nm = g.tex("Base Colour Map", "BC", uv), g.tex("ORM Map", "ORM", uv), g.tex("Normal Map", "N", uv)
    vc = g.vc()
    gm = g.tex("Macro Map", "M", g.world_xy(g.scalar("GrainTile", 30.0, "Rake")))
    grain = g.add(g.const(1.0), g.mul(g.mul(g.sub((gm, "B"), half), g.const(2.0)), g.scalar("GrainAmount", 0.0, "Rake")))
    bc_rgb = g.switch("UseRakeVar", g.mul((bc, "RGB"), grain), (bc, "RGB"), group="Rake")
    col, rough = g.macro(tint(g, bc_rgb), (orm, "G"))
    wd = g.scalar("Wear Dark", 1.0, "Stone")
    wear = g.add(wd, g.mul((vc, "R"), g.sub(g.const(1.0), wd)))
    col = g.mul(col, g.lerp(g.const(1.0), wear, g.scalar("Wear On", 0.0, "Stone")))
    # per-object random (Blender Object Info Random on the instance; here a hash of the actor position)
    h = g.un(unreal.MaterialExpressionFrac, g.mul(g.un(unreal.MaterialExpressionSine, g.dot(
        (g.node(unreal.MaterialExpressionObjectPositionWS), ""), g.const3((0.129898, 0.78233, 0.37719))), period=1.0),
        g.const(43758.5453)))
    gain = g.add(g.const(1.0), g.mul(g.mul(g.scalar("Instance Tint", 0.0, "Stone"), g.sub(h, g.const(0.5))), g.const(2.0)))
    hue = g.lerp(g.vector("Hue Warm", (1, 1, 1), "Stone"), g.vector("Hue Cool", (1, 1, 1), "Stone"),
                 g.un(unreal.MaterialExpressionFrac, g.mul(h, g.const(17.31))))
    hue = g.lerp(g.const3((1, 1, 1)), hue, g.scalar("Hue Var", 0.0, "Stone"))
    col = g.look(g.mul(g.mul(col, gain), hue))
    rough = g.sub(rough, g.mul((vc, "R"), g.scalar("Crown Gloss", 0.0, "Stone")))
    g.out(col[0], col[1], MP.MP_BASE_COLOR)
    g.out(orm, "R", MP.MP_AMBIENT_OCCLUSION)
    g.out(rough[0], rough[1], MP.MP_ROUGHNESS)
    g.out(orm, "B", MP.MP_METALLIC)
    # round 3: the rake normal fades with view distance (the ground track's moire guard, layout_ground.json
    # normal_fade): N = lerp(N, (0, 0, 1), (1 - far) * saturate((PixelDepth - start) / (end - start))); the defaults
    # (far strength 1) leave every other ground material unchanged
    start = g.scalar("NormalFadeStart", 1200.0, "Look")
    fade = g.sat(g.div(g.sub((g.node(unreal.MaterialExpressionPixelDepth), ""), start),
                       g.mx(g.sub(g.scalar("NormalFadeEnd", 3500.0, "Look"), start), g.const(1.0))))
    k = g.mul(fade, g.sub(g.const(1.0), g.scalar("NormalFarStrength", 1.0, "Look")))
    nv = g.tex("Macro Map", "M", g.world_xy(g.scalar("NormalVarTile", 600.0, "Rake")))
    kv = g.mx(k, g.mul(g.sat(g.mul(g.sub((nv, "R"), g.const(0.35)), g.const(2.0))), g.scalar("NormalVar", 0.0, "Rake")))
    k = g.switch("UseRakeVar", kv, k, group="Rake")
    n = g.lerp((nm, "RGB"), g.const3((0.0, 0.0, 1.0)), k)
    g.out(n[0], n[1], MP.MP_NORMAL)


def build_ground_xy(mat):
    reset(mat)
    g = G(mat)
    uv = g.world_xy(g.scalar("Tile cm", 400.0, "UV"))
    bc, orm, nm = g.tex("Base Colour Map", "BC", uv), g.tex("ORM Map", "ORM", uv), g.tex("Normal Map", "N", uv)
    col, rough = g.macro(tint(g, (bc, "RGB")), (orm, "G"))
    col = g.look(col)
    g.out(col[0], col[1], MP.MP_BASE_COLOR)
    g.out(orm, "R", MP.MP_AMBIENT_OCCLUSION)
    g.out(rough[0], rough[1], MP.MP_ROUGHNESS)
    g.out(orm, "B", MP.MP_METALLIC)
    g.out(nm, "RGB", MP.MP_NORMAL)


def build_bedblend(mat):
    reset(mat)
    g = G(mat)
    uv = g.world_xy(g.scalar("Tile cm", 400.0, "UV"))
    gb, go, gn = g.tex("Gravel BC", "BC", uv), g.tex("Gravel ORM", "ORM", uv), g.tex("Gravel N", "N", uv)
    sb, so, sn = g.tex("Soil BC", "BC", uv), g.tex("Soil ORM", "ORM", uv), g.tex("Soil N", "N", uv)
    lum = g.dot((gb, "RGB"), g.const3((0.2126, 0.7152, 0.0722)))
    t = g.smoothstep(g.add((g.vc(), "R"), g.mul(g.scalar("Blend Contrast", 0.35, "Blend"), g.sub(g.const(0.5), lum))),
                     0.4, 0.6)
    col = g.lerp((gb, "RGB"), (sb, "RGB"), t)
    orm = g.lerp((go, "RGB"), (so, "RGB"), t)
    col, rough = g.macro(col, g.mask(orm, "G"))
    col = g.look(col)
    g.out(col[0], col[1], MP.MP_BASE_COLOR)
    a = g.mask(orm, "R")
    g.out(a[0], a[1], MP.MP_AMBIENT_OCCLUSION)
    g.out(rough[0], rough[1], MP.MP_ROUGHNESS)
    n = g.lerp((gn, "RGB"), (sn, "RGB"), t)
    g.out(n[0], n[1], MP.MP_NORMAL)


def build_dressing(mat):
    reset(mat, two_sided=True)
    g = G(mat)
    c = g.mask((g.vc(), ""), "RGB")
    g.out(c[0], c[1], MP.MP_BASE_COLOR)
    r = g.scalar("Roughness", 0.78)
    g.out(r[0], r[1], MP.MP_ROUGHNESS)


def build_prop(mat, masked=False):
    reset(mat, blend=unreal.BlendMode.BLEND_MASKED if masked else unreal.BlendMode.BLEND_OPAQUE, two_sided=masked)
    g = G(mat)
    uv = g.uv0()
    bc, orm, nm = g.tex("Base Colour Map", "BC", uv), g.tex("ORM Map", "ORM", uv), g.tex("Normal Map", "N", uv)
    base = g.mul(tint(g, (bc, "RGB")), g.lerp(g.const(1.0), (orm, "R"), g.scalar("AO To Base", 0.0)))
    if masked:
        g.out(bc, "A", MP.MP_OPACITY_MASK)
        g.out(base[0], base[1], MP.MP_BASE_COLOR)
        g.out(orm, "R", MP.MP_AMBIENT_OCCLUSION)
        g.out(orm, "G", MP.MP_ROUGHNESS)
        g.out(orm, "B", MP.MP_METALLIC)
        g.out(nm, "RGB", MP.MP_NORMAL)
        return
    vc = g.vc()
    gf = g.mul((vc, "R"), g.scalar("VC Grime", 0.0, "Weathering"))
    df = g.mul((vc, "B"), g.scalar("VC Dust", 0.0, "Weathering"))
    wf = g.mul((vc, "G"), g.scalar("VC Wear", 0.0, "Weathering"))
    lum = g.dot(base, g.const3((0.2126, 0.7152, 0.0722)))
    bleach = g.sat(g.mul(g.lerp(lum, base, g.const(0.72)), g.const(2.1)))          # Blender HSV: sat 0.72, value 2.1
    bare = g.lerp(base, g.vector("Worn Colour", (0.30, 0.29, 0.27), "Weathering"), g.const(0.6))
    worn = g.lerp(bleach, bare, g.scalar("Worn Metal", 0.0, "Weathering"))
    col = g.lerp(base, g.vector("Grime Colour", (0.012, 0.008, 0.005), "Weathering"), gf)
    col = g.lerp(col, g.vector("Dust Colour", (0.16, 0.13, 0.10), "Weathering"), df)
    col = g.lerp(col, worn, wf)
    rough = g.sub(g.add((orm, "G"), g.mul((vc, "R"), g.scalar("Grime Rough", 0.0, "Weathering"))),
                  g.mul((vc, "G"), g.scalar("Wear Rough", 0.0, "Weathering")))
    g.out(col[0], col[1], MP.MP_BASE_COLOR)
    g.out(orm, "R", MP.MP_AMBIENT_OCCLUSION)
    g.out(rough[0], rough[1], MP.MP_ROUGHNESS)
    g.out(orm, "B", MP.MP_METALLIC)
    g.out(nm, "RGB", MP.MP_NORMAL)


def build_emissive_tex(mat):
    reset(mat)
    g = G(mat)
    uv = g.uv0()
    bc, orm, nm = g.tex("Base Colour Map", "BC", uv), g.tex("ORM Map", "ORM", uv), g.tex("Normal Map", "N", uv)
    g.out(bc, "RGB", MP.MP_BASE_COLOR)
    g.out(orm, "R", MP.MP_AMBIENT_OCCLUSION)
    g.out(orm, "G", MP.MP_ROUGHNESS)
    g.out(orm, "B", MP.MP_METALLIC)
    g.out(nm, "RGB", MP.MP_NORMAL)
    e = g.mul((bc, "RGB"), g.scalar("Emissive Intensity", 1.0, "Emission"))
    g.out(e[0], e[1], MP.MP_EMISSIVE_COLOR)


def build_flat(mat):
    reset(mat)
    g = G(mat)
    for name, v, prop in (("Base Colour", None, MP.MP_BASE_COLOR), ("Roughness", 0.5, MP.MP_ROUGHNESS),
                          ("Metallic", 0.0, MP.MP_METALLIC), ("Specular", 0.5, MP.MP_SPECULAR)):
        n = g.vector(name, (0.5, 0.5, 0.5)) if v is None else g.scalar(name, v)
        g.out(n[0], n[1], prop)


def build_emissive_flat(mat):
    reset(mat)
    g = G(mat)
    b = g.vector("Base Colour", (0.5, 0.5, 0.5))
    g.out(b[0], b[1], MP.MP_BASE_COLOR)
    r = g.scalar("Roughness", 0.4)
    g.out(r[0], r[1], MP.MP_ROUGHNESS)
    # round 6: Specular (default 0.5 = the old implicit value): the far ridge rings can drop the sky-Fresnel crest rim
    sp = g.scalar("Specular", 0.5)
    g.out(sp[0], sp[1], MP.MP_SPECULAR)
    e = g.mul(g.vector("Emissive Colour", (1, 1, 1), "Emission"), g.scalar("Emissive Intensity", 1.0, "Emission"))
    g.out(e[0], e[1], MP.MP_EMISSIVE_COLOR)


def flat_normal(g, nm_rgb):
    return g.lerp(g.const3((0.0, 0.0, 1.0)), nm_rgb, g.scalar("NormalStrength", 1.0))


def build_lib_opaque(mat):
    """M_DJ_Lib_Opaque (README): UV0 in tile units, every material at scale 1."""
    reset(mat)
    g = G(mat)
    uv = (g.node(unreal.MaterialExpressionTextureCoordinate, coordinate_index=0), "")
    bc, orm, nm = g.tex("BC", "BC", uv), g.tex("ORM", "ORM", uv), g.tex("N", "N", uv)
    vc = g.vc()
    m = (g.tex("WearMask", "M", g.mul(uv, g.mask(g.vector("TileM", (4, 4, 0, 0), "Weathering"), "RG"))), "R")
    col = g.lib_colour((bc, "RGB"), vc)
    rough = g.mul((orm, "G"), g.scalar("RoughMult", 1.0))
    col, rough = g.lib_finish(col, rough, vc, m)
    g.out(col[0], col[1], MP.MP_BASE_COLOR)
    # round 3: AOStrength (1 = the map as baked): the granite set's cavity AO is a black speckle that multiplies all
    # the indirect light, which read as dalmatian spots in shade
    ao = g.lerp(g.const(1.0), (orm, "R"), g.scalar("AOStrength", 1.0, "Look"))
    g.out(ao[0], ao[1], MP.MP_AMBIENT_OCCLUSION)
    g.out(rough[0], rough[1], MP.MP_ROUGHNESS)
    # round 6: MetallicMult (1 = the ORM map as authored): weathered downpipes / gutters are oxide-dull, not bare metal
    # (the Iron set's metallic 0.85 left them reflecting the dark eaves: (8, 6, 6) against the sky-lit plaster)
    mt = g.mul((orm, "B"), g.scalar("MetallicMult", 1.0, "Look"))
    g.out(mt[0], mt[1], MP.MP_METALLIC)
    # round 6: Specular (UE default 0.5 = unchanged for every instance that leaves it): the tile instance lowers it so
    # the warm low sun's specular lobe does not tint the sunlit kawara tan (sunlit tile R/B <= 1.2)
    sp = g.scalar("Specular", 0.5, "Look")
    g.out(sp[0], sp[1], MP.MP_SPECULAR)
    n = flat_normal(g, (nm, "RGB"))
    g.out(n[0], n[1], MP.MP_NORMAL)


def build_lib_triplanar(mat):
    """M_DJ_Lib_Triplanar (README): the same maths world-aligned (TextureSize = tile_m x 100 cm); the WearMask on its
    1 m tile; world-space normal (tangent_space_normal off)."""
    reset(mat)
    mat.set_editor_property("tangent_space_normal", False)
    g = G(mat)
    T = g.scalar("TextureSize", 400.0, "UV")
    vc = g.vc()
    col = g.lib_colour(g.triplanar("BC", "BC", T), vc)
    orm = g.triplanar("ORM", "ORM", T)
    m = g.triplanar("WearMask", "M", g.const(100.0), out="R")
    rough = g.mul(g.mask(orm, "G"), g.scalar("RoughMult", 1.0))
    col, rough = g.lib_finish(col, rough, vc, m)
    g.out(col[0], col[1], MP.MP_BASE_COLOR)
    ao = g.lerp(g.const(1.0), g.mask(orm, "R"), g.scalar("AOStrength", 1.0, "Look"))   # round 3 (as Lib_Opaque)
    g.out(ao[0], ao[1], MP.MP_AMBIENT_OCCLUSION)
    c = g.mask(orm, "B")
    g.out(c[0], c[1], MP.MP_METALLIC)
    g.out(rough[0], rough[1], MP.MP_ROUGHNESS)
    geo = (g.node(unreal.MaterialExpressionVertexNormalWS), "")
    n = g.un(unreal.MaterialExpressionNormalize,
             g.lerp(geo, g.triplanar_normal_ws("N", T), g.scalar("NormalStrength", 1.0)))
    g.out(n[0], n[1], MP.MP_NORMAL)


def build_lib_emissive(mat):
    """M_DJ_Lib_Emissive (README): BaseColor = BC x BaseMult, Emissive = BC x EmissiveIntensity x EmissiveTint."""
    reset(mat)
    g = G(mat)
    uv = (g.node(unreal.MaterialExpressionTextureCoordinate, coordinate_index=0), "")
    bc, orm, nm = g.tex("BC", "BC", uv), g.tex("ORM", "ORM", uv), g.tex("N", "N", uv)
    b = g.mul((bc, "RGB"), g.scalar("BaseMult", 0.25))
    g.out(b[0], b[1], MP.MP_BASE_COLOR)
    g.out(orm, "R", MP.MP_AMBIENT_OCCLUSION)
    r = g.mul((orm, "G"), g.scalar("RoughMult", 1.0))
    g.out(r[0], r[1], MP.MP_ROUGHNESS)
    z = g.const(0.0)
    g.out(z[0], z[1], MP.MP_METALLIC)
    n = flat_normal(g, (nm, "RGB"))
    g.out(n[0], n[1], MP.MP_NORMAL)
    e = g.mul(g.mul((bc, "RGB"), g.scalar("EmissiveIntensity", 1.0, "Emission")),
              g.vector("EmissiveTint", (1, 1, 1), "Emission"))
    e = g.look(e)   # round 3: Saturation / ValueMult on the emission (the amber glass reads less saturated)
    g.out(e[0], e[1], MP.MP_EMISSIVE_COLOR)


def build_decal(mat):
    """Round 5 (2026-09-29): M_DKD_Decal_Master, the dressing track's weathering / moss decals (decals.json 'master'):
    deferred decal, translucent (DBuffer colour + normal + roughness); BaseColor = BC x Tint (then the round-3 look:
    Saturation / ValueMult), Normal = lerp((0, 0, 1), N, NormalStrength), Roughness = ORM.g x RoughMult, Metallic 0,
    Specular 0.5, Opacity = saturate(M.r x Opacity)."""
    MEL.delete_all_material_expressions(mat)
    mat.set_editor_property("material_domain", unreal.MaterialDomain.MD_DEFERRED_DECAL)
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    g = G(mat)
    uv = (g.node(unreal.MaterialExpressionTextureCoordinate, coordinate_index=0), "")
    bc, orm, nm, m = g.tex("BC", "BC", uv), g.tex("ORM", "ORM", uv), g.tex("N", "N", uv), g.tex("M", "M", uv)
    col = g.look(tint(g, (bc, "RGB")))
    g.out(col[0], col[1], MP.MP_BASE_COLOR)
    r = g.sat(g.mul((orm, "G"), g.scalar("RoughMult", 1.0)))
    g.out(r[0], r[1], MP.MP_ROUGHNESS)
    z = g.const(0.0)
    g.out(z[0], z[1], MP.MP_METALLIC)
    sp = g.const(0.5)
    g.out(sp[0], sp[1], MP.MP_SPECULAR)
    n = flat_normal(g, (nm, "RGB"))
    g.out(n[0], n[1], MP.MP_NORMAL)
    o = g.sat(g.mul((m, "R"), g.scalar("Opacity", 1.0)))
    # round 5 fix f1 (CU_R5_MossWallFoot: the moss ended in hard straight cuts at the projection box): an edge feather
    # over the decal's UV border, EdgeFeather = the fade width in UV (0 = off, the previous look)
    ef = g.mx(g.scalar("EdgeFeather", 0.0), g.const(1e-4))
    feather = None
    for ch in ("R", "G"):
        c = g.mask(uv, ch)
        edge = g._bin(unreal.MaterialExpressionMin, c, g.sub(g.const(1.0), c))
        f = g.sat(g.div(edge, ef))
        feather = f if feather is None else g.mul(feather, f)
    o = g.mul(o, feather)
    g.out(o[0], o[1], MP.MP_OPACITY)


MASTERS = {"M_DJ_Lib_Opaque": build_lib_opaque, "M_DJ_Lib_Triplanar": build_lib_triplanar,
           "M_DJ_Lib_Emissive": build_lib_emissive,
           "M_DJ_K1_Master": build_k1, "M_DJ_K1World_Master": build_k1_world, "M_DJ_Ground_Master": build_ground,
           "M_DJ_GroundXY_Master": build_ground_xy, "M_DJ_BedBlend_Master": build_bedblend,
           "M_DJ_Dressing_Master": build_dressing, "M_DJ_Prop_Master": build_prop,
           "M_DJ_PropMasked_Master": lambda m: build_prop(m, masked=True),
           "M_DJ_EmissiveTex_Master": build_emissive_tex, "M_DJ_Flat_Master": build_flat,
           "M_DJ_EmissiveFlat_Master": build_emissive_flat, "M_DKD_Decal_Master": build_decal}


def main():
    t0 = time.time()
    rep = {"engine": unreal.SystemLibrary.get_engine_version(), "masters": {}, "instances": {}, "meshes": {}}
    masters = {}
    wanted = {r["master"] for r in L["materials"].values()}
    for name, fn in MASTERS.items():
        if name not in wanted:      # round 2: only the masters the layout's recipes use (the others stay as they are)
            continue
        e = {}
        try:
            mat, created = get_or_create(f"{S.MASTER_DIR}/{name}", unreal.Material, unreal.MaterialFactoryNew())
            fn(mat)
            MEL.layout_material_expressions(mat)
            MEL.recompile_material(mat)
            e = {"created": created, "expressions": int(MEL.get_num_material_expressions(mat)),
                 "saved": bool(EAL.save_loaded_asset(mat, False))}
            masters[name] = mat
        except Exception:  # noqa: BLE001
            e["error"] = traceback.format_exc()[-2000:]
        rep["masters"][name] = e
    mis = {}
    for name, r in sorted(L["materials"].items()):
        e = {"master": r["master"]}
        try:
            mi, created = get_or_create(f"{r['ue_dir']}/{name}", unreal.MaterialInstanceConstant,
                                        unreal.MaterialInstanceConstantFactoryNew())
            MEL.clear_all_material_instance_parameters(mi)
            MEL.set_material_instance_parent(mi, masters[r["master"]])
            for k, v in r["scalars"].items():
                if k in ("EmissiveIntensity", "Emissive Intensity"):
                    v = float(v) * S.EMISSIVE_SCALE
                MEL.set_material_instance_scalar_parameter_value(mi, k, float(v))
            for k, v in r.get("switches", {}).items():
                MEL.set_material_instance_static_switch_parameter_value(mi, k, bool(v))
            for k, v in r["vectors"].items():
                MEL.set_material_instance_vector_parameter_value(mi, k, lc(v))
            for k, v in r["textures"].items():
                t = unreal.load_asset(S.tex_path(L, v))
                if t is None:
                    raise RuntimeError(f"texture {v} missing")
                MEL.set_material_instance_texture_parameter_value(mi, k, t)
            MEL.update_material_instance(mi)
            sw = {k: bool(MEL.get_material_instance_static_switch_parameter_value(mi, k)) for k in r.get("switches", {})}
            if sw != {k: bool(v) for k, v in r.get("switches", {}).items()}:
                raise RuntimeError(f"static switches read back {sw}, want {r.get('switches')}")
            e.update({"created": created, "readback": {k: round(float(MEL.get_material_instance_scalar_parameter_value(mi, k)), 4)
                                                       for k in r["scalars"]}, "switches": sw,
                      "saved": bool(EAL.save_loaded_asset(mi, False))})
            mis[name] = mi
        except Exception:  # noqa: BLE001
            e["error"] = traceback.format_exc()[-1500:]
        rep["instances"][name] = e
    for piece, p in sorted(L["pieces"].items()):
        if p["kit"] == "greybox":
            continue
        e = {"slots": {}, "unmatched": []}
        try:
            mesh = unreal.load_asset(S.mesh_path(L, piece))
            for i, s in enumerate(mesh.get_editor_property("static_materials")):
                slot = str(s.get_editor_property("material_slot_name"))
                mi = mis.get(slot) or (unreal.load_asset(S.mat_path(L, slot)) if slot.startswith("M_DGB_") else None)
                if mi is None:
                    e["unmatched"].append(slot)
                    continue
                mesh.set_material(i, mi)
                e["slots"][slot] = mi.get_path_name()
            e["saved"] = bool(EAL.save_loaded_asset(mesh, False))
        except Exception:  # noqa: BLE001
            e["error"] = traceback.format_exc()[-1500:]
        rep["meshes"][piece] = e
    rep["errors"] = [f"{sec}:{k}" for sec in ("masters", "instances", "meshes") for k, v in rep[sec].items() if v.get("error")]
    rep["unmatched_slots"] = {k: v["unmatched"] for k, v in rep["meshes"].items() if v.get("unmatched")}
    rep["passed"] = not rep["errors"] and not rep["unmatched_slots"] and len(mis) == len(L["materials"])
    rep["sec"] = round(time.time() - t0, 1)
    S.write_json(S.SC_OUT / "materials.json", rep)
    unreal.log(f"DJ_STEP_DONE sc_materials passed={rep['passed']} masters={len(masters)} instances={len(mis)} "
               f"meshes={len(rep['meshes'])} errors={len(rep['errors'])}")


main()
