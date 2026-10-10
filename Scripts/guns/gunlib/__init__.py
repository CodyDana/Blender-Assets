"""gunlib: shared code for the gun line (GUN_BUILDING_STUDY 4.7).

Every module derives the repo root from its own location (never a literal path), so a worktree build never writes
into the main checkout. Modules that need ``bpy`` (mesh.to_object, bl, render, fit) import it lazily or live in files
that are only imported inside Blender; geo2d, spec, compare, camsolve and qa_gun's deny list run in plain Python.

Started by the AR-01 rifle build (stages 1-2, 2026-10-04). The SMG reuses it next.

0.2.0 (2026-10-09, SMG_BUILD_PLAN 15 W1a, lock GunLib):
- parts/ is a package (the 0.1.0 parts.py is parts/__init__.py: PartDef, build_part, BuildCtx unchanged; new
  build_composite: per-piece edge breaks, then unions) with the line's shared generators: rail_1913 (MIL-STD-1913
  profile, 10.01 pitch), mag_box (straight box magazine), hinge (knuckles, axle, latch bolt, detents, B3 groups),
  sights_flip (rail-clamp flip sights, aperture / post heads), hardware (flush / roll pins, rivets, ISO socket heads);
- standard.py + WorkFiles/guns/gunlib/gun_standard.json (frame, bones, sockets, rail, clearance, process classes,
  hardware norms, camera, texel classes, UD thresholds);
- ud.py: gates UD1-UD2 at form time (Unreal's degenerate rule, micro strips / needles, zero-tangent risk groups);
- gunconf.py + drivers/: the AR-01's gate drivers made gun-agnostic (b3, b4 (+ aperture), b6a, measure,
  magfit_check (rock via hook + generic straight set), viewgates, g5_lods, rig_verify, mag_fit, ud) with a per-gun
  config (Scripts/guns/rifle/rifle_gun.py for the AR-01; the rifle_* scripts are shims);
- gateutil.py (shared gate helpers), spec.GunSpec.gun_sockets(), bl.bevel_weighted_convex / outer_edges_pred.
AR-01 regression: WorkFiles/guns/smg/gates/gunlib_regression.json (tests/ar01_regression.sh).

0.2.1 (2026-10-09, SMG W1b form, lock GunLib; every addition opt-in, the AR-01's calls unchanged):
- bl.weighted_normals(clear_custom=): drop stale custom normals first (they made flat faces shade with neighbours');
  bl.clear_custom_normals;
- ud.repair: crumbs (tiny boolean shells), tjunc (needle apex on its longest edge: split + merge), relaxed_final
  (sub-margin slivers and needle corners: looser collapses); validated step by step as before;
- compare.PanelFrame: the trace's up_dir_px (panels drawn muzzle-left);
- drivers.b3: optional group keys pre (pre-pose), exclude, sample_mm, coarse_proof="radius" (per-sample r x step / 2
  proof, fit.sweep(proof=)), --only; descending ranges; the clearance rows exclude declared allowance windows;
- look.rough_polymer / PHOS_* and rough_steel(metallic=, rough_add=); realism_job polymer_slots / steel_style /
  poses / hide.

0.2.2 (2026-10-09, SMG W1b form fix round, lock GunLib; opt-in, the AR-01's rock path unchanged):
- drivers.magfit_check: cfg.magfit["catch_spring"] = {"nose_M", "cam_mm_per_step"} evaluates M4 with the real
  pattern's spring-loaded catch (the smallest clearing rotation per step inside the release travel, the nose move per
  step bounded = a ramp not a shoulder, the snap at the seat); without the key M4 is the static-catch allowance as
  before.
"""
from __future__ import annotations

from pathlib import Path

LIB_VERSION = "0.2.2"
ROOT = Path(__file__).resolve().parents[3]          # Scripts/guns/gunlib -> repo root
BLENDER = "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
