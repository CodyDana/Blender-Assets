"""One-off patch of Scripts/dojo/outside/build_outside.py for round 5 fix f1 (far town, ridge rings, house variety,
thinner power line). Kept for the record; the builder itself is the source of truth afterwards."""
from pathlib import Path

p = Path(r"C:\Users\Cody\Desktop\Blender_Projects\Scripts\dojo\outside\build_outside.py")
s = p.read_text(encoding="utf-8")
rep = []
# 1. far ground: to the first ridge's foot
rep.append(('''    n = 160
    radii = [None, 60.0, 200.0, 600.0, 1400.0]
    verts, faces = [], []
    for k in range(n):
        th = 2 * math.pi * k / n
        ex, ey = rect_edge_point(th)
        r0 = math.hypot(ex - CX, ey - CY)
        z0 = edge_z(ex, ey) - 0.3
        for j, R in enumerate(radii):
            if R is None:
                verts.append(Vector((ex, ey, z0)))
            else:
                rr = max(R + r0, r0 + 5.0)
                zz = z0 + (-12.0 - z0) * smooth(0.0, 900.0, rr - r0)
                verts.append(Vector((CX + math.cos(th) * rr, CY + math.sin(th) * rr, zz)))''',
'''    n = 160
    # round 5 fix f1: out to FAR_R + 40 (under the first ridge ring's front foot), covered by the far town; it no
    # longer reaches the horizon as a plain (the judges' 'flat lavender plane with a hard straight edge')
    radii = [None, 60.0, 200.0, FAR_R + 40.0]
    verts, faces = [], []
    for k in range(n):
        th = 2 * math.pi * k / n
        ex, ey = rect_edge_point(th)
        r0 = math.hypot(ex - CX, ey - CY)
        z0 = edge_z(ex, ey) - 0.3
        for j, R in enumerate(radii):
            if R is None:
                verts.append(Vector((ex, ey, z0)))
            else:
                rr = max(R if j == len(radii) - 1 else R + r0, r0 + 5.0)
                verts.append(Vector((CX + math.cos(th) * rr, CY + math.sin(th) * rr, far_z_r(z0, rr - r0))))'''))
rep.append(('''def far_ground():''', '''FAR_R = 430.0          # round 5 f1: the far town / far ground radius (the first ridge ring's front foot at 450 m)


def far_z_r(z0, d):
    """Far ground height d m past the town rectangle's edge (edge height z0): a gentle fall to -4 m."""
    return z0 + (-4.0 - z0) * smooth(0.0, 350.0, d)


def far_z(x, y):
    th = math.atan2(y - CY, x - CX)
    ex, ey = rect_edge_point(th)
    return far_z_r(edge_z(ex, ey) - 0.3, math.hypot(x - CX, y - CY) - math.hypot(ex - CX, ey - CY))


def far_house(g, rng, cx, cy, ang, w, d, eave, kind, z0):
    """One low-poly far-town house (about 20 tris): walls, a gable / hip / gable-front roof with eave overhangs and
    underside faces (seen from the courtyard's low eye). u = frontage (w), v = depth (d), rotated by ang."""
    ca, sa = math.cos(ang), math.sin(ang)

    def P0(u, v, z):
        return Vector((cx + u * ca - v * sa, cy + u * sa + v * ca, z))
    wall = OX.FWALL_P if (kind == "kura" or rng.random() < 0.6) else OX.FWALL_W
    roof = OX.FROOF_A if rng.random() < 0.55 else OX.FROOF_B
    hu, hv = w / 2, d / 2
    corners = [(-hu, -hv), (hu, -hv), (hu, hv), (-hu, hv)]
    for k in range(4):                                  # outward walls (counter-clockwise seen from outside)
        (u0, v0), (u1, v1) = corners[k], corners[(k + 1) % 4]
        g.add([P0(u0, v0, z0), P0(u1, v1, z0), P0(u1, v1, eave), P0(u0, v0, eave)], [(0, 1, 2, 3)], wall, None,
              jit=False)
    ov = 0.5
    tn = math.tan(math.radians(rng.uniform(22.0, 28.0)))
    if kind in ("gable_front", "kura"):                 # ridge along v: swap the axes (a quarter turn)
        hu, hv = hv, hu

        def P(u, v, z):
            return P0(-v, u, z)
    else:
        P = P0
    zr = eave + hv * tn                                 # ridge over the wall line's centre
    ze = eave - ov * tn                                 # the eave edge, ov past the wall
    if kind == "hip" and hu > hv + 0.5:
        rl = hu - hv
        slopes = [[P(-hu - ov, -hv - ov, ze), P(hu + ov, -hv - ov, ze), P(rl, 0.0, zr), P(-rl, 0.0, zr)],
                  [P(hu + ov, hv + ov, ze), P(-hu - ov, hv + ov, ze), P(-rl, 0.0, zr), P(rl, 0.0, zr)]]
        tris = [[P(hu + ov, -hv - ov, ze), P(hu + ov, hv + ov, ze), P(rl, 0.0, zr)],
                [P(-hu - ov, hv + ov, ze), P(-hu - ov, -hv - ov, ze), P(-rl, 0.0, zr)]]
    else:
        slopes = [[P(-hu - ov, -hv - ov, ze), P(hu + ov, -hv - ov, ze), P(hu + ov, 0.0, zr), P(-hu - ov, 0.0, zr)],
                  [P(hu + ov, hv + ov, ze), P(-hu - ov, hv + ov, ze), P(-hu - ov, 0.0, zr), P(hu + ov, 0.0, zr)]]
        tris = []
        for sgn in (-1, 1):                             # gable triangles (wall material) in the wall planes
            a, b, c = P(sgn * hu, -hv, eave), P(sgn * hu, hv, eave), P(sgn * hu, 0.0, zr - 0.05)
            g.add([a, b, c] if sgn > 0 else [b, a, c], [(0, 1, 2)], wall, None, jit=False)
    dn = Vector((0.0, 0.0, -0.03))
    for q in slopes:                                    # top, and a 3 cm lower underside (its own vertices)
        g.add(q, [(0, 1, 2, 3)], roof, None, jit=False)
        g.add([v + dn for v in q], [(3, 2, 1, 0)], roof, None, jit=False)
    for t in tris:
        g.add(t, [(0, 1, 2)], roof, None, jit=False)
        g.add([v + dn for v in t], [(2, 1, 0)], roof, None, jit=False)


def far_town():
    """Round 5 fix f1: the far town, roof clusters from the town rectangle out to FAR_R (430 m), so the ground never
    shows as a plain at the horizon (dojo1_reference2: distant roofs, then the hazy ranges). Districts of rectangular
    blocks (their own grid rotation per 45 deg sector), two back-to-back rows of houses per block with random frontage,
    depth, eave height and type (gable, hip, gable-front, kura, two-storey), thinning a little with distance."""
    p = Piece("SM_DKX_FarTown", "nocollision", "Outside/Far",
              "round 5 f1: the far town (low-poly roof clusters to 430 m, about 20 tris a house) in place of the flat "
              "far plain; flat colour sets M_DKX_FarRoofA/B, M_DKX_FarWallPlaster/Wood; no collision (token UCX)",
              pivot=(CX, CY, 0.0))
    rng = random.Random(4242)
    g = p.g
    n_house = 0
    sectors = 8
    for sct in range(sectors):
        rot = math.radians(sct * 45.0 + rng.uniform(-12.0, 12.0))
        ca, sa = math.cos(rot), math.sin(rot)
        BL, BS, ST = rng.uniform(30.0, 40.0), rng.uniform(19.0, 25.0), rng.uniform(4.5, 6.5)
        n = int(FAR_R / min(BL, BS)) + 2
        for i in range(-n, n + 1):
            for j in range(-n, n + 1):
                bu, bv = i * (BL + ST), j * (BS + ST)
                bx, by = CX + bu * ca - bv * sa, CY + bu * sa + bv * ca
                th = math.atan2(by - CY, bx - CX) % (2 * math.pi)
                if int(th / (2 * math.pi / sectors)) % sectors != sct:
                    continue
                r = math.hypot(bx - CX, by - CY)
                if r > FAR_R - 10.0:
                    continue
                if XW - 8.0 < bx < XE + 8.0 and YS - 8.0 < by < YN + 8.0:
                    continue
                if rng.random() < 0.08:                 # an open yard / temple ground now and then
                    continue
                for row in (-1, 1):
                    dep = rng.uniform(6.0, 9.0)
                    vv = bv + row * (BS / 2 - dep / 2 - rng.uniform(0.0, 0.8))
                    u = bu - BL / 2 + rng.uniform(0.0, 1.5)
                    while True:
                        wdt = rng.uniform(6.0, 14.0)
                        if u + wdt > bu + BL / 2:
                            break
                        uc = u + wdt / 2
                        hx, hy = CX + uc * ca - vv * sa, CY + uc * sa + vv * ca
                        u += wdt + rng.uniform(0.3, 2.2)
                        if XW - 3.0 < hx < XE + 3.0 and YS - 3.0 < hy < YN + 3.0:
                            continue
                        rr = math.hypot(hx - CX, hy - CY)
                        if rr > FAR_R or rng.random() < 0.06 + 0.22 * smooth(250.0, FAR_R, rr):
                            continue
                        t = rng.random()
                        if t < 0.50:
                            kind, eave = "gable", rng.uniform(2.8, 3.5)
                        elif t < 0.70:
                            kind, eave = "hip", rng.uniform(3.0, 3.6)
                        elif t < 0.82:
                            kind, eave = "gable_front", rng.uniform(4.0, 5.0)
                        elif t < 0.90:
                            kind, eave = "kura", rng.uniform(4.2, 5.2)
                        else:
                            kind, eave = "gable", rng.uniform(5.0, 5.8)      # two-storey
                        z0 = far_z(hx, hy) - 0.2
                        far_house(g, rng, hx, hy, rot + (math.pi if row > 0 else 0.0), wdt, dep, z0 + eave, kind, z0)
                        n_house += 1
    p.hull_box(CX - 0.02, CX + 0.02, CY - 0.02, CY + 0.02, -60.02, -59.98)
    p.wear = False
    p.nanite = True
    p.extra = {"houses": n_house, "radius_m": FAR_R}
    return p


def far_ground():'''))
# 2. four ridge rings
rep.append(('''    P += [far_ground(),
          mountains("SM_DKX_Mountains_Near", 900.0, 1150.0, 1350.0, 30.0, 60.0, 31, MNEAR,
                    "near ridge ring round the town (0.9-1.35 km, ridge 30-90 m): low dark forested hills; a far MESH "
                    "(M_DKX_MountainNear, flat, haze-friendly); no collision (token UCX)"),
          mountains("SM_DKX_Mountains_Far", 1600.0, 1900.0, 2200.0, 120.0, 180.0, 57, MFAR,
                    "far ridge ring (1.6-2.2 km, ridge 120-300 m, inside the 2.4 km cloud dome): paler blue-grey "
                    "ridges (M_DKX_MountainFar); no collision (token UCX)")]''',
'''    P += [far_ground(), far_town()] + [
        mountains(f"SM_DKX_Ridge{k + 1}", rf, rr, rb, base, amp, seed, OX.RIDGES[k],
                  f"round 5 f1 ridge ring {k + 1} of 4 ({rf / 1000:.2f}-{rb / 1000:.2f} km, ridge {base:.0f}-"
                  f"{base + amp:.0f} m): its own flat emissive colour, lighter and bluer with distance (the far ridge "
                  "near the sky colour), the height fog on top; no collision (token UCX)")
        for k, (rf, rr, rb, base, amp, seed) in enumerate(RIDGE_RINGS)]'''))
rep.append(('''def ridge_heights(n, seed, base, amp, kmax=48, peaks=6):''',
'''# round 5 fix f1: four ridge rings in place of the two smooth shells (front foot, ridge, back radius m; ridge base and
# amplitude m; seed). Elevations from the courtyard: about 1.5-4.5 deg (ring 1, mostly behind the town roofs), 2-5.5,
# 2.7-7, 3.3-8.7: the layered, receding ranges of dojo1_reference2
RIDGE_RINGS = [(450.0, 560.0, 650.0, 14.0, 30.0, 131), (800.0, 980.0, 1120.0, 30.0, 62.0, 31),
               (1300.0, 1520.0, 1700.0, 70.0, 125.0, 57), (1850.0, 2080.0, 2250.0, 120.0, 200.0, 77)]


def ridge_heights(n, seed, base, amp, kmax=48, peaks=6):'''))
# 3. instances: far town + ridges; houses with scale
rep.append(('''          ("SM_DKX_FarGround", (CX, CY, 0.0), 0.0),
          ("SM_DKX_Mountains_Near", (CX, CY, 0.0), 0.0),
          ("SM_DKX_Mountains_Far", (CX, CY, 0.0), 0.0)]''',
'''          ("SM_DKX_FarGround", (CX, CY, 0.0), 0.0), ("SM_DKX_FarTown", (CX, CY, 0.0), 0.0)] + \\
        [(f"SM_DKX_Ridge{k + 1}", (CX, CY, 0.0), 0.0) for k in range(len(RIDGE_RINGS))]'''))
rep.append(('''    for (pc, hx, hy, rot) in house_list:
        h = HOUSES[pc]
        W, D = h["W"], h["D"]''', '''    for (pc, hx, hy, rot, hsc) in house_list:
        h = HOUSES[pc]
        W, D = h["W"] * hsc[0], h["D"]'''))
rep.append(('''        I.append((pc, (hx, hy, round(min(zs), 3)), rot))
    return I''', '''        I.append((pc, (hx, hy, round(min(zs), 3)), rot, "", hsc))
    return I'''))
# 4. house plan: scale + mixed types
rep.append(('''        while True:
            pc = seq[k % len(seq)]
            h = HOUSES[pc]
            W, D = h["W"], h["D"]''', '''        while True:
            pc = seq[k % len(seq)]
            if rng.random() < 0.35:                    # round 5 f1: break the cycle (the judges: one type repeated)
                pc = rng.choice(list(HOUSES))
            h = HOUSES[pc]
            # round 5 f1: every house its own frontage length and height (instance scale on local X / Z)
            sx, sz = rng.uniform(0.82, 1.22), rng.uniform(0.86, 1.16)
            W, D = h["W"] * sx, h["D"]'''))
rep.append(('''            if axis == "y":
                out.append((pc, c, mid, facing_rot))
            else:
                out.append((pc, mid, c, facing_rot))''', '''            if axis == "y":
                out.append((pc, c, mid, facing_rot, (round(sx, 3), 1.0, round(sz, 3))))
            else:
                out.append((pc, mid, c, facing_rot, (round(sx, 3), 1.0, round(sz, 3))))'''))
rep.append(('''    tall = ["SM_DKX_House_E", "SM_DKX_House_A", "SM_DKX_House_C", "SM_DKX_House_A", "SM_DKX_House_E", "SM_DKX_House_B"]''',
'''    tall = ["SM_DKX_House_E", "SM_DKX_House_B", "SM_DKX_House_C", "SM_DKX_House_A", "SM_DKX_House_D", "SM_DKX_House_E",
            "SM_DKX_House_C", "SM_DKX_House_B"]   # round 5 f1: single-storey and kura mixed in'''))
rep.append(('''        "houses": [{"piece": h[0], "x": round(h[1], 3), "y": round(h[2], 3), "rot_z": h[3]} for h in house_list],''',
'''        "houses": [{"piece": h[0], "x": round(h[1], 3), "y": round(h[2], 3), "rot_z": h[3], "scale": list(h[4])}
                   for h in house_list],'''))
# 5. thin the power line: the upper crossarm's four conductors only
rep.append(('''            if x0 == -15.5:
                span_rows.setdefault(r["piece"], []).append((r["loc"][0] - x0, r["loc"][1] - old_y, r["loc"][2],
                                                             note.split(",")[0]))''',
'''            lab = note.split(",")[0]
            # round 5 fix f1 (whole judge delta 9: the wires clutter the skyline over the gate): the power line keeps
            # its upper crossarm (conductors A-D); the lower arm's E-H are dropped
            if x0 == -15.5 and not any(lab.endswith(f"Wire_{c}") for c in "EFGH"):
                span_rows.setdefault(r["piece"], []).append((r["loc"][0] - x0, r["loc"][1] - old_y, r["loc"][2], lab))'''))
# 6. waivers
rep.append(('''    waive = {n: ("texel_density",) for n in ("SM_DKX_Water", "SM_DKX_FarGround", "SM_DKX_Mountains_Near",
                                               "SM_DKX_Mountains_Far")}''',
'''    waive = {n: ("texel_density",) for n in ("SM_DKX_Water", "SM_DKX_FarGround", "SM_DKX_FarTown")
             + tuple(f"SM_DKX_Ridge{k + 1}" for k in range(len(RIDGE_RINGS)))}'''))
for a, b in rep:
    assert a in s, a[:80]
    s = s.replace(a, b)
p.write_text(s, encoding="utf-8")
print("patched", len(rep))
