p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/fan_geom.py"
s = open(p, encoding="utf-8").read()
def rep(old, new, count=1):
    global s
    assert old in s, old[:60]
    s = s.replace(old, new, count)
rep('''        self.TG: List[str] = []                           # group (face / stick id)''',
    '''        self.TG: List[str] = []                           # group (face / stick id)
        self.TL: List[np.ndarray] = []                    # (3, 2) per-corner local paint coords (mm)
        self.TK: List[str] = []                           # paint kind (leaf / top / bottom / wall / rivet)''')
rep('''    def tri(self, pts, uvs, nrms, bone: str, slot: int, part: str, group: str, layer: str = "",
            check_normal: bool = True):''', '''    def tri(self, pts, uvs, nrms, bone: str, slot: int, part: str, group: str, layer: str = "",
            check_normal: bool = True, locs=None, kind: str = ""):''')
rep('''        if check_normal and float(n @ nrms.mean(0)) < 0:
            idx = idx[::-1]
            uvs = list(uvs)[::-1]
            nrms = nrms[::-1]''', '''        locs = np.zeros((3, 2)) if locs is None else np.asarray(locs, np.float64)
        if check_normal and float(n @ nrms.mean(0)) < 0:
            idx = idx[::-1]
            uvs = list(uvs)[::-1]
            nrms = nrms[::-1]
            locs = locs[::-1]''')
rep('''        self.TG.append(group)

    def triangles''', '''        self.TG.append(group)
        self.TL.append(np.asarray(locs, np.float64))
        self.TK.append(kind)

    def triangles''')
# sticks: top/bottom locs = stick-frame coords; walls = (perimeter, z)
rep('''            mb.tri([P(q, zz) for q in pts], [uvf(q) for q in pts], [nrm] * 3, bone, slot, "sticks", group)''',
    '''            mb.tri([P(q, zz) for q in pts], [uvf(q) for q in pts], [nrm] * 3, bone, slot, "sticks", group,
                   locs=[q for q in pts], kind="top" if zz == z1 else "bottom")''')
rep('''            mb.tri([ca, cb, cc], [uva, uvb, uvc], [na, nb, nc], bone, slot, "sticks", group)
            mb.tri([ca, cc, cd], [uva, uvc, uvd], [na, nc, nd], bone, slot, "sticks", group)''',
    '''            la, lb = (per[i], za), (per[i + 1], za)
            lc, ld = (per[i + 1], zb), (per[i], zb)
            mb.tri([ca, cb, cc], [uva, uvb, uvc], [na, nb, nc], bone, slot, "sticks", group, locs=[la, lb, lc], kind="wall")
            mb.tri([ca, cc, cd], [uva, uvc, uvd], [na, nc, nd], bone, slot, "sticks", group, locs=[la, lc, ld], kind="wall")''')
rep('''            mb.tri([A1, B1, B0], [u0, u1, u2], [_rot_n(na, frame_deg), _rot_n(nb, frame_deg), _rot_n(nb, frame_deg)],
                   bone, slot, "sticks", group)
            mb.tri([A1, B0, A0], [u0, u2, u3], [_rot_n(na, frame_deg), _rot_n(nb, frame_deg), _rot_n(na, frame_deg)],
                   bone, slot, "sticks", group)''', '''            hl = [(i * 0.5, z1), ((i + 1) * 0.5, z1), ((i + 1) * 0.5, z0), (i * 0.5, z0)]
            mb.tri([A1, B1, B0], [u0, u1, u2], [_rot_n(na, frame_deg), _rot_n(nb, frame_deg), _rot_n(nb, frame_deg)],
                   bone, slot, "sticks", group, locs=[hl[0], hl[1], hl[2]], kind="hole")
            mb.tri([A1, B0, A0], [u0, u2, u3], [_rot_n(na, frame_deg), _rot_n(nb, frame_deg), _rot_n(na, frame_deg)],
                   bone, slot, "sticks", group, locs=[hl[0], hl[2], hl[3]], kind="hole")''')
# leaf: locs = flat development coords
rep('''        uvs = []
        for c in range(4):
            k = fold_of(f, c)''', '''        uvs, flat = [], []
        for c in range(4):
            k = fold_of(f, c)''')
rep('''            uvs.append(uvf(k, dist) / side)
        bone = f"leaf_{j:02d}"''', '''            uvs.append(uvf(k, dist) / side)
            th = k * spec.face_angle_deg * D2R
            flat.append(np.array([dist * math.cos(th), dist * math.sin(th)]))
        bone = f"leaf_{j:02d}"''')
rep('''            mb.tri([q[a], q[b], q[c]], [uvs[a], uvs[b], uvs[c]], [cn[a], cn[b], cn[c]], bone, slot, "leaf", grp,
                   layer="front")''', '''            mb.tri([q[a], q[b], q[c]], [uvs[a], uvs[b], uvs[c]], [cn[a], cn[b], cn[c]], bone, slot, "leaf", grp,
                   layer="front", locs=[flat[a], flat[b], flat[c]], kind="leaf")''')
rep('''            mb.tri([back[a], back[c], back[b]], [uvs[a], uvs[c], uvs[b]], [-cn[a], -cn[c], -cn[b]], bone, slot, "leaf",
                   grp, layer="back")''', '''            mb.tri([back[a], back[c], back[b]], [uvs[a], uvs[c], uvs[b]], [-cn[a], -cn[c], -cn[b]], bone, slot, "leaf",
                   grp, layer="back", locs=[flat[a], flat[c], flat[b]], kind="leaf")''')
open(p, "w", encoding="utf-8").write(s)
print("patched")
