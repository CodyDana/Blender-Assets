import sys, numpy as np, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/metrology")
from fb_lib import *
ref = load_srgb(); H, W = ref.shape[:2]
lin = srgb_to_lin(ref)
L = lum(ref)
g = ref[..., 1] - 0.5*(ref[..., 0] + ref[..., 2])
chroma = ref.max(2) - ref.min(2)
yy, xx = np.mgrid[0:H, 0:W]
def stats(mask, name):
    px = ref[mask]; pl = lin[mask]
    lv = px @ LW
    o = dict(n=int(mask.sum()))
    for q in (10, 50, 90):
        # pick percentile by luminance, report mean colour of pixels near that luminance percentile
        t = np.percentile(lv, q); sel = np.abs(lv - t) <= np.percentile(np.abs(lv - t), 5) + 1e-6
        c = px[sel].mean(0)
        o[f'p{q}_srgb'] = [round(float(v), 4) for v in c]
        o[f'p{q}_srgb8'] = [int(round(v*255)) for v in c]
        o[f'p{q}_lin'] = [round(float(v), 4) for v in srgb_to_lin(c)]
    o['mean_lin'] = [round(float(v), 4) for v in pl.mean(0)]
    print(name, json.dumps(o))
    return o
# body regions (between sleeve top and cap) per view
BODY = dict(v1=(69, 247), v2=(380, 555), v3=(658, 833), v4=(1013, 1128))   # v4: left of lever
holes_c = dict(v2=469, v3=760)
out = {}
bodym = np.zeros((H, W), bool)
for v, (a, b) in BODY.items():
    bodym |= (xx >= a+4) & (xx <= b-4) & (yy >= 203) & (yy <= 626)
paint = bodym & (g > 0.02)
out['paint'] = stats(paint, 'paint')
# holes: ellipses around v2/v3 centre holes
hol = np.zeros((H, W), bool)
for v, cx in holes_c.items():
    for cy in (326, 442, 562):
        hol |= ((xx - cx)/26.0)**2 + ((yy - cy)/31.0)**2 <= 1
out['brass_tube_in_holes'] = stats(hol, 'brass')
brass_bright = hol & (L > np.percentile(L[hol], 60))
out['brass_tube_lit'] = stats(brass_bright, 'brass_lit')
# exclude holes broadly: non-paint in body not in dilated hole zones (use paint-mask holes: big connected non-paint areas approximated by low-greenness + blur)
nonpaint = bodym & (g <= 0.012)
holezone = gauss_blur((g <= 0.012).astype(np.float32), 4) > 0.75   # large non-paint blobs = holes
chips = nonpaint & ~holezone
bright_chip = chips & (L > 0.30) & (chroma < 0.12)
dark_grime = bodym & ~holezone & (L < 0.12)
out['bare_steel_chips_on_body'] = stats(bright_chip, 'bare_chip')
out['grime_dark_on_body'] = stats(dark_grime, 'grime')
cap = np.zeros((H, W), bool)
for (a, b) in ((66, 248), (378, 555), (655, 838), (1010, 1196)):
    cap |= (xx >= a) & (xx <= b) & (yy >= 648) & (yy <= 696)
out['dark_steel_basecap'] = stats(cap, 'cap')
cap_bright = cap & (L > np.percentile(L[cap], 97))
out['worn_edge_steel_basecap_top3pct'] = stats(cap_bright, 'cap_bright')
hous = (xx >= 450) & (xx <= 498) & (yy >= 75) & (yy <= 140)
hous |= (xx >= 752) & (xx <= 815) & (yy >= 70) & (yy <= 140)
out['dark_steel_fuze_housing'] = stats(hous, 'housing')
lev = (xx >= 1142) & (xx <= 1178) & (yy >= 300) & (yy <= 540)
out['lever_steel_v4_face'] = stats(lev, 'lever')
coll = (xx >= 410) & (xx <= 530) & (yy >= 160) & (yy <= 178)
out['collar_steel'] = stats(coll, 'collar')
bg = ((xx < 40) | ((xx > 600) & (xx < 625)) | ((xx > 945) & (xx < 965))) & (yy > 40) & (yy < 650)
out['background_top_row'] = stats(bg, 'bg')
# wear coverage: fraction of body (non-hole) area that is not paint
nh = bodym & ~holezone
out['coverage'] = dict(paint_frac_of_nonhole_body=round(float((paint & ~holezone).sum() / nh.sum()), 3),
                       chips_frac=round(float(chips.sum()/nh.sum()), 3), bright_chip_frac=round(float(bright_chip.sum()/nh.sum()), 3),
                       dark_grime_frac=round(float(dark_grime.sum()/nh.sum()), 3))
# wear density by height band (fraction non-paint, non-hole)
bands = {}
for y0 in range(200, 630, 10):
    m = nh & (yy >= y0) & (yy < y0+10)
    if m.sum() > 50: bands[y0] = round(float((chips & m).sum()/m.sum()), 3)
out['chip_frac_by_y10'] = bands
# wear vs distance to hole edges: dilate holezone rings
d1 = gauss_blur(holezone.astype(np.float32), 3) > 0.02
d2 = gauss_blur(holezone.astype(np.float32), 8) > 0.02
ring1 = nh & d1; ring2 = nh & d2 & ~d1; far = nh & ~d2
out['chip_frac_near_holes'] = dict(within_3px=round(float((chips & ring1).sum()/max(1, ring1.sum())), 3),
                                   px3_to_8=round(float((chips & ring2).sum()/max(1, ring2.sum())), 3),
                                   beyond_8px=round(float((chips & far).sum()/max(1, far.sum())), 3))
print('coverage', out['coverage'], out['chip_frac_near_holes'])
print('bands', bands)
json.dump(out, open(DBG + "/fb_colour.json", "w"), indent=1)
vis = ref*0.4; vis[paint] = [0.1, 0.6, 0.1]; vis[bright_chip] = [1, 1, 0]; vis[dark_grime] = [1, 0, 1]; vis[hol] = [1, 0.5, 0]; vis[cap] = vis[cap]*0.5+[0, 0, 0.5]
save_png(DBG + "/colour_regions.png", vis[:745])
