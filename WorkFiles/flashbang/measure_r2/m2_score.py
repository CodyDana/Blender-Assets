import numpy as np, json
W = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/measure_r2/"
ref = np.load(W + "m2_refmask.npy")
info = json.load(open(W + "m2_refinfo.json"))
H = ref.shape[0]
full = np.zeros((1254, 1254), bool); full[:H] = ref
for v, d in info.items():  # clip floor shadow beside the cap
    x0, x1 = d["cap_x"]; full[676:, :x0 - 3] &= False if False else full[676:, :x0 - 3]
r2 = full.reshape(627, 2, 627, 2).mean((1, 3)) > 0.5
VB = {"v1": (40, 345), "v2": (345, 615), "v3": (615, 950), "v4": (950, 1240)}
out = {}
for el in ("el0", "tz30", "tz130", "tz180"):
    z = np.load(W + f"m2_sweep_{el}.npz")
    for v, (x0, x1) in VB.items():
        a, b = x0 // 2, x1 // 2
        R = r2[:, a:b]
        sc = []
        for k in z.files:
            O = z[k][:, a:b]
            # ignore rows below the floor shadow for the ref: rows > bottom
            sc.append((float((R & O).sum() / (R | O).sum()), int(k)))
        sc.sort(reverse=True)
        out[(el, v)] = sc[:4]
        print(el, v, [(round(s, 3), y) for s, y in sc[:5]])
