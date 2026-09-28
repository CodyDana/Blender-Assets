
def audit_face(parts, label, m):
    """Any stem (own or other) running through or in front of a blossom's face (axis samples inside its disc above
    the back surface, 1 mm tolerance)."""
    axes, flowers = [], []
    for verts, faces, uvs, mats, sm in parts:
        vv = [Vector(v) for v in verts]
        if isinstance(mats, list):
            c = vv[0]
            R = max((v - c).length for v in vv)
            # normal: the flower's first petal fan tri faces +nrm
            f0 = faces[0]
            nrm = sum(((vv[f[1]] - vv[f[0]]).cross(vv[f[2]] - vv[f[0]]) for f in faces[:5 * (m + 1)]), Vector()).normalized()
            R = max(((v - c) - nrm * (v - c).dot(nrm)).length for v in vv[:1 + 5 + 5 * m])
            flowers.append((c, R, nrm))
        elif mats == M.BARK:
            sides = faces[0][3]
            nring = (len(vv) - 1) // sides
            cen = [sum(vv[k * sides:(k + 1) * sides], Vector()) / sides for k in range(nring)]
            rad = [(vv[k * sides] - cen[k]).length for k in range(nring)]
            axes.append((cen, rad))
    bad = []
    for c, R, nrm in flowers:
        hit = False
        for cen, rad in axes:
            for i in range(1, len(cen)):
                a, b = cen[i - 1], cen[i]
                n = max(1, int((b - a).length / 0.002))
                for j in range(n + 1):
                    q = a.lerp(b, j / n); rr = rad[i - 1] + (rad[i] - rad[i - 1]) * j / n
                    d = q - c
                    if d.length > 1.05 * R + rr:
                        continue
                    h = d.dot(nrm); rho = (d - nrm * h).length
                    if rho - rr > 0.9 * R:
                        continue
                    hb = -0.03 * R + (0.42 * 0.846 * R + 0.03 * R) * min(1.0, max(0.0, rho - rr) / (0.92 * R))
                    hf = 0.42 * 1.12 * R * (min(1.0, max(0.0, rho - rr) / (0.92 * R))) ** 2 + 0.3 * R
                    if h + rr > hb + 0.001 and h - rr < hf + 0.45 * R:
                        hit = True; break
                if hit: break
            if hit: break
        if hit:
            bad.append(tuple(round(x, 3) for x in c))
    print("AUDIT_FACE", label, "blossoms with a stem across the face", len(bad), "of", len(flowers), bad[:6])
