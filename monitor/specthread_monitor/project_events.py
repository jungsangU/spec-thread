"""Local observation history shared by independently opened project sessions."""
import base64
import json
import os
import secrets
import time

from sdd_core.office import location

LIMIT = 256
RETENTION = 7 * 24 * 60 * 60


def event_paths(folder):
    paths = []
    for path in folder.glob("*.json"):
        try:
            if not path.is_symlink() and path.is_file():
                paths.append((path.stat().st_mtime, path))
        except OSError:
            continue
    return sorted(paths)


def record(root, agent, event):
    folder = location(root)
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    if folder.is_symlink():
        return
    event = {**event, "agent": agent, "observed_at": time.time()}
    identifier = f"{time.time_ns()}-{secrets.token_hex(6)}"
    pending = folder / f"{identifier}.tmp"
    with private_file(pending) as stream:
        stream.write(json.dumps(event, ensure_ascii=True).encode())
    pending.replace(folder / f"{identifier}.json")
    deadline = time.time() - RETENTION
    paths = event_paths(folder)
    for _, path in paths[:-LIMIT]:
        path.unlink(missing_ok=True)
    for modified, path in paths[-LIMIT:]:
        if modified < deadline:
            path.unlink(missing_ok=True)


def private_file(path):
    return os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb")


def read(root):
    deadline = time.time() - RETENTION
    rows = []
    for modified, path in event_paths(location(root))[-LIMIT:]:
        if modified < deadline:
            continue
        try:
            with path.open("rb") as stream:
                data = stream.read(4097)
            if len(data) <= 4096:
                raw = json.loads(data)
                if isinstance(raw, dict) and raw.get("agent") in ("codex", "claude"):
                    rows.append((path.stem, raw))
        except (OSError, ValueError, RecursionError):
            continue
    return rows


def configured_agent(root):
    for agent, directory, name in (("codex", ".codex", "hooks.json"), ("claude", ".claude", "settings.local.json")):
        path = root / directory / name
        try:
            if path.is_file() and path.stat().st_size <= 2 * 1024 * 1024:
                config = json.loads(path.read_text(encoding="utf-8"))
                for groups in config.get("hooks", {}).values():
                    for group in groups:
                        for handler in group.get("hooks", []):
                            command = handler.get("command", "")
                            if "-EncodedCommand " in command:
                                command = base64.b64decode(command.split("-EncodedCommand ", 1)[1]).decode("utf-16-le")
                            if "specthread_monitor.session" in command or "specthread_monitor.session" in handler.get("args", []):
                                return agent
        except (OSError, ValueError, TypeError, AttributeError, UnicodeError):
            continue
    return None
