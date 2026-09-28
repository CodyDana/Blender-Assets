"""Armory gallery kit, lean build (WorkFiles/armory/ARMORY_PLAN.md v2, sections 3, 5 and 7): the room and the empty
display cases. No items.

Builds every kit piece at the origin (collection "Kit", with UCX_ collision children), an assembled room from one
layout table (collection "Assembly", linked copies of the kit meshes), writes WorkFiles/armory/build/layout.json
(pieces, lights, cameras) for the Unreal assembly, runs the pipeline QA, exports each piece through Scripts/pipeline,
and saves Assets/Armory/ArmoryKit.blend.

Frame: Blender metres, origin = interior south-west corner at floor level, +X across (0-12), +Y along the axis toward
the rear platform (0-16), +Z up. Wall pieces: length along local +X, inner face at local y = 0, thickness toward -Y,
pivot on the inner face at the base.

Building stage (2026-09-27, BUILD_NOTES.md): the room is 12.0 x 16.0 m (user decision), with a 4.0 x 3.0 m entrance, the
user's own emblem on every plinth front, tansu and banner, and the reference-2 dressing (banners, sill ledges with black
vases and red plum branches, rear alcoves with empty upright racks, LED-edged beams, lattice ceiling panels). The display
cases stay empty: no items, stands, mannequins or placeholders.

Run: blender -b --factory-startup --python Scripts/armory/build_armory_kit.py -- [--no-export]
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Scripts"))
from pipeline.export_fbx import export_fbx  # noqa: E402
from pipeline.qa_check import qa_check  # noqa: E402

TEX = ROOT / "Exports" / "ArmoryKit" / "Textures"
EXPORT_DIR = ROOT / "Exports" / "ArmoryKit"
WORK = ROOT / "WorkFiles" / "armory" / "build"
BLEND = ROOT / "Assets" / "Armory" / "ArmoryKit.blend"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
# hero pieces (2026-09-28): --preview-dir DIR builds a TEST copy of the room into DIR (layout.json, reports and
# ArmoryKit_preview.blend there; never the live blend, layout or exports: implies --no-export). With the environment
# variable ARMORY_HERO_ALL=1 every hero module is loaded even while ENABLED = False (the user approves from these renders)
if "--preview-dir" in ARGS:
    WORK = Path(ARGS[ARGS.index("--preview-dir") + 1])
    BLEND = WORK / "ArmoryKit_preview.blend"
    ARGS.append("--no-export")

# --------------------------------------------------------------------------- materials

def srgb_to_lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hexcol(h):
    return tuple(srgb_to_lin(int(h[i:i + 2], 16) / 255.0) for i in (1, 3, 5)) + (1.0,)


# name: (texture set or None, tile size in m (None = unique UV), flat params)
MATERIALS = {
    "M_AK_Timber": ("Timber", 2.0, {}),
    "M_AK_Plaster": ("Plaster", 2.0, {}),
    # look pass: the same plaster set times a flat tint (an MI of the plaster master in Unreal) for the subdued
    # ceiling coffers and the transom grille backs
    "M_AK_PlasterShade": ("Plaster", 2.0, {"tint": 0.30}),
    # building stage: the warm grey-cream plaster panels of the upper rear wall (reference 2), plaster set x 0.55
    "M_AK_PlasterMid": ("Plaster", 2.0, {"tint": 0.30}),   # f1: 0.55 -> 0.30 (reference 2's upper rear wall is dark)
    # look2: back to a 4 m tile of long walnut boards; the floor comes in four UV-offset variants (A-D) laid as a 2 x 2
    # checker, so each 2 m piece shows its own quarter of the 4 m period (fix1's 2 m tile repeated every piece)
    "M_AK_Plank": ("Plank", 4.0, {}),
    "M_AK_Ground": ("Ground", 4.0, {}),
    "M_AK_Mat": ("Mat", None, {}),
    "M_AK_Painting": ("Painting", None, {}),
    "M_AK_Lacquer": (None, 1.0, {"color": "#15120F", "rough": 0.16, "coat": 0.6}),
    "M_AK_Brass": (None, 1.0, {"color": "#B08A4A", "rough": 0.30, "metal": 1.0}),
    "M_AK_Linen": (None, 1.0, {"color": "#D8CDB8", "rough": 0.92}),
    "M_AK_Glass": (None, 1.0, {"glass": True}),
    # f1: 30 -> 12: at 30 the step nosings and halo lines mirrored as stacks of hot lines in every case glass
    "M_AK_LED": (None, 1.0, {"color": "#FFB872", "emit": 12.0}),
    # building r4: hotter, yellower paper (reference 2: the lanterns burn near white; 1.6 / #FF9A40 read peach); albedo
    # kept <= 0.80 (house rule for plaster / paper)
    # f1 (blind judge: lanterns read as white light boxes): amber paper glowing from inside at a third of the strength
    # (was 3.2, #FFB260), and a darker paper albedo so the room light does not wash it to cream
    # f2: the bigger sun patches reach the entry lanterns and washed the paper to cream: a darker paper albedo
    # (#5E4F3C -> #3E3328) and a yellower amber glow (#FFA838 -> #FFB24A, 0.4 -> 0.5; #FF8C28 read salmon-pink), so they
    # read as glowing amber as in reference 2
    "M_AK_Paper": (None, 1.0, {"color": "#3E3328", "emit": 0.5, "emit_color": "#FFB24A"}),
    # f2 (reference 2's lanterns: hot near-white core, deep amber toward the frame; a flat emission tone-maps to one
    # cream tone): the floor-lantern panes use a glow picture on a unique UV per pane (T_AK_LanternPaper), unlit (base
    # colour 0, so no sun or case light washes them), strength 0.40
    "M_AK_LanternPaper": ("LanternPaper", None, {"emit_image": True, "emit": 0.40, "unlit": True}),
    # look pass: warm backlit shoji paper behind the blind lattice panels of the upper walls
    # fix1: emission 0.55 -> 0.06, so the blind panels read as dim screens and only the two real windows per side glow
    # (the review judged the continuous lit band an atrium clerestory)
    "M_AK_Shoji": (None, 1.0, {"color": "#6A5F4E", "emit": 0.06, "emit_color": "#FFD39A"}),
    # fix1: dark case decks and backdrops (black felt, reference 2) and dark niche back boards (walnut)
    # fix1: soft LED for the niche edge lines (a glow on the back board, not a visible tube)
    "M_AK_LEDSoft": (None, 1.0, {"color": "#FFB872", "emit": 0.8}),   # f1: 4.0 -> 0.8 (niche edge lines, subdued)
    # f1 (blind judge blocker 1, supersedes the look2 oxblood felt #4A1715): the case decks and the hero table top are
    # black lacquer, roughness 0.25, as reference 2's decks read near-black; the thin brass deck edge stays
    "M_AK_DeckLacquer": (None, 1.0, {"color": "#0E0C0B", "rough": 0.25}),
    # f1 (blind judge blocker 2): the niche and rack back boards are a dark warm wood, NOT an emissive lightbox; each
    # niche is lit by one warm spot at its top lip, so the light grazes down the panel and falls off toward the counter
    # f2 (blind judge delta 11: reference 2's wall bays have lit CREAM backs above a dark dado): a warm cream board, still
    # not emissive; the spot at the lens under the head lights it hot at the top, falling off toward the counter
    "M_AK_BackBoard": (None, 1.0, {"color": "#7C6446", "rough": 0.8}),   # look3: warmer, dimmer display boards
    # f2 (blind judge delta 8: the rear alcoves flanking the painting glow strongly in reference 2): a softly backlit
    # cream panel behind the empty rack (a low emission; the top spot and the rack wash do the rest)
    "M_AK_AlcoveLit": (None, 1.0, {"color": "#8C7350", "emit": 0.09, "emit_color": "#FFB45C"}),   # look3: rear alcoves measured 0.59 vs 0.37
    # f1 (blind judge delta 12): the plinth under-glow strips are a soft amber line (was the 30-strength M_AK_LED); the
    # pool on the floor comes from the UnderGlow area lights
    "M_AK_LEDGlow": (None, 1.0, {"color": "#FFA24A", "emit": 4.0}),
    # look2: thin dark-bronze glass frames (the brass stays on plinth bands, deck edges and emblem plates)
    "M_AK_Bronze": (None, 1.0, {"color": "#5E4527", "rough": 0.38, "metal": 1.0}),
    # look2: sunlit garden card outside the windows and the door (emissive, casts no shadow)
    "M_AK_Backdrop": ("Backdrop", None, {"emit_image": True, "emit": 8.0}),   # building: 3 -> 5 (bright garden)
    # building stage: the user's emblem as a gold-on-lacquer medallion face (T_AK_Emblem_BC/ORM/N, derived from the
    # T_AK_Emblem mask), the black banner cloth with the gold crest (two-sided in Unreal), the red plum-blossom cards
    # (alpha-masked: Unreal needs a Masked two-sided material), black glazed ceramic for the vases, and a gold backlight
    # behind the ornamental lattices (rear alcove screens, ceiling lattice panels)
    "M_AK_Emblem": ("Emblem", None, {}),
    "M_AK_Banner": ("Banner", None, {"two_sided": True}),
    "M_AK_Plum": ("Plum", None, {"alpha": True, "two_sided": True}),
    "M_AK_Glaze": (None, 1.0, {"color": "#0E0D0C", "rough": 0.12, "coat": 0.8}),
    "M_AK_GoldGlow": (None, 1.0, {"color": "#C8914E", "emit": 0.8, "emit_color": "#FFB35C"}),   # r4: 1.6 -> 1.1; f1: 0.8
    # building stage: the fine warm LED lines on the beam edges and posts (R8, R9); the 30-strength LED blew them out
    "M_AK_LEDLine": (None, 1.0, {"color": "#FFA85A", "emit": 1.6}),
    # building stage: the dim patterned screens flanking the painting (reference 2: dark warm grey, not lit paper)
    "M_AK_ScreenPanel": (None, 1.0, {"color": "#3A332C", "rough": 0.8}),
    # building r3: the closed shoji panes of the three south bays of the west wall (warm glowing paper, blocks the sun)
    "M_AK_ShojiLit": (None, 1.0, {"color": "#CCBC9E", "emit": 0.9, "emit_color": "#FFD9A0"}),
}
# exterior stage (2026-09-27): the courtyard garden, roof, foundation and scenery live in build_armory_exterior.py
# (pieces SM_AKX_*, materials M_AKX_*, textures T_AKX_* from make_exterior_textures.py). The flat garden backdrop cards
# and the plain exterior ground they replace are gone (M_AK_Backdrop, M_AK_Ground, SM_AK_Ext_*).
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_armory_exterior as EXT  # noqa: E402
EXT.setup(globals())
MATERIALS.update(EXT.MATERIALS)
import armory_items as ITEMS  # noqa: E402   items on display, added one at a time (item 1: the shuriken tray)
ITEMS.setup(globals())
MATERIALS.update(ITEMS.MATERIALS)
import armory_hero as HERO  # noqa: E402   hero pieces: detailed replacements for scripted pieces (Scripts/armory/hero)
HERO.setup(globals())
HERO.load()
MATERIALS.update(HERO.MATERIALS)
del MATERIALS["M_AK_Backdrop"], MATERIALS["M_AK_Ground"]
TILE = {k: v[1] for k, v in MATERIALS.items()}


def tex_file(tex, suffix):
    """Texture sets named AKX_* are the exterior's T_AKX_<set>_<suffix>.png; the others T_AK_<set>_<suffix>.png."""
    return TEX / (f"T_{tex}_{suffix}.png" if tex.startswith("AKX_") else f"T_AK_{tex}_{suffix}.png")


def build_material(name):
    tex, _tile, p = MATERIALS[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    if p.get("emit_image"):   # an emissive picture (the garden backdrop): base colour and emission from one BC map
        node = nt.nodes.new("ShaderNodeTexImage")
        node.image = bpy.data.images.load(str(tex_file(tex, "BC")), check_existing=True)
        if p.get("unlit"):   # exterior stage: far scenery is pure emission (its light is painted in), no sun on it
            bsdf.inputs["Base Color"].default_value = (0.0, 0.0, 0.0, 1.0)
        else:
            nt.links.new(node.outputs["Color"], bsdf.inputs["Base Color"])
        nt.links.new(node.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = p["emit"]
        bsdf.inputs["Roughness"].default_value = 1.0
        if p.get("alpha"):   # exterior stage: the alpha-masked tree-line cards
            nt.links.new(node.outputs["Alpha"], bsdf.inputs["Alpha"])
        return mat
    if tex:
        def img(suffix, noncolor):
            node = nt.nodes.new("ShaderNodeTexImage")
            image = bpy.data.images.load(str(tex_file(tex, suffix)), check_existing=True)
            if noncolor:
                image.colorspace_settings.name = "Non-Color"
            node.image = image
            return node
        bc, orm, nrm = img("BC", False), img("ORM", True), img("N", True)
        if "tint" in p:   # flat multiply on the base colour (a scalar parameter on the Unreal MI)
            mul = nt.nodes.new("ShaderNodeVectorMath")
            mul.operation = "MULTIPLY"
            mul.inputs[1].default_value = (p["tint"],) * 3
            nt.links.new(bc.outputs["Color"], mul.inputs[0])
            nt.links.new(mul.outputs["Vector"], bsdf.inputs["Base Color"])
        else:
            nt.links.new(bc.outputs["Color"], bsdf.inputs["Base Color"])
        alpha_out = bc.outputs["Alpha"]
        if p.get("edge_fade"):   # exterior stage: foliage cards fade out edge-on (no bright streaks from thin cards)
            lw = nt.nodes.new("ShaderNodeLayerWeight")
            fade = nt.nodes.new("ShaderNodeMapRange")          # facing 0 (face-on) .. 1 (edge-on) -> 1 .. 0
            fade.inputs["From Min"].default_value = 0.55
            fade.inputs["From Max"].default_value = 0.85
            fade.inputs["To Min"].default_value = 1.0
            fade.inputs["To Max"].default_value = 0.0
            nt.links.new(lw.outputs["Facing"], fade.inputs["Value"])
            am = nt.nodes.new("ShaderNodeMath")
            am.operation = "MULTIPLY"
            nt.links.new(bc.outputs["Alpha"], am.inputs[0])
            nt.links.new(fade.outputs["Result"], am.inputs[1])
            alpha_out = am.outputs[0]
        if p.get("alpha"):   # building stage: alpha-masked cards (plum branches)
            nt.links.new(alpha_out, bsdf.inputs["Alpha"])
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(orm.outputs["Color"], sep.inputs["Color"])
        nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
        nt.links.new(sep.outputs[2], bsdf.inputs["Metallic"])
        # the maps are DirectX (UE); flip green back to OpenGL for Blender's review renders
        sep_n = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(nrm.outputs["Color"], sep_n.inputs["Color"])
        inv = nt.nodes.new("ShaderNodeMath")
        inv.operation = "SUBTRACT"
        inv.inputs[0].default_value = 1.0
        nt.links.new(sep_n.outputs[1], inv.inputs[1])
        comb = nt.nodes.new("ShaderNodeCombineColor")
        nt.links.new(sep_n.outputs[0], comb.inputs[0])
        nt.links.new(inv.outputs[0], comb.inputs[1])
        nt.links.new(sep_n.outputs[2], comb.inputs[2])
        nmap = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(comb.outputs["Color"], nmap.inputs["Color"])
        nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
        if p.get("translucent"):   # exterior stage: leaf cards pass some light (Unreal: two-sided foliage)
            out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
            trl = nt.nodes.new("ShaderNodeBsdfTranslucent")
            nt.links.new(bc.outputs["Color"], trl.inputs["Color"])
            clear = nt.nodes.new("ShaderNodeBsdfTransparent")
            leaf = nt.nodes.new("ShaderNodeMixShader")      # transparent where alpha is 0, translucent leaf elsewhere
            nt.links.new(alpha_out, leaf.inputs[0])
            nt.links.new(clear.outputs[0], leaf.inputs[1])
            nt.links.new(trl.outputs[0], leaf.inputs[2])
            mix = nt.nodes.new("ShaderNodeMixShader")
            mix.inputs[0].default_value = p["translucent"]
            nt.links.new(bsdf.outputs[0], mix.inputs[1])
            nt.links.new(leaf.outputs[0], mix.inputs[2])
            nt.links.new(mix.outputs[0], out.inputs["Surface"])
    elif p.get("glass"):
        bsdf.inputs["Base Color"].default_value = (0.95, 0.97, 0.96, 1)
        bsdf.inputs["Roughness"].default_value = 0.02
        bsdf.inputs["Transmission Weight"].default_value = 1.0
        bsdf.inputs["IOR"].default_value = 1.5
        # look2: thin architectural glass, as Unreal's thin translucent pane renders it: see-through (no refraction, no
        # smoky internal bounces), a Fresnel-weighted mirror reflection on top, and fully transparent to shadow rays
        lp = nt.nodes.new("ShaderNodeLightPath")
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        if "tint" in p:   # hero_shared (optional): a faint see-through colour, hex sRGB (default: clear white)
            tr.inputs["Color"].default_value = hexcol(p["tint"])
        gloss = nt.nodes.new("ShaderNodeBsdfGlossy")
        gloss.inputs["Roughness"].default_value = 0.02
        fres = nt.nodes.new("ShaderNodeFresnel")
        fres.inputs["IOR"].default_value = 1.5
        thin = nt.nodes.new("ShaderNodeMixShader")
        # museum low-iron glass with an anti-reflective feel: a third of the plain Fresnel reflection, so from above the
        # lids do not mirror the dark ceiling and hide the lit decks (reference 2 reads straight into every case)
        kf = nt.nodes.new("ShaderNodeMath")
        kf.operation = "MULTIPLY"
        # f2: 0.18 -> 0.02 (judge delta 10: C5's tall glass mirrored the sunlit courtyard through the entrance; a k = 0 /
        # 0.04 test proved it a reflection, still plain at 0.04 because the sunlit garden is far brighter than the room).
        # 0.02 x Fresnel = 0.1 % face-on, up to 2 % at grazing: museum anti-reflective glass. f1: 0.3 -> 0.18
        kf.inputs[1].default_value = p.get("refl", 0.02)   # hero_shared (optional): the Fresnel reflection factor
        nt.links.new(fres.outputs[0], kf.inputs[0])
        nt.links.new(kf.outputs[0], thin.inputs[0])
        nt.links.new(tr.outputs[0], thin.inputs[1])
        nt.links.new(gloss.outputs[0], thin.inputs[2])
        tr2 = nt.nodes.new("ShaderNodeBsdfTransparent")
        mix = nt.nodes.new("ShaderNodeMixShader")
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        nt.links.new(lp.outputs["Is Shadow Ray"], mix.inputs[0])
        nt.links.new(thin.outputs[0], mix.inputs[1])
        nt.links.new(tr2.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs["Surface"])
    elif "emit" in p:
        bsdf.inputs["Base Color"].default_value = hexcol(p["color"])
        bsdf.inputs["Emission Color"].default_value = hexcol(p.get("emit_color", p["color"]))
        bsdf.inputs["Roughness"].default_value = 0.8
        bsdf.inputs["Emission Strength"].default_value = p["emit"]
    else:
        bsdf.inputs["Base Color"].default_value = hexcol(p["color"])
        bsdf.inputs["Roughness"].default_value = p.get("rough", 0.5)
        bsdf.inputs["Metallic"].default_value = p.get("metal", 0.0)
        if "coat" in p:
            bsdf.inputs["Coat Weight"].default_value = p["coat"]
            bsdf.inputs["Coat Roughness"].default_value = 0.05
    return mat


# --------------------------------------------------------------------------- geometry

class Piece:
    """Collects boxes and prisms, then builds one mesh with tiling UV0, material slots and UCX boxes."""
    count = 0

    def __init__(self, name):
        self.name = name
        self.boxes = []   # (x0, x1, y0, y1, z0, z1, material, uv_axis, unique_face)
        self.cyls = []    # (cx, cy, z0, z1, r, material, sides)
        self.ucx = []     # (x0, x1, y0, y1, z0, z1)
        self.meshes = []  # building stage: free meshes (verts, faces, per-face loop UVs, per-face materials, smooth)

    def box(self, x0, x1, y0, y1, z0, z1, mat, uv=None, unique=None, uvoff=(0.0, 0.0, 0.0)):
        self.boxes.append((x0, x1, y0, y1, z0, z1, mat, uv, unique, uvoff))
        return self

    def cyl(self, cx, cy, z0, z1, r, mat, sides=12):
        self.cyls.append((cx, cy, z0, z1, r, mat, sides))
        return self

    def mesh(self, verts, faces, uvs, mats, smooth=False):
        """Building stage: an arbitrary welded mesh part (discs, lathes, cloth sheets, foliage cards). mats is one
        material name or one per face; uvs is one list of (u, v) per face."""
        if isinstance(mats, str):
            mats = [mats] * len(faces)
        self.meshes.append((verts, faces, uvs, mats, smooth))
        return self

    def col(self, x0, x1, y0, y1, z0, z1):
        self.ucx.append((x0, x1, y0, y1, z0, z1))
        return self

    def build(self, coll):
        mats = []
        bm = bmesh.new()
        uv = bm.loops.layers.uv.new("UV0")

        def mat_index(m):
            if m not in mats:
                mats.append(m)
            return mats.index(m)

        for (x0, x1, y0, y1, z0, z1, m, uv_axis, unique, uvoff) in self.boxes:
            off = {"x": uvoff[0], "y": uvoff[1], "z": uvoff[2]}   # look2: world offset for the floor variants
            # a tiny unique growth per box: abutting boxes overlap instead of sharing coincident vertices
            Piece.count += 1
            g = 0.0003 + (Piece.count % 997) * 2e-6
            x0, x1, y0, y1, z0, z1 = x0 - g, x1 + g, y0 - g, y1 + g, z0 - g, z1 + g
            v = [bm.verts.new(c) for c in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                                           (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
            quads = {"-z": (0, 3, 2, 1), "+z": (4, 5, 6, 7), "-y": (0, 1, 5, 4),
                     "+y": (2, 3, 7, 6), "-x": (3, 0, 4, 7), "+x": (1, 2, 6, 5)}
            ext = {"x": x1 - x0, "y": y1 - y0, "z": z1 - z0}
            idx = mat_index(m)
            tile = TILE.get(m) or 1.0
            for key, q in quads.items():
                f = bm.faces.new([v[i] for i in q])
                f.material_index = idx
                n_axis = key[1]
                plane = [a for a in "xyz" if a != n_axis]
                if uv_axis in plane:
                    ua = uv_axis
                else:
                    ua = max(plane, key=lambda a: ext[a])
                va = [a for a in plane if a != ua][0]
                for loop in f.loops:
                    co = loop.vert.co
                    c = {"x": co.x, "y": co.y, "z": co.z}
                    if unique == key:  # unique 0-1 mapping over this face (painting, mat)
                        lo = {"x": x0, "y": y0, "z": z0}
                        u_val = (c[ua] - lo[ua]) / ext[ua]
                        v_val = (c[va] - lo[va]) / ext[va]
                        if key in ("+y", "-x"):
                            u_val = 1.0 - u_val   # read left-to-right from outside the face
                        loop[uv].uv = (u_val, v_val)
                    elif unique:
                        loop[uv].uv = (0.001, 0.001)  # hidden faces of a uniquely mapped box sample one texel
                    else:
                        loop[uv].uv = ((c[ua] + off[ua]) / tile, (c[va] + off[va]) / tile)
        for (cx, cy, z0, z1, r, m, sides) in self.cyls:
            idx = mat_index(m)
            ring0, ring1 = [], []
            for i in range(sides):
                a = 2 * math.pi * i / sides
                ring0.append(bm.verts.new((cx + r * math.cos(a), cy + r * math.sin(a), z0)))
                ring1.append(bm.verts.new((cx + r * math.cos(a), cy + r * math.sin(a), z1)))
            c0 = bm.verts.new((cx, cy, z0))
            c1 = bm.verts.new((cx, cy, z1))
            faces = []
            for i in range(sides):
                j = (i + 1) % sides
                faces.append(bm.faces.new([ring0[i], ring0[j], ring1[j], ring1[i]]))
                faces.append(bm.faces.new([c0, ring0[j], ring0[i]]))   # caps as fans: no n-gons
                faces.append(bm.faces.new([c1, ring1[i], ring1[j]]))
            for f in faces:
                f.material_index = idx
                for loop in f.loops:
                    loop[uv].uv = (loop.vert.co.x, loop.vert.co.y)
        for verts, faces, uvs, fmats, smooth in self.meshes:
            vs = [bm.verts.new(v) for v in verts]
            sm = smooth if isinstance(smooth, list) else [smooth] * len(faces)   # hero pieces: per-face smooth
            for f_idx, fu, m, s_ in zip(faces, uvs, fmats, sm):
                f = bm.faces.new([vs[i] for i in f_idx])
                f.material_index = mat_index(m)
                f.smooth = s_
                for loop, (u_, v_) in zip(f.loops, fu):
                    loop[uv].uv = (u_, v_)
        bm.normal_update()
        mesh = bpy.data.meshes.new(self.name)
        bm.to_mesh(mesh)
        bm.free()
        for m in mats:
            mesh.materials.append(bpy.data.materials[m])
        obj = bpy.data.objects.new(self.name, mesh)
        coll.objects.link(obj)
        add_uv1(obj)
        for i, (x0, x1, y0, y1, z0, z1) in enumerate(self.ucx or [bounds_of(self)]):
            hull = bpy.data.meshes.new(f"UCX_{self.name}_{i:02d}")
            hb = bmesh.new()
            bmesh.ops.create_cube(hb, size=1.0)
            for vert in hb.verts:
                vert.co.x = x0 + (vert.co.x + 0.5) * (x1 - x0)
                vert.co.y = y0 + (vert.co.y + 0.5) * (y1 - y0)
                vert.co.z = z0 + (vert.co.z + 0.5) * (z1 - z0)
            hb.to_mesh(hull)
            hb.free()
            h = bpy.data.objects.new(f"UCX_{self.name}_{i:02d}", hull)
            coll.objects.link(h)
            h.parent = obj
            h.hide_render = True
            h.display_type = "WIRE"
        return obj


def bounds_of(piece):
    xs = [b[0] for b in piece.boxes] + [b[1] for b in piece.boxes]
    ys = [b[2] for b in piece.boxes] + [b[3] for b in piece.boxes]
    zs = [b[4] for b in piece.boxes] + [b[5] for b in piece.boxes]
    for verts, *_ in piece.meshes:
        xs += [v[0] for v in verts]
        ys += [v[1] for v in verts]
        zs += [v[2] for v in verts]
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))


def add_uv1(obj):
    """UV1 lightmap channel (Fab rule): Blender's lightmap pack, which never overlaps and stays in 0-1."""
    me = obj.data
    me.uv_layers.new(name="UV1")
    me.uv_layers.active_index = 1
    with bpy.context.temp_override(active_object=obj, object=obj, selected_objects=[obj],
                                   selected_editable_objects=[obj]):
        bpy.ops.uv.lightmap_pack(PREF_CONTEXT="ALL_FACES", PREF_PACK_IN_ONE=False, PREF_NEW_UVLAYER=False,
                                 PREF_BOX_DIV=12, PREF_MARGIN_DIV=0.2)
    me.uv_layers.active_index = 0


# --------------------------------------------------------------------------- the kit

T, P, PL, LQ, BR, LI, GL, LED, PA = ("M_AK_Timber", "M_AK_Plaster", "M_AK_Plank", "M_AK_Lacquer", "M_AK_Brass",
                                     "M_AK_Linen", "M_AK_Glass", "M_AK_LED", "M_AK_Paper")
SH, PS, FE, BB, LS = "M_AK_Shoji", "M_AK_PlasterShade", "M_AK_DeckLacquer", "M_AK_BackBoard", "M_AK_LEDSoft"   # f1: decks are lacquer
BZ = "M_AK_Bronze"
EM, BN, PM, GZ, GG = "M_AK_Emblem", "M_AK_Banner", "M_AK_Plum", "M_AK_Glaze", "M_AK_GoldGlow"
LL = "M_AK_LEDLine"
LG = "M_AK_LEDGlow"   # f1: soft amber plinth under-glow strips
# fix1: door and window rough openings are widened by the 3.1 cm lining so the CLEAR openings are the plan's
# 150 x 200 (door) and 150 x 90 at sill +350 (windows). Piece-local: clear X 0.25-1.75, lining 0.031
LIN = 0.031
# building r2: 150 x 120 clear opening, world +2.65 to +3.85 (reference 2: big windows). f1: head +3.85 -> +4.10 (150 x 145):
# reference 2's windows are about as tall as the niche band under them, and the judge asked for larger, hotter windows;
# the taller opening also lengthens each sun patch (1.45 / tan 28 deg = 2.7 m along the ray)
WIN_SILL, WIN_HEAD = 0.15, 1.60
RO0, RO1 = 0.25 - LIN, 1.75 + LIN   # rough opening 0.219-1.781 (156.2 cm)
NICHE_LENS_Y = 0.20                  # f1: the niche downlight lens, 20 cm in front of the back board
# f2: niche bays over a dark dado (hall: floor to +2.40, counter +0.85; platform: +0.60 to +2.50, counter +1.00)
NICHE_H_FLOOR, NICHE_DADO_FLOOR, NICHE_H_PLAT, NICHE_DADO_PLAT = 2.40, 0.85, 1.90, 0.40
ROOM_W, ROOM_L, CEIL = 12.0, 16.0, 4.80   # building stage (user decision 2026-09-27): 12.0 x 16.0 m interior
ENTRY_X = (4.0, 8.0)                      # building stage: 4.0 m wide x 3.0 m tall clear entrance, centred
# f1: 3.0 -> 3.65 m. Reference 2's establishing view is a level (shift-lens) camera at about +3.4 m, 1.5 m in front of the
# entrance (landmark fit, BUILD_NOTES f1); the lintel must clear the top of that frame (computed: needs >= 3.61)
ENTRY_H = 3.65
PLAT_Y = 13.45                            # platform front edge (+0.60); steps Y 12.70-13.45
# newel lanterns (USER DECISION 2026-09-28, "follow the armory reference"): the slim newel posts at the stair foot
# (SM_AK_LanternPedestal, directly in front of the heavy posts) carry a small lantern each, as reference 2 shows. The
# newel body stays 0.85 m (brass cap block at the top); a 2 cm dark top plate (0.30 m square) over it is what the lantern
# stands on: NEWEL_TOP. The lantern is a hero piece (SM_AK_H_NewelLantern, hero_lantern_vase.py), placed by its
# instances() and lit by its lights() (armory_hero.lights()), so a --no-hero build keeps the bare newels.
NEWEL_X, NEWEL_Y, NEWEL_TOP = (3.30, 8.70), PLAT_Y - 0.20, 0.87
NEWEL_PLATE = 0.15                        # half width of the newel's top plate (build 3: 0.28 -> 0.30 m, seats the 0.28 m lantern)
PAINT_H, PAINT_Z = 2.3, 1.50              # building r2: painting 2.4 x 2.3 m, Z 1.50-3.80
CASES = {  # type: (width along local X, depth along local Y, plinth height, glass height)
    # building r2, fitted to reference 2 through the C1 camera (BUILD_NOTES): the front case is a low plinth under tall
    # glass (plinth top +0.50, glass top +1.45), the kasa case a low base under tall glass; the hero is a low two-tier
    # lacquer TABLE (no glass: G = 0)
    "L": (1.8, 1.3, 0.50, 0.95), "LN": (1.6, 1.0, 0.45, 0.75), "M": (1.8, 1.2, 0.70, 0.55),
    "S": (1.4, 1.1, 0.90, 0.45), "Tall": (1.5, 1.1, 0.50, 1.70), "Hero": (2.4, 0.9, 0.52, 0.0),
}


# ---- building stage: mesh generators (welded parts for Piece.mesh; outward winding checked by hand, see notes)

def disc_y(cx, y0, cz, r, depth, face_mat, rim_mat, sides=32, facing=-1):
    """A thin medallion disc whose axis is Y. Its show face (UV 0-1 over the disc, read left to right from outside)
    sits at y0 and faces -Y (facing=-1) or +Y (facing=+1); the body runs `depth` back into the surface."""
    ring_f, ring_b = [], []
    for i in range(sides):
        a = 2 * math.pi * i / sides
        ring_f.append((cx + r * math.cos(a), y0, cz + r * math.sin(a)))
        ring_b.append((cx + r * math.cos(a), y0 + depth, cz + r * math.sin(a)))
    verts = ring_f + ring_b + [(cx, y0, cz), (cx, y0 + depth, cz)]
    cf, cb = 2 * sides, 2 * sides + 1
    faces, uvs, mats = [], [], []
    uvd = lambda v: (0.5 + (v[0] - cx) / (2 * r), 0.5 + (v[2] - cz) / (2 * r))
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((cf, i, j))                                   # front fan, normal -Y
        uvs.append([uvd(verts[cf]), uvd(verts[i]), uvd(verts[j])])
        mats.append(face_mat)
        faces.append((cb, sides + j, sides + i))                   # back fan, normal +Y
        uvs.append([(0.01, 0.01)] * 3)
        mats.append(rim_mat)
        faces.append((i, sides + i, sides + j, j))                 # rim, outward
        uvs.append([(i / sides, 0), (i / sides, 0.02), (j / sides, 0.02), (j / sides, 0)])
        mats.append(rim_mat)
    if facing > 0:   # rotate 180 deg about the vertical axis through (cx, y0): a rotation keeps the winding
        verts = [(2 * cx - x, 2 * y0 - y, z) for (x, y, z) in verts]
    return verts, faces, uvs, mats


def lathe(profile, sides=24, cx=0.0, cy=0.0):
    """Surface of revolution about Z from a (r, z) profile. A point with r == 0 becomes a single pole vertex. The
    profile runs up the outside, over the lip and down the inside, so every face winds outward (or into the mouth)."""
    verts, rings = [], []
    for (r, z) in profile:
        if r == 0:
            verts.append((cx, cy, z))
            rings.append([len(verts) - 1] * sides)
        else:
            idx = []
            for i in range(sides):
                a = 2 * math.pi * i / sides
                verts.append((cx + r * math.cos(a), cy + r * math.sin(a), z))
                idx.append(len(verts) - 1)
            rings.append(idx)
    faces, uvs = [], []
    lens = [0.0]
    for k in range(1, len(profile)):
        lens.append(lens[-1] + math.dist(profile[k - 1], profile[k]))
    for k in range(len(profile) - 1):
        a, b = rings[k], rings[k + 1]
        for i in range(sides):
            j = (i + 1) % sides
            quad = [a[i], a[j], b[j], b[i]]
            uv = [(i / sides, lens[k]), (j / sides, lens[k]), (j / sides, lens[k + 1]), (i / sides, lens[k + 1])]
            if profile[k][0] == 0:
                faces.append((a[i], b[j], b[i]))
                uvs.append([uv[0], uv[2], uv[3]])
            elif profile[k + 1][0] == 0:
                faces.append((a[i], a[j], b[i]))
                uvs.append([uv[0], uv[1], uv[3]])
            else:
                faces.append(tuple(quad))
                uvs.append(uv)
    return verts, faces, uvs


def card(angle_deg, width, z0, z1, cx=0.0, cy=0.0):
    """A vertical foliage card through (cx, cy), turned angle_deg about Z, UV 0-1 over the card."""
    a = math.radians(angle_deg)
    dx, dy = math.cos(a) * width / 2, math.sin(a) * width / 2
    verts = [(cx - dx, cy - dy, z0), (cx + dx, cy + dy, z0), (cx + dx, cy + dy, z1), (cx - dx, cy - dy, z1)]
    return verts, [(0, 1, 2, 3)], [[(0, 0), (1, 0), (1, 1), (0, 1)]]


def cloth(x0, x1, z0, z1, nu=16, nv=4, amp=0.012, period=0.14):
    """A hanging cloth sheet facing -Y with soft vertical folds, UV 0-1 (read left to right from the front)."""
    verts, faces, uvs = [], [], []
    for j in range(nv + 1):
        for i in range(nu + 1):
            x = x0 + (x1 - x0) * i / nu
            verts.append((x, amp * math.sin(2 * math.pi * (x - x0) / period), z0 + (z1 - z0) * j / nv))
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i
            faces.append((a, a + 1, a + nu + 2, a + nu + 1))   # (+x) x (+z) = -Y: faces the room
            uvs.append([(i / nu, j / nv), ((i + 1) / nu, j / nv), ((i + 1) / nu, (j + 1) / nv), (i / nu, (j + 1) / nv)])
    return verts, faces, uvs


def shoji(pc, x0, x1, z0, z1, n_vert, horiz, bar=0.025, casing=0.04):
    """Look pass: a blind shoji panel on the wall face (backlit paper, lattice bars, a dark casing), so the upper walls
    read as the reference's continuous clerestory of lattice windows. Local frame of a wall piece (inner face y = 0)."""
    pc.box(x0, x1, 0, 0.006, z0, z1, SH)
    for i in range(1, n_vert + 1):
        xc = x0 + i * (x1 - x0) / (n_vert + 1)
        pc.box(xc - bar / 2, xc + bar / 2, 0.006, 0.02, z0, z1, T)
    for zc in horiz:
        pc.box(x0, x1, 0.006, 0.02, zc - bar / 2, zc + bar / 2, T)
    pc.box(x0 - casing, x0, 0, 0.025, z0, z1 + casing, T).box(x1, x1 + casing, 0, 0.025, z0, z1 + casing, T)
    pc.box(x0 - casing, x1 + casing, 0, 0.025, z1, z1 + casing, T)
    return pc


def transom(pc, x0, x1):
    """Look pass: a ranma-style square-grid transom just under the ceiling (+4.52 to +4.70 world)."""
    pc.box(x0 - 0.04, x1 + 0.04, 0, 0.025, 1.97, 2.02, T)
    n = max(3, round((x1 - x0) / 0.10) - 1)
    pc.box(x0, x1, 0, 0.006, 2.02, 2.20, PS)   # unlit, subdued: the dark upper grilles of the reference
    for i in range(1, n + 1):
        xc = x0 + i * (x1 - x0) / (n + 1)
        pc.box(xc - 0.01, xc + 0.01, 0.006, 0.02, 2.02, 2.20, T)
    pc.box(x0, x1, 0.006, 0.02, 2.10, 2.12, T)
    return pc


SHOJI_H = (1.33, 1.59)   # lattice rails at +3.83 and +4.09 world, level with the real window lattice


def vase_profile(s):
    """Black glazed vase (reference 2): round shoulder, short neck, flared lip, open mouth. s = height in metres."""
    k = s / 0.30
    pts = [(0, 0), (0.055, 0), (0.062, 0.008), (0.086, 0.055), (0.099, 0.125), (0.093, 0.19), (0.068, 0.24),
           (0.040, 0.268), (0.036, 0.285), (0.046, 0.298), (0.044, 0.304), (0.031, 0.300), (0.028, 0.262), (0, 0.248)]
    return [(r * k, z * k) for r, z in pts]


def plinth_front(pl, hw, bi, zb, facing):
    """Building stage (reference 2, R5): a louvred band of vertical lacquer slats at each end of the plinth face and
    the user's emblem as a gold medallion centred on it. bi = half depth of the inset body; facing -1 = front (-Y)."""
    y_face = facing * bi
    W = 2 * hw
    band = 0.18 * W
    for side in (-1, 1):
        a0 = -hw + 0.06 if side < 0 else hw - 0.06 - band
        n = int(band / 0.034)
        for i in range(n):
            xc = a0 + (i + 0.5) * band / n
            if facing < 0:
                pl.box(xc - 0.008, xc + 0.008, y_face - 0.012, y_face, 0.13, zb - 0.03, BZ)
            else:
                pl.box(xc - 0.008, xc + 0.008, y_face, y_face + 0.012, 0.13, zb - 0.03, BZ)
    zc = (0.08 + zb) / 2
    r = min(0.15, (zb - 0.08) / 2 - 0.035)
    if facing < 0:
        pl.mesh(*disc_y(0.0, y_face - 0.008, zc, r, 0.008, EM, BR, 32, -1))
    else:
        pl.mesh(*disc_y(0.0, y_face + 0.008, zc, r, 0.008, EM, BR, 32, +1))


def hero_table(W, D, H):
    """Building r2 (reference 2, R6): the low black lacquer hero table on the platform: a wide base with a gold top line,
    louvred bands and the user's emblem centred on its front, a warm under-glow, and a narrower upper tier. No glass."""
    hw, hd = W / 2, D / 2
    t = Piece("SM_AK_Case_Hero_Plinth")
    t.box(-hw + 0.05, hw - 0.05, -hd + 0.05, hd - 0.05, 0, 0.06, LQ)
    t.box(-hw + 0.06, hw - 0.06, -hd + 0.04, -hd + 0.05, 0.040, 0.052, LG)
    zb = 0.30
    t.box(-hw, hw, -hd, hd, 0.06, zb - 0.02, LQ).box(-hw - 0.01, hw + 0.01, -hd - 0.01, hd + 0.01, zb - 0.02, zb, LQ)
    t.box(-hw - 0.013, hw + 0.013, -hd - 0.013, -hd - 0.01, zb - 0.012, zb, BR)
    for side in (-1, 1):   # louvred bands either side of the emblem
        a0 = -hw + 0.10 if side < 0 else hw - 0.10 - 0.55
        for i in range(14):
            xc = a0 + (i + 0.5) * 0.55 / 14
            t.box(xc - 0.008, xc + 0.008, -hd - 0.012, -hd, 0.09, zb - 0.05, BZ)
    t.mesh(*disc_y(0.0, -hd - 0.008, (0.06 + zb - 0.02) / 2, 0.10, 0.008, EM, BR, 32, -1))   # f1: 17 -> 20 cm
    uw, ud = hw - 0.25, hd - 0.15
    t.box(-uw, uw, -ud, ud, zb, H - 0.012, LQ).box(-uw - 0.004, uw + 0.004, -ud - 0.004, ud + 0.004, H - 0.012, H, BR)
    t.box(-uw + 0.03, uw - 0.03, -ud + 0.03, ud - 0.03, H, H + 0.004, FE)
    t.mesh(*disc_y(0.0, -ud - 0.006, (zb + H) / 2, 0.055, 0.006, EM, BR, 32, -1))
    return t.col(-hw - 0.013, hw + 0.013, -hd - 0.013, hd + 0.01, 0, H)


def kit():
    pieces = []
    for L in (2, 1):
        # look pass: the wall body is near-black timber (was cream plaster); cream now lives in the lit niches
        pieces.append(Piece(f"SM_AK_WallLower_{L}")
                      .box(0, L, -0.30, 0, 0, 2.5, T).box(0, L, 0, 0.012, 0, 0.40, T)
                      .box(0, L, 0, 0.02, 2.40, 2.52, T).col(0, L, -0.30, 0.02, 0, 2.5))
        up = Piece(f"SM_AK_WallUpper_{L}")
        up.box(0, L, -0.30, 0, 0, 2.5, T).box(0, L, 0, 0.02, 0.85, 0.95, T).box(0, L, 0, 0.05, 0.95, 1.0, T)
        up.box(0, L, 0, 0.02, 2.20, 2.30, T)
        spans = ((0.12, 0.88), (1.12, 1.88)) if L == 2 else ((0.12, 0.88),)   # clear of the posts every 1 m
        for x0, x1 in spans:
            shoji(up, x0, x1, 1.0, 1.9, 5, SHOJI_H)
            transom(up, x0, x1)
        up.col(0, L, -0.30, 0.02, 0, 2.5)
        pieces.append(up)
    # building stage (R6): the north wall's upper band: framed plaster panels (not blind shoji) behind the banners
    upn = Piece("SM_AK_WallUpper_Plain_2")
    upn.box(0, 2, -0.30, 0, 0, 2.5, T).box(0, 2, 0, 0.02, 2.20, 2.30, T).box(0, 2, 0, 0.05, 0.0, 0.10, T)
    for x0, x1 in ((0.10, 0.92), (1.08, 1.90)):
        upn.box(x0, x1, 0, 0.008, 0.25, 1.90, "M_AK_ScreenPanel")   # f1: dark screen panels (reference 2's upper rear wall)
        upn.box(x0 - 0.04, x0, 0, 0.03, 0.21, 1.94, T).box(x1, x1 + 0.04, 0, 0.03, 0.21, 1.94, T)
        upn.box(x0, x1, 0, 0.03, 0.21, 0.25, T).box(x0, x1, 0, 0.03, 1.90, 1.94, T)
        transom(upn, x0, x1)
    upn.col(0, 2, -0.30, 0.02, 0, 2.5)
    pieces.append(upn)
    w = Piece("SM_AK_WallUpper_Window_2")
    s0, h0 = WIN_SILL - LIN, WIN_HEAD + LIN
    w.box(0, RO0, -0.30, 0, 0, 2.5, T).box(RO1, 2, -0.30, 0, 0, 2.5, T)
    w.box(RO0, RO1, -0.30, 0, 0, s0, T).box(RO0, RO1, -0.30, 0, h0, 2.5, T)
    transom(w, 0.25, 1.75)
    shoji(w, 0.25, 1.75, WIN_HEAD + LIN + 0.08, 1.93, 13, (1.82,))   # dense ranma band (13 bars); f1: +4.21 to +4.43
    w.box(RO0, RO1, -0.30, 0.03, s0, WIN_SILL, T).box(RO0, RO1, -0.30, 0.03, WIN_HEAD, h0, T)
    w.box(RO0, 0.25, -0.30, 0.03, WIN_SILL, WIN_HEAD, T).box(1.75, RO1, -0.30, 0.03, WIN_SILL, WIN_HEAD, T)
    w.box(0, 2, 0, 0.05, s0 - 0.05, s0, T).box(0, 2, 0, 0.02, 2.20, 2.30, T)            # sill board, top rail
    w.box(RO0 - 0.07, RO0, 0, 0.025, s0, h0 + 0.07, T).box(RO1, RO1 + 0.07, 0, 0.025, s0, h0 + 0.07, T)
    w.box(RO0 - 0.07, RO1 + 0.07, 0, 0.025, h0, h0 + 0.07, T)
    w.col(0, RO0, -0.30, 0.02, 0, 2.5).col(RO1, 2, -0.30, 0.02, 0, 2.5)
    w.col(RO0, RO1, -0.30, 0.02, 0, s0).col(RO0, RO1, -0.30, 0.02, h0, 2.5)
    pieces.append(w)
    # building stage (R3): reference-2 windows have dense vertical muntins and one horizontal rail (was a 5 x 4 grid)
    lat = Piece("SM_AK_Window_Lattice")
    H = WIN_HEAD - WIN_SILL
    lat.box(0, 1.50, -0.02, 0.02, 0, 0.04, T).box(0, 1.50, -0.02, 0.02, H - 0.04, H, T)
    lat.box(0, 0.04, -0.02, 0.02, 0.04, H - 0.04, T).box(1.46, 1.50, -0.02, 0.02, 0.04, H - 0.04, T)
    # f2 (blind judge delta 4: "a square grid instead of mostly vertical slats"; reference 2's near-left windows show
    # tall panes, about 7-9 muntins and 2-3 rails): 9 muntins and 3 rails, panes 14.2 x 34.3 cm (was 11 muntins, 1 rail)
    for i in range(1, 10):
        xc = 0.04 + i * 1.42 / 10
        lat.box(xc - 0.011, xc + 0.011, -0.0125, 0.0125, 0.04, H - 0.04, T)
    for k in range(1, 4):
        zc = 0.04 + k * (H - 0.08) / 4
        lat.box(0.04, 1.46, -0.0125, 0.0125, zc - 0.012, zc + 0.012, T)
    lat.col(0, 1.50, -0.02, 0.02, 0, H)
    pieces.append(lat)
    # building r3: a closed paper pane behind the lattice (the west wall's three south bays, Y 0-6): with a 22 deg sun
    # from the north-west these windows would throw their lattice patches onto the entry mat and lanterns, which reference
    # 2 keeps in shade; closed, they glow like the reference's paper ranma. Outside the lattice, in the wall thickness.
    if WEST_CLOSED_Y0:   # f1: no closed bays, so the piece (and its FBX) is not built
        pieces.append(Piece("SM_AK_Window_ShojiPane").box(0, 1.50, -0.04, -0.03, 0, WIN_HEAD - WIN_SILL, "M_AK_ShojiLit")
                      .col(0, 1.50, -0.04, -0.03, 0, WIN_HEAD - WIN_SILL))
    # building stage: the big entrance (user decision): a full-height south-wall piece around a CLEAR 4.0 x 3.65 m
    # opening. Layout 2 (user-approved 2026-09-27, reference entrance.png's composition). Layout 2 r2: the piece is the
    # whole south wall, 12 m, world X 0-12 (local = world; ENTRANCE_X0 = 0; was SM_AK_Entrance_10, X 1-11, between plain
    # 1 m wall pieces), clear opening X 4-8, so the sheet's wall cladding and lattice band run on to the corners. The
    # heavy jamb posts (SM_AK_Post_Jamb_480, layout JAMB_POSTS) stand against its room face at the OUTER ENDS of the
    # frame. Layout 2 r3 (blind judge: taller and narrower between the posts, deep posts, one heavy lintel with no brass
    # inlays, a visible inner jamb band): posts X 1.61-2.11 / 9.89-10.39 (80 cm deep), a 14 cm inner jamb band with a
    # brass edge between each post and its parked leaf (X 2.11-2.25 / 9.75-9.89, standing on the step), the 1.70 x 3.90 m
    # leaves (X 2.25-3.95 / 8.05-9.75); between the posts a recessed board panel over the opening and the leaves
    # (3.65-4.30) carrying the brass track (a rod on stand-offs at +4.12, four hanger wheels and straps) and ONE heavy
    # lintel 4.30-4.72 (the posts rise above it); outside them 1.6 m of clad wall (skirting, rails, a track-height rail,
    # the lit lattice band level with the lintel) to the corners
    L, o0, o1 = ENTRANCE_W, ENTRY_X[0] - ENTRANCE_X0, ENTRY_X[1] - ENTRANCE_X0
    en = Piece("SM_AK_Entrance_12")
    en.box(0, o0, -0.30, 0, 0, 5.0, T).box(o1, L, -0.30, 0, 0, 5.0, T)
    en.box(o0, o1, -0.30, 0, ENTRY_H, 5.0, T)
    pa = JAMB_POSTS[0][0] + JAMB_HW - ENTRANCE_X0                               # 2.11: the posts' inner faces
    pb = JAMB_POSTS[1][0] - JAMB_HW - ENTRANCE_X0                               # 9.89
    en.box(pa, pb, 0, 0.025, ENTRY_H, ENT_LINTEL[0], T)                         # the recessed panel behind the track
    en.box(o0 - 0.06, o1 + 0.06, 0.025, 0.045, ENTRY_H, ENTRY_H + 0.07, T)      # the opening's head casing
    en.box(pa, pb, 0, 0.24, ENT_LINTEL[0], ENT_LINTEL[1], T)                    # the one heavy lintel
    rz = ENT_TRACK_Z
    en.box(pa, pb, 0.145, 0.185, rz - 0.02, rz + 0.02, BR)                      # the brass track rod on stand-offs
    for xs in (pa + 0.45, pa + 2.05, L / 2, pb - 2.05, pb - 0.45):
        en.box(xs - 0.02, xs + 0.02, 0.025, 0.145, rz - 0.02, rz + 0.02, BR)
    top = ENTRY_TOP + DOOR_LEAF_H                                               # the leaves' top (+3.995)
    for lx in DOOR_LEAF_X:                                                      # four hanger wheels and straps
        for s in (0.25, DOOR_LEAF_W - 0.25):
            xh = lx - ENTRANCE_X0 + s
            en.box(xh - 0.07, xh + 0.07, 0.136, 0.164, rz + 0.02, rz + 0.16, BR)
            en.box(xh - 0.035, xh + 0.035, 0.19, 0.197, top - 0.002, rz + 0.09, BR)
    for (ka, kb), (ra, rb) in (((pa, pa + ENT_JAMB_W), (pa + ENT_JAMB_W - 0.012, pa + ENT_JAMB_W)),
                               ((pb - ENT_JAMB_W, pb), (pb - ENT_JAMB_W, pb - ENT_JAMB_W + 0.012))):
        en.box(ka, kb, 0, 0.205, ENTRY_TOP, ENT_LINTEL[0], T)                   # inner jamb band on the step
        en.box(ra, rb, 0.205, 0.215, ENTRY_TOP, ENT_LINTEL[0], BR)              # its brass edge
    for (ka, kb), (ra, rb) in (((o0 - 0.06, o0), (o0 - 0.008, o0)), ((o1, o1 + 0.06), (o1, o1 + 0.008))):
        en.box(ka, kb, 0, 0.03, 0, ENTRY_H, T).box(ra, rb, 0.022, 0.034, 0, ENTRY_H, BR)   # slim opening casing
    so = JAMB_POSTS[0][0] - JAMB_HW - ENTRANCE_X0                               # 1.61: the posts' outer faces
    for xa, xb in ((0.0, so), (L - so, L)):                                     # the flanks: skirting, rails, lit band
        en.box(xa, xb, 0, 0.012, 0, 0.10, T).box(xa, xb, 0, 0.03, 0.36, 0.55, T).box(xa, xb, 0, 0.03, 4.02, 4.22, T)
        en.box(xa, xb, 0, 0.006, ENT_LAT[0], ENT_LAT[1], SH)
        en.box(xa, xb, 0.006, 0.03, ENT_LAT[0] - 0.03, ENT_LAT[0], T).box(xa, xb, 0.006, 0.03, ENT_LAT[1], ENT_LAT[1] + 0.03, T)
        nc = round((xb - xa) / 0.08)
        for i in range(1, nc):
            xc = xa + i * (xb - xa) / nc
            en.box(xc - 0.009, xc + 0.009, 0.006, 0.026, ENT_LAT[0], ENT_LAT[1], T)
        for k in range(1, 4):
            zc = ENT_LAT[0] + k * (ENT_LAT[1] - ENT_LAT[0]) / 4
            en.box(xa, xb, 0.006, 0.024, zc - 0.009, zc + 0.009, T)
        en.box(xa, xb, 0, 0.04, ENT_LAT[1] + 0.03, ENT_LINTEL[1], T)             # the top board, level with the lintel
    en.col(0, o0, -0.30, 0.03, 0, 5.0).col(o1, L, -0.30, 0.03, 0, 5.0)
    en.col(pa, pb, -0.30, 0.24, ENTRY_H, 5.0)
    en.col(pa, pa + ENT_JAMB_W, 0, 0.215, 0, ENT_LINTEL[0]).col(pb - ENT_JAMB_W, pb, 0, 0.215, 0, ENT_LINTEL[0])
    pieces.append(en)
    # the raised threshold beam across the 4 m opening, between the posts (r3: its body runs to the nosing on the room
    # side, so no slot shows under the nosing against the mat). r4: the outer sill only (ENTRY_SILL, the exterior door
    # casing's depth); the mat runs back through the doorway to it
    pieces.append(Piece("SM_AK_Threshold_4").box(0, 4.0, ENTRY_SILL[0], ENTRY_SILL[1], 0, ENTRY_TOP, T)
                  .col(0, 4.0, ENTRY_SILL[0], ENTRY_SILL[1], 0, ENTRY_TOP))
    # a sliding leaf, parked open on the inner face either side of the opening (static). Layout 2: two hands, so each
    # leaf has ONE pull, on its leading stile at the opening: SM_AK_DoorLeaf (the west leaf, pull on its +X stile) and
    # SM_AK_DoorLeaf_R (the east leaf, pull on its -X stile). Layout 2 r2 (blind judge: the scripted leaf was a uniform
    # shoji grid): the sheet's leaf - stiles, a solid lower third with the user's emblem, a square grid band, an upper
    # panel of fine vertical slats over backlit paper with one cross bar, a solid brass pull on the leading stile at the
    # slat-to-grid transition, two brass hanger straps on the top rail. r3: 1.70 x 3.90 m, standing on the step (the
    # layout places it at +0.095), so it rises above the 3.65 m opening to the track like the sheet's
    DH = DOOR_LEAF_H
    LW, sw = DOOR_LEAF_W, 0.22
    for leaf_name, lead in (("SM_AK_DoorLeaf", +1), ("SM_AK_DoorLeaf_R", -1)):
        dl = Piece(leaf_name)
        dl.box(0, sw, 0, 0.05, 0, DH, T).box(LW - sw, LW, 0, 0.05, 0, DH, T)
        for z0, z1 in ((0, 0.16), (1.12, 1.24), (1.72, 1.82), (3.64, DH)):
            dl.box(sw, LW - sw, 0, 0.05, z0, z1, T)
        dl.box(sw, LW - sw, 0.009, 0.041, 0.16, 1.12, T)                          # the solid lower panel
        dl.mesh(*disc_y(LW / 2, 0.049, 0.64, 0.22, 0.008, EM, BR, 32, +1))      # the user's emblem
        dl.box(sw, LW - sw, 0.024, 0.026, 1.24, 1.72, SH).box(sw, LW - sw, 0.024, 0.026, 1.82, 3.64, SH)
        for yb0, yb1 in ((0.026, 0.044), (0.006, 0.024)):
            for i in range(1, 10):                                              # the square grid band
                xc = sw + i * (LW - 2 * sw) / 10
                dl.box(xc - 0.011, xc + 0.011, yb0, yb1, 1.24, 1.72, T)
            for k in (1, 2):
                zc = 1.24 + k * 0.48 / 3
                dl.box(sw, LW - sw, yb0, yb1, zc - 0.011, zc + 0.011, T)
            for i in range(1, 15):                                              # 14 fine vertical slats
                xc = sw + i * (LW - 2 * sw) / 15
                dl.box(xc - 0.017, xc + 0.017, yb0, yb1, 1.82, 3.64, T)
            dl.box(sw, LW - sw, yb0, yb1, 3.019, 3.047, T)                      # the cross bar a third down
        xc = LW - sw / 2 if lead > 0 else sw / 2
        dl.box(xc - 0.03, xc + 0.03, 0.05, 0.058, 1.44, 1.90, BR)               # the solid brass pull
        for s in (0.25, LW - 0.25):
            dl.box(s - 0.035, s + 0.035, 0.05, 0.057, 3.66, DH, BR)             # hanger straps
        dl.col(0, LW, 0, 0.05, 0, DH)
        pieces.append(dl)
    pieces.append(Piece("SM_AK_Corner_5").box(-0.30, 0, -0.30, 0, 0, 5.0, T))
    pieces.append(Piece("SM_AK_Post_480").box(-0.075, 0.075, -0.10, 0.05, 0, 4.80, T))
    # look2: the posts at the window centres stop under the (lower, larger) sill at +2.75
    pieces.append(Piece("SM_AK_Post_260").box(-0.075, 0.075, -0.10, 0.05, 0, 2.60, T))
    # building stage (R9): a freestanding 20 cm post with warm LED lines down its two front (-Y) edges
    pl_ = Piece("SM_AK_Post_LED_480").box(-0.10, 0.10, -0.10, 0.10, 0, 4.80, T)
    pl_.box(-0.106, -0.094, -0.106, -0.094, 0.05, 4.75, LL).box(0.094, 0.106, -0.106, -0.094, 0.05, 4.75, LL)
    pieces.append(pl_.col(-0.10, 0.10, -0.10, 0.10, 0, 4.80))
    # building r4 (R6, R9): the heavy 30 cm posts at the platform front corners of the stair, behind the pedestal lanterns
    ph = Piece("SM_AK_Post_Heavy_480").box(-0.15, 0.15, -0.15, 0.15, 0, 4.80, T)
    ph.box(-0.153, 0.153, -0.153, 0.153, 0.70, 0.712, BR).box(-0.153, 0.153, -0.153, 0.153, 3.60, 3.612, BR)
    pieces.append(ph.col(-0.15, 0.15, -0.15, 0.15, 0, 4.80))
    # f2 (blind judge delta 9: reference 2's door jambs fill the left and right frame edges; the 30 cm posts read thin):
    # a heavy jamb post, full height. Layout 2 (entrance.png's composition): the pair stands at the OUTER ENDS of the
    # entrance frame against the south wall's room face (layout JAMB_POSTS), rising through the ceiling line into the
    # void to +5.00 like the wall pieces (the sheet's posts break through the top beam). Layout 2 r2: a dark plinth, a
    # brass shoe 0.7 x the post width high, a flat brass plate on the three show faces near the top and a dark end-grain
    # top, a brass boss on the room face. Layout 2 r3 (blind judge: the sheet's posts are deep square columns standing
    # well proud of the wall, on a dark plinth a little wider than the post): 50 x 80 cm timber (local Y -0.40..+0.40 at
    # placement Y 0.40), the plinth 4 cm proud on the sides and front, the plate above the lintel (+4.74 to +4.97)
    hd, pl = JAMB_D / 2, JAMB_PL
    jb = Piece("SM_AK_Post_Jamb_480").box(-JAMB_HW, JAMB_HW, -hd, hd, 0.25, 4.994, T)
    jb.box(-JAMB_HW - pl, JAMB_HW + pl, -hd, hd + pl, 0, 0.25, LQ).box(-JAMB_HW, JAMB_HW, -hd, hd, 4.994, 5.0, LQ)
    e = 0.006
    jb.box(-JAMB_HW - e, JAMB_HW + e, -hd, hd + e, 0.25, 0.25 + 1.4 * JAMB_HW, BR)
    jb.box(-JAMB_HW - e, JAMB_HW + e, -hd, hd + e, 4.74, 4.97, BR)
    jb.box(-0.06, 0.06, hd, hd + 0.015, 4.45, 4.57, BR)
    pieces.append(jb.col(-JAMB_HW - pl, JAMB_HW + pl, -hd, hd + pl, 0, 5.0))
    for k, (ox, oy) in zip("ABCD", ((0, 0), (2, 0), (0, 2), (2, 2))):   # look2: 4 m tile over a 2 x 2 checker
        pieces.append(Piece(f"SM_AK_Floor_Plank_2x2_{k}").box(0, 2, 0, 2, -0.10, 0, PL, uv="y", uvoff=(ox, oy, 0)))

    def led_ring(c, a, b, z):
        e = 0.012   # 12 mm: an 8 mm line fell under a pixel from the floor
        c.box(a, b, a, a + e, z, z + e, LL).box(a, b, b - e, b, z, z + e, LL)
        c.box(a, a + e, a + e, b - e, z, z + e, LL).box(b - e, b, a + e, b - e, z, z + e, LL)
        return c

    def coffer_ring(c):
        c.box(0, 2, 0, 2, 0, 0.20, T)   # f1: dark timber coffer boards (the plaster-shade boards read olive in window light)
        c.box(0, 2, 0, 0.08, -0.06, 0, T).box(0, 2, 1.92, 2, -0.06, 0, T)
        c.box(0, 0.08, 0.08, 1.92, -0.06, 0, T).box(1.92, 2, 0.08, 1.92, -0.06, 0, T)
        return c
    c = coffer_ring(Piece("SM_AK_Ceiling_Coffer_2x2"))
    # look pass: a second, inner timber ring makes each coffer read as a stepped recess (dark ceiling, as referenced)
    c.box(0.35, 1.65, 0.35, 0.39, -0.03, 0, T).box(0.35, 1.65, 1.61, 1.65, -0.03, 0, T)
    c.box(0.35, 0.39, 0.39, 1.61, -0.03, 0, T).box(1.61, 1.65, 0.39, 1.61, -0.03, 0, T)
    # f1 (blind judge delta 7): a visible round downlight can (black body, brass trim, warm lens) instead of a flush disc;
    # the review spot sits just under the lens (lights(): Down_* at CEIL - 0.145)
    # f2 (blind judge delta 6: "clearly visible spotlight pucks"): a larger can, 14 cm across and 16 cm deep (was 11 x 13)
    c.cyl(1, 1, -0.014, 0, 0.09, BR, 24).cyl(1, 1, -0.16, -0.013, 0.07, LQ, 24).cyl(1, 1, -0.165, -0.1595, 0.055, LED, 24)
    # f2 (blind judge delta 6: "LED-edged coffers"): a fine warm LED line round the inner lower edge of each coffer ring
    led_ring(c, 0.08, 1.92, -0.06)
    c.col(0, 2, 0, 2, -0.06, 0.20)
    pieces.append(c)
    # f1 (blind judge delta 7): ribs along the axis on every 2 m line, so the ceiling reads as a coffer GRID (the cross
    # beams alone read as parallel LED strips). 16 x 30 cm, shallower than the 40 cm cross beams (no coplanar faces
    # where they meet), warm LED lines on both lower edges
    rb = Piece("SM_AK_Ceiling_Rib_2").box(0, 2, -0.08, 0.08, -0.30, 0, T)
    # (f1 test: LED lines on the ribs made the ceiling a bright office grid; the ribs stay plain dark timber)
    pieces.append(rb.col(0, 2, -0.08, 0.08, -0.30, 0))
    # building stage (R8): the ornamental lattice ceiling panel: a dense dark grid under a gold backlight
    cl = coffer_ring(Piece("SM_AK_Ceiling_Lattice_2x2"))
    cl.box(0.08, 1.92, 0.08, 1.92, -0.012, -0.004, GG)   # glow sheet just above the grid (under the coffer face)
    for i in range(1, 16):
        q = 0.08 + i * 1.84 / 16
        cl.box(q - 0.011, q + 0.011, 0.08, 1.92, -0.05, -0.012, T).box(0.08, 1.92, q - 0.011, q + 0.011, -0.05, -0.012, T)
    cl.col(0, 2, 0, 2, -0.06, 0.20)
    pieces.append(cl)
    # building stage (R8): 4 m beams (the 12 m room is three of them per line) with warm LED lines on both lower edges
    bm4 = Piece("SM_AK_Ceiling_Beam_4").box(0, 4, -0.125, 0.125, -0.40, 0, T)
    bm4.box(0.02, 3.98, -0.131, -0.119, -0.40, -0.388, LL).box(0.02, 3.98, 0.119, 0.131, -0.40, -0.388, LL)
    pieces.append(bm4.col(0, 4, -0.125, 0.125, -0.40, 0))
    pieces.append(Piece("SM_AK_Platform_2x1").box(0, 2, 0, 0.85, 0, 0.57, T).box(0, 2, 0, 0.85, 0.57, 0.60, PL)
                  .col(0, 2, 0, 0.85, 0, 0.60))
    pe = Piece("SM_AK_Platform_Edge_2x1").box(0, 2, 0, 0.85, 0, 0.57, T)
    pe.box(0, 2, -0.02, 0.85, 0.57, 0.60, PL).box(0.01, 1.99, -0.012, 0, 0.545, 0.56, LED)
    pe.box(0, 2, -0.004, 0, 0.50, 0.51, BR)
    # building stage (R6): the platform front reads as a row of dark cabinet doors (split line, brass pulls)
    pe.box(0.997, 1.003, -0.008, 0, 0.06, 0.46, LQ).box(0.03, 1.97, -0.008, 0, 0.46, 0.47, LQ)
    pe.box(0.90, 0.93, -0.016, 0, 0.24, 0.32, BR).box(1.07, 1.10, -0.016, 0, 0.24, 0.32, BR)
    pieces.append(pe.col(0, 2, -0.02, 0.85, 0, 0.60))
    s = Piece("SM_AK_Steps_2")
    s.box(0, 2, 0, 0.75, 0, 0.12, T).box(0, 2, 0.25, 0.75, 0.12, 0.27, T).box(0, 2, 0.5, 0.75, 0.27, 0.42, T)
    s.box(0, 2, -0.02, 0.25, 0.12, 0.15, PL).box(0, 2, 0.23, 0.50, 0.27, 0.30, PL).box(0, 2, 0.48, 0.75, 0.42, 0.45, PL)
    s.box(0.01, 1.99, -0.01, 0, 0.10, 0.115, LED).box(0.01, 1.99, 0.24, 0.25, 0.25, 0.265, LED)
    s.box(0.01, 1.99, 0.49, 0.50, 0.40, 0.415, LED)
    s.col(0, 2, -0.02, 0.75, 0, 0.15).col(0, 2, 0.23, 0.75, 0.15, 0.30).col(0, 2, 0.48, 0.75, 0.30, 0.45)
    pieces.append(s)
    # fix1 / look2: the lit wall niche (a golden backlit panel, black lacquer counter, brass rails, a lattice grille)
    # f1 (blind judge blocker 2, reference 2 left-wall zoom): a dark recess, not a lightbox. A plain dark-wood back board
    # (no emission, no grille band, no LED edge lines), a small warm downlight lens under the head 20 cm off the back,
    # a black lacquer counter over a closed lacquer front, and two pairs of short brass pegs (EMPTY fixtures; the long
    # brass rails read as extra horizontal lines). The review light is a spot at the lens pointing straight down: the
    # light grazes the board, hot under the head and falling off toward the counter (computed E ~ d / r^3: 17x dimmer
    # 0.5 m down than 0.1 m down). Two heights: 2.0 m on the hall floor (+0.40 to +2.40) and 1.90 m on the platform bays
    # (+0.60 to +2.50; measurer f1: top <= +2.54, under the sill ledge underside +2.549)
    # f2 (blind judge delta 11, reference 2 left and right walls zoomed): the niches are wall display bays ABOVE a dark
    # dado: a black lacquer cabinet front from the floor to the counter (+0.85 on the hall floor), a projecting lacquer
    # counter with a brass nosing, and the lit cream back board from the counter up to the head. Two pieces: the hall
    # bay (floor to +2.40, counter +0.85-+0.90) and the platform bay (placed on the platform, +0.60 to +2.50, counter
    # 40 cm up). The pegs stay at +1.35 / +1.70 above the hall floor (counter + 0.50 / + 0.85 in both pieces)
    for wname, NH, DZ in (("SM_AK_WallPanel_Lit", NICHE_H_FLOOR, NICHE_DADO_FLOOR),
                          ("SM_AK_WallPanel_Lit_190", NICHE_H_PLAT, NICHE_DADO_PLAT)):
        wp = Piece(wname)
        hd = NH - 0.05   # underside of the head
        wp.box(0.03, 0.82, 0, 0.02, DZ + 0.05, hd, BB).box(0, 0.03, 0, 0.25, 0, NH, T).box(0.82, 0.85, 0, 0.25, 0, NH, T)
        wp.box(0.03, 0.82, 0, 0.25, hd, NH, T)
        wp.cyl(0.425, NICHE_LENS_Y, hd - 0.012, hd, 0.035, BR, 16).cyl(0.425, NICHE_LENS_Y, hd - 0.016, hd - 0.0115, 0.024, LED, 16)
        wp.box(0.03, 0.82, 0, 0.22, 0, 0.08, T)                        # recessed toe kick
        wp.box(0.03, 0.82, 0, 0.25, 0.08, DZ, LQ)                      # the dark dado cabinet front
        wp.box(0.03, 0.82, 0.25, 0.254, 0.10, DZ - 0.02, LQ)           # its door panel, proud by 4 mm
        wp.box(0.4235, 0.4265, 0.254, 0.257, 0.12, DZ - 0.04, BR)      # the door split line in brass
        wp.box(0.0, 0.85, 0, 0.29, DZ, DZ + 0.05, LQ)                  # projecting counter (shelf ledge)
        wp.box(0.0, 0.85, 0.29, 0.294, DZ + 0.015, DZ + 0.035, BR)     # brass nosing
        for zp in (DZ + 0.50, DZ + 0.85):
            for xp in (0.22, 0.63):
                wp.box(xp - 0.012, xp + 0.012, 0.02, 0.075, zp - 0.012, zp + 0.012, BR)
        wp.col(0, 0.85, 0, 0.294, 0, NH)
        pieces.append(wp)
    # building stage (R3): the deep continuous windowsill ledge (2 m module, 32 cm deep, top at +2.64 world)
    pieces.append(Piece("SM_AK_SillLedge_2").box(0, 2, 0, 0.32, 0, 0.05, T).box(0, 2, 0.30, 0.335, -0.04, 0.05, T)
                  .col(0, 2, 0, 0.335, -0.04, 0.05))
    # building stage (R6): the rear alcove (replaces the corner rack): golden backlit panel, an EMPTY upright sword rack
    # on a black tansu carrying the emblem, an ornamental lattice screen with a gold backlight above. 1.8 x 0.6 x 3.2 m
    ra = Piece("SM_AK_RearAlcove")
    ra.box(0, 0.08, 0, 0.6, 0, 3.2, T).box(1.72, 1.8, 0, 0.6, 0, 3.2, T)
    ra.box(0.08, 1.72, 0, 0.6, 3.1, 3.2, T).box(0.08, 1.72, 0, 0.6, 0, 0.04, T)
    ra.box(0.08, 1.72, 0, 0.02, 0.04, 2.35, "M_AK_AlcoveLit")   # f2: softly backlit cream (was the dark board)
    ra.box(0.08, 0.086, 0.02, 0.028, 0.10, 2.30, LS).box(1.714, 1.72, 0.02, 0.028, 0.10, 2.30, LS)
    # f1: two small downlight lenses under the head replace the bright LED strip across the front lip
    for xl in (0.55, 1.25):
        ra.cyl(xl, 0.36, 2.338, 2.35, 0.04, BR, 16).cyl(xl, 0.36, 2.334, 2.3385, 0.028, LED, 16)
    ra.box(0.08, 1.72, 0, 0.6, 2.35, 2.45, T)
    ra.box(0.08, 1.72, 0, 0.02, 2.45, 3.1, GG)
    for i in range(1, 33):   # building r4: 32 x 12 bars, 26 mm wide (was 26 x 7, 14 mm): gold glints through a dark grid
        xc = 0.08 + i * 1.64 / 33
        ra.box(xc - 0.013, xc + 0.013, 0.02, 0.045, 2.45, 3.1, T)
    for i in range(1, 13):
        zc = 2.45 + i * 0.65 / 13
        ra.box(0.08, 1.72, 0.02, 0.045, zc - 0.013, zc + 0.013, T)
    ra.box(0.25, 1.55, 0.06, 0.46, 0.04, 0.52, LQ).box(0.25, 1.55, 0.06, 0.46, 0.52, 0.528, BR)
    ra.box(0.897, 0.903, 0.46, 0.464, 0.06, 0.50, T)
    ra.box(0.55, 0.65, 0.46, 0.475, 0.41, 0.425, BR).box(1.15, 1.25, 0.46, 0.475, 0.41, 0.425, BR)
    ra.mesh(*disc_y(0.9, 0.46 + 0.008, 0.25, 0.075, 0.008, EM, BR, 32, +1))
    ra.box(0.35, 1.45, 0.18, 0.34, 0.528, 0.61, LQ).box(0.35, 1.45, 0.18, 0.34, 0.61, 0.616, BR)   # empty rack
    ra.box(0.35, 0.41, 0.23, 0.29, 0.616, 1.75, LQ).box(1.39, 1.45, 0.23, 0.29, 0.616, 1.75, LQ)
    ra.box(0.35, 1.45, 0.20, 0.32, 1.62, 1.70, LQ).box(0.35, 1.45, 0.20, 0.32, 1.70, 1.706, BR)
    for i in range(7):
        xc = 0.52 + i * 0.126
        ra.box(xc - 0.012, xc + 0.012, 0.32, 0.326, 1.62, 1.70, BR).box(xc - 0.012, xc + 0.012, 0.34, 0.346, 0.53, 0.61, BR)
    ra.col(0, 1.8, 0, 0.6, 0, 3.2)
    pieces.append(ra)
    # building stage (R6): the dark patterned screens flanking the painting (0.7 x 3.4 m)
    rs = Piece("SM_AK_RearScreen")
    rs.box(0, 0.7, 0, 0.04, 0, 3.4, "M_AK_ScreenPanel")
    rs.box(0, 0.05, 0, 0.08, 0, 3.4, T).box(0.65, 0.7, 0, 0.08, 0, 3.4, T)
    rs.box(0.05, 0.65, 0, 0.08, 3.35, 3.4, T).box(0.05, 0.65, 0, 0.08, 0, 0.05, T)
    for xc in (0.2, 0.35, 0.5):
        rs.box(xc - 0.006, xc + 0.006, 0.04, 0.05, 0.05, 3.35, T)
    for i in range(1, 12):
        zc = i * 3.4 / 12
        rs.box(0.05, 0.65, 0.04, 0.05, zc - 0.006, zc + 0.006, T)
    pieces.append(rs.col(0, 0.7, 0, 0.08, 0, 3.4))
    # fix1: the painting reads as a warm backlit recess: a brass fillet inside the frame and a thin LED halo line
    # around the frame's outer edge (the glowing gold border of reference 2)
    pp = Piece("SM_AK_PaintingPanel")
    PH = PAINT_H   # building r2: 2.4 x 2.3 m (reference 2: the panel is nearly square and fills the bay)
    # f1 (blind judge delta 13): a warm gold frame (was dark timber) inside the LED halo
    pp.box(0, 2.4, 0, 0.10, 0, 0.08, BR).box(0, 2.4, 0, 0.10, PH - 0.08, PH, BR)
    pp.box(0, 0.08, 0, 0.10, 0.08, PH - 0.08, BR).box(2.32, 2.4, 0, 0.10, 0.08, PH - 0.08, BR)
    pp.box(0.08, 2.32, 0, 0.06, 0.08, PH - 0.08, "M_AK_Painting", uv="x", unique="+y")
    f = 0.012
    pp.box(0.08, 2.32, 0.06, 0.07, 0.08, 0.08 + f, BR).box(0.08, 2.32, 0.06, 0.07, PH - 0.08 - f, PH - 0.08, BR)
    pp.box(0.08, 0.08 + f, 0.06, 0.07, 0.08 + f, PH - 0.08 - f, BR)
    pp.box(2.32 - f, 2.32, 0.06, 0.07, 0.08 + f, PH - 0.08 - f, BR)
    g = 0.008
    pp.box(-g, 2.4 + g, 0.0, 0.03, -g, 0, LED).box(-g, 2.4 + g, 0.0, 0.03, PH, PH + g, LED)
    pp.box(-g, 0, 0.0, 0.03, 0, PH, LED).box(2.4, 2.4 + g, 0.0, 0.03, 0, PH, LED)
    pp.col(0, 2.4, 0, 0.10, 0, PH)
    pieces.append(pp)
    # building stage (R1): the woven mat and the entry step. Layout 2 r2 (blind judge, entrance.png): the sheet's
    # raised step platform runs plinth to plinth in front of the doors, top flush with the threshold (+0.095), and the
    # woven mat is inset flush in it across the opening, a wide landscape rectangle in a black border (was a 1.6 x 2.4
    # runner and a detached 4.4 m sill beam at Y 2.56). Layout 2 r3 (blind judge: the sheet's step is a shallow ledge
    # ending at the post fronts, the leaves stand on it): mat world X 4.02-7.98, Y 0.135-0.77 (ENTRY_MAT); the platform
    # world X 2.15-9.85 (plinth to plinth), decks under the parked leaves from Y 0.035, a front board to Y 0.86
    # (ENTRY_STEP); 9.5 cm, walkable (walk_check: max step 0.45). Layout 2 r4 (entrance.png): the platform +0.15 (one
    # walkable step), the mat 4.0 x 1.05 m across the opening and back through the doorway (world X 4-8, Y -0.30-0.75)
    mw, md = ENTRY_MAT[2] - ENTRY_MAT[0], ENTRY_MAT[3] - ENTRY_MAT[1]
    em = Piece("SM_AK_EntryMat").box(0.09, mw - 0.09, 0.09, md - 0.09, 0, ENTRY_TOP - 0.005, "M_AK_Mat", uv="x",
                                     unique="+z")
    em.box(0, 0.09, 0, md, 0, ENTRY_TOP, T).box(mw - 0.09, mw, 0, md, 0, ENTRY_TOP, T)
    em.box(0.09, mw - 0.09, 0, 0.09, 0, ENTRY_TOP, T).box(0.09, mw - 0.09, md - 0.09, md, 0, ENTRY_TOP, T)
    pieces.append(em.col(0, mw, 0, md, 0, ENTRY_TOP))
    es = Piece("SM_AK_EntryStep_4")
    for (xa, xb, ya, yb) in entry_step_parts():
        es.box(xa, xb, ya, yb, 0, ENTRY_TOP, T).col(xa, xb, ya, yb, 0, ENTRY_TOP)
    pieces.append(es)
    # exterior stage: SM_AK_Ext_Ground and SM_AK_Ext_Backdrop are replaced by the SM_AKX_ garden (build_armory_exterior)
    for t, (W, D, H, G) in CASES.items():
        hw, hd = W / 2, D / 2
        if t == "Hero":
            pieces.append(hero_table(W, D, H))
            continue
        pl = Piece(f"SM_AK_Case_{t}_Plinth")
        pl.box(-hw + 0.05, hw - 0.05, -hd + 0.05, hd - 0.05, 0, 0.08, LQ)
        pl.box(-hw + 0.06, hw - 0.06, -hd + 0.04, -hd + 0.05, 0.055, 0.07, LG)
        pl.box(-hw + 0.06, hw - 0.06, hd - 0.05, hd - 0.04, 0.055, 0.07, LG)
        pl.box(-hw + 0.04, -hw + 0.05, -hd + 0.06, hd - 0.06, 0.055, 0.07, LG)
        pl.box(hw - 0.05, hw - 0.04, -hd + 0.06, hd - 0.06, 0.055, 0.07, LG)
        # look pass: the body sits 15 mm inside a full-footprint lacquer cap with a brass top edge, as in the
        # reference (a crisp gold line where the glass meets the plinth); the gold band runs on the inset body
        i = 0.015
        pl.box(-hw + i, hw - i, -hd + i, hd - i, 0.08, H - 0.035, LQ).box(-hw, hw, -hd, hd, H - 0.035, H, LQ)
        e = 0.003
        pl.box(-hw - e, hw + e, -hd - e, -hd, H - 0.012, H, BR).box(-hw - e, hw + e, hd, hd + e, H - 0.012, H, BR)
        pl.box(-hw - e, -hw, -hd, hd, H - 0.012, H, BR).box(hw, hw + e, -hd, hd, H - 0.012, H, BR)
        zb = H - 0.10 if H > 0.3 else 0.12
        bi = hd - i
        ai = hw - i
        pl.box(-ai, ai, -bi - 0.004, -bi, zb, zb + 0.015, BR).box(-ai, ai, bi, bi + 0.004, zb, zb + 0.015, BR)
        pl.box(-ai - 0.004, -ai, -bi, bi, zb, zb + 0.015, BR).box(ai, ai + 0.004, -bi, bi, zb, zb + 0.015, BR)
        # f1: black lacquer deck (was the look2 oxblood cloth) with a thin brass edge just inside the glass
        pl.box(-hw + 0.03, hw - 0.03, -hd + 0.03, hd - 0.03, H, H + 0.004, FE)
        tb = 0.008
        pl.box(-hw + 0.03, hw - 0.03, -hd + 0.03, -hd + 0.03 + tb, H, H + 0.007, BR)
        pl.box(-hw + 0.03, hw - 0.03, hd - 0.03 - tb, hd - 0.03, H, H + 0.007, BR)
        pl.box(-hw + 0.03, -hw + 0.03 + tb, -hd + 0.03 + tb, hd - 0.03 - tb, H, H + 0.007, BR)
        pl.box(hw - 0.03 - tb, hw - 0.03, -hd + 0.03 + tb, hd - 0.03 - tb, H, H + 0.007, BR)
        if H > 0.3:
            # building stage (R5): louvred slat bands and the user's emblem medallion on the front AND back faces
            # (the brass inlay frame and the blank plate of fix1 are gone)
            plinth_front(pl, ai, bi, zb, -1)
            plinth_front(pl, ai, bi, zb, +1)
        else:   # the tall case's 20 cm plinth: a small medallion on the front face only
            pl.mesh(*disc_y(0.0, -bi - 0.010, 0.1225, 0.036, 0.010, EM, BR, 24, -1))
        pl.col(-hw, hw, -hd, hd, 0, H)
        pieces.append(pl)
        gw, gd = (W - 0.04) / 2, (D - 0.04) / 2
        gl = Piece(f"SM_AK_Case_{t}_Glass")
        for sx in (-1, 1):
            for sy in (-1, 1):
                x, y = sx * (gw - 0.006), sy * (gd - 0.006)
                gl.box(x - 0.004, x + 0.004, y - 0.004, y + 0.004, 0, G, BZ)
        for z0, z1 in ((0, 0.010), (G - 0.010, G)):
            gl.box(-gw, gw, -gd, -gd + 0.008, z0, z1, BZ).box(-gw, gw, gd - 0.008, gd, z0, z1, BZ)
            gl.box(-gw, -gw + 0.008, -gd + 0.008, gd - 0.008, z0, z1, BZ).box(gw - 0.008, gw, -gd + 0.008, gd - 0.008, z0, z1, BZ)
        gl.box(-gw + 0.012, gw - 0.012, -gd + 0.003, -gd + 0.009, 0.015, G - 0.015, GL)
        gl.box(-gw + 0.012, gw - 0.012, gd - 0.009, gd - 0.003, 0.015, G - 0.015, GL)
        gl.box(-gw + 0.003, -gw + 0.009, -gd + 0.012, gd - 0.012, 0.015, G - 0.015, GL)
        gl.box(gw - 0.009, gw - 0.003, -gd + 0.012, gd - 0.012, 0.015, G - 0.015, GL)
        gl.box(-gw + 0.012, gw - 0.012, -gd + 0.012, gd - 0.012, G - 0.012, G - 0.006, GL)
        # building r2: the tall case's backdrop panel is gone (reference 2: clear glass on all four sides; the lit
        # panel read as a bright door)
        gl.col(-gw, gw, -gd, gd, 0, G)
        pieces.append(gl)
    # f1 (blind judge delta 8, reference 2 andon, zoomed): heavy dark corner posts that run past the top as short
    # finials, a base frame on four feet, a projecting top frame with two cross bars, paper recessed behind the frame
    # with one low rail (the reference's panes are open and tall), amber paper (M_AK_Paper). 46 x 46 x 70 cm.
    ln = Piece("SM_AK_Lantern")
    for sx in (-1, 1):
        for sy in (-1, 1):
            # f2 (judge delta 9): the posts stop at the top frame (no finials above it), as reference 2's lantern
            ln.box(sx * 0.205 - 0.022, sx * 0.205 + 0.022, sy * 0.205 - 0.022, sy * 0.205 + 0.022, 0.0, 0.645, T)
    for z0, z1 in ((0.035, 0.075), (0.585, 0.625)):   # base frame and top frame rails, all four sides
        ln.box(-0.183, 0.183, -0.225, -0.187, z0, z1, T).box(-0.183, 0.183, 0.187, 0.225, z0, z1, T)
        ln.box(-0.225, -0.187, -0.183, 0.183, z0, z1, T).box(0.187, 0.225, -0.183, 0.183, z0, z1, T)
    # projecting top ledge: an open frame (reference 2: the glow shows through the open top)
    ln.box(-0.23, 0.23, -0.23, -0.17, 0.625, 0.645, T).box(-0.23, 0.23, 0.17, 0.23, 0.625, 0.645, T)
    ln.box(-0.23, -0.17, -0.17, 0.17, 0.625, 0.645, T).box(0.17, 0.23, -0.17, 0.17, 0.625, 0.645, T)
    # f2 (judge delta 9): the two cross bars over the top are gone (reference 2's cap is the plain open frame)
    ln.box(-0.183, 0.183, -0.183, 0.183, 0.035, 0.05, T)              # base board
    LP = "M_AK_LanternPaper"   # f2: the glow picture, uniquely mapped on each pane's outer face
    ln.box(-0.17, 0.17, -0.19, -0.18, 0.075, 0.585, LP, uv="x", unique="-y")
    ln.box(-0.17, 0.17, 0.18, 0.19, 0.075, 0.585, LP, uv="x", unique="+y")
    ln.box(-0.19, -0.18, -0.17, 0.17, 0.075, 0.585, LP, uv="y", unique="-x")
    ln.box(0.18, 0.19, -0.17, 0.17, 0.075, 0.585, LP, uv="y", unique="+x")
    for zc in (0.165,):   # one low rail on each face
        ln.box(-0.183, 0.183, -0.195, -0.185, zc - 0.01, zc + 0.01, T).box(-0.183, 0.183, 0.185, 0.195, zc - 0.01, zc + 0.01, T)
        ln.box(-0.195, -0.185, -0.183, 0.183, zc - 0.01, zc + 0.01, T).box(0.185, 0.195, -0.183, 0.183, zc - 0.01, zc + 0.01, T)
    ln.col(-0.23, 0.23, -0.23, 0.23, 0, 0.645)
    pieces.append(ln)
    # building stage (R6): the dark pedestal the step-side lanterns stand on (40 x 40 x 60 cm, brass bands)
    # hero r4 (USER DECISION 2026-09-28): a slim newel post at the stair foot as back_wall.png (0.23 m square, 0.85 m
    # tall, a brass kick plate and a brass collar under the cap); no lantern stands on it any more
    # newel lanterns (USER DECISION 2026-09-28, "follow the armory reference"): a 2 cm top plate (0.30 m square, to
    # NEWEL_TOP +0.87) for the small hero lantern SM_AK_H_NewelLantern to stand on (build 3: 0.30 m)
    pd = Piece("SM_AK_LanternPedestal").box(-0.105, 0.105, -0.105, 0.105, 0, 0.805, T)
    pd.box(-0.115, 0.115, -0.115, 0.115, 0.805, 0.85, T)
    pd.box(-NEWEL_PLATE, NEWEL_PLATE, -NEWEL_PLATE, NEWEL_PLATE, 0.85, NEWEL_TOP, T)
    pd.box(-0.108, 0.108, -0.108, 0.108, 0.03, 0.14, BR).box(-0.108, 0.108, -0.108, 0.108, 0.738, 0.792, BR)
    pd.col(-0.115, 0.115, -0.115, 0.115, 0, 0.85)
    pieces.append(pd.col(-NEWEL_PLATE, NEWEL_PLATE, -NEWEL_PLATE, NEWEL_PLATE, 0.85, NEWEL_TOP))
    # building stage (R7): a tall black cloth banner (0.55 x 2.2 m) with the user's gold crest, on a rod with cords
    bn = Piece("SM_AK_Banner")
    bn.mesh(*cloth(-0.275, 0.275, 0.0, 2.2), BN)
    bn.box(-0.32, 0.32, -0.018, 0.018, 2.215, 2.25, T)
    bn.box(-0.345, -0.32, -0.022, 0.022, 2.21, 2.255, BR).box(0.32, 0.345, -0.022, 0.022, 2.21, 2.255, BR)
    # f1: 15 cm hanging cords (was 30): hung from the ceiling at +4.80 the cloth now spans +2.40 to +4.60, the height
    # the landmark-fitted C1 camera measures for reference 2's banners (Z 2.41-4.60)
    bn.box(-0.254, -0.246, -0.004, 0.004, 2.25, 2.40, T).box(0.246, 0.254, -0.004, 0.004, 2.25, 2.40, T)
    pieces.append(bn.col(-0.345, 0.345, -0.03, 0.03, 0, 2.40))
    # building stage (R3, R6): black glazed vases holding red plum-blossom sprays (two crossed alpha-masked cards); r4: the
    # sill vase 0.30 -> 0.40 m (reference 2: the sill sprays are nearly as wide as a window mullion bay)
    # f1: the sill vase 0.40 -> 0.46 m and its spray 0.60 -> 0.62 m wide (judge: they read as tiny silhouettes), and its
    # two cards turned to +/-25 deg off the wall line (was 15 / 95: the 95 deg card put a stem 12.9 cm into the wall).
    # Computed: the cards reach at most 0.31 x sin 25 = 0.131 m toward the wall from the vase axis (0.17 m off the wall),
    # so they stop 3.9 cm in front of the wall face and clear the 3 cm window-head lining
    # f2 (blind judge delta 7: full, bushy sprays about 1.5x the vase height; reference 2's near-left sill spray is about
    # 1.7x the vase height tall and 2.5x as wide): the plum texture is a square wide bush now (T_AK_Plum 2048 x 2048), on
    # square cards. Sill vase: three 0.88 m cards at 0 and +/-16 deg off the wall line, from +0.30 (inside the mouth) to
    # +1.18, so the spray stands 0.72 m over the 0.46 m vase (1.6x) and 0.88 m wide (1.9x). Computed reach toward the
    # wall 0.44 x sin 16 = 0.121 m from the vase axis at 0.17 m: the cards stop 4.9 cm in front of the wall face and
    # 2.4 cm in front of the window casing (0-2.5 cm proud), which the outer card end passes at 0.77 m along the wall
    # (at +/-20 deg it would have touched the casing by 0.55 cm)
    # Big vase: two 0.90 m cards at 60 / 120 deg (+0.42 to +1.32): X reach 0.45 x cos 60 = 0.225 m, clear of the platform
    # lanterns (bbox X 3.288-3.812 / 8.188-8.712 against the cards' X 3.975-4.425 / 7.575-8.025)
    for name, hgt, cw, cz0, angs in (("SM_AK_Vase_Plum_S", 0.46, 0.88, 0.30, (0, 16, -16)),
                                     ("SM_AK_Vase_Plum_L", 0.56, 0.90, 0.42, (60, 120))):
        v = Piece(name)
        prof = vase_profile(hgt)
        v.mesh(*lathe(prof, 24), GZ, smooth=True)
        for ang in angs:
            v.mesh(*card(ang, cw, cz0, cz0 + cw), PM)
        rmax = max(r for r, _ in prof)
        pieces.append(v.col(-rmax, rmax, -rmax, rmax, 0, hgt))
    # building stage (R3): small objects on the sills: a lacquer tea caddy with a brass lid band and a little box
    cd_ = Piece("SM_AK_SillCaddy").cyl(0, 0, 0, 0.12, 0.045, LQ, 16).cyl(0, 0, 0.1205, 0.135, 0.047, BR, 16)
    cd_.box(0.08, 0.20, -0.05, 0.05, 0, 0.08, LQ).box(0.078, 0.202, -0.052, 0.052, 0.08, 0.09, BR)
    pieces.append(cd_.col(-0.047, 0.202, -0.052, 0.052, 0, 0.135))
    # f1 (measurer, R6): the user's emblem at the platform front centre: a gold medallion (11.6 cm) on the top riser face
    # between the top tread (+0.45) and the platform lip (+0.57), set over the riser's LED line on the axis
    ed = Piece("SM_AK_EmblemDisc_12").mesh(*disc_y(0.0, 0.0, 0.0, 0.058, 0.02, EM, BR, 32, -1))
    pieces.append(ed.col(-0.058, 0.058, 0.0, 0.02, -0.058, 0.058))
    return pieces


# --------------------------------------------------------------------------- the room layout

# look2: every 2 m upper bay of the long walls is a lattice window; building stage: 8 per wall over the 16 m length
UPPER_RUN = [(y0, 2, "SM_AK_WallUpper_Window_2") for y0 in range(0, 16, 2)]
WINDOWS_Y = [(y0 + 0.25, y0 + 1.75) for y0, _L, p in UPPER_RUN if p == "SM_AK_WallUpper_Window_2"]  # clear openings
SHORT_POSTS_Y = tuple(range(1, 16, 2))
# building r3: west bays with a closed shoji pane (no sun patches in the entry zone). f1: none: every window is open, as in
# reference 2 (its near-left windows are open and hot), and at the f1 sun (30 deg up, heading 30) the south bays' patches
# land on the floor by the entry, where reference 2 also shows lattice sun (zoom of its bottom-left lantern)
WEST_CLOSED_Y0 = ()
# (every odd post sits at a window centre and stops under the sill)
# building stage: the displays, re-laid for the 12 x 16 m hall (spirit of reference 1). (label, type, x, y, rot).
# Centre row on the axis X 6; side rows face the aisles at X 1.75 / 10.25 (aisles 2.7-2.9 m). G1-G3 are EMPTY growth slots.
CASE_TABLE = [
    ("1", "L", 6.0, 3.70, 0), ("2", "M", 6.0, 7.6, 0), ("3", "LN", 6.0, 11.3, 0),
    ("5", "S", 1.75, 4.1, 90), ("4", "Tall", 1.75, 6.6, 90), ("G1", "S", 1.75, 9.1, 90), ("G3", "Tall", 1.75, 11.6, 90),
    ("8", "S", 10.25, 4.0, -90), ("7", "S", 10.25, 6.3, -90), ("6", "Tall", 10.25, 8.8, -90),
    ("G2", "Tall", 10.25, 11.4, -90),
    ("10", "Hero", 6.0, 14.85, 0),
]
LANTERNS = [(3.90, 2.25, 0.0), (8.10, 2.25, 0.0),        # entry, flanking the runner (R1)
            # hero r4 (USER DECISION 2026-09-28): the two lanterns on the stair-foot pedestals are gone (the pedestals
            # are slim newel posts, back_wall.png shows no lanterns there); their lights go with them
            # 2026-09-28 (USER DECISION "follow the armory reference"): reference 2's stair-foot lanterns are back as
            # the smaller SM_AK_H_NewelLantern on the newel tops (NEWEL_*; hero_lantern_vase instances() / lights())
            # r5: on the platform. f1: X 4.0 -> 3.55 / 8.45, Y 15.10 (the lantern crossed the big plum vase by 10 cm; the
            # reference's platform lanterns stand outboard of the vases, beside the rear alcoves)
            (3.55, 15.10, 0.60), (8.45, 15.10, 0.60)]
NICHE_Y_FLOOR = list(range(1, 13))          # wall niche bays on the hall floor, both long walls (Y 1-13)
NICHE_Y_PLAT = [14]                          # a bay on the platform on each long wall (Y 14-15); f1: 1.90 m, +0.62-+2.52
NICHE_Z_PLAT = 0.60   # on the platform top; top +2.50, 4.9 cm under the sill ledge underside (+2.549)
# f2 (judge delta 7: one vase in each bay along both walls): every window bay, 8 per wall (was 4)
SILL_VASES_Y = tuple(float(y) for y in range(1, 16, 2))   # window centres; west vases at y - 0.35, east at y + 0.35
# f1: the banners hang from the ceiling near the side walls just in front of the platform, facing the entrance: the
# landmark-fitted C1 camera puts reference 2's banners (x 355-392 / 1056-1093 px, y 25-172 px on 1448 x 1086; 0.55 m
# wide) at X 0.78 / 11.22, Y 13.13, cloth Z 2.41-4.60 (was X 1.65 / 10.35, Y 15.55, where the wall medallion read)
BANNER_X, BANNER_Y, BANNER_Z = (0.78, 11.22), 13.13, 2.40
# f1: the rear alcoves move outboard to X 1.2-3.0 / 9.0-10.8 (were 2.0-3.8 / 8.2-10.0): the fitted C1 camera measures
# reference 2's rack alcoves at X ~1.0-2.3; the north-wall corner niches they now cover are gone (reference 2 has none)
REAR_ALCOVE_X = (1.2, 9.0)
PLUM_L_X = (4.20, 7.80)                      # f1: the big vases stand in front of the LED bay posts (was 4.45 / 7.55)
# Layout 2 (user-approved 2026-09-27, reference entrance.png's composition): the vestibule posts 1 m inside the entrance
# (f1/f2: (3.995, 1.02) / (8.005, 1.02)) are gone. The heavy jamb posts stand at the OUTER ENDS of the entrance frame on
# the south wall line, back face on the wall's room face (Y 0-0.30). Layout 2 r2 (blind judge: the sheet's proportions,
# inner jambs and raised step): the frame spans X 1.78-10.22 (post timber X 1.80-2.26 / 9.74-10.20 on 50 cm plinths),
# a 7 cm inner jamb strip (X 2.26-2.33 / 9.67-9.74), the 1.62 m leaves parked at X 2.33-3.95 / 8.05-9.67 (Y 0.14-0.19)
ENTRANCE_X0, ENTRANCE_W = 0.0, 12.0                 # SM_AK_Entrance_12: the whole south wall, X 0-12 (opening X 4-8)
# Layout 2 r3 (blind judge: the sheet is taller and narrower between the posts, its posts deep square columns standing
# well proud of the wall with the step ending at their fronts, a brass-edged inner jamb band between post and leaf):
# 50 x 80 cm post timber (X 1.61-2.11 / 9.89-10.39, Y 0-0.80) on a 58 x 84 cm plinth, a 14 cm inner jamb band
# (X 2.11-2.25 / 9.75-9.89), the 1.70 x 3.90 m leaves standing on the step (X 2.25-3.95 / 8.05-9.75, Z 0.095-3.995);
# the frame spans X 1.57-10.43
JAMB_HW, JAMB_D = 0.25, 0.80                        # post timber half width / depth off the wall's room face
JAMB_POSTS = ((1.86, 0.40), (10.14, 0.40))          # post centres (rot 0): timber Y 0-0.80, plinth to Y 0.84
JAMB_PL = 0.04                                      # the plinth stands 4 cm proud of the timber (sides and front)
ENT_JAMB_W = 0.14                                   # the inner jamb band between each post and its parked leaf
DOOR_LEAF_X, DOOR_LEAF_W, DOOR_LEAF_H = (2.25, 8.05), 1.70, 3.90   # parked leaves' world X, width, height (on the step)
ENT_TRACK_Z = 4.12                                  # the brass track rod's axis (the hanger wheels ride on it)
ENT_LINTEL = (4.30, 4.72)                           # the one heavy lintel, post to post (the posts rise to +5.00)
ENT_LAT = (4.30, 4.60)                              # the flanks' lit lattice band, level with the lintel
# Layout 2 r4 (entrance.png, the top view: a RAISED step with a lipped front edge plinth to plinth, the golden rush mat
# a large rectangle nearly filling the platform's depth, running back through the doorway): the platform +0.15 (one
# walkable step; was a 9.5 cm sliver), the mat the full 4 m opening wide from the wall's outer face (Y -0.30) to just
# behind the step's front board (4.0 x 1.05 m; was a 3.96 x 0.635 strip), the threshold the outer sill in front of it
ENTRY_TOP = 0.15                                    # the step platform / inset mat top (flush with the threshold)
ENTRY_MAT = (4.0, -0.30, 8.0, 0.75)                 # world x0, y0, x1, y1: the mat across the opening and the doorway
ENTRY_STEP = (2.15, 0.035, 9.85, 0.86)              # world x0, y0, x1, y1: the step, plinth to plinth, to the post fronts
ENTRY_SILL = (-0.435, -0.30)                        # the threshold sill's Y range (the exterior door casing's depth)


def entry_step_parts():
    """The step platform round the inset mat, as (x0, x1, y0, y1) local to its placement (ENTRY_STEP x0, y0): a side
    deck under each parked leaf (from Y 0.035, in front of the opening casings, the leaves stand on it) to the mat's
    front edge, a filler between each deck and the mat when the mat is narrower than the opening (r4: none, the mat
    is the opening's width), and the front board across the whole width to the post fronts."""
    x0, y0, x1, y1 = ENTRY_STEP
    mx0, my0, mx1, my1 = ENTRY_MAT
    ox0, ox1 = ENTRY_X
    r = lambda v: round(v, 4)
    parts = [(0.0, r(ox0 - x0), 0.0, r(my1 - y0)), (r(ox0 - x0), r(mx0 - x0), r(max(my0, y0) - y0), r(my1 - y0)),
             (r(mx1 - x0), r(ox1 - x0), r(max(my0, y0) - y0), r(my1 - y0)), (r(ox1 - x0), r(x1 - x0), 0.0, r(my1 - y0)),
             (0.0, r(x1 - x0), r(my1 - y0), r(y1 - y0))]
    return [q for q in parts if q[1] - q[0] > 1e-3 and q[3] - q[2] > 1e-3]
SILL_CADDIES = [(0.20, 5.40), (11.80, 8.60), (0.20, 13.40), (11.80, 0.60)]   # f2: clear of the vase in every bay
# f2 (blind judge delta 6: "lattice panels in the central coffers"): besides the two over the platform (r5), the centre
# coffers X 4-8 over the gaps between the centre cases (Y 8-10 behind case 2, Y 12-14 at the steps)
LATTICE_COFFERS = ((4, 8), (6, 8), (4, 12), (6, 12), (4, 14), (6, 14))


def layout():
    """Instances as (piece, (x, y, z) metres, rotation about Z in degrees). ARMORY_PLAN.md v2 section 3."""
    I = []
    add = lambda p, x, y, z=0.0, r=0.0: I.append((p, (round(x, 4), round(y, 4), round(z, 4)), r))
    nx, ny = int(ROOM_W // 2), int(ROOM_L // 2)
    for i in range(nx):
        for j in range(ny):
            add(f"SM_AK_Floor_Plank_2x2_{'ABCD'[(i % 2) + 2 * (j % 2)]}", 2 * i, 2 * j)
            lattice = (2 * i, 2 * j) in LATTICE_COFFERS   # R8: ornamental panels over the centre bays and the platform
            add("SM_AK_Ceiling_Lattice_2x2" if lattice else "SM_AK_Ceiling_Coffer_2x2", 2 * i, 2 * j, CEIL)
    for yb in range(2, int(ROOM_L), 2):
        for xb in (0, 4, 8):
            add("SM_AK_Ceiling_Beam_4", xb, yb, CEIL)
    for xr in (2, 4, 6, 8, 10):   # f1 (R8): ribs along the axis between the cross beams: a coffer grid
        for y0 in range(0, int(ROOM_L), 2):
            if y0 == 0 and xr in (2, 4, 6, 8, 10):   # layout 2 r3: the entrance's lintel (X 2.11-9.89) and its
                continue                              # jamb posts (X 1.57-2.15 / 9.85-10.43, Y 0-0.84) to +5.00
            add("SM_AK_Ceiling_Rib_2", xr, y0, CEIL, 90)
    # south wall (rot 0), layout 2 r2: one piece, the entrance wall X 0-12 between the corners (clear opening X 4-8; was
    # plain WallLower_1 / WallUpper_1 at X 0-1 / 11-12 with Post_480s on the joints at X 1 / 11, which would now stand
    # on the clad wall); the jamb posts stand at the frame's outer ends (JAMB_POSTS, below)
    add("SM_AK_Entrance_12", ENTRANCE_X0, 0)
    add("SM_AK_Threshold_4", ENTRY_X[0], 0)
    add("SM_AK_DoorLeaf", DOOR_LEAF_X[0], 0.14, ENTRY_TOP)     # parked open over X 2.25-3.95 and 8.05-9.75 on the
    add("SM_AK_DoorLeaf_R", DOOR_LEAF_X[1], 0.14, ENTRY_TOP)   # inner face, standing on the step between the jamb posts;
    # each leaf's pull on its leading stile
    # north wall (rot 180): location at the segment's east end
    for x0 in range(0, int(ROOM_W), 2):
        add("SM_AK_WallLower_2", x0 + 2, ROOM_L, 0, 180)
        add("SM_AK_WallUpper_Plain_2", x0 + 2, ROOM_L, 2.5, 180)
    for y0 in range(0, int(ROOM_L), 2):
        add("SM_AK_WallLower_2", 0, y0 + 2, 0, -90)           # west: length runs -Y from the location
        add("SM_AK_WallLower_2", ROOM_W, y0, 0, 90)           # east: length runs +Y
        add("SM_AK_SillLedge_2", 0, y0 + 2, 2.59, -90)        # R3: the deep sill ledge under every window
        add("SM_AK_SillLedge_2", ROOM_W, y0, 2.59, 90)
    for y0, L, up in UPPER_RUN:
        add(up, 0, y0 + L, 2.5, -90)
        add(up, ROOM_W, y0, 2.5, 90)
        add("SM_AK_Window_Lattice", -0.15, y0 + 2 - 0.25, 2.5 + WIN_SILL, -90)
        if y0 in WEST_CLOSED_Y0:
            add("SM_AK_Window_ShojiPane", -0.15, y0 + 2 - 0.25, 2.5 + WIN_SILL, -90)
        add("SM_AK_Window_Lattice", ROOM_W + 0.15, y0 + 0.25, 2.5 + WIN_SILL, 90)
    for (x, y, r) in ((0, 0, 0), (ROOM_W, 0, 90), (ROOM_W, ROOM_L, 180), (0, ROOM_L, -90)):
        add("SM_AK_Corner_5", x, y, 0, r)
    for y in range(1, int(ROOM_L)):
        post = "SM_AK_Post_260" if y in SHORT_POSTS_Y else "SM_AK_Post_480"
        add(post, 0, y, 0, -90)
        add(post, ROOM_W, y, 0, 90)
    for y in NICHE_Y_FLOOR:   # R4: the lit wall niche band down both long walls
        add("SM_AK_WallPanel_Lit", 0, y + 0.925, 0.0, -90)          # f2: from the floor (dado + bay), was +0.40
        add("SM_AK_WallPanel_Lit", ROOM_W, y + 0.075, 0.0, 90)
    for y in NICHE_Y_PLAT:   # f1: the 1.90 m niche, +0.60 to +2.50 (under the sill ledge; the 2 m one cut through it)
        add("SM_AK_WallPanel_Lit_190", 0, y + 0.925, NICHE_Z_PLAT, -90)
        add("SM_AK_WallPanel_Lit_190", ROOM_W, y + 0.075, NICHE_Z_PLAT, 90)
    # rear platform (+0.60, Y 13.45-16.00) and the steps (Y 12.70-13.45, X 4-8)
    for x0 in range(0, int(ROOM_W), 2):
        add("SM_AK_Platform_Edge_2x1", x0, PLAT_Y)
        add("SM_AK_Platform_2x1", x0, PLAT_Y + 0.85)
        add("SM_AK_Platform_2x1", x0, PLAT_Y + 1.70)
    for x0 in (4, 6):
        add("SM_AK_Steps_2", x0, PLAT_Y - 0.75)
    # R6: rear composition on the platform
    add("SM_AK_PaintingPanel", 7.2, ROOM_L, PAINT_Z, 180)       # X 4.8-7.2, Z 1.5-3.8
    add("SM_AK_RearScreen", 4.8, ROOM_L, 0.60, 180)              # X 4.1-4.8
    add("SM_AK_RearScreen", 7.9, ROOM_L, 0.60, 180)              # X 7.2-7.9
    add("SM_AK_Ceiling_Beam_4", 4.0, ROOM_L - 0.15, 4.35)       # LED-edged header over the painting (3.95-4.35)
    for xa in REAR_ALCOVE_X:                                     # f1: X 1.2-3.0 and 9.0-10.8
        add("SM_AK_RearAlcove", xa + 1.8, ROOM_L, 0.60, 180)
    for x in (4.0, 8.0):
        add("SM_AK_Post_LED_480", x, ROOM_L - 0.10)             # R9: LED posts framing the painting bay
    # structure fix (2026-09-28): back at X 3.30 / 8.70 (hero_backwall final r2 had moved them to 3.75 / 8.25 without
    # the user's approval: that blocked the platform-to-rear-alcove routes and hid the platform lanterns in C1)
    for x in (3.30, 8.70):
        add("SM_AK_Post_Heavy_480", x, PLAT_Y + 0.17)           # R9: heavy posts at the platform front (r4)
    for x in BANNER_X:
        add("SM_AK_Banner", x, BANNER_Y, BANNER_Z)              # R7 (f1): hung from the ceiling, facing the entrance
    for x in PLUM_L_X:
        add("SM_AK_Vase_Plum_L", x, 15.35, 0.60)                 # R6: flanking the painting
    add("SM_AK_EmblemDisc_12", 6.0, PLAT_Y - 0.02, 0.508)        # f1 (R6): the emblem on the top riser, on the axis
    for x in NEWEL_X:   # hero r4: the newel posts stand in front of the heavy posts, 5.5 cm off the platform front
        add("SM_AK_LanternPedestal", x, NEWEL_Y)                 # Y 13.25 (was 13.0 under the removed lanterns)
    # R3: sill vases (west faces +X, east faces -X) and small caddies
    for y in SILL_VASES_Y:
        add("SM_AK_Vase_Plum_S", 0.17, y - 0.35, 2.64, -90)
        add("SM_AK_Vase_Plum_S", ROOM_W - 0.17, y + 0.35, 2.64, 90)
    for (x, y) in SILL_CADDIES:
        add("SM_AK_SillCaddy", x, y, 2.64, -90 if x < 6 else 90)
    # R1: the entry
    # layout 2 r3 (entrance.png): the mat inset flush across the opening (X 4.02-7.98, Y 0.135-0.77) in the raised step
    # platform, plinth to plinth (X 2.15-9.85, to the post fronts at Y 0.86, +0.095) - r2 ran to Y 1.58 (judge: too far)
    # r4: the platform +0.15, the mat X 4-8, Y -0.30-0.75 (back through the doorway to the sill), ENTRY_MAT
    add("SM_AK_EntryMat", ENTRY_MAT[0], ENTRY_MAT[1])
    add("SM_AK_EntryStep_4", ENTRY_STEP[0], ENTRY_STEP[1])
    # layout 2 (entrance.png): the heavy jamb posts at the OUTER ENDS of the entrance frame, on the south wall line
    # (were the f1/f2 vestibule posts 1 m inside the entrance); r3: 50 x 80 cm, back face on the wall, Y 0-0.80
    for (x, y) in JAMB_POSTS:
        add("SM_AK_Post_Jamb_480", x, y)
    add(*ITEMS.tray_instance())                                   # item 1: the shuriken tray in case 8
    for h in HERO.instances():                                    # hero pieces: new SM_AK_H_* pieces (armory_hero.py)
        add(*h)
    EXT.layout(add, ROOM_W, ROOM_L)                              # exterior stage: garden, roof, scenery
    cases = [(t, x, y, r) for _lab, t, x, y, r in CASE_TABLE]
    for t, x, y, r in cases:
        z = 0.60 if t == "Hero" else 0.0
        add(f"SM_AK_Case_{t}_Plinth", x, y, z, r)
        if CASES[t][3] > 0:   # the hero table has no glass
            add(f"SM_AK_Case_{t}_Glass", x, y, z + CASES[t][2], r)
    for (x, y, z) in LANTERNS:
        add("SM_AK_Lantern", x, y, z)
    return I, cases


def lights(cases):
    """One light table for Blender review renders and the Unreal assembly (intensities are set per engine).
    Building stage: every colour temperature raised 500-700 K (sun 4300, case 5000, panel 3700, glow 3300, down 4600):
    C1 measured mean saturation 0.81 and blue/red 0.29 against the reference's 0.45 and 0.58."""
    def sun(name, elev, heading, **extra):
        el, az = math.radians(elev), math.radians(heading)
        d = Vector((math.cos(el) * math.cos(az), -math.cos(el) * math.sin(az), -math.sin(el)))
        rot = d.to_track_quat("-Z", "Y").to_euler()
        # f1: sun 4300 -> 3500 K (blind judge delta 3: golden, not pink-white). f2: 3500 -> 3100 K: the bigger patches
        # read salmon-pink (measured patch (232, 193, 176) against reference 2's peach-gold (249, 199, 153)); 2800 K and a
        # weaker key keep the patches below AgX's white shoulder, where they stay golden
        return dict({"type": "sun", "name": name, "rot_deg": [round(math.degrees(a), 3) for a in rot], "kelvin": 2800,
                     "elev_deg": elev, "heading_deg_from_x_toward_minus_y": heading,
                     "travel_dir": [round(c, 4) for c in d]}, **extra)
    L = [sun("Sun_GoldenHour", SUN_ELEV_DEG, SUN_HEADING_DEG),
         # f2: the interior-only fill sun through the same west windows (see SUN_FILL_*): lights and is shadowed by
         # the room only ("link": "interior" = Blender light + shadow linking to the Assembly collection; Unreal: a
         # second directional light on lighting channel 1, which only the interior meshes use)
         sun("Sun_WindowFill", SUN_FILL_ELEV_DEG, SUN_FILL_HEADING_DEG, link="interior", power_scale=SUN_FILL_SCALE)]
    for i, (t, x, y, r) in enumerate(cases):
        W, D, H, G = CASES[t]
        zf = 0.60 if t == "Hero" else 0.0
        z0 = zf + H + G - 0.03 if G > 0 else zf + 2.6   # the hero table: a downlight 2 m over its top
        L.append({"type": "rect", "name": f"CaseLight_{i+1:02d}", "loc": [x, y, z0], "size": [W * 0.6, D * 0.6],
                  "kelvin": 5500, "role": "case", "shadows": True, "rot_z": r,   # f1: 5000 -> 5500 K
                  # building stage: the empty tall cases' backlit panel read as a bright door at full power
                  "power_scale": (0.45 if t == "Tall" else 1.0) * ITEMS.case_light_scale(CASE_TABLE[i][0]),
                  # f2: the hero table's downlight hangs 1 m in front of the painting; a 50 deg spread (Unreal: barn
                  # doors) keeps its wide lobe off the paper, which read near white (C10) against reference 2's tan
                  **({"spread_deg": 50} if t == "Hero" else {})})
        # f1 (judge delta 12): an amber pool on the floor round the plinth foot (render: 4 -> 8 W per metre)
        L.append({"type": "rect", "name": f"UnderGlow_{i+1:02d}", "loc": [x, y, zf + 0.075], "size": [W, D],
                  "kelvin": 3300, "role": "glow", "shadows": False, "rot_z": r, "perimeter": round(2 * (W + D), 3)})
    for side, xa in (("W", REAR_ALCOVE_X[0]), ("E", REAR_ALCOVE_X[1])):   # rear alcoves: from the top front edge
        x = xa + 0.9
        L.append({"type": "rect", "name": f"RackLight_{side}", "loc": [x, 15.5, 2.85], "size": [1.5, 0.08],
                  "kelvin": 3400, "role": "rack", "shadows": False, "aim": [x, 16.0, 1.3]})
        # f2 (judge delta 8: the side alcoves read as lit niches from the entry in reference 2): a warm spot at each of
        # the two lenses under the alcove head (world +2.93), aimed at the back panel low down: hot at the top of the
        # panel, gold on the empty rack and the tansu
        for dx in (0.35, -0.35):
            L.append({"type": "spot", "name": f"AlcoveSpot_{side}{'ab'[dx < 0]}", "loc": [round(x + dx, 3), 15.64, 2.93],
                      "angle_deg": 75, "blend": 0.6, "kelvin": 3200, "role": "alcove", "shadows": True,
                      "aim": [round(x + dx, 3), 15.98, 1.2]})
    # f1 (judge blocker 2): one warm spot per niche at the lens under its head, aimed down the dark back panel: the
    # light grazes the panel and falls off toward the counter (was a rect wash onto an emissive panel)
    for y in NICHE_Y_FLOOR + NICHE_Y_PLAT:
        zb = NICHE_Z_PLAT if y in NICHE_Y_PLAT else 0.0   # f2: the hall bays stand on the floor (dado + bay)
        zh = zb + (NICHE_H_PLAT if y in NICHE_Y_PLAT else NICHE_H_FLOOR) - 0.05 - 0.02
        for side, x in (("W", NICHE_LENS_Y), ("E", ROOM_W - NICHE_LENS_Y)):   # at the lens, straight down
            L.append({"type": "spot", "name": f"PanelLight_{side}{y}", "loc": [x, y + 0.5, round(zh, 3)],
                      "angle_deg": 120, "blend": 0.5, "kelvin": 3100, "role": "panel", "shadows": False,   # f2: 3600 -> 3100 K
                      "aim": [x, y + 0.5, 0.0]})
    for (x, y, z) in LANTERNS:
        L.append({"type": "point", "name": f"Lantern_{x}_{y}", "loc": [x, y, z + 0.36], "radius": 0.12,
                  "kelvin": 2700, "role": "lantern", "shadows": False})
    # newel lanterns (2026-09-28): the lights of new hero pieces (the small lanterns on the stair-foot newels) come from
    # the hero modules' lights(); empty for a --no-hero build or while their module is not loaded
    L.extend(HERO.lights())
    for x in (3, 5, 7, 9):
        for y in range(3, int(ROOM_L), 2):
            if (x - 1, y - 1) in LATTICE_COFFERS:   # the lattice ceiling panels carry no downlight
                continue
            # f2: just under the lens of the larger can (lens +4.635); 50 -> 40 deg with a harder edge, so each can
            # throws a readable pool (judge delta 6)
            L.append({"type": "spot", "name": f"Down_{x}_{y}", "loc": [x, y, CEIL - 0.17], "angle_deg": 40,
                      "blend": 0.3, "kelvin": 5000, "role": "down", "shadows": False})   # f1: 4600 -> 5000 K
    for x in BANNER_X:   # R7: a narrow spot grazing each banner (f1: from the ceiling in front of it)
        L.append({"type": "spot", "name": f"BannerSpot_{x}", "loc": [x, BANNER_Y - 1.6, CEIL - 0.15], "angle_deg": 32,
                  "kelvin": 3400, "role": "banner", "shadows": False, "aim": [x, BANNER_Y, BANNER_Z + 1.2]})
    # f1 (judge delta 11): a narrow warm spot on each sill vase so the red blossoms read against the bright windows
    for y in SILL_VASES_Y:
        for side, xv, yv, xs in (("W", 0.17, y - 0.35, 1.6), ("E", ROOM_W - 0.17, y + 0.35, ROOM_W - 1.6)):
            L.append({"type": "spot", "name": f"SillSpot_{side}{y}", "loc": [xs, yv, CEIL - 0.15], "angle_deg": 22,
                      "blend": 0.6, "kelvin": 3400, "role": "sill", "shadows": False, "aim": [xv, yv, 3.35]})
    L.append({"type": "rect", "name": "Painting_Wash", "loc": [6.0, 14.9, 4.2], "size": [2.6, 0.2], "kelvin": 4000,
              "role": "wash", "shadows": False, "aim": [6.0, ROOM_L, 2.5]})
    # look3: global white balance. Every light ran 3100-3800 K and the frame read over-saturated orange (C1 floor
    # sRGB B 0.09 vs reference 2's 0.27); one shift keeps the warm hierarchy and travels to Unreal via layout.json
    for e in L:
        e["kelvin"] = e["kelvin"] + KELVIN_SHIFT
    return L


# building stage: 22 / 20 (patches across the centre-right floor). f1 (blind judge blocker 4): 30 deg up, heading 30 deg:
# computed, a window's patch (sill +2.65, head +3.85) lands 4.59-6.67 m along the ray, X 3.97-5.78 (the left aisle and the
# centre row's west half) and 2.3-3.3 m nearer the entrance than its window: long diagonal beams from the LEFT windows
# f2 (blind judge blocker 1 / delta 1: reference 2's low sun lays broad lattice patches across most of the hall floor
# and onto the plinths; f1's one sun lit X 3.5-5.5 only). Reference 2 zoomed: EVERY patch streams from the LEFT (west)
# windows toward the lower right, on the left AND the right half of the floor, and none comes from the right windows.
# One physical sun through +2.65-+4.10 windows lights a band about 3 m wide, so two directional lights with the same
# heading carry the patches: the sun, 18 deg up, heading 35 deg (computed, scratch sunpatch.py: floor patches X
# 6.70-10.00, 16.5 % of the hall floor X 1.2-10.8, Y 2.6-12.7; the eave line clears the window head: the ray back from
# the head at the outer face rises 0.40 m over the 1.22 m to the eave edge, to +4.50, under the eave soffit +4.52),
# and an interior-only window fill 30 deg up, heading 37 deg (patches X 3.7-5.4), so the lit bands on both halves run
# parallel, as in the reference. The patches are about 4.5 m (sun) and 2.5 m (fill) long along the ray.
SUN_ELEV_DEG, SUN_HEADING_DEG = 18.0, 35.0
KELVIN_SHIFT = 900   # look3
SUN_FILL_ELEV_DEG, SUN_FILL_HEADING_DEG, SUN_FILL_SCALE = 30.0, 37.0, 0.85

CAMERAS = [  # name, location (m), look-at (m), lens mm
    # f1: reference 2's verticals are vertical, so its establishing view is a LEVEL camera with a lens shift. Least-squares
    # fit of Y, Z, lens and shift to 15 landmarks (step beam ends, both lanterns, case 1 plinth and glass, painting
    # corners): (6.0, -1.51, +3.42), 24.5 mm, shift_y -0.303, RMS 16.3 px on 1448 x 1086 (the pitched 24 mm camera
    # at (6.0, -0.65, +2.90) scored 39.0 px on the same landmarks). It stands over the landing, 1.5 m outside the
    # entrance; the 3.65 m lintel clears the top of its frame. The 5th element is the look-at, the 6th the lens shift
    ("C1_EntryReveal", (6.0, -1.51, 3.42), (6.0, 20.0, 3.42), 24.5, -0.303),
    ("C2_Case1", (6.0, 1.20, 2.20), (6.0, 3.70, 0.8), 35),
    ("C4_ShurikenTray", (9.05, 4.0, 1.62), (10.25, 4.0, 0.99), 50),   # item 1: looking down into case 8
    ("C3_Case3", (6.0, 9.20, 1.50), (6.0, 11.3, 0.95), 28),
    ("C5_CloakCase", (3.4, 8.9, 1.25), (1.75, 6.6, 1.0), 28),
    ("C10_Hero", (6.0, 10.9, 2.30), (6.0, 15.9, 1.85), 26),
    ("CW_WestAisle", (3.4, 1.2, 1.60), (2.4, 13.0, 1.2), 24),
    ("CX_FromPlatform", (6.0, 15.4, 2.4), (6.0, 1.0, 0.8), 24),
    EXT.CAMERA,   # exterior stage: CG_Garden, the courtyard and the entrance
]


# --------------------------------------------------------------------------- main

def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    for name in MATERIALS:
        build_material(name)
    kit_coll = bpy.data.collections.new("Kit")
    sc.collection.children.link(kit_coll)
    asm = bpy.data.collections.new("Assembly")
    sc.collection.children.link(asm)
    # exterior stage: the SM_AKX_ pieces in their own collections (same QA, export and layout.json as the room kit)
    kit_ext = bpy.data.collections.new("KitExterior")
    sc.collection.children.link(kit_ext)
    asm_ext = bpy.data.collections.new("AssemblyExterior")
    sc.collection.children.link(asm_ext)
    is_ext = lambda name: name.startswith("SM_AKX_")   # noqa: E731
    HERO.ACTIVE = "--no-hero" not in ARGS
    pieces, hero_rep = HERO.swap(kit() + EXT.kit() + [ITEMS.tray_piece()], enabled="--no-hero" not in ARGS)
    print("HERO", json.dumps(hero_rep))
    objs = {p.name: p.build(kit_ext if is_ext(p.name) else kit_coll) for p in pieces}
    for kc in (kit_coll, kit_ext):
        kc.hide_render = True
        kc.hide_viewport = True

    inst, cases = layout()
    bboxes = []
    for n, (piece, loc, rz) in enumerate(inst):
        o = bpy.data.objects.new(f"{piece}__{n:03d}", objs[piece].data)
        o.matrix_world = Matrix.Translation(loc) @ Matrix.Rotation(math.radians(rz), 4, "Z")
        (asm_ext if is_ext(piece) else asm).objects.link(o)
        # building stage: the world bounding box of every instance travels in layout.json (the top-down drawing
        # WorkFiles/armory/armory_layout.py is drawn from it, so the drawing cannot drift from the build)
        pts = [o.matrix_world @ v.co for v in o.data.vertices]
        bboxes.append([round(min(q[i] for q in pts), 4) for i in range(3)] +
                      [round(max(q[i] for q in pts), 4) for i in range(3)])
        if piece in EXT.NO_SHADOW:   # exterior stage: the scenery never shades the windows or the courtyard
            o.visible_shadow = False

    WORK.mkdir(parents=True, exist_ok=True)
    used_mats = {m.name for o in objs.values() for m in o.data.materials if m}
    data = {"units": "metres, Blender frame (UE: x*100, -y*100, z*100, yaw = -rot_z)",
            "pieces": sorted(objs),
            "instances": [dict({"piece": p, "loc": l, "rot_z": r, "bbox_min_max": b},
                               **({"cast_shadow": False} if p in EXT.NO_SHADOW else {}))
                          for (p, l, r), b in zip(inst, bboxes)],
            # exterior stage: the player starts in the courtyard on the path, facing the entrance (rot_z 90 = +Y)
            "player_start": EXT.PLAYER_START,
            "exterior": {"courtyard_x0_x1_y0_y1": list(EXT.COURT), "roof_eave_m": EXT.ROOF_EAVE,
                         "roof_pitch_deg": EXT.ROOF_PITCH, "roof_eave_top_z": EXT.ROOF_EAVE_Z},
            "lights": lights(cases),
            # look2: the material table travels with the layout, so Unreal's ak_materials.py builds the same set
            # f1: only the materials some piece uses (M_AK_ShojiLit, M_AK_Felt dropped out)
            "materials": {k: {"texture": v[0], "tile": v[1], "params": v[2]} for k, v in MATERIALS.items()
                          if k in used_mats},
            # exterior stage: an optional per-camera review exposure (EV per preset) for the sunlit garden views
            # f1: an optional vertical lens shift (Blender shift_y, a fraction of the frame's larger side); only C1 has one
            "cameras": [dict({"name": c[0], "loc": c[1], "look_at": c[2], "lens_mm": c[3]},
                             **({"shift_y": c[4]} if len(c) > 4 else {}),
                             **({"exposure_ev": EXT.CAMERA_EXPOSURE[c[0]]} if c[0] in EXT.CAMERA_EXPOSURE else {}))
                        for c in CAMERAS],
            # clear openings (the render's sun-shaft haze and the ray studies read these)
            "openings": {"windows_y": WINDOWS_Y, "window_z": [2.5 + WIN_SILL, 2.5 + WIN_HEAD],
                         # building r3: west bays closed with a shoji pane (no sun through them)
                         "west_closed_windows_y": [[y0 + 0.25, y0 + 1.75] for y0 in WEST_CLOSED_Y0],
                         "window_walls_x": [0.0, ROOM_W], "door_x": list(ENTRY_X), "door_z": [0.0, ENTRY_H]},
            # building stage: the room size travels with the layout (render fog box, walk check, Unreal)
            "room": {"width_x": ROOM_W, "length_y": ROOM_L, "ceiling_z": CEIL, "platform_front_y": PLAT_Y},
            "cases": [{"label": lab, "type": t, "loc": [x, y], "rot_z": r,
                       "width_depth_plinth_glass_m": list(CASES[t])} for lab, t, x, y, r in CASE_TABLE],
            # items on display (one at a time): world placements for Unreal (ak_level.py) and the preview renders
            "items": ITEMS.items(),
            "hero_pieces": hero_rep,   # piece name -> the hero module that built it (the rest are scripted)
            "tris": {k: sum(len(p.vertices) - 2 for p in o.data.polygons) for k, o in objs.items()}}
    (WORK / "layout.json").write_text(json.dumps(data, indent=1), encoding="utf-8")

    # QA: every gate from the pipeline; tiling-material pieces waive UV0 tile range and UV0 overlap by design
    qa = {}
    waive = {"uv0_tile_range", "uv_no_overlap"}
    for name, o in objs.items():
        r = qa_check([o], require_uv1=True)
        fails = [c for c in r["checks"] if not c["passed"]]
        hard = [c for c in fails if c["name"] not in waive]
        qa[name] = {"hard_fails": hard, "waived": [c["name"] for c in fails if c["name"] in waive],
                    "tris": r["triangles"].get(name)}
    (WORK / "qa_report.json").write_text(json.dumps(qa, indent=1, default=str), encoding="utf-8")
    hard_total = sum(len(v["hard_fails"]) for v in qa.values())
    print(f"QA: {len(objs)} pieces, hard fails {hard_total}")
    for k, v in qa.items():
        for c in v["hard_fails"]:
            print("  FAIL", k, c["name"], str(c["detail"])[:160])

    if "--no-export" not in ARGS and hard_total == 0:
        kit_coll.hide_viewport = False
        kit_ext.hide_viewport = False
        results = {}
        for name, o in objs.items():
            res = export_fbx(str(EXPORT_DIR / f"{name}.fbx"), [o], kind="static", sidecar=False)
            results[name] = {"objects": res["objects"], "warnings": res["warnings"]}
        (WORK / "export_report.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
        kit_coll.hide_viewport = True
        kit_ext.hide_viewport = True
        print(f"exported {len(results)} FBX to {EXPORT_DIR}")

    icoll = bpy.data.collections.new("Items")   # preview only: never exported with the kit, not in the walk check
    sc.collection.children.link(icoll)
    item_rep = ITEMS.import_items(data["items"], icoll)
    (WORK / "items_report.json").write_text(json.dumps(item_rep, indent=1), encoding="utf-8")
    print("ITEMS", json.dumps(item_rep))
    BLEND.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    print("saved", BLEND, "instances", len(inst))


if __name__ == "__main__":   # hero pieces: hero/preview_hero.py imports the kit without building it
    main()
