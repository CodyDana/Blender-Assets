"""Read-only texture check of Exports/BlackCloak/Textures (loads PNGs, never saves)."""
import bpy, json, sys, os, hashlib
import numpy as np
out = sys.argv[sys.argv.index("--") + 1]
D = "C:/Users/Cody/Desktop/Blender_Projects/Exports/BlackCloak/Textures/"
res = {}
px = {}
for f in sorted(os.listdir(D)):
    im = bpy.data.images.load(D + f, check_existing=False)
    im.colorspace_settings.name = "Non-Color"  # read stored values
    a = np.array(im.pixels[:], dtype=np.float32).reshape(im.size[1], im.size[0], im.channels)
    px[f] = a
    res[f] = {"size": list(im.size), "channels": im.channels, "depth": im.depth, "is_float": im.is_float,
              "sha256": hashlib.sha256(open(D + f, "rb").read()).hexdigest(),
              "mean": a[..., :3].reshape(-1, 3).mean(0).round(4).tolist(),
              "min": a[..., :3].reshape(-1, 3).min(0).round(4).tolist(),
              "max": a[..., :3].reshape(-1, 3).max(0).round(4).tolist(),
              "p1_p99_ch0": np.percentile(a[..., 0], [1, 99]).round(4).tolist()}
gl = px.get("T_BlackCloak_Normal_OpenGL.png"); dx = px.get("T_BlackCloak_Normal_DirectX.png")
if gl is not None and dx is not None:
    res["dx_vs_gl"] = {"R_max_abs_diff": float(np.abs(gl[..., 0] - dx[..., 0]).max()),
                       "B_max_abs_diff": float(np.abs(gl[..., 2] - dx[..., 2]).max()),
                       "G_dx_plus_G_gl_minus_1_max_abs": float(np.abs(gl[..., 1] + dx[..., 1] - 1).max()),
                       "G_equal_max_abs": float(np.abs(gl[..., 1] - dx[..., 1]).max())}
    # decoded normal length sanity
    n = dx[..., :3] * 2 - 1
    L = np.linalg.norm(n, axis=-1)
    res["dx_normal_length_p1_p50_p99"] = np.percentile(L, [1, 50, 99]).round(4).tolist()
# tile seam check: left vs right column / top vs bottom row difference vs interior neighbour difference
for f, a in px.items():
    edge = float(np.abs(a[:, 0, :3] - a[:, -1, :3]).mean()); inner = float(np.abs(a[:, 1, :3] - a[:, 0, :3]).mean())
    edge2 = float(np.abs(a[0, :, :3] - a[-1, :, :3]).mean()); inner2 = float(np.abs(a[1, :, :3] - a[0, :, :3]).mean())
    res[f]["tiling_seam_ratio_u_v"] = [round(edge / max(inner, 1e-6), 2), round(edge2 / max(inner2, 1e-6), 2)]
bc = px.get("T_BlackCloak_BaseColor.png")
if bc is not None:
    # stored sRGB values; how much range a tint would have to work with
    lum = 0.2126 * bc[..., 0] + 0.7152 * bc[..., 1] + 0.0722 * bc[..., 2]
    res["basecolor_luma_srgb_p1_p50_p99"] = np.percentile(lum, [1, 50, 99]).round(4).tolist()
with open(out, "w", encoding="utf-8") as fh:
    json.dump(res, fh, indent=1)
print("TEX_DONE")
