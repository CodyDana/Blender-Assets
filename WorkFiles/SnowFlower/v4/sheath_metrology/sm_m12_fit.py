# sm_m12: FIT - can the straight reference sheath hold the blade?  (numpy only, run in Blender python)
# Blade frame: z along blade (seat plane -> tip), x in the blade plane (+x = side the tip sweeps to), y thickness.
# Sheath frame: y_px image rows (mouth top row 31 .. tip 1496), outer half-width from the silhouette.
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from sm_lib import *
s01 = json.load(open(os.path.join(HERE, "sm_s01.json")))
prof = np.array(s01["profile"]); TOP = s01["top"]; BOT = s01["bottom"]
half_px = body_half_table(prof)
body_half_px = lambda y: half_px[int(round(y))]
s09 = json.load(open(os.path.join(HERE, "sm_s09.json")))
s07 = json.load(open(os.path.join(HERE, "sm_s07.json")))

Z_SEAT = 0.1628   # rev-3 guard under-leaf lower face (blade side); pendant hangs to 0.1708 -> mouth pocket
TIP_Z = 1.085
rev3 = []
for r in s09["rows"]:
    if r["z"] < Z_SEAT:
        continue
    ry = max(abs(r.get("rymin", 0)), abs(r.get("rymax", 0)), abs(r["ymin"]), abs(r["ymax"]))
    rev3.append((r["z"] - Z_SEAT, r["xmin"], r["xmax"], ry))
rev3.append((TIP_Z - Z_SEAT, 0.0305, 0.0305, 0.001))
rev3 = np.array(rev3)

# reference-faithful blade from the design sheet front view (mirrored so the tip sweeps to +x like rev-3)
front = {y: rs for y, rs in s07["front"]}
ys = sorted(front)
top_px = ys[0]
# tip row: last row <1235 with a blade run
blade_rows = []
for y in range(338, 1235):
    rs = [r for r in front.get(y, []) if r[0] >= 235 and r[1] <= 335]
    if not rs:
        continue
    l = min(r[0] for r in rs); rr = max(r[1] for r in rs)
    blade_rows.append((y, l, rr))
blade_rows = np.array(blade_rows, float)
tip_px = blade_rows[-1, 0]
sheet_len_px = tip_px - top_px
PXM = sheet_len_px / (TIP_Z + 0.1713)  # sheet px per metre from overall sword length (rev-3 overall 1.2563 m)
axis_x = ((blade_rows[:40, 1] + blade_rows[:40, 2]) / 2).mean()
seat_px = 338
ref = []
for y, l, rr in blade_rows:
    z = (y - seat_px) / PXM
    xa = -(rr - axis_x) / PXM; xb = -(l - axis_x) / PXM  # mirror
    ref.append((z, xa, xb, 0.003))
ref = np.array(ref)
print("sheet: pommel top row %d tip row %d -> %.1f px/m ; ref blade seat->tip %.4f m, base width %.4f m, width at 70%% %.4f"
      % (top_px, tip_px, PXM, ref[-1, 0], ref[0, 2] - ref[0, 1], np.interp(0.7 * ref[-1, 0], ref[:, 0], ref[:, 2] - ref[:, 1])))
def sweep(bl):
    # tip sweep beyond the straight back edge: max x near tip minus back-edge x at 60% length
    z60 = 0.6 * bl[-1, 0]
    return bl[:, 2].max() - np.interp(z60, bl[:, 0], bl[:, 2])
print("tip sweep beyond the straight back edge: rev3 %.4f m, sheet %.4f m" % (sweep(rev3), sweep(ref)))
print("blade length seat->tip: rev3 %.4f  sheet %.4f" % (rev3[-1, 0], ref[-1, 0]))

WALL = 0.0030   # lacquered wall (DESIGNED)
CLR = 0.0015    # clearance per side (DESIGNED)
TIPCLR = 0.005  # tip clearance to cavity end
COLLAR_FRAC = 64 / 97.0  # measured: top collar width / body width below the throat

def fit(bl, y_end, allow_offset=True):
    Lb = bl[-1, 0] + TIPCLR
    k = Lb / (y_end - TOP)              # metres per sheath px
    zs = bl[:, 0]
    yst = TOP + zs / k
    inner = np.array([body_half_px(y) * k for y in yst]) - WALL - CLR
    best = None
    for d in np.linspace(-0.02, 0.02, 801) if allow_offset else [0.0]:
        need = np.maximum(bl[:, 2] - d, d - bl[:, 1])
        m = (inner - need).min()
        if best is None or m > best[0]:
            best = (m, d, int(np.argmin(inner - need)))
    # swept (straight insertion): at station of section i, envelope = [xmin_i, max_{j>=i} xmax_j]
    sx = np.maximum.accumulate(bl[::-1, 2])[::-1]
    bestS = None
    for d in np.linspace(-0.02, 0.02, 801):
        need = np.maximum(sx - d, d - bl[:, 1])
        m = (inner - need).min()
        if bestS is None or m > bestS[0]:
            bestS = (m, d)
    body_w = 97 * k; collar_w = 64 * k
    mouth_need = (bl[0, 2] - bl[0, 1]) + 2 * (CLR + 0.0015)  # blade base + clearance + 1.5 mm metal collar wall
    return dict(y_end=y_end, k_mm_per_px=k * 1000, sheath_len=1466 * k, body_w_mouth=body_w, throat_max_w=147 * k,
                chape_len=(1496 - 1263) * k, static_margin=best[0], offset=best[1], worst_z=float(bl[best[2], 0]),
                swept_margin=bestS[0], swept_offset=bestS[1], collar_w=collar_w, collar_opening=collar_w - 0.003,
                mouth_need=mouth_need, overhang=(1496 - y_end) * k)

res = {"rev3": [], "sheet": []}
for name, bl in (("rev3", rev3), ("sheet", ref)):
    print("\n=== blade:", name)
    print(" y_end  k(mm/px) sheathL  bodyW  throatW  collarW(open) mouthNeed | static margin (offset, worst z) | swept margin (offset) | overhang past tip")
    for y_end in list(range(1150, 1300, 25)) + list(range(1300, 1470, 10)):
        f = fit(bl, y_end)
        res[name].append(f)
        print(" %4d   %.3f   %.3f  %.1fmm  %.1fmm  %.1f(%.1f)  %.1f | %+.1fmm (%+.1f, z %.2f) | %+.1fmm (%+.1f) | %.0fmm" % (
            y_end, f["k_mm_per_px"], f["sheath_len"], f["body_w_mouth"] * 1000, f["throat_max_w"] * 1000,
            f["collar_w"] * 1000, f["collar_opening"] * 1000, f["mouth_need"] * 1000, f["static_margin"] * 1000,
            f["offset"] * 1000, f["worst_z"], f["swept_margin"] * 1000, f["swept_offset"] * 1000, f["overhang"] * 1000))
# thickness requirement (rev3 incl. relief)
print("\nrev3 half-thickness incl relief: max %.4f at z %.3f ; at 50%% %.4f ; at 85%% %.4f" % (
    rev3[:, 3].max(), rev3[np.argmax(rev3[:, 3]), 0], np.interp(0.46, rev3[:, 0], rev3[:, 3]), np.interp(0.78, rev3[:, 0], rev3[:, 3])))
json.dump(dict(PXM=PXM, top_px=top_px, tip_px=float(tip_px), axis_x=float(axis_x), rev3=rev3.tolist(), sheet=ref.tolist(),
               fits=res, WALL=WALL, CLR=CLR, TIPCLR=TIPCLR), open(os.path.join(HERE, "sm_s12.json"), "w"))
