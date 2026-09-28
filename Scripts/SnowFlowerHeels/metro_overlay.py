"""Draw metro_traces.T over the reference.  usage: python metro_overlay.py x0 y0 x1 y1 scale out.png [view]"""
import sys, numpy as np
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/SnowFlowerHeels")
import metro_crop as mc, metro_traces as mt

COL = {"silver": (0, 1, 1), "pearl": (1, 0.2, 1), "toecap_gloss": (1, 1, 0), "strap_leather": (0.2, 1, 0.2)}


def overlay_json(view=None):
    pls, pts = [], []
    for k, t in mt.T.items():
        if view and t["view"] != view: continue
        col = COL.get(t.get("material", ""), (1, 0.3, 0.1))
        if t["kind"] in ("outline", "polyline", "centerline"):
            pls.append({"pts": t["pts"], "color": col, "closed": t["kind"] == "outline"})
        elif t["kind"] in ("point", "points"):
            r = t.get("d_px", 4) / 2
            for p in t["pts"]:
                if r > 3:
                    ang = np.linspace(0, 2*np.pi, 25)
                    pls.append({"pts": [[p[0]+r*np.cos(a), p[1]+r*np.sin(a)] for a in ang], "color": col, "closed": True})
                pts.append(p)
    return {"polylines": pls, "points": pts}


if __name__ == "__main__":
    x0, y0, x1, y1, s = map(int, sys.argv[1:6])
    view = sys.argv[7] if len(sys.argv) > 7 else None
    mc.crop(x0, y0, x1, y1, s, 25 if s < 3 else 10, sys.argv[6], overlay=overlay_json(view))
