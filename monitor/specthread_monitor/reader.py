"""Short-lived Office roles for native agent permission requests."""
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
import time

from sdd_core.office import LEASE_SECONDS, active_role, location
COMMANDS = frozenset({
    "pwd", "ls", "ls -a", "ls -l", "ls -la",
    "git branch --show-current", "git rev-parse --show-toplevel",
    "git rev-parse --is-inside-work-tree",
})


def set_office_role(root, role, enabled):
    if role not in ("reader", "ceo"):
        raise ValueError("Unknown Office role")
    folder = location(root)
    if folder.is_symlink():
        raise ValueError("Invalid Reader state directory")
    state = folder / role
    if not enabled:
        state.unlink(missing_ok=True)
        return
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=folder, delete=False, mode="w", encoding="utf-8") as stream:
        temporary = Path(stream.name)
        try:
            json.dump(time.time() + LEASE_SECONDS, stream)
            stream.close()
            temporary.replace(state)
        finally:
            temporary.unlink(missing_ok=True)


def set_reader(root, enabled):
    set_office_role(root, "reader", enabled)


def reader_response(root, raw):
    if raw.get("hook_event_name") != "PermissionRequest":
        return None
    tool = raw.get("tool_name")
    inputs = raw.get("tool_input")
    if not isinstance(tool, str) or not tool or not isinstance(inputs, dict):
        return None
    try:
        if Path(raw["cwd"]).resolve() != root or inputs.get("workdir") not in (None, raw["cwd"]):
            return None
    except (OSError, ValueError, TypeError, KeyError, RuntimeError):
        return None
    if not active_role(root, "ceo"):
        command = inputs.get("command")
        if (tool not in ("Bash", "PowerShell") or not isinstance(command, str)
                or command.strip(" ") not in COMMANDS or not active_role(root, "reader")):
            return None
    return {"hookSpecificOutput": {"hookEventName": "PermissionRequest", "decision": {"behavior": "allow"}}}
