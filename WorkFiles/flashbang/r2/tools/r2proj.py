"""numpy replica of the gallery's reference-row camera (flashbang_look.row_camera / place_row)."""
import math, numpy as np
REF = 1254; F = 2600.0; HOR = 460.0; CD = 652.5
VIEW_X_PX = {"v1": 157.68, "v2": 467.01, "v3": 745.55, "v4": 1103.2}
YAWS = {"v1": -130.0, "v2": 170.0, "v3": -110.0, "v4": -25.0}
pitch = math.atan((REF / 2.0 - HOR) / F)
below = math.atan((717.0 - REF / 2.0) / F) + pitch
ZC = CD * math.tan(below)
CAM = np.array([0.0, -CD, ZC])
FW = np.array([0.0, math.cos(pitch), -math.sin(pitch)])
UP = np.array([0.0, math.sin(pitch), math.cos(pitch)])
RT = np.array([1.0, 0.0, 0.0])
def world(pts_local, view, yaw=None):
    yaw = YAWS[view] if yaw is None else yaw
    x = (VIEW_X_PX[view] - REF / 2.0) / F * CD
    cam_az = math.degrees(math.atan2(-CD, -x))
    rot = math.radians(cam_az - yaw)
    c, s = math.cos(rot), math.sin(rot)
    P = np.asarray(pts_local, float)
    return np.stack([c * P[:, 0] - s * P[:, 1] + x, s * P[:, 0] + c * P[:, 1], P[:, 2]], 1)
def project(pts_local, view, yaw=None):
    W = world(pts_local, view, yaw) - CAM
    z = W @ FW
    return np.stack([REF / 2.0 + F * (W @ RT) / z, REF / 2.0 - F * (W @ UP) / z], 1), z
