p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/fan_tassel.py"
s = open(p, encoding="utf-8").read()
def rep(old, new, cnt=1):
    global s
    assert old in s, old[:70]
    s = s.replace(old, new, cnt)
rep('''                def nrm(p, dr):
                    v = np.array([p[0], p[1], dr])
                    return v / np.linalg.norm(v)
                dr = (rs[i] - rs[i + 1]) / max(abs(zs[i] - zs[i + 1]), 1e-6)
                na, nb, nc, nd = nrm(a, dr * math.hypot(a[0], a[1]) * 0.0 + dr * rs[i] * 0 + dr), nrm(b, dr), nrm(c, dr), nrm(d, dr)''',
'''                slope = (rs[i + 1] - rs[i]) / (zs[i + 1] - zs[i]) if abs(zs[i + 1] - zs[i]) > 1e-9 else 0.0

                def nrm(p, sl=slope):
                    r = math.hypot(p[0], p[1])
                    v = np.array([p[0] / r, p[1] / r, -sl])
                    return v / np.linalg.norm(v)
                na, nb, nc, nd = nrm(a), nrm(b), nrm(c), nrm(d)''')
s = s.replace('"knot", 0, "tassel", "knot"', '"tassel_root", 0, "tassel", "knot"')
s = s.replace('"skirt_02", 0, "tassel", "skirt"', '"tassel_root", 0, "tassel", "skirt"')
open(p, "w", encoding="utf-8").write(s)
print("ok")
