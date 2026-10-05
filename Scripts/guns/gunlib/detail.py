"""Detail-pass kit: per-part close-up cameras, traces and reference-vs-ours crops at identical framing (plain Python;
renders through a headless Blender subprocess running gunlib/render_job.py).

A gun configures it with its sheet panels and detail parts (the rifle: Scripts/guns/rifle/rifle_detail.py):

    kit = DetailKit(cfg)
    kit.solve_closeup_camera(part)   camera per close-up of the part: the panel camera (landmarks + silhouette, cached)
                                     refined on the part's own window -> scratch/cameras/<part>__<panel>.json
    kit.trace_closeup(part)          outline rings + internal edges of the reference in the part's window
                                     -> review/<part>/trace_<panel>.png / .json
    kit.render_part_crop(parts)      ROUGH LOOK render at each solved camera (one Blender run for all shots),
                                     composited on the panel's fitted backdrop; ref / ours crops of the same window,
                                     side-by-side pair, edge overlay and numbers -> review/<part>/

cfg keys: sheet (path), panels {key: panel cfg}, parts {part: {"objects": [...], "panels": [...]}}, npz (triangles in
frame M with names), blend, offset_M (frame B origin in M), wood_slots, review_dir, scratch_dir, blender, ss, samples.
Panel cfg: box (sheet px, inclusive), title, model, from_dir, up, roll_deg, bound_deg, landmarks, dist_mm, objects
(object names the panel shows; None = all), max_hole_px (reference holes smaller than this are filled), fixed_camera
(path of an already solved camera JSON, e.g. the 3/4 view's), lam_lm.
"""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

from . import closeup as CU
from . import compare as C


def fill_small_holes(m, max_area):
    if max_area is None:
        return ndi.binary_fill_holes(m)
    if max_area <= 0:
        return m
    holes = ndi.binary_fill_holes(m) & ~m
    lab, n = ndi.label(holes)
    if n == 0:
        return m
    sizes = ndi.sum(holes, lab, range(1, n + 1))
    small = np.zeros(n + 1, bool)
    small[1:] = sizes < max_area
    return m | small[lab]


def fill_bglike_holes(m, near_bg, max_area=300, min_bg_frac=0.6, thin_px=3.5):
    """Fill the mask's holes except real see-through openings. A hole stays open when at least min_bg_frac of its
    pixels look like the backdrop (|L - backdrop| < 7, chroma < 8) and it is not tiny (< 40 px); below max_area it
    must look like the backdrop almost everywhere (85 %). Lit or scratched steel that merged with the backdrop is
    textured / off-level and gets filled; so is a thin hole (inscribed radius < thin_px: a reflection streak along a
    polished surface, which can mirror the backdrop exactly)."""
    holes = ndi.binary_fill_holes(m) & ~m
    lab, n = ndi.label(holes)
    if n == 0:
        return m
    idx = np.arange(1, n + 1)
    area = ndi.sum(holes, lab, idx)
    frac = ndi.mean(near_bg.astype(float), lab, idx)
    rad = ndi.maximum(ndi.distance_transform_edt(holes), lab, idx)
    fill = np.zeros(n + 1, bool)
    fill[1:] = (area < 40) | (frac < min_bg_frac) | ((area < max_area) & (frac < 0.85)) | (rad < thin_px)
    return m | fill[lab]


class DetailKit:
    def __init__(self, cfg: Dict):
        self.cfg = cfg
        self.review = Path(cfg["review_dir"])
        self.scratch = Path(cfg["scratch_dir"])
        for p in (self.review, self.scratch, self.scratch / "cameras", self.scratch / "renders", self.review / "_panels"):
            p.mkdir(parents=True, exist_ok=True)
        self._rgb = None
        self._mask: Dict[str, np.ndarray] = {}
        self._geom = None
        self._panel_cam: Dict[str, object] = {}
        self.ss = int(cfg.get("ss", 3))

    # ------------------------------------------------------------------------------------------ inputs
    @property
    def rgb(self):
        if self._rgb is None:
            self._rgb = CU.load_rgb(self.cfg["sheet"])
        return self._rgb

    def panel(self, key) -> np.ndarray:
        return CU.crop(self.rgb, self.cfg["panels"][key]["box"])

    def mask(self, key) -> np.ndarray:
        if key not in self._mask:
            pc = self.cfg["panels"][key]
            P = self.panel(key)
            bgL, _, _, _ = CU.fit_background(P)
            sides = pc.get("cut_sides", "")
            m = CU.ref_mask(P, dl=pc.get("dl", 30.0), largest=False, fill=False, db=pc.get("db", 12.0), border=0)
            # the outermost pixel row / column can carry the white separator's fringe: copy it from its inward
            # neighbour on cut sides (the gun continues), clear it elsewhere
            for side, sl, nb in (("top", np.s_[0, :], np.s_[1, :]), ("bottom", np.s_[-1, :], np.s_[-2, :]),
                                 ("left", np.s_[:, 0], np.s_[:, 1]), ("right", np.s_[:, -1], np.s_[:, -2])):
                m[sl] = m[nb] if side in sides else False
            if pc.get("floor_rows"):                     # contact shadow on the studio floor under a standing item:
                n = int(pc["floor_rows"])                # only the dark steel survives in the bottom rows
                m[-n:, :] &= (P.mean(2) < bgL - pc.get("floor_dark", 55.0))[-n:, :]
            m = ndi.binary_closing(m, iterations=pc.get("close_px", 2), border_value=0) | m
            m = CU.largest_component(m) if pc.get("largest", True) else CU.drop_small(m, 60)
            # sides where the gun runs out of the panel count as foreground for the hole fill, so a light surface
            # that merges with the backdrop between two dark edges (a lit dust cover top) closes up
            pad = [(1 if "top" in sides else 0, 1 if "bottom" in sides else 0),
                   (1 if "left" in sides else 0, 1 if "right" in sides else 0)]
            mp = np.pad(m, pad, constant_values=False)
            if "top" in sides:
                mp[0, :] = True
            if "bottom" in sides:
                mp[-1, :] = True
            if "left" in sides:
                mp[:, 0] = True
            if "right" in sides:
                mp[:, -1] = True
            near = (np.abs(P.mean(2) - bgL) < 7.0) & ((P.max(2) - P.min(2)) < 8.0)
            filled = fill_bglike_holes(mp, np.pad(near, pad, constant_values=True), pc.get("max_hole_px", 300),
                                       thin_px=pc.get("thin_hole_px", 3.5))
            H, W = m.shape
            self._mask[key] = filled[pad[0][0]:pad[0][0] + H, pad[1][0]:pad[1][0] + W]
        return self._mask[key]

    def geometry(self):
        if self._geom is None:
            D = np.load(self.cfg["npz"])
            self._geom = (D["V"], D["T"], D["lab"], [str(n) for n in D["names"]])
        return self._geom

    def subset(self, names: Optional[List[str]]):
        """(V, T) of the named objects (None = all)."""
        V, T, lab, nm = self.geometry()
        if not names:
            return V, T
        ids = [i for i, n in enumerate(nm) if n in set(names)]
        missing = set(names) - set(nm)
        if missing:
            raise KeyError(f"objects not in {self.cfg['npz']}: {sorted(missing)}")
        return V, T[np.isin(lab, ids)]

    def part_vertices(self, part, window=True):
        """Vertices of the part's objects; with window=True those of its window_objects (the objects that frame its
        crop, e.g. the front sight without the long cleaning rod) when the part config lists them."""
        pc = self.cfg["parts"][part]
        V, T = self.subset(pc.get("window_objects", pc["objects"]) if window else pc["objects"])
        return V[np.unique(T)]

    # ------------------------------------------------------------------------------------------ cameras
    def _cam_path(self, key, part=None):
        return self.scratch / "cameras" / (f"{part}__{key}.json" if part else f"panel_{key}.json")

    def solve_panel(self, key, force=False):
        """Panel camera (landmarks + silhouette over the whole panel); cached in scratch/cameras/panel_<key>.json."""
        pc = self.cfg["panels"][key]
        if key in self._panel_cam and not force:
            return self._panel_cam[key]
        if pc.get("fixed_camera"):
            d = json.loads(Path(pc["fixed_camera"]).read_text())
            H, W = self.panel(key).shape[:2]
            d.setdefault("panel_px", [W, H])
            if "type" not in d:
                d["type"] = "PERSP"
            cam = CU.cam_from_json(d)
            rep = {"model": "fixed (" + Path(pc["fixed_camera"]).name + ")"}
            V, T = self.subset(pc.get("objects"))
            ref = self.mask(key)
            Tv = CU.visible_tris(cam, V, T)
            cov = C.raster_tris(cam.project(V), Tv, ref.shape, ss=2)
            rep["iou_in_frame"] = round(C.iou(cov > 0.5, ref), 4)
            self._panel_cam[key] = (cam, rep)
            return cam, rep
        p = self._cam_path(key)
        if p.exists() and not force:
            d = json.loads(p.read_text())
            cam, rep = CU.cam_from_json(d["camera"]), d["report"]
            self._panel_cam[key] = (cam, rep)
            return cam, rep
        P = self.panel(key)
        H, W = P.shape[:2]
        V, T = self.subset(pc.get("objects"))
        ref = self.mask(key)
        t0 = time.time()
        cam, rep = CU.solve_camera(pc, W, H, V, T, ref, iters=pc.get("iters", 500))
        rep["seconds"] = round(time.time() - t0, 1)
        p.write_text(json.dumps({"panel": key, "camera": cam.to_json(), "report": rep}, indent=1))
        CU.solve_overlay(P, cam, V, T, ref, self.review / "_panels" / f"solve_{key}.png", pc.get("landmarks", []))
        self._panel_cam[key] = (cam, rep)
        return cam, rep

    def solve_closeup_camera(self, part, force=False) -> Dict[str, Dict]:
        """Per-part cameras: the panel camera refined so the part's own window matches (close-ups are stylised and
        not to scale, so each part gets the framing its close-up draws). Fixed cameras (the 3/4 view) are reused."""
        out = {}
        pdir = self.review / part
        pdir.mkdir(parents=True, exist_ok=True)
        for key in self.cfg["parts"][part]["panels"]:
            pc = self.cfg["panels"][key]
            cam0, rep0 = self.solve_panel(key, force=False)
            path = self._cam_path(key, part)
            if pc.get("fixed_camera"):
                path.write_text(json.dumps({"panel": key, "part": part, "camera": cam0.to_json(), "report": rep0}, indent=1))
                out[key] = {"panel_camera": rep0, "part_camera": rep0}
                continue
            if path.exists() and not force:
                d = json.loads(path.read_text())
                out[key] = {"panel_camera": rep0, "part_camera": d["report"]}
                continue
            P = self.panel(key)
            H, W = P.shape[:2]
            V, T = self.subset(pc.get("objects"))
            ref = self.mask(key)
            win = CU.part_window(cam0, self.part_vertices(part), margin=0.3)
            roi = np.zeros((H, W), bool)
            roi[win[1]:win[3], win[0]:win[2]] = True
            sub = dict(pc)
            sub["bound_deg"] = pc.get("part_bound_deg", 5.0)
            sub["lam_lm"] = pc.get("part_lam_lm", 0.25)
            t0 = time.time()
            cam, rep = CU.solve_camera(sub, W, H, V, T, ref, roi=roi, init=cam0, iters=pc.get("part_iters", 300))
            rep["seconds"] = round(time.time() - t0, 1)
            rep["roi_px"] = list(win)
            path.write_text(json.dumps({"panel": key, "part": part, "camera": cam.to_json(), "report": rep}, indent=1))
            CU.solve_overlay(P, cam, V, T, ref, pdir / f"solve_{key}.png", pc.get("landmarks", []), roi_box=win)
            out[key] = {"panel_camera": rep0, "part_camera": rep}
        return out

    def part_camera(self, part, key):
        d = json.loads(self._cam_path(key, part).read_text())
        return CU.cam_from_json(d["camera"])

    def window(self, part, key):
        cam = self.part_camera(part, key)
        return CU.part_window(cam, self.part_vertices(part), margin=0.15)

    # ------------------------------------------------------------------------------------------ traces
    def trace_panel(self, key):
        pc = self.cfg["panels"][key]
        P = self.panel(key)
        tr = CU.trace_panel(P, dl=pc.get("dl", 30.0), largest=pc.get("largest", True))
        tr["mask"] = self.mask(key)
        return tr

    def trace_closeup(self, part) -> Dict[str, Dict]:
        """Reference outlines and internal edges inside the part's window of each of its panels (panel px)."""
        out = {}
        pdir = self.review / part
        pdir.mkdir(parents=True, exist_ok=True)
        for key in self.cfg["parts"][part]["panels"]:
            tr = self.trace_panel(key)
            x0, y0, x1, y1 = self.window(part, key)
            P = self.panel(key)
            sub = {"mask": tr["mask"][y0:y1, x0:x1], "edges": tr["edges"][y0:y1, x0:x1],
                   "rings": [r - (x0, y0) for r in tr["rings"]
                             if (r[:, 0].max() >= x0 and r[:, 0].min() < x1 and r[:, 1].max() >= y0 and r[:, 1].min() < y1)]}
            scale = max(2, int(round(640 / max(1, y1 - y0))))
            CU.save_trace(P[y0:y1, x0:x1], sub, pdir / f"trace_{key}.png", pdir / f"trace_{key}.json", scale=min(scale, 8),
                          meta={"panel": key, "part": part, "window_px": [x0, y0, x1, y1],
                                "coords": "rings_px and edge_px_uv are relative to the window's top-left (add window_px[0:2] for panel px)"})
            out[key] = {"window_px": [x0, y0, x1, y1], "edge_px": int(sub["edges"].sum()), "rings": len(sub["rings"])}
        return out

    # ------------------------------------------------------------------------------------------ renders and crops
    def _shot(self, part, key, tag):
        pc = self.cfg["panels"][key]
        cam = self.part_camera(part, key)
        P = self.panel(key)
        _, _, _, bg = CU.fit_background(P)
        Vp = self.part_vertices(part, window=False)
        return {"name": f"{part}__{key}", "camera": cam.to_json(), "show": pc.get("objects"),
                "poses": pc.get("poses", []),
                "out": str(self.scratch / "renders" / f"{part}__{key}{'_' + tag if tag else ''}.png"),
                "bg_rgb": [float(v) for v in bg.reshape(-1, 3).mean(0)], "target_M": Vp.mean(0).tolist()}

    def run_blender(self, shots, log_name="render_job"):
        job = {"offset_M": [float(v) for v in self.cfg["offset_M"]], "ss": self.ss, "samples": int(self.cfg.get("samples", 96)),
               "wood_slots": self.cfg.get("wood_slots", []), "worn_steel_objects": self.cfg.get("worn_steel_objects", []),
               "env": self.cfg.get("env", 0.45),
               "light": self.cfg.get("light", 1.0), "poses": self.cfg.get("poses", []), "shots": shots}
        jp = self.scratch / f"{log_name}.json"
        jp.write_text(json.dumps(job, indent=1))
        script = Path(__file__).resolve().parent / "render_job.py"
        log = self.scratch / f"{log_name}.log"
        with open(log, "w", encoding="utf-8", errors="replace") as f:
            subprocess.run([self.cfg["blender"], "-b", str(self.cfg["blend"]), "--factory-startup", "--python", str(script),
                            "--", "--job", str(jp)], stdout=f, stderr=subprocess.STDOUT, check=False)
        txt = log.read_text(encoding="utf-8", errors="replace")
        if "Traceback" in txt or "RENDER_JOB_DONE" not in txt:
            raise RuntimeError(f"render job failed, see {log}")

    def render_part_crop(self, parts, tag="", render=True) -> Dict[str, Dict]:
        """Render every (part, panel) shot of the given parts in one Blender run, then write per part and panel:
        ref_<panel>.png and [tag_]ours_<panel>.png (the same panel window at ss x), [tag_]pair_<panel>.png (side by
        side), [tag_]edges_<panel>.png (reference edges blue, ours red, silhouettes cyan / orange) and the numbers
        (silhouette IoU in the window, edge agreement) in [tag_]crops.json."""
        parts = [parts] if isinstance(parts, str) else list(parts)
        shots = [self._shot(p, k, tag) for p in parts for k in self.cfg["parts"][p]["panels"]]
        if render:
            self.run_blender(shots, f"render_{tag or 'current'}")
        res = {}
        pre = f"{tag}_" if tag else ""
        ss = self.ss
        for p in parts:
            pdir = self.review / p
            pdir.mkdir(parents=True, exist_ok=True)
            res[p] = {}
            for k in self.cfg["parts"][p]["panels"]:
                P = self.panel(k)
                H, W = P.shape[:2]
                _, _, _, bg = CU.fit_background(P)
                rgba = np.asarray(Image.open(self.scratch / "renders" / f"{p}__{k}{'_' + tag if tag else ''}.png").convert("RGBA"))
                ours = CU.composite_on(bg, rgba, ss)
                x0, y0, x1, y1 = self.window(p, k)
                ref_ss = CU.upscale(P, ss)
                rc = ref_ss[y0 * ss:y1 * ss, x0 * ss:x1 * ss]
                oc = ours[y0 * ss:y1 * ss, x0 * ss:x1 * ss]
                Image.fromarray(rc).save(pdir / f"ref_{k}.png")
                Image.fromarray(oc).save(pdir / f"{pre}ours_{k}.png")
                title = f"{p} vs {self.cfg['panels'][k].get('title', k)}  (window {x0},{y0}-{x1},{y1} panel px; ROUGH LOOK)"
                CU.pair_image(rc, oc, pdir / f"{pre}pair_{k}.png", ("reference " + k, "ours " + (tag or "current")), title=title)
                # numbers at panel resolution in the window
                our_small = CU.downscale(ours, ss)
                alpha = CU.downscale(np.repeat(rgba[:, :, 3:4], 3, 2).astype(np.uint8), ss)[:, :, 0] / 255.0
                ref_m = self.mask(k)
                sil_o = alpha > 0.5
                roi = np.zeros((H, W), bool)
                roi[y0:y1, x0:x1] = True
                inner_r = ndi.binary_erosion(ref_m, iterations=2)
                inner_o = ndi.binary_erosion(sil_o, iterations=2)
                er, _ = CU.canny(P.mean(2), 1.4, 88.0, mask=inner_r)
                eo, _ = CU.canny(our_small.mean(2), 1.4, 88.0, mask=inner_o)
                em = CU.edge_metrics(er, eo, roi, 2.0)
                iou = C.iou(sil_o, ref_m, roi)
                CU.edge_overlay(P[y0:y1, x0:x1], er[y0:y1, x0:x1], eo[y0:y1, x0:x1], pdir / f"{pre}edges_{k}.png",
                                ref_m[y0:y1, x0:x1], sil_o[y0:y1, x0:x1])
                # enlarge the edge overlay for viewing
                im = Image.open(pdir / f"{pre}edges_{k}.png")
                kz = max(1, int(round(480 / max(1, im.height))))
                im.resize((im.width * kz, im.height * kz), Image.NEAREST).save(pdir / f"{pre}edges_{k}.png")
                res[p][k] = {"window_px": [x0, y0, x1, y1], "silhouette_iou_window": round(iou, 4), "edges": em,
                             "files": {"ref": f"ref_{k}.png", "ours": f"{pre}ours_{k}.png", "pair": f"{pre}pair_{k}.png",
                                       "edges": f"{pre}edges_{k}.png"}}
            (pdir / f"{pre}crops.json").write_text(json.dumps(res[p], indent=1))
        return res
