"""t7 (user 2026-10-03: "also match the ring handle to the reference"): trace the photo's ring-handle hardware as the 2D
outline authority, corrected for the camera: every outline pixel is unprojected through the photo's fitted camera
(photo_cam.py) onto the barrel surface (r = body_r(x) + the plate's height), then laid out flat in the plate's own
frame (s = arc length round the drum, t = along the axis, design units) about the plate centre.

  plate   black and neutral (luminance < 55, R/G < 1.7) inside the hardware box, holes filled, the largest blob; its
          boundary in polar form about the centre; then made 4-fold and mirror symmetric (the median of the 8 copies, so
          the ring lying over the lower-left edge and the wood grain are voted out).
  washer  pale brass (luminance > 75, R/G < 1.35, not the plate): its boundary radius vs angle about its centre over
          the angles the ring and the boss do not cover; the petal count is the strongest Fourier harmonic 10-20.
  rivets, boss, ring  centres / sizes picked on the 3x crop (t7 ring_grid.png) and unprojected the same way.
Writes t7/ring_trace.json (sizes in DESIGN units; real = taiko_uv.DRUM_SCALE x) and Scripts/dojo/props/taiko/
ring_trace_t7.json (read by build_taiko), and t7/ring_trace_debug.png.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

T7 = Path(__file__).resolve().parent
ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
OUT_T7 = ROOT / "WorkFiles" / "dojo" / "build" / "props" / "taiko" / "t7"
SCRIPTS = Path(sys.argv[sys.argv.index("--scripts") + 1]) if "--scripts" in sys.argv else ROOT / "Scripts" / "dojo" / "props" / "taiko"
sys.path.insert(0, str(T7))
sys.path.insert(0, str(SCRIPTS))
import photo_cam as PC  # noqa: E402
import taiko_uv as UVL  # noqa: E402

img = Image.open(ROOT / "References" / "Dojo" / "taiko_tacks_ref_user.webp").convert("RGB")
A = np.asarray(img).astype(float)
U0, V0, U1, V1 = 385, 475, 665, 740
sub = A[V0:V1, U0:U1]
lum = sub.mean(2)
rg = sub[..., 0] / np.maximum(sub[..., 1], 1)
PLATE_H = 0.004          # design: the plate's top above the wood (unproject height)


def unproject(u, v, h=PLATE_H):
    hit = PC.hit_revolution(u, v, lambda x: UVL.body_r(np.abs(x)) + h, -0.3, 0.3)
    return hit                  # (x, r, th)


# ---- plate mask
black = (lum < 55) & (rg < 1.7)
black = ndi.binary_opening(black, iterations=1)
filled = ndi.binary_fill_holes(ndi.binary_closing(black, iterations=3))
lab, n = ndi.label(filled)
big = lab == (1 + np.argmax(ndi.sum(filled, lab, range(1, n + 1))))
edge = big & ~ndi.binary_erosion(big)
ev, eu = np.nonzero(edge)
eu, ev = eu + U0, ev + V0
cv_, cu_ = ndi.center_of_mass(big)
cu_, cv_ = cu_ + U0, cv_ + V0
# the tips: extreme boundary points in the four diagonal-free directions
tips_px = {"top": (eu[np.argmin(ev)], ev.min()), "bottom": (eu[np.argmax(ev)], ev.max()),
           "left": (eu.min(), ev[np.argmin(eu)]), "right": (eu.max(), ev[np.argmax(eu)])}
c_px = (0.5 * (tips_px["left"][0] + tips_px["right"][0]), 0.5 * (tips_px["top"][1] + tips_px["bottom"][1]))
xc, rc, thc = unproject(*c_px)


def to_plane(u, v, h=PLATE_H):
    """pixel -> plate-plane (s, t) design metres about the plate centre: s round the drum (+ = +th), t along +x"""
    x, r, th = unproject(u, v, h)
    return ((th - thc) * (UVL.body_r(xc) + h), x - xc)


pts = np.array([to_plane(u, v) for u, v in zip(eu, ev)])
ang = np.arctan2(pts[:, 1], pts[:, 0])
rad = np.hypot(pts[:, 0], pts[:, 1])
NB = 360
bins = np.linspace(-math.pi, math.pi, NB + 1)
r_phi = np.full(NB, np.nan)
for i in range(NB):
    m = (ang >= bins[i]) & (ang < bins[i + 1])
    if m.any():
        r_phi[i] = rad[m].max()            # the outer boundary
idx = np.arange(NB)
ok = ~np.isnan(r_phi)
r_phi = np.interp(idx, idx[ok], r_phi[ok], period=NB)
# mirror about the s axis (phi -> -phi): index i <-> NB - i (mod NB) with the bins centred at -pi + (i + 0.5) deg
mir = lambda a: a[(NB - 1 - idx) % NB]   # noqa: E731
copies = [np.roll(r_phi, -90 * k) for k in range(4)]
copies += [mir(c) for c in copies]
r_sym = np.median(np.array(copies), 0)
phi_c = 0.5 * (bins[:-1] + bins[1:])
outline = np.c_[r_sym * np.cos(phi_c), r_sym * np.sin(phi_c)]
half_w = float(np.max(np.abs(outline[:, 0])))

# ---- picked features (px, from t7 ring_grid.png at 3x: u = 385 + X / 3, v = 475 + Y / 3)
riv_px = {"top": (526.7, 508.3), "left": (423.3, 603.3), "right": (628.3, 600.0), "bottom": (531.7, 701.7)}
riv_d_px = 20.0
washer_c_px = (531.7, 608.3)
boss_c_px, boss_d_px = (530.7, 620.0), 42.0
ring_c_px, ring_od_px, ring_tube_px = (485.0, 626.7), 98.0, 8.5


def size_at(u, v, d_px, h=PLATE_H):
    a = to_plane(u - d_px / 2, v, h)
    b = to_plane(u + d_px / 2, v, h)
    return abs(b[0] - a[0])


riv = {k: to_plane(*p, h=PLATE_H + 0.004) for k, p in riv_px.items()}
riv_r = float(np.median([math.hypot(*q) for q in riv.values()]))
riv_d = size_at(*riv_px["left"], riv_d_px, PLATE_H + 0.004)
# washer: pale brass boundary about its centre
pale = (lum > 75) & (rg < 1.35) & (sub[..., 0] > sub[..., 2] + 8)
pale = ndi.binary_opening(pale, iterations=1)
lab2, n2 = ndi.label(pale)
cand = [(ndi.sum(pale, lab2, i), i) for i in range(1, n2 + 1)]
wm = lab2 == max(cand)[1]
wv, wu = np.nonzero(wm & ~ndi.binary_erosion(wm))
wu, wv = wu + U0, wv + V0
wc = to_plane(*washer_c_px, h=PLATE_H + 0.002)
wp = np.array([to_plane(u, v, PLATE_H + 0.002) for u, v in zip(wu, wv)]) - np.array(wc)
wa = np.arctan2(wp[:, 1], wp[:, 0])
wr = np.hypot(wp[:, 0], wp[:, 1])
NW = 180
wr_phi = np.full(NW, np.nan)
wb = np.linspace(-math.pi, math.pi, NW + 1)
for i in range(NW):
    m = (wa >= wb[i]) & (wa < wb[i + 1])
    if m.any():
        wr_phi[i] = wr[m].max()
# the washer's free arc: right half (the ring covers the left, the boss the middle)
wphi = 0.5 * (wb[:-1] + wb[1:])
free = (~np.isnan(wr_phi)) & (np.abs(wphi) < math.radians(100))
r_out = float(np.percentile(wr_phi[free], 92))
r_in = float(np.percentile(wr_phi[free], 15))
spec = {}
fr = np.interp(np.arange(NW), np.nonzero(~np.isnan(wr_phi))[0], wr_phi[~np.isnan(wr_phi)], period=NW)
for k in range(8, 21):
    w_ = np.where(free, 1.0, 0.0)
    c = np.sum(w_ * (fr - fr[free].mean()) * np.exp(-1j * k * wphi))
    spec[k] = float(abs(c))
petals = max(spec, key=spec.get)
boss = to_plane(*boss_c_px, h=PLATE_H + 0.015)
boss_d = size_at(*boss_c_px, boss_d_px, PLATE_H + 0.015)
ring_c = to_plane(*ring_c_px, h=PLATE_H + 0.010)
ring_od = size_at(*ring_c_px, ring_od_px, PLATE_H + 0.010)
ring_t = size_at(*ring_c_px, ring_tube_px, PLATE_H + 0.010)
# body width at the plate's height (silhouette) for the proportion
body_w_px = None
row = int(round(c_px[1]))
fg = ndi.binary_fill_holes(A.min(2) < 240)
xs = np.where(fg[row])[0]
body_w_px = float(xs.max() - xs.min())
plate_w_px = float(tips_px["right"][0] - tips_px["left"][0])
res = {"camera": "photo_cam.py (t7, +Y handle side)", "plate_centre_px": [round(c_px[0], 1), round(c_px[1], 1)],
       "plate_centre_design_x_th_deg": [round(xc, 4), round(math.degrees(thc), 2)],
       "tips_px": {k: [int(a_), int(b_)] for k, (a_, b_) in tips_px.items()},
       "plate_half_width_design_m": round(half_w, 4),
       "plate_outline_polar_design_m": [round(float(q), 5) for q in r_sym],
       "plate_outline_phi_deg": [round(math.degrees(q), 2) for q in phi_c],
       "rivet_centre_radius_design_m": round(riv_r, 4), "rivet_diameter_design_m": round(riv_d, 4),
       "rivets_plane_design_m": {k: [round(q[0], 4), round(q[1], 4)] for k, q in riv.items()},
       "washer_centre_offset_design_m": [round(wc[0], 4), round(wc[1], 4)],
       "washer_outer_radius_design_m": round(r_out, 4), "washer_petal_root_radius_design_m": round(r_in, 4),
       "washer_petals": int(petals), "washer_petal_spectrum": {k: round(v, 4) for k, v in spec.items()},
       "boss_centre_offset_design_m": [round(boss[0], 4), round(boss[1], 4)], "boss_diameter_design_m": round(boss_d, 4),
       "ring_centre_offset_design_m": [round(ring_c[0], 4), round(ring_c[1], 4)],
       "ring_outer_diameter_design_m": round(ring_od, 4), "ring_tube_diameter_design_m": round(ring_t, 4),
       "proportions_px": {"plate_width_px": plate_w_px, "body_width_px_at_plate_row": body_w_px,
                          "plate_over_body_width": round(plate_w_px / body_w_px, 4),
                          "ring_od_over_plate_width": round(ring_od_px / plate_w_px, 4),
                          "washer_d_over_plate_width": round(2 * r_out / (2 * half_w), 4)}}
OUT_T7.mkdir(parents=True, exist_ok=True)
(OUT_T7 / "ring_trace.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
(SCRIPTS / "ring_trace_t7.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
# debug: the photo crop at 3x with the boundary, the symmetric outline re-projected, the washer boundary
z = 3
dbg = img.crop((U0, V0, U1, V1)).resize(((U1 - U0) * z, (V1 - V0) * z), Image.LANCZOS)
d = ImageDraw.Draw(dbg)
for u, v in zip(eu, ev):
    d.point(((u - U0) * z, (v - V0) * z), fill=(0, 255, 0))
for u, v in zip(wu, wv):
    d.point(((u - U0) * z, (v - V0) * z), fill=(255, 255, 0))
R_ = UVL.body_r(xc) + PLATE_H
P3 = np.array([[xc + t, R_ * math.cos(thc + s / R_), R_ * math.sin(thc + s / R_)] for s, t in outline])
q = PC.project_design(P3)
d.line([((a_ - U0) * z, (b_ - V0) * z) for a_, b_ in np.r_[q, q[:1]]], fill=(255, 0, 0), width=2)
dbg.save(OUT_T7 / "ring_trace_debug.png")
print(json.dumps({k: v for k, v in res.items() if not k.startswith("plate_outline")}, indent=1))
