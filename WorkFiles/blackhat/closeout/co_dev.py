"""Surface pass DEV loop (not shipped): geometry + atlas + paint + maps (no AO bake: Cycles never
reads ORM.R) + LOD0 + the reference view + side-by-side + 3x crops + region metrics.

  blender -b --factory-startup --python sp_dev.py -- OUTDIR [--samples 64] [--extra-crops]
"""
import sys, json, time
from pathlib import Path
PROJECT = Path("C:/Users/Cody/Desktop/Blender_Projects")
sys.path.insert(0, str(PROJECT / "Scripts"))
sys.path.insert(0, str(PROJECT / "Scripts" / "props"))
import bpy
import numpy as np
import build_black_hat as BB
from props_lib import blackhat_camera as CAM, blackhat_look as LK, blackhat_paint as BP
from props_lib.blackhat_spec import BLACK_HAT

argv = sys.argv[sys.argv.index("--") + 1:]
out = Path(argv[0]); out.mkdir(parents=True, exist_ok=True)
samples = int(argv[argv.index("--samples") + 1]) if "--samples" in argv else 64
T0 = time.time()
if "--filter" in argv:
    _fw = float(argv[argv.index("--filter") + 1])
    _orig = LK._cycles
    def _cy(scene, samples, denoise=False):
        _orig(scene, samples, denoise)
    LK.FILTER_WIDTH = _fw
if "--spec-straw" in argv:
    LK.SPEC_SCALE["straw"] = float(argv[argv.index("--spec-straw") + 1])
bpy.ops.wm.read_factory_settings(use_empty=True)
spec = BLACK_HAT
cam = CAM.RefCamera(spec)
report = {}
BB.TEXTURES = out / "Textures"
BB.TEXTURES.mkdir(parents=True, exist_ok=True)
builders, tails = BB.stage_geometry(spec, cam, report)
print("TRIS", [mb.triangles() for mb in builders], {k: sum(len(builders[0].F[i]) - 2 for i in v) for k, v in builders[0].parts.items()})
at, uvs = BB.stage_atlas(spec, builders, report)
hat = BB.G.Hat(spec)
maps, paths = {}, {}
for k in ("straw", "cloth"):
    ch = BP.paint_atlas(builders[0], at[k], seed=spec.seed, hat=hat, log=print)
    maps[k] = BP.finish(ch, BB.CHROMA[k], rough_range=BB.ROUGH_RANGE[k])
    paths[k] = {kk: LK.write_png(BB.TEXTURES / f"{BB.STEMS[k]}_{kk}.png", maps[k][kk]) for kk in ("BC", "ORM", "N", "Detail")}
    print(k, "recolour", maps[k]["recolour"]["detail_levels_used"], maps[k]["recolour"]["detail_min_max_code"],
          maps[k]["recolour"]["mean_of_bias_plus_scale_x_detail"], "rough", maps[k]["roughness_stats"],
          "mip", BB.mip_parity(maps[k])["max_abs_pct"])
mats = {k: BB._material(BB.MATS[k], paths[k], maps[k], k, pack=False) for k in ("straw", "cloth")}
lod0 = LK.to_blender(builders[0], uvs[0], "SM_BlackHat", [mats["straw"], mats["cloth"]])
print("paint done", round(time.time() - T0, 1))
ref_png = out / "ref_view.png"
LK.reference_view(lod0, cam, ref_png, out, samples=samples)
LK.side_by_side(str(BB.REFERENCE), ref_png, out / "sbs.png")
LK.crops_sheet(str(BB.REFERENCE), ref_png, out / "crops.png", BB.CROPS3X, scale=3)
# extra crops: more of what the judge saw
extra = [(20, 280, 140, 350), (140, 330, 260, 410), (440, 300, 560, 380), (300, 140, 380, 180), (450, 190, 520, 250)]
LK.crops_sheet(str(BB.REFERENCE), ref_png, out / "crops_extra.png", extra, scale=4)
fid = BB.fidelity(ref_png)
gates = BB.fidelity_gates(fid)
# region metrics (m1 boxes): p50 linear lum and high-pass std (sRGB), + "pale" share (> 1.8x local p30)
ref = LK.load_png(BB.REFERENCE)[..., :3].astype(np.float64)
ren = LK.load_png(ref_png)[..., :3].astype(np.float64)
W3 = np.array([0.2126, 0.7152, 0.0722])
boxes = {'front_bay': (300, 330, 380, 380), 'left_worn': (80, 250, 200, 330), 'left_mid': (170, 230, 260, 300),
         'right_bay': (560, 270, 630, 320), 'knot': (445, 205, 480, 240), 'tailA': (565, 440, 600, 510),
         'tailB': (615, 430, 645, 500), 'rim_front': (240, 405, 440, 432), 'cap': (305, 145, 365, 160),
         'upper_cone': (250, 170, 330, 210)}
met = {}
for nm, img in (("ref", ref), ("ren", ren)):
    S = img @ W3
    L = BP.srgb_decode(img) @ W3
    for k, (x0, y0, x1, y1) in boxes.items():
        a = S[y0:y1, x0:x1]
        m = a < 0.6
        blur = (a[:-2, 1:-1] + a[2:, 1:-1] + a[1:-1, :-2] + a[1:-1, 2:] + a[1:-1, 1:-1]) / 5
        h = (a[1:-1, 1:-1] - blur)[m[1:-1, 1:-1]]
        l = L[y0:y1, x0:x1][m]
        pale = float(np.mean(l > 1.8 * np.percentile(l, 30))) if l.size else 0
        met.setdefault(k, {})[nm] = [round(float(np.median(l)), 4), round(float(h.std()), 4), round(pale, 3),
                                     round(float(np.percentile(l, 95)), 4)]
res = {"gates": gates, "dev": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in fid["deviation"].items()
                               if k != "tail_tip_reference_measured_px"},
       "lum": [fid["reference"]["object_lum_lin_p10_50_90"], fid["render"]["object_lum_lin_p10_50_90"]],
       "chroma": [fid["reference"]["object_chroma"], fid["render"]["object_chroma"]],
       "regions [p50, hp_std, pale, p95]": met}
(out / "metrics.json").write_text(json.dumps(res, indent=1))
print("METRICS", json.dumps(res, indent=1))
bpy.ops.wm.save_as_mainfile(filepath=str(out / "dev.blend"))
print("done", round(time.time() - T0, 1))
