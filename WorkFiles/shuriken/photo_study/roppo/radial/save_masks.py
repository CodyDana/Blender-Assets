"""Write mask PNGs for each threshold tag (white = plate, black = background/hole)."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import imgio
outdir = sys.argv[sys.argv.index("--") + 1]
for t in ("T35", "T50", "T65", "T80"):
    m = np.load(os.path.join(outdir, f"solid_{t}.npy")).astype(np.float32)
    imgio.save_rgb(os.path.join(outdir, f"mask_{t}.png"), m)
    if t == "T65":
        imgio.save_rgb(os.path.join(outdir, "mask.png"), m)
print("masks written")
