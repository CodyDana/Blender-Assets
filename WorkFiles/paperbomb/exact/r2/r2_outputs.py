"""Round outputs: <tag>_side_by_side.png, <tag>_diff.png, <tag>_emblem_x8.png (+ json of numbers).
usage: r1_outputs.py <tag>   (reads the SHIPPED Exports/PaperBomb/Textures/T_PaperBomb_BC.png and
Renders/PaperBomb/paperbomb_front.png, i.e. the baked maps and the render made from them)"""
import os, sys, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/exact")
import numpy as np
from props_lib import trace as T
from props_lib import paperbomb_trace as PT
from props_lib import paperbomb_tracedart as TA
from props_lib import paperbomb_fidelity as FD
from props_lib import atlas as AT
from props_lib.spec import PAPER_BOMB
import xt_io

ROOT = r"C:/Users/Cody/Desktop/Blender_Projects"
OUT = os.path.join(ROOT, "WorkFiles/paperbomb/exact")
tag = sys.argv[1] if len(sys.argv) > 1 else "r2"
plan = AT.plan_for(PAPER_BOMB)
ppmm, pad = plan.ppmm, plan.pad_mm
rw, rh = plan.raster

bc_all, _ = xt_io.read(os.path.join(ROOT, "Exports/PaperBomb/Textures/T_PaperBomb_BC.png"))
bc_st = bc_all[:rh, :rw, :3]
# THE FRONT RENDER held beside the reference: the flatbed-lit scan (paperbomb_gallery),
# rendered from the baked maps; the pack-exposed front is kept as a third panel
render, _ = xt_io.read(os.path.join(ROOT, "Renders/PaperBomb/paperbomb_front_scan.png"))
render = render[..., :3]
pack, _ = xt_io.read(os.path.join(ROOT, "Renders/PaperBomb/paperbomb_front.png"))
pack = pack[..., :3]

m = TA.reference_model()
src, fit = m.L.src, m.L.fit
ref = src.rgb


def samp(img, u, v):
    H, W = img.shape[:2]
    u = np.clip(u, 0, W - 1.000001); v = np.clip(v, 0, H - 1.000001)
    j = np.floor(u).astype(int); i = np.floor(v).astype(int)
    fu = (u - j)[..., None]; fv = (v - i)[..., None]
    return ((img[i, j] * (1 - fu) + img[i, np.minimum(j + 1, W - 1)] * fu) * (1 - fv)
            + (img[np.minimum(i + 1, H - 1), j] * (1 - fu)
               + img[np.minimum(i + 1, H - 1), np.minimum(j + 1, W - 1)] * fu) * fv)


# --- the render's own card fit (the same edge-crossing instrument as the reference's)
rsrc = T.Source(path="render", sha256="", nbytes=0, rgb=render, info={})
rfit = T.fit_card(rsrc)
print("render card fit", rfit.record()["corners_px"], "ppmm", round(rfit.ppmm, 3), "aspect", round(rfit.aspect, 5))

# --- 1. side by side at the same height and framing: the reference's whole frame, and
#        the render resampled so the card occupies exactly the same place in the frame
S = 2                       # output scale over the reference's 653 px
Ho, Wo = ref.shape[0] * S, ref.shape[1] * S
yy, xx = np.mgrid[0:Ho, 0:Wo]
spx = (xx + 0.5) / S; spy = (yy + 0.5) / S
xm, ym = fit.px_to_mm(spx, spy)
rpx, rpy = rfit.mm_to_px(xm, ym)
ours_r = samp(render, rpx - 0.5, rpy - 0.5)
ref_up = samp(ref, spx - 0.5, spy - 0.5)
gap = np.ones((Ho, 16, 3))
xt_io.write(os.path.join(OUT, tag + "_side_by_side.png"), np.concatenate([ref_up, gap, ours_r], 1))
psrc_ = T.Source(path="pack", sha256="", nbytes=0, rgb=pack, info={})
pfit = T.fit_card(psrc_)
ppx, ppy = pfit.mm_to_px(xm, ym)
pack_r = samp(pack, ppx - 0.5, ppy - 0.5)
xt_io.write(os.path.join(OUT, tag + "_side_by_side_packfront.png"), np.concatenate([ref_up, gap, ours_r, gap, pack_r], 1))

# --- 2. aligned difference.  Panels: dE2000 reference vs render (render exposure-matched
#        per channel on the bare paper, because the gallery light is not the reference's
#        flat scan) | dE2000 reference vs the BAKED BC map photographed at the reference's
#        grid | signed luma difference of the latter (red = ours darker, blue = ours lighter)
ours_rs = samp(render, *[a - 0.5 for a in rfit.mm_to_px(*fit.px_to_mm(np.mgrid[0:ref.shape[0], 0:ref.shape[1]][1] + 0.5,
                                                                   np.mgrid[0:ref.shape[0], 0:ref.shape[1]][0] + 0.5))])
bare = (m.L.black + m.L.red) < 0.03
yyp, xxp = np.mgrid[0:ref.shape[0], 0:ref.shape[1]] + 0.5
xmp, ymp = fit.px_to_mm(xxp, yyp)
card = (xmp > 0.8) & (xmp < 69.2) & (ymp > 0.8) & (ymp < 161.5)
bare &= card
gain = np.median(T.srgb_to_linear(ref)[bare], 0) / np.maximum(np.median(T.srgb_to_linear(ours_rs)[bare], 0), 1e-6)
ours_rs_m = T.linear_to_srgb(np.clip(T.srgb_to_linear(ours_rs) * gain, 0, 1))
de_render = T.delta_e2000(T.srgb_to_lab(ref), T.srgb_to_lab(ours_rs_m))
bc_lin = T.srgb_to_linear(bc_st)
card_mask = np.ones(bc_lin.shape[:2])
# the art raster's own card mask is not shipped; the octagon is re-derived from the outline
from props_lib import paperbomb_art as A
cfg = A.ArtConfig(ppmm=ppmm, pad_mm=pad, supersample=1)
W_, H_ = A.raster_size(cfg)
card_mask, _ = A._card_mask(cfg, A.LAYOUT, W_, H_)
card_mask = card_mask[:rh, :rw] if card_mask.shape[0] >= rh else np.pad(card_mask, ((0, rh - card_mask.shape[0]), (0, 0)), mode="edge")
card_mask = card_mask[:, :rw] if card_mask.shape[1] >= rw else np.pad(card_mask, ((0, 0), (0, rw - card_mask.shape[1])), mode="edge")
fid = FD.score(bc_lin, card_mask, ppmm, pad, model=m)
de_map = fid["_de"]
lum = np.array([0.2126, 0.7152, 0.0722])
dl = (fid["_photo"] - ref) @ lum


def heat(d, top=10.0):
    t = np.clip(d / top, 0, 1)
    return np.stack([np.clip(1.5 * t, 0, 1), np.clip(1.5 * t - 0.5, 0, 1), np.clip(3 * t - 2, 0, 1) * 0 + 0.15 * (1 - t)], -1)


def signed(d, top=0.25):
    t = np.clip(d / top, -1, 1)
    base = np.ones(d.shape + (3,))
    base[..., 1] -= np.abs(t)
    base[..., 0] -= np.clip(-t, 0, 1)
    base[..., 2] -= np.clip(t, 0, 1)
    return np.clip(base, 0, 1)


panels = [ref, ours_rs_m, heat(de_render), fid["_photo"], heat(de_map), signed(-dl)]
sep = np.ones((ref.shape[0], 6, 3))
row = []
for p in panels:
    row += [p, sep]
xt_io.write(os.path.join(OUT, tag + "_diff.png"), np.concatenate(row[:-1], 1), scale=2)

# --- 3. the emblem at 8x the reference: reference | ours (the baked BC map) | overlay
x0, y0, x1, y1 = 21.5, 18.5, 48.5, 43.6
F = 8
op = fit.ppmm * F
nx = int((x1 - x0) * op); ny = int((y1 - y0) * op)
exm, eym = np.meshgrid(x0 + (np.arange(nx) + 0.5) / op, y0 + (np.arange(ny) + 0.5) / op)
epx, epy = fit.mm_to_px(exm, eym)
e_ref = samp(ref, epx - 0.5, epy - 0.5)
e_ours = samp(bc_st, (exm + pad) * ppmm - 0.5, (eym + pad) * ppmm - 0.5)
# reference ink at half strength: the unmixed black field over its density, bilinear
kref = samp((m.L.black / m.L.density["black"])[..., None], epx - 0.5, epy - 0.5)[..., 0] > 0.5
lo = e_ours @ lum
paper_l = np.median((bc_st @ lum)[int(30 * ppmm):int(40 * ppmm), int(8 * ppmm):int(12 * ppmm)])
ink_l = float(np.array(T.BLACK_STORED) @ lum)
kours = lo < 0.5 * (paper_l + ink_l)
ov = np.repeat((e_ref @ lum)[..., None], 3, -1) * 0.35 + 0.65
ov[kref & kours] = [0.15, 0.15, 0.15]
ov[kours & ~kref] = [0.90, 0.10, 0.80]
ov[kref & ~kours] = [0.10, 0.70, 0.20]
sepv = np.ones((ny, 8, 3))
xt_io.write(os.path.join(OUT, tag + "_emblem_x8.png"), np.concatenate([e_ref, sepv, e_ours, sepv, ov], 1))
xor = float((kref ^ kours).sum()) / max(1.0, float((kref | kours).sum()))

# --- 4. the RENDER scored element by element: the scan photographed at the reference's
#        grid (4 x 4 footprint samples per reference pixel + the source PSF), unmixed by the
#        tracer's instrument, then the tracer's element regions (no exposure gain: the scan
#        is calibrated on the baked BC's own paper)
def photo_render(img, rf, sub=4):
    H, W = ref.shape[:2]
    acc = np.zeros((H, W, 3))
    yy_, xx_ = np.mgrid[0:H, 0:W].astype(np.float64)
    for a_ in range(sub):
        for b_ in range(sub):
            xm_, ym_ = fit.px_to_mm(xx_ + (b_ + 0.5) / sub, yy_ + (a_ + 0.5) / sub)
            u_, v_ = rf.mm_to_px(xm_, ym_)
            acc += samp(img, u_ - 0.5, v_ - 0.5)
    acc /= sub * sub
    return np.stack([T.gauss_blur(acc[..., k], T.SOURCE_PSF_SIGMA_PX) for k in range(3)], -1)
rphoto = photo_render(render, rfit)
rsrc2 = T.Source(path="scanphoto", sha256="", nbytes=0, rgb=rphoto, info={})
rk, rr, _ru = T.ink_layers(rsrc2, fit)
masks = PT.group_masks(m.L); regions = PT.group_regions(m.L, masks); eregs = PT.element_regions(m.L, masks, regions)
occluded = m.L.black > 0.85
de_r = T.delta_e2000(T.srgb_to_lab(ref), T.srgb_to_lab(rphoto))
render_elements = {}
for e in PT.ELEMENTS:
    layers = {}
    ws = []
    for layer, obs_, ours_ in (("black", m.L.black, rk), ("red", m.L.red_behind, rr)):
        if (e.name, layer) not in eregs:
            continue
        reg = eregs[(e.name, layer)]
        if layer == "red":
            reg = reg & ~occluded
        sc = PT.score_fields(ours_, obs_, reg, fit.ppmm)
        core_r = reg & (obs_ > 0.5); core_o = reg & (ours_ > 0.5)
        if core_r.any() and core_o.any():
            sc["de_median"] = round(float(T.delta_e2000(T.srgb_to_lab(np.median(ref[core_r], 0)),
                                                        T.srgb_to_lab(np.median(rphoto[core_o], 0)))), 3)
        layers[layer] = sc
        ws.append((sc.get("ink_px_obs", 0) + sc.get("ink_px_pred", 0), sc))
    tot = sum(w for w, _ in ws)
    render_elements[e.name] = {
        "iou": round(sum(w * v["iou"] for w, v in ws) / max(tot, 1), 4),
        "edge_mean_mm": round(float(np.mean([v["edge_mean_mm"] for _, v in ws if "edge_mean_mm" in v])), 4),
        "de_median": round(sum(w * v.get("de_median", 0) for w, v in ws) / max(tot, 1), 3),
        "layers": layers}
bare_r = bare
render_paper = {"de_median": round(float(T.delta_e2000(T.srgb_to_lab(np.median(ref[bare_r], 0)),
                                                          T.srgb_to_lab(np.median(rphoto[bare_r], 0)))), 3),
                "px_de_mean": round(float(de_r[bare_r].mean()), 3),
                "grain_L_std_ref": round(float(T.srgb_to_lab(ref[bare_r])[:, 0].std()), 3),
                "grain_L_std_scan": round(float(T.srgb_to_lab(rphoto[bare_r])[:, 0].std()), 3)}
render_card = {"de_mean": round(float(de_r[card].mean()), 3), "de_p90": round(float(np.percentile(de_r[card], 90)), 3)}

rec = {"tag": tag, "render_elements": render_elements, "render_paper": render_paper,
       "render_card_raw": render_card, "render_card_fit": rfit.record()["corners_px"], "render_ppmm": round(rfit.ppmm, 4),
       "render_exposure_gain_rgb": [round(float(v), 4) for v in gain],
       "render_de2000_card_mean": round(float(de_render[card].mean()), 3),
       "render_de2000_card_p90": round(float(np.percentile(de_render[card], 90)), 3),
       "fidelity_from_shipped_bc": FD.public(fid), "fidelity_gates": FD.gates(fid),
       "emblem_x8_iou": round(1.0 - xor, 4)}
json.dump(rec, open(os.path.join(OUT, tag + "_outputs.json"), "w"), indent=1)
print(json.dumps({k: v for k, v in rec.items() if k not in ("fidelity_from_shipped_bc", "fidelity_gates")}, indent=1))
print("render (scan) paper", render_paper, "card", render_card)
for k, v in render_elements.items():
    print("  render %-10s IoU %.4f edge %.4f mm dE %s" % (k, v["iou"], v["edge_mean_mm"], v["de_median"]))
for k, v in fid["elements"].items():
    print("  %-10s IoU %.4f edge %.4f mm  dE med %s mean %s" % (k, v["iou"], v["edge_mean_mm"] or -1, v.get("de_median"), v.get("de_mean")))
print("  paper", fid.get("paper"))
