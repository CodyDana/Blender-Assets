"""r20 look: floor colour stats. Albedo of a BC map (x tint, linear), and image regions, as mean sRGB + HSV."""
import colorsys, sys, json
import numpy as np
from PIL import Image

def lin(c): return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
def srgb(l): l = np.clip(l, 0, 1); return np.where(l <= 0.0031308, l * 12.92, 1.055 * l ** (1 / 2.4) - 0.055)

def hsv_of(rgb):
    h, s, v = colorsys.rgb_to_hsv(*[float(x) for x in rgb])
    return round(h * 360, 1), round(s, 3), round(v, 3)

def tex(path, tint=1.0):
    a = np.asarray(Image.open(path).convert("RGB")).astype(float) / 255
    l = lin(a) * tint
    m = l.reshape(-1, 3).mean(0)          # mean linear albedo
    s = srgb(m)
    lum = float((m * [0.2126, 0.7152, 0.0722]).sum())
    return {"file": path.split("\\")[-1].split("/")[-1], "tint": tint, "mean_lin": [round(float(x), 4) for x in m],
            "mean_srgb": [round(float(x), 3) for x in s], "srgb255": [int(round(float(x) * 255)) for x in s],
            "hsv(of mean sRGB)": hsv_of(s), "lin_lum": round(lum, 4)}

def region(path, box):
    a = np.asarray(Image.open(path).convert("RGB")).astype(float) / 255
    x0, y0, x1, y1 = box
    r = a[y0:y1, x0:x1].reshape(-1, 3)
    m = srgb(lin(r).mean(0))
    return {"box": box, "mean_srgb": [round(float(x), 3) for x in m], "hsv": hsv_of(m)}

if __name__ == "__main__":
    print(json.dumps(eval(sys.argv[1]), indent=1))
