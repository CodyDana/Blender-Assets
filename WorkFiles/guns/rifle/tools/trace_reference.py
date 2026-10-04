"""Trace and measure the AR-01 rifle reference sheet (References/Guns/Rifle/rifle_sheetAB.webp).

    py -3 -B WorkFiles/guns/rifle/tools/trace_reference.py

Regenerates everything the build uses as its 2D outline authority:
  WorkFiles/guns/rifle/scratch/crops/*.png        every panel cropped at full resolution (not committed)
  WorkFiles/guns/rifle/trace/*.png               binary masks (silhouette, rifle without magazine, magazine, parts)
  WorkFiles/guns/rifle/trace/*.json              outlines (sub-pixel marching squares, simplified) in px and in mm
  WorkFiles/guns/rifle/rifle_measured.json       all numbers (px/mm per view, crop boxes, agreement stats, dims)
  WorkFiles/guns/rifle/RIFLE_TRACE_OVERLAY.png   QA overlay (outlines on the reference crops)

Frames
  Panel px: (x right, y down), pixel-centre coordinates inside each panel crop (box in rifle_measured.json).
  Gun mm:   +X toward the muzzle, +Z up, +Y = the gun's LEFT side (right-handed). Origin X = 0 at the rearmost point of
            the butt plate, Z = 0 on the bore axis (barrel centre line), Y = 0 on the gun's mid-plane.
  Every view gets its own frame: its axis (LEFT/RIGHT: the bore = exposed barrel centre line; TOP: the gun's overall
  centre line), X = 0 at its rearmost point, scale s = px per mm such that its overall length is 880 mm.
  LEFT  : X along the bore toward the muzzle, Z = image up.   RIGHT: the panel is mirrored first, then the same.
  TOP   : X along the centre line, Y = image up (gun left for a camera above; see MEASUREMENT_NOTES.md).

Only numpy, scipy and Pillow are needed. Manual inputs (the seams between steel parts that are not on the silhouette,
the magazine cut, the selector lever face outline, and real see-through holes) are the CONFIG below; each was read off
zoomed, gridded crops and is accurate to about +-1 px.
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
SHEET = ROOT / "References" / "Guns" / "Rifle" / "rifle_sheetAB.webp"
OUT = ROOT / "WorkFiles" / "guns" / "rifle"
TRACE = OUT / "trace"
SCRATCH = OUT / "scratch"
CROPS = SCRATCH / "crops"

OVERALL_MM = 880.0          # chosen real-world overall length (butt plate to muzzle-brake tip), see notes
PANEL_NAMES = ["LEFT", "RIGHT", "TOP", "FRONT_3Q_RIGHT", "CU_RECEIVER_SELECTOR_RIGHT", "CU_DUSTCOVER_REARSIGHT",
               "CU_FRONTSIGHT_MUZZLE", "CU_MAGAZINE_LEFT", "CU_MAGAZINE_FRONT", "CU_GRIP_TRIGGER_LEFT",
               "CU_BUTTPLATE_END"]

# ------------------------------------------------------------------------------------------------ CONFIG
# Coordinates are px relative to the sheet point "origin" (the top-left used while reading the gridded zooms; the
# View converts them to its detected panel box). RIGHT coordinates are raw (un-mirrored).
CONFIG = {
    "LEFT": {
        "origin": (9, 21),
        "exclude_below_y": 236,               # the cm ruler and its labels start at y ~241
        # real see-through holes (checked on 12x gridded zooms): rod gap front, rod gap rear, gas tube / barrel gap,
        # front sight hood window, trigger guard opening, gap under the rear sight leaf
        "keep_hole_seeds": [(650, 84.5), (575, 83.5), (570, 66.5), (689, 61.5), (298, 118), (410, 43.5)],
        "fill_hole_seeds": [],
        "force_fg": [[(551, 47.5), (577, 47.5), (577, 52.5), (551, 52.5)],    # exposed gas tube top highlight
                     [(577, 48.5), (594, 48.5), (598, 52.5), (598, 56), (577, 56)],   # gas block top highlight
                     [(217, 69), (218, 61), (224, 54), (231, 50), (244, 50), (244, 69)]],   # dust cover rear
        "strict": [([(355, 220.5), (425, 220.5), (425, 234), (355, 234)], 100.0)],   # floor shadow under the magazine
        "handguard_split_y": 65.0,
        "barrel_probe": {"x": [622, 677], "y": 74.5},    # exposed barrel between gas block and front sight
        "mag_region": [(319.0, 100.5), (377.0, 100.5), (470, 200), (470, 245), (300, 245), (300, 140), (319.0, 136)],
        # steel part regions, first match wins; wood parts come from colour; magazine from mag_region
        # Check fixes (2026-10-04): the rear sight leaf overhangs the dust cover front (its rear end and notch plate
        # reach X ~448.6 mm, c2 shows the overhang), the front sight block's rear face is the dark seam at X ~806.5 mm
        # (config x 677.7), and the dark front strap of the pistol grip (X ~284-298.5 mm) is grip, not trigger guard
        # (whose rear leg starts at X ~299 mm, config x 260).
        "steel_regions": [
            ("butt_plate", [(0, 50), (40, 50), (40, 180), (0, 180)]),
            ("sling_swivel_rear", [(67, 151.5), (85, 151.5), (85, 163), (67, 163)]),
            ("rear_sight", [(379.5, 15), (388.5, 15), (388.5, 44.8), (379.5, 44.8)]),    # leaf overhang, Z > ~37
            ("dust_cover", [(212.5, 25), (388.5, 25), (388.5, 66.5), (272, 66.5), (262, 74.5), (212.5, 74.5)]),
            ("receiver", [(185, 25), (212.5, 25), (212.5, 74.5), (262, 74.5), (272, 66.5), (411.8, 66.5),
                          (411.8, 103.5), (185, 103.5)]),
            ("rear_sight", [(388.5, 20), (445.5, 20), (445.5, 66.5), (388.5, 66.5)]),
            ("gas_tube_rear_cap", [(445.5, 25), (455.5, 25), (455.5, 65.5), (445.5, 65.5)]),
            ("handguard_front_band", [(538.5, 30), (546, 30), (546, 100), (538.5, 100)]),
            ("gas_block", [(575, 30), (600, 30), (620.5, 60), (620.5, 95), (597, 95), (597, 64.5), (575, 64.5)]),
            ("gas_tube", [(546, 30), (575, 30), (575, 64.5), (546, 64.5)]),
            ("barrel", [(546, 64.5), (597, 64.5), (597, 83.2), (546, 83.2)]),
            ("barrel", [(620.5, 60), (677.7, 60), (677.7, 83.2), (620.5, 83.2)]),
            ("cleaning_rod", [(546, 83.2), (680.5, 83.2), (680.5, 95), (546, 95)]),
            ("front_sight_block", [(677.7, 20), (712.0, 20), (712.0, 100), (677.7, 100)]),
            ("muzzle_brake", [(712.0, 40), (760, 40), (760, 100), (712.0, 100)]),
            ("trigger", [(265.2, 103.5), (274, 103.5), (274, 112.9), (269.3, 112.9), (265.2, 108.0)]),   # blade top rear
            ("trigger", [(274, 103.5), (294, 103.5), (294, 127), (274, 127)]),
            ("pistol_grip", [(225, 104.4), (260, 104.4), (260, 190), (225, 190)]),        # dark front strap (below Z -35.7)
            ("trigger_guard", [(260, 103.5), (306.5, 103.5), (306.5, 145), (260, 145)]),
            ("mag_catch", [(306.5, 103.5), (321, 103.5), (321, 145), (306.5, 145)]),
        ],
        # face features (drawn on the side face, not on the silhouette): outline polygons
        "face_features": {
            "selector_lever": [(242, 78), (246, 76), (251, 76.5), (262, 76.5), (266, 74.5), (270, 71), (273, 69.5),
                               (304, 69.5), (308, 71.5), (307, 74), (300, 76.5), (285, 80), (270, 84), (256, 88),
                               (249, 88.5), (243, 86.5), (241.5, 82)],
            "selector_pivot": [(247 + 5.5 * math.cos(t), 81.5 + 5.5 * math.sin(t))
                               for t in np.linspace(0, 2 * math.pi, 24, endpoint=False)],
        },
    },
    "RIGHT": {
        "origin": (771, 20),
        "exclude_below_y": 236,
        "keep_hole_seeds": [(103, 84.5), (178, 83.5), (180, 67.5), (65, 63.5), (455, 118), (330, 45)],
        "handguard_split_y": 65.5,
        "barrel_probe": {"x": [85, 120], "y": 77.0},
        "steel_regions": [],
        "force_fg": [[(528, 63), (522, 56), (517, 51.5), (427, 51.5), (427, 60), (528, 63)],   # dust cover top
                     [(204, 52), (157, 52), (152, 57), (152, 63), (204, 63)]],                # gas tube / block top
        "strict": [([(317, 221.5), (392, 221.5), (392, 235), (317, 235)], 100.0)],         # floor shadow
        "mag_region": [(423.5, 100.5), (423.5, 137), (450, 137), (450, 245), (250, 245), (250, 200), (379, 100.5)],
    },
    "TOP": {
        "origin": (9, 323),
        "exclude_below_y": None,
        "barrel_probe": {"x": [616, 660]},
        # the soft drop shadow along the image-bottom side of the receiver reaches -48 below the backdrop (steel is
        # darker than -70 there); the knob at x ~400-415 keeps the normal threshold
        "strict": [([(199, 127.5), (399, 127.5), (399, 149), (199, 149)], 62.0),
                   ([(416, 127.5), (469, 127.5), (469, 149), (416, 149)], 62.0)],
        "keep_hole_seeds": [],
    },
}


# ------------------------------------------------------------------------------------------------ helpers
def load_sheet():
    return np.asarray(Image.open(SHEET).convert("RGB"))


def rings_out(rings, tol=0.25, min_area=2.0):
    out = []
    for r in rings:
        a = R.signed_area(r)
        if abs(a) < min_area:
            continue
        s = R.dp_simplify(r, tol)
        out.append(s)
    return out


def ring_json(r, to_mm=None):
    d = {"area_px": round(R.signed_area(r), 2), "kind": "outer" if R.signed_area(r) > 0 else "hole",
         "px": [[round(float(x), 3), round(float(y), 3)] for x, y in r]}
    if to_mm is not None:
        d["mm"] = [[round(float(a), 3), round(float(b), 3)] for a, b in (to_mm(x, y) for x, y in r)]
    return d


def save_mask(m, name):
    Image.fromarray((m * 255).astype(np.uint8)).save(TRACE / name)


class View:
    """One orthographic panel: soft field, silhouette mask, sub-pixel rings."""

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
            ex[int(cfg["exclude_below_y"] + cfg["origin"][1] - box[1]):] = True
        self.exclude = ex
        bg, sd = R.fit_background(L, S, exclude=ex)
        self.bg, self.bg_sd = bg, sd
        F = R.soft_field(L, S, bg, dl=cfg.get("dl", 40.0))
        F[ex] = 0.0
        F[:3, :] = F[-3:, :] = 0.0          # the panel's anti-aliased border against the white sheet
        F[:, :3] = F[:, -3:] = 0.0
        # force-foreground patches: steel surfaces whose top highlight matches the backdrop so closely that no
        # automatic criterion can see the edge; each patch was read off a 12x gridded zoom (edge to +-0.5 px)
        fg = [self.poly(P) for P in cfg.get("force_fg", [])]
        if fg:
            F = np.maximum(F, R.poly_coverage(fg, F.shape))
        # strict patches: where a soft contact shadow on the floor touches the gun, demand a much darker pixel
        for P, dl in cfg.get("strict", []):
            cov = R.poly_coverage([self.poly(P)], F.shape)
            Fs = R.soft_field(L, S, bg, dl=dl)
            F = F * (1 - cov) + Fs * cov
        m0 = F > 0.5
        m = R.drop_small(m0, 30)
        F[m0 & ~m] = np.minimum(F[m0 & ~m], 0.49)          # drop specks
        # Holes: fill everything enclosed except real see-through holes (auto "looks like backdrop" criterion OR a
        # keep seed). Pass 1 works on the holes of the mask itself. Pass 2 repeats on a closed mask (3x3 square and a
        # 7 px vertical line) so that the long bright highlight bands on the blued steel, which reach the backdrop at
        # their ends, still count as enclosed; when such a hole is filled, its bridging pixels are filled with it
        # (never pixels of a kept real hole). Pass 3 fills whatever enclosed specks remain.
        seeds = [self.px(sx, sy) for sx, sy in cfg.get("keep_hole_seeds", [])]
        fills = [self.px(sx, sy) for sx, sy in cfg.get("fill_hole_seeds", [])]
        Ld = L - bg
        kept, keptmask, filled = [], np.zeros_like(m), 0

        def classify(h):
            area = int(h.sum())
            hi = ndi.binary_erosion(h)
            r = Ld[hi] if hi.sum() > 2 else Ld[h]
            auto = area >= 6 and abs(np.median(r)) < 10 and np.std(r) < 7 and np.median(S[h]) < 5
            auto = auto and cfg.get("auto_holes", False)
            if any(h[max(0, int(round(sy)) - 2):int(round(sy)) + 3,
                     max(0, int(round(sx)) - 2):int(round(sx)) + 3].any() for sx, sy in fills):
                return False, False, area, r
            seeded = area >= 6 and any(h[max(0, int(round(sy)) - 3):int(round(sy)) + 4,
                           max(0, int(round(sx)) - 3):int(round(sx)) + 4].any() for sx, sy in seeds)
            return auto, seeded, area, r

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
                auto, seeded, area, r = classify(h)
                if auto or seeded:
                    ys, xs = np.nonzero(h)
                    kept.append({"area_px": area, "bbox_px": [int(xs.min()), int(ys.min()), int(xs.max()),
                                                              int(ys.max())],
                                 "by": "seed" if seeded else "auto", "median_dL": round(float(np.median(r)), 1)})
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
        self.rings = rings_out(R.marching_squares(F))
        self.sil = R.rings_to_mask(self.rings, F.shape)

    def px(self, x, y):
        """CONFIG coords (relative to cfg origin, un-mirrored) -> this view's panel coords (mirrored if needed)."""
        ox, oy = self.cfg.get("origin", self.box[:2])
        x = x + ox - self.box[0]
        y = y + oy - self.box[1]
        return ((self.W - 1 - x) if self.mirror else x, y)

    def poly(self, P):
        return [self.px(x, y) for x, y in P]


MIN_PIECE_PX = 40        # a part's detached piece smaller than this (and not its largest) is a sliver
MIN_HOLE_PX = 20         # smaller part holes are seam noise


def part_rings(F, labels, k, sigma=0.6):
    """Sub-pixel rings of part k: outer edges from the soft field F, seams from a smoothed nearest-label map.
    Outer rings under MIN_PIECE_PX (except the part's largest) and holes under MIN_HOLE_PX are dropped: they are
    slivers of the soft seam field, not part extents (check fix 2026-10-04)."""
    cov = ndi.gaussian_filter((labels == k).astype(float), sigma)
    rr = rings_out(R.marching_squares(np.minimum(F, cov)))
    outers = [r for r in rr if R.signed_area(r) > 0]
    if not outers:
        return rr
    amax = max(R.signed_area(r) for r in outers)
    return [r for r in rr if (R.signed_area(r) > 0 and (R.signed_area(r) >= MIN_PIECE_PX or R.signed_area(r) == amax))
            or (R.signed_area(r) < 0 and -R.signed_area(r) >= MIN_HOLE_PX)]


def extend_labels(lab, sil):
    """Give every pixel the label of the nearest labelled silhouette pixel (so seams continue into the backdrop)."""
    idx = ndi.distance_transform_edt(lab == 0, return_distances=False, return_indices=True)
    ext = lab[idx[0], idx[1]]
    return ext


def wood_mask(view, sil):
    S = ndi.median_filter(view.S, 3)
    w = (S >= 18) & sil
    w = ndi.binary_opening(w, iterations=1)
    w = R.drop_small(w, 50)
    w = ndi.binary_fill_holes(w)
    return w & sil


# ------------------------------------------------------------------------------------------------ side analysis
def side_parts(view, cfg):
    """Magazine mask: silhouette inside the hand-placed magazine cut region."""
    sil = view.sil
    magcov = R.poly_coverage([view.poly(cfg["mag_region"])], sil.shape) > 0.5
    mag = R.drop_small(sil & magcov, 30)
    return mag


def label_left_parts(view, cfg, mag):
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
    w = wood_mask(view, sil) & ~mag
    wl, wn = ndi.label(w)
    for i in range(1, wn + 1):
        c = wl == i
        if c.sum() < 50:
            continue
        ys, xs = np.nonzero(c)
        cx, cy = xs.mean(), ys.mean()
        if cx < 200:
            add("stock", c)
        elif cx < 280 and cy > 100:
            add("pistol_grip", c)
        elif cx > 405:
            # the two handguards touch at their ends in the mask; split on the dark seam line between them
            _, ysplit = view.px(0, cfg["handguard_split_y"])
            yy = np.arange(sil.shape[0])[:, None]
            add("handguard_upper", c & (yy < ysplit))
            add("handguard_lower", c & (yy >= ysplit))
        else:
            add("wood_other", c)
    steel = sil & (lab == 0)
    for nm, P in cfg["steel_regions"]:
        cov = R.poly_coverage([view.poly(P)], sil.shape) > 0.5
        add(nm, steel & cov & (lab == 0))
    # leftover silhouette pixels (mostly the dark anti-aliased rims of the wood parts) join the nearest part
    rest = sil & (lab == 0)
    if rest.any() and (lab > 0).any():
        dist, idx = ndi.distance_transform_edt(lab == 0, return_indices=True)
        near = lab[idx[0], idx[1]]
        take = rest & (dist <= 3.0)
        lab[take] = near[take]
    # small detached pieces of a part (under MIN_PIECE_PX, not the part's largest piece) are slivers cut off by a
    # region boundary: they join the nearest other part (check fix 2026-10-04: they had been read as part extents)
    # (the magazine keeps its hand-placed cut: it neither gives nor takes pixels here)
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
            if not other.any():
                continue
            _, idx = ndi.distance_transform_edt(~other, return_indices=True)
            near = lab[idx[0], idx[1]]
            lab[comp] = near[comp]
    add("unassigned", sil & (lab == 0))
    return lab, names


# ------------------------------------------------------------------------------------------------ alignment
def align_similarity(src_rings, dst_mask, shape, init):
    """Find s, theta, tx, ty so that transformed src rings best overlap dst (maximise IoU)."""
    def tf(params, P):
        s, th, tx, ty = params
        c, sn = math.cos(th), math.sin(th)
        return np.c_[s * (c * P[:, 0] - sn * P[:, 1]) + tx, s * (sn * P[:, 0] + c * P[:, 1]) + ty]

    def cost(params):
        m = R.rings_to_mask([tf(params, r) for r in src_rings], shape, ss=2)
        return -R.iou(m, dst_mask)

    res = minimize(cost, init, method="Nelder-Mead",
                   options={"xatol": 1e-4, "fatol": 1e-5, "maxiter": 600,
                            "initial_simplex": [init, init + [0.01, 0, 0, 0], init + [0, 0.004, 0, 0],
                                                init + [0, 0, 1.5, 0], init + [0, 0, 0, 1.5]]})
    return res.x, -res.fun, tf


# ------------------------------------------------------------------------------------------------ ring geometry
def hits_v(rings, x):
    """Sorted y of all ring crossings with the vertical line at x (half-open rule, even-odd pairs = inside)."""
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
    """The inside interval (lo, hi) of sorted crossings that contains ref, else None."""
    for i in range(0, len(hits) - 1, 2):
        if hits[i] <= ref <= hits[i + 1]:
            return float(hits[i]), float(hits[i + 1])
    return None


def outer(rings):
    return [r for r in rings if R.signed_area(r) > 0]


def bbox(rings):
    P = np.vstack(outer(rings))
    return float(P[:, 0].min()), float(P[:, 0].max()), float(P[:, 1].min()), float(P[:, 1].max())


class Frame:
    """Panel px <-> gun mm for one view. u = unit bore direction (toward the muzzle) in image coords; n = u turned to
    point image-up (= +Z in the side views, +Y in the top view)."""

    def __init__(self, s, u, p0):
        self.s = float(s)
        self.u = np.array(u, float) / np.hypot(*u)
        self.n = np.array([self.u[1], -self.u[0]])
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
    """One measurement: value and its 1-sigma uncertainty (mm) from the edge types (px) at scale s (px/mm)."""
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


# ------------------------------------------------------------------------------------------------ side view analysis
def analyse_side(view, cfg, with_parts):
    mag = side_parts(view, cfg)
    lab, names = label_left_parts(view, cfg, mag)
    ext = extend_labels(lab, view.sil)
    parts = {}
    for k, nm in enumerate(names):
        if k == 0 or not (lab == k).any():
            continue
        if not with_parts and nm not in ("magazine", "stock", "pistol_grip", "handguard_upper", "handguard_lower"):
            continue
        parts[nm] = part_rings(view.F, ext, k)
    magk = names.index("magazine")
    cov_rifle = ndi.gaussian_filter((ext != magk).astype(float), 0.6)
    rifle = rings_out(R.marching_squares(np.minimum(view.F, cov_rifle)))
    return {"sil": view.rings, "mag": parts.get("magazine", []), "rifle": rifle, "parts": parts, "lab": lab,
            "names": names, "mag_mask": mag}


def side_frame(view):
    """Bore axis from the exposed barrel between the gas block and the front sight block; scale from 880 mm."""
    xs, tops, bots = [], [], []
    bp = view.cfg["barrel_probe"]
    lo, hi = sorted((view.px(bp["x"][0], 0)[0], view.px(bp["x"][1], 0)[0]))
    yref = view.px(0, bp["y"])[1]
    for x in np.arange(lo, hi + 0.01, 1.0):
        sp = span(hits_v(view.rings, x), yref)
        if sp is None:
            continue
        xs.append(x)
        tops.append(sp[0])
        bots.append(sp[1])
    xs, tops, bots = map(np.array, (xs, tops, bots))
    a, b, rms = R.fit_line(xs, (tops + bots) / 2)
    _, _, rmst = R.fit_line(xs, tops)
    _, _, rmsb = R.fit_line(xs, bots)
    u = np.array([1.0, a]) / math.hypot(1.0, a)
    allp = np.vstack(outer(view.rings))
    t = allp @ u
    p_on = np.array([xs.mean(), a * xs.mean() + b])
    L_px = float(t.max() - t.min())
    p0 = p_on + (t.min() - p_on @ u) * u
    fr = Frame(L_px / OVERALL_MM, u, p0)
    fr.bore = {"slope": a, "slope_deg": math.degrees(math.atan(a)), "intercept_y": b, "rms_mid_px": rms,
               "rms_top_px": rmst, "rms_bottom_px": rmsb, "diameter_px": float(np.mean(bots - tops)),
               "diameter_sd_px": float(np.std(bots - tops)), "x_range_px": [float(xs.min()), float(xs.max())],
               "n_columns": int(len(xs))}
    return fr, L_px


def part_box_mm(fr, rings):
    P = fr.mm_arr(np.vstack(outer(rings)))
    return float(P[:, 0].min()), float(P[:, 0].max()), float(P[:, 1].min()), float(P[:, 1].max())


def col_span_mm(fr, rings, X, Zref):
    """Inside interval along Z of rings at station X (mm) containing Zref -> (bottom Z, top Z) or None."""
    p = fr.px(X, Zref)
    sp = span(hits_v(rings, p[0]), p[1])
    if sp is None:
        return None
    return fr.mm(p[0], sp[1])[1], fr.mm(p[0], sp[0])[1]


def col_extent(fr, rings, X):
    """(bottom Z, top Z) of the outermost silhouette crossings at station X, or None."""
    p = fr.px(X, 0.0)
    h = hits_v(rings, p[0])
    if len(h) < 2:
        return None
    return fr.mm(p[0], h[-1])[1], fr.mm(p[0], h[0])[1]


def row_span_mm(fr, rings, Z, Xref):
    """Inside interval along X of rings at height Z (mm) containing Xref -> (rear X, front X) or None."""
    p = fr.px(Xref, Z)
    sp = span(hits_h(rings, p[1]), p[0])
    if sp is None:
        return None
    return fr.mm(sp[0], p[1])[0], fr.mm(sp[1], p[1])[0]


def measure_left(view, A, fr):
    s = fr.s
    P, cfg = A["parts"], CONFIG["LEFT"]
    out = {}
    bx = {k: part_box_mm(fr, v) for k, v in P.items() if outer(v)}
    sil = A["sil"]
    X0, X1, Z0, Z1 = part_box_mm(fr, sil)
    rX0, rX1, rZ0, rZ1 = part_box_mm(fr, A["rifle"])
    out["overall"] = {
        "length": M(X1 - X0, s, how="rearmost butt plate point to muzzle brake tip, along the bore (set = 880)"),
        "height_with_magazine": M(Z1 - Z0, s, how="front sight hood top to magazine floor plate bottom"),
        "height_without_magazine": M(rZ1 - rZ0, s, how="front sight hood top to pistol grip bottom"),
        "top_Z": M(Z1, s, ("sil",)), "bottom_Z_with_mag": M(Z0, s, ("sil",)),
        "bottom_Z_without_mag": M(rZ0, s, ("sil",)),
    }
    # ---------------- barrel, gas tube, cleaning rod
    bo = fr.bore
    bar = {"diameter": M(bo["diameter_px"] / s, s, how="mean top-bottom edge distance of the exposed barrel between "
                         "gas block and front sight block (%d columns, sd %.2f px)" % (bo["n_columns"],
                                                                                      bo["diameter_sd_px"]))}
    d2 = []
    for X in np.arange(bx["gas_tube"][0] + 4, bx["gas_block"][0] - 2, 1.0):
        sp = col_span_mm(fr, sil, X, 0.0)
        if sp:
            d2.append(sp[1] - sp[0])
    bar["diameter_behind_gas_block"] = M(np.median(d2), s, how="same, between handguard front band and gas block "
                                                                "(between the two see-through gaps)")
    rf = bx["receiver"][1]
    bar["receiver_front_face_X"] = M(rf, s, ("seam",), how="seam receiver / lower handguard")
    bar["muzzle_end_X"] = M(bx["muzzle_brake"][0], s, ("seam",),
                            how="barrel muzzle taken at the brake rear face (front of the front sight block collar)")
    bar["receiver_face_to_muzzle"] = M(bx["muzzle_brake"][0] - rf, s, ("seam", "seam"))
    bar["exposed_between_handguard_band_and_fsb"] = M(bx["front_sight_block"][0] - bx["handguard_front_band"][1], s,
                                                      ("seam", "seam"))
    out["barrel"] = bar
    gt = []
    zc = (bx["gas_tube"][2] + bx["gas_tube"][3]) / 2
    for X in np.arange(bx["handguard_front_band"][1] + 1, bx["gas_block"][0] - 1, 1.0):
        sp = col_span_mm(fr, sil, X, zc)
        if sp:
            gt.append(sp)
    gt = np.array(gt)
    gb = bx["gas_block"]
    out["gas_tube"] = {
        "diameter_exposed": M(np.median(gt[:, 1] - gt[:, 0]), s, ("sil", "est"),
                              how="exposed vented section; its top edge is a backdrop-coloured highlight "
                                  "(force_fg patch), so that edge is +-1-2 px"),
        "axis_Z": M(np.median(gt.mean(axis=1)), s, ("sil", "est")),
        "rear_X_visible": M(bx["rear_sight"][1], s, ("seam",), how="front of the rear sight block"),
        "exposed_length": M(gb[0] - bx["handguard_front_band"][1], s, ("seam", "seam"),
                            how="handguard front band to gas block shoulder"),
        "gas_block": {"X": r1(gb[:2]), "Z": r1(gb[2:]), "length": M(gb[1] - gb[0], s, ("seam", "seam")),
                      "top_Z": M(gb[3], s, ("sil",)), "bottom_Z_incl_lug": M(gb[2], s, ("sil",))},
    }
    cr = []
    for X in np.arange(bx["barrel"][1] - 50, bx["barrel"][1] - 2, 1.0):
        sp = col_span_mm(fr, sil, X, (bx["cleaning_rod"][2] + bx["cleaning_rod"][3]) / 2)
        if sp:
            cr.append(sp)
    cr = np.array(cr)
    out["cleaning_rod"] = {"diameter": M(np.median(cr[:, 1] - cr[:, 0]), s), "axis_Z": M(np.median(cr.mean(axis=1)), s),
                           "X": r1([bx["cleaning_rod"][0], bx["front_sight_block"][0]]),
                           "note": "runs under the barrel from the lower handguard to the front sight block lug"}
    # ---------------- receiver + dust cover + rear sight
    rcv = bx["receiver"]
    rb = []
    xa = fr.mm(*view.px(cfg["mag_region"][1][0] + 2, 90))[0]       # just ahead of the magazine's top front corner
    for X in np.arange(xa, rf - 1.5, 0.5):
        sp = col_span_mm(fr, sil, X, -10.0)
        if sp:
            rb.append(sp[0])
    rec_bottom = float(np.median(rb))
    seam_top = fr.mm(*view.px(400, 66.5))[1]
    dc = bx["dust_cover"]
    out["receiver"] = {
        "X": r1([rcv[0], rf]),
        "length": M(rf - rcv[0], s, ("sil", "seam"), how="rear end cap (stock socket) to front face"),
        "side_plate_rear_X": M(fr.mm(*view.px(212.5, 85))[0], s, ("seam",)),
        "bottom_Z": M(rec_bottom, s, ("sil",), how="silhouette bottom between magazine and lower handguard"),
        "side_top_Z": M(seam_top, s, ("seam",), how="dust cover / receiver seam at the front"),
        "height_side_plate": M(seam_top - rec_bottom, s, ("seam", "sil")),
        "height_incl_dust_cover": M(dc[3] - rec_bottom, s),
        "rear_cap_Z": r1(rcv[2:]),
    }
    out["dust_cover"] = {"X": r1(dc[:2]), "length": M(dc[1] - dc[0], s, ("sil", "seam")), "top_Z": M(dc[3], s, ("sil",)),
                         "height_above_receiver_side": M(dc[3] - seam_top, s, ("sil", "seam"))}
    rs = bx["rear_sight"]
    leaf_top = rs[3]
    xs_ = []
    for dz in np.linspace(0.6, 3.0, 9):
        hh = hits_h(P["rear_sight"], fr.px(0, leaf_top - dz)[1])
        if len(hh) >= 2:
            xs_ += [fr.mm(hh[0], 0)[0], fr.mm(hh[-1], 0)[0]]
    lr = (min(xs_), max(xs_)) if xs_ else None
    out["rear_sight"] = {"block_X": r1(rs[:2]), "block_length": M(rs[1] - rs[0], s, ("seam", "seam")),
                         "leaf_top_Z": M(leaf_top, s, ("sil",)),
                         "leaf_X_span_top_3mm": r1(lr) if lr else None,
                         "notch_X_est": M(lr[0] if lr else rs[0], s, ("est",),
                                          how="rear end of the leaf top (the notch itself is not resolved)")}
    # ---------------- handguards, bands
    for nm in ("handguard_upper", "handguard_lower"):
        b = bx[nm]
        hh = []
        for X in np.linspace(b[0] + 8, b[1] - 8, 25):
            sp = col_span_mm(fr, P[nm], X, (b[2] + b[3]) / 2)
            if sp:
                hh.append(sp)
        hh = np.array(hh)
        out[nm] = {"X": r1(b[:2]), "length": M(b[1] - b[0], s, ("seam", "seam")), "Z": r1(b[2:]),
                   "height_max": M(b[3] - b[2], s, ("sil", "seam")),
                   "height_median": M(np.median(hh[:, 1] - hh[:, 0]), s, ("sil", "seam"))}
    out["gas_tube_rear_cap"] = {"X": r1(bx["gas_tube_rear_cap"][:2]), "Z": r1(bx["gas_tube_rear_cap"][2:])}
    hb = bx["handguard_front_band"]
    out["handguard_front_band"] = {"X": r1(hb[:2]), "Z": r1(hb[2:]), "length": M(hb[1] - hb[0], s, ("seam", "seam"))}
    # ---------------- front sight block, muzzle brake
    fs = bx["front_sight_block"]
    hood = []
    for Z in np.linspace(fs[3] - 1.5, fs[3] - 8, 8):
        hh = hits_h(P["front_sight_block"], fr.px(0, Z)[1])
        if len(hh) >= 2:
            hood.append((fr.mm(hh[0], 0)[0], fr.mm(hh[-1], 0)[0]))
    hood = np.array(hood)
    out["front_sight_block"] = {
        "X": r1(fs[:2]), "length_incl_front_collar": M(fs[1] - fs[0], s, ("seam", "seam")),
        "hood_top_Z": M(fs[3], s, ("sil",)), "bottom_Z_incl_rod_lug": M(fs[2], s, ("sil",)),
        "hood_top_X_span": r1([hood[:, 0].mean(), hood[:, 1].mean()]),
        "hood_centre_X": M(float(hood.mean()), s, ("sil", "sil")),
        "hood_width_side": M(float(np.mean(hood[:, 1] - hood[:, 0])), s),
        "window_px": [h for h in view.kept_holes if h["bbox_px"][0] > view.px(670, 0)[0]
                      and h["bbox_px"][3] < view.px(0, 70)[1]],
    }
    mb = bx["muzzle_brake"]
    hgt = []
    for X in np.linspace(mb[0] + 1, mb[0] + 8, 8):
        sp = col_span_mm(fr, P["muzzle_brake"], X, (mb[2] + mb[3]) / 2)
        if sp:
            hgt.append(sp[1] - sp[0])
    pts = []
    for Z in np.linspace(mb[2] + 1.0, mb[3] - 1.0, 15):
        hh = hits_h(P["muzzle_brake"], fr.px(0, Z)[1])
        if len(hh):
            pts.append((fr.mm(hh[-1], fr.px(0, Z)[1])[0], Z))
    pts = np.array(pts)
    k, c, rms = R.fit_line(pts[:, 1], pts[:, 0])
    out["muzzle_brake"] = {"X": r1(mb[:2]), "length": M(mb[1] - mb[0], s, ("seam", "sil")), "Z": r1(mb[2:]),
                           "height": M(np.median(hgt), s),
                           "front_face_angle_from_vertical_deg": round(math.degrees(math.atan(-k)), 1),
                           "front_face_note": "front cut slopes back from the bottom lip (front) to the top; "
                                              "positive = bottom ahead of the top",
                           "front_face_fit_rms_mm": round(rms, 2)}
    # ---------------- pistol grip
    g = bx["pistol_grip"]
    fe, re_ = [], []
    for Z in np.linspace(g[3] - 8, g[2] + 10, 30):
        hh = hits_h(P["pistol_grip"], fr.px(0, Z)[1])
        if len(hh) < 2:
            continue
        re_.append((Z, fr.mm(hh[0], 0)[0]))
        fe.append((Z, fr.mm(hh[-1], 0)[0]))
    fe, re_ = np.array(fe), np.array(re_)
    kf, cf, rf_ = R.fit_line(fe[:, 0], fe[:, 1])
    kr, cr_, rr_ = R.fit_line(re_[:, 0], re_[:, 1])
    ang_f, ang_r = math.degrees(math.atan(kf)), math.degrees(math.atan(kr))
    axis_ang = (ang_f + ang_r) / 2
    width_h = float(np.median(fe[:, 1] - re_[:, 1]))
    out["pistol_grip"] = {
        "X": r1(g[:2]), "Z": r1(g[2:]),
        "front_edge_rake_from_vertical_deg": round(ang_f, 1), "rear_edge_rake_from_vertical_deg": round(ang_r, 1),
        "axis_rake_from_vertical_deg": round(axis_ang, 1),
        "angle_between_grip_axis_and_bore_deg": round(90 - axis_ang, 1),
        "width_horizontal_median": M(width_h, s),
        "width_perpendicular_to_axis": M(width_h * math.cos(math.radians(axis_ang)), s),
        "length_along_axis": M((g[3] - g[2]) / math.cos(math.radians(axis_ang)), s, ("seam", "sil"),
                               how="receiver bottom seam to grip bottom, along the grip axis"),
        "bottom_Z": M(g[2], s, ("sil",)), "edge_fit_rms_mm": [round(rf_, 2), round(rr_, 2)],
        "note": "rake = how far the grip leans back (bottom toward the butt) from the perpendicular to the bore; "
                "X = k*Z + c fits of the front and rear edges",
    }
    # ---------------- trigger guard, trigger, mag catch
    tg, tr, mc = bx["trigger_guard"], bx["trigger"], bx["mag_catch"]
    out["trigger_guard"] = {"X": r1(tg[:2]), "length": M(tg[1] - tg[0], s), "bottom_Z": M(tg[2], s, ("sil",)),
                            "drop_below_receiver_bottom": M(rec_bottom - tg[2], s),
                            "opening_px": [h for h in view.kept_holes if h["area_px"] > 400]}
    out["trigger"] = {"X": r1(tr[:2]), "bottom_Z": M(tr[2], s, ("sil",))}
    out["mag_catch"] = {"X": r1(mc[:2]), "Z": r1(mc[2:]), "bottom_Z": M(mc[2], s, ("sil",)),
                        "gap_to_magazine_rear_at_receiver": M(bx["magazine"][0] - mc[1], s, ("seam", "sil"))}
    # ---------------- stock + butt plate
    st, bp = bx["stock"], bx["butt_plate"]
    top_pts, bot_pts = [], []
    for X in np.arange(st[0] + 0.5, st[1] - 0.5, 1.0):
        x = fr.px(X, 0)[0]
        h = hits_v(P["stock"], x)
        if len(h) >= 2:
            top_pts.append((X, fr.mm(x, h[0])[1]))
            bot_pts.append((X, fr.mm(x, h[-1])[1]))
    top_pts, bot_pts = np.array(top_pts), np.array(bot_pts)
    # heel = highest top point within 10 mm of the wood's rear end, toe = lowest bottom point within 25 mm (the rear
    # seam to the butt plate is slanted, so the first columns cut only part of the height)
    rr = top_pts[:, 0] < st[0] + 10
    heel = top_pts[rr][np.argmax(top_pts[rr][:, 1])]
    rr = bot_pts[:, 0] < st[0] + 25
    toe = bot_pts[rr][np.argmin(bot_pts[rr][:, 1])]
    # the slanted end seams also cut the first / last columns short; keep columns with > 30 % of the max height
    full = (top_pts[:, 1] - bot_pts[:, 1]) > 0.3 * (top_pts[:, 1] - bot_pts[:, 1]).max()
    top_pts, bot_pts = top_pts[full], bot_pts[full]
    Ls = st[1] - st[0]
    sel = (top_pts[:, 0] > st[0] + 0.4 * Ls) & (top_pts[:, 0] < st[0] + 0.85 * Ls)
    comb = top_pts[sel][np.argmax(top_pts[sel][:, 1])]
    sel2 = (top_pts[:, 0] > comb[0]) & (top_pts[:, 0] < st[1] - 8)
    wrist = top_pts[sel2][np.argmin(top_pts[sel2][:, 1])]
    sel3 = (top_pts[:, 0] > st[0] + 5) & (top_pts[:, 0] < comb[0] - 15)
    kc, cc, rc = R.fit_line(top_pts[sel3][:, 0], top_pts[sel3][:, 1])
    sel4 = (bot_pts[:, 0] > st[0] + 15) & (bot_pts[:, 0] < st[1] - 10)
    kb, cb, rb_ = R.fit_line(bot_pts[sel4][:, 0], bot_pts[sel4][:, 1])
    rear = []
    for Z in np.linspace(bp[2] + 4, bp[3] - 4, 20):
        y = fr.px(0, Z)[1]
        h = hits_h(P["butt_plate"], y)
        if len(h):
            rear.append((Z, fr.mm(h[0], y)[0]))
    rear = np.array(rear)
    kbp, cbp, rbp = R.fit_line(rear[:, 0], rear[:, 1])
    thick = []
    for Z in np.linspace(bp[2] + 6, bp[3] - 6, 15):
        y = fr.px(0, Z)[1]
        h = hits_h(P["butt_plate"], y)
        if len(h) >= 2:
            thick.append(fr.mm(h[-1], y)[0] - fr.mm(h[0], y)[0])
    out["stock"] = {
        "X_wood": r1(st[:2]),
        "length_butt_to_receiver": M(st[1] - X0, s, ("sil", "seam"),
                                     how="rearmost butt plate point to the wood / receiver-cap seam"),
        "heel_Z": M(heel[1], s, ("sil",), how="top rear corner of the wood"),
        "toe_Z": M(toe[1], s, ("sil",), how="bottom rear corner of the wood"),
        "comb_nose": {"X": round(float(comb[0]), 1), "Z": M(comb[1], s, ("sil",))},
        "wrist_low_point": {"X": round(float(wrist[0]), 1), "Z": M(wrist[1], s, ("sil",))},
        "comb_line_slope_deg": round(math.degrees(math.atan(kc)), 2), "comb_line_fit_rms_mm": round(rc, 2),
        "bottom_line_slope_deg": round(math.degrees(math.atan(kb)), 2), "bottom_line_fit_rms_mm": round(rb_, 2),
        "height_at_butt_wood": M(heel[1] - toe[1], s),
        "drop_at_heel_below_bore": M(-heel[1], s), "drop_at_comb_below_bore": M(-comb[1], s),
        "note": "comb = highest top point of the stock ahead of the butt; wrist = the dip behind the receiver; "
                "negative Z = below the bore",
        "profile_top_mm": [[round(float(a), 1), round(float(b), 2)] for a, b in top_pts[::4]],
        "profile_bottom_mm": [[round(float(a), 1), round(float(b), 2)] for a, b in bot_pts[::4]],
    }
    out["butt_plate"] = {"X": r1(bp[:2]), "Z": r1(bp[2:]), "height": M(bp[3] - bp[2], s),
                         "thickness_side_view": M(float(np.median(thick)), s, ("sil", "seam")),
                         "rear_face_tilt_deg": round(math.degrees(math.atan(kbp)), 1),
                         "rear_face_note": "fit X = k*Z + c of the rear face; positive angle = the top (heel) is "
                                           "further forward than the toe",
                         "rear_face_fit_rms_mm": round(rbp, 2)}
    sw = bx["sling_swivel_rear"]
    out["sling_swivel_rear"] = {"X": r1(sw[:2]), "Z": r1(sw[2:])}
    out["magazine"] = measure_mag(view, fr, A["mag"], bx["mag_catch"])
    out["heights"] = {
        "bore_above_receiver_bottom": M(-rec_bottom, s, ("sil", "sil")),
        "bore_above_grip_bottom": M(-g[2], s, ("sil", "sil")),
        "bore_above_magazine_bottom": M(-Z0, s, ("sil", "sil")),
        "dust_cover_top_above_bore": M(dc[3], s, ("sil", "sil")),
        "front_sight_hood_top_above_bore": M(fs[3], s, ("sil", "sil")),
        "rear_sight_leaf_top_above_bore": M(leaf_top, s, ("sil", "sil")),
        "sight_radius_est": M(out["front_sight_block"]["hood_centre_X"]["mm"] - out["rear_sight"]["notch_X_est"]["mm"],
                              s, ("est", "sil"), how="rear leaf rear end to front hood centre"),
        "note": "the front post is hidden inside the hood in the side views; the hood top is an upper bound for the "
                "sight line at the muzzle end",
    }
    ff = {}
    for nm, Pp in cfg["face_features"].items():
        Q = np.array(view.poly(Pp))
        Qm = fr.mm_arr(Q)
        ff[nm] = {"X": r1([Qm[:, 0].min(), Qm[:, 0].max()]), "Z": r1([Qm[:, 1].min(), Qm[:, 1].max()]),
                  "outline_px": [[round(float(a), 2), round(float(b), 2)] for a, b in Q],
                  "outline_mm": [[round(float(a), 2), round(float(b), 2)] for a, b in Qm]}
    out["face_features"] = ff
    out["part_boxes_mm_X0_X1_Z0_Z1"] = {k: [round(v, 2) for v in b] for k, b in bx.items()}
    return out


def measure_mag(view, fr, mag_rings, catch_box):
    s = fr.s
    Pm = fr.mm_arr(np.vstack(outer(mag_rings)))
    X0, X1, Z0, Z1 = Pm[:, 0].min(), Pm[:, 0].max(), Pm[:, 1].min(), Pm[:, 1].max()
    tip = Pm[np.argmax(Pm[:, 0])]                 # floor plate front corner
    lowest = Pm[np.argmin(Pm[:, 1])]              # floor plate rear-bottom corner
    front, rear = [], []
    for Z in np.linspace(Z1 - 3, tip[1] + 10, 40):
        y = fr.px(0, Z)[1]
        h = hits_h(outer(mag_rings), y)
        if len(h) >= 2:
            rear.append(fr.mm(h[0], y))
            front.append(fr.mm(h[-1], y))
    front, rear = np.array(front), np.array(rear)
    cxf, czf, rfr, resf = R.fit_circle(front[:, 0], front[:, 1])
    cxr, czr, rre, resr = R.fit_circle(rear[:, 0], rear[:, 1])
    A = np.r_[front, rear]
    w = np.r_[np.ones(len(front)), np.zeros(len(rear))]

    def cost(p):
        d = np.hypot(A[:, 0] - p[0], A[:, 1] - p[1])
        return np.sum((d[w == 1] - d[w == 1].mean()) ** 2) + np.sum((d[w == 0] - d[w == 0].mean()) ** 2)

    res = minimize(cost, [(cxf + cxr) / 2, (czf + czr) / 2], method="Nelder-Mead")
    cx, cz = res.x
    d = np.hypot(A[:, 0] - cx, A[:, 1] - cz)
    R1, R2 = d[w == 1].mean(), d[w == 0].mean()
    rms_c = math.sqrt(res.fun / len(A))
    Rm = (R1 + R2) / 2
    top_mid = (front[0] + rear[0]) / 2
    bot_mid = (lowest + tip) / 2
    a0 = math.atan2(top_mid[1] - cz, top_mid[0] - cx)
    a1 = math.atan2(bot_mid[1] - cz, bot_mid[0] - cx)
    rib = mag_ribs(view, fr, cx, cz, R1, R2, a0, a1)
    return {
        "X": r1([X0, X1]), "Z": r1([Z0, Z1]), "top_Z_receiver_cut": M(Z1, s, ("seam",)),
        "front_edge_circle": {"centre_XZ": r1([cxf, czf]), "radius": M(rfr, s, extra_unc=resf), "rms_mm": round(resf, 2)},
        "rear_edge_circle": {"centre_XZ": r1([cxr, czr]), "radius": M(rre, s, extra_unc=resr), "rms_mm": round(resr, 2)},
        "concentric_fit": {"centre_XZ": r1([cx, cz]), "R_front_concave": round(float(R1), 1),
                           "R_rear_convex": round(float(R2), 1), "rms_mm": round(rms_c, 2),
                           "note": "the magazine curves forward: the centre of curvature is ahead of it, so the front "
                                   "edge is the inner (concave) arc and the rear edge the outer (convex) arc; both "
                                   "fitted as concentric arcs about one centre (floor plate excluded)"},
        "width_front_to_rear_radial": M(abs(R2 - R1), s, how="R_rear - R_front of the concentric fit"),
        "width_at_receiver": M(float(np.hypot(*(front[0] - rear[0]))), s),
        "length_chord_top_mid_to_floor_mid": M(float(np.hypot(*(bot_mid - top_mid))), s, ("seam", "sil")),
        "length_along_centre_arc": M(abs(a1 - a0) * Rm, s, ("seam", "sil")),
        "arc_sweep_deg": round(math.degrees(abs(a1 - a0)), 1),
        "floor_plate_corner_to_corner": M(float(np.hypot(*(tip - lowest))), s),
        "lowest_point_XZ": r1(lowest), "front_most_point_XZ": r1(tip),
        "ribs_side_view": rib,
        "mag_catch": {"X": r1(catch_box[:2]), "bottom_Z": round(catch_box[2], 1),
                      "note": "the catch lever hangs from the receiver directly behind the magazine's rear (concave) "
                              "edge"},
        "front_edge_points_mm": [[round(float(a), 2), round(float(b), 2)] for a, b in front],
        "rear_edge_points_mm": [[round(float(a), 2), round(float(b), 2)] for a, b in rear],
    }


def mag_ribs(view, fr, cx, cz, R1, R2, a0, a1):
    """Rib highlight lines across the magazine body: mean normalised luminance along radial lines (rear edge -> front
    edge) at 7 angles across the middle of the arc; peaks = bright rib crests."""
    Lum = ndi.gaussian_filter(view.L, 0.6)
    fr_list = np.linspace(0.04, 0.96, 93)
    profs = []
    for t in np.linspace(0.25, 0.75, 7):
        a = a0 + t * (a1 - a0)
        # f = 0 on the rear (outer, R2) edge, f = 1 on the front (inner, R1) edge
        xy = np.array([fr.px(cx + (R2 + f * (R1 - R2)) * math.cos(a), cz + (R2 + f * (R1 - R2)) * math.sin(a))
                       for f in fr_list])
        v = ndi.map_coordinates(Lum, [xy[:, 1], xy[:, 0]], order=1)
        profs.append((v - v.mean()) / (v.std() + 1e-6))
    prof = np.mean(profs, axis=0)
    peaks = [i for i in range(2, len(prof) - 2) if prof[i] == prof[i - 2:i + 3].max() and prof[i] > 0.35]
    return {"method": "mean normalised luminance on 7 radial lines across the arc; 0 = rear (outer) edge, 1 = front "
                      "(inner) edge; peaks = bright rib crests / edge highlights",
            "bright_line_positions_fraction_of_width": [round(float(fr_list[i]), 3) for i in peaks],
            "bright_line_strength": [round(float(prof[i]), 2) for i in peaks],
            "count": len(peaks), "profile": [round(float(v), 2) for v in prof]}


# ------------------------------------------------------------------------------------------------ top view
def analyse_top(view):
    rings = view.rings
    w = wood_mask(view, view.sil)
    wl, wn = ndi.label(w)
    comps = []
    for i in range(1, wn + 1):
        c = wl == i
        if c.sum() >= 80:
            comps.append((np.nonzero(c)[1].mean(), c))
    comps.sort(key=lambda t: t[0])
    lab = np.zeros(view.sil.shape, np.int32)
    names = ["background"]
    for nm, (_, c) in zip(["stock", "handguard"], [comps[0], comps[-1]]):
        names.append(nm)
        lab[c] = len(names) - 1
    names.append("steel")
    lab[view.sil & (lab == 0)] = len(names) - 1
    ext = extend_labels(lab, view.sil)
    wood = {nm: part_rings(view.F, ext, k) for k, nm in enumerate(names) if k and nm != "steel"}
    allp = np.vstack(outer(rings))
    x0, x1 = allp[:, 0].min(), allp[:, 0].max()
    xs, tops, bots = [], [], []
    bp = view.cfg["barrel_probe"]
    for x in np.arange(view.px(bp["x"][0], 0)[0], view.px(bp["x"][1], 0)[0] + 0.01, 1.0):
        h = hits_v(rings, x)
        if len(h) >= 2:
            xs.append(x)
            tops.append(h[0])
            bots.append(h[-1])
    xs, tops, bots = map(np.array, (xs, tops, bots))
    a, b, rms = R.fit_line(xs, (tops + bots) / 2)
    # the frame axis is the gun's overall centre line (stock, handguard and barrel centres), not the barrel alone:
    # in this view the barrel is drawn ~0.5 deg off the rest of the gun
    cx, cy = [], []
    for f0, f1 in ((0.03, 0.23), (0.565, 0.72), (0.84, 0.91)):
        for x in np.arange(x0 + f0 * (x1 - x0), x0 + f1 * (x1 - x0), 1.0):
            h = hits_v(rings, x)
            if len(h) >= 2:
                cx.append(x)
                cy.append((h[0] + h[-1]) / 2)
    ac, bc, rmsc = R.fit_line(np.array(cx), np.array(cy))
    u = np.array([1.0, ac]) / math.hypot(1, ac)
    t = allp @ u
    L_px = float(t.max() - t.min())
    p_on = np.array([np.mean(cx), ac * np.mean(cx) + bc])
    fr = Frame(L_px / OVERALL_MM, u, p_on + (t.min() - p_on @ u) * u)
    prof = []
    for x in np.arange(np.ceil(x0), x1, 0.5):
        h = hits_v(rings, x)
        if len(h) >= 2:
            X, Yl = fr.mm(x, h[0])
            _, Yr = fr.mm(x, h[-1])
            prof.append((X, Yl, Yr))
    return {"rings": rings, "frame": fr, "L_px": L_px,
            "axis": {"slope_deg": math.degrees(math.atan(ac)), "centre_line_rms_px": rmsc,
                     "barrel_slope_deg": math.degrees(math.atan(a)), "rms_px": rms,
                     "barrel_bend_vs_centre_line_deg": math.degrees(math.atan(a) - math.atan(ac)),
                     "barrel_width_px": float(np.mean(bots - tops)), "barrel_width_sd_px": float(np.std(bots - tops)),
                     "x_range_px": [float(xs.min()), float(xs.max())]},
            "profile": np.array(prof), "wood": wood}


def measure_top(T):
    fr, prof = T["frame"], T["profile"]
    s = fr.s

    def widths(Xa, Xb):
        sel = (prof[:, 0] >= Xa) & (prof[:, 0] <= Xb)
        return prof[sel, 1] - prof[sel, 2]

    out = {}
    wb = {k: part_box_mm(fr, v) for k, v in T["wood"].items()}
    st, hg = wb["stock"], wb["handguard"]
    out["stock_wood_X"] = r1(st[:2])
    out["handguard_wood_X"] = r1(hg[:2])
    out["butt_plate_width"] = M(float(widths(0.5, st[0] - 0.5).max()), s, how="max width behind the stock wood")
    out["butt_plate_thickness_top_view"] = M(st[0] - prof[0, 0], s, ("sil", "seam"))
    out["stock_width_by_X"] = {str(int(X)): round(float(np.median(widths(X - 2, X + 2))), 1)
                               for X in np.arange(round(st[0] + 10), st[1] - 5, 20)}
    out["stock_width_at_butt"] = M(float(np.median(widths(st[0] + 2, st[0] + 12))), s)
    out["stock_width_at_wrist"] = M(float(np.median(widths(st[1] - 25, st[1] - 10))), s)
    out["handguard_width"] = M(float(np.median(widths(hg[0] + 10, hg[1] - 10))), s)
    out["barrel_width"] = M(T["axis"]["barrel_width_px"] / s, s)
    out["front_sight_block_max_width"] = M(float(widths(0.915 * OVERALL_MM, 0.965 * OVERALL_MM).max()), s)
    out["muzzle_brake_width"] = M(float(np.median(widths(0.975 * OVERALL_MM, 0.995 * OVERALL_MM))), s)
    body = (prof[:, 0] > st[1] + 70) & (prof[:, 0] < st[1] + 115)        # the plain middle of the receiver
    body_l, body_r = np.median(prof[body, 1]), np.median(prof[body, 2])
    out["receiver_body_Y"] = [round(float(body_r), 1), round(float(body_l), 1)]
    out["receiver_body_width_plain_section"] = M(float(body_l - body_r), s, how="median over the plain middle section "
                                                 "of the receiver (no lateral features)")
    zone = (prof[:, 0] > st[1]) & (prof[:, 0] < hg[0] + 2)

    def runs(sel, col, sign, base):
        out_, cur = [], []
        for k in np.nonzero(zone)[0]:
            if sel[k]:
                cur.append(k)
            elif cur:
                out_.append(cur)
                cur = []
        if cur:
            out_.append(cur)
        res = []
        for c in out_:
            seg = prof[c]
            if seg[-1, 0] - seg[0, 0] < 3:
                continue
            ext = seg[:, col].max() if sign > 0 else seg[:, col].min()
            res.append({"X": r1([seg[0, 0], seg[-1, 0]]), "Y_extreme": round(float(ext), 1),
                        "beyond_body_mm": round(float(abs(ext - base)), 1)})
        return res

    out["lateral_features_image_up"] = runs(prof[:, 1] > body_l + 3, 1, 1, body_l)
    out["lateral_features_image_down"] = runs(prof[:, 2] < body_r - 3, 2, -1, body_r)
    step = max(1, int(round(5 * s / 0.5)))
    out["width_profile_mm_every_5mm_X_Yleft_Yright"] = [[round(float(p[0]), 1), round(float(p[1]), 2),
                                                         round(float(p[2]), 2)] for p in prof[::step]]
    return out


# ------------------------------------------------------------------------------------------------ close-ups, ruler
def closeup_field(rgb, box):
    x0, y0, x1, y1 = box
    P = rgb[y0:y1 + 1, x0:x1 + 1].astype(float)
    L, S = P.mean(2), P.max(2) - P.min(2)
    bg, _ = R.fit_background(L, S, deg=3)
    return P, L, S, bg


def measure_closeups(rgb, boxes):
    out = {}
    P, L, S, bg = closeup_field(rgb, boxes["CU_MAGAZINE_FRONT"])
    m = ndi.binary_fill_holes(R.largest_component(R.soft_field(L, S, bg) > 0.5))
    ys, xs = np.nonzero(m)
    H = ys.max() - ys.min() + 1
    w = np.array([m[r].sum() for r in range(ys.min() + int(0.25 * H), ys.min() + int(0.75 * H))])
    out["magazine_front"] = {"height_px": int(H), "body_width_px_median": float(np.median(w)),
                             "thickness_over_vertical_height": round(float(np.median(w) / H), 4)}
    P, L, S, bg = closeup_field(rgb, boxes["CU_MAGAZINE_LEFT"])
    m2 = ndi.binary_fill_holes(R.largest_component(R.soft_field(L, S, bg) > 0.5))
    ys, xs = np.nonzero(m2)
    out["magazine_left_closeup"] = {"height_px": int(ys.max() - ys.min() + 1), "width_px": int(xs.max() - xs.min() + 1),
                                    "note": "drawn curving the other way from the rifle's left view (front edge on the "
                                            "left), i.e. really a right-side view; used for the rib pattern only"}
    # butt plate end: neutral steel plate between the chromatic wood on both sides; width by a centre-out chroma
    # scan on the middle rows, height from the dark rim on the centre column against the backdrop above / below
    x0, y0, x1, y1 = boxes["CU_BUTTPLATE_END"]
    P = rgb[y0:y1 + 1, x0:x1 + 1].astype(float)
    L, S = P.mean(2), ndi.median_filter(P.max(2) - P.min(2), 3)
    H, W = L.shape
    xc = W // 2
    ws = []
    for r in range(int(0.35 * H), int(0.65 * H)):
        lft = np.nonzero(S[r, :xc] > 20)[0]
        rgt = np.nonzero(S[r, xc:] > 20)[0]
        if len(lft) and len(rgt):
            ws.append((xc + rgt[0]) - lft[-1])
    col = ndi.median_filter(L[:, xc], 3)
    tb, bb = np.median(col[:8]), np.median(col[-8:])
    top = int(np.nonzero(np.abs(col - tb) > 25)[0][0])
    bot = int(np.nonzero(np.abs(col - bb) > 25)[0][-1])
    Hs = bot - top + 1
    out["butt_plate_end"] = {"plate_height_px": Hs, "plate_width_px_median": float(np.median(ws)),
                             "width_over_height": round(float(np.median(ws) / Hs), 4),
                             "shape": "stadium (long rounded rectangle) with a raised rim and two slotted screws on "
                                      "the centre line near each end"}
    return out


def ruler_scale(view):
    """px per cm of the sheet's printed ruler (side views), from its tick marks."""
    y0 = int(CONFIG[view.name]["exclude_below_y"] + CONFIG[view.name]["origin"][1] - view.box[1])
    sub = view.L[y0:y0 + 30]
    D = sub < (np.percentile(sub, 75) - 40)          # the backdrop model is not fitted down here; it is ~flat
    D[:, :4] = D[:, -4:] = False
    yl = int(np.argmax(D.sum(axis=1)))
    cols = D[max(0, yl - 6):yl].sum(axis=0) >= 2
    yl += y0
    lab, n = ndi.label(cols)
    cent = np.sort(np.array([np.mean(np.nonzero(lab == k)[0]) for k in range(1, n + 1)]))
    step = np.median(np.diff(cent))
    idx = np.round((cent - cent[0]) / step)
    k, c, rms = R.fit_line(idx, cent)
    return {"ruler_line_row_px": yl, "ticks_found": int(n), "tick_spacing_px": round(float(k), 3),
            "fit_rms_px": round(rms, 3), "tick_cm": 5.0, "px_per_cm": round(float(k) / 5.0, 4)}


# ------------------------------------------------------------------------------------------------ overlay
PART_COLS = {"stock": (255, 140, 0), "pistol_grip": (255, 140, 0), "handguard_upper": (255, 210, 0),
             "handguard_lower": (255, 140, 0), "magazine": (255, 255, 0), "butt_plate": (0, 255, 255),
             "receiver": (0, 255, 0), "dust_cover": (0, 190, 255), "rear_sight": (160, 255, 60),
             "gas_tube": (0, 255, 160), "gas_block": (255, 80, 80), "barrel": (120, 180, 255),
             "front_sight_block": (160, 255, 60), "muzzle_brake": (0, 255, 255), "trigger_guard": (255, 80, 80),
             "trigger": (0, 255, 255), "mag_catch": (160, 255, 60), "cleaning_rod": (255, 255, 255),
             "gas_tube_rear_cap": (0, 190, 255), "handguard_front_band": (0, 190, 255),
             "sling_swivel_rear": (0, 255, 255), "unassigned": (255, 0, 0)}


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


def draw_view(d, v, A, T, sc, off, left=None, al=None):
    if A is not None and v.name == "LEFT":
        for nm, rr in A["parts"].items():
            draw_rings(d, rr, sc, off, PART_COLS.get(nm, (200, 200, 200)))
        for nm, Pp in CONFIG["LEFT"]["face_features"].items():
            draw_rings(d, [np.array(v.poly(Pp))], sc, off, (255, 255, 255))
    if A is not None and v.name == "RIGHT" and left is not None:
        draw_rings(d, [al(r) for r in left.rings], sc, off, (0, 255, 255))
    if A is not None:
        draw_rings(d, A["mag"], sc, off, (255, 255, 0))
    if T is not None:
        for rr in T["wood"].values():
            draw_rings(d, rr, sc, off, (255, 140, 0))
        fr = T["frame"]
        for X in np.arange(0, OVERALL_MM, 12):
            p, q = fr.px(X, 0), fr.px(X + 6, 0)
            d.line([((p[0] + .5) * sc + off[0], (p[1] + .5) * sc + off[1]),
                    ((q[0] + .5) * sc + off[0], (q[1] + .5) * sc + off[1])], fill=(255, 0, 0))
    draw_rings(d, v.rings, sc, off, (255, 0, 255))


def make_overlay(left, right, top, AL, AR, T, al, path):
    sc, pad = 2, 34
    rows = [("LEFT: silhouette (magenta), parts (colours), magazine (yellow), selector face outline (white)",
             left, AL, None),
            ("RIGHT, mirrored: its silhouette (magenta), magazine (yellow), LEFT silhouette in RIGHT's frame (cyan)",
             right, AR, None),
            ("TOP: silhouette (magenta), wood (orange), gun centre-line axis = frame X axis (red dashes)", top, None,
             T)]
    W = max(v.W for _, v, _, _ in rows) * sc + 20
    H = sum(v.H * sc + pad for _, v, _, _ in rows) + 10
    im = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(im)
    f = font(18)
    y = 0
    for title, v, A, TT in rows:
        d.text((10, y + 8), title, fill=(0, 0, 0), font=f)
        y += pad
        im.paste(Image.fromarray(v.rgb.astype(np.uint8)).resize((v.W * sc, v.H * sc), Image.LANCZOS), (10, y))
        draw_view(d, v, A, TT, sc, (10, y), left, al)
        y += v.H * sc
    im.save(path)


def zoom_tiles(left, right, top, AL, AR, T, al):
    """4x QA tiles (scratch only, not committed)."""
    paths = []
    for v, A, TT in ((left, AL, None), (right, AR, None), (top, None, T)):
        sc = 4
        im = Image.fromarray(v.rgb.astype(np.uint8)).resize((v.W * sc, v.H * sc), Image.LANCZOS)
        draw_view(ImageDraw.Draw(im), v, A, TT, sc, (0, 0), left, al)
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
    AL = analyse_side(left, CONFIG["LEFT"], True)
    AR = analyse_side(right, CONFIG["RIGHT"], False)
    frL, LpxL = side_frame(left)
    frR, LpxR = side_frame(right)
    sL = frL.s
    T = analyse_top(top)
    frT, sT = T["frame"], T["frame"].s

    # ---------------- LEFT vs mirrored RIGHT
    # primary: frame alignment (each view on its own bore axis, butt at X = 0, scaled to 880 mm) - no fitting
    def r2l(P):
        return frL.px_arr(frR.mm_arr(P))

    def l2r(P):
        return frR.px_arr(frL.mm_arr(P))

    shape = left.sil.shape
    mR = R.rings_to_mask([r2l(r) for r in right.rings], shape)
    iou_fr = R.iou(mR, left.sil)
    iou_rifle = R.iou(R.rings_to_mask([r2l(r) for r in AR["rifle"]], shape), R.rings_to_mask(AL["rifle"], shape))
    iou_mag = R.iou(R.rings_to_mask([r2l(r) for r in AR["mag"]], shape), R.rings_to_mask(AL["mag"], shape))
    edL = left.sil ^ ndi.binary_erosion(left.sil)
    edR = mR ^ ndi.binary_erosion(mR)
    dists = np.r_[ndi.distance_transform_edt(~edL)[edR], ndi.distance_transform_edt(~edR)[edL]] / sL
    # secondary: the similarity transform that maximises IoU (shows how much a free fit could hide)
    bl, br = bbox(left.rings), bbox(right.rings)
    init = np.array([(bl[1] - bl[0]) / (br[1] - br[0]), 0.0, bl[0] - br[0], bl[2] - br[2]])
    al, iou_al, tf = align_similarity(right.rings, left.sil, shape, init)
    iou_al = R.iou(R.rings_to_mask([tf(al, r) for r in right.rings], shape), left.sil)
    comp = {}
    for nm in ("stock", "pistol_grip", "handguard_upper", "handguard_lower", "magazine"):
        if nm in AL["parts"] and nm in AR["parts"]:
            bL = part_box_mm(frL, AL["parts"][nm])
            bR = part_box_mm(frR, AR["parts"][nm])
            comp[nm] = {"LEFT_X": r1(bL[:2]), "RIGHT_X": r1(bR[:2]), "LEFT_Z": r1(bL[2:]), "RIGHT_Z": r1(bR[2:]),
                        "d_length_mm": round((bR[1] - bR[0]) - (bL[1] - bL[0]), 1),
                        "d_height_mm": round((bR[3] - bR[2]) - (bL[3] - bL[2]), 1),
                        "d_rear_X_mm": round(bR[0] - bL[0], 1), "d_front_X_mm": round(bR[1] - bL[1], 1),
                        "d_bottom_Z_mm": round(bR[2] - bL[2], 1), "d_top_Z_mm": round(bR[3] - bL[3], 1)}
    prof_cmp = []
    for X in np.arange(20, 870, 10.0):
        a = col_extent(frL, left.rings, X)
        b = col_extent(frR, right.rings, X)
        if a and b:
            prof_cmp.append((X, b[1] - a[1], b[0] - a[0]))
    prof_cmp = np.array(prof_cmp)
    agreement_lr = {
        "method": "RIGHT panel mirrored; both views put in the gun frame independently (own bore axis, X = 0 at "
                  "the rearmost butt point, own scale so the overall length is 880 mm) and compared without any "
                  "fitting; a free similarity fit (max IoU) is given as a secondary number",
        "iou_silhouette_frame_aligned": round(iou_fr, 4), "iou_rifle_without_mag_frame_aligned": round(iou_rifle, 4),
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
        "bore_slope_deg": {"LEFT": round(frL.bore["slope_deg"], 3), "RIGHT_mirrored": round(frR.bore["slope_deg"], 3)},
        "barrel_diameter_px": {"LEFT": round(frL.bore["diameter_px"], 2), "RIGHT": round(frR.bore["diameter_px"], 2)},
        "parts": comp,
    }

    # ---------------- measurements
    ML = measure_left(left, AL, frL)
    MT = measure_top(T)
    CU = measure_closeups(rgb, boxes)
    rulerL, rulerR = ruler_scale(left), ruler_scale(right)
    mag_vert = ML["magazine"]["Z"][1] - ML["magazine"]["Z"][0]
    thick = CU["magazine_front"]["thickness_over_vertical_height"] * mag_vert
    ML["magazine"]["thickness_from_front_closeup"] = M(
        thick, sL, ("est", "est"), extra_unc=0.1 * thick,
        how="front close-up width/height ratio x the LEFT view's vertical magazine height (assumes the close-up "
            "shows the same full height); +-10 %")
    bp_h = ML["butt_plate"]["height"]["mm"]
    ML["butt_plate"]["width_from_end_closeup"] = M(CU["butt_plate_end"]["width_over_height"] * bp_h, sL,
                                                   ("est", "est"), extra_unc=0.05 * bp_h * 0.33)
    ML["butt_plate"]["width_from_top_view"] = MT["butt_plate_width"]

    stL, hgL = ML["stock"]["X_wood"], ML["handguard_upper"]["X"]
    agreement_top = {
        "overall_length_px": {"TOP": round(T["L_px"], 2), "LEFT": round(LpxL, 2),
                              "ratio_TOP_over_LEFT": round(T["L_px"] / LpxL, 5)},
        "axis_slope_deg": round(T["axis"]["slope_deg"], 3),
        "stations_mm_each_view_scaled_to_880": {
            "stock_wood_rear": {"TOP": MT["stock_wood_X"][0], "LEFT": stL[0],
                                "diff": round(MT["stock_wood_X"][0] - stL[0], 1)},
            "stock_wood_front": {"TOP": MT["stock_wood_X"][1], "LEFT": stL[1],
                                 "diff": round(MT["stock_wood_X"][1] - stL[1], 1)},
            "upper_handguard_rear": {"TOP": MT["handguard_wood_X"][0], "LEFT": hgL[0],
                                     "diff": round(MT["handguard_wood_X"][0] - hgL[0], 1)},
            "upper_handguard_front": {"TOP": MT["handguard_wood_X"][1], "LEFT": hgL[1],
                                      "diff": round(MT["handguard_wood_X"][1] - hgL[1], 1)},
        },
        "barrel": {"TOP_width_mm": MT["barrel_width"]["mm"], "LEFT_height_mm": ML["barrel"]["diameter"]["mm"],
                   "ratio": round(MT["barrel_width"]["mm"] / ML["barrel"]["diameter"]["mm"], 3),
                   "note": "a round barrel reads the same in both views if both are orthographic at the same scale"},
        "butt_plate_width": {"TOP": MT["butt_plate_width"]["mm"],
                             "END_closeup": ML["butt_plate"]["width_from_end_closeup"]["mm"]},
    }

    fsb = ML["front_sight_block"]
    fs_front = []
    for Z in np.linspace(fsb["hood_top_Z"]["mm"] - 2, 14, 12):
        hh = hits_h(AL["parts"]["front_sight_block"], frL.px(0, Z)[1])
        if len(hh):
            fs_front.append((Z, frL.mm(hh[-1], frL.px(0, Z)[1])[0]))
    fs_front = np.array(fs_front)
    kf, cf, rmsf = R.fit_line(fs_front[:, 0], fs_front[:, 1])
    perspective = {
        "bore_straightness_rms_px": {"LEFT": round(frL.bore["rms_mid_px"], 3), "RIGHT": round(frR.bore["rms_mid_px"], 3),
                                     "TOP": round(T["axis"]["rms_px"], 3)},
        "barrel_edge_line_rms_px_LEFT": {"top": round(frL.bore["rms_top_px"], 3),
                                         "bottom": round(frL.bore["rms_bottom_px"], 3)},
        "front_sight_hood_front_edge_tilt_deg": round(math.degrees(math.atan(kf)), 2),
        "front_sight_hood_front_edge_fit_rms_mm": round(rmsf, 2),
        "left_right_scale_ratio": round(float(al[0]), 5),
        "top_vs_side_length_ratio": round(T["L_px"] / LpxL, 5),
        "barrel_top_width_over_side_height": agreement_top["barrel"]["ratio"],
    }
    perspective["conclusion"] = (
        "No measurable perspective in LEFT, RIGHT or TOP: the barrel edges are straight lines to %.2f px rms over the "
        "exposed barrel, the bore axis is level to %.2f deg in LEFT, the front sight hood's front edge is vertical to "
        "%.1f deg, and LEFT / mirrored RIGHT / TOP have the same overall length in px to within %.1f %%. The views are "
        "treated as orthographic. What does differ between them is the drawing itself (part positions shift by up to "
        "~16 mm, the barrel reads 14.8 / 15.5 / 16.7 mm): image-generator inconsistency, not projection."
        % (max(frL.bore["rms_top_px"], frL.bore["rms_bottom_px"]), abs(frL.bore["slope_deg"]),
           abs(perspective["front_sight_hood_front_edge_tilt_deg"]),
           100 * max(abs(LpxR / LpxL - 1), abs(T["L_px"] / LpxL - 1))))

    # ---------------- traces
    def outline_json(view, A, fr, extra=None):
        d = {"view": view.name, "panel_box_sheet_px": list(view.box), "mirrored": view.mirror,
             "frame": "mm: X toward the muzzle, Z up; X = 0 at the rearmost butt point, Z = 0 on the bore axis. px: "
                      "pixel-centre coords in the panel crop",
             "px_per_mm": round(fr.s, 6), "bore_dir_px": [round(float(fr.u[0]), 6), round(float(fr.u[1]), 6)],
             "origin_px": [round(float(fr.p0[0]), 3), round(float(fr.p0[1]), 3)],
             "silhouette": [ring_json(r, fr.mm) for r in view.rings]}
        if A is not None:
            d["rifle_without_magazine"] = [ring_json(r, fr.mm) for r in A["rifle"]]
            d["magazine"] = [ring_json(r, fr.mm) for r in A["mag"]]
            d["parts"] = {nm: [ring_json(r, fr.mm) for r in rr] for nm, rr in A["parts"].items()}
        if extra:
            d.update(extra)
        return d

    (TRACE / "LEFT_outline.json").write_text(json.dumps(outline_json(
        left, AL, frL, {"face_features": ML["face_features"], "see_through_holes_px": left.kept_holes}), indent=1))

    def mm_aligned(r):
        return [[round(float(a), 3), round(float(b), 3)] for a, b in frR.mm_arr(r)]

    jr = {"view": "RIGHT", "panel_box_sheet_px": list(right.box), "mirrored": True,
          "frame": "px = mirrored RIGHT panel crop; mm = X toward the muzzle, Z up, X = 0 at the rearmost butt "
                   "point, Z = 0 on RIGHT's own bore axis, scaled so the overall length is 880 mm",
          "px_per_mm": round(frR.s, 6),
          "silhouette": [dict(ring_json(r), mm=mm_aligned(r)) for r in right.rings],
          "rifle_without_magazine": [dict(ring_json(r), mm=mm_aligned(r)) for r in AR["rifle"]],
          "magazine": [dict(ring_json(r), mm=mm_aligned(r)) for r in AR["mag"]],
          "see_through_holes_px": right.kept_holes}
    (TRACE / "RIGHT_outline.json").write_text(json.dumps(jr, indent=1))
    jt = {"view": "TOP", "panel_box_sheet_px": list(top.box), "px_per_mm": round(sT, 6),
          "frame": "mm: X toward the muzzle, Y = image up (= gun LEFT for a camera above, see notes); X = 0 at the "
                   "rearmost butt point, Y = 0 on the barrel axis",
          "bore_dir_px": [round(float(frT.u[0]), 6), round(float(frT.u[1]), 6)],
          "origin_px": [round(float(frT.p0[0]), 3), round(float(frT.p0[1]), 3)],
          "silhouette": [ring_json(r, frT.mm) for r in top.rings],
          "wood": {nm: [ring_json(r, frT.mm) for r in rr] for nm, rr in T["wood"].items()},
          "width_profile_mm_X_Yleft_Yright": MT["width_profile_mm_every_5mm_X_Yleft_Yright"]}
    (TRACE / "TOP_outline.json").write_text(json.dumps(jt, indent=1))
    save_mask(left.sil, "LEFT_silhouette.png")
    save_mask(R.rings_to_mask(AL["rifle"], left.sil.shape), "LEFT_rifle_no_mag.png")
    save_mask(R.rings_to_mask(AL["mag"], left.sil.shape), "LEFT_magazine.png")
    save_mask(right.sil, "RIGHT_mirrored_silhouette.png")
    save_mask(R.rings_to_mask(AR["rifle"], right.sil.shape), "RIGHT_mirrored_rifle_no_mag.png")
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
        "asset": "AR-01 assault rifle (generic AK-pattern): reference measurement of the user's sheet",
        "source": "References/Guns/Rifle/rifle_sheetAB.webp (1536x1024, AI-generated)",
        "tool": "WorkFiles/guns/rifle/tools/trace_reference.py (regenerates this file, trace/ and the overlay)",
        "frame": {"axes": "+X toward the muzzle, +Z up, +Y = gun left (right-handed)",
                  "origin": "X = 0 at the rearmost point of the butt plate; Z = 0 on the bore axis (barrel centre "
                            "line fitted on the exposed barrel between the gas block and the front sight block); "
                            "Y = 0 on the mid-plane",
                  "units": "mm unless the key ends in _px"},
        "scale": {"overall_length_mm_chosen": OVERALL_MM,
                  "px_per_mm": {"LEFT": round(sL, 5), "RIGHT": round(frR.s, 5), "TOP": round(sT, 5)},
                  "mm_per_px": {"LEFT": round(1 / sL, 4), "RIGHT": round(1 / frR.s, 4), "TOP": round(1 / sT, 4)},
                  "sheet_ruler": {"LEFT": rulerL, "RIGHT": rulerR,
                                  "implied_overall_length_cm_LEFT": round(LpxL / rulerL["px_per_cm"], 1),
                                  "implied_overall_length_cm_RIGHT": round(LpxR / rulerR["px_per_cm"], 1)},
                  "global_scale_uncertainty_pct": 1.5,
                  "uncertainty_note": "unc_mm = 1-sigma measurement uncertainty from the edge types (silhouette "
                                      "+-0.4 px, hand-placed seam +-1 px, estimate +-2 px) at that view's scale; the "
                                      "880 mm scale choice adds +-1.5 % to every length on top"},
        "panels_sheet_px_x0_y0_x1_y1_inclusive": {k: list(v) for k, v in boxes.items()},
        "backdrop_fit_residual_sd": {"LEFT": round(left.bg_sd, 2), "RIGHT": round(right.bg_sd, 2),
                                     "TOP": round(top.bg_sd, 2)},
        "see_through_holes_px": {"LEFT": left.kept_holes, "RIGHT_mirrored": right.kept_holes, "TOP": top.kept_holes},
        "bore_axis_fit_px": {"LEFT": frL.bore, "RIGHT_mirrored": frR.bore, "TOP": T["axis"]},
        "agreement": {"left_vs_right": agreement_lr, "top_vs_side": agreement_top, "perspective": perspective},
        "authority": {
            "lengths_heights_XZ": "LEFT (all parts traced; sharpest); RIGHT is the cross-check",
            "widths_Y": "TOP (the only view showing widths); magazine thickness and butt plate width cross-checked "
                        "with the close-ups",
            "magazine": "LEFT (in place on the rifle); close-ups only for the rib pattern and thickness ratio",
            "details": "close-ups and the 3/4 view for surface features only (not to scale)",
        },
        "dimensions": ML,
        "top_view": MT,
        "closeups": CU,
    }
    (OUT / "rifle_measured.json").write_text(json.dumps(measured, indent=1))
    make_overlay(left, right, top, AL, AR, T, l2r, OUT / "RIFLE_TRACE_OVERLAY.png")
    zoom_tiles(left, right, top, AL, AR, T, l2r)
    print(json.dumps({"px_per_mm": measured["scale"]["px_per_mm"], "iou_lr": agreement_lr["iou_silhouette_frame_aligned"],
                      "ruler_cm": measured["scale"]["sheet_ruler"]["implied_overall_length_cm_LEFT"],
                      "unassigned_px": int((AL["lab"] == names.index("unassigned")).sum())
                      if "unassigned" in names else 0}, indent=1))


if __name__ == "__main__":
    main()
