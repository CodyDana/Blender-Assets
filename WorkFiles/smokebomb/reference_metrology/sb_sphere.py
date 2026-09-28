"""Sphere back-projection + circle-on-sphere fitting (pure numpy; importable by Blender Python).
Camera frame: X right, Y up, Z toward the camera. Orthographic model (see spec for the perspective note)."""
import numpy as np

CX, CY, R = 627.378, 628.918, 464.107   # stage-1 circle fit at the half-max edge


def to_sphere(pts):
    p = np.asarray(pts, float)
    x = (p[:, 0] - CX) / R
    y = (CY - p[:, 1]) / R
    r2 = x * x + y * y
    s = np.where(r2 > 1, 1 / np.sqrt(r2), 1.0)
    x, y = x * s, y * s
    z = np.sqrt(np.clip(1 - x * x - y * y, 0, 1))
    return np.c_[x, y, z]


def to_image(n):
    n = np.asarray(n, float)
    return np.c_[CX + n[:, 0] * R, CY - n[:, 1] * R]


def fit_plane(P, great=False):
    """fit n.a = d to unit vectors P. returns a (unit), d, rms angular residual (rad)."""
    if great:
        u, s, vt = np.linalg.svd(P, full_matrices=False)
        a = vt[-1]; d = 0.0
    else:
        mu = P.mean(0)
        u, s, vt = np.linalg.svd(P - mu, full_matrices=False)
        a = vt[-1]; d = float(mu @ a)
    if d < 0 or (d == 0 and a[2] < 0):
        a, d = -a, -d
    res = np.arcsin(np.clip(P @ a, -1, 1)) - np.arcsin(np.clip(d, -1, 1))
    return a, d, float(np.sqrt(np.mean(res ** 2)))


def circle_points(a, d, n=720):
    a = np.asarray(a, float); a = a / np.linalg.norm(a)
    t = np.array([1.0, 0, 0]) if abs(a[0]) < 0.9 else np.array([0, 1.0, 0])
    e1 = np.cross(a, t); e1 /= np.linalg.norm(e1)
    e2 = np.cross(a, e1)
    rr = np.sqrt(max(0.0, 1 - d * d))
    ph = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return d * a[None, :] + rr * (np.cos(ph)[:, None] * e1[None, :] + np.sin(ph)[:, None] * e2[None, :])


def limb_crossings(a, d):
    """points where the circle n.a=d meets the limb z=0 -> image angles (deg, CCW from +x, y up)."""
    P = circle_points(a, d, 3600)
    z = P[:, 2]
    out = []
    for i in range(len(P)):
        j = (i + 1) % len(P)
        if (z[i] >= 0) != (z[j] >= 0):
            t = z[i] / (z[i] - z[j])
            q = P[i] + t * (P[j] - P[i])
            out.append(float(np.degrees(np.arctan2(q[1], q[0])) % 360))
    return out


def latlon(n, pole=(0, 1, 0), front=(0, 0, 1)):
    """latitude/longitude of unit vectors about a pole axis; longitude 0 toward 'front'."""
    n = np.asarray(n, float)
    p = np.asarray(pole, float); p /= np.linalg.norm(p)
    f = np.asarray(front, float); f = f - (f @ p) * p; f /= np.linalg.norm(f)
    g = np.cross(p, f)
    lat = np.degrees(np.arcsin(np.clip(n @ p, -1, 1)))
    lon = np.degrees(np.arctan2(n @ g, n @ f))
    return lat, lon
