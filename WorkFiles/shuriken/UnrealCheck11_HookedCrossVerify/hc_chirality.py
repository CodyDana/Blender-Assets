"""UnrealCheck11: which way does a hooked cross read ON SCREEN?  Pure Python (no numpy, no bpy, no unreal), so the very
same code runs inside Blender and inside the Unreal commandlet.  Written fresh for this verification; it does not use
shuriken_lib.outline_plate.handedness_gate.

Input: the triangles a viewer actually sees (front-facing to that viewer), already projected to SCREEN coordinates
(x to the viewer's right, y up, millimetres, the plate centre at the origin).  Screen coordinates carry the viewer's
own orientation, so "counter-clockwise" below is counter-clockwise as the viewer sees it.

    tips   the four vertices farthest from the centre (clustered by angle; one tip per cluster)
    arms   the angular runs of the visible surface on a probe circle through the arms' straight part (r = 20 mm lies
           between the centre square and the hook inner corners at u = 34.4 mm); the run centre is the arm axis
    offset the signed angle from the nearest arm axis to each tip, counter-clockwise positive

Reading (the study 2.6 definition, restated in screen terms): +35 deg on all four arms = every hook runs
counter-clockwise of its arm = the left-facing form (U+534D); -35 deg on all four = the mirror image (U+5350).
"""
import math

LEFT = "left-facing (U+534D): every hook tip counter-clockwise of its arm"
RIGHT = "right-facing mirror image (U+5350): every hook tip clockwise of its arm"


def wrap(a):
    return (a + 180.0) % 360.0 - 180.0


def _in_tri(p, a, b, c, eps=1e-9):
    d1 = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
    d2 = (c[0] - b[0]) * (p[1] - b[1]) - (c[1] - b[1]) * (p[0] - b[0])
    d3 = (a[0] - c[0]) * (p[1] - c[1]) - (a[1] - c[1]) * (p[0] - c[0])
    neg = d1 < -eps or d2 < -eps or d3 < -eps
    pos = d1 > eps or d2 > eps or d3 > eps
    return not (neg and pos)


def signed_area2(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])


def analyse(tris2d, probe_r=20.0, n_samples=7200, tip_tol=0.05, cluster_deg=10.0):
    """tris2d: [((x0, y0), (x1, y1), (x2, y2)), ...] in screen mm.  Returns a dict with the verdict."""
    tris2d = [t for t in tris2d if abs(signed_area2(*t)) > 1e-12]
    pts = {}
    for t in tris2d:
        for p in t:
            pts[(round(p[0], 6), round(p[1], 6))] = p
    pts = list(pts.values())
    radius = [math.hypot(x, y) for x, y in pts]
    rmax = max(radius)
    cand = sorted(((r, math.degrees(math.atan2(p[1], p[0])), p) for p, r in zip(pts, radius) if r > rmax - tip_tol),
                  key=lambda c: -c[0])
    tips = []
    for r, a, p in cand:
        if all(abs(wrap(a - t["angle_deg"])) > cluster_deg for t in tips):
            tips.append({"angle_deg": round(a, 4), "r_mm": round(r, 5), "xy_mm": [round(p[0], 5), round(p[1], 5)]})
    # coverage of the probe circle, through a uniform grid of triangle buckets
    cell = 2.0
    grid = {}
    for ti, (a, b, c) in enumerate(tris2d):
        x0, x1 = min(a[0], b[0], c[0]), max(a[0], b[0], c[0])
        y0, y1 = min(a[1], b[1], c[1]), max(a[1], b[1], c[1])
        if math.hypot(max(abs(x0), abs(x1)), max(abs(y0), abs(y1))) < probe_r - 1e-6:
            continue
        for gx in range(int(math.floor(x0 / cell)), int(math.floor(x1 / cell)) + 1):
            for gy in range(int(math.floor(y0 / cell)), int(math.floor(y1 / cell)) + 1):
                grid.setdefault((gx, gy), []).append(ti)
    cov = []
    for i in range(n_samples):
        th = 2.0 * math.pi * (i + 0.5) / n_samples
        p = (probe_r * math.cos(th), probe_r * math.sin(th))
        hit = False
        for ti in grid.get((int(math.floor(p[0] / cell)), int(math.floor(p[1] / cell))), ()):
            if _in_tri(p, *tris2d[ti]):
                hit = True
                break
        cov.append(hit)
    runs = []
    if all(cov):
        runs = []
    elif any(cov):
        start = next(i for i in range(n_samples) if not cov[i])        # rotate so index 0 is uncovered
        order = [(start + k) % n_samples for k in range(n_samples)]
        cur = None
        for idx in order:
            if cov[idx]:
                if cur is None:
                    cur = [idx, idx, 1]
                else:
                    cur[1], cur[2] = idx, cur[2] + 1
            elif cur is not None:
                runs.append(cur)
                cur = None
        if cur is not None:
            runs.append(cur)
    step = 360.0 / n_samples
    arms = []
    for a, _b, n in runs:
        start_deg = (a + 0.5) * step
        centre = wrap(start_deg + (n - 1) * step / 2.0)
        arms.append({"axis_deg": round(centre, 3), "width_deg": round(n * step, 3)})
    arms.sort(key=lambda r: r["axis_deg"])
    out = {"visible_triangles": len(tris2d), "tip_radius_mm": round(rmax, 5), "probe_radius_mm": probe_r,
           "tips": tips, "arms": arms}
    for t in tips:
        if arms:
            near = min(arms, key=lambda r: abs(wrap(t["angle_deg"] - r["axis_deg"])))
            t["arm_axis_deg"] = near["axis_deg"]
            t["offset_ccw_deg"] = round(wrap(t["angle_deg"] - near["axis_deg"]), 3)
            others = sorted(abs(wrap(t["angle_deg"] - r["axis_deg"])) for r in arms)
            t["next_arm_distance_deg"] = round(others[1], 3) if len(others) > 1 else None
    offs = [t.get("offset_ccw_deg") for t in tips]
    spacing = [round(wrap(arms[(i + 1) % len(arms)]["axis_deg"] - arms[i]["axis_deg"]) % 360.0, 3)
               for i in range(len(arms))] if len(arms) > 1 else []
    out["arm_spacing_deg"] = spacing
    shape_ok = len(tips) == 4 and len(arms) == 4 and all(abs(s - 90.0) < 1.0 for s in spacing)
    out["four_tips_four_arms_c4"] = shape_ok
    if shape_ok and all(o is not None and 34.0 < o < 36.0 for o in offs):
        out["reads"], out["left_facing"] = LEFT, True
    elif shape_ok and all(o is not None and -36.0 < o < -34.0 for o in offs):
        out["reads"], out["left_facing"] = RIGHT, False
    else:
        out["reads"], out["left_facing"] = "undetermined", None
    # the arm that points to the viewer's right, and where its hook goes (the study's wording, screen terms)
    if shape_ok:
        right_arm = min(arms, key=lambda r: abs(wrap(r["axis_deg"])))
        tip = [t for t in tips if t.get("arm_axis_deg") == right_arm["axis_deg"]]
        if tip:
            out["screen_right_arm_hooks"] = "up" if tip[0]["xy_mm"][1] > 0 else "down"
        up_arm = min(arms, key=lambda r: abs(wrap(r["axis_deg"] - 90.0)))
        tip = [t for t in tips if t.get("arm_axis_deg") == up_arm["axis_deg"]]
        if tip:
            out["screen_up_arm_hooks"] = "left" if tip[0]["xy_mm"][0] < 0 else "right"
    return out


# ---------------------------------------------------------------- 3D helpers shared by both sides
def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def norm(a):
    ln = math.sqrt(dot(a, a))
    return (a[0] / ln, a[1] / ln, a[2] / ln) if ln > 0 else (0.0, 0.0, 0.0)


def winding_normal(p0, p1, p2, convention):
    """Face normal implied by the corner order.  'blender': right-handed CCW, (P1-P0) x (P2-P0).  'unreal': the
    engine's own rule (StaticMeshOperations.cpp: 'We have a left-handed coordinate system, but a counter-clockwise
    winding order. Hence normal calculation has to take the triangle vectors cross product in reverse.'):
    CrossProduct(P2-P0, P1-P0)."""
    if convention == "blender":
        return cross(sub(p1, p0), sub(p2, p0))
    return cross(sub(p2, p0), sub(p1, p0))


def screen_view(verts, tris, face_normals, forward, right, up):
    """The triangles a camera with this basis sees front-on (face normal toward the camera: n . forward < 0), projected
    to screen (x = p . right, y = p . up).  Also returns the on-screen signed areas of those triangles in corner order
    (positive = counter-clockwise as the viewer sees it)."""
    out, areas = [], []
    for (i, j, k), n in zip(tris, face_normals):
        if dot(norm(n), forward) >= -1e-9:
            continue
        t = tuple((dot(verts[m], right), dot(verts[m], up)) for m in (i, j, k))
        out.append(t)
        areas.append(signed_area2(*t))
    return out, areas
