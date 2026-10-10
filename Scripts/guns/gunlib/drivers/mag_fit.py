"""Magazine fit verification on the SHIPPED bytes of the static twin and the magazine, in a fresh Blender process.
Promoted from the AR-01's rifle_mag_fit.py (gunlib 0.2.0).

    blender -b --factory-startup --python <shim> -- [--out json] [--geom npz]

GUN_BUILDING_STUDY 7.2 M-gates. Both FBX files are re-imported (nothing from a build scene); the magazine is placed
from the exported gun sidecar's sockets. This driver owns what every gun shares:
- the imports (the twin's merged magazine faces, slot M_<code>_Mag, are kept apart from the gun's), the sidecars,
  the socket frames, placing the magazine at a socket frame, the co-visible LOD pairs and the coarse-LOD pixel rule;
- M7: the gun bytes = the stage-5 sha256 and the magazine bytes = its build's (and built from those gun bytes);
and calls the gun's hook ``cfg.mag_fit["gates"](F)`` for M1-M6, M8 and the build-report gates (the AR-01's rock path
in rifle_gun_magfit.py; a straight-insert gun writes its own with the same scene: MagInsertStart -> Mag along the
mag's -Z, M4b / M5 with mag_release posed on the SK at its release angle).

Config ``cfg.mag_fit``: gates(F) -> list, switch_m ({k: metres} rifle LOD switch-in distances; default from
game_lod_sizes.json, d = 1.778 r / s), well_box_M (magazine surface inside it is hidden at every LOD), pairs, out
(default gates/mag.json), geom (default scratch/mag/fit_geom.npz), rig_report, mag_report.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .. import game as GM
from .. import gateutil as GU

PAIRS = [(0, 0), (1, 1), (2, 2), (3, 3), (0, 1), (1, 0), (1, 2), (2, 1), (2, 3), (3, 2)]


class FitScene:
    def __init__(self, cfg, argv):
        self.cfg = cfg
        C = cfg.mag_fit
        self.C = C
        self.argv = argv
        self.grip = cfg.grip
        self.EXP = cfg.exports
        self.RIG = json.loads(Path(C.get("rig_report") or cfg.scratch / "rig" / "rig_report.json").read_text())
        self.MAGREP = json.loads(Path(C.get("mag_report") or cfg.scratch / "mag" / "mag_report.json").read_text())
        self.pairs = [tuple(p) for p in C.get("pairs", PAIRS)]
        if "switch_m" in C:
            self.switch_m = {int(k): float(v) for k, v in C["switch_m"].items()}
        else:
            sz = json.loads((cfg.gates / "game_lod_sizes.json").read_text())
            self.switch_m = {k: 1.778 * sz["bounds_radius_m"] / sz[cfg.twin][k] for k in (1, 2, 3)}
        self.gun_fbx = self.EXP / f"{cfg.twin}.fbx"
        self.mag_fbx = self.EXP / f"{cfg.mag}.fbx"
        self.gun = {}
        self.mag = {}

    # ------------------------------------------------------------------ imports
    def import_bytes(self):
        import bpy
        cfg = self.cfg
        bpy.ops.import_scene.fbx(filepath=str(self.gun_fbx), use_custom_normals=True)
        for o in bpy.data.objects:
            if o.type == "MESH" and o.name.startswith(f"{cfg.twin}_LOD"):
                k = int(o.name[-1])
                V, T, mat = GU.mesh_np(o, materials=True)
                keep = mat != cfg.mag_slot
                self.gun[k] = (V, T[keep], T[~keep])
        before = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=str(self.mag_fbx), use_custom_normals=True)
        for o in bpy.data.objects:
            if o not in before and o.type == "MESH" and o.name.startswith(f"{cfg.mag}_LOD"):
                V, T = GU.mesh_np(o)
                self.mag[int(o.name[-1])] = (V, T)
        self.gs = {s["socket"]: s for s in json.loads((self.EXP / f"{cfg.twin}.sockets.json").read_text())["sockets"]}
        self.ms = {s["socket"]: s for s in json.loads((self.EXP / f"{cfg.mag}.sockets.json").read_text())["sockets"]}
        self.sk = {s["name"]: s for s in json.loads((self.EXP / f"{cfg.skeletal}.skeletal.json").read_text())["sockets"]}

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def sock_frame(rec):
        """Static sidecar socket -> (R, t) in Blender frame B (mm)."""
        from mathutils import Euler
        loc = np.array(rec["location_cm"], float) * 10.0
        t = np.array([loc[0], -loc[1], loc[2]])
        ro = rec["rotation_deg"]
        R = np.array(Euler(GM.blender_euler_for_ue(ro["roll"], ro["pitch"], ro["yaw"]), "XYZ").to_matrix())
        return R, t

    def place(self, k, R, t):
        V, T = self.mag[k]
        return V @ R.T + t, T          # mag frame -> B: the magazine's local axes ride the given socket frame

    @staticmethod
    def samples(V, T, step):
        return GM.dense_samples(V, T, step)

    @staticmethod
    def tree(V, T):
        return GU.tree(V, T)

    @staticmethod
    def depth_inside(points, t, lo, hi, cap=60.0):
        return GU.depth_inside(points, t, lo, hi, cap)

    def visible_only(self, P):
        """Magazine points outside the LOD0 well box (frame B in, frame M box): the hidden part never shows."""
        box = self.C["well_box_M"]
        M = P + self.grip
        inside = ((M[:, 0] >= box["X"][0]) & (M[:, 0] <= box["X"][1]) & (M[:, 1] >= box["Y"][0]) &
                  (M[:, 1] <= box["Y"][1]) & (M[:, 2] >= box["Z"][0]) & (M[:, 2] <= box["Z"][1]))
        return P[~inside]

    def px_per_mm(self, k):
        """At LOD k's switch-in distance (2560 x 1440, 90 deg hFOV): 1280 / d(mm)."""
        return 1280.0 / (self.switch_m[k] * 1000.0)


def main(cfg, argv=None):
    argv = GU.argv_after_dashes() if argv is None else argv
    GU.clear_scene()
    F = FitScene(cfg, argv)
    gates = []
    out = {"stage": F.C.get("stage", "6 Mag (fit, geo, uv, maps, game, export, verify)")}
    # ------------------------------------------------------------ M7 bytes
    r_sha, m_sha = GU.sha256(F.gun_fbx), GU.sha256(F.mag_fbx)
    r_want = F.RIG["files"][cfg.rel(F.gun_fbx)]["sha256"]
    m_want = F.MAGREP["files"][cfg.rel(F.mag_fbx)]["sha256"]
    noun = F.C.get("noun", "gun")
    gates.append(GU.gate(f"M7 {noun} bytes = the shipped stage-5 sha256", {noun: r_sha, "recorded": r_want,
                         "mag": m_sha, "mag_recorded": m_want,
                         f"mag_built_from_{noun}_sha": F.MAGREP[f"{noun}_bytes"]["sha256"]},
                         "equal (and the magazine was built from these %s bytes)" % noun,
                         r_sha == r_want and m_sha == m_want and F.MAGREP[f"{noun}_bytes"]["sha256"] == r_sha))
    F.r_sha, F.m_sha = r_sha, m_sha
    F.import_bytes()
    gates += F.C["gates"](F, out)
    out["gates"] = gates
    out["failed"] = [g["name"] for g in gates if not g["pass"]]
    out["status"] = "pass" if not out["failed"] else "fail"
    out["files"] = {**{k: v for k, v in F.MAGREP["files"].items()},
                    f"{cfg.rel(F.gun_fbx)} (input)": {"sha256": r_sha}}
    out["build_report"] = "scratch/mag/mag_report.json"
    out_path = Path(GU.opt(argv, "--out") or F.C.get("out") or cfg.gates / "mag.json")
    out_path.write_text(json.dumps(out, indent=1, default=str))
    if "geom" in F.C or GU.opt(argv, "--geom"):
        geom = getattr(F, "geom", None)
        if geom:
            np.savez_compressed(GU.opt(argv, "--geom") or F.C["geom"], **geom)
    print("[%s-fit]" % cfg.log_tag, out["status"], out["failed"], flush=True)
    return out
