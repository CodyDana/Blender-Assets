import sys
import numpy as np
from PIL import Image
for p in sys.argv[1:]:
    L = np.asarray(Image.open(p).convert("RGB")).astype(float) @ [0.299, 0.587, 0.114]
    def m(x0, x1, y0, y1): return L[y0:y1, x0:x1].mean()
    print(p.split("/")[-3], f"Lbind(y990-1010,x416-428) {m(416,428,990,1010):.0f} Rbind(x1019-1029) {m(1019,1029,990,1010):.0f} "
          f"band(x650-800,y1072-1077) {m(650,800,1072,1077):.0f} topbind(x650-800,y941-946) {m(650,800,941,946):.0f} "
          f"field(x700-900,y960-1050) {m(700,900,960,1050):.0f} Lrail(x386-406) {m(386,406,990,1010):.0f} "
          f"Rrail(x1041-1063) {m(1041,1063,990,1010):.0f} gapL(x411-414) {m(411,414,990,1010):.0f}")
