# final-pass experiment: why does the pack front render lift and flatten the black ink?
# Renders the flat front of Assets/PaperBomb.blend (baked maps) under the pack's flat rig
# in several variants into exact/fx/ and measures black-core luminance like the judge.
import sys, json, math
from pathlib import Path
PROJECT = Path("C:/Users/Cody/Desktop/Blender_Projects")
sys.path.insert(0, str(PROJECT / "Scripts")); sys.path.insert(0, str(PROJECT / "Scripts" / "props"))
import bpy, numpy as np
from props_lib import render as R
from props_lib import gallery as G
from props_lib.spec import PAPER_BOMB as spec

OUT = PROJECT / "WorkFiles/paperbomb/exact/fx"; OUT.mkdir(parents=True, exist_ok=True)
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
variants = argv[0].split(",") if argv else ["base", "matte", "nodn", "matte_nodn"]
samples = int(argv[1]) if len(argv) > 1 else 320

lod0 = next(o for o in bpy.data.objects if o.type == "MESH" and o.name.endswith("LOD0"))
mat = lod0.data.materials[0]
tree = mat.node_tree
imgs = {n.image.name: n for n in tree.nodes if n.type == "TEX_IMAGE" and n.image}
print("images", list(imgs))
orm_node = next(n for k, n in imgs.items() if k.endswith("_ORM"))
m_node = next(n for k, n in imgs.items() if k.endswith("_M"))
orm_img = orm_node.image; w, h = orm_img.size
orm0 = np.empty(w * h * 4, np.float32); orm_img.pixels.foreach_get(orm0)
orm0 = orm0.reshape(h, w, 4)
mm = np.empty(w * h * 4, np.float32); m_node.image.pixels.foreach_get(mm); mm = mm.reshape(h, w, 4)
ink = mm[..., 2]
paper_sel = ink < 0.02
rp = float(np.median(orm0[..., 1][paper_sel & (orm0[..., 1] > 0.5)]))
print("paper roughness median", rp, "ink roughness median", float(np.median(orm0[..., 1][ink > 0.9])))

for o in bpy.data.objects:
    if o.type == "MESH":
        o.hide_render = True
dev = R.setup_render(samples=samples)
rig = R.build_rig(spec)
front = G._clone(lod0, "PREVIEW_Front")
front.hide_render = False
cam = rig["cam_flat"]
cam.rotation_euler = (0.0, 0.0, math.radians(-90.0)); cam.location = (0.0, 0.0, 0.40)
cam.data.ortho_scale = (spec.height_mm / G.FLAT_FILL) * 0.001 * R.RES_X / R.RES_Y
scene = bpy.context.scene
bsdf = next(n for n in tree.nodes if n.type == "BSDF_PRINCIPLED")
for v in variants:
    orm = orm0.copy()
    if "matte" in v:
        orm[..., 1] = orm0[..., 1] * (1 - ink) + (float(v.split("matte")[1][:2]) / 100 if v.split("matte")[1][:2].isdigit() else rp) * ink
    orm_img.pixels.foreach_set(orm.ravel()); orm_img.update()
    scene.cycles.use_denoising = "nodn" not in v
    spec_lvl = 0.0 if "nospec" in v else 0.5
    bsdf.inputs["Specular IOR Level"].default_value = spec_lvl
    p = OUT / f"fx_front_{v}.png"
    R.render_to(p, cam, rig["flat"])
    print("rendered", v, p, flush=True)
orm_img.pixels.foreach_set(orm0.ravel())
