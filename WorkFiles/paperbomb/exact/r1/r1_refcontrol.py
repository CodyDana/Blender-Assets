"""CONTROL: run every REFERENCE_SPEC gate on the REFERENCE ITSELF (resampled onto the art grid,
ink layers from the tracer's unmixing) and on our built front, side by side.  A gate the
reference itself fails is miscalibrated for the reference of record."""
import os, sys, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props"); sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/exact")
import numpy as np
from props_lib import trace as T
from props_lib import paperbomb_art as A
from props_lib import paperbomb_tracedart as TA
from props_lib import art_metrics as AM
ppmm, pad = 12.4222, 1.2880166154143389
m = TA.reference_model(); fit = m.L.fit
cfg = A.ArtConfig(ppmm=ppmm, pad_mm=pad, supersample=1)
W, H = A.raster_size(cfg)
card, outline = A._card_mask(cfg, A.LAYOUT, W, H)
(spx, spy), _ = TA.texture_to_source(fit, ppmm, pad, H, W)
MODE = sys.argv[1] if len(sys.argv) > 1 else "reference"
if MODE == "reference":
    rgb_src, kb, rb = m.L.src.rgb, m.L.black, m.L.red_behind
else:
    # OUR shipped BC map, photographed at the reference's grid, unmixed by the same instrument
    import xt_io
    from props_lib import paperbomb_fidelity as FD
    sys.path.insert(0, ".")
    bc, _ = xt_io.read(r"C:/Users/Cody/Desktop/Blender_Projects/Exports/PaperBomb/Textures/T_PaperBomb_BC.png")
    bc = bc[:2048, :902, :3]
    cm, _o = A._card_mask(cfg, A.LAYOUT, W, H)
    photo = FD.photograph(T.srgb_to_linear(bc), cm[:2048, :902], ppmm, pad, m.L.src, fit)
    ps = T.Source(path="photo", sha256="", nbytes=0, rgb=photo, info={})
    kb, rb, _u = T.ink_layers(ps, fit)
    rgb_src = photo
chans = [T.srgb_to_linear(rgb_src[..., k]) for k in range(3)] + [kb, rb]
coef = np.stack([TA._prefilter(c) for c in chans], 0)
f = np.concatenate([TA.sample_fields(coef, spx[r:r+256], spy[r:r+256]) for r in range(0, H, 256)], 1)
f = np.clip(f, 0, 1).astype(np.float32)
base = np.moveaxis(f[:3], 0, -1)
red = A.Ink(H, W); black = A.Ink(H, W); red.a = f[4]; black.a = f[3]
art = A.TagArt(side="front", ppmm=ppmm, width=W, height=H, base_colour=base, paper_rgb=base,
               roughness=np.zeros((H, W), np.float32), relief=np.zeros((H, W), np.float32),
               card_mask=card, fringe=np.zeros((H, W)), scorch=np.zeros((H, W)),
               ink_mask=np.maximum(f[3], f[4]), ink_black=black, ink_red=red, outline_mm=outline)
art.report = {"text": TA.text_report(m)}
meas = AM.measure_front(art, cfg, A.LAYOUT)
gref = AM.spec_gates(meas, A.CORNER_CLIP_MM)
rep = json.load(open("r1_b1_report.json", encoding="utf-8"))
gour = rep["art"]["reference_spec_gates"]; mour = rep["art"]["reference_spec"]
out = {}
for k in sorted(gref):
    out[k] = {"reference": gref[k], "ours": gour.get(k)}
    if not (gref[k] and gour.get(k)):
        print("%-45s reference %-5s ours %s" % (k, gref[k], gour.get(k)))
json.dump({"gates": out, "measured_reference": meas}, open("r1/r1_refcontrol_%s.json" % MODE, "w"), indent=1, default=str)
print(MODE, "passes", sum(gref.values()), "/", len(gref))
