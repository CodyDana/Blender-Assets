"""Blender side of smg_maps_vs_clay.py (SMG01 W4 resume, spec R45): smg_texrender.py's close-ups with one variant.

    blender -b <SMG01 W2 blend> --factory-startup --python Scripts/guns/smg/smg_maps_vs_clay_bl.py -- \
        --variant tex|flat --rig rough|studio --consts <json> --out DIR [--samples 96]

tex   the game materials on the shipped maps (gunlib.game.game_material), exactly as smg_texrender
flat  the same material with BC / roughness / metallic / normal unplugged and set to the per-set constants in --consts
      (the maps' medians): a constant per-set "clay" with the same mean colour
rough the texrender rig (grey world 126 at 0.3 + gunlib.look.rough_lights)
studio the realism views' studio rig (gunlib export_review_job 'studio': Blender's bundled studio HDRI, saturation 0,
      strength 0.6, + rough_lights at 0.35 of the texrender scale; the camera sees the grey backdrop)
Review only: nothing here is exported.
"""
from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import bpy  # noqa: E402
from gunlib import game as GM  # noqa: E402
from gunlib import look as LK  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]


def arg(n, d=None):
    return argv[argv.index(n) + 1] if n in argv else d


VAR, RIG = arg("--variant", "tex"), arg("--rig", "rough")
CONSTS = json.loads(Path(arg("--consts")).read_text()) if arg("--consts") else {}
_orig_gm = GM.game_material


def _gm(name, stem, tex):
    m = _orig_gm(name, stem, tex)
    if VAR != "flat":
        return m
    st = stem.split("_")[-1]
    c = CONSTS[st]
    nt = m.node_tree
    bs = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    for sock in ("Base Color", "Roughness", "Metallic", "Normal"):
        for ln in list(bs.inputs[sock].links):
            nt.links.remove(ln)
    bs.inputs["Base Color"].default_value = (*LK.srgb_to_lin(c["bc_srgb"]), 1.0)
    bs.inputs["Roughness"].default_value = float(c["rough"])
    bs.inputs["Metallic"].default_value = 0.0
    return m


GM.game_material = _gm

if RIG == "studio":
    def _world(sc, rgb=(126, 126, 126), env=0.45):
        w = bpy.data.worlds.new("MVC_Studio")
        sc.world = w
        w.use_nodes = True
        nt = w.node_tree
        bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
        bg.inputs["Color"].default_value = (*LK.srgb_to_lin(rgb), 1.0)
        bg.inputs["Strength"].default_value = 1.0
        d = Path(bpy.utils.system_resource("DATAFILES", path="studiolights/world"))
        env_n = nt.nodes.new("ShaderNodeTexEnvironment")
        env_n.image = bpy.data.images.load(str(d / "studio.exr"), check_existing=True)
        hs = nt.nodes.new("ShaderNodeHueSaturation")
        hs.inputs["Saturation"].default_value = 0.0
        nt.links.new(env_n.outputs["Color"], hs.inputs["Color"])
        bg2 = nt.nodes.new("ShaderNodeBackground")
        bg2.inputs["Strength"].default_value = 0.6
        nt.links.new(hs.outputs["Color"], bg2.inputs["Color"])
        lp = nt.nodes.new("ShaderNodeLightPath")
        mix = nt.nodes.new("ShaderNodeMixShader")
        out = next(n for n in nt.nodes if n.type == "OUTPUT_WORLD")
        nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
        nt.links.new(bg2.outputs["Background"], mix.inputs[1])
        nt.links.new(bg.outputs["Background"], mix.inputs[2])
        nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
        sc.render.film_transparent = True
        return w

    _orig_lights = LK.rough_lights

    def _lights(cam_ob, target_B, dist=1.1, k=1.0):
        _orig_lights(cam_ob, target_B, dist, k * 0.35)

    LK.rough_world = _world
    LK.rough_lights = _lights

sys.argv = [sys.argv[0], "--", "--set", "closeups", "--out", arg("--out"), "--samples", arg("--samples", "96")] +     (["--tex", arg("--tex")] if arg("--tex") else [])
runpy.run_path(str(HERE / "smg_texrender.py"), run_name="__main__")
print("[maps-vs-clay] DONE", VAR, RIG)
