"""Revision-3 ornament construction, KEPT for the v4 high-poly (bake source).

Ported from Scripts/SnowFlower/build_snow_flower.py and floral_revision.py (revision 3, built by
another agent): the cupped plum petal flower with rims, engraving, filaments and stamens; the
woody relief branch with bark creases; the Catmull-Rom smooth path and the hash noise. The maths
is unchanged; only the output goes to Snow Flower v4 MeshBuilders (millimetres) instead of the
revision-3 global part buffers. Revision 3 worked in metres; every length here is in mm.
"""
from __future__ import annotations

import math

from mathutils import Vector

from sfv4_mesh import MB

# high-poly material slots (see sfv4_look.HIGH_MATERIALS)
BLADE, SILVER, INLAY, RECESS, BLACKSTEEL, BRANCH, CORD, CORE, PEARL = range(9)


class Sink:
    """One MeshBuilder per high material; rev-3 ``add(name, material, group, vs, fs)`` lands here."""

    def __init__(self, prefix):
        self.prefix = prefix
        self.mbs = {}

    def mb(self, mat):
        if mat not in self.mbs:
            self.mbs[mat] = MB(f"{self.prefix}_{mat}")
        return self.mbs[mat]

    def add(self, mat, vs, fs):
        mb = self.mb(mat)
        off = len(mb.verts)
        mb.vs([tuple(v) for v in vs])
        for f in fs:
            mb.f([i + off for i in f], None, "HIGH", mat)


def relief_noise(x, seed):
    i = math.floor(x)
    t = x - i
    t = t * t * (3 - 2 * t)

    def h(j):
        value = math.sin(j * 127.1 + seed * 311.7) * 43758.5453
        return (value - math.floor(value)) * 2 - 1
    return h(i) * (1 - t) + h(i + 1) * t


def smooth_path(points, steps=5):
    p = list(map(Vector, points))
    out = []
    for i in range(len(p) - 1):
        a, b, c, d = p[max(0, i - 1)], p[i], p[i + 1], p[min(len(p) - 1, i + 2)]
        for j in range(steps):
            t = j / steps
            out.append(.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t * t + (-a + 3 * b - 3 * c + d) * t * t * t))
    out.append(p[-1])
    return out


def tube(sink, points, radius, mat=SILVER, sides=6, closed=False):
    """Revision-3 tube (same frame rule)."""
    points = [Vector(p) for p in points]
    if len(points) < 2:
        return
    vs = []
    fs = []
    previous = None
    for i, p in enumerate(points):
        tangent = (points[(i + 1) % len(points)] - points[i - 1] if closed
                   else points[min(i + 1, len(points) - 1)] - points[max(i - 1, 0)])
        if tangent.length < 1e-9:
            tangent = Vector((0, 0, 1))
        tangent.normalize()
        axis = tangent.cross(Vector((0, 1, 0)))
        if axis.length < .001:
            axis = tangent.cross(Vector((1, 0, 0)))
        axis.normalize()
        if previous is not None and axis.dot(previous) < 0:
            axis = -axis
        previous = axis.copy()
        axis2 = tangent.cross(axis).normalized()
        rr = radius(i / max(1, len(points) - 1)) if callable(radius) else radius
        for k in range(sides):
            a = math.tau * k / sides
            vs.append(p + rr * (axis * math.cos(a) + axis2 * math.sin(a)))
    for i in range(len(points) if closed else len(points) - 1):
        j = (i + 1) % len(points)
        for k in range(sides):
            fs.append((i * sides + k, j * sides + k, j * sides + (k + 1) % sides, i * sides + (k + 1) % sides))
    if not closed:
        fs.extend([tuple(reversed(range(sides))), tuple((len(points) - 1) * sides + k for k in range(sides))])
    sink.add(mat, vs, fs)


def ellipsoid(sink, center, a, b, c, mat, segments=12, rings=6):
    center = Vector(center)
    a, b, c = Vector(a), Vector(b), Vector(c)
    vs = [center + c]
    fs = []
    for j in range(1, rings):
        phi = math.pi * j / rings
        for i in range(segments):
            theta = math.tau * i / segments
            vs.append(center + math.sin(phi) * (a * math.cos(theta) + b * math.sin(theta)) + c * math.cos(phi))
    bottom = len(vs)
    vs.append(center - c)
    for i in range(segments):
        fs.append((0, 1 + i, 1 + (i + 1) % segments))
    for j in range(rings - 2):
        for i in range(segments):
            a0 = 1 + j * segments + i
            b0 = 1 + j * segments + (i + 1) % segments
            fs.append((a0, a0 + segments, b0 + segments, b0))
    for i in range(segments):
        fs.append((bottom, 1 + (rings - 2) * segments + (i + 1) % segments, 1 + (rings - 2) * segments + i))
    sink.add(mat, vs, fs)


def flower(sink, center, radius, normal=(0, -1, 0), phase=0.0, large=False, blade=True, up_hint=None):
    """Revision-3 plum blossom (floral_revision.flower), radius = petal length in mm."""
    C = Vector(center)
    N = Vector(normal).normalized()
    U = Vector(up_hint) if up_hint is not None else Vector((1, 0, 0))
    if abs(N.dot(U)) > .9:
        U = Vector((0, 1, 0))
    U = (U - N * U.dot(N)).normalized()
    V = N.cross(U).normalized()
    count = 24 if large else 16
    for k in range(5):
        angle = phase + math.tau * k / 5 + (.018 * math.sin(k * 4.3 + phase) if blade else 0)
        R = U * math.cos(angle) + V * math.sin(angle)
        T = N.cross(R)
        length = radius * (1 + .038 * math.sin(k * 2.7 + phase))
        width = radius * (.335 if blade else (.258 if k == 0 else .335))
        pc = C + R * length * .52
        outline = []
        for j in range(count):
            a = math.tau * j / count
            radial = .48 * length * math.cos(a)
            if blade:
                radial -= length * .045 * math.exp(-((math.atan2(math.sin(a), math.cos(a)) / .23) ** 2))
            lateral = width * math.sin(a) * (1 + .12 * math.cos(a)) * (1 + .025 * math.sin(a * 3 + k))
            if not blade and k == 0:
                lateral *= 1 - .36 * max(0, math.cos(a))
            outline.append((radial, lateral, a))
        verts = [pc + N * radius * .040]
        faces = []
        for ring in (1 / 3, 2 / 3, 1):
            for radial, lateral, a in outline:
                height = radius * (.040 + .072 * ring * ring + .021 * math.cos(a) * ring)
                verts.append(pc + R * (radial * ring) + T * (lateral * ring) + N * height)
        for j in range(count):
            faces.append((0, 1 + j, 1 + (j + 1) % count))
        for ring in range(2):
            for j in range(count):
                a = 1 + ring * count + j
                b = 1 + ring * count + (j + 1) % count
                faces.append((a, a + count, b + count, b))
        bot = len(verts)
        verts.append(pc + N * radius * .014)
        base = len(verts)
        for radial, lateral, a in outline:
            verts.append(pc + R * radial + T * lateral + N * (radius * (.082 + .021 * math.cos(a))))
        for j in range(count):
            a = 1 + 2 * count + j
            b = 1 + 2 * count + (j + 1) % count
            faces.append((a, b, base + (j + 1) % count, base + j))
            faces.append((bot, base + (j + 1) % count, base + j))
        sink.add(INLAY, verts, faces)
        border = [pc + R * r + T * l + N * (radius * (.117 + .021 * math.cos(a))) for r, l, a in outline]
        tube(sink, border, radius * .010, SILVER, 5, True)
        for vindex in (-1, 0, 1):
            line = []
            for j in range(7):
                t = j / 6
                rr = radius * (.14 + .30 * t)
                line.append(C + R * rr + T * (radius * vindex * .047 * t * t) + N * radius * (.085 - .030 * t))
            tube(sink, line, radius * .0034, RECESS, 4)
    ellipsoid(sink, C + N * radius * .125, U * radius * .102, V * radius * .102, N * radius * .065, INLAY, 10, 5)
    for i in range(9 if large else 7):
        a = math.tau * i / (9 if large else 7) + phase
        D = U * math.cos(a) + V * math.sin(a)
        reach = radius * (.17 + .035 * math.sin(i * 2.4))
        end = C + D * reach + N * radius * .165
        tube(sink, [C + D * radius * .065 + N * radius * .12, end], radius * .012, SILVER, 5)
        ellipsoid(sink, end, U * radius * .028, V * radius * .028, N * radius * .026, SILVER, 8, 4)


def relief_branch(sink, points, radii, side_normal, lateral_fn=None, woody=True, mat=BRANCH, steps=10, round_=False):
    """Revision-3 woody relief branch. ``side_normal`` is the substrate normal (rev 3: +-Y).
    ``lateral_fn(p, tangent)`` gives the in-surface lateral direction (default rev-3 XZ rule)."""
    pp = smooth_path(points, steps)
    v = []
    f = []
    sides = 10
    frames_ = []
    Nn = Vector(side_normal).normalized()
    profile = [(-1, 0), (-.76, .16), (-.39, .35), (.10, .66), (.49, .32), (.83, .14), (1, -.03), (.42, -.13),
               (-.30, -.15), (-.85, -.04)]
    if round_:   # look-match R1 (sword blade): a ROUNDED half-round branch (the sheet), not the flat stepped strip
        profile = [(-1, -.10), (-.93, .18), (-.72, .40), (-.38, .55), (.02, .60), (.40, .54), (.74, .38), (.94, .16),
                   (1, -.10), (0, -.16)]
    for i, p in enumerate(pp):
        t = i / (len(pp) - 1)
        u = t * (len(radii) - 1)
        j = min(int(u), len(radii) - 2)
        rr = radii[j] * (1 - (u - j)) + radii[j + 1] * (u - j)
        tangent = (pp[min(i + 1, len(pp) - 1)] - pp[max(0, i - 1)]).normalized()
        lateral = lateral_fn(p, tangent) if lateral_fn else tangent.cross(Nn).normalized()
        key = p.z
        if round_:   # smooth knobbly swelling (the sheet), not a 3 mm zig-zag
            rr *= 1 + .20 * relief_noise(key / 9.0, 3) + .06 * relief_noise(key / 3.5, 7)
            p = p + lateral * rr * (.10 * relief_noise(key / 12.0, 11))
        else:
            rr *= 1 + .29 * relief_noise(key / 3.1, 3) + .13 * relief_noise(key / 1.3, 7)
            p = p + lateral * rr * (.27 * relief_noise(key / 3.7, 11) + .12 * relief_noise(key / 1.8, 21))
        frames_.append((p.copy(), lateral.copy(), rr))
        for k in range(sides):
            a, b = profile[k]
            relief = (b + .15) * (1 + (.06 if round_ else .16) * relief_noise(key / 2.7, k + 1))
            v.append(p + lateral * (rr * a) + Nn * (rr * relief))
        if i:
            for k in range(sides):
                f.append(((i - 1) * sides + k, i * sides + k, i * sides + (k + 1) % sides, (i - 1) * sides + (k + 1) % sides))
    f.extend([tuple(reversed(range(sides))), tuple((len(pp) - 1) * sides + k for k in range(sides))])
    sink.add(mat, v, f)
    if woody:
        for q in (-1, 1):
            groove = []
            for i, (p, lat, rr) in enumerate(frames_):
                x = q * .24 + .095 * relief_noise(p.z / 6.0, 19 + q)
                h = 0.3
                for k in range(6):
                    a, b = profile[k]
                    c, d = profile[k + 1]
                    if a <= x <= c:
                        ha = (b + .15) * (1 + .16 * relief_noise(p.z / 2.7, k + 1))
                        hb = (d + .15) * (1 + .16 * relief_noise(p.z / 2.7, k + 2))
                        h = ha + (hb - ha) * (x - a) / (c - a)
                        break
                groove.append(p + lat * rr * x + Nn * (rr * h - .015))
            for start in range(3 if q < 0 else 11, len(groove) - 4, 23):
                segment = groove[start:min(start + 8, len(groove))]
                rr = radii[0] * (1 - start / len(groove)) + radii[-1] * start / len(groove)
                tube(sink, segment, max(.05, rr * .06), RECESS, 4)
    return [fr[0] for fr in frames_]
