"""Normalize explicitly selected agent event streams. Never retain raw payloads."""
from collections import deque
import json
import os
import re

from .observe import project_path, safe_file

TAIL_BYTES = 256 * 1024
MAX_EVENTS = 100
IDENTIFIER = re.compile(r"[a-zA-Z0-9_-]{1,128}")


def recent_lines(path):
    if not safe_file(path, float("inf")).is_file():
        return b"", []
    with path.open("rb") as source:
        identity = os.fstat(source.fileno()).st_ino
        size = source.seek(0, 2)
        offset = max(size - TAIL_BYTES, 0)
        head = b""
        if offset:
            source.seek(0)
            head = source.readline(8192)
            source.seek(offset - 1)
            partial = source.read(1) != b"\n"
        else:
            source.seek(0)
            partial = False
        rows = []
        for index, line in enumerate(source.read(TAIL_BYTES).split(b"\n")[:-1]):
            if not partial or index:
                rows.append((identity, offset, line))
            offset += len(line) + 1
    return head, rows


def normalized_path(root, value):
    if not isinstance(value, str) or len(value) > 512:
        return None
    if value.startswith(str(root) + "/"):
        value = value[len(str(root)) + 1:]
    try:
        project_path(root, value)
    except (OSError, ValueError):
        return None
    return value


def codex_event(root, raw, session):
    kind = raw.get("type")
    if kind == "thread.started":
        return raw.get("thread_id"), "session_started", []
    if kind in ("turn.started", "turn.completed", "turn.failed"):
        return session, kind.replace(".", "_"), []
    item = raw.get("item")
    if kind != "item.completed" or not isinstance(item, dict):
        return session, None, []
    if item.get("type") == "file_change":
        if item.get("status") == "failed":
            return session, "file_change_failed", []
        paths = [normalized_path(root, entry.get("path")) for entry in item.get("changes", [])[:30]
                 if isinstance(entry, dict)]
        return session, "file_change", [path for path in paths if path]
    if item.get("type") == "command_execution":
        return session, {"failed": "command_failed", "declined": "command_declined"}.get(
            item.get("status"), "command_completed"), []
    return session, None, []


def hook_event(root, raw, agent):
    session = raw.get("session_id")
    if raw.get("cwd") != str(root):
        return session, None, []
    hook = raw["hook_event_name"]
    if agent == "claude" and hook == "PostToolUse" and raw.get("tool_name") in ("Edit", "Write", "MultiEdit"):
        parameters = raw.get("tool_input")
        path = normalized_path(root, parameters.get("file_path")) if isinstance(parameters, dict) else None
        return session, "file_change" if path else "tool_completed", [path] if path else []
    kind = {"SessionStart": "session_started", "SessionEnd": "session_ended",
            "Stop": "turn_completed", "PostToolUse": "tool_completed", "Interrupt": "turn_interrupted",
            "PermissionRequest": "permission_requested"}.get(hook)
    return session, kind, []


def claude_event(root, raw):
    session = raw.get("session_id")
    if raw.get("type") == "system" and raw.get("subtype") == "init":
        if raw.get("cwd") and raw["cwd"] != str(root):
            return None, None, []
        return session, "session_started", []
    if raw.get("type") == "result":
        return session, "turn_failed" if raw.get("is_error") else "turn_completed", []
    return session, None, []


def collect(root, sources):
    events = deque(maxlen=MAX_EVENTS)
    sessions = {}
    errors = []
    for source_number, (agent, file) in enumerate(sources[:10]):
        try:
            head, lines = recent_lines(file)
        except (OSError, ValueError):
            errors.append(agent)
            continue
        session = None
        rejected_stream = set()
        for identity, offset, line in ([(-1, -1, head)] if head else []) + lines:
            try:
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    continue
                if isinstance(raw.get("hook_event_name"), str):
                    event_session, kind, paths = hook_event(root, raw, agent)
                elif agent == "codex":
                    session, kind, paths = codex_event(root, raw, session)
                    event_session = session
                else:
                    origin = raw.get("session_id")
                    if (isinstance(origin, str) and raw.get("type") == "system"
                            and raw.get("subtype") == "init" and raw.get("cwd")
                            and raw["cwd"] != str(root)):
                        rejected_stream.add(origin)
                    event_session, kind, paths = claude_event(root, raw)
                    if isinstance(event_session, str) and event_session in rejected_stream:
                        continue
                if offset == -1 or not kind or not isinstance(event_session, str) or not IDENTIFIER.fullmatch(event_session):
                    continue
                event = {"agent": agent, "session": event_session, "kind": kind, "paths": paths,
                         "id": f"{source_number}:{identity}:{offset}:{event_session}:{kind}"}
                events.append(event)
                key = (agent, event_session)
                sessions.pop(key, None)
                sessions[key] = event
                if len(sessions) > MAX_EVENTS:
                    del sessions[next(iter(sessions))]
            except (OSError, ValueError, TypeError, RecursionError):
                continue
    return {"events": list(events), "sessions": list(sessions.values()),
            "errors": errors, "configured": bool(sources)}
