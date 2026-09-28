"""Start the MCP for Blender socket server inside a GUI Blender session.

Usage (normally via Scripts/launch_blender.ps1):
    blender.exe [file.blend] --python Scripts/mcp_autostart.py -- --port 9876 --agent claude

Each AI agent gets its own Blender window bound to its own port:
    claude -> 9876   codex -> 9877
The addon stores the port on the scene (Scene.blendermcp_port).
Status is written to WorkFiles/mcp_status_<agent>.json; the log is WorkFiles/mcp_autostart.log.
"""
import argparse
import json
import os
import sys
import traceback
from pathlib import Path

import addon_utils
import bpy

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "WorkFiles" / "mcp_autostart.log"
ADDON = "blender_mcp"             # mcp-for-blender addon module (v1.7+)
LEGACY = ("blender_mcp_addon",)   # old module names to disable if still enabled in prefs

_argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
_ap = argparse.ArgumentParser()
_ap.add_argument("--port", type=int, default=9876)
_ap.add_argument("--agent", default="claude")
ARGS = _ap.parse_args(_argv)
_state = {"tries": 0}


def _log(msg: str) -> None:
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"[{ARGS.agent}:{ARGS.port}] {msg}\n")
    except Exception:
        pass


def _server():
    return getattr(bpy.types, "blendermcp_server", None)


def _stop_server() -> None:
    srv = _server()
    if srv is None:
        return
    try:
        bpy.ops.blendermcp.stop_server()
    except Exception:
        try:
            srv.stop()
        except Exception:
            pass
    try:
        bpy.types.blendermcp_server = None
    except Exception:
        pass


def _addon_version():
    try:
        return list(addon_utils.module_bl_info(sys.modules[ADDON])["version"])
    except Exception:
        return None


def _tick():
    _state["tries"] += 1
    try:
        for legacy in LEGACY:
            try:
                if bpy.context.preferences.addons.get(legacy):
                    addon_utils.disable(legacy, default_set=True)
            except Exception:
                pass
        addon_utils.enable(ADDON, default_set=True, persistent=True)
        prefs = bpy.context.preferences.addons[ADDON].preferences
        if hasattr(prefs, "telemetry_consent"):
            prefs.telemetry_consent = False
        bpy.context.scene.blendermcp_port = ARGS.port

        srv = _server()
        running = bool(srv is not None and getattr(srv, "running", False))
        if running and getattr(srv, "port", None) != ARGS.port:
            _log(f"addon auto-started on port {srv.port}; restarting on {ARGS.port}")
            _stop_server()
            running = False
        if not running:
            bpy.ops.blendermcp.start_server()
        srv = _server()
        status = {
            "agent": ARGS.agent,
            "port": getattr(srv, "port", ARGS.port),
            "running": bool(getattr(srv, "running", False)),
            "blend": bpy.data.filepath,
            "blender": bpy.app.version_string,
            "addon_version": _addon_version(),
            "telemetry_consent": bool(getattr(prefs, "telemetry_consent", True)),
            "pid": os.getpid(),
        }
        out = ROOT / "WorkFiles" / f"mcp_status_{ARGS.agent}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(status, indent=2), encoding="utf-8")
        try:
            bpy.ops.wm.save_userpref()
        except Exception:
            pass
        _log(f"STARTED {status}")
        return None
    except Exception as e:
        _log(f"FAIL try {_state['tries']}: {e!r}\n{traceback.format_exc()}")
        return 1.0 if _state["tries"] < 15 else None


_log("=== script loaded ===")
bpy.app.timers.register(_tick, first_interval=3.0)
