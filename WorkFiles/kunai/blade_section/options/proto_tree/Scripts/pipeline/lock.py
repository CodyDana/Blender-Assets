"""Asset ownership locks for concurrent agents (stdlib only).

A lock is one JSON file per asset in ``WorkFiles/locks/<asset>.json`` with the
keys ``asset``, ``agent``, ``blend``, ``port``, ``pid``, ``since`` and
``updated`` (ISO-8601 local time). Any script that opens a .blend should call
``assert_owner`` first.

Concurrency: ``claim`` takes the lock with an atomic ``O_CREAT | O_EXCL``
create, so two agents racing for the same asset cannot both win; the loser gets
``LockHeldError``. Refreshes and forced takeovers are written to a unique
temporary file and moved into place with ``os.replace`` (retried, because a
concurrent reader can hold the target open on Windows).

Case: Windows filenames are case-insensitive, so the lock file is named from
``asset.casefold()`` and the original spelling is stored in the record. Reading
a record whose ``asset`` does not case-fold to the requested name is an error
rather than a silent match.

Staleness: a CLI process exits as soon as it returns, so ``pid`` is only
meaningful when the caller passes ``--pid`` (the long-lived Blender or editor
process). Every claim also stamps ``updated``; ``status`` reports
``age_seconds`` and flags the lock ``stale`` once it is older than
``PIPELINE_LOCK_TTL`` seconds (default 8 h). ``--force`` stays the explicit
takeover.

This module runs under Blender's Python and under the system Python 3.12; it
never imports bpy.

CLI (exit code 0 on success, 2 when the lock is held by another agent, 1 on any
other error)::

    py Scripts/pipeline/lock.py claim <Asset> --agent claude|codex [--blend path] [--port 9876] [--pid 1234] [--force]
    py Scripts/pipeline/lock.py release <Asset> --agent X [--force]
    py Scripts/pipeline/lock.py status [<Asset>]
    py Scripts/pipeline/lock.py list
    py Scripts/pipeline/lock.py assert <Asset> --agent X
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import re
import sys
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_LOCK_DIR = Path("C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/locks")
LOCK_DIR = Path(os.environ.get("PIPELINE_LOCK_DIR", str(DEFAULT_LOCK_DIR)))
DEFAULT_TTL_SECONDS = 8 * 3600
KNOWN_AGENTS = ("claude", "codex")
_ASSET_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]*$")
_REPLACE_ATTEMPTS = 10
_REPLACE_DELAY = 0.05

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_HELD = 2


class LockError(RuntimeError):
    """Base class for lock failures."""


class LockHeldError(LockError):
    """Raised when another agent holds the asset lock."""

    def __init__(self, asset: str, lock: Optional[Dict[str, Any]], agent: str):
        self.asset = asset
        self.lock = lock
        self.agent = agent
        holder = lock.get("agent") if lock else None
        since = lock.get("since") if lock else None
        super().__init__(f"{asset}: lock held by {holder!r} since {since} (requested by {agent!r})")


class LockMissingError(LockError):
    """Raised by ``assert_owner`` when no lock exists for the asset."""


def ttl_seconds() -> int:
    """Age in seconds after which a lock is reported stale (``PIPELINE_LOCK_TTL``)."""
    try:
        return max(0, int(os.environ.get("PIPELINE_LOCK_TTL", DEFAULT_TTL_SECONDS)))
    except ValueError:
        return DEFAULT_TTL_SECONDS


def _lock_path(asset: str) -> Path:
    """Lock file for ``asset``; the file name is case-folded because Windows paths are."""
    if not _ASSET_RE.match(asset or ""):
        raise ValueError(f"Invalid asset name {asset!r}: use letters, digits, underscore, dash or dot")
    return LOCK_DIR / f"{asset.casefold()}.json"


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _age_seconds(stamp: Optional[str]) -> Optional[float]:
    if not stamp:
        return None
    try:
        return max(0.0, (datetime.now().astimezone() - datetime.fromisoformat(stamp)).total_seconds())
    except (TypeError, ValueError):
        return None


def _read(path: Path, asset: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Return the record in ``path``; raise when it is malformed or names another asset."""
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:  # released between the is_file() call and the read
        return None
    except (OSError, ValueError) as exc:
        raise LockError(f"Unreadable lock file {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise LockError(f"Malformed lock file {path}")
    stored = data.get("asset")
    if asset is not None and isinstance(stored, str) and stored.casefold() != asset.casefold():
        raise LockError(f"Lock file {path} holds asset {stored!r}, not {asset!r}")
    return data


def _dump(record: Dict[str, Any]) -> bytes:
    return (json.dumps(record, indent=2) + "\n").encode("utf-8")


def _write_atomic(path: Path, data: Dict[str, Any]) -> None:
    """Replace ``path`` with ``data`` through a unique temp file in the same directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f"{path.name}.{uuid.uuid4().hex}.", suffix=".tmp")
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(_dump(data))
            handle.flush()
            os.fsync(handle.fileno())
        last: Optional[OSError] = None
        for attempt in range(_REPLACE_ATTEMPTS):
            try:
                os.replace(tmp, path)
                return
            except PermissionError as exc:  # a reader can hold the target open on Windows
                last = exc
                time.sleep(_REPLACE_DELAY * (attempt + 1))
        raise LockError(f"Could not replace {path}: {last}")
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def _create_exclusive(path: Path, data: Dict[str, Any]) -> bool:
    """Create ``path`` atomically; return False when it already exists."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0))
    except FileExistsError:
        return False
    with os.fdopen(fd, "wb") as handle:
        handle.write(_dump(data))
        handle.flush()
        os.fsync(handle.fileno())
    return True


def pid_alive(pid: Optional[int]) -> Optional[bool]:
    """Return True/False when it can be determined whether ``pid`` runs, else None.

    Never uses ``os.kill(pid, 0)`` on Windows, where that would terminate the
    process. A recycled PID can read as alive, so treat this as a hint and use
    the ``stale`` flag for the real staleness signal.
    """
    if not pid:
        return None
    try:
        if os.name == "nt":
            kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
            process_query_limited_information = 0x1000
            handle = kernel32.OpenProcess(process_query_limited_information, False, int(pid))
            if not handle:
                return False
            try:
                code = ctypes.c_ulong()
                if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                    return None
                return code.value == 259  # STILL_ACTIVE
            finally:
                kernel32.CloseHandle(handle)
        os.kill(int(pid), 0)
        return True
    except ProcessLookupError:
        return False
    except (OSError, AttributeError, ValueError):
        return None


def _decorate(data: Dict[str, Any]) -> Dict[str, Any]:
    """Add the derived ``pid_alive``, ``age_seconds`` and ``stale`` fields to a record."""
    data = dict(data)
    data["pid_alive"] = pid_alive(data.get("pid"))
    age = _age_seconds(data.get("updated") or data.get("since"))
    data["age_seconds"] = None if age is None else round(age, 1)
    data["stale"] = bool(age is not None and age > ttl_seconds())
    return data


def status(asset: str) -> Optional[Dict[str, Any]]:
    """Return the lock record for ``asset`` with the derived fields, or None when unlocked."""
    data = _read(_lock_path(asset), asset)
    return None if data is None else _decorate(data)


def list_locks() -> List[Dict[str, Any]]:
    """Return every lock record in the lock directory, sorted by file name."""
    if not LOCK_DIR.is_dir():
        return []
    records = []
    for path in sorted(LOCK_DIR.glob("*.json")):
        data = _read(path)
        if data is not None:
            records.append(_decorate(data))
    return records


def claim(asset: str, agent: str, blend: Optional[str] = None, port: Optional[int] = None,
          force: bool = False, pid: Optional[int] = None) -> Dict[str, Any]:
    """Claim ``asset`` for ``agent`` and return the stored record.

    The first writer wins through an atomic exclusive create, so two agents
    racing cannot both succeed. Raises LockHeldError if another agent holds the
    lock and ``force`` is False; re-claiming an asset already held by ``agent``
    refreshes ``updated`` and keeps the original ``since``. Pass ``pid`` when
    the calling process is short-lived (a CLI) but the work happens in a
    long-lived Blender or editor process.
    """
    if not agent:
        raise ValueError("agent is required")
    path = _lock_path(asset)
    now = _now_iso()
    record: Dict[str, Any] = {
        "asset": asset,
        "agent": agent,
        "blend": str(blend) if blend else None,
        "port": int(port) if port is not None else None,
        "pid": int(pid) if pid is not None else os.getpid(),
        "since": now,
        "updated": now,
    }
    for _attempt in range(3):
        if _create_exclusive(path, record):
            return record
        current = _read(path, asset)
        if current is None:
            continue  # released between the failed create and the read; try again
        if current.get("agent") != agent and not force:
            raise LockHeldError(asset, current, agent)
        if current.get("agent") == agent:
            record["since"] = current.get("since", now)
        else:
            record["taken_from"] = {"agent": current.get("agent"), "since": current.get("since")}
        _write_atomic(path, record)
        return record
    raise LockError(f"{asset}: could not take the lock after 3 attempts")


def release(asset: str, agent: str, force: bool = False) -> Optional[Dict[str, Any]]:
    """Release ``asset``.

    Raises LockHeldError if another agent holds it and ``force`` is False.
    Returns the released record, or None when no lock existed.
    """
    if not agent:
        raise ValueError("agent is required")
    path = _lock_path(asset)
    current = _read(path, asset)
    if current is None:
        return None
    if current.get("agent") != agent and not force:
        raise LockHeldError(asset, current, agent)
    try:
        path.unlink()
    except FileNotFoundError:
        return None
    return current


def assert_owner(asset: str, agent: str) -> Dict[str, Any]:
    """Raise unless ``agent`` holds the lock for ``asset``; return the record otherwise.

    Call this at the top of any script that opens a .blend file. Raises
    LockMissingError when no lock exists and LockHeldError when another agent
    holds it or the stored asset name does not match.
    """
    current = _read(_lock_path(asset), asset)
    if current is None:
        raise LockMissingError(
            f"{asset}: no lock; run `py Scripts/pipeline/lock.py claim {asset} --agent {agent}` first")
    if current.get("agent") != agent:
        raise LockHeldError(asset, current, agent)
    return current


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lock.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_claim = sub.add_parser("claim", help="claim an asset lock")
    p_claim.add_argument("asset")
    p_claim.add_argument("--agent", required=True)
    p_claim.add_argument("--blend", default=None)
    p_claim.add_argument("--port", type=int, default=None)
    p_claim.add_argument("--pid", type=int, default=None,
                         help="PID of the long-lived process to record (default: this process)")
    p_claim.add_argument("--force", action="store_true")

    p_release = sub.add_parser("release", help="release an asset lock")
    p_release.add_argument("asset")
    p_release.add_argument("--agent", required=True)
    p_release.add_argument("--force", action="store_true")

    p_status = sub.add_parser("status", help="show one lock or all locks")
    p_status.add_argument("asset", nargs="?", default=None)

    sub.add_parser("list", help="list all locks")

    p_assert = sub.add_parser("assert", help="exit 0 only when the agent owns the lock")
    p_assert.add_argument("asset")
    p_assert.add_argument("--agent", required=True)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point; returns the process exit code."""
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "claim":
            result: Any = claim(args.asset, args.agent, blend=args.blend, port=args.port,
                                force=args.force, pid=args.pid)
        elif args.command == "release":
            released = release(args.asset, args.agent, force=args.force)
            if released is None:
                result = {"asset": args.asset, "released": False, "note": "no lock existed"}
            else:
                result = {"asset": args.asset, "released": True, "previous": released}
        elif args.command == "status":
            result = status(args.asset) if args.asset else list_locks()
        elif args.command == "list":
            result = list_locks()
        elif args.command == "assert":
            result = assert_owner(args.asset, args.agent)
        else:  # pragma: no cover
            raise ValueError(args.command)
    except LockHeldError as exc:
        print(json.dumps({"error": str(exc), "held_by": exc.lock}, indent=2))
        return EXIT_HELD
    except (LockError, ValueError, OSError) as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        return EXIT_ERROR
    print(json.dumps(result, indent=2))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
