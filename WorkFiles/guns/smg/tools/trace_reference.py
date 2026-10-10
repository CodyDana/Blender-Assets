"""Trace and measure the SMG01 (Compact SMG SM-01) reference sheet (References/Guns/SMG/smg_sheetA.webp).

    py -3 -B WorkFiles/guns/smg/tools/trace_reference.py

Adapted from the AR-01 tool (WorkFiles/guns/rifle/tools/trace_reference.py). Regenerates the 2D outline authority:
  WorkFiles/guns/smg/scratch/crops/*.png        the 4 panels at full resolution (not committed)
  WorkFiles/guns/smg/scratch/qa_zoom_*.png      4x QA tiles with the trace drawn on (not committed)
  WorkFiles/guns/smg/trace/*.png                binary masks (silhouettes, gun without magazine, magazine, LEFT parts)
  WorkFiles/guns/smg/trace/*.json               outlines (sub-pixel marching squares, simplified) in px and in mm
  WorkFiles/guns/smg/smg_measured.json          all numbers (scales, crop boxes, agreement, dimensions + uncertainty)
  WorkFiles/guns/smg/SMG_TRACE_OVERLAY.png      QA overlay (outlines on the reference crops)

Sheet layout (found by pixel analysis): LEFT side view (muzzle image-left), RIGHT side view (muzzle image-right), TOP
view (muzzle image-left, gun left = image-down), 3/4 FRONT VIEW (LEFT). Each side panel has a cm ruler (unreliable).

Frames
  Panel px: (x right, y down), pixel-centre coordinates inside each panel crop (boxes in smg_measured.json). RIGHT is
            mirrored before tracing (so it has the muzzle image-left like LEFT); RIGHT CONFIG coords are raw.
  Gun mm:   +X toward the muzzle, +Z up, +Y = the gun's LEFT side (right-handed, = GUN_BUILDING_STUDY 5.1).
            Origin X = 0 at the rearmost point of the butt pad (stock extended), Z = 0 on the bore axis, Y = 0 on the
            mid-plane. The bore axis: its direction is the top 1913 rail (tooth-top line, the longest straight edge on
            the gun); its height is the muzzle device / exposed barrel centre line.
  Each view gets its own frame (own axis, own X = 0, own scale so its overall length = OVERALL_MM, 625 mm since the 2026-10-09 ruling); views are compared
  in mm without fitting.

Only numpy, scipy and Pillow are needed. Hand inputs (seams that are not on the silhouette, the magazine cut, face
features, real see-through holes) are the CONFIG below, read off gridded 4-10x zooms (tools/gridzoom.py), +-1 px.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
from scipy.optimize import minimize

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import refimg as R  # noqa: E402

ROOT = HERE.parents[3]
SHEET = ROOT / "References" / "Guns" / "SMG" / "smg_sheetA.webp"
OUT = ROOT / "WorkFiles" / "guns" / "smg"
TRACE = OUT / "trace"
SCRATCH = OUT / "scratch"
CROPS = SCRATCH / "crops"

OVERALL_MM = 625.0          # overall length, stock extended (butt pad rear to muzzle device tip): orchestrator ruling
                            # 2026-10-09 (spec resolution R26): the sheet was drawn at ~625 (side rail pitch 10.01,
                            # receiver width = the real 61); it was 690 (the real pattern's length) before
SHEET_MM = 690.0            # the scale every mm window below was written at (measuring windows scale with the sheet)
SW = OVERALL_MM / SHEET_MM


def W(v):
    """A measuring window / step written in mm at the 690 scale, at the current scale (same panel px)."""
    return v * SW

FOLDED_MM_REAL = 450.0      # real pattern, stock folded
BARREL_MM_REAL = 200.0      # real pattern barrel
HEIGHT_MM_REAL = 280.0      # real pattern height (maker's table, 11.02 in), with the 25-round magazine
WIDTH_MM_REAL = 61.0        # real pattern width (maker's table, 2.40 in)
RAIL_PITCH = 10.01          # MIL-STD-1913 slot pitch
PANEL_NAMES = ["LEFT", "RIGHT", "TOP", "Q34_FRONT_LEFT"]


def circle(cx, cy, r, n=24):
    return [(cx + r * math.cos(t), cy + r * math.sin(t)) for t in np.linspace(0, 2 * math.pi, n, endpoint=False)]


# ------------------------------------------------------------------------------------------------ CONFIG
# Coordinates: panel-crop px (pixel centres). RIGHT: raw (un-mirrored) crop px.
CONFIG = {
    "LEFT": {
        "exclude_below_y": 440,                 # the cm ruler starts at y ~480
        # real see-through holes: trigger guard opening, stock front (triangular) window, stock rear window,
        # the gap between the receiver's hinge block and the stock knuckle (checked on 7x zooms)
        "keep_hole_seeds": [(255, 262), (450, 205), (528, 215), (370.5, 195)],
        "fill_hole_seeds": [],
        "force_fg": [],
        "strict": [],
        "rail_probe_x": [124, 300],             # top-rail teeth between the sights
        "bore_probe_x": [[17, 44], [54, 59]],   # muzzle device body and the exposed barrel neck
        "bore_probe_y": 193.0,
        # magazine cut: the dark lower edge of the magwell lip (172,258)-(214,266); the rear boundary stays in front
        # of the trigger guard's front leg (x 218+)
        "mag_region": [(140, 258.5), (170, 258.5), (213.5, 266.5), (213.5, 440), (140, 440)],
        # part regions, first match wins (magazine already cut). Seams read off 6-10x zooms:
        #   muzzle device / barrel neck at x 53.5 (rear collar of the device), barrel / receiver front face x 72.5,
        #   rail underside y 161.5, lower rail top y 221.5, upper/lower receiver seam y 211 (x >= 219) with the lower's
        #   front tab (top y 206.5, x 191-217) and its front edge diagonal (191,206.5)-(172,231), receiver rear end
        #   x 352.5, hinge block / stock knuckle gap x 369.5, stock knuckle / stock neck x 393, butt pad seam x 575.5
        "regions": [
            ("muzzle_device", [(0, 150), (53.5, 150), (53.5, 240), (0, 240)]),
            ("barrel", [(53.5, 150), (72.5, 150), (72.5, 240), (53.5, 240)]),
            ("sight_front", [(72.5, 100), (101, 100), (101, 157.5), (72.5, 157.5)]),
            ("sight_rear", [(305, 100), (341, 100), (341, 157.5), (305, 157.5)]),
            ("top_rail", [(72.5, 100), (352.5, 100), (352.5, 161.5), (72.5, 161.5)]),
            ("lower_rail", [(72.5, 221.5), (146, 221.5), (146, 240), (72.5, 240)]),
            ("hinge_block", [(352.5, 100), (369.5, 100), (369.5, 240), (352.5, 240)]),
            ("stock_hinge_knuckle", [(369.5, 100), (393, 100), (393, 240), (369.5, 240)]),
            ("butt_pad", [(575.5, 100), (640, 100), (640, 300), (575.5, 300)]),
            # trigger blade inside the guard opening (before the guard)
            ("trigger", [(238, 241.5), (263, 241.5), (263, 275.5), (238, 275.5)]),
            # mag release paddle (check fix C1, 2026-10-09): the lever DRAWN inside the guard's front leg (rounded
            # outline x 217.3-225.5, y 245.5-267.5, pin head at (222, 249.5)); the old box x 209-219 was the magwell's
            # rear corner (the lip-band lines run through it) and is now part of mag_well
            ("mag_release", [(217.3, 245.5), (225.0, 245.5), (225.5, 247.0), (225.5, 266.0), (224.0, 267.5),
                             (219.5, 267.5), (217.5, 264.5)]),
            # trigger guard incl. its front leg from the lever's front edge (x 217.3) back; the strip x 215-217 ahead
            # of the lever lies where the built magwell rear wall stands, so it stays mag_well
            ("trigger_guard", [(219, 241.5), (282, 241.5), (297, 290), (296, 300), (217.3, 300), (217.3, 243)]),
            # pistol grip incl. its rear tang that curves up into the receiver seam
            ("grip", [(281, 243), (298, 241), (330, 236), (346, 226), (355, 211.5), (380, 211.5), (380, 380),
                      (281, 380)]),
            # magwell housing = the front of the lower: its sloped front band under the seam (147,205.5)-(172,231),
            # the front tab (191-217, top y 206.5) and the walls down to the lip; rear boundary the vertical line x 219
            ("mag_well", [(147, 205.5), (172, 231), (191, 206.5), (217, 206.5), (219, 211), (219, 241.5), (217.3, 243),
                          (217.3, 271), (141, 271), (141, 228)]),
            ("receiver_lower", [(219, 211), (352.5, 211), (352.5, 300), (219, 300)]),
            # the slotted front of the upper (no seam on the sheet: zone ends at the start of the V seam, x 147)
            ("handguard_area", [(72.5, 100), (147, 100), (147, 205.5), (141, 228), (72.5, 228)]),
            ("receiver_upper", [(72.5, 100), (352.5, 100), (352.5, 211), (219, 211), (217, 206.5), (191, 206.5),
                                (172, 231), (147, 205.5)]),
        ],
        # stock frame (x 393-575.5) is split automatically from the two windows (see stock_parts())
        "stock_x": [393.0, 575.5],
        # face features (drawn on the side face, not on the silhouette): outline polygons, panel px
        "face_features": {
            "charging_handle_knob": circle(135.0, 174.7, 5.5),
            "charging_handle_rod": [(140.5, 173.6), (163.7, 173.6), (163.7, 176.3), (140.5, 176.3)],
            "charging_handle_rear_block": [(163.7, 173.6), (173.7, 173.6), (173.7, 180.0), (163.7, 180.0)],
            "front_upper_slot": [(90.6, 169.4), (125.6, 169.4), (125.6, 175.6), (90.6, 175.6)],
            "selector_pivot_ring": circle(292.5, 219.5, 8.8),
            "selector_lever": [(290.0, 212.0), (295.0, 212.0), (300.5, 236.0), (297.5, 238.5), (293.5, 236.5),
                               (289.5, 221.0)],
            "pin_front_takedown": circle(167.0, 215.5, 3.3),
            # check fix C7 (2026-10-09): the ring head is centred at (225.5, 228.5), not (233, 229.5) (plain wall)
            "pin_lower_rear_of_magwell": circle(225.5, 228.5, 3.3),
            "pin_hinge_block": circle(361.0, 208.5, 2.8),
            # check fix C7: every other drawn head, recess and boss on the LEFT face (10x zooms, +-0.5 px)
            "head_above_rear_pin": circle(227.0, 217.0, 1.5),
            "recess_oblong": [(249.5, 215.0), (256.5, 215.0), (258.0, 216.7), (256.5, 218.4), (249.5, 218.4),
                              (248.0, 216.7)],
            "trigger_axle_head": circle(259.5, 229.5, 2.2),
            "seam_boss_ring": circle(301.5, 209.5, 7.0),
            "seam_boss_pin": circle(303.0, 207.0, 1.3),
            "head_end_block": circle(347.0, 206.5, 1.7),
            "mag_release_pin_head": circle(222.0, 249.5, 1.3),
        },
        "selector_pivot": (292.5, 219.5),
        "charging_knob_centre": (135.0, 174.7),
    },
    "RIGHT": {
        "exclude_below_y": 440,
        "keep_hole_seeds": [(361, 262), (167, 205), (88, 215), (246.5, 195)],
        "fill_hole_seeds": [],
        "force_fg": [],
        "strict": [],
        "rail_probe_x": [320, 495],
        "bore_probe_x": [[573, 600], [558, 563]],
        "bore_probe_y": 193.0,
        "mag_region": [(396, 265.5), (452, 259.5), (480, 259.5), (480, 440), (396, 440)],
        "face_features": {
            "ejection_port": [(397.0, 174.0), (451.0, 174.0), (451.0, 194.0), (397.0, 194.0)],
            "boss_front_of_port": [(450.0, 174.0), (464.0, 174.0), (464.0, 210.0), (450.0, 210.0)],
            "selector_pivot_ring": circle(328.5, 219.0, 8.8),
            "selector_lever": [(326.0, 212.0), (331.0, 213.0), (321.0, 236.5), (316.0, 236.0), (318.0, 230.0)],
            # check fix C7 (2026-10-09): the RIGHT face's own fasteners, raw (un-mirrored) panel px = 617 - mirrored x
            "pin_lower_rear_of_magwell": circle(391.0, 227.9, 3.3),
            "head_above_rear_pin": circle(390.6, 216.9, 1.5),
            "trigger_axle_head": circle(359.0, 229.75, 2.2),
            "seam_head_upper": circle(313.75, 206.9, 1.5),
            "seam_head_lower": circle(314.1, 212.25, 1.5),
            "head_behind_selector": circle(305.4, 223.75, 1.5),
            "head_end_block": circle(270.0, 206.9, 1.7),
            "locking_pin_end": [(252.4, 206.75), (256.4, 206.75), (256.4, 210.75), (252.4, 210.75)],
        },
        "selector_pivot": (328.5, 219.0),
    },
    "TOP": {
        "exclude_below_y": None,
        "keep_hole_seeds": [],
        "fill_hole_seeds": [],
        "force_fg": [],
        "strict": [],
        "bore_probe_x": [[18, 44], [54, 58]],
        "body_probe_x": [190, 290],             # plain receiver sides (no lateral features)
        "charging_knob_x": [133.75, 150.0],      # knob protruding at image-down = gun LEFT (read off a 4x zoom)
    },
    # 3/4 view reads (panel px, 6x zooms): front-face widths of the magwell lip and of the magazine at the same depth
    "Q34": {
        "magwell_lip_front_face_px": [191.0, 222.0],
        "magazine_front_face_px_at_y300": [200.0, 219.5],
        "magazine_side_face_px_at_y300": [219.5, 259.0],
        # muzzle device end face (a circle seen at the view's yaw): ellipse width / height = sin(yaw)
        "device_end_face_ellipse_px": {"x": [26.0, 47.0], "y": [183.5, 218.5]},
        "note": "both front faces have the same orientation and nearly the same depth, so their width ratio does not "
                "depend on the view angle or scale",
    },
}

PART_COLS = {"muzzle_device": (0, 255, 255), "barrel": (120, 180, 255), "sight_front": (160, 255, 60),
             "sight_rear": (160, 255, 60), "top_rail": (255, 210, 0), "lower_rail": (255, 210, 0),
             "handguard_area": (0, 190, 255), "receiver_upper": (0, 255, 0), "receiver_lower": (255, 140, 0),
             "mag_well": (255, 80, 80), "magazine": (255, 255, 0), "mag_release": (0, 255, 255),
             "trigger_guard": (255, 80, 80), "trigger": (0, 255, 255), "grip": (255, 140, 0),
             "hinge_block": (0, 190, 255), "stock_hinge_knuckle": (255, 0, 255), "stock_neck": (160, 255, 60),
             "stock_top_strut": (0, 255, 160), "stock_lower_strut": (255, 210, 0), "stock_web": (255, 80, 80),
             "stock_rear_upright": (0, 190, 255), "butt_pad": (0, 255, 255), "unassigned": (255, 0, 0)}


# ------------------------------------------------------------------------------------------------ helpers
def load_sheet():
    return np.asarray(Image.open(SHEET).convert("RGB"))


def rings_out(rings, tol=0.25, min_area=2.0):
    return [R.dp_simplify(r, tol) for r in rings if abs(R.signed_area(r)) >= min_area]


def ring_json(r, to_mm=None):
    d = {"area_px": round(R.signed_area(r), 2), "kind": "outer" if R.signed_area(r) > 0 else "hole",
         "px": [[round(float(x), 3), round(float(y), 3)] for x, y in r]}
    if to_mm is not None:
        d["mm"] = [[round(float(a), 3), round(float(b), 3)] for a, b in (to_mm(x, y) for x, y in r)]
    return d


def save_mask(m, name):
    Image.fromarray((m * 255).astype(np.uint8)).save(TRACE / name)


class View:
    """One orthographic panel: soft field, silhouette mask, sub-pixel rings (from the AR-01 tool)."""

    def __init__(self, name, rgb, box, cfg, mirror=False):
        self.name, self.box, self.cfg, self.mirror = name, box, cfg, mirror
        x0, y0, x1, y1 = box
        P = rgb[y0:y1 + 1, x0:x1 + 1].astype(float)
        if mirror:
            P = P[:, ::-1]
        self.rgb = P
        self.H, self.W = P.shape[:2]
        L = P.mean(axis=2)
        S = P.max(axis=2) - P.min(axis=2)
        self.L, self.S = L, S
        ex = np.zeros_like(L, bool)
        if cfg.get("exclude_below_y") is not None:
            ex[int(cfg["exclude_below_y"]):] = True
        self.exclude = ex
        bg, sd = R.fit_background(L, S, exclude=ex)
        self.bg, self.bg_sd = bg, sd
        F = R.soft_field(L, S, bg, dl=cfg.get("dl", 40.0))
        F[ex] = 0.0
        F[:3, :] = F[-3:, :] = 0.0
        F[:, :3] = F[:, -3:] = 0.0
        fg = [self.poly(Pp) for Pp in cfg.get("force_fg", [])]
        if fg:
            F = np.maximum(F, R.poly_coverage(fg, F.shape))
        for Pp, dl in cfg.get("strict", []):
            cov = R.poly_coverage([self.poly(Pp)], F.shape)
            F = F * (1 - cov) + R.soft_field(L, S, bg, dl=dl) * cov
        m0 = F > 0.5
        m = R.drop_small(m0, 30)
        F[m0 & ~m] = np.minimum(F[m0 & ~m], 0.49)
        seeds = [self.px(sx, sy) for sx, sy in cfg.get("keep_hole_seeds", [])]
        Ld = L - bg
        kept, keptmask, filled = [], np.zeros_like(m), 0

        def classify(h):
            area = int(h.sum())
            hi = ndi.binary_erosion(h)
            r = Ld[hi] if hi.sum() > 2 else Ld[h]
            seeded = area >= 4 and any(h[max(0, int(round(sy)) - 3):int(round(sy)) + 4,
                                       max(0, int(round(sx)) - 3):int(round(sx)) + 4].any() for sx, sy in seeds)
            return seeded, area, r

        for pass_ in (1, 2):
            if pass_ == 1:
                base, bridge = m, np.zeros_like(m)
            else:
                base = (m | ndi.binary_closing(m, structure=np.ones((3, 3), bool), border_value=0)
                        | ndi.binary_closing(m, structure=np.ones((7, 1), bool), border_value=0))
                bridge = base & ~m & ~keptmask
            lab, n = R.holes_of(base)
            for k in range(1, n + 1):
                h = lab == k
                if (h & keptmask).any():
                    continue
                seeded, area, r = classify(h)
                if seeded:
                    ys, xs = np.nonzero(h)
                    kept.append({"area_px": area, "bbox_px": [int(xs.min()), int(ys.min()), int(xs.max()),
                                                              int(ys.max())],
                                 "by": "seed", "median_dL": round(float(np.median(r)), 1)})
                    keptmask |= h
                else:
                    hb = h | (ndi.binary_dilation(h, iterations=2) & bridge)
                    F[hb] = 1.0
                    m |= hb
                    filled += 1
        lab, n = R.holes_of(m)
        for k in range(1, n + 1):
            h = lab == k
            if not (h & keptmask).any():
                F[h] = 1.0
                m |= h
                filled += 1
        self.F, self.mask = F, m
        self.kept_holes, self.filled_holes = kept, filled
        self.keptmask = keptmask
        self.rings = rings_out(R.marching_squares(F))
        self.sil = R.rings_to_mask(self.rings, F.shape)

    def px(self, x, y):
        """CONFIG coords (panel crop px, un-mirrored) -> this view's working coords (mirrored if needed)."""
        return ((self.W - 1 - x) if self.mirror else x, y)

    def poly(self, P):
        return [self.px(x, y) for x, y in P]


MIN_PIECE_PX = 25
MIN_HOLE_PX = 12


def part_rings(F, labels, k, sigma=0.6):
    cov = ndi.gaussian_filter((labels == k).astype(float), sigma)
    rr = rings_out(R.marching_squares(np.minimum(F, cov)))
    outers = [r for r in rr if R.signed_area(r) > 0]
    if not outers:
        return rr
    amax = max(R.signed_area(r) for r in outers)
    return [r for r in rr if (R.signed_area(r) > 0 and (R.signed_area(r) >= MIN_PIECE_PX or R.signed_area(r) == amax))
            or (R.signed_area(r) < 0 and -R.signed_area(r) >= MIN_HOLE_PX)]


def extend_labels(lab):
    idx = ndi.distance_transform_edt(lab == 0, return_distances=False, return_indices=True)
    return lab[idx[0], idx[1]]


# ------------------------------------------------------------------------------------------------ ring geometry
def hits_v(rings, x):
    out = []
    for r in rings:
        a, b = r, np.roll(r, -1, axis=0)
        m = ((a[:, 0] <= x) & (b[:, 0] > x)) | ((b[:, 0] <= x) & (a[:, 0] > x))
        if m.any():
            t = (x - a[m, 0]) / (b[m, 0] - a[m, 0])
            out.extend(a[m, 1] + t * (b[m, 1] - a[m, 1]))
    return np.sort(np.array(out))


def hits_h(rings, y):
    out = []
    for r in rings:
        a, b = r, np.roll(r, -1, axis=0)
        m = ((a[:, 1] <= y) & (b[:, 1] > y)) | ((b[:, 1] <= y) & (a[:, 1] > y))
        if m.any():
            t = (y - a[m, 1]) / (b[m, 1] - a[m, 1])
            out.extend(a[m, 0] + t * (b[m, 0] - a[m, 0]))
    return np.sort(np.array(out))


def span(hits, ref):
    for i in range(0, len(hits) - 1, 2):
        if hits[i] <= ref <= hits[i + 1]:
            return float(hits[i]), float(hits[i + 1])
    return None


def intervals(hits):
    return [(float(hits[i]), float(hits[i + 1])) for i in range(0, len(hits) - 1, 2)]


def outer(rings):
    return [r for r in rings if R.signed_area(r) > 0]


def bbox(rings):
    P = np.vstack(outer(rings))
    return float(P[:, 0].min()), float(P[:, 0].max()), float(P[:, 1].min()), float(P[:, 1].max())


class Frame:
    """Panel px <-> gun mm for one view. u = unit bore direction toward the muzzle (image coords); n = the
    perpendicular that points image-up (side views: +Z) or image-down (TOP: +Y = gun left)."""

    def __init__(self, s, u, p0, second="up"):
        self.s = float(s)
        self.u = np.array(u, float) / np.hypot(*u)
        n = np.array([self.u[1], -self.u[0]])
        if (second == "up" and n[1] > 0) or (second == "down" and n[1] < 0):
            n = -n
        self.n = n
        self.p0 = np.array(p0, float)
        self.bore = None

    def mm(self, x, y):
        d = np.array([x, y], float) - self.p0
        return float(d @ self.u / self.s), float(d @ self.n / self.s)

    def mm_arr(self, P):
        d = np.asarray(P, float) - self.p0
        return np.c_[d @ self.u, d @ self.n] / self.s

    def px(self, X, Z):
        return self.p0 + self.s * (X * self.u + Z * self.n)

    def px_arr(self, Q):
        Q = np.asarray(Q, float)
        return self.p0 + self.s * (Q[:, :1] * self.u + Q[:, 1:2] * self.n)


EDGE_PX = {"sil": 0.4, "seam": 1.0, "est": 2.0}


def M(value_mm, s, edges=("sil", "sil"), px=None, how="", extra_unc=0.0, dec=1):
    e = math.sqrt(sum(EDGE_PX[k] ** 2 for k in edges)) / s if edges else 0.0
    unc = math.sqrt(e ** 2 + extra_unc ** 2)
    d = {"mm": round(float(value_mm), dec), "unc_mm": round(unc, 1)}
    if px is not None:
        d["px"] = round(float(px), 2)
    if how:
        d["how"] = how
    return d


def r1(v):
    return [round(float(a), 1) for a in v]


def part_box_mm(fr, rings):
    P = fr.mm_arr(np.vstack(outer(rings)))
    return float(P[:, 0].min()), float(P[:, 0].max()), float(P[:, 1].min()), float(P[:, 1].max())


def col_span_mm(fr, rings, X, Zref):
    p = fr.px(X, Zref)
    sp = span(hits_v(rings, p[0]), p[1])
    if sp is None:
        return None
    a, b = fr.mm(p[0], sp[0])[1], fr.mm(p[0], sp[1])[1]
    return min(a, b), max(a, b)


def col_extent(fr, rings, X):
    p = fr.px(X, 0.0)
    h = hits_v(rings, p[0])
    if len(h) < 2:
        return None
    a, b = fr.mm(p[0], h[0])[1], fr.mm(p[0], h[-1])[1]
    return min(a, b), max(a, b)


def col_intervals_mm(fr, rings, X):
    p = fr.px(X, 0.0)
    out = []
    for a, b in intervals(hits_v(rings, p[0])):
        za, zb = fr.mm(p[0], a)[1], fr.mm(p[0], b)[1]
        out.append((min(za, zb), max(za, zb)))
    return sorted(out, key=lambda t: -t[1])          # top first


def row_span_mm(fr, rings, Z, Xref):
    p = fr.px(Xref, Z)
    sp = span(hits_h(rings, p[1]), p[0])
    if sp is None:
        return None
    a, b = fr.mm(sp[0], p[1])[0], fr.mm(sp[1], p[1])[0]
    return min(a, b), max(a, b)


def row_intervals_mm(fr, rings, Z):
    p = fr.px(0.0, Z)
    out = []
    for a, b in intervals(hits_h(rings, p[1])):
        xa, xb = fr.mm(a, p[1])[0], fr.mm(b, p[1])[0]
        out.append((min(xa, xb), max(xa, xb)))
    return sorted(out)


# ------------------------------------------------------------------------------------------------ side frames
def side_frame(view):
    """Axis direction from the top rail's tooth tops; bore height from the muzzle device / barrel centre line;
    X = 0 at the rearmost point; scale so the overall length is OVERALL_MM."""
    cfg = view.cfg
    # (1) rail tooth tops: top crossing per column; tooth tops = minimum y in each 12 px window
    lo, hi = sorted((view.px(cfg["rail_probe_x"][0], 0)[0], view.px(cfg["rail_probe_x"][1], 0)[0]))
    cols, tops = [], []
    for x in np.arange(lo, hi + 0.01, 0.5):
        h = hits_v(view.rings, x)
        if len(h):
            cols.append(x)
            tops.append(h[0])
    cols, tops = np.array(cols), np.array(tops)
    bx, by = [], []
    for x0 in np.arange(lo, hi - 12, 12.0):
        sel = (cols >= x0) & (cols < x0 + 12)
        if sel.sum() > 4:
            k = np.argmin(tops[sel])
            bx.append(cols[sel][k])
            by.append(tops[sel][k])
    a_r, b_r, rms_r = R.fit_line(np.array(bx), np.array(by))
    # (2) bore: centre of the muzzle device / barrel spans
    xs, mids, dia = [], [], []
    for xa, xb in cfg["bore_probe_x"]:
        lo2, hi2 = sorted((view.px(xa, 0)[0], view.px(xb, 0)[0]))
        for x in np.arange(lo2, hi2 + 0.01, 1.0):
            sp = span(hits_v(view.rings, x), cfg["bore_probe_y"])
            if sp:
                xs.append(x)
                mids.append((sp[0] + sp[1]) / 2)
                dia.append(sp[1] - sp[0])
    xs, mids = np.array(xs), np.array(mids)
    a_b, b_b, rms_b = R.fit_line(xs, mids)
    xm = float(xs.mean())
    p_on = np.array([xm, float(np.mean(mids - a_r * (xs - xm)))])   # bore height at xm with the rail's slope
    u = np.array([-1.0, -a_r])                                      # muzzle is image-left in LEFT and mirrored RIGHT
    u /= np.hypot(*u)
    allp = np.vstack(outer(view.rings))
    t = allp @ u
    L_px = float(t.max() - t.min())
    p0 = p_on + (t.min() - p_on @ u) * u
    fr = Frame(L_px / OVERALL_MM, u, p0, "up")
    fr.bore = {"rail_tooth_top_slope": a_r, "rail_slope_deg": math.degrees(math.atan(a_r)),
               "rail_tooth_top_fit_rms_px": rms_r, "rail_teeth_used": len(bx),
               "muzzle_centre_slope_deg": math.degrees(math.atan(a_b)), "muzzle_centre_fit_rms_px": rms_b,
               "muzzle_vs_rail_deg": math.degrees(math.atan(a_b) - math.atan(a_r)),
               "bore_point_px": [round(float(p_on[0]), 3), round(float(p_on[1]), 3)],
               "muzzle_device_dia_px_median": float(np.median(dia)), "n_columns": int(len(xs))}
    cz = {}
    for nm, (xa, xb) in zip(("device_body", "barrel_neck"), cfg["bore_probe_x"]):
        sel = (xs >= min(view.px(xa, 0)[0], view.px(xb, 0)[0]) - 0.1) & (xs <= max(view.px(xa, 0)[0],
                                                                                    view.px(xb, 0)[0]) + 0.1)
        cz[nm + "_centre_Z_mm"] = round(float(np.mean([fr.mm(x, y)[1] for x, y in zip(xs[sel], mids[sel])])), 2)
    fr.bore.update(cz)
    return fr, L_px


# ------------------------------------------------------------------------------------------------ parts (LEFT)
def mag_mask(view):
    cov = R.poly_coverage([view.poly(view.cfg["mag_region"])], view.sil.shape) > 0.5
    return R.drop_small(view.sil & cov, 30)


def stock_parts(view, lab, add):
    """Split the skeleton stock (x in stock_x) into neck, top strut, lower strut, web, rear upright using the two
    windows: the top strut's lower edge = line through the window tops, the lower strut's upper edge = line through
    the window bottoms; neck = in front of the front window, web = between the windows, upright = behind the rear one."""
    sx0, sx1 = view.cfg["stock_x"]
    H, W = view.sil.shape
    wins = []
    for h in view.kept_holes:
        x0, y0, x1, y1 = h["bbox_px"]
        if x0 > sx0 and x1 < sx1 and (x1 - x0) > 15:
            wins.append(h)
    wins.sort(key=lambda h: h["bbox_px"][0])
    assert len(wins) == 2, wins
    hl, _ = R.holes_of(view.sil)
    tops_x, tops_y, bots_x, bots_y = [], [], [], []
    winmasks = []
    for h in wins:
        x0, y0, x1, y1 = h["bbox_px"]
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        k = hl[cy, cx]
        wm = hl == k
        winmasks.append(wm)
        ys, xs = np.nonzero(wm)
        for x in range(xs.min() + 3, xs.max() - 2):
            col = ys[xs == x]
            if len(col):
                tops_x.append(x)
                tops_y.append(col.min() - 0.5)
                bots_x.append(x)
                bots_y.append(col.max() + 0.5)
    at, bt, rt = R.fit_line(np.array(tops_x, float), np.array(tops_y, float))
    ab, bb, rb = R.fit_line(np.array(bots_x, float), np.array(bots_y, float))
    yy, xx = np.mgrid[0:H, 0:W]
    zone = view.sil & (xx >= sx0) & (xx < sx1) & (lab == 0)
    topline = at * xx + bt
    botline = ab * xx + bb
    wx = [(np.nonzero(w)[1].min(), np.nonzero(w)[1].max()) for w in winmasks]
    add("stock_top_strut", zone & (yy < topline) & (xx >= wx[0][0]))
    add("stock_lower_strut", zone & (yy > botline) & (xx >= wx[0][0]))
    add("stock_neck", zone & (xx < wx[0][0]))
    mid = zone & (yy >= topline) & (yy <= botline)
    add("stock_web", mid & (xx > wx[0][1]) & (xx < wx[1][0]))
    add("stock_rear_upright", mid & (xx >= wx[1][1]))
    add("stock_top_strut", zone & (yy < topline))
    add("stock_lower_strut", zone)
    return {"window_top_line": {"slope": at, "intercept": bt, "rms_px": rt},
            "window_bottom_line": {"slope": ab, "intercept": bb, "rms_px": rb},
            "windows_px_x": [[int(a), int(b)] for a, b in wx]}


def label_parts(view, mag):
    cfg = view.cfg
    sil = view.sil
    names = ["background"]
    lab = np.zeros(sil.shape, np.int32)

    def add(name, m):
        if name in names:
            k = names.index(name)
        else:
            names.append(name)
            k = len(names) - 1
        lab[m & (lab == 0)] = k

    add("magazine", mag)
    pre = [r for r in cfg["regions"] if r[0] in ("muzzle_device", "barrel", "sight_front", "sight_rear", "top_rail",
                                                    "lower_rail", "hinge_block", "stock_hinge_knuckle", "butt_pad")]
    for nm, P in pre:
        add(nm, sil & (R.poly_coverage([view.poly(P)], sil.shape) > 0.5))
    stock_info = stock_parts(view, lab, add)
    for nm, P in cfg["regions"]:
        if (nm, P) in pre:
            continue
        add(nm, sil & (R.poly_coverage([view.poly(P)], sil.shape) > 0.5))
    rest = sil & (lab == 0)
    if rest.any():
        dist, idx = ndi.distance_transform_edt(lab == 0, return_indices=True)
        near = lab[idx[0], idx[1]]
        take = rest & (dist <= 3.0)
        lab[take] = near[take]
    st8 = np.ones((3, 3), bool)
    kmag = names.index("magazine")
    for k in range(1, len(names)):
        if k == kmag:
            continue
        cl, cn = ndi.label(lab == k, structure=st8)
        if cn < 2:
            continue
        sizes = np.bincount(cl.ravel())[1:]
        big = int(np.argmax(sizes)) + 1
        for i, sz in enumerate(sizes, 1):
            if i == big or sz >= MIN_PIECE_PX:
                continue
            comp = cl == i
            other = (lab > 0) & (lab != k) & (lab != kmag)
            _, idx = ndi.distance_transform_edt(~other, return_indices=True)
            near = lab[idx[0], idx[1]]
            lab[comp] = near[comp]
    add("unassigned", sil & (lab == 0))
    return lab, names, stock_info


def analyse_side(view, with_parts):
    mag = mag_mask(view)
    out = {"sil": view.rings, "mag_mask": mag}
    if with_parts:
        lab, names, stock_info = label_parts(view, mag)
        ext = extend_labels(lab)
        parts = {}
        for k, nm in enumerate(names):
            if k and (lab == k).any() and nm != "unassigned":
                parts[nm] = part_rings(view.F, ext, k)
        out.update(lab=lab, names=names, parts=parts, stock_info=stock_info)
        magk = names.index("magazine")
        cov = ndi.gaussian_filter((ext != magk).astype(float), 0.6)
        out["mag"] = parts["magazine"]
    else:
        lab = np.where(mag, 1, np.where(view.sil, 2, 0))
        ext = extend_labels(lab)
        out["mag"] = part_rings(view.F, ext, 1)
        cov = ndi.gaussian_filter((ext != 1).astype(float), 0.6)
    out["gun"] = rings_out(R.marching_squares(np.minimum(view.F, cov)))
    return out


# ------------------------------------------------------------------------------------------------ periodic features
def pitch_from_profile(x, z, pmin, pmax):
    """Dominant period (px) of a sampled profile z(x) between pmin and pmax by autocorrelation + parabolic peak."""
    z = np.asarray(z, float) - np.mean(z)
    dx = float(np.median(np.diff(x)))
    n = len(z)
    ac = np.correlate(z, z, "full")[n - 1:]
    ac /= ac[0]
    lags = np.arange(n) * dx
    sel = (lags >= pmin) & (lags <= pmax)
    i = int(np.nonzero(sel)[0][np.argmax(ac[sel])])
    if 0 < i < n - 1:
        y0, y1, y2 = ac[i - 1], ac[i], ac[i + 1]
        d = 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2) if (y0 - 2 * y1 + y2) != 0 else 0.0
    else:
        d = 0.0
    return (i + d) * dx, float(ac[i])


def teeth_runs(x, z, thr):
    """Runs of z above thr (teeth) -> list of (x_start, x_end)."""
    up = z > thr
    runs, s = [], None
    for i, f in enumerate(up):
        if f and s is None:
            s = i
        elif not f and s is not None:
            runs.append((x[s], x[i - 1]))
            s = None
    if s is not None:
        runs.append((x[s], x[-1]))
    return runs


# ------------------------------------------------------------------------------------------------ LEFT measurements
def measure_left(view, A, fr):
    s = fr.s
    P = A["parts"]
    cfg = view.cfg
    bx = {k: part_box_mm(fr, v) for k, v in P.items() if outer(v)}
    sil, gun = A["sil"], A["gun"]
    X0, X1, Z0, Z1 = part_box_mm(fr, sil)
    gX0, gX1, gZ0, gZ1 = part_box_mm(fr, gun)
    out = {"part_boxes_mm_X0_X1_Z0_Z1": {k: r1(v) for k, v in bx.items()}}
    out["overall"] = {
        "length_stock_extended": M(X1 - X0, s, how="butt pad rearmost point to muzzle device tip along the bore "
                                                    "(set = %.0f)" % OVERALL_MM),
        "height_with_magazine": M(Z1 - Z0, s, how="sight top to magazine floor plate bottom"),
        "height_without_magazine": M(gZ1 - gZ0, s, how="sight top to grip bottom"),
        "top_Z": M(Z1, s, ("sil",)), "bottom_Z_with_mag": M(Z0, s, ("sil",)), "bottom_Z_without_mag": M(gZ0, s, ("sil",)),
    }
    # ---------------- muzzle device, barrel
    md, br = bx["muzzle_device"], bx["barrel"]
    dd = [sp[1] - sp[0] for X in np.arange(md[0] + W(4), md[1] - W(4), W(0.5)) if (sp := col_span_mm(fr, sil, X, 0.0))]
    nk = [sp[1] - sp[0] for X in np.arange(br[1] - W(5.0), br[1] - W(1.0), W(0.25)) if (sp := col_span_mm(fr, sil, X, 0.0))]
    cl = [sp[1] - sp[0] for X in np.arange(br[0] + W(1.5), br[0] + W(12), W(0.5)) if (sp := col_span_mm(fr, sil, X, 0.0))]
    out["muzzle_device"] = {
        "X": r1(md[:2]), "length": M(md[1] - md[0], s, ("sil", "seam"), how="tip to the rear of its collar (seam x 53.5)"),
        "diameter": M(np.median(dd), s, how="median outer diameter over the slotted body"),
        "max_diameter": M(max(dd), s), "Z": r1(md[2:]),
        "note": "slotted cylindrical flash hider (birdcage-like, 3+ long slots visible) with a rear collar",
    }
    out["barrel"] = {
        "exposed_X": r1(br[:2]), "exposed_length": M(br[1] - br[0], s, ("seam", "seam"),
                                                    how="device collar to receiver front face"),
        "neck_diameter": M(np.median(nk), s, how="exposed barrel neck just behind the device"),
        "front_collar_diameter": M(np.median(cl), s, how="the ring / barrel nut against the receiver front face"),
        "muzzle_tip_X": M(X1, s, ("sil",)),
        "device_seat_X": M(md[0], s, ("seam",), how="rear of the device collar = MuzzleSeat"),
        "receiver_front_face_X": M(br[0], s, ("seam",)),
    }
    # ---------------- rails
    rails = {}
    rt = bx["top_rail"]
    xs = np.arange(rt[0] + W(0.5), rt[1] - W(0.5), W(0.25))
    tz = []
    for X in xs:
        e = col_extent(fr, P["top_rail"], X)
        tz.append(e[1] if e else np.nan)
    tz = np.array(tz)
    ok = ~np.isnan(tz)
    tooth_top = float(np.percentile(tz[ok], 90))
    slot_bot = float(np.percentile(tz[ok], 8))
    runs = [r for r in teeth_runs(xs[ok], tz[ok], (tooth_top + slot_bot) / 2) if r[1] - r[0] > W(1.0)]
    # periodic section between the sights
    secX0 = bx["sight_rear"][1] + W(2)         # X grows toward the muzzle: rear sight first
    secX1 = bx["sight_front"][0] - W(2)
    sel = ok & (xs < secX1) & (xs > secX0)
    p_mm, q = pitch_from_profile(xs[sel], tz[sel], W(6), W(16))
    teeth_between = [r for r in runs if r[0] > secX0 and r[1] < secX1]
    centres = np.array([(a + b) / 2 for a, b in teeth_between])
    if len(centres) > 3:
        k_, c_, rms_c = R.fit_line(np.arange(len(centres), dtype=float), centres)
    else:
        k_, rms_c = p_mm, 0.0
    rails["top"] = {
        "X": r1(rt[:2]), "length": M(rt[1] - rt[0], s, ("seam", "seam")),
        "tooth_top_Z": M(tooth_top, s, ("sil",)), "slot_bottom_Z": M(slot_bot, s, ("sil",)),
        "slot_depth_side_view": M(tooth_top - slot_bot, s, how="silhouette, teeth vs slots (real 3.0)"),
        "underside_Z_seam": M(fr.mm(*view.px(200, 161.5))[1], s, ("seam",)),
        "teeth_runs_X": [r1(r) for r in runs],
        "n_teeth_visible_total": len(runs),
        "n_teeth_between_sights": len(teeth_between),
        "pitch_autocorr": M(p_mm, s, ("est",), extra_unc=0.0, how="autocorrelation of the tooth-top profile between "
                                                                 "the sights (peak %.2f)" % q, dec=2),
        "pitch_tooth_centres_fit": {"mm": round(float(k_), 2), "rms_mm": round(float(rms_c), 2)},
        "tooth_length_median": M(float(np.median([b - a for a, b in teeth_between])) if teeth_between else 0, s,
                                 ("sil", "sil")),
    }
    rails["top"]["implied_overall_mm_if_pitch_is_10.01"] = round(OVERALL_MM * RAIL_PITCH / float(k_), 1)
    rails["top"]["slots_at_10.01_over_length"] = round((rt[1] - rt[0]) / RAIL_PITCH, 1)
    # lower rail (bottom profile)
    lr = bx["lower_rail"]
    xs2 = np.arange(lr[0] + W(0.3), lr[1] - W(0.3), W(0.25))
    bz = np.array([(col_extent(fr, P["lower_rail"], X) or (np.nan, np.nan))[0] for X in xs2])
    ok2 = ~np.isnan(bz)
    t_lo = float(np.percentile(bz[ok2], 10))
    t_hi = float(np.percentile(bz[ok2], 92))
    runs2 = [r for r in teeth_runs(xs2[ok2], -bz[ok2], -(t_lo + t_hi) / 2) if r[1] - r[0] > W(1.0)]
    c2 = np.array([(a + b) / 2 for a, b in runs2])
    k2 = R.fit_line(np.arange(len(c2), dtype=float), c2)[0] if len(c2) > 2 else float("nan")
    rails["bottom"] = {
        "X": r1(lr[:2]), "length": M(lr[1] - lr[0], s, ("seam", "sil")),
        "tooth_bottom_Z": M(t_lo, s, ("sil",)), "slot_Z": M(t_hi, s, ("sil",)),
        "top_Z_seam": M(fr.mm(*view.px(100, 221.5))[1], s, ("seam",)),
        "teeth_runs_X": [r1(r) for r in runs2], "n_teeth_visible": len(runs2),
        "pitch_tooth_centres_fit_mm": round(float(k2), 2),
    }
    out["rails"] = rails
    # ---------------- sights
    sg = {}
    for nm in ("sight_front", "sight_rear"):
        b = bx[nm]
        topz = b[3]
        # the upper part (above the base): X span 2-6 mm below the top
        sp = [row_span_mm(fr, P[nm], topz - dz, (b[0] + b[1]) / 2) for dz in np.linspace(W(1.0), W(6.0), 11)]
        sp = np.array([t for t in sp if t])
        base = [row_span_mm(fr, P[nm], tooth_top + dz, (b[0] + b[1]) / 2) for dz in (W(1.0), W(2.0), W(3.0))]
        base = np.array([t for t in base if t])
        sg[nm] = {"X": r1(b[:2]), "top_Z": M(topz, s, ("sil",)),
                  "head_X_span_1to6mm_below_top": r1([sp[:, 0].mean(), sp[:, 1].mean()]),
                  "head_centre_X": M(float(sp.mean()), s), "head_length": M(float(np.mean(sp[:, 1] - sp[:, 0])), s),
                  "base_X_span_above_rail": r1([base[:, 0].mean(), base[:, 1].mean()]) if len(base) else None,
                  "base_length": M(float(np.mean(base[:, 1] - base[:, 0])), s) if len(base) else None,
                  "height_above_rail_tooth_top": M(topz - tooth_top, s)}
    sg["sight_radius_head_centres"] = M(sg["sight_front"]["head_centre_X"]["mm"] - sg["sight_rear"]["head_centre_X"]["mm"],
                                        s, ("sil", "sil", "sil", "sil"))
    sg["note"] = ("flip-up sights drawn UP: front = post between protective ears; rear = diopter (aperture) between "
                  "ears; both clamp on the top rail. The aperture and post tips are not resolved in the side view")
    out["sights"] = sg
    # ---------------- receiver
    rcv_front = br[0]
    rcv_rear = bx["receiver_upper"][0]
    def zcol(X, fn):
        e = col_extent(fr, gun, X)
        return fn(e) if e else None
    seam_Z = fr.mm(*view.px(300, 211.0))[1]
    under_rail = fr.mm(*view.px(200, 161.5))[1]
    out["receiver"] = {
        "X": r1([rcv_rear, rcv_front]),
        "length_front_face_to_rear_end": M(rcv_front - rcv_rear, s, ("sil", "seam"),
                                           how="front face (barrel collar seam) to the rear end at the hinge block seam"),
        "upper_top_Z_under_rail": M(under_rail, s, ("seam",)),
        "upper_lower_seam_Z": M(seam_Z, s, ("seam",), how="horizontal seam y 211 from the hinge to x 219"),
        "lower_front_tab_top_Z": M(fr.mm(*view.px(200, 206.5))[1], s, ("seam",)),
        "upper_height_rail_underside_to_seam": M(under_rail - seam_Z, s, ("seam", "seam")),
        "front_body_bottom_Z_above_lower_rail": M(fr.mm(*view.px(100, 221.5))[1], s, ("seam",)),
        "front_body_height_rail_underside_to_lower_rail": M(under_rail - fr.mm(*view.px(100, 221.5))[1], s,
                                                             ("seam", "seam")),
        "gun_without_mag_extent_every_10mm_X_Zbottom_Ztop": [
            [round(float(X), 0), round(e[0], 1), round(e[1], 1)]
            for X in np.arange(rcv_rear, rcv_front + 0.1, 10.0) if (e := col_extent(fr, gun, X))],
        "handguard_area_X": r1(bx["handguard_area"][:2]),
        "receiver_upper_box": r1(bx["receiver_upper"]),
        "receiver_lower_box": r1(bx["receiver_lower"]),
        "note": "the upper is one housing incl. the slotted front (handguard area) and the rail; the lower is the "
                "grip frame with magwell and trigger guard; seams as drawn (hand-read)",
    }
    # ---------------- magazine + magwell
    out["magazine"] = measure_mag(view, fr, A)
    mw = bx["mag_well"]
    lip = [fr.mm(*view.px(x, y)) for x, y in [(172, 258.0), (214, 266.0)]]
    out["mag_well"] = {
        "X": r1(mw[:2]), "Z": r1(mw[2:]),
        "front_face_X": M(mw[1], s, ("sil",)),
        "lip_lower_edge_front_XZ": r1(lip[0]), "lip_lower_edge_rear_XZ": r1(lip[1]),
        "lip_slope_deg": round(math.degrees(math.atan2(lip[0][1] - lip[1][1], lip[0][0] - lip[1][0])), 1),
        "note": "the lip is the flared lower edge of the well; it slopes up toward the muzzle (front higher)",
    }
    # ---------------- trigger group
    tg, tr = bx["trigger_guard"], bx["trigger"]
    out["trigger_guard"] = {"X": r1(tg[:2]), "Z": r1(tg[2:]), "length": M(tg[1] - tg[0], s),
                            "bottom_Z": M(tg[2], s, ("sil",)),
                            "opening_hole_px": [h for h in view.kept_holes if
                                                h["bbox_px"][0] < view.px(300, 0)[0] and h["bbox_px"][1] > 230]}
    # trigger face: front-most (toward muzzle) X of the blade at each Z, lower half of the blade
    tz = np.linspace(tr[2] + 1.0, tr[3] - 1.5, 12)
    face = []
    for Z in tz:
        hh = hits_h(P["trigger"], fr.px(0, Z)[1])
        if len(hh) >= 2:
            xs_ = [fr.mm(h, fr.px(0, Z)[1])[0] for h in hh]
            face.append((Z, max(xs_), min(xs_)))
    face = np.array(face)
    out["trigger"] = {"X": r1(tr[:2]), "Z": r1(tr[2:]), "tip_Z": M(tr[2], s, ("sil",)),
                      "face_profile_Z_Xfront_Xrear": [r1(f) for f in face]}
    # ---------------- grip
    gp = bx["grip"]
    zweb = fr.mm(*view.px(300, 241))[1]
    gz = np.linspace(gp[2] + W(15), zweb - W(10), 40)
    fe, re_ = [], []
    for Z in gz:
        ints = row_intervals_mm(fr, P["grip"], Z)
        if ints:
            fe.append((Z, max(b for a, b in ints)))       # front edge = largest X (toward the muzzle)
            re_.append((Z, min(a for a, b in ints)))
    fe, re_ = np.array(fe), np.array(re_)
    kf, cf, rmsf = R.fit_line(fe[:, 0], fe[:, 1])
    up = re_[:, 0] > gp[2] + W(35)                      # backstrap: its upper part (the palm swell below is curved)
    kr, cr, rmsr = R.fit_line(re_[up, 0], re_[up, 1])
    ang_f = math.degrees(math.atan(kf))     # dX/dZ: + means the edge leans forward going up
    ang_r = math.degrees(math.atan(kr))
    mid_k = (kf + kr) / 2
    width_perp = float(np.median((fe[:, 1] - re_[:, 1]) * math.cos(math.atan(mid_k))))
    bottom = fr.mm_arr(np.vstack(outer(P["grip"])))
    bpt = bottom[np.argmin(bottom[:, 1])]
    out["grip"] = {
        "X": r1(gp[:2]), "Z": r1(gp[2:]), "bottom_Z": M(gp[2], s, ("sil",)), "lowest_point_XZ": r1(bpt),
        "front_edge_rake_deg_from_vertical": round(ang_f, 2), "rear_edge_rake_deg_from_vertical": round(ang_r, 2),
        "axis_rake_deg_from_perpendicular_to_bore": M(math.degrees(math.atan(mid_k)), 1.0, (), dec=2,
                                                      how="mean of the front edge fit (Z %.0f..%.0f, rms %.2f mm) and "
                                                          "the backstrap fit (upper part, rms %.2f mm); + = the bottom "
                                                          "is behind the top" % (gz[0], gz[-1], rmsf, rmsr)),
        "taper_note": "the grip widens toward the bottom (backstrap rakes more than the front strap: palm swell / "
                      "flared heel)",
        "width_perpendicular_to_axis": M(width_perp, s),
        "width_horizontal_median": M(float(np.median(fe[:, 1] - re_[:, 1])), s),
        "length_along_axis_from_receiver_seam": M((seam_Z - gp[2]) / math.cos(math.atan(mid_k)), s, ("seam", "sil")),
        "rear_edge_X_at_Z": {str(int(round(z))): round(float(x), 1) for z, x in re_[::5]},
        "front_edge_X_at_Z": {str(int(round(z))): round(float(x), 1) for z, x in fe[::5]},
    }
    # trigger reach: backstrap (grip rear edge line) to the trigger blade at the finger-pad height (lower third)
    zf = float(face[len(face) // 3, 0]) if len(face) else tr[2] + 5
    xfront = float(np.interp(zf, face[:, 0], face[:, 1]))
    xrear = float(np.interp(zf, face[:, 0], face[:, 2]))
    xback = kr * zf + cr
    out["trigger_reach_to_blade_front_face"] = M(xfront - xback, s, ("sil", "sil"), extra_unc=1.5,
                                                 how="parallel to the bore at Z %.1f (blade lower third): backstrap "
                                                     "line (grip rear edge, upper part) to the blade's front (finger) "
                                                     "face" % zf)
    out["trigger_reach_to_blade_rear_face"] = M(xrear - xback, s, ("sil", "sil"), extra_unc=1.5)
    out["trigger_reach_note"] = ("the finger pad rests on the blade's front face; real-pattern reach for a full-size "
                                 "rifle-type grip is about 65-75 mm (at 690 mm the sheet's trigger group was drawn 13-29 %% large; "
                                 "at %.0f it reads as measured here; see the scale cross-checks)" % OVERALL_MM)
    # ---------------- stock
    out["stock"] = measure_stock(view, fr, A, bx)
    # ---------------- face features (charging handle, selector, pins, slots)
    ff = {}
    for nm, Pp in cfg["face_features"].items():
        Q = fr.mm_arr(view.poly(Pp))
        ff[nm] = {"X": r1([Q[:, 0].min(), Q[:, 0].max()]), "Z": r1([Q[:, 1].min(), Q[:, 1].max()]),
                  "centre_XZ": r1(Q.mean(axis=0)), "outline_mm": [r1(q) for q in Q], "unc_mm": round(1.0 / s, 1)}
    out["face_features"] = ff
    kn = fr.mm(*view.px(*cfg["charging_knob_centre"]))
    out["charging_handle"] = {"knob_centre_XZ": M(kn[0], s, ("seam",)) | {"Z": round(kn[1], 1)},
                              "knob_diameter": M(11.0 / s, s, ("seam", "seam")),
                              "rod_and_block_X": ff["charging_handle_rod"]["X"][:1] +
                              ff["charging_handle_rear_block"]["X"][1:],
                              "side": "LEFT (front upper receiver, below the rail)"}
    sp_ = fr.mm(*view.px(*cfg["selector_pivot"]))
    out["selector_left"] = {"pivot_XZ": r1(sp_), "unc_mm": round(1.0 / s, 1),
                            "lever_tip_XZ": r1(fr.mm(*view.px(298.5, 237.5))),
                            "ring_diameter": M(17.6 / s, s, ("seam", "seam"))}
    # ---------------- dark slots / vents (auto: dark blobs inside the silhouette, upper housing only)
    out["dark_features_auto"] = dark_features(view, fr, A)
    # ---------------- reference points for the build
    gcen = (re_[:, 1] + fe[:, 1]) / 2
    kg, cg, _ = R.fit_line(re_[:, 0], gcen)
    zj = seam_Z if seam_Z < 0 else fr.mm(*view.px(300, 241))[1]
    zj = fr.mm(*view.px(300, 241))[1]             # the grip / trigger-guard junction (web line) in the side view
    zgrip = zj - 40.0 * math.cos(math.atan(kg))
    out["reference_points"] = {
        "grip_axis_line_X_of_Z": {"slope_dX_dZ": round(kg, 4), "X_at_Z0": round(cg, 2)},
        "grip_junction_web_Z": round(zj, 1),
        "Grip_origin_provisional_XZ": [round(kg * zgrip + cg, 1), round(zgrip, 1)],
        "Grip_note": "GUN_BUILDING_STUDY 5.1: on the grip axis, 40 mm down from the grip/receiver junction (web line, "
                     "here the grip front's top at the trigger guard, Z of panel y 241); provisional until H1",
        "bore_axis_Z": 0.0,
        "sight_line_Z_front_top": sg["sight_front"]["top_Z"]["mm"],
        "sight_line_Z_rear_top": sg["sight_rear"]["top_Z"]["mm"],
        "rail_top_Z": rails["top"]["tooth_top_Z"]["mm"],
    }
    return out


def measure_mag(view, fr, A):
    s = fr.s
    rings = A["mag"]
    Q = fr.mm_arr(np.vstack(outer(rings)))
    X0, X1, Z0, Z1 = Q[:, 0].min(), Q[:, 0].max(), Q[:, 1].min(), Q[:, 1].max()
    # check fix C2 (2026-10-09): fit the edges on the straight body only (Z0+14 .. Z1-14 = about Z -240 .. -90): the
    # old window (Z0+6 .. Z1-4) took in the lip-cut rear corner and the floor-plate flare and read 7.42 deg vs 8.25
    zs = np.linspace(Z0 + W(14), Z1 - W(14), 40)
    fe, re_ = [], []
    for Z in zs:
        ints = row_intervals_mm(fr, rings, Z)
        if ints:
            fe.append((Z, max(b for a, b in ints)))
            re_.append((Z, min(a for a, b in ints)))
    fe, re_ = np.array(fe), np.array(re_)
    kf, cf, rmsf = R.fit_line(fe[:, 0], fe[:, 1])
    kr, cr, rmsr = R.fit_line(re_[:, 0], re_[:, 1])
    k = (kf + kr) / 2
    rake = math.degrees(math.atan(k))           # + = the top is further forward than the bottom
    w = (fe[:, 1] - re_[:, 1]) * math.cos(math.atan(k))
    # length along the axis: top cut (lip) to the floor plate bottom, measured on the mid line
    out = {
        "X": r1([X0, X1]), "Z": r1([Z0, Z1]),
        "exposed_top_Z_at_lip": M(Z1, s, ("seam",)), "floor_bottom_Z": M(Z0, s, ("sil",)),
        "rake_deg_from_perpendicular_to_bore": round(rake, 2),
        "width_front_to_back_perpendicular_to_axis": M(float(np.median(w)), s),
        "width_profile_Z_w": [[round(float(z), 1), round(float(v), 1)] for z, v in zip(fe[::4, 0], w[::4])],
        "exposed_length_along_axis": M((Z1 - Z0) / math.cos(math.atan(k)), s, ("seam", "sil")),
        "front_edge_X_at_top_bottom": r1([kf * Z1 + cf, kf * Z0 + cf]),
        "front_edge_line": {"dX_dZ": round(kf, 4), "X_at_Z0": round(cf, 2)},
        "rear_edge_line": {"dX_dZ": round(kr, 4), "X_at_Z0": round(cr, 2)},
        "front_edge_X_extended_to_receiver_seam_Z_-18.5": round(kf * W(-18.5) + cf, 1),
        "rear_edge_X_at_top_bottom": r1([kr * Z1 + cr, kr * Z0 + cr]),
        "floor_plate": {},
    }
    # floor plate: the widest few mm at the bottom
    fp = []
    for Z in np.linspace(Z0 + W(0.5), Z0 + W(8), 16):
        ints = row_intervals_mm(fr, rings, Z)
        if ints:
            fp.append((Z, min(a for a, b in ints), max(b for a, b in ints)))
    fp = np.array(fp)
    out["floor_plate"] = {"max_length_X": M(float((fp[:, 2] - fp[:, 1]).max()), s),
                          "profile_Z_Xrear_Xfront": [r1(f) for f in fp[::3]]}
    # the sign convention, stated plainly
    out["rake_note"] = ("angle of the magazine's centre line from the perpendicular to the bore; + = the edges move "
                        "toward the muzzle going UP (top forward of the bottom), - = the floor plate is forward of the "
                        "top. Edge fit rms %.2f / %.2f mm" % (rmsf, rmsr))
    return out


def measure_stock(view, fr, A, bx):
    s = fr.s
    P = A["parts"]
    info = A["stock_info"]
    out = {"parts_X_Z": {k: r1(bx[k]) for k in ("hinge_block", "stock_hinge_knuckle", "stock_neck", "stock_top_strut",
                                                 "stock_lower_strut", "stock_web", "stock_rear_upright", "butt_pad")
                         if k in bx}}
    hb, kn, bp = bx["hinge_block"], bx["stock_hinge_knuckle"], bx["butt_pad"]
    out["hinge_block_length"] = M(hb[1] - hb[0], s, ("seam", "seam"))
    out["knuckle_length"] = M(kn[1] - kn[0], s, ("seam", "seam"))
    gaps = [h for h in view.kept_holes if abs(h["bbox_px"][0] - view.px(370.5, 0)[0]) < 4]
    out["hinge_gap_hole_px"] = gaps
    gz = fr.mm(*view.px(370.5, 183.0))[1], fr.mm(*view.px(370.5, 206.0))[1]
    out["hinge_axis_estimate"] = {
        "X": M(fr.mm(*view.px(369.5, 0))[0], s, ("seam",)),
        "Z_range_of_gap": r1(sorted(gz)),
        "note": "the hinge axis is vertical (side-folding stock) and sits at the gap between the receiver's hinge block "
                "and the stock knuckle; its lateral (Y) position is not shown (real pattern: the stock folds to the "
                "gun's right, axis at the right rear corner)"}
    out["butt_pad"] = {"X": r1(bp[:2]), "thickness_side": M(bp[1] - bp[0], s, ("seam", "sil")),
                       "height": M(bp[3] - bp[2], s), "Z": r1(bp[2:])}
    # struts at stations
    w0, w1 = info["windows_px_x"]
    st = {}
    for nm in ("stock_top_strut", "stock_lower_strut"):
        b = bx[nm]
        prof = []
        for X in np.linspace(b[0] + W(3), b[1] - W(3), 9):
            iv = col_intervals_mm(fr, P[nm], X)
            if iv:
                prof.append((X, iv[0][0], iv[0][1]))
        prof = np.array(prof)
        kk_top = R.fit_line(prof[:, 0], prof[:, 2])
        kk_bot = R.fit_line(prof[:, 0], prof[:, 1])
        ang = math.degrees(math.atan((kk_top[0] + kk_bot[0]) / 2))
        st[nm] = {"X": r1(b[:2]), "profile_X_Zbottom_Ztop": [r1(p) for p in prof],
                  "thickness_vertical_median": M(float(np.median(prof[:, 2] - prof[:, 1])), s),
                  "thickness_perpendicular_median": M(float(np.median(prof[:, 2] - prof[:, 1])) *
                                                      math.cos(math.radians(ang)), s),
                  "angle_deg_from_bore": round(ang, 2), "angle_note": "+ = rises toward the muzzle"}
    out["struts"] = st
    for nm in ("stock_web", "stock_rear_upright", "stock_neck"):
        b = bx[nm]
        zmid = (b[2] + b[3]) / 2
        ints = row_intervals_mm(fr, P[nm], zmid)
        out[nm] = {"X": r1(b[:2]), "Z": r1(b[2:]),
                   "thickness_X_at_mid_height": M(max(b_ - a_ for a_, b_ in ints), s, ("seam", "seam")) if ints else None}
    wins = [h for h in view.kept_holes if h["bbox_px"][0] >= min(w0[0], w1[0]) - 1 and h["bbox_px"][2] <= max(
        w0[1], w1[1]) + 1 and (h["bbox_px"][2] - h["bbox_px"][0]) > 15]
    out["windows_px"] = wins
    out["window_lines_px"] = {k: v for k, v in info.items() if k != "windows_px_x"}
    sil = A["sil"]
    rear = part_box_mm(fr, sil)[0]
    out["length_hinge_gap_to_butt_rear"] = M(out["hinge_axis_estimate"]["X"]["mm"] - rear, s, ("seam", "sil"))
    out["length_receiver_rear_to_butt_rear"] = M(hb[0] - rear, s, ("seam", "sil"))
    out["top_strut_top_Z_at_hinge_and_pad"] = r1([st["stock_top_strut"]["profile_X_Zbottom_Ztop"][-1][2],
                                                 st["stock_top_strut"]["profile_X_Zbottom_Ztop"][0][2]])
    return out


def dark_features(view, fr, A, thr=30.0):
    """Very dark blobs (slots, vents, the ejection port...) inside the gun's silhouette: bbox in mm, auto-detected."""
    sil = R.rings_to_mask(A["gun"], view.sil.shape)
    sil = ndi.binary_erosion(sil, iterations=2)
    D = (ndi.median_filter(view.L, 3) < thr) & sil
    D = ndi.binary_opening(D, structure=np.ones((2, 2), bool))
    lab, n = ndi.label(D)
    out = []
    for k in range(1, n + 1):
        m = lab == k
        a = int(m.sum())
        if a < 12:
            continue
        ys, xs = np.nonzero(m)
        w, h = xs.max() - xs.min() + 1, ys.max() - ys.min() + 1
        if max(w, h) < 6 or a > 1500 or a < 30:
            continue
        Q = fr.mm_arr(np.c_[[xs.min(), xs.max()], [ys.max(), ys.min()]])
        if min(Q[:, 1]) > W(38):                 # rail slots (reported under rails)
            continue
        out.append({"bbox_px": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())], "area_px": a,
                    "X": r1(sorted(Q[:, 0])), "Z": r1(sorted(Q[:, 1]))})
    out.sort(key=lambda d: -d["X"][1])
    return out


# ------------------------------------------------------------------------------------------------ TOP view
def analyse_top(view):
    rings = view.rings
    cfg = view.cfg
    allp = np.vstack(outer(rings))
    cx, cy = [], []
    for xa, xb in cfg["bore_probe_x"] + [cfg["body_probe_x"]]:
        for x in np.arange(xa, xb + 0.01, 1.0):
            h = hits_v(rings, x)
            if len(h) >= 2:
                cx.append(x)
                cy.append((h[0] + h[-1]) / 2)
    cx, cy = np.array(cx), np.array(cy)
    a, b, rms = R.fit_line(cx, cy)
    # separately: device-only centre and body-only centre
    dev = cx < cfg["bore_probe_x"][-1][1] + 1
    u = np.array([-1.0, -a])
    u /= np.hypot(*u)
    t = allp @ u
    L_px = float(t.max() - t.min())
    p_on = np.array([cx.mean(), a * cx.mean() + b])
    fr = Frame(L_px / OVERALL_MM, u, p_on + (t.min() - p_on @ u) * u, "down")
    prof = []
    for x in np.arange(np.ceil(allp[:, 0].min()), allp[:, 0].max(), 0.5):
        h = hits_v(rings, x)
        if len(h) >= 2:
            X, Y1 = fr.mm(x, h[0])
            _, Y2 = fr.mm(x, h[-1])
            prof.append((X, max(Y1, Y2), min(Y1, Y2)))      # X, Y_left (+), Y_right (-)
    prof = np.array(prof)
    prof = prof[np.argsort(prof[:, 0])]
    devc = cy[dev] - (a * cx[dev] + b)
    bodyc = cy[~dev] - (a * cx[~dev] + b)
    return {"rings": rings, "frame": fr, "L_px": L_px, "profile": prof,
            "axis": {"slope_deg": math.degrees(math.atan(a)), "fit_rms_px": rms,
                     "device_centre_offset_px": round(float(np.mean(devc)), 2),
                     "body_centre_offset_px": round(float(np.mean(bodyc)), 2)}}


def measure_top(T, ML):
    fr, prof = T["frame"], T["profile"]
    s = fr.s

    def band(Xa, Xb):
        sel = (prof[:, 0] >= Xa) & (prof[:, 0] <= Xb)
        return prof[sel]

    def wmed(Xa, Xb):
        p = band(Xa, Xb)
        return float(np.median(p[:, 1] - p[:, 2]))

    out = {}
    # stations from LEFT for orientation (each view has its own frame, so these are only windows)
    md = ML["muzzle_device"]["X"]
    rf = ML["barrel"]["receiver_front_face_X"]["mm"]
    rr = ML["receiver"]["X"][0]
    out["muzzle_device_width"] = M(wmed(md[0] + W(4), md[1] - W(4)), s)
    out["receiver_body_width_plain"] = M(wmed(rr + W(100), rf - W(110)), s,
                                         how="median over the plain middle of the receiver (X %.0f-%.0f, no lateral "
                                             "features)" % (rr + W(100), rf - W(110)))
    out["front_body_width"] = M(wmed(rf - W(62), rf - W(38)), s, how="slotted front section between the charging handle "
                                                                 "knob and the front sight base (X %.0f-%.0f)" % (
                                                                     rf - W(62), rf - W(38)))
    out["front_sight_zone_width"] = M(wmed(rf - W(30), rf - W(8)), s, how="front sight base / ears zone; protrudes to the "
                                                                     "gun's right in TOP")
    pb = band(rr + W(100), rf - W(110))
    out["receiver_body_Y_left_right"] = r1([np.median(pb[:, 1]), np.median(pb[:, 2])])
    out["receiver_offset_of_mid_plane"] = M(float(np.median((pb[:, 1] + pb[:, 2]) / 2)), s, how="body centre vs axis")
    # steps in the width profile: find the device -> body step, body -> stock step, stock -> butt pad step
    w = prof[:, 1] - prof[:, 2]
    X = prof[:, 0]
    sm = ndi.median_filter(w, 5)
    out["width_profile_mm_every_5mm_X_Yleft_Yright"] = [[round(float(p[0]), 1), round(float(p[1]), 2),
                                                         round(float(p[2]), 2)] for p in prof[::max(1, int(round(
                                                             5 * s / 0.5)))]]
    # the body front face: first X (from the muzzle) where the width exceeds 1.6 x the device width
    dw = out["muzzle_device_width"]["mm"]
    front = X[(sm > 1.6 * dw)].max()
    out["body_front_face_X"] = M(float(front), s, ("sil",))
    # the stock: the rear of the receiver block = where the width drops below 0.75 x the plain body width, behind it
    bw = out["receiver_body_width_plain"]["mm"]
    behind = (X < rr + W(40)) & (sm < 0.85 * bw)
    out["body_rear_end_X_width_drop"] = M(float(X[behind].max()), s, ("sil",),
                                          how="first width drop below 85 % of the plain body width, going rearward")
    # butt pad: the widest thing at the rear
    rear = X < W(60)
    out["butt_pad_width"] = M(float(w[rear].max()), s)
    out["butt_pad_front_X_estimate"] = M(float(X[rear & (sm > 0.85 * w[rear].max())].max()), s, ("sil", "est"))
    stock = (X > W(60)) & (X < X[behind].max() - W(30))
    out["stock_width_profile_median"] = M(float(np.median(w[stock])), s)
    out["stock_width_by_X"] = {str(int(x)): round(float(np.median(w[(X > x - 3) & (X < x + 3)])), 1)
                               for x in np.arange(W(70), X[behind].max() - W(20), W(20))}
    # lateral features beyond the plain body (gun left = +Y, gun right = -Y)
    yl, yr = out["receiver_body_Y_left_right"]
    zone = (X > rr) & (X < front - 3)

    def runs(cond, col, sign, base):
        res, cur = [], []
        for k in np.nonzero(zone)[0]:
            if cond[k]:
                cur.append(k)
            elif cur:
                res.append(cur)
                cur = []
        if cur:
            res.append(cur)
        o = []
        for c in res:
            seg = prof[c]
            if seg[-1, 0] - seg[0, 0] < W(2.5):
                continue
            ext = seg[:, col].max() if sign > 0 else seg[:, col].min()
            o.append({"X": r1([seg[0, 0], seg[-1, 0]]), "Y_extreme": round(float(ext), 1),
                      "beyond_body_mm": round(float(abs(ext - base)), 1)})
        return o

    out["lateral_features_gun_left_(+Y,image-down)"] = runs(prof[:, 1] > yl + W(2.5), 1, 1, yl)
    out["lateral_features_gun_right_(-Y,image-up)"] = runs(prof[:, 2] < yr - W(2.5), 2, -1, yr)
    kx = [fr.mm(x, 300)[0] for x in T["cfg"]["charging_knob_x"]]
    out["charging_knob_X_hand_read"] = r1(sorted(kx))
    out["overall_width_max"] = M(float(w.max()), s, how="incl. the charging handle knob and the butt pad")
    out["max_width_receiver_zone_incl_knob"] = M(float(w[(X > rr) & (X < front)].max()), s)
    # rail slot pitch from the luminance along the rail centre line (cross slots read as stripes)
    vals, xsr = [], []
    v = T["view"]
    for Xs in np.arange(rr + W(90), rf - W(40), W(0.25)):
        p = fr.px(Xs, 0.0)
        xi, yi = p
        x0, y0 = int(np.floor(xi)), int(np.floor(yi))
        fx, fy = xi - x0, yi - y0
        Lb = v.L[y0 - 6:y0 + 7, x0:x0 + 2].mean(axis=0)
        vals.append((1 - fx) * Lb[0] + fx * Lb[1])
        xsr.append(Xs)
    p_mm, q = pitch_from_profile(np.array(xsr), np.array(vals), W(6), W(16))
    out["rail_stripe_pitch_autocorr"] = {"mm": round(p_mm, 2), "peak": round(q, 3),
                                         "implied_overall_mm_if_10.01": round(OVERALL_MM * RAIL_PITCH / p_mm, 1)}
    return out


# ------------------------------------------------------------------------------------------------ ruler
def ruler_scale(view):
    """px per 10 cm of the printed ruler. The ruler is a horizontal line (row found as the darkest full row under the
    gun) with long ticks every 10 cm (labels 0..70, on both sides of the line) and short 5 cm ticks above it only;
    the long ticks are the ones below the line."""
    sub = view.L[440:530]
    thr = np.percentile(sub, 75) - 40
    D = sub < thr
    D[:, :4] = D[:, -4:] = False
    yl = int(np.argmax(D.sum(axis=1)))
    cols = D[yl + 1:yl + 11].sum(axis=0) >= 2
    lab, n = ndi.label(cols)
    cent = np.sort(np.array([np.mean(np.nonzero(lab == k)[0]) for k in range(1, n + 1)]))
    if view.mirror:
        cent = np.sort(view.W - 1 - cent)
    k, c, rms = R.fit_line(np.arange(len(cent), dtype=float), cent)
    short = D[yl - 10:yl].sum(axis=0) >= 2
    return {"ruler_line_row_px": int(yl + 440), "long_ticks_found": int(n), "tick_spacing_px_per_10cm": round(float(k), 3),
            "fit_rms_px": round(rms, 3), "zero_tick_x_px": round(float(c), 2),
            "short_tick_columns_above": int(ndi.label(short)[1])}


# ------------------------------------------------------------------------------------------------ overlay
def draw_rings(d, rings, sc, off, col, w=1):
    for r in rings:
        d.line([((x + 0.5) * sc + off[0], (y + 0.5) * sc + off[1]) for x, y in np.vstack([r, r[:1]])], fill=col,
               width=w)


def font(sz):
    for f in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(f, sz)
        except OSError:
            pass
    return ImageFont.load_default()


def draw_axis(d, fr, sc, off, X1, col=(255, 0, 0)):
    for X in np.arange(0, X1, 12):
        p, q = fr.px(X, 0), fr.px(X + 6, 0)
        d.line([((p[0] + .5) * sc + off[0], (p[1] + .5) * sc + off[1]),
                ((q[0] + .5) * sc + off[0], (q[1] + .5) * sc + off[1])], fill=col)


def draw_view(d, v, A, sc, off, fr, other=None, label_parts=True):
    if A is not None and "parts" in A and label_parts:
        for nm, rr in A["parts"].items():
            draw_rings(d, rr, sc, off, PART_COLS.get(nm, (200, 200, 200)))
        for nm, Pp in v.cfg.get("face_features", {}).items():
            draw_rings(d, [np.array(v.poly(Pp))], sc, off, (255, 255, 255))
    elif A is not None:
        draw_rings(d, A["mag"], sc, off, (255, 255, 0))
        for nm, Pp in v.cfg.get("face_features", {}).items():
            draw_rings(d, [np.array(v.poly(Pp))], sc, off, (255, 255, 255))
    if other is not None:
        draw_rings(d, other, sc, off, (0, 255, 255))
    draw_rings(d, v.rings, sc, off, (255, 0, 255))
    draw_axis(d, fr, sc, off, OVERALL_MM)


def crop_box(v, pad=8):
    x0, x1, y0, y1 = bbox(v.rings)
    return int(max(0, x0 - pad)), int(max(0, y0 - pad)), int(min(v.W, x1 + pad)), int(min(v.H, y1 + pad))


def make_overlay(rows, path, sc=2):
    pad = 34
    tiles = []
    for title, v, A, fr, other in rows:
        cx0, cy0, cx1, cy1 = crop_box(v)
        im = Image.fromarray(v.rgb.astype(np.uint8)).resize((v.W * sc, v.H * sc), Image.LANCZOS)
        d = ImageDraw.Draw(im)
        draw_view(d, v, A, sc, (0, 0), fr, other)
        tiles.append((title, im.crop((cx0 * sc, cy0 * sc, cx1 * sc, cy1 * sc))))
    W = max(t.width for _, t in tiles) + 20
    H = sum(t.height + pad for _, t in tiles) + 10
    out = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(out)
    f = font(17)
    y = 0
    for title, t in tiles:
        d.text((10, y + 8), title, fill=(0, 0, 0), font=f)
        y += pad
        out.paste(t, (10, y))
        y += t.height
    out.save(path)


def zoom_tiles(rows):
    paths = []
    for title, v, A, fr, other in rows:
        sc = 4
        im = Image.fromarray(v.rgb.astype(np.uint8)).resize((v.W * sc, v.H * sc), Image.LANCZOS)
        draw_view(ImageDraw.Draw(im), v, A, sc, (0, 0), fr, other)
        x0, x1, y0, y1 = bbox(v.rings)
        xs = np.linspace(x0 - 4, x1 + 5, 5).astype(int)
        for i in range(4):
            p = SCRATCH / f"qa_zoom_{v.name}_{i}.png"
            im.crop((xs[i] * sc, int(y0 - 4) * sc, xs[i + 1] * sc, int(y1 + 5) * sc)).save(p)
            paths.append(p)
    return paths


# ------------------------------------------------------------------------------------------------ main
def main():
    for d in (TRACE, SCRATCH, CROPS):
        d.mkdir(parents=True, exist_ok=True)
    rgb = load_sheet()
    panels = R.find_panels(rgb)
    assert len(panels) == len(PANEL_NAMES), panels
    boxes = dict(zip(PANEL_NAMES, panels))
    for nm, (x0, y0, x1, y1) in boxes.items():
        Image.fromarray(rgb[y0:y1 + 1, x0:x1 + 1]).save(CROPS / f"{nm}.png")

    left = View("LEFT", rgb, boxes["LEFT"], CONFIG["LEFT"])
    right = View("RIGHT", rgb, boxes["RIGHT"], CONFIG["RIGHT"], mirror=True)
    top = View("TOP", rgb, boxes["TOP"], CONFIG["TOP"])
    AL = analyse_side(left, True)
    AR = analyse_side(right, False)
    frL, LpxL = side_frame(left)
    frR, LpxR = side_frame(right)
    sL = frL.s
    T = analyse_top(top)
    T["cfg"], T["view"] = CONFIG["TOP"], top
    frT = T["frame"]

    # ---------------- LEFT vs mirrored RIGHT (frame-aligned, no fitting)
    def r2l(P):
        return frL.px_arr(frR.mm_arr(P))

    def l2r(P):
        return frR.px_arr(frL.mm_arr(P))

    shape = left.sil.shape
    mR = R.rings_to_mask([r2l(r) for r in right.rings], shape)
    iou_fr = R.iou(mR, left.sil)
    iou_gun = R.iou(R.rings_to_mask([r2l(r) for r in AR["gun"]], shape), R.rings_to_mask(AL["gun"], shape))
    iou_mag = R.iou(R.rings_to_mask([r2l(r) for r in AR["mag"]], shape), R.rings_to_mask(AL["mag"], shape))
    edL = left.sil ^ ndi.binary_erosion(left.sil)
    edR = mR ^ ndi.binary_erosion(mR)
    dists = np.r_[ndi.distance_transform_edt(~edL)[edR], ndi.distance_transform_edt(~edR)[edL]] / sL

    def tf(params, P):
        s_, th, tx, ty = params
        c, sn = math.cos(th), math.sin(th)
        return np.c_[s_ * (c * P[:, 0] - sn * P[:, 1]) + tx, s_ * (sn * P[:, 0] + c * P[:, 1]) + ty]

    def cost(params):
        return -R.iou(R.rings_to_mask([tf(params, r) for r in right.rings], shape, ss=2), left.sil)

    bl, br_ = bbox(left.rings), bbox(right.rings)
    init = np.array([(bl[1] - bl[0]) / (br_[1] - br_[0]), 0.0, bl[0] - br_[0], bl[2] - br_[2]])
    res = minimize(cost, init, method="Nelder-Mead",
                   options={"xatol": 1e-4, "fatol": 1e-5, "maxiter": 600,
                            "initial_simplex": [init, init + [0.01, 0, 0, 0], init + [0, 0.004, 0, 0],
                                                init + [0, 0, 1.5, 0], init + [0, 0, 0, 1.5]]})
    al = res.x
    iou_al = R.iou(R.rings_to_mask([tf(al, r) for r in right.rings], shape), left.sil)

    # per-feature offsets RIGHT - LEFT, measured identically on both silhouettes in their own frames
    def feats(view, A, fr):
        f = {}
        sil = A["sil"]
        X0, X1, Z0, Z1 = part_box_mm(fr, sil)
        f["muzzle_tip_X"] = X1
        f["sight_top_Z"] = Z1
        # sights: columns where the top is > 8 mm above the rail line, clustered
        tops = [(X, e[1]) for X in np.arange(X0 + W(1), X1 - W(1), W(0.5)) if (e := col_extent(fr, sil, X))]
        tops = np.array(tops)
        hi = tops[tops[:, 1] > np.percentile(tops[:, 1], 60) + W(8)]
        if len(hi):
            gap = np.nonzero(np.diff(hi[:, 0]) > W(20))[0]
            groups = np.split(hi, gap + 1)
            groups.sort(key=lambda g: g[:, 0].mean())
            f["rear_sight_X_centre"] = float(groups[0][:, 0].mean())
            f["front_sight_X_centre"] = float(groups[-1][:, 0].mean())
            f["rear_sight_top_Z"] = float(groups[0][:, 1].max())
            f["front_sight_top_Z"] = float(groups[-1][:, 1].max())
        mb = part_box_mm(fr, A["mag"])
        f["mag_rear_X"], f["mag_front_X"], f["mag_bottom_Z"] = mb[0], mb[1], mb[2]
        gun = A["gun"]
        g = fr.mm_arr(np.vstack(outer(gun)))
        behind = g[g[:, 0] < mb[0] - W(10)]
        low = behind[np.argmin(behind[:, 1])]
        f["grip_bottom_X"], f["grip_bottom_Z"] = float(low[0]), float(low[1])
        hol = [fr.mm_arr(np.array([[h["bbox_px"][0], h["bbox_px"][1]], [h["bbox_px"][2], h["bbox_px"][3]]]))
               for h in view.kept_holes]
        hol = sorted([(min(q[:, 0]), max(q[:, 0]), min(q[:, 1]), max(q[:, 1])) for q in hol], key=lambda t: t[0])
        wins = [h for h in hol if h[1] < W(240) and h[1] - h[0] > W(15)]
        for nm, h in zip(("stock_rear_window", "stock_front_window"), wins):
            f[nm + "_X_centre"] = (h[0] + h[1]) / 2
            f[nm + "_Z_centre"] = (h[2] + h[3]) / 2
            f[nm + "_X_length"] = h[1] - h[0]
        for h in hol:
            if h[3] < W(-40):
                f["trigger_guard_opening_X_centre"] = (h[0] + h[1]) / 2
                f["trigger_guard_opening_X_length"] = h[1] - h[0]
                f["trigger_guard_opening_Z_height"] = h[3] - h[2]
        sp = fr.mm(*view.px(*view.cfg["selector_pivot"]))
        f["selector_pivot_X"], f["selector_pivot_Z"] = sp
        f["rear_X_butt"] = X0
        return f

    fL, fR = feats(left, AL, frL), feats(right, AR, frR)
    feat_cmp = {k: {"LEFT": round(fL[k], 1), "RIGHT": round(fR[k], 1), "RIGHT_minus_LEFT": round(fR[k] - fL[k], 1)}
                for k in fL if k in fR}
    prof_cmp = []
    for X in np.arange(W(10), W(680), W(10.0)):
        a = col_extent(frL, left.rings, X)
        b = col_extent(frR, right.rings, X)
        if a and b:
            prof_cmp.append((X, b[1] - a[1], b[0] - a[0]))
    prof_cmp = np.array(prof_cmp)
    agreement_lr = {
        "method": "RIGHT panel mirrored; both side views in the gun frame independently (own rail-direction axis, "
                  "own bore height, X = 0 at the rearmost butt pad point, own scale to %.0f mm) and compared without "
                  "fitting; a free similarity fit (max IoU) is the secondary number" % OVERALL_MM,
        "iou_silhouette_frame_aligned": round(iou_fr, 4), "iou_gun_without_mag_frame_aligned": round(iou_gun, 4),
        "iou_magazine_frame_aligned": round(iou_mag, 4),
        "boundary_distance_mm": {"median": round(float(np.median(dists)), 2),
                                 "p90": round(float(np.percentile(dists, 90)), 2),
                                 "p99": round(float(np.percentile(dists, 99)), 2), "max": round(float(dists.max()), 2)},
        "best_fit_similarity": {"iou": round(iou_al, 4), "scale": round(float(al[0]), 5),
                                "rotation_deg": round(math.degrees(al[1]), 3),
                                "shift_px": [round(float(al[2]), 2), round(float(al[3]), 2)]},
        "profile_diff_RIGHT_minus_LEFT_mm": {
            "note": "outermost top / bottom silhouette Z at stations every 10 mm (RIGHT minus LEFT)",
            "top_abs_median": round(float(np.median(np.abs(prof_cmp[:, 1]))), 2),
            "bottom_abs_median": round(float(np.median(np.abs(prof_cmp[:, 2]))), 2),
            "rows_X_dTop_dBottom": [[round(float(a), 0), round(float(b), 1), round(float(c), 1)]
                                    for a, b, c in prof_cmp]},
        "overall_length_px": {"LEFT": round(LpxL, 2), "RIGHT": round(LpxR, 2), "ratio_R_over_L": round(LpxR / LpxL, 5)},
        "axis_slope_deg": {"LEFT": round(frL.bore["rail_slope_deg"], 3),
                           "RIGHT_mirrored": round(frR.bore["rail_slope_deg"], 3)},
        "feature_offsets_mm": feat_cmp,
    }

    # ---------------- measurements
    ML = measure_left(left, AL, frL)
    MT = measure_top(T, ML)
    rulerL, rulerR = ruler_scale(left), ruler_scale(right)
    q = CONFIG["Q34"]
    mw_f = q["magwell_lip_front_face_px"][1] - q["magwell_lip_front_face_px"][0]
    mg_f = q["magazine_front_face_px_at_y300"][1] - q["magazine_front_face_px_at_y300"][0]
    mg_s = q["magazine_side_face_px_at_y300"][1] - q["magazine_side_face_px_at_y300"][0]
    ew = q["device_end_face_ellipse_px"]
    theta = math.asin(min(1.0, (ew["x"][1] - ew["x"][0]) / (ew["y"][1] - ew["y"][0])))
    D_mag = ML["magazine"]["width_front_to_back_perpendicular_to_axis"]["mm"]
    T_mag = D_mag * (mg_f / mg_s) / math.tan(theta)
    T_lo = D_mag * (mg_f / mg_s) / math.tan(theta + math.radians(5))
    T_hi = D_mag * (mg_f / mg_s) / math.tan(theta - math.radians(5))
    ML["magazine"]["thickness_estimate_from_3q"] = M(
        T_mag, sL, (), extra_unc=(T_hi - T_lo) / 2,
        how="3/4 view: view yaw theta = asin(width / height of the muzzle device's end-face ellipse) = %.1f deg; "
            "thickness = LEFT front-to-back width %.1f x (front-face px / side-face px = %.3f) / tan(theta); "
            "+-5 deg on theta gives the uncertainty" % (math.degrees(theta), D_mag, mg_f / mg_s))
    ML["magazine"]["q34_front_over_side_px"] = round(mg_f / mg_s, 3)
    k_loc = mg_s / (D_mag * math.cos(theta))
    ML["mag_well"]["outer_width_estimate_from_3q"] = M(mw_f / (k_loc * math.sin(theta)), sL, (), extra_unc=0.15 * mw_f / (
        k_loc * math.sin(theta)), how="magwell-lip front face %.1f px / (local px/mm %.3f x sin theta)" % (mw_f, k_loc))
    MR = measure_mag(right, frR, AR)

    # ---------------- TOP vs side stations
    st_cmp = {
        "body_front_face_X": {"TOP": MT["body_front_face_X"]["mm"], "LEFT": ML["barrel"]["receiver_front_face_X"]["mm"]},
        "body_rear_end_X": {"TOP": MT["body_rear_end_X_width_drop"]["mm"], "LEFT_hinge_knuckle_rear":
                            ML["stock"]["parts_X_Z"]["stock_hinge_knuckle"][0], "LEFT_receiver_rear":
                            ML["receiver"]["X"][0]},
        "charging_knob_X": {"TOP": MT["charging_knob_X_hand_read"], "LEFT": ML["face_features"]["charging_handle_knob"]["X"]},
        "butt_pad_front_X": {"TOP_estimate": MT["butt_pad_front_X_estimate"]["mm"],
                             "LEFT": ML["stock"]["butt_pad"]["X"][1]},
    }
    for k, v in st_cmp.items():
        a = v.get("TOP", v.get("TOP_estimate"))
        b = v.get("LEFT", v.get("LEFT_hinge_knuckle_rear"))
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            v["diff_TOP_minus_LEFT"] = round(a - b, 1)
    agreement_top = {"overall_length_px": {"TOP": round(T["L_px"], 2), "LEFT": round(LpxL, 2),
                                           "ratio_TOP_over_LEFT": round(T["L_px"] / LpxL, 5)},
                     "axis": T["axis"], "stations_mm": st_cmp,
                     "muzzle_device": {"TOP_width": MT["muzzle_device_width"]["mm"],
                                       "LEFT_height": ML["muzzle_device"]["diameter"]["mm"]}}

    # ---------------- scale cross-checks
    rail_p = ML["rails"]["top"]["pitch_tooth_centres_fit"]["mm"]
    folded_est = ML["barrel"]["muzzle_tip_X"]["mm"] - ML["stock"]["hinge_axis_estimate"]["X"]["mm"]
    hgt = ML["overall"]["height_with_magazine"]["mm"]
    scale = {
        "overall_length_mm_chosen": OVERALL_MM,
        "px_per_mm": {"LEFT": round(sL, 5), "RIGHT": round(frR.s, 5), "TOP": round(frT.s, 5)},
        "mm_per_px": {"LEFT": round(1 / sL, 4), "RIGHT": round(1 / frR.s, 4), "TOP": round(1 / frT.s, 4)},
        "sheet_ruler": {"LEFT": rulerL, "RIGHT": rulerR,
                        "px_per_cm_LEFT": round(rulerL["tick_spacing_px_per_10cm"] / 10, 4),
                        "implied_overall_length_cm_LEFT": round(LpxL / (rulerL["tick_spacing_px_per_10cm"] / 10), 1),
                        "implied_overall_length_cm_RIGHT": round(LpxR / (rulerR["tick_spacing_px_per_10cm"] / 10), 1),
                        "error_vs_overall_pct": round(100 * (LpxL / (rulerL["tick_spacing_px_per_10cm"] / 10) * 10 /
                                                         OVERALL_MM - 1), 1)},
        "cross_checks": {
            "folded_length_muzzle_tip_to_hinge_gap": {"mm": round(folded_est, 1), "real": FOLDED_MM_REAL,
                                                      "implied_overall_if_folded_is_450": round(
                                                          OVERALL_MM * FOLDED_MM_REAL / folded_est, 1),
                                                      "note": "the folded gun's length is set by the receiver + hinge "
                                                              "(the folded stock lies alongside); the hinge gap is the "
                                                              "rear end"},
            "height_with_magazine": {"mm": hgt, "real_maker_table": HEIGHT_MM_REAL,
                                     "ratio_height_over_length_sheet": round(hgt / OVERALL_MM, 4),
                                     "ratio_real": round(HEIGHT_MM_REAL / OVERALL_MM, 4),
                                     "implied_overall_if_height_is_280": round(OVERALL_MM * HEIGHT_MM_REAL / hgt, 1)},
            "top_rail_pitch": {"sheet_mm": rail_p, "standard": RAIL_PITCH,
                               "implied_overall_if_pitch_is_10.01": ML["rails"]["top"][
                                   "implied_overall_mm_if_pitch_is_10.01"],
                               "TOP_view_stripes": MT["rail_stripe_pitch_autocorr"]},
            "width": {"TOP_max_receiver_zone_incl_knob_mm": MT["max_width_receiver_zone_incl_knob"]["mm"],
                      "TOP_plain_body_mm": MT["receiver_body_width_plain"]["mm"], "real_maker_table": WIDTH_MM_REAL},
            "barrel_200_check": {
                "device_seat_X": ML["barrel"]["device_seat_X"]["mm"],
                "breech_X_if_barrel_200_ending_at_the_device_seat": round(ML["barrel"]["device_seat_X"]["mm"] -
                                                                         BARREL_MM_REAL, 1),
                "ejection_port_X_from_RIGHT": None},
        },
        "global_scale_note": "%.0f mm is the orchestrator ruling of 2026-10-09 (spec resolution R26). At the real "
                             "pattern's 690 the sheet's grip / trigger group was 13-29 %% larger than real (trigger reach "
                             "90.5 vs ~70); at ~625 the side-view rail pitch is exactly 10.01 and the receiver width matches "
                             "the real 61, so the sheet was evidently drawn at ~625. Every silhouette proportion stays the "
                             "sheet's (one uniform scale); the anchors below show what remains off the real pattern" % OVERALL_MM,
        "uncertainty_note": "unc_mm = 1-sigma measurement uncertainty from the edge types (silhouette +-0.4 px, "
                            "hand-placed seam +-1 px, estimate +-2 px) at that view's scale; it does not include the "
                            "scale choice",
    }
    anchors = {
        "trigger_reach_front_face": (ML["trigger_reach_to_blade_front_face"]["mm"], 70.0, "real 65-75 (rifle-type grip)"),
        "height_with_magazine": (hgt, HEIGHT_MM_REAL, "maker's table 11.02 in (magazine not stated)"),
        "top_rail_pitch_side": (rail_p, RAIL_PITCH, "MIL-STD-1913"),
        "top_rail_pitch_TOP_stripes": (MT["rail_stripe_pitch_autocorr"]["mm"], RAIL_PITCH, "MIL-STD-1913"),
        "receiver_width_TOP": (MT["receiver_body_width_plain"]["mm"], WIDTH_MM_REAL, "maker's table 2.40 in"),
        "folded_length": (round(folded_est, 1), FOLDED_MM_REAL, "real pattern"),
    }
    scale["real_anchor_ratios_sheet_over_real"] = {
        k: {"sheet_mm": v[0], "real_mm": v[1], "ratio": round(v[0] / v[1], 3),
            "implied_overall_mm": round(OVERALL_MM * v[1] / v[0], 1), "source": v[2]} for k, v in anchors.items()}
    scale["scale_ruling"] = {
        "overall_mm": OVERALL_MM, "was_mm": SHEET_MM, "factor_vs_690": round(SW, 6),
        "rail_pitch_scale_overall_mm": 625.3,
        "note": "orchestrator ruling 2026-10-09 (spec R26): 625 mm overall, all silhouette proportions the sheet's; at "
                "~625 the side-view rail pitch is exactly 10.01 and the receiver width matches the real 61 mm; "
                "overall 690 -> 625 (-9.4 %), folded and height follow the sheet's proportions"}
    # hidden barrel: the breech face must sit at the magazine's top front (feed) under the ejection port
    mag_top_front = ML["magazine"]["front_edge_X_extended_to_receiver_seam_Z_-18.5"]
    port = scale["cross_checks"]["barrel_200_check"]
    scale["cross_checks"]["barrel_200_check"]["note"] = (
        "a 200 mm barrel ending at the device seat would put the breech at X %.0f, over the magazine's rear half and "
        "behind the ejection port's rear edge; the sheet's feed geometry (magazine front wall extended up to the "
        "receiver seam: X %.0f; magwell front face X %.0f; port X ?) puts the breech face at about X %.0f-%.0f (just "
        "ahead of the magazine's top front, at the port's front edge), i.e. a hidden barrel of about %.0f-%.0f mm to a "
        "crown inside the device collar (X ~%.0f-%.0f)" % (
            ML["barrel"]["device_seat_X"]["mm"] - BARREL_MM_REAL, mag_top_front, ML["mag_well"]["front_face_X"]["mm"],
            mag_top_front + W(4), mag_top_front + W(16), W(655) - (mag_top_front + W(16)), W(660) - (mag_top_front + W(4)),
            W(655), W(660)))
    port = np.array(frR.mm_arr(right.poly(CONFIG["RIGHT"]["face_features"]["ejection_port"])))
    scale["cross_checks"]["barrel_200_check"]["ejection_port_X_from_RIGHT"] = r1([port[:, 0].min(), port[:, 0].max()])
    scale["cross_checks"]["barrel_200_check"]["note"] = scale["cross_checks"]["barrel_200_check"]["note"].replace(
        "port X ?", "port X %.0f-%.0f" % (port[:, 0].min(), port[:, 0].max()))
    rff = {nm: {"X": r1([Q[:, 0].min(), Q[:, 0].max()]), "Z": r1([Q[:, 1].min(), Q[:, 1].max()]),
                "centre_XZ": r1(Q.mean(axis=0))}
           for nm, Pp in CONFIG["RIGHT"]["face_features"].items()
           for Q in [frR.mm_arr(right.poly(Pp))]}
    spR = frR.mm(*right.px(*CONFIG["RIGHT"]["selector_pivot"]))
    rff["selector_pivot_XZ"] = r1(spR)
    rff["dark_features_auto"] = dark_features(right, frR, AR)

    # ---------------- traces
    def outline_json(view, A, fr, extra=None, zname="Z"):
        d = {"view": view.name, "panel_box_sheet_px": list(view.box), "mirrored": view.mirror,
             "frame": "mm: X toward the muzzle, %s %s; X = 0 at the rearmost butt pad point, %s = 0 on the bore axis. "
                      "px: pixel-centre coords in the panel crop%s" % (
                          zname, "up" if zname == "Z" else "= gun left (image-down)", zname,
                          " (mirrored)" if view.mirror else ""),
             "px_per_mm": round(fr.s, 6), "bore_dir_px": [round(float(fr.u[0]), 6), round(float(fr.u[1]), 6)],
             "up_dir_px": [round(float(fr.n[0]), 6), round(float(fr.n[1]), 6)],
             "origin_px": [round(float(fr.p0[0]), 3), round(float(fr.p0[1]), 3)],
             "silhouette": [ring_json(r, fr.mm) for r in view.rings],
             "see_through_holes_px": view.kept_holes}
        if A is not None:
            d["gun_without_magazine"] = [ring_json(r, fr.mm) for r in A["gun"]]
            d["magazine"] = [ring_json(r, fr.mm) for r in A["mag"]]
            if "parts" in A:
                d["parts"] = {nm: [ring_json(r, fr.mm) for r in rr] for nm, rr in A["parts"].items()}
            d["face_features"] = {nm: {"px": [r1(p) for p in view.poly(Pp)],
                                       "mm": [r1(q) for q in fr.mm_arr(view.poly(Pp))]}
                                  for nm, Pp in view.cfg.get("face_features", {}).items()}
        if extra:
            d.update(extra)
        return d

    (TRACE / "LEFT_outline.json").write_text(json.dumps(outline_json(left, AL, frL), indent=1))
    (TRACE / "RIGHT_outline.json").write_text(json.dumps(outline_json(right, AR, frR), indent=1))
    (TRACE / "TOP_outline.json").write_text(json.dumps(outline_json(
        top, None, frT, {"width_profile_mm_X_Yleft_Yright": MT["width_profile_mm_every_5mm_X_Yleft_Yright"]},
        zname="Y"), indent=1))
    save_mask(left.sil, "LEFT_silhouette.png")
    save_mask(R.rings_to_mask(AL["gun"], left.sil.shape), "LEFT_gun_no_mag.png")
    save_mask(R.rings_to_mask(AL["mag"], left.sil.shape), "LEFT_magazine.png")
    save_mask(right.sil, "RIGHT_mirrored_silhouette.png")
    save_mask(R.rings_to_mask(AR["gun"], right.sil.shape), "RIGHT_mirrored_gun_no_mag.png")
    save_mask(R.rings_to_mask(AR["mag"], right.sil.shape), "RIGHT_mirrored_magazine.png")
    save_mask(top.sil, "TOP_silhouette.png")
    names = AL["names"]
    pal = np.array([[0, 0, 0]] + [PART_COLS.get(n, (128, 128, 128)) for n in names[1:]], np.uint8)
    Image.fromarray(pal[AL["lab"]]).save(TRACE / "LEFT_parts_labels.png")
    Image.fromarray(AL["lab"].astype(np.uint8)).save(TRACE / "LEFT_parts_index.png")
    (TRACE / "LEFT_parts_labels.json").write_text(json.dumps(
        {"index_png": "LEFT_parts_index.png (pixel value = index)", "colour_png": "LEFT_parts_labels.png",
         "labels": {str(i): n for i, n in enumerate(names)},
         "colours": {n: [int(c) for c in pal[i]] for i, n in enumerate(names)},
         "pixels": {n: int((AL["lab"] == i).sum()) for i, n in enumerate(names)}}, indent=1))

    measured = {
        "asset": "Compact SMG SM-01 (SMG01): reference measurement of the user's Sheet A",
        "source": "References/Guns/SMG/smg_sheetA.webp (1254x1254, AI-generated; panels LEFT, RIGHT, TOP, 3/4 FRONT "
                  "VIEW (LEFT))",
        "tool": "WorkFiles/guns/smg/tools/trace_reference.py (regenerates this file, trace/ and the overlay)",
        "frame": {"axes": "+X toward the muzzle, +Z up, +Y = gun left (right-handed)",
                  "origin": "X = 0 at the rearmost point of the butt pad, stock extended; Z = 0 on the bore axis "
                            "(direction = top rail tooth-top line; height = muzzle device / barrel centre line); "
                            "Y = 0 on the mid-plane",
                  "units": "mm unless the key ends in _px"},
        "sides": {
            "LEFT_panel_is_true_left": True,
            "evidence": "LEFT panel: charging handle knob at the front upper receiver (real pattern: left side); no "
                        "ejection port. RIGHT panel: the ejection port (rectangular window at the receiver top-middle) "
                        "and no knob (real pattern: port on the right). TOP (muzzle image-left, so gun left = "
                        "image-down for a camera above): the knob protrudes image-down = left. 3/4 FRONT VIEW (LEFT) "
                        "shows the knob. Selector levers on both sides (ambidextrous, as the prompt asks) at the same "
                        "X within %.1f mm. No panel is mirrored." % abs(feat_cmp["selector_pivot_X"]["RIGHT_minus_LEFT"]),
        },
        "scale": scale,
        "panels_sheet_px_x0_y0_x1_y1_inclusive": {k: list(v) for k, v in boxes.items()},
        "backdrop_fit_residual_sd": {"LEFT": round(left.bg_sd, 2), "RIGHT": round(right.bg_sd, 2),
                                     "TOP": round(top.bg_sd, 2)},
        "see_through_holes_px": {"LEFT": left.kept_holes, "RIGHT_mirrored": right.kept_holes, "TOP": top.kept_holes},
        "axis_fit_px": {"LEFT": frL.bore, "RIGHT_mirrored": frR.bore, "TOP": T["axis"]},
        "agreement": {"left_vs_right": agreement_lr, "top_vs_side": agreement_top,
                      "magazine_RIGHT": {k: MR[k] for k in ("X", "Z", "rake_deg_from_perpendicular_to_bore",
                                                            "width_front_to_back_perpendicular_to_axis",
                                                            "exposed_length_along_axis")}},
        "dimensions_LEFT": ML,
        "right_side_features": rff,
        "top_view": MT,
        "q34_reads": CONFIG["Q34"],
    }
    (OUT / "smg_measured.json").write_text(json.dumps(measured, indent=1))
    rows = [("LEFT: silhouette (magenta), parts (colours), face features (white), bore axis (red dashes)",
             left, AL, frL, None),
            ("RIGHT, mirrored: silhouette (magenta), magazine (yellow), face features (white), LEFT silhouette in "
             "RIGHT's frame (cyan)", right, AR, frR, [l2r(r) for r in left.rings]),
            ("TOP: silhouette (magenta), frame X axis = bore line (red dashes); gun left = image-down", top, None, frT,
             None)]
    make_overlay(rows, OUT / "SMG_TRACE_OVERLAY.png")
    zoom_tiles(rows)
    print(json.dumps({"px_per_mm": scale["px_per_mm"], "iou_lr": agreement_lr["iou_silhouette_frame_aligned"],
                      "ruler_cm": scale["sheet_ruler"]["implied_overall_length_cm_LEFT"],
                      "unassigned_px": int((AL["lab"] == names.index("unassigned")).sum())
                      if "unassigned" in names else 0,
                      "holes_L": [h["bbox_px"] for h in left.kept_holes],
                      "holes_R": [h["bbox_px"] for h in right.kept_holes]}, indent=1))


if __name__ == "__main__":
    main()
