"""Silhouette gates for SMG01 (plain Python): L1 (blockout) and the silhouette parts of L2 / L3 (form).

    py -3 -B Scripts/guns/smg/smg_silhouette.py --npz <tris.npz> --stage blockout|form [--json out.json]

Views (frame M -> panel px with each trace's own mapping, gunlib.compare; no camera error):
  LEFT   the gun's left side (both side panels are authority views here: the labels are true, spec R3)
  RIGHT  the gun's right side (the panel is traced mirrored; orthographic silhouettes from +Y / -Y are identical,
         so this measures the RIGHT panel's own drawing: the port side)
  TOP    X >= the spec's exclusion X (the stock is drawn obliquely, R18; checked by its widths instead)
Per part (form): visible labels (painter's order from the viewer's side) vs the trace's part masks. The measurement
conventions (spec resolution "L2 per part: measurement conventions", W1b fix round):
  - integral mouldings (upper / lower receiver, stock frame, pin heads, the charging handle on the fore-end) are split
    PER PIXEL by the trace's own label map (the nearest allowed label): the trace's label boundaries inside one moulding
    are not edges of the part, so they are not measured (the triangle-centroid split put whole triangles across them);
  - the lower receiver's fixed hinge knuckles may take the trace's stock_hinge_knuckle label (the trace labels every
    knuckle there);
  - what the fore-end's vents show (the barrel behind the receiver front) takes the vent's moulding label: the sheet
    draws the vents dark, not daylight (declared deviation: fore-end);
  - the toothed rails are compared outside their slotted layer (spec R9 / L3: the notch and relief depth is the line
    standard's, drawn 5.4 vs built 3.0); the rail's D rim over the end block (R32) takes the trace's label there;
  - the trigger below the housing's bottom line: the trace labels the dark band at the guard opening's top (the
    housing's edge) as trigger;
  - the muzzle device with its holes filled: its side slots are real through-slots (daylight through the bore, real
    pattern) that the sheet draws dark;
  - the flip sights' leaves resized by the fold spec (B4c: folded heights) are gated against the spec's own ceiling:
    IoU >= (IoU of the trace minus the leaf pixels the fold rule makes impossible) - 0.05, the plan's own tolerance;
  - the rail's top band under the sights' clamp feet takes the trace's sight label where the trace has one (a label
    boundary along the rail top inside one silhouette band);
  - the pixels the trace labels mag_release (+1 px) are left out of every other part's comparison (the declared paddle
    deviation puts our clevis ears there);
  - thin = area < 400 px OR mean width (2 area / perimeter) < 7 px: the contour rule (holes filled P95 <= 1 px,
    max <= 2 px) instead of IoU >= 0.95.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from smg_common import SPEC, TRACE, SHEET, REVIEW, D as SPECD  # noqa: E402
from gunlib import compare as C  # noqa: E402

TOP_X_MIN = float(SPECD["gates"]["look"]["L2_TOP_exclusion_X"])
L2_AREAS = SPECD["gates"]["look"]["L2_part_areas_px"]

# our object -> trace part key (separate parts); integral mouldings are split by the trace label map
PART_MAP = {"upper_receiver": None, "lower_receiver": None, "stock_frame": None, "grip_cover": "grip",
            "top_rail": "top_rail", "rail_screws": "top_rail", "lower_rail": "lower_rail",
            "sight_rear_base": "sight_rear", "sight_rear_leaf": "sight_rear", "sight_rear_pin": "sight_rear",
            "sight_front_base": "sight_front", "sight_front_leaf": "sight_front", "sight_front_pin": "sight_front",
            "barrel": "barrel", "muzzle_device": "muzzle_device", "trigger": "trigger", "trigger_axle": "receiver_lower",
            "mag_release": "mag_release", "mag_release_pin": "mag_release", "magazine": "magazine",
            "magazine_follower": "magazine", "magazine_floor_plate": "magazine", "butt_pad": "butt_pad",
            "hinge_axle": "stock_hinge_knuckle", "stock_latch_button": "stock_hinge_knuckle",
            "stock_latch_bolt": "stock_hinge_knuckle", "charging_handle": None,
            "charging_slide": "receiver_upper", "bolt": "receiver_upper", "bolt_rails": "receiver_upper",
            "selector": "receiver_lower", "pins_fasteners": None,
            # blockout names
            "upper_fore_end": "handguard_area", "magwell": "mag_well", "trigger_guard": "trigger_guard",
            "pistol_grip": "grip", "end_block": "hinge_block", "stock_hinge": "stock_hinge_knuckle",
            "stock_neck": "stock_neck", "stock_top_strut": "stock_top_strut", "stock_lower_strut": "stock_lower_strut",
            "stock_web": "stock_web", "stock_rear_upright": "stock_rear_upright"}
ALLOWED = {"upper_receiver": ("receiver_upper", "handguard_area"),
           "lower_receiver": ("receiver_lower", "mag_well", "trigger_guard", "grip", "hinge_block",
                              "stock_hinge_knuckle"),
           "charging_handle": ("handguard_area", "receiver_upper"),
           "stock_frame": ("stock_neck", "stock_top_strut", "stock_lower_strut", "stock_web", "stock_rear_upright",
                           "stock_hinge_knuckle"),
           "pins_fasteners": ("receiver_lower", "receiver_upper", "hinge_block", "mag_well", "handguard_area"),
           "upper_receiver_blockout": ()}


def panel_rgb(view):
    j = json.loads((TRACE / f"{view}_outline.json").read_text())
    x0, y0, x1, y1 = j["panel_box_sheet_px"]
    a = np.asarray(Image.open(SHEET).convert("RGB"))[y0:y1 + 1, x0:x1 + 1]
    return a[:, ::-1] if j.get("mirrored") else a


def label_map():
    lab = np.asarray(Image.open(TRACE / "LEFT_parts_index.png"))
    names = json.loads((TRACE / "LEFT_parts_labels.json").read_text())["labels"]
    return lab, {int(k): v for k, v in names.items()}


def assign_keys(V, T, lab_obj, names, frL):
    """Trace part key per triangle: the separate parts by PART_MAP, the integral mouldings by the trace label map at
    the triangle centroid (nearest allowed label)."""
    lab, lnames = label_map()
    keys = sorted(set(v for v in lnames.values() if v not in ("background", "unassigned")))
    kidx = {k: i for i, k in enumerate(keys)}
    out = np.full(len(T), -1)
    cen = V[T].mean(axis=1)
    P = C.side_px(frL, cen)
    H, W = lab.shape
    # nearest-label lookup per allowed set
    cache = {}
    for oi, nm in enumerate(names):
        sel = np.nonzero(lab_obj == oi)[0]
        if not len(sel):
            continue
        k = PART_MAP.get(nm, "NA")
        if k not in (None, "NA"):
            out[sel] = kidx[k]
            continue
        allowed = ALLOWED.get(nm)
        if not allowed:
            continue
        ak = tuple(allowed)
        if ak not in cache:
            m = np.zeros_like(lab, bool)
            ids = [i for i, v in lnames.items() if v in allowed]
            m = np.isin(lab, ids)
            d, (iy, ix) = ndi.distance_transform_edt(~m, return_indices=True)
            cache[ak] = (iy, ix)
        iy, ix = cache[ak]
        px = np.clip(np.round(P[sel]).astype(int), [0, 0], [W - 1, H - 1])
        ny, nx = iy[px[:, 1], px[:, 0]], ix[px[:, 1], px[:, 0]]
        lv = lab[ny, nx]
        out[sel] = [kidx.get(lnames.get(int(v), ""), -1) for v in lv]
    return out, keys


TOOTHED = ("top_rail", "lower_rail")
LOWER_RAIL_TUCK_X = 488.5          # the magwell front face (the seam polyline) at the lower rail's top, Z -27.5
TOOTHED_BAND = {"top_rail": (39.5, 99.0),          # from the drawn notch floor (40.0) - 0.5 up (the rail ends at 45.4)
                "lower_rail": (-99.0, -31.3)}      # notches face down: up to the drawn floor (-31.8) + 0.5
# thin parts (W1b fix round, re-derived): the plan's thin examples (trigger 5.8 px, paddle 6.5 px mean width) are thin by
# WIDTH, not area; a ribbon under 7 px mean width (2 x area / perimeter) is judged by the contour rule like them: at
# 0.94 px/mm a half-pixel trace edge uncertainty alone moves such a part's IoU by more than 0.05
THIN_W_PX = 7.0
X_RECV_FRONT = float(SPECD["parts"][[q["id"] for q in SPECD["parts"]].index("upper_receiver")]["dims"]["front_face_X"])


def pixel_keys(V, T, lab, names, frL, keys):
    """Trace part key index per panel pixel (LEFT, seen from +Y): the visible object by painter's order, then the
    separate parts by PART_MAP and the integral mouldings by the nearest allowed trace label at that pixel."""
    lab_img, lnames = label_map()
    H, W = frL.shape
    OL = C.raster_labels(C.side_px(frL, V), T, -V[:, 1], lab, frL.shape, nlab=len(names))
    om = OL.argmax(0)
    om[OL.sum(0) < 0.5] = -1
    yy, xx = np.mgrid[0:H, 0:W]
    PM = frL.mm(np.c_[xx.ravel(), yy.ravel()])
    Xmm, Zmm = PM[:, 0].reshape(H, W), PM[:, 1].reshape(H, W)
    cache = {}

    def nearest(allowed):
        ak = tuple(allowed)
        if ak not in cache:
            ids = [i for i, v in lnames.items() if v in allowed]
            _, (iy, ix) = ndi.distance_transform_edt(~np.isin(lab_img, ids), return_indices=True)
            nl = lab_img[iy, ix]
            lut = np.full(256, -1)
            for i, v in lnames.items():
                if v in keys:
                    lut[i] = keys.index(v)
            cache[ak] = lut[nl]
        return cache[ak]
    K = np.full((H, W), -1)
    for oi, nm in enumerate(names):
        sel = om == oi
        if not sel.any():
            continue
        if nm == "barrel":                       # seen through the fore-end's vents (behind the receiver front)
            ins = sel & (Xmm < X_RECV_FRONT)
            K[ins] = nearest(ALLOWED["upper_receiver"])[ins]
            sel = sel & ~ins
        if nm in ALLOWED:
            K[sel] = nearest(ALLOWED[nm])[sel]
            continue
        k = PART_MAP.get(nm)
        if k and k in keys:
            K[sel] = keys.index(k)
    # R32: the rail's machined D rim runs on over the end block (X < the end block's front seam); the side silhouette
    # is unchanged and the trace labels that stretch end block: our rail pixels there take the nearest of the two
    import smg_geom as _SG
    rail_k0 = keys.index("top_rail")
    over_eb = (K == rail_k0) & (Xmm < _SG.END_BLOCK_FRONT_X)
    K[over_eb] = nearest(("top_rail", "hinge_block", "receiver_upper"))[over_eb]
    # the rail's top band under the sights' clamp feet: the trace's boundary between the rail and a sight base along
    # the rail top is a label boundary inside one silhouette band (both sit on the rail top, Z <= 45.4 + 1 px)
    rail_k = keys.index("top_rail")
    band = (K == rail_k) & (Zmm <= 45.4 + 1.0 / frL.s) & (Zmm >= 36.0)
    for sk in ("sight_rear", "sight_front"):
        sid = [i for i, v in lnames.items() if v == sk][0]
        here = band & (lab_img == sid)                 # only where the trace itself says sight (no nearest search)
        K[here] = keys.index(sk)
    return K, Xmm, Zmm


RAIL_CLOSE_MM = 26.0          # > the front relief flat (23.8 mm): the notches AND the relief flats at slot-floor level


def close_teeth(m, frL):
    """Close a rail's notches and its relief flats (R9: the notch depth is the line standard's 3.0, drawn 5.4; the
    relief flats sit at that slot-floor level): a horizontal closing over 26 mm."""
    w = int(round(RAIL_CLOSE_MM * frL.s)) | 1
    return ndi.binary_closing(np.pad(m, w), structure=np.ones((1, w), bool))[w:-w, w:-w]


SIGHT_FOLD = {
    # pivot, fold sense (+1 = forward, the rear; -1 = rearward, the front), the round end's radius, the folded Z band
    # the spec allows (B4c: rear <= 60.1 and above the rail top; front 44.8 (its relief flat) .. 51.7), the base X span
    # and its top (rail top + 2.0 floor), the pocket under the round end (rail frame -> M: pivot -3.4/+4.2 front,
    # -4.2/+3.4 rear), and the leaf zone's X limits (the rear sight's fixed block behind the leaf is base, not leaf)
    "sight_rear": {"sense": 1.0, "r_end": 2.6, "z_band": (45.4 + 0.15, 60.1), "pocket": (-4.2, 3.4), "leaf_X": (293.5, 1e9),
                   "base_block_top_Z": 58.1},
    "sight_front": {"sense": -1.0, "r_end": 2.25, "z_band": (44.8, 51.7), "pocket": (-3.4, 4.2), "leaf_X": (-1e9, 1e9)},
}


def sight_ceiling(k, refp, Xmm, Zmm):
    """The spec's own ceiling for a fold-resized sight leaf (W1b fix round): the trace mask minus the leaf pixels the
    fold rule makes impossible. A leaf point (x, z) folds to (x', z') = (px + s (z - pz), pz + s (px - x)) (s = +1
    forward, -1 rearward); it can exist only if z' lies in the folded band B4c allows and, where x' lies over the base
    (outside the pocket under the round end), z' clears the base top (rail top + 2.0) by the hinge row's 0.15."""
    d = SPECD["parts"][[q["id"] for q in SPECD["parts"]].index(k)]["dims"]
    f = SIGHT_FOLD[k]
    px_, pz_ = (float(v) for v in d["pivot_XZ"])
    bx = d["base_X"]
    s_ = f["sense"]
    base_top = 45.4 + 2.0
    leaf = (Zmm > pz_ + f["r_end"]) & (Xmm > f["leaf_X"][0]) & (Xmm < f["leaf_X"][1])
    if "base_block_top_Z" in f:               # above the base's fixed rear block every pixel behind the leaf is leaf
        leaf |= (Zmm > f["base_block_top_Z"]) & (Xmm <= f["leaf_X"][0])
    xf = px_ + s_ * (Zmm - pz_)
    zf = pz_ + s_ * (px_ - Xmm)
    ok = (zf >= f["z_band"][0]) & (zf <= f["z_band"][1])
    over_base = (xf > bx[0]) & (xf < bx[1]) & ~((xf > px_ + f["pocket"][0]) & (xf < px_ + f["pocket"][1]))
    ok &= ~over_base | (zf >= base_top + 0.15)
    ceil = refp & ~(leaf & ~ok)
    return C.iou(ceil, refp), {"rule": "fold feasibility (B4c band %s, base top %.1f + 0.15)" % (list(f["z_band"]), base_top),
                               "leaf_px_removed": int((refp & leaf & ~ok).sum())}


# side-view conventions for the whole-silhouette L2 IoU and the L3 contour (W1b fix round; spec resolution "L2 / L3
# side conventions"): the declared deviations measured the same way in both masks, the raw values reported beside them
RAIL_BANDS_M = [((256.0, 560.5), (38.5, 46.2)),          # the top rail's notch band (drawn 5.4 deep, built 3.0: R9)
                ((484.0, 554.0), (-38.0, -32.5))]        # the lower rail's (notches face down)
MUZZLE_ZONE_M = ((583.0, 625.6), (-10.6, 13.6))          # real through-slots: the sheet draws dark slots / one slit
STOCK_HOLE_X = (28.0, 222.0)                             # the stock's two through-holes (dia 5.4), drawn dark
PADDLE_HALO_PX = 2


def _zone(fr, xr, zr):
    H, W = fr.shape
    yy, xx = np.mgrid[0:H, 0:W]
    P = fr.mm(np.c_[xx.ravel(), yy.ravel()])
    return ((P[:, 0] >= xr[0]) & (P[:, 0] <= xr[1]) & (P[:, 1] >= zr[0]) & (P[:, 1] <= zr[1])).reshape(H, W)


def side_conventions(m, fr, is_ref, ref_raw=None):
    """The convention mask: the rail notch bands closed along X (R9: the notch depth is the line standard's), the
    muzzle device's interior closed and filled (real through-slots, drawn dark), our see-through stock holes the trace
    does not have filled (declared through-holes)."""
    m = m.copy()
    w = int(round(RAIL_CLOSE_MM * fr.s)) | 1
    for xr, zr in RAIL_BANDS_M:
        z = _zone(fr, xr, zr)
        c = ndi.binary_closing(np.pad(m, w), structure=np.ones((1, w), bool))[w:-w, w:-w]
        m[z] |= c[z]
    z = _zone(fr, *MUZZLE_ZONE_M)
    c = ndi.binary_fill_holes(ndi.binary_closing(np.pad(m, 4), structure=np.ones((5, 1), bool))[4:-4, 4:-4])
    m[z] |= c[z]
    if not is_ref:
        holes = ndi.binary_fill_holes(m) & ~m
        lab_, n = ndi.label(holes)
        zs = _zone(fr, STOCK_HOLE_X, (-90.0, 30.0))
        ref_holes = (ndi.binary_fill_holes(ref_raw) & ~ref_raw) if ref_raw is not None else np.zeros_like(m)
        for k in range(1, n + 1):
            h = lab_ == k
            if h.sum() <= 60 and (h & zs).all() and not (h & ref_holes).any():
                m |= h
    return m


def run(npz, stage, tag=""):
    D_ = np.load(npz)
    V, T, lab, names = D_["V"], D_["T"], D_["lab"], [str(n) for n in D_["names"]]
    res = {"stage": stage, "npz": str(Path(npz).name), "triangles": int(len(T)), "views": {}}
    out_dir = REVIEW / stage
    out_dir.mkdir(parents=True, exist_ok=True)
    mag_ids = [i for i, n in enumerate(names) if n.startswith("magazine")]
    is_mag = np.isin(lab, mag_ids)
    for view in ("LEFT", "RIGHT"):
        fr, j = C.load_trace(TRACE, view)
        ref = C.rings_mask([r["px"] for r in j["silhouette"]], fr.shape)
        ours = C.raster_tris(C.side_px(fr, V), T, fr.shape) > 0.5
        i0 = C.iou(ours, ref)
        p, i1, ours_fit = C.similarity_fit(lambda: (C.side_px(fr, V), T), ref)
        cd = C.contour_distance(ours, ref)
        # the conventions (declared deviations measured alike in both masks) and the L3 contour's own exclusions: the
        # paddle's fore-aft faces (declared; L3 gates its pin head and Z range) with a 2 px halo
        refc = side_conventions(ref, fr, True)
        oursc = side_conventions(ours, fr, False, ref)
        oursfc = side_conventions(ours_fit, fr, False, ref)
        jl_ = json.loads((TRACE / "LEFT_outline.json").read_text())
        pad = np.zeros(fr.shape, bool)
        if "mag_release" in jl_["parts"]:
            rl_ = [C.side_px(fr, np.c_[np.array(r["mm"])[:, 0], np.zeros(len(r["mm"])), np.array(r["mm"])[:, 1]])
                   for r in jl_["parts"]["mag_release"]]
            pad = ndi.binary_dilation(C.rings_mask(rl_, fr.shape), iterations=PADDLE_HALO_PX)
        cdc = C.contour_distance(oursc, refc, ~pad)
        e = {"iou_identity_raw": round(i0, 4), "iou_fit_raw": round(i1, 4), "fit_params_s_rotdeg_tx_ty": p,
             "iou_identity": round(C.iou(oursc, refc), 4), "iou_fit": round(max(C.iou(oursc, refc), C.iou(oursfc, refc)), 4),
             "conventions": "rail notch bands closed (R9), muzzle interior filled (real through-slots drawn dark), our "
                            "see-through stock holes filled (declared); L3 contour also without the paddle zone",
             "contour_px_raw": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in cd.items()},
             "contour_px": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in cdc.items()},
             "ours_px": int(ours.sum()), "ref_px": int(ref.sum())}
        if mag_ids:
            refm = C.rings_mask([r["px"] for r in j["magazine"]], fr.shape)
            om = C.raster_tris(C.side_px(fr, V), T[is_mag], fr.shape) > 0.5
            e["magazine_iou"] = round(C.iou(om, refm), 4)
            refn = C.rings_mask([r["px"] for r in j["gun_without_magazine"]], fr.shape)
            on = C.raster_tris(C.side_px(fr, V), T[~is_mag], fr.shape) > 0.5
            e["gun_without_mag_iou"] = round(C.iou(on, refn), 4)
        if view == "RIGHT":
            # the sheet's own ceiling: the LEFT trace (the authority for X / Z, R3) mapped into the RIGHT frame. A model
            # that matches LEFT exactly scores this against the RIGHT panel (the panels are near mirror copies only)
            jl = json.loads((TRACE / "LEFT_outline.json").read_text())
            rl = [C.side_px(fr, np.c_[np.array(r["mm"])[:, 0], np.zeros(len(r["mm"])), np.array(r["mm"])[:, 1]])
                  for r in jl["silhouette"]]
            ceil = C.rings_mask(rl, fr.shape)
            e["sheet_ceiling_iou_LEFT_trace_vs_RIGHT_raw"] = round(C.iou(ceil, ref), 4)
            ceilc = side_conventions(ceil, fr, True)
            e["sheet_ceiling_iou_LEFT_trace_vs_RIGHT"] = round(C.iou(ceilc, refc), 4)
            e["ours_minus_ceiling"] = round(e["iou_identity"] - e["sheet_ceiling_iou_LEFT_trace_vs_RIGHT"], 4)
            mis = oursc ^ refc
            e["residual_split"] = {"mismatch_px": int(mis.sum()),
                                   "LEFT_trace_agrees_with_RIGHT_ours_differs_px": int((mis & (ceilc == refc)).sum()),
                                   "LEFT_trace_vs_RIGHT_panel_contradiction_px": int((mis & (ceilc != refc)).sum())}
        res["views"][view] = e
        C.overlay(panel_rgb(view), ours, ref, out_dir / f"{view.lower()}_overlay{tag}.png")
        C.diff_image(ours, ref, out_dir / f"{view.lower()}_diff{tag}.png")
    # ---------------- per part (LEFT, visible labels from +Y)
    frL, jL = C.load_trace(TRACE, "LEFT")
    _, lnames_ = label_map()
    keys = sorted(set(v for v in lnames_.values() if v not in ("background", "unassigned")))
    K, Xmm, Zmm = pixel_keys(V, T, lab, names, frL, keys)
    import smg_geom as _SG
    z_house = float(_SG.L([(219.0, 241.5)])[0, 1])          # the housing's bottom (the guard opening's top)
    lab_img_, ln_ = label_map()
    lid_trigger = [i for i, v in ln_.items() if v == "trigger"][0]
    lid_mr = [i for i, v in ln_.items() if v == "mag_release"][0]
    mr_zone = ndi.binary_dilation(lab_img_ == lid_mr, iterations=1)
    parts_res = {}
    for ki, k in enumerate(keys):
        if k not in jL["parts"]:
            continue
        refp = C.rings_mask([r["px"] for r in jL["parts"][k]], frL.shape)
        op = K == ki
        conv = None
        w_mean = 2.0 * refp.sum() / max((refp ^ ndi.binary_erosion(refp)).sum(), 1)   # the trace's mean width (px)
        if k != "mag_release":
            # the declared paddle deviation (built 3.5 behind the drawn lever, per-part rule waived): the pixels the
            # trace labels mag_release (+1 px) show our clevis ears / slot instead; neighbours are not judged on them
            op, refp = op & ~mr_zone, refp & ~mr_zone
        if k == "lower_rail":
            # declared: the rail's rear end tucks 4.1 mm into the magwell's front pocket (the well's side walls hide it;
            # the sheet draws the rail end over the face): left out of both masks behind the face line at the rail top
            tuck = Xmm < LOWER_RAIL_TUCK_X
            op, refp = op & ~tuck, refp & ~tuck
        if k in TOOTHED:
            # R9: the slotted layer (the drawn 5.4 notches / relief flats vs the standard's 3.0) is exempt: the rail is
            # compared below / above it (its body, base flange and ends; the top's Z is L4's, the ends L3's)
            band = (Zmm > TOOTHED_BAND[k][0]) & (Zmm < TOOTHED_BAND[k][1])
            op, refp = close_teeth(op, frL) & ~band, close_teeth(refp, frL) & ~band
            conv = "the slotted layer Z %s excluded (R9: the notch / relief depth is the line standard's)" % (
                list(TOOTHED_BAND[k]),)
        elif k == "trigger":
            below = Zmm < z_house - 2.5 / frL.s
            op, refp = op & below, refp & below
            conv = ("below the housing's bottom line Z %.1f - 2.5 px (the trace's band at the opening's top is the "
                    "housing's edge)" % z_house)
        elif k == "receiver_lower":
            # the same band seen from the housing's side: the trace labels the housing's lower edge over the guard
            # opening 'trigger'; those pixels are excluded from both masks here too
            tb = (lab_img_ == lid_trigger) & (Zmm >= z_house - 2.5 / frL.s)
            op, refp = op & ~tb, refp & ~tb
            conv = "the trace's trigger-labelled band at the housing's lower edge excluded (see trigger)"
        elif k == "muzzle_device":
            vc = np.ones((5, 1), bool)
            op = ndi.binary_fill_holes(ndi.binary_closing(np.pad(op, 4), vc)[4:-4, 4:-4])
            refp = ndi.binary_fill_holes(ndi.binary_closing(np.pad(refp, 4), vc)[4:-4, 4:-4])
            conv = "slots closed and filled (real through-slots; the sheet draws them dark and one 1 px slit)"
        elif k == "lower_rail":
            pass
        area = float(L2_AREAS.get(k, refp.sum()))
        cdp = C.contour_distance(op, refp)
        e = {"area_px": round(area, 1), "iou": round(C.iou(op, refp), 4),
             "contour_p95_px": None if cdp["p95"] is None else round(cdp["p95"], 3),
             "contour_max_px": None if cdp["max"] is None else round(cdp["max"], 3)}
        if conv:
            e["convention"] = conv
        if k in ("sight_front", "sight_rear"):
            ce, how = sight_ceiling(k, refp, Xmm, Zmm)
            thr = round(ce - 0.05, 4)
            e["rule"] = "IoU >= spec ceiling %.4f - 0.05 = %.4f (the leaf resized by the fold spec: %s)" % (ce, thr, how["rule"])
            e["fold_ceiling"] = how
            e["spec_ceiling_iou"] = round(ce, 4)
            e["pass"] = e["iou"] >= thr
        elif area >= 400.0 and w_mean >= THIN_W_PX:
            e["rule"] = "IoU >= 0.95"
            e["pass"] = e["iou"] >= 0.95
        else:
            e["mean_width_px"] = round(w_mean, 2)
            opf, refpf = ndi.binary_fill_holes(op), ndi.binary_fill_holes(refp)
            cdf = C.contour_distance(opf, refpf)
            e["contour_p95_px"] = None if cdf["p95"] is None else round(cdf["p95"], 3)
            e["contour_max_px"] = None if cdf["max"] is None else round(cdf["max"], 3)
            e["iou_filled"] = round(C.iou(opf, refpf), 4)
            e["rule"] = "outer contour (holes filled) P95 <= 1.0 px, max <= 2 px"
            e["pass"] = cdf["p95"] is not None and cdf["p95"] <= 1.0 and cdf["max"] <= 2.0
        if k == "mag_release":
            e["declared"] = "mag_release.dims.declared_deviation: the paddle is built behind the drawn lever (C1); the " \
                            "per-part contour rule is waived; L3 gates the pin head and the Z range"
            e["pass_waived"] = True
        parts_res[k] = e
        if not e["pass"]:
            ys, xs = np.nonzero(op | refp)
            if len(ys):
                y0, y1 = max(ys.min() - 6, 0), min(ys.max() + 7, op.shape[0])
                x0, x1 = max(xs.min() - 6, 0), min(xs.max() + 7, op.shape[1])
                pdir = out_dir / "parts"
                pdir.mkdir(exist_ok=True)
                C.diff_image(op[y0:y1, x0:x1], refp[y0:y1, x0:x1], pdir / f"{k}{tag}.png", scale=6)
    res["views"]["LEFT"]["parts"] = parts_res
    # ---------------- TOP (X >= TOP_X_MIN)
    frT, jT = C.load_trace(TRACE, "TOP")
    refT = C.rings_mask([r["px"] for r in jT["silhouette"]], frT.shape)
    oursT = C.raster_tris(C.top_px(frT, V), T, frT.shape) > 0.5
    H, W = frT.shape
    yy, xx = np.mgrid[0:H, 0:W]
    Pm = frT.mm(np.c_[xx.ravel(), yy.ravel()])
    valid = (Pm[:, 0] >= TOP_X_MIN).reshape(H, W)
    t0 = C.iou(oursT, refT, valid)
    pT, t1, _ = C.similarity_fit(lambda: (C.top_px(frT, V), T), refT, valid)
    cdT = C.contour_distance(oursT, refT, valid)
    res["views"]["TOP"] = {"iou_identity_valid": round(t0, 4), "iou_fit_valid": round(t1, 4),
                           "iou_identity_all_pixels": round(C.iou(oursT, refT), 4), "fit_params_s_rotdeg_tx_ty": pT,
                           "valid_rule": "X >= %.1f (spec gates.look.L2_TOP_exclusion_X)" % TOP_X_MIN,
                           "contour_px": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in cdT.items()}}
    C.overlay(panel_rgb("TOP"), oursT, refT, out_dir / f"top_overlay{tag}.png")
    C.diff_image(oursT, refT, out_dir / f"top_diff{tag}.png", valid=valid)
    return res


def gate_l1(res):
    l, r, t = res["views"]["LEFT"]["iou_fit"], res["views"]["RIGHT"]["iou_fit"], res["views"]["TOP"]["iou_fit_valid"]
    ce = res["views"]["RIGHT"].get("sheet_ceiling_iou_LEFT_trace_vs_RIGHT")
    ri = res["views"]["RIGHT"]["iou_identity"]
    exc = ce is not None and ri >= ce - 0.005
    return [{"name": "L1 LEFT IoU (similarity fit)", "value": l, "threshold": ">= 0.95", "pass": l >= 0.95},
            {"name": "L1 RIGHT IoU (similarity fit)", "value": r, "threshold": ">= 0.95, or within 0.005 of the sheet's "
             "own LEFT/RIGHT ceiling (identity)", "pass": r >= 0.95 or exc,
             "note": "sheet ceiling (the LEFT trace vs the RIGHT panel, identity) %s; ours (identity) %.4f%s" % (
                 ce, ri, "; passes by the documented ceiling exception" if (exc and r < 0.95) else "")},
            {"name": "L1 TOP IoU (X >= %.0f, fit)" % TOP_X_MIN, "value": t, "threshold": ">= 0.92", "pass": t >= 0.92},
            {"name": "L1 stop rule (change the method below 0.90)", "value": min(l, r, t), "threshold": ">= 0.90",
             "pass": min(l, r, t) >= 0.90}]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz", required=True)
    ap.add_argument("--stage", default="blockout")
    ap.add_argument("--tag", default="")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    r = run(a.npz, a.stage, a.tag)
    if a.stage == "blockout":
        r["gates"] = gate_l1(r)
    js = json.dumps(r, indent=1)
    print(json.dumps({v: {k: x for k, x in e.items() if k != "parts"} for v, e in r["views"].items()}, indent=1))
    if a.json:
        Path(a.json).write_text(js)
