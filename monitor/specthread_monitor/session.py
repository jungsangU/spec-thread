"""Opt-in interactive launch and an observation-only hook receiver."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread
import webbrowser

from sdd_core.version_sync import PROJECT
from .events import IDENTIFIER, hook_event

EVENTS = ("SessionStart", "PostToolUse", "PermissionRequest", "Stop", "SessionEnd")
EVENT_FILE = "SPECTHREAD_MONITOR_EVENTS"
FILE_LIMIT = 1024 * 1024


def hook_groups(command):
    return {event: [{"hooks": [{"type": "command", "command": command, "timeout": 1}]}]
            for event in EVENTS}


def launch_arguments(executable, agent):
    if agent == "codex":
        return [executable]
    command = shlex.join([sys.executable, "-m", "specthread_monitor.session"])
    return [executable, "--settings", json.dumps({"hooks": hook_groups(command)})]


def record_event():
    destination = os.environ.get(EVENT_FILE)
    agent = os.environ.get("SPECTHREAD_MONITOR_AGENT")
    if not destination or agent not in ("codex", "claude"):
        return
    try:
        raw = json.loads(sys.stdin.buffer.read(1024 * 1024))
        if not isinstance(raw, dict) or raw.get("hook_event_name") not in EVENTS:
            return
        root = Path.cwd().resolve()
        session, kind, paths = hook_event(root, raw, agent)
        if not kind or not isinstance(session, str) or not IDENTIFIER.fullmatch(session):
            return
        event = {"session_id": session, "cwd": str(root), "hook_event_name": raw["hook_event_name"]}
        if paths:
            event.update(tool_name="Edit", tool_input={"file_path": paths[0]})
        path = Path(destination)
        if path.stat().st_size < FILE_LIMIT:
            with path.open("ab") as stream:
                stream.write(json.dumps(event, ensure_ascii=True).encode() + b"\n")
    except (OSError, ValueError, TypeError, RecursionError):
        pass


def run_session(root, port, sources, *, browser=True):
    from .server import MonitorServer, serve_dashboard

    try:
        agent = json.loads((root / PROJECT).read_text(encoding="utf-8"))["agent"]
    except (OSError, ValueError, TypeError, KeyError):
        print("프로젝트의 SpecThread 설치 기록을 읽을 수 없습니다.", file=sys.stderr)
        return 1
    executable = shutil.which(agent) if agent in ("codex", "claude") else None
    if executable is None:
        print("에이전트 CLI를 찾을 수 없어 대시보드만 엽니다.", file=sys.stderr)
        return serve_dashboard(root, sources, port, browser=browser)
    arguments = launch_arguments(executable, agent)
    with TemporaryDirectory(prefix="specthread-session-") as directory:
        event_file = Path(directory) / "events.jsonl"
        event_file.touch(mode=0o600)
        env = {**os.environ, EVENT_FILE: str(event_file), "SPECTHREAD_MONITOR_AGENT": agent}
        try:
            server = MonitorServer(root, [*sources, (agent, event_file)], port)
        except OSError:
            print("Monitor 주소를 열지 못했습니다. 에이전트 세션은 계속 시작합니다.", file=sys.stderr)
            return subprocess.call(arguments, cwd=root, env=env)
        with server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f"http://{server.authority}/#token={server.token}"
                print(f"SpecThread Monitor  {url}", flush=True)
                if agent == "codex":
                    print("처음에는 Codex의 /hooks에서 Monitor Hook을 검토하고 신뢰해야 세션 이벤트가 표시됩니다.", flush=True)
                if browser:
                    try:
                        webbrowser.open(url)
                    except (OSError, webbrowser.Error):
                        pass
                return subprocess.call(arguments, cwd=root, env=env)
            finally:
                server.shutdown()
                thread.join()


if __name__ == "__main__":
    record_event()
