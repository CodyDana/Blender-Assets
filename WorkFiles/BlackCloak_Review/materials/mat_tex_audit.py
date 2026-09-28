"""Read-only texture audit of Exports/BlackCloak/Textures (BlackCloak review, materials area).
Run: blender -b --factory-startup --python mat_tex_audit.py
Writes only WorkFiles/BlackCloak_Review/materials/mat_tex_audit.json + a few PNG crops.
"""
import bpy, json, hashlib
import numpy as np
from pathlib import Path

ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
TEX = ROOT / "Exports/BlackCloak/Textures"
OUT = ROOT / "WorkFiles/BlackCloak_Review/materials"
R = {}


def load(name):
    p = TEX / (name + ".png")
    img = bpy.data.images.load(str(p), check_existing=False)
    img.colorspace_settings.name = "Non-Color"  # stored values, no transform
    w, h = img.size
    a = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    a = a.reshape(h, w, 4)  # row 0 = bottom of image (Blender convention) => +V up
    bpy.data.images.remove(img)
    return np.rint(a[:, :, :3] * 255).astype(np.int32), hashlib.sha256(p.read_bytes()).hexdigest()


def s2l(x):
    x = x / 255.0
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def stats(x):
    return {"min": float(x.min()), "p01": float(np.percentile(x, 1)), "mean": float(x.mean()),
            "p99": float(np.percentile(x, 99)), "max": float(x.max()), "std": float(x.std()),
            "unique_levels": int(len(np.unique(x)))}


bc, h_bc = load("T_BlackCloak_BaseColor")
gl, h_gl = load("T_BlackCloak_Normal_OpenGL")
dx, h_dx = load("T_BlackCloak_Normal_DirectX")
ro, h_ro = load("T_BlackCloak_Roughness")
R["sha256"] = {"BaseColor": h_bc, "Normal_OpenGL": h_gl, "Normal_DirectX": h_dx, "Roughness": h_ro}

# ---- base colour
lin = s2l(bc)
R["basecolor"] = {
    "stored_R": stats(bc[:, :, 0]), "stored_G": stats(bc[:, :, 1]), "stored_B": stats(bc[:, :, 2]),
    "linear_R": stats(lin[:, :, 0]),
    "linear_mean_rgb": [float(lin[:, :, i].mean()) for i in range(3)],
    "greyscale": bool((np.abs(bc[:, :, 0] - bc[:, :, 1]) <= 1).all() and (np.abs(bc[:, :, 0] - bc[:, :, 2]) <= 1).all()),
    "max_linear_over_mean": float(lin[:, :, 0].max() / lin[:, :, 0].mean()),
    "min_linear_over_mean": float(lin[:, :, 0].min() / lin[:, :, 0].mean()),
}
# ---- roughness
R["roughness"] = {"stored": stats(ro[:, :, 0]), "as_value": stats(ro[:, :, 0] / 255.0),
                  "channels_equal": bool((ro[:, :, 0] == ro[:, :, 1]).all() and (ro[:, :, 0] == ro[:, :, 2]).all())}

# ---- normals
def decode(n):
    v = n.astype(np.float64) / 255.0 * 2 - 1
    return v
g = decode(gl); d = decode(dx)
R["normal_green_relation"] = {
    "gl_G_plus_dx_G_stored": stats(gl[:, :, 1] + dx[:, :, 1]),
    "R_equal": bool((gl[:, :, 0] == dx[:, :, 0]).all()),
    "B_equal": bool((gl[:, :, 2] == dx[:, :, 2]).all()),
    "corr_G_gl_vs_dx": float(np.corrcoef(gl[:, :, 1].ravel(), dx[:, :, 1].ravel())[0, 1]),
}
ln = np.linalg.norm(g, axis=2)
R["normal_opengl"] = {"R": stats(gl[:, :, 0]), "G": stats(gl[:, :, 1]), "B": stats(gl[:, :, 2]),
                      "length": stats(ln), "z_decoded": stats(g[:, :, 2]),
                      "max_tilt_deg": float(np.degrees(np.arccos(np.clip(g[:, :, 2] / ln, -1, 1))).max()),
                      "p99_tilt_deg": float(np.percentile(np.degrees(np.arccos(np.clip(g[:, :, 2] / ln, -1, 1))), 99)),
                      "mean_tilt_deg": float(np.degrees(np.arccos(np.clip(g[:, :, 2] / ln, -1, 1))).mean()),
                      "mean_xy": [float(g[:, :, 0].mean()), float(g[:, :, 1].mean())]}

# ---- sign test: divergence of the (x,y) normal field ~ -Laplacian(h): positive on raised threads.
# Raised thread = where the base colour's weave term is high (base shade adds +0.008*weave; weave is also the height).
# Use array axes: axis1 = +U (right), axis0 = +V (up, Blender row 0 = bottom).
def div(nx, ny):
    return (np.roll(nx, -1, 1) - np.roll(nx, 1, 1)) / 2 + (np.roll(ny, -1, 0) - np.roll(ny, 1, 0)) / 2
bc_hp = lin[:, :, 0] - (np.roll(lin[:, :, 0], 8, 0) + np.roll(lin[:, :, 0], -8, 0) + np.roll(lin[:, :, 0], 8, 1) + np.roll(lin[:, :, 0], -8, 1)) / 4
res = {}
for label, n, green_up in [("OpenGL_map_read_as_OpenGL(+Y up)", g, 1), ("OpenGL_map_read_as_DirectX", g, -1),
                           ("DirectX_map_read_as_DirectX(+Y down)", d, -1), ("DirectX_map_read_as_OpenGL", d, 1)]:
    dv = div(n[:, :, 0], green_up * n[:, :, 1])
    res[label] = float(np.corrcoef(dv.ravel(), bc_hp.ravel())[0, 1])
# Also directly: reconstruct the generator's weave (height) and correlate with divergence
n_ = 2048
yy, xx = np.mgrid[0:n_, 0:n_].astype(np.float64)
u, v = xx / n_, yy / n_
tau = 2 * np.pi
px = tau * (128 * u + 0.25 * np.sin(tau * 37 * v)); py = tau * (128 * v + 0.22 * np.sin(tau * 43 * u))
warp = (0.5 + 0.5 * np.cos(px)) ** 1.35; weft = (0.5 + 0.5 * np.cos(py)) ** 1.35
cr = np.cos(px * 0.5) * np.cos(py * 0.5)
weave = warp * (0.53 + 0.12 * cr) + weft * (0.47 - 0.12 * cr)
lap = (np.roll(weave, 1, 0) + np.roll(weave, -1, 0) + np.roll(weave, 1, 1) + np.roll(weave, -1, 1) - 4 * weave)
for label, n, green_up in [("GL_as_GL", g, 1), ("GL_as_DX", g, -1), ("DX_as_DX", d, -1), ("DX_as_GL", d, 1)]:
    dv = div(n[:, :, 0], green_up * n[:, :, 1])
    res["vs_generator_height_" + label] = float(np.corrcoef(dv.ravel(), (-lap).ravel())[0, 1])
res["weave_height_vs_basecolor_highpass_corr"] = float(np.corrcoef((weave - np.roll(weave, 8, 0)).ravel(), bc_hp.ravel())[0, 1])
res["note"] = "positive = raised thread reads raised in that convention. Divergence of the XY normal field equals -Laplacian(height)."
R["normal_sign_test"] = res

# ---- tiling seams: compare wrap-around neighbour difference to interior neighbour difference
def seam(a):
    a = a.astype(np.float64)
    inner_x = np.abs(np.diff(a, axis=1)).mean(); inner_y = np.abs(np.diff(a, axis=0)).mean()
    edge_x = np.abs(a[:, 0] - a[:, -1]).mean(); edge_y = np.abs(a[0, :] - a[-1, :]).mean()
    return {"interior_dU": inner_x, "wrap_dU": edge_x, "interior_dV": inner_y, "wrap_dV": edge_y}
R["tiling_seams"] = {"basecolor_R": seam(bc[:, :, 0]), "normal_gl_R": seam(gl[:, :, 0]), "normal_gl_G": seam(gl[:, :, 1]),
                     "roughness": seam(ro[:, :, 0])}

# ---- spectral content: how much base-colour variance lives at which spatial scale (tile = 128 mm, 2048 px)
F = np.abs(np.fft.fft2(lin[:, :, 0] - lin[:, :, 0].mean())) ** 2
fy = np.fft.fftfreq(n_) * n_; fx = np.fft.fftfreq(n_) * n_
FR = np.sqrt(fx[None, :] ** 2 + fy[:, None] ** 2)  # cycles per tile
tot = F.sum()
bands = {}
for lo, hi, lab in [(0, 4, ">32mm"), (4, 16, "8-32mm"), (16, 64, "2-8mm"), (64, 256, "0.5-2mm"), (256, 4096, "<0.5mm")]:
    bands[lab] = float(F[(FR >= lo) & (FR < hi)].sum() / tot)
R["basecolor_variance_by_wavelength"] = bands

# ---- mip simulation: box-filter mips; contrast (std/mean, linear) per mip
mips = []
m = lin[:, :, 0].copy(); level = 0
while m.shape[0] >= 8:
    mips.append({"mip": level, "size": m.shape[0], "linear_std_over_mean": float(m.std() / m.mean()),
                 "range_over_mean": [float(m.min() / m.mean()), float(m.max() / m.mean())]})
    m = m.reshape(m.shape[0] // 2, 2, m.shape[1] // 2, 2).mean(axis=(1, 3)); level += 1
R["basecolor_mips"] = mips
nm = g.copy(); level = 0; nmips = []
while nm.shape[0] >= 8:
    L = np.linalg.norm(nm, axis=2)
    nmips.append({"mip": level, "mean_tilt_deg": float(np.degrees(np.arccos(np.clip(nm[:, :, 2] / L, -1, 1))).mean()),
                  "mean_len": float(L.mean())})
    nm = nm.reshape(nm.shape[0] // 2, 2, nm.shape[1] // 2, 2, 3).mean(axis=(1, 3)); level += 1
R["normal_mips"] = nmips

# ---- simulated recolour with the cloak's own graph: base = CloakColor * lerp(1, sat(Rlin/0.013702083), FD)
mask = np.clip(lin[:, :, 0] / 0.013702083, 0, 1)
rec = {}
for hexc in ["FFFFFF", "FF0000", "0000FF", "000000", "F2E8D5", "808080"]:
    c = np.array([int(hexc[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float64)
    cl = s2l(c)
    out = np.clip(cl[None, None, :] * mask[:, :, None], 0, 1)
    enc = np.where(out <= 0.0031308, out * 12.92, 1.055 * out ** (1 / 2.4) - 0.055)
    lev = np.rint(enc * 255).astype(int)
    ch = int(np.argmax(cl)) if cl.max() > 0 else 0
    L = lev[:, :, ch]
    top = L.max()
    rec[hexc] = {"linear_colour": cl.tolist(), "out_linear_mean": [float(out[:, :, i].mean()) for i in range(3)],
                 "stored_levels_main_channel": int(len(np.unique(L))), "stored_min_max": [int(L.min()), int(L.max())],
                 "plateau_at_max_pct": float((L == top).mean() * 100),
                 "log_contrast_p99_p1": float(np.log(np.percentile(out[:, :, ch] + 1e-6, 99) / np.percentile(out[:, :, ch] + 1e-6, 1)))}
R["cloak_graph_recolour_twin"] = rec
R["mask_stats"] = stats(mask)
R["mask_fraction_at_1"] = float((mask >= 0.9999).mean())
# preset black
blk = np.array([0.013702083, 0.01355, 0.0134])
R["preset_black_mean_linear"] = float((blk[0] * mask).mean())

(OUT / "mat_tex_audit.json").write_text(json.dumps(R, indent=2), encoding="utf-8")

# crops for eyeballing: 256px crop, contrast stretched
def save_png(arr, name):
    h, w = arr.shape[:2]
    im = bpy.data.images.new(name, w, h, alpha=False)
    px = np.ones((h, w, 4), np.float32)
    px[:, :, :3] = arr if arr.ndim == 3 else arr[:, :, None]
    im.pixels.foreach_set(px.ravel())
    im.filepath_raw = str(OUT / (name + ".png")); im.file_format = "PNG"; im.save()
c = bc[:256, :256, 0].astype(np.float32)
save_png(np.repeat(((c - c.min()) / (c.max() - c.min()))[:, :, None], 3, 2), "mat_crop_basecolor_stretched_256")
save_png(gl[:256, :256].astype(np.float32) / 255, "mat_crop_normal_gl_256")
save_png(np.repeat((bc[:, :, 0:1].astype(np.float32) / 255), 3, 2)[::4, ::4], "mat_basecolor_full_as_stored_512")
print("MAT_TEX_AUDIT_DONE")
