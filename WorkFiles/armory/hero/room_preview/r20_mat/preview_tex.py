"""r20_mat: quick look at a mat texture set before a build: the tile, and the tile repeated over the mat (2.32 x 0.76 m
field) shaded by a low golden light and shrunk to C1's scale (~254 px/m across, ~173 px/m along), beside the crop."""
import sys
from pathlib import Path
import numpy as np
from PIL import Image
HERE = Path(__file__).resolve().parent
name = sys.argv[1]
T = HERE / "Textures"
bc = np.asarray(Image.open(T / f"T_AK_{name}_BC.png").convert("RGB")).astype(float) / 255
nm = np.asarray(Image.open(T / f"T_AK_{name}_N.png").convert("RGB")).astype(float) / 255
ao = np.asarray(Image.open(T / f"T_AK_{name}_ORM.png").convert("RGB")).astype(float)[..., 0] / 255
nx, ny, nz = nm[..., 0] * 2 - 1, -(nm[..., 1] * 2 - 1), nm[..., 2] * 2 - 1
L = np.array([-0.5, 0.35, 0.55]); L /= np.linalg.norm(L)       # low light from the left / behind
sh = np.clip(nx * L[0] + ny * L[1] + nz * L[2], 0, 1)
lit = np.clip(bc * (0.25 + 1.1 * sh[..., None]) * ao[..., None], 0, 1)
n = bc.shape[0]
# image columns = U = world Y (toward the bar), rows = V = world X: transpose so X runs across the picture
lit = lit.transpose(1, 0, 2)
reps_x, reps_y = 3, 1
big = np.tile(lit, (reps_y, reps_x, 1))[: int(0.76 * n), : int(2.32 * n)]
big = big[::-1]                                                    # far (bar) at the top
im = Image.fromarray((big * 255).astype(np.uint8))
small = im.resize((int(2.32 * 254), int(0.76 * 173)), Image.LANCZOS)
view = small.resize((small.width * 2, small.height * 2), Image.LANCZOS)
crop = Image.open(Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory\reference\armory3_reference2.png")).convert("RGB")
crop = crop.crop((440, 950, 1020, 1070)).resize((1160, 240), Image.LANCZOS)
tile = Image.fromarray((lit[:400, :400] * 255).astype(np.uint8))
W = max(view.width, crop.width) + 420
out = Image.new("RGB", (W, view.height + crop.height + 30), (20, 20, 20))
out.paste(crop, (0, 0)); out.paste(view, (0, crop.height + 20)); out.paste(tile, (W - 410, 0))
out.save(HERE / "compare" / f"tex_{name}.png")
print("mean bc srgb", bc.reshape(-1, 3).mean(0).round(3))
