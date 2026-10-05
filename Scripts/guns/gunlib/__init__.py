"""gunlib: shared code for the gun line (GUN_BUILDING_STUDY 4.7).

Every module derives the repo root from its own location (never a literal path), so a worktree build never writes
into the main checkout. Modules that need ``bpy`` (mesh.to_object, bl, render, fit) import it lazily or live in files
that are only imported inside Blender; geo2d, spec, compare, camsolve and qa_gun's deny list run in plain Python.

Started by the AR-01 rifle build (stages 1-2, 2026-10-04). The SMG reuses it next.
"""
from __future__ import annotations

from pathlib import Path

LIB_VERSION = "0.1.0"
ROOT = Path(__file__).resolve().parents[3]          # Scripts/guns/gunlib -> repo root
BLENDER = "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
