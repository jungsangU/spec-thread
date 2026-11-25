"""Normalize explicitly selected agent event streams. Never retain raw payloads."""
from collections import deque
import json
import os
from pathlib import Path
import time
import re

from .observe import project_path, safe_file

TAIL_BYTES = 256 * 1024
MAX_EVENTS = 100
IDENTIFIER = re.compile(r"[a-zA-Z0-9_-]{1,128}")

WORK_ID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}")
GATE_COMMAND = re.compile(
    r"^\s*(?:python(?:3(?:\.\d+)?)?|py(?:\s+-3)?)\s+"
    r"""(?:["']?\.specify[/\\]sdd-core["']?)\s+(stage-check|gates|gate-run|gate-refresh)\s+"""
    r"([\da-f-]{36})(?=\s|$)"
)
GATE_STAGES = {"develop", "verify", "complete"}


def observed_gate_work(raw):
    saved = raw.get("gate_work")
    if isinstance(saved, dict):
        work, phase = saved.get("work"), saved.get("phase")
        if isinstance(work, str) and WORK_ID.fullmatch(work) and (phase is None or (isinstance(phase, str) and phase in GATE_STAGES)):
            return {"work": work, "phase": phase}
    if raw.get("hook_event_name") == "PostToolUse" and raw.get("tool_name") in ("Bash", "PowerShell"):
        detail = raw.get("tool_input")
    elif raw.get("type") == "item.completed":
        detail = raw.get("item")
        if not isinstance(detail, dict) or detail.get("type") != "command_execution":
            return None
    else:
        return None
    command = detail.get("command") if isinstance(detail, dict) else None
    if not isinstance(command, str) or len(command) > 4096 or re.search(r"[;|&\x60\r\n]|\$\(", command):
        return None
    match = GATE_COMMAND.match(command)
    if not match or not WORK_ID.fullmatch(match[2]):
        return None
    args = command[match.end():].split()
    phase = args[0] if match[1] == "stage-check" and args and args[0] in GATE_STAGES else None
    return {"work": match[2], "phase": phase}


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
    path = Path(value)
    if path.is_absolute():
        try:
            value = path.resolve().relative_to(root).as_posix()
        except (OSError, ValueError, RuntimeError):
            return None
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
    cwd = raw.get("cwd")
    if not isinstance(cwd, str) or not Path(cwd).is_absolute():
        return session, None, []
    try:
        directory = Path(cwd).resolve()
        if not directory.is_relative_to(root):
            return session, None, []
        candidate = directory
        while candidate != root:
            if (candidate / ".specify/spec-thread.json").is_file():
                return session, None, []
            candidate = candidate.parent
    except (OSError, ValueError, RuntimeError):
        return session, None, []
    hook = raw["hook_event_name"]
    if agent == "claude" and hook == "PostToolUse" and raw.get("tool_name") in ("Edit", "Write", "MultiEdit"):
        parameters = raw.get("tool_input")
        filename = parameters.get("file_path") if isinstance(parameters, dict) else None
        if isinstance(filename, str) and filename:
            filename = str(directory / filename)
        path = normalized_path(root, filename)
        return session, "file_change" if path else "tool_completed", [path] if path else []
    if hook == "Notification":
        return session, "input_requested" if raw.get("notification_type") in (
            "permission_prompt", "idle_prompt", "elicitation_dialog") else None, []
    if hook == "PreToolUse":
        tool = raw.get("tool_name", "")
        return session, "input_requested" if isinstance(tool, str) and (
            tool.rsplit(".", 1)[-1] in ("AskUserQuestion", "ExitPlanMode", "request_user_input")
            or tool.endswith("__request_user_input")
        ) else None, []
    kind = {"SessionStart": "session_started", "SessionEnd": "session_ended",
            "Stop": "turn_completed", "PostToolUse": "tool_completed", "UserPromptSubmit": "turn_started", "Interrupt": "turn_interrupted",
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


def collect(root, sources, project_rows=(), *, idle_seconds=900, project_configured=False):
    events = deque(maxlen=MAX_EVENTS)
    sessions = {}
    gate_work = {}
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
                work = observed_gate_work(raw)
                if work:
                    gate_work[key] = work
                sessions.pop(key, None)
                sessions[key] = event
                if len(sessions) > MAX_EVENTS:
                    del sessions[next(iter(sessions))]
            except (OSError, ValueError, TypeError, RecursionError):
                continue
    current = time.time()
    for identity, raw in project_rows:
        agent = raw["agent"]
        session, kind, paths = hook_event(root, raw, agent)
        observed_at = raw.get("observed_at")
        if not kind or not isinstance(session, str) or not IDENTIFIER.fullmatch(session):
            continue
        if not isinstance(observed_at, (int, float)) or not 0 < observed_at <= current + 60:
            continue
        event = {"agent": agent, "session": session, "kind": kind, "paths": paths,
                 "id": f"project:{identity}", "observed_at": observed_at}
        events.append(event)
        key = (agent, session)
        work = observed_gate_work(raw)
        if work:
            gate_work[key] = work
        sessions.pop(key, None)
        sessions[key] = event
    recent = list(sessions.values())[-MAX_EVENTS:]
    for session in recent:
        observed_at = session.get("observed_at")
        if session["kind"] == "session_ended":
            state = "ended"
        elif observed_at is None:
            state = "unknown"
        elif current - observed_at > idle_seconds:
            state = "quiet"
        elif session["kind"] in ("turn_started", "tool_completed", "file_change"):
            state = "working"
        else:
            state = "recent"
        session["state"] = state
        session["gate_work"] = gate_work.get((session["agent"], session["session"]))
    return {"events": list(events), "sessions": recent,
            "errors": errors, "configured": bool(sources) or project_configured or bool(project_rows)}
